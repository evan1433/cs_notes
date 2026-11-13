---
title: Netty 核心原理与实战
description: 从 BIO 到主从 Reactor 讲清 Netty 线程模型，拆解 EventLoop、ChannelPipeline、ByteBuf 三大核心，含可运行的 Echo/HTTP 示例、粘包拆包与自定义协议、心跳/背压/优雅停机实践，以及与 Tomcat 的定位差异
tags:
  - netty
  - nio
  - network-programming
  - concurrency
  - java
  - backend
date: 2026-11-13
---

# Netty 核心原理与实战

## 概述

Netty 是一个**异步事件驱动的网络应用框架**，用它对 TCP/UDP 做编程，相当于把 JDK NIO 那套又长又坑的
`Selector` + `Channel` + `ByteBuffer` 手工循环，换成了"声明式装配 Handler"的写法。它解决的不是"能不能通信"，
而是"高并发下能不能稳定、可维护地通信"。

原生 NIO 的四个现实痛点：

| 痛点 | 具体表现 | Netty 的解法 |
| --- | --- | --- |
| API 复杂 | 需要自己管理 Selector 注册、就绪事件分发、缓冲区读写指针 | `Bootstrap` + `ChannelPipeline` 装配式编程 |
| 粘包/拆包 | TCP 是字节流，业务层收到的不是"一条消息" | 内置十余种 `ByteToMessageDecoder` |
| 半包与不完整请求 | 一次 read 可能只拿到半个请求体 | 累积缓冲区 + 解码器状态机 |
| 已知缺陷 | epoll 空轮询导致 CPU 100%、JDK NIO 的部分平台差异 | 空轮询检测重建 Selector、统一的 `EventLoop` 抽象 |

它也是很多中间件的底座：Dubbo、RocketMQ、Elasticsearch、gRPC-Java、Spring WebFlux 的 Reactor Netty、
Redis 客户端 Lettuce 等，网络层基本都是 Netty。

### 版本现状

截至 2026 年 11 月，Netty 官方下载页给出的版本状态：

| 版本 | 状态 | 说明 |
| --- | --- | --- |
| `4.2.20.Final` | Stable（推荐） | 当前主线，引入通用 `IoHandler` 抽象与新版 EventLoop API |
| `4.1.140.Final` | Stable | 长期维护分支，存量项目大多在此 |
| `5.0.0.Alpha5` | Development | 2022 年 9 月后未再发布，**不要用于生产** |

> JDK 要求：Netty 4.x 官方口径是 JDK 6+（实际项目普遍运行在 8/11/17 上），Netty 5 需要 JDK 11+。

Maven 依赖（`netty-all` 是聚合包；生产环境更推荐按需引入 `netty-transport`、`netty-codec-http` 等子模块，
避免把不用的编解码器打进包）：

```xml
<dependency>
    <groupId>io.netty</groupId>
    <artifactId>netty-all</artifactId>
    <version>4.2.20.Final</version>
</dependency>
```

> 版本差异要点：4.2 把 `NioEventLoopGroup` 标记为 `@Deprecated`，官方推荐改用
> `new MultiThreadIoEventLoopGroup(NioIoHandler.newFactory())`。4.1 的旧写法仍可编译运行，
> 存量项目不必急着改，新代码建议直接用新 API（见第 4 节的写法对比）。

## 1. 从 BIO 到主从 Reactor

### 1.1 为什么不能一个连接一个线程

BIO 模型下 `accept()` 后把连接丢给线程池，每个连接独占一个线程阻塞在 `read()`：

```java
// BIO：连接数上限 = 线程池大小，1000 个空闲长连接就吃掉 1000 个线程
try (ServerSocket server = new ServerSocket(9000)) {
    ExecutorService pool = Executors.newFixedThreadPool(200);
    while (true) {
        Socket socket = server.accept();          // 阻塞点 1
        pool.submit(() -> handle(socket));        // handle 内部 read() 是阻塞点 2
    }
}
```

一台机器开几千个线程后，线程栈内存、上下文切换、GC 扫描成本一起爆炸。更致命的是：这些线程 99% 的时间在等
数据，属于纯浪费。

### 1.2 Reactor 三种形态

