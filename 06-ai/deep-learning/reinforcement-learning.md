---
tag:
  - RL
  - deep-learning
---

# 传统强化学习

机器学习的一个分支，核心思想是**通过试错来学习**。
机器学习的一种范式，核心思想是：  
👉 **智能体（Agent）通过与环境（Environment）不断交互，根据得到的奖励（Reward）来学习最优行为策略（Policy）**。

## 核心要素：

1. **智能体（Agent）**：学习和做决策的主体。
2. **环境（Environment）**：智能体所处的外部世界，会根据智能体的动作给出反馈。
3. **状态（State）**：环境在某一时刻的情况描述。
4. **动作（Action）**：智能体可以做出的行为。
5. **奖励（Reward）**：环境对智能体动作的即时反馈（一个数值）。
6. **策略（Policy）**：智能体的行为准则，规定了在什么状态下应该采取什么动作。
7. **价值（Value）**：对长期累积奖励的预测，代表一个状态或动作的“长远好坏”。


![](https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcS8x2u5eP1dm-SRo3t_8KlkaQF7vYX6487UqLivoWIzAPEyEHkbTWBqUEe5fpG1rzvK65iBV09HfOhPX089n_mAxCJ9LK64Cdy8yiD9KH4BQRBr1KY)
## 强化学习与其他机器学习的区别

| **特性**   | **监督学习 (Supervised)** | **强化学习 (Reinforcement)** |
| -------- | --------------------- | ------------------------ |
| **数据源**  | 已经标记好的数据（正确答案）        | 通过与环境交互产生的数据             |
| **反馈机制** | 告诉你是或错                | 给出分数值（奖励/惩罚）             |
| **决策性质** | 独立预测（看图识猫）            | 序列决策（下一步怎么走影响未来）         |
| **学习目标** | 减小预测误差                | 最大化长期回报                  |

## 目标- > 最大化长期累计奖励（Expected Cumulative Reward）
找到一种行动方案（$\pi$）， 使得智能体*agent*从现在开始到未来所有能拿到的奖金（**$r$**）总和，在考虑了未来的不确定性和打折（$\gamma$）之后，其平均预期值（**$E$**）达到最大。
$$r_t = R(s_t, a_t, s_{t+1})$$
$$\pi_{\max} E \left[ \sum_{t=0}^{\infty} \gamma^t r_t \right]$$

| **符号**                    | **名称**                     | **含义解释**                                                          |
| ------------------------- | -------------------------- | ----------------------------------------------------------------- |
| $\pi$                 | **策略 (Policy)**            | 智能体的“决策蓝图”。它定义了在特定状态下，智能体应该采取什么动作。$\pi_{\max}$ 表示我们要找到一个**最优策略**。 |
| $E$                   | **期望 (Expectation)**       | 因为环境往往具有随机性（比如掷骰子或风向变化），我们无法保证每次结果一样，所以我们要计算所有可能结果的**平均预期值**。     |
| $\sum_{t=0}^{\infty}$ | **累加和**                    | 表示从时间步 $t=0$ 开始，一直到无穷远的未来，将所有获得的奖励加在一起。                           |
| $r_t$                 | **奖励 (Reward)**            | 在时间步 $t$ 时，智能体因为执行了某个动作而从环境获得的即时反馈（如得分或扣分）。                       |
| $\gamma$ (Gamma)      | **折扣因子 (Discount Factor)** | 取值范围通常在 $[0, 1]$ 之间。它决定了智能体**有多看重未来的奖励**。                         |

### 奖励计算方式
1. 稀疏奖励
2. 密集奖励
3. 惩罚项

## 策略（Policy）

**策略 π**：
> 给定状态 s，选择动作 a 的规则
- **确定性策略**：    $a = \pi(s)$
- **随机策略**：    $\pi(a|s) = P(a \mid s)$

## 典型算法分类

### **1️⃣ 基于价值（Value-based）**
学习“这个状态/动作值不值钱”
- **Q-learning**
- **SARSA**
- **DQN（Deep Q-Network）**
---
### **2️⃣ 基于策略（Policy-based）**
直接学习策略
- **REINFORCE**
- **Policy Gradient**
---
### **3️⃣ Actor-Critic（混合）**
- Actor：学策略
- Critic：学价值
常见算法：
- **A2C / A3C**
- **PPO**
- **DDPG / SAC**
## 主要挑战
- 奖励稀疏（Sparse rewards）：智能体很难获得有效反馈。
- 探索与利用的权衡（Exploration vs. Exploitation）。
- 样本效率低（需要大量交互）。
- 环境动态复杂或部分可观测。

## 强化学习应用
擅长处理需要**连续决策**的复杂任务。
- 🎮 游戏（AlphaGo、Atari）
- 🚗 自动驾驶
- 🤖 机器人控制
- 📈 资源调度、推荐策略
- 🧠 大模型对齐（RLHF）

