---
title: Reactor 起源与演进
description: 从 Rx 谱系到 Reactive Streams 规范，再到 Reactor 1/2/3 与 Spring WebFlux 的采纳，以及版本线与虚拟线程时代的定位
tags:
  - java
  - reactor
  - reactive
  - history
date: 2026-11-13
aliases:
  - reactor-history
  - reactive-streams
---

# Reactor 起源与演进

## 概述

Reactor 不是凭空设计出来的框架，而是**一次长达十年的收敛结果**：微软的 Rx 证明了"事件流可以用组合子描述"，
Netflix 在网关的实战里证明了"没有背压会死"，几家公司于是把背压写进一份四接口的规范，Reactor 则是这份规范在
Spring 生态里的实现。理解这条来路，才能理解今天 API 为什么长这样、为什么 `Processor` 会被废弃。

## 前置知识

- [[01-concepts|核心概念]]：先知道 `Publisher`/`Subscriber`/`Subscription` 是什么
- 观察者模式与回调地狱
- Servlet 线程模型与 C10K 问题

## 一、前史：从观察者模式到 Rx

### 观察者模式的三个缺口

GoF 的观察者模式（`addListener` / `onEvent`）能解耦，但解决不了三件事：

1. **组合**：想"过滤 + 变换 + 合并两个事件源"，只能手写状态机。
2. **完成与错误**：事件流什么时候结束？出错了怎么通知？接口里没有位置放。
3. **流速**：生产者不管消费者死活，快生产者直接把消费者压垮。

### Rx：把事件流做成"可组合的集合"

2009 年微软在 .NET 上发布 **Reactive Extensions（Rx.NET）**，核心洞察是：
**把"随时间到达的事件"当成"集合"来操作**——`List` 有 `filter`/`map`，事件流也应该有。
为此它引入了两个终止信号（`OnCompleted`/`OnError`），并给出 `IObservable<T>`/`IObserver<T>` 一对接口。

2013 年 Netflix 把 Rx 移植到 JVM，即 **RxJava**。它被用在 API 网关里：一个页面请求要扇出调用几十个后端服务，
如果用阻塞线程，网关的连接数和线程数会被同时打满。RxJava 的异步组合能力救了这一层，但也暴露了新问题——
**RxJava 1.x 没有标准化的背压接口**，各家实现的 `request` 语义不一致。

## 二、规范的诞生：Reactive Streams（2013-2015）

### 谁在做

2013 年起，Netflix（RxJava）、Pivotal（Reactor）、Typesafe/Lightbend（Akka）三家坐到一起，
目标是**只定义接口，不定义实现**，让不同库之间可以互操作。这就是 Reactive Streams 倡议。

### 规范内容

四个接口，一份 TCK（技术兼容性测试套件），加上一套对信号顺序、背压、取消的严格规则：

| 版本 | 时间 | 意义 |
|------|------|------|
| 1.0.0 | 2015 年 5 月 | 规范正式发布，JVM 绑定定型 |
| 1.0.3 | 2019 年 | 错误处理与规则澄清 |
| 1.0.4 | 2022 年 | 最后一个广泛使用的版本 |

关键决定是**把背压写进接口本身**：`Subscription.request(long n)` 不是可选优化，而是协议的一部分。
这条决定直接区分了"响应式流"与"异步回调"——后者只是换个方式阻塞，前者才真正控制流速。

### 规范化的连锁反应

```text
2015  Reactive Streams 1.0.0
        │
        ├─> 2016  Reactor 3 重写，完全基于规范
        ├─> 2017  JDK 9 吸收为 java.util.concurrent.Flow（JEP 266）
        └─> 2017  Spring Framework 5 选择 Reactor 作为 WebFlux 的底层
```

