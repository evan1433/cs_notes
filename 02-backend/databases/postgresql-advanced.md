---
title: PostgreSQL 特性与实战
description: PostgreSQL 高级特性详解：JSONB、全文检索、窗口函数、分区表、MVCC、复制与高可用、性能调优等。
tags:
  - database
  - postgresql
  - sql
  - advanced
date: 2026-08-28
---

# PostgreSQL 特性与实战

> 基础篇（SQL 分类、约束、事务、索引入门）见 [[postgresql|PostgreSQL 基础]]。
> 本文聚焦 PostgreSQL 区别于普通关系型数据库的**高级特性**与**实战用法**，面向系统分析师备考与日常开发。

## 特性总览

PostgreSQL（简称 PG / Postgres）是功能最完善的开源关系型数据库，核心优势：

| 特性 | 说明 |
| --- | --- |
| MVCC | 读不阻塞写、写不阻塞读，多版本并发控制 |
| 丰富数据类型 | `jsonb`、数组、范围、UUID、网络、几何、枚举等原生支持 |
| 扩展生态 | 300+ 扩展：`postgis`、`pgvector`、`pg_trgm`、`postgres_fdw` 等 |
| 高级 SQL | 窗口函数、递归 CTE、物化视图、`ON CONFLICT`、`RETURNING` |
| 数据完整性 | 约束、触发器、排他约束、行级安全（RLS） |
| 高可用 | 流复制、逻辑复制、时间点恢复（PITR）、在线升级 |
| 许可证 | PostgreSQL License（类 BSD），可自由商用，无供应商锁定 |

**版本现状**（2026-08）：当前稳定版为 PostgreSQL 18（2025-09 发布）。18 的关键新特性：异步 I/O（AIO，读性能最高提升 3 倍）、`uuidv7()` 时间有序 UUID、虚拟生成列（默认）、逻辑复制并行流式应用（默认）、OAuth 2.0 认证、`initdb` 默认启用页校验和。

## 安装与连接

### 快速启动（Docker）

```bash
# 启动 PG 18 容器
docker run -d --name pg18 \
  -e POSTGRES_USER=app -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=app_db \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:18

# 进入容器内的 psql
docker exec -it pg18 psql -U app -d app_db
```

### 连接方式

连接串（libpq URL）统一格式：

```text
postgresql://user:password@host:5432/dbname?sslmode=disable
jdbc:postgresql://host:5432/dbname            # JDBC
```

常用客户端/驱动：

| 语言 | 推荐驱动 | 示例 |
| --- | --- | --- |
| Python | `psycopg`（v3） | `psycopg.connect("postgresql://app:secret@localhost/app_db")` |
| Node.js | `pg`（node-postgres） | `new Client({ connectionString })` |
| Java | `org.postgresql:postgresql` | JDBC 驱动 |
| Go | `pgx` | `pgxpool.New(ctx, url)` |

### psql 常用元命令

psql 是 PG 自带交互式客户端，以反斜杠开头的都是客户端命令（非 SQL）：

| 命令 | 作用 |
| --- | --- |
| `\l` | 列出所有数据库 |
| `\c dbname` | 切换数据库 |
| `\dt` / `\di` / `\dv` | 列出表 / 索引 / 视图 |
| `\d 表名` / `\d+ 表名` | 查看表结构 / 详细结构 |
| `\x` | 切换纵向显示（宽表友好） |
| `\timing` | 显示每条 SQL 耗时 |
| `\i file.sql` | 执行 SQL 脚本文件 |
| `\copy 表 TO 'a.csv' CSV HEADER` | 客户端侧导入导出（无需超管） |
| `\q` | 退出 |

## 高级数据类型

除常规的 `numeric`、`text`、`timestamptz` 外，PG 原生支持以下类型：

### UUID

```sql
-- PG 13+ 内置 gen_random_uuid()；PG 18 新增 uuidv4() 别名与 uuidv7()
SELECT gen_random_uuid();

-- 时间有序 UUID：随机值按时间排序，B-tree 索引写入友好（推荐做主键）
CREATE TABLE sessions (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    created_at timestamptz NOT NULL DEFAULT now()
);
```

> 随机 UUID（v4）做主键会导致索引页频繁分裂；`uuidv7()` 内嵌毫秒时间戳，新行总是插入索引末尾，高写入场景更优。

