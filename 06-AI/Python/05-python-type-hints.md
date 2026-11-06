---
title: Python 类型提示
description: typing 模块的类型标注体系，从基础语法到 Protocol、TypedDict、TypeGuard、PEP 695 泛型、ParamSpec 与 mypy/pyright 实操
tags:
  - python
  - typing
  - type-hints
date: 2026-11-06
aliases:
  - python-type-hints
---

# Python 类型提示

Python 的 `typing` 模块是 Python 3.5 引入的标准库，为 Python 添加了**类型提示（Type Hints）**的支持。

虽然 Python 本质上仍然是一门**动态类型语言**（在运行时不会强制检查类型），但类型提示主要用于**静态分析**工具（如 mypy、IDE），以提高代码的可读性和健壮性。

---

## 1. 核心作用

1. **静态类型检查**：使用 `mypy` 等工具可以在代码运行前发现类型错误
2. **提升开发效率**：IDE 能根据类型提示提供精准的代码补全和错误高亮
3. **文档化代码**：类型提示本身就是最好的文档

---

## 2. 基础用法

### 变量注解

```python
name: str = "Alice"
age: int = 30
is_active: bool = True
```

### 函数注解

使用 `->` 标记返回值类型：

```python
def greeting(name: str) -> str:
    return "Hello " + name
```

---

## 3. 容器类型

从 Python 3.9 开始，可以直接使用内置的 `list[]`、`dict[]` 等。

| 类型                | 用法示例              | 说明            |
| ----------------- | ----------------- | ------------- |
| `list[int]`       | `List[int]`       | 一个只包含整数的列表    |
| `dict[str, int]`  | `Dict[str, int]`  | 键是字符串，值是整数的字典 |
| `tuple[str, int]` | `Tuple[str, int]` | 定长元组          |
| `set[str]`        | `Set[str]`        | 包含字符串的集合      |

```python
from typing import List, Dict

numbers: List[int] = [1, 2, 3, 4]
scores: Dict[str, float] = {"Alice": 95.5, "Bob": 88.0}
```

补充两种高频容器的精确写法：

```python
# 变长同构元组 vs 定长异构元组
coords: tuple[int, ...] = (1, 2, 3)       # 任意个 int
point: tuple[float, float] = (1.0, 2.0)   # 恰好两个 float

# 可空映射：值是 int 或 None
cache: dict[str, int | None] = {}

# 只读视图（协变，适合做函数参数）
from collections.abc import Mapping, Sequence
def total(prices: Mapping[str, float]) -> float:
    return sum(prices.values())
```

> 优先用 `collections.abc` 里的抽象类型（`Sequence` / `Mapping` / `Iterable`）做**参数**标注，
> 用具体类型（`list` / `dict`）做**返回值**标注——前者让调用方可以传任何兼容类型，后者给调用方更多信息。

---

## 4. 逻辑类型

### Union（联合类型）

表示变量可以是几种类型中的一种：

```python
from typing import Union

def process(x: Union[int, str]):
    pass

# Python 3.10+ 写法
def process(x: int | str):
    pass
```

### Optional（可选类型）

表示变量可以是某种类型，也可以是 `None`：

```python
from typing import Optional

def find_user(user_id: int) -> Optional[str]:
    if user_id == 1:
        return "Admin"
    return None

# 等价于 Union[str, None]
```

### Any（任意类型）

当无法确定类型时使用，静态检查器将不再检查该变量：

```python
from typing import Any

def messy_function(data: Any):
    print(data)
```

> `Any` 会**污染传播**：任何与 `Any` 交互的结果都变成 `Any`，检查器的保护在这一点上就断了。
> 用 `--disallow-any-expr`（mypy）或 `reportAny`（pyright strict）可以把它们揪出来。
> 能用 `object` + 收窄的地方，优先用 `object`。

---

## 5. 进阶用法

### Callable（函数类型）

用于标注一个参数是"函数"或"可调用对象"。

格式：`Callable[[Arg1Type, Arg2Type], ReturnType]`

```python
from collections.abc import Callable

def apply_func(x: int, func: Callable[[int], int]) -> int:
    return func(x)

def double(n: int) -> int:
    return n * 2

apply_func(5, double)  # 结果 10
```

### TypeVar（泛型）

