---
title: 架构决策记录（ADR）索引
description: architecture 下的架构决策记录存档，按编号倒序维护，记录每个重要决策的背景、候选方案与后果
tags:
  - architecture-decision-record
  - system-architecture
  - index
date: 2026-11-13
---

# 架构决策记录（ADR）索引

本目录存放架构决策的**不可变存档**。每篇 ADR 记录一个决策当时的约束、候选方案和结论，
写完即冻结——要改结论就新开一篇并把旧的标记为 `superseded`，不要原地改写历史。

方法论与模板见 [[architecture-decision-records|架构决策记录（ADR）]]，
模板文件见 `templates/adr-template.md`。

## 编号规则

`adr-{三位编号}-{英文短横线标题}.md`，编号只增不减，即使决策被否决也占用编号
（被否决的决策本身是有价值的信息）。

## 决策清单

| 编号 | 决策 | 状态 | 日期 | 影响范围 |
|------|------|------|------|----------|
| [[architecture/decisions/adr-002-order-service-split|ADR-002]] | 订单能力从单体拆分为独立服务 | accepted | 2026-11-13 | 交易域、运维、发布流程 |
| [[architecture/decisions/adr-001-config-center-nacos|ADR-001]] | 配置中心选用 Nacos（而非 Consul / Apollo） | accepted | 2026-11-13 | 全部后端服务、运维 |

## 待决策（Backlog）

尚未拍板但已识别的问题，避免决策悬空导致实现层各写一套：

| 议题 | 为什么还没定 | 卡点 |
|------|--------------|------|
| 服务间通信：同步 RPC 还是异步消息为主 | 缺少真实调用链数据 | 需先完成链路追踪埋点 |
| 是否引入服务网格 | 当前服务数量未达收益阈值 | 服务数 < 20 时 Sidecar 运维成本大于收益 |

## 与其他笔记的关系

- 决策的评审过程见 [[architecture-review|架构评审与 ATAM]]
- 服务拆分边界的判定理论见 [[domain-driven-design|领域驱动设计（DDD）]]
- 决策后需要保障的稳定性指标见 [[high-availability|高可用与稳定性设计]]
- 配置中心方案的完整技术对比见 [[service-governance-config-center|服务治理与配置中心：Nacos / Consul / Apollo]]
