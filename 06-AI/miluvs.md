---
title: Milvus 向量数据库技术文档
description: Milvus 云原生向量数据库的核心概念、系统架构、索引体系、检索能力与运维实践（基于 Milvus 3.0）
tags:
  - ai
  - vector-database
  - milvus
  - rag
date: 2026-09-02
draft: false
---

# Milvus 向量数据库技术文档

> **版本基线**：Milvus **3.0.0**（2026-07-29 发布，Apache 2.0，LF AI & Data 毕业项目）。
> 涉及版本演进的地方会显式标注 2.x / 3.0 差异。

Milvus 是一个开源的**云原生向量数据库**，专为海量向量的相似度检索设计，底层整合 Faiss、HNSW、DiskANN、SCANN 等向量检索库，
广泛应用于推荐系统、以图搜图、语义搜索、RAG、生物信息学等场景。

**特点速览**

- **高性能**：基于 ANN（近似最近邻）索引的毫秒级相似度检索，支持标量过滤与向量检索混合执行。
- **可扩展**：存算分离、计算节点无状态，可在 Kubernetes 上水平扩缩容。
- **索引丰富**：提供 FLAT / IVF 系列 / HNSW 系列 / DiskANN / SCANN / RaBitQ / GPU 系列等十余种索引。
- **云原生**：依赖仅剩对象存储、etcd 与自研零磁盘 WAL（Woodpecker），部署与运维成本低。

---

## 1. 数据模型

### 1.1 逻辑层级

Milvus 的数据组织从上到下分为 6 层：

| 层级 | 类比关系型数据库 | 说明 |
| --- | --- | --- |
| Database | Database | 命名空间，默认 `default`，单实例默认上限 64 个 |
| Collection | Table | 由主键 + 至少 1 个向量字段 + 若干标量字段组成 |
| Partition | 分区表 | 可选，按业务键（如租户、日期）物理隔离数据，减少扫描范围 |
| Shard | 分库（写入通道） | 集合创建时指定 `num_shards`，决定写入并行度与 DML 通道数 |
| Segment | 数据文件组 | 存储与索引的基本单位，分为 **Growing Segment** 与 **Sealed Segment** |
| Entity | Row | 一条记录，包含主键、向量与元数据字段 |

**Growing / Sealed Segment** 是理解 Milvus 读写路径的关键：

- **Growing Segment**：刚写入、仍可被持续追加的数据，驻留在 Streaming Node 内存中，可实时查询，但没有完整索引（暴力扫描）。
- **Sealed Segment**：达到一定阈值后封存的数据，落到对象存储，由 Data Node 建索引，再由 Query Node 加载提供检索。

封存阈值由 `dataCoord.segment.maxSize`（默认 **1024 MB**）与 `dataCoord.segment.sealProportion`（默认 **0.12**）共同决定，
使用 DiskANN 的集合上限为 `diskSegmentMaxSize`（默认 2048 MB）。

### 1.2 字段数据类型

| 分类 | 类型 | 说明 |
| --- | --- | --- |
| 主键 | `INT64` / `VARCHAR` | 仅这两种可作为主键，支持 `auto_id` 自动生成 |
| 标量 | `BOOL` | 布尔 |
| 标量 | `INT8` / `INT16` / `INT32` / `INT64` | 整型，时间戳常用 INT64 |
| 标量 | `FLOAT` / `DOUBLE` | 浮点 |
| 标量 | `VARCHAR` | 字符串，需指定 `max_length` |
| 标量 | `JSON` | 半结构化对象，支持 `JSON Path Index` |
| 标量 | `ARRAY` | 同构元素数组，需指定 `element_type` 与 `max_capacity` |
| 标量 | `GEOMETRY` / `TIMESTAMPTZ` / StructArray | 3.0 起支持（地理空间、带时区时间、结构体数组） |
| 向量 | `FLOAT_VECTOR` | 32 位浮点稠密向量，**最常用的类型** |
| 向量 | `FLOAT16_VECTOR` / `BFLOAT16_VECTOR` | 半精度，省内存/带宽 |
| 向量 | `INT8_VECTOR` | 8 位整型量化向量，适配量化推理模型 |
| 向量 | `BINARY_VECTOR` | 二值向量，图像指纹、化学指纹场景 |
| 向量 | `SPARSE_FLOAT_VECTOR` | 稀疏向量，用于 BM25 全文检索与学习式稀疏检索（SPLADE 等） |

**Schema 设计要点**

