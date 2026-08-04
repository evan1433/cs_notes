---
title: SSH 协议与使用指南
description: SSH（Secure Shell）协议的基础概念、工作原理、认证方式、配置文件、常用命令、安全配置、端口转发等完整技术指南
tags:
  - ssh
  - security
  - network
  - devops
date: 2026-04-24
---

# SSH 协议与使用指南

SSH（Secure Shell）是一种加密的网络传输协议，用于在不安全的网络环境中安全地传输数据。SSH 广泛用于远程登录、命令执行、文件传输等场景。

## SSH 基础概念

### 什么是 SSH

SSH 是一种网络协议，用于计算机之间的加密登录和安全数据传输。

**主要功能**：

- 远程登录（替代 Telnet、rlogin）
- 远程命令执行
- 文件传输（SCP、SFTP）
- 端口转发（隧道）
- 代理服务

**SSH 版本**：

- SSH-1：第一版，已弃用（存在安全漏洞）
- SSH-2：第二版，当前主流版本（更安全、功能更强）

### SSH 的优势

相比传统的 Telnet、rsh、rlogin：

1. **加密传输**：所有数据加密，防止窃听
2. **身份认证**：多种认证方式，防止冒充
3. **数据完整性**：防止数据篡改
4. **端口转发**：加密其他协议的传输
5. **跨平台**：支持多种操作系统

## SSH 工作原理

### SSH 协议架构

SSH 协议分为三层：

```
┌─────────────────────────────────┐
│   SSH 应用层（SSH Connection）   │  ← 远程命令、文件传输、端口转发
├─────────────────────────────────┤
│   SSH 认证层（SSH Authentication）│  ← 用户身份认证
├─────────────────────────────────┤
│   SSH 传输层（SSH Transport）     │  ← 加密、完整性、服务器认证
└─────────────────────────────────┘
```

### SSH 连接过程

SSH 连接分为三个阶段：

#### 1. SSH 传输层协议（服务器认证）

**步骤**：

1. 客户端发起 TCP 连接（默认端口 22）
2. 双方协商协议版本和算法（加密算法、MAC 算法、压缩算法）
3. 服务器发送主机公钥（用于服务器认证）
4. 客户端验证服务器身份（首次连接提示保存公钥）
5. 双方生成会话密钥（使用 Diffie-Hellman 密钥交换）
6. 建立加密通道

**首次连接提示**：

```bash
$ ssh user@server.example.com
The authenticity of host 'server.example.com (192.168.1.100)' can't be established.
ECDSA key fingerprint is SHA256:abc123...
Are you sure you want to continue connecting (yes/no)? yes
Warning: Permanently added 'server.example.com' (ECDSA) to the list of known hosts.
```

- 客户端将服务器公钥保存到 `~/.ssh/known_hosts`
- 后续连接会验证服务器公钥是否匹配

#### 2. SSH 认证层协议（用户认证）

SSH 支持多种认证方式：

**认证方式优先级**：

1. 公钥认证（publickey）
2. 主机认证（hostbased）
3. 密码认证（password）
4. 键盘交互认证（keyboard-interactive）

**认证流程**：

```bash
# 1. 客户端发送认证请求
# 2. 服务器返回支持的认证方式
# 3. 客户端选择认证方式并发送认证数据
# 4. 服务器验证并返回结果
```

#### 3. SSH 连接层协议（会话管理）

建立认证后，SSH 连接层管理会话：

- **会话通道（Session）**：远程命令执行、Shell 登录
- **X11 转发**：远程图形界面
- **端口转发**：TCP 隧道
- **SFTP 协议**：文件传输

### SSH 加密算法

SSH 支持多种加密算法：

**加密算法（对称加密）**：

- `aes256-ctr`：AES-256（推荐）
- `aes192-ctr`：AES-192
- `aes128-ctr`：AES-128
- `chacha20-poly1305`：ChaCha20（推荐）

**密钥交换算法（非对称加密）**：

- `curve25519-sha256`：Curve25519（推荐）
- `ecdh-sha2-nistp256`：ECDH
- `diffie-hellman-group14-sha256`：DH-14

**MAC 算法（消息认证码）**：

- `hmac-sha2-256`：SHA-256（推荐）
- `hmac-sha2-512`：SHA-512
- `umac-64-etm`：UMAC-64

**查看支持的算法**：

```bash
# 查看客户端支持的算法
ssh -Q cipher        # 加密算法
ssh -Q mac           # MAC 算法
ssh -Q kex           # 密钥交换算法
ssh -Q key           # 公钥算法

# 查看服务器支持的算法
sshd -Q cipher
sshd -Q mac
```

## SSH 认证方式

### 密码认证

最简单的认证方式，但安全性较低。

**使用方式**：

```bash
ssh user@server.example.com
# 输入密码
```

**缺点**：

- 密码容易被暴力破解
- 密码可能被窃取
- 无法自动化登录

