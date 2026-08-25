---
title: Tmux 终端复用器使用指南
description: Tmux 的核心概念、会话管理、窗口与窗格操作、复制模式、常用配置和排错方法。
tags:
  - tmux
  - terminal
  - devtools
date: 2026-06-11
---
# Tmux 终端复用器使用指南

Tmux 是一个终端复用器（terminal multiplexer），可以在一个终端里管理多个会话、窗口和窗格。它最适合远程服务器开发、长任务运行、多项目切换和命令行工作区管理。

## 核心概念

Tmux 的层级关系如下：

```text
tmux server
└── session 会话：一个独立工作区，例如 project-api
    └── window 窗口：类似终端里的标签页，例如 editor、server、logs
        └── pane 窗格：一个窗口内的分屏终端
```

常用术语：

| 概念 | 说明 | 类比 |
| ------ | ------ | ------ |
| server | tmux 后台服务进程 | 管理所有工作区的后台程序 |
| session | 可分离、可恢复的工作环境 | 一个项目工作区 |
| window | session 内的标签页 | 浏览器标签页 |
| pane | window 内的分屏区域 | 分屏终端 |
| prefix | tmux 快捷键前缀，默认 `Ctrl+b` | 进入 tmux 控制模式 |

## 安装与启动

### 安装

```bash
# macOS
brew install tmux

# Ubuntu / Debian
sudo apt install tmux

# Fedora
sudo dnf install tmux

# CentOS / RHEL
sudo yum install tmux
```

### 启动

```bash
# 启动一个默认会话
tmux

# 启动并命名会话
tmux new -s dev

# 启动会话，并指定第一个窗口名称
tmux new -s dev -n editor
```

进入 tmux 后，快捷键通常都需要先按 `Ctrl+b`，松开后再按目标键。
例如 `Ctrl+b d` 表示：先按 `Ctrl+b`，松开，再按 `d`。

## 最常用工作流

### 远程服务器保活

```bash
# 1. 登录服务器
ssh user@example.com

# 2. 创建长期会话
tmux new -s train

# 3. 运行耗时任务
python train.py

# 4. 分离会话，任务继续在后台运行
# 快捷键：Ctrl+b d

# 5. 之后重新连接
tmux attach -t train
```

这个流程可以避免 SSH 断开后任务跟着终止。

### 项目开发工作区

```bash
tmux new -s api -n editor

# 在 tmux 中创建窗口和窗格：
# Ctrl+b c        新建窗口
# Ctrl+b ,        重命名窗口
# Ctrl+b %        左右分屏
# Ctrl+b "        上下分屏
# Ctrl+b d        暂时离开
```

推荐窗口组织方式：

| 窗口 | 用途 |
| ------ | ------ |
| `editor` | 编辑器或文件操作 |
| `server` | 开发服务、构建命令 |
| `logs` | 日志、监控、测试 |
| `shell` | 临时命令 |

## 会话管理

### 命令速查

| 操作 | 命令 |
| ------ | ------ |
| 新建会话 | `tmux new -s <session>` |
| 后台新建会话 | `tmux new -d -s <session>` |
| 查看会话 | `tmux ls` |
| 连接会话 | `tmux attach -t <session>` |
| 切换会话 | `tmux switch -t <session>` |
| 重命名会话 | `tmux rename-session -t <old> <new>` |
| 杀死会话 | `tmux kill-session -t <session>` |
| 杀死所有会话 | `tmux kill-server` |

### 常用示例

```bash
# 创建名为 blog 的会话
tmux new -s blog

# 连接最近使用的会话
tmux attach

# 连接指定会话
tmux attach -t blog

# 在后台创建会话并执行命令
tmux new -d -s job 'python script.py'

# 杀死指定会话
tmux kill-session -t blog
```

### 会话快捷键

| 快捷键 | 作用 |
| -------- | ------ |
| `Ctrl+b d` | 分离当前会话 |
| `Ctrl+b s` | 列出并切换会话 |
| `Ctrl+b $` | 重命名当前会话 |
| `Ctrl+b (` | 切换到上一个会话 |
| `Ctrl+b )` | 切换到下一个会话 |

