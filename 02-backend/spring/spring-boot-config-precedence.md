---
title: Spring Boot 配置优先级
description: 命令行参数、JVM 系统属性、环境变量与配置文件的覆盖顺序，含配置文件加载位置、宽松绑定规则与高频踩坑
tags:
  - spring-boot
  - java
  - backend
  - configuration
date: 2026-11-04
aliases:
  - spring-boot-config-precedence
---

# Spring Boot 配置优先级

> 适用于 Spring Boot 2.4+（含 3.x / 4.x）。2.4 之前的 bootstrap 与 `spring.profiles` 加载机制有差异，文末单列。底层 `-D` 写法见 [[jvm-options|JVM 启动参数速查]]。

## 一句话结论

优先级从高到低：

```text
命令行参数  --key=value
    >  SPRING_APPLICATION_JSON  ▶ 内联 JSON
    >  JVM 系统属性  -Dkey=value
    >  操作系统环境变量  KEY=value
    >  配置文件  application.properties / yaml ← 外部 > jar 内，profile > 非 profile
    >  @PropertySource 注解
    >  SpringApplication.setDefaultProperties 默认值
```

记两条就够用：**越靠近"进程启动现场"的越赢**（命令行 > 环境变量 > 文件），**文件里"越晚被加载的"越赢**（外部 > jar 内，profile 文件 > 默认文件）。

## 同一个配置的五种写法

| 方式 | 写法示例 | 谁最常用它 | 说明 |
|------|----------|------------|------|
| 命令行参数 | `--server.port=8081` | 临时排障、脚本 | 必须 `--` 开头且带 `=` |
| JVM 系统属性 | `-Dserver.port=8081` | 运维改启动脚本 | 必须写在 `-jar` **之前** |
| 环境变量 | `SERVER_PORT=8081` | Docker / K8s | 点变下划线、连字符去掉、全大写 |
| 内联 JSON | `SPRING_APPLICATION_JSON='{"server.port":8081}'` | 平台批量注入 | 整段 JSON 作为一个变量值 |
| 配置文件 | `server.port: 8081` | 开发与默认值 | 见下节加载位置 |

```bash
# 三种方式叠在同一行时的胜负关系：命令行最后出现，优先级最高
java -Dserver.port=8081 \
     -jar order-service.jar \
     --server.port=9090
# 最终端口 9090
```

## 完整优先级表（官方 15 层，高 → 低）

| 优先级 | 属性源 | 典型场景 | 能不能压过它 |
|--------|--------|----------|--------------|
| 1（最高） | Devtools 全局设置 `$HOME/.config/spring-boot/` | 开发者本机个性化 | 仅 devtools 启用时存在 |
| 2 | `@TestPropertySource` | 测试类 | — |
| 3 | `@DynamicPropertySource` | 测试类动态注入 | — |
| 4 | `@SpringBootTest(properties = ...)` 等测试注解 | 测试类 | — |
| 5 | **命令行参数** `--key=value` | 启动脚本、排障 | 无 |
| 6 | `SPRING_APPLICATION_JSON` | 平台侧统一注入 | 只有命令行能压 |
| 7 | `ServletConfig` init 参数 | 传统 WAR 部署 | 上面几条 |
| 8 | `ServletContext` init 参数 | 传统 WAR 部署 | 上面几条 |
| 9 | JNDI `java:comp/env` | 应用服务器 | 上面几条 |
| 10 | **JVM 系统属性** `-Dkey=value` | 启动脚本 | 上面几条 |
| 11 | **操作系统环境变量** | Docker / K8s / systemd | 上面几条；**`-D` 能压它** |
| 12 | `RandomValuePropertySource`（仅 `random.*`） | 随机端口/密钥 | 上面几条 |
| 13 | **配置文件（Config Data）** | `application.yml` | 上面所有 |
| 14 | `@PropertySource` 注解 | 老项目零散配置 | 配置文件也能压它 |
| 15（最低） | `setDefaultProperties()` 默认值 | 兜底值 | 全部 |

**三个容易被忽略的点：**

1. **`-D` 压得过环境变量**。很多人以为容器里 `SERVER_PORT` 一定生效，其实启动脚本里的 `-Dserver.port` 会赢——排查"改了环境变量没反应"时先看这里。
2. **`@PropertySource` 比配置文件还低**。它加载晚于 Config Data，想覆盖它很容易，别把它当高优先级来源。
3. **`@PropertySource` 读不到早期属性**。`logging.*`、`spring.main.*`、`spring.profiles.*` 在上下文 refresh 前就已读取，写在该注解里无效。

## 配置文件加载位置与顺序

