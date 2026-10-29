---
title: Elasticsearch 技术文档
description: Elasticsearch 核心原理、索引设计、查询 DSL、聚合分析与生产调优的系统性笔记
tags:
  - elasticsearch
  - middleware
  - search
  - backend
  - distributed-system
date: 2026-10-28
aliases:
  - es
  - elastic-search
---

# Elasticsearch 技术文档

## 概述

关系型数据库做搜索会碰到三堵墙：`LIKE '%keyword%'` 无法命中 B+ 树索引只能全表扫描；无法按"相关性"
排序，只能按某个字段机械排序；无法在毫秒级完成多维度的聚合分析。
Elasticsearch（简称 ES）基于 Lucene的倒排索引构建，是一个分布式的**搜索与分析引擎**：它把"查找"变成词项到文档的映射查表，把分片副本机制
用于水平扩展，从而在亿级数据上做到近实时检索。

本文以 **8.x / 9.x** 为主（当前 GA 为 9.5.x），关键差异处会标注 7.x 的行为。

> **定位**：ES 是"搜索引擎 + 分析引擎"，不是主库。它不保证强一致的实时读、不支持事务与 JOIN，
> 业务写入应走 MySQL/PostgreSQL 等主库，再通过 CDC 或消息队列同步到 ES。

## 前置知识

- [[mysql|MySQL]]：理解索引、事务与主从同步，才能理解 ES 与数据库的分工
- [[redis|Redis]]：同样是缓存/中间件，对比 ES 的定位差异
- [[docker|Docker]]：本文用 Docker Compose 起本地环境

## 快速开始

### Docker Compose 单机环境

```yaml
# docker-compose.yml —— 开发/练手用，生产不要关安全认证
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:${ES_VERSION:-8.15.3}
    container_name: es01
    environment:
      - discovery.type=single-node          # 单机模式，跳过集群选举
      - xpack.security.enabled=false        # 关闭 TLS/认证，仅本地开发用
      - ES_JAVA_OPTS=-Xms1g -Xmx1g          # JVM 堆，不超过物理内存的 50%
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - es-data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:${ES_VERSION:-8.15.3}
    container_name: kibana01
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  es-data:
```

```bash
docker compose up -d
curl http://localhost:9200          # 返回版本与集群名即启动成功
curl -X GET "localhost:9200/_cat/health?v"   # 查看集群健康状态
```

> **8.x 起安全默认开启**：线上环境会强制 TLS 与账号密码，调用方式变为
> `curl -u elastic:<password> --cacert http_ca.crt https://localhost:9200`。

### 常用_cat 运维接口

```bash
GET /_cat/nodes?v              # 节点列表
GET /_cat/indices?v            # 索引列表（docs.count / store.size / health）
GET /_cat/shards?v             # 分片分布
GET /_cat/allocation?v         # 磁盘分配
GET /_cluster/health?pretty    # 集群健康：green / yellow / red
```

## 核心概念

### 逻辑模型：Index / Document / Field

| Elasticsearch | MySQL | 说明 |
|---------------|-------|------|
| Index（索引） | Table | 一类文档的集合，8.x 起已彻底移除 `type` 概念 |
| Document（文档） | Row | 一条 JSON 记录，最小数据单元 |
| Field（字段） | Column | 字段，类型由 mapping 定义 |
| Mapping | Schema | 字段类型与分词规则定义 |
| DSL（Query DSL） | SQL | JSON 格式的查询语言 |
| `_id` | 主键 | 文档唯一标识，不指定则由 ES 自动生成 |

### 物理模型：Cluster / Node / Shard / Segment

```text
Cluster
 └── Node（一个 ES 进程实例，有角色：master / data / ingest / coordinating）
      └── Index（逻辑）
           └── Shard（分片，Lucene 实例，index 创建时定死，不可改）
                ├── Primary Shard（主分片，承载写入）
                └── Replica Shard（副本，容灾 + 分摊读）
                     └── Segment（倒排索引的最小不可变单元，后台持续 merge）
```

关键性质：

