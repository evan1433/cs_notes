---
title: RocketMQ 技术文档
description: RocketMQ 5.x 深度笔记：NameServer/Broker/Proxy 架构、CommitLog 存储、顺序/定时/事务消息、重试与死信、运维命令与 Spring Boot 实战
tags:
  - rocketmq
  - middleware
  - message-queue
  - distributed-system
  - java
date: 2026-11-09
aliases:
  - rocketmq-notes
  - apache-rocketmq
---

# RocketMQ 技术文档

## 概述

RocketMQ 是阿里开源、后捐给 Apache 的消息中间件，长期支撑双十一级别的交易链路，因此在**业务消息**这个
方向上打磨得比其他产品更细：原生事务消息、任意时间的定时消息、顺序消息、消息轨迹、Tag/SQL 过滤，
这些都是电商与金融场景的高频需求。存储上它沿用日志模型，但用**单文件 CommitLog + 轻量索引**的方式
把所有 topic 的写收敛成一次顺序写，避免分区数一多就变成随机写。

5.x 是分水岭：**计算与存储分离、引入无状态 Proxy、gRPC 多语言客户端、Controller 自动选主**，
从"单机中间件"变成云原生架构。

本文以 **5.x（当前 5.5.x）** 为主，4.x 的差异（18 级延时、remoting 客户端、手工主备切换）会单独标注。
总览与选型见 [[message-queue|消息队列技术文档]]；对照篇：[[kafka|Kafka 技术文档]]。

## 前置知识

- [[message-queue|消息队列总览]]：日志模型、投递语义、可靠性三段论
- [[java-concurrency|Java 并发]]：消费线程池、顺序消费的锁机制
- [[docker|Docker]]：本地起 NameServer + Broker
- 分布式基础：主从复制、Raft 选主（Controller 模式依赖）

## 快速开始

### 本地单机（NameServer + Broker）

```bash
# 1. NameServer：无状态路由中心，多节点之间互不通信
docker run -d --name rmqnamesrv -p 9876:9876 apache/rocketmq:5.5.1 sh mqnamesrv

# 2. Broker：真正存消息的节点，启动时向 NameServer 注册
docker run -d --name rmqbroker \
  -p 10909:10909 -p 10911:10911 -p 10912:10912 \
  -e "NAMESRV_ADDR=host.docker.internal:9876" \
  apache/rocketmq:5.5.1 sh mqbroker -n host.docker.internal:9876

# 3. 建 topic（5.x 建议显式建 topic，不要依赖自动创建）
docker exec -it rmqbroker sh mqadmin updateTopic \
  -n host.docker.internal:9876 -c DefaultCluster -t order_created_topic

# 4. 验证：能看到 topic 的队列分布与 broker
docker exec -it rmqbroker sh mqadmin topicStatus \
  -n host.docker.internal:9876 -t order_created_topic
```

生产部署还要有：

```bash
# Proxy（5.x 推荐入口）：无状态，对外暴露 gRPC（8081）与 remoting（8080）
sh mqproxy -n <namesrv>:9876 -pc <proxy.conf>
```

> 4.x 客户端直连 Broker（10911）走 remoting；5.x 推荐客户端连 **Proxy**，Broker 不再直接暴露给业务。
> 老项目用 `rocketmq-client` 4.x 也能连 5.x Broker，但享受不到 gRPC 客户端的新特性（SimpleConsumer、定时消息）。

## 架构

### 四个角色

```text
             ┌──────────── NameServer 集群（无状态，互不通信）────────────┐
             │  ns1                ns2                ns3               │
             └───▲──────────────────▲──────────────────▲───────────────┘
     路由注册/心跳│                  │                  │ 路由拉取（每 30s）
          ┌──────┴───────┐   ┌──────┴───────┐          │
          │  broker-a    │   │  broker-b    │          │
          │ (master)     │   │ (master)     │          │
          │ (slave)      │   │ (slave)      │          │
          └──────▲───────┘   └──────▲───────┘          │
                 │                  │                  │
          ┌──────┴──────────────────┴──────────────────┴──────┐
          │                    Proxy（无状态）                  │
          └──────────────────────────▲─────────────────────────┘
                                     │ gRPC / remoting
                              生产者 / 消费者
```

