---
title: Python 依赖管理配置文件
description: requirements.txt 完整语法（说明符、环境标记、extras、直接引用）、pyproject.toml（PEP 621）字段速查、PEP 735 依赖组、lock 文件分工与提交策略
tags:
  - python
  - packaging
  - dependency-management
date: 2026-11-06
aliases:
  - python-dependency-config
---

# Python 依赖管理配置文件

Python 的依赖配置不是"一个文件"，而是三种角色各司其职：

| 角色 | 文件 | 回答的问题 | 谁维护 |
|---|---|---|---|
| **声明**（我想要什么） | `pyproject.toml` 的 `[project].dependencies` | "这个项目需要 requests 和 flask" | 人，宽泛约束 |
| **锁定**（实际定了什么） | `uv.lock` / `poetry.lock` / `pip-compile` 产物 | "最终解析成 requests 2.32 + urllib3 2.2" | 工具生成，精确到补丁版与哈希 |
| **事实**（环境里装了什么） | `pip freeze` 导出的 `requirements.txt` | "我这台机器现在有什么" | 由环境反推，**不该当声明用** |

混用这三者是绝大多数"在我机器上能跑"问题的源头。下面按文件类型拆开讲。

---

## 1. requirements.txt

### 1.1 格式

```text
requests==2.28.0
flask>=2.0.0
numpy>=1.20,<2.0
pandas  # 不指定版本
```

### 1.2 版本说明符

| 符号 | 含义 |
|------|------|
| `==` | 精确版本 |
| `>=` | 大于等于 |
| `<=` | 小于等于 |
| `>` | 大于 |
| `<` | 小于 |
| `~=` | 兼容版本（如 `~=1.4.2` 等价于 `>=1.4.2,<1.5.0`） |

补充三个原文表格没列、但实际常遇到的：

| 符号 | 含义 | 示例 |
|------|------|------|
| `!=` | 排除某个版本（常用于跳过有 bug 的发布） | `django!=4.2.7` |
| `===` | 任意字符串精确匹配，**不做版本规范化** | `===1.0.0+local.build` |
| 逗号 | 交集约束，可叠加多个 | `>=1.20,!=1.24.0,<2.0` |

> `~=` 的语义按**倒数第二位**截断，这点最容易记错：
>
> - `~=1.4.2` → `>=1.4.2, ==1.4.*`（只允许补丁版变动）
> - `~=1.4` → `>=1.4, ==1.*`（允许次版本变动）
> - `~=1` → 非法写法，至少写两位

### 1.3 环境标记（markers）

同一个文件在不同平台装不同的包，靠 PEP 508 的 `;` 标记：

```text
# Windows 才装
pywin32==306; sys_platform == "win32"

# 仅 Linux
uvloop>=0.19; sys_platform == "linux"

# 按 Python 版本分流
numpy>=1.26; python_version >= "3.12"
numpy<1.26; python_version < "3.12"

# 按 CPU 架构（Apple Silicon / x86）
torch==2.4.0; platform_machine == "arm64"
```

常用标记变量：

| 标记 | 取值示例 |
|------|----------|
| `python_version` | `"3.12"`（主.次，字符串比较） |
| `python_full_version` | `"3.12.4"` |
| `sys_platform` | `"linux"` / `"darwin"` / `"win32"` |
| `platform_system` | `"Linux"` / `"Darwin"` / `"Windows"` |
| `platform_machine` | `"x86_64"` / `"arm64"` / `"aarch64"` |
| `implementation_name` | `"cpython"` / `"pypy"` |

> 版本比较是**字符串**比较，`python_version > "3.9"` 会把 `"3.10"` 判成小于 `"3.9"`（因为 `"1" < "9"`）。
> 要么写 `>=` / `<` 分段，要么改用 `python_full_version`。

### 1.4 extras 与直接引用

