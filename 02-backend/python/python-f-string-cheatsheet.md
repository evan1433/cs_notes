---
title: Python f-String Cheat Sheet
description: f-string 的插值、格式说明符、对齐与调试写法速查，含训练日志常用格式
tags:
  - python
  - f-string
  - string-formatting
date: 2026-11-06
aliases:
  - Python f-String Cheat Sheet
  - python-f-string-cheat-sheet
---

# Python f-String Cheat Sheet

## 1. Basic Variable Interpolation

```python
name = "Alice"
age = 25

print(f"Hello {name}")
print(f"Age: {age}")
```

Output:

```text
Hello Alice
Age: 25
```

---

## 2. Expressions

```python
x = 10
y = 5

print(f"{x} + {y} = {x + y}")
print(f"{x} * {y} = {x * y}")
```

Output:

```text
10 + 5 = 15
10 * 5 = 50
```

---

## 3. Debugging Syntax (Python 3.8+)

Very useful for logging and debugging.

```python
name = "Alice"
score = 95

print(f"{name=}")
print(f"{score=}")
```

Output:

```text
name='Alice'
score=95
```

You can even use expressions:

```python
x = 10
y = 20

print(f"{x+y=}")
```

Output:

```text
x+y=30
```

---

# Number Formatting

## 4. Decimal Places

```python
pi = 3.1415926535

print(f"{pi:.2f}")
print(f"{pi:.4f}")
```

Output:

```text
3.14
3.1416
```

---

## 5. Percentage

```python
rate = 0.8765

print(f"{rate:.2%}")
```

Output:

```text
87.65%
```

---

## 6. Thousands Separator

```python
num = 1234567890

print(f"{num:,}")
```

Output:

```text
1,234,567,890
```

---

## 7. Scientific Notation

```python
num = 1234567

print(f"{num:e}")
print(f"{num:.2e}")
```

Output:

```text
1.234567e+06
1.23e+06
```

---

## 8. Binary / Octal / Hex

```python
num = 255

print(f"{num:b}")   # binary
print(f"{num:o}")   # octal
print(f"{num:x}")   # hex lowercase
print(f"{num:X}")   # hex uppercase
```

Output:

```text
11111111
377
ff
FF
```

---

# Width & Alignment

## 9. Minimum Width

```python
num = 42

print(f"|{num:5}|")
```

Output:

```text
|   42|
```

---

## 10. Left / Right / Center Alignment

```python
text = "cat"

print(f"|{text:<10}|")   # left
print(f"|{text:>10}|")   # right
print(f"|{text:^10}|")   # center
```

Output:

```text
|cat       |
|       cat|
|   cat    |
```

---

## 11. Fill Characters

```python
text = "cat"

print(f"|{text:*^10}|")
print(f"|{text:-<10}|")
```

Output:

```text
|***cat****|
|cat-------|
```

---

## 12. Zero Padding

```python
num = 42

print(f"{num:05}")
```

Output:

```text
00042
```

---

# String Formatting

## 13. Truncate Strings

```python
text = "HelloWorld"

print(f"{text:.5}")
```

Output:

```text
Hello
```

---

## 14. Width + Truncation

```python
text = "HelloWorld"

print(f"|{text:10.5}|")
```

Output:

```text
|Hello     |
```

---

# Date & Time Formatting

```python
from datetime import datetime

now = datetime.now()

print(f"{now:%Y-%m-%d}")
print(f"{now:%H:%M:%S}")
print(f"{now:%Y-%m-%d %H:%M:%S}")
```

Example Output:

```text
2026-06-02
14:30:15
2026-06-02 14:30:15
```

Common date codes:

|Code|Meaning|
|---|---|
|`%Y`|4-digit year|
|`%m`|month|
|`%d`|day|
|`%H`|hour (24h)|
|`%M`|minute|
|`%S`|second|

---

# Dictionary and Object Access

## Dictionary

```python
user = {
    "name": "Alice",
    "age": 25
}

print(f"{user['name']} ({user['age']})")
```

Output:

```text
Alice (25)
```

---

## Object Attributes

```python
class User:
    def __init__(self):
        self.name = "Alice"

u = User()

print(f"{u.name}")
```

Output:

```text
Alice
```

---

# Escaping Braces

```python
print(f"{{Hello}}")
```

Output:

```text
{Hello}
```

---

# Common Real-World Examples

## Logging

```python
epoch = 10
loss = 0.012345

print(f"epoch={epoch}, loss={loss:.4f}")
```

Output:

```text
epoch=10, loss=0.0123
```

---

## File Names

```python
epoch = 5

filename = f"checkpoint_epoch_{epoch:03d}.pt"

print(filename)
```

Output:

```text
checkpoint_epoch_005.pt
```

---

## Training Metrics

```python
step = 1200
loss = 1.23456
lr = 5e-5

print(
    f"step={step:,}, "
    f"loss={loss:.4f}, "
    f"lr={lr:.2e}"
)
```

Output:

```text
step=1,200, loss=1.2346, lr=5.00e-05
```

---

# Most Useful Formats for ML/LLM Engineers

```python
f"{loss:.4f}"          # 1.2345
f"{accuracy:.2%}"      # 95.23%
f"{step:,}"            # 100,000
f"{lr:.2e}"            # 5.00e-05
f"{epoch:03d}"         # 001
f"{gpu_mem:.1f} GB"    # 23.5 GB
f"{name=}"             # name='llama'
f"{batch_size=}"       # batch_size=128
```

These are the formats you'll use most often when working with PyTorch, TRL, DeepSpeed, Accelerate, and LLM training logs.

---

## See Also

- [[logging-module-guide|logging 模块使用指南]] —— 日志里的指标格式大多靠 `:.4f`、`:.2%` 这类说明符
- [[01-python-basics|Python 基础语法]] —— 字符串基础与常用字符串方法
- [[06-python-stdlib|Python 内建模块]] —— `datetime` 的时间格式化与 f-string 的配合
- [[python/index|Python 笔记目录]]