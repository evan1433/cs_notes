---
title: Go 测试与质量保障
description: 通过表驱动测试、HTTP 测试、数据库集成测试、竞争检测、基准测试与模糊测试验证 Go 程序。
tags:
  - go
  - testing
  - security
date: 2026-11-18
---

# Go 测试与质量保障

## 概述

测试的目标是验证业务契约以及失败后的状态，而不是复制实现逻辑。
Go 将测试纳入工具链：同一包中的 `*_test.go` 文件可以由 `go test` 发现，测试失败会产生非零退出码。
本文以数量解析和 HTTP 接口为完整示例，再补充数据库、并发、性能与安全检查。
前置知识为 [[go-errors-and-resources|错误处理]]、[[go-standard-library-and-http|HTTP 服务]]。

所有示例使用 Go 1.24+。标准库示例独立成组；数据库测试需额外使用 [[go-database-sql|数据库访问]] 的环境和代码。

## 第一步：从业务契约建立测试用例

先明确规则：数量必须是十进制、能由当前平台的 `int` 表示且大于零；输入前后不允许多余空白。
错误的精确提示可以变化，但调用者应始终能够通过 `errors.Is` 识别非法数量。

示例组 **quantity-tests**，在一个空目录运行：

```bash
go mod init example.com/quantity-tests
```

文件 `quantity.go`：

```go
package quantity

import (
	"errors"
	"fmt"
	"strconv"
)

var ErrQuantity = errors.New("非法购买数量")

func ParseQuantity(input string) (int, error) {
	value, err := strconv.Atoi(input)
	if err != nil {
		return 0, fmt.Errorf("%w：%q 无法解析", ErrQuantity, input)
	}
	if value <= 0 {
		return 0, fmt.Errorf("%w：必须大于零", ErrQuantity)
	}
	return value, nil
}
```

文件 `quantity_test.go`：

```go
package quantity

import (
	"errors"
	"strconv"
	"testing"
)

func TestParseQuantity(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    int
		wantErr bool
	}{
		{"positive", "3", 3, false},
		{"zero", "0", 0, true},
		{"negative", "-2", 0, true},
		{"empty", "", 0, true},
		{"letters", "book", 0, true},
		{"whitespace", " 3", 0, true},
		{"overflow", "999999999999999999999999999999999", 0, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got, err := ParseQuantity(tt.input)
			if tt.wantErr {
				if !errors.Is(err, ErrQuantity) {
					t.Fatalf("错误 = %v，期望 ErrQuantity", err)
				}
				return
			}
			if err != nil || got != tt.want {
				t.Fatalf("结果 = %d, %v；期望 %d, nil", got, err, tt.want)
			}
		})
	}
}

func BenchmarkParseQuantity(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		value, err := ParseQuantity("123")
		if err != nil || value != 123 {
			b.Fatal("解析结果异常")
		}
	}
}

func FuzzParseQuantity(f *testing.F) {
	for _, seed := range []string{"1", "0", "-1", "abc", "001", "+2"} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, input string) {
		value, err := ParseQuantity(input)
		if err != nil {
			if !errors.Is(err, ErrQuantity) {
				t.Fatalf("错误丢失业务类别：%v", err)
			}
			return
		}
		if value <= 0 {
			t.Fatalf("成功结果必须为正数：%d", value)
		}
		// 对已接受的数据执行规范化与回读，检查稳定性。
		again, err := ParseQuantity(strconv.Itoa(value))
		if err != nil || again != value {
			t.Fatalf("规范化后不稳定：%d, %v", again, err)
		}
	})
}
```

执行以下命令，单元测试应全部通过；模糊测试会额外探索输入，耗时约 5 秒：

```bash
go test -v ./...
go test -race ./...
go test -run '^$' -bench . -benchmem -count=3
go test -run '^$' -fuzz '^FuzzParseQuantity$' -fuzztime=5s
```

表驱动测试把场景数据与断言分开；子测试名称用于定位失败，也可以用 `-run` 单独执行。
本例没有共享可变状态，可以并行运行。数据库 fixture、全局配置或环境变量相互影响时，不能机械添加 `t.Parallel()`。
更改环境变量可用 `t.Setenv`，但它不应与并行测试混用。

## 第二步：验证 HTTP 行为而不是手工调用处理器