```text
# extras：装上包的附加功能依赖
requests[socks,security]>=2.31

# 直接从 wheel / sdist URL 装（内网制品库常用）
mylib @ https://pkgs.company.com/wheels/mylib-1.0.0-py3-none-any.whl

# 从 git 装：@ 后面是 ref（分支/tag/commit）
mylib @ git+https://github.com/org/mylib.git@v1.2.0

# 本地可编辑安装（开发期）
-e .
-e ./packages/core
```

`包名 @ URL` 这种写法叫 **direct reference**，语法来自 PEP 508。它的代价是**不可被依赖解析器回溯**——一旦写了 URL，工具不会再为它寻找其他版本。

### 1.5 组合：`-r` / `-c` / `--hash`

```text
# requirements-dev.txt —— 分层引用，避免重复维护
-r requirements.txt
pytest>=8.0
ruff

# constraints.txt —— 只约束不安装（不改依赖图，只压版本）
urllib3<2.0
```

```bash
pip install -r requirements-dev.txt          # 展开 -r 后一起装
pip install -r requirements.txt -c constraints.txt   # 用约束压住传递依赖
```

`-c` 的用途：顶层依赖放宽（`>=`），但把某个已知会出问题的**传递依赖**钉死在约束文件里，不改动原始声明。详见 [[08-pypi-pip|PyPI 与 pip]] 的 `--require-hashes` 一节。

### 1.6 分层组织实践

```text
requirements/
├── base.txt        # 运行时公共依赖
├── dev.txt         # -r base.txt + pytest/mypy/ruff
├── prod.txt        # -r base.txt + gunicorn，且全部 == 锁定
└── constraints.txt # 跨文件统一的传递依赖约束
```

> **不要**用 `pip freeze` 生成 `base.txt`：它会把环境里所有包（包括你临时试验装的）都写进去，
> 且丢失"哪些是直接依赖"的信息。正确做法是从 `pyproject.toml` 声明出发，由工具生成锁定的 `prod.txt`。

---

## 2. pyproject.toml

现代 Python 项目的配置文件（PEP 517/518）：

```toml
[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "requests>=2.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=22.0.0",
]

[build-system]
requires = ["setuptools>=45"]
build-backend = "setuptools.build_meta"
```

### 2.1 `[project]` 字段速查（PEP 621）

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 分发包名（**不是** import 名，见 [[08-pypi-pip\|PyPI 与 pip]]） |
| `version` | 二选一 | 静态版本；或写进 `dynamic` 由构建后端求值 |
| `dependencies` | | 运行时依赖列表，语法同 requirements.txt |
| `requires-python` | 建议 | 如 `">=3.10"`，装包时低于此版本直接拒绝 |
| `description` | | 一句话简介 |
| `readme` | | `"README.md"`，会自动作为 PyPI 长描述 |
| `license` | | 新版打包标准（PEP 639）用 SPDX 字符串 `"MIT"`；旧写法是 `{text = "MIT"}` 或 `{file = "LICENSE"}` |
| `authors` / `maintainers` | | `[{name = "...", email = "..."}]` |
| `keywords` / `classifiers` | | PyPI 检索与分类 |
| `urls` | | `{Homepage = "...", Repository = "..."}` |
| `scripts` | | 命令行入口，见 2.3 |
| `optional-dependencies` | | extras，见 2.4 |
| `dynamic` | | 声明哪些字段不在此静态给出，如 `["version"]` |

动态版本的最小写法：

```toml
[project]
name = "myproject"
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "myproject.__version__"}
```

### 2.2 `[build-system]`：选哪个后端

`build-backend` 决定"谁来把这个项目打成 wheel"，`requires` 是构建它所需的依赖（pip 会先建一个隔离环境装这些）：

| 后端 | 声明 | 特点 |
|------|------|------|
| **setuptools** | `setuptools.build_meta` | 兼容性最好，老项目迁移首选 |
| **hatchling** | `hatchling.build` | 配置干净，现代库常用 |
| **flit-core** | `flit_core.buildapi` | 极简，适合纯 Python 单包 |
| **pdm-backend** | `pdm.backend` | 支持 PEP 621 全部特性 |
| **poetry-core** | `poetry.core.masonry.api` | 读取 `[tool.poetry]` 段（非标准） |
| **maturin** | `maturin` | Rust 扩展（PyO3） |
| **scikit-build-core** | `scikit_build_core.build` | C/C++/CMake 扩展 |