Reactor 模式把"等待就绪"和"处理事件"拆开，由少量 selector 线程负责等待，事件就绪后分发给业务处理。

| 形态 | 结构 | 优点 | 缺点 |
| --- | --- | --- | --- |
| 单 Reactor 单线程 | 1 个线程做 accept + read + 业务 | 模型最简单，无并发问题 | 一个慢业务阻塞全部连接，无法利用多核 |
| 单 Reactor 多线程 | 1 个线程 accept/read，业务丢线程池 | 业务不阻塞 IO | Reactor 仍是单点，海量连接下 accept 成瓶颈 |
| 主从 Reactor 多线程 | 主 Reactor 只 accept，从 Reactor 组负责读写，业务再下沉 | 连接接入与 IO 分离，横向扩展 | 结构复杂，Netty 帮你封装掉了 |

**Netty 采用主从 Reactor 多线程模型**：`bossGroup`（主 Reactor，通常 1 个线程）负责 `accept`，
`workerGroup`（从 Reactor，默认 `2 × CPU` 个线程）负责已建立连接的读写事件。

## 2. 核心组件全景

```text
ServerBootstrap
 ├── EventLoopGroup(boss)   ── 接受连接
 ├── EventLoopGroup(worker) ── 处理读写
 └── Channel(NioServerSocketChannel)
       └── ChannelPipeline（每个连接各一份）
            ├── ChannelHandler 1   （解码）
            ├── ChannelHandler 2   （业务）
            └── ChannelHandler 3   （编码）
```

| 组件 | 定位 | 关键点 |
| --- | --- | --- |
| `Bootstrap` / `ServerBootstrap` | 客户端 / 服务端启动器 | 链式配置 group、channel、option、handler |
| `EventLoopGroup` | 线程组 | 一组 `EventLoop`，内部含 Selector 与任务队列 |
| `EventLoop` | 单线程事件循环 | 一个 Channel 终生只绑定一个 EventLoop |
| `Channel` | 网络连接的抽象 | 所有 IO 操作都是异步的，返回 `ChannelFuture` |
| `ChannelPipeline` | Handler 责任链容器 | 入站/出站两条方向，顺序敏感 |
| `ChannelHandler` | 编解码与业务逻辑载体 | 分 `ChannelInboundHandler` / `ChannelOutboundHandler` |
| `ChannelHandlerContext` | Handler 与 Pipeline 的连接点 | 决定事件从哪个 Handler 继续传播 |
| `ByteBuf` | 字节容器 | 读写双指针、引用计数、池化 |
| `ChannelFuture` / `Promise` | 异步结果 | `sync()` 阻塞等待，`addListener()` 回调 |

### 2.1 Pipeline 的入站与出站

同一个 Pipeline 里，**入站事件（读）从头到尾传播，出站事件（写）从尾到头传播**。这是新手最容易写错方向的地方：
把编码器放在业务 Handler 前面，写出去的数据就永远不会被编码。

```text
入站：Head → Decoder → Business → Tail
出站：Tail → Business → Encoder → Head
```

### 2.2 Handler 是否线程安全

`@ChannelHandler.Sharable` 标记的 Handler 可以被多个连接共享（必须无状态）；没标记的，每个 `Channel` 都会
`new` 一份，天然隔离。**给有状态 Handler 加 `@Sharable` 是 Netty 里最经典的并发 Bug**。

## 3. ByteBuf：为什么不用 ByteBuffer

| 对比项 | JDK `ByteBuffer` | Netty `ByteBuf` |
| --- | --- | --- |
| 读写模式切换 | 每次读写要 `flip()` / `rewind()` | 读指针、写指针分离，无需切换 |
| 容量扩展 | 固定，满了要自己新建并拷贝 | `capacity` 按需扩容至 `maxCapacity` |
| 池化 | 无 | `PooledByteBufAllocator` 复用内存，降低 GC 压力 |
| 引用计数 | 无（靠 GC） | 有，跨 Handler 传递需 `retain()` / `release()` |
| 组合 | 需要自己拼 | `CompositeByteBuf` 逻辑拼接不拷贝 |

