---
title: Python 函数式编程
description: 列表生成式、生成器与迭代器、map/filter/sorted、装饰器与偏函数的用法与取舍
tags:
  - python
  - functional-programming
  - iterator
date: 2026-11-06
aliases:
  - python-functional
---

# Python 函数式编程

## 1. 列表生成式

```python
>>> [x * x for x in range(1, 11)]
[1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

>>> [x * x for x in range(1, 11) if x % 2 == 0]
[4, 16, 36, 64, 100]

>>> [m + n for m in 'ABC' for n in 'XYZ']
['AX', 'AY', 'AZ', 'BX', 'BY', 'BZ', 'CX', 'CY', 'CZ']
```

---

## 2. 生成器（Generator）

生成器是一种**惰性计算**的迭代器，按需生成值，节省内存。

### 生成器表达式

把列表生成式的 `[]` 改成 `()`：

```python
# 列表生成式
>>> L = [x * x for x in range(10)]
>>> L
[0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 生成器
>>> g = (x * x for x in range(10))
>>> g
<generator object <genexpr> at 0x1022ef630>

>>> next(g)
0
>>> next(g)
1
```

### yield 关键字

使用函数实现 generator：

```python
def fib(max):
    n, a, b = 0, 0, 1
    while n < max:
        yield b
        a, b = b, a + b
        n = n + 1
    return 'done'

>>> f = fib(6)
>>> for n in f:
...     print(n)
1
1
2
3
5
8
```

### yield 与 return 的区别

- `return`：返回值，函数结束
- `yield`：返回值，暂停函数，下次调用从暂停处继续

---

## 3. 迭代器

### 可迭代对象（Iterable）

可以直接作用于 `for` 循环的对象：

- 集合数据类型：`list`、`tuple`、`dict`、`set`、`str`
- `generator`

```python
>>> from collections.abc import Iterable
>>> isinstance([], Iterable)
True
>>> isinstance({}, Iterable)
True
>>> isinstance('abc', Iterable)
True
>>> isinstance((x for x in range(10)), Iterable)
True
```

### 迭代器（Iterator）

可以被 `next()` 函数调用并不断返回下一个值的对象：

```python
>>> from collections.abc import Iterator
>>> isinstance((x for x in range(10)), Iterator)
True
>>> isinstance([], Iterator)
False
>>> isinstance({}, Iterator)
False
```

### iter() 函数

将 Iterable 转为 Iterator：

```python
>>> isinstance(iter([]), Iterator)
True
>>> isinstance(iter('abc'), Iterator)
True
```

---

## 4. zip

`zip()` 用于把多个可迭代对象按位置“打包”在一起，每次返回一个元组。
它返回的是**惰性迭代器**，需要用 `list()`、`dict()` 或 `for` 循环消费。

### 基本用法

```python
names = ["Alice", "Bob", "Charlie"]
scores = [95, 87, 92]

for name, score in zip(names, scores):
    print(name, score)

# 输出:
# Alice 95
# Bob 87
# Charlie 92
```

### 生成字典

当一个列表保存键、另一个列表保存值时，可以直接配合 `dict()` 创建字典。

```python
keys = ["name", "age", "city"]
values = ["Alice", 20, "Shanghai"]

user = dict(zip(keys, values))
print(user)
# {'name': 'Alice', 'age': 20, 'city': 'Shanghai'}
```

### 同时遍历多个列表

`zip()` 常用于避免手动使用索引，让代码更清晰。

```python
products = ["book", "pen", "bag"]
prices = [30, 5, 120]
stocks = [10, 100, 8]

for product, price, stock in zip(products, prices, stocks):
    print(f"{product}: 单价 {price}, 库存 {stock}")
```

### 解包：矩阵转置

`zip(*iterable)` 可以把二维结构按列重新组合，常用于矩阵转置。

```python
matrix = [
    [1, 2, 3],
    [4, 5, 6],
]

transposed = list(zip(*matrix))
print(transposed)
# [(1, 4), (2, 5), (3, 6)]
```

如果需要列表而不是元组，可以再转换一次：

```python
transposed = [list(row) for row in zip(*matrix)]
print(transposed)
# [[1, 4], [2, 5], [3, 6]]
```

### 长度不一致时的行为

默认情况下，`zip()` 会在最短的可迭代对象耗尽时停止。

```python
names = ["Alice", "Bob", "Charlie"]
scores = [95, 87]

print(list(zip(names, scores)))
# [('Alice', 95), ('Bob', 87)]
```

Python 3.10+ 可以使用 `strict=True`。当多个可迭代对象长度不一致时，
它会抛出 `ValueError`，适合需要严格校验数据对齐的场景。

```python
names = ["Alice", "Bob", "Charlie"]
scores = [95, 87]

list(zip(names, scores, strict=True))
# ValueError: zip() argument 2 is shorter than argument 1
```

---

## 5. map/reduce

### map

将函数作用于序列的每个元素：

```python
>>> def f(x):
...     return x * x
...
>>> r = map(f, [1, 2, 3, 4, 5, 6, 7, 8, 9])
>>> list(r)
[1, 4, 9, 16, 25, 36, 49, 64, 81]
```

### reduce

对序列进行累积计算：

```python
>>> from functools import reduce
>>> def add(x, y):
...     return x + y
...
>>> reduce(add, [1, 3, 5, 7, 9])
25
```

---

## 6. filter

过滤序列：

```python
>>> def is_odd(n):
...     return n % 2 == 1
...
>>> list(filter(is_odd, [1, 2, 4, 5, 6, 9, 10, 15]))
[1, 5, 9, 15]
```

---

## 7. sorted

排序：

```python
>>> sorted([36, 5, -12, 9, -21])
[-21, -12, 5, 9, 36]

>>> sorted([36, 5, -12, 9, -21], key=abs)
[5, 9, -12, -21, 36]

>>> sorted(['bob', 'about', 'Zoo', 'Credit'], key=str.lower, reverse=True)
['Zoo', 'Credit', 'bob', 'about']
```

---

## 8. 装饰器

装饰器是一种**在不修改函数代码的情况下扩展函数功能**的设计模式。

### 基本用法

```python
import functools

def log(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        print('call %s():' % func.__name__)
        return func(*args, **kw)
    return wrapper

@log
def now():
    print('2015-3-25')

# 等价于 now = log(now)
```

### 带参数的装饰器

```python
import functools

def log(text):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            print('%s %s():' % (text, func.__name__))
            return func(*args, **kw)
        return wrapper
    return decorator

@log('execute')
def now():
    print('2015-3-25')

# 等价于 now = log('execute')(now)
```

### 类装饰器

```python
import time

class TimerDecorator:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        start = time.time()
        result = self.func(*args, **kwargs)
        print(f"耗时: {time.time() - start:.4f}秒")
        return result

@TimerDecorator
def my_task(duration):
    time.sleep(duration)
    return "完成"
```

---

## 9. 偏函数

固定函数的某些参数：

```python
>>> from functools import partial
>>> int2 = partial(int, base=2)
>>> int2('1000000')
64
>>> int2('1010101')
85
```

---

## See Also

- [[01-python-basics|Python 基础语法]] —— 函数、作用域与闭包是装饰器的前提
- [[02-python-oop|Python 面向对象]] —— `__iter__`/`__next__` 与 `__call__` 让对象参与函数式写法
- [[04-python-async|Python 异步编程]] —— 生成器让出执行权的能力，正是协程的语法源头
- [[05-python-type-hints|Python 类型提示]] —— `Iterator`、`Generator`、`Callable` 的标注方式
- [[python/index|Python 笔记目录]]