| 角色 | 职责 | 关键点 |
|------|------|--------|
| **NameServer** | 保存 topic → 队列 → broker 的路由，提供心跳注册与路由查询 | 节点间**不通信、不同步**，靠客户端多写多读容忍不一致；单机即可扛住万级连接 |
| **Broker** | 存消息、投递消息、管消费进度 | 主从成对（brokerId 0 主 / >0 从），支持同步/异步复制与刷盘 |
| **Proxy** | 协议转换与入口：gRPC ⇄ remoting，屏蔽 broker 拓扑 | 无状态可水平扩展；`local` 模式与 broker 同进程，`cluster` 模式独立部署 |
| **Controller** | 5.x 新增，基于 Raft 选主，故障时自动切换主从 | 替代 4.x 的"手工切换 + DLedger 单独部署" |

### 路由与心跳

- Broker 每 **30s** 向所有 NameServer 发心跳（含 topic 配置、队列信息）；NameServer 超过 **120s** 没收到即剔除；
- 生产者每 30s 拉一次路由，发送失败（`No route info of this topic`、`broker busy`）时**主动刷新路由**并重试其他 broker；
- 因此 NameServer 短暂不可用**不影响已有连接的生产消费**，只影响新 topic 的路由发现——这是它敢做无状态设计的原因。

### Controller 模式（自动主备切换）

4.x 的主从切换是手工的：master 挂了需要运维改配置、重启 slave 提升为主，期间写入中断。
5.x 的 Controller 用 Raft（DLedger）维护"谁是主"的共识，Broker 向 Controller 注册并上报状态，
master 失联后 Controller 自动把 slave 提为主，并把新地址推给 NameServer：

```bash
# Controller 模式启动（三节点 controller 集群，多数派可用）
sh mqcontroller -c controller.conf
# Broker 配置里指定 controller 地址，brokerId 由 controller 分配而非写死
# enableControllerMode=true
# controllerAddr=<controller1>:9878;<controller2>:9878;<controller3>:9878
```

代价：切换依赖多数派，Controller 集群本身要按 3 节点部署；跨机房场景仍需评估脑裂风险。

## 存储

### 三个文件

```text
store/
├── commitlog/
│   └── 00000000000000000000        # 所有 topic 的消息本体，单文件 1GB，顺序写满即滚
├── consumequeue/
│   └── order_created_topic/
│       └── 0/
│           └── 00000000000000000000  # 定长索引，每条 20 字节
└── index/
    └── 20261109120000000           # 按 messageKey 反查（约 120MB/文件，500 万槽位）
```

| 文件 | 内容 | 作用 |
|------|------|------|
| **CommitLog** | 全部消息的完整内容（含 body、属性、tag） | **唯一真实存储**，写入是纯顺序 append |
| **ConsumeQueue** | 每条 20 字节：8 字节 commitlog 物理偏移 + 4 字节消息长度 + 8 字节 tag hash | 按队列消费时的索引，体积极小，几乎全量驻留 PageCache |
| **IndexFile** | 哈希槽 + 索引项（keyHash / 物理偏移 / 时间差 / 链表指针） | 支持 `mqadmin queryMsgByKey` 按业务 key 查消息 |

这个设计的核心价值：**扩容队列（topic 加队列）不会增加磁盘随机写**。Kafka 是"每分区一个日志文件"，
分区多了就是多路随机写；RocketMQ 把所有队列的写合并到 CommitLog 一条顺序流上，索引另算。

> 代价是**读放大**：消费要先读 ConsumeQueue 拿偏移，再随机读 CommitLog。所以 RocketMQ 更适合
> "顺序消费、堆积量大"而不是"大量随机按 key 查"的场景，后者要用 IndexFile（较慢）。

### mmap、刷盘与页缓存

- CommitLog 与 ConsumeQueue 都用 **mmap（内存映射）** 写，写内存即写 PageCache，由 OS 决定何时刷盘；
- 刷盘策略 `flushDiskType`：

