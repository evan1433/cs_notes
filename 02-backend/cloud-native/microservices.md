---
title: 微服务架构：由来、概念、优势与落地方案
description: 从单体天花板与 SOA 教训讲清微服务的由来，拆解九大特征与边界划分方法，逐条对应服务发现、容错、分布式事务、可观测性等问题的解决方案
tags:
  - microservices
  - architecture
  - cloud-native
  - distributed-system
  - spring-cloud
date: 2026-11-12
aliases:
  - microservices
---

# 微服务架构：由来、概念、优势与落地方案

## 概述

微服务不是一种"更先进的架构"，而是一笔**用分布式复杂性换组织扩展性**的交易：
把一个大进程拆成一组能独立部署的小服务，让多个团队可以并行交付而不互相阻塞。
代价是原本的**方法调用变成了网络调用**——超时、重试、数据一致性、链路追踪这些问题全部浮出水面。

所以理解微服务的关键不是记住九个特征，而是搞清楚：**它换来了什么、代价是什么、代价怎么付**。
本文按"由来 → 概念 → 优势 → 要解决的问题 → 对应方案 → 演进路径"的顺序展开，
组件级用法（Eureka、OpenFeign、Resilience4j 等）见 [[spring-cloud|Spring Cloud]]。

## 前置知识

- [[cloud-concepts|云计算基础]]：云原生四支柱与容器编排的基本概念
- [[http-protocol|HTTP 协议]]：REST 风格服务契约的基础
- [[kafka|Kafka]] 或 [[message-queue|消息队列]]：异步通信与最终一致性的载体
- 领域驱动设计的基本概念（限界上下文、聚合根），否则第 2.3 节会读得吃力

## 一、由来：微服务是被逼出来的，不是被设计出来的

### 1.1 单体的天花板不在代码，在协作

单体架构本身没有问题——它部署简单、调试直观、事务天然一致。
真正的瓶颈出现在**团队规模**超过一定阈值之后：

| 单体的瓶颈 | 表现 | 本质 |
|-----------|------|------|
| 构建与发布耦合 | 改一个文案要全量回归、全量发布 | 发布单元太大 |
| 扩容不经济 | 只有订单模块吃 CPU，也要复制整个应用 | 伸缩单元太大 |
| 故障不隔离 | 一个内存泄漏拖垮整个进程 | 故障域太大 |
| 技术栈锁死 | 想给搜索模块换 ES 客户端，被全局依赖卡住 | 依赖边界不清 |
| 组织冲突 | 几十人改同一个仓库，合并冲突天天有 | 代码所有权不清 |

前四条是技术问题，第五条是**组织问题**——而组织问题往往才是主因。
康威定律说"系统架构会映射组织沟通结构"，单体的问题在于：它强制所有团队共享同一个交付节奏。

### 1.2 SOA 的教训：治理做过头，反而拖死交付

SOA 的出发点是对的——把公共能力（用户、鉴权、消息）抽成共享服务，避免重复建设。
但落地方式出了偏差：**企业服务总线（ESB）**把路由、协议转换、数据映射、编排全部集中到一个中间件里。

结果变成：任何一次服务变更都要牵动 ESB 配置，ESB 成了性能瓶颈和单点故障；
SOAP/WSDL 的协议栈笨重，开发调试成本极高；服务粒度偏粗，一个"用户服务"背后是几十张表。
**服务化了，但没有换来交付速度**——这是微服务刻意要避开的坑。

### 1.3 互联网公司的实践走在了定义前面

- 2002 年，Amazon 推行"所有团队必须通过 API 暴露能力、不允许后门直连数据库"的内部规定，
  把组织强制切分成可独立演进的服务单元（后来演化为 AWS 的形态）
- 2009 年后，Netflix 为应对单库单体的扩容瓶颈，把系统迁到 AWS 并大规模服务化，
  顺手开源了 Eureka、Hystrix、Zuul 等一整套治理组件