- 一个集合最多可包含 **4 个向量字段**（支持多模态 / 混合检索），向量维度必须显式指定。
- 开启 `enable_dynamic_field=True` 后，未声明的字段会自动写入 `$meta` JSON 动态字段，适合 schema 频繁变化的场景。
- 3.0 起支持**在线 Schema 演进**：不停机新增字段、外部/内部回填（backfill）、删除字段，无需重建集合。

---

## 2. 系统架构

### 2.1 四层架构

Milvus 遵循**控制面与数据面分离、存算分离**的原则，分为四层，各层可独立扩缩容：

```text
┌──────────────────────────────────────────────────────────────┐
│  Client (pymilvus / Java / Go / Node.js / REST / gRPC)       │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 1  接入层  Proxy（无状态，MPP 结果聚合 / 后处理）       │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 2  协调层  Coordinator（MixCoord，全局唯一 Active）     │
│            DDL/DCL/TSO · 流服务管理 · 查询管理 · 历史数据管理   │
└──────┬─────────────────────────────────────────┬─────────────┘
       │                                         │
┌──────▼──────────────────────────────┐  ┌───────▼─────────────────────────┐
│  Layer 3  执行层（Worker Nodes）     │  │  Layer 4  存储层                │
│                                     │  │                                 │
│  · Streaming Node  → 增量 / 实时     │  │  · 元存储  etcd                 │
│    WAL 读写、Growing 数据查询、       │  │  · WAL     Woodpecker（默认）   │
│    Growing → Sealed 转换、查询委派    │  │            / Kafka / Pulsar     │
│  · Query Node      → 历史数据查询     │  │  · 对象存储 MinIO / S3 / OSS /  │
│  · Data Node       → 压缩、建索引     │  │            COS / Vortex（v3）   │
└─────────────────────────────────────┘  └─────────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 状态 | 职责 |
| --- | --- | --- |
| **Proxy** | 无状态 | 请求校验、路由缓存、MPP 聚合与后处理（rerank、全局 TopK 归并） |
| **Coordinator**（MixCoord） | 主备 | 集群拓扑、DDL/DCL、TSO 发号、流服务发现、查询视图管理、下发压缩与建索引任务 |
| **Streaming Node** | 无状态 | 分片级 WAL 读写、实时数据查询、生成查询计划、故障恢复、Growing 数据落盘 |
| **Query Node** | 无状态 | 加载 Sealed Segment，执行历史数据检索与段内结果归并 |
| **Data Node** | 无状态 | 历史数据的 Compaction、索引构建、统计信息收集、Bulk Import |
| **etcd** | 有状态 | 元数据快照（Schema、消费位点）、服务注册与健康检查 |
| **Woodpecker** | 有状态 | 零磁盘云原生 WAL，直写对象存储，3.0 起支持独立服务化部署 |
| **对象存储** | 有状态 | 日志快照、标量/向量索引文件、中间查询结果 |

### 2.3 数据流

**写入路径（DML）**

1. Proxy 校验请求后转发到对应分片的 Streaming Node；
2. Streaming Node 先写 **WAL** 保证持久化；
3. 数据进入 Growing Segment，**立即可被查询**（实时性来源）；
4. Segment 达到封存阈值后转为 Sealed，Streaming Node 将其落盘到对象存储；
5. Data Node 对 Sealed Segment 执行 Compaction 与索引构建；
6. Query Node 加载新索引并替换对应的 Growing 数据。

**查询路径（DQL）**

1. Proxy 通过路由缓存定位目标节点（缓存未命中才访问 Coordinator）；
2. Proxy 转发到 Streaming Node，由其本地执行 Growing 数据查询，同时协调 Query Node 查询 Sealed 数据；
3. Query Node 按需从对象存储加载 Sealed Segment 并执行段级检索；
4. **多级归并**：Query Node 归并段内结果 → Streaming Node 归并 Query Node 结果 → Proxy 归并全部分片结果返回客户端。

### 2.4 架构演进（2.5 → 2.6 → 3.0）

| 变化 | 说明 |
| --- | --- |
| Streaming Node 独立（2.5 引入，2.6 GA） | 流处理从 DataNode/QueryNode/Proxy 中抽离，实现**流批分离** |
| Coordinator 合并为 MixCoord（2.6） | RootCoord / QueryCoord / DataCoord 三合一，跨模块通信变为进程内函数调用 |
| IndexNode 合并进 DataNode（2.6） | 压缩、Bulk Import、统计、建索引由统一调度器管理 |
| Woodpecker 替代 Kafka/Pulsar（2.6） | 去除外部 MQ 依赖，零磁盘 WAL 直写对象存储，中小规模部署成本大幅下降 |
| 外部集合 / 湖原生（3.0） | 可直接在 Parquet / Lance / Iceberg / Vortex 上建索引并提供服务，零拷贝 |
| Loon（Storage v3）（3.0） | 面向 ANN 后点读优化的列式存储引擎，点读 I/O 较 Parquet 降低约 135 倍 |

> **升级提示**：2.6 → 3.0 允许回滚，但一旦启用改变序列化格式的特性（如 Storage v3）则不可回滚。
> 3.0 中 Storage v3 与新索引版本默认关闭，需通过 `common.storage.useLoonFFI`、
> `dataCoord.targetVecIndexVersion=10`、`dataCoord.targetScalarIndexVersion=4` 手动开启。

---

## 3. 部署形态

| 形态 | 适用场景 | 部署方式 | 说明 |
| --- | --- | --- | --- |
| **Milvus Lite** | 本地原型、Notebook、单元测试 | `pip install pymilvus`，`MilvusClient("./demo.db")` | 嵌入式，Python 进程内运行，无需服务 |
| **Standalone** | 单机生产、中小规模（千万级） | Docker / Docker Compose | 单进程多模块，3.0 默认使用 Woodpecker + 内嵌 etcd |
| **Distributed** | 大规模生产（十亿级） | Kubernetes（Helm / Milvus Operator） | 各组件独立扩缩容 |
| **Zilliz Cloud** | 免运维托管 | 云 | 商业版，兼容 Milvus API |

### 3.1 单机部署（Docker）

```bash
# 下载并启动（默认 Woodpecker + 内嵌 etcd，无需外部依赖）
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh \
  -o standalone_embed.sh
