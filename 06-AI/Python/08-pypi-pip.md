---
title: PyPI 与 pip
description: Python 包生态全景：PyPI 仓库机制、包分发格式（sdist/wheel）、pip 依赖解析原理、镜像源与私有源配置、打包发布流程与常见排错
tags:
  - python
  - pypi
  - pip
  - package-management
date: 2026-09-17
---

# PyPI 与 pip

Python 的包管理生态由三部分组成：**仓库（PyPI）** 负责存储与分发包，**安装器（pip）** 负责解析依赖并安装，**构建后端（setuptools / hatchling 等）** 负责把源码打成可分发的产物。本文覆盖从"装包"到"发包"的完整链路。

## 1. PyPI

**PyPI**（Python Package Index）是 Python 语言的"应用商店"或"代码仓库"，官方站点为 <https://pypi.org>。

**pip** 是安装工具，从 PyPI 仓库中拉取包。

### 几个容易混淆的概念

| 概念 | 说明 |
|------|------|
| **PyPI** | 中央仓库（服务端），托管所有公开包 |
| **pip** | 安装器（客户端），默认从 PyPI 拉取 |
| **index / index-url** | 仓库地址。PyPI 只是其中之一，公司私服、镜像源都是另一种 index |
| **distribution / 分发包** | 一个可被安装的产物（`.whl` 或 `.tar.gz`），名字即 `pip install` 的名字 |
| **import package** | 代码里 `import` 的模块名，**与分发包名可能不同**（如 `pip install Pillow` → `import PIL`） |

> **TestPyPI**（<https://test.pypi.org>）是官方的练习用仓库，发布流程演练应先走这里，避免污染正式仓库。

### 包的分发格式

PyPI 上的一个"包"通常同时提供两种产物：

| 格式 | 扩展名 | 本质 | pip 安装时 |
|------|--------|------|-----------|
| **wheel（推荐）** | `.whl` | 已构建好的 zip 包，含编译产物 | 直接解压到 site-packages，**秒装，无需本地编译** |
| **sdist（源码分发）** | `.tar.gz` | 源码压缩包 | 需在本地执行构建后端，可能触发 C/C++ 编译，慢且依赖系统工具链 |

wheel 文件名本身编码了兼容信息，遵循 `{distribution}-{version}-{python tag}-{abi tag}-{platform tag}.whl`：

```text
numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
│     │      │     │     └── 平台标签：Linux x86_64 + glibc >= 2.17
│     │      │     └── ABI 标签：CPython 3.11 的 C API
│     │      └── Python 标签：仅支持 CPython 3.11
│     └── 版本
└── 分发包名

torch-2.1.0-py3-none-any.whl   # py3-none-any = 纯 Python 包，全平台通用
```

**实践建议**：装不上某个包时（尤其带 C 扩展的，如 `psycopg2`、`lxml`），优先检查 PyPI 上是否有匹配你 Python 版本和操作系统的 wheel；没有 wheel 时 pip 会回退到 sdist 编译，此时需要系统装好编译器和头文件。

## 2. pip

### 基本命令

```bash
pip install requests          # 安装包
pip install requests==2.28.0  # 安装指定版本
pip install -r requirements.txt  # 从文件安装

pip uninstall requests        # 卸载包
pip list                      # 列出已安装的包
pip show requests             # 显示包信息
pip freeze > requirements.txt # 导出依赖
```

### 常用进阶命令

```bash
pip install "requests>=2.28,<3"     # 版本区间（shell 中建议加引号，避免 > < 被当成重定向）
pip install -U requests             # 升级到最新（--upgrade）
pip install --pre torch             # 允许安装预发布版（a/b/rc），默认不会装
pip install --no-deps some-pkg      # 只装它自己，不装依赖
pip install --force-reinstall --no-cache-dir requests  # 忽略已安装状态与缓存，重装

pip check                           # 检查已装包的依赖冲突（CI 里很有用）
pip index versions requests         # 查看所有可用版本（pip 21.2+）
pip download -d ./wheels -r requirements.txt  # 只下载不安装（离线部署用）
pip cache dir / pip cache purge     # 查看 / 清空本地缓存目录
```