同一份 `application.{properties|yml}` 可能出现在五个位置，靠后的覆盖靠前的：

| 顺序 | 位置 | 说明 |
|------|------|------|
| 1（最低） | `classpath:/` | jar 内根目录，打包进镜像的默认值 |
| 2 | `classpath:/config/` | jar 内 config 包 |
| 3 | `file:./` | jar 同级目录，运维现场改这里 |
| 4 | `file:./config/` | 同级 config 目录，**最常用的外部化位置** |
| 5（最高） | `file:./config/*/` | config 下的一级子目录，多环境并存时用 |

**profile 文件的规则：**

- `application-prod.yml` 覆盖同位置的 `application.yml`
- 多个 profile 同时激活时 **last wins**：`--spring.profiles.active=prod,live` → `application-live.yml` 赢
- 未激活任何 profile 时，默认 profile 为 `default`，会读 `application-default.yml`

> **边界情况别赌**：jar 内的 `application-prod.yml` 与 jar 外的 `application.yml` 谁赢，官方文档两处描述存在张力（位置顺序 vs "profile 文件恒优先"）。生产上不要依赖这种交叉场景，用 `spring.config.location` 显式指定，或在外部文件里也提供 profile 版本。

### 调整加载位置的两个开关

```bash
# 替换默认位置：只读这里，忽略其他默认位置
java -jar app.jar --spring.config.location=optional:file:/etc/app/

# 追加位置：默认位置照旧加载，额外位置优先级更高
java -jar app.jar --spring.config.additional-location=optional:file:/etc/app/
```

> **必须用环境属性声明**：`spring.config.name` / `spring.config.location` / `spring.config.additional-location` 在配置文件被解析**之前**就要确定，所以写进 `application.yml` 里是无效的，只能用命令行、`-D` 或环境变量。

### 常见目录结构

```text
/etc/app/                      # 外部配置目录（优先级高于 jar 内）
├── application.yml            # 公共配置
├── application-prod.yml       # 生产覆盖
└── logback-spring.xml         # 日志配置（用 -Dlogging.config 指过来）
/opt/app/
├── order-service.jar
└── config/                    # 若用默认位置，这里会被自动加载
    └── application.yml
```

```bash
java -Dlogging.config=/etc/app/logback-spring.xml \
     -jar /opt/app/order-service.jar \
     --spring.profiles.active=prod \
     --spring.config.additional-location=optional:file:/etc/app/
```

## 宽松绑定：同一个 key 的合法写法

`my.app.item-price` 这一个配置，以下写法都等价：

| 写法 | 用在哪 | 备注 |
|------|--------|------|
| `my.app.item-price` | `.properties` / YAML | **推荐**，canonical form |
| `my.app.itemPrice` | YAML / `-D` | 驼峰，绑定同样生效 |
| `my.app.item_price` | YAML | 下划线写法 |
| `MY_APP_ITEMPRICE` | 环境变量 | 点→下划线、去掉连字符、全大写 |

**转换规则（手工推导环境变量名时用）：**

1. `.` → `_`
2. 删除所有 `-`
3. 全部大写

所以 `spring.main.log-startup-info` → `SPRING_MAIN_LOGSTARTUPINFO`（注意不是 `SPRING_MAIN_LOG_STARTUP_INFO`）。

```yaml
# 列表与 Map 的绑定写法
my:
  servers:
    - 10.0.0.1        # 索引形式：MY_SERVERS_0=10.0.0.1
    - 10.0.0.2
  labels:
    env: prod         # Map：MY_LABELS_ENV=prod，key 会被转小写
```

> `@ConfigurationProperties(prefix = ...)` 的 prefix **必须**是 kebab-case 全小写，写成驼峰会启动失败。

## 验证生效顺序

```bash
# 1. Actuator：按优先级从高到低列出所有 propertySources，直接看谁赢
curl -s localhost:8081/actuator/env | jq '.propertySources[].name'
# 输出示例（越靠前优先级越高）：
# "commandLineArgs"
# "systemProperties"
# "systemEnvironment"
# "Config resource 'file [/etc/app/application-prod.yml]' via location 'optional:file:/etc/app/'"
# "Config resource 'class path resource [application.yml]'"

# 2. 查单个属性最终值及来源
curl -s localhost:8081/actuator/env/server.port | jq '{value: .property.value, source: .property.source}'
```

```java
// 3. 代码里断言来源，适合写集成测试
@SpringBootTest
class ConfigSourceTest {
    @Autowired
    private Environment env;

    @Test
    void serverPortShouldComeFromCommandLine() {
        // 测试中用 properties 属性注入，可验证优先级是否如预期
        assertThat(env.getProperty("server.port")).isEqualTo("9090");
    }
}
```

