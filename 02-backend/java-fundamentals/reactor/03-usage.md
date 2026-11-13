---
title: Reactor 使用指南
description: 依赖引入、操作符分类、线程切换、调试手段与 StepVerifier 测试的实战手册
tags:
  - java
  - reactor
  - reactive
date: 2026-11-13
aliases:
  - reactor-usage
---

# Reactor 使用指南

## 概述

本篇是"日常怎么写"的手册：从引入依赖开始，按**创建 → 转换 → 组合 → 容错 → 切线程 → 收尾**的顺序走一遍，
最后给出调试和测试的手法。概念层面的解释见 [[01-concepts|核心概念]]，完整可运行的例子见
[[06-code-examples|代码案例]]。

## 前置知识

- [[01-concepts|核心概念]]的"惰性""背压""Scheduler"三节（不理解惰性，本篇的代码会被误读）
- Maven 或 Gradle 基本用法

## 一、依赖与版本

**Spring Boot 项目不需要写版本**，由 BOM 决定：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
```

独立项目（或需要显式控制版本时）用 Reactor BOM：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.projectreactor</groupId>
            <artifactId>reactor-bom</artifactId>
            <version>2025.0.0</version>   <!-- 对应 reactor-core 3.8.x -->
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>io.projectreactor</groupId>
        <artifactId>reactor-core</artifactId>
    </dependency>
    <!-- 测试：StepVerifier / TestPublisher -->
    <dependency>
        <groupId>io.projectreactor</groupId>
        <artifactId>reactor-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

> 版本基线：`reactor-core` 3.5.x 支持 Java 8；**3.6 起要求 Java 17**。若项目跑在 Java 8 上，
> 最高只能用到 3.5.x（对应 Boot 2.7）。

## 二、三个必须内化的约定

1. **没订阅 = 没执行**。返回 `Flux`/`Mono` 的方法在被订阅前不做任何事。Controller 里返回它是正确的——
   框架负责订阅；`main` 方法里必须自己 `subscribe()`。
2. **链是不可变的**。`map` 返回新实例，原对象不变。所以"调了操作符却没赋值"（`flux.map(...)` 后丢弃返回值）
   等于没写。
3. **末端只订阅一次**。`subscribe()` 内部的 `subscribe()` 会切断背压与错误传播，正确做法是用 `flatMap`/`then` 组合。

## 三、创建

| 类别 | 操作符 | 说明 |
|------|--------|------|
| 定值 | `Flux.just(1, 2, 3)` / `Mono.just(x)` | 已就绪的内存值 |
| 空/错误 | `Mono.empty()` / `Flux.error(e)` / `Mono.never()` | 边界与测试 |
| 集合 | `Flux.fromIterable(list)` / `fromArray` / `fromStream` | 桥接同步集合 |
| 序列 | `Flux.range(1, 5)` / `Flux.interval(Duration.ofSeconds(1))` | 计数、定时 |
| 延迟计算 | `Mono.fromCallable(() -> jdbcQuery())` | 每次订阅重新执行，异常进 `onError` |
| 延迟装配 | `Mono.defer(() -> dynamicPublisher())` | 每次订阅重建整个流 |
| 异步桥接 | `Mono.fromFuture(cf)` / `Mono.fromCompletionStage` | 对接 `CompletableFuture` |
| 回调桥接 | `Flux.create(sink -> ...)` | 对接事件监听器（见 [[04-sink\|Sink]]） |
| 资源绑定 | `Flux.using(...)` / `Mono.usingWhen(...)` | 有打开/关闭配对的资源 |

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.Arrays;

public class CreateDemo {
    public static void main(String[] args) {
        // fromCallable：把阻塞调用变成"每次订阅才执行"
        Mono<String> user = Mono.fromCallable(() -> loadFromDb("u-1"));

        // defer：根据运行时条件决定返回哪种流（just / empty / error）
        Mono<String> maybe = Mono.defer(() ->
                Math.random() > 0.5 ? Mono.just("hit") : Mono.empty());

        // interval 默认在 parallel 调度器上跑，必须 take 限制个数，否则永不结束
        Flux<Long> ticks = Flux.interval(Duration.ofMillis(100)).take(3);

        System.out.println(user.block());          // 仅在 main/测试里可以 block
        ticks.subscribe(t -> System.out.println("tick " + t));
        sleep(500);                                 // 演示用：等异步流跑完
    }

    static String loadFromDb(String id) { return "user:" + id; }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

## 四、转换与过滤

```java
Flux.just("order-1", "order-2", "order-3")
        .filter(id -> !id.endsWith("2"))         // 过滤
        .map(String::toUpperCase)                // 同步 1:1 转换
        .flatMap(id -> Mono.just(id.length()))   // 异步 1:N 转换（并发）
        .distinct()                              // 去重
        .take(2)                                 // 取前 2 个
        .subscribe(System.out::println);