- **分片数不可变**：`number_of_shards` 建索引时确定，改了要 reindex；`number_of_replicas` 可随时调整。
- **副本不提升写入性能**：副本在主分片写入后同步，副本多反而增加写放大，它主要提升读吞吐与可用性。
- **Segment 不可变**：删除是打 `.del` 标记，更新是"删旧 + 插新"，因此 ES 的更新成本高于插入。

### 倒排索引：为什么搜索快

正排是"文档 → 内容"，倒排是"词项 → 文档列表"。

```text
文档 1：小米手机 性能 强
文档 2：华为手机 拍照 强

Term Dictionary      Postings List（含词频、位置、偏移量）
小米                 → [1]
手机                 → [1, 2]
华为                 → [2]
拍照                 → [2]
强                   → [1, 2]
```

Lucene 在 Term Dictionary 之上又建了一层 **Term Index（FST）** 常驻内存，用于快速定位词项，
真正庞大的词项字典和倒排表压在磁盘上，靠 mmap/OS 页缓存加速。

| 结构 | 作用 | 是否默认开启 |
|------|------|--------------|
| Inverted Index | 倒排索引，支撑全文检索 | 是 |
| `_source` | 原始 JSON 全文，用于取回与 reindex | 是（可关闭省空间） |
| Doc Values | 列式存储，支撑排序、聚合、脚本 | 是（`text` 无，需要 `keyword`） |
| Stored Fields | 单独存储的字段，用于 `fields` 显式取回 | 否，需配置 |
| BKD Tree | 数值/地理/日期的多维索引，支撑 range 查询 | 是（数值字段自动） |

**`text` vs `keyword`** 是最容易踩的坑：

| 类型 | 是否分词 | 用途 | 能否聚合排序 |
|------|----------|------|--------------|
| `text` | 是，进倒排索引 | 全文检索 | 默认不能（需开 `fielddata`，不推荐） |
| `keyword` | 否，整体作为一个词项 | 精确匹配、聚合、排序 | 能 |

### 分词与分析器 Analysis

分析器由三段流水线组成：**character filter → tokenizer → token filter**。

```json
// 验证分词效果，排错神器
GET /_analyze
{
  "analyzer": "standard",
  "text": "Elasticsearch 8.x 实战笔记"
}
```

| 分析器 | 行为 | 适用 |
|--------|------|------|
| `standard` | 按 Unicode 分词，英文转小写；中文逐字切 | 英文默认 |
| `ik_smart` | 中文粗粒度切分 | 中文检索（需装插件） |
| `ik_max_word` | 中文最细粒度切分 | 中文索引（需装插件） |
| `keyword` | 不分词，整体作为一个 term | 精确值 |
| `simple` / `whitespace` | 按非字母 / 空格切分 | 简单场景 |

装中文分词插件（版本必须与 ES 完全一致）：

```bash
bin/elasticsearch-plugin install analysis-ik     # 或从 infinilabs/analysis-ik 下载对应版本 zip 离线安装
# 安装后重启节点，推荐建索引时用 ik_max_word 索引、ik_smart 检索
```

## 索引设计（Mapping）

### 字段类型速查

| 类型 | 说明 | 典型字段 |
|------|------|----------|
| `text` / `keyword` | 全文 / 精确 | 标题、品牌 |
| `long` / `integer` / `short` | 整数 | 库存、数量 |
| `double` / `float` / `scaled_float` | 浮点（金额用 `scaled_float` + `scaling_factor`） | 价格 |
| `date` | 日期，支持 `epoch_millis` 等 format | 创建时间 |
| `boolean` | 布尔 | 是否上架 |
| `object` | 内嵌对象，扁平化存储 | 扩展属性 |
| `nested` | 内嵌数组，独立文档存储 | 商品规格列表 |
| `dense_vector` | 向量，支撑 kNN 语义检索 | embedding |
| `geo_point` | 经纬度 | 门店坐标 |

### 显式 Mapping 示例（电商商品）

