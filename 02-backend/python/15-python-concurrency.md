---
title: Python 并发与并行
description: GIL 的真实约束、threading 同步原语与竞态复现、concurrent.futures 线程池与进程池、子解释器，以及三者的选型矩阵
tags:
  - python
  - concurrency
  - threading
  - multiprocessing
  - gil
date: 2026-11-06
aliases:
  - python-threading
  - python-concurrent-futures
  - python-gil
---

# Python 并发与并行

> **版本基线**：`ThreadPoolExecutor.shutdown(cancel_futures=)` 3.9；free-threaded 构建 3.13 实验性、
> 3.14 起官方支持（PEP 779）；`concurrent.interpreters` / `InterpreterPoolExecutor` 3.14。
> 实测环境：CPython 3.13.12，12 核 Apple Silicon。

## 1. 先分清三个词

| 概念 | 含义 | Python 中的手段 | 是否真同时执行 |
|------|------|-----------------|----------------|
| 并发（concurrency） | 多个任务**交替推进**，任一时刻只有一个在跑 | 线程、协程 | 否 |
| 并行（parallelism） | 多个任务**同时**在多个核上跑 | 多进程、子解释器 | 是 |
| 异步（async） | 单线程内用事件循环调度，遇 I/O 主动让出 | `asyncio` | 否 |

三者不是替代关系：一个服务可以同时用 asyncio 处理连接、用线程池跑阻塞库、
用进程池做 CPU 密集的向量计算。选型的唯一依据是**任务在等什么**。

## 2. GIL：到底限制了谁

GIL（Global Interpreter Lock）是 CPython 的一把全局锁：**同一时刻只允许一个线程执行
Python 字节码**。这句话常被简化成"Python 多线程是假的"，这个说法既不准确也没有指导意义。

准确的说法是：GIL 限制的是**纯 Python 字节码的并行**，以下三类工作不受影响：

| 工作类型 | 是否受 GIL 限制 | 原因 |
|----------|-----------------|------|
| 纯 Python 计算（循环、字符串拼接） | 受限制 | 全程持有 GIL |
| 阻塞式 I/O（`read`、`sleep`、网络请求） | 不受限制 | 系统调用期间主动释放 GIL |
| C 扩展内部计算（NumPy、PyTorch 的核函数） | 通常不受限制 | 扩展自行释放 GIL |

### 2.1 实测：线程 vs 进程

同一份 CPU 密集任务，分别用串行、4 线程、4 进程执行：

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def cpu_task(n):
    total = 0
    for i in range(n):
        total += i * i % 7
    return total

def run_threads(jobs, n, workers):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(cpu_task, [n] * jobs))

def run_processes(jobs, n, workers):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(cpu_task, [n] * jobs))
```

4 个任务、每个 4000 万次循环、4 个 worker：

| 执行方式 | 耗时 | 加速比 |
|----------|------|--------|
| 串行 | 5.12 s | 1.00x |
| 线程池（4 线程） | 4.63 s | **1.11x** |
| 进程池（4 进程） | 1.46 s | **3.51x** |

线程几乎没提速——4 个线程在抢同一把 GIL；进程接近线性（3.51x 而非 4x，
差的部分是进程启动与结果序列化开销）。

### 2.2 实测：I/O 密集正好相反

8 个各 `sleep(0.5)` 的任务：

| 执行方式 | 耗时 | 加速比 |
|----------|------|--------|
| 串行 | 4.03 s | 1.00x |
| 线程池（8 线程） | 0.51 s | **7.97x** |

`sleep` 期间线程释放 GIL，8 个等待完全重叠。**这两张表就是选型的全部依据**：
I/O 等待用线程或协程，CPU 计算用进程。

### 2.3 free-threaded 构建（3.13 实验 → 3.14 官方支持）

PEP 703 提供了可关闭 GIL 的构建（`python3.13t`）。3.13 阶段是实验性的，
3.14 起按 PEP 779 转为**官方支持**，代价是单线程性能下降约 5-10%（官方文档口径）。

是否运行在无 GIL 构建上可以运行时查询：

```python
import sys

if hasattr(sys, "_is_gil_enabled"):
    print(sys._is_gil_enabled())    # False 表示 free-threaded 构建且已关闭 GIL
