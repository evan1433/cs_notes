---
title: project-reactor
tag:
  - reactor
---
> **本笔记已拆分为专题**：概念、来源、使用、应用、代码案例、Sink 与 Processor 组件分别成篇，
> 入口见 [[02-backend/java-fundamentals/reactor/index|Project Reactor 专题]]。本页保留为速查与碎片笔记合集。

[Reactor 3 参考指南](https://easywheelsoft.github.io/reactor-core-zh/index.html#about-doc)

## reactive stream

---

​**​Reactive Stream 的核心思想​**​是通过​**​标准化异步流处理​**​，解决高并发场景下​**​生产者与消费者速率不匹配​**​的问题（即背压，Backpressure），确保系统在资源有限时仍能保持​**​弹性（Resilient）​**​和​**​高效性​**​。以下是其核心设计理念、关键组件及实际意义：

---
### ​**​一、核心设计理念​**​

#### 1. ​**​异步非阻塞通信​**​

- ​**​目标​**​：避免线程阻塞，最大化资源利用率。
- ​**​实现​**​：数据生产（Publisher）与消费（Subscriber）通过​**​异步消息传递​**​解耦，不依赖线程等待。
#### 2. ​**​背压（Backpressure）机制​**​

- ​**​问题​**​：生产者速度 > 消费者速度时，可能导致内存溢出或系统崩溃。
- ​**​方案​**​：消费者通过​**​动态请求（Demand Signaling）​**​控制数据流速。
    
```text
    示例流程：   
    1. 订阅者（Subscriber）向发布者（Publisher）订阅，并声明初始需求（如请求10个数据）。   
    2. 发布者按需求发送数据（最多10个）。   
    3. 订阅者处理完数据后，继续请求新数据（如再请求5个）。
```
    

#### 3. ​**​标准化接口​**​

- 定义统一的 API 规范（如 `Publisher`、`Subscriber`），确保不同库（如 Reactor、RxJava）的​**​互操作性​**​。

#### 4. ​**​动态性与弹性​**​

- 支持运行时动态调整数据流（如熔断、重试、流量控制），适应高负载或故障场景。

---

### ​**​二、关键组件​**​

Reactive Stream 规范（JVM 版）定义了四个核心接口：

#### 1. ​**​`Publisher<T>`（发布者）​**​

- ​**​职责​**​：生成数据流。
- ​**​核心方法​**​：`subscribe(Subscriber<? super T> s)`  
    _向发布者注册订阅者，建立数据流通道。_

#### 2. ​**​`Subscriber<T>`（订阅者）​**​

- ​**​职责​**​：消费数据，管理背压。
- ​**​核心方法​**​：
    - `onSubscribe(Subscription s)`：收到订阅令牌，可初始化请求。
    - `onNext(T data)`：接收数据。
    - `onError(Throwable t)`：处理错误。
    - `onComplete()`：流结束回调。

#### 3. ​**​`Subscription`（订阅令牌）​**​

- ​**​职责​**​：协调生产者和消费者的背压。
- ​**​核心方法​**​：
    - `request(long n)`：向生产者请求 `n` 个数据。
    - `cancel()`：终止数据流。

#### 4. ​**​`Processor<T, R>`（处理器）​**​

- ​**​职责​**​：同时扮演发布者和订阅者角色，用于数据转换（如过滤、映射）。
- ​**​示例​**​：`TransformProcessor`、`FilterProcessor`。

---

### ​**​三、数据流生命周期示例​**​

```
+------------+          subscribe()          +------------+   | Publisher  | ----------------------------> | Subscriber |   +------------+                               +------------+        ^                                              |        |                                              | onSubscribe(Subscription)        |                                              V        |                                        +------------+        |                                        | Subscription|        |                                        +------------+        |                                              |        | request(n)                                   | onNext(data)        +----------------------------------------------+
```

1. ​**​订阅建立​**​：订阅者调用 `Publisher.subscribe()`，触发 `onSubscribe()` 回调。
2. ​**​背压协商​**​：订阅者通过 `Subscription.request(n)` 声明初始需求。
3. ​**​数据传输​**​：发布者按需求调用 `onNext()` 发送数据，直至完成（`onComplete()`）或出错（`onError()`）。
4. ​**​动态调控​**​：订阅者可随时通过 `request(n)` 调整需求，或通过 `cancel()` 终止流。

---

### ​**​四、实际意义​**​

#### 1. ​**​解决高并发瓶颈​**​

- 传统阻塞模型（如 Tomcat 线程池）在并发连接激增时，线程资源迅速耗尽。
- ​**​Reactive Stream 方案​**​：通过非阻塞 I/O 和背压，单线程可处理数千并发连接（如 Netty + Reactor）。

#### 2. ​**​弹性系统设计​**​

- ​**​自动流量控制​**​：背压机制防止系统过载。
- ​**​故障恢复​**​：通过操作符（如 `retry`、`timeout`）实现容错。
    
    ```java
    Flux.from(publisher)       
    .timeout(Duration.ofSeconds(5))  // 超时熔断       
    .retry(3)                        // 自动重试3次
    .onErrorResume(fallbackFlow)     // 降级逻辑       
    .subscribe();
	```
    

#### 3. ​**​统一编程模型​**​

- 数据库、HTTP 客户端、消息队列等组件可通过 Reactive Stream 接口统一接入，形成端到端的非阻塞链路。
    
    ```java
    // 示例：响应式数据库查询 -> HTTP 响应   
    reactiveMongoRepository.findUsers()
    .map(user -> transform(user))
    .flatMap(data -> webClient.post().bodyValue(data).retrieve())
    .subscribe();
	```
    

---

### ​**​五、与其他技术的对比​**​

|​**​特性​**​|​**​传统阻塞式（如 Servlet）​**​|​**​Reactive Stream​**​|
|---|---|---|
|​**​线程模型​**​|每个请求占用一个线程|少量线程处理所有请求（事件循环）|
|​**​资源利用率​**​|低（线程空闲等待 I/O）|高（线程始终忙碌）|
|​**​背压支持​**​|无（易导致内存溢出）|内置动态背压控制|
|​**​适用场景​**​|低并发、同步任务|高并发、异步实时系统|

---

### ​**​六、挑战与局限​**​

1. ​**​调试复杂性​**​：异步调用链的堆栈跟踪难以追踪。
2. ​**​学习曲线​**​：需理解流式编程、函数式操作符（如 `flatMap`、`zip`）。
3. ​**​生态依赖​**​：需全链路支持非阻塞（如响应式数据库驱动）。

---

### ​**​七、总结​**​

Reactive Stream 的思想本质是​**​通过标准化接口和背压机制，实现高效的异步数据流处理​**​。其核心价值在于：

- ​**​资源高效​**​：非阻塞模型最大化利用 CPU 和内存。
- ​**​系统弹性​**​：背压和容错机制防止级联故障。
- ​**​组件解耦​**​：统一接口促进跨技术栈集成。

实际应用中，它尤其适合：

- 实时数据处理（如金融行情推送）
- 高并发 API 网关
- 微服务间异步通信
- 大数据流水线（如实时 ETL）

通过 Reactor、Akka Streams 或 RxJava 等实现库，开发者可构建高性能、响应式的现代应用系统。

## Flux 和 Mono常用api介绍
在Spring WebFlux中，`Flux`和`Mono`是**Project Reactor**提供的核心响应式类型，用于处理异步数据流。以下是它们的常用API分类及示例：

---

### ​**​1. 创建流​**​

#### ​**​Flux​**​

- `Flux.just(T...)`：创建包含多个元素的流。
    
    `Flux.just("A", "B", "C");`
    
- `Flux.fromIterable(Iterable)`：从集合创建流。
    
    `Flux.fromIterable(Arrays.asList(1, 2, 3));`
    
- `Flux.range(start, count)`：生成整数序列。
    
    `Flux.range(1, 5); // 1, 2, 3, 4, 5`
    
- `Flux.generate()`：同步生成元素（适合有状态流）。
    
    `Flux.generate(sink -> sink.next("data"));`
    
- `Flux.create()`：异步生成元素（支持多线程推送）。
    
    `Flux.create(sink -> asyncEventSource.onData(sink::next));`
    

#### ​**​Mono​**​

- `Mono.just(T)`：创建包含单个元素的流。
    
    `Mono.just("Hello");`
    
- `Mono.empty()`：创建空流。
    
    `Mono.empty();`
    
- `Mono.error(Throwable)`：创建包含错误的流。
    
    `Mono.error(new RuntimeException("Error"));`
    

---

### ​**​2. 转换操作​**​

#### ​**​通用操作（Flux和Mono都支持）​**​

- `map(Function<T, R>)`：同步转换元素。
    
    `flux.map(s -> s.toUpperCase());`
    
- `flatMap(Function<T, Publisher<R>>)`：异步转换元素为新的流并合并。
    
    `flux.flatMap(s -> Mono.just(s.length()));`
    
- `filter(Predicate<T>)`：过滤元素。
    
    `flux.filter(s -> s.startsWith("A"));`
    

#### ​**​Flux特有​**​

- `concatMap`：保持顺序的`flatMap`（逐个处理元素）。
- `flatMapSequential`：异步处理但按原始顺序合并结果。

---

### ​**​3. 组合流​**​

#### ​**​合并流​**​

- `Flux.merge(Publisher...)`：无序合并多个流。
    
    `Flux.merge(flux1, flux2);`
    
- `Flux.concat(Publisher...)`：按顺序连接流。
    
    `Flux.concat(flux1, flux2);`
    
- `Flux.zip(Publisher...)`：将多个流的元素按位置配对。
    
    `Flux.zip(flux1, flux2, (a, b) -> a + b);`
    

#### ​**​Mono特有​**​

- `Mono.when(Mono...)`：等待多个`Mono`完成。
    
    `Mono.when(mono1, mono2).then(() -> ...);`
    
- `Mono.zipWith(Mono)`：将两个`Mono`的结果配对。
    
    `mono1.zipWith(mono2, (a, b) -> a + b);`
    

---

### ​**​4. 错误处理​**​

- `onErrorReturn(T)`：出错时返回默认值。
    
    `flux.onErrorReturn("fallback");`
    
- `onErrorResume(Function<Throwable, Publisher<T>>)`：出错时切换为备用流。
    
    `flux.onErrorResume(ex -> fallbackFlux());`
    
- `retry(n)`：重试订阅（指定次数）。
    
    `flux.retry(3);`
    

---

### ​**​5. 背压控制​**​

- `limitRate(int)`：限制请求速率。
    
    `flux.limitRate(10); // 每次请求10个元素`
    
- `onBackpressureBuffer()`：缓存溢出的元素。

---

### ​**​6. 其他常用操作​**​

#### ​**​通用​**​

- `take(long)`：取前N个元素。
    
    `flux.take(3);`
    
- `skip(long)`：跳过前N个元素。
- `distinct()`：去重。
- `log()`：记录流事件（调试用）。

#### ​**​Flux特有​**​

- `collectList()`：将元素收集到`Mono<List<T>>`。
    
    `flux.collectList().subscribe(list -> ...);`
    
- `window(int)`：将流拆分为多个`Flux<T>`窗口。
    
    `flux.window(2); // 拆分为每2个元素一个窗口`
    

#### ​**​Mono特有​**​

- `flatMapMany(Function<T, Publisher<R>>)`：将`Mono`转换为`Flux`。
    
    `mono.flatMapMany(s -> Flux.just(s.split("")));`
    
- `defaultIfEmpty(T)`：流为空时返回默认值。
    
    `mono.defaultIfEmpty("default");`
    

---

### ​**​7. 订阅流​**​

- `subscribe()`：触发流执行，可自定义处理逻辑。
    
    ```java
    flux.subscribe(       
	    data -> System.out.println(data),       
	    err -> err.printStackTrace(),       
	    () -> System.out.println("Complete")   
	    );
	```
    

---

### ​**​总结​**​

- ​**​Flux​**​：处理0-N个元素的流，适合集合、实时数据推送等场景。
- ​**​Mono​**​：处理0-1个元素的流，适合HTTP请求、单个结果等场景。
- ​**​核心操作​**​：包括创建、转换、组合、错误处理等，结合背压控制实现高效异步处理。

通过合理组合这些API，可以构建高性能、非阻塞的响应式应用。


## Sink

在响应式编程（如 Project Reactor 或 Spring WebFlux）中，​**​`Sink`​**​ 是一个核心概念，字面意思是“水槽”，但你可以理解为一个​**​数据出口​**​。它允许你以编程方式手动控制数据流的发射（推送数据、完成信号或错误）。

---

### ​**​Sink 的作用​**​

当使用 `Flux.generate()`、`Flux.create()` 或类似方法创建自定义数据流时，你会得到一个 `Sink` 对象。通过它，你可以：

1. ​**​推送数据​**​：调用 `next(T)` 方法发射一个元素。
2. ​**​标记完成​**​：调用 `complete()` 方法表示流结束。
3. ​**​抛出错误​**​：调用 `error(Throwable)` 方法终止流并传递错误。

---

### ​**​Sink 的两种类型​**​

#### 1. ​**​`SynchronousSink`​**​（同步 Sink）

- ​**​使用场景​**​：在 `Flux.generate()` 中。
    
- ​**​特点​**​：​**​单线程同步生成数据​**​，每次调用 `next()` 只能发射一个元素，必须返回新的状态（用于生成下一个元素）。
    
    ```java
	Flux.generate(       () -> 0, // 初始状态：计数器从0开始           
	(state, sink) -> {  
	            sink.next("Value: " + state); // 发射当前状态               
	if (state == 5) sink.complete(); // 达到5时结束流               
	return state + 1; // 更新状态（下次调用时使用）           
	}  
	).subscribe(System.out::println);
	```
    

#### 2. ​**​`FluxSink`​**​（异步 Sink）

- ​**​使用场景​**​：在 `Flux.create()` 或 `Mono.create()` 中。
    
- ​**​特点​**​：​**​支持多线程异步生成数据​**​，可以多次调用 `next()`，需要手动管理背压（backpressure）和资源释放。
    
    ```java
	Flux.create(sink -> {       // 模拟异步事件（如监听消息队列）  
	    eventSource.registerListener(data -> {  
	        sink.next(data); // 异步推送数据             
	if (data.equals("END")) {  
	            sink.complete(); // 收到END时结束流             
	}  
	    });       // 资源清理（当流取消订阅时执行）         
	sink.onCancel(() -> eventSource.shutdown());  
	}).subscribe();
	```
    

---

### ​**​Sink 的常见方法​**​

|方法|说明|
|---|---|
|`sink.next(T)`|向订阅者推送一个元素。|
|`sink.complete()`|标记流正常结束（订阅者收到 `onComplete` 事件）。|
|`sink.error(Throwable)`|终止流并传递错误（订阅者收到 `onError` 事件）。|
|`sink.currentContext()`|获取当前响应式流的上下文（Context）。|
|`sink.onRequest(...)`|定义背压策略（处理订阅者的请求量）。|

---

### ​**​何时使用 Sink？​**​

1. ​**​生成自定义数据流​**​：例如从外部事件（如消息队列、WebSocket）转换为响应式流。
2. ​**​集成非响应式 API​**​：将阻塞或回调式代码封装为响应式流。
3. ​**​控制背压策略​**​：手动处理订阅者的请求速率（如 `onRequest`）。

---

### ​**​注意事项​**​

1. ​**​线程安全​**​：`FluxSink` 可能在多线程环境下使用，需确保线程安全。
2. ​**​资源管理​**​：在 `Flux.create()` 中注册的资源（如监听器）需通过 `sink.onDispose()` 或 `sink.onCancel()` 释放。
3. ​**​避免重复调用​**​：`complete()` 或 `error()` 调用后，流会终止，后续 `next()` 会被忽略。
4. ​**​背压处理​**​：如果不使用 `onRequest`，默认会启用无界缓冲（可能导致内存溢出）。

---

### ​**​示例场景​**​

#### 场景1：生成一个简单序列

```java
Flux.generate(sink -> {  
    sink.next("Hello");  // 发射数据         
	sink.complete();    // 立即结束   
	}).subscribe();
```

#### 场景2：异步推送事件

```java
Flux.create(sink -> {  
    // 模拟异步回调  
    asyncService.fetchData(new Callback() {  
        @Override  
        public void onData(String data) {  
            sink.next(data);  
        }  
  
        @Override  
        public void onComplete() {  
            sink.complete();  
        }  
  
        @Override  
        public void onError(Throwable e) {  
            sink.error(e);  
        }  
    });  
});
```

---

### ​**​总结​**​

- ​**​`Sink`​**​ 是响应式编程中​**​手动控制数据流​**​的核心工具。
- 使用 `SynchronousSink`（同步）或 `FluxSink`（异步）取决于是否需要在多线程环境下生成数据。
- 确保正确处理资源释放和背压，避免内存泄漏或数据丢失。


## Mono.defer

在 Spring WebFlux 中，`Mono.defer` 是一个用于​**​延迟创建 `Mono`​**​ 的操作符。它的核心意义是：​**​直到有订阅者订阅时，才真正创建 `Mono` 实例​**​。这可以避免在声明阶段就固定数据源，使每次订阅都能动态生成新的数据流。

---

### ​**​为什么需要 `Mono.defer`？​**​

直接使用 `Mono.just()` 或 `Mono.error()` 时，数据源的创建是​**​即时（eager）​**​的，即在声明阶段就确定了值。而 `Mono.defer` 允许​**​延迟（lazy）​**​创建数据源，适用于以下场景：

1. ​**​每次订阅需要动态生成数据​**​（如获取当前时间、动态计算结果）。
2. ​**​避免副作用过早执行​**​（如延迟执行数据库查询）。
3. ​**​确保每次订阅得到独立的数据流​**​。

---

### ​**​实例对比​**​

#### 场景1：每次订阅返回最新的时间戳

```java
// 错误写法：时间戳在声明时固定     
Mono<Long> mono = Mono.just(System.currentTimeMillis());  
// 正确写法：每次订阅获取最新时间     
Mono<Long> deferredMono = Mono.defer(() -> Mono.just(System.currentTimeMillis()));  
// 测试     
deferredMono.subscribe(time -> System.out.println("Sub1: " + time));  
// 输出当前时间     
Thread.sleep(1000);  
        deferredMono.subscribe(time -> System.out.println("Sub2: " + time));  
// 1秒后的时间（与Sub1不同）
```

#### 场景2：延迟执行数据库查询

```java
Mono<User> getUserById(String id) {
	return Mono.defer(() ->  // 每次订阅时才执行查询（避免声明时立即执行）       
	Mono.fromCallable(() -> database.findUserById(id)) );   
	}
```

#### 场景3：动态生成成功/失败的流

```java
static Mono<String> riskyOperation() {  
    return Mono.defer(() -> {  
        double random = Math.random();  
        if (random > 0.5) {  
            return Mono.just("Success!");  
        } else {  
            return Mono.error(new RuntimeException("Failed"));  
        }  
    });  
}

riskyOperation()  
        .subscribe(success -> System.out.println(success),   
                error -> System.err.println(error.getMessage()));


```

---

### ​**​`Mono.defer` 的工作原理​**​

1. ​**​声明阶段​**​：只是包装一个 `Supplier<Mono<T>>`，不会执行具体逻辑。
2. ​**​订阅阶段​**​：当有订阅者订阅时，调用 `Supplier` 生成一个新的 `Mono` 实例。
3. ​**​数据流隔离​**​：每次订阅都会触发独立的 `Mono` 创建，确保数据源的动态性。

---

### ​**​常见使用场景​**​

1. ​**​依赖外部状态​**​（如当前时间、动态配置）。
2. ​**​需要重试的逻辑​**​（每次重试重新生成流）。
3. ​**​避免副作用提前触发​**​（如日志、资源分配）。

---

### ​**​与 `Mono.fromSupplier` 的区别​**​

- `Mono.fromSupplier`：延迟生成​**​数据值​**​（直接返回值本身）。
- `Mono.defer`：延迟生成​**​整个 `Mono` 数据流​**​（可以包含复杂逻辑）。

```java
        // 返回一个固定的值（延迟获取）  
        Mono.fromSupplier(() -> "Value: " + System.currentTimeMillis());  
		// 返回一个动态生成的流（可以包含错误、空等逻辑）  
        Mono.defer(() -> {  
            if (condition) {  
                return Mono.just("OK");  
            } else {  
                return Mono.error(new RuntimeException());  
            }  
    });

```

---

### ​**​总结​**​

- ​**​`Mono.defer`​**​ 用于延迟创建 `Mono`，确保每次订阅生成独立的数据流。
- 适用于需要动态数据源、避免副作用或隔离订阅上下文的场景。
- 与 `Mono.just` 等即时操作符互补，增强响应式流的灵活性。


## java函数式编程

Java 的函数式编程是 ​**​以 Lambda 表达式和函数式接口为核心​**​ 的编程范式，旨在简化代码、提升可读性，并支持更灵活的集合操作和异步处理。以下是关键概念和实例解析：

---

### ​**​一、核心概念​**​

#### 1. ​**​Lambda 表达式​**​

- ​**​本质​**​：匿名函数，简化单方法接口的实现。
- ​**​语法​**​：`(参数) -> { 逻辑 }`
    
    ```java
    // 传统写法（匿名内部类）   
    Runnable r1 = new Runnable() {      
     @Override       
     public void run() { System.out.println("Hello"); }   
     };     
     // Lambda 写法   
     Runnable r2 = () -> System.out.println("Hello");
	```
    

#### 2. ​**​函数式接口（Functional Interface）​**​

- ​**​定义​**​：仅含一个抽象方法的接口，可用 `@FunctionalInterface` 标注。
- ​**​常见接口​**​：
    - `Consumer<T>`：消费数据，`void accept(T t)`
    - `Function<T,R>`：转换数据，`R apply(T t)`
    - `Predicate<T>`：条件判断，`boolean test(T t)`
    - `Supplier<T>`：提供数据，`T get()`

#### 3. ​**​方法引用​**​

- ​**​简化 Lambda​**​：直接指向已有方法。
- ​**​四种形式​**​：
    
    ```java
    // 静态方法引用   
    Function<String, Integer> parser = Integer::parseInt;     
     // 实例方法引用   
     List<String> list = Arrays.asList("A", "B");
     list.forEach(System.out::println);       
     // 构造方法引用   
     Supplier<List<String>> supplier = ArrayList::new;
	```
    

---

### ​**​二、函数式编程实践​**​

#### 1. ​**​Stream API​**​

- ​**​作用​**​：对集合进行链式操作（过滤、映射、归约等）。
- ​**​示例​**​：
    
    ```java
    List<String> names = Arrays.asList("Alice", "Bob", "Charlie");      // 过滤长度>3的名字，转大写，收集到List   
    List<String> result = names.stream()
    .filter(s -> s.length() > 3)
    .map(String::toUpperCase)
    .collect(Collectors.toList()); // [ALICE, CHARLIE]
	```
    

#### 2. ​**​Optional 类​**​

- ​**​作用​**​：优雅处理 `null`，避免空指针异常。
    
    ```java
    Optional<String> name = Optional.ofNullable(getName());   
    String value = name.orElse("Default"); // 非空时返回值，否则返回"Default"
	```
    

#### 3. ​**​并行流（Parallel Stream）​**​

- ​**​作用​**​：利用多核并行处理数据。
    
    ```java
    List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5);   
    int sum = numbers.parallelStream().mapToInt(n -> n * 2).sum(); // 并行计算总和
	```
    

---

### ​**​三、函数式编程的优势​**​

1. ​**​代码简洁​**​：减少模板代码（如循环、条件判断）。
2. ​**​声明式风格​**​：关注“做什么”而非“如何做”。
3. ​**​易于并行化​**​：通过 `parallelStream` 简化多线程编程。
4. ​**​组合性​**​：通过链式调用组合复杂逻辑。

---

### ​**​四、实际应用场景​**​

#### 1. ​**​集合处理​**​

```java
// 统计单词频率   
List<String> words = Arrays.asList("apple", "banana", "apple");   Map<String, Long> frequency = words.stream()       .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));   
// {banana=1, apple=2}
```

#### 2. ​**​异步回调​**​

```java
CompletableFuture.supplyAsync(() -> fetchDataFromDB())
.thenApply(data -> processData(data))
.thenAccept(result -> sendToUI(result))
.exceptionally(ex -> handleError(ex));
```

#### 3. ​**​条件过滤链​**​

```java
Predicate<String> isLong = s -> s.length() > 5;   
Predicate<String> containsA = s -> s.contains("A");      
List<String> filtered = list.stream()
.filter(isLong.and(containsA))
.collect(Collectors.toList());

```

---

### ​**​五、注意事项​**​

1. ​**​性能开销​**​：Stream 的链式操作可能比传统循环慢（小数据量无需过度优化）。
2. ​**​状态隔离​**​：Lambda 中避免修改外部变量（应使用 `final` 或等效不可变变量）。
3. ​**​调试困难​**​：链式调用可能导致堆栈跟踪复杂化。

---

### ​**​六、总结​**​

Java 函数式编程通过 ​**​Lambda、Stream、Optional​**​ 等工具，显著提升了代码的表达力和简洁性。适用于集合操作、异步处理和条件组合等场景。建议结合 Java 8+ 特性（如 `CompletableFuture`、`LocalDateTime`）深入学习，掌握函数式与面向对象的混合使用技巧。




## 副作用


这是一个非常常见的 **响应式编程** 场景：你有一个数字流（如 `Flux<Integer>`），你需要对每个数字进行处理，并在这个过程中 **改变其他对象的状态**。这种“改变其他对象状态”的行为，本质上属于 **副作用（side-effect）**。

---

### ✅ 你的问题可以拆解为：

> 如何在 Reactor 流中执行副作用操作（比如修改外部对象的状态）？

#### 🔹 回答是：
- 如果 **不需要返回新值**，而是只想基于当前元素去修改外部状态，使用 `doOnNext`、`subscribe` 或 `doOnEach`。
- 如果 **需要根据输入数据生成新的数据流或结果**，再影响外部状态，则结合 `map` / `flatMap` + 副作用操作。

---

#### 🧩 示例场景

假设你有如下需求：

```java
List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5);
AtomicInteger counter = new AtomicInteger(0); // 外部状态
```

你想遍历这些数字，**每处理一个数就更新 `counter` 的值**。

---

### ✅ 方法一：使用 `doOnNext`（推荐用于副作用）

适用于你只关心每个元素的值，不打算转换它，只是想做一些额外操作（如记录日志、修改外部变量等）。

```java
Flux.fromIterable(numbers)
    .doOnNext(num -> {
        System.out.println("Processing number: " + num);
        counter.addAndGet(num); // 修改外部状态
    })
    .subscribe(); // 必须订阅才能触发流
```

✅ 特点：
- 不会改变数据流本身。
- 只是插入一些副作用逻辑。
- 推荐用于“观察”流中的数据并产生副作用。

---

### ✅ 方法二：使用 `map` + 副作用（如果你想转换数据的同时改变状态）

如果你不仅想修改外部状态，还想转换流中的数据，可以用 `map`：

```java
Flux.fromIterable(numbers)
    .map(num -> {
        counter.addAndGet(num); // 改变外部状态
        return num * 2; // 同时返回新值
    })
    .subscribe(System.out::println);
```

✅ 特点：
- 同时完成数据转换和副作用。
- 更适合“一边改状态一边生成新数据”的情况。

---

### ✅ 方法三：直接使用 `subscribe`（最简单方式）

如果你并不需要继续链式操作，可以直接在 `subscribe()` 中处理副作用：

```java
Flux.fromIterable(numbers)
    .subscribe(num -> {
        System.out.println("Received: " + num);
        counter.addAndGet(num);
    });
```

✅ 特点：
- 最简单直接的方式。
- 但只能用在流的末端（不能再链式调用其他操作符）。

---

### ⚠️ 注意事项

#### 🔸 1. **副作用必须是线程安全的**
如果你的流是异步/并发执行的（例如用了 `.parallel()` 或 `.publishOn()`），那你要确保访问共享状态（如 `counter`）是线程安全的。

推荐使用：
- `AtomicInteger`
- `synchronized` 块
- `volatile` 字段（视具体使用场景而定）

#### 🔸 2. **Reactor 是惰性的**
除非你调用 `subscribe()`，否则上面的任何操作都不会执行。

---

### ✅ 进阶：结合 flatMap 异步处理并修改状态

如果你的处理过程是异步的（比如网络请求、数据库查询），你可以用 `flatMap` 并配合副作用：

```java
Flux.fromIterable(numbers)
    .flatMap(num -> Mono.fromCallable(() -> {
        // 模拟耗时操作
        Thread.sleep(100);
        int result = num * 2;
        counter.addAndGet(result); // 修改状态
        return result;
    }))
    .subscribe(System.out::println);
```

---

### ✅ 总结对比表

| 方法         | 是否改变流内容 | 是否支持副作用 | 是否适合异步处理 | 推荐用途 |
|--------------|----------------|----------------|------------------|-----------|
| `doOnNext`   | ❌ 否           | ✅ 是           | ✅ 是             | 日志、监控、副作用 |
| `map`        | ✅ 是           | ✅ 是           | ❌ 否（同步）     | 数据转换+副作用 |
| `subscribe`  | ❌ 否           | ✅ 是           | ✅ 是             | 终止操作、最终消费 |
| `flatMap`    | ✅ 是           | ✅ 是           | ✅ 是             | 异步处理+副作用 |

---

### 📎 补充建议

如果你要处理的是：

- **顺序任务** → 使用 `concatMap`
- **限流控制** → 使用 `limitRate(n)`
- **背压管理** → 使用 `onBackpressureBuffer` / `drop` / `latest`
- **错误恢复** → 使用 `onErrorResume`, `retry`

---

如果你能提供更具体的业务逻辑（比如你想修改哪些对象的状态、是否涉及异步等），我可以给出更贴合实际的代码示例。欢迎继续提问！