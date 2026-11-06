---
title: Python 面向对象
description: 类的定义与访问控制、继承与 MRO、property 与描述符协议、抽象基类、组合与继承的取舍、元类，以及特殊方法（dunder）与 __slots__ 的核心机制
tags:
  - python
  - oop
  - dunder-methods
  - descriptor
date: 2026-11-06
aliases:
  - python-oop
---

# Python 面向对象

Python 的类系统有两层：**语法层**（`class`、继承、`super()`）和**协议层**（dunder 方法、描述符、元类）。
日常写业务代码只用得上第一层，但只要碰过框架（Django Model、Pydantic、SQLAlchemy、`dataclasses`），
就已经在不知不觉地使用第二层。本文按"定义 → 继承 → 封装 → 多态 → 特殊方法 → 类创建"的顺序展开。

## 1. 类的定义

```python
class Student(object):
    def __init__(self, name, score):
        self.name = name
        self.score = score
    
    def print_score(self):
        print('%s: %s' % (self.name, self.score))
```

### 访问限制

- `__foo__` - 特殊方法，系统定义名字，类似 `__init__()`
- `_foo` - 保护类型（protected），只能允许其本身与子类进行访问
- `__foo` - 私有类型（private），只能允许这个类本身进行访问

补充两点原文没展开的机制：

| 写法 | 真实机制 | 能否从外部访问 |
|------|---------|---------------|
| `_foo` | **纯约定**，解释器不做任何处理，只靠 `from module import *` 时被跳过 | 能，`obj._foo` 照常 |
| `__foo`（类内） | 名称改写（name mangling）：编译期变成 `_类名__foo` | 能，但要写 `obj._Student__foo` |
| `__foo__` | 前后双下划线，Python 保留给特殊方法 | 能，且**不应该自己造**这种名字 |

```python
class Student:
    def __init__(self):
        self.__secret = 42       # 实际存成 _Student__secret

s = Student()
print(s._Student__secret)        # 42 —— "私有"只是改了名字，不是访问控制
print(hasattr(s, "__secret"))    # False
```

> 结论：Python 没有真正的私有成员。`__x` 的目的是**避免子类意外覆盖父类的内部属性**，不是安全边界。

---

## 2. 继承与方法解析顺序（MRO）

### 2.1 单继承与 `super()`

```python
class Animal:
    def __init__(self, name: str) -> None:
        self.name = name

    def speak(self) -> str:
        return f"{self.name} 发出声音"

class Dog(Animal):
    def __init__(self, name: str, breed: str) -> None:
        super().__init__(name)      # 别写 Animal.__init__(self, name)
        self.breed = breed

    def speak(self) -> str:
        return f"{self.name} 汪汪"
```

`super()` 不带参数时依赖编译器注入的 `__class__` 闭包，所以在类体内直接写 `super()` 才有"隐式 self/cls"；把它赋值给变量再调用会失效。

### 2.2 MRO：多继承时按什么顺序找方法

Python 用 **C3 线性化**算法把继承图压成一个线性列表，存在 `__mro__` 里：

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print([c.__name__ for c in D.__mro__])
# ['D', 'B', 'C', 'A', 'object']
```

规则可以概括为三条：

1. **子类先于父类**（D 在 B/C 之前）
2. **声明顺序靠前的基类优先**（B 在 C 之前）
3. **单调性**：某个类在列表中只出现一次，且不会出现"父类排在子类前面"

C3 保证的正是"菱形继承下公共祖先只执行一次"，这也是 Python 敢支持多继承的底气。

### 2.3 `super()` 不是"父类"，而是"MRO 上的下一个"

这是最容易被误解的一点。`super()` 返回的是一个**代理对象**，它沿着 `__mro__` 找**当前类之后**的那个类：

```python
class X:
    def who(self): return "X"

class Y(X):
    def who(self): return "Y->" + super().who()

class Z(X):
    def who(self): return "Z->" + super().who()

class W(Y, Z):
    pass