### 公钥认证

最推荐的认证方式，安全性高，支持自动化。

#### 生成 SSH 密钥对

**生成密钥对**：

```bash
# 生成 RSA 密钥（传统）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 生成 Ed25519 密钥（推荐，更安全、更快速）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 生成 ECDSA 密钥
ssh-keygen -t ecdsa -b 521 -C "your_email@example.com"
```

**参数说明**：

- `-t`：密钥类型（rsa、ed25519、ecdsa）
- `-b`：密钥长度（RSA 推荐 4096）
- `-C`：注释（通常为邮箱）
- `-f`：指定密钥文件名（默认 `~/.ssh/id_rsa`）

**生成过程**：

```bash
$ ssh-keygen -t ed25519 -C "user@example.com"
Generating public/private ed25519 key pair.
Enter file in which to save the key (~/.ssh/id_ed25519): 
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
Your identification has been saved in ~/.ssh/id_ed25519
Your public key has been saved in ~/.ssh/id_ed25519.pub
```

**密钥文件**：

- 私钥：`~/.ssh/id_ed25519`（保密，不能泄露）
- 公钥：`~/.ssh/id_ed25519.pub`（公开，上传到服务器）

#### 上传公钥到服务器

**方法 1：使用 ssh-copy-id（推荐）**：

```bash
# 自动上传公钥到服务器
ssh-copy-id user@server.example.com

# 指定公钥文件
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server.example.com
```

**方法 2：手动上传公钥**：

```bash
# 查看公钥内容
cat ~/.ssh/id_ed25519.pub

# 登录服务器，添加公钥到 authorized_keys
ssh user@server.example.com
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3Nza... user@example.com" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**方法 3：使用 SCP 上传**：

```bash
# 上传公钥到服务器
scp ~/.ssh/id_ed25519.pub user@server.example.com:~/.ssh/

# 在服务器上添加到 authorized_keys
ssh user@server.example.com
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

#### 使用公钥登录

```bash
# 直接登录（无需密码）
ssh user@server.example.com

# 指定私钥文件
ssh -i ~/.ssh/id_ed25519 user@server.example.com
```

#### 密钥管理

**查看密钥指纹**：

```bash
# 查看私钥指纹
ssh-keygen -l -f ~/.ssh/id_ed25519

# 查看公钥指纹
ssh-keygen -l -f ~/.ssh/id_ed25519.pub
```

**修改密钥密码**：

```bash
# 修改私钥密码
ssh-keygen -p -f ~/.ssh/id_ed25519
```

**验证密钥**：

```bash
# 测试 SSH 连接
ssh -v user@server.example.com

# 查看认证过程
ssh -vvv user@server.example.com
```

### 主机认证

基于客户端主机密钥的认证（较少使用）。

**配置**：

```bash
# 客户端生成主机密钥
ssh-keygen -t rsa -f /etc/ssh/ssh_host_key

# 服务器配置允许主机认证
# /etc/ssh/sshd_config
HostbasedAuthentication yes
IgnoreRhosts no
```

### 键盘交互认证

用于双因素认证等复杂认证场景。

**示例**：

```bash
# Google Authenticator 双因素认证
ssh user@server.example.com
# 输入密码
# 输入验证码
```

## SSH 配置文件

### 客户端配置文件

**位置**：`~/.ssh/config` 或 `/etc/ssh/ssh_config`

#### ~/.ssh/config 配置示例

```ssh
# 全局配置
Host *
    # 默认用户
    User admin
    # 默认端口
    Port 22
    # 保持连接
    ServerAliveInterval 60
    ServerAliveCountMax 3
    # 连接超时
    ConnectTimeout 10
    # 使用密钥认证
    PreferredAuthentications publickey
    # 指定密钥文件
    IdentityFile ~/.ssh/id_ed25519

# 特定主机配置
Host server1
    HostName server1.example.com
    User deploy
    Port 2222
    IdentityFile ~/.ssh/server1_key

Host server2
    HostName 192.168.1.100
    User root
    IdentityFile ~/.ssh/server2_key

# 简化配置（使用别名）
Host dev
    HostName dev.example.com
    User developer

# 通配符配置
Host *.example.com
    User admin
    ForwardAgent yes

# SSH 隧道配置
Host tunnel
    HostName server.example.com
    LocalForward 8080 localhost:80
    DynamicForward 1080

# 跳板机配置（ProxyJump）
Host target-server
    HostName 192.168.2.100
    User admin
    ProxyJump jump-server

Host jump-server
    HostName jump.example.com
    User jump-user
```