## 窗口管理

窗口适合承载不同任务，例如编辑、运行服务、查看日志。

| 快捷键                     | 作用        |
| ----------------------- | --------- |
| `Ctrl+b c`              | 新建窗口      |
| `Ctrl+b ,`              | 重命名当前窗口   |
| `Ctrl+b &`              | 关闭当前窗口    |
| `Ctrl+b n`              | 下一个窗口     |
| `Ctrl+b p`              | 上一个窗口     |
| `Ctrl+b 0` 到 `Ctrl+b 9` | 切换到指定编号窗口 |
| `Ctrl+b w`              | 列出并选择窗口   |
| `Ctrl+b f`              | 按名称搜索窗口   |

命令方式：

```bash
# 在指定会话中新建窗口
tmux new-window -t dev -n logs

# 重命名当前窗口
tmux rename-window server

# 关闭指定窗口
tmux kill-window -t dev:logs
```

## 窗格管理

窗格适合在同一个窗口中同时看编辑器、服务和日志。

### 分屏与切换

| 快捷键 | 作用 |
| -------- | ------ |
| `Ctrl+b %` | 左右分屏 |
| `Ctrl+b "` | 上下分屏 |
| `Ctrl+b 方向键` | 切换窗格 |
| `Ctrl+b o` | 切换到下一个窗格 |
| `Ctrl+b ;` | 切换到上一个活跃窗格 |
| `Ctrl+b q` | 显示窗格编号 |
| `Ctrl+b q` 后按数字 | 跳转到指定窗格 |

### 调整与关闭

| 快捷键 | 作用 |
| -------- | ------ |
| `Ctrl+b z` | 当前窗格全屏或还原 |
| `Ctrl+b x` | 关闭当前窗格 |
| `Ctrl+b !` | 将当前窗格拆成新窗口 |
| `Ctrl+b {` | 当前窗格向前移动 |
| `Ctrl+b }` | 当前窗格向后移动 |
| `Ctrl+b Space` | 切换布局 |
| `Ctrl+b Ctrl+方向键` | 调整窗格大小 |

命令方式：

```bash
# 左右分屏
tmux split-window -h

# 上下分屏
tmux split-window -v

# 在新窗格中运行命令
tmux split-window -h 'tail -f app.log'

# 关闭当前窗格
tmux kill-pane
```

## 复制模式

Tmux 有自己的历史滚动和复制模式，常用于查看远程日志或复制命令输出。

| 快捷键 | 作用 |
| -------- | ------ |
| `Ctrl+b [` | 进入复制模式 |
| `q` | 退出复制模式 |
| `Space` | 开始选择文本 |
| `Enter` | 复制选中文本 |
| `Ctrl+b ]` | 粘贴 tmux 缓冲区内容 |

如果开启了 vi 模式，复制模式更接近 Vim：

```tmux
setw -g mode-keys vi
```

常用 vi 操作：

| 按键 | 作用 |
| ------ | ------ |
| `h` `j` `k` `l` | 移动光标 |
| `/` | 搜索 |
| `n` | 下一个搜索结果 |
| `N` | 上一个搜索结果 |
| `v` | 开始选择 |
| `y` | 复制 |

## 命令模式

按 `Ctrl+b :` 可以进入 tmux 命令模式，直接输入 tmux 命令。

```tmux
# 重命名当前窗口
rename-window logs

# 开启鼠标
set -g mouse on

# 重新加载配置
source-file ~/.tmux.conf
```

命令模式适合临时调整配置，也适合验证 `.tmux.conf` 中的写法。

## 配置文件

Tmux 默认读取 `~/.tmux.conf`。修改后可以用 `Ctrl+b :` 执行 `source-file ~/.tmux.conf` 重新加载。

### 推荐基础配置

