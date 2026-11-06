---
title: Python 命令行工具：-c、-m 与 CLI 入口
description: 四种调用方式的 sys.path 与 __main__ 差异、-m 的导入语义与双执行陷阱、常用解释器开关、argparse CLI 骨架、退出码约定与 console_scripts 分发
tags:
  - python
  - cli
  - argparse
  - stdlib
date: 2026-11-06
aliases:
  - python-cli
  - python-argparse
---

# Python 命令行工具：-c、-m 与 CLI 入口

> **版本基线**：`-P` / `PYTHONSAFEPATH` 3.11；`-X int_max_str_digits` 3.11；
> `-X pycache_prefix` 3.8；`-X dev` 3.7。本文示例在 CPython 3.13.12 实跑验证，
> 文中所有"实测"标注的数字与输出均为本机真实运行结果。

## 1. 四种把代码交给解释器的方式

同一个 `hello`，有四种送进去的办法，它们**不是**等价的：

```bash
python script.py            # 跑一个文件
python -m script            # 把一个模块当程序跑（不要写 .py）
python -c "print('hi')"     # 跑一段字符串
cat script.py | python -    # 从标准输入读代码
```

差别在于解释器怎么设置三个东西：`sys.path[0]`（模块搜索路径的第一项）、
`sys.argv[0]`（程序名）、`__package__`（相对导入的锚点）。

用同一段探针把四种方式都跑一遍：

```python
# probe.py
import sys
print("sys.path[0] =", repr(sys.path[0]))
print("argv[0]     =", repr(sys.argv[0]))
print("__name__    =", repr(__name__))
print("__package__ =", repr(__package__))
```

实测结果（目录 `/tmp/cli-probe`，`pkg/` 是含 `__init__.py` 与 `__main__.py` 的包）：

| 调用方式 | `sys.path[0]` | `sys.argv[0]` | `__package__` |
|----------|---------------|---------------|---------------|
| `python probe.py` | 脚本所在目录 | `'probe.py'` | `None` |
| `python -m probe` | 当前工作目录 | 模块文件的绝对路径 | `''` |
| `python -m pkg` | 当前工作目录 | `.../pkg/__main__.py` | `'pkg'` |
| `python -c "..."` | `''`（即 cwd） | `'-c'` | `None` |
| `python -` | `''`（即 cwd） | `'-'` | `None` |

`__name__` 在所有情况下都是 `'__main__'`——这就是为什么入口判断永远写成
`if __name__ == "__main__":`，而不是去比较 `sys.argv[0]`。

两条容易被忽略的结论：

- **`python script.py` 会把脚本所在目录塞进 `sys.path[0]`**，于是脚本目录里的
  `json.py`、`random.py` 会**遮蔽**标准库同名模块。这是"我明明装了 requests 却报
  `ImportError: cannot import name`"的经典来源。
- **`python -m` 的第一项是当前工作目录，不是模块所在的目录**。所以 `-m` 能不能找到
  你的包，取决于你站在哪个目录下敲命令。

## 2. `-m` 到底做了什么

`-m` 不是"运行一个文件"，而是**先按模块导入，再执行**。这带来三个可观察的后果。

### 2.1 包靠 `__main__.py` 提供入口

`python -m pkg` 执行的是 `pkg/__main__.py`，不是 `pkg/__init__.py`：

```python
# pkg/__main__.py
import sys

print("[__main__.py] argv[0]     =", repr(sys.argv[0]))
print("[__main__.py] __package__ =", repr(__package__))
```

```bash
$ python -m pkg
[__main__.py] argv[0]     = '/tmp/cli-probe/pkg/__main__.py'
[__main__.py] __package__ = 'pkg'
```

`__package__` 是 `'pkg'` 而不是 `None`，所以 `__main__.py` 里可以写相对导入
`from . import helper`。换个方式直接跑文件就会崩：

```bash
$ python pkg/sub.py
ImportError: attempted relative import with no known parent package
```

因为 `python pkg/sub.py` 里 `__package__` 是 `None`，解释器不知道 `.` 指的是谁。
**只要模块里有相对导入，就只应该用 `-m` 启动它。**

### 2.2 一个文件可能被执行两次

这是 `-m` 最隐蔽的坑。假设模块在内部又导入了自己：

```python
# pkg/mod.py
import sys
import pkg.mod
print("__name__ =", __name__)
```

