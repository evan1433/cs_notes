---
title: Spring Security 指南：概念、用法与常见案例
description: Spring Security 核心概念（认证/授权/过滤器链）、请求级与方法级授权写法、REST API/JWT/数据库用户/RBAC 常见案例与排错
tags:
  - spring
  - java
  - security
  - backend
  - authentication
date: 2026-11-11
---

# Spring Security 指南：概念、用法与常见案例

Spring Security 解决三件事：**你是谁（认证）、你能做什么（授权）、别被攻击（CSRF、会话固定、点击劫持等防护）**。它的配置方式在 6.0 / 7.0 两代里发生了彻底变化，网上大量旧文章仍在教 `WebSecurityConfigurerAdapter`——那套在 6.0 就已经删除了。本文只写现行写法。

> **版本说明**：截至 2026 年 11 月，Spring Security 最新 GA 为 **7.1.2**。版本配套关系：6.x ↔ Spring Boot 3.x，7.0.x ↔ Boot 4.0，7.1.x ↔ Boot 4.1，5.x ↔ Boot 2.x（已停止支持）。本文写法适用于 6.x 与 7.x，差异处单独标注。

## 1. 先分清两件事：认证与授权

| 维度 | 认证 Authentication | 授权 Authorization |
|------|---------------------|--------------------|
| 回答的问题 | 你是谁 | 你能做什么 |
| 发生时机 | 先 | 后（请求级授权在过滤器链**最后一环**） |
| 失败的语义 | 未登录 / 凭证无效 | 登录了但没权限 |
| 默认 HTTP 状态码 | `401 Unauthorized` | `403 Forbidden` |
| 代码载体 | `AuthenticationManager` | `authorizeHttpRequests`、`@PreAuthorize` |

排错时先判断是 401 还是 403：401 说明认证环节就失败了（用户没登录、token 过期、密码错误），403 说明认证成功但授权规则没通过（角色不对、路径规则写错）。

## 2. 核心概念与组件

| 组件                       | 职责                       | 常见实现 / 载体                                                |
| ------------------------ | ------------------------ | -------------------------------------------------------- |
| `SecurityFilterChain`    | 一组安全过滤器，整个框架的骨架          | `@Bean` + `HttpSecurity`                                 |
| `AuthenticationManager`  | 认证总入口                    | `ProviderManager`（组合多个 Provider）                         |
| `AuthenticationProvider` | 一种具体的认证方式                | `DaoAuthenticationProvider`（用户名密码）                       |
| `UserDetailsService`     | 按用户名查用户                  | `InMemoryUserDetailsManager` / 自定义查库实现                   |
| `UserDetails`            | 用户的密码、权限、启用/锁定标志         | `User.builder()`                                         |
| `PasswordEncoder`        | 密码单向哈希与比对                | `BCryptPasswordEncoder`、`DelegatingPasswordEncoder`      |
| `GrantedAuthority`       | 一个权限点（角色或细粒度权限）          | `"ROLE_ADMIN"`、`"order:read"`                            |
| `SecurityContextHolder`  | 当前请求的认证结果（`ThreadLocal`） | `SecurityContextHolder.getContext().getAuthentication()` |

### 2.1 一次表单登录在内部发生了什么

```text
POST /login  username/password
  → UsernamePasswordAuthenticationFilter 构造未认证的 UsernamePasswordAuthenticationToken
  → AuthenticationManager（实现是 ProviderManager）
  → DaoAuthenticationProvider
      ├─ UserDetailsService.loadUserByUsername()   按用户名查出 UserDetails
      └─ PasswordEncoder.matches()                 比对密码哈希
  → 认证成功的 Authentication（带 authorities）
  → 存入 SecurityContextHolder，写入 SecurityContextRepository（默认 session）
  → 后续请求由 SecurityContextHolderFilter 恢复登录态
```

### 2.2 过滤器链的位置与顺序

Spring Security 不是 Spring MVC 的拦截器，而是**标准的 Servlet Filter**，注册在所有业务代码之前：

