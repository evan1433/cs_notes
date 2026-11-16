---
title: Linux FHS 目录配置
description: Linux FHS（文件系统层次结构标准）目录配置规范，根目录及 /usr、/var 等子目录详解
tags: [linux, fhs, file-system]
---

# Linux FHS 目录配置

## 1. FHS 简介

FHS（Filesystem Hierarchy Standard，文件系统层次结构标准）是 Linux 文件系统目录配置的标准规范，由 Linux 基金会维护，定义了各个目录的用途、存放的内容以及目录结构。

### FHS 的作用

1. **统一标准**：让用户和开发者能够预测文件和目录的位置
2. **软件兼容**：不同 Linux 发行版遵循相同标准，软件安装更统一
3. **系统管理**：管理员能够快速找到配置文件、日志文件等
4. **文档规范**：便于编写文档和培训材料

### FHS 分类标准

#### 可分享与不可分享

| 类型 | 定义 | 示例 |
|------|------|------|
| **可分享（Shareable）** | 可在多个主机间共享的目录 | `/usr`, `/opt`, `/home` |
| **不可分享（Unshareable）** | 仅本机使用的目录 | `/etc`, `/boot`, `/var` |

#### 静态与可变

| 类型 | 定义 | 示例 |
|------|------|------|
| **静态（Static）** | 不经常变化的目录（除非管理员干预） | `/usr`, `/opt`, `/boot` |
| **可变（Variable）** | 经常变化的目录 | `/var`, `/tmp`, `/home` |

#### 四种组合

| 组合 | 目录示例 | 说明 |
|------|----------|------|
| **可分享 + 静态** | `/usr`, `/opt` | 可共享的应用程序 |
| **可分享 + 可变** | `/home`, `/var/mail` | 可共享的用户数据 |
| **不可分享 + 静态** | `/etc`, `/boot` | 本机配置和启动文件 |
| **不可分享 + 可变** | `/var/run`, `/var/log` | 本机运行时数据 |

## 2. 目录树结构

Linux 文件系统采用树状结构，根目录（`/`）是所有目录的起点：

```
/
├── bin/       # 用户基本命令
├── boot/      # 启动加载程序文件
├── dev/       # 设备文件
├── etc/       # 系统配置文件
├── home/      # 用户主目录
├── lib/       # 共享库和内核模块
├── lib64/     # 64位共享库
├── media/     # 可移动设备挂载点
├── mnt/       # 临时挂载点
├── opt/       # 可选应用软件包
├── proc/      # 进程和内核信息
├── root/      # root 用户主目录
├── run/       # 运行时变量数据
├── sbin/      # 系统管理命令
├── srv/       # 服务数据
├── sys/       # 系统设备信息
├── tmp/       # 临时文件
├── usr/       # 用户程序和数据
└── var/       # 可变数据文件
```

## 3. 根目录下主要目录

### 3.1 `/bin` - 用户基本命令

存放所有用户都能使用的基本命令（二进制文件）。

**特点**：
- 单用户模式下也能使用
- 不依赖其他分区
- 系统启动必需的命令

**常见内容**：`ls, cp, mv, cat, rm, mkdir, rmdir, bash, sh, echo, pwd, date, uname`

### 3.2 `/boot` - 启动加载程序文件

存放系统启动所需的文件，包括内核、引导加载程序等。

**常见内容**：`vmlinuz`（内核文件）、`initrd/initramfs`（初始化 RAM 磁盘）、`grub/`（GRUB 配置）

### 3.3 `/dev` - 设备文件

存放设备文件（设备驱动程序的接口），包括硬件设备和虚拟设备。

**常见设备文件**：
- `/dev/null`：空设备（丢弃所有输入）
- `/dev/zero`：零设备（提供无限零字节）
- `/dev/random`：随机数设备
- `/dev/sda`：SCSI/SATA 硬盘

### 3.4 `/etc` - 系统配置文件

存放系统配置文件，大部分是文本文件。

**常见配置文件**：
- `/etc/passwd`：用户账户信息
- `/etc/shadow`：用户密码信息
- `/etc/group`：用户组信息
- `/etc/fstab`：文件系统挂载配置
- `/etc/hosts`：主机名解析
- `/etc/resolv.conf`：DNS 配置
- `/etc/ssh/`：SSH 配置
- `/etc/crontab`：系统定时任务

### 3.5 `/home` - 用户主目录

存放普通用户的主目录，每个用户都有一个子目录。

**目录结构**：
```
/home/
├── user1/
│   ├── .bashrc
│   ├── .bash_profile
│   ├── Documents/
│   └── Downloads/
├── user2/
└── user3/
```

### 3.6 `/lib` - 共享库和内核模块

存放系统启动和运行 `/bin`、`/sbin` 中命令所需的共享库（动态链接库）。

**常见内容**：`/lib/modules/`（内核模块）、`*.so`（共享对象文件）、`*.a`（静态库文件）

### 3.7 `/lib64` - 64 位共享库

存放 64 位系统所需的共享库（仅在 64 位系统中存在）。

### 3.8 `/media` - 可移动设备挂载点

用于挂载可移动设备（U盘、光盘、移动硬盘等），系统自动挂载。

### 3.9 `/mnt` - 临时挂载点

用于临时挂载文件系统（管理员手动挂载）。

