---
title: BitDance - Scaling Autoregressive Generative Models with Binary Tokens
date: 2026-02-15
tags: [vlm, 图像生成, 自回归, diffusion]
---

# BitDance - Scaling Autoregressive Generative Models with Binary Tokens

> 论文链接: [arXiv:2602.14041](https://arxiv.org/abs/2602.14041)
> GitHub: [shallowdream204/BitDance](https://github.com/shallowdream204/BitDance)

## 概述

BitDance 是一种可扩展的自回归（AR）图像生成器，通过预测**二进制视觉 tokens**而非传统的 codebook 索引，实现了高效的高分辨率图像生成。

**核心贡献**: 在 ImageNet 256x256 上达到 FID 1.24，是 AR 模型中的最佳结果。

## 核心创新

### 1. 二进制视觉 Tokens

传统 AR 模型使用 codebook 索引（如 VQ-VAE 的离散编码），而 BitDance 使用**二进制 latents**：

- 每个 token 可表示 **2^256 种状态**
- 紧凑且高度表达的离散表示
- 高熵二进制表示，信息密度更高

### 2. Binary Diffusion Head

由于 token 空间巨大（2^256），标准分类（softmax）难以采样。BitDance 使用**二进制扩散头**：

- 不用 softmax 预测索引
- 使用连续空间扩散生成二进制 tokens
- 解决大 token 空间的采样难题

### 3. Next-Patch Diffusion

新的解码方法，**并行预测多个 tokens**：

- 高准确度的并行预测
- 大幅加速推理速度
- 相比传统 AR 的逐 token 生成更高效

## 性能表现

### ImageNet 256x256

| 模型 | FID | 参数量 |
|------|-----|--------|
| BitDance | **1.24** | 260M |
| 其他 AR 模型 | > 1.5 | 更大 |

**关键优势**:
- AR 模型中最佳 FID
- 参数效率高（260M vs 1.4B）

### 与 SOTA 对比

| 对比项 | BitDance | SOTA AR |
|--------|----------|---------|
| 参数量 | 260M | 1.4B |
| 参数效率 | **5.4x 更少** | - |
| 推理速度 | **8.7x 更快** | - |

### Text-to-Image 生成

- 大规模多模态 tokens 训练
- 高分辨率、逼真图像生成
- 强性能和良好的扩展性

### 1024x1024 图像生成

| 对比项 | BitDance | Prior AR |
|--------|----------|----------|
| 速度提升 | **> 30x** | - |

## 技术细节

### 二进制 Token 表示

```
传统方法: codebook index (有限状态，如 8192)
BitDance: binary latent (2^256 状态)
```

### Binary Diffusion Head

```
传统 AR: softmax → 预测 codebook index
BitDance: diffusion → 生成 binary tokens
```

### Next-Patch Diffusion

- 并行解码多个 patches
- 保持高准确度
- 显著减少推理步数

## 模型版本

| 模型 | 参数量 | 说明 |
|------|--------|------|
| BitDance-14B-16x | 15B | 16 倍下采样 |
| BitDance-14B-64x | 15B | 64 倍下采样 |

## 关键优势

### 1. 表达能力强

- 2^256 状态 vs 传统 codebook 的有限状态
- 更高的信息密度

### 2. 生成效率高

- 并行 token 预测
- 推理速度大幅提升

### 3. 参数效率好

- 更少参数达到更好性能
- 良好的扩展性

## 与其他方法对比

| 方法类型 | 代表模型 | 特点 |
|----------|----------|------|
| 传统 AR | VQ-GAN | 逐 token 生成，慢 |
| 并行 AR | Parallel AR | 并行但参数大 |
| Diffusion | Stable Diffusion | 高质量但迭代多 |
| **BitDance** | - | AR + Diffusion，快且高效 |

## 应用场景

### 1. Text-to-Image

- 高分辨率图像生成
- 逼真细节
- 快速生成

### 2. ImageNet 类条件生成

- 最佳 FID
- 高效训练

## 局限性

- 二进制表示需要特殊处理
- Diffusion head 增加训练复杂度
- 大规模训练资源需求

## 影响与意义

### 技术创新

- 打破传统 AR 模型的 token 表示限制
- 结合 AR 和 Diffusion 的优势
- 开辟新的生成模型方向

### 实用价值

- 高分辨率图像快速生成
- 参数效率高，部署友好
- 开源代码和模型

## 参考资源

- 论文: [arXiv:2602.14041](https://arxiv.org/abs/2602.14041)
- GitHub: [shallowdream204/BitDance](https://github.com/shallowdream204/BitDance)
- Huggingface: [shallowdream204/BitDance-14B-16x](https://huggingface.co/shallowdream204/BitDance-14B-16x)