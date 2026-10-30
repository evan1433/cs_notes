---
title: Spring Framework 7
description: Spring Framework 7.0 详解：Jakarta EE 11 基线、Jackson 3 与 JSpecify 空安全、原生 API 版本控制、@ImportHttpServices 分组客户端、内置 @Retryable / @ConcurrencyLimit 弹性能力与 RestTestClient
tags:
  - java
  - spring
  - api-versioning
  - resilience
  - jakarta-ee
date: 2026-10-30
aliases:
  - spring7
  - Spring7
  - Spring Framework 7
---

# Spring Framework 7

Spring 7 是第七代框架的第一个版本（2025 年 11 月 GA）。如果说 Spring 6 解决的是"**能在 Java 17 上跑**"，那 Spring 7 解决的是"**在这套基线上把过去要靠第三方库或自研脚手架补的能力，收进框架本体**"：

- API 版本控制：不用再靠 URL 里塞 `/v1` 或自定义 Header 拦截器
- HTTP 接口客户端分组：不用再为每个远程服务手写 `HttpServiceProxyFactory`
- 重试与并发限流：不用再引 `spring-retry` + Resilience4j 两套注解
- 空安全：不用再靠 `@Nullable` 猜，用 JSpecify 让编译器和 IDE 真正检查

> **版本提示**：本文档事实核对时间为 2026 年 10 月。当前主线为 **7.0.x（最新 7.0.8）**，7.1.x 特性分支计划 2026 年 11 月开启。7.0 保留了 JDK 17 作为最低基线，但**官方推荐 JDK 25**。

## 1. 版本与基线

### 1.1 支持状态

| 版本 | GA 时间 | 状态 |
|------|---------|------|
| 7.0.x | 2025-11 | 当前生产主线 |
| 7.1.x | 计划 2026-11 | 下一特性分支 |
| 6.2.x | 2024-11 | 第六代终版，开源支持 **2026-06 已结束** |
| 5.3.x | 2020-10 | 开源支持 2024-08 已结束 |

### 1.2 基线升级

| 项 | Spring 6.2 | Spring 7.0 |
|----|-----------|-----------|
| JDK | 17 - 25 | **17 - 25+**（推荐 25） |
| Jakarta EE | EE 9-10 | **EE 11**（早期支持 EE 12） |
| Servlet | Servlet 6.0 | **Servlet 6.1**（Tomcat 11.0 / Jetty 12.1） |
| JPA | 3.1 | **3.2**（Hibernate ORM 7.1 / 7.2） |
| Bean Validation | 3.0 | **3.1**（Hibernate Validator 9.0 / 9.1） |
| Kotlin | 1.7+ | **2.2** |
| GraalVM | 22.x | **25** + 新的 exact reachability metadata 格式 |
| Netty | 4.1 | **4.2** |
| JUnit | JUnit 5 | **JUnit 6** |
| Jackson | 2.15+ | **Jackson 3.x**（2.x 降级为兼容） |

### 1.3 Jackson 3 是这次升级最容易被低估的部分

Spring 7 默认探测 Jackson 3。Jackson 3 把包名从 `com.fasterxml.jackson.*` 整体搬到 **`tools.jackson.*`**，这意味着：

| 项 | Jackson 2 | Jackson 3 |
|----|-----------|-----------|
| 根包 | `com.fasterxml.jackson` | **`tools.jackson`** |
| Maven 坐标 | `com.fasterxml.jackson.core:jackson-databind` | **`tools.jackson.core:jackson-databind`** |
| `JsonMapper` | `com.fasterxml.jackson.databind.json.JsonMapper` | `tools.jackson.databind.json.JsonMapper` |
| 异常体系 | 受检异常 `IOException` | **改为运行时异常**，方法签名不再 `throws` |
| 注解 | `com.fasterxml.jackson.annotation.*` | 包名不变（注解兼容） |

```java
// Spring 7 默认走 Jackson 3，import 已经是 tools.jackson
import tools.jackson.databind.json.JsonMapper;

JsonMapper jsonMapper = JsonMapper.builder()
        .findAndAddModules()
        .build();
```

