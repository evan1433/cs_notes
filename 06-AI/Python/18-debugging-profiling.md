---
title: Python 调试与性能分析
description: breakpoint 与 pdb 断点调试、事后调试、faulthandler 转储卡死栈、cProfile 与 pstats 解读、timeit 微基准、tracemalloc 内存分析、py-spy 线上排查
tags:
  - python
  - debugging
  - profiling
  - performance
date: 2026-11-06
aliases:
  - python-pdb
  - python-profiling
  - python-debugging
---

# Python 调试与性能分析

> **版本基线**：`breakpoint()` 3.7；pdb 的命令行改为 argparse 风格在 3.13
> （`-q` 等旧参数不再被接受）。示例在本机 CPython 3.13 实跑验证。

## 1. 先分清四类问题，再选工具

"程序有问题"这句话对应四种完全不同的排查手段，用错工具会浪费大量时间：

| 症状 | 本质 | 该用的工具 |
|------|------|-----------|
| 结果不对，但能跑完 | 逻辑错误 | `breakpoint()` + pdb |
| 抛异常退出 | 栈被破坏 | traceback、`python -m pdb -c continue`、`pytest --pdb` |
| 卡住不动 / 段错误 | 死锁、死循环、C 扩展崩溃 | `faulthandler`、`py-spy dump` |
| 能跑完但太慢 | 热点在别处 | `cProfile`、`timeit`、`py-spy top` |
| 内存持续增长 | 泄漏或大对象滞留 | `tracemalloc` |

一条前置原则：**先能复现，再谈分析**。线上问题无法复现时，唯一可靠的手段是
在出问题前就把可观测性埋好（结构化日志 + `faulthandler` + 定期 `py-spy` 采样）。

## 2. print 够用吗

小脚本里 `print` 是最快的诊断工具。但当问题出现在"偶发、线上、多线程"场景时，
它会同时暴露四个缺陷：

| 缺陷 | 后果 |
|------|------|
| 没有级别 | 无法在生产关掉调试输出 |
| 没有时间戳与来源 | 无法判断顺序，也无法定位是哪个模块打的 |
| 写到 stdout | 与正常输出混在一起，无法单独采集 |
| 无法聚合 | 只能人眼看，不能做告警与统计 |

logging 的最小可用配置：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

logger.info("加载订单 order_id=%s items=%d", order_id, len(items))
```

注意用 **`%s` 占位而不是 f-string**：日志级别被过滤时，f-string 仍然会先把字符串拼出来，
白白付出格式化开销；占位符形式则不会。

`logger.exception("...")` 只能在 `except` 块里用，它会自动附带 traceback——
这是"记了日志但没有栈"这类问题的标准修法。

## 3. breakpoint() 与 pdb

### 3.1 用 breakpoint() 而不是 pdb.set_trace()

```python
def settle(order):
    total = order["amount"] * order["qty"]
    breakpoint()          # 执行到这里会暂停，进入 pdb
    return total
```

`breakpoint()`（3.7+）是 `pdb.set_trace()` 的受控版本，它读 `PYTHONBREAKPOINT` 环境变量：

| 环境变量 | 行为 |
|----------|------|
| 未设置 | 进入 pdb |
| `PYTHONBREAKPOINT=0` | **完全跳过**，相当于断点不存在 |
| `PYTHONBREAKPOINT=ipdb.set_trace` | 换成 ipdb |
| `PYTHONBREAKPOINT=pudb.set_trace` | 换成 pudb（终端图形界面） |

实测 `PYTHONBREAKPOINT=0` 的效果：

```console
$ PYTHONBREAKPOINT=0 python3 -c "breakpoint(); print('跳过了 pdb')"
跳过了 pdb
```

这条机制的价值：**断点可以留在代码里提交**。CI 与生产环境设 `PYTHONBREAKPOINT=0`
就不会卡住，本地开发时又能直接命中。

### 3.2 pdb 常用命令

| 命令 | 缩写 | 作用 |
|------|------|------|
| `next` | `n` | 执行下一行（不进入函数） |
| `step` | `s` | 进入被调用函数 |
| `continue` | `c` | 继续运行到下一个断点 |
| `return` | `r` | 运行到当前函数返回 |
| `until` | `unt` | 运行到当前行号之后（跳出循环常用） |
| `list` | `l` | 显示当前位置附近的源码 |
| `longlist` | `ll` | 显示整个函数源码 |
| `print` | `p` | 求值并打印表达式 |
| `pp` | `pp` | 美化打印（看 dict / 嵌套结构） |
| `where` | `w` | 打印调用栈（含每个帧的当前行） |
| `up` / `down` | `u` / `d` | 在调用栈里上下移动帧 |
| `break` | `b` | 设断点（`b file.py:42`、`b func`、条件断点 `b 42, x>10`） |
| `condition` | — | 给已有断点加条件 |
| `!` | — | 执行任意语句（`!order["qty"] = 1`） |
| `interact` | — | 进入交互式解释器，保留当前命名空间 |
| `quit` | `q` | 退出调试 |

最实用的三个组合：

- `w` + `u`/`d`：定位"我是从哪条路径进来的"；
- `b 42, x > 10`：只在特定数据下停住，避免手动 `c` 无数次；
- `!变量 = 新值`：不重启进程就能试"如果这个值是 0 会怎样"。

### 3.3 事后调试：异常发生后回看现场

程序已经崩了，最想知道的是"崩溃时局部变量是什么"。三种进入方式：

**方式一：命令行启动**

```console
$ python3 -m pdb -c continue post_mortem.py
Traceback (most recent call last):
  ...
