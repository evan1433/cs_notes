---
title: SGLang 推理服务框架
description: SGLang 高性能 LLM 推理与部署框架全面解析：RadixAttention 前缀缓存原理、前端语言、安装部署、launch_server 配置、分布式推理、结构化输出与性能对比
tags:
  - ai
  - llm
  - inference
  - sglang
  - deployment
date: 2026-08-24
aliases:
  - sglang
  - SGLang
reference: https://docs.sglang.io/
---
# SGLang 推理服务框架

## 1. 概述

SGLang（Structured Generation Language for LLMs）是由斯坦福大学 LMSYS 组织主导的高性能大语言模型（LLM）推理与服务框架。与 vLLM 等通用引擎不同，SGLang 的核心理念是**为"语言模型程序"（LM Programs）设计**——即同时优化前端编程语言与后端运行时，系统性利用多次生成调用之间的结构相似性来提升效率。

SGLang 的行业地位：

- 全球支撑 **40 万+ GPU** 的生产部署，每天生成数万亿 token
- 论文 *SGLang: Efficient Execution of Structured Language Model Programs* 发表于 **NeurIPS 2024**（[arXiv:2312.07104](https://arxiv.org/abs/2312.07104)）
- 在 agent 控制、RAG、JSON 解码、多轮对话等场景，吞吐可达现有系统的 **6.4 倍**

核心特色：

- **RadixAttention**：基于基数树（Radix Tree）的全局 KV Cache 复用，前缀命中即跳过重复计算
- **前端语言**：Python 内嵌 DSL，支持链式生成、并行控制、结构化 I/O，可解释执行或编译执行
- **结构化输出**：基于压缩有限状态机（Compressed FSM）的约束解码，JSON 解码速度显著提升
- **PD 分离**：prefill 与 decode 解耦，分别扩缩容（disaggregation）
- **零开销 CPU 调度器** + CUDA Graph 高级技术，decode 延迟极低

> 相关文档：[[vllm|vLLM 推理服务框架]]、[[Inference Engine|推理引擎对比]]、[[quantization|模型量化]]、[[Ascend 昇腾|华为昇腾部署]]

## 2. 核心原理

### 2.1 RadixAttention（基数树前缀缓存）

SGLang 的核心创新。传统推理框架（含 vLLM 早期版本）的 KV Cache 随请求结束即释放，但真实业务中大量请求**共享公共前缀**：

| 场景 | 公共前缀 |
|------|----------|
| 多轮对话 | 系统提示 + 历史对话 |
| RAG 流水线 | 固定的检索指令 + 文档片段 |
| Agent 控制 | 工具定义 + 角色设定 |
| few-shot 学习 | 示例集合 |
| self-consistency / tree-of-thought | 相同的初始问题 |

RadixAttention 用**基数树（Radix Tree，压缩前缀树）** 维护全局 KV Cache 池：

- 树的每条边标记一段 token 序列（而非单个 token），空间利用率高
- 新请求到达时做**最长前缀匹配**：命中部分直接复用已有 KV Cache，跳过 prefill；仅对未命中后缀执行计算并追加到树中
- 显存不足时按 **LRU** 策略递归淘汰叶节点
- 树结构存储在 CPU 上，维护开销极小；与连续批处理、分页注意力天然兼容

```
请求1: [系统提示][问题A] → 计算完整 KV 并缓存
请求2: [系统提示][问题B] → 命中 [系统提示] 前缀，仅计算 [问题B]

         radix tree
        ┌──────────┐
        │  系统提示  │ ← 共享节点（两个请求复用）
        └────┬─────┘
        ┌────┴────┐
      [问题A]    [问题B]
```

**效果**：若系统提示占请求总长一半，则每次命中省一半 prefill 计算。在前缀复用率高的 SaaS / RAG 负载中，SGLang 相比 vLLM 公开测试可取得 **5~10 倍**吞吐优势（非普适结论，取决于前缀命中率）。

> **RadixAttention vs PagedAttention**：两者解决不同问题。PagedAttention 管的是"单个请求内部"的显存碎片；RadixAttention 管的是"跨请求之间"的 KV 复用。vLLM 后来通过 `--enable-prefix-caching` 实现了类似能力，但复用模式与缓存管理策略不同。

### 2.2 前端语言（SGLang DSL）

SGLang 提供了 Python 内嵌的领域特定语言，用于编写复杂 LLM 应用：

- **原语**：`extend`（拼接 prompt）、`gen`（生成）、`select`（从候选中选择）
- **并行控制**：`fork` / `join`（实现 self-consistency、树搜索）
- 兼容 Python 原生控制流与库，可解释执行或编译执行

```python
import sglang as sgl


@sgl.function
def multi_turn_qa(s, question):
    # extend: 拼接 prompt（结构化方式，自动处理角色分隔）
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(question)
    s += sgl.assistant(sgl.gen("answer", max_tokens=512))


# 调用
state = multi_turn_qa.run(question="什么是 RadixAttention?")
print(state["answer"])
```

### 2.3 后端运行时优化

| 优化项 | 说明 |
|--------|------|
| 连续批处理 | 请求动态进出 batch，无静态 batch 尾部浪费 |
| 分页注意力 | KV Cache 分页管理，配合 RadixAttention 复用 |
| 零开销 CPU 调度器 | 调度决策与 GPU 计算流水线化，隐藏调度延迟 |
| Chunked Prefill | 长 prompt 分块 prefill，降低长上下文 TTFT |
| CUDA Graph | 捕获计算图消除内核启动开销（含 Advanced CUDA Graph 技术） |
| 推测解码 | EAGLE / n-gram 等小模型草稿加速 |
| PD 分离 | prefill 与 decode 拆分为独立服务，各自扩缩容 |
| 分层 KV Cache（HiCache） | 多级 KV 缓存（GPU/CPU/磁盘），扩展缓存容量 |
| torch.compile | 小模型小 batch 场景加速 |

## 3. 安装

> **前置要求**：Python 3.10+，NVIDIA GPU（sm75+，即 T4 及以上）。FlashInfer 是默认 attention 内核后端。

### 3.1 pip / uv 安装（推荐）

```bash
# 推荐使用 uv，安装更快
pip install --upgrade pip
pip install uv
uv pip install --prerelease=allow sglang
```

> **注意**：默认安装对应 CUDA 13。若使用 CUDA 12 环境：

```bash
uv pip install --prerelease=allow sglang
uv pip install --force-reinstall torch==2.13.0 torchaudio==2.11.0 torchvision \
    --index-url https://download.pytorch.org/whl/cu129
uv pip install --force-reinstall sglang-kernel \
    --index-url https://docs.sglang.ai/whl/cu129/
```

### 3.2 Docker 安装（生产推荐）

```bash
# --shm-size 必填：SGLang 多进程通过共享内存通信
docker run --gpus all \
    --shm-size 32g \
    -p 30000:30000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    --env "HF_TOKEN=<your-hf-token>" \
    --ipc=host \
    lmsysorg/sglang:latest \
    python3 -m sglang.launch_server \
        --model-path meta-llama/Llama-3.1-8B-Instruct \
        --host 0.0.0.0 --port 30000
```

- `latest` / `dev` 是可变标签，生产环境建议锁定版本号（如 `lmsysorg/sglang:v0.5.18`）
- 生产部署用 `-runtime` 变体，体积小约 40%：`lmsysorg/sglang:latest-runtime`
- CUDA 12 环境使用 `-cu129` 后缀镜像

### 3.3 源码安装

```bash
git clone -b v0.5.18 https://github.com/sgl-project/sglang.git
cd sglang
pip install -e "python"
```

> Kubernetes 生产管理推荐 [OME](https://github.com/sgl-project/ome)（SGLang 官方 operator）。

## 4. 快速开始

### 4.1 启动服务器

```bash
# 默认端口 30000（注意与 vLLM 的 8000 不同）
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-8B \
    --host 0.0.0.0 \
    --port 30000
```

### 4.2 OpenAI 兼容 API 调用

```bash
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-8B",
    "messages": [{"role": "user", "content": "介绍一下你自己"}],
    "temperature": 0.7,
    "max_tokens": 256,
    "stream": true
  }'
```

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:30000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=[{"role": "user", "content": "用 Python 写一个快速排序"}],
    stream=False,
)
print(response.choices[0].message.content)
```

### 4.3 离线推理

```python
import sglang as sgl

llm = sgl.Engine(model_path="Qwen/Qwen3-8B", mem_fraction_static=0.9)

sampling_params = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_new_tokens": 512,
}

