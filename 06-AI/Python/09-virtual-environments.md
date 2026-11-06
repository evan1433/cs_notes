---
title: Python 虚拟环境
description: venv 的隔离原理（pyvenv.cfg 与 sys.prefix）、创建参数、激活机制与免激活用法、venv/virtualenv/conda/uv 选型及常见误区
tags:
  - python
  - venv
  - dependency-management
date: 2026-11-06
aliases:
  - python-virtualenv
---

# Python 虚拟环境

虚拟环境常被当成"隔离依赖的容器"，这个理解会导致一连串误判：以为必须激活才能用、以为目录可以随便拷给同事、
以为它隔离了 Python 版本。实际上它只做了一件事——**让解释器启动时把 `sys.prefix` 指向另一个目录，
从而换掉 `site-packages` 的搜索路径**。它不是容器、不是沙箱、也不隔离进程。

---

## 1. venv（Python 内置）

```bash
python -m venv .venv          # 创建虚拟环境
source .venv/bin/activate     # 激活（Linux/macOS）
.venv\Scripts\activate        # 激活（Windows）
deactivate                    # 退出虚拟环境
```

---

## 2. 虚拟环境的作用

- 隔离项目依赖
- 避免版本冲突
- 便于项目迁移

展开说，一个环境实际隔离的是三样东西：

| 被隔离的对象 | 具体表现 | 不隔离什么 |
|---|---|---|
| `site-packages` 搜索路径 | 装包只落到本环境目录 | 不隔离**标准库**（共享同一个） |
| 可执行脚本（`bin/` 下的 `pip`、`pytest`） | 各自独立，互不覆盖 | 不隔离**系统命令**（`git`、`gcc` 照旧） |
| 解释器本身（软链接或副本） | 每个环境绑定一个 base Python | 不隔离**Python 版本**——版本由创建时选的 base 决定，想换要重建或用 `--upgrade` |

> "便于项目迁移"这条要打个折：环境目录内的脚本 shebang 写的是**绝对路径**，
> 官方文档明确说 "environments are inherently non-portable"。真正可迁移的是 `pyproject.toml` + lock
> 文件，不是 `.venv/` 目录本身。

---

## 3. 隔离的底层机制

### 3.1 `pyvenv.cfg`：环境的身份证

创建后环境根目录会多出一个 `pyvenv.cfg`，解释器启动时就是靠它判断"我处在虚拟环境中"：

```ini
home = /usr/local/bin
include-system-site-packages = false
version = 3.13.12
executable = /usr/local/bin/python3.13
command = /usr/local/bin/python3 -m venv .venv
```

| 键 | 作用 | 是否被官方文档明确说明 |
|---|---|---|
| `home` | 基础解释器所在目录，Python 去这里找标准库 | 是，原文："places a `pyvenv.cfg` file in it with a `home` key" |
| `include-system-site-packages` | 是否把系统 `site-packages` 也加入搜索路径 | 是，由 `--system-site-packages` 决定 |
| `version` / `executable` / `command` | 记录创建时的版本、解释器路径与原始命令，便于排查 | 文档未逐一列出，但实际生成的文件里都有 |

动手改 `include-system-site-packages` 也能生效，但下次 `python -m venv --upgrade` 会把它覆盖回去，所以还是用命令行参数。

### 3.2 `sys.prefix` 与 `sys.base_prefix`

这是判断"我在不在虚拟环境里"的唯一可靠依据：

```python
import sys

print("prefix      =", sys.prefix)       # /path/to/project/.venv
print("base_prefix =", sys.base_prefix)  # /usr/local
print("executable  =", sys.executable)   # /path/to/project/.venv/bin/python
print("is_venv     =", sys.prefix != sys.base_prefix)
```

官方文档原话：

> "It is sufficient to check `sys.prefix != sys.base_prefix` to determine if the current interpreter
> is running from a virtual environment."

**为什么不看 `VIRTUAL_ENV`**：它只在"激活过"时才存在，而激活是可选的。同一段文档也写了——"Since explicitly
activating a virtual environment is not required to use it, `VIRTUAL_ENV` cannot be relied upon to
determine whether a virtual environment is being used."。

### 3.3 目录结构