当函数的参数类型和返回类型保持一致，但不限定具体类型时使用：

```python
from typing import TypeVar, List

T = TypeVar('T')

def get_first(items: List[T]) -> T:
    return items[0]
```

### Literal（字面量）

强制变量只能是特定的几个值之一：

```python
from typing import Literal

def open_file(mode: Literal['r', 'w', 'rb', 'wb']):
    pass

open_file('r')   # OK
open_file('x')   # Type Checker 会报错
```

### TypedDict

用于定义结构固定的字典：

```python
from typing import TypedDict, NotRequired

class User(TypedDict):
    name: str
    id: int
    email: NotRequired[str]  # Python 3.11+ 可选键

user: User = {"name": "Alice", "id": 101}
```

**核心优势：**
- 提升可读性：字典结构一目了然
- 增强健壮性：静态检查工具可发现错误
- 改善 IDE 支持：提供精确的代码补全

---

## 6. 协程相关类型

```python
from collections.abc import Awaitable, Coroutine, AsyncGenerator

async def fetch(url: str) -> str:
    ...

# 类型标注
result: Awaitable[str] = fetch("https://example.com")
coro: Coroutine[None, None, str] = fetch("https://example.com")
```

---

## 7. 注意事项

### 运行时不报错

Python 解释器在运行时会完全忽略类型提示：

```python
x: int = "hello"  # 运行时不会报错，IDE 会警告
```

### Python 3.9+ 的变化

建议直接使用内置类型（如 `list[str]`）代替 `typing.List[str]`。

### 循环引用

在类型提示中引用尚未定义的类：

```python
class Node:
    def add_child(self, node: 'Node'):  # 使用引号包裹类名
        pass
```

或者在文件头部加上 `from __future__ import annotations`（Python 3.7+）。

### Python 3.14+ 的变化：注解改为延迟求值

从 3.14 起（PEP 649 / PEP 749），函数、类、模块的注解**不再在定义时立即求值**，而是存进一个 `__annotate__` 函数里，按需求值。原文：

> "The annotations on functions, classes, and modules are no longer evaluated eagerly... evaluated only when necessary
> (except if `from __future__ import annotations` is used)."

实际影响：

```python
# 3.14+ 里这个写法不再报 NameError，因为注解根本没被求值
def make() -> Widget:      # Widget 在下面才定义
    ...

class Widget:
    pass
```

| 版本 | 行为 |
|------|------|
| ≤ 3.13 | 注解在定义时立即求值，前向引用必须加引号或开 `from __future__ import annotations` |
| 3.14+ | 默认延迟求值，前向引用可以直接写类名；`from __future__ import annotations` 仍可用，但会**退回**旧的字符串化行为 |
| 需要运行时读注解 | 用 `annotationlib.get_annotations()` 替代直接读 `__annotations__`，它支持 `Format.VALUE / FORWARDREF / STRING` |

所以"循环引用要加引号"这条建议在 3.14+ 已非必须，但**写引号依然兼容所有版本**，跨版本库还是建议保留。

---

## 8. 结构化子类型：Protocol

`Protocol`（PEP 544，3.8+）让你不必修改别人的类，就能声明"长得像这个就行"——这就是静态版的鸭子类型。

```python
from typing import Protocol

class Notifier(Protocol):
    def send(self, to: str, body: str) -> None: ...

class EmailNotifier:                    # 完全没有继承 Notifier
    def send(self, to: str, body: str) -> None:
        print(f"email -> {to}: {body}")

def notify(n: Notifier, to: str) -> None:
    n.send(to, "hello")

notify(EmailNotifier(), "a@b.com")      # 类型检查通过（结构匹配）
```

| 维度 | 具名子类型（ABC / 继承） | 结构化子类型（Protocol） |
|------|------------------------|------------------------|
| 是否需要改目标类 | ✅ 必须继承 | ❌ 不需要 |
| 能否给第三方类用 | ❌ 改不了 | ✅ 完全可以 |
| 能否共享实现代码 | ✅ 抽象类可放具体方法 | ❌ 只约定形状，无实现 |
| 运行时可 `isinstance` | ✅ | 需加 `@runtime_checkable` |

`@runtime_checkable` 的限制要说清楚：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Sized(Protocol):
    def __len__(self) -> int: ...

