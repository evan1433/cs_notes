---
title: Java 后端高并发系统设计
description: 面向 Java 后端的高并发系统设计指南，涵盖单机并发、缓存、异步削峰、数据层、限流降级、分布式锁与秒杀实战
tags:
  - java
  - backend
  - concurrency
  - distributed-system
  - high-concurrency
date: 2026-11-03
---

# Java 后端高并发系统设计

> 前置知识：[[java-multithreading|Java 多线程基础]]、[[java-thread-pool|Java 线程池]]、
> [[java-concurrency|Java 并发编程（CompletableFuture）]]、[[redis|Redis]]、[[mysql|MySQL]]

## 概述

高并发要解决的矛盾只有一个：**有限的硬件资源与无限增长的并发请求之间的不匹配**。
它表现为三个工程问题——请求太多处理不过来（排队/超时）、共享资源争抢导致正确性问题（超卖/脏读）、
局部故障扩散成整体不可用（雪崩）。

本文按「单机 → 缓存 → 异步 → 数据层 → 治理」五层展开，每一层给出可直接落地的 Java 方案与参数经验值。
从系统角度看，这五层对应的是：提升单节点吞吐、降低单点读压力、削平流量峰值、突破数据库写瓶颈、保证过载时的稳定性。

## 一、先量化：高并发的核心指标

没指标就没有优化。四个量纲必须先统一：

| 指标 | 定义 | 典型健康值（参考） |
|------|------|-------------------|
| QPS / TPS | 每秒查询数 / 每秒事务数 | 视业务而定，读接口 1k~10k |
| RT（响应时间） | 请求发出到收到响应的耗时 | P99 < 200ms（C 端） |
| 并发数 | 系统同时处理的请求数 | 由下式推导 |
| 错误率 / 超时率 | 失败请求占比 | < 0.1% |

四者通过 **Little's Law（利特尔法则）** 关联：

```text
并发数 = QPS × RT
```

例：目标 QPS = 2000，P99 RT = 50ms（0.05s），则系统内需同时承载
`2000 × 0.05 = 100` 个并发请求。这直接决定了 Tomcat 线程数、连接池大小该怎么配。

> **注意**：RT 必须统一用秒作单位，且用 P99 而非平均值——平均值会掩盖长尾。

**关键推论**：优化高并发只有两条路——**缩短 RT**（缓存、索引、异步）或**增加并发处理能力**（扩容、异步化）。
单纯"加机器"只是提高并发数上限，若 RT 因慢查询恶化，加机器反而拖垮数据库。

## 二、第一层：单机并发能力

### 2.1 线程模型与线程池参数

Java 后端最常见的误区是"线程池越大越好"。实际上线程数超过 CPU 与 IO 承载能力后，
**上下文切换成本会吞掉所有收益**。

线程池大小的经典估算公式（Brian Goetz）：

```text
N_threads = N_cpu × U_cpu × (1 + W/C)

N_cpu：CPU 核数（Runtime.getRuntime().availableProcessors()）
U_cpu：期望的 CPU 利用率（0 ~ 1）
W/C  ：阻塞等待时间 / CPU 计算时间
```

| 任务类型 | W/C 特征 | 线程数取值 | 场景 |
|----------|---------|-----------|------|
| CPU 密集 | W/C ≈ 0 | N_cpu ~ N_cpu+1 | 加解密、图像处理、JSON 大报文转换 |
| IO 密集 | W/C 较大（10~100） | N_cpu × (1 + W/C) | HTTP 调用、DB 查询、Redis 访问 |
| 混合型 | 需实测 | 拆分两个池，避免互相拖累 | 见下方建议 |

**生产建议：CPU 密集与 IO 密集任务必须拆成独立线程池。** 混在一个池里，
一次 DB 抖动会让所有 CPU 密集任务排队。

```java
// 两类任务分开：rpcPool 容忍较大并发（等待远端响应），cpuPool 严格对齐核数
@Bean("rpcPool")
public ExecutorService rpcPool() {
    int ncpu = Runtime.getRuntime().availableProcessors();
    // 假定 IO 等待占比高，取 4 倍核数起步，压测后调整
    return new ThreadPoolExecutor(
        ncpu * 2, ncpu * 4,
        60L, TimeUnit.SECONDS,
        new LinkedBlockingQueue<>(2000),        // 有界队列，防止 OOM
        new ThreadFactoryBuilder().setNameFormat("rpc-%d").build(),
        new ThreadPoolExecutor.CallerRunsPolicy()); // 队列满则回压调用方，形成自我保护
}

@Bean("cpuPool")
public ExecutorService cpuPool() {
    int ncpu = Runtime.getRuntime().availableProcessors();
    return new ThreadPoolExecutor(
        ncpu, ncpu,                              // CPU 密集：不扩容
        0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(500),
        new ThreadFactoryBuilder().setNameFormat("cpu-%d").build(),
        new ThreadPoolExecutor.AbortPolicy());   // CPU 池饱和说明容量不足，快速失败优于静默排队
}
```