bash standalone_embed.sh start

# 常用运维命令
bash standalone_embed.sh stop      # 停止
bash standalone_embed.sh upgrade   # 升级（保留数据与配置）
bash standalone_embed.sh delete    # 删除数据

# 需要 Backup 能力时改用 Docker Compose 方式部署
```

启动后可访问：

- gRPC / SDK 端口：**19530**
- 内嵌 etcd：2379（配置映射为当前目录 `embedEtcd.yaml`）
- **Milvus WebUI**：<http://127.0.0.1:9091/webui/>
- 数据卷：当前目录 `volumes/milvus`，自定义配置写入 `user.yaml`

### 3.2 分布式部署（Milvus Operator）

```yaml
apiVersion: milvus.io/v1beta1
kind: Milvus
metadata:
  name: my-milvus
  namespace: milvus
spec:
  mode: cluster
  components:
    image: milvusdb/milvus:v3.0.0
    imageUpdateMode: rollingUpgrade
    proxy:
      replicas: 2
    mixCoord:
      replicas: 1
    dataNode:
      replicas: 2
    queryNode:
      replicas: 4
      resources:
        requests:
          cpu: "4"
          memory: "16Gi"
  dependencies:
    etcd:
      inCluster:
        values:
          replicaCount: 3
    storage:
      type: MinIO
      inCluster:
        values:
          mode: distributed
    msgStreamType: woodpecker
  config:
    dataCoord:
      enableActiveStandby: true
