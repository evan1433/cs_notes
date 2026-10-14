---
title: Git Worktree 多工作树使用指南
description: 用 git worktree 在同一仓库下并行检出多个分支，告别 stash 与反复 clone
tags:
  - git
  - devtools
  - workflow
date: 2026-10-13
---

> 适用于 Git 2.17+（本文命令在 **Git 2.56** 上实测验证）。要点：**一个分支同一时刻只能被一个工作树检出**。

# Git Worktree 多工作树使用指南

`git worktree` 允许在**同一个仓库**下同时检出多个分支到**不同的目录**，每个目录都有独立的工作区与暂存区，但共享同一份 `.git` 对象库。

它的价值在于解决传统单工作区切换分支的代价：不用 `git stash` 暂存半成品、不用重新 `git clone`（省磁盘、省 `npm install`、省 IDE 重新索引）。

| 方案 | 切换成本 | 磁盘占用 | 共享对象库 |
|------|---------|---------|-----------|
| `git checkout` 来回切 | 高（要 stash、要重建/重索引） | 1 份工作区 | 是 |
| 再 `git clone` 一份 | 无 | N 份完整仓库 | 否（要重新 fetch） |
| **`git worktree`** | 无（直接 `cd`） | N 份工作区，**只 1 份对象库** | 是 |

## 核心概念

### 主工作树与链接工作树

- **主工作树（main worktree）**：最初 `git clone` / `git init` 出来的那个目录，内含真正的 `.git` **目录**。
- **链接工作树（linked worktree）**：`git worktree add` 创建出来的目录，它里面的 `.git` 是一个**文件**，只有一行内容指向主仓库的管理目录：

```bash
$ cat ../wt-hotfix/.git
gitdir: /tmp/wt-demo/main-repo/.git/worktrees/wt-hotfix
```

### 共享什么、隔离什么

```
main-repo/.git/
├── HEAD  index  config  hooks/  objects/  refs/     # 所有工作树共享
└── worktrees/
    ├── wt-hotfix/   # 某个链接工作树的私有状态
    │   ├── HEAD        # 该工作树当前检出的分支
    │   ├── index       # 该工作树独立的暂存区
    │   └── gitdir      # 反向指回工作树目录
    └── wt-pay/
```

| 内容 | 是否共享 |
|------|---------|
| `objects/`（提交、blob） | ✅ 共享，所以创建工作树几乎不占额外空间 |
| `refs/heads/`、远程跟踪分支 | ✅ 共享 |
| `config`、hooks | ✅ 共享（`core.bare` 等少数项按工作树生效） |
| `HEAD`、暂存区 `index` | ❌ 每个工作树独立 |
| stash、rebase/bisect 中间状态 | ❌ 每个工作树独立 |

## 常用操作速查

| 场景 | 命令 | 说明 |
|------|------|------|
| 检出现有分支 | `git worktree add ../hotfix hotfix-login` | 最常用 |
| 新建分支并检出 | `git worktree add -b feature/pay ../pay` | 从当前 HEAD 拉新分支 |
| 从指定提交起新分支 | `git worktree add -b fix/x ../fix origin/main` | 第二个参数是起点 |
| 只看代码不建分支 | `git worktree add --detach ../review v1.2.0` | 游离 HEAD，适合看历史版本 |
| 查看所有工作树 | `git worktree list` | 加 `-v` 看 locked / prunable 标注 |
| 删除工作树 | `git worktree remove ../pay` | 目录 + 管理数据一起清掉 |
| 移动工作树 | `git worktree move ../pay ../new-pay` | 会自动修复内部路径 |
| 清理失效记录 | `git worktree prune` | 手动 `rm -rf` 目录后必做 |
| 防止被自动清理 | `git worktree lock ../hotfix` | 工作树放在移动硬盘/NAS 时用 |

## 命令详解

### `git worktree add`

**用途**：创建一个新的工作树并检出到指定目录。

```bash
# 已有分支：把 hotfix-login 检出到 ../wt-hotfix
git worktree add ../wt-hotfix hotfix-login

# 新建分支：基于当前 HEAD 创建 feature/pay，检出到 ../wt-pay
git worktree add -b feature/pay ../wt-pay

# 基于远程分支新建，并自动建立跟踪关系
git worktree add -b feature/pay --track ../wt-pay origin/main

# 游离 HEAD 检出某个 tag，用于临时看老版本代码
git worktree add --detach ../wt-v120 v1.2.0

# 只占位不检出文件（配合 sparse-checkout 用）
git worktree add --no-checkout ../wt-empty main
```