- 2011 年，威尼斯的一个架构研讨会上开始用 "microservices" 描述这类做法
- 2014 年，Martin Fowler 与 James Lewis 发表《Microservices》，行业才有了公认定义

### 1.4 一个关键判断

微服务的成熟不是架构思想的胜利，而是**基础设施成熟**的结果：
容器（2013）、编排（2014）、CI/CD、云上按量计费，让"几十个服务各自部署几十次/天"变得可行。
**没有自动化交付能力的团队上微服务，等于把单体的耦合换成分步发布的痛苦。**

## 二、概念：微服务到底在说什么

### 2.1 定义

把单一应用拆分为一组**小服务**，每个服务：
运行在独立进程中、围绕**业务能力**构建、通过**轻量级机制**（HTTP/REST、gRPC、消息）通信、
可**独立部署**、拥有**独立的数据存储**、可由**小团队全生命周期负责**。

定义里最容易忽略的是"独立数据存储"。**共享数据库的微服务不是微服务**，只是被拆散的分布式单体。

### 2.2 九个特征（Fowler / Lewis）

| 特征 | 含义 | 对立面（单体的做法） |
|------|------|---------------------|
| 通过服务组件化 | 库是进程内组件，服务是可独立部署组件 | 一个 jar 里所有模块 |
| 围绕业务能力组织 | 团队按"订单""库存"划分，不是按"前端组""DBA 组" | 按技术职能分层 |
| 做产品不是做项目 | 团队对服务全生命周期负责 | 交付完就转交运维 |
| 智能端点、哑管道 | 逻辑在服务里，通道只做传输（REST/MQ） | ESB 里塞满路由与转换逻辑 |
| 去中心化治理 | 每个服务可选合适的技术栈 | 全公司统一技术栈 |
| 去中心化数据管理 | 每服务独立库，跨服务一致性靠事件 | 单一共享库 + 跨表 JOIN |
| 基础设施自动化 | 部署、扩缩、测试必须自动化 | 手工部署脚本 |
| 为失败而设计 | 默认下游会挂，超时/熔断/降级是标配 | 假设调用一定成功 |
| 演进式设计 | 服务可替换、可拆分、可合并 | 一旦定型难以改动 |

### 2.3 边界怎么划：这是微服务最难的一步

拆分粒度不看代码行数，看**业务边界**。可用的三个依据，按优先级从高到低：

1. **限界上下文（Bounded Context）**：同一个词在不同上下文含义不同——"商品"在商品中心是 SPU/SKU，
   在交易里是快照，在搜索里是索引文档。词义变了，边界就到了
2. **业务能力**：能被一句话完整描述、有明确输入输出的能力（下单、扣库存、发券）
3. **团队边界**：一个服务应该能被一个小团队（5–8 人）完整负责。
   如果拆出的服务需要两个团队共同修改才能发布，说明边界划错了

反过来说：**如果一个服务无法独立回答"它拥有哪些数据、暴露哪些接口、承诺什么 SLO"，
它就不是一个合格的服务单元。**

### 2.4 与单体、SOA、模块化单体的区别

| 维度 | 单体 | 模块化单体 | SOA | 微服务 |
|------|------|-----------|-----|--------|
| 部署单元 | 1 个 | 1 个 | 数个粗粒度服务 | 数十到数百个服务 |
| 数据 | 单库 | 单库，schema 隔离 | 共享库常见 | 每服务独立库 |
| 通信 | 方法调用 | 方法调用 | ESB / SOAP | REST / gRPC / MQ |
| 治理方式 | 无需治理 | 编译期约束 | 集中式（ESB） | 去中心化 + 平台化 |
| 事务 | 本地事务 | 本地事务 | 分布式事务 | 最终一致 |
| 适合团队 | 1–10 人 | 10–50 人 | 大企业集成 | 多团队并行、高增长业务 |

