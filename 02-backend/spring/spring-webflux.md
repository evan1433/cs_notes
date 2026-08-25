- [WebFlux源码之DispatcherHandler](https://www.cnblogs.com/huiyao/p/14444280.html)

## DispatcherHandler

[spring webflux 核心组件](https://cloud.tencent.com/developer/article/2278305)
### 核心组件

#### 1. DispatcherHandler

DispatcherHandler 是 Spring WebFlux 框架的核心处理器，用于分发和处理 HTTP 请求。DispatcherHandler 通过注册多个 HandlerMapping 和 HandlerAdapter 来处理不同类型的请求，并使用 Reactor 库提供的 Mono 和 Flux 类型来异步处理请求和响应。DispatcherHandler 还提供了自定义过滤器和拦截器的机制，以实现请求和响应的转换和增强。

#### 2. HandlerMapping

HandlerMapping 是 Spring WebFlux 框架的一个接口，用于将 HTTP 请求映射到对应的处理器。HandlerMapping 可以根据请求的 URI、HTTP 方法、请求头等信息来选择合适的处理器，并返回对应的 HandlerFunction 或 ControllerFunction 对象。Spring WebFlux 提供了多种内置的 HandlerMapping 实现，例如 RouterFunctionMapping、RequestMappingHandlerMapping 和 WebSocketHandlerMapping 等。

#### 3. HandlerAdapter

HandlerAdapter 是 Spring WebFlux 框架的一个接口，用于将 HandlerFunction 或 ControllerFunction 对象转换为可处理 HTTP 请求和响应的对象。HandlerAdapter 可以根据请求的类型、响应的类型、请求参数和响应状态等信息来适配不同的 HandlerFunction 和 ControllerFunction 对象，并返回对应的 Mono 或 Flux 类型。Spring WebFlux 提供了多种内置的 HandlerAdapter 实现，例如 RequestMappingHandlerAdapter、WebSocketHandlerAdapter 和 ServerSentEventHttpMessageWriter 等。

#### 4. HandlerFunction

HandlerFunction 是 Spring WebFlux 框架的一个接口，用于处理 HTTP 请求并生成响应。HandlerFunction 接口只包含一个 apply() 方法，该方法接受一个 ServerRequest 对象作为输入，返回一个 Mono 类型的响应对象。开发人员可以实现自己的 HandlerFunction 接口，并使用 RouterFunction 或 RequestMappingHandlerMapping 注册到 DispatcherHandler 中。

#### 5. RouterFunction

RouterFunction 是 Spring WebFlux 框架的一个接口，用于定义 HTTP 请求的路由规则和对应的 HandlerFunction 对象。RouterFunction 接口提供了多个方法来定义 URI、HTTP 方法、请求头和请求参数等条件，并将它们映射到对应的 HandlerFunction 对象。开发人员可以实现自己的 RouterFunction 接口，并使用 RouterFunctionMapping 注册到 DispatcherHandler 中。

#### 6. ServerHttpRequest

ServerHttpRequest 是 Spring WebFlux 框架的一个接口，用于表示 HTTP 请求对象。ServerHttpRequest 包含了请求的 URI、HTTP 方法、请求头、请求体和请求参数等信息，并提供了多个方法来获取和解析这些信息。开发人员可以使用 ServerHttpRequest 对象来访问请求信息，并根据需要进行处理和转换。

#### 7. ServerHttpResponse

ServerHttpResponse 是 Spring WebFlux 框架的一个接口，用于表示 HTTP 响应对象。ServerHttpResponse 包含了响应的状态码、响应头和响应体等信息，并提供了多个方法来设置和修改这些信息。开发人员可以使用 ServerHttpResponse 对象来访问响应信息，并根据需要进行处理和转换。

### 响应式编程模型

Spring WebFlux 框架使用响应式编程模型来处理请求和响应。响应式编程模型是一种基于流和异步编程的编程范式，它可以让开发人员更加灵活和高效地处理数据流和事件流。Spring WebFlux 框架使用 Reactor 库提供的 Mono 和 Flux 类型来表示异步数据流，以支持响应式编程模型。

#### Mono

Mono 是 Reactor 库中的一个类型，表示一个异步的单值容器。Mono 对象可以包含一个值或一个异常，可以用于表示异步操作的结果。Mono 对象可以被订阅者订阅，并在异步操作完成后返回结果。Spring WebFlux 框架使用 Mono 类型来表示 HTTP 响应的主体内容。

#### Flux

Flux 是 Reactor 库中的一个类型，表示一个异步的多值容器。Flux 对象可以包含多个值或一个异常，可以用于表示异步数据流。Flux 对象可以被订阅者订阅，并在异步操作完成后返回数据流。Spring WebFlux 框架使用 Flux 类型来表示 HTTP 响应的数据流内容。