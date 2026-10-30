---
title: Java Web 开发
description: JavaWeb 服务端开发：Tomcat、XML、Servlet、JSP、Listener、Filter、EL/JSTL、Cookie/Session 等核心组件
tags:
  - java
  - javaweb
  - servlet
  - jsp
date: 2026-10-30
---

# Java Web 开发

**JavaWeb** 是指所有通过 Java 语言编写、可以通过浏览器访问的程序的总称。JavaWeb 是**基于请求和响应**来开发的：请求 `Request`、响应 `Response`。

## 参考

- [尚硅谷最新版JavaWeb全套教程,javaweb零基础入门完整版](https://www.bilibili.com/video/BV1Y7411K7zz/?share_source=copy_web&vd_source=e65574be5c4ff436d099ae0526b97fd9)

## 前置知识：前端三件套

本笔记聚焦服务端部分，教程中涉及的前端基础已整理至 `03-frontend/` 目录：

- [[html|HTML]]：标签、表格、表单、表单提交规则（GET/POST）
- [[css|CSS]]：选择器、CSS 与 HTML 的结合方式
- [[javascript|JavaScript]]：语法、BOM、DOM、事件监听
- [[jquery|jQuery]]：核心函数、选择器、AJAX 请求
- [[json|JSON]]：JS 侧 json 对象/字符串与互转方法

# Tomcat

web服务器：

- `tomcat`: 由 Apache 组织提供的一种 Web 服务器，提供对 jsp 和 Servlet 的支持。它是一种轻量级的 javaWeb 容器（服务器），也是当前应用最广的 JavaWeb 服务器（免费）。
- `Jboss`：是一个遵从 JavaEE 规范的、开放源代码的、纯 Java 的 EJB 服务器，它支持所有的 JavaEE 规范（免费）。

# XML

## 语法

1. **文档声明**  
    XML 文档通常以声明开头，指定 XML 版本和编码方式。  

    ```xml
    <?xml version="1.0" encoding="UTF-8"?>
    ```

2. **元素**  
    元素是 XML 的基本组成部分，使用成对的标签包裹内容。  

    ```xml
    <book>
      <title>Java Web</title>
      <author>Duke</author>
    </book>
    ```

    - 元素必须正确嵌套，区分大小写。

3. **XML 属性**  
    元素可以包含属性，属性以键值对形式出现在开始标签中。  

    ```xml
    <book id="001" category="programming">
      <title>Java Web</title>
    </book>
    ```

4. **XML 注释**  
    注释用于文档说明，不会被解析。  

    ```xml
    <!-- 这是一本 Java Web 书籍 -->
    ```

5. **文本区域（CDATA 区）**  
    CDATA 区用于包含不会被解析的字符数据，适合包含特殊字符的内容。  

    ```xml
    <script><![CDATA[
      if (a < b && b > 0) {
         alert("Hello, XML!");
      }
    ]]></script>
    ```

6. **命名空间（Namespace）**  
    命名空间用于区分不同 XML 文档或元素中可能出现的同名标签，避免命名冲突。通过 `xmlns` 属性声明命名空间，并为元素或属性加上前缀。

    ```xml
    <bookstore xmlns:java="http://example.com/java">
      <java:book>
        <java:title>Java Web</java:title>
      </java:book>
    </bookstore>
    ```

    - 命名空间常用于大型 XML 文档或集成多种标准时，确保标签唯一性。

## 其他注意事项

- XML 必须有且只有一个根元素。
- 标签必须正确关闭，可以使用自闭合标签：`<tag />`
- 属性值必须用引号包裹。
- 支持嵌套和层级结构，常用于数据交换和配置文件。

XML解析技术介绍  
`DOM` 和 `sax`

1. dom 解析技术是 W3C 组织制定的，而所有的编程语言都对这个解析技术使用了自己语言的特点进行实现。 Java 对 dom 技术解析标记也做了实现。
2. SUN 公司在 JDK5 版本对 dom 解析技术进行升级：SAX（ Simple API for XML ） SAX 解析，它跟 W3C 制定的解析不太一样。它是以类似事件机制通过回调告诉用户当前正在解析的内容。 它是一行一行的读取 xml 文件进行解析的。不会创建大量的 dom 对象。 所以它在解析 xml 的时候，在内存的使用上。和性能上。都优于 Dom 解析。

第三方解析：

- `jdom`
- `dom4j`
- `pull` 用于安卓

# Servlet1

## Servlet技术

1. 什么是`Servlet`
    1. Servlet 是 JavaEE 规范之一。规范就是接口
    2. Servlet 就 JavaWeb 三大组件之一。JavaWeb***三大组件***分别是：**Servlet程序、Filter 过滤器、Listener监听器**。
    3. Servlet 是运行在服务器上的一个java小程序，它可以接收客户端发送过来的请求，并响应数据给客户端。

手动实现Servlet程序
1、编写一个类去实现 `Servlet` 接口
2、实现 `service` 方法，处理请求，并响应数据
3、到 `web.xml` 中去配置 `servlet` 程序的访问地址

### web.xml配置

```xml
 <!--context-param是上下文参数(它属于整个web工程)-->
    <context-param>
        <param-name>username</param-name>
        <param-value>context</param-value>
    </context-param>
    <context-param>
        <param-name>password</param-name>
        <param-value>root</param-value>
    </context-param>
    <!-- servlet标签给Tomcat配置Servlet程序 -->
    <servlet>
        <!--servlet-name标签 Servlet程序起一个别名（一般是类名） -->
        <servlet-name>HelloServlet</servlet-name>
        <!--servlet-class是Servlet程序的全类名-->
        <servlet-class>com.atguigu.servlet.HelloServlet</servlet-class>
        <!--init-param是初始化参数-->
        <init-param>
            <!--是参数名-->
            <param-name>username</param-name>
            <!--是参数值-->
            <param-value>root</param-value>
        </init-param>
        <!--init-param是初始化参数-->
        <init-param>
            <!--是参数名-->
            <param-name>url</param-name>
            <!--是参数值-->
            <param-value>jdbc:mysql://localhost:3306/test</param-value>
        </init-param>
    </servlet>
    <!--servlet-mapping标签给servlet程序配置访问地址-->
    <servlet-mapping>
        <!--servlet-name标签的作用是告诉服务器，我当前配置的地址给哪个Servlet程序使用-->
        <servlet-name>HelloServlet</servlet-name>
        <!--
           url-pattern标签配置访问地址                             
           / 斜杠在服务器解析的时候，表示地址为：http://ip:port/工程路径
           /hello 表示地址为：http://ip:port/工程路径/hello 
        -->
        <url-pattern>/hello</url-pattern>
    </servlet-mapping>
```

### Servlet的生命周期

1. 执行`Servlet`构造器方法
2. 执行`init`初始化方法
    - 第一二步，是在第一次访问的时候创建`Servlet`程序会调用
3. 执行`service`方法
    - 第三步，每次访问都会调用
4. 执行`destroy`销毁方法
    - 第四步，在web工程停止的时候调用

- 通过继承`HttpServlet`实现`Servlet`程序
    1. 编写一个类去继承 `HttpServlet` 类
    2. 根据业务需要重写 `doGet()` 或 `doPost()` 方法
    3. 到 web.xml 中的配置`Servlet`程序的访问地址

- [HttpServlet源码分析](https://www.cnblogs.com/fxust/p/7944242.html)

## ServletConfig类

`ServletConfig` 类从类名上来看，就知道是 `Servlet` 程序的配置信息类。  
`Servlet` 程序和 `ServletConfig` 对象都是由 Tomcat 负责创建，我们负责使用。

Servlet 程序默认是第一次访问的时候创建，`ServletConfig`是每个 `Servlet` 程序创建时，就创建一个对应的 `ServletConfig` 对象。

`ServletConfig` 类的三大作用

1. 可以获取 `Servlet` 程序的别名 `servlet-name` 的值
2. 获取初始化参数 `init-param`
3. 获取 `ServletContext` 对象

```java
@Override
public void init(ServletConfig servletConfig) throws ServletException {
System.out.println("2 init 初始化方法");

// 1、可以获取 Servlet 程序的别名 servlet-name 的值
System.out.println("HelloServlet 程序的别名是:" + servletConfig.getServletName());

// 2、获取初始化参数 init-param
System.out.println("初始化参数 username 的值是;" + servletConfig.getInitParameter("username"));

System.out.println("初始化参数 url 的值是;" + servletConfig.getInitParameter("url"));

// 3、获取 ServletContext 对象

System.out.println(servletConfig.getServletContext());

}
```

重写`init`方法一定要调用父类的`init`方法

```java
    @Override
    public void init(ServletConfig config) throws ServletException {
        super.init(config);
        System.out.println("重写了init初始化方法,做了一些工作");
    }
```

`ServletConfig Servlet.getServletConfig()`

## ServletContext类

1. `ServletContext` 是一个接口，它表示 `Servlet` 上下文对象。
2. 一个 web 工程，只有一个 `ServletContext` 对象实例。
3. `ServletContext` 对象是一个域对象。
4. `ServletContext` 是在 web 工程部署启动的时候创建。在 web 工程停止的时候销毁。

什么是域对象?
域对象，是可以像 Map 一样存取数据的对象，叫**域对象**。
这里的域指的是存取数据的操作范围，整个 web 工程。

|  |存数据|取数据|删除数据|
|---|----|----|-------|
|Map|put()|get()|remove()|
|域对象|setAttribute()|getAttribute()|removeAttribute()|

- `ServeltContext`类的四个作用
    1. 获取 `web.xml`中配置的上下文参数 `context-param`
    2. 获取当前的工程路径，格式: `/工程路径`
    3. 获取工程部署后在服务器硬盘上的绝对路径
    4. 像 Map 一样存取数据
- `ServletConetx getServletContext()`

## HTTP协议

什么是**协议**?

- 协议是指双方，或多方，相互约定好，大家都需要遵守的规则，叫协议。
- 所谓 HTTP 协议，就是指，客户端和服务器之间通信时，发送的数据，需要遵守的规则，叫 HTTP 协议。
- HTTP 协议中的数据又叫报文。
  - 客户端给服务器发送数据叫**请求**。
  - 服务器给客户端回传数据叫**响应**。

## HTTP请求协议

- GET请求
    1. 请求行  
        1. 请求方式                   `GET`
        2. 请求资源路径               `[+?+请求参数]`
        3. 请求的协议版本号            `HTTP/1.1`
    2. 请求头
        1. key:value
- POST请求
    1. 请求行  
        1. 请求方式                     POST  
        2. 请求的资源路径               `[+?+请求参数]`
        3. 请求的协议的版本号            HTTP/1.1
    2. 请求头
        1. key:value
    3. 空行
    4. 请求体  就是发生给服务器的数据

- 常用请求头的说明
`Accept`: 表示客户端可以接收的数据类型
`Accpet-Languege`: 表示客户端可以接收的语言类型
`User-Agent`: 表示客户端浏览器的信息
`Host`：表示请求时的服务器 ip 和端口号

哪些是GET请求，哪些是POST请求（html中）  

- GET 请求有哪些：
    1. form 标签 `method=get`
    2. a 标签
    3. link 标签引入 css
    4. Script 标签引入 js 文件
    5. img 标签引入图片
    6. iframe 引入 html 页面
    7. 在浏览器地址栏中输入地址后敲回车
- POST 请求有哪些：
    1. form 标签 `method=post`

## HTTP响应协议

- 响应的HTTP协议
    1. 响应行
        1. 响应协议和版本号
        2. 响应状态码
        3. 响应状态描述符
    2. 响应头
        - key:value
    3. 空行
    4. 响应体  

- 常用响应码说明

| 响应码 | 说明                              |
| --- | ------------------------------- |
| 200 | 表示请求成功                          |
| 302 | 表示请求重定向                         |
| 404 | 表示请求服务器已经收到了，但是你要的数据不存在（请求地址错误） |
| 500 | 表示服务器已经收到请求，但是服务器内部错误（代码错误）     |

# Serverlet2

## HttpServletRequest

1. `HttpServletRequest`类的作用
    - 每次只要有请求进入 Tomcat 服务器，Tomcat 服务器就会把请求过来的 HTTP 协议信息解析好封装到`Request`对象中。然后传递到`service`方法（`doGet()`和`doPost()`）中给我们使用。我们可以通过`HttpServletRequest`对象，获取到所有请求的信息
2. `HttpServletRequest`类的常用方法
    1. `getRequestURI()`      获取请求的资源路径
    2. `getRequestURL()`      获取请求的统一资源定位符（绝对路径）
    3. `getRemoteHost()`      获取客户端的 ip 地址
    4. `String getHeader(String s)`         获取请求头
    5. `String gerParamerter(String s)`      获取请求的参数
    6. `String[] getParameterValues(String s)`  获取请求的参数（多个值的时候使用）
    7. `String getMethod()`          获取请求的方式 GET 或 POST
    8. `setAttribute()`       设置域数据
    9. `getAttribute()`       获取域数据
    10. `getRequestDispacher()`获取请求转发对象
3. 如何获取请求参数
    - 上述5和6  
4. `doGet`请求中的中文乱码
5. `doPost`请求中的中文乱码
6. 请求的转发
    - 请求转发是指，服务器收到请求后，从一次资源跳转到另一个资源的操作叫请求转发。
7. base标签的作用
8. web中的相对路径和绝对路径
9. web 中 / 斜杠的不同意义

请求转发

```java
RequestDispatcher requestDispatcher = req.getRequestDispatcher("/servlet2");
// 走向 Sevlet2（柜台 2）
requestDispatcher.forward(req,resp);
```

## HttpServletResponse

1. `HttpServletResponse` 类的作用
    - `HttpServletResponse` 类和 `HttpServletRequest` 类一样。每次请求进来，Tomcat 服务器都会创建一个 `Response` 对象传递给 `Servlet` 程序去使用。
    - `HttpServletRequest` 表示请求过来的信息，
    - `HttpServletResponse` 表示所有响应的信息，我们如果需要设置返回给客户端的信息，都可以通过 `HttpServletResponse` 对象来进行设置
2. 两个输出流的说明。  
    - `ServletOutputStream getOutputStream()` 常用于下载
    - `PrintWriter getWriter()`  常用于回传数据（常用）
    - **两个流同时只能使用一个**。使用了字节流，就不能再使用字符流，反之亦然，否则就会报错。
3. 如何往客户端回传数据

    ```java
    // 向客户端回传数据
        PrintWriter writer = resp.getWriter();
        writer.wrire("response's content");
    ```

4. 响应的乱码解决

    - 方案一  不推荐

    ```java
    // 设置服务器字符集为 UTF-8
    resp.setCharacterEncoding("UTF-8");
    // 通过响应头，设置浏览器也使用 UTF-8 字符集
    resp.setHeader("Content-Type", "text/html; charset=UTF-8");
    ```

    - 方案二  推荐

    ```java
    // 它会同时设置服务器和客户端都使用 UTF-8 字符集，还设置了响应头
    // 此方法一定要在获取流对象之前调用才有效
    resp.setContentType("text/html; charset=UTF-8");
    ```

5. 请求重定向

    - 第一种方案(不推荐)：

    ```java
    // 设置响应状态码 302 ，表示重定向，（已搬迁）
    resp.setStatus(302);
    // 设置响应头，说明 新的地址在哪里
    resp.setHeader("Location", "http://localhost:8080");
    ```

    - 第二种方案（推荐使用）：

    ```java
    resp.sendRedirect("http://localhost:8080");
    ```

# JSP

`JSP`的全称是`java server pages`。java的服务器页面。
JSP的主要作用是代替Servlet程序回传html页面的数据。
jsp本质是一个Servlet程序。
`HttpJspServlet`继承了`HttpServlet`类。
其底层实现，就是通过输出流，把 html 页面数据回传给客户端

## JSP的三种语法

jsp文件头部声明介绍
`<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>`
这是jsp文件的头声明。表示这是`jsp`页面。

- `language` 属性      值只能是 `java`。 表示翻译的得到的是` java `语言的
- `contentType`属性   设置响应头 `contentType` 的内容
- `pageEncoding`属性  设置当前 jsp 页面的编码
- `import` 属性       给当前` jsp `页面导入需要使用的类包
- `autoFlush` 属性    设置是否自动刷新 out 的缓冲区，默认为 true
- `buffer` 属性       设置 `out` 的缓冲区大小。默认为 8KB
- `errorPage` 属性    设置当前 jsp 发生错误后，需要跳转到哪个页面去显示错误信息
- `isErrorPage` 属性   设置当前 jsp 页面是否是错误页面。是的话，就可以使用 exception 异常对象
- `session` 属性     设置当前 `jsp` 页面是否获取 `session` 对象,默认为 `true`
- `extends` 属性     给服务器厂商预留的 `jsp` 默认翻译的 `servlet` 继承于什么类

jsp中的三种脚本介绍

1. 声明脚本（声明脚本）

    - `<%! java code %>`

    - 在声明脚本块中，我们可以干 4 件事情

    1. 我们可以定义全局变量。
    2. 定义 static 静态代码块
    3. 定义方法
    4. 定义内部类

    - 几乎可以写在类的内部写的代码，都可以通过声明脚本来实现

2. 表达式脚本(重点，常用)

    - `<%= expression here %>`

    - 表达式脚本 用于向页面输出内容。
    - 表达式脚本 翻译到 `Servlet` 程序的 `service` 方法中 以`out.print()`打印输出
    - `out` 是 jsp 的一个内置对象，用于生成 html 的源代码
    - 注意：表达式不要以分号结尾，否则会报错
    - 表达式脚本可以输出任意类型。

        1. 输出整型
        2. 输出浮点型
        3. 输出字符串
        4. 输出对象

3. 代码脚本(重点，常用)

    - `<% java code here %>`

    - 代码脚本里可以书写任意的 java 语句。
    - 代码脚本的内容都会被翻译到 `service` 方法中。
    - 所以 service 方法中可以写的 java 代码，都可以书写到代码脚本中

4. jsp中有三种注释：

    1. html注释

        - `<!--  html注释  -->`
        - html注释翻译之后会在_`jspService()`方法以`out.write`输出到页面

    2. java注释

        - `// 单行注释`
        - `/*  多行注释 */`
        - java的多行注释在翻译之后在翻译到servlet程序的源代码中

    3. jsp注释

        - `<%-- jsp注释 --%>`
        - jsp注释可以注掉jsp中所有内容，在jsp翻译的时候会被完全忽略掉

## jsp九大内置对象

| 对象            | 作用                                                      |
| ------------- | ------------------------------------------------------- |
| `request`     | 请求对象，可以获取请求信息                                           |
| `response`    | 响应对象。可以设置响应信息                                           |
| `pageContext` | 当前页面上下文对象。可以在当前上下文保存属性信息                                |
| `session`     | 会话对象。可以获取会话信息。                                          |
| `exception`   | 异常对象只有在 jsp 页面的 page 指令中设置 `isErrorPage="true"` 的时候才会存在 |
| `application` | `ServletContext` 对象实例，可以获取整个工程的一些信息。                    |
| `config`      | `ServletConfig` 对象实例，可以获取 `Servlet` 的配置信息               |
| `out`         | 输出流                                                     |
| `page`        | 表示当前 `Servlet` 对象实例（无用，用它不如使用 this 对象）。                 |

九大内置对象，都是我们可以在【代码脚本】中或【表达式脚本】中直接使用的对象。

## jsp四大域对象

| 对象|作用|
|-----| ----|
|`pageContex(PageContextImpl类)` |    当前jsp页面范围内有效|
|`request(HttpServletRequest类)`   |  一次请求内有效|
|`session(HttpSession类)` |           一次会话范围内有效（打开浏览器访问服务器，知道关闭浏览器）|
|`application(ServletContext类)` |    整个web工程范围内都有效（只要web工程不停止，数据都在）|

## JSP常用标签

- jsp 静态包含

```jsp
<%--
<%@ include file=""%> 就是静态包含
file 属性指定你要包含的 jsp 页面的路径
地址中第一个斜杠 / 表示为 http://ip:port/工程路径/ 映射到代码的 web 目录
静态包含的特点：
1、静态包含不会翻译被包含的 jsp 页面。
2、静态包含其实是把被包含的 jsp 页面的代码拷贝到包含的位置执行输出
--%>
<%@ include file="/include/footer.jsp"%>
```

- jsp动态包含

```jsp
<%--
<jsp:include page=""></jsp:include>
这是动态包含 page 属性是指定你要包含的 jsp 页面的路径
动态包含也可以像静态包含一样。把被包含的内容执行输出到包含位置
动态包含的特点：
1、动态包含会把包含的 jsp 页面也翻译成为 java 代码
2、动态包含底层代码使用如下代码去调用被包含的 jsp 页面执行输出。
JspRuntimeLibrary.include(request, response, "/include/footer.jsp", out, false);
3、动态包含，还可以传递参数
--%>
<jsp:include page="/include/footer.jsp">

<jsp:param name="username" value="bbj"/>

<jsp:param name="password" value="root"/>

</jsp:include>
```

jsp标签-转发

```jsp
<%--
<jsp:forward page=""></jsp:forward> 是请求转发标签，它的功能就是请求转发
page 属性设置请求转发的路径
--%>
<jsp:forward page="/scope2.jsp"></jsp:forward>
```

# Listener

1. `Listener` 监听器它是 JavaWeb 的三大组件之一。
    - JavaWeb 的三大组件分别是：**Servlet 程序**、 **Filter 过滤器**、 **Listener 监听器**。
2. `Listener` 它是 JavaEE 的规范，就是接口
3. 监听器的作用是，监听某种事物的变化。然后通过回调函数，反馈给客户（程序）去做一些相应的处理。
    - `ServletContextListener`它可以监听` ServletContext `对象的创建和销毁。
    - `ServletContext` 对象在 web 工程启动的时候创建，在 web 工程停止的时候销毁。

监听到创建和销毁之后都会分别调用 `ServletContextListener` 监听器的方法反馈。

```java

public interface ServletContextListener extends EventListener {
 /**
 * 在 ServletContext 对象创建之后马上调用，做初始化
 */
 public void contextInitialized(ServletContextEvent sce);
 
 /**
 * 在 ServletContext 对象销毁之后调用
 */
 public void contextDestroyed(ServletContextEvent sce);

}
```

如何使用 `ServletContextListener`监听器监听 `ServletContext`对象。 使用步骤如下：
1、 编写一个类去实现 `ServletContextListener`
2、 实现其两个回调方法
3、 到` web.xml `中去配置监听器

```java
public class MyServletContextListenerImpl implements ServletContextListener {

 @Override 
 public void contextInitialized(ServletContextEvent sce) { 
  System.out.println("ServletContext 对象被创建了");
 }
 
 @Override 
 public void contextDestroyed(ServletContextEvent sce) { 
  System.out.println("ServletContext 对象被销毁了"); 
 }
}
```

web.xml 配置

```xml
<!--配置监听器-->
<listener>
 <listener-class>com.atguigu.listener.MyServletContextListenerImpl</listener-class>
</listener>
```

# EL表达式 JSTL表达式

## EL表达式

EL 表达式主要是代替 JSP 页面中的表达式脚本在 JSP 页面中进行数据的输出。

因为 EL 表达式在输出数据的时候，要比 JSP 的表达式脚本要简洁很多。
格式：`${expression}`

### 常见用法示例

#### **输出作用域中的属性值**

假设在 JSP 页面中设置了属性：

```jsp
<%
request.setAttribute("username", "duke");
%>
```

使用 EL 表达式输出：

```jsp
${username}
```

#### **访问对象的属性**

假设有如下 JavaBean：

```java
public class User {
    private String name;
    private int age;
    // getter 和 setter
}
```

在 JSP 中：

```jsp
<%
User user = new User();
user.setName("Tom");
user.setAge(20);
request.setAttribute("user", user);
%>
```

EL 表达式访问属性：

```jsp
${user.name}   <!-- 输出 Tom -->
${user.age}    <!-- 输出 20 -->
```

#### **访问集合和数组**

```jsp
<%
String[] arr = {"A", "B", "C"};
request.setAttribute("arr", arr);
%>
${arr[0]}   <!-- 输出 A -->
```

#### **访问 Map**

```jsp
<%
Map<String, String> map = new HashMap<>();
map.put("city", "Beijing");
request.setAttribute("map", map);
%>
${map.city}   <!-- 输出 Beijing -->
```

#### **EL 表达式中的运算**

```jsp
<%
request.setAttribute("a", 5);
request.setAttribute("b", 3);
%>
${a + b}   <!-- 输出 8 -->
${a > b}   <!-- 输出 true -->
```

#### **空值处理和默认值**

```jsp
${empty username}         <!-- 判断 username 是否为空 -->
${username != null ? username : '匿名'}   <!-- EL 3.0 支持三元运算 -->
${username or '匿名'}     <!-- 输出 username，不存在则输出 '匿名' -->
```

> EL 表达式默认会从 page、request、session、application 四个作用域中查找变量。

## JSTL表达式

# Cookie and Session

`resp.addCookie()`

`request.getCookie()`

`cookie.setMacage()`    秒

```java

req.getSession().setAttribute("key1", "value1");

resp.getWriter().write("已经往 Session 中保存了数据");
```

# Filter

`Filter` 的生命周期包含几个方法

1. 构造器方法
2. ` init `初始化方法
    - 第 1，2 步，在 web 工程启动的时候执行（Filter 已经创建）
3. `doFilter` 过滤方法
    - 第 3 步，每次拦截到请求，就会执行
4. `destroy` 销毁
    - 第 4 步，停止 web 工程的时候，就会执行（停止 web 工程，也会销毁 Filter 过滤器）

`FilterConfig`类

`Filter`的拦截路径

- 精确匹配
- 目录匹配
- 后缀名匹配

# JSON 与 AJAX

前后端数据交互的接缝：前端侧的 JSON 用法（json 对象/字符串、`JSON.stringify()` / `JSON.parse()`）见 [[json]]；jQuery 发起 AJAX 请求的用法见 [[jquery]]。

AJAX 即 `Asynchronous JavaScript And XML`（异步 JavaScript 和 XML），是一种浏览器通过 js 异步发起请求、局部更新页面的技术。局部更新时浏览器地址栏不会发生变化，也不会舍弃原来页面的内容。

## JSON 在 Java 中的使用

使用 `gson.jar`。json 在 Java 中的操作常见的有三种情况：

1. Java 对象和 json 的转换
2. Java 对象 list 集合和 json 的转换
3. Map 对象和 json 的转换
