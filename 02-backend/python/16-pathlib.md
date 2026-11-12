---
title: pathlib 路径操作
description: Path 对象语义、路径拼接与变形、文件读写、glob 与 walk 遍历、与 os.path 的完整对照表及常见陷阱
tags:
  - python
  - pathlib
  - file-system
  - stdlib
date: 2026-11-06
aliases:
  - python-pathlib
  - python-path
---

# pathlib 路径操作

> **版本基线**：`Path.walk` / `is_junction` 3.12；`glob(case_sensitive=)` 3.12；
> `glob(recurse_symlinks=)` 3.13；`Path.copy` / `move` / `info` 3.14。
> 示例在本机 CPython 3.13 实跑验证。

## 1. 为什么不该再用字符串拼路径

同一个需求，两种写法：

```python
import os

# 字符串方案：分隔符、空段、类型混用全靠约定
base = "/data/exports"
path = os.path.join(base, "2026", "11") + "/" + "orders.csv"
parent = os.path.dirname(os.path.dirname(path))
size = os.path.getsize(path)
```

```python
from pathlib import Path

base = Path("/data/exports")
path = base / "2026" / "11" / "orders.csv"
parent = path.parent.parent
size = path.stat().st_size
```

差别不只是"短一点"：

| 问题 | 字符串方案 | Path 方案 |
|------|-----------|-----------|
| 分隔符 | 手写 `/` 或 `os.sep`，Windows 上易出错 | `/` 运算符自动用当前平台分隔符 |
| 中间路径可能不存在 | 无法表达"这只是个路径" | 纯运算与 I/O 分离，运算不碰磁盘 |
| 参数传递 | 只能传 `str`，或到处 `str(path)` | 实现 `os.PathLike`，可直接传给 `open`/`shutil` |
| 语义 | `path + ".bak"` 与 `path.with_suffix(".bak")` 结果不同 | 有明确 API 表达"改名"还是"加后缀" |
| 可读性 | `os.path.dirname(os.path.dirname(p))` | `p.parent.parent` |

最关键的是**Path 是不可变对象**：所有变形操作返回新对象，不存在"改了一半"的状态，
也不会出现"函数内部把调用方的路径变量改掉"这类问题。

## 2. PurePath 与 Path 的分工

pathlib 的类分两层：

| 类 | 是否访问文件系统 | 用途 |
|----|------------------|------|
| `PurePath` | 否 | 纯路径计算；测试、生成配置、拼 URL 路径 |
| `PurePosixPath` / `PureWindowsPath` | 否 | 在任意平台上处理**指定风格**的路径 |
| `Path` | 是 | 日常使用，自动选当前平台的具体实现 |
| `PosixPath` / `WindowsPath` | 是 | 平台实现，一般不直接实例化 |

```python
from pathlib import PurePosixPath, PureWindowsPath

# 在 macOS/Linux 上处理 Windows 路径（例如解析远端日志里的路径）
win = PureWindowsPath(r"C:\Users\duke\notes\a.md")
print(win.parts)      # ('C:\\', 'Users', 'duke', 'notes', 'a.md')
print(win.drive)      # C:
print(win.name)       # a.md

posix = PurePosixPath("/var/log/app.log")
print(posix.parts)    # ('/', 'var', 'log', 'app.log')
```

`Path` 只能实例化当前平台的实现：

```pycon
>>> from pathlib import Path, WindowsPath
>>> WindowsPath("C:/x")          # 在 Linux/macOS 上
NotImplementedError: cannot instantiate 'WindowsPath' on your system
```

> 需要写"跨平台都能跑"的单元测试时，用 `PurePath` 家族，不要在测试里碰真实文件系统。

## 3. 路径的组成与变形

### 3.1 分解路径

```python
p = PurePosixPath("/var/log/app/error.log")

print(p.parts)        # ('/', 'var', 'log', 'app', 'error.log')
print(p.name)         # error.log
print(p.stem)         # error
print(p.suffix)       # .log
print(p.parent)       # /var/log/app
print(list(p.parents)[:3])   # [/var/log/app, /var/log, /var]
```

多后缀文件的 `suffix` 只取最后一段，`suffixes` 返回全部：

```python
f = Path("report.tar.gz")
print(f.suffix)          # .gz
print(f.suffixes)        # ['.tar', '.gz']
print(f.with_suffix(".zip"))    # report.tar.zip  <- 只替换最后一段
print(f.with_stem("final"))     # final.gz
print(f.with_name("summary.md"))  # summary.md
```