```

三点现实约束，决定它短期内不会成为默认选择：

- 需要专门编译安装（官方安装包提供独立变体），不是 `python3` 的默认构建；
- 依赖的 C 扩展必须重新编译并声明线程安全，否则会在无 GIL 下出错；
- 无 GIL 不等于"不用锁"——**共享可变状态依然需要同步**，只是锁的粒度可以更细。

> 结论：当前做 CPU 密集加速，仍应优先用进程池或子解释器；free-threaded 适合
> "大量线程 + 大量共享状态"的特定场景，且要等生态跟上。

## 3. 选型矩阵

| 任务特征 | 首选 | 备选 | 不要用 |
|----------|------|------|--------|
| 网络 / 磁盘 I/O，高并发连接 | `asyncio` | 线程池 | 进程池（开销大于收益） |
| 调用阻塞式第三方库（requests、SDK） | 线程池 | `asyncio.to_thread` | 手写线程管理 |
| 纯 Python CPU 计算 | 进程池 | 子解释器（3.14+） | 线程池（GIL 白等） |
| NumPy / PyTorch 张量运算 | 库内部已并行，通常无需自己并行 | 进程池（多机/多卡另说） | 再套线程池 |
| 需要共享大量可变状态 | 线程池 + 锁 | 协程（单线程天然无竞态） | 进程池（要序列化） |
| 任务数远大于核数、单任务很短 | 固定大小线程/进程池复用 | `map` 分批 | 每任务启一个进程 |

一条经验规则：**先测再选**。任务耗时里 I/O 等待占比超过一半就是 I/O 密集；
反之是 CPU 密集。凭直觉判断往往错——序列化、日志、锁竞争都可能把"看起来是 CPU"的任务
变成 I/O 密集。

## 4. threading：线程与同步原语

### 4.1 线程的创建与回收

```python
import threading

def fetch(url):
    ...

worker = threading.Thread(target=fetch, args=("https://example.com",), name="fetch-1")
worker.start()
worker.join(timeout=5)          # 最多等 5 秒
print(worker.is_alive())
```

`join()` 是**必须**的：不 join 的线程会在后台继续跑，主线程退出后可能被强行终止，
造成文件写一半、事务未提交。`daemon=True` 的线程则随主线程一起被杀死，
只适合"日志上报"这类丢了也无所谓的任务。

### 4.2 竞态：单条 `+=` 也不是原子的

这是 Python 多线程最容易误判的地方。`self.value += 1` 实际是"读-改-写"三步，
线程可能在任意两步之间被切换：

```python
import threading, time

class Counter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def add_unsafe(self):
        current = self.value
        time.sleep(0)              # 释放 GIL 强制切换，放大窗口
        self.value = current + 1

    def add_safe(self):
        with self._lock:
            current = self.value
            time.sleep(0)
            self.value = current + 1
```

8 线程各加 2000 次，实测结果：

```text
add_unsafe   期望 2000, 实际 353     ← 大量更新互相覆盖
add_safe     期望 2000, 实际 2000
```

注意：不加 `time.sleep(0)` 时这个 bug 往往**跑不出来**（GIL 默认 5ms 才切换一次，
2000 次加法在 5ms 内就跑完了）。这解释了为什么竞态 bug 总在线上偶发——
它依赖调度时机，而调度时机随负载变化。

### 4.3 同步原语速查

| 原语 | 用途 | 关键行为 |
|------|------|----------|
| `Lock` | 互斥访问 | 不可重入，同一线程重复获取会死锁 |
| `RLock` | 可重入互斥 | 同一线程可多次获取，需同样次数释放 |
| `Event` | 一次性信号广播 | `set()` 后 `wait()` 立即返回；跨线程启动顺序解耦 |
| `Condition` | 等待某个条件成立 | 配合 `while` 循环检查条件，避免虚假唤醒 |
| `Semaphore` | 限制并发数 | 常用于连接池、限流 |
| `Barrier` | 等待 N 个线程到齐 | 用于分阶段并行计算 |
| `local` | 线程私有存储 | 每线程独立命名空间，适合 trace_id 这类上下文 |

`Event` 的典型用法——让消费者不必关心生产者的启动顺序：

```python
import threading

ready = threading.Event()
result = {}

def producer():
    result["payload"] = "data"
    ready.set()

def consumer():
    ready.wait(timeout=1.0)       # 等到有数据（或超时）
    print(result.get("payload"))

t1 = threading.Thread(target=consumer)
t2 = threading.Thread(target=producer)
t1.start(); t2.start(); t1.join(); t2.join()
```

`threading.local` 解决"共享变量被其他线程覆盖"的问题：

```python
import threading

state = threading.local()

def worker(name):
    state.trace_id = name          # 每个线程独立，互不覆盖
    return state.trace_id
```

用线程池时要注意：**线程是复用的**，`local` 里的值会残留到下一个任务。
必须在任务开始时显式重置，否则会串数据。

### 4.4 死锁：固定加锁顺序

两个线程以相反顺序获取两把锁就会死锁。唯一可靠的工程手段是**全局约定加锁顺序**：

```python
def safe_transfer(from_acc, to_acc):
    first, second = sorted((from_acc, to_acc), key=id)   # 统一顺序
    with first.lock, second.lock:
        ...
