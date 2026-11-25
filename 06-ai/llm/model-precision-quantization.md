---
title: 模型精度与量化方法
description: 深度学习模型中常用的数值精度格式（FP32/BF16/FP16/FP8/INT8/INT4 等）及量化方法的全面解析
tags:
  - llm
  - quantization
  - precision
  - inference
date: 2026-05-25
---
# 模型精度与量化方法

## 1. 数值精度格式总览

深度学习中常用的浮点/整数格式，决定了**内存占用**、**计算速度**和**精度损失**的权衡。

### 1.1 格式位宽分布

| 格式 | 总位数 | 符号位 | 指数位 | 尾数位 | 动态范围 | 最小精度 |
|------|--------|--------|--------|--------|----------|----------|
| FP64 | 64 | 1 | 11 | 52 | ±1.8×10³⁰⁸ | ~2.2×10⁻¹⁶ |
| FP32 | 32 | 1 | 8 | 23 | ±3.4×10³⁸ | ~1.2×10⁻⁷ |
| TF32 | 19 | 1 | 8 | 10 | ±3.4×10³⁸ | ~9.8×10⁻⁴ |
| BF16 | 16 | 1 | 8 | 7 | ±3.4×10³⁸ | ~7.8×10⁻³ |
| FP16 | 16 | 1 | 5 | 10 | ±65504 | ~9.8×10⁻⁴ |
| FP8 E4M3 | 8 | 1 | 4 | 3 | ±448 | ~0.002 |
| FP8 E5M2 | 8 | 1 | 5 | 2 | ±57344 | ~0.031 |
| INT8 | 8 | 1 | — | — | −128 ~ 127 | 1 |
| INT4 | 4 | 1 | — | — | −8 ~ 7 | 1 |
| INT2 | 2 | 1 | — | — | −2 ~ 1 | 1 |
| INT1 | 1 | — | — | — | 0 / 1 | 1 |

> **记忆口诀**：BF16 = FP32 的指数 + 砍掉一半尾数，动态范围不变；FP16 = 指数位只有 5 位，精度更高但动态范围窄。

---

## 2. 各精度格式详解

### 2.1 FP32（单精度浮点）

- **位宽**：32 bit / 4 bytes
- **地位**：训练黄金标准，精度基准
- **特点**：数值稳定，梯度更新准确
- **内存**：每个参数 4 bytes；70B 模型约 **280 GB**
- **适用场景**：全精度训练、精度敏感的科学计算

```
[1 符号][8 指数][23 尾数]
```

---

### 2.2 BF16（Brain Float 16）

- **位宽**：16 bit / 2 bytes
- **来源**：Google Brain 团队为 TPU 设计
- **特点**：
  - 与 FP32 **相同的指数位（8位）** → 动态范围与 FP32 完全一致
  - 尾数只有 7 位，精度略低
  - 从 FP32 转换 BF16 只需截断，不需要重新缩放
- **内存**：每个参数 2 bytes；70B 模型约 **140 GB**
- **硬件支持**：A100、H100、A10、RTX 3090+、TPU v2+
- **适用场景**：混合精度训练（主流方案）、大模型推理

```
[1 符号][8 指数][7 尾数]
          ↕ 与 FP32 相同
```

---

### 2.3 FP16（半精度浮点）

- **位宽**：16 bit / 2 bytes
- **特点**：
  - 指数位只有 5 位 → **动态范围极小**（±65504），容易发生溢出/下溢
  - 尾数 10 位，精度比 BF16 稍高
  - 训练时需要**损失缩放（Loss Scaling）** 来避免梯度消失
- **内存**：同 BF16，70B 模型约 **140 GB**
- **硬件支持**：V100、P100、所有支持半精度的 GPU
- **适用场景**：早期混合精度训练（现已被 BF16 取代）、推理

```
[1 符号][5 指数][10 尾数]
```

> **BF16 vs FP16 选择原则**：有 A100/H100 优先用 BF16；仅有 V100 或更老卡才用 FP16。

---

### 2.4 TF32（TensorFloat-32）

- **位宽**：存储 32 bit，计算使用 19 bit 精度
- **来源**：NVIDIA Ampere 架构引入（A100+）
- **特点**：
  - FP32 的指数 + FP16 的尾数（10 bit）
  - **自动在 Tensor Core 上使用**，无需代码修改
  - 计算速度约为 FP32 的 10x，精度损失极小
- **内存**：存储仍为 32 bit（4 bytes）
- **适用场景**：A100+ 上的透明加速，默认开启