#### 常用配置选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `Host` | 主机别名 | `Host server1` |
| `HostName` | 主机地址 | `HostName 192.168.1.100` |
| `User` | 登录用户 | `User admin` |
| `Port` | SSH 端口 | `Port 2222` |
| `IdentityFile` | 私钥文件 | `IdentityFile ~/.ssh/id_ed25519` |
| `PreferredAuthentications` | 认证方式 | `PreferredAuthentications publickey,password` |
| `ServerAliveInterval` | 心跳间隔（秒） | `ServerAliveInterval 60` |
| `ServerAliveCountMax` | 心跳次数 | `ServerAliveCountMax 3` |
| `ConnectTimeout` | 连接超时（秒） | `ConnectTimeout 10` |
| `ForwardAgent` | 转发认证代理 | `ForwardAgent yes` |
| `LocalForward` | 本地端口转发 | `LocalForward 8080 localhost:80` |
| `RemoteForward` | 远程端口转发 | `RemoteForward 8080 localhost:80` |
| `DynamicForward` | 动态端口转发（SOCKS） | `DynamicForward 1080` |
| `ProxyJump` | 跳板机 | `ProxyJump jump-server` |
| `StrictHostKeyChecking` | 主机密钥检查 | `StrictHostKeyChecking no` |
| `UserKnownHostsFile` | 已知主机文件 | `UserKnownHostsFile ~/.ssh/known_hosts` |

#### 使用配置文件

```bash
# 使用别名连接
ssh server1  # 等同于 ssh -p 2222 deploy@server1.example.com

# 使用通配符配置
ssh dev.example.com  # 自动使用 User admin

# 使用隧道配置
ssh tunnel  # 自动建立端口转发
```

### 服务器配置文件

**位置**：`/etc/ssh/sshd_config`

#### sshd_config 配置示例

```ssh
# SSH 协议版本
Protocol 2

# 监听端口
Port 22
# 监听地址（0.0.0.0 表示所有地址）
ListenAddress 0.0.0.0

# 主机密钥文件
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key


# 认证配置
# 允许的认证方式
AuthenticationMethods publickey,password
PubkeyAuthentication yes
PasswordAuthentication no  # 禁用密码认证（推荐）

# 公钥认证配置
AuthorizedKeysFile .ssh/authorized_keys
AuthorizedKeysCommand none
AuthorizedKeysCommandUser none

# 密码认证配置
PermitEmptyPasswords no  # 禁止空密码
ChallengeResponseAuthentication no

# 用户权限
PermitRootLogin no  # 禁止 root 登录（推荐）
AllowUsers admin deploy  # 允许的用户列表
DenyUsers hacker  # 禁止的用户列表
AllowGroups ssh-users  # 允许的用户组
DenyGroups blocked-users  # 禁止的用户组

# 会话配置
LoginGraceTime 60  # 登录超时（秒）
MaxAuthTries 3  # 最大认证尝试次数
MaxSessions 10  # 最大会话数
MaxStartups 10:30:100  # 最大连接启动数

# 连接保持
ClientAliveInterval 300  # 心跳间隔（秒）
ClientAliveCountMax 2  # 心跳次数

# 加密算法配置
Ciphers aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256,hmac-sha2-512
KexAlgorithms curve25519-sha256,ecdh-sha2-nistp256

# 端口转发
AllowTcpForwarding yes
X11Forwarding no  # 禁用 X11 转发
GatewayPorts no  # 禁用网关端口

# 其他配置
UseDNS no  # 禁用 DNS 解析（提高速度）
PrintMotd no  # 不显示 MOTD
PrintLastLog yes  # 显示上次登录时间
Banner /etc/ssh/banner  # 登录提示信息

# 日志配置
SyslogFacility AUTH
LogLevel INFO

# 子系统配置
Subsystem sftp /usr/lib/openssh/sftp-server
```

#### 安全配置建议

**推荐配置**：

```ssh
# 禁用密码认证，仅使用公钥认证
PasswordAuthentication no
PubkeyAuthentication yes

# 禁止 root 登录
PermitRootLogin no

# 限制用户和用户组
AllowUsers admin deploy

# 限制认证尝试次数
MaxAuthTries 3

# 设置登录超时
LoginGraceTime 60

# 禁用 X11 转发
X11Forwarding no

# 禁用端口转发（如不需要）
AllowTcpForwarding no

# 使用强加密算法
Ciphers aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256,hmac-sha2-512
```

#### 修改配置后重启服务

```bash
# 检查配置文件语法
sshd -t

# 重启 SSH 服务
sudo systemctl restart sshd
sudo service ssh restart

# 或使用 reload（不中断现有连接）
sudo systemctl reload sshd
```

## SSH 常用命令

### ssh 命令

#### 基本用法

```bash
# 远程登录
ssh user@host

# 指定端口
ssh -p 2222 user@host

# 指定私钥文件
ssh -i ~/.ssh/id_ed25519 user@host

# 使用配置文件别名
ssh server1

# 执行远程命令
ssh user@host 'command'

# 执行多个命令
ssh user@host 'command1; command2; command3'

# 使用交互式 Shell
ssh user@host -t 'command'  # -t 强制分配伪终端
```