```tmux
# 将 prefix 从 Ctrl+b 改为 Ctrl+a，更接近 screen，也更容易按
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# 开启鼠标，支持点击切换窗格、拖拽调整大小、滚轮查看历史
set -g mouse on

# 使用 vi 风格复制模式
setw -g mode-keys vi

# 增加历史滚动行数
set -g history-limit 10000

# 窗口和窗格编号从 1 开始，便于键盘选择
set -g base-index 1
setw -g pane-base-index 1

# 自动重新编号窗口，避免关闭窗口后编号中断
set -g renumber-windows on

# 重新加载配置
bind r source-file ~/.tmux.conf \; display-message "tmux config reloaded"

# 更直观的分屏快捷键
bind | split-window -h
bind - split-window -v

# 使用 Vim 风格方向键切换窗格
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R
```

配置生效：

```bash
tmux source-file ~/.tmux.conf
```

## 自动化工作区

Tmux 可以用命令脚本快速恢复项目布局。

```bash
#!/usr/bin/env bash

SESSION="api"

tmux new-session -d -s "$SESSION" -n editor
tmux send-keys -t "$SESSION:editor" "nvim ." C-m

tmux new-window -t "$SESSION" -n server
tmux send-keys -t "$SESSION:server" "npm run dev" C-m

tmux new-window -t "$SESSION" -n logs
tmux split-window -h -t "$SESSION:logs"
tmux send-keys -t "$SESSION:logs.1" "tail -f logs/app.log" C-m

tmux attach -t "$SESSION"
```

保存为 `dev-tmux.sh` 后执行：

```bash
chmod +x dev-tmux.sh
./dev-tmux.sh
```

## 常见问题

### SSH 断开后任务还在吗

如果任务运行在 tmux 会话里，并且只是 SSH 断开或执行了 `Ctrl+b d` 分离会话，任务会继续运行。重新登录后执行：

```bash
tmux ls
tmux attach -t <session>
```

### 如何退出 tmux

退出当前 shell：

```bash
exit
```

或按 `Ctrl+d`。如果窗口里所有窗格都退出，对应窗口会关闭；如果会话里所有窗口都关闭，会话结束。

### 为什么快捷键没有反应

先确认是否在 tmux 中：

```bash
echo "$TMUX"
```

如果输出为空，说明当前 shell 不在 tmux 内。还要确认 prefix 是否被 `.tmux.conf` 改过，例如从默认 `Ctrl+b` 改成了 `Ctrl+a`。

### 误按进入复制模式怎么办

按 `q` 退出复制模式。

### 如何查看所有快捷键

```bash
tmux list-keys
```

也可以在 tmux 内按 `Ctrl+b ?` 查看快捷键列表。

### 如何让鼠标滚轮直接滚动历史

在 `~/.tmux.conf` 中开启鼠标：

```tmux
set -g mouse on
```

重新加载：

```bash
tmux source-file ~/.tmux.conf
```

## 快速备忘

| 场景 | 操作 |
| ------ | ------ |
| 创建项目会话 | `tmux new -s project` |
| 暂时离开 | `Ctrl+b d` |
| 恢复现场 | `tmux attach -t project` |
| 新建窗口 | `Ctrl+b c` |
| 分屏 | `Ctrl+b %` 或 `Ctrl+b "` |
| 切换窗格 | `Ctrl+b 方向键` |
| 当前窗格全屏 | `Ctrl+b z` |
| 查看历史输出 | `Ctrl+b [` |
| 重载配置 | `tmux source-file ~/.tmux.conf` |

## tmux 常用命令速查表
---

为你整理了一份 **tmux 常用命令速查表**，分为**快捷键**（Prefix键默认为 `Ctrl+b`）和**终端命令行**两部分，方便快速查阅：

---

### 🎮 快捷键操作（会话与窗口管理）