---

### 2.5 FP8

- **位宽**：8 bit / 1 byte
- **两种子类型**：
  - **E4M3**（4 位指数 + 3 位尾数）：动态范围小（±448），精度较高 → 适合**前向传播激活值**
  - **E5M2**（5 位指数 + 2 位尾数）：动态范围大（±57344），精度低 → 适合**梯度计算**
- **内存**：每个参数 1 byte；70B 模型约 **70 GB**
- **硬件支持**：H100（Hopper 架构）、H20、Ada Lovelace（RTX 4090）
- **适用场景**：H100 上的高性能推理与训练，vLLM/TensorRT-LLM 支持 FP8

---

### 2.6 INT8

- **位宽**：8 bit / 1 byte
- **特点**：整数类型，不是浮点，需要**量化（Quantization）** 将浮点映射到整数
- **内存**：70B 模型约 **70 GB**（权重 INT8）
- **精度损失**：通常 < 1%，需校准（Calibration）
- **适用场景**：推理加速，LLM.int8()（bitsandbytes）

---

### 2.7 INT4 / GPTQ / AWQ

- **位宽**：4 bit，每个参数 0.5 bytes
- **内存**：70B 模型约 **35 GB**（纯 4bit 权重）
- **精度损失**：中等，依赖量化算法质量
- **适用场景**：消费级 GPU 部署大模型

---

### 2.8 更低位宽

| 格式 | 位宽 | 70B 模型内存（仅权重） | 说明 |
|------|------|----------------------|------|
| INT3 | 3 bit | ~26 GB | GGUF 支持，精度损失明显 |
| INT2 | 2 bit | ~18 GB | 实验性，质量较差 |
| 1-bit | 1 bit | ~9 GB | BitNet（微软），专门训练架构 |

---

## 3. 各精度内存对比

### 3.1 不同规模模型的显存需求（仅权重）

| 模型规模 | FP32 | BF16/FP16 | FP8/INT8 | INT4 | INT3 | INT2 |
|----------|------|-----------|----------|------|------|------|
| 7B | 28 GB | 14 GB | 7 GB | 3.5 GB | 2.6 GB | 1.8 GB |
| 13B | 52 GB | 26 GB | 13 GB | 6.5 GB | 4.9 GB | 3.3 GB |
| 30B | 120 GB | 60 GB | 30 GB | 15 GB | 11 GB | 7.5 GB |
| 70B | 280 GB | 140 GB | 70 GB | 35 GB | 26 GB | 18 GB |
| 405B | 1620 GB | 810 GB | 405 GB | 203 GB | 152 GB | 101 GB |

> **注**：实际推理需额外加上 KV Cache、激活值等，通常需要 **权重显存 × 1.2～1.5** 的总显存。

### 3.2 内存计算公式

```
显存(GB) = 参数量(B) × 每参数字节数
```

| 精度 | 每参数字节数 |
|------|------------|
| FP32 | 4 bytes |
| BF16 / FP16 | 2 bytes |
| FP8 / INT8 | 1 byte |
| INT4 | 0.5 bytes |
| INT3 | 0.375 bytes |
| INT2 | 0.25 bytes |

---

## 4. 量化方法详解

量化（Quantization）是将高精度浮点数映射到低位宽整数/浮点的技术，分为**训练后量化（PTQ）** 和**量化感知训练（QAT）**两大类。

### 4.1 量化基本原理

**线性量化公式**：

```
量化：Q(x) = round(x / scale + zero_point)
反量化：x̂  = (Q(x) - zero_point) × scale

其中：
  scale = (max - min) / (2^bits - 1)
  zero_point = round(-min / scale)
```

**对称量化**（zero_point = 0）：
```
Q(x) = round(x / scale)
scale = max(|x|) / (2^(bits-1) - 1)
```

---

### 4.2 训练后量化（PTQ）

不需要重新训练，直接对训练好的模型进行量化。

#### LLM.int8()

- **论文**：Dettmers et al., 2022
- **工具**：`bitsandbytes` 库
- **原理**：
  - 发现 LLM 中存在**离群值（Outlier）**，这些极大值无法被 INT8 很好地表示
  - 对包含离群值的特征维度保持 FP16，其余维度量化为 INT8
  - 称为**混合精度分解（Mixed-Precision Decomposition）**
- **特点**：推理几乎无精度损失，但速度提升有限（有矩阵分解开销）

```python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf",
    load_in_8bit=True,   # 使用 bitsandbytes LLM.int8()
    device_map="auto"
)
```

