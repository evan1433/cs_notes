---
title: rsync 使用文档
description: rsync 增量同步原理、常用选项、过滤规则与备份/部署实战示例
tags:
  - rsync
  - linux
  - devops
  - backup
date: 2026-11-03
reference: https://download.samba.org/pub/rsync/rsync.1
---

# rsync 使用文档

`rsync`（remote sync）是 Linux/Unix 下最常用的**文件同步与增量传输**工具。它只传输源与目标之间的**差异部分**，
因此无论是本地拷贝、服务器之间迁移数据，还是定时增量备份，效率都远高于 `cp` / `scp`。

- [rsync 官方文档（man page）](https://download.samba.org/pub/rsync/rsync.1)
- [rsync 官网](https://rsync.samba.org/)
- [Arch Wiki: rsync](https://wiki.archlinux.org/title/Rsync)

## 目录

1. [核心特性与工作原理](#1-核心特性与工作原理)
2. [安装与版本](#2-安装与版本)
3. [命令语法](#3-命令语法)
4. [斜杠陷阱：必须搞懂的第一件事](#4-斜杠陷阱必须搞懂的第一件事)
5. [常用选项速查](#5-常用选项速查)
6. [`-a` 归档模式到底包含什么](#6--a-归档模式到底包含什么)
7. [试运行与输出解读](#7-试运行与输出解读)
8. [`--delete`：镜像同步与数据安全](#8---delete镜像同步与数据安全)
9. [过滤规则：exclude / include / filter](#9-过滤规则exclude--include--filter)
10. [远程同步：SSH 与守护进程模式](#10-远程同步ssh-与守护进程模式)
11. [断点续传、限速与进度](#11-断点续传限速与进度)
12. [增量快照备份：`--link-dest`](#12-增量快照备份--link-dest)
13. [典型场景实战](#13-典型场景实战)
14. [退出码](#14-退出码)
15. [常见坑与排错](#15-常见坑与排错)
16. [rsync vs scp vs cp](#16-rsync-vs-scp-vs-cp)

---

## 1. 核心特性与工作原理

### 1.1 为什么快：delta-transfer 算法

rsync 的核心不是"重新传一遍文件"，而是**只传变化的那部分字节**：

```text
源端 ──(1) 文件列表 + quick check 元数据──> 比对
     ──(2) 对变化文件做滚动校验（rolling checksum）──> 定位差异块
     ──(3) 仅传输差异块 + 字面数据──> 目标端重组文件
```

1. **Quick check（快速检查）**：默认按 `文件大小 + 修改时间（mtime）` 判断文件是否"相同"，相同则直接跳过。
   加 `-c` 后改用 checksum 比对，更准但更慢（需要读两边全部内容）。
2. **Delta transfer**：对需要同步的文件，两端分块计算校验和，只传输目标端没有的块。
   因此给一个大日志追加 1MB，rsync 不会重传整个文件。
3. **传输前压缩**：`-z` 在传输过程中压缩，适合跨公网、带宽受限的场景（局域网一般不开，白费 CPU）。

### 1.2 三种工作模式

| 模式 | 示例 | 说明 |
|------|------|------|
| 本地同步 | `rsync -av /src/ /dst/` | 类似 `cp -a`，但支持增量与过滤 |
| 远程同步（SSH） | `rsync -av /src/ user@host:/dst/` | 走 SSH 通道，最常用，**推荐** |
| 守护进程模式 | `rsync -av /src/ user@host::module` | 走 rsync 自有 873 端口，适合做公共镜像站 |

> **记忆要点**：判断是不是远程，看路径里有没有 `:`。
> 单冒号 `host:/path` = SSH 模式；双冒号 `host::module` = 守护进程模式。

---

## 2. 安装与版本

```bash
# Debian / Ubuntu
sudo apt install rsync

# RHEL / CentOS / Rocky
sudo dnf install rsync    # 或 yum install rsync

# macOS（系统自带 2.6.9，较老；建议用 Homebrew 装新版）
brew install rsync
```

```bash
rsync --version   # 查看版本，注意 protocol version
```

> macOS 自带版本是 2.6.9（2008 年），缺少 `--info=progress2` 等新特性。
> Homebrew 安装的 3.x 位于 `/opt/homebrew/bin/rsync`（Intel 机器是 `/usr/local/bin/rsync`），注意 PATH 优先级。

---

## 3. 命令语法

```text
rsync [OPTION...] SRC... [DEST]
```

等价于 `cp` 的直觉：`rsync 选项 源 目标`。

```bash
# 本地：把 src 目录同步成 dst 目录
rsync -av /data/src/ /data/dst/

# 本地 → 远程（推 push）
rsync -av /data/src/ user@10.0.0.5:/data/dst/

# 远程 → 本地（拉 pull）
rsync -av user@10.0.0.5:/data/src/ /data/dst/
```

**方向术语**：
- **push（推）**：本地是源，远端是目标 → 上传。
- **pull（拉）**：远端是源，本地是目标 → 下载。

---

## 4. 斜杠陷阱：必须搞懂的第一件事

**源路径末尾的斜杠，决定"拷目录本身"还是"拷目录里的内容"**，这是新手最常踩的坑。

```bash
rsync -av /data/src  /data/dst/    # 无斜杠：结果是 /data/dst/src/...
rsync -av /data/src/ /data/dst/    # 有斜杠：结果是 /data/dst/...（src 的内容被铺开）
```

| 命令 | 结果 |
|------|------|
| `rsync -a /src /dst/` | 生成 `/dst/src`，把整个目录搬过去 |
| `rsync -a /src/ /dst/` | `/dst` 成为 `/src` 的**镜像**，不额外多一层 |

**目标路径的斜杠不影响语义**，但建议始终写上，明确表示"这是个目录"。

> **实践建议**：做镜像同步时，源和目标都带尾斜杠：`rsync -av /src/ /dst/`。

---

## 5. 常用选项速查

### 5.1 几乎每次都写

| 选项 | 含义 |
|------|------|
| `-a` / `--archive` | 归档模式，等价于 `-rlptgoD`（见 [第 6 节](#6--a-归档模式到底包含什么)） |
| `-v` / `--verbose` | 输出详细信息 |
| `-z` / `--compress` | 传输时压缩（跨公网建议开，局域网不开） |
| `-P` | 等价于 `--partial --progress`，断点续传 + 进度条 |
| `-n` / `--dry-run` | **试运行**，只打印将要做什么，不真写（强烈建议先跑一遍） |
| `-h` / `--human-readable` | 数字以 K/M/G 显示 |

### 5.2 控制同步行为

| 选项 | 含义 |
|------|------|
| `--delete` | 删除目标端"源端已没有"的文件，使目标成为源的严格镜像 |
| `--delete-before` | 传输前先删除（默认策略之一，适合磁盘紧张） |
| `--delete-during` / `--del` | 传输过程中删除（默认） |
| `--delete-after` | 传输完成后再删除（最安全，中途失败也不会提前删数据） |
| `--delete-excluded` | 连目标端"被 exclude 规则排除"的文件也一并删除 |
| `-u` / `--update` | 跳过目标端**更新**的文件（按 mtime 判断） |
| `--ignore-existing` | 跳过目标端**已存在**的文件（只补缺，不覆盖） |
| `-c` / `--checksum` | 用校验和而非"大小+mtime"判断差异 |
| `--size-only` | 只按文件大小判断差异（忽略时间） |
| `-I` / `--ignore-times` | 忽略 quick check，强制重传所有文件 |
| `--existing` | 只更新目标端已存在的文件，不创建新文件 |
| `--max-size=SIZE` / `--min-size=SIZE` | 按文件大小过滤，如 `--max-size=100M` |

### 5.3 权限与属性

| 选项 | 含义 |
|------|------|
| `-r` / `--recursive` | 递归目录 |
| `-l` / `--links` | 保留软链接（不跟随） |
| `-L` / `--copy-links` | 把软链接转成**真实文件/目录**拷贝 |
| `-p` / `--perms` | 保留权限 |
| `-t` / `--times` | 保留修改时间（**增量同步的基础，别丢**） |
| `-g` / `--group` `-o` / `--owner` | 保留属组 / 属主（需 root） |
| `-D` | 保留设备文件与特殊文件（需 root） |
| `-A` / `--acls` `-X` / `--xattrs` | 保留 ACL / 扩展属性 |
| `--numeric-ids` | 用数字 UID/GID 映射，不做用户名解析（跨机器迁移推荐） |
| `--chown=user:group` | 传输时直接改写属主属组 |
| `--chmod=CHMOD` | 传输时改写权限，如 `--chmod=D755,F644`（D=目录，F=文件） |

### 5.4 网络与远程

| 选项 | 含义 |
|------|------|
| `-e` / `--rsh=COMMAND` | 指定远程 shell，如 `-e "ssh -p 2222"` |
| `--rsync-path=PROG` | 指定远端 rsync 路径（远端 PATH 里没 rsync 时用） |
| `--port=PORT` | 守护进程模式的端口（默认 873） |
| `--password-file=FILE` | 守护进程模式的密码文件 |
| `--bwlimit=RATE` | 限速，单位 KB/s，如 `--bwlimit=5000` ≈ 5MB/s |
| `--timeout=SECONDS` | I/O 超时 |
| `--contimeout=SECONDS` | 连接超时 |
| `-4` / `-6` | 强制 IPv4 / IPv6 |

### 5.5 输出与其他

| 选项 | 含义 |
|------|------|
| `-q` / `--quiet` | 静默 |
| `--stats` | 结束后打印统计信息 |
| `--info=progress2` | 显示**整体**进度（而非单文件进度） |
| `--out-format=FORMAT` | 自定义输出格式 |
| `--log-file=FILE` | 写日志文件 |
| `-i` / `--itemize-changes` | 逐条列出变更及原因（排错利器） |
| `--exclude=PATTERN` | 排除匹配的文件/目录 |
| `--exclude-from=FILE` | 从文件读取排除列表 |
| `--include=PATTERN` | 配合 exclude 做白名单 |
| `--files-from=FILE` | 只同步文件中列出的路径 |
| `--link-dest=DIR` | 硬链接到基准目录，做增量快照（见 [第 12 节](#12-增量快照备份--link-dest)） |
| `--remove-source-files` | 传输成功后删除源文件（相当于"移动"） |

---

## 6. `-a` 归档模式到底包含什么

`-a`（archive）是几个选项的集合：

```text
-a  ==  -rlptgoD
```

| 组成部分 | 作用          |
| ---- | ----------- |
| `-r` | 递归          |
| `-l` | 保留软链接为链接    |
| `-p` | 保留权限        |
| `-t` | 保留修改时间      |
| `-g` | 保留属组        |
| `-o` | 保留属主        |
| `-D` | 保留设备文件、特殊文件 |

**注意**：`-a` **不包含**以下常用项，需要单独加：

- `-z`（压缩）
- `-P`（进度 + 断点续传）
- `-v`（详细输出）
- `--delete`（镜像删除）
- `-A` / `-X`（ACL / 扩展属性）
- `-H`（保留硬链接）

所以最常见的组合是：

```bash
rsync -avzP --delete /src/ user@host:/dst/
```

或本地镜像：

```bash
rsync -aHAX --delete --info=progress2 /src/ /dst/
```

---

## 7. 试运行与输出解读

### 7.1 永远先 `--dry-run`

`--delete` 是破坏性操作。**养成习惯：任何带 `--delete` 的命令，先跑一遍 `-n` 看它会删什么。**

```bash
rsync -avn --delete /src/ /dst/      # 只看不做
rsync -av  --delete /src/ /dst/      # 确认无误后再去掉 -n
```

### 7.2 输出行首的字母含义

```text
$ rsync -av /src/ /dst/
sending incremental file list
.d..t...... ./
>f+++++++++ app.log
>f.st...... config.yaml
cd..t...... subdir/
```

第一个字符是**操作类型**，后续字符是**变更原因**：

| 位置 | 字符 | 含义 |
|------|------|------|
| 1 | `>` | 文件被传输到远端（本地→远端） |
| 1 | `<` | 文件从远端传回本地 |
| 1 | `c` | 本地创建（目录 `cd`、符号链接 `cL`、设备 `cD`） |
| 1 | `h` | 创建的是硬链接 |
| 1 | `.` | 无实际传输，仅属性变更 |
| 1 | `*` | 后面带了 message（如 `*deleting`） |
| 2 | `f` / `d` / `L` / `D` / `S` | 普通文件 / 目录 / 软链接 / 设备 / 特殊文件 |
| 3+ | `s` | 文件大小不同 |
| 3+ | `t` | 修改时间不同 |
| 3+ | `p` | 权限不同 |
| 3+ | `o` | 属主不同 |
| 3+ | `g` | 属组不同 |
| 3+ | `a` | ACL 不同 |
| 3+ | `x` | 扩展属性不同 |
| 3+ | `+` | 目标端**不存在**（新建文件） |

所以 `>f.st......` 读作："文件被传输出去，因为大小或时间不同"。

---

## 8. `--delete`：镜像同步与数据安全

### 8.1 行为说明

不加 `--delete` 时，rsync 只会**追加/覆盖**，目标端多出来的文件会一直留着。
加 `--delete` 后，目标端成为源的严格镜像：源端没有的，目标端会被删掉。

```bash
# 危险示例：如果 /dst/ 写错成系统目录，数据就没了
rsync -av --delete /src/ /important/data/
```

### 8.2 安全实践

```bash
# 1. 先试运行，确认删除清单
rsync -avn --delete /src/ /dst/ | grep deleting

# 2. 用 --delete-after，传输失败也保留原数据
rsync -av --delete-after /src/ /dst/

# 3. 给重要目录加 --backup，删除/覆盖前先备份
rsync -av --delete --backup --backup-dir=/bak/$(date +%F) /src/ /dst/

# 4. 限制删除深度，避免误删整树（3.0+ 支持 --max-delete）
rsync -av --delete --max-delete=100 /src/ /dst/
```

> `--max-delete` 是最后一道保险：删除数量超过阈值就直接报错退出，防止路径写错导致的灾难性删除。

---

## 9. 过滤规则：exclude / include / filter

### 9.1 基本写法

规则按顺序匹配，**第一个命中的规则生效**，之后的不再判断。

```bash
rsync -av --exclude='node_modules' --exclude='.git' /src/ /dst/
rsync -av --exclude='*.log' --exclude='tmp/' /src/ /dst/
```

匹配规则：
- 含 `/`（结尾的 `/` 除外）→ 匹配**完整路径**（相对源根）
- 不含 `/` → 匹配路径**最后一段**（文件名/目录名），任意层级
- `*` 匹配任意非 `/` 字符，`**` 匹配含 `/` 的任意字符，`?` 匹配单个字符

### 9.2 白名单写法

`--exclude='*'` 会把目录本身也排除掉，导致什么都不同步。正确写法是先 include 目录，再排除其余：

```bash
# 只同步 .jpg 和 .png（递归）
rsync -av \
  --include='*/' \
  --include='*.jpg' --include='*.png' \
  --exclude='*' \
  /src/ /dst/
```

> `--include='*/'` 让 rsync 能进入所有子目录；`--exclude='*'` 兜底排除其余文件。
> 顺序不能颠倒。

### 9.3 用文件管理规则

规则多了就放到文件里，一行一条，`;` 或 `#` 开头是注释：

```bash
# rsync-exclude.txt
.git/
node_modules/
__pycache__/
*.pyc
*.log
.DS_Store
```

```bash
rsync -av --exclude-from='rsync-exclude.txt' /src/ /dst/
```

### 9.4 `--filter` 高级规则

`--filter` 用简写前缀表达更精细的控制：

| 规则 | 含义 |
|------|------|
| `--filter='- *.tmp'` | 排除（等价于 exclude） |
| `--filter='+ *.keep'` | 包含（等价于 include） |
| `--filter='P *.log'` | protect：目标端**永不删除**这些文件（配合 `--delete` 用） |
| `--filter='R *.bak'` | 源文件端不传，但仍按 protect 保护目标端 |
| `--filter='H *.iso'` | hide：源端不传，且目标端可被 `--delete` 删除 |
| `--filter='S *.iso'` | show：覆盖 hide |

典型用法——镜像同步时保留目标端的本地配置不被删：

```bash
rsync -av --delete --filter='P .env.local' /src/ user@host:/app/
```

---

## 10. 远程同步：SSH 与守护进程模式

### 10.1 SSH 模式（推荐）

```bash
# 基本推送
rsync -avzP /data/ user@host:/backup/data/

# 指定端口与密钥
rsync -avzP -e "ssh -p 2222 -i ~/.ssh/id_ed25519" /data/ user@host:/backup/

# 通过跳板机
rsync -avzP -e "ssh -J jumpuser@jumphost" /data/ user@inner:/backup/

# 限制 SSH 算法/关闭严格主机检查（自动化脚本常用）
rsync -avzP -e "ssh -o StrictHostKeyChecking=no" /data/ user@host:/backup/
```

免密配置（否则每次都要输密码）：

```bash
ssh-keygen -t ed25519
ssh-copy-id user@host
```

> **注意**：rsync 要求**两端都装有 rsync**。远端找不到时会报
> `rsync: command not found`，可用 `--rsync-path=/usr/local/bin/rsync` 指定。

### 10.2 守护进程模式（适合公共镜像站 / 内网分发）

服务端配置 `/etc/rsyncd.conf`：

```ini
uid = nobody
gid = nobody
use chroot = yes
max connections = 10
pid file = /var/run/rsyncd.pid
log file = /var/log/rsyncd.log

[backup]
    path = /data/backup
    comment = Backup share
    read only = no
    auth users = rsyncuser
    secrets file = /etc/rsyncd.secrets
    hosts allow = 10.0.0.0/24
```

密码文件 `/etc/rsyncd.secrets`（权限必须 600）：

```bash
echo "rsyncuser:yourpassword" | sudo tee /etc/rsyncd.secrets
sudo chmod 600 /etc/rsyncd.secrets
```

启动与客户端使用：

```bash
# 服务端
sudo rsync --daemon

# 客户端：列出可用模块
rsync rsync://host/

# 客户端：拉取
rsync -avzP rsyncuser@host::backup/ /local/backup/

# 非交互：用密码文件
rsync -avzP --password-file=/etc/rsync.pass rsyncuser@host::backup/ /local/backup/
```

### 10.3 两种模式对比

| 维度 | SSH 模式 | 守护进程模式 |
|------|----------|--------------|
| 传输通道 | SSH 加密（22 端口） | rsync 协议（873 端口，明文） |
| 认证 | SSH 密钥/密码 | rsyncd.secrets 用户密码 |
| 权限控制 | 依赖 SSH 用户权限 | 模块级 `read only` / `hosts allow` |
| 适用场景 | 日常运维、服务器互联 | 镜像站、匿名只读分发 |
| 安全性 | 高 | 低，仅建议内网 |

---

## 11. 断点续传、限速与进度

```bash
# 断点续传 + 单文件进度（大文件必备）
rsync -avzP big.iso user@host:/data/

# --partial 保留半截文件，--append 只追加尾部（适合持续增长的日志）
rsync -av --partial --append large.log user@host:/data/

# 整体进度百分比（比 -P 的单文件进度更直观）
rsync -a --info=progress2 /src/ /dst/

# 限速 5MB/s，避免打满生产带宽
rsync -avzP --bwlimit=5000 /src/ user@host:/dst/

# 传输完打印统计
rsync -av --stats /src/ /dst/
```

> `--append` 有风险：它假定目标端前 N 字节与源完全一致，只追加差异部分。
> 若文件被截断过（`--append` 不带 `--append-verify`），可能产出损坏文件。
> 严谨做法用 `--append-verify`（会用校验和验证前缀，慢一点但安全）。

---

## 12. 增量快照备份：`--link-dest`

做"每天一份全量快照，但只占增量空间"的经典方案：

```bash
#!/usr/bin/env bash
set -euo pipefail

SRC="/data/"
BASE="/backup"
TODAY="$BASE/$(date +%F)"

# 找到最近一次快照作为硬链接基准
LAST="$(ls -1d "$BASE"/2* 2>/dev/null | tail -n1 || true)"

if [[ -n "$LAST" ]]; then
  # 未变化的文件硬链接到上次快照，几乎不占空间
  rsync -a --delete --link-dest="$LAST" "$SRC" "$TODAY"
else
  rsync -a "$SRC" "$TODAY"
fi
```

效果：

```text
/backup/2026-11-01/     ← 完整快照（真实占用）
/backup/2026-11-02/     ← 只存变化文件，其余硬链接到 11-01
/backup/2026-11-03/     ← 只存变化文件，其余硬链接到 11-02
```

每个目录看起来都是"全量"，实际磁盘占用接近一次全量 + N 次增量。

> **注意**：`--link-dest` 依赖硬链接，要求基准目录与目标目录在**同一文件系统**。
> 且目标目录不能已存在（rsync 会自己创建）。

---

## 13. 典型场景实战

### 13.1 网站/前端产物部署

```bash
rsync -avz --delete \
  --exclude='.env.local' \
  --exclude='.git/' \
  --chmod=D755,F644 \
  dist/ deploy@web01:/var/www/site/
```

### 13.2 服务器整机迁移

```bash
# 保留属主属组、ACL、扩展属性、硬链接，用数字 UID/GID
sudo rsync -aHAX --numeric-ids --info=progress2 \
  --exclude='/dev/*' --exclude='/proc/*' --exclude='/sys/*' \
  --exclude='/tmp/*' --exclude='/run/*' --exclude='/mnt/*' \
  --exclude='/lost+found' \
  / user@newhost:/
```

> 迁移 `/` 时**必须**排除 `/proc`、`/sys`、`/dev` 这类伪文件系统，否则会同步到大量无效内容。

### 13.3 只同步当天修改过的文件

```bash
find /data -type f -mtime -1 -print0 | \
  rsync -av --files-from=- --from0 / user@host:/backup/
```

### 13.4 双向同步的注意事项

rsync **不是**双向同步工具，它没有冲突合并能力。需要双向请用 `unison` 或 `syncthing`。
如果强行"来回各跑一次"，后跑的那次可能用旧时间戳覆盖新文件。

### 13.5 定时备份脚本（配合 cron）

```bash
#!/usr/bin/env bash
# /usr/local/bin/backup.sh
set -euo pipefail

LOG=/var/log/rsync-backup.log
rsync -az --delete \
  --backup --backup-dir=/backup/deleted/$(date +%F) \
  --bwlimit=10000 \
  --log-file="$LOG" \
  /data/ backup@10.0.0.9:/backup/data/ >> "$LOG" 2>&1

echo "[$(date)] backup finished, exit=$?" >> "$LOG"
```

```cron
# 每天凌晨 2 点执行
0 2 * * * /usr/local/bin/backup.sh
```

---

## 14. 退出码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | 语法或用法错误 |
| 2 | 协议不兼容 |
| 3 | 选择输入/输出文件时出错 |
| 4 | 请求的操作不支持（如尝试传输不支持的文件类型） |
| 5 | 启动 client-server 通信时出错 |
| 6 | 守护进程无法追加到日志文件 |
| 10 | socket I/O 错误 |
| 11 | 文件 I/O 错误 |
| 12 | rsync 数据流错误 |
| 13 | 程序诊断错误 |
| 14 | IPC 错误 |
| 20 | 收到 SIGUSR1 / SIGINT |
| 21 | 等待文件时发生错误（chdir/权限等） |
| 22 | 内存分配失败 |
| 23 | **部分传输**（部分文件失败/未传完）——脚本里最常见 |
| 24 | 源文件在传输过程中消失 |
| 25 | `--max-delete` 限制被触发 |
| 30 | 发送/接收数据时超时 |
| 35 | 等待守护进程连接超时 |

脚本中最需要单独处理的是 **23**（部分成功）和 **24**（源被移走），它们通常不代表致命错误，
但也不该当成完全成功：

```bash
rsync -av /src/ /dst/
rc=$?
case $rc in
  0)  echo "OK" ;;
  23|24) echo "WARN: partial transfer (rc=$rc)" ;;
  *)  echo "ERROR: rsync failed (rc=$rc)" >&2; exit 1 ;;
esac
```

---

## 15. 常见坑与排错

### 15.1 `--delete` 删错目录

**症状**：目标目录被清空。
**原因**：源路径末尾多了 `/`，导致同步层级错位（`rsync -a /src/* /dst/` 尤其危险）。
**预防**：先用 `-n` 试跑 + `--max-delete` 兜底。

### 15.2 每次都全量重传

**症状**：明明只改一个文件，却传了整个目录。
**原因**：目标端文件的 mtime 变了（比如某些文件系统不支持精确时间戳，或挂载参数问题）。
**排查**：

```bash
rsync -av --itemize-changes -n /src/ /dst/    # 看每个文件的变更原因
```

若输出里满屏 `t`（时间不同），可考虑 `--checksum` 或 `--size-only`。

### 15.3 权限/属主没同步

**症状**：`-a` 用了，但目标端属主还是当前用户。
**原因**：`-o`（属主）需要 root 权限。普通用户无法 chown。
**解决**：`sudo rsync -a ...`；或同步后 `chown -R`。

### 15.4 软链接变成真实文件 / 反之

- 保留软链接：`-a`（含 `-l`）即可。
- 想把链接指向的内容拷出来：加 `-L`。

### 15.5 `rsync: command not found`

远端没装 rsync，或 PATH 里没有：

```bash
rsync -av --rsync-path=/usr/local/bin/rsync /src/ host:/dst/
```

### 15.6 SSH 每次都要密码

```bash
ssh-copy-id user@host          # 装公钥
# 或指定密钥
rsync -av -e "ssh -i ~/.ssh/id_ed25519" /src/ host:/dst/
```

### 15.7 NTFS / FAT / exFAT 挂载盘同步报错

这类文件系统不支持 Unix 权限与符号链接，会报
`failed to set permissions` 或 `symlink has no referent`。

```bash
rsync -rtv --no-perms --no-owner --no-group /src/ /mnt/usb/
```

### 15.8 macOS 上的额外注意

macOS 自带 rsync 2.6.9，且 HFS+/APFS 的资源分支需要 `-E`（新版 3.x 用 `--xattrs`）：

```bash
/opt/homebrew/bin/rsync -aHAXE --delete /src/ /dst/
```

---

## 16. rsync vs scp vs cp

| 维度 | `cp` | `scp` | `rsync` |
|------|------|-------|---------|
| 跨主机 | ❌ | ✅ | ✅ |
| 增量传输 | ❌ 全量拷 | ❌ 全量传 | ✅ 只传差异 |
| 断点续传 | ❌ | ❌ | ✅ `-P` |
| 保留属性 | `-a` | 部分（`-p`） | ✅ `-a` |
| 过滤规则 | ❌ | ❌ | ✅ exclude/include |
| 镜像删除 | ❌ | ❌ | ✅ `--delete` |
| 限速 | ❌ | `-l` | ✅ `--bwlimit` |
| 试运行 | ❌ | ❌ | ✅ `-n` |
| 典型场景 | 本机小文件拷贝 | 临时传单个文件 | **备份、部署、迁移** |

> **结论**：日常运维、备份、部署一律用 rsync；`scp` 只在"临时传一个文件"时图方便。
> 另外 `scp` 基于已废弃的 SCP 协议，新版 OpenSSH 已推荐改用 `sftp` 或 `rsync over ssh`。

---

## 速查卡片

```bash
# 本地镜像
rsync -a --delete --info=progress2 /src/ /dst/

# 推到远程
rsync -avzP --delete /src/ user@host:/dst/

# 从远程拉
rsync -avzP user@host:/src/ /dst/

# 安全试跑（做任何删除前必做）
rsync -avn --delete /src/ /dst/

# 备份（保留被覆盖/删除的文件）
rsync -a --delete --backup --backup-dir=/bak/$(date +%F) /src/ /dst/

# 增量快照
rsync -a --delete --link-dest=/backup/last /src/ /backup/now/

# 限速同步大文件
rsync -avzP --bwlimit=5000 big.iso user@host:/data/
```

## 相关笔记

- [[ssh|SSH]]
- [[linux|Linux]]
- [[docker|Docker]]
- [[nginx|Nginx]]
- [[tmux|Tmux]]