#### 调试选项

```bash
# 显示调试信息（v、vv、vvv 级别递增）
ssh -v user@host
ssh -vv user@host
ssh -vvv user@host

# 显示版本
ssh -V

# 显示支持的算法
ssh -Q cipher
ssh -Q mac
ssh -Q kex
```

#### 连接保持

```bash
# 心跳检测（防止断连）
ssh -o ServerAliveInterval=60 user@host

# 心跳次数
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=3 user@host

# 连接超时
ssh -o ConnectTimeout=10 user@host
```

#### 后台运行

```bash
# 后台运行 SSH 命令
ssh -f user@host 'command'

# 后台运行端口转发
ssh -f -N -L 8080:localhost:80 user@host
```

### scp 命令

SCP（Secure Copy）用于 SSH 协议的文件传输。

#### 基本用法

```bash
# 本地文件上传到远程
scp local_file user@host:/remote/path/

# 远程文件下载到本地
scp user@host:/remote/file local_path/

# 复制目录（递归）
scp -r local_dir/ user@host:/remote/path/

# 指定端口
scp -P 2222 local_file user@host:/remote/path/

# 指定私钥文件
scp -i ~/.ssh/id_ed25519 local_file user@host:/remote/path/

# 保留文件属性（权限、时间戳）
scp -p local_file user@host:/remote/path/

# 显示传输进度
scp -v local_file user@host:/remote/path/

# 限制传输速度（KB/s）
scp -l 1000 local_file user@host:/remote/path/
```

#### 远程到远程复制

```bash
# 远程服务器 A 到远程服务器 B
scp user1@host1:/file user2@host2:/path/

# 通过本地转发（-3 选项）
scp -3 user1@host1:/file user2@host2:/path/
```

### sftp 命令

SFTP（SSH File Transfer Protocol）提供交互式文件传输。

#### 基本用法

```bash
# 连接 SFTP
sftp user@host

# 指定端口
sftp -P 2222 user@host

# 指定私钥文件
sftp -i ~/.ssh/id_ed25519 user@host
```

#### SFTP 交互命令

```bash
sftp> help  # 查看帮助

# 本地操作（前缀 l）
sftp> lcd /local/path      # 切换本地目录
sftp> lls                  # 列出本地文件
sftp> lmkdir local_dir     # 创建本地目录
sftp> lpwd                 # 显示本地当前目录

# 远程操作
sftp> cd /remote/path      # 切换远程目录
sftp> ls                   # 列出远程文件
sftp> mkdir remote_dir     # 创建远程目录
sftp> pwd                  # 显示远程当前目录

# 文件传输
sftp> get remote_file      # 下载文件
sftp> get remote_file local_name  # 下载并重命名
sftp> mget *.txt           # 批量下载

sftp> put local_file       # 上传文件
sftp> put local_file remote_name  # 上传并重命名
sftp> mput *.txt           # 批量上传

# 其他命令
sftp> rm remote_file       # 删除远程文件
sftp> rename old new       # 重命名远程文件
sftp> chmod 755 file       # 修改远程文件权限
sftp> exit                 # 退出 SFTP
sftp> quit                 # 退出 SFTP
```

### ssh-keygen 命令

#### 生成密钥

```bash
# 生成 RSA 密钥
ssh-keygen -t rsa -b 4096

# 生成 Ed25519 密钥（推荐）
ssh-keygen -t ed25519

# 生成 ECDSA 密钥
ssh-keygen -t ecdsa -b 521

# 指定密钥文件名
ssh-keygen -t ed25519 -f ~/.ssh/my_key

# 添加注释
ssh-keygen -t ed25519 -C "user@example.com"

# 不设置密码（自动化场景）
ssh-keygen -t ed25519 -N ""

# 指定密码
ssh-keygen -t ed25519 -N "my_password"
```

#### 密钥管理

```bash
# 查看密钥指纹
ssh-keygen -l -f ~/.ssh/id_ed25519

# 查看公钥内容
ssh-keygen -y -f ~/.ssh/id_ed25519

# 修改密钥密码
ssh-keygen -p -f ~/.ssh/id_ed25519

# 移除密钥密码
ssh-keygen -p -f ~/.ssh/id_ed25519 -N ""

# 验证密钥有效性
ssh-keygen -y -f ~/.ssh/id_ed25519
```

### ssh-copy-id 命令

```bash
# 上传默认公钥到服务器
ssh-copy-id user@host

# 指定公钥文件
ssh-copy-id -i ~/.ssh/my_key.pub user@host

# 指定端口
ssh-copy-id -p 2222 user@host
```

### ssh-agent 命令

SSH Agent 用于管理私钥，避免重复输入密码。

#### 使用 ssh-agent

