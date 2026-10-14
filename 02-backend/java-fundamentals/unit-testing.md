---
title: Java 单元测试规范与原理
description: 从 JUnit 5 与 Mockito 的运行原理，到 Spring Boot 测试上下文缓存与切片测试机制，再到覆盖率提升路径的完整指南
tags:
  - java
  - testing
  - junit
  - mockito
  - spring-boot
  - backend
date: 2026-10-12
aliases:
  - Java 单元测试
  - Spring Boot 测试
---

# Java 单元测试规范与原理

本文回答三个问题：**单元测试到底在测什么**、**Spring Boot 的测试机制是怎么跑起来的**、
**怎样系统性地把测试面补齐**。示例基于 JUnit 5.10+、Mockito 5.x、Spring Boot 3.x、Java 17+。

## 单元测试的定位

### 测试金字塔

| 层次 | 占比 | 典型工具 | 单个耗时 | 说明 |
|------|------|----------|----------|------|
| 单元测试 | 约 70% | JUnit 5 + Mockito，不启容器 | 毫秒级 | 测业务逻辑分支 |
| 集成 / 切片测试 | 约 20% | `@WebMvcTest`、`@DataJpaTest` | 百毫秒级 | 测装配与映射 |
| 端到端测试 | 约 10% | Testcontainers + 真实端口 | 秒级 | 测真实链路 |

金字塔的意义不是"数量比例"，而是**成本与定位能力的权衡**：越往上越真实、越慢、失败时越
难定位。因此业务分支的判断逻辑应尽量压到最底层去测。

### 单元到底是什么

"单元 = 一个类"是最常见的误解。更准确的定义是：**单元是一个可观察的行为**
（a unit of behavior），它可能横跨一个类的几个方法，甚至几个协作对象。

判断标准有两条：

1. **失败时能立刻定位**——报错信息直接指向被破坏的行为。
2. **重构时能提供保护**——内部实现改了但行为没变，测试应当仍然通过。

反过来，如果一个测试在"重命名私有方法""调整内部调用顺序"时就红，说明它测的是实现
细节而非行为，这是测试脆弱（brittle test）的根源。

### FIRST 原则

| 字母 | 含义 | 实践要求 |
|------|------|----------|
| F | Fast 快速 | 单测套件应在秒级跑完，否则没人愿意跑 |
| I | Isolated 隔离 | 不依赖外部系统、不依赖执行顺序、不依赖其他测试留下的状态 |
| R | Repeatable 可重复 | 任何环境、任何次运行结果一致，时间/随机数/ID 必须可注入 |
| S | Self-validating 自校验 | 只有通过与失败两种结果，不靠人眼看日志 |
| T | Timely 及时 | 最好与实现同步编写，而不是上线前补 |

## JUnit 5 原理

### 三层架构

JUnit 5 不是一个单体库，而是三个职责分离的子项目：

```
┌─ 调用方：Maven Surefire / Gradle Test / IDE ─┐
│                                              │
├─ JUnit Platform：Launcher + TestEngine SPI ──┤  ← 运行框架
│                                              │
├─ Jupiter 引擎：解析 @Test，驱动生命周期 ─────┤  ← 测试写法
│                                              │
├─ Vintage 引擎：兼容 JUnit 3/4 ───────────────┤
└──────────────────────────────────────────────┘
```

- **`junit-platform-launcher`**：提供 `Launcher` API，负责发现和执行测试。
- **`junit-platform-engine`**：定义 `TestEngine` SPI，任何框架只要实现它就能被 JUnit 驱动
  （例如 Spock、Kotest、Cucumber 都有自己的引擎）。
- **`junit-jupiter-engine`**：JUnit 5 自己的引擎，解析 `@Test` 等 Jupiter 注解。
- **`junit-vintage-engine`**：桥接老的 JUnit 4 测试，便于渐进迁移。

**这套 SPI 正是 Spring Boot 能接进来的原因**：Spring 提供 `SpringExtension`（实现
`TestInstancePostProcessor`、`BeforeEachCallback`、`ParameterResolver` 等接口），
JUnit 在执行到对应生命周期节点时回调它，Spring 便在回调里完成依赖注入、容器启动与事务管理。

### 生命周期与实例作用域

默认每个测试方法都会**新建一个测试类实例**（`PER_METHOD`），保证测试间状态互不污染：

```text
@BeforeAll（静态方法，整个类一次）
  └─ 每个 @Test：新建实例 → @BeforeEach → 测试方法 → @AfterEach
@AfterAll（静态方法，整个类一次）
```

