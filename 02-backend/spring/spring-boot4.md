---
title: Spring Boot 4 使用指南与发展现状
description: 介绍 Spring Boot 4 的发布时间、发展现状、核心变化，并通过完整示例讲解项目创建、REST API、测试、监控、部署与升级
tags:
  - java
  - spring-boot
  - backend
date: 2026-08-04
aliases:
  - Spring Boot 4
---

# Spring Boot 4 使用指南与发展现状

Spring Boot 4 是建立在 Spring Framework 7 之上的新一代 Spring Boot，重点不是改变
Spring Boot 的基本编程模型，而是为未来数年的 Java 应用提供新的技术基线：更细粒度的模块、Jakarta EE 11、Jackson 3、JSpecify 空安全、API 版本管理和更完善的 HTTP 客户端。

本文分为两部分：先回答 Spring Boot 4 何时发布、目前发展到什么阶段、是否适合使用，
再通过一个可运行的 REST API 介绍 Spring Boot 4.1 的日常开发方式。

## 发布时间与版本历程

Spring Boot 4 经历了里程碑版本和候选版本验证，于 **2025 年 11 月 20 日**发布
`4.0.0` 正式版。它与 Spring Framework 7、Spring Security 7 等 Spring 生态的大版本
一起构成新一代 Spring 技术栈。

截至 **2026 年 8 月 4 日**，官方文档列出的 Spring Boot 4 稳定版本为：

| 版本线 | 发布时间或状态 | 定位 |
| --- | --- | --- |
| 4.0.0 | 2025-11-20 正式发布 | Spring Boot 4 首个 GA 版本 |
| 4.0.7 | 稳定维护版本 | 4.0 系列的错误与安全修复 |
| 4.1.0 | 2026-06-10 正式发布 | 当前 4.x 功能主线 |
| 4.2.0-SNAPSHOT | 开发中 | 下一条功能版本线，不能用于生产 |

> **说明**：GA 是 General Availability 的缩写，表示正式可用版本，不是预览版。
> 本文以当前稳定的 `4.1.0` 为例。版本状态会变化，实际项目应再次查看官方文档。

## 当前发展现状

### 核心框架已经稳定

Spring Boot 4 已经完成从 4.0 到 4.1 的一次功能迭代，并持续发布维护版本。
Spring Framework、Spring Security、Spring Data、Spring Batch、Spring Kafka 等核心项目均已发布与它配套的大版本。因此，Spring Boot 4 已经不是试验性的里程碑版本，适合经过兼容性评估的新项目投入生产。

Spring Boot 4.1 新增或增强的能力包括：

- Spring gRPC 的客户端、服务端与测试支持。
- HTTP 客户端 SSRF 防护能力。
- OpenTelemetry、指标和异步上下文传播增强。
- Jackson 配置与自定义能力增强。
- Spring Batch MongoDB、Redis Listener 等自动配置。
- HTTP 客户端、日志轮转、Docker Compose 和 Testcontainers 的持续改进。

### 生态处于迁移与普及阶段

“Spring Boot 4 已稳定”不等于“所有第三方库都已兼容”。使用下面这些组件时应逐项检查：

- 第三方 Spring Boot Starter 是否发布了明确支持 Boot 4 的主版本。
- Spring Cloud、Spring AI、工作流引擎、API 文档和代码生成工具的兼容矩阵。
- 依赖是否支持 Jakarta EE 11、Servlet 6.1、Jackson 3 或 JSpecify。
- 公司内部 Starter 是否依赖已经移动的 Spring Boot 包或自动配置实现细节。
- APM Agent、字节码增强、Native Image 和应用服务器是否支持当前组合。

对只使用 Spring 官方 Starter、JDBC/JPA、Redis、Kafka 和标准 Web 技术的新项目，
迁移阻力通常较小。依赖大量内部 Starter、旧应用服务器或停更组件的系统，应先做验证项目。

### 现在应该选择 Spring Boot 3 还是 4

| 场景 | 建议 |
| --- | --- |
| 全新项目，依赖均支持 Boot 4 | 优先评估 Spring Boot 4.1 |
| 新项目，但关键 Starter 尚未兼容 | 使用受支持的 Boot 3.5，并制定升级计划 |
| 已稳定运行的 Boot 3 系统 | 不必只为追新立即升级，先核对收益和兼容性 |
| 准备从 Boot 2 升级 | 先升级到 2.7，再到 3.5，最后评估 4.x |
| 需要 Java 25、API 版本管理或 Jackson 3 | Spring Boot 4 更合适 |