```

`map` 与 `flatMap` 的选择是新手最容易混淆的地方：

| 操作符 | 输入 → 输出 | 是否异步 | 顺序 | 用途 |
|--------|-------------|----------|------|------|
| `map` | `T` → `R` | 否（同步） | 严格保序 | 字段转换、解析 |
| `flatMap` | `T` → `Publisher<R>` | 是（并发，默认 256 并发度） | **不保序** | 每个元素触发一次远程调用 |
| `concatMap` | `T` → `Publisher<R>` | 是（串行） | 保序 | 有先后依赖、需要限速 |
| `flatMapSequential` | `T` → `Publisher<R>` | 是（并发） | 保序（按源顺序缓冲） | 想要并发又要顺序 |

`flatMap(f, concurrency)` 的第二个参数是最有用的调优旋钮：并发度设小可以保护下游（防止把下游打挂），
设大则吞吐高但内存与连接数上升。

## 五、组合

| 需求 | 操作符 | 语义 |
|------|--------|------|
| 汇聚多个结果 | `Mono.zip(a, b)` / `Flux.zip(a, b, combinator)` | 各取一个，按位置配对；任一为空则结果为空 |
| 无顺序合并 | `Flux.merge(a, b)` | 谁先来谁先出 |
| 串行拼接 | `Flux.concat(a, b)` | 前一个完成后才订阅下一个 |
| 取最新组合 | `Flux.combineLatest(a, b, f)` | 任一更新就重算一次 |
| 等待全部完成 | `Mono.when(a, b)` | 只关心完成，不关心结果 |
| 条件分支 | `switchIfEmpty` / `defaultIfEmpty` | 空流兜底 |
| 完成后接着做 | `then` / `thenReturn` / `thenMany` | 丢弃前序元素，只保留完成信号 |

```java
Mono<String> profile = fetchProfile(userId);
Mono<Integer> score = fetchScore(userId);

// 并行发起，两者都回来才组装（任一超时/失败则整体失败，可用 onErrorResume 降级）
Mono<String> summary = Mono.zip(profile, score)
        .map(t -> t.getT1() + " -> " + t.getT2())
        .timeout(Duration.ofSeconds(2))
        .onErrorResume(e -> Mono.just("degraded"));
```

注意 `zip` 的短路特性：**任一上游为空，整体就为空**，不是"另一个值照常返回"。这是线上
"明明有数据却返回空"的常见根因，需要时改用 `zipWith` + `defaultIfEmpty` 或 `optional` 组合。

## 六、错误处理

| 操作符 | 行为 | 场景 |
|--------|------|------|
| `onErrorReturn(v)` | 出错返回固定值 | 兜底默认值 |
| `onErrorResume(f)` | 出错切换到备用流 | 降级调用缓存/静态数据 |
| `onErrorMap(f)` | 转换异常类型 | 把技术异常转成业务异常 |
| `onErrorContinue` | 跳过错误元素继续 | **慎用**：会破坏流语义，仅在批处理容忍失败时考虑 |
| `retry(n)` | 重订阅上游 n 次 | 瞬时故障 |
| `retryWhen(Retry.backoff(...))` | 带退避/过滤的重试 | 生产推荐 |
| `timeout(Duration)` | 超时抛 `TimeoutException` | 保护尾部延迟 |
| `doFinally(sig)` | 无论成功/失败/取消都执行 | 埋点、资源清理 |

```java
import reactor.core.publisher.Flux;
import reactor.util.retry.Retry;

import java.time.Duration;

public class RetryDemo {
    public static void main(String[] args) {
        Flux<String> call = Flux.defer(() -> unstableRemoteCall())
                .timeout(Duration.ofMillis(300))
                // 只对超时/网络类错误重试，4xx 这类业务错误不重试
                .retryWhen(Retry.backoff(3, Duration.ofMillis(100))
                        .filter(err -> !(err instanceof IllegalArgumentException))
                        .maxBackoff(Duration.ofSeconds(2)))
                .onErrorResume(err -> Flux.just("fallback"));

        System.out.println(call.collectList().block());
    }