```bash
$ python -m pkg.mod
__name__ = pkg.mod      # 第一遍：作为 pkg.mod 被 import
__name__ = __main__     # 第二遍：作为程序入口执行
```

`runpy` 把 `pkg/mod.py` 以 `__main__` 的名字跑起来，而 `import pkg.mod` 又按正常
模块名加载了**同一份源码的第二份模块对象**。于是模块级状态（缓存、连接池、注册表、
单例、`logging` 配置）全部有两份。

判断方法很直接：

```python
import sys
print(sys.modules["pkg.mod"] is sys.modules["__main__"])   # 实测 False
```

规避方式：入口模块只放 `main()` 与参数解析，真正的逻辑放别的模块；或者用
`python -m pkg` + `__main__.py`（`__main__.py` 本来就不该被 import）。

### 2.3 `.py` 后缀不是"指定文件"，而是"子模块"

直觉上 `python -m foo.py` 该等于 `python foo.py`。实际不是，而且失败方式很坑：

```bash
$ python -m foo.py
ran foo.py | __name__ = foo      # 先被当作模块 foo 执行了一遍！
python3: Error while finding module specification for 'foo.py'
         (ModuleNotFoundError: __path__ attribute not found on 'foo' ...)
         Try using 'foo' instead of 'foo.py' as the module name.
$ echo $?
1
```

解释器把 `foo.py` 理解成"模块 `foo` 的子模块 `py`"：先 `import foo`，再去找 `foo.py`
这个子模块，找不到就报错。

关键在第一句——`import foo` 时 `__name__` 是 `'foo'`，所以
`if __name__ == "__main__":` **不会**触发，`main()` 根本没跑；但模块级代码照跑不误。
实测一个只写文件、不开 guard 的模块：

```bash
$ cat side.py
open("sideffect.txt", "w").write("执行了")

$ python -m side.py; ls sideffect.txt
sideffect.txt        # 副作用已经落地，进程却以 1 退出
```

于是出现最难查的状态：**做了一半事，报错退出，`main()` 从未执行**。

结论：`-m` 只吃模块名（`foo`、`pkg.mod`），不吃路径（`sub/bar.py` 同样报错）。
想跑文件就用 `python foo.py`，想用包的上下文就用 `python -m pkg.mod`。

### 2.4 `-m` 与 `-P` 互斥

`-P`（3.11+）的作用是"不要把脚本目录或 cwd 插进 `sys.path`"，用于安全加固。实测：

```bash
$ python -P -m pkg
python3: No module named pkg        # 本地包找不到了
```

因为 `-m` 依赖 cwd 在 `sys.path` 里才能发现本地包。**`-P` 适合跑已安装的东西，
不适合开发中的本地包。**

## 3. `-c` 的引用地狱

`-c` 的代码字符串先经过 shell，再交给 Python。所以引用规则是 shell 的，不是 Python 的：

```bash
export NAME=duke
python -c "print('hello $NAME')"    # hello duke —— shell 先展开了
python -c 'print("hello $NAME")'    # hello $NAME —— 字面量
```

写多行代码用**单引号**包住整段，内部随意使用双引号：

```bash
python -c '
import json, sys
data = {"k": "v"}
print(json.dumps(data, ensure_ascii=False))
'
```

需要给 `-c` 传外部值时，不要拼字符串（既难读又有注入风险），走环境变量：

```bash
COUNT=3 python -c "import os; print(int(os.environ['COUNT']) * 2)"   # 6
```

需要传多个参数时，`sys.argv[0]` 是 `'-c'`，其余参数从 `sys.argv[1]` 开始正常可用。

## 4. 解释器开关速查

`python -h` 会打出一长串，日常真正用得上的就这些：

