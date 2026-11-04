---
title: JVM 虚拟机核心原理
description: JVM 内存模型、类加载机制、垃圾回收算法与收集器、JIT 编译及常用调优与排错实践
tags:
  - java
  - jvm
  - garbage-collection
  - memory-management
date: 2026-11-04
---

# JVM 虚拟机核心原理

## 概述

JVM（Java Virtual Machine）是 Java "一次编写、到处运行" 的基石：它把 `.class` 字节码翻译成对应平台的机器指令，并接管内存分配与回收。理解 JVM 的价值在于——生产环境中的 OutOfMemoryError、长时间 Full GC 导致的接口超时、类加载冲突（`NoSuchMethodError`）这类问题，只有从 JVM 层面才能定位根因，业务代码层面往往毫无线索。

## 前置知识

- [[java-se|Java SE 核心语法]]：需要熟悉对象、引用、继承的基本概念
- [[操作系统|操作系统基础]]：了解进程内存布局（堆、栈、虚拟内存）有助于对比理解
- [[java-multithreading|Java 多线程基础]]：GC 行为与线程私有区域密切相关

## 整体架构

JVM 可以粗略分为三块，各自独立又相互协作：

```
┌─────────────────────────────────────────────┐
│              Class Loader 子系统              │
│   加载 → 验证 → 准备 → 解析 → 初始化          │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│              运行时数据区                     │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ 方法区/元空间 │ │    堆    │  │ 虚拟机栈(线程私有) │  │
│  └──────────┘ └──────────┘  └─────────────┘  │
│  ┌──────────┐ ┌──────────┐                   │
│  │ 本地方法栈 │ │  程序计数器 │                  │
│  └──────────┘ └──────────┘                   │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│           执行引擎（解释器 + JIT）             │
│        本地方法接口 (JNI) / 本地方法库         │
└─────────────────────────────────────────────┘
```

- **类加载子系统**：负责把字节码装载进内存并校验合法性
- **运行时数据区**：JVM 管理的内存，GC 主战场是堆
- **执行引擎**：解释执行字节码 + 热点代码即时编译成本地机器码

## 类加载机制

### 为什么需要类加载

Java 是动态链接的语言：类之间在编译期只记录符号引用（如 `com/example/OrderService.create`），真正解析成内存地址发生在运行时类加载阶段。这带来了灵活性的同时也埋了坑——编译期通过不代表运行期能找到正确的类版本。

### 加载的五个阶段

| 阶段 | 做什么 | 关键点 |
|------|--------|--------|
| 加载 | 读取字节流，生成 `Class` 对象 | 可来自文件、网络、动态代理生成 |
| 验证 | 校验字节码合法性 | 防止恶意构造的字节码破坏 JVM |
| 准备 | 静态变量分配内存并设零值 | `static int a = 1` 此刻 a = 0，赋值在初始化阶段 |
| 解析 | 符号引用 → 直接引用 | 可延迟到首次使用时（懒解析） |
| 初始化 | 执行 `<clinit>()`（静态变量赋值 + static 块） | JVM 保证线程安全，这正是单例模式的基石 |

### 双亲委派模型

类加载器收到加载请求时，先委派给父加载器，父加载器无法完成时才自己加载。好处：**核心类库（如 `java.lang.String`）永远由启动类加载器加载**，用户无法伪造同名类替换它，保证了类型安全。

```text
Bootstrap ClassLoader（加载 JAVA_HOME/lib 核心库）
        ▲
ExtClassLoader / PlatformClassLoader（JDK 9+，加载扩展库）
        ▲
Application ClassLoader（加载 classpath 上的应用类）
        ▲
自定义 ClassLoader
```

经典应用——利用类加载器实现热部署或隔离（不同 ClassLoader 加载同名类，JVM 视为不同类型）：

```java
// 破坏双亲委派的典型合法场景：SPI（如 JDBC DriverManager）
// 线程上下文类加载器让核心库能"反向"加载应用 classpath 的实现类
ClassLoader appLoader = Thread.currentThread().getContextClassLoader();
Class<?> driverClass = appLoader.loadClass("com.mysql.cj.jdbc.Driver");
```

## 运行时数据区

### 堆（Heap）—— 线程共享，GC 主战场

现代 JVM（JDK 8+）的堆按分代组织：

```
┌─────────────────── 堆 ───────────────────┐
│  ┌─────────┐  ┌───────────────────────┐ │
│  │  年轻代   │  │        老年代          │ │
│  │ Eden+S0+S1│ │  长期存活的大对象/老对象   │ │
│  └─────────┘  └───────────────────────┘ │
└─────────────────────────────────────────┘
```

对象优先在 Eden 分配；Minor GC 后存活对象进入 Survivor 区，每熬过一次 Minor GC 年龄 +1，达到阈值（默认 15）晋升老年代。

### 线程私有区域

