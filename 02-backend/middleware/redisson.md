---
title: Redisson 技术文档
description: Redisson 客户端架构、分布式对象、RLock 加锁与看门狗原理、延迟队列、限流器、布隆过滤器、Spring Boot 集成与生产配置
tags:
  - redis
  - redisson
  - middleware
  - distributed-system
  - backend
date: 2026-11-11
aliases:
  - redisson-lock
  - redisson-notes
---

# Redisson 技术文档

## 概述

Jedis / Lettuce 解决的是"怎么连上 Redis 并执行命令"，而 Redisson 在其之上解决的是"怎么把 Redis
当成一个**分布式运行时**来用"：它把 `Map`、`Lock`、`Semaphore`、`Queue`、`ExecutorService` 这些
JDK 熟悉的抽象搬到分布式环境，让多进程 JVM 像操作本地对象一样共享状态与协调并发。核心价值在三块：

- **分布式锁体系**：`RLock` 带可重入、自动续期（Watchdog）、公平锁、读写锁、联锁，生产级开箱即用
- **分布式数据结构**：延迟队列、布隆过滤器、限流器、RateLimiter、HyperLogLog 等高阶结构
- **分布式服务**：`RExecutorService` 把任务提交到远端执行，`RRemoteService` 提供轻量 RPC

Redisson 基于 Netty 实现，连接天然线程安全，底层通过 Lua 脚本保证复合操作的原子性。

> **定位**：Redisson 是客户端框架，不改变 Redis 的本质约束。Redis 是 AP 系统，主从切换瞬间锁可能
> 丢失——Redisson 让"正确使用锁"变简单，但不能把 Redis 变成强一致协调器。强一致互斥请考虑
> ZooKeeper / etcd。锁的通用原理见 [[redis|Redis]] 分布式锁一节与 [[java-high-concurrency|Java 高并发]]。

## 前置知识

- [[redis|Redis]]：数据结构、持久化与高可用架构，本文的底层依赖
- [[java-high-concurrency|Java 高并发]]：`AQS`、`ReadWriteLock` 等本地并发原语，Redisson 的接口与之对齐
- [[spring-boot3|Spring Boot 3]]：本文用其演示整合方式

## 快速开始

### 依赖

```xml
<!-- 核心包（纯客户端，不含 Spring 集成） -->
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson</artifactId>
    <version>3.45.1</version>
</dependency>

<!-- Spring Boot 场景下推荐 starter，自动装配 + 替换 Lettuce -->
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
    <version>3.45.1</version>
</dependency>
```