示例组 **http-tests** 是独立目录，使用 `go mod init example.com/http-tests` 初始化。
文件 `handler.go`：

```go
package health

import (
	"encoding/json"
	"net/http"
)

func Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	return mux
}
```

文件 `handler_test.go`：

```go
package health

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestHealth(t *testing.T) {
	tests := []struct {
		name   string
		method string
		path   string
		status int
	}{
		{"healthy", http.MethodGet, "/health", http.StatusOK},
		{"method", http.MethodPost, "/health", http.StatusMethodNotAllowed},
		{"missing", http.MethodGet, "/missing", http.StatusNotFound},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			recorder := httptest.NewRecorder()
			Handler().ServeHTTP(recorder, httptest.NewRequest(tt.method, tt.path, nil))
			if recorder.Code != tt.status {
				t.Fatalf("状态 = %d，期望 %d", recorder.Code, tt.status)
			}
			if tt.status == http.StatusOK {
				var body map[string]string
				if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
					t.Fatal(err)
				}
				if body["status"] != "ok" {
					t.Fatalf("健康状态 = %q", body["status"])
				}
			}
		})
	}
}

func TestClientCancellation(t *testing.T) {
	started := make(chan struct{})
	stopped := make(chan struct{})
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		close(started)
		<-r.Context().Done()
		close(stopped)
	}))
	defer server.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, server.URL, nil)
	if err != nil {
		t.Fatal(err)
	}
	finished := make(chan error, 1)
	go func() {
		resp, err := server.Client().Do(req)
		if resp != nil {
			resp.Body.Close()
		}
		finished <- err
	}()
	select {
	case <-started:
	case <-ctx.Done():
		t.Fatal("处理器未启动")
	}
	cancel()
	select {
	case err := <-finished:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("客户端错误 = %v，期望取消", err)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("客户端未结束")
	}
	select {
	case <-stopped:
	case <-time.After(3 * time.Second):
		t.Fatal("处理器未观察到取消")
	}
}
```

运行 `go test -race -v ./...`，应验证正常状态、方法限制、未知路径和客户端取消传播。
Recorder 适合快速验证路由、状态码与响应；NewServer 创建真实本地监听器，适合验证客户端和连接行为。
测试用 channel 表达“处理器已开始”，超时只作失败上限，没有通过 Sleep 猜测时序。
这里的超时值不是性能指标，繁忙 CI 环境下仍需合理设置预算。

## 第三步：验证数据库事务的最终状态

以下示例组 **sql-integration** 不是独立业务程序：复制 [[go-database-sql|数据库访问]] 的 `main.go`、
对应 `go.mod` 和 `go.sum` 到一个测试目录，并使用该文建立的学习表结构。
在同目录新增 `database_test.go`：

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"testing"
	"time"
)

