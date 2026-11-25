---
title: PPO 近端策略优化算法
description: 深入解析PPO算法原理、数学推导、代码实现及在大模型RLHF中的应用
tags:
  - reinforcement-learning
  - deep-learning
  - ppo
  - rlhf
  - llm
date: 2026-04-13
---

# PPO 近端策略优化算法

PPO（Proximal Policy Optimization，近端策略优化）是OpenAI于2017年提出的一种策略梯度强化学习算法，以其高效性、稳定性和易实现性成为强化学习领域的主流算法，也是ChatGPT等大模型RLHF训练的核心技术。

## 核心原理

### 问题背景

传统策略梯度方法存在两大痛点：

| 问题 | 描述 |
|------|------|
| **更新步长敏感** | 步长过大易导致策略崩溃，步长过小则收敛缓慢 |
| **样本利用率低** | 需大量环境交互数据，单次更新后数据即失效 |

TRPO（Trust Region Policy Optimization）通过约束策略更新幅度解决这些问题，但实现复杂、计算成本高。PPO通过简化约束机制，在保持稳定性的同时大幅降低实现复杂度。

### PPO的解决方案

| 技术手段 | 作用 |
|---------|------|
| **Clipped Surrogate Objective** | 限制策略更新幅度，确保新策略与旧策略差异可控 |
| **重要性采样** | 复用旧策略采集的数据，提升样本效率 |
| **自适应KL惩罚** | 替代TRPO的复杂约束优化，降低计算成本 |

## 数学推导

### 策略梯度基础

策略梯度目标函数：

$$\nabla_\theta J(\theta) = \mathbb{E}[\nabla_\theta \log \pi_\theta(a|s) A(s,a)]$$

其中 $A(s,a)$ 为优势函数，衡量动作的相对价值。

### PPO目标函数

PPO引入重要性采样比，构建clipped目标函数：

$$L^{CLIP}(\theta) = \mathbb{E}_t[\min(r_t(\theta) \hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon) \hat{A}_t)]$$

**关键符号说明：**

| 符号 | 含义 |
|------|------|
| $r_t(\theta)$ | 概率比率：$\frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{old}}(a_t|s_t)}$ |
| $\hat{A}_t$ | 优势函数估计 |
| $\epsilon$ | 裁剪参数（通常为0.2） |
| $\text{clip}(x, a, b)$ | 将 $x$ 限制在 $[a, b]$ 区间 |

**Clip机制的核心作用：**

- 限制 $r_t(\theta)$ 在 $[1-\epsilon, 1+\epsilon]$ 区间
- 取最小值确保优化方向保守，避免过度偏离旧策略
- 当优势为正时，鼓励该动作但不过度增加概率
- 当优势为负时，抑制该动作但不过度降低概率

### 优势估计（GAE）

广义优势估计（Generalized Advantage Estimation）：

$$\hat{A}_t = \sum_{l=0}^{\infty}(\gamma\lambda)^l \delta_{t+l}$$

其中：

$$\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

- $\gamma$：折扣因子（通常为0.99）
- $\lambda$：GAE参数（通常为0.95），控制偏差-方差权衡

## PyTorch代码实现

### 核心算法实现

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

class PPO:
    def __init__(self, actor_critic, clip_param=0.2, lr=3e-4, 
                 ent_coef=0.01, gamma=0.99, gae_lambda=0.95):
        self.actor_critic = actor_critic
        self.optimizer = optim.Adam(actor_critic.parameters(), lr=lr)
        self.clip_param = clip_param
        self.ent_coef = ent_coef  # 熵正则化系数
        self.gamma = gamma
        self.gae_lambda = gae_lambda

    def compute_gae(self, rewards, values, next_values, dones):
        """计算广义优势估计"""
        advantages = []
        gae = 0
        
        # 从后往前计算
        for t in reversed(range(len(rewards))):
            delta = rewards[t] + self.gamma * next_values[t] * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages.append(gae)
        
        advantages = torch.tensor(advantages[::-1], dtype=torch.float32)
        # 归一化优势函数
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        return advantages

    def update(self, rollouts):
        """PPO更新步骤"""
        obs, actions, old_log_probs, returns, advantages = rollouts.sample()

        # 计算新策略的概率和熵
        dist, values = self.actor_critic(obs)
        new_log_probs = dist.log_prob(actions)
        entropy = dist.entropy().mean()

        # 重要性采样比
        ratio = (new_log_probs - old_log_probs).exp()
        
        # PPO裁剪目标函数
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1 - self.clip_param, 
                           1 + self.clip_param) * advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        # 价值函数损失（使用Huber损失）
        value_loss = 0.5 * (returns - values).pow(2).mean()

        # 总损失（含熵正则化）
        loss = policy_loss + value_loss - self.ent_coef * entropy

        # 梯度更新
        self.optimizer.zero_grad()
        loss.backward()
        # 梯度裁剪防止梯度爆炸
        torch.nn.utils.clip_grad_norm_(self.actor_critic.parameters(), 0.5)
        self.optimizer.step()
        
        return policy_loss.item(), value_loss.item(), entropy.item()
```

### 算法流程伪代码

```
for epoch in 1, 2, ..., N:
    # 1. 收集数据
    for t in 1, 2, ..., T:
        使用当前策略 π_θ_old 与环境交互
        存储 {s_t, a_t, r_t, log_prob_t, V_t}
    
    # 2. 计算优势与回报
    使用GAE算法计算每个时间步的优势值 A_t
    计算回报 G_t = A_t + V_t
    
    # 3. 优化策略（多轮更新）
    for k in 1, 2, ..., K:
        随机采样一个 batch 数据
        计算重要性采样比 r_t(θ)
        计算 clipped 目标函数 L^CLIP
        更新策略网络参数 θ
        更新价值网络参数 φ
