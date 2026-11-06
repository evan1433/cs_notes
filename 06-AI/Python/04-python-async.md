---
title: Python 异步编程
description: asyncio 的协程模型、事件循环调度机制、Task 与 TaskGroup、取消与超时，以及同步库接入异步世界的取舍
tags:
  - python
  - asyncio
  - concurrency
  - ai
date: 2026-11-05
aliases:
  - python-async
  - python-asyncio
---

# Python 异步编程

Python 的 `async` 和 `await` 是用于编写**异步代码**的关键字，构成 Python 的异步编程模型（基于协程）。特别适合处理 I/O 密集型任务，如网络请求、文件操作等。

异步编程想解决的问题只有一个：**等待 I/O 的时间里，线程不要空转**。理解了这一点，`await` 为什么必须存在、为什么一个 `time.sleep` 就能把整条流水线卡死，都变得顺理成章。

> **版本基线**：本文示例以 Python 3.11+ 为基线（`asyncio.TaskGroup`、`asyncio.timeout` 均自 3.11 引入）。
> 截至 2026 年 11 月，Python 最新稳定系列为 3.15（3.15.2），此前系列为 3.14（3.14.10）。
> 涉及版本差异的 API 会在小节内单独标注。

---

## 1. 异步到底解决什么问题

### 三种并发模型的分工

Python 里做并发有三条路，它们不是替代关系而是分工关系：

| 模型 | 调度方式 | 能否利用多核 | 切换成本 | 适合的负载 |
|------|----------|--------------|----------|------------|
| 多进程 `multiprocessing` | 操作系统调度 | 能（各自独立解释器） | 高（进程创建/序列化） | CPU 密集型：计算、编解码 |
| 多线程 `threading` | 操作系统抢占式调度 | 不能（GIL 限制纯 Python 计算） | 中（内核切换 + 锁竞争） | 阻塞式 I/O、调用无异步版本的库 |
| 协程 `asyncio` | 事件循环协作式调度 | 不能（单线程） | 极低（一次函数调用） | 高并发 I/O：网络请求、数据库、消息队列 |

关键认知：**异步不会让单个任务变快，它只是把多个任务的等待时间重叠起来**。一个耗时 1 秒的网络请求，异步之后依然要 1 秒；但 100 个这样的请求可以只用 1 秒多而不是 100 秒。

```python
import asyncio
import time

async def fetch_data(source: str, delay: float) -> str:
    """用 sleep 模拟一次耗时 delay 秒的远程调用。"""
    await asyncio.sleep(delay)
    return f"{source} 数据"

async def serial() -> None:
    start = time.perf_counter()
    # 逐个 await：每个请求都要等上一个彻底结束才开始
    for source, delay in [("订单服务", 1.0), ("用户服务", 1.0), ("库存服务", 1.0)]:
        await fetch_data(source, delay)
    print(f"串行耗时 {time.perf_counter() - start:.2f}s")   # 约 3.00s

async def concurrent() -> None:
    start = time.perf_counter()
    # 三个协程同时挂起，等待时间重叠在一起
    await asyncio.gather(
        fetch_data("订单服务", 1.0),
        fetch_data("用户服务", 1.0),
        fetch_data("库存服务", 1.0),
    )
    print(f"并发耗时 {time.perf_counter() - start:.2f}s")   # 约 1.00s

asyncio.run(serial())
asyncio.run(concurrent())
```

### 什么时候不该用异步

- **CPU 密集型**：`for` 循环算哈希、图像处理、模型推理，换成协程不会更快，只会多出调度开销——应该用多进程或把计算下沉到 C 扩展。
- **依赖的库全是同步的**：整个调用链都在等 `requests`、`psycopg2` 这类阻塞接口，强行包一层协程只是把阻塞搬进了线程池，不如直接用线程。
- **一次性脚本**：只发一个请求、只读一个文件，异步带来的复杂度没有回报。

---

## 2. 核心概念

### 协程（Coroutine）

- 使用 `async def` 定义的函数
- 调用时不会立即执行，而是返回一个协程对象
- 需要事件循环来驱动执行

```python
async def my_coroutine():
    return "Hello from coroutine"
```

这三条值得展开，因为初学者 80% 的困惑都出在这里：

**① 调用 `async def` 函数不会执行任何一行函数体**，只造出一个协程对象：

```python
import asyncio
import inspect

async def my_coroutine():
    return "Hello from coroutine"

coro = my_coroutine()                       # 函数体一行都没跑
print(type(coro))                           # <class 'coroutine'>
print(inspect.getcoroutinestate(coro))      # CORO_CREATED

print(asyncio.run(coro))                    # 交给事件循环后才真正执行
```

**② 协程有明确的生命周期状态**，`inspect` 可以直接看到：

