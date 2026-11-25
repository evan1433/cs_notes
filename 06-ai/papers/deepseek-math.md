---
title: DeepSeekMath - Pushing the Limits of Mathematical Reasoning in Open Language Models
date: 2024-02-05
tags: [llm, 数学推理, reinforcement-learning, deepseek, grpo]
---

# DeepSeekMath - Pushing the Limits of Mathematical Reasoning in Open Language Models

> 论文链接: [arXiv:2402.03300](https://arxiv.org/abs/2402.03300)
> Huggingface: [papers/2402.03300](https://huggingface.co/papers/2402.03300)

## 概述

DeepSeekMath 7B 是 DeepSeek 团队推出的专注于数学推理能力的开源语言模型。该模型通过大规模数学数据预训练和创新的强化学习方法，在数学推理任务上取得了接近 GPT-4 的性能。

## 核心贡献

### 1. 大规模数学数据预训练

- 基于 DeepSeek-Coder-Base-v1.5 7B 继续预训练
- 使用 **120B 数学相关 tokens**（来自 Common Crawl）
- 结合自然语言和代码数据
- 精心设计的数据选择管道（data selection pipeline）

### 2. Group Relative Policy Optimization (GRPO)

GRPO 是 PPO 的改进版本，专门用于增强数学推理能力：

- **内存优化**: 相比 PPO 显著降低内存使用
- **效率提升**: 更高效的强化学习训练
- **推理增强**: 专门针对数学推理任务优化

## 性能表现

### MATH Benchmark

| 方法 | 分数 |
|------|------|
| DeepSeekMath 7B (单样本) | 51.7% |
| DeepSeekMath 7B (64样本自一致性) | 60.9% |
| Gemini-Ultra | ~55% |
| GPT-4 | ~52% |

**关键特点**:
- 不依赖外部工具包（如计算器、代码执行）
- 不使用投票技术（单样本即可达到高性能）

## 技术细节

### 数据选择管道

从 Common Crawl 中筛选数学相关数据的关键步骤：

1. **种子数据收集**: 从高质量数学网站收集种子 URL
2. **分类器训练**: 训练分类器识别数学相关网页
3. **数据过滤**: 去除低质量、重复内容
4. **去重处理**: 确保数据多样性

### GRPO 算法

Group Relative Policy Optimization 的核心思想：

- 使用组内相对奖励（group-relative rewards）
- 减少对价值网络（value network）的依赖
- 降低训练内存开销
- 更稳定的训练过程

## 模型版本

| 模型 | 说明 |
|------|------|
| deepseek-math-7b-base | 基础预训练模型 |
| deepseek-math-7b-instruct | 指令微调版本 |
| deepseek-math-7b-rl | 强化学习优化版本 |

## 关键发现

1. **公开网络数据的潜力**: 通过精心设计的数据选择，公开网络数据可以显著提升数学推理能力
2. **代码预训练的价值**: 代码预训练对数学推理有正向迁移效果
3. **强化学习的有效性**: GRPO 能有效提升模型的推理能力

## 相关工作

- DeepSeek-Coder: 代码预训练模型
- PPO (Proximal Policy Optimization): 强化学习算法
- MATH Benchmark: 数学竞赛级别评测集

## 启示与应用

1. **数据质量 > 数据量**: 精心筛选的数据比大规模低质量数据更有效
2. **领域特定预训练**: 针特定领域（如数学）的预训练可以显著提升性能
3. **强化学习 + LLM**: RL 方法可以有效提升 LLM 的推理能力

## 参考资源

- [GitHub 仓库](https://github.com/deepseek-ai/DeepSeek-Math)
- [Huggingface 模型](https://huggingface.co/deepseek-ai)
- arXiv: [2402.03300](https://arxiv.org/abs/2402.03300)