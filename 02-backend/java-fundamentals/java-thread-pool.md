---
title: Java 线程池
description: 线程池原理与实战，涵盖 ThreadPoolExecutor 七大参数、执行流程、工作队列与拒绝策略、Executors 陷阱、参数调优、监控动态调参、ForkJoinPool 与虚拟线程
tags:
  - java
  - concurrency
  - thread-pool
  - backend
date: 2026-10-12
---

# Java 线程池

线程池是 Java 并发最常用也最容易踩坑的组件。本文从「为什么需要线程池」出发，讲清 `ThreadPoolExecutor` 的每个参数、任务流转的完整路径、生产环境的配置与调优方法，以及那些只在事故复盘里才会被提起的坑。

> 多线程基础请见 [[java-multithreading|Java 多线程基础]]，异步编排请见 [[java-concurrency|Java 并发编程（CompletableFuture）]]。

---

## 一、为什么需要线程池

直接 `new Thread()` 有三个致命问题：

1. **创建销毁开销大**：线程创建涉及内核态切换、栈内存分配（默认 1MB），频繁创建销毁非常昂贵。
2. **资源不可控**：无限创建线程会耗尽内存（`OutOfMemoryError: unable to create native thread`），且大量线程上下文切换会拖垮系统。
3. **无法统一管理**：缺少统一的拒绝、监控、异常处理能力。

线程池的核心价值是**线程复用 + 统一管理 + 削峰填谷**。

```text
  任务提交方              线程池                      工作线程
 ─────────────        ──────────────            ─────────────
 submit(task)  ──►  ┌──────────────┐   take()  ┌────────┐
                    │  工作队列     │  ──────► │ 线程-1 │ ──► 执行 task
 submit(task)  ──►  │  (Blocking   │  ──────► │ 线程-2 │ ──► 执行 task
                    │   Queue)     │  ──────► │ 线程-3 │ ──► 执行 task
 submit(task)  ──►  └──────────────┘           └────────┘
                    队列满 + 线程满 → 拒绝策略        │
                                                    └── 执行完不销毁，回到队列取下一个任务
```

---

## 二、Executor 框架体系

```text
Executor (接口：只有一个 execute(Runnable))
   └── ExecutorService (接口：增加 submit/shutdown/invokeAll 等生命周期方法)
          ├── ThreadPoolExecutor              ← 通用线程池（本文主角）
          │      └── ScheduledThreadPoolExecutor  ← 定时/周期任务
          └── ForkJoinPool                    ← 分治任务 + 工作窃取
```

| 接口/类 | 核心能力 |
|---------|----------|
| `Executor` | 提交任务 `execute(Runnable)`，无返回值 |
| `ExecutorService` | 增加 `submit()`（返回 `Future`）、`shutdown()`、`invokeAll()` |
| `ThreadPoolExecutor` | 可配置全部参数的完整实现 |
| `ScheduledThreadPoolExecutor` | 支持延迟执行与周期性执行 |
| `ForkJoinPool` | 分治（Fork/Join）+ 工作窃取，适合 CPU 密集的递归任务 |
| `Executors` | 静态工厂工具类（**生产环境慎用，见第五节**） |

---

## 三、ThreadPoolExecutor 七大参数

这是全文最关键的部分，必须逐字理解：

```java
public ThreadPoolExecutor(int corePoolSize,          // ① 核心线程数
                          int maximumPoolSize,       // ② 最大线程数
                          long keepAliveTime,        // ③ 空闲线程存活时间
                          TimeUnit unit,             // ④ 时间单位
                          BlockingQueue<Runnable> workQueue,      // ⑤ 工作队列
                          ThreadFactory threadFactory,            // ⑥ 线程工厂
                          RejectedExecutionHandler handler)       // ⑦ 拒绝策略
```