print(W().who())   # Y->Z->X
```

注意 `Y.who()` 里的 `super()` 从 `W` 的 MRO 看是 `Z`，而不是 `X`——尽管 `Y` 的直接父类是 `X`。**`super()` 的查找起点由"实例的实际类型"决定，不是由定义它的类决定。**

### 2.4 协作式多继承（cooperative multiple inheritance）

由此推出一个硬性要求：**多继承链上的每个方法都必须调用 `super()`**，否则链条断掉。

```python
class Base:
    def hello(self) -> list[str]:
        return ["Base"]

class M1(Base):
    def hello(self) -> list[str]:
        return ["M1"] + super().hello()

class M2(Base):
    def hello(self) -> list[str]:
        return ["M2"] + super().hello()

class Child(M1, M2):
    def hello(self) -> list[str]:
        return ["Child"] + super().hello()

print(Child().hello())   # ['Child', 'M1', 'M2', 'Base']
```

如果 `M2.hello()` 里不调 `super()`，`Base.hello()` 就永远不会执行——这正是"混入（Mixin）"类必须写成协作式的原因。

### 2.5 Mixin 模式

多继承最适合的用法不是"is-a 分类"，而是**横向能力叠加**：

```python
class TimestampMixin:
    def touch(self) -> None:
        import time
        self.updated_at = time.time()

class LogMixin:
    def log(self, msg: str) -> None:
        print(f"[{type(self).__name__}] {msg}")

class Order(TimestampMixin, LogMixin):   # 能力混入，无共同父类
    def __init__(self, oid: str) -> None:
        self.oid = oid

o = Order("A001")
o.touch()
o.log(f"创建订单 {o.oid}")
```

Mixin 的约定：**只提供方法、不定义 `__init__`、不保存自身状态**（状态一律放实例上），这样它们才能被安全地插到任意 MRO 位置。

---

## 3. 封装：property 与描述符

### 3.1 `property`：把方法伪装成属性

```python
class Temperature:
    def __init__(self, celsius: float = 0.0) -> None:
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("低于绝对零度")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:       # 只读派生属性
        return self._celsius * 9 / 5 + 32