```bash
# 启动 ssh-agent
eval "$(ssh-agent -s)"

# 添加私钥到 agent
ssh-add ~/.ssh/id_ed25519

# 添加所有私钥
ssh-add

# 添加私钥并设置超时（秒）
ssh-add -t 3600 ~/.ssh/id_ed25519

# 列出已添加的密钥
ssh-add -l

# 删除所有密钥
ssh-add -D

# 删除指定密钥
ssh-add -d ~/.ssh/id_ed25519

# 锁定 agent（需要密码解锁）
ssh-add -x

# 解锁 agent
ssh-add -X
```

#### 配置自动启动 ssh-agent

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
# 自动启动 ssh-agent
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval "$(ssh-agent -s)"
  ssh-add ~/.ssh/id_ed25519
fi

# 或使用更智能的配置
SSH_ENV="$HOME/.ssh/environment"

function start_agent {
    echo "Initializing new SSH agent..."
    ssh-agent -s | sed 's/^echo/#echo/' > "$SSH_ENV"
    echo succeeded
    chmod 600 "$SSH_ENV"
    . "$SSH_ENV" > /dev/null
    ssh-add
}

# Source SSH settings, if applicable
if [ -f "$SSH_ENV" ]; then
    . "$SSH_ENV" > /dev/null
    ps -ef | grep $SSH_AGENT_PID | grep ssh-agent > /dev/null || {
        start_agent;
    }
else
    start_agent;
fi
```

## SSH 端口转发

SSH 端口转发（SSH Tunneling）用于加密其他协议的传输或访问受限网络。

### 本地端口转发

将远程服务的端口映射到本地端口。

#### 基本用法

```bash
# 格式：-L [本地端口]:[目标主机]:[目标端口] [SSH服务器]
ssh -L 8080:localhost:80 user@server.example.com

# 访问远程 MySQL（远程服务器上的服务）
ssh -L 3306:localhost:3306 user@server.example.com

# 访问远程服务器能访问的服务（跳板机场景）
ssh -L 8080:192.168.2.100:80 user@jump-server.example.com
```

#### 使用示例

**访问远程数据库**：

```bash
# 远程 MySQL 服务器（仅允许内网访问）
ssh -L 3306:localhost:3306 user@db-server.example.com

# 本地连接 MySQL
mysql -h 127.0.0.1 -P 3306 -u dbuser -p
```

**访问内网 Web 服务**：

```bash
# 通过跳板机访问内网 Web 服务
ssh -L 8080:192.168.2.100:80 user@jump-server.example.com

# 本地浏览器访问
http://localhost:8080
```

**后台运行端口转发**：

```bash
# -f: 后台运行
# -N: 不执行远程命令（仅端口转发）
ssh -f -N -L 8080:localhost:80 user@server.example.com
```

#### 配置文件配置

```ssh
Host tunnel-web
    HostName server.example.com
    User admin
    LocalForward 8080 localhost:80

Host tunnel-db
    HostName server.example.com
    User admin
    LocalForward 3306 localhost:3306
```

```bash
# 使用配置文件
ssh tunnel-web
ssh tunnel-db
```

### 远程端口转发

将本地服务的端口映射到远程服务器端口。

#### 基本用法

```bash
# 格式：-R [远程端口]:[目标主机]:[目标端口] [SSH服务器]
ssh -R 8080:localhost:80 user@server.example.com

# 远程服务器监听 8080，转发到本地 80
ssh -R 8080:localhost:80 user@server.example.com
```

#### 使用示例

**本地 Web 服务暴露到远程服务器**：

```bash
# 本地运行 Web 服务（localhost:80）
# 远程服务器可通过 8080 访问本地服务
ssh -R 8080:localhost:80 user@server.example.com

# 远程服务器访问
curl http://localhost:8080
```

**远程端口转发配置**：

```ssh
Host reverse-tunnel
    HostName server.example.com
    User admin
    RemoteForward 8080 localhost:80
```

#### 注意事项

远程端口转发默认只允许远程服务器本地访问，如需外部访问，需配置：

```ssh
# sshd_config 配置
GatewayPorts yes  # 或 GatewayPorts clientspecified
```

```bash
# 指定远程监听地址
ssh -R 0.0.0.0:8080:localhost:80 user@server.example.com
```

### 动态端口转发

创建 SOCKS 代理，动态转发所有流量。

#### 基本用法

```bash
# 格式：-D [本地端口] [SSH服务器]
ssh -D 1080 user@server.example.com

# 创建 SOCKS5 代理（本地 1080 端口）
ssh -D 1080 user@server.example.com
```

#### 使用示例

**创建 SOCKS 代理**：

```bash
# 后台运行 SOCKS 代理
ssh -f -N -D 1080 user@server.example.com

# 配置浏览器使用 SOCKS 代理
# SOCKS Host: 127.0.0.1, Port: 1080

# 使用 curl 测试
curl --socks5 127.0.0.1:1080 http://example.com
```

**配置文件配置**：

```ssh
Host socks-proxy
    HostName server.example.com
    User admin
    DynamicForward 1080