| 参数 | 说明 | 配置要点 |
|------|------|----------|
| ① `corePoolSize` | 核心线程数，线程池维持的常驻线程。**即使空闲也不销毁**（除非 `allowCoreThreadTimeOut(true)`） | 按业务特性估算，见第六节 |
| ② `maximumPoolSize` | 线程池允许创建的最大线程数 | 必须 ≥ corePoolSize，否则抛 `IllegalArgumentException` |
| ③ `keepAliveTime` | 非核心线程空闲多久后被回收 | 突发流量过后回收多余线程 |
| ④ `unit` | 时间单位 | `TimeUnit.SECONDS` |
| ⑤ `workQueue` | 保存等待执行任务的阻塞队列 | **必须用有界队列** |
| ⑥ `threadFactory` | 创建线程的工厂 | 自定义线程名、优先级、守护线程属性，方便排查问题 |
| ⑦ `handler` | 队列和线程池都满时的处理策略 | 按业务容忍度选择 |

### 核心线程会超时吗？

默认不会。`allowCoreThreadTimeOut(true)` 可以让核心线程在空闲 `keepAliveTime` 后也被回收，适合流量波谷明显的场景。

### 核心线程是延迟创建的吗？

是的。默认情况下核心线程是**按需创建**的（提交任务时才创建）。`prestartCoreThread()` 可以提前启动一个核心线程，`prestartAllCoreThreads()` 启动全部，用于降低冷启动延迟。

---

## 四、任务执行流程

这是面试与实战的双重重点，务必记住**「先入队，再扩容」**这个反直觉的顺序：

```text
                          提交任务 execute()/submit()
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ 当前线程数 < corePoolSize ?    │
                    └───────────────────────────────┘
                           是 │              │ 否
                              ▼              ▼
                     ┌────────────────┐   ┌────────────────────┐
                     │ 创建【核心线程】 │   │ 工作队列未满？        │
                     │ 立即执行该任务   │   └────────────────────┘
                     └────────────────┘      是 │          │ 否（队列已满）
                                               ▼          ▼
                                    ┌────────────┐  ┌──────────────────────────┐
                                    │ 任务入队    │  │ 线程数 < maximumPoolSize? │
                                    │ 等待被取走  │  └──────────────────────────┘
                                    └────────────┘    是 │              │ 否
                                                        ▼              ▼
                                          ┌──────────────────┐  ┌──────────────┐
                                          │ 创建【非核心线程】 │  │ 执行拒绝策略  │
                                          │（救急线程）执行    │  │ RejectedExec │
                                          └──────────────────┘  └──────────────┘
```

**为什么是先入队而不是先扩容？**

线程池的设计意图是：尽量用**固定数量的核心线程 + 队列缓冲**处理任务，把「创建更多线程」当作队列扛不住时的兜底手段。这样可以控制系统的并发度，避免线程数随流量暴涨。

这也解释了一个常见误区：**使用无界队列（如 `LinkedBlockingQueue` 无参构造）时，`maximumPoolSize` 完全失效**——因为队列永远不满，永远不会创建非核心线程，任务会一直堆积在队列里直到 OOM。

### 线程数与任务的关系示例

假设 `core=2, max=4, queue=2`：

| 提交第 N 个任务 | 发生什么 |
|-----------------|----------|
| 1、2 | 创建 2 个核心线程执行 |
| 3、4 | 入队（队列 2 个位置填满） |
| 5、6 | 队列满，创建 2 个非核心线程执行（线程数达 4） |
| 7 | 队列满 + 线程数达 max = 4 → 拒绝策略 |

---

## 五、Executors 工厂类及其陷阱

`Executors` 提供了开箱即用的工厂方法，但**《阿里巴巴 Java 开发手册》明确禁止在生产环境使用**（强制级别），原因是它们隐藏了关键参数，且默认配置有 OOM 风险。

