---
title: Maven 与 mvn 命令手册
description: Maven 构建生命周期、mvn 常用参数、多模块构建、依赖分析、测试与配置诊断手册
tags:
  - java
  - maven
  - build-tools
date: 2026-07-23
---

# Maven 与 mvn 命令手册

Maven 是以 POM（Project Object Model）为核心的 Java 项目构建与依赖管理工具。`mvn` 是 Maven的命令行入口，可以执行生命周期阶段、插件目标，以及修改构建行为的命令行选项。

本文以 Maven 3.9 为主要基线；仅适用于 Maven 4 的行为会单独标注。

## 1. 命令结构

```bash
mvn [全局选项] [生命周期阶段或插件目标] [-D属性=值]
```

最常见的三种调用形式：

```bash
# 执行生命周期阶段
mvn clean verify

# 执行插件目标，格式为 插件前缀:目标
mvn dependency:tree

# 指定插件的完整坐标，适合插件前缀无法解析的场景
mvn groupId:artifactId:version:goal
```

- **生命周期阶段（phase）**：例如 `compile`、`test`、`package`、`verify`、`install`。
- **插件目标（goal）**：例如 `dependency:tree`、`help:effective-pom`。
- **命令行选项（option）**：例如 `-Pdev`、`-pl :order-service`、`-X`。
- **用户属性（user property）**：通过 `-Dkey=value` 传入，可供 POM 或插件读取。

先确认当前使用的 Java、Maven 版本和配置位置：

```bash
mvn --version
mvn --help
```

## 2. 生命周期与常用构建命令

Maven 内置 `clean`、`default` 和 `site` 三套生命周期。命令执行到某个阶段时，会依次执行该
生命周期中排在它之前的阶段。

| 阶段或命令 | 作用 |
| --- | --- |
| `mvn clean` | 删除上次构建产生的输出，默认是 `target/` |
| `mvn validate` | 检查项目和 POM 是否具备构建所需的信息 |
| `mvn compile` | 编译主代码 |
| `mvn test` | 编译并运行单元测试 |
| `mvn package` | 运行前置阶段并生成 JAR、WAR 等制品 |
| `mvn verify` | 运行检查与集成测试，并验证制品是否有效 |
| `mvn install` | 将制品安装到本地仓库，供本机其他项目使用 |
| `mvn deploy` | 将制品上传到远程仓库，供团队或发布流程使用 |
| `mvn site` | 生成项目站点和报告 |

日常开发常用：

```bash
# 快速编译
mvn compile

# 运行单元测试
mvn test

# 完整验证，通常比只执行 package 更适合提交前检查
mvn clean verify

# 安装到本地仓库
mvn clean install

# 发布到 POM 中 distributionManagement 指定的远程仓库
mvn clean deploy
```

> [!IMPORTANT]
> 不建议单独调用 `pre-*`、`post-*` 或 `process-*` 阶段。对于含集成测试的项目，应执行
> `mvn verify`，而不是只执行 `mvn integration-test`，否则测试环境可能得不到正常清理。

### `package`、`verify`、`install` 与 `deploy` 的区别

```text
package -> verify -> install -> deploy
```

- `package`：只在当前项目的 `target/` 中生成制品。
- `verify`：在打包后继续完成质量检查和集成测试。
- `install`：在验证后将制品写入本地仓库。
- `deploy`：在安装后将制品发布到远程仓库。

## 3. 常用全局选项

| 短选项 | 长选项 | 作用 |
| --- | --- | --- |
| `-B` | `--batch-mode` | 批处理模式，适合 CI，避免交互提示 |
| `-q` | `--quiet` | 只输出错误信息 |
| `-e` | `--errors` | 输出异常堆栈 |
| `-X` | `--debug` | 输出详细调试日志 |
| `-l file` | `--log-file file` | 将构建日志写入文件 |
| `-o` | `--offline` | 离线构建，只使用本地仓库 |
| `-U` | `--update-snapshots` | 强制检查缺失的版本和更新 SNAPSHOT |
| `-nsu` | `--no-snapshot-updates` | 禁止更新 SNAPSHOT |
| `-ntp` | `--no-transfer-progress` | 隐藏依赖下载进度，适合 CI 日志 |
| `-C` | `--strict-checksums` | 校验和不匹配时让构建失败 |
| `-f path` | `--file path` | 使用指定的 POM 文件或项目目录 |
| `-s file` | `--settings file` | 使用指定的用户级 `settings.xml` |
| `-gs file` | `--global-settings file` | 使用指定的全局 `settings.xml` |
| `-P list` | `--activate-profiles list` | 激活或停用 Profile |
| `-T count` | `--threads count` | 并行构建，例如 `4`、`1C`、`2C` |
| `-N` | `--non-recursive` | 只构建当前项目，不递归构建模块 |
| `-V` | `--show-version` | 显示版本后继续构建 |
| `-v` | `--version` | 显示版本后退出 |

