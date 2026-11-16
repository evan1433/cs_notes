---
title: MyBatis 核心原理与实践
description: MyBatis 核心对象、XML 配置与映射、动态 SQL、事务、缓存及插件机制的入门与排错指南
tags:
  - java
  - mybatis
  - persistence
date: 2026-11-16
---

# MyBatis 核心原理与实践

## 概述

MyBatis 是 SQL 映射框架：开发者编写 SQL，框架负责参数绑定、语句执行和结果映射，减少重复的 JDBC 代码。
它适合需要控制查询语句、处理复杂查询的应用；表结构、SQL 性能和事务边界仍由开发者负责设计。
本文以 MyBatis 3 为范围，先用独立 Java 程序理解执行过程，再说明 SSM 集成时需要注意的边界。

## 前置知识

- [[java-se|Java SE 核心语法]]：接口、泛型、异常处理和 try-with-resources。
- [[mysql|MySQL]]：SQL、主键、索引和数据库事务。
- [[ssm-integration|SSM 整合]]：了解 Spring 管理对象与事务的职责。

## 核心对象与执行过程

```text
配置文件 / Java 配置
        ↓
SqlSessionFactoryBuilder → SqlSessionFactory
                                  ↓ openSession()
                             SqlSession
                                  ↓ getMapper()
                             Mapper 代理
                                  ↓
                    Executor → JDBC → 数据库
                                  ↓
                          结果映射为 Java 对象
```

| 对象 | 负责什么 | 推荐生命周期 |
|------|----------|----------------|
| `SqlSessionFactoryBuilder` | 读取配置并构建工厂 | 构建时使用，完成后即可释放 |
| `SqlSessionFactory` | 保存配置并创建会话 | 应用级复用，避免每次查询重新构建 |
| `SqlSession` | 执行 SQL、维护会话状态和事务 | 一次工作单元内使用，及时关闭；不能跨线程共享 |
| Mapper 接口代理 | 将方法调用定位到映射语句 | 独立模式下随所属会话使用 |

