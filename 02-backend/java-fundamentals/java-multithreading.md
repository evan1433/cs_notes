---
title: Java 多线程基础
description: Java 多线程核心知识，涵盖线程创建与生命周期、JMM 内存模型、synchronized/volatile、Lock 体系、原子类、ThreadLocal、并发容器与同步工具
tags:
  - java
  - concurrency
  - multithreading
  - backend
date: 2026-10-12
---

# Java 多线程基础

多线程是 Java 后端开发的地基，也是线程池、异步编排、并发容器的前置知识。本文按「线程怎么用 → 为什么会出错 → 怎么保证安全 → 有哪些现成工具」的顺序组织。

> 线程池相关请见 [[java-thread-pool|Java 线程池]]，异步编排请见 [[java-concurrency|Java 并发编程（CompletableFuture）]]。

---

## 一、线程与进程

| 维度 | 进程 | 线程 |
|------|------|------|
| 定义 | 操作系统资源分配的基本单位 | CPU 调度执行的最小单位 |
| 内存空间 | 独立地址空间 | 共享所属进程的堆与方法区，独占栈与程序计数器 |
| 切换开销 | 大（涉及页表、内核栈切换） | 小（只需保存少量寄存器） |
| 通信方式 | IPC（管道、共享内存、Socket） | 共享变量、等待/通知机制 |
| 健壮性 | 一个进程崩溃不影响其他进程 | 线程崩溃会导致整个进程退出 |

**线程独享**：程序计数器、虚拟机栈、本地方法栈。
**线程共享**：堆、方法区（元空间）、直接内存。

这正是线程安全问题的根源——多个线程可以同时读写同一块堆内存。

---

## 二、创建线程的三种方式

### 1. 继承 Thread

```java
class MyThread extends Thread {
    @Override
    public void run() {
        System.out.println(Thread.currentThread().getName() + " 执行中");
    }
}

new MyThread().start();
```

缺点：Java 单继承，占用继承名额；任务与线程绑定，无法复用。

### 2. 实现 Runnable（推荐）

```java
Runnable task = () -> System.out.println(Thread.currentThread().getName() + " 执行中");
new Thread(task, "worker-1").start();
```

任务（`Runnable`）与执行载体（`Thread`）解耦，同一个任务可以交给多个线程或线程池执行，且无返回值。

### 3. 实现 Callable + Future（需要返回值）

```java
Callable<Integer> task = () -> {
    TimeUnit.SECONDS.sleep(1);
    return 42;
};

FutureTask<Integer> futureTask = new FutureTask<>(task);
new Thread(futureTask, "calc-1").start();

Integer result = futureTask.get();              // 阻塞直到结果返回
Integer timeoutResult = futureTask.get(2, TimeUnit.SECONDS); // 带超时
```

| 方式 | 返回值 | 受检异常 | 适用场景 |
|------|--------|----------|----------|
| 继承 Thread | 无 | 不能抛 | 几乎不用 |
| 实现 Runnable | 无 | 不能抛 | 通用，配合线程池 |
| 实现 Callable | 有 | 可抛 `Exception` | 需要结果或异常传递 |

> **注意**：启动线程必须调用 `start()`，直接调用 `run()` 只是在当前线程里执行了一个普通方法，不会开启新线程。

---

## 三、线程生命周期

Java 的 `Thread.State` 定义了 6 种状态：

```text
                    start()
   ┌─────┐  ──────────────────────►  ┌───────────┐
   │ NEW │                            │ RUNNABLE  │◄──┐
   └─────┘                            └───────────┘   │
                                       │      ▲       │
                    synchronized 争抢失败 │      │ 获得CPU │ notify()/notifyAll()
                                       ▼      │ 时间片 │ 或 LockSupport.unpark()
                                  ┌─────────┐ │       │ wait()/join()/park()
                                  │ BLOCKED │─┘       │
                                  └─────────┘         │
                                                      │
              wait()/join()/park()          ┌──────────────────┐
                             ┌─────────────►│WAITING /         │
                             │              │TIMED_WAITING     │
                             └──────────────┴──────────────────┘
                                             sleep(n)/wait(n)/join(n)/parkNanos()

   run() 正常结束或抛出未捕获异常 ──────────► ┌────────────┐
                                              │ TERMINATED │
                                              └────────────┘
```