若希望 `@BeforeAll` 能写成非静态方法（常用于配合 `@Nested` 或 Kotlin），可声明
`@TestInstance(TestInstance.Lifecycle.PER_CLASS)`，代价是实例状态会在测试方法间共享，
需要自己保证不残留脏数据。

### 常用注解

```java
@DisplayName("订单金额计算")
class OrderAmountTest {

    @Nested
    @DisplayName("当使用优惠券时")
    class WithCoupon {
        @Test
        @DisplayName("金额不得低于零")
        void shouldClampToZero_whenCouponExceedsAmount() {
            // ...
        }
    }

    @ParameterizedTest
    @CsvSource({"100, 10, 90", "100, 100, 0", "50, 60, 0"})
    void shouldDeductCoupon(int amount, int coupon, int expected) {
        assertThat(OrderAmount.deduct(amount, coupon)).isEqualTo(expected);
    }

    @Test
    @Timeout(value = 2, unit = TimeUnit.SECONDS)
    void shouldFinishQuickly() {
        // 超时即失败，防止死循环拖垮 CI
    }
}
```

### 断言为什么推荐 AssertJ

JUnit 自带的 `assertEquals(expected, actual)` 参数顺序容易写反，且错误信息贫乏。
AssertJ 的流式 API 可读性和诊断信息都更好：

```java
// 弱断言：只验证了非空
assertThat(result).isNotNull();

// 强断言：精确描述期望
assertThat(result)
    .hasSize(2)
    .extracting(Order::getStatus)
    .containsExactly(OrderStatus.PAID, OrderStatus.CANCELLED);

// 异常断言，连消息一起校验
assertThatThrownBy(() -> orderService.pay(-1L))
    .isInstanceOf(IllegalArgumentException.class)
    .hasMessageContaining("订单金额非法");
```

**断言强度直接决定测试价值**。只断言"不抛异常"的测试，等于没写。

## Mockito 原理

### mock 是怎么造出来的

1. Mockito 5 默认使用 **inline mock maker**，基于 Byte Buddy 在运行时**改写目标类的字节码**
   （通过 Instrumentation 重定义已加载的类），因此可以 mock `final` 类、`final` 方法和
   `static` 方法——这也是为什么 Mockito 5 要求 JDK 11+。
2. 实例创建走 **Objenesis**，绕过构造函数直接分配对象，避免构造器里的副作用。
3. 生成的对象内部持有 `MockHandler`，每次方法调用都会被拦截，记录到
   `InvocationContainer`，然后：若命中已配置的 stub 则返回预设值，否则返回**零值**
   （`null`、0、`false`、空集合）。

理解第 3 点很重要：**未打桩的 mock 方法不会报错，只会静默返回零值**。这是"测试明明绿了
但线上挂了"的经典来源。可以用严格模式让它暴露出来：

```java
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.STRICT_STUBS)
class OrderServiceTest {
    // STRICT_STUBS：多余的 stub 会报 UnnecessaryStubbingException
    // 潜在桩冲突会报 PotentialStubbingProblem
}
```

### @Mock / @Spy / @InjectMocks

| 注解 | 行为 | 使用场景 |
|------|------|----------|
| `@Mock` | 全量代理，方法默认返回零值 | 替换掉不想真实调用的依赖 |
| `@Spy` | 包装真实对象，默认走真实逻辑，可局部打桩 | 只想替换某个方法，其余保持真实 |
| `@InjectMocks` | 把上面的 mock/spy 注入被测对象 | 构造被测实例 |

`@InjectMocks` 的注入优先级为：**构造器注入（选参数最多且能匹配的构造器）→ setter 注入 →
字段反射注入**。构造器注入最可靠，也最推荐——它能顺带暴露"这个类依赖是不是太多了"的设计问题。

### 什么时候不该 mock

| 对象 | 建议 | 原因 |
|------|------|------|
| 值对象、Entity、DTO、枚举 | 不要 mock，直接 new | 没有行为需要替换 |
| 自己写的纯函数/工具类 | 不要 mock | 直接调用更真实 |
| 外部服务、MQ、HTTP 客户端、时钟 | 应该 mock 或抽象成接口 | 不可控、慢 |
| 数据库 Repository | 单测 mock，集成测真跑 | 见下一节分层策略 |

一条经验法则：**mock 跨越进程边界的东西，mock 你无法控制的东西**；不要 mock 你自己的
领域逻辑，否则测试只是在验证 mock 配置本身。

## Spring Boot 测试原理

### spring-boot-starter-test 装了什么

引入这一个 starter，等价于引入：JUnit 5（Jupiter）、Spring Test、Spring Boot Test、
AssertJ、Hamcrest、Mockito（`mockito-core` + `mockito-junit-jupiter`）、JSONassert、JsonPath。

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

