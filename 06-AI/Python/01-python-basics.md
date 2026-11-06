---
title: Python 基础语法
description: Python 的数据类型、内置容器（list/dict/set/tuple）、函数与控制流核心语法
tags:
  - python
  - fundamentals
  - data-structures
date: 2026-11-06
aliases:
  - python-basics
---

> 参考：[廖雪峰 Python 教程](https://liaoxuefeng.com/books/python/introduction/index.html)

# Python 基础语法

## 1. 数据类型和变量

### 基本数据类型

- 整数 (`int`)
- 浮点数 (`float`)
- 字符串 (`str`)
- 布尔值 (`bool`)

### 布尔运算

```python
and  # 与
or   # 或
not  # 非
```

### 空值

```python
None
```

### 字符编码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```

---

## 2. 数据结构

### list（列表）

```python
>>> classmates = ['Michael', 'Bob', 'Tracy']
>>> classmates
['Michael', 'Bob', 'Tracy']
>>> len(classmates)
3
>>> classmates[0]
'Michael'
>>> classmates.append('Adam')
>>> classmates.insert(1, 'Jack')
>>> classmates.pop()
'Adam'
```

### tuple（元组）

一旦初始化就不能修改：

```python
>>> classmates = ('Michael', 'Bob', 'Tracy')
```

### dict（字典）

```python
>>> d = {'Michael': 95, 'Bob': 75, 'Tracy': 85}
>>> d['Michael']
95
>>> 'Thomas' in d
False
>>> d.get('Thomas', -1)
-1
>>> d.pop('Bob')
75
```


字典是 Python 中最重要的数据结构之一，它是键值对（Key-Value）的无序集合（Python 3.7+ 中保持插入顺序）。

#### 1. 创建字典的多种方式

除了使用 `{}` 或 `dict()` 构造函数，还可以使用推导式和 `fromkeys`。

```python
# 方式 1: 直接定义
d1 = {'a': 1, 'b': 2}

# 方式 2: 使用 dict() 构造函数
d2 = dict(a=1, b=2) 
d3 = dict([('a', 1), ('b', 2)]) # 从键值对列表创建

# 方式 3: 字典推导式 (Dictionary Comprehension)
# 类似列表生成式，语法为 {key_expr: value_expr for item in iterable}
d4 = {x: x**2 for x in range(3)} 
# 结果: {0: 0, 1: 1, 2: 4}

# 方式 4: fromkeys (创建所有键具有相同默认值的字典)
d5 = dict.fromkeys(['a', 'b', 'c'], 0)
# 结果: {'a': 0, 'b': 0, 'c': 0}
```

#### 2. 安全访问与修改

直接使用 `d[key]` 访问不存在的键会抛出 `KeyError`，推荐使用更安全的方法。

```python
d = {'Michael': 95, 'Bob': 75}

# 1. get(key, default): 获取值，若键不存在返回默认值 (默认为 None)
val = d.get('Thomas', -1)  # 返回 -1，不会报错

# 2. setdefault(key, default): 
# 若键存在，返回其值；若键不存在，插入该键并设为默认值，然后返回默认值
d.setdefault('Tracy', 85)  # 如果 'Tracy' 不在 d 中，则添加 {'Tracy': 85}

# 3. pop(key, default): 
# 删除键并返回对应的值。若键不存在且提供了 default，则返回 default，否则报错
removed_val = d.pop('Bob', None) 
```

#### 3. 遍历字典

Python 提供了多种遍历字典的方式，效率略有不同。

```python
d = {'a': 1, 'b': 2, 'c': 3}

# 1. 遍历键 (默认行为)
for k in d:
    print(k, d[k])

# 2. 遍历键值对 (推荐，效率最高)
for k, v in d.items():
    print(k, v)

# 3. 仅遍历值
for v in d.values():
    print(v)
```

#### 4. 字典合并 (Python 3.5+)

合并两个字典有多种方法，注意后者的键会覆盖前者相同的键。

```python
d1 = {'a': 1, 'b': 2}
d2 = {'b': 3, 'c': 4}

# 方法 1: update() 方法 (原地修改 d1)
d1.update(d2) 
# d1 变为: {'a': 1, 'b': 3, 'c': 4}

# 方法 2: ** 解包操作符 (Python 3.5+, 创建新字典)
d3 = {**d1, **d2}

# 方法 3: | 运算符 (Python 3.9+, 创建新字典)
d4 = d1 | d2
```

#### 5. 其他常用操作

```python
d = {'a': 1, 'b': 2, 'c': 3}

# 获取所有键/值/键值对视图 (动态视图，随字典变化而变化)
keys = d.keys()   
values = d.values() 
items = d.items() 

# 复制字典 (浅拷贝)
d_copy = d.copy()

# 清空字典
d.clear()

# 检查键是否存在 (推荐方式)
if 'a' in d:
    pass
# 或者
if 'a' in d.keys():
    pass
```

#### 6. 注意事项

- **键的唯一性**：字典的键必须是唯一的。如果重复赋值，后面的值会覆盖前面的值。
- **键的不可变性**：键必须是不可变类型（如字符串、数字、tuple），不能是 list 或 dict。
- **有序性**：在 Python 3.7 及以上版本中，字典默认保持**插入顺序**。在早期版本中是无序的。

---

### set（集合）

```python
>>> s = {1, 2, 3}
>>> s.add(4)
>>> s.remove(4)
>>> s1 = {1, 2, 3}
>>> s2 = {2, 3, 4}
>>> s1 & s2
{2, 3}
>>> s1 | s2
{1, 2, 3, 4}
```

集合（`set`）是一个**无序**、**不重复**的元素序列。它主要用于去重和进行数学上的集合运算（交集、并集、差集等）。

#### 1. 创建集合

注意：创建空集合必须使用 `set()`，因为 `{}` 会被识别为空字典。

```python
# 方式 1: 直接定义 (非空)
s1 = {1, 2, 3, 2} 
# 结果: {1, 2, 3} (自动去重)

# 方式 2: 创建空集合 (重要!)
s2 = set() 
# 错误写法: s = {} -> 这是一个 dict

# 方式 3: 从列表或其他可迭代对象创建 (常用于去重)
lst = [1, 2, 2, 3, 4]
s3 = set(lst) 
# 结果: {1, 2, 3, 4}

# 方式 4: 集合推导式
s4 = {x for x in 'abracadabra' if x not in 'abc'}
# 结果: {'r', 'd'}
```

#### 2. 基本操作 (增删改查)

由于集合无序，不支持索引访问（如 `s[0]` 会报错）。

```python
s = {1, 2, 3}

# 1. 添加元素
s.add(4)        # 添加单个元素
s.update([5, 6]) # 批量添加，参数可以是任何可迭代对象

# 2. 删除元素
s.remove(3)     # 删除指定元素，若不存在则抛出 KeyError
s.discard(3)    # 删除指定元素，若不存在则**不报错** (推荐)
s.pop()         # 随机删除并返回一个元素 (因为无序，不知道删的是谁)
s.clear()       # 清空集合

# 3. 判断存在性 (效率极高，O(1))
if 2 in s:
    print("Exists")
```

#### 3. 集合运算 (数学逻辑)

集合最强大的功能在于数学运算，有两种写法：方法调用和运算符。

```python
s1 = {1, 2, 3, 4}
s2 = {3, 4, 5, 6}

# 1. 交集 (Intersection): 两个集合都有的元素
# 结果: {3, 4}
res_inter = s1 & s2 
# 或: s1.intersection(s2)

# 2. 并集 (Union): 两个集合所有的元素 (去重)
# 结果: {1, 2, 3, 4, 5, 6}
res_union = s1 | s2 
# 或: s1.union(s2)

# 3. 差集 (Difference): 在 s1 中但不在 s2 中的元素
# 结果: {1, 2}
res_diff = s1 - s2 
# 或: s1.difference(s2)

# 4. 对称差集 (Symmetric Difference): 在 s1 或 s2 中，但不同时存在的元素
# 结果: {1, 2, 5, 6}
res_sym = s1 ^ s2 
# 或: s1.symmetric_difference(s2)

# 5. 子集/超集判断
s3 = {1, 2}
s3 < s1       # True (s3 是 s1 的子集)
s1 > s3       # True (s1 是 s3 的超集)
s3 <= s1      # True (子集或相等)
```

#### 4. 冻结集合 (frozenset)

标准 `set` 是可变的（mutable），因此不能作为字典的键或另一个集合的元素。如果需要不可变的集合，使用 `frozenset`。

```python
fs = frozenset([1, 2, 3])
# fs.add(4)  # 报错: AttributeError

# 应用场景: 作为字典的键
d = {fs: "value"} 
```

#### 5. 实用技巧：列表去重

这是 `set` 最常见的应用场景之一。

```python
data = ['apple', 'banana', 'apple', 'orange', 'banana']
unique_data = list(set(data))
# 结果: ['apple', 'banana', 'orange'] (顺序可能改变)

# 如果需要保持原顺序去重 (Python 3.7+ dict 保持顺序)
unique_ordered = list(dict.fromkeys(data))
# 结果: ['apple', 'banana', 'orange'] (保持原序)
```

#### 6. 注意事项

- **无序性**：集合中的元素没有顺序，每次打印或遍历的顺序可能不同（虽然 Python 3.7+ 的哈希实现让它在某些情况下看起来有序，但逻辑上不应依赖顺序）。
- **元素要求**：集合中的元素必须是**可哈希的**（hashable），即不可变类型（如数字、字符串、tuple）。不能包含 list 或 dict。
- **性能**：对于大规模数据的存在性检查（`x in s`），`set` 的速度远快于 `list`，因为 `set` 的查找复杂度是 $O(1)$，而 `list` 是 $O(n)$。

---

## 3. 函数

### 参数类型

在 Python 中定义函数，可以用**必选参数、默认参数、可变参数、关键字参数和命名关键字参数**，这5种参数都可以组合使用。

参数定义的顺序必须是：**必选参数 → 默认参数 → 可变参数 → 命名关键字参数 → 关键字参数**

```python
def func(a, b, c=0, *args, **kw):
    print('a =', a, 'b =', b, 'c =', c, 'args =', args, 'kw =', kw)
```

### Lambda 函数

> 参考：[How to Use Python Lambda Functions](https://realpython.com/python-lambda/)

```python
>>> f = lambda x: x * x
>>> f(5)
25
```

---

## 4. 控制流

### 条件判断

```python
if x > 0:
    print('positive')
elif x == 0:
    print('zero')
else:
    print('negative')
```

### 循环

```python
for i in range(5):
    print(i)

while n > 0:
    n -= 1
```

### 列表生成式

```python
>>> [x * x for x in range(1, 11)]
[1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

>>> [x * x for x in range(1, 11) if x % 2 == 0]
[4, 16, 36, 64, 100]
```

---

## See Also

- [[02-python-oop|Python 面向对象]] —— 用类组织数据与行为
- [[03-python-functional|Python 函数式编程]] —— 上面最后一段的列表生成式在这里展开
- [[05-python-type-hints|Python 类型提示]] —— 给基础语法加上类型标注
- [[13-python-exceptions|Python 异常处理]] —— 本文只提到 `try/except` 的语法形式，
  异常链、`ExceptionGroup` 与自定义异常体系在那一篇展开
- [[06-python-stdlib|Python 内建模块]] —— `collections` 对内置容器的增强
- [[04-python-async|Python 异步编程]] —— 函数定义 `async def` 的延伸
- [[06-AI/python/index|Python 笔记目录]]