---

#### GPTQ（Generative Pre-trained Transformer Quantization）

- **论文**：Frantar et al., 2022
- **工具**：`auto-gptq`、`transformers` 集成
- **原理**：
  - 基于 OBQ（Optimal Brain Quantization）框架
  - 逐层量化，利用 **Hessian 矩阵**调整权重，补偿量化误差
  - 需要少量校准数据（~128 样本）
  - 支持 2/3/4/8 bit
- **特点**：精度损失小，推理速度快（ExLlama 等后端优化良好）

```python
from transformers import AutoModelForCausalLM, GPTQConfig

gptq_config = GPTQConfig(bits=4, dataset="c4", tokenizer=tokenizer)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=gptq_config
)
```

---

#### AWQ（Activation-aware Weight Quantization）

- **论文**：Lin et al., 2023
- **工具**：`autoawq` 库
- **原理**：
  - 发现只有约 **1% 的权重通道**对模型输出影响显著（对应激活值大的通道）
  - 对重要通道**保护**（scale up），其余通道正常量化
  - 无需 Hessian 矩阵，速度更快
  - 支持 4/3/2 bit
- **特点**：量化速度比 GPTQ 快，精度相当甚至更好

```python
from awq import AutoAWQForCausalLM

model = AutoAWQForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")
quant_config = {"zero_point": True, "q_group_size": 128, "w_bit": 4, "version": "GEMM"}
model.quantize(tokenizer, quant_config=quant_config)
```

---

#### GGUF / GGML（llama.cpp 量化格式）

- **工具**：`llama.cpp`、`ollama`
- **原理**：
  - 自定义量化格式，支持多种位宽混合
  - 常见格式：Q4_K_M、Q4_K_S、Q5_K_M、Q8_0 等
  - 后缀含义：Q=量化，4=bits，K=K-quant（分组），M/S=Medium/Small（精度等级）
- **特点**：CPU 推理效率极高，适合本地部署

| GGUF 格式 | 位宽 | 70B 内存 | 质量 |
|-----------|------|----------|------|
| Q2_K | ~2.5 bit | ~26 GB | 较差 |
| Q4_K_S | ~4.3 bit | ~37 GB | 较好 |
| Q4_K_M | ~4.5 bit | ~39 GB | 好 |
| Q5_K_M | ~5.5 bit | ~48 GB | 很好 |
| Q6_K | ~6.6 bit | ~58 GB | 接近原始 |
| Q8_0 | ~8.5 bit | ~74 GB | 几乎无损 |

---

#### SmoothQuant

- **论文**：Xiao et al., 2022
- **原理**：
  - 量化难点：激活值的离群值比权重更大，INT8 量化激活误差大
  - 核心思路：将激活值的量化难度**迁移**到权重上（per-channel scaling）
  - `Y = (X diag(s)⁻¹)(diag(s) W)` —— 缩放激活值、反缩放权重
- **特点**：权重和激活值都可以 INT8，推理延迟真正降低（W8A8）

---

### 4.3 量化感知训练（QAT）

在训练阶段模拟量化误差，使模型适应量化精度。

#### BitNet / 1-bit LLM

- **论文**：Wang et al., 2023（BitNet），Ma et al., 2024（BitNet b1.58）
- **原理**：
  - 权重只有 {-1, 0, +1}（1.58 bit），通过 AbsMax 量化
  - 激活值保持 INT8
  - 矩阵乘法退化为加减法，无需乘法器
- **特点**：需要从头训练，现有模型不能直接转换；能效极高

#### GPTQ-QAT / LoRA-QAT

- 在量化后的模型上继续微调（通常配合 LoRA）
- 恢复量化带来的精度损失

---

### 4.4 量化粒度

| 粒度 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| Per-tensor | 整个张量共享 scale | 实现简单，速度快 | 精度损失大 |
| Per-channel | 每个输出通道独立 scale | 精度好（权重常用） | 稍复杂 |
| Per-group | 每 N 个元素共享 scale（常 N=128） | 精度与效率折中 | GPTQ/AWQ 默认 |
| Per-token | 每个 token 独立 scale（激活值常用） | 处理离群值效果好 | 在线计算 scale |

---

## 5. 混合精度训练（Mixed Precision Training）

现代大模型训练的标准方案，兼顾精度与效率。

### 5.1 经典 FP16/BF16 混合精度流程