简而言之：Spring Boot 4 已经可以用于生产，但大版本升级的决定应由依赖兼容性、维护周期和业务收益驱动，而不是只看版本号。

## Spring Boot 4 的核心变化

### 技术基线

| 项目 | Spring Boot 4.1 要求或默认值 |
| --- | --- |
| Java | 最低 17，最高兼容到 26 |
| 推荐 JDK | Java 21 LTS 或 Java 25 LTS |
| Spring Framework | 7.0.8 或更高兼容版本 |
| Jakarta EE | Jakarta EE 11 |
| Servlet | 6.1 |
| 默认 Servlet 容器 | Tomcat 11 |
| 可选 Servlet 容器 | Jetty 12.1 |
| Maven | 3.6.3+，推荐 3.9+ |
| Gradle | 8.14+ 或 9.x |
| GraalVM Native Image | GraalVM 25+ |

Spring Boot 4 仍然保留 Java 17 兼容性，但新项目建议使用当前 LTS JDK。
某些第三方技术可能有更高要求，例如特定版本的 jOOQ 需要 Java 21。

### 更细粒度的模块化设计

Spring Boot 4 将原先较大的模块拆成更聚焦的模块，并为多数技术提供主 Starter 和测试
Starter。这样可以减少无关自动配置进入类路径，但升级旧项目时可能需要补充依赖。

常见依赖变化：

| Spring Boot 3 常见依赖 | Spring Boot 4 推荐依赖 |
| --- | --- |
| `spring-boot-starter-web` | `spring-boot-starter-webmvc` |
| `spring-boot-starter-test` | 按技术选择 `*-test` Starter |
| 直接使用 `flyway-core` | `spring-boot-starter-flyway` |
| 直接使用 `liquibase-core` | `spring-boot-starter-liquibase` |
| `spring-boot-starter-aop` | `spring-boot-starter-aspectj` |

旧的 `spring-boot-starter-web` 在 4.x 中暂时可用，但已经弃用。新项目直接使用
`spring-boot-starter-webmvc`，不要主动积累下一次升级要处理的弃用项。

### Jackson 3 成为默认 JSON 实现

Jackson 3 是 Spring Boot 4 的默认 JSON 库。其 Java 包名从 Jackson 2 的
`com.fasterxml.jackson.*` 迁移到 `tools.jackson.*`。仅使用 `@RestController` 和 DTO的代码通常无需调整；直接注册 Jackson Module、自定义序列化器或操作`ObjectMapper`的代码需要重点检查。

Spring Boot 4 暂时提供 Jackson 2 兼容模块，但它已经弃用，只适合作为迁移过渡方案。

### JSpecify 空安全

Spring Boot 4 和新一代 Spring 项目使用 JSpecify 描述参数、返回值与类型参数的可空性。
这能改善 IDE、静态分析器和 Kotlin 对空值的判断。启用严格空安全检查的项目升级后可能出现
新的编译告警或错误，应把它们视为 API 契约变化逐项处理。

### API 版本管理与 HTTP Service Client

Spring Framework 7 为 Spring MVC 和 WebFlux 增加内置 API 版本管理，可以从请求头、
查询参数、媒体类型或 URL 路径解析版本。Spring Boot 4 还增强了声明式 HTTP Service
Client，可按组配置基础地址、超时、SSL 与默认请求头。

### 被移除或变化较大的能力

- `Undertow` 因未满足 Servlet 6.1 基线，不再作为 Spring Boot 4 嵌入式容器。
- Spring Boot 3 中已经弃用的类、方法和配置项在 4.0 中被清理。
- 默认 Web 技术、测试和数据访问相关类可能移动到新的模块包名。
- `@SpringBootTest` 不再自动提供 MockMvc，需要额外使用 `@AutoConfigureMockMvc`。
- Flyway、Liquibase 等功能应使用 Spring Boot 4 提供的专用 Starter。
- 日志文件默认字符集统一为 UTF-8。
- Actuator 的 liveness 和 readiness 健康组默认启用。

## 创建第一个 Spring Boot 4 项目

### 环境准备

本文使用 Java 21 和 Maven。先检查环境：

```bash
java -version
mvn -version
```

