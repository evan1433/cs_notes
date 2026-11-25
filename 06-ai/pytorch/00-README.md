# PyTorch 知识体系

本文档是 PyTorch 使用指南的总览，涵盖了从入门到进阶的完整知识体系。

## 📚 知识体系结构

### 一、PyTorch 基础

#### 1.1 张量操作
- [[01-vectors]] - 多维张量基础概念与理解
- [[02-tensor-operations]] - 张量的创建、索引、切片、变形等操作

#### 1.2 自动求导
- [[03-autograd]] - 计算图与自动微分机制

#### 1.3 数据处理
- [[04-data-loading]] - 数据集定义与数据加载器

### 二、神经网络基础

#### 2.1 核心组件
- [[05-nn-module]] - 神经网络模块基类
- [[06-linear]] - 全连接层（线性层）

#### 2.2 激活函数
- [[07-activation-functions]] - ReLU、Sigmoid、Tanh 等

#### 2.3 损失函数
- [[08-loss-functions]] - 交叉熵、MSE、CTC 等

#### 2.4 优化器
- [[09-optimizers]] - SGD、Adam、AdamW 等

### 三、经典网络架构

#### 3.1 多层感知机
- [[10-mlp]] - 最基础的神经网络结构

#### 3.2 循环神经网络
- [[11-lstm]] - 长短时记忆网络

#### 3.3 注意力机制
- [[12-transformer]] - Transformer 架构详解

### 四、训练与实践

#### 4.1 训练流程
- [[06-ai/pytorch/13-training-pipeline|13-training流程]] - 从数据到模型的完整训练流程

## 📖 学习顺序

| 序号 | 文件名 | 主题 | 说明 |
|:----:|--------|------|------|
| 00 | `00-README.md` | 知识体系总览 | 整体架构与学习路径 |
| 01 | `01-vectors.md` | 张量概念 | 多维张量基础理解 |
| 02 | `02-tensor-operations.md` | 张量操作 | 创建、索引、运算 |
| 03 | `03-autograd.md` | 梯度计算 | 计算图与反向传播 |
| 04 | `04-data-loading.md` | 数据处理 | 数据集与数据加载器 |
| 05 | `05-nn-module.md` | 模型构建 | 神经网络基类 |
| 06 | `06-linear.md` | 全连接层 | 线性层详解 |
| 07 | `07-activation-functions.md` | 激活函数 | ReLU、GELU 等 |
| 08 | `08-loss-functions.md` | 损失函数 | CrossEntropy、MSE |
| 09 | `09-optimizers.md` | 优化器 | Adam、SGD、学习率调度 |
| 10 | `10-mlp.md` | MLP | 基础神经网络实战 |
| 11 | `11-lstm.md` | LSTM | 序列建模 |
| 12 | `12-transformer.md` | Transformer | 注意力架构 |
| 13 | `13-training流程.md` | 训练流程 | 端到端实战 |

## 🎯 学习路径建议

### 入门路径（第1-2周）
1. [[01-vectors]] → 理解数据结构
2. [[02-tensor-operations]] → 掌握张量操作
3. [[03-autograd]] → 理解梯度计算
4. [[04-data-loading]] → 掌握数据处理
5. [[05-nn-module]] → 学会构建模型

### 进阶路径（第3-4周）
1. [[06-linear]] + [[07-activation-functions]] → 理解网络层
2. [[08-loss-functions]] + [[09-optimizers]] → 完成训练流程
3. [[10-mlp]] → 动手实现第一个模型
4. [[06-ai/pytorch/13-training-pipeline|13-training流程]] → 掌握端到端训练

### 高级路径（第5-8周）
1. [[11-lstm]] → 序列模型
2. [[12-transformer]] → 注意力机制
3. 实战项目 → 巩固知识

## 💡 使用建议

1. **结合实践**：每个概念都要动手写代码验证
2. **循序渐进**：按照编号顺序学习，不要跳跃
3. **记录问题**：遇到问题及时记录并解决
4. **项目驱动**：通过实际项目巩固知识

## 🔗 官方资源

- [PyTorch 官方文档](https://pytorch.org/docs/)
- [PyTorch 官方教程](https://pytorch.org/tutorials/)
- [PyTorch GitHub](https://github.com/pytorch/pytorch)