> 注意表格里"模块化单体"这一列：**对大多数团队来说，它是比微服务更划算的起点**。
> 保留单库与进程内调用，用模块边界 + 编译期依赖检查把耦合挡在代码层，等边界稳定后再拆服务。

### 2.5 一个服务的最小契约

服务对外只需要承诺三件事，写清楚了协作成本就降一半：

```yaml
# service-contract.yaml：契约不是文档，是要被 CI 校验的约束
service: order-service
owner: trade-team
api:
  style: rest
  versioning: uri            # /v1/orders，禁止无版本变更
  breakingChangePolicy: 只允许新增字段，删除需双版本并行一个迭代
data:
  owned: [orders, order_items, order_status_log]
  forbidden: [直接读 inventory.stock]   # 别人的数据只能通过 API 或事件获取
slo:
  availability: 99.95%
  latencyP99: 300ms
  errorBudget: 0.5%/month
dependencies: [inventory-service, payment-service]
```

## 三、优势：换来了什么，以及什么时候换不到

微服务的收益是**有前提条件**的。把"宣称的优势"和"成立前提"放在一起看才诚实：

| 优势 | 为什么成立 | 成立前提 | 常见落空情形 |
|------|-----------|----------|-------------|
| 独立部署 | 发布单元小，回归范围小 | 有 CI/CD 与自动化回归 | 手工部署，发布反而更累 |
| 独立伸缩 | 按服务粒度配副本与资源 | 有编排与弹性策略 | 所有服务平均分配资源 |
| 故障隔离 | 故障域限定在单进程 | 有熔断与降级 | 同步调用链过长，一处挂全链挂 |
| 技术异构 | 服务间只靠契约耦合 | 团队有多语言能力 | 异构带来运维成本翻倍 |
| 团队自治 | 康威定律的正向利用 | 有清晰的边界与所有权 | 边界混乱，谁都改不了 |
| 可复用组合 | 能力以 API 形式暴露 | 有契约治理与版本策略 | 复用变成"谁都能改我的库" |
| 渐进式重构 | 可单独替换某个服务 | 有绞杀者路径与流量开关 | 新旧并存永久化 |

**一句话结论**：微服务放大的是团队的工程能力。
工程能力强，收益按倍数放大；工程能力弱，问题也按倍数放大。

## 四、要解决的问题：拆开之后，每样都要自己造

这部分是微服务真正的成本清单。**每个问题都来自"方法调用变成网络调用"这一件事。**

| 问题 | 单体里怎么解决 | 微服务里变成什么 | 不解决的后果 |
|------|---------------|-----------------|-------------|
| 服务定位 | 直接 new 对象 | 实例动态变化，IP 不固定 | 硬编码地址，扩缩容即故障 |
| 调用失败 | 抛异常，同进程可捕获 | 超时、网络抖动、部分成功 | 线程池耗尽，雪崩 |
| 配置管理 | 配置文件跟着包发布 | 几十个服务几百份配置 | 改一个开关要重新发布 |
| 流量入口 | 一个 Nginx | 网关、鉴权、限流、灰度都要做 | 每个服务重复实现鉴权 |
| 数据一致性 | 本地事务 ACID | 跨服务无共享事务 | 钱扣了库存没减 |
| 跨服务查询 | SQL JOIN | 无法 JOIN | 只能在内存拼装，性能不可控 |
| 问题定位 | 单机日志一把梭 | 一个请求跨十几个进程 | 排查一个超时要翻十份日志 |
| 发布 | 停服重启 | 多服务版本并存 | 版本不兼容导致线上报错 |
| 安全 | 进程内调用免鉴权 | 内网也需要认证与加密 | 内网横向移动，一次失守全网 |
| 测试 | 一个集成测试覆盖全链 | 依赖大量下游 | 测试环境永远起不全 |
| 认知负载 | 一个代码库 | 几十个仓库与契约 | 新人三个月上不了手 |

### 4.1 服务发现：地址不能写死

