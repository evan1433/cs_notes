---
title: FastAPI 使用指南
description: 从零搭建 FastAPI 服务，掌握路由、数据校验、依赖注入、数据库、测试与部署
tags:
  - python
  - fastapi
  - backend
  - web-api
date: 2026-07-20
aliases:
  - FastAPI
  - fast-api
---

# FastAPI 使用指南

FastAPI 是一个基于 Python 类型提示构建 Web API 的 ASGI 框架。它以 Starlette 处理 Web 能力，
以 Pydantic 完成数据解析与校验，并能根据类型声明自动生成 OpenAPI 文档。

本文使用 Python 3.10+ 和 Pydantic v2 语法，目标是从一个可运行的单文件应用开始，
逐步扩展到结构化、可测试、可部署的项目。

## 1. 适用场景与核心概念

FastAPI 适合以下场景：

- REST API、内部微服务和 BFF（Backend for Frontend）
- AI 模型推理、数据处理和自动化服务
- 需要 OpenAPI、参数校验和类型提示的 Python 后端
- I/O 密集型服务，例如访问数据库、缓存或其他 HTTP API

一次请求的大致处理流程如下：

1. ASGI 服务器（通常是 Uvicorn）接收请求。
2. Starlette 完成路由匹配、中间件和底层请求处理。
3. FastAPI 根据函数签名提取路径、查询、请求头和请求体参数。
4. Pydantic 转换并校验数据；失败时默认返回 `422 Unprocessable Entity`。
5. FastAPI 调用依赖项和路径操作函数，再序列化响应。
6. OpenAPI 模式同步记录参数、模型、响应和安全方案。

常见对象：

| 对象                               | 用途                |
| -------------------------------- | ----------------- |
| `FastAPI`                        | 创建应用并保存全局配置       |
| `APIRouter`                      | 按业务模块组织路由         |
| `BaseModel`                      | 声明请求、响应数据模型       |
| `Path`、`Query`、`Header`、`Cookie` | 声明参数来源和约束         |
| `Depends`                        | 注入共享逻辑、数据库会话或认证信息 |
| `HTTPException`                  | 主动返回 HTTP 错误      |
| `Request`、`Response`             | 访问底层请求与响应对象       |

## 2. 安装与第一个应用

### 2.1 创建项目

推荐使用 [[06-uv|uv]] 管理虚拟环境和依赖：

```bash
mkdir fastapi-demo
cd fastapi-demo
uv init
uv add "fastapi[standard]"
```

也可以使用标准 `venv` 和 `pip`：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install "fastapi[standard]"
```

`fastapi[standard]` 会安装 FastAPI CLI、Uvicorn、HTTPX、表单解析等常用可选依赖。
若希望自行控制依赖，可以只安装 `fastapi`，再按需添加 ASGI 服务器和其他包。

### 2.2 最小可运行示例

创建 `main.py`：

```python
from fastapi import FastAPI