拒绝策略的选择本质是**过载保护策略**：

| 策略 | 行为 | 适用 |
|------|------|------|
| `AbortPolicy` | 抛 `RejectedExecutionException` | 后台任务，需显式感知失败并重试 |
| `CallerRunsPolicy` | 由提交方线程执行 | 主链路，天然形成背压，降低提交速率 |
| `DiscardOldestPolicy` | 丢弃队头任务 | 允许丢失的时效性任务（如埋点上报） |
| 自定义 | 记录日志 + 降级返回值 | 生产推荐：可观测 + 兜底 |

### 2.2 Tomcat / Web 容器参数

Spring Boot 内嵌 Tomcat 的默认参数是为"通用场景"设计的，高并发下必须调整：
默认 `server.tomcat.threads.max=200`、`accept-count=100`。

```yaml
server:
  tomcat:
    threads:
      min-spare: 50        # 预热线程，避免冷启动突发流量时现建线程
      max: 400             # 依据 Little's Law：QPS × RT，压测校准
    accept-count: 1000     # 队列长度：超过则直接拒绝连接，防止请求无限堆积
    max-connections: 10000 # NIO 下可容纳的连接数上限
    connection-timeout: 10000
  # 关键：给下游留出超时预算，避免线程被慢调用长期占用
spring:
  mvc:
    async:
      request-timeout: 10s
```

**经验值**：Web 层线程数 ≈ 单机目标 QPS × 平均 RT。若单机目标 500 QPS、RT 100ms，
则 `500 × 0.1 = 50` 即可，留 2~3 倍余量取 150~200。不要盲目调到 1000+——
Tomcat 线程是平台线程，默认栈 1MB，1000 个线程光栈内存就接近 1GB。

### 2.3 虚拟线程（JDK 21+）

平台线程昂贵（1MB 栈、内核态调度），**虚拟线程**由 JVM 调度、栈按需增长，
可以让"一个请求一个线程"的模型在十万并发下依然成立。

```java
// JDK 21：虚拟线程的 Executor，每次提交创建一个虚拟线程
try (ExecutorService vtExecutor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<OrderSummary>> futures = orderIds.stream()
        .map(id -> vtExecutor.submit(() -> queryOrderSummary(id)))
        .toList();
    for (Future<OrderSummary> f : futures) {
        render(f.join());
    }
}
// 注意：虚拟线程廉价，不要用池化思维复用；但外部资源（DB 连接）仍需限流
```

| 维度 | 平台线程 | 虚拟线程 |
|------|---------|---------|
| 内存开销 | ~1MB 栈/线程 | ~几百字节起，动态增长 |
| 创建上限 | 数千 | 百万级 |
| 调度 | OS 内核 | JVM（挂载到载体线程） |
| 适用场景 | CPU 密集、长期存活任务 | **高 IO 阻塞**、短任务 |
| 池化 | 必须池化 | 无需池化，用完即弃 |

三个必踩的坑：

1. **不要池化虚拟线程**——它足够廉价，池化反而限制吞吐。
2. **CPU 密集任务不要用虚拟线程**——没有阻塞点，无法让出载体线程，纯增加调度开销。
3. **JDK 21~23 中 `synchronized` 会 pin 住载体线程**（虚拟线程无法卸载），阻塞 IO + synchronized
   组合会退化成平台线程模型。改用 `ReentrantLock`，或升级到 **JDK 24（JEP 491）** 已修复该问题。

> 外部资源（连接池、下游 QPS 上限）是真实瓶颈，虚拟线程只能解除"线程数"限制，
> 解除不了"连接数"限制。用 `Semaphore` 显式限流：
>
> ```java
> Semaphore dbPermits = new Semaphore(hikariMaximumPoolSize);
> try (ExecutorService vt = Executors.newVirtualThreadPerTaskExecutor()) {
>     orderIds.forEach(id -> vt.submit(() -> {
>         dbPermits.acquire();          // 与连接池大小对齐，避免排队打爆连接池
>         try { return queryOrderSummary(id); }
>         finally { dbPermits.release(); }
>     }));
> }
> ```

### 2.4 锁竞争与无锁化

高并发下锁是吞吐杀手。优化路径按性价比排序：