ZeroDivisionError: division by zero
Uncaught exception. Entering post mortem debugging
Running 'cont' or 'step' will restart the program
> /private/tmp/b3/post_mortem.py(3)average()
-> return total / len(rows)
(Pdb) p rows
[]
```

注意 `-c continue` 不可省略：**直接 `python -m pdb script.py` 会停在第一行**，
而不是停在异常处。另外 3.13 起 pdb 的命令行参数改用 argparse，旧教程里的 `-q` 会直接报
`unrecognized arguments: -q`。

**方式二：pytest 里**

```console
$ pytest --pdb            # 用例失败时直接进入 pdb
$ pytest --trace          # 每个用例一开始就停住
```

**方式三：代码里捕获后主动进入**

```python
import pdb
import sys

try:
    run()
except Exception:
    pdb.post_mortem(sys.exc_info()[2])   # 传入 traceback 对象
```

方式三适合"批处理里某一条数据出错，想就地看看这条数据长什么样"的场景。

### 3.4 pdb 的能力边界

pdb 是纯终端工具，看复杂数据结构很吃力。日常开发中更高效的选择：

| 工具 | 优势 | 代价 |
|------|------|------|
| `ipdb` | 语法高亮、tab 补全、`pp` 更友好 | 需额外安装 |
| `pudb` | 终端里的图形界面，可看源码与变量面板 | 需额外安装 |
| IDE 断点（VS Code / PyCharm） | 图形化、条件断点、变量树 | 需要图形环境 |
| `breakpoint()` + `PYTHONBREAKPOINT` | 零依赖、可提交、可远程关掉 | 仅终端 |

## 4. faulthandler：卡死与段错误

pdb 只能用在"程序还活着、还能响应输入"的场景。**死锁、死循环、C 扩展段错误**
时进程不再执行 Python 字节码，任何 Python 层的调试器都进不去。

`faulthandler` 由解释器在 C 层实现，即使 GIL 被持有也能打印栈：

```python
import faulthandler
import time

faulthandler.dump_traceback_later(0.5, exit=True)   # 0.5 秒后转储并退出
print("开始卡住", flush=True)
time.sleep(10)
```

实测输出：

```text
开始卡住
Timeout (0:00:00.500000)!
Thread 0x00000001f1a2d300 (most recent call first):
  File "/private/tmp/b3/hang.py", line 6 in <module>
```

即使卡在 C 扩展里，这段栈也能指出"最后执行的 Python 帧"。
另外两个用法：

- 环境变量 `PYTHONFAULTHANDLER=1`：进程崩溃（SIGSEGV）时自动转储，无需改代码；
- `python -X faulthandler`：同上，适合临时排查。

> 生产环境的常规做法：启动时设 `PYTHONFAULTHANDLER=1`，并在看门狗里调用
> `dump_traceback_later(超时, exit=True)`。这样"卡死"会变成"带栈的崩溃"，可被监控捕获。

## 5. cProfile：先定位，再优化

### 5.1 两种运行方式

代码内精确控制范围：

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
main()
profiler.disable()
pstats.Stats(profiler).sort_stats("cumtime").print_stats(8)
```

命令行方式不需要改代码：

```console
$ python3 -m cProfile -s tottime prof_cmd.py
$ python3 -m cProfile -o prof.out prof_cmd.py     # 先存盘
$ python3 -c "import pstats; pstats.Stats('prof.out').sort_stats('cumulative').print_stats()"
```

`-o` 存盘再分析的价值：**同一次运行可以用不同维度反复看**，不必重跑（重跑可能复现不了）。

### 5.2 五个列怎么读

实测输出（`time.sleep(0.05)` 加一点列表计算）：