outputs = llm.generate(
    input_texts=["请解释什么是大语言模型？", "1+1=?"],
    sampling_params=sampling_params,
)
for output in outputs:
    print(output["text"])
```

## 5. launch_server 命令详解

SGLang 通过 `python -m sglang.launch_server` 启动服务，所有参数可通过 `--help` 查看，也支持 YAML 配置文件：

```bash
# 配置文件方式（CLI 参数优先于配置文件）
python -m sglang.launch_server --config config.yaml
```

```yaml
# config.yaml 示例
model-path: Qwen/Qwen3-32B
served-model-name: medical-llm        # API 暴露的模型名
tp: 4                                  # 张量并行
mem-fraction-static: 0.9               # 静态内存分配比例
context-length: 32768
dtype: bfloat16
quantization: fp8
enable-prefix-caching: true
chunked-prefill-size: 8192
host: 0.0.0.0
port: 30000
api-key: ${SGLANG_API_KEY}
```

### 5.1 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model-path` / `--model` | - | 模型路径或 HF repo ID |
| `--served-model-name` | 同 model-path | API 对外暴露的模型名 |
| `--tokenizer-path` | 同 model-path | tokenizer 路径 |
| `--dtype` | `auto` | `auto` / `bfloat16` / `float16` / `float32` |
| `--context-length` | 自动 | 最大上下文长度 |
| `--quantization` | - | 权重量化：`fp8` / `awq` / `gptq` / `fp4` 等 |
| `--trust-remote-code` | `False` | 信任远程模型代码 |
| `--reasoning-parser` | - | 推理解析器：`qwen3` / `deepseek-r1` / `glm45` 等 |
| `--tool-call-parser` | - | 工具调用解析器：`qwen3` / `glm47` / `hermes` 等 |
| `--load-format` | `auto` | 权重加载格式：`auto` / `pt` / `safetensors` / `gguf` / `bitsandbytes` / `dummy` 等 |
| `--hf-chat-template-name` | - | tokenizer 有多个命名模板时选择（如 `tool_use`） |