```text
.venv/
├── pyvenv.cfg                 # 环境元信息（见 3.1）
├── bin/                       # Windows 为 Scripts/
│   ├── python -> /usr/local/bin/python3.13   # 软链接，跨文件系统时改为副本
│   ├── pip / pip3 / pip3.13
│   ├── activate               # bash/zsh
│   ├── activate.csh / activate.fish
│   └── Activate.ps1           # Windows PowerShell
├── include/                   # C 扩展编译时的头文件
└── lib/python3.13/site-packages/   # 本环境装的包都在这
```

---

## 4. 创建参数

```bash
python -m venv .venv                        # 最常用：默认不继承系统包
python -m venv --system-site-packages .venv # 继承系统 site-packages
python -m venv --prompt "myapp" .venv       # 改激活后提示符前缀，目录名仍为 .venv
python -m venv --clear .venv                # 先清空目录再创建
python -m venv --upgrade .venv              # 基础 Python 原地升级后，同步环境
python -m venv --upgrade-deps .venv         # 顺带把环境里的 pip 升到最新（3.9+）
python -m venv --without-pip .venv          # 不装 pip（极少用）
```

| 参数 | 什么时候用 | 注意 |
|---|---|---|
| `--system-site-packages` | 想复用系统里已装的大包（如 conda 里的 torch） | 依赖会**隐式泄漏**，别人复现时缺包；生产环境不要用 |
| `--copies` / `--symlinks` | 环境要跨文件系统放置时用 `--copies` | 默认跟随平台；Windows 上不建议用符号链接，双击 `python.exe` 会解析掉链接绕过环境 |
| `--clear` | 环境被搞坏了，想保留目录名重建 | 会**删掉目录内所有内容** |
| `--upgrade` | 用 Homebrew 升级了 Python 之后 | 只换 base 指向，不重装包 |
| `--prompt` | 同时开多个环境，怕提示符分不清 | 支持 `.` 表示用当前目录名 |

版本变更中容易踩的两条：

- **3.12 起 `setuptools` 不再是 venv 的核心依赖**。老教程里"新建环境后直接 `python setup.py`"
  或 `pip install -e .`（老式非 PEP 517 项目）会失败，需要自己 `pip install setuptools`。
- **3.13 起 venv 默认在环境目录里生成 `.gitignore`**（内容是 `*`），所以即使误把 `.venv`
  当成可提交目录，git 也会忽略它；对应的关闭开关是 `--without-scm-ignore-files`。

---

## 5. 激活做了什么，以及为什么可以不做

`activate` 是个 shell 脚本，做的事只有三件：

1. 把 `<env>/bin` **前置**到 `PATH`（所以 `python`、`pip` 指向环境内的版本）
2. 导出 `VIRTUAL_ENV=<env 绝对路径>`
3. 改 `PS1` 提示符，前面加 `(.venv) `

它**没有**改变当前 shell 的任何其他行为，也**没有**启动守护进程。所以"退出终端后环境就没了"是错觉——环境目录一直在，只是 `PATH` 变了。

### 官方支持不激活直接用

> "You don't specifically *need* to activate a virtual environment, as you can just specify the full path
> to that environment's Python interpreter when invoking Python."

三种用法对比：

| 用法 | 命令 | 适用场景 | 缺点 |
|---|---|---|---|
| 激活 | `source .venv/bin/activate` | 交互式开发、连续敲多条命令 | 容易忘记激活而装错地方 |
| 直接路径 | `.venv/bin/python -m pip install requests` | 脚本、CI、定时任务、Makefile | 命令略长 |
| 工具代办 | `uv run python script.py` | 现代项目管理 | 需要引入 uv，见 [[10-uv\|uv 包管理器]] |

**为什么直接路径一定装对**：`bin/` 下的脚本第一行 shebang 写的是环境解释器的绝对路径，例如
`#!/path/to/.venv/bin/python3`。不管 `PATH` 指向哪，脚本都会用环境内的解释器执行——这也正是环境不可迁移的原因。

推荐在脚本和 CI 里一律用显式路径，避免"先 activate 再跑"这种隐式依赖：

```bash
# 反例：CI 里若漏了 activate，装到系统 Python 上会静默成功
pip install -r requirements.txt

# 正例：装到哪一目了然，也不需要 activate
.venv/bin/python -m pip install -r requirements.txt
```

---

## 6. venv / virtualenv / conda / uv 怎么选