独立使用时，应显式控制提交和回滚。Spring 集成中，事务通常由 Spring 管理，
不能把原生 `SqlSession` 的生命周期规则直接套用到线程安全的 `SqlSessionTemplate` 上。
参见 [MyBatis 入门说明](https://mybatis.org/mybatis-3/getting-started.html)
和 [MyBatis-Spring 事务](https://mybatis.org/spring/transactions.html)。

## 最小可运行示例

示例使用 Java 17、Maven 和 H2 内存数据库，不需要安装数据库服务。
下面固定依赖版本以便复现，不表示这些版本是最新版本。

### 项目结构与依赖

```text
mybatis-demo/
├── pom.xml
└── src/main/java/demo/App.java
```

`pom.xml`：

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>demo</groupId>
  <artifactId>mybatis-demo</artifactId>
  <version>1.0.0</version>
  <properties>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.mybatis</groupId>
      <artifactId>mybatis</artifactId>
      <version>3.5.19</version>
    </dependency>
    <dependency>
      <groupId>com.h2database</groupId>
      <artifactId>h2</artifactId>
      <version>2.3.232</version>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.13.0</version>
      </plugin>
      <plugin>
        <groupId>org.codehaus.mojo</groupId>
        <artifactId>exec-maven-plugin</artifactId>
        <version>3.5.0</version>
      </plugin>
    </plugins>
  </build>
</project>
```

### Mapper、查询与事务

`src/main/java/demo/App.java`：

```java
package demo;

import java.sql.Connection;
import java.sql.Statement;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.datasource.unpooled.UnpooledDataSource;
import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory;

public class App {
    public interface CustomerMapper {
        @Insert("INSERT INTO customer(id, name) VALUES(#{id}, #{name})")
        int insert(@Param("id") long id, @Param("name") String name);

        @Select("SELECT name FROM customer WHERE id = #{id}")
        String findName(@Param("id") long id);
    }

    public static void main(String[] args) throws Exception {
        var dataSource = new UnpooledDataSource(
                "org.h2.Driver", "jdbc:h2:mem:demo;DB_CLOSE_DELAY=-1", "sa", "");
        // 建表单独完成，让业务会话只展示增查事务。
        try (Connection connection = dataSource.getConnection();
             Statement statement = connection.createStatement()) {
            statement.execute("CREATE TABLE customer(id BIGINT PRIMARY KEY, name VARCHAR(80))");
        }

        var environment = new Environment("demo", new JdbcTransactionFactory(), dataSource);
        var configuration = new Configuration(environment);
        configuration.addMapper(CustomerMapper.class);
        SqlSessionFactory factory = new SqlSessionFactoryBuilder().build(configuration);

        try (SqlSession session = factory.openSession(false)) {
            try {
                CustomerMapper mapper = session.getMapper(CustomerMapper.class);
                mapper.insert(1L, "张三");
                System.out.println(mapper.findName(1L));
                session.commit();
            } catch (RuntimeException exception) {
                // 出错时回滚整个工作单元，不能仅打印异常后继续提交。
                session.rollback();
                throw exception;
            }
        }
    }
}
```

在项目目录执行：

```bash
mvn -q compile exec:java -Dexec.mainClass=demo.App
```

预期输出包含 `张三`。相同主键重复插入会触发约束异常，并进入回滚分支。
本例只用于演示；实际应用通常通过连接池获取连接，在服务层定义事务边界。

## XML 配置

### 配置文件与外部属性

程序化配置和 XML 配置是两种入口。以下 XML 示例采用独立的 `demo.CustomerMapper` 接口，
不是上例的嵌套接口；将接口与映射文件拆出后使用，避免同一语句同时注册注解和 XML。

`src/main/resources/mybatis-config.xml`：

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE configuration PUBLIC "-//mybatis.org//DTD Config 3.0//EN"
    "https://mybatis.org/dtd/mybatis-3-config.dtd">
<configuration>
  <properties resource="jdbc.properties"/>
  <settings>
    <setting name="mapUnderscoreToCamelCase" value="true"/>
    <setting name="defaultStatementTimeout" value="25"/>
  </settings>
  <environments default="development">
    <environment id="development">
      <transactionManager type="JDBC"/>
      <dataSource type="POOLED">
        <property name="driver" value="${driver}"/>
        <property name="url" value="${url}"/>
        <property name="username" value="${username}"/>
        <property name="password" value="${password}"/>
      </dataSource>
    </environment>
  </environments>
  <mappers>
    <mapper resource="demo/CustomerMapper.xml"/>
  </mappers>
</configuration>
```

`src/main/resources/jdbc.properties`（仅用于本地 H2 示例）：

```properties
driver=org.h2.Driver
url=jdbc:h2:mem:demo;DB_CLOSE_DELAY=-1
username=sa
password=
```

XML 方式只配置连接与映射，不会自动创建示例表。业务数据库的初始化应单独完成。
配置属性同名时，构建工厂时传入的 `Properties` 优先，其次是资源文件，再次是 XML 内联属性。
生产凭据应由部署配置提供，不要写入笔记或提交到仓库。

### 常用配置与扩展点

| 配置项 | 用途与注意事项 |
|--------|----------------|
| `mapUnderscoreToCamelCase` | 将 `customer_name` 自动映射到 `customerName`；复杂结果优先显式映射 |
| `defaultStatementTimeout` | 语句超时秒数，实际行为受 JDBC 驱动支持影响 |
| `defaultExecutorType` | 选择 `SIMPLE`、`REUSE` 或 `BATCH`，一次只能配置一个值 |
| `localCacheScope` | `SESSION` 或 `STATEMENT`，控制本地缓存的作用范围 |
| `cacheEnabled` | 二级缓存总开关；开启它不等于所有 Mapper 自动启用二级缓存 |
| `lazyLoadingEnabled` | 配合关联查询使用，需警惕延迟加载造成额外查询 |
| `logImpl` | 指定单个日志实现，例如 `SLF4J`；还需配置对应日志依赖 |
| `typeAliases` | 为 Java 类型提供短名称，不改变数据转换规则 |
| `typeHandlers` | 处理 Java 类型与 JDBC 类型之间的转换 |
| `objectFactory` | 定制结果对象的创建方式，不负责执行 SQL |
| `plugins` | 注册拦截器，扩展执行流程 |
| `environments` | 选择数据源与事务管理方式，一次工厂构建选择一个环境 |
| `databaseIdProvider` | 识别数据库厂商以选择方言语句；不是 `dataSourceIdProvider` |

XML 顶层元素应遵循 DTD 规定的顺序。Mapper 可按资源路径、URL、接口类或包注册；
类和包注册时，要保证 XML 能按接口对应的类路径位置被发现。
完整取值与扩展契约见 [官方配置文档](https://mybatis.org/mybatis-3/configuration.html)。

## Mapper XML 与参数绑定

### 接口方法如何定位 SQL

接口全限定名对应 XML 的 `namespace`，方法名对应语句的 `id`。下面展示查询映射片段，
放入 `src/main/resources/demo/CustomerMapper.xml`：

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "https://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="demo.CustomerMapper">
  <select id="findName" resultType="string">
    SELECT name FROM customer WHERE id = #{id}
  </select>
</mapper>
```

对应接口的方法签名为 `String findName(@Param("id") long id)`。
多个参数建议用 `@Param` 命名，避免依赖编译器是否保留参数名称。

### 参数与结果映射

- `#{value}` 用于绑定数据值，通过预处理参数传给 JDBC。
- `${value}` 将文本直接拼入 SQL；不能直接接收用户输入的列名、排序方向或表名。
- 动态标识符应由服务端白名单选择；标识符不能简单用 `#{column}` 替换。
- `resultType` 适合简单结果；`resultMap` 适合列名与属性不同、关联对象等显式映射。
- 集合查询中的结果类型指单个元素类型，不是 `List` 本身。

多表结果要给重名列设置别名，再映射到明确的对象属性。
`association` 表达单个关联对象，`collection` 表达集合；逐行发起关联查询可能产生 N+1 问题。
参见 [SQL 映射文档](https://mybatis.org/mybatis-3/sqlmap-xml.html)。

### SQL 片段复用与 include 参数

下面的片段放在 Mapper 内；方法使用 `@Param("customerId") long customerId` 参数。
这里 `${alias}` 来自 XML 中写死的别名，只用于复用字段列表，不接受外部请求传值。

```xml
<sql id="customerColumns">
  ${alias}.id, ${alias}.name
</sql>

<select id="findCustomer" resultType="map">
  SELECT
  <include refid="customerColumns">
    <property name="alias" value="c"/>
  </include>
  FROM customer c
  WHERE c.id = #{customerId}
</select>
```

## 动态 SQL

动态 SQL 用于按条件组合语句。`where` 可处理开头多余的 `AND` / `OR`，
`set` 可处理更新字段尾部的逗号，但它们不会替你检查业务条件是否完整。

| 元素 | 典型用途 | 边界处理 |
|------|----------|----------|
| `if` | 可选条件 | 明确空值与空字符串是否应视为“未提供” |
| `choose/when/otherwise` | 多个条件中只选择一个分支 | 为缺省情况提供明确行为 |
| `where/trim` | 组织条件前缀 | 所有条件都为空时可能成为全表查询 |
| `set` | 动态更新字段 | 所有字段都为空时应拒绝更新请求 |
| `foreach` | 生成 `IN` 列表或批量值 | 空集合应明确返回空结果或拒绝请求 |

例如接口方法 `List<String> findNames(@Param("ids") List<Long> ids)`
可以配合下面的 Mapper 片段，避免空列表意外退化为全表查询：

```xml
<select id="findNames" resultType="string">
  SELECT name FROM customer
  <where>
    <choose>
      <when test="ids != null and ids.size() > 0">
        id IN
        <foreach collection="ids" item="id" open="(" separator="," close=")">
          #{id}
        </foreach>
      </when>
      <otherwise>1 = 0</otherwise>
    </choose>
  </where>
  ORDER BY id
</select>
```

更新和删除尤其需要业务层校验，不能仅依赖 `<where>` 防止全表操作。
完整语法见 [动态 SQL 文档](https://mybatis.org/mybatis-3/dynamic-sql.html)。

## 缓存与事务边界

| 层级 | 作用范围 | 使用要点 |
|------|----------|----------|
| 一级缓存 | 原生 `SqlSession` 本地缓存 | 默认会话范围；不同会话不能据此共享结果 |
| 二级缓存 | Mapper 命名空间，跨会话 | 需要配置 `<cache/>` 等，不是应用级通用缓存 |

一级缓存帮助复用相同查询的结果；更新、提交、回滚和关闭等操作会影响其内容。
同一会话可能返回同一个对象实例，修改查询对象时需要考虑后续读取是否受到影响。

二级缓存与事务生命周期协作，不能把“查询结束”理解为“立刻对其他会话发布结果”。
跨命名空间更新、外部 SQL 或其他应用修改数据库时，也不能假设 MyBatis 自动保证所有缓存一致。
引入缓存前应先明确哪些表被哪些服务修改，再决定是否启用。

Spring 集成时，使用 Spring 管理的会话和事务，不手动对注入的 Mapper 所属会话调用 `commit()`。
事务边界与会话复用的具体关系见 [MyBatis-Spring 会话管理](https://mybatis.org/spring/sqlsession.html)。

## 插件机制

插件通过实现 `org.apache.ibatis.plugin.Interceptor` 并声明拦截签名，介入指定方法调用。
常见扩展对象如下，原文中的 `Excutor` 应为 `Executor`：

| 对象 | 职责 | 常见扩展方向 |
|------|------|--------------|
| `Executor` | 协调查询、更新、缓存与事务相关操作 | SQL 调用统计 |
| `StatementHandler` | 创建、准备并执行 JDBC Statement | SQL 检查或改写 |
| `ParameterHandler` | 将参数写入 PreparedStatement | 特定参数处理 |
| `ResultSetHandler` | 将结果集映射成 Java 对象 | 结果处理扩展 |

插件必须匹配具体方法签名，并正确调用后续逻辑。随意改写 SQL 可能影响参数顺序、分页和缓存键，
不应只凭接口名称推测拦截时机。仅需字段类型转换时，优先使用 `TypeHandler`。

## 常见错误与排查

| 现象 | 常见原因 | 排查方向 |
|------|----------|----------|
| `Invalid bound statement (not found)` | XML 未注册或名称不匹配 | 检查资源打包、namespace、接口方法名和语句 id |
| `Parameter ... not found` | SQL 参数名与方法参数不一致 | 对照 `@Param` 和 `#{...}` |
| 查询字段为 null | 列名、别名与属性不匹配 | 检查驼峰映射或显式 resultMap |
| 写入后其他连接看不到数据 | 未提交或事务尚未结束 | 确认事务是否由当前程序或 Spring 管理 |
| `TooManyResultsException` | 单结果查询实际返回多行 | 检查唯一条件，或改用集合返回类型 |
| SQL 数量远超预期 | 关联嵌套查询或延迟加载 | 检查实际 SQL 与 N+1 查询 |
| 配置解析失败 | 把候选值列表当成一个值、标签顺序错误 | 使用单个合法配置值，检查 DTD 与异常位置 |

## 与相关概念的关系

- [[mybatis-plus|MyBatis-Plus]]：在 MyBatis 之上提供增强能力，仍需理解映射、SQL 与事务。
- [[ssm-integration|SSM 整合]]：理解 Spring、Spring MVC 与 MyBatis 的职责分工。
- [[mysql|MySQL]]：SQL 执行计划与索引决定数据库侧性能，框架不能替代这些优化。

## 参考

- [MyBatis 官方文档（中文）](https://mybatis.org/mybatis-3/zh_CN/index.html)
- [MyBatis Java API](https://mybatis.org/mybatis-3/java-api.html)
- [MyBatis-Spring 官方文档](https://mybatis.org/spring/)
- [尚硅谷 MyBatis 入门课程](https://www.bilibili.com/video/BV1VP4y1c7j7)
- [原整理资料：MyBatis Markdown 笔记](https://blog.csdn.net/qq_19387933/article/details/123256034)
- [原整理资料：include 高级使用](https://blog.csdn.net/m0_67318913/article/details/136595480)
- [原笔记来源：代码重工](https://www.wolai.com/rYAoeiSK9o6dc4qVEn76hw)
