---
title: vLLM 推理服务框架
description: vLLM 高性能 LLM 推理与部署框架全面解析：PagedAttention 原理、安装部署、vllm serve 配置、分布式推理、量化与性能调优
tags:
  - ai
  - llm
  - inference
  - vllm
  - deployment
date: 2026-08-24
aliases:
  - vllm
  - vLLM
---
# vLLM 推理服务框架

## 1. 概述

vLLM 是由 UC Berkeley Sky Computing Lab 发起的高性能大语言模型（LLM）推理与服务框架，是目前开源社区最活跃的 LLM 服务项目之一（GitHub 2000+ 贡献者）。其核心理念是 **Easy, fast, and cheap LLM serving**——以接近零成本的内存管理换取数倍于传统框架的吞吐量。

vLLM 的核心优势：

- **高吞吐**：基于 PagedAttention + Continuous Batching，吞吐量可达传统方案（FasterTransformer、Orca 等）的 **2~4 倍**
- **低成本**：KV Cache 内存碎片化近乎为零，相同 GPU 可服务更多并发请求
- **易用**：无缝对接 HuggingFace 模型，一行命令启动 OpenAI 兼容 API 服务
- **生态广**：支持 200+ 模型架构，覆盖 NVIDIA / AMD / CPU / Ascend / TPU 等多种硬件

