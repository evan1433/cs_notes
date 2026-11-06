---
title: Python 上下文管理器与 contextlib
description: with 协议的精确语义、__exit__ 抑制规则、contextmanager 生成器写法、ExitStack 动态资源管理、异步上下文管理器与 aclosing
tags:
  - python
  - context-manager
  - contextlib
  - resource-management
date: 2026-11-06
aliases:
  - python-with-statement
  - python-contextlib
---

# Python 上下文管理器与 contextlib

> **版本基线**：`asynccontextmanager` 3.7、`nullcontext` 3.7、`aclosing` 3.10、`chdir` 3.11；
> `suppress` 自 3.12 起支持 `BaseExceptionGroup`。示例在本机 CPython 3.13 实跑验证。

## 1. with 解决的不是"省几行代码"

拿最熟悉的文件读写对比。用 `try/finally` 也能保证关闭，为什么还要 `with`？

```python
# try/finally：正确，但有三处容易写错
f = open("orders.csv", encoding="utf-8")
try:
    for line in f:
        process(line)
finally:
    f.close()

# with：关闭时机由协议保证，且不占用一个变量名
with open("orders.csv", encoding="utf-8") as f:
    for line in f:
        process(line)
```

三处容易写错的地方：忘记 `finally`、`open` 本身失败时对 `f` 调 `close()` 触发 `NameError`、
清理动作写在了 `except` 分支里导致正常路径不执行。`with` 把这些全部收进协议。

更重要的差别在**表达力**：`with` 能描述"进入"和"退出"两个阶段，因此能承载
锁的获取与释放、事务的开始与提交/回滚、临时切换全局状态并恢复——
这些都不是"关闭一个句柄"能概括的。`try/finally` 只能表达后者。

有一处 `with` 反而更弱：**它不能直接拿到"异常是否被处理"的结果做分支**，
需要靠 `__exit__` 的返回值表达（见 2.3）。因此"失败要重试"这类逻辑仍应写成 `try/except`。

## 2. with 协议：__enter__ 与 __exit__

### 2.1 精确的进出顺序

`with` 语句的语义可以完全由两个方法定义：

```python
class Trace:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        log.append(f"enter {self.name}")
        return self.name              # 绑定到 as 后面的变量

    def __exit__(self, exc_type, exc, tb):
        log.append(f"exit {self.name}")
        return None                   # 假值：不抑制异常


log = []
with Trace("A") as a, Trace("B") as b:
    log.append(f"body {a}{b}")

print(log)
# ['enter A', 'enter B', 'body AB', 'exit B', 'exit A']
```

四个要点：

| 规则 | 说明 |
|------|------|
| 进入按从左到右 | `A` 先于 `B` |
| 退出按从右到左 | 后进入的先清理，保证依赖关系（B 可能依赖 A 的资源） |
| `as` 绑定的是 `__enter__` 的返回值 | 不是上下文管理器对象本身。`with open(...) as f` 拿到的是文件对象 |
| `return` / `break` / 异常都会触发 `__exit__` | 它挂在"离开 with 块"这个动作上，而非正常结束 |

最后一条实测：

```python
log = []

def f():
    with Trace("R"):
        log.append("before return")
        return "returned"

print(f(), log)
# returned ['enter R', 'before return', 'exit R']
```

`__exit__` 在 `return` 真正返回之前执行，所以清理一定能完成。

### 2.2 __enter__ 抛异常时，__exit__ 不会被调用

这是实现"获取资源"型上下文管理器时最容易忽略的点：

```python
class FailsOnEnter:
    def __enter__(self):
        log.append("enter")
        raise RuntimeError("连接失败")

    def __exit__(self, *exc):
        log.append("exit")

log = []
try:
    with FailsOnEnter():
        pass
except RuntimeError as e:
    print(e, log)      # 连接失败 ['enter']
```

因为"进入"没有完成，协议认为你从未持有资源，自然不该清理。
**推论**：`__enter__` 里如果分多步获取资源（先连库再建游标），
前半段成功、后半段失败时，前半段必须自己回滚——`__exit__` 帮不了你。
标准做法是把 `__enter__` 写成"要么全成功，要么全部释放"的原子操作。

### 2.3 __exit__ 的返回值决定是否抑制异常

`__exit__(exc_type, exc, tb)` 的三个参数在无异常时全是 `None`。返回值按真值判断：

```python
class Swallow:
    def __enter__(self):
        return "resource"

    def __exit__(self, exc_type, exc, tb):
        print("收到", exc_type.__name__ if exc_type else None)
        return True                 # 真值：异常被吞掉

class Propagate:
    def __enter__(self):
        return "resource"

    def __exit__(self, exc_type, exc, tb):
        return None                 # 假值：继续传播

with Swallow():
    raise ValueError("被吞掉")
print("Swallow 之后仍能执行")        # 会执行

try:
    with Propagate():
        raise ValueError("继续传播")
except ValueError as e:
    print("外层接住:", e)
```

