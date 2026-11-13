---
title: Reactor Sink 组件
description: Sinks 门面的三类多播语义、EmitResult 与失败处理、线程安全规则、生命周期与实战用法
tags:
  - java
  - reactor
  - reactive
  - sink
date: 2026-11-13
aliases:
  - reactor-sink
  - sinks
---

# Reactor Sink 组件

## 概述

`Sinks` 是 Reactor 3.4 引入的**手动推流门面**：当数据不是"你要它才给你"（拉），而是"外部事件来了就推"，
就用它把外部世界的事件转成一条 `Flux`/`Mono`。它同时解决了旧 `Processor` 的三个问题——
发射结果可判定（`EmitResult`）、失败处理可定义（`EmitFailureHandler`）、多播语义可显式选择。

一个必须先分清的命名陷阱：

| 名称 | 是什么 | 出现在哪 |
|------|--------|----------|
| `FluxSink` / `SynchronousSink` | **回调式**的发射器，只在 `Flux.create`/`generate` 的 lambda 里存在 | 桥接旧 API |
| `Sinks` 门面（`Sinks.Many`/`One`/`Empty`） | **独立存在**的推流器，可以先创建、后暴露、随时发射 | 事件总线、SSE、WebSocket |

本篇讲后者。前者见 [[03-usage|使用指南]] 的"创建"一节。

## 前置知识

- [[01-concepts|核心概念]]的"冷流/热流"与"背压"两节
- [[03-usage|使用指南]]的 `Flux`/`Mono` 基本操作

## 一、API 结构

```text
Sinks.many()  →  Sinks.ManySpec  ─┬─ unicast()   → 单订阅者，带缓冲
                                  ├─ multicast() → 多订阅者，可选缓冲/直发
                                  └─ replay()    → 多订阅者，向新订阅者重放历史

Sinks.one()   →  Sinks.One<T>    → 0..1 个值，语义等同 Mono，但可外部写入
Sinks.empty() →  Sinks.Empty<T>  → 只发完成/错误信号，等价 Mono<Void>
```

拿到 `Sinks.Many<T>` 后，两侧的用法是：

```java
Sinks.Many<String> sink = Sinks.many().multicast().onBackpressureBuffer();

Flux<String> stream = sink.asFlux();   // 对外暴露给订阅者（热流）

sink.tryEmitNext("hello");             // 外部事件到来时推进去
sink.tryEmitComplete();                // 或 tryEmitError(t)
```

## 二、三种多播语义（选错就是线上事故）

| 工厂方法 | 订阅者数 | 缓冲 | 无订阅者时发射 | 慢订阅者 | 典型用途 |
|----------|----------|------|----------------|----------|----------|
| `many().unicast().onBackpressureBuffer()` | **仅 1 个** | 有界/无界缓冲 | `FAIL_ZERO_SUBSCRIBER` | 背压有效，不会丢 | 单个消费者消费一条事件流 |
| `many().multicast().onBackpressureBuffer()` | 多个 | 每个订阅者独立缓冲 | **缓冲起来，等第一个订阅者** | 各自缓冲 | 广播 + 允许慢消费者（默认首选） |
| `many().multicast().directBestEffort()` | 多个 | 无 | `FAIL_ZERO_SUBSCRIBER` | **只对慢的那个丢弃**，不影响别人 | 实时指标、UI 刷新 |
| `many().multicast().directAllOrNothing()` | 多个 | 无 | `FAIL_ZERO_SUBSCRIBER` | **任一慢则整次发射失败** | 严格一致的广播 |
| `many().replay().all()` | 多个 | 全量 | 缓冲起来 | 新订阅者收到全部历史 | 状态广播、配置变更 |
| `many().replay().latest()` | 多个 | 仅最后 1 个 | 缓冲起来 | 新订阅者只收到最后一个 | "当前值"型广播 |
| `many().replay().limit(n)` | 多个 | 最近 n 个 | 缓冲起来 | 新订阅者收到最近 n 个 | 有限回放 |

三条实践结论：

1. **默认用 `multicast().onBackpressureBuffer()`**。它在"没人订阅时先缓冲"这一点上最宽容，
   避免了启动顺序竞态导致的 `FAIL_ZERO_SUBSCRIBER`。
2. **`directBestEffort()` 会静默丢数据**，只适合"允许丢"的场景（实时刷新、指标采样）。
3. **`unicast()` 只允许一个订阅者**，第二个订阅者会收到错误。做 WebSocket 单连接推送时可以，
   做"多端同步"时是错的。

