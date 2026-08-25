---
title: MongoDB
description: MongoDB 文档数据库的核心概念、数据建模、CRUD 操作、索引、聚合管道、副本集与分片、事务及性能优化。
tags:
  - database
  - mongodb
  - nosql
date: 2026-08-23
---

# MongoDB

MongoDB 是面向文档的分布式 NoSQL 数据库，使用 BSON（Binary JSON）格式存储数据，以灵活的模式、水平扩展能力和丰富的查询语言著称。适用于内容管理、用户画像、物联网时序数据、实时分析等模式频繁变化或数据量增长迅速的场景。

## 核心概念

### 与关系型数据库的术语对照

| 关系型数据库 | MongoDB | 说明 |
| --- | --- | --- |
| Database | Database | 数据库容器 |
| Table | Collection | 集合，存储一组文档 |
| Row | Document | 文档，以 BSON 存储，对应一个 JSON 对象 |
| Column | Field | 文档中的字段 |
| Index | Index | 索引，底层使用 B-tree 或专用类型 |
| Join | `$lookup` | 聚合管道阶段，实现左外连接 |
| Foreign Key | Reference | 引用，通过 `_id` 或手动存引用 |
| Primary Key | `_id` | 默认 `ObjectId`，也可自定义 |

### 文档与集合

一个文档就是一个类 JSON 对象，MongoDB 内部以 BSON 存储，支持更多数据类型（如 `ObjectId`、`Date`、`Decimal128`、`BinData` 等）：

```javascript
// 一个典型的用户文档
{
  _id: ObjectId("65a1b2c3d4e5f6a7b8c9d0e1"),
  username: "alice",
  email: "alice@example.com",
  age: 28,
  tags: ["vip", "active"],
  profile: {
    city: "上海",
    hobbies: ["reading", "hiking"]
  },
  created_at: ISODate("2026-01-15T08:30:00Z"),
  status: "active"
}
```

