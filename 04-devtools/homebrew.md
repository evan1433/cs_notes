---
title: macOS Homebrew 使用指南
description: 介绍 Homebrew 的核心概念、安装方法、常用命令、服务管理、Brewfile 与故障排查
tags:
  - devtools
  - homebrew
  - package-manager
date: 2026-07-24
aliases:
  - brew
  - mac-brew
---

# macOS Homebrew 使用指南

Homebrew 是 macOS 上常用的包管理器，用于安装、升级和卸载命令行工具、编程语言、
数据库以及桌面应用。它把软件及其依赖统一交给 `brew` 命令管理，避免手动下载、
解压和维护版本。

典型用途包括：

- 安装命令行工具，例如 Git、wget、tree 和 jq。
- 安装开发环境，例如 Node.js、Python、Go 和 OpenJDK。
- 安装桌面应用，例如 Visual Studio Code、iTerm2 和 Google Chrome。
- 管理 PostgreSQL、Redis 等后台服务。
- 使用 `Brewfile` 记录软件清单，在新 Mac 上快速恢复开发环境。

## 核心概念

| 概念 | 含义 | 示例 |
|------|------|------|
| Formula | 通常表示命令行工具、库或服务的软件包定义 | `git`、`node`、`redis` |
| Cask | 通常表示带图形界面的 macOS 应用或字体 | `visual-studio-code`、`font-fira-code` |
| Tap | 软件仓库，用于提供额外的 Formula、Cask 或 `brew` 子命令 | `user/repository` |
| Bottle | Homebrew 提供的预编译二进制包 | 某个 macOS 版本的 `wget` 二进制包 |
| Keg | 某个软件版本实际安装到 Cellar 后形成的目录 | `Cellar/wget/1.25.0` |
| Cellar | Formula 的实际安装目录 | `/opt/homebrew/Cellar` |
| Prefix | Homebrew 的安装前缀，也是命令和配置的主要入口 | Apple Silicon 为 `/opt/homebrew` |

Homebrew 默认先把每个 Formula 安装到独立的 Keg，再把需要使用的命令链接到
`$(brew --prefix)/bin`。因此可以用统一的命令查看安装位置，而不必在脚本中写死
Apple Silicon 或 Intel Mac 的路径。

```bash
# 查看当前 Mac 上 Homebrew 的安装前缀
brew --prefix

# 查看某个 Formula 的安装前缀
brew --prefix node

# 查看 Homebrew 的下载缓存目录
brew --cache
```

## 安装 Homebrew

### 安装要求

根据 Homebrew 官方文档，当前受支持的 macOS 安装需要：

- Apple Silicon 或 64 位 Intel 处理器。
- 受支持版本的 macOS。
- Xcode Command Line Tools 或 Xcode。
- 用于执行安装脚本的 Bash。

