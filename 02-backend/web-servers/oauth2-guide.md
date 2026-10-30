---
title: OAuth 2.0
date: 2024-01-01
tags:
  - OAuth
  - 认证
  - 安全
---
# OAuth 2.0

OAuth 是一个关于授权（authorization）的开放网络标准，在全世界得到广泛应用，目前的版本是 2.0 版。

## 应用场景

假设有一个"云冲印"网站，需要读取用户在 Google 上的照片。传统做法是用户把 Google 密码告诉云冲印，但这有以下缺点：

1. 云冲印会保存用户密码，不安全
2. Google 必须部署密码登录，不够安全
3. 用户无法限制授权范围和有效期
4. 用户只有修改密码才能收回授权
5. 一个第三方应用被破解会导致所有数据泄露

OAuth 就是为了解决这些问题而诞生的。

## 核心名词

| 名词 | 说明 |
|------|------|
| Third-party application | 第三方应用程序（客户端） |
| HTTP service | HTTP 服务提供商 |
| Resource Owner | 资源所有者（用户） |
| User Agent | 用户代理（浏览器） |
| Authorization server | 认证服务器 |
| Resource server | 资源服务器 |

## OAuth 的思路

OAuth 在"客户端"与"服务提供商"之间设置了一个**授权层**：

- 客户端不能直接登录服务提供商
- 客户端登录授权层所用的令牌（token）与用户密码不同
- 用户可以指定令牌的权限范围和有效期

## 运行流程

```
(A) 用户打开客户端，客户端要求用户给予授权
(B) 用户同意给予客户端授权
(C) 客户端使用授权，向认证服务器申请令牌
(D) 认证服务器确认无误，发放令牌
(E) 客户端使用令牌，向资源服务器申请资源
(F) 资源服务器确认令牌，开放资源
```

## 四种授权模式

OAuth 2.0 定义了四种授权方式：

### 1. 授权码模式（Authorization Code）

功能最完整、流程最严密的授权模式。通过客户端后台服务器与认证服务器互动。

**流程**：

```
(A) 用户访问客户端，客户端导向认证服务器
(B) 用户选择是否给予授权
(C) 用户授权后，认证服务器重定向到客户端，附带授权码
(D) 客户端用授权码向认证服务器申请令牌
(E) 认证服务器验证授权码，发放令牌
```

**请求示例**：

```
GET /authorize?response_type=code&client_id=s6BhdRkqt3&state=xyz
        &redirect_uri=https%3A%2F%2Fclient%2Eexample%2Ecom%2Fcb HTTP/1.1
Host: server.example.com
```

**令牌请求**：

```
POST /token HTTP/1.1
Host: server.example.com
Authorization: Basic czZCaGRSa3F0MzpnWDFmQmF0M2JW
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA
&redirect_uri=https%3A%2F%2Fclient%2Eexample%2Ecom%2Fcb
```

**令牌响应**：

```json
{
  "access_token":"2YotnFZFEjr1zCsicMWpAA",
  "token_type":"example",
  "expires_in":3600,
  "refresh_token":"tGzv3JOkF0XG5Qx2TlKWIA",
  "example_parameter":"example_value"
}
```

### 2. 简化模式（Implicit）

不通过第三方应用程序的服务器，直接在浏览器中向认证服务器申请令牌。

**适用场景**：纯前端应用，没有后端服务器

**流程**：

```
(A) 客户端将用户导向认证服务器
(B) 用户决定是否给客户端授权
(C) 认证服务器重定向，直接返回令牌（URL 参数）
(D) 浏览器向资源服务器请求资源
(E) 资源服务器返回资源
```

**请求示例**：

```
GET /authorize?response_type=token&client_id=s6BhdRkqt3&state=xyz
    &redirect_uri=https%3A%2F%2Fclient%2Eexample%2Ecom%2Fcb HTTP/1.1
Host: server.example.com
```

### 3. 密码模式（Resource Owner Password Credentials）

用户向客户端提供自己的用户名和密码，客户端使用这些信息向认证服务器申请令牌。

**适用场景**：高度信任的应用（如官方应用）

**流程**：

```
(A) 用户向客户端提供用户名和密码
(B) 客户端向认证服务器申请令牌
(C) 认证服务器确认后发放令牌
```

**请求示例**：

```
POST /token HTTP/1.1
Host: server.example.com
Authorization: Basic czZCaGRSa3F0MzpnWDFmQmF0M2JW
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=johndoe&password=A3ddj375
```

### 4. 客户端模式（Client Credentials）

客户端以自己的名义向认证服务器申请令牌，而不是以用户名义。

**适用场景**：客户端访问自己的资源，而非用户资源

**流程**：

```
(A) 客户端向认证服务器进行身份认证，申请令牌
(B) 认证服务器确认后发放令牌
```

**请求示例**：

```
POST /token HTTP/1.1
Host: server.example.com
Authorization: Basic czZCaGRSa3F0MzpnWDFmQmF0M2JW
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```

## 令牌使用

客户端拿到令牌后，向资源服务器请求资源：

```
GET /resource/1 HTTP/1.1
Host: server.example.com
Authorization: Bearer MFZiN2Q1YjM2OGYxZWM2OWM2
```

## 更新令牌

令牌有效期到期后，可以使用 refresh_token 获取新令牌：

```
POST /token HTTP/1.1
Host: server.example.com
Authorization: Basic czZCaGRSa3F0MzpnWDFmQmF0M2JW
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=tGzv3JOkF0XG5Qx2TlKWIA
```

## 四种模式对比

| 模式 | 适用场景 | 安全性 | 特点 |
|------|----------|--------|------|
| 授权码模式 | Web 应用 | 最高 | 最完整、最严密 |
| 简化模式 | 纯前端应用 | 较低 | 无后端服务器参与 |
| 密码模式 | 官方应用 | 中等 | 需要高度信任 |
| 客户端模式 | 服务间调用 | 中等 | 无用户参与 |

## 参考资源

- RFC 6749: The OAuth 2.0 Authorization Framework
- [理解 OAuth 2.0 - 阮一峰](https://www.ruanyifeng.com/blog/2014/05/oauth_2_0.html)