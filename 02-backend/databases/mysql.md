---
title: MySQL 技术指南
description: 从 SQL 语法、库表设计、索引与事务原理，到性能优化与高可用架构的 MySQL 全栈知识体系
tags:
  - database
  - mysql
  - sql
  - index
  - transaction
date: 2026-10-26
aliases:
  - MySQL 深入学习
  - mysql-guide
---

# MySQL 技术指南

> 本文以 MySQL 8.0 为主（8.0 的差异会在文中单独标注），覆盖**语言 → 设计 → 原理 → 优化 → 架构**五个层次。
> 如果只想快速查语法，见 [[mysql-crash-course|MySQL 必知必会]]；如果关注其他数据库，见 [[postgresql|PostgreSQL]]、
> [[clickhouse|ClickHouse]]、[[mongodb|MongoDB]]。

## 1. 认识 MySQL

### 1.1 MySQL 的定位

MySQL 是最主流的**关系型数据库（RDBMS）**，属于 OLTP 场景（在线事务处理）的默认选择，核心优势：

- **生态成熟**：几乎所有后端语言、ORM 框架、运维工具都一等公民支持。
- **存储引擎可插拔**：InnoDB 负责事务与行锁，Memory 负责临时表，可按表选用。
- **主从复制简单可靠**：基于 binlog 的异步复制是读写分离的基石。
- **成本低**：单机性能足够撑起绝大多数业务，分库分表的门槛很高。

不适合的场景：海量列式分析（用 ClickHouse）、超大规模文档存储（用 MongoDB）、
强分布式事务的全球多活（用 NewSQL，如 TiDB、OceanBase）。

### 1.2 逻辑架构

理解分层是理解后面所有原理（索引、事务、锁、日志）的前提：

```text
┌──────────────────────────────────────────────────────┐
│ 客户端（JDBC / mysql-cli / 连接池）                  │
└──────────────────────────────────────────────────────┘
                           │ TCP 3306
┌──────────────────────────────────────────────────────┐
│ 连接层：连接管理、认证、权限校验、线程复用           │
├──────────────────────────────────────────────────────┤
│ Server 层                                            │
│   解析器 → 预处理器 → 优化器 → 执行器                │
│   内置函数、视图、触发器、存储过程                   │
│   查询缓存（8.0 已移除）                             │
├──────────────────────────────────────────────────────┤
│ 存储引擎层（可插拔）：InnoDB / MyISAM / Memory       │
│   事务、行锁、MVCC、redo/undo log 都在这一层         │
└──────────────────────────────────────────────────────┘
                           │
                       文件系统（.ibd / binlog）
```

三条重要的分层结论：

1. **SQL 是逐层降级执行的**：优化器在 Server 层决定"走哪个索引"，但真正读页的是存储引擎。
   所以"索引失效"本质是优化器认为全表扫描更便宜。