class Bag:
    def __len__(self) -> int: return 0

print(isinstance(Bag(), Sized))   # True
```

它**只检查成员是否存在，不校验签名**——`def __len__(self) -> str` 也会被判为 `True`。所以运行时检查只能当"粗略护栏"，真正的类型安全靠静态检查。

> 选型：自己控制全部实现类 → 用 `ABC`（能共享代码）；给别人的类定接口 → 用 `Protocol`。对比见 [[02-python-oop|Python 面向对象]] 第 4 节。

---

## 9. TypedDict 进阶

第 5 节给了基础写法，这里补上控制"哪些键必填、哪些只读"的开关：

```python
from typing import TypedDict, Required, NotRequired, ReadOnly

class Movie(TypedDict):
    title: str                    # 默认必填
    year: NotRequired[int]        # 可选
    rating: ReadOnly[float]       # 只读，赋值会被检查器拒绝

# 反向写法：整体可选，少量必填
class Config(TypedDict, total=False):
    debug: bool
    host: Required[str]
```

运行时的真相（别指望它做校验）：

```python
class User(TypedDict):
    name: str
    age: NotRequired[int]

print(User.__required_keys__, User.__optional_keys__)   # {'name'} {'age'}
u: User = {"name": "Alice"}      # 缺可选键没问题
u2: User = {"name": "b", "x": 1} # 多余键：静态检查器报错，运行时**不报错**
```

| 特性 | 版本 | 说明 |
|------|------|------|
| `TypedDict` | 3.8（PEP 589） | 结构化的 dict 类型 |
| `Required` / `NotRequired` | 3.11（PEP 655） | 逐键改必填性 |
| `ReadOnly` | 3.13（PEP 705） | 标记键不可写 |
| `closed=True` / `extra_items=` | 3.15 起（PEP 728） | 禁止或限定额外键；3.13 上会报 `unexpected keyword argument` |

TypedDict 与相邻方案的分工：

| 方案 | 运行时校验 | 开销 | 适用 |
|------|-----------|------|------|
| `TypedDict` | ❌ 完全不管 | 零 | 已经是 dict 的数据（JSON、API 响应） |
| `@dataclass` | ❌（仅类型标注） | 低 | 内部数据结构，要属性和方法 |
| Pydantic `BaseModel` | ✅ 强制校验 + 转换 | 中 | 外部输入边界（API 请求体、配置） |

详见 [[pydantic-validation|Pydantic 数据类型校验]]。

---

## 10. 类型收窄：TypeGuard 与 TypeIs

用来给自定义的判断函数"发证书"，让检查器在 `if` 分支里认账：

```python
from typing import TypeGuard, TypeIs

def is_str_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in val)

def is_int_list(val: list[object]) -> TypeIs[list[int]]:
    return all(isinstance(x, int) for x in val)

def handle(items: list[object]) -> None:
    if is_str_list(items):
        print(items[0].upper())    # items 被收窄为 list[str]
```

两者的区别是**关键考点**：

| 维度 | `TypeGuard[T]`（3.10，PEP 647） | `TypeIs[T]`（3.13，PEP 742） |
|------|-------------------------------|----------------------------|
| `if` 分支收窄 | ✅ | ✅ |
| `else` 分支收窄 | ❌ 保持原类型 | ✅ 收窄为"排除 T 之后剩下的类型" |
| 返回值与声明是否需一致 | ❌ 不校验（可以"说谎"） | ✅ 必须一致，否则检查器报错 |
| 与被检查类型的关系 | 可以收窄到任意子类型 | 目标类型必须是原类型的子类型 |

结论：**能用 `TypeIs` 就用 `TypeIs`**，它更严格、`else` 分支也有信息；`TypeGuard` 保留给"收窄到不相关类型"的特殊场景（如 `isinstance` 风格的工厂）。

---

## 11. 泛型进阶与 PEP 695

### 带约束的 TypeVar

```python
from typing import TypeVar

T = TypeVar("T")
Num = TypeVar("Num", int, float)              # 只能是 int 或 float
Comparable = TypeVar("Comparable", bound="SupportsRichComparison")   # 上界约束

def add(a: Num, b: Num) -> Num:
    return a + b