```

---

## 4. 索引体系

### 4.1 索引 = 数据结构 + 量化 + 精排

Milvus 的向量索引由三部分组成，理解这一点就掌握了全部索引命名的规律：

- **数据结构**：决定如何缩小候选集。
  - **IVF（倒排文件）**：用聚类把向量分桶，只扫描质心接近查询向量的桶；适合大规模、大 topK。
  - **Graph（图，HNSW）**：分层可导航小世界图，查询复杂度近似对数级；适合低延迟、高精度。
- **量化（可选）**：压缩向量降低内存与算力。
  - **SQ8**：每维压成 1 字节，内存降至 1/4。
  - **PQ**：切分子向量并用码本编码，压缩比 4~32 倍，召回略有损失。
  - **RaBitQ（2.6+）**：1 bit 量化，压缩至 1/32，配合 SQ6/SQ8/FP16/FP32 精排可保住召回。
- **精排（Refiner，可选）**：构建索引时确定**扩检率**，查询时先取 `topK × 扩检率` 个候选，再用更高精度重算距离，返回最准的 topK。

### 4.2 索引类型全景

| 字段类型 | 类别 | 可用索引 |
| --- | --- | --- |
| `FLOAT_VECTOR` | 内存型 | `FLAT`、`IVF_FLAT`、`IVF_SQ8`、`IVF_PQ`、`IVF_RABITQ`、`HNSW`、`HNSW_SQ/PQ/PRQ`、`SCANN` |
| `FLOAT_VECTOR` | 磁盘 / GPU | `DISKANN`、`AISAQ`、`FAISS`、`GPU_CAGRA`、`GPU_IVF_FLAT`、`GPU_IVF_PQ`、`GPU_BRUTE_FORCE` |
| `FLOAT16/BFLOAT16/INT8_VECTOR` | 内存 / 磁盘 | 同上（除 `FAISS` 外） |
| `BINARY_VECTOR` | `BIN_FLAT`、`BIN_IVF_FLAT`、`MINHASH_LSH`、`FAISS` |
| `SPARSE_FLOAT_VECTOR` | `SPARSE_INVERTED_INDEX`（3.0 内部支持 SINDI / Block-Max WAND / MaxScore） |
| `VARCHAR` | `INVERTED`（推荐）、`BITMAP`、`Trie` |
| `BOOL` | `BITMAP`（推荐）、`INVERTED` |
| 整型 | `INVERTED`、`STL_SORT` |
| `FLOAT` / `DOUBLE` | `INVERTED` |
| `ARRAY` | `BITMAP`（推荐）、`INVERTED` |
| `JSON` | `INVERTED`（支持 JSON Path Index） |

> 稀疏索引注意：自 2.5.4 起 `SPARSE_WAND` 索引类型已废弃，改用 `"inverted_index_algo": "DAAT_WAND"` 参数。
> 3.0 中 SINDI 是稀疏 IP 检索的默认算法，BM25 默认走 MaxScore。
> `FAISS` 是 3.0 新增的直通索引，通过 `faiss_index_name` 传入任意 Faiss index-factory 字符串
> （如 `IVF64,Flat`、`HNSW16,Flat`、`OPQ16,IVF64,PQ16x4`）。

### 4.3 关键索引参数

| 索引 | 构建参数 | 搜索参数 | 要点 |
| --- | --- | --- | --- |
| `FLAT` | — | — | 暴力精确检索，100% 召回，仅适合百万级以下 |
| `IVF_FLAT` | `nlist` | `nprobe` | `nlist` 建议取 `4 × √N`；`nprobe` 越大召回越高、延迟越高 |
| `IVF_SQ8` | `nlist` | `nprobe` | 内存降至约 1/4，性价比高 |
| `IVF_PQ` | `nlist`、`m`、`nbits` | `nprobe` | `m` 为子向量数（需整除 dim），压缩最激进 |
| `IVF_RABITQ` | `nlist`、`refine_type`、`rbq_bits_query` | `nprobe` | 1bit 量化 + 精排，内存约 28%，QPS 提升 3~4 倍 |
| `HNSW` | `M`、`efConstruction` | `ef` | `M` 建议 8~64，`efConstruction` 建议 8~512；`ef` 必须 ≥ topK |
| `HNSW_SQ/PQ/PRQ` | 同 HNSW + 量化参数 | 同 HNSW | 图结构 + 量化，省内存 |
| `SCANN` | `nlist`、`with_raw_data` | `nprobe`、`reorder_k` | Google 出品，超大数据集高吞吐 |
| `DISKANN` | — | `search_list_size` | 图存磁盘，适合内存装不下且要求稳定延迟 |
| `GPU_CAGRA` | `intermediate_graph_degree`、`graph_degree` | `search_width`、`itopk_size` | GPU 图索引，构建与检索性能极高 |

### 4.4 索引选型决策矩阵

| 场景 | 推荐索引 |
| --- | --- |
| 原始数据可全部放入内存 | `HNSW`，或 `IVF_*` + 精排；低 topK / 高召回优先 HNSW |
| 数据在 SSD，要求低延迟稳定 | `DISKANN` |
| 数据在磁盘，内存受限 | `IVF_PQ` / `IVF_SQ8` + `mmap` |
| 过滤率 > 95% | `FLAT`（候选集极小，索引开销反而浪费） |
| topK 很大（≥ 数据集 1%） | `IVF` 系列 |
| 要求召回率 > 99% | `FLAT` + GPU |
| 十亿级 + 成本敏感 | `IVF_RABITQ` / `DISKANN` / 量化 + mmap |

**过滤率与索引的对应关系**（经验值，需实测校准）：

- 过滤率 < 85%：图索引（HNSW）优于 IVF；
- 过滤率 85% ~ 95%：IVF 系列更优；
- 过滤率 > 98%：直接使用暴力检索 `FLAT`。

### 4.5 内存估算

以 **100 万条 128 维** float32 向量（原始 512 MB）为例，官方给出的 IVF 系列估算：

| 配置 | 构成 | 总内存 |
| --- | --- | --- |
| IVF-PQ（无精排） | 质心 1.0 MB + 聚类 ID 2.0 MB + PQ 8.0 MB | **11.0 MB** |
| IVF-PQ + 10% 原始精排 | 上述 + 51.2 MB | **62.2 MB** |
| IVF-SQ8（无精排） | 1.0 MB + 2.0 MB + 128 MB | **131.0 MB** |
| IVF-FLAT（完整原始向量） | 1.0 MB + 2.0 MB + 512 MB | **515.0 MB** |

通用估算公式：

```text
原始向量内存   = N × dim × 4 bytes            （float32）
HNSW 内存      ≈ 原始向量 × 1.5 ~ 2.5          （图结构每节点约 2×M 条边）
IVF_SQ8 内存   ≈ 原始向量 × 1/4
IVF_PQ 内存    ≈ 原始向量 × 1/32 ~ 1/16
```

---

## 5. 相似度度量

| 度量类型 | 字段类型 | 值域 / 语义 | 说明 |
| --- | --- | --- | --- |
| `L2` | 稠密浮点向量 | `[0, +∞)`，**越小越相似** | 欧氏距离，Milvus 内部不取平方根 |
| `IP` | 稠密浮点向量 | 越大越相似 | 内积，适合关心模长的场景 |
| `COSINE` | 稠密浮点向量 | `[-1, 1]`，越大越相似 | 余弦相似度，等价于归一化后的 IP |
| `JACCARD` | 二值向量 | `[0, 1]`，越小越相似 | 集合交并比 |
| `HAMMING` | 二值向量 | `[0, dim]`，越小越相似 | 汉明距离 |
| `IP` / `BM25` | 稀疏向量 | 越大越相似 | 全文检索默认使用 `BM25` |

> **最常见的坑**：使用 `IP` 时必须先对向量做归一化，否则 top1 结果可能不是查询向量自身；
> 归一化后 `IP` 等价于 `COSINE`。集合默认度量类型为 `COSINE`。

---

## 6. 一致性模型

Milvus 提供 4 种一致性级别，**默认为 Bounded（有界过期）**，可在单次 `search` / `hybrid_search` / `query` 中覆盖。

| 级别 | 语义 | 延迟 | 典型场景 |
| --- | --- | --- | --- |
| `Strong` | 总能读到最新数据 | 最高 | 金融支付、账单、功能测试验证 |
| `Bounded` | 允许一段时间内的数据不可见 | 低 | 推荐系统、视频召回（默认） |
| `Session` | 同一客户端写入的数据立即可读 | 较低 | 写后立即刷新页面可见的后台管理场景 |
| `Eventually` | 不保证读写顺序，副本最终收敛 | 最低 | 商品评论、评分等弱一致场景 |

**底层机制**：Milvus 通过 **Guarantee Timestamp（GuaranteeTs）** 实现一致性。查询节点在执行请求前会等待，
直到 GuaranteeTs 之前的所有数据都可见为止。

- `Strong`：GuaranteeTs = 最新系统时间戳；
- `Bounded`：GuaranteeTs 略小于最新系统时间戳（容忍有界的数据滞后）；
- `Session`：GuaranteeTs = 该客户端最近一次写入的时间戳；
- `Eventually`：GuaranteeTs 取极小值，跳过一致性检查。

```python
res = client.search(
    collection_name="kb_docs",
    data=[query_vector],
    limit=10,
    consistency_level="Strong",   # Strong / Bounded / Session / Eventually
)
```

---

## 7. 检索能力

### 7.1 能力矩阵

| 能力 | 入口 | 说明 |
| --- | --- | --- |
| 单向量 ANN 检索 | `search()` | 基础相似度检索 |
| 过滤检索 | `search(filter=...)` | 布尔表达式先过滤再检索 |
| 混合检索 | `hybrid_search()` | 多路召回 + RRF / 加权融合 |
| 范围检索 | `search(params={"radius":..., "range_filter":...})` | 返回距离落在区间内的结果 |
| 分组检索 | `search(group_by_field=...)` | 按字段分组去重，提升结果多样性 |
| 关键词检索 | `filter='text_match(...)'` | 基于倒排的精确词项匹配 |
| 短语匹配 | `filter='phrase_match(...)'` | 3.0 支持词序敏感匹配，可调 `slop` |
| 全文检索（BM25） | `SPARSE_FLOAT_VECTOR` + BM25 Function | 2.5 起原生支持 |
| 标量查询 | `query()` / `query_iterator()` | 按主键或表达式取原始记录 |
| 分页 | `offset` + `limit` | 深分页建议改用 `search_iterator` |
| 排序 / 聚合 / 分面 | `order_by` / 聚合函数 / facet 字段 | 3.0 起服务端完成，减少客户端过度取数 |
| 时间衰减重排 | Decay Function | 3.0 起，按指数/线性/高斯衰减调整时效性 |

### 7.2 过滤表达式

```text
# 比较与逻辑
pub_ts >= 1735660800 and category in ["ai", "db"] and not (score < 0.5)

