---
title: Go 错误处理与资源管理
description: 通过错误链、类型分类、defer 和资源关闭示例，建立可维护的 Go 失败处理契约。
tags:
  - go
  - error-handling
  - resource-management
date: 2026-11-18
---

# Go 错误处理与资源管理

## 概述

失败是函数行为的一部分：输入不合法、订单不存在、数据库不可用，需要不同的处理方式。
Go 通过返回错误让调用者明确决定是否重试、终止或转换响应；通过 defer 让清理逻辑靠近资源获取位置。
本篇关注错误如何跨层传播，以及资源如何在成功和失败路径上得到释放。

## 前置知识与运行约定

先阅读 [[go-type-system-and-memory|类型系统与内存语义]]，尤其是接口与 nil。
示例要求 Go 1.24 或更高版本，无第三方依赖。
每个独立示例分别保存为新目录的 `main.go`，初始化后运行：

```bash
go mod init example.com/error-demo
go run .
go vet ./...
```

## 先定义错误契约，再决定如何记录

返回 `(Result, error)` 时，通常约定错误不为 nil 就不要使用结果，除非文档明确允许部分成功。
错误信息应补充操作上下文，例如“读取订单 A100”，但不应携带密码、令牌或完整敏感请求。
底层返回错误，上层在具有请求上下文的边界统一记录，避免每层都打印同一个失败。

| 表达方式 | 用途 | 调用方判断方式 |
|----------|------|----------------|
| 哨兵错误 | 稳定的失败类别，例如不存在 | `errors.Is` |
| 自定义错误类型 | 需要读取字段，例如哪个参数无效 | `errors.As` |
| 普通带上下文错误 | 提供诊断描述，无稳定分类需求 | 记录或向上返回 |
| 包装错误 | 添加上下文并保留原因 | `%w` 与错误链检查 |

不要根据 `err.Error()` 的文本判断业务分支；文字修改、包装和本地化都可能使判断失效。
对外暴露一个可检查的底层错误，也意味着调用者可能依赖它，应将其视为接口契约的一部分。

## 独立示例 A：错误分类、包装与检查

将以下完整程序保存为 `main.go`：

```go
package main

import (
	"errors"
	"fmt"
)

var ErrOrderNotFound = errors.New("订单不存在")

type ValidationError struct {
	Field string
	Value int
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("%s 必须大于零，实际为 %d", e.Field, e.Value)
}

func loadOrder(id string, quantity int) (string, error) {
	if quantity <= 0 {
		return "", &ValidationError{Field: "quantity", Value: quantity}
	}
	if id != "A100" {
		return "", fmt.Errorf("查询订单 %s：%w", id, ErrOrderNotFound)
	}
	return "已确认", nil
}

func main() {
	cases := []struct {
		id       string
		quantity int
	}{{"A100", 2}, {"missing", 1}, {"A100", 0}}

	for _, item := range cases {
		status, err := loadOrder(item.id, item.quantity)
		if err == nil {
			fmt.Println("成功：", status)
			continue
		}
		var invalid *ValidationError
		switch {
		case errors.Is(err, ErrOrderNotFound):
			fmt.Println("返回 404")
		case errors.As(err, &invalid):
			fmt.Println("返回 400：", invalid.Field)
		default:
			fmt.Println("内部失败：", err)
		}
	}
}
```

依次输出成功状态、`返回 404`、`返回 400： quantity`。
`errors.Is` 判断错误链是否包含目标或符合相应匹配规则，`errors.As` 找到兼容类型并填入目标变量。
`errors.As` 的第二个参数是非 nil 指针，因此这里传入 `&invalid`，不是 `invalid`。
这些映射只是示范应用边界，数据库层本身不应直接依赖 HTTP 状态码。

用 `%v` 拼接错误只保留描述，`%w` 则保留可检查的原因。
当底层实现细节不应成为公共契约时，可以在边界转换为自己的错误类别，而不是无条件透传。

## defer：调用参数立即求值，函数退出时执行

执行到 `defer f(x)` 时会先计算参数，真正的调用推迟到当前函数返回时。
多个 defer 按后进先出顺序执行。闭包可以在执行时读取外部变量，与直接传参的效果不同。

### 独立示例 B：观察求值与返回值

保存为新的 `main.go`：

```go
package main

import "fmt"

func settle() (total int) {
	total = 10
	defer fmt.Println("参数快照：", total)
	defer func() {
		fmt.Println("闭包读取：", total)
		total++
	}()
	total = 20
	return
}

func main() {
	fmt.Println("最终返回：", settle())
}
```

输出顺序为“闭包读取：20”“参数快照：10”“最终返回：21”。
命名返回值是函数内变量，defer 可以修改它；这一能力适合合并清理错误，但滥用会增加阅读负担。
`defer` 作用域是函数，不是循环体。在长循环里逐次打开文件再 defer 关闭，会积累到函数结束。
应将每轮处理提取到小函数，或在每次迭代结束时显式释放。