单体里 `orderService.calculate()` 是编译期绑定；微服务里实例随时增减，地址是运行时信息。
需要两件事：**注册**（实例启动后上报自己）与**发现**（调用方按服务名拿到可用实例列表）。

三种实现路线，越往下越"基础设施化"：

| 路线 | 机制 | 代表 | 特点 |
|------|------|------|------|
| 客户端发现 | 客户端查注册中心，自己选实例 | Eureka + Ribbon、Nacos | 灵活，但每语言都要实现客户端 |
| 服务端发现 | 请求打到 LB/网关，由它转发 | K8s Service、云 LB | 客户端无感，策略受平台约束 |
| DNS 发现 | 服务名解析为集群 IP | K8s Headless Service | 最简单，健康检查粒度较粗 |

### 4.2 远程调用：五个必须一起设计的策略

网络调用有四种"部分失败"：超时、拒绝、慢响应、成功但响应丢失。**只做重试会把故障放大**，
必须成套设计：

| 策略 | 解决什么 | 关键参数 | 写错的后果 |
|------|----------|----------|-----------|
| 超时 | 慢下游拖死调用方线程 | 必须小于上游超时，逐层递减 | 无超时 → 线程池打满 |
| 重试 | 瞬时故障（网络抖动、实例重启） | 只重试幂等操作，退避 + 上限 | 重试风暴放大 3 倍流量 |
| 熔断 | 下游持续失败时快速失败 | 失败率阈值、半开探测 | 不熔断 → 雪崩 |
| 舱壁隔离 | 单一依赖故障不占满所有资源 | 独立线程池/信号量 | 共享池 → 一个依赖打死全部 |
| 降级 | 非核心能力降级保核心 | 兜底值、开关 | 降级返回脏数据 |

排序原则：**超时 → 幂等 → 重试 → 熔断 → 隔离 → 降级**，顺序错了策略互相打架。

### 4.3 数据一致性：微服务最贵的一课

跨服务没有共享事务，只能选"强一致"或"最终一致"。先明确一个事实：
**绝大多数业务场景不需要强一致**，需要的是"不出错 + 可对账 + 可补偿"。

| 方案 | 一致性 | 业务侵入 | 适用 | 主要代价 |
|------|--------|----------|------|----------|
| 2PC / XA | 强一致 | 低 | 同库多资源、少量关键操作 | 同步阻塞、协调者单点、性能差 |
| TCC | 强一致（业务级） | 高（写三个方法） | 资金、库存等强约束场景 | 需处理空回滚、悬挂、幂等 |
| Saga | 最终一致 | 中（写补偿） | 长流程、跨多个服务 | 无隔离性，中间态对外可见 |
| 事务性发件箱（Outbox） | 最终一致 | 低 | 事件驱动、状态扩散 | 需 CDC 或轮询，有延迟 |
| 本地消息表 / 最大努力通知 | 最终一致 | 中 | 通知类、可容忍重复 | 需对账兜底 |

**Outbox 是最值得先落地的一个**：把"改业务数据"和"写事件"放进同一个本地事务，
再由独立进程把事件投出去，从根上消除"数据改了但消息没发"的双写问题。

### 4.4 跨服务查询：不能 JOIN 怎么办

| 场景 | 方案 | 说明 |
|------|------|------|
| 实时拼装少量数据 | API 组合（BFF / 聚合服务） | 简单，但下游多时延迟叠加 |
| 高频复杂查询 | CQRS 读模型 | 事件驱动构建读库，读写分离 |
| 多条件检索 | 数据同步到 ES / 宽表 | 用 [[elasticsearch|Elasticsearch]] 承担查询 |
| 报表统计 | 数仓 / 离线聚合 | 不占在线库资源 |

**底线**：不要为了"图方便"让服务直接读别人的库。一旦发生，边界就永久失效了。

### 4.5 可观测性：一个请求散落在十几个进程