t = Temperature()
t.celsius = 25          # 走 setter，触发校验
print(t.fahrenheit)     # 77.0
```

用 `property` 而不是直接暴露 `self.celsius = value` 的三个理由：

| 需求 | 直接属性 | `property` |
|------|---------|-----------|
| 赋值时校验 | ❌ 只能靠 `__setattr__` | ✅ setter 里写 |
| 派生值（如摄氏度→华氏度） | ❌ 需要额外同步，容易不一致 | ✅ 每次实时计算 |
| 未来加逻辑而不改调用方 | ❌ 接口会变 | ✅ 读写语法不变 |
| 性能 | 最快 | 每次访问有一次函数调用开销 |

### 3.2 描述符协议：`property` 的底层

`property` 本身不是魔法，它只是**描述符协议**的一个内置实现。任何实现了下面任一方法的类都是描述符：

| 方法 | 触发时机 |
|------|---------|
| `__get__(self, obj, objtype=None)` | `obj.attr` 读取 |
| `__set__(self, obj, value)` | `obj.attr = value` 赋值 |
| `__delete__(self, obj)` | `del obj.attr` |
| `__set_name__(self, owner, name)` | 类创建时自动调用，告知属性名 |

同时实现 `__get__` + `__set__` 的叫**数据描述符**，只有 `__get__` 的叫**非数据描述符**。属性查找优先级是：

```text
数据描述符  >  实例 __dict__  >  非数据描述符  >  类属性
```

这条优先级解释了三个日常现象：

- **函数是非数据描述符**，所以实例属性可以覆盖同名方法（`obj.method = lambda: 1` 会生效）
- **`property` 是数据描述符**，所以实例上写 `obj.celsius = 1` 不会盖住它，而是触发 setter
- **`__getattr__` 优先级最低**，只在常规查找全部失败后才调用

自建一个带校验的字段（这就是 Pydantic / Django ORM 字段的简化版）：

```python
class Field:
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = "_" + name          # 真实值存到 _age

    def __get__(self, obj, objtype=None):
        if obj is None:                 # 通过类访问：Model.age
            return self
        return getattr(obj, self.name, None)

    def __set__(self, obj, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError(f"{self.name} 必须是 int")
        setattr(obj, self.name, value)

class Model:
    age = Field()

m = Model()
m.age = 30
print(m.age)            # 30
m.age = "30"            # TypeError: _age 必须是 int
```

> `__set_name__` 是 Python 3.6+ 加的，在此之前字段类只能靠 `Model.__init__` 里手动传名字。写框架代码时优先用它。

---

## 4. 抽象基类与接口约定

### 4.1 `ABC` + `@abstractmethod`

想表达"这个类不能被直接实例化，子类必须实现某些方法"：

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...

    def describe(self) -> str:          # 抽象类里可以有具体方法
        return f"{type(self).__name__}: {self.area():.2f}"

class Circle(Shape):
    def __init__(self, r: float) -> None:
        self.r = r

    def area(self) -> float:
        return 3.14159 * self.r ** 2

print(Circle(1).describe())   # Circle: 3.14

class Bad(Shape):
    pass

Bad()   # TypeError: Can't instantiate abstract class Bad
        #            without an implementation for abstract method 'area'
```

要点：

- `ABC` 只是 `metaclass=ABCMeta` 的语法糖，两者等价
- **抽象类仍然可以有实现和状态**，`describe()` 这种模板方法放在抽象类里正合适
- 抽象方法可以有方法体，子类用 `super().area()` 复用
- `@abstractmethod` 与 `@staticmethod` / `@property` 叠加时，`@abstractmethod` 要放在**最内层**

```python
class Repo(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...      # 正确顺序：property 在外，abstractmethod 在内
```

### 4.2 `ABC` 与 `Protocol` 怎么选

| 方式 | 子类需要显式继承吗 | 是否做运行时检查 | 适用场景 |
|------|------------------|----------------|---------|
| `ABC` | ✅ 必须 | ✅ `isinstance` 有效 | 自己控制全部实现类，要共享代码 |
| `Protocol` | ❌ 结构匹配即可（鸭子类型） | 加 `@runtime_checkable` 才能 `isinstance` | 给第三方类定接口，不能改它 |

`Protocol` 的写法见 [[05-python-type-hints|Python 类型提示]]。经验法则：**自己写的类用 ABC（能共享代码），别人的类用 Protocol（只能约定形状）**。

---

## 5. 组合优于继承

继承表达 "is-a"，组合表达 "has-a / uses-a"。如果一句话说不通 "A 是一种 B"，就不应该用继承。

```python
# 反例：用继承复用"发送"能力，Logger 并不是一种 HttpClient
class HttpClient:
    def post(self, url: str, data: dict) -> None: ...

class Logger(HttpClient):        # 语义错误：Logger 不是 HttpClient
    def log(self, msg: str) -> None:
        self.post("https://logs.example.com", {"msg": msg})

# 正例：把能力作为依赖注入
class Logger:
    def __init__(self, client: HttpClient) -> None:
        self.client = client

    def log(self, msg: str) -> None:
        self.client.post("https://logs.example.com", {"msg": msg})
```

| 维度 | 继承 | 组合 |
|------|------|------|
| 耦合度 | 高（子类依赖父类实现细节） | 低（只依赖接口） |
| 运行时能否替换 | ❌ 编译期定死 | ✅ 构造时注入 |
| 多重能力叠加 | 只能靠多继承 / Mixin | 各自独立组合 |
| 修改父类的影响面 | 波及所有子类 | 不影响持有者 |
| 适合 | 真正的分类体系（`Circle` is a `Shape`） | 装配能力（`Service` 用一个 `Repo`） |

**判据（Liskov 替换原则）**：如果子类需要重写父类方法并抛 `NotImplementedError`、或者需要把父类的某几个方法"禁用"，说明继承关系用错了，改用组合。

---

## 6. 特殊方法（Dunder Methods）

Python 中以双下划线开头和结尾的特殊方法（称为 "dunder" 方法）为 Python 提供了强大的元编程能力。

### 6.1 对象生命周期

| 方法 | 说明 |
|------|------|
| `__new__(cls[, ...])` | 创建实例时调用（构造函数） |
| `__init__(self[, ...])` | 初始化实例 |
| `__del__(self)` | 对象销毁时调用 |

### 6.2 字符串表示

| 方法 | 说明 |
|------|------|
| `__str__(self)` | `str(obj)` 和 `print(obj)` 时调用 |
| `__repr__(self)` | `repr(obj)` 和交互式环境显示时调用 |
| `__format__(self, format_spec)` | 格式化输出 |

### 6.3 比较运算符

```python
__eq__(self, other)   # ==
__ne__(self, other)   # !=
__lt__(self, other)   # <
__le__(self, other)   # <=
__gt__(self, other)   # >
__ge__(self, other)   # >=
```

### 6.4 算术运算

```python
__add__(self, other)      # +
__sub__(self, other)      # -
__mul__(self, other)      # *
__truediv__(self, other)  # /
__floordiv__(self, other) # //
__mod__(self, other)      # %
__pow__(self, other)      # **
```

### 6.5 容器类型行为

| 方法 | 说明 |
|------|------|
| `__len__(self)` | `len(obj)` 时调用 |
| `__getitem__(self, key)` | `obj[key]` 获取元素 |
| `__setitem__(self, key, value)` | `obj[key] = value` 设置元素 |
| `__delitem__(self, key)` | `del obj[key]` 删除元素 |
| `__contains__(self, item)` | `item in obj` 时调用 |

### 6.6 可调用对象

`__call__` 方法让对象可以像函数一样被调用。

```python
class Adder:
    def __call__(self, a, b):
        return a + b

add = Adder()
print(add(3, 5))  # 输出: 8
```

**核心概念：**
- **函数**：像遥控器，调用时执行特定动作
- **普通对象**：像电视机，有属性和方法，但不能直接"按"
- **`__call__`**：让"电视机"也变成"遥控器"

**主要用途：**

1. **状态保持** - 在多次调用之间保留内部状态

```python
class Counter:
    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1
        return self.count

counter = Counter()
print(counter())  # 1
print(counter())  # 2
```

2. **实现装饰器**

```python
import time

class TimerDecorator:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        start_time = time.time()
        result = self.func(*args, **kwargs)
        print(f"耗时: {time.time() - start_time:.4f}秒")
        return result

@TimerDecorator
def my_task(duration):
    time.sleep(duration)
    return "完成"

my_task(1)
```

### 6.7 属性访问

```python
__getattr__(self, name)      # 访问不存在的属性时
__getattribute__(self, name) # 访问任何属性时
__setattr__(self, name, value) # 设置属性时
__delattr__(self, name)      # 删除属性时
```

### 6.8 上下文管理器

| 方法 | 说明 |
|------|------|
| `__enter__(self)` | 进入 `with` 代码块时调用 |
| `__exit__(self, exc_type, exc_val, exc_tb)` | 退出 `with` 代码块时调用 |

### 6.9 类的内置属性

```python
hasattr(emp1, 'age')    # 如果存在 'age' 属性返回 True
getattr(emp1, 'age')    # 返回 'age' 属性的值
setattr(emp1, 'age', 8) # 添加属性 'age' 值为 8
delattr(emp1, 'age')    # 删除属性 'age'
```

常用内置属性：
- `__dict__` - 类的属性（包含一个字典）
- `__doc__` - 类的文档字符串
- `__name__` - 类名
- `__module__` - 类定义所在的模块
- `__bases__` - 类的所有父类构成元素

---

## 7. `__slots__`

`__slots__` 用于**显式声明类实例允许的属性**，从而优化内存使用和提高属性访问速度。

### 核心作用

1. **内存优化** - 用固定大小的数组替代字典存储属性，内存节省可达 30-50%
2. **属性限制** - 限制实例只能拥有 `__slots__` 中声明的属性
3. **性能提升** - 属性访问速度更快

### 基本用法

```python
class Person:
    __slots__ = ('name', 'age')
    
    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("Alice", 30)
p.gender = "Female"  # AttributeError
```

### 内存对比

```python
import sys

class WithoutSlots:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class WithSlots:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 未使用 __slots__: 约 120-140 字节/实例
# 使用 __slots__: 约 32-48 字节/实例
```

实测口径需要澄清一下：在 CPython 3.13 上 `sys.getsizeof(实例)` **两者都是 48 字节**，差别不在实例本身，而在那个额外的属性字典：

```python
a, b = WithoutSlots(1, 2), WithSlots(1, 2)

print(sys.getsizeof(a), sys.getsizeof(a.__dict__))   # 48 296 -> 合计 344
print(sys.getsizeof(b), hasattr(b, "__dict__"))      # 48 False -> 合计 48
print(sys.getsizeof(WithoutSlots), sys.getsizeof(WithSlots))   # 1712 944
```

也就是说，**每个实例省下的主要是 `__dict__` 那 296 字节**（字典本身还会随属性增多而扩容），
而类对象因为多了若干 slots 描述符反而变大 700 多字节。所以 `__slots__` 只在**实例数量远大于类数量**时才有意义。

### 继承行为

```python
class Base:
    __slots__ = ('a', 'b')

class Derived(Base):
    __slots__ = ('c', 'd')  # 继承父类的 slots 并添加新的
```

两个坑：

```python
# 坑 1：子类不写 __slots__，字典又回来了，父类的优化全废
class Child(Base):
    pass
hasattr(Child(), "__dict__")     # True

# 坑 2：多个带非空 slots 的基类无法合并布局
class A: __slots__ = ("a",)
class B: __slots__ = ("b",)
class C(A, B):                   # TypeError: multiple bases have instance lay-out conflict
    __slots__ = ()
```

想保住优化，继承链上**每一层**都得写 `__slots__`（可以写空元组 `()`）。

### 适用场景

- 需要创建大量实例的类（游戏实体、数据点、连接对象）
- 需要严格控制属性的类
- 性能敏感的应用

> 如果只是想要"字段固定 + 自动生成 `__init__`"，用 `@dataclass` 更省事，见
> [[07-python-advanced|Python 进阶话题]] 第 4 节；`@dataclass(slots=True)`（3.10+）可以直接生成 `__slots__`。

---

## 8. 元类与类的创建过程

### 8.1 类也是对象

`type(obj)` 得到类，`type(类)` 得到元类——默认就是 `type`：

```python
class A: pass

print(type(A))          # <class 'type'>
print(type(A()))        # <class 'A'>
```

所以 `class A: pass` 大致等价于：

```python
A = type("A", (), {})   # type(name, bases, namespace)
```

### 8.2 创建类的完整流程

```text
class Foo(Base, metaclass=Meta):
    x = 1
    def m(self): ...
```

1. 调用 `Meta.__prepare__(name, bases)` 得到类体命名空间（默认返回 `dict`）
2. 在命名空间中执行类体代码，`x`、`m` 写进去
3. 调用 `Meta.__new__(mcls, name, bases, ns)` 得到类对象
4. 对命名空间里所有实现了 `__set_name__` 的值调用它（描述符靠这步拿到名字）
5. 调用 `Meta.__init__(cls, name, bases, ns)`

### 8.3 最小可用示例：注册表

```python
class RegistryMeta(type):
    registry: dict[str, type] = {}

    def __new__(mcls, name, bases, ns, **kwargs):
        cls = super().__new__(mcls, name, bases, ns, **kwargs)
        if not name.startswith("_"):
            mcls.registry[name] = cls
        return cls

class Base(metaclass=RegistryMeta):
    pass

class OrderHandler(Base):
    pass

class UserHandler(Base):
    pass

print(RegistryMeta.registry)    # {'Base': ..., 'OrderHandler': ..., 'UserHandler': ...}
```

Django 的 Model、SQLAlchemy 的 declarative base 都是这个思路的复杂版本。

### 8.4 先别急着用元类

元类是"修改类创建过程"的**最后手段**，因为它完全不可读、难以组合、跟 IDE 和类型检查器配合差。按代价从低到高依次尝试：

| 需求 | 首选 | 示例 |
|------|------|------|
| 给单个类加能力 | 类装饰器 | `@dataclass`、`@total_ordering` |
| 给所有子类加行为 | `__init_subclass__`（3.6+） | 自动注册、校验类属性 |
| 控制实例的创建 | `__new__` 或 `__init__` | 单例、对象池 |
| 改变"类"本身怎么生成 | 元类 | 注册表、接口校验、DSL |

`__init_subclass__` 能覆盖大部分元类场景，写起来是普通方法：

```python
class Plugin:
    plugins: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.plugins[cls.__name__] = cls

class CSVPlugin(Plugin):
    pass

print(Plugin.plugins)   # {'CSVPlugin': <class 'CSVPlugin'>}
```

---

## 9. 特殊变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `__name__` | 模块的名称，直接运行时为 `'__main__'` | `if __name__ == '__main__':` |
| `__file__` | 当前模块的文件路径 | `print(__file__)` |
| `__doc__` | 文档字符串 | `func.__doc__` |
| `__package__` | 当前模块所属的包名 | - |
| `__annotations__` | 类型注解字典 | `{'a': int, 'return': str}` |
| `__all__` | 控制 `from module import *` 导入的内容 | `__all__ = ['func1']` |
| `__mro__` | 方法解析顺序 | `ClassA.__mro__` |
| `__bases__` | 类的基类元组 | `Child.__bases__` |
| `__subclasses__()` | 获取类的直接子类列表 | `Parent.__subclasses__()` |

---

## 10. 总结表格

| 类别 | 特殊成员 | 主要用途 |
|------|----------|----------|
| 对象生命周期 | `__new__`, `__init__`, `__del__` | 创建/初始化/销毁对象 |
| 字符串表示 | `__str__`, `__repr__`, `__format__` | 自定义对象显示 |
| 运算符重载 | `__add__`, `__eq__`, `__lt__` 等 | 重载运算符行为 |
| 容器行为 | `__len__`, `__getitem__`, `__setitem__` | 使对象像容器 |
| 属性控制 | `__slots__`, `__getattr__`, `__setattr__` | 控制属性访问 |
| 可调用对象 | `__call__` | 使实例可像函数调用 |
| 上下文管理 | `__enter__`, `__exit__` | 实现 `with` 语句 |
| 类关系 | `__bases__`, `__mro__`, `__subclasses__` | 类继承关系 |
| 继承协作 | `super()`, `__init_subclass__` | 沿 MRO 调用、子类钩子 |
| 属性协议 | `__get__`, `__set__`, `__set_name__` | 描述符（`property` 的底层） |
| 抽象接口 | `ABC`, `@abstractmethod` | 强制子类实现方法 |

三条最容易踩的结论：

1. `super()` 找的是 **MRO 上的下一个类**，不是"父类"；多继承链上必须层层调用
2. `property` 是**数据描述符**，所以实例属性盖不住它；普通函数是**非数据描述符**，所以能被实例属性盖住
3. `__slots__` 省的是 `__dict__`，且**每一层子类都要写**才有效

---

## See Also

- [[01-python-basics|Python 基础语法]] —— 属性访问与命名空间是理解类的基础
- [[03-python-functional|Python 函数式编程]] —— 装饰器本质是"接收函数返回函数"，与 `__call__` 同源
- [[05-python-type-hints|Python 类型提示]] —— 类属性标注、`Self`、`Protocol` 与 `override`
- [[07-python-advanced|Python 进阶话题]] —— `dataclass` 是手写 `__init__`/`__repr__` 的官方替代
- [[04-python-async|Python 异步编程]] —— `__aenter__`/`__aiter__` 等异步协议
- [[06-AI/python/index|Python 笔记目录]]

## 参考

- [Python 官方文档 - 数据模型（3.3 特殊方法查找 / 3.4 类创建）](https://docs.python.org/3/reference/datamodel.html)
- [Python 官方文档 - 内置类型与描述符指南](https://docs.python.org/3/howto/descriptor.html)
- [Python 官方文档 - abc 模块](https://docs.python.org/3/library/abc.html)
- [The Python 2.3 Method Resolution Order（C3 算法原文）](https://www.python.org/download/releases/2.3/mro/)
