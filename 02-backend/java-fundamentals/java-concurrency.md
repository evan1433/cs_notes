---
title: Java 并发编程（CompletableFuture）
description: CompletableFuture 异步编排进阶：创建任务、链式组合、超时与取消、异常处理、并发度控制，以及商品详情页聚合、异步重试等生产实战
tags:
  - java
  - concurrency
  - completable-future
  - backend
date: 2026-11-13
---

> 前置知识：[[java-multithreading|Java 多线程基础]]、[[java-thread-pool|Java 线程池]]

# Java 并发编程（CompletableFuture）

`CompletableFuture` 解决的是**编排**问题，不是"怎么开线程"的问题：线程怎么来交给线程池（见
[[java-thread-pool|Java 线程池]]），而"三个远程调用怎么并行发起、结果怎么拼、某个失败了怎么降级、
整体超时了怎么办"——这些把它写成一条声明式调用链就行，不用嵌套回调、不用手工计数。

本文的代码块都已实际编译运行过（`javac --release 17`，3.2 的 `state()` 用 JDK 21），输出为实测值；涉及 JDK 9+ 才有的 API 会单独标注。

参考：

- https://redspider.gitbook.io/concurrent
- [CompletableFuture](https://juejin.cn/post/7455561985378598951)

---

## 一、为什么需要 CompletableFuture

### 1.1 Future 的三处硬伤

`Future`（Java 5 就有了）只解决了"异步执行"，没解决"异步编排"：

| 硬伤 | 表现 | CompletableFuture 的解法 |
|------|------|--------------------------|
| 取结果只能阻塞 | `get()` 把调用线程按住；没有"结果到了叫我"的机制 | `thenApply` / `thenAccept` 注册回调，由完成线程驱动往下走 |
| 无法组合 | 三个 Future"全部完成后统一处理"只能手工 `get` 三次或自己数 `CountDownLatch` | `allOf` / `thenCombine` / `thenCompose` |
| 没有异常语义 | 异常被塞进 `ExecutionException`，只有 `get()` 的那一刻能感知 | `exceptionally` / `handle` 在链上统一收口 |

### 1.2 商品详情页的骨架

四个下游服务各自可独立查询，页面要等四份数据齐了才能渲染——这是 `CompletableFuture` 最典型的用法：

```java
CompletableFuture<ProductInfo> productFuture = CompletableFuture.supplyAsync(() -> getProductInfo());

CompletableFuture<Stock> stockFuture = CompletableFuture.supplyAsync(() -> getStock());

CompletableFuture<Promotion> promotionFuture = CompletableFuture.supplyAsync(() -> getPromotion());

CompletableFuture<Comments> commentsFuture = CompletableFuture.supplyAsync(() -> getComments());

CompletableFuture.allOf(productFuture, stockFuture, promotionFuture, commentsFuture)
    .thenAccept(v -> {
        // 所有数据都准备好了，开始组装页面
        buildPage(productFuture.join(), stockFuture.join(),
                 promotionFuture.join(), commentsFuture.join());
    });

```

（业务类型与 `getProductInfo()` 等方法省略，只保留编排骨架；下一节是可直接运行的完整版。）

另外注意这四行都没传 `Executor`，等于全部丢进 `commonPool`——真实代码请按 2.4 指定业务线程池。

### 1.3 补成可运行版本

```java
import java.util.concurrent.*;

public class CfFutureVsCf {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(4, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });

        // ---------- ① 串行：三次远程调用依次等待 ----------
        long t0 = System.currentTimeMillis();
        String serial = call("profile", 200) + " / " + call("score", 180) + " / coupons=" + couponCount(220);
        System.out.println("[串行]   " + serial + "  cost=" + (System.currentTimeMillis() - t0) + "ms");

        // ---------- ② 传统 Future：能并行，但"取结果"只能阻塞，且无法声明式降级 ----------
        long t1 = System.currentTimeMillis();
        Future<String> profile = pool.submit(() -> call("profile", 200));
        Future<String> score = pool.submit(() -> call("score", 180));
        Future<Integer> coupons = pool.submit(() -> couponCount(220));
        String viaFuture = profile.get() + " / " + score.get() + " / coupons=" + coupons.get();
        System.out.println("[Future] " + viaFuture + "  cost=" + (System.currentTimeMillis() - t1) + "ms");

        // ---------- ③ CompletableFuture：结果一到就往下走，组合与降级都是链上的一环 ----------
        long t2 = System.currentTimeMillis();
        CompletableFuture<String> f1 = CompletableFuture.supplyAsync(() -> call("profile", 200), pool);
        CompletableFuture<String> f2 = CompletableFuture.supplyAsync(() -> call("score", 180), pool);
        CompletableFuture<Integer> f3 = CompletableFuture.supplyAsync(() -> couponCount(220), pool);
        String viaCf = CompletableFuture.allOf(f1, f2, f3)
                .thenApply(v -> f1.join() + " / " + f2.join() + " / coupons=" + f3.join())
                .orTimeout(500, TimeUnit.MILLISECONDS)
                .exceptionally(err -> "降级页：" + err.getClass().getSimpleName())
                .join();
        System.out.println("[CF]     " + viaCf + "  cost=" + (System.currentTimeMillis() - t2) + "ms");

        pool.shutdown();
    }

    static String call(String name, long ms) {
        sleep(ms);
        return name;
    }

    static int couponCount(long ms) {
        sleep(ms);
        return 3;
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

输出（三个下游分别耗时 200/180/220ms，一次实测值，绝对数值随机器浮动）：

```text
[串行]   profile / score / coupons=3  cost≈630ms
[Future] profile / score / coupons=3  cost≈233ms
[CF]     profile / score / coupons=3  cost≈228ms
```

这里有个容易误解的地方值得先说清楚：

- **并行收益来自线程池，不来自 CompletableFuture**。`Future` 版同样是 233ms，跟 CF 版差在毫秒级噪声内。
- CF 的增量在于**可读性与可组合性**：`Future` 版后面想加"整体 500ms 超时 + 降级"必须再包一层
  `get(timeout)` + `try-catch` + `cancel`，而 CF 版就是链上多挂 `orTimeout` 与 `exceptionally` 两个方法。
- `allOf(...).thenApply(v -> f1.join())` 里的 `join` **不会阻塞**——`allOf` 保证所有子任务都已完成，
  此时取结果只是读内存。`allOf` 本身只返回 `CompletableFuture<Void>`，要结果必须自己回捞。

---

## 二、创建异步任务的花式方法

### 2.1 supplyAsync 与 runAsync

```java
// supplyAsync：我做事靠谱，一定给你返回点什么
CompletableFuture<String> future1 = CompletableFuture.supplyAsync(() -> {
    return "我是有结果的异步任务";
});

// runAsync：我比较佛系，不想给你返回任何东西
CompletableFuture<Void> future2 = CompletableFuture.runAsync(() -> {
    System.out.println("我只是默默地执行，不给你返回值");
});

```

| 方法 | 返回 | 任务抛异常时 |
|------|------|--------------|
| `supplyAsync(Supplier<U>)` | `CompletableFuture<U>` | future 异常完成，异常在 `join/get` 或后续 `exceptionally` 处暴露 |
| `runAsync(Runnable)` | `CompletableFuture<Void>` | 同上；`Void` 只能通过异常是否发生来传递信息 |

两者的重载都可以传 `Executor`。**不传就用 `ForkJoinPool.commonPool()`**，见 2.4。

### 2.2 自定义线程池的正确姿势

```java
// 错误示范：这是一匹脱缰的野马！
ExecutorService wrongPool = Executors.newFixedThreadPool(10);

// 正确示范：这才是精心调教过的千里马
ThreadPoolExecutor rightPool = new ThreadPoolExecutor(
    5,                      // 核心线程数（正式员工）
    10,                     // 最大线程数（含临时工）
    60L,                    // 空闲线程存活时间
    TimeUnit.SECONDS,       // 时间单位
    new LinkedBlockingQueue<>(100),  // 工作队列（候客区）
    new ThreadFactoryBuilder().setNameFormat("async-pool-%d").build(),  // 线程工厂（员工登记处）
    new ThreadPoolExecutor.CallerRunsPolicy()  // 拒绝策略（客满时的处理方案）
);

// 使用自定义线程池
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    return "我是通过专属线程池执行的任务";
}, rightPool);

