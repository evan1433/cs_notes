---
title: Spring AI 技术文档
description: 基于 Spring AI 官方文档整理的技术参考，涵盖核心概念、ChatClient/ChatModel API、工具调用、Advisor、RAG、向量数据库、MCP 与可观测性
tags:
  - spring-ai
  - ai
  - spring-boot
  - rag
  - llm
date: 2026-08-31
reference: https://docs.spring.io/spring-ai/reference/index.html
---

> 本文基于 [Spring AI 官方参考文档](https://docs.spring.io/spring-ai/reference/index.html)（2.0.x）整理。Spring AI 2.0.x 支持 Spring Boot 4.0.x 与 4.1.x。

## 概述

Spring AI 旨在**简化 AI 功能应用的开发**，无需引入不必要的复杂性。它汲取了 LangChain、LlamaIndex 等 Python 项目的灵感，但并非直接移植——其核心理念是：生成式 AI 的下一波应用不仅面向 Python 开发者，而将覆盖所有主流编程语言。

Spring AI 解决 AI 集成的根本挑战：**将企业数据与 API 连接到 AI 模型**。

### 核心特性一览

| 能力 | 说明 |
|------|------|
| **可移植模型 API** | 跨 AI 提供商统一 Chat、文本生成图像、Embedding 接口，支持同步与流式 |
| **多模型类型** | Chat Completion、Embedding、Text to Image、Audio Transcription、Text to Speech、Moderation |
| **结构化输出** | 将 AI 模型输出映射为 POJO |
| **向量数据库** | 支持 18+ 提供商（PGVector、Redis、Milvus、Pinecone 等）及类 SQL 元数据过滤 |
| **工具/函数调用** | 模型可请求执行客户端工具，获取实时信息或执行操作 |
| **可观测性** | 基于 Micrometer 的指标与链路追踪 |
| **ETL 框架** | 文档摄取管道，用于数据工程 |
| **模型评估** | 评估生成内容、防范幻觉的工具 |
| **MCP 协议** | 消费 MCP 服务器或将 Spring 服务暴露给 AI 生态 |
| **ChatClient API** | 类似 WebClient/RestClient 的流畅 API |
| **Advisor API** | 封装生成式 AI 常见模式，转换 LLM 数据流 |
| **对话记忆与 RAG** | 支持 Chat Memory 和检索增强生成 |

---

## 核心概念

### 模型（Models）

AI 模型是处理和生成信息的算法。Spring AI 支持以语言、图像、音频为输入输出的模型。GPT 中的 "P" 代表预训练（Pre-trained），这使 AI 成为无需深厚 ML 背景即可使用的通用开发工具。

### Prompt 与模板

创建有效 Prompt 的关键在于建立请求上下文，并用用户特定值替换部分内容。Spring AI 使用 StringTemplate 库进行模板渲染，变量语法为 `{variable}`，类似于 Spring MVC 中 "View" 的角色。

### Embeddings（嵌入）

嵌入是文本、图像或视频的**数值表示**——将内容转换为浮点数数组（向量），向量长度称为维度（dimensionality）。通过计算两个向量间的数值距离，可判断内容的语义相似度。嵌入在 RAG 中至关重要：数据被表示为语义空间中的点，相似内容在多维空间中距离更近。

### Tokens（词元）

Token 是 AI 模型工作的基本单元。输入时模型将词转换为 token，输出时再转回词。在英语中，一个 token 约对应一个词的 75%。

关键点：**Token = Money**。托管 AI 模型按 token 用量计费，且模型存在 token 限制（上下文窗口），超出限制的文本不会被处理。

### 结构化输出

AI 模型的输出传统上是 `String`，即使要求返回 JSON 也只是一个字符串而非数据结构。Structured Output 通过精心设计的提示词和类型转换，将模型输出解析为可用的 Java 对象。

### 将数据与 API 带给 AI 模型

模型训练后知识会冻结。让模型访问未训练数据的三种技术：

| 技术 | 说明 |
|------|------|
| **Fine Tuning（微调）** | 传统 ML 技术，调整模型内部权重；资源密集，部分模型不支持 |
| **Prompt Stuffing（提示填充 / RAG）** | 将数据嵌入 Prompt，需在 token 限制内呈现相关数据 |
| **Tool Calling（工具调用）** | 注册工具连接 LLM 到外部系统 API，获取实时数据或执行操作 |

### 检索增强生成（RAG）

RAG 采用批处理式编程模型：从文档读取非结构化数据 → 转换 → 写入向量数据库。其中最重要的转换是**将文档分割为小块**，需保留语义边界（不在段落或表格中间断开），且小块大小应占模型 token 限制的较小比例。

用户提问时，将问题与所有"相似"文档块放入 Prompt 发送给模型——这正是向量数据库的用途：它非常擅长找到相似内容。

---

## 快速开始

### 依赖管理

Spring AI 的 BOM（Bill of Materials）声明了给定版本所有依赖的推荐版本。将其加入项目：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.ai</groupId>
            <artifactId>spring-ai-bom</artifactId>
            <version>2.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

Gradle 对应写法：

```groovy
implementation platform("org.springframework.ai:spring-ai-bom:2.0.0")
```

发布版本在 Maven Central 可用，无需额外仓库配置。使用快照版本（如 `2.0.0-SNAPSHOT`）则需添加 Spring Snapshots 仓库。

> **注意**：若 Maven `settings.xml` 中配置了 `mirrorOf=*` 的镜像，通配符会将所有请求重定向到镜像，导致无法访问 Spring 快照仓库。需修改为 `mirrorOf=*,!spring-snapshots,!central-portal-snapshots` 排除 Spring 仓库。

### 第一个 AI 应用

最简方式：通过 Spring Initializr（[start.spring.io](https://start.spring.io/)）选择所需 AI 模型和向量数据库，然后注入自动配置的 `ChatClient.Builder`：

```java
@RestController
class MyController {

    private final ChatClient chatClient;

    public MyController(ChatClient.Builder chatClientBuilder) {
        this.chatClient = chatClientBuilder.build();
    }

    @GetMapping("/ai")
    String generation(String userInput) {
        return this.chatClient.prompt()
            .user(userInput)
            .call()
            .content();
    }
}
```

> `call()` 方法向 AI 模型发送请求，`content()` 以 `String` 返回模型响应。

---

## ChatModel API

ChatModel API 提供与各种 AI 模型交互的可移植接口，遵循 Spring 的模块化与可互换理念。

### 核心接口

```java
public interface ChatModel extends Model<Prompt, ChatResponse>, StreamingChatModel {

    default String call(String message) { ... }

    @Override
    ChatResponse call(Prompt prompt);
}
```

```java
public interface StreamingChatModel extends StreamingModel<Prompt, ChatResponse> {

    default Flux<String> stream(String message) { ... }

    @Override
    Flux<ChatResponse> stream(Prompt prompt);
}
```

`call(String)` 简化入门使用；实际应用中更常用 `call(Prompt)` 返回 `ChatResponse`。`stream()` 方法则使用 Reactive Flux API 流式返回响应。

### Prompt 与 Message

`Prompt` 封装了一组 `Message` 对象和可选的模型请求选项：

```java
public class Prompt implements ModelRequest<List<Message>> {
    private final List<Message> messages;
    private ChatOptions modelOptions;
    // ...
}
```

`Message` 接口按对话角色（MessageType）区分消息类别——如 `system`、`user`、`assistant`。OpenAI 识别 `system`、`user`、`function`、`assistant` 等角色。

### ChatOptions

`ChatOptions` 定义可传递给 AI 模型的可移植选项：

```java
public interface ChatOptions extends ModelOptions {
    String getModel();
    Double getFrequencyPenalty();
    Integer getMaxTokens();
    Double getPresencePenalty();
    List<String> getStopSequences();
    Double getTemperature();
    Integer getTopK();
    Double getTopP();
    ChatOptions.Builder<?> mutate();
}
```

配置流程：启动时初始化 ChatModel 的默认选项 → 运行时 Prompt 中的选项**完全覆盖**启动选项 → 使用 `ChatClient` 可增量覆盖。

### ChatResponse 与 Generation

```java
public class ChatResponse implements ModelResponse<Generation> {
    private final ChatResponseMetadata chatResponseMetadata;
    private final List<Generation> generations;
    // ...
}
```

`ChatResponse` 持有模型输出，每个 `Generation` 包含一个 `AssistantMessage` 及相关元数据（如 token 用量）。

### 支持的实现

- [OpenAI Chat Completion](https://docs.spring.io/spring-ai/reference/api/chat/openai-chat.html)（流式、多模态、函数调用）
- [Ollama Chat Completion](https://docs.spring.io/spring-ai/reference/api/chat/ollama-chat.html)（流式、多模态、函数调用）
- Amazon Bedrock、Mistral AI、Anthropic 等

---

## ChatClient API

`ChatClient` 提供与 AI 模型通信的**流畅 API（Fluent API）**，同时支持同步与流式编程模型。

### 创建 ChatClient

**方式一：自动配置的 Builder（推荐）**

Spring Boot 自动配置会创建 prototype 作用域的 `ChatClient.Builder` bean：

```java
@Configuration
class ChatClientConfig {
    @Bean
    ChatClient defaultChatClient(ChatClient.Builder builder) {
        return builder.build();
    }

    @Bean
    ChatClient customChatClient(ChatClient.Builder builder) {
        return builder.defaultSystem("You are a helpful assistant.").build();
    }
}
```

> Builder 为 prototype 作用域，每个注入点获得新实例。

**方式二：多模型场景**

> ⚠️ 重要：直接使用 `ChatClient.create(chatModel)` 或 `ChatClient.builder(chatModel)` 会**绕过自动配置**，导致可观测性和 `ChatClientBuilderCustomizer` bean 被忽略。应注入 `ChatClientBuilderConfigurer` 来创建自定义 builder，以保留可观测性：

```java
@Configuration
public class ChatClientConfig {

    @Bean
    @Primary
    public ChatClient openAiChatClient(OpenAiChatModel chatModel,
            ChatClientBuilderConfigurer configurer,
            ObjectProvider<ObservationRegistry> observationRegistry,
            ObjectProvider<ChatClientObservationConvention> chatClientObservationConvention,
            ObjectProvider<AdvisorObservationConvention> advisorObservationConvention,
            ObjectProvider<ToolCallingAdvisor.Builder<?>> toolCallingAdvisorBuilder) {
        return buildChatClient(chatModel, configurer, observationRegistry,
                chatClientObservationConvention, advisorObservationConvention,
                toolCallingAdvisorBuilder);
    }

    private ChatClient buildChatClient(ChatModel chatModel,
            ChatClientBuilderConfigurer configurer, /* ... */) {
        ChatClient.Builder builder = ChatClient.builder(chatModel,
                observationRegistry.getIfUnique(() -> ObservationRegistry.NOOP),
                chatClientObservationConvention.getIfUnique(),
                advisorObservationConvention.getIfUnique(),
                toolCallingAdvisorBuilder.getIfAvailable());
        return configurer.configure(builder).build();
    }
}
```

当上下文中存在多个 `ChatModel` bean 时，用 `@Primary` 标记其一解决歧义，通过 `@Qualifier` 注入使用。

### Fluent API 入口

`prompt()` 方法有三种重载：

| 方法 | 用途 |
|------|------|
| `prompt()` | 无参数，逐步构建 user、system 等部分 |
| `prompt(Prompt prompt)` | 传入已创建的 Prompt 实例 |
| `prompt(String content)` | 便捷方法，直接传入用户文本 |

常用请求构建方法：

| 方法 | 说明 |
|------|------|
| `.user(String)` / `.user(Consumer<UserSpec>)` | 设置用户消息 |
| `.system(String)` / `.system(Consumer<PromptSystemSpec>)` | 设置系统消息 |
| `.tools(Object…)` | 注册工具 |
| `.advisors(Advisor...)` / `.advisors(Consumer<AdvisorSpec>)` | 添加 Advisor 及参数 |
| `.messages(Message…)` | 直接传入消息 |
| `.options(ChatOptions.Builder)` | 设置运行时选项 |
| `.toolContext(Map<String, Object>)` | 工具执行上下文 |
| `.templateRenderer(TemplateRenderer)` | 设置模板渲染器 |

### Prompt 模板

```java
String answer = ChatClient.create(chatModel).prompt()
    .user(u -> u
            .text("Tell me the names of 5 movies whose soundtrack was composed by {composer}")
            .param("composer", "John Williams"))
    .call()
    .content();
```

默认使用 `StTemplateRenderer`（基于 StringTemplate），变量语法为 `{}`。若提示词包含 JSON，可自定义分隔符避免语法冲突：

```java
.templateRenderer(StTemplateRenderer.builder()
    .startDelimiterToken('<')
    .endDelimiterToken('>')
    .build())
```

> ChatClient 上配置的 `TemplateRenderer` 仅作用于 builder 链中的提示内容，**不影响** Advisor 内部使用的模板（如 `QuestionAnswerAdvisor`）。

### call() vs stream()

> **关键机制**：调用 `call()` 本身**不触发模型执行**，仅告知使用同步还是流式。实际调用发生在 `content()`、`chatResponse()`、`responseEntity()` 等终端方法时。

**call()（同步）返回值：**

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `content()` | `String` | 响应字符串 |
| `chatResponse()` | `ChatResponse` | 含多个 Generation 和元数据（token 用量） |
| `chatClientResponse()` | `ChatClientResponse` | 含 ChatResponse + 执行上下文（可访问 Advisor 数据） |
| `entity(...)` | `T` | 映射为 Java 实体 |
| `responseEntity(...)` | `ResponseEntity` | 同时返回 ChatResponse 和实体 |

**stream()（流式）返回值：**

| 方法 | 返回类型 |
|------|---------|
| `content()` | `Flux<String>` |
| `chatResponse()` | `Flux<ChatResponse>` |
| `chatClientResponse()` | `Flux<ChatClientResponse>` |

```java
Flux<String> output = chatClient.prompt()
    .user("Tell me a joke")
    .stream()
    .content();
```

### 默认值

在 `@Configuration` 类中设置默认系统文本，简化运行时代码：

```java
@Configuration
class Config {
    @Bean
    ChatClient chatClient(ChatClient.Builder builder) {
        return builder
            .defaultSystem("You are a friendly chat bot that answers question in the voice of a {voice}")
            .build();
    }
}
```

运行时注入参数：

```java
@GetMapping("/ai")
Map<String, String> completion(@RequestParam(defaultValue = "Tell me a joke") String message,
        String voice) {
    return Map.of("completion",
            this.chatClient.prompt()
                    .system(sp -> sp.param("voice", voice))
                    .user(message)
                    .call()
                    .content());
}
```

Builder 级别其他默认值：`defaultOptions`、`defaultTools`、`defaultToolContext`、`defaultUser`、`defaultTemplateRenderer`、`defaultAdvisors`，均可在运行时用不带 `default` 前缀的方法覆盖。使用 `mutate()` 可基于现有配置创建新的 ChatClient。

---

## 结构化输出（Structured Output）

LLM 是文本输入、文本输出系统。当下游代码需要按字段路由、持久化值或根据结果分支时，文本必须转为类型化记录。结构化输出通过 `.entity(...)` 桥接这一差距。

### 类型化响应

```java
record ActorsFilms(String actor, List<String> movies) {}
```

```java
ActorsFilms films = chatClient.prompt()
    .user("Generate the filmography for a random actor.")
    .call()
    .entity(ActorsFilms.class);
```

Spring AI 在背后做了三件事：将 record 转为 JSON Schema → Schema 追加到 Prompt 的系统上下文 → 模型 JSON 响应交由类型转换器解析回 record。

### 泛型类型

```java
List<ActorsFilms> films = chatClient.prompt()
    .user("Generate filmographies for three random actors.")
    .call()
    .entity(new ParameterizedTypeReference<List<ActorsFilms>>() {});
```

### 可靠性开关（EntityParamSpec）

所有 `.entity()` 重载接受可选的 `Consumer<EntityParamSpec>`，提供两个独立、可组合的行为：

| 开关 | 作用 |
|------|------|
| `validateSchema()` | 验证 JSON 响应，失败时自动带错误反馈重试（默认最多 3 次） |
| `useProviderStructuredOutput()` | 将 schema 作为 API 级约束发送给提供商，而非提示文本 |

```java
ActorsFilms films = chatClient.prompt()
    .user("Generate the filmography for a random actor.")
    .call()
    .entity(ActorsFilms.class, spec -> spec
        .useProviderStructuredOutput()
        .validateSchema());
```

两者解决不同问题，组合使用可最大限度减少畸形输出。

### 速查表

| 需求 | 用法 |
|------|------|
| 默认（所有提供商可用） | `.entity(Type.class)` |
| 泛型 `List<T>` 等 | `.entity(new ParameterizedTypeReference<…>() {})` |
| 不因畸形输出失败 | `.entity(Type.class, spec -> spec.validateSchema())` |
| 提供商级更强保证 | `.entity(Type.class, spec -> spec.useProviderStructuredOutput())` |
| 两者结合 | `.entity(Type.class, spec -> spec.useProviderStructuredOutput().validateSchema())` |
| 需 token 用量/元数据 | `.responseEntity(...)` |
| 模型包裹 JSON 在 markdown 围栏，或非 JSON 格式 | 实现 `StructuredOutputConverter<T>` 传入 `.entity()` |
| 流式响应 | 不支持，`.entity()` 仅限 `.call()` |

> 结构化输出是尽力而为的，模型不保证返回所请求结构。正确性重要时使用 `validateSchema()` 和/或 `useProviderStructuredOutput()`。

---

## 工具调用（Tool Calling）

工具调用是 AI 模型调用应用程序定义函数并处理其结果的能力，是构建 Agent 系统的基石。

> **安全机制**：模型只负责请求调用工具并提供参数，**由应用程序负责执行工具并返回结果**。模型永远不会直接访问工具背后的 API。

### Spring AI 2.0 架构

Spring AI 2.0 将工具调用循环提升为一等公民、可组合组件，集成在 `ChatClient` 的 advisor 链中：

1. 定义工具并传递给 `ChatClient`
2. `ChatClient` 自动注册 `ToolCallingAdvisor` 驱动循环
3. 模型决定调用哪些工具；`ToolCallingManager` 执行它们
4. 循环持续直到模型产出无工具调用的响应

### 声明式：`@Tool` 注解

```java
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.context.i18n.LocaleContextHolder;

class DateTimeTools {

    @Tool(description = "Get the current date and time in the user's timezone")
    String getCurrentDateTime() {
        return LocalDateTime.now().atZone(LocaleContextHolder.getTimeZone().toZoneId()).toString();
    }

    @Tool(description = "Set a user alarm for the given time, provided in ISO-8601 format")
    void setAlarm(String time) {
        LocalDateTime alarmTime = LocalDateTime.parse(time, DateTimeFormatter.ISO_DATE_TIME);
        System.out.println("Alarm set for " + alarmTime);
    }
}
```

```java
String response = ChatClient.create(chatModel)
        .prompt("Can you set an alarm 10 minutes from now?")
        .tools(new DateTimeTools())
        .call()
        .content();
```

模型自动决定先调用 `getCurrentDateTime()`，再用计算出的时间调用 `setAlarm(...)`，Spring AI 自动处理完整往返。

`@Tool` 注解属性：

| 属性 | 说明 |
|------|------|
| `name` | 工具名称，默认方法名，在工具集中必须唯一 |
| `description` | 工具功能和何时使用的说明（**强烈建议提供**） |
| `returnDirect` | 直接将结果返回调用者，而非回传模型 |
| `resultConverter` | 指定 `ToolCallResultConverter` 进行结果转换 |

参数描述使用 `@ToolParam`：

```java
@Tool(description = "Get the weather for a city at a specific time")
public String getWeather(
        @ToolParam(description = "City name") String city,
        @ToolParam(description = "Time in ISO-8601 format", required = false) String at) {
    return weatherService.fetch(city, at);
}
```

### 三种定义方式

| 风格 | 适用场景 |
|------|---------|
| 声明式 `@Tool` | 拥有方法且希望最小编码 |
| `MethodToolCallback` | 编程式控制基于方法的工具 |
| `FunctionToolCallback` | 暴露 `Function`/`Supplier`/`Consumer` lambda 或方法引用 |

**编程式 FunctionToolCallback：**

```java
FunctionToolCallback callback = FunctionToolCallback.builder("currentWeather", weatherService::getWeather)
    .description("Get the weather in location")
    .inputType(WeatherRequest.class)
    .build();
```

> ⚠️ Spring AI 2.0 移除了 1.x 中裸 `Function` Bean 按名称解析的模式，工具必须注册为显式 `ToolCallback` Bean。

### 向 ChatClient 传递工具

```java
// 按调用传递——工具仅对该次请求可用
chatClient.prompt(...)
    .tools(new WeatherTools(), currentWeather)
    .call();

// 作为默认值——每次请求都可用
ChatClient client = ChatClient.builder(chatModel)
    .defaultTools(new WeatherTools(), currentWeather)
    .build();
```

最终工具列表 = `.defaultTools()` ∪ `.tools()`。高风险和破坏性工具应逐调用添加。

### ToolContext（工具上下文）

`ToolContext` 用于传递非模型数据（租户 ID、用户 ID 等）给工具方法。**该数据不会发送给模型**：

```java
class CustomerTools {
    @Tool(description = "Retrieve customer information")
    Customer getCustomerInfo(Long id, ToolContext toolContext) {
        return customerRepository.findById(id, toolContext.getContext().get("tenantId"));
    }
}

String response = ChatClient.create(chatModel)
        .prompt("Tell me more about the customer with ID 42")
        .tools(new CustomerTools())
        .toolContext(Map.of("tenantId", "acme"))
        .call()
        .content();
```

### Return Direct（直接返回）

`returnDirect = true` 时结果绕过模型直接返回调用者，适用于工具输出即最终答案的场景（如 RAG 检索）。若一轮中请求多个工具调用，`returnDirect` 仅当**所有**被调用工具均为 `returnDirect = true` 时才生效。

### 工具调用限制

```java
ToolCallingManager toolCallingManager = ToolCallingManager.builder()
    .maxCallsPerTool(40)                           // 每工具默认
    .maxCallsPerTool("search", 10)                  // 覆盖单个工具
    .excludeToolFromLimit("getCurrentWeather")      // 不限制此工具
    .maxTotalToolCalls(150)                         // 所有工具总计上限
    .onLimitExceeded(ToolCallLimitBehavior.THROW)   // 或 RETURN_ERROR_RESPONSE
    .build();
```

### 用户控制的工具执行

需要完全掌控每次迭代时（外部审批门控、SSE 中间进度转发等），禁用自动注册并手动驱动循环：

```java
ChatClientResponse response = chatClient.prompt()
    .user(question)
    .options(chatOptions)
    .advisors(AdvisorParams.toolCallingAdvisorAutoRegister(false))  // 禁用自动注册
    .call()
    .chatClientResponse();

while (response.chatResponse() != null && response.chatResponse().hasToolCalls()) {
    ToolExecutionResult result = toolCallingManager.executeToolCalls(prompt, response.chatResponse());
    prompt = new Prompt(result.conversationHistory(), chatOptions);
    response = chatClient.prompt()
        .messages(result.conversationHistory())
        .options(chatOptions)
        .advisors(AdvisorParams.toolCallingAdvisorAutoRegister(false))
        .call()
        .chatClientResponse();
}
```

全局禁用：`spring.ai.chat.client.tool-calling.enabled=false`。

---

## Advisor API

Advisors API 提供拦截、修改和增强 AI 驱动交互的灵活方式：封装重复出现的生成式 AI 模式、转换 LLM 数据流、提供跨模型用例可移植性。

### 核心组件

| 组件 | 作用 |
|------|------|
| `CallAdvisor` / `CallAdvisorChain` | 非流式场景 |
| `StreamAdvisor` / `StreamAdvisorChain` | 流式场景 |
| `ChatClientRequest` | 未封装的 Prompt 请求 |
| `ChatClientResponse` | Chat Completion 响应 |

两者均持有 `advise-context`，用于在 advisor 链中**共享状态**。

### 接口定义

```java
public interface Advisor extends Ordered {
    String getName();
}

public interface CallAdvisor extends Advisor {
    ChatClientResponse adviseCall(ChatClientRequest chatClientRequest, CallAdvisorChain callAdvisorChain);
}

public interface StreamAdvisor extends Advisor {
    Flux<ChatClientResponse> adviseStream(ChatClientRequest chatClientRequest, StreamAdvisorChain streamAdvisorChain);
}
```

### 顺序（Ordering）

执行顺序由 `getOrder()` 决定，**值越小越先执行**。链以**栈**方式运作：

- 链中第一个 advisor **最先处理请求，最后处理响应**
- `Ordered.HIGHEST_PRECEDENCE`（`Integer.MIN_VALUE`）→ 最先处理请求
- 较高的值 = 较低优先级

> 若需在输入端和输出端都最先处理，应使用两个独立 advisor 配置不同 order 值，通过 context 共享状态。

### 请求/响应流转

1. Spring AI 根据 Prompt 创建 `ChatClientRequest`，附带空 context
2. 每个 advisor 处理请求（可修改），也可阻断请求（自己负责填充响应）
3. 最后一个 advisor（框架自动添加）将请求发送给 Chat Model
4. 响应沿链回传，转为 `ChatClientResponse`
5. 每个 advisor 可处理或修改响应
6. 最终 `ChatClientResponse` 返回给客户端

### 内置 Advisors

| 类别 | Advisor | 说明 |
|------|---------|------|
| Chat Memory | `MessageChatMemoryAdvisor` | 检索记忆并作为消息集合加入 prompt |
| | `VectorStoreChatMemoryAdvisor` | 从 VectorStore 检索记忆加入 system 文本 |
| 问答/RAG | `QuestionAnswerAdvisor` | 使用向量存储实现 Naive RAG |
| | `RetrievalAugmentationAdvisor` | 基于 Modular RAG 架构实现常见 RAG 流程 |
| 推理增强 | `ReReadingAdvisor` | 实现 Re2 重读策略，增强 LLM 对输入理解 |
| 工具调用 | `ToolCallingAdvisor` | 处理工具调用循环，由 ChatClient 自动注册 |
| 内容安全 | `SafeGuardAdvisor` | 防止模型生成有害或不当内容 |

### 自定义 Advisor

观察型（不修改数据）示例：

```java
public class SimpleLoggerAdvisor implements CallAdvisor, StreamAdvisor {

    private static final Logger logger = LoggerFactory.getLogger(SimpleLoggerAdvisor.class);

    @Override
    public String getName() { return this.getClass().getSimpleName(); }

    @Override
    public int getOrder() { return 0; }

    @Override
    public ChatClientResponse adviseCall(ChatClientRequest chatClientRequest,
            CallAdvisorChain callAdvisorChain) {
        logRequest(chatClientRequest);
        ChatClientResponse chatClientResponse = callAdvisorChain.nextCall(chatClientRequest);
        logResponse(chatClientResponse);
        return chatClientResponse;
    }

    @Override
    public Flux<ChatClientResponse> adviseStream(ChatClientRequest chatClientRequest,
            StreamAdvisorChain streamAdvisorChain) {
        logRequest(chatClientRequest);
        Flux<ChatClientResponse> chatClientResponses =
                streamAdvisorChain.nextStream(chatClientRequest);
        return new ChatClientMessageAggregator()
                .aggregateChatClientResponse(chatClientResponses, this::logResponse);
    }
}
```

启用日志：

```
logging.level.org.springframework.ai.chat.client.advisor=DEBUG
```

> 建议将 `SimpleLoggerAdvisor` 添加在 Advisor 链**末端**；生产环境注意不要记录敏感信息。

增强型（基于 `BaseAdvisor` 的 Re2 示例）：

```java
public class ReReadingAdvisor implements BaseAdvisor {

    private static final String DEFAULT_RE2_ADVISE_TEMPLATE = """
            {re2_input_query}
            Read the question again: {re2_input_query}
            """;

    @Override
    public ChatClientRequest before(ChatClientRequest chatClientRequest, AdvisorChain advisorChain) {
        String augmentedUserText = PromptTemplate.builder()
            .template(this.re2AdviseTemplate)
            .variables(Map.of("re2_input_query",
                    chatClientRequest.prompt().getUserMessage().getText()))
            .build()
            .render();

        return chatClientRequest.mutate()
            .prompt(chatClientRequest.prompt().augmentUserMessage(augmentedUserText))
            .build();
    }

    @Override
    public ChatClientResponse after(ChatClientResponse chatClientResponse, AdvisorChain advisorChain) {
        return chatClientResponse;
    }
}
```

---

## 聊天记忆（Chat Memory）

聊天模型 API 是**无状态**的，每次请求必须携带历史消息。

### 核心接口与实现

- `ChatMemory` 接口：提供添加消息、检索消息、清除历史的方法
- `MessageWindowChatMemory`：维护指定最大数量的消息窗口（**默认 20 条**），超限时淘汰旧消息但**保留系统消息**
- 由 `ChatMemoryRepository` 抽象支撑，实现包括：`InMemoryChatMemoryRepository`、`JdbcChatMemoryRepository`、`CassandraChatMemoryRepository`、`Neo4jChatMemoryRepository`、`MongoChatMemoryRepository`、`RedisChatMemoryRepository`

### 关键要求

> `ChatMemory.CONVERSATION_ID` 参数对所有 memory advisor 是**必需的**，必须通过 `.advisors(a -> a.param(ChatMemory.CONVERSATION_ID, conversationId))` 提供。**省略它会在运行时抛出 `IllegalArgumentException`，没有默认的 conversation ID。**

### 记忆与工具循环

`MessageChatMemoryAdvisor` 默认顺序 `HIGHEST_PRECEDENCE + 200`（低于 `ToolCallingAdvisor` 的 `+300`），位于循环**外部**：

- 循环开始前加载一次历史
- 循环结束后仅持久化最终用户消息和最终助手消息
- 永不看到工具调用请求或工具响应消息

要让模型在后续轮次看到完整工具记录，将记忆 advisor 置于循环**内部**：

```java
var chatMemoryAdvisor = MessageChatMemoryAdvisor.builder(chatMemory)
    .order(BaseAdvisor.HIGHEST_PRECEDENCE + 400)  // 循环内（ToolCallingAdvisor 之后）
    .build();
```

---

## RAG 检索增强生成

### QuestionAnswerAdvisor

实现 Naive RAG 问答模式，基于用户文本附加相关上下文信息来增强 prompt：

```java
var chatClient = ChatClient.builder(chatModel)
    .defaultAdvisors(
        MessageChatMemoryAdvisor.builder(chatMemory).build(),
        QuestionAnswerAdvisor.builder(vectorStore).build()
    )
    .build();

String response = this.chatClient.prompt()
    .advisors(a -> a
        .param(ChatMemory.CONVERSATION_ID, conversationId))
    .user(userText)
    .call()
    .content();
```

通过 `chatClientResponse()` 可访问 RAG 流程中检索到的相关文档。`QuestionAnswerAdvisor` 有自己的模板定制机制（独立于 ChatClient 的 `TemplateRenderer`）。

### RetrievalAugmentationAdvisor

基于 `org.springframework.ai.rag` 包的构建块，遵循 Modular RAG 架构实现常见 RAG 流程，比 `QuestionAnswerAdvisor` 更灵活可组合。

---

## ETL 数据管道

Spring AI 的 ETL 管道是 RAG 场景中数据处理的核心框架，协调从原始数据源到结构化向量存储的数据流。

### 三大组件

| 组件 | 接口 | 职责 |
|------|------|------|
| `DocumentReader` | `Supplier<List<Document>>` | 从 PDF、文本等创建 Document |
| `DocumentTransformer` | `Function<List<Document>, List<Document>>` | 分割、丰富元数据等 |
| `DocumentWriter` | `Consumer<List<Document>>` | 写入向量数据库或文件 |

```java
// 函数式风格
vectorStore.accept(tokenTextSplitter.apply(pdfReader.get()));

// 领域表达风格
vectorStore.write(tokenTextSplitter.split(pdfReader.read()));
```

### DocumentReaders（读取器）

| 读取器 | 说明 |
|------|------|
| `JsonReader` | 将 JSON 转为 Document，支持 JSON Pointer 定位 |
| `TextReader` | 读取纯文本为单个 Document（不适合超大文件） |
| `JsoupDocumentReader` | 使用 JSoup 处理 HTML，CSS 选择器提取元素 |
| `MarkdownDocumentReader` | 处理 Markdown，标题→元数据，段落→内容 |
| `PagePdfDocumentReader` | 使用 PdfBox 按页分割 PDF |
| `ParagraphPdfDocumentReader` | 利用 PDF 目录按段落分割（需 PDF 含 TOC） |
| `TikaDocumentReader` | 使用 Apache Tika 提取多种格式（PDF、DOC/DOCX、PPT 等） |

### TokenTextSplitter

基于 token 数量分割文本，适配 AI 模型上下文窗口：

```java
TokenTextSplitter splitter = TokenTextSplitter.builder()
    .withChunkSize(1000)              // 每块目标 token 数（默认 800）
    .withMinChunkSizeChars(400)       // 最小字符数（默认 350）
    .withMaxNumChunks(5000)           // 最大块数（默认 10000）
    .withKeepSeparator(true)          // 保留分隔符
    .build();
```

支持中文标点的国际化分割：

```java
TokenTextSplitter splitter = TokenTextSplitter.builder()
    .withChunkSize(800)
    .withPunctuationMarks(List.of('。', '？', '！', '；'))
    .build();
```

### AI 增强转换器

- `KeywordMetadataEnricher`：使用 AI 模型提取关键词，存入元数据键 `excerpt_keywords`
- `SummaryMetadataEnricher`：生成文档摘要，元数据键 `section_summary`、`prev_section_summary`、`next_section_summary`

### 完整管道示例

```java
PagePdfDocumentReader pdfReader = new PagePdfDocumentReader("classpath:/sample1.pdf");
TokenTextSplitter splitter = TokenTextSplitter.builder().withChunkSize(800).build();
VectorStore vectorStore = /* 初始化向量存储 */;

// 读取 PDF → 分割 → 写入向量存储
vectorStore.write(splitter.split(pdfReader.read()));
```

---

## 向量数据库（Vector Store）

Spring AI 通过 `VectorStore` 接口为向量数据库提供统一抽象 API，支持相似性搜索（而非 SQL 精确匹配），常用于 RAG 流程。

### 接口定义

```java
public interface VectorStore extends DocumentWriter, VectorStoreRetriever {
    void add(List<Document> documents);
    void delete(List<String> idList);
    void delete(Filter.Expression filterExpression);
    default void delete(String filterExpression) { ... }
    default <T> Optional<T> getNativeClient() { return Optional.empty(); }
}
```

只读接口 `VectorStoreRetriever` 仅暴露相似性搜索功能（最小权限原则）：

```java
@FunctionalInterface
public interface VectorStoreRetriever {
    List<Document> similaritySearch(SearchRequest request);
    default List<Document> similaritySearch(String query) { ... }
}
```

### 相似性搜索

```java
SearchRequest request = SearchRequest.builder()
    .query(question)               // 查询字符串
    .topK(5)                        // 返回最多 5 个结果（默认 4）
    .similarityThreshold(0.7)       // 相似度阈值 [0,1]，默认 0.0
    .filterExpression("country == 'UK'")  // 元数据过滤
    .build();
List<Document> docs = retriever.similaritySearch(request);
```

### 元数据过滤

SQL 风格字符串：

```java
"genre == 'drama' && year >= 2020"
"genre in ['comedy', 'documentary', 'drama']"
```

流式 DSL（`FilterExpressionBuilder`）：

```java
FilterExpressionBuilder b = new FilterExpressionBuilder();
Expression exp = b.and(b.eq("genre", "drama"), b.gte("year", 2020)).build();
```

支持的操作符：比较（`==`、`!=`、`>`、`>=`、`<`、`<=`）、逻辑（`AND`/`&&`、`OR`/`||`）、集合（`IN`、`NIN`）、否定（`NOT`）、空值（`IS NULL`、`IS NOT NULL`）。

### 支持的提供商

共 18+ 种：Azure Vector Search、Pinecone、MongoDB Atlas、Elasticsearch、OpenSearch、Typesense、Cassandra、Chroma、Milvus、Qdrant、Weaviate、Redis、PGVector、MariaDB、Oracle、Neo4j、GemFire 等。

---

## Embedding 模型 API

嵌入将文本、图像、视频转为浮点数数组（向量），捕获内容语义关系。

```java
public interface EmbeddingModel extends Model<EmbeddingRequest, EmbeddingResponse> {

    EmbeddingResponse call(EmbeddingRequest request);

    float[] embed(Document document);

    default float[] embed(String text) { ... }

    default List<float[]> embed(List<String> texts) { ... }

    default EmbeddingResponse embedForResponse(List<String> texts) { ... }

    default int dimensions() { ... }
}
```

- `embed(String)` / `embed(Document)`：转换单个文本为向量
- `embed(List<String>)`：批量嵌入
- `embedForResponse(List<String>)`：返回含元数据的完整响应
- `dimensions()`：获取向量维度

支持实现：OpenAI、Ollama、Transformers (ONNX)、PostgresML、Bedrock Cohere/Titan、Vertex AI、Mistral AI 等。

---

## MCP 模型上下文协议

MCP 是标准化协议，使 AI 模型能够以结构化方式与外部工具和资源交互——如同 AI 模型与现实世界之间的桥梁，支持数据库、API、文件系统等外部服务的一致接口。

### Java SDK 三层架构

| 层 | 组件 | 职责 |
|----|------|------|
| 客户端/服务器层 | `McpClient`、`McpServer` | 主应用逻辑和协议操作 |
| 会话层 | `McpSession` | 连接管理、协议版本/能力协商 |
| 传输层 | `McpTransport` | JSON-RPC 消息序列化，支持 STDIO、HTTP/SSE、Streamable-HTTP 等 |

### Spring AI MCP 集成

通过 Boot Starters 简化集成，开发者可同时参与 MCP 生态两侧——构建消费 MCP 服务器的 AI 应用，以及创建将 Spring 服务暴露给 AI 社区的 MCP 服务器。

**客户端 Starters：**

| Starter | 传输支持 |
|---------|---------|
| `spring-ai-starter-mcp-client` | STDIO、Servlet Streamable-HTTP、Stateless、SSE |
| `spring-ai-starter-mcp-client-webflux` | WebFlux Streamable-HTTP、Stateless、SSE |

**服务器端 Starters：**

| Starter | 传输支持 |
|---------|---------|
| `spring-ai-starter-mcp-server` | STDIO（`spring.ai.mcp.server.stdio=true`） |
| `spring-ai-starter-mcp-server-webmvc` | SSE、Streamable-HTTP、Stateless Streamable-HTTP |
| `spring-ai-starter-mcp-server-webflux` | 同上（Reactive） |

### MCP 注解

通过声明式注解简化 MCP 操作创建：

- 服务器注解：`@McpTool`、`@McpResource`、`@McpPrompt`、`@McpComplete`
- 客户端注解：`@McpLogging`、`@McpSampling`、`@McpElicitation`、`@McpProgress`
- 自动发现：可配置包扫描的包含/排除
- 自动生成工具参数的 JSON Schema

---

## 可观测性（Observability）

Spring AI 基于 Spring Boot Actuator + Micrometer，为以下组件提供指标和链路追踪：

- `ChatClient`（含 `Advisor`）
- `ChatModel`
- `EmbeddingModel`
- `ImageModel`
- `VectorStore`

### 设计原则

- **低基数键** → 同时添加到 metrics 和 traces
- **高基数键** → 仅添加到 traces

### ChatClient 可观测性

调用 `call()` 或 `stream()` 时记录 `spring.ai.chat.client` 观测数据。低基数键包括 `gen_ai.operation.name`（固定 `framework`）、`gen_ai.system`（固定 `spring_ai`）、`spring.ai.chat.client.stream`；高基数键包括 advisor 列表、会话 ID、工具名称。

Prompt/Completion 日志配置：

```yaml
spring:
  ai:
    chat:
      client:
        observations:
          log-prompt: false      # 是否记录 prompt 内容（默认 false）
          log-completion: false  # 是否记录 completion 内容（默认 false）
```

> ⚠️ 启用后存在**暴露敏感/隐私信息的风险**。

### Token 用量指标

```
gen_ai_client_token_usage_total  (Counter, 单位: tokens)

标签:
  gen_ai_token_type=input   → 发送给模型的 prompt tokens
  gen_ai_token_type=output  → 模型返回的 completion tokens
  gen_ai_token_type=total   → input + output
```

### VectorStore 可观测性

度量 `query`、`add`、`remove` 操作耗时，低基数键包括 `db.operation.name` 和 `db.system`（如 `pg_vector`、`redis`、`chroma`、`milvus` 等 17 种）。

---

## 支持的 AI 模型提供商

Spring AI 提供可移植 API，支持所有主要 AI 模型提供商：

| 提供商 | 支持能力 |
|--------|---------|
| OpenAI | Chat、Embedding、Image、Audio、Moderation |
| Anthropic | Chat（流式、函数调用） |
| Google Vertex AI | Chat、Embedding |
| Amazon Bedrock | Chat、Embedding |
| Ollama | Chat（流式、多模态、函数调用） |
| Mistral AI | Chat、Embedding |
| Azure OpenAI | Chat、Embedding |
| HuggingFace | Chat、Embedding |

> 完整列表和对比见 [Chat Models Comparison](https://docs.spring.io/spring-ai/reference/api/chat/comparison.html)。

---

## 参考资料

- [Spring AI 官方文档](https://docs.spring.io/spring-ai/reference/index.html)
- [Spring AI GitHub](https://github.com/spring-projects/spring-ai)
- [Spring AI 示例集合](https://github.com/spring-ai-community/awesome-spring-ai)
- [MCP 规范](https://modelcontextprotocol.io/)
- [OpenTelemetry 生成式 AI 语义约定](https://opentelemetry.io/docs/specs/semconv/gen-ai/)

---

> 相关笔记：[[spring-boot3]]、[[docker]]、[[agent-scope-java]]
