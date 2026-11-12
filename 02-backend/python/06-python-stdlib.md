---
title: Python 内建模块
description: collections、os、sys、datetime、argparse、hashlib、json 等标准库常用模块速查
tags:
  - python
  - stdlib
  - collections
date: 2026-11-06
aliases:
  - python-stdlib
---

> 参考：[廖雪峰 - 常用内建模块](https://liaoxuefeng.com/books/python/built-in-modules/index.html)

# Python 内建模块

## 1. collections

### namedtuple

命名元组，用名字访问元素：

```python
from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])
p = Point(1, 2)
print(p.x, p.y)  # 1 2
```

### deque

双端队列，适合队列和栈：

```python
from collections import deque

q = deque(['a', 'b', 'c'])
q.append('x')
q.appendleft('y')
print(q)  # deque(['y', 'a', 'b', 'c', 'x'])
```

### defaultdict

带默认值的字典：

```python
from collections import defaultdict

dd = defaultdict(lambda: 'N/A')
dd['key1'] = 'abc'
print(dd['key1'])  # 'abc'
print(dd['key2'])  # 'N/A'
```

### OrderedDict

有序字典（Python 3.7+ 普通 dict 已有序）：

```python
from collections import OrderedDict

od = OrderedDict([('a', 1), ('b', 2), ('c', 3)])
print(od)  # OrderedDict([('a', 1), ('b', 2), ('c', 3)])
```

### Counter

计数器：

```python
from collections import Counter

c = Counter('programming')
print(c)  # Counter({'r': 2, 'g': 2, 'm': 2, ...})
c.update('hello')
```

---

## 2. os 模块

> 详细指南参见：
>
> - [[os-module-guide|Python os 模块使用指南]]（完整 os 模块指南）
> - [[os-path-guide|os.path 模块深度指南]]（os.path 专项指南）

### 路径操作（os.path）

```python
import os

# 路径拼接
os.path.join('/usr', 'local', 'bin')  # '/usr/local/bin'

# 路径分解
os.path.split('/usr/local/bin/python')  # ('/usr/local/bin', 'python')
os.path.splitext('/path/to/file.txt')   # ('/path/to/file', '.txt')

# 获取信息
os.path.dirname('/path/to/file.txt')   # '/path/to'
os.path.basename('/path/to/file.txt')  # 'file.txt'

# 检查
os.path.exists('/path/to/file')
os.path.isfile('/path/to/file')
os.path.isdir('/path/to/dir')
os.path.isabs('/path/to/file')

# 规范化
os.path.abspath('file.txt')
os.path.realpath('/path/to/link')

# 获取文件属性
os.path.getsize('/path/to/file')      # 文件大小（字节）
os.path.getmtime('/path/to/file')     # 修改时间（时间戳）
os.path.getatime('/path/to/file')     # 访问时间
os.path.getctime('/path/to/file')     # 创建时间

# 路径处理
os.path.normpath('/a/b/../c/./d')     # 规范化为 '/a/c/d'
os.path.relpath('/a/b/c', '/a/b')     # 相对路径 'c'
os.path.commonpath(['/a/b/c', '/a/b/d'])  # 公共路径 '/a/b'

# 用户目录展开
os.path.expanduser('~/Documents')     # '/home/user/Documents'
os.path.expandvars('$HOME/Documents')  # 展开环境变量

# 路径分隔符
os.path.sep      # '/' (Unix) 或 '\\' (Windows)
os.path.extsep   # '.' 扩展名分隔符
os.path.pathsep  # ':' (Unix) 或 ';' (Windows) PATH 分隔符
```

### 文件和目录操作

```python
import os

# 目录操作
os.mkdir('new_dir')
os.makedirs('a/b/c')  # 递归创建
os.rmdir('empty_dir')
os.removedirs('a/b/c')

# 文件操作
os.remove('file.txt')
os.rename('old.txt', 'new.txt')

# 遍历
for root, dirs, files in os.walk('.'):
    for file in files:
        print(os.path.join(root, file))
```

### 环境变量

```python
import os

os.environ.get('PATH')
os.environ['MY_VAR'] = 'value'
```

---

## 3. sys 模块

### 查看 Python 版本

```python
import sys

print(sys.version)           # 完整字符串，带编译信息
print(sys.version_info)      # 具名元组 (major, minor, micro, …)
```

### 其他常用

```python
import sys

sys.argv          # 命令行参数列表
sys.path          # 模块搜索路径
sys.platform      # 操作系统平台
sys.exit(0)       # 退出程序
```

---

## 4. datetime

```python
from datetime import datetime, timedelta

# 当前时间
now = datetime.now()

# 格式化
now.strftime('%Y-%m-%d %H:%M:%S')

# 解析
datetime.strptime('2024-01-01', '%Y-%m-%d')

# 时间运算
tomorrow = now + timedelta(days=1)
```

---

## 5. argparse

命令行参数解析：

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--name', type=str, default='World')
parser.add_argument('--count', type=int, default=1)
args = parser.parse_args()

print(f"Hello {args.name} " * args.count)
```

---

## 6. hashlib

哈希算法：

```python
import hashlib

md5 = hashlib.md5()
md5.update('hello'.encode('utf-8'))
print(md5.hexdigest())

sha256 = hashlib.sha256()
sha256.update('hello'.encode('utf-8'))
print(sha256.hexdigest())
```

---

## 7. base64

Base64 编解码：

```python
import base64

encoded = base64.b64encode(b'hello')
print(encoded)  # b'aGVsbG8='

decoded = base64.b64decode(encoded)
print(decoded)  # b'hello'
```

---

## 8. json

JSON 处理：

```python
import json

# 序列化
json_str = json.dumps({'name': 'Alice', 'age': 30})
json_bytes = json.dumps({'name': 'Alice'}, ensure_ascii=False).encode('utf-8')

# 反序列化
obj = json.loads('{"name": "Alice", "age": 30}')

# 文件操作
with open('data.json', 'w') as f:
    json.dump(obj, f)

with open('data.json', 'r') as f:
    obj = json.load(f)
```

---

## 9. platform

系统信息：

```python
import platform

print(platform.python_version())        # '3.11.2'
print(platform.python_version_tuple())  # ('3', '11', '2')
print(platform.system())                # 'Darwin', 'Linux', 'Windows'
print(platform.machine())               # 'x86_64', 'arm64'
```