```

```bash
# 使用配置文件
ssh socks-proxy
```

### X11 转发

转发远程图形界面到本地。

#### 基本用法

```bash
# 启用 X11 转发
ssh -X user@server.example.com

# 运行远程图形程序
ssh -X user@server.example.com 'xclock'
```

#### 配置

**服务器配置**：

```ssh
# sshd_config
X11Forwarding yes
X11DisplayOffset 10
X11UseLocalhost yes
```

**客户端配置**：

```ssh
# ~/.ssh/config
Host *
    ForwardX11 yes
```

#### 注意事项

- 本地需要运行 X Server（Linux 默认有，macOS 需要 XQuartz，Windows 需要 Xming）
- X11 转发有安全风险，谨慎使用

### 跳板机

通过跳板机连接目标服务器。

#### 使用 ProxyJump（推荐）

```bash
# 通过跳板机连接目标服务器
ssh -J jump-user@jump-server target-user@target-server

# 多级跳板机
ssh -J jump1@server1,jump2@server2 target-user@target-server
```

#### 配置文件配置

```ssh
Host target-server
    HostName 192.168.2.100
    User admin
    ProxyJump jump-server

Host jump-server
    HostName jump.example.com
    User jump-user
```

```bash
# 使用配置文件（自动通过跳板机）
ssh target-server
```

#### 使用 ProxyCommand（旧方法）

```bash
# 通过跳板机连接目标服务器
ssh -o ProxyCommand="ssh -W %h:%p jump-user@jump-server" target-user@target-server
```

```ssh
# ~/.ssh/config
Host target-server
    HostName 192.168.2.100
    User admin
    ProxyCommand ssh -W %h:%p jump-user@jump-server
```

## SSH 安全配置

### 禁用密码认证

最重要的安全配置，防止暴力破解。

```ssh
# sshd_config
PasswordAuthentication no
PubkeyAuthentication yes
```

### 禁止 root 登录

防止攻击者直接尝试 root 登录。

```ssh
# sshd_config
PermitRootLogin no
```

### 修改默认端口

减少自动化扫描攻击。

```ssh
# sshd_config
Port 2222  # 或其他非标准端口
```

```bash
# 客户端连接
ssh -p 2222 user@host
```

### 限制用户和用户组

仅允许特定用户 SSH 登录。

```ssh
# sshd_config
AllowUsers admin deploy
AllowGroups ssh-users

# 或禁止特定用户
DenyUsers hacker
DenyGroups blocked-users
```

### 使用强加密算法

禁用弱加密算法。

```ssh
# sshd_config
Ciphers aes256-ctr,aes192-ctr,aes128-ctr,chacha20-poly1305@openssh.com
MACs hmac-sha2-256,hmac-sha2-512,umac-64-etm@openssh.com,umac-128-etm@openssh.com
KexAlgorithms curve25519-sha256,ecdh-sha2-nistp256,diffie-hellman-group14-sha256
```

### 限制认证尝试次数

防止暴力破解。

```ssh
# sshd_config
MaxAuthTries 3
MaxStartups 10:30:100
```

### 使用 Fail2Ban

自动封禁暴力破解的 IP。

**安装 Fail2Ban**：

```bash
# Debian/Ubuntu
sudo apt install fail2ban

# CentOS/RHEL
sudo yum install fail2ban
```

**配置 SSH 保护**：

```bash
# /etc/fail2ban/jail.local
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
findtime = 600
bantime = 3600
```

**参数说明**：

- `maxretry`：最大尝试次数
- `findtime`：检测时间窗口（秒）
- `bantime`：封禁时间（秒）

### 使用双因素认证

增强安全性，结合 Google Authenticator。

**安装**：

```bash
# Debian/Ubuntu
sudo apt install libpam-google-authenticator

# CentOS/RHEL
sudo yum install google-authenticator
```

**配置**：

```bash
# 运行配置工具
google-authenticator

# /etc/pam.d/sshd
auth required pam_google_authenticator.so

# /etc/ssh/sshd_config
ChallengeResponseAuthentication yes
AuthenticationMethods publickey,keyboard-interactive
```

### 密钥管理安全

**私钥安全**：

```bash
# 私钥权限必须是 600
chmod 600 ~/.ssh/id_ed25519

# 私钥不能泄露，不要上传到服务器
# 不要通过邮件、聊天工具发送私钥

# 设置私钥密码
ssh-keygen -p -f ~/.ssh/id_ed25519
```

**公钥管理**：

```bash
# 公钥权限 644
chmod 644 ~/.ssh/id_ed25519.pub

# authorized_keys 权限 600
chmod 600 ~/.ssh/authorized_keys

# .ssh 目录权限 700
chmod 700 ~/.ssh
```

### 监控 SSH 登录

**查看登录日志**：

```bash
# 查看认证日志
tail -f /var/log/auth.log        # Debian/Ubuntu
tail -f /var/log/secure          # CentOS/RHEL