### 上下文缓存机制

这是 Spring Boot 测试最重要的原理。`ApplicationContext` 不会为每个测试类重启，而是被
**TestContext Framework 缓存复用**：

1. 测试类启动时，`SpringBootTestContextBootstrapper` 收集配置类、`@ActiveProfiles`、
   属性源、`ContextCustomizer` 等，组装成 `MergedContextConfiguration`。
2. 该对象作为 `ContextCache` 的 key（它正确实现了 `equals`/`hashCode`）。
3. **key 相同 → 复用同一个容器**，几乎零成本；key 不同 → 新建容器，代价是秒级。

由此得到两条重要的工程结论：

- **不要为了"隔离"随意加注解**。`@MockBean`、`@SpyBean`、`@TestPropertySource`、
  `@DynamicPropertySource` 都会改变配置指纹，导致缓存失效、容器重启。一个项目里
  `@MockBean` 用得越杂，测试跑得越慢。
- **`@DirtiesContext` 是核武器**。它会关闭并从缓存移除上下文，通常只在"测试确实污染了
  容器状态"时使用，滥用会让整个测试套件退化成"每类启一次容器"。

> **注意**：`ContextCache` 默认上限为 32 个上下文，超出后按 LRU 关闭。缓存被频繁击穿时，
> 日志里会出现上下文反复启动的现象，这是测试变慢的首要排查点。

### 切片测试是怎么实现的

`@SpringBootTest` 会加载**完整**应用上下文，而切片测试只加载一层。实现靠两个机制配合：

1. **类型排除过滤器**：`@WebMvcTest` 上标注了 `@TypeExcludeFilters(WebMvcTypeExcludeFilter.class)`，
   在组件扫描时把非 Web 层的 Bean 全部过滤掉（只留 `@Controller`、`@ControllerAdvice`、
   `WebMvcConfigurer`、`Filter` 等）。
2. **自动配置裁剪**：`@AutoConfigureMockMvc` 等注解配合
   `spring-boot-test-autoconfigure` 中预定义的自动配置清单，只导入该切片需要的配置。

### 常用注解对照

| 注解 | 加载范围 | 适用场景 |
|------|----------|----------|
| `@SpringBootTest` | 完整上下文 | 跨层集成、验证整体装配 |
| `@WebMvcTest` | 仅 Web 层 | 校验入参、状态码、异常处理器、JSON 序列化 |
| `@DataJpaTest` | 仅 JPA 层，自带事务回滚 | 验证 SQL、实体映射、复杂查询 |
| `@RestClientTest` | 仅 HTTP 客户端 | 验证 `RestClient`/`WebClient` 调用 |
| `@JsonTest` | 仅 JSON 序列化 | 验证序列化注解与格式 |

### @MockMvc 为什么不启端口

`@WebMvcTest` 下注入的 `MockMvc` 构造过程是：创建一个 `MockServletContext` 与
`MockHttpServletRequest/Response`，然后**直接调用 `DispatcherServlet.service()`**，
完全跳过 Servlet 容器和网络栈。所以它快，但也因此**测不到**过滤器链之外的真实网络行为
（如真实端口、SSL、连接超时）。需要这些时改用
`@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)` + `TestRestTemplate`。

### 完整示例

一个典型的 Controller 切片测试：

```java
@WebMvcTest(OrderController.class)
@Import(SecurityConfig.class)          // 切片不会自动带上安全配置
class OrderControllerTest {

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @MockitoBean OrderService orderService;   // Spring Boot 3.4+ 推荐，替代 @MockBean

    @Test
    @WithMockUser(roles = "USER")
    void shouldReturn400_whenAmountIsNegative() throws Exception {
        mockMvc.perform(post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(new OrderRequest(-1L))))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("INVALID_AMOUNT"));
    }

    @Test
    @WithMockUser(roles = "USER")
    void shouldReturnOrder_whenServiceSucceeds() throws Exception {
        given(orderService.create(any())).willReturn(new OrderDto(100L, "PAID"));

        mockMvc.perform(post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"amount\":100}"))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.orderId").value(100L));
        // 只验证 HTTP 契约，不验证业务逻辑——业务逻辑属于 Service 层单测
    }
}
```

> **注意**：示例中的 `@WithMockUser` 来自 `spring-security-test`，需额外引入依赖。
>
> 另外，Spring Boot 3.4 起 `@MockBean` 被标记为 deprecated，官方推荐使用
> `@MockitoBean`。后者在语义上等价，但实现不依赖 `ContextCustomizer`，因而**不会破坏
> 上下文缓存**，这是升级后最值得拿到的收益。