    static Flux<String> unstableRemoteCall() {
        if (Math.random() < 0.7) {
            return Flux.error(new java.io.IOException("connection reset"));
        }
        return Flux.just("ok");
    }
}
```

`retry` 的语义是**重新订阅上游**，装配阶段不会重跑。所以像"读取当前时间""生成随机数"这类逻辑，
必须包在 `defer`/`fromCallable` 里，否则重试拿到的还是同一个值。

## 七、背压相关操作符

| 操作符 | 作用 |
|--------|------|
| `limitRate(n)` | 把上游请求拆成每批 n 个，降低峰值内存 |
| `onBackpressureBuffer()` | 无界缓冲（危险） |
| `onBackpressureBuffer(capacity)` | 有界缓冲，溢出报错 |
| `onBackpressureDrop()` | 溢出丢弃 |
| `onBackpressureLatest()` | 只留最新值 |
| `bufferTimeout(maxSize, Duration)` | 凑批：满 n 个或超时就发一批 |
| `publishOn(scheduler, prefetch)` | 切换消费线程并设定预取量 |

对"下游是一个慢速外部系统（比如逐条写库）"的场景，`bufferTimeout` 是提高吞吐最有效的手段：

```java
import reactor.core.publisher.Flux;

import java.time.Duration;
import java.util.List;

public class BatchDemo {
    public static void main(String[] args) {
        Flux.range(1, 100)
                .bufferTimeout(20, Duration.ofMillis(200))   // 每 20 条或 200ms 触发一次
                .subscribe(batch -> writeBatch(batch));
        try { Thread.sleep(1500); } catch (InterruptedException ignored) { }
    }

    static void writeBatch(List<Integer> batch) {
        System.out.println("写入 " + batch.size() + " 条: " + batch);
    }
}
```

## 八、Scheduler 与线程切换

```java
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

public class SchedulerDemo {
    public static void main(String[] args) {
        Mono.fromCallable(() -> blockingJdbcQuery())          // 数据源在 elastic 线程生产
                .subscribeOn(Schedulers.boundedElastic())
                .map(String::trim)                             // 仍在 elastic
                .publishOn(Schedulers.parallel())              // 从这里往下切到 CPU 线程
                .map(v -> v.length() * 2)                      // 在 parallel
                .subscribe(len -> System.out.println("len=" + len));
    }

    static String blockingJdbcQuery() { return "  result  "; }
}
```

三条规则：

- **阻塞代码一律进 `boundedElastic`**，不要进 `parallel`（线程数只有 CPU 核数，阻塞会饿死整机）。
- **`subscribeOn` 只影响上游，且只有最靠近源头的那个生效**；`publishOn` 影响下游，可以多次出现形成接力。
- **`Flux.interval` / `delayElements` / `timeout` 自带调度器**，不需要也不应该再包 `subscribeOn`。

## 九、生命周期钩子与资源管理

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.SignalType;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

public class ResourceDemo {
    public static void main(String[] args) throws Exception {
        // using：资源在订阅时打开，在终止/取消时关闭（等价于 try-with-resources）
        Flux<String> lines = Flux.using(
                () -> Files.newBufferedReader(Paths.get("pom.xml")),
                reader -> Flux.fromStream(reader.lines()),
                reader -> {                                  // 清理函数不能抛受检异常，必须自己兜住
                    try {
                        reader.close();
                    } catch (IOException e) {
                        System.err.println("close failed: " + e.getMessage());
                    }
                });

        lines.doOnSubscribe(s -> System.out.println(">>> 订阅开始"))
             .doOnNext(line -> System.out.println("读到: " + line))
             .doFinally(signal -> System.out.println("<<< 结束, 信号=" + signal))
             .take(3)                                  // 提前取消，仍会触发 doFinally(CANCEL)
             .subscribe();
    }
}
```

`doFinally(SignalType)` 是埋点与清理的落点，`SignalType` 会告诉你到底是 `ON_COMPLETE`、`ON_ERROR` 还是 `CANCEL`——
区分取消与完成对统计"用户中断"很关键。

## 十、复用：`transform` 与 `transformDeferred`

一堆操作符被反复拼装时，把它们收成一个函数：

```java
import reactor.core.publisher.Flux;
import reactor.util.retry.Retry;

import java.time.Duration;

public class TransformDemo {
    // 把"超时 + 退避重试 + 日志"打包成可复用算子
    static <T> Flux<T> withResilience(Flux<T> source) {
        return source
                .timeout(Duration.ofSeconds(2))
                .retryWhen(Retry.backoff(2, Duration.ofMillis(100)))
                .doOnError(e -> System.out.println("最终失败: " + e.getMessage()));
    }

    public static void main(String[] args) {
        Flux<Integer> data = withResilience(Flux.just(1, 2, 3)).map(i -> i * 10);
        System.out.println(data.collectList().block());
    }
}
```

`transform` 在**装配阶段**执行（同一实例共享算子），`transformDeferred` 在**每次订阅时**执行
（可以读取运行时状态）。需要"每个订阅者拿到独立配置"时用后者。

