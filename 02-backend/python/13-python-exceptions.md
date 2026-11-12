---
title: Python 异常处理
description: 异常传播机制、异常链 __cause__/__context__、ExceptionGroup 与 except*、自定义异常体系设计、EAFP 与异常开销实测
tags:
  - python
  - exception-handling
  - error-handling
date: 2026-11-06
aliases:
  - python-exceptions
  - python-error-handling
---

# Python 异常处理

> **版本基线**：`ExceptionGroup` / `except*` / `add_note` 自 3.11 引入；`except*` 捕获 `BaseExceptionGroup`
> 的行为自 3.11 起可用。示例在本机 CPython 3.13 实跑验证。

## 1. 异常是什么：控制流的第二条通道

多数语言教程把异常讲成"报错处理"，这会造成两个误判：以为 `try` 只是给可能出错的代码包一层壳，
以及以为异常很慢、应当尽量用返回值代替。

异常真正的价值是**它是一条独立于返回值的控制流通道**：一旦抛出，它会沿着调用栈向上逐层展开，
直到遇到第一个愿意处理它的 `except`。这条通道可以让"20 层调用之下的磁盘写满"直接抵达
"main 里的统一错误处理"，中间 20 层完全不必知道失败的可能。

因此关于异常有三个必须理解的点，后文按此顺序展开：

| 问题 | 本质 | 对应章节 |
|------|------|----------|
| 谁能被捕获 | 异常是对象，靠 `isinstance` 匹配类型层级 | 第 2 节 |
| 在哪被捕获 | 栈展开过程与 `try/else/finally` 的先后顺序 | 第 3 节 |
| 原始错误去哪了 | 异常链，或在包装时被静默丢弃 | 第 4 节 |

## 2. 异常层级：BaseException 与 Exception 的分界

`BaseException` 之下只有五个直接子类，这个分界是 Python 刻意设计的"系统级信号 vs 应用级错误"：

```pycon
>>> [c.__name__ for c in BaseException.__subclasses__()]
['BaseExceptionGroup', 'Exception', 'GeneratorExit', 'KeyboardInterrupt', 'SystemExit']
>>> issubclass(SystemExit, Exception)
False
```

`KeyboardInterrupt`（Ctrl-C）、`SystemExit`（`sys.exit()`）、`GeneratorExit`（生成器被关闭）
都不属于 `Exception`。它们的共同点是：**由外部事件或解释器发起，而非程序逻辑出错**，
所以默认不该被业务代码拦截。

这条分界直接决定了两条写法禁令：

```python
# 反模式：裸 except 连 Ctrl-C 和 sys.exit 都吃掉，进程无法正常退出
try:
    run_service()
except:                      # 等价于 except BaseException
    pass

# 正确：只兜住应用级错误
try:
    run_service()
except Exception:
    logger.exception("服务启动失败")
```

实测确认了这个差异：

```python
def bare():
    try:
        raise SystemExit("退出")
    except:                      # 裸 except 连 SystemExit 都吃
        print("裸 except 捕获了 SystemExit")

def proper():
    try:
        raise SystemExit("退出")
    except Exception:            # 放过 SystemExit
        print("不该到这里")

bare()                           # 输出：裸 except 捕获了 SystemExit
try:
    proper()
except SystemExit as e:          # 到这一层才被接住
    print("except Exception 放过 SystemExit ->", e)
```

> `asyncio.CancelledError` 在 3.8 之前继承 `Exception`，3.8 起改为继承 `BaseException`，
> 理由与此完全相同：任务取消是调度器发起的信号，不该被 `except Exception` 顺手吞掉。
> 详见 [[04-python-async|Python 异步编程]]。

**自定义异常该继承谁**：一律继承 `Exception`（实践中继承自己的业务基类）。
继承 `BaseException` 会让调用方的 `except Exception` 完全失效，属于给自己埋雷。

## 3. try/except/else/finally 的执行顺序

