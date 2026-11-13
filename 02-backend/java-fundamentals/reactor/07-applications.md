---
title: Reactor 应用场景
description: Reactor 在 Spring WebFlux、Cloud Gateway、Reactor Netty、R2DBC、RSocket、流式 AI 中的位置，以及生产实践与选型边界
tags:
  - java
  - reactor
  - spring
  - webflux
  - architecture
date: 2026-11-13
aliases:
  - reactor-applications
  - 响应式应用
---

# Reactor 应用场景

## 概述

Reactor 在真实系统里很少被"直接使用"，它更多是**框架之间的公共语言**：WebFlux 用它表达请求处理，
R2DBC 用它表达查询结果，Reactor Netty 用它表达字节流，你的业务代码只是接住这些 `Flux`/`Mono` 再交出去。
理解"哪些组件在用、边界在哪"，比多背十个操作符更有用。

本篇先给全景，再逐层看典型代码，最后给生产实践与选型边界。

## 前置知识

- [[03-usage|使用指南]]：操作符与线程切换
- [[04-sink|Sink 组件]]：SSE/WebSocket 广播的实现手段
- [[spring-webflux|Spring WebFlux]]：Spring 侧的完整视角

## 一、全景：Reactor 出现在哪一层

| 层 | 组件 | Reactor 的位置 | 典型返回类型 |
|----|------|----------------|--------------|
| Web 框架 | Spring WebFlux | 请求处理返回值 | `Mono<T>` / `Flux<T>` |
| HTTP 客户端 | `WebClient` | 响应体 | `Mono<T>` / `Flux<T>` |
| 网关 | Spring Cloud Gateway | 过滤器链 | `Mono<Void>` |
| 网络层 | Reactor Netty | 连接/字节流 | `Flux<ByteBuf>` |
| 数据访问 | R2DBC、Spring Data Reactive | 查询结果 | `Flux<T>` / `Mono<T>` |
| 消息 | Reactor Kafka、Reactor RabbitMQ | 消费/发送 | `Flux<ConsumerRecord>` |
| RPC | RSocket | 请求/流 | `Mono` / `Flux` |
| 流式 AI | Spring AI | token 流 | `Flux<String>` |
| 缓存 | Reactive Redis | 读写 | `Mono<V>` |

一句话：**从入口到数据库，整条链路都用同一种类型表达异步**，这就是"端到端非阻塞"的含义。
链路上只要有一环回到阻塞，这条收益链就断了。

## 二、Spring WebFlux：返回值即流

```java
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
public class OrderController {

    private final ReactiveOrderRepository repository;   // 返回 Mono/Flux 的仓储

    public OrderController(ReactiveOrderRepository repository) {
        this.repository = repository;
    }

    /** 单值：框架订阅，不需要也不允许 block() */
    @GetMapping("/orders/{id}")
    public Mono<Order> get(@PathVariable String id) {
        return repository.findById(id)
                .switchIfEmpty(Mono.error(new OrderNotFoundException(id)));
    }

    /** 多值流式：SSE，客户端边收边渲染 */
    @GetMapping(value = "/orders/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<Order> stream() {
        return repository.findAll();
    }
}
```

要点：`Controller` 方法**不订阅**，只返回流水线；订阅与背压由 WebFlux 的运行时处理。
一旦你在里面写 `block()`，WebFlux 会在事件循环线程上抛
`IllegalStateException: block()/blockFirst()/blockLast() are blocking, which is not supported in thread reactor-http-nio-*`。

## 三、WebClient：非阻塞 HTTP 客户端

```java
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;

public class UserClient {

    private final WebClient client = WebClient.builder()
            .baseUrl("https://user-service")
            .build();

    public Mono<User> find(String id) {
        return client.get()
                .uri("/users/{id}", id)
                .retrieve()
                .bodyToMono(User.class)
                .timeout(Duration.ofMillis(500))
                .onErrorResume(e -> Mono.just(User.anonymous()));   // 降级
    }

    /** 流式响应：bodyToFlux 天然支持分块 */
    public Flux<Event> subscribeEvents() {
        return client.get()
                .uri("/events")
                .accept(org.springframework.http.MediaType.TEXT_EVENT_STREAM)
                .retrieve()
                .bodyToFlux(Event.class);
    }
}
```

与 `RestTemplate` 的差异不只是"异步"：`WebClient` 复用同一个事件循环，连接与线程都不随并发线性增长；
`RestTemplate` 每个请求占一个线程直到响应返回。

## 四、Spring Cloud Gateway：过滤器链就是 `Mono<Void>`