| 状态 | `inspect` 常量 | 含义 |
|------|----------------|------|
| 创建 | `CORO_CREATED` | 对象已创建，函数体尚未开始 |
| 运行 | `CORO_RUNNING` | 正在被执行 |
| 挂起 | `CORO_SUSPENDED` | 停在某个 `await` 处，等待条件满足 |
| 结束 | `CORO_CLOSED` | 已返回或已抛异常，不可再次执行 |

**③ 协程对象只能被 await 一次**。重复 await 会抛 `RuntimeError: cannot reuse already awaited coroutine`；想跑两次就重新调用函数。忘记 await 而直接丢弃协程对象时，CPython 只会打印一条 `RuntimeWarning: coroutine ... was never awaited` 然后静默丢弃——**不报错，也不执行**，这是最常见的隐形 bug。

**④ 与生成器的关系**：协程在语法上脱胎于生成器（`yield` 让出执行权的能力），但两者类型不同。老式的生成器协程装饰器 `@asyncio.coroutine` 已在 Python 3.11 中移除，现在只有原生协程（`types.CoroutineType`）。生成器本身的内容见 [[03-python-functional|Python 函数式编程]]。

### 可等待对象（Awaitable）

`await` 后面能接的东西只有三类，分清它们的区别是写出正确并发代码的前提：

| 对象 | 谁创建 | `await` 它的语义 | 典型用途 |
|------|--------|------------------|----------|
| 协程 coroutine | 调用 `async def` 函数 | **内联执行**，与调用方共用同一个任务 | 拆分层级、顺序调用 |
| Task | `asyncio.create_task()`、`TaskGroup.create_task()` | 等待**另一个调度单元**跑完 | 真正制造并发 |
| Future | `loop.create_future()`、部分底层库 | 等待一个未来才会被赋值的结果 | 框架/库内部使用，业务代码基本不手写 |

这里有个容易踩的概念坑：**`await coro` 不会产生并发**。它只是把被调协程在当前任务里展开执行，调用方让出的控制权立刻又被同一个被调协程拿走，中间没有第二个任务可跑。想并发就必须先把它变成 Task。

`asyncio.gather()` 之所以看起来"自动并发"，是因为它内部会把传入的协程**自动包装成 Task**；而 `asyncio.wait()` 在 3.11 起**禁止**直接接收协程对象，只接受 Task/Future。

### 事件循环（Event Loop）

- 异步程序的运行核心
- 负责调度和执行协程
- Python 3.7+ 使用 `asyncio.run()` 简化

```python
import asyncio

result = asyncio.run(my_coroutine())
print(result)  # 输出: Hello from coroutine
```

事件循环本质上是一个 `while True` 循环加一个 I/O 多路复用器（Linux 上是 `epoll`，macOS 上是 `kqueue`）：

1. 从**就绪队列**取出一个 Task 执行，直到它 `await` 一个未就绪的对象；
2. Task 挂起，控制权交回循环；
3. 循环把等待中的文件描述符和超时时间交给 `epoll`/`kqueue`，进入睡眠；
4. 某个 socket 可读或某个定时器到期，对应 Task 被放回就绪队列；
5. 回到第 1 步。

`asyncio.run()` 帮你做完了四件事：创建新的事件循环 → 把 `main()` 包成 Task 跑起来 → 结束时清理未关闭的异步生成器（`shutdown_asyncgens`）→ 关闭默认线程池（`shutdown_default_executor`）。所以**应用入口只该调用一次 `asyncio.run()`**，不要在函数中间反复调用。

取循环句柄时用 `asyncio.get_running_loop()`，它有明确语义：没有运行中的循环就抛 `RuntimeError`。对比之下 `asyncio.get_event_loop()` 行为复杂且正在退场：

| API | 无运行中循环时 | 状态 |
|-----|----------------|------|
| `asyncio.get_running_loop()` | 抛 `RuntimeError` | 首选，3.7+ |
| `asyncio.get_event_loop()` | 3.14 起**也抛 `RuntimeError`**（此前会隐式新建一个循环） | 逐步废弃 |
| `asyncio.get_event_loop_policy()` | —— | policy 体系已废弃，计划 3.16 移除 |

### await 表达式

- 用于挂起协程的执行，等待其他协程完成
- 只能用在 `async def` 函数内部

```python
async def main():
    result = await my_coroutine()
    print(result)
```

`await` 的准确含义不是"阻塞等它"，而是：**如果结果还没好，就保存当前执行位置，把控制权交还事件循环**。等结果就绪后，循环再从保存的位置恢复执行。因此：

