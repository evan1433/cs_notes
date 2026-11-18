---
title: Go 语言入门：从基础语法到并发编程
description: 通过可运行示例理解 Go 的类型、集合、接口、错误处理、并发与工程工具链。
tags:
  - go
  - backend
  - concurrency
date: 2026-11-18
aliases:
  - Go 语言入门
  - Golang 基础
---

# Go 语言入门：从基础语法到并发编程

## 概述

Go 是一种静态类型、编译型语言，提供垃圾回收、内置并发机制和统一工具链。
它用较少的语言机制组织程序，适合编写网络服务、命令行工具和基础设施软件。
学习 Go 的关键，是理解它如何用组合、显式错误返回和并发通信表达业务逻辑。

本文面向了解变量、函数和循环的读者；所有 Go 示例均为独立程序，可分别保存为 `main.go` 运行。
关于语言设计与编码习惯，可参阅 [Effective Go](https://go.dev/doc/effective_go)。
该文档较早，Modules 和泛型等内容应结合现代官方教程学习。

## 准备环境与第一个程序

按照 [官方安装指南](https://go.dev/doc/install) 安装 Go，并在终端确认：

```bash
go version
mkdir go-learning
cd go-learning
go mod init example.com/go-learning
```

Module 是依赖与版本管理的单位，`go.mod` 记录模块路径及 Go 版本等信息；
package 是源代码组织的单位，一个 module 可以包含多个 package。
示例中的 `example.com/go-learning` 用于本地学习，不要求注册这个域名。
这与 [官方入门教程](https://go.dev/doc/tutorial/getting-started) 使用的初始化方式一致。

创建 `main.go`：

```go
package main

import "fmt"

func main() {
	fmt.Println("你好，Go！")
}
```

执行以下命令，输出为 `你好，Go！`：

```bash
go run .
```

`package main` 表示可执行程序所在的包，`main` 函数是入口。
`fmt` 来自标准库，负责格式化输入输出。
Go 通常不需要手写语句末尾的分号，但左花括号应与函数声明放在同一行。

## 基础语法：显式类型与简洁表达

变量既可以显式声明类型，也可以让编译器推导类型。
`:=` 只能用于函数内部的短变量声明，同一作用域中至少要引入一个新变量。
没有显式初始化的变量具有零值：数值为 `0`、布尔值为 `false`、字符串为 `""`。

```go
package main

import "fmt"

func main() {
	const price = 25
	quantity := 3
	var paid bool
	total := price * quantity

	if total >= 50 {
		fmt.Println("满足优惠条件")
	}
	for item := 1; item <= quantity; item++ {
		fmt.Printf("商品 %d\n", item)
	}
	fmt.Printf("总价：%d，已支付：%t\n", total, paid)
}
```

Go 使用 `for` 表达传统循环、条件循环和无限循环，没有单独的 `while` 关键字。
不同数值类型之间一般需要显式转换，例如把 `int` 转成 `float64`。
包级名称以大写字母开头时可被其他包访问，例如 `fmt.Println`。

## 集合：数组、切片与 map

| 类型 | 特点 | 常见用途 |
|------|------|----------|
| 数组，如 `[3]int` | 长度属于类型，赋值会复制数组值 | 固定长度数据 |
| 切片，如 `[]int` | 描述底层数组的一段视图，具有长度和容量 | 可变长度序列 |
| map，如 `map[string]int` | 键值映射，遍历顺序不保证 | 计数、索引与查找 |

切片赋值不会复制元素：两个切片可能共享底层数组。
`append` 可能分配新的底层数组，因此需要接收它的返回值。
map 查找可以同时返回值和是否存在，避免把“不存在”误认为“值为零”。

```go
package main

import "fmt"

func main() {
	scores := []int{80, 90}
	scores = append(scores, 95)

	// 复制元素，避免修改副本时意外影响原切片。
	backup := make([]int, len(scores))
	copy(backup, scores)
	backup[0] = 100
	fmt.Println(scores, backup)

	stock := map[string]int{"笔记本": 12}
	if count, ok := stock["键盘"]; ok {
		fmt.Println("库存：", count)
	} else {
		fmt.Println("商品尚未录入")
	}
}
```

`nil` 切片可以直接 `append`；`nil` map 可以读取，但写入会 panic，写入前应使用 `make` 或字面量初始化。
这些集合可以结合 [[数据结构|数据结构]] 中的数组与哈希表知识理解。

## 结构体、方法与接口

Go 用结构体描述数据，用方法表达行为，通过组合复用功能。
接口定义行为契约：类型只要拥有接口要求的方法，就隐式实现接口，不需要写 `implements`。

```go
package main

import "fmt"

type Notifier interface {
	Notify(message string) string
}

type EmailNotifier struct {
	Address string
}

func (n EmailNotifier) Notify(message string) string {
	return fmt.Sprintf("发送到 %s：%s", n.Address, message)
}

func announce(n Notifier) {
	fmt.Println(n.Notify("订单已发货"))
}

func main() {
	announce(EmailNotifier{Address: "reader@example.com"})
}
```

此示例只格式化通知文本，不会发送真实邮件。
`EmailNotifier` 无需声明与 `Notifier` 的关系，也能作为参数传入。
实际设计中，让接口只包含调用方所需的方法，可以减少组件之间的耦合。

值接收者如 `(n EmailNotifier)` 接收一个副本；需要修改结构体本身时，通常使用指针接收者。
如果方法只定义在 `*EmailNotifier` 上，则 `EmailNotifier` 值本身未必满足该接口，传参时需要注意方法集。
Go 支持泛型，可用类型参数复用算法；入门时先掌握具体类型和接口，更容易理解两者的使用边界。

## 错误处理：让失败成为函数契约

Go 通常用返回值 `error` 表达可预期失败。
调用者应先检查错误，再使用结果，避免把无效数据继续传递。
下面用购买数量解析展示错误包装和业务校验：

```go
package main

import (
	"fmt"
	"strconv"
)

func parseQuantity(input string) (int, error) {
	quantity, err := strconv.Atoi(input)
	if err != nil {
		// 保留原始错误，便于上层通过 errors.Is / errors.As 继续检查。
		return 0, fmt.Errorf("解析购买数量 %q 失败：%w", input, err)
	}
	if quantity <= 0 {
		return 0, fmt.Errorf("购买数量必须大于 0，实际为 %d", quantity)
	}
	return quantity, nil
}

func main() {
	for _, input := range []string{"3", "abc", "0"} {
		quantity, err := parseQuantity(input)
		if err != nil {
			fmt.Println("下单失败：", err)
			continue
		}
		fmt.Println("购买数量：", quantity)
	}
}
```

该程序依次演示成功、格式错误和业务校验失败。
`%w` 用于包装错误，相关机制见 [官方错误处理说明](https://go.dev/blog/go1.13-errors)。
`panic` 不适合作为普通参数错误的处理方式，应优先返回 `error`。

`defer` 可以安排函数返回前执行清理，例如打开文件成功后立即声明 `defer file.Close()`。
多个延迟调用按后进先出顺序执行；资源应在获取成功后才安排释放。
对写文件等场景，关闭时也可能出错，不能一概忽略 `Close` 的返回值。

## 并发：goroutine 与 channel

goroutine 是由 Go 运行时调度的并发执行单元，使用 `go` 启动。
channel 用于传递有类型的数据，也能协调执行时序。
并发表示任务可以交错推进；是否并行运行取决于调度和可用计算资源。

```go
package main

import "fmt"

type Result struct {
	OrderID string
	Total   int
}

func calculate(orderID string, prices []int, results chan<- Result) {
	total := 0
	for _, price := range prices {
		total += price
	}
	results <- Result{OrderID: orderID, Total: total}
}

func main() {
	results := make(chan Result)
	go calculate("A100", []int{20, 30}, results)
	go calculate("B200", []int{15, 25}, results)

	// 明确接收两个结果，使 main 在任务完成前保持运行。
	for received := 0; received < 2; received++ {
		result := <-results
		fmt.Printf("订单 %s，总价 %d\n", result.OrderID, result.Total)
	}
}
```

两个订单的总价分别是 `50` 和 `40`，打印顺序不固定。
无缓冲 channel 的发送与接收需要配对，示例因此可以等待结果，而不依赖 `time.Sleep` 猜测执行时间。
这里接收次数已知，无需关闭 channel；若使用 `for range` 接收，应由负责发送的一方协调关闭。

goroutine 不会自动消除数据竞争。
多个 goroutine 读写共享 map 或变量时，需要使用互斥锁、原子操作，或通过 channel 转移数据。
可用 `go run -race .` 检查运行时实际触发的竞争；没有报告并不代表所有执行路径都安全。
使用方式与支持的平台见 [官方数据竞争检测文档](https://go.dev/doc/articles/race_detector)。
实际服务还需要限制并发数量，并通过 `context` 传递取消信号和截止时间。

## 工程工具链

在上述模块目录中，可以使用以下命令完成格式化、检查和构建：

```bash
go fmt ./...
go vet ./...
go test ./...
go build -o go-learning .
```

`go fmt` 统一代码格式，`go vet` 检查部分可疑用法，`go test` 运行测试，`go build` 生成可执行文件。
本教程未创建测试文件，因此 `go test` 会提示没有测试文件；业务项目应补充 `*_test.go`。
`./...` 表示当前目录及其子目录中的包。

需要第三方依赖时使用 Modules 管理，并通过 `go mod tidy` 整理依赖声明。
提交项目时通常同时提交 `go.mod` 和生成的 `go.sum`，不要手工猜测依赖校验值。

## 常见误区与排查

| 现象或误区 | 原因 | 处理方式 |
|------------|------|----------|
| `declared and not used` | 函数内声明的变量没有使用 | 删除无用变量或完成实际逻辑 |
| `imported and not used` | 导入了未使用的包 | 删除无用导入 |
| `no new variables on left side of :=` | 当前作用域中没有新变量 | 更新已有变量时使用 `=` |
| `assignment to entry in nil map` | 未初始化 map 就写入 | 用 `make` 或 map 字面量初始化 |
| 切片修改影响另一变量 | 两个切片共享底层数组 | 用 `make` 与 `copy` 复制元素 |
| goroutine 还没完成程序就退出 | `main` 返回会结束程序 | 使用 channel 或 `sync.WaitGroup` 等待 |
| 认为垃圾回收会关闭文件 | 内存管理与外部资源生命周期不同 | 显式关闭文件、响应体等资源 |
| 把字符串长度当作字符数 | `len(string)` 返回字节数 | 按 Unicode 码点遍历可使用 `range` |

## 与相关知识的关系

- [[数据结构|数据结构]]：帮助理解切片容量、复制开销与 map 的使用场景。
- [[操作系统|操作系统]]：帮助区分 goroutine、操作系统线程与并发同步。
- [[计算机网络|计算机网络]]：为后续学习 Go HTTP 服务和网络超时控制提供基础。

接下来可以尝试用标准库 `net/http` 编写一个健康检查接口，再补充参数校验与自动化测试。
在掌握语法之后，重点练习错误边界、资源释放和并发任务的退出条件。

## 参考

继续学习：[[go-type-system-and-memory|类型系统与内存语义]]。
完整路线见 [[02-backend/go/index|Go 开发学习路径]]。

- [Go 官方入门教程](https://go.dev/doc/tutorial/getting-started)
- [Go 语言规范](https://go.dev/ref/spec)
- [Go 标准库文档](https://pkg.go.dev/std)
- [A Tour of Go](https://go.dev/tour/)