```

`ThreadFactoryBuilder` 来自 Guava。项目里没有 Guava 就手写一个，效果一样且没有额外依赖：

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class PoolFactory {

    /** 命名 + 守护线程 + 未捕获异常兜底，三件事一个工厂全办 */
    static ThreadFactory namedFactory(String prefix, boolean daemon) {
        AtomicInteger seq = new AtomicInteger();
        return r -> {
            Thread t = new Thread(r, prefix + "-" + seq.incrementAndGet());
            t.setDaemon(daemon);
            t.setUncaughtExceptionHandler((thread, ex) ->
                    System.err.println("[" + thread.getName() + "] 未捕获异常: " + ex));
            return t;
        };
    }

    public static void main(String[] args) {
        ExecutorService pool = new ThreadPoolExecutor(
                5, 10, 60L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(100),
                namedFactory("async-pool", true),
                new ThreadPoolExecutor.CallerRunsPolicy());

        System.out.println(CompletableFuture.supplyAsync(
                () -> "线程名=" + Thread.currentThread().getName(), pool).join());
        pool.shutdown();
    }
}
```

参数怎么定（核心线程数、队列容量、拒绝策略）在 [[java-thread-pool|Java 线程池]] 里有完整推导，
这里只强调一点：**异步编排用的池要和同步业务池分开**，否则慢下游会把同步请求一起拖死。

### 2.3 现成结果、失败结果与延迟执行

```java
import java.util.concurrent.*;

public class CfCreate {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });

        // supplyAsync：有返回值
        CompletableFuture<String> withResult = CompletableFuture.supplyAsync(() -> "查到的商品", pool);

        // runAsync：只关心"做完了"，不关心结果
        CompletableFuture<Void> fireAndForget = CompletableFuture.runAsync(
                () -> System.out.println("埋点上报完成"), pool);

        // 已经是现成结果：省掉一次线程切换，常用于短路分支与单测
        CompletableFuture<String> cached = CompletableFuture.completedFuture("命中本地缓存");

        // 已经是失败结果：JDK 9+，用于"提前失败"的分支
        CompletableFuture<String> failed = CompletableFuture.failedFuture(new IllegalStateException("库存服务不可用"));

        // 延迟执行：JDK 9+，等价于 ScheduledExecutorService 的一次性任务
        Executor delayed = CompletableFuture.delayedExecutor(100, TimeUnit.MILLISECONDS, pool);
        CompletableFuture<String> later = CompletableFuture.supplyAsync(() -> "100ms 后才跑", delayed);

        System.out.println(withResult.join());
        System.out.println(cached.join());
        System.out.println(later.join());
        System.out.println("failed.isCompletedExceptionally = " + failed.isCompletedExceptionally());
        fireAndForget.join();
        pool.shutdown();
    }
}
```

输出：

```text
埋点上报完成
查到的商品
命中本地缓存
100ms 后才跑
failed.isCompletedExceptionally = true
```

`completedFuture` / `failedFuture` 看着不起眼，但它们是**消除分支**的关键：让"命中缓存"和"回源查询"
返回同一个类型，调用方不用写 `if (cached)` 两套逻辑。`delayedExecutor` 则是实现异步重试退避的现成积木（见 6.2）。

### 2.4 默认线程池的陷阱

