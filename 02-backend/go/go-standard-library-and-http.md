---
title: Go 标准库与 HTTP 服务开发
description: 从流式 I/O 和严格 JSON 解码出发，构建具有超时、请求限制和优雅退出能力的 HTTP 服务。
tags:
  - go
  - backend
  - http
date: 2026-11-18
---

# Go 标准库与 HTTP 服务开发

## 你将得到什么

完成本文后，你可以用标准库实现一个订单校验接口，并解释请求体限制、超时和资源释放为什么必不可少。
本文侧重 HTTP 边界，不保存订单；持久化见 [[go-database-sql|Go 数据库访问]]。
学习前应掌握 [[go-errors-and-resources|错误与资源管理]]、[[go-concurrency-and-context|并发与 context]]。

环境为 Go 1.24 或更高版本，示例只依赖标准库。每个示例组使用单独目录，避免多个 `main` 函数冲突。

## 先理解标准库的接口协作

I/O 处理围绕 `io.Reader`、`io.Writer` 等小接口组织。
Reader 不承诺一次读满缓冲区；即使同时返回数据和错误，也应先处理已经读到的数据。
`io.Copy` 可以连接文件、网络响应和编码器，避免先将整个内容读进内存。

| 工具 | 适合的任务 | 应注意的边界 |
|------|------------|--------------|
| `io.Copy` | 流式转移数据 | 仍需检查复制错误及关闭错误 |
| `io.ReadAll` | 已知足够小的数据 | 输入必须有可信上限 |
| `bufio.Scanner` | 按行处理文本 | 默认 token 大小有限，应配置上限并检查 `Err` |
| `json.Decoder` | 从 Reader 解码 JSON | 一次 Decode 不保证输入只有一个 JSON 值 |
| `json.Encoder` | 向 Writer 编码 JSON | 写出部分响应后无法可靠更改状态码 |

下面是独立示例组 **stream-copy**，文件为 `main.go`。
这里使用内存 Reader 便于复现，替换为文件或响应体时还要管理它们的关闭。

```go
package main

import (
	"fmt"
	"io"
	"os"
	"strings"
)

func main() {
	reader := strings.NewReader("订单 A100\n订单 A101\n")
	written, err := io.Copy(os.Stdout, reader)
	if err != nil {
		fmt.Fprintln(os.Stderr, "输出失败：", err)
		os.Exit(1)
	}
	fmt.Printf("共输出 %d 字节\n", written)
}
```

保存后运行 `go run main.go`，会输出两行订单和字节计数。
流式复制降低峰值内存，并不代表输入可信；网络输入仍然需要大小限制和截止时间。

## 第一步：构建严格校验的 HTTP 服务

在独立目录初始化模块：

```bash
mkdir http-orders
cd http-orders
go mod init example.com/http-orders
```

示例组 **http-orders** 只有下面一个 `main.go`。
服务监听本机 `127.0.0.1:8080`，提供健康检查与订单校验接口。

```go
package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type createOrder struct {
	Product  string `json:"product"`
	Quantity *int   `json:"quantity"`
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	// 先序列化，使编码错误发生在写出状态码之前。
	data, err := json.Marshal(value)
	if err != nil {
		http.Error(w, "响应编码失败", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if _, err := w.Write(append(data, '\n')); err != nil {
		slog.Warn("写响应失败", "error", err)
	}
}

func orders(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()
	// 限制应用读取的请求体，避免不受限的内存或解析成本。
	r.Body = http.MaxBytesReader(w, r.Body, 4096)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var input createOrder
	if err := decoder.Decode(&input); err != nil {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			http.Error(w, "请求体超过 4096 字节", http.StatusRequestEntityTooLarge)
			return
		}
		http.Error(w, "JSON 格式或字段不合法", http.StatusBadRequest)
		return
	}
	// 拒绝两个拼接的 JSON 值，也会消耗尾部空白以验证整体大小。
	if err := decoder.Decode(new(any)); err != io.EOF {
		var tooLarge *http.MaxBytesError
		if errors.As(err, &tooLarge) {
			http.Error(w, "请求体超过 4096 字节", http.StatusRequestEntityTooLarge)
			return
		}
		http.Error(w, "请求必须只有一个 JSON 值", http.StatusBadRequest)
		return
	}
	if input.Product == "" || input.Quantity == nil || *input.Quantity <= 0 {
		http.Error(w, "product 必填且 quantity 必须为正数", http.StatusBadRequest)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"product": input.Product, "quantity": *input.Quantity, "validated": true,
	})
}

func requestLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		next.ServeHTTP(w, r)
		slog.Info("请求结束", "method", r.Method, "path", r.URL.Path,
			"duration", time.Since(started))
	})
}

func run() error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /orders", orders)
	server := &http.Server{
		Addr: "127.0.0.1:8080", Handler: requestLog(mux),
		ReadHeaderTimeout: 2 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       60 * time.Second,
		MaxHeaderBytes:    16 << 10,
	}
	serveErr := make(chan error, 1)
	go func() { serveErr <- server.ListenAndServe() }()
	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}
	// 原信号 context 已取消，退出过程需要新的、有上限的 context。
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		_ = server.Close()
		return err
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

func main() {
	if err := run(); err != nil {
		slog.Error("服务退出", "error", err)
		os.Exit(1)
	}
}
```