适合 CI 的基础组合：

```bash
mvn -B -ntp -C clean verify
```

记录完整日志并显示异常堆栈：

```bash
mvn -e -l build.log clean verify
```

## 4. `-D` 属性与 POM 属性

`-D` 与属性名之间不能有空格。

```bash
mvn package -Drevision=1.2.3
mvn test -Duser.timezone=Asia/Shanghai
mvn package -DskipTests
```

在 POM 中可以用 `${属性名}` 读取命令行属性：

```xml
<properties>
    <revision>1.0.0-SNAPSHOT</revision>
</properties>

<version>${revision}</version>
```

命令行用户属性的优先级通常高于 POM 中的同名普通属性，因此可以用于构建参数化。属性值包含空格、通配符或 shell 特殊字符时应加引号：

```bash
mvn test "-Dtest=OrderServiceTest,PaymentServiceTest"
```

## 5. Profile 用法

### 激活、组合与停用

```bash
# 激活一个 Profile
mvn verify -Pdev

# 同时激活多个 Profile
mvn verify -Pdev,feature-x

# 停用 prod Profile；这种写法可避免 shell 将减号误认为新选项
mvn verify -P=-prod

# 查看实际激活的 Profile
mvn help:active-profiles -Pdev

# 查看项目声明的全部 Profile
mvn help:all-profiles
```

Profile 可在 POM 或 `settings.xml` 中按操作系统、JDK、属性、文件存在性等条件自动激活。

Maven 4 支持在 Profile 名称前加 `?` 表示“如果存在才激活”，例如：

```bash
mvn verify -Pdev,?local-feature
```

Maven 3 不应依赖该语法。停用 `!profile` 时还可能触发 shell 的历史展开，因此更推荐
`-P=-profile`。

## 6. 测试控制

```bash
# 运行全部单元测试
mvn test

# 只运行一个测试类
mvn -Dtest=OrderServiceTest test

# 运行多个测试类
mvn "-Dtest=OrderServiceTest,PaymentServiceTest" test

# 按通配符选择测试类
mvn "-Dtest=*ServiceTest" test

# 运行指定测试方法；具体支持情况取决于测试 Provider
mvn "-Dtest=OrderServiceTest#createsOrder" test
```

两种跳过测试方式不同：

```bash
# 编译测试代码，但不执行测试
mvn package -DskipTests

# 不编译也不执行测试
mvn package -Dmaven.test.skip=true
```

`maven.test.skip=true` 同时受到 Surefire、Failsafe 和 Compiler 插件支持，但它可能掩盖测试代码的
编译错误。日常临时打包通常优先用 `-DskipTests`，正式 CI 不应跳过测试。

## 7. 依赖查询与诊断

### 查看依赖树

```bash
# 查看完整依赖树
mvn dependency:tree

# 只查看指定 groupId/artifactId
mvn dependency:tree -Dincludes=io.netty:*

# 排除指定依赖
mvn dependency:tree -Dexcludes=org.slf4j:*

# 只查看测试范围依赖
mvn dependency:tree -Dscope=test

# 将结果写入文件
mvn dependency:tree -DoutputFile=target/dependency-tree.txt
```

需要借助文本工具进一步过滤时：

```bash
mvn dependency:tree | grep -i netty
```

直接使用 `-Dincludes` 更利于跨平台和自动化。

### 分析、下载与复制依赖

```bash
# 分析已使用但未声明、已声明但未使用的依赖
mvn dependency:analyze

# 解析并下载源码包
mvn dependency:resolve-sources

# 为离线构建预下载项目依赖、插件及其依赖
mvn dependency:go-offline

# 输出编译 classpath
mvn dependency:build-classpath

# 复制运行时依赖
mvn dependency:copy-dependencies -DincludeScope=runtime -DoutputDirectory=target/dependency
```