> Actuator 的 `env` 端点会暴露配置值，生产环境要么不暴露（`management.endpoints.web.exposure.include` 里去掉），要么加认证。

## 高频踩坑对照表

| 现象 | 根因 | 正确做法 |
|------|------|----------|
| `mvn spring-boot:run -Dspring.profiles.active=prod` 没生效 | 这个 `-D` 被 Maven 吃了，没进应用 JVM | 用 `-Dspring-boot.run.jvmArguments="-Dspring.profiles.active=prod"` 或 `-Dspring-boot.run.profiles=prod` |
| IDEA 里改了配置不生效 | 分不清 VM options 与 Program arguments | VM options 填 `-Dkey=value`；Program arguments 填 `--key=value` |
| `java -jar app.jar -Dkey=value` 无效 | `-D` 写在 jar 之后，成了应用入参 | `-D` 放到 `-jar` 之前 |
| `--server.port 8081`（空格分隔）绑不上 | Boot 只认 `--key=value`，无等号时值为空串 | 必须写 `=` |
| 环境变量 `spring.profiles.active=prod` 不生效 | 环境变量名不能带点 | 写 `SPRING_PROFILES_ACTIVE=prod` |
| `SPRING_MAIN_LOG_STARTUP_INFO` 不生效 | 多加了连字符对应的下划线 | 应为 `SPRING_MAIN_LOGSTARTUPINFO` |
| 配置文件里写 `spring.config.location` 无效 | 该属性在配置加载前就要读 | 用 `-D` / 命令行 / 环境变量 |
| 同名 `.properties` 与 `.yml` 并存，改了 yml 没反应 | 同位置下 `.properties` 优先 | 删掉其中一个，别混用格式 |
| K8s 里改了 env，Pod 里还是旧值 | 旧 Pod 未重建，或 `-D` 在脚本里压过了它 | `kubectl exec` 进容器看 `/proc/1/environ` 与 `ps -ef` |
| Spring Cloud Config 的值改不动本地 | 远程配置源优先级默认高于本地文件 | 调 `spring.cloud.config.allow-override` / `override-none`，或改用 `spring.config.import` |
| 用 `spring.profiles.active` 在 profile 文件里切 profile | profile 文件中的 `spring.profiles.active` 被禁止 | 用 `spring.profiles.group` 组合，或在外层文件激活 |

## 分层约定建议

生产项目里让优先级"可预期"比"能用"更重要，建议固定三层职责：

| 层 | 载体 | 放什么 | 谁维护 |
|----|------|--------|--------|
| 默认值 | jar 内 `application.yml` | 端口、连接池基线、超时默认值 | 研发，随代码走 |
| 环境差异 | 环境变量（K8s ConfigMap/Secret） | 数据库地址、外部服务域名、开关 | 运维 / 平台 |
| 临时覆盖 | 命令行参数 | 排障时调日志级别、临时关某个功能 | 值班同学，用完即撤 |

配套约定：不要在启动脚本里写死 `-Dspring.profiles.active`，交给部署平台的环境变量；不要用 `@PropertySource` 做主要配置来源；同一目录不要同时存在 `.properties` 和 `.yml`。

## 与 Spring Boot 2.4 之前的差异

| 变化点 | 2.4 之前 | 2.4+ / 3.x |
|--------|----------|------------|
| 配置加载机制 | `ConfigFileApplicationListener` | Config Data API（`spring.config.import`） |
| 外部配置引入 | `bootstrap.yml` + Spring Cloud Bootstrap | `spring.config.import=optional:configserver:` |
| `spring.profiles.include` | 可在任意位置使用 | 只能在非 profile-specific 文档中使用，多值改用 group |
| profile 激活方式 | `spring.profiles.active` 单值为主 | 支持多 profile + `spring.profiles.group` |

## 参考

- [Spring Boot 官方文档：Externalized Configuration（15 层优先级原始表）](https://docs.spring.io/spring-boot/reference/features/external-config.html)
- [Spring Boot 官方文档：Profile-specific Configuration](https://docs.spring.io/spring-boot/reference/features/profiles.html)
- [Relaxed Binding 规则说明](https://docs.spring.io/spring-boot/reference/features/external-config.html#features.external-config.typesafe-configuration-properties.relaxed-binding)
- 各版本使用指南：[[spring-boot3|Spring Boot 3]]、[[spring-boot4|Spring Boot 4]]、[[spring-boot2|Spring Boot 2]]
- `-D` 与 `-X`/`-XX` 的区别见 [[jvm-options|JVM 启动参数速查]]