- `await` 是**唯一**的切换点，不写 `await` 的代码绝不会被打断；
- 一个没有 `await` 的死循环会永久占住事件循环，整个程序假死；
- 在 `await` 前后，其他协程可能已经改动了共享状态——这就是协程也需要锁的原因（见[并发控制与同步原语](#7-并发控制与同步原语)）。

---

## 3. 一次 await 到底发生了什么

理解调度时序，比记 API 重要得多。用下面这段代码观察两个协程的交错：

```python
import asyncio

async def worker(name: str) -> None:
    print(f"{name} 开始")
    await asyncio.sleep(0.1)      # 在这里挂起，控制权回到事件循环
    print(f"{name} 结束")

async def main() -> None:
    await asyncio.gather(worker("A"), worker("B"))

asyncio.run(main())
# A 开始 → B 开始 → A 结束 → B 结束
```

输出顺序说明：`A` 打印"开始"后挂起，循环立刻去跑 `B`；两个都挂起后循环睡眠，0.1 秒后两个都就绪，按注册顺序依次恢复。整个过程**只有一个线程**，没有任何抢占。

把它和"同步阻塞"放在一起对比，差别就清楚了：

| 维度 | 同步阻塞（`time.sleep`） | 异步挂起（`await asyncio.sleep`） |
|------|--------------------------|-----------------------------------|
| 线程状态 | 内核睡眠，线程被占住 | 线程空闲，可执行其他任务 |
| 谁能感知等待 | 只有操作系统 | 事件循环（可同时挂起成千上万个） |
| 恢复方式 | 超时后由内核唤醒 | I/O 就绪事件触发回调，重新入队 |
| 1000 个并发连接的代价 | 1000 个线程（约 GB 级栈内存） | 1000 个协程对象（MB 级） |

这也解释了为什么异步常被称为"单线程内的并发"：**并发（concurrency）不等于并行（parallelism）**，前者是任务交替推进，后者是物理上同时执行。asyncio 给你的是前者。

> **调试技巧**（Python 3.14+）：卡住不动的异步程序不用猜，`python -m asyncio ps <pid>` 可以看到进程内所有任务的当前状态，`python -m asyncio pstree <pid>` 看任务的父子关系与等待链。

---

## 4. 基本用法

### 创建和运行协程

```python
import asyncio

async def say_hello():
    print("Hello")
    await asyncio.sleep(1)  # 模拟 I/O 操作
    print("World")

asyncio.run(say_hello())
```

### 并发执行多个协程

```python
import asyncio

async def task(name, seconds):
    print(f"Task {name} started")
    await asyncio.sleep(seconds)
    print(f"Task {name} completed after {seconds} seconds")

async def main():
    await asyncio.gather(
        task("A", 2),
        task("B", 1),
        task("C", 3)
    )

asyncio.run(main())
```

`gather()` 的语义需要记全，否则容易写出"以为失败了其实还在后台跑"的代码：

- 返回值是一个 **list**，顺序与传入顺序一致，**不是**完成顺序；
- 默认 `return_exceptions=False`：任一任务抛异常就立即向上抛，但**其他任务不会被取消**，它们继续在后台跑；
- `return_exceptions=True`：异常被当成结果放进列表，由调用方自己检查；
- `gather()` 自身被取消时，所有未完成的子任务**会**被一并取消。

最后一条是它和 `TaskGroup` 的分界线。

### 创建任务（Task）

```python
async def main():
    task1 = asyncio.create_task(task("Task1", 2))
    task2 = asyncio.create_task(task("Task2", 1))
    
    await task1
    await task2
```

`create_task()` 让协程立刻进入事件循环的排队序列，从而可以在"稍后 await"的间隙里先干别的事：

```python
import asyncio

async def load_config() -> dict:
    await asyncio.sleep(0.5)
    return {"timeout": 30}

async def warm_up_cache() -> None:
    await asyncio.sleep(0.5)

async def main() -> None:
    # 先启动两个任务，再一起等——总耗时约 0.5s 而不是 1.0s
    config_task = asyncio.create_task(load_config(), name="load-config")
    cache_task = asyncio.create_task(warm_up_cache(), name="warm-up-cache")

    config = await config_task
    await cache_task
    print(config)                     # {'timeout': 30}
    print(config_task.get_name())     # load-config（3.8+ 支持 name，排障时非常有用）

asyncio.run(main())
```

两个必须知道的陷阱：

1. **事件循环只持有 Task 的弱引用**。如果 `create_task()` 的返回值没有被任何变量或集合保存，任务可能在跑完前被垃圾回收，日志里出现 `Task was destroyed but it is pending!`。要"发射后不管"，就把任务存进集合并在结束时清理。
2. **`create_task` 抛出的异常不会自动冒泡**。没人 `await` 的任务失败时只有一句 `Task exception was never retrieved`，业务逻辑会静默丢失错误。

### 推荐替代：TaskGroup（3.11+）

`gather` 的问题是"兄弟任务不会跟着失败一起收手"。3.11 引入的 `TaskGroup` 实现了**结构化并发**：一组任务同生共死，任一失败则取消其余，全部异常打包成 `ExceptionGroup` 抛出。

```python
import asyncio

async def fetch(source: str, delay: float) -> str:
    await asyncio.sleep(delay)
    if source == "库存服务":
        raise RuntimeError("库存服务返回 503")
    return f"{source} 数据"

async def main() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch("订单服务", 0.3))
            tg.create_task(fetch("库存服务", 0.1))   # 0.1s 后失败
            tg.create_task(fetch("用户服务", 5.0))   # 会被连带取消，不必干等 5 秒
    except* RuntimeError as group:
        print(f"捕获 {len(group.exceptions)} 个错误：{group.exceptions[0]}")

asyncio.run(main())
```

`except*` 是处理 `ExceptionGroup` 的语法（3.11+），普通 `except RuntimeError` 捕获不到被包裹的异常，这点在迁移 `gather` 代码时最容易漏。

| 对比项 | `asyncio.gather` | `asyncio.TaskGroup` |
|--------|------------------|---------------------|
| 引入版本 | 3.4 | 3.11 |
| 一个任务失败 | 其余**继续运行** | 其余**被取消** |
| 异常形式 | 直接抛出第一个异常 | `ExceptionGroup` / `BaseExceptionGroup` |
| 返回值 | 结果列表（等长、有序） | 无，需自己从任务对象或闭包取值 |
| 适合场景 | 失败也要拿齐所有结果（批量采集） | 一组操作必须全部成功（事务性流程） |

---

## 5. 核心 API

最常用的四个：

| API                            | 作用                   | 使用场景                |
| ------------------------------ | -------------------- | ------------------- |
| `asyncio.create_task(coro)`    | 创建协程任务，立即加入事件循环      | 并发执行多个协程            |
| `asyncio.gather(*coros)`       | 等待多个协程完成，按顺序返回结果     | 批量执行协程并收集结果         |
| `asyncio.wait(coros, timeout)` | 等待协程完成，返回（已完成，未完成）元组 | 灵活处理部分完成的任务、超时控制    |
| `loop.run_in_executor()`       | 将阻塞性代码放到线程池/进程池执行    | 协程中处理非异步代码，避免阻塞事件循环 |

补充说明：上表中的 `wait()` 从 **3.11 起禁止直接传协程**，必须先 `create_task` 再传；`wait_for()` 从 **3.11 起抛内置 `TimeoutError`**（不再是 `asyncio.TimeoutError`，两者现在是同一个类）。

按用途整理的完整速查：

| 用途 | API | 版本 | 备注 |
|------|-----|------|------|
| 程序入口 | `asyncio.run(main())` | 3.7 | 一次进程只调一次 |
| 起一个任务 | `asyncio.create_task(coro, name=...)` | 3.7 | 必须保存引用 |
| 一组任务 | `asyncio.TaskGroup()` | 3.11 | 失败即取消兄弟任务 |
| 收集结果 | `asyncio.gather(*aws, return_exceptions=False)` | 3.4 | 结果有序，失败不取消兄弟 |
| 谁先完成 | `asyncio.as_completed(aws)` | 3.4 | 按完成顺序迭代，适合抢答式请求 |
| 挑一个成功 | `asyncio.wait(aws, return_when=FIRST_COMPLETED)` | 3.4 | 只接受 Task/Future |
| 超时 | `asyncio.timeout(delay)` | 3.11 | 上下文管理器写法，推荐 |
| 超时（旧式） | `await asyncio.wait_for(coro, timeout)` | 3.4 | 3.12 起内部改为基于 `timeout()` |
| 跑同步函数 | `await asyncio.to_thread(fn, *args)` | 3.9 | 首选，自动传递 contextvars |
| 跑同步函数（池） | `loop.run_in_executor(pool, fn, *args)` | 3.4 | 需要进程池或自定义池时用 |
| 防取消 | `await asyncio.shield(task)` | 3.4 | "别取消我，但我可以不等人" |
| 限流 | `asyncio.Semaphore(n)` | 3.4 | 控制同时在飞的请求数 |
| 互斥 | `asyncio.Lock()` | 3.4 | 保护跨 `await` 的共享状态 |
| 任务间传数据 | `asyncio.Queue(maxsize=n)` | 3.4 | 有界队列天然自带背压 |

---

## 6. 取消与超时

这是异步编程里被示例代码跳过、但生产代码必须处理的部分。

### 取消是"请求"，不是"杀死"

`task.cancel()` 不会立刻终止任何东西，它只是**在下一次 `await` 处注入一个 `asyncio.CancelledError`**。这意味着：

- 从 `cancel()` 到任务真正结束之间有窗口期，资源还在被持有；
- `CancelledError` 自 3.8 起直接继承 `BaseException`（不是 `Exception`），所以裸的 `except Exception` 不会误吞它——但 `except BaseException` 会；
- **捕获了就必须重新抛出**，否则 `TaskGroup`、`asyncio.timeout()` 这些依赖取消的机制会误判任务已正常结束。

```python
import asyncio

async def long_job() -> None:
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("收到取消请求，清理临时文件")
        raise                       # 必须向上抛，让调度层知道取消生效了
    finally:
        print("无论成功、失败还是取消，finally 都会执行")

async def main() -> None:
    pending = asyncio.create_task(long_job(), name="long-job")
    await asyncio.sleep(0.1)
    pending.cancel()
    try:
        await pending               # 等它真正收尾；不 await 会留下 pending 警告
    except asyncio.CancelledError:
        print(f"{pending.get_name()} 已取消：{pending.cancelled()}")

asyncio.run(main())
```

需要"吞掉取消但保留取消状态"的极少数场景（例如必须记完审计日志），用 `task.uncancel()` 配合 `task.cancelling()` 显式声明，不要靠 `pass` 蒙混过去。

### 超时：优先用 asyncio.timeout

```python
import asyncio

async def slow_query() -> str:
    await asyncio.sleep(5)
    return "结果"

async def main() -> None:
    try:
        # 3.11+ 推荐写法：超时即取消当前协程，无需额外包一层 Task
        async with asyncio.timeout(1.0):
            result = await slow_query()
    except TimeoutError:            # 3.11 起即内置超时异常
        print("查询超时")

asyncio.run(main())
```

| 写法 | 版本 | 特点 |
|------|------|------|
| `await asyncio.wait_for(coro, 1.0)` | 3.4 | 简单场景够用；3.12 起内部实现改为 `timeout()` |
| `async with asyncio.timeout(1.0):` | 3.11 | 可覆盖多条语句共享一个总预算，推荐 |
| `async with asyncio.timeout_at(deadline):` | 3.11 | 按绝对时间点截止，适合请求级 deadline 传递 |
| `timeout.reschedule()` | 3.11 | 运行中动态延长/缩短预算 |

注意 `asyncio.timeout()` 的 `TimeoutError` **只能在 `async with` 块外面捕获**，块内捕获不到。

---

## 7. 并发控制与同步原语

### 为什么要限流

协程切换几乎零成本，于是"能开多少开多少"的写法很容易把对方打挂：一次 `gather` 一万个请求，换来的是 DNS 超时、连接被拒、内存飙升。正确做法是用信号量把并发数压到合理水位。

```python
import asyncio
from asyncio import Semaphore

async def limited_task(semaphore, task_id):
    async with semaphore:
        print(f"Task {task_id} started")
        await asyncio.sleep(1)
        print(f"Task {task_id} completed")

async def main():
    semaphore = Semaphore(3)  # 最多同时运行3个任务
    tasks = [limited_task(semaphore, i) for i in range(10)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

### 协程也需要锁

单线程不代表没有竞态。只要"读—改—写"之间存在 `await`，其他协程就能插进来：

```python
import asyncio

class Counter:
    def __init__(self) -> None:
        self.value = 0
        self._lock = asyncio.Lock()

    async def increase(self) -> None:
        async with self._lock:          # 去掉这行，最终结果会小于 1000
            current = self.value
            await asyncio.sleep(0)      # 这里的 await 就是竞态窗口
            self.value = current + 1

async def main() -> None:
    counter = Counter()
    await asyncio.gather(*(counter.increase() for _ in range(1000)))
    print(counter.value)                # 加锁后稳定输出 1000

asyncio.run(main())
```

### 用队列解耦生产者与消费者

`asyncio.Queue` 是协程间传数据的标准做法，`maxsize` 一旦设上，就会在队列满时自动阻塞生产者——这就是背压（backpressure），比手工计数可靠。

```python
import asyncio

async def producer(queue: asyncio.Queue) -> None:
    for order_id in range(3):
        await queue.put(f"订单-{order_id}")
    await queue.put(None)               # 哨兵值：通知消费者收工

async def consumer(queue: asyncio.Queue) -> None:
    while (item := await queue.get()) is not None:
        print(f"处理 {item}")
        queue.task_done()

async def main() -> None:
    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=10)
    await asyncio.gather(producer(queue), consumer(queue))