```

更好的做法是**避免同时持有两把锁**：先完成一次操作、释放，再做下一次。
嵌套锁的需求通常来自设计问题，而非真实约束。

## 5. concurrent.futures：优先用它而不是手写线程

`threading.Thread` 适合长期运行的后台任务；**一次性任务的批量执行应该用执行器**——
它负责线程复用、异常收集、结果顺序、优雅关闭。

### 5.1 四个 API 的语义差别

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

def job(i):
    time.sleep(0.1 * (3 - i))
    return i

# map：结果顺序 = 输入顺序，异常在迭代到该项时抛出
with ThreadPoolExecutor(max_workers=3) as pool:
    print(list(pool.map(job, range(3))))          # [0, 1, 2]

# submit + as_completed：按完成顺序拿结果
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = [pool.submit(job, i) for i in range(3)]
    print([f.result() for f in as_completed(futures)])   # [2, 1, 0]
```

| API | 结果顺序 | 异常处理 | 适用 |
|-----|----------|----------|------|
| `pool.map(fn, it)` | 输入顺序 | 迭代到失败项时抛出，**其余任务不被取消** | 批量转换、结果要与输入对齐 |
| `pool.submit(fn)` | 手动 | `future.exception()` / `.result()` 取 | 需要单个 Future 做组合 |
| `as_completed(fs)` | 完成顺序 | 逐个 `result()` 抛 | 谁先好先处理、超时逐出 |
| `wait(fs, return_when=...)` | 不产出结果 | 只等状态 | 需要"第一个完成就继续" |

`map` 的异常时机需要特别注意：

```python
from concurrent.futures import ThreadPoolExecutor

def boom(i):
    if i == 1:
        raise ValueError(f"第 {i} 个失败")
    return i

with ThreadPoolExecutor(max_workers=2) as pool:
    it = pool.map(boom, range(3))
    next(it)        # 0，正常
    next(it)        # 这里才抛 ValueError: 第 1 个失败
```

如果不开迭代，异常永远不会暴露——**`pool.map` 不用 `list()` 消费一遍就等于吞掉异常**。

### 5.2 关闭与取消

```python
import time
from concurrent.futures import ThreadPoolExecutor

pool = ThreadPoolExecutor(max_workers=4)
try:
    futures = [pool.submit(time.sleep, 1) for _ in range(100)]
finally:
    pool.shutdown(wait=False, cancel_futures=True)   # 3.9+
```

`cancel_futures=True` 只会取消**尚未开始**的任务；正在执行的任务无法被强制中断
（Python 没有安全的线程 kill）。要能中断，任务本身必须周期性检查一个 `Event`。

用 `with ThreadPoolExecutor(...)` 时，退出会自动 `shutdown(wait=True)`，
即等待所有任务结束。这在"任务可能卡住"时会导致进程无法退出——此时应显式管理生命周期。

### 5.3 进程池的三条硬约束

```python
from concurrent.futures import ProcessPoolExecutor

def count_primes(limit: int) -> int:
    return sum(all(n % d for d in range(2, int(n ** 0.5) + 1)) for n in range(2, limit))

if __name__ == "__main__":                 # macOS/Windows 必须
    with ProcessPoolExecutor() as pool:
        print(pool.submit(count_primes, 200_000).result())
```

| 约束 | 原因 | 症状 |
|------|------|------|
| 入口必须放在 `if __name__ == "__main__":` 下 | spawn 启动方式会重新导入主模块 | 无限递归创建进程，或 `RuntimeError` / `BrokenProcessPool` |
| 参数与返回值必须可 pickle | 跨进程通过管道传输 | `TypeError: cannot pickle 'XxxType' object` |
| 子进程不共享内存 | 每个进程独立解释器 | 在子进程里改全局变量，主进程看不到 |

第三条常被误认为 bug：进程池里函数修改了模块级变量，主进程读到的还是旧值。
需要汇总结果就靠返回值；需要共享状态就得用 `multiprocessing.Manager`
（有序列化开销，通常不值得）。

### 5.4 3.14 的相关变化

| 变化 | 影响 |
|------|------|
| Linux 上 `ProcessPoolExecutor` 默认启动方式改为 `forkserver` | 依赖 `fork` 继承父进程状态的代码需显式传 `mp_context` |
| 新增 `terminate_workers()` / `kill_workers()` | 卡死的进程池终于有强制回收手段 |
| `Executor.map` 新增 `buffersize` | 限制"已提交但未消费"的任务数，避免大迭代器撑爆内存 |

