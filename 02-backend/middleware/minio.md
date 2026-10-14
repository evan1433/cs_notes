---
title: MinIO
description: MinIO 对象存储核心原理、纠删码架构、部署运维与 SDK 实战指南
tags:
  - middleware
  - minio
  - object-storage
  - s3
  - distributed-system
date: 2026-09-07
---

# MinIO

## 概述

MinIO 是一个用 Go 编写的高性能**对象存储**系统，完全兼容 Amazon S3 API。它以「一个二进制文件 + 一堆裸盘」的方式提供 PB 级存储能力，常用于：

| 场景 | 说明 |
|------|------|
| 私有云对象存储 | 替代公有云 S3，数据不出内网 |
| AI/ML 数据湖 | 存放训练样本、模型权重、数据集版本 |
| 大数据存储层 | 作为 Spark / Flink / Trino 的底层存储（S3A 协议） |
| 备份归档 | 结合生命周期规则做冷热分层 |
| 应用静态资源 | 图片、视频、日志归档 |

核心特征：

- **S3 兼容**：AWS Signature v2/v4 签名，SDK、CLI、Terraform 等生态可直接复用
- **纠删码保护**：无 RAID、无副本冗余，靠 Reed-Solomon 编码实现高可用
- **强一致**：read-after-write、list-after-write 语义
- **轻量**：单二进制部署，无外部依赖（不依赖 ZooKeeper / etcd 等元数据服务）

## 核心概念与术语

先用一张表把 S3 概念、MinIO 内部术语、物理实体对上：

| 层级 | S3 / 用户视角 | MinIO 内部术语 | 物理实体 |
|------|--------------|----------------|----------|
| 集群 | — | **Tenant / Deployment** | 一组 MinIO 节点 |
| 分组 | — | **Server Pool**（服务器池） | 一组同构节点，可横向扩容 |
| 分片组 | — | **Erasure Set**（纠删集） | 一组 Drive，通常 4~16 块 |
| 设备 | — | **Drive** | 一块磁盘或一个目录 |
| 命名空间 | **Bucket** | Volume | 每个 Drive 上的一级目录 |
| 数据 | **Object** | Object | 一个目录 + `xl.meta` 元数据文件 |
| 描述信息 | **Metadata** | `xl.meta` | 元数据 + 校验和 |

关键术语解释：

- **Drive**：MinIO 的最小存储单元，可以是一块裸盘、一个挂载点、甚至只是一个目录。同一个集群内所有 Drive 的容量应尽量一致（木桶效应）。
- **Erasure Set**：纠删码的作用域。MinIO 会按固定算法把集群内所有 Drive 划分成若干纠删集，一个对象只写入**一个**纠删集，不会跨集分布。
- **Server Pool**：扩容单位。新增一个 Pool 即可扩容，新对象按各 Pool 剩余容量比例写入；Pool 内部仍做纠删码保护。
- **Tenant**：一个逻辑上独立的 MinIO 集群（在 Kubernetes Operator 语境下常用）。

## 存储架构

### 逻辑分层

```text
                    ┌─────────────────────────────────────┐
   S3 API 请求 ───▶  │        MinIO Server (Go)            │
                    │  ┌───────────────────────────────┐  │
                    │  │  1. 认证 (IAM / STS / Policy)  │  │
                    │  │  2. 路由：Bucket → Erasure Set │  │
                    │  │  3. 纠删码编码 / 解码          │  │
                    │  │  4. 位衰减校验 (HighwayHash)   │  │
                    │  └───────────────────────────────┘  │
                    └───────────────┬─────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        Server Pool 0         Server Pool 1            ...
      ┌──────────────┐
      │ Erasure Set  │  ← 对象写入的最小分布单元
      │  drive0..15  │
      └──────────────┘
```

### 对象在磁盘上的布局

对象在 MinIO 中**不是**一个普通文件。写入 `mybucket/photos/a.jpg` 后，每个相关 Drive 上会出现：

```text
/data/drive0/
└── mybucket/
    └── photos/
        └── a.jpg/              # 注意：对象名是一个「目录」
            └── xl.meta         # 元数据 + 数据分片（inline）或分片引用
```

- **`xl.meta`**：二进制（msgpack 编码）元数据文件，包含对象版本、大小、ETag、用户元数据、
  每个数据/校验分片的 HighwayHash 校验和、加密信息等。
  早期版本叫 `xl.json`，`RELEASE.2021-06` 之后改为 `xl.meta`。