asyncio.run(main())
```

其余原语速查：`asyncio.Event`（一次性广播通知）、`asyncio.Condition`（条件等待）、`asyncio.Barrier`（3.11+，多任务对齐起点）。

---

## 8. 高级用法

### 异步上下文管理器

```python
class AsyncResource:
    async def __aenter__(self):
        print("Acquiring resource")
        await asyncio.sleep(0.5)
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        print("Releasing resource")
        await asyncio.sleep(0.5)

async def use_resource():
    async with AsyncResource() as resource:
        print("Using resource")
        await asyncio.sleep(1)
```

手写 `__aenter__`/`__aexit__` 只适合需要精细控制的场景。日常更推荐 `contextlib.asynccontextmanager`，写法与同步的 `@contextmanager` 一致：

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_transaction(name: str):
    print(f"[{name}] BEGIN")
    try:
        yield f"{name}-connection"
        print(f"[{name}] COMMIT")
    except Exception:
        print(f"[{name}] ROLLBACK")
        raise

async def main() -> None:
    async with db_transaction("orders") as conn:
        print(f"使用 {conn}")

asyncio.run(main())
```

注意 `__aexit__` 返回 `True` 会**吞掉异常**；写资源清理代码时应当返回 `None`（默认），让异常正常传播。

### 异步迭代器

