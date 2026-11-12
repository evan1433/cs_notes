---
title: Kafka 技术文档
description: Kafka 4.x 深度笔记：KRaft 架构、副本与 ISR、分区日志存储、生产者批次与幂等事务、消费者组与重平衡、分层存储、监控调优与 Spring Boot 实战
tags:
  - kafka
  - middleware
  - message-queue
  - distributed-system
  - backend
date: 2026-11-09
aliases:
  - kafka-notes
  - apache-kafka
---

# Kafka 技术文档

## 概述

Kafka 把自己定位成**分布式提交日志（distributed commit log）**，而不是传统消息队列：消息 append 到分区尾部，
按 offset 编号，读取只是移动游标，**消费不删除数据**。这个设计带来两个别家很难同时具备的性质——
**顺序写带来的高吞吐**（单机十万到百万级 TPS）和**可回溯重放**（改 offset 就能重放历史）。

代价是它把复杂度转移到了使用方：分区规划、副本同步、重平衡、消费者位移管理、幂等与顺序，
每一个踩错都会以"丢消息/重复消费/消费卡住"的形式暴露在生产环境。

本文以 **Kafka 4.x（当前稳定版 4.4.x）** 为准。4.x 有几个硬性变化必须先知道：

| 变化 | 说明 |
|------|------|
| **只支持 KRaft** | ZooKeeper 模式在 4.0 被彻底移除，`--zookeeper` 参数全部失效 |
| **Broker 需 Java 17** | Broker/Connect/Tools 最低 Java 17，客户端（含 Streams）最低 Java 11 |
| **`linger.ms` 默认 0 → 5** | 换取更大批次与更高吞吐，低延迟场景要显式改回 0 |
| **`acks` 默认 `all`** | 自 3.0 起生效，配合 `enable.idempotence=true`（默认） |
| 移除 `log.message.format.version` 等旧配置 | 升级前必须清理配置文件 |

> 总览与选型见 [[message-queue|消息队列技术文档]]；本文只讲 Kafka 自身。
> 兄弟篇：[[rocketmq|RocketMQ 技术文档]]。

## 前置知识

- [[message-queue|消息队列总览]]：队列模型 vs 日志模型、可靠性三段论
- [[docker|Docker]]：本文用它起本地集群
- [[java-concurrency|Java 并发]]：消费线程模型与背压的前提
- 分布式基础：Raft/多数派、副本、主从切换

## 快速开始

### 单节点 KRaft（开发用）

```yaml
# docker-compose.yml
services:
  kafka:
    image: apache/kafka:4.4.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      # 单节点只能单副本，否则内部 topic 创建会一直卡住
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
```

### 三条必会命令

```bash
# 1. 建 topic（分区数决定并行度上限，运行中只能增不能减）
kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic order.created --partitions 6 --replication-factor 1 \
  --config retention.ms=604800000 --config min.insync.replicas=1

# 2. 看消费组积压：LAG = LOG-END-OFFSET - CURRENT-OFFSET
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group order-service

# 3. 看 KRaft 元数据仲裁状态（4.x 没有 ZK 了，看这个）
kafka-metadata-quorum.sh --bootstrap-server localhost:9092 describe --status
```

## 架构

### KRaft：元数据自己管

ZK 时代，Broker 把元数据（topic、分区、ISR、ACL、配置）写进 ZooKeeper，controller 从 ZK 读出来下发。
链路长、一致性弱（ZK 与 Broker 视图不一致导致的"幽灵分区"是经典故障）。

KRaft 把元数据变成**一个内部的 Raft 日志**（`__cluster_metadata` topic），controller 节点组成仲裁组
（quorum）对它做多数派复制，Broker 直接消费这条日志来更新本地元数据缓存：

```text
            ┌──────────────── controller quorum (Raft) ────────────────┐
            │  controller-1(leader)   controller-2   controller-3      │
            │         │  __cluster_metadata（元数据日志）               │
            └─────────┼────────────────────────────────────────────────┘
                      │ 复制 / 下发
        ┌─────────────┼─────────────┬─────────────┐
     broker-1      broker-2       broker-3     broker-N
     （只存分区数据，元数据来自日志回放）
```

要点：

- **controller 数一般是 3 或 5**，与 broker 混部（`process.roles=broker,controller`）适合中小集群，
  大规模建议独立部署 controller 节点（`process.roles=controller`）。