> **弃用时间线已排定**：Jackson 2.x 支持在 7.0 中被标记为弃用，**7.1 关闭自动探测，7.2 完全移除**。升级到 7.0 就是迁 Jackson 3 的最后窗口期——现在不改，7.2 时就得连业务代码一起改。

## 2. 从 6.x 升级

### 2.1 被移除的东西

| 移除项 | 说明 | 替代方案 |
|--------|------|---------|
| `spring-jcl` 模块 | 不再自带 JCL 桥接 | 直接用 Apache Commons Logging 1.3.0（多数应用无感） |
| `javax.annotation` / `javax.inject` 注解 | `@Resource` / `@PostConstruct` / `@Inject` 的 javax 版不再识别 | 改 `jakarta.annotation` / `jakarta.inject` |
| Undertow 支持 | Undertow 尚不支持 Servlet 6.1 | 换 Tomcat 11 或 Jetty 12.1 |
| `suffixPatternMatch` / `trailingSlashMatch` / `favorPathExtension` | 路径后缀与尾斜杠匹配的旧选项全部移除 | 在网关/前端层规范 URL，或用 `UrlHandlerFilter` |
| `PathPatternParser.matchOptionalTrailingSeparator` | 同上 | 同上 |
| `ListenableFuture` | 6.0 起弃用，7.0 移除 | `CompletableFuture` |
| OkHttp3 支持 | 客户端传输实现移除 | JDK `HttpClient` / Apache HttpClient 5 / Reactor Netty |
| `Theme` 支持 | 主题解析机制移除 | 自行实现 |
| `webjars-locator-core` | 旧版 WebJars 定位器 | `webjars-locator-lite` |
| JUnit 4 支持 | 4.x 集成移除 | JUnit Jupiter + `SpringExtension` |

### 2.2 六个静默行为变更

这些不报错、但语义变了，升级后必须主动排查：

| 变更 | 6.x 行为 | 7.0 行为 |
|------|---------|---------|
| `HttpHeaders` 继承关系 | 实现 `MultiValueMap<String, String>` | **不再是 `MultiValueMap`**，按 Map 用的代码要改 |
| SpEL 求值上限 | 无限制 | **默认最多 10,000 次操作**，可调 `spring.expression.maxOperations` |
| `SimpleEvaluationContext` 编译 | 默认支持表达式编译 | **默认不支持**，需显式 `withCompilationSupported()` |
| `SpringExtension` 的 `ExtensionContext` | 类级作用域 | **测试方法级作用域**，依赖它的自定义扩展可能异常 |
| `HttpStatus` | 与 RFC 7231 对齐 | 与 **RFC 9110** 对齐，新增若干状态码、部分旧码弃用 |
| `RestTemplate` | 正常维护 | 弃用已排期（**7.1 起正式标 `@Deprecated`**） |

### 2.3 弃用清单（还能用，但别新增）

`PathMatcher`（含 `AntPathMatcher`）、`HandlerMappingIntrospector`、`<mvc:*>` 与 `<lang:*>` XML 命名空间、Jackson 2.x、`view.document` / `view.feed` 里的 XLS/RSS/PDF `*View`、Kotlin 脚本模板、BeanShell 脚本支持。

## 3. 空安全：JSpecify

### 3.1 为什么换 JSpecify

Spring 长期用 JSR 305 那套 `@Nullable` / `@NonNull`（还带着 `javax.annotation` 的历史包袱）。它的问题很实在：**注解只能标在类型最外层**，标不了泛型参数、数组元素、可变参数元素。`List<@Nullable String>` 这种语义根本表达不出来。

JSpecify 补上了这一层，并且和 Kotlin、IDE、静态分析工具的集成更紧。

### 3.2 用法

包级开启，一个包一个 `package-info.java`：

```java
// src/main/java/com/example/order/package-info.java
@NullMarked
package com.example.order;

import org.jspecify.annotations.NullMarked;
```

开了 `@NullMarked` 之后，包里所有类型默认非空，**只有显式标注的才可空**：