```python
class AsyncCounter:
    def __init__(self, stop):
        self.current = 0
        self.stop = stop
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.current < self.stop:
            await asyncio.sleep(0.5)
            self.current += 1
            return self.current
        else:
            raise StopAsyncIteration

async def main():
    async for i in AsyncCounter(5):
        print(i)
```

协议要点：`__aiter__` 返回迭代器本身（同步方法），`__anext__` 是协程，迭代结束时抛 `StopAsyncIteration`——对应同步迭代的 `StopIteration`，混用会得到 `TypeError`。

### 异步生成器

```python
async def async_generator(n):
    for i in range(n):
        await asyncio.sleep(0.5)
        yield i

async def main():
    async for item in async_generator(5):
        print(item)
```

异步生成器最大的坑是**提前 `break` 时清理逻辑不一定执行**：生成器被垃圾回收时才关闭，`finally` 可能延迟到很晚或根本轮不到。要确定性清理就用 `contextlib.aclosing`（3.10+），或 `AsyncExitStack`：

```python
import asyncio
from contextlib import aclosing

async def stream_rows(n: int):
    try:
        for i in range(n):
            yield i
    finally:
        print("释放数据库游标")        # 提前 break 也会执行

async def main() -> None:
    async with aclosing(stream_rows(100)) as rows:
        async for row in rows:
            if row == 2:
                break

asyncio.run(main())
```