| 策略 | 行为 | 适用 |
|------|------|------|
| `ASYNC_FLUSH`（默认） | 后台线程批量刷盘 | 大多数业务，性能最好，宕机丢少量 |
| `SYNC_FLUSH` | 每条消息等落盘才返回 | 金融/订单，吞吐下降明显 |

- 主从复制 `brokerRole`：

| 角色 | 行为 | 组合建议 |
|------|------|----------|
| `ASYNC_MASTER` | 写完主即返回，异步同步给从 | 吞吐优先，主宕机可能丢未同步消息 |
| `SYNC_MASTER` | 等从节点确认才返回 | 与 `SYNC_FLUSH` 组合才是"不丢"配置 |
| `SLAVE` | 只读副本，可承接消费（5.x 支持从节点读） | 分担消费压力 |

```properties
# broker.conf —— 金融级不丢配置（代价是 RT 上升）
brokerRole=SYNC_MASTER
flushDiskType=SYNC_FLUSH
# 主从同步复制时，从节点落后多少会拒绝写入
syncFlushTimeout=5000
```

### 文件清理

| 配置 | 默认 | 说明 |
|------|------|------|
| `fileReservedTime` | 72（小时） | 消息保留时长，从**最后一次写满该文件**算起 |
| `deleteWhen` | `04` | 每天 4 点执行清理 |
| `diskMaxUsedSpaceRatio` | 75（%） | 磁盘使用率超过后开始强制清理最旧文件 |
| `cleanFileForciblyEnable` | true | 允许强制删除未到期文件以保命 |

> 磁盘满不是"消息丢了"，而是**写入被拒绝**（`disk full`），生产端会持续失败。
> 现场处理：先扩盘或调大 `fileReservedTime` 之外的手段（清理下游积压），别只盯着 retention 改。

## 消息类型

### 普通消息

```java
// 5.x gRPC 客户端（推荐）
ClientServiceProvider provider = ClientServiceProvider.loadService();
Producer producer = provider.newProducerBuilder()
        .setClientConfiguration(ClientConfiguration.newBuilder()
                .setEndpoints("localhost:8081").build())
        .setTopics("order_created_topic")
        .build();

Message message = provider.newMessageBuilder()
        .setTopic("order_created_topic")
        .setKeys(orderId)                 // 业务 key，用于查询与去重
        .setTag("created")                // Tag 过滤
        .setBody(JsonUtils.toJson(event).getBytes(StandardCharsets.UTF_8))
        .build();

SendReceipt receipt = producer.send(message);   // 同步发送：必须判结果
```

### 顺序消息

RocketMQ 的顺序消息是**产品级能力**（Kafka 只提供"单分区有序"的原语）：

```java
// 生产端：同一个 orderId 选同一个队列（Hash 或手动指定）
rocketMQTemplate.syncSendOrderly("order_events", event, String.valueOf(orderId));
```

```java
// 消费端：ConsumeMode.ORDERLY 会对队列加锁，串行处理后再提交
@RocketMQMessageListener(
        topic = "order_events",
        consumerGroup = "order-consumer-group",
        consumeMode = ConsumeMode.ORDERLY)
public class OrderEventListener implements RocketMQListener<OrderEvent> {
    @Override
    public void onMessage(OrderEvent event) {
        orderService.apply(event);   // 抛异常会阻塞该队列重试，直到成功
    }
}
```

要点：

- 全局有序 = 所有消息进**一个队列**，吞吐等于单线程，几乎不可用；实际用**分区有序**（按业务主键选队列）；
- `MessageListenerOrderly` 用"队列锁 + 本地消费队列"保证同一队列串行；
- **顺序消费失败会阻塞该队列**（原地重试，保住顺序），默认不会自动转死信——所以必须用
  `suspendCurrentQueueTimeMillis` 控制重试间隔，并在业务侧做"超过 N 次转人工/落库"的兜底，
  否则一条坏消息能卡死整条链路。

### 定时 / 延时消息

| 版本 | 能力 | 实现 |
|------|------|------|
| 4.x | 固定 18 个级别：`1s 5s 10s 30s 1m 2m 3m 4m 5m 6m 7m 8m 9m 10m 20m 30m 1h 2h` | `delayLevel` 对应内部重试 topic |
| 5.x | **任意时刻**（传时间戳），默认上限 **24 小时**，精度**秒级**（默认 1000ms） | 时间轮 + TimerLog 定时文件落盘，到期写回 CommitLog |