| 区域 | 作用 | 溢出场景 |
|------|------|----------|
| 虚拟机栈 | 每个方法调用对应一个栈帧（局部变量表、操作数栈） | 无终止递归 → `StackOverflowError` |
| 本地方法栈 | 为 native 方法服务 | 同上 |
| 程序计数器 | 记录当前线程执行的字节码行号 | 唯一不会 OOM 的区域 |

```java
// 栈溢出的最小复现：无出口递归
public class StackOverflowDemo {
    private int depth = 0;
    public void recurse() {
        depth++;          // 每次调用压入一个栈帧，超出 -Xss 上限即溢出
        recurse();
    }
    public static void main(String[] args) {
        StackOverflowDemo demo = new StackOverflowDemo();
        try {
            demo.recurse();
        } catch (StackOverflowError e) {
            // 注意：Error 不应被常规 catch，此处仅用于演示
            System.out.println("溢出时递归深度: " + demo.depth);
        }
    }
}
```

### 方法区与元空间（Metaspace）

JDK 8 起方法区由永久代（PermGen，堆内）改为元空间（Metaspace，**本地内存**）。原因：永久代大小受 `-XX:MaxPermSize` 硬限制，动态生成大量类（CGLIB、Groovy 脚本）时极易 OOM。元空间默认只受物理内存限制，可通过 `-XX:MaxMetaspaceSize` 设上限。

直接内存（Direct Memory）同样位于堆外，NIO 的 `ByteBuffer.allocateDirect()` 使用它，避免了堆内堆外来回复制，但分配回收成本更高。

## 垃圾回收（GC）

### 判断对象是否存活

- **引用计数法**：实现简单但无法处理循环引用，JVM 主流实现不采用
- **可达性分析**：从 GC Roots（栈帧局部变量、静态变量、JNI 引用等）向下搜索，不可达即为垃圾。HotSpot 采用此方案

```java
// 循环引用在可达性分析下可被正确回收
Object a = new Object();
Object b = new Object();
a.field = b;   // a 引用 b
b.field = a;   // b 引用 a
a = null;      // 断开 GC Roots 到 a/b 的路径后，两者均可被回收
b = null;
```

### GC 算法对比

| 算法 | 原理 | 优势 | 局限 |
|------|------|------|------|
| 标记-清除 | 标记垃圾后直接清除 | 简单 | 内存碎片、效率不稳定 |
| 标记-复制 | 存活对象复制到另一半空间 | 无碎片、高效（存活少时） | 浪费一半空间，适合年轻代 |
| 标记-整理 | 存活对象向一端移动 | 无碎片、不浪费空间 | 移动对象成本高，适合老年代 |
| 分代收集 | 年轻代用复制、老年代用标记-清除/整理 | 各取所长 | 需要跨代引用记录（卡表） |

### 主流垃圾收集器

| 收集器 | 作用区域 | 算法 | 特点 | 适用场景 |
|--------|----------|------|------|----------|
| Serial | 年轻代 | 复制 | 单线程，STW | 客户端/小内存 |
| Parallel Scavenge | 年轻代 | 复制 | 吞吐量优先，多线程 | 批处理任务 |
| CMS | 老年代 | 标记-清除 | 并发低停顿 | JDK 14 已移除，仅了解 |
| **G1** | 整堆 | 区域化分代 | 可预测停顿，Region 组织 | JDK 9+ 默认，大堆首选 |
| **ZGC** | 整堆 | 着色指针 + 读屏障 | 停顿 < 1ms（与堆大小无关） | JDK 15+ 生产可用，超大堆低延迟 |

选型经验：堆 4GB 以下 G1 足够；对 P99 延迟敏感（如交易接口）且堆 8GB+ 时考虑 ZGC（`-XX:+UseZGC`）。

### 触发 Full GC 的常见原因

1. 老年代空间不足（大对象直接进老年代 / 晋升过快）
2. 元空间不足（动态类生成过多）
3. 显式调用 `System.gc()`（生产环境建议 `-XX:+DisableExplicitGC`，但注意开启后 NIO 直接内存依赖该调用回收，需配合 `-XX:+ExplicitGCInvokesConcurrent`）
4. CMS 并发模式失败（promotion failed）退化 Serial Old

## 执行引擎与 JIT 编译

### 为什么字节码不能只靠解释执行

解释执行是逐条翻译字节码，热点代码反复翻译开销巨大。JIT（Just-In-Time）编译器把**热点代码**（被多次调用的方法、循环体）编译成本地机器码并缓存，后续直接执行机器码。

### 分层编译与逃逸分析

HotSpot 用方法调用计数器 + 回边计数器（循环）探测热点，触发编译。逃逸分析是 JIT 的高级优化：

```java
public long sumPoint() {
    // point 未逃逸出方法 → JIT 可栈上分配/标量替换，
    // 实际不会在堆上创建对象，GC 压力为零
    Point point = new Point(1, 2);
    return point.x + point.y;
}

static class Point {
    final int x, y;
    Point(int x, int y) { this.x = x; this.y = y; }
}
```

