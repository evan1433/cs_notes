---
title: GPU 规格参数与性能对比
description: NVIDIA 与华为昇腾主流 AI GPU 规格参数详细对比
tags:
  - gpu
  - nvidia
  - ascend
  - ai-hardware
date: 2026-06-04
---

# GPU 规格参数与性能对比

## 一、NVIDIA 数据中心/推理卡

### 1.1 基础规格总览

| 参数              | T4           | A10            | L4             | L40S           | A100 80G    | H100 80G       | H200           | B200            |
| --------------- | ------------ | -------------- | -------------- | -------------- | ----------- | -------------- | -------------- | --------------- |
| **架构**          | Turing       | Ampere         | Ada Lovelace   | Ada Lovelace   | Ampere      | Hopper         | Hopper         | Blackwell       |
| **制程**          | 12 nm        | 8 nm (Samsung) | 5 nm (TSMC 4N) | 5 nm (TSMC 4N) | 7 nm        | 4 nm (TSMC 4N) | 4 nm (TSMC 4N) | 4 nm (TSMC 4NP) |
| **显存**          | 16 GB GDDR6  | 24 GB GDDR6    | 24 GB GDDR6X   | 48 GB GDDR6X   | 80 GB HBM2e | 80 GB HBM3     | 141 GB HBM3e   | 192 GB HBM3e    |
| **显存带宽**        | 320 GB/s     | 600 GB/s       | 300 GB/s       | 864 GB/s       | 2.0 TB/s    | 3.35 TB/s      | 4.8 TB/s       | 8.0 TB/s        |
| **FP32 算力**     | 8.1 TFLOPS   | 31.2 TFLOPS    | 30.3 TFLOPS    | 90.5 TFLOPS    | 19.5 TFLOPS | 51 TFLOPS      | 67 TFLOPS      | 90 TFLOPS       |
| **FP16 算力**     | 65 TFLOPS    | 125 TFLOPS     | 121 TFLOPS     | 362 TFLOPS     | 312 TFLOPS  | 989 TFLOPS     | 989 TFLOPS     | 2,250 TFLOPS    |
| **FP16 稀疏**     | —            | 250 TFLOPS     | 242 TFLOPS     | 733 TFLOPS     | 624 TFLOPS  | 1,979 TFLOPS   | 1,979 TFLOPS   | 4,500 TFLOPS    |
| **INT8 算力**     | 130 TOPS     | 250 TOPS       | 242 TOPS       | 724 TOPS       | 624 TOPS    | 1,979 TOPS⁺    | 1,979 TOPS⁺    | 4,500 TOPS⁺     |
| **FP8 算力**      | —            | —              | —              | —              | —           | 1,979 TFLOPS   | 1,979 TFLOPS   | 4,500 TFLOPS    |
| **FP4 算力**      | —            | —              | —              | —              | —           | —              | —              | 9,000 TFLOPS    |
| **TDP 功耗**      | 70 W         | 150 W          | 72 W           | 350 W          | 300 W       | 350 W (SXM)    | 700 W          | 1,000 W         |
| **NVLink 带宽**   | —            | —              | —              | —              | 600 GB/s    | 900 GB/s       | 900 GB/s       | 1.8 TB/s        |
| **PCIe**        | PCIe 3.0 x16 | PCIe 4.0 x16   | PCIe 4.0 x16   | PCIe 4.0 x16   | PCIe 4.0    | PCIe 5.0       | PCIe 5.0       | PCIe 6.0        |
| **CUDA 核心**     | 2,560        | 9,216          | 7,680          | 18,176         | 6,912       | 16,896         | 16,896         | 18,432          |
| **Tensor Core** | 320          | 288            | 240            | 568            | 432         | 528            | 528            | —               |

> ⁕ H100/B200 的 INT8 算力通过 FP8 Tensor Core 等效换算；稀疏算力为密集算力的约 2 倍。
> T4 实际有 16GB 版本，部分云厂商提供 14GB 可用显存的分区配置。

### 1.2 中国特供版

| 参数 | A800 | H800 | H20 标准款 | H20 大显存款 |
|------|------|------|-----------|-------------|
| **架构** | Ampere | Hopper | Hopper | Hopper |
| **显存** | 80 GB HBM2e | 80 GB HBM3 | 96 GB HBM3 | 141 GB HBM3e |
| **显存带宽** | 2.0 TB/s | 3.35 TB/s | 4.0 TB/s | 4.8 TB/s |
| **FP16 算力** | 312 TFLOPS | 989 TFLOPS | 148 TFLOPS | 148 TFLOPS |
| **INT8 算力** | 624 TOPS | 1,979 TOPS | 296 TOPS | 296 TOPS |
| **NVLink 带宽** | 400 GB/s ⚠️ | 400 GB/s ⚠️ | 900 GB/s | 900 GB/s |
| **TDP 功耗** | 300 W | 350 W | — | — |

> ⚠️ A800/H800 的 NVLink 带宽从 600/900 GB/s 降至 400 GB/s，对大规模分布式训练性能影响显著。
> H20 算力大幅削减但保留 NVLink 带宽，适用于对互联带宽敏感的场景。

## 二、华为昇腾（Ascend）系列

### 2.1 基础规格总览