vLLM 已于 2023 年 SOSP 发表论文（[arXiv:2309.06180](https://arxiv.org/abs/2309.06180)），并被阿里云、字节跳动等广泛用于生产环境。

> 相关文档：[[Inference Engine|推理引擎对比]]、[[quantization|模型量化]]、[[Ascend 昇腾|华为昇腾部署]]

## 2. 核心原理

### 2.1 PagedAttention（分页注意力）

传统推理框架在显存中为每个请求的 KV Cache 预先分配**连续**内存。由于生成长度不可预知，往往按最大可能长度分配，导致：

- **内部碎片**：预留的内存用不满（实际生成长度 < 最大长度）
- **外部碎片**：不同请求的内存块大小不一，无法合并利用
- 内存利用率通常仅 **20%~40%**

PagedAttention 借鉴操作系统**虚拟内存分页**思想：

- 将 KV Cache 划分为固定大小的 **Block**（默认每个 block 存 16 个 token 的 KV）
- 通过**块表（Block Table）** 将逻辑连续的 KV 映射到物理上分散的 block
- 内存利用率提升至 **90%+**，几乎无碎片

```
传统方案:  [========请求A 预留 4096 tokens========]  ← 大量空白浪费
PagedAttention:
  逻辑视图: [A0][A1][A2][A3]...[A_n]     ← token 逻辑连续
  物理视图: [block5][block13][block2]... ← 物理分散，块表索引
```

**块共享（Copy-on-Write）**：当多个请求共享相同前缀时（如 beam search、parallel sampling），可共享同一个 block 的只读副本，仅在写入时才复制。这在并行采样场景下可再省 55% 的内存。

### 2.2 Continuous Batching（连续批处理）

传统静态批处理必须等整批请求全部完成后才能接收新请求，GPU 在 batch 尾部大量空闲。

连续批处理允许**请求动态进出** batch：

- 某个请求生成完成 → 立即从 batch 移除，腾出的 slot 立刻被新请求占用
- 配合调度器在每个 decode step 动态决定参与计算的请求集合
- 相比静态批处理吞吐提升最高可达 **23 倍**（p50 延迟同时下降）

### 2.3 Chunked Prefill（分块预填充）

长 prompt 的 prefill（预填充）阶段计算量大、耗时长，会阻塞其他请求的 decode 输出（即首字延迟升高）。

分块预填充将 prefill 拆成多个 chunk 与 decode 交错执行，保证解码请求不被"饿死"，显著降低长 prompt 场景下的 TTFT（首 Token 延迟）。

```bash
# 启用分块 prefill
vllm serve Qwen/Qwen3-8B --enable-chunked-prefill

# 可选：限制单次迭代的最大 token 数（含 prefill + decode）
vllm serve Qwen/Qwen3-8B --enable-chunked-prefill --max-num-batched-tokens 4096
```

### 2.4 Automatic Prefix Caching（自动前缀缓存）

系统提示词、few-shot 示例等公共前缀在多个请求中重复出现。vLLM 自动对前缀做哈希，命中时直接复用已有 KV Cache，跳过重复计算：

- 前缀越长、复用越频繁，收益越大
- 典型场景：多轮对话的系统提示、RAG 的固定检索指令
- 与 PagedAttention 的块共享机制天然配合

```bash
vllm serve Qwen/Qwen3-8B --enable-prefix-caching
```

### 2.5 其他关键特性

| 特性 | 说明 |
|------|------|
| CUDA Graph | 捕获计算图消除内核启动开销，大幅降低 decode 延迟 |
| Speculative Decoding | n-gram / EAGLE / DFlash 等投机解码，小模型草稿 + 大模型验证加速 |
| Structured Outputs | 基于 xgrammar / guidance 约束生成 JSON 等结构化输出 |
| Disaggregated Prefill/Decode | prefill 与 decode 分离部署，各自独立扩缩容 |
| 量化内核 | FP8 / INT8 / INT4 / GPTQ / AWQ / GGUF 等推理内核优化 |

## 3. 安装

### 3.1 pip 安装（推荐）

```bash
# 仅 CPU 版本
pip install vllm

# GPU 版本（CUDA 12.x，自动匹配 PyTorch 版本）
pip install vllm

# 带 gRPC 服务支持
pip install "vllm[grpc]"

# 安装特定版本（生产环境建议锁版本）
pip install vllm==0.10.0
```

> **注意**：vLLM 对 Python 版本有要求（通常 3.9+），且与 PyTorch 版本强绑定。建议使用独立虚拟环境安装，避免污染训练环境（如用户项目中的 transformers 训练环境）。

### 3.2 Docker 安装（生产推荐）

```bash
# 拉取官方镜像
docker pull vllm/vllm-openai:latest

# 启动服务（挂载模型缓存目录）
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen3-8B
```

### 3.3 源码安装

```bash
git clone https://github.com/vllm-project/vllm.git
cd vllm
pip install -e .
```

> **注意**：源码编译需要 CUDA toolkit 与匹配的编译器，且耗时较长，仅建议开发调试场景使用。

## 4. 快速开始

### 4.1 离线推理（Python API）

```python
from vllm import LLM, SamplingParams

# 加载模型（自动选择最优推理后端）
llm = LLM(model="Qwen/Qwen3-8B", gpu_memory_utilization=0.9)

# 采样参数
sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=512,
)

# 批量推理（内部自动并行批处理）
outputs = llm.generate(
    ["请解释什么是大语言模型？", "用 Python 写一个快速排序"],
    sampling_params,
)

for output in outputs:
    prompt = output.prompt
    generated = output.outputs[0].text
    print(f"Prompt: {prompt!r}\n生成: {generated!r}\n")
```

### 4.2 启动 OpenAI 兼容 API 服务

```bash
# 一行命令启动，默认端口 8000
vllm serve Qwen/Qwen3-8B --port 8000
```

```bash
# curl 调用（OpenAI 兼容 /v1/chat/completions）
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-8B",
    "messages": [{"role": "user", "content": "介绍一下你自己"}],
    "temperature": 0.7,
    "max_tokens": 256,
    "stream": true
  }'
```

### 4.3 常用 Python 客户端

```python
from openai import OpenAI

# 服务端模型名与本地模型名可通过 --served-model-name 区分
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[{"role": "user", "content": "1+1=?"}],
    stream=True,  # 流式返回
)

for chunk in response:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

## 5. vllm serve 命令详解

vLLM 提供完整 CLI，`vllm serve` 是最常用的子命令。所有参数也支持通过 YAML 配置文件传入。

```bash
# 配置文件方式（推荐生产使用）
vllm serve --config serve_config.yaml
```

```yaml
# serve_config.yaml 示例
model: Qwen/Qwen3-32B
served-model-name: medical-llm        # API 暴露的模型名
tokenizer: Qwen/Qwen3-32B
tensor-parallel-size: 4               # 4 卡张量并行
gpu-memory-utilization: 0.9
max-model-len: 32768
dtype: bfloat16
enable-prefix-caching: true
enable-chunked-prefill: true
port: 8000
api-key: ${VLLM_API_KEY}              # 支持环境变量
```

### 5.1 核心模型参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `Qwen/Qwen3-0.6B` | HF 模型名或本地路径 |
| `--served-model-name` | 同 model | API 中对外暴露的模型名（可多个，如 `--served-model-name a --served-model-name b`） |
| `--tokenizer` | 同 model | tokenizer 名称或路径 |
| `--dtype` | `auto` | `auto` / `bfloat16` / `float16` / `float32` |
| `--max-model-len` | 自动推导 | 最大上下文长度（prompt+output），支持 `8k` / `2M` / `auto` 人类可读格式 |
| `--quantization` / `-q` | - | 量化方法：`awq` / `gptq` / `fp8` / `gguf` 等 |
| `--trust-remote-code` | `False` | 信任模型远程代码（自定义模型结构时需开启） |
| `--revision` | - | 模型分支/tag/commit |
| `--hf-token` | - | HuggingFace 鉴权 token（私有模型） |

### 5.2 内存与缓存参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--gpu-memory-utilization` | `0.92` | GPU 内存利用率（权重 + KV Cache 总预算），调低可防 OOM |
| `--kv-cache-dtype` | `auto` | KV Cache 精度：`fp8` / `fp8_e4m3` / `fp8_e5m2` 等，降显存占用 |
| `--block-size` | 自动 | 每个 KV block 的 token 数（16 或 32） |
| `--enable-prefix-caching` | - | 启用自动前缀缓存 |
| `--enable-chunked-prefill` | - | 启用分块 prefill |
| `--cpu-offload-gb` | `0` | CPU 卸载显存（GiB），大模型跑小 GPU 时使用 |
| `--kv-offloading-size` | - | KV Cache 卸载到 CPU 的缓冲大小（GiB） |

### 5.3 并行与分布式参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--tensor-parallel-size` | `-tp` | `1` | 张量并行组数（单卡放不下模型时用） |
| `--pipeline-parallel-size` | `-pp` | `1` | 流水线并行组数（跨节点大模型） |
| `--data-parallel-size` | `-dp` | `1` | 数据并行组数（高并发吞吐） |
| `--enable-expert-parallel` | `-ep` | `False` | MoE 模型专家并行 |
| `--nnodes` | `-n` | `1` | 节点数 |
| `--node-rank` | `-r` | `0` | 当前节点 rank |
| `--distributed-executor-backend` | - | `mp` | 分布式后端：`mp`（多进程）/ `ray` |
| `--max-num-seqs` | - | 自动 | 单次迭代最大并发序列数 |
| `--max-num-batched-tokens` | - | - | 单次迭代最大 token 数（prefill+decode） |

### 5.4 服务与安全参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `0.0.0.0` | 监听地址 |
| `--port` | `8000` | 服务端口 |
| `--api-key` | - | API 鉴权密钥（请求头 `Authorization: Bearer`） |
| `--ssl-keyfile` / `--ssl-certfile` | - | HTTPS 配置 |
| `--allowed-origins` | `['*']` | CORS 来源白名单 |
| `--root-path` | - | 反向代理路径前缀（如 `/vllm`） |
| `--grpc` | `False` | 启动 gRPC 服务替代 HTTP |
| `--enable-log-requests` | `False` | 记录请求日志 |

### 5.5 LoRA 与结构化输出参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--enable-lora` | - | 启用 LoRA 适配器服务 |
| `--max-loras` | `1` | 单 batch 最大并发 LoRA 数 |
| `--max-lora-rank` | `16` | 最大 LoRA rank |
| `--lora-modules` | - | 预加载 LoRA 模块（如 `name=path`） |

## 6. 分布式推理

vLLM 支持多种并行策略，可组合使用：

```
┌─────────────────────────────────────────────────┐
│  DP 数据并行（多副本，提升吞吐）                    │
│  ┌──────────┐  ┌──────────┐                      │
│  │ TP 张量并行 │  │ TP 张量并行 │  ← 每副本内部     │
│  │ ┌──┬──┬──┐ │  │ ┌──┬──┬──┐ │    切分权重       │
│  │ │GPU│GPU│GPU│ │  │GPU│GPU│GPU│                  │
│  │ └──┴──┴──┘ │  │ └──┴──┴──┘ │                  │
│  │ PP 流水线   │  │ PP 流水线   │  ← 跨层切分       │
│  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────┘
```

| 策略 | 简写 | 适用场景 | 说明 |
|------|------|----------|------|
| 张量并行 | `TP` | 单节点多卡 | 按层内切分权重，卡间通信频繁，需高速互联（NVLink） |
| 流水线并行 | `PP` | 跨节点 | 按层切分，通信量小，适合千兆网络跨机部署 |
| 数据并行 | `DP` | 高并发 | 多份模型副本各处理一批请求，需配合负载均衡 |
| 专家并行 | `EP` | MoE 模型 | 专家网络分布到不同 GPU，如 DeepSeek-V3 |

### 6.1 单机多卡（张量并行）

```bash
# 70B 模型 4 卡 TP 部署
vllm serve meta-llama/Llama-3-70B \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.92
```

### 6.2 多节点部署

节点 1（rank 0）：

```bash
vllm serve meta-llama/Llama-3-70B \
    --tensor-parallel-size 8 \
    --pipeline-parallel-size 2 \
    --nnodes 2 \
    --node-rank 0 \
    --distributed-executor-backend ray \
    --master-addr 192.168.1.10 --master-port 29501
```

节点 2（rank 1）：

```bash
vllm serve meta-llama/Llama-3-70B \
    --tensor-parallel-size 8 \
    --pipeline-parallel-size 2 \
    --nnodes 2 \
    --node-rank 1 \
    --distributed-executor-backend ray \
    --master-addr 192.168.1.10 --master-port 29501
```

### 6.3 显存估算

权重 + KV Cache 的粗略估算公式：

```text
权重显存 = 参数量(B) × 2 字节（BF16）
KV Cache = 2(键+值) × 层数 × 头维度 × 序列长度 × 并发数 × 2 字节
```

示例：Qwen3-32B（BF16）+ 32K 上下文 + 64 并发：

```text
权重 ≈ 32B × 2B = 64 GB
KV  ≈ 2 × 64层 × 128头 × 128维 × 32768 × 64 × 2B ≈ 88 GB
合计 ≈ 152 GB → 至少 4 张 A100-40G 或 4 张 A10 需配合量化
```

> 小技巧：启动时可用 `--max-model-len auto` 让 vLLM 根据显存自动推算最大上下文长度，避免手动算错导致 OOM。

## 7. 量化推理

vLLM 原生支持多种量化格式，可在部署时直接加载量化权重（无需额外转换）：

```bash
# AWQ 量化模型
vllm serve TheBloke/Llama-3-8B-AWQ --quantization awq --dtype half

# GPTQ 量化模型
vllm serve TheBloke/Llama-3-8B-GPTQ --quantization gptq

# FP8（H100 等支持 FP8 加速的 GPU 推荐）
vllm serve Qwen/Qwen3-32B --quantization fp8

# KV Cache 单独量化（不动权重，只压 KV 内存）
vllm serve Qwen/Qwen3-32B --kv-cache-dtype fp8
```

| 量化方案 | 精度 | 显存节省 | 适用场景 |
|----------|------|----------|----------|
| FP8 E4M3 | 8bit | ~50% | H100/Ada 系 GPU，精度损失小，首选 |
| AWQ | 4bit | ~75% | 通用 GPU，激活感知量化，精度好 |
| GPTQ | 4bit | ~75% | 通用 GPU，经典后训练量化 |
| GGUF | 2~8bit | 可变 | CPU 推理、边缘设备 |
| INT8 | 8bit | ~50% | 兼容性最好 |

> 详细精度格式对比见 [[model-precision-quantization|模型精度与量化方法]]。

## 8. 多模态与特殊模型

vLLM 支持 LLaVA、Qwen-VL、Pixtral 等多模态模型以及 Mamba 状态空间模型：

```bash
# 视觉模型（限制每 prompt 最多 4 张图）
vllm serve llava-hf/llava-v1.6-mistral-7b-hf \
    --limit-mm-per-prompt '{"image": 4}'

# 仅文本模型（关闭多模态以省显存）
vllm serve Qwen/Qwen3-8B --language-model-only
```

多模态调用示例：

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="Qwen/Qwen3-VL-8B",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "https://example.com/x-ray.jpg"}},
            {"type": "text", "text": "请描述这张医学影像中的异常区域"},
        ],
    }],
)
print(response.choices[0].message.content)
```

## 9. 实战配置与最佳实践

### 9.1 生产部署模板（OpenAI 兼容服务）

```bash
vllm serve Qwen/Qwen3-32B \
    --served-model-name production-llm \
    --dtype bfloat16 \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.92 \
    --max-model-len 32768 \
    --enable-prefix-caching \
    --enable-chunked-prefill \
    --max-num-batched-tokens 8192 \
    --max-num-seqs 256 \
    --api-key sk-prod-xxx \
    --port 8000 \
    --enable-log-requests
