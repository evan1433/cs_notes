---
title: Nginx 全面指南
description: Nginx 架构原理、安装、配置语法、虚拟主机、反向代理、负载均衡、HTTPS、性能调优、安全加固与常见排错
tags:
  - nginx
  - web-server
  - reverse-proxy
  - devops
date: 2026-08-12
---

# Nginx 全面指南

Nginx（发音 "engine-x"）是一款轻量级、高性能的 HTTP 服务器、反向代理服务器及邮件（IMAP/POP3）代理服务器。它以高并发、低内存、丰富的模块生态著称，是当前生产环境中最常用的 Web 服务器之一。

> **适用版本**：本文以 Nginx 1.24+（Stable）为准，部分新特性（如 HTTP/3）需要 1.25+。

## 概述

### Nginx 能做什么

| 能力 | 典型场景 |
|------|----------|
| 静态 HTTP 服务器 | 托管前端 SPA、图片、下载站点 |
| 反向代理 | 转发请求到后端 Tomcat / Node.js / Python |
| 负载均衡 | 多实例分流（轮询 / 哈希 / 最少连接） |
| API 网关 | 路径路由、协议转换、限流 |
| HTTPS 终端 | TLS 卸载、HTTP/2、HTTP/3 |
| 缓存服务 | 代理缓存后端响应 |
| 流媒体 | HLS / MP4 / FLV 推拉流 |

### Nginx vs Apache

| 维度 | Nginx | Apache |
|------|-------|--------|
| 并发模型 | 事件驱动（epoll/kqueue），单进程多连接 | 进程/线程池，一个连接一个线程 |
| 内存占用 | 低（万级连接仅需数 MB） | 高 |
| 静态性能 | 极强 | 良好 |
| 动态处理 | 反向代理到后端 | 原生支持 mod_php 等 |
| 配置风格 | 嵌套块 `{}` + 指令 | `.htaccess` 分布式 |
| 模块加载 | 编译期静态加载（1.9.11+ 支持动态模块） | 运行时动态加载 |

## 架构原理

### 进程模型

Nginx 采用 **Master-Worker** 多进程架构：

```
                ┌──────────────────────┐
                │      Master          │  管理进程：读配置、绑定端口、派生 worker
                │  (root, 1 个)        │
                └──────────┬───────────┘
                           │ fork
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Worker 1   │     │  Worker 2   │     │  Worker N   │  工作进程：处理实际请求
│ (nginx 用户)│     │ (nginx 用户)│     │ (nginx 用户)│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
   epoll 事件循环      epoll 事件循环      epoll 事件循环
   （单进程支撑数千~数万并发连接）
```

- **Master 进程**：以 root 启动，负责读取配置、绑定 80/443 等特权端口、管理 worker 进程（创建、退出、reload）。
- **Worker 进程**：以非特权用户（如 `nginx` / `www-data`）运行，处理实际的 HTTP 请求。worker 数通常设置为 CPU 核心数。
- **Cache 相关进程**：`cache manager` 定期清理过期缓存，`cache loader` 启动时加载缓存元数据。

### 事件驱动

每个 worker 是一个单线程的事件循环，基于 epoll（Linux）/ kqueue（BSD）/ select（兜底）：

- 一个 worker 可以同时管理数万个连接（`worker_connections`）。
- 采用非阻塞 I/O，请求处理过程中 worker 不会因等待后端而阻塞。
- 这使得 Nginx 在 C10K 甚至 C100K 场景下仍能保持低内存、低 CPU。

### 请求处理流程

```
Client ──HTTP──▶ Worker(epoll)
                    │
                    ├─ 1. 解析请求行/Header
                    ├─ 2. 匹配 server_name → server 块
                    ├─ 3. 匹配 URI → location 块
                    ├─ 4. 执行 rewrite / return 等阶段
                    ├─ 5. 静态文件? → 直接读磁盘返回
                    │      反向代理? → proxy_pass 到后端
                    │      FastCGI? → fastcgi_pass 到 PHP-FPM
                    ├─ 6. 过滤阶段（gzip / sub / header 修改）
                    └─ 7. 返回响应给 Client
```

## 安装

### macOS（Homebrew）

```bash
# 安装
brew install nginx

# 启动（前台）
nginx
# 或作为服务
brew services start nginx

# 默认监听 8080，根目录 /opt/homebrew/var/www（Apple Silicon）
# 配置文件 /opt/homebrew/etc/nginx/nginx.conf
```

### Ubuntu / Debian

```bash
# 官方源（推荐，版本最新）
sudo apt install -y curl gnupg2 ca-certificates lsb-release ubuntu-keyring
curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor \
  | sudo tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
  http://nginx.org/packages/ubuntu $(lsb_release -cs) nginx" \
  | sudo tee /etc/apt/sources.list.d/nginx.list

sudo apt update && sudo apt install -y nginx
sudo systemctl enable --now nginx
```

### CentOS / RHEL

```bash
sudo yum install -y yum-utils
sudo tee /etc/yum.repos.d/nginx.repo >/dev/null <<'EOF'
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
EOF

sudo yum install -y nginx
sudo systemctl enable --now nginx
```