---

## 9. 把同步代码接进异步世界

现实中的库不会全是异步的。选哪种包装方式，取决于被包装的函数是 **I/O 密集**还是 **CPU 密集**：

| 场景 | 方案 | 版本 | 说明 |
|------|------|------|------|
| 阻塞式 I/O（`requests`、`os` 文件读） | `await asyncio.to_thread(fn, ...)` | 3.9 | 一行搞定，自动传递 `contextvars` |
| 同上，但要自定义/复用线程池 | `loop.run_in_executor(pool, fn, ...)` | 3.4 | 需要限制线程数或共享池时用 |
| CPU 密集 | `ProcessPoolExecutor` + `run_in_executor` | 3.4 | 绕过 GIL，唯一能真正并行的方式 |
| 有异步版本 | 直接用异步库（`httpx`、`asyncpg`、`aiofiles`） | —— | 永远优先，不要包同步库 |

当需要在协程中调用同步 API 时，使用 `run_in_executor`：

```python
import asyncio
import time

def sync_task(seconds):
    time.sleep(seconds)
    return f"Slept for {seconds} seconds"

async def main():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, sync_task, 2)
    print(result)

asyncio.run(main())
```

同样的需求用 `to_thread` 更简洁（少一层 loop 获取，且参数传递更自然）：

```python
import asyncio
import time

def blocking_io(seconds: float) -> str:
    time.sleep(seconds)                 # 同步阻塞调用，不能直接放进协程
    return f"阻塞 {seconds}s 完成"

async def main() -> None:
    result = await asyncio.to_thread(blocking_io, 1.0)
    print(result)

asyncio.run(main())
```

CPU 密集任务换成进程池，否则线程池会被 GIL 卡住，等于什么都没做：

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

def count_primes(limit: int) -> int:
    return sum(all(n % d for d in range(2, int(n ** 0.5) + 1)) for n in range(2, limit))

async def main() -> None:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        count = await loop.run_in_executor(pool, count_primes, 200_000)
    print(f"素数个数 {count}")

# 必须放在 __main__ 保护里：子进程会重新导入本模块，
# 否则顶层 asyncio.run() 会被再次执行，抛 BrokenProcessPool
if __name__ == "__main__":
    asyncio.run(main())
```

---

## 10. 实际应用

### 异步 HTTP 请求（aiohttp）

```python
import aiohttp
import asyncio

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def main():
    urls = ["https://example.com", "https://python.org"]
    results = await asyncio.gather(*(fetch(url) for url in urls))
    for url, content in zip(urls, results):
        print(f"{url}: {len(content)} bytes")

asyncio.run(main())
```

上面的写法在**批量抓取时是反模式**：`fetch()` 每次调用都新建一个 `ClientSession`，连接池、DNS 缓存、Cookie 全部丢弃，每次都要重新 TLS 握手。正确做法是让整个任务共享一个 session：

```python
import asyncio
import aiohttp

async def main() -> None:
    connector = aiohttp.TCPConnector(limit=20)          # 复用连接 + 限制连接数
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get("https://example.com") as response:
            print(response.status, len(await response.text()))

asyncio.run(main())
```

### 异步文件操作（aiofiles）

```python
import aiofiles
import asyncio

async def write_file(filename, content):
    async with aiofiles.open(filename, 'w') as f:
        await f.write(content)

async def read_file(filename):
    async with aiofiles.open(filename, 'r') as f:
        return await f.read()