| 手段 | 原理 | 适用场景 |
|------|------|---------|
| 减小锁粒度 | 锁代码块而非整个方法 | 通用 |
| 读写分离锁 | `ReentrantReadWriteLock` / `StampedLock` | 读多写少配置、缓存 |
| 无锁 CAS | `AtomicLong`、`LongAdder` | 计数器、序列号 |
| 分段/分片 | `ConcurrentHashMap` 分段思想、库存分段 | 热点资源争抢 |
| ThreadLocal | 线程内共享，避免共享变量 | 上下文传递、非线程安全工具类复用 |
| 不可变对象 | 无状态即无锁 | 配置、DTO |

```java
// 高并发计数：LongAdder 优于 AtomicLong —— 分段累加，冲突时分散到不同 Cell
private final LongAdder requestCounter = new LongAdder();

public void onRequest() {
    requestCounter.increment();   // 热点写场景下吞吐远高于 AtomicLong
}
public long snapshot() {
    return requestCounter.sumThenReset(); // sum() 非原子快照，监控场景可接受
}
```

`LongAdder` 的取舍：空间换时间，`sum()` 不保证强一致（适用于监控计数，不适用余额）。

## 三、第二层：缓存——把读压力挡在数据库之前

缓存是高并发读场景收益最高的手段，但也是一个**一致性难题**。

### 3.1 三大经典问题与对策

| 问题 | 现象 | 根因 | 方案 |
|------|------|------|------|
| 缓存穿透 | 查询不存在的数据，全打到 DB | 恶意攻击 / 无效 ID | 布隆过滤器 + 空值缓存（短 TTL） |
| 缓存击穿 | 单个热点 key 过期，瞬间打爆 DB | 热点 key 集中失效 | 逻辑过期 + 互斥重建；热点 key 永不过期 |
| 缓存雪崩 | 大量 key 同时失效或 Redis 宕机 | TTL 设置集中 / 单点 | TTL 加随机抖动 + 多级缓存 + Redis 集群 + 熔断降级 |

```java
// 空值缓存防穿透：DB 查不到也写入占位值，TTL 设短（如 2 分钟）
public ProductDTO getProduct(Long productId) {
    String key = "product:" + productId;
    String cached = redisTemplate.opsForValue().get(key);
    if (cached != null) {
        return "".equals(cached) ? null : JSON.parseObject(cached, ProductDTO.class);
    }
    ProductDTO product = productMapper.selectById(productId);
    if (product == null) {
        redisTemplate.opsForValue().set(key, "", 2, TimeUnit.MINUTES); // 占位，防止反复穿透
        return null;
    }
    // 基础 TTL + 随机抖动，避免同一批 key 同时过期引发雪崩
    long ttl = 30 + ThreadLocalRandom.current().nextInt(10);
    redisTemplate.opsForValue().set(key, JSON.toJSONString(product), ttl, TimeUnit.MINUTES);
    return product;
}
```

### 3.2 缓存击穿：互斥重建 vs 逻辑过期

| 方案 | 一致性 | 复杂度 | 是否阻塞 | 适用 |
|------|--------|--------|---------|------|
| 互斥锁（SETNX）重建 | 强一致 | 低 | 未命中线程等待 | 通用 |
| 逻辑过期（永不过期） | 短暂读到旧值 | 中 | 不阻塞，返回旧值 | 秒杀、热点商品 |
| 定时刷新 | 弱一致 | 低 | 不阻塞 | 可预测的热点 |

```java
// 逻辑过期方案：物理不设 TTL，value 中携带 expireAt；过期后拿锁异步重建，其他线程先返回旧值
public ProductDTO getProductWithLogicalExpire(Long productId) {
    String key = "product:logic:" + productId;
    String json = redisTemplate.opsForValue().get(key);
    if (json == null) {
        return loadAndCacheFromDb(productId, key);   // 冷启动，同步加载一次
    }
    CacheItem<ProductDTO> item = JSON.parseObject(json, new TypeReference<>() {});
    if (item.getExpireAt() > System.currentTimeMillis()) {
        return item.getData();                      // 未逻辑过期，直接返回
    }
    // 已逻辑过期：尝试抢重建锁，抢到则异步刷新，抢不到就返回旧数据（可用性优先）
    String lockKey = "lock:rebuild:" + productId;
    Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, "1", 10, TimeUnit.SECONDS); // 必须带过期时间，防死锁
    if (Boolean.TRUE.equals(acquired)) {
        CompletableFuture.runAsync(() -> {
            try {
                loadAndCacheFromDb(productId, key);
            } finally {
                redisTemplate.delete(lockKey);
            }
        }, rebuildExecutor);   // 独立的重建线程池，避免占用业务线程
    }
    return item.getData();     // 返回旧值：宁可短暂不一致，也不让请求打到 DB
}
```

### 3.3 缓存一致性策略

没有银弹，只有取舍。主流做法：