# 查看成功登录
grep "Accepted password" /var/log/auth.log
grep "Accepted publickey" /var/log/auth.log

# 查看失败登录
grep "Failed password" /var/log/auth.log
grep "Connection closed" /var/log/auth.log

# 查看当前登录用户
who
w
```

**使用 last 命令**：

```bash
# 查看登录历史
last

# 查看 SSH 登录历史
last -f /var/log/wtmp

# 查看失败登录
lastb
```

## SSH 最佳实践

### 客户端最佳实践

1. **使用 Ed25519 密钥**：

```bash
ssh-keygen -t ed25519 -C "user@example.com"
```

2. **使用 SSH 配置文件**：

```ssh
# ~/.ssh/config
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    PreferredAuthentications publickey
```

3. **使用 ssh-agent 管理密钥**：

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

4. **使用跳板机**：

```ssh
Host target-server
    ProxyJump jump-server
```

5. **定期更新密钥**：

```bash
# 每年更新一次密钥
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_2026
```

### 服务器最佳实践

1. **禁用密码认证**：

```ssh
PasswordAuthentication no
PubkeyAuthentication yes
```

2. **禁止 root 登录**：

```ssh
PermitRootLogin no
```

3. **修改默认端口**：

```ssh
Port 2222
```

4. **限制用户**：

```ssh
AllowUsers admin deploy
```

5. **使用 Fail2Ban**：

```bash
sudo apt install fail2ban
```

6. **定期审计日志**：

```bash
grep "Failed" /var/log/auth.log
```

7. **定期更新 SSH 版本**：

```bash
sudo apt update
sudo apt upgrade openssh-server
```

### 密钥管理最佳实践

1. **使用强密钥**：

```bash
ssh-keygen -t ed25519 -b 4096
```

2. **设置密钥密码**：

```bash
ssh-keygen -p -f ~/.ssh/id_ed25519
```

3. **妥善保管私钥**：

- 不要上传到服务器
- 不要通过邮件发送
- 不要存储在云盘
- 使用硬件密钥（YubiKey）

4. **定期轮换密钥**：

```bash
# 每年生成新密钥
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_new
ssh-copy-id -i ~/.ssh/id_ed25519_new.pub user@host
```

5. **备份密钥**：

```bash
# 加密备份私钥
tar -czf - ~/.ssh/id_ed25519 | gpg -c > ssh_keys.tar.gz.gpg

# 解密恢复
gpg -d ssh_keys.tar.gz.gpg | tar -xzf -
```

### 端口转发最佳实践

1. **使用本地端口转发访问内网服务**：

```bash
ssh -L 3306:localhost:3306 user@db-server
```

2. **使用动态端口转发创建代理**：

```bash
ssh -D 1080 user@proxy-server
```

3. **后台运行端口转发**：

```bash
ssh -f -N -L 8080:localhost:80 user@server
```

4. **使用配置文件管理端口转发**：

```ssh
Host tunnel-web
    LocalForward 8080 localhost:80
```

## SSH 故障排查

### 连接失败

**错误：Connection refused**

```bash
# 检查 SSH 服务是否运行
sudo systemctl status sshd

# 启动 SSH 服务
sudo systemctl start sshd

# 检查端口监听
sudo netstat -tlnp | grep 22
```

**错误：Connection timed out**

```bash
# 检查防火墙
sudo iptables -L -n
sudo firewall-cmd --list-all

# 检查网络连通性
ping server.example.com
telnet server.example.com 22
```

**错误：Host key verification failed**

```bash
# 服务器密钥变更，删除旧密钥
ssh-keygen -R server.example.com

# 或手动编辑 known_hosts
vim ~/.ssh/known_hosts
```

### 认证失败

**错误：Permission denied (publickey)**

```bash
# 检查公钥是否上传
ssh user@host "cat ~/.ssh/authorized_keys"

# 检查私钥权限
ls -l ~/.ssh/id_ed25519
chmod 600 ~/.ssh/id_ed25519

# 检查 authorized_keys 权限
ssh user@host "ls -l ~/.ssh/authorized_keys"
ssh user@host "chmod 600 ~/.ssh/authorized_keys"

# 检查 .ssh 目录权限
ssh user@host "ls -ld ~/.ssh"
ssh user@host "chmod 700 ~/.ssh"
```

**错误：Too many authentication failures**

```bash
# 指定密钥文件
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes user@host

# 或配置文件
Host *
    IdentitiesOnly yes
    IdentityFile ~/.ssh/id_ed25519
```

### 连接断开

**自动断开**：

```bash
# 配置心跳检测
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=3 user@host

# 或配置文件
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### 调试方法

**使用详细输出**：

```bash
# 显示连接过程
ssh -v user@host

# 显示详细调试信息
ssh -vvv user@host
```