### 数组

```sql
CREATE TABLE articles (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL,
    tags text[] DEFAULT '{}'
);

INSERT INTO articles (title, tags) VALUES ('PG 特性', ARRAY['database', 'postgresql']);

-- 查询包含某标签的文章（配合 GIN 索引）
SELECT * FROM articles WHERE tags @> ARRAY['database'];
CREATE INDEX ON articles USING gin (tags);
```

### 范围类型

用于表示区间：`int4range`、`numrange`、`daterange`、`tsrange`（时间范围）等。

```sql
CREATE TABLE room_bookings (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id int NOT NULL,
    during tsrange NOT NULL
);

-- 时间段是否重叠（需要 GiST 索引 + 排他约束）
CREATE INDEX ON room_bookings USING gist (during);

ALTER TABLE room_bookings ADD CONSTRAINT no_overlap
    EXCLUDE USING gist (room_id WITH =, during WITH &&);
```

### 其他常用类型

| 类型 | 用途 |
| --- | --- |
| `inet` / `cidr` | IPv4/IPv6 地址，支持 `>>=` 子网包含判断 |
| `macaddr` | MAC 地址 |
| `enum`（`CREATE TYPE mood AS ENUM(...)`） | 枚举，值的顺序固定 |
| `hstore` | key-value 单列存储（轻量，优先考虑 jsonb） |
| `bit varying` | 位串 |
| 复合类型（`CREATE TYPE`） | 表或结构体类型的列 |

## JSONB 与文档数据

`jsonb` 是 PG 最出名的特性：在关系表中直接存文档，且可建索引、可被 SQL 精确查询。

### json vs jsonb

- `json`：原样保存文本，保留重复键与空白，**无索引**，仅适合原样存取。
- `jsonb`：解析后二进制存储，键去重、值重排，支持 GIN 索引与丰富操作符，**日常首选**。

### 核心操作符

| 操作符 | 含义 | 示例 |
| --- | --- | --- |
| `->` | 取键/下标，结果为 jsonb | `data->'user'` |
| `->>` | 取键/下标，结果为 text | `data->>'name'` |
| `#>` / `#>>` | 按路径取（jsonb/text） | `data #> '{user,email}'` |
| `@>` | 左侧包含右侧（jsonb 包含） | `data @> '{"role": "admin"}'` |
| `?` / `?|` / `?&` | 顶层键存在 / 任一 / 全部 | `data ? 'email'` |
| `||` | 合并两个 jsonb | `data || '{"age": 30}'::jsonb` |
| `-` | 删除键 | `data - 'password'` |

### 实战示例

```sql
CREATE TABLE events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO events (payload) VALUES
('{"event_type": "login", "user": {"id": 1, "name": "alice"}, "ip": "10.0.0.1"}'),
('{"event_type": "purchase", "amount": 99.9, "user": {"id": 2, "name": "bob"}}');

-- 条件查询 + 投影
SELECT payload->>'event_type' AS event,
       payload #>> '{user,name}' AS user_name
FROM events
WHERE payload @> '{"event_type": "login"}';

-- 更新嵌套字段：jsonb_set 按路径改写
UPDATE events
SET payload = jsonb_set(payload, '{user,name}', '"alice_new"')
WHERE payload->'user'->>'id' = '1';

-- SQL/JSON 路径查询（PG 12+）
SELECT jsonb_path_query(payload, '$.user.name')
FROM events
WHERE jsonb_path_exists(payload, '$.event_type ? (@ == "purchase")');

-- 顶层键索引：GIN 默认（推荐 jsonb_path_ops 更小更快）
CREATE INDEX idx_events_payload_gin ON events USING gin (payload jsonb_path_ops);
```

> 索引用 `jsonb_path_ops` 只支持 `@>` 包含查询，但索引更小、更快；需要 `?`、`?|` 等操作符时用默认 GIN。

## 全文检索

PG 内置全文检索（Full-Text Search，FTS），无需外部搜索引擎即可实现分词与相关性排序。

### 核心概念

- `tsvector`：分词后的文档向量。
- `tsquery`：查询表达式（`&` 与、`|` 或、`!` 非、`<->` 相邻）。
- `@@`：匹配操作符。