单体排错看一份日志；微服务必须靠**关联 ID 把散落的日志串起来**。
最小可用组合：Metrics（有没有问题）→ Trace（问题在哪一跳）→ Logs（那一跳发生了什么）。
实现要点：入口生成 `traceId` 并通过 HTTP header / MQ header 透传，全链路日志格式统一。

### 4.6 其他四类问题一句话概括

- **发布**：多版本并存 → 需要契约兼容策略 + 灰度/蓝绿 + 流量染色
- **安全**：内网不再是可信边界 → 零信任，网关统一鉴权 + 服务间 mTLS + 最小权限
- **测试**：测试环境起不全 → 消费者契约测试（Pact）+ 服务虚拟化
- **组织**：认知负载过高 → 平台团队承接基础设施，业务团队只管服务本身

## 五、对应的解决方案

### 5.1 一张全景分层表

| 层 | 职责 | 典型组件 |
|----|------|----------|
| 接入层 | 统一入口、鉴权、限流、灰度 | Spring Cloud Gateway、APISIX、[[nginx|Nginx]] Ingress |
| 治理层 | 注册发现、负载均衡、熔断限流 | Nacos、Resilience4j、Sentinel |
| 通信层 | 同步/异步调用、契约 | OpenFeign、gRPC、[[rocketmq|RocketMQ]]、[[kafka|Kafka]] |
| 数据层 | 每服务独立库、缓存、搜索 | MySQL、[[redis|Redis]]、[[elasticsearch|Elasticsearch]] |
| 可观测层 | 指标、追踪、日志 | Prometheus、OpenTelemetry、Loki |
| 交付层 | 构建、部署、编排 | CI/CD、[[docker|Docker]]、[[kubernetes|Kubernetes]]、[[helm|Helm]] |

组件级用法与版本兼容矩阵见 [[spring-cloud|Spring Cloud]]，本文只讲**为什么需要它、什么时候不该用它**。

### 5.2 注册中心与配置中心：可以合成一个

Nacos 同时提供服务注册与配置管理，是 Java 技术栈最常见的起点：

```yaml
# application.yml：服务名 + 注册中心 + 配置中心，三行解决"我在哪、别人怎么找我"
spring:
  application:
    name: order-service
  cloud:
    nacos:
      discovery:
        server-addr: nacos.infra.svc:8848
        namespace: prod-trade        # 用命名空间隔离环境，比改地址更可靠
      config:
        server-addr: nacos.infra.svc:8848
        file-extension: yaml
        refresh-enabled: true        # 支持 @RefreshScope 热更新，避免为改开关重启
```

**选型取舍**：已有 K8s 就优先用 K8s 原生的 Service + DNS + ConfigMap/Secret，
少一套注册中心就少一个故障点；需要跨集群、跨云、或强配置灰度能力时，再引入 Nacos/Apollo。

### 5.3 通信方式：同步还是异步

| 方式 | 适用 | 优势 | 代价 |
|------|------|------|------|
| REST/JSON | 对外 API、内部简单查询 | 生态好、调试直观 | 序列化开销、弱类型 |
| gRPC | 内部高频调用、流式 | 二进制高效、强契约（IDL） | 浏览器支持差、调试门槛高 |
| 消息（MQ） | 状态扩散、异步解耦、削峰 | 天然解耦、可缓冲、便于最终一致 | 需处理重复、顺序、积压 |

经验规则：**查询用同步，状态变更通知用异步**。一条链路里同步调用超过 3 跳，
基本说明编排逻辑该下沉到某个服务或改成事件驱动了。

### 5.4 容错落地：把五个策略写进代码