### 源码编译（启用自定义模块）

```bash
# 安装编译依赖
sudo apt install -y build-essential libpcre3-dev zlib1g-dev libssl-dev

# 下载并解压
wget https://nginx.org/download/nginx-1.24.0.tar.gz
tar -xzf nginx-1.24.0.tar.gz && cd nginx-1.24.0

# 配置编译参数（按需启用模块）
./configure \
  --prefix=/usr/local/nginx \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_realip_module \
  --with-http_gzip_static_module \
  --with-stream \
  --with-threads

make -j$(nproc) && sudo make install
```

### Docker

```bash
# 直接运行静态站点
docker run -d --name nginx \
  -p 80:80 -p 443:443 \
  -v $(pwd)/html:/usr/share/nginx/html:ro \
  -v $(pwd)/conf:/etc/nginx/conf.d:ro \
  nginx:stable
```

## 目录结构

以 Ubuntu/Debian 官方包为例：

| 路径 | 说明 |
|------|------|
| `/etc/nginx/nginx.conf` | 主配置文件 |
| `/etc/nginx/conf.d/*.conf` | 站点配置片段（自动 include） |
| `/etc/nginx/sites-available/` | 可用站点（Debian 系约定） |
| `/etc/nginx/sites-enabled/` | 已启用站点（软链到 available） |
| `/etc/nginx/snippets/` | 可复用配置片段（如 SSL 参数） |
| `/etc/nginx/mime.types` | MIME 类型映射 |
| `/etc/logrotate.d/nginx` | 日志轮转配置 |
| `/var/log/nginx/access.log` | 访问日志 |
| `/var/log/nginx/error.log` | 错误日志 |
| `/usr/share/nginx/html/` | 默认站点根目录 |
| `/var/run/nginx.pid` | PID 文件 |
| `/usr/sbin/nginx` | 可执行文件 |

> macOS Homebrew 安装路径：`/opt/homebrew/etc/nginx/`（Apple Silicon）或 `/usr/local/etc/nginx/`（Intel）。

## 常用命令

```bash
# 测试配置语法（修改后必须先执行）
nginx -t

# 启动
nginx

# 停止（优雅：处理完当前请求再退出）
nginx -s quit
# 强制停止
nginx -s stop
# 或
kill -TERM $(cat /var/run/nginx.pid)

# 平滑重载配置（不中断服务）
nginx -s reload

# 重新打开日志文件（日志切割时用）
nginx -s reopen

# 查看版本及编译参数
nginx -V
# 查看版本
nginx -v

# 指定配置文件启动
nginx -c /path/to/nginx.conf

# 指定 prefix
nginx -p /usr/local/nginx
```

### systemd 服务管理（Linux）

```bash
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx    # 重启（短暂中断）
sudo systemctl reload nginx     # 平滑重载（推荐）
sudo systemctl status nginx
sudo systemctl enable nginx     # 开机自启
```

## 配置文件结构

Nginx 配置采用嵌套块结构，从外到内分为：

```
main         全局配置（worker_processes、error_log、pid 等）
└── events   事件模型配置（worker_connections、use）
└── http     HTTP 服务配置（可包含多个 server）
    └── server       虚拟主机（监听端口 + 域名）
        └── location     URL 路径匹配规则
    └── upstream        负载均衡后端组
└── stream  TCP/UDP 代理配置（与 http 平级）
```

### 完整最小配置示例

```nginx
# /etc/nginx/nginx.conf
user  nginx;
worker_processes  auto;
error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;

events {
    worker_connections  1024;
    use epoll;          # Linux 推荐
    multi_accept on;    # 一次接受多个连接
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout  65;
    client_max_body_size  10m;

    gzip  on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript;

    include /etc/nginx/conf.d/*.conf;
}
```

### main 块指令

| 指令 | 说明 | 示例 |
|------|------|------|
| `user` | worker 进程运行用户 | `user nginx;` |
| `worker_processes` | worker 进程数，`auto` 自动按 CPU 核心数 | `worker_processes auto;` |
| `worker_cpu_affinity` | 绑定 worker 到 CPU 核心 | `worker_cpu_affinity auto;` |
| `worker_rlimit_nofile` | worker 最大文件描述符数 | `worker_rlimit_nofile 65535;` |
| `error_log` | 错误日志路径及级别 | `error_log /var/log/nginx/error.log warn;` |
| `pid` | PID 文件路径 | `pid /var/run/nginx.pid;` |
| `daemon` | 是否后台运行（调试用 `off`） | `daemon on;` |

### events 块指令

| 指令 | 说明 |
|------|------|
| `worker_connections` | 每个 worker 最大连接数（含客户端 + 后端），建议 ≥ 65535 |
| `use` | 事件模型：`epoll`（Linux）/ `kqueue`（BSD） |
| `multi_accept` | `on` 时 worker 一次接受所有新连接 |
| `accept_mutex` | `on` 时 worker 轮流接受连接，避免惊群 |