四个子句不是"四个可选项"，而是一条确定的执行序列。实测输出如下：

```python
def order(raise_it):
    trace = []
    try:
        trace.append("try")
        if raise_it:
            raise ValueError("boom")
        trace.append("try-ok")
    except ValueError:
        trace.append("except")
    else:
        trace.append("else")
    finally:
        trace.append("finally")
    return trace

print(order(False))   # ['try', 'try-ok', 'else', 'finally']
print(order(True))    # ['try', 'except', 'finally']
```

两条规律：**`else` 只在 try 块零异常时执行**；**`finally` 在任何情况下都执行**（包括 `return`、
`break`、异常传播路径）。完整语义可以归纳成一张表：

| 情形 | 执行序列 | 异常是否继续传播 |
|------|----------|------------------|
| try 正常结束 | try → else → finally | 无异常 |
| try 内抛出且被 except 捕获 | try → except → finally | 否 |
| try 内抛出但无匹配 except | try → finally | 是 |
| except 内又抛新异常 | try → except → finally | 是（新异常，原异常进 `__context__`） |
| 上述任一分支中 return | 先执行 finally，再返回 | finally 中的 return 会覆盖原返回值 |

### 3.1 else 的价值：缩小捕获范围

`else` 唯一的作用是把"不该被 `except` 覆盖的代码"挪出 `try`：

```python
# 反模式：process() 抛的 ValueError 会被误判成"解析失败"
try:
    payload = json.loads(raw)
    result = process(payload)        # 这里的 ValueError 与 JSON 无关
except ValueError:
    logger.warning("JSON 解析失败")   # 归因错误

# 正确：try 只包住可能抛该异常的那一句
try:
    payload = json.loads(raw)
except ValueError:
    logger.warning("JSON 解析失败")
else:
    result = process(payload)        # 这里的异常原样向上传播
```

这条规则可以记成一句话：**`try` 块的大小应以"能准确说出捕获的是哪一句抛的"为下限**。

### 3.2 finally 的三个陷阱

**陷阱一：`finally` 里的 `return` 会吞掉异常。** 这不是"顺便返回"，而是把正在传播的异常
直接丢弃——连日志都不会留：

```python
def swallow():
    try:
        raise ValueError("本该抛出")
    finally:
        return "finally 的返回值"

print(swallow())     # finally 的返回值 —— 异常消失了
```

**陷阱二：`finally` 里抛新异常会覆盖原异常。** 原异常进 `__context__`，但打印出来的是新异常，
若新异常在 `finally` 中且没有 `from`，排查时极易看错主次。

**陷阱三：在 `finally` 里做可能失败的清理。** 例如 `conn.close()` 网络已断时抛错，
会掩盖真正的业务异常。清理动作应当自己兜住异常：

```python
try:
    process(conn)
finally:
    try:
        conn.close()          # 清理自身失败时不能盖住业务异常
    except Exception:
        logger.warning("连接关闭失败，忽略", exc_info=True)
```

## 4. 异常链：原始错误去哪了

包装异常（把底层 `ValueError` 变成业务 `ConfigError`）是常见操作，但包装方式决定了排查时
能否看到根因。Python 有两条链，语义完全不同：

| 属性 | 产生方式 | 含义 | traceback 中的措辞 |
|------|----------|------|--------------------|
| `__context__` | 处理 A 时抛出 B，自动设置 | "B 是在处理 A 的过程中发生的" | During handling of the above exception... |
| `__cause__` | `raise B from A` 显式设置 | "B 是由 A 直接导致的" | The above exception was the direct cause... |
| `__suppress_context__` | `raise B from None` | 隐藏 `__context__`，只显示 B | 只打印 B |

### 4.1 三种形态的实测