| 参数 | 昇腾 310P | 昇腾 910 | 昇腾 910B | 昇腾 910C | 昇腾 950PR | 昇腾 970 |
|------|----------|----------|----------|----------|----------|----------|
| **架构** | Da Vinci (mini) | Da Vinci (max) | Da Vinci (max) | Da Vinci (Chiplet) | Da Vinci (SIMD+SIMT) | Da Vinci (SIMD+SIMT) |
| **制程** | 12 nm | 7 nm+ EUV | 7 nm DUV | 7 nm N+2 (中芯国际) | — | N+3 |
| **内存** | 4 GB LPDDR4X | 32 GB HBM2 | ~64 GB HBM | ~64 GB HBM | 128 GB (HiBL 1.0) | 288 GB |
| **内存带宽** | — | ~1.2 TB/s | ~900 GB/s | — | — | 最高 14.4 TB/s |
| **FP16 算力** | 88 TFLOPS | 256 TFLOPS | 320 TFLOPS | 800 TFLOPS | 1,000 TFLOPS (FP8) | — |
| **INT8 算力** | 176 TOPS | 512 TOPS | 640 TOPS | — | — | 8,000 TOPS (FP4) |
| **TDP 功耗** | 86 W | 310 W | 310 W | ~350-450 W | — | — |
| **互联方式** | — | HCCS | HCCS | HCCS | — | — |
| **互联带宽** | — | — | 392 GB/s (8卡总) | 784 GB/s | — | 4.0 TB/s |
| **定位** | 边缘推理 | 数据中心训练 | 数据中心训练 | 大规模训练 | 推理 Prefill | 下一代旗舰 |

### 2.2 昇腾与 NVIDIA 关键差异

| 对比维度 | 昇腾系列 | NVIDIA 系列 |
|---------|---------|------------|
| **软件生态** | CANN + MindSpore，PyTorch 兼容持续优化 | CUDA 完整生态，行业事实标准 |
| **互联拓扑** | HCCS 对等拓扑，单卡间带宽 56 GB/s | NVSwitch 全网状拓扑，单卡间 400+ GB/s |
| **精度支持** | FP16/INT8 为主，950 起支持 FP8/FP4 | 全精度覆盖，FP8 自 Hopper 起原生支持 |
| **集群方案** | Atlas 900 / CloudMatrix 384 | DGX / HGX |
| **国产替代** | ✅ 自主可控 | ❌ 受出口管制影响 |

## 三、性能梯队划分

### 3.1 AI 训练算力梯队（FP16 密集算力）

```
第一梯队 ── B200 (2,250 TFLOPS) │ H200/H100 (989 TFLOPS)
第二梯队 ── A100 (312 TFLOPS)  │ L40S (362 TFLOPS) │ 昇腾910C (800 TFLOPS)
第三梯队 ── A10 (125 TFLOPS)   │ L4 (121 TFLOPS)   │ 昇腾910B (320 TFLOPS)
第四梯队 ── T4 (65 TFLOPS)     │ 昇腾310P (88 TFLOPS)
```

### 3.2 推理能效比（INT8 算力 / TDP）

| GPU     | INT8 算力    | TDP   | 能效比 (TOPS/W) |
| ------- | ---------- | ----- | ------------ |
| L4      | 242 TOPS   | 72 W  | **3.36**     |
| T4      | 130 TOPS   | 70 W  | **1.86**     |
| H100    | 1,979 TOPS | 350 W | **5.65**     |
| A100    | 624 TOPS   | 300 W | **2.08**     |
| A10     | 250 TOPS   | 150 W | **1.67**     |
| 昇腾 910B | 640 TOPS   | 310 W | **2.06**     |
| 昇腾 310P | 176 TOPS   | 86 W  | **2.05**     |

### 3.3 显存容量 vs 带宽

| GPU      | 显存     | 带宽           | 适用模型规模            |
| -------- | ------ | ------------ | ----------------- |
| T4       | 16 GB  | 320 GB/s     | ≤ 7B 推理           |
| A10 / L4 | 24 GB  | 600/300 GB/s | 7B-13B 推理         |
| L40S     | 48 GB  | 864 GB/s     | 13B-34B 推理        |
| A100     | 80 GB  | 2.0 TB/s     | 70B 训练 / 34B 推理   |
| H100     | 80 GB  | 3.35 TB/s    | 70B 训练 / 34B 推理   |
| H200     | 141 GB | 4.8 TB/s     | 70B+ 训练 / 120B 推理 |
| B200     | 192 GB | 8.0 TB/s     | 175B+ 训练 / 推理     |
| 昇腾 910B  | ~64 GB | ~900 GB/s    | 7B-34B 训练         |
| 昇腾 910C  | ~64 GB | —            | 70B 训练            |

## 四、选型建议

| 场景 | 推荐 GPU | 理由 |
|------|---------|------|
| 轻量推理（≤ 7B） | T4 / L4 | 低功耗、高性价比，L4 能效比更优 |
| 中等推理（7B-13B） | A10 / L4 | 24GB 显存覆盖主流小模型 |
| 中等训练/微调 | A10 / L40S | A10 性价比好，L40S 显存翻倍 |
| 大模型训练（70B） | A100 80G / H100 | H100 算力 3 倍于 A100，首选预算允许时 |
| 超大规模训练 | H100/H200 集群 | NVLink 互联带宽优势明显 |
| 国产替代方案 | 昇腾 910B/910C | 自主可控，算力接近 A100，生态持续完善 |
| 边缘推理 | 昇腾 310P / T4 | 低功耗部署，310P 国产方案 |

## 五、参考来源

- [NVIDIA 官方 GPU 规格](https://www.nvidia.cn/data-center/)
- [英伟达 GPU 参数速查表 - CHEGVA](https://chegva.com/6562.html)
- [NVIDIA GPU 全面对比：A 系 / H 系 / B 系](https://iris.findtruman.io/web/ai-hardware/api/2025-12-16/nvidia-gpu-comparison-a-h-b-series)
- [华为昇腾系列 AI 芯片详细参数对比（2025-2028）](https://www.eet-china.com/mp/a486527.html)
- [Ascend 910B 服务器深度解析](https://blog.csdn.net/gs80140/article/details/155558238)