- **`KAFKA_CONTROLLER_QUORUM_VOTERS` 是静态列表**；3.9 起支持动态仲裁（KIP-853），
  可以用 `kafka-metadata-quorum.sh add-controller` 在线增删 controller。
- **元数据版本（metadata.version）是一个 feature flag**，升级集群必须显式推进：
  `kafka-features.sh --bootstrap-server ... upgrade --release-version 4.4`。
- 4.0 起不再有 `config/kraft` 目录区分，KRaft 配置与普通配置合并。

### 请求路径与"哪个 broker 干活"

| 请求 | 落到哪个节点 | 说明 |
|------|--------------|------|
| Produce | 分区的 **leader** | 客户端元数据里缓存了 leader 位置，发错会收到 `NotLeaderForPartition` 后刷新重试 |
| Fetch | 分区的 **leader**（3.x 起支持 follower fetching） | 同机房消费可配置 `client.rack` + `replica.selector.class` 从 follower 读，省跨机房流量 |
| 元数据 | 任意 broker | 客户端向"最少连接数"的节点要元数据 |
| 消费组协调 | 该组的 **group coordinator** | 由 `__consumer_offsets` 分区 leader 承担 |
| 事务协调 | **transaction coordinator** | 由 `__transaction_state` 分区 leader 承担 |

### 副本与 ISR：写入什么时候算成功

每个分区有 1 个 leader + N 个 follower。follower 主动向 leader 发 fetch 拉数据（**拉模型复制**），
与普通消费者走同一套协议。关键概念：

| 概念 | 含义 |
|------|------|
| **LEO**（Log End Offset） | 每个副本自己日志的下一条待写位置 |
| **HW**（High Watermark） | ISR 中所有副本 LEO 的最小值；**消费者只能读到 HW 之前** |
| **ISR** | 与 leader 保持同步的副本集合；落后超过 `replica.lag.time.max.ms`（默认 30s）被踢出 |
| **leader epoch** | leader 纪元号，用于识别"过期 leader"并避免数据截断错乱（替代了早期的 HW 判断） |

一次写入的完整判定：

1. 生产者发到 leader，leader 追加到本地日志；
2. follower 拉取并追加，回报 LEO；
3. leader 更新 HW，并向生产者返回成功——**返回时机由 `acks` 决定**：

| `acks` | 何时返回 | 风险 |
|--------|----------|------|
| `0` | 发出即返回，不等任何确认 | 网络抖动即丢，仅日志采集可接受 |
| `1` | leader 落盘即返回 | leader 宕机、follower 未同步 → 丢 |
| `all`（`-1`） | **所有 ISR 副本都写入**才返回 | 最安全，与 `min.insync.replicas` 配合 |

```properties
# 生产环境"不丢"三件套，缺一不可
acks=all
min.insync.replicas=2
unclean.leader.election.enable=false
```

> `min.insync.replicas=2` 的直接后果：ISR 掉到 1 个副本时，生产端会收到
> `NotEnoughReplicasException`——**这是设计上的"宁可不可写也不丢数据"**。
> 此时要么恢复副本，要么临时（且明确知情地）降低该值。

### Leader 选举与 unclean 选举

leader 挂掉后，controller 从 ISR 中选新 leader（`clean` 选举），数据不丢。
如果 ISR 全挂，而某个落后很多的副本还活着，是否让它当 leader 由
`unclean.leader.election.enable` 决定：

- `false`（默认，推荐）：宁可分区不可用（`OfflinePartitionsCount > 0`），等 ISR 副本回来；
- `true`：可用性优先，但会**截断**未同步的消息——这是真丢数据。

## 存储

### 分区日志与 segment

每个分区在磁盘上是一个目录（`<topic>-<partition>`），内部是若干 segment 文件：

```text
order.created-0/
├── 00000000000000000000.log        # 消息本体（按批次追加，含 CRC）
├── 00000000000000000000.index      # offset → 物理位置（稀疏索引）
├── 00000000000000000000.timeindex  # 时间戳 → offset（按时间查位点用）
├── 00000000000000009432.log        # 滚动出的新 segment
└── leader-epoch-checkpoint         # leader 纪元与起始位移
```

几个默认值（建 topic 时最常调）：

| 配置 | 默认 | 说明 |
|------|------|------|
| `log.segment.bytes` | 1 GiB | 单个 segment 上限，写满即滚动 |
| `log.roll.hours` | 168 | 即使没写满，7 天也强制滚动 |
| `retention.ms` / `log.retention.hours` | 7 天 | 超过即删整个 segment |
| `retention.bytes` | -1（不限） | 按分区算的容量上限 |
| `segment.ms` | 7 天 | 与 `log.roll.hours` 对应 |