```

`bound=` 是"任意子类型都行"，枚举多个类型是"只能是这几个之一"——前者更灵活，日常优先用 `bound`。

### 泛型类：旧写法 vs PEP 695

```python
# 旧写法（3.11 及以前，仍完全支持）
from typing import Generic, TypeVar
T = TypeVar("T")

class Box(Generic[T]):
    def __init__(self, item: T) -> None:
        self.item = item
    def get(self) -> T:
        return self.item

# 新写法（3.12+，PEP 695）：类型参数声明在类名后
class Box[T]:
    def __init__(self, item: T) -> None:
        self.item = item
    def get(self) -> T:
        return self.item

print(Box[int](1).get())      # 1
print(Box.__type_params__)    # (T,)
```

### `type` 语句：类型别名

```python
# 旧写法：运行时不区分"别名"和"新类型"，容易混
Vector = list[float]

# 新写法（3.12+）：显式声明这是类型别名，可带类型参数
type Vector = list[float]
type Matrix[T] = list[list[T]]
```

`type` 语句创建的是惰性求值的别名对象，不会在定义时执行右侧表达式——这也是它能表达递归别名的原因。

### 变型（variance）一句话版

| 场景 | 写法 |
|------|------|
| 只读容器（生产者） | `TypeVar("T", covariant=True)`，如 `Sequence` |
| 只写容器（消费者） | `TypeVar("T", contravariant=True)`，如 `Sink` |
| 既读又写 | 默认不变（invariant），如 `list` |

PEP 695 的 `class Box[T]` 会**自动推断**变型，不再需要手写 `covariant=True`。

---

## 12. 可调用对象进阶

### ParamSpec：转发函数签名

装饰器最麻烦的是"包装后签名丢了"。`ParamSpec`（3.10，PEP 612）解决这个问题：

```python
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def with_retry(fn: Callable[P, R], times: int = 3) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        for attempt in range(times):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt == times - 1:
                    raise
        raise RuntimeError("unreachable")
    return wrapper

@with_retry
def fetch(url: str, timeout: float = 5.0) -> bytes: ...

