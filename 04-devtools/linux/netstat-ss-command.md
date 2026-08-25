---
title: netstat 与 ss 命令详解
description: Linux 网络连接查看命令 netstat 与 ss 的完整用法，包括端口监听、连接状态、路由表、接口统计及实战排障场景
tags:
  - linux
  - command
  - network
  - netstat
  - ss
---
# netstat 与 ss 命令详解

`netstat`（network statistics）和 `ss`（socket statistics）是 Linux 下查看网络连接、路由表、接口统计等网络信息的核心工具。
`ss` 是 `netstat` 的现代替代品，来自 `iproute2` 工具包，速度更快、信息更全；
`netstat` 来自旧版 `net-tools`，已被许多发行版标记为弃用，但因其语法简单仍被广泛使用。

> **背景**：`net-tools` 工具包（含 `netstat`、`ifconfig`、`route` 等）自 2001 年起停止维护；`iproute2`（含 `ss`、`ip` 等）是官方推荐的现代替代。两者在大多数场景下可以互换。

## 1. 基础概念

### 1.1 套接字（Socket）与连接状态

`netstat`/`ss` 查看的是内核维护的套接字表。TCP 套接字有以下状态：

| 状态            | 含义                 | 排障关注点                  |
| ------------- | ------------------ | ---------------------- |
| `LISTEN`      | 等待连接请求             | 服务是否正常监听端口             |
| `ESTABLISHED` | 连接已建立              | 活跃连接数                  |
| `TIME_WAIT`   | 主动关闭后等待残留报文        | 大量 TIME_WAIT 可能耗尽端口    |
| `CLOSE_WAIT`  | 被动关闭，等待本端关闭        | 程序未正确 close → 泄漏       |
| `SYN_SENT`    | 已发送 SYN，等待 SYN-ACK | 连接建立缓慢                 |
| `SYN_RECV`    | 已收到 SYN，发送 SYN-ACK | 半连接堆积 → 可能遭受 SYN Flood |

### 1.2 netstat vs ss 总览

| 对比项 | `netstat` | `ss` |
|--------|-----------|------|
| 所属包 | `net-tools`（旧） | `iproute2`（新） |
| 数据来源 | 遍历 `/proc/net/*` | 直接读取内核 socket（netlink） |
| 速度 | 较慢（大量连接时明显） | 快得多（快 1-2 个数量级） |
| 过滤能力 | 基本协议/状态过滤 | 强大的过滤表达式 |
| 进程信息 | 需 `sudo` 才能看到 PID | 同样需 `sudo` |
| 推荐度 | 兼容老系统 | 现代首选 |

## 2. netstat 基础用法

### 2.1 最常用组合

```bash
# 查看所有监听中的 TCP 端口（带进程名）
sudo netstat -tlnp

# 查看所有 TCP/UDP 监听端口
sudo netstat -tulnp

# 查看所有活跃连接（数字显示地址端口）
netstat -tn

# 查看所有连接（含监听 + 已连接，TCP+UDP）
netstat -a
```

### 2.2 核心选项

| 选项 | 全称 | 说明 |
|------|------|------|
| `-t` | `--tcp` | 只显示 TCP 连接 |
| `-u` | `--udp` | 只显示 UDP 连接 |
| `-l` | `--listening` | 只显示监听中的套接字 |
| `-a` | `--all` | 显示所有（含监听 + 非监听） |
| `-n` | `--numeric` | 数字显示地址和端口（不做 DNS 解析） |
| `-p` | `--program` | 显示占用套接字的进程 PID/名称 |
| `-r` | `--route` | 显示路由表 |
| `-i` | `--interfaces` | 显示网络接口统计 |
| `-s` | `--statistics` | 按协议显示统计信息 |
| `-c` | `--continuous` | 持续刷新（类似 top） |
| `-e` | `--extend` | 显示扩展信息（user、inode 等） |
| `-W` | `--wide` | 宽格式显示（不截断地址） |

### 2.3 典型场景