app = FastAPI(
    title="任务管理 API",
    description="一个最小的 FastAPI 示例",
    version="1.0.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}
```

开发模式启动服务：

```bash
fastapi dev main.py
```

开发模式会监听代码变更并自动重载。打开以下地址：

- API：`http://127.0.0.1:8000/`
- Swagger UI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`
- OpenAPI JSON：`http://127.0.0.1:8000/openapi.json`

也可以直接使用 Uvicorn，其中 `main` 是模块名，`app` 是模块中的应用对象：

```bash
uvicorn main:app --reload
```

> `--reload` 只用于开发环境，不要在生产环境开启。

## 3. 路由与参数

路径操作由 HTTP 方法装饰器和 Python 函数组成：

```python
from typing import Annotated

from fastapi import FastAPI, Header, Path, Query

app = FastAPI()


@app.get("/users/{user_id}")
async def get_user(
    user_id: Annotated[int, Path(ge=1, description="用户 ID")],
    keyword: Annotated[str | None, Query(max_length=50)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_agent: Annotated[str | None, Header()] = None,
) -> dict:
    return {
        "user_id": user_id,
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "user_agent": user_agent,
    }
```

FastAPI 根据声明自动判断数据来源：

- 出现在路径模板中的参数来自路径，例如 `user_id`。
- `str`、`int`、`bool` 等标量参数默认来自查询字符串。
- Pydantic 模型默认来自 JSON 请求体。
- 使用 `Header`、`Cookie`、`Form`、`File` 可以显式指定其他来源。

固定路径应写在动态路径之前，否则 `/users/me` 可能被当成 `user_id="me"`：

```python
@app.get("/users/me")
async def get_current_user() -> dict[str, str]:
    return {"username": "current-user"}


@app.get("/users/{user_id}")
async def get_user(user_id: int) -> dict[str, int]:
    return {"user_id": user_id}
```

## 4. 请求体、校验与响应模型

不要让数据库模型、请求模型和响应模型承担完全相同的职责。
分别声明模型可以防止客户端传入 `id`，也能避免把密码、内部状态等字段返回给客户端。

```python
from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(gt=0)


class ProductCreate(ProductBase):
    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)


class ProductPublic(ProductBase):
    id: int
    stock: int
```

### 4.1 完整的内存 CRUD 示例

以下 `main.py` 可以直接运行，适合先理解 API 行为；进程结束后数据会丢失：

```python
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="商品 API", version="1.0.0")


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(gt=0)


class ProductCreate(ProductBase):
    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)


class ProductPublic(ProductBase):
    id: int
    stock: int


products: dict[int, ProductPublic] = {}
next_id = 1


@app.post(
    "/products",
    response_model=ProductPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(payload: ProductCreate) -> ProductPublic:
    global next_id
    product = ProductPublic(id=next_id, **payload.model_dump())
    products[next_id] = product
    next_id += 1
    return product


@app.get("/products", response_model=list[ProductPublic])
async def list_products(
    keyword: Annotated[str | None, Query(max_length=50)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ProductPublic]:
    result = list(products.values())
    if keyword:
        normalized_keyword = keyword.casefold()
        result = [item for item in result if normalized_keyword in item.name.casefold()]
    return result[offset : offset + limit]


@app.get("/products/{product_id}", response_model=ProductPublic)
async def get_product(product_id: int) -> ProductPublic:
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@app.patch("/products/{product_id}", response_model=ProductPublic)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
) -> ProductPublic:
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    changes = payload.model_dump(exclude_unset=True)
    updated = product.model_copy(update=changes)
    products[product_id] = updated
    return updated


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int) -> Response:
    if products.pop(product_id, None) is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

可以用 [[curl|curl]] 验证：

```bash
curl -X POST http://127.0.0.1:8000/products \
  -H 'Content-Type: application/json' \
  -d '{"name":"机械键盘","price":399,"stock":10}'

curl 'http://127.0.0.1:8000/products?keyword=键盘&limit=10'

curl -X PATCH http://127.0.0.1:8000/products/1 \
  -H 'Content-Type: application/json' \
  -d '{"stock":8}'
```

### 4.2 `response_model` 的作用

`response_model` 不只是文档声明，它还会：

- 校验服务端返回值是否符合约定。
- 过滤响应模型中未声明的字段，降低敏感字段泄露风险。
- 生成 OpenAPI 响应模式和客户端类型信息。

如果返回类型与 `response_model` 同时存在，以 `response_model` 作为 FastAPI 的响应模式。
业务代码仍应返回正确的数据，不要把字段过滤当作唯一的安全边界。

## 5. 错误处理

业务错误使用 `HTTPException`：

```python
from fastapi import HTTPException


def ensure_balance(balance: float, amount: float) -> None:
    if amount > balance:
        raise HTTPException(
            status_code=409,
            detail="账户余额不足",
            headers={"X-Error-Code": "INSUFFICIENT_BALANCE"},
        )
```

对统一错误格式有要求时，可以注册异常处理器：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


class DomainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message


@app.exception_handler(DomainError)
async def handle_domain_error(
    request: Request,
    exc: DomainError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "code": exc.code,
            "message": exc.message,
            "path": request.url.path,
        },
    )
```

不要把原始数据库错误、堆栈、SQL、令牌或密钥放进生产响应。
服务端记录完整上下文，对客户端返回稳定的错误码和安全描述。

## 6. 依赖注入

`Depends` 适合复用以下能力：

- 身份认证和权限检查
- 数据库会话或事务
- 分页参数与请求上下文
- 配置、HTTP 客户端和缓存连接

### 6.1 参数依赖

```python
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, Query

app = FastAPI()


@dataclass
class Pagination:
    offset: int
    limit: int


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Pagination:
    return Pagination(offset=(page - 1) * page_size, limit=page_size)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@app.get("/orders")
async def list_orders(pagination: PaginationDep) -> dict[str, int]:
    return {
        "offset": pagination.offset,
        "limit": pagination.limit,
    }
```

使用类型别名可以减少重复声明，并保留编辑器补全。
依赖还可以依赖其他依赖；FastAPI 会构建依赖树，同一次请求中默认复用同一个依赖结果。

### 6.2 带清理逻辑的依赖

使用 `yield` 管理“获取—使用—释放”资源：

```python
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.database import engine


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
```

即使路径函数抛出异常，`with` 也会关闭数据库会话。
默认情况下，依赖中 `yield` 后的清理会围绕响应过程执行。
只有明确需要在发送响应前释放资源时，才考虑 `Depends(..., scope="function")`。

## 7. 认证与授权

认证回答“你是谁”，授权回答“你能做什么”。FastAPI 提供 API Key、HTTP Basic、OAuth2、
OpenID Connect 等安全工具，并将安全方案写入 OpenAPI。

下面用 API Key 演示依赖式认证：

```python
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader

app = FastAPI()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str:
    expected = "replace-with-secret-from-environment"
    if api_key is None or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
        )
    return api_key


ApiKeyDep = Annotated[str, Depends(verify_api_key)]


@app.get("/private")
async def private_endpoint(api_key: ApiKeyDep) -> dict[str, str]:
    return {"message": "认证成功", "key_suffix": api_key[-4:]}
```

生产环境注意事项：

- 密钥必须来自环境变量或密钥管理系统，不能硬编码或提交到 Git。
- 外部用户登录优先采用成熟的 OAuth2/OIDC 身份提供方，不要自行发明认证协议。
- 密码只保存强哈希，不保存明文或可逆加密结果。
- JWT 必须验证签名、允许的算法、过期时间、签发者和受众；不要只解码载荷。
- 权限检查放在依赖或业务服务层，不要只依赖前端隐藏按钮。
- 生产流量使用 HTTPS，并配置速率限制、审计日志和密钥轮换。

完整的 Bearer Token 示例可参考 FastAPI 官方的
[OAuth2 + JWT 教程](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)。

## 8. `async def` 还是 `def`

FastAPI 同时支持同步和异步路径函数：

| 情况                                | 建议                         |
| --------------------------------- | -------------------------- |
| 使用异步数据库驱动、HTTPX AsyncClient 等可等待库 | 使用 `async def` 和 `await`   |
| 使用没有异步 API 的阻塞式库                  | 使用普通 `def`，FastAPI 会在线程池调用 |
| 纯 CPU 密集计算                        | 交给任务队列、进程池或独立计算服务          |
| 不确定，且调用链中没有 `await`               | 普通 `def` 往往更诚实             |

异步并不等于自动并行。以下写法会阻塞事件循环：

```python
import time


async def bad_endpoint() -> dict[str, bool]:
    time.sleep(5)  # 阻塞整个事件循环，不要这样写
    return {"ok": True}
```

异步上下文应使用可等待操作：

```python
import asyncio


async def good_endpoint() -> dict[str, bool]:
    await asyncio.sleep(5)
    return {"ok": True}
```

参见 [[24-python-async|Python 异步编程]]。

## 9. 配置管理

安装 Pydantic Settings：

```bash
uv add pydantic-settings
```

创建 `app/config.py`：

```python
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "商品 API"
    debug: bool = False
    database_url: str = "sqlite:///./app.db"
    api_key: str = Field(min_length=16)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
```

`.env` 示例：

```dotenv
APP_NAME=商品服务
DEBUG=false
DATABASE_URL=postgresql+psycopg://app:password@db:5432/app
API_KEY=replace-with-a-long-random-secret
```

字段名默认映射为不区分大小写的环境变量。
缓存配置对象可以避免每次请求都重新读取文件。
测试时可通过 `app.dependency_overrides` 替换依赖。
`.env` 只适合本地开发，务必加入 `.gitignore`。

## 10. 拆分大型应用

项目变大后，用 `APIRouter` 按业务域拆分路由，而不是把所有端点堆在 `main.py`：

```text
fastapi-demo/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── routers/
│       ├── __init__.py
│       └── products.py
├── tests/
│   └── test_products.py
└── pyproject.toml
```

`app/routers/products.py`：

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}")
async def get_product(product_id: int) -> dict[str, int]:
    if product_id < 1:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"product_id": product_id}