具体支持的 macOS 版本会随 Homebrew 更新，应以
[Installation](https://docs.brew.sh/Installation) 和
[Support Tiers](https://docs.brew.sh/Support-Tiers) 为准。

### 安装步骤

先安装 Xcode Command Line Tools：

```bash
xcode-select --install
```

从 [Homebrew 官网](https://brew.sh/) 获取并执行官方安装命令：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

该脚本会先说明准备执行的操作，并在真正安装前等待确认。脚本需要联网，并可能在
安装阶段请求管理员密码。安装完成后，日常执行 `brew install` 不应再加 `sudo`。

> **安全提示**：执行从网络下载的脚本前，应确认域名和脚本来源。对安全要求较高时，
> 可以先下载并阅读脚本内容，再执行本地文件。

### 配置 Shell 环境

安装程序最后会输出 `Next steps`。应优先复制它给出的命令，因为命令会根据当前
Mac 的架构和 Shell 自动生成。

Apple Silicon Mac 的默认安装前缀为 `/opt/homebrew`，Zsh 通常可这样配置：

```bash
# 写入登录 Shell 配置，使以后打开的终端都能找到 brew
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile

# 让当前终端立即生效
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Intel Mac 的默认安装前缀为 `/usr/local`：

```bash
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/usr/local/bin/brew shellenv)"
```

可以用下面的命令确认处理器架构：

```bash
uname -m
```

- 输出 `arm64` 表示当前 Shell 原生运行在 Apple Silicon 上。
- 输出 `x86_64` 通常表示 Intel Mac，或 Apple Silicon 上的 Rosetta 终端。

不要为了“统一路径”而把 Homebrew 安装到非默认目录。默认前缀可以使用大多数
Bottle；非默认目录可能触发耗时且更容易失败的源码编译。

### 验证安装

```bash
# 查看版本，确认命令已经加入 PATH
brew --version

# 查看 Homebrew、Ruby、Git、处理器和安装路径等信息
brew config

# 检查可能影响 Homebrew 的系统配置问题
brew doctor
```

`brew doctor` 输出警告不一定表示 Homebrew 无法使用。遇到安装或升级问题时，应
结合具体警告处理，不要盲目修改系统目录权限。

## 查找与了解软件

安装前先搜索并查看详情，可以确认软件名称、类型、版本、依赖和安装注意事项。

```bash
# 同时搜索 Formula 和 Cask
brew search ripgrep

# 查看 Formula 的版本、依赖、安装选项和注意事项
brew info node

# 明确查看 Cask 信息
brew info --cask visual-studio-code

# 在浏览器中打开 Homebrew 官网
brew home
```

也可以直接使用 [Homebrew Formulae](https://formulae.brew.sh/) 网站搜索软件。

## 安装软件

### 安装 Formula

```bash
# 安装单个命令行工具
brew install wget

# 一次安装多个开发工具
brew install git jq ripgrep

# 安装带版本后缀的 Formula
brew install postgresql@17
```

安装结束后要留意终端中的 `Caveats`。它可能包含 PATH 配置、初始化数据库、
启动服务或版本切换等必要说明。之后也可以重新查看：

```bash
brew info postgresql@17
```

### 安装 Cask

```bash
# 安装 macOS 桌面应用
brew install --cask visual-studio-code

# 一次安装多个桌面应用
brew install --cask iterm2 rectangle
```

Cask 通常会把应用安装到 `/Applications`。部分安装器可能请求管理员权限，
这与直接使用 `sudo brew install` 不同。

### 查看已安装的软件

```bash
# 查看所有已安装的 Formula
brew list --formula

# 查看所有已安装的 Cask
brew list --cask

# 只查看用户主动安装、而不是作为依赖安装的 Formula
brew leaves

# 查看某个 Formula 安装了哪些文件
brew list wget

# 查看某个命令来自哪里
command -v wget
```

## 更新与升级

`update` 和 `upgrade` 的作用不同：

- `brew update` 更新 Homebrew 自身及可用软件的元数据。
- `brew upgrade` 把已经安装的软件升级到当前可用版本。

推荐的维护流程如下：

```bash
# 1. 更新 Homebrew 和软件元数据
brew update

# 2. 查看哪些软件可以升级
brew outdated

# 3. 升级所有已安装的软件
brew upgrade

# 4. 删除旧版本和过期缓存
brew cleanup

# 5. 检查环境是否健康
brew doctor
```

只升级指定软件时：

```bash
brew upgrade node
brew upgrade --cask visual-studio-code
```

需要暂时阻止某个 Formula 被 `brew upgrade` 更新时，可以使用：

```bash
# 固定当前版本
brew pin postgresql@17

# 查看已固定的 Formula
brew list --pinned

# 恢复正常升级
brew unpin postgresql@17
```

Homebrew 是滚动更新的包管理器，不适合长期管理任意旧版本。项目若要求严格的
运行时版本，通常应配合语言专用版本管理工具，例如 `fnm`、`pyenv` 或 `mise`。

## 卸载与清理

```bash
# 卸载 Formula
brew uninstall wget

# 卸载 Cask
brew uninstall --cask rectangle

# 预览不再需要的依赖，不做实际删除
brew autoremove --dry-run

# 删除不再被其他软件依赖的 Formula
brew autoremove

# 预览 cleanup 将删除的内容
brew cleanup --dry-run

# 删除旧版本、过期下载和陈旧锁文件
brew cleanup
```

对 Cask 使用 `--zap` 可能额外删除关联的偏好设置和支持文件：

```bash
brew uninstall --cask --zap rectangle
```

`--zap` 的清理范围由具体 Cask 定义，可能包含用户配置。执行前应先备份需要保留的
数据，不要把它当作默认卸载方式。

## 管理后台服务

数据库、缓存和消息队列等 Formula 可以通过 `brew services` 接入 macOS 的
`launchctl`，实现后台运行和登录时自动启动。

以 Redis 为例：

```bash
# 安装 Redis
brew install redis

# 启动 Redis，并注册为当前用户登录时自动启动
brew services start redis

# 查看 Homebrew 管理的所有服务
brew services list

# 重启服务，使配置变更生效
brew services restart redis

# 停止服务，并取消自动启动
brew services stop redis
```

如果只想在当前终端临时运行服务，可以直接执行 Formula 提供的命令，而不注册
登录启动项：

```bash
redis-server
```

通常不要使用 `sudo brew services`。不带 `sudo` 时服务属于当前用户并在登录时
启动；带 `sudo` 会创建系统级服务，权限、配置目录和运行时机都会不同。

## 使用 Brewfile 复现开发环境

`Brewfile` 是 Homebrew Bundle 使用的软件清单。它适合加入 dotfiles 仓库或项目
仓库，让新电脑或团队成员用一个命令安装一致的基础工具。

下面是一个可用的 `Brewfile`：

```ruby
# 命令行工具
brew "git"
brew "jq"
brew "ripgrep"
brew "node"

# macOS 桌面应用
cask "visual-studio-code"
cask "iterm2"

# 安装 Redis，并在安装或版本变化后重启服务
brew "redis", restart_service: :changed
```

在 `Brewfile` 所在目录执行：

```bash
# 安装或升级清单中的软件；已满足的项目不会重复安装
brew bundle

# 只检查当前环境是否满足清单，不做修改
brew bundle check
```

把当前已经安装的软件导出为全局清单：

```bash
# --force 表示覆盖已经存在的全局 Brewfile
brew bundle dump --global --force

# 在另一台 Mac 上按全局 Brewfile 恢复环境
brew bundle --global
```

`Brewfile` 描述期望安装的软件，但不是带精确版本锁定的 lock 文件。它适合复现
工具集合，不保证每台电脑安装完全相同的历史版本。更多用法参见
[Homebrew Bundle 官方文档](https://docs.brew.sh/Brew-Bundle-and-Brewfile)。

## Tap 与第三方仓库

Tap 可以扩展 Homebrew 的软件来源：

```bash
# 查看已经添加的 Tap
brew tap

# 添加第三方 Tap
brew tap user/repository

# 使用完整名称安装其中的 Formula
brew install user/repository/tool

# 不再需要时移除 Tap
brew untap user/repository
```

第三方 Tap 中的软件定义和安装逻辑会以当前用户权限运行。添加前应确认维护者、
源码地址和可信度；优先使用完整名称安装需要的单个软件，不要随意信任未知 Tap。
详见 [Taps 官方文档](https://docs.brew.sh/Taps)。

## 常见问题

### 提示 `brew: command not found`

先确认 Homebrew 是否存在：

```bash
# Apple Silicon
test -x /opt/homebrew/bin/brew && /opt/homebrew/bin/brew --version

# Intel
test -x /usr/local/bin/brew && /usr/local/bin/brew --version
```

如果能输出版本，说明只是 Shell 没有加载 Homebrew 环境。重新执行安装程序给出的
`brew shellenv` 命令，并检查 `~/.zprofile` 是否正确。配置 Shell 的更多信息参见
[[zsh|Zsh 配置文件加载顺序]]。

### Apple Silicon 上出现架构混用

先检查当前终端和 `brew` 的架构与路径：

```bash
uname -m
which -a brew
file "$(which brew)"
brew --prefix
```

Apple Silicon 原生 Homebrew 的前缀应为 `/opt/homebrew`。如果当前终端通过
Rosetta 运行，`uname -m` 可能显示 `x86_64`，并调用 `/usr/local` 下的 Intel
Homebrew。除非确实需要 Intel 软件，否则应使用原生终端和 `/opt/homebrew`。

### 软件已经安装，但命令仍然找不到

先查看 `Caveats` 和安装路径：

```bash
brew info openjdk
brew --prefix openjdk
```

一些 Formula 是 `keg-only`，Homebrew 不会自动把它们链接到公共 `bin` 目录，以免
覆盖 macOS 自带软件或与其他版本冲突。应按 `brew info` 的提示设置 PATH，不要在
不了解影响时强制执行 `brew link --force`。

### `brew doctor` 报告权限问题

不要直接对 `/usr/local` 或 `/opt/homebrew` 整棵目录执行宽泛的 `chmod`、`chown`。
先运行：

```bash
brew doctor
brew config
```

根据输出定位具体目录，并对照
[Troubleshooting](https://docs.brew.sh/Troubleshooting) 处理。Homebrew 日常命令
不应使用 `sudo`，权限异常通常需要修复安装归属，而不是长期提升权限运行。

### 下载失败或更新很慢

先确认 GitHub、Homebrew API 和目标软件源是否可访问，再重试：

```bash
# 输出更详细的执行过程，便于定位失败阶段
brew update --verbose

# 检查 Homebrew 环境
brew doctor
```

不要复制来源不明的镜像配置。镜像仓库或二进制包一旦被替换，可能直接执行恶意
代码；如确需镜像，应使用可信机构提供的地址，并了解如何恢复官方源。

## 常用命令速查

| 任务 | 命令 |
|------|------|
| 查看帮助 | `brew help`、`brew help install` |
| 查看版本与配置 | `brew --version`、`brew config` |
| 搜索软件 | `brew search <关键词>` |
| 查看详情 | `brew info <名称>` |
| 安装 Formula | `brew install <名称>` |
| 安装 Cask | `brew install --cask <名称>` |
| 查看已安装软件 | `brew list --formula`、`brew list --cask` |
| 更新元数据 | `brew update` |
| 查看可升级软件 | `brew outdated` |
| 升级软件 | `brew upgrade [名称]` |
| 卸载软件 | `brew uninstall <名称>` |
| 清理旧版本和缓存 | `brew cleanup` |
| 检查环境 | `brew doctor` |
| 管理服务 | `brew services list` |
| 按清单安装 | `brew bundle` |

命令参数可能随版本变化。遇到不确定的选项时，优先查看当前安装版本自带的帮助：

```bash
brew help
brew help install
brew help services
man brew
```

## 参考资料

- [Homebrew 官网](https://brew.sh/)
- [Homebrew 官方文档](https://docs.brew.sh/)
- [Homebrew 命令手册](https://docs.brew.sh/Manpage)
- [Homebrew FAQ](https://docs.brew.sh/FAQ)
- [Homebrew Formulae](https://formulae.brew.sh/)
- [[zsh|Zsh 配置文件加载顺序]]
