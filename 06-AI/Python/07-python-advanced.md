---
title: Python 进阶话题
description: PEP 机制、包与 __init__.py、dataclass、海象运算符与结构化模式匹配
tags:
  - python
  - pep
  - dataclass
date: 2026-11-06
aliases:
  - python-advanced
---

# Python 进阶话题

## 1. PEP（Python Enhancement Proposal）

PEP 是 **"Python Enhancement Proposal"** 的缩写，中文通常叫"Python 增强提案"。

它是一份设计文档，用来向 Python 社区提出：
- 新语言特性
- 标准库新增/修改
- 开发流程、编码规范、发布策略等改进

每份 PEP 先由作者公开草案，经 python-dev 邮件列表充分讨论，最后由 Python Steering Council 决定是否接受。

### 重要 PEP 速查表

| 发号 | 名称 | 引入版本 | 一句话作用 |
|------|------|----------|------------|
| **语言语法** |||
| PEP 8 | Style Guide for Python Code | 2001 | 社区最广泛遵循的代码格式与命名规范 |
| PEP 492 | async / await 语法 | 3.5 | 把协程做成一等语法，实现高效 I/O 并发 |
| PEP 572 | 海象运算符 := | 3.8 | 在表达式内完成赋值，减少重复求值 |
| PEP 634 | 结构化模式匹配 (match-case) | 3.10 | 类似 switch，但支持解构与守卫条件 |
| **类型提示** |||
| PEP 484 | Type Hints | 3.5 | 引入函数注解＋ typing 模块 |
| PEP 526 | 变量注解语法 | 3.6 | 给类属性、全局/局部变量也加上类型提示 |
| PEP 585 | 内置泛型 (list[int]) | 3.9 | 不再必须从 typing 引入 List Dict 等 |
| PEP 604 | 联合类型简写 (str \| int) | 3.10 | 用 \| 代替 Union |
| PEP 544 | Protocol（静态"鸭子类型"） | 3.8 | 无需继承即可描述对象接口 |
| **数据与性能** |||
| PEP 448 | 更通用解包 | 3.5 | 允许 {**d1, **d2}、[*a, *b] 等写法 |
| PEP 557 | Data Classes | 3.7 | 用 @dataclass 自动生成样板代码 |
| **构建与发布** |||
| PEP 440 | 版本号统一规范 | 2013 | 规定版本号格式 |
| PEP 517/518 | 构建后端隔离 | 3.6+ | 允许用非 setuptools 工具打包 |
| **并发与并行** |||
| PEP 3156 | asyncio 框架 | 3.4 | 统一事件循环、Future/Task 模型 |
| PEP 525/530 | 异步生成器/异步推导式 | 3.6/3.7 | 让 yield 与 for 也能在协程里高效工作 |

---

## 2. `__init__.py` 文件

`__init__.py` 文件是 Python 包中的一个特殊文件，它有几个重要作用：

### 2.1 标识目录为 Python 包

- 当 Python 解释器看到一个目录中包含 `__init__.py` 文件时，它会将该目录视为一个 Python 包
- 没有 `__init__.py` 的目录只是一个普通目录，不能被导入为包

### 2.2 执行包初始化代码

- 当包或包中的模块被导入时，`__init__.py` 文件会自动执行
- 可以在这里设置包级别的变量、导入必要的模块或执行初始化操作

### 2.3 控制包的导入行为

- 通过在 `__init__.py` 中定义 `__all__` 变量，可以控制 `from package import *` 的行为
- 可以在 `__init__.py` 中导入子模块，使它们在包级别可用

### 2.4 示例

```python
# __init__.py
"""这是一个示例包"""

__version__ = "1.0.0"
__all__ = ["function1", "Class1"]

from .module1 import function1
from .module2 import Class1

print("包已初始化")
```

### 2.5 Python 3.3+ 的变化

- 在 Python 3.3 之后，有了**命名空间包**（不需要 `__init__.py`）
- 但传统包仍然推荐使用 `__init__.py`

---

## 3. Runnable 概念

Runnable 并非 Python 内置关键字或类，而是 **并发编程中的概念**，指代"可被线程执行的任务/代码逻辑"。

### 3.1 函数作为 Runnable

```python
import threading

def task(name: str):
    print(f"Task {name}")

thread = threading.Thread(target=task, args=("A",))
thread.start()
thread.join()
```

### 3.2 类作为 Runnable

```python
import threading

class MyTask(threading.Thread):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def run(self):
        print(f"Task {self.name}")

task = MyTask("A")
task.start()
task.join()
```

### 3.3 Runnable vs 协程

| 特性 | Runnable（线程） | 协程 |
|------|------------------|------|
| 调度方式 | 内核态抢占式 | 用户态协作式 |
| 切换开销 | 较大 | 极小 |
| 适用场景 | I/O + CPU 密集型 | I/O 密集型 |

---

## 4. 数据类（dataclass）

PEP 557 引入，Python 3.7+ 支持：

```python
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int
    email: str = ""

p = Person("Alice", 30)
print(p)  # Person(name='Alice', age=30, email='')
```

自动生成 `__init__`、`__repr__`、`__eq__` 等方法。

---

## 5. 海象运算符（:=）

PEP 572 引入，Python 3.8+ 支持：

```python
# 在表达式内赋值
if (n := len(data)) > 10:
    print(f"数据太长: {n} 个元素")

# 避免重复调用
while (line := file.readline()) != "":
    process(line)
```

---

## 6. 结构化模式匹配

PEP 634 引入，Python 3.10+ 支持：

```python
def http_error(status):
    match status:
        case 400:
            return "Bad request"
        case 404:
            return "Not found"
        case 418:
            return "I'm a teapot"
        case 401 | 403 | 407:
            return "Not allowed"
        case _:
            return "Something's wrong"
```

### 解构匹配

```python
point = (1, 2)

match point:
    case (0, 0):
        print("Origin")
    case (0, y):
        print(f"Y axis: {y}")
    case (x, 0):
        print(f"X axis: {x}")
    case (x, y):
        print(f"Point: ({x}, {y})")
```

---

## See Also

- [[01-python-basics|Python 基础语法]] —— 语法层面的前置知识
- [[02-python-oop|Python 面向对象]] —— `dataclass` 生成的 `__init__`/`__repr__` 等价于手写 dunder
- [[05-python-type-hints|Python 类型提示]] —— PEP 484 → 695 的类型语法演进
- [[14-context-managers|Python 上下文管理器与 contextlib]] —— `with` 协议与装饰器的组合用法
  （`ContextDecorator` 让上下文管理器同时充当装饰器）
- [[13-python-exceptions|Python 异常处理]] —— `except*` 与 `ExceptionGroup` 属于 3.11 的语法级新特性
- [[15-python-concurrency|Python 并发与并行]] —— 解释器层面的约束（GIL、子解释器）
- [[08-pypi-pip|PyPI 与 pip]] —— `__init__.py` 与包发布的关系
- [[10-uv|uv 包管理器]] —— 现代项目脚手架与 PEP 机制的关系
- [[index|Python 笔记目录]]