```

`app/main.py`：

```python
from fastapi import FastAPI

from app.routers import products

app = FastAPI(title="商品 API")
app.include_router(products.router, prefix="/api/v1")
```

启动模块化应用：

```bash
fastapi dev app/main.py
```

一种常见分层方式：

- `routers`：HTTP 协议适配，只处理参数、状态码和响应模型。
- `services`：业务规则和用例编排，不依赖具体 HTTP 请求。
- `models`：数据库表模型。
- `schemas`：请求与响应模型。
- `dependencies`：连接会话、认证主体和共享资源。

不要为了分层而分层。
小型应用可以先从单文件开始，当路由、模型和依赖明显增长时再拆分。

## 11. 生命周期、中间件与 CORS

### 11.1 生命周期

数据库连接池、模型权重、HTTP 客户端等应用级资源应在 `lifespan` 中初始化和释放：

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = AsyncClient(timeout=10.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)
```

现代 FastAPI 项目优先使用 `lifespan`，不要再为新代码使用已弃用的 `@app.on_event("startup")` 和
`@app.on_event("shutdown")`。

### 11.2 请求中间件

中间件适合请求 ID、耗时统计、统一响应头等横切逻辑：

```python
import time
import uuid

from fastapi import FastAPI, Request

app = FastAPI()


@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started_at = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - started_at
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"
    return response
```