## 独立示例 C：写入失败与关闭失败都保留

文件写成功不代表关闭一定成功。某些错误可能在刷新或关闭时才出现，不能一概丢弃。
以下程序使用临时目录避免覆盖业务文件，将完整程序保存为 `main.go`：

```go
package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

func writeReceipt(path string, content string) (err error) {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("创建收据：%w", err)
	}
	defer func() {
		if closeErr := file.Close(); closeErr != nil {
			err = errors.Join(err, fmt.Errorf("关闭收据：%w", closeErr))
		}
	}()
	if _, err = file.WriteString(content); err != nil {
		return fmt.Errorf("写入收据：%w", err)
	}
	return nil
}

func run() error {
	dir, err := os.MkdirTemp("", "go-receipt-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(dir)
	path := filepath.Join(dir, "A100.txt")
	if err := writeReceipt(path, "订单 A100：已支付\n"); err != nil {
		return err
	}
	content, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	fmt.Print(string(content))

	err = writeReceipt(filepath.Join(dir, "missing", "receipt.txt"), "test")
	if err == nil {
		return errors.New("预期缺失目录导致创建失败")
	}
	fmt.Println("预期失败：", err)
	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
```

预期打印订单内容，随后报告不存在目录导致的创建失败；临时目录在 `run` 返回时清理。
`errors.Join` 可以保留多个非 nil 错误，便于继续用 `errors.Is/As` 检查。
这里忽略临时目录清理错误是示例的明确取舍；生产清理任务应根据业务要求记录或上报。

注意 `os.Exit` 不执行 defer，所以将资源处理放进 `run`，等它返回后才决定进程退出码。
文件 `Close` 成功也不等于数据已经可靠落到持久介质；需要抗崩溃持久化时还要考虑 `Sync`、
临时文件加重命名以及目录同步等平台语义。本例只演示错误保留，不提供原子持久化承诺。

## panic/recover：限制在明确的隔离边界

普通参数错误、订单不存在和网络超时应返回 error。
panic 更适合表达当前流程无法继续的异常状态，recover 只能在发生 panic 的同一 goroutine 中生效。
recover 需要在延迟函数中直接调用；父 goroutine 的 defer 无法捕获子 goroutine 的 panic。

### 独立示例 D：将不可信回调隔离为错误

保存为 `main.go`：

```go
package main

import (
	"fmt"
	"runtime/debug"
)

func invoke(task func()) (err error) {
	defer func() {
		if recovered := recover(); recovered != nil {
			err = fmt.Errorf("回调 panic：%v\n%s", recovered, debug.Stack())
		}
	}()
	task()
	return nil
}

func main() {
	err := invoke(func() {
		panic("模拟第三方回调失败")
	})
	if err != nil {
		fmt.Println("已隔离失败：", err)
	}
	fmt.Println("后续独立任务仍可处理")
}
```

预期输出包含 panic 原因和堆栈，最后继续执行独立任务。
这是可控练习，不意味着应在每层添加 recover：吞掉程序缺陷后继续使用已破坏的共享状态可能更危险。
堆栈用于内部诊断，不应原样返回外部客户端。

## 常见误区与练习

| 现象 | 根因 | 处理方式 |
|------|------|----------|
| 包装后 `err == target` 失败 | 顶层已变为另一错误值 | 使用 `errors.Is` |
| `errors.As` panic | 目标参数形态不正确 | 传入可接收目标错误类型的指针 |
| 函数返回非 nil error 却没有实际错误 | 把 nil 具体错误指针装入接口 | 成功路径直接返回 `nil` |
| 文件句柄持续增加 | 循环中 defer，函数迟迟不返回 | 缩短资源作用域 |
| 只看到最后的 Close 错误 | 清理错误覆盖原始失败 | 明确优先级或使用 `errors.Join` |

练习一：给示例 A 增加错误包装层，验证 `errors.Is/As` 仍正确。
练习二：将收据写入函数改为接收一个带 `Write` 和 `Close` 方法的小接口，
用测试替身分别模拟写入失败、关闭失败及二者同时失败，确认原始错误不会丢失。
练习三：解释为什么一个 HTTP 请求取消后不应被无条件重试，结合操作是否幂等判断。

## 与相关概念的关系

- [[go-standard-library-and-http|标准库与 HTTP 服务]]：在请求边界转换错误并释放响应体。
- [[go-database-sql|数据库访问]]：事务回滚与提交失败需要明确的错误契约。
- [[go-testing-and-quality|测试与质量保障]]：通过失败注入验证清理分支。

## 参考

- [Go 官方：错误包装与检查](https://go.dev/blog/go1.13-errors)
- [errors 标准库](https://pkg.go.dev/errors)
- [Go 语言规范：defer、panic 和 recover](https://go.dev/ref/spec)
- [Go 官方：defer、panic 与 recover](https://go.dev/blog/defer-panic-and-recover)