```java
ByteBuf buf = Unpooled.buffer(16, 64);
buf.writeInt(0xCAFE);              // 写指针后移 4
buf.writeBytes("hello".getBytes(StandardCharsets.UTF_8));
System.out.println(buf.readableBytes());   // 9：写指针 - 读指针
int magic = buf.readInt();                 // 读指针后移 4
System.out.println(Integer.toHexString(magic)); // cafe
```

### 3.1 Netty 的"零拷贝"到底指什么

这个词在 Netty 语境里有四层含义，面试常被追问，容易答串：

| 层次 | 手段 | 省掉的是什么 |
| --- | --- | --- |
| 内存层 | 直接内存 `DirectByteBuf` | JVM 堆 → 内核缓冲区的那次拷贝 |
| 组合层 | `CompositeByteBuf` | 多个 ByteBuf 合并成一个大数组的拷贝 |
| 视图层 | `slice()` / `duplicate()` | 复制底层字节数组 |
| 传输层 | `FileRegion` / `transferTo` | 用户态与内核态之间的数据往返（sendfile） |

## 4. 线程模型与 EventLoop

`EventLoop` 本质上是一个"永远在跑的死循环"：

```text
for (;;) {
    select()              // 等待 IO 事件（带超时，避免空轮询）
    处理就绪的 IO 事件      // read / write / accept
    执行任务队列            // 普通任务 + 定时任务
}
```

三个必须记住的结论：

1. **一个 Channel 终生只注册在一个 EventLoop 上**，因此单连接内的所有事件天然串行，Handler 无需加锁。
2. **绝不能在 EventLoop 线程里做阻塞操作**（数据库查询、同步 RPC、`Thread.sleep`）。它会拖住该线程上
   所有连接的 IO。阻塞业务要下沉到独立线程池（见 4.2）。
3. `EventLoopGroup` 默认线程数是 `2 × CPU 核数`。IO 密集可维持默认；如果 Handler 里有轻量计算，
   适当调大；如果业务已下沉到业务线程池，`worker` 线程数不必设很大，8~16 核机器上 8～16 个通常足够。

### 4.1 4.2 的 EventLoopGroup 写法

Netty 4.2 抽象出通用的 `IoHandler`，让同一个 `MultiThreadIoEventLoopGroup` 可以承载 NIO、epoll、kqueue、
io_uring 等不同实现：

```java
import io.netty.channel.EventLoopGroup;
import io.netty.channel.MultiThreadIoEventLoopGroup;
import io.netty.channel.nio.NioIoHandler;

// 4.2 推荐写法：通用线程组 + NIO 的 IoHandler 工厂
EventLoopGroup boss   = new MultiThreadIoEventLoopGroup(1, NioIoHandler.newFactory());
EventLoopGroup worker = new MultiThreadIoEventLoopGroup(NioIoHandler.newFactory());

// 4.1 及以前的写法（4.2 中已标记 @Deprecated，但仍可用）
// EventLoopGroup boss   = new NioEventLoopGroup(1);
// EventLoopGroup worker = new NioEventLoopGroup();
```

4.2 还提供了 `AutoScalingEventExecutorChooserFactory`，可让线程组按实际利用率自动扩缩容（构造
`MultiThreadIoEventLoopGroup` 时传入该 chooser），适合流量波峰波谷差异大的场景。

### 4.2 把阻塞业务挪出 EventLoop

```java
import io.netty.channel.ChannelInitializer;
import io.netty.channel.socket.SocketChannel;
import io.netty.util.concurrent.DefaultEventExecutorGroup;
import io.netty.util.concurrent.EventExecutorGroup;

EventExecutorGroup businessGroup = new DefaultEventExecutorGroup(32);

new ChannelInitializer<SocketChannel>() {
    @Override
    protected void initChannel(SocketChannel ch) {
        ch.pipeline()
          // 指定 executorGroup：该 Handler 的回调改由业务线程池执行
          .addLast(businessGroup, new BlockingBusinessHandler());
    }
};
```

等价做法是在 Handler 内部把任务提交到自己的 Spring 线程池。区别在于：用 `addLast(group, handler)`
能保证**同一个 Channel 的业务回调仍按顺序执行**，而随手丢进公共线程池可能乱序。

