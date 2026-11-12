---
title: Spring AOP 写法手册
description: Spring AOP 的实战写法：切面注册、五种通知的方法签名、切点表达式与参数绑定、通知执行顺序、代理机制与失效排查
tags:
  - spring
  - java
  - aop
  - backend
date: 2026-11-11
---

# Spring AOP 写法手册

这是一篇「怎么写」的手册：从加依赖、开自动代理，到写出能上线的切面，再到踩坑排查。

AOP 的概念模型（术语对照、为什么需要切面、代理在 Bean 生命周期的第 8 步才生成）在 [[spring5|Spring 5 核心]] 的 AOP 与 `BeanPostProcessor` 两节，这里不重复。

> **版本说明**：截至 2026 年 11 月，Spring Framework 最新 GA 为 **7.0.8**。`@AspectJ` 注解写法从 Spring 2 沿用至今，Spring 6（Java 17 + `jakarta.*`）与 Spring 7 均未改动。真正的差异只有三处：依赖坐标、Spring Boot 4 改了 starter 名、7.0 新增了 `@Proxyable`。

## 1. 接入：把自动代理打开

### 1.1 Spring Boot

```xml
<!-- Spring Boot 4.x：starter 已改名 -->
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-aspectj</artifactId>
</dependency>
```

Spring Boot 3.x 及以前叫 `spring-boot-starter-aop`；4.x 起改名为 `spring-boot-starter-aspectj`（迁移对照见 [[spring-boot4|Spring Boot 4 使用指南与发展现状]]）。

Boot 的 `AopAutoConfiguration` 会在 classpath 上存在 `aspectjweaver` 时**自动注册 `@EnableAspectJAutoProxy`**，不需要额外加注解。两个相关开关：

| 配置项 | 默认值 | 作用 |
|--------|--------|------|
| `spring.aop.auto` | `true` | 是否自动开启 AspectJ 自动代理 |
| `spring.aop.proxy-target-class` | `true`（Boot 2.x 起） | `true` 强制 CGLIB，`false` 退回「有接口用 JDK 代理」 |

### 1.2 非 Boot（纯 Spring / SSM）

```java
@Configuration
@EnableAspectJAutoProxy(proxyTargetClass = true, exposeProxy = false)
public class AopConfig {
}
```

- `proxyTargetClass = true`：强制 CGLIB。Boot 环境下由 `spring.aop.proxy-target-class` 代劳，不用写。
- `exposeProxy = true`：把代理放进 `AopContext`，才能用 `AopContext.currentProxy()`。除非万不得已不要开——原因见下文「代理机制与自调用」。

无论哪种方式，classpath 上都必须有 AspectJ 的 `org.aspectj:aspectjweaver`（1.9+）。Spring 只是借用它的注解和切点解析器，**不需要** AspectJ 编译器或织入器。

XML 老项目对应的是 `<aop:aspectj-autoproxy proxy-target-class="true"/>`，效果等价，写法见 [[ssm-integration|SSM 整合]]。

## 2. 最小可用的切面：五步

一个能跑起来的切面只做五件事：

```java
package com.example.order.aspect;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.*;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

@Aspect                       // 1. 声明这是切面
@Component                    // 2. 必须注册成 Bean，否则注解白写
@Order(1)                     // 3. 多切面时定优先级，值越小越外层
public class AuditAspect {

    // 4. 切点：抽成命名切点，供本类与其他切面复用
    @Pointcut("execution(public * com.example.order.service..*.*(..))")
    public void serviceLayer() {}

    @Before("serviceLayer()")                                   // 5. 通知
    public void before(JoinPoint jp) {
        System.out.println("enter " + jp.getSignature().toShortString());
    }
}
```

五个要素缺一不可，且**顺序无关**。最容易漏的是第 2 步：`@Aspect` 本身不带 `@Component`，不是 Bean 的类 Spring 根本不会去看它。

