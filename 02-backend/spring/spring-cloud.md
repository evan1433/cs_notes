---
title: Spring Cloud
description: Spring Cloud 微服务治理体系：Release Train 版本管理、Eureka 注册发现、LoadBalancer 负载均衡、Resilience4j 熔断降级、OpenFeign 声明式调用、Gateway 网关与 Config 配置中心，含 Netflix 组件退役后的现代替代方案
tags:
  - java
  - spring
  - spring-cloud
  - microservices
  - distributed-system
date: 2026-10-30
aliases:
  - spring-cloud
  - 微服务
---

# Spring Cloud

> 原文参考：[一篇文章搞懂 Spring Cloud 是什么](https://www.cnblogs.com/mrhelloworld/p/springcloud.html)

Spring Cloud 解决的是一个很具体的问题：把分布式系统里**反复要写一遍的样板代码**（配置集中管理、服务注册发现、路由、熔断、负载均衡、链路追踪）封装成一组可以"引依赖即用"的 Starter，让每个微服务只关心自己的业务代码。它不是另一个框架，而是架在 Spring Boot 自动装配之上的一整套**分布式治理工具箱**。

一句话概括它的价值：**版本由 BOM 统一管理，能力由 Starter 提供，行为由 `application.yml` 调节**。

> **版本提示**：本文档事实核对时间为 2026 年 10 月。截至该时间，spring.io 标注 Spring Cloud 最新可用版本为 **2025.1.4（Oakwood）**，对应的 Spring Cloud Gateway 为 5.0.3、OpenFeign 为 5.0.4、Netflix 为 5.0.3。版本号变化快，落地前请以 [spring.io/projects/spring-cloud](https://spring.io/projects/spring-cloud) 的版本兼容表为准。

## 1. 版本管理：Release Train 与 BOM

Spring Cloud **不用普通版本号**，而是用"发布列车（Release Train）"，命名是伦敦地铁站名的字母表顺序（Hoxton → Ilford → Jubilee → Kilburn → Leyton → Moorgate → Northfields → Oakwood）。每个包含一个代号，下面通过 SR（Service Release，如 2025.1.2）滚动修 bug。

**列车与 Spring Boot 的对应关系是硬性约束，配错就启动失败：**

| Release Train | 代号 | 兼容 Spring Boot | 状态 |
|---------------|------|------------------|------|
| 2025.1.x | Oakwood | 4.0.x；4.1.x（自 2025.1.2 起） | 当前主线 |
| 2025.0.x | Northfields | 3.5.x | 已 EOL |
| 2024.0.x | Moorgate | 3.4.x | 已 EOL |
| 2023.0.x | Leyton | 3.2.x、3.3.x（自 2023.0.2 起） | 已 EOL |
| 2022.0.x | Kilburn | 3.0.x、3.1.x（自 2022.0.3 起） | 已 EOL |
| 2021.0.x | Jubilee | 2.6.x、2.7.x（自 2021.0.3 起） | 已 EOL |
| 2020.0.x | Ilford | 2.4.x、2.5.x（自 2020.0.3 起） | 已 EOL |

> 除 2025.1.x 之外，表中其余列车均已进入 end-of-life，不再有任何补丁。**新项目请直接用 2025.1.x + Spring Boot 4.x**。

引入方式是导入 BOM，之后所有 Starter **不用再写版本号**：

```xml
<properties>
    <spring-cloud.version>2025.1.2</spring-cloud.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.0'
    id 'io.spring.dependency-management' version '1.1.7'
}

ext {
    set('springCloudVersion', "2025.1.2")
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.cloud:spring-cloud-dependencies:${springCloudVersion}"
    }
}
```

> 建议只导入 `spring-cloud-dependencies` 这一个 BOM：它是纯版本管理 POM，不夹带任何依赖传递和插件声明，与 Spring Boot parent POM 可以共存。

## 2. 微服务要解决的三个层次

原文留下的三条主线，对应到具体组件：

| 层次 | 要解决的问题 | Spring Cloud 组件 |
|------|-------------|-------------------|
| 微服务概念 | 单体拆分成独立部署单元后，服务边界、进程间通信怎么定 | OpenFeign / RestClient / Spring Cloud Stream |
| 服务发现 | 实例 IP 动态漂移，调用方怎么知道对方在哪 | Eureka / Consul / Zookeeper / Kubernetes Discovery |
| 服务治理 | 雪崩、配置漂移、入口统一鉴权、灰度路由谁来兜底 | Circuit Breaker / Config / Gateway / LoadBalancer |

这三层不是并列的功能清单，而是**依赖关系**：没有服务发现，负载均衡就是空的；没有熔断，微服务之间的级联故障会把整条链路拖垮。

## 3. 服务发现：Eureka

### 3.1 Eureka Server

Eureka 是 Spring Cloud Netflix 目前**唯一还在维护的模块**（Hystrix、Ribbon、Zuul 均已移除，见第 5、4 节）。

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-server</artifactId>
</dependency>
```

```java
@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
```

```yaml
server:
  port: 8761

eureka:
  instance:
    hostname: localhost
  client:
    # 单机 Server 不要注册到自己，也不要拉取注册表
    register-with-eureka: false
    fetch-registry: false
    service-url:
      defaultZone: http://${eureka.instance.hostname}:${server.port}/eureka/
```

### 3.2 Eureka Client

只要在 classpath 上有 `spring-cloud-starter-netflix-eureka-client`，任何 Spring Boot 应用都会默认去 `http://localhost:8761`（即 `eureka.client.serviceUrl.defaultZone` 的默认值）注册自己——不需要任何显式注解。

```java
@SpringBootApplication
@RestController
public class Application {

    @RequestMapping("/")
    public String home() {
        return "Hello World";
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

```yaml
spring:
  application:
    name: order-service   # 这个名字就是后文 lb:// 要用的服务名

eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/
  instance:
    prefer-ip-address: true   # 容器内跑时避免 hostname 不可解析
```

### 3.3 注册中心选型对比

| 注册中心 | Spring Cloud 集成 | CAP 取向 | 适用环境 |
|----------|------------------|----------|----------|
| Eureka | Spring Cloud Netflix（官方） | AP，可用性优先 | Java 单体云 / 虚拟机部署 |
| Consul | Spring Cloud Consul（官方） | CP | 已用 HashiCorp 栈，需要健康检查与 KV 配置 |
| Zookeeper | Spring Cloud Zookeeper（官方） | CP | 已有 ZK 集群的存量系统 |
| Kubernetes Discovery | Spring Cloud Kubernetes（官方） | 依赖 etcd | 服务真的跑在 K8s 上，避免重复维护一套注册表 |

## 4. 客户端负载均衡：Ribbon → Spring Cloud LoadBalancer

### Ribbon 负载均衡

> **Ribbon 已进入维护停止状态，2019 年后不再有新功能**。Ribbon 的核心能力由 `spring-cloud-starter-loadbalancer` 接手，**不要用 `spring-cloud-starter-netflix-ribbon` 开新项目**。

| 对比项 | Netflix Ribbon（已淘汰） | Spring Cloud LoadBalancer（现行） |
|--------|--------------------------|----------------------------------|
| Starter | `spring-cloud-starter-netflix-ribbon` | `spring-cloud-starter-loadbalancer` |
| 编程模型 | `IRule` 接口实现 | `ReactorLoadBalancer<ServiceInstance>` + `ServiceInstanceListSupplier` |
| 响应式 | 阻塞 | 原生响应式，同时兼容阻塞调用 |
| 配置前缀 | `<service>.ribbon.*` | `spring.cloud.loadbalancer.*` |

### LoadBalancer 用法

```java
@Configuration
public class ClientConfig {

    // 只加一个注解，就把"服务名"翻译成真实地址
    @Bean
    @LoadBalanced
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder.build();
    }

    @Bean
    @LoadBalanced
    public WebClient.Builder loadBalancedWebClientBuilder() {
        return WebClient.builder();
    }
}
```

```java
@Service
public class InventoryClient {

    private final RestTemplate restTemplate;

    public InventoryClient(@LoadBalanced RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public Stock query(String sku) {
        // 直接写服务名，不再写死 host:port
        return restTemplate.getForObject(
                "http://inventory-service/stock/" + sku, Stock.class);
    }
}
```

> Spring Framework 7 / Boot 4 时代更推荐用 `RestClient` 替代 `RestTemplate`；新版 LoadBalancer 也支持对 `RestClient.Builder` 加 `@LoadBalanced`，具体可用性请以所用版本的 `spring-cloud-loadbalancer` 参考文档为准。

## 5. 熔断降级：Hystrix → Spring Cloud Circuit Breaker

### Hystrix 熔断器

> **Hystrix 已于 2021 年正式退役，并从 Spring Cloud Netflix 中移除**，下面这段是原文保留的历史写法，**请勿在新项目中使用**。

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-hystrix</artifactId>
</dependency>
```

`@EnableCircuitBreaker`（该注解及整套 Hystrix Dashboard / Turbine 生态均已停止维护）。

### 现代替代：Spring Cloud Circuit Breaker + Resilience4j

官方抽象层 `spring-cloud-starter-circuitbreaker-*`，现有两种实现：

| 实现 | Starter | 适用场景 |
|------|---------|----------|
| Resilience4j | `spring-cloud-starter-circuitbreaker-resilience4j` | 阻塞式调用（`RestTemplate` / `RestClient`） |
| Reactive Resilience4j | `spring-cloud-starter-circuitbreaker-reactor-resilience4j` | 响应式调用（`WebClient`） |
| Spring Retry | `spring-cloud-starter-circuitbreaker-spring-retry` | 只需要简单重试，不需要完整熔断状态机 |

核心 API 是 `CircuitBreakerFactory`（响应式版本为 `ReactiveCircuitBreakerFactory`），classpath 上有 starter 就自动注入对应实现：

```java
@Service
public class InventoryService {

    private final RestTemplate rest;
    private final CircuitBreakerFactory cbFactory;

    public InventoryService(RestTemplate rest, CircuitBreakerFactory cbFactory) {
        this.rest = rest;
        this.cbFactory = cbFactory;
    }

    public String slow() {
        return cbFactory.create("slow").run(
                // Supplier：被熔断器包裹的业务调用
                () -> rest.getForObject("/slow", String.class),
                // Function：熔断触发后的降级逻辑，入参是导致失败的 Throwable
                throwable -> "fallback");
    }
}
```

```java
// 响应式版本入口是 ReactiveCircuitBreakerFactory
public Mono<String> slow() {
    return webClient.get()
            .uri("/slow")
            .retrieve()
            .bodyToMono(String.class)
            .transform(it -> cbFactory.create("slow")
                    .run(it, throwable -> Mono.just("fallback")));
}
```

```yaml
resilience4j.circuitbreaker:
  instances:
    slow:
      slidingWindowSize: 20
      failureRateThreshold: 50     # 失败率达到 50% 后跳闸
      waitDurationInOpenState: 10s # 断开状态持续多久后进入半开探测
      permittedNumberOfCallsInHalfOpenState: 3
```

> Resilience4j 的 Spring Boot 属性名随版本推进有过变动（早期在 `resilience4j.circuitbreaker.instances.*` 下也见过 camelCase 写法），升级时建议先跑一遍配置迁移检查，或直接对照所用版本的参考文档确认字段名。

## 6. OpenFeign 声明式调用

OpenFeign 的思路很简单：写一个带 Spring MVC 注解的接口，框架替你生成 HTTP 调用实现类——**从此不再手写 `RestTemplate`**。当前版本为 5.0.4。

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
```

```java
@SpringBootApplication
@EnableFeignClients
public class WebApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebApplication.class, args);
    }

    @FeignClient("name")
    static interface NameService {
        @RequestMapping("/")
        public String getName();
    }
}
```

实际项目里通常加上 `path`、降级工厂和超时配置：

```java
// name/value 是注册中心里的服务名；path 是该服务的统一前缀
@FeignClient(name = "inventory-service",
             path = "/stock",
             fallbackFactory = InventoryClientFallbackFactory.class)
