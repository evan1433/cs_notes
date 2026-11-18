---
title: Go 订单服务综合实战
description: 使用标准库 HTTP、PostgreSQL 与 database/sql 实现可取消、可测试、具有事务和幂等语义的订单服务。
tags:
  - go
  - backend
  - idempotency
date: 2026-11-18
---

# Go 订单服务综合实战

## 你将得到什么

完成本教程后，你可以创建和查询订单，并验证重复提交只扣一次库存。
这个练习把 HTTP 输入边界、数据库事务、请求取消、测试和服务退出串起来。
它是本地教学服务：未实现登录、多租户、支付和订单状态机，不应直接暴露到公网。

成功创建的响应形如 `{"id":1,"sku":"book","quantity":2,"total_cents":5000}`；
相同幂等键与参数返回同一订单，不同参数复用该键返回 `409`。

## 环境与前置知识

- Go 1.24 或以上；本系列使用 Go 1.27.4 验证。
- Docker、本地可用的 `18080` 和 `55432` 端口、curl。
- [[go-standard-library-and-http|HTTP 服务]]、[[go-database-sql|数据库事务]]、[[go-testing-and-quality|测试]]。
- [[go-project-design-patterns|依赖注入]]与 [[go-concurrency-and-context|context]]。

所有 Go 文件属于同一个新目录 `order-practice`，依赖固定为 pgx v5.7.6。
各文件的完整内容如下，不需要其他章节的代码文件。

## 第一步：明确接口和一致性规则

| 接口 | 输入 | 成功 | 主要失败 |
|------|------|------|----------|
| `POST /orders` | JSON：`sku`、`quantity`；`Idempotency-Key` 请求头 | 首次 201，重复 200 | 400 非法输入，409 库存不足或键冲突 |
| `GET /orders/{id}` | 正整数订单 ID | 200 订单 | 400 ID 非法，404 不存在 |
| `GET /health` | 无 | 200 存活 | 只表示 HTTP 进程可服务 |
| `GET /ready` | 无 | 204 数据库可达 | 503 数据库不可达 |

数量限制为 `1..100`，金额使用整数分，避免浮点误差。
本地单用户练习的幂等键全局唯一；真实系统应按已认证的租户或用户划分作用域。
唯一约束负责处理并发重复请求，进程内的 map 无法在重启或多实例之间保证这一点。