## 3. 五种通知的方法签名

这是写切面时唯一需要背下来的表——写错签名的报错信息通常很晦涩。

| 通知 | 执行时机 | 签名硬性要求 | 能否改变结果 |
|------|----------|--------------|--------------|
| `@Before` | 目标方法执行前 | 无返回值要求；可选加 `JoinPoint` | 不能 |
| `@AfterReturning` | 正常返回后 | `returning` 的值必须与参数名**逐字一致** | 不能替换返回值 |
| `@AfterThrowing` | 抛异常退出时 | `throwing` 的值必须与参数名一致 | 不能吞异常，要吞用 `@Around` |
| `@After` | finally，无论成败 | 需同时容忍正常/异常两种结果 | 不能 |
| `@Around` | 包住整个调用 | 返回类型必须是 `Object`；第一个参数必须是 `ProceedingJoinPoint` | 能：返回值、异常、调用次数都能改 |

### 3.1 Before / AfterReturning / AfterThrowing / After

```java
@Before("serviceLayer()")
public void before(JoinPoint jp) {
    // jp 不是必需的，只是为了拿方法签名和参数
    System.out.println("call " + jp.getSignature().toShortString());
}

@AfterReturning(pointcut = "serviceLayer()", returning = "ret")
public void afterReturning(Object ret) {
    // returning = "ret" 与形参名 ret 必须完全一致，改个名字就启动报错
    System.out.println("returned: " + ret);
}

@AfterThrowing(pointcut = "serviceLayer()", throwing = "ex")
public void afterThrowing(Throwable ex) {
    // 声明 Throwable 能接所有异常；声明具体类型则自动收窄匹配范围
    System.out.println("failed: " + ex.getClass().getSimpleName());
}

@After("serviceLayer()")
public void after(JoinPoint jp) {
    // 等价于 finally：正常返回和抛异常都会走到这里
    System.out.println("exit " + jp.getSignature().getName());
}
```

两个容易误解的点：

- `@AfterThrowing` **不是全局异常处理器**。它只能接到「目标方法自己抛出的异常」，切面里 `@After` / `@AfterReturning` 方法自己抛的异常它收不到。
- `@AfterReturning` **无法替换返回值**——想改返回值只能用 `@Around`。

### 3.2 Around：唯一能做「环绕」的通知

```java
@Around("serviceLayer()")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
    long start = System.nanoTime();
    try {
        Object result = pjp.proceed();          // 不调用它，业务方法根本不执行
        return result;                          // 必须把结果返回，否则调用方拿到 null
    } finally {
        System.out.println(pjp.getSignature().toShortString()
                + " cost " + (System.nanoTime() - start) / 1_000_000 + "ms");
    }
}
```

规则清单：

1. **返回类型必须写 `Object`**。若声明成 `void`，调用方永远拿到 `null`，`proceed()` 的返回值被直接丢弃。
2. **必须 `return pjp.proceed()` 的结果**，哪怕目标方法返回 `void`。
3. `proceed()` 可以调用 0 次、1 次或多次——0 次是缓存命中，多次是重试。
4. 用 `proceed(Object[])` 可以替换实参，例如补齐默认值。
5. 官方建议：**能用 `@Before` 就别用 `@Around`**。`@Around` 一旦忘了返回或忘了 `proceed()`，故障非常隐蔽。

## 4. 切点表达式

### 4.1 execution 的完整文法

```text
execution(modifiers-pattern?        // 可选：public / protected
          ret-type-pattern          // 必填：返回值类型，* 表示任意
          declaring-type-pattern?   // 可选：类名，后面要跟一个点
          name-pattern(param-pattern)  // 必填：方法名 + 参数
          throws-pattern?)          // 可选：异常声明
```

参数部分的三种写法：`()` 无参、`(..)` 任意个参数、`(*)` 一个任意类型参数、`(*,String)` 两个参数且第二个是 `String`。