public interface InventoryClient {

    @GetMapping("/{sku}")
    StockDTO getStock(@PathVariable("sku") String sku);

    @PostMapping("/deduct")
    void deduct(@RequestBody DeductRequest request);
}
```

```java
@Component
public class InventoryClientFallbackFactory
        implements FallbackFactory<InventoryClient> {

    @Override
    public InventoryClient create(Throwable cause) {
        // 降级时能拿到真实异常，便于区分"超时"和"404"
        return new InventoryClient() {
            @Override
            public StockDTO getStock(String sku) {
                return StockDTO.unknown(sku);
            }

            @Override
            public void deduct(DeductRequest request) {
                // 记录待补偿流水，避免强依赖串味到主链路
                log.warn("deduct fallback, request={}, cause={}", request, cause.toString());
            }
        };
    }
}
```

```yaml
spring:
  cloud:
    openfeign:
      circuitbreaker:
        enabled: true        # 打开后才走 Spring Cloud Circuit Breaker 降级
      client:
        config:
          default:
            connectTimeout: 3000
            readTimeout: 10000
```

> Feign 的默认超时策略比较保守，生产环境**必须显式配置超时并配 fallback**，否则一次慢依赖会沿着调用链一路反压到网关。

## 7. Spring Cloud Gateway 网关

网关承担统一入口职责：路由转发、鉴权、限流、灰度、日志。**Zuul 1.x 已被官方移除**，Spring Cloud Gateway 是现行唯一官方实现。

### 7.1 核心模型：predicate → filters → uri

任何一条路由，无论是 YAML 还是 Java DSL，本质都是三件事：

```text
谓词（是否匹配） → 过滤器（请求/响应加工） → 目标地址（转发到哪）
   path/method      rewritePath/rateLimit       http://host:port 或 lb://service-name