`with_suffix` 的行为常被误解：它不是"换扩展名"，而是"**替换最后一个后缀**"。
要把 `report.tar.gz` 变成 `report.zip`，应该写 `f.with_suffix("").with_suffix(".zip")`。

### 3.2 拼接：`/` 运算符

```python
base = Path("data")
print(base / "2026" / "11" / "orders.csv")   # data/2026/11/orders.csv
print("data" / Path("x.txt"))                # data/x.txt，字符串在左也可以
print(base.joinpath("a", "b", "c"))           # 一次拼多段
```

**绝对路径会重置整条路径**，与 `os.path.join` 一致：

```python
print(Path("/etc") / "/usr/bin")     # /usr/bin
```

这是安全漏洞的常见来源：用户传入 `"/etc/passwd"`，`base / user_input` 直接跳出沙箱目录。
拼接不可信输入前必须先校验：

```python
def safe_join(base: Path, user_part: str) -> Path:
    candidate = (base / user_part).resolve()
    if not candidate.is_relative_to(base.resolve()):
        raise ValueError(f"路径越界: {user_part}")
    return candidate
```

> 这段校验依赖 3.9+ 的 `is_relative_to`。注意 `resolve()` 会解析符号链接，
> 因此也能挡住"软链接指向沙箱外"的绕过方式。

## 4. 读写文件

### 4.1 一次性读写

```python
from pathlib import Path

target = Path("data/orders.csv")
target.write_text("id,amount\n1,99\n", encoding="utf-8")
text = target.read_text(encoding="utf-8")

blob = target.read_bytes()
target.write_bytes(b"raw")
```

**`encoding` 必须显式传**。`read_text()` / `write_text()` 的默认值是 `None`，
等同于使用 `locale.getpreferredencoding(False)`：

| 平台 | 典型默认编码 | 后果 |
|------|--------------|------|
| Linux（UTF-8 locale） | utf-8 | 正常 |
| macOS | utf-8 | 正常 |
| Windows 中文版 | cp936（GBK） | 写出的文件在 Linux 上读是乱码 |

本机实测 `locale.getpreferredencoding(False)` 为 `utf-8`，所以**在本机测不出这个问题**——
换到 Windows CI 才会暴露。这是"必须显式传 encoding"最实际的理由。

### 4.2 需要流式或控制换行时用 open

```python
with target.open("r", encoding="utf-8", newline="") as fh:
    for line in fh:
        process(line)
```

`Path.open()` 等价于内置 `open()`。`read_text` / `write_text` 的 `newline` 参数倒是新加的：
`write_text` 3.10 起支持，`read_text` 3.13 起支持。需要保留原始 `\r\n` 时用得上：

```python
data = Path("crlf.txt").read_text(encoding="utf-8", newline="")
print(repr(data))     # 'a\r\nb\r\n'，未做换行转换
```

### 4.3 大文件不要 read_text

`read_text()` 会把整个文件读进内存。日志、模型权重、CSV 导出这类文件必须流式处理，
用 `open()` 逐行读，或用 `shutil.copyfileobj` 搬运。

## 5. 目录遍历

### 5.1 三种遍历方式

```python
root = Path("data")

# 只看一层
for child in root.iterdir():
    print(child.name, child.is_dir())

# 按模式匹配（不递归）
for csv in root.glob("*.csv"):
    print(csv)

# 递归匹配
for csv in root.rglob("*.csv"):
    print(csv)

# 等价写法，可读性稍差
for csv in root.glob("**/*.csv"):
    print(csv)
```

实测结果（`data/` 下有 `a.txt`、`b.log`、`.hidden.txt`、`2026/c.txt`）：

```text
glob('*.txt')       -> ['data/a.txt', 'data/.hidden.txt']
rglob('*.txt')      -> ['data/2026/c.txt', 'data/a.txt', 'data/.hidden.txt']
glob('**/*.txt')    -> 同上
```

注意 `pathlib` 的 `glob` **会匹配点开头的隐藏文件**，这与传统 `glob.glob()` 不同
（后者默认跳过 `.` 开头）。从 `glob` 模块迁移过来时这点容易造成行为变化。

### 5.2 Path.walk（3.12+）

```python
for dirpath, dirnames, filenames in root.walk():
    print(dirpath, sorted(dirnames), sorted(filenames))
```

```text
data          ['2026']  ['a.txt', 'b.log', '.hidden.txt']
data/2026     ['11']    ['c.txt']
data/2026/11  []        ['orders.csv']
```

