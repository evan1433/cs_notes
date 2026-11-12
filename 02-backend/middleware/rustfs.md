---
title: RustFS
description: Rust 编写的 S3 兼容分布式对象存储，纠删码架构、部署拓扑、rc 运维与 MinIO 迁移指南
tags:
  - middleware
  - rustfs
  - object-storage
  - s3
  - rust
  - distributed-system
date: 2026-11-09
---

# RustFS

## 概述

RustFS 是一个用 **Rust** 编写的分布式**对象存储**系统，兼容 Amazon S3 API，采用 Apache 2.0 协议开源。它解决的核心问题与 [[minio]] 相同——「一堆裸盘 + 一个二进制」提供 PB 级 S3 存储——但实现语言换成了 Rust，并显式把**与 MinIO / Ceph 的迁移和共存**作为产品目标：`MINIO_*` 环境变量可直接映射、`rc` 命令行沿用了 `mc` 的操作习惯、桶级别还提供按需拉取（on-demand migration）能力。

> 版本提示：截至 2026 年 11 月，发布线为 **1.0.x**（Helm chart 引用 `1.0.4`、Console 文档示例为 `v1.0.3`），CLI `rc` 为 `v0.1.30`。RustFS 迭代很快，命令与变量名请以 `rc --help` 和官方 [环境变量参考](https://docs.rustfs.com/en/reference/environment-variables) 为准。

典型应用场景：

| 场景 | 说明 |
|------|------|
| MinIO 替代 / 迁移 | 配置变量与 CLI 语义高度兼容，迁移成本低 |
| AI/ML 数据湖 | 存放训练样本、模型权重、数据集版本；内置 `AiTraining` 缓冲配置档 |
| 大数据存储层 | 与 Spark / Flink / Trino / Iceberg / Hudi 集成（官方有集成文档） |
| 私有云对象存储 | 替代公有云 S3，数据不出内网 |
| 备份归档 | 结合生命周期规则与远程分层（tiered storage）做冷热分层 |
| 应用静态资源 | 图片、视频、附件直传与分发 |

核心特征：

- **S3 兼容**：AWS Signature V4 签名，`aws-cli`、AWS SDK、`rclone`、`s3cmd`、Terraform 等生态可直接复用
- **纠删码保护**：Reed-Solomon 编码，无 RAID、无多副本
- **单二进制 + 无外部依赖**：不依赖 ZooKeeper / etcd 等元数据服务
- **轻量跨平台**：Linux、macOS、Windows、FreeBSD，x86 / ARM / RISC-V
- **声明式初始化**：容器支持在启动时自动创建桶（bucket bootstrap）
- **可观测性内建**：原生 OTLP/HTTP 导出 traces / metrics / logs

## 与 MinIO 的关系

RustFS 不是 MinIO 的分支，而是「同协议、同运维语义」的重实现。理解差异比记住功能列表更重要：

| 维度 | MinIO | RustFS |
|------|-------|--------|
| 实现语言 | Go | Rust（Tokio 异步运行时） |
| 开源协议 | AGPL-3.0（社区版功能有裁剪） | **Apache 2.0**（商用友好） |
| 配置变量前缀 | `MINIO_*` | `RUSTFS_*`（自动映射白名单内的 `MINIO_*`） |
| 命令行 | `mc` | `rc`（命令组更「名词优先」：`rc bucket ...`、`rc object ...`） |
| 部署拓扑术语 | Server Pool / Erasure Set | Storage Pool / Erasure Set（一致） |
| 桶级别迁移 | 主要靠 `mc mirror` / 站点复制 | 额外提供**按需拉取（on-demand migration）** |
| 生态成熟度 | 十年积累，周边工具齐全 | 较新，S3 兼容性以 Ceph `s3tests` 子集为闸门 |
| 硬件要求 | 生产建议 4 节点起 | 生产建议 MNMD（4+ 节点），单机可用 SNMD |

S3 兼容性现状（官方兼容矩阵，2026-08 快照）：已实现测试 455 例；**ACL 授权被有意排除**，桶访问日志、桶所有权控制、`POST Object` 表单校验等仍标记为 planned。加密对象格式**不跨实现可移植**——RustFS 加密的对象不能直接拷给 MinIO 读。

> 换句话说：常规的桶/对象/分片上传/预签名/版本控制/Object Lock 都能用；如果业务依赖 ACL 或 S3 POST 表单上传，需要先验证。

## 核心概念与部署拓扑

### 术语对照

| 层级 | S3 视角 | RustFS 术语 | 说明 |
|------|---------|-------------|------|
| 集群 | — | **Cluster** | 一组节点 + 一组存储池 |
| 分组 | — | **Storage Pool** | 可横向扩容的同构节点组 |
| 分片组 | — | **Erasure Set** | 一组 Drive，宽度 2~16（多盘模式） |
| 设备 | — | **Drive** | 一块裸盘 / 挂载点 |
| 命名空间 | **Bucket** | Bucket | 扁平命名空间 |
| 数据 | **Object** | Object | 数据分片 + 元数据 |
| 描述信息 | **Metadata** | 元数据文件 | 含校验和（支持 128 KiB 以下对象内联） |

### 三种部署形态

| 模式 | 全称 | 节点 | 磁盘 | 容错能力 | 适用 |
|------|------|------|------|----------|------|
| **SNSD** | Single Node Single Disk | 1 | 1 | **无**（只能靠备份） | 开发、试用、非关键小业务 |
| **SNMD** | Single Node Multiple Disk | 1 | 多 | 可容忍 ≤ M 块盘失效 | 单机中型业务 |
| **MNMD** | Multiple Node Multiple Disk | 4+ | 每节点多块 | 盘级 + 节点级（取决于分片分布） | 生产环境 |

> 生产不要停留在 SNSD。安装脚本默认装出来的就是 SNSD——零冗余。

### 网络与端口

| 端口 | 用途 |
|------|------|
| `9000` | S3 API（同时承载节点间 RPC） |
| `9001` | Web Console |

健康检查端点（默认无需认证，可用 `RUSTFS_HEALTH_ENDPOINT_ENABLE=false` 关闭）：

```bash
curl --fail http://localhost:9000/health          # 存活
curl --fail http://localhost:9000/health/ready    # 就绪（集群依赖已可用）
```

## 快速开始

### 方式一：Linux 官方脚本（systemd）

要求：Linux x86_64 / aarch64、`systemd`、root 或 sudo、已安装 `unzip`。

```bash
# 下载并执行官方安装脚本
curl -O https://rustfs.com/install_rustfs.sh && bash install_rustfs.sh
```

脚本会完成三件事：

```text
/usr/local/bin/rustfs           # 二进制
systemd 服务 rustfs             # 自动注册并启动
/etc/default/rustfs             # 配置文件（含占位凭据）
```

默认数据目录 `/data/rustfs0`，S3 API `9000`，Console `9001`。安装成功后终端会打印：

```text
Service port: 9000,  Console port: 9001,  Data directory: /data/rustfs0
[SECURITY WARNING] Please change the default value for RUSTFS_ACCESS_KEY/RUSTFS_SECRET_KEY immediately
```

**立即改凭据**（不改则回落到 `rustfsadmin` / `rustfsadmin`）：

```bash
# 先生成强密钥，记下输出
openssl rand -base64 24
```

```bash
# /etc/default/rustfs —— 值必须是字面量：systemd 的 EnvironmentFile 不做命令替换，
# 写 $(openssl ...) 会原样当成字符串
RUSTFS_ACCESS_KEY=AKIAEXAMPLEKEY1234
RUSTFS_SECRET_KEY=<上一步 openssl 的输出>
```

```bash
sudo systemctl restart rustfs
sudo systemctl status rustfs --no-pager   # active (running)
```

> **坑**：`RUSTFS_ACCESS_KEY` 必须是**大写字母数字**。Base64 输出可能含 `/`，与 SigV4 的 credential scope（用 `/` 分隔）冲突，会导致签名异常。

### 方式二：Docker

```bash
docker pull rustfs/rustfs:latest
docker volume create rustfs-data

docker run -d \
  --name rustfs \
  --restart unless-stopped \
  -p 9000:9000 \
  -p 9001:9001 \
  -v rustfs-data:/data \
  -e RUSTFS_ACCESS_KEY="AKIAEXAMPLEKEY1234" \
  -e RUSTFS_SECRET_KEY="CHANGE_ME_STRONG_SECRET" \
  -e RUSTFS_ADDRESS=":9000" \
  -e RUSTFS_CONSOLE_ADDRESS=":9001" \
  -e RUSTFS_CONSOLE_ENABLE=true \
  -e RUSTFS_OBS_LOGGER_LEVEL=error \
  -e RUSTFS_OBS_LOG_DIRECTORY="/var/log/rustfs/" \
  rustfs/rustfs:latest \
  /data
```

容器内进程以 **非 root 用户 `rustfs`（uid 10001）** 运行。绑定挂载宿主机目录时必须先改属主，否则报 permission denied：

```bash
sudo chown -R 10001:10001 /data/rustfs
```

同一套参数也可以用命令行 flag 传入（flag 优先级高于环境变量）：

```bash
docker run -d --name rustfs -p 9000:9000 -p 9001:9001 \
  -v rustfs-data:/data \
  rustfs/rustfs:latest \
  --access-key "AKIAEXAMPLEKEY1234" \
  --secret-key "CHANGE_ME_STRONG_SECRET" \
  --address :9000 \
  --console-enable \
  /data
```

验证：

```bash
docker ps --filter name=rustfs
curl --fail http://localhost:9000/health
```

## 部署实践

### 多节点（MNMD）与卷展开语法

RustFS 的 `RUSTFS_VOLUMES` 支持 MinIO 风格的**省略号展开**，一行描述整个集群：

```bash
RUSTFS_VOLUMES="http://node{1...4}:9000/data/rustfs{0...3}"
```

等价于声明了 4 节点 × 4 盘 = 16 个 Drive：

```text
http://node1:9000/data/rustfs0  http://node1:9000/data/rustfs1  ...
http://node4:9000/data/rustfs3
```

每个节点上的启动参数（Docker 场景需 `--network host`，bridge 网络不支持多节点）：

```bash
docker run -d --name rustfs --network host \
  -v /mnt/rustfs/data:/data \
  -e RUSTFS_ACCESS_KEY="AKIAEXAMPLEKEY1234" \
  -e RUSTFS_SECRET_KEY="CHANGE_ME_STRONG_SECRET" \
  -e RUSTFS_ADDRESS=":9000" \
  -e RUSTFS_CONSOLE_ADDRESS=":9001" \
  -e RUSTFS_CONSOLE_ENABLE=true \
  -e RUSTFS_VOLUMES="http://node{1...4}:9000/data/rustfs{0...3}" \
  rustfs/rustfs:latest
```

约束（与 MinIO 一致的部分不再重复，见 [[minio#部署实践]]）：

- 所有节点的卷数量、容量、文件系统应一致（XFS + `noatime`）
- 节点需连续主机名以支持 `{1...N}` 展开，并写入每个节点的 `/etc/hosts` 或 DNS
- NTP 时间同步必须配置，SigV4 校验依赖时间戳
- 全默认凭据的多节点集群必须显式设置 `RUSTFS_RPC_SECRET`（节点间 RPC 认证密钥），否则派生密钥不安全

### 磁盘准备

```bash
# XFS，inode size 512、ftype=1（纠删码依赖 d_type 判断目录类型）
sudo mkfs.xfs -f -i size=512 -n ftype=1 -L RUSTFS0 /dev/sdb

# 按 UUID 挂载，避免设备名漂移
sudo blkid -s UUID -o value /dev/sdb
# /etc/fstab
# UUID=<filesystem-uuid> /data/rustfs0 xfs defaults,noatime,nodiratime 0 0
sudo mount -a && findmnt /data/rustfs0
```

### Kubernetes

官方提供两条路径：**Helm Chart**（单集群快速部署）与 **Operator**（多租户、池扩容、生命周期管理）。二者都支持 cert-manager 证书与 mTLS。细节见 [[helm]] 与 [[kubernetes]]。

## 纠删码与容量规划

### Reed-Solomon 布局

每个**存储池**被切分为若干 Erasure Set，对象只写入**一个** Set。以 `N` 块盘、`M` 个校验片为例：

```text
N = 16, M = 4（EC:4）
  ├─ 12 个数据片 ──▶ 并行写入 12 块盘
  └─  4 个校验片 ──▶ 并行写入  4 块盘

可恢复任意 ≤ 4 块盘失效
容量利用率 ≈ (16 - 4) / 16 = 75%
```

公式与边界：

| 项 | 规则 |
|----|------|
| 数据片 | `N - M` |
| 校验片 | `M` |
| 可容忍失效片数 | `M` |
| 利用率 | `(N - M) / N` |
| 多盘 Set 宽度 | `2 ~ 16` |
| 显式校验片约束 | `M <= N / 2`（且对**每个**池都成立） |
| 故障域 | `M` 是**片**级容错，不必然等于节点级容错 |

> 最后一行是关键：一个节点可能承载同一个 Set 内的多块盘，`EC:4` 不代表能扛 4 台机器同时宕机。

### 自动 parity（推荐不设）

官方建议**不要**显式设置 `RUSTFS_STORAGE_CLASS_STANDARD`，让 RustFS 按每个池的 Set 宽度自动推导：

| Set 内盘数 N | 自动 STANDARD parity | 数据片 | 近似利用率 |
|--------------|----------------------|--------|-------------|
| 1 | `EC:0` | 1 | 100% |
| 2–3 | `EC:1` | N-1 | 50%–67% |
| 4–5 | `EC:2` | N-2 | 50%–60% |
| 6–7 | `EC:3` | N-3 | 50%–57% |
| 8–16 | `EC:4` | N-4 | 50%–75% |

需要固定冗余度时才显式配置：

```bash
# /etc/default/rustfs
RUSTFS_STORAGE_CLASS_STANDARD=EC:4     # STANDARD 存储类
RUSTFS_STORAGE_CLASS_RRS=EC:1          # REDUCED_REDUNDANCY，默认 EC:1
# RUSTFS_ERASURE_SET_DRIVE_COUNT=16    # 仅在你已确认整个池布局对称时才设
```

启动时 RustFS 会**逐池**校验显式配置，非法值直接启动失败（而不是静默降级）——这是比自动纠偏更好的行为，避免"以为有 4 副本、实际只有 2 副本"。

### 容量估算

```text
可用容量 ≈ 裸容量 × (N - M) / N
```

例：16 块 10 TiB 盘组成一个 16 盘 Set、`EC:4`：

```text
160 TiB × (16 - 4) / 16 = 120 TiB
```

这 120 TiB 还要扣掉 XFS 元数据、对象元数据、版本历史、未完成分片、heal 期间的临时占用和运维余量。**按规划值再打 8 折**更接近真实可用。

### 与多副本的取舍

纠删码 vs 三副本的通用权衡（空间效率、重建读放大、失效组合数）与 MinIO 相同，不再重复推导，见 [[minio#与多副本方案对比]]。RustFS 侧的差异只有两点：

- 小于 **128 KiB** 的对象会内联进元数据（`RUSTFS_STORAGE_CLASS_INLINE_BLOCK=131072`），小文件场景能省一次 IO
- 写入持久化策略可调：`RUSTFS_DURABILITY_MODE=strict|relaxed|none`，`relaxed` 换取更低写延迟，代价是掉电时可能丢最近写入

## 关键配置项

RustFS 全部配置都可通过环境变量或同名命令行 flag 提供（flag 优先）。生产最常动的部分：

### 核心与凭据

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RUSTFS_VOLUMES` | 必填（镜像内为 `/data`） | 卷或端点列表，空格分隔，支持 `{N...M}` 展开 |
| `RUSTFS_ADDRESS` | `:9000` | S3 API 监听地址（同时承载节点间 RPC） |
| `RUSTFS_CONSOLE_ADDRESS` | `:9001` | Console 监听地址 |
| `RUSTFS_CONSOLE_ENABLE` | `true` | 是否启用内嵌 Console |
| `RUSTFS_ACCESS_KEY` | `rustfsadmin` | 根 Access Key（可用 `_FILE` 变体读挂载的 secret） |
| `RUSTFS_SECRET_KEY` | `rustfsadmin` | 根 Secret Key（同上） |
| `RUSTFS_RPC_SECRET` | 由 AK/SK 派生 | 节点间 RPC 认证密钥，多节点且用默认凭据时必须显式设置 |
| `RUSTFS_SERVER_DOMAINS` | 未设 | 虚拟主机风格域名，如 `s3.example.com`，不设则只支持 path-style |
| `RUSTFS_REGION` | 回落 `us-east-1` | 返回给客户端的 region |
| `RUSTFS_BUFFER_PROFILE` | `GeneralPurpose` | 缓冲自适应档位：`AiTraining` / `DataAnalytics` / `WebWorkload` / `IndustrialIoT` / `SecureStorage` |
| `RUSTFS_CHECK_UPDATE` | `true` | 启动时向 `version.rustfs.com` 发一次版本检查（仅记日志），内网离线环境应设 `false` |

### 存储与纠删码

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RUSTFS_STORAGE_CLASS_STANDARD` | 自动 | `EC:n`，留空则按 Set 宽度推导 |
| `RUSTFS_STORAGE_CLASS_RRS` | `EC:1` | 低冗余存储类 |
| `RUSTFS_STORAGE_CLASS_INLINE_BLOCK` | `131072` | 内联阈值（128 KiB） |
| `RUSTFS_ERASURE_SET_DRIVE_COUNT` | `0`（自动） | 强制 Set 宽度，2~16 |
| `RUSTFS_DURABILITY_MODE` | 未设 | 写持久化：`strict` / `relaxed` / `none` |

### 自愈与扫描

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RUSTFS_HEAL_AUTO_HEAL_ENABLE` | `true` | 后台自动修复降级对象 |
| `RUSTFS_HEAL_MAX_CONCURRENT_HEALS` | `4` | 并发修复任务上限 |
| `RUSTFS_SCANNER_SPEED` | `default` | 扫描速度档位：`fastest` → `slowest` |
| `RUSTFS_SCANNER_BITROT_CYCLE_SECS` | `2592000`（30 天） | 深度位衰减扫描周期 |
| `RUSTFS_SCANNER_IDLE_MODE` | `true` | 空闲时自动限速，避免抢占业务 IO |

### 可观测与通知

| 变量 | 说明 |
|------|------|
| `RUSTFS_OBS_ENDPOINT` | OTLP/HTTP 根地址，如 `http://otel-collector:4318`；为空则只输出到本地文件/stdout |
| `RUSTFS_OBS_LOGGER_LEVEL` | 日志级别，生产建议 `info` 或 `error` |
| `RUSTFS_OBS_LOG_ROTATION_TIME` | 轮转周期：`hourly` / `daily` / `minutely`，默认 `hourly` |
| `RUSTFS_OBS_LOG_KEEP_FILES` | 保留的轮转文件数，默认 `30` |
| `RUSTFS_NOTIFY_ENABLE` | 开启桶事件通知（Webhook / Kafka / MQTT / MySQL / PG / NATS / Redis / AMQP / Pulsar） |
| `RUSTFS_AUDIT_ENABLE` | 开启审计日志，目标类型与通知相同 |

事件通知的典型用法与 [[minio#事件通知（Event Notification）]] 一致：图片上传后触发异步转码，或把变更投递到 [[kafka]] 做下游处理。

## 客户端接入

### rc 命令行（运维主力）

`rc` 是 RustFS 官方 CLI，定位等同于 `mc`，但命令组是**名词优先**的。

```bash
# 安装（macOS 走 Homebrew，Linux 走 release 包）
brew install rustfs/tap/rc
# curl -fLO https://github.com/rustfs/cli/releases/download/v0.1.30/rustfs-cli-linux-amd64-v0.1.30.tar.gz
# tar -xzf rustfs-cli-linux-amd64-v0.1.30.tar.gz && sudo install -m 0755 rc /usr/local/bin/rc

rc --version
```

```bash
# 1. 注册别名（之后用 local 指代该集群）
rc alias set local http://localhost:9000 AKIAEXAMPLEKEY1234 CHANGE_ME_STRONG_SECRET
rc alias list                       # 不打印 secret

# 2. 健康检查
rc ping local                       # 服务是否存活
rc ready local                      # 依赖是否就绪

# 3. 集群巡检
rc admin info cluster local         # 状态、服务器、磁盘、容量、EC 布局
rc admin pool list local            # 存储池列表

# 4. 桶与对象
rc bucket list local/
rc bucket create local/my-bucket
rc object list local/my-bucket
rc object stat local/my-bucket/hello.txt
rc object copy ./hello.txt local/my-bucket/hello.txt
rc cp local/my-bucket/big.zip /tmp/

# 5. 生命周期与分层
rc bucket lifecycle rule list local/my-bucket
rc bucket lifecycle tier list local
rc bucket lifecycle restore local/my-bucket/archive.tar --days 7
```

> `rc ilm` 作为兼容别名仍可用，新脚本请用 `rc bucket lifecycle`。任何层级加 `--help` 都能看到该版本真实支持的子命令——**不要凭记忆写命令**。

### Java SDK（Spring Boot 集成）

RustFS **不提供**自有 Java SDK，直接使用 AWS SDK for Java v2 指过来即可。

```xml
<dependency>
  <groupId>software.amazon.awssdk</groupId>
  <artifactId>s3</artifactId>
  <version>2.25.27</version>
</dependency>
```

配置类（关键是 `endpointOverride` + `forcePathStyle(true)` + `us-east-1`）：

```java
@Configuration
public class RustfsConfig {

    @Bean
    public S3Client s3Client(
            @Value("${rustfs.endpoint}") String endpoint,
            @Value("${rustfs.access-key}") String accessKey,
            @Value("${rustfs.secret-key}") String secretKey) {
        return S3Client.builder()
                // 明文 HTTP 场景必须写 http://，SDK 默认走 HTTPS 会卡住不返回
                .endpointOverride(URI.create(endpoint))
                .region(Region.US_EAST_1)
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(accessKey, secretKey)))
                // RustFS 默认 path-style；虚拟主机风格需配置 RUSTFS_SERVER_DOMAINS
                .forcePathStyle(true)
                .build();
    }

    /** 预签名器必须同样开启 path-style，否则签名与请求路径不匹配 */
    @Bean
    public S3Presigner s3Presigner(
            @Value("${rustfs.endpoint}") String endpoint,
            @Value("${rustfs.access-key}") String accessKey,
            @Value("${rustfs.secret-key}") String secretKey) {
        return S3Presigner.builder()
                .endpointOverride(URI.create(endpoint))
                .region(Region.US_EAST_1)
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(accessKey, secretKey)))
                .serviceConfiguration(
                        S3Configuration.builder().pathStyleAccessEnabled(true).build())
                .build();
    }
}
```

上传与预签名下载：

```java
@Service
public class StorageService {

    private final S3Client s3;
    private final S3Presigner presigner;

    public StorageService(S3Client s3, S3Presigner presigner) {
        this.s3 = s3;
        this.presigner = presigner;
    }

    /** 上传本地文件；Content-Type 不传时对象下载会被浏览器当二进制处理 */
    public void upload(String bucket, String key, Path file, String contentType) {
        s3.putObject(
                PutObjectRequest.builder()
                        .bucket(bucket).key(key)
                        .contentType(contentType)
                        .metadata(Map.of("project-id", "10086"))   // 自动加 x-amz-meta- 前缀
                        .build(),
                file);
    }

    /** 前端直传：生成 PUT 预签名地址，文件不经过应用服务器 */
    public String presignedUploadUrl(String bucket, String key, Duration ttl) {
        return presigner.presignPutObject(
                PutObjectPresignRequest.builder()
                        .putObjectRequest(r -> r.bucket(bucket).key(key))
                        .signatureDuration(ttl)      // 建议分钟级
                        .build())
                .url().toString();
    }
}
```

配置示例：

```yaml
rustfs:
  endpoint: http://127.0.0.1:9000
  access-key: ${RUSTFS_ACCESS_KEY}
  secret-key: ${RUSTFS_SECRET_KEY}
```

### 其他语言

官方文档给出 Go、Python（`boto3`）、JavaScript/TypeScript、Rust、以及 `aws-cli` / `rclone` / `s3cmd` / Terraform 的接入示例。Python 侧就是标准 boto3，把 `endpoint_url` 指到 `9000` 即可：

```python
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:9000",
    aws_access_key_id="AKIAEXAMPLEKEY1234",
    aws_secret_access_key="CHANGE_ME_STRONG_SECRET",
    region_name="us-east-1",
)

s3.create_bucket(Bucket="images")
s3.upload_file("logo.png", "images", "2026/logo.png")
print(s3.list_objects_v2(Bucket="images")["KeyCount"])
```

## 从 MinIO 迁移

RustFS 把迁移拆成三个层次，按数据量选择：

| 层次 | 手段 | 特点 |
|------|------|------|
| 配置 | `MINIO_*` 变量自动映射 | 改造成本接近零 |
| 数据 | `rc` 复制 / `rclone` / `mc mirror` 到新端点 | 一次性全量，可控 |
| 数据（懒加载） | 桶级别**按需拉取** | 先切流量，读未命中时回源并落地 |

### 配置变量映射

启动时 RustFS 会把一份**白名单**内的 `MINIO_*` 映射为 `RUSTFS_*`：

- 只设 `MINIO_*` → 生效并打印 deprecation 警告
- 两者都设且值不同 → `RUSTFS_*` 胜出，并记录冲突

覆盖的常见后缀：`ACCESS_KEY`、`SECRET_KEY`、`ROOT_USER`、`ROOT_PASSWORD`、`ADDRESS`、`CONSOLE_ADDRESS`、`VOLUMES`、`REGION`、`ERASURE_SET_DRIVE_COUNT`、`STORAGE_CLASS_STANDARD`、`STORAGE_CLASS_RRS`、`SCANNER_*`、`IDENTITY_OPENID_*`、`NOTIFY_WEBHOOK_*`、`AUDIT_WEBHOOK_*` 等。

已废弃别名：`RUSTFS_ROOT_USER` → `RUSTFS_ACCESS_KEY`，`RUSTFS_ROOT_PASSWORD` → `RUSTFS_SECRET_KEY`。

> 迁移时直接复用旧 compose 文件通常能起来，但请逐个核对未被映射的变量（例如 `MINIO_DOMAIN` 对应的是 `RUSTFS_SERVER_DOMAINS`），别指望"跑起来 = 行为一致"。

### 按需拉取（on-demand migration）

适合"数据量大、不能停机、绝大多数历史对象很少访问"的场景。语义是**入向拉取**：

```text
客户端 GET 未命中的 key
  → RustFS 去源端读（S3 / S3 兼容 / MinIO / RustFS / R2 / GCS / Azure Blob）
  → 返回给客户端，同时落到本地桶
  → 之后同一个 key 由本地服务
```

操作流程（Console → 桶 → Settings → Automation → On-demand migration）：

1. 建一个**空**的本地桶（不要拿复制目标桶当源，会成环）
2. 填 Provider / Endpoint / Region / Source Bucket / 读写凭据（源端务必用**只读** token）
3. **Test connection** 通过后 Enable migration
4. 用 `rc cp` 读一个未命中对象验证拉取，或 **Start backfill** 按前缀批量回填（先开 **Dry run** 核对清单再关掉）

```bash
# 注意：指向本地 RustFS，不是源端
rc alias set rustfs http://localhost:9000 AKIAEXAMPLEKEY1234 CHANGE_ME_STRONG_SECRET \
  --region us-east-1 --bucket-lookup path

rc cp rustfs/migration/artifacts/nightly/pkg.deb /tmp/
```

**边界必须清楚**：

- 不是持续复制。对象落地后，源端的后续改动**不会**同步过来；本地 `PUT` 也**不回写**源端
- RustFS **不会**在源端执行写/删除
- 本地开启了版本控制时，一个 delete marker 可能把源端 key「遮住」

需要双向或持续同步，请用**桶复制**或**站点复制**，而不是按需拉取。

## 运维与可观测性

### 巡检

```bash
rc ping local                 # 存活
rc ready local                # 就绪
rc admin info cluster local   # 网络布局、EC parity、磁盘可用性、池成员
rc admin pool list local      # 多池场景
```

Console 的 **Status** 页面提供同一份信息，排障时优先看它——比一堆变量推导更快。

### 指标与日志

RustFS 通过 **OTLP/HTTP** 导出 traces / metrics / logs，仓库自带的 `docker-compose.yml` 已包含 `otel-collector`、`prometheus`、`grafana`、`jaeger`：

```bash
git clone https://github.com/rustfs/rustfs.git
docker compose --profile observability up -d        # 全套可观测栈
docker compose -f docker-compose.yml up -d rustfs   # 只要 RustFS
```

```bash
# 只接 OTel Collector
RUSTFS_OBS_ENDPOINT=http://otel-collector:4318
RUSTFS_OBS_SERVICE_NAME=rustfs-prod
RUSTFS_OBS_ENVIRONMENT=production
```

指标采集间隔按作用域配置，形如 `RUSTFS_METRICS_<SCOPE>_INTERVAL_SEC`（scope：`DEFAULT` / `SYSTEM` / `CLUSTER` / `BUCKET` / `NODE` / `RESOURCE` / `AUDIT` / `NOTIFICATION`）：

```bash
RUSTFS_METRICS_CLUSTER_INTERVAL_SEC=60
```

需要重点关注的信号：**离线盘数量**、**可用容量百分比**、**heal 队列长度与耗时**、**S3 5xx 比例**、**TTFB P99**。具体指标名以 `rc admin info` 输出与 Console 指标页为准，不要照搬 MinIO 的 `minio_*` 指标名——两者不通用。

### 换盘与自愈

```bash
# 1. 停服务并卸载故障盘（umount 报 busy 就先停 rustfs）
sudo systemctl stop rustfs
sudo umount /data/rustfs0

# 2. 新盘按原规格格式化（容量不小于旧盘，保持 XFS）
sudo mkfs.xfs -f -i size=512 -n ftype=1 -L RUSTFS0 /dev/sdb

# 3. 按 UUID 挂回原路径（必须与原 RUSTFS_VOLUMES 中的路径一致）
sudo blkid -s UUID -o value /dev/sdb
sudo mount -a && findmnt /data/rustfs0

# 4. 启动后观察自愈
sudo systemctl start rustfs
journalctl -u rustfs -f
tail -f /var/log/rustfs/rustfs.log
```

RustFS 发现已知挂载点上是新格式化盘时，会自动把缺失分片重建上去。自愈读写放大会同时抬高盘和网络的负载，**在多盘同时失效时请安排维护窗口**，不要让重建和业务高峰抢资源。

### 扩容

| 方式 | 说明 |
|------|------|
| 池内加盘 | 需保持 Set 宽度对称，且不破坏既有分区规则 |
| 新增存储池 | 推荐方式；新对象按剩余容量比例写入新池，旧数据不自动搬迁 |
| 再平衡（rebalance） | 主动把数据迁移到新池，属于重 IO 操作，需窗口执行 |
| 退役池（decommission） | 把整个池的数据迁走后再下线 |

## 选型建议

| 方案 | 优势 | 劣势 | 适用 |
|------|------|------|------|
| **RustFS** | Apache 2.0、Rust 内存安全与低占用、与 MinIO 迁移友好、原生 OTLP | 项目较新，S3 兼容为子集（无 ACL），社区案例少 | 想替换 MinIO 又介意 AGPL、团队愿意承担新项目风险 |
| **MinIO** | 生态成熟、文档与案例多、工具链完整 | AGPL-3.0，社区版功能有裁剪 | 需要稳定与可预期行为的生产系统 |
| **Ceph RGW** | 块/文件/对象三合一，超大规模 | 运维复杂度高 | 大型私有云、同时需要块存储 |
| **公有云 S3 / OSS / COS** | 免运维、弹性、生态最全 | 长期成本高、数据出境与合规问题 | 数据量波动大、不想养存储团队 |

**判断口径**：如果把对象存储当"基础设施底座"，稳定性权重最高，成熟方案优先；如果把它当"可替换的 S3 实现"，且团队有能力读源码、跟进 issue，RustFS 的许可证与资源占用优势才成立。任何"性能是 MinIO 的 N 倍"的说法都应该在自己的硬件和对象尺寸分布上复测后再采信。

> 需要随机写、追加写或 POSIX 挂载的场景，对象存储都不合适，应选 CephFS / RBD——这一点与 MinIO 完全一致，见 [[minio#方案对比]]。

## 常见排错

| 现象 / 报错 | 原因 | 解决 |
|-------------|------|------|
| `403 Forbidden` / `SignatureDoesNotMatch` | AK/SK 错误；或节点时间漂移；或反向代理改了 Host | 核对凭据；配 NTP（偏差 < 15 分钟）；代理保留原始 Host，必要时设 `RUSTFS_SERVER_DOMAINS` |
| Access Key 无法通过签名校验 | 用了含 `/` 的 Base64 作为 Access Key | 改用**大写字母数字**，Secret 才用 Base64 |
| `301 Moved Permanently` | 客户端未开 path-style，或 region 不匹配 | `.forcePathStyle(true)` + region `us-east-1` |
| 上传卡住无响应 | SDK 默认 HTTPS，服务端是明文 HTTP | `endpointOverride` 明确写 `http://`；或给 RustFS 配 `RUSTFS_TLS_PATH` |
| `Connection refused` | 服务未启动 / 端口未放行 / 只监听了 `:9000` 之外的地址 | `systemctl status rustfs`；检查 `RUSTFS_ADDRESS` 与防火墙 |
| 启动失败，提示存储类非法 | 显式 `EC:n` 违反 `M <= N/2`，或对某个窄池不成立 | 删掉 `RUSTFS_STORAGE_CLASS_STANDARD` 回到自动 parity，或选所有池都满足的值 |
| 绑定挂载目录报 permission denied | 容器以 uid `10001` 运行 | `sudo chown -R 10001:10001 /path` |
| 多节点 RPC 认证失败 | 使用默认凭据且未设 `RUSTFS_RPC_SECRET` | 显式设置相同的 `RUSTFS_RPC_SECRET` 于所有节点 |
| 虚拟主机风格访问 404 | 未配置域名 | 设 `RUSTFS_SERVER_DOMAINS=s3.example.com` 并配泛解析 |
| Console 打不开 | `RUSTFS_CONSOLE_ENABLE=false` 或端口未映射 | 开启并映射 `9001` |
| 加密对象换实现后读不出 | 加密格式不跨实现可移植 | 跨系统迁移前先解密，或改用应用层加密 |
| 小文件占空间远超预期 | 元数据开销 + 128 KiB 以下内联 + 版本历史 | 开生命周期清理旧版本；小文件考虑打包 |
| 未完成分片占满容量 | 分片上传未 Complete/Abort | 配桶生命周期规则定期 abort |

## 最佳实践清单

- [ ] 立即替换默认凭据 `rustfsadmin`，Access Key 用大写字母数字
- [ ] 生产用 MNMD（4+ 节点 × 每节点多盘），别停在安装脚本给的 SNSD
- [ ] 所有 Drive 同型号同容量，XFS + `noatime`，按 UUID 挂载
- [ ] 保持 `RUSTFS_STORAGE_CLASS_STANDARD` 留空，让 RustFS 按 Set 宽度自动定 parity
- [ ] 容量规划按 `(N-M)/N` 算完再打 8 折，并预留 heal 期间的额外读带宽
- [ ] 开启 TLS（`RUSTFS_TLS_PATH`），对外只暴露必要端口
- [ ] 配置 NTP；多节点显式设置 `RUSTFS_RPC_SECRET`
- [ ] 接 OTLP → Prometheus，重点告警离线盘与可用容量
- [ ] 大文件走分片上传，前端直传一律用预签名 URL
- [ ] 开版本控制 + 生命周期，控制容量增长与未完成分片
- [ ] 迁移前用 `Dry run` 核对清单，迁移后用 `rc object stat` 抽样比对 ETag/大小
- [ ] 演练一次换盘流程，确认自愈能跑完

## 相关笔记

- [[middleware/index|中间件索引]]
- [[minio|MinIO]]：同为 S3 兼容对象存储，纠删码原理与多副本对比的详细推导在那边
- [[docker|Docker]] / [[docker-compose|Docker Compose]]：容器化部署
- [[kubernetes|Kubernetes]] / [[helm|Helm]]：MNMD 集群与 Operator 部署
- [[nginx|Nginx]]：反向代理与虚拟主机风格寻址
- [[linux|Linux]]：磁盘分区、XFS、systemd
- [[kafka|Kafka]]：作为事件通知的下游

## 参考

- [RustFS 官网](https://rustfs.com)
- [RustFS GitHub](https://github.com/rustfs/rustfs)
- [RustFS 官方文档](https://docs.rustfs.com/)
- [Docker 部署](https://docs.rustfs.com/en/installation/container/docker)
- [纠删码配置（EC Configuration）](https://docs.rustfs.com/en/installation/requirement/ec-configuration)
- [环境变量参考](https://docs.rustfs.com/en/reference/environment-variables)
- [rc CLI](https://docs.rustfs.com/en/operations/rc)
- [S3 兼容性矩阵](https://docs.rustfs.com/en/reference/s3-compatibility)
- [按需迁移](https://docs.rustfs.com/en/administration/data/bucket/on-demand-migration)
- [RustFS CLI 仓库](https://github.com/rustfs/cli)