订单写入与扣库存处于同一事务：先锁定商品，再尝试插入幂等记录、按条件扣库存，最后写金额并提交。
库存不足时回滚，因此失败请求不占用幂等键；成功提交后幂等记录保留。
参考 PostgreSQL 的 [ON CONFLICT 行为](https://www.postgresql.org/docs/17/sql-insert.html)。

```mermaid
flowchart TD
    A[校验请求] --> L[开始事务并锁定商品]
    L --> B[尝试插入订单]
    B --> C{幂等键已存在?}
    C -->|是| D[比较原订单参数]
    D -->|一致| E[返回原订单]
    D -->|不同| F[409 冲突]
    C -->|否| G[按库存条件扣减]
    G -->|不足| H[回滚并返回 409]
    G -->|成功| I[写入金额并提交]
```

## 第二步：准备数据库与模块

启动专用学习数据库。示例密码只用于本机，发布时通过部署平台注入密钥，并启用符合环境要求的 TLS。
如果前面数据库篇的 `go-notes-pg` 仍占用 `55432`，先用 `docker stop go-notes-pg` 停止它，保留其学习数据。

```bash
docker run -d --name go-order-pg \
  -e POSTGRES_USER=notes -e POSTGRES_PASSWORD=notes-local-only \
  -e POSTGRES_DB=notes -p 127.0.0.1:55432:5432 postgres:17.12
docker exec go-order-pg pg_isready -U notes -d notes
mkdir order-practice
cd order-practice
go mod init example.com/order-practice
go get github.com/jackc/pgx/v5@v5.7.6
```

等待 `pg_isready` 返回 accepting connections，再将以下内容保存为 `schema.sql`。
如果容器仍在初始化，重新执行就绪检查；不要立即运行建表命令。

```sql
CREATE TABLE IF NOT EXISTS practice_stock (
    sku text PRIMARY KEY,
    available integer NOT NULL CHECK (available >= 0),
    price_cents bigint NOT NULL CHECK (price_cents > 0)
);
CREATE TABLE IF NOT EXISTS practice_orders (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_key varchar(128) NOT NULL UNIQUE,
    sku text NOT NULL REFERENCES practice_stock(sku),
    quantity integer NOT NULL CHECK (quantity BETWEEN 1 AND 100),
    total_cents bigint NOT NULL CHECK (total_cents >= 0)
);
INSERT INTO practice_stock (sku, available, price_cents)
VALUES ('book', 10, 2500) ON CONFLICT (sku) DO NOTHING;
```

```bash
docker exec -i go-order-pg psql -v ON_ERROR_STOP=1 -U notes -d notes < schema.sql
export DATABASE_URL='postgres://notes:notes-local-only@127.0.0.1:55432/notes?sslmode=disable'
```

建表可以重复执行，但不会重置已有库存；后面的测试使用单独 SKU，避免依赖初始订单 ID。

## 第三步：实现事务存储

保存为 `store.go`。接口面向 HTTP 调用者，存储层负责一致性，HTTP 层不需要理解 SQL。
`sql.DB` 是可并发使用的连接池，使用方式参考 [database/sql](https://pkg.go.dev/database/sql)。

```go
package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
)

var (
	ErrConflict = errors.New("幂等键对应不同参数")
	ErrStock    = errors.New("商品不存在或库存不足")
)

type Order struct {
	ID         int64  `json:"id"`
	SKU        string `json:"sku"`
	Quantity   int    `json:"quantity"`
	TotalCents int64  `json:"total_cents"`
}

type Store interface {
	Create(context.Context, string, string, int) (Order, bool, error)
	Get(context.Context, int64) (Order, error)
}

type SQLStore struct{ DB *sql.DB }

func (s SQLStore) Create(ctx context.Context, key, sku string, qty int) (Order, bool, error) {
	if key == "" || len(key) > 128 || sku == "" || len(sku) > 64 || qty < 1 || qty > 100 {
		return Order{}, false, fmt.Errorf("无效订单参数")
	}
	tx, err := s.DB.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})
	if err != nil {
		return Order{}, false, err
	}
	// Commit 成功后 Rollback 返回 ErrTxDone；提前返回时确保回滚。
	defer tx.Rollback()

	// 先锁定库存记录，避免不存在的 SKU 触发外键错误，并串行化同商品的扣减。
	var price int64
	err = tx.QueryRowContext(ctx,
		`SELECT price_cents FROM practice_stock WHERE sku=$1 FOR UPDATE`, sku).Scan(&price)
	if errors.Is(err, sql.ErrNoRows) {
		return Order{}, false, ErrStock
	}
	if err != nil {
		return Order{}, false, err
	}
	order := Order{SKU: sku, Quantity: qty}
	err = tx.QueryRowContext(ctx, `
		INSERT INTO practice_orders (request_key, sku, quantity, total_cents)
		VALUES ($1,$2,$3,0) ON CONFLICT (request_key) DO NOTHING RETURNING id`,
		key, sku, qty).Scan(&order.ID)
	if errors.Is(err, sql.ErrNoRows) {
		err = tx.QueryRowContext(ctx, `
			SELECT id, sku, quantity, total_cents FROM practice_orders WHERE request_key=$1`,
			key).Scan(&order.ID, &order.SKU, &order.Quantity, &order.TotalCents)
		if err != nil {
			return Order{}, false, err
		}
		if order.SKU != sku || order.Quantity != qty {
			return Order{}, false, ErrConflict
		}
		return order, false, nil
	}
	if err != nil {
		return Order{}, false, err
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE practice_stock SET available=available-$1 WHERE sku=$2 AND available >= $1`, qty, sku)
	if err != nil {
		return Order{}, false, err
	}
	changed, err := result.RowsAffected()
	if err != nil {
		return Order{}, false, err
	}
	if changed != 1 {
		return Order{}, false, ErrStock
	}
	if price <= 0 || price > (1<<63-1)/int64(qty) {
		return Order{}, false, fmt.Errorf("商品价格超出可计算范围")
	}
	order.TotalCents = price * int64(qty)
	if _, err = tx.ExecContext(ctx,
		`UPDATE practice_orders SET total_cents=$1 WHERE id=$2`, order.TotalCents, order.ID); err != nil {
		return Order{}, false, err
	}
	if err = tx.Commit(); err != nil {
		return Order{}, false, err
	}
	return order, true, nil
}