> **版本对齐**：starter 会传递依赖 `spring-data-redis` 与 `redisson-spring-data-xxx`。Spring Boot 3.x
> 要求 Redisson 3.17+；版本不匹配时会出现 `RedisConnectionFactory` 类型冲突或序列化异常，优先按
> [官方兼容矩阵](https://github.com/redisson/redisson/tree/master/redisson-spring-boot-starter)选版。

### 程序化配置

```java
Config config = new Config();
config.useSingleServer()
      .setAddress("redis://127.0.0.1:6379")
      .setPassword("strong-pass")
      .setDatabase(0)
      .setConnectionPoolSize(32)        // 默认 64
      .setConnectionMinimumIdleSize(8); // 空闲保活连接数

RedissonClient redisson = Redisson.create(config);

RLock lock = redisson.getLock("lock:demo");
try {
    if (lock.tryLock(3, TimeUnit.SECONDS)) {   // 未指定 leaseTime → Watchdog 生效
        // 业务代码
    }
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}

redisson.shutdown();   // 应用退出时释放连接，否则进程挂起
```

### Spring Boot 集成（redisson.yaml）

starter 默认读取 classpath 下的 `redisson.yaml`（也支持 `redisson.json`）；未提供时回退到 `spring.data.redis.*` 配置。

```yaml
# src/main/resources/redisson.yaml
singleServerConfig:
  address: "redis://127.0.0.1:6379"
  password: strong-pass
  database: 0
  connectionPoolSize: 32
  connectionMinimumIdleSize: 8
  timeout: 3000          # 命令响应超时，ms
  retryAttempts: 3       # 命令失败重试次数
  retryInterval: 1500    # 重试间隔，ms
  pingConnectionInterval: 30000  # 定期 ping 探活，防长连接被中间件静默断开
lockWatchdogTimeout: 30000      # 看门狗默认续期基准，ms
nettyThreads: 8
codec: !<org.redisson.codec.JsonJacksonCodec> {}
```

引入 starter 后，`RedissonClient` 直接注入使用，同时 `RedisTemplate` 的连接工厂被替换为 Redisson 实现（Lettuce 被顶替），一套连接池复用两条路径。

## 核心概念

### 三大 Java 客户端对比

| 维度 | Jedis | Lettuce | Redisson |
|------|-------|---------|----------|
| 底层 | 直连 Socket | Netty | Netty |
| 线程安全 | 否，需连接池 | 是（连接共享） | 是（连接池 + 复用） |
| 抽象层级 | 命令级 API | 命令级 + 异步/响应式 | **分布式对象级** |
| 分布式锁 | 手写 Lua | 手写 Lua（Spring 有 LockRepository） | `RLock` 内置 |
| 异步模型 | 同步阻塞 | Future / Reactive | RFuture / Reactive |
| 典型选择 | 老项目、简单场景 | Spring Boot 默认 | 需要锁/队列/限流等高阶能力 |

选型不是二选一：Redisson starter 与 `RedisTemplate` 可以共存，简单读写用 `RedisTemplate`，协调类语义用 Redisson API。

### 与 JDK 并发接口的对应关系

Redisson 的 API 设计刻意对齐 `java.util.concurrent`，学习成本几乎为零：

| JDK 接口 | Redisson 对应 | 底层 Redis 结构 |
|----------|---------------|-----------------|
| `ConcurrentMap` | `RMap` / `RMapCache`（带 TTL 的 entry） | Hash |
| `List` | `RList` | List |
| `Set` | `RSet` / `RSetCache` | Set |
| `SortedSet` | `RSortedSet` / `RScoredSortedSet` | Zset |
| `Queue` / `Deque` | `RQueue` / `RDeque` | List |
| `Lock` | `RLock` | Hash + Pub/Sub + Lua |
| `ReadWriteLock` | `RReadWriteLock` | RLock 组合 |
| `Semaphore` | `RSemaphore` | String 计数 + Lua |
| `CountDownLatch` | `RCountDownLatch` | String 计数 + Pub/Sub |
| `AtomicLong` | `RAtomicLong` | String |
| `ExecutorService` | `RExecutorService` | List + Pub/Sub |

其中 `RMap` / `RSet` 的 `*Cache` 变体支持**元素级 TTL**（`put(key, value, 5, TimeUnit.MINUTES)`），这是原生 Redis 结构做不到的——底层由 Redisson 的调度任务负责惰性/主动清理。

### 序列化 Codec

Redisson 的所有对象读写都经过 `Codec`，默认 `MarshallingCodec`（JBoss Marshalling，二进制，仅 Java 端可读）。常用替换：

| Codec | 特点 | 适用 |
|-------|------|------|
| `JsonJacksonCodec` | 跨语言可读，JSON 文本 | 默认推荐，但注意数值/泛型坑 |
| `TypedJsonJacksonCodec` | 携带具体类型的 Jackson | `RMap<RUser>` 等泛型场景，避免反序列化成 `LinkedHashMap` |
| `StringCodec` | 纯字符串 | 只存字符串时，运维可直接 `redis-cli` 查看 |
| `SerializationCodec` | JDK 序列化 | 兼容旧系统；体积大、跨语言差，不推荐 |
| `CompositeCodec` | 按结构组合（如 key 用 String、value 用 Jackson） | 生产推荐：key 可读、value 通用 |

```java
config.setCodec(new CompositeCodec(
        StringCodec.INSTANCE,                       // map key
        new TypedJsonJacksonCodec(Order.class),     // map value
        new JsonJacksonCodec()));                   // 其余
```

## 分布式锁 RLock（核心重点）

### 基础用法与参数语义

```java
RLock lock = redisson.getLock("lock:order:" + orderId);

// 形式 1：阻塞获取，永久等待（不要在生产用）
lock.lock();

// 形式 2：指定 leaseTime —— 到期自动释放，无看门狗续期
lock.lock(30, TimeUnit.SECONDS);

// 形式 3：限时等待 + 指定租期（推荐有明确 SLA 时使用）
boolean ok = lock.tryLock(5, 30, TimeUnit.SECONDS);
//                  ↑ 等待 5s   ↑ 持有 30s

// 形式 4：限时等待 + 不指定租期 → 看门狗自动续期（推荐默认）
boolean ok2 = lock.tryLock(5, TimeUnit.SECONDS);

try {
    // 业务
} finally {
    // unlock 前必须确认是自己持有，否则抛 IllegalMonitorStateException
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

### 加锁原理：Hash + Lua

锁不是简单的 `SET key value NX`，而是一个 **Hash 结构**：

```text
key   = lock:order:1001
field = {clientId(UUID)}:{threadId}     ← 持有者身份
value = 1                                ← 重入计数
```

加锁 Lua（简化）：

```lua
-- field 存在 → 重入，计数 +1 并刷新过期时间
if redis.call('EXISTS', KEYS[1]) == 0 then
    redis.call('HINCRBY', KEYS[1], ARGV[2], 1)
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
    return nil
end
if redis.call('HEXISTS', KEYS[1], ARGV[2]) == 1 then
    redis.call('HINCRBY', KEYS[1], ARGV[2], 1)
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
    return nil
end
return redis.call('PTTL', KEYS[1])      -- 加锁失败，返回剩余时间供客户端重试
```

这样设计带来三个性质，恰好补齐手写锁的三大缺陷（见 [[redis|Redis]] 分布式锁反模式表）：

1. **可重入**：同一线程重复加锁只增加计数，解锁递减，归零删除 key
2. **防误删**：解锁 Lua 校验 field 匹配才删，不可能释放别人的锁
3. **等待唤醒**：加锁失败的线程订阅 `redisson_lock__channel:{key}`，持有者解锁时 Publish 消息唤醒，而不是自旋轮询

### 看门狗（Watchdog）机制

业务耗时不可预知时，写死 `leaseTime` 要么提前释放（并发安全失效）、要么设太长（宕机后锁卡住）。Redisson 的解法是**不指定 `leaseTime` 时自动续期**：

```text
默认 internalLockLeaseTime = lockWatchdogTimeout = 30s
                        ┌────────────────────────────────────┐
加锁成功 ──► 启动定时任务 ── 每 leaseTime / 3 = 10s 执行续期 Lua ──► 重置 TTL 为 30s
                        │
        持有者进程存活 & 锁未被释放 → 持续续期（无限延长）
        持有者宕机 / 显式 unlock → 任务终止，锁最长 30s 后自动过期
```

关键结论（面试与排障高频）：

- **传了 `leaseTime` 就没有看门狗**——续期只服务于"未指定租期"的锁
- 看门狗的前提是**客户端进程存活**：进程被 `kill -9`、Full GC 长暂停都可能造成"业务还在跑但不再续期"，锁到期后他人即可获取，极端场景下会出现双持有
- 续期由客户端定时任务驱动（`RedissonLock` 内部 `ExpirationEntry` 调度），不是 Redis 服务端行为
- `lockWatchdogTimeout` 全局生效，按业务特征调整：短任务调小（宕机快速释放），长任务可适度放大

### 锁家族一览

| 锁类型 | 获取方式 | 语义 | 典型场景 |
|--------|----------|------|----------|
| 非公平锁（默认） | `getLock()` | 抢占式，不保证排队顺序 | 绝大多数互斥场景 |
| 公平锁 | `getFairLock()` | 先到先得，按请求顺序排队 | 对顺序敏感的串行化 |
| 读写锁 | `getReadWriteLock()` | 读读并行，读写/写写互斥 | 缓存刷新：写锁重建，读并发 |
| 联锁 MultiLock | `getMultiLock(l1, l2...)` | 同时持有全部锁才算成功 | 跨多个 Redis / 资源的原子操作 |
| 红锁 RedLock | `getRedLock(...)` | 独立多实例多数派 | 强一致诉求（见下，慎用） |

```java
// 读写锁示例：缓存重建
RReadWriteLock rw = redisson.getReadWriteLock("rw:cache:" + key);
RLock r = rw.readLock();
RLock w = rw.writeLock();
```

### RedLock 的争议

RedLock 在 N 个**相互独立**的 Redis 主节点上加锁，超过半数成功且总耗时小于锁有效期才算成功。但该算法依赖"各节点时钟近似同步"与"进程停顿可忽略"，Martin Kleppmann 与 Antirez 的著名论战结论可概括为：

- Redisson 官方也只将其列为可选项，不作为默认推荐
- 主从切换 / 时钟跳变 / GC 停顿都可能破坏其正确性假设
- **工程实践**：效率型互斥（防重复计算、防并发写脏）用单实例 `RLock` 足够；正确性攸关（资金扣减、库存精确扣减）换 ZooKeeper / 数据库行锁 / 幂等设计，而不是堆 Redis 实例

## 分布式对象与工具

### 延迟队列 RDelayedQueue

"30 分钟未支付自动取消"这类延迟任务的轻量实现，不用引入 MQ：

```java
RBlockingQueue<OrderEvent> cancelQueue =
        redisson.getBlockingQueue("queue:order-cancel");
RDelayedQueue<OrderEvent> delayedQueue =
        redisson.getDelayedQueue(cancelQueue);   // 目标队列

// 投递：30 分钟后进入 cancelQueue
delayedQueue.offer(new OrderEvent(orderId), 30, TimeUnit.MINUTES);

// 消费端：普通 BlockingQueue 语义
new Thread(() -> {
    while (!Thread.currentThread().isInterrupted()) {
        try {
            OrderEvent event = cancelQueue.take();   // 阻塞等待
            cancelOrder(event);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}).start();
```

实现原理：元素写入目标队列（List）的同时，以到期时间戳为 score 写入一份到延迟集合（Zset）；**投递方客户端**的后台任务周期性执行 Lua，把到期元素从延迟集合搬运到目标队列。

> **关键陷阱**：搬运由客户端驱动——投递进程停了，到期的元素就会滞留在 Zset 里不再投递。
> 重启后任务恢复会继续搬运，但**时效无法保证**。对时效严格（超时取消罚款级）的场景应改用
> RocketMQ 定时消息或 Kafka + 时间轮，参见 [[rocketmq|RocketMQ]] 与 [[kafka|Kafka]]。

### 限流器 RRateLimiter

```java
RRateLimiter limiter = redisson.getRateLimiter("rate:api:" + apiId);
// 全局每秒最多 100 次；RateType.PER_CLIENT 则按客户端实例独立计数
limiter.trySetRate(RateType.OVERALL, 100, 1, RateIntervalUnit.SECONDS);

if (limiter.tryAcquire(1)) {
    // 放行
} else {
    throw new BizException(429, "请求过于频繁");
}
```

原理是基于 Hash 存储 rate/interval 配置 + Lua 按时间片比例计算当前可用许可数，**均匀速率模型**而非漏桶突变。注意：

- `trySetRate` 是"不存在才设置"；改限流规则要先 `setRate`（会清空许可计数）
- 单节点 Redis 下全局限流已够用；Cluster 下限流 key 只在一个分片上，不构成集群瓶颈问题，但该分片的吞吐要扛住全部流量

### 布隆过滤器 RBloomFilter

缓存穿透的第一道防线（见 [[redis|Redis]] 缓存经典问题）：

```java
RBloomFilter<Long> filter = redisson.getBloomFilter("bloom:user");
filter.tryInit(1_000_000, 0.01);   // 预期 100 万元素，误判率 1%

filter.add(userId);
if (!filter.contains(userId)) {
    return null;    // 一定不存在，直接拦截，不打到 DB
}
// contains == true 只代表"大概率存在"，仍需查缓存/DB 确认
```

容量与误判率一旦初始化不可修改；预估容量要留余量（实际元素数超过预期会加速误判率恶化）。列表类防穿透也可用 `RHyperLogLog` 做基数统计。

### Spring Cache 集成

Redisson 提供 `RedissonSpringCacheManager`，弥补 Spring Cache 注解**原生不支持 TTL** 的短板：

```yaml
spring:
  cache:
    type: redis
```

```java
// 编程式注册，给每个 cache 配独立 TTL（Spring 原生注解缓存不支持）
@Bean
public CacheManager cacheManager(RedissonClient redisson) {
    Map<String, CacheConfig> config = new HashMap<>();
    // 参数：TTL 30min；maxIdleTime 15min（超时未被访问则淘汰）
    CacheConfig userCfg = new CacheConfig(30 * 60_000, 15 * 60_000);
    config.put("user", userCfg);
    CacheConfig hotCfg = new CacheConfig(5 * 60_000, 0);
    config.put("hot", hotCfg);
    return new RedissonSpringCacheManager(redisson, config);
}
```

> **注意**：`RedissonSpringCacheManager` 支持注解上带 TTL 元数据（`${cache.user.ttl}` 语法写进 cache name）和 yml 按 cache name 配置两种简化方式，但编程式注册最直观、配置集中，推荐中小项目直接用。

## 集群与高可用拓扑配置

Redisson 原生支持 Redis 全部部署形态，客户端自动感知拓扑变化（哨兵主从切换、Cluster 扩缩容）：

```yaml
# 哨兵
sentinelServersConfig:
  masterName: "mymaster"
  sentinelAddresses: ["redis://s1:26379", "redis://s2:26379", "redis://s3:26379"]
  password: strong-pass

# Cluster
clusterServersConfig:
  nodeAddresses: ["redis://n1:6379", "redis://n2:6379", "redis://n3:6379"]
  scanInterval: 1000        # 拓扑扫描周期，ms
  readMode: "SLAVE"         # 读走从节点（读写分离）；MASTER 则全走主
  subscriptionMode: "MASTER" # 订阅走主，避免从节点订阅积压
```

**Cluster 模式约束**（见 [[redis|Redis]] Redis Cluster）：

- Lua 脚本与事务要求所有 key 落在同一 slot。`RLock` 单 key 无碍；`RBatch` / 跨 key 的 `RMap` 操作、联锁跨节点时，key 必须用 **hash tag** 强制同槽：`lock:{order1001}:a`、`lock:{order1001}:b`
- hash tag 是以 `{}` 包裹的第一段参与 slot 计算，滥用会把热点集中到单分片，仅用于确需原子操作的一组 key

## 常见陷阱与排障

| 陷阱 | 现象 | 正解 |
|------|------|------|
| 传了 `leaseTime` 期待续期 | 业务超过 30s 后锁被他人获取 | 不传 leaseTime 才有看门狗；或 leaseTime 覆盖 P99 业务耗时 |
| `unlock()` 抛 `IllegalMonitorStateException` | 锁已超时易主/非本线程持有 | `finally` 中先 `isHeldByCurrentThread()` 再 unlock |
| 锁内业务抛异常未走 finally | 锁滞留至 TTL 到期 | lock/unlock 必须严格 try-finally 包裹 |
| 混用 Codec 读写同一 key | 反序列化 `ClassCastException` | key 的读写方统一 codec；key 建议固定 `StringCodec` |
| Jackson 读回 Integer 而非 Long | 大数值精度/类型不符预期 | 用 `TypedJsonJacksonCodec` 或统一数值类型 |
| 依赖看门狗却发生长 Full GC | 续期任务停摆，锁超时易主 | 调优 JVM（见 [[jvm\|JVM]]）；leaseTime 设为 > GC 最坏暂停 |
| 延迟任务不触发 | 投递端进程停了，搬运任务停摆 | 消费端独立部署且监控 `queue:*` Zset 积压；严格场景换 MQ 定时消息 |
| 连接池耗尽 | 请求堆积、`RedisTimeoutException` | 增大 `connectionPoolSize`，排查慢命令与大 key（`SLOWLOG`） |
| 每次请求 `getLock` 后丢弃 RedissonClient | 连接泄漏 | `RedissonClient` 全局单例，shutdown 仅在应用停机时调用 |
| `trySetRate` 后改限流不生效 | 配置"不存在才设置" | 变更规则用 `setRate`，并评估清空许可的影响 |

### 典型排障路径

```bash
# 1. 看锁的实际结构：field 是 UUID:threadId，value 是重入计数
redis-cli> HGETALL lock:order:1001
# 2. 看等待队列长度：value 是阻塞线程数
redis-cli> HGETALL redisson_lock__channel:queue
# 3. 慢命令与连接
redis-cli> SLOWLOG GET 10
redis-cli> CLIENT LIST
```

## 生产配置清单

```yaml
singleServerConfig:
  address: "redis://redis.prod.internal:6379"
  password: ${REDIS_PASSWORD}
  database: 0
  connectionPoolSize: 64          # 按 QPS × 平均命令耗时评估，默认 64 通常够
  connectionMinimumIdleSize: 16   # 应对突发，避免临时建连
  idleConnectionTimeout: 10000
  connectTimeout: 10000
  timeout: 3000                   # 命令超时；内网可降到 1000
  retryAttempts: 3
  retryInterval: 1500
  pingConnectionInterval: 30000   # 必设：防 NAT/LB 静默断连
  keepAlive: true
  subscriptionsPerConnection: 5
  subscriptionConnectionPoolSize: 25   # RLock 等待唤醒依赖订阅连接，高争用锁时调大
lockWatchdogTimeout: 30000
nettyThreads: 16                  # CPU 核数 ~ 2×
threads: 16
codec: !<org.redisson.codec.JsonJacksonCodec> {}
```

部署检查项：

- `RedissonClient` 单例注入，禁止按请求创建
- 停机钩子里调用 `redisson.shutdown()`（Spring 容器销毁回调中完成）
- 锁 key 命名带业务域前缀并纳入容量预估：每个锁是 1 个 Hash + 1 个订阅 channel
- 监控指标：`RedisTimeoutException` 频率、订阅连接数、延迟 Zset 积压长度

## 参考链接

- [Redisson GitHub Wiki（分布式锁与同步器章节）](https://github.com/redisson/redisson/wiki/8.-Distributed-locks-and-synchronizers)
- [Redisson 官方文档（配置项全表）](https://github.com/redisson/redisson/wiki/2.-Configuration)
- [Martin Kleppmann: How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)
  （RedLock 争议原文，可对照 Antirez 的回应文章阅读）
- [[redis|Redis]]：锁的手工实现反模式、Cluster 与 hashtag 细节
- [[java-high-concurrency|Java 高并发]]：本地锁 → 分布式锁的演进与选型对比
- [[rocketmq|RocketMQ]]：延迟队列的 MQ 级替代方案