> **最大连接数公式**：`max_clients = worker_processes × worker_connections`。反向代理场景下，每个客户端连接会占用 2 个连接（client↔nginx + nginx↔backend），实际容量需除以 2。

## http 块

http 块定义 HTTP 协议相关全局配置，可包含多个 server 块（虚拟主机）。

### 常用指令

```nginx
http {
    # MIME 映射
    include       mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for" '
                      'rt=$request_time uct="$upstream_connect_time" '
                      'urt="$upstream_response_time"';

    access_log  /var/log/nginx/access.log  main;

    # 文件传输优化
    sendfile        on;        # 内核零拷贝
    tcp_nopush      on;        # 配合 sendfile，合并响应头和体
    tcp_nodelay     on;        # 禁用 Nagle，小包立即发送
    keepalive_timeout  65;     # 客户端 keep-alive 超时
    keepalive_requests 1000;   # 单个 keep-alive 连接最大请求数

    # 客户端请求限制
    client_max_body_size    10m;   # 请求体最大大小（上传文件场景需调大）
    client_body_buffer_size 128k;
    client_header_timeout   60s;
    client_body_timeout     60s;
    send_timeout            60s;

    # 服务器响应缓冲
    proxy_buffer_size       4k;
    proxy_buffers           8 4k;

    # Gzip 压缩
    gzip  on;
    gzip_min_length  1k;
    gzip_comp_level  6;
    gzip_types  text/plain text/css application/json
                application/javascript text/xml application/xml
                application/xml+rss text/javascript
                image/svg+xml;
    gzip_vary on;

    # 文件缓存（open_file_cache）
    open_file_cache max=10000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    include /etc/nginx/conf.d/*.conf;
}
```

### 常用变量

| 变量 | 说明 |
|------|------|
| `$remote_addr` | 客户端 IP（经过代理时是上一跳 IP） |
| `$http_x_forwarded_for` | X-Forwarded-For 链 |
| `$remote_user` | HTTP Basic 认证用户名 |
| `$time_local` | 本地时间 |
| `$request` | 完整请求行 |
| `$status` | 响应状态码 |
| `$body_bytes_sent` | 响应体字节数（不含 Header） |
| `$request_time` | 请求总处理时间 |
| `$upstream_response_time` | 后端响应时间 |
| `$host` | 请求 Host 头或 server_name |
| `$uri` | 规范化后的 URI（不含参数） |
| `$args` / `$query_string` | 查询字符串 |
| `$request_uri` | 原始 URI（含参数） |
| `$scheme` | http 或 https |
| `$server_name` | 当前 server 的 server_name |

## server 块（虚拟主机）

每个 server 块定义一个虚拟主机，通过 `listen` + `server_name` 区分。

### 基于域名的虚拟主机

```nginx
server {
    listen       80;
    server_name  www.example.com example.com;
    root         /var/www/example;
    index        index.html index.htm;

    location / {
        try_files $uri $uri/ =404;
    }

    error_page  404              /404.html;
    error_page  500 502 503 504  /50x.html;
}
```

### server_name 匹配规则

Nginx 按以下优先级匹配 server_name：

| 优先级 | 形式 | 示例 |
|--------|------|------|
| 1 | 精确匹配 | `server_name example.com;` |
| 2 | 通配符开头（最长） | `server_name *.example.com;` |
| 3 | 通配符结尾（最长） | `server_name www.*;` |
| 4 | 正则匹配（按出现顺序） | `server_name ~^www\d+\.example\.com$;` |
| 5 | 默认服务器 | `default_server` 或第一个 server |

```nginx
server {
    listen 80 default_server;   # 未匹配到任何 server_name 时走这里
    server_name _;              # "_" 是无效域名，常配合 default_server
    return 444;                 # 直接关闭连接
}
```

### 基于 IP 的虚拟主机

```nginx
server {
    listen 192.168.1.10:80;
    server_name example.com;
    # ...
}
server {
    listen 192.168.1.11:80;
    server_name example.com;
    # ...
}
```

### listen 指令详解

```nginx
listen 80;                              # 监听所有 IP 的 80 端口
listen 127.0.0.1:8080;                  # 仅监听本机
listen 443 ssl;                         # HTTPS
listen 443 ssl http2;                   # HTTPS + HTTP/2（1.25.1 前写法）
listen 443 ssl;
http2 on;                               # 1.25.1+ 全局开启 HTTP/2
listen [::]:80 ipv6only=on;             # 仅 IPv6
listen 80 default_server;               # 默认虚拟主机
listen 80 reuseport;                    # 启用 SO_REUSEPORT（每 worker 独立 socket）
listen 80 backlog=1024;                 # 连接队列长度
```

## location 块

location 用于根据 URI 匹配规则，将请求路由到不同处理逻辑。

### 匹配修饰符