```

补充一点事实：`aiofiles` 内部就是线程池包装，它让协程不被文件 I/O 阻塞，但**不会让磁盘变快**。SSD 上小文件读写用同步写法往往更简单；只有大文件或网络挂载存储才值得引入。

---

## 11. 常见误区与性能真相

| 误区 | 实际情况 | 纠正方式 |
|------|----------|----------|
| 异步一定比同步快 | 单任务上异步只会更慢（多了调度开销） | 只在"大量并发等待"时才有收益 |
| 单线程所以没有数据竞争 | `await` 之间任何协程都能插队 | 跨 `await` 的共享状态用 `asyncio.Lock` |
| `await coro` 就等于并发 | 内联执行，不产生第二个调度单元 | 要并发先 `create_task` 或交给 `gather`/`TaskGroup` |
| `create_task` 后不管也行 | 弱引用 + 异常不冒泡，任务可能消失或静默失败 | 保存引用并 `await`，或用 `TaskGroup` |
| 加个 `async` 就能加速 CPU 计算 | 单线程 + GIL，计算结果一样慢 | 换多进程，或把计算下沉到 C/Rust 扩展 |
| `except Exception` 能兜住所有错误 | `CancelledError` 继承 `BaseException`，捕不到 | 需要感知取消时显式写 `except asyncio.CancelledError` |
| 协程开得越多吞吐越高 | 对端连接数、文件描述符、内存都会先崩 | 用 `Semaphore` 限流，用有界 `Queue` 背压 |

### 关于 uvloop

`uvloop` 用 Cython + libuv 重写了事件循环，在真实网络 I/O 场景下能明显降低调度开销；它对纯 `asyncio.sleep` 的微基准帮助很小，因为热点不在事件循环上。

- 安装：`pip install uvloop`（要求 Python 3.9+）
- 启用（0.18+ 推荐）：`uvloop.run(main())`，它会用 uvloop 作为 `asyncio.run()` 的循环工厂
- 平台限制：基于 libuv 的 POSIX 实现，**不支持 Windows**；Windows 上继续用默认的 `ProactorEventLoop`

```python
import asyncio
import uvloop

async def main() -> None:
    await asyncio.sleep(0)

uvloop.run(main())          # 替代 asyncio.run(main())
```

---

## 12. 注意事项

1. **避免阻塞操作**：不要在协程中使用 `time.sleep()`，应使用 `asyncio.sleep()`
2. **事件循环**：每个线程只有一个事件循环
3. **错误处理**：使用 `try/except` 捕获协程中的异常
4. **性能**：异步编程适合 I/O 密集型任务，对 CPU 密集型任务效果有限
5. **兼容性**：Python 3.5+ 支持 async/await 语法

补充几条与版本演进相关的坑：

6. **别在已有循环里再开循环**：Jupyter、FastAPI、pytest-asyncio 里已经在跑事件循环，此时调用 `asyncio.run()` 会抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`，应改成 `await main()`。
7. **`asyncio.wait()` 不接受协程**（3.11+ 起强制）：先 `create_task` 再传，否则直接 `TypeError`。
8. **取循环用 `get_running_loop()`**：`get_event_loop()` 在 3.14+ 没有运行中循环时会抛 `RuntimeError`，事件循环 policy 体系也计划在 3.16 移除。
9. **`async with` 与 `async for` 不能出现在同步函数里**：语法层面就报 `SyntaxError`，不是运行时问题。

---

## 13. 最佳实践