```bash
# 1. 排查某端口是否被占用（两种方式）
sudo netstat -tlnp | grep :8080
sudo netstat -tlnp | grep 8080

# 2. 查看某个进程的网络连接
sudo netstat -tnp | grep nginx

# 3. 统计各状态连接数（排查 TIME_WAIT 等）
netstat -tn | awk '{print $NF}' | sort | uniq -c | sort -rn

# 4. 持续监控连接变化
netstat -tn -c

# 5. 查看路由表（等价 ip route）
netstat -rn
```

### 2.4 查看路由表

```bash
# 标准路由表
netstat -rn

# 输出示例：
# Kernel IP routing table
# Destination     Gateway         Genmask         Flags   MSS Window  irtt Iface
# 0.0.0.0         192.168.1.1     0.0.0.0         UG        0 0          0 eth0
# 192.168.1.0     0.0.0.0         255.255.255.0   U         0 0          0 eth0
```

| 输出列 | 含义 |
|--------|------|
| `Destination` | 目标网络/主机 |
| `Gateway` | 网关地址（`0.0.0.0` 表示直连） |
| `Genmask` | 子网掩码 |
| `Flags` | `U`=可用、`G`=网关、`H`=主机路由 |
| `Iface` | 出口网卡 |

### 2.5 查看接口统计

```bash
# 查看所有网络接口的收发包统计
netstat -i

# 查看指定接口
netstat -i eth0
```

| 输出列 | 含义 |
|--------|------|
| `RX-OK` / `RX-ERR` | 接收成功 / 错误包数 |
| `TX-OK` / `TX-ERR` | 发送成功 / 错误包数 |
| `Flg` | 接口标志（`RU`=Running/Up） |

### 2.6 按协议统计

```bash
# 查看各协议（IP/TCP/UDP/ICMP）的收发统计
netstat -s

# 只看 TCP 统计
netstat -s -t

# 只看 UDP 统计
netstat -s -u
```

> **实用技巧**：`netstat -s` 是排查网络层问题的重要手段，重点关注 `failed connection attempts`（连接失败）、`segments retransmited`（重传）等异常计数。

## 3. ss 基础用法

### 3.1 最常用组合

```bash
# 查看所有监听中的 TCP 端口（带进程名）—— ss 的黄金组合
sudo ss -tlnp

# 查看所有 TCP 连接
ss -tn

# 查看连接摘要
ss -s

# 查看所有套接字（最全量）
ss -a
```

### 3.2 核心选项

| 选项          | 全称                  | 说明                  |
| ----------- | ------------------- | ------------------- |
| `-t`        | `--tcp`             | 只显示 TCP 套接字         |
| `-u`        | `--udp`             | 只显示 UDP 套接字         |
| `-l`        | `--listening`       | 只显示监听中的套接字          |
| `-a`        | `--all`             | 显示所有（含监听 + 非监听）     |
| `-n`        | `--numeric`         | 数字显示地址和端口           |
| `-p`        | `--processes`       | 显示进程信息              |
| `-e`        | `--extended`        | 显示扩展信息（uid、inode 等） |
| `-m`        | `--memory`          | 显示套接字内存使用           |
| `-o`        | `--options`         | 显示定时器信息             |
| `-s`        | `--summary`         | 显示套接字摘要统计           |
| `-4` / `-6` | `--ipv4` / `--ipv6` | 只显示 IPv4 / IPv6     |
| `-r`        | `--resolve`         | 解析为主机名/端口名（反向 DNS）  |

### 3.3 按状态过滤（ss 的优势）

ss 支持强大的过滤表达式，这是 netstat 不具备的能力：

```bash
# 查看所有 ESTABLISHED 状态的 TCP 连接
ss -tn state ESTABLISHED

# 查看所有 TIME_WAIT 连接（排查端口耗尽）
ss -tn state TIME-WAIT

# 查看所有 CLOSE_WAIT 连接（排查程序未关闭 socket）
ss -tn state CLOSE-WAIT

# 查看监听状态的 TCP
ss -tn state LISTEN

# 多状态组合（排除 LISTEN）
ss -tn state established state time-wait
```

> **注意**：ss 的状态名使用连字符格式（`TIME-WAIT`），而非 netstat 输出中的下划线（`TIME_WAIT`）。

### 3.4 按地址/端口过滤

