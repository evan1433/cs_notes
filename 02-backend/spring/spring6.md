---
title: Spring Framework 6
description: Spring Framework 6.x 断代升级详解：Java 17 与 Jakarta EE 9 基线、javax→jakarta 迁移、HTTP Interface、ProblemDetail、AOT 原生镜像、RestClient、JdbcClient、虚拟线程与 6.2 的 MockMvcTester
tags:
  - java
  - spring
  - jakarta-ee
  - rest-client
  - native-image
date: 2026-10-30
aliases:
  - spring6
  - Spring6
  - Spring Framework 6
---

# Spring Framework 6

Spring 6 不是"5 加几个功能"，而是一次**底座换代**：整个代码库提升到 Java 17 源码级别，Servlet / JPA / Bean Validation 全线从 `javax.*` 切到 `jakarta.*`，并为 GraalVM 原生镜像补齐了 AOT 处理链路。业务代码的写法几乎没变，但**依赖链、命名空间、编译参数**必须跟着动。

> **版本提示**：本文档事实核对时间为 2026 年 10 月。Spring Framework 当前主线为 **7.0.x**（GA 于 2025 年 11 月，最新 7.0.8）；**6.2.x 是第六代最后一个特性分支，开源支持已于 2026 年 6 月结束**，只剩商业 LTS。新项目直接上 7.0，存量 6.x 项目要么升 7.0 要么买商业支持。

## 1. 版本与基线

### 1.1 三个小版本的分工

| 版本 | GA 时间 | 定位 | 标志性能力 |
|------|---------|------|-----------|
| 6.0 | 2022-11 | 断代起点 | Java 17 + Jakarta EE 9 基线、`jakarta` 命名空间、AOT / 原生镜像、Observability、HTTP Interface、ProblemDetail |
| 6.1 | 2023-11 | 补齐开发者体验 | `RestClient`、`JdbcClient`、虚拟线程、内置方法校验、`@HttpExchange` 支持服务端 |
| 6.2 | 2024-11 | 第六代收尾 | `MockMvcTester`（AssertJ）、`@TestBean` / `@MockitoBean`、`@Fallback`、后台 Bean 初始化、模板片段渲染 |

### 1.2 硬性基线（配错就起不来）

| 项 | Spring 5.3 | Spring 6.2 | Spring 7.0 |
|----|-----------|-----------|-----------|
| JDK 范围 | 8 - 21 | **17 - 25** | 17 - 25+ |
| 命名空间 | `javax.*` | **`jakarta.*`** | `jakarta.*` |
| Jakarta EE | Java EE 7-8 | EE 9-10（Servlet 6.0、JPA 3.1、BV 3.0） | EE 11-12（Servlet 6.1、JPA 3.2、BV 3.1） |
| Servlet 容器 | Tomcat 9 | Tomcat 10.1 / Jetty 11 / Undertow 2.3 | Tomcat 11 |
| 开源支持 | 2024-08 结束 | 2026-06 结束 | 当前主线 |

> 生产环境请用 JDK 17 / 21 / 25 这三个 LTS，22/23/24 属于 best-effort（官方接受 bug 报告但不承诺修复时限）。

## 2. 从 5.x 迁移：javax → jakarta

这是整个升级里唯一"无法用代码兼容"的部分：包名改了，字节码里就是不同的类。**没有银弹，只能逐个依赖升级到位。**

### 2.1 包名对照

| 能力 | Spring 5.3（`javax`） | Spring 6（`jakarta`） |
|------|----------------------|----------------------|
| Servlet | `javax.servlet.*` | `jakarta.servlet.*` |
| JPA | `javax.persistence.*` | `jakarta.persistence.*` |
| Bean Validation | `javax.validation.*` | `jakarta.validation.*` |
| 依赖注入注解 | `javax.inject.Inject` | `jakarta.inject.Inject` |
| 生命周期注解 | `javax.annotation.PostConstruct` / `PreDestroy` | `jakarta.annotation.PostConstruct` / `PreDestroy` |
| WebSocket | `javax.websocket.*` | `jakarta.websocket.*` |

> Spring 6 **仍然能识别 `javax` 版** 的 `@PostConstruct` / `@PreDestroy`（为了兼容预编译的旧二进制），但 `@Inject` 只认 `jakarta.inject`。不要依赖这个向后兼容，源码里统一改成 `jakarta`。

### 2.2 依赖升级清单