JDK 9 的 `Flow` 四个接口（`Publisher`/`Subscriber`/`Subscription`/`Processor`）与 Reactive Streams
一一对应，只是包名不同。这意味着"响应式流"不再是第三方库的方言，而是 JDK 的一部分；
也意味着 Reactor 的 `Flux` 与新 API 之间需要适配层（`FlowAdapters`），但两者语义一致。

## 三、Reactor 自己的三代

| 代际 | 时间 | 定位 | 结局 |
|------|------|------|------|
| Reactor 1.x | 2013-2014 | Pivotal 出品的事件驱动框架，核心是 `Reactor`/`Stream`，理念接近 Node.js 的事件循环 | 设计不再延续 |
| Reactor 2.x | 2014-2016 | 引入 `Stream`/`Promise`，部分吸收 Reactive Streams | 被 3.x 取代，停止维护 |
| Reactor 3.x | 2016 至今 | 完全基于 Reactive Streams 重写，对外只暴露 `Flux`/`Mono` | 现役 |

**为什么 2.x 必须推倒重来**：2.x 是在"规范还没定型"的时期长出来的，`Stream` 与 `Promise` 两套抽象并存，
背压语义与规范不一致，也背上了大量历史 API。3.x 的选择是极简——只留两个类型（`Flux`=0..N，`Mono`=0..1），
所有能力通过操作符表达。这个"两个类型 + 一堆操作符"的形态，此后十年没变过，也是它能稳定演进的原因。

### Reactor 3 之后的关键节点

| 版本 | 时间（约） | 关键变化 |
|------|-----------|----------|
| 3.0 | 2016 | `Flux`/`Mono` 定型；被 Spring 5 选定为 WebFlux 基础 |
| 3.1 | 2017 | 引入 `Context`；`Schedulers` 体系完善 |
| 3.2 | 2018 | 调试能力（`checkpoint`、`Hooks.onOperatorDebug`）、`Retry` 重写 |
| 3.3 | 2019 | `flatMapSequential` 等操作符成熟；`reactor-pool` 起步 |
| 3.4 | 2021 | **引入 `Sinks` 门面**，开始替代 `Processor`；基线仍为 Java 8 |
| 3.5 | 2022 | `FluxProcessor` 全系标记 `@Deprecated`；性能与内存优化 |
| 3.6 | 2022 末 | **基线升到 Java 17**，对齐 Spring Framework 6 / Boot 3 |
| 3.7 | 2023 末 | 对齐 Boot 3.2；JDK 21 适配、Micrometer 观测整合 |
| 3.8 | 2025 | 对齐 Spring Framework 7 / Boot 4；`reactor-core` 3.8.x 为当前主线 |

Reactor 从 2020 年起改用**日历版本号命名发布列车（release train）**，核心构件版本与列车名分离：

| 发布列车 | `reactor-core` | 配套 Spring Boot |
|----------|----------------|------------------|
| 2020.0 | 3.4.x | Boot 2.4 – 2.5 |
| 2022.0 | 3.5.x | Boot 3.0 – 3.1 |
| 2023.0 | 3.6.x | Boot 3.2 – 3.3 |
| 2024.0 | 3.7.x | Boot 3.4 – 3.5 |
| 2025.0 | 3.8.x | Boot 4.0 – 4.1 |

实际项目里**不要手写 `reactor-core` 版本**，让 Spring Boot BOM 决定；需要覆盖时统一在
`dependencyManagement` 里钉版本，避免出现 `NoSuchMethodError` 落在 reactor 内部类这种难查的故障。

## 四、与其他实现的对比

| 实现 | 规范符合 | 多平台 | 特点 | 现状 |
|------|----------|--------|------|------|
| **Reactor 3** | 是 | JVM | 与 Spring 生态深度绑定，操作符覆盖最全，`Sinks` 设计清晰 | 主流，活跃 |
| RxJava 2/3 | 是 | JVM | 操作符最多，`Observable` 家族更庞杂（含不支持背压的 `Observable`） | 活跃，Android 生态偏多 |
| Akka Streams | 是（GraphStage） | JVM/Scala | 图式流处理，适合复杂拓扑 | 活跃，Scala 优先 |
| JDK `Flow` | 是（接口级） | JDK 9+ | 只有接口，无操作符 | 作为规范基座存在 |
| Kotlin Flow / Coroutines | 否（互操作） | JVM/Native | 挂起函数风格，写法更接近同步代码 | 活跃 |