```bash
# 按目标地址过滤
ss -tn dst 192.168.1.100
ss -tn dst 192.168.1.0/24
ss -tn dst :443                # 目标端口为 443

# 按源地址过滤
ss -tn src 192.168.1.100
ss -tn src :8080

# 按端口范围过滤
ss -tn dport = :443
ss -tn dport ge :8000 and dport le :9000
```

### 3.5 摘要统计

```bash
# 快速查看各类套接字数量概览
ss -s

# 输出示例：
# Total: 156 (kernel 0)
# TCP:   12 (estab 5, closed 1, orphaned 0, synrecv 0, timewait 1/0), ports 0
# UDP:    2 (0, 0)
# ...
```

这是快速判断连接数是否异常的最佳命令。

## 4. 实战场景

### 4.1 排查端口占用

```bash
# 方式一：netstat
sudo netstat -tlnp | grep :3306

# 方式二：ss（更快，推荐）
sudo ss -tlnp | grep :3306

# 方式三：ss 直接按端口过滤
sudo ss -tlnp sport = :3306
```

输出中 `users:(("mysqld",pid=1234,fd=30))` 即可定位到占用端口的进程。

### 4.2 统计各状态连接数

```bash
# netstat 方式 —— 借助 awk 统计
netstat -tn | awk 'NR>1 {print $NF}' | sort | uniq -c | sort -rn

# ss 方式 —— 逐个状态统计
ss -s                          # 摘要中直接包含各状态计数

# ss 逐个查询（精确统计）
for state in ESTAB TIME-WAIT CLOSE-WAIT SYN-SENT; do
  echo "$state: $(ss -tn state $state | tail -n +2 | wc -l)"
done
```

### 4.3 排查 TIME_WAIT 过多

大量 `TIME_WAIT` 会耗尽 ephemeral port（默认 32768-60999），导致新连接失败。

```bash
# 1. 查看 TIME_WAIT 数量
ss -tn state TIME-WAIT | wc -l
netstat -tn | grep TIME_WAIT | wc -l

# 2. 查看 TIME_WAIT 来源分布（哪些远端）
ss -tn state TIME-WAIT | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head

# 3. 查看当前系统端口范围
cat /proc/sys/net/ipv4/ip_local_port_range

# 4. 临时扩大端口范围
sysctl -w net.ipv4.ip_local_port_range="1024 65535"

# 5. 允许 TIME_WAIT 快速回收（生产环境慎用，可能影响 NAT）
sysctl -w net.ipv4.tcp_tw_reuse=1
```

### 4.4 排查 CLOSE_WAIT 泄漏

`CLOSE_WAIT` 表示对端已关闭连接但本端程序未调用 `close()`，属于程序 Bug。

```bash
# 查看哪些进程持有 CLOSE_WAIT
sudo ss -tnp state CLOSE-WAIT

# 输出示例：
# CLOSE-WAIT 1 0 192.168.1.10:8080 192.168.1.20:54320 users:(("java",pid=5678,fd=42))
```

定位到进程 PID 后，用 `strace -p <PID>` 或排查代码中未关闭的连接。

### 4.5 检查服务是否正常监听

```bash
# 检查 Nginx 是否监听 80/443
sudo ss -tlnp | grep -E ':80\b|:443\b'

# 检查 MySQL 是否监听 3306
sudo ss -tlnp sport = :3306

# 检查 Redis 是否监听 6379（注意应绑定 127.0.0.1）
sudo ss -tlnp sport = :6379
```

### 4.6 查看某进程的所有网络连接

```bash
# netstat 方式
sudo netstat -tnp | grep nginx

# ss 方式 —— 按进程名过滤
sudo ss -tnp | grep nginx

# ss 按进程 PID 精确过滤
sudo ss -tnp | grep "pid=1234"
```

### 4.7 安全排查 —— 异常外连检测

```bash
# 查看所有对外的 ESTABLISHED 连接
ss -tn state ESTABLISHED

# 关注非常规端口的外连（可能是后门/挖矿）
ss -tn state ESTABLISHED | awk '{print $4, $5}' | grep -vE ':(80|443|22)\b'

# 查看监听在 0.0.0.0 而非 127.0.0.1 的端口（对外暴露的服务）
sudo ss -tlnp | grep "0.0.0.0\|::"
```