`dependency:analyze` 基于字节码分析，反射、注解处理器或运行时加载的依赖可能被误报，需要
结合代码实际情况判断。

### 清理本地仓库中的项目依赖

```bash
# 清理当前项目相关依赖，并默认重新解析
mvn dependency:purge-local-repository

# 只清理指定依赖
mvn dependency:purge-local-repository -DmanualInclude=com.example:shared-library
```

> [!WARNING]
> 不要直接删除整个 `~/.m2/repository` 来处理单个依赖问题。优先使用
> `dependency:purge-local-repository` 的过滤参数，降低重新下载全部依赖的成本。

## 8. POM、Settings 与插件诊断

Maven Help Plugin 是排查“配置从哪里来”的首选工具。

```bash
# 查看继承、插值和 Profile 合并后的有效 POM
mvn help:effective-pom

# 输出有效 POM 到文件
mvn help:effective-pom -Dverbose -Doutput=target/effective-pom.xml

# 查看全局与用户配置合并后的有效 Settings
mvn help:effective-settings

# 输出有效 Settings 到文件
mvn help:effective-settings -Doutput=target/effective-settings.xml

# 读取单个表达式，forceStdout 便于脚本获取结果
mvn help:evaluate -Dexpression=project.version -q -DforceStdout

# 查看插件或目标的参数说明
mvn help:describe -Dplugin=dependency -Dgoal=tree -Ddetail

# 查看 Java 系统属性和环境变量
mvn help:system
```

`help:effective-settings` 的输出可能包含仓库、镜像和服务器标识等环境信息，分享前应检查并
脱敏。

## 9. 多模块项目与 Reactor

Maven Reactor 会收集模块、根据模块间依赖排序，然后按顺序构建。

```bash
# 只构建指定模块
mvn -pl :order-service package

# 构建指定模块及其所依赖的 Reactor 模块
mvn -pl :order-service -am clean verify

# 构建指定模块及依赖它的 Reactor 模块
mvn -pl :shared-library -amd test

# 同时选择多个模块
mvn -pl :order-service,:payment-service package

# 从失败模块继续构建
mvn -rf :payment-service verify

# 只构建聚合项目自身，不递归模块
mvn -N validate
```

模块选择器可以是相对路径，也可以是 `groupId:artifactId` 或 `:artifactId`：

```bash
mvn -pl services/order-service -am verify
mvn -pl com.example:order-service -am verify
mvn -pl :order-service -am verify
```

### 失败处理策略

```bash
# 默认策略：遇到第一个失败立即停止
mvn --fail-fast verify

# 当前模块失败后继续构建不受影响的模块，最后返回失败
mvn --fail-at-end verify

# 无论失败都继续，且不以失败状态退出；不建议用于正式 CI
mvn --fail-never verify
```

短选项分别为 `-ff`、`-fae` 和 `-fn`。

### 并行构建

```bash
# 使用 4 个线程
mvn -T 4 clean verify

# 每个 CPU 核心使用 1 个线程
mvn -T 1C clean verify
```

仅当项目使用的插件具备线程安全性时才应开启并行构建。首次启用后，应重点检查代码生成、共享
目录、集成测试端口和外部服务是否存在并发冲突。

## 10. 指定 POM、Settings 与本地仓库

```bash
# 在任意目录使用指定 POM
mvn -f services/order-service/pom.xml clean verify

# 使用项目专用 Settings
mvn -s .mvn/settings.xml clean verify

# 临时使用独立的本地仓库
mvn -Dmaven.repo.local=target/maven-repository clean verify

# 离线构建
mvn -o clean verify

# 强制更新 SNAPSHOT
mvn -U clean verify
```

默认用户配置位于 `~/.m2/settings.xml`，默认本地仓库位于 `~/.m2/repository`。
私服用户名和密码应放在 `settings.xml` 的 `<servers>` 中，并使用 `<id>` 与 POM 的仓库声明关联；不要把凭据写进 POM。

## 11. 调试下载、插件与构建失败

遇到失败时，按从低噪声到高噪声的顺序排查：