### python -m pip

推荐使用 `python -m pip` 确保使用正确的 Python 环境：

```bash
python -m pip install requests
```

原因：`pip` 这个可执行文件是**某个特定解释器**的软链接，系统里存在多个 Python（系统 Python、Homebrew Python、conda、pyenv…）时，直接敲 `pip` 装到的环境常常不是你当前 `python` 对应的那个。用 `python -m pip` 会把 pip 作为模块运行在当前解释器下，装哪去一目了然。

### pip 装包的内部流程

理解这四步，能解释绝大多数"装包失败"的现象：

```text
1. 定位（resolve）
   向 index 请求包元数据 → 挑一个同时满足版本约束且平台匹配的 wheel
   ↓
2. 依赖解析（dependency resolution）
   递归展开所有子依赖的版本约束，求出一组互不冲突的版本组合
   ↓
3. 下载（download）
   从 index 取回产物，存入本地缓存（~/.cache/pip）
   ↓
4. 安装（install）
   有 wheel → 解压到 site-packages
   只有 sdist → 先调用构建后端（PEP 517）本地构建，再安装
```

关于第 2 步：pip 20.3 起默认启用新解析器（`2020-resolver`）。它会做**回溯搜索**，遇到冲突时不再像旧版那样"先装了再说"，而是报错并告知冲突来源。因此现代 pip 报错信息通常长这样：

```text
ERROR: Cannot install flask==3.0.0 and requests==2.25.0 because these package
versions have conflicting dependencies.

The conflict is caused by:
    flask 3.0.0 depends on Werkzeug>=3.0.0
    ...
```

> 解析失败的应对：放宽顶层约束（`>=` 而非 `==`），或用 `pip install pkg1 pkg2` 让 pip 一次性看到全部约束——**逐条 `pip install` 会让解析器每次只看一个包**，这是最常见的冲突诱因。

### 指定镜像源（-i）

使用 `-i` 参数可以指定包的下载源（镜像源）：

```bash
# 使用清华镜像安装
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用阿里云镜像安装
pip install requests -i https://mirrors.aliyun.com/pypi/simple/
```

**常用国内镜像源：**

| 镜像源 | 地址 |
|--------|------|
| 清华 | https://pypi.tuna.tsinghua.edu.cn/simple |
| 阿里云 | https://mirrors.aliyun.com/pypi/simple/ |
| 中科大 | https://pypi.mirrors.ustc.edu.cn/simple/ |
| 豆瓣 | https://pypi.douban.com/simple/ |
| 腾讯 | https://mirrors.cloud.tencent.com/pypi/simple/ |

**永久设置镜像源：**

```bash
# 设置全局默认镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 查看当前配置
pip config list

# 删除配置
pip config unset global.index-url
```

### 配置文件与优先级

`pip config set` 实际写入配置文件。pip 会按以下顺序读取，**后者覆盖前者**：

| 级别 | 文件路径（macOS / Linux） |
|------|--------------------------|
| 系统级 | `/etc/pip.conf` |
| 用户级 | `~/.config/pip/pip.conf`（macOS 也可为 `~/Library/Application Support/pip/pip.conf`） |
| 虚拟环境级 | `$VIRTUAL_ENV/pip.conf` |
| 环境变量 | `PIP_INDEX_URL` 等 `PIP_<OPTION>` 形式 |
| 命令行参数 | `-i` / `--index-url`，优先级最高 |

典型配置片段：

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
extra-index-url = https://<token>@pkgs.company.com/simple
timeout = 30
retries = 3

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
               pkgs.company.com
```

> **注意**：`trusted-host` 会跳过该主机的 TLS 证书校验。仅用于内网 HTTP 私服，公网源不要加，否则等于放弃 HTTPS 保护。

### 私有源与多源

```bash
# extra-index-url：在默认源之外追加，两者都会查
pip install internal-pkg --extra-index-url https://pkgs.company.com/simple