```text
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.052    0.052    0.052    0.052 {built-in method time.sleep}
        1    0.002    0.002    0.002    0.002 prof_cmd.py:4(load_orders)
        3    0.001    0.000    0.001    0.001 prof_cmd.py:8(summarize)
        1    0.001    0.001    0.056    0.056 prof_cmd.py:1(<module>)
```

| 列 | 含义 | 怎么用 |
|----|------|--------|
| `ncalls` | 调用次数 | 次数异常多说明循环里在反复建对象 |
| `tottime` | **本函数自身**耗时（不含子调用） | 找真正的热点 |
| `percall`（第一个） | `tottime / ncalls` | 单次成本 |
| `cumtime` | 含子调用的累计耗时 | 找"哪个入口最贵" |
| `percall`（第二个） | `cumtime / ncalls` | 平均路径成本 |

关键区别：**优化要看 `tottime`，定位入口要看 `cumtime`**。`<module>` 的 `cumtime` 永远最大
（它包含一切），只看它没有意义。

上表还有一个重要信号：`time.sleep` 的 `tottime` 高达 0.052s，但它**不消耗 CPU**。
cProfile 统计的是"函数耗时"，不区分"在算"还是"在等"。所以：

- 如果热点是 `sleep`、`recv`、`read`，问题在 I/O 而不在计算，优化算法没用；
- 真正的 CPU 热点要看"非 I/O 函数的 tottime 排名"。

### 5.3 排序与过滤

```python
stats = pstats.Stats("prof.out")
stats.sort_stats("cumulative").print_stats("order_service", 10)  # 只看本项目的函数
stats.print_callers("summarize")     # 谁调用了它
stats.print_callees("main")          # 它调用了谁
```

`print_callers` / `print_callees` 是 cProfile 最被低估的功能：前者回答"这个热点被谁拖进来的"，
后者回答"这个慢函数的时间花在哪个子调用上"。

### 5.4 cProfile 的失真

cProfile 会为每次函数调用插桩，因此：

- **调用次数极多的小函数被严重放大**（每次调用都有固定开销）；
- 内联的 C 代码、生成器表达式、推导式可能不显示为独立条目；
- 用它测"某个表达式快不快"会得到错误的结论——那类问题要用 `timeit`。

## 6. timeit：微基准

只关心"这两行代码哪个快"时用 `timeit`，它会自动多次运行、取最优、并关闭 GC 干扰：

```console
$ python3 -m timeit -s "data = list(range(1000))" "sum(data)"
200000 loops, best of 5: 2 usec per loop
```

| 参数 | 作用 |
|------|------|
| `-s "setup"` | 只执行一次的准备工作（导入、造数据） |
| `-n 10000` | 指定循环次数 |
| `-r 5` | 重复 5 轮，取最好成绩 |
| `-p 3` | 输出到 3 位小数的排名 |

代码内写法（需要对比多组时更方便）：

```python
import timeit

setup = "data = {'order_id': 1001}"
try_stmt = """
try:
    v = data['order_id']
except KeyError:
    v = None
"""
if_stmt = "v = data['order_id'] if 'order_id' in data else None"

n = 1_000_000
t_try = min(timeit.repeat(try_stmt, setup, number=n, repeat=5))
t_if = min(timeit.repeat(if_stmt, setup, number=n, repeat=5))
print(f"try {t_try/n*1e9:.1f} ns vs if {t_if/n*1e9:.1f} ns")
```

三个陷阱：

- **setup 里的代码不要放进 stmt**，否则测的是"建数据 + 用数据"；
- **必须取多次的最小值**，平均值会被系统调度噪声拉高；
- **微基准结论不能外推**。在 CPython 3.13 上 `try/except` 的无异常路径比 `if` 预判还快
  （零成本异常），但这个结论依赖版本与实现细节，不能当作通用规则。

## 7. tracemalloc：内存去哪了

`sys.getsizeof()` 只算对象自身（浅大小），看不到它引用的子对象。`tracemalloc` 能按
**分配位置**统计真实占用：

```python
import tracemalloc

tracemalloc.start()
data = build_orders(50_000)
current, peak = tracemalloc.get_traced_memory()
print(f"当前 {current/1024:.0f}KB，峰值 {peak/1024:.0f}KB")
tracemalloc.stop()
```

按行聚合，直接指出是哪一行在吃内存：

```python
tracemalloc.start(25)              # 保留 25 帧回溯
data = build_dicts(50_000)
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics("lineno")[:3]:
    print(stat)
tracemalloc.stop()
```

```text
/private/tmp/b3/mem_demo.py:13: size=11.8 MiB, count=199484, average=62 B
```