- **集合**（Collection）是无固定模式的，同一集合中的文档可以拥有不同的字段结构。
- **`_id` 字段**是必须的，如果插入时不指定，MongoDB 会自动生成一个 `ObjectId`。`ObjectId` 由 12 字节组成（4 字节时间戳 + 5 字节随机值 + 3 字节递增计数器），天然具备有序性。
- MongoDB 对**单文档大小限制为 16MB**，大字段应使用 [GridFS](https://www.mongodb.com/docs/manual/core/gridfs/) 分块存储。

### 数据类型

| 类型 | 示例 | 说明 |
| --- | --- | --- |
| String | `"hello"` | UTF-8 字符串，最常用 |
| ObjectId | `ObjectId(...)` | 12 字节唯一标识 |
| Integer | `42` / `NumberLong(42)` | 32 位或 64 位 |
| Double | `3.14` | 64 位浮点 |
| Decimal128 | `NumberDecimal("99.99")` | 高精度十进制，适合金额 |
| Boolean | `true` | 布尔值 |
| Date | `ISODate(...)` | UTC 时间戳，精度到毫秒 |
| Array | `[1, 2, 3]` | 有序元素列表 |
| Object | `{ key: "value" }` | 嵌套文档 |
| Null | `null` | 空值 |
| BinData | `BinData(...)` | 二进制数据 |
| Timestamp | `Timestamp(...)` | 内部复制 oplog 使用 |

## 数据建模

### 嵌套文档 vs 引用

MongoDB 建模的核心决策是**将相关数据嵌入同一文档，还是通过引用分散到不同集合**。

| 维度 | 嵌入（Embedded） | 引用（Referenced） |
| --- | --- | --- |
| 读取 | 一次查询获取完整数据，无需 `$lookup` | 需多次查询或聚合管道 |
| 写入 | 更新子文档需重写部分文档 | 各文档独立更新 |
| 数据一致性 | 单文档原子操作 | 需事务保证跨文档一致性 |
| 适用 | 子数据量小、读取为主、"一对少量" | 子数据量大、"一对多/多对多"、数据共享 |

#### 嵌入示例

```javascript
// 博客文章内嵌评论——一次查询获取文章和所有评论
db.articles.insertOne({
  title: "MongoDB 入门",
  content: "MongoDB 是文档数据库...",
  author: "alice",
  tags: ["database", "nosql"],
  comments: [
    { author: "bob", text: "写得很好", created_at: ISODate("2026-08-20T10:00:00Z") },
    { author: "carol", text: "学到了", created_at: ISODate("2026-08-20T11:00:00Z") }
  ],
  created_at: ISODate("2026-08-20T09:00:00Z")
});

// 查询时一次拿到全部内容
db.articles.findOne({ title: "MongoDB 入门" });
```

#### 引用示例

```javascript
// 订单引用商品——商品数据量大且被多订单共享
db.products.insertOne({
  _id: "P001",
  name: "机械键盘",
  price: NumberDecimal("599.00"),
  stock: 100
});

db.orders.insertOne({
  order_no: "ORD-20260823-001",
  customer_id: ObjectId("65a1b2c3d4e5f6a7b8c9d0e1"),
  items: [
    { product_id: "P001", quantity: 2, unit_price: NumberDecimal("599.00") },
    { product_id: "P002", quantity: 1, unit_price: NumberDecimal("299.00") }
  ],
  total: NumberDecimal("1497.00"),
  status: "pending",
  created_at: ISODate("2026-08-23T10:00:00Z")
});

// 通过聚合管道关联查询
db.orders.aggregate([
  { $match: { status: "pending" } },
  { $unwind: "$items" },
  {
    $lookup: {
      from: "products",
      localField: "items.product_id",
      foreignField: "_id",
      as: "product_info"
    }
  }
]);
```

### 建模原则

1. **优先嵌入**：数据量小、频繁一起读取时嵌入，减少查询往返。
2. **避免无限增长**：文档不应无限变大（如评论无上限增长），超过几百条应拆分到独立集合并引用。
3. **读写分离考量**：如果子文档频繁单独更新，嵌入会导致每次写入重写整个数组。
4. **金额用 Decimal128**：不要用 `Double` 存储金额，浮点误差会导致精度问题。
5. **时间用 ISODate**：统一存储 UTC 时间，在应用层做时区转换。

## CRUD 操作

### 创建（Create）

```javascript
// 插入单条文档
db.users.insertOne({
  username: "alice",
  email: "alice@example.com",
  age: 28,
  status: "active",
  created_at: new Date()
});

// 批量插入——ordered: false 时遇到错误会继续执行后续文档
db.users.insertMany([
  { username: "bob", email: "bob@example.com", age: 24, status: "active" },
  { username: "carol", email: "carol@example.com", age: 31, status: "inactive" },
  { username: "dave", email: "dave@example.com", age: 27, status: "active" }
], { ordered: false });
```

> **注意**：`ordered: true`（默认）时，插入遇到主键冲突会立即停止；`ordered: false` 会跳过错误文档继续插入，适合大批量导入。

### 读取（Read）

MongoDB 查询使用 JSON 格式的查询文档，通过操作符表达条件。

```javascript
// 等值查询
db.users.find({ status: "active" });

// 比较操作符
db.users.find({ age: { $gte: 25, $lte: 35 } });
// $gt(>) $gte(>=) $lt(<) $lte(<=) $ne(!=) $in(在集合中) $nin(不在集合中)

// 逻辑组合
db.users.find({
  $and: [
    { status: "active" },
    { age: { $gte: 25 } }
  ]
});
// 等价简写（多条件同一字段时必须用 $and）
db.users.find({ status: "active", age: { $gte: 25 } });

// 或条件
db.users.find({
  $or: [
    { age: { $lt: 20 } },
    { age: { $gt: 60 } }
  ]
});

// 数组查询
db.articles.find({ tags: "nosql" });              // 数组包含该元素
db.articles.find({ tags: { $all: ["nosql", "database"] } }); // 包含全部
db.articles.find({ tags: { $size: 3 } });         // 数组长度为 3

// 嵌套文档查询——使用点号
db.users.find({ "profile.city": "上海" });

// 正则匹配
db.users.find({ username: /^a/ });  // 以 a 开头的用户名
```

#### 投影

通过投影只返回需要的字段，减少网络传输：

```javascript
// 只返回 username 和 email（_id 默认返回，需显式排除）
db.users.find(
  { status: "active" },
  { username: 1, email: 1, _id: 0 }
);

// 排除字段
db.users.find(
  {},
  { profile: 0, created_at: 0 }
);
```

> **注意**：投影中不能同时使用包含和排除（`_id` 除外）。`{ username: 1, age: 0 }` 会报错。

### 更新（Update）

```javascript
// 更新单个文档
db.users.updateOne(
  { username: "alice" },
  { $set: { age: 29, "profile.city": "北京" } }
);

// 更新多个文档
db.users.updateMany(
  { status: "inactive" },
  { $set: { status: "active" } }
);

// 替换整个文档（保留 _id）
db.users.replaceOne(
  { username: "alice" },
  { username: "alice", email: "alice@example.com", age: 29 }
);

// 常用更新操作符
db.users.updateOne(
  { username: "alice" },
  {
    $set: { status: "active" },        // 设置字段值
    $unset: { temp_field: "" },       // 删除字段
    $inc: { login_count: 1 },         // 字段自增
    $push: { tags: "vip" },           // 数组追加元素
    $pull: { tags: "inactive" },      // 数组移除元素
    $addToSet: { tags: "premium" },    // 数组添加元素（去重）
    $rename: { old_name: "new_name" }  // 重命名字段
  }
);

// 更新不存在则插入（upsert）
db.users.updateOne(
  { username: "eve" },
  { $set: { email: "eve@example.com", age: 30 } },
  { upsert: true }
);
```

### 删除（Delete）

```javascript
// 删除匹配的文档
db.users.deleteOne({ username: "alice" });
db.users.deleteMany({ status: "inactive" });

// 删除集合中的所有文档（不删除集合本身）
db.users.deleteMany({});

// 删除整个集合
db.users.drop();

// 删除数据库
db.dropDatabase();
```

> **警告**：`deleteMany({})` 会删除所有文档，操作不可逆。生产环境务必先执行 `find()` 确认匹配范围，或先做备份。

### 事务写法

从 MongoDB 4.0 开始支持多文档 ACID 事务（需副本集环境）：

```javascript
const session = db.getMongo().startSession();
try {
  session.startTransaction();

  // 转账：从 alice 扣款
  db.accounts.updateOne(
    { name: "alice", balance: { $gte: 500 } },
    { $inc: { balance: -500 } },
    { session }
  );

  // 给 bob 加款
  db.accounts.updateOne(
    { name: "bob" },
    { $inc: { balance: 500 } },
    { session }
  );

  session.commitTransaction();
} catch (error) {
  session.abortTransaction();
  print("事务回滚: " + error.message);
} finally {
  session.endSession();
}
```

## 索引

索引是提升查询性能的关键手段。MongoDB 默认在 `_id` 上创建唯一索引。

### 索引类型

| 类型 | 适用场景 | 示例 |
| --- | --- | --- |
| 单字段索引 | 单字段等值/范围查询 | `{ username: 1 }` |
| 复合索引 | 多字段组合查询，遵循 ESR 原则 | `{ status: 1, age: -1 }` |
| 多键索引 | 数组字段 | `{ tags: 1 }` |
| 文本索引 | 全文搜索 | `{ content: "text" }` |
| 地理空间索引 | 2D/2DSphere 查询 | `{ location: "2dsphere" }` |
| TTL 索引 | 自动过期删除文档 | `{ created_at: 1 }, expireAfterSeconds: 86400 }` |
| 哈希索引 | 分片键，均匀分布 | `{ user_id: "hashed" }` |
| 唯一索引 | 唯一约束 | `{ email: 1 }, { unique: true }` |

### 创建与查看索引

```javascript
// 单字段升序索引
db.users.createIndex({ username: 1 });

// 复合索引——ESR 原则：Equal(等值) → Sort(排序) → Range(范围)
db.users.createIndex({ status: 1, age: -1 });

// 唯一索引
db.users.createIndex({ email: 1 }, { unique: true });

// TTL 索引——日志 7 天后自动删除
db.logs.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 604800 }   // 7 days
);

// 部分索引——只索引活跃用户，减小索引体积
db.users.createIndex(
  { email: 1 },
  { partialFilterExpression: { status: "active" } }
);

// 查看集合上的所有索引
db.users.getIndexes();

// 查看查询执行计划
db.users.find({ status: "active", age: { $gte: 25 } }).explain("executionStats");
```

### 复合索引的 ESR 原则

构建复合索引时，字段顺序应遵循 **E（Equal）→ S（Sort）→ R（Range）** 原则，使一个索引同时覆盖等值、排序和范围查询：

```javascript
// 查询场景：status 等值 + age 范围 + created_at 降序
// 查询语句：db.users.find({ status: "active", age: { $gte: 25 } }).sort({ created_at: -1 })

// 正确索引：Equal(status) → Range(age) → Sort(created_at)
db.users.createIndex({ status: 1, age: 1, created_at: -1 });
```

### 索引使用建议

1. **为高频查询建索引**：`find`、`sort`、`aggregate` 中出现在 `$match` 和 `$sort` 阶段的字段。
2. **避免过多索引**：每个索引都有写入和存储开销，通常单集合不超过 5-10 个索引。
3. **利用覆盖查询**：查询和投影的字段全部在索引中时，MongoDB 直接从索引返回数据，不回表。
4. **TTL 索引注意时区**：TTL 基于 UTC 时间，后台每 60 秒执行一次删除，有延迟。
5. **定期分析慢查询**：开启 `db.setProfilingLevel(1)` 记录慢查询，结合 `explain` 优化。

## 聚合管道

聚合管道是 MongoDB 的数据分析引擎，通过多个阶段对文档进行流水线式处理。

### 常用阶段

| 阶段 | 作用 | 类比 SQL |
| --- | --- | --- |
| `$match` | 过滤文档 | WHERE |
| `$group` | 分组聚合 | GROUP BY |
| `$project` | 字段投影/重塑 | SELECT |
| `$sort` | 排序 | ORDER BY |
| `$limit` / `$skip` | 分页 | LIMIT / OFFSET |
| `$lookup` | 关联其他集合 | LEFT JOIN |
| `$unwind` | 展开数组 | — |
| `$addFields` | 添加字段 | — |
| `$count` | 计数 | COUNT(*) |
| `$bucket` | 分桶统计 | — |
| `$facet` | 多管道并行 | — |

### 实战示例

```javascript
// 统计每个状态的用户数量和平均年龄
db.users.aggregate([
  { $match: { age: { $gte: 18 } } },           // 过滤成年用户
  {
    $group: {
      _id: "$status",                           // 按状态分组
      count: { $sum: 1 },                       // 每组数量
      avg_age: { $avg: "$age" },                // 平均年龄
      max_age: { $max: "$age" }                 // 最大年龄
    }
  },
  { $sort: { count: -1 } }                       // 按数量降序
]);
// 输出示例: [{ _id: "active", count: 2, avg_age: 26, max_age: 28 }, { _id: "inactive", count: 1, avg_age: 31, max_age: 31 }]
```

```javascript
// 关联查询：查找每个订单的商品详细信息
db.orders.aggregate([
  { $match: { status: "pending" } },
  { $unwind: "$items" },                         // 展开商品数组
  {
    $lookup: {
      from: "products",
      localField: "items.product_id",
      foreignField: "_id",
      as: "product"
    }
  },
  { $unwind: "$product" },                       // 展开 lookup 结果数组
  {
    $project: {
      order_no: 1,
      product_name: "$product.name",
      quantity: "$items.quantity",
      line_total: { $multiply: ["$items.quantity", "$items.unit_price"] }
    }
  },
  { $sort: { order_no: 1, product_name: 1 } }
]);
```

```javascript
// 按年龄段分桶统计
db.users.aggregate([
  {
    $bucket: {
      groupBy: "$age",
      boundaries: [0, 18, 30, 45, 60, 100],
      default: "other",
      output: {
        count: { $sum: 1 },
        usernames: { $push: "$username" }
      }
    }
  }
]);
```

> **性能提示**：将 `$match` 放在管道最前面，尽早减少文档数量。聚合管道各阶段之间不能利用索引（除 `$match` 和 `$sort` 首阶段外），因此早期过滤至关重要。

## 副本集与分片

### 副本集（Replica Set）

副本集由一组维护相同数据副本的 MongoDB 实例组成，提供高可用和数据冗余。

```
        ┌──────────────────┐
        │   Replica Set    │
        │                  │
        │  ┌────────────┐  │
        │  │  Primary   │  │  读写请求
        │  └─────┬──────┘  │
        │        │ oplog   │
        │   ┌────┴────┐    │
        │  ▼         ▼     │
        │ ┌─────┐ ┌─────┐  │
        │ │Sec-1│ │Sec-2│  │  同步数据，可承担读请求
        │ └─────┘ └─────┘  │
        └──────────────────┘
```

- **Primary**：唯一接受写操作的节点。
- **Secondary**：从 Primary 的 oplog 异步复制数据，可配置为可读。
- **选举**：Primary 故障时，Secondary 通过 Raft 协议自动选举新 Primary（通常需多数派节点存活）。
- **最小配置**：3 个投票节点（如 1 Primary + 2 Secondary），或 1 Primary + 1 Secondary + 1 Arbiter（仲裁节点不存数据）。

```bash
# 启动副本集（在 mongosh 中初始化）
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo1:27017" },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" }
  ]
});

# 查看副本集状态
rs.status();

# 设置 Secondary 可读
db.getMongo().setReadPref("secondaryPreferred");
```

### 分片（Sharding）

分片用于在多台机器上水平拆分数据，突破单机硬件限制。

| 组件 | 职责 |
| --- | --- |
| `mongos` | 路由服务，接收客户端请求并转发到正确的分片 |
| Config Server | 存储集群元数据和分片路由表 |
| Shard | 实际存储数据的 MongoDB 实例（通常是副本集） |
| 分片键 | 决定文档分布到哪个分片的字段 |

#### 分片键选择

| 策略 | 特点 | 适用场景 |
| --- | --- | --- |
| 范围分片 | 按键值范围拆分，可能数据倾斜 | 范围查询、时间序列 |
| 哈希分片 | 均匀分布，不支持范围查询 | 随机写入、负载均衡 |
| 区域分片 | 按标签指定数据存放的分片 | 地理隔离、冷热分离 |

```bash
# 启用分片
sh.enableSharding("shop");

# 对集合分片（需先在分片键上建索引）
db.orders.createIndex({ order_no: "hashed" });
sh.shardCollection("shop.orders", { order_no: "hashed" });

# 查看分片状态
sh.status();
```

> **注意**：分片键一旦设定无法修改（MongoDB 5.0 后可对未分片集合重新分片）。选错分片键是分片集群最常见的问题，可能导致数据分布不均或产生大量跨分片查询。

## 性能优化

### 查询优化

1. **使用 `explain()` 分析执行计划**：

```javascript
// 查看是否走了索引、扫描了多少文档
db.users.find({ status: "active" }).explain("executionStats");

// 关键指标：
// totalDocsExamined — 扫描的文档数，应接近返回数
// executionTimeMillis — 执行时间
// winningPlan.stage — "IXSCAN" 表示使用了索引，"COLLSCAN" 表示全表扫描
```

2. **避免全表扫描**：查询条件没有索引支持时会扫描整个集合，数据量大时严重影响性能。
3. **限制结果集**：始终使用 `limit()` 限制返回数量，分页用 `skip + limit` 或基于游标的分页。

```javascript
// 传统分页（skip 越大越慢）
db.users.find().skip(10000).limit(20);

// 游标分页（性能稳定）
// 记录上一页最后一条文档的 _id，下次查询从该点开始
const last_id = ObjectId("65a1b2c3d4e5f6a7b8c9d0e1");
db.users.find({ _id: { $gt: last_id } }).limit(20);
```

### 写入优化

| 技术 | 效果 | 适用 |
| --- | --- | --- |
| 批量写入 (`insertMany`) | 减少网络往返 | 批量导入 |
| `ordered: false` | 并行插入，不因单条失败中断 | 容忍部分失败的批量导入 |
| 写关注降级 (`w: 1`) | 降低写入确认等待 | 非关键日志数据 |
| 无索引集合 | 插入时不维护索引 | 临时数据、缓冲表 |

### 存储与内存

- **WiredTiger 存储引擎**（默认）：支持 Snappy 压缩和块级并发控制。
- **工作集**：MongoDB 倾向于将热数据保留在内存中，确保 ` WiredTiger Cache` 能容纳常用索引和数据。
- **定期压缩**：频繁删除/更新会产生磁盘碎片，使用 `compact` 命令回收空间（需排他锁）。

```javascript
// 查看存储统计
db.users.stats();
db.stats();
```

## 安全

### 认证与授权

```bash
# 启用访问控制后，必须先创建管理员用户
use admin
db.createUser({
  user: "admin",
  pwd: passwordPrompt(),       # 交互式输入密码
  roles: [
    { role: "userAdminAnyDatabase", db: "admin" },
    { role: "readWriteAnyDatabase", db: "admin" }
  ]
});
```

### 常用内置角色

| 角色 | 权限 |
| --- | --- |
| `read` | 读取指定数据库 |
| `readWrite` | 读写指定数据库 |
| `dbAdmin` | 管理指定数据库（索引、压缩、统计） |
| `userAdmin` | 管理指定数据库的用户 |
| `readAnyDatabase` | 读取所有数据库（仅 admin） |
| `root` | 超级管理员 |

### 连接字符串

```bash
# 单节点
mongodb://user:password@host:27017/database?authSource=admin

# 副本集
mongodb://user:password@mongo1:27017,mongo2:27017,mongo3:27017/database?replicaSet=rs0&authSource=admin

# 分片集群（连接 mongos）
mongodb://user:password@mongos1:27017,mongos2:27017/database?authSource=admin
```

### 安全最佳实践

1. 生产环境**必须启用认证**（`security.authorization: enabled`）。
2. 使用 TLS/SSL 加密客户端到数据库的通信。
3. 最小权限原则：应用账户只授予 `readWrite`，不使用 `root`。
4. 网络隔离：MongoDB 实例不直接暴露在公网，通过 VPC 或防火墙限制。
5. 密钥文件认证：副本集和分片集群内部节点间使用 KeyFile 认证。

## 常见模式与最佳实践

### 时间序列数据

```javascript
// 将同一设备同一小时的指标聚合到单个文档，减少文档数量
db.metrics.insertOne({
  device_id: "sensor-001",
  timestamp: ISODate("2026-08-23T10:00:00Z"),  // 小时整点
  granularity: "hourly",
  values: [
    { t: 0, temp: 22.5 },    // 分钟 0
    { t: 1, temp: 22.6 },    // 分钟 1
    // ...
    { t: 59, temp: 23.1 }    // 分钟 59
  ],
  // 预聚合统计
  min_temp: 22.5,
  max_temp: 23.1,
  avg_temp: 22.8
});

// 创建 TTL 索引自动清理历史数据（保留 30 天）
db.metrics.createIndex(
  { timestamp: 1 },
  { expireAfterSeconds: 2592000 }
);
```

### 多态查询模式

利用集合的无模式特性，在同类文档中使用 `type` 字段区分：

```javascript
// 同一 notifications 集合存储不同通知类型
db.notifications.insertMany([
  { type: "email", to: "alice@example.com", subject: "Welcome", sent: true },
  { type: "sms", to: "13800138000", body: "验证码: 1234", sent: true },
  { type: "push", device_token: "abc123", title: "New message", sent: false }
]);

// 查询时按类型过滤
db.notifications.find({ type: "email", sent: true });
```

### 物化视图模式

将聚合结果写入独立集合，避免每次实时计算：

```javascript
// 使用 $merge 将聚合结果写入汇总集合
db.orders.aggregate([
  {
    $group: {
      _id: { customer_id: "$customer_id", month: { $month: "$created_at" } },
      total: { $sum: "$total" },
      count: { $sum: 1 }
    }
  },
  {
    $merge: {
      into: "order_monthly_summary",
      whenMatched: "replace",
      whenNotMatched: "insert"
    }
  }
]);

// 查询汇总结果，毫秒级响应
db.order_monthly_summary.find({ "customer_id": "C001" });
```

## 与关系型数据库对比

| 维度 | MongoDB | 关系型数据库（如 [[postgresql|PostgreSQL]]） |
| --- | --- | --- |
| 数据模型 | 文档（BSON），灵活模式 | 表-行-列，严格模式 |
| 查询语言 | MongoDB Query Language + 聚合管道 | 标准 SQL |
| Join | `$lookup`，性能不如关系型 | 原生 JOIN，优化成熟 |
| 事务 | 4.0+ 支持多文档 ACID（需副本集） | 原生 ACID，隔离级别丰富 |
| 扩展 | 分片水平扩展，天然分布式 | 需中间件或分布式方案 |
| Schema 变更 | 无需迁移，直接添加字段 | 需 `ALTER TABLE`，可能锁表 |
| 适用场景 | 内容管理、用户画像、IoT、实时分析 | 强一致性交易、复杂关联查询 |

## 常见问题

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| 查询慢 | 没有索引或索引选择率低 | `explain()` 分析，创建合适索引 |
| 写入阻塞 | 索引过多或写入关注过高 | 精简索引，评估写关注级别 |
| 文档超 16MB | 嵌入了大量子文档 | 拆分到独立集合并引用 |
| 副本集延迟大 | Secondary 写入跟不上 | 检查网络延迟、磁盘 I/O、硬件配置 |
| 分片不均匀 | 分片键选择不当 | 使用哈希分片或调整区域 |
| 内存不足 | 工作集超出物理内存 | 增加内存、优化查询减少扫描范围 |

## See Also

- [[postgresql|PostgreSQL]] — 关系型数据库对比参考
- [[mysql|MySQL 深入学习]] — 关系型数据库基础
- [MongoDB 官方文档](https://www.mongodb.com/docs/manual/)
- [MongoDB University](https://learn.mongodb.com/) — 官方免费课程