**删除的粒度是 segment，不是单条消息**——这就是"Kafka 不按条删"的原因，也是"消费了也不释放磁盘"的原因。

### 为什么这么快

| 手段 | 原理 |
|------|------|
| 顺序追加 | 只往文件末尾写，机械盘也能跑满带宽，避免了随机 IO |
| PageCache 优先 | 读写都先过 OS 页缓存，热数据不落盘；Kafka 自己**不维护堆内缓存**，避免 GC 压力 |
| 零拷贝 | 消费走 `sendfile`，数据从页缓存直接到 socket，省掉两次用户态拷贝 |
| 批量 + 压缩 | 生产者按批发送，broker 以批为单位存储与复制，压缩算法（lz4/zstd）对整批生效 |
| 稀疏索引 | `.index` 每 `log.index.interval.bytes`（默认 4KB）才记一条，索引小到能常驻内存 |

> 推论：**JVM 堆不要开太大**（一般 6~8GB 足够）。堆越大 GC 越久，而真正的缓存是操作系统的 PageCache。
> 磁盘建议 JBOD（多盘独立，`log.dirs=/data1,/data2,...`）而不是 RAID5——Kafka 自己用副本保证可靠性。

### 日志压缩（compaction）

对"按 key 保留最新状态"的场景（如 CDC 的 changelog、配置同步），用 `cleanup.policy=compact`：

```bash
kafka-topics.sh --bootstrap-server localhost:9092 --alter \
  --topic user.profile.compacted --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.3 --config delete.retention.ms=86400000
```

清理线程在后台重写 segment，**只保留每个 key 的最后一条**。注意：

- 压缩**不是立刻生效**，取决于 `min.cleanable.dirty.ratio` 与清理线程调度；
- key 为 null 的消息在压缩 topic 里无法被清理，会成为"垃圾"；
- `compact,delete` 可组合（既按 key 保留又按时间淘汰）。

### 分层存储（Tiered Storage）

Kafka 3.9 起 GA（KIP-405）。本地只留热数据，冷 segment 上传到对象存储/HDFS：

```properties
# broker 端开启
remote.log.storage.system.enable=true
remote.log.storage.manager.class.name=org.apache.kafka.server.log.remote.storage.RemoteLogManager
# topic 端：本地留 12 小时，远端留 30 天
local.retention.ms=43200000
retention.ms=2592000000
remote.storage.enable=true
```

带来的收益不只是省钱：**扩分区/迁移副本时只需搬本地层数据**，分区重分配和 broker 恢复都会快一个量级。
代价是冷读要走远端，延迟从毫秒变几十毫秒，且需要额外部署 RemoteStorageManager 插件（Kafka 不自带 S3 实现）。

## 生产者

### 发送流程

```text
send() → 序列化 → 分区器选分区 → RecordAccumulator（按分区攒批）
      → Sender 线程按 broker 聚合请求 → 网络发送 → 响应回调
```

关键：**`send()` 是非阻塞的**，消息进内存缓冲（`buffer.memory`，默认 32MB）就返回。
真正失败会通过回调或 `Future` 暴露——所以生产端**必须处理返回值**，否则丢消息完全是自己的锅。

```properties
# 吞吐优先（4.x 默认 linger.ms 已是 5，这里进一步放大）
batch.size=65536                # 单批上限，太小则压缩率与吞吐下降
linger.ms=20                    # 最多等 20ms 攒批，是"吞吐 vs 延迟"的总开关
compression.type=zstd           # 4.x 支持 zstd；CPU 换带宽与磁盘
buffer.memory=67108864
max.request.size=1048576
```

### 分区与有序

- key 为 null：2.4 起用**粘性分区**（sticky partitioner），一批消息尽量写同一分区，攒满再换，兼顾批效率与均衡；
- key 不为 null：`murmur2(key) % numPartitions`，**同一 key 必进同一分区**——这是保证"单实体有序"的唯一手段；
- 自定义分区器：需要按业务维度路由时实现 `Partitioner` 接口，但要清楚它会破坏默认的均衡性。

### 幂等与事务

**幂等生产者**（`enable.idempotence=true`，3.0 起默认）：broker 为每个 producer 分配 PID，
每条消息带 `<PID, epoch, sequence>`，broker 按分区去重。它解决的是**重试导致的重复写与乱序**，
覆盖范围仅限"单 producer 会话、单分区"。

