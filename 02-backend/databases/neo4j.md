---
title: Neo4j 图数据库
description: 图数据库基本原理、Neo4j 安装部署、Cypher 查询语言、数据建模与 Python 驱动实战
tags:
  - database
  - neo4j
  - graph-database
  - cypher
date: 2026-11-11
---

# Neo4j 图数据库

## 概述

Neo4j 是目前最流行的**原生图数据库**，用"节点 + 关系"的方式存储数据。它解决的核心痛点是：**当数据之间的关系本身比数据更重要时，关系型数据库的多表 JOIN 会变得低效且难以表达**。

典型场景：社交网络（"朋友的朋友"）、欺诈检测（资金链路追踪）、知识图谱、
推荐系统（"买了 A 的人也买了 B"）、权限继承等——这些查询的共同特点是**深度遍历**：
在 SQL 里需要 5 层以上自连接，而在 Cypher 里一行 `()-[:FRIEND*1..5]->()` 就能搞定，
且性能不随数据总量劣化（原生的邻接存储使遍历代价只与"走过的边数"相关，而非全表扫描）。

> 选型时先想清楚：数据之间的关系本身是不是查询的主角。是 → 图数据库；否 → 继续用关系型/文档型。

## 前置知识

- 关系型数据库基础：理解表、主键、JOIN，才能体会图模型的差异 → [[mysql|MySQL 技术指南]]、[[postgresql|PostgreSQL 基础]]
- [图论基础](https://zh.wikipedia.org/wiki/图论)：知道"顶点、边、路径"即可
- Docker 基础（本文部署方式）→ [[docker|Docker]]、[[docker-compose|Docker Compose]]

## 核心概念

### 图模型：节点、关系、标签、属性

Neo4j 的数据模型只有两个一等公民：

| 概念 | 类比关系型数据库 | 说明 |
|------|-----------------|------|
| **节点 (Node)** | 一行记录 | 实体，如一个人、一部电影 |
| **标签 (Label)** | 表名 | 节点的类型，一个节点可以有多个标签 |
| **关系 (Relationship)** | 外键 + JOIN | 连接两个节点的有向边，**必须有类型且方向唯一** |
| **属性 (Property)** | 列 | 键值对，节点和关系都可以挂属性 |

与关系型数据库的关键差异：

1. **关系是一等公民**：不是运行时 JOIN 出来的，而是物理存储的连接，遍历关系近似指针跳转
2. **Schema 自由**：属性可以按需增减，没有 `ALTER TABLE` 的心理负担（代价是没有强约束，需要自律）
3. **遍历代价恒定**：查询成本只与遍历的子图大小有关，与总数据量无关

### 图模型 vs 关系模型 vs 文档模型

| 维度 | 关系型 (MySQL/PG) | 文档型 ([[mongodb|MongoDB]]) | 图 (Neo4j) |
|------|------------------|-----------------|-----------|
| 数据单元 | 行 | JSON 文档 | 节点 / 关系 |
| 关系表达 | 外键 + 运行时 JOIN | 内嵌或引用 | 物理存储的边 |
| 深层遍历 | N 层需 N-1 次 JOIN，性能急剧下降 | 多次应用层查询 | 一次模式匹配，代价稳定 |
| Schema | 强约束 | 灵活 | 灵活（可选约束） |
| 典型场景 | 事务、报表、结构稳定 | 读多写少、单文档聚合 | 关系密集、深度遍历 |

> **选型经验**：如果 80% 的查询都要 JOIN 3 张以上的表，或业务频繁问"X 和 Y 之间有什么联系"，
> 值得认真评估图数据库；如果只是普通 CRUD，继续用 MySQL/PostgreSQL
> （`WITH RECURSIVE` 足以应付浅层递归）。

## 安装部署

### Docker 单机部署（开发/学习推荐）

```bash
# 映射 Browser(7474) 与 Bolt(7687) 端口，数据持久化到命名卷
# NEO4J_AUTH 格式为 用户名/密码；设为 none 则免密（仅限本地调试，生产严禁）
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  -v neo4j_data:/data \
  neo4j:5-community
```

启动后：

- 浏览器访问 `http://localhost:7474` → **Neo4j Browser**，可视化查询界面
- 程序连接 `bolt://localhost:7687`（Bolt 二进制协议，比 HTTP 接口快得多）

### Docker Compose 部署

```yaml
services:
  neo4j:
    image: neo4j:5-community
    container_name: neo4j
    ports:
      - "7474:7474"   # Browser HTTP
      - "7687:7687"   # Bolt
    environment:
      NEO4J_AUTH: neo4j/your_password
      # page cache 建议设为数据集大小的 1.5-2 倍，决定遍历性能
      NEO4J_dbms_memory_pagecache_size: 1G
      # heap 决定排序、聚合等查询处理的上限
      NEO4J_dbms_memory_heap_max__size: 1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

volumes:
  neo4j_data:
  neo4j_logs:
```

> **内存原则**：两者之和不要超过容器内存限制的 75%，否则会被 OOM Killer 光顾。

### 加载官方示例数据

在 Browser 中执行以下命令，导入经典的"电影"数据集（本文 Cypher 示例均基于它）：

```cypher
:play movie-graph
```

按页面提示逐步执行即可得到 `Person`、`Movie` 两类节点和 `ACTED_IN`、`DIRECTED` 等关系。

## Cypher 查询语言

Cypher 是 Neo4j 的声明式图查询语言，核心思想是**"ASCII Art 画图案"**——怎么画，怎么查。

### 模式语法速查

| 模式 | 含义 |
|------|------|
| `(a:Person)` | 变量 `a`，标签为 `Person` 的节点 |
| `(a:Person {name: "Tom Hanks"})` | 带属性匹配的节点 |
| `()-[:ACTED_IN]->(m:Movie)` | 一条 `ACTED_IN` 类型的有向关系 |
| `(a)-[:FRIEND*1..3]->(b)` | 可变长度路径：1 到 3 跳 |
| `(a)-[:ACTED_IN]-(b)` | 忽略方向 |
| `shortestPath((a)-[*]-(b))` | 两点间最短路径 |

### 增删改查（CRUD）

```cypher
// 建节点：MERGE 是"有则复用，无则创建"，幂等且防重复
MERGE (p:Person {name: "Tom Hanks"})
SET p.born = 1956, p.roles = ["actor", "producer"]
RETURN p;

// 建关系：先 MERGE 两端节点，再 MERGE 关系（方向决定语义！）
MATCH (p:Person {name: "Tom Hanks"}), (m:Movie {title: "Forrest Gump"})
MERGE (p)-[r:ACTED_IN {roles: ["Forrest"]}]->(m)
RETURN p, r, m;

// 查询：Tom Hanks 演过的电影及其导演
MATCH (p:Person {name: "Tom Hanks"})-[:ACTED_IN]->(m:Movie)
MATCH (d:Person)-[:DIRECTED]->(m)
RETURN m.title AS movie, collect(d.name) AS directors;

// 更新：SET 支持属性、标签、+= 增量合并
MATCH (p:Person {name: "Tom Hanks"})
SET p.oscars = 2
RETURN p;

// 删除：先 DELETE 关系和节点（DETACH 会先断开所有关系）
MATCH (m:Movie {title: "Cloud Atlas"})
DETACH DELETE m;
```

> **MERGE vs CREATE**：`CREATE` 无条件新建，跑两次脚本就产生重复节点；导入脚本一律用 `MERGE`，并保证 MERGE 的属性集上有唯一约束（见下文索引一节）。

### 经典查询：可变长度路径

```cypher
// "朋友的朋友"：找 Tom Hanks 通过 2-4 层 ACTED_IN 认识的演员
MATCH (p:Person {name: "Tom Hanks"})-[:ACTED_IN]->()<-[:ACTED_IN]-(coactor)-[:ACTED_IN]->()<-[:ACTED_IN]-(fof:Person)
WHERE fof <> p
RETURN fof.name, count(*) AS commonMovies
ORDER BY commonMovies DESC
LIMIT 10;

// 可变长度写法：路径 1..3 跳
MATCH path = (p:Person {name: "Tom Hanks"})-[:KNOWS*1..3]->(target:Person)
RETURN [n IN nodes(path) | n.name] AS chain;
```

### 聚合与分组

```cypher
// 每部电影的演员数量（count 自动分组，无需 GROUP BY）
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
RETURN m.title, count(p) AS actors
ORDER BY actors DESC
LIMIT 5;

// WITH：流水线式的中间结果传递
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
WITH m, count(p) AS actors
WHERE actors >= 5
RETURN m.title, actors;
```

`WITH` 是 Cypher 的灵魂——相当于管道，把上一步的结果裁剪、过滤、聚合后传给下一步，避免一个巨型 MATCH 不可读、也不可优化。

## 数据建模与性能

### 建模方法：先问题后模型

图建模和 ER 建模思路相反：**从查询出发倒推结构**。

1. 写下业务最关心的 10 条查询
2. 每个实体 → 一个标签；实体间回答查询所需的关联 → 一种关系类型
3. 把"用于定位实体的属性"建索引；把"遍历时才需要的属性"留在节点上

### 索引与约束

```cypher
// 唯一约束 = 索引 + 唯一校验，MERGE 的最佳搭档
CREATE CONSTRAINT person_name IF NOT EXISTS
FOR (p:Person) REQUIRE p.name IS UNIQUE;

// 普通范围索引（等值 + 范围查询）
CREATE INDEX movie_title IF NOT EXISTS
FOR (m:Movie) ON (m.title);

// 全文索引：LIKE '%xx%' 这类模糊查询必须靠它
CREATE FULLTEXT INDEX movie_desc IF NOT EXISTS
FOR (m:Movie) ON EACH [m.title, m.tagline];

// 查看已有索引
SHOW INDEXES;
```

| 查询方式 | 是否走索引 |
|---------|-----------|
| `MATCH (p:Person {name: "X"})` | 是（有索引时） |
| `WHERE p.name STARTS WITH "X"` | 是（范围索引） |
| `WHERE p.name CONTAINS "X"` | 否 → 全节点扫描，需全文索引 |
| `MATCH (p:Person)` 之后过滤 | 否 → 扫描所有 Person |

### 性能实践

1. **让模式尽量具体**：标签、关系类型、方向都写全。`(p)-[]->()` 会让引擎扫描所有关系类型
2. **有索引的锚点放前面**：从有索引匹配的节点开始展开，把无界遍历放在查询末端
3. **EXPLAIN / PROFILE 分析**：`PROFILE` 前置查看实际行数，发现某一步 Rows 暴涨就是优化点
4. **避免大结果集的 `*` 无界深度**：`-[*]->` 理论上会走遍全图，务必限定 `*1..3` 并配合 `WHERE` 剪枝

## Python 驱动实战

```bash
pip install neo4j
```

```python
from neo4j import GraphDatabase


class MovieRepo:
    def __init__(self, uri, user, password):
        # 驱动是线程安全的，全局只创建一次
        # 连接池默认 max_connection_pool_size=100
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_actor(self, name: str, born: int):
        # 会话绑定一个数据库；查询用参数占位符 $name 防注入
        # execute_write 自动开启事务并在异常时回滚
        with self.driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MERGE (p:Person {name: $name})
                    SET p.born = $born
                    """,
                    name=name,
                    born=born,
                ).consume()
            )

    def find_coactors(self, name: str) -> list[str]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (:Person {name: $name})-[:ACTED_IN]->()<-[:ACTED_IN]-(coactor:Person)
                RETURN DISTINCT coactor.name AS name
                ORDER BY name
                """,
                name=name,
            )
            return [record["name"] for record in result]


if __name__ == "__main__":
    repo = MovieRepo("bolt://localhost:7687", "neo4j", "your_password")
    try:
        coactors = repo.find_coactors("Tom Hanks")
        print(f"co-actors: {coactors}")
    finally:
        # driver 持有连接池，不关闭会在进程退出前泄漏连接
        repo.close()
```

> **异步场景**：高并发服务用 `neo4j.AsyncGraphDatabase.driver()`，API 与同步版一致（方法前缀 `async with` / `await`）。

## 数据导入

### LOAD CSV：小批量导入

```cypher
// CSV 第一行为表头：name,born,title,roles
// 批量导入要加 USING PERIODIC COMMIT，避免事务过大撑爆内存
LOAD CSV WITH HEADERS FROM 'file:///actors.csv' AS row
CALL {
  WITH row
  MERGE (p:Person {name: row.name})
  MERGE (m:Movie {title: row.title})
  MERGE (p)-[:ACTED_IN {roles: split(row.roles, '|')}]->(m)
} IN TRANSACTIONS OF 1000 ROWS
```

`file:///` 对应容器内 `/data` 目录（挂载卷即主机目录），远程 CSV 可用 `https://` 直链。

### neo4j-admin：大规模导入

百万级以上节点使用 `neo4j-admin database import full`（离线工具，导入前数据库必须为空，速度快一个数量级），需要把节点和关系分别导出成 CSV。日常几万~几十万级数据用 `LOAD CSV` 足够。

## 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| 图数据库不用建索引 | 无索引时按属性查节点是全库扫描 | 对所有"入口属性"建唯一约束或索引 |
| 关系方向无所谓 | 方向参与物理存储和查询匹配 | 建模时明确方向；查询时可显式忽略 `-[r]-`，但写入必须有方向 |
| 把一切属性塞进节点 | 遍历时反序列化大属性浪费内存 | 大文本等"叶子属性"可拆成独立节点 `(:Text)`，需要时才取 |
| 用 CREATE 导入数据 | 重跑一次产生全量重复 | 用 MERGE + 唯一约束保证幂等 |
| Cypher 写完不看执行计划 | 一个无界 `*` 跳性能崩塌 | 上线前 `PROFILE` 检查每步 Rows |

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 查询超时，CPU 飙满 | 无索引的属性匹配或无界深度遍历 | `PROFILE` 定位；建索引；限定 `*1..3` 跳 |
| `ServiceUnavailable: connection refused` | Bolt 端口未映射或容器未就绪 | 确认 7687 映射；驱动首次连接自带重试 |
| `Neo.ClientError.Schema.ConstraintValidation` | 违反唯一约束（MERGE 竞态） | 唯一约束 + MERGE 是正确组合，说明拦截了重复数据 |
| 导入 CSV 内存溢出 | 单事务过大 | `IN TRANSACTIONS OF 1000 ROWS` 分批提交 |
| Browser 能连，程序连不上 | 程序用了 http:// 而非 bolt:// | Python/Java 驱动一律走 `bolt://` 或 `neo4j://` |

## 相关概念

- 与 [[mongodb|MongoDB]] 的对比：同为 Schema 自由，文档型适合"单实体聚合读"，图适合"关系遍历读"
- 与 [[postgresql|PostgreSQL]] 的关系：PG 可用 `WITH RECURSIVE` 或 Apache AGE 扩展做浅层图查询；深度遍历和大规模图才需要专职图库
- 部署运维相关：[[docker|Docker]]、[[docker-compose|Docker Compose]]

## 参考

- [Neo4j 官方文档](https://neo4j.com/docs/)
- [Cypher 查询语言手册](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [GraphAcademy 免费官方课程](https://graphacademy.neo4j.com/)