| 参数 | 说明 |
|------|------|
| `-b <branch>` | 创建新分支；分支已存在则报错 |
| `-B <branch>` | 创建或**重置**已有分支（会丢弃该分支原内容，慎用） |
| `--detach` / `-d` | 游离 HEAD，不占用分支名 |
| `-f` / `--force` | 强制检出已被其它工作树占用的分支 |
| `--lock` | 创建后立即锁定，可加 `--reason "原因"` |
| `--orphan` | 创建无历史的新生分支（Git 2.42+） |
| `--no-checkout` | 只建立工作树结构，不写工作区文件 |
| `--relative-paths` | `.git` 文件用相对路径，整个仓库目录搬家后仍可用 |
| `-q` | 静默，不输出进度 |

**注意事项**：

- 不指定 `<commit-ish>` 时默认基于当前 HEAD；给了 `-b` 且该名字能匹配到远程跟踪分支时，会自动建立跟踪关系（可用 `--no-track` 关闭）。
- 目录必须**不存在或为空**，且不要在仓库内部创建（否则会被当成未跟踪目录）。约定俗成放在仓库同级，如 `../myrepo-feature`。

### `git worktree list`

**用途**：列出所有工作树及其检出位置。

```bash
$ git worktree list
/tmp/wt-demo/main-repo f46a44a [master]
/tmp/wt-demo/wt-hotfix 78b4f0f [hotfix-login]
/tmp/wt-demo/wt-pay    f46a44a [feature/pay]

$ git worktree list --porcelain      # 脚本解析用
worktree /tmp/wt-demo/wt-hotfix
HEAD 78b4f0f0de38d6ce23525998f16907d07f55e6d8
branch refs/heads/hotfix-login
```

| 参数 | 说明 |
|------|------|
| `-v` | 显示 `locked`、`prunable` 及其原因 |
| `--porcelain` | 稳定机器可读格式 |
| `-z` | 记录以 NUL 结尾，配合 `xargs -0` |
| `--expire <time>` | 给缺失的工作树打 `prunable` 标记 |

### `git worktree remove`

**用途**：删除一个工作树（同时清掉 `.git/worktrees/<name>` 中的管理数据）。

```bash
git worktree remove ../wt-pay            # 干净的工作树
git worktree remove -f ../wt-pay         # 有未提交修改或已 lock 时强制删
```

**注意事项**：默认拒绝删除**有未提交修改**（dirty）或 **locked** 的工作树，这是防误删保护。`-f` 会丢弃这些修改，**不可恢复**。

### `git worktree move`

**用途**：把工作树挪到新路径，内部链接自动修复，无需手工改 `.git` 文件。

```bash
git worktree move ../wt-pay ../wt-pay-moved
```

**注意事项**：主工作树不能被 move；如果工作树处于锁状态需要先 `unlock`。

### `git worktree lock` / `unlock`

**用途**：给工作树加"保护锁"，避免它被 `prune` 误清理。典型场景是工作树放在**移动硬盘、NAS 或网络盘**上——设备没挂载时 git 会认为它"已消失"。

```bash
git worktree lock --reason "放在 NAS 上，勿删" ../wt-hotfix
git worktree list -v
# .../wt-hotfix  78b4f0f [hotfix-login]
#     locked: 放在 NAS 上，勿删
git worktree unlock ../wt-hotfix
```

### `git worktree prune`

**用途**：清理已经不存在的目录残留的管理记录。

```bash
git worktree prune -n -v     # 干跑，先看会删哪些（强烈推荐先跑这个）
git worktree prune           # 真正清理
git worktree prune --expire 7.days.ago
```

**注意事项**：如果你图省事直接 `rm -rf` 了工作树目录，git 不会自动感知，必须跑一次 `prune`，否则 `git worktree list` 会一直显示那条 `"prunable"` 的幽灵记录。

### `git worktree repair`

**用途**：修复断裂的双向链接。当**主仓库目录被移动**或**工作树目录被移动**（且没用 `move`）时，两边的路径都对不上了。

```bash
git worktree repair            # 在主仓库里执行，修复所有链接工作树
git worktree repair ../wt-a ../wt-b   # 只修复指定路径
```

## 典型场景

### 场景一：紧急 hotfix 打断当前开发

不用 stash、不用动当前工作区：