| 工厂方法 | 底层配置 | 风险 |
|----------|----------|------|
| `newFixedThreadPool(n)` | `core = max = n`，`LinkedBlockingQueue`（无界） | 队列无界，任务持续堆积 → **堆内存 OOM** |
| `newSingleThreadExecutor()` | `core = max = 1`，`LinkedBlockingQueue`（无界） | 同上，且无并发能力 |
| `newCachedThreadPool()` | `core = 0`，`max = Integer.MAX_VALUE`，`SynchronousQueue` | 来一个任务建一个线程 → **线程数爆炸 OOM** |
| `newScheduledThreadPool(n)` | `core = n`，`max = Integer.MAX_VALUE`，`DelayedWorkQueue`（无界） | 无界队列 + 理论上无限线程 |
| `newWorkStealingPool()` | `ForkJoinPool`（并行度 = CPU 核数） | 无界队列，且不适合阻塞型 IO 任务 |

**结论**：这些方法的参数不可控、队列无界、线程名无意义，出问题很难排查。生产环境一律手写 `ThreadPoolExecutor` 构造函数。

---

## 六、正确创建线程池的姿势

```java
import com.google.common.util.concurrent.ThreadFactoryBuilder; // Guava
import java.util.concurrent.*;

@Configuration
public class ThreadPoolConfig {

    @Bean("bizExecutor")
    public ThreadPoolExecutor bizExecutor() {
        ThreadFactory namedFactory = new ThreadFactoryBuilder()
                .setNameFormat("biz-pool-%d")
                .setUncaughtExceptionHandler((t, e) ->
                        log.error("线程 {} 执行任务发生未捕获异常", t.getName(), e))
                .build();

        return new ThreadPoolExecutor(
                8,                                  // corePoolSize
                16,                                 // maximumPoolSize
                60L, TimeUnit.SECONDS,              // 非核心线程空闲 60s 回收
                new ArrayBlockingQueue<>(500),       // 有界队列，容量 500
                namedFactory,
                new ThreadPoolExecutor.CallerRunsPolicy()  // 让提交方自己执行，天然限流
        );
    }
}
```

几个关键点：

1. **队列必须有界**：`new ArrayBlockingQueue<>(capacity)` 或 `new LinkedBlockingQueue<>(capacity)`。
2. **线程必须命名**：默认的 `pool-1-thread-3` 在 `jstack` 里毫无信息量，命名后一眼看出是哪个业务的线程池。
3. **设置 `UncaughtExceptionHandler`**：兜住 `execute()` 提交的任务抛出的异常，避免异常被静默吞掉。
4. **根据业务拆分线程池**：核心交易、旁路通知、定时任务应使用**独立线程池**，避免慢任务拖垮快任务。

---

## 七、工作队列选型

| 队列 | 是否有界 | 特点 | 适用 |
|------|----------|------|------|
| `ArrayBlockingQueue` | 有界 | 数组实现，读写共用一把锁 | 常规首选，容量可控 |
| `LinkedBlockingQueue` | 可指定容量 | 链表实现，put/take 双锁，吞吐更高 | 需要高吞吐时（**务必指定容量**） |
| `SynchronousQueue` | 不存储 | 任务必须立即交给线程，否则新建线程 | 配合 `max = Integer.MAX_VALUE`（`CachedThreadPool`） |
| `PriorityBlockingQueue` | 无界 | 按优先级出队，需实现 `Comparable` | 需要任务优先级 |
| `DelayQueue` | 无界 | 延迟到期才能取出 | 延迟任务、缓存过期 |
| `LinkedTransferQueue` | 无界 | 生产者可等待消费者接收 | 需要确认送达的场景 |

**经验**：绝大多数业务场景选 `ArrayBlockingQueue` 或指定容量的 `LinkedBlockingQueue` 即可。

---

## 八、拒绝策略

JDK 内置 4 种，均实现 `RejectedExecutionHandler`：