### 5.2 内存与调度参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--mem-fraction-static` | `0.9` | 静态内存分配比例（KV 池），OOM 时调小（如 `0.7`） |
| `--kv-cache-dtype` | - | KV Cache 量化：`fp8_e4m3` / `fp8_e5m2` |
| `--enable-prefix-caching` | `True`（默认开启） | RadixAttention 前缀缓存 |
| `--chunked-prefill-size` | - | 分块 prefill 大小，长 prompt OOM 时调小 |
| `--max-running-requests` | - | 最大并发运行请求数 |
| `--max-prefill-tokens` | - | 单次迭代最大 prefill token 数 |
| `--max-total-tokens` | - | 单请求最大总 token 数（含 KV 预算） |
| `--cuda-graph-max-bs-decode` | - | decode 阶段 CUDA Graph 最大 batch |
| `--enable-torch-compile` | `False` | torch.compile 加速（小模型小 batch 场景） |
| `--attention-backend` | `flashinfer` | 注意力后端：`flashinfer` / `triton` / `fa3` 等 |

### 5.3 并行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--tp` / `--tensor-parallel-size` | - | `1` | 张量并行组数 |
| `--pp-size` | - | `1` | 流水线并行组数 |
| `--dp` | - | `1` | 数据并行组数（配合 `sglang_router` 使用） |
| `--ep-size` | - | `1` | 专家并行组数（MoE） |
| `--nnodes` | - | `1` | 节点数 |
| `--node-rank` | - | `0` | 节点 rank |
| `--dist-init-addr` | - | - | 分布式初始化地址（`host:port`） |
| `--enable-p2p-check` | - | - | 检查 GPU 间 P2P 访问（`peer access is not supported` 报错时开启） |

