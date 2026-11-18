---
title: Go 工程组织与常用设计模式
description: 通过可运行订单示例理解 Go 的包边界、小接口、依赖注入、装饰器与 Functional Options。
tags:
  - go
  - backend
  - design-patterns
date: 2026-11-18
---

# Go 工程组织与常用设计模式

## 概述

服务变大后，困难常来自业务规则、数据库和网络调用缠在一起，导致修改难以测试。
Go 可以用包、组合和小接口建立清晰边界，再根据实际变化引入设计模式。
本篇重点是让依赖方向清楚、失败可见、测试可以替换外部系统，而非追求固定目录数量。

## 前置知识与环境

- [[go-type-system-and-memory|类型系统与内存语义]]：理解方法集和接口。
- [[go-errors-and-resources|错误处理与资源管理]]：理解错误传播。
- [[go-concurrency-and-context|并发与生命周期管理]]：理解取消与等待。
- Go 1.24 或更新版本；本文程序仅依赖标准库。

## 包、Module 与依赖方向

Module 管理模块路径和依赖版本，package 管理源码与可见性。
包名应表达提供的能力，例如 `orders`，而不是把不相关函数都放入 `utils`。
同一个包的非测试源码通常放在同一目录；包之间不能循环导入。

一个小服务可以从单包开始。出现可复用领域规则或独立适配器后，再按职责拆分：

```text
order-service/
├── go.mod
├── cmd/orders/main.go
└── internal/
    ├── orders/service.go
    ├── postgres/repository.go
    └── httpapi/handler.go
```

以上是目录示意，不是要求创建空文件的脚手架。
`cmd/orders` 负责组装依赖；`orders` 表达业务规则；数据库和 HTTP 适配器负责协议转换。
`internal` 利用工具链限制导入范围，其规则与目录祖先有关，并不只是命名约定。
包组织的更多变体见 [官方模块布局说明](https://go.dev/doc/modules/layout)。

合理的依赖关系是 HTTP 层调用业务，业务通过自己需要的接口访问存储，存储实现不反向控制业务。
对于小型 CRUD 服务，也不必为每张表复制 controller/service/repository 三层空壳。
拆分的依据应是变化、职责和测试边界。

## 可运行示例：小接口、注入与装饰器

在新目录初始化模块：

```bash
mkdir go-design-lab
cd go-design-lab
go mod init example.com/go-design-lab
```

保存以下完整程序为 `main.go`：

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"
)

var ErrNotFound = errors.New("order not found")

type Order struct {
	ID    string
	Total int
}

// 由调用方定义所需能力，避免让业务依赖完整数据库客户端。
type OrderReader interface {
	Find(context.Context, string) (Order, error)
}

type Service struct {
	reader OrderReader
	logger *slog.Logger
}

type Option func(*Service) error

func WithLogger(logger *slog.Logger) Option {
	return func(service *Service) error {
		if logger == nil {
			return errors.New("logger must not be nil")
		}
		service.logger = logger
		return nil
	}
}

func NewService(reader OrderReader, options ...Option) (*Service, error) {
	if reader == nil {
		return nil, errors.New("reader must not be nil")
	}
	service := &Service{
		reader: reader,
		logger: slog.New(slog.NewTextHandler(io.Discard, nil)),
	}
	for _, option := range options {
		if option == nil {
			return nil, errors.New("option must not be nil")
		}
		if err := option(service); err != nil {
			return nil, err
		}
	}
	return service, nil
}

func (s *Service) Get(ctx context.Context, id string) (Order, error) {
	if strings.TrimSpace(id) == "" {
		return Order{}, errors.New("order ID must not be empty")
	}
	order, err := s.reader.Find(ctx, id)
	if err != nil {
		return Order{}, fmt.Errorf("get order %q: %w", id, err)
	}
	s.logger.InfoContext(ctx, "order loaded", "order_id", order.ID)
	return order, nil
}

type MemoryReader struct {
	orders map[string]Order
}

func (m MemoryReader) Find(ctx context.Context, id string) (Order, error) {
	if err := ctx.Err(); err != nil {
		return Order{}, err
	}
	order, ok := m.orders[id]
	if !ok {
		return Order{}, ErrNotFound
	}
	return order, nil
}

// 装饰器遵循原接口，在不改变存储实现的情况下增加行为。
type AuditReader struct {
	Next   OrderReader
	Logger *slog.Logger
}

