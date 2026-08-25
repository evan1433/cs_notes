---
title: Tomcat 与 Jetty 架构深度解析
description: 基于"深入拆解 Tomcat & Jetty"系列笔记，系统梳理 Web 容器、HTTP 协议、Servlet 规范、Tomcat 连接器与容器架构、生命周期与启动流程，并对比 Jetty 架构与选型
tags:
  - tomcat
  - jetty
  - servlet
  - web-server
  - java
date: 2026-08-23
---

# Tomcat 与 Jetty 架构深度解析

> 本文档基于简书博主 [r09er](https://www.jianshu.com/u/d359562d9cd0) 的《深入拆解 Tomcat & Jetty》系列笔记（共七篇）整理，主体为 Tomcat 架构分析；Jetty 部分及两者对比为补充内容。

## 一、Web 容器概述

### 1.1 什么是 Web 容器

随着互联网的发展，静态页面不能满足动态获取结果的需求。Sun 公司推出了 `Servlet` 技术——可以简单理解为运行在服务端的 Java 程序。但 **Servlet 并没有 main 方法**，需要一个容器对 Servlet 进行实例化并调用它。

**Tomcat 和 Jetty 就是运行 Servlet 的容器，为了方便使用，同时具备 HTTP 服务器的功能，因此它们本质上是：**

```text
Web 容器 = HTTP 服务器 + Servlet 容器
```

### 1.2 轻量级服务器趋势

在微服务架构下，以 Spring Boot 为代表的内嵌式 Servlet 容器非常流行：

- 服务变多 → 要求 Web 服务器轻量，消耗更少的内存和 CPU
- 由应用本身启动嵌入式 Web 容器，显著降低部署复杂度
- Spring Boot 内嵌的 Tomcat 已支持 Servlet 4.0 规范

### 1.3 学习 Web 容器的知识要求

| 领域 | 需要掌握的内容 |
|------|----------------|
| 操作系统 | 进程与线程、线程同步、内核空间/用户空间、进程通信、虚拟内存、I/O 模型、阻塞与非阻塞、同步与异步 |
| 网络 | OSI 七层模型、TCP/IP、UDP、HTTP 协议 |
| Java 语言 | 集合、多线程与并发、BIO/NIO/AIO、注解、反射 |
| JVM | 类加载机制、JVM 内存模型、内存空间分布、JVM 内存与本地内存的区别、GC 原理 |
| JavaWeb | Servlet 规范、Spring MVC 与 Servlet 的关系 |

> **关键认知**：Spring MVC 框架就是对 Servlet 的封装，Spring MVC 应用本身就是一个 Servlet（`DispatcherServlet`）。理解 `Servlet` 与 `Servlet 容器`的工作方式，才能更好地理解 Spring MVC。

## 二、HTTP 协议必知必会

### 2.1 HTTP 的本质

HTTP（Hyper Text Transfer Protocol，超文本传输协议）是浏览器与服务器之间的数据传输协议：

- 基于 TCP/IP 的**应用层协议**，用于传递 HTML 文件、图片、查询结果等数据
- 不涉及数据包（Packet）传输细节，主要规定**客户端和服务器之间的通信格式**

**HTTP 协议的本质就是浏览器与服务器之间约定好的通信格式。**

在一次 HTTP 请求过程中，Tomcat/Jetty 负责：`接受连接` → `解析请求数据` → `处理请求` → `发送响应`。

### 2.2 请求与响应结构

HTTP 请求数据由三部分组成：

| 组成部分 | 内容 |
|----------|------|
| 请求行 | 请求方法、URL、协议版本 |
| 请求头 | Content-Type、Cookie 等 |
| 请求正文 | 表单数据、JSON 等 |

当请求数据到达 Tomcat 后，Tomcat 将字节流解析成 `Request` 对象（封装全部 HTTP 请求信息），交给 Web 应用处理，得到 `Response` 对象后再转换成 HTTP 格式的响应数据发送给浏览器。

HTTP 响应同样由三部分组成：**状态行、响应头、响应体**。

### 2.3 Cookie 与 Session

HTTP 是无状态协议，两次请求之间服务器无法识别用户，由此产生了 Cookie 和 Session：

| 对比项 | Cookie | Session |
|--------|--------|---------|
| 存储位置 | 用户本地文件 | 服务器开辟的存储空间 |
| 安全性 | 携带用户信息，存在安全隐患 | 用户信息保存在服务端，相对安全 |
| 作用 | 存储用户标识 | 通过 Cookie 中的标识查找对应用户状态 |
| 流量 | 每次请求携带完整信息 | 只传标识，节省流量 |

Session 的创建与存储要点（以 Tomcat 为例）：

- Web 应用调用 `HttpServletRequest.getSession()` 时由 Web 容器创建
- Tomcat 提供多种 Session 持久化方案，生产环境通常采用 Redis 等分布式存储防止单点故障
- Session 有过期时间，Tomcat 会开启后台线程定时轮询，过期则使其失效

## 三、Servlet 规范与 Servlet 容器

### 3.1 为什么需要 Servlet 容器

HTTP 服务器收到请求后需要调用服务端程序（开发人员编写的 Java 类）处理，但：

1. HTTP 服务器**不知道**该调用哪个 Java 类的哪个方法 → 于是有了 `Servlet 接口`
2. 对于特定请求，HTTP 服务器不知道由哪个 Servlet 处理 → 于是有了 `Servlet 容器`

Servlet 容器负责加载和管理业务类，将 HTTP 请求转发到具体的 Servlet；若 Servlet 尚未创建则先实例化，再调用其接口方法。

**Servlet 接口其实是 Servlet 容器跟具体业务类之间的接口**；Servlet 接口 + Servlet 容器这套规范就是 `Servlet 规范`。**Tomcat 和 Jetty 都按 Servlet 规范实现了 Servlet 容器，同时具备 HTTP 服务器功能。**

### 3.2 Servlet 接口

```java
public interface Servlet {
    void init(ServletConfig config) throws ServletException;
    ServletConfig getServletConfig();
    void service(ServletRequest req, ServletResponse res)
            throws ServletException, IOException;
    String getServletInfo();
    void destroy();
}
```

- 最重要的是 `service` 方法，业务逻辑在此实现
- `ServletRequest` 封装请求信息、`ServletResponse` 封装响应信息——**本质上是这两个类对通信协议的封装**
- Spring MVC 的 `DispatcherServlet` 在 `init` 方法中创建了自己的 Spring 容器

一个可运行的最小 Servlet 示例：

```java
import javax.servlet.ServletException;
import javax.servlet.http.*;

public class HelloServlet extends HttpServlet {
    @Override
    public void init() throws ServletException {
        System.out.println("Servlet 初始化");
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws java.io.IOException {
        resp.setContentType("text/plain;charset=UTF-8");
        resp.getWriter().write("Hello from Servlet!");
    }
}
```

配合 `WEB-INF/web.xml` 中的 `servlet-mapping` 配置即可在 Tomcat 中运行。

### 3.3 Servlet 容器工作流程

1. HTTP 服务器将请求封装成 `ServletRequest` 对象，调用 Servlet 的 `service` 方法
2. 根据请求 URL 与 Servlet 的映射关系，找到相应的 Servlet
3. 如果 Servlet 没有被加载，利用**反射机制**创建，调用 `init` 方法完成初始化，再调用 `service` 方法处理请求
4. 响应内容封装成 `ServletResponse` 返回给 HTTP 服务器，发送给客户端

### 3.4 Web 应用目录结构

根据 Servlet 规范，Web 应用程序有一定目录结构：

```shell
|- WebApp
 |- WEB-INF/web.xml     -- 配置文件，用来配置 Servlet
 |- WEB-INF/lib/        -- 存放 Web 应用的各种 Jar 包
 |- WEB-INF/classes/    -- 存放应用类、Servlet 类
 |- META-INF/           -- 存放工程的信息
```

Servlet 规范定义了 `ServletContext` 接口对应 Web 应用：

- Web 应用部署后，Servlet 容器启动时加载 Web 应用，并为其创建**唯一**的 `ServletContext` 对象
- 一个应用只有一个 `ServletContext`，有多个 Servlet，Servlet 之间可通过 `ServletContext` 共享数据

### 3.5 扩展机制：Filter 与 Listener

**Filter（过滤器）**：对请求和响应做定制化处理，例如限流、根据地区修改响应内容。

- 工作原理：Servlet 容器把所有 Filter 链接成 `FilterChain`，请求进来后获取第一个 Filter 调用 `doFilter` 方法，`doFilter` 负责调用 FilterChain 的下一个节点——**责任链模式**

**Listener（监听器）**：监听容器内部事件，如 Web 应用的启动、停止、用户请求到达等。

- Spring 实现了自己的监听器来监听 `ServletContext` 启动事件，在 Servlet 容器启动时创建并初始化全局的 Spring 容器（即 `ContextLoaderListener`）

两者的本质区别：

| 对比项 | Filter | Listener |
|--------|--------|----------|
| 作用方式 | 干预过程，是过程的一部分，基于过程行为 | 基于状态，任何行为改变同一个状态，触发的事件一致 |
| 典型场景 | 请求/响应处理链 | 容器生命周期事件通知 |

## 四、Tomcat 总体架构

### 4.1 两大核心组件

Tomcat 需要做两件事：

1. **处理 Socket 连接**，负责网络字节流与 Request/Response 对象的转化
2. **加载和管理 Servlet**，以及具体处理 Request 请求

为此 Tomcat 设计了两个核心组件：**连接器（Connector）负责对外交流，容器（Container）负责内部处理**。一个容器可以对接多个连接器（多种协议/IO 模型），连接器与容器组合形成 `Service` 对外提供服务，一个 Tomcat 实例可以有多个 Service。连接器与容器之间通过 `ServletRequest` / `ServletResponse` 通信。

### 4.2 支持的 I/O 模型与应用层协议

| 分类     | 类型       | 说明                             |
| ------ | -------- | ------------------------------ |
| I/O 模型 | NIO      | 非阻塞 IO，使用 Java NIO 类库实现        |
| I/O 模型 | NIO2     | 异步 IO，采用 JDK7 的 NIO2 类库实现      |
| I/O 模型 | APR      | 采用 Apache 可移植运行库（C/C++ 编写的本地库） |
| 应用层协议  | HTTP/1.1 | 大部分 Web 应用采用的访问协议              |
| 应用层协议  | AJP      | 用于和 Web 服务器集成                  |
| 应用层协议  | HTTP/2   | 较新的 Web 应用协议，大幅提升 Web 性能       |

## 五、连接器（Connector）详解

### 5.1 连接器的九大功能

1. 监听网络端口
2. 接受网络连接请求
3. 读取请求网络字节流
4. 根据具体应用层协议（HTTP/AJP）解析字节流，生成统一的 Tomcat Request 对象（`org.apache.coyote.Request`）
5. 将 Tomcat Request 对象转换成标准的 ServletRequest
6. 调用 Servlet 容器，得到 ServletResponse
7. 将 ServletResponse 转成 Tomcat Response 对象（`org.apache.coyote.Response`）
8. 将 Tomcat Response 转成网络字节流
9. 将响应字节流写回给浏览器

这九大功能内聚为三大模块，对应三个核心组件：

| 组件 | 职责 |
|------|------|
| **EndPoint** | 网络通信，处理传输层 |
| **Processor** | 应用层协议解析（HTTP/AJP） |
| **Adapter** | Tomcat Request/Response 与 ServletRequest/ServletResponse 的转换 |

### 5.2 ProtocolHandler：组合的封装

由于 I/O 模型和应用层协议可以自由组合（如 NIO+HTTP、NIO2+AJP），Tomcat 通过 `ProtocolHandler` 接口封装这种组合的变化，每种组合都有对应的实现类，如 `Http11NioProtocol`、`AjpNioProtocol`。

### 5.3 EndPoint：通信端点

- EndPoint 监听通信端口，实现 TCP/IP 协议，是具体 Socket 接收和发送的处理器，**是对传输层的抽象**
- 抽象类 `AbstractEndpoint` 是主要逻辑实现，其中定义了两个重要的类：
  - **Acceptor**：实现 `Runnable`，用于监听 Socket 连接请求
  - **SocketProcessor**：继承 `SocketProcessorBase`，其 `run` 方法中调用协议处理组件 Processor；为提高处理能力，SocketProcessor 会被**提交到线程池**中执行
- Tomcat 的线程池扩展了原生 Java 线程池

### 5.4 请求在连接器中的流转

```text
1. EndPoint 接收到 Socket 连接后，生成一个 SocketProcessor
2. 将 SocketProcessor 提交到线程池
3. SocketProcessor 在 run 方法中调用 Processor 解析应用层协议
4. Processor 通过解析字节流生成 Tomcat Request 对象
5. Processor 调用 Adapter 的 service 方法
```

### 5.5 Adapter：协议适配

Tomcat Request 对象并不能被 Servlet 容器直接处理，需要一层适配：

- 具体实现为 `org.apache.catalina.connector.CoyoteAdapter`
- 连接器调用 CoyoteAdapter 的 service 方法，传入 Tomcat Request 对象
- CoyoteAdapter 负责将 Tomcat Request 转成 ServletRequest，再调用容器的 service 方法

> **设计精髓**：连接器对 Servlet 容器屏蔽了协议和 I/O 模型的差异，暴露出标准的 ServletRequest 对象——典型的适配器模式。

## 六、容器（Container）详解

### 6.1 四层容器层次结构

Tomcat 的容器用来装载 Servlet，设计了 4 种有层级关系的容器：

```text
Container
 └── Engine          引擎：管理站点，一个 Service 只能有一个 Engine
      └── Host       虚拟主机：一个站点，可配置多个虚拟主机域名
           └── Context  Web 应用：一个 Context 代表一个 Web 应用
                └── Wrapper  Servlet 包装：一个 Wrapper 对应一个 Servlet
```

顶层接口 `Container` 的关键方法（体现父子关系管理）：

```java
public interface Container extends Lifecycle {
    public void setName(String name);
    public Container getParent();
    public void setParent(Container container);
    public void addChild(Container child);
    public void removeChild(Container child);
    public Container findChild(String name);
}
```

这种层级关系可以直接从 `server.xml` 配置文件中看出来。

### 6.2 请求定位 Servlet 的过程

以一个网购系统为例：后台管理系统和在线购物系统跑在同一个 Tomcat 上，通过两个虚拟域名隔离：`manage.shopping.com` 和 `user.shopping.com`。用户请求 `http://user.shopping.com:8080/order/buy` 时：

1. **根据协议和端口选定 Service 和 Engine**：每个 Connector 对应不同端口（HTTP 默认 8080，AJP 默认 8009），根据 8080 定位 Connector → Connector 只属于一个 Service → Service 确定 Engine
2. **根据域名选定 Host**：Mapper 组件通过 URL 中的域名 `user.shopping.com` 查找对应的 Host 容器
3. **根据 URL 确定 Context**：URL 中的 `/order` 确定 Context（Web 应用）
4. **根据 URL 找到 Wrapper（Servlet）**：Mapper 通过 `web.xml` 配置的 Servlet 映射路径找到具体的 Wrapper 和 Servlet

> 注意：并不是只有最终的 Servlet 处理请求，**整个定位路径上的容器都会对请求进行处理**，一层层传递到 Wrapper，最后由 Wrapper 调用 Servlet。这个过程通过 **Pipeline-Valve 管道**实现。

### 6.3 Pipeline-Valve：责任链模式

- 每个 Valve 代表一个处理点，`Valve` 接口中的 `getNext` / `setNext` 方法体现了责任链设计
- `Pipeline` 维护 Valve 的链表，且有一个 `BasicValve`（基础阀），用于调用下层容器的第一个 Valve
- 入口在连接器：`CoyoteAdapter#service` 方法调用 Pipeline 中第一个 Valve，触发整条链
- 最后的 `WrapperValve` 的 `invoke` 方法中会创建 **FilterChain**，并调用所有 Filter 的 `doFilter` 方法

```text
请求 → CoyoteAdapter
      → Engine Pipeline（Valve... → StandardEngineValve）
      → Host Pipeline（Valve... → StandardHostValve）
      → Context Pipeline（Valve... → StandardContextValve）
      → Wrapper Pipeline（Valve... → StandardWrapperValve）
      → 创建 FilterChain → Filter.doFilter... → Servlet.service
```

### 6.4 Valve 与 Filter 的区别

| 对比项 | Valve | Filter |
|--------|-------|--------|
| 规范来源 | Tomcat 内部实现机制，与 Tomcat 架构紧密结合 | Servlet 规范定义，可运行在所有支持 Servlet 规范的容器 |
| 作用范围 | 运行在 Web 容器中，拦截**所有**经过 Tomcat 的请求 | Context 级隔离（应用隔离），只拦截某个 Web 应用 |

### 6.5 三个"Context"的辨析

| 概念 | 说明 |
|------|------|
| Tomcat 的 Context 组件 | Tomcat 中代表 Web 应用的容器，装载所有 Servlet 对应的 Wrapper，内部包含 ServletContext 变量 |
| ServletContext | Servlet 规范中表示 Web 应用上下文环境的接口 |
| Spring 的 ApplicationContext | Spring 框架 BeanFactory 的重要实现，对外提供 Bean 的获取和访问；Tomcat 的每个 Context 只有一个 Spring IOC 容器 |

> `ContextLoaderListener` 监听容器初始化，Spring 在监听触发后初始化父容器 ApplicationContext，然后存储到 ServletContext 中。

## 七、生命周期管理

### 7.1 为什么需要 Lifecycle

系统对外提供服务，需要**创建、组装、启动**这些组件；停止时需要释放资源、销毁组件。整个过程是动态的，Tomcat 需要统一管理组件的生命周期。

每个组件都要经历 `创建 → 初始化 → 启动` 的过程，状态转变是固定的，但各组件的初始化和启动逻辑不同。因此 Tomcat 把生命周期方法抽象到 `Lifecycle` 接口，由具体组件实现。

### 7.2 设计模式

- **模板方法模式**：`LifecycleBase` 实现了 `Lifecycle` 接口的所有方法，并定义相应抽象方法交给子类实现
- **观察者模式**：组件状态变化会通知所有监听器（Listener）；`LifecycleState` 枚举类定义了组件的所有状态

### 7.3 `LifecycleBase#init` 的执行步骤

初始化方法用 `synchronized` 修饰（组件创建不能多线程并发进行）：

1. 检查状态
2. 修改状态，触发 `INITIALIZING` 事件监听（状态变化通知所有观察者）
3. 调用子类的初始化方法（模板方法）
4. 修改状态，触发 `INITIALIZED` 事件监听

### 7.4 监听器注册的两种方式

- **Tomcat 自定义监听器**：父组件在创建子组件的过程中注册到子组件。例如 `MemoryLeakTracingListener`（检测 Context 容器内存泄漏）在 Host 容器创建 Context 时注册（位于 `StandardHost#addChild`）
- **server.xml 中定义**：Tomcat 启动时解析 server.xml，创建监听器并注册到容器组件

### 7.5 ContainerBase 的公共逻辑

1. 容器的创建 / 初始化 / 销毁
2. 容器添加 / 删除子容器

## 八、Tomcat 启动过程分析

### 8.1 启动链路

```text
执行 bin/startup.sh
  └── 启动 JVM 运行启动类 BootStrap        （Tomcat 本质是一个 Java 程序）
       └── BootStrap 初始化类加载器，创建 Catalina
            └── Catalina 解析 server.xml，创建各组件，调用 Server.start()
                 └── Server 管理 Service，调用 Service.start()
                      └── Service 管理顶层容器 Engine，调用 Engine.start()
```

> Tomcat 和我们平时写的 Java 程序没有本质区别，只是通过脚本启动，我们常用的 Spring Boot 或简单 Java 类通过 java 命令启动。

**公司类比**（便于记忆）：

| 组件 | 类比角色 | 职责 |
|------|----------|------|
| Catalina | 公司创始人 | 组建团队，创建 Server 及其子组件 |
| Server | CEO | 管理多个事业群（Service） |
| Service | 事业群总经理 | 管理两个职能部门：对外的市场部（连接器）+ 对内的研发部（容器） |
| Engine | 研发部总经理 | 最顶层容器组件 |

### 8.2 Catalina：启动入口

Catalina 的主要任务是创建 Server、解析 `server.xml`、实例化各组件，然后调用 Server 的 init 和 start 方法。`Catalina.start()` 核心流程（简化）：

```java
public void start() {
    // 1. 获取 Server，如果为空则通过 load() 创建（load 会解析 server.xml）
    if (getServer() == null) {
        load();
    }
    // 2. 创建失败直接报错退出
    if (getServer() == null) {
        log.fatal(sm.getString("catalina.noServer"));
        return;
    }
    // 3. 启动 Server
    try {
        getServer().start();
    } catch (LifecycleException e) {
        // 启动失败则销毁 Server 并退出
    }
    // 4. 注册 JVM 关闭钩子（ShutdownHook）
    if (useShutdownHook) {
        if (shutdownHook == null) {
            shutdownHook = new CatalinaShutdownHook();
        }
        Runtime.getRuntime().addShutdownHook(shutdownHook);
    }
    // 5. 监听 Tomcat 停止请求
    if (await) {
        await();
        stop();
    }
}
```

**关闭钩子（Shutdown Hook）**：本质是一个线程，JVM 停止之前会尝试执行该线程的 `run` 方法，用于清理工作（如刷缓存到磁盘、清理临时文件）。`CatalinaShutdownHook` 的 `run` 方法内部只是调用 `Catalina.this.stop()`，最终通过 Server 的 stop 和 destroy 方法完成资源释放。

### 8.3 Server：管理 Service 与停止端口

实现类为 `StandardServer`，继承 `LifecycleBase`，生命周期被统一管理：

- **管理 Service**：通过数组持有所有 Service 引用；每次新增 Service 时创建长度+1 的新数组并用 `System.arraycopy()`（Native 方法）复制，避免数组 1.5 倍自动扩容浪费内存
- **监听停止端口**：Catalina 启动最后的 `await()` 调用 `Server#await`，创建 Socket 在死循环中监听 **8005 端口**，收到 `SHUTDOWN` 指令后退出循环进入 stop 流程——这就是 `shutdown.sh` 能停止 Tomcat 的原理

### 8.4 Service：组件组装者

实现类 `StandardService`，持有 Server、Connector 数组、Engine、Mapper 等组件：

```java
public class StandardService extends LifecycleBase implements Service {
    private Server server = null;                          // Server 实例
    protected Connector connectors[] = new Connector[0];   // 连接器数组
    private Engine engine = null;                          // 对应的 Engine 容器
    protected final Mapper mapper = new Mapper();          // 映射器
    protected final MapperListener mapperListener = new MapperListener(this);
}
```

> `MapperListener` 的作用是支持动态部署：监听容器变化并将信息更新到 Mapper 中。

**启动顺序**（`startInternal`）：先启动 Engine（由 Engine 启动其子容器）→ 再启动 MapperListener → 最后启动连接器。

> 原因：只有对内组件都启动好了才能对外服务，避免连接进来时内部组件尚未初始化完成的问题。**停止顺序与启动顺序刚好相反。**

### 8.5 Engine：顶层容器

- 实现类 `StandardEngine`，继承 `ContainerBase`（很多功能已抽象到 ContainerBase）
- 通过 `HashMap` 持有所有子容器 Host 的引用，启动子容器时使用专门的线程池
- 构造函数中就设置好了 Pipeline 的基础阀：

```java
public StandardEngine() {
    super();
    // 设置第一个基础阀
    pipeline.setBasic(new StandardEngineValve());
}
```

`StandardEngineValve` 是整条调用链的起点之一。由于 Mapper 已对请求完成路由、把目标容器对象保存在 Request 中，基础阀可直接取 Host 并触发下一层 Pipeline：

```java
public final void invoke(Request request, Response response)
        throws IOException, ServletException {
    // 选择该请求对应的 Host
    Host host = request.getHost();
    if (host == null) {
        return;
    }
    // 交给 Host 的 Pipeline 继续处理
    host.getPipeline().getFirst().invoke(request, response);
}
```

### 8.6 线程安全说明

Server 内部使用线程不安全的数组持有 Service、Engine 使用线程不安全的 HashMap 持有 Host；由于存在资源的动态添加和删除，所以在启动连接器和容器时都进行了**加锁**，保证多线程操作共享资源的正确性。

## 九、Jetty 架构

> 博客系列标题虽含 Jetty，但正文以 Tomcat 为主。以下为补充内容，帮助形成完整对比视角。

### 9.1 Jetty 简介

Jetty 是 Eclipse 基金会旗下的开源 Servlet 容器，同样实现 Servlet 规范。它与 Tomcat 定位相同（HTTP 服务器 + Servlet 容器），但设计哲学不同：**Jetty 基于 Handler 的组合式架构，Tomcat 基于容器的层级式架构**。

### 9.2 核心组件

Jetty 的架构比 Tomcat 更扁平，核心三件套：

| 组件 | 职责 | 与 Tomcat 的对应关系 |
|------|------|----------------------|
| Server | Jetty 的入口，持有 ThreadPool 和 Connector，本身也是一个 Handler | 相当于 Service + Catalina 的部分职责 |
| Connector | 接受网络连接（默认 `ServerConnector` 基于 NIO，内部由 `ManagedSelector` 管理事件轮询） | 对应 Connector + EndPoint |
| Handler | 处理请求的核心抽象，所有组件都是 Handler，通过组合完成功能 | 对应 Container 层级 + Pipeline-Valve |

### 9.3 Handler 体系：组合优于继承

Jetty 中**一切皆 Handler**，`HandlerWrapper` 通过链式引用把 Handler 串起来（类似 Tomcat 的 Pipeline-Valve，但由开发者自由组装）：

```text
Server
 └── HandlerWrapper（链式）
      ├── ContextHandlerCollection   -- 按上下文分发
      │    ├── ServletContextHandler -- 提供 ServletContext 环境
      │    │    └── ServletHandler   -- 管理 Filter/Servlet 链
      │    └── WebAppContext         -- 完整 Web 应用（对应 Tomcat 的 Context）
      └── DefaultHandler             -- 兜底处理（404 等）
```

一个嵌入式 Jetty 的最小可运行示例：

```java
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;

public class JettyDemo {
    public static void main(String[] args) throws Exception {
        Server server = new Server(8080);
        ServletContextHandler handler = new ServletContextHandler(ServletContextHandler.SESSIONS);
        handler.setContextPath("/");
        handler.addServlet(new ServletHolder(new HelloServlet()), "/hello");
        server.setHandler(handler);
        server.start();
        server.join();
    }
}
```

### 9.4 Jetty 的线程模型

- Jetty 使用 `QueuedThreadPool`（可替换），负责处理所有已接收的连接
- NIO 模型下由少量 Selector 线程（`ManagedSelector`）监听事件，事件就绪后分发到线程池执行
- 与 Tomcat 的 Acceptor + Poller + 工作线程池结构思想一致，但实现更精简

## 十、Tomcat 与 Jetty 对比

| 对比维度 | Tomcat | Jetty |
|----------|--------|-------|
| 架构风格 | 层级容器（Engine/Host/Context/Wrapper）+ Pipeline-Valve | 扁平 Handler 组合体系，一切皆 Handler |
| 设计模式 | 责任链（Valve）、模板方法（LifecycleBase）、观察者（Lifecycle 事件）、适配器（CoyoteAdapter） | 组合模式（HandlerWrapper）、责任链 |
| 传统优势 | 功能全面、生态成熟、Servlet 规范实现最完整、社区庞大 | 更轻量、模块化强（按需引入 jar）、启动快、内存占用小 |
| 扩展方式 | Valve（容器级）+ Filter（应用级，规范内） | Handler 自由组装，灵活度更高 |
| 长连接/异步 | 支持 NIO/NIO2/APR、HTTP/2 | 原生为异步设计，HTTP/2、WebSocket 支持良好 |
| 典型场景 | 传统 WAR 部署、Spring Boot 默认容器 | 嵌入式场景、网关/代理类组件（如 Solr、Spark、Eclipse IDE）、内嵌定制 |
| 治理 | Apache 基金会 | Eclipse 基金会 |

**选型建议**：

- 一般业务系统、Spring Boot 默认场景 → **Tomcat**（生态成熟、资料多、性能经充分验证）
- 深度定制容器行为、追求极低资源占用、嵌入式组件开发 → **Jetty**
- 两者都遵循 Servlet 规范，对上层应用（Spring MVC 等）透明，切换成本低

## 参考来源

- [深入拆解 Tomcat & Jetty（一）Web 容器](https://www.jianshu.com/p/53be6fb1c130)
- [深入拆解 Tomcat & Jetty（二）HTTP 协议必知必会](https://www.jianshu.com/p/2fb60fc28ba9)
- [深入拆解 Tomcat & Jetty（三）Servlet 规范和 Servlet 容器](https://www.jianshu.com/p/2bfe0639a4d3)
- [深入拆解 Tomcat & Jetty（四）Tomcat 总体架构](https://www.jianshu.com/p/9498728d6b6b)
- [深入拆解 Tomcat & Jetty（五）容器层次结构](https://www.jianshu.com/p/c17c16c6759b)
- [深入拆解 Tomcat & Jetty（六）生命周期管理](https://www.jianshu.com/p/dc2519e5a8aa)
- [深入拆解 Tomcat & Jetty（七）启动过程](https://www.jianshu.com/p/31b26b3025e1)
