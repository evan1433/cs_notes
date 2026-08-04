---
title: Spring Boot 3 使用指南
description: 从项目初始化、配置管理和 REST API 开发，到数据访问、测试、监控与部署的 Spring Boot 3 实战指南
tags:
  - java
  - spring-boot
  - backend
date: 2026-08-04
aliases:
  - Spring Boot 3
---

# Spring Boot 3 使用指南

Spring Boot 3 基于 Spring Framework 6，最低要求 Java 17，并全面使用
`jakarta.*` 命名空间。本指南以 Spring Boot 3.5.x、Java 21、Maven 和 Spring MVC
为例，完成一个可运行的 REST API，并介绍工程中常用的配置、数据访问、测试、监控与部署方式。

## 版本与环境准备

### 推荐环境

| 工具 | 建议版本 | 说明 |
| --- | --- | --- |
| JDK | 21 LTS | Spring Boot 3 最低要求 Java 17 |
| Spring Boot | 3.5.x | 本文示例使用 `3.5.16` |
| Maven | 3.9+ | 也可以使用项目自带的 Maven Wrapper |
| IDE | IntelliJ IDEA | 需正确配置项目 JDK |

检查本机环境：

```bash
java -version
mvn -version
```

> **注意**：Spring Boot 3 不支持 Java 8 或 Java 11。新项目优先选择 Java 21；
> 维护已有系统时至少升级到 Java 17。

### Spring Boot 3 的关键变化

- Java 基线提升到 17，可直接使用 `record`、文本块和模式匹配等语法。
- Java EE API 从 `javax.*` 迁移到 `jakarta.*`，例如
  `jakarta.persistence.Entity` 和 `jakarta.validation.Valid`。
- 默认使用 Spring Framework 6、Spring Security 6、Hibernate 6。
- 可使用 GraalVM Native Image，但并非所有反射或动态代理场景都能自动适配。
- 可观测性统一建立在 Micrometer Observation 之上。

## 创建项目