func (a AuditReader) Find(ctx context.Context, id string) (Order, error) {
	order, err := a.Next.Find(ctx, id)
	a.Logger.InfoContext(ctx, "storage lookup", "order_id", id, "found", err == nil)
	return order, err
}

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	reader := AuditReader{
		Next: MemoryReader{orders: map[string]Order{
			"A100": {ID: "A100", Total: 50},
		}},
		Logger: logger,
	}
	service, err := NewService(reader, WithLogger(logger))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, id := range []string{"A100", "missing", ""} {
		order, err := service.Get(context.Background(), id)
		switch {
		case errors.Is(err, ErrNotFound):
			fmt.Println("订单不存在")
		case err != nil:
			fmt.Println("请求失败：", err)
		default:
			fmt.Println(order.ID, order.Total)
		}
	}
}
```

执行：

```bash
go fmt ./...
go vet ./...
go run .
```

除带时间的日志外，预期出现 `A100 50`、`订单不存在` 和空订单号的校验错误。
`MemoryReader` 只读初始化后的 map；若以后增加并发写入，需要补充同步机制。
`AuditReader` 在组装时要求有效的 `Next` 和 `Logger`；将其变成公共 API 时应增加构造函数校验。

### 为什么让调用方定义接口

业务仅需要 `Find`，因此接口只暴露一个方法。
测试可以实现同样的方法返回指定错误，不需要启动数据库。
接口不是“每个结构体必配一个”的装饰；只有需要隔离变化或替换依赖时才有价值。
例如只有一个纯计算函数时，直接调用通常比预先抽象更清楚。

构造函数中的 `reader == nil` 只能检查 nil 接口。
它无法拒绝接口内部的 nil 指针，因此实现者必须提供有效实例；不要让带 nil 指针的实现穿过组装边界。
相关语义见 [[go-type-system-and-memory|接口与 nil]]。

### Functional Options 的适用条件

必需依赖使用显式参数，可选配置使用选项，并在构造阶段校验。
示例中省略日志选项有安全默认行为，显式传入 nil 则返回错误。
如果只有一个可选超时字段，普通配置结构体可能更加直观。
选项执行有顺序，同一个选项重复设置时本例后者覆盖前者；涉及相互冲突的配置时应集中校验。

### 装饰器与中间件

装饰器包装同一接口，适合计时、审计、缓存等横切行为。
HTTP 中间件也遵循这个思想：接收 `http.Handler`，返回另一个 `http.Handler`。
包装顺序影响结果，例如鉴权应在业务执行之前，日志需要覆盖失败路径。
缓存装饰器还必须定义失效、并发安全和错误处理，不能只增加一个 map 就称为完整缓存。

## 并发模式的选择

| 模式 | 解决的问题 | 必须明确的退出条件 |
|------|------------|--------------------|
| Worker Pool | 限制同时执行的任务数 | 谁关闭输入，谁等待 worker，取消后是否停止取任务 |
| Pipeline | 将处理拆成多阶段 | 下游退出时，上游不能永久阻塞发送 |
| Fan-out/Fan-in | 多任务分发与结果汇总 | 发送者全部退出后由协调者关闭结果 channel |
| 装饰器 | 在调用边界增加公共行为 | 是否保持原错误、取消语义与并发安全 |

可运行并发示例见 [[go-concurrency-and-context|并发与生命周期管理]]。
需要特别区分 goroutine 数量限制与队列长度限制：有限 worker 仍可能配上无限增长的待处理队列。
请求到达速度长期超过处理能力时，需要拒绝、阻塞上游或持久化排队，并给调用方明确反馈。

## 依赖管理与代码审查

添加依赖前检查许可证、维护状态、传递依赖和实际需要的 API。
模块版本与源码版本应可追踪，提交 `go.mod` 和生成的 `go.sum`。
`go mod tidy` 会整理依赖，执行后检查差异，不应把它当作无影响的格式化命令。

```bash
go list -m all
go mod graph
go mod tidy
go test ./...
```

本例仅用标准库，不会生成第三方依赖校验项。
多模块协作时可使用 workspace，但不能依赖开发机上的 `go.work` 掩盖模块本身无法独立构建的问题。
模块版本选择和发布规则见 [Go Modules Reference](https://go.dev/ref/mod)。

审查时重点追问：外部依赖是否显式传入？错误是否保留原因？包是否通过全局变量互相影响？
接口是否被迫包含调用方根本不需要的方法？测试是否必须启动整套基础设施才能验证简单规则？

## 常见误区与练习

| 误区 | 实际问题 | 改进方式 |
|------|----------|----------|
| 所有对象都实现巨大接口 | 变更牵动大量实现，测试替身复杂 | 按调用方需求缩小接口 |
| 用全局数据库实例简化传参 | 生命周期与测试互相干扰 | 在 main 组装，再通过构造函数传入 |
| 业务层直接读环境变量 | 配置来源与业务规则耦合 | 启动阶段读取并校验配置 |
| 层数越多越规范 | 转发代码掩盖真正逻辑 | 以职责和变化为拆分依据 |
| 所有错误都在每层记录日志 | 同一错误重复打印多次 | 通常在有上下文的处理边界记录 |

练习：为 `Service` 编写一个始终返回 `context.DeadlineExceeded` 的 reader，验证错误链仍可识别。
再编写一个记录调用次数的装饰器，并用测试确认非法 ID 不会调用存储。
最后将程序拆成前述目录，确认 `orders` 包不导入数据库或 HTTP 适配器。

## 参考与后续

- [Go 官方模块布局](https://go.dev/doc/modules/layout)
- [Go Modules Reference](https://go.dev/ref/mod)
- [Effective Go：接口与组合](https://go.dev/doc/effective_go)
- [[go-testing-and-quality|测试与质量保障]]：验证依赖边界。
- [[go-order-service-practice|订单服务综合练习]]：把模式放入实际业务。
