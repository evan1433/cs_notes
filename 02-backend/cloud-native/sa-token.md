---
title: Sa-Token 权限认证框架
description: Sa-Token 登录认证、权限与角色鉴权、Session 会话、Redis 持久化、微服务网关鉴权、SSO 与 OAuth2 的完整实践笔记
tags:
  - java
  - spring-boot
  - auth
  - sa-token
date: 2026-10-28
---

# Sa-Token 权限认证框架

开源仓库：<https://github.com/dromara/sa-token>

Sa-Token 是 Dromara 社区的国产轻量级 Java 权限认证框架，用"一个静态工具类 + 少量配置"覆盖登录认证、权限与角色鉴权、Session 会话、踢人下线、SSO 单点登录、OAuth2.0、微服务网关鉴权等一整条链路上会遇到的鉴权问题。它的核心卖点不是功能多，而是**把"校验当前请求是谁、有没有权限"这件事的调用成本压到一行代码**：`StpUtil.login(10001)` 完成登录，`StpUtil.checkLogin()` 完成校验，`@SaCheckPermission("user:add")` 完成方法级鉴权。

本文以 **v1.46.0** 为基线（截至 2026 年 10 月官方文档站头部标注的最新版本）。配置项与 API 签名均对照 `SaTokenConfig` / `StpUtil` 源码核对过。

## 1. 定位与取舍

### 1.1 与 Spring Security、Apache Shiro 的对比

选鉴权框架本质是选"复杂度放在哪里"。三者都能用，但心智负担的分布完全不同：

| 维度 | Sa-Token | Spring Security | Apache Shiro |
|------|----------|-----------------|--------------|
| API 形态 | 静态工具类 `StpUtil.xxx()` | 过滤器链 + DSL 配置 | `Subject` + 自定义 `Realm` |
| 最小可用成本 | 加依赖，`StpUtil.login(id)` | 理解 `SecurityFilterChain`、`UserDetailsService`、`PasswordEncoder` 等 | 实现 `Realm`、配置过滤器链 |
| 侵入性 | 低，不强制实现任何接口 | 中高，深度绑定 Spring 生态 | 中 |
| 会话存储 | 默认内存，可切 Redis / 自定义 `SaTokenDao` | `HttpSession` / 自定义 | `SessionDAO` |
| 微服务方案 | 官方提供网关鉴权、RPC 上下文传递、Same-Token | 需自行扩展或用 Spring Cloud Security | 无官方方案 |
| 中文资料 | 官方文档即中文，示例齐全 | 主要依赖英文文档 | 文档偏旧，社区活跃度下降 |

**选型建议**：内部系统、中后台、微服务网关鉴权这类"要快、要可控、要中文资料"的场景，Sa-Token 的性价比最高；如果需要深度定制 Spring 生态安全能力（如 LDAP、SAML、复杂 CSRF 策略），Spring Security 仍是更稳妥的选择。

### 1.2 模块全景

| 模块 | artifactId | 作用 |
|------|-----------|------|
| 核心 | `sa-token-core` | 零第三方依赖的内核，一般不直接引入 |
| Servlet 集成 | `sa-token-spring-boot-starter`（Boot 3 用 `-3`，Boot 4 用 `-4`） | SpringMVC / Spring Boot 环境 |
| Reactor 集成 | `sa-token-reactor-spring-boot-starter`（同理带 `-3`/`-4`） | WebFlux、Spring Cloud Gateway |
| Redis 持久化 | `sa-token-redis-template`、`sa-token-redis-jackson` | 会话数据落 Redis |
| 独立 Redis | `sa-token-alone-redis` | 权限缓存与业务缓存物理隔离 |
| JWT | `sa-token-jwt`、`sa-token-temp-jwt` | 无状态令牌、临时令牌 |
| 单点登录 | `sa-token-sso` | 三种 SSO 模式 |
| OAuth2.0 | `sa-token-oauth2` | 搭建授权中心 |
| 其它 | `sa-token-apikey`、`sa-token-sign`、`sa-token-context-dubbo`、`sa-token-context-grpc` | API Key 授权、参数签名、RPC 上下文传递 |