| 组件 | 5.x 时代 | 6.x 要求 |
|------|---------|---------|
| Tomcat | 9.x | **10.1+**（Servlet 6.0） |
| Jetty | 9/10 | **11+** |
| Undertow | 2.1 | **2.2.19+**，且要用 `undertow-servlet-jakarta` 这个 artifact |
| Hibernate ORM | 5.4/5.5 | 5.6 的 `hibernate-core-jakarta`，**建议直接上 6.x**（Boot 3 自带） |
| Hibernate Validator | 6.x | **7.0+**（EE 9）或 8.0（EE 10） |
| EclipseLink | 2.7 | **3.0+** |
| Apache HttpClient | 4.x | **5.x**（`HttpComponentsClientHttpRequestFactory` 强制要求） |
| Jackson | 2.13 | **2.14+** |

### 2.3 迁移步骤

```bash
# 1. 先全量替换包名（含测试代码和资源文件里的全限定类名）
grep -rl "javax\.\(servlet\|persistence\|validation\|annotation\|inject\|websocket\)" \
  src/main src/test | xargs sed -i '' \
  -e 's/javax\.servlet/jakarta.servlet/g' \
  -e 's/javax\.persistence/jakarta.persistence/g' \
  -e 's/javax\.validation/jakarta.validation/g' \
  -e 's/javax\.annotation/jakarta.annotation/g' \
  -e 's/javax\.inject/jakarta.inject/g' \
  -e 's/javax\.websocket/jakarta.websocket/g'

# 2. 全量编译，让编译器把所有不兼容点一次性暴露出来
mvn -q clean compile

# 3. 打开 -parameters，否则参数名反射会失效（Spring 6 已移除字节码推断方案）
mvn -q clean test -Dmaven.compiler.parameters=true
```

> 社区有 OpenRewrite 的 Spring Boot 3 升级 recipe（`rewrite-spring`），能自动处理包名替换、`HttpMethod` 枚举改类、`WebSecurityConfigurerAdapter` 移除等一批机械改动，比手搓 sed 稳。

### 2.4 五个静默行为变更

升级后不报错、但行为变了的地方，最值得提前排查：

| 变更 | 5.3 行为 | 6.0 行为 |
|------|---------|---------|
| 尾斜杠匹配 | `/api/user` 同时匹配 `/api/user/` | **默认不匹配**，返回 404 |
| 控制器识别 | 类型上有 `@RequestMapping` 即视为控制器 | 不再仅凭类型级 `@RequestMapping` 识别，接口式 AOP 代理可能失效 |
| `HttpMethod` | 枚举 | **普通类**，`EnumSet<HttpMethod>` 要改成 `Set<HttpMethod>`，`switch` 要改成 `if-else` |
| `@Async` 返回值 | 不校验 | 必须返回 `Future` 或 `void`，否则**抛异常** |
| 参数名解析 | 可从字节码局部变量表推断 | 移除该方案，**必须用 `-parameters` 编译** |

尾斜杠那条的兼容写法：

```java
@Configuration
public class WebConfiguration implements WebMvcConfigurer {

    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        // 临时回退到 5.3 行为；长期应在前端/网关层统一规范 URL
        configurer.setUseTrailingSlashMatch(true);
    }
}
```

## 3. 6.0 新增能力

### 3.1 HTTP Interface：把远程调用写成接口

和 OpenFeign 思路一致，但**不依赖 Spring Cloud**，纯 Framework 就有：

```java
public interface OrderClient {

    @GetExchange("/orders/{id}")
    OrderDTO findById(@PathVariable("id") long id);

    @PostExchange("/orders")
    OrderDTO create(@RequestBody CreateOrderRequest request);
}
```

```java
@Configuration
public class ClientConfig {

    @Bean
    public OrderClient orderClient() {
        RestClient restClient = RestClient.create("https://api.example.com");
        // 6.1 起才有 builderFor(RestClientAdapter) 这套写法；
        // 6.0 时期只能用 WebClientAdapter 适配 WebClient
        HttpServiceProxyFactory factory = HttpServiceProxyFactory
                .builderFor(RestClientAdapter.create(restClient))
                .build();
        return factory.createClient(OrderClient.class);
    }
}
```

> 6.1 起同一个 `@HttpExchange` 接口也能**反向用作服务端**（Spring MVC / WebFlux 可直接实现该接口处理请求），客户端与服务端共享接口定义，避免两边各写一份契约。

### 3.2 ProblemDetail：RFC 7807 标准错误响应

以前各家用 `{code, msg, data}` 自定义错误体，现在框架直接给标准结构（`type` / `title` / `status` / `detail` / `instance`）：

```java
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(OrderNotFoundException.class)
    public ProblemDetail handleNotFound(OrderNotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setTitle("Order Not Found");
        pd.setProperty("orderId", ex.getOrderId());   // 追加自定义字段
        return pd;
    }
}
```