### 4.2 Spring AOP 支持的切点指示符（PCD）

| PCD | 匹配对象 | 典型用途 |
|-----|----------|----------|
| `execution` | 方法执行 | **主力**，90% 的切面用它 |
| `within` | 指定类型内的所有方法 | 整包/整类拦截，不关心方法签名 |
| `this` | 代理对象是指定类型的实例 | 区分 JDK 代理场景 |
| `target` | 目标对象是指定类型的实例 | 绑定目标对象、按实现类拦截 |
| `args` | 实参是指定类型 | 按入参类型拦截并绑定参数 |
| `@target` | 执行对象所属类有该注解 | 类级注解 |
| `@args` | 实参的**运行时类型**有该注解 | 少见 |
| `@within` | 方法**声明在**带该注解的类型里 | 类级注解，与 `@target` 近似 |
| `@annotation` | **被调用的方法**上有该注解 | 自定义注解驱动切面，最常用 |

**不支持的**：`call`、`get`、`set`、`initialization`、`preinitialization`、`staticinitialization`、`handler`、`adviceexecution`、`withincode`、`cflow`、`cflowbelow`、`if`、`@this`、`@withincode`。在 Spring AOP 里写了会直接抛 `IllegalArgumentException`——这些是完整 AspectJ 的能力，需要编译期/加载期织入才有。

### 4.3 组合与命名切点复用

```java
public class CommonPointcuts {

    @Pointcut("within(com.example.order.service..*)")
    public void inServiceLayer() {}

    @Pointcut("execution(public * *(..))")
    public void publicMethod() {}

    @Pointcut("inServiceLayer() && publicMethod()")
    public void serviceOperation() {}

    // 只对加了注解的方法生效，同时把注解实例绑定给通知
    @Pointcut("@annotation(com.example.order.aspect.Auditable)")
    public void auditable() {}
}
```

跨类引用时写**全限定名 + 方法名**：

```java
@Before("com.example.order.aspect.CommonPointcuts.serviceOperation()")
public void check(JoinPoint jp) { }
```

官方推荐把常用切点集中到一个 `CommonPointcuts` 类里，再由各处组合——否则每个切面各写一遍 `execution(...)`，改包名时全库 grep。

## 5. 参数与上下文

### 5.1 JoinPoint 能拿到什么

| 方法 | 返回 | 说明 |
|------|------|------|
| `getArgs()` | `Object[]` | 方法实参，改它会改实际调用（`@Around` 里） |
| `getThis()` | `Object` | 代理对象 |
| `getTarget()` | `Object` | 目标对象（原始 Bean） |
| `getSignature()` | `Signature` | `getName()` / `getDeclaringTypeName()` / `toShortString()` |
| `getKind()` | `String` | Spring AOP 恒为 `method-execution` |

`ProceedingJoinPoint` 继承自 `JoinPoint`，多了 `proceed()` 和 `proceed(Object[])`。

### 5.2 三种常见的参数绑定

```java
// 1) 绑定方法参数：args(名字) 中写变量名而非类型名
@Before("execution(* com.example.order.service.*.*(..)) && args(cmd,..)")
public void beforeCreate(OrderCommand cmd) {
    // 双重作用：既是匹配条件（第一个参数是 OrderCommand），也是绑定
}

// 2) 绑定方法上的注解
@Around("@annotation(auditable)")
public Object around(ProceedingJoinPoint pjp, Auditable auditable) throws Throwable {
    return pjp.proceed();
}

// 3) 绑定目标对象
@Before("target(orderService) && execution(* *(..))")
public void before(OrderService orderService) { }
```

**绑定泛型集合会失败**：`args(param)` 配 `Collection<Order> param` 不生效（擦除后无法校验元素、也无法处理 `null`）。要么改成 `Collection<?>` 自己判元素类型，要么别绑。

### 5.3 参数名从哪来