与 `os.walk` 的差别：**`follow_symlinks=False`（默认）时，指向目录的符号链接会被放进
`filenames`**，而不是 `dirnames`。这是官方文档明确指出的差异，写清理脚本时会导致
"软链接目录没被递归"或"被误当成文件删除"。

### 5.3 glob 的两个新参数

| 参数 | 版本 | 作用 |
|------|------|------|
| `case_sensitive` | 3.12 | 显式指定大小写敏感；默认按平台规则（POSIX 敏感、Windows 不敏感） |
| `recurse_symlinks` | 3.13 | 是否跟随符号链接展开 `**`；默认 False |

```python
for p in root.glob("*.CSV", case_sensitive=False):
    print(p)
```

跨平台脚本里显式写 `case_sensitive=False`，可以避免"在 macOS 上跑得好、部署到 Linux 找不到文件"。
（macOS 默认文件系统大小写不敏感，Linux 敏感，这是典型的本地通过、线上失败。）

## 6. 路径解析与比较

### 6.1 resolve / absolute / expanduser

```python
rel = Path("data/../data/a.txt")
print(rel)                 # data/../data/a.txt，Path 不会自动折叠 ..
print(rel.resolve())       # /private/tmp/b3/plab/data/a.txt
print(Path("~/logs").expanduser())   # /Users/duke/logs
```

| 方法 | 是否访问文件系统 | 是否解析符号链接 | 是否折叠 `..` | 结果 |
|------|------------------|------------------|---------------|------|
| `resolve()` | 是（可 `strict=True` 强制存在） | 是 | 是 | 绝对路径 |
| `absolute()`（3.11+） | 否 | 否 | 否 | 绝对路径，可能含 `..` |
| `os.path.abspath()` | 否 | 否 | 是（纯字符串） | 绝对路径 |

`resolve()` 默认 `strict=False`：文件不存在也返回一个"看起来合理"的绝对路径。
这掩盖拼写错误，排查时容易误判——需要确认真实存在就用 `resolve(strict=True)`：

```python
try:
    Path("data/nope.txt").resolve(strict=True)
except FileNotFoundError as e:
    print("不存在")        # 走这里
```

### 6.2 相对路径计算

```python
target = Path("data/2026/11/orders.csv")
root = Path("data")

print(target.relative_to(root))        # 2026/11/orders.csv
print(target.is_relative_to(root))     # True
```

`relative_to` 在"不在其下"时抛 `ValueError`，`is_relative_to` 返回布尔值。
两者都是**纯字符串判断**，不访问文件系统、不特殊处理 `..`：

```pycon
>>> Path("/etc/passwd").relative_to(Path("data"))
ValueError: '/etc/passwd' is not in the subpath of 'data'
```

### 6.3 相等比较的边界

`Path` 的 `==` 会在构造时做轻量归一化（去掉 `.`、合并重复分隔符），但**不访问文件系统**：

```python
p1 = Path("data/a.txt")
p2 = Path("./data//a.txt")
print(p1 == p2)          # True，归一化后一致

p3 = Path("DATA/A.TXT")
print(p1 == p3)          # False（大小写敏感比较）
print(p1.samefile(p3))   # True（macOS 默认文件系统大小写不敏感）
```

所以：**判断"是不是同一个文件"用 `samefile()`，不要用 `==`**。反过来，
判断"配置里的路径字符串是否与预期一致"才该用 `==`。

## 7. 与 os.path 的完整对照