| 状态 | 含义 | 触发方式 |
|------|------|----------|
| NEW | 已创建未启动 | `new Thread()` |
| RUNNABLE | 正在执行或等待 CPU 时间片（含 OS 层面的 Ready/Running） | `start()` |
| BLOCKED | 等待进入 `synchronized` 监视器 | 竞争锁失败 |
| WAITING | 无限期等待被显式唤醒 | `wait()`、`join()`、`LockSupport.park()` |
| TIMED_WAITING | 限期等待 | `sleep(n)`、`wait(n)`、`join(n)`、`parkNanos()` |
| TERMINATED | 执行结束 | `run()` 返回或异常终止 |

**关键区别**：`BLOCKED` 是等待 `synchronized` 的**隐式锁**；
`WAITING`/`TIMED_WAITING` 是线程主动调用等待方法，等待被其他线程显式唤醒。
基于 AQS 的 `Lock` 阻塞表现为 `WAITING`，而非 `BLOCKED`。

---

## 四、线程常用方法

| 方法                    | 作用                            | 注意点                                 |
| --------------------- | ----------------------------- | ----------------------------------- |
| `start()`             | 启动新线程，由 JVM 调用 `run()`        | 重复调用抛 `IllegalThreadStateException` |
| `run()`               | 线程体                           | 直接调用不会开启新线程                         |
| `join()` / `join(ms)` | 等待目标线程结束                      | 底层是 `wait()`，会释放目标线程对象锁             |
| `sleep(ms)`           | 休眠，**不释放**已持有的锁               | 是 `Thread` 静态方法，响应中断                |
| `yield()`             | 让出 CPU，重回就绪态                  | 只是提示，不保证生效                          |
| `wait()` / `notify()` | 等待/通知，必须在 `synchronized` 块内调用 | `Object` 的方法，会释放锁                   |
| `interrupt()`         | 设置中断标志                        | 不强行终止线程                             |

### `sleep` vs `wait`

| 对比项 | `sleep` | `wait` |
|--------|---------|--------|
| 所属类 | `Thread` 静态方法 | `Object` 实例方法 |
| 是否释放锁 | 不释放 | 释放 |
| 使用条件 | 任意位置 | 必须在同步块/同步方法中 |
| 唤醒方式 | 时间到 | `notify()`/`notifyAll()` 或被中断 |

### 中断机制

`interrupt()` 只是给线程打一个「中断标志」，线程自己决定如何响应：

```java
Thread worker = new Thread(() -> {
    while (!Thread.currentThread().isInterrupted()) {  // 1. 主动检查标志
        try {
            TimeUnit.SECONDS.sleep(1);
        } catch (InterruptedException e) {
            // 2. sleep/wait/join 被中断时会抛异常，并【清除】中断标志
            Thread.currentThread().interrupt();        // 3. 恢复标志，向上传递
            break;
        }
    }
    System.out.println("线程已退出");
});
worker.start();
TimeUnit.SECONDS.sleep(3);
worker.interrupt();
```

要点：
- `isInterrupted()`：查询标志，**不清除**。
- `Thread.interrupted()`：静态方法，查询并**清除**标志。
- 阻塞方法（`sleep`/`wait`/`join`）被中断时抛 `InterruptedException` 并清除标志，所以捕获后通常需要重新 `interrupt()` 恢复标志，否则上层无法感知。
- 不要用已废弃的 `stop()`/`suspend()`——强行终止会导致锁未释放、数据不一致。

---

## 五、线程安全的三个来源

并发问题归根结底来自三个特性被破坏：

| 特性  | 含义                  | 破坏原因          | 解决手段                              |
| --- | ------------------- | ------------- | --------------------------------- |
| 原子性 | 一组操作要么全做要么不做，中间不被打断 | 线程切换          | `synchronized`、`Lock`、原子类         |
| 可见性 | 一个线程修改共享变量，其他线程立即可见 | 工作内存缓存        | `volatile`、`synchronized`、`final` |
| 有序性 | 代码执行顺序符合预期          | 编译器/CPU 指令重排序 | `volatile`、`happens-before` 规则    |

### JMM（Java 内存模型）