| 修饰符 | 匹配方式 | 优先级 | 示例 |
|--------|----------|--------|------|
| `=` | 精确匹配（路径完全相等） | 最高 | `location = /favicon.ico` |
| `^~` | 前缀匹配（不再进行正则） | 次高 | `location ^~ /static/` |
| `~` | 区分大小写的正则 | 按出现顺序 | `location ~ \.php$` |
| `~*` | 不区分大小写的正则 | 按出现顺序 | `location ~* \.(jpg\|png)$` |
| `!~` / `!~*` | 正则取反 | 按出现顺序 | `location !~ \.test$` |
| `/xxx` | 普通前缀匹配 | 最低 | `location /api/` |
| `@` | 命名 location（内部跳转） | 仅内部 | `location @fallback` |

### 匹配流程

```
1. 查找 = 精确匹配，命中则直接使用，停止后续匹配
2. 查找 ^~ 前缀匹配，命中则使用，不再进行正则匹配
3. 按配置文件顺序查找 ~ 和 ~* 正则匹配，命中第一个即停止
4. 若正则未命中，使用最长前缀匹配的普通 location
```

### 示例

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/example;

    # 精确匹配首页（性能优化）
    location = / {
        index index.html;
    }

    # 静态资源走前缀匹配，跳过正则
    location ^~ /static/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 图片走正则（不区分大小写）
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2?)$ {
        expires 7d;
        access_log off;
    }

    # PHP 请求转发到 PHP-FPM
    location ~ \.php$ {
        fastcgi_pass   127.0.0.1:9000;
        fastcgi_index  index.php;
        fastcgi_param  SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include        fastcgi_params;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
    }

    # 兜底
    location / {
        try_files $uri $uri/ /index.html?$args;
    }

    # 命名 location（内部跳转）
    location @fallback {
        proxy_pass http://backup_backend;
    }
}
```

### root vs alias

| 指令 | 行为 | 示例请求 | 实际路径 |
|------|------|----------|----------|
| `root` | 把 location 路径**追加**到 root 后 | `location /i/ { root /data; }` 请求 `/i/a.png` | `/data/i/a.png` |
| `alias` | 把 location 路径**替换**为 alias | `location /i/ { alias /data/; }` 请求 `/i/a.png` | `/data/a.png` |

> **注意**：`alias` 末尾的 `/` 很关键，路径拼接错误是常见坑。

### try_files

按顺序尝试文件 / 路径，全部失败时使用最后一项（可以是命名 location、URI 或状态码）。

```nginx
# SPA 单页应用：所有未匹配的路径回退到 index.html
location / {
    try_files $uri $uri/ /index.html;
}

# 静态文件不存在则返回 404
location /files/ {
    try_files $uri =404;
}

# 失败时跳转到命名 location
location / {
    try_files $uri $uri/ @proxy;
}
location @proxy {
    proxy_pass http://backend;
}
```

## 反向代理

反向代理是 Nginx 最核心的用途之一，将客户端请求转发到后端服务。

### 基础反向代理

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;

        # 传递客户端真实信息
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 5s;
        proxy_send_timeout    60s;
        proxy_read_timeout    60s;

        # 缓冲设置
        proxy_buffering       on;
        proxy_buffer_size     4k;
        proxy_buffers         8 4k;
        proxy_busy_buffers_size 8k;
    }
}
```

### proxy_pass 路径规则

```nginx
# 情况 1：proxy_pass 不带 URI，原样转发
location /api/ {
    proxy_pass http://backend;
    # 请求 /api/users → http://backend/api/users
}

# 情况 2：proxy_pass 带 URI，替换 location 前缀
location /api/ {
    proxy_pass http://backend/;
    # 请求 /api/users → http://backend/users
}

# 情况 3：带路径前缀
location /api/ {
    proxy_pass http://backend/v1/;
    # 请求 /api/users → http://backend/v1/users
}

# 情况 4：使用正则 location，proxy_pass 不能带 URI
location ~ ^/api/(.*)$ {
    proxy_pass http://backend/$1;   # 手动拼装
}
```

### 代理 WebSocket