## 2. 快速接入

### 2.1 依赖坐标

`groupId` 统一为 `cn.dev33`。**starter 的artifactId 必须和 Spring Boot 大版本对齐**，这是新手最常见的错误来源：

| 运行环境 | artifactId |
|----------|-----------|
| Spring Boot 2.x | `sa-token-spring-boot-starter` |
| Spring Boot 3.x | `sa-token-spring-boot3-starter` |
| Spring Boot 4.x | `sa-token-spring-boot4-starter` |
| WebFlux / Gateway（Boot 2.x） | `sa-token-reactor-spring-boot-starter` |
| WebFlux / Gateway（Boot 3.x） | `sa-token-reactor-spring-boot3-starter` |

```xml
<properties>
    <sa-token.version>1.46.0</sa-token.version>
</properties>

<dependencies>
    <!-- Sa-Token 权限认证（Spring Boot 3.x 请改用 sa-token-spring-boot3-starter） -->
    <dependency>
        <groupId>cn.dev33</groupId>
        <artifactId>sa-token-spring-boot-starter</artifactId>
        <version>${sa-token.version}</version>
    </dependency>
</dependencies>

<!-- 多模块同时引入 starter / redis / jwt 时，用 BOM 统一版本可避免版本漂移 -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>cn.dev33</groupId>
            <artifactId>sa-token-bom</artifactId>
            <version>${sa-token.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

> JDK 要求 8+，Spring Boot 建议 2.0 以上。

### 2.2 最小可运行示例

框架可以**零配置启动**，下面这段代码不需要任何配置文件就能跑：

```java
@RestController
@RequestMapping("/user/")
public class UserController {

    // 会话登录：参数填写登录人的账号 id
    @RequestMapping("doLogin")
    public SaResult doLogin(String name, String pwd) {
        // 此处仅作模拟，真实项目需校验数据库中的账号密码
        if ("zhang".equals(name) && "123456".equals(pwd)) {
            StpUtil.login(10001);
            return SaResult.ok("登录成功")
                    .setData(StpUtil.getTokenValue());
        }
        return SaResult.error("登录失败");
    }

    // 查询登录状态
    @RequestMapping("isLogin")
    public SaResult isLogin() {
        return SaResult.ok("是否登录：" + StpUtil.isLogin());
    }

    // 校验登录：未登录时抛出 NotLoginException
    @RequestMapping("info")
    public SaResult info() {
        StpUtil.checkLogin();
        return SaResult.ok("账号 id：" + StpUtil.getLoginId());
    }

    @RequestMapping("logout")
    public SaResult logout() {
        StpUtil.logout();
        return SaResult.ok();
    }
}
```

### 2.3 常用配置项

```yaml
sa-token:
  # token 名称，同时也是 cookie 名称、请求头名称
  token-name: satoken
  # token 有效期（秒），默认 30 天，-1 代表永久有效
  timeout: 2592000
  # token 最低活跃频率（秒）：超过此时间未访问系统则冻结，默认 -1 表示不限制
  active-timeout: -1
  # 是否允许同一账号多地同时登录（false 时新登录挤掉旧登录）
  is-concurrent: true
  # 多人登录同一账号时是否共用一个 token（false 时每次登录新建 token）
  is-share: false
  # token 风格：uuid / simple-uuid / random-32 / random-64 / random-128 / tik
  token-style: uuid
  # 是否写入响应头（前后端分离场景常设为 true）
  is-write-header: false
  # 是否输出操作日志
  is-log: true