```json
PUT /product
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "5s",
    "analysis": {
      "analyzer": {
        "ik_idx":  { "type": "custom", "tokenizer": "ik_max_word" },
        "ik_srch": { "type": "custom", "tokenizer": "ik_smart" }
      }
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "title":    { "type": "text", "analyzer": "ik_idx", "search_analyzer": "ik_srch" },
      "brand":    { "type": "keyword" },
      "category": { "type": "keyword" },
      "price":    { "type": "scaled_float", "scaling_factor": 100 },
      "stock":    { "type": "integer" },
      "onSale":   { "type": "boolean" },
      "tags":     { "type": "keyword" },
      "specs":    {
        "type": "nested",
        "properties": {
          "name":  { "type": "keyword" },
          "value": { "type": "keyword" }
        }
      },
      "createTime": { "type": "date", "format": "yyyy-MM-dd HH:mm:ss||epoch_millis" }
    }
  }
}
```

### 设计要点

1. **优先显式 mapping，别依赖动态映射**。动态映射遇到第一个 `"2026-10-28"` 就推断成 `date`，
   之后再来个 `"未知时间"` 直接报错，且类型一旦生成无法修改，只能 reindex。
2. **用 `dynamic: "strict"` 或 `"false"` 防止字段爆炸**。
   `"strict"` 遇到未知字段直接拒绝写入，`"false"` 忽略该字段但仍存进 `_source`；
   生产推荐 `strict`，把 schema 变更变成可控的发版动作。
3. **字符串默认上 `keyword`**，只对真正需要全文检索的字段开 `text`；
   需要兼顾两者时用多字段：`"title": { "type": "text", "fields": { "raw": { "type": "keyword" } } }`，
   检索用 `title`，聚合排序用 `title.raw`。
4. **`object` 数组会丢失关联性**。`[{name: 颜色, value: 红}, {name: 尺寸, value: L}]`
   用 `object` 存会扁平成"颜色=[红], 尺寸=[L]"，查"颜色=红 且 尺寸=XL"会误命中，
   必须用 `nested`。`nested` 查询性能约为普通字段的数倍，只在确实需要时用。
5. **`join` 类型（父子文档）性能代价大**，绝大多数场景应反范式化冗余成宽表。

| 方案 | 存储方式 | 关联性 | 性能 | 适用 |
|------|----------|--------|------|------|
| `object` | 扁平化 | 丢失 | 高 | 单层固定结构 |
| `nested` | 独立隐藏文档 | 保留 | 中（查询放大） | 对象数组且需联合过滤 |
| `join` | 父子文档同分片 | 保留 | 低 | 子文档极多且频繁更新 |

## 写入流程与近实时搜索

```text
写入请求
  → 路由到主分片（shard = hash(_id) % 主分片数）
  → 写内存 buffer + 追加 translog（防宕机丢数据）
  → 并发同步到副本分片
  → refresh（默认 1s）：buffer 生成新 segment 并打开 → 此时可被搜索到（近实时）
  → flush：segment 落盘（fsync）+ 清空 translog（默认 30min 或 translog 达 512MB）
  → 后台 merge：多个小 segment 合并成大 segment，清理已删除文档
```

**近实时（NRT）** 的"近"就来自 `refresh_interval`（默认 1s）。写入后立即可查要显式 refresh，
但会破坏批量写入性能，不要逐条调用。

| 调优手段 | 做法 | 代价 |
|----------|------|------|
| 降低刷新频率 | 批量导入时 `refresh_interval: -1`，导完改回 | 可见延迟变长 |
| 关闭副本导入 | 导入期 `number_of_replicas: 0` | 期间无容灾 |
| 批量写入 | 用 `_bulk`，单批 5–15MB / 1000–5000 条 | 内存占用 |
| translog 异步刷盘 | `index.translog.durability: async` | 宕机可能丢最近几秒数据 |
| 自动生成 ID | 不指定 `_id` | 无法做幂等更新，需业务侧去重 |

## 文档操作 API