| 功能           | 快捷键                                                            | 说明             |
| :----------- | :------------------------------------------------------------- | :------------- |
| **会话管理**     |                                                                |                |
| 新建会话         | `tmux new -s <名称>`                                             | 命令行操作，创建并进入新会话 |
| 重命名会话        | `Prefix + $`                                                   | 修改当前会话的名称      |
| 断开当前会话       | `Prefix + d`                                                   | 保持会话后台运行，返回终端  |
| 查看会话列表       | `Prefix + s`                                                   | 用列表选择并切换会话     |
| **窗口管理**     |                                                                |                |
| 新建窗口         | `Prefix + c`                                                   | 创建新窗口          |
| 关闭当前窗口       | `Prefix + &`                                                   | 需按 `y` 确认      |
| 切换窗口         | `Prefix + n`（下一个）<br>`Prefix + p`（上一个）<br>`Prefix + 0-9`（编号跳转） | 快速切换           |
| 查看窗口列表       | `Prefix + w`                                                   | 用列表选择窗口        |
| **窗格（面板）管理** |                                                                |                |
| 垂直分割         | `Prefix + %`                                                   | 左右分割出新的窗格      |
| 水平分割         | `Prefix + "`                                                   | 上下分割出新的窗格      |
| 切换窗格         | `Prefix + 方向键`                                                 | 在相邻窗格间切换焦点     |
| 关闭当前窗格       | `Prefix + x`                                                   | 需按 `y` 确认      |
| 缩放/还原窗格      | `Prefix + z`                                                   | 当前窗格全屏，再按一次恢复  |
| 调整窗格大小       | `Prefix + Ctrl + 方向键`                                          | 以 5 个单元格为单位调整  |
| **其他实用操作**   |                                                                |                |
| 进入复制模式       | `Prefix + [`                                                   | 可用方向键滚动浏览历史输出  |
| 粘贴内容         | `Prefix + ]`                                                   | 粘贴复制模式中选中的内容   |
| 显示帮助         | `Prefix + ?`                                                   | 列出所有快捷键        |

---

### 🖥️ 终端命令行操作

| 功能 | 命令 | 说明 |
| :--- | :--- | :--- |
| **会话操作** | | |
| 列出所有会话 | `tmux ls` | 显示每个会话的名称、窗口数、状态 |
| 创建新会话 | `tmux new -s <名称>` | 可加 `-d` 参数在后台创建 |
| 附着（进入）会话 | `tmux attach -t <名称或编号>` | 进入指定会话 |
| 重命名会话 | `tmux rename-session -t <旧名> <新名>` | 对任意会话生效（包括后台的） |
| 杀死会话 | `tmux kill-session -t <名称>` | 彻底结束指定会话及其中所有窗口 |
| 杀死所有会话 | `tmux kill-server` | 关闭所有 tmux 会话 |
| **窗口操作** | | |
| 在指定会话中新建窗口 | `tmux new-window -t <会话名>` | 可加 `-n <窗口名>` 命名 |
| 重命名窗口 | `tmux rename-window -t <会话名:窗口名> <新名称>` | 或在窗口中用 `Prefix + ,` |
| **窗格操作** | | |
| 按比例分割窗格 | `tmux split-window -h -p 30 -t <会话名:窗口名>` | `-h` 水平，`-p` 指定百分比 |

---

### 📌 实用技巧
- **批量重命名**：如果需要按规则统一修改会话名称，可以结合 `tmux ls` 和 `awk` 等工具写脚本。
- **配置个性化**：可以修改 `~/.tmux.conf` 文件，将默认的 `Prefix` 键改为更方便的 `Ctrl+a`（类似 screen 风格）。

如果你需要更详细的配置或进阶用法（例如自定义状态栏、保存会话等），随时告诉我～😊


## 参考资料

- [Tmux 使用教程](https://www.ruanyifeng.com/blog/2019/10/tmux.html)
- [tmux GitHub 仓库](https://github.com/tmux/tmux)
- [tmux man page](https://man7.org/linux/man-pages/man1/tmux.1.html)
- [tmux wiki get-started](https://github.com/tmux/tmux/wiki/Getting-Started)
- [tmux man page](https://man.openbsd.org/OpenBSD-current/man1/tmux.1)