## 十一、调试

响应式的痛点是没有可读的堆栈。三件工具按成本排序：

| 手段 | 用法 | 成本 | 适用 |
|------|------|------|------|
| `log()` | `.log("order-flow")` | 低 | 定位"到底有没有发出/收到" |
| `checkpoint()` | `.checkpoint("after-fetch-user")` | 低 | 在长链上标注位置，异常里会带上这个标记 |
| `Hooks.onOperatorDebug()` | 全局开启装配栈捕获 | **高**（每次装配都抓栈） | 只允许在本地/预发开启 |
| `ReactorDebugAgent`（`-javaagent`） | JVM 参数挂载 | 低 | 生产可用，需引入 `reactor-tools` |

```java
import reactor.core.publisher.Flux;

public class DebugDemo {
    public static void main(String[] args) {
        Flux.just("a", "b")
                .map(String::toUpperCase)
                .checkpoint("after-uppercase")            // 异常堆栈里会显示这个标记
                .log("demo")                              // 打印 subscribe/request/onNext 全事件
                .subscribe();
    }
}
```

## 十二、测试：StepVerifier

不要用 `block()` 断言结果——那会丢掉"信号顺序""是否有多余元素""是否完成"等信息。
`reactor-test` 的 `StepVerifier` 是标准做法：

```java
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.time.Duration;

class OrderServiceTest {

    @Test
    void 过滤并转换_应只保留有效订单() {
        Flux<String> result = Flux.just("A-1", "B-2", "A-3")
                .filter(id -> id.startsWith("A"))
                .map(String::toLowerCase);

        StepVerifier.create(result)
                .expectNext("a-1", "a-3")
                .verifyComplete();     // 顺带校验"没有多余元素且正常完成"
    }

    @Test
    void 空结果_应走降级() {
        Mono<String> fallback = Mono.<String>empty().defaultIfEmpty("default");
        StepVerifier.create(fallback).expectNext("default").verifyComplete();
    }

    @Test
    void 延迟_用虚拟时间加速() {
        // 注意：流必须在 lambda 内创建。Mono.delay/timeout 在装配时就捕获调度器，
        // 提前创建好再传进来，虚拟时间不会生效，测试会真的等一小时
        StepVerifier.withVirtualTime(() -> Mono.delay(Duration.ofHours(1)))
                .thenAwait(Duration.ofHours(1))
                .expectNextCount(1)
                .verifyComplete();     // 不需要真的等一小时
    }
}
```

`TestPublisher` 用于构造"手动控制信号"的场景（验证背压、验证取消），比模拟对象更贴近协议层。

## 常见陷阱

| 陷阱 | 现象 | 正确做法 |
|------|------|----------|
| 忘记订阅 | 什么都没发生，无日志无异常 | 末端 `subscribe()`，或返回给框架 |
| `subscribe` 套 `subscribe` | 背压失效、异常吞掉、无法取消 | `flatMap`/`then` 组合成一条链 |
| 在 `parallel` 上阻塞 | 整机响应变慢甚至卡死 | 阻塞进 `boundedElastic` |
| `Mono.just(null)` | `NullPointerException` | `Mono.empty()` / `justOrEmpty` |
| `zip` 遇空即空 | 明明有数据却返回空 | 转 `Optional` 或用 `switchIfEmpty` |
| `block()` 在事件循环里 | `IllegalStateException: block()/blockFirst() is blocking, which is not supported in thread reactor-http-nio-*` | 去掉 `block`，改返回值 |
| `doOnNext` 里改共享状态 | 并发下数据错乱 | 用原子类型，或在下游 `publishOn` 串行化 |
| `retry` 无退避 | 故障时打爆下游 | `Retry.backoff` + `filter` |

## 与相关概念的关系

- [[04-sink|Sink 组件]]：当数据来自"外部推"而不是"自己拉"时，用 `Sinks` 而不是 `Flux.create` 的匿名回调。
- [[05-processor|Processor 组件]]：老代码里 `UnicastProcessor`/`EmitterProcessor` 的等价写法在这里都有对照。
- [[spring-webflux|Spring WebFlux]]：Controller 层怎么把这套东西暴露成 HTTP。
- [[java-concurrency|Java 并发编程（CompletableFuture）]]:从 `CompletableFuture` 迁移过来的思维对照。

## 参考

- [Reactor 参考文档：Operator 全表](https://projectreactor.io/docs/core/release/reference/#which-operator)
- [reactor-test 与 StepVerifier](https://projectreactor.io/docs/core/release/reference/#testing)
- [[06-code-examples|代码案例]]：本篇操作符的完整可运行版本