## 6. 子解释器：进程的隔离 + 线程的开销（3.14+）

PEP 734 让"同一进程内的多个解释器"进入标准库，每个解释器有自己的 GIL
（3.12 起支持），因此可以真正并行，同时避免进程间的序列化成本：

```python
# 需要 Python 3.14+，3.13 及以下没有 concurrent.futures.InterpreterPoolExecutor
from concurrent.futures import InterpreterPoolExecutor

def count_primes(limit: int) -> int:
    return sum(all(n % d for d in range(2, int(n ** 0.5) + 1)) for n in range(2, limit))

if __name__ == "__main__":
    with InterpreterPoolExecutor(max_workers=4) as pool:
        print(pool.submit(count_primes, 200_000).result())
```

| 维度 | 线程 | 进程 | 子解释器 |
|------|------|------|----------|
| 真并行 | 否（GIL） | 是 | 是（各自一把 GIL） |
| 创建开销 | 低 | 高（fork/spawn） | 中 |
| 共享数据 | 直接共享 | 需 pickle / Manager | 选项很少（目前主要 `memoryview`） |
| 第三方 C 扩展兼容性 | 好 | 好 | 部分不兼容（标准库扩展全兼容） |
| 崩溃影响 | 拖垮整个进程 | 隔离 | 隔离 |

现状判断：3.14 已可用，但"跨解释器共享对象"的机制还很少，
第三方扩展兼容性也未铺开。**当前生产环境的默认选择仍是进程池**，
子解释器适合"任务纯 Python、需要频繁调用、又不想付进程启动成本"的场景。

## 7. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| "多线程能加速 Python 计算" | 纯 Python 计算受 GIL 限制，实测仅 1.11x | CPU 密集改用进程池 |
| "有 GIL 就不用加锁" | GIL 只保证字节码不并行，`+=` 仍是读改写三步 | 共享可变状态必须用 `Lock` |
| "线程池线程是 daemon" | `ThreadPoolExecutor` 的线程是非 daemon，解释器退出会 join | 长任务要显式 `shutdown(wait=False)` |
| "`cancel_futures` 能中断运行中的任务" | 只能取消未开始的任务 | 任务内部检查 `Event` 主动退出 |
| "`pool.map` 会等所有任务完成" | 返回生成器，不消费就不执行也不抛异常 | 用 `list()` 或 `for` 消费 |
| "进程池函数里改全局变量主进程能看到" | 进程间内存独立 | 用返回值汇总，或改用共享内存 |
| "`threading.local` 在线程池里安全" | 线程被复用，`local` 值会残留 | 任务开始时重置 |
| "`sleep` 能当同步手段" | 轮询 `sleep` 既慢又不可靠 | 用 `Event` / `Condition` |
| "进程越多越快" | 超过核数后是调度开销与内存压力 | worker 数 ≈ 核数（I/O 密集可更多） |
| "加了锁就线程安全" | 锁保护的是临界区，锁外访问依然可能读到中间状态 | 明确不变量，读也要在同一把锁内 |

## 8. 与相关概念的关系

- **与 [[04-python-async|Python 异步编程]]**：asyncio 是单线程协程调度，天然无数据竞态，
  但阻塞调用会卡死整个事件循环——必须用 `asyncio.to_thread` 或 `run_in_executor`
  把阻塞库丢进线程池。两者的选型边界见该文第 6 节。
- **与 [[13-python-exceptions|Python 异常处理]]**：线程池里的异常保存在 Future 中，
  不调用 `result()` 就永远不会抛出；进程池的异常需要能 pickle 才能传回主进程。
- **与 [[14-context-managers|Python 上下文管理器]]**：`with ThreadPoolExecutor(...)`
  靠 `__exit__` 保证 `shutdown(wait=True)`；`ExitStack` 可用于动态管理多个池。
- **与 [[18-debugging-profiling|调试与性能分析]]**：线程死锁、进程卡死用 `faulthandler`
  与 `py-spy` 定位；优化前先 profile，确认瓶颈真的在 CPU 而不是 I/O。

## 参考

- [threading — Thread-based parallelism](https://docs.python.org/3/library/threading.html)
- [concurrent.futures — Launching parallel tasks](https://docs.python.org/3/library/concurrent.futures.html)
- [PEP 703 – Making the GIL Optional](https://peps.python.org/pep-0703/)
- [PEP 734 – Multiple Interpreters in the Stdlib](https://peps.python.org/pep-0734/)
- [PEP 779 – Criteria for accepting free-threaded Python](https://peps.python.org/pep-0779/)
- [What's New in Python 3.14](https://docs.python.org/3/whatsnew/3.14.html)