| 策略 | 行为 | 适用 |
|------|------|------|
| `AbortPolicy`（默认） | 抛 `RejectedExecutionException` | 需要明确感知失败，配合告警 |
| `CallerRunsPolicy` | 由提交任务的线程自己执行 | **推荐**：天然反压，提交方变慢，减缓流入速度 |
| `DiscardPolicy` | 静默丢弃，无任何提示 | 任务可容忍丢失（极少使用） |
| `DiscardOldestPolicy` | 丢弃队列中最老的任务，重新提交当前任务 | 允许丢弃旧任务的场景（如实时行情） |

### 自定义拒绝策略（生产推荐）

生产中通常需要「记录 + 告警 + 降级/持久化」，内置的都不够用：

```java
public class AlertingRejectedHandler implements RejectedExecutionHandler {
    @Override
    public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
        // 1. 打点 + 告警，让线程池的容量问题可观测
        Metrics.counter("thread_pool.rejected",
                "pool", executor.getPoolSize() + "").increment();
        log.error("线程池拒绝任务: poolSize={}, active={}, queue={}/{}",
                executor.getPoolSize(), executor.getActiveCount(),
                executor.getQueue().size(), executor.getQueue().remainingCapacity() + executor.getQueue().size());

        // 2. 降级：能丢就丢，不能丢则持久化后补偿
        if (r instanceof PersistableTask task) {
            taskStore.saveAsync(task);   // 落库，后续重试
            return;
        }
        throw new RejectedExecutionException("系统繁忙，请稍后重试");
    }
}
```

---

## 九、参数怎么设置

### 按任务类型估算

| 任务类型 | 特点 | 线程数建议 |
|----------|------|-----------|
| **CPU 密集型** | 加解密、图像处理、复杂计算、序列化 | `N(cpu) + 1`，避免过多线程切换 |
| **IO 密集型** | 数据库、RPC、磁盘读写 | `N(cpu) × (1 + 等待时间/计算时间)` 或 `2 × N(cpu)` |

获取 CPU 核数：

```java
int cpuCount = Runtime.getRuntime().availableProcessors();
```

### 利特尔法则（Little's Law）

对线程池更严谨的估算来自排队论：

```text
线程数 = QPS × 平均响应时间(RT，秒)

例：单接口 QPS = 200，平均 RT = 50ms = 0.05s
    线程数 = 200 × 0.05 = 10
```

考虑到 RT 波动和突发流量，实际取值可以在理论值上留 20%~50% 余量。

### 队列容量的权衡

队列是把双刃剑：

- **队列太大**：任务排队时间长，响应延迟（RT）飙升，且掩盖了容量不足的问题。
- **队列太小**：拒绝频繁，浪费系统吞吐。

经验做法：以「可接受的最大排队时间」反推容量，例如最大排队 1 秒、单任务 20ms、线程数 10 → 队列 ≈ 10 × (1000/20) = 500。

> **核心原则**：任何公式都只是起点，真实参数必须靠**压测 + 监控**逐步调整。线程池配置没有银弹。

---

## 十、提交任务：execute vs submit

这两个方法的异常处理行为完全不同，是最隐蔽的坑之一。

| 对比项 | `execute(Runnable)` | `submit(Runnable/Callable)` |
|--------|--------------------|----------------------------|
| 返回值 | 无 | `Future<?>` |
| 任务抛异常 | 直接抛出，线程终止，可被 `UncaughtExceptionHandler` 捕获 | 异常被封装进 `Future`，**不显式抛出** |
| 获取异常 | — | 必须调用 `future.get()` 才抛出 `ExecutionException` |

**问题代码**：

```java
executor.submit(() -> {
    int i = 1 / 0;   // 异常被吞掉，日志里什么都看不到
});
```

**正确写法**（三选一）：

```java
// 方案 1：任务内部 try-catch
executor.submit(() -> {
    try { doWork(); }
    catch (Exception e) { log.error("任务执行失败", e); }
});

// 方案 2：用 execute（异常会交给 UncaughtExceptionHandler）
executor.execute(() -> doWork());

// 方案 3：处理 Future
Future<?> f = executor.submit(() -> doWork());
try {
    f.get();
} catch (ExecutionException e) {
    log.error("任务异常", e.getCause());   // 真实异常在 cause 里
}
```