- **小对象内联**：小于一定阈值（默认 128KiB）的对象，数据会直接内联进 `xl.meta`，减少一次 IO，显著提升小文件性能。
- **大对象**：数据分片直接写在 `a.jpg/` 目录下，元数据只记录索引和校验和。

> **运维提示**：因此不能用 `cp` / `rsync` 手工往数据目录里塞文件，MinIO 不认；迁移数据必须用 `mc mirror` 或 S3 API。

## 读写流程

### 写流程（PUT Object）

1. **认证与鉴权**：校验 Access Key 签名，匹配 Bucket / Prefix 上的 IAM Policy。
2. **定位纠删集**：对 Bucket + ObjectName 做确定性哈希，选出一个 Erasure Set（保证同一对象每次落在同一位置）。
3. **获取分布式锁**：同一对象的并发写通过 Quorum 写锁串行化，保证强一致。
4. **纠删码编码**：按对象大小分片，切成 `K` 个数据块，再算出 `M` 个校验块。
5. **并行落盘**：`K + M` 个分片并发写入纠删集内的不同 Drive，同时计算每片的 HighwayHash。
6. **Quorum 确认**：收到足够数量（见下节）的成功响应即返回成功，不满足则整体失败并清理残留。

### 读流程（GET Object）

1. 定位纠删集，读取各 Drive 上的 `xl.meta`。
2. 校验 HighwayHash，检测**位衰减（Bitrot）**；损坏的分片被标记为不可用。
3. 若数据分片齐全，直接流式返回；若有分片缺失/损坏，用任意 `K` 个可用分片**解码重建**。
4. 解码发生在内存中，对客户端透明。

> 因为需要至少 `K` 个分片才能重建，读放大和修复流量是纠删码方案的主要代价：一块盘挂掉后，重建需要读取 `K` 块盘的数据量。

## 纠删码与数据保护

### Reed-Solomon 原理

MinIO 使用 **Reed-Solomon** 编码：把对象切成 `K` 个数据块，编码出 `M` 个校验块，共 `K + M` 块分散到不同 Drive。

```text
对象 (10 MB)
  │
  ├─ 分片 →  D1 ┐
  │            D2 ├─ K=4 个数据块
  │            D3 │
  │            D4 ┘
  │
  └─ 编码 →  P1 ┐
               P2 ├─ M=4 个校验块（可容忍任意 4 块盘失效）
               P3 │
               P4 ┘
```

- 丢失任意 ≤ `M` 块，都能用剩余任意 `K` 块恢复原始数据。
- 空间利用率 = `K / (K + M)`。K=M=4 时利用率为 **50%**，与两副本相同，但可靠性远高于两副本。
- MinIO 默认配置 `EC:4`（`MINIO_STORAGE_CLASS_STANDARD`），校验块数不超过纠删集 Drive 总数的一半。

存储类环境变量：

```bash
# 标准存储：默认 EC:4（纠删集内一半数据、一半校验）
export MINIO_STORAGE_CLASS_STANDARD="EC:4"
# 低冗余存储（RRS）：适合可再生成的数据，默认 EC:2
export MINIO_STORAGE_CLASS_RRS="EC:2"
```

### 与多副本方案对比

| 维度 | 三副本 | MinIO 纠删码 (K=8,M=8) |
|------|--------|------------------------|
| 空间利用率 | 33% | 50% |
| 可容忍失效盘数 | 2（有上限，且 3 副本全坏即丢） | 8 |
| 重建读流量 | 1 份 | 8 份（读放大） |
| 任意 N 块盘同时坏的概率 | 高 | 低（组合数更多） |
| 适用场景 | 小集群、低延迟敏感 | 大容量、冷数据、归档 |

### Quorum（法定数量）

- **写 Quorum**：需要至少 `K` 个 Drive 写入成功；当 `K == M` 时，MinIO 要求 `K + 1`，用于避免脑裂（split-brain）场景下新旧数据不可区分。
- **读 Quorum**：需要 `K` 个可用分片才能重建；若可用分片 < `K`，对象不可读。

### 位衰减防护（Bitrot Protection）

磁盘会因为磁介质老化、宇宙射线、固件 bug 等原因出现**静默数据损坏**——数据还在，但比特翻转了，传统 RAID 无法发现。

MinIO 的做法：