```java
package com.example.order;

import org.jspecify.annotations.Nullable;
import java.util.List;

public class OrderQueryService {

    // 返回集合可能为空，但集合里不会有 null 元素
    public List<Order> findByStatus(String status) {
        return repository.selectByStatus(status);
    }

    // 返回值可能为 null —— 调用方和 IDE 都能看到
    public @Nullable Order findLatest(String sku) {
        return repository.selectLatest(sku);
    }

    // 元素可空：JSR 305 时代写不出来
    public List<@Nullable String> findNotes(long orderId) {
        return repository.selectNotes(orderId);
    }
}
```

### 3.3 实际收益

- IDE 能在调用 `findLatest()` 后直接提示空指针风险，不用等运行期 NPE
- Kotlin 侧能把 Java 方法识别成 `Order?` 而不是平台类型 `Order!`
- 生成 API 文档时能标出可空性，对开放平台尤其有用

> 注意：这是**编译期契约**，不加运行时校验。真正需要兜底的入口（Controller 参数、MQ 消息体）还是要靠 Bean Validation。

## 4. API 版本控制

这是 7.0 最有分量的功能。过去做 API 版本要么在 URL 里写 `/v1/orders`，要么自己写拦截器读 Header 再路由——前者让 URL 语义变脏，后者等于重写一遍 `HandlerMapping`。

Spring 7 在 **Spring MVC 与 WebFlux** 两侧都做成了原生能力。

### 4.1 服务端：一个路径，多个版本

```java
@RestController
public class AccountController {

    @GetMapping(path = "/accounts/{id}", version = "1.0")
    public AccountV1 getV1(@PathVariable long id) {
        return service.findV1(id);
    }

    @GetMapping(path = "/accounts/{id}", version = "1.1")
    public AccountV1 getV1_1(@PathVariable long id) {
        AccountV1 account = service.findV1(id);
        account.setContact(service.findContact(id));   // 1.1 多返回联系方式
        return account;
    }

    @GetMapping(path = "/accounts/{id}", version = "2.0")
    public AccountV2 getV2(@PathVariable long id) {
        return service.findV2(id);                      // 2.0 结构变更
    }
}
```

请求带 `API-Version: 1.1` 命中第二个方法，带 `2.0` 命中第三个。**没带版本号时用默认版本**（默认按语义版本的 `1.0` 处理）。

### 4.2 基线版本：`1.2+`

真实场景里大部分接口在两个版本间根本不变。`1.2+` 表示"从 1.2 起所有版本都兼容这个方法"：

```java
@GetMapping(path = "/accounts/{id}", version = "1.2+")
public AccountV1 getFrom12Onwards(@PathVariable long id) {
    return service.findV1(id);
}
```

规则是：**更高版本里如果没有更具体的映射，就落到这条基线上**。上例中 `1.5` 会命中它，但只要有人写了 `version = "1.5"` 的方法，`1.5` 就改走那条。

### 4.3 函数式端点

`RouterFunction` 用 `version` 请求谓词：

```java
RouterFunction<ServerResponse> routes = RouterFunctions.route()
        .GET("/hello-world", version("1.2"),
             request -> ServerResponse.ok().body("Hello World"))
        .build();
```

### 4.4 版本放在哪：Header / Query / MediaType / Path

| 位置 | 是否需要改映射 | 说明 |
|------|---------------|------|
| 请求头 | 不用 | 最常用，如 `API-Version: 1.1` |
| 查询参数 | 不用 | 如 `?version=1.1` |
| Media Type 参数 | 不用 | 如 `Accept: application/json;v=1.1` |
| 路径段 | **需要** | 必须声明成 URI 变量，如 `/api/{version}/accounts`，否则框架不知道哪段是版本 |

路径段方案通常不逐个方法写，而是配成全局的公共前缀（Path Matching 设置），避免每个映射重复一遍。

### 4.5 弃用提示：自动返回标准响应头

老版本接口要下线时，框架能自动带上下线信号（按 RFC 9745 / RFC 8594）：

```http
HTTP/1.1 200 OK
Deprecation: @1735689600
Sunset: Wed, 01 Jul 2026 00:00:00 GMT
Link: <https://api.example.com/deprecation>; rel="deprecation"; type="text/html"
```