## 分层测试策略

| 层次 | 推荐测试方式 | 重点覆盖内容 | 不测什么 |
|------|--------------|--------------|----------|
| Controller | `@WebMvcTest` + MockMvc | 参数校验、状态码、异常映射、JSON 契约 | 业务计算 |
| Service | 纯 JUnit + Mockito | 分支、边界值、异常路径、事务边界 | SQL 正确性 |
| Domain / 工具类 | 纯 JUnit，零 mock | 领域规则、金额计算、状态机流转 | 框架行为 |
| Repository | `@DataJpaTest` 或 Testcontainers | SQL、实体映射、分页、并发 | 业务逻辑 |
| 外部依赖 | WireMock / Mockito / Testcontainers | 超时、重试、反序列化异常 | — |

**核心原则：一层测一类问题，不要混着测。** 用 `@SpringBootTest` 测业务分支是最常见的浪费——
既慢，失败时又无法定位是哪一层出了问题。

## 如何提升覆盖面

### 覆盖率指标的三个层次

| 指标 | 含义 | 盲区 |
|------|------|------|
| 行覆盖 | 代码行被执行过 | 断言弱甚至没有断言也算覆盖 |
| 分支覆盖 | `if`/`switch` 每个分支都走过 | 边界值、异常组合仍可能漏 |
| 变异得分 | 自动改源码后测试是否失败 | 最接近真实保障，但耗时较长 |

**80% 的行覆盖可能一行有效断言都没有。** 提升覆盖面的正确顺序是：先补断言强度，再补分支，
最后用变异测试找漏网之鱼。

### 补测的优先级

1. **领域层与工具类**——零依赖、零 mock，投入产出比最高，先做到 90%+。
2. **Service 层**——业务分支最密集，按"正常路径 / 边界值 / 异常路径"三类逐个补。
3. **Controller 层**——补参数校验与异常码，用切片测试，成本低。
4. **Repository 层**——只补复杂 SQL 与映射，简单 CRUD 由框架保证。
5. **关键链路集成测试**——只挑 2~3 条主流程，不要全量铺开。

### 边界值与等价类

补齐分支覆盖最快的方法是**按清单检查每个条件判断**：

- 数值：`0`、`负数`、`极大值`、`Integer.MAX_VALUE` 附近、精度（`BigDecimal` 的 scale）。
- 集合：`null`、`空集合`、`单元素`、`重复元素`、`超出分页大小`。
- 字符串：`null`、`空串`、`全空格`、`超长`、`特殊字符`。
- 时间：跨天、跨月、闰年、`null`、未来时间。
- 异常路径：依赖抛异常时是否正确回滚、是否吞掉了异常、错误消息是否可用。

### 让代码变得可测

覆盖率补不上去，很多时候不是测试写得少，而是**代码本身不可测**。四种典型改造：

```java
// 1. 时间：不要直接 new，注入 Clock
private final Clock clock;
boolean isExpired() { return expiry.isBefore(Instant.now(clock)); }

// 2. 随机数与 ID：抽成接口，测试时注入固定值
private final IdGenerator idGenerator;   // 测试用 () -> "fixed-id"

// 3. 静态调用：包一层可替换的 Bean，而不是用 mockStatic 硬扛
private final SmsGateway smsGateway;     // 内部才调用静态方法

// 4. 外部 IO：依赖倒置，领域层只依赖接口
public interface InventoryPort { boolean reserve(String sku, int qty); }
```

能不用 `mockStatic` 就不用——它意味着你的代码和具体实现强耦合了。