绑定依赖「切点里的变量名 == 通知方法的形参名」。Spring 依次尝试 `AspectJAnnotationParameterNameDiscoverer`（读 `argNames`）→ `KotlinReflection...` → `StandardReflection...`（需要 `-parameters`）→ `AspectJAdviceParameterNameDiscoverer`（从表达式反推）。

编译期没加 `-parameters`、又推不出来时，启动就报 `Name for argument of type [...] not specified`。两种解法：

```xml
<!-- 方案一：编译时保留参数名（推荐） -->
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-compiler-plugin</artifactId>
  <configuration>
    <parameters>true</parameters>
  </configuration>
</plugin>
```

```java
// 方案二：显式声明 argNames（第一个 JoinPoint 参数可以省略不写）
@Before(value = "serviceOperation() && args(cmd,..)", argNames = "cmd")
public void before(JoinPoint jp, OrderCommand cmd) { }
```

Gradle 对应 `tasks.withType(JavaCompile) { options.compilerArgs << '-parameters' }`；Spring Boot 的 parent / starter 默认已开启该参数。

## 6. 执行顺序

### 6.1 不同切面之间

用 `@Order(n)` 或实现 `Ordered`，**值越小优先级越高**。

- 「进入」方向：优先级高的**先**执行。
- 「退出」方向：优先级高的**后**执行（先进后出，像栈）。

```text
Order(1) 的前置 → Order(2) 的前置 → 目标方法 → Order(2) 的后置 → Order(1) 的后置
```

事务切面默认是 `Ordered.LOWEST_PRECEDENCE`（最内层），所以自定义切面想包在事务外层必须显式给更小的值；想读已提交的数据则要给它更大的值。

### 6.2 同一个切面内部

| 优先级（从高到低） | 通知 |
|--------------------|------|
| 1 | `@Around` |
| 2 | `@Before` |
| 3 | `@After` |
| 4 | `@AfterReturning` |
| 5 | `@AfterThrowing` |

注意 `@After` 排在这里的语义是「after finally」：它会在 `@AfterReturning` / `@AfterThrowing` **之后**执行。此外，**同一个切面里同类型的多个通知执行顺序是未定义的**——需要确定顺序就合并成一个方法，或拆成两个可用 `@Order` 排序的切面。

## 7. 代理机制与自调用

### 7.1 先判断手上的对象是不是代理

```java
import org.springframework.aop.support.AopUtils;
import org.springframework.test.util.AopTestUtils;

AopUtils.isAopProxy(bean);        // 是否为 AOP 代理
AopUtils.isCglibProxy(bean);      // 是否为 CGLIB 代理
AopUtils.getTargetClass(bean);    // 穿透代理拿到真实类型
AopTestUtils.getTargetObject(bean); // 测试里拿到原始对象（spring-test）
```

JDK 代理与 CGLIB 的完整对比在 [[spring5|Spring 5 核心]] 的 5.3 节。写代码时只需记住三条结论：

- 目标是 `final` 类 / `final` 方法 / `private` 方法 → **无法拦截**（CGLIB 无法覆写）。
- 有接口时默认走 JDK 代理，注入和强转都必须用**接口类型**；Boot 默认 `proxy-target-class=true`，一律 CGLIB，所以给 `@RestController` 加切面不需要接口。
- `@Aspect` 类自己**不会被其他切面代理**（否则会无限递归），所以别在切面类上再挂 `@Transactional`。

### 7.2 自调用为什么失效

代理只在「外部调用穿过来」时起作用。`this.bar()` 是对原始对象的直接调用，压根没经过代理：

```java
@Service
public class OrderService {

    public void placeOrder(OrderCommand cmd) {
        this.doSave(cmd);        // ❌ 自调用，doSave 上的切面/事务全部失效
    }

    @Transactional(rollbackFor = Exception.class)
    public void doSave(OrderCommand cmd) { /* ... */ }
}
```