```python
class ConfigError(Exception):
    pass

def load():
    try:
        int("not-a-number")
    except ValueError as exc:
        raise ConfigError("配置解析失败") from exc     # 显式因果

try:
    load()
except ConfigError as e:
    print(e.__cause__)            # ValueError('invalid literal for int()...')
    print(e.__context__)          # 同一个对象
    print(e.__suppress_context__) # True：有 cause 时默认不显示 context
```

三种写法的 traceback 差别：

```python
raise ConfigError("配置解析失败") from exc   # 两个异常都打印，标注 direct cause
raise ConfigError("配置解析失败")            # 两个异常都打印，标注 During handling
raise ConfigError("配置解析失败") from None  # 只打印 ConfigError
```

`from None` 并不会清空 `__context__`，它只是把 `__suppress_context__` 置为 `True`
让打印器跳过——`e.__context__` 仍能取到原异常：

```python
try:
    load_suppressed()
except ConfigError as e:
    print(e.__suppress_context__)          # True
    print(type(e.__context__).__name__)    # ValueError，数据还在
```

### 4.2 什么时候必须写 from

| 场景 | 写法 | 理由 |
|------|------|------|
| 把底层异常翻译成业务异常 | `raise BizError(...) from exc` | 保留根因；不写会变成 "During handling"，把因果关系说成"顺带" |
| 在 except 里做重试后仍失败 | `raise` 或 `from exc` | 保留原栈，不要 `raise e`（见 4.4） |
| 底层异常对调用方无意义（如内部解析细节） | `from None` | 避免噪音；但要确保日志里已记录原异常 |
| 纯新增上下文信息 | `exc.add_note(...)` + `raise` | 不改变异常类型与因果链（见 4.3） |

### 4.3 add_note：给异常附加结构化上下文（3.11+）

过去要补充"这条数据是从哪来的"，只能拼进 message 字符串，破坏异常消息的可解析性。
3.11 的 `add_note()` 把附注单独存放，并追加在 traceback 末尾：

```python
def parse_order(raw):
    try:
        return {"id": int(raw)}
    except ValueError as exc:
        exc.add_note(f"原始输入: {raw!r}")
        exc.add_note("来源: POST /orders 请求体 order_id 字段")
        raise                      # 类型不变、栈不变，只是多了附注

try:
    parse_order("A-1001")
except ValueError as exc:
    print(exc.__notes__)
```

输出（`__notes__` 是字符串列表，traceback 里逐行追加在异常消息之后）：

```text
["原始输入: 'A-1001'", '来源: POST /orders 请求体 order_id 字段']
Traceback (most recent call last):
  ...
ValueError: invalid literal for int() with base 10: 'A-1001'
原始输入: 'A-1001'
来源: POST /orders 请求体 order_id 字段
```

> 附注只影响显示，`str(exc)` 不包含它们。需要机器可读的信息仍应放异常属性（见第 6 节）。

### 4.4 raise e 与 raise 的栈差异

在 `except` 块里重新抛出，`raise` 与 `raise e` 不等价。实测帧序列：

```python
def inner():
    raise ValueError("原始")

def rethrow_bad():
    try:
        inner()
    except ValueError as e:
        raise e          # 在当前行再抛一次，traceback 多出一帧

def rethrow_good():
    try:
        inner()
    except ValueError:
        raise            # 重新抛出当前异常，栈保持原样
```

```text
rethrow_bad:  ['<module>', 'rethrow_bad', 'rethrow_bad', 'inner']   # 重复帧
rethrow_good: ['<module>', 'rethrow_good', 'inner']                 # 干净
```

`raise e` 会让栈里出现两个 `rethrow_bad` 帧，深层嵌套时 traceback 迅速膨胀且指向误导性的行号。
**规则：能不接异常对象就不接**（`except ValueError:` 而非 `except ValueError as e:`），
需要原样重抛时用裸 `raise`。

## 5. ExceptionGroup 与 except*（3.11+）

### 5.1 为什么需要异常组