> 用 `CompletableFuture` 时同理，记得加 `exceptionally()` / `handle()`。

---

## 十一、关闭线程池

```java
// 推荐写法：优雅停机
public void shutdownGracefully(ExecutorService executor) {
    executor.shutdown();       // 1. 停止接收新任务，已提交任务继续执行完
    try {
        // 2. 等待最多 30 秒
        if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
            List<Runnable> dropped = executor.shutdownNow();  // 3. 超时则强制中断
            log.warn("强制关闭，{} 个任务未执行", dropped.size());
            // 4. 再等一会，确保响应中断的任务有机会收尾
            if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                log.error("线程池未能正常终止");
            }
        }
    } catch (InterruptedException e) {
        executor.shutdownNow();
        Thread.currentThread().interrupt();
    }
}
```

| 方法 | 行为 |
|------|------|
| `shutdown()` | 平滑关闭：不再接收新任务，队列中的任务继续执行完 |
| `shutdownNow()` | 立即关闭：尝试中断正在执行的任务，返回队列中未执行的任务列表 |
| `awaitTermination(timeout)` | 阻塞等待关闭完成，返回是否全部结束 |
| `isShutdown()` | 是否调用了 shutdown |
| `isTerminated()` | 是否全部任务执行完毕且已关闭 |

**注意**：`shutdownNow()` 依赖 `Thread.interrupt()`，如果任务不响应中断（不检查 `isInterrupted()`、不处理 `InterruptedException`），它就无法被强制停止。

Spring 环境可以配合 `@PreDestroy` 或实现 `DisposableBean`，在应用关闭时优雅停机。

---

## 十二、监控与动态调参

### 内置监控指标

`ThreadPoolExecutor` 提供了一批 getter，可直接接入监控（Micrometer / Prometheus）：

| 方法 | 含义 | 告警建议 |
|------|------|----------|
| `getPoolSize()` | 当前线程数 | — |
| `getActiveCount()` | 活跃（正在执行任务）线程数 | 长期 ≈ maximumPoolSize 说明容量不足 |
| `getCorePoolSize()` / `getMaximumPoolSize()` | 配置的线程数 | — |
| `getQueue().size()` / `remainingCapacity()` | 队列堆积量 | 堆积率 > 80% 告警 |
| `getCompletedTaskCount()` | 已完成任务总数 | 用于计算吞吐 |
| `getTaskCount()` | 总任务数（已完成 + 执行中 + 队列中） | — |
| `getLargestPoolSize()` | 历史最大线程数 | 判断是否曾触发扩容 |

### 扩展监控点

继承 `ThreadPoolExecutor` 重写钩子方法，可以精确统计每个任务的执行耗时：

```java
public class MonitoredThreadPool extends ThreadPoolExecutor {

    public MonitoredThreadPool(int core, int max, long keepAlive, TimeUnit unit,
                               BlockingQueue<Runnable> queue, ThreadFactory factory) {
        super(core, max, keepAlive, unit, queue, factory, new AbortPolicy());
    }

    @Override
    protected void beforeExecute(Thread t, Runnable r) {
        super.beforeExecute(t, r);
        Metrics.counter("pool.task.submitted").increment();
    }

    @Override
    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);
        // submit 提交的任务异常不会走这里，需要额外从 Future 里取
        if (t != null) {
            log.error("任务执行异常", t);
        }
    }

    @Override
    protected void terminated() {
        super.terminated();
        log.info("线程池已关闭，共完成 {} 个任务", getCompletedTaskCount());
    }
}
```

### 动态调参

`ThreadPoolExecutor` 提供了 setter，可以在运行时调整：

```java
executor.setCorePoolSize(16);
executor.setMaximumPoolSize(32);
executor.setKeepAliveTime(120, TimeUnit.SECONDS);
```