| 维度 | `venv`（内置） | `virtualenv` | `conda` | `uv venv` |
|---|---|---|---|---|
| 是否需额外安装 | 否，标准库自带 | 需 `pip install virtualenv` | 需装 Miniconda/Anaconda | 需装 uv |
| 创建速度 | 慢（每次重新 bootstrap pip） | 快于 venv | 慢 | 最快 |
| 能否管理 Python 版本 | ❌ 只能用已有的 base | ❌ | ✅ 可装任意版本 | ✅ `uv python install` |
| 能否装非 Python 依赖（CUDA/MKL） | ❌ | ❌ | ✅ | ❌ |
| 是否自动生成 lock | ❌ | ❌ | 弱（`environment.yml`） | ✅ `uv.lock` |
| 典型用途 | 零依赖项目的保底方案 | 需要兼容 Python 2 的老项目 | AI 训练、科学计算 | 现代项目默认选择 |

选型口诀：

- **只是隔离依赖** → `python -m venv .venv`，够用且零安装
- **要管 CUDA / cuDNN / MKL** → `conda`（环境内仍可用 `uv pip` 装纯 Python 包，见 [[10-uv\|uv 包管理器]]）
- **新项目、要可复现** → `uv`，`uv sync` 一条命令搞定环境和 lock 对齐
- **不要混用**：在 conda 环境里再套一层 venv，会让 `which python` 彻底不可信

---

## 7. 常见误区

| 误区 | 实际情况 |
|---|---|
| "把 `.venv` 提交到 git 就能共享环境" | 含绝对路径与平台相关二进制，**不可移植**；该提交的是 lock，见 [[12-dependency-config\|依赖配置]] |
| "换台机器直接 `scp -r .venv` 就能用" | shebang 与 `pyvenv.cfg` 里的路径全指向旧机器，必然失败。在新机器上重建环境 |
| "激活了就一定装对环境" | 激活只改 `PATH`。若 IDE / 子进程没继承这个 shell，仍会装到别处。用 `python -c "import sys; print(sys.prefix)"` 确认 |
| "`--system-site-packages` 只是多几个包，无所谓" | 系统包会**遮蔽**环境内的同名包（取决于路径顺序），且换机器后这些包不存在，排查成本很高 |
| "删除环境目录会留下残留" | 不会。venv 是自包含的，`rm -rf .venv` 即彻底清理，不会写注册表或全局配置 |
| "`deactivate` 能退出所有环境" | 它只是 `activate` 定义的 shell 函数，嵌套激活时只能退最内层；环境目录本身不受影响 |

---

## 8. 常见排错

| 现象 | 原因 | 解决 |
|---|---|---|
| `-bash: .venv/bin/activate: No such file` | 环境建在别处或 Windows 上建的 | Windows 用 `Scripts\activate` |
| Windows PowerShell 提示"禁止运行脚本" | 执行策略默认 `Restricted` | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| 激活后 `python` 仍指向系统版本 | 环境 `bin/` 前还有更高优先级的 shim（pyenv、conda、asdf） | `which -a python`；或干脆用 `.venv/bin/python` 显式路径 |
| `pip install` 报 `externally-managed-environment` | 装到了系统 Python（PEP 668） | 激活正确环境，或用 `.venv/bin/python -m pip` |
| 升级 Python 后环境里的包全消失/报错 | 用的是 Homebrew 的版本化路径，旧 base 已被删除 | `python -m venv --upgrade .venv`；严重时用 `--clear` 重建后重装 |
| 团队里有人能跑有人不能 | 有人开了 `--system-site-packages`，依赖了系统包 | 统一用默认参数创建；CI 里跑一遍干净环境验证 |
| `python -m venv` 报 `ensurepip is not available` | `ensurepip` 被拆成单独包（Debian） | `apt install python3-venv` |

---

## See Also

- [[08-pypi-pip|PyPI 与 pip]] —— 在激活后的环境里安装依赖，含镜像源与离线安装
- [[10-uv|uv 包管理器]] —— `uv venv` / `uv sync` 是同一件事的更快实现，且自带 lock
- [[12-dependency-config|依赖管理配置文件]] —— 决定环境里到底要装什么
- [[11-python-cli|Python 命令行工具]] —— `python -m venv` 正是 `-m` 的典型用法
- [[index|Python 笔记目录]]

## 参考

- [venv — Creation of virtual environments](https://docs.python.org/3/library/venv.html)
- [PEP 405 – Python Virtual Environments](https://peps.python.org/pep-0405/)
- [PEP 668 – Marking Python base environments as externally managed](https://peps.python.org/pep-0668/)