并发场景下"三个请求同时发，两个失败"是常态。`asyncio.gather` 默认只抛第一个异常，
其余失败被静默丢弃；要收集全部失败，过去只能手动维护一个列表再包装。
PEP 654 引入 `ExceptionGroup`：**一个异常对象里装多个异常**，且能被语法级拆解。

```python
# 手工构造：批量健康检查后的结果
raise ExceptionGroup("批量健康检查失败", [
    RuntimeError("订单服务 503"),
    ValueError("库存服务返回非法 JSON"),
    RuntimeError("用户服务超时"),
])
```

### 5.2 except* 的语义：按类型分组，剩余继续传播

`except*` 不是 `except` 的别名，它的行为完全不同：**每个子句只处理匹配的那部分子集，
未匹配的异常自动组成新组继续向上传播**；多个 `except*` 子句都会被尝试（而非命中即止）。

```python
try:
    raise ExceptionGroup("批量健康检查失败", [
        RuntimeError("订单服务 503"),
        ValueError("库存服务返回非法 JSON"),
        RuntimeError("用户服务超时"),
    ])
except* RuntimeError as group:
    print("RuntimeError 子组:", [str(e) for e in group.exceptions])
except* ValueError as group:
    print("ValueError 子组:", [str(e) for e in group.exceptions])
```

```text
RuntimeError 子组: ['订单服务 503', '用户服务超时']
ValueError 子组: ['库存服务返回非法 JSON']
```

关键细节：

- **`except*` 不能与 `except` 出现在同一个 `try`**，混用直接报语法错误
  `cannot have both 'except' and 'except*' on the same 'try'`；
- 子句里拿到的是**新的组对象**（由 `derive()` 生成），不是原组；
- **`except*` 也能接住单个异常**——解释器会自动把它包成只含一个成员的组，
  所以 `raise ValueError("单发")` 被 `except* ValueError` 捕获时，`as` 拿到的是
  `(1 sub-exception)` 的组而不是裸异常；这也是它不能与 `except` 混用的原因；
- 未匹配的异常不会消失，继续传播，外层可以再用普通 `except ExceptionGroup` 接住：

```python
try:
    try:
        raise ExceptionGroup("混合", [RuntimeError("r"), ValueError("v")])
    except* RuntimeError:
        print("只处理了 RuntimeError")
except ExceptionGroup as rest:
    print("剩余继续传播:", [type(e).__name__ for e in rest.exceptions])
# 剩余继续传播: ['ValueError']
```

### 5.3 嵌套组不会被拍平

这是最容易误判的一点：`except*` 匹配时会**保留嵌套结构**。内层组里命中的异常，
外层拿到的是"被裁剪过的内层组"，而不是裸异常：

```python
try:
    raise ExceptionGroup("外层", [
        ExceptionGroup("内层A", [ValueError("a1")]),
        RuntimeError("b"),
    ])
except* ValueError as g:
    print([str(e) for e in g.exceptions])
# ['内层A (1 sub-exception)']  ← 仍是组，不是 'a1'
```

所以处理嵌套组时要递归，或直接用下面三个 API。

### 5.4 split / subgroup / derive

| API | 作用 | 返回 |
|-----|------|------|
| `group.split(predicate)` | 按类型/谓词一分为二 | `(匹配的组, 剩余的组)`，某一侧为空时对应位置为 `None` |
| `group.subgroup(predicate)` | 只取匹配部分 | 组或 `None` |
| `group.derive(excs)` | 用同类组包装新异常列表 | 保留 `message` 与元数据类型 |

```python
group = ExceptionGroup("g", [ValueError("v1"), TypeError("t1"), ValueError("v2")])

matched, rest = group.split(ValueError)
print([str(e) for e in matched.exceptions])   # ['v1', 'v2']
print([type(e).__name__ for e in rest.exceptions])  # ['TypeError']

print([str(e) for e in group.subgroup(ValueError).exceptions])  # ['v1', 'v2']
```