```bash
# 写入：指定 ID（幂等）；不指定用 POST 由 ES 生成 ID
PUT /product/_doc/1001
{ "title": "小米 14 手机", "brand": "小米", "price": 3999.00, "stock": 120 }

# 查询单个文档
GET /product/_doc/1001
GET /product/_doc/1001?_source_includes=title,price

# 局部更新（本质：取原文档 → 修改 → 整条重新索引）
POST /product/_update/1001
{ "doc": { "stock": 118 } }

# 删除（._del 标记，segment merge 时真正回收空间）
DELETE /product/_doc/1001

# 批量操作：两行一组（action + data），末尾必须换行
POST /_bulk
{ "index": { "_index": "product", "_id": "1002" } }
{ "title": "华为 Mate 60", "brand": "华为", "price": 5999.00 }
{ "update": { "_index": "product", "_id": "1001" } }
{ "doc": { "stock": 100 } }
{ "delete": { "_index": "product", "_id": "1003" } }
```

## 查询 DSL

### Query 上下文 vs Filter 上下文

| 维度 | Query（查询上下文） | Filter（过滤上下文） |
|------|--------------------|----------------------|
| 目的 | "有多匹配" | "是否匹配" |
| 是否算分 | 算 `_score` 并排序 | 不算分 |
| 是否缓存 | 否 | 是，缓存在 Node Query Cache |
| 典型子句 | `must` / `should` | `filter` / `must_not` |
| 适用 | 全文检索、相关性排序 | 状态、时间范围、分类、价格区间 |

**凡是"是否"类条件一律放 `filter`**——这是 ES 优化的第一优先级。

### 常用查询速查

| 查询 | 用途 | 是否分词 |
|------|------|----------|
| `match` | 标准全文检索，分词后按 term 匹配 | 是 |
| `match_phrase` | 短语匹配，要求词序相邻 | 是（保留位置） |
| `match_phrase_prefix` | 短语前缀，搜索框联想 | 是 |
| `multi_match` | 多字段检索，支持 `best_fields`／`cross_fields` | 是 |
| `term` / `terms` | 精确匹配，不分词 | 否 |
| `range` | 范围，支持 `gte/lte/gt/lt`、`now-7d` | - |
| `exists` | 字段是否存在 | - |
| `prefix` / `wildcard` / `regexp` | 前缀／通配／正则 | 否 |
| `fuzzy` | 编辑距离容错 | 否 |
| `ids` | 按 ID 批量取 | - |
| `nested` | 内嵌对象查询 | - |

### 组合查询 bool

```json
GET /product/_search
{
  "query": {
    "bool": {
      "must":     [ { "match": { "title": "手机 拍照" } } ],
      "should":   [ { "term": { "brand": "小米" } },
                    { "match": { "title": "旗舰" } } ],
      "minimum_should_match": 1,
      "filter":   [ { "range":  { "price": { "gte": 1000, "lte": 6000 } } },
                    { "term":   { "onSale": true } } ],
      "must_not": [ { "term": { "category": "配件" } } ]
    }
  },
  "sort":  [ { "price": "asc" }, { "_score": "desc" } ],
  "from": 0, "size": 20,
  "_source": { "excludes": [ "specs" ] },
  "highlight": {
    "fields": { "title": { "pre_tags": ["<em>"], "post_tags": ["</em>"] } }
  }
}
```

### 分页：三种方式的取舍

| 方式 | 机制 | 上限 | 适用 |
|------|------|------|------|
| `from` + `size` | 各分片取 `from+size` 条再在协调节点排序截断 | 默认 10000（`max_result_window`） | 浅分页，前几百条 |
| `search_after` | 用上一页排序值做游标，配合 PIT 保证一致性 | 无上限 | 深度翻页、用户下拉列表 |
| `scroll` | 创建快照游标遍历 | 无上限但占资源 | 全量导出、reindex |

深分页灾难：`from=990, size=10` 时，3 个分片各要算 1000 条，协调节点排序 3000 条后丢弃 2990 条，
数据量和分片数随页数线性放大，是集群 OOM 的经典来源。

```json
// search_after：必须有全局唯一排序键（通常加 _id 兜底）
POST /product/_search
{
  "size": 20,
  "sort": [ { "price": "asc" }, { "_id": "asc" } ],
  "search_after": [ 3999.0, "1001" ]
}
```

### 聚合分析