# 只用私有源时，直接换掉 index-url 更安全（避免依赖混淆攻击）
pip install -r requirements.txt -i https://pkgs.company.com/simple
```

**依赖混淆（dependency confusion）**：同时配置公私两个源时，若内部包名（如 `company-utils`）被攻击者在 PyPI 抢注成更高版本号，pip 可能优先从公网拉到恶意包。内网环境应把内部包用 `==` 精确锁定，或使用 devpi / Nexus / Artifactory 这类**同时代理 PyPI 与私包**的一体化仓库。

### 离线 / 内网安装

先把依赖整体下载到目录，再到无网机器上装：

```bash
# 有网机器：下载 wheel（--platform 可指定目标平台，实现跨机器拉取）
pip download -d ./wheels -r requirements.txt

# 无网机器：禁用 index，只从本地目录找
pip install --no-index --find-links=/path/to/local_packages package_name
pip install --no-index --find-links=./wheels -r requirements.txt
```

## 3. 依赖声明与锁定

| 文件 | 作用 | 生成方式 |
|------|------|----------|
| `requirements.txt` | 扁平的依赖列表，常用于部署 | `pip freeze > requirements.txt` |
| `constraints.txt` | 只约束版本、不触发安装，配合 `-c` 使用 | 手工维护或从 lock 转换 |
| `pyproject.toml` | 项目元数据 + 顶层依赖声明（PEP 621） | 手工维护 |
| lock 文件 | 含传递依赖与哈希的完全锁定结果 | `uv lock` / `pip-compile` / `poetry lock` |

**`pip freeze` 的问题**：它导出的是环境里**所有**包，包括你间接装上的和手动测试装的。开发环境用 `pip freeze` 会产出一份臃肿且不准的清单。正确做法是：依赖写进 `pyproject.toml`，由工具生成 lock，CI/生产只装 lock。

**固定哈希**（高安全场景，防止传输过程被篡改或源被污染）：

```bash
# 生成带哈希的 requirements
pip hash requests-2.31.0-py3-none-any.whl

# 安装时校验：一旦开启，所有包都必须带哈希，否则报错
pip install --require-hashes -r requirements.txt
```

```text
# requirements.txt（--require-hashes 模式下的写法）
requests==2.31.0 \
    --hash=sha256:58cd2187c01e70e6e26505bca751777aa9f2ee0b7f4300988b709f44e013003f
```

详见 [[12-dependency-config|依赖管理配置文件]]。

## 4. 构建与发布自己的包

### 最小可用的 pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-utils"
version = "0.1.0"
description = "Some internal utilities"
requires-python = ">=3.9"
dependencies = ["requests>=2.28.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "ruff"]
```

### 构建

```bash
pip install build twine
python -m build           # 同时产出 sdist 与 wheel 到 dist/
```

### 上传

```bash
# 先传 TestPyPI 验证
python -m twine upload --repository testpypi dist/*
pip install -i https://test.pypi.org/simple/ my-utils==0.1.0

# 正式发布
python -m twine upload dist/*
```

认证方式（安全性从低到高）：

| 方式 | 说明 |
|------|------|
| 账号密码 | 已废弃，PyPI 不再支持 |
| **API token** | 在 pypi.org 账号设置里生成，`pypi-` 前缀；写入 `~/.pypirc` 或交互输入 |
| **Trusted Publishing（OIDC）** | 在 PyPI 上绑定 GitHub 仓库 + workflow，CI 中免密发布，**推荐** |

> ⚠️ **版本号不可复用**：PyPI 上同一个版本号只能上传一次，删了也不行。发布失败需要重传时，必须递增版本号（或加 `.post1` 后缀）。另外正式仓库**不能删包**，只能 `yank`（标记为不推荐，已 pinned 的用户仍可安装）。

### 本地安装自己的项目

```bash
pip install -e .          # 可编辑安装（PEP 660），改源码立即生效，开发期首选
pip install .             # 常规安装，拷贝一份到 site-packages
```

## 5. 工具链对比