JMM 规定：所有共享变量存于**主内存**，每个线程有自己的**工作内存**（CPU 缓存/寄存器抽象），线程对变量的读写在工作内存中进行，再同步回主内存。

```text
   线程A                              线程B
 ┌────────┐                         ┌────────┐
 │工作内存│                         │工作内存│
 │ x = 1  │                         │ x = 0  │  ← 读到的是旧值
 └───┬────┘                         └───▲────┘
     │ write                      read │
     ▼                                 │
 ┌────────────────────────────────────────┐
 │              主内存  x = 1              │
 └────────────────────────────────────────┘
```

### happens-before 规则

JMM 通过 happens-before 描述「前一个操作的结果对后一个操作可见」。程序员只需遵守这些规则，无需关心底层内存屏障：

1. **程序次序规则**：单线程内，前面的操作 happens-before 后面的操作。
2. **volatile 规则**：对 volatile 变量的写 happens-before 后续对该变量的读。
3. **传递性**：A hb B，B hb C，则 A hb C。
4. **锁规则**：解锁 happens-before 随后的加锁。
5. **线程启动规则**：`start()` happens-before 线程内的任何操作。
6. **线程终止规则**：线程内任何操作 happens-before 其他线程检测到该线程结束（`join()` 返回或 `isAlive()` 为 false）。
7. **中断规则**：`interrupt()` happens-before 被中断线程检测到中断。
8. **对象终结规则**：对象构造完成 happens-before `finalize()` 开始。

---

## 六、volatile

`volatile` 提供两件事：

1. **可见性**：写操作立即刷新到主内存，读操作从主内存读取。
2. **禁止指令重排序**：通过内存屏障实现。

```java
class ConfigHolder {
    private volatile boolean inited = false;

    public void init() {
        // 初始化逻辑
        inited = true;  // volatile 写：保证上面的初始化不会被重排到这之后
    }

    public void doWork() {
        if (inited) {   // volatile 读：保证能看到完整的初始化结果
            // 安全使用
        }
    }
}
```

> **volatile 不保证原子性**。`volatile int i` 的 `i++` 在并发下依然会丢失更新，
> 因为 `i++` 是「读-改-写」三步。需要原子性时用 `synchronized`、`Lock` 或 `AtomicInteger`。

**典型用法**：
- 状态标志位（如停止线程的开关）。
- 双重检查锁（DCL）单例中的实例字段。
- 独立观察（一个线程写、多个线程读）。

---

## 七、synchronized

### 三种用法

```java
// 1. 修饰实例方法：锁是当前实例对象 this
public synchronized void methodA() { }

// 2. 修饰静态方法：锁是当前类的 Class 对象
public static synchronized void methodB() { }

// 3. 修饰代码块：锁是括号内指定的对象（推荐，粒度可控）
private final Object lock = new Object();
public void methodC() {
    synchronized (lock) {
        // 临界区
    }
}
```

### 实现原理

`synchronized` 基于 JVM 内置的 **Monitor（管程）** 实现。编译后会在代码块前后插入 `monitorenter` 和 `monitorexit` 字节码指令。

JDK 6 之后引入了锁升级（膨胀）机制，避免直接使用重量级锁的开销：

```text
无锁 → 偏向锁 → 轻量级锁（CAS 自旋） → 重量级锁（Monitor，线程挂起）
```

| 锁状态 | 适用场景 | 特点 |
|--------|----------|------|
| 偏向锁 | 只有一个线程访问 | 记录线程 ID，几乎无开销。**JDK 15 起默认禁用**（JEP 374） |
| 轻量级锁 | 少量线程交替执行，持锁时间短 | CAS 自旋，不阻塞线程 |
| 重量级锁 | 多线程激烈竞争 | 未获锁线程阻塞挂起，涉及内核态切换 |

锁只能升级不能降级（偏向锁可撤销）。

### synchronized vs Lock

| 对比项 | `synchronized` | `ReentrantLock` |
|--------|----------------|-----------------|
| 实现方式 | JVM 关键字，自动释放锁 | JDK 层 AQS，需手动 `unlock()` |
| 释放锁 | 代码块结束或异常自动释放 | 必须在 `finally` 中释放 |
| 可中断 | 不可中断 | `lockInterruptibly()` 支持 |
| 超时 | 不支持 | `tryLock(timeout)` 支持 |
| 公平性 | 非公平 | 可构造公平锁（有性能损耗） |
| 条件队列 | 单个 `wait`/`notify` | 多个 `Condition`，可分组唤醒 |
| 性能 | JDK 6 优化后两者接近 | 高争用下更稳定 |