| `__exit__` 返回 | 异常是否传播 | 后续代码 |
|-----------------|--------------|----------|
| `None` / `False` / `0` | 传播 | 不执行 with 之后的语句 |
| `True` / 非空对象 | 被抑制 | 从 with 之后继续执行 |
| 抛出新异常 | 新异常传播 | 原异常进 `__context__` |

**`__exit__` 里抛新异常会覆盖原异常**，这一点在清理动作可能失败时尤其危险：

```python
class BadExit:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        raise RuntimeError("清理失败")

try:
    with BadExit():
        raise ValueError("业务异常")
except RuntimeError as e:
    print(type(e).__name__, e, type(e.__context__).__name__)
# RuntimeError 清理失败 ValueError
```

外层看到的是 `RuntimeError`，真正的业务异常退居 `__context__`。
如果清理动作可能失败，必须自己在 `__exit__` 里兜住（见 [[13-python-exceptions|Python 异常处理]] 3.2）。

## 3. @contextmanager：用生成器写上下文管理器

写一个类需要 `__init__`、`__enter__`、`__exit__` 三个方法，多数场景用不上这么重。
`@contextmanager` 用"一个生成器"表达同样的语义：**`yield` 之前是进入，之后是退出**。

### 3.1 三行模板

```python
from contextlib import contextmanager

@contextmanager
def tx(name):
    print(f"[{name}] BEGIN")          # __enter__ 阶段
    try:
        yield name                     # as 拿到这里 yield 的值
        print(f"[{name}] COMMIT")      # 正常路径收尾
    except Exception as exc:
        print(f"[{name}] ROLLBACK: {exc}")
        raise                          # 不 raise 就等于吞掉异常
    finally:
        print(f"[{name}] 释放连接")     # 无论成败都执行
```

实际行为：

```python
with tx("orders"):
    print("业务执行")
# [orders] BEGIN
# 业务执行
# [orders] COMMIT
# [orders] 释放连接

try:
    with tx("refund"):
        raise ValueError("余额不足")
except ValueError:
    pass
# [refund] BEGIN
# [refund] ROLLBACK: 余额不足
# [refund] 释放连接
```

机制上，`with` 块的异常会被 **`throw` 进生成器的 `yield` 位置**。
所以 `try/except` 包住 `yield` 就能捕获块内异常，`finally` 就是清理点。

### 3.2 吞异常：不 re-raise 即可

`@contextmanager` 里没有"返回值"可控制，抑制异常的方式就是**捕获后不重新抛出**：

```python
@contextmanager
def ignore_value_error():
    try:
        yield
    except ValueError:
        pass                # 不 re-raise -> 生成器正常结束 -> 视为已处理

with ignore_value_error():
    raise ValueError("静默忽略")
print("之后的代码继续执行")
```

文档对这点有明确告诫：如果捕获异常只是为了记日志或做统计，**必须 re-raise**，
否则 `with` 语句会认为异常已被完全处理，程序带着错误状态继续往下跑。

### 3.3 单次使用，且必须恰好 yield 一次

`@contextmanager` 生成的上下文管理器**不能复用**——它内部就是一个生成器，走完即耗尽：

```python
cm = tx("shared")
with cm:
    pass
with cm:            # 第二次进入失败
    pass
```

报错信息随版本不同：3.13 上是 `AttributeError: '_GeneratorContextManager' object has no
attribute 'args'`（实现里第二次 `__enter__` 访问了已删除的属性），更早的版本抛
`RuntimeError: generator didn't yield`。**不要去记具体异常**，规则是：
每次 `with` 都调用一次工厂函数（`with tx("orders"):` 而不是复用变量）。

如果生成器一次都没 `yield`，则必定报错，这条错误信息是稳定的：

```python
@contextmanager
def never_yields():
    if False:
        yield

try:
    with never_yields():
        pass
except RuntimeError as e:
    print(e)          # generator didn't yield
```

> 这条约束的实际价值：`@contextmanager` 里"提前 return"会静默变成"没有 yield"，
> 上线后才在某个分支炸掉。需要提前退出时，应改成 `yield` 前抛异常，或改用 `nullcontext`。

## 4. contextlib 工具箱