响应体：

```json
{
  "type": "about:blank",
  "title": "Order Not Found",
  "status": 404,
  "detail": "order 42 does not exist",
  "instance": "/orders/42",
  "orderId": 42
}
```

### 3.3 AOT 与 GraalVM 原生镜像

Spring 6 补齐了整条 AOT（Ahead-Of-Time）处理链：启动时不再是"运行期反射扫描"，而是**构建期就生成 BeanDefinition、代理类、反射 hint**。

| 模式 | 类加载/装配 | 启动耗时 | 内存 | 适用 |
|------|------------|---------|------|------|
| 传统 JIT | 运行期扫描 + 反射 | 秒级 | 高 | 绝大多数业务系统 |
| AOT（JVM 上跑） | 构建期生成，运行期直接用 | 明显更短 | 相近 | 冷启动敏感的 Serverless |
| Native Image | 构建期编译成机器码 | 毫秒级 | 低 | CLI、FaaS、边缘 |

```java
// 反射用到的 DTO（如 Jackson 反序列化目标）在 Native 下必须显式登记
@RegisterReflectionForBinding({OrderDTO.class, CreateOrderRequest.class})
@SpringBootApplication
public class Application { }
```

> 代价：构建从秒级变成分钟级；动态代理、`Class.forName`、运行期生成字节码的库都要额外适配。**不要为了"看起来先进"上 Native**，只有冷启动真正成为瓶颈时才值得。

### 3.4 Observability：Micrometer Observation 直接织进框架

`spring-web` 把 `io.micrometer:micrometer-observation:1.10+` 变成编译依赖，`RestTemplate` / `WebClient` 会自动产生 HTTP 客户端观测；Spring MVC 与 WebFlux 也各有 `ServerHttpObservationFilter` 产生服务端观测。

```java
ObservationRegistry registry = ObservationRegistry.create();

RestClient client = RestClient.builder()
        .baseUrl("https://api.example.com")
        .observationRegistry(registry)   // 一行接入 metrics + tracing
        .build();
```

意义在于：**不再需要为每个 HTTP 客户端手写埋点**，Micrometer 会把 Observation 同时翻译成指标（Prometheus）和链路 span（OpenTelemetry / Brave）。

## 4. 6.1 新增能力

### 4.1 RestClient：同步 HTTP 客户端的新标准

`RestTemplate` 的 API 是 2009 年的设计，`WebClient` 又是响应式的、阻塞场景用起来别扭。6.1 补上了中间那块：**流式 API + 同步语义 + 与 `RestTemplate` 共享底层**。

```java
RestClient client = RestClient.builder()
        .baseUrl("https://api.example.com")
        .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + token)
        .build();

// GET
OrderDTO order = client.get()
        .uri("/orders/{id}", 42)
        .retrieve()
        .body(OrderDTO.class);

// POST，只关心状态码
client.post()
        .uri("/orders")
        .contentType(MediaType.APPLICATION_JSON)
        .body(request)
        .retrieve()
        .toBodilessEntity();

// 错误处理：默认 4xx/5xx 会抛异常，这里改成带上下文的业务异常
client.get()
        .uri("/orders/{id}", 42)
        .retrieve()
        .onStatus(HttpStatusCode::is4xxClientError, (req, res) -> {
            throw new OrderQueryException("查询失败, status=" + res.getStatusCode());
        })
        .body(OrderDTO.class);
```

三者怎么选：

| 客户端 | 编程模型 | 何时用 |
|--------|---------|--------|
| `RestTemplate` | 阻塞、模板方法 | 存量代码，不再新增 |
| `RestClient` | 阻塞、流式 API | **新代码默认选它** |
| `WebClient` | 响应式、`Mono`/`Flux` | 全链路响应式、需要流式/SSE |

> 6.2 有个容易踩的行为变更：只调 `.retrieve()` 而不接终止操作（`.body()` / `.toBodilessEntity()`）以前是"发后即忘"并泄漏观测作用域，6.2 起**变成 no-op**——必须调用终止操作才会真正发请求。

### 4.2 JdbcClient：JDBC 的统一门面

`JdbcTemplate` + `NamedParameterJdbcTemplate` 两套 API 长期并存，`JdbcClient` 把它们合成一个流式入口：

```java
@Bean
public JdbcClient jdbcClient(DataSource dataSource) {
    return JdbcClient.create(dataSource);
}
```