实测对比（5 万个对象，同一份数据用 `dict` 与 `__slots__` 类两种表示）：

| 表示方式 | 当前内存 | 相对开销 |
|----------|----------|----------|
| `dict` | 12131 KB | 1.00x |
| `__slots__` 类 | 5502 KB | **0.45x** |

这组数据解释了 [[02-python-oop|Python 面向对象]] 里"`__slots__` 只在实例数远大于类数时值得"
的判断：5 万个对象省下 6.6MB，量级足够改变一个数据管道的可行性。

两种快照对比用法：

```python
snap_before = tracemalloc.take_snapshot()
run_workload()
snap_after = tracemalloc.take_snapshot()
for stat in snap_after.compare_to(snap_before, "lineno")[:5]:
    print(stat)                    # 只列出"增长了"的部分
```

`compare_to` 是排查"循环里每轮都泄漏一点"的标准手法。

## 8. 线上排查：py-spy

线上进程不能重启、不能加断点，`py-spy` 通过读取进程内存采样，**不需要修改代码、
不需要重启、开销低于 1%**：

```console
$ py-spy dump --pid 12345          # 打印当前所有线程的栈（查卡死）
$ py-spy top --pid 12345           # 类似 top 的实时视图
$ py-spy record -o profile.svg --pid 12345 --duration 30   # 生成火焰图
```

`dump` 是排查"服务无响应"的首选：一次输出就能看出是卡在锁、卡在网络读，
还是卡在某个正则的回溯里。容器环境需要给容器加 `SYS_PTRACE` 能力，
否则会报 `Permission denied`。

## 9. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| 用 `print` 定位线上问题 | 无级别、无时间戳、无法关闭 | 改用 logging，关键路径用 `logger.exception` |
| 日志用 f-string 拼接 | 级别被过滤时仍付出格式化开销 | 用 `logger.info("%s", x)` 占位符 |
| 把 `pdb.set_trace()` 提交进仓库 | 生产环境会直接卡死 | 用 `breakpoint()` + `PYTHONBREAKPOINT=0` |
| 以为 `python -m pdb x.py` 会停在异常处 | 它会停在第一行 | 加 `-c continue` |
| 用 pdb 排查卡死 | 进程不执行字节码，pdb 进不去 | 用 `faulthandler` 或 `py-spy dump` |
| 只看 cProfile 的 `cumtime` 排名 | `<module>` 永远第一，没有指导意义 | 看 `tottime` 找热点，`cumtime` 只用于定位入口 |
| 把 `sleep`/`recv` 当 CPU 热点优化 | 它们不消耗 CPU，是等待 | 先判断 I/O 还是计算 |
| 用 cProfile 测单行表达式 | 插桩开销会淹没真实差异 | 用 `timeit` |
| `timeit` 只跑一次取平均 | 系统噪声导致结果不可比 | `repeat` 多次取最小值 |
| 用 `sys.getsizeof` 判断内存占用 | 只算浅大小，看不到子对象 | 用 `tracemalloc` |
| 优化凭直觉 | 真实热点常在意外的地方 | 先 profile，再改代码，改完再 profile |

## 10. 与相关概念的关系

- **与 [[13-python-exceptions|Python 异常处理]]**：`logger.exception` 与
  `pdb.post_mortem` 都依赖 traceback 对象；`__cause__` / `__context__` 的区分
  直接决定事后调试时能不能找到根因。
- **与 [[17-pytest|pytest 测试]]**：`--pdb` 与 `--trace` 把断点接进测试流程；
  `--durations=10` 能直接列出最慢的用例，比 profile 更快定位。
- **与 [[15-python-concurrency|Python 并发与并行]]**：多线程卡死先用 `faulthandler`
  看所有线程栈；`py-spy dump` 会按线程分组输出，能直接看出锁的持有关系。
- **与 [[02-python-oop|Python 面向对象]]**：`__slots__` 的内存收益需要用 `tracemalloc`
  实测，`sys.getsizeof` 会得出错误结论。

## 参考

- [pdb — The Python Debugger](https://docs.python.org/3/library/pdb.html)
- [faulthandler — Dump the Python traceback](https://docs.python.org/3/library/faulthandler.html)
- [cProfile and profile — Python profilers](https://docs.python.org/3/library/profile.html)
- [timeit — Measure execution time of small code snippets](https://docs.python.org/3/library/timeit.html)
- [tracemalloc — Trace memory allocations](https://docs.python.org/3/library/tracemalloc.html)
- [py-spy](https://github.com/benfred/py-spy)
- [[logging-module-guide|logging 模块使用指南]]