fetch("https://example.com", timeout=1.0)   # 参数名与类型都被保留
```

`Concatenate` 用来在签名前面**追加**固定参数（如给每个被装饰函数注入 `self` 或 `logger`）：

```python
from collections.abc import Callable
from typing import Concatenate, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def with_logger(fn: Callable[Concatenate[str, P], R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn("[INFO]", *args, **kwargs)
    return wrapper

@with_logger
def log_it(level: str, msg: str) -> str:
    return f"{level}:{msg}"

print(log_it("hi"))    # [INFO]:hi
```

### `@overload`：同一函数多种签名

```python
from typing import overload

@overload
def parse(x: str) -> int: ...
@overload
def parse(x: bytes) -> str: ...
def parse(x: str | bytes) -> int | str:      # 实现：只有它参与运行时
    return int(x) if isinstance(x, str) else x.decode()

parse("42")     # 检查器推断为 int
parse(b"42")    # 检查器推断为 str
```

**必须遵守的三条**：至少两个 `@overload`；实现签名要能兼容所有重载；最后一个实现**不带** `@overload`。

---

## 13. Self、Never 与穷尽性检查

### `Self`：返回自身类型

```python
from typing import Self

class Builder:
    name: str
    def set_name(self, name: str) -> Self:
        self.name = name
        return self

class SubBuilder(Builder):
    extra: int
    def set_extra(self, v: int) -> Self:
        self.extra = v
        return self

SubBuilder().set_name("a").set_extra(1)   # 链式调用全程保持 SubBuilder
```

不用 `Self` 就得写 `TypeVar("T", bound="Builder")` 那套模板，`Self`（3.11，PEP 673）把它简化成一行。

### `Never`：表示"走不到这里"

```python
from typing import Literal, Never, assert_never

def handle(status: Literal["ok", "fail"]) -> str:
    if status == "ok":
        return "fine"
    elif status == "fail":
        return "bad"
    else:
        assert_never(status)      # 若 status 收窄后不是 Never，检查器报错
```

`assert_never` 的价值在**穷尽性检查**：以后给 `status` 加了新取值，忘了处理就会在类型检查阶段报错，
而不是运行时静默返回 `None`。这是替代 `raise NotImplementedError` 的现代写法。

`NoReturn` 是 `Never` 的旧名字（3.11 起 `Never` 为规范名），语义基本一致，新代码统一用 `Never`。

---

## 14. 类型检查器实操

### mypy

```bash
pip install mypy
mypy src/                       # 检查目录
mypy --strict src/              # 最严格档位，新项目建议直接开
mypy --install-types            # 自动补装缺失的 stub（types-requests 等）
```

### pyright

```bash
npm install -g pyright          # 官方分发方式（需要 Node）
pip install "pyright[nodejs]"   # PyPI 上的社区包装器，会自带 Node
pyright src/
```

> PyPI 上的 `pyright` 包**不是微软官方发布的**，它是 `pyright-python` 项目做的 CLI 包装器，运行时再去调 npm 包。要绝对可控就走 npm，图省事用 pip 也完全够用。

### 两者怎么选

| 维度 | mypy | pyright |
|------|------|---------|
| 实现语言 | Python | TypeScript（Node 运行） |
| 速度 | 慢 | 快（尤其大仓库） |
| 严格档位 | `--strict` | `typeCheckingMode = "strict"` |
| 生态 | 老牌，插件多（Django、SQLAlchemy） | VS Code / Pylance 同源，编辑器体验一致 |
| 误报倾向 | 偏保守 | 偏激进（推断更聪明） |

### 配置写进 `pyproject.toml`

```toml
[tool.mypy]
strict = true
python_version = "3.12"
files = ["src"]
warn_unused_ignores = true      # 忽略注释失效时报警，防止堆积

[tool.pyright]
include = ["src"]
typeCheckingMode = "standard"   # off / basic / standard / strict
venvPath = "."
venv = ".venv"                  # 让它找到项目环境里的第三方包
```

### 三个日常工具

```python
from typing import cast, reveal_type

value: object = get_payload()

reveal_type(value)              # 检查器在此处报告推断类型；3.11+ 运行时会真的打印一行
n = cast(int, value)            # 强制断言类型，运行时不做任何转换

x: int = "hello"  # type: ignore[assignment]   # 精确到错误码，别用裸 ignore
```

CI 里最小一条：

```yaml
- run: uv run mypy --strict src
- run: uv run pyright src
```

---

## 15. 注解的运行时行为

### `__annotations__` 存的是什么

```python
def f(x: "int") -> "list[int]":
    return [x]

print(f.__annotations__)          # {'x': 'int', 'return': 'list[int]'}  —— 原样字符串
```

它**不做求值、不做转换**，存的就是源码里的对象（写成字符串就存字符串）。想拿到真实类型对象要用 `get_type_hints()`：

```python
from typing import get_type_hints
print(get_type_hints(f))          # {'x': <class 'int'>, 'return': list[int]}
```

代价是它会**真的执行**注解里的表达式，所以引用了未定义名称时会抛 `NameError`。

### `TYPE_CHECKING`：只在类型检查时导入

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:                 # 运行时为 False，静态检查时按 True 处理
    from expensive_lib import HeavyType   # 避免运行时导入开销与循环导入

def process(x: "HeavyType") -> None:      # 运行时用字符串，避免 NameError
    ...
```

这是解决"循环导入 + 类型标注"的标准手法，比把 import 挪来挪去干净得多。

### 运行时校验只能靠专门库

类型提示**不产生任何运行时检查**，想让它在运行时生效必须显式验证：

```python
from typing import get_type_hints

def checked(fn):
    hints = get_type_hints(fn)
    def wrapper(*args, **kwargs):
        for (name, value) in zip(hints, args):
            expect = hints[name]
            if not isinstance(value, expect):
                raise TypeError(f"{name} 期望 {expect}，实际 {type(value)}")
        return fn(*args, **kwargs)
    return wrapper
```

这段手写代码就是 Pydantic 的雏形。生产环境直接用 [[pydantic-validation|Pydantic]]，别自己造。

---

## 16. 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `Cannot find stub for module "requests"` | 目标库没带 `py.typed` 标记 | 装 `types-requests` 或 `mypy --install-types` |
| `Library stubs not installed for "yaml"` | 同上 | `pip install types-PyYAML` |
| `Name "X" is not defined` | 前向引用没加引号（≤3.13），或 `TYPE_CHECKING` 里导入过 | 加引号 / 开 `from __future__ import annotations` |
| `Incompatible types in assignment`（`None`） | 用了 `Optional` 却直接当非空用 | 先 `if x is not None:` 收窄 |
| 加了 `# type: ignore` 反而报 `unused ignore` | 该行本来没错误，或错误码不匹配 | 写 `# type: ignore[code]`；或删掉该注释 |
| `mypy` 报第三方库内部一堆错 | 检查范围包含了 `site-packages` | `exclude = ["\\.venv"]`；只检查自己的 `src/` |
| pyright 找不到项目依赖 | 没告诉它虚拟环境在哪 | `[tool.pyright]` 里配 `venvPath` + `venv` |
| `TypeError: ... unexpected keyword argument 'closed'` | `closed=` 需要 3.15+ | 3.13 及以下用 `total=False` 或换 Pydantic |
| `NameError` 出现在 `get_type_hints()` | 注解引用了运行时不可见的名称 | 把 import 提到顶层，或用 `Format.STRING` 读取 |

---

## 17. 总结

| 类型 | 用途 | 示例 |
|------|------|------|
| `list[int]` | 列表类型 | `def f(items: list[int])` |
| `dict[str, int]` | 字典类型 | `scores: dict[str, int]` |
| `Union[A, B]` | 联合类型 | `Union[int, str]` 或 `int \| str` |
| `Optional[T]` | 可选类型 | `Optional[str]` |
| `Callable[[Args], Return]` | 函数类型 | `Callable[[int], str]` |
| `TypedDict` | 结构化字典 | 定义固定键值类型的字典 |
| `TypeVar` | 泛型 | `T = TypeVar('T')` |
| `Literal` | 字面量 | `Literal['a', 'b']` |
| `Protocol` | 结构化子类型 | 不继承也能"长得像" |
| `TypeIs` / `TypeGuard` | 类型收窄 | 自定义判断函数给 `if` 分支发证书 |
| `Self` | 返回自身类型 | 链式调用保持子类类型 |
| `ParamSpec` | 转发签名 | 装饰器保留原函数参数 |
| `Never` | 不可达 | 配合 `assert_never` 做穷尽检查 |

版本速查（按引入时间）：

| 版本 | 新增 |
|------|------|
| 3.8 | `Protocol`、`TypedDict`、`Final`、`Literal` |
| 3.9 | 内置泛型 `list[int]`、`dict[str, int]` |
| 3.10 | `int \| str` 联合语法、`TypeGuard`、`ParamSpec`、`Concatenate` |
| 3.11 | `Self`、`Never`、`Required` / `NotRequired`、`Unpack`、`assert_never` |
| 3.12 | PEP 695：`class Box[T]`、`type` 别名语句、`override` |
| 3.13 | `TypeIs`、`ReadOnly`、`NoDefault` |
| 3.14 | PEP 649 注解延迟求值、`annotationlib` |

---

## See Also

- [[01-python-basics|Python 基础语法]] —— 内置类型是标注的最小单位
- [[02-python-oop|Python 面向对象]] —— 类属性、方法签名的标注写法，以及 `ABC` 与 `Protocol` 的对比
- [[04-python-async|Python 异步编程]] —— `Coroutine`、`Awaitable`、`AsyncIterator` 的标注
- [[pydantic-validation|Pydantic 数据类型校验]] —— 把类型提示变成运行时校验
- [[07-python-advanced|Python 进阶话题]] —— `dataclass` 与类型标注天然配合
- [[06-AI/python/index|Python 笔记目录]]

## 参考

- [Python 官方文档 - typing](https://docs.python.org/3/library/typing.html)
- [Python 官方文档 - annotationlib（3.14+）](https://docs.python.org/3/library/annotationlib.html)
- [PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [PEP 589 – TypedDict](https://peps.python.org/pep-0589/)
- [PEP 612 – Parameter Specification Variables](https://peps.python.org/pep-0612/)
- [PEP 647 – User-Defined Type Guards](https://peps.python.org/pep-0647/)
- [PEP 673 – Self Type](https://peps.python.org/pep-0673/)
- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 742 – Narrowing types with TypeIs](https://peps.python.org/pep-0742/)
- [mypy 官方文档](https://mypy.readthedocs.io/)
- [pyright 官方文档](https://microsoft.github.io/pyright/)