## 5. 可运行的 Echo 服务端

### 5.1 服务端

```java
import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.MultiThreadIoEventLoopGroup;
import io.netty.channel.nio.NioIoHandler;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.string.StringDecoder;
import io.netty.handler.codec.string.StringEncoder;

public class EchoServer {

    private static final int PORT = 9000;

    public static void main(String[] args) throws InterruptedException {
        EventLoopGroup boss = new MultiThreadIoEventLoopGroup(1, NioIoHandler.newFactory());
        EventLoopGroup worker = new MultiThreadIoEventLoopGroup(NioIoHandler.newFactory());
        try {
            ServerBootstrap bootstrap = new ServerBootstrap();
            bootstrap.group(boss, worker)
                    .channel(NioServerSocketChannel.class)
                    // 服务端连接队列长度：高并发接入时适当放大，减少 accept 丢失
                    .option(ChannelOption.SO_BACKLOG, 1024)
                    // 小包场景关闭 Nagle，降低延迟；大吞吐场景可保持默认开启
                    .childOption(ChannelOption.TCP_NODELAY, true)
                    .childHandler(new ChannelInitializer<SocketChannel>() {
                        @Override
                        protected void initChannel(SocketChannel ch) {
                            ch.pipeline()
                              .addLast(new StringDecoder())
                              .addLast(new StringEncoder())
                              .addLast(new EchoHandler());
                        }
                    });
            ChannelFuture future = bootstrap.bind(PORT).sync();
            System.out.println("echo server listening on " + PORT);
            // 阻塞直到 Channel 关闭，避免 main 线程退出
            future.channel().closeFuture().sync();
        } finally {
            boss.shutdownGracefully();
            worker.shutdownGracefully();
        }
    }
}
```

```java
import io.netty.channel.ChannelHandler;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.SimpleChannelInboundHandler;

// 无状态，可被所有连接共享
@ChannelHandler.Sharable
public class EchoHandler extends SimpleChannelInboundHandler<String> {

    @Override
    public void channelActive(ChannelHandlerContext ctx) {
        System.out.println("new connection: " + ctx.channel().remoteAddress());
    }

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, String msg) {
        ctx.writeAndFlush("echo: " + msg);
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
        // 不处理异常会导致连接泄漏：这里记录并关闭该连接
        cause.printStackTrace();
        ctx.close();
    }
}
```

用 `nc` 验证：

```bash
# 终端 1：启动服务端后，终端 2 连上去发消息
printf 'hello\n' | nc 127.0.0.1 9000
# 输出：echo: hello
```

### 5.2 客户端（含断线重连）

```java
import io.netty.bootstrap.Bootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelFutureListener;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.MultiThreadIoEventLoopGroup;
import io.netty.channel.nio.NioIoHandler;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioSocketChannel;
import io.netty.handler.codec.string.StringDecoder;
import io.netty.handler.codec.string.StringEncoder;
import java.util.concurrent.TimeUnit;

public class EchoClient {

    private final EventLoopGroup group =
            new MultiThreadIoEventLoopGroup(NioIoHandler.newFactory());
    private final String host;
    private final int port;
    private Bootstrap bootstrap;
    private volatile Channel channel;

    public EchoClient(String host, int port) {
        this.host = host;
        this.port = port;
    }

    public void start() {
        bootstrap = new Bootstrap();
        bootstrap.group(group)
                .channel(NioSocketChannel.class)
                .handler(new ChannelInitializer<SocketChannel>() {
                    @Override
                    protected void initChannel(SocketChannel ch) {
                        ch.pipeline()
                          .addLast(new StringDecoder())
                          .addLast(new StringEncoder());
                    }
                });
        connect();
    }

    private void connect() {
        bootstrap.connect(host, port).addListener((ChannelFutureListener) future -> {
            if (future.isSuccess()) {
                this.channel = future.channel();
                System.out.println("connected to " + host + ":" + port);
                // 连接断开时触发重连（对端重启、网络抖动都会走到这里）
                future.channel().closeFuture().addListener(f -> scheduleReconnect());
            } else {
                System.err.println("connect failed: " + future.cause().getMessage());
                scheduleReconnect();
            }
        });
    }

    private void scheduleReconnect() {
        // 重连必须延后，不能在 EventLoop 线程里 sleep，否则整组连接的事件都被卡住
        group.schedule(this::connect, 3, TimeUnit.SECONDS);
    }

    public static void main(String[] args) {
        new EchoClient("127.0.0.1", 9000).start();
    }
}
```