| 策略 | 流程 | 一致性 | 适用 |
|------|------|--------|------|
| **Cache Aside（推荐）** | 读：命中返回，未命中读 DB 回写；写：**先更 DB，再删缓存** | 最终一致 | 通用默认 |
| 延迟双删 | 删缓存 → 更 DB → sleep → 再删 | 较好 | 对脏读敏感 |
| binlog 订阅（Canal） | 更新 DB，订阅 binlog 异步删缓存 | 最终一致，解耦 | 大型系统 |
| Write Through / Behind | 应用只写缓存，缓存负责落库 | 依赖实现 | 写多读少 |

**为什么是"先更 DB 再删缓存"而不是"先删缓存再更 DB"？**
后者存在并发窗口：线程 A 删缓存 → 线程 B 读未命中、查到旧值写入缓存 → 线程 A 更新 DB，
此后缓存中一直是旧值，直到下次失效。而"先更 DB 再删缓存"的最坏情况是缓存被回写成旧值后
再被删除，脏数据窗口极短。

**为什么是"删除"而不是"更新"缓存？** 更新缓存会带来两类问题：
（1）写多读少时频繁无效更新；（2）缓存 value 是聚合结果时，更新成本高且易并发乱序。

### 3.4 多级缓存：本地缓存 + Redis

Redis 也有网络开销与单线程上限，极端热点（如秒杀商品）应加一层进程内缓存。

```java
// Caffeine 本地缓存 + Redis 二级缓存，本地 TTL 短（秒级）以控制不一致窗口
Cache<Long, ProductDTO> localCache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(5, TimeUnit.SECONDS)   // 短 TTL：集群内各节点不一致窗口 ≤ 5s
    .recordStats()
    .build();

public ProductDTO getProductTwoLevel(Long productId) {
    ProductDTO local = localCache.getIfPresent(productId);
    if (local != null) {
        return local;
    }
    ProductDTO remote = getProduct(productId);   // 走 Redis + DB
    if (remote != null) {
        localCache.put(productId, remote);
    }
    return remote;
}
```

取舍：本地缓存牺牲了集群一致性换取极致性能，因此 **TTL 必须短**（秒级），且只用于
极少变更、可接受短暂陈旧的数据。若需要主动失效，可借助 Redis Pub/Sub 广播清除。

### 3.5 热 Key 与 Big Key

- **热 Key**：单 key QPS 打满单个 Redis 分片。方案：key 拆分（`stock:1001:0..N` 分片）+ 本地缓存 + 读写分离。
- **Big Key**：单 value 过大导致网络阻塞与慢查询。方案：拆分为 hash 多字段、分页获取、压缩。

## 四、第三层：异步与削峰

### 4.1 异步化的三种形态

| 形态 | 手段 | 解决的问题 |
|------|------|-----------|
| 请求内并行 | `CompletableFuture` 编排多个下游调用 | 缩短 RT（串行 300ms → 并行 120ms） |
| 请求外异步 | 主流程同步返回，非关键路径丢 MQ | 缩短 RT + 削峰 |
| 削峰填谷 | MQ 缓冲，消费者按固定速率消费 | 保护下游不被峰值打垮 |

请求内并行示例（详见 [[java-concurrency|Java 并发编程（CompletableFuture）]]）：

```java
// 商品详情页聚合：4 个下游调用从串行改为并行，RT 由 max 决定而非 sum
public ProductDetail aggregate(Long productId) {
    CompletableFuture<ProductInfo> info = CompletableFuture
        .supplyAsync(() -> productService.getInfo(productId), rpcPool);
    CompletableFuture<Integer> stock = CompletableFuture
        .supplyAsync(() -> stockService.getStock(productId), rpcPool);
    CompletableFuture<List<Comment>> comments = CompletableFuture
        .supplyAsync(() -> commentService.topN(productId, 10), rpcPool)
        .exceptionally(ex -> List.of());   // 非关键依赖：降级为空列表，不拖垮主流程

    // orTimeout 是 JDK 9+ 的能力，必须有超时兜底，否则慢依赖会拖死整个请求
    return info.thenCombine(stock, ProductDetail::new)
               .thenCombine(comments, ProductDetail::withComments)
               .orTimeout(300, TimeUnit.MILLISECONDS)
               .exceptionally(ex -> ProductDetail.fallback(productId))
               .join();
}
```

**要点**：并行编排必须配 `orTimeout` + `exceptionally`，且每个下游要有独立超时预算。
任一依赖缺少超时，线程池就会被慢调用占满，进而拖垮整个服务。

### 4.2 MQ 削峰与消息可靠性

秒杀下单这类写场景，真实峰值可能是 DB 承载能力的十倍。MQ 把"瞬时写入"变成"匀速写入"：