### 11.3 CORS

浏览器前端跨域访问 API 时，显式配置允许的来源：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

当 `allow_credentials=True` 时，不要用通配符草率放开来源、方法和请求头。
CORS 是浏览器安全策略，不是服务端身份认证，也不能阻止非浏览器客户端直接请求 API。

## 12. 数据库：SQLModel 示例

FastAPI 不绑定 ORM，可以使用 SQLModel、SQLAlchemy、Django ORM 或数据库原生驱动。
以下示例使用 SQLite，安装依赖：

```bash
uv add sqlmodel
```

创建 `database_app.py`：

```python
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlmodel import Field, Session, SQLModel, create_engine, select


class TodoBase(SQLModel):
    title: str = Field(min_length=1, max_length=200, index=True)
    completed: bool = False


class Todo(TodoBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TodoCreate(TodoBase):
    pass


class TodoPublic(TodoBase):
    id: int


engine = create_engine(
    "sqlite:///./todos.db",
    connect_args={"check_same_thread": False},
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title="待办事项 API", lifespan=lifespan)


@app.post(
    "/todos",
    response_model=TodoPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(payload: TodoCreate, session: SessionDep) -> Todo:
    todo = Todo.model_validate(payload)
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


@app.get("/todos", response_model=list[TodoPublic])
def list_todos(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Todo]:
    statement = select(Todo).offset(offset).limit(limit)
    return list(session.exec(statement).all())


@app.get("/todos/{todo_id}", response_model=TodoPublic)
def get_todo(todo_id: int, session: SessionDep) -> Todo:
    todo = session.get(Todo, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="待办事项不存在")
    return todo
```