三类聚合：**Bucket**（分桶）→ **Metric**（指标计算）→ **Pipeline**（对聚合结果再聚合）。

```json
GET /product/_search
{
  "size": 0,
  "query": { "term": { "onSale": true } },
  "aggs": {
    "by_brand": {
      "terms": { "field": "brand", "size": 10, "order": { "avg_price": "desc" } },
      "aggs": {
        "avg_price": { "avg":    { "field": "price" } },
        "max_price": { "max":    { "field": "price" } },
        "price_range": {
          "range": { "field": "price", "ranges": [
            { "to": 2000 }, { "from": 2000, "to": 5000 }, { "from": 5000 } ] }
        }
      }
    },
    "price_percentile": { "percentiles": { "field": "price" } },
    "brand_count":      { "cardinality": { "field": "brand" } }
  }
}
```

> `cardinality` 是 HyperLogLog 近似值，有约 5% 误差，可通过 `precision_threshold` 提高精度（换内存）。
> `terms` 聚合的 `doc_count` 也是近似值，可能出现 `doc_count_error_upper_bound` 非零的情况。

## 相关性算分

ES 5.0 起默认使用 **BM25**（7.x 正式取代 TF-IDF），它解决了 TF-IDF 的两个问题：
词频无限增长导致分数无上界；长文档天然占优。

```text
score(D, Q) = Σ  IDF(qi) × ( f(qi,D) × (k1 + 1) ) / ( f(qi,D) + k1 × (1 - b + b × |D| / avgdl) )

IDF(qi) = ln( 1 + (N - n(qi) + 0.5) / (n(qi) + 0.5) )

f(qi,D)：词 qi 在文档 D 中的词频      |D|：文档长度
avgdl：平均文档长度                    k1 = 1.2（词频饱和度）  b = 0.75（长度惩罚）
```

调试手段与干预方式：

```bash
GET /product/_explain/1001
{ "query": { "match": { "title": "小米 手机" } } }   # 逐条看打分明细
```

| 手段 | 用法 | 场景 |
|------|------|------|
| `boost` | 字段级权重提升 | 标题比正文重要 |
| `boosting` 查询 | `negative_boost` 降权不排除 | 广告商品降权但不出局 |
| `function_score` | `field_value_factor` / `gauss` 衰减 / `random_score` | 销量加权、时间衰减、人气打散 |
| `rescore` | 先粗排后精排 | 只重算 Top N，成本可控 |
| `explain: true` | 返回算分明细 | 调相关性 |

## 集群与分片规划

### 节点角色

| 角色 | 配置 | 职责 |
|------|------|------|
| master-eligible | `node.roles: [master]` | 集群状态、索引创建、分片调度 |
| data | `node.roles: [data]` | 存储与执行数据相关操作 |
| ingest | `node.roles: [ingest]` | 预处理管道（pipeline） |
| coordinating | `node.roles: []` | 纯协调，分发与聚合结果 |

生产集群至少 3 个 master 候选节点（防脑裂），且 master 与 data 分离。

### 容量规划经验值

- **单个分片 20–50GB**（日志类可到 50GB，搜索类建议 20GB 左右），不要过碎也不要过大。
- **JVM 堆不超过物理内存的 50%，且 ≤ 30.5GB**（超过后 JVM 压缩指针失效，内存反而浪费），
  剩下的留给 OS 页缓存，Lucene 严重依赖它。
- **分片总数 = 主分片 × (1 + 副本数)**，每 GB 堆内存承载的分片数建议控制在 20 以内。
- 分片数一旦过多：每个分片都是完整 Lucene 实例，元数据、文件句柄、线程池消耗叠加，
  且 `from/size` 查询会按分片数放大。典型症状：几十个索引各 5 主分片 + 1 副本 → 数百分片 → 集群变慢。
- 时序数据（日志、指标）用 **ILM + 数据流（data stream）** 滚动，按天/按量切索引，
  过期索引走 `frozen` 或直接删除，不要无限往一个索引里写。

## Java 客户端实战

### 官方 Java API Client（8.x）

Maven 依赖：`co.elastic.clients:elasticsearch-java` + `org.elasticsearch.client:elasticsearch-rest-client`。