**限制**：`LinkedBlockingQueue` 的 `capacity` 是 `final` 的，**无法动态修改队列容量**。
业界做法（如美团技术团队）是自定义 `ResizableCapacityLinkedBlockingQueue`，
把 `capacity` 改为非 `final` 并提供 setter，配合配置中心实现真正的动态调参。

---

## 十三、ScheduledThreadPoolExecutor（定时任务）

```java
ScheduledThreadPoolExecutor scheduler =
        new ScheduledThreadPoolExecutor(4, namedThreadFactory);

// 1. 延迟 5 秒执行一次
scheduler.schedule(() -> sendReminder(), 5, TimeUnit.SECONDS);

// 2. 固定【频率】执行：以上一次任务【开始】时间 + period 计算下一次
scheduler.scheduleAtFixedRate(() -> syncData(), 1, 5, TimeUnit.MINUTES);

// 3. 固定【延迟】执行：以上一次任务【结束】时间 + delay 计算下一次
scheduler.scheduleWithFixedDelay(() -> cleanUp(), 1, 5, TimeUnit.MINUTES);
```

### 与 Timer 对比

| 对比项 | `Timer` | `ScheduledThreadPoolExecutor` |
|--------|---------|-------------------------------|
| 执行线程 | 单线程 | 多线程 |
| 任务异常 | 一个任务抛异常，整个 Timer 挂掉 | 只影响当前任务 |
| 时间基准 | 绝对时间，对系统时间调整敏感 | 相对时间（`System.nanoTime()`），不受影响 |
| 功能 | 基础 | 支持 `Future`、自定义线程池 |

**结论**：永远不要用 `Timer`，用 `ScheduledThreadPoolExecutor` 或 Spring 的 `@Scheduled`。

> `scheduleAtFixedRate` 的一个细节：如果单次执行耗时超过 period，
> 下一次会**立即**执行（不会并发执行同一个任务，但会连续执行），可能造成 CPU 打满。
> 此时应该用 `scheduleWithFixedDelay`。

---

## 十四、ForkJoinPool

`ForkJoinPool` 是「分而治之」的实现，核心是**工作窃取（work-stealing）**：

```text
  线程1 [任务栈] ████████████ ← 从头部取任务执行
                           ▲
                           │ 从【尾部】窃取
                           │
  线程2 [任务栈] ░░░        ← 自己的队列空了，去别人尾部偷一个
```

- 每个线程维护一个**双端队列**，自己从头部取任务，空闲时从其他线程队列**尾部**窃取，减少竞争。
- 适合 CPU 密集、可递归拆分的大任务（如大数组排序、遍历文件系统）。
- `Executors.newWorkStealingPool()` 底层就是它。

```java
class SumTask extends RecursiveTask<Long> {
    private static final int THRESHOLD = 10_000;
    private final long[] array;
    private final int start, end;

    public SumTask(long[] array, int start, int end) {
        this.array = array; this.start = start; this.end = end;
    }

    @Override
    protected Long compute() {
        if (end - start <= THRESHOLD) {           // 足够小，直接算
            long sum = 0;
            for (int i = start; i < end; i++) sum += array[i];
            return sum;
        }
        int mid = (start + end) >>> 1;            // 拆分
        SumTask left  = new SumTask(array, start, mid);
        SumTask right = new SumTask(array, mid, end);
        left.fork();                              // 异步执行子任务
        long rightResult = right.compute();       // 当前线程算另一半
        return left.join() + rightResult;         // 合并结果
    }
}

long sum = new ForkJoinPool().invoke(new SumTask(array, 0, array.length));
```

> **重要限制**：`ForkJoinPool` 不适合阻塞型 IO 任务——工作窃取算法假设任务不会阻塞，
> 阻塞任务会导致线程饥饿。`parallelStream()` 底层用的就是 `ForkJoinPool.commonPool()`，
> 这也是不建议在 `parallelStream()` 里做 IO 操作的原因。