| 开关 | 作用 | 典型场景 |
|------|------|----------|
| `-u` | stdout/stderr 无缓冲 | 日志管道、容器里实时看输出 |
| `-B` | 不写 `__pycache__` | 只读文件系统、CI 里避免污染 |
| `-O` | `__debug__ = False`，跳过 `assert` | 生产环境关断言 |
| `-OO` | 在 `-O` 基础上再剥掉 docstring | 减小包体积 |
| `-W error` | 把警告升级为异常 | CI 里卡住 DeprecationWarning |
| `-X dev` | 开发模式：开默认警告与调试钩子 | 本地排查 |
| `-X importtime` | 打印每个模块的导入耗时 | 优化启动速度 |
| `-X utf8` | 强制 UTF-8 模式 | 跨平台编码一致性 |
| `-X pycache_prefix=DIR` | 把 pyc 统一写到别处 | 只读源码目录 |
| `-i` | 脚本跑完进入交互式解释器 | 调试脚本留下的现场 |
| `-I` | 隔离模式，等价于 `-E -s -P` | 复现"干净环境"下的问题 |
| `-E` | 忽略所有 `PYTHON*` 环境变量 | 排查环境变量污染 |
| `-s` | 不加载用户 site-packages | 排除本地乱装的包 |
| `-S` | 不加载 `site` 模块（更彻底） | 极简环境、嵌入式 |
| `-P` | 不把脚本目录/cwd 放进 `sys.path` | 防止同名文件遮蔽标准库 |
| `-q` | 不打印启动横幅 | 脚本化调用 |

几组实测输出，便于建立直觉：

```bash
$ python -c "import sys; print(sys.flags.isolated, sys.flags.ignore_environment)"
0 0
$ python -I -c "import sys; print(sys.flags.isolated, sys.flags.ignore_environment)"
1 1
```

`-O` 与 `-OO` 的差别只在 docstring，且两者的 pyc 文件名不同，可以并存：

| 开关 | `__debug__` | 模块 docstring | pyc 文件名 |
|------|-------------|----------------|------------|
| 默认 | `True` | 保留 | `opt2.cpython-313.pyc` |
| `-O` | `False` | 保留 | `opt2.cpython-313.opt-1.pyc` |
| `-OO` | `False` | `None` | `opt2.cpython-313.opt-2.pyc` |

`-O` 的作用面很窄：只是把 `__debug__` 置为 `False`，从而让 `assert` 被跳过。代价是
**被跳过时没有任何提示**。要用在生产环境里做参数校验的判断，就别写成 `assert`——
改成 `if not cond: raise ValueError(...)`，才能做到"该拦的拦、该报的报"。

## 5. 写一个真正的 CLI

骨架只有三段：解析参数、干活、返回退出码。

```python
# cli.py
import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="notes", description="整理 Markdown 笔记")
    p.add_argument("paths", nargs="+", metavar="PATH", help="要处理的文件")
    p.add_argument("-o", "--output", help="输出文件，默认写 stdout")
    p.add_argument("--dry-run", action="store_true", help="只打印计划，不落盘")
    p.add_argument("-v", "--verbose", action="count", default=0, help="可重复叠加")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verbose:
        print(f"verbose={args.verbose} paths={args.paths}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
$ python cli.py --help
usage: notes [-h] [-o OUTPUT] [--dry-run] [-v] PATH [PATH ...]

整理 Markdown 笔记

positional arguments:
  PATH                 要处理的文件

options:
  -h, --help           show this help message and exit
  -o, --output OUTPUT  输出文件，默认写 stdout
  --dry-run            只打印计划，不落盘
  -v, --verbose        可重复叠加
```

```bash
$ python cli.py -vv a.md b.md     # verbose=2 paths=['a.md', 'b.md']
```

这个骨架里有几个刻意的选择：

| 写法 | 为什么 |
|------|--------|
| `main(argv=None)` | 测试时可以直接传 `["-v", "a.md"]`，不用改 `sys.argv` |
| 返回 `int` 而非直接 `sys.exit` | 让 `main()` 可被 import 复用，退出码只在一处决定 |
| `sys.exit(main())` | 统一把返回值变成进程退出码；返回 `None` 视为 0 |
| `prog="notes"` | 见下节，`-m` 调用时默认 prog 是文件名，很难看 |
| `-v` 用 `action="count"` | `-vv` 自然叠加成 2，比 `-v -v` 友好 |

### 5.1 `prog` 在 `-m` 下会变成文件名

argparse 默认用 `os.path.basename(sys.argv[0])` 当程序名。用 `-m` 调用时，
`sys.argv[0]` 是模块文件的绝对路径，于是 help 里就露馅了：

```bash
$ python -m pkg.tool --help
usage: tool.py [-h] name        # 不是 pkg.tool

$ python -m pkg.tool2 --help    # 显式传 prog="pkg.tool2"
usage: pkg.tool2 [-h] name
```