比在接口文档里写一行"该版本将于某日下线"可靠得多——**客户端能被程序化检测到**。

### 4.6 客户端：一次配置，逐请求指定版本

```java
RestClient client = RestClient.builder()
        .baseUrl("http://localhost:8080")
        .apiVersionInserter(ApiVersionInserter.useHeader("API-Version"))
        .build();

// 只关心这次请求的版本，插入方式由 inserter 决定
Account account = client.get()
        .uri("/accounts/1")
        .apiVersion("1.1")
        .retrieve()
        .body(Account.class);
```

HTTP 接口客户端直接在注解上声明：

```java
@HttpExchange("/accounts")
public interface AccountService {

    @GetExchange(url = "/{id}", version = "1.1")
    Account getAccount(@PathVariable int id);
}
```

### 4.7 测试侧

`RestTestClient`、`WebTestClient`、`MockMvc` 都支持版本控制。standalone 模式下需要自己提供 `ApiVersionStrategy`；走 `ApplicationContext` 的模式则直接从上下文读取服务端配置，无需重复声明。

> 版本解析默认按语义版本（major.minor.patch）比较；要用日期或其他格式，提供自定义 `ApiVersionParser` 即可。

## 5. HTTP 接口客户端：`@ImportHttpServices`

6.0 引入了 `@HttpExchange` + `HttpServiceProxyFactory`，但真正落地时是这样的：一个应用接了 GitHub、StackOverflow、内部用户中心三个远程服务，于是每个接口都要 `new` 一个工厂、`createClient`、再注册成 Bean。**重复配置比业务代码还长**。

7.0 加了注册表层：按"组"声明接口，框架自动建代理并注册为 Bean。

### 5.1 声明

```java
@Configuration(proxyBeanMethods = false)
@ImportHttpServices(group = "weather", types = {FreeWeather.class, CommercialWeather.class})
@ImportHttpServices(group = "user", types = {UserServiceInternal.class, UserServiceOfficial.class})
public class HttpServicesConfiguration { }
```

也可以用包扫描，省掉逐个列接口：

```java
@ImportHttpServices(group = "github", basePackages = "com.example.client.github")
```

一个组 = 一批共享同一套客户端配置的接口。默认用 `RestClient`，通过 `clientType` 属性可切到 `WebClient`。

### 5.2 配置组的客户端

```java
@Bean
RestClientHttpServiceGroupConfigurer groupConfigurer() {
    return groups -> {
        groups.filterByName("weather", "user")
              .forEachClient((group, builder) -> builder
                      .defaultHeader("User-Agent", "My-Application"));

        groups.filterByName("weather")
              .forEachClient((group, builder) -> builder
                      .baseUrl("https://api.weather.example.com"));
    };
}
```

配置完直接按类型注入即可，不用关心代理怎么来的：

```java
@RestController
public class WeatherController {

    private final FreeWeather freeWeather;

    public WeatherController(FreeWeather freeWeather) {
        this.freeWeather = freeWeather;
    }
}
```

> 同一个接口出现在多个组里时，按类型注入会有歧义——这时从 `HttpServiceProxyRegistry` 里按组名取。

### 5.3 大文件：流的支持

```java
@HttpExchange("/files")
public interface FileService {

    // 响应侧：直接拿流，不整体读进内存
    @GetExchange("/{id}")
    InputStream download(@PathVariable long id);
}
```

请求侧用 `StreamingHttpOutputMessage.Body` 作为方法参数，往 `OutputStream` 里写。响应侧返回 `InputStream` 或 `ResponseEntity<InputStream>`。

### 5.4 生态怎么接上来

| 组件 | 通过组配置器加的能力 |
|------|---------------------|
| Spring Boot 4.0 | `spring.http.serviceclient.<group>.*` 属性配置，每个组独立 base-url、超时 |
| Spring Cloud 2025.1 | 透明加上负载均衡与熔断 |
| Spring Security 7.0 | 识别 `@HttpExchange` 方法上的 `@ClientRegistrationId`，自动带 OAuth 令牌 |

## 6. 弹性能力：`@Retryable` 与 `@ConcurrencyLimit`