1. 写入时按分片计算 **HighwayHash-256** 校验和，存入 `xl.meta`。
2. 读取时重新计算并比对，不匹配则判定该分片损坏。
3. 损坏分片自动从其他分片重建（Healing），并用正确数据回写修复。

```bash
# 手工触发一次修复扫描（正常情况 MinIO 会后台自动修复）
mc admin heal -r myminio/mybucket
```

### 一致性保证

MinIO 是**强一致**的，而非最终一致：

- `PUT` 成功后的 `GET` 一定能读到新数据（read-after-write）
- 写入后的 `ListObjects` 一定能列出该对象（list-after-write）
- `DELETE` 成功后立即不可见

实现手段：Quorum 写 + 分布式锁 + 版本号。

## 部署实践

### 单机模式（Docker）

```bash
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=ChangeMe123456" \
  -v /data/minio:/data \
  -v /data/minio-config:/root/.minio \
  minio/minio:latest server /data --console-address ":9001"
```

- `9000`：S3 API 端口
- `9001`：Web 控制台端口（新版必须显式指定，否则随机端口）

> 单机单盘不启用纠删码（相当于直接写文件系统），仅用于开发测试。生产环境至少 4 块盘。

### 分布式模式（Docker Compose）

4 节点 × 每节点 2 块盘 = 8 块 Drive 的示例：

```yaml
# docker-compose.yml
version: "3.8"

services:
  minio1:
    image: minio/minio:latest
    hostname: minio1
    command: server --console-address ":9001" http://minio{1...4}/data{1...2}
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: ChangeMe123456
    volumes:
      - ./data/minio1-1:/data1
      - ./data/minio1-2:/data2
    networks: [minio-net]

  # minio2 / minio3 / minio4 结构完全一致，仅 volumes 路径不同

networks:
  minio-net:
    driver: bridge
```

`http://minio{1...4}/data{1...2}` 是 MinIO 的**展开语法（ellipsis notation）**，等价于：

```text
http://minio1/data1 http://minio1/data2
http://minio2/data1 http://minio2/data2
http://minio3/data1 http://minio3/data2
http://minio4/data1 http://minio4/data2
```

部署约束：

- 所有节点的 Drive 数量、容量必须一致
- 节点间需要低延迟网络（同城/同机房，跨 WAN 用**站点复制**而非一个集群）
- 使用连续的主机名（支持 `{1...N}` 展开）
- 时间同步（NTP）必须配置，签名校验依赖时间戳

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `MINIO_ROOT_USER` | 根用户 Access Key（≥ 3 字符） |
| `MINIO_ROOT_PASSWORD` | 根用户 Secret Key（≥ 8 字符） |
| `MINIO_STORAGE_CLASS_STANDARD` | 标准存储类的 EC 配置，如 `EC:4` |
| `MINIO_STORAGE_CLASS_RRS` | 低冗余存储类配置 |
| `MINIO_DOMAIN` | 启用虚拟主机风格（path-style → virtual-hosted-style）寻址 |
| `MINIO_PROMETHEUS_AUTH_TYPE` | 监控端点认证方式，`public` 或 `jwt` |
| `MINIO_SERVER_URL` | 对外暴露的 API 地址（反向代理场景必配） |

> 配合 [[nginx]] 做反向代理或负载均衡时，务必设置 `MINIO_SERVER_URL`，否则预签名 URL 的签名校验会失败。

## 客户端与 SDK 实战

### mc 命令行

`mc`（MinIO Client）是运维主力工具：

```bash
# 1. 注册别名（之后所有命令用 myminio 指代该集群）
mc alias set myminio http://127.0.0.1:9000 admin ChangeMe123456

# 2. 桶操作
mc mb myminio/images              # 创建桶
mc ls myminio                     # 列出桶
mc rb --force myminio/old-bucket  # 强制删除非空桶

# 3. 对象操作
mc cp report.pdf myminio/docs/2026/report.pdf
mc cp --recursive ./dist myminio/web/
mc mirror --overwrite ./backup myminio/backup   # 增量同步（类似 rsync）
mc stat myminio/images/logo.png                 # 查看对象元数据
mc cat myminio/docs/summary.txt                 # 直接输出内容

# 4. 匿名访问策略
mc anonymous set download myminio/images        # 公开只读
mc anonymous set none myminio/images            # 取消公开

# 5. 集群运维
mc admin info myminio                           # 集群健康与容量
mc admin heal -r myminio                        # 修复扫描
mc admin prometheus generate myminio            # 生成 Prometheus 抓取配置
mc admin config get myminio                     # 查看运行时配置
```