可以通过 [Spring Initializr](https://start.spring.io/) 创建项目，选择：

- Project：Maven
- Language：Java
- Spring Boot：3.5.x
- Packaging：Jar
- Java：21
- Dependencies：Spring Web、Validation、Spring Data JPA、H2 Database、Actuator

也可以手工创建 `pom.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.5.16</version>
        <relativePath/>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>product-service</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>product-service</name>

    <properties>
        <java.version>21</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

父工程统一管理依赖版本。对于 Spring Boot 已管理的依赖，不要单独指定版本，
否则容易产生不兼容的依赖组合。

## 工程结构与启动流程

推荐按业务或功能分包，避免大型项目完全按 `controller`、`service`、`repository`
分成横向目录。本文为了展示完整示例，使用以下小型结构：

```text
src/
├── main/
│   ├── java/com/example/product/
│   │   ├── ProductApplication.java
│   │   └── product/
│   │       ├── Product.java
│   │       ├── ProductController.java
│   │       ├── ProductNotFoundException.java
│   │       ├── ProductRepository.java
│   │       └── ProductRequest.java
│   └── resources/
│       └── application.yml
└── test/
    └── java/com/example/product/product/
        └── ProductControllerTest.java
```

主启动类应放在根包中，这样默认组件扫描能够覆盖所有子包：

```java
package com.example.product;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ProductApplication {

    public static void main(String[] args) {
        SpringApplication.run(ProductApplication.class, args);
    }
}
```

`@SpringBootApplication` 组合了三个核心能力：

- `@SpringBootConfiguration`：声明 Spring Boot 配置类。
- `@EnableAutoConfiguration`：根据类路径、配置和 Bean 条件启用自动配置。
- `@ComponentScan`：扫描启动类所在包及其子包。

启动与打包：

```bash
./mvnw spring-boot:run
./mvnw clean package
java -jar target/product-service-0.0.1-SNAPSHOT.jar
```

Windows 环境使用 `mvnw.cmd`。如果项目没有 Wrapper，可以将命令中的 `./mvnw`
替换为 `mvn`。

## 配置管理

### application.yml

Spring Boot 支持 `.properties` 和 YAML。团队中应统一格式，避免在同一位置同时存在
`application.properties` 和 `application.yml`：

```yaml
spring:
  application:
    name: product-service
  datasource:
    url: jdbc:h2:mem:products;MODE=PostgreSQL
    username: sa
    password: ""
  jpa:
    hibernate:
      ddl-auto: create-drop
    open-in-view: false

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: when-authorized
```

`spring.jpa.open-in-view=false` 可以避免在 Controller 层意外触发延迟加载；生产环境中，
数据库结构应由 Flyway 或 Liquibase 管理，不要使用 `ddl-auto=update` 自动修改表结构。

### Profile 环境隔离

公共配置写在 `application.yml`，差异配置放入不同 Profile：

```yaml
# application-dev.yml
logging:
  level:
    com.example.product: debug
```

```yaml
# application-prod.yml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

通过命令行启用生产环境：

```bash
java -jar app.jar --spring.profiles.active=prod
```

不要在配置文件中提交密码、Token 或私钥。Spring Boot 属性值可以由环境变量覆盖：

```bash
export SPRING_DATASOURCE_URL='jdbc:postgresql://localhost:5432/products'
export SPRING_DATASOURCE_USERNAME='product_app'
export SPRING_DATASOURCE_PASSWORD='replace-with-secret-manager-value'
java -jar app.jar --spring.profiles.active=prod
```

属性覆盖优先级较多，排查时重点检查命令行参数、环境变量、Profile 配置和基础配置。

### 类型安全配置

对于一组业务配置，优先使用 `@ConfigurationProperties`，不要散落多个 `@Value`：

```java
package com.example.product.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "product.cache")
public record ProductCacheProperties(int maximumSize, Duration ttl) {
}
```

在配置类上启用扫描：

```java
package com.example.product.config;

import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@ConfigurationPropertiesScan
public class ProductConfiguration {
}
```

对应配置：

```yaml
product:
  cache:
    maximum-size: 1000
    ttl: 10m
```

## 开发 REST API

下面实现商品的创建、查询和删除接口。示例使用 DTO 接收输入，避免直接把持久化实体
暴露为接口契约。

### 实体与数据仓库

```java
package com.example.product.product;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.math.BigDecimal;

@Entity
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;
    private BigDecimal price;

    protected Product() {
        // JPA 需要无参构造方法，业务代码不应直接调用。
    }

    public Product(String name, BigDecimal price) {
        this.name = name;
        this.price = price;
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public BigDecimal getPrice() {
        return price;
    }
}
```

```java
package com.example.product.product;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductRepository extends JpaRepository<Product, Long> {
}
```

Spring Data JPA 会在运行时为 `ProductRepository` 创建实现，常用的保存、分页、排序和
按 ID 查询方法无需手写 SQL。

### 请求校验

```java
package com.example.product.product;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public record ProductRequest(
        @NotBlank(message = "商品名称不能为空")
        @Size(max = 100, message = "商品名称不能超过 100 个字符")
        String name,

        @NotNull(message = "商品价格不能为空")
        @DecimalMin(value = "0.01", message = "商品价格必须大于等于 0.01")
        BigDecimal price) {
}
```

### Controller

```java
package com.example.product.product;

import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final ProductRepository repository;

    public ProductController(ProductRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public List<Product> findAll() {
        return repository.findAll();
    }

    @GetMapping("/{id}")
    public Product findById(@PathVariable Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new ProductNotFoundException(id));
    }

    @PostMapping
    public ResponseEntity<Product> create(@Valid @RequestBody ProductRequest request) {
        Product saved = repository.save(new Product(request.name(), request.price()));
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(saved.getId())
                .toUri();
        return ResponseEntity.created(location).body(saved);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        if (!repository.existsById(id)) {
            throw new ProductNotFoundException(id);
        }
        repository.deleteById(id);
        return ResponseEntity.noContent().build();
    }
}
```

小型示例可以直接注入 Repository。实际业务包含事务、多表协作或复杂规则时，应增加
Service 层，并将 `@Transactional` 放在 public 业务方法上。

### 统一异常响应

```java
package com.example.product.product;

public class ProductNotFoundException extends RuntimeException {

    public ProductNotFoundException(Long id) {
        super("商品不存在，id=" + id);
    }
}
```

Spring Framework 6 支持 RFC 9457 Problem Details，可用 `ProblemDetail` 返回统一错误：

```java
package com.example.product.product;

import java.net.URI;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ProductNotFoundException.class)
    ProblemDetail handleNotFound(ProductNotFoundException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND, exception.getMessage());
        problem.setTitle("商品不存在");
        problem.setType(URI.create("https://example.com/problems/product-not-found"));
        return problem;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ProblemDetail handleValidation(MethodArgumentNotValidException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "请求参数校验失败");
        problem.setTitle("参数错误");
        List<String> errors = exception.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .toList();
        problem.setProperty("errors", errors);
        return problem;
    }
}
```

启动应用后测试接口：

```bash
curl -i -X POST http://localhost:8080/api/products \
  -H 'Content-Type: application/json' \
  -d '{"name":"机械键盘","price":399.00}'

curl http://localhost:8080/api/products
curl http://localhost:8080/api/products/1
curl -i -X DELETE http://localhost:8080/api/products/1
```

## 数据库与事务

### 使用 PostgreSQL

将 H2 替换为 PostgreSQL 驱动：

```xml
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <scope>runtime</scope>
</dependency>
```

生产配置只保留连接信息，不让 Hibernate 修改结构：

```yaml
spring:
  datasource:
    url: ${SPRING_DATASOURCE_URL}
    username: ${SPRING_DATASOURCE_USERNAME}
    password: ${SPRING_DATASOURCE_PASSWORD}
    hikari:
      maximum-pool-size: 20
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false
```

连接池大小不能盲目设置。需要综合数据库最大连接数、应用实例数、查询耗时与并发量计算，
并通过指标持续调整。

### 使用 Flyway 管理结构

添加依赖：

```xml
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
</dependency>
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-database-postgresql</artifactId>
</dependency>
```

创建 `src/main/resources/db/migration/V1__create_product.sql`：

```sql
CREATE TABLE product (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0.01)
);
```

已执行的迁移脚本不要修改。结构变化应添加 `V2__...sql`，以保证开发、测试与生产环境
可以按同样顺序演进。

### 事务边界

```java
@Service
public class OrderService {

    private final OrderRepository orderRepository;
    private final InventoryRepository inventoryRepository;

    public OrderService(OrderRepository orderRepository,
                        InventoryRepository inventoryRepository) {
        this.orderRepository = orderRepository;
        this.inventoryRepository = inventoryRepository;
    }

    @Transactional
    public Order createOrder(CreateOrderCommand command) {
        // 扣减库存和创建订单必须全部成功或全部回滚。
        inventoryRepository.decrease(command.productId(), command.quantity());
        return orderRepository.save(Order.from(command));
    }
}
```

注意以下问题：

- 默认只对 `RuntimeException` 和 `Error` 回滚；受检异常需要显式配置。
- 同一个对象内部调用另一个 `@Transactional` 方法，通常不会经过代理，事务可能不生效。
- 不要在持有数据库事务时执行耗时的远程调用。
- `readOnly = true` 是优化提示，不是数据库写入的安全屏障。

## 测试

Spring Boot 3 默认使用 JUnit 5。应根据测试目标选择最小上下文，避免所有测试都使用
`@SpringBootTest`。

| 测试目标 | 常用注解 | 是否加载完整应用 |
| --- | --- | --- |
| 普通 Java 类 | 无 | 否 |
| MVC Controller | `@WebMvcTest` | 否，仅 Web 切片 |
| JPA Repository | `@DataJpaTest` | 否，仅数据切片 |
| 完整集成测试 | `@SpringBootTest` | 是 |

Controller 切片测试：

```java
package com.example.product.product;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.util.ReflectionTestUtils;

@WebMvcTest(ProductController.class)
class ProductControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private ProductRepository repository;

    @Test
    void shouldCreateProduct() throws Exception {
        Product saved = new Product("机械键盘", new BigDecimal("399.00"));
        ReflectionTestUtils.setField(saved, "id", 1L);
        when(repository.save(any(Product.class))).thenReturn(saved);

        mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"机械键盘","price":399.00}
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().exists("Location"))
                .andExpect(jsonPath("$.name").value("机械键盘"));
    }
}
```

测试通过 `ReflectionTestUtils` 模拟数据库生成 ID，使 `Location` 响应头可以稳定断言。
更大型的项目应让 Controller 返回独立的响应 DTO，避免 Web 契约依赖 JPA 实体的内部状态。

运行测试：

```bash
./mvnw test
```

涉及 PostgreSQL、Redis 或 Kafka 的集成测试，推荐使用 Testcontainers 启动真实依赖，
减少 H2 与生产数据库语法或行为不同造成的误判。

## 日志、监控与健康检查

引入 `spring-boot-starter-actuator` 后，默认可访问：

```bash
curl http://localhost:8080/actuator/health
```

生产环境建议只暴露必要端点：

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  endpoint:
    health:
      probes:
        enabled: true
      show-details: when-authorized
```

如需 Prometheus 格式指标，添加 `micrometer-registry-prometheus` 依赖。此时 Kubernetes
可分别使用 `/actuator/health/liveness` 和 `/actuator/health/readiness` 进行存活与就绪探测。

不要在公网暴露 `env`、`configprops`、`heapdump` 等敏感端点。Actuator 端点应通过
Spring Security、独立管理端口、内网或网关访问策略保护。

应用日志优先使用参数化写法：

```java
private static final Logger log = LoggerFactory.getLogger(OrderService.class);

log.info("订单创建成功，orderId={}, customerId={}", orderId, customerId);
```

不要使用字符串拼接，也不要记录密码、Token、身份证号等敏感数据。错误日志应包含异常对象：

```java
try {
    paymentClient.charge(command);
} catch (PaymentException exception) {
    log.error("支付失败，orderId={}", command.orderId(), exception);
    throw exception;
}
```

## 打包与部署

### 可执行 Jar

```bash
./mvnw clean verify
java -jar target/product-service-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=prod
```

### 容器镜像

Spring Boot Maven 插件可以基于 Cloud Native Buildpacks 构建 OCI 镜像，无需手写
Dockerfile：

```bash
./mvnw spring-boot:build-image \
  -Dspring-boot.build-image.imageName=product-service:1.0.0
```

运行镜像：

```bash
docker run --rm -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e SPRING_DATASOURCE_URL='jdbc:postgresql://db:5432/products' \
  -e SPRING_DATASOURCE_USERNAME='product_app' \
  -e SPRING_DATASOURCE_PASSWORD='replace-with-secret-manager-value' \
  product-service:1.0.0
```

生产部署还应设置资源限制、滚动更新策略、优雅停机、健康检查以及集中式日志和指标采集。

## 从 Spring Boot 2 迁移

迁移时不要一次跨越多个大版本。先升级到 Spring Boot 2.7 的最新补丁版本并消除弃用项，
再迁移到 3.x。

| 变化 | Spring Boot 2 | Spring Boot 3 |
| --- | --- | --- |
| Java 版本 | 常见为 Java 8/11 | 最低 Java 17 |
| Servlet API | `javax.servlet.*` | `jakarta.servlet.*` |
| JPA API | `javax.persistence.*` | `jakarta.persistence.*` |
| Validation API | `javax.validation.*` | `jakarta.validation.*` |
| Security 配置 | `WebSecurityConfigurerAdapter` | `SecurityFilterChain` Bean |
| Hibernate | Hibernate 5 | Hibernate 6 |
| Springfox | 常见但维护滞后 | 通常迁移到 springdoc-openapi 2.x |

建议迁移步骤：

1. 升级 JDK 和构建工具，确认 CI、容器基础镜像也使用 Java 17+。
2. 升级到 Spring Boot 2.7 最新版本，修复全部编译警告和弃用 API。
3. 将依赖升级到支持 Jakarta EE 10 的版本，排查无法迁移的第三方库。
4. 升级 Spring Boot 父版本，批量调整 `javax.*` 为 `jakarta.*`，但不要修改
   `javax.sql`、`javax.crypto` 等仍属于 Java SE 的包。
5. 检查 Hibernate 6 的 SQL、类型映射与方言变化。
6. 执行单元测试、集成测试、数据库迁移演练和性能回归测试。

可以临时引入 `spring-boot-properties-migrator` 帮助发现已重命名或删除的配置项，
完成迁移后应移除该依赖。

## 常见问题

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 启动时报 `UnsupportedClassVersionError` | 运行时 JDK 低于编译 JDK | 同时检查终端、IDE、Maven 与容器的 JDK |
| 找不到 Bean | 启动类包位置错误或组件未被扫描 | 将启动类放到根包，或显式配置扫描范围 |
| `javax.*` 类不存在 | 依赖仍使用旧 Java EE API | 改用 `jakarta.*` 并升级第三方依赖 |
| 请求体校验不生效 | 缺少 Validation Starter 或 `@Valid` | 添加依赖并在参数前使用 `@Valid` |
| `@Transactional` 不生效 | 类内部自调用、方法非 public 或对象不是 Bean | 让调用经过 Spring 代理并重新划分服务边界 |
| JSON 序列化失败 | 双向关联递归、懒加载或 DTO 不匹配 | 使用响应 DTO，不直接序列化复杂实体图 |
| 数据库连接耗尽 | 慢查询、事务过长或连接池配置不合理 | 查指标与慢 SQL，缩短事务并重新计算池大小 |
| Actuator 端点返回 404 | 端点未暴露 | 检查 `management.endpoints.web.exposure.include` |
| 修改配置未生效 | 被高优先级配置覆盖 | 检查环境变量、命令行参数和激活的 Profile |

## 工程实践清单

- 使用构造器注入，避免字段注入。
- Controller 只处理 HTTP 协议和参数转换，业务规则放在 Service。
- 使用请求/响应 DTO，避免直接暴露 JPA Entity。
- 使用 Jakarta Validation 在系统边界校验输入。
- 数据库结构使用 Flyway 或 Liquibase 版本化管理。
- 密钥来自 Secret Manager 或运行环境，不进入 Git。
- 为核心业务编写单元测试，为数据库和消息系统编写真实依赖的集成测试。
- 启用 Actuator 健康检查、指标和优雅停机，并限制管理端点访问。
- 依赖版本优先交给 Spring Boot BOM 管理，定期升级补丁版本并关注安全公告。

## 参考资料

- [Spring Boot 3.5 Reference Documentation](https://docs.spring.io/spring-boot/3.5/reference/)
- [Spring Boot System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html)
- [Spring Initializr](https://start.spring.io/)
- [Spring Boot Actuator Endpoints](https://docs.spring.io/spring-boot/3.5/reference/actuator/endpoints.html)
- [Spring Boot Testing](https://docs.spring.io/spring-boot/3.5/reference/testing/index.html)
- [[spring5|Spring 核心]]
- [[spring-mvc|Spring MVC]]
- [[spring-boot2|Spring Boot 2]]