可以在 [Spring Initializr](https://start.spring.io/) 中选择 Spring Boot 4.1.x、Java 21、
Maven，并加入 Spring Web、Validation、Spring Data JPA、H2 和 Actuator。

### Maven 配置

以下 `pom.xml` 使用 Spring Boot 4 的新 Starter 命名：

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
        <version>4.1.0</version>
        <relativePath/>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>todo-service</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>todo-service</name>

    <properties>
        <java.version>21</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-webmvc</artifactId>
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
            <artifactId>spring-boot-starter-webmvc-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa-test</artifactId>
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

专用测试 Starter 会传递引入通用的 Spring Boot 测试支持、JUnit、AssertJ 和 Mockito，
因此不必再重复声明 `spring-boot-starter-test`。

### 项目结构

```text
src/
├── main/
│   ├── java/com/example/todo/
│   │   ├── TodoApplication.java
│   │   └── todo/
│   │       ├── TodoController.java
│   │       ├── TodoEntity.java
│   │       ├── TodoNotFoundException.java
│   │       ├── TodoRepository.java
│   │       ├── TodoRequest.java
│   │       ├── TodoResponse.java
│   │       └── TodoService.java
│   └── resources/application.yml
└── test/java/com/example/todo/todo/
    └── TodoControllerTest.java
```

启动类放在根包中：

```java
package com.example.todo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class TodoApplication {

    public static void main(String[] args) {
        SpringApplication.run(TodoApplication.class, args);
    }
}
```

运行项目：

```bash
./mvnw spring-boot:run
```

如果项目没有 Maven Wrapper，可使用 `mvn spring-boot:run`。

## 配置管理

创建 `src/main/resources/application.yml`：

```yaml
spring:
  application:
    name: todo-service
  datasource:
    url: jdbc:h2:mem:todo;MODE=PostgreSQL
    username: sa
    password: ""
  jpa:
    hibernate:
      ddl-auto: create-drop
    open-in-view: false

server:
  port: 8080
  shutdown: graceful

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: when-authorized
```

开发、测试和生产环境的差异使用 Profile 管理，例如 `application-prod.yml`：

```yaml
spring:
  datasource:
    url: ${SPRING_DATASOURCE_URL}
    username: ${SPRING_DATASOURCE_USERNAME}
    password: ${SPRING_DATASOURCE_PASSWORD}
  jpa:
    hibernate:
      ddl-auto: validate

server:
  shutdown: graceful
```

启动生产 Profile：

```bash
java -jar target/todo-service-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=prod
```

密码、Token 和私钥必须通过 Secret Manager 或运行环境注入，不能提交到 Git。

## 开发 REST API

下面实现待办事项的创建、列表查询和按 ID 查询。示例使用 DTO 作为接口契约，避免直接序列化 JPA Entity。

### 持久化实体

```java
package com.example.todo.todo;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "todo_item")
public class TodoEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String title;
    private boolean completed;

    protected TodoEntity() {
        // JPA 需要无参构造方法。
    }

    public TodoEntity(String title) {
        this.title = title;
        this.completed = false;
    }

    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public boolean isCompleted() {
        return completed;
    }
}
```

### Repository 与 DTO

```java
package com.example.todo.todo;

import org.springframework.data.jpa.repository.JpaRepository;

public interface TodoRepository extends JpaRepository<TodoEntity, Long> {
}
```

```java
package com.example.todo.todo;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record TodoRequest(
        @NotBlank(message = "标题不能为空")
        @Size(max = 200, message = "标题不能超过 200 个字符")
        String title) {
}
```

```java
package com.example.todo.todo;

public record TodoResponse(Long id, String title, boolean completed) {

    public static TodoResponse from(TodoEntity entity) {
        return new TodoResponse(entity.getId(), entity.getTitle(), entity.isCompleted());
    }
}
```

### Service 与事务

```java
package com.example.todo.todo;

import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TodoService {

    private final TodoRepository repository;

    public TodoService(TodoRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<TodoResponse> findAll() {
        return repository.findAll().stream()
                .map(TodoResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public TodoResponse findById(Long id) {
        return repository.findById(id)
                .map(TodoResponse::from)
                .orElseThrow(() -> new TodoNotFoundException(id));
    }

    @Transactional
    public TodoResponse create(TodoRequest request) {
        TodoEntity saved = repository.save(new TodoEntity(request.title()));
        return TodoResponse.from(saved);
    }
}
```

### Controller

```java
package com.example.todo.todo;

import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@RestController
@RequestMapping("/api/todos")
public class TodoController {

    private final TodoService service;

    public TodoController(TodoService service) {
        this.service = service;
    }

    @GetMapping
    public List<TodoResponse> findAll() {
        return service.findAll();
    }

    @GetMapping("/{id}")
    public TodoResponse findById(@PathVariable Long id) {
        return service.findById(id);
    }

    @PostMapping
    public ResponseEntity<TodoResponse> create(
            @Valid @RequestBody TodoRequest request) {
        TodoResponse saved = service.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(saved.id())
                .toUri();
        return ResponseEntity.created(location).body(saved);
    }
}
```

测试接口：

```bash
curl -i -X POST http://localhost:8080/api/todos \
  -H 'Content-Type: application/json' \
  -d '{"title":"学习 Spring Boot 4"}'

curl http://localhost:8080/api/todos
curl http://localhost:8080/api/todos/1
```

### 统一异常处理

```java
package com.example.todo.todo;

public class TodoNotFoundException extends RuntimeException {

    public TodoNotFoundException(Long id) {
        super("待办事项不存在，id=" + id);
    }
}
```

```java
package com.example.todo.todo;

import java.net.URI;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(TodoNotFoundException.class)
    ProblemDetail handleNotFound(TodoNotFoundException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND, exception.getMessage());
        problem.setTitle("资源不存在");
        problem.setType(URI.create("https://example.com/problems/todo-not-found"));
        return problem;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ProblemDetail handleValidation(MethodArgumentNotValidException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "请求参数校验失败");
        List<String> errors = exception.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .toList();
        problem.setTitle("参数错误");
        problem.setProperty("errors", errors);
        return problem;
    }
}
```

`ProblemDetail` 使用标准化的问题详情格式，客户端可以稳定读取 `status`、`title`、
`detail` 和自定义属性。

## 使用 API 版本管理

Spring Framework 7 可以通过请求头管理 API 版本。先实现 MVC 配置：

```java
package com.example.todo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ApiVersionConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration(proxyBeanMethods = false)
public class WebConfiguration implements WebMvcConfigurer {

    @Override
    public void configureApiVersioning(ApiVersionConfigurer configurer) {
        configurer.useRequestHeader("API-Version");
    }
}
```

然后为映射声明版本。下面的 Controller 可以直接运行，用于观察不同版本的响应结构：

```java
package com.example.todo.todo;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/todos/summary")
public class TodoSummaryController {

    @GetMapping(version = "1.0")
    public Map<String, Long> summaryV1() {
        return Map.of("total", 12L);
    }

    @GetMapping(version = "2.0+")
    public Map<String, Long> summaryV2() {
        return Map.of("total", 12L, "completed", 8L);
    }
}
```

调用时携带版本请求头：

```bash
curl -H 'API-Version: 1.0' http://localhost:8080/api/todos/summary
curl -H 'API-Version: 2.0' http://localhost:8080/api/todos/summary
```

内置能力还支持查询参数、媒体类型和 URL 路径版本，并可返回 `Deprecation`、`Sunset`
等响应头。版本策略一旦选定应保持一致，不要在同一 API 中混用多种方式。

## 调用远程 REST 服务

同步 MVC 应用优先使用 `RestClient` 或声明式 HTTP Service Client。添加依赖：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-restclient</artifactId>
</dependency>
```

声明客户端接口：

```java
package com.example.todo.client;

import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.service.annotation.GetExchange;

public interface UserClient {

    @GetExchange("/users/{id}")
    UserResponse findById(@PathVariable Long id);
}

record UserResponse(Long id, String name) {
}
```

在启动类上导入并分组：

```java
@SpringBootApplication
@ImportHttpServices(group = "user-service", types = UserClient.class)
public class TodoApplication {

    public static void main(String[] args) {
        SpringApplication.run(TodoApplication.class, args);
    }
}
```

其中 `@ImportHttpServices` 的导入路径是：

```java
import org.springframework.web.service.registry.ImportHttpServices;
```

通过配置设置地址和超时，不在注解中硬编码环境地址：

```yaml
spring:
  http:
    clients:
      connect-timeout: 1s
    serviceclient:
      user-service:
        base-url: https://users.example.com
        connect-timeout: 2s
        read-timeout: 3s
```

如果 URL 来自用户输入，还应使用 Spring Boot 4.1 的 `InetAddressFilter` 或网关策略防止
SSRF，禁止访问回环地址、云元数据地址和内部管理网段。

## 数据库迁移

生产环境不应使用 Hibernate 自动修改表结构。Spring Boot 4 使用 Flyway Starter：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-flyway</artifactId>
</dependency>
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-database-postgresql</artifactId>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <scope>runtime</scope>
</dependency>
```

Flyway Starter 支持 H2 等内存或文件数据库；PostgreSQL、MySQL 等数据库还需要各自的
Flyway 数据库模块。

创建 `src/main/resources/db/migration/V1__create_todo_item.sql`：

```sql
CREATE TABLE todo_item (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE
);
```

生产环境设置 `spring.jpa.hibernate.ddl-auto=validate`，由 Flyway 执行版本化迁移。
已经在任何共享环境执行过的迁移脚本都不能修改，应新增下一个版本脚本。

## 测试

Spring Boot 4 将测试支持拆分到专用模块，部分注解的包名与 Boot 3 不同。

### MVC 切片测试

```java
package com.example.todo.todo;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(TodoController.class)
class TodoControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TodoService service;

    @Test
    void shouldListTodos() throws Exception {
        when(service.findAll()).thenReturn(List.of(
                new TodoResponse(1L, "学习 Spring Boot 4", false)));

        mockMvc.perform(get("/api/todos"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(1))
                .andExpect(jsonPath("$[0].title").value("学习 Spring Boot 4"));
    }
}
```

注意 Boot 4 的导入路径是
`org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest`，不要继续复制 Boot 3 的
`org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest`。

### 完整应用测试

`@SpringBootTest` 不再隐式启用 MockMvc。如果完整上下文测试需要 MockMvc，应显式添加：

```java
@SpringBootTest
@AutoConfigureMockMvc
class TodoApplicationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointShouldBeAvailable() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk());
    }
}
```

`AutoConfigureMockMvc` 的 Boot 4 导入路径为：

```java
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
```

运行测试：

```bash
./mvnw test
```

数据库、Redis、Kafka 和 RabbitMQ 集成测试优先使用 Testcontainers，避免内存替代品与
生产环境行为不同。

## Actuator 与可观测性

检查应用健康状态：

```bash
curl http://localhost:8080/actuator/health
curl http://localhost:8080/actuator/health/liveness
curl http://localhost:8080/actuator/health/readiness
```

Spring Boot 4 默认启用 `liveness` 和 `readiness` 健康组，但 Web 暴露范围仍应保持最小化。
需要 Prometheus 时添加对应注册表，并只暴露必要端点：

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  endpoint:
    health:
      show-details: when-authorized
```

不要把 `env`、`configprops`、`heapdump` 等端点直接暴露到公网。管理端点应通过
Spring Security、管理网络、网关访问策略或独立管理端口保护。

Spring Boot 4.1 进一步增强 OpenTelemetry 自动配置。选择观测方案时应统一日志、指标、
Trace 的关联 ID 和导出协议，避免同时引入多套互不关联的 Agent 与 SDK。

## 打包与部署

生成并运行可执行 Jar：

```bash
./mvnw clean verify
java -jar target/todo-service-0.0.1-SNAPSHOT.jar
```

使用 Cloud Native Buildpacks 构建 OCI 镜像：

```bash
./mvnw spring-boot:build-image \
  -Dspring-boot.build-image.imageName=todo-service:1.0.0
```

```bash
docker run --rm -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e SPRING_DATASOURCE_URL='jdbc:postgresql://db:5432/todo' \
  -e SPRING_DATASOURCE_USERNAME='todo_app' \
  -e SPRING_DATASOURCE_PASSWORD='replace-with-secret-value' \
  todo-service:1.0.0
```

生产部署还应配置资源限制、启动探针、就绪探针、滚动更新、优雅停机、数据库迁移策略
和可回滚的镜像版本。

## 从 Spring Boot 3.5 升级到 4

不要直接从早期 Boot 3 小版本升级。先升级到最新 `3.5.x`，清理所有弃用 API，确保测试
通过，再开始 Boot 4 迁移。

### 推荐步骤

1. 将 JDK、Maven/Gradle、CI 和容器基础镜像升级到受支持版本。
2. 把应用升级到最新 Spring Boot 3.5.x，并消除弃用警告。
3. 盘点 Spring Cloud、数据库驱动、Starter、APM Agent 和内部框架的兼容性。
4. 将父版本改为 Spring Boot 4，临时使用 Classic Starter 恢复较完整的类路径。
5. 按编译错误修复包名和 API，重点检查测试、持久化、Jackson 与自动配置扩展。
6. 将 Classic Starter 拆回精确的主 Starter 和测试 Starter。
7. 运行单元测试、真实依赖集成测试、数据库迁移演练与性能回归。
8. 先灰度发布，观察错误率、延迟、连接池、GC、日志和 Trace，再扩大流量。

### Classic Starter 过渡方案

大型应用可以临时使用：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-classic</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test-classic</artifactId>
    <scope>test</scope>
</dependency>
```

这只是一种降低首次迁移难度的中间状态。验证应用可运行后，应逐步替换为准确的 Starter，发挥 Boot 4 模块化的价值。

### 配置项迁移工具

可以临时添加：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-properties-migrator</artifactId>
    <scope>runtime</scope>
</dependency>
```

它会在启动时报告被重命名或删除的配置。完成迁移后必须移除，不能把它当作长期兼容层。

### 升级重点检查清单

- 将已弃用的 `spring-boot-starter-web` 改为 `spring-boot-starter-webmvc`。
- 使用 Flyway/Liquibase 专用 Starter，不再只引入第三方核心包。
- 更新 Boot 4 中已经移动的测试注解和自动配置类导入路径。
- 检查 Jackson 2 自定义代码并迁移到 Jackson 3。
- 检查 `@SpringBootTest` 是否依赖过去隐式提供的 MockMvc。
- 如果使用 Undertow，迁移到 Tomcat 11、Jetty 12.1 或调整架构。
- 检查 JSpecify 空安全对 Java 静态分析和 Kotlin 编译的影响。
- 检查自定义 Starter 是否读取 Spring Boot 内部类或旧包名。
- 对 Hibernate、数据库方言、SQL 和实体映射执行回归测试。

## 常见问题

| 问题 | 原因 | 解决方式 |
| --- | --- | --- |
| `spring-boot-starter-web` 出现弃用警告 | Boot 4 调整 Starter 命名 | 改用 `spring-boot-starter-webmvc` |
| 找不到 `WebMvcTest` | 测试模块和包名已调整 | 加入 WebMVC Test Starter 并更新 import |
| Flyway 没有自动运行 | 只引入了第三方核心包 | 改用 `spring-boot-starter-flyway` |
| Jackson 自定义代码无法编译 | 默认升级到 Jackson 3 | 将相关 API 迁移到 `tools.jackson.*` |
| Undertow Starter 不存在 | Boot 4 不再支持 Undertow | 使用 Tomcat 或 Jetty |
| `@SpringBootTest` 中没有 MockMvc | Boot 4 不再隐式配置 | 添加 `@AutoConfigureMockMvc` |
| 第三方 Starter 启动失败 | 仍面向 Boot 3 或旧 Jakarta API | 升级、替换或暂缓迁移 |
| 出现新的空安全告警 | Spring 生态使用 JSpecify | 按新的可空契约修复代码 |
| API 版本请求返回 400 | 缺少版本或版本不受支持 | 检查版本解析策略和映射声明 |

## 使用建议总结

- 新项目优先使用 Spring Boot 4.1 的新 Starter 名称和模块结构。
- Java 21 是稳妥选择，需要新 JVM 能力时可评估 Java 25。
- 不要照搬 Boot 3 的测试注解包名、Flyway 依赖和 Jackson 自定义代码。
- 核心 Spring 生态已稳定，但每个第三方 Starter 都要验证兼容版本。
- 生产项目锁定具体补丁版本，定期跟进安全公告并升级维护版本。
- 老项目先升级到 Boot 3.5，再通过测试驱动的方式迁移到 Boot 4。

## 参考资料

- [Spring Boot 4.0.0 发布公告](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)
- [Spring Boot 4.1.0 发布公告](https://spring.io/blog/2026/06/10/spring-boot-4/)
- [Spring Boot 4.1 官方文档](https://docs.spring.io/spring-boot/4.1/reference/)
- [Spring Boot 4.1 系统要求](https://docs.spring.io/spring-boot/4.1/system-requirements.html)
- [Spring Boot 4.0 迁移指南](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide)
- [Spring Boot 4.1 Release Notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes)
- [Spring Framework 7 API 版本管理](https://docs.spring.io/spring-framework/reference/web/webmvc-versioning.html)
- [[spring-boot3|Spring Boot 3 使用指南]]
- [[spring-mvc|Spring MVC]]