所以**打算同时支持 `python -m xxx` 和命令行入口的工具，一定要显式写 `prog=`**。

### 5.2 输出流的约定

| 流 | 放什么 | 依据 |
|----|--------|------|
| stdout | 程序的**结果**（数据、报告、JSON） | 要被 `\|` 或 `>` 消费 |
| stderr | 日志、进度、警告、错误 | 不该混进结果里 |
| 退出码 | 成功/失败的机器可读信号 | shell 靠它做判断 |

进度条写 stdout 是最常见的错误：一旦有人 `python tool.py > out.csv`，进度条就污染了
数据文件。正确的做法是写 stderr，并按 `sys.stderr.isatty()` 决定要不要画：

```python
import sys

if sys.stderr.isatty():
    print("\r处理中 42%", end="", file=sys.stderr, flush=True)
```

`isatty()` 在重定向或管道里是 `False`，这时退化成纯文本日志即可。

## 6. 退出码

shell、CI、`subprocess` 全靠退出码判断成败，这里的约定值得记准（下表退出码均为实测）：

| 退出码 | 含义 | 来源 |
|--------|------|------|
| `0` | 成功 | 正常返回 / `sys.exit(0)` / `sys.exit(None)` |
| `1` | 一般性失败 | 未捕获异常；`sys.exit("错误消息")` |
| `2` | 用法错误 | argparse 参数不合法（自动） |
| `120` | 退出时 flush stdout 失败 | 管道下游提前关闭（如 `\| head`） |
| `126` | 找到了但不可执行 | shell 层 |
| `127` | 命令不存在 | shell 层 |
| `130` | 被 Ctrl-C 中断 | SIGINT（128+2） |
| `141` | 被 SIGPIPE 终止 | SIGPIPE（128+13），仅在 `SIG_DFL` 下 |
| `143` | 被 SIGTERM 终止 | SIGTERM（128+15） |

几个反直觉点：

```bash
$ python -c "import sys; sys.exit('出错了：缺少输入文件')"
出错了：缺少输入文件        # 注意：打到 stderr，不是 stdout
$ echo $?
1
```

传字符串给 `sys.exit()` 等价于"打印到 stderr + 退出码 1"，不会变成退出码，也不该
拿它传状态码。想要自定义码就传整数：

```bash
$ python -c "import sys; sys.exit(3)";    echo $?   # 3
$ python -c "import sys; sys.exit(256)";  echo $?   # 0（按 256 取模）
$ python -c "import sys; sys.exit(-1)";   echo $?   # 255
```

退出码只有一个字节，超出 0–255 会被截断——这点在容器里尤其坑，`exit 256` 会被当成成功。

### 6.1 管道下游关闭：120 而不是 141

```bash
$ python -c "
for i in range(300000):
    print(i)
" | head -2
0
1
Traceback (most recent call last):
  ...
BrokenPipeError: [Errno 32] Broken pipe
Exception ignored on flushing sys.stdout:
BrokenPipeError: [Errno 32] Broken pipe
$ echo ${pipestatus[1]}     # zsh：实测 120（bash 用 ${PIPESTATUS[0]}）
```

Python 默认把 `SIGPIPE` 设成忽略，让 `write()` 返回 `EPIPE` 并抛 `BrokenPipeError`。
在 shell 脚本里这会被当成"程序失败"，于是 `set -o pipefail` 的场景直接炸。

想恢复 Unix 惯例（安静退出，码 141）：

```python
import signal

signal.signal(signal.SIGPIPE, signal.SIG_DFL)
```

实测改成 `SIG_DFL` 后，同一条管道安静退出，`pipestatus` 为 `141`。注意这只在 Unix
上有效，Windows 没有 `SIGPIPE`。

## 7. 缓冲与管道

交互终端里 stdout 是**行缓冲**（换行就 flush），重定向到文件或管道就变成**块缓冲**
（攒满约 8KB 才写）。所以同一个脚本"终端里能看到输出，写进日志却一片空白"。

用子进程逐行读取并打时间戳，实测（`print` 之后 `sleep(0.3)`，共 3 行）：

| 模式 | 三行到达时刻 |
|------|--------------|
| 默认（管道） | `0.94s` / `0.94s` / `0.94s` —— 全挤在退出瞬间 |
| `-u` | `0.04s` / `0.34s` / `0.65s` —— 每行间隔 0.3s |

三种解法，按推荐顺序：

