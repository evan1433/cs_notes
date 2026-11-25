 **Causal Language Model（因果语言模型，CLM）** 是 NLP 中的核心架构，也是当前 GPT、LLaMA、Qwen 等主流大模型的基础范式。

## 核心定义

**因果语言模型 = 仅使用单向上下文（左侧 token）预测下一个 token**

与 BERT 等双向模型不同，CLM 严格遵循"从左到右"的因果约束：
- 位置 $i$ 的预测只能依赖 $0 \dots {i-1}$ 的 token
- 通过 **三角掩码（Triangular/Causal Mask）** 实现：$M_{ij} = -\infty$ if $j > i$

```
输入:  [我] [喜欢] [深度] [学习]
预测:   ↓    ↓     ↓      ↓
      P(我) P(喜欢|我) P(深度|我喜欢) P(学习|我喜欢深度)
```

## 关键特性

| 特性        | 说明                                    |
| --------- | ------------------------------------- |
| **自回归生成** | 逐 token 生成，天然适合文本生成任务                 |
| **单向注意力** | 使用 Causal Self-Attention，复杂度 $O(n^2)$ |
| **预训练目标** | Next Token Prediction（NTP）            |
| **位置编码**  | 需要显式位置编码（RoPE、ALiBi 等）                |

## 与 MLM 的对比

| | **CLM (GPT 系列)** | **MLM (BERT)** |
|--|-------------------|----------------|
| 方向 | 单向（Left-to-Right） | 双向 |
| 掩码 | 三角掩码 | 随机掩码 [MASK] |
| 预训练 | 预测下一个 token | 预测被掩码的 token |
| 生成能力 | **强**，原生支持 | 弱，需额外适配 |
| 理解能力 | 良好 | **更强**（双向语境） |
| 典型应用 | 文本生成、对话、代码 | 文本理解、分类、NER |

## 代码实现要点

```python
import torch
import torch.nn as nn

# 1. Causal Mask 生成
def create_causal_mask(seq_len):
    """下三角矩阵，True/1 表示可 attend"""
    mask = torch.tril(torch.ones(seq_len, seq_len))
    return mask.bool()

# 2. 在 Transformer 中的应用
causal_mask = create_causal_mask(seq_len)  # [seq_len, seq_len]
attn_scores = attn_scores.masked_fill(~causal_mask, float('-inf'))
```

Hugging Face 中，GPT-2/LLaMA 等模型的 `is_decoder=True` 即启用因果掩码。

## 训练目标

$$
\mathcal{L}_{CLM} = -\sum_{i=1}^{N} \log P(x_i | x_{<i}; \theta)
$$

等价于交叉熵损失，标签为输入序列的右移版本（next token 作为 target）。

## 变体与演进

| 变体 | 改进点 |
|------|--------|
| **Prefix LM**（T5、UniLM） | 前缀双向，后续单向，兼顾理解与生成 |
| **Causal with Prefix** | 如 Qwen-VL，图像部分双向，文本部分因果 |
| **Sliding Window** | 局部因果注意力，降低长序列成本 |

## 与你的技术栈关联

基于你的背景（PyTorch + Transformers + 正在做 VLM）：

- **Qwen-VL/Qwen2-VL**：视觉部分用 ViT 编码，文本部分标准 **Causal LM**
- **LLaVA**：同样遵循 Causal LM 架构，视觉 token 作为前缀
- **PrefixLM vs CLM**：Qwen-VL 的图像-文本交互中，图像 token 通常可双向 attend（Prefix），文本保持因果

需要我展开 **Prefix LM 的具体实现**（与纯 Causal LM 的 mask 差异），或者提供一份可运行的 **Mini Causal LM 训练代码**？