```

其它源码中确认存在的配置项（按需使用）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `is-read-header` | `true` | 是否从请求头读取 token |
| `is-read-body` | `true` | 是否从请求体读取 token |
| `is-read-cookie` | `true` | 是否从 Cookie 读取 token |
| `auto-renew` | `true` | 是否自动续签 |
| `token-prefix` | 空 | token 前缀，如 `Bearer` |
| `max-login-count` | `12` | 同一账号最多登录数量 |
| `replaced-range` | `CURR_DEVICE_TYPE` | 顶替范围：同端 / 全部端 |
| `logout-range` | `TOKEN` | 注销范围：仅 token / 整个账号 |
| `check-same-token` | `false` | 是否校验 Same-Token（微服务内部调用） |

## 3. 登录认证核心 API

### 3.1 登录、注销与校验

`StpUtil` 是门面类，所有方法都是静态的，底层委托给可替换的 `StpLogic` 实例：

```java
// —— 登录 ——
StpUtil.login(10001);                    // 按全局配置登录
StpUtil.login(10001, "PC");              // 指定设备类型登录
StpUtil.login(10001, 60 * 60 * 24 * 7);  // 单独指定本次登录有效期

// —— 注销 / 踢人 ——
StpUtil.logout();                        // 当前会话注销
StpUtil.logout(10001);                   // 指定账号全部端下线
StpUtil.logout(10001, "PC");             // 指定账号指定端下线
StpUtil.kickout(10001);                  // 强制踢下线（冻结标记与上者不同）
StpUtil.replaced(10001);                 // 顶替下线（记为"被顶替"）
StpUtil.logoutByTokenValue(tokenValue);  // 按 token 值注销

// —— 校验与读取 ——
StpUtil.isLogin();                       // 返回 boolean
StpUtil.checkLogin();                    // 未登录抛 NotLoginException
StpUtil.getLoginId();                    // 未登录抛异常
StpUtil.getLoginIdDefaultNull();         // 未登录返回 null
StpUtil.getLoginIdAsString();            // 以 String 形式返回
StpUtil.getTokenValue();                 // 当前请求的 token 值
StpUtil.getTokenInfo();                  // tokenName / tokenValue / loginDeviceType 等
```

> `logout` / `kickout` / `replaced` 的区别在于**给会话打的状态标记不同**：注销可以再次登录；踢下线会写入冻结标记，在 `timeout` 内不允许再登录；顶替下线用于"被新登录挤掉"的语义区分。

### 3.2 登录参数细粒度控制

需要覆盖全局配置时，传 `SaLoginParameter`：

```java
StpUtil.login(10001, new SaLoginParameter()
        .setDeviceType("APP")            // 设备类型，用于多端登录隔离
        .setTimeout(60 * 60 * 2)         // 本次登录有效期 2 小时
        .setIsConcurrent(false)          // 本次登录不允许并发
        .setIsLastingCookie(true)        // Cookie 持久化（记住我）
        .setExtra("tenantId", 7));       // 附加业务数据，随会话保存

// 读取附加数据
Object tenantId = StpUtil.getExtra("tenantId");
```

### 3.3 多端登录与同端互斥

"能不能多地同时登录""多地登录是否共用 token""顶替的是同端还是全部端"，由三个配置共同决定：

| 需求 | `is-concurrent` | `is-share` | `replaced-range` |
|------|-----------------|-----------|------------------|
| 允许多地同时登录，各自独立 token | `true` | `false` | — |
| 允许多地登录，但共用一个 token | `true` | `true` | — |
| 单端登录，新登录挤掉旧登录（全部端） | `false` | `false` | `ALL_DEVICE_TYPE` |
| 同端互斥（手机挤手机，不影响 PC） | `false` | `false` | `CURR_DEVICE_TYPE` |

```yaml
sa-token:
  is-concurrent: false      # 不允许并发登录
  is-share: false
  replaced-range: CURR_DEVICE_TYPE   # 只顶替同设备类型
  replaced-login-exit-mode: OLD_DEVICE