```sql
-- 基本用法
SELECT to_tsvector('english', 'The quick brown fox jumps over the lazy dog')
       @@ to_tsquery('english', 'fox & dog');   -- true

-- 建表 + GIN 索引
CREATE TABLE posts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL,
    body text NOT NULL
);

CREATE INDEX idx_posts_fts ON posts
    USING gin (to_tsvector('english', title || ' ' || body));

-- 查询 + 相关性排序 + 高亮
SELECT id, ts_headline('english', body, query, 'StartSel=<b>, StopSel=</b>') AS snippet
FROM posts, to_tsquery('english', 'postgres & index') AS query
WHERE to_tsvector('english', title || ' ' || body) @@ query
ORDER BY ts_rank(to_tsvector('english', title || ' ' || body), query) DESC;
```

### 中文检索

默认 parser 不切分中文（连续汉字被当作一个 token），需要扩展：

```sql
-- 方案一：zhparser（依赖 SCWS 分词）
CREATE EXTENSION zhparser;
CREATE TEXT SEARCH CONFIGURATION zh (PARSER = zhparser);
ALTER TEXT SEARCH CONFIGURATION zh ADD MAPPING FOR n,v,a,i,e,l WITH simple;

SELECT to_tsvector('zh', 'PostgreSQL 是一款功能完善的开源数据库');

-- 方案二：pg_jieba（结巴分词，无需编译 SCWS）
CREATE EXTENSION pg_jieba;
SELECT to_tsvector('jiebacfg', 'PostgreSQL 是一款功能完善的开源数据库');
```

## 窗口函数

窗口函数在不合并行的前提下，对每组行做计算，是“分组 Top-N”“同比环比”“去重保留最新”等场景的标准解法。

```sql
-- 语法：函数() OVER (PARTITION BY 分组 ORDER BY 排序 [帧定义])
SELECT employee_id, department_id, salary,
       rank()       OVER (PARTITION BY department_id ORDER BY salary DESC) AS rk,
       row_number() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rn,
       dense_rank() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dr
FROM employees;
```

常用窗口函数：

| 函数 | 作用 |
| --- | --- |
| `row_number()` | 组内行号（不重复） |
| `rank()` | 排名（并列占位，有空洞） |
| `dense_rank()` | 排名（并列不占位，无空洞） |
| `ntile(n)` | 平均分桶 |
| `lag(col, n)` / `lead(col, n)` | 取前/后第 n 行的值（环比、同比） |
| `first_value` / `last_value` | 组内首/尾值 |
| `sum() over (...)` | 累计求和（滚动聚合） |

```sql
-- 典型场景 1：按用户去重，保留最新一条
WITH ranked AS (
    SELECT *, row_number() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
    FROM login_records
)
DELETE FROM login_records WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

-- 典型场景 2：月度累计销售额
SELECT month,
       sum(amount) AS monthly_amount,
       sum(sum(amount)) OVER (ORDER BY month) AS running_total
FROM sales
GROUP BY month;
```

## 递归查询（WITH RECURSIVE）

处理树形/图结构（组织架构、菜单、BOM、评论楼中楼）的利器。

```sql
CREATE TABLE orgs (
    id bigint PRIMARY KEY,
    name text NOT NULL,
    parent_id bigint REFERENCES orgs (id)
);

-- 递归展开整棵树：顶层（parent_id 为空）作为锚点，逐层 UNION ALL 向下
WITH RECURSIVE org_tree AS (
    SELECT id, name, parent_id, 1 AS depth, ARRAY[id] AS path
    FROM orgs WHERE parent_id IS NULL
  UNION ALL
    SELECT o.id, o.name, o.parent_id, t.depth + 1, t.path || o.id
    FROM orgs o
    JOIN org_tree t ON o.parent_id = t.id
)
SELECT id, name, depth, path
FROM org_tree
ORDER BY path;
```

要点：递归部分必须 `UNION ALL`（`UNION` 会去重并引入排序开销）；注意限制深度防止无限递归。

## 视图与物化视图

