---
title: Reactor 核心概念
description: 响应式流规范四件套、背压机制、Flux 与 Mono、冷热流、Scheduler 线程模型与 Context
tags:
  - java
  - reactor
  - reactive
  - concurrency
date: 2026-11-13
aliases:
  - reactor-concepts
---

# Reactor 核心概念

## 概述

Reactor 把"异步数据流"抽象成**一条可以被描述、组合、订阅的流水线**。要读懂这条流水线，只需要掌握五组概念：
规范的四个接口、背压、`Flux`/`Mono` 两种容器、冷热流与惰性、以及线程（`Scheduler`）与上下文（`Context`）。

本篇是后续所有篇目的地基。[[03-usage|使用指南]] 里的每个操作符，本质上都只是在操作这几组概念。

## 前置知识

- Lambda 表达式与函数式接口（`Function`、`Consumer`、`Supplier`、`Predicate`）
- `CompletableFuture` 的异步回调模型，以及它为什么处理不了"多个值 + 背压"
- 线程池与阻塞 I/O 的成本模型

## 一、为什么需要响应式

### 阻塞模型的成本上限

Servlet 容器（Tomcat）用"一请求一线程"承接流量。一个线程在等待下游 HTTP/DB 响应时**完全占用栈内存与调度名额**，
无法做别的事。于是单机的并发上限被钉死在一个简单不等式上：

```text
最大并发 ≈ 线程池大小 = f(可用内存, 每线程栈, 上下文切换成本)
```

想让并发上一个数量级，只能加内存、加机器。而事实上这段时间 CPU 什么都没做——只是"等"。

### Reactor 的答案

用少量固定线程 + 事件驱动，把"等"变成"注册回调后让出线程"：

| 维度 | 阻塞模型（Servlet + RestTemplate） | 响应式模型（WebFlux + WebClient） |
|------|-----------------------------------|-----------------------------------|
| 线程数 | 每请求一线程，数百到数千 | 固定少量（CPU 核数量级） |
| 线程在等 I/O 时 | 阻塞挂起，占住资源 | 释放，去处理别的连接 |
| 数据量控制 | 无（下游慢就堆积/超时） | 背压：按需拉取 |
| 错误与超时 | try/catch + 客户端超时配置 | 流内操作符统一表达（`timeout`/`retry`/`onErrorResume`） |
| 组合多个异步结果 | 回调嵌套或 `CompletableFuture` 拼装 | `zip`/`merge`/`flatMap` 声明式组合 |
| 调试成本 | 低（同步栈） | 高（异步栈、需要 checkpoint） |