```

## 4. 权限认证与角色认证

### 4.1 提供权限数据源：StpInterface

框架不关心权限从哪来，只要求你实现 `StpInterface` 告诉它"某个账号有哪些权限码 / 角色标识"：

```java
@Component   // 必须被 Spring 扫描到，否则鉴权永远失败
public class StpInterfaceImpl implements StpInterface {

    @Autowired
    private PermissionMapper permissionMapper;

    // 返回账号拥有的权限码集合
    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        return permissionMapper.selectCodeByUserId((Long) loginId);
    }

    // 返回账号拥有的角色标识集合
    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        return permissionMapper.selectRoleByUserId((Long) loginId);
    }
}
```

> 生产环境建议把权限码缓存到 [[redis|Redis]]，在 `getPermissionList` 中先读缓存、未命中再查库，避免每次鉴权都打数据库。

### 4.2 校验 API 对照

| 语义 | 权限 | 角色 |
|------|------|------|
| 取集合 | `getPermissionList()` | `getRoleList()` |
| 判断（返回 boolean） | `hasPermission("user:add")` | `hasRole("admin")` |
| 全部满足 | `hasPermissionAnd("a", "b")` | `hasRoleAnd("admin", "hr")` |
| 任一满足 | `hasPermissionOr("a", "b")` | `hasRoleOr("admin", "hr")` |
| 校验（不通过抛异常） | `checkPermission("user:add")` | `checkRole("admin")` |
| 校验全部满足 | `checkPermissionAnd("a", "b")` | `checkRoleAnd("admin", "hr")` |

以上方法都有 `xxx(loginId, ...)` 重载，可对**任意账号**做校验而不只是当前会话。

权限码支持 `*` 通配符：`"art.*"` 表示拥有 `art` 模块下的所有权限。

### 4.3 全局异常处理

`checkXxx` 系列失败时抛异常，统一转成前端可读的响应：

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(SaTokenException.class)
    public SaResult handleSaTokenException(SaTokenException e) {
        if (e instanceof NotLoginException) {
            return SaResult.error("未登录或登录已失效").setCode(401);
        }
        if (e instanceof NotPermissionException) {
            return SaResult.error("权限不足").setCode(403);
        }
        if (e instanceof NotRoleException) {
            return SaResult.error("角色不匹配").setCode(403);
        }
        if (e instanceof DisableServiceException) {
            return SaResult.error("账号已被封禁").setCode(403);
        }
        return SaResult.error(e.getMessage()).setCode(500);
    }
}
```

## 5. 两种鉴权方式：注解 vs 路由拦截

### 5.1 前置条件：注册拦截器

**注解鉴权和路由拦截鉴权都必须先注册 `SaInterceptor`**，否则注解完全不生效（这是最常见的"注解加了没反应"的原因）：

```java
@Configuration
public class SaTokenConfigure implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor())
                .addPathPatterns("/**")
                .excludePathPatterns("/user/doLogin", "/favicon.ico", "/error");
    }
}
```

### 5.2 注解鉴权

```java
@RestController
@RequestMapping("/at/")
public class AtController {

    @SaCheckLogin                                  // 登录即可访问
    @RequestMapping("checkLogin")
    public SaResult checkLogin() { return SaResult.ok(); }

    @SaCheckPermission("user:add")                 // 需要指定权限
    @RequestMapping("add")
    public SaResult add() { return SaResult.ok(); }

    @SaCheckPermission({"user:add", "user:delete"})
    @RequestMapping("batch")
    public SaResult batch() { return SaResult.ok(); }   // 默认全部满足

    @SaCheckPermission(value = {"user:add", "user:delete"}, mode = SaMode.OR)
    @RequestMapping("batchOr")
    public SaResult batchOr() { return SaResult.ok(); } // 任一满足即可

    @SaCheckRole("admin")                          // 需要指定角色
    @RequestMapping("admin")
    public SaResult admin() { return SaResult.ok(); }

    @SaCheckSafe                                   // 需要二级认证
    @RequestMapping("transfer")
    public SaResult transfer() { return SaResult.ok(); }

    @SaIgnore                                      // 打在类上时，放行个别方法
    @RequestMapping("publicInfo")
    public SaResult publicInfo() { return SaResult.ok(); }
}
```