```sql
-- 普通视图：只是保存的查询，不占存储，实时反映底层数据
CREATE VIEW v_employee_dept AS
SELECT e.id, e.name AS employee, d.name AS department
FROM employees e JOIN departments d ON d.id = e.department_id;

-- 物化视图：结果物理存储，查询快但数据是快照
CREATE MATERIALIZED VIEW mv_department_stats AS
SELECT d.name, count(*) AS employee_count, sum(e.salary) AS total_salary
FROM departments d JOIN employees e ON e.department_id = d.id
GROUP BY d.name
WITH DATA;

-- 刷新：CONCURRENTLY 不阻塞读，但需要唯一索引
CREATE UNIQUE INDEX ON mv_department_stats (name);
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_department_stats;
```

适用建议：报表/统计等读多写少、可容忍短暂滞后的场景用物化视图；需要实时性的用普通视图。

## PL/pgSQL 函数与触发器

### 函数

```sql
CREATE OR REPLACE FUNCTION get_dept_stats(dept_id bigint)
RETURNS TABLE (employee_count bigint, avg_salary numeric)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT count(*)::bigint, avg(e.salary)
    FROM employees e
    WHERE e.department_id = dept_id;
END;
$$;

-- 调用
SELECT * FROM get_dept_stats(1);
```

- 函数内可用 `IF/ELSE`、`FOR` 循环、`RAISE NOTICE` 调试输出。
- `CREATE PROCEDURE`（可 `CALL` 调用）与函数区别：**存储过程内部可以控制事务**（`COMMIT`/`ROLLBACK`），函数不能。
- `DO $$ ... $$;` 匿名块适合一次性脚本，无需建函数。

### 触发器

```sql
-- 1) 触发器函数必须返回 trigger 类型，可通过 NEW/OLD 访问行
CREATE OR REPLACE FUNCTION audit_employee_changes()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO audit_log (entity, entity_id, action, old_data, new_data, changed_at)
    VALUES (TG_TABLE_NAME, NEW.id, TG_OP, row_to_json(OLD), row_to_json(NEW), now());
    RETURN NEW;   -- RETURN NULL 可取消本次操作（如 BEFORE 触发器）
END;
$$;

-- 2) 绑定触发器（PG 11+ 推荐 EXECUTE FUNCTION）
CREATE TRIGGER trg_employees_audit
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW EXECUTE FUNCTION audit_employee_changes();
```

- `BEFORE` 触发器可在写入前校验/改写数据；`AFTER` 用于审计、级联等。
- `FOR EACH ROW` 每行触发，`FOR EACH STATEMENT` 每条语句触发一次。

## 分区表

大数据量表（日志、流水）按分区存储，配合**分区裁剪**可显著提升查询性能与维护效率（PG 10 引入声明式分区，11 起支持 HASH 分区）。

```sql
-- RANGE 分区：按时间
CREATE TABLE events (
    id bigint GENERATED ALWAYS AS IDENTITY,
    occurred_at timestamptz NOT NULL,
    payload jsonb
) PARTITION BY RANGE (occurred_at);

CREATE TABLE events_2026_08 PARTITION OF events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE events_2026_09 PARTITION OF events
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

-- LIST 分区：按枚举值
CREATE TABLE orders_part (
    id bigint,
    status text
) PARTITION BY LIST (status);
CREATE TABLE orders_done PARTITION OF orders_part FOR VALUES IN ('done', 'cancelled');

-- HASH 分区：按哈希均分（适合数据无自然边界）
CREATE TABLE sessions_part (
    id bigint,
    user_id bigint
) PARTITION BY HASH (user_id);
CREATE TABLE sessions_p0 PARTITION OF sessions_part FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE sessions_p1 PARTITION OF sessions_part FOR VALUES WITH (MODULUS 4, REMAINDER 1);

-- 查询只扫描匹配分区（EXPLAIN 中体现为 Partition Pruning）
SELECT count(*) FROM events WHERE occurred_at >= '2026-08-15' AND occurred_at < '2026-08-16';

-- 动态挂载/分离分区（数据归档常用）
ALTER TABLE events DETACH PARTITION events_2026_08;
```

**注意事项**：
- 分区表的主键/唯一约束**必须包含分区键**。
- 分区键上的查询条件才能触发裁剪；条件写在函数里（如 `date(occurred_at) = ...`）会失效。
- 分区过多（数千）会拖慢规划器，需合理设计分区粒度。

## MVCC、VACUUM 与并发控制

### MVCC 工作原理