```java
// 查询列表
List<Order> paid = jdbcClient
        .sql("select id, sku, qty from orders where status = :status limit :limit")
        .param("status", "PAID")
        .param("limit", 100)
        .query((rs, rowNum) -> new Order(
                rs.getLong("id"), rs.getString("sku"), rs.getInt("qty")))
        .list();

// 查单条：查不到返回 Optional，不再抛 EmptyResultDataAccessException
Optional<Order> one = jdbcClient
        .sql("select id, sku, qty from orders where id = :id")
        .param("id", 42L)
        .query(ROW_MAPPER)
        .optional();

// 更新
int rows = jdbcClient
        .sql("update orders set status = :status where id = :id")
        .param("status", "SHIPPED")
        .param("id", 42L)
        .update();
```

### 4.3 虚拟线程

6.1 起框架全面兼容 JDK 21 虚拟线程，并提供专用执行器：

```java
@Bean
public AsyncTaskExecutor applicationTaskExecutor() {
    // 每个任务一条虚拟线程：阻塞式代码也能拿到接近响应式的并发度
    return new VirtualThreadTaskExecutor("vt-");
}
```

Spring Boot 3.2+ 只需一行配置即可全局打开（Tomcat 请求线程、`@Async`、`@Scheduled` 一起切换）：

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

> **前提是别踩这两个坑**：`synchronized` 块里做阻塞 IO 会钉住载体线程（JDK 24 前）；线程池大小限制类逻辑（如信号量式的连接池上限）在虚拟线程下会变成真瓶颈。虚拟线程解决的是"线程太贵"，不是"下游扛不住"。

### 4.4 内置方法校验

以前要在类上加 `@Validated` 才能让 `@Min` / `@NotBlank` 在方法参数上生效，现在**直接生效，不需要 `@Validated`**：

```java
@RestController
public class OrderController {

    @GetMapping("/orders/{id}")
    public OrderDTO find(@PathVariable @Min(1) long id) {
        return orderService.find(id);
    }
}
```

```java
@RestControllerAdvice
public class ValidationAdvice {

    @ExceptionHandler(HandlerMethodValidationException.class)
    public ProblemDetail onInvalid(HandlerMethodValidationException ex) {
        ProblemDetail pd = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        pd.setTitle("参数校验失败");
        pd.setProperty("errors", ex.getAllErrors().stream()
                .map(e -> e.getDefaultMessage()).toList());
        return pd;
    }
}
```

> 注意：如果项目里还留着类级 `@Validated` 的 AOP 式校验，会和内置校验**双重触发**，迁移时把 `@Validated` 去掉。

## 5. 6.2 新增能力

6.2 是第六代的收尾版本，重点补的是**测试体验**和**启动性能**。

### 5.1 MockMvcTester：AssertJ 风格的接口测试

`MockMvc` 的 `andExpect(...)` 静态导入可发现性差、自定义断言难写。6.2 提供了基于 AssertJ 的 `MvcTester`：

```java
// 纯单元测试：不启动容器，直接传控制器
MvcTester mvc = MvcTester.of(new OrderController(orderService));

assertThat(mvc.get().uri("/orders/42"))
        .hasStatusOk()
        .body().json().isLenientlyEqualTo(new ClassPathResource("order.json"));
```

```java
// 集成测试：从已有上下文构建
MvcTester mvc = MvcTester.from(webApplicationContext);
assertThat(mvc.post().uri("/orders").contentType(MediaType.APPLICATION_JSON).content(body))
        .hasStatus(HttpStatus.CREATED);
```

### 5.2 测试替身注解：`@TestBean` 与 `@MockitoBean`

| 注解 | 作用 | 取代 |
|------|------|------|
| `@TestBean` | 用测试类里的静态工厂方法提供 Bean | 手写 `@TestConfiguration` |
| `@MockitoBean` | 用 Mockito mock 替换容器中的 Bean | Boot 的 `@MockBean` |
| `@MockitoSpyBean` | 用 Spy 包装容器中的 Bean | Boot 的 `@SpyBean` |

```java
@SpringBootTest
class OrderServiceTest {

    // 工厂方法必须 static、与字段同名、返回同类型
    @TestBean
    Clock clock;

    static Clock clock() {
        return Clock.fixed(Instant.parse("2026-01-01T00:00:00Z"), ZoneOffset.UTC);
    }

    @MockitoBean
    StockClient stockClient;
}
```

> `@MockBean` / `@SpyBean` 原先属于 Spring Boot，6.2 把它们下沉到 Framework 并重命名为 `@MockitoBean` / `@MockitoSpyBean`，同时**每次使用都会新建一个 ApplicationContext 缓存分区**——测试类里用得越多，上下文越多、跑得越慢。能用 `@TestBean` 就别用 mock。

### 5.3 其它值得知道的变化