### 用 JaCoCo 卡阈值

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>check</id>
            <phase>verify</phase>
            <goals><goal>check</goal></goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>BRANCH</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.60</minimum>
                            </limit>
                        </limits>
                        <excludes>
                            <exclude>**/config/**</exclude>
                            <exclude>**/*Application.class</exclude>
                            <exclude>**/dto/**</exclude>
                        </excludes>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

**优先卡分支覆盖率而不是行覆盖率**，并把配置类、启动类、纯 DTO 排除在外——否则阈值会被
大量无逻辑代码稀释，失去意义。

### 变异测试

JaCoCo 只能告诉你"哪些行没人跑"，不能告诉你"跑了的地方是否真的被验证"。PIT（ pitest）
会自动修改字节码制造变异体（如把 `>` 改成 `>=`、删除一行、返回值取反），若测试仍然通过，
说明该处**没有被有效断言**：

```bash
mvn org.pitest:pitest-maven:mutationCoverage \
    -DmutationThreshold=70 \
    -DtargetClasses=com.example.order.* \
    -DtargetTests=com.example.order.*
```

变异测试耗时长，建议在 CI 的夜间任务跑，或在覆盖率达标后作为进阶指标。

## 命名与结构规范

### 命名

推荐 `被测方法_场景_期望结果`，或 `should_期望_When_场景`：

```java
// 推荐：见名知义，失败时一眼看出破坏了什么
void deduct_shouldReturnZero_whenCouponExceedsAmount()
void pay_shouldThrowException_whenOrderAlreadyCancelled()

// 不推荐
void test1()
void testDeduct()
```

### AAA 结构

每个测试方法内部严格三段式，段落之间空行分隔：

```java
@Test
void deduct_shouldReturnZero_whenCouponExceedsAmount() {
    // Arrange：准备输入与依赖行为
    Order order = OrderFixture.paidOrder(100);
    given(couponRepo.findValid(any())).willReturn(Coupon.of(150));

    // Act：只调用一个被测行为
    int actual = orderService.deduct(order);

    // Assert：只断言这一件事的期望
    assertThat(actual).isZero();
}
```

配套约定：

- **一个测试只验证一个行为**——多个断言应当是同一行为的不同侧面，而不是顺手多测几个分支。
- **不要写 `try-catch` 吞异常**——用 `assertThatThrownBy`，失败信息更清晰。
- **测试数据用工厂方法**（`OrderFixture`、`ObjectMother`、Builder），避免每个测试手写
  十几行构造代码，也避免改字段时全量返工。
- **避免测试间共享可变状态**——`static` 字段、`@BeforeAll` 里创建的集合都是隐患。

### Surefire 与 Failsafe

```xml
<plugin>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <!-- 单元测试：*Test.java，快 -->
        <excludedGroups>slow</excludedGroups>
    </configuration>
</plugin>
<plugin>
    <artifactId>maven-failsafe-plugin</artifactId>
    <executions>
        <execution>
            <goals><goal>integration-test</goal><goal>verify</goal></goals>
        </execution>
    </executions>
</plugin>
```

Surefire 默认认 `*Test.java`、`Test*.java`、`*Tests.java`、`*TestCase.java`；
Failsafe 认 `*IT.java`，用于区分慢速集成测试，避免拖慢日常提交。

## 常见反模式

| 反模式 | 后果 | 改进 |
|--------|------|------|
| 所有测试都用 `@SpringBootTest` | 套件从 10 秒变成 10 分钟 | 业务分支下沉为纯单测 |
| 断言只写 `isNotNull()` | 覆盖率虚高，缺陷照样漏 | 断言精确的期望值 |
| 滥用 `@MockBean` | 上下文缓存反复击穿 | 优先构造器注入；升级到 `@MockitoBean` |
| 测试依赖执行顺序 | 单跑绿、全跑红 | 每个测试自建数据，加事务回滚 |
| mock 自己的领域对象 | 测试在验证 mock 配置 | 领域逻辑直接真跑 |
| 用 `Thread.sleep` 等异步 | 偶发失败（flaky） | 用 Awaitility 轮询条件 |
| 测试数据硬编码日期 | 过一段时间集体失效 | 注入 `Clock`，测试里固定时间 |
| 为了覆盖率给 getter 写测试 | 指标好看，保障为零 | 排除 DTO、配置类 |

## 落地清单

1. 引入 `spring-boot-starter-test`，确认 Surefire / Failsafe 分工。
2. 领域层与工具类先补到 90% 分支覆盖，全部为纯单测。
3. Service 层按"正常 / 边界 / 异常"三类补分支，依赖用 `@Mock` 替换。
4. Controller 层改用 `@WebMvcTest`，只验 HTTP 契约。
5. Repository 层用 `@DataJpaTest`，只验复杂 SQL 与映射。
6. 排查 `@MockBean` 与 `@DirtiesContext` 的使用，减少上下文重启。
7. 配置 JaCoCo 分支覆盖阈值并接入 CI，配置类与 DTO 排除。
8. 覆盖率达标后引入 PIT，把变异得分作为进阶指标。

## 参考

- [JUnit 5 官方文档](https://junit.org/junit5/docs/current/user-guide/)
- [Mockito 官方文档](https://site.mockito.org/)
- [Spring Boot Testing 文档](https://docs.spring.io/spring-boot/reference/testing/index.html)
- [AssertJ 文档](https://assertj.github.io/doc/)
- [PIT Mutation Testing](https://pitest.org/)
- [[java-se|Java SE 核心语法]]
- [[spring-boot3|Spring Boot 3 使用指南]]