过去要重试就引 `spring-retry`（另一套 `@Retryable`），要限并发就引 Resilience4j 或自己写信号量。7.0 把这两件事收进了 `spring-core` / `spring-context` 的 `org.springframework.core.retry` 包。

### 6.1 开启方式

```java
@Configuration
@EnableResilientMethods
public class ResilienceConfig { }
```

`@EnableResilientMethods` 注册 `RetryAnnotationBeanPostProcessor` 和 `ConcurrencyLimitBeanPostProcessor`。**不加这个注解，两个注解会被完全忽略，一次都不重试**——这是最容易踩的坑。

### 6.2 `@Retryable`

默认行为：任意异常都重试，**首次失败后再重试 3 次**，每次间隔 1 秒。

```java
@Service
public class NotificationService {

    @Retryable
    public void send(String payload) {
        jmsClient.destination("notifications").send(payload);
    }

    // 只对指定异常重试，并自定义退避策略
    @Retryable(
            includes = MessageDeliveryException.class,
            maxAttempts = 5,
            delay = 100,
            multiplier = 2,
            maxDelay = 1000,
            jitter = 10)
    public void sendWithBackoff(String payload) {
        jmsClient.destination("notifications").send(payload);
    }
}
```

| 属性 | 含义 |
|------|------|
| `value` / `includes` | 只对这些异常触发重试，`@Retryable(X.class)` 是 `includes` 的简写 |
| `excludes` | 这些异常不重试 |
| `maxAttempts` | **重试次数**，不含首次调用（默认 3） |
| `delay` | 首次退避间隔（毫秒） |
| `multiplier` | 退避倍数，`2` 即指数退避 |
| `maxDelay` | 单次退避上限 |
| `jitter` | 随机抖动，避免大量实例同时重试形成尖峰 |

> **语义与 Spring Retry 相反**：Spring Retry 的 `maxAttempts` 把首次调用也算进去，Framework 7 的 `maxAttempts` **只算重试**。所以 `maxAttempts = 2` 实际会调用 3 次。从 `spring-retry` 迁过来的代码必须逐处核对这个数字。

响应式方法直接支持：返回 `Mono` / `Flux` 时，框架自动用 Reactor 的 retry 能力装饰管道。

### 6.3 `@ConcurrencyLimit`

保护下游资源不被并发打爆。**在虚拟线程时代这个能力尤其重要**——虚拟线程没有线程池上限，不显式限流就等于不限流。

```java
@Service
public class InventoryService {

    @ConcurrencyLimit(10)   // 同时最多 10 个调用进入
    public void syncInventory() {
        remoteApi.pull();
    }

    @ConcurrencyLimit(1)    // 默认值，等价于串行化，实质是给这个 Bean 加锁
    public void rebuildCache() {
        cache.reload();
    }
}
```

可以标在类上，作用于该类层级里所有经代理的方法。

### 6.4 编程式

需要动态策略（按配置决定重试几次、按运行时条件决定是否重试）时用 `RetryTemplate`，它在 `org.springframework.core.retry` 包里。

## 7. 其它值得知道的

### 7.1 `BeanRegistrar`：程序化注册 Bean

一个 `@Bean` 方法只能返回一个 Bean，想按配置动态注册一批就很别扭。7.0 新增 `BeanRegistrar` 契约：

```java
public class ReportBeanRegistrar implements BeanRegistrar {

    @Override
    public void register(BeanRegistry registry, Environment env) {
        registry.registerBean("dailyReport", DailyReportJob.class);
        if (env.matchesProfiles("dev")) {
            registry.registerBean("reportSeeder", ReportSeeder.class);
        }
    }
}
```

### 7.2 代理策略统一 + `@Proxyable`

以前不同代理处理器（事务、`@Async`、缓存、校验）对"用 JDK 接口代理还是 CGLIB 子类代理"的默认值不一致，出问题很难定位。7.0 统一成 CGLIB 默认，并新增 `@Proxyable` 让**单个 Bean 可以退出全局策略**，选择接口代理或子类代理。

### 7.3 `HttpMessageConverters`：集中配置转换器