| 能力 | 说明 |
|------|------|
| `@Fallback` Bean | 标记为"兜底候选"：只有没有其它同类型 Bean 时才生效，比 `@ConditionalOnMissingBean` 少了对自动配置顺序的依赖 |
| 后台 Bean 初始化 | 非关键 Bean 可以放到容器 refresh 之后在后台线程完成初始化，缩短启动时间 |
| 属性占位符转义 | `\${...}` 可以输出字面量而不被解析 |
| 构造器数据绑定到集合 | `@ModelAttribute` 支持直接绑定 `List` / `Map` / 数组参数 |
| 请求头数据绑定 | 请求头可绑定到 `@ModelAttribute` 参数 |
| 模板片段渲染 | 服务端模板支持只渲染片段（配合 htmx 一类局部刷新） |
| `@ExceptionHandler` 内容协商 | 异常处理方法也参与 `Accept` 协商，可对同一异常返回 JSON 或 HTML |
| `UrlHandlerFilter` | 统一处理尾斜杠重定向，替代已废弃的 `setUseTrailingSlashMatch` |

## 6. 与 Spring Boot 的版本对应

Framework 版本不是你直接选的——**由 Boot 决定**：

| Spring Boot | Spring Framework | 备注 |
|-------------|------------------|------|
| 3.0.x / 3.1.x | 6.0.x | 首个 Java 17 + `jakarta` 组合 |
| 3.2.x / 3.3.x | 6.1.x | `RestClient` / `JdbcClient` 可用 |
| 3.4.x / 3.5.x | 6.2.x | `MockMvcTester`、`@MockitoBean` |
| 4.0.x | 7.0.x | 新主线，见 [[spring-boot4\|Spring Boot 4]] |

## 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 启动报 `ClassNotFoundException: javax.servlet.Filter` | 依赖还停在 Servlet 5 / Tomcat 9 | 升到 Tomcat 10.1+，或换 `undertow-servlet-jakarta` |
| `NoSuchMethodError: javax.persistence.*` | Hibernate 5.4/5.5 未换 jakarta 版 | 用 `hibernate-core-jakarta` 5.6 或直接升 Hibernate 6 |
| `@PostConstruct` 不执行 | 用了 `javax.annotation` 版本，而容器只认 `jakarta` | 改 import 为 `jakarta.annotation.PostConstruct` |
| 参数名全部变成 `arg0` / `arg1` | 未用 `-parameters` 编译 | 加编译参数；Spring 6 已移除字节码推断 |
| 接口 404，日志显示 No mapping | 尾斜杠不再默认匹配 | 前端统一去尾斜杠，或临时 `setUseTrailingSlashMatch(true)` |
| 编译报 `EnumSet<HttpMethod>` 类型错误 | `HttpMethod` 从枚举改成了类 | 改成 `Set<HttpMethod>`，`switch` 改 `if-else` |
| `@Async` 方法启动即报错 | 返回值不是 `Future`/`void` | 改返回类型；需要结果用 `CompletableFuture` |
| `RestClient` 请求没发出去 | 只调了 `.retrieve()` 没接终止操作（6.2 行为） | 补 `.body(...)` 或 `.toBodilessEntity()` |
| Native 镜像启动即挂，报反射相关异常 | 运行期反射的类未登记 hint | 用 `@RegisterReflectionForBinding`，或改用 `-H:+ReportExceptionStackTraces` 定位 |
| 校验注解不生效又被触发两次 | 同时存在类级 `@Validated` 和 6.1 内置校验 | 删掉 `@Validated`，统一用内置校验 |

## See Also

- [[spring5|Spring 5 核心]]（容器、Bean 生命周期、AOP、事务——机制层面两代通用）
- [[spring7|Spring Framework 7]]（下一代：Jakarta EE 11、Jackson 3、API 版本控制）
- [[spring-boot3|Spring Boot 3 使用指南]]（6.x 的自动装配载体）
- [[spring-boot4|Spring Boot 4 使用指南与发展现状]]（升到 Framework 7.0）
- [[jdk17|JDK 17]]（Java 17 的语言特性是新基线的一部分）
- [[spring-webflux|Spring WebFlux]]
- [[spring-mvc|Spring MVC]]
- [[spring/index|Spring 生态目录]]

## 参考

- [Spring Framework 官方参考文档](https://docs.spring.io/spring-framework/reference/)
- [Spring Framework 版本与支持策略](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions)
- [6.0 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)
- [6.1 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.1-Release-Notes)
- [6.2 Release Notes](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.2-Release-Notes)
- [升级到 Spring Framework 6.x 指南](https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-6.x)