```

### 9.2 多 LoRA 服务（微调模型热切换）

```bash
# 启动时注册 LoRA 模块
vllm serve Qwen/Qwen3-14B \
    --enable-lora \
    --max-loras 4 \
    --max-lora-rank 64 \
    --lora-modules medical-lora=/models/lora/medical \
    --lora-modules legal-lora=/models/lora/legal
```

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

# 请求时通过 extra_body 指定 LoRA 适配器
response = client.chat.completions.create(
    model="medical-lora",  # 对应 --lora-modules 中注册的名称
    messages=[{"role": "user", "content": "诊断该病例"}],
    extra_body={"max_tokens": 512},
)
```

### 9.3 结构化输出（JSON 约束）

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="production-llm",
    messages=[{"role": "user", "content": "输出患者信息"}],
    response_format={"type": "json_object"},  # 强制合法 JSON
)
```

### 9.4 健康检查与监控

```bash
# 健康检查端点
curl http://localhost:8000/health

# Prometheus 指标
curl http://localhost:8000/metrics
```

内置关键指标：

| 指标 | 含义 |
|------|------|
| `vllm:num_requests_running` | 当前运行请求数 |
| `vllm:num_requests_waiting` | 排队请求数 |
| `vllm:gpu_cache_usage_perc` | KV Cache 利用率（接近 1 说明内存紧张） |
| `vllm:time_to_first_token_seconds` | 首 Token 延迟 |
| `vllm:time_per_output_token_seconds` | 每 Token 生成时间（吞吐） |
| `vllm:e2e_request_latency_seconds` | 端到端请求延迟 |

## 10. 性能调优

### 10.1 调优检查清单

| 方向 | 建议 |
|------|------|
| 吞吐优先 | 增大 `--max-num-seqs`、`--max-num-batched-tokens`，开启 chunked prefill |
| 延迟优先 | 降低并发、启用 CUDA Graph（默认开启）、关闭 prefix caching 的哈希开销场景 |
| 显存不足 | 调低 `--gpu-memory-utilization`、KV Cache 量化 `--kv-cache-dtype fp8`、权重量化 |
| 长上下文 | 调大 `--max-model-len`、开启 chunked prefill、考虑 KV offload |
| MoE 模型 | 开启 `--enable-expert-parallel` |
| 高并发在线服务 | 使用 `--data-parallel-size` 多副本 + 外部负载均衡 |

### 10.2 常见误区

1. **`--gpu-memory-utilization` 不是"用满才好"**：调太高会导致 KV Cache 预留过少、触发 OOM；建议 0.85~0.92
2. **`--max-model-len` 越大越好？**：上下文越长 KV Cache 占用越大，会压缩并发能力。按业务实际需求设置
3. **TP 不是越多越好**：TP 卡间通信开销大，8 卡以上建议评估 PP/EP 组合

## 11. 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `CUDA out of memory` | 显存不足 | 调低 `--gpu-memory-utilization`、`--max-model-len`；开启量化 |
| `The model's max seq len is larger than the maximum number of tokens` | `max_model_len` 超配置 | 显式设置 `--max-model-len`（如 `8192`） |
| `ValueError: Tokenizer class ... not found` | 缺少 tokenizer 文件 | 指定 `--tokenizer` 或检查本地模型目录完整性 |
| 多卡启动卡死/超时 | NCCL 通信问题 | 检查节点互通、`--master-addr`、防火墙端口（29500-29502） |
| 推理速度极慢 | 误用 eager 模式 | 确认未加 `--enforce-eager`，CUDA Graph 默认开启 |
| 私有模型 401/403 | HF 鉴权失败 | 添加 `--hf-token` 或使用 `huggingface-cli login` |
| 流式输出不生效 | 客户端未启用 stream | 请求体加 `"stream": true` |

