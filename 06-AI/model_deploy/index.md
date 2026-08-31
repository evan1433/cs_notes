---
title: 模型部署
description: LLM 推理服务框架、量化技术与国产算力适配的部署实践笔记
tags:
  - ai
  - llm
  - inference
  - deployment
date: 2026-08-28
---

# 模型部署

> 覆盖大模型推理服务化的三个核心议题：推理框架选型（vLLM / SGLang）、量化技术、以及昇腾等国产算力的适配方案。

## 学习路径

1. [[vllm|vLLM 推理服务框架]] —— PagedAttention 原理、`vllm serve` 配置、分布式推理与量化
2. [[sglang|SGLang 推理服务框架]] —— RadixAttention 前缀缓存、launch_server 部署
3. [[quantization|模型量化]] —— AWQ 等量化方案与 Qwen 系列的量化实践
4. 昇腾生态 —— [[vllm-ascend]] 与 [[Ascend 昇腾|昇腾环境]] 的 NPU 适配

## 笔记索引

| 笔记 | 类型 | 状态 | 说明 |
|------|------|------|------|
| [[vllm\|vLLM 推理服务框架]] | 概念+速查 | ✅ 完整 | PagedAttention、部署、调优 |
| [[sglang\|SGLang 推理服务框架]] | 概念+速查 | ✅ 完整 | RadixAttention、结构化输出 |
| [[quantization\|模型量化]] | 速查 | 🚧 草稿 | 量化方案链接集 |
| [[vllm-ascend]] | 速查 | 🕳 待补 | vLLM 昇腾版本文档链接 |
| [[vLLM-Omni]] | 速查 | 🕳 待补 | vLLM-Omni 文档链接 |
| [[Ascend 昇腾\|昇腾环境]] | 教程 | 🚧 草稿 | CANN 安装与 NPU 验证 |
| [[Inference Engine\|推理引擎对比]] | 速查 | 🕳 待补 | 框架文档入口集合 |

## 相关目录

- [[../llm/index|LLM]]
- [[../gpu-specs|GPU 规格对比]]
