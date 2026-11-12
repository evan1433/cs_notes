---
title: 中间件
description: Redis、Elasticsearch、MinIO、RustFS、消息队列等后端中间件技术
tags:
  - middleware
  - redis
  - elasticsearch
  - object-storage
  - message-queue
  - backend
date: 2026-11-09
---

# 中间件

中间件技术，包括 Redis、MinIO 等。

## 内容导航

- [[elasticsearch|Elasticsearch]]：分布式搜索与分析引擎，倒排索引、查询 DSL、聚合与调优
- [[kafka|Kafka]]：日志模型代表，KRaft 架构、ISR 副本、分层存储、事务与消费组调优
- [[message-queue|消息队列]]：MQ 通用原理与选型（队列 vs 日志模型、可靠性三段论、幂等与顺序）
- [[minio|MinIO]]：Go 编写的 S3 兼容对象存储，纠删码架构、部署运维与 SDK 实战
- [[redis|Redis]]：内存数据结构存储，缓存、分布式锁、队列与高可用架构
- [[redisson|Redisson]]：Redis Java 客户端框架，RLock 看门狗、延迟队列、限流器与分布式对象
- [[rocketmq|RocketMQ]]：业务消息中间件，CommitLog 存储、顺序/定时/事务消息、重试与死信
- [[rustfs|RustFS]]：Rust 编写的 S3 兼容对象存储，Apache 2.0、纠删码、rc 运维与 MinIO 迁移
