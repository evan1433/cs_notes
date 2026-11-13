---
title: Reactor Processor 组件
description: 规范中的 Processor 双重角色、FluxProcessor 家族、被 Sinks 取代的原因与迁移对照
tags:
  - java
  - reactor
  - reactive
  - processor
date: 2026-11-13
aliases:
  - reactor-processor
  - fluxprocessor
---

# Reactor Processor 组件

## 概述

`Processor` 是响应式流规范里唯一的"中间人"角色：**同时实现 `Subscriber` 与 `Publisher`**，
一头接上游、一头接下游。它在 Reactor 3 的早期（3.0-3.4）是构造热流、做事件总线的主力，
但从 3.4 引入 `Sinks`、3.5 起全系标记 `@Deprecated` 之后，**新代码不应再使用**。

本篇讲三件事：它本来要解决什么问题、`FluxProcessor` 四个实现分别是什么语义、
以及为什么它被 `Sinks` 取代、老代码怎么平滑迁移。

## 前置知识

- [[01-concepts|核心概念]]：四个接口与冷热流
- [[04-sink|Sink 组件]]：接替它的现代 API（建议先读）

## 一、它在规范中的位置

```text
        Publisher<T>                Processor<T,R>                 Subscriber<R>
数据源 ──────────────>  [ Subscriber 侧 | Publisher 侧 ]  ──────────────> 下游
                        （收 onNext）      （发 onNext）
```

规范里 `Processor<T,R>` 的原意是"**带类型转换的中转**"：从 `T` 收，往 `R` 发。
但 Reactor 的实现全部是 `FluxIdentityProcessor<T>`（`T` 与 `R` 相同），也就是**只中转不转换**——
转换交给操作符做，这符合 Reactor "能力尽量落在操作符上"的设计取向。

正因为它同时是两个角色，它天然适合三种场景：

| 场景 | 说明 |
|------|------|
| 冷转热 | 把一条上游流变成可被多方独立订阅的热流 |
| 桥接外部事件 | 外部回调里 `onNext`，下游当流消费 |
| 中间缓冲 | 上下游速率不一致时插一层缓冲 |

## 二、FluxProcessor 家族

Reactor 3 提供四个具体实现，语义差异很大，混用就是事故来源：

| 实现 | 订阅者数 | 背压 | 缓冲 | 重放 | 无订阅者时 |
|------|----------|------|------|------|-----------|
| `DirectProcessor` | 多个 | **不支持**（慢订阅者拿 `OverflowException`） | 无 | 无 | 发出去就丢了 |
| `UnicastProcessor` | **仅 1 个** | 支持 | 有（无界/有界） | 无 | 缓冲 |
| `EmitterProcessor` | 多个 | 支持（按 buffer 大小） | 有 | 无 | 缓冲 |
| `ReplayProcessor` | 多个 | 支持 | 有 | **有**（全部/最近 n 个） | 缓冲 |

几个必须知道的细节：

- `DirectProcessor` 是"最热"的：谁在订阅时在线谁就能收到，晚到的收不到，慢的会直接报 `OverflowException`。
  它没有 `onError`/`onComplete` 之后的复用能力——终止即永久终止。
- `UnicastProcessor` 只能有一个订阅者，而且**它自己也 subscribes 到一个上游**时可以当作"带缓冲的管道"用，
  这是它在老项目里最常见的身影。
- `EmitterProcessor` 表面看最像"正确选择"，但它的背压行为被埋在 `create(int bufferSize)` 里，
  溢出了只会在下游看到 `IllegalStateException`，非常难排查。
- `ReplayProcessor.cacheLast()` 是"只保留最新一个值"的老写法，等价于 `Sinks.many().replay().latest()`。

## 三、为什么被废弃

不是因为"不好用"，而是因为**语义不可判定**：

| 问题 | 老 API 的表现 | `Sinks` 的解法 |
|------|---------------|----------------|
| 发射是否成功？ | `onNext()` 返回 `void`，失败了静默 | `tryEmitNext()` 返回 `EmitResult` |
| 并发发射怎么处理？ | 各实现规则不同，`DirectProcessor` 需外部串行化 | 统一返回 `FAIL_NON_SERIALIZED`，用 `EmitFailureHandler` 重试 |
| 背压策略在哪选？ | 藏在不同工厂方法的参数里 | 由 `unicast/multicast/replay` 三类显式表达 |
| 多订阅者时谁被丢？ | 无法预判 | `directBestEffort` / `directAllOrNothing` 明确到方法名 |
| Context 传播 | 中转层断开，`contextWrite` 传不过去 | 用 `Sinks` + 组合操作符，链路不断 |
| 与 `Flux.create`/`generate` 的关系 | 三套等价能力并存 | 收敛为 `Sinks` + 回调式 sink 两条清晰路径 |