```properties
enable.idempotence=true
max.in.flight.requests.per.connection=5   # ≤5 时幂等仍能保序
```

**事务**：跨分区、跨会话的原子写，配合消费端 `isolation.level=read_committed` 实现
"读—处理—写"闭环的 EOS：

```java
producer.initTransactions();
try {
    producer.beginTransaction();
    producer.send(new ProducerRecord<>("order.paid", orderId, paidEvent));
    producer.send(new ProducerRecord<>("inventory.deduct", skuId, deductEvent));
    // 把消费位移也纳入事务：要么一起生效，要么一起回滚
    producer.sendOffsetsToTransaction(currentOffsets, consumerGroupMetadata);
    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();   // 未提交的消息对 read_committed 消费者不可见
    throw e;
}
```

> 事务的性能开销不小（额外 RPC、`__transaction_state` 写入），且**不覆盖外部系统**：
> 事务里如果写了 MySQL，那部分不受 Kafka 控制。跨系统一致性请用事务消息或 Outbox 表
> （见 [[message-queue|消息队列]] 的"事务消息与数据库一致性"一节）。

## 消费者

### 消费组与位移

- 一个分区在同一时刻只被**同组**内的一个消费者消费；不同组各自持有独立位移，互不影响（广播天然支持）。
- 位移提交到内部 topic `__consumer_offsets`（50 个分区，按 group 哈希定位），由 group coordinator 管理。
- `auto.offset.reset`：**没有已提交位移**时才生效，`latest`（默认）/`earliest`/`none`（抛异常）。

```properties
enable.auto.commit=false          # 生产必须关；自动提交是"处理前就提交"，崩溃即丢
auto.offset.reset=earliest
isolation.level=read_committed    # 读事务 topic 时必须
```

### 重平衡：什么时候发生、怎么少发生

触发条件：**组成员变化**（上线/下线/心跳超时/处理超时被踢）、**订阅关系变化**、**分区数变化**。

| 协议 | 行为 | 评价 |
|------|------|------|
| Eager（Range/RoundRobin） | 全部 revoke → 重新分配 → 全部 resume | 简单，但**全组暂停**，分区多时抖动大 |
| Cooperative Sticky | 只迁移需要变动的分区，其余继续消费 | 推荐，`CooperativeStickyAssignor` |
| Static Membership | `group.instance.id` 固定身份，重启不触发重平衡 | K8s 滚动发布必备 |

```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
group.instance.id=order-service-pod-0      # 静态成员，配合优雅停机
session.timeout.ms=45000                   # 心跳超时（心跳由后台线程发）
heartbeat.interval.ms=3000
max.poll.interval.ms=300000                # 两次 poll 的最大间隔，超时=踢出组
max.poll.records=500                       # 决定单批处理耗时，最常调错的一项
```

> 高频故障：`max.poll.records` 太大 + 单条处理慢 → 单批超过 `max.poll.interval.ms` →
> 消费者被踢出组 → 重平衡 → 位移回退 → **同一批消息被反复消费**，表现为"永远追不上 lag"。
> 先降 `max.poll.records`，再谈扩分区。

### 拉取与背压

消费者是**拉模型**：`poll()` 一次拉一批，`fetch.min.bytes`（默认 1）与 `fetch.max.wait.ms`（默认 500）
控制"攒多久/攒多少再返回"。背压来自三处：

1. `max.poll.records` —— 控制单次交给业务的数量；
2. 业务侧线程池的有界队列 —— 满了就阻塞 poll（这才是真正的背压）；
3. `pause()/resume()` —— 手动暂停分区，适合下游限流的场景。

```java
// 手动暂停/恢复：下游数据库限流时不要硬扛，暂停分区比堆积在内存里安全
if (downstream.isThrottled()) {
    container.pause();
} else {
    container.resume();
}
```

### 位移重置与重放

```bash
# 把组位移重置到最早（先停消费者，否则提交会被覆盖）
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group order-service --topic order.created \
  --reset-offsets --to-earliest --execute
# 也可 --to-datetime 2026-11-01T00:00:00.000 / --shift-by -1000 / --to-offset N
```

重放是 Kafka 相对传统 MQ 的核心优势（修 bug 后重算、新服务回填历史），
但**前提是下游幂等**——重放等于主动制造重复。

## 精确一次语义的真实边界