> 生产环境的重连要加退避（3s → 6s → 12s，上限 60s）与重试上限，否则下游宕机时会变成自我 DDoS。

### 5.3 HTTP 服务端

```java
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.SimpleChannelInboundHandler;
import io.netty.channel.socket.SocketChannel;
import io.netty.handler.codec.http.DefaultFullHttpResponse;
import io.netty.handler.codec.http.FullHttpRequest;
import io.netty.handler.codec.http.FullHttpResponse;
import io.netty.handler.codec.http.HttpHeaderNames;
import io.netty.handler.codec.http.HttpObjectAggregator;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.netty.handler.codec.http.HttpServerCodec;
import io.netty.handler.codec.http.HttpVersion;
import java.nio.charset.StandardCharsets;

// 放进上面的 bootstrap.childHandler(...) 即可
public class HttpPipeline extends ChannelInitializer<SocketChannel> {

    @Override
    protected void initChannel(SocketChannel ch) {
        ch.pipeline()
          // HTTP 编解码：把字节流拆成 HttpRequest / HttpResponse
          .addLast(new HttpServerCodec())
          // 把分片的请求体聚合成一个 FullHttpRequest，上限 64KB
          .addLast(new HttpObjectAggregator(64 * 1024))
          .addLast(new SimpleChannelInboundHandler<FullHttpRequest>() {
              @Override
              protected void channelRead0(ChannelHandlerContext ctx, FullHttpRequest req) {
                  ByteBuf body = Unpooled.copiedBuffer("hello netty", StandardCharsets.UTF_8);
                  FullHttpResponse resp = new DefaultFullHttpResponse(
                          HttpVersion.HTTP_1_1, HttpResponseStatus.OK, body);
                  resp.headers().set(HttpHeaderNames.CONTENT_TYPE, "text/plain;charset=UTF-8");
                  // Content-Length 必须与 body 实际长度一致，否则客户端会一直等
                  resp.headers().setInt(HttpHeaderNames.CONTENT_LENGTH, body.readableBytes());
                  ctx.writeAndFlush(resp);
              }
          });
    }
}
```

`HttpServerCodec` 是 `HttpRequestDecoder` + `HttpResponseEncoder` 的组合。**不加 `HttpObjectAggregator`
时你拿到的可能是半个请求**，这是自建 HTTP 服务最常见的坑。

## 6. 粘包与拆包

TCP 是面向字节流的协议，没有"消息边界"概念。客户端连发 `"AAA"`、`"BBB"`，服务端可能读到 `"AAABBB"`（粘包），
也可能分两次读到 `"AA"`、`"ABBB"`（拆包）。这是 TCP 的固有特性，不是 Netty 的 Bug。

三种业界通用解法：

| 方案 | 编码成本 | 适用场景 | Netty 解码器 |
| --- | --- | --- | --- |
| 固定长度 | 低 | 报文长度恒定的私有协议 | `FixedLengthFrameDecoder` |
| 特殊分隔符 | 低 | 文本协议（如 Redis 命令、日志流） | `DelimiterBasedFrameDecoder` / `LineBasedFrameDecoder` |
| 长度字段 | 中 | 二进制 RPC 协议的主流做法 | `LengthFieldBasedFrameDecoder` |

### 6.1 LengthFieldBasedFrameDecoder 的五个参数

这是最容易配错的一个类，五个参数的含义可以用一条公式串起来：

```text
帧总长 = 长度字段的值 + lengthFieldOffset + lengthFieldLength + lengthAdjustment
```

