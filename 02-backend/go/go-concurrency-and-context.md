---
title: Go 并发与生命周期管理
description: 掌握 channel、锁、context 与并发上限，编写可取消、可等待且无数据竞争的 Go 任务。
tags:
  - go
  - concurrency
  - context
date: 2026-11-18
---

# Go 并发与生命周期管理

## 概述

启动 goroutine 很容易，确保它在失败、超时和服务关闭时退出才是工程重点。
本篇围绕任务所有权建立并发模型：谁启动，谁协调取消，谁等待，谁关闭通信通道。
目标是让任务既能并发推进，也能在有限资源内可靠停止。

## 前置知识与运行约定

先阅读 [[go-language-basics|Go 语言入门]] 和 [[go-errors-and-resources|错误与资源管理]]。
所有示例要求 Go 1.24 或更高版本，只使用标准库。
每个独立示例在新目录保存为 `main.go`，运行：

```bash
go mod init example.com/concurrency-demo
go run -race .
go vet ./...
```

竞争检测依赖受支持的平台及相应工具链环境；它只能发现实际执行路径上的竞争。
示例使用 `WaitGroup.Add/Done`，方便在最低版本运行，不依赖更高版本新增的方法。

## 先明确共享状态与同步关系

goroutine 是运行时调度的并发执行单元，不等同于一个固定的操作系统线程。
多个 goroutine 可以交错执行，也可能在多核上并行；调度先后不能作为同步保证。

如果两个 goroutine 访问同一内存位置，其中至少一个是写入，且缺少必要同步，就可能存在数据竞争。
“我观察到它总是先运行”无法证明安全，`time.Sleep` 也不会建立内存同步关系。
同步不仅用于避免同时操作，还用于确保其他 goroutine 能观察到正确的数据。
详细规则见 [Go 内存模型](https://go.dev/ref/mem)。

| 机制 | 解决的问题 | 注意事项 |
|------|------------|----------|
| `sync.Mutex` | 保护多字段不变量或临界区 | 所有相关访问应遵循同一把锁 |
| `sync.RWMutex` | 区分只读访问与独占写入 | 不能简单假设读多时一定更快 |
| 原子操作 | 单个值的原子更新与读取 | 不自动维护多个字段之间的约束 |
| channel | 传递数据与协调事件 | 每一次阻塞都要考虑退出条件 |
| `sync.WaitGroup` | 等待一组任务完成 | 不负责传递错误，也不负责取消 |
| `context` | 传播取消和截止时间 | 不会强制终止不检查它的代码 |

`Mutex.Unlock` 与后续相应的 `Lock`、channel 的发送与对应接收等建立规定的同步关系。
不要用普通布尔变量在两个 goroutine 之间发送“已经完成”的信号。

## 独立示例 A：用锁维护共享订单统计

保存为 `main.go`：

```go
package main

import (
	"fmt"
	"sync"
)

type Counter struct {
	mu     sync.Mutex
	orders map[string]int
}

func (c *Counter) Add(customer string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.orders[customer]++
}

func (c *Counter) Count(customer string) int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.orders[customer]
}

func main() {
	counter := &Counter{orders: make(map[string]int)}
	var workers sync.WaitGroup
	for worker := 0; worker < 4; worker++ {
		workers.Add(1)
		go func() {
			defer workers.Done()
			for order := 0; order < 100; order++ {
				counter.Add("customer-1")
			}
		}()
	}
	workers.Wait()
	fmt.Println(counter.Count("customer-1"))
}
```

预期输出为 `400`，竞争检测应无报告。
计数器使用指针传递，避免复制已经使用的锁；读取与写入都遵守同一锁协议。
`Add(1)` 在启动 goroutine 前执行，避免等待方过早观察到计数为零。
`Done` 安排在 defer 中，确保任务正常返回或提前返回时都能减少计数。

如果只有一个独立计数值，`atomic.Int64` 可以简化实现；但“余额扣减与订单插入同时成立”
属于跨字段、甚至跨系统的约束，不能靠一个原子计数器代替事务或锁。
不要持有锁执行缓慢网络请求，否则其他任务会长时间等待。

## channel：状态、方向与关闭责任

无缓冲 channel 需要发送和接收配对；有缓冲 channel 在容量耗尽时仍会阻塞。
缓冲区只能吸收有限突发量，不能解决无限生产或缺少消费者的问题。

| 操作 | nil channel | 已关闭 channel |
|------|-------------|----------------|
| 发送 | 永久阻塞 | panic |
| 接收 | 永久阻塞 | 先取完缓冲数据，再立即得到零值和 `ok=false` |
| 关闭 | panic | 再次关闭会 panic |

`value, ok := <-ch` 中的 `ok` 用于区分真实零值与通道结束。
`for range ch` 会持续接收直到关闭并排空，不能在发送方永不关闭时自然结束。
关闭表达“以后不会再发送”，通常由拥有发送生命周期的一方执行。
有多个发送方时，应由协调者等待所有发送方结束后统一关闭，而不是每个发送方自行关闭。

`chan<- T` 和 `<-chan T` 可以限制函数能做的操作，但不会自动解决关闭责任。
不需要向接收者广播结束且接收次数明确时，可以不关闭 channel；回收内存不以 close 为前提。

## context：取消是一份合作协议

将 `context.Context` 作为需要取消的函数的第一个参数，沿调用链传递。
使用 `WithCancel`、`WithTimeout` 或 `WithDeadline` 创建子上下文后，应调用返回的 cancel 释放相关资源。
不要把请求 context 长期保存在全局对象中；独立后台任务应拥有明确的服务级生命周期。

收到 `ctx.Done()` 不代表任务已结束；取消方仍需等待任务退出。
`ctx.Err()` 通常返回 `context.Canceled` 或 `context.DeadlineExceeded`。
CPU 密集循环要主动检查取消，数据库和 HTTP 调用要使用接受 context 的 API。

context 的值只适合跨 API 传递请求范围的数据，例如请求标识，不能作为隐式配置容器。
业务必需参数应显式传入；私有类型的 key 可以减少不同包之间发生键冲突的风险。

## 独立示例 B：有上限、可取消的任务处理器

下面使用两个 worker 处理订单，不会为每个订单无界创建 goroutine。
保存为 `main.go`；正常运行输出四个金额结果，顺序不固定。

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"
)

