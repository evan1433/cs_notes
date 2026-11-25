---
title: Google A2A 协议指南
tags: [ai, agent, a2a, protocols, google, 互操作性, json-rpc]
---

# Google A2A 协议指南

## 概述

**Agent-to-Agent (A2A) 协议** 是由 Google 于 2025 年 4 月推出的开源协议，旨在实现不同 AI 代理之间的标准化通信和互操作性。2025 年 8 月，在 Linux 基金会的管理下，IBM 的 Agent Communication Protocol 合并到 A2A 规范中，使其成为 LLM 代理互操作性的主导标准。

> **核心目标**: 让来自不同供应商的 AI 代理能够无缝通信和协作，无需定制的胶水代码。

---

## A2A vs MCP

| 协议 | 全称 | 推出时间 | 用途 |
|------|------|----------|------|
| **A2A** | Agent-to-Agent Protocol | 2025 年 4 月 (Google) | 代理 ↔ 代理 通信 |
| **MCP** | Model Context Protocol | 2024 年 11 月 (Anthropic) | 代理 ↔ 工具 通信 |

**场景示例**（旅行预订）：

- 航班代理使用 **MCP** 调用预订 API
- 航班代理使用 **A2A** 与旅行代理共享结果

---

## 核心概念

### 1. Agent Card（代理卡片）

Agent Card 是一个 JSON 对象，用于描述代理的能力、技能和连接信息。它是代理发现机制的核心。

```json
{
  "name": "booking-agent",
  "url": "https://agent.example.com",
  "version": "1.0.0",
  "description": "航班预订代理",
  "skills": [
    {
      "id": "book-flight",
      "name": "Flight Booking",
      "description": "预订航班"
    },
    {
      "id": "cancel-flight",
      "name": "Flight Cancellation",
      "description": "取消航班"
    }
  ],
  "authentication": {
    "schemes": ["oauth2", "api-key"]
  },
  "capabilities": {
    "streaming": true,
    "async": true
  }
}
```

### 2. Task（任务）

任务是 A2A 协议中的核心工作单元，具有状态管理。

**任务状态**:

| 状态 | 说明 |
|------|------|
| `submitted` | 任务已提交，等待处理 |
| `working` | 任务正在执行中 |
| `input-required` | 需要用户提供更多信息 |
| `completed` | 任务已完成 |
| `failed` | 任务执行失败 |

### 3. Artifact（工件）

工件是任务执行的输出结果，代表代理任务的"终端状态"。

### 4. Message（消息）

消息是原子通信单元，与上下文 ID（context ID）关联：

- **客户端** 可以提供一个上下文的 ID
- **服务器** 必须提供一个上下文的 ID

---

## 通信架构

### 传输绑定（Transport Bindings）

A2A 协议支持多种传输方式：

| 传输方式 | 使用场景 |
|----------|----------|
| **JSON-RPC** | 最统一的格式，默认参考实现 |
| **gRPC** | v0.3+ 支持，使用 protobuf 模式 |
| **REST (JSON over HTTP)** | 标准 HTTP API |
| **自定义绑定** | 允许创建自定义协议绑定 |

### 交付机制（Delivery Mechanisms）

| 机制 | 特点 |
|------|------|
| **同步 HTTP POST** | 即时请求 |
| **Server-Sent Events (SSE)** | 需要响应性的长时间运行任务 |
| **Webhook 推送通知** | 异步任务更新（非 SSE） |
| **gRPC 流** | v0.3+ 支持流式传输 |

> **关键约束**: 操作必须立即返回，不允许阻塞。长时间运行的异步更新通过 webhook 发送。

---

## 消息格式示例

### 任务响应示例（需要输入）

```json
{
  "task": {
    "id": "task-12345",
    "contextId": "ctx-67890",
    "status": {
      "state": "input-required",
      "message": {
        "role": "agent",
        "parts": [
          {
            "type": "text",
            "text": "I need more details. Where would you like to fly from and to?"
          }
        ]
      }
    }
  }
}
```

### 任务完成响应

```json
{
  "task": {
    "id": "task-12345",
    "contextId": "ctx-67890",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [
          {
            "type": "text",
            "text": "Your flight has been booked successfully."
          }
        ]
      }
    },
    "artifacts": [
      {
        "id": "artifact-001",
        "type": "booking-confirmation",
        "data": {
          "confirmationNumber": "ABC123",
          "flightNumber": "UA456"
        }
      }
    ]
  }
}
```

### 通信模式

- **客户端** 发送 `Message` 对象
- **服务器** 响应 `Task` 对象
- 即使在请求输入时，服务器也返回 `input-required` 状态的 `Task`，其中包含 `Message` 组件

---

## 认证与授权

### 支持的认证方案