一句话：**`Processor` 把"发射语义"和"背压语义"混在一个类型里，而两者都需要被显式选择**。
`Sinks` 的做法是把这两个维度拆成两层 API（`Sinks.Many` 选多播语义，`tryEmit*` 给出结果）。

## 四、迁移对照

官方给出的等价关系，可以直接照着替换：

| 旧写法（`@Deprecated`） | 新写法 |
|------------------------|--------|
| `DirectProcessor.create()` | `Sinks.many().multicast().directBestEffort()` |
| `EmitterProcessor.create()` | `Sinks.many().multicast().onBackpressureBuffer()` |
| `ReplayProcessor.create()` | `Sinks.many().replay().all()` |
| `ReplayProcessor.cacheLast()` | `Sinks.many().replay().latest()` |
| `UnicastProcessor.create()` | `Sinks.many().unicast().onBackpressureBuffer()` |
| `MonoProcessor`（已移除） | `Sinks.one()` |

### 迁移前后对照

```java
// ---------- 旧写法：Processor ----------
import reactor.core.publisher.DirectProcessor;
import reactor.core.publisher.FluxProcessor;

FluxProcessor<String, String> legacy = DirectProcessor.create();
legacy.subscribe(v -> System.out.println("[A] " + v));
legacy.onNext("order-created");          // 返回值是 void，成没成功不知道
legacy.onComplete();                      // 之后 onNext 静默无效

// ---------- 新写法：Sinks ----------
import reactor.core.publisher.Sinks;

Sinks.Many<String> modern = Sinks.many().multicast().directBestEffort();
modern.asFlux().subscribe(v -> System.out.println("[A] " + v));
System.out.println(modern.tryEmitNext("order-created"));   // OK
System.out.println(modern.tryEmitComplete());               // OK
System.out.println(modern.tryEmitNext("late"));             // FAIL_TERMINATED（可判定）
```

迁移时最容易漏的一点：旧代码里 `processor.onNext(x)` 之后没有任何判断，替换成 `tryEmitNext` 后
**必须处理失败分支**，否则等于把静默失败换成了显式忽略——收益为零。

## 五、还需要 Processor 吗

两种情况下它仍然会出现在你的视野里：

**1. 读遗留代码。** 见到 `UnicastProcessor` 不要慌，按语义翻译成 `Sinks.many().unicast()...`；
见到 `DirectProcessor` 就要警惕——它意味着"慢订阅者会挂，且没有背压"，这在高负载下是隐患。

**2. 需要真正类型转换的中转。** 规范允许 `Processor<T,R>`，但 `FluxProcessor` 不做转换。
如果确实需要 `T → R` 的中转，正确做法是**用 `Sinks` 接收入参，再用操作符转换**：

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

import java.util.Locale;

public class TypedBridge {

    // 入口是 String，出口是 Integer —— 用 Sinks + map 表达，而不是自造 Processor
    private final Sinks.Many<String> inbound = Sinks.many().multicast().onBackpressureBuffer();

    public Flux<Integer> lengths() {
        return inbound.asFlux()
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(s -> s.toLowerCase(Locale.ROOT).length());
    }

    public void receive(String raw) {
        inbound.tryEmitNext(raw);
    }
}
```

## 六、如果非要自己实现一个 Processor

只在写"连接两个不同 API 的适配层"时才需要。规范要求实现 `Processor` 的四个 `Subscriber` 方法与
`Publisher.subscribe`，其中最关键的是**把下游的 `request(n)` 转给上游的 `Subscription`**：

```java
import org.reactivestreams.Processor;
import org.reactivestreams.Subscriber;
import org.reactivestreams.Subscription;
import reactor.core.publisher.Flux;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 极简直通 Processor：只演示协议义务，不具备生产所需的背压缓冲与并发安全。
 * 生产代码请直接用 Sinks 或 Flux 操作符。
 */
public class PassThroughProcessor<T> implements Processor<T, T> {

    private final AtomicReference<Subscriber<? super T>> downstream = new AtomicReference<>();
    private volatile Subscription upstream;

    @Override
    public void subscribe(Subscriber<? super T> s) {
        downstream.set(s);
        s.onSubscribe(new Subscription() {
            @Override public void request(long n) { upstream.request(n); }   // 需求透传
            @Override public void cancel()         { upstream.cancel(); }
        });
    }