```java
// 一次调用同时具备：超时、舱壁、熔断、重试、降级
// 顺序很关键：舱壁在最外层限制并发，熔断判断是否还值得尝试，重试只在熔断闭合时生效
@Bean
public CircuitBreaker orderCircuitBreaker() {
    return CircuitBreaker.of("inventory",
        CircuitBreakerConfig.custom()
            .slidingWindowSize(20)
            .failureRateThreshold(50)        // 20 次里失败过半就打开，避免慢失败持续消耗线程
            .waitDurationInOpenState(Duration.ofSeconds(10))
            .permittedNumberOfCallsInHalfOpenState(3)   // 半开只用少量请求试探，别一开就放全量
            .build());
}

@Bean
public TimeLimiter orderTimeLimiter() {
    // 超时必须小于网关侧超时，否则调用方已放弃、这边还在占资源
    return TimeLimiter.of(Duration.ofMillis(800));
}

@Bean
public Bulkhead inventoryBulkhead() {
    // 给库存依赖单独的并发额度：库存慢了不影响支付以外的其他依赖
    return Bulkhead.of("inventoryBulkhead", BulkheadConfig.custom().maxConcurrentCalls(20).build());
}

public OrderResult createOrder(OrderCommand cmd) {
    Supplier<OrderResult> decorated = Decorators.ofSupplier(() -> inventoryClient.reserve(cmd))
        .withBulkhead(inventoryBulkhead)
        .withCircuitBreaker(orderCircuitBreaker)
        .withTimeLimiter(orderTimeLimiter, Executors.newScheduledThreadPool(4))
        .withFallback(List.of(CallNotPermittedException.class, TimeoutException.class),
            e -> OrderResult.degraded(cmd.orderId(), "库存服务暂不可用，已转人工审核"))
        .decorate();
    return decorated.get();
}
```

注意降级返回的 `degraded` 是**业务上可接受的中间态**，不是伪装成功。
降级写成"返回成功"是最危险的一类线上事故来源。

### 5.5 网关：入口只做入口该做的事

```yaml
# gateway.yml：鉴权、限流、路由在网关；业务编排不要塞进网关
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service          # lb:// 表示走注册中心做客户端负载均衡
          predicates:
            - Path=/api/v1/orders/**
          filters:
            - StripPrefix=1                # 去掉 /api 前缀，服务内部不感知外部路径
            - name: RequestRateLimiter     # 入口限流，保护下游而不是保护网关
              args:
                redis-rate-limiter.replenishRate: 200
                redis-rate-limiter.burstCapacity: 400
      default-filters:
        - name: CircuitBreaker             # 网关级熔断，防止单服务拖垮入口
          args: { name: gatewayCb, fallbackUri: forward:/fallback }
```

网关职责边界：**路由、鉴权、限流、协议转换、日志埋点**。
"下单要调用库存+支付+发券"这类编排属于业务，放在 BFF 或专门的编排服务里。

### 5.6 分布式事务：Outbox + 幂等消费的完整闭环

```sql
-- 1) 业务变更与事件在同一个本地事务里落库，杜绝双写不一致
BEGIN;
UPDATE inventory SET stock = stock - 1 WHERE sku_id = 'SKU-1001' AND stock >= 1;
INSERT INTO outbox_event (id, aggregate_id, event_type, payload, status)
VALUES (UUID(), 'SKU-1001', 'StockReserved', '{"orderId":"O-778","qty":1}', 'PENDING');
COMMIT;

-- 2) 独立投递进程扫描 PENDING 并发送（也可用 Debezium 读 binlog 做 CDC，延迟更低）
-- SELECT * FROM outbox_event WHERE status = 'PENDING' ORDER BY id LIMIT 100;
```

消费端必须幂等，否则重投就重复扣款：