```nginx
# HTTP Upgrade 头处理
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name ws.example.com;

    location /ws {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        # WebSocket 长连接，超时调大
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

### 代理缓存

```nginx
http {
    # 定义缓存区
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m
                     max_size=1g inactive=60m use_temp_path=off;

    server {
        location /api/ {
            proxy_pass http://backend;
            proxy_cache api_cache;
            proxy_cache_key "$scheme$request_method$host$request_uri";
            proxy_cache_valid 200    10m;
            proxy_cache_valid 404    1m;
            proxy_cache_valid any     1m;

            # 响应头加缓存命中状态（调试用）
            add_header X-Cache-Status $upstream_cache_status;

            # 后端显式控制是否跳过缓存
            proxy_cache_bypass $http_cache_control $http_authorization;
            proxy_no_cache     $http_cache_control $http_authorization;

            # 上游错误时的备援：使用旧缓存
            proxy_cache_use_stale error timeout http_500 http_502 http_503 http_504;
        }
    }
}
```

`$upstream_cache_status` 取值：

| 值 | 含义 |
|----|------|
| `MISS` | 未命中，请求转发到后端 |
| `BYPASS` | 命中 bypass 规则，跳过缓存 |
| `EXPIRED` | 缓存已过期，重新请求后端 |
| `STALE` | 后端错误，返回旧缓存 |
| `UPDATING` | 正在异步更新 |
| `REVALIDATED` | 启用 proxy_cache_revalidate 后验证通过 |
| `HIT` | 命中缓存 |

## 负载均衡

通过 `upstream` 定义一组后端服务器，再由 `proxy_pass` 引用。

### 调度算法对比

| 算法 | 指令 | 说明 |
|------|------|------|
| 轮询（默认） | 无 | 按顺序逐一分配，自动跳过 down 的服务器 |
| 加权轮询 | `weight=N` | 按权重比例分配 |
| IP 哈希 | `ip_hash;` | 同一 IP 固定到同一后端（会话保持） |
| 一致性哈希 | `hash $key consistent;` | 基于 key 哈希，加减节点影响小（需第三方模块或 1.7.2+） |
| 最少连接 | `least_conn;` | 转发到当前连接数最少的后端 |
| 随机 | `random;` | 随机选一台；`random two least_conn;` 随机选 2 台取连接最少的 |

### 配置示例

```nginx
http {
    upstream backend {
        # 加权轮询
        server 192.168.1.11:8080 weight=3;
        server 192.168.1.12:8080 weight=1;
        server 192.168.1.13:8080 weight=1;

        # 备用服务器（主服务器全挂才启用）
        server 192.168.1.99:8080 backup;

        # 故障服务器，手动标记下线
        # server 192.168.1.14:8080 down;

        # 健康检查参数
        max_fails=3       fail_timeout=30s;   # 30s 内失败 3 次则认为不可用
        keepalive 32;                          # 到后端保持 32 个长连接
    }

    # 最少连接
    upstream api_backend {
        least_conn;
        server 192.168.1.11:8080;
        server 192.168.1.12:8080;
    }

    # IP 哈希（会话粘性）
    upstream session_backend {
        ip_hash;
        server 192.168.1.11:8080;
        server 192.168.1.12:8080;
    }

    # 一致性哈希（基于 URI）
    upstream hash_backend {
        hash $request_uri consistent;
        server 192.168.1.11:8080;
        server 192.168.1.12:8080;
    }

    server {
        listen 80;
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # 长连接到后端（配合 upstream 的 keepalive）
            proxy_http_version 1.1;
            proxy_set_header Connection "";

            # 失败重试：把请求转给下一台
            proxy_next_upstream error timeout http_502 http_503 http_504;
            proxy_next_upstream_tries 3;
            proxy_next_upstream_timeout 10s;
        }
    }
}
```

### server 指令参数

| 参数 | 说明 |
|------|------|
| `weight=N` | 权重，默认 1 |
| `max_fails=N` | 失败次数阈值（默认 1） |
| `fail_timeout=T` | 失败统计窗口时长（默认 10s），同时该服务器在该时长内被视为不可用 |
| `backup` | 备用服务器，仅在主服务器不可用时启用 |
| `down` | 手动标记下线 |
| `max_conns=N` | 限制到该后端的最大并发连接数 |
| `resolve` | 域名后端动态解析（需在 commercial 版本或 1.27.3+ OSS） |
| `slow_start=T` | 服务恢复时缓慢提升权重（仅商业版） |

### 主动健康检查（开源版）

开源 Nginx 仅支持被动检查（请求失败才标记 down）。主动检查可用：

- **nginx_upstream_check_module**（第三方模块，需编译）
- **商业版 Nginx Plus** 内置 `health_check` 指令

被动检查示例已足够覆盖大多数场景：

```nginx
upstream backend {
    server 192.168.1.11:8080 max_fails=3 fail_timeout=30s;
    server 192.168.1.12:8080 max_fails=3 fail_timeout=30s;
}
```

## HTTPS / SSL

### 单域名 HTTPS

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name www.example.com;

    ssl_certificate     /etc/nginx/ssl/www.example.com.pem;   # 含证书链
    ssl_certificate_key /etc/nginx/ssl/www.example.com.key;

    # 推荐参数（兼容性 + 安全性）
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;     # TLS 1.3 由客户端选 cipher
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # HSTS：强制浏览器后续都走 HTTPS（谨慎使用）
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### HTTP 跳转 HTTPS

```nginx
server {
    listen 80;
    server_name www.example.com;
    return 301 https://$host$request_uri;
}
```

### Let's Encrypt 自动签发（Certbot）

```bash
# 安装 certbot + nginx 插件
sudo apt install -y certbot python3-certbot-nginx

# 自动修改 nginx 配置并申请证书
sudo certbot --nginx -d www.example.com -d example.com

# 自动续期（已写入 systemd timer）
sudo certbot renew --dry-run
```

### 多证书 SNI

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name a.example.com;
    ssl_certificate     /etc/nginx/ssl/a.pem;
    ssl_certificate_key /etc/nginx/ssl/a.key;
}
server {
    listen 443 ssl;
    http2 on;
    server_name b.example.com;
    ssl_certificate     /etc/nginx/ssl/b.pem;
    ssl_certificate_key /etc/nginx/ssl/b.key;
}
```

Nginx 基于 SNI（Server Name Indication）选择对应证书，一个 IP 可承载多个 HTTPS 站点。