不传 `Executor` 时用 `ForkJoinPool.commonPool()`——**JVM 全局共享**，并行度只有 `CPU 核数 - 1`。
一个慢 SQL 就能让全应用所有 `supplyAsync` / `parallelStream` 一起排队。完整的故障分析与参数推导见
[[java-thread-pool#十五、CompletableFuture 的默认线程池陷阱|线程池笔记第十五节]]，结论只有一句：

```java
// 危险：IO 型任务占满 commonPool，故障面放大到整个 JVM
CompletableFuture.supplyAsync(() -> callRemoteService());

// 正确：始终显式传入专用线程池
CompletableFuture.supplyAsync(() -> callRemoteService(), bizExecutor);
```

---

## 三、结果的获取与状态

### 3.1 get / join / getNow

| 方法 | 是否阻塞 | 异常形态 | 响应中断 | 适用 |
|------|----------|----------|----------|------|
| `get()` | 是 | 受检 `ExecutionException` / `InterruptedException` | **是** | 需要响应中断的边界代码 |
| `get(timeout, unit)` | 是，最长等 timeout | 同上 + `TimeoutException` | 是 | 同步场景的最后一道等待 |
| `join()` | 是 | 非受检 `CompletionException` | **否** | lambda 里用（不引入 checked 异常） |
| `getNow(T)` | 否 | 未完成直接返回默认值 | — | 降级读取、埋点采样 |

`join` 不响应中断这点是实测出来的：

```java
import java.util.concurrent.*;

public class JoinVsGet {

    public static void main(String[] args) throws Exception {
        CompletableFuture<String> never = new CompletableFuture<>();

        Thread joiner = new Thread(() -> {
            never.join();                       // join 不响应中断，会一直等下去
            System.out.println("joiner 结束");
        }, "joiner");
        joiner.setDaemon(true);
        joiner.start();
        Thread.sleep(100);
        joiner.interrupt();
        joiner.join(500);
        System.out.println("A. interrupt 之后 joiner 还活着？ " + joiner.isAlive());

        Thread getter = new Thread(() -> {
            try {
                never.get();                    // get 会抛 InterruptedException
            } catch (InterruptedException e) {
                System.out.println("B. get 抛出了 InterruptedException");
            } catch (ExecutionException e) {
                System.out.println("B. get 抛出了 ExecutionException");
            }
        }, "getter");
        getter.setDaemon(true);
        getter.start();
        Thread.sleep(100);
        getter.interrupt();
        getter.join(500);
        System.out.println("B. interrupt 之后 getter 还活着？ " + getter.isAlive());
    }
}
```

输出：

```text
A. interrupt 之后 joiner 还活着？ true
B. get 抛出了 InterruptedException
B. interrupt 之后 getter 还活着？ false
```

所以在"优雅停机"这类需要响应中断的地方不要用 `join()` 干等。

### 3.2 状态查询

| 方法                           | 含义                                                      |
| ---------------------------- | ------------------------------------------------------- |
| `isDone()`                   | 已完成（正常完成、异常完成、被取消都算 `true`）                             |
| `isCompletedExceptionally()` | 异常完成或被取消                                                |
| `isCancelled()`              | 被取消                                                     |
| `state()`（JDK 19+）           | `RUNNING` / `SUCCESS` / `FAILED` / `CANCELLED`，一次拿到精确状态 |

```java
import java.util.concurrent.*;

public class StateDemo {
    public static void main(String[] args) {
        CompletableFuture<String> running = new CompletableFuture<>();
        CompletableFuture<String> failed = CompletableFuture.failedFuture(new IllegalStateException("x"));
        CompletableFuture<String> done = CompletableFuture.completedFuture("v");

        System.out.println("刚创建   -> " + running.state() + ", isDone=" + running.isDone());
        System.out.println("失败     -> " + failed.state() + ", isCompletedExceptionally=" + failed.isCompletedExceptionally());
        System.out.println("已完成   -> " + done.state());

        running.cancel(false);
        System.out.println("取消后   -> " + running.state() + ", isCancelled=" + running.isCancelled());
    }
}
```

输出（JDK 21）：

```text
刚创建   -> RUNNING, isDone=false
失败     -> FAILED, isCompletedExceptionally=true
已完成   -> SUCCESS
取消后   -> CANCELLED, isCancelled=true
```

JDK 17 及以下没有 `state()`，就用 `isDone` / `isCompletedExceptionally` / `isCancelled` 三者组合。

### 3.3 异步任务的超时处理

三种写法语义完全不同，别混用：

```java
import java.util.concurrent.*;

public class CfTimeout {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });

        // ① get(timeout)：阻塞等待，超时抛 TimeoutException——任务本身不会停
        CompletableFuture<String> f1 = CompletableFuture.supplyAsync(() -> slow("A", 500), pool);
        try {
            System.out.println("① " + f1.get(200, TimeUnit.MILLISECONDS));
        } catch (TimeoutException e) {
            System.out.println("① get(200ms) 超时；任务仍在后台跑，f1.isDone=" + f1.isDone());
        }

        // ② orTimeout：超时把 future 置为"异常完成"，cause 是 TimeoutException
        CompletableFuture<String> f2 = CompletableFuture.supplyAsync(() -> slow("B", 500), pool)
                .orTimeout(200, TimeUnit.MILLISECONDS)
                .exceptionally(err -> "② 降级值（cause=" + causeOf(err).getClass().getSimpleName() + "）");
        System.out.println(f2.join());

        // ③ completeOnTimeout：超时用默认值补齐，不抛异常，链路继续往下走
        CompletableFuture<String> f3 = CompletableFuture.supplyAsync(() -> slow("C", 500), pool)
                .completeOnTimeout("③ 默认值", 200, TimeUnit.MILLISECONDS);
        System.out.println(f3.join());

        Thread.sleep(400);   // 等后台任务收尾，观察它们其实都跑完了
        pool.shutdown();
    }

    static String slow(String tag, long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        return tag + "-完成";
    }

    static Throwable causeOf(Throwable t) {
        return t.getCause() == null ? t : t.getCause();
    }
}
```

输出：

```text
① get(200ms) 超时；任务仍在后台跑，f1.isDone=false
② 降级值（cause=TimeoutException）
③ 默认值
```

| 写法 | 调用线程 | 超时后 future 状态 | 底层任务 | 典型场景 |
|------|----------|--------------------|----------|----------|
| `get(timeout)` | 被阻塞 | 不变（仍 RUNNING） | 继续跑 | 兜底等待、批处理作业 |
| `orTimeout` | 不阻塞 | 异常完成，cause=`TimeoutException` | 继续跑，结果被丢弃 | 需要"超时就当失败"的链路 |
| `completeOnTimeout` | 不阻塞 | 正常完成，值是默认值 | 继续跑，结果被丢弃 | 弱依赖（推荐位、计数、日志） |

**不要把它们串联在同一个 future 上**，两个定时器都会生效，谁先到谁说话：

```java
// 反例：以为"先给默认值，再兜一层超时"，实际是两个定时器赛跑
CompletableFuture<String> chained = f3
        .completeOnTimeout("fallback", 100, TimeUnit.MILLISECONDS)   // 100ms
        .orTimeout(50, TimeUnit.MILLISECONDS);                      // 50ms ← 先触发，直接异常
```

实测结果是 `CompletionException(cause=TimeoutException)`，`fallback` 根本没机会生效。想表达"超时先降级、
再没有任何兜底就报错"，应该是二选一，或者分层用（子任务 `completeOnTimeout`，整体 `orTimeout`，见 6.1）。

### 3.4 cancel 为什么不打断任务

这是 CompletableFuture 最反直觉的地方：

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

public class CancelDemo {

    public static void main(String[] args) throws Exception {
        AtomicReference<String> outcome = new AtomicReference<>("(未设置)");
        CountDownLatch started = new CountDownLatch(1);

        CompletableFuture<String> f = CompletableFuture.supplyAsync(() -> {
            started.countDown();
            try {
                Thread.sleep(600);
                outcome.set("跑完了");
            } catch (InterruptedException e) {
                outcome.set("被中断");
            }
            return "done";
        });

        started.await();
        System.out.println("cancel(true) -> " + f.cancel(true) + ", isCancelled=" + f.isCancelled());
        try {
            f.join();
        } catch (CancellationException e) {
            System.out.println("join -> CancellationException");
        }

        Thread.sleep(900);
        System.out.println("底层任务实际结果 = " + outcome.get());
    }
}
```

输出：

```text
cancel(true) -> true, isCancelled=true
join -> CancellationException
底层任务实际结果 = 跑完了
```

`mayInterruptIfRunning` 这个参数对 `CompletableFuture` **完全没有作用**——它只把 future 状态翻成
`CANCELLED`，正在跑的 lambda 毫不知情。对比一下传统 `FutureTask`（`pool.submit(...)` 返回的），
同样 `cancel(true)`，底层任务实测**会被中断**，`sleep` 抛 `InterruptedException`。

想真正停掉任务，只能靠这三条：

| 手段 | 做法 | 限制 |
|------|------|------|
| 中断协作 | 任务内部轮询 `Thread.currentThread().isInterrupted()` | 阻塞调用必须可中断（`sleep`/`wait`/`take`） |
| 协议级取消 | 用支持取消的客户端：`OkHttp Call.cancel()`、JDBC `Statement.cancel()` | 依赖具体客户端能力 |
| 结果丢弃 | `orTimeout` + 不再消费结果 | 任务仍占线程与连接，只是不阻塞调用方 |

生产上最常见的是第三条——**"取消"往往只是"我不等了"，而不是"你别干了"**。要真正省下资源，
得把超时控制下沉到 HTTP/RPC 客户端。

---

## 四、链式调用的艺术

### 4.1 thenApply、thenAccept、thenRun 的区别

```java
CompletableFuture.supplyAsync(() -> "Hello")
    .thenApply(s -> {
        // 我是加工工人，负责把材料加工后返回新成品
        return s + " World";
    })
    .thenAccept(result -> {
        // 我是检验工人，只负责验收，不返回东西
        System.out.println("收到结果: " + result);
    })
    .thenRun(() -> {
        // 我是打扫工人，不关心之前的结果，只负责收尾工作
        System.out.println("生产线工作完成，开始打扫");
    });

```

| 方法 | 入参 | 返回 | 用途 |
|------|------|------|------|
| `thenApply(fn)` | 上一步的值 | `CF<新值>` | 类型转换、加工 |
| `thenAccept(fn)` | 上一步的值 | `CF<Void>` | 消费（打印、写库、发 MQ） |
| `thenRun(rn)` | 无 | `CF<Void>` | 收尾（埋点、释放资源） |

三个方法也都有 `*Async` 重载。区别只在于**在哪个线程执行**，语义完全一样。

### 4.2 同步阶段到底跑在哪个线程

这是排查"线程池明明配了 8 个，为什么只用一个线程"类问题的关键，实测结论：

| 阶段 | 执行线程 |
|------|----------|
| `supplyAsync(..., pool)` | `pool` 的线程 |
| `thenApply`（注册时上游**未**完成） | **完成上游的那个线程**（这里是 `biz-pool`），不会再切一次 |
| `thenApply`（注册时上游**已**完成） | **注册者自己**（谁调用谁执行，这里是 `main`） |
| `thenApplyAsync`（不带 Executor） | `ForkJoinPool.commonPool-worker-N` |
| `thenApplyAsync(..., pool)` | `pool` 的线程 |

```java
import java.util.concurrent.*;

public class ThreadDemo {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });
        System.out.println("main thread = " + Thread.currentThread().getName());

        // 上游先睡 100ms，保证 main 在它完成之前就注册好了后续阶段
        CompletableFuture.supplyAsync(() -> {
                    sleep(100);
                    System.out.println("supplyAsync    on " + Thread.currentThread().getName());
                    return "x";
                }, pool)
                .thenApply(s -> {
                    System.out.println("thenApply      on " + Thread.currentThread().getName());
                    return s;
                })
                .thenApplyAsync(s -> {
                    System.out.println("thenApplyAsync on " + Thread.currentThread().getName());
                    return s;
                })
                .join();

        // 上游早已完成时，同步阶段由注册者执行
        CompletableFuture.completedFuture("v")
                .thenApply(s -> {
                    System.out.println("completedFuture+thenApply on " + Thread.currentThread().getName());
                    return s;
                })
                .join();
        pool.shutdown();
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

输出：

```text
main thread = main
supplyAsync    on biz-pool
thenApply      on biz-pool
thenApplyAsync on ForkJoinPool.commonPool-worker-1
completedFuture+thenApply on main
```

两条实践推论：

1. **同步阶段是"零成本"的**——不切线程，在完成线程上顺着执行。适合轻量的转换/判断。
2. **同步阶段里不要做阻塞操作**。它跑在池线程上，一阻塞就等于占着线程池的名额；这跟"IO 要切线程"是同一件事。

### 4.3 异步转换：thenApplyAsync 的使用场景

```java
CompletableFuture.supplyAsync(() -> {
    // 模拟获取用户信息
    return "用户基础信息";
}).thenApplyAsync(info -> {
    // 耗时的处理操作，在新的线程中执行
    try {
        Thread.sleep(1000);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
    return info + " + 附加信息";
}, customExecutor);  // 可以指定自己的线程池

```

这里的 `customExecutor` 就是 2.2 里的 `rightPool`。判断标准很简单：

| 场景 | 用哪个 |
|------|--------|
| 纯内存计算、字段映射（微秒级） | `thenApply` |
| 要发 HTTP / 查 DB / 读文件（毫秒级以上） | `thenApplyAsync(..., pool)`——**必须显式传池** |
| 完全不想关心线程 | 接受 `commonPool`（仅限 CPU 密集型小任务） |

### 4.4 组合多个异步操作：thenCompose vs thenCombine

`thenCompose` 用于**串行依赖**：第二步要等第一步的结果，而且第二步本身也是异步的。
如果误用 `thenApply`，会得到 `CompletableFuture<CompletableFuture<T>>` 这种嵌套结构。

```java
CompletableFuture<String> getUserEmail(String userId) {
    return CompletableFuture.supplyAsync(() -> "user@example.com");
}

CompletableFuture<String> future = CompletableFuture
    .supplyAsync(() -> "userId")
    .thenCompose(userId -> getUserEmail(userId));  // 基于第一个结果去获取邮箱

```

`thenCombine` 用于**并行汇合**：两个 future 互不依赖，但要拿双方结果做一次合并。

| 方法 | 关系 | 入参 | 返回 |
|------|------|------|------|
| `thenCompose(fn)` | 串行（后者依赖前者） | `T -> CompletionStage<U>` | `CF<U>`（已拍平） |
| `thenCombine(other, fn)` | 并行（两者独立） | `(T, U) -> V` | `CF<V>` |
| `thenApply(fn)` | 就地变换 | `T -> U` | `CF<U>` |

记住口诀：**要等结果再造一个异步 → `thenCompose`；两个异步都有结果了要合并 → `thenCombine`；
同步改一下值 → `thenApply`**。

### 4.5 多任务聚合：allOf 与 anyOf

```java
import java.util.concurrent.*;
import java.util.List;

public class CfChain {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(4, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });

        // ① 三段式：变换 -> 消费 -> 收尾
        CompletableFuture.supplyAsync(() -> "Hello", pool)
                .thenApply(s -> s + " World")                        // 有入参有返回值
                .thenAccept(s -> System.out.println("① 消费: " + s))  // 有入参无返回值
                .thenRun(() -> System.out.println("① 收尾: 日志/指标")) // 无入参无返回值
                .join();

        // ② thenCompose：把"嵌套的 Future"拍平（串行依赖）
        String avatar = CompletableFuture.supplyAsync(() -> "u-1", pool)
                .thenCompose(CfChain::loadEmail)       // Function<T, CompletionStage<U>>
                .thenCompose(CfChain::loadAvatar)
                .join();
        System.out.println("② compose 结果: " + avatar);

        // ③ thenCombine：两个独立 Future 汇合（并行无依赖）
        String merged = CompletableFuture.supplyAsync(() -> "价格 99", pool)
                .thenCombine(
                        CompletableFuture.supplyAsync(() -> "库存 12", pool),
                        (price, stock) -> price + " / " + stock)
                .join();
        System.out.println("③ combine 结果: " + merged);

        // ④ allOf 收集结果：allOf 只给 Void，要结果得自己 join
        List<CompletableFuture<String>> jobs = List.of(
                CompletableFuture.supplyAsync(() -> "a", pool),
                CompletableFuture.supplyAsync(() -> "b", pool),
                CompletableFuture.supplyAsync(() -> "c", pool));
        List<String> results = CompletableFuture.allOf(jobs.toArray(new CompletableFuture[0]))
                .thenApply(v -> jobs.stream().map(CompletableFuture::join).toList())
                .join();
        System.out.println("④ allOf 结果: " + results);

        // ⑤ anyOf：谁先回用谁，返回 Object，需要自己转型
        Object fastest = CompletableFuture.anyOf(
                CompletableFuture.supplyAsync(() -> speed("slow", 300), pool),
                CompletableFuture.supplyAsync(() -> speed("fast", 80), pool)).join();
        System.out.println("⑤ anyOf 结果: " + fastest);

        pool.shutdown();
    }

    static CompletableFuture<String> loadEmail(String userId) {
        return CompletableFuture.supplyAsync(() -> userId + "@example.com");
    }

    static CompletableFuture<String> loadAvatar(String email) {
        return CompletableFuture.supplyAsync(() -> "avatar(" + email + ")");
    }

    static String speed(String tag, long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        return tag;
    }
}
```

输出：

```text
① 消费: Hello World
① 收尾: 日志/指标
② compose 结果: avatar(u-1@example.com)
③ combine 结果: 价格 99 / 库存 12
④ allOf 结果: [a, b, c]
⑤ anyOf 结果: fast
```

`allOf` 的两个注意点：

- 它是**全部完成**语义，任何一个子任务失败，`allOf` 就是异常完成（`join` 抛 `CompletionException`，
  cause 是那个原始异常）。想让失败不拖累整体，必须在**子任务上**各自 `exceptionally`。
- 它**不收集结果**，只给 `Void`。形如 ④ 的写法是标准姿势：先 `allOf.toArray`，再在 `thenApply` 里逐个 `join`。

### 4.6 方法全景速查

| 方法 | 入参 | 返回 | 上游失败时 |
|------|------|------|------------|
| `thenApply` | `T` | `U` | 跳过我，异常往下传 |
| `thenAccept` | `T` | `Void` | 同上 |
| `thenRun` | 无 | `Void` | 同上 |
| `thenCompose` | `T` | `CompletionStage<U>` | 同上 |
| `thenCombine` | `T`, `U` | `V` | 任一失败即失败 |
| `applyToEither` | `T`, `T` | `U` | 先完成的那个说了算 |
| `exceptionally` | `Throwable` | `T` | **接住**，链恢复 |
| `handle` | `T` / `Throwable` | `U` | **接住**，可换值可换类型 |
| `whenComplete` | `T` / `Throwable` | 原值 | 只观测，不改写既有失败 |

---

## 五、异常处理的技巧

### 5.1 应急的 exceptionally

```java
CompletableFuture<String> future = CompletableFuture
    .supplyAsync(() -> {
        if (Math.random() < 0.5) {
            throw new RuntimeException("服务暂时不可用");
        }
        return "正常返回的数据";
    })
    .exceptionally(throwable -> {
        // 记录异常日志
        log.error("操作失败", throwable);
        // 返回默认值
        return "服务异常，返回默认数据";
    });

```

### 5.2 两全其美的 handle

```java
CompletableFuture<String> future = CompletableFuture
    .supplyAsync(() -> {
        if (Math.random() < 0.5) {
            throw new RuntimeException("模拟服务异常");
        }
        return "原始数据";
    })
    .handle((result, throwable) -> {
        if (throwable != null) {
            log.error("处理异常", throwable);
            return "发生异常，返回备用数据";
        }
        return result + " - 正常处理完成";
    });

```

### 5.3 whenComplete

```java
// whenComplete：只是旁观者，不能修改结果
CompletableFuture<String> future1 = CompletableFuture
    .supplyAsync(() -> "原始数据")
    .whenComplete((result, throwable) -> {
        // 只能查看结果，无法修改
        if (throwable != null) {
            log.error("发生异常", throwable);
        } else {
            log.info("处理完成: {}", result);
        }
    });

// handle：既是参与者又是修改者
CompletableFuture<String> future2 = CompletableFuture
    .supplyAsync(() -> "原始数据")
    .handle((result, throwable) -> {
        // 可以根据结果或异常，返回新的值
        if (throwable != null) {
            return "异常情况下的替代数据";
        }
        return result + " - 已处理";
    });

```

### 5.4 三者对比与实测细节

| 维度 | `exceptionally` | `handle` | `whenComplete` |
|------|-----------------|----------|----------------|
| 成功时是否执行 | 否 | 是 | 是 |
| 能否改变返回值 | 能（兜底值） | 能 | **不能**（返回 `CF<T>`，值透传） |
| 能否把成功改成失败 | 不能（返回不了异常态） | 能（抛异常） | 能（抛异常，但见下） |
| 能否把失败改回成功 | 能 | 能 | **不能** |
| 典型用途 | 降级、默认值 | 统一收口、类型转换 | 打日志、埋点、释放资源 |

`whenComplete` 有一条很容易记错的语义（JDK 规范 + 实测）：

```java
import java.util.concurrent.*;

public class WhenCompleteEdge {

    public static void main(String[] args) {
        // A. 源成功 + 回调抛异常 → 新异常成为结果
        try {
            CompletableFuture.supplyAsync(() -> "ok")
                    .whenComplete((v, err) -> { throw new IllegalStateException("观测代码异常"); })
                    .join();
        } catch (CompletionException e) {
            System.out.println("A. " + e.getCause().getMessage());
        }

        // B. 源失败 + 回调抛异常 → 原异常保留，回调的异常被吞
        try {
            CompletableFuture.supplyAsync(() -> { throw new IllegalStateException("原始异常"); })
                    .whenComplete((v, err) -> { throw new IllegalStateException("观测代码异常"); })
                    .join();
        } catch (CompletionException e) {
            System.out.println("B. " + e.getCause().getMessage());
        }

        // C. handle 抛异常 → 覆盖
        try {
            CompletableFuture.supplyAsync(() -> { throw new IllegalStateException("原始异常"); })
                    .handle((v, err) -> { throw new IllegalStateException("handle 抛的异常"); })
                    .join();
        } catch (CompletionException e) {
            System.out.println("C. " + e.getCause().getMessage());
        }
    }
}
```

输出：

```text
A. 观测代码异常
B. 原始异常
C. handle 抛的异常
```

结论：`whenComplete` 里**别写会抛异常的代码**。源本身就失败时，它抛的异常不会上报，会被静默吞掉——
这就是"日志里只有原始异常，看不到监控代码报错"的根因。

### 5.5 异常怎么"穿透"整条链

一旦某一步失败，后续所有 `thenApply` / `thenAccept` / `thenRun` / `thenCompose` 都会**被跳过**，
异常沿链往下传，直到遇到第一个 `exceptionally` / `handle`。这跟 Stream 的短路很像，区别是短路原因是异常。

```java
import java.util.concurrent.*;

public class ErrorFlow {

    public static void main(String[] args) {
        String result = CompletableFuture.supplyAsync(() -> "step1")
                .thenApply(s -> { throw new IllegalArgumentException("step2 校验失败"); })
                .thenApply(s -> "这一行永远不会执行")
                .thenAccept(s -> System.out.println("这一行也不会执行"))
                .handle((v, err) -> "在 handle 处接住：" + rootCause(err).getMessage())
                .join();
        System.out.println(result);
    }

    /** 一层层剥掉 CompletionException / ExecutionException 的包装 */
    static Throwable rootCause(Throwable t) {
        Throwable cur = t;
        while ((cur instanceof CompletionException || cur instanceof ExecutionException) && cur.getCause() != null) {
            cur = cur.getCause();
        }
        return cur;
    }
}
```

输出：

```text
在 handle 处接住：step2 校验失败
```

两个实践要点：

1. `exceptionally` / `handle` 收到的异常几乎总是被 `CompletionException` 包了一层，日志里要打 `rootCause`，
   否则 `instanceof TimeoutException` 之类的判断永远不成立。
2. 异常如果没有被任何阶段处理，**不会自动打日志**，要等到 `join` / `get` 时才抛出来。如果这条链是
   "发起后就不管了"（fire-and-forget），异常等于凭空消失——必须在链尾挂 `exceptionally` 或 `whenComplete` 兜住。

### 5.6 拒绝"异常被吞"的写法

```java
// 反面：不 join、不接异常，失败了没有任何痕迹
CompletableFuture.runAsync(() -> mqProducer.send(msg), pool);

// 正面：至少留一条日志 + 一个指标
CompletableFuture.runAsync(() -> mqProducer.send(msg), pool)
        .exceptionally(err -> {
            log.error("MQ 发送失败, msg={}", msg, rootCause(err));
            metrics.counter("mq.send.fail").increment();
            return null;               // 已经处理过，返回 null 让链正常结束
        });
```

---

## 六、实战模式

### 6.1 并行聚合 + 双层降级

真实页面的诉求几乎总是"**单个模块挂了降级，整体不能卡住**"。于是需要两层：

- 子任务级 `orTimeout` + `exceptionally`：每个下游都有自己的超时与默认值；
- 整体级 `orTimeout`：防止某个子任务连超时都没触发（例如线程池排队）。

```java
import java.util.concurrent.*;

public class AggregateDemo {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(8, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });
        long t0 = System.currentTimeMillis();

        // 每个子任务自带"局部降级"：超时就给默认值，不让整页挂掉
        CompletableFuture<String> profile = guarded(() -> call("profile", 120), "游客", pool, 300);
        CompletableFuture<String> score = guarded(() -> call("score", 150), "暂无评分", pool, 300);
        CompletableFuture<String> coupons = guarded(() -> call("coupons", 900), "暂无优惠", pool, 300);  // 故意慢

        // 整体再加一道超时兜底 + 统一降级：防止某个子任务卡住整页
        String page = CompletableFuture.allOf(profile, score, coupons)
                .thenApply(v -> "profile=" + profile.join()
                        + " | score=" + score.join()
                        + " | coupons=" + coupons.join())
                .orTimeout(500, TimeUnit.MILLISECONDS)
                .exceptionally(err -> "整页降级：" + err.getClass().getSimpleName())
                .join();

        System.out.println(page);
        System.out.println("cost=" + (System.currentTimeMillis() - t0) + "ms");
        pool.shutdown();
    }

    /** 给单个子任务套上"超时即降级"，保证它一定产出值 */
    static <T> CompletableFuture<T> guarded(Callable<T> task, T fallback,
                                            Executor executor, long timeoutMs) {
        return CompletableFuture.supplyAsync(() -> {
                    try {
                        return task.call();
                    } catch (Exception e) {
                        throw new CompletionException(e);
                    }
                }, executor)
                .orTimeout(timeoutMs, TimeUnit.MILLISECONDS)
                .exceptionally(err -> fallback);
    }

    static String call(String name, long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        return name + "(ok)";
    }
}
```

输出（优惠券服务 900ms，300ms 时降级）：

```text
profile=profile(ok) | score=score(ok) | coupons=暂无优惠
cost≈314ms
```

要点：

- `guarded(...)` 把"超时 + 兜底"封装成一个可复用的算子，调用处一眼能看出**这个下游的降级值是什么**。
  这比在最后统一 `catch` 更好——不同下游的降级语义本来就不同。
- 整体 `orTimeout(500ms)` 是最后一道防线。子任务已经保证 300ms 内有结果，所以这里正常不会触发；
  一旦触发（比如线程池排队），整页走"整页降级"，用户看到的是骨架页而不是白屏转圈。
- `orTimeout` 之后**不要再 `join` 子任务**，否则可能阻塞在没有降级的那个 future 上。

### 6.2 异步重试（带退避）

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

public class RetryDemo {

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });
        AtomicInteger calls = new AtomicInteger();

        // 前两次失败，第三次成功
        String result = retry(() -> CompletableFuture.supplyAsync(() -> {
                    int n = calls.incrementAndGet();
                    if (n < 3) {
                        throw new IllegalStateException("第 " + n + " 次调用超时");
                    }
                    return "第 " + n + " 次成功";
                }, pool),
                3,        // 最多 3 次
                100,      // 退避 100ms
                pool)
                .exceptionally(err -> "重试耗尽：" + rootCause(err).getMessage())
                .join();

        System.out.println(result);
        System.out.println("实际调用次数=" + calls.get());
        pool.shutdown();
    }

    /**
     * 异步重试：失败后延迟 backoffMs 再试，最多 maxAttempts 次。
     * 注意：重试的是"整条链路"，action 内部必须幂等。
     */
    static <T> CompletableFuture<T> retry(Supplier<CompletableFuture<T>> action,
                                          int maxAttempts, long backoffMs, Executor executor) {
        Executor delayed = CompletableFuture.delayedExecutor(backoffMs, TimeUnit.MILLISECONDS, executor);
        return attempt(action, new AtomicInteger(1), maxAttempts, delayed);
    }

    private static <T> CompletableFuture<T> attempt(Supplier<CompletableFuture<T>> action,
                                                    AtomicInteger used, int maxAttempts, Executor delayed) {
        return action.get()
                .handle((value, err) -> {
                    if (err == null) {
                        return CompletableFuture.completedFuture(value);
                    }
                    if (used.get() >= maxAttempts) {
                        return CompletableFuture.<T>failedFuture(rootCause(err));
                    }
                    used.incrementAndGet();
                    System.out.println("失败后第 " + used.get() + " 次尝试，异常：" + rootCause(err).getMessage());
                    // supplyAsync(delayed) 先"空转"等够退避时间，再递归发起下一次
                    return CompletableFuture.<Void>supplyAsync(() -> null, delayed)
                            .thenCompose(x -> attempt(action, used, maxAttempts, delayed));
                })
                .thenCompose(f -> f);
    }

    static Throwable rootCause(Throwable t) {
        Throwable cur = t;
        while ((cur instanceof CompletionException || cur instanceof ExecutionException) && cur.getCause() != null) {
            cur = cur.getCause();
        }
        return cur;
    }
}
```

输出：

```text
失败后第 2 次尝试，异常：第 1 次调用超时
失败后第 3 次尝试，异常：第 2 次调用超时
第 3 次成功
实际调用次数=3
```

三个易错点：

1. `handle` 返回的必须是"扁平"的 `CompletableFuture<T>`，所以外面还得套一层 `thenCompose(f -> f)`，
   不然会得到 `CF<CF<T>>`。
2. 退避用 `delayedExecutor` + 空 `supplyAsync`，**不要 `Thread.sleep`**——那是拿池线程白白睡觉。
3. 重试必须有上限，且只重试**幂等**操作。写操作重试前先确认下游有没有幂等键。

### 6.3 并发度控制：线程池 ≠ 并发上限

线程池大小限制的是"同时有多少任务在跑"，但真正的瓶颈常常在下游（数据库连接数、对方接口的限流）。
用 `Semaphore` 把并发度压在业务侧，比缩小线程池更精准——线程池缩了会影响同一个池里的其它任务。

```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class LimitDemo {

    private static final AtomicInteger running = new AtomicInteger();
    private static final AtomicInteger peak = new AtomicInteger();

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(16, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });
        // 线程池 16 个线程，但下游只允许 4 个并发——并发度由信号量说了算
        Semaphore gate = new Semaphore(4);

        long t0 = System.currentTimeMillis();
        List<CompletableFuture<Void>> jobs = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            jobs.add(CompletableFuture.runAsync(() -> {
                try {
                    gate.acquire();
                    int now = running.incrementAndGet();
                    peak.accumulateAndGet(now, Math::max);
                    try {
                        Thread.sleep(100);              // 模拟一次远程调用
                    } finally {
                        running.decrementAndGet();
                        gate.release();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }, pool));
        }

        CompletableFuture.allOf(jobs.toArray(new CompletableFuture[0])).join();
        System.out.println("20 个任务、并发度 4、每个 100ms -> cost="
                + (System.currentTimeMillis() - t0) + "ms, 观测到的峰值并发=" + peak.get());
        pool.shutdown();
    }
}
```

输出：

```text
20 个任务、并发度 4、每个 100ms -> cost≈524ms, 观测到的峰值并发=4
```

20 个任务 ÷ 并发 4 = 5 批 × 100ms ≈ 500ms，实测 520ms 左右符合预期。

注意 `gate.acquire()` 会**阻塞池线程**：许可数如果配得和线程池一样大，信号量就形同虚设（线程池才是真正的
上限），还会让一批线程白白挂在 `acquire` 上。所以许可数要明显小于池大小，让"排队"发生在信号量而不是线程池。
生产上更彻底的方案是用 `Flux.flatMap(fn, concurrency)`
（见 [[reactor/index|Project Reactor 专题]]）——它在信号层面限流，不占线程。信号量只是没有 Reactor 时的轻量替代。

### 6.4 上下文传递：ThreadLocal 会丢

日志 traceId、用户身份这类 `ThreadLocal` 上下文，一切线程就没了。这不是 CF 的 bug，是线程模型的必然：

```java
import java.util.Map;
import java.util.concurrent.*;