| 参数 | 含义 | 说明 |
| --- | --- | --- |
| `maxFrameLength` | 单帧最大字节数 | 超过直接抛 `TooLongFrameException`，是防攻击的一道闸 |
| `lengthFieldOffset` | 长度字段距帧头的偏移 | 前面有魔数、版本号时要算进去 |
| `lengthFieldLength` | 长度字段自身占几字节 | 常见 2（`short`）或 4（`int`） |
| `lengthAdjustment` | 长度值与"剩余字节数"的差值修正 | 长度只含 body 时填 0；长度含头部时填负数 |
| `initialBytesToStrip` | 解码成功后丢弃的前导字节数 | 想让业务 Handler 看到完整头部就填 0 |

### 6.2 一个自定义协议的完整示例

协议格式（头部固定 8 字节）：

```text
+--------+---------+-------+----------+--------------+
| magic  | version | type  | length   | body         |
| 2 byte | 1 byte  | 1byte | 4 byte   | length bytes |
+--------+---------+-------+----------+--------------+
```

```java
import io.netty.handler.codec.LengthFieldBasedFrameDecoder;

// 帧总长 = body 长度 + 4(offset) + 4(length 自身) + 0 = body + 8，与协议一致
public class MyProtocolDecoder extends LengthFieldBasedFrameDecoder {

    public MyProtocolDecoder() {
        super(
                1024 * 1024,  // maxFrameLength：单帧上限 1MB
                4,            // lengthFieldOffset：magic(2) + version(1) + type(1)
                4,            // lengthFieldLength：length 字段 4 字节
                0,            // lengthAdjustment：length 只统计 body，无需修正
                0             // initialBytesToStrip：保留完整头部，交给业务解析
        );
    }
}
```

装配顺序（顺序错了协议永远解析不对）：

```java
ch.pipeline()
  .addLast(new MyProtocolDecoder())        // 先把字节流切成完整帧
  .addLast(new MyMessageDecoder())         // 再把帧解析成 POJO（继承 ByteToMessageDecoder）
  .addLast(new MyBusinessHandler());       // 业务只处理 POJO
```

### 6.3 三类解码器的区别

| 基类 / 接口 | 输入 → 输出 | 是否需要手动释放入参 |
| --- | --- | --- |
| `ByteToMessageDecoder` | `ByteBuf` → 任意对象 | 否，父类自动释放已消费部分 |
| `MessageToMessageDecoder<I>` | 对象 → 对象 | 否，父类自动 `release` 入参 |
| `SimpleChannelInboundHandler<I>` | 对象 → 无（终点） | 否，自动释放；**若要把消息往后传或异步持有，必须 `retain()`** |

`SimpleChannelInboundHandler` 的自动释放是把双刃剑：把 `msg` 存进队列稍后处理，必须 `ReferenceCountUtil.retain(msg)`，
否则会看到 `IllegalReferenceCountException: refCnt: 0`。

## 7. 可靠性机制

### 7.1 心跳与空闲检测

```java
import io.netty.handler.timeout.IdleStateHandler;
import java.util.concurrent.TimeUnit;

ch.pipeline()
  // 30 秒没读到数据 → 触发 READER_IDLE 事件
  .addLast(new IdleStateHandler(30, 0, 0, TimeUnit.SECONDS))
  .addLast(new HeartbeatHandler());
```

```java
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import io.netty.handler.timeout.IdleStateEvent;

public class HeartbeatHandler extends ChannelInboundHandlerAdapter {

    @Override
    public void userEventTriggered(ChannelHandlerContext ctx, Object evt) throws Exception {
        if (evt instanceof IdleStateEvent event) {
            switch (event.state()) {
                case READER_IDLE -> {
                    // 长时间收不到对端数据，判定连接已死（半开连接靠这个清理）
                    System.out.println("reader idle, closing " + ctx.channel().remoteAddress());
                    ctx.close();
                }
                case WRITER_IDLE -> ctx.writeAndFlush("PING\n");
                default -> { }
            }
            return;
        }
        super.userEventTriggered(ctx, evt);
    }
}
```

心跳的作用是**探测半开连接**：对端进程被 kill、网线被拔时，本地 TCP 状态可能仍停留在 ESTABLISHED，
只有靠应用层心跳或 TCP KeepAlive 才能发现。移动网络场景建议应用层心跳 + 服务端双向检测。

### 7.2 背压：写不出去的时候怎么办