选型结论：**在 Spring 技术栈里用 Reactor 是默认答案**（WebFlux、Gateway、R2DBC 都基于它），
在纯 JVM 库或 Android 里 RxJava 仍有存量优势。

## 五、虚拟线程之后：定位变了，但没有消失

JDK 21 转正虚拟线程，Spring Boot 3.2 起一行配置 `spring.threads.virtual.enabled=true` 就能让阻塞式 MVC
获得接近响应式的吞吐。这条变化让"为了高并发而上 Reactor"的理由不再充分，但它没有覆盖 Reactor 的另外三项能力：

| 场景 | 虚拟线程是否够用 | 结论 |
|------|------------------|------|
| 高并发 CRUD（JDBC/同步 SDK） | 够用，且代码更简单 | 用 MVC + 虚拟线程 |
| 流式输出（SSE、日志尾随、LLM token） | 勉强（需手写循环与背压） | 用 `Flux`，天然分块与取消 |
| 多下游扇出编排（`zip`/`flatMap`/超时/降级） | 需要手写 `StructuredTaskScope` | `Mono.zip` 更省事 |
| 生产快于消费的实时数据 | 无内建机制 | 背压操作符不可替代 |
| 网关、代理类纯 I/O 转发 | 可以，但线程仍占资源 | WebFlux + Reactor Netty 仍是主流 |

一句话总结：**虚拟线程接管了"高并发"，Reactor 退回到"流式 + 编排 + 背压"**。这也意味着新项目不该
"为了响应式而响应式"——把阻塞代码硬塞进 `Flux` 只是给线程模型换了层皮，成本更高。取舍清单见
[[07-applications#虚拟线程时代还要不要 Reactor|虚拟线程时代还要不要 Reactor]]。

## 常见误区

| 误区 | 实际情况 |
|------|----------|
| "Reactor 就是 RxJava 换皮" | 同源不同代：Rx 是 2009 年的 .NET 设计，Reactor 3 是按 2015 年规范重写的 |
| "响应式就是异步" | 响应式的核心是背压与组合；异步只是必要手段。同步的 `Flux.just(1,2,3)` 也完全合法 |
| "Reactor 5 会有大改" | 主线一直是 3.x；演进方式是发布列车 + 基线 JDK 提升，而非大版本重写 |
| "`Processor` 是 Reactor 的核心组件" | 它是规范里的角色，但在 Reactor 里已被 `Sinks` 取代，新代码不应使用 |
| "用了 WebFlux 就自动高并发" | 链路上任意一处阻塞（JDBC、`Thread.sleep`、同步 SDK）都会抵消收益 |

## 与相关概念的关系

- [[01-concepts|核心概念]]：本篇解释了那些概念"为什么是那样"。
- [[05-processor|Processor 组件]]：规范留给"中间人"的位置，以及它在 Reactor 中的退场。
- [[04-sink|Sink 组件]]：3.4 之后接替 `Processor` 的统一推流入口。
- [[spring-webflux|Spring WebFlux]]：Reactor 最大的消费方，也是它进入主流的原因。
- [[07-applications|应用场景]]：规范落地到具体框架的位置清单。

## 参考

- [Reactive Streams 官网与规范](https://www.reactive-streams.org/)
- [JEP 266: More Concurrency Updates（`java.util.concurrent.Flow`）](https://openjdk.org/jeps/266)
- [Reactor 官方文档：History / Release Notes](https://projectreactor.io/docs/core/release/reference/)
- [Spring Boot 版本与 Java 兼容矩阵](https://endoflife.date/spring-boot)