```text
用户请求 → 网关限流 → 校验/扣库存 → 投递 MQ（毫秒级返回） → 消费者匀速落库
```

可靠性三要素（以 RocketMQ / Kafka 为例）：

| 环节 | 风险 | 保障手段 |
|------|------|---------|
| 生产端 | 消息丢失 | 发送确认（同步/异步 + 重试）、事务消息 |
| Broker | 宕机丢消息 | 多副本、同步刷盘（性能与可靠性取舍） |
| 消费端 | 处理失败/重复 | 幂等消费 + 手动 ACK + 重试队列 + 死信队列 |

### 4.3 幂等设计（异步场景必做）

消息重投、上游重试、用户重复点击都会导致重复请求，所有写接口必须幂等：

| 方案 | 实现 | 适用 |
|------|------|------|
| 数据库唯一索引 | 用业务唯一键建 unique index，冲突即忽略 | 最可靠，首选 |
| 防重 Token | 进入页面先申请 token，提交时校验并删除 | 防表单重复提交 |
| 状态机 | `待支付 → 已支付` 才允许流转，UPDATE 带 where 状态 | 订单状态流转 |
| 乐观锁 | `UPDATE ... SET stock = stock - 1 WHERE id = ? AND stock = ?` | 库存扣减 |

```java
// 消费端幂等：以 messageId 建唯一索引，重复消息直接 ACK 忽略
@Transactional
public void handleOrderCreated(OrderCreatedMessage msg) {
    try {
        idempotentMapper.insertIgnore(msg.getMessageId(), "ORDER_CREATED");
    } catch (DuplicateKeyException e) {
        log.warn("duplicate message ignored, messageId={}", msg.getMessageId());
        return;   // 已处理过，直接返回成功
    }
    doCreateOrder(msg);
}
```

## 五、第四层：数据层——突破写瓶颈

### 5.1 连接池调优

HikariCP 是 Spring Boot 默认连接池。常见错误是把 `maximum-pool-size` 调到几百——
**连接池不是越大越好**，数据库能并行执行的查询数受 CPU 与磁盘限制。

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20       # 经验公式：connections ≈ core_count × 2 + disk_count
      minimum-idle: 10            # 与 maximum 一致可消除扩容抖动，但会常驻连接
      connection-timeout: 3000    # 获取连接超时：快速失败优于无限等待
      idle-timeout: 600000
      max-lifetime: 1800000       # 必须小于 DB 的 wait_timeout，避免拿到被服务端关闭的连接
      validation-timeout: 1000
```

HikariCP 官方建议：`connections = ((core_count × 2) + effective_spindle_count)`。
4 核 SSD 机器约 10~20 即可。连接数翻倍不会让吞吐翻倍，反而增加锁竞争与上下文切换。

**关键一致性原则**：`maximumPoolSize ≥ Web 线程数 × 单请求平均连接占用时间占比`，
否则线程会阻塞在获取连接上。更简单的办法：让 Web 线程数不要远超连接池，或启用
异步Servlet 释放 Tomcat 线程。

### 5.2 库存扣减：三种方案对比（秒杀核心）

| 方案 | 实现 | 一致性 | 性能 | 风险 |
|------|------|--------|------|------|
| 悲观锁 | `SELECT ... FOR UPDATE` | 强一致 | 低（串行化） | 死锁、连接池占满 |
| 乐观锁 | `UPDATE ... WHERE stock = 期望值` 重试 | 强一致 | 中 | 高冲突下大量重试失败 |
| Redis 预扣减 + 异步落库 | 原子 `DECR` 判断，MQ 异步落库 | 最终一致 | 高 | 需处理回滚与对账 |

```java
// 方案：Redis 原子预扣减 + MQ 异步落库（秒杀场景首选）
public SeckillResult seckill(Long productId, Long userId) {
    String stockKey = "seckill:stock:" + productId;
    // Lua 脚本保证「判断库存 + 扣减 + 记录用户」三步原子，避免超卖与重复抢购
    Long result = redisTemplate.execute(stockScript,
        List.of(stockKey, "seckill:users:" + productId), productId.toString(), userId.toString());
    if (result == null || result < 0) {
        return SeckillResult.soldOut();      // -1：库存不足；-2：重复下单
    }
    // 库存扣减成功后立即返回，订单创建走 MQ 异步化，RT 从百毫秒降到毫秒级
    mqTemplate.send("seckill-order-topic", new SeckillOrderMessage(productId, userId));
    return SeckillResult.accepted();
}
```

对应 Lua（保证原子性）：

```lua
-- KEYS[1]=库存key, KEYS[2]=已购用户集合, ARGV[1]=商品ID, ARGV[2]=用户ID
local stock = tonumber(redis.call('get', KEYS[1]))
if stock == nil or stock <= 0 then
    return -1                                   -- 库存不足