```bash
# 显示异常堆栈
mvn -e clean verify

# 输出 Debug 日志
mvn -X clean verify

# 强制检查 SNAPSHOT 和缺失版本
mvn -U clean verify

# 严格校验制品校验和
mvn -C clean verify
```

常用判断：

1. 依赖版本冲突：运行 `mvn dependency:tree`，检查实际选中的版本和依赖路径。
2. POM 继承或 Profile 异常：运行 `mvn help:effective-pom` 和 `help:active-profiles`。
3. 镜像、代理或仓库异常：运行 `mvn help:effective-settings`，检查 `<mirrors>`、`<proxies>`。
4. SNAPSHOT 未更新：先运行 `mvn -U verify`，必要时定向清理本地依赖。
5. 插件参数不确定：运行 `mvn help:describe -Dplugin=插件前缀 -Dgoal=目标 -Ddetail`。

### SSL 校验失败

下面的参数会放宽或跳过 HTTPS 证书校验，只能用于临时诊断：

```bash
mvn verify \
  -Dmaven.wagon.http.ssl.insecure=true \
  -Dmaven.wagon.http.ssl.allowall=true
```

> [!WARNING]
> 这些参数会削弱传输安全，不能作为 CI 或生产环境的长期配置。正确做法是修复证书链，将组织
> CA 导入 Java TrustStore，或修复 Maven 私服的 TLS 配置。

## 12. 插件目标

插件目标的调用形式如下：

```text
mvn prefix:goal
mvn groupId:artifactId:goal
mvn groupId:artifactId:version:goal
```

常见示例：

```bash
mvn compiler:compile
mvn surefire:test
mvn dependency:tree
mvn help:describe -Dplugin=compiler -Dgoal=compile -Ddetail
```

同一条命令可以包含多个阶段和目标，Maven 会按从左到右的顺序执行：

```bash
mvn clean dependency:analyze verify
```

通常优先执行生命周期阶段，让 POM 中绑定的插件按项目约定运行；只有诊断或执行独立任务时，
才直接调用插件目标。

### 安装本地 JAR

第三方 JAR 不在任何仓库中时，可临时安装到本地仓库：

```bash
mvn install:install-file \
  -Dfile=libs/vendor-sdk.jar \
  -DgroupId=com.vendor \
  -DartifactId=vendor-sdk \
  -Dversion=1.2.0 \
  -Dpackaging=jar
```

团队项目更适合把这类制品发布到私服，而不是要求每位开发者手动安装。

## 13. Maven Wrapper

Maven Wrapper 将项目约定的 Maven 版本固定在仓库配置中，开发者和 CI 无须预先安装完全相同的 Maven 版本。

```bash
# macOS/Linux
./mvnw --version
./mvnw clean verify

# Windows
mvnw.cmd --version
mvnw.cmd clean verify
```

为项目添加或更新 Wrapper：

```bash
mvn wrapper:wrapper
```

提交 `.mvn/wrapper/`、`mvnw` 和 `mvnw.cmd` 后，团队构建脚本应优先调用 Wrapper。

## 14. 常用实战组合

### 本地提交前验证

```bash
./mvnw clean verify
```

### CI 构建

```bash
./mvnw -B -ntp -C clean verify
```

### 只验证受影响模块及其依赖

```bash
./mvnw -pl :order-service -am clean verify
```

### 从失败模块继续

```bash
./mvnw -rf :payment-service verify
```

### 准备离线构建

```bash
./mvnw dependency:go-offline
./mvnw -o clean verify
```

### 定位依赖冲突

```bash
./mvnw dependency:tree -Dincludes=com.fasterxml.jackson.core:*
./mvnw help:effective-pom -Doutput=target/effective-pom.xml
```

## 15. POM 核心概念

### 坐标与依赖

Maven 坐标由以下字段标识：

- `groupId`：组织或项目组。
- `artifactId`：模块或制品名称。
- `version`：版本。
- `packaging`：打包类型，默认是 `jar`。

`<dependencies>` 会实际引入依赖，`<dependencyManagement>` 只集中管理默认版本和范围，不会自动
引入依赖。

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-core</artifactId>
            <version>${spring.version}</version>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>org.springframework</groupId>
        <artifactId>spring-core</artifactId>
    </dependency>