```java
// 5.x：设置投递时间戳（必须先建 message.type=DELAY 的 topic）
Message message = provider.newMessageBuilder()
        .setTopic("order_timeout_topic")
        .setBody(body)
        .setDeliveryTimestamp(System.currentTimeMillis() + 30 * 60 * 1000L)  // 30 分钟后
        .build();
```

```bash
# 定时消息专用 topic（类型必须匹配，否则消息立刻投递）
sh mqadmin updateTopic -n <namesrv>:9876 -c DefaultCluster \
  -t order_timeout_topic -a +message.type=DELAY
```

坑点：**把大量消息设成同一个定时时刻**会在到期瞬间形成洪峰，导致投递延迟、精度下降——
订单超时这类场景建议按分钟做散列偏移。

### 事务消息

RocketMQ 的招牌能力，解决"本地事务 + 发消息"的原子性：

```text
1. 生产者发送【半消息】→ broker 存入 RMQ_SYS_TRANS_HALF_TOPIC（消费者不可见）
2. broker 返回成功 → 生产者执行本地事务（写订单表）
3. 本地事务成功 → 发送 COMMIT，broker 把半消息转正到真实 topic
   本地事务失败 → 发送 ROLLBACK，broker 删除半消息
4. 若 broker 一直没收到 COMMIT/ROLLBACK → 定时回查生产者的 checkLocalTransaction（默认最多 15 次）
```

```java
@Service
public class OrderPaidProducer {

    @Resource
    private RocketMQTemplate rocketMQTemplate;

    public void publishPaid(OrderPaidEvent event) {
        Message<OrderPaidEvent> message = MessageBuilder.withPayload(event)
                .setHeader(RocketMQHeaders.KEYS, event.orderId())
                .build();
        // 第二个参数会透传给 executeLocalTransaction，避免回查时再解析一遍
        rocketMQTemplate.sendMessageInTransaction("order_paid_topic", message, event.orderId());
    }
}
```

```java
@RocketMQTransactionListener
public class OrderPaidTxListener implements RocketMQLocalTransactionListener {

    @Override
    public RocketMQLocalTransactionState executeLocalTransaction(Message msg, Object arg) {
        try {
            orderService.markPaid((String) arg);
            return RocketMQLocalTransactionState.COMMIT;
        } catch (Exception e) {
            return RocketMQLocalTransactionState.ROLLBACK;
        }
    }

    // 回查：必须能查到真实事务状态，且可重复调用（幂等）
    @Override
    public RocketMQLocalTransactionState checkLocalTransaction(Message msg) {
        String orderId = (String) msg.getHeaders().get(RocketMQHeaders.KEYS);
        return orderService.isPaid(orderId)
                ? RocketMQLocalTransactionState.COMMIT
                : RocketMQLocalTransactionState.ROLLBACK;
    }
}
```

> 回查接口的三个要求：**幂等、只读、不抛异常**。回查查不到结果时返回 `UNKNOWN` 让它继续回查，
> 而不是 `ROLLBACK`——后者会把一条可能已成功的业务消息直接丢弃。

### 过滤与批量

| 方式 | 写法 | 说明 |
|------|------|------|
| Tag 过滤 | `new FilterExpression("created \|\| paid", ExpressionType.TAG)` | 服务端用 tag hash 过滤，成本极低，**首选** |
| SQL92 过滤 | `new FilterExpression("amount > 100", ExpressionType.SQL92)` | 需 broker 开启 `enablePropertyFilter=true`，按属性过滤，有性能成本 |
| 批量发送 | `producer.send(List<Message>)` | 一批 ≤ 4MB，**同一 topic 同类型**，不支持批量定时/事务 |

## 消费

### Push 与 SimpleConsumer

| 模式 | 语义 | 适用 |
|------|------|------|
| **PushConsumer** | 长轮询模拟推送：broker 挂起请求（默认十几秒），有消息立即返回；回调里处理 | 绝大多数业务，代码最简单 |
| **SimpleConsumer**（5.x） | 主动 `receive()` 一批，业务自己 ack，可控可见性超时 | 需要批处理、流控、精确控制重试的场景 |