PG 每个事务拥有递增的 `xid`；一行数据可能有多个版本（通过系统列 `xmin`/`xmax` 标识可见性）。读操作通过快照判断可见性，因此**读不阻塞写，写不阻塞读**。

更新 = 插入新版本 + 标记旧版本过期。过期版本（死元组，dead tuple）不会立即删除，需要 `VACUUM` 清理并复用空间。

### VACUUM

```sql
-- 常规清理（不锁表，只回收可复用空间）
VACUUM (VERBOSE, ANALYZE) events;

-- 查询表的死元组情况
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- 查看 VACUUM 进度（PG 13+）
SELECT * FROM pg_stat_progress_vacuum;
```

| 操作 | 是否锁表 | 用途 |
| --- | --- | --- |
| `autovacuum`（默认开启） | 否 | 自动清理死元组、更新统计信息 |
| `VACUUM` | 否 | 手动清理指定表 |
| `VACUUM FULL` | **是（排他锁）** | 重写表、物理收缩文件，停机窗口使用 |
| `ANALYZE` | 否 | 只更新统计信息 |

> **注意**：表膨胀严重（`n_dead_tup` 长期很高、磁盘占用远超数据量）时，`VACUUM FULL` 会锁表；在线重写可用 `pg_repack` 扩展。

### 事务隔离级别（实战）

| 隔离级别 | 行为 | 典型场景 |
| --- | --- | --- |
| `READ COMMITTED`（默认） | 每条语句取新快照，可能不可重复读 | 绝大多数 OLTP |
| `REPEATABLE READ` | 整个事务一个快照；并发写冲突时后提交者报 `serialization failure` | 报表统计、先读后写 |
| `SERIALIZABLE` | 可串行化；应用需重试序列化错误 | 严格一致性的复杂事务 |

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
-- ... 事务内所有查询看到同一快照
COMMIT;
```

### 锁与并发控制

```sql
-- 行级锁：锁住选中的行，防止并发修改
BEGIN;
SELECT * FROM accounts WHERE id = 1 FOR UPDATE;   -- 独占锁
COMMIT;

-- 任务队列模式：SKIP LOCKED 跳过已被其他事务锁定的行（不阻塞、不抢同一批）
BEGIN;
SELECT * FROM jobs
WHERE status = 'pending'
ORDER BY id
LIMIT 10
FOR UPDATE SKIP LOCKED;
UPDATE jobs SET status = 'processing' WHERE id = ANY(...);
COMMIT;

-- 咨询锁（advisory lock）：应用层分布式互斥
SELECT pg_advisory_lock(42);      -- 会话级，直到显式解锁
SELECT pg_try_advisory_lock(42);  -- 不阻塞，拿到 true/false
```

排障：`pg_locks` 查看锁，`pg_blocking_pids(pid)` 找出谁在阻塞谁；PG 会自动检测死锁并牺牲其中一个事务。

## 索引深入

索引类型选择直接决定查询性能：

| 索引 | 适用场景 | 典型用法 |
| --- | --- | --- |
| B-tree（默认） | 等值、范围、排序、`IN`、`BETWEEN` | 绝大部分列 |
| GIN | 多值键：`jsonb`、数组、全文检索 | `USING gin (payload jsonb_path_ops)` |
| GiST | 几何、范围、相似度、最近邻排序 | 排他约束、`ORDER BY col <-> 目标` |
| BRIN | 与物理顺序强相关的大表（如时间序） | `USING brin (occurred_at)`，索引极小 |
| Hash | 超长等值比较（如长文本 hash） | `USING hash (col)` |

### B-tree 高级形态

```sql
-- 表达式索引：函数包装的列无法直接用普通索引
CREATE INDEX idx_employees_email_lower ON employees ((lower(email)));
SELECT * FROM employees WHERE lower(email) = 'alice@example.com';

-- 部分索引：只索引高频子集，体积小、维护成本低
CREATE INDEX idx_employees_active ON employees (department_id) WHERE status = 'active';

-- 覆盖索引（INCLUDE）：索引中携带附加值，实现 Index Only Scan，避免回表
CREATE INDEX idx_orders_user ON orders (user_id) INCLUDE (amount, status);