```bash
# 挂载 NFS 文件系统
sudo mount 192.168.1.100:/share /mnt/nfs
```

### 3.10 `/opt` - 可选应用软件包

存放可选的第三方应用软件包（大型独立软件）。

**常见内容**：`/opt/google/chrome/`、`/opt/java/`

### 3.11 `/proc` - 进程和内核信息

虚拟文件系统，存放进程信息和内核参数（不占用磁盘空间）。

**常见内容**：
- `/proc/cpuinfo`：CPU 信息
- `/proc/meminfo`：内存信息
- `/proc/version`：内核版本
- `/proc/loadavg`：系统负载
- `/proc/[pid]/`：进程信息目录
- `/proc/sys/`：内核参数（可修改）

### 3.12 `/root` - root 用户主目录

root 用户（超级管理员）的主目录，普通用户无权访问。

### 3.13 `/run` - 运行时变量数据

存放系统运行时的临时文件（重启后清空），临时文件系统（内存中）。

### 3.14 `/sbin` - 系统管理命令

存放系统管理命令（只有 root 用户能使用）。

**常见内容**：`init, shutdown, reboot, fdisk, mkfs, fsck, ifconfig, ip, iptables, systemctl, mount, umount`

### 3.15 `/srv` - 服务数据

存放服务提供的数据（Web、FTP 等服务的数据）。

### 3.16 `/sys` - 系统设备信息

虚拟文件系统，存放设备和驱动程序信息（类似 `/proc`）。

### 3.17 `/tmp` - 临时文件

存放临时文件，所有用户可访问，系统重启后清空。

## 4. `/usr` 目录结构

`/usr`（Unix System Resource）是用户程序和数据的存放位置，包含大部分用户应用软件。

```
/usr/
├── bin/       # 用户命令（非必需）
├── sbin/      # 系统管理命令（非必需）
├── lib/       # 共享库
├── lib64/     # 64位共享库
├── include/   # 头文件（开发用）
├── share/     # 共享数据（文档、图标等）
├── local/     # 本地安装的软件
├── src/       # 源代码
└── games/     # 游戏程序
```

### 常见子目录

- **`/usr/bin/`**：用户命令（非启动必需），如 `python, gcc, vim`
- **`/usr/sbin/`**：系统管理命令，如 `httpd, nginx`
- **`/usr/lib/`**：共享库
- **`/usr/include/`**：C/C++ 头文件（开发用）
- **`/usr/share/`**：共享数据（文档、图标、man 手册）
- **`/usr/local/`**：本地安装的软件（手动安装）

```bash
# 手动安装软件到 /usr/local
./configure --prefix=/usr/local
make
sudo make install
```

## 5. `/var` 目录结构

`/var`（Variable）存放可变数据文件，包括日志、缓存、临时文件等。

```
/var/
├── log/       # 系统日志文件
├── cache/     # 应用缓存数据
├── lib/       # 应用状态数据
├── spool/     # 队列数据（邮件、打印等）
├── tmp/       # 临时文件（重启不清空）
├── mail/      # 用户邮件
├── www/       # Web 服务数据
├── ftp/       # FTP 服务数据
└── run/       # 运行时数据（已移至 /run）
```

### 常见子目录

- **`/var/log/`**：系统日志文件（最重要的目录之一）
    - `/var/log/syslog`（Debian/Ubuntu）或 `/var/log/messages`（CentOS/RHEL）
    - `/var/log/auth.log`：认证日志
    - `/var/log/kern.log`：内核日志
- **`/var/cache/`**：应用缓存数据（可删除）
    - `/var/cache/apt/`、`/var/cache/yum/`
- **`/var/lib/`**：应用状态数据
    - `/var/lib/mysql/`、`/var/lib/docker/`
- **`/var/spool/`**：队列数据（邮件、打印等）
- **`/var/www/`**：Web 服务数据

## 6. 不同发行版的差异

| 目录 | Debian/Ubuntu | CentOS/RHEL | 说明 |
|------|---------------|-------------|------|
| 网络配置 | `/etc/network/` | `/etc/sysconfig/network-scripts/` | 配置位置不同 |
| Web 数据 | `/var/www/html/` | `/var/www/html/` | 基本一致 |
| 日志文件 | `/var/log/syslog` | `/var/log/messages` | 主日志文件名称不同 |
| 包管理缓存 | `/var/cache/apt/` | `/var/cache/yum/` | 包管理器不同 |

## 7. 常用目录速查

| 目录 | 用途 | 常见内容 |
|------|------|----------|
| `/bin` | 基本命令 | `ls, cp, mv, cat` |
| `/etc` | 配置文件 | `passwd, fstab, hosts` |
| `/home` | 用户目录 | 用户个人文件 |
| `/var/log` | 日志文件 | 系统和服务日志 |
| `/usr/bin` | 用户命令 | `python, gcc, vim` |
| `/usr/local` | 本地软件 | 手动安装的软件 |
| `/tmp` | 临时文件 | 临时数据 |
| `/proc` | 进程信息 | CPU、内存、进程信息 |

## 8. 最佳实践

1. 遵循 FHS 标准，将文件放在正确位置
2. 不要随意修改系统目录权限
3. 定期清理 `/tmp` 和 `/var/cache`
4. 重要数据备份 `/home` 和 `/var/lib`
5. 监控 `/var/log` 日志文件大小