func TestDatabaseTransaction(t *testing.T) {
	if os.Getenv("DATABASE_URL") == "" {
		t.Skip("未设置 DATABASE_URL，跳过真实数据库测试")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	db, err := openDB(ctx)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	// createOrder 固定使用商品 1，因此只允许连接专用学习数据库串行执行。
	if _, err := db.ExecContext(ctx,
		"UPDATE products SET stock = 10 WHERE id = 1"); err != nil {
		t.Fatal(err)
	}
	key := fmt.Sprintf("test-%d", time.Now().UnixNano())
	t.Cleanup(func() {
		cleanupCtx, stop := context.WithTimeout(context.Background(), 2*time.Second)
		defer stop()
		if _, err := db.ExecContext(cleanupCtx, "DELETE FROM orders WHERE request_key = $1", key); err != nil {
			t.Errorf("清理订单：%v", err)
		}
		if _, err := db.ExecContext(cleanupCtx, "UPDATE products SET stock = 10 WHERE id = 1"); err != nil {
			t.Errorf("恢复库存：%v", err)
		}
	})
	if _, err := createOrder(ctx, db, key, 2); err != nil {
		t.Fatal(err)
	}
	if _, err := createOrder(ctx, db, key, 2); err == nil {
		t.Fatal("重复请求应失败")
	}
	var stock, count int
	if err := db.QueryRowContext(ctx, "SELECT stock FROM products WHERE id = 1").Scan(&stock); err != nil {
		t.Fatal(err)
	}
	if err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM orders WHERE request_key = $1", key).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if stock != 8 || count != 1 {
		t.Fatalf("事务状态异常：库存 %d，订单数 %d", stock, count)
	}
	cancelled, stop := context.WithCancel(ctx)
	stop()
	if err := db.PingContext(cancelled); !errors.Is(err, context.Canceled) {
		t.Fatalf("取消后的错误 = %v", err)
	}
}
```

执行 `DATABASE_URL='本地学习连接串' go test -count=1 -run TestDatabaseTransaction -v .`。
需确认输出为 PASS，而非因环境缺失而 SKIP；`-count=1` 避免缓存掩盖环境变化。
本例会改动学习商品库存，不得指向生产或共享数据库，也不要与其他库存实验并发运行。
测试同时检查库存和订单数，才能发现“重复插入失败但库存没有回滚”的缺陷。
真实项目应为测试创建独立数据库或 schema，并让数据访问层可注入商品 ID，以支持隔离的并行测试。

## 如何正确理解质量工具

| 工具 | 能提供的证据 | 不能保证的事情 |
|------|--------------|----------------|
| 单元测试 | 已列场景符合契约 | 未列出的业务场景全部正确 |
| 集成测试 | 真实驱动、SQL 与服务交互符合预期 | 生产网络与负载下始终正确 |
| `-race` | 执行路径上发现数据竞争 | 所有路径无竞争、无死锁 |
| Benchmark | 指定环境中的耗时与分配 | 跨机器结果可直接比较 |
| Fuzz | 自动探索输入、保存失败样本 | 测试属性完整覆盖需求 |
| 覆盖率 | 哪些语句被执行 | 断言有效或业务逻辑正确 |

Benchmark 应在相同机器、相同 Go 版本和相近负载下比较，多次运行后分析差异。
先确认测量内容，再考虑优化；不要把数据库网络波动误认为函数本身变慢。
模糊测试发现的最小失败输入应保留成回归样本，而非修复后删除。

## 静态检查、安全检查与 CI 顺序

建议先运行快速检查，再运行依赖外部环境的测试：

```bash
go vet ./...
go test ./...
go test -race ./...
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

竞争检测依赖受支持的平台、编译器和环境，CI 应提供对应运行器。
代码格式使用 `gofmt`；`go vet` 不会替代单元测试，也不覆盖所有代码风格问题。

漏洞检查使用官方 `golang.org/x/vuln/cmd/govulncheck`。
工具示例固定为 v1.10.0，其工具模块要求 Go 1.26.0+；业务示例的最低版本仍为 Go 1.24。
在装有 Go 1.26+ 的工具环境执行以下命令，并确保 Go bin 目录已加入 PATH：

```bash
go install golang.org/x/vuln/cmd/govulncheck@v1.10.0
govulncheck ./...
```

不要把工具自动升级混入业务测试；工具链版本要求见
[该版本 go.mod](https://github.com/golang/vuln/blob/v1.10.0/go.mod)。
扫描结果需要结合可达调用链评估并升级依赖，不应简单忽略告警。

## 常见失败与自测任务

- 测试偶尔失败：优先排查共享全局状态、时序假设、端口冲突和外部依赖，不要直接添加 Sleep。
- 子 goroutine 中测试失败：不要从任意 goroutine 调用 `t.Fatal`；将错误传回测试 goroutine 再结束测试。
- 测试通过但代码有问题：检查是否只断言“不返回错误”，遗漏返回值与持久化状态。
- 集成测试总是绿色：确认没有长期 SKIP，并在 CI 显式检查数据库连接与建表结果。

练习：给订单校验接口增加超大请求测试；给事务增加库存不足断言；
将 Fuzz 的性质补充为“空白输入永不成功”；最后故意移除事务回滚，确认测试能发现缺陷。
诊断测试发现的性能问题，继续阅读 [[go-runtime-and-diagnostics|运行时与性能诊断]]。

## 参考

- [testing 官方文档](https://pkg.go.dev/testing)：测试、子测试、Benchmark 与 Fuzz API。
- [httptest 官方文档](https://pkg.go.dev/net/http/httptest)：响应记录器与测试服务器。
- [Go 官方 Fuzz 教程](https://go.dev/doc/tutorial/fuzz)：失败样本与运行流程。
- [数据竞争检测说明](https://go.dev/doc/articles/race_detector)：运行方式及局限。
- [govulncheck 官方文档](https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck)：漏洞扫描工具安装与使用。