```java
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

public class TraceIdFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String traceId = exchange.getRequest().getHeaders().getFirst("X-Trace-Id");
        if (traceId == null) {
            traceId = java.util.UUID.randomUUID().toString();
        }
        String finalTraceId = traceId;

        // 请求前加头，响应后记录耗时：前后两段用 then/thenReturn 串起来
        return chain.filter(exchange.mutate()
                        .request(r -> r.headers(h -> h.set("X-Trace-Id", finalTraceId)))
                        .build())
                .then(Mono.fromRunnable(() ->
                        System.out.println("done trace=" + finalTraceId)));
    }

    @Override
    public int getOrder() { return -100; }
}
```

网关是 Reactor 最"天然"的场景：它的工作就是转发 I/O，几乎没有计算，用线程模型换并发毫无意义。

## 五、数据访问：R2DBC 与响应式仓储

```java
import org.springframework.r2dbc.core.DatabaseClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

public class OrderR2dbcRepository {

    private final DatabaseClient client;

    public OrderR2dbcRepository(DatabaseClient client) {
        this.client = client;
    }

    public Flux<Order> findByStatus(String status) {
        return client.sql("select id, amount, status from orders where status = :status")
                .bind("status", status)
                .map((row, meta) -> new Order(
                        row.get("id", String.class),
                        row.get("amount", java.math.BigDecimal.class),
                        row.get("status", String.class)))
                .all();                                  // Flux<Order>
    }

    public Mono<Long> count() {
        return client.sql("select count(*) as c from orders")
                .map((row, meta) -> row.get("c", Long.class))
                .one();                                  // Mono<Long>
    }
}
```

注意：**传统 JDBC 没有非阻塞驱动**，JDBC 调用必须包进 `boundedElastic`，否则就是把阻塞塞进事件循环。
这是"响应式改造"最常见的假动作——接口变成了 `Mono`，底层还在阻塞。

## 六、消息：Reactor Kafka

```java
import reactor.core.publisher.Flux;
import reactor.kafka.receiver.KafkaReceiver;
import reactor.kafka.receiver.ReceiverOptions;

import java.util.Collections;

public class OrderConsumer {

    public Flux<String> consume(ReceiverOptions<String, String> options) {
        return KafkaReceiver.create(options.assignment(
                        s -> s.topicPartitions(Collections.singleton(
                                new org.apache.kafka.common.TopicPartition("orders", 0)))))
                .receive()
                .map(record -> {
                    // 业务处理放在 map/flatMap 里，处理完再 commit，天然形成"处理-提交"顺序
                    return record.value();
                })
                .doOnNext(v -> System.out.println("consumed " + v));
    }
}
```

Reactor Kafka 把"拉取-处理-提交"三段变成一条链，背压直接作用在 poll 上：**下游慢，poll 就慢**，
不会出现"拉了一大堆堆在内存里"。

## 七、流式 AI：`Flux<String>` 是标准形态

大模型推理的返回是一串 token，这与 `Flux` 的语义天然同构：

```java
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

@RestController
public class DiagnosisController {

    private final ChatClient chatClient;

    public DiagnosisController(ChatClient chatClient) {
        this.chatClient = chatClient;
    }

    /** 边生成边推送，前端逐字渲染；用户关闭页面时框架取消订阅，推理随之停止 */
    @GetMapping(value = "/diagnosis/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> stream(@RequestParam String complaint) {
        return chatClient.prompt()
                .user("请基于主诉给出鉴别诊断思路：" + complaint)
                .stream()
                .content();                            // Flux<String>，逐 token
    }
}
```

这套结构在医疗问答、客服、代码补全里是通用范式。三个工程要点：

1. **取消传播**：客户端断开 → 订阅取消 → 上游 HTTP 连接关闭 → 推理停止计费。这是响应式相对"轮询"的实质优势。
2. **首 token 超时**：用 `timeout` 卡住"迟迟不吐第一个字"，比整体超时更贴近用户体验。
3. **错误降级**：流已经发出部分内容后报错，前端要能处理"半截回答"，后端用 `onErrorResume` 追加提示而不是抛 500。

## 八、虚拟线程时代还要不要 Reactor

Spring Boot 3.2 起一行 `spring.threads.virtual.enabled=true` 就能让 MVC + JDBC 获得接近响应式的吞吐。
于是选型问题变成：**这件事的本质是"等 I/O"还是"处理一条随时间到达的数据流"？**