1. 使用 `asyncio.run()` 作为主入口点
2. 优先使用 `asyncio.gather()` 并发执行任务
3. 使用 `async with` 管理异步资源
4. 使用信号量控制并发数（示例见[并发控制与同步原语](#7-并发控制与同步原语)）
5. 使用 `uvloop` 替代默认事件循环以获得更好性能

在第 2 条上补一个当代修正：**3.11+ 且"要么全成功要么全失败"的场景，`TaskGroup` 比 `gather` 更安全**——`gather` 在兄弟任务失败后不会取消其余任务，容易留下后台在跑的半成品任务。批量采集（允许部分失败）继续用 `gather` + `return_exceptions=True`。

其余值得固化的习惯：

- **给任务起名字**：`create_task(coro, name="fetch-orders")`，出问题时日志和 `python -m asyncio ps` 都能直接定位。
- **库代码不自建事件循环**：只暴露 `async def`，把 `run()` 的决定权交给调用方，否则嵌入到别人的异步程序里必然崩。
- **超时写在最外层**：请求级 deadline 用 `asyncio.timeout()` 包住整条链路，比在每个子调用上零散设超时更贴近真实需求。
- **同步接口用 `to_thread` 而不是自己 `ThreadPoolExecutor`**：后者容易漏掉关闭和异常传播。

---

## 14. 协程与线程的对比

| 特性 | 协程 | 线程 |
|------|------|------|
| 调度方式 | 用户态协作式调度 | 内核态抢占式调度 |
| 切换开销 | 极小（无上下文切换） | 较大（需要内核参与） |
| 内存占用 | 小（KB级别） | 大（MB级别） |
| 适用场景 | I/O 密集型 | I/O 密集型 + CPU 密集型 |
| 编程复杂度 | 需要异步思维 | 需要处理同步问题 |

再补两行常被忽略的差异，以及进程作为参照：

| 特性 | 协程 | 线程 | 进程 |
|------|------|------|------|
| 谁决定切换 | 代码里的 `await` | 操作系统时间片 | 操作系统 |
| 抢占风险 | 无（不 `await` 不让出） | 有（任意指令处可能被切） | 有 |
| 数据共享 | 直接共享内存 | 共享内存 + 需加锁 | 需序列化/IPC |
| 崩溃影响 | 异常可被捕获，循环存活 | 单线程崩溃影响进程 | 进程隔离，最安全 |
| 数量级上限 | 万级 | 千级 | 十级 |

一句话选择法：**等 I/O 用协程，堵在同步库用线程，算得动用进程。**

---

## 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `RuntimeWarning: coroutine 'foo' was never awaited` | 调用了 `async def` 函数但没 `await`，协程对象被丢弃 | 补 `await`，或显式 `create_task` 后保存引用 |
| `RuntimeError: asyncio.run() cannot be called from a running event loop` | 已有循环在跑（Jupyter / FastAPI / pytest-asyncio） | 改成 `await main()`，或 `nest_asyncio` 只作临时手段 |
| `TypeError: object dict can't be used in 'await' expression` | `await` 了非可等待对象，常见于漏写括号拿到函数本身 | 检查 `await` 右侧是否为协程/Task/Future |
| `TypeError: Passing coroutines is forbidden, use tasks explicitly` | `asyncio.wait()` 直接传了协程（3.11+） | 先 `create_task`，再传给 `wait()` |
| `Task was destroyed but it is pending!` | `create_task` 返回值没被引用，任务被 GC | 用变量或集合持有任务，退出前 `await` |
| `Task exception was never retrieved` | 任务抛异常但无人 `await` | 统一用 `TaskGroup`，或给任务加 `add_done_callback` |
| 程序整体卡住、日志不再输出 | 协程里调了 `time.sleep` / 同步 HTTP / 大循环，阻塞了事件循环 | 换 `asyncio.sleep`，同步调用用 `to_thread` 包起来 |
| `asyncio.exceptions.CancelledError` 冒泡到最外层 | 任务被取消且未在上层处理 | 在合适的边界 `except asyncio.CancelledError` 做清理后 `raise` |
| `TimeoutError` 捕获不到 | `asyncio.timeout()` 的异常在块内被吞，或用了 `except asyncio.TimeoutError` 但版本 < 3.11 | 在 `async with` 块外捕获 `TimeoutError` |
| `RuntimeError: no running event loop`（3.14+） | 在协程外用 `get_event_loop()` 取循环 | 用 `asyncio.run()`，协程内改用 `get_running_loop()` |

---

## See Also

- [[03-python-functional|Python 函数式编程]] —— 生成器与惰性求值，是理解协程的前置知识
- [[02-python-oop|Python 面向对象]] —— `__aenter__`/`__aiter__` 等异步协议属于魔术方法体系
- [[05-python-type-hints|Python 类型提示]] —— `Coroutine`、`Awaitable`、`AsyncIterator` 的类型标注写法
- [[14-context-managers|Python 上下文管理器与 contextlib]] —— `async with`、`aclosing`、
  `AsyncExitStack` 的完整机制，本文只讲了异步场景下的用法
- [[13-python-exceptions|Python 异常处理]] —— `ExceptionGroup`、`except*`、
  `CancelledError` 继承 `BaseException` 的来龙去脉
- [[15-python-concurrency|Python 并发与并行]] —— 阻塞库如何用线程池接进事件循环、三者选型边界
- [[07-python-advanced|Python 进阶话题]] —— 装饰器与语言机制的其他侧面
- [[pydantic-validation|Pydantic 数据类型校验]] —— 异步接口层的数据边界校验
- [[01-python-basics|Python 基础语法]] —— 语法基础回顾
- [[index|Python 笔记目录]]

## 参考

- [asyncio 协程与任务（官方文档）](https://docs.python.org/3/library/asyncio-task.html)
- [asyncio 事件循环（官方文档）](https://docs.python.org/3/library/asyncio-eventloop.html)
- [Python 3.14 更新说明](https://docs.python.org/3/whatsnew/3.14.html)
- [PEP 492 – Coroutines with async and await syntax](https://peps.python.org/pep-0492/)
- [PEP 3156 – Asynchronous IO Support Rebooted: the asyncio module](https://peps.python.org/pep-3156/)
- [uvloop 项目主页](https://github.com/MagicStack/uvloop)