### Java SDK（Spring Boot 集成）

Maven 依赖：

```xml
<dependency>
    <groupId>io.minio</groupId>
    <artifactId>minio</artifactId>
    <version>8.5.17</version>
</dependency>
```

配置类：

```java
@Configuration
public class MinioConfig {

    @Bean
    public MinioClient minioClient(
            @Value("${minio.endpoint}") String endpoint,
            @Value("${minio.access-key}") String accessKey,
            @Value("${minio.secret-key}") String secretKey) {
        return MinioClient.builder()
                .endpoint(endpoint)
                .credentials(accessKey, secretKey)
                // 直连场景可用 HTTP；生产建议走 TLS
                .build();
    }
}
```

服务层（上传、预签名下载、删除、检查存在）：

```java
@Service
public class StorageService {

    private final MinioClient minioClient;

    public StorageService(MinioClient minioClient) {
        this.minioClient = minioClient;
    }

    /** 上传文件，同时写入业务自定义元数据 */
    public String upload(String bucket, String objectName,
                         InputStream stream, String contentType,
                         Map<String, String> metadata) throws Exception {
        // 桶不存在时自动创建，避免启动顺序问题
        boolean found = minioClient.bucketExists(
                BucketExistsArgs.builder().bucket(bucket).build());
        if (!found) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
        }

        minioClient.putObject(
                PutObjectArgs.builder()
                        .bucket(bucket)
                        .object(objectName)
                        .stream(stream, stream.available(), 5 * 1024 * 1024)  // partSize 5MiB
                        .contentType(contentType)
                        // 自定义元数据：SDK 会自动加 x-amz-meta- 前缀
                        .userMetadata(metadata)
                        .build());
        return objectName;
    }

    /** 生成临时下载链接，避免把 AK/SK 暴露给前端 */
    public String presignedUrl(String bucket, String objectName, int expirySeconds)
            throws Exception {
        return minioClient.getPresignedObjectUrl(
                GetPresignedObjectUrlArgs.builder()
                        .method(Method.GET)
                        .bucket(bucket)
                        .object(objectName)
                        .expiry(expirySeconds)   // 最大 7 天（604800 秒）
                        .build());
    }

    /** 前端直传：生成 PUT 预签名地址，文件不经过应用服务器 */
    public String presignedUploadUrl(String bucket, String objectName) throws Exception {
        return minioClient.getPresignedObjectUrl(
                GetPresignedObjectUrlArgs.builder()
                        .method(Method.PUT)
                        .bucket(bucket)
                        .object(objectName)
                        .expiry(3600)
                        .build());
    }

    public void remove(String bucket, String objectName) throws Exception {
        minioClient.removeObject(
                RemoveObjectArgs.builder()
                        .bucket(bucket).object(objectName).build());
    }
}
```

> **性能要点**：`stream(...)` 的第 3 个参数 `partSize` 决定分片大小，最小 5MiB；未知大小时传 `-1`，SDK 会按 5MiB 分片并使用 multipart 上传。

### Python SDK

```python
from minio import Minio
from minio.error import S3Error
from datetime import timedelta

client = Minio(
    "127.0.0.1:9000",
    access_key="admin",
    secret_key="ChangeMe123456",
    secure=False,          # 生产环境为 True（HTTPS）
)

def upload_file(bucket: str, object_name: str, file_path: str) -> str:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    result = client.fput_object(
        bucket, object_name, file_path,
        content_type="application/octet-stream",
        metadata={"project-id": "10086", "owner": "alice"},
    )
    return result.etag

def presigned_download(bucket: str, object_name: str) -> str:
    return client.presigned_get_object(
        bucket, object_name, expires=timedelta(hours=1)
    )

if __name__ == "__main__":
    try:
        print(upload_file("images", "2026/logo.png", "./logo.png"))
        print(presigned_download("images", "2026/logo.png"))
    except S3Error as exc:
        print("MinIO error:", exc.code, exc.message)
```

## 元数据概述

在 MinIO（以及整个对象存储系统，如 Amazon S3）中，**文件的元数据（Metadata）** 指的是描述文件（对象）属性的键值对信息，类似于文件系统中文件的"属性"，但比传统文件系统的元数据更灵活和可扩展。

### 元数据的分类

MinIO 中的元数据主要分为两类：

#### 1. 系统元数据（System Metadata）