```java
SimpleConsumer consumer = provider.newSimpleConsumerBuilder()
        .setClientConfiguration(ClientConfiguration.newBuilder()
                .setEndpoints("localhost:8081").build())
        .setConsumerGroup("order-consumer-group")
        .setAwaitDuration(Duration.ofSeconds(10))
        .setSubscriptionExpressions(Map.of(
                "order_created_topic", new FilterExpression("*", ExpressionType.TAG)))
        .build();

List<MessageView> messages = consumer.receive(16, Duration.ofSeconds(30));
for (MessageView view : messages) {
    try {
        orderService.handle(view);     // 业务处理
        consumer.ack(view);            // 成功才 ack
    } catch (Exception e) {
        // 不 ack → 可见性超时后重新投递；也可显式 changeInvisibleDuration 延后重试
        log.error("处理失败 messageId={}", view.getMessageId(), e);
    }
}
```

### 集群消费 vs 广播消费

| 模式 | 行为 | 场景 |
|------|------|------|
| `CLUSTERING`（默认） | 同组内分摊队列，一条消息只给一个消费者 | 业务消费 |
| `BROADCASTING` | 每个消费者都收到全量消息 | 本地缓存刷新、配置广播 |

广播模式**不重试、不进死信、进度存本地**，别用它做业务主链路。

### 重试与死信

| 消费模式 | 失败行为 | 兜底 |
|----------|----------|------|
| 并发消费（默认） | 进 `%RETRY%<consumerGroup>`，按退避级别重投，默认 **16 次** | 超过后进 `%DLQ%<consumerGroup>` |
| 顺序消费 | 原地阻塞重试（保住顺序），**默认不会自动进死信** | 用 `suspendCurrentQueueTimeMillis` 控间隔 + 业务侧超次转人工 |

```java
// 业务侧声明式兜底：超过次数后自己落库告警，别指望人天天看 DLQ
@RocketMQMessageListener(topic = "order_created_topic", consumerGroup = "order-consumer-group",
        maxReconsumeTimes = 5)
public class OrderListener implements RocketMQListener<OrderCreatedEvent> {
    @Override
    public void onMessage(OrderCreatedEvent event) {
        orderService.handle(event);   // 抛异常 → 重试；重试耗尽 → DLQ
    }
}
```

死信队列不是"自动处理"，必须有人管：

```bash
# 查看死信队列消息
sh mqadmin queryMsgByKey -n <namesrv>:9876 -t %DLQ%order-consumer-group -k <orderId>
# 修复后把消息重新投回原 topic（写个小工具，用相同 body 重发即可）
```

### 消费进度与堆积

```bash
# 查消费进度：Diff Total 就是积压量，最关键的一列
sh mqadmin consumerProgress -n <namesrv>:9876 -g order-consumer-group
# 看消费者实例与订阅关系（排查"为什么只有一台在消费"）
sh mqadmin consumerConnection -n <namesrv>:9876 -g order-consumer-group
# 按时间回滚进度（重放）——先停消费者！
sh mqadmin resetOffsetByTime -n <namesrv>:9876 -g order-consumer-group \
  -t order_created_topic -s 1762560000000 -f true
```

> 集群模式下进度存在 **broker**（5.x 用 RocksDB），所以"换一台机器重启消费者"不会丢进度；
> 但**队列数与消费者数不匹配**时，多出的消费者会分不到队列而空转——这和 Kafka 的逻辑一致。

## 运维命令速查