public class ContextDemo {

    /** 模拟 MDC / 用户上下文这类 ThreadLocal */
    static final ThreadLocal<String> TRACE = new ThreadLocal<>();

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2, r -> {
            Thread t = new Thread(r, "biz-pool");
            t.setDaemon(true);
            return t;
        });

        TRACE.set("trace-1234");   // 请求线程里放好上下文

        // ① 直接切线程：上下文丢了
        System.out.println("① 裸传: " + CompletableFuture
                .supplyAsync(() -> "trace=" + TRACE.get(), pool).join());

        // ② 包装 executor：提交任务时抓快照，执行时还原
        System.out.println("② 包装后: " + CompletableFuture
                .supplyAsync(() -> "trace=" + TRACE.get(), contextPropagating(pool)).join());

        pool.shutdown();
    }

    /** 把调用线程的 ThreadLocal 快照带进池线程，用完复原，避免污染下一个任务 */
    static Executor contextPropagating(Executor delegate) {
        return task -> {
            Map<ThreadLocal<?>, Object> snapshot = Map.of(TRACE, TRACE.get());
            delegate.execute(() -> {
                Object previous = TRACE.get();
                TRACE.set((String) snapshot.get(TRACE));
                try {
                    task.run();
                } finally {
                    TRACE.set((String) previous);   // 必须复原，否则线程复用时串味
                }
            });
        };
    }
}
```

输出：

```text
① 裸传: trace=null
② 包装后: trace=trace-1234
```

`finally` 里的复原不能省。线程池的线程会被复用，如果只 set 不清理，下一个请求会读到上一个请求的 traceId，
排查问题时会看到"日志串号"这种灵异现象。框架层已经有现成实现：Spring 的 `TaskDecorator`、
Alibaba `TransmittableThreadLocal`、Micrometer Context Propagation，原理都是"提交时快照、执行时还原、结束清理"。

---

## 七、常见坑汇总

| 现象 | 原因 | 解决 |
|------|------|------|
| 异步任务莫名串行、慢 | 没传 Executor，全部挤在 `commonPool`（并行度 = CPU-1） | 显式传业务线程池 |
| 配了 8 个线程却像单线程 | 同步阶段 `thenApply` 在完成线程上执行，且上游是串行完成的 | 需要并行就用 `*Async(pool)` |
| `cancel(true)` 之后任务还在跑 | CF 的 `cancel` 不中断底层线程 | 见 3.4，用可中断的阻塞调用或协议级取消 |
| 超时后 CPU/连接不降 | `orTimeout` 只是不消费结果，任务仍在跑 | 超时控制下沉到 HTTP/RPC 客户端 |
| 整体卡在 30s | 子任务没有各自超时，整体只能等最慢的 | 子任务 `orTimeout` + 整体 `orTimeout` 双层（6.1） |
| 日志里只有原始异常 | `whenComplete` 里抛的异常在源已失败时被吞 | 监控/日志放 `exceptionally` 或独立 try-catch |
| 抛了 `TimeoutException` 却 `instanceof` 不成立 | 异常被 `CompletionException` 包了一层 | 用 `rootCause` 解包（5.5） |
| 应用不退出 | 线程池没 shutdown，或非守护线程 | 池设为守护线程 / 注册 shutdown hook |
| 线程池满、任务排队到超时 | 父子任务同一池，父任务 `join` 等子任务 | 父子用不同池，或子任务改用 `thenCompose` 串联 |
| 拿到 `CF<CF<T>>` | 该用 `thenCompose` 的地方用了 `thenApply` | 见 4.4 |
| traceId 丢失 | `ThreadLocal` 不跨线程 | 上下文传递包装器（6.4） |

其中"父子任务同一池"的饥饿死锁最容易在上线后爆发，可以复现：

```java
import java.util.concurrent.*;

