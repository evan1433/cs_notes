---
title: 消息队列技术文档
description: 消息队列的核心模型、可靠性三段论、顺序与幂等、事务消息、延迟消息，以及 Kafka/RocketMQ/RabbitMQ/Pulsar 对比选型与 Java 实战
tags:
  - middleware
  - message-queue
  - kafka
  - rocketmq
  - rabbitmq
  - distributed-system
  - backend
date: 2026-11-09
aliases:
  - mq
  - message-queue-notes
---

# 消息队列技术文档

## 概述

同步调用把 A、B、C 三个服务的可用性、响应时间、发布节奏全部绑在一起：
- B 抖动，A 就超时；
- C 要加字段，A 就得跟着发版。

消息队列（Message Queue，MQ）在中间插一层**持久化的异步通道**，让生产方只管把事件写进去，
消费方按自己的节奏取出来处理，从而换来三件事：**解耦**、**异步**、**削峰**。

代价是分布式系统里最难的几个问题被引入了：**消息会不会丢？会不会重复？会不会乱序？积压了怎么办？
上下游数据怎么保证一致？** 本文按"模型 → 可靠性 → 一致性 → 顺序 → 实战 → 排错"的顺序展开，
产品层面的差异集中在 [主流产品对比](#主流产品对比) 一节。

本文以 **Kafka 4.x（KRaft 模式）、RocketMQ 5.x、RabbitMQ 4.x** 为主，Pulsar 作为存储计算分离方案补充。

> **定位**：MQ 是**基础设施层**的异步通信管道，不是数据库。它保证"消息按顺序追加、可被多次拉取"，
> 但**不保证业务幂等、不保证端到端只消费一次**——这两件事必须在业务侧兜住。

**单产品深度文档**（本文只做通用原理与横向对比）：

- [[kafka|Kafka 技术文档]]：KRaft 架构、ISR、分层存储、事务与重平衡调优
- [[rocketmq|RocketMQ 技术文档]]：NameServer/Broker/Proxy、CommitLog 存储、定时与事务消息

## 前置知识

- [[docker|Docker]]：本文用它起本地单机环境
- [[java-concurrency|Java 并发]]：理解消费线程模型、批处理与背压的基础
- [[redis|Redis]]：轻量场景常用 List/Stream 顶替 MQ，需要知道它的边界
- [[19-microservices|微服务架构]]：MQ 在服务拆分中承担的事件总线角色
- 分布式基础：分区、副本、Raft/Paxos 的"多数派"概念

## 快速开始

### Kafka（KRaft 单节点，4.x 已不需要 ZooKeeper）

```yaml
# docker-compose.yml —— 单节点 KRaft，仅用于开发
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
      # 单节点只能副本数为 1，否则内部 topic 创建失败
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
```

```bash
docker compose up -d
# 建 topic：3 分区 1 副本，消息保留 7 天
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic order.created --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000
# 命令行消费（从最早开始）
docker exec -it kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic order.created --from-beginning
```

### RocketMQ（NameServer + Broker）

```bash
# 5.x 的 Broker 与 NameServer 分进程；生产还要单独部署 Proxy
docker run -d --name rmqnamesrv -p 9876:9876 apache/rocketmq:5.5.1 sh mqnamesrv
docker run -d --name rmqbroker -p 10911:10911 -p 10909:10909 \
  -e "NAMESRV_ADDR=host.docker.internal:9876" \
  apache/rocketmq:5.5.1 sh mqbroker -n host.docker.internal:9876

docker exec -it rmqbroker sh mqadmin updateTopic \
  -n host.docker.internal:9876 -c DefaultCluster -t order_created_topic
```

### RabbitMQ

```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4-management
# 管理台 http://localhost:15672，默认 guest/guest（只能本机登录）
```

## 核心概念

### 两种底层模型：队列 vs 日志

所有 MQ 的差异，本质上是这两个模型的不同取舍：

| 维度   | 队列模型（RabbitMQ 经典队列）                 | 日志模型（Kafka / RocketMQ / Pulsar）   |
| ---- | ----------------------------------- | --------------------------------- |
| 消息存储 | 每条消息一个存储条目，消费后删除                    | append-only 日志，按 offset 定位，保留期内不删 |
| 消费语义 | 队列内竞争消费（一条消息只给一个消费者）                | 消费组内分区独占，组间互不影响（广播天然支持）           |
| 回溯重放 | 不支持（消费即删）；Stream 类型可回溯              | 支持，改 offset 即可重放                  |
| 路由能力 | 强（Exchange + Binding + Routing Key） | 弱（Topic + Tag/Header 过滤）          |
| 吞吐   | 单队列数万级，受队列索引限制                      | 单分区数十万级，靠分区水平扩展                   |
| 典型定位 | 业务通知、任务分发、RPC 异步化                   | 事件流、日志管道、CDC、流式计算                 |

> 结论：**需要"重放历史"就是日志模型，需要"灵活路由 + 单条精细确认"就是队列模型。**
> RabbitMQ 4.x 的 Stream 类型、Kafka 4.1 起的 Share Group（KIP-932，仍在演进）都在向对方靠拢，
> 但底层存储的差异没有变。

### 术语对照

同一件事在四个产品里叫法不同，读文档时最容易在这里绕晕：

| 概念 | Kafka | RocketMQ | RabbitMQ | Pulsar |
|------|-------|----------|----------|--------|
| 逻辑通道 | Topic | Topic | Exchange + Queue | Topic |
| 并行单元 | Partition | MessageQueue | Queue（多消费者竞争） | Partition |
| 订阅者身份 | Consumer Group | Consumer Group | Consumer（同一队列即竞争） | Subscription |
| 消费进度 | Offset（提交到 `__consumer_offsets`） | Offset（Broker 端 + 客户端） | 无 offset，消费即 ack 删除 | Cursor（ledger 级） |
| 副本机制 | ISR 同步复制 | 主从同步/异步复制 | Quorum Queue（Raft） | BookKeeper 多副本 |
| 过滤能力 | Header / Key | Tag（`TagA \|\| TagB`） | Routing Key + Header 匹配 | Tag / Key_Shared |

### 分区、消费组与重平衡

**分区是并行度的唯一来源。** 一个分区在同一时刻只能被同组内的一个消费者消费，所以：

```text
消费者数 < 分区数  → 一人负责多个分区，并行度未打满
消费者数 = 分区数  → 理想状态
消费者数 > 分区数  → 多出来的消费者分不到分区，空转（浪费）
```

Kafka 的重平衡（Rebalance）是"分区归属重新分配"，触发条件有三类：组成员变化（上下线、心跳超时）、
订阅的 topic 变化、分区数变化。**重平衡期间整个消费组暂停消费**，这是线上 lag 尖刺最常见的元凶。

两个参数直接决定会不会被误判为"死掉"：

```properties
# 心跳线程负责证明存活，与业务处理解耦
session.timeout.ms=45000            # 默认 45s，超过没心跳就踢出组
heartbeat.interval.ms=3000
# 单批消息必须在此时长内处理完，否则主动离组触发重平衡
max.poll.interval.ms=300000         # 默认 5 分钟
max.poll.records=500                # 一批拉多少条，批越大越容易超时
```

分配策略上，`CooperativeStickyAssignor`（增量式协作重平衡）只迁移需要变动的分区，远优于老版
`RangeAssignor` 的全量 revoke：

```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```

### 投递语义：三种"保证"的真实含义

| 语义 | 实现方式 | 代价 | 适用 |
|------|----------|------|------|
| At most once | 先提交 offset 再处理 | 进程崩溃即丢消息 | 日志采集等可丢场景 |
| At least once | 先处理再提交 offset | 崩溃/重试导致重复 | **绝大多数业务的选择** |
| Exactly once | 幂等生产 + 事务 + 事务性读 | 吞吐下降、只覆盖 MQ 内部链路 | 金融级流处理 |

必须记住的边界：**Kafka 的 EOS 覆盖的是"读 topic → 处理 → 写 topic"这条 Kafka 内部链路**
（`isolation.level=read_committed` + 事务性 produce）。一旦处理逻辑里写了 MySQL 或调了外部 HTTP，
端到端仍然只能是 at-least-once，**必须靠业务幂等兜底**。

### 可靠性三段论：消息在哪一段会丢

丢消息只可能发生在三个位置，逐段封堵才有意义：

| 环节 | 丢失原因 | Kafka 封堵手段 | RocketMQ 封堵手段 |
|------|----------|----------------|-------------------|
| 生产端 | 发送失败被忽略、重试耗尽 | `acks=all` + 同步 send 判返回值 + 失败落本地表重投 | `sendStatus != SEND_OK` 重投；同步发送 |
| 存储端 | 刷盘前宕机、副本未同步 | `min.insync.replicas=2`、`unclean.leader.election.enable=false` | `flushDiskType=SYNC_FLUSH` + `brokerRole=SYNC_MASTER` |
| 消费端 | 自动提交 offset、异步处理未完成就 ack | `enable.auto.commit=false` + 手动 ack（处理成功后） | `ConsumeConcurrentlyStatus.RECONSUME_LATER` |

```properties
# 生产端"不丢"的最小配置
acks=all
enable.idempotence=true                      # 3.0 起默认 true，防重试导致乱序/重复
retries=2147483647                           # 交给 delivery.timeout.ms 控制总时长
delivery.timeout.ms=120000
```

```properties
# Broker 端：至少 2 个副本确认才算写成功，且不允许落后副本当 leader
min.insync.replicas=2
unclean.leader.election.enable=false
replication.factor=3
```

> 注意 `acks=all` 只保证"写入 ISR 集合"，如果 `min.insync.replicas=1` 而 ISR 只剩一个副本，
> 照样会在该副本宕机时丢数据。**`acks=all` 与 `min.insync.replicas>=2` 必须成对出现。**

### 重复消费与幂等：这是业务问题

at-least-once 下重复是**必然**的，触发路径至少有四种：生产端重试、消费端处理完但 ack 失败、
重平衡导致分区回退、人为重置 offset 重放。所以消费端必须幂等，常用四种手法：

| 手法       | 实现                             | 适用           | 注意           |
| -------- | ------------------------------ | ------------ | ------------ |
| 唯一索引去重   | 消费记录表 + 唯一键                    | 落库类业务，最可靠    | 与业务写入同一事务    |
| 状态机      | 只允许 `待支付 → 已支付`，已是终态则跳过        | 有明确生命周期的单据   | 要处理并发更新      |
| Redis 去重 | `SET msgId NX EX 86400`        | 高频、可容忍极小概率丢失 | key 过期后仍可能重复 |
| 版本号/乐观锁  | `update ... where version = ?` | 更新类操作        | 需业务字段支持      |

```java
// 幂等消费：把"判重"和"业务写入"放进同一个本地事务
@Transactional
public void handle(OrderCreatedEvent event) {
    // ON DUPLICATE KEY UPDATE 比 INSERT IGNORE 好：只吞掉唯一键冲突，其他错误仍会抛出
    int affected = jdbc.update("""
        INSERT INTO consumed_message(msg_id, topic, consumed_at)
        VALUES (?, ?, NOW())
        ON DUPLICATE KEY UPDATE msg_id = msg_id
        """, event.msgId(), "order.created");
    if (affected == 0) {
        return;  // 已处理过，直接返回（不要抛异常，否则会无限重投）
    }
    orderRepository.markPaid(event.orderId(), event.paidAt());
}
```

> 判重表的 `msg_id` 必须由**生产端**生成并在重投时保持不变（业务单号、雪花 ID、事件 UUID），
> 不能用 Broker 生成的 messageId —— 生产端重试时它是新的。

### 顺序性：只在单分区内成立

MQ 只保证**同一分区内**的 FIFO，全局有序等于把并发度压到 1，通常不可接受。正确做法是
"**按业务主键选分区**"：

```java
// 同一个 orderId 永远进同一分区 → 该订单的创建/支付/发货严格有序
ProducerRecord<String, String> record =
        new ProducerRecord<>("order.events", String.valueOf(orderId), payload);
producer.send(record).get(3, TimeUnit.SECONDS);   // 同步等确认，失败可重投
// key 不为 null 时，默认分区器用 murmur2(key) % partitionCount 定位分区
```

消费端还要避免自己把顺序打乱：

- 禁止在消费逻辑里丢给线程池异步处理（异步即无序）；
- 重试要**阻塞当前分区**（RocketMQ 的顺序消费靠 `MessageListenerOrderly` 加本地队列锁实现）；
- 扩分区会改变 `key → partition` 的映射，**运行中扩分区会让同一 key 的新旧消息落到不同分区**，
  顺序性短期失效。分区数要一次规划到位。

### 事务消息与"数据库 + MQ"一致性

业务最常见的坑：本地事务提交成功、发消息失败（或反之）。四条路线：

| 方案             | 原理                                    | 优点             | 缺点                       |
| -------------- | ------------------------------------- | -------------- | ------------------------ |
| 本地消息表          | 业务表 + 消息表同库同事务，定时任务扫表重投               | 实现简单、不依赖 MQ 特性 | 需要扫表任务，有延迟               |
| 事务消息（RocketMQ） | 先发半消息 → 执行本地事务 → commit/rollback，超时回查 | 延迟低、无扫表        | 只有 RocketMQ 原生支持；回查接口要幂等 |
| Outbox + CDC   | 只写业务表和 outbox 表，Debezium 订阅 binlog 投递 | 业务代码零侵入、吞吐高    | 需运维 CDC 组件               |
| 最佳努力 + 对账      | 异步发送 + 定时对账补偿                         | 成本最低           | 一致性窗口长，只适合弱一致场景          |

```java
// RocketMQ 事务消息：本地事务与消息的最终一致
@RocketMQTransactionListener
public class OrderPaidTxListener implements RocketMQLocalTransactionListener {

    @Override
    public RocketMQLocalTransactionState executeLocalTransaction(Message msg, Object arg) {
        try {
            orderService.markPaid(((OrderPaidEvent) arg).orderId());
            return RocketMQLocalTransactionState.COMMIT;
        } catch (Exception e) {
            return RocketMQLocalTransactionState.ROLLBACK;
        }
    }

    // Broker 未收到 commit/rollback 时会回查（默认最多 15 次），这里必须能查真实状态且可重入
    @Override
    public RocketMQLocalTransactionState checkLocalTransaction(Message msg) {
        String orderId = new String((byte[]) msg.getHeaders().get("orderId"));
        return orderService.isPaid(orderId)
                ? RocketMQLocalTransactionState.COMMIT
                : RocketMQLocalTransactionState.UNKNOWN;
    }
}
```

Kafka 的事务（`transactional.id` + `sendOffsetsToTransaction`）解决的是**流处理场景**的读-处理-写原子性，
**不解决**"写 MySQL 和发 Kafka"的跨系统原子性，二者不可混用。

### 延迟消息

| 产品           | 能力                 | 实现                                                     |
| ------------ | ------------------ | ------------------------------------------------------ |
| RocketMQ 4.x | 固定 18 个级别（1s 到 2h） | 内部重试 topic + 定时调度                                      |
| RocketMQ 5.x | **任意时间**（定时消息）     | 时间轮 + 定时文件落盘，到期投递到真实 topic                             |
| RabbitMQ     | 需插件或 TTL + 死信      | `rabbitmq_delayed_message_exchange` 插件；或队列 TTL 到期转 DLX |
| Kafka        | 无原生支持              | 外部调度（时间轮服务/数据库扫表）后投递，或用多级 topic 模拟                     |

> RabbitMQ 用 "TTL + DLX" 模拟延迟有经典陷阱：**队列是 FIFO 的，队头消息 TTL 未到期会阻塞后面
> 短 TTL 的消息**（head-of-line blocking）。要么每个延迟档位一个队列，要么直接用延迟插件。

### 重试、死信与积压

消费失败不是"无限重试"就完事：重试要有**次数上限 + 退避 + 兜底队列**，否则一条坏消息能把整个分区堵死。

- **Kafka**：`DefaultErrorHandler` + `DeadLetterPublishingRecoverer`，超过次数投到 `xxx.DLT`；
  非幂等失败（如参数错误）应设为不可重试，直接进 DLT。
- **RocketMQ**：失败返回 `RECONSUME_LATER`，进 `%RETRY%<consumerGroup>`，默认 16 次后进
  `%DLQ%<consumerGroup>`，死信队列需要人工或定时任务处理。
- **RabbitMQ**：`basic.nack(requeue=false)` + 队列配置 `x-dead-letter-exchange` 转死信。

**积压的处置顺序**（不要一上来就扩分区）：

1. 先看是**消费能力不足**还是**下游变慢**：对比消费 TPS 与下游 RT，别盲目加消费者；
2. 消费者数已等于分区数，加机器无效 → 提升单消费者并发（批量 + 线程池，注意顺序性要求）；
3. 仍需扩容 → **新增分区**（只能增不能减，且会改变 key 映射），或提前按 3~5 倍峰值规划分区数；
4. 紧急止血：把消息转存到对象存储/临时 topic 做离线补算，先恢复主链路。

## 存储机制：为什么它能扛住百万级写入

三个产品的存储设计差异，解释了它们的性能上限：

| 产品 | 存储结构 | 关键优化 |
|------|----------|----------|
| Kafka | 每分区一个 append-only 日志，切成 segment（`.log` + `.index` + `.timeindex`） | 顺序写 + PageCache + `sendfile` 零拷贝，消费不删文件，只移动 offset |
| RocketMQ | 所有 topic 共用一个 CommitLog 顺序写，ConsumeQueue 存定长索引（offset + size + tagHash） | 单文件顺序写摊平随机 IO；索引小到可全量载入内存 |
| RabbitMQ | 经典队列：队列索引 + 消息存储；Quorum Queue：Raft 日志 | 强在路由与低延迟，吞吐受队列索引与镜像复制限制 |
| Pulsar | Broker 无状态，消息写 BookKeeper（ledger + bookie） | 存储计算分离，扩缩容不搬数据，天然多租户与分层存储 |

> 一个常被忽略的推论：Kafka **消费不删除数据**，磁盘占用只由 `retention.ms` / `retention.bytes`
> 决定。发现磁盘涨，先查 retention 与是否有消费组长期 lag 卡住（未过期数据不能删）。

## 主流产品对比

| 维度    | Kafka 4.x                | RocketMQ 5.x               | RabbitMQ 4.x            | Pulsar 4.x                   |
| ----- | ------------------------ | -------------------------- | ----------------------- | ---------------------------- |
| 模型    | 日志（分区）                   | 日志（CommitLog）              | 队列（AMQP 路由）             | 日志（分区 + BookKeeper）          |
| 单机吞吐  | 极高（十万~百万级）               | 高（十万级）                     | 中（万级）                   | 高（十万级）                       |
| 延迟    | ms 级                     | ms 级                       | **亚毫秒~ms（最低）**          | ms 级                         |
| 顺序消息  | 分区有序                     | 分区有序 + 顺序消费 API            | 单队列有序                   | 分区有序                         |
| 延迟消息  | 无原生                      | **5.x 任意时间**               | 插件/TTL+DLX              | 有（delayed delivery）          |
| 事务消息  | 流处理事务（非跨系统）              | **原生半消息 + 回查**             | 无（靠 confirm + 业务）       | 事务（较新）                       |
| 消息回溯  | 强（offset 任意重置）           | 支持（按时间/offset）             | 经典队列不支持，Stream 支持       | 强                            |
| 路由能力  | 弱                        | 中（Tag）                     | **强（Exchange/Binding）** | 中                            |
| 运维复杂度 | 中（KRaft 后大幅降低）           | 中（NameServer/Broker/Proxy） | **低**（单机即可用）            | 高（Broker + BookKeeper + 元数据） |
| 生态    | 流计算事实标准（Flink/Spark/CDC） | 阿里系、金融/电商场景成熟              | 中小企业、任务分发               | 多租户、混合云                      |
| 国内使用度 | 高                        | **很高**                     | 中                       | 低                            |

### 选型矩阵

| 场景 | 首选 | 理由 |
|------|------|------|
| 日志采集、埋点、CDC 进数据湖 | Kafka | 吞吐最高，Flink/Spark 生态无缝 |
| 订单、支付等业务事件，需事务消息/延迟消息 | RocketMQ | 半消息 + 任意延迟 + 死信齐全 |
| 任务分发、RPC 异步化、路由规则复杂 | RabbitMQ | Exchange 路由灵活，延迟最低，运维最轻 |
| 多租户 SaaS、存储计算分离、跨云 | Pulsar | 原生多租户 + 分层存储 |
| 每日消息量 < 10 万、只需简单异步 | **Redis Stream / 数据库表** | 少一个中间件就少一个故障点 |

> 反直觉但重要：**消息量很小的时候不要上 MQ**。多一个集群 = 多一套监控、告警、备份、升级、
> 权限与容量规划。用 Redis List（`LPUSH` + `BRPOP`）或一张 outbox 表往往更划算。

## 落地要点（与产品无关的共性）

不管选哪个产品，这四件事上线前必须定下来，否则换产品也救不了：

| 事项 | 要点 | 常见错误 |
|------|------|----------|
| 幂等 | 消费端用唯一键/状态机；去重 ID 由**生产端**生成 | 用 Broker 的 messageId 去重（重投后是新 ID） |
| 顺序 | 按业务主键选分区/队列，消费端禁止丢线程池异步处理 | 扩分区/扩队列后顺序性失效 |
| 一致性 | 本地消息表 / 事务消息 / Outbox+CDC 三选一 | 先提交数据库再发消息，发失败就丢事件 |
| 可观测 | lag、消费 RT、死信量、磁盘水位四项必备 | 只监控"消息有没有发出去" |

产品级的配置、客户端 API 与运维命令见单产品文档：

- [[kafka|Kafka 技术文档]]：KRaft 架构、ISR、分层存储、Spring Boot + spring-kafka 完整示例
- [[rocketmq|RocketMQ 技术文档]]：NameServer/Broker/Proxy、事务消息与定时消息代码、mqadmin 命令


## 生产实践要点

### Topic 与分区规划

- **命名**：`<业务域>.<实体>.<动作>`，如 `order.created`、`payment.refunded`；一个 topic 只承载一种事件。
- **分区数**：按 `峰值 TPS / 单分区消费能力` 估算，再乘 3~5 倍冗余（分区只增不减）。
  通用经验：业务 topic 6~12 分区，日志类 30~60；超过 100 分区要警惕元数据与重平衡开销。
- **副本数**：生产环境 3；跨机房用 MirrorMaker2 / RocketMQ 主从异步复制，不要指望跨机房强一致。
- **保留期**：按"最长故障恢复时间 + 重放窗口"设定，日志类 3~7 天，事件类可 7~30 天。

### 关键监控指标

| 指标 | 含义 | 告警阈值参考 |
|------|------|--------------|
| Consumer Lag | 未消费条数（最关键） | 持续 10 分钟增长 > 0 |
| 消费 TPS vs 生产 TPS | 是否入大于出 | 消费 < 生产 持续 5 分钟 |
| Rebalance 次数 | 组稳定性 | 每小时 > 3 次 |
| ISR 收缩 / UnderReplicated | 副本落后 | 任一分区 URP > 0 持续 5 分钟 |
| 磁盘使用率 | 保留策略是否合理 | > 75% |
| 端到端延迟 | 生产时间 → 消费时间差 | p99 超过业务 SLA |

```bash
# 查消费组积压（Kafka 4.x）
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --group order-service
# 关键列：CURRENT-OFFSET / LOG-END-OFFSET / LAG
```

### 灰度与升级

- 消费逻辑不兼容变更（字段删除、语义改变）→ **新建 topic + 双写 + 迁移消费组**，不要原地改协议；
- 加字段属于兼容变更，消费端必须忽略未知字段（Jackson `FAIL_ON_UNKNOWN_PROPERTIES=false`）；
- 客户端版本升级前先看 Broker 的兼容矩阵，Kafka 4.x **只能 KRaft**，3.x 的 ZK 集群升级需先迁 KRaft。

## 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| "MQ 保证消息不丢" | MQ 只保证"写进去且在保留期内不丢"，生产/消费两段仍需业务兜底 | 三段论逐段封堵 + 对账 |
| "MQ 保证不重复消费" | at-least-once 是主流语义，重复是必然 | 消费端幂等（唯一键/状态机） |
| "用了 MQ 就是异步解耦" | 同步等 MQ 返回结果只是把 RPC 换了个协议 | 真正异步：不阻塞主流程，失败可补偿 |
| "acks=all 就一定不丢" | `min.insync.replicas=1` 时仍可能丢 | 二者必须成对配置 |
| "Kafka 事务能保证写库 + 发消息原子" | 只覆盖 Kafka 内部读-处理-写链路 | 用事务消息 / Outbox 表 |
| "积压了扩分区就好" | 扩分区改变 key 映射、破坏顺序性，且不可逆 | 先提并发，再考虑扩分区 |
| "消息消费即删除，所以不占磁盘"（Kafka） | Kafka 按保留策略删除，与消费无关 | 查 retention 与卡住的 lag |
| "延迟队列用 TTL + DLX 一把梭" | 队头阻塞，短 TTL 被长 TTL 挡住 | 分档位队列或用延迟插件 |
| "自动提交 offset 省事" | 提交后进程崩溃 → 消息永久丢失 | 手动 ack，处理成功后提交 |

## 排错

| 现象 | 常见原因 | 排查与处理 |
|------|----------|-----------|
| Lag 持续上涨 | 消费能力不足 / 分区数瓶颈 / 下游慢 | 看消费 TPS 与下游 RT；先提并发与批量，再评估扩分区 |
| 反复重平衡、消费频繁中断 | `max.poll.interval.ms` 小于单批处理耗时；GC 停顿 | 减小 `max.poll.records`、加大超时、换协作式分配器 |
| 同一消息被消费多次 | ack 超时/重平衡回退；生产端重试 | 幂等表验证；查 `enable.auto.commit` 与 ack 时机 |
| 顺序错乱 | 多分区 / 多线程消费 / 重试跳过 | key 固定分区 + 单线程顺序消费 + 顺序重试 |
| 消息"消失" | `acks=1` + 异步刷盘；offset 自动提交 | 关自动提交；`acks=all`；RocketMQ 用同步刷盘 + 同步复制 |
| 生产者超时 `TimeoutException: Expired` | `delivery.timeout.ms` 过短；Broker 负载高 | 看 Broker 请求队列与磁盘 IO，放宽超时 |
| `UnknownTopicOrPartitionException` | topic 未创建且未开自动创建；分区被删 | 生产环境显式建 topic（`auto.create.topics.enable=false`） |
| 反序列化失败进入死循环 | 消息格式与消费者不兼容 | 设不可重试异常 + 进 DLT；消费端忽略未知字段 |
| RabbitMQ 内存告警、publish 被阻塞 | 队列堆积触发内存/磁盘水位 | 扩消费者、设 `x-max-length` 或改用 Quorum Queue |
| RocketMQ `SLAVE_NOT_AVAILABLE` | 主从同步复制但从节点不可用 | 恢复从节点；临时切异步复制需评估丢消息风险 |

## 与相关概念的关系

- 与 [[redis]] 的区别：Redis 的 List/Stream 能顶替轻量队列，但**无副本强一致、无保留期重放、
  内存成本高**，适合"任务少、可丢、要快"的场景；MQ 才是持久化管道。
- 与 [[elasticsearch]] 的联系：典型链路是 `业务库 → CDC/Kafka → ES`，MQ 承担削峰与解耦，
  ES 承担检索；这也解释了为什么两者都要关注"积压"——消费者慢会同时拖垮两端。
- 与 [[java-concurrency|Java 并发]] 的联系：消费线程模型（单线程拉取 + 批处理 + 背压）本质是
  生产者-消费者队列的分布式版本，`max.poll.records` 就是背压阀门。
- 与 [[19-microservices|微服务架构]] 的联系：服务间同步调用（RPC）与异步事件（MQ）是两种耦合方式，
  前者强一致低延迟，后者最终一致高可用；领域事件驱动架构（EDA）建立在 MQ 之上。
- 与 [[spring-boot3|Spring Boot 3]] 的联系：`spring-kafka` / `rocketmq-spring-boot-starter`
  把容器、序列化、重试、死信都封装成配置，但**幂等与顺序仍需业务自行保证**。

## 参考

- [Apache Kafka 官方文档](https://kafka.apache.org/documentation/)
- [Apache RocketMQ 官方文档](https://rocketmq.apache.org/zh/docs/)
- [RabbitMQ 官方文档](https://www.rabbitmq.com/docs)
- [Apache Pulsar 官方文档](https://pulsar.apache.org/docs/)
- [Spring for Apache Kafka 参考文档](https://docs.spring.io/spring-kafka/reference/)
- [[redis|Redis 技术文档]]
- [[elasticsearch|Elasticsearch 技术文档]]
