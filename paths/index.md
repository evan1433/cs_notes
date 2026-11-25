---
title: 学习路线
description: 按顺序学习 LLM、Agent、后端工程和系统架构，并用实践检验所学。
tags:
  - learning-path
date: 2026-11-25
---

按目标选一条路线。需要补齐计算机基础或 Python 时，可以在 [[learning/index|系统学习清单]] 勾选进度。

## LLM 与 Agent

- **LLM** · 沿 [[06-ai/index#LLM 基础|LLM 基础路线]] 学习模型结构、下一 token 预测和 Transformers，动手运行一次文本推理。
- **Agent** · 沿 [[06-ai/index#Agent 应用|Agent 应用路线]] 学习工具调用、检索和框架接入，为一个任务画出交互流程及停止条件。

想自行训练模型或提供服务，可以接着走 [[06-ai/index#模型训练|模型训练]] 或 [[06-ai/index#推理部署|推理部署]] 路线。

## 后端工程

1. 从 [[02-backend/java-fundamentals/index|Java 基础]] 或 [[02-backend/python/index|Python]] 选一门语言，练习数据处理与错误处理。
2. 阅读 [[02-backend/databases/index|数据库]] 和 [[02-backend/spring/index|Spring]]，用数据库和 Web 框架搭一个持久化接口。
3. 对照 [[02-backend/projects/gulimall-project|谷粒商城实践]]，理解服务注册、配置和网关各自解决的问题。

## 系统架构

1. 阅读 [[architecture/domain-driven-design|领域驱动设计]]，为一个业务场景划分上下文和服务边界。
2. 阅读 [[architecture/high-availability|高可用设计]]，为服务间依赖设置超时，分析重试与降级的取舍。
3. 参考 [[architecture/architecture-decision-records|架构决策记录]] 和 [[architecture/decisions/adr-002-order-service-split|订单服务拆分案例]]，记录选项、后果和验证方法。