三种解法，从好到坏：

```java
// 方案一（首选）：拆类，让调用从外部穿过代理
@Service
public class OrderService {
    private final OrderWriter writer;
    public void placeOrder(OrderCommand cmd) { writer.doSave(cmd); }   // ✅ 走代理
}

// 方案二：自注入，拿到自己的代理引用
@Service
public class OrderService {
    private final ObjectProvider<OrderService> self;   // 用 Provider 避免循环依赖告警
    public void placeOrder(OrderCommand cmd) {
        self.getObject().doSave(cmd);                  // ✅ 走代理
    }
}

// 方案三（官方明确不推荐）：绑定到 Spring AOP，需要 exposeProxy = true
public void placeOrder(OrderCommand cmd) {
    ((OrderService) AopContext.currentProxy()).doSave(cmd);   // ❌ 与 Spring 强耦合
}
```

### 7.3 Spring Framework 7.0：按 Bean 指定代理类型

7.0 起可以用 `@Proxyable`（`org.springframework.context.annotation.Proxyable`）标注 `@Bean` 方法或 `@Component` 类，覆盖全局默认：

```java
@Proxyable(TARGET_CLASS)     // 强制 CGLIB；写成 INTERFACES 则强制 JDK 动态代理
@Component
public class OrderService { }
```

枚举类型是 `Proxyable.ProxyType`（`DEFAULT` / `INTERFACES` / `TARGET_CLASS`），实际书写时静态导入常量即可。同时 7.0 统一了代理默认值的传播——`@EnableAsync` 这类单独的代理处理器现在也会遵循全局的 `proxyTargetClass` 设置。

## 8. 完整例子：注解驱动的操作日志

把「打日志 + 计时 + 异常记录」从业务代码里彻底拿掉，是切面最典型的落地场景。

### 8.1 自定义注解

```java
package com.example.order.aspect;

import java.lang.annotation.*;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface OperationLog {

    /** 操作名，写进日志的 action 字段 */
    String value();

    /** 是否打印入参，涉及手机号/身份证的方法置 false */
    boolean logArgs() default true;
}
```

### 8.2 切面

依赖 Lombok 的 `@Slf4j`（提供 `log` 字段）与 `org.springframework.core.Ordered`、`java.util.Arrays` 两个导入。

```java
@Slf4j
@Aspect
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)   // 尽量在外层，才能统计到内层切面的耗时
public class OperationLogAspect {

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint pjp, OperationLog operationLog) throws Throwable {
        String method = pjp.getSignature().toShortString();
        if (operationLog.logArgs()) {
            log.info("[{}] {} 入参={}", operationLog.value(), method, Arrays.toString(pjp.getArgs()));
        }

        long start = System.nanoTime();
        try {
            Object result = pjp.proceed();
            return result;
        } catch (Throwable ex) {
            // 只记录不吞：吞掉异常会让上层事务和调用方都以为成功
            log.warn("[{}] {} 失败: {}", operationLog.value(), method, ex.toString());
            throw ex;
        } finally {
            log.info("[{}] {} 耗时 {}ms", operationLog.value(), method,
                    (System.nanoTime() - start) / 1_000_000);
        }
    }
}
```

### 8.3 使用

```java
@Service
public class OrderService {

    @OperationLog(value = "下单", logArgs = false)
    @Transactional(rollbackFor = Exception.class)
    public void placeOrder(OrderCommand cmd) {
        // 业务代码里不再有任何日志样板
    }
}
```

> **注意**：`Arrays.toString(pjp.getArgs())` 只适合排查期。生产环境打全量入参有两个风险——日志里出现敏感信息（手机号、token）、大对象拖慢日志。稳妥做法是配 Jackson 序列化 + 字段脱敏，或默认 `logArgs = false`。

## 9. 引入（Introduction）：给对象「加」接口

