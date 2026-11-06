---
title: Python 实战案例
description: Python 在真实项目中的落地案例，记录场景、完整代码与踩坑
tags:
  - python
  - practice
date: 2026-11-06
---

# 实战案例

把语法与库知识放进具体场景里验证的案例集合：每个案例都给出可运行代码与
"为什么这样做"的取舍说明，而不是孤立的 API 示例。

## 案例列表

| 案例 | 场景 | 涉及技术 |
|------|------|----------|
| [[milvus-coroutines\|协程操作 Milvus 向量数据库]] | 批量向量检索与写入 | asyncio、`run_in_executor`、pymilvus |

## 相关

- [[index|Python 笔记目录]]
- [[04-python-async|Python 异步编程]] —— 案例中用到的协程调度与同步 SDK 包装方式