```text
请求
 └ DelegatingFilterProxy          把 Servlet Filter 桥接进 Spring 容器
    └ FilterChainProxy            Spring Security 总入口，按规则挑一条链
       └ SecurityFilterChain      （securityMatcher("/api/**") 决定谁用这条链）
          ├ SecurityContextHolderFilter    恢复本次请求的 SecurityContext
          ├ CsrfFilter                     校验 CSRF token（写接口才拦）
          ├ UsernamePasswordAuthenticationFilter  表单登录
          ├ BearerTokenAuthenticationFilter       Bearer token（配置了资源服务器才有）
          ├ ExceptionTranslationFilter     把认证/授权异常翻译成 401/403
          └ AuthorizationFilter            最后才做请求级授权
```

两个值得记住的结论：

- **`AuthorizationFilter` 在最后**，所以业务代码执行前该完成的认证都已就绪；同时 MVC 视图 `FORWARD`、Boot 的 `/error` 会触发第二次授权，需要显式放行（见第 4 节）。
- 老架构里的 `FilterSecurityInterceptor` 已被 `AuthorizationFilter` + `AuthorizationManager` 取代，**不再查询匿名请求的 Authentication**（规则不需要就不查），性能更好。

## 3. 五分钟跑起来：Boot 的默认行为

加一个依赖，安全就全量生效：

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

启动后你什么都不用写，就已经获得了（Boot 自动配置的结果）：

| 默认行为 | 细节 |
|----------|------|
| 所有接口要求认证 | 包括 Boot 自己的 `/error` |
| 内置用户 `user` | 密码**随机生成并打印在控制台**：`Using generated security password: ...` |
| 密码存储 | BCrypt 哈希 |
| 表单登录 + HTTP Basic | 浏览器访问被 302 到 `/login`；curl 无凭证得到 401（内容协商） |
| CSRF 防护 | 写接口需要 token |
| 会话固定防护 | 登录成功后更换 `sessionId` |
| 安全响应头 | `X-Content-Type-Options`、`X-Frame-Options`、`Cache-Control`、`Strict-Transport-Security` |

### 3.1 覆盖默认用户

只要容器里出现 `UserDetailsService` 类型的 Bean，自动配置就退位：

```java
@Configuration
public class SecurityConfig {

    @Bean
    public UserDetailsService userDetailsService() {
        // {bcrypt} 前缀告诉 DelegatingPasswordEncoder 用哪个编码器比对
        UserDetails user = User.withUsername("alice")
                .password("{bcrypt}$2a$10$dXJ3SW6G7P50lGmMkkmwe.20cQQubK3.HZWzG3YB1tlRy.fqvM/BG")
                .roles("USER")
                .build();
        return new InMemoryUserDetailsManager(user);
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }
}
```

### 3.2 密码存储：为什么有个 `{bcrypt}` 前缀

存储格式是 `{id}encodedPassword`。`DelegatingPasswordEncoder` 拿 id 决定委托给哪个编码器：

| id | 算法 |
|----|------|
| `{bcrypt}` | BCrypt（默认编码算法，默认强度 10） |
| `{argon2}` | Argon2（7.0 另有基于 Password4j 的实现） |
| `{pbkdf2}` | PBKDF2 |
| `{scrypt}` | SCrypt |
| `{noop}` | 明文（**只用于测试**） |

这套设计的目的：**编码用最新算法、校验兼容历史格式**。库里 5 年前用 `{sha256}` 存的密码照样能登录，登录成功后可以顺手升级成 `{bcrypt}`。

```bash
# 生产环境预先生成哈希，别把明文写进代码
spring encodepassword myPassword
# {bcrypt}$2a$10$X5wFBtLrL/kHcmrOGGTrGufsBX8CJ0WpQpF3pgeuxBB/H73BK1DW6
```

> 演示用 `User.withDefaultPasswordEncoder()` 可以让框架帮你哈希，但明文仍留在源码里，官方明确标注不适用于生产。

## 4. 请求级授权：`authorizeHttpRequests`

现行写法没有基类、没有 `and()`，只有**一个返回 `SecurityFilterChain` 的 Bean**：