| 工具 | 用途 | 版本 | 典型场景 |
|------|------|------|----------|
| `closing(thing)` | 退出时调用 `thing.close()` | — | 第三方对象只有 `close()`，没有 `with` |
| `suppress(*excs)` | 忽略指定异常 | 3.4 | 删除可能不存在的文件 |
| `nullcontext(v)` | 空上下文，`as` 得到 `v` | 3.7（3.10 支持异步） | 可选上下文的分支占位 |
| `ExitStack()` | 动态组合多个上下文与回调 | 3.3 | 数量由运行时决定的资源 |
| `AsyncExitStack()` | 异步版 | 3.7 | 异步资源组合 |
| `redirect_stdout(f)` | 临时重定向 `sys.stdout` | 3.4 | 捕获第三方库的打印输出 |
| `chdir(path)` | 临时切换工作目录 | 3.11 | 只适合单线程脚本 |
| `aclosing(agen)` | 退出时 `await agen.aclose()` | 3.10 | 异步生成器提前 break |

### 4.1 suppress：比 except: pass 好在哪里

```python
from contextlib import suppress
from pathlib import Path

with suppress(FileNotFoundError):
    Path("cache.tmp").unlink()
```

三个实际差别：捕获范围被限定在 with 块内（不会误吞后面代码的同类异常）；异常类型是显式的；
3.12 起还支持异常组——**只移除匹配的成员，其余重新组成新组抛出**：

```python
try:
    with suppress(ValueError):
        raise ExceptionGroup("g", [ValueError("v"), TypeError("t")])
except ExceptionGroup as e:
    print([type(x).__name__ for x in e.exceptions])   # ['TypeError']
```

> 文档对 `suppress` 有明确限定：只应用于"静默继续确实是正确行为"的特定错误。
> 用它包裹业务逻辑主干，等于把错误处理退化成 `except: pass`。

### 4.2 ExitStack：资源数量由运行时决定

固定的 `with a as x, b as y` 无法应对"要打开的文件列表是运行时才知道的"。
`ExitStack` 维护一个回调栈，退出时**逆序**执行：

```python
from contextlib import ExitStack, closing

events = []

class Tracked:
    def __init__(self, name):
        self.name = name
    def close(self):
        events.append(f"close {self.name}")

with ExitStack() as stack:
    handles = [stack.enter_context(closing(Tracked(n))) for n in ("a", "b", "c")]
    stack.callback(lambda: events.append("callback"))
    print([h.name for h in handles])      # ['a', 'b', 'c']

print(events)
# ['callback', 'close c', 'close b', 'close a']
```

注意 `callback` 最后注册却最先执行——它和 `enter_context` 共用同一个后进先出栈。

`ExitStack` 最有价值的用法是 **all-or-nothing**：一组资源要么全部获取成功，
要么在失败时把已获取的全部释放。`pop_all()` 可以把回调栈整体转移出去，
从而"成功后不再自动关闭"：

```python
def open_all(names):
    with ExitStack() as stack:
        for n in names:
            stack.enter_context(closing(Tracked(n)))
        return stack.pop_all()      # 转移回调，with 退出时不关闭

bundle = open_all(("x", "y"))
print(events[-2:])                  # ['close b', 'close a']，x/y 尚未关闭
bundle.close()
print(events[-2:])                  # ['close y', 'close x']
```

两个容易踩的坑：

- **`callback` 注册的回调无法抑制异常**（它拿不到异常信息），只有 `push` 传入完整的
  `__exit__` 才能抑制；
- **`ExitStack` 被 GC 时不会执行回调**（文档明确写了 "callbacks are not invoked implicitly
  when the context stack instance is garbage collected"），必须显式 `close()`。

### 4.3 nullcontext：可选上下文

```python
def maybe_capture(enabled):
    return open("debug.log", "w") if enabled else nullcontext(sys.stdout)

with maybe_capture(False) as f:
    print("这条进 stdout", file=f)
```

作用是把"有 / 没有上下文"的分支收敛成同一种写法，避免在调用处写两遍 `with` 块。

## 5. 异步版本

### 5.1 __aenter__ / __aexit__ 与 asynccontextmanager

协议完全对应，只是方法变成协程、语法变成 `async with`：

```python
import asyncio
from contextlib import asynccontextmanager

class AsyncResource:
    async def __aenter__(self):
        await asyncio.sleep(0)      # 模拟异步建立连接
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is ValueError:
            return True             # 异步版本同样靠真值抑制
        return None

async def main():
    async with AsyncResource():
        raise ValueError("业务失败")
    print("抑制后继续执行")
```

日常更多用生成器写法：

```python
@asynccontextmanager
async def db_tx(name):
    events.append(f"{name}:begin")
    try:
        yield name
        events.append(f"{name}:commit")
    except Exception as exc:
        events.append(f"{name}:rollback({exc})")
        raise
    finally:
        events.append(f"{name}:release")

async with db_tx("orders") as tx:
    ...
# ['orders:begin', 'use orders', 'orders:commit', 'orders:release']
```

