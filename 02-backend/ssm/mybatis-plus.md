---
title: MyBatis-Plus 核心用法与实践
description: MyBatis-Plus 的 CRUD、实体映射、条件构造器、分页、逻辑删除和乐观锁用法
tags:
  - java
  - mybatis
  - persistence
date: 2026-11-16
---

# MyBatis-Plus 核心用法与实践

## 概述

MyBatis-Plus 在 [[mybatis|MyBatis]] 基础上提供通用 CRUD、条件构造器和插件，减少简单持久化操作的重复代码。
复杂 SQL 仍可使用 MyBatis Mapper XML 编写。使用这些封装时，仍需关注事务、SQL、索引和并发更新。

## 前置知识

- [[java-se|Java SE 核心语法]]：泛型、Lambda 和方法引用。
- [[mybatis|MyBatis 核心原理与实践]]：Mapper、参数绑定和事务。
- [[mysql|MySQL]]：主键、索引及分页查询。

## 快速入门：Spring Boot 与 H2

下面是一个可独立运行的示例，使用 Java 17、Spring Boot 3.3.5 和 MyBatis-Plus 3.5.7。
这些版本用于复现示例；其他 Spring Boot 主版本应选择对应的 starter，不要重复引入不兼容的 MyBatis starter。

```text
mybatis-plus-demo/
├── pom.xml
└── src/main/java/demo/DemoApplication.java
```

`pom.xml`：

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.5</version>
    <relativePath/>
  </parent>
  <groupId>demo</groupId>
  <artifactId>mybatis-plus-demo</artifactId>
  <version>1.0.0</version>
  <properties><java.version>17</java.version></properties>
  <dependencies>
    <dependency>
      <groupId>com.baomidou</groupId>
      <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
      <version>3.5.7</version>
    </dependency>
    <dependency>
      <groupId>com.h2database</groupId>
      <artifactId>h2</artifactId>
      <scope>runtime</scope>
    </dependency>
  </dependencies>
  <build><plugins><plugin>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-maven-plugin</artifactId>
  </plugin></plugins></build>
</project>
```

`src/main/java/demo/DemoApplication.java`：

```java
package demo;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }

    @Bean
    CommandLineRunner run(JdbcTemplate jdbc, CustomerMapper mapper) {
        return args -> {
            // 示例每次启动使用内存库；生产环境使用迁移工具管理表结构。
            jdbc.execute("CREATE TABLE customer (id BIGINT PRIMARY KEY, name VARCHAR(80))");
            Customer customer = new Customer();
            customer.setId(1L);
            customer.setName("张三");
            mapper.insert(customer);
            var query = new LambdaQueryWrapper<Customer>()
                    .eq(Customer::getName, "张三");
            mapper.selectList(query).forEach(item -> System.out.println(item.getName()));
        };
    }

    @Mapper
    public interface CustomerMapper extends BaseMapper<Customer> {}

    @TableName("customer")
    public static class Customer {
        @TableId(type = IdType.INPUT)
        private Long id;
        private String name;
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }
}
```

在项目根目录运行：

```bash
mvn -q spring-boot:run
```

Spring Boot 使用内嵌 H2 自动配置数据源，程序应输出 `张三` 后退出。
`IdType.INPUT` 表示示例显式提供主键；真实业务应根据表结构与 ID 生成方案选型。

## 基础 CRUD 与 Service

`BaseMapper<T>` 提供按实体的插入、更新、删除与查询。Mapper 执行数据库操作，事务通常由服务层管理。

| 层次 | 常见方法 | 返回与注意事项 |
|------|----------|----------------|
| `BaseMapper<T>` | `insert`、`deleteById`、`updateById`、`selectById` | 写方法通常返回受影响行数；查询不存在时可能返回 `null` |
| `IService<T>` / `ServiceImpl<M, T>` | `save`、`remove`、`update`、`get`、`list`、`page` | 在 Mapper 上提供服务层封装；`getOne` 遇多行时需按版本与参数理解行为 |

Spring 应用中可以定义领域服务：

```java
public interface CustomerService extends IService<Customer> {
}

@Service
public class CustomerServiceImpl extends ServiceImpl<CustomerMapper, Customer>
        implements CustomerService {
}
```

此片段假定实体、Mapper、Spring 注解和对应 MyBatis-Plus 类型已导入。
它不会自动解决业务事务：涉及多个写操作时，应在合适的服务方法设置 Spring 事务边界。

## 实体与常用注解

| 注解 | 作用 | 示例或注意事项 |
|------|------|----------------|
| `@TableName` | 指定实体对应的表 | `@TableName("customer")`；也可配置统一表前缀 |
| `@TableId` | 指定主键列及策略 | `IdType.AUTO` 依赖数据库自增；`ASSIGN_ID` 使用配置的 ID 生成器 |
| `@TableField` | 控制普通字段映射 | `@TableField("customer_name")`；`exist = false` 表示非表字段 |
| `@TableLogic` | 标记逻辑删除字段 | 删除操作通常转换为更新，并在生成的查询中追加未删除条件 |
| `@Version` | 标记乐观锁版本字段 | 需注册乐观锁拦截器，且仅支持文档列出的操作和类型 |

`@TableField` 不是逻辑删除注解；逻辑删除需要 `@TableLogic` 或相应全局配置。
例如下面是实体字段片段，数据库需有对应列，并为新记录提供未删除状态及初始版本：

```java
@TableId(type = IdType.AUTO)
private Long id;
@TableField("customer_name")
private String name;
@TableLogic(value = "0", delval = "1")
private Integer deleted;
@Version
private Integer version;
```

自定义 XML 或手写 SQL 不能假定自动附加逻辑删除条件，需自行检查 SQL。
逻辑删除不替代数据库权限、审计及唯一索引设计。

## 条件构造器

| 类型 | 常用场景 |
|------|----------|
| `QueryWrapper` | 用列名字符串构造查询 |
| `LambdaQueryWrapper` | 使用 getter 方法引用构造查询，减少手写列名 |
| `UpdateWrapper` | 用列名字符串构造更新条件和赋值 |
| `LambdaUpdateWrapper` | 使用方法引用构造更新条件和赋值 |

例如，在服务或 Mapper 调用处按条件查询：

```java
LambdaQueryWrapper<Customer> query = new LambdaQueryWrapper<Customer>()
        .eq(name != null && !name.isBlank(), Customer::getName, name)
        .orderByAsc(Customer::getId);