```java
import jakarta.servlet.DispatcherType;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;

@Configuration
@EnableWebSecurity
public class WebSecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authorize -> authorize
                // 放行内部转发与 /error，否则错误页会被再次拦截
                .dispatcherTypeMatchers(DispatcherType.FORWARD, DispatcherType.ERROR).permitAll()
                .requestMatchers("/public/**", "/login", "/about").permitAll()
                .requestMatchers(HttpMethod.DELETE, "/api/orders/**").hasRole("ADMIN")
                .requestMatchers("/api/orders/**").hasAnyRole("USER", "ADMIN")
                .anyRequest().denyAll()     // 兜底：白名单之外的全部拒绝
            )
            .formLogin(Customizer.withDefaults())
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}
```

### 4.1 顺序就是规则

`AuthorizationFilter` **按声明顺序逐条匹配，命中第一条即停止**。所以：

- 具体、严格的规则写在**前面**，宽泛规则写在后面；
- 结尾用 `anyRequest().denyAll()` 形成允许列表（allow list），新增接口默认被拒，比 `anyRequest().authenticated()` 更安全——后者忘改规则时会静默暴露。

### 4.2 内置规则速查

| 规则 | 说明 |
|------|------|
| `permitAll` / `denyAll` | 全放行 / 全拒绝（不触发认证查询） |
| `authenticated` / `anonymous` | 需要登录 / 只允许匿名 |
| `hasRole("ADMIN")` | 等价于 `hasAuthority("ROLE_ADMIN")`，**自动加 `ROLE_` 前缀** |
| `hasAnyRole(...)` / `hasAnyAuthority(...)` | 满足其一即可 |
| `hasAllAuthorities(...)` | 必须同时拥有全部（7.0 新增对应方法） |
| `access(new WebExpressionAuthorizationManager("hasRole('A') and hasRole('B')"))` | 复杂 SpEL 表达式 |

### 4.3 匹配手段与两个易混点

- 匹配默认走 `PathPattern` 风格（`/api/**`）；6.x 里 `requestMatchers` 在 MVC 环境用 `MvcRequestMatcher`、Servlet 环境用 `AntPathRequestMatcher`，**7.0 统一为 `PathPatternRequestMatcher`**。
- 只匹配**路径**，不匹配查询参数；要按参数放行得自己写 `RequestMatcher`。
- `securityMatcher("/api/**")` 限定了**整条链**的适用范围（可以据此配置多条链）；`requestMatchers` 只是链内的一条授权规则，两者不是一回事。

## 5. 方法级安全：`@EnableMethodSecurity`

**Boot 的 starter 默认不开方法级安全**，先加注解：

```java
@Configuration
@EnableMethodSecurity   // 取代废弃的 @EnableGlobalMethodSecurity(prePostEnabled = true)
public class MethodSecurityConfig { }
```

```java
@Service
public class OrderService {

    @PreAuthorize("hasRole('ADMIN')")
    public void auditAll() { }

    // 引用方法参数：#id；SpEL 里还能 @bean 引用任意 Spring Bean
    @PreAuthorize("#username == authentication.name or hasRole('ADMIN')")
    public Order findUserOrder(String username, Long id) { }

    // 返回后再校验，防“查别人数据”（IDOR）；returnObject 是返回值
    @PostAuthorize("returnObject.owner == authentication.name")
    public Order load(Long id) { }

    @PreAuthorize("hasRole('ADMIN')")
    @PostFilter("filterObject.status == 'ACTIVE'")   // 过滤返回集合
    public List<Order> listAll() { }
}
```

| 注解 | 作用 | 专属变量 |
|------|------|----------|
| `@PreAuthorize` | 调用前授权 | `#参数名`、`authentication` |
| `@PostAuthorize` | 返回后校验 | `returnObject` |
| `@PreFilter` | 过滤入参集合 | `filterObject` |
| `@PostFilter` | 过滤返回集合 | `filterObject` |

三个必须知道的坑：

1. **实现机制是 Spring AOP 代理**——同类自调用 `this.method()` 会绕过注解，机制与排查见 [[spring-aop|Spring AOP 写法手册]]；需要彻底免疫自调用可切到 `@EnableMethodSecurity(mode = AdviceMode.ASPECTJ)` 字节码织入。
2. `@PostAuthorize` 校验发生在方法返回之后，**不要**与写操作放同一方法（校验失败时写已经发生）。
3. 授权失败抛 `AccessDeniedException`：在 HTTP 上下文里由 `ExceptionTranslationFilter` 转成 403；在定时任务、MQ 消费者里没人翻译，需要自己 catch。