Netty 的写操作是异步的：`writeAndFlush` 只是把数据放进 ChannelOutboundBuffer 就返回。下游消费慢、上游猛发，
缓冲区会无限膨胀直至 OOM。Netty 用"高低水位"提供反馈：

```java
import io.netty.channel.ChannelOption;
import io.netty.channel.WriteBufferWaterMark;

// 32KB 以下可写，64KB 以上不可写（默认值即 32KB / 64KB）
bootstrap.childOption(ChannelOption.WRITE_BUFFER_WATER_MARK,
        new WriteBufferWaterMark(32 * 1024, 64 * 1024));
```

```java
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;

public class BackpressureHandler extends ChannelInboundHandlerAdapter {

    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) {
        if (!ctx.channel().isWritable()) {
            // 不可写：停止读取，把压力反推给上游（需要先关闭 autoRead）
            ctx.channel().config().setAutoRead(false);
            return;
        }
        ctx.write(msg);
    }

    @Override
    public void channelWritabilityChanged(ChannelHandlerContext ctx) {
        if (ctx.channel().isWritable()) {
            ctx.channel().config().setAutoRead(true);   // 缓冲区排空，恢复读取
        }
        ctx.fireChannelWritabilityChanged();
    }
}
```

`isWritable() == false` 时继续 `write` 不会报错，只会把内存越吃越多——**这是线上内存缓慢增长的常见根因之一**。

### 7.3 优雅停机

```java
// 关闭时不要用 shutdownNow()，直接 shutdownGracefully 让在途请求跑完
boss.shutdownGracefully(0, 5, TimeUnit.SECONDS).sync();
worker.shutdownGracefully(0, 5, TimeUnit.SECONDS).sync();
```

`shutdownGracefully(quietPeriod, timeout, unit)`：先静默 `quietPeriod`（等待新任务停止提交），
再最多等 `timeout` 让在途任务结束。K8s 滚动发布时，先摘流量再停机，能避免一批 502。

### 7.4 内存泄漏排查

Netty 的 ByteBuf 走引用计数，忘记 `release()` 就是内存泄漏。默认检测级别是 `SIMPLE`（抽样），
排查期可以调到 `PARANOID`：

```bash
# 启动参数方式；也可在代码里 ResourceLeakDetector.setLevel(Level.PARANOID)
java -Dio.netty.leakDetection.level=paranoid -jar app.jar
```

```text
LEAK: ByteBuf.release() was not called before it's garbage-collected.
Recent access records: ... Created at: io.netty.buffer.PooledByteBufAllocator.newDirectBuffer(...)
```

看到这段日志，按 `Created at` 的堆栈找到创建点，检查是否跨线程传递后漏了 `retain` / `release`。
**`PARANOID` 只用于排查，线上常开会带来明显性能损耗。**

## 8. Netty 与 Tomcat 的定位差异

两者经常被放在一起问，但压根不是竞品：Tomcat 是 **Servlet 容器**（跑应用），Netty 是 **网络编程框架**
（写协议）。Spring WebFlux 用的 Reactor Netty 就是"Netty + 响应式适配"，正好说明二者是不同层的东西。

| 维度 | Tomcat | Netty |
| --- | --- | --- |
| 抽象层次 | 实现 Servlet 规范，提供 `HttpServletRequest` | 提供 Channel/Handler 原语，HTTP 只是内置编解码器之一 |
| 对外协议 | HTTP/1.1、HTTP/2、AJP、WebSocket | 任意 TCP/UDP 私有协议，HTTP/gRPC/自定义 |
| 编程模型 | 一请求一线程（阻塞），也可挂异步 Servlet | 全异步事件驱动，回调/`Future`/`Promise` |
| 线程模型 | Acceptor + Poller + 工作线程池 | 主从 Reactor，一个 Channel 绑定一个 EventLoop |
| 上手成本 | 低，写好 Controller 就跑 | 高，需自己设计协议、编解码、连接管理 |
| 典型场景 | 业务 Web 应用、Spring Boot 默认容器 | 网关、RPC 框架、IM/推送、消息中间件、代理 |
| 类比 | 现成的"应用服务器" | 造服务器的"积木" |

选型判断很简单：