| 操作 | 命令 |
|------|------|
| 查看集群 | `mqadmin clusterList -n <ns>` |
| 查看 broker 状态 | `mqadmin brokerStatus -n <ns> -b <brokerIp>:10911` |
| 列出所有 topic | `mqadmin topicList -n <ns>` |
| 查看 topic 队列分布 | `mqadmin topicStatus -n <ns> -t <topic>` |
| 查看 topic 配置 | `mqadmin topicRoute -n <ns> -t <topic>` |
| 扩容队列 | `mqadmin updateTopic -n <ns> -c <cluster> -t <topic> -r 16` |
| 删除 topic | `mqadmin deleteTopic -n <ns> -c <cluster> -t <topic>` |
| 按 key 查消息 | `mqadmin queryMsgByKey -n <ns> -t <topic> -k <key>` |
| 按 msgId 查 | `mqadmin queryMsgById -n <ns> -i <msgId>` |
| 消费进度 | `mqadmin consumerProgress -n <ns> -g <group>` |
| 重置进度 | `mqadmin resetOffsetByTime -n <ns> -g <group> -t <topic> -s <ts>` |

## 监控与调优

### 关键指标

| 指标 | 含义 | 关注点 |
|------|------|--------|
| `Consumer Lag`（Diff Total） | 积压条数 | 持续增长 → 消费能力不足 |
| `sendTPS` / `sendLatency` | 生产吞吐与 RT | `SYNC_FLUSH` 下 RT 会明显升高 |
| `CommitLog 磁盘使用率` | 容量 | > 75% 触发清理，> 90% 强制删 |
| `PageCache busy` | 读放大严重（索引未命中） | 内存不足或消费随机读过多 |
| `Broker 的 dispatchBehindBytes` | 写入与索引构建的落后字节数 | 持续增长说明索引构建跟不上 |
| `重试队列深度` | `%RETRY%group` 的消息量 | 大量积压通常是下游故障 |

5.x 原生支持 **OpenTelemetry** 的 metrics 与 trace，推荐接 Prometheus + Grafana，别自己写埋点。

### 调优要点

| 层 | 项 | 建议 |
|----|----|------|
| OS | 内存 | PageCache 是核心，Broker 堆 8~16GB，剩下的全留给页缓存 |
| OS | 磁盘 | 顺序写为主，SSD 明显提升；不要用带电池缓存的 RAID 卡做"假同步刷盘" |
| Broker | `sendMessageThreadPoolNums` | 按 CPU 核数调，默认 1 往往偏小 |
| Broker | `useReentrantLockWhenPutMessage` | 高并发下 `true` 减少 CAS 自旋 |
| Broker | `transientStorePoolEnable` | 读写分离（堆外写缓冲）可提升写入稳定性 |
| Producer | 批量 + 压缩 | 批量 ≤ 4MB，开启压缩（zstd/lz4）降低网络与磁盘压力 |
| Consumer | 线程数 | `consumeThreadMin/Max` 与下游承载能力对齐，别盲目拉高 |

## Spring Boot 实战

```xml
<dependency>
    <groupId>org.apache.rocketmq</groupId>
    <artifactId>rocketmq-spring-boot-starter</artifactId>
    <version>2.3.3</version>
</dependency>
```

```yaml
rocketmq:
  name-server: localhost:9876
  producer:
    group: order-producer-group
    send-message-timeout: 3000
    retry-times-when-send-failed: 2
```

```java
@Service
public class OrderEventPublisher {

    @Resource
    private RocketMQTemplate rocketMQTemplate;

    public void publishCreated(OrderCreatedEvent event) {
        // syncSend：等 broker 确认，失败抛异常由本地事务/调用方处理；不要用 convertAndSend 后不管返回值
        SendResult result = rocketMQTemplate.syncSend(
                "order_created_topic:created",        // topic:tag
                MessageBuilder.withPayload(event).setHeader(RocketMQHeaders.KEYS, event.orderId()).build());
        if (result.getSendStatus() != SendStatus.SEND_OK) {
            throw new IllegalStateException("消息发送失败: " + result.getSendStatus());
        }
    }
}
```

```java
@Component
@RocketMQMessageListener(
        topic = "order_created_topic",
        selectorExpression = "created",          // 只订阅 tag=created
        consumerGroup = "order-consumer-group",
        messageModel = MessageModel.CLUSTERING,
        maxReconsumeTimes = 5)
public class OrderCreatedListener implements RocketMQListener<OrderCreatedEvent> {

    @Override
    public void onMessage(OrderCreatedEvent event) {
        // 抛异常即触发重试；重试耗尽进 %DLQ%order-consumer-group
        orderService.handleCreated(event);
    }
}
```