List<Customer> customers = customerMapper.selectList(query);
```

条件为 `false` 时，该条件不会加入 SQL；若全部过滤条件被省略，可能查询全表。
更新或删除前应单独验证必要条件。不要把客户端传入的列名、SQL 片段直接传给 `last`、`apply`
或字符串列名接口；动态排序应由服务端白名单映射。Wrapper 应按操作创建，不应作为远程请求对象传输。

## 分页插件

分页需要注册 `MybatisPlusInterceptor` 和 `PaginationInnerInterceptor`。
下面为 MySQL 配置，其他数据库需调整 `DbType`：

```java
@Configuration
@MapperScan("com.example.customer.mapper")
public class MybatisPlusConfig {
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        return interceptor;
    }
}
```

这是配置片段，需要导入 Spring、MyBatis 和 MyBatis-Plus 对应类型，并将扫描包替换为项目实际路径。
**从 MyBatis-Plus 3.5.9 起**，分页插件所需解析器拆分为独立依赖 `mybatis-plus-jsqlparser`；
示例依赖版本为 3.5.7，不需要单独声明该模块。升级时参照
[官方分页插件文档](https://baomidou.com/en/plugins/pagination/)选择与主库一致的版本。
存在多个内部拦截器时，官方建议分页拦截器放在最后。

```java
Page<Customer> page = new Page<>(1, 10); // 页码从 1 开始
Page<Customer> result = customerMapper.selectPage(page, query);
System.out.println("总记录数：" + result.getTotal());
result.getRecords().forEach(customer -> System.out.println(customer.getName()));
```

分页默认可能执行总数查询；复杂关联 SQL 应检查生成的 count SQL 和结果是否符合预期。
限制外部传入的页大小，并结合索引评估深分页性能。PageHelper 是另一个分页方案，
不要在同一查询链中无意叠加两个分页拦截器。

## 逻辑删除与乐观锁

配置逻辑删除后，使用框架生成的删除方法会更新删除标记；应确保默认值和已有数据与查询条件一致。
逻辑删除的数据仍占用存储，也可能继续影响唯一索引。

乐观锁用于检测并发覆盖：读取带版本号的实体，更新时框架在支持的方法中比较旧版本并递增版本；
如果更新行数为 0，调用方应按业务决定重试或返回冲突。

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
    interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());
    interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
    return interceptor;
}
```

这是与前面分页配置**二选一的完整拦截器组合**，不要同时注册两个同名 Bean。
实体需有 `@Version` 字段，更新前需要取得当前版本。批量或自定义 SQL 不应假设自动应用乐观锁；
当使用带 Wrapper 的更新方法时，注意官方要求的 Wrapper 不能复用。
详见[乐观锁文档](https://baomidou.com/en/plugins/optimistic-locker/)。

## 日志与排错

开发环境可临时使用标准输出查看 SQL：

```yaml
mybatis-plus:
  configuration:
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl
```

生产环境优先接入项目日志框架，并根据敏感数据与日志量配置级别。

| 现象 | 常见原因 | 排查方向 |
|------|----------|----------|
| Mapper 未注入 | 扫描路径错误或缺少注解 | 检查 `@MapperScan`、`@Mapper` 和 Spring 容器 |
| 表或字段不存在 | 命名策略与数据库不一致 | 检查 `@TableName`、`@TableField` 和实际表结构 |
| 分页不起作用 | 未注册分页拦截器或缺少解析器依赖 | 检查版本、依赖、插件顺序和生成的 SQL |
| 更新行数为 0 | 记录不存在、逻辑删除或乐观锁冲突 | 检查实际条件、删除标记和版本号 |
| 查询出现 N+1 或性能差 | 逐条查询、索引不足或深分页 | 查看 SQL、执行计划和请求次数 |

## 与相关概念的关系

- [[mybatis|MyBatis]]：MyBatis-Plus 建立在其 Mapper、SQL 映射和事务机制之上。
- [[ssm-integration|SSM 整合]]：了解 Spring 事务和 Mapper 注册。
- [[mysql|MySQL]]：通过索引和执行计划分析持久化性能。

## 参考

- [MyBatis-Plus 快速开始](https://baomidou.com/en/getting-started/)
- [持久层接口](https://baomidou.com/en/guides/data-interface/)
- [条件构造器](https://baomidou.com/en/guides/wrapper/)
- [分页插件](https://baomidou.com/en/plugins/pagination/)
- [逻辑删除](https://baomidou.com/en/guides/logic-delete/)
- [乐观锁插件](https://baomidou.com/en/plugins/optimistic-locker/)