## 三、EmitResult：发射是有结果的

旧 `Processor` 的 `onNext` 返回 `void`，失败了你看不到。`tryEmitNext` 返回 `Sinks.EmitResult`，
六种取值各有含义和处理方式：

| EmitResult | 含义 | 处理建议 |
|-----------|------|----------|
| `OK` | 成功 | 继续 |
| `FAIL_TERMINATED` | 流已终止（完成/出错/取消） | 停止发射，通常说明上游生命周期该结束了 |
| `FAIL_OVERFLOW` | 缓冲满（有界缓冲或 directAllOrNothing 遇慢消费者） | 降级、丢弃或阻塞重试 |
| `FAIL_CANCELLED` | 所有订阅者已取消 | 释放资源、停止生产 |
| `FAIL_NON_SERIALIZED` | **并发发射冲突**（多线程同时 `tryEmitNext`） | 重试或改用串行化入口 |
| `FAIL_ZERO_SUBSCRIBER` | 无订阅者（且该模式不缓冲） | 重试/等待订阅者 |

`FAIL_NON_SERIALIZED` 是最容易被忽略的一个：`Sinks` 内部用序列号保证发信号是串行的，
**并发调用不会被排队，而是直接失败**。所以要区分两种写法：

```java
// 单生产者（推荐）：直接 tryEmitXxx，失败了自己决定怎么处理
Sinks.EmitResult r = sink.tryEmitNext(event);
if (r.isFailure()) {
    log.warn("emit failed: {}", r);
}

// 多生产者：用 emitNext + 重试策略，把并发冲突"转"成串行
sink.emitNext(event, Sinks.EmitFailureHandler.busyLooping(Duration.ofSeconds(1)));
```

| 失败处理器 | 行为 |
|-----------|------|
| `EmitFailureHandler.FAIL_FAST` | 不重试，直接把失败返回（默认） |
| `busyLooping(Duration timeout)` | 对 `FAIL_NON_SERIALIZED` 自旋重试，直到超时 |

注意 `busyLooping` **只重试 `FAIL_NON_SERIALIZED`**，其余失败仍然立即返回——这是设计上的克制：
溢出和终止不该被"重试"掩盖。

## 四、完整示例：从事件源到流

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

import java.time.Duration;

public class SinkDemo {

    public static void main(String[] args) {
        // 1) 选语义：广播 + 缓冲 + 多订阅者
        Sinks.Many<String> bus = Sinks.many().multicast().onBackpressureBuffer();

        Flux<String> stream = bus.asFlux();

        stream.subscribe(v -> System.out.println("[A] " + v));
        stream.subscribe(v -> System.out.println("[B] " + v));

        // 2) 外部线程推送（模拟消息队列/MQTT/WebSocket 回调）
        bus.emitNext("order-created", Sinks.EmitFailureHandler.busyLooping(Duration.ofSeconds(1)));
        bus.emitNext("order-paid", Sinks.EmitFailureHandler.busyLooping(Duration.ofSeconds(1)));

        // 3) 终止：complete / error 二选一，且只生效一次
        bus.emitComplete(Sinks.EmitFailureHandler.FAIL_FAST);

        // 4) 终止后再发，返回 FAIL_TERMINATED
        System.out.println("after complete -> " + bus.tryEmitNext("late"));
    }
}
```

预期输出（顺序稳定）：

```text
[A] order-created
[B] order-created
[A] order-paid
[B] order-paid
after complete -> FAIL_TERMINATED
```

## 五、生命周期与资源

| 关键点 | 说明 |
|--------|------|
| 一次性 | `Sinks` 终止后不可复用；需要新流就新建一个 `Sinks.Many` |
| 完成 ≠ 订阅者消失 | `tryEmitComplete()` 后 `asFlux()` 仍可被订阅（立即完成），但不能再发元素 |
| 取消检测 | 用 `asFlux().doOnCancel(...)` 或检查 `FAIL_CANCELLED` |
| 资源清理 | 监听者/连接的注销放在 `asFlux().doFinally(sig -> close())` 里 |
| 不要 `asFlux()` 多次分发 | 尤其 `unicast`：多次订阅会冲突。一个 `Sinks` 只 `asFlux()` 一次并复用该 `Flux` |

## 六、四个实战模式

### 模式 1：SSE / WebSocket 广播

```java
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

@RestController
public class NotificationController {

    // 应用级单例：所有连接共享同一场广播
    private final Sinks.Many<String> notifications =
            Sinks.many().multicast().onBackpressureBuffer(256);