    @Override public void onSubscribe(Subscription s) { this.upstream = s; }
    @Override public void onNext(T t)                 { downstream.get().onNext(t); }
    @Override public void onError(Throwable t)        { downstream.get().onError(t); }
    @Override public void onComplete()                { downstream.get().onComplete(); }

    public static void main(String[] args) {
        PassThroughProcessor<Integer> processor = new PassThroughProcessor<>();
        List<Integer> received = new ArrayList<>();

        // 顺序很关键：先接上游（此刻 Processor 是 Subscriber），再让下游订阅（此刻它是 Publisher）。
        // 反过来做，下游 request 时 upstream 还是 null，直接 NPE。
        Flux.range(1, 3).subscribe(processor);

        processor.subscribe(new Subscriber<Integer>() {
            @Override public void onSubscribe(Subscription s) { s.request(3); }
            @Override public void onNext(Integer v)           { received.add(v); }
            @Override public void onError(Throwable t)        { }
            @Override public void onComplete()                { System.out.println("received=" + received); }
        });
    }
}
```

运行输出：

```text
received=[1, 2, 3]
```

这段代码能编译、能跑通，但它**丢掉了所有难点**：多订阅者、缓冲、并发序列化、取消传播、
`onSubscribe` 顺序校验、以及"下游先于上游连接"的容错。这正是 `Sinks` 存在的理由——
这些细节不该由每个使用者重写一遍。

## 七、`ConnectableFlux`：另一条"造热流"的路

`Processor` 的替代并不只有 `Sinks`。如果源头本来就是一条 `Flux`，只是想让多个下游共享同一次订阅，
用 `ConnectableFlux` 更贴切：

```java
import reactor.core.publisher.ConnectableFlux;
import reactor.core.publisher.Flux;

import java.time.Duration;

public class ConnectableDemo {
    public static void main(String[] args) {
        // 只订阅一次上游（比如只打一次远程接口），结果广播给多个下游
        ConnectableFlux<Long> shared = Flux.interval(Duration.ofMillis(100))
                .take(3)
                .publish();          // 尚未连接

        shared.subscribe(v -> System.out.println("[A] " + v));
        shared.subscribe(v -> System.out.println("[B] " + v));

        shared.connect();            // 此刻才真正订阅上游，两个下游同时开始收
        sleep(600);
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

| 需求 | 选择 |
|------|------|
| 外部事件推进来（MQ、回调、WebSocket） | `Sinks.Many` |
| 已有 `Flux`，多个下游共享一次订阅 | `publish().autoConnect(n)` / `share()` |
| 已有 `Flux`，结果要缓存给后来者 | `cache()` / `replay(n).autoConnect()` |
| 需要 `T → R` 类型转换 | `Sinks` + `map`/`flatMap` |
| 单值异步结果 | `Sinks.One` / `Mono.fromFuture` |

## 常见陷阱

| 陷阱 | 后果 | 纠正 |
|------|------|------|
| 新代码继续用 `DirectProcessor` | 慢订阅者直接抛 `OverflowException` | `Sinks.many().multicast().onBackpressureBuffer()` |
| 把 `Processor` 当"线程安全的队列" | 并发 `onNext` 打乱信号顺序 | `Sinks` + `EmitFailureHandler` 或外部串行化 |
| 在 `Processor` 上期望 `contextWrite` 生效 | Context 在断点处丢失 | 改用 `Sinks` + 单条链 |
| 一个 `Processor` 全局复用 | 一次终止后整个应用再也收不到消息 | 每次生命周期新建实例，并管理终止 |
| 用 `UnicastProcessor` 做广播 | 第二个订阅者报错 | 广播用 `multicast()` |
| 忽略 `ReplayProcessor` 的内存增长 | 长跑后 OOM | `replay().limit(n)` 或 `replay().latest()` |

## 与相关概念的关系

- [[04-sink|Sink 组件]]：直接替代品，先读它再看本篇的迁移表会更顺。
- [[01-concepts|核心概念]]：`Processor` 是"既是 `Subscriber` 又是 `Publisher`"这一角色的具体化。
- [[03-usage|使用指南]]：`Flux.create`/`generate` 里的 `FluxSink` 是另一套发射入口，别与 `Processor` 混用。
- [[02-origin|起源与演进]]：为什么 3.4/3.5 是这条 API 的分水岭。

## 参考

- [Reactor 文档：Sinks（替代 Processor）](https://projectreactor.io/docs/core/release/reference/#sinks)
- [FluxProcessor Javadoc（含 Deprecated 说明）](https://projectreactor.io/docs/core/release/api/reactor/core/publisher/FluxProcessor.html)
- [Reactor 3.5 Release Notes](https://github.com/reactor/reactor-core/releases)