```json
{
  "authentication": {
    "schemes": ["oauth2", "api-key", "bearer"],
    "oauth2": {
      "authorizationUrl": "https://auth.example.com/oauth/authorize",
      "tokenUrl": "https://auth.example.com/oauth/token",
      "scopes": ["read", "write", "execute"]
    }
  }
}
```

### 安全注意事项

> **重要**: A2A 协议的授权是"实现定义"的——协议本身不强制要求认证，由实现者自行决定。

---

## 安全考虑

### 攻击面

| 领域 | 风险 |
|------|------|
| **执行器实现** | 任务处理和 LLM 调用中的业务逻辑错误 |
| **SDKs** | 对象处理、序列化边缘情况、语言特定问题 |
| **LLM 输入** | 提示注入、继承的 MCP 攻击面 |

### 协议级漏洞

#### 1. 未签名的 Agent Cards (v0.3+)

- 支持签名但**不强制**
- 可能被恶意行为者利用进行欺骗
- 没有中央注册表进行验证

#### 2. OAuth 控制不足

- **令牌生命周期**: 不强制使用短期令牌
- **粗粒度范围**: 支付令牌未限制为单次交易
- **缺少同意机制**: 没有协议级的用户批准要求

#### 3. 流劫持

- 允许多个并发流
- 被盗/伪造的会话令牌可以静默监听受害者流

#### 4. 数据泄露

- 敏感数据（支付凭证、身份文档）经过中间代理
- 共享代理上下文可能暴露敏感信息

#### 5. 序列化攻击

- 使用 JSON-RPC 2.0
- 易受攻击：Unicode 规范化、嵌套对象深度、超大负载、动态类型处理

### 推荐缓解措施

1. **基于能力的访问控制** - 资源"感知"谁有访问权限
2. **将所有输入视为不可信** - 标准 HTTP API 安全实践
3. **短期 OAuth 令牌** - 减少令牌泄露影响
4. **细粒度范围** - 将令牌功能限制为特定交易
5. **SDK 尽职调查** - 选择成熟的实现

---

## 审计清单

审计 A2A 实现时的检查项：

- [ ] Agent Card 签名已启用
- [ ] OAuth 令牌生命周期强制执行
- [ ] 细粒度范围定义
- [ ] 敏感数据共享的用户同意机制
- [ ] 流终止策略
- [ ] 输入验证和清理
- [ ] 序列化限制（深度、大小）
- [ ] 基于能力的授权方案

---

## 实现示例

### Python SDK 示例

```python
from a2a import AgentClient, Task

# 创建客户端
client = AgentClient(
    agent_url="https://agent.example.com",
    auth_token="your-token"
)

# 发现代理能力
agent_card = client.get_agent_card()
print(f"Agent: {agent_card.name}")
print(f"Skills: {agent_card.skills}")

# 创建任务
task = client.create_task(
    message="Book a flight from NYC to LA",
    context_id="ctx-12345"
)

# 轮询任务状态
while task.status.state in ["submitted", "working"]:
    task = client.get_task(task.id)
    
if task.status.state == "input-required":
    # 提供所需输入
    response = input(task.status.message.parts[0].text)
    task = client.submit_input(task.id, response)

# 获取结果
if task.status.state == "completed":
    for artifact in task.artifacts:
        print(f"Result: {artifact.data}")
```

### Agent Card 生成器

```python
from a2a import AgentCard, Skill

# 创建 Agent Card
card = AgentCard(
    name="travel-assistant",
    url="https://travel.example.com/a2a",
    version="1.0.0",
    description="旅行助手代理",
    skills=[
        Skill(id="book-flight", name="Flight Booking"),
        Skill(id="book-hotel", name="Hotel Booking"),
        Skill(id="plan-itinerary", name="Itinerary Planning")
    ],
    authentication={
        "schemes": ["oauth2"],
        "oauth2": {
            "authorizationUrl": "https://auth.example.com/oauth/authorize",
            "tokenUrl": "https://auth.example.com/oauth/token",
            "scopes": ["read", "write"]
        }
    }
)

# 导出为 JSON
print(card.to_json())
```

---

## 关键要点

1. **A2A 实现黑盒互操作性** - LLM 代理之间无需定制胶水代码即可通信
2. **安全模型假设类人用户** - LLM 是"困惑的代理人问题的人格化"
3. **早期采用阶段** - 目前生产实现有限，但正在增长（如 GitLab Duo）
4. **需要深度防御** - 结合协议安全与 LLM 特定保护（提示注入缓解）

---

## 参考资源

- [A2A 官方规范](https://google.github.io/A2A)
- [A2A GitHub 仓库](https://github.com/a2aproject/A2A)
- [A2A 协议调查](https://agentprotocol.ai/)
- [A2A 安全分析](https://semgrep.dev/blog/2025/a2a-security-analysis)
- [MCP 安全最佳实践](https://semgrep.dev/blog/2025/mcp-security-best-practices)

---


