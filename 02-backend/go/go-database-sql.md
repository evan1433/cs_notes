---
title: Go 数据库访问：连接池、事务与取消
description: 使用 database/sql 和 pgx 访问 PostgreSQL，掌握参数化查询、连接池、事务回滚与请求取消。
tags:
  - go
  - postgresql
  - transaction
date: 2026-11-18
---

# Go 数据库访问：连接池、事务与取消

## 你将得到什么

本教程实现一个库存扣减与订单插入事务，成功时同时提交，失败时全部回滚。
SQL 与 Go 的边界同样重要：返回错误不能自动撤销先前执行的独立语句，必须显式建立事务。
前置知识为 [[go-errors-and-resources|错误处理]]、[[go-concurrency-and-context|context]] 和 [[postgresql|PostgreSQL]]。

环境要求：Go 1.24+、Docker、PostgreSQL 镜像 `postgres:17.12`。
Go 驱动固定为 `github.com/jackc/pgx/v5 v5.7.6`，通过其 `stdlib` 适配 `database/sql`。
这些版本是教程的复现基线，不代表最新安全版本；真实部署应评估升级与漏洞扫描。

## 第一步：启动隔离的学习数据库

下面的密码只用于本机临时学习环境，不用于真实服务。
端口绑定到回环地址，容器使用独立名称，避免误操作现有数据库。

```bash
docker run --name go-notes-pg \
  -e POSTGRES_USER=learner \
  -e POSTGRES_PASSWORD=local-only \
  -e POSTGRES_DB=go_notes \
  -p 127.0.0.1:55432:5432 \
  -d postgres:17.12
docker exec go-notes-pg pg_isready -U learner -d go_notes
```

如果尚未 ready，重复执行第二条命令，确认 ready 后再继续。
保存下面内容为本地 `schema.sql`：

```sql
CREATE TABLE IF NOT EXISTS products (
    id BIGINT PRIMARY KEY,
    stock INTEGER NOT NULL CHECK (stock >= 0)
);
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_key TEXT NOT NULL UNIQUE,
    product_id BIGINT NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);
INSERT INTO products(id, stock) VALUES (1, 10)
ON CONFLICT (id) DO NOTHING;
```

应用建表与初始化：

```bash
docker exec -i go-notes-pg psql -v ON_ERROR_STOP=1 -U learner -d go_notes < schema.sql
mkdir sql-orders
cd sql-orders
go mod init example.com/sql-orders
go get github.com/jackc/pgx/v5@v5.7.6
go get github.com/jackc/pgx/v5/stdlib@v5.7.6
export DATABASE_URL='postgres://learner:local-only@127.0.0.1:55432/go_notes?sslmode=disable'
```

`sslmode=disable` 仅用于这里的本地容器；跨主机访问需要按环境正确配置 TLS。
不要将含密码的真实连接串提交到 Git 或写进日志。

## 第二步：理解 sql.DB 与连接池

`sql.DB` 是可并发复用的连接池句柄，不是一条专用连接。
通常在启动时创建一次，执行 `PingContext` 检查可用性，退出时关闭。
`sql.Open` 本身可能尚未连接数据库，不能将返回成功当作数据库健康。

| 配置 | 含义 | 风险 |
|------|------|------|
| `SetMaxOpenConns` | 最大打开连接数 | 太大压垮数据库，太小导致排队 |
| `SetMaxIdleConns` | 保留空闲连接数 | 太低会频繁建连 |
| `SetConnMaxLifetime` | 连接最大复用时长 | 不会替代查询超时 |
| `SetConnMaxIdleTime` | 空闲连接最大时长 | 需结合数据库及网络配置 |

连接数应按服务副本总数和数据库预算规划，不能把示例值视为生产默认值。
使用 `db.Stats()` 观察 `InUse`、`WaitCount`、`WaitDuration`，才能判断池是否成为瓶颈。
事务会占用连接；事务中调用 `db.QueryContext` 可能另取连接，破坏原子性并造成池等待。

## 第三步：实现参数化事务

示例组 **sql-orders**：将下面完整程序保存为 `main.go`，与前面的模块对应。
程序接收可选请求键，首次创建成功，再次使用同一键会报告重复并回滚本次扣库存。

```go
package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
	_ "github.com/jackc/pgx/v5/stdlib"
)

var ErrOutOfStock = errors.New("库存不足或商品不存在")

func openDB(ctx context.Context) (*sql.DB, error) {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		return nil, errors.New("缺少 DATABASE_URL")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(5)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(30 * time.Minute)
	db.SetConnMaxIdleTime(5 * time.Minute)
	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("连接数据库：%w", err)
	}
	return db, nil
}

func createOrder(ctx context.Context, db *sql.DB, key string, quantity int) (int64, error) {
	if key == "" || quantity <= 0 {
		return 0, errors.New("请求键不能为空且数量必须大于零")
	}
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("开始事务：%w", err)
	}
	// Commit 成功后 Rollback 返回 ErrTxDone；此处忽略已结束事务的结果。
	defer tx.Rollback()
	result, err := tx.ExecContext(ctx,
		"UPDATE products SET stock = stock - $1 WHERE id = $2 AND stock >= $1", quantity, 1)
	if err != nil {
		return 0, fmt.Errorf("扣减库存：%w", err)
	}
	count, err := result.RowsAffected()
	if err != nil {
		return 0, err
	}
	if count != 1 {
		return 0, ErrOutOfStock
	}
	var id int64
	err = tx.QueryRowContext(ctx,
		"INSERT INTO orders(request_key, product_id, quantity) VALUES ($1, $2, $3) RETURNING id",
		key, 1, quantity).Scan(&id)
	if err != nil {
		return 0, fmt.Errorf("保存订单：%w", err)
	}
	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("提交事务：%w", err)
	}
	return id, nil
}

func run() error {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	db, err := openDB(ctx)
	if err != nil {
		return err
	}
	defer db.Close()
	key := "learning-order-001"
	if len(os.Args) > 1 {
		key = os.Args[1]
	}
	id, err := createOrder(ctx, db, key, 2)
	if err != nil {
		var pgErr *pgconn.PgError
		switch {
		case errors.Is(err, ErrOutOfStock):
			return fmt.Errorf("业务拒绝：%w", err)
		case errors.Is(err, context.DeadlineExceeded), ctx.Err() != nil:
			return fmt.Errorf("数据库操作超时或取消：%w", err)
		case errors.As(err, &pgErr) && pgErr.Code == "23505":
			return fmt.Errorf("请求键重复，请先查询已有订单：%w", err)
		default:
			return err
		}
	}
	fmt.Printf("订单 %d 已提交\n", id)
	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
```