## 6. 常见案例

### 案例 1：前后端分离 REST API（无状态、JSON 错误、CORS）

不用 Cookie 就没有 CSRF 的攻击面，可以显式关闭；同时把 401/403 从默认的空响应/重定向改成 JSON：

```java
@Configuration
@EnableWebSecurity
public class ApiSecurityConfig {

    @Bean
    public SecurityFilterChain apiChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/api/**")
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/login").permitAll()
                .anyRequest().authenticated())
            .csrf(csrf -> csrf.disable())          // 前提：认证凭证不落在 Cookie 里
            .sessionManagement(sm ->
                sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(eh -> eh
                .authenticationEntryPoint((req, res, ex) -> writeJson(res, 401, "未认证"))
                .accessDeniedHandler((req, res, ex) -> writeJson(res, 403, "无权限")))
            .cors(Customizer.withDefaults());      // 与下面的 CorsConfigurationSource Bean 联动
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration cfg = new CorsConfiguration();
        cfg.setAllowedOrigins(List.of("https://app.example.com"));   // 别用 "*" 配合凭证
        cfg.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
        cfg.setAllowedHeaders(List.of("Authorization", "Content-Type"));

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", cfg);
        return source;
    }

    private static void writeJson(HttpServletResponse res, int status, String msg) throws IOException {
        res.setStatus(status);
        res.setContentType("application/json;charset=UTF-8");
        res.getWriter().write("{\"code\":" + status + ",\"message\":\"" + msg + "\"}");
    }
}
```

> 关闭 CSRF 的前提要反复确认：认证信息不走 Cookie（token 放 `Authorization` 头）。只要登录态还依赖 Cookie，CSRF 防护就必须保留；SPA 场景 7.0 提供了 `http.csrf(csrf -> csrf.spa())` 的专用配置。

### 案例 2：JWT 资源服务器（对接外部认证中心，官方推荐路径）

应用只做资源服务器，登录和签发 token 交给认证中心（Keycloak、Authing、企业自建 IdP 等）：

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
</dependency>
```

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://sso.example.com   # 首个请求时才去发现端点拿公钥，启动不强依赖
```

```java
@Bean
SecurityFilterChain jwtChain(HttpSecurity http) throws Exception {
    http
        .securityMatcher("/api/**")
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/api/public/**").permitAll()
            .anyRequest().authenticated())
        .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .csrf(csrf -> csrf.disable())
        .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()));
    return http.build();
}
```

**验证逻辑**（不用自己写）：签名（从 `jwk-set-uri` 拉公钥，密钥轮换自动生效）、`exp`/`nbf`（默认容忍 60 秒时钟偏差）、`iss`（与 issuer-uri 比对）。默认只信任 RS256。

**权限映射**默认把 `scope`/`scp` claim 加 `SCOPE_` 前缀变成 authority。国内常见把角色放 `roles` claim，自定义转换器：

```java
@Bean
public JwtAuthenticationConverter jwtAuthenticationConverter() {
    JwtGrantedAuthoritiesConverter authorities = new JwtGrantedAuthoritiesConverter();
    authorities.setAuthoritiesClaimName("roles");   // 默认是 scope/scp
    authorities.setAuthorityPrefix("ROLE_");        // 默认是 SCOPE_；写 "" 则不加前缀

    JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
    converter.setJwtGrantedAuthoritiesConverter(authorities);
    return converter;
}
```

```java
// 接线
.oauth2ResourceServer(o -> o.jwt(j -> j.jwtAuthenticationConverter(jwtAuthenticationConverter())))
```

Token 本身的概念（结构、签名算法、安全实践）见 [[jwt|JWT 入门与使用]]，[[oauth2|OAuth2]] 讲协议流程。

### 案例 3：自己发 JWT 的登录端点

认证交给框架、签发自己做的轻量方案（单体服务没有独立认证中心时很常见）：