由 MinIO 自动生成和管理，用于描述对象的基础属性，用户无法直接修改，例如：

- `Content-Length`：对象的大小（字节数）
- `Content-Type`：对象的 MIME 类型（如 `image/jpeg`、`application/json`）
- `ETag`：对象内容的哈希值（用于验证文件完整性）
- `Last-Modified`：对象最后修改的时间戳
- `X-Amz-Storage-Class`：存储类别（如标准存储、低频访问存储）

> **注意**：MinIO 中大于分片阈值的对象，其 `ETag` **不是**完整的 MD5（格式类似 `abc...-3`，后缀为分片数量）。因此不能用本地 MD5 与之直接比对做秒传校验。

#### 2. 用户自定义元数据（User-Defined Metadata）

由用户在上传或更新对象时手动添加的键值对，用于自定义描述对象的业务属性，例如：

- `X-Amz-Meta-Author`：文件的作者
- `X-Amz-Meta-Category`：文件的分类（如"文档""图片"）
- `X-Amz-Meta-Expire-Date`：文件的过期日期
- `X-Amz-Meta-Project-Id`：关联的业务项目 ID

> 自定义元数据的键名需以 `X-Amz-Meta-` 为前缀（遵循 S3 协议规范），值可以是任意字符串。HTTP 头只能传 ASCII，中文或二进制值需先做 URL 编码或 Base64。

### 元数据的作用

#### 1. 描述对象属性，辅助管理

元数据提供了对象的核心信息（如大小、类型、修改时间），帮助用户快速了解对象的基本特征，无需读取文件内容即可判断是否为目标文件。

#### 2. 支持业务逻辑扩展

自定义元数据可嵌入业务信息（如用户 ID、权限标识、分类标签），让对象存储与业务系统深度结合。例如：

- 存储图片时，用元数据记录拍摄设备、分辨率等信息
- 存储文档时，用元数据记录审批状态、版本号等

#### 3. 优化查询与筛选

结合 MinIO 的查询功能（如基于元数据的对象筛选），可快速定位符合条件的文件。

> **重要限制**：对象存储的元数据**不可作为查询索引**。`ListObjects` 只按字典序遍历 key，
> 无法按元数据过滤。真正的元数据检索需要额外维护索引（把元数据写入 [[redis]]、
> Elasticsearch 或关系库），或用 Spark/Trino 做全量扫描分析。

#### 4. 保障数据完整性与安全性

系统元数据（如 `ETag`）可用于校验文件传输或存储过程中是否损坏；通过自定义元数据可附加权限标识，辅助业务层实现访问控制。

#### 5. 支持生命周期管理

结合元数据（如过期时间），可配置 MinIO 的生命周期规则，自动删除过期文件或迁移到低成本存储类别。

### 元数据使用示例

```bash
# 上传文件并添加元数据
mc cp local-file.txt myminio/mybucket/remote-file.txt \
  --attr "X-Amz-Meta-Author=alice,X-Amz-Meta-Category=report"

# 查看对象的元数据（含系统元数据与自定义元数据）
mc stat myminio/mybucket/remote-file.txt
```

### 总结

元数据是 MinIO 中描述对象特征的关键信息，既包含系统自动维护的基础属性，也支持用户自定义业务属性。它的核心作用是**增强对象的可管理性、可查询性，并桥接对象存储与业务逻辑**，是构建灵活、高效的对象存储应用的重要工具。

## 高级特性

### 分片上传（Multipart Upload）

大文件（建议 > 100MB）必须走分片上传，好处是支持断点续传、并发加速、失败只重试单个分片。

```text
1. InitiateMultipartUpload  → 获得 UploadId
2. UploadPart (可并发，带 PartNumber 1~10000)
3. CompleteMultipartUpload  → 服务端按序号拼装
```

约束：

| 项 | 限制 |
|----|------|
| 单个对象最大 | 5 TiB |
| 分片大小 | 5 MiB ~ 5 GiB（最后一片可小于 5 MiB） |
| 分片数量 | 最多 10,000 |
| 未完成的分片 | 占用空间，需配置 `mc admin config set` 的 `expiry` 规则清理 |

### 预签名 URL（Presigned URL）

在不暴露 AK/SK 的前提下，把临时读写权限授予第三方。机制是：服务端用 Secret Key 对「HTTP 方法 + 资源路径 + 过期时间」做 HMAC 签名，MinIO 校验签名与时间戳即可放行。