可用注解：`@SaCheckLogin`、`@SaCheckRole`、`@SaCheckPermission`、`@SaCheckSafe`、`@SaCheckDisable`、`@SaCheckHttpBasic`、`@SaCheckHttpDigest`、`@SaIgnore`，以及组合式的 `@SaCheckOr`。

### 5.3 路由拦截鉴权

按 URL 批量划分鉴权规则，适合"整个模块统一要求某权限"的场景：

```java
@Configuration
public class SaTokenConfigure implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handler -> {
            SaRouter.match("/user/**", r -> StpUtil.checkPermission("user"));
            SaRouter.match("/admin/**", r -> StpUtil.checkPermission("admin"));
            SaRouter.match("/goods/**", r -> StpUtil.checkPermission("goods"));

            // 排除登录接口：其它路径一律要求登录
            SaRouter.match("/**", "/user/doLogin", r -> StpUtil.checkLogin());
        })).addPathPatterns("/**");
    }
}
```

### 5.4 两种方式怎么选

| 方式 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| 注解鉴权 | 规则就近写在业务方法旁，可读性强 | 规则散落各处，难以全局审视 | 权限点与业务强绑定的接口 |
| 路由拦截 | 集中管理，一眼看清全站规则 | 与方法解耦，改 URL 易漏改规则 | 按模块/路由划分的权限模型 |

实际项目通常**组合使用**：全局用路由拦截兜底登录校验，个别敏感接口用注解叠加权限校验。

## 6. Session 会话模型

Sa-Token 提供三级会话，从"账号维度"到"单次登录维度"逐级细分：

| 会话类型 | 获取方式 | 数据归属 | 典型用途 |
|----------|----------|----------|----------|
| User-Session | `StpUtil.getSession()` | 同一账号的所有登录共享 | 用户资料、购物车等跨端数据 |
| Token-Session | `StpUtil.getTokenSession()` | 仅当前这一次登录独享 | 当前设备的临时状态 |
| 自定义 Session | `SaSessionCustomUtil.getSessionById("shop-1")` | 任意业务 id 绑定 | 房间、直播间等"非账号主体" |

```java
// User-Session：账号维度，手机端和 PC 端共享同一份数据
SaSession session = StpUtil.getSession();
session.set("nickname", "张三");

// Token-Session：仅当前登录端可见
StpUtil.getTokenSession().set("lastVisitPath", "/goods/1");

// 自定义 Session：以业务 id 为主体，与账号无关
SaSession roomSession = SaSessionCustomUtil.getSessionById("room-1001");
roomSession.set("onlineCount", 20);
```

> 选择依据只有一条：**数据的生命周期和谁对齐**。跟随账号走用 User-Session，跟随单次登录走用 Token-Session，跟随业务实体走用自定义 Session。

## 7. 会话治理

```java
// —— 封禁 ——
StpUtil.disable(10001, 60 * 60 * 24);            // 封禁 24 小时
StpUtil.disable(10001, "comment", 3600);         // 只封禁"评论"业务
StpUtil.disableLevel(10001, 3, 3600);            // 按处罚阶梯封禁
StpUtil.isDisable(10001);
StpUtil.untieDisable(10001);

// —— 二级认证（敏感操作前再次验证）——
StpUtil.openSafe(600);        // 开启二级认证，有效期 600 秒
StpUtil.checkSafe();          // 校验
StpUtil.isSafe();
StpUtil.closeSafe();

// —— 身份切换（运维代客操作）——
StpUtil.switchTo(10002);      // 临时切换到 10002 的身份
StpUtil.isSwitch();           // 是否处于切换态
StpUtil.endSwitch();          // 结束切换

// —— 会话查询 ——
StpUtil.getTokenValueByLoginId(10001);              // 该账号的 token 值
StpUtil.getTokenValueListByLoginId(10001);          // 全部 token 列表
StpUtil.getTerminalListByLoginId(10001);            // 该账号的终端列表
StpUtil.searchTokenValue("1000", 0, 10, false);     // 按关键字搜索会话
StpUtil.renewTimeout(60 * 60 * 24 * 7);             // 手动续签
```