消息转换器的配置一直是"散落在各个 Configurer 里"，7.0 引入 `HttpMessageConverters`，思路对齐响应式的 `CodecConfigurer`：

```java
@Configuration
public class WebConfiguration implements WebMvcConfigurer {

    @Override
    public void configureMessageConverters(HttpMessageConverters.ServerBuilder builder) {
        // 注意：Jackson 3 的包名是 tools.jackson
        JsonMapper jsonMapper = JsonMapper.builder()
                .findAndAddModules()
                .enable(SerializationFeature.INDENT_OUTPUT)
                .build();
        builder.jsonMessageConverter(new JacksonJsonHttpMessageConverter(jsonMapper));
    }
}
```

`RestClient` 与 `RestTemplate` 也有同名方法，服务端和客户端可以共用一套 JSON 配置。

### 7.4 `PathPattern` 增强

`AntPathMatcher` 正式进入弃用流程。此前一直有人卡在升级上，原因是 `PathPattern` 不支持**多段前缀匹配**——7.0 补上了，现在 `/**/pages/index.html` 这种模式可以用了。

### 7.5 数据访问与消息

| 能力 | 说明 |
|------|------|
| `JmsClient` | 新的 JMS 门面，对齐 `JdbcClient` 的设计，支持可复用的操作句柄与 QoS 设置 |
| `JdbcClient` 增强 | 支持语句级 fetch size、max rows、query timeout |
| JPA 3.2 | `LocalContainerEntityManagerFactoryBean` 支持 `PersistenceConfiguration` |
| Hibernate `StatelessSession` | `LocalSessionFactoryBean` 暴露事务性 `Session` 与 `StatelessSession` 代理，推荐 ORM 7.2 |
| Jackson JMS 可信包 | 7.0.8 起可用 `setTrustedPackages(...)` 限制反序列化包范围 |

### 7.6 `RestTestClient`

社区要了很久的"`WebTestClient` 的阻塞版"，用于测试服务端应用。它内部包着 `RestClient`，所以**请求构造 API 与 `RestClient` 完全一致，到 `exchange()` 为止都通用**。

```java
// 绑定单个 Controller，不起服务器
RestTestClient client = RestTestClient.bindToController(new OrderController(service))
        .baseUrl("/test")
        .build();

client.get().uri("/orders/42")
        .accept(MediaType.APPLICATION_JSON)
        .exchange()
        .expectStatus().isOk()
        .expectHeader().contentType(MediaType.APPLICATION_JSON)
        .expectBody();
```

四种绑定方式：

| 工厂方法 | 用途 |
|----------|------|
| `bindToController(Object...)` | 只测指定 Controller，Mock 请求响应 |
| `bindToApplicationContext(WebApplicationContext)` | 加载完整 MVC 配置，但不起真实服务器 |
| `bindToRouterFunction(RouterFunction...)` | 测函数式端点 |
| `bindToServer()` | 连真实服务器，走完整网络栈 |

需要所有断言都执行完再统一报告失败时用 `expectAll(...)`，类似 AssertJ 的 soft assertions。

> Spring Boot 的 `TestRestTemplate` 在能力上已被它覆盖，官方团队正在考虑弃用后者。

### 7.7 测试基础设施

| 变化 | 说明 |
|------|------|
| 测试上下文暂停 | 缓存中不用的 `ApplicationContext` 会被暂停、需要时自动恢复，避免后台任务持续跑。7.0.3 起默认只在取到不同上下文时暂停，可用 `spring.test.context.cache.pause` 控制 |
| `@Nested` 注入 | `SpringExtension` 支持向嵌套测试类的构造器与字段注入，与生命周期方法共用同一上下文 |
| 非单例的 Bean Override | `@MockitoBean` / `@MockitoSpyBean` / `@TestBean` 现在也能替换 `prototype` 或自定义作用域的 Bean |
| 测试内动态属性 | 可以在测试的 `ApplicationContext` 内注册动态属性 |

### 7.8 语言与运行时