### HTTP/2 与 HTTP/3

```nginx
# HTTP/2（1.25.1+ 推荐写法）
server {
    listen 443 ssl;
    http2 on;
    # ...
}

# HTTP/3 / QUIC（需 1.25.0+ 编译时启用 --with-http_v3_module）
server {
    listen 443 ssl;
    listen 443 quic reuseport;
    http2 on;
    http3 on;
    add_header Alt-Svc 'h3=":443"; ma=86400';
    # ...
}
```

## 静态文件服务

### 基础配置

```nginx
server {
    listen 80;
    server_name static.example.com;
    root /var/www/static;

    location / {
        autoindex on;             # 目录列表（仅内部使用）
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # 禁止访问隐藏文件（如 .git）
    location ~ /\. {
        deny all;
    }
}
```

### 大文件下载优化

```nginx
location /download/ {
    root /data/files;

    # 直接 sendfile 高效传输
    sendfile           on;
    tcp_nopush         on;
    aio                on;          # 异步 I/O
    directio           8m;          # 大于 8MB 走 directio 绕过 page cache
    output_buffers     2 1m;
    limit_rate         1m;          # 单连接限速 1MB/s
    limit_rate_after   10m;         # 前 10MB 不限速
}
```

### 浏览器缓存控制

```nginx
# 通过 expires 指令
location ~* \.(jpg|jpeg|png|gif|ico|woff2?)$ {
    expires 30d;
    add_header Cache-Control "public";
    access_log off;
}

location ~* \.(css|js)$ {
    expires 7d;
    add_header Cache-Control "public, must-revalidate";
}

# HTML 不缓存
location ~ \.html$ {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    expires off;
}
```

### SPA 单页应用

```nginx
server {
    listen 80;
    server_name app.example.com;
    root /var/www/vue-app;
    index index.html;

    location / {
        # history 模式路由回退到 index.html
        try_files $uri $uri/ /index.html;
    }

    # 静态资源带 hash 长缓存
    location ~* \.(js|css|png|jpg|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # index.html 强制不缓存
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
```

## URL 重写与跳转

### rewrite 指令

```nginx
# 语法：rewrite regex replacement [flag];
# flag：
#   last      - 重写后重新匹配 location（默认）
#   break     - 重写后不再匹配后续 rewrite，继续在当前 location 执行
#   redirect  - 302 临时重定向
#   permanent - 301 永久重定向

server {
    # 旧路径永久跳转
    rewrite ^/old/(.*)$ /new/$1 permanent;

    # 把 /user/123 重写为 /profile?id=123（内部重写）
    rewrite ^/user/(\d+)$ /profile?id=$1 last;

    # http 跳 https
    if ($scheme = http) {
        return 301 https://$host$request_uri;
    }
}
```

### return 指令

比 `rewrite` 更轻量，直接返回状态码或重定向。

```nginx
location = /maintenance {
    return 503;                    # 返回状态码
}

location /old-api {
    return 301 /new-api$request_uri;   # 301 重定向
}

location /forbidden {
    return 403 "Access Denied";     # 返回自定义文本
}
```

### if 指令（谨慎使用）

> Nginx 官方建议：`if` 仅在 `location` 内用于 `return` / `rewrite`，其他用法易出问题（"If Is Evil"）。

```nginx
location / {
    # 仅允许 POST
    if ($request_method != POST) {
        return 405;
    }

    # 阻止特定 User-Agent
    if ($http_user_agent ~* "bot|spider") {
        return 403;
    }
}
```

复杂条件建议用 `map`：

```nginx
# http 块
map $request_method $is_post {
    default 0;
    POST    1;
}

server {
    location /api {
        if ($is_post = 0) { return 405; }
    }
}
```

## 安全加固

### 访问控制

```nginx
# IP 白名单
location /admin {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny  all;
    proxy_pass http://backend;
}

# HTTP Basic 认证
location /private {
    auth_basic           "Restricted Area";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://backend;
}
```

生成密码文件：

```bash
# 安装工具
sudo apt install -y apache2-utils

# 添加用户（首次用 -c 创建文件）
sudo htpasswd -c /etc/nginx/.htpasswd user1
sudo htpasswd /etc/nginx/.htpasswd user2
```

### 限流

```nginx
http {
    # 按 IP 限速：每 IP 每秒 10 个请求
    limit_req_zone $binary_remote_addr zone=req_limit:10m rate=10r/s;

    # 按连接数限流：每 IP 最多 20 个并发连接
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    server {
        location /api/ {
            # 突发流量：burst=20 排队，nodelay 立即处理不延迟
            limit_req  zone=req_limit burst=20 nodelay;

            # 并发连接限制
            limit_conn zone=conn_limit 20;

            # 超限返回 429（默认 503）
            limit_req_status 429;
            limit_conn_status 429;

            proxy_pass http://backend;
        }
    }
}
```

### 常见安全 Header