-- 排序方向：配合 ORDER BY ... DESC / NULLS LAST
CREATE INDEX idx_orders_created ON orders (created_at DESC NULLS LAST);

-- 多列索引遵循最左前缀：WHERE 必须命中第一列才可用
CREATE INDEX idx_emp_dept_status ON employees (department_id, status);
```

### 最近邻搜索（向量/地理）

```sql
-- GiST 支持 KNN 排序：找最近的 10 条
SELECT id, name, geom
FROM pois
ORDER BY geom <-> 'SRID=4326;POINT(116.4 39.9)'::geometry
LIMIT 10;
```

### 索引维护

```sql
-- 找出从未被使用的索引（idx_scan = 0 且写入多 → 考虑删除）
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY relname;

-- 重建索引（并发方式不锁写）
REINDEX INDEX CONCURRENTLY idx_events_payload_gin;
```

## EXPLAIN 与性能调优

### 读懂执行计划

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;        -- 实际执行并统计（生产谨慎）
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ...;  -- 机器可读
```

> PG 18 起 `EXPLAIN ANALYZE` 默认自动显示缓冲区访问统计，无需再手动加 `BUFFERS`。

常见计划节点：

| 节点 | 含义 | 关注点 |
| --- | --- | --- |
| `Seq Scan` | 全表扫描 | 大表上出现且 `filter` 多 → 缺索引 |
| `Index Scan` | 索引定位 + 回表 | 合理 |
| `Index Only Scan` | 索引覆盖，免回表 | 依赖 visibility map，需及时 VACUUM |
| `Bitmap Index/Heap Scan` | 多个索引条件合并 | 过滤性强时优于单索引 |
| `Nested Loop` | 小表驱动大表，逐行查 | 内表必须有索引 |
| `Hash Join` | 无索引大表连接，建哈希表 | 大数据连接常见 |
| `Merge Join` | 两侧有序连接 | 依赖排序或索引序 |
| `Aggregate` / `GroupAggregate` / `HashAggregate` | 聚合计算 | 大表聚合注意内存 |

调优口诀：**先看 `rows` 估算与实际是否偏差大**（统计信息过期 → `ANALYZE`）；再看是否出现不必要的大表 `Seq Scan`；最后看 `Loops` 是否异常放大（NL 内表循环次数多）。

### 关键配置参数

| 参数 | 建议 | 说明 |
| --- | --- | --- |
| `shared_buffers` | 内存 25% | 共享缓冲区（默认 128MB，偏小） |
| `effective_cache_size` | 内存 50-75% | 帮助规划器估算可用缓存 |
| `work_mem` | 4-64MB（按连接数权衡） | 单次排序/哈希内存，谨慎调大 |
| `maintenance_work_mem` | 256MB-1GB | VACUUM/建索引专用 |
| `max_connections` | 按场景 | 连接过多会放大内存占用，配合连接池 |
| `wal_level` | `replica` | 复制与归档的基础 |
| `checkpoint_completion_target` | 0.9 | 平滑刷新脏页 |

### 慢查询观测

```sql
-- 启用 pg_stat_statements（需 shared_preload_libraries = 'pg_stat_statements' 并重启）
CREATE EXTENSION pg_stat_statements;

-- 按总耗时找 Top SQL
SELECT query, calls, total_exec_time / 1000 AS total_ms,
       mean_exec_time / 1000 AS mean_ms, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

## 扩展生态

PG 的能力很大程度上由扩展提供：

```sql
CREATE EXTENSION IF NOT EXISTS <name>;
```

| 扩展 | 用途 |
| --- | --- |
| `pgcrypto` | 加解密、哈希（`crypt`、`digest`、`pgp_sym_encrypt`） |
| `pg_trgm` | 模糊匹配与相似度（`ILIKE '%xx%'` 加速、`similarity()`） |
| `citext` | 大小写不敏感的文本类型 |
| `hstore` | 轻量 key-value 列 |
| `postgis` | 地理空间数据（点线面、空间索引、距离计算） |
| `pgvector` | 向量存储与相似度检索（AI/RAG） |
| `pg_stat_statements` | SQL 级性能统计 |
| `pg_partman` | 分区自动管理 |
| `pg_repack` | 在线重写表，消除膨胀且不锁写 |
| `tablefunc` | `crosstab()` 行转列（透视） |
| `postgres_fdw` | 跨库/跨 PG 实例访问外部表 |
| `pg_jieba` / `zhparser` | 中文全文检索分词 |

### pgvector：AI 时代最常用扩展

```sql
CREATE EXTENSION vector;