启动并访问 `/docs`：

```bash
fastapi dev database_app.py
```

生产项目还应做到：

- 使用 PostgreSQL、MySQL 等服务型数据库，并从配置读取连接 URL。
- 使用 Alembic 管理可审计、可回滚的数据库迁移，不依赖 `create_all()` 演进表结构。
- 为过滤、排序和关联字段设计索引，并检查慢查询和执行计划。
- 明确事务边界；异常时回滚，成功后再提交。
- 不在异步路径中调用同步数据库 I/O；同步驱动配合 `def`，或改用异步驱动和 `AsyncSession`。
- 避免把数据库表模型直接作为所有外部请求与响应模型。

数据库基础可参见 [[postgresql|PostgreSQL]] 和 [[mysql|MySQL]]。

## 13. 后台任务

响应发送后才需要执行的轻量工作可以使用 `BackgroundTasks`：

```python
from fastapi import BackgroundTasks, FastAPI, status

app = FastAPI()


def write_audit_log(order_id: int) -> None:
    with open("audit.log", "a", encoding="utf-8") as file:
        file.write(f"created order: {order_id}\n")


@app.post("/orders", status_code=status.HTTP_202_ACCEPTED)
async def create_order(background_tasks: BackgroundTasks) -> dict[str, int]:
    order_id = 1001
    background_tasks.add_task(write_audit_log, order_id)
    return {"order_id": order_id}
```

`BackgroundTasks` 与当前 Web 进程共享生命周期，进程退出时任务可能丢失。
耗时长、需要重试、跨机器执行或必须可靠完成的任务，
应使用 Celery、Dramatiq、RQ 等任务队列，并设计幂等性、重试和死信处理。

## 14. 测试

安装 pytest；`fastapi[standard]` 已包含 `TestClient` 所需的 HTTPX：

```bash
uv add --dev pytest
```