## 8. 前后端分离与 Token 传递

默认同时从 **Cookie、请求头、请求体**三处读取 token（分别由 `is-read-cookie` / `is-read-header` / `is-read-body` 控制，默认均为 `true`）。前后端分离项目中，前端按 `token-name` 的值放进请求头即可：

```bash
curl -H "satoken: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
     http://localhost:8081/user/info
```

如果希望响应中也回写 token（`is-write-header: true`），前端就能从响应头拿到续签后的值。跨域场景下还需配合 CORS 允许该请求头，参见 [[http-protocol|HTTP 协议]]。

## 9. 持久化：集成 Redis

### 9.1 依赖改名警告

**从 v1.34 之后 Redis 插件做过一轮改名**，很多旧博客里的坐标已经拉不到包：

| 序列化方式 | 旧坐标（≤ 1.34.0） | 当前坐标 |
|-----------|-------------------|----------|
| Jackson（可读，推荐） | `sa-token-dao-redis-jackson` | `sa-token-redis-jackson` |
| JDK 原生序列化 | `sa-token-dao-redis` | `sa-token-redis-template-jdk-serializer` |
| Redisson | `sa-token-dao-redisson-jackson` | `sa-token-redisson-jackson` |

```xml
<dependency>
    <groupId>cn.dev33</groupId>
    <artifactId>sa-token-redis-template</artifactId>
    <version>${sa-token.version}</version>
</dependency>
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-pool2</artifactId>
</dependency>
```

> 引入依赖不等于连上了 Redis，仍需 `spring-boot-starter-data-redis` 与 `spring.data.redis.*` 连接配置。切换存储介质后，内存模式下的旧 token 会全部失效，属于预期行为。

### 9.2 独立 Redis

权限数据与业务缓存混在同一个 Redis 实例时，一次 `FLUSHDB` 就会把所有用户踢下线。用 `sa-token-alone-redis` 做物理隔离：

```yaml
sa-token:
  alone-redis:
    database: 2
    host: 127.0.0.1
    port: 6379
    timeout: 10s
spring:
  redis:
    database: 0
    host: 127.0.0.1
    port: 6379
```

## 10. 多账号体系

一个系统存在两套账号（如商城的 `user` 表与后台的 `admin` 表）时，用不同 `loginType` 的 `StpLogic` 隔离，两者的会话、权限、配置完全独立：

```java
public class StpUserUtil {
    // 账号类型标识，不能与默认的 "login" 重复
    public static final String TYPE = "user";
    public static StpLogic stpLogic = new StpLogic(TYPE);

    public static void login(Object id) { stpLogic.login(id); }
    public static void checkLogin() { stpLogic.checkLogin(); }
    public static Object getLoginId() { return stpLogic.getLoginId(); }
    public static void logout() { stpLogic.logout(); }
}
```

`StpInterface` 的两个方法都会收到 `loginType` 参数，据此返回不同体系的权限数据。

## 11. 分布式与微服务鉴权

典型架构：**网关统一鉴权 + 内部服务信任网关**。子服务不重复解析用户 token，而是校验网关签发的 Same-Token，防止外部绕过网关直连内部服务。

```java
// 网关侧：为转发请求追加 Same-Token 头
@Component
public class ForwardAuthFilter implements GlobalFilter {
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest newRequest = exchange.getRequest().mutate()
                .header(SaSameUtil.SAME_TOKEN, SaSameUtil.getToken())
                .build();
        return chain.filter(exchange.mutate().request(newRequest).build());
    }
}
```