CREATE TABLE embeddings (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content text,
    embedding vector(1536)      -- 维度与嵌入模型输出一致
);

-- 相似度检索：<-> 欧氏距离、<=> 余弦相似度、<#> 内积
SELECT id, content, embedding <=> '[...]'::vector AS distance
FROM embeddings
ORDER BY embedding <-> '[...]'::vector
LIMIT 5;

-- HNSW 索引：召回率高、查询快（推荐），或 IVFFlat（训练后使用）
CREATE INDEX ON embeddings USING hnsw (embedding vector_l2_ops);
```

典型场景：RAG 知识库、语义搜索、推荐系统（与 OpenAI/通义等 Embedding API 配合）。

## 备份与恢复

### 逻辑备份（跨版本迁移首选）

```bash
# 自定义格式（压缩、支持并行恢复）
pg_dump -Fc -d app_db -f app_db.dump
pg_dump -Fc -d app_db -t 'public.orders*' -f orders.dump   # 只导部分表

# 并行恢复
pg_restore -d app_db --jobs=4 app_db.dump

# 纯 SQL 格式（可读、可 grep）
pg_dump -Fp -d app_db -f app_db.sql

# 全实例（角色 + 所有库）
pg_dumpall -f all.sql
```

### 物理备份与时间点恢复（PITR）

```sql
-- 1) 配置 WAL 归档（postgresql.conf）
archive_mode = on
archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'

-- 2) 基础备份（全量）
pg_basebackup -D /backup/base -Fp -Xs -P -h localhost -U replicator

-- 3) 恢复：把基础备份放到数据目录，创建 recovery.signal（PG 12+），
--    并配置 restore_command 回放 WAL 到目标时间点
-- restore_command = 'cp /backup/wal/%f %p'
-- recovery_target_time = '2026-08-28 10:00:00'
```

> **注意**：备份必须定期做**恢复演练**验证可用性；只备份数据文件而忽略 WAL 无法保证一致性。

## 复制与高可用

### 流复制（物理复制，整实例）

```sql
-- 主库：wal_level = replica，创建复制账号
CREATE ROLE replicator LOGIN REPLICATION PASSWORD 'secret';

-- 备库：pg_basebackup 拉取 + primary_conninfo 建立流复制
pg_basebackup -h primary -D /var/lib/postgresql/data -U replicator -Fp -Xs -P
-- standby.signal + primary_conninfo = 'host=primary port=5432 user=replicator ...'
-- 备库设 hot_standby = on 可提供只读查询
```

特点：整库一致、延迟低、只读扩展；主备切换需要手动或依赖高可用组件。

### 逻辑复制（按表/按库，跨版本跨平台）

```sql
-- 发布端（Publisher）
CREATE PUBLICATION mypub FOR TABLE users, orders;
CREATE PUBLICATION mypub_all FOR ALL TABLES;      -- PG 15+

-- 订阅端（Subscriber）
CREATE SUBSCRIPTION mysub
CONNECTION 'host=publisher port=5432 dbname=app_db user=repl password=secret'
PUBLICATION mypub;
```

特点：粒度细（可按表/行/列）、支持不同 PG 主版本间同步、可做数据汇聚/分流、支持双向复制（PG 14+，需处理冲突）；PG 18 起并行流式应用为默认，大事务复制延迟显著降低。

### 对比与选型

| 维度 | 流复制 | 逻辑复制 |
| --- | --- | --- |
| 粒度 | 整个实例 | 表/库级 |
| 主版本兼容 | 必须一致 | 可跨版本 |
| 复制内容 | 全部数据 | 可过滤（WHERE、列） |
| 双向 | 不支持 | 支持（需冲突处理） |
| 典型用途 | 高可用、只读扩展 | 数据分发、迁移、汇聚 |

### 高可用与连接层

- **Patroni + etcd/Consul**：自动故障切换的事实标准，配合 `pg_rewind` 快速恢复原主库。
- **PgBouncer**：轻量连接池，缓解 `max_connections` 压力（事务级/会话级池）。
- **Pgpool-II / HAProxy**：读写分离路由与负载均衡。
- **云服务**：RDS for PostgreSQL、Aurora PostgreSQL 等托管方案自带高可用。

## 安全与权限

### 角色与最小权限

```sql
-- 只读账号
CREATE ROLE readonly LOGIN PASSWORD 'secret';
GRANT CONNECT ON DATABASE app_db TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- 新表自动继承（关键！否则以后建的表读不了）
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;

