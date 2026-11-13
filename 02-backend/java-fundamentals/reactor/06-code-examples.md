---
title: Reactor 代码案例
description: 八个可直接运行的 Reactor 案例：阻塞桥接、并发聚合、顺序控制、批处理、重试退避、SSE 广播、LLM 流式输出与测试
tags:
  - java
  - reactor
  - reactive
  - examples
date: 2026-11-13
aliases:
  - reactor-examples
---

# Reactor 代码案例

## 概述

以下八个案例都是**能跑的最小闭环**：每个示例只有一个 `main`（测试那个是 JUnit 5 类），
不依赖 Spring，只依赖 `reactor-core`（测试案例额外依赖 `reactor-test`）。
本地用 JDK 17+ 编译、`java` 直接运行即可，无需 `System.exit` 之外的额外配置。

每个案例都标注了它解决的真实问题，以及**为什么不能写成另一种看起来更简单的形式**。

## 环境准备

最小可运行结构（Maven）：

```xml
<dependencies>
    <dependency>
        <groupId>io.projectreactor</groupId>
        <artifactId>reactor-core</artifactId>
        <version>3.8.6</version>
    </dependency>
    <dependency>
        <groupId>io.projectreactor</groupId>
        <artifactId>reactor-test</artifactId>
        <version>3.8.6</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

不用构建工具也可以直接跑（把 jar 放进 `lib/`）：

```bash
javac -cp "lib/*" -d out src/*.java
java  -cp "out:lib/*" Case1BlockingBridge
```

## 案例 1：把阻塞调用桥接进响应式

**问题**：技术栈已经是 WebFlux，但手上只有 JDBC 驱动和老 SDK，全是阻塞的。

```java
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

public class Case1BlockingBridge {

    public static void main(String[] args) {
        // 错误示范：阻塞调用落在 parallel（CPU 线程池），并发一上来就饿死整机
        // Mono.fromCallable(() -> jdbcQuery(1)).subscribeOn(Schedulers.parallel())  ← 不要这样

        Mono<String> result = fetchUserName(42L)
                .map(String::toUpperCase)
                .defaultIfEmpty("UNKNOWN");

        System.out.println(result.block());   // 仅 main/测试里可以 block
    }

    /** 关键：fromCallable 保证每次订阅才执行；boundedElastic 允许阻塞 */
    static Mono<String> fetchUserName(long userId) {
        return Mono.fromCallable(() -> blockingJdbcQuery(userId))
                .subscribeOn(Schedulers.boundedElastic());
    }

    static String blockingJdbcQuery(long userId) {
        sleep(50);                                   // 模拟 jdbc 往返
        return "user-" + userId;
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

输出：

```text
USER-42
```

要点：`createDb` 这类方法**不要返回已经执行完的 `Mono.just(...)`**，那样阻塞发生在调用方线程，
`subscribeOn` 也救不了——`subscribeOn` 只能决定"订阅"发生在哪个线程，管不到已经算好的值。

## 案例 2：并发聚合多个下游 + 超时降级

**问题**：一个接口要聚合用户信息、积分、优惠券三个下游，串行调用 P99 相加超时。

```java
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;

public class Case2FanOutAggregate {

    public static void main(String[] args) {
        long start = System.currentTimeMillis();

        Mono<UserView> view = Mono.zip(
                        fetchProfile("u-1"),        // 三个子流同时订阅，总耗时≈最慢的那个
                        fetchScore("u-1"),
                        fetchCoupons("u-1"))
                .map(t -> new UserView(t.getT1(), t.getT2(), t.getT3()))
                .timeout(Duration.ofMillis(300))
                .onErrorResume(err -> Mono.just(UserView.degraded()));

        UserView v = view.block();
        System.out.println(v + "  cost=" + (System.currentTimeMillis() - start) + "ms");
    }

    static Mono<String> fetchProfile(String id) {
        return Mono.fromCallable(() -> { sleep(200); return "name:" + id; })
                .subscribeOn(Schedulers.boundedElastic());   // 必须切线程，否则见下方"踩坑记录"
    }

    static Mono<Integer> fetchScore(String id) {
        return Mono.fromCallable(() -> { sleep(180); return 880; })
                .subscribeOn(Schedulers.boundedElastic());
    }

    /** 故意慢：触发整体超时，走降级分支 */
    static Mono<String> fetchCoupons(String id) {
        return Mono.fromCallable(() -> { sleep(500); return "COUPON-3"; })
                .subscribeOn(Schedulers.boundedElastic());
    }

    static class UserView {
        final String name; final int score; final String coupons;
        UserView(String name, int score, String coupons) {
            this.name = name; this.score = score; this.coupons = coupons;
        }
        static UserView degraded() { return new UserView("anonymous", 0, "none"); }
        @Override public String toString() {
            return name + "/" + score + "/" + coupons;
        }
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

输出（稳态约 300ms，而不是三个下游相加的 880ms；**首次运行**因为 `boundedElastic` 线程池初始化
会多出约 100ms，实测 4xx ms）：

```text
anonymous/0/none  cost=403ms
```

要点：**`timeout` 放在 `zip` 之后**，约束的是"整体聚合"；放在每个子调用上会让降级逐项发生，
语义完全不同。两种都可以，取决于产品要"整体降级"还是"局部降级"。

> **踩坑记录（这个案例的第一版就是错的）**：如果三个 `fetch*` 方法只写 `Mono.fromCallable(...)`
> 而不加 `subscribeOn`，`zip` 会在**调用 `block()` 的那个线程上依次订阅**——于是三个阻塞调用串行执行
> （总耗时 880ms），而且 `timeout(300ms)` 根本不会触发，因为线程被 `sleep` 占死，定时器没有机会执行。
> 现象是"超时配置看起来生效了，实际却超时不了"。这条是 Reactor 最典型的组合陷阱：
> **`zip`/`merge` 只负责并发地"订阅"，真正并行执行取决于各子流是否切了线程。**

## 案例 3：并发与顺序的三岔口

**问题**：`flatMap` 快了但乱序，业务要求按源顺序输出。

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;

public class Case3Ordering {

    public static void main(String[] args) {
        System.out.println("flatMap(并发, 乱序)        = " + run(Flux.range(1, 5), false));
        System.out.println("concatMap(串行, 保序)       = " + run(Flux.range(1, 5), true));
        System.out.println("flatMapSequential(并发保序) = " + runSequential(Flux.range(1, 5)));
    }

    /** 模拟：越小的号排队越久，故意让完成顺序反过来 */
    static Mono<Integer> slowCall(int i) {
        return Mono.delay(Duration.ofMillis((6 - i) * 60L)).map(t -> i);
    }

    static String run(Flux<Integer> source, boolean ordered) {
        Flux<Integer> result = ordered
                ? source.concatMap(i -> slowCall(i))
                : source.flatMap(i -> slowCall(i));
        return result.collectList().block().toString();
    }

    static String runSequential(Flux<Integer> source) {
        return source.flatMapSequential(i -> slowCall(i)).collectList().block().toString();
    }
}
```

输出：

```text
flatMap(并发, 乱序)        = [5, 4, 3, 2, 1]
concatMap(串行, 保序)       = [1, 2, 3, 4, 5]
flatMapSequential(并发保序) = [1, 2, 3, 4, 5]
```

三者的真实差异在**总耗时**：`flatMap` 与 `flatMapSequential` 都是并发（总耗时≈最慢的一个），
`concatMap` 是串行（总耗时=全部之和）。要"又快又保序"就用 `flatMapSequential`，
代价是乱序完成的结果要在内存里等前面的先到位。

## 案例 4：背压与凑批写入

**问题**：逐条写库太慢，批量写又怕攒不满永远不提交。

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

public class Case4Batching {

    private static final AtomicInteger written = new AtomicInteger();

    public static void main(String[] args) {
        long start = System.currentTimeMillis();

        Flux.range(1, 95)
                .limitRate(32)                                  // 每批最多向源请求 32 个，削峰
                .bufferTimeout(20, Duration.ofMillis(150))       // 满 20 条 或 150ms 触发
                .concatMap(Case4Batching::writeBatch)            // 串行写，避免并发抢锁
                .doOnNext(size -> System.out.println("batch=" + size))
                .blockLast();

        System.out.println("total=" + written.get()
                + " cost=" + (System.currentTimeMillis() - start) + "ms");
    }

    static Mono<Integer> writeBatch(List<Integer> batch) {
        return Mono.fromCallable(() -> {
            sleep(30);                                           // 模拟一次批量 insert
            written.addAndGet(batch.size());
            return batch.size();
        }).subscribeOn(Schedulers.boundedElastic());
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

输出（5 批：20/20/20/20/15）：

```text
batch=20
batch=20
batch=20
batch=20
batch=15
total=95 cost=2xx ms
```

要点：`concatMap` 而不是 `flatMap`——批量写通常不是线程安全的，串行能保证顺序且避免锁竞争；
真正的吞吐靠"批大小"而不是"并发度"。

## 案例 5：带退避与错误过滤的重试

**问题**：下游偶发超时，但 4xx 这类业务错误重试没有意义，还会放大故障。

```java
import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

public class Case5RetryBackoff {

    private static final AtomicInteger attempts = new AtomicInteger();

    public static void main(String[] args) {
        Mono<String> call = Mono.defer(Case5RetryBackoff::flakyRemote)
                .retryWhen(Retry.backoff(3, Duration.ofMillis(50))     // 最多 3 次，首次退避 50ms
                        .maxBackoff(Duration.ofSeconds(1))
                        .filter(Case5RetryBackoff::isRetryable)         // 业务异常不重试
                        .doBeforeRetry(rs -> System.out.println(
                                "retry #" + rs.totalRetries() + " after " + rs.failure().getMessage())))
                .onErrorResume(err -> Mono.just("fallback(" + err.getClass().getSimpleName() + ")"));

        System.out.println("result=" + call.block() + ", attempts=" + attempts.get());
    }

    /** 前两次失败，第三次成功 */
    static Mono<String> flakyRemote() {
        int n = attempts.incrementAndGet();
        if (n < 3) {
            return Mono.error(new java.io.IOException("read timeout"));
        }
        return Mono.just("ok@" + n);
    }

    static boolean isRetryable(Throwable t) {
        return !(t instanceof IllegalArgumentException);
    }
}
```

输出（注意 `totalRetries()` 从 0 开始计数）：

```text
retry #0 after read timeout
retry #1 after read timeout
result=ok@3, attempts=3
```

要点：`Mono.defer` 是必须的——否则 `flakyRemote()` 在装配阶段就被调用一次，
`attempts` 的计数与"重试了几次"完全对不上，这也是很多人误以为"retry 没生效"的根因。

## 案例 6：`Sinks` 做应用内事件广播

**问题**：多个模块要感知同一件事（配置刷新、缓存失效），但不想引入消息队列。

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

import java.time.Duration;

public class Case6EventBus {

    /** 广播 + 缓冲：启动期没有订阅者也不会丢事件 */
    private static final Sinks.Many<String> BUS =
            Sinks.many().multicast().onBackpressureBuffer(128);

    public static void main(String[] args) {
        Flux<String> events = BUS.asFlux();

        events.filter(e -> e.startsWith("cache"))
              .subscribe(e -> System.out.println("[cache] " + e));

        events.filter(e -> e.startsWith("config"))
              .subscribe(e -> System.out.println("[config] " + e));

        publish("cache:evict:user-1");
        publish("config:reload");

        BUS.emitComplete(Sinks.EmitFailureHandler.FAIL_FAST);
    }

    static void publish(String event) {
        // tryEmitNext 返回 EmitResult，失败可判定（这是 Sinks 相对旧 Processor 的关键改进）
        Sinks.EmitResult r = BUS.tryEmitNext(event);
        if (r.isFailure()) {
            System.out.println("publish failed: " + r);
            return;
        }
        // 若确有多个线程并发 publish，改用下面这行：它对 FAIL_NON_SERIALIZED 自旋重试，
        // 返回 void，所以失败处理要放进 EmitFailureHandler 里
        // BUS.emitNext(event, Sinks.EmitFailureHandler.busyLooping(Duration.ofSeconds(1)));
    }
}
```

输出：

```text
[cache] cache:evict:user-1
[config] config:reload
```

要点：**`asFlux()` 只调用一次并复用**同一个 `Flux` 给所有下游（示例里赋给局部变量后 filter 两次），
每次 `asFlux()` 都新订阅一遍在 `unicast` 模式下会直接报错。

## 案例 7：大模型流式输出（token 流）

**问题**：诊断助手要边生成边显示，且首 token 迟迟不来时要能中断降级。

```java
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

public class Case7LlmStreaming {

    public static void main(String[] args) {
        StringBuilder shown = new StringBuilder();
        AtomicInteger tokenCount = new AtomicInteger();

        Flux<String> answer = diagnosisStream("主诉胸痛3小时，伴出汗");

        String full = answer
                // 任意两个 token 间隔超过 800ms 视为推理卡住
                .timeout(Duration.ofMillis(800))
                .doOnNext(t -> {
                    shown.append(t);
                    tokenCount.incrementAndGet();
                    System.out.print(t);            // 增量输出（生产里是 SSE/WebSocket 写回）
                    System.out.flush();
                })
                .onErrorResume(err -> Mono.just("\n[推理中断: " + err.getClass().getSimpleName() + "]"))
                .doOnTerminate(() -> System.out.println("\n--- tokens=" + tokenCount.get()))
                // 用 then 把"整段文本"作为结果带回：blockLast() 只会返回最后一个 token
                .then(Mono.fromSupplier(shown::toString))
                .block();

        System.out.println("最终文本长度: " + full.length()
                + ", 已输出长度: " + shown.length());
    }

    /** 模拟 LLM 逐 token 返回；用 delayElements 制造真实间隔 */
    static Flux<String> diagnosisStream(String complaint) {
        return Flux.just("根据", "主诉", "（", complaint, "）", "建议", "先", "排除", "急性冠脉综合征")
                .delayElements(Duration.ofMillis(80));
    }
}
```

输出（增量打印，最后两行是统计）：

```text
根据主诉（主诉胸痛3小时，伴出汗）建议先排除急性冠脉综合征
--- tokens=9
最终文本长度: 29, 已输出长度: 29
```

要点：

- `timeout` 作用在**信号间隔**上，正好对应"首 token 超时"与"生成中断"两种线上故障。
- 用 `doOnNext` 做增量推送（SSE）；`block()` 只为在 `main` 里等流结束，在 WebFlux 里应直接
  返回 `Flux<String>` 并配 `MediaType.TEXT_EVENT_STREAM_VALUE`。
- **要拿"整段文本"必须用 `then(Mono.fromSupplier(...))`**：`blockLast()` 返回的是**最后一个元素**，
  不是累积结果，这是流式场景里很容易踩的一个坑。
- 别忘了 `doFinally` 里记录 `CANCEL`——用户关页面时流会被取消，这是统计"用户中途放弃"的唯一信号。

## 案例 8：用 StepVerifier 做协议级断言

**问题**：异步代码用 `block()` + `assertEquals` 断言，只能验证"最后一个值"，验不出信号顺序与背压。

```java
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;
import reactor.test.publisher.TestPublisher;

import java.time.Duration;

class Case8StepVerifierTest {

    @Test
    void 过滤与映射_应保序且正常完成() {
        Flux<String> result = Flux.just("A-1", "B-2", "A-3")
                .filter(id -> id.startsWith("A"))
                .map(String::toLowerCase);

        StepVerifier.create(result)
                .expectNext("a-1", "a-3")
                .verifyComplete();
    }

    @Test
    void 异常应被转成降级值() {
        Mono<String> guarded = Mono.<String>error(new IllegalStateException("boom"))
                .onErrorReturn("fallback");

        StepVerifier.create(guarded)
                .expectNext("fallback")
                .verifyComplete();
    }

    @Test
    void 超时_用虚拟时间验证而不真的等待() {
        // 关键：Mono.delay / timeout 在"装配时"就捕获了调度器实例，
        // 所以必须把流的创建放进 withVirtualTime 的 lambda 里，否则虚拟时间不生效——测试会真的等 30 分钟
        StepVerifier.withVirtualTime(() ->
                        Mono.delay(Duration.ofMinutes(30)).timeout(Duration.ofMinutes(29)))
                .thenAwait(Duration.ofMinutes(30))
                .expectError(java.util.concurrent.TimeoutException.class)
                .verify();
    }

    @Test
    void 手动控制信号_验证背压下的转换() {
        TestPublisher<Integer> publisher = TestPublisher.create();

        StepVerifier.create(publisher.flux().map(i -> i * 2))
                .then(() -> publisher.next(1, 2))
                .expectNext(2, 4)
                .then(() -> publisher.complete())
                .verifyComplete();
    }
}
```

要点：`then(...)` 用来在断言序列中间插入"触发动作"（推一个信号、检查某个副作用），
这是 `StepVerifier` 相比 `assertEquals` 的核心增量能力——它能断言**时间轴上的事件顺序**。

## 与相关概念的关系

- [[03-usage|使用指南]]：本篇每个案例对应的操作符语义与陷阱。
- [[04-sink|Sink 组件]]：案例 6 的多播语义选择依据。
- [[07-applications|应用场景]]：这些案例在 WebFlux/Gateway/流式 AI 里的实际位置。
- [[01-concepts|核心概念]]：案例 1、3、4 都在验证 Scheduler 与背压这两块地基。

## 参考

- [Reactor 官方示例集（reactor-core 源码 `src/test`）](https://github.com/reactor/reactor-core/tree/main/reactor-core/src/test/java/reactor/core/publisher)
- [StepVerifier Javadoc](https://projectreactor.io/docs/core/release/api/reactor/test/StepVerifier.html)