```nginx
server {
    # 隐藏版本号
    server_tokens off;

    # 安全响应头
    add_header X-Content-Type-Options    "nosniff" always;
    add_header X-Frame-Options           "SAMEORIGIN" always;
    add_header X-XSS-Protection          "1; mode=block" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy   "default-src 'self'; script-src 'self' 'unsafe-inline'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### 防 DDoS 基础

```nginx
http {
    # 限制请求体大小
    client_max_body_size 1m;
    client_body_buffer_size 16k;

    # 限制请求头大小
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;

    # 慢连接超时
    client_body_timeout     10s;
    client_header_timeout   10s;
    keepalive_timeout      15s;
    send_timeout            10s;

    # 限制连接数（每个 IP）
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    server {
        location / {
            limit_conn addr 50;     # 每 IP 最多 50 个并发连接
        }
    }
}
```

## 性能调优

### 进程与连接

```nginx
worker_processes  auto;             # = CPU 核心数
worker_cpu_affinity auto;           # 自动绑定 CPU
worker_rlimit_nofile 100000;        # 文件描述符上限（需配合 ulimit）

events {
    worker_connections  40000;      # 每 worker 最大连接数
    use epoll;
    multi_accept on;
}
```

系统层面配套调整：

```bash
# 临时提高文件描述符上限
ulimit -n 65535

# 永久生效
sudo tee -a /etc/security/limits.conf <<EOF
*  soft  nofile  65535
*  hard  nofile  65535
EOF

# 内核参数
sudo sysctl -w net.core.somaxconn=65535
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=65535
sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535"
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
```

### HTTP 优化

```nginx
http {
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;

    keepalive_timeout   65;
    keepalive_requests  1000;

    # 长连接复用（到后端）
    upstream backend {
        server 127.0.0.1:8080;
        keepalive 32;
    }

    # 文件缓存
    open_file_cache          max=10000 inactive=20s;
    open_file_cache_valid    30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors   on;

    # Gzip
    gzip              on;
    gzip_min_length   1k;
    gzip_comp_level   5;
    gzip_proxied      any;
    gzip_vary         on;
    gzip_types        text/plain text/css application/json
                      application/javascript text/xml application/xml
                      text/javascript image/svg+xml;
}
```

### 调优检查清单

| 维度 | 检查项 |
|------|--------|
| 进程 | `worker_processes` 是否 = CPU 核数 |
| 连接 | `worker_connections` 与 `worker_rlimit_nofile` 是否足够 |
| 传输 | `sendfile` / `tcp_nopush` / `tcp_nodelay` 是否开启 |
| 缓存 | 静态资源是否启用 `open_file_cache` 与浏览器缓存 |
| 压缩 | gzip 是否开启，`gzip_types` 是否覆盖主要类型 |
| 长连接 | 到后端是否启用 `keepalive`，`proxy_http_version 1.1` |
| 超时 | `keepalive_timeout` / `client_*_timeout` 是否合理 |
| 系统 | `ulimit -n`、`somaxconn`、`tcp_tw_reuse` 是否调整 |

## 日志

### 自定义日志格式

```nginx
http {
    # JSON 格式日志（方便 ELK / Loki 采集）
    log_format json escape=json '{'
        '"time":"$time_iso8601",'
        '"remote_addr":"$remote_addr",'
        '"x_forwarded_for":"$http_x_forwarded_for",'
        '"request":"$request",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"upstream_response_time":"$upstream_response_time",'
        '"http_referer":"$http_referer",'
        '"http_user_agent":"$http_user_agent"'
    '}';

    access_log /var/log/nginx/access.log json;
    error_log  /var/log/nginx/error.log warn;
}
```

### 日志按天切割（logrotate）

`/etc/logrotate.d/nginx`：

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 nginx adm
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 $(cat /var/run/nginx.pid)
        fi
    endscript
}
```

`kill -USR1` 通知 Nginx 重新打开日志文件，无需重启。

### 关闭指定 location 的日志

```nginx
location ~* \.(jpg|png|gif|css|js|woff2?)$ {
    access_log off;
}
```

## 常用场景配置

### PHP-FPM

```nginx
server {
    listen 80;
    server_name php.example.com;
    root /var/www/php;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass   unix:/run/php/php8.2-fpm.sock;
        fastcgi_index  index.php;
        fastcgi_param  SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include        fastcgi_params;
        fastcgi_buffers 16 16k;
        fastcgi_buffer_size 32k;
    }

    location ~ /\.ht {
        deny all;
    }
}
```

### Node.js 反向代理

```nginx
upstream node_backend {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80;
    server_name node.example.com;

    location / {
        proxy_pass http://node_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /socket.io/ {
        proxy_pass http://node_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

### Python (uWSGI / Gunicorn)

```nginx
# uWSGI
location / {
    include       uwsgi_params;
    uwsgi_pass    127.0.0.1:3031;
}