</dependencies>
```

### 父 POM、继承与 BOM

父工程通常使用 `pom` 打包方式：

```xml
<packaging>pom</packaging>
```

通过属性集中管理版本：

```xml
<properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <java.version>17</java.version>
    <maven.compiler.release>${java.version}</maven.compiler.release>
    <spring.version>6.2.0</spring.version>
</properties>
```

BOM（Bill of Materials）通常在 `<dependencyManagement>` 中以 `import` 范围导入：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-framework-bom</artifactId>
            <version>${spring.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### 依赖传递与冲突

如果 A 依赖 B、B 依赖 C，则 C 通常会作为 A 的传递依赖。发生版本冲突时，主要遵循：

1. 路径更近的版本优先。
2. 路径深度相同时，先声明的依赖优先。
3. 可通过 `<dependencyManagement>` 显式锁定版本。
4. 可通过 `<exclusions>` 排除不需要的传递依赖。

```xml
<dependency>
    <groupId>com.example</groupId>
    <artifactId>order-client</artifactId>
    <version>1.0.0</version>
    <exclusions>
        <exclusion>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-simple</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

### 依赖范围

| Scope | 编译 | 测试 | 运行 | 是否传递 | 典型用途 |
| --- | --- | --- | --- | --- | --- |
| `compile` | 是 | 是 | 是 | 是 | 默认范围 |
| `provided` | 是 | 是 | 否 | 否 | Servlet API、容器提供的接口 |
| `runtime` | 否 | 是 | 是 | 是 | JDBC 驱动、运行时实现 |
| `test` | 否 | 是 | 否 | 否 | JUnit、测试工具 |
| `system` | 是 | 是 | 否 | 否 | 本机固定路径 JAR，不推荐 |
| `import` | 不适用 | 不适用 | 不适用 | 不适用 | 在依赖管理中导入 BOM |

### Optional 依赖

`optional` 表示当前项目需要该依赖，但依赖当前项目的下游项目不会自动获得它：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-devtools</artifactId>
    <optional>true</optional>
</dependency>
```

## 16. Versions 插件

[Versions Maven Plugin](https://www.mojohaus.org/versions/versions-maven-plugin/) 可检查和修改项目版本。

```bash
# 修改当前项目版本
mvn versions:set -DnewVersion=2.0.0-SNAPSHOT

# 确认修改，删除备份 POM
mvn versions:commit

# 撤销尚未提交的版本修改
mvn versions:revert

# 查看可用的依赖更新
mvn versions:display-dependency-updates

# 查看可用的插件更新
mvn versions:display-plugin-updates
```

插件版本应通过父 POM 的 `<pluginManagement>` 统一锁定，避免依赖构建当天解析到的最新版本。

## 17. 常见误区

- `clean` 属于独立生命周期；`mvn package` 不会自动执行 `clean`。
- `install` 只写入本地仓库，`deploy` 才会上传远程仓库。
- `-P` 是 Profile，必须大写；`-p` 不是它的等价写法。
- `-D` 与属性名之间不能有空格。
- `-DskipTests` 仍编译测试，`-Dmaven.test.skip=true` 连测试编译也跳过。
- `-U` 主要用于更新 SNAPSHOT 和重新检查缺失版本，并不表示无条件重下所有 Release。
- `-fn` 会掩盖失败退出状态，不适合作为正式 CI 的默认策略。
- 并行构建不是线程越多越快，插件、磁盘、网络和外部测试环境都可能成为瓶颈。
- 不要通过关闭 SSL 校验来长期绕过证书问题。

## 参考资料

- [Maven 官方指南](https://maven.apache.org/guides/index.html)
- [Maven CLI 选项参考](https://maven.apache.org/ref/current/maven-embedder/cli.html)
- [Maven 构建生命周期](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html)
- [Maven 多模块构建](https://maven.apache.org/guides/mini/guide-multiple-modules.html)
- [Maven Profile 简介](https://maven.apache.org/guides/introduction/introduction-to-profiles.html)
- [Maven 依赖机制](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)
- [Maven Dependency Plugin](https://maven.apache.org/plugins/maven-dependency-plugin/usage.html)
- [Maven Help Plugin](https://maven.apache.org/plugins/maven-help-plugin/usage.html)
- [Maven Surefire Plugin](https://maven.apache.org/surefire/maven-surefire-plugin/)
- [Maven Wrapper](https://maven.apache.org/wrapper/)