# 字符串匹配
title like "Milvus%"                        # 前缀/通配符匹配

# JSON 路径（配合 JSON Path Index 可大幅加速）
metadata["author"]["city"] == "Beijing"
json_contains(tags, "llm")

# 数组
array_contains(labels, "rag")
array_length(labels) > 3

# 全文
text_match(content, "vector database")
phrase_match(content, "vector database", 1)   # 第三个参数为 slop

# 空值与类型转换
publish_year is null
CAST(publish_year as VARCHAR) == "2026"
```

### 7.3 混合检索融合策略

| 策略 | 说明 | 适用 |
| --- | --- | --- |
| `RRFRanker(k)` | 倒数排名融合，`score = Σ 1/(k + rank)`，k 默认 60 | 各路分数量纲不一致时的默认选择 |
| `WeightedRanker(w1, w2, ...)` | 加权求和，权重之和无需为 1 | 明确知道各路重要性的业务 |

---

## 8. Python 实战（pymilvus）

> 三种部署形态共用同一套客户端 API，切换时只需更换 `uri` 与 `token`。

### 8.1 连接

```python
from pymilvus import MilvusClient

# Milvus Lite（本地文件，零依赖）
client = MilvusClient("./milvus_demo.db")

# Standalone / Distributed
client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
```

### 8.2 定义 Schema（稠密 + BM25 稀疏双路）

```python
from pymilvus import MilvusClient, DataType, Function, FunctionType