# Gunicorn
location / {
    proxy_pass    http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Java (Spring Boot)

```nginx
upstream spring_backend {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name api.example.com;
    client_max_body_size 50m;

    location /api/ {
        proxy_pass http://spring_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Spring Boot Actuator 长连接超时
        proxy_read_timeout 60s;
    }
}
```

### 前后端分离（同域路由）

```nginx
server {
    listen 80;
    server_name app.example.com;
    root /var/www/frontend;

    # 前端 SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态资源（独立子域或同域）
    location /static/ {
        alias /var/www/frontend/assets/;
        expires 30d;
        access_log off;
    }
}
```

### TCP / UDP 代理（stream 模块）

```nginx
# 注意：stream 块与 http 块平级，写在 nginx.conf 顶层
stream {
    upstream mysql_backend {
        server 192.168.1.11:3306;
        server 192.168.1.12:3306;
    }

    server {
        listen 3306;
        proxy_pass mysql_backend;
        proxy_connect_timeout 5s;
        proxy_timeout 300s;
    }

    # UDP（如 DNS）
    server {
        listen 53 udp;
        proxy_pass 192.168.1.11:53;
    }
}
```

### 灰度发布（按 Cookie / Header 分流）

```nginx
# 按 Header 路由到不同版本
map $http_x_version $upstream_pool {
    default  stable_backend;
    "v2"     canary_backend;
}

server {
    location / {
        proxy_pass http://$upstream_pool;
    }
}
```

## 故障排查

### 常见错误

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)` | 80 端口被占用 | `lsof -i:80` 找出进程并停止，或改 `listen` 端口 |
| `nginx: [emerg] host not found in upstream "xxx"` | upstream 域名解析失败 | 检查 DNS / `resolver` 指令 |
| `nginx: [emerg] "proxy_pass" cannot have URI part in location given by regular expression` | 正则 location 中 proxy_pass 带 URI | 改用 `proxy_pass http://backend/$1;` 拼装 |
| `413 Request Entity Too Large` | 上传文件超过 `client_max_body_size` | 调大该值，如 `client_max_body_size 100m;` |
| `502 Bad Gateway` | 后端服务未启动 / 崩溃 | 检查后端进程、监听端口、防火墙 |
| `504 Gateway Timeout` | 后端响应超时 | 调大 `proxy_read_timeout`，或排查后端慢查询 |
| `400 Request Header Or Cookie Too Large` | Header/Cookie 超过缓冲区 | 调大 `large_client_header_buffers` |
| `Permission denied` 访问静态文件 403 | worker 用户无读取权限 | `chmod`/`chown` 或调整 `user` 指令 |
| `too many open files` | 文件描述符耗尽 | 调大 `worker_rlimit_nofile` 与 `ulimit -n` |

### 调试技巧

```bash
# 1. 检查配置语法
nginx -t

# 2. 查看完整编译配置
nginx -V 2>&1

# 3. 查看进程
ps -ef | grep nginx

# 4. 实时查看日志
tail -f /var/log/nginx/access.log /var/log/nginx/error.log

# 5. 测试某个 URL 命中的 location
# 在 location 中加 add_header 调试
location ~ \.php$ {
    add_header X-Debug-Location "php matched" always;
    # ...
}

# 6. 检查端口监听
ss -tlnp | grep nginx

# 7. 模拟请求，查看响应头
curl -vI http://localhost/
```

### 502 / 504 排查思路

```
502 Bad Gateway
├── 后端进程未启动 ── systemctl status <backend>
├── 后端监听端口 / socket 不匹配 ── ss -tlnp
├── SELinux 拦截 ── sudo setenforce 0 测试 / audit2allow
├── 防火墙拦截 ── iptables -L / firewall-cmd
└── 后端崩了 ── 查后端日志

504 Gateway Timeout
├── 后端处理慢 ── 查后端日志 / APM
├── proxy_read_timeout 太小 ── 调大到 60s/120s
├── 网络丢包 ── ping / mtr 后端
└── 后端死锁 ── jstack / py-spy 抓栈
```

## 配置片段复用

把通用配置抽成 snippet，在多个站点 include。

```nginx
# /etc/nginx/snippets/proxy_common.conf
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 5s;
proxy_read_timeout    60s;
proxy_send_timeout    60s;

# /etc/nginx/snippets/ssl_common.conf
ssl_protocols              TLSv1.2 TLSv1.3;
ssl_ciphers                ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers  off;
ssl_session_cache          shared:SSL:10m;
ssl_session_timeout        1d;
ssl_stapling               on;
ssl_stapling_verify        on;

# 站点配置
server {
    listen 443 ssl;
    http2 on;
    server_name api.example.com;
    ssl_certificate     /etc/nginx/ssl/api.pem;
    ssl_certificate_key /etc/nginx/ssl/api.key;
    include snippets/ssl_common.conf;

    location / {
        proxy_pass http://backend;
        include snippets/proxy_common.conf;
    }
}
```

## 参考资源

- 官方文档：<https://nginx.org/en/docs/>
- 完整指令索引：<https://nginx.org/en/docs/dirindex.html>
- 变量参考：<https://nginx.org/en/docs/varindex.html>
- 配置生成器：<https://www.digitalocean.com/community/tools/nginx>
- Nginx 官方博客：<https://www.nginx.com/blog/>
- 相关笔记：[[docker|Docker 部署 Nginx]]、[[http-protocol|HTTP 协议]]、[[linux|Linux 命令]]