```java
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final TokenService tokenService;   // 自己封装的签发/续期逻辑

    public AuthController(AuthenticationManager authenticationManager,
                          TokenService tokenService) {
        this.authenticationManager = authenticationManager;
        this.tokenService = tokenService;
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody LoginRequest req) {
        // 失败抛 AuthenticationException（BadCredentialsException 等），交给全局异常处理器转 401
        Authentication auth = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(req.username(), req.password()));

        List<String> roles = auth.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .toList();
        return new LoginResponse(tokenService.issue(auth.getName(), roles), roles);
    }
}

// 认证管理器要自己暴露成 Bean，AuthController 才能注入
@Bean
AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
    return configuration.getAuthenticationManager();
}
```

后续请求的校验有两条路：

- **对称密钥/单密钥**：自己实现 `OncePerRequestFilter`，验签后构造 `Authentication` 放进 `SecurityContextHolder`（签发与解析的 Java 实现见 [[jwt|JWT 入门与使用]]）；
- **想复用官方过滤器**：发布 `JwtDecoder` Bean 交给 `oauth2ResourceServer`（Nimbus 实现支持 `withSecretKey` / `withJwkSetUri`）。

> 需要完整的认证中心（授权码模式、PKCE、客户端管理）时，别手搓——**Spring Authorization Server 已在 7.0 并入 Spring Security**，直接用它。顺带一提：OAuth 2.0 的 password grant 在 7.0 已被移除，老方案迁移只能走授权码 + PKCE。

### 案例 4：用户存数据库

自定义 `UserDetailsService` 查库，密码列存 `{bcrypt}...` 格式的哈希：

```java
@Service
public class DbUserDetailsService implements UserDetailsService {

    private final UserMapper userMapper;

    public DbUserDetailsService(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    @Override
    public UserDetails loadUserByUsername(String username) {
        var u = userMapper.findByUsername(username)
                .orElseThrow(() -> new UsernameNotFoundException("用户不存在: " + username));
        return User.withUsername(u.username())
                .password(u.passwordHash())                 // 库里存 {bcrypt}...
                .disabled(!u.enabled())
                .authorities(u.roles().stream()
                        .map(r -> "ROLE_" + r)              // hasRole 要求的前缀，只加一次
                        .toArray(String[]::new))
                .build();
    }
}
```

```java
// 注册 / 改密时入库的一律是哈希，永远不存明文
String hash = passwordEncoder.encode(rawPassword);
userMapper.updatePassword(userId, hash);
```

内置的 `JdbcUserDetailsManager` 提供了默认表结构（`users` / `authorities`）的现成实现，表结构不合口味就按上面自写。

### 案例 5：方法级 RBAC，用元注解收敛规则

把散落各处的 `@PreAuthorize("hasRole('ADMIN')")` 收敛成一个自定义注解，改角色名只动一处：

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@PreAuthorize("hasRole('ADMIN')")
public @interface IsAdmin { }
```

```java
@Service
public class RiskyService {

    @IsAdmin
    public void purgeExpiredData() { }

    // 复杂判断抽到 Bean 里，可单测
    @PreAuthorize("@orderAuthz.canModify(#orderId, authentication)")
    public void modify(Long orderId) { }
}

