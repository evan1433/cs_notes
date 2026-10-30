---
title: Spring 5 核心
description: Spring Framework 5.x 核心机制：IoC 容器与 Bean 生命周期、Aware 回调、BeanPostProcessor 扩展点、AOP 代理、声明式事务失效场景与 JdbcTemplate 数据访问
tags:
  - java
  - spring
  - dependency-injection
  - aop
  - transaction
date: 2026-10-30
aliases:
  - spring5
  - Spring5
---

# Spring 5 核心

> 学习资源：
>
> - [【Spring5】尚硅谷 Spring5 教程](https://www.bilibili.com/video/BV1yq4y1Q7N7/?p=19&share_source=copy_web&vd_source=e65574be5c4ff436d099ae0526b97fd9)
> - [廖雪峰 - Spring 教程](https://liaoxuefeng.com/books/java/spring/index.html)

Spring 5 是**以 `javax.*` 命名空间、JDK 8 为基线**的最后一代 Spring。它奠定了今天所有人写 Spring 代码的姿势：注解驱动开发、`@Transactional` 声明式事务、`JdbcTemplate` 模板化数据访问、`@Aspect` 切面。Spring 6 改的是底座（Java 17 + `jakarta.*`），**这些用法一行都不用改**——所以把 Spring 5 的容器机制吃透，等于同时掌握了 Spring 6 的核心。

> **版本提示**：5.3.x 是第五代最后一个特性分支，**开源支持已于 2024 年 8 月结束**，仅剩商业 LTS。新项目请直接看 [[spring6|Spring Framework 6]]。本文档事实核对时间为 2026 年 10 月。

## 1. 版本定位：5.x 处在哪一代

| 代际 | 终版 | JDK 范围 | 命名空间 | 开源支持 |
|------|------|----------|----------|----------|
| Spring 5.3 | 5.3.x | JDK 8 - 21 | `javax.*`（Java EE 7-8） | 2024-08 已结束 |
| Spring 6.2 | 6.2.x | JDK 17 - 25 | `jakarta.*`（Jakarta EE 9-10） | 2026-06 已结束 |
| Spring 7.0 | 7.0.x | JDK 17 - 25+ | `jakarta.*`（Jakarta EE 11-12） | 当前主线 |

5.x 内部四个小版本的演进主线：

| 版本 | GA 年份 | 标志性能力 |
|------|---------|-----------|
| 5.0 | 2017 | JDK 8 基线、响应式栈 WebFlux、Kotlin 支持、函数式 Bean 注册 |
| 5.1 | 2018 | JDK 11 支持、Bean 定义 DSL、`@Bean` 懒注册优化 |
| 5.2 | 2019 | RSocket、`@Configuration(proxyBeanMethods = false)`、协程支持 |
| 5.3 | 2020 | JDK 8-21 跨度、GraalVM 原生镜像（spring-native）、HTTP/2，**最后一个特性分支** |

## 2. IoC 容器

IoC（控制反转）解决的是**对象创建权与依赖装配权的归属问题**：对象不再 `new` 自己的依赖，改由容器读配置/注解后统一装配。这样替换实现、加代理、做作用域控制才有统一的切入点。

### 2.1 BeanFactory 与 ApplicationContext

| 对比项 | `BeanFactory` | `ApplicationContext` |
|--------|---------------|----------------------|
| 定位 | 最底层容器接口，只做 Bean 的注册与获取 | 面向应用的容器，继承 `BeanFactory` 并叠加企业级能力 |
| Bean 创建时机 | 默认懒加载（`getBean` 才创建） | 默认启动即预实例化单例 |
| 国际化 | 无 | `MessageSource` |
| 事件机制 | 无 | `ApplicationEventPublisher` |
| 资源加载 | 无 | `ResourceLoader`（可读 classpath / file / URL） |
| 注解驱动 | 需手动注册后处理器 | `AnnotationConfigApplicationContext` 开箱即用 |
| 典型实现 | `DefaultListableBeanFactory` | `AnnotationConfigApplicationContext`、`ClassPathXmlApplicationContext` |

一句话：`ApplicationContext` = `BeanFactory` + 国际化 + 事件 + 资源 + 自动注册的后处理器。日常开发用的都是后者。

### 2.2 依赖注入与生命周期回调

一个典型的被容器管理的 Bean：

```java
@Component
public class MailService {
    @Autowired(required = false)
    ZoneId zoneId = ZoneId.systemDefault();

    @PostConstruct
    public void init() {
        System.out.println("Init mail service with zoneId = " + this.zoneId);
    }

    @PreDestroy
    public void shutdown() {
        System.out.println("Shutdown mail service");
    }
}
```

这段代码里有三个容易被忽略的语义：

| 写法 | 真实含义 |
|------|----------|
| `@Autowired(required = false)` | 容器里找不到 `ZoneId` 类型的 Bean 时**不报错**，保留字段初始值。注意：只有字段/方法注入支持 `required`，构造器注入的必需性由参数本身决定 |
| `@PostConstruct` | 依赖注入**完成之后**、Bean 可用之前执行；此时 `zoneId` 一定已就绪 |
| `@PreDestroy` | 容器关闭时执行，适合放连接释放、线程池 shutdown。**原型（prototype）作用域的 Bean 不会触发此回调** |

> 在 Spring 6 中，`@PostConstruct`/`@PreDestroy` 来自 `jakarta.annotation` 而非 `javax.annotation`，迁移细节见 [[spring6|Spring Framework 6]]。

### 2.3 Bean 的完整生命周期

单例 Bean 从创建到销毁共 12 个节点，**理解顺序才能判断"我的代码为什么在依赖还没注入时就被调用"**：

```text
1  实例化（构造器 / 工厂方法）
2  属性填充（依赖注入）
3  Aware 回调：BeanNameAware → BeanClassLoaderAware → BeanFactoryAware
4  BeanPostProcessor.postProcessBeforeInitialization
5  @PostConstruct
6  InitializingBean.afterPropertiesSet()
7  自定义 init-method
8  BeanPostProcessor.postProcessAfterInitialization   ← AOP 代理在这里生成
9  进入使用期（业务调用）
10 @PreDestroy
11 DisposableBean.destroy()
12 自定义 destroy-method
```

两个关键结论：

- **AOP 代理在第 8 步才生成**，所以第 3-7 步里 `this` 还是原始对象，拿不到代理。
- 第 6、7 步与第 10、12 步是两套并存的机制（接口 vs 配置），实际项目里用注解版（第 5、10 步）即可，别混用。

### 2.4 作用域

| 作用域 | 说明 | 注意 |
|--------|------|------|
| `singleton` | 默认。容器内唯一实例 | 有状态字段会有线程安全问题 |
| `prototype` | 每次 `getBean` 新建 | 容器不管理销毁，`@PreDestroy` 不生效 |
| `request` / `session` | Web 环境，与 HTTP 请求/会话同生命周期 | 需 Web 感知容器 |
| `application` | 与 `ServletContext` 同生命周期 | 用得少 |

## 3. Aware 接口

Aware 是 Spring 提供的一类"回调式注入"：Bean 实现某个接口，容器在初始化阶段把对应基础设施对象**通过 setter 传进来**。它的存在意义是——当注解注入表达不了"我需要容器本身"时（比如要拿 `ApplicationContext` 做动态取 Bean），用 Aware 比 `@Autowired` 更语义化。

### 3.1 常用的 Aware 接口

Aware 全部位于 `org.springframework.beans.factory` 和 `org.springframework.context` 两个包，命名规律是「基础设施类型 + Aware」，回调方法统一为 `setXxx(...)`。

#### 1. `BeanFactoryAware`

感知 Bean 所在的容器，回调 `setBeanFactory(BeanFactory)`。拿到引用后可以在运行时按名字/类型取其他 Bean、查询 Bean 定义。注意给的是 `BeanFactory` 而不是上下文，**没有国际化、事件、资源加载能力**，需要这些请用下一个。

#### 2. `ApplicationContextAware`

感知应用上下文，回调 `setApplicationContext(ApplicationContext)`。`ApplicationContext` 本身是 `BeanFactory` 的子接口，所以能力是上一个的超集：取 Bean、发事件、读资源、做国际化都能覆盖。

> 两个接口是并列关系，不是继承关系（`ApplicationContextAware` 并不继承 `BeanFactoryAware`）。同时实现时 `setBeanFactory` 先执行（生命周期第 3 步，容器直接调用），`setApplicationContext` 在后（第 4 步，由 `ApplicationContextAwareProcessor` 这个后处理器调用）。

#### 3. `EnvironmentAware`

感知 `Environment`，回调 `setEnvironment(Environment)`。`getProperty(...)` 读配置、`getActiveProfiles()` 判断当前环境、`acceptsProfiles(...)` 做条件分支。

#### 4. `ResourceLoaderAware`

感知 `ResourceLoader`，回调 `setResourceLoader(ResourceLoader)`。用 `getResource("classpath:app.yml")` / `"file:/etc/app.yml"` 统一读取 classpath、文件系统、URL 三类资源。注入的声明类型是 `ResourceLoader`，**要通配符匹配（`classpath*:`）得转成 `ResourcePatternResolver`**——`ApplicationContext` 正好实现了它。

#### 5. `MessageSourceAware`

感知 `MessageSource`，回调 `setMessageSource(MessageSource)`，用于代码里主动取国际化消息：`getMessage("order.notfound", args, locale)`。业务代码直接 `@Autowired MessageSource` 更常见，Aware 主要用于框架级扩展。

#### 6. `ApplicationEventPublisherAware`

感知事件发布器，回调 `setApplicationEventPublisher(ApplicationEventPublisher)`，之后可 `publishEvent(new OrderPaidEvent(id))` 发领域事件。同样可以直接注入 `ApplicationEventPublisher`，用 Aware 只是省掉一层依赖声明。

#### 7. `BeanClassLoaderAware`

感知加载当前 Bean 的 `ClassLoader`，回调 `setBeanClassLoader(ClassLoader)`。用于反射加载插件类、动态注册类型。业务代码基本用不到，写框架时才需要。

#### 8. `BeanNameAware`

感知自己在容器里的 beanName，回调 `setBeanName(String)`。日志里打出来能直接定位「究竟是哪个 Bean 报的错」，也是原型作用域下生成唯一资源名的常用手段。

Aware 家族远不止这 8 个，完整列表看 `org.springframework.beans.factory.Aware` 的子接口，较常用的还有 `ServletContextAware`、`LoadTimeWeaverAware`、`NotificationPublisherAware`（JMX）。

### 3.2 与容器扩展点的区别

`BeanPostProcessor` 和 `BeanFactoryPostProcessor` 名字里都带 `Aware`/`Processor` 之类的基础设施色彩，容易被归到同一类，但它们**不实现 `Aware`、不接收任何上下文对象注入**，是另一套机制：容器扩展点。

| 对比项 | Aware 接口 | `BeanPostProcessor` / `BeanFactoryPostProcessor` |
|--------|-----------|--------------------------------------------------|
| 方向 | 容器把基础设施对象**推给** Bean（`setXxx`） | 扩展点**拦截**容器处理 Bean（定义）的流程 |
| 作用范围 | 只影响实现了该接口的那个 Bean | 一个 BPP 作用于容器内**所有** Bean |
| 执行时机 | 每个 Bean 初始化时回调（生命周期第 3、4 步） | BPP 在每个 Bean 初始化前后（第 4、8 步）；BFPP 早于所有 Bean 实例化 |

详见[第 4 节 BeanPostProcessor](#4-beanpostprocessor)。

### 3.3 正确用法

```java
@Component
public class OrderEventHandler implements ApplicationContextAware, BeanNameAware {

    private ApplicationContext ctx;
    private String beanName;

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) {
        this.ctx = applicationContext;
    }

    @Override
    public void setBeanName(String name) {
        // 便于日志定位"究竟是哪个 Bean 报的错"
        this.beanName = name;
    }

    public void publishLater(String orderId) {
        // 延迟到运行时才确定用哪个处理器：注解注入表达不了，Aware 可以
        OrderHandler handler = ctx.getBean(orderId.startsWith("B2B")
                ? "b2bOrderHandler" : "retailOrderHandler", OrderHandler.class);
        handler.handle(orderId);
    }
}
```

> **不要滥用 Aware**：它把业务类绑死在 Spring API 上，单测时得手搓 `ApplicationContext`。能用 `@Autowired` 注入具体依赖就不要注入容器本身——`ctx.getBean(...)` 是服务定位器模式，是依赖注入的反面。

## 4. BeanPostProcessor

`BeanPostProcessor`（BPP）是 Spring 最重要的扩展点之一：它在**每个 Bean 初始化前后**被调用，是 AOP 自动代理、`@Autowired` 注解处理、`@PostConstruct` 调用、`@Async` 代理等功能的实现基础。

### 4.1 与 BeanFactoryPostProcessor 的区别

| 对比项 | `BeanPostProcessor` | `BeanFactoryPostProcessor` |
|--------|---------------------|----------------------------|
| 作用对象 | **Bean 实例** | **BeanDefinition（元数据）** |
| 执行时机 | 每个 Bean 初始化前/后（第 4、8 步） | 所有 BeanDefinition 加载完、任何 Bean 实例化之前 |
| 能否修改 Bean 属性值 | 能 | 不能（Bean 还没实例化） |
| 典型用途 | 生成代理、注入注解、校验 | 解析占位符、改作用域、条件注册 |
| 典型实现 | `AutowiredAnnotationBeanPostProcessor`、`AbstractAutoProxyCreator` | `PropertySourcesPlaceholderConfigurer`、`ConfigurationClassPostProcessor` |

### 4.2 示例：给特定 Bean 包一层代理

```java
@Component
public class TimingBeanPostProcessor implements BeanPostProcessor {

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        // 只处理带 @Timed 的类，避免给所有 Bean 加代理（会拖慢启动、破坏类型判断）
        if (!bean.getClass().isAnnotationPresent(Timed.class)) {
            return bean;
        }
        ProxyFactory factory = new ProxyFactory(bean);
        factory.addAdvice((MethodInterceptor) invocation -> {
            long start = System.nanoTime();
            try {
                return invocation.proceed();
            } finally {
                long costMs = (System.nanoTime() - start) / 1_000_000;
                System.out.printf("[timing] %s#%s cost=%dms%n",
                        beanName, invocation.getMethod().getName(), costMs);
            }
        });
        return factory.getProxy();
    }
}
```

### 4.3 三个必须知道的坑

1. **BPP 自身不会被其他 BPP 处理**。你写的 BPP 如果依赖了别的 Bean，可能拿到的是尚未初始化的半成品——所以 BPP 里尽量只依赖基础设施 Bean。
2. **BPP 里 `@Autowired` 可能不生效**。BPP 的注册时机极早，注入由 `AutowiredAnnotationBeanPostProcessor` 负责，而它自己也必须先从 BPP 注册流程里出来。需要依赖时用 `BeanFactoryAware` 或方法参数注入。
3. **返回 `null` 会导致该 Bean 缺失**。返回 `null` 在 Spring 语义里表示"跳过后续处理并让容器把该 Bean 视为未创建"，容易造成莫名其妙的 `NoSuchBeanDefinitionException`。

## 5. AOP

AOP 解决"横切关注点"问题：日志、鉴权、事务、埋点这类逻辑天然散布在所有业务方法周围，用切面把它们从业务代码里抽出来。

### 5.1 术语对照

| 术语 | 含义 | 代码载体 |
|------|------|----------|
| 切面 Aspect | 横切逻辑的模块化封装 | `@Aspect` 类 |
| 连接点 JoinPoint | 程序执行中可以织入的点（方法调用、异常抛出） | 运行时对象 `JoinPoint` |
| 切点 Pointcut | 用来**筛选**连接点的表达式 | `@Pointcut("execution(...)")` |
| 通知 Advice | 在切点上执行的动作 | `@Before` / `@After` / `@Around` 等 |
| 织入 Weaving | 把切面接到目标对象上的过程 | 运行时生成代理（Spring AOP） |
| 目标对象 Target | 被代理的原始对象 | 你的 `@Service` |

### 5.2 一个能跑的切面

```java
@Aspect
@Component
@Order(1)   // 多个切面时决定优先级，值越小越外层
public class AuditAspect {

    // 切点：com.example.order.service 包下所有 public 方法
    @Pointcut("execution(public * com.example.order.service..*(..))")
    public void serviceLayer() {}

    @Before("serviceLayer()")
    public void before(JoinPoint jp) {
        System.out.println("call " + jp.getSignature().toShortString());
    }

    @Around("serviceLayer() && @annotation(auditable)")
    public Object around(ProceedingJoinPoint pjp, Auditable auditable) throws Throwable {
        try {
            Object result = pjp.proceed();          // 必须调用，否则业务方法不执行
            return result;
        } catch (Throwable ex) {
            // 切面里吞异常是最常见的线上事故来源之一，这里只记录再抛出
            System.err.println("failed: " + pjp.getSignature() + " -> " + ex.getMessage());
            throw ex;
        }
    }

    @AfterReturning(pointcut = "serviceLayer()", returning = "ret")
    public void afterReturning(Object ret) {
        System.out.println("returned: " + ret);
    }

    @AfterThrowing(pointcut = "serviceLayer()", throwing = "ex")
    public void afterThrowing(Throwable ex) {
        System.out.println("exception: " + ex.getClass().getSimpleName());
    }
}
```

### 5.3 JDK 动态代理 vs CGLIB

| 对比项 | JDK 动态代理 | CGLIB |
|--------|--------------|-------|
| 前提 | 目标类**必须实现接口** | 目标类不能是 `final`，方法不能是 `final`/`private` |
| 原理 | 生成接口的实现类，委托给 `InvocationHandler` | 生成目标类的子类，覆写方法 |
| 依赖 | JDK 自带 | 三方库（Spring 已内置并重打包） |
| 性能 | 创建快、调用略慢 | 创建慢、调用快（现代 JVM 差异已很小） |
| 默认策略 | 有接口用 JDK 代理 | 无接口用 CGLIB；`@EnableAspectJAutoProxy(proxyTargetClass = true)` 强制 CGLIB |

> Spring Boot 2.x 起 `spring.aop.proxy-target-class` 默认 `true`，即**一律 CGLIB**。这也解释了为什么给 `@RestController` 加切面时不需要接口。

### 5.4 切点表达式速查

| 表达式 | 匹配范围 |
|--------|----------|
| `execution(* com.example..*Service.*(..))` | 包及其子包下所有 `*Service` 类的任意方法 |
| `execution(public * *(..))` | 所有 public 方法 |
| `within(com.example.order..*)` | 包内所有类的所有方法（不依赖方法签名） |
| `@annotation(org.springframework.transaction.annotation.Transactional)` | 标注了该注解的方法 |
| `@within(org.springframework.stereotype.Service)` | 类上有该注解的所有方法 |
| `args(java.lang.String, ..)` | 第一个参数是 String 的方法 |
| `bean(orderService)` | 指定 beanName 的对象 |

## 6. 事务

`@Transactional` 是 Spring AOP 最成功的应用：把「开启 → 提交/回滚 → 释放连接」这段样板从业务代码里彻底拿掉。也正因为它是**基于代理**实现的，失效场景特别多。

### 6.1 基本用法

```java
@Service
public class OrderService {

    private final OrderRepository orderRepository;
    private final StockClient stockClient;

    public OrderService(OrderRepository orderRepository, StockClient stockClient) {
        this.orderRepository = orderRepository;
        this.stockClient = stockClient;
    }

    // rollbackFor 必须显式写：默认只对 RuntimeException 和 Error 回滚
    @Transactional(rollbackFor = Exception.class, timeout = 5)
    public void placeOrder(OrderCommand cmd) throws BizException {
        orderRepository.insert(cmd.toOrder());
        stockClient.deduct(cmd.getSku(), cmd.getQty());   // 远程调用失败会抛受检异常
    }
}
```

### 6.2 八个失效场景（按踩坑频率排序）

| 场景 | 原因 | 正确做法 |
|------|------|----------|
| 同类内部方法自调用 `this.method()` | 不经过代理，拦截器根本没被触发 | 拆到另一个 Bean；或注入自身代理 `@Lazy Self self`；或改用 `TransactionTemplate` |
| 方法不是 `public` | 5.x 的 CGLIB/JDK 代理默认只拦 public 方法 | 改为 public；或调整 `proxyTargetClass` 与 `@EnableTransactionManagement` 配置 |
| 方法或类是 `final` | 无法生成子类代理 | 去掉 `final` |
| 异常被自己 `catch` 住了 | 容器看不到异常，认为成功 | 记录日志后 `throw`；或手动 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()` |
| 抛的是受检异常 | 默认只回滚 `RuntimeException`/`Error` | `rollbackFor = Exception.class` |
| 类没有被 Spring 管理（自己 `new` 的） | 没有代理对象 | 交给容器管理 |
| 多线程/异步里操作 | 事务绑定在 `ThreadLocal` 上，子线程拿不到 | 子线程内重新开启事务，或改用编程式事务 |
| 表引擎不支持事务（MySQL MyISAM） | 数据库层就不支持 | 换 InnoDB |

### 6.3 传播行为

| 传播行为 | 有外层事务时 | 无外层事务时 | 典型用途 |
|----------|-------------|-------------|----------|
| `REQUIRED`（默认） | 加入 | 新建 | 绝大多数业务方法 |
| `REQUIRES_NEW` | 挂起外层，新建独立事务 | 新建 | 记录操作日志（主事务回滚也要留痕） |
| `NESTED` | 建保存点，内层回滚不影响外层 | 等同 `REQUIRED` | 可部分失败的批量操作 |
| `SUPPORTS` | 加入 | 以非事务方式执行 | 查询方法 |
| `NOT_SUPPORTED` | 挂起外层 | 非事务执行 | 耗时的非关键逻辑 |
| `MANDATORY` | 加入 | **抛异常** | 强制要求调用方开事务 |
| `NEVER` | **抛异常** | 非事务执行 | 明确禁止事务的场景 |

### 6.4 隔离级别

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|----------|------|-----------|------|
| `READ_UNCOMMITTED` | 可能 | 可能 | 可能 |
| `READ_COMMITTED` | 不会 | 可能 | 可能 |
| `REPEATABLE_READ`（MySQL InnoDB 默认） | 不会 | 不会 | 可能（InnoDB 用间隙锁基本规避） |
| `SERIALIZABLE` | 不会 | 不会 | 不会 |

## 7. JdbcTemplate

`JdbcTemplate` 把 JDBC 的「拿连接 → 建 Statement → 设参数 → 执行 → 遍历 ResultSet → 关资源 → 翻译异常」七步压缩成一行调用，是理解 Spring 数据访问抽象的最佳入口。

### 7.1 配置

```java
@Configuration
public class JdbcConfig {

    @Bean
    public DataSource dataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://localhost:3306/shop");
        config.setUsername("app");
        config.setPassword(System.getenv("DB_PASSWORD"));
        config.setMaximumPoolSize(10);
        return new HikariDataSource(config);
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        // JdbcTemplate 是线程安全的，容器内单例即可
        return new JdbcTemplate(dataSource);
    }

    @Bean
    public NamedParameterJdbcTemplate namedParameterJdbcTemplate(DataSource dataSource) {
        return new NamedParameterJdbcTemplate(dataSource);
    }
}
```

### 7.2 CRUD

```java
@Repository
public class OrderJdbcRepository {

    private final JdbcTemplate jdbc;
    private final NamedParameterJdbcTemplate namedJdbc;

    public OrderJdbcRepository(JdbcTemplate jdbc, NamedParameterJdbcTemplate namedJdbc) {
        this.jdbc = jdbc;
        this.namedJdbc = namedJdbc;
    }

    public int insert(Order order) {
        return jdbc.update(
                "insert into orders(sku, qty, status) values (?, ?, ?)",
                order.getSku(), order.getQty(), order.getStatus());
    }

    // 命名参数：参数一多，? 的顺序就成了维护噩梦
    public List<Order> findByStatus(String status, int limit) {
        MapSqlParameterSource params = new MapSqlParameterSource()
                .addValue("status", status)
                .addValue("limit", limit);
        return namedJdbc.query(
                "select id, sku, qty, status from orders where status = :status limit :limit",
                params,
                ROW_MAPPER);
    }

    public Optional<Order> findById(long id) {
        // queryForObject 查不到会抛 EmptyResultDataAccessException，要 Optional 得自己接
        List<Order> list = jdbc.query(
                "select id, sku, qty, status from orders where id = ?", ROW_MAPPER, id);
        return list.stream().findFirst();
    }

    public int[] batchInsert(List<Order> orders) {
        return jdbc.batchUpdate(
                "insert into orders(sku, qty, status) values (?, ?, ?)",
                new BatchPreparedStatementSetter() {
                    @Override
                    public void setValues(PreparedStatement ps, int i) throws SQLException {
                        Order o = orders.get(i);
                        ps.setString(1, o.getSku());
                        ps.setInt(2, o.getQty());
                        ps.setString(3, o.getStatus());
                    }

                    @Override
                    public int getBatchSize() {
                        return orders.size();
                    }
                });
    }

    private static final RowMapper<Order> ROW_MAPPER = (rs, rowNum) -> new Order(
            rs.getLong("id"),
            rs.getString("sku"),
            rs.getInt("qty"),
            rs.getString("status"));
}
```

> Spring 6.1 起有了更顺手的 `JdbcClient`，同一个查询可以写成 `jdbcClient.sql("...").param("status", s).query(ROW_MAPPER).list()`，详见 [[spring6#5.2 JdbcClient]]。

## 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `NoSuchBeanDefinitionException` | 类没被扫描到，或 `@ComponentScan` 范围不包含 | 检查启动类包路径；确认类上有 `@Component`/`@Service` |
| `NoUniqueBeanDefinitionException` | 同类型多个 Bean | `@Primary` 指定默认；或 `@Qualifier("beanName")` 精确指定 |
| `NullPointerException` 出现在注入字段上 | 该类是自己 `new` 的，没走容器 | 交给 Spring 管理，或改用构造器注入以便早暴露 |
| `@Transactional` 不生效 | 见 6.2 节的八个场景 | 优先检查自调用与异常被吞 |
| 切面不生效 | 目标类没被 Spring 管理；或 `@Aspect` 类没注册为 Bean | 加 `@Component`；确认 `@EnableAspectJAutoProxy` 已开启 |
| `BeanCurrentlyInCreationException` | 构造器注入构成循环依赖 | 改字段/`@Lazy` 注入；更好的做法是重构拆分职责 |
| `EmptyResultDataAccessException` | `queryForObject` 查不到记录 | 改用 `query(...).stream().findFirst()` |
| 事务提交了但数据没变 | 表引擎不支持事务，或 `@Transactional` 加在读方法上却做了写操作 | 换 InnoDB；确认注解加在写方法上 |

## See Also

- [[spring6|Spring Framework 6]]（同一套容器机制，换到 Java 17 + `jakarta.*` 底座）
- [[spring-mvc|Spring MVC]]
- [[spring-boot2|Spring Boot 2]]（Spring 5 体系的自动装配）
- [[spring-webflux|Spring WebFlux]]（5.0 引入的响应式栈）
- [[spring/index|Spring 生态目录]]
- [[java-se|Java SE 基础]]（反射、注解、动态代理是理解 AOP 的前提）

## 参考

- [Spring Framework 官方参考文档](https://docs.spring.io/spring-framework/reference/)
- [Spring Framework 版本与支持策略](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions)
- [Spring Framework 5.x 新特性](https://github.com/spring-projects/spring-framework/wiki/What%27s-New-in-Spring-Framework-5.x)
- [廖雪峰 - Spring 教程](https://liaoxuefeng.com/books/java/spring/index.html)