| 场景 | 能否 EOS | 说明 |
|------|----------|------|
| Kafka → Kafka（Streams / 事务性消费-生产） | 能 | `processing.guarantee=exactly_once_v2` |
| Kafka → 外部系统（MySQL/ES/HTTP） | **不能** | MQ 无法参与外部事务，只能 at-least-once + 幂等 |
| 外部系统 → Kafka | 不能（Kafka 侧） | 用 Outbox + CDC 或事务消息 |

> 记住这句话：**EOS 是"Kafka 内部"的语义，端到端幂等永远是你的业务责任。**

## 常用运维命令

```bash
# 描述 topic：分区、副本、ISR、配置来源
kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic order.created

# 动态改配置（不必重启）
kafka-configs.sh --bootstrap-server localhost:9092 --alter \
  --entity-type topics --entity-name order.created \
  --add-config retention.ms=1209600000,max.message.bytes=2097152

# 分区重分配（限流！否则打满网卡影响正常读写）
kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file plan.json --execute --throttle 104857600

# 查看某分区的日志目录与占用
kafka-log-dirs.sh --bootstrap-server localhost:9092 --describe --topic-list order.created

# 生产者/消费者压测（官方自带，别用业务代码压）
kafka-producer-perf-test.sh --topic perf --num-records 1000000 \
  --record-size 1024 --throughput -1 --producer-props bootstrap.servers=localhost:9092 acks=all
```

跨集群同步用 **MirrorMaker 2**（基于 Connect，支持 topic 自动发现、offset 同步、ACL 同步）。
注意 4.0 已移除老的 MM1。

## 监控与调优

### 必看指标（JMX）

| 指标 | 含义 | 告警建议 |
|------|------|----------|
| `UnderReplicatedPartitions` | 副本落后的分区数 | > 0 持续 5 分钟 |
| `OfflinePartitionsCount` | 无 leader 的分区数 | **> 0 立即告警**（不可用） |
| `ActiveControllerCount` | 集群内应恒为 1 | 总和 ≠ 1 说明脑裂/无 controller |
| `IsrShrinksPerSec` / `IsrExpandsPerSec` | ISR 抖动 | 频繁收缩说明网络或磁盘跟不上 |
| `RequestHandlerAvgIdlePercent` | 请求处理线程空闲率 | < 30% 说明 CPU/线程不足 |
| `MessagesInPerSec` / `BytesInPerSec` | 入口流量 | 结合容量规划 |
| `LogFlushStats` / 磁盘使用率 | 落盘与容量 | 使用率 > 75% |
| Consumer `records-lag-max` | 消费积压 | 持续增长即告警 |

### 调优清单

| 层 | 项 | 建议 |
|----|----|------|
| OS | 文件句柄、`vm.swappiness` | `nofile` 提到 10 万+，`vm.swappiness=1`（避免换出 PageCache） |
| OS | 磁盘 | JBOD 多盘，XFS，禁用 `atime`；不要用网络存储 |
| JVM | 堆 | 6~8GB，G1（默认），`-XX:MaxGCPauseMillis=20` |
| Broker | 线程 | `num.network.threads=8`、`num.io.threads=16`（按核数调整） |
| Broker | 复制 | `num.replica.fetchers=4`，跨机房时适当放大 |
| Topic | 分区数 | 按峰值 TPS / 单分区能力估算，留 3~5 倍余量（只增不减） |
| 客户端 | 压缩 | `zstd`（CPU 换带宽，跨机房尤其值） |

## Spring Boot 3 实战

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      acks: all
      properties:
        enable.idempotence: true
        compression.type: zstd
        linger.ms: 10
    consumer:
      group-id: order-service
      enable-auto-commit: false
      max-poll-records: 200
      properties:
        isolation.level: read_committed
        partition.assignment.strategy: >-
          org.apache.kafka.clients.consumer.CooperativeStickyAssignor
    listener:
      ack-mode: manual_immediate
      concurrency: 6            # = 分区数
```

```java
@Component
public class OrderEventConsumer {