> `requires` 里**只需写构建后端本身**，不写运行时依赖（后者由 `dependencies` 描述）。写成
> `requires = ["setuptools", "requests"]` 是常见错误——它会让 requests 在构建阶段被装上，但运行时并不会因此可用。

### 2.3 命令行入口：`[project.scripts]`

```toml
[project.scripts]
mytool = "myproject.cli:main"
```

装包后就会有 `mytool` 命令，等价于调用 `myproject.cli.main()`。这是替代
`entry_points={'console_scripts': [...]}` 的标准写法。入口函数的返回值会被当作退出码（返回 `None` 视为 0）。

### 2.4 `optional-dependencies`（extras）vs `dependency-groups`（PEP 735）

这两个容易混，区别在**给谁用**：

```toml
# extras：给"使用者"的，会写进 wheel 的 METADATA
[project.optional-dependencies]
socks = ["PySocks>=1.5.6"]
all = ["myproject[socks]", "pandas"]

# 依赖组：给"开发者"的，不进入构建产物
[dependency-groups]
test = ["pytest>=8", "coverage"]
lint = ["ruff"]
dev = [{include-group = "test"}, {include-group = "lint"}, "mypy"]
```

| 维度 | extras（optional-dependencies） | dependency-groups（PEP 735） |
|------|------|------|
| 是否写入 wheel 元数据 | ✅ 是，使用者 `pip install "pkg[socks]"` 能装到 | ❌ 否，构建后端"不得写入"（PEP 原文 "MUST NOT"） |
| 面向对象 | 包的使用者（公共 API） | 项目开发者（内部工具链） |
| 装它是否连带装本项目 | ✅ 是（extras 无法脱离包单独安装） | ❌ 否，不隐含安装包本身 |
| 支持非打包项目（纯脚本/数据科学） | ❌ 会被当成"包" | ✅ 支持 |
| 跨组复用 | 只能靠 `"pkg[other]"` 自引用 | ✅ `{include-group = "test"}`，支持嵌套（禁止循环） |

PEP 735 已是 **Final**（2024-10-10 通过），规范现由 PyPA specs 维护。安装方式各工具不同：

```bash
pip install --group dev          # pip 25.1+ 起支持 --group
pip install -e .                 # 依赖组不隐含装项目本身，通常还需要这一条
uv sync --group dev              # uv 用 --group
uv sync --all-groups             # 装全部组
```

> `uv add --dev pytest` 写入的正是 `[dependency-groups].dev`，不再是 `[tool.uv] dev-dependencies`（旧写法已废弃）。

### 2.5 `[tool.*]`：各工具配置集中地