```yaml
sa-token:
  # 网关与子服务约定同一个 Same-Token
  same-token: please-change-this-value
  check-same-token: true
```

网关与子服务的 starter 也可以分开引入（Servlet 型服务用 `sa-token-spring-boot*-starter`，Reactor 型网关用 `sa-token-reactor-spring-boot*-starter`），微服务场景下务必分开引，**不要在父 POM 里统一引入**。

## 12. 单点登录与 OAuth2.0

| 能力 | 依赖 | 说明 |
|------|------|------|
| SSO | `sa-token-sso` | 三种模式：同域、跨域（共享 / 跨 Redis）、前后端分离；支持单点注销 |
| OAuth2.0 | `sa-token-oauth2` | 支持授权码、隐式、密码、客户端凭证四种模式，可扩展 openid |

```java
// SSO-Server 端：一个入口承接所有 SSO 请求
@RestController
public class SsoServerController {
    @RequestMapping("/sso/*")
    public Object ssoRequest() {
        return SaSsoHandle.serverRequest();
    }
}
```

协议细节见 [[oauth2|OAuth2.0]]；令牌格式对比见 [[jwt|JWT]]。

## 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 加了 `@SaCheckPermission` 但任何人都能访问 | `SaInterceptor` 未注册，或配置类未被 Spring 扫描 | 新增实现 `WebMvcConfigurer` 的配置类注册 `SaInterceptor`；确认配置类在启动类同包或子包下 |
| 登录成功，带 token 请求仍提示未登录 | 请求头字段名与 `sa-token.token-name` 不一致 | 对齐字段名；若经网关/[[nginx|Nginx]] 转发，检查请求头是否被丢弃 |
| 返回 `ERR syntax error` | v1.46.0 起的 Redis 插件使用 Redis 6.0+ 的 `SET KEEPTTL` | 升级 Redis 到 6.0+，或改用 JDK 序列化插件 |
| Spring Boot 3 项目启动报类找不到 | 用了 Boot 2 的 `sa-token-spring-boot-starter` | 换成 `sa-token-spring-boot3-starter`（Boot 4 用 `-4`） |
| `sa-token-dao-redis-jackson` 依赖拉不到 | 该坐标 1.34.0 后已改名 | 改用 `sa-token-redis-jackson` 或 `sa-token-redis-template` |
| 权限校验永远不通过 | `StpInterfaceImpl` 未加 `@Component`，或返回的权限码拼写不一致 | 确认实现类被扫描；打开 `sa-token.is-log: true` 观察实际校验的权限码 |
| 集成 Redis 后旧 token 全部失效 | 会话存储介质已切换 | 预期行为，用户重新登录即可 |
| 顶替登录把别的设备也踢了 | `replaced-range` 默认只顶替同端，若配置为 `ALL_DEVICE_TYPE` 则全端 | 改回 `CURR_DEVICE_TYPE` |

## See Also

- [[cloud-native/index|云原生目录]] —— 本文所属目录
- [[spring-boot3|Spring Boot 3]] —— 集成 Sa-Token 时的 Boot 版本基线
- [[spring-mvc|Spring MVC]] —— `SaInterceptor` 依托的拦截器机制
- [[spring-cloud|Spring Cloud]] —— 微服务网关鉴权场景
- [[redis|Redis]] —— 会话持久化介质
- [[jwt|JWT]] —— 令牌格式与无状态鉴权方案
- [[oauth2|OAuth2.0]] —— 授权协议基础
- [[http-protocol|HTTP 协议]] —— Cookie / Header 传递 token 的细节
- [[maven|Maven]] —— 依赖坐标与 BOM 管理

## 参考

- 官方文档：<https://sa-token.cc>
- 开源仓库：<https://github.com/dromara/sa-token>
- Maven 中央仓库：<https://central.sonatype.com/namespace/cn.dev33>
