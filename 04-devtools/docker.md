---
title: Docker 实战笔记
description: Docker 核心概念、Dockerfile 指令与 CLI 命令行详解
tags:
  - docker
  - devops
  - container
date: 2026-09-09
reference: https://docs.docker.com/reference/cli/docker/
---

# Docker 实战笔记

- [Docker 常用命令与 `Dockerfile`](https://xiets.blog.csdn.net/article/details/122866186)
- [Docker 环境清理的常用方法](https://www.zhihu.com/tardis/bd/ans/2998335721)
- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Dockerfile 官方文档](https://docs.docker.com/engine/reference/builder/)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker 从入门到实践](https://vuepress.mirror.docker-practice.com/)

## 目录

1. [核心概念](#1-核心概念)
2. [Dockerfile 指令详解](#2-dockerfile-指令详解)
3. [CLI 命令行详解](#3-cli-命令行详解)
4. [Docker Compose](#4-docker-compose)
5. [镜像加速与 Registry](#5-镜像加速与-registry)
6. [常用技巧](#6-常用技巧)

---

## 0. 两个核心维度：Dockerfile vs CLI

学习 Docker 首先需要分清两个维度，它们解决的是**不同阶段**的问题：

| 维度 | Dockerfile 指令 | CLI 命令行 |
|------|----------------|-----------|
| **是什么** | 写在 `Dockerfile` 文件里的**构建指令** | 在终端里输入的**操作命令** |
| **作用阶段** | `docker build` 构建镜像时执行 | 构建、运行、管理镜像/容器时执行 |
| **产物** | 生成**镜像**（Image） | 基于镜像运行**容器**（Container） |
| **执行时机** | 构建期（build time） | 运行期（runtime）为主 |
| **典型例子** | `FROM` `RUN` `COPY` `CMD` `ENTRYPOINT` | `docker build` `docker run` `docker ps` `docker exec` |
| **类比** | 一份「配方/蓝图」，描述镜像怎么造 | 一套「操作手册」，描述怎么使用和管理 |

> **一句话记忆**：`Dockerfile` 定义「**这个镜像长什么样**」，CLI 命令负责「**怎么用它、怎么管它**」。

下面按这条主线组织全文：先讲概念，再讲 Dockerfile（构建），再讲 CLI（运行与管理）。

---

## 1. 核心概念

### 1.1 架构

```
Dockerfile ──(docker build)──> Image ──(docker run)──> Container
    │                            │                        │
  构建蓝图                     只读模板                  可运行实例
    │                            │                        │
                                └──(docker push/pull)──> Registry(仓库 hub)
```

三个核心对象：

- **镜像（Image）**：只读的静态模板，包含运行一个应用所需的文件系统、依赖和启动配置。
- **容器（Container）**：镜像的运行实例，在镜像之上叠加一层可写层 + 进程隔离。
- **仓库（Registry / Repository）**：存放和分发镜像的地方，如 Docker Hub、腾讯云镜像仓库、私有 harbor。

### 1.2 Docker 整体架构

Docker 采用经典的 **Client/Server（C/S）** 架构：

```
docker CLI (客户端)
    │  REST API (unix socket / TCP)
    ▼
Docker Daemon (dockerd 守护进程)
    ├── containerd  容器运行时管理层
    └── runc        真正创建/运行容器的 OCI 运行时
```

- `docker` 命令本身只是个客户端，所有请求最终发给 `dockerd` 守护进程处理。
- 守护进程通过 `containerd` + `runc` 管理容器的完整生命周期。
- 这也解释了为什么 Linux 上普通用户需要加入 `docker` 组才能操作 Docker（本质是访问 `/var/run/docker.sock`）。

### 1.3 分层存储（UnionFS / OverlayFS）

Docker 镜像体积小、复用高的核心秘密是**分层存储**：

- 镜像由一系列**只读层（Layer）**堆叠而成，每一条 `RUN` / `COPY` 指令通常产生一个新层。
- 多个镜像可以共享相同的底层（如都基于 `ubuntu:22.04` 时，只存一份基础层）。
- 容器启动时，在镜像只读层之上叠加一层**可写容器层（Container Layer）**，所有写操作都发生在这一层。

```
┌─────────────────────────┐
│  Container Layer (可写) │  ← 容器运行时产生，容器删除即消失
├─────────────────────────┤
│  Layer 3: COPY app/     │
├─────────────────────────┤
│  Layer 2: RUN pip inst… │  ← 只读镜像层
├─────────────────────────┤
│  Layer 1: FROM ubuntu   │
└─────────────────────────┘
```

关键技术点：

1. **Copy-on-Write（写时复制）**：容器要修改镜像层里的文件时，不会直接改只读层，而是把文件复制到可写层再改。
2. **删除 = 打标记（whiteout）**：容器删除镜像层的文件时，只是在可写层放一个"白out"标记文件，底层文件并未真的删除。
3. **层不可变**：镜像层一旦构建完成就不可修改，任何改动都是新增一层，这也是 `RUN` 里 `rm -rf` 无法减小镜像体积的原因。

> 存储驱动实现上 Linux 默认用 `overlay2`，早期有 `aufs`、`devicemapper` 等。可用 `docker info | grep Storage` 查看当前驱动。

### 1.4 容器隔离：Namespace 与 Cgroup

容器本质是宿主机上的一个**受限进程**，通过 Linux 内核两大机制实现隔离与限制：

| 机制 | 作用 | 说明 |
|------|------|------|
| **Namespace（命名空间）** | 隔离 | 隔离 PID、网络、挂载、用户、IPC、UTS 等，让容器"看不见"其他进程 |
| **Cgroup（控制组）** | 限制 | 限制 CPU、内存、磁盘 IO、网络带宽等资源使用量 |

- `docker run --cpus=2 --memory=512m` 背后就是配置 cgroup 限额。
- 容器共享宿主机内核，因此 Linux 容器无法直接运行 Windows 内核（Windows 容器同理），这也是 `--platform` 跨平台构建的由来。

---

## 2. Dockerfile 指令详解

> 本节所有指令都写在 `Dockerfile` 里，由 `docker build` 在**构建期**执行。

### 2.0 指令总览

| 指令 | 作用 | 阶段 |
|------|------|------|
| `FROM` | 指定基础镜像 | 构建 |
| `RUN` | 构建时执行命令 | 构建 |
| `COPY` | 复制宿主机文件到镜像 | 构建 |
| `ADD` | 复制文件（支持 URL/自动解压） | 构建 |
| `WORKDIR` | 设置工作目录 | 构建/运行 |
| `ENV` | 设置环境变量（构建+运行均生效） | 构建/运行 |
| `ARG` | 构建参数（仅构建期） | 构建 |
| `EXPOSE` | 声明容器监听端口 | 声明 |
| `VOLUME` | 声明挂载点/匿名卷 | 声明 |
| `USER` | 指定运行用户 | 构建/运行 |
| `LABEL` | 添加元数据 | 构建 |
| `HEALTHCHECK` | 健康检查 | 运行 |
| `CMD` | 容器默认启动命令 | 运行 |
| `ENTRYPOINT` | 容器入口命令 | 运行 |

### 2.1 FROM —— 基础镜像

```dockerfile
FROM nginx
FROM ubuntu:22.04
FROM python:3.11-slim AS builder

# 指定架构
FROM --platform=linux/amd64 python:3.11
FROM --platform=linux/arm64 python:3.11
```

- 必须是 Dockerfile 的**第一条有效指令**（`ARG` 除外）。
- 建议**显式指定 tag**，避免使用 `latest`（`latest` 会漂移，导致不可复现）。
- `scratch` 是一个特殊的空镜像，用于构建极简镜像或静态编译的二进制。
- 架构选择：`linux/amd64`（x86）、`linux/arm64`（ARM，如 Apple Silicon）。

### 2.2 RUN —— 构建时执行命令

两种格式：

```dockerfile
# shell 格式（默认 /bin/sh -c）
RUN <命令>

# exec 格式（不经过 shell）
RUN ["可执行文件", "参数1", "参数2"]
```

**每条 `RUN` 都会生成一个新镜像层**，因此要合并命令、清理缓存以减小体积：

```dockerfile
# ❌ 错误：三层 + 保留 apt 缓存
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y vim

# ✅ 正确：合并为一条，用 && 连接，安装完清理缓存
RUN apt-get update && apt-get install -y \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*
```

### 2.3 COPY vs ADD —— 复制文件

```dockerfile
COPY [--chown=<user>:<group>] <源路径>... <目标路径>
ADD  [--chown=<user>:<group>] <源路径>... <目标路径>
```

**关键差异**：

| 特性 | COPY | ADD |
|------|------|-----|
| 复制本地文件 | ✅ | ✅ |
| 自动解压 tar 压缩包 | ❌ | ✅（仅本地 tar） |
| 从 URL 下载 | ❌ | ✅ |
| 官方推荐 | ✅ **首选** | ⚠️ 仅在需要解压时使用 |

- **COPY 是官方推荐首选**，语义清晰、行为可预期。
- `ADD` 的 URL 下载不会做校验、版本不可控，官方建议用 `RUN curl` 代替；自动解压也常带来意外行为。
- **重要**：源路径为**文件夹**时，复制的是文件夹里的**内容**，而非文件夹本身：

```dockerfile
# 本地 ./static 目录 → 镜像 /app/static 目录（内容平铺进去）
COPY ./static /app/static
```

- 目标路径不存在时会自动创建。

### 2.4 WORKDIR —— 工作目录

```dockerfile
WORKDIR /app
```

- 等价于 `cd` + 后续指令都在该目录执行。
- 推荐用**绝对路径**，且 **`WORKDIR` 优于 `RUN cd`**（`RUN cd` 每条是独立 shell，切换不持久）。
- 目录不存在会自动创建，多次 `WORKDIR` 是相对上一次叠加的。

```dockerfile
# ✅ 推荐
WORKDIR /app
RUN go build -o myapp

# ❌ 错误：RUN cd 不影响后续层
RUN cd /app
RUN ls   # 这里仍在 / 下
```

### 2.5 ENV vs ARG —— 环境变量与构建参数

| 特性 | ENV | ARG |
|------|-----|-----|
| 定义格式 | `ENV <key>=<value>` | `ARG <name>[=<默认值>]` |
| 生效阶段 | 构建期 + 运行期 | **仅构建期** |
| 能否在容器中读到 | ✅ 可以 | ❌ 不行 |
| 覆盖方式 | 不可在 build 时覆盖 | `docker build --build-arg` |
| 可见性 | `docker history` 可见 | `docker history` 可见 |

```dockerfile
ENV VERSION=1.0 DEBUG=on \
    NAME="Happy Feet"

ARG VERSION=2.0
# 构建时覆盖：docker build --build-arg VERSION=3.0 .
```

- **`ARG` 无法在运行时存在**：构建结束后变量就消失了。
- **安全提示**：`ARG` 和 `ENV` 的值都能通过 `docker history` 看到，**不要用它们存密码/密钥**，敏感信息用 `docker secret` / 构建工具注入。
- 典型用法：`ARG` 声明版本，`ENV` 把需要的值固化进运行时。

### 2.6 EXPOSE —— 声明端口

```dockerfile
EXPOSE 80
EXPOSE 80/tcp
```

- **只是文档性声明**，告诉使用者"这个镜像的进程监听哪个端口"，**本身不会发布端口**。
- 真正对外映射需要在运行时用 `-p`（`docker run -p 8080:80`），或 `-P` 把 EXPOSE 的端口随机映射到宿主机。
- `EXPOSE 80` 与 `EXPOSE 80/tcp` 等价（默认 TCP）。

### 2.7 VOLUME —— 声明挂载点

详见 [3.5 数据卷管理](#35-数据卷管理-volume)。在 Dockerfile 中：

```dockerfile
VOLUME ["/data", "/logs"]
VOLUME /data
```

- 创建**匿名卷**，声明该目录应该被持久化，容器删除后数据不丢。
- **关键陷阱**：`VOLUME` 指令之后对挂载目录的修改**不会生效**：

```dockerfile
# ❌ 错误：数据不会保留
VOLUME /data
RUN echo "test" > /data/test.txt

# ✅ 正确：先写数据，再声明 VOLUME
RUN echo "test" > /data/test.txt
VOLUME /data
```

- 生产环境推荐在**运行时用命名卷覆盖**匿名卷（见 3.5）。

### 2.8 USER —— 运行用户

```dockerfile
USER <user>[:<group>]
USER www-data
USER 1000:1000
```

- 指定后续指令（及运行时）以哪个用户执行，默认 `root`。
- **最佳实践**：生产镜像避免以 `root` 运行，降低安全风险。
- 注意：先创建用户再切换：

```dockerfile
RUN groupadd -r app && useradd -r -g app app
USER app
```

### 2.9 HEALTHCHECK —— 健康检查

```dockerfile
HEALTHCHECK [选项] CMD <命令>
# 选项：
#   --interval=30s   检查间隔（默认 30s）
#   --timeout=10s    单次检查超时（默认 30s）
#   --retries=3      连续失败次数阈值（默认 3）
#   --start-period=40s  启动缓冲期，此期间失败不计入

HEALTHCHECK NONE   # 禁用基础镜像的健康检查
```

```dockerfile
FROM nginx
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1
```

- 容器状态会变为 `healthy` / `unhealthy`。
- 配合 Compose 的 `depends_on` + `condition: service_healthy` 可实现服务启动顺序控制。

### 2.10 CMD —— 默认启动命令

```dockerfile
# exec 格式（推荐）
CMD ["可执行文件", "参数1", "参数2"]

# shell 格式
CMD command param1

# 作为 ENTRYPOINT 的默认参数
CMD ["参数1", "参数2"]
```

- 指定容器启动时**默认执行**的命令，每个 Dockerfile 只能有一个（多个时仅最后一个生效）。
- **`docker run` 后面跟的命令会完全覆盖 CMD**。
- 若同时有 `ENTRYPOINT`，`CMD` 就退化为 ENTRYPOINT 的默认参数。

### 2.11 ENTRYPOINT —— 入口命令

```dockerfile
# exec 格式（推荐）
ENTRYPOINT ["executable", "param1", "param2"]

# shell 格式（不推荐）
ENTRYPOINT command param1 param2
```

- 指定容器启动时**必定执行**的主命令。
- `docker run` 传的参数会**追加**到 ENTRYPOINT 之后，而非覆盖。
- 可用 `--entrypoint` 强制覆盖。

```dockerfile
FROM ubuntu
ENTRYPOINT ["echo"]
CMD ["Hello Docker"]
```

```bash
docker run myimage           # Hello Docker（ENTRYPOINT + CMD）
docker run myimage "World"   # World（CMD 被替换）
docker run --entrypoint ls myimage /   # 执行 ls /
```

### 2.12 CMD 与 ENTRYPOINT 的区别

| 特性 | CMD | ENTRYPOINT |
|------|-----|------------|
| **作用** | 默认启动命令 | 必定执行的主命令 |
| **docker run 参数** | **完全覆盖** | **追加**在后面 |
| **覆盖方式** | 直接传命令 | 需用 `--entrypoint` |
| **组合使用** | 作为 ENTRYPOINT 的默认参数 | 作为主命令，CMD 提供默认参数 |
| **推荐场景** | 可变参数、可选命令 | 固定主命令、类似"可执行程序" |

**组合使用模式（最佳实践）**：

```dockerfile
# 模式 1：ENTRYPOINT + CMD（推荐）
FROM ubuntu
ENTRYPOINT ["curl"]            # 主命令固定
CMD ["https://example.com"]    # 默认参数可变

docker run myimage                        # curl https://example.com
docker run myimage https://google.com     # curl https://google.com
docker run myimage -I https://example.com # curl -I https://example.com
```

```dockerfile
# 模式 2：只用 CMD（灵活场景）
FROM ubuntu
CMD ["nginx", "-g", "daemon off;"]
docker run myimage      # 启动 nginx
docker run myimage bash # 改为 bash（调试）
```

```dockerfile
# 模式 3：只用 ENTRYPOINT（固定命令）
FROM ubuntu
ENTRYPOINT ["python", "app.py"]
docker run myimage          # python app.py
docker run myimage --debug  # python app.py --debug
```

### 2.13 Shell 格式 vs Exec 格式（信号传递）

| 格式 | CMD | ENTRYPOINT | 特点 |
|------|-----|------------|------|
| **exec 格式** | `CMD ["cmd", "args"]` | `ENTRYPOINT ["cmd", "args"]` | 推荐，信号正确传递 |
| **shell 格式** | `CMD cmd args` | `ENTRYPOINT cmd args` | 不推荐，会套一层 shell |

**exec 格式的优势**：

- 程序作为 **PID 1** 直接运行，容器能正确接收 `SIGTERM`/`SIGINT`，实现优雅停止。
- 注意：exec 格式是 JSON 数组，**必须用双引号**，不能写单引号。

**shell 格式的问题**：

```dockerfile
ENTRYPOINT python app.py
# 实际执行 /bin/sh -c "python app.py"
# PID 1 是 sh，python 是子进程，信号无法传递给 python
# docker stop 时 python 收不到 SIGTERM，等待超时后被 SIGKILL 强杀
```

> 若应用需要正确处理停止信号，务必使用 exec 格式；或配合 `--init`（`docker run --init`）用一个轻量 init 进程转发信号、回收僵尸进程。

### 2.14 LABEL —— 元数据

```dockerfile
LABEL <key>=<value> [<key>=<value> ...]

LABEL maintainer="team@example.com" version="1.0" environment="production"

LABEL maintainer="team@example.com" \
      version="1.0" \
      environment="production"
```

- 为镜像添加键值对元数据，用 `docker inspect <image>` 的 `"Labels"` 字段查看。
- 可用于 CI/CD 工具筛选、镜像分类、版本追踪。
- 团队内建议统一前缀（如 `org.label-schema.*`），不要存敏感信息。

### 2.15 多阶段构建

将构建环境与运行环境分离，大幅减小镜像体积：

```dockerfile
# 阶段 1：构建（包含完整工具链）
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN go build -o myapp

# 阶段 2：运行（仅保留二进制）
FROM alpine:3.19
COPY --from=builder /app/myapp /usr/local/bin/myapp
CMD ["myapp"]
```

```bash
# 只构建到 builder 阶段（调试用）
docker build --target builder -t myapp:builder .

# 构建最终镜像
docker build -t myapp:1.0 .
```

- 每个 `FROM` 开启一个新阶段，前面的阶段可用 `AS` 命名。
- `COPY --from=<阶段名|索引>` 从其他阶段复制产物。
- 最终镜像只包含最后一个阶段，构建工具链不进入产物。

### 2.16 .dockerignore

在构建上下文根目录创建 `.dockerignore`，排除不需要的文件：

```text
node_modules
.git
dist
*.md
.env
.DS_Store
__pycache__
*.pyc
.venv
```

- **作用**：减小构建上下文（`docker build .` 会把整个上下文发给 daemon）、加速构建、避免敏感文件（如 `.env`）打进镜像。

### 2.17 构建缓存与优化

```dockerfile
# ❌ 错误：每次代码变更都重新安装依赖
COPY . /app
RUN pip install -r requirements.txt

# ✅ 正确：先复制依赖文件，利用缓存
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app
```

**缓存失效规则**：

- 指令本身变更 → 该层及后续所有层缓存失效。
- `COPY`/`ADD` 的源文件变更 → 该层及后续缓存失效。
- **尽量把变化频率低的指令放前面**，变化频率高的（如代码）放后面。

**其他优化技巧**：

1. 选择更小的基础镜像（`alpine`、`-slim`、`distroless`）。
2. 合并 `RUN`、清理包管理器缓存（见 2.2）。
3. 多阶段构建（见 2.15）。
4. 使用 `--no-cache` 强制全量重建排查缓存问题。

---

## 3. CLI 命令行详解

> 本节命令都在终端输入，由 `docker` 客户端执行。按功能分为：构建、镜像、容器、存储、网络、系统管理。

### 3.1 构建与镜像管理

#### docker build

```bash
docker build [OPTIONS] PATH | URL | -
```

| 选项 | 说明 | 示例 |
|------|------|------|
| `-t, --tag` | 镜像名和标签 | `-t myapp:1.0` |
| `-f, --file` | 指定 Dockerfile 路径 | `-f Dockerfile.prod .` |
| `--build-arg` | 传递构建参数 | `--build-arg VERSION=2.0` |
| `--no-cache` | 不使用构建缓存 | `--no-cache` |
| `--platform` | 指定目标平台 | `--platform=linux/amd64` |
| `--target` | 构建到指定阶段 | `--target builder` |
| `--progress` | 进度显示方式 | `--progress=plain` |
| `-q, --quiet` | 静默，只输出镜像 ID | `-q` |
| `--rm` | 构建后删除中间容器（默认 true） | `--rm=false` |

```bash
# 基本构建（当前目录 Dockerfile）
docker build -t myapp:1.0 .

# 指定 Dockerfile
docker build -t myapp:1.0 -f docker/Dockerfile.prod .

# 传递构建参数
docker build -t myapp:1.0 --build-arg VERSION=2.0 .

# 不使用缓存
docker build --no-cache -t myapp:1.0 .

# 跨平台构建
docker build --platform=linux/amd64,linux/arm64 -t myapp:1.0 .

# 多阶段只构建到指定阶段
docker build --target builder -t myapp:builder .

# 详细构建日志（排查缓存/报错）
docker build --progress=plain -t myapp:1.0 .

# 从 Git 仓库构建
docker build -t myapp:1.0 https://github.com/user/repo.git#main

# 从 stdin 读取 Dockerfile（无构建上下文）
docker build -t myapp:1.0 - <<EOF
FROM alpine
RUN echo "hello"
EOF
```

#### docker pull / push

```bash
# 拉取
docker pull nginx:latest
docker pull --platform=linux/arm64 nginx:latest
docker pull --platform=linux/amd64 nginx:latest

# 从私有仓库拉取
docker pull [Registry地址[:端口]/]仓库名[:标签]
docker pull registry.example.com/myapp:1.0

# 拉取所有标签
docker pull --all-tags nginx

# 静默模式
docker pull -q nginx:latest
```

```bash
# 推送到仓库
docker push myapp:1.0

# 推送到私有仓库（先 tag 到仓库前缀）
docker tag myapp:1.0 registry.example.com/myapp:1.0
docker push registry.example.com/myapp:1.0

# 登录/登出
docker login
docker login registry.example.com
docker logout registry.example.com
```

#### docker image

```bash
# 列出镜像
docker image ls                    # 同 docker images
docker image ls -a                 # 含中间层
docker image ls -q                 # 只显示 ID
docker image ls --format "{{.Repository}}:{{.Tag}}"
docker image ls --filter "dangling=true"   # 悬空镜像（无标签）

# 删除镜像
docker image rm <镜像名或ID>       # 同 docker rmi
docker image rm $(docker image ls -q)      # 删除所有（危险）
docker image rm -f <ID>            # 强制删除

# 构建
docker image build -t myapp:1.0 .  # 同 docker build

# 查看详情 / 历史
docker image inspect <镜像名或ID>
docker image history <镜像名或ID>

# 清理悬空镜像
docker image prune
docker image prune -a              # 删除所有未被容器使用的镜像

# 标记 / 推送
docker image tag source:tag target:tag
docker image push <镜像名:标签>

# 保存/加载（离线迁移）
docker image save -o myapp.tar myapp:1.0   # 导出
docker image load -i myapp.tar             # 导入

# 查看占用空间
docker image ls --format "{{.Repository}}:{{.Tag}}\t{{.Size}}"
```

### 3.2 容器管理

#### docker run

```bash
docker run [OPTIONS] IMAGE [COMMAND] [ARG...]
```

**常用选项速查**：

| 选项 | 说明 |
|------|------|
| `-d` | 后台运行（detached） |
| `-it` | `-i` 保持 STDIN + `-t` 分配伪终端（交互式） |
| `--name` | 指定容器名 |
| `--rm` | 退出后自动删除容器 |
| `-p` | 端口映射 `宿主机:容器` |
| `-P` | 随机映射所有 EXPOSE 端口 |
| `-v` / `--mount` | 挂载卷 |
| `-e` / `--env-file` | 环境变量 |
| `--restart` | 重启策略 |
| `--cpus` / `--memory` | 资源限制 |
| `--network` | 网络模式 |
| `--gpus` | GPU 设备 |
| `-w` | 容器内工作目录 |
| `-u` | 运行用户 |

```bash
# 交互式运行（进入容器）
docker run -it --rm ubuntu:latest /bin/bash

# 后台运行
docker run -d --name myapp -p 8080:80 nginx:latest

# 带环境变量
docker run -d --name myapp \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=mydb \
  mysql:latest

# 使用 env 文件
docker run -d --name myapp --env-file .env myapp:1.0

# 重启策略：no | on-failure[:max-retries] | always | unless-stopped
docker run -d --name myapp --restart=always nginx:latest

# 资源限制
docker run -d --name myapp \
  --cpus=2 --memory=512m --memory-swap=1g nginx:latest

# GPU
docker run -d --name myapp --gpus all pytorch/pytorch:latest
docker run -d --name myapp --gpus '"device=0,1"' pytorch/pytorch:latest
```

**`-it` 解析**：`-i`（interactive）保持 STDIN 打开，`-t`（tty）分配伪终端。二者通常成对使用，交互式 shell 场景缺一不可。

**`--restart` 重启策略详解**：

`--restart` 决定容器**退出后**（以及 Docker 守护进程/宿主机重启后）是否自动重启，有 4 种取值：

| 取值 | 触发重启的条件 | 宿主机/守护进程重启后 | 适用场景 |
|------|---------------|---------------------|---------|
| `no` | 从不自动重启 | 不重启 | 默认值，一次性任务 |
| `on-failure[:N]` | 仅**非正常退出**（退出码非 0）时 | 守护进程重启时**会**尝试重启（若之前异常退出） | 需要容错但希望正常退出后保持停止 |
| `always` | **任何情况**（含正常退出） | 总会重启 | 常驻服务（web、数据库） |
| `unless-stopped` | 任何情况，但**手动 `docker stop` 后不重启** | 除非被手动停止，否则重启 | 推荐的生产环境默认策略 |

```bash
# 默认：不自动重启
docker run -d --name job myapp:1.0

# 异常退出才重启，最多重试 3 次（超过后放弃）
docker run -d --name job --restart=on-failure:3 myapp:1.0

# 无论什么原因退出都重启
docker run -d --name web --restart=always nginx:latest

# 类似 always，但手动 stop 后不会在 daemon 重启时被拉起
docker run -d --name web --restart=unless-stopped nginx:latest
```

**关键区别：`always` vs `unless-stopped`**

- 两者在日常运行中行为几乎一致：容器退出即自动重启。
- 差异体现在**守护进程重启（或宿主机重启）**时：
  - `always`：无论容器之前是什么状态，daemon 启动后都会把它拉起。
  - `unless-stopped`：如果容器在 daemon 停止前是被你**手动 `docker stop`** 的，则 daemon 重启后**不会**再拉起它。
- 通俗理解：`unless-stopped` = "除非我明确让你停，否则一直给我活着"，这是**生产环境首选**——既保证自愈，又尊重运维的停机意图。

**注意事项**：

1. `--restart` 只影响"退出后是否重启"，与 `docker restart` 命令（手动重启）是两回事。
2. 只有 `docker run` 时指定才生效；对已运行的容器可用 `docker update --restart=always <容器>` 修改。
3. 退出码为 0 的正常退出：`always`/`unless-stopped` 会重启，`on-failure` 不会。
4. 可结合 `--rm` 吗？**不可以**——`--rm`（退出即删除）与 `--restart`（退出即重启）语义冲突，同时指定会报错。

#### docker ps

```bash
docker ps               # 运行中的容器
docker ps -a            # 所有容器（含停止）
docker ps -q            # 只显示 ID
docker ps -n 5          # 最近 5 个
docker ps --filter "status=exited"
docker ps --filter "name=myapp"
docker ps --filter "ancestor=nginx:latest"
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
docker ps -s            # 显示容器占用大小
```

**容器状态机**：

```
created ──> running ──> exited
               │  ↕        │
            paused     restarting
                          │
                         dead（通常资源不足）
```

| 状态 | 含义 |
|------|------|
| `created` | 已创建未启动 |
| `running` | 正在运行 |
| `paused` | 已暂停（冻结进程） |
| `restarting` | 重启中 |
| `removing` | 删除中 |
| `exited` | 已停止 |
| `dead` | 无法启动（通常资源不足） |

#### docker start / stop / restart

```bash
docker start <容器名或ID>        # 启动已停止容器
docker start -ai <容器名或ID>    # 交互式启动

docker stop <容器名或ID>         # 优雅停止（SIGTERM，超时后 SIGKILL）
docker stop -t 30 <容器名或ID>   # 指定超时（秒）

docker restart <容器名或ID>      # 重启

docker pause <容器名或ID>        # 暂停（冻结进程）
docker unpause <容器名或ID>      # 恢复

docker kill <容器名或ID>         # 强制终止（SIGKILL）
```

#### docker exec vs attach

```bash
# exec：在运行容器内新开进程（不影响主进程）
docker exec -it <容器> /bin/bash
docker exec -it <容器> /bin/sh       # Alpine 无 bash
docker exec <容器> ls /app
docker exec -u root <容器> apt-get update
docker exec -e DEBUG=1 <容器> python app.py
docker exec -w /app <容器> ls
docker exec -d <容器> python bg_task.py   # 后台执行

# attach：附加到容器主进程（PID 1）
docker attach <容器>
```

**`exec` vs `attach` 区别**：

| | `docker exec` | `docker attach` |
|--|--------------|-----------------|
| 连接对象 | 新开的进程 | 主进程（PID 1）的 STDIN/STDOUT |
| 退出影响 | 不影响容器 | `exit`/`Ctrl+C` 会导致**容器停止** |
| 用途 | 进入容器执行命令 | 查看主进程实时输出 |

> `attach` 安全退出（不停止容器）：`Ctrl+P` → `Ctrl+Q`。

#### docker logs

```bash
docker logs <容器>
docker logs -f <容器>              # 实时跟踪（tail -f）
docker logs --tail 100 <容器>      # 最近 100 行
docker logs -t <容器>              # 显示时间戳
docker logs --since 30m <容器>     # 最近 30 分钟
docker logs --until "2025-01-01T12:00:00" <容器>
docker logs -f --tail 50 <容器>
```

**日志驱动**：

```bash
docker inspect --format '{{.HostConfig.LogConfig.Type}}' <容器>

docker run -d --log-driver=json-file \
  --log-opt max-size=10m --log-opt max-file=3 nginx:latest
```

常用驱动：`json-file`（默认）、`local`（自动轮转）、`syslog`、`none`（禁用）。

#### docker cp

```bash
# 容器 → 宿主机
docker cp <容器>:/app/config.yml ./config.yml
docker cp <容器>:/app/logs/ ./logs/

# 宿主机 → 容器
docker cp ./config.yml <容器>:/app/config.yml
docker cp ./data/ <容器>:/app/data/

# 保留权限
docker cp -a <容器>:/app/data/ ./data/
```

> `docker cp` 不要求容器运行中，已停止容器也可复制。

#### docker rm / inspect / top / stats

```bash
docker rm <容器>                              # 删除已停止容器
docker rm -f <容器>                           # 强制删除运行中容器
docker rm -v <容器>                           # 同时删除匿名卷
docker container prune                        # 删除所有已停止容器
docker rm $(docker ps -a -q -f "status=exited")
```

```bash
docker inspect <容器>     # 容器/镜像详情
docker inspect --format '{{.NetworkSettings.IPAddress}}' <容器>
docker inspect --format '{{.State.Status}}' <容器>
docker inspect --format '{{.Config.Env}}' <容器>
docker inspect --format '{{json .State}}' <容器> | python3 -m json.tool

docker port <容器>        # 查看端口映射
docker top <容器>         # 容器内进程

docker stats              # 实时资源使用
docker stats --no-stream
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

#### docker commit / diff / export / import

```bash
docker commit <容器> myapp:1.0
docker commit -m "添加配置" -a "author" <容器> myapp:1.0
docker commit --change 'CMD ["python", "app.py"]' <容器> myapp:1.0

docker diff <容器>     # A=新增 C=修改 D=删除

docker export <容器> -o myapp.tar     # 导出容器文件系统
docker import myapp.tar myapp:1.0     # 导入为镜像
docker import http://example.com/myapp.tar myapp:1.0
```

> **`export/import` vs `save/load`**：`export/import` 操作**容器快照**（丢历史和层信息）；`save/load` 操作**镜像**（保留完整层信息）。迁移镜像用 `save/load`，迁移容器当前状态用 `export/import`。
>
> `docker commit` 适合快速调试，**不建议**用于生产镜像构建，应优先用 Dockerfile。

### 3.3 数据卷管理（Volume）

Docker 数据卷是容器数据持久化的核心机制，用于宿主机与容器间、容器与容器间共享数据。

**卷的作用**：数据持久化、数据共享、数据隔离、性能优化、跨平台一致。

#### 三种挂载类型

| 类型 | 存储位置 | 适用场景 |
|------|---------|---------|
| **命名卷（Named Volume）** | Docker 管理（`/var/lib/docker/volumes/`） | 生产环境 |
| **匿名卷（Anonymous Volume）** | Docker 管理，随机名 | Dockerfile `VOLUME` 声明 |
| **绑定挂载（Bind Mount）** | 宿主机指定路径 | 开发环境、配置文件 |

```bash
# 命名卷
docker volume create my-vol
docker volume inspect my-vol
docker volume ls
docker run -d --name myapp -v my-vol:/app/data nginx

# 匿名卷
docker run -d --name myapp -v /app/data nginx

# 绑定挂载
docker run -d --name myapp -v /host/path:/container/path nginx
docker run -d --name myapp -v /host/config.yml:/app/config.yml nginx
docker run -d --name myapp -v /host/path:/container/path:ro nginx   # 只读
```

#### `-v` vs `--mount`

| 特性 | `-v` | `--mount` |
|------|------|-----------|
| 语法简洁性 | 简洁 | 详细 |
| 错误提示 | 不明确 | 明确 |
| SELinux | 支持（`z`/`Z`） | 不支持 |
| 卷不存在时 | 自动创建 | 报错 |
| 推荐场景 | 开发环境 | 生产环境 |

```bash
# --mount 命名卷
docker run -d --name myapp \
  --mount type=volume,source=my-vol,target=/app/data nginx

# --mount 绑定挂载
docker run -d --name myapp \
  --mount type=bind,source=/host/path,target=/app/data,readonly nginx

# --mount tmpfs（内存临时文件系统）
docker run -d --name myapp \
  --mount type=tmpfs,target=/app/tmp nginx
```

#### 卷管理命令

```bash
docker volume create my-vol
docker volume create --driver local my-vol
docker volume ls
docker volume inspect my-vol
docker volume rm my-vol
docker volume prune            # 清理未使用卷
docker ps --filter volume=my-vol
```

#### 备份与恢复

```bash
# 备份
docker run --rm -v my-vol:/data -v $(pwd):/backup \
  alpine tar cvf /backup/my-vol-backup.tar /data

# 恢复
docker run --rm -v my-vol:/data -v $(pwd):/backup \
  alpine tar xvf /backup/my-vol-backup.tar -C /
```

#### 常见问题

```bash
# 1. 权限问题：容器用户与宿主机不一致
docker run -d --name app -v /host/data:/data \
  --user $(id -u):$(id -g) myapp

# 2. SELinux（CentOS/RHEL）
docker run -d --name app -v /host/data:/data:z myapp

# 3. 路径不存在
#    -v 会自动创建目录；--mount 会报错

# 4. Windows/Mac 路径
#    Docker Desktop 需在设置中允许访问目录
```

### 3.4 网络管理（Network）

#### 网络模式对比

| 模式 | 隔离性 | 性能 | 适用场景 |
|------|--------|------|----------|
| `bridge` | 高 | 中等 | 默认隔离环境（单机） |
| `host` | 低 | 高 | 高性能需求 |
| `none` | 最高 | 无 | 无网络需求 |
| `container` | 低 | 高 | 共享网络栈（Sidecar） |
| `user-defined` | 高 | 中等 | 多容器应用（DNS 解析） |
| `overlay` | 高 | 中等 | 跨主机通信（Swarm） |
| `macvlan`/`ipvlan` | 高 | 高 | 直接暴露物理网络 |

#### 各模式详解

**1. bridge（默认桥接）**

- 每个容器分配独立 IP，通过 NAT 访问外网，用 `-p` 映射端口。
- 底层通过 iptables + docker0 网桥实现。
- 同一默认桥接网络下，容器只能通过 IP 互访（**无 DNS 解析**）。

```bash
docker run -d --name my_container -p 8080:80 nginx
docker inspect my_container | grep IPAddress
```

**2. host（主机模式）**

- 共享宿主机网络命名空间，直接用宿主机 IP/端口，无 NAT 开销，隔离性差。

```bash
docker run -d --name my_container --network=host nginx
```

**3. none（无网络）**

```bash
docker run -d --name my_container --network=none nginx
```

**4. container（共享另一容器网络）**

```bash
docker run -d --name container1 nginx
docker run -d --name container2 --network=container:container1 alpine
```

**5. 自定义网络（推荐）**

- 支持**容器名 DNS 自动解析**，容器间可直接用名字互访。

```bash
docker network create my_network
docker run -d --name app1 --network=my_network nginx
docker run -d --name app2 --network=my_network mysql
docker exec app2 ping app1   # 直接通过容器名解析
```

**6. overlay（跨主机）**

```bash
docker network create -d overlay my_overlay_net   # Swarm 集群
```

**7. macvlan / ipvlan**

```bash
docker network create -d macvlan \
  --subnet=192.168.1.0/24 --gateway=192.168.1.1 \
  --parent=eth0 my_macvlan_net
```

#### 网络命令

```bash
docker network ls
docker network inspect my_network
docker network inspect bridge

docker network create my_network
docker network create --driver bridge --subnet 172.20.0.0/16 my_network
docker network create --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 my_network

docker network connect my_network my_container
docker network disconnect my_network my_container

docker run -d --name app --network=my_network nginx
docker network rm my_network
docker network prune
```

#### 如何选择网络模式

- **开发测试**：默认 `bridge` 或自定义网络。
- **生产环境**：`host`（高性能）或自定义网络（隔离 + DNS）。
- **跨主机**：`overlay`（Swarm 集群）。
- **物理网络集成**：`macvlan`/`ipvlan`。

### 3.5 系统管理（docker system）

#### docker system df

```bash
docker system df        # 概览
docker system df -v     # 详细（每个镜像/容器/卷/缓存占用）
```

```text
TYPE            TOTAL   ACTIVE  SIZE    RECLAIMABLE
Images          15      5       5.2GB   3.1GB (59%)
Containers      8       3       120MB   80MB (66%)
Local Volumes   6       3       800MB   400MB (50%)
Build Cache     25      0       2.1GB   2.1GB (100%)
```

#### docker system prune

```bash
docker system prune                    # 清理停止容器、未用网络、悬空镜像、构建缓存
docker system prune -a                 # 同时清理未用镜像
docker system prune --volumes          # 同时清理卷（⚠️ 删数据）
docker system prune -a --volumes       # 全量（危险）
docker system prune -f                 # 不确认
```

**清理范围对比**：

| 命令 | 停止容器 | 悬空镜像 | 未用镜像 | 未用网络 | 未用卷 | 构建缓存 |
|------|---------|---------|---------|---------|-------|---------|
| `system prune` | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| `system prune -a` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `system prune -a --volumes` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

#### 分项清理

```bash
docker container prune      # 停止容器
docker image prune          # 悬空镜像
docker image prune -a       # 未用镜像
docker volume prune         # 未用卷
docker network prune        # 未用网络
docker builder prune        # 构建缓存

docker builder prune --filter "until=24h"
docker image prune -a --filter "until=2025-01-01"
docker image prune -a --filter "label!=keep"
```

#### 磁盘排查流程

```bash
docker system df -v
docker image ls --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" | sort -k2 -h
docker system prune -a
docker system prune -a --volumes   # 深度清理
docker builder prune -a
```

---

## 4. Docker Compose

用 `compose.yaml` 声明式管理多容器应用。

### 4.1 compose.yaml 基本结构

```yaml
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html
    depends_on:
      - db
    networks:
      - app-network
    restart: unless-stopped

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: mydb
    volumes:
      - db-data:/var/lib/mysql
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

volumes:
  db-data:
  redis-data:

networks:
  app-network:
    driver: bridge
```

### 4.2 常用命令

```bash
docker compose up -d                 # 启动所有服务（后台）
docker compose up -d --build         # 启动并强制重建镜像
docker compose up -d web redis       # 启动指定服务

docker compose down                  # 停止并删除所有容器
docker compose down -v               # 同时删除卷（清数据）

docker compose ps                    # 状态
docker compose logs                  # 日志
docker compose logs -f web
docker compose logs --tail 50 web

docker compose exec web /bin/bash
docker compose exec db mysql -uroot -proot

docker compose run --rm web python manage.py migrate   # 一次性命令

docker compose build                 # 重建镜像
docker compose build --no-cache
docker compose pull                  # 拉取最新镜像
docker compose restart web
docker compose pause web / unpause web

docker compose config                # 验证 yaml 是否正确
docker compose top                   # 资源使用
```

### 4.3 多环境配置

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose -p myproject up -d
docker compose --env-file .env.prod up -d
```

**环境变量优先级（高 → 低）**：

1. `compose.yaml` 中硬编码的值
2. shell 环境变量
3. `.env` 文件
4. Dockerfile 中的 `ENV`
5. 变量定义的默认值

### 4.4 构建配置

```yaml
services:
  app:
    build:
      context: .                    # 构建上下文
      dockerfile: Dockerfile.prod   # 指定 Dockerfile
      args:                         # 构建参数
        VERSION: "2.0"
      target: production            # 多阶段目标
    image: myapp:2.0               # 构建后镜像名
```

### 4.5 健康检查

```yaml
services:
  web:
    image: nginx:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 4.6 资源限制

```yaml
services:
  app:
    image: myapp:latest
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 512M
        reservations:
          cpus: "0.5"
          memory: 256M
```

### 4.7 常用模板（Web + DB + Redis）

```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  pg-data:
  redis-data:
```

---

## 5. 镜像加速与 Registry

### 5.1 镜像加速器配置

国内拉取 Docker Hub 较慢，可配置镜像加速器。配置文件：

- **macOS**：`~/.docker/daemon.json`（Docker Desktop → Settings → Docker Engine）
- **Linux**：`/etc/docker/daemon.json`

```json
{
  "registry-mirrors" : [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io",
    "https://mirror.aliyuncs.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.baidubce.com",
    "https://docker.nju.edu.cn",
    "https://docker.rainbond.cc"
  ],
  "insecure-registries" : [
    "http://10.11.3.164"
  ]
}
```

> 镜像源可用性经常变化，失效时替换为当前可用的加速地址即可。

### 5.2 私有仓库

```bash
# 登录私有仓库
docker login registry.example.com

# 打 tag 并推送
docker tag myapp:1.0 registry.example.com/myapp:1.0
docker push registry.example.com/myapp:1.0

# 拉取
docker pull registry.example.com/myapp:1.0
```

---

## 6. 常用技巧

### 6.1 Mac 上构建 linux/amd64 镜像

```bash
# 方法 1：--platform
docker build --platform=linux/amd64 -t myapp:1.0 .
docker run --platform=linux/amd64 myapp:1.0

# 方法 2：buildx 多平台构建
docker buildx build --platform=linux/amd64,linux/arm64 -t myapp:1.0 .

# 方法 3：Dockerfile 指定
# FROM --platform=linux/amd64 python:3.11
```

### 6.2 清理构建缓存

```bash
docker builder prune
docker builder prune -a
docker builder prune --filter "until=24h"
```

### 6.3 Dockerfile 中更换国内源

```dockerfile
# Ubuntu/Debian 换源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# Alpine 换源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# pip 换源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# npm 换源
RUN npm config set registry https://registry.npmmirror.com
```

### 6.4 常见问题排查

| 问题 | 排查方向 |
|------|---------|
| 容器启动即退出 | `docker logs` 看主进程是否结束；`docker inspect` 看 `State.ExitCode` |
| 端口不通 | `docker port` 确认映射；`--network` 模式是否正确 |
| 容器间 ping 不通 | 默认 bridge 无 DNS，用自定义网络 |
| 镜像体积过大 | 多阶段构建、合并 RUN、换 slim/alpine 基础镜像 |
| `docker stop` 卡住 | 应用未处理 SIGTERM，改用 exec 格式或 `--init` |

---

## 参考链接

- [Docker cp 命令详解](https://blog.csdn.net/Tester_muller/article/details/131678630)
- [Mac 上构建 Docker 配置 linux/amd64](https://www.jianshu.com/p/3119635e2196)
- [Docker 深度清除镜像缓存](https://juejin.cn/post/7041119023286730782)
- [Dockerfile 中更换国内源](https://blog.csdn.net/yyj108317/article/details/105984674)

[[k8s#k8s概述]]