2. **事务、锁、MVCC 都是 InnoDB 的能力**，不是 MySQL 的能力——这解释了为什么 MyISAM 不支持事务。
3. **Server 层的 binlog 与 InnoDB 层的 redo log 是两套独立日志**，这是崩溃恢复与主从复制的核心，
   也是"两阶段提交"存在的原因（见 [12.1](#121-三种日志与两阶段提交)）。

### 1.3 一条查询 SQL 的完整旅程

```sql
SELECT id, name FROM employee WHERE dept_id = 10 AND salary > 20000 LIMIT 10;
```

| 阶段 | 动作 | 关键点 |
|------|------|--------|
| 连接 | 三次握手 → 认证 → 分配线程 | 长连接会累积内存（`wait_timeout`） |
| 解析 | 词法/语法分析生成语法树 | 语法错误在此报 `You have an error in your SQL syntax` |
| 预处理 | 检查表、列是否存在，展开 `*`、视图 | 报 `Unknown column` / `Table doesn't exist` |
| 优化 | 选索引、决定连接顺序、改写子查询 | 生成执行计划，`EXPLAIN` 看到的就是它 |
| 执行 | 调用存储引擎接口逐行取数 | 按需读取（`LIMIT` 会提前终止扫描） |
| 返回 | 结果集发送客户端 | 大结果集建议流式读取 |

### 1.4 存储引擎对比

| 特性 | InnoDB | MyISAM | Memory |
|------|--------|--------|--------|
| 事务 | ✅ 支持 ACID | ❌ | ❌ |
| 锁粒度 | 行锁 + 间隙锁 | 表锁 | 表锁 |
| 外键 | ✅ | ❌ | ❌ |
| 崩溃恢复 | ✅ redo log | ❌ 需 `REPAIR TABLE` | ❌ 数据丢失 |
| 聚簇索引 | ✅ 主键即数据 | ❌ 索引与数据分离 | ❌ |
| 全文索引 | ✅（5.6+） | ✅ | ❌ |
| 适用场景 | **默认选择，99% 的业务表** | 只读历史归档表 | 临时表、缓存小字典 |

```sql
-- 查看支持的引擎及默认引擎
SHOW ENGINES;
-- 建表时指定引擎与字符集（推荐显式指定，不依赖服务端默认值）
CREATE TABLE t_demo (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
```

> **坑**：MySQL 5.7 默认引擎是 InnoDB，但默认字符集是 `latin1`（部分发行版）或 `utf8`（三字节，
> 存不了 emoji）。8.0 起默认 `utf8mb4`。**永远显式写 `utf8mb4`**，否则插入 emoji 会报
> `Incorrect string value`。

## 2. SQL 语言四分类

| 分类 | 全称 | 作用 | 关键字 |
|------|------|------|--------|
| **DDL** | Data Definition Language | 定义库、表、列、索引等结构 | `CREATE` `DROP` `ALTER` `TRUNCATE` `RENAME` |
| **DML** | Data Manipulation Language | 增删改**表数据** | `INSERT` `UPDATE` `DELETE` |
| **DQL** | Data Query Language | 查询表数据 | `SELECT` |
| **DCL** | Data Control Language | 权限与安全 | `GRANT` `REVOKE` |
| **TCL** | Transaction Control Language | 事务控制（常并入 DCL） | `COMMIT` `ROLLBACK` `SAVEPOINT` |

记忆要点：

- **DDL 隐式提交**：执行 `ALTER TABLE`、`TRUNCATE` 会强制提交当前事务，且无法回滚。
  这是"事务里混入 DDL 导致数据不一致"的根源。
- **DML 可回滚**（InnoDB），但 `TRUNCATE` 属于 DDL，不可回滚且会重置自增计数器。
- **DQL 不产生 undo**，但会产生一致性读的快照（见 [9.4 MVCC](#94-mvcc-多版本并发控制)）。

## 3. 数据类型选型

类型选错是后期最难改的技术债（改类型 = 重建表 + 锁表风险）。先看结论：

| 需求 | 推荐类型 | 理由 |
|------|----------|------|
| 主键 | `BIGINT UNSIGNED AUTO_INCREMENT` 或 `BINARY(16)`（UUID） | 自增有序，避免页分裂 |
| 金额 | `DECIMAL(18,4)` | 精确小数，`FLOAT/DOUBLE` 有精度误差 |
| 状态/枚举 | `TINYINT UNSIGNED` + 注释 | 比 `VARCHAR` 省空间，比 `ENUM` 易扩展 |
| 短文本（< 500 字符，定长查询） | `VARCHAR(n)` | 按需分配 |
| 定长标识（手机号、身份证、MD5） | `CHAR(n)` | 定长检索更快 |
| 长文本 | `TEXT` / `LONGTEXT` | 存放在溢出页，避免主表膨胀 |
| 时间点（跨时区） | `TIMESTAMP` | 自动时区转换，但有 2038 上限 |
| 业务时间（生日、账单日） | `DATETIME` | 范围 1000–9999 年，不做时区转换 |
| 半结构化数据 | `JSON`（8.0） | 支持路径查询与虚拟列索引 |

### 3.1 数值类型

```sql
-- 整数：按取值范围选最小够用的类型，联合索引里能省大量空间
CREATE TABLE t_int (
  a TINYINT   UNSIGNED,  -- 0 ~ 255
  b SMALLINT  UNSIGNED,  -- 0 ~ 65535
  c INT       UNSIGNED,  -- 0 ~ 42 亿
  d BIGINT    UNSIGNED,  -- 0 ~ 1844 京
  e DECIMAL(18, 4)       -- 金额：18 位总长，4 位小数
);
```

> `INT(11)` 里的 `11` 是**显示宽度**，不影响取值范围，8.0.19 起已被废弃（仅 `ZEROFILL` 时保留意义）。
> 面试常问"`INT(11)` 和 `INT(20)` 有区别吗"——存储和范围完全一样。

### 3.2 字符串类型

| 类型 | 长度 | 存储 | 特点 |
|------|------|------|------|
| `CHAR(n)` | 固定 n 字符 | 定长，不足补空格（读时去除） | 适合定长编码 |
| `VARCHAR(n)` | 变长，上限 65535 字节 | 1~2 字节长度前缀 + 实际内容 | 最常用 |
| `TEXT` | 上限 64KB | 行外存储，只留 20 字节指针 | 不能有默认值，索引需前缀长度 |
| `BLOB` | 二进制大对象 | 行外存储 | 存文件请用对象存储（见 [[minio]]） |

**`VARCHAR(255)` 是经验值**：单字节长度前缀上限 255，超过 255 需要 2 字节前缀。
但在 `utf8mb4` 下 `VARCHAR(255)` 最长占 1020 字节，仍可能让行超过 8126 字节的行内上限。

### 3.3 时间类型

```sql
CREATE TABLE t_time (
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  birth_date DATE,
  stat_date  DATETIME
);
```

| 类型 | 字节 | 范围 | 时区行为 |
|------|------|------|----------|
| `DATETIME` | 5~8 | 1000-01-01 ~ 9999-12-31 | 原样存取，不做转换 |
| `TIMESTAMP` | 4 | 1970-01-01 ~ 2038-01-19 | 存入转 UTC，取出转会话时区 |
| `DATE` | 3 | 1000-01-01 ~ 9999-12-31 | — |

> `TIMESTAMP` 的 2038 问题真实存在。做长期系统（合同到期日、会员有效期）用 `DATETIME`。

### 3.4 JSON 类型（8.0）

```sql
CREATE TABLE t_order (
  id BIGINT PRIMARY KEY,
  ext JSON,   -- 生成列 + 索引，让 JSON 字段也能走索引
  user_id BIGINT GENERATED ALWAYS AS (ext ->> '$.user_id') STORED,
  KEY idx_user_id (user_id)
);

INSERT INTO t_order (id, ext) VALUES (1, '{"user_id": 1001, "channel": "app"}');

-- -> 返回 JSON 值，->> 返回去引号的字符串（可直接比较）
SELECT id, ext ->> '$.channel' AS channel FROM t_order WHERE ext ->> '$.channel' = 'app';
```

注意：JSON 字段**不能直接建索引**，必须通过生成列中转。频繁按 JSON 内部字段查询，
说明数据模型该拆表了。

## 4. DDL：库与表

### 4.1 数据库操作

```sql
CREATE DATABASE IF NOT EXISTS shop
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

SHOW DATABASES;
USE shop;
SELECT DATABASE();          -- 当前所在库
SHOW CREATE DATABASE shop;  -- 查看建库语句
DROP DATABASE IF EXISTS shop;
```

### 4.2 建表、改表、删表

```sql
CREATE TABLE employee (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  name        VARCHAR(50)     NOT NULL                COMMENT '姓名',
  dept_id     INT             NOT NULL                COMMENT '部门ID',
  salary      DECIMAL(12, 2)  NOT NULL DEFAULT 0.00   COMMENT '月薪',
  phone       VARCHAR(20)         NULL                COMMENT '手机号',
  is_deleted  TINYINT         NOT NULL DEFAULT 0      COMMENT '0正常 1删除',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_phone (phone),
  KEY idx_dept_salary (dept_id, salary)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '员工表';
```

```sql
-- 改表：所有结构变更都用 ALTER TABLE
ALTER TABLE employee ADD COLUMN email VARCHAR(100) NULL COMMENT '邮箱' AFTER phone;
ALTER TABLE employee MODIFY COLUMN name VARCHAR(64) NOT NULL COMMENT '姓名';
ALTER TABLE employee CHANGE COLUMN phone mobile VARCHAR(20) NULL COMMENT '手机号';  -- 改名 + 改类型
ALTER TABLE employee DROP COLUMN email;
ALTER TABLE employee RENAME TO staff;
ALTER TABLE employee ADD INDEX idx_name (name);   -- 加索引
ALTER TABLE employee DROP INDEX idx_name;         -- 删索引

-- 删表（结构 + 数据一起删，不可回滚）
DROP TABLE IF EXISTS staff;
TRUNCATE TABLE staff;   -- 只清数据，保留结构，重置自增，不可回滚
```

`DELETE` / `TRUNCATE` / `DROP` 的区别是高频面试题：

| 对比项 | `DELETE` | `TRUNCATE` | `DROP` |
|--------|----------|------------|--------|
| 语言分类 | DML | DDL | DDL |
| 是否可回滚 | ✅（InnoDB） | ❌ | ❌ |
| 是否逐行删除 | ✅ 逐行，写 undo | ❌ 重建表 | ❌ 删除表定义 |
| 触发触发器 | ✅ | ❌ | ❌ |
| 自增计数器 | 不重置 | 重置为 1 | — |
| 速度 | 慢（大表极慢） | 快 | 快 |
| 空间回收 | 不释放，产生碎片 | 释放 | 释放 |

### 4.3 约束

**概念**：约束是对表数据的限定，保证数据的正确性、有效性和完整性。

| 约束 | 关键字 | 作用 | 说明 |
|------|--------|------|------|
| 主键 | `PRIMARY KEY` | 非空 + 唯一 | 一张表只能有一个，是聚簇索引的依据 |
| 非空 | `NOT NULL` | 值不能为 NULL | 最基础也最容易漏的约束 |
| 唯一 | `UNIQUE` | 值不重复 | **允许多个 NULL**（NULL 不等于 NULL） |
| 外键 | `FOREIGN KEY` | 引用完整性 | 互联网业务常因性能/分库分表而弃用 |
| 默认值 | `DEFAULT` | 未赋值时填充 | 8.0 支持表达式默认值 |
| 检查 | `CHECK` | 值满足布尔表达式 | **5.7 解析但忽略，8.0.16+ 真正生效** |

#### 4.3.1 非空约束

```sql
-- 建表时指定
CREATE TABLE stu (
  id   INT,
  name VARCHAR(20) NOT NULL
);

-- 建表后追加
ALTER TABLE stu MODIFY name VARCHAR(20) NOT NULL;

-- 删除（注意：改成 NULL 只是允许 NULL，已有 NULL 值需先清理）
ALTER TABLE stu MODIFY name VARCHAR(20) NULL;
```

#### 4.3.2 唯一约束

```sql
CREATE TABLE stu (
  id     INT,
  phone  VARCHAR(20) UNIQUE           -- 唯一约束
);

-- 命名唯一约束（推荐：便于后续删除和报错定位）
CREATE TABLE stu2 (
  id    INT,
  phone VARCHAR(20),
  CONSTRAINT uk_stu_phone UNIQUE (phone)
);

-- 删除唯一约束 = 删除它背后的唯一索引
ALTER TABLE stu DROP INDEX phone;

-- 建表后追加唯一约束：本质是建了一个唯一索引
ALTER TABLE stu ADD UNIQUE KEY uk_phone (phone);

-- 联合唯一：同一用户对同一商品只能有一条评价
ALTER TABLE review ADD CONSTRAINT uk_user_goods UNIQUE (user_id, goods_id);
```

> **关键特性**：唯一约束列的多个 `NULL` 是允许的，因为 `NULL <> NULL`。
> 若业务要求"必填 + 唯一"，必须同时写 `NOT NULL UNIQUE`。

#### 4.3.3 主键约束

```sql
-- 建表时添加
CREATE TABLE stu (
  id   INT PRIMARY KEY,
  name VARCHAR(20)
);

-- 表级写法（联合主键必须这样写）
CREATE TABLE course_score (
  stu_id    INT,
  course_id INT,
  score     DECIMAL(5, 2),
  PRIMARY KEY (stu_id, course_id)
);

-- 删除主键（若列带 auto_increment，必须先去掉自增，否则报错）
ALTER TABLE stu MODIFY id INT;        -- 先取消自增
ALTER TABLE stu DROP PRIMARY KEY;     -- 再删除主键

-- 建表后添加主键
ALTER TABLE stu MODIFY id INT PRIMARY KEY;   -- 单列
ALTER TABLE stu ADD PRIMARY KEY (id);        -- 更通用的写法
```

主键三条铁律：

1. **非空且唯一**，等价于 `NOT NULL + UNIQUE` 的组合。
2. **一张表只能有一个主键**，但主键可以由多列组成（联合主键）。
3. **InnoDB 的主键即数据本身**（聚簇索引），所以主键选择直接决定写入性能（见 [8.2](#82-聚簇索引与二级索引)）。

#### 4.3.4 自增 `AUTO_INCREMENT`

```sql
CREATE TABLE stu (
  id   INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(20)
);

-- 删除自增
ALTER TABLE stu MODIFY id INT;

-- 添加自增（列必须是索引的一部分）
ALTER TABLE stu MODIFY id INT AUTO_INCREMENT;

-- 查询上一次插入生成的自增值（注意：是连接级别的，不是表级别的）
SELECT LAST_INSERT_ID();
```

三个易踩的坑：

- **自增不连续**是正常现象：回滚、`INSERT ... ON DUPLICATE KEY UPDATE`、批量插入预分配都会造成空洞。
  自增值只保证**单调递增**，不保证连续，不要用它做业务编号。
- **8.0 之前自增计数器只在内存中**，重启后取 `MAX(id) + 1`，删除最大行后重启会复用 ID。
  8.0 起写入 redo log，持久化了。
- **自增锁**模式由 `innodb_autoinc_lock_mode` 控制，默认 `2`（交叉模式），批量插入性能最好，
  但 binlog 必须用 `ROW` 格式才能保证主从一致。

#### 4.3.5 外键约束

外键让两张表产生关系，由数据库保证引用完整性。

```sql
-- 建表时添加（推荐显式命名，否则后续删除要靠猜）
CREATE TABLE employee (
  id      INT PRIMARY KEY AUTO_INCREMENT,
  dept_id INT,
  CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES department (id)
);

-- 建表后添加
ALTER TABLE employee
  ADD CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES department (id);

-- 删除外键（注意：删的是"约束"，不是索引）
ALTER TABLE employee DROP FOREIGN KEY fk_emp_dept;

-- 查看外键
SELECT constraint_name, table_name, referenced_table_name
FROM information_schema.key_column_usage
WHERE table_schema = 'shop' AND referenced_table_name IS NOT NULL;
```

外键的三个隐性代价：

1. 每次写入都要回查主表，**加锁范围扩大**，高并发下容易死锁。
2. DDL 变更（改主表结构）会被阻塞。
3. **分库分表后外键必然失效**，所以互联网公司通常把完整性校验上移到应用层。

#### 4.3.6 级联操作

```sql
ALTER TABLE employee
  ADD CONSTRAINT fk_emp_dept
  FOREIGN KEY (dept_id) REFERENCES department (id)
  ON UPDATE CASCADE      -- 主表主键更新时，子表外键跟着改
  ON DELETE CASCADE;     -- 主表删除时，子表关联记录一起删
```

| 选项 | 行为 | 风险 |
|------|------|------|
| `RESTRICT` / `NO ACTION` | 有子记录时禁止操作（默认） | 安全，推荐 |
| `CASCADE` | 级联更新/删除 | **危险**，误删主表会连带删掉整片数据 |
| `SET NULL` | 子表外键置 NULL（列必须可空） | 数据可能变成孤儿 |
| `SET DEFAULT` | InnoDB **不支持** | — |

> 生产建议：**默认全部用 `RESTRICT`，禁止用 `DELETE` 级联**。需要级联删除时用应用层显式逻辑，
> 保证操作可审计、可回滚。

#### 4.3.7 检查约束（8.0.16+）

```sql
CREATE TABLE product (
  id    INT PRIMARY KEY,
  price DECIMAL(10, 2) NOT NULL,
  stock INT NOT NULL,
  CONSTRAINT chk_price CHECK (price >= 0),
  CONSTRAINT chk_stock CHECK (stock >= 0)
);

-- 违反约束会直接报错：Check constraint 'chk_price' is violated.
INSERT INTO product VALUES (1, -1, 10);
```

## 5. DML：数据操作

```sql
-- 指定列插入（推荐：表结构变更时不受影响）
INSERT INTO employee (name, dept_id, salary, phone)
VALUES ('张三', 10, 18000.00, '13800000000');

-- 批量插入（一条 SQL 插入多行，比循环单条快一个数量级）
INSERT INTO employee (name, dept_id, salary)
VALUES ('李四', 10, 15000.00),
       ('王五', 20, 22000.00),
       ('赵六', 20, 19500.00);

-- 从查询结果插入
INSERT INTO employee_archive (id, name, dept_id, salary)
SELECT id, name, dept_id, salary FROM employee WHERE created_at < '2024-01-01';

-- UPSERT：主键/唯一键冲突时更新（统计计数、幂等写入常用）
INSERT INTO goods_stat (goods_id, view_count)
VALUES (1001, 1)
ON DUPLICATE KEY UPDATE view_count = view_count + 1;

-- 更新
UPDATE employee SET salary = salary * 1.1 WHERE dept_id = 10;

-- 删除
DELETE FROM employee WHERE id = 5;
```

**安全红线**：`UPDATE` / `DELETE` 忘记写 `WHERE` 是全表灾难。生产环境建议开启安全模式：

```sql
SET sql_safe_updates = 1;   -- 没有 WHERE 或 WHERE 不走索引的 UPDATE/DELETE 会被拒绝
```

另一个坑：`UPDATE ... LIMIT n` 在没有 `ORDER BY` 时更新的行是**不确定的**。

## 6. DQL：查询

### 6.1 单表查询的完整骨架

```sql
SELECT   dept_id, COUNT(*) AS cnt, AVG(salary) AS avg_salary
FROM     employee
WHERE    is_deleted = 0 AND salary > 10000
GROUP BY dept_id
HAVING   COUNT(*) >= 3
ORDER BY avg_salary DESC
LIMIT    10;
```

**书写顺序 ≠ 执行顺序**，这是理解 SQL 的关键：

```text
书写：SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT
执行：FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT
```

由此推出几个必然结论：

- `WHERE` 里**不能**用 `SELECT` 中定义的别名（此时还没算出来）；但 `ORDER BY` 可以。
- `WHERE` 过滤行，`HAVING` 过滤分组，**能在 `WHERE` 过滤的绝不放到 `HAVING`**（前者能走索引）。
- `LIMIT` 最后执行，所以深分页 `LIMIT 1000000, 10` 必须先扫描 100 万行（见 [11.4](#114-深分页优化)）。

### 6.2 过滤与排序

```sql
-- 比较与范围
SELECT * FROM employee WHERE salary BETWEEN 10000 AND 20000;
SELECT * FROM employee WHERE phone IS NULL;            -- 判断 NULL 只能用 IS NULL
SELECT * FROM employee WHERE dept_id IN (10, 20, 30);

-- 模糊查询
SELECT * FROM employee WHERE name LIKE '张%';    -- ✅ 能用索引（前缀匹配）
SELECT * FROM employee WHERE name LIKE '%三';    -- ❌ 索引失效，全表扫描

-- 排序（多列：前一个相同才比后一个）
SELECT * FROM employee ORDER BY dept_id ASC, salary DESC;
```

**`NULL` 的三值逻辑**是常见错误源：

| 表达式 | 结果 |
|--------|------|
| `NULL = NULL` | `NULL`（不是 `TRUE`） |
| `NULL <> NULL` | `NULL` |
| `NULL AND FALSE` | `FALSE` |
| `NULL OR TRUE` | `TRUE` |
| `COUNT(col)` 遇 `NULL` | 不计数 |
| `SUM/AVG/MAX/MIN` 遇 `NULL` | 跳过该行 |

```sql
-- 错误：想查"手机号为空或不等于某值"，这样写会漏掉 NULL 行
SELECT * FROM employee WHERE phone <> '13800000000';

-- 正确
SELECT * FROM employee WHERE phone <> '13800000000' OR phone IS NULL;
-- 或用 NULL 安全比较（8.0 的 <=> 等价于 IS NOT DISTINCT FROM）
SELECT * FROM employee WHERE NOT (phone <=> '13800000000');
```

### 6.3 聚合与分组

```sql
SELECT dept_id,
       COUNT(*)          AS total,      -- 统计行数，含 NULL
       COUNT(phone)      AS has_phone,  -- 不含 NULL
       COUNT(DISTINCT dept_id) AS dept_cnt
FROM employee
GROUP BY dept_id;
```

| 函数 | 是否忽略 NULL | 备注 |
|------|---------------|------|
| `COUNT(*)` | 不忽略 | 统计行数，InnoDB 中会选最小的二级索引扫描 |
| `COUNT(col)` | 忽略 | 统计该列非 NULL 的行数 |
| `SUM` `AVG` `MAX` `MIN` | 忽略 | 全为 NULL 时返回 `NULL` |

> **`GROUP BY` 与 `ONLY_FULL_GROUP_BY`**：MySQL 5.7 起默认开启该 `sql_mode`，`SELECT` 中的非聚合列
> 必须出现在 `GROUP BY` 中，否则报错。这是从"能跑"到"语义正确"的强制升级。
> 若确实需要取分组内某行，用 `ANY_VALUE(col)`（明确表示"我不在乎哪一行"）或改用窗口函数。

### 6.4 多表查询

#### 笛卡尔积

```sql
-- 两张表无条件连接：结果行数 = A 行数 × B 行数（3 部门 × 4 员工 = 12 行）
SELECT * FROM department, employee;
```

笛卡尔积几乎永远是**错误**的，多表查询必须带连接条件。

#### 内连接（只保留两边都匹配的行）

```sql
-- 隐式内连接（SQL92 写法，连接条件放 WHERE）
SELECT e.name, d.dept_name
FROM employee e, department d
WHERE e.dept_id = d.id;

-- 显式内连接（推荐，语义清晰，连接条件与过滤条件分离）
SELECT e.name, d.dept_name
FROM employee e
INNER JOIN department d ON e.dept_id = d.id
WHERE e.salary > 10000;
```

#### 外连接（保留一侧的全部行）

```sql
-- 左外连接：保留左表全部行，右表无匹配则补 NULL
SELECT d.dept_name, e.name
FROM department d
LEFT JOIN employee e ON d.id = e.dept_id;

-- 右外连接：保留右表全部行
SELECT e.name, d.dept_name
FROM employee e
RIGHT JOIN department d ON e.dept_id = d.id;

-- 经典场景：找出没有员工的部门
SELECT d.dept_name
FROM department d
LEFT JOIN employee e ON d.id = e.dept_id
WHERE e.id IS NULL;
```

| 连接类型 | 关键字 | 结果集 |
|----------|--------|--------|
| 内连接 | `INNER JOIN` | 两边都匹配的行 |
| 左外连接 | `LEFT JOIN` | 左表全量 + 右表匹配（不匹配补 NULL） |
| 右外连接 | `RIGHT JOIN` | 右表全量 + 左表匹配 |
| 全外连接 | `FULL OUTER JOIN` | **MySQL 不支持**，用 `LEFT JOIN UNION RIGHT JOIN` 模拟 |
| 交叉连接 | `CROSS JOIN` | 笛卡尔积 |

> **性能提示**：`LEFT JOIN` 的**左表必须是小表**（驱动表），否则优化器可能改写成 `JOIN` 反而变慢。
> 判断"要不要用外连接"的标准：**是否需要保留不匹配的行**。不需要就用内连接，可优化空间更大。

### 6.5 子查询

```sql
-- 标量子查询：返回单个值，可放在 SELECT / WHERE 中
SELECT name, salary,
       (SELECT AVG(salary) FROM employee) AS company_avg
FROM employee;

-- 列子查询 + IN
SELECT name FROM employee
WHERE dept_id IN (SELECT id FROM department WHERE city = '杭州');

-- 相关子查询 + EXISTS（找到有员工的部门）
SELECT d.dept_name FROM department d
WHERE EXISTS (SELECT 1 FROM employee e WHERE e.dept_id = d.id);

-- 派生表（FROM 子句里的子查询，必须有别名）
SELECT t.dept_id, t.avg_salary
FROM (SELECT dept_id, AVG(salary) AS avg_salary FROM employee GROUP BY dept_id) t
WHERE t.avg_salary > 15000;
```

**`IN` 与 `EXISTS` 怎么选**：

| 场景 | 推荐 | 原因 |
|------|------|------|
| 子查询结果集小 | `IN` | 先算出小集合，再走索引匹配 |
| 外层表小、子查询表大 | `EXISTS` | 外层每行做一次索引探测，命中即停 |
| 子查询含 `NULL` | `EXISTS` | `NOT IN (… NULL …)` 恒为 `NULL`，结果为空 |

```sql
-- 陷阱：子查询里有 NULL，NOT IN 返回空集
SELECT * FROM employee WHERE dept_id NOT IN (SELECT dept_id FROM project);  -- 若某项目 dept_id 为 NULL

-- 安全写法
SELECT * FROM employee e
WHERE NOT EXISTS (SELECT 1 FROM project p WHERE p.dept_id = e.dept_id);
```

> MySQL 8.0 的优化器会把多数 `IN` 子查询**半连接（semi-join）**改写，性能差异已明显缩小。
> 但仍建议对 `NOT IN` 保持警惕。

### 6.6 窗口函数与 CTE（8.0）

**窗口函数**：在不折叠行的前提下做分组计算，是"每个部门工资前三"这类需求的正解。

```sql
-- 每个部门工资前 3 名
SELECT dept_id, name, salary, rn
FROM (
  SELECT dept_id, name, salary,
         ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rn
  FROM employee
) t
WHERE rn <= 3;
```

| 函数 | 说明 |
|------|------|
| `ROW_NUMBER()` | 连续序号，相同值也编号 1、2、3 |
| `RANK()` | 相同值并列，后续跳号 1、1、3 |
| `DENSE_RANK()` | 相同值并列，不跳号 1、1、2 |
| `LAG(col, n)` / `LEAD(col, n)` | 取前/后第 n 行（同比环比） |
| `SUM() OVER (...)` | 累计求和（running total） |

```sql
-- 环比：本月销售额与上月对比
SELECT month, amount,
       LAG(amount, 1) OVER (ORDER BY month) AS prev_amount,
       ROUND((amount - LAG(amount, 1) OVER (ORDER BY month))
             / LAG(amount, 1) OVER (ORDER BY month) * 100, 2) AS growth_pct
FROM sales_monthly;
```

**CTE（`WITH`）**：把复杂查询拆成可读的步骤。

```sql
WITH dept_stat AS (
  SELECT dept_id, COUNT(*) AS cnt, AVG(salary) AS avg_salary
  FROM employee
  GROUP BY dept_id
),
rich_dept AS (
  SELECT * FROM dept_stat WHERE avg_salary > 18000
)
SELECT d.dept_name, r.cnt, r.avg_salary
FROM rich_dept r
JOIN department d ON d.id = r.dept_id;
```

```sql
-- 递归 CTE：查组织架构树（8.0）
WITH RECURSIVE org_tree AS (
  SELECT id, name, manager_id, 1 AS lvl
  FROM employee WHERE manager_id IS NULL      -- 锚点：顶层
  UNION ALL
  SELECT e.id, e.name, e.manager_id, t.lvl + 1
  FROM employee e
  JOIN org_tree t ON e.manager_id = t.id      -- 递归：向下展开
)
SELECT * FROM org_tree ORDER BY lvl, id;
```

> 递归 CTE 默认最大深度由 `cte_max_recursion_depth` 控制（默认 1000），
> 层级很深时需调大，或加 `WHERE lvl < 10` 防止无限循环。

## 7. 数据库设计

### 7.1 范式

**概念**：范式是设计关系数据库时需要遵循的规范，**高级范式必须先满足低级范式**。
范式越高，冗余越小，但连接越多。目前共有六种：1NF、2NF、3NF、BCNF、4NF、5NF（完美范式）。

#### 第一范式（1NF）：列不可再分

每一列都是**原子数据项**，不能是集合、数组或可拆分的复合值。

**违反 1NF**：`contact` 列里塞了多个值，无法单独按手机号查询。

| id | contact |
|----|---------|
| 1 | 张三,138xxx |

**满足 1NF**：把复合值拆成独立的列。

| id | name | phone |
|----|------|-------|
| 1 | 张三 | 138xxx |

> 注意：`JSON` 字段在物理上是一个原子值，**形式上满足 1NF**，但把可查询的业务字段塞进 JSON
> 属于"逻辑上的非原子"，仍应按需拆表。

#### 函数依赖的五个基础概念

| 概念 | 定义 | 例子 |
|------|------|------|
| 函数依赖 | 通过 A 的值可唯一确定 B 的值（A → B） | 学号 → 姓名 |
| 完全函数依赖 | A 是属性组，B 的确定**需要 A 中全部属性** | （学号, 课程名）→ 分数 |
| 部分函数依赖 | B 只需依赖 A 中的**部分属性** | （学号, 课程名）→ 姓名（只需学号） |
| 传递函数依赖 | A → B，B → C，则 C 传递依赖于 A | 学号 → 系名 → 系主任 |
| 码（候选键） | 能被其余所有属性完全依赖的属性（组） | （学号, 课程名） |

- **主属性**：包含在任一码中的属性。
- **非主属性**：不包含在任何码中的属性。

#### 第二范式（2NF）：消除非主属性对码的部分依赖

在 1NF 基础上，**非主属性必须完全依赖于码**（不能只依赖联合主键的一部分）。

**违反 2NF**（码 = 学号 + 课程名）：`姓名`、`系名` 只依赖 `学号`，与 `课程名` 无关。

| 学号 | 课程名 | 姓名 | 系名 | 分数 |
|------|--------|------|------|------|
| 1001 | 数据库 | 张三 | 计算机 | 92 |

**拆分后**：`学生表(学号, 姓名, 系名)` + `选课表(学号, 课程名, 分数)`，
每张表的非主属性都完全依赖于自己的码。

#### 第三范式（3NF）：消除传递依赖

在 2NF 基础上，**任何非主属性不能依赖于其它非主属性**。

```text
❌ 违反 3NF：学生表(学号, 姓名, 系名, 系主任)
   学号 → 系名 → 系主任，系主任传递依赖于学号

✅ 拆分后
学生表(学号, 姓名, 系名)
系表(系名, 系主任)
```

一句话总结：**"每个非主属性都直接依赖码，而不依赖其他非主属性"**。

### 7.2 反范式：为什么真实系统不追求 3NF

范式消除了冗余，代价是**更多 JOIN**。JOIN 在分库分表后代价极高，因此互联网系统普遍做**适度冗余**：

| 场景 | 反范式做法 | 收益 | 代价 |
|------|-----------|------|------|
| 订单列表要显示用户名 | `order` 表冗余 `user_name` | 省一次 JOIN | 用户改名需异步同步 |
| 商品列表要显示类目名 | `goods` 表冗余 `category_name` | 省一次 JOIN | 类目改名需批量更新 |
| 统计看板 | 建汇总表 / 物化统计字段 | 避免实时聚合 | 需要定时任务或触发器维护 |
| 高频查询组合 | 建联合索引覆盖 | 避免回表 | 写入放大、占用空间 |

**判断标准**：如果冗余字段的**变更频率远低于读取频率**，且业务允许短暂不一致，就可以冗余。

### 7.3 表关系建模

| 关系 | 例子 | 实现方式 |
|------|------|----------|
| 一对一 | 人 ↔ 身份证 | 任意一方加**唯一外键**指向对方主键；或干脆合成一张表 |
| 一对多 | 部门 ↔ 员工 | **多的一方**加外键，指向一的一方的主键 |
| 多对多 | 学生 ↔ 课程 | 建**中间表**，两个字段各指向一张表的主键，用**联合主键** |

```sql
-- 一对多：员工表持有 dept_id
CREATE TABLE department (
  id        INT PRIMARY KEY AUTO_INCREMENT,
  dept_name VARCHAR(50) NOT NULL
);

CREATE TABLE employee (
  id      INT PRIMARY KEY AUTO_INCREMENT,
  name    VARCHAR(50) NOT NULL,
  dept_id INT NOT NULL,
  CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES department (id)
);

-- 多对多：学生选课中间表
CREATE TABLE student (
  id   INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL
);

CREATE TABLE course (
  id   INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL
);

CREATE TABLE student_course (
  student_id INT NOT NULL,
  course_id  INT NOT NULL,
  score      DECIMAL(5, 2),
  PRIMARY KEY (student_id, course_id),                          -- 联合主键，天然防重复选课
  KEY idx_course (course_id),                                    -- 反向查询走这个索引
  CONSTRAINT fk_sc_student FOREIGN KEY (student_id) REFERENCES student (id),
  CONSTRAINT fk_sc_course  FOREIGN KEY (course_id)  REFERENCES course (id)
);
```

> 中间表的联合主键顺序有讲究：`(student_id, course_id)` 让"查某学生的课"走索引，
> 若还要"查某课程的学生"，必须补一个反向索引 `(course_id)`。

### 7.4 建表规范清单

| 项目 | 规范 | 理由 |
|------|------|------|
| 主键 | 必须有，`BIGINT UNSIGNED AUTO_INCREMENT` | 有序、定长、避免页分裂 |
| 字符集 | `utf8mb4` + `utf8mb4_0900_ai_ci` | 支持 emoji，排序规则统一 |
| 时间字段 | `created_at` / `updated_at` 全表必备 | 排查问题、增量同步的依据 |
| 布尔字段 | `is_xxx TINYINT`，不用 `BOOLEAN` | `BOOLEAN` 只是 `TINYINT(1)` 的别名 |
| 软删除 | `is_deleted TINYINT DEFAULT 0` | 但要注意它会让唯一索引失效（见下） |
| 金额 | `DECIMAL`，禁止 `FLOAT/DOUBLE` | 浮点误差 |
| 字段长度 | 按实际需要，不要一律 `VARCHAR(255)` | 索引大小、内存占用 |
| 索引数量 | 单表 ≤ 5 个 | 每个索引都是一次写放大 |
| 表/字段注释 | `COMMENT` 必填 | 三个月后你会感谢自己 |

> **软删除 + 唯一索引的冲突**：`is_deleted` 置 1 后，原唯一索引（如 `uk_phone`）仍占位，
> 同一手机号无法再次注册。三种解法：
> 1. 唯一索引改为 `(phone, is_deleted)`，但只能容忍一条删除记录；
> 2. 删除时把 `phone` 改写为 `phone_deleted_<id>`；
> 3. 用 `deleted_at`（NULL 表示未删），唯一索引改为 `(phone, deleted_at)`——NULL 不参与唯一冲突，
>    天然支持多次删除。

## 8. 索引

索引的本质是**用空间换时间**：把无序的数据按某种顺序组织成可快速定位的结构。
它是 MySQL 性能优化的第一杠杆——**90% 的慢查询靠加对索引解决**。

### 8.1 为什么是 B+ 树

| 结构 | 能否做 MySQL 索引 | 原因 |
|------|-------------------|------|
| 哈希表 | 部分（Memory 引擎） | 只支持等值查询，不支持范围、排序 |
| 二叉搜索树 | ❌ | 退化成链表时是 O(n) |
| 平衡二叉树（AVL/红黑树） | ❌ | 树高过大，每层一次磁盘 IO |
| B 树 | 可用 | 每个节点存数据，单节点扇出（分支数）小 |
| **B+ 树** | ✅ InnoDB 采用 | 非叶子节点只存键，**扇出极大，树高只有 3~4 层** |
| LSM 树 | ❌（用于 RocksDB/HBase） | 写优化，读放大 |

B+ 树的三个决定性优势：

1. **矮胖**：InnoDB 页 16KB，一个非叶子节点可存约 1170 个键（BIGINT 8 字节 + 指针 6 字节）。
   三层 B+ 树可索引 `1170 × 1170 × 16 ≈ 2100 万` 行，**任何查询最多 3 次磁盘 IO**。
2. **叶子节点双向链表**：范围查询、`ORDER BY` 只需顺着链表扫，不用回到根节点。
3. **数据只在叶子节点**：非叶子节点不存数据，同样大小的页能装更多键，进一步压低树高。

### 8.2 聚簇索引与二级索引

```text
【聚簇索引】主键索引，叶子节点就是数据本身

  根节点（只存主键键值）
    ├──► 叶子页 10：id=10, name='张三', salary=18000, ...
    └──► 叶子页 20：id=20, name='李四', salary=22000, ...
             ↑ 叶子页之间用双向链表相连，范围查询顺序扫描

【二级索引】如 idx_name，叶子节点只存「索引列 + 主键值」

  根节点（只存 name 键值）
    └──► 叶子：'张三' → 1001
              ↑ 要取 salary，必须拿 1001 回聚簇索引再查一次 → 这就是「回表」
```

由此得出三个核心结论：

- **每张 InnoDB 表有且只有一个聚簇索引**，就是主键索引。没有主键时，InnoDB 选第一个非空唯一索引；
  都没有则隐式创建 6 字节的 `DB_ROW_ID`。
- **二级索引查询需要"回表"**：先在二级索引找到主键，再用主键查聚簇索引。**回表是随机 IO，代价高**。
- **主键不能太长**：所有二级索引的叶子节点都存主键值，主键每多 8 字节，每个二级索引都膨胀 8 字节。
  这是"不要用 UUID 做主键"的根本原因（`BINARY(16)` 可接受，`CHAR(36)` 不行）。

### 8.3 索引类型与创建

```sql
-- 主键索引（聚簇索引）
ALTER TABLE employee ADD PRIMARY KEY (id);

-- 唯一索引（值唯一，允许多个 NULL）
ALTER TABLE employee ADD UNIQUE KEY uk_phone (phone);

-- 普通索引（最常见）
ALTER TABLE employee ADD KEY idx_dept (dept_id);

-- 联合索引（多列组合，遵循最左前缀）
ALTER TABLE employee ADD KEY idx_dept_salary (dept_id, salary);

-- 前缀索引（长字符串只索引前 N 个字符，省空间）
ALTER TABLE employee ADD KEY idx_name_prefix (name(10));

-- 全文索引（中文需 ngram 分词器）
ALTER TABLE article ADD FULLTEXT KEY ft_content (content) WITH PARSER ngram;

-- 8.0：函数索引（直接索引表达式，无需生成列）
ALTER TABLE employee ADD KEY idx_year ((YEAR(created_at)));

-- 8.0：不可见索引（先设为不可见观察，确认无影响后再删，安全的删索引方式）
ALTER TABLE employee ALTER INDEX idx_dept INVISIBLE;
ALTER TABLE employee ALTER INDEX idx_dept VISIBLE;

-- 查看索引
SHOW INDEX FROM employee;
```

**前缀索引的选择性**：前缀长度应让选择性接近全列。

```sql
-- 逐步加大前缀长度，直到 distinct 值数量接近全列
SELECT COUNT(DISTINCT LEFT(name, 5))  / COUNT(*) AS sel_5,
       COUNT(DISTINCT LEFT(name, 10)) / COUNT(*) AS sel_10,
       COUNT(DISTINCT name)           / COUNT(*) AS sel_full
FROM employee;
```

> 前缀索引**无法用于覆盖索引**（因为拿不到完整值）和 `ORDER BY` / `GROUP BY`。

### 8.4 联合索引与最左前缀

联合索引 `(a, b, c)` 的排序规则是：**先按 a 排，a 相同再按 b 排，b 相同再按 c 排**。

```sql
ALTER TABLE employee ADD KEY idx_abc (dept_id, salary, name);
```

| 查询条件 | 是否走索引 | 用到几列 | 说明 |
|----------|-----------|----------|------|
| `dept_id = 10` | ✅ | a | 最左前缀 |
| `dept_id = 10 AND salary > 10000` | ✅ | a, b | b 用于范围 |
| `dept_id = 10 AND salary = 10000 AND name = '张三'` | ✅ | a, b, c | 全命中 |
| `salary = 10000` | ❌ | — | 缺最左列 a |
| `name = '张三'` | ❌ | — | 缺 a、b |
| `dept_id = 10 AND name = '张三'` | ⚠️ | 仅 a | b 断了，c 无法用索引定位 |
| `dept_id > 10 AND salary = 10000` | ⚠️ | 仅 a | **a 是范围，b 失效**（范围列之后的列无法定位） |

> **关键规则**：联合索引中**一旦某列使用了范围条件（`>`、`<`、`BETWEEN`、`LIKE 'x%'`），
> 它后面的列就无法再用于索引定位**——但仍可用于"索引下推"过滤（见 8.5）。
> 这与 `IN` 不同：`IN` 是多个等值，后续列仍可用。

**联合索引的列顺序原则**：

1. **等值条件列在前，范围条件列在后**。
2. **区分度高的列在前**（选择性 = `COUNT(DISTINCT col) / COUNT(*)`，越接近 1 越好）。
3. **考虑排序**：`ORDER BY` 的列顺序要与索引一致，且方向一致（8.0 支持降序索引）。

### 8.5 覆盖索引与索引下推

**覆盖索引**：查询需要的所有列都在索引里，**不需要回表**。

```sql
-- 假设有 idx_dept_salary (dept_id, salary)

-- ❌ 需要回表：SELECT 里有 name，索引中没有
SELECT name, salary FROM employee WHERE dept_id = 10;

-- ✅ 覆盖索引：只查 dept_id 和 salary，索引里都有
SELECT dept_id, salary FROM employee WHERE dept_id = 10;
-- EXPLAIN 的 Extra 会显示 Using index

-- 优化：把需要的列放进索引，一次查询免回表
ALTER TABLE employee ADD KEY idx_cover (dept_id, salary, name);
```

**索引下推（Index Condition Pushdown, ICP，5.6+）**：把 `WHERE` 中能用索引判断的条件下推到存储引擎层，
**减少回表次数**。

```sql
-- 索引 (dept_id, name)
SELECT * FROM employee WHERE dept_id = 10 AND name LIKE '%三';
```

| 无 ICP | 有 ICP（默认开启） |
|--------|-------------------|
| 用 `dept_id = 10` 找到一批主键 → **全部回表** → 回表后判断 `name LIKE '%三'` | 找到主键后先在索引上判断 `name LIKE '%三'` → **只对命中的行回表** |

`EXPLAIN` 的 `Extra` 中出现 `Using index condition` 即表示 ICP 生效。

### 8.6 索引失效的七种场景

| # | 场景 | 失效原因 | 正确写法 |
|---|------|----------|----------|
| 1 | `WHERE YEAR(created_at) = 2024` | 列上做函数运算 | `created_at >= '2024-01-01' AND created_at < '2025-01-01'` |
| 2 | `WHERE id + 1 = 100` | 列上做算术运算 | `WHERE id = 99` |
| 3 | `WHERE phone = 13800000000`（phone 是 varchar） | **隐式类型转换**，等价于 `CAST(phone AS INT)` | `WHERE phone = '13800000000'` |
| 4 | `WHERE name LIKE '%三%'` | 前导通配符 | 改为后缀匹配，或上 ES / 全文索引 |
| 5 | `WHERE a = 1 OR b = 2`（b 无索引） | OR 中有一侧无索引则整体走全表 | 给 b 加索引，或改 `UNION ALL` |
| 6 | `WHERE dept_id = 10 AND name = 'x'`（索引 `(name, dept_id)`） | 不满足最左前缀 | 调整索引列顺序 |
| 7 | `WHERE status != 1` / `NOT IN` | 优化器判断走索引不如全表扫 | 改为 `IN` 正向枚举 |

**隐式转换是最隐蔽的坑**，务必注意：

```sql
-- ❌ 索引失效：字符串列用数字比较，MySQL 把列转成数字，索引废掉
SELECT * FROM employee WHERE phone = 13800000000;

-- ✅ 索引有效
SELECT * FROM employee WHERE phone = '13800000000';
```

> **一个反直觉的点**：`WHERE int_col = '10'` 是**有效的**（MySQL 把字符串常量转成数字，列本身不变）。
> 规则是"**谁被转换谁就失去索引**"——列被转换才失效，常量被转换不影响。

**索引失效不等于一定全表扫**：优化器是**基于成本**决策的。当表很小（几百行）或筛选出的行占比很高
（如 `status` 只有两种值且各占 50%）时，"不走索引"反而是正确选择。判断依据永远是 `EXPLAIN`。

### 8.7 索引设计原则

| 原则 | 说明 |
|------|------|
| **为查询建索引，不为字段建索引** | 索引要匹配实际的 `WHERE` / `ORDER BY` / `JOIN` 组合 |
| **优先建联合索引** | 一个 `(a, b, c)` 可顶 `(a)`、`(a,b)`、`(a,b,c)` 三个索引 |
| **单表索引 ≤ 5 个** | 每个索引都增加写入成本（B+ 树维护 + redo） |
| **区分度低的列不单独建索引** | 性别、状态等列单独建索引几乎无效，但可作为联合索引的后缀 |
| **尽量覆盖高频查询** | 用覆盖索引消除回表 |
| **避免冗余索引** | `(a)` 是 `(a, b)` 的前缀，前者可删 |
| **长字符串用前缀索引** | 或用哈希列（`crc32(url)`）建索引 |
| **外键列必须建索引** | 否则父表删除时子表会锁全表 |

```sql
-- 查看冗余索引与未使用索引（8.0 的 sys schema）
SELECT * FROM sys.schema_redundant_indexes;
SELECT * FROM sys.schema_unused_indexes;
```

## 9. 事务

### 9.1 事务的概念

**事务**是一组不可分割的数据库操作序列，要么全部成功，要么全部失败。

以转账为例：张三给李四转 500 元，必须"扣款"和"入账"同时生效。

```sql
CREATE TABLE account (
  id      INT PRIMARY KEY AUTO_INCREMENT,
  name    VARCHAR(10),
  balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00
);

INSERT INTO account (name, balance) VALUES ('zhangsan', 1000.00), ('lisi', 1000.00);

-- 开始事务
START TRANSACTION;

-- 1. 张三 -500
UPDATE account SET balance = balance - 500 WHERE name = 'zhangsan';

-- 2. 李四 +500（若此处失败，前面的扣款必须撤销）
UPDATE account SET balance = balance + 500 WHERE name = 'lisi';

-- 校验中间结果（可选）：此时其他会话读不到未提交的变更
SELECT * FROM account;

-- 一切正常则提交
COMMIT;

-- 若发现问题，回滚到事务开始前的状态
-- ROLLBACK;
```

### 9.2 事务控制语句

```sql
START TRANSACTION;                        -- 开启事务（或 BEGIN）
COMMIT;                                   -- 提交
ROLLBACK;                                 -- 回滚全部

-- 保存点：部分回滚（嵌套事务的替代方案）
START TRANSACTION;
UPDATE account SET balance = balance - 100 WHERE name = 'zhangsan';
SAVEPOINT sp1;
UPDATE account SET balance = balance - 100 WHERE name = 'lisi';
ROLLBACK TO SAVEPOINT sp1;                -- 只撤销 sp1 之后的操作
COMMIT;                                   -- 提交 sp1 之前的扣款

-- 只读事务（可减少事务 ID 分配，提升只读性能）
START TRANSACTION READ ONLY;
```

### 9.3 自动提交

MySQL **默认自动提交**（`autocommit = 1`），即每条 DML 都是一次独立事务。

```sql
-- 查看当前会话的提交模式
SELECT @@autocommit;        -- 1 = 自动提交，0 = 手动提交

-- 改为手动提交（Oracle / PostgreSQL 默认手动，MySQL 相反）
SET autocommit = 0;
-- 此后每条 DML 都需要显式 COMMIT，否则连接断开时自动回滚
SET autocommit = 1;         -- 恢复
```

| 数据库 | 默认提交模式 |
|--------|-------------|
| MySQL | 自动提交 |
| Oracle | 手动提交 |
| PostgreSQL | 自动提交（同 MySQL） |

> **连接池陷阱**：使用连接池时，`SET autocommit = 0` 会被后续借用的请求继承，
> 导致"改了数据但没提交、别人看不到"。**必须用 `START TRANSACTION` 而不是全局改 `autocommit`**，
> 并确保连接归还前 `COMMIT`/`ROLLBACK`。

### 9.4 ACID

| 特性 | 含义 | InnoDB 的实现手段 |
|------|------|-------------------|
| **原子性**（Atomicity） | 事务是不可分割的最小单位，要么全成，要么全败 | **undo log**：记录反向操作，回滚时逆序执行 |
| **一致性**（Consistency） | 事务前后数据满足所有约束（业务 + 数据库约束） | 由**应用层 + 约束 + 其他三个特性共同保证**，数据库本身只保证约束层面 |
| **隔离性**（Isolation） | 并发事务互不干扰 | **锁 + MVCC** |
| **持久性**（Durability） | 提交后的数据永久保存，崩溃不丢 | **redo log**（WAL：先写日志再写数据页） |

一致性是"目的"，原子性、隔离性、持久性是"手段"——这是理解 ACID 的最佳角度。

### 9.5 并发事务的三大问题

| 问题 | 定义 | 示例 |
|------|------|------|
| **脏读**（Dirty Read） | 读到其他事务**未提交**的数据 | A 事务改了余额未提交，B 读到新余额，A 回滚后 B 的数据是错的 |
| **不可重复读**（Non-Repeatable Read） | 同一事务内两次读**同一行**，结果不同 | A 第一次读余额 1000，B 提交了扣款，A 再读变 500 |
| **幻读**（Phantom Read） | 同一事务内两次**范围查询**，行数不同 | A 查"工资 > 20000 有 5 人"，B 插入 1 人并提交，A 再查变 6 人 |

**不可重复读 vs 幻读**：前者针对**已有行的修改**（`UPDATE`），后者针对**新插入的行**（`INSERT`）。
前者用行锁解决，后者必须用**间隙锁**或**串行化**解决。

### 9.6 隔离级别

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | 说明 |
|----------|------|-----------|------|------|
| `READ UNCOMMITTED` | 可能 | 可能 | 可能 | 几乎不用 |
| `READ COMMITTED` | 不可能 | 可能 | 可能 | Oracle/PG 默认，适合高并发 |
| `REPEATABLE READ` | 不可能 | 不可能 | 基本不可能 | **MySQL 默认**，InnoDB 用间隙锁补上 |
| `SERIALIZABLE` | 不可能 | 不可能 | 不可能 | 全部加锁，并发极差 |

> **关于 RR 级别的幻读**：SQL 标准中 RR 允许幻读，但 **InnoDB 在 RR 下通过"当前读 + 临键锁"
> 基本消除了幻读**。需要精确理解的两点：
> 1. **快照读**（普通 `SELECT`）通过 MVCC 保证不出现幻读；
> 2. **当前读**（`SELECT ... FOR UPDATE`、`UPDATE`、`DELETE`）通过临键锁保证不出现幻读。
>
> 所以"MySQL 的 RR 能防幻读"在 InnoDB 下成立，但这**不是标准行为**，换数据库不成立。

```sql
-- 查看当前隔离级别（8.0 语法）
SELECT @@transaction_isolation;
-- 5.7 及以前：SELECT @@tx_isolation;

-- 设置隔离级别（会话级）
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 全局设置（需重连生效，写入 my.cnf 更可靠）
SET GLOBAL TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

**RR 与 RC 的取舍**：

| 维度 | REPEATABLE READ | READ COMMITTED |
|------|-----------------|----------------|
| 数据一致性 | 整个事务看到同一快照 | 每条语句看到最新已提交 |
| 间隙锁 | 有 → **更易死锁** | 无 → 死锁更少 |
| undo log 保留 | 事务期间不能清理**（长事务会撑大 undo 表空间）** | 语句结束即可清理 |
| 主从一致性 | binlog `STATEMENT` 格式下更安全 | 需 `ROW` 格式 |
| 适用场景 | 默认，业务逻辑依赖快照一致 | 高并发写入、短事务 |

### 9.7 MVCC：多版本并发控制

MVCC 让**读不加锁、读写不阻塞**，是 InnoDB 高并发的核心。

#### 实现三要素

1. **隐藏字段**（每行都有）：
   - `DB_TRX_ID`（6 字节）：最后修改该行的事务 ID。
   - `DB_ROLL_PTR`（7 字节）：指向 undo log 中的历史版本。
   - `DB_ROW_ID`（6 字节）：无主键时生成的隐式主键。
2. **undo log**：记录行的历史版本，通过 `DB_ROLL_PTR` 串成版本链。
3. **ReadView**：事务快照，决定"能看到哪个版本"。

#### 版本链示例

```text
当前行（DB_TRX_ID = 300）
  └─ DB_ROLL_PTR ──► undo: 版本 trx=200（salary=15000）
                        └─ DB_ROLL_PTR ──► undo: 版本 trx=100（salary=12000）
```

#### ReadView 的可见性判断

ReadView 有四个关键字段：

| 字段 | 含义 |
|------|------|
| `m_ids` | 生成快照时**活跃（未提交）**的事务 ID 列表 |
| `min_trx_id` | `m_ids` 中的最小值 |
| `max_trx_id` | 生成快照时**下一个将分配**的事务 ID |
| `creator_trx_id` | 创建该 ReadView 的事务 ID |

判断某版本（`trx_id`）是否可见：

```text
判断步骤（按顺序，命中即返回）：
  ① trx_id == creator_trx_id   → 可见（自己改的自己看得到）
  ② trx_id <  min_trx_id       → 可见（该事务早已提交）
  ③ trx_id >= max_trx_id       → 不可见（在我之后才开启的事务）
  ④ min_trx_id <= trx_id < max_trx_id
       ├─ trx_id 在 m_ids 中    → 不可见（当时还活跃，未提交）
       └─ trx_id 不在 m_ids 中  → 可见（当时已提交）

若判定不可见，顺着 DB_ROLL_PTR 找上一个历史版本，重复上述判断。
```

#### RC 与 RR 的本质区别

| 级别 | ReadView 生成时机 | 效果 |
|------|-------------------|------|
| `READ COMMITTED` | **每条 SELECT** 都生成新 ReadView | 能看到别人刚提交的数据 → 不可重复读 |
| `REPEATABLE READ` | **事务中第一条 SELECT** 时生成一次 | 整个事务看到同一快照 → 可重复读 |

这就是"RR 靠 MVCC 实现可重复读"的完整机制。

> **快照读 vs 当前读**：
> - 快照读：普通 `SELECT`，读 ReadView 可见的历史版本，**不加锁**。
> - 当前读：`SELECT ... FOR UPDATE` / `FOR SHARE`、`UPDATE`、`DELETE`、`INSERT`，
>   读**最新版本**并加锁，是"读到最新数据"的唯一方式。

## 10. 锁

### 10.1 按读写性质分：共享锁与排他锁

| 锁类型 | 别名 | 关键字 | 兼容性 |
|--------|------|--------|--------|
| **共享锁**（S） | 读锁 | `LOCK IN SHARE MODE` / `FOR SHARE` | 多个 S 可共存，S 与 X 互斥 |
| **排他锁**（X） | 写锁 | `FOR UPDATE` | 与任何锁都互斥 |

```sql
-- 共享锁：允许其他事务也加 S 锁，但阻塞 X 锁（8.0 语法）
SELECT * FROM account WHERE id = 1 FOR SHARE;
-- 8.0 之前：SELECT * FROM account WHERE id = 1 LOCK IN SHARE MODE;

-- 排他锁：阻塞其他事务的任何锁
SELECT * FROM account WHERE id = 1 FOR UPDATE;

-- 跳过被锁的行（避免等待，抢锁场景常用）
SELECT * FROM account WHERE id = 1 FOR UPDATE SKIP LOCKED;

-- 只等 2 秒，超时放弃（避免长阻塞）
SELECT * FROM account WHERE id = 1 FOR UPDATE NOWAIT;
```

**兼容性矩阵**：

| | S 锁 | X 锁 |
|---|------|------|
| **S 锁** | ✅ 兼容 | ❌ 冲突 |
| **X 锁** | ❌ 冲突 | ❌ 冲突 |

> **重要**：普通 `SELECT`（快照读）**不加任何锁**。`UPDATE` / `DELETE` 会自动加 X 锁。
> 唯一索引的等值更新若值未变化，InnoDB 会**优化掉锁**（只有真正修改才加锁）。

### 10.2 按粒度分：表锁与行锁

| 粒度 | 加锁方式 | 特点 | 适用 |
|------|----------|------|------|
| **表锁** | `LOCK TABLES ... READ/WRITE` | 开销小、并发差 | MyISAM、DDL、备份 |
| **行锁** | InnoDB 自动，基于索引 | 开销大、并发好 | OLTP 主力 |
| **意向锁** | InnoDB 自动（表级） | 快速判断表中是否有行锁 | 配合表锁使用 |

```sql
-- 显式表锁（一般只在维护时用，且会阻塞所有业务写入）
LOCK TABLES account READ;
UNLOCK TABLES;

-- 查看表锁等待
SHOW STATUS LIKE 'Table_locks%';
```

**行锁的关键前提**：**InnoDB 的行锁是加在索引上的**。如果 `WHERE` 条件没有走索引，
InnoDB 会扫描全部行并给每一行加锁，效果等同于**锁全表**。

```sql
-- 假设 name 上没有索引
-- 这条语句会给表中所有行加锁，其他事务插不进任何数据
UPDATE employee SET salary = salary + 100 WHERE name = '张三';
```

### 10.3 意向锁

意向锁是**表级锁**，作用是让"表锁"能快速判断"表里是否有行锁"，无需逐行检查。

| 意向锁 | 含义 |
|--------|------|
| `IS`（意向共享锁） | 事务准备给某行加 S 锁 |
| `IX`（意向排他锁） | 事务准备给某行加 X 锁 |

加锁顺序是**先表后行**：事务给行加 S 锁前，先给表加 IS；加 X 锁前，先加 IX。
意向锁之间**互相兼容**（IS 与 IX 可共存），只与表级的 S/X 锁互斥。

### 10.4 行锁的三种形态：记录锁、间隙锁、临键锁

| 类型 | 锁定范围 | 解决的问题 |
|------|----------|-----------|
| **记录锁**（Record Lock） | 锁定**索引上的一条记录** | 防止该行被并发修改 |
| **间隙锁**（Gap Lock） | 锁定**两条记录之间的间隙**（不含记录本身） | 防止在间隙中插入新行 → **防幻读** |
| **临键锁**（Next-Key Lock） | 记录锁 + 间隙锁，锁定**左开右闭区间** `(a, b]` | InnoDB RR 的默认行锁形态 |

```text
假设主键值：5, 10, 15, 20

SELECT * FROM t WHERE id = 12 FOR UPDATE;   -- 落在间隙 (10, 20)
        ↓
加临键锁 (10, 20]，锁住 (10, 20] 区间，其他事务无法插入 11~20

SELECT * FROM t WHERE id = 10 FOR UPDATE;   -- 命中唯一索引的等值查询
        ↓
退化为记录锁，只锁 id=10，不锁间隙（唯一索引等值命中时）

SELECT * FROM t WHERE id BETWEEN 10 AND 15 FOR UPDATE;
        ↓
临键锁 (5, 10] + (10, 15]，范围查询会锁住区间及两侧间隙
```

三条规则：

1. **唯一索引 + 等值查询 + 记录存在** → 临键锁退化为**记录锁**。
2. **唯一索引 + 等值查询 + 记录不存在** → 退化为**间隙锁**。
3. **非唯一索引 / 范围查询** → 使用**临键锁**。

> **间隙锁只在 RR 及以上级别生效**。RC 级别下**没有间隙锁**（这也是很多公司把级别改成 RC 的原因：
> 大幅减少死锁），代价是需要依赖 `binlog=ROW` 保证主从一致。
>
> 间隙锁之间**互相兼容**——两个事务可以同时持有同一间隙的间隙锁，但都无法插入。
> 这是死锁的常见来源。

### 10.5 死锁

**死锁成因**：两个事务互相持有对方需要的锁，形成环路。

```text
事务 A：UPDATE account SET ... WHERE id = 1;   -- 持有 id=1 的 X 锁
事务 B：UPDATE account SET ... WHERE id = 2;   -- 持有 id=2 的 X 锁
事务 A：UPDATE account SET ... WHERE id = 2;   -- 等待 B 释放 → 阻塞
事务 B：UPDATE account SET ... WHERE id = 1;   -- 等待 A 释放 → 死锁
```

InnoDB 会**自动检测死锁并回滚代价较小的事务**（报 `Deadlock found when trying to get lock`）。

```sql
-- 查看最近一次死锁的详细信息
SHOW ENGINE INNODB STATUS\G
-- 关注 LATEST DETECTED DEADLOCK 段：两个事务的 SQL、持有的锁、等待的锁

-- 查看当前锁等待
SELECT * FROM performance_schema.data_locks;
SELECT * FROM performance_schema.data_lock_waits;

-- 查看锁等待超时时间（默认 50 秒）
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';
```

**避免死锁的四条实践**：

1. **统一加锁顺序**：所有事务按相同顺序（如按主键升序）访问资源。
2. **缩短事务**：事务内不做 RPC、不发 MQ、不做大计算。
3. **降低隔离级别**：RC 无间隙锁，死锁概率大幅下降。
4. **命中索引**：避免行锁升级为"锁全表"。
5. **应用层兜底**：捕获死锁异常后**重试**（幂等前提下）。

```java
// 死锁重试的标准写法（伪代码）
for (int attempt = 0; attempt < 3; attempt++) {
    try {
        return transactionTemplate.execute(status -> doTransfer(from, to, amount));
    } catch (DeadlockLoserDataAccessException e) {
        // 指数退避后重试，仅对死锁异常重试，不要对其他异常重试
        sleep(50L << attempt);
    }
}
throw new IllegalStateException("转账失败，请稍后重试");
```

## 11. 性能优化

### 11.1 定位问题：慢查询日志

优化的第一步永远是**找到慢在哪**，不要凭感觉调。

```sql
-- 开启慢查询日志（生产建议写配置文件，而非动态开启）
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;              -- 超过 1 秒记录
SET GLOBAL log_queries_not_using_indexes = ON;  -- 记录未走索引的语句（日志量会很大）

SHOW VARIABLES LIKE 'slow_query_log%';
SHOW VARIABLES LIKE 'long_query_time';

-- 用 mysqldumpslow 汇总（按总耗时排序 Top 10）
-- mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
```

```sql
-- 8.0 更推荐：performance_schema 直接查 Top SQL
SELECT digest_text,
       count_star                                    AS exec_count,
       ROUND(sum_timer_wait / 1e12, 3)               AS total_sec,
       ROUND(avg_timer_wait / 1e12, 3)               AS avg_sec,
       sum_rows_examined                             AS rows_examined
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_timer_wait DESC
LIMIT 10;
```

### 11.2 EXPLAIN 执行计划

```sql
EXPLAIN SELECT e.name, d.dept_name
FROM employee e
JOIN department d ON e.dept_id = d.id
WHERE e.salary > 15000;
```

| 列 | 关注点 |
|----|--------|
| `id` | 执行顺序，**id 越大越先执行**；相同则从上往下 |
| `select_type` | `SIMPLE` / `PRIMARY` / `SUBQUERY` / `DERIVED` / `UNION` |
| `table` | 正在访问的表 |
| `type` | **最重要的列**，访问类型（见下表） |
| `possible_keys` | 可能用到的索引 |
| `key` | **实际用到的索引**，为 `NULL` 说明没走索引 |
| `key_len` | 索引使用的字节数，可推断**联合索引用到了几列** |
| `ref` | 与索引比较的列或常量 |
| `rows` | 预估扫描行数，**越小越好** |
| `filtered` | 扫描后剩余行的百分比 |
| `Extra` | 额外信息，见下方 |

**`type` 的性能排序**（从好到坏）：

| type | 含义 | 评价 |
|------|------|------|
| `system` | 表只有一行 | 最优 |
| `const` | 主键/唯一索引等值查询，最多一行 | 最优 |
| `eq_ref` | 联表时被驱动表用主键/唯一索引匹配 | 很好 |
| `ref` | 普通索引等值查询 | 好 |
| `range` | 索引范围扫描（`BETWEEN`、`>`、`IN`） | 可接受 |
| `index` | **全索引扫描**（遍历整棵索引树） | 需优化 |
| `ALL` | **全表扫描** | 必须优化 |

**`Extra` 的常见值**：

| 值 | 含义 | 处理建议 |
|----|------|----------|
| `Using index` | 覆盖索引，无需回表 | ✅ 理想 |
| `Using index condition` | 索引下推生效 | ✅ 良好 |
| `Using where` | 在 Server 层过滤（索引未完全覆盖） | 检查能否加索引 |
| `Using filesort` | 需要额外排序（内存或磁盘） | 让 `ORDER BY` 走索引 |
| `Using temporary` | 用了临时表（`GROUP BY` / `DISTINCT` / `UNION`） | 优化分组或加索引 |
| `Using join buffer` | 联表无索引，用了 join buffer | 给被驱动表加索引 |

```sql
-- EXPLAIN ANALYZE（8.0.18+）：真实执行并给出各步骤实际耗时
EXPLAIN ANALYZE SELECT * FROM employee WHERE dept_id = 10;
```

> `EXPLAIN` 给的是**预估**，`EXPLAIN ANALYZE` 是**真实执行**。前者不跑 SQL，后者会跑（注意在只读库上做）。

### 11.3 SQL 优化清单

按见效速度排序：

| # | 优化项 | 做法 |
|---|--------|------|
| 1 | **加对索引** | 按 [8.7](#87-索引设计原则) 的原则建联合索引、覆盖索引 |
| 2 | **消除索引失效** | 按 [8.6](#86-索引失效的七种场景) 逐条自查 |
| 3 | **禁止 `SELECT *`** | 只取需要的列，才有机会走覆盖索引 |
| 4 | **小表驱动大表** | `JOIN` 时让小结果集做驱动表 |
| 5 | **避免大事务** | 批量操作分批提交（每批 500~1000 行） |
| 6 | **用 `UNION ALL` 代替 `UNION`** | 前者不去重，省一次排序 |
| 7 | **`EXISTS` 代替 `IN`**（子查询大时） | 见 [6.5](#65-子查询) |
| 8 | **批量插入代替循环单条** | 一条 SQL 多 `VALUES`，减少网络往返 |
| 9 | **`ORDER BY` / `GROUP BY` 走索引** | 排序列与索引列顺序、方向一致 |
| 10 | **拆分大字段** | `TEXT` / `BLOB` 单独成表，避免主表行溢出 |

```sql
-- ❌ 反例：循环 1000 次单条插入，1000 次网络往返 + 1000 次事务
-- for (row : rows) { INSERT INTO t VALUES (...); }

-- ✅ 正例：分批批量插入
INSERT INTO t (a, b, c) VALUES
(1, 'x', 100), (2, 'y', 200), (3, 'z', 300);
```

### 11.4 深分页优化

```sql
-- ❌ 深分页：必须扫描并丢弃前 100 万行，越翻越慢
SELECT * FROM orders ORDER BY id LIMIT 1000000, 10;
```

**方案一：游标分页（推荐，适用于"下一页"场景）**

```sql
-- 记住上一页最后一条的 id，用范围条件代替 OFFSET
SELECT * FROM orders WHERE id > 1000000 ORDER BY id LIMIT 10;
```

**方案二：延迟关联（必须跳页时）**

```sql
-- 先在索引上完成分页拿到主键，再用主键取数据
SELECT o.*
FROM orders o
JOIN (SELECT id FROM orders ORDER BY id LIMIT 1000000, 10) t ON o.id = t.id;
```

> 延迟关联的前提是 `ORDER BY` 的列**有索引**，使得子查询能走覆盖索引（`Using index`），
> 避免回表 100 万次。如果 `ORDER BY` 是无索引列，两种方案都会慢，只能上 ES。

### 11.5 大表 DDL 与在线变更

`ALTER TABLE` 在 5.6 之前会**锁表重建**，大表可能导致分钟级不可写。8.0 支持 **Online DDL**：

```sql
-- 显式声明在线 DDL：不锁表，允许并发读写
ALTER TABLE orders ADD COLUMN remark VARCHAR(200) NULL, ALGORITHM = INPLACE, LOCK = NONE;

-- 若语法不支持，会直接报错而不是悄悄锁表（这正是显式声明的好处）
```

| 操作 | 是否支持 Online | 备注 |
|------|----------------|------|
| 加/删索引 | ✅ | 最常见，影响小 |
| 加列（末尾） | ✅ | 秒级完成 |
| 加列（`AFTER` / 首位） | ❌ | 需重建表 |
| 改列类型 | ❌ | 需重建表（`VARCHAR` 扩长在部分情况可 INPLACE） |
| 改字符集 | ❌ | 需重建表 |
| 加外键 | ❌ | 需 `foreign_key_checks=0` |

超大表（千万级以上）的通用做法：

1. **`pt-online-schema-change`**：建影子表 + 触发器同步 + 原子 rename。
2. **`gh-ost`**：基于 binlog 同步，无触发器，对主库压力更小（GitHub 出品）。
3. **业务低峰期执行** + 主从切换：先在从库改，再切主。

### 11.6 Buffer Pool 与关键参数

| 参数 | 建议值 | 说明 |
|------|--------|------|
| `innodb_buffer_pool_size` | 物理内存的 **50%~70%** | 最重要的参数，缓存数据页与索引页 |
| `innodb_buffer_pool_instances` | 8（缓冲池 > 8GB 时） | 减少争用 |
| `innodb_log_file_size` | 1~2GB | redo log 大小，太小会导致频繁 checkpoint |
| `innodb_flush_log_at_trx_commit` | `1`（强一致）/ `2`（高性能） | 1=每次提交刷盘，2=每秒刷盘 |
| `sync_binlog` | `1`（强一致） | 1=每次提交刷 binlog |
| `innodb_io_capacity` | SSD 2000 | 控制刷脏页速率 |
| `max_connections` | 按并发量 | 连接数过多会拖垮实例，优先用连接池 |

> `innodb_flush_log_at_trx_commit=1` + `sync_binlog=1` 即所谓的**"双 1 配置"**，
> 保证不丢数据（金融级要求），代价是每次提交两次 fsync。日志型业务可降到 `2` / `0`。

## 12. 架构与高可用

### 12.1 三种日志与两阶段提交

| 日志 | 所属层 | 内容 | 作用 |
|------|--------|------|------|
| **redo log** | InnoDB | 物理页修改（"在某个页的某偏移写入什么"） | **崩溃恢复**，实现持久性 |
| **undo log** | InnoDB | 逻辑反向操作 | **回滚** + **MVCC 版本链** |
| **binlog** | Server | 逻辑变更（SQL 或行变更） | **主从复制** + **数据恢复** |

**WAL（Write-Ahead Logging）**：修改数据时先写 redo log（顺序写，快），再异步刷数据页（随机写，慢）。
这样把随机写变成了顺序写，是 InnoDB 高性能的关键。

**两阶段提交**：redo log 和 binlog 是两套独立日志，必须保证一致，否则主从数据会错乱。

```text
① 写 redo log，标记为 prepare 状态
② 写 binlog
③ 提交事务，redo log 标记为 commit 状态
```

崩溃恢复的判断规则：

- redo log 是 `commit` → 直接应用。
- redo log 是 `prepare` → **检查 binlog 是否完整**：完整则提交，不完整则回滚。

**binlog 的三种格式**：

| 格式 | 内容 | 优点 | 缺点 |
|------|------|------|------|
| `STATEMENT` | 原始 SQL | 日志小 | 含 `NOW()`、`UUID()`、`LIMIT` 的语句主从不一致 |
| `ROW` | 每行的变更前后值 | **绝对一致**，可用于数据恢复 | 日志大（批量更新会暴涨） |
| `MIXED` | 自动切换 | 折中 | 仍有不确定性 |

> 5.7.7 起默认 `ROW`。**生产必须用 `ROW`**——否则在 RC 隔离级别、或使用自增/非确定性函数时，
> 主从必然出现数据不一致。

```sql
SHOW VARIABLES LIKE 'binlog_format';
SHOW BINARY LOGS;                                    -- 列出所有 binlog 文件
SHOW BINLOG EVENTS IN 'binlog.000001' LIMIT 10;       -- 查看内容
```

### 12.2 主从复制

```text
【Master】接收写请求
    └─ ① 执行事务并写 binlog

【binlog 文件】
    └─ ② dump 线程读取 binlog，推送给 Slave
              │
              ▼
【Slave】
    ├─ ③ IO 线程接收 binlog，写入 relay log（中继日志）
    └─ ④ SQL 线程读取 relay log 并重放，数据追平 Master

【读请求】由 Slave 承担，写请求只走 Master
```

三个线程的分工：

| 线程 | 所在节点 | 职责 |
|------|----------|------|
| **dump 线程** | Master | 读取 binlog 并推送给 Slave |
| **IO 线程** | Slave | 接收 binlog，写入 relay log |
| **SQL 线程** | Slave | 读取 relay log 并重放 |

```sql
-- 主库：创建复制账号并授权
CREATE USER 'repl'@'%' IDENTIFIED BY 'StrongPwd!2024';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';

-- 从库：配置指向主库（8.0.23+ 语法）
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST = '10.0.0.10',
  SOURCE_PORT = 3306,
  SOURCE_USER = 'repl',
  SOURCE_PASSWORD = 'StrongPwd!2024',
  SOURCE_AUTO_POSITION = 1;      -- 使用 GTID 自动定位，推荐

START REPLICA;
SHOW REPLICA STATUS\G             -- 关注 Replica_IO_Running / Replica_SQL_Running 均为 Yes
```

**复制模式演进**：

| 模式 | 机制 | 数据安全性 | 性能 |
|------|------|-----------|------|
| 异步复制（默认） | 主库提交即返回，不等从库 | 主库宕机可能丢数据 | 最高 |
| 半同步复制 | 至少一个从库 ACK 后才返回 | 较好 | 中 |
| 组复制（MGR） | Paxos 多数派确认 | 高，支持自动选主 | 较低 |

```sql
-- 开启半同步（主从都需安装插件）
INSTALL PLUGIN rpl_semi_sync_master SONAME 'semisync_master.so';
SET GLOBAL rpl_semi_sync_master_enabled = 1;
SET GLOBAL rpl_semi_sync_master_timeout = 1000;   -- 1 秒未 ACK 则退化为异步
```

### 12.3 读写分离与主从延迟

**读写分离**：写走主库，读走从库。核心问题是**主从延迟**（主库已提交，从库还没重放）。

典型的不一致场景：用户下单后立即跳转订单详情页，读从库 → 查不到刚创建的订单。

| 解决方案 | 做法 | 适用 |
|----------|------|------|
| **强制走主库** | 写后的一段时间内（如 1 秒）读主库 | 简单有效，最常用 |
| **按业务分** | 支付、订单详情等强一致读走主库 | 有明确边界 |
| **半同步复制** | 至少一个从库确认后才返回 | 减少延迟窗口，不消除 |
| **GTID + 位点等待** | 记录主库 binlog 位点，从库追上才读 | 精确但需中间件支持 |

**延迟的常见原因**：

1. **从库压力大**：从库承担全部读流量，SQL 线程重放不过来（大事务是元凶）。
2. **大表 DDL**：从库串行重放 DDL，期间阻塞后续所有事务。
3. **无主键表**：`ROW` 格式下全表扫描定位行，重放极慢（**每张表必须有主键**）。
4. **从库配置差**：`innodb_flush_log_at_trx_commit=1` + 机械盘。

```sql
-- 监控延迟（Seconds_Behind_Source，单位为秒，但大事务时会失真）
SHOW REPLICA STATUS\G

-- 更准确：对比 GTID 或位点
SELECT @@gtid_executed;
```

> `Seconds_Behind_Source` 只反映"SQL 线程落后 IO 线程多少"，**不代表真实延迟**。
> 生产监控应同时采集：GTID 差值、心跳表（定期写时间戳）延迟。

### 12.4 分库分表

**什么时候才需要分**：单表 > 2000 万行或 > 50GB，且**索引优化已到极限**。
分表是最后手段，因为引入了分布式事务、跨库 JOIN、全局排序等一系列问题。

| 方案 | 拆分依据 | 优点 | 缺点 |
|------|----------|------|------|
| **垂直分库** | 按业务域（用户库、订单库） | 业务解耦 | 跨库 JOIN 消失 |
| **垂直分表** | 按字段冷热（主表 + 扩展表） | 主表变小，缓存命中率高 | 需两次查询 |
| **水平分表** | 按行（`user_id % 16`） | 单表可控 | 跨片查询、扩容迁移 |
| **水平分库** | 按行 + 多实例 | 突破单机上限 | 分布式事务 |

**分片键的选择**是分库分表最关键的决策：

- **必须高基数、分布均匀**，避免数据倾斜。
- **必须覆盖高频查询**，否则每次都要广播到所有分片。
- 常见做法：`user_id` 做分片键，`order_id` 用 `Snowflake` 生成并**把 `user_id` 编码进 ID**
  （如 `order_id % 1024` 反解出分片），实现"订单号直接定位分片"。

**跨分片问题的解法**：

| 问题 | 解法 |
|------|------|
| 跨分片分页 | 各分片取前 N 条 → 内存归并排序 → 取前 N（深分页不可行，改限制） |
| 跨分片聚合 | 上 ES / ClickHouse 做分析库，MySQL 只存明细 |
| 分布式事务 | 尽量**避免**：用本地消息表 + 最终一致，而非 2PC/XA |
| 全局唯一 ID | 号段模式（Leaf）、Snowflake、Redis `INCR` |
| 扩容 | 一致性哈希（减少迁移量）或成倍扩容 + 双写迁移 |

> 中间件选型：ShardingSphere-JDBC（客户端，无代理开销）、MyCat（代理，语言无关）、
> Vitess（云原生，K8s 友好）。规模不大时优先考虑**先不拆**。

### 12.5 备份与恢复

| 方式 | 工具 | 特点 |
|------|------|------|
| 逻辑备份 | `mysqldump` | 可读、跨版本，**大库慢** |
| 逻辑备份（并行） | `mydumper` / `mysqlpump` | 多线程，快数倍 |
| 物理备份 | **XtraBackup** | **热备**，大库首选，支持增量 |
| 快照备份 | LVM / 云盘快照 | 秒级，依赖基础设施 |

```bash
# 逻辑备份（单库，含存储过程与触发器）
mysqldump -u root -p --single-transaction --routines --triggers \
  --set-gtid-purged=OFF shop > shop_20261026.sql

# 恢复
mysql -u root -p shop < shop_20261026.sql

# 物理备份（XtraBackup，不停机）
xtrabackup --backup --target-dir=/backup/full --user=root --password=***

# 准备（apply redo log，使备份一致）
xtrabackup --prepare --target-dir=/backup/full
```

> **`--single-transaction` 是 InnoDB 热备的关键**：它在 RR 隔离级别下开启一个一致性快照事务，
> 保证备份期间数据一致，且**不锁表**。但**只对 InnoDB 有效**，MyISAM 表仍会锁。
>
> **备份必须验证恢复**——没验证过的备份等于没有备份。建议每季度做一次恢复演练。

## 13. 常用命令速查

```sql
-- ===== 连接与库 =====
mysql -h 10.0.0.10 -P 3306 -u root -p shop       -- 命令行登录
SHOW DATABASES;
USE shop;
SELECT DATABASE(), VERSION(), USER(), NOW();

-- ===== 表与结构 =====
SHOW TABLES;
SHOW CREATE TABLE employee\G
DESC employee;

-- ===== 状态与进程 =====
SHOW PROCESSLIST;                                 -- 当前连接与执行中的 SQL
SHOW FULL PROCESSLIST;                            -- 含完整 SQL
SELECT * FROM information_schema.processlist WHERE time > 10;   -- 超过 10 秒的

-- ===== 变量与配置 =====
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SET GLOBAL long_query_time = 1;
SET SESSION sql_mode = 'STRICT_TRANS_TABLES';

-- ===== 锁与事务 =====
SHOW ENGINE INNODB STATUS\G                       -- 死锁、锁等待、事务详情
SELECT * FROM performance_schema.data_locks;
SELECT * FROM information_schema.innodb_trx;      -- 当前运行的事务

-- ===== 用户与权限 =====
CREATE USER 'app'@'10.0.0.%' IDENTIFIED BY 'Pwd!2024';
GRANT SELECT, INSERT, UPDATE ON shop.* TO 'app'@'10.0.0.%';
FLUSH PRIVILEGES;
SHOW GRANTS FOR 'app'@'10.0.0.%';

-- ===== 空间与容量 =====
SELECT table_name,
       ROUND(data_length / 1024 / 1024, 2)      AS data_mb,
       ROUND(index_length / 1024 / 1024, 2)     AS index_mb,
       table_rows
FROM information_schema.tables
WHERE table_schema = 'shop'
ORDER BY data_length DESC;
```

## 14. 常见问题排查

| 报错 / 现象 | 原因 | 处理 |
|-------------|------|------|
| `Too many connections` | 连接数打满 | 查 `SHOW PROCESSLIST` 找泄漏；调大 `max_connections`；检查连接池配置 |
| `Lock wait timeout exceeded` | 行锁等待超时（默认 50s） | 查 `data_lock_waits` 找阻塞源，`KILL` 长事务 |
| `Deadlock found when trying to get lock` | 死锁 | 查 `SHOW ENGINE INNODB STATUS`；统一加锁顺序；缩短事务；应用层重试 |
| `Incorrect string value: '\xF0\x9F...'` | 字符集为 `utf8`（三字节），存不了 emoji | 表和列都改为 `utf8mb4` |
| `Specified key was too long` | 索引长度超限（3072 字节 / InnoDB DYNAMIC） | 缩短索引列或用前缀索引 |
| `Data too long for column` | 值超列长度 | 加长列，或检查 `sql_mode` 是否严格模式 |
| `Duplicate entry 'x' for key 'uk_phone'` | 唯一键冲突 | 用 `ON DUPLICATE KEY UPDATE`，或先查后写（注意并发） |
| `Table 'shop.xxx' doesn't exist` | 库名/表名错，或大小写敏感 | Linux 下 `lower_case_table_names=0`，表名**大小写敏感** |
| `This version of MySQL doesn't yet support ...` | 语法超出当前版本 | 确认版本（如窗口函数需 8.0） |
| 查询突然变慢，索引没变 | 统计信息过期 / 执行计划漂移 | `ANALYZE TABLE` 更新统计信息；用 `FORCE INDEX` 临时兜底 |
| 磁盘空间持续增长 | undo 表空间膨胀 / binlog 堆积 | 检查长事务；`PURGE BINARY LOGS`；调 `binlog_expire_logs_seconds` |

```sql
-- 一次典型的"锁等待"排查流程
-- 1. 找到阻塞的会话
SELECT waiting_pid, blocking_pid, waiting_query, blocking_query
FROM sys.innodb_lock_waits;

-- 2. 确认阻塞事务跑了多久
SELECT trx_id, trx_state, trx_started,
       TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS seconds
FROM information_schema.innodb_trx
ORDER BY seconds DESC;

-- 3. 处理（谨慎！确认业务影响后再执行）
KILL <thread_id>;
```

## 15. 版本演进与选型提示

| 版本 | 关键变化 |
|------|----------|
| 5.6 | Online DDL、ICP（索引下推）、`DATETIME` 支持毫秒 |
| 5.7 | JSON 类型、生成列、`ONLY_FULL_GROUP_BY` 默认开启、多源复制 |
| 8.0 | 窗口函数、CTE、降序索引、不可见索引、函数索引、`utf8mb4` 默认、移除查询缓存、默认 `caching_sha2_password` |
| 8.0.19+ | 废弃 `INT(n)` 显示宽度 |
| 8.0.23+ | `CHANGE REPLICATION SOURCE TO` 语法（替代 `CHANGE MASTER TO`） |

**踩坑提醒**：

- 8.0 默认认证插件是 `caching_sha2_password`，老版本客户端/驱动可能连不上，
  需升级驱动或改回 `mysql_native_password`（8.0.34 起后者已标记废弃）。
- 8.0 **移除了查询缓存**（`query_cache_type`），不要再按 5.7 的经验调优。
- 8.0 的 `JSON` 与 `utf8mb4` 让很多 5.7 的"最佳实践"过时，遇到旧资料要先看版本。

## 16. 延伸阅读

- [[mysql-crash-course|MySQL 必知必会（语法速查）]]
- [[postgresql|PostgreSQL 基础]] · [[postgresql-advanced|PostgreSQL 特性与实战]]
- [[redis|Redis]] — 缓存与 MySQL 的经典配合（Cache-Aside、缓存穿透/击穿/雪崩）
- [[clickhouse|ClickHouse]] — OLAP 分析场景
- [[mongodb|MongoDB]] — 文档型数据库对比
- [[databases/index|数据库目录]]

**官方文档**

- [MySQL 8.0 Reference Manual](https://dev.mysql.com/doc/refman/8.0/en/)
- [InnoDB Locking](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html)
- [Optimization Overview](https://dev.mysql.com/doc/refman/8.0/en/optimization.html)

**推荐书目**

- 《高性能 MySQL》（第 4 版）— 索引、优化、架构的权威参考
- 《MySQL 技术内幕：InnoDB 存储引擎》— 原理层必读
- 《MySQL 实战 45 讲》— 实战视角的问题驱动讲解