适用场景：前端直传、临时下载链接、第三方系统限时取数。

> 安全建议：有效期尽量短（分钟级）；`PUT` 预签名地址应绑定到确定的 objectName，避免攻击者覆盖他人文件。

### 版本控制（Versioning）

```bash
mc version enable myminio/docs
mc ls --versions myminio/docs    # 查看历史版本
```

- 开启后删除操作写入一个「删除标记（Delete Marker）」，数据仍在，可恢复。
- 结合 `mc retention` 设置**对象锁定（Object Lock）**（合规模式/治理模式），实现 WORM（一次写入多次读取），满足审计合规要求。

### 生命周期管理（Lifecycle）

```bash
# 30 天后删除 tmp/ 前缀下的对象，未完成的碎片 7 天清理
mc ilm rule add myminio/logs \
  --expire-days 30 --prefix "tmp/" \
  --expired-object-delete-marker
```

### 事件通知（Event Notification）

对象变更（PUT / GET / DELETE 等）可推送到：Webhook、Kafka、Redis、AMQP/RabbitMQ、NATS、Elasticsearch、MySQL、PostgreSQL、MQTT。

```bash
mc admin config set myminio notify_webhook:1 \
  endpoint="http://127.0.0.1:8080/minio-hook"

mc event add myminio/images arn:minio:sqs::1:webhook \
  --event put,delete
mc admin service restart myminio
```

典型用法：图片上传后触发异步转码、缩略图生成。

### 复制（Replication）

| 类型 | 说明 |
|------|------|
| **桶复制** | Bucket 级别单向/双向复制，用于跨机房容灾 |
| **站点复制** | 多站点多活，任一站点写入都会同步到其他站点 |
| **批量复制** | `mc replicate` 一次性迁移历史数据 |

## 权限与安全

### IAM 体系

MinIO 内置了一套兼容 S3 IAM 的权限模型：

- **User**：默认只有 root 用户，建议通过 `mc admin user add` 创建子账号
- **Group**：用户组，策略可挂到组上
- **Policy**：JSON 文档，由 `Action + Resource + Condition` 组成
- **STS**：临时凭证，配合 OpenID Connect / LDAP / 自建服务发放短期 AK/SK

内置策略：`consoleAdmin`、`readwrite`、`readonly`、`writeonly`、`diagnostics`。

最小权限示例（只允许读 `images` 桶的 `public/` 前缀）：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::images",
        "arn:aws:s3:::images/public/*"
      ]
    }
  ]
}
```

```bash
mc admin policy create myminio images-readonly policy.json
mc admin user add myminio app-user AppSecret123456
mc admin policy attach myminio images-readonly --user app-user
```

### 加密

| 模式 | 说明 |
|------|------|
| **SSE-S3** | 服务端加密，密钥由 MinIO/KMS 托管 |
| **SSE-KMS** | 密钥由外部 KMS（如 Vault、KES）管理，支持按对象粒度换密钥 |
| **SSE-C** | 客户端提供密钥，服务端不存储密钥 |
| **TLS** | 传输层加密，生产必开 |

```bash
# 启用 SSE-S3 自动加密某个桶
mc encrypt set sse-s3 myminio/secrets
```

## 运维与可观测性

### Prometheus 监控

```bash
# 生成抓取配置
mc admin prometheus generate myminio