end
if redis.call('sismember', KEYS[2], ARGV[2]) == 1 then
    return -2                                   -- 重复抢购
end
redis.call('decr', KEYS[1])
redis.call('sadd', KEYS[2], ARGV[2])
return stock - 1
```

> **为什么必须用 Lua**：`GET` 判断 + `DECR` 扣减若分两次调用，并发下会出现
> "都读到 stock=1，都执行 DECR" 的超卖。Lua 脚本在 Redis 中单线程原子执行。

### 5.3 读写分离与分库分表

| 阶段 | 手段 | 解决 |
|------|------|------|
| 读写压力不均 | 主从复制 + 读写分离 | 读扩展 |
| 单表数据量过大 | 分库分表（ShardingSphere） | B+ 树层级降低、锁范围缩小 |
| 跨库事务 | 柔性事务 / Seata / 本地消息表 | 一致性 |

分片键选择原则：**按最高频查询维度分片**，并避免跨片查询与分布式事务。
订单表常用 `user_id` 分片（用户查自己的订单是核心场景），同时维护 `order_id → user_id` 的路由表支撑按单号查询。

## 六、第五层：服务治理——过载时如何活下来

高并发下最危险的不是"慢"，而是"雪崩"：A 慢 → B 线程池占满 → B 不可用 → C 重试 → 全链路崩溃。

### 6.1 限流

| 算法 | 原理 | 特点 | 实现 |
|------|------|------|------|
| 计数器（固定窗口） | 单位时间计数 | 临界突刺问题（2 倍流量） | 简单，精度要求低 |
| 滑动窗口 | 细分格子统计 | 平滑，无临界问题 | Sentinel 默认 |
| 令牌桶 | 匀速生成令牌，允许突发 | **允许突发**，推荐 | Guava `RateLimiter` |
| 漏桶 | 恒定速率出水 | 严格平滑，无突发 | 网关层整形 |

```java
// 单机限流：Guava RateLimiter（令牌桶）—— 适合保护本地资源（如昂贵的本地计算）
RateLimiter limiter = RateLimiter.create(500.0);   // 每秒 500 个令牌

public Response query(Request req) {
    if (!limiter.tryAcquire(50, TimeUnit.MILLISECONDS)) {   // 最多等 50ms，超时即降级
        return Response.tooManyRequests("系统繁忙，请稍后再试");
    }
    return doQuery(req);
}
```

**单机限流 vs 分布式限流**：单机限流的集群总配额 = 单机配额 × 节点数，节点伸缩时不准；
分布式限流用 Redis（如 `INCR` + 过期窗口）或 Sentinel 集群流控，代价是每次请求多一次 Redis 访问。
生产通常**网关层做粗粒度分布式限流 + 单机做细粒度兜底**。

### 6.2 熔断与降级

| 机制 | 触发条件 | 行为 |
|------|---------|------|
| 熔断（Circuit Breaker） | 错误率/慢调用比例超阈值 | 直接快速失败，不再调用下游；半开状态试探恢复 |
| 降级 | 熔断打开 / 手动开关 / 资源不足 | 返回兜底值（缓存旧值、默认值、空列表） |
| 隔离（Bulkhead） | —— | 不同下游用独立线程池/信号量，故障不扩散 |

```java
// Resilience4j：超时 + 熔断 + 舱壁隔离，三者通常组合使用
@CircuitBreaker(name = "couponService", fallbackMethod = "queryCouponFallback")
@TimeLimiter(name = "couponService")     // 必须有超时，否则熔断依赖的慢调用统计无从谈起
@Bulkhead(name = "couponService", type = Bulkhead.Type.THREADPOOL)
public CompletableFuture<List<Coupon>> queryCoupons(Long userId) {
    return CompletableFuture.supplyAsync(() -> couponClient.list(userId));
}