**优先使用 `synchronized`**（简洁、不易出错），需要可中断/超时/多条件队列时才用 `Lock`。

---

## 八、Lock 体系

### ReentrantLock

```java
private final ReentrantLock lock = new ReentrantLock(true); // true = 公平锁

public void transfer(Account from, Account to, int amount) {
    lock.lock();
    try {
        from.debit(amount);
        to.credit(amount);
    } finally {
        lock.unlock();  // 必须放 finally
    }
}

// 超时获取锁，避免无限等待
if (lock.tryLock(3, TimeUnit.SECONDS)) {
    try { /* 临界区 */ } finally { lock.unlock(); }
} else {
    log.warn("获取锁超时，放弃操作");
}
```

### Condition

一个 `Lock` 可以绑定多个 `Condition`，实现精准唤醒——这是 `wait/notify` 做不到的：

```java
class BoundedBuffer<T> {
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notFull  = lock.newCondition();
    private final Condition notEmpty = lock.newCondition();
    private final Object[] items = new Object[100];
    private int putPtr, takePtr, count;

    public void put(T x) throws InterruptedException {
        lock.lock();
        try {
            while (count == items.length) notFull.await();   // 队列满，等空位
            items[putPtr] = x;
            if (++putPtr == items.length) putPtr = 0;
            ++count;
            notEmpty.signal();                               // 只唤醒消费者
        } finally { lock.unlock(); }
    }

    @SuppressWarnings("unchecked")
    public T take() throws InterruptedException {
        lock.lock();
        try {
            while (count == 0) notEmpty.await();             // 队列空，等数据
            T x = (T) items[takePtr];
            if (++takePtr == items.length) takePtr = 0;
            --count;
            notFull.signal();                                // 只唤醒生产者
            return x;
        } finally { lock.unlock(); }
    }
}
```

> **为什么用 `while` 而不是 `if` 判断等待条件？** 因为存在「虚假唤醒」（spurious wakeup），被唤醒后条件可能已被其他线程改变，必须重新检查。

### 读写锁与 StampedLock

| 锁 | 特点 | 适用场景 |
|----|------|----------|
| `ReentrantReadWriteLock` | 读读共享、读写互斥、写写互斥，可降级 | 读多写少的缓存 |
| `StampedLock` | 提供乐观读，不加锁直接读，用 stamp 校验是否被写改过 | 读极多、写极少，追求极致吞吐 |

```java
// StampedLock 乐观读
private final StampedLock sl = new StampedLock();

public double distanceFromOrigin() {
    long stamp = sl.tryOptimisticRead();   // 不加锁，拿一个戳
    double cx = x, cy = y;
    if (!sl.validate(stamp)) {             // 期间被写过，退化为悲观读锁
        stamp = sl.readLock();
        try { cx = x; cy = y; }
        finally { sl.unlockRead(stamp); }
    }
    return Math.sqrt(cx * cx + cy * cy);
}
```

---

## 九、CAS 与原子类

CAS（Compare And Swap）是无锁算法的基石，CPU 原语保证原子性，包含三个操作数：内存位置 V、预期值 A、新值 B。当且仅当 V == A 时，将 V 更新为 B。

```text
 期望值 A        内存值 V        结果
 ─────────     ─────────     ─────────
   1     ==       1      →   更新为 2，返回 true
   1     !=       3      →   不更新，返回 false（自旋重试）
```

| 类 | 说明 |
|----|------|
| `AtomicInteger` / `AtomicLong` / `AtomicBoolean` | 基本类型原子更新 |
| `AtomicReference` | 对象引用原子更新 |
| `AtomicStampedReference` | 带版本号，解决 **ABA 问题** |
| `AtomicIntegerArray` | 数组元素原子更新 |
| `LongAdder` / `DoubleAdder` | 分段累加，高并发计数下性能远超 `AtomicLong` |
| `LongAccumulator` | 支持自定义累加规则 |