```

## 大模型RLHF中的应用

### RLHF三阶段流程

PPO是RLHF（Reinforcement Learning from Human Feedback）第三阶段的核心算法：

| 阶段          | 方法          | 目标             |
| ----------- | ----------- | -------------- |
| **Stage 1** | SFT（监督微调）   | 让模型学会基本对话能力    |
| **Stage 2** | RM（奖励模型训练）  | 训练一个能判断回答质量的模型 |
| **Stage 3** | PPO（强化学习优化） | 使用奖励模型优化策略模型   |

### RLHF中的四个关键模型

在PPO阶段，涉及四个核心模型：

| 模型 | 角色 | 状态 | 作用 |
|------|------|------|------|
| **Actor Model** | 演员 | 可训练 | 目标语言模型，生成回复 |
| **Reference Model** | 参考 | 冻结 | 防止Actor偏离原始SFT模型太远 |
| **Critic Model** | 评论家 | 可训练 | 预测总收益 $V_t$ |
| **Reward Model** | 奖励 | 冻结 | 计算即时收益 $R_t$ |

### RLHF中的奖励计算

在LLM场景下，奖励函数设计特殊：

**非最后token位置：**
$$R_t = -kl\_ctl \times (\log P_{actor} - \log P_{ref})$$

**最后token位置：**
$$R_T = \text{KL惩罚} + \text{Reward Model打分}$$

即：整个回复的奖励分数只在最后一个token位置给出，其余位置主要由KL散度惩罚构成，防止模型偏离参考模型太远。

### RLHF中的Actor Loss

$$actor\_loss = -\min(Adv_t \cdot ratio, Adv_t \cdot \text{clip}(ratio, 1-\epsilon, 1+\epsilon))$$

其中优势函数 $Adv_t$ 基于GAE计算：

$$Adv_t = (R_t + \gamma V_{t+1} - V_t) + \gamma \lambda Adv_{t+1}$$

### RLHF中的Critic Loss

$$critic\_loss = \frac{1}{2} (V_t - returns_t)^2$$

其中 $returns_t = Adv_t + V_t$（基于GAE计算的实际收益）。

同样会对预测值 $V_t$ 进行裁剪，限制其在 $V_{old}$ 的一定范围内。

### 应用案例

| 模型 | 应用说明 |
|------|---------|
| **ChatGPT / GPT-4** | PPO是RLHF训练的核心算法，确保输出符合人类偏好 |
| **Claude** | 使用类似RLHF框架，PPO用于安全性和有用性对齐 |
| **Llama 2** | 采用PPO进行RLHF训练，开源完整训练流程 |
| **InstructGPT** | OpenAI早期PPO应用示范 |

## 算法优势与局限

### 优势

| 特点 | 说明 |
|------|------|
| **稳定性** | 限制策略更新幅度，避免训练崩溃 |
| **效率** | 支持大规模并行训练，样本利用率高 |
| **可控性** | KL散度惩罚确保输出质量 |
| **易实现** | 相比TRPO实现简单，计算成本低 |

### 局限性与改进

| 局限性 | 改进方向 |
|--------|----------|
| 局部最优陷阱 | PPO-Adaptive：动态调整Clip范围 |
| 高维动作空间调整困难 | POP：解耦策略与价值函数更新频率 |
| 探索能力受限 | 结合元学习（如Meta-PPO） |

## 与其他算法对比

### PPO vs TRPO

| 特性 | PPO | TRPO |
|------|-----|------|
| **约束方式** | 裁剪目标函数 | KL散度硬约束 |
| **实现复杂度** | 简单 | 复杂（需二阶优化） |
| **计算成本** | 低 | 高 |
| **性能** | 相当或更好 | 较好 |

### PPO vs DPO

DPO（Direct Preference Optimization）是PPO的简化替代方案：

| 特性 | PPO | DPO |
|------|-----|------|
| **训练流程** | 需奖励模型 + PPO优化 | 直接优化，无需奖励模型 |
| **计算成本** | 高（四个模型） | 低（仅需策略模型） |
| **稳定性** | 需调参 | 更稳定 |
| **效果** | 更强（复杂场景） | 较好（简单场景） |

## 参考资源

### 原论文

- **PPO论文**：[Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347) (OpenAI, 2017)
- **GAE论文**：[High-Dimensional Continuous Control Using Generalized Advantage Estimation](https://arxiv.org/abs/1506.02438)

### 教程与博客

- [强化学习算法解析：PPO](https://www.cnblogs.com/BlogNetSpace/p/18806099) - 详细数学推导与代码实现
- [大模型RLHF：PPO原理与源码解读](https://www.cnblogs.com/zhangxianrong/p/18277086) - DeepSpeed-Chat源码分析
- [近端策略优化(PPO)算法的理论基础与PyTorch代码详解](https://developer.aliyun.com/article/1651947) - 实战代码实现

### 开源实现

- **Stable Baselines3**：[github.com/DLR-RM/stable-baselines3](https://github.com/DLR-RM/stable-baselines3)
- **TRL (HuggingFace)**：[github.com/huggingface/trl](https://github.com/huggingface/trl) - RLHF训练框架
- **DeepSpeed-Chat**：[github.com/microsoft/DeepSpeedExamples](https://github.com/microsoft/DeepSpeedExamples) - 大模型RLHF实现

## 相关笔记

- [[reinforcement-learning|强化学习基础]]
- [[llm-rl-vs-traditional-rl|大模型强化学习与传统RL的区别]]
- [[fine-tuning-framework|大模型微调框架]]