先 `go mod tidy`，再运行 `go run .`。首次输出订单编号；再次执行应报告请求键重复。
查询数据库验证：首次库存由 10 变为 8，重复请求后仍为 8，而且只有一条订单。

```bash
docker exec go-notes-pg psql -U learner -d go_notes \
  -c 'SELECT * FROM products; SELECT * FROM orders;'
```

所有事务语句都通过 `tx` 执行，`$1` 等占位符将数据与 SQL 结构分开。
占位符不能替代表名、列名等 SQL 标识符；动态排序字段需要白名单，不能直接拼接任意请求内容。
条件 UPDATE 把“检查库存”和“扣库存”合成一个数据库操作，避免先读后写的竞争窗口。

这里的唯一请求键只是防止重复入库，并未实现完整幂等接口：重复请求应查询已有记录、比较请求内容，
再决定返回原结果还是冲突；不能把任意唯一约束错误都视为一次成功。
更完整的 HTTP 语义见 [[go-order-service-practice|订单服务综合练习]]。

## 查询、取消与提交结果的不确定性

单行查询的错误由 `Scan` 返回，查不到数据时可用 `errors.Is(err, sql.ErrNoRows)` 分类。
多行查询则需要 `defer rows.Close()`、逐行 `Scan`，循环后检查 `rows.Err()`，否则可能漏掉中途网络错误。
NULL 字段应选择指针或 `sql.NullString` 等类型，不能假设都能直接扫描到普通字符串。

传入 context 可以覆盖等待连接与查询执行，但驱动可能用自己的错误形式报告取消。
错误分类应结合 context 状态和驱动文档；业务层应保留原始错误链，而非只比较错误字符串。
事务开始后一直持有连接，不要在事务中等待用户交互或调用耗时的外部支付服务。

取消演练：在独立查询实验中对 `SELECT pg_sleep(5)` 使用 50ms 的 context，确认及时返回错误。
将 context 在调用前取消，则操作通常不会真正发起，可用于确定性测试取消传播。
真实请求取消后，必须由应用与数据库共同完成资源释放，不能仅依靠 HTTP 写入超时。

Commit 返回失败时，某些网络故障下无法仅凭客户端错误判断数据库是否已经提交。
对于付款、下单等操作，应通过业务唯一键查询确认结果，并设计幂等重试；不要立即无条件重复执行。
序列生成的订单 ID 可能在回滚后出现空洞，不能要求编号连续。

## 常见失败排查与练习

| 现象 | 可能原因 | 处理方式 |
|------|----------|----------|
| `connection refused` | 容器未就绪或端口错误 | 检查 pg_isready、映射端口与连接串 |
| 请求大量等待 | 连接未归还或事务太长 | 检查 rows.Close、事务生命周期及池统计 |
| 库存扣了但订单没写入 | 两条语句没有使用同一个事务 | 所有相关语句统一使用 tx |
| 错误后继续执行事务 | PostgreSQL 事务已中止 | 结束并回滚，重新建立必要的事务 |
| 重复请求多扣库存 | 幂等约束或回滚缺失 | 验证唯一键、事务边界与冲突处理 |

练习一：把数量改为 11，确认返回库存不足且两张表均没有额外变化。
练习二：连续用两个不同请求键创建订单，再用同一请求键重复调用，比较库存与记录数。
练习三：设置较小连接池并并发执行慢查询，观察等待计数；不要仅靠扩大连接池掩盖慢 SQL。
索引、锁与隔离级别原理复用 [[postgresql-advanced|PostgreSQL 进阶]]，测试方法见 [[go-testing-and-quality|质量保障]]。

## 清理与参考

以下命令只移除本文创建的临时学习容器，其数据也会随容器移除，不操作其他数据库：

```bash
docker rm -f go-notes-pg
```

- [database/sql 官方文档](https://pkg.go.dev/database/sql)：连接池、查询与事务 API。
- [Go 官方事务教程](https://go.dev/doc/database/execute-transactions)：事务操作及错误处理边界。
- [pgx v5.7.6 stdlib 文档](https://pkg.go.dev/github.com/jackc/pgx/v5@v5.7.6/stdlib)：驱动适配与用法。
- [PostgreSQL 17 事务说明](https://www.postgresql.org/docs/17/tutorial-transactions.html)：提交与回滚语义。