```java
// 1. 建客户端：RestClient 负责 HTTP，transport 负责序列化
ElasticsearchClient client = new ElasticsearchClient(
    new RestClientTransport(
        RestClient.builder(new HttpHost("localhost", 9200, "http")).build(),
        new JacksonJsonpMapper()));

// 2. 组合检索：must 走相关性，filter 走缓存
SearchResponse<Product> resp = client.search(s -> s
        .index("product")
        .query(q -> q.bool(b -> b
            .must(m -> m.match(t -> t.field("title").query(keyword)))
            .filter(f -> f.term(t -> t.field("brand").value(brand)))
            .filter(f -> f.range(r -> r.field("price").gte(JsonData.of(minPrice))))))
        .sort(so -> so.field(fd -> fd.field("price").order(SortOrder.Asc)))
        .from(0).size(20),
    Product.class);

for (Hit<Product> hit : resp.hits().hits()) {
    log.info("id={} score={} product={}", hit.id(), hit.score(), hit.source());
}
```

### Spring Data Elasticsearch（Spring Boot 3.x 对应 5.x）

```java
@Document(indexName = "product")
public class ProductDoc {
    @Id
    private String id;
    @Field(type = FieldType.Text, analyzer = "ik_max_word", searchAnalyzer = "ik_smart")
    private String title;
    @Field(type = FieldType.Keyword)
    private String brand;
    @Field(type = FieldType.Double)
    private BigDecimal price;
    @Field(type = FieldType.Date, format = DateFormat.date_hour_minute_second)
    private LocalDateTime createTime;
}
```

```java
// 简单查询用 Repository 方法名派生；复杂检索用 NativeQuery 直接写原生 DSL
NativeQuery query = NativeQuery.builder()
        .withQuery(q -> q.bool(b -> b
            .must(m -> m.match(mm -> mm.field("title").query(keyword)))
            .filter(f -> f.term(t -> t.field("brand").value(brand)))))
        .withPageable(PageRequest.of(0, 20))
        .build();

SearchHits<ProductDoc> hits = elasticsearchTemplate.search(query, ProductDoc.class);
```

> **版本对齐是硬约束**：Spring Boot 3.x → Spring Data Elasticsearch 5.x → ES Java Client 8.x，
> 客户端大版本必须与服务端大版本一致，否则序列化协议不兼容，直接报错。

## 性能优化与最佳实践

### 查询侧

1. **先 filter 后 query**：filter 结果进 Query Cache，且先缩小候选集能显著降低后续算分量。
2. **避免前置通配**：`*手机` 会强制扫描整个词项字典，改为 `ngram` 分词或用 `match_phrase_prefix`。
3. **只取需要的字段**：`_source` 过滤，或干脆用 `docvalue_fields` 取列存字段，减少网络与解压开销。
4. **只读不写的字段聚合走 `keyword`**：别在 `text` 上开 `fielddata`（堆内存杀手）。
5. **聚合前用 query 缩小范围**，高基数字段聚合考虑用 `composite` 分页聚合代替一次性 `terms`。
6. **用 `profile: true` 或 `_explain` 定位慢查询**，不要凭感觉调。

### 写入侧

1. **必须批量**：`_bulk` 单批 5–15MB，用 `_bulk` 的 `filter_path` 减少响应体积，失败要按 `item` 逐个重试。
2. **大批量导入时临时关刷新与副本**（见上文表格），导完再恢复并 `_forcemerge`。
3. **按业务键做 `_id`** 保证幂等重放，配合 `op_type=create` 或乐观锁（`if_seq_no` / `if_primary_term`）防覆盖。
4. **高频更新字段拆出去**：ES 更新是整条重建，把计数器类字段放 Redis 或独立索引。
5. **写入路由**：用 `routing` 把同租户数据打到固定分片，查询时可只查单分片，显著提速。

### 运维侧

- 磁盘水位线：`cluster.routing.allocation.disk.watermark` 默认 85%（低）/ 90%（高）/ 95%（冻结），
  磁盘打满会导致分片无法分配，务必留 20% 余量并配 ILM 清理。
