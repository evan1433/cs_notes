---
title: JWT 入门与使用
description: 介绍 JSON Web Token 的概念、结构、认证流程、Java 示例与安全实践。
tags:
  - backend
  - security
  - jwt
  - authentication
date: 2026-06-18
---
# JWT 入门与使用

## 概览

JWT（JSON Web Token）是一种用于在双方之间安全传递声明信息的令牌格式。它常用于登录态保持、接口认证、
单点登录和微服务之间的身份传递。

JWT 本身不是“登录协议”，而是一种**令牌载体**。在实际系统中，它通常和 Session、[[oauth2|OAuth2]]、
网关、Spring Security 等机制配合使用。

## JWT 解决什么问题

传统 Session 登录通常会把用户登录状态保存在服务端：

1. 用户登录成功后，服务端生成 `sessionId`。
2. 浏览器通过 Cookie 携带 `sessionId`。
3. 服务端根据 `sessionId` 查询用户状态。

JWT 的思路不同：服务端登录成功后，把用户身份、过期时间等信息写入 Token，并用密钥签名。客户端后续请求
直接携带 Token，服务端通过验签和解析 Token 判断请求是否合法。

JWT 适合这些场景：

- 前后端分离应用的接口认证。
- 移动端、桌面端等不方便依赖 Cookie Session 的客户端。
- 微服务网关统一认证后，向下游服务传递用户身份。
- OAuth2 / OpenID Connect 中作为 Access Token 或 ID Token 的格式。

JWT 不适合这些场景：

- 需要服务端随时强制踢下线，但没有黑名单或令牌版本机制。
- 令牌中需要放大量动态权限或敏感信息。
- 系统更依赖服务端集中控制会话状态，且水平扩展压力不大。

## 令牌结构

一个 JWT 由三部分组成，中间用点号连接：

```text
header.payload.signature
```

例如：

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDAxIiwiZXhwIjoxNzEwMDAwMDAwfQ.signature
```

### Header

Header 描述令牌类型和签名算法：

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

常见算法：

- `HS256`：HMAC + SHA-256，对称密钥签名，签发方和校验方使用同一个密钥。
- `RS256`：RSA + SHA-256，私钥签名，公钥校验，适合认证中心签发、多个服务校验。
- `ES256`：ECDSA + SHA-256，签名更短，但工程兼容性需要确认。

### Payload

Payload 保存声明（Claims）。声明是关于用户、客户端、过期时间等信息的 JSON 字段。

```json
{
  "sub": "1001",
  "name": "张三",
  "role": "admin",
  "iat": 1710000000,
  "exp": 1710003600
}
```

常见标准声明：

- `iss`：Issuer，签发者。
- `sub`：Subject，主体，通常是用户 ID。
- `aud`：Audience，接收方，表示这个 Token 给谁用。
- `exp`：Expiration Time，过期时间。
- `nbf`：Not Before，在此时间之前不可用。
- `iat`：Issued At，签发时间。
- `jti`：JWT ID，令牌唯一 ID，可用于黑名单或防重放。

Payload 只做 Base64URL 编码，**不是加密**。任何拿到 Token 的人都可以解析 Payload，所以不要把密码、手机号、
身份证号、银行卡号等敏感信息放进去。

### Signature

Signature 用来证明 Token 没有被篡改。以 `HS256` 为例，签名逻辑可以理解为：

```text
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

如果攻击者修改了 Payload 中的 `role`，但不知道服务端密钥，就无法生成合法签名。服务端验签会失败。

## 登录认证流程

典型 JWT 登录流程如下：

1. 用户提交用户名和密码到登录接口。
2. 服务端校验账号密码。
3. 校验成功后，服务端签发 Access Token，必要时同时签发 Refresh Token。
4. 客户端保存 Token，并在后续请求中携带：

   ```http
   Authorization: Bearer <access_token>
   ```

5. 服务端拦截请求，提取 Token。
6. 服务端校验签名、过期时间、签发者、接收方等字段。
7. 校验成功后，把用户身份放入当前请求上下文，继续执行业务逻辑。

## Access Token 与 Refresh Token

在真实系统中，通常不要只发一个长期有效的 JWT，而是拆成两个 Token：

- **Access Token**：访问业务接口，生命周期短，例如 15 分钟到 2 小时。
- **Refresh Token**：用于换取新的 Access Token，生命周期长，例如 7 天到 30 天。

这样做的好处是：Access Token 泄露后的风险窗口较短；用户长期在线则依赖 Refresh Token 刷新登录态。

刷新流程：

1. Access Token 过期。
2. 客户端用 Refresh Token 请求刷新接口。
3. 服务端校验 Refresh Token 是否有效、是否被撤销、是否和设备匹配。
4. 校验通过后签发新的 Access Token，必要时轮换 Refresh Token。

## Java 17 最小示例

下面示例演示如何用 Java 标准库生成和校验一个 `HS256` JWT。它适合学习 JWT 的底层结构，生产环境建议使用
成熟库，例如 `jjwt`、`java-jwt`，或者直接使用 Spring Security OAuth2 Resource Server。

保存为 `JwtDemo.java` 后运行：

```bash
javac JwtDemo.java
java JwtDemo
```