type Order struct {
	ID    int
	Price int
}

type Result struct {
	ID    int
	Total int
}

func process(ctx context.Context, orders []Order, limit int) ([]Result, error) {
	if limit <= 0 {
		return nil, errors.New("worker 数量必须大于零")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	jobs := make(chan Order)
	results := make(chan Result)
	var workers sync.WaitGroup

	for worker := 0; worker < limit; worker++ {
		workers.Add(1)
		go func() {
			defer workers.Done()
			for {
				select {
				case <-ctx.Done():
					return
				case order, ok := <-jobs:
					if !ok {
						return
					}
					result := Result{ID: order.ID, Total: order.Price * 2}
					select {
					case results <- result:
					case <-ctx.Done():
						return
					}
				}
			}
		}()
	}

	producerDone := make(chan struct{})
	go func() {
		defer close(producerDone)
		defer close(jobs)
		for _, order := range orders {
			select {
			case jobs <- order:
			case <-ctx.Done():
				return
			}
		}
	}()
	go func() {
		workers.Wait()
		close(results)
	}()

	var collected []Result
	for result := range results {
		collected = append(collected, result)
	}
	<-producerDone
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return collected, nil
}

func main() {
	orders := []Order{{1, 10}, {2, 20}, {3, 30}, {4, 40}}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if len(os.Args) > 1 && os.Args[1] == "cancel" {
		cancel()
	}
	results, err := process(ctx, orders, 2)
	if err != nil {
		fmt.Println("任务结束：", err)
		return
	}
	for _, result := range results {
		fmt.Printf("订单 %d：%d\n", result.ID, result.Total)
	}
}
```

分别验证正常与取消路径：

```bash
go run -race .
go run -race . cancel
```

第一条命令返回订单 1–4，金额分别为 20、40、60、80；第二条返回 `任务结束： context canceled`。
第二条使用提前取消确保结果可复现；运行中取消也由同样的 channel 分支处理。
练习时可以在任务获取后通过受控信号取消，验证工作中途退出，而不是用睡眠推测时序。

### 生命周期逐项核对

- `process` 启动并等待这一批任务，调用方控制父 context。
- 生产者是 `jobs` 的唯一发送方，因此负责关闭 `jobs`。
- worker 可以阻塞在获取任务或发送结果的位置，两处都有取消分支。
- 协调者等待全部 worker，再关闭 `results`，避免向已关闭通道发送。
- 主调用收完 `results`，再等待生产者退出，不把后台活动遗留给调用方。

`select` 在多个分支同时就绪时不会优先选择取消分支。
因此取消不等于“从此绝不会再计算一项”，更不能作为撤销已发生外部副作用的保证。
如果真实处理会写库，应将 context 传入数据库调用，并通过事务与幂等规则处理提交边界。
本例发生取消时丢弃已收集结果；若业务允许部分成功，应显式设计返回类型和重试规则。

## select、背压与超时设计

在 `select` 中添加 `default` 会让所有通信都不能立即完成时直接执行该分支。
持续循环中的 default 可能形成忙等，应在确实需要非阻塞尝试时使用。
把某个接收 channel 设为 nil，可以暂时禁用对应分支，但所有分支都失效时仍可能永久等待。

背压表示下游速度影响上游生产速度。本例无缓冲 `jobs` 会限制生产者超前投递，
但仍保存了调用方传入的全部订单；处理无限数据流时还要限制输入队列和结果存储。

对网络或数据库任务，优先设置实际操作的超时，不要只给外围 goroutine 一个超时后就不管它。
如果底层操作不支持取消，外层提前返回仍可能留下持续运行的任务。
使用计时器后应按其 API 管理生命周期，避免每轮循环重复创建不必要的长寿命定时资源。

## 排查死锁、泄漏与取消失效

| 现象 | 常见原因 | 排查方向 |
|------|----------|----------|
| 任务无法结束 | 发送端等待一个已退出的接收端 | 检查每个阻塞点的取消分支 |
| range 永不返回 | 没有协调者关闭通道 | 明确唯一关闭责任 |
| 偶发 map 崩溃或 race 报告 | 共享数据缺少一致同步 | 保护全部访问，而不只写入 |
| worker 数量持续增长 | 每个请求无界启动后台任务 | 限制并发并等待退出 |
| 调用 cancel 后仍很慢 | 底层调用不响应 context | 检查实际 I/O API 和 CPU 循环 |
| WaitGroup 提前返回或 panic | Add 时机不正确或 Done 次数不匹配 | 启动前登记，任务内 defer Done |

死锁检测不保证发现所有局部挂起：HTTP 服务可能仍在接收其他请求，而某一批任务已经永远阻塞。
借助 goroutine profile 和执行追踪观察等待位置，方法见 [[go-runtime-and-diagnostics|运行时与诊断]]。

## 自测与扩展练习

1. 给示例 B 增加非法订单错误，要求第一次业务失败时取消其他任务，并等待所有 goroutine 退出。
2. 用测试可控制的信号协调“任务开始 → 取消 → 任务退出”，验证取消，不依赖 `time.Sleep`。
3. 把结果收集改为回调，讨论回调很慢或失败时应如何施加背压、取消并处理部分结果。
4. 解释为什么给 `results` 增加一个缓冲区，不能证明所有发送方都不会泄漏。

完成标准：能够对每个 goroutine 画出启动、阻塞、取消和退出路径，并说明每个共享变量的同步机制。

## 与相关概念的关系

- [[go-type-system-and-memory|类型与内存语义]]：理解共享对象后才能判断哪些访问需要同步。
- [[go-project-design-patterns|工程组织与设计模式]]：比较 Worker Pool、Pipeline 与扇出扇入。
- [[go-testing-and-quality|测试与质量保障]]：用竞争检测和可控时序验证并发行为。
- [[01-cs-fundamentals/operating-systems|操作系统]]：理解调度、线程和同步的基本概念。

## 参考

- [Go 内存模型](https://go.dev/ref/mem)
- [context 标准库](https://pkg.go.dev/context)
- [sync 标准库](https://pkg.go.dev/sync)
- [sync/atomic 标准库](https://pkg.go.dev/sync/atomic)
- [官方并发模式：Pipeline 与取消](https://go.dev/blog/pipelines)
- [数据竞争检测](https://go.dev/doc/articles/race_detector)