```
前向传播：BF16/FP16（快）
         ↓
损失计算：FP32（精确）
         ↓
反向传播：BF16/FP16（快）
         ↓
优化器更新：FP32 主权重（精确）
           ↓（转换）
模型权重：BF16/FP16（存储节省）
```

**内存组成（以 7B BF16 训练为例）**：

| 组件 | 精度 | 内存 |
|------|------|------|
| 模型权重 | BF16 | 14 GB |
| 梯度 | BF16 | 14 GB |
| 优化器状态（AdamW） | FP32 × 2 | 56 GB |
| **合计** | — | **~84 GB** |

---

## 6. 推理部署精度选择指南

```
推理场景精度选择树：

H100/H20 可用？
├── Yes → FP8（最佳性能）或 BF16（最高精度）
└── No → A100/A10/RTX 4090？
    ├── Yes → BF16 推理 或 INT8（内存受限时）
    └── No → 消费级 GPU / 无 GPU？
        ├── 消费级 GPU（24GB）→ INT4 (AWQ/GPTQ)，可跑 13B 模型
        ├── 消费级 GPU（8GB）→ INT4，可跑 7B 模型
        └── CPU → GGUF Q4/Q5，llama.cpp
```

### 6.1 各部署方案对比

| 方案 | 精度格式 | 工具 | 适合场景 |
|------|----------|------|----------|
| BF16 全精度推理 | BF16 | vLLM, HF | A100+ 服务端，高精度要求 |
| FP8 推理 | FP8 E4M3 | vLLM, TensorRT-LLM | H100，高吞吐量 |
| INT8 量化 | INT8 | bitsandbytes, TensorRT | 内存节省 50%，精度损失小 |
| INT4 GPTQ | INT4 | AutoGPTQ, vLLM | 消费级 GPU，节省 75% 内存 |
| INT4 AWQ | INT4 | AutoAWQ, vLLM | 消费级 GPU，量化速度快 |
| GGUF CPU | 2-8 bit | llama.cpp, Ollama | 本地 CPU/Mac M 系列 |

---

## 7. 常用工具生态

| 工具 | 支持格式 | 特点 |
|------|---------|------|
| [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) | INT8, INT4 (NF4) | transformers 深度集成，`load_in_8bit/4bit` |
| [AutoGPTQ](https://github.com/AutoGPTQ/AutoGPTQ) | GPTQ 2/3/4/8bit | 工业级 GPTQ 实现 |
| [AutoAWQ](https://github.com/casper-hansen/AutoAWQ) | AWQ 4bit | 速度快，精度好 |
| [llama.cpp](https://github.com/ggerganov/llama.cpp) | GGUF 2-8bit | CPU 推理，跨平台 |
| [vLLM](https://github.com/vllm-project/vllm) | FP8, AWQ, GPTQ, INT8 | 高性能服务端推理 |
| [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | FP8, INT8, INT4 | NVIDIA 官方，H100 最优 |
| [Quanto](https://github.com/huggingface/quanto) | INT2/4/8, FP8 | HF 官方，纯 PyTorch |
| [EETQ](https://github.com/NetEase-FuXi/EETQ) | INT8 | 快速 W8A16 量化 |

---

## 8. 精度选择总结

| 需求 | 推荐精度 | 原因 |
|------|----------|------|
| 全精度训练基准 | FP32 | 数值最稳定 |
| 混合精度训练（A100+）| BF16 + FP32 优化器 | 与 FP32 等动态范围，训练稳定 |
| 混合精度训练（V100）| FP16 + 损失缩放 | V100 不支持 BF16 |
| H100 推理 | FP8 | 2x 吞吐量提升 |
| A100 推理 | BF16 | 精度最高 |
| 内存受限推理 | INT8 | 精度损失 <1% |
| 消费级 GPU | INT4 (AWQ/GPTQ) | 内存节省 75% |
| 本地 CPU 部署 | GGUF Q4_K_M | 效率与质量最佳折中 |

---

## 参考资料

- [Dettmers et al., LLM.int8() (2022)](https://arxiv.org/abs/2208.07339)
- [Frantar et al., GPTQ (2022)](https://arxiv.org/abs/2210.17323)
- [Lin et al., AWQ (2023)](https://arxiv.org/abs/2306.00978)
- [Xiao et al., SmoothQuant (2022)](https://arxiv.org/abs/2211.10438)
- [Ma et al., Era of 1-bit LLMs (2024)](https://arxiv.org/abs/2402.17764)
- [HuggingFace 量化文档](https://huggingface.co/docs/transformers/quantization/overview)