---

## 十五、CompletableFuture 的默认线程池陷阱

`CompletableFuture.supplyAsync()` 不传线程池时，会使用 `ForkJoinPool.commonPool()`，
一个 **JVM 全局共享**的线程池，其并行度为 `availableProcessors() - 1`。

```java
// 危险：IO 型任务占满 commonPool，会影响整个 JVM 里所有 CompletableFuture / parallelStream
CompletableFuture.supplyAsync(() -> callRemoteService());

// 正确：始终显式传入专用线程池
CompletableFuture.supplyAsync(() -> callRemoteService(), bizExecutor);
```

后果：一个慢 SQL 或慢 RPC 就能让整个应用里所有依赖 `commonPool` 的异步任务排队，故障面被放大到全应用，且极难定位。

---

## 十六、虚拟线程（JDK 21+）

JDK 21 正式引入虚拟线程（JEP 444），由 JVM 调度，创建成本极低，可轻松创建百万级。

```java
// 方式 1：直接创建
Thread vt = Thread.ofVirtual().name("vt-1").start(() -> handleRequest());

// 方式 2：每个任务一个虚拟线程
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i ->
            executor.submit(() -> {
                Thread.sleep(Duration.ofSeconds(1));   // 阻塞时自动让出载体线程
                return i;
            }));
}
```

| 对比项 | 平台线程（传统线程池） | 虚拟线程 |
|--------|----------------------|----------|
| 调度方 | 操作系统内核 | JVM |
| 内存开销 | 约 1MB 栈/线程 | 约几百字节，动态扩容 |
| 数量级 | 数百 ~ 数千 | 百万级 |
| 阻塞代价 | 占用 OS 线程，昂贵 | 自动从载体线程卸载，几乎免费 |
| 适用场景 | CPU 密集、需要精细控制并发度 | **IO 密集**、高并发请求处理 |

**使用原则**：

1. **不要池化虚拟线程**——它们创建成本极低，用完即弃即可。
2. **适合 IO 密集**，不适合 CPU 密集（CPU 密集仍用固定大小的平台线程池）。
3. 阻塞操作（如 `synchronized`）在 JDK 21~23 会导致虚拟线程被「钉住」（pinning）在载体线程上；
   JDK 24（JEP 491）已解决该问题，在 JDK 21 上建议优先使用 `ReentrantLock` 替代 `synchronized`。
4. 需要**限制并发度**（如数据库连接数）时用 `Semaphore`，而不是线程池大小。
5. Spring Boot 3.2+ 可通过 `spring.threads.virtual.enabled=true` 开启。

---

## 十七、Spring 中的线程池

### ThreadPoolTaskExecutor

Spring 对 `ThreadPoolExecutor` 的封装，支持通过配置属性注入：

```java
@Configuration
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(8);
        executor.setMaxPoolSize(16);
        executor.setQueueCapacity(500);
        executor.setKeepAliveSeconds(60);
        executor.setThreadNamePrefix("async-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());  // 传递 MDC/TraceId
        executor.setWaitForTasksToCompleteOnShutdown(true); // 关闭时等待任务完成
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();                              // 不要忘记
        return executor;
    }
}
```

对应的 `application.yml`：

```yaml
spring:
  task:
    execution:
      pool:
        core-size: 8
        max-size: 16
        queue-capacity: 500
        keep-alive: 60s
      thread-name-prefix: async-
```

### @Async 的三个坑

1. **同类内部调用失效**：`@Async` 基于 AOP 代理，`this.method()` 不经过代理，异步不生效。需注入自身代理或拆分到另一个 Bean。
2. **返回值**：想拿结果必须返回 `CompletableFuture<T>` 或 `Future<T>`，返回 `void` 时异常无法传递。
3. **默认线程池无界**：Spring Boot 默认的 `applicationTaskExecutor` 队列容量为 `Integer.MAX_VALUE`，高并发下有 OOM 风险，**必须显式配置**。