func (s SQLStore) Get(ctx context.Context, id int64) (Order, error) {
	var order Order
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, sku, quantity, total_cents FROM practice_orders WHERE id=$1`, id).
		Scan(&order.ID, &order.SKU, &order.Quantity, &order.TotalCents)
	return order, err
}
```

这里对同一 SKU 加行锁，方便学习和验证库存一致性；热门商品会产生锁等待，吞吐需要另行评估。
每个事务只锁一个 SKU；多商品订单需要统一加锁顺序以降低死锁风险。
示例不删除库存记录，重复请求仍能找到商品。生产环境应明确商品归档与幂等记录保留策略。
计算金额前检查整数溢出；业务还应根据商品规则设置更严格的单价上限。

提交失败可能意味着连接中断，客户端未必知道数据库是否已经提交。
不要换一个幂等键盲目重试；用原键查询或重试，确认最终状态。

## 第四步：实现 HTTP 边界

保存为 `handler.go`。每次请求的数据库预算为 2 秒，JSON 限制为 4 KiB，只接受一个 JSON 值。
SKU 在此练习中限制为 ASCII 标识符，幂等键由调用者生成且只接受 ASCII 字母、数字、下划线和连字符。

```go
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"mime"
	"net/http"
	"regexp"
	"strconv"
	"time"
)

var identifier = regexp.MustCompile(`^[A-Za-z0-9_-]+$`)

func routes(store Store) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	mux.HandleFunc("POST /orders", func(w http.ResponseWriter, r *http.Request) {
		media, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
		if err != nil || media != "application/json" {
			http.Error(w, "需要 application/json", http.StatusUnsupportedMediaType)
			return
		}
		key := r.Header.Get("Idempotency-Key")
		var input struct {
			SKU      string `json:"sku"`
			Quantity int    `json:"quantity"`
		}
		r.Body = http.MaxBytesReader(w, r.Body, 4096)
		defer r.Body.Close()
		decoder := json.NewDecoder(r.Body)
		decoder.DisallowUnknownFields()
		if err = decoder.Decode(&input); err != nil {
			http.Error(w, "无效或过大的 JSON", http.StatusBadRequest)
			return
		}
		if err = decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
			http.Error(w, "只允许一个 JSON 值", http.StatusBadRequest)
			return
		}
		if len(key) > 128 || !identifier.MatchString(key) || len(input.SKU) > 64 ||
			!identifier.MatchString(input.SKU) || input.Quantity < 1 || input.Quantity > 100 {
			http.Error(w, "无效订单参数", http.StatusBadRequest)
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		order, created, err := store.Create(ctx, key, input.SKU, input.Quantity)
		if err != nil {
			writeStoreError(w, r, ctx, err)
			return
		}
		status := http.StatusOK
		if created {
			status = http.StatusCreated
		}
		writeJSON(w, status, order)
	})
	mux.HandleFunc("GET /orders/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
		if err != nil || id <= 0 {
			http.Error(w, "无效订单 ID", http.StatusBadRequest)
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		order, err := store.Get(ctx, id)
		if err != nil {
			writeStoreError(w, r, ctx, err)
			return
		}
		writeJSON(w, http.StatusOK, order)
	})
	return mux
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(value); err != nil {
		slog.Warn("write response", "error", err)
	}
}

func writeStoreError(w http.ResponseWriter, r *http.Request, ctx context.Context, err error) {
	switch {
	case r.Context().Err() != nil:
		// 请求已经取消，不再尝试向断开的客户端发送错误正文。
		slog.Info("request canceled", "error", r.Context().Err())
	case errors.Is(err, ErrConflict), errors.Is(err, ErrStock):
		http.Error(w, err.Error(), http.StatusConflict)
	case errors.Is(err, sql.ErrNoRows):
		http.Error(w, "订单不存在", http.StatusNotFound)
	case errors.Is(err, context.DeadlineExceeded), errors.Is(ctx.Err(), context.DeadlineExceeded):
		http.Error(w, "处理超时", http.StatusGatewayTimeout)
	default:
		slog.Error("store operation failed", "error", err)
		http.Error(w, "服务暂不可用", http.StatusServiceUnavailable)
	}
}
```

错误正文不会输出数据库连接串或底层 SQL 错误。
驱动在取消时可能返回数据库错误而非 `context.DeadlineExceeded`，因此示例同时检查操作上下文状态。
标准 JSON 解码器会接受重复字段并使用后面的值；本例不提供重复字段拒绝策略。
若接口签名或安全策略依赖唯一字段，应另行实现检测并补充测试。

## 第五步：管理进程与数据库生命周期

保存为 `main.go`。退出信号先停止接收请求并等待在途请求，超时才强制关闭连接，最后关闭数据库池。

```go
package main

import (
	"context"
	"database/sql"
	"errors"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

func run() error {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		return errors.New("必须设置 DATABASE_URL")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return err
	}
	defer db.Close()
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	err = db.PingContext(ctx)
	cancel()
	if err != nil {
		return err
	}
	mux := routes(SQLStore{DB: db})
	mux.HandleFunc("GET /ready", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), time.Second)
		defer cancel()
		if err := db.PingContext(ctx); err != nil {
			http.Error(w, "not ready", http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	server := &http.Server{
		Handler: mux, ReadHeaderTimeout: 3 * time.Second,
		ReadTimeout: 5 * time.Second, WriteTimeout: 5 * time.Second,
		IdleTimeout: 60 * time.Second,
	}
	listener, err := net.Listen("tcp", "127.0.0.1:18080")
	if err != nil {
		return err
	}
	stop, release := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer release()
	served := make(chan error, 1)
	go func() { served <- server.Serve(listener) }()
	slog.Info("listening", "address", listener.Addr().String())
	select {
	case err := <-served:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	case <-stop.Done():
		release()
	}
	shutdown, end := context.WithTimeout(context.Background(), 5*time.Second)
	defer end()
	if err := server.Shutdown(shutdown); err != nil {
		_ = server.Close()
		<-served
		return err
	}
	err = <-served
	if errors.Is(err, http.ErrServerClosed) {
		err = nil
	}
	return err
}

func main() {
	if err := run(); err != nil {
		slog.Error("service stopped", "error", err)
		os.Exit(1)
	}
}
```

`Shutdown` 的等待上下文独立于已取消的信号上下文。
它不会替你等待任意后台任务；本例只在 HTTP 请求内同步操作数据库。
如需增加异步任务，应另行定义接单停止、取消和等待策略。
超时后的 `Close` 是强制关闭连接，不保证所有 handler 已返回；真实服务若要求严格等待，应额外跟踪在途任务。

```bash
go mod tidy
go fmt ./...
go vet ./...
go build -o orders .
./orders
```

另开终端执行：

```bash
curl -i http://127.0.0.1:18080/ready
curl -i -X POST http://127.0.0.1:18080/orders \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: learning-001' \
  -d '{"sku":"book","quantity":2}'
```

第一次创建返回 `201`，记下响应中的 `id`，用 `GET /orders/实际ID` 查询。
原样重发返回 `200` 和同一 ID；将数量改成 `3` 但保留原键，应返回 `409`。
使用新键请求数量 `100`，应因库存不足返回 `409`，库存保持不变。

## 第六步：验证输入边界

保存为 `handler_test.go`。用可控替身验证非法输入不会进入存储层、错误映射正确。

```go
package main

import (
	"context"
	"database/sql"
	"net/http/httptest"
	"strings"
	"testing"
)

type fakeStore struct {
	calls int
	err   error
}

func (s *fakeStore) Create(ctx context.Context, key, sku string, qty int) (Order, bool, error) {
	s.calls++
	return Order{ID: 1, SKU: sku, Quantity: qty, TotalCents: 5000}, true, s.err
}

func (s *fakeStore) Get(ctx context.Context, id int64) (Order, error) {
	return Order{}, sql.ErrNoRows
}

func TestCreateBoundary(t *testing.T) {
	cases := []struct {
		name, body, key string
		err             error
		status, calls   int
	}{
		{"created", `{"sku":"book","quantity":2}`, "key-1", nil, 201, 1},
		{"unknown field", `{"sku":"book","quantity":2,"extra":1}`, "key-1", nil, 400, 0},
		{"two values", `{"sku":"book","quantity":2} {}`, "key-1", nil, 400, 0},
		{"zero", `{"sku":"book","quantity":0}`, "key-1", nil, 400, 0},
		{"missing key", `{"sku":"book","quantity":2}`, "", nil, 400, 0},
		{"too large", strings.Repeat(" ", 4097), "key-1", nil, 400, 0},
		{"conflict", `{"sku":"book","quantity":2}`, "key-1", ErrConflict, 409, 1},
		{"stock", `{"sku":"book","quantity":2}`, "key-1", ErrStock, 409, 1},
		{"timeout", `{"sku":"book","quantity":2}`, "key-1", context.DeadlineExceeded, 504, 1},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			store := &fakeStore{err: tc.err}
			req := httptest.NewRequest("POST", "/orders", strings.NewReader(tc.body))
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("Idempotency-Key", tc.key)
			response := httptest.NewRecorder()
			routes(store).ServeHTTP(response, req)
			if response.Code != tc.status || store.calls != tc.calls {
				t.Fatalf("status=%d calls=%d body=%s", response.Code, store.calls, response.Body)
			}
		})
	}
}
```

## 第七步：验证数据库一致性

保存为 `store_integration_test.go`。构建标签保证默认测试不要求数据库；显式执行集成测试却缺少配置时直接失败。
测试创建独立 SKU 和幂等键并清理，仅用于专用学习数据库。

```go
//go:build integration

package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"sync"
	"testing"
	"time"
)

func TestSQLConsistency(t *testing.T) {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		t.Fatal("DATABASE_URL is required for integration tests")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	sku := fmt.Sprintf("test-%d", time.Now().UnixNano())
	if _, err := db.ExecContext(ctx,
		`INSERT INTO practice_stock (sku, available, price_cents) VALUES ($1,10,2500)`, sku); err != nil {
		t.Fatal(err)
	}
	defer func() {
		cleanup, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		if _, err := db.ExecContext(cleanup, `DELETE FROM practice_orders WHERE sku=$1`, sku); err != nil {
			t.Error(err)
		}
		if _, err := db.ExecContext(cleanup, `DELETE FROM practice_stock WHERE sku=$1`, sku); err != nil {
			t.Error(err)
		}
	}()
	store := SQLStore{DB: db}
	var wait sync.WaitGroup
	ids := make(chan int64, 8)
	failures := make(chan error, 8)
	for worker := 0; worker < 8; worker++ {
		wait.Add(1)
		go func() {
			defer wait.Done()
			order, _, err := store.Create(ctx, sku+"-key", sku, 2)
			if err != nil {
				failures <- err
				return
			}
			ids <- order.ID
		}()
	}
	wait.Wait()
	close(ids)
	close(failures)
	for err := range failures {
		t.Error(err)
	}
	var first int64
	for id := range ids {
		if first != 0 && id != first {
			t.Errorf("different orders: %d and %d", first, id)
		}
		first = id
	}
	if first == 0 {
		t.Fatal("no successful order")
	}
	if _, _, err := store.Create(ctx, sku+"-key", sku, 3); !errors.Is(err, ErrConflict) {
		t.Fatalf("want conflict, got %v", err)
	}
	if _, _, err := store.Create(ctx, sku+"-large", sku, 100); !errors.Is(err, ErrStock) {
		t.Fatalf("want insufficient stock, got %v", err)
	}
	var available, count int
	if err := db.QueryRowContext(ctx, `SELECT available FROM practice_stock WHERE sku=$1`, sku).
		Scan(&available); err != nil {
		t.Fatal(err)
	}
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM practice_orders WHERE sku=$1`, sku).
		Scan(&count); err != nil {
		t.Fatal(err)
	}
	if available != 8 || count != 1 {
		t.Fatalf("available=%d orders=%d, want 8 and 1", available, count)
	}
	canceled, stop := context.WithCancel(ctx)
	stop()
	if _, _, err := store.Create(canceled, sku+"-cancel", sku, 1); err == nil {
		t.Fatal("canceled operation must fail")
	}
	// 持有库存行锁，让另一个操作真实进入数据库等待，再验证超时退出。
	lock, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer lock.Rollback()
	var locked int
	if err := lock.QueryRowContext(ctx,
		`SELECT available FROM practice_stock WHERE sku=$1 FOR UPDATE`, sku).Scan(&locked); err != nil {
		t.Fatal(err)
	}
	waiting, end := context.WithTimeout(ctx, 100*time.Millisecond)
	_, _, waitErr := store.Create(waiting, sku+"-wait", sku, 1)
	contextErr := waiting.Err()
	end()
	if err := lock.Rollback(); err != nil {
		t.Fatal(err)
	}
	if waitErr == nil || !errors.Is(contextErr, context.DeadlineExceeded) {
		t.Fatalf("want canceled lock wait, got %v / %v", waitErr, contextErr)
	}
	order, err := store.Get(ctx, first)
	if err != nil || order.TotalCents != 5000 {
		t.Fatalf("order=%+v error=%v", order, err)
	}
}
```

```bash
go test -race ./...
go test -race -tags=integration ./...
```

两条命令应通过。集成测试验证同键并发请求只生成一笔订单、只扣一次库存、参数冲突不写入和库存不足回滚。
取消测试既覆盖预取消，也覆盖等待真实数据库行锁期间的超时。

## 第八步：故障演练与交付

| 场景 | 操作 | 验收结果 |
|------|------|----------|
| 数据库不可达 | 停止 `go-order-pg`，请求 `/ready` | 有限时间内 503；`/health` 仍为 200 |
| 库存行被锁定 | 在 psql 事务中锁住 book 行，再创建订单 | 请求约 2 秒后返回 504，不永久等待 |
| 非法输入 | 发送负数量、未知字段、第二个 JSON | 400，不写数据库 |
| 重复提交 | 使用同一键并发发送相同请求 | 同一订单 ID，库存只扣一次 |
| 进程退出 | 对 `orders` 发送 SIGTERM | 停止接收请求，等待在途请求，退出后端口释放 |

锁等待演练可在数据库终端运行以下 SQL，保持事务不结束，再从另一终端创建订单；演练完成执行 `ROLLBACK`。

```sql
BEGIN;
SELECT * FROM practice_stock WHERE sku='book' FOR UPDATE;
-- 在另一个终端发出 HTTP 请求，观察超时后，再执行下面语句释放锁。
ROLLBACK;
```

服务部署方案见 [[go-service-delivery|服务交付]]，这里的监听地址固定为本地回环地址。
迁入容器时需将监听地址配置为 `:18080`，数据库地址改为容器网络中的服务名。
同时补齐认证、按用户授权查询、TLS、限流和幂等键保留周期，再讨论公网部署。

## 常见排错与清理

| 问题 | 原因与处理 |
|------|------------|
| 启动后立即退出 | 检查 DATABASE_URL、数据库就绪状态和端口占用；不要打印含密码的连接串 |
| 测试报表不存在 | 在同一 DATABASE_URL 指向的数据库中执行 schema.sql |
| 重复请求不是 201 | 首次已成功；相同键复用返回 200 是预期行为 |
| 库存比预期少 | 学习数据库保留了前次订单；查询实际库存，勿在服务运行时随意重置 |
| 集成测试失败 | 确认未指向真实业务库，检查权限、网络和测试超时 |

停止服务后，删除本教程专用容器；这会删除容器内的学习数据。

```bash
docker rm -f go-order-pg
```

## 自测与延伸

1. 为 GET 的非法 ID、404、Content-Type 错误和真实请求超时补充测试。
2. 为金额溢出保护补充测试，证明失败后不会留下订单或扣减库存。
3. 将本地单用户幂等约束扩展为“已认证用户＋幂等键”，测试用户之间互不影响。
4. 采集请求耗时和连接池等待指标，结合 [[go-runtime-and-diagnostics|诊断工具]]分析锁等待。

## 参考

- [Go HTTP 服务与 Shutdown](https://pkg.go.dev/net/http)
- [Go 数据库事务](https://go.dev/doc/database/execute-transactions)
- [pgx database/sql 适配器](https://pkg.go.dev/github.com/jackc/pgx/v5/stdlib)
- [PostgreSQL 行锁](https://www.postgresql.org/docs/17/explicit-locking.html)
- [[02-backend/go/index|返回 Go 学习路径]]