```bash
python -u script.py                 # 整个进程无缓冲
PYTHONUNBUFFERED=1 python script.py # 同上，环境变量版（容器里常用）
```

```python
print("进度", flush=True)            # 只让关键那行立刻出去
```

日志场景优先用 `logging` 配 `StreamHandler`，它默认每条都 flush，不需要 `-u`。

## 8. 打包成命令

写好的 CLI 有两种对外形态，一般**两个都提供**：

| 形态 | 用户怎么用 | 需要什么 |
|------|-----------|----------|
| 模块入口 | `python -m mytool` | `mytool/__main__.py` |
| 控制台脚本 | `mytool` | `[project.scripts]` 入口点 |

`pyproject.toml` 里声明入口点：

```toml
[project.scripts]
mytool = "mytool.cli:main"
```

安装后，`mytool` 这个命令会调用 `mytool.cli.main()`，并**把返回值当退出码**
（返回 `None` 视为 0）。这就是 `main()` 要返回 `int` 的原因——它同时服务
`sys.exit(main())` 和 console script 两条路径。

`__main__.py` 则只要两行：

```python
# mytool/__main__.py
import sys

from .cli import main

sys.exit(main())
```

### 8.1 为什么推荐 `python -m pip`

`pip` 这个命令是个独立的可执行文件，它的 shebang 指向**安装时那个解释器**。机器上装了
多个 Python 时，`pip install x` 很可能装进了另一个环境，然后 `python -c "import x"`
报找不到。

```bash
python -m pip install requests   # 一定装进"当前这个 python"
pip install requests             # 装进 pip 自己 shebang 指向的那个
```

`-m` 让解释器自己去加载 pip 模块，不存在"哪个 pip"的问题。同理适用于
`python -m pytest`、`python -m venv`、`python -m http.server`、`python -m json.tool`。

标准库自带一批可以直接用的小工具，不必自己写脚本：

```bash
python -m json.tool < data.json          # 格式化/校验 JSON
python -m http.server 8000               # 起一个静态文件服务器
python -m calendar 2026 11               # 打印月历（参数顺序是 年 月）
python -m site                           # 看 sys.path 与 site-packages 位置
python -m venv .venv                     # 建虚拟环境
```

## 9. 常见误区

| 误区 | 实际行为 |
|------|----------|
| `python -m script.py` 可以当路径用 | **危险**：它先把 `script` 当模块执行一遍（`__name__` 是 `script`，`main()` 不跑但模块级副作用照跑），再报错退出 1 |
| `python -m` 等于 `python 文件` | `-m` 先导入再执行，`sys.path[0]` 是 cwd，且会设置 `__package__` |
| `python script.py` 找不到包就加 `sys.path` | 先看是不是被同名文件遮蔽了；`-P` 或 `-m` 往往才是正解 |
| `assert` 可以当参数校验 | `-O` 下被静默跳过；用户输入校验必须用 `if ... raise` |
| `sys.exit("msg")` 传的是退出码 | 它是"打印到 stderr + 码 1" |
| 进度条写 stdout | 重定向时污染结果文件；应写 stderr |
| `pip install` 和 `python -m pip install` 等价 | 多解释器环境下可能装到不同地方 |
| `-c` 里用双引号包代码 | shell 会先展开 `$VAR`、反引号；多行代码一律用单引号 |

## See Also

- [[06-python-stdlib|Python 内建模块]] —— `argparse` 的 `add_argument` 基础用法在那里，本文只讲 CLI 骨架
- [[12-dependency-config|依赖管理配置文件]] —— `[project.scripts]` 与 `entry_points` 的完整写法与迁移对照
- [[09-virtual-environments|虚拟环境]] —— `python -m venv` 是 `-m` 的典型用法，也解释了为什么要用 `python -m pip`
- [[10-uv|uv 包管理器]] —— `uv run` / `uv tool run` 把解释器选择与脚本执行一并接管
- [[17-pytest|pytest 测试框架]] —— `python -m pytest` 相比 `pytest` 能避免解释器错配
- [[18-debugging-profiling|Python 调试与性能分析]] —— `-X importtime`、`python -m pdb` 与本文的开关体系直接衔接
- [[13-python-exceptions|Python 异常处理]] —— 未捕获异常为何退出码是 1、怎样映射成自定义退出码
- [[index|Python 笔记目录]]