- 业务是标准 HTTP 的增删改查 → **Tomcat**（Spring MVC / Spring Boot），不要重复造轮子
- 需要长连接、自定义二进制协议、超高连接数（十万级）→ **Netty**
- 想要非阻塞的 HTTP 服务又不想写协议 → **Spring WebFlux（底层 Reactor Netty）**

Tomcat 的连接器、容器层级与启动流程见 [[tomcat-jetty|Tomcat 与 Jetty 架构深度解析]]；Servlet 规范本身见
[[java-web|Java Web 开发]]。

## 9. 常见排错

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `IllegalReferenceCountException: refCnt: 0` | 消息已被自动释放后又使用，或跨线程未 `retain` | 异步持有前 `retain()`，用完 `release()` |
| 业务偶发卡顿、心跳超时成片出现 | Handler 里做了阻塞调用，拖死 EventLoop | 用 `addLast(executorGroup, handler)` 或提交业务线程池 |
| 内存持续增长不回落 | 对端不读导致 `ChannelOutboundBuffer` 堆积；或 ByteBuf 泄漏 | 打开 `paranoid` 检测；用 `isWritable()` 做背压 |
| 服务端收到的消息"合在一起"或"断成两截" | 没做粘包拆包处理 | 装配 `LengthFieldBasedFrameDecoder` 等解码器 |
| HTTP 请求 body 读不全 | 未加 `HttpObjectAggregator`，拿到的是分片 | 加 `HttpObjectAggregator(maxContentLength)` |
| 连接数上万后 CPU 打满但 QPS 很低 | `SO_BACKLOG` 太小导致 accept 排队；或 epoll 空轮询 | 调大 backlog；升级到含空轮询修复的版本 |
| `TooLongFrameException` | 长度字段解析错位，把脏数据读成超大长度 | 核对 `lengthFieldOffset` / `lengthAdjustment` 与协议是否一致 |
| 停机时大量请求 502 | 直接 `shutdownNow()`，在途请求被切断 | 先摘流量，再 `shutdownGracefully` |
| 客户端连接数暴涨后服务端 FD 耗尽 | 半开连接未清理 | 加 `IdleStateHandler` 心跳 + 调低 `ulimit -n` 相关配置 |

## 10. 生产落地清单

- [ ] 协议有明确边界：魔数 + 版本 + 长度字段，长度字段设上限
- [ ] 所有解码器、Handler 的装配顺序与注释一起写清楚
- [ ] 阻塞逻辑全部下沉到业务线程池，EventLoop 里只做内存操作
- [ ] 心跳（`IdleStateHandler`）双向配置，半开连接能被清理
- [ ] 写侧有背压（`isWritable` / 高低水位），不无限堆缓冲
- [ ] 客户端重连带指数退避与重试上限
- [ ] 停机走 `shutdownGracefully`，配合 K8s 摘流量
- [ ] 压测关注：连接数、`ChannelOutboundBuffer` 水位、直接内存（`-XX:MaxDirectMemorySize`）、GC
- [ ] 直接内存要显式限制，否则 `OutOfMemoryError: Direct buffer memory` 比堆 OOM 更难定位

## See Also

- [[tomcat-jetty|Tomcat 与 Jetty 架构深度解析]] —— 连接器/容器分层、Pipeline-Valve、启动流程
- [[java-web|Java Web 开发]] —— Servlet 规范、Filter/Listener、Cookie/Session
- [[java-thread-pool|Java 线程池]] —— 线程池参数与业务线程池隔离思路
- [[jvm|JVM 虚拟机核心原理]] —— 直接内存、GC 与内存泄漏排查
- [[project-reactor|Project Reactor]] —— 响应式编程模型，WebFlux 的上层抽象
- [[microservices|微服务架构]] —— 网关、RPC 在微服务体系中的位置
- [[02-backend/web-servers/index|Web 服务器目录]]

## 参考

- [Netty 官网](https://netty.io/)
- [Netty 下载与版本状态](https://netty.io/downloads.html)
- [Netty 4.2 API 文档](https://netty.io/4.2/api/index.html)
- [Netty 官方示例（GitHub）](https://github.com/netty/netty/tree/4.2/example)
- [Apache Tomcat 版本对照](https://tomcat.apache.org/whichversion.html)