> 实际写业务代码时，`except*` 已经覆盖九成场景；需要"部分失败部分成功"的返回值时，
> 用 `split()` 比在 `except*` 里手写状态更清晰。

## 6. 设计自定义异常体系

### 6.1 一个包一个基类

```python
class AppError(Exception):
    """所有业务异常的基类，便于上层一次性拦截。"""
    retriable = False

    def __init__(self, message, *, service=None, order_id=None):
        super().__init__(message)
        self.service = service
        self.order_id = order_id


class InventoryShortage(AppError):
    retriable = False


class UpstreamTimeout(AppError):
    retriable = True
```

好处是调用方可以分层次拦截：具体异常做补救，基类做兜底。

```python
try:
    charge("A-1001")
except UpstreamTimeout:
    schedule_retry()          # 可重试，走补偿
except AppError as exc:
    logger.error("业务失败", extra={"service": exc.service})
    raise
```

### 6.2 用属性携带上下文，不要拼字符串

```python
def charge(order_id):
    raise InventoryShortage("库存不足", service="inventory", order_id=order_id)

try:
    charge("A-1001")
except AppError as exc:
    print(exc.service, exc.order_id, exc.retriable)
# inventory A-1001 False
```

对比反模式 `raise InventoryShortage(f"库存不足 order={order_id} service=inventory")`：
后者只能靠正则从消息里抠字段，日志系统无法结构化索引，消息一改就全崩。

### 6.3 三条设计约束

| 约束 | 原因 | 反例 |
|------|------|------|
| 异常类型表达"错在哪一类"，属性表达"错在哪个对象" | 类型用于分支，属性用于展示 | 一个 `AppError` 配几十种 message 前缀 |
| 不要在异常里塞大对象 | 异常常被长期持有（如 `sys.exc_info`），大对象会延迟回收 | `self.payload = 整个 1MB 响应体` |
| `retriable` 这类策略标记放类属性 | 类属性零成本，实例属性每建一个异常多一次赋值 | 构造函数里 `self.retriable = True` |

## 7. EAFP vs LBYL

两种风格：**EAFP**（Easier to Ask Forgiveness than Permission，先做再捕异常）
与 **LBYL**（Look Before You Leap，先检查再执行）。

### 7.1 Python 偏好 EAFP 的实质原因

不是审美，而是 LBYL 在并发/外部状态下**根本不成立**：

```python
# LBYL：检查与使用之间存在时间窗口，文件随时可能被删
if path.exists():          # TOCTOU: Time-of-check to time-of-use
    data = path.read_text()  # 这里仍可能 FileNotFoundError

# EAFP：一步到位，不存在窗口
try:
    data = path.read_text()
except FileNotFoundError:
    data = ""
```

同理适用于 `dict` 取值、网络请求、数据库行锁——凡是"检查结果可能立即过期"的场景，
只能 EAFP。

### 7.2 性能真相：无异常路径几乎免费

"异常很慢"是 Python 2 时代的经验。3.11 起改用零成本异常（zero-cost exceptions）：
`try` 块在无异常时不产生任何运行时开销，成本只在**真正抛出**时才付。

本机实测（CPython 3.13，Apple Silicon，取 5 次最小值）：

| 写法 | 单次耗时 | 说明 |
|------|----------|------|
| `try` 取值命中（无异常） | 6.3 ns | 与不带 try 几乎无差别 |
| `if key in dict` 预判 | 9.9 ns | 反而更慢，多一次哈希查找 |
| `dict.get(key)` | 8.1 ns | 不需要区分"缺失"与"值为 None"时的最优解 |
| `try` 取值未命中（抛 `KeyError`） | 54.9 ns | 约为命中路径的 9 倍 |

但异常成本**随栈深线性增长**，因为 traceback 要逐帧记录：

| 抛出位置栈深 | 单次耗时 |
|--------------|----------|
| 0 层 | 137 ns |
| 20 层 | 1.1 µs |
| 60 层 | 3.1 µs |