client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
COLL = "kb_docs"

schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
schema.add_field("doc_id", DataType.INT64, is_primary=True)
schema.add_field("title", DataType.VARCHAR, max_length=512)
schema.add_field("category", DataType.VARCHAR, max_length=64)
schema.add_field("pub_ts", DataType.INT64)
schema.add_field(
    "content", DataType.VARCHAR, max_length=8192,
    enable_analyzer=True, analyzer_params={"type": "chinese"},
)
schema.add_field("dense", DataType.FLOAT_VECTOR, dim=1024)
schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)

# 服务端自动生成 BM25 稀疏向量（Data-in, Data-out）
schema.add_function(Function(
    name="bm25_fn",
    function_type=FunctionType.BM25,
    input_field_names=["content"],
    output_field_names=["sparse"],
))
```

### 8.3 建索引与建集合

```python
index_params = MilvusClient.prepare_index_params()
index_params.add_index(
    field_name="dense", index_type="HNSW", metric_type="COSINE",
    params={"M": 16, "efConstruction": 200},
)
index_params.add_index(
    field_name="sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25",
    params={"inverted_index_algo": "DAAT_MAXSCORE", "bm25_k1": 1.2, "bm25_b": 0.75},
)
index_params.add_index(field_name="category", index_type="INVERTED")
index_params.add_index(field_name="pub_ts", index_type="INVERTED")

client.create_collection(
    collection_name=COLL,
    schema=schema,
    index_params=index_params,
    num_shards=2,                    # 写入并行度
    consistency_level="Bounded",
)
```

### 8.4 写入与加载

```python
rows = [
    {
        "doc_id": 1,
        "title": "Milvus 架构解析",
        "category": "ai",
        "pub_ts": 1735660800,
        "content": "Milvus 采用存算分离架构，由 Proxy、Coordinator、Worker Node 与存储层组成。",
        "dense": [0.021, -0.113, 0.087],   # 实际应为 1024 维模型输出
    },
]