```sql
-- 用唯一索引做去重，重复消息第二次插不进去，直接视为已处理
CREATE TABLE consumed_event (
  event_id   VARCHAR(36) PRIMARY KEY,   -- 主键冲突即天然幂等
  consumer   VARCHAR(64) NOT NULL,
  consumed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

```java
// 消费逻辑：先占坑再处理，占不到说明已消费过
@Transactional
public void onStockReserved(StockReservedEvent event) {
    try {
        dedupRepo.insert(event.eventId(), "order-service");   // 唯一索引挡重复
    } catch (DuplicateKeyException alreadyConsumed) {
        log.info("skip duplicated event {}", event.eventId()); // 重投/重平衡导致的重复，正常现象
        return;
    }
    orderRepository.markStockReserved(event.orderId());
}
```

完整的一致性方案还要配**对账任务**：定时比对两侧业务状态，把长期不一致的单据捞出来人工或自动修复。
**最终一致不是"最终会一致"，而是"有机制保证最终会一致"。**

### 5.7 可观测性：先统一 ID，再谈工具

```java
// 入口生成 traceId，出口透传；这是全链路可观测的地基，比选哪个 APM 更重要
@Component
public class TraceIdFilter extends OncePerRequestFilter {
    private static final String HEADER = "X-Trace-Id";

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse resp,
                                    FilterChain chain) throws ServletException, IOException {
        String traceId = Optional.ofNullable(req.getHeader(HEADER))
            .orElse(UUID.randomUUID().toString().replace("-", ""));
        MDC.put("traceId", traceId);            // 日志格式里输出 %X{traceId}，日志与链路才能对上
        resp.setHeader(HEADER, traceId);        // 回传给调用方，便于跨团队定位
        try {
            chain.doFilter(req, resp);
        } finally {
            MDC.remove("traceId");               // 线程池复用，必须清理否则串号
        }
    }
}
```

### 5.8 部署与服务网格：什么时候该上 Mesh

| 阶段 | 治理位置 | 判断信号 |
|------|----------|----------|
| 早期 | 治理逻辑在业务代码（SDK） | 单一语言栈、服务数 < 30 |
| 中期 | 治理下沉到网关 + 平台（K8s） | 服务数增长，SDK 版本升级成本高 |
| 后期 | 服务网格（Sidecar） | 多语言栈、需要统一 mTLS 与灰度、跨集群 |

服务网格的代价要算清楚：每个 Pod 多一个 sidecar（内存 + 延迟），多一层控制面要运维，
排错链路变长。**"多语言 + 强合规"两个条件不同时成立，就别上 Mesh。**

### 5.9 技术栈选型对照

| 方案 | 适合 | 优势 | 局限 |
|------|------|------|------|
| Spring Cloud Alibaba | Java 单栈团队 | 组件齐全、中文资料多、上手快 | 生态绑定 Java，SDK 需随版本升级 |
| Spring Cloud + K8s 原生 | 已有 K8s | 少维护一套注册中心，资源利用率高 | 配置灰度、跨集群能力偏弱 |
| Istio / Linkerd | 多语言、强治理要求 | 治理与业务解耦，能力统一 | 运维复杂，资源开销明显 |
| Serverless（FaaS） | 事件型、低频任务 | 免运维、按调用计费 | 冷启动、长任务不适用 |

## 六、演进路径：不要从零开始微服务

### 6.1 三步走

| 阶段 | 目标 | 关键动作 | 退出条件 |
|------|------|----------|----------|
| 一、模块化单体 | 先把边界理清 | 按限界上下文分模块，禁止跨模块直连数据库 | 模块间依赖无环，可独立测试 |
| 二、试点拆分 | 验证交付链路 | 挑一个**边缘、低风险**的服务先拆（如通知、搜索） | 能独立发布、独立回滚 |
| 三、平台化 | 让拆分规模化 | CI/CD、注册配置、可观测、灰度四件套就位 | 新服务一天内可上线 |
| 四、持续绞杀 | 按价值逐步迁移 | 用绞杀者模式把单体能力一格格搬走 | 单体退化为薄壳或下线 |

### 6.2 绞杀者模式（Strangler Fig）

不停机迁移的标准做法：在旧系统外面架一层**门面/网关**，把需要迁移的入口逐个切到新服务，
验证稳定后再扩大流量比例，最终旧实现自然"饿死"。

```text
第一步：请求 → 门面 → 旧单体（全部流量）
第二步：请求 → 门面 → 新服务（5%） + 旧单体（95%）
第三步：请求 → 门面 → 新服务（100%），旧代码保留只读
第四步：删除旧路径，门面合并进网关
```

关键在于**门面层要能按维度切流**（用户 ID 哈希、租户、接口路径），否则无法灰度也无法快速回退。

### 6.3 拆分的反模式

| 反模式 | 表现 | 为什么错 |
|--------|------|----------|
| 按技术层拆 | 一个 controller 服务、一个 dao 服务 | 每次业务变更都要改所有服务，耦合更重 |
| 按数据库表拆 | 每张表一个服务 | 表结构不等于业务边界，跨表事务爆炸 |
| 分布式单体 | 服务间强同步调用、共享库、必须一起发布 | 拿到了分布式的成本，没拿到独立性 |
| 纳米服务 | 一个服务只有一个接口 | 治理成本 > 业务价值 |
| 过早抽象共享库 | 把业务逻辑放进 common 包 | 共享库升级牵动所有服务，变成隐性单体 |
| 拆分不改组织 | 服务拆了，团队还是一个大组 | 康威定律反向作用，边界必然退化 |

## 七、常见误区

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| 微服务性能更好 | 多一跳网络调用，延迟一定高于方法调用 | 只在需要独立伸缩/隔离处拆分 |
| 服务越细越"微"越好 | 治理成本随服务数线性上升 | 以团队可维护粒度为下限 |
| 拆完就自动敏捷 | 没有 CI/CD，发布成本反而翻倍 | 先把交付流水线做好再拆 |
| 必须用 K8s / 必须上 Mesh | 小规模用注册中心 + 容器足够 | 按服务数与语言栈决定 |
| 跨服务必须强一致 | 强一致代价高，多数场景最终一致足够 | 用 Outbox + 幂等 + 对账 |
| 有网关就安全了 | 内网横向移动、越权访问仍在 | 零信任，服务间也要鉴权 |
| 链路追踪能替代日志 | Trace 看"哪一跳慢"，Log 看"为什么慢" | 两者靠 traceId 关联，缺一不可 |
| 微服务等于 SOA 换皮 | SOA 集中治理（ESB），微服务去中心化 + 平台化 | 别把 ESB 逻辑搬进网关 |
| 共享数据库省事 | 边界立刻失效，等于分布式单体 | 每服务独立库，跨库只走 API/事件 |

## 八、与相关概念的关系

- 与 [[cloud-concepts|云计算基础]]：微服务是云原生四支柱之一，云提供资源池与弹性，微服务提供应用形态。
- 与 [[spring-cloud|Spring Cloud]]：解决"组件怎么用"；本文解决"为什么这么设计、什么时候不该用"。
- 与 [[kubernetes|Kubernetes]]：编排层承接部署、伸缩、自愈，让"数十个服务独立发布"的成本可承受。
- 与 [[docker|Docker]]：容器是微服务的标准交付物，保证"开发环境与生产环境一致"。
- 与 [[kafka|Kafka]] 等消息中间件：异步通信与最终一致性的基础设施，Outbox 方案的投递通道。
- 与 [[../../06-AI/ai-native-arch|AI 原生架构]]：AI 原生改变的是服务内部逻辑与算力结构，分布式治理问题依然复用本文方案。
- 与 SOA 的区别：SOA 靠 ESB 集中治理，微服务靠平台化与契约治理，强调去中心化。

## 参考

- [Martin Fowler & James Lewis: Microservices](https://martinfowler.com/articles/microservices.html)
- [Microservices.io: Pattern Catalog](https://microservices.io/patterns/index.html)
- [Chris Richardson: Pattern: Saga](https://microservices.io/patterns/data/saga.html)
- [Chris Richardson: Pattern: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- [[spring-cloud|Spring Cloud 组件手册]]、[[cloud-native/index|云原生目录]]