| 需求 | os.path / os | pathlib |
|------|--------------|---------|
| 拼接 | `os.path.join(a, b)` | `a / b`、`a.joinpath(b)` |
| 取目录 | `os.path.dirname(p)` | `p.parent` |
| 取文件名 | `os.path.basename(p)` | `p.name` |
| 去扩展名 | `os.path.splitext(p)[0]` | `p.stem` |
| 取扩展名 | `os.path.splitext(p)[1]` | `p.suffix` |
| 绝对化 | `os.path.abspath(p)` | `p.resolve()` / `p.absolute()` |
| 展开 `~` | `os.path.expanduser(p)` | `p.expanduser()` |
| 是否存在 | `os.path.exists(p)` | `p.exists()` |
| 是文件 / 目录 | `os.path.isfile/isdir(p)` | `p.is_file()` / `p.is_dir()` |
| 是符号链接 | `os.path.islink(p)` | `p.is_symlink()` |
| 文件大小 | `os.path.getsize(p)` | `p.stat().st_size` |
| 修改时间 | `os.path.getmtime(p)` | `p.stat().st_mtime` |
| 列出目录 | `os.listdir(p)` | `p.iterdir()` |
| 递归遍历 | `os.walk(p)` | `p.walk()`（3.12+）/ `p.rglob("*")` |
| 创建目录 | `os.makedirs(p, exist_ok=True)` | `p.mkdir(parents=True, exist_ok=True)` |
| 删除文件 | `os.remove(p)` | `p.unlink(missing_ok=True)`（3.8+） |
| 删除空目录 | `os.rmdir(p)` | `p.rmdir()` |
| 重命名 / 移动 | `os.replace(src, dst)` | `p.replace(dst)`；3.14 起 `p.move(dst)` |
| 复制 | `shutil.copy2(src, dst)` | `shutil.copy2(src, dst)`；3.14 起 `src.copy(dst)` |
| 硬链接 | `os.link(src, dst)` | `dst.hardlink_to(src)`（3.10+，参数顺序相反） |
| 软链接 | `os.symlink(src, dst)` | `dst.symlink_to(src)`（参数顺序相反） |
| 规范化 | `os.path.normpath(p)` | `PurePath(p)` 构造即归一化 |
| 相对路径 | `os.path.relpath(p, start)` | `p.relative_to(start)` |
| 取当前目录 | `os.getcwd()` | `Path.cwd()` |
| 取 home | `os.path.expanduser("~")` | `Path.home()` |

记忆规律：**`os.path` 是"函数操作字符串"，pathlib 是"方法操作对象"**。
`relative_to` 与 `os.path.relpath` 有一个重要区别：前者要求目标确实在基准之下（否则抛错），
后者会返回带 `../` 的相对路径。

## 8. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| `with_suffix(".zip")` 能改掉 `.tar.gz` | 只替换最后一个后缀，得 `report.tar.zip` | `f.with_suffix("").with_suffix(".zip")` |
| `Path("~/logs")` 会自动展开 | 不会，`~` 只是一个普通目录名 | 显式 `.expanduser()` |
| 不传 `encoding` 也没问题 | 默认用 locale 编码，Windows 中文版是 GBK | 一律显式 `encoding="utf-8"` |
| `glob("*.txt")` 只返回普通文件 | 也会匹配 `.hidden.txt`，与传统 `glob` 模块不同 | 需要过滤时显式检查 `p.name.startswith(".")` |
| 用 `==` 判断是否同一文件 | `==` 不访问文件系统，大小写与软链接都不同 | 用 `samefile()` |
| `base / user_input` 是安全的 | 绝对路径会重置整条路径，可越界读文件 | 拼接后 `resolve()` + `is_relative_to()` 校验 |
| `resolve()` 能验证路径存在 | 默认 `strict=False`，不存在也返回 | 需要校验时 `resolve(strict=True)` |
| `Path` 可以"修改" | Path 不可变，所有变形都返回新对象 | 用返回值，别指望原地生效 |
| 用 `read_text()` 读大文件 | 一次性读入内存 | 用 `open()` 流式读 |
| `p.walk()` 与 `os.walk()` 行为完全一致 | 默认不跟随符号链接，且把目录软链接归入 `filenames` | 需要跟随时显式 `follow_symlinks=True` |

## 9. 与相关概念的关系

- **与 [[os-path-guide|os.path 模块深度指南]]**：旧式写法仍是大量存量代码的基础，
  两者需要能互相翻译；本文第 7 节就是对照表。新代码优先 pathlib。
- **与 [[14-context-managers|Python 上下文管理器]]**：`Path.read_text()` 内部已完成
  打开与关闭，不需要再套 `with`；只有 `Path.open()` 需要。
- **与 [[os-module-guide|os 模块使用指南]]**：文件权限、环境变量、进程操作仍在 `os` 里，
  pathlib 只覆盖路径与基础 I/O。
- **与 [[17-pytest|pytest 测试]]**：`tmp_path` fixture 直接返回 `Path` 对象，
  测试中的临时文件读写可以完全用 pathlib 表达。

## 参考

- [pathlib — Object-oriented filesystem paths](https://docs.python.org/3/library/pathlib.html)
- [os.path — Common pathname manipulations](https://docs.python.org/3/library/os.path.html)
- [PEP 428 – The pathlib module](https://peps.python.org/pep-0428/)
- [[06-python-stdlib|Python 内建模块]]