## 12. 与其他推理框架对比

| 维度 | vLLM | SGLang | TGI | llama.cpp |
|------|------|--------|-----|-----------|
| 核心卖点 | PagedAttention，吞吐高 | RadixAttention，前缀复用强 | HuggingFace 官方，生态无缝 | 纯 CPU/边缘可跑 |
| 吞吐 | ★★★★★ | ★★★★★ | ★★★★ | ★★★ |
| OpenAI API | 原生支持 | 原生支持 | 原生支持 | 需额外封装 |
| 多模态 | 支持 | 支持 | 支持 | 部分 |
| 分布式 | TP/PP/DP/EP 完整 | TP/PP/DP | TP/PP | 无 |
| 硬件支持 | NVIDIA/AMD/CPU/Ascend/TPU | NVIDIA/AMD/AWS | NVIDIA/AMD | CPU/Apple Silicon |
| 量化 | AWQ/GPTQ/FP8/GGUF 等 | 同左 | 同左 | GGUF |

**选型建议**：

- 生产环境 GPU 推理首选 **vLLM**（生态成熟、社区活跃）
- 前缀复用极多的场景（如 RAG 大量固定指令）可评估 **SGLang**
- CPU / Apple Silicon / 边缘设备选 **llama.cpp**
- 华为昇腾环境参考 [[Ascend 昇腾|MindIE-LLM 部署]]（昇腾官方，与 vLLM 同 API 风格）

## 13. 参考链接

- [vLLM 官方文档](https://docs.vllm.ai/en/stable/)
- [vLLM GitHub 仓库](https://github.com/vllm-project/vllm)
- [PagedAttention 技术博客](https://blog.vllm.ai/2023/06/20/vllm.html)
- [vLLM 论文（SOSP 2023）](https://arxiv.org/abs/2309.06180)
- [vllm serve CLI 参考](https://docs.vllm.ai/en/stable/cli/serve/)

## See Also

- [[Inference Engine|推理引擎对比与部署]]
- [[quantization|模型量化]]
- [[Ascend 昇腾|华为昇腾 MindIE 部署]]
- [[model-precision-quantization|模型精度与量化方法]]
