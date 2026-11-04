---
title: JVM 启动参数与 -D 系统属性速查
description: 常用 -D 系统属性、-X/-XX 参数分类速查，含优先级规则、生效验证与失效参数清单
tags:
  - java
  - jvm
  - configuration
  - troubleshooting
date: 2026-11-04
aliases:
  - jvm-d-options
---

# JVM 启动参数与 -D 系统属性速查

> 覆盖 JDK 8 ~ JDK 21。原理部分见 [[jvm|JVM 虚拟机核心原理]]，本文只解决"该写哪个参数、值怎么给、为什么不生效"。

## 常用操作速查

| 场景 | 参数 | 说明 |
|------|------|------|
| 改默认时区 | `-Duser.timezone=Asia/Shanghai` | 容器里最常见的问题源 |
| 强制 UTF-8 | `-Dfile.encoding=UTF-8` | JDK 18+ 已是默认 |
| 临时目录 | `-Djava.io.tmpdir=/data/app/tmp` | 容器根分区只读时必设 |
| 指定 Spring 环境 | `-Dspring.profiles.active=prod` | 等价 `--spring.profiles.active=prod` |
| 指定外部配置 | `-Dspring.config.additional-location=file:/etc/app/` | 保留 jar 内配置并叠加外部 |
| 日志配置外置 | `-Dlogback.configurationFile=/etc/app/logback.xml` | log4j2 用 `-Dlog4j.configurationFile=` |
| 无图形环境 | `-Djava.awt.headless=true` | 避免验证码/图片处理报 AWT 错 |
| 内网代理 | `-Dhttps.proxyHost=10.0.0.1 -Dhttps.proxyPort=8080` | 配合 `-Dhttp.nonProxyHosts` |
| 自定义信任库 | `-Djavax.net.ssl.trustStore=/etc/app/truststore.jks` | 连自签 HTTPS 服务时 |
| 验证全部属性 | `java -XshowSettings:properties -version` | 排查拼写错误的第一招 |

## 先分清三类参数

Java 启动器把参数分成三个体系，**混用是排障中最常见的浪费**：

| 前缀 | 全称 | 作用对象 | 典型示例 | 是否标准 |
|------|------|----------|----------|----------|
| `-D` | Define property | **系统属性表**（`System.getProperty` 读） | `-Duser.timezone=Asia/Shanghai` | 标准，所有 JVM 通用 |
| `-X` | 非标准 | JVM 实现自身（内存、栈） | `-Xms2g -Xmx2g -Xss512k` | 非标准，HotSpot 约定 |
| `-XX` | 高级选项 | JVM 内部行为（收集器、JIT） | `-XX:+UseG1GC -XX:MaxMetaspaceSize=512m` | 非标准，随版本变化 |

一句话区分：**`-D` 改的是"程序能读到的配置"，`-X`/`-XX` 改的是"JVM 自己的行为"**。`-D` 不需要 JVM 认识这个键——写错了不会报错，只是没人读它；`-XX` 写错则会启动失败并提示 `Unrecognized VM option`。

### `-D` 的语法细节

```bash
# 正确：键值紧贴等号，整体作为一个 shell 参数
java -Dapp.env=prod -Dapp.region=cn-north -jar order-service.jar

# 值含空格：整体加引号，引号不能出现在等号左侧
java -Dapp.displayName="Order Service" -jar order-service.jar

# 只给键：值为空字符串 ""（不是 null，也不是 true）
java -Dfeature.audit -jar order-service.jar
```

**读法验证**：

```java
public class PropertyProbe {
    public static void main(String[] args) {
        // 三类来源的读取顺序：系统属性 → 环境变量兜底，是常见配置习惯
        String env = System.getProperty("app.env", "dev");
        String region = System.getProperty("app.region");
        System.out.println("app.env=" + env + ", app.region=" + region);
        // 只给键时输出空串而非 null
        System.out.println("feature.audit=[" + System.getProperty("feature.audit") + "]");
    }
}
```

## 优先级与生效规则

| 规则 | 说明 |
|------|------|
| 位置必须在主类之前 | `java -jar app.jar -Dfoo=bar` 里的 `-D` 会变成 `main(String[] args)` 的入参，属性不生效 |
| 同名后者覆盖前者 | 重复写 `-Dapp.env=dev -Dapp.env=prod`，以 `prod` 为准 |
| 命令行 > 环境变量注入 | `JAVA_TOOL_OPTIONS` / `JDK_JAVA_OPTIONS` 会被**拼在命令行参数之前**，因此命令行能覆盖它们 |
| 代码可运行时覆盖 | `System.setProperty()` 在启动后执行，优先级高于启动参数（但用 `System.getProperty` 拿默认值的框架仍可能已读过一次） |
| 容器环境下只看最终进程 | K8s 里改 Deployment 的 `env` 后务必 `ps -ef \| grep java` 确认参数真的进去了 |

```bash
# 临时诊断推荐：对所有 JVM 生效，包括构建工具，用完即删
export JAVA_TOOL_OPTIONS="-Dapp.env=debug"
# JDK_JAVA_OPTIONS 只影响 java 启动器（不影响 javac/mvn 等）
export JDK_JAVA_OPTIONS="-Dspring.profiles.active=local"
```