```java
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;

public class JwtDemo {
    private static final String SECRET = "change-me-to-a-long-random-secret-at-least-32-bytes";

    public static void main(String[] args) throws Exception {
        long now = Instant.now().getEpochSecond();
        String token = createToken("1001", now, now + 3600);

        System.out.println("JWT: " + token);
        System.out.println("valid: " + verifyToken(token));
    }

    private static String createToken(String userId, long issuedAt, long expiresAt) throws Exception {
        String header = """
                {"alg":"HS256","typ":"JWT"}""";
        String payload = """
                {"sub":"%s","iat":%d,"exp":%d}""".formatted(userId, issuedAt, expiresAt);

        String encodedHeader = base64Url(header.getBytes(StandardCharsets.UTF_8));
        String encodedPayload = base64Url(payload.getBytes(StandardCharsets.UTF_8));
        String signingInput = encodedHeader + "." + encodedPayload;
        String signature = hmacSha256(signingInput, SECRET);

        return signingInput + "." + signature;
    }

    private static boolean verifyToken(String token) throws Exception {
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            return false;
        }

        String signingInput = parts[0] + "." + parts[1];
        String expectedSignature = hmacSha256(signingInput, SECRET);

        return constantTimeEquals(expectedSignature, parts[2]);
    }

    private static String hmacSha256(String data, String secret) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        SecretKeySpec key = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        mac.init(key);
        return base64Url(mac.doFinal(data.getBytes(StandardCharsets.UTF_8)));
    }

    private static String base64Url(byte[] bytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private static boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) {
            return false;
        }

        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }
}
```

这个示例只校验了签名，没有完整校验 `exp`、`iss`、`aud` 等声明。真实项目中必须同时校验这些字段。

## Spring Boot 中的常见用法

在 Spring Boot 项目里，JWT 常见落点是过滤器或 Spring Security 的资源服务器配置：

```java
@Bean
SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    return http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                    .requestMatchers("/api/auth/login").permitAll()
                    .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .build();
}
```

这个配置表示：

- 登录接口允许匿名访问。
- 其他接口都需要认证。
- 请求中的 `Authorization: Bearer <token>` 会按 JWT 方式解析和校验。

如果是单体应用，也可以自定义 `OncePerRequestFilter`：

1. 从请求头读取 `Authorization`。
2. 判断是否以 `Bearer` 前缀开头。
3. 解析并校验 JWT。
4. 构造认证对象，写入 `SecurityContextHolder`。
5. 继续执行过滤器链。

自定义过滤器适合学习和简单项目；生产环境更推荐使用 Spring Security 已有能力，减少安全细节遗漏。

## 存储与传输

JWT 传输时最常见的方式是 HTTP Header：

```http
Authorization: Bearer <access_token>
```

客户端存储方式需要根据应用类型选择：

- Web 前端：可以放在内存中，刷新页面后通过 Refresh Token 或重新登录恢复。
- Cookie：建议使用 `HttpOnly`、`Secure`、`SameSite`，并配合 CSRF 防护策略。
- LocalStorage：实现简单，但一旦发生 XSS，Token 容易被读取，敏感系统应谨慎使用。
- 移动端：使用系统提供的安全存储，例如 Keychain、Keystore。

无论哪种方式，都应该全站使用 HTTPS，避免 Token 在传输过程中泄露。

## 安全实践

- 使用足够强的密钥，`HS256` 密钥至少 256 bit，并通过配置中心或密钥管理系统保存。
- Access Token 设置较短过期时间，不发长期有效的访问令牌。
- 校验 `exp`、`nbf`、`iss`、`aud`，不要只验签名。
- 不信任客户端传来的角色和权限，关键权限最好从服务端数据库或缓存重新加载。
- 不在 Payload 中存放敏感信息，因为 JWT 默认不加密。
- 支持令牌撤销机制，例如 Refresh Token 表、黑名单、用户 tokenVersion。
- 防止算法混淆攻击，不接受请求方随意指定算法，只允许服务端配置的算法。
- 对刷新接口做风控，例如设备绑定、IP 异常检测、刷新令牌轮换。
- 服务端记录关键认证日志，便于排查异常登录和 Token 滥用。

## 常见误区

### JWT 不是加密

JWT 默认只是签名，不是加密。Payload 可以被任何人解码查看。签名保证的是“没有被篡改”，不是“别人看不见”。

### JWT 不是天然无状态万能方案

JWT 可以减少服务端 Session 查询，但只要系统需要强制退出、修改权限立即生效、检测设备登录状态，就仍然需要服务端状态。

### 令牌越大越不好

JWT 会随着每次请求发送。Payload 放太多字段会增加网络开销，也会让身份信息扩散到更多日志、代理和中间件中。

## 与 Session 的对比

| 维度 | Session | JWT |
| --- | --- | --- |
| 状态保存 | 服务端保存登录态 | Token 自带声明，服务端可少保存状态 |
| 扩展性 | 需要共享 Session 或集中存储 | 多服务只要能验签即可识别身份 |
| 撤销能力 | 服务端删除 Session 即可 | 需要黑名单、版本号或短过期策略 |
| Token 大小 | 通常只有 sessionId | 通常比 sessionId 大 |
| 安全重点 | Session 存储、Cookie 安全 | 密钥管理、过期时间、撤销机制 |

实践中不必把 Session 和 JWT 对立起来。很多系统会使用短期 JWT 做接口访问，同时使用服务端状态管理 Refresh Token。

## 参考资料

- [RFC 7519: JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519)
- [JWT 官方介绍](https://jwt.io/introduction)
- [Spring Security OAuth2 Resource Server JWT](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html)