## 常见误区

| 误区 | 实际情况 |
|------|----------|
| "RocketMQ 消息消费后就删除" | 逻辑标记已消费，物理文件按保留时间（默认 72h）滚动清理，可回溯 |
| "自动创建 topic 很方便" | 自动创建的 topic 队列数少、权限与配置不可控，生产必须 `autoCreateTopicEnable=false` 并显式建 |
| "顺序消息可以用多线程消费" | 顺序消费本质是队列级串行，多线程会打乱顺序 |
| "定时消息可以设任意长" | 5.x 开源版默认上限 24 小时，且必须用 `message.type=DELAY` 的 topic |
| "事务消息能保证消费端也只消费一次" | 只保证"本地事务与消息发送"的原子性，消费端仍需幂等 |
| "消费失败会一直重试" | 并发消费默认 16 次后进 DLQ；顺序消费才是一直重试（会堵队列） |
| "主从切换很快" | 4.x 需手工；5.x 依赖 Controller 多数派，未部署 Controller 就没有自动切换 |
| "队列越多吞吐越高" | 队列多了索引与会话开销上升，还会让顺序性变差；按消费并行度规划 |

## 排错

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `No route info of this topic` | topic 未创建 / Broker 未注册到该 NameServer / 路由未刷新 | `mqadmin topicStatus` 确认；检查 broker 与 ns 的连通性 |
| `broker busy, start flow control` | 写入压力过大、刷盘慢、PageCache 忙 | 看磁盘 IO 与 `SYNC_FLUSH` 配置，扩 broker 或降批量 |
| 发送超时但消息其实成功了 | 网络抖动 / `sendMsgTimeout` 过短 | 用事务消息或业务幂等 + 唯一键，别靠"重发" |
| 消费组只有部分实例在消费 | 实例数 > 队列数 | 扩队列（`-r`）或减少实例；检查订阅关系是否一致（同组订阅必须完全一致） |
| 消费进度不前进、日志无异常 | 顺序消费被某条消息卡住 / 线程池满 | `consumerConnection` 看消费 RT；查卡住的消息并修复 |
| 大量消息进 DLQ | 下游长期失败 / 反序列化不兼容 | 修下游后用工具把 DLQ 消息重投 |
| NameServer 挂了但生产消费仍正常 | 路由已缓存 | 属正常现象；但新 topic 无法发现，尽快恢复 |
| 磁盘告警、写入被拒 | CommitLog 达到水位 | 扩盘、清理积压消费、评估 `fileReservedTime` |
| 定时消息立即投递 | topic 类型不是 DELAY / 时间戳早于当前 | 用 `-a +message.type=DELAY` 重建 topic |

## 与相关概念的关系

- [[message-queue|消息队列总览]]：RocketMQ 在日志模型上补足了事务消息与定时消息，是"业务消息"路线的代表。
- [[kafka|Kafka]]：同为日志模型。Kafka 强在生态与吞吐（流计算事实标准），RocketMQ 强在业务特性
  （事务/定时/顺序/轨迹）与国内运维经验；选型见总览的对比表。
- [[redis|Redis]]：Redis 的 List/Stream 只能做轻量队列，无副本与长保留期。
- [[spring-boot3|Spring Boot 3]]：`rocketmq-spring-boot-starter` 封装了模板与监听容器，但幂等与顺序语义仍需业务保证。
- [[19-microservices|微服务架构]]：事务消息是"跨服务最终一致"最常用的落地手段之一，与本地消息表、Outbox 并列。

## 参考

- [Apache RocketMQ 官方文档](https://rocketmq.apache.org/zh/docs/)
- [定时/延时消息（5.x，默认上限 24 小时、秒级精度）](https://rocketmq.apache.org/zh/docs/featureBehavior/02delaymessage/)
- [领域模型与消息传输模型](https://rocketmq.apache.org/zh/docs/domainModel/01main/)
- [RocketMQ 版本发布记录](https://rocketmq.apache.org/zh/release-notes/)
- [rocketmq-spring](https://github.com/apache/rocketmq-spring)
- [[message-queue|消息队列技术文档]]