`Quantity` 使用指针，能够区分正整数与“缺失/null”；这里把缺失和 null 都视为非法。
严格解码会拒绝未知字段，但不自动拒绝 JSON 的重复键；如业务要求禁止重复键，需要额外解析策略。
示例也没有把 `Content-Type` 当作解析保证，若 API 契约要求媒体类型，应使用 `mime.ParseMediaType` 校验。

本例的服务端请求体由标准库负责最终关闭，处理器仍显式安排关闭以表达资源边界。
日志没有记录完整请求体、认证凭证或查询参数，避免业务数据进入普通访问日志。

## 第二步：验证正常与失败路径

第一个终端运行 `go run .`，第二个终端执行：

```bash
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/orders \
  -H 'Content-Type: application/json' -d '{"product":"book","quantity":2}'
curl -i http://127.0.0.1:8080/orders \
  -H 'Content-Type: application/json' -d '{"product":"book","quantity":0}'
curl -i http://127.0.0.1:8080/orders \
  -H 'Content-Type: application/json' -d '{"product":"book","quantity":2,"extra":1}'
curl -i http://127.0.0.1:8080/orders -d '{}{}'
```

预期健康检查与合法请求返回 `200`，其余返回 `400`。
发送大于 4096 字节的请求应返回 `413`；使用不支持的方法应由路由返回 `405`。
在服务终端按 Ctrl+C，会停止接受新连接，并在退出时限内等待活动请求。
不要用 `kill -9` 验证优雅退出，因为进程没有机会接收并处理退出流程。

## 第三步：复用客户端并限制响应体

HTTP Client 和 Transport 应复用，避免每次请求重新建立连接。
下面是独立示例组 **http-client**，保存为另一个目录的 `main.go`；先启动上一组服务。

```go
package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

var client = &http.Client{Timeout: 3 * time.Second}

func fetchHealth(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		"http://127.0.0.1:8080/health", nil)
	if err != nil {
		return err
	}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("请求健康检查：%w", err)
	}
	defer resp.Body.Close()
	const limit = 4096
	body, err := io.ReadAll(io.LimitReader(resp.Body, limit+1))
	if err != nil {
		return err
	}
	if len(body) > limit {
		return fmt.Errorf("响应超过 %d 字节", limit)
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("上游返回状态 %d", resp.StatusCode)
	}
	fmt.Print(string(body))
	return nil
}

func main() {
	defer client.CloseIdleConnections()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := fetchHealth(ctx); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
```

运行 `go run main.go`，应输出健康检查 JSON；服务未启动时应报告连接失败并非零退出。
非 2xx 状态不会自动使 `client.Do` 返回错误，必须由调用方检查。
小响应读到 EOF 后关闭有助于连接复用；超大响应应及时关闭，不应为了复用连接无上限地排空响应体。

## 超时的分工与边界

| 机制 | 控制范围 | 不能替代的能力 |
|------|----------|----------------|
| `ReadHeaderTimeout` | 读取请求头 | 不能限制整个业务执行时间 |
| `ReadTimeout` | 包含请求体读取的读取期限 | 不会强制终止业务 goroutine |
| `WriteTimeout` | 响应写入期限 | 不等同于自动取消所有下游操作 |
| `Client.Timeout` | 单次客户端请求整体过程 | 不能替代服务的总预算设计 |
| 请求 context | 向下游传播取消与截止时间 | 任务必须主动观察并响应取消 |

下游数据库、HTTP 请求应接收同一请求链路的 context，并根据预算设置更短截止时间。
超时不代表远端一定未执行成功，写操作重试必须结合幂等机制。
流式响应通常需要不同的超时策略，不能直接照搬这里短请求的配置。

## 常见失败排查与练习

| 问题 | 常见原因 | 排查方向 |
|------|----------|----------|
| 连接无法复用 | 响应体未读完或未关闭 | 检查所有成功和失败返回路径 |
| 接口内存持续增长 | 无界读取请求或响应 | 同时限制字节数、并发数和持续时间 |
| JSON 后带垃圾仍成功 | 只调用一次 Decode | 二次解码确认 EOF |
| 退出卡住 | 活动请求不结束、连接被劫持 | 设置退出预算；单独管理 WebSocket 等连接 |
| 错误响应仍为 200 | 写正文后才设置状态码 | 首次 Write 前设置状态 |

练习：用 `httptest` 为未知字段、两个 JSON 值、缺失数量、超大请求分别写测试。
再让业务处理等待 `r.Context().Done()`，验证客户端取消能够结束等待。
优雅退出只处理 HTTP 层，后台队列、定时器和数据库连接仍要按生命周期顺序停止。

## 延伸与参考

- [[go-testing-and-quality|测试与质量保障]]：把手工 curl 检查转成自动化测试。
- [[go-service-delivery|服务交付]]：补充配置、探针和部署退出流程。
- [net/http 官方文档](https://pkg.go.dev/net/http)：Server、Client 与 Shutdown 的准确契约。
- [encoding/json 官方文档](https://pkg.go.dev/encoding/json)：解码与字段处理规则。
- [io 官方文档](https://pkg.go.dev/io)：流式复制和受限 Reader。