> **注意**：`JAVA_TOOL_OPTIONS` 会作用于同机所有 JVM 进程，生产机上误留会导致构建、运维脚本行为异常。仅作临时手段。

## 配置参考

### 编码、时区与本地化

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-Dfile.encoding=UTF-8` | JDK 18+ 为 UTF-8，之前随平台 | 读写文件/控制台的默认字符集（JEP 400） |
| `-Dfile.encoding=COMPAT` | — | JDK 18+ 想恢复"跟随系统编码"的旧行为 |
| `-Dsun.jnu.encoding=zh_CN.UTF-8` | 随系统 locale | Linux 上**文件名**的编码，中文文件名乱码查这个 |
| `-Duser.timezone=Asia/Shanghai` | 随系统 | 时区，容器默认 UTC 时最常被忽略 |
| `-Duser.language=zh -Duser.country=CN` | 随系统 | 影响 `Locale.getDefault()`，日期/数字格式化随之变化 |
| `-Djava.locale.providers=COMPAT,CLDR` | `CLDR,COMPAT` | JDK 9+ 的 Locale 数据源，旧系统升级后日期格式变化时查这里 |

```bash
# 容器内推荐的显式声明组合，消除"本地正常、线上乱码/差 8 小时"
java -Dfile.encoding=UTF-8 \
     -Duser.timezone=Asia/Shanghai \
     -Duser.language=zh -Duser.country=CN \
     -jar order-service.jar
```

### 路径与文件

| 参数 | 说明 |
|------|------|
| `-Djava.io.tmpdir=/data/app/tmp` | 临时目录，容器只读根分区、或 `/tmp` 被清空策略影响时必设 |
| `-Djava.library.path=/opt/app/native` | `System.loadLibrary()` 的搜索路径（JNI 依赖） |
| `-Dlogback.configurationFile=/etc/app/logback.xml` | Logback 外部配置 |
| `-Dlog4j.configurationFile=/etc/app/log4j2.xml` | Log4j2 外部配置 |
| `-Djava.util.logging.config.file=/etc/app/logging.properties` | JUL 配置 |
| `-Dspring.config.additional-location=file:/etc/app/` | Spring Boot 追加配置目录（保留 jar 内配置） |
| `-Dspring.config.location=file:/etc/app/application.yml` | Spring Boot 替换默认配置位置 |

### 网络与代理

| 参数 | 说明 |
|------|------|
| `-Dhttp.proxyHost=10.0.0.1` `-Dhttp.proxyPort=8080` | HTTP 代理，对 `HttpURLConnection` 生效 |
| `-Dhttps.proxyHost=10.0.0.1` `-Dhttps.proxyPort=8080` | HTTPS 代理，**必须单独设**，不会复用 http 的 |
| `-Dhttp.nonProxyHosts="localhost\|127.0.0.1\|*.internal"` | 直连白名单，`\|` 分隔，值含管道符必须加引号 |
| `-Djava.net.preferIPv4Stack=true` | 只走 IPv4，双栈环境下连接超时/连不通时的排查开关 |
| `-DsocksProxyHost=10.0.0.2` `-DsocksProxyPort=1080` | SOCKS 代理 |

```bash
# 典型内网组合：走代理但排除内网域名
java -Dhttps.proxyHost=10.0.0.1 -Dhttps.proxyPort=8080 \
     -Dhttp.nonProxyHosts="localhost|127.0.0.1|*.internal|10.*" \
     -jar report-service.jar