结论：

- **正常路径用异常做分支是划算的**（6 ns vs 10 ns），不必为了"性能"把代码写成 LBYL；
- **异常路径不能当常规控制流**——深层调用里每循环抛一次，成本是普通分支的几十倍；
- 高频循环里的"缺失"判定，用 `dict.get()` 或哨兵值比抛异常更合适。

### 7.3 选型速查

| 场景 | 推荐 | 理由 |
|------|------|------|
| 键可能不存在，缺失是正常情况 | `d.get(k, default)` | 无异常开销，语义明确 |
| 键不存在代表数据损坏 | `d[k]` + `except KeyError` | 异常即信号，不该静默给默认值 |
| 文件/网络/外部状态 | EAFP | LBYL 存在 TOCTOU 窗口 |
| 参数校验（调用方错误） | LBYL（显式 `if` + `raise`） | 错误应在入口处暴露，不是靠深层异常回溯 |
| 高频循环里的可选字段 | 哨兵值 / `get` | 异常成本 × 循环次数 |

## 8. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| `except:` 兜住一切最安全 | 会吞掉 Ctrl-C、`sys.exit()`、`GeneratorExit` | 改用 `except Exception` |
| `except Exception: pass` | 失败被静默吞掉，问题延后爆发且无从定位 | 至少 `logger.exception()`；确实要忽略用 `contextlib.suppress` |
| `finally` 里 `return` | 正在传播的异常被直接丢弃 | `finally` 只做清理，不返回值 |
| `raise e` 重抛 | traceback 多出一帧且行号误导 | 用裸 `raise` |
| 包装异常不写 `from` | 根因变成 "During handling"，因果被弱化 | `raise NewError(...) from exc` |
| except 子句顺序随意 | 父类在前会让子类分支永远不执行 | 子类在前、父类在后 |
| 用 `e.args[0]` 取消息 | 多参数异常时错位；消息格式无契约 | `str(e)` 取展示文本，结构化信息放属性 |
| 在循环内 `try` 包住整个循环体 | 一次失败终止全部，无法逐条处理 | `try` 放进循环体内，逐条隔离 |
| 异常消息里拼业务数据 | 日志无法结构化检索 | 数据放属性 + `add_note` 补充上下文 |
| 自定义异常继承 `BaseException` | 调用方的 `except Exception` 全部失效 | 继承 `Exception` 或业务基类 |

## 9. 与相关概念的关系

- **与 [[14-context-managers|上下文管理器]]**：`with` 的 `__exit__(exc_type, exc, tb)` 是异常的
  另一个处理入口，返回 `True` 即抑制异常。资源清理优先用 `with` 而非 `finally`——
  后者容易漏掉"清理本身失败"的情况。
- **与 [[04-python-async|Python 异步编程]]**：`TaskGroup` 在兄弟任务失败时会取消其余任务并抛
  `ExceptionGroup`，必须用 `except*` 接；`CancelledError` 继承 `BaseException`，
  捕获后必须重抛。
- **与 [[17-pytest|pytest 测试]]**：`pytest.raises(ValueError, match="...")` 用正则匹配消息，
  这也是"异常消息要稳定"的一个现实约束。
- **与 [[18-debugging-profiling|调试与性能分析]]**：`traceback` 模块、`faulthandler`、
  事后调试（`pdb.post_mortem`）都建立在异常对象与 traceback 之上。

## 参考

- [Built-in Exceptions](https://docs.python.org/3/library/exceptions.html)
- [PEP 654 – Exception Groups and except*](https://peps.python.org/pep-0654/)
- [PEP 678 – Enriching Exceptions with Notes](https://peps.python.org/pep-0678/)
- [What's New in Python 3.11 – Faster CPython / zero-cost exceptions](https://docs.python.org/3/whatsnew/3.11.html)
- [[01-python-basics|Python 基础语法]]
- [[07-python-advanced|Python 进阶话题]]