### 上下文传递

线程池会丢失 `ThreadLocal` 中的 TraceId / 用户信息，需要 `TaskDecorator` 手动传递：

```java
public class MdcTaskDecorator implements TaskDecorator {
    @Override
    public Runnable decorate(Runnable runnable) {
        Map<String, String> contextMap = MDC.getCopyOfContextMap();  // 提交时快照
        RequestAttributes attrs = RequestContextHolder.getRequestAttributes();
        return () -> {
            try {
                if (contextMap != null) MDC.setContextMap(contextMap);
                if (attrs != null) RequestContextHolder.setRequestAttributes(attrs);
                runnable.run();
            } finally {
                MDC.clear();
                RequestContextHolder.resetRequestAttributes();
            }
        };
    }
}
```

---

## 十八、常见坑汇总

### 1. 池内任务互相等待导致死锁（饥饿死锁）

父任务和子任务提交到**同一个**线程池，父任务等子任务结果，子任务在队列里等线程：

```java
// 危险：同一个池，core=1 时必然死锁
executor.submit(() -> {
    Future<Integer> f = executor.submit(() -> 42);
    return f.get();      // 父任务占着唯一线程等子任务，子任务永远拿不到线程
});
```

**解决**：父子任务使用**不同的线程池**，或使用 `ForkJoinPool`（其 `invokeAll` 会「补偿」线程）。

### 2. ThreadLocal 脏数据与内存泄漏

线程复用导致上一个请求的 `ThreadLocal` 残留。必须在 `finally` 中 `remove()`。详见 [[java-multithreading|Java 多线程基础]]。

### 3. 异常被静默吞掉

`submit()` 的异常封装在 `Future` 里，`execute()` 需要 `UncaughtExceptionHandler`。详见第十节。

### 4. 无界队列导致 OOM

`LinkedBlockingQueue` 不指定容量就是「无界」，`maximumPoolSize` 形同虚设，任务堆积直接打爆堆内存。

### 5. 线程池未关闭导致应用无法退出

`Executors.newFixedThreadPool()` 创建的线程**是非守护线程**，如果不 `shutdown()`，JVM 永远不会退出。
局部创建的线程池必须显式关闭，或用 `try-with-resources`（JDK 19+ 起 `ExecutorService` 实现 `AutoCloseable`）。

### 6. 线程池被当作「局部变量」反复创建

每次请求 `new ThreadPoolExecutor()` 完全违背线程池「复用」的初衷，还会因未关闭导致线程泄漏。线程池必须是**全局单例**或容器管理的 Bean。

---

## 十九、配置速查表

| 场景 | core | max | 队列 | 拒绝策略 |
|------|------|-----|------|----------|
| 核心交易（低延迟） | CPU 核数 ~ 2×核数 | 2×core | 有界，容量小（50~200） | `AbortPolicy` + 告警 |
| 异步通知（可延迟） | 2~4 | 8 | 有界，容量大（1000+） | `CallerRunsPolicy` |
| 定时任务 | 按任务数 | = core | `DelayedWorkQueue` | `AbortPolicy` |
| IO 密集批处理 | 2×核数 | 4×核数 | 有界（500~2000） | `CallerRunsPolicy` |
| CPU 密集计算 | 核数 + 1 | 核数 + 1 | 有界 | `AbortPolicy` |

**通用原则**：

1. 队列**必须有界**。
2. 线程**必须命名**。
3. 拒绝策略**必须显式指定**（默认是抛异常的 `AbortPolicy`）。
4. 按业务**隔离线程池**，避免相互影响。
5. 参数以**压测和监控**为准，公式只是起点。

---

## 参考

- Oracle 官方 `ThreadPoolExecutor` 文档：
  <https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html>
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491)
- 《阿里巴巴 Java 开发手册》并发处理章节
- 美团技术团队：《Java 线程池实现原理及其在美团业务中的实践》