public class StarvationDemo {
    public static void main(String[] args) throws Exception {
        // 只有 1 个线程：父任务占着它，又去等一个只能由这个线程执行的任务
        ExecutorService single = Executors.newFixedThreadPool(1, r -> {
            Thread t = new Thread(r, "biz-1");
            t.setDaemon(true);
            return t;
        });
        CompletableFuture<String> f = CompletableFuture.supplyAsync(() -> {
            CompletableFuture<String> child = CompletableFuture.supplyAsync(() -> "child", single);
            return child.join();
        }, single);

        try {
            System.out.println(f.get(2, TimeUnit.SECONDS));
        } catch (TimeoutException e) {
            System.out.println("2s 内没完成 -> 饥饿死锁（父任务占着唯一线程等子任务）");
        }
        single.shutdownNow();
    }
}
```

输出：

```text
2s 内没完成 -> 饥饿死锁（父任务占着唯一线程等子任务）
```

---

## 常见排错

| 现象 | 可能原因 | 排查动作 |
|------|----------|----------|
| 接口 RT 高但下游监控正常 | 线程池排队 | `jstack` 看 `biz-pool` 线程是否都在 `WAITING`；看队列长度 |
| 偶发 `RejectedExecutionException` | 队列满 + 拒绝策略是 `AbortPolicy` | 换 `CallerRunsPolicy` 或调大队列，同时看是不是下游变慢 |
| 同样的代码本地快、线上慢 | 本地 CPU 多 → `commonPool` 并行度高 | 统一显式线程池，行为才可复现 |
| 内存缓慢上涨 | Future 链持有大对象，或回调里捕获了大上下文 | 用 `jmap` 看 `CompletableFuture` 实例数与引用链 |
| 超时日志里没有堆栈 | `orTimeout` 只给 `TimeoutException`，不含业务上下文 | 在 `exceptionally` 里补日志（带 traceId、下游名、耗时） |

---

## 与相关技术的关系

| 方案 | 表达力 | 背压 | 学习成本 | 适用 |
|------|--------|------|----------|------|
| `CompletableFuture` | 一次性异步任务、有限组合 | 无 | 低 | 并行聚合、异步 IO、单个 RPC 编排 |
| `Reactor`（`Flux`/`Mono`） | 流式、可重试/限流/背压 | 有 | 中高 | 流式数据处理、SSE、网关 |
| 虚拟线程 + 同步阻塞代码 | 无（就是普通方法调用） | 无 | 极低 | IO 密集的高并发请求处理，见 [[java-thread-pool#十六、虚拟线程（JDK 21+）\|线程池笔记第十六节]] |

一句话选择：**几个调用拼一个结果 → CompletableFuture；一条流要背压/限流/多播 → Reactor；
只是"每请求一线程"的吞吐问题 → 虚拟线程，别上异步**。异步不是性能银弹，它换来的是资源占用，
代价是调试难度与上下文丢失；虚拟线程普及之后，"为了省线程而异步"的理由已经弱了很多。

---

## See Also

- [[java-multithreading|Java 多线程基础]] —— JMM、`volatile`、`synchronized`、`ThreadLocal`、并发容器
- [[java-thread-pool|Java 线程池]] —— 七大参数、队列与拒绝策略、动态调参、虚拟线程
- [[java-high-concurrency|Java 后端高并发系统设计]] —— 限流、熔断、缓存、削峰的整体视角
- [[02-backend/java-fundamentals/reactor/index|Project Reactor 专题]] —— 需要背压与流式处理时的替代方案
- [[unit-testing|Java 单元测试规范与原理]] —— 异步代码怎么测（`CountDownLatch`、`awaitility`）

## 参考

- [CompletableFuture (Java SE API)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html)
- [Guide to CompletableFuture (Baeldung)](https://www.baeldung.com/java-completablefuture)
- [Java 并发编程实战（RedSpider 社区）](https://redspider.gitbook.io/concurrent)
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