## 6. 分布式推理

### 6.1 张量并行与数据并行

```bash
# 单节点 2 卡张量并行
python -m sglang.launch_server \
    --model-path meta-llama/Meta-Llama-3-8B-Instruct \
    --tp 2

# 数据并行（吞吐优先，显存充足时推荐）
# 官方推荐通过 SGLang Router 做数据并行负载均衡
python -m sglang_router.launch_server \
    --model-path meta-llama/Meta-Llama-3-8B-Instruct \
    --dp 2 --tp 2    # 共使用 4 卡
```

> **P2P 报错**：多卡 TP 若报 `peer access is not supported between these two devices`，加 `--enable-p2p-check`。

### 6.2 多节点部署

```bash
# 节点 0
python -m sglang.launch_server \
    --model-path meta-llama/Meta-Llama-3-8B-Instruct \
    --tp 4 \
    --dist-init-addr sgl-dev-0:50000 \
    --nnodes 2 \
    --node-rank 0

# 节点 1
python -m sglang.launch_server \
    --model-path meta-llama/Meta-Llama-3-8B-Instruct \
    --tp 4 \
    --dist-init-addr sgl-dev-0:50000 \
    --nnodes 2 \
    --node-rank 1
```

### 6.3 PD 分离部署（Prefill/Decode 解耦）

大吞吐生产场景可将 prefill 与 decode 拆分为独立服务，各自独立扩缩容（如借助 Mooncake 高速传输后端）：

```bash
# Prefill worker（负责长 prompt 计算）
python -m sglang.launch_server \
    --model-path meta-llama/Llama-3-8B \
    --disaggregation-mode prefill \
    --port 30000 \
    --disaggregation-bootstrap-port 9001 \
    --disaggregation-transfer-backend mooncake \
    --tensor-parallel-size 2

# Decode worker（负责逐 token 生成）
python -m sglang.launch_server \
    --model-path meta-llama/Llama-3-8B \
    --disaggregation-mode decode \
    --port 30001 \
    --disaggregation-transfer-backend mooncake \
    --tensor-parallel-size 2
```

## 7. 量化与 KV Cache 优化

```bash
# FP8 权重量化（FP16 checkpoint 上启用）
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-32B \
    --quantization fp8

# FP8 KV Cache 量化（压缩 KV 显存）
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-32B \
    --kv-cache-dtype fp8_e4m3

# AWQ / GPTQ 量化模型直接加载
python -m sglang.launch_server \
    --model-path TheBloke/Llama-3-8B-AWQ \
    --quantization awq
```

| 方案 | 说明 |
|------|------|
| FP8 / FP4 | 现代 GPU 首选，精度损失小 |
| AWQ / GPTQ | 4bit 通用量化 |
| GGUF | CPU 推理场景（`--load-format gguf`） |
| bitsandbytes | 按需量化加载 |
| KV Cache FP8 | 不影响权重，仅压缩 KV 内存，与权重量化可叠加 |

> 详细精度格式对比见 [[model-precision-quantization|模型精度与量化方法]]。

## 8. 结构化输出与推理解析器

### 8.1 结构化输出（JSON 约束解码）