`@DeclareParents` 能让被切中的类凭空获得一个新接口的能力，适合给存量类补横切能力（如统一加 `Auditable` 标记接口）：

```java
@Aspect
@Component
public class AuditableIntroduction {

    // value 里的 + 表示「该类型及其子类型」
    @DeclareParents(value = "com.example.order.service.*+", defaultImpl = DefaultAuditable.class)
    public static Auditable auditable;
}
```

用的时候把 Bean 强转成 `Auditable` 即可。注意它同样受代理机制约束：JDK 代理下只有接口方法可见。

## 10. 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 切面完全不生效，日志一行没有 | 切面类不是 Bean（漏了 `@Component`） | 补 `@Component`，或确认包在扫描范围内 |
| 启动报 `Name for argument of type [...] not specified` | 编译没带 `-parameters`，参数名推断不出来 | 加编译器 `-parameters`，或显式写 `argNames` |
| 启动报 `IllegalArgumentException: Pointcut is not well-formed` | 用了 Spring AOP 不支持的 PCD（`call`/`cflow` 等） | 改写成 `execution` / `within` |
| 报 `Cannot subclass final class` | 目标类是 `final`，CGLIB 无法继承 | 去掉 `final`，或让它实现接口走 JDK 代理 |
| `final` / `private` 方法怎么都不被拦截 | 无法覆写，代理拿不到 | 改成非 `final` 的 public/protected 方法 |
| 注入时 `ClassCastException` / `NoSuchBeanDefinition` | 注入的是实现类，但走的是 JDK 接口代理 | 改成注入接口类型，或开 `proxyTargetClass` |
| `@Transactional` 在同类内部调用时失效 | 自调用绕过代理 | 拆类 / 自注入代理，见 7.2 |
| `AopContext.currentProxy()` 抛 `IllegalStateException` | 没开 `exposeProxy` | `@EnableAspectJAutoProxy(exposeProxy = true)`；仍建议改掉这个写法 |
| `@AfterReturning` 拿不到返回值 | `returning` 名与形参名不一致 | 两边改成完全相同的名字 |
| `@Around` 之后调用方拿到 `null` | 忘记 `return pjp.proceed()`，或返回类型写成了 `void` | 返回类型改 `Object` 并 return |
| 切面里的 `@Autowired` 字段是 `null` | 切面实例被手工 `new` 出来，不在容器里 | 确保切面由 Spring 创建 |
| 两个切面执行顺序和预期相反 | `@Order` 值理解反了，或同一切面内同类型通知顺序未定义 | 值小的在外层；同类型通知合并成一个方法 |
| 给 `@Aspect` 类加了 `@Transactional` 无效 | 切面自身不参与自动代理 | 把事务挪到目标 Bean 上 |

## See Also

- [[spring5|Spring 5 核心]] —— AOP 术语、代理生成时机（`BeanPostProcessor`）、切点表达式速查
- [[spring-security|Spring Security 指南]] —— 方法级安全就是 AOP 的官方落地，自调用坑同源
- [[spring7|Spring Framework 7]] —— `@Proxyable`、`@Retryable` 等 7.0 新特性
- [[spring-boot4|Spring Boot 4 使用指南与发展现状]] —— starter 改名等迁移项
- [[ssm-integration|SSM 整合]] —— 基于 XML 的 AOP 配置（老项目维护用）
- [[spring-mvc|Spring MVC]] —— `@ControllerAdvice` 与 AOP 的分工

## 参考

- [@AspectJ support](https://docs.spring.io/spring-framework/reference/core/aop/ataspectj.html)
- [Declaring a Pointcut](https://docs.spring.io/spring-framework/reference/core/aop/ataspectj/pointcuts.html)
- [Declaring Advice](https://docs.spring.io/spring-framework/reference/core/aop/ataspectj/advice.html)
- [Proxying Mechanisms](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)
- [Spring AOP APIs](https://docs.spring.io/spring-framework/reference/core/aop/api.html)