| 工具 | 定位 | 适用场景 |
|------|------|----------|
| **pip + venv** | 官方标配，只做安装与环境隔离 | 简单项目、容器镜像 |
| **uv** | Rust 写的极速安装器 + 项目管理 + Python 版本管理 | 新项目首选，见 [[10-uv\|uv 包管理器]] |
| **Poetry / PDM** | 依赖管理 + 打包发布一体化，自带 lock | 需要发布到 PyPI 的库 |
| **conda / mamba** | 跨语言包管理，能管 CUDA、MKL 等非 Python 依赖 | 科学计算、AI 训练环境 |
| **pipx** | 为每个命令行工具创建独立环境 | 装 black、ruff、httpie 这类 CLI |
| **tox / nox** | 多 Python 版本矩阵测试 | 库作者 |

**结论**：日常开发推荐 `uv`；涉及 CUDA/cuDNN 等系统级依赖的训练环境用 `conda`；装命令行小工具用 `pipx`。pip 是它们的底层基础，命令语法大多兼容。

## 6. 安全与最佳实践

| 做法                                                      | 原因                                          |
| ------------------------------------------------------- | ------------------------------------------- |
| 永远在虚拟环境里装包，不要 `sudo pip install`                        | 污染系统 Python，可能破坏系统工具（macOS/Linux 部分系统组件依赖它） |
| 遇到 `externally-managed-environment` 报错，改用 venv 或 `pipx` | PEP 668 保护机制，pip 23.0+ 对系统 Python 生效        |
| 提交 `requirements.txt` / lock 文件到版本库，不提交 `site-packages` | 保证可复现                                       |
| 生产环境用 `==` 精确锁定                                         | 避免上游 breaking change 导致线上事故                 |
| 定期 `pip audit` 扫已知漏洞                                    | 依赖供应链安全                                     |
| 不要对公网源使用 `trusted-host`                                 | 关闭 TLS 校验等于引入中间人风险                          |

## 7. 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `error: externally-managed-environment` | PEP 668 阻止往系统 Python 装包 | `python -m venv .venv && source .venv/bin/activate`，或加 `--break-system-packages`（不推荐） |
| `Could not find a version that satisfies the requirement` | 版本约束无解 / 该版本没有匹配你平台或 Python 版本的 wheel | `pip index versions <pkg>` 看可用版本；放宽约束或升级 Python |
| `ERROR: Failed building wheel for xxx` | 无匹配 wheel，本地编译失败 | 装系统依赖（`build-essential`、Xcode CLT、`python3-dev`）；或换用提供 wheel 的版本 |
| `ResolutionImpossible: conflicting dependencies` | 传递依赖版本冲突 | 把冲突包放在**同一条** `pip install` 命令里让解析器全局求解；或用 `constraints.txt` 统一版本 |
| 下载超时 / `ReadTimeoutError` | 网络问题 | 换国内镜像源，或 `pip --timeout 60 --retries 5` |
| `SSL: CERTIFICATE_VERIFY_FAILED` | 证书问题（常见于公司代理、内网私服） | 配好 CA 证书；内网 HTTP 源才用 `trusted-host` |
| 装完仍 `ModuleNotFoundError` | 分发包名 ≠ import 名，或装到了别的解释器 | `pip show <pkg>` 确认位置；统一用 `python -m pip` |
| `pip` 命令不存在 | 解释器未带 pip 或未加进 PATH | 用 `python -m ensurepip --upgrade`，或 `python -m pip` |

## See Also

- [[09-virtual-environments|虚拟环境]]
- [[10-uv|uv 包管理器]]
- [[12-dependency-config|依赖管理配置文件]]
- [[index|Python 目录]]

## 参考

- [Python Packaging User Guide - Installing Packages](https://packaging.python.org/en/latest/tutorials/installing-packages/)
- [Python Packaging User Guide - Overview](https://packaging.python.org/en/latest/overview/)
- [pip 官方文档](https://pip.pypa.io/en/stable/)
- [PEP 668 - Marking Python base environments as externally managed](https://peps.python.org/pep-0668/)
- [PyPI 官方站点](https://pypi.org)