```java
// 计数：高并发下 LongAdder 明显优于 AtomicLong
private final LongAdder requestCount = new LongAdder();

public void handle() {
    requestCount.increment();
}

public long total() {
    return requestCount.sum();  // 注意：并发下 sum() 不是精确快照
}
```

**CAS 的三个问题**：
1. **ABA 问题**：值从 A 变 B 又变回 A，CAS 会误判为没变化。用 `AtomicStampedReference` 加版本号解决。
2. **自旋开销大**：竞争激烈时长时间空转。JDK 8 引入的 `LongAdder` 用「分段」分散热点。
3. **只能保证一个变量的原子操作**：多个变量需用 `AtomicReference` 封装成对象。

---

## 十、ThreadLocal

`ThreadLocal` 给每个线程提供一份独立的变量副本，常用于保存用户信息、TraceId、数据库连接等上下文。

```java
public class UserContext {
    private static final ThreadLocal<User> HOLDER = new ThreadLocal<>();

    public static void set(User user) { HOLDER.set(user); }
    public static User get() { return HOLDER.get(); }
    public static void clear() { HOLDER.remove(); }  // 必须清理
}
```

### 内存泄漏问题

`ThreadLocalMap` 中的 key 是**弱引用**的 `ThreadLocal`，value 是强引用。
当 `ThreadLocal` 对象被回收后，key 变成 `null`，但 value 仍被线程强引用：

```text
Thread → ThreadLocalMap → Entry(key=null(弱引用), value=强引用) → 泄漏的对象
```

如果线程是**线程池中的常驻线程**，生命周期与 JVM 同长，value 永远无法回收 → 内存泄漏，且会造成**脏数据**（读到上一个请求的用户信息）。

**正确用法**：

```java
try {
    UserContext.set(currentUser);
    // 业务逻辑
} finally {
    UserContext.clear();   // 必须在 finally 中 remove
}
```

> 在线程池场景下这一条是硬要求，也是面试高频考点。更完善的方案是用 `TransmittableThreadLocal`（阿里开源）解决线程池跨线程传递问题。

---

## 十一、并发容器

| 容器 | 实现要点 | 适用场景 |
|------|----------|----------|
| `ConcurrentHashMap` | JDK 8 起：数组 + 链表/红黑树（链表 ≥ 8 且容量 ≥ 64 时树化），对**单个桶**用 CAS + `synchronized`，读操作无锁 | 高并发 KV 缓存 |
| `CopyOnWriteArrayList` | 写时复制整个数组，读完全无锁 | 读极多写极少（如监听器列表、黑白名单） |
| `ConcurrentLinkedQueue` | 无界非阻塞队列，CAS 实现 | 高并发生产者消费者 |
| `BlockingQueue` 系列 | 阻塞式入队/出队 | 线程池工作队列、生产者消费者 |
| `ConcurrentSkipListMap` | 跳表实现，有序 | 需要排序的并发 Map |

`BlockingQueue` 常见实现：

| 实现 | 是否有界 | 特点 |
|------|----------|------|
| `ArrayBlockingQueue` | 有界（构造时指定） | 数组实现，单锁，吞吐稳定 |
| `LinkedBlockingQueue` | 可选（默认 `Integer.MAX_VALUE`，相当于无界） | 双锁（put/take 分离），吞吐高 |
| `SynchronousQueue` | 不存储元素 | 直接移交，配 `CachedThreadPool` 用 |
| `PriorityBlockingQueue` | 无界 | 按优先级出队 |
| `DelayQueue` | 无界 | 延迟到期才能取出，用于定时/缓存过期 |

`ConcurrentHashMap` 的**复合操作**仍需加锁或用 `computeIfAbsent` 等原子方法：

```java
// 错误：先判空再 put，仍然存在竞态
if (!map.containsKey(key)) {
    map.put(key, createValue());
}

// 正确：原子方法
map.computeIfAbsent(key, k -> createValue());
```

---

## 十二、同步工具

| 工具 | 作用 | 是否可复用 | 典型场景 |
|------|------|-----------|----------|
| `CountDownLatch` | 一个或多个线程等待其他线程完成 | 否（计数归零即失效） | 主线程等待多个服务初始化完成 |
| `CyclicBarrier` | 一组线程互相等待，到达屏障点后一起继续 | 是 | 多线程分阶段计算，最后汇总 |
| `Semaphore` | 控制同时访问资源的线程数（许可） | 是 | 限流、接口并发度控制 |
| `Phaser` | 更灵活的多阶段屏障，支持动态注册 | 是 | 复杂分阶段任务 |
| `Exchanger` | 两个线程在汇合点交换数据 | 是 | 双缓冲、校对数据 |