@Component("orderAuthz")
public class OrderAuthorizationLogic {
    public boolean canModify(Long orderId, Authentication auth) {
        // 集中的、可单元测试的授权判断
        return auth.getAuthorities().contains(new SimpleGrantedAuthority("ROLE_ADMIN"))
                || orderMapper.isOwner(orderId, auth.getName());
    }
}
```

复杂业务授权**别写在 SpEL 字符串里**——委托给 Bean 是官方推荐做法，逻辑可测试、可复用。

## 7. 迁移对照表（老文章 → 现行写法）

| 旧写法 | 命运 | 现行写法 |
|--------|------|----------|
| `extends WebSecurityConfigurerAdapter` 重写 `configure()` | **6.0 已删除** | `@Bean SecurityFilterChain` |
| `antMatchers()` / `mvcMatchers()` | **6.0 已删除** | `requestMatchers()` |
| `authorizeRequests()` + `.and()` 链式拼接 | **7.0 已删除** | `authorizeHttpRequests(auth -> ...)` lambda |
| `@EnableGlobalMethodSecurity(prePostEnabled = true)` | 废弃 | `@EnableMethodSecurity`（默认开 pre/post） |
| `User.withDefaultPasswordEncoder()` | 仅演示 | 预先 `encode` 入库 / `spring encodepassword` |
| OAuth 2.0 password grant | **7.0 已删除** | 授权码模式 + PKCE |
| 自建授权服务器 | — | Spring Authorization Server（7.0 起并入） |
| CSRF 一刀切 disable | — | 无 Cookie 才允许关；SPA 用 `csrf.spa()`（7.0） |

6.x 的教程里 `requestMatchers` 之外仍能看到 `and()` 拼接的写法，那在 6.x 可用（已标废弃）、**升 Boot 4 会直接编译失败**。

## 8. 常见排错

| 现象 | 原因 | 解决 |
|------|------|------|
| 加了依赖，全站 401/302 | 这是**预期行为**：默认保护一切 | 配 `permitAll` 白名单，或去掉依赖 |
| 浏览器被 302 到登录页，curl 得到 401 | 内容协商：给页面跳登录、给接口 401 | REST 场景自定义 `authenticationEntryPoint` 返回 JSON |
| `hasRole("ADMIN")` 永远不通过 | 权限串前缀问题：库里存了 `ROLE_ADMIN` 又被自动加前缀成 `ROLE_ROLE_ADMIN`，或压根没前缀 | `hasRole` 会自动加 `ROLE_`，数据侧只存一份 |
| 启动/登录报 `There is no PasswordEncoder mapped for the id "null"` | 密码串缺少 `{bcrypt}` 等 id 前缀 | 用 `PasswordEncoderFactories.createDelegatingPasswordEncoder()`，入库带前缀 |
| GET 正常，POST/PUT 一律 403 | CSRF 防护拦了写接口 | 凭证不走 Cookie 时 `csrf.disable()`；否则带上 XSRF token |
| 出错时 `/error` 也返回 401 | ERROR 分发被再次授权 | `dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()` |
| `@PreAuthorize` 不生效 | 忘了 `@EnableMethodSecurity`（starter 不默认开）；或同类自调用绕过代理 | 加注解；自调用解法见 [[spring-aop\|Spring AOP 写法手册]] |
| CORS 预检 OPTIONS 403/401 | 预检请求不带凭证，先撞上认证/CSRF | `http.cors(withDefaults())` + `CorsConfigurationSource` Bean（或放行 OPTIONS） |
| 同一密码每次 `encode` 结果都不同 | BCrypt 自带随机盐，**属正常** | 比对只能用 `matches()`，不能比字符串 |
| 每次登录 `JSESSIONID` 都变 | 会话固定防护默认开启 | 预期行为，不是 bug |
| token 明明没过期却 `JwtValidationException` | 校验含 `iss` 比对与 60 秒时钟偏差 | 核对 issuer-uri；集群间校时（NTP） |
| 升级 Boot 4 后 `authorizeRequests` 编译报错 | 7.0 已删除该 API 及 `and()` | 改 `authorizeHttpRequests` lambda 写法 |
| 定时任务里授权异常没变成 403 | `ExceptionTranslationFilter` 只在 HTTP 链上 | 非 Web 入口自己 catch `AccessDeniedException` |

## See Also

- [[spring-aop|Spring AOP 写法手册]] —— 方法级安全的代理实现与自调用失效
- [[jwt|JWT 入门与使用]] —— token 结构、签发与验签的 Java 实现
- [[oauth2|OAuth2]] —— 授权码模式、PKCE 等协议流程
- [[sa-token|Sa-Token]] —— 轻量级国产替代方案，写法对比
- [[spring-boot3|Spring Boot 3 使用指南]] / [[spring-boot4|Spring Boot 4 使用指南与发展现状]]
- [[spring5|Spring 5 核心]] —— 容器与 Bean 机制
- [[ssm-auth-project|SSM 认证项目实战]]

## 参考

- [Hello Spring Security（默认行为）](https://docs.spring.io/spring-security/reference/servlet/getting-started.html)
- [Authorize HttpServletRequests](https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html)
- [Method Security](https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html)
- [Password Storage（DelegatingPasswordEncoder）](https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html)
- [OAuth 2.0 Resource Server JWT](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html)
- [What's New in Spring Security 7.0（移除清单）](https://www.springframework.org/spring-security/reference/7.0/whats-new.html)