    @GetMapping(value = "/notifications", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> stream() {
        return notifications.asFlux();          // 连接关闭时框架自动取消订阅
    }

    // 业务侧调用：推一条通知
    public void publish(String message) {
        notifications.emitNext(message, Sinks.EmitFailureHandler.FAIL_FAST);
    }
}
```

### 模式 2：请求-应答桥接（把回调式 SDK 变成 `Mono`）

```java
import reactor.core.publisher.Mono;
import reactor.core.publisher.Sinks;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class RequestReplyBridge {

    private final Map<String, Sinks.One<String>> pending = new ConcurrentHashMap<>();

    /** 调用方视角：一次异步请求 = 一个 Mono */
    public Mono<String> request(String requestId) {
        Sinks.One<String> slot = Sinks.one();
        pending.put(requestId, slot);
        sendToDevice(requestId);                       // 触发外部异步回调
        return slot.asMono().timeout(Duration.ofSeconds(5));   // 超时由流自身兜底
    }

    /** 回调线程视角：拿到结果后回填 */
    public void onResponse(String requestId, String payload) {
        Sinks.One<String> slot = pending.remove(requestId);
        if (slot != null) {
            slot.tryEmitValue(payload);                // 已有订阅者会立刻收到
        }
    }

    private void sendToDevice(String requestId) {
        // 省略：写入 socket / 发送 MQ 消息
    }
}
```

这个模式的要点：**`Sinks.One` 是"未完成的 `Mono`"**，它让"回调风格"和"响应式风格"在边界处完成转换，
而且超时、降级、取消都能继续用操作符表达。

### 模式 3：有界单消费者（背压有效）

```java
import reactor.core.publisher.Sinks;

public class UnicastDemo {
    public static void main(String[] args) {
        Sinks.Many<Integer> pipe = Sinks.many().unicast().onBackpressureBuffer();

        pipe.asFlux()
                .doOnNext(i -> sleep(50))          // 慢消费者
                .subscribe(i -> System.out.println("consumed " + i));

        for (int i = 0; i < 5; i++) {
            pipe.tryEmitNext(i);                   // 缓冲，不会因为消费慢而丢
        }
        pipe.tryEmitComplete();
        sleep(500);
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

### 模式 4：`Sinks.empty()` 做"完成信号"

```java
import reactor.core.publisher.Mono;
import reactor.core.publisher.Sinks;

public class ShutdownSignal {
    private final Sinks.Empty<Void> shutdown = Sinks.empty();

    public Mono<Void> awaitShutdown() { return shutdown.asMono(); }

    public void trigger() { shutdown.tryEmitEmpty(); }   // 所有等待者同时被唤醒并完成
}
```

## 常见陷阱

| 陷阱 | 现象 | 纠正 |
|------|------|------|
| 多线程直接 `tryEmitNext` | 偶发丢事件，日志里出现 `FAIL_NON_SERIALIZED` | 用 `emitNext(v, busyLooping(...))` 或串行化入口 |
| 用 `directBestEffort()` 却又要求不丢 | 高峰丢数据 | 换 `onBackpressureBuffer()` |
| `unicast()` 被两处订阅 | 第二处报错 | 广播用 `multicast()` |
| 每次请求都 `asFlux()` | 多订阅、行为异常 | 只 `asFlux()` 一次，持有 `Flux` 引用 |
| 无界缓冲 `onBackpressureBuffer()` | 内存持续上涨 | 给容量参数并处理 `FAIL_OVERFLOW` |
| 终止后继续发射 | 静默无效 | 检查返回的 `EmitResult` |
| 忘记释放监听器 | 线程/连接泄漏 | `doFinally` 里清理 |

## 与相关概念的关系

- [[05-processor|Processor 组件]]：`Sinks` 的前身与迁移对照，**新代码不要再写 `Processor`**。
- [[01-concepts|核心概念]]：`Sinks` 是制造"热流"的标准手段，配合 `ConnectableFlux` 理解更完整。
- [[03-usage|使用指南]]：`Flux.create(sink -> ...)` 里的 `FluxSink` 与本篇的 `Sinks` 不是同一个东西。
- [[07-applications|应用场景]]：SSE、WebSocket、消息桥接都是 `Sinks` 的主战场。

## 参考

- [Reactor 文档：Sinks](https://projectreactor.io/docs/core/release/reference/#sinks)
- [Sinks Javadoc](https://projectreactor.io/docs/core/release/api/reactor/core/publisher/Sinks.html)