```java
// CountDownLatch：主线程等待 3 个初始化任务完成
CountDownLatch latch = new CountDownLatch(3);
for (int i = 0; i < 3; i++) {
    executor.submit(() -> {
        try { initModule(); }
        finally { latch.countDown(); }   // 必须放 finally，避免异常导致永久阻塞
    });
}
latch.await(10, TimeUnit.SECONDS);       // 建议带超时

// CyclicBarrier：所有线程到达后再一起进入下一阶段
CyclicBarrier barrier = new CyclicBarrier(4, () -> log.info("本阶段完成，开始汇总"));
for (int i = 0; i < 4; i++) {
    executor.submit(() -> {
        computePhase();
        barrier.await();
        nextPhase();
    });
}

// Semaphore：限制接口并发数为 20
Semaphore semaphore = new Semaphore(20);
public Response call() {
    if (!semaphore.tryAcquire(100, TimeUnit.MILLISECONDS)) {
        throw new RuntimeException("系统繁忙");
    }
    try { return doCall(); }
    finally { semaphore.release(); }
}
```

---

## 十三、死锁

### 四个必要条件（缺一不可）

1. **互斥**：资源一次只能被一个线程持有。
2. **占有且等待**：持有一个资源的同时等待另一个资源。
3. **不可抢占**：已获得的资源不能被强行抢占。
4. **循环等待**：存在一个首尾相接的等待链。

### 典型死锁代码

```java
// 线程1：锁 A → 等 B ； 线程2：锁 B → 等 A
void transfer(Account from, Account to, int amount) {
    synchronized (from) {
        synchronized (to) {        // 顺序相反就会死锁
            from.debit(amount);
            to.credit(amount);
        }
    }
}
```

### 预防与排查

| 手段 | 说明 |
|------|------|
| **固定加锁顺序** | 按对象 hash 或 ID 排序后依次加锁，破坏「循环等待」 |
| **一次性申请全部资源** | 破坏「占有且等待」 |
| **使用带超时的锁** | `tryLock(timeout)`，超时释放已持有的锁后重试 |
| **减少锁粒度** | 缩小 `synchronized` 范围，降低碰撞概率 |

排查工具：
- `jstack <pid>`：JVM 会自动检测并输出 `Found one Java-level deadlock`。
- `jconsole` / `VisualVM`：图形化查看线程状态。
- Arthas `thread -b`：一键定位阻塞其他线程的「罪魁祸首」。

---

## 十四、避坑清单

1. `run()` 与 `start()` 混淆，导致根本没有开启新线程。
2. 认为 `volatile` 能保证原子性（`i++` 依然不安全）。
3. `sleep()` 不释放锁，持锁休眠会阻塞其他线程。
4. `wait()` 用 `if` 判断条件，未处理虚假唤醒。
5. `notify()` 只随机唤醒一个线程，可能唤醒同类线程导致「信号丢失」——优先用 `notifyAll()` 或 `Condition`。
6. `Lock` 未在 `finally` 中 `unlock()`，异常时锁永远不释放。
7. 线程池中使用 `ThreadLocal` 未 `remove()`，导致内存泄漏与脏数据。
8. `ConcurrentHashMap` 的复合操作（先判空再 put）不是原子的，需用 `putIfAbsent`/`computeIfAbsent`。
9. 在持有锁的情况下调用外部服务（RPC/DB），锁持有时间不可控，容易引发雪崩。
10. 用 `Thread.stop()` 强行终止线程。

---

## 参考

- 《Java 并发编程实战》
- 《深入理解 Java 虚拟机》第 12、13 章（Java 内存模型与线程安全）
- [JSR 133: Java Memory Model and Thread Specification](https://www.cs.umd.edu/~pugh/java/memoryModel/jsr133.pdf)
- [JEP 374: Deprecate and Disable Biased Locking](https://openjdk.org/jeps/374)
- 红蜘蛛并发编程教程：<https://redspider.gitbook.io/concurrent>
