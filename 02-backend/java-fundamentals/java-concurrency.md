---
title: java-并发
description: Java 并发编程进阶，以 CompletableFuture 异步编排为主线
tags:
  - java
  - concurrency
  - completable-future
  - backend
date: 2026-10-12
---

> 前置知识：[[java-multithreading|Java 多线程基础]]、[[java-thread-pool|Java 线程池]]

- https://redspider.gitbook.io/concurrent


[CompletableFuture](https://juejin.cn/post/7455561985378598951)

#### 为什么要使用CompletableFuture
示例 

```java
CompletableFuture<ProductInfo> productFuture = CompletableFuture.supplyAsync(() -> getProductInfo());

CompletableFuture<Stock> stockFuture = CompletableFuture.supplyAsync(() -> getStock());

CompletableFuture<Promotion> promotionFuture = CompletableFuture.supplyAsync(() -> getPromotion());

CompletableFuture<Comments> commentsFuture = CompletableFuture.supplyAsync(() -> getComments());

CompletableFuture.allOf(productFuture, stockFuture, promotionFuture, commentsFuture)
    .thenAccept(v -> {
        // 所有数据都准备好了，开始组装页面
        buildPage(productFuture.join(), stockFuture.join(), 
                 promotionFuture.join(), commentsFuture.join());
    });

```

### 2. 创建异步任务的花式方法

```java
// supplyAsync：我做事靠谱，一定给你返回点什么
CompletableFuture<String> future1 = CompletableFuture.supplyAsync(() -> {
    return "我是有结果的异步任务";
});

// runAsync：我比较佛系，不想给你返回任何东西
CompletableFuture<Void> future2 = CompletableFuture.runAsync(() -> {
    System.out.println("我只是默默地执行，不给你返回值");
});

```

#### 自定义线程池的正确姿势

```java
// 错误示范：这是一匹脱缰的野马！
ExecutorService wrongPool = Executors.newFixedThreadPool(10);

// 正确示范：这才是精心调教过的千里马
ThreadPoolExecutor rightPool = new ThreadPoolExecutor(
    5,                      // 核心线程数（正式员工）
    10,                     // 最大线程数（含临时工）
    60L,                    // 空闲线程存活时间
    TimeUnit.SECONDS,       // 时间单位
    new LinkedBlockingQueue<>(100),  // 工作队列（候客区）
    new ThreadFactoryBuilder().setNameFormat("async-pool-%d").build(),  // 线程工厂（员工登记处）
    new ThreadPoolExecutor.CallerRunsPolicy()  // 拒绝策略（客满时的处理方案）
);

// 使用自定义线程池
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    return "我是通过专属线程池执行的任务";
}, rightPool);

```



#### 异步任务的取消和超时处理

```java
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    // 模拟一个耗时操作
    try {
        Thread.sleep(5000);
    } catch (InterruptedException e) {
        // 被中断时的处理
        return "我被中断了！";
    }
    return "正常完成";
});

// 设置超时
try {
    String result = future.get(3, TimeUnit.SECONDS);
} catch (TimeoutException e) {
    future.cancel(true);  // 超时就取消任务
    System.out.println("等太久了，不等了！");
}

// 更优雅的超时处理
future.completeOnTimeout("默认值", 3, TimeUnit.SECONDS)
      .thenAccept(result -> System.out.println("最终结果：" + result));

// 或者配合orTimeout使用
future.orTimeout(3, TimeUnit.SECONDS)  // 超时就抛异常
      .exceptionally(ex -> "超时默认值")
      .thenAccept(result -> System.out.println("最终结果：" + result));

```


### 3. 链式调用的艺术
#### thenApply、thenAccept、thenRun的区别

```java
CompletableFuture.supplyAsync(() -> "Hello")
    .thenApply(s -> {
        // 我是加工工人，负责把材料加工后返回新成品
        return s + " World";
    })
    .thenAccept(result -> {
        // 我是检验工人，只负责验收，不返回东西
        System.out.println("收到结果: " + result);
    })
    .thenRun(() -> {
        // 我是打扫工人，不关心之前的结果，只负责收尾工作
        System.out.println("生产线工作完成，开始打扫");
    });

```


#### 异步转换：thenApplyAsync的使用场景

```java
CompletableFuture.supplyAsync(() -> {
    // 模拟获取用户信息
    return "用户基础信息";
}).thenApplyAsync(info -> {
    // 耗时的处理操作，在新的线程中执行
    try {
        Thread.sleep(1000);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
    return info + " + 附加信息";
}, customExecutor);  // 可以指定自己的线程池

```


#### 组合多个异步操作：thenCompose vs thenCombine

```java
CompletableFuture<String> getUserEmail(String userId) {
    return CompletableFuture.supplyAsync(() -> "user@example.com");
}

CompletableFuture<String> future = CompletableFuture
    .supplyAsync(() -> "userId")
    .thenCompose(userId -> getUserEmail(userId));  // 基于第一个结果去获取邮箱

```


### 4. 异常处理的技巧

#### 应急的exceptionally

```java
CompletableFuture<String> future = CompletableFuture
    .supplyAsync(() -> {
        if (Math.random() < 0.5) {
            throw new RuntimeException("服务暂时不可用");
        }
        return "正常返回的数据";
    })
    .exceptionally(throwable -> {
        // 记录异常日志
        log.error("操作失败", throwable);
        // 返回默认值
        return "服务异常，返回默认数据";
    });

```
#### 两全其美的handle


```java
CompletableFuture<String> future = CompletableFuture
    .supplyAsync(() -> {
        if (Math.random() < 0.5) {
            throw new RuntimeException("模拟服务异常");
        }
        return "原始数据";
    })
    .handle((result, throwable) -> {
        if (throwable != null) {
            log.error("处理异常", throwable);
            return "发生异常，返回备用数据";
        }
        return result + " - 正常处理完成";
    });

```

#### whenComplete

```java
// whenComplete：只是旁观者，不能修改结果
CompletableFuture<String> future1 = CompletableFuture
    .supplyAsync(() -> "原始数据")
    .whenComplete((result, throwable) -> {
        // 只能查看结果，无法修改
        if (throwable != null) {
            log.error("发生异常", throwable);
        } else {
            log.info("处理完成: {}", result);
        }
    });

// handle：既是参与者又是修改者
CompletableFuture<String> future2 = CompletableFuture
    .supplyAsync(() -> "原始数据")
    .handle((result, throwable) -> {
        // 可以根据结果或异常，返回新的值
        if (throwable != null) {
            return "异常情况下的替代数据";
        }
        return result + " - 已处理";
    });

```