    @KafkaListener(topics = "order.created", concurrency = "6")
    public void onMessage(ConsumerRecord<String, OrderCreatedEvent> record, Acknowledgment ack) {
        // 幂等：判重表与业务写入同一本地事务，重复投递直接跳过
        if (!orderService.handleIdempotent(record.value())) {
            ack.acknowledge();
            return;
        }
        ack.acknowledge();   // 处理成功才提交位移
    }
}
```

批量消费 + 事务性写的组合（吞吐提升最明显），用 `batch="true"` 配合 `Acknowledgment`：

```java
@KafkaListener(topics = "order.created", batch = "true", concurrency = "6")
public void onBatch(List<ConsumerRecord<String, OrderCreatedEvent>> records, Acknowledgment ack) {
    orderService.batchInsert(records);   // 一条 SQL 批量写，失败整批重试
    ack.acknowledge();
}
```

## 常见误区

| 误区 | 实际情况 |
|------|----------|
| "Kafka 会删已消费的消息" | 只按 retention 删 segment，与消费无关 |
| "分区越多吞吐越高" | 分区多了元数据、重平衡、文件句柄、复制线程都变重；单 broker 数百分区以上要谨慎 |
| "自动提交 offset 省事" | 自动提交发生在处理之前，崩溃即丢消息 |
| "扩分区能救积压" | 会破坏 key→分区映射与顺序性，且不可回退；先提并发 |
| "acks=all 就一定不丢" | 还需 `min.insync.replicas>=2`，否则单副本 ISR 一样丢 |
| "开启事务就能端到端 exactly-once" | 只覆盖 Kafka 内部链路 |
| "`auto.offset.reset=earliest` 就能重放" | 只在**没有已提交位移**时生效；重放要显式 reset |
| "Kafka 适合做 RPC / 低延迟任务队列" | 有攒批与 fsync 抖动，延迟敏感场景不如 RabbitMQ |

## 排错

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 生产端 `TimeoutException: Expired` | `delivery.timeout.ms` 太短 / broker 繁忙 / 网络 | 查 `RequestHandlerAvgIdlePercent` 与磁盘 IO，放宽超时 |
| `NotEnoughReplicasException` | ISR 副本数 < `min.insync.replicas` | 恢复落后副本；确认磁盘/网络瓶颈 |
| `NotLeaderForPartitionException` | leader 切换，元数据过期 | 客户端自动重试并刷新元数据；频繁出现查 controller 日志 |
| 消费组一直在重平衡 | `max.poll.interval.ms` 太小、处理太慢、GC 停顿 | 降 `max.poll.records`、加超时、排查 Full GC |
| LAG 持续增长但 CPU 不高 | 消费者数 > 分区数（有空转）或下游 RT 高 | 对齐消费者数与分区数；查下游 |
| 消费到某条消息就卡住 | 该条处理抛异常且无限重试 | 配 `DefaultErrorHandler` + DLT，不可重试异常直接转死信 |
| 磁盘持续增长 | retention 过大 / 有组长期 lag 卡住未过期数据 | 调整 retention；`--describe` 找卡住的组 |
| 启动报 `UnsupportedVersionException` | 客户端版本高于 broker / 4.0 前配置残留 | 对齐版本，清理已移除配置 |
| `OfflinePartitionsCount > 0` | ISR 全挂且 `unclean.leader.election=false` | 恢复副本；确认是否要临时开启 unclean 选举（会丢数据） |

## 与相关概念的关系

- [[message-queue|消息队列总览]]：Kafka 是日志模型的代表，与其他产品的取舍见总览的对比表。
- [[rocketmq|RocketMQ]]：同为日志模型，但 CommitLog 单文件顺序写 + 轻量索引，业务侧多了事务/定时消息的原生支持。
- [[elasticsearch|Elasticsearch]]：经典链路 `业务库 → CDC(Kafka) → ES`，Kafka 负责缓冲与解耦。
- [[redis|Redis]]：Redis Stream 可做轻量替代，但无分区副本与长保留期，不适合做主干管道。
- [[19-microservices|微服务架构]]：事件驱动架构（EDA）以 Kafka 为事件总线，强调"事件是事实，不是命令"。

## 参考

- [Apache Kafka 官方文档](https://kafka.apache.org/documentation/)
- [Kafka 4.0 升级说明（Java 17、linger.ms、ZK 移除）](https://kafka.apache.org/40/getting-started/upgrade/)
- [Kafka 3.9 发布说明（分层存储 GA、动态 KRaft 仲裁）](https://kafka.apache.org/blog/2024/11/06/apache-kafka-3.9.0-release-announcement/)
- [KIP-405: Tiered Storage](https://cwiki.apache.org/confluence/display/KAFKA/KIP-405%3A+Kafka+Tiered+Storage)
- [Spring for Apache Kafka](https://docs.spring.io/spring-kafka/reference/)
- [[message-queue|消息队列技术文档]]