## 5. netstat 与 ss 对照表

| 场景 | netstat | ss |
|------|---------|-----|
| 查看监听 TCP 端口 | `netstat -tlnp` | `ss -tlnp` |
| 查看所有 TCP 连接 | `netstat -tn` | `ss -tn` |
| 查看所有 TCP/UDP 监听 | `netstat -tulnp` | `ss -tulnp` |
| 查看路由表 | `netstat -rn` | `ip route`（ss 不支持） |
| 查看接口统计 | `netstat -i` | `ip -s link`（ss 不支持） |
| 协议统计 | `netstat -s` | `ss -s`（仅摘要） |
| 按状态过滤 | 不支持 | `ss -tn state TIME-WAIT` |
| 按地址过滤 | `grep` | `ss -tn dst 1.2.3.4` |
| 持续刷新 | `netstat -c` | `watch ss -tn` |

> **迁移建议**：新系统优先使用 `ss`；遇到需要路由表和接口统计时用 `ip route` / `ip -s link`，而非 `netstat`。

## 6. 输出格式详解

### 6.1 netstat -tn 输出

```
Proto Recv-Q Send-Q Local Address   Foreign Address  State
tcp        0      0 192.168.1.10:22  10.0.0.5:52341  ESTABLISHED
```

| 列 | 含义 |
|----|------|
| `Proto` | 协议（tcp/tcp6/udp/udp6） |
| `Recv-Q` | 接收队列中未读取的字节数（非 0 说明程序读取慢） |
| `Send-Q` | 发送队列中未发送的字节数（非 0 说明网络拥塞或对端接收慢） |
| `Local Address` | 本端地址:端口 |
| `Foreign Address` | 远端地址:端口 |
| `State` | 连接状态（UDP 无此列） |

### 6.2 ss -tn 输出

```
State       Recv-Q Send-Q Local Address:Port  Peer Address:Port
ESTAB       0      0      192.168.1.10:22     10.0.0.5:52341
```

ss 的输出更紧凑，状态在最前，地址端口合并为一列。

### 6.3 Recv-Q / Send-Q 排障

| 队列 | 持续非零含义 | 可能原因 |
|------|--------------|----------|
| `Recv-Q` | 应用读取速度跟不上到达速度 | 应用处理慢、线程池打满、事件循环阻塞 |
| `Send-Q` | 数据发出速度跟不上写入速度 | 网络带宽不足、对端接收窗口小、TCP 拥塞 |

## 7. 命令速查表

| 场景               | 命令                                                          |
| ---------------- | ----------------------------------------------------------- |
| 查看监听 TCP 端口      | `sudo ss -tlnp`                                             |
| 查看所有 TCP 连接      | `ss -tn`                                                    |
| 查看 TCP/UDP 监听    | `sudo ss -tulnp`                                            |
| 查看连接摘要           | `ss -s`                                                     |
| 端口是否被占用          | `sudo ss -tlnp \| grep :8080`                               |
| 统计各状态连接数         | `ss -tn \| awk '{print $1}' \| sort \| uniq -c \| sort -rn` |
| 查看 TIME_WAIT 连接  | `ss -tn state TIME-WAIT`                                    |
| 查看 CLOSE_WAIT 连接 | `ss -tn state CLOSE-WAIT`                                   |
| 按目标地址过滤          | `ss -tn dst 192.168.1.100`                                  |
| 按目标端口过滤          | `ss -tn dport = :443`                                       |
| 查看某进程的连接         | `sudo ss -tnp \| grep nginx`                                |
| 持续监控             | `watch -n 1 ss -tn`                                         |
| 查看路由表            | `ip route`                                                  |
| 查看接口统计           | `ip -s link`                                                |
| 兼容老系统用 netstat   | `sudo netstat -tlnp`                                        |

## See Also

- [[process-management|进程管理]] — ps、top、kill、nohup 后台运行
- [[bash-basics|Bash 基础]] — 管道、重定向等 Shell 技巧
- [ss 官方文档](https://man7.org/linux/man-pages/man8/ss.8.html)
- [netstat 官方文档](https://man7.org/linux/man-pages/man8/netstat.8.html)