```

同一条路由上的多个谓词是 **AND** 关系，必须全部满足。

### 7.2 两个技术栈：WebFlux vs Web MVC

**这是升级到 Spring Cloud Gateway 5.x 最容易踩的坑。** 网关被拆成了两个互相独立的构件，一个应用只能选一个：

| 项 | Server WebFlux | Server Web MVC |
|----|----------------|----------------|
| 运行时 | Netty，事件循环 | Tomcat（可开虚拟线程），每请求一线程 |
| Starter | `spring-cloud-starter-gateway-server-webflux` | `spring-cloud-starter-gateway-server-webmvc` |
| 配置前缀 | `spring.cloud.gateway.server.webflux.*` | `spring.cloud.gateway.server.webmvc.*` |
| 路由 DSL | `RouteLocator`（`RouteLocatorBuilder`） | `RouterFunction`（`GatewayRouterFunctions`） |
| 限流 | 内置 `RequestRateLimiter`（Redis Lua 令牌桶） | Bucket4j `Bucket4jFilterFunctions.rateLimit` |

**旧名称已全部废弃**（使用会打 warning 日志）：

| 废弃 artifact | 新 artifact |
|---------------|-------------|
| `spring-cloud-starter-gateway` | `spring-cloud-starter-gateway-server-webflux` |
| `spring-cloud-starter-gateway-mvc` | `spring-cloud-starter-gateway-server-webmvc` |

| 废弃配置前缀 | 新配置前缀 |
|--------------|------------|
| `spring.cloud.gateway.*` | `spring.cloud.gateway.server.webflux.*` |
| `spring.cloud.gateway.mvc.*` | `spring.cloud.gateway.server.webmvc.*` |

> 把旧教程里的 `spring.cloud.gateway.routes:` 复制进 Spring Boot 4 项目，**配置不会报错，但也不会生效**——前缀已经不认识了。这是"路由配了没反应"最常见的成因。

### 7.3 WebFlux 版：Java DSL

```java
@SpringBootApplication
public class DemoGatewayApplication {

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                .route("path_route", r -> r.path("/get")
                        .uri("https://httpbin.org"))
                .route("host_route", r -> r.host("*.myhost.org")
                        .uri("https://httpbin.org"))
                .route("rewrite_route", r -> r.host("*.rewrite.org")
                        .filters(f -> f.rewritePath("/foo/(?<segment>.*)", "/${segment}"))
                        .uri("https://httpbin.org"))
                .route("circuit_breaker_route", r -> r.host("*.circuitbreaker.org")
                        .filters(f -> f.circuitBreaker(c -> c.setName("slowcmd")))
                        .uri("https://httpbin.org"))
                .route("limit_route", r -> r
                        .host("*.limited.org").and().path("/anything/**")
                        .filters(f -> f.requestRateLimiter(c -> c.setRateLimiter(redisRateLimiter())))
                        .uri("https://httpbin.org"))
                .build();
    }
}
```

### 7.4 Web MVC 版：函数式路由

静态导入的三个入口分别是 `GatewayRouterFunctions.route`、前置过滤 `BeforeFilterFunctions`、谓词 `GatewayRequestPredicates`：

```java
import static org.springframework.cloud.gateway.server.mvc.handler.GatewayRouterFunctions.route;
import static org.springframework.cloud.gateway.server.mvc.filter.BeforeFilterFunctions.*;
import static org.springframework.cloud.gateway.server.mvc.predicate.GatewayRequestPredicates.*;