`AsyncExitStack` 的用法与同步版一致，只是把 `enter_context` 换成
`await stack.enter_async_context(...)`。

### 5.2 aclosing：异步生成器提前退出的确定性清理

这是异步场景独有的坑。同步生成器被 `break` 后会由引用计数立即触发 `finally`；
**异步生成器不行**——它只能由事件循环的异步生成器钩子在关闭时统一回收：

```python
async def stream_rows(n):
    try:
        for i in range(n):
            yield i
    finally:
        print("释放游标")

async def without_aclosing():
    gen = stream_rows(100)
    async for row in gen:
        if row == 2:
            break
    print("break 之后立刻检查")      # 此时游标还没释放

asyncio.run(without_aclosing())
# break 之后立刻检查
# 释放游标            <- 出现在 asyncio.run 关闭事件循环时
```

实测顺序说明：清理**确实会执行**，但推迟到了事件循环 shutdown，
持有游标的时间被拉长；如果清理逻辑依赖某个已结束的 task，还可能直接失败。
`aclosing` 把清理绑到 with 块退出这个确定时点：

```python
from contextlib import aclosing

async def with_aclosing():
    async with aclosing(stream_rows(100)) as rows:
        async for row in rows:
            if row == 2:
                break
    print("with aclosing 块已退出")

asyncio.run(with_aclosing())
# 释放游标
# with aclosing 块已退出
```

> 用异步生成器读数据库游标、读消息队列时，只要循环体里可能出现 `break` 或异常，
> 就应该套 `aclosing`。这也解释了为什么 [[04-python-async|Python 异步编程]]
> 里宁可多写一层 `async with`。

## 6. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| `__exit__` 无脑 `return True` | 所有异常被静默吞掉，包括本该暴露的程序缺陷 | 只在明确"这类异常可忽略"时返回真值 |
| 清理动作写在 `except` 分支 | 正常路径不清理，异常被抑制时也不清理 | 放 `finally` |
| `__enter__` 分多步获取资源 | 中途失败时 `__exit__` 不会调用，前半段泄漏 | 用 `ExitStack` 逐步 push，或自己 try/except 回滚 |
| 复用 `@contextmanager` 实例 | 生成器已耗尽，第二次进入报错 | 每次调用工厂函数重新创建 |
| 只捕获不 re-raise | 异常被视为已处理，程序带错误状态继续 | 记日志后 `raise` |
| `@contextmanager` 里提前 `return` | 等价于"没有 yield"，`with` 处报 `generator didn't yield` | 改为抛异常或 `nullcontext` |
| 用 `with` 改全局状态还不加锁 | `chdir` / `redirect_stdout` 影响进程级全局，多线程下互相干扰 | 只用于单线程脚本；并发场景改为显式传参 |
| `closing()` 包已支持 with 的对象 | 多一层包装，语义反而模糊 | 直接 `with obj:` |
| `ExitStack` 依赖 GC 触发清理 | 文档明确 GC 不执行回调 | 显式 `close()` 或用 `with` |
| 嵌套 `with` 顺序随意 | 后进入的先退出，顺序颠倒会让依赖方先被清理 | 按依赖关系从外到内书写 |

## 7. 与相关概念的关系

- **与 [[13-python-exceptions|Python 异常处理]]**：`__exit__` 是异常处理的第二个入口，
  与 `except` 的区别是"它必须处理所有类型，且只能整体抑制"。`with` 也不该替代
  `try/except`——前者管资源生命周期，后者管错误语义。
- **与 [[04-python-async|Python 异步编程]]**：`asyncio.timeout()`、`TaskGroup` 都是
  异步上下文管理器；`CancelledError` 会在 `__aexit__` 里出现，清理逻辑要能容忍它。
- **与 [[16-pathlib|pathlib]]**：`Path.read_text()` / `write_text()` 内部已完成
  打开-关闭，不需要额外套 `with`；只有需要流式读写时才用 `Path.open()`。
- **与 [[17-pytest|pytest 测试]]**：fixture 的 `yield` 结构与 `@contextmanager` 同构，
  测试中的临时资源清理常直接复用 `ExitStack`。

## 参考

- [contextlib — Utilities for with-statement contexts](https://docs.python.org/3/library/contextlib.html)
- [The with statement (Language Reference)](https://docs.python.org/3/reference/compound_stmts.html#the-with-statement)
- [PEP 343 – The "with" Statement](https://peps.python.org/pep-0343/)
- [[01-python-basics|Python 基础语法]]