-- 撤销
REVOKE ALL ON TABLE employees FROM readonly;
```

### 行级安全（RLS）

多租户场景下，在数据库层强制数据隔离：

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_own_rows ON users
    USING (id = current_setting('app.user_id')::bigint);

-- 应用连接后设置上下文
SET app.user_id = '1001';
SELECT * FROM users;   -- 只能看到自己
```

> **注意**：表 owner 默认绕过 RLS；`ALTER TABLE ... FORCE ROW LEVEL SECURITY` 可强制 owner 也受限。RLS 不是应用鉴权的替代品，而是纵深防御的一层。

### 其他安全要点

- 密码默认使用 `scram-sha-256`（PG 14+），不要降级为 `md5`。
- 警惕 `search_path` 注入：`SET search_path = public, pg_catalog`，不要把不可信 schema 放在第一位。
- 生产启用 SSL：`ssl = on`，配置证书；远程连接禁用 `trust` 认证。
- 最小权限原则：应用账号不授予 `superuser`，DDL 与 DML 分离。

## 运维监控与排障

```sql
-- 当前所有会话与状态
SELECT pid, usename, state, wait_event_type, wait_event,
       now() - query_start AS duration, left(query, 80) AS query
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duration DESC;

-- 终止/取消会话
SELECT pg_terminate_backend(pid);   -- 强制断开
SELECT pg_cancel_backend(pid);      -- 取消当前查询（温和）

-- 查看阻塞链
SELECT pid, pg_blocking_pids(pid) AS blocked_by, query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- 数据库与表大小
SELECT pg_size_pretty(pg_database_size('app_db'));
SELECT pg_size_pretty(pg_total_relation_size('events'));

-- 死锁与冲突计数
SELECT datname, deadlocks, conflicts, blks_read, blks_hit
FROM pg_stat_database;
```

### 常见问题速查

| 现象 | 常见原因 | 处理 |
| --- | --- | --- |
| 磁盘持续增长 | 死元组未清理 / 大日志 | `VACUUM (ANALYZE)`，膨胀严重用 `pg_repack` |
| 连接数爆满 | 无连接池 / 长事务泄漏 | 查 `pg_stat_activity`，接入 PgBouncer |
| 查询突然变慢 | 统计信息过期 | `ANALYZE`；检查执行计划 |
| 复制延迟 | 备库资源不足 / 大事务 | 检查 `pg_stat_replication`，优化大事务 |
| 时区错乱 | 用了 `timestamp` 而非 `timestamptz` | 业务统一存 `timestamptz` |

## 选型建议

| 维度 | 选 PostgreSQL | 选 MySQL |
| --- | --- | --- |
| 数据形态 | 需要 JSON/文档、地理、向量、全文检索 | 纯关系型简单 OLTP |
| 查询复杂度 | 窗口函数、递归、物化视图、复杂分析 | 简单 CRUD |
| 高可用 | 需要 PITR、逻辑复制、复杂拓扑 | 主从 + 半同步即可 |
| 生态 | 愿意接受扩展式生态 | 运维团队 MySQL 经验丰富 |
| 商业考虑 | 规避 Oracle/专有授权成本 | 云厂商 MySQL 托管成熟 |

**一句话总结**：PostgreSQL 是“什么都能干”的关系型数据库——文档、搜索、地理、向量都能在库里解决；如果业务以复杂查询、混合数据类型、AI 向量检索为主，PG 是首选；纯简单 OLTP 且团队以 MySQL 经验为主，MySQL 依然稳妥。

## 参考

- 官方文档：https://www.postgresql.org/docs/
- 官方中文（不完全）：https://www.postgresql.org/docs/current/
- pgvector：https://github.com/pgvector/pgvector
- PostgreSQL 18 发布说明：https://www.postgresql.org/docs/release/18/