# 若未开认证，可直接抓取
curl http://127.0.0.1:9000/minio/v2/metrics/cluster
```

### 关键指标

| 指标 | 含义 | 关注点 |
|------|------|--------|
| `minio_cluster_capacity_usable_free_bytes` | 可用容量 | < 20% 需扩容 |
| `minio_cluster_drive_offline_total` | 离线盘数量 | > 0 立即排查 |
| `minio_cluster_drive_online_total` | 在线盘数量 | 应与总数一致 |
| `minio_s3_requests_total` | 请求量 | 按 API 维度统计 |
| `minio_s3_requests_errors_total` | 错误量 | 4xx/5xx 分类 |
| `minio_s3_ttfb_seconds_distribution` | 首字节延迟 | P99 突刺 |
| `minio_heal_objects_heal_count` | 修复对象数 | 持续增长说明盘有问题 |

### 扩容

1. **纵向扩容**：给每个节点加盘（注意成倍增加，保持纠删集均衡）
2. **横向扩容**：新增一个 Server Pool，要求新 Pool 的**节点数和盘数与已有 Pool 完全一致**
3. 扩容后 MinIO 按各 Pool 剩余可用空间比例写入新对象，旧数据不自动搬迁

### 备份

- 跨集群复制（推荐）
- `mc mirror --watch` 实时增量同步到备集群
- 定期导出 IAM 配置：`mc admin config export myminio`

## 方案对比

| 方案 | 类型 | 优势 | 劣势 | 适用 |
|------|------|------|------|------|
| **MinIO** | 对象存储 | 轻量、S3 兼容、部署极简、性能高 | 不支持 POSIX 挂载、不适合大量小文件随机改写 | 云原生、AI 数据湖、备份归档 |
| **Ceph (RGW/RBD)** | 统一存储 | 块/文件/对象三合一，生态成熟 | 运维复杂度高、组件多 | 大型私有云、需要块存储 |
| **HDFS** | 分布式文件系统 | 大数据生态原生、吞吐高 | 单点 NameNode（需 HA）、不适合小文件 | Hadoop/Spark 数仓 |
| **FastDFS** | 分布式文件系统 | 轻量、小文件友好 | 无纠删码（靠副本）、生态弱、维护放缓 | 中小规模图片/文件服务 |
| **NFS / NAS** | 网络文件系统 | POSIX 兼容、改造成本低 | 扩展性差、单点风险 | 小规模共享目录 |

**选型经验**：如果业务能接受「一次写入、整体读取、不做原地修改」的对象语义，MinIO 几乎总是性价比最高的选择；如果需要随机写、追加写或 POSIX 挂载，应改选 CephFS / RBD。

## 常见问题排错

| 现象 / 报错 | 原因 | 解决方案 |
|-------------|------|----------|
| `The difference between the request time and the server's time is too large` | 客户端与服务器时间不同步 | 配置 NTP，时间偏差需 < 15 分钟 |
| `SignatureDoesNotMatch` | 走反向代理后 Host/URL 变化导致签名不匹配 | 设置 `MINIO_SERVER_URL`，代理转发时保留原始 Host |
| `Access Denied` | 桶策略或 IAM 未授权 | `mc admin policy info` 检查；确认 `Resource` ARN 拼写 |
| `DiskFull` / 写入失败 | 磁盘满或 inode 耗尽 | 检查 `df -h` 与 `df -i`；预留 inode 余量 |
| `Drive offline` | 磁盘故障或挂载丢失 | `mc admin info` 定位；换盘后用同路径重新挂载，MinIO 自动 heal |
| 控制台打不开 | 未指定 console 端口 | 启动加 `--console-address ":9001"`，并放行防火墙 |
| 前端直传 CORS 报错 | 桶未配置 CORS | `mc admin config set myminio api cors_allow_origin="https://your.domain"` |
| `mc cp` 报 `drive is part of root drive` | 数据目录在系统盘根分区 | 挂载独立数据盘，或显式加 `--root` 之外的独立路径 |
| 分片上传残留占用空间 | 未 Complete/Abort | 配置 lifecycle 的 `abort_incomplete_multipart_upload_days` |

## 最佳实践清单

- [ ] 生产至少 4 节点 × 4 盘，节点间同机房低延迟网络
- [ ] 所有 Drive 型号/容量一致，使用 XFS 文件系统
- [ ] 开启 TLS，root 账号仅用于初始配置，日常用子账号 + 最小权限 Policy
- [ ] 配置 NTP 时间同步
- [ ] 大文件（> 100MB）走分片上传；小文件可考虑打包合并，避免元数据膨胀
- [ ] 前端上传一律走预签名 URL 直传，不要让文件流经应用服务器
- [ ] 开启版本控制 + 生命周期规则，控制容量增长
- [ ] 接入 Prometheus 告警，重点关注离线盘与可用容量
- [ ] 定演练：拔盘、关节点，验证 heal 与业务可用性

## 相关笔记

- [[middleware/index|中间件索引]]
- [[redis|Redis]]
- [[docker|Docker]]
- [[docker-compose|Docker Compose]]
- [[nginx|Nginx 反向代理]]
- [[linux|Linux]]

## 参考资料

- [MinIO 官方文档](https://min.io/docs/minio/linux/index.html)
- [MinIO Erasure Coding 原理](https://min.io/docs/minio/linux/operations/concepts/erasure-coding.html)
- [MinIO Java SDK](https://github.com/minio/minio-java)
- [Amazon S3 API Reference](https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html)