代价要说清楚：**响应式不是免费的**。它换来并发能力，付出的是心智负担——一旦链路中有一环是阻塞的，
整条链的收益立刻归零（见 [[07-applications#生产实践|生产实践]] 里的 BlockHound 检测）。

## 二、响应式流规范：四个接口

Reactive Streams 是一个**只有四个接口**的规范（`org.reactivestreams`），Reactor 是它的实现之一。
理解这四个接口的职责划分，比背任何操作符都重要。

| 接口               | 角色  | 关键方法                                                | 职责                                            |
| ---------------- | --- | --------------------------------------------------- | --------------------------------------------- |
| `Publisher<T>`   | 数据源 | `subscribe(Subscriber)`                             | 接受订阅，按需生产                                     |
| `Subscriber<T>`  | 消费者 | `onSubscribe` / `onNext` / `onError` / `onComplete` | 声明需求、处理数据与终止信号                                |
| `Subscription`   | 契约  | `request(long n)` / `cancel()`                      | 把"我要 n 个"传给上游，支持取消                            |
| `Processor<T,R>` | 中间人 | 同时继承上面两个接口                                          | 既是订阅者又是发布者（详见 [[05-processor\|Processor 组件]]） |

一次完整的交互严格遵循这个顺序：

```text
Subscriber                Publisher              Subscription
    │  subscribe()  ────────> │
    │ <──── onSubscribe(s) ───┤
    │  s.request(10) ─────────┼──────────────> │   （声明需求：最多给我 10 个）
    │ <──── onNext(a) ────────┤ <──────────────│
    │ <──── onNext(b) ────────┤                │
    │  s.request(5) ──────────┼──────────────> │   （消费完再要，动态调节）
    │ <──── onComplete() ─────┤                │   （或 onError(t)，二者只出现一次）
```

三条容易忽略的规则，违反了就是 bug：

1. **`onSubscribe` 必须先于任何 `onNext`**，且只调用一次。
2. **`onComplete` 与 `onError` 是终止信号**，出现后不能再有任何信号（`onNext`、`request` 都失效）。
3. **`request(n)` 的 `n` 必须为正**；`request(Long.MAX_VALUE)` 表示"取消背压，全速发"。

## 三、背压：Reactor 的核心卖点

背压（Backpressure）解决的是**生产快于消费**。没有它，快生产者只会做两件事之一：撑爆内存，或者丢数据。

### 拉模型

Reactor 采用**拉模型（request-driven）**：需求由消费者声明，生产者不得超发。这跟 `Iterator` 的
"`hasNext()` + `next()`"是同一种哲学——差别在于响应式的 `request(n)` 是异步批量声明，且可以随时追加。

### 上游不支持背压怎么办

现实里很多数据源（消息队列、WebSocket、`Sinks` 的某些模式）天生不支持背压。Reactor 提供四种显式策略，
**必须选一个，不能装作没发生**：

| 操作符 | 行为 | 适用场景 | 风险 |
|--------|------|----------|------|
| `onBackpressureBuffer()` | 无界队列缓存 | 下游只是短暂变慢 | OOM |
| `onBackpressureBuffer(1000)` | 有界队列，溢出报错 | 大多数生产场景 | 溢出时 `OverflowException` |
| `onBackpressureDrop()` | 溢出即丢 | 指标采样、日志 | 静默丢数据 |
| `onBackpressureLatest()` | 只保留最新一个 | 实时行情、UI 刷新 | 中间值丢失 |

消费侧的另一个旋钮是 `limitRate(n)`：把上游的大请求拆成小批（默认 prefetch 256，`limitRate` 常用 32/64），
避免一次拉太多堆在内存里。

### prefetch 与 request 的关系

看到 `flatMap(f, 8)` 或 `publishOn(scheduler, 32)` 时，第二个参数是 **prefetch**：每个内部流预先请求多少。
prefetch 越大吞吐越好、内存越高；这是 Reactor 里最常被忽略的性能参数。

## 四、Flux 与 Mono

| 类型 | 元素个数 | 典型来源 | 典型用途 |
|------|----------|----------|----------|
| `Flux<T>` | 0..N | 查询列表、消息流、文件行、SSE | 多值流 |
| `Mono<T>` | 0..1 | 单条查询、一次 HTTP 调用、`save()` | 单值/空/错误 |

选择原则：**能用 `Mono` 就不要用 `Flux`**。`Mono` 表达"最多一个结果"，语义更准确，也让调用方明确知道
不需要遍历；同时 `Mono` 在空值处理（`switchIfEmpty`、`defaultIfEmpty`）上有更清晰的语义。

两者可以互转：

```java
Flux<String> many = Mono.just("a").flatMapMany(one -> Flux.just(one, one + one));
Mono<List<String>> one = Flux.just("a", "b").collectList();
Mono<Long> count = Flux.just("a", "b").count();
Flux<String> never = Mono.<String>empty().flux();   // 0 个元素
```

## 五、惰性与"两个阶段"

Reactor 的流水线在**装配阶段（assembly time）**只是构建一条操作符链，**不执行任何逻辑**；
直到**订阅阶段（subscription time）**才真正开始跑。这条规则解释了绝大多数"为什么没生效""为什么执行了两次"。

```java
// 装配：没有任何输出，也没有任何副作用
Flux<String> pipeline = Flux.just("a", "b")
        .map(v -> { System.out.println("map " + v); return v; });

System.out.println("装配完成");     // 先打印这句

pipeline.subscribe();               // 此刻才打印 map a / map b
pipeline.subscribe();               // 再来一遍：整条链重新执行
```

由此推出一条实践规则：**需要"每次订阅重新取值/重新执行"时，用 `defer` 包一层**。

```java
// 错误：时间戳在装配时固定，两次订阅拿到同一个值
Mono<Long> frozen = Mono.just(System.currentTimeMillis());

// 正确：每次订阅都重新取
Mono<Long> fresh = Mono.defer(() -> Mono.just(System.currentTimeMillis()));
```

`defer` 与 `fromCallable` 的区别：前者延迟**整个流的构建**（可以返回 `Mono.empty()` 或 `Mono.error()`），
后者延迟**一个值的计算**（异常自动转成 `onError`）。需要条件分支用 `defer`，只是延迟计算用 `fromCallable`。

## 六、冷流、热流与 ConnectableFlux

| 类型 | 数据何时产生 | 多订阅者行为 | Reactor 中的来源 |
|------|--------------|--------------|------------------|
| 冷流（cold） | 每个订阅者订阅时独立开始 | 各订阅者各自完整收到一份 | `Flux.just`、`fromIterable`、`WebClient` 调用 |
| 热流（hot） | 与订阅者无关，持续产生 | 后订阅者只收到订阅之后的元素 | `Sinks.many().multicast()`、`ConnectableFlux`、消息队列 |
| 可连接流 | 手动/达到阈值才开始 | 共享同一个上游订阅 | `publish()`、`replay()`、`share()`、`cache()` |

`ConnectableFlux` 是"把冷流转成热流"的工具，四个关键方法语义差异很大：

| 方法 | 何时连接上游 | 上游取消时机 | 备注 |
|------|--------------|--------------|------|
| `publish()` | 需 `connect()` | 无人订阅仍连接 | 配合 `autoConnect(n)` 延迟到 n 个订阅者 |
| `replay(n)` | 需 `connect()` | 同上 | 向新订阅者重放最近 n 个 |
| `share()` | 第一个订阅者到达 | 所有订阅者取消后上游取消 | 多用于"多个下游共享一次昂贵调用" |
| `cache()` | 第一个订阅者到达 | 永不 | 结果永久缓存，适合不变数据 |

一个经典陷阱：对冷流调用两次 `subscribe()`，下游会被调用两次（比如查两次库）。这不是 bug，是冷流语义。
需要共享就用 `cache()`/`share()`，或者在上游用 `Sinks` 做一次广播（见 [[04-sink|Sink 组件]]）。

## 七、Scheduler：线程在哪里

`Scheduler` 是 Reactor 的线程池抽象。**默认情况下，操作符在调用 `subscribe()` 的那个线程上同步执行**——
Reactor 不会自动帮你切线程。不显式切换，整条链就是单线程的。

| Scheduler | 线程数 | 阻塞是否允许 | 用途 |
|-----------|--------|--------------|------|
| `Schedulers.immediate()` | 当前线程 | — | 测试、调试 |
| `Schedulers.single()` | 1 | 不建议 | 需要严格串行的任务 |
| `Schedulers.parallel()` | CPU 核数 | **禁止** | 纯 CPU 计算 |
| `Schedulers.boundedElastic()` | 10 × 核数（上限），队列 10 万 | 允许 | 包装阻塞 I/O（JDBC、老 SDK） |
| `Schedulers.fromExecutorService(es)` | 自定义 | 看情况 | 接入既有线程池 |

两个切换操作符方向完全相反，这是最常见的混淆点：

```text
subscribeOn：作用于"订阅动作"以及其上游的 request 传播 —— 决定数据源在哪个线程生产
publishOn  ：作用于其下游的所有操作符 —— 决定数据在哪个线程被消费（可多次出现，形成接力）

Flux.just(1, 2, 3)
    .subscribeOn(Schedulers.boundedElastic())   // 上游（含订阅）跑在 elastic 线程
    .map(this::parse)                            // 仍在 elastic
    .publishOn(Schedulers.parallel())            // 从这里往下切到 parallel
    .map(this::compute)                          // 在 parallel
    .subscribe();
```

记住一句：**`subscribeOn` 只影响上游且只有最靠近源头的那个生效；`publishOn` 影响下游且可以多次使用。**

## 八、Context：跨操作符传递的不可变上下文

`ThreadLocal` 在响应式里失效——同一条流会在多个线程间跳。Reactor 用 `Context` 替代它：一个附着在订阅上的
不可变键值集合，**从下游向上游可见**。

```java
Mono.deferContextual(ctx -> {
            String traceId = ctx.get("traceId");   // 只在"更靠近订阅端"写入时才拿得到
            return Mono.just("handled by " + traceId);
        })
        .contextWrite(Context.of("traceId", "T-1001"))   // 写在链的末尾（靠近订阅端）
        .subscribe(System.out::println);
```

方向要点：`contextWrite` 写在**下游**，读取写在**上游**（`deferContextual`）。反向写会拿到空值，是高频错误。

## 九、常见误区

| 误区 | 实际情况 | 纠正 |
|------|----------|------|
| "声明了就会执行" | 惰性，无订阅不执行 | 末端必须有 `subscribe()`，或返回给框架由框架订阅 |
| "`map` 能放阻塞调用" | 会占住事件循环线程，拖垮整机 | 阻塞逻辑放 `boundedElastic`，或改用响应式客户端 |
| "`flatMap` 保证顺序" | 并发执行，完成顺序不定 | 需要顺序用 `concatMap`；要并发又要保序用 `flatMapSequential` |
| "`subscribe` 里再 `subscribe`" | 拆断了背压与错误传播链 | 用 `flatMap`/`then` 组合，只在末端订阅一次 |
| "`Schedulers.parallel()` 能给阻塞任务加速" | 线程数只有核数，阻塞会饿死 | 阻塞用 `boundedElastic` |
| "`Mono.just(null)` 表示空" | 直接抛 `NullPointerException` | 用 `Mono.empty()` 或 `Mono.justOrEmpty(x)` |
| "`retry` 会重新建立整条链" | 只重新订阅上游，装配阶段不会重跑 | 需要重跑装配逻辑用 `defer` + `retry` |

## 与相关概念的关系

- 与 `CompletableFuture` 的区别：`CompletableFuture` 描述"一个将来会有的值"，没有背压、没有多值、组合靠回调；
  `Flux` 描述"一串值随时间到达"，支持背压与取消。见 [[java-concurrency|Java 并发编程（CompletableFuture）]]。
- 与 Java `Stream` 的区别：`Stream` 是拉取式、一次性、同步、无时间维度；`Flux` 可重复订阅、可异步、可带时间语义
  （`interval`、`timeout`、`bufferTimeout`）。
- 与 [[05-processor|Processor]] 的关系：`Processor` 就是同时实现 `Publisher` 与 `Subscriber` 的组件，
  是规范里唯一的"中间人"角色，现已由 `Sinks` 取代。
- 与虚拟线程的关系：JDK 21 的虚拟线程让"阻塞代码也能高并发"，削弱了响应式在**吞吐**上的独占优势，
  但背压、流式组合、取消传播仍是 Reactor 的独有能力。取舍见 [[07-applications#虚拟线程时代还要不要 Reactor|虚拟线程时代还要不要 Reactor]]。

## 参考

- [Reactive Streams 规范与 TCK](https://github.com/reactive-streams/reactive-streams-jvm)
- [Reactor 参考文档：Core Concepts](https://projectreactor.io/docs/core/release/reference/#core-concepts)
- [[02-origin|起源与演进]]：这些概念是怎么一步步长出来的