# 大模型强化学习


[chatgpt answer: 大模型强化学习 RLHF SFT PPO 这几个概念的逻辑关系](https://chatgpt.com/c/695dcd75-c954-8325-a028-a7e4c473d708)

SFT 本质上就是强化学习力的 Imitation Learning  / Behavior Cloning

## RLHF

**RLHF**（Reinforcement Learning from Human Feedback，人类反馈强化学习）
## 目标

**让模型“说人话、做人事”**，即实现 **人类对齐（Human Alignment）**。
**RLHF的核心思想是：将人类模糊的“偏好”转化为一个可优化的数学目标。**

> Hugging Face RLHF Blog

[huggingface-ChatGPT 背后的“功臣”——RLHF 技术详解](https://huggingface.co/blog/zh/rlhf)


RLHF 三步骤
1. SFT （Supervised Fine-Tuning）
2. RM 奖励模型
3. PPO

## SFT
$$
L_{SFT} = -\sum_{t}log\pi_\theta(y_t|x,y_{<t})
$$

## PPO（Proximal Policy Optimization）

chat with gpt  [什么是强化学习](https://chatgpt.com/c/6948ff06-b378-8331-9536-b271f40b5f2c)

目标   在提高策略表现的同时，限制每一次更新不要改得太猛。

四个模型

|**模型名称**|**角色 (Role)**|**作用**|**是否更新参数**|
|---|---|---|---|
|**Policy Model**|Actor (演员)|正在被优化的 LLM，负责生成回复。|**是**|
|**Value Model**|Critic (评论家)|预测当前状态能获得的长期回报，辅助 Actor 更新。|**是**|
|**Reward Model**|Reward (奖励)|根据人类偏好给回复打分（由 RLHF 第二步训练好）。|否|
|**Reference Model**|Ref (参考)|初始的 SFT 模型，用来防止 Policy 偏离太远（KL 散度约束）。|否|

| 符号           | 含义                           |
| ------------ | ---------------------------- |
| $s$          | 状态（环境当前情况）                   |
| $a$          | 在状态 (s) 下采取的动作               |
| $\hat A$     | Advantage（优势），表示“这个动作比平均好多少” |
| $\mathbb{E}$ | 对很多采样取平均                     |
- $\pi_\theta(a|s)$ 

概率比率（ratio）
$$
r_t​(θ)= \frac{π_θ​(a_t​∣s_t​)}{π_{θ_{old}}​​(a_t​∣s_t)​)}​​
$$

| 符号                    | 含义         |
| --------------------- | ---------- |
| $t$                   | 时间步        |
| $\theta$              | 当前要更新的参数   |
| $\theta_{\text{old}}$ | 采样数据时的旧参数  |
| $s_t$                 | 第 t 步的状态   |
| $a_t$                 | 第 t 步采取的动作 |

clip

$$
clip(rt​,1−ϵ,1+ϵ)
$$
把 $r_t$​ **限制在** $[1-\epsilon,\,1+\epsilon]$ 之间

PPO
$$
L_{PPO}​(θ)=E_t​[min(r_t​(θ)A^t​,clip(r_t​(θ),1−ϵ,1+ϵ)A^t​)]
$$

Advantage 
$$
\hat{A_t} = R_t-V(s_t)
$$
### KL散度
KL 散度（Kullback–Leibler Divergence）定义为：

$$
KL(πθ​∥πref​)=E_{a∼πθ}​​[log \frac{π_\theta(a∣s)}{π_{ref}​(a∣s)}​]
$$

## DPO (Direct Preference Optimization)
**DPO**（Direct Preference Optimization，**直接偏好优化**）


## GRPO (Group Relative Policy Optimization)
**Group Relative Policy Optimization**（分组相对策略优化）

GRPO 损失 = 策略优化损失（PPO 裁剪） - KL 散度约束

$L_{\text{GRPO}} = \mathbb{E}\left[ \min\left(\rho_i A_i, \operatorname{clip}(\rho_i, 1-\epsilon, 1+\epsilon) A_i \right) - \beta D_{\text{KL}}(\pi_{\text{new}} \parallel \pi_{\text{ref}}) \right]$

$\rho_i = \frac{\pi_{\text{new}}(y_i|x)}{\pi_{\text{old}}(y_i|x)}$

$A_i = \frac{r_i - \mu(R)}{\sigma(R)}$
- $r_i$：第 i 个回答的**奖励分数**（正确 / 格式 / 语言）
- μ(R)：一个组内所有回答奖励的**平均值**
- σ(R)：一个组内所有回答奖励的**标准差**
# RL framework
TRL (Transformer Reinforcement Learning)

TRLX


# reference
https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide
https://unsloth.ai/docs/zh/bo-ke/ai-engineers-2025