public CompletableFuture<List<Coupon>> queryCouponFallback(Long userId, Throwable t) {
    log.warn("coupon service degraded, userId={}", userId, t);
    return CompletableFuture.completedFuture(List.of());  // 优惠券不可用不影响下单主流程
}
```

### 6.3 超时与重试

**超时必须逐层收敛**：网关 3s > 服务 A 2s > 服务 B 1s > DB 500ms。
外层超时必须大于内层，否则外层先超时（用户已放弃）而内层还在执行，白白消耗资源。

重试的风险是**重试风暴**：下游已经过载，上游重试 3 倍流量直接压垮它。

| 反模式 | 正确做法 |
|--------|---------|
| 无条件重试 | 只对**幂等**的读/写 + 可恢复错误（超时、5xx）重试，业务错误（4xx）不重试 |
| 固定间隔立即重试 | 指数退避 + 抖动（jitter），避免重试请求对齐形成第二波峰值 |
| 无限重试 | 限制重试次数（≤ 2 次）；配合熔断，下游不健康时直接不重试 |
| 链路中每个节点都重试 | 只在**链路最外层**重试，避免放大（3 层 × 3 次 = 27 倍） |

## 七、分布式锁

单机 `synchronized` 在多实例部署下失效，需要跨 JVM 的互斥。

| 方案 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| Redis SETNX | `SET key val NX PX 30000` | 性能高、实现简单 | 非阻塞、需处理续期与误删 |
| Redisson | `RLock` + Watchdog 自动续期 | 可重入、自动续期、生产可用 | 依赖 Redisson；主从切换有极端风险 |
| Redlock | 多独立 Redis 实例多数派 | 理论上更健壮 | 争议大（时钟/GC 假设），多数场景不推荐 |
| DB 唯一索引 | `INSERT` 唯一键，释放即删除 | 无需新组件，强一致 | 性能低、需处理死锁与超时 |
| ZooKeeper | 临时顺序节点 | 强一致、无超时问题 | 性能低、运维重 |

```java
// Redisson 用法：看门狗默认每 10s 续期，锁默认 30s 过期，避免业务未完成锁就失效
RLock lock = redissonClient.getLock("lock:order:" + orderId);
boolean acquired = lock.tryLock(5, 30, TimeUnit.SECONDS);   // 最多等 5s，30s 后自动释放
if (!acquired) {
    return Response.busy("操作过于频繁");
}
try {
    return doBusiness(orderId);      // 阻塞式锁：务必确保业务耗时可控且可中断
} finally {
    lock.unlock();                   // 只能释放自己持有的锁（Redisson 内部校验线程 ID）
}
```

避坑清单：

1. **必须设置过期时间**——否则持锁进程崩溃后锁永不释放（死锁）。
2. **释放时校验持有者**——否则可能误删别人的锁（A 超时后 B 加锁，A 恢复后删掉 B 的锁）。
3. **不要依赖 Redis 主从切换的强一致**——主节点宕机且未同步到从节点时会丢失锁，金融级场景用 DB/ZK。
4. `tryLock` 优于 `lock()`——无界等待会把线程池占满。

## 八、实战：秒杀系统的分层拦截

秒杀是高并发的极端形态，核心思路是**层层拦截，让最终到达 DB 的请求只占极小比例**。

```text
CDN / 静态化       拦截 90%  —— 页面静态资源、活动页 HTML 全部走 CDN，动态数据用 Ajax 拉取
   ↓
网关层限流         拦截大部分机器流量与重复请求 —— 令牌桶 + 用户维度频率限制 + 验证码/风控
   ↓
服务层校验         活动时间、用户资格、是否已购（Redis Set）
   ↓
Redis 原子扣库存   Lua 脚本保证不超卖，扣减成功才继续
   ↓
MQ 异步下单        削峰，消费者按 DB 承载速率匀速落库
   ↓