SGLang 基于压缩有限状态机（Compressed FSM）实现约束解码，相比逐 token 采样，JSON 解码可一次解码多个 token：

```python
import json
import sglang as sgl


@sgl.function
def extract_patient_info(s, text):
    s += sgl.system("You are a medical record extractor. Output JSON only.")
    s += sgl.user(text)
    s += sgl.assistant(
        sgl.gen(
            "info",
            max_tokens=256,
            # 通过正则约束输出格式（等效 JSON Schema 约束）
            regex=r'{"name": "\w+", "age": \d+, "diagnosis": "\w+"}',
        )
    )


state = extract_patient_info.run(text="患者张三，45岁，确诊高血压。")
info = json.loads(state["info"])
print(info)  # {'name': '张三', 'age': 45, 'diagnosis': '高血压'}
```

OpenAI API 同样支持 `response_format={"type": "json_object"}`。

### 8.2 推理解析器（Reasoning Parser）

面向 Qwen3 / DeepSeek-R1 等思考模型，解析思考内容与最终回答：

```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-32B \
    --reasoning-parser qwen3 \
    --tool-call-parser qwen3
```

## 9. 实战配置与最佳实践

### 9.1 生产部署模板

```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-32B \
    --served-model-name production-llm \
    --dtype bfloat16 \
    --tp 4 \
    --mem-fraction-static 0.9 \
    --context-length 32768 \
    --enable-prefix-caching \
    --chunked-prefill-size 8192 \
    --max-running-requests 128 \
    --quantization fp8 \
    --reasoning-parser qwen3 \
    --host 0.0.0.0 \
    --port 30000 \
    --api-key sk-prod-xxx
```

### 9.2 多 LoRA 服务

```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-14B \
    --enable-lora \
    --lora-modules medical-lora=/models/lora/medical \
    --lora-modules legal-lora=/models/lora/legal
```

### 9.3 监控与可观测性

```bash
# 健康检查
curl http://localhost:30000/health

# Prometheus 指标（启动时加 --enable-metrics）
curl http://localhost:30000/metrics
```

| 指标 | 含义 |
|------|------|
| `sglang:num_running_reqs` | 当前运行请求数 |
| `sglang:num_waiting_reqs` | 排队请求数 |
| `sglang:cache_hit_rate` | 前缀缓存命中率（RadixAttention 效果核心指标） |
| `sglang:time_to_first_token` | 首 Token 延迟 |
| `sglang:time_per_output_token` | 每 Token 生成时间 |
| `sglang:prompt_tokens_total` | 累计输入 token 数 |
| `sglang:generation_tokens_total` | 累计输出 token 数 |

> 可结合 `--enable-cache-report` 查看缓存命中明细，评估是否值得保留长公共前缀。

### 9.4 分布式环境注意

- **Docker/K8s 必须设置共享内存**：`--shm-size 32g`（docker）或 `/dev/shm` 扩容（K8s），SGLang 多进程依赖共享内存通信
- 生产环境使用 SGLang Router（`sglang_router.launch_server`）做 DP 负载均衡与故障转移

## 10. 性能调优

| 方向 | 建议 |
|------|------|
| 前缀命中率低 | 检查公共 prompt 是否一致（末尾空白/换行会影响匹配）；考虑固定 system prompt 模板 |
| 长 prompt OOM | 调小 `--chunked-prefill-size`（如 4096）、`--mem-fraction-static` |
| 整体 OOM | `--mem-fraction-static 0.7`、KV Cache 量化 `--kv-cache-dtype fp8_e4m3`、权重量化 |
| 吞吐优先 | 增大 `--max-running-requests`、启用 DP + Router |
| 延迟优先 | 调小 batch、开启 CUDA Graph（默认）、考虑 PD 分离 |
| 小模型小 batch | `--enable-torch-compile` 加速 |
| 高并发在线 | PD 分离 + 数据并行 + Router 负载均衡 |
| 确定性输出 | `--enable-deterministic-inference` |

