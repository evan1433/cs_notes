---
title: Project Reactor 专题
description: Project Reactor 全景导读：概念、来源、使用、应用、代码案例，以及 Sink 与 Processor 组件
tags:
  - java
  - reactor
  - reactive
  - spring
  - webflux
date: 2026-11-13
aliases:
  - reactor-topic
  - 响应式编程
---

# Project Reactor 专题

Reactor 是 JVM 上的响应式流（Reactive Streams）实现，是 Spring WebFlux、Spring Cloud Gateway、Reactor Netty、R2DBC
这一整条非阻塞技术栈的底座。它的价值不在"多一个集合工具类"，而在于**用一条声明式的流水线，把异步、并发、背压、
超时与容错统一表达**——写的是数据如何流动，而不是线程如何调度。

本专题拆成 7 篇，按"是什么 → 从哪来 → 怎么用 → 两类组件 → 实战 → 落地"组织。旧的单文件笔记
[[project-reactor|Project Reactor（旧笔记）]] 内容仍然保留，可与本专题对照阅读。

## 专题地图

| 篇目 | 回答的问题 | 关键内容 |
|------|-----------|----------|
| [[01-concepts\|核心概念]] | Reactor 到底在抽象什么？ | 响应式流四件套、背压、Flux/Mono、冷热流、Scheduler、Context |
| [[02-origin\|起源与演进]] | 为什么会有它？现在处于什么位置？ | Rx 谱系、Reactive Streams 规范、Reactor 1/2/3、版本线、虚拟线程冲击 |
| [[03-usage\|使用指南]] | 日常怎么写、怎么调、怎么测？ | 创建/转换/组合/容错操作符、线程切换、调试、StepVerifier |
| [[04-sink\|Sink 组件]] | 怎么从外部"推进来"数据？ | `Sinks.many/one/empty`、unicast/multicast/replay、`EmitResult` |
| [[05-processor\|Processor 组件]] | 老代码里的 Processor 是什么？还能用吗？ | `FluxProcessor` 家族、废弃原因、迁移对照 |
| [[06-code-examples\|代码案例]] | 完整可运行的例子长什么样？ | 阻塞桥接、并发聚合、顺序控制、批处理、SSE、LLM 流式输出 |
| [[07-applications\|应用场景]] | 在真实系统里它出现在哪？ | WebFlux、Gateway、R2DBC、RSocket、流式 AI、生产实践 |

## 三条阅读路径

**入门（约 60 分钟）**：[[01-concepts|核心概念]] → [[03-usage|使用指南]] 的"三个约定"与"创建/转换"两节 →
[[06-code-examples|代码案例]] 案例 1、2。

**实战（有 WebFlux 项目在身）**：[[03-usage|使用指南]] 全篇 → [[04-sink|Sink]] →
[[06-code-examples|代码案例]] 案例 5-8 → [[07-applications|应用场景]] 生产实践一节。

**读源码/接手遗留系统**：[[02-origin|起源与演进]] → [[05-processor|Processor]] →
[[01-concepts|核心概念]] 的"惰性"与"冷热流"两节。这两节是理解为什么"订阅了两次却查了两次库"的关键。

## 关键脉络速览

```text
Rx.NET (2009)
   └─> RxJava (2013, Netflix)              ┐
Reactor 1/2 (2013-2015, Pivotal)           ├─> Reactive Streams 规范 1.0.0 (2015)
Akka Streams (Typesafe)                    ┘        │
                                                    ├─> JDK 9 Flow (JEP 266, 2017)
                                                    └─> Reactor 3 (2016) ─> Spring WebFlux (2017)
                                                                              └─> 至今 3.8.x / Spring Boot 4
```

一句话记住四件事，后面所有内容都是它们的展开：

1. **没有订阅，什么都不会发生**（assembly 与 subscription 是两个阶段）。
2. **数据流是拉动的**：订阅者 `request(n)`，发布者最多发 `n` 个——这就是背压。
3. **`Flux` 是 0..N，`Mono` 是 0..1**，选错类型不会报错，但会让 API 语义失真。
4. **不要在流水线上 `block()`**，尤其在事件循环线程里。

## 前置知识

- Java 8 Lambda / 函数式接口 / `Stream`：见 [[java-se|Java SE 核心语法]]
- `CompletableFuture` 与线程池：见 [[java-concurrency|Java 并发编程（CompletableFuture）]]、[[java-thread-pool|Java 线程池]]
- HTTP 与 Servlet 线程模型：见 [[java-web|Java Web 开发]]
- 想在 Spring 语境里对照：见 [[spring-webflux|Spring WebFlux]]

## 参考

- [Reactor 官方参考文档](https://projectreactor.io/docs/core/release/reference/)
- [Reactor 3 中文参考指南](https://easywheelsoft.github.io/reactor-core-zh/index.html)
- [Reactive Streams 规范](https://www.reactive-streams.org/)