假设应用位于 `app/main.py`，创建 `tests/test_main.py`：

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_product() -> None:
    response = client.post(
        "/products",
        json={
            "name": "显示器",
            "description": "27 英寸 4K 显示器",
            "price": 2499,
            "stock": 5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "显示器"
    assert body["id"] > 0


def test_reject_invalid_price() -> None:
    response = client.post(
        "/products",
        json={"name": "显示器", "price": 0, "stock": 5},
    )

    assert response.status_code == 422
```

运行测试：

```bash
pytest -q
```

### 14.1 覆盖依赖

测试不应访问真实外部服务。通过 `app.dependency_overrides` 替换数据库、认证或配置依赖：

```python
from collections.abc import Iterator

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app


def get_test_session() -> Iterator[object]:
    session = build_isolated_test_session()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_session] = get_test_session

with TestClient(app) as client:
    response = client.get("/products")
    assert response.status_code == 200

app.dependency_overrides.clear()
```

上例中的 `build_isolated_test_session()` 需要由项目根据测试数据库实现。
使用 `with TestClient(app)` 可以触发应用的 `lifespan`。
测试结束后清理覆盖，避免污染其他用例。
若测试本身还需要调用异步数据库或异步客户端，使用 HTTPX `AsyncClient` 和异步 pytest 插件。

## 15. 生产部署

生产启动命令：

```bash
fastapi run app/main.py --port 8000
```

直接部署在虚拟机上时，可以通过多个 worker 使用多核 CPU：

```bash
fastapi run app/main.py --port 8000 --workers 4
```

每个 worker 都是独立进程，会分别占用内存、连接池和模型资源。
对于加载大型 AI 模型的服务，不能简单按 CPU 核数配置 worker，必须先估算内存或显存。

### 15.1 Docker 镜像

`requirements.txt`：

```text
fastapi[standard]
```

`Dockerfile`：

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
```

构建与运行：

```bash
docker build -t product-api:1.0.0 .
docker run --rm -p 8000:8000 --env-file .env product-api:1.0.0
```

使用 Kubernetes 等编排平台时，通常让每个容器运行一个 worker，再通过副本数横向扩容。
健康检查、HTTPS、重启、日志、指标和密钥注入交给平台或边缘代理处理。
详见 [[docker|Docker]]、[[kubernetes|Kubernetes]] 和 [[nginx|Nginx]]。

### 15.2 上线检查清单

- 关闭调试模式和自动重载，不向客户端暴露异常堆栈。
- 固定并定期升级依赖版本，执行测试和安全扫描。
- 使用 HTTPS，限制可信代理和允许的 Host、Origin。
- 从密钥系统注入凭据，制定轮换和吊销机制。
- 配置结构化日志、请求 ID、指标、追踪和告警。
- 设置请求体大小、超时、连接池和并发上限。
- 为写操作设计幂等键，为外部调用设计超时、重试和熔断。
- 使用数据库迁移，在发布流程中完成兼容性检查。
- 提供存活与就绪探针，优雅处理进程终止信号。
- 根据负载测试结果设置 worker 或容器副本数，而不是凭经验猜测。

## 16. 常见问题排查

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 返回 `422` | 参数位置、类型或约束不匹配 | 查看 `detail`，并在 `/docs` 对照请求模式 |
| 返回 `405` | 路径存在，但 HTTP 方法不匹配 | 检查 `GET`、`POST` 等装饰器和客户端请求方法 |
| 导入应用失败 | 当前目录或模块路径错误 | 从项目根目录启动，确认包中存在 `__init__.py` |
| 修改代码未生效 | 未开启开发重载或运行了错误模块 | 开发时使用 `fastapi dev app/main.py` |
| `Form data requires ...` | 缺少表单解析依赖 | 安装 `python-multipart`，或使用 `fastapi[standard]` |
| 测试找不到 HTTPX | 只安装了精简依赖 | 安装 `httpx`，或使用 `fastapi[standard]` |
| 并发时延升高 | 异步函数中执行阻塞 I/O | 使用异步库、普通 `def` 或任务队列 |
| 浏览器 CORS 错误 | 来源、方法或请求头不在白名单 | 配置 CORS 并检查代理响应头 |
| 多 worker 数据不一致 | 把可变状态保存在进程内存 | 使用数据库、Redis 等共享存储 |
| 宿主机无法访问容器 | 端口或监听地址错误 | 发布端口，并监听容器网络接口 |
| 数据库连接耗尽 | 会话未关闭、池过小或并发过高 | 用 `yield` 释放会话，调整连接池 |

## 17. 学习路线

建议按以下顺序练习：

1. 跑通单文件 CRUD，并观察 `/docs` 和 `openapi.json`。
2. 为查询参数、请求体和响应模型添加约束，主动触发并理解 `422`。
3. 使用 `Depends` 抽取分页、配置和认证逻辑。
4. 用 `APIRouter` 拆分模块，并用 service 层承载业务规则。
5. 接入数据库、迁移工具和事务管理。
6. 为成功、校验失败、未认证和资源不存在编写测试。
7. 容器化应用，补齐日志、健康检查、指标和安全配置。
8. 通过负载测试决定同步/异步驱动、连接池、worker 和副本数。

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [FastAPI 教程](https://fastapi.tiangolo.com/tutorial/)
- [依赖注入](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [大型应用与 APIRouter](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [安全与认证](https://fastapi.tiangolo.com/tutorial/security/)
- [SQL 数据库](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [测试](https://fastapi.tiangolo.com/tutorial/testing/)
- [应用生命周期](https://fastapi.tiangolo.com/advanced/events/)
- [部署与多 worker](https://fastapi.tiangolo.com/deployment/server-workers/)