client.insert(collection_name=COLL, data=rows)
client.flush(collection_name=COLL)          # 立即封存，保证落盘可见
client.load_collection(collection_name=COLL)  # 检索前必须加载
```

### 8.5 单向量检索（带过滤）

```python
res = client.search(
    collection_name=COLL,
    data=[query_vector],      # 支持一次传入多个查询向量批量检索
    anns_field="dense",
    limit=10,
    filter='category == "ai" and pub_ts >= 1735660800',
    search_params={"metric_type": "COSINE", "params": {"ef": 128}},
    output_fields=["title", "category"],
    consistency_level="Bounded",
)

for hits in res:
    for hit in hits:
        print(hit["id"], round(hit["distance"], 4), hit["entity"]["title"])
```

### 8.6 混合检索（稠密 + BM25）

```python
from pymilvus import AnnSearchRequest, RRFRanker, WeightedRanker

req_dense = AnnSearchRequest(
    data=[query_vector],
    anns_field="dense",
    param={"metric_type": "COSINE", "params": {"ef": 128}},
    limit=20,
)
req_sparse = AnnSearchRequest(
    data=[query_sparse_vector],        # 启用 Function 时可直接传原始文本
    anns_field="sparse",
    param={"metric_type": "BM25", "params": {"drop_ratio_search": 0.2}},
    limit=20,
)

res = client.hybrid_search(
    collection_name=COLL,
    reqs=[req_dense, req_sparse],
    ranker=RRFRanker(60),              # 或 WeightedRanker(0.7, 0.3)
    limit=10,
    output_fields=["title", "content"],
)
```

### 8.7 分组检索、范围检索与迭代取数

```python
# 分组检索：同一作者最多返回 2 条，提升结果多样性
client.search(
    collection_name=COLL, data=[query_vector], anns_field="dense", limit=10,
    group_by_field="doc_id", group_size=2, strict_group_size=False,
    search_params={"metric_type": "COSINE", "params": {"ef": 128}},
)

# 范围检索：COSINE 相似度落在 [0.7, 1.0] 之间
client.search(
    collection_name=COLL, data=[query_vector], anns_field="dense", limit=100,
    search_params={
        "metric_type": "COSINE",
        "params": {"radius": 0.7, "range_filter": 1.0, "ef": 128},
    },
)

# 大数据量导出：避免深分页
it = client.query_iterator(
    collection_name=COLL, filter='category == "ai"',
    batch_size=1000, output_fields=["doc_id", "title"],
)
while True:
    batch = it.next()
    if not batch:
        it.close()
        break
```

### 8.8 删除与更新

```python
client.delete(collection_name=COLL, ids=[1, 2])
client.delete(collection_name=COLL, filter='category == "draft"')
client.upsert(collection_name=COLL, data=rows)      # 主键存在则更新，否则插入
client.drop_collection(collection_name=COLL)
```

---

## 9. 性能调优

### 9.1 调优清单

| 维度 | 手段 | 建议 |
| --- | --- | --- |
| 索引参数 | `nlist` / `nprobe` / `ef` / `M` | 先固定召回目标（如 95%），再最小化 `nprobe`/`ef` 换取延迟 |
| 标量过滤 | 给高频过滤字段建 `INVERTED` 索引 | 不建索引时过滤退化为全量扫描 |
| JSON 过滤 | JSON Path Index | 官方实测单 Segment 过滤延迟 140 ms → 1.5 ms（P99 480 ms → 10 ms） |
| 内存 | `mmap` | 通过 `queryNode.mmap.vectorField` 等开关把冷数据换出到磁盘 |
| 段管理 | `dataCoord.segment.maxSize` | 默认 1024 MB；段过多会增加检索放大，可用 `ForceMerge` 手动合并 |
| 分区 | Partition / Partition Key | 按租户或时间分区，检索时可裁剪大部分数据 |
| 并行度 | `num_shards` | 与写吞吐、Query Node 数量匹配，过多会增加归并成本 |
| 资源估算 | Query Node 内存 ≥ 索引大小 + 开销 | 内存不足会触发频繁换入换出甚至加载失败 |
| 批量写入 | Bulk Import | 亿级初始化数据用 Bulk Import，避免逐条 insert 打爆 WAL |
| 只读副本 | Query Node 多副本 | 提升 QPS 与可用性 |

### 9.2 mmap 配置

```yaml
queryNode:
  mmap:
    vectorField: true       # 向量原始 data 使用 mmap 加载
    vectorIndex: false      # 向量索引
    scalarField: false      # 标量原始 data
    scalarIndex: false      # 标量索引
    jsonShredding: true     # JSON 统计信息
    maxDiskUsagePercentageForMmapAlloc: 50