**检查服务器日志**：

```bash
# 查看 SSH 服务日志
tail -f /var/log/auth.log
tail -f /var/log/secure

# 查看 systemd 日志
journalctl -u sshd -f
```

## SSH 相关工具

### sshpass

用于自动化 SSH 密码登录（不推荐，有安全风险）。

```bash
# 安装 sshpass
sudo apt install sshpass

# 使用密码登录
sshpass -p 'password' ssh user@host

# 从文件读取密码
sshpass -f password_file ssh user@host

# 从环境变量读取密码
export SSHPASS='password'
sshpass -e ssh user@host
```

### autossh

自动重连 SSH 连接，用于持久化端口转发。

```bash
# 安装 autossh
sudo apt install autossh

# 自动重连端口转发
autossh -M 0 -f -N -L 8080:localhost:80 user@host

# 参数说明
# -M 0: 不使用监控端口（依赖 SSH 心跳）
# -f: 后台运行
# -N: 不执行远程命令
```

### sshuttle

通过 SSH 创建透明代理（无需配置 SOCKS）。

```bash
# 安装 sshuttle
pip install sshuttle

# 创建透明代理（转发所有流量）
sshuttle -r user@host 0/0

# 仅转发特定网段
sshuttle -r user@host 192.168.0.0/16

# 排除特定网段
sshuttle -r user@host 0/0 --exclude 192.168.1.0/24
```

### parallel-ssh

并行 SSH 工具，批量执行命令。

```bash
# 安装 parallel-ssh
pip install parallel-ssh

# 批量执行命令
parallel-ssh -h hosts.txt -l user 'command'

# hosts.txt 文件内容
server1.example.com
server2.example.com
server3.example.com
```

### SSH 客户端工具

**Windows**：

- PuTTY：经典 SSH 客户端
- WinSCP：SCP/SFTP 客户端
- MobaXterm：多功能终端（推荐）
- Windows Terminal + OpenSSH：Windows 10+ 内置

**macOS**：

- Terminal.app：系统自带终端
- iTerm2：增强终端（推荐）
- Termius：跨平台 SSH 客户端

**Linux**：

- OpenSSH：默认 SSH 客户端
- Terminator：多窗口终端
- Byobu：终端增强工具

**跨平台**：

- Termius：支持 Windows、macOS、Linux、iOS、Android
- Royal TSX：macOS 远程管理工具
- SecureCRT：商业 SSH 客户端

## SSH 常用命令速查表

### 连接命令

```bash
ssh user@host                    # 基本连接
ssh -p 2222 user@host            # 指定端口
ssh -i key_file user@host        # 指定密钥
ssh -v user@host                 # 调试模式
ssh -J jump user@target          # 跳板机
ssh -L 8080:localhost:80 user@host  # 本地端口转发
ssh -R 8080:localhost:80 user@host  # 远程端口转发
ssh -D 1080 user@host            # 动态端口转发
```

### 文件传输

```bash
scp file user@host:/path         # 上传文件
scp user@host:/file /path        # 下载文件
scp -r dir user@host:/path       # 上传目录
scp -P 2222 file user@host:/path # 指定端口

sftp user@host                   # SFTP 连接
```

### 密钥管理

```bash
ssh-keygen -t ed25519            # 生成密钥
ssh-keygen -p -f key_file        # 修改密码
ssh-keygen -l -f key_file        # 查看指纹
ssh-copy-id user@host            # 上传公钥
ssh-add key_file                 # 添加密钥到 agent
ssh-add -l                       # 列出密钥
ssh-add -D                       # 删除所有密钥
```

### 服务器管理

```bash
systemctl start sshd             # 启动 SSH 服务
systemctl stop sshd              # 停止 SSH 服务
systemctl restart sshd           # 重启 SSH 服务
systemctl status sshd            # 查看服务状态
sshd -t                          # 检查配置语法
```

### 日志查看

```bash
tail -f /var/log/auth.log        # 查看认证日志
last                             # 查看登录历史
lastb                            # 查看失败登录
who                              # 查看当前登录
w                                # 查看当前登录详情
```

## 总结

SSH 是运维和开发人员的必备技能，掌握 SSH 的核心概念和最佳实践对于系统安全和效率至关重要。

**核心要点**：

1. 使用公钥认证，禁用密码认证
2. 使用 Ed25519 密钥（更安全、更快速）
3. 配置 SSH 配置文件简化连接
4. 使用跳板机访问内网服务器
5. 定期审计 SSH 日志
6. 使用 Fail2Ban 防止暴力破解
7. 妥善保管私钥，定期轮换密钥

**推荐阅读**：

- [OpenSSH 官方文档](https://www.openssh.com/manual.html)
- [SSH 配置最佳实践](https://www.ssh.com/academy/ssh/sshd_config)
- [SSH 端口转发详解](https://www.ssh.com/academy/ssh/sshd_config)