```bash
cd ~/code/myapp
git worktree add -b hotfix/order-timeout ../myapp-hotfix origin/main
cd ../myapp-hotfix
# 改代码、跑测试、提交、推送
git push -u origin hotfix/order-timeout
# 收工，回到原目录继续开发，工作区纹丝未动
cd ~/code/myapp
git worktree remove ../myapp-hotfix
```

### 场景二：并行跑两个需求分支 / 同时跑测试

一个目录在 IDE 里开发，另一个目录跑长时间集成测试，互不干扰：

```bash
git worktree add ../myapp-e2e feature/checkout
cd ../myapp-e2e && pnpm test:e2e      # 跑测试期间主目录照常开发
```

### 场景三：读老版本代码 / 做版本对比

```bash
git worktree add --detach ../myapp-v120 v1.2.0
diff -ru ../myapp-v120/src ./src | head
```

### 场景四：裸仓库 + worktree（CI / 服务器部署常用）

服务器上不需要工作区，只保留裸仓库，再按需要挂工作树：

```bash
git clone --bare git@github.com:me/myapp.git myapp.git
cd myapp.git
git worktree add /var/www/myapp-prod main      # 生产
git worktree add /var/www/myapp-staging staging # 预发
# 部署即：cd /var/www/myapp-prod && git pull --ff-only
```

这样每个环境目录是独立检出，互不影响，且只维护一份对象库。

### 场景五：多版本文档站并行构建

把不同 tag 各挂一个工作树，同时构建到不同输出目录（本仓库的 Quartz 站点就适合这么玩）：

```bash
git worktree add ../cs_notes-v1 v1.0.0
git worktree add ../cs_notes-v2 v2.0.0
```

## 进阶技巧

### 每个工作树用不同配置

先开启扩展，再用 `--worktree` 写入只对该工作树生效的配置（如不同提交邮箱）：

```bash
git config extensions.worktreeConfig true
git config --worktree user.email bot@example.com
git config --list --worktree | grep user.email   # user.email=bot@example.com
```

### 在脚本里批量处理

```bash
git worktree list --porcelain -z | while IFS= read -r -d '' line; do
  echo "$line"
done
```

### 配合稀疏检出处理大仓库

```bash
git worktree add --no-checkout ../mono-svc main
cd ../mono-svc
git sparse-checkout set services/order
git checkout
```

## 注意事项与坑

1. **同一分支不能被两个工作树同时检出**

```bash
$ git worktree add ../wt-dup hotfix-login
fatal: 'hotfix-login' is already used by worktree at '/tmp/wt-demo/wt-hotfix'
```

   需要的话用 `-f` 强制（第二个工作树会是"抢过来"的状态），或者改用 `--detach`。

2. **不要在工作树目录里再 `git worktree add` 到仓库内部**，会造成嵌套与路径混乱。放在仓库外部的同级目录最省心。

3. **子模块不会自动共享**：每个工作树要各自 `git submodule update --init --recursive`。

4. **IDE / 构建产物要隔离**：`node_modules`、`target/`、`.venv` 等每个工作树各一份；如果它们被 `.gitignore` 就不会互相污染，但要注意磁盘。

5. **删除前先确认没有未提交内容**：`git worktree remove` 会直接拒绝 dirty 的工作树，别习惯性加 `-f`。

6. **主工作树不能被删除或移动**，它是对象库所在。

## 排错对照表

| 报错 / 现象 | 含义 | 处理 |
|------------|------|------|
| `fatal: 'xxx' is already used by worktree at ...` | 该分支已在别的工作树检出 | 换分支、加 `-f`，或改用 `--detach` |
| `fatal: '<path>' already exists` | 目标目录非空 | 换路径或清空目录 |
| `fatal: '<path>' is a missing but locked worktree` | 目录没了但处于 lock 状态 | 先 `git worktree unlock <path>`，再 `prune` |
| `git worktree list` 里出现 `prunable` 幽灵条目 | 目录被手工删除，记录还在 | `git worktree prune -n -v` 确认后 `prune` |
| 移动主仓库后所有工作树失效 | `.git` 文件里的绝对路径断了 | 在主仓库执行 `git worktree repair` |
| `fatal: not a git repository` 在新目录里 | 该目录不是通过 worktree 创建的 | 用 `git worktree add` 重建 |

## 参考

- [Git 官方文档：git-worktree](https://git-scm.com/docs/git-worktree)
- [Git 官方文档：git sparse-checkout](https://git-scm.com/docs/git-sparse-checkout)
- 基础命令见 [[git|Git 常用命令]]
- 同类工具：[[tmux|Tmux]] 常与 worktree 搭配，一个终端窗格对应一个工作树
