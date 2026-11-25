---
title: CLIP - Learning Transferable Visual Models From Natural Language Supervision
date: 2021-02-26
tags: [clip, vision-language, 对比学习, 零样本]
---

# CLIP - Learning Transferable Visual Models From Natural Language Supervision

> 论文链接: [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
> GitHub: [openai/CLIP](https://github.com/openai/CLIP)
> OpenAI Blog: [CLIP](https://openai.com/index/clip/)

## 概述

CLIP（Contrastive Language-Image Pre-Training）是 OpenAI 提出的视觉语言预训练模型，通过对比学习在 4 亿图像-文本对上训练，实现了强大的零样本迁移能力。

**核心贡献**: 在 ImageNet 上零样本达到 ResNet-50 的准确率，无需使用任何训练样本。

## Abstract

CLIP (Contrastive Language-Image Pre-Training) is a neural network trained on a variety of (image, text) pairs. It can be instructed in natural language to predict the most relevant text snippet, given an image, without directly optimizing for the task, similarly to the zero-shot capabilities of GPT-2 and 3. We found CLIP matches the performance of the original ResNet50 on ImageNet "zero-shot" without using any of the original 1.28M labeled examples, overcoming several major challenges in computer vision.

CLIP（对比语言-图像预训练）是一种在多种（图像，文本）对上训练的神经网络。它可以通过自然语言指令，在不直接针对该任务进行优化的情况下，根据图像预测最相关的文本片段，这与 GPT-2 和 GPT-3 的零样本能力类似。我们发现，CLIP 在未使用 ImageNet 原始 128 万标注样本中的任何一个的情况下，其"零样本"性能即可媲美原始的 ResNet50，从而克服了计算机视觉领域的若干重大挑战。

## 核心思想

### 传统方法的局限

传统计算机视觉系统存在以下问题：

1. 只能预测**固定的预定义类别**
2. 扩展新类别需要**额外标注数据**
3. 监督形式受限，泛化能力不足

### CLIP 的解决方案

- 从**原始文本**直接学习图像表示
- 利用更广泛的监督来源
- 通过自然语言引用视觉概念，实现零样本迁移

## 模型架构

### 双编码器结构

```
Image Encoder (ViT / ResNet)     Text Encoder (Transformer)
        ↓                              ↓
    Image Features                Text Features
        ↓                              ↓
        └──────────→ Contrastive ←──────────
                     Learning
```

### 编码器选择

| 图像编码器 | 说明 |
|------------|------|
| ResNet-50 | CNN 架构 |
| ViT-B/32 | Vision Transformer |
| ViT-B/16 | 更大的 ViT |
| ViT-L/14 | 最大版本 |

### 预训练目标

**对比学习（Contrastive Learning）**:

- 预测哪个 caption 对应哪个 image
- 正样本：匹配的图像-文本对
- 负样本：不匹配的图像-文本对

## 训练数据

### WIT 数据集

- **WebImageText** (WIT)
- 4 亿 (image, text) 对
- 从互联网收集
- 涵盖广泛视觉概念

## 零样本迁移

### 工作原理

```python
# 零样本分类示例
image_features = model.encode_image(image)
text_features = model.encode_text(["a dog", "a cat", "a bird"])
probs = (image_features @ text_features.T).softmax(dim=-1)
```

### Prompt Engineering

使用 prompt template 提升性能：

```
"a photo of a {label}"
"a photo of a {label}, a type of pet"
```

## 性能表现

### ImageNet 零样本

| 模型 | ImageNet Top-1 |
|------|----------------|
| ResNet-50 (监督) | 76.2% |
| CLIP ViT-B/32 (零样本) | 63.2% |
| CLIP ViT-B/16 (零样本) | 68.7% |
| CLIP ViT-L/14 (零样本) | 75.5% |

### 跨任务迁移

在 30+ 数据集上测试：

| 任务类型 | 数据集 | 零样本表现 |
|----------|--------|------------|
| OCR | SVHN | 竞争力强 |
| 视频动作识别 | UCF101 | 良好 |
| 地理定位 | Country211 | 良好 |
| 细粒度分类 | Flowers102 | 竞争力强 |

## 关键发现

### 1. 零样本迁移能力

- 无需任务特定训练
- 自然语言描述即可定义任务
- 跨领域泛化能力强

### 2. 对比学习效率

- 简单的预训练任务
- 高效且可扩展
- 从零开始学习 SOTA 表示

### 3. 数据规模的重要性

- 4 亿数据对是关键
- 数据多样性提升泛化
- 网络数据的有效利用

## 应用场景

### 图像分类

```python
import clip
model, preprocess = clip.load("ViT-B/32")

image = preprocess(Image.open("image.jpg"))
text = clip.tokenize(["a dog", "a cat", "a bird"])
image_features = model.encode_image(image)
text_features = model.encode_text(text)
```

### 图像-文本检索

- 图像搜索文本
- 文本搜索图像

### 作为其他模型的组件

- Stable Diffusion 的文本编码器
- DALL-E 的图像理解模块

## 局限性

### 1. 细粒度分类

在某些细粒度任务上表现不佳：
- 区分相似车型
- 区分特定花卉品种

### 2. 抽象概念

难以理解抽象概念：
- 计数（"几张照片"）
- 空间关系（"左边"、"右边"）

### 3. 分布外数据

对训练分布外的数据敏感：
- 真实世界噪声数据
- 长尾类别

## 影响与后续工作

### 直接影响

- 开启 Vision-Language Pre-training 热潮
- 成为多模态模型的基础组件
- Stable Diffusion、DALL-E 等都使用 CLIP

### 后续模型

| 模型 | 改进点 |
|------|--------|
| ALIGN | 更大规模数据 |
| BLIP | 数据清洗+生成 |
| ViLT | 无卷积架构 |
| SigLIP | sigmoid 损失 |

## 参考资源

- 论文: [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- GitHub: [openai/CLIP](https://github.com/openai/CLIP)
- Huggingface: [openai/clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14)