`pyproject.toml` 已成为事实上的统一配置入口，`setup.cfg` / `tox.ini` / `.flake8` 的内容都可以搬进来：

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.uv]
package = true      # 见 [[10-uv|uv 包管理器]]
```

---

## 3. lock 文件：可复现性的真正来源

声明文件只保证"意图一致"，不保证"装出来一样"——因为 `>=` 会随时间漂移。lock 文件把**整棵依赖树**（含传递依赖、版本、哈希）钉死：

| 工具 | lock 文件名 | 是否跨平台通用 |
|------|------------|--------------|
| uv | `uv.lock` | ✅ 一份锁全平台（标记了平台条件） |
| Poetry | `poetry.lock` | 部分（按平台分节） |
| PDM | `pdm.lock` | ✅ |
| pip-tools | `requirements.txt`（带 `--hash`） | ❌ 通常按平台各生成一份 |
| Pipenv | `Pipfile.lock` | ❌ |

lock 与声明的差异处理，uv 给了三档策略（`--frozen` / `--locked` / `--check`），细节见 [[10-uv|uv 包管理器]] 第 2 节。

---

## 4. 三件套分工与提交策略

| 文件 | 提交到 git | 原因 |
|------|-----------|------|
| `pyproject.toml` | ✅ | 项目定义，人维护 |
| lock 文件（`uv.lock` 等） | ✅ | 可复现性来源，**库项目**也建议提交以便 CI 复现 |
| `requirements.txt`（手写声明） | ✅ | 部署场景仍广泛使用 |
| `pip freeze` 产物 | ⚠️ 谨慎 | 只应作为一次性的部署快照，不要当长期声明 |
| `constraints.txt` | ✅ | 团队共享的版本约束 |
| `.venv/` | ❌ | 含绝对路径，不可移植，见 [[09-virtual-environments\|Python 虚拟环境]] |

---

## 5. setup.py 时代对照

老项目里这些写法现在都有对应替代：

| 旧写法（setup.py / setup.cfg） | 现写法（pyproject.toml） |
|------|------|
| `setup(name=..., version=...)` | `[project]` 的 `name` / `version` |
| `install_requires=[...]` | `[project].dependencies` |
| `extras_require={"dev": [...]}` | `[project.optional-dependencies]` |
| `entry_points={"console_scripts": [...]}` | `[project.scripts]` |
| `python_requires=">=3.9"` | `requires-python = ">=3.9"` |
| `packages=find_packages()` | 由构建后端自动发现 |
| `tests_require`（已废弃） | `[dependency-groups].test` |
| `setup.cfg` 里的 `[flake8]` | `[tool.ruff]` 等 |

迁移时不必一次改完：`pyproject.toml` 与 `setup.py` 可以共存，setuptools 会合并两边的元数据（`[project]` 优先）。

---

## 6. 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `No matching distribution found for pkg>=X` | 无匹配当前 Python/平台的 wheel，或索引里没有 | `pip index versions pkg` 查可用版本；放宽约束 |
| 装了 extras 但 import 仍失败 | 包名 ≠ import 名，或 extras 名拼错 | `pip show pkg` 看 `Provides-Extra`；对照 PyPI 页面 |
| 环境标记不生效，装上了别的平台的包 | 标记里的变量名写错 | `python -c "import sys; print(sys.platform)"` 对照实际值 |
| `TOMLDecodeError` | `pyproject.toml` 语法错误（手写数组常漏逗号） | 用 `tomllib` 解析定位；编辑器装 TOML 插件 |
| `ValueError: project must contain ['name']` | 缺 `[project]` 的 `name` / `version` 必填项 | 补 `name` + `version` |
| `Multiple top-level packages discovered` | setuptools 自动发现包时撞到多个目录 | 显式写 `[tool.setuptools] packages` |
| `-e .` 报 `requires a build backend` | 缺 `[build-system]` | 补 `[build-system]` + 装 setuptools |
| 使用方装不到 dev 依赖 | 用了 `[dependency-groups]`，它不进 wheel 元数据 | 改放 `[project.optional-dependencies]`（见 2.4） |

---

## See Also

- [[08-pypi-pip|PyPI 与 pip]] —— 从配置文件到实际安装的完整链路、镜像源与离线安装
- [[10-uv|uv 包管理器]] —— `uv.lock` 的锁定语义与 `--locked` / `--frozen` 策略
- [[09-virtual-environments|Python 虚拟环境]] —— 依赖装进哪个隔离环境
- [[07-python-advanced|Python 进阶话题]] —— `__init__.py` 与包结构
- [[02-python-oop|Python 面向对象]] —— `entry_points` 指向的函数通常就是模块级 `main()`
- [[index|Python 笔记目录]]

## 参考

- [PyPA - Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [PyPA - Dependency Groups 规范](https://packaging.python.org/en/latest/specifications/dependency-groups/)
- [PEP 621 – Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 508 – Dependency specification for Python Software Packages](https://peps.python.org/pep-0508/)
- [PEP 735 – Dependency Groups in pyproject.toml](https://peps.python.org/pep-0735/)
- [PEP 440 – Version Identification and Dependency Specification](https://peps.python.org/pep-0440/)