```

> mmap 不是万能解：当大部分数据落在磁盘上时，`DISKANN` 的延迟表现通常优于 mmap。

### 9.3 常见性能反模式

- 未建标量索引就做大比例过滤检索；
- `ef` 设置小于 `limit`，导致召回被硬性截断；
- 单集合分片数远超 Query Node 数量，归并开销大于并行收益；
- 用 `offset` 做深分页（应改用 `search_iterator` 或游标字段）；
- 为每个小集合都分配独立 Partition，导致元数据膨胀（3.0 已支持 10 万级集合，仍建议控制粒度）。

---

## 10. 运维与生态工具

| 工具 | 用途 |
| --- | --- |
| **Milvus WebUI** | 内置可视化面板，<http://127.0.0.1:9091/webui/> |
| **Attu** | 图形化管理 GUI，集合/数据/索引可视化操作 |
| **Milvus CLI** | 命令行工具，适合脚本化运维 |
| **Milvus Backup** | 备份与恢复（Standalone 建议使用 Docker Compose 部署方式） |
| **Birdwatcher** | 调试与动态配置更新 |
| **Milvus CDC** | 数据变更捕获，支持主从同步 |
| **Prometheus + Grafana** | 指标监控，官方提供 Grafana 看板 |
| **Milvus Operator / Helm** | Kubernetes 部署与生命周期管理 |

**关键监控指标**：查询延迟（P50/P99）、QPS、Segment 数量与大小、Growing Segment 存量、
Query Node 内存水位、WAL 消费延迟、Compaction 任务堆积。

---

## 11. 生态集成

| 方向 | 集成方式 |
| --- | --- |
| RAG 框架 | LangChain（`MilvusVectorStore`）、LlamaIndex（`MilvusVectorStore`） |
| Java 生态 | Spring AI 的 `MilvusVectorStore`（支持 18+ 向量库统一抽象） |
| 模型接入 | 3.0 起内置 Function，支持 OpenAI / Bedrock / Vertex AI / Hugging Face 在线向量化 |
| 数据处理 | Spark DataSource V2 Connector（3.0）、Snapshot 导出给批处理/去重/聚类任务 |
| Agent 工具 | 官方 MCP Server 与 `milvus-skill`，供 AI 编码助手生成正确的 Milvus 代码 |

**RAG 典型链路**

```text
文档 → 切分 → Embedding 模型 → Milvus（稠密 + BM25 稀疏双路索引）
                                     ↓
用户提问 → 向量化 → 混合检索 + 元数据过滤 → RRF 融合 → Rerank 模型 → TopK → LLM 生成
```

---

## 12. 应用场景

- **RAG 与知识库**：稠密 + 稀疏混合检索，配合元数据过滤与重排，效果显著优于单路召回。
- **推荐系统**：用户/物品向量化后做实时相似召回，用 `Bounded` 一致性换取低延迟。
- **以图搜图**：存储图像特征向量实现相似图检索，规模大时选 `DISKANN` 或 `IVF_RABITQ`。
- **自然语言处理**：文本嵌入向量存储，支撑语义搜索与问答。
- **生物信息学**：基因序列、蛋白质结构向量化后的相似性分析。
- **近似去重**：`MINHASH_LSH` 索引 + MinHash Function，用于训练语料清洗。

---

## 13. 参考

- 官方文档：<https://milvus.io/docs>
- 索引选型：<https://milvus.io/docs/index-explained.md>
- 相似度度量：<https://milvus.io/docs/metric.md>
- 一致性模型：<https://milvus.io/docs/consistency.md>
- 架构总览：<https://milvus.io/docs/architecture_overview.md>
- 版本说明：<https://milvus.io/docs/release_notes.md>
- 中文架构解析：[云原生向量数据库 Milvus 知识大全](https://cloud.tencent.com/developer/article/2338267)
- 本地实践笔记：[[milvus-coroutines]]
- [Milvus 3.0 发布：湖原生向量搜索与更强大的检索引擎](https://milvus.io/blog/announcing-milvus-3-lake-native-vector-search-and-a-more-powerful-retrieval-engine.md)