- **Class-File API**：JDK 24+ 上用 JEP 484 的 `ClassFileMetadataReader` 取代历史 ASM fork，对应用透明
- **SpEL 支持 `Optional`**：安全导航操作符与 Elvis 操作符会自动解包
- **Kotlin 协程上下文传播**：通过 `PropagationContextElement` 把追踪上下文带进协程

## 8. 与 Spring Boot 的对应关系

| Spring Boot | Spring Framework |
|-------------|------------------|
| 3.4.x / 3.5.x | 6.2.x |
| **4.0.x** | **7.0.x** |

Boot 4.0 同步做了两件配套的事：代码库全面模块化（自动配置拆成独立 artifact），以及新增 `spring-boot-starter-restclient` / `spring-boot-starter-webclient`，让"我要不要起 Web 服务器"和"我要不要 HTTP 客户端"彻底解耦。详见 [[spring-boot4|Spring Boot 4 使用指南]]。

## 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 升级后大量 `NoClassDefFoundError: com/fasterxml/jackson/...` | 还在用 Jackson 2 的坐标或包名 | 换 `tools.jackson.core:jackson-databind`，import 改 `tools.jackson.*` |
| Jackson 3 下方法签名编译不过 | Jackson 3 的异常改为运行时异常 | 去掉 `throws IOException`，catch 改 `JacksonException` |
| 找不到 `@PostConstruct` | 用了 `javax.annotation` | 改 `jakarta.annotation` |
| Undertow 起不来 | 7.0 移除 Undertow 支持 | 换 Tomcat 11 / Jetty 12.1 |
| 尾斜杠配置类编译失败 | `setUseTrailingSlashMatch` 已移除 | 用 `UrlHandlerFilter` 做重定向 |
| 把 `HttpHeaders` 当 `MultiValueMap` 传递 | 7.0 断开继承关系 | 改用 `HttpHeaders` 自身 API，必要时显式转换 |
| 复杂 SpEL 表达式突然抛异常 | 默认操作数上限 10,000 | 拆表达式，或调 `spring.expression.maxOperations` |
| `@Retryable` 完全不生效 | 没加 `@EnableResilientMethods` | 加注解，或手动注册 `RetryAnnotationBeanPostProcessor` |
| 重试次数比预期多一次 | `maxAttempts` 只算重试，不含首次 | 按"总调用次数 - 1"来配 |
| `@Retryable` 在同类内部调用无效 | 自调用绕过代理 | 拆到另一个 Bean |
| API 版本映射全部 404 | 版本放在路径里却没声明 URI 变量 | 路径改成 `/api/{version}/...`，或改用 Header / Query |
| `@ImportHttpServices` 的接口注入不到 | 用了 `basePackages` 但包路径写错，或没在 `@Configuration` 上 | 核对包名；确认注解标在配置类上 |
| 同类型接口注入有歧义 | 同一接口出现在多个组 | 从 `HttpServiceProxyRegistry` 按组名取 |

## See Also

- [[spring6|Spring Framework 6]]（迁移的前一站：Java 17 与 jakarta 命名空间）
- [[spring5|Spring 5 核心]]（容器、AOP、事务机制两代通用）
- [[spring-boot4|Spring Boot 4 使用指南与发展现状]]
- [[spring-cloud|Spring Cloud]]（HTTP 服务组的负载均衡与熔断由 Spring Cloud 2025.1 接管）
- [[jdk17|JDK 17]]（语言基线）
- [[spring/index|Spring 生态目录]]

## 参考

- [Spring Framework 官方参考文档](https://docs.spring.io/spring-framework/reference/)
- [Spring Framework 版本与支持策略](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions)
- [7.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes)
- [API Versioning in Spring](https://spring.io/blog/2025/09/16/api-versioning-in-spring)
- [HTTP Service Client Enhancements](https://spring.io/blog/2025/09/23/http-service-client-enhancements)
- [Core Spring Resilience Features](https://spring.io/blog/2025/09/09/core-spring-resilience-features)
- [The state of HTTP clients in Spring](https://spring.io/blog/2025/09/30/the-state-of-http-clients-in-spring)
- [RestTestClient 参考文档](https://docs.spring.io/spring-framework/reference/testing/resttestclient.html)