DB 最终落库        唯一索引保证一人一单，乐观锁兜底
```

配套的六个关键点：

1. **动静分离**：商品详情页的静态部分（描述、图片）CDN 缓存，只有库存/价格走动态接口。
2. **按钮防重复**：前端点击后置灰 + 后端 Redis Set 判重，双重保障。
3. **库存分段**：把 `stock:1001` 拆成 `stock:1001:0..9` 十个子 key，扣减时路由到随机子 key，
   把单 key 热点的争抢分散到 10 个 key（Redis Cluster 下还能分散到不同分片）。
4. **隐藏下单接口**：秒杀开始前前端拿不到真实下单 URL，防止脚本提前刷。
5. **独立部署**：秒杀服务与数据库独立资源池，避免拖垮主站。
6. **对账与回滚**：异步下单失败需回补 Redis 库存，定时任务做库存对账。

## 九、压测与容量规划

没有压测的高并发改造都是猜测。推荐流程：

1. **基准压测**：单接口、单机，摸清当前基线（QPS、P99、CPU、GC）。
2. **容量压测**：逐步加压直到 RT 明显恶化或错误率上升，拐点即单机容量。
3. **稳定性压测**：以容量的 70% 持续运行 12~24h，观察内存泄漏、连接泄漏、磁盘增长。
4. **破坏性测试**：注入故障（Redis 宕机、下游超时、网络分区），验证熔断降级是否生效。

关注指标优先级：**错误率 > P99 RT > QPS > CPU**。只盯 QPS 会掩盖长尾恶化。

JVM 侧要点（高并发下 GC 是主要抖动源）：

- 堆大小固定：`-Xms` = `-Xmx`，避免运行时扩容引发 STW。
- 低延迟选 **G1**（`-XX:MaxGCPauseMillis=100`），JDK 17+ 超低延迟可评估 **ZGC**。
- 关注 `Young GC` 频率与对象晋升速率，高并发下大量临时对象会推高 YGC 次数。

## 十、排查工具箱

| 问题现象 | 工具 | 关键命令/用法 |
|---------|------|--------------|
| CPU 飙高 | arthas | `thread -n 3`（最忙线程）、`profiler start`（火焰图） |
| 线程阻塞/死锁 | jstack / arthas | `jstack -l <pid>`、`thread -b`（找出阻塞其他线程的那个） |
| 内存泄漏 | jmap + MAT | `jmap -histo:live <pid>`，对比两次堆转储 |
| GC 频繁 | jstat / GC 日志 | `jstat -gcutil <pid> 1000` |
| 慢 SQL | 数据库慢日志 + `EXPLAIN` | 关注 type=ALL、rows 巨大、filesort |
| 接口 RT 分布 | Micrometer + Prometheus | 打点 P50/P95/P99，不要只看平均 |

## 十一、常见故障与排错

| 现象 | 常见原因 | 排查与解决 |
|------|---------|-----------|
| 接口 RT 突增，CPU 不高 | 线程被阻塞在外部 IO（DB/HTTP） | `jstack` 看线程栈聚集在 `SocketInputStream.read`；加超时、扩容连接池 |
| 线程池 `RejectedExecutionException` | 队列/最大线程数过小或下游变慢 | 看拒绝策略是否合理；先治下游慢调用，再调参数 |
| 数据库连接池耗尽 | 慢 SQL / 大事务 / 连接未归还 | 查慢日志；确认 `try-with-resources` 或事务边界正确 |
| Redis 变慢 | Big Key、热 Key、`KEYS *`、内存逐出 | 禁用 `KEYS`；`SLOWLOG GET`；拆分 Big Key |
| 超卖 | 非原子扣减 / 事务隔离级别不足 | 改用 Lua 原子扣减；DB 加乐观锁或 `FOR UPDATE` |
| 雪崩 | 无降级 + 重试风暴 | 加熔断降级；重试只在最外层 + 指数退避 |
| 缓存与 DB 不一致 | 先删缓存后更 DB | 改为先更 DB 再删缓存；必要时延迟双删 |
| 虚拟线程下吞吐没提升 | `synchronized` 钉住载体线程 / CPU 密集任务 | 换 `ReentrantLock` 或升级 JDK 24；CPU 密集不用虚拟线程 |

## 十二、落地检查清单

上线前逐项确认：

- [ ] 每个接口都有**超时**与**降级**兜底，无裸调用
- [ ] 线程池使用**有界队列**且命名可辨识，拒绝策略明确
- [ ] 所有写接口**幂等**（唯一索引 / 状态机 / Token）
- [ ] 缓存有 TTL **随机抖动**，热点 key 有击穿防护
- [ ] 下游依赖有**限流 + 熔断 + 隔离**
- [ ] 压测报告覆盖容量拐点与稳定性时长
- [ ] 慢 SQL 已治理，核心查询有 `EXPLAIN` 佐证
- [ ] 核心链路有 P99 监控与告警

## 与相关概念的关系

- 与 [[java-thread-pool|Java 线程池]]：线程池是单机并发的执行载体，参数配置直接决定单机吞吐上限。
- 与 [[java-concurrency|Java 并发编程]]：`CompletableFuture` 是请求内并行编排、缩短 RT 的主要手段。
- 与 [[java-multithreading|Java 多线程基础]]：锁、CAS、内存模型是理解并发安全与性能瓶颈的前提。
- 与 [[project-reactor|Project Reactor]]：响应式编程是另一条高并发路线（非阻塞 IO），可与 [[spring-webflux|Spring WebFlux]] 配合。
- 与 [[redis|Redis]]：缓存与分布式锁的落地组件。
- 与 [[mysql|MySQL]]：最终落库的性能天花板，索引与事务设计决定写能力。
- 与 [[spring-cloud|Spring Cloud]]：微服务治理（限流、熔断、网关）通常在此层实现。

## 参考

- [Java 并发编程实战（Brian Goetz）](https://jcip.net/)
- [JDK 21 Virtual Threads（JEP 444）](https://openjdk.org/jeps/444)
- [JDK 24 Synchronize Virtual Threads without Pinning（JEP 491）](https://openjdk.org/jeps/491)
- [HikariCP 连接池大小调优](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)
- [Redisson 分布式锁文档](https://github.com/redisson/redisson/wiki/8.-Distributed-locks-and-synchronizers)
- [Resilience4j 官方文档](https://resilience4j.readme.io/docs)
- [[java-thread-pool|Java 线程池]]
- [[redis|Redis]]