@SpringBootApplication
public class DemoGatewayApplication {

    @Bean
    public RouterFunction customRoutes() {
        return route("path_route")
                .GET("/get", http())
                .before(uri("https://httpbin.org"))
                .build()
            .and(route("circuitbreaker_route")
                .route(host("*.circuitbreaker.org"), http())
                .before(uri("https://httpbin.org"))
                .filter(circuitBreaker("slowcmd"))
                .build())
            .and(route("limit_route")
                .route(host("*.limited.org").and(path("/anything/**")), http())
                .before(uri("https://httpbin.org"))
                .filter(rateLimit(c -> c.setCapacity(10)
                        .setPeriod(Duration.ofSeconds(1))
                        .setKeyResolver(request -> request.headers().firstHeader("X-TokenId"))))
                .build());
    }
}
```

### 7.5 YAML 配置（新前缀）

```yaml
spring:
  cloud:
    gateway:
      server:
        webflux:
          # 2025.0.0 起 X-Forwarded-* 默认不生效，必须显式声明可信代理
          trusted-proxies: 10\.0\.0\..*
          routes:
            - id: order-service
              # lb:// 走 LoadBalancer，服务名来自注册中心
              uri: lb://order-service
              predicates:
                - Path=/api/order/**
              filters:
                - StripPrefix=1
                - name: RequestRateLimiter
                  args:
                    redis-rate-limiter.replenishRate: 100
                    redis-rate-limiter.burstCapacity: 200
```

> `X-Forwarded-*`、`Forwarded` 头的默认行为在新版本中改为**不启用**，需要时用 `trusted-proxies`（一个表示可信代理的正则）打开，否则拿到的是代理服务器的真实 IP。

## 8. 配置中心：Spring Cloud Config

Server 端把配置托管在 Git 仓库，Client 端启动时拉取。微服务多了以后，"改一个配置要重新打包所有服务"这件事才算彻底解决。

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-config-server</artifactId>
</dependency>
```

```java
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
```

```yaml
server:
  port: 8888

spring:
  cloud:
    config:
      server:
        git:
          uri: https://github.com/your-org/your-config-repo
          search-paths: '{application}'   # 按应用名找目录
```

Client 端不再需要 `bootstrap.yml`（Spring Boot 2.4 起 `bootstrap` 上下文默认关闭），用 `spring.config.import`：

```yaml
spring:
  application:
    name: order-service
  config:
    # optional: 表示配置中心不可达也不阻断启动
    import: optional:configserver:http://localhost:8888
```

配置变更后让客户端感知，靠的是 `spring-cloud-bus` 广播刷新事件，或者用 actuator 端点手动刷新：

```bash
# 手动触发单个实例的配置刷新
curl -X POST http://localhost:8080/actuator/refresh
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: refresh,health,info
```

## 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 启动时报 `NoSuchMethodError` / 自动配置不生效 | Spring Cloud 版本与 Spring Boot 版本不匹配 | 按第 1 节表格对齐版本，只导入 `spring-cloud-dependencies` BOM |
| Feign 调用报 `UnknownHostException: order-service` | 没引入负载均衡器，或没加 `@LoadBalanced` | 加 `spring-cloud-starter-loadbalancer`；确认该服务已在注册中心 |
| Gateway 路由配了但 404 | 用了旧前缀 `spring.cloud.gateway.routes` | 改成 `spring.cloud.gateway.server.webflux.routes`（MVC 版用 `...server.webmvc.routes`） |
| Gateway 日志提示 artifact deprecated | 还在用 `spring-cloud-starter-gateway` / `-gateway-mvc` | 换成 `-gateway-server-webflux` / `-gateway-server-webmvc` |
| 网关后拿到的是 Nginx/LB 的 IP，不是客户端 IP | 新版 `X-Forwarded-*` 默认关闭 | 配 `spring.cloud.gateway.server.webflux.trusted-proxies`，值为可信代理的正则 |
| 服务上线后调用方隔很久才发现新实例 | Eureka 多级缓存 + client 拉取间隔叠加，最长约 30s+ | 调小 `eureka.client.registry-fetch-interval-seconds`；日常环境可关 read-only cache |
| 配置中心改了，客户端没生效 | 没触发 refresh，或用了已废弃的 `bootstrap.yml` | 改用 `spring.config.import`，调用 `/actuator/refresh` 或接 `spring-cloud-bus` |
| 熔断始终不跳闸 | 未显式配置 Resilience4j 实例，或 Feign 未开 circuitbreaker | 配 `resilience4j.circuitbreaker.instances.<name>`，设 `spring.cloud.openfeign.circuitbreaker.enabled=true` |
| 项目里引用了 Hystrix/Ribbon 教程代码，依赖拉不下来 | 相关模块已从 Spring Cloud Netflix 移除 | 迁移到第 4、5 节的 LoadBalancer 与 Circuit Breaker |

## See Also

- [[spring-boot4|Spring Boot 4 使用指南与发展现状]]
- [[spring-boot3|Spring Boot 3 使用指南]]
- [[spring-boot2|Spring Boot 2]]
- [[spring-webflux|Spring WebFlux]]
- [[spring/index|Spring 生态目录]]
- [[cloud-concepts|云原生常见概念]]
- [[oauth2-guide|OAuth2 指南]]（网关做统一鉴权时的协议背景）
- [[redis|Redis]]（Gateway 分布式限流的存储依赖）

## 参考

- [Spring Cloud 官方主页与版本兼容表](https://spring.io/projects/spring-cloud)
- [Spring Cloud Gateway 参考文档](https://docs.spring.io/spring-cloud-gateway/reference/)
- [Spring Cloud Netflix（仅剩 Eureka）](https://spring.io/projects/spring-cloud-netflix)
- [Spring Cloud OpenFeign](https://spring.io/projects/spring-cloud-openfeign)
- [Spring Cloud Circuit Breaker](https://spring.io/projects/spring-cloud-circuitbreaker)
- [Spring Cloud 2025.0.0 GA 发布公告（Gateway 新命名与前缀迁移）](https://spring.io/blog/2025/05/29/spring-cloud-2025-0-0-is-abvailable)
- [Release Train 命名规则](https://github.com/spring-cloud/spring-cloud-release/wiki/Release-Train-Naming-Convention)