## 11. 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `CUDA out of memory` | 显存不足 | 调小 `--mem-fraction-static`、`--chunked-prefill-size`；启用量化 |
| `peer access is not supported between these two devices` | 多卡 P2P 检查失败 | 添加 `--enable-p2p-check` |
| FlashInfer 相关报错（sm75+ 设备） | FlashInfer 内核兼容问题 | `--attention-backend triton --sampling-backend pytorch` |
| Docker 内多进程卡死 | 共享内存不足 | 设置 `--shm-size 32g`、`--ipc=host` |
| 多节点启动死锁 | 分布式初始化失败 | 检查 `--dist-init-addr` 连通性；尝试 `--disable-cuda-graph` |
| `OSError: CUDA_HOME environment variable is not set` | CUDA 环境缺失 | `export CUDA_HOME=/usr/local/cuda-<version>` 或先安装 FlashInfer |
| 前缀缓存命中率低 | prompt 前缀不一致 | 统一 system prompt 格式（注意空白符）；确认 `--enable-prefix-caching` 开启 |
| 长 prompt prefill OOM | 单请求 prefill 过大 | 调小 `--chunked-prefill-size` |

## 12. 与 vLLM 对比

| 维度    | SGLang                              | vLLM                                |
| ----- | ----------------------------------- | ----------------------------------- |
| 起源    | Stanford LMSYS                      | UC Berkeley Sky Computing Lab       |
| 核心卖点  | RadixAttention 全局前缀复用 + 前端 DSL      | PagedAttention 分页内存 + 生态成熟          |
| 前缀缓存  | **默认开启**，Radix Tree + LRU           | `--enable-prefix-caching` 手动开启，哈希匹配 |
| 前端语言  | 内嵌 DSL（extend/gen/select/fork/join） | 无（纯服务框架）                            |
| 结构化输出 | Compressed FSM，可一次解码多 token         | xgrammar / guidance 约束              |
| 启动方式  | `python -m sglang.launch_server`    | `vllm serve`                        |
| 默认端口  | 30000                               | 8000                                |
| 分布式   | TP/PP/DP/EP 齐全                      | TP/PP/DP/EP/CP 齐全                   |
| PD 分离 | 支持（disaggregation）                  | 支持                                  |
| 硬件支持  | NVIDIA/AMD/CPU/TPU/Ascend           | NVIDIA/AMD/CPU/TPU/Ascend 等         |
| 适用场景  | 前缀高度复用的 RAG/Agent/多轮对话              | 通用部署、生态整合度要求高的团队                    |

**选型建议**：

- **前缀复用率高**（固定 system prompt、RAG、agent 工具定义）→ SGLang 的 RadixAttention 收益明显
- **通用场景 / 团队已有 vLLM 运维经验** → vLLM 生态更成熟、资料更多
- 两者均支持 OpenAI 兼容 API，迁移成本低，可先在相同负载下 benchmark 再决定
- 昇腾环境参考 [[Ascend 昇腾|MindIE-LLM 部署]]（昇腾官方方案，SGLang 也提供 Ascend NPU 支持）

## 13. 参考链接

- [SGLang 官方文档](https://docs.sglang.ai/)
- [SGLang GitHub 仓库](https://github.com/sgl-project/sglang)
- [SGLang 论文（NeurIPS 2024）](https://arxiv.org/abs/2312.07104)
- [RadixAttention 技术博客（LMSYS）](https://www.lmsys.org/blog/2024-01-17-sglang/)
- [Server Arguments 文档](https://docs.sglang.ai/docs/advanced_features/server_arguments)

## See Also

- [[vllm|vLLM 推理服务框架]]
- [[Inference Engine|推理引擎对比与部署]]
- [[quantization|模型量化]]
- [[Ascend 昇腾|华为昇腾 MindIE 部署]]
- [[model-precision-quantization|模型精度与量化方法]]