| 场景 | 推荐 | 理由 |
|------|------|------|
| 常规 CRUD（JDBC/同步 SDK） | MVC + 虚拟线程 | 代码简单、栈可读、生态完整 |
| 高并发 I/O 转发（网关、代理） | WebFlux + Reactor | 线程数固定，连接数不设上限 |
| SSE / WebSocket / token 流 | Reactor | 分块、取消、背压都是内建能力 |
| 多下游扇出聚合（`zip` + 超时 + 降级） | Reactor | 声明式编排，比手写 `StructuredTaskScope` 省事 |
| 生产快于消费的实时数据 | Reactor | 背压是刚需，虚拟线程没有对应机制 |
| 已有大量阻塞依赖且无响应式驱动 | MVC + 虚拟线程 | 硬套 Reactive 只会让阻塞更难发现 |

结论不是"Reactor 过时了"，而是**它从"高并发的通用解"退回到"流式与编排的专用解"**。
判断标准可以简化成一句：**数据是"一次请求一个结果"，还是"一条持续到来的流"？** 前者交给虚拟线程，
后者交给 Reactor。

## 九、生产实践

### 1. 别让阻塞偷偷溜进来

`BlockHound` 能在运行时检测"在非阻塞线程上执行了阻塞调用"，是响应式项目的必备闸门：

```java
import reactor.blockhound.BlockHound;

public class Bootstrap {
    public static void main(String[] args) {
        // 只在测试/预发启用：有性能开销，且会对反射调用产生误报
        BlockHound.install();
        // 启动应用...
    }
}
```

依赖：`io.projectreactor.tools:blockhound`（测试 scope）。

### 2. 线程池参数要显式

默认值对中等流量够用，对高流量不够：`boundedElastic` 默认 10 × 核数、队列 10 万。
真正做批处理或大量阻塞桥接时，用 `reactor.schedulers.defaultBoundedElasticSize`、
`reactor.schedulers.defaultBoundedElasticQueueSize` 显式设定，并监控队列长度。

### 3. 可观测性

- **指标**：引入 `reactor-core-micrometer`，配合 Micrometer 观察 `reactor.subscribed`、`reactor.flow.duration`
  等指标，能直接看到"哪条流在堵"。
- **日志**：`Context` 里放 traceId，用 `doOnEach` 写 MDC；不要用 `ThreadLocal`（线程会变）。
- **链路追踪**：Micrometer Tracing 已内建 Reactor 支持，`contextWrite` 里带上 span 即可自动透传。

```java
// Context 透传 traceId：写入端（下游）contextWrite，读取端（上游）deferContextual
import reactor.core.publisher.Mono;
import reactor.util.context.Context;

Mono<String> handled = Mono.deferContextual(ctx -> {
            String traceId = ctx.getOrDefault("traceId", "-");
            return Mono.just("trace=" + traceId);
        })
        .contextWrite(Context.of("traceId", "T-9"));
```

### 4. 常见生产事故与对策

| 事故 | 根因 | 对策 |
|------|------|------|
| CPU 打满但 QPS 很低 | 事件循环线程里混入阻塞调用 | BlockHound + 代码评审卡点 |
| 内存缓慢上涨 | `onBackpressureBuffer()` 无界缓冲 | 给容量 + 监控 `FAIL_OVERFLOW` |
| 超时配置不生效 | 上游在同线程阻塞，定时器跑不起来 | 阻塞调用一律 `subscribeOn(boundedElastic)` |
| 偶发丢消息 | `directBestEffort()` 静默丢弃 | 换 `onBackpressureBuffer()` |
| 线程数暴涨 | 每处都新建 `Schedulers` | 全局单例，禁止 `Schedulers.newXxx()` 滥用 |

## 十、什么时候不要用 Reactor

- **团队里没人能在 3 个月内熟练掌握**——响应式的调试成本是实实在在的，写错比写慢更贵。
- **链路无法端到端非阻塞**——驱动全是 JDBC/同步 SDK 时，收益为零，只剩复杂度。
- **业务是"一次请求一个结果"的 CRUD**——虚拟线程更划算。
- **需要极简可维护性的内部工具**——MVC 足够，不要为了简历上多一行而上 Reactive。

## 与相关概念的关系

- [[spring-webflux|Spring WebFlux]]：本篇的 Web 层细节在那边展开。
- [[06-code-examples|代码案例]]：本篇代码的可运行简化版。
- [[04-sink|Sink 组件]]：SSE、WebSocket 广播的实现基础。
- [[02-origin|起源与演进]]：为什么"端到端非阻塞"是这套技术栈的核心命题。
- [[microservices|微服务]]：网关与扇出编排在这类架构里的位置。

## 参考

- [Spring WebFlux 官方文档](https://docs.spring.io/spring-framework/reference/web/webflux.html)
- [Spring Cloud Gateway](https://docs.spring.io/spring-cloud-gateway/reference/)
- [Reactor Netty](https://projectreactor.io/docs/netty/release/reference/)
- [Spring AI：Streaming Chat](https://docs.spring.io/spring-ai/reference/)