```

> 注意：这些属性只影响 JDK 自带 HTTP 客户端（`HttpURLConnection`）以及遵循它们的库。OkHttp、Apache HttpClient、WebClient 通常需要各自配置，`-D` 不一定生效。

### TLS 与证书

| 参数 | 说明 |
|------|------|
| `-Djavax.net.ssl.trustStore=/etc/app/truststore.jks` | 自定义信任库（连自签/企业 CA 的服务） |
| `-Djavax.net.ssl.trustStorePassword=changeit` | 信任库口令 |
| `-Djavax.net.ssl.keyStore=/etc/app/client.p12` | 双向 TLS 的客户端证书 |
| `-Djdk.tls.client.protocols=TLSv1.2` | 限制客户端协议版本（老服务只支持 1.2 时） |
| `-Dhttps.protocols=TLSv1.2` | 仅对 `HttpsURLConnection` 生效 |
| `-Djava.security.debug=ssl` | 打印 SSL 握手细节，排查证书链问题的终极手段（日志量大） |

`-Djava.security.debug=ssl` 输出极啰嗦，只在定位 `PKIX path building failed` 类问题时短暂开启。

### 监控、调试与诊断

| 参数 | 说明 |
|------|------|
| `-Dcom.sun.management.jmxremote` | 开启 JMX |
| `-Dcom.sun.management.jmxremote.port=9010` | JMX 端口 |
| `-Dcom.sun.management.jmxremote.local.only=false` | 允许远程连接 |
| `-Dcom.sun.management.jmxremote.authenticate=false` `-Dcom.sun.management.jmxremote.ssl=false` | 关闭认证与 SSL，**仅限隔离内网**，公网暴露等于开门 |
| `-Djava.rmi.server.hostname=10.0.0.12` | RMI 回连地址，容器/NAT 环境下不设会连不上 |
| `-Djava.awt.headless=true` | 无图形环境运行，避免 `HeadlessException` |
| `-Dio.netty.leakDetection.level=paranoid` | Netty 检测堆外内存泄漏，`simple`/`advanced`/`paranoid` 逐级变重 |
| `-Dio.netty.maxDirectMemory=0` | Netty 不再自行管理直接内存，全部交给 JVM |

### 应用与框架层（本质仍是 `-D`）

| 参数 | 所属 | 说明 |
|------|------|------|
| `-Dspring.profiles.active=prod` | Spring Boot | 激活 profile |
| `-Dserver.port=8081` | Spring Boot | 覆盖端口 |
| `-Dspring.main.allow-circular-references=true` | Spring Boot | 放开循环依赖（临时救火，别长期留） |
| `-Dspring.devtools.restart.enabled=false` | Spring Boot DevTools | 生产关闭热重启 |
| `-Dlog4j2.debug=true` | Log4j2 | 打印配置加载过程，排查"配置没生效" |
| `-Djava.util.concurrent.ForkJoinPool.common.parallelism=16` | JDK | 公共 ForkJoinPool 并行度，影响 `parallelStream()` |
| `-Dreactor.netty.ioWorkerCount=8` | Reactor Netty | IO 线程数 |

## 排错对照表

| 现象 | 原因 | 处理 |
|------|------|------|
| 参数明明加了却不生效 | `-D` 写在了主类/jar 之后 | 移到 `-jar` 之前 |
| 参数不生效且无任何报错 | 键名拼错（`-Dspring.proflie.active`），`-D` 静默忽略未知键 | `jcmd <pid> VM.system_properties` 核对实际值 |
| 值被截断或只取到一半 | 值含空格未加引号，被切成两个参数 | `-Dkey="a b"` |
| 时区差 8 小时 | 容器默认 UTC，未设 `user.timezone` | 加 `-Duser.timezone=Asia/Shanghai` 或挂载 `/etc/localtime` |
| 中文文件名乱码但内容正常 | `sun.jnu.encoding` 与系统 locale 不一致 | 设置正确 locale 或统一 UTF-8 |
| `Unrecognized VM option` | `-XX` 参数拼错或该版本不支持 | 换 `-XX:+PrintFlagsFinal` 查实际支持的选项 |
| 启动变慢且随机卡住 | 旧版 JDK `SecureRandom` 读 `/dev/random` 阻塞熵池 | 升级 JDK；旧版临时用 `-Djava.security.egd=file:/dev/urandom` |
| 改了 `-Dfile.encoding` 仍乱码 | 未覆盖 `sun.jnu.encoding`，或 JDK 18+ 下无效 | 见上文编码表格 |

### 已失效 / 不要再用的参数

| 参数 | 状态 | 替代方案 |
|------|------|----------|
| `-Djava.ext.dirs` | JDK 9 移除 | classpath / 模块路径 |
| `-Djava.endorsed.dirs` | JDK 9 移除 | 直接依赖正确版本 |
| `-Djava.security.manager` | JDK 17 废弃，JDK 24 起停用 | 容器/进程级隔离 |
| `-Dweblogic.*` / `-Dsun.*` 私有键 | 未文档化，跨版本可能消失 | 优先用公开 API 或框架配置 |

## 生效性验证三步

```bash
# 1. 看启动脚本最终拼出的参数（以 pid 查命令行）
ps -ef | grep '[j]ava'

# 2. 打印 JVM 视角下的全部系统属性（含默认值，可确认拼写）
jcmd <pid> VM.system_properties | grep -E 'app\.|user\.timezone'

# 3. 不启动应用也能预检：直接让 java 打印属性表
java -Dapp.env=prod -XshowSettings:properties -version 2>&1 | grep -E 'app\.env|user\.timezone'
```

`-XshowSettings:properties` 是排查 `-D` 的最省事手段——它把 JVM 实际读到的属性全打出来，拼写错误一眼就能看出"少了个字母所以没出现"。

> 参数放哪儿：内存/GC 类（`-Xms`、`-XX`）建议写死在启动脚本或 Dockerfile 的 `ENTRYPOINT`；环境相关（profile、时区、外部配置路径）优先用环境变量 + 启动脚本转换，避免同机不同服务参数漂移。

## 参考

- [Java 启动器官方文档（`java` 命令与 `-D`）](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)
- [JEP 400: UTF-8 by Default](https://openjdk.org/jeps/400)
- [JDK 21 系统属性完整清单（System Properties for Java 2 SDK）](https://docs.oracle.com/en/java/javase/21/docs/api/system-properties.html)
- 原理与 GC 参数见 [[jvm|JVM 虚拟机核心原理]]
- Spring Boot 参数覆盖顺序见 [[spring-boot2|Spring Boot 2 配置]]