这解释了一个常见 benchmark 陷阱：不控制 JIT 的微基准测试结果毫无意义。正式的基准测试请用 [JMH](https://github.com/openjdk/jmh)。

## 调优与排错实战

### 常用参数速查

| 目的 | 参数 | 说明 |
|------|------|------|
| 堆初始/最大 | `-Xms4g -Xmx4g` | 生产建议设成相同，避免动态扩容抖动 |
| 年轻代大小 | `-Xmn2g` 或 `-XX:NewRatio=2` | G1 下一般不手动设 |
| 栈大小 | `-Xss512k` | 每线程栈大小 |
| 收集器 | `-XX:+UseG1GC` / `-XX:+UseZGC` | |
| OOM 转储 | `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/data/dump/` | **生产必开** |
| GC 日志 | `-Xlog:gc*:file=gc.log:time,uptime:filecount=5,filesize=50m`（JDK 9+） | 排障第一手资料 |

### 现场排查工具链

```bash
# 查看进程 JVM 概要信息（收集器、参数、类加载情况）
jinfo -sysprops <pid>

# 实时观察 GC 频率与各代占用（每 1s 输出一次，共 10 次）
jstat -gcutil <pid> 1000 10
#  S0  S1   E    O     M    YGC  YGCT  FGC  FGCT
#  0.00 95.2 80.1 45.3  98.1 1024 12.3   5   3.45

# 导出堆快照（OOM 排查核心步骤）
jmap -dump:live,format=b,file=heap.hprof <pid>

# 线程栈转储（排查死锁、线程暴涨）
jstack <pid> > thread-dump.txt
```

拿到 `heap.hprof` 后用 [VisualVM](https://visualvm.github.io/)、MAT 或 `jhat` 分析支配树，定位占据内存最大的对象及其引用链。

### OOM 类型速查

| 错误信息 | 根因 | 排查方向 |
|----------|------|----------|
| `Java heap space` | 堆内存耗尽 | heap dump 找大对象；检查集合类无限增长 |
| `GC overhead limit exceeded` | 98% 时间在 GC 却回收不到 2% | 堆接近全满，多为内存泄漏 |
| `Metaspace` | 类元数据超限 | CGLIB/反射动态代理滥用、类加载器泄漏 |
| `Direct buffer memory` | 堆外直接内存耗尽 | NIO DirectByteBuffer 未释放 |
| `unable to create new native thread` | 线程数超系统限制 | 线程池失控，检查 `-Xss` 与 ulimit |

## 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| "对象在栈上分配是 Java 语法特性" | 栈上分配是 JIT 逃逸分析的运行时优化 | 理解为"未逃逸对象可能被优化掉堆分配" |
| "调大堆就能解决 OOM" | 内存泄漏时只会推迟爆发时间 | 先分析 dump 定位泄漏点，再谈容量 |
| `System.gc()` 立即触发 Full GC | 只是"建议"，且可被禁用 | 依赖它做内存管理是反模式 |
| "GC 一定会 STW（Stop The World）" | CMS/G1/ZGC 的并发阶段几乎不停顿 | 区分 Minor / 并发标记 / Full GC 的停顿特征 |
| " finalize 可以做资源清理" | 执行时机不确定且拖垮 GC | 用 try-with-resources（见 [[java-se]]） |
| 手动置 null 帮助 GC | 绝大多数场景 JIT 即可判定死亡 | 仅长生命周期容器中的"过期引用"需要显式清理 |

## 与相关概念的关系

- 与 [[java-se|Java SE 核心语法]] 的关系：语言层面的引用类型、static、final 语义最终都落实为 JVM 指令与内存布局
- 与 [[java-multithreading|Java 多线程基础]] 的联系：虚拟机栈、程序计数器按线程私有，是线程隔离性的底层支撑
- 与 [[操作系统|操作系统基础]] 的联系：JVM 本身是用户态进程，堆内存映射到 OS 虚拟内存页，理解页交换有助于解释"GC 突然变慢"
- 与 [[java-interview|Java 面试题]] 的联系：JVM 内存区域与 GC 是高频面试题，本文档的表格可直接用于复习
- 与 [[java-high-concurrency|Java 后端高并发系统设计]] 的联系：低延迟目标下的 GC 停顿是接口长尾的重要来源

## 参考

- [The Java Virtual Machine Specification (Java SE)](https://docs.oracle.com/javase/specs/jvms/se21/html/)
- [HotSpot Virtual Machine Garbage Collection Tuning Guide](https://docs.oracle.com/en/java/javase/21/gctuning/)
- 《深入理解 Java 虚拟机（第 3 版）》周志明 著 —— JVM 中文经典
- [JMH — Java Microbenchmark Harness](https://github.com/openjdk/jmh)
- [[jvm-options|JVM 启动参数与 -D 系统属性速查]]：`-D` / `-X` / `-XX` 的完整参数清单与失效判断
- [[java-interview|Java 面试题]]