- 只读索引做完 `_forcemerge` 到 1 个 segment，可显著降低内存与提升查询速度（代价是瞬时 IO 高）。
- 定期快照：`_snapshot` 到 S3/OSS/HDFS，跨集群迁移与回滚的唯一可靠手段。

## 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| 把 ES 当主库用 | ES 无事务、无强一致实时读，写入可能丢 | 主库存 MySQL，ES 只做检索副本 |
| 用 `term` 查 `text` 字段 | `text` 已分词，`term` 查不到原词 | `term` 只打 `keyword`，全文用 `match` |
| 写入后立刻查不到 | 近实时，默认 1s refresh | 业务上容忍，或显式 `?refresh=wait_for` |
| 深分页用 `from/size` | 分片数 × (from+size) 放大，易 OOM | 换 `search_after` 或限定页数 |
| 追求分片越多越好 | 分片过多元数据爆炸、查询放大 | 单分片 20–50GB，总量控制在堆内存的 20 分片/GB 内 |
| 在 `text` 上做聚合 | 报错或需开 `fielddata` 吃堆内存 | 建 `keyword` 子字段聚合 |
| 改字段类型 | ES 不允许改已有字段类型 | 新建索引 + `_reindex` + 别名切换 |
| 副本提升写入性能 | 副本增加写放大 | 副本是为读扩展与高可用 |
| `wildcard: *xx` | 全量扫描词项字典 | 改 `ngram` 分词或换检索方案 |
| 把大字段塞进 `_source` | 存储与网络成本翻倍 | `_source.excludes` 或只存必要字段 |

## 排错

| 症状 | 原因 | 排查/解决 |
|------|------|-----------|
| 集群 `red` | 有主分片缺失 | `GET _cluster/allocation/explain`；检查磁盘水位、节点是否掉线 |
| 集群 `yellow` | 副本分片未分配 | 单节点集群属正常；多节点则查节点数是否 ≥ `副本数 + 1` |
| `circuit_breaking_exception` | 聚合/fielddata 打爆堆内存 | 限制聚合基数、加断路阈值、改用 `composite` 分页聚合 |
| `too_many_clauses` | 布尔查询子句超 1024 | 改 `terms` lookup 或拆分查询 |
| `mapper_parsing_exception` | 字段类型与 mapping 不符 | 检查日期格式、数值溢出；必要时 reindex |
| `Result window is too large` | `from+size` 超 `max_result_window` | 改 `search_after`，或调大窗口（不推荐） |
| 写入 `rejected execution` | 写入线程池打满 | 降并发、增大 `bulk` 批次、扩容 data 节点 |
| 搜不到中文词 | 用了 `standard` 分词器 | 装 IK 插件并指定 `analyzer` |

## 与相关概念的关系

- 与 [[mysql|MySQL]]：MySQL 是主库，负责事务与强一致；ES 负责检索与分析。二者通过 Canal/CDC/MQ 同步，
  典型架构是"写 MySQL → binlog → 同步 ES"，ES 侧靠业务主键幂等保证最终一致。
- 与 [[redis|Redis]]：Redis 是精确键值的低延迟缓存，无检索与聚合能力；ES 是检索层，
  延迟高一个量级，二者常组合为"Redis 挡热点 → ES 兜底检索"。
- 与 [[clickhouse|ClickHouse]]：ClickHouse 是列式 OLAP，擅长大宽表聚合与即席分析，写入吞吐极高；
  ES 擅长全文检索与相关性排序。日志场景两者重叠，搜索场景选 ES，纯分析场景选 ClickHouse。
- 与 [[mongodb|MongoDB]]：MongoDB 是文档型主库，自带较弱全文索引；复杂检索通常仍外接 ES。

## 参考

- [Elasticsearch 官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Elasticsearch 权威指南（中文）](https://www.elastic.co/guide/cn/elasticsearch/guide/current/index.html)
- [analysis-ik 中文分词插件](https://github.com/infinilabs/analysis-ik)
- [[middleware/index|中间件索引]]
- [[mysql|MySQL]]
