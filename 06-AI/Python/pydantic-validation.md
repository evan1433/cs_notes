---
title: Pydantic 数据类型校验
description: Pydantic v2 的模型定义、字段约束、自定义校验、序列化、配置管理与工程实践
tags:
  - python
  - pydantic
  - type-validation
date: 2026-07-23
---

# Pydantic 数据类型校验

Pydantic 是一个基于 Python 类型提示的数据校验与序列化库。它适合放在系统边界：读取 HTTP 请求、配置文件、
消息队列、数据库记录或第三方 API 响应时，把不可信的原始数据转换为结构明确、类型可靠的 Python 对象。

本文使用 **Pydantic v2** API，示例采用 Python 3.10+ 语法。阅读前建议先了解
[[05-python-type-hints|Python 类型提示]]。

## 1. 类型提示与运行时校验

Python 类型提示本身不会在运行时阻止错误数据：

```python
age: int = "18"  # Python 可以运行，静态类型检查器会提示错误
print(age)
```

Pydantic 会读取类型提示，并在运行时完成解析、校验和错误报告：

```python
from pydantic import BaseModel, ValidationError


class User(BaseModel):
    name: str
    age: int


user = User(name="小林", age="18")
print(user.age, type(user.age))  # 18 <class 'int'>

try:
    User(name="小林", age="未知")
except ValidationError as exc:
    print(exc.errors())
```

| 工具 | 检查时机 | 是否转换数据 | 典型用途 |
|------|----------|--------------|----------|
| 类型提示 | 不检查，仅提供类型信息 | 否 | IDE 补全、代码文档 |
| mypy、Pyright | 运行前的静态分析 | 否 | 尽早发现代码内部的类型错误 |
| Pydantic | 程序运行时 | 默认会合理转换 | 校验外部输入和系统边界数据 |

> Pydantic 保证的是**校验后的输出对象**符合模型声明。默认的宽松模式可能把 `"18"` 转换为 `18`；
> 如果输入类型也必须完全匹配，应启用严格模式。

## 2. 安装

```bash
python -m pip install "pydantic>=2,<3"
```

使用 uv：

```bash
uv add "pydantic>=2,<3"
```

`EmailStr` 等类型需要额外依赖：

```bash
python -m pip install "pydantic[email]>=2,<3"
```

环境变量与 `.env` 配置管理位于独立包中：

```bash
python -m pip install pydantic-settings
```

## 3. 定义第一个模型

继承 `BaseModel`，使用类型注解声明字段：

```python
from datetime import datetime

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


product = Product(
    id="1001",
    name="机械键盘",
    price="599.00",
    tags=["外设", "键盘"],
)

print(product.id, type(product.id))       # 1001 <class 'int'>
print(product.price, type(product.price)) # 599.0 <class 'float'>
print(product.model_dump())
```

### 3.1 必填、可空与默认值

```python
from pydantic import BaseModel


class Profile(BaseModel):
    username: str                   # 必填，不能为 None
    nickname: str | None            # 必填，但允许传入 None
    bio: str | None = None          # 非必填，默认值为 None
    language: str = "zh-CN"         # 非必填，具有普通默认值
```

`str | None` 只表示“值可以是 `None`”，不代表字段可以省略。要让字段可省略，需要显式提供默认值。

### 3.2 可变默认值

列表、字典等可变值建议使用 `default_factory`，明确表达“每个实例创建一个新对象”：

```python
from pydantic import BaseModel, Field


class ShoppingCart(BaseModel):
    item_ids: list[int] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
```

## 4. 创建和校验模型

Pydantic v2 提供多个入口：

```python
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str


# 关键字参数
user1 = User(id="1", name="小林")

# Python 字典或其他映射对象
user2 = User.model_validate({"id": "2", "name": "小周"})

# JSON 字符串或 bytes；通常比先 json.loads 再校验更直接
user3 = User.model_validate_json('{"id": "3", "name": "小吴"}')

assert [user1.id, user2.id, user3.id] == [1, 2, 3]
```

常用方法：

| API | 用途 |
|-----|------|
| `Model(...)` | 使用关键字参数创建并校验模型 |
| `Model.model_validate(data)` | 校验 Python 对象 |
| `Model.model_validate_json(data)` | 直接校验 JSON 字符串或 `bytes` |
| `model.model_dump()` | 转换为 Python 字典 |
| `model.model_dump_json()` | 序列化为 JSON 字符串 |
| `Model.model_json_schema()` | 生成 JSON Schema |

## 5. 字段约束

### 5.1 使用 `Field`

`Field` 可以添加数值范围、字符串长度、格式、别名和文档信息：

```python
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    age: int = Field(ge=18, le=120)
    password: str = Field(min_length=8, exclude=True)
    invite_code: str | None = Field(default=None, alias="inviteCode")
```

常用约束：

| 参数 | 含义 |
|------|------|
| `gt`、`ge` | 大于、大于等于 |
| `lt`、`le` | 小于、小于等于 |
| `multiple_of` | 必须是指定值的倍数 |
| `min_length`、`max_length` | 字符串或容器长度 |
| `pattern` | 字符串正则表达式 |
| `strict=True` | 仅对当前字段启用严格校验 |
| `alias` | 输入和输出使用的别名 |
| `exclude=True` | 默认序列化时排除字段 |

### 5.2 使用 `Annotated` 复用规则

`Annotated` 能把类型和校验元数据组合成可复用类型：

```python
from typing import Annotated

from pydantic import BaseModel, Field

UserId = Annotated[int, Field(gt=0)]
ShortText = Annotated[str, Field(min_length=1, max_length=100)]


class Comment(BaseModel):
    author_id: UserId
    content: ShortText


comment = Comment(author_id=42, content="写得很清楚")
print(comment)
```

这种写法保留了静态类型检查器对 `int`、`str` 的理解，同时让 Pydantic 执行额外约束。

### 5.3 常用内置类型

```python
from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, HttpUrl, PositiveInt


class Contact(BaseModel):
    id: UUID
    email: EmailStr
    homepage: HttpUrl | None = None
    birthday: date | None = None
    login_count: PositiveInt
```

除 Python 标准库类型外，Pydantic 还提供 `EmailStr`、`HttpUrl`、`PositiveInt`、`SecretStr` 等类型。
密码、令牌等敏感信息适合使用 `SecretStr`，避免在日志和 `repr` 中直接显示原文。

## 6. 嵌套模型与复杂结构

### 6.1 嵌套模型

```python
from pydantic import BaseModel, Field


class Address(BaseModel):
    city: str
    street: str


class Customer(BaseModel):
    id: int
    name: str
    addresses: list[Address] = Field(default_factory=list)


customer = Customer.model_validate(
    {
        "id": 1,
        "name": "小林",
        "addresses": [{"city": "杭州", "street": "文一路 1 号"}],
    }
)

print(customer.addresses[0].city)  # 杭州
```

内部字典会被递归转换为 `Address` 对象，错误位置也会包含完整路径，例如 `addresses.0.city`。

### 6.2 枚举与字面量

```python
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class PaymentMethod(str, Enum):
    ALIPAY = "alipay"
    WECHAT = "wechat"


class Payment(BaseModel):
    method: PaymentMethod
    currency: Literal["CNY", "USD"] = "CNY"
```

`Enum` 适合在多个模型中复用；`Literal` 适合少量、局部的固定值。

### 6.3 可辨识联合类型

多个结构相似的模型组成联合类型时，使用 discriminator 能获得更快、更清晰的校验：

```python
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class EmailNotice(BaseModel):
    channel: Literal["email"]
    address: str


class SmsNotice(BaseModel):
    channel: Literal["sms"]
    phone: str


Notice = Annotated[EmailNotice | SmsNotice, Field(discriminator="channel")]


class NoticeTask(BaseModel):
    notice: Notice


task = NoticeTask.model_validate(
    {"notice": {"channel": "sms", "phone": "13800000000"}}
)
assert isinstance(task.notice, SmsNotice)
```

## 7. 自定义校验器

优先使用类型和 `Field` 表达规则；只有跨字段规则、规范化或业务约束无法声明时，才编写校验器。

### 7.1 字段校验器

```python
from pydantic import BaseModel, field_validator


class CreateUser(BaseModel):
    username: str

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        # before 接收原始输入，适合预处理。
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("username")
    @classmethod
    def reject_reserved_name(cls, value: str) -> str:
        # 默认 after：value 已通过 str 类型校验。
        if value in {"admin", "root", "system"}:
            raise ValueError("用户名为系统保留名称")
        return value
```

校验器模式：

| 模式 | 执行时机 | 适用场景 |
|------|----------|----------|
| `before` | Pydantic 类型校验之前 | 清理和转换原始输入 |
| `after` | 类型校验之后，默认模式 | 基于可靠类型做业务校验 |
| `plain` | 替代内部校验流程 | 完全自定义字段校验 |
| `wrap` | 包裹内部校验流程 | 需要在校验前后执行逻辑或截获错误 |

> 业务输入不合法时应抛出 `ValueError` 或 `AssertionError`。不要在校验器中手动构造
> `ValidationError`，也不要用 `TypeError` 表示输入错误。

### 7.2 模型校验器

跨字段校验使用 `model_validator`：

```python
from typing_extensions import Self

from pydantic import BaseModel, model_validator


class PasswordChange(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self
```

`mode="after"` 时方法接收已经构建的模型实例，并且必须返回实例。`mode="before"` 接收原始数据，
但需要自行处理输入可能不是字典的情况。

## 8. 错误处理

一次校验可以收集多个字段错误，通过 `ValidationError.errors()` 得到适合程序处理的结构：

```python
from pydantic import BaseModel, Field, ValidationError


class Transfer(BaseModel):
    account_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=100_000)


try:
    Transfer.model_validate({"account_id": -1, "amount": "很多"})
except ValidationError as exc:
    for error in exc.errors():
        print(
            {
                "path": ".".join(str(part) for part in error["loc"]),
                "type": error["type"],
                "message": error["msg"],
            }
        )
```

单条错误通常包含：

| 键 | 含义 |
|----|------|
| `loc` | 错误字段路径，嵌套模型和列表会有多级位置 |
| `type` | 稳定的错误类型标识，如 `missing`、`int_parsing` |
| `msg` | 面向开发者的默认错误描述 |
| `input` | 导致错误的原始输入 |
| `ctx` | 约束上下文，例如上限或下限 |

生产环境建议把 `loc` 和 `type` 映射为自己的 API 错误码与本地化文案。记录错误时注意 `input`
可能含密码、令牌或个人信息，不要直接写入日志。

## 9. 宽松模式与严格模式

默认宽松模式会执行合理的类型转换：

```python
from pydantic import BaseModel


class LaxModel(BaseModel):
    count: int


assert LaxModel(count="12").count == 12
```

金融金额、权限标识等不希望隐式转换的数据，可以启用严格模式：

```python
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StrictOrder(BaseModel):
    model_config = ConfigDict(strict=True)

    quantity: int
    note: str


try:
    StrictOrder(quantity="2", note="加急")
except ValidationError as exc:
    print(exc.errors()[0]["type"])  # int_type


class MixedOrder(BaseModel):
    quantity: int = Field(strict=True)
    discount: float = 0
```

严格模式可用于单次调用、单个字段或整个模型。注意 JSON 没有日期、UUID 等原生类型，
因此 `model_validate_json(..., strict=True)` 对部分类型仍允许标准 JSON 字符串表示；以官方转换表为准。

## 10. 模型配置

Pydantic v2 使用 `ConfigDict`：

```python
from pydantic import BaseModel, ConfigDict


class ApiRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",              # 拒绝模型未声明的字段
        str_strip_whitespace=True,    # 自动清理字符串首尾空白
        validate_assignment=True,     # 属性重新赋值时也进行校验
        validate_default=True,        # 同样校验默认值
    )

    request_id: int
    action: str
```

常用配置：

| 配置 | 作用 |
|------|------|
| `extra="ignore"` | 忽略额外字段，默认行为 |
| `extra="forbid"` | 拒绝额外字段，API 入参通常推荐 |
| `extra="allow"` | 保留额外字段 |
| `strict=True` | 整个模型启用严格模式 |
| `validate_assignment=True` | 字段赋值时重新校验 |
| `frozen=True` | 阻止修改模型字段，创建近似不可变对象 |
| `from_attributes=True` | 允许从普通对象属性读取数据 |
| `validate_by_name=True` | 有别名时也允许使用字段名作为输入 |
| `validate_by_alias=True` | 允许使用字段别名作为输入，默认为 `True` |

Pydantic 默认只在创建模型时校验。若模型是跨模块共享的长期状态，考虑 `validate_assignment=True`
或 `frozen=True`，避免对象创建后进入无效状态。

## 11. 别名与序列化

### 11.1 字段别名

外部 API 常使用 camelCase，Python 代码通常使用 snake_case：

```python
from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    user_id: int = Field(alias="userId")
    display_name: str = Field(alias="displayName")


user = UserResponse(user_id=1, display_name="小林")
print(user.model_dump())                 # {'user_id': 1, 'display_name': '小林'}
print(user.model_dump(by_alias=True))   # {'userId': 1, 'displayName': '小林'}
```

输入和输出必须使用不同名称时，可分别设置 `validation_alias` 与 `serialization_alias`。

### 11.2 导出字典和 JSON

```python
from datetime import datetime, timezone

from pydantic import BaseModel


class Event(BaseModel):
    name: str
    occurred_at: datetime
    detail: str | None = None


event = Event(name="user.created", occurred_at=datetime.now(timezone.utc))

python_data = event.model_dump()
json_ready_data = event.model_dump(mode="json")
json_text = event.model_dump_json()
compact_data = event.model_dump(exclude_none=True)

print(python_data)
print(json_ready_data)
print(json_text)
print(compact_data)
```

- `mode="python"` 是默认模式，保留 `datetime`、`UUID` 等 Python 对象。
- `mode="json"` 返回只包含 JSON 可序列化值的字典。
- `exclude_none`、`exclude_defaults`、`exclude_unset` 可控制输出字段。

不要把模型的 `repr` 或 `str(model)` 当成稳定的 API 输出；应显式调用 `model_dump()` 或
`model_dump_json()`。

## 12. 校验普通类型

只有一个 `list`、`TypedDict` 或联合类型需要校验时，不必创建只有根字段的模型，可使用 `TypeAdapter`：

```python
from pydantic import TypeAdapter, ValidationError

integer_list = TypeAdapter(list[int])

values = integer_list.validate_python(["1", 2, 3])
assert values == [1, 2, 3]

try:
    integer_list.validate_python(["not-a-number"])
except ValidationError as exc:
    print(exc.errors())

print(integer_list.dump_json(values))
print(integer_list.json_schema())
```

`TypeAdapter` 构建校验器有一定开销，热点路径中应复用同一个实例，不要在循环内重复创建。

## 13. 校验函数参数

`validate_call` 可根据函数注解校验调用参数：

```python
from pydantic import Field, validate_call
from typing_extensions import Annotated


@validate_call
def reserve_stock(
    product_id: int,
    quantity: Annotated[int, Field(gt=0)],
) -> str:
    return f"商品 {product_id} 预留 {quantity} 件"


print(reserve_stock("1001", 2))
```

它适合任务入口、脚本接口和插件边界，不应代替核心业务代码的合理设计。默认只校验参数；如需校验返回值，
使用 `@validate_call(validate_return=True)`。

## 14. 从对象属性创建模型

把 ORM 实体或普通对象转换为输出模型时，启用 `from_attributes`：

```python
from pydantic import BaseModel, ConfigDict


class UserEntity:
    def __init__(self, user_id: int, username: str) -> None:
        self.user_id = user_id
        self.username = username


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str


entity = UserEntity(1, "xiaolin")
view = UserView.model_validate(entity)
print(view.model_dump())
```

这只负责读取属性和校验数据，不负责管理数据库会话。访问延迟加载关系时，仍需留意 N+1 查询和会话生命周期。

## 15. 配置管理

Pydantic v2 已将 `BaseSettings` 移到 `pydantic-settings`：

```python
import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str
    api_token: SecretStr
    worker_count: int = Field(default=4, ge=1, le=32)


# 仅为使示例可以独立运行；实际项目应由运行环境注入这些值。
os.environ.setdefault("APP_DATABASE_URL", "postgresql://localhost/shop")
os.environ.setdefault("APP_API_TOKEN", "development-only-token")

# 读取 APP_DATABASE_URL、APP_API_TOKEN、APP_WORKER_COUNT 等环境变量。
settings = Settings()  # type: ignore[call-arg]
print(settings.environment)
print(settings.api_token)  # **********
```

不要提交包含真实密钥的 `.env`。生产环境优先从平台的 Secret Manager 或环境变量注入配置。

## 16. 生成 JSON Schema

```python
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    keyword: str = Field(min_length=1, description="搜索关键词")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


schema = SearchQuery.model_json_schema()
print(schema)
```

JSON Schema 可用于 API 文档、表单生成、跨语言契约和测试数据生成。FastAPI 的请求体校验与 OpenAPI
文档生成就建立在 Pydantic 模型之上。

## 17. 完整示例：订单入参校验

下面的示例组合了嵌套模型、约束类型、字段校验、跨字段校验、严格配置和错误处理，可保存后直接运行：

```python
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from typing_extensions import Self

PositiveQuantity = Annotated[int, Field(strict=True, gt=0, le=999)]
Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    unit_price: Money
    quantity: PositiveQuantity

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("商品名称不能为空")
        return normalized

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    customer_id: int = Field(gt=0)
    delivery: Literal["standard", "express"] = "standard"
    items: list[OrderItem] = Field(min_length=1, max_length=100)
    coupon_amount: Decimal = Field(default=Decimal("0"), ge=0)
    remark: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def coupon_not_greater_than_total(self) -> Self:
        total = sum((item.subtotal for item in self.items), start=Decimal("0"))
        if self.coupon_amount > total:
            raise ValueError("优惠金额不能超过商品总额")
        return self

    @property
    def payable_amount(self) -> Decimal:
        total = sum((item.subtotal for item in self.items), start=Decimal("0"))
        return total - self.coupon_amount


payload = {
    "customer_id": "10001",
    "delivery": "express",
    "items": [
        {
            "product_id": 2001,
            "name": " 机械键盘 ",
            "unit_price": "599.00",
            "quantity": 2,
        }
    ],
    "coupon_amount": "50.00",
}

try:
    order = CreateOrderRequest.model_validate(payload)
    print(order)
    print("应付金额：", order.payable_amount)  # 1148.00
    print(order.model_dump(mode="json", exclude_none=True))
except ValidationError as exc:
    for error in exc.errors():
        path = ".".join(str(part) for part in error["loc"])
        print(f"{path}: {error['msg']} ({error['type']})")
```

这里仅对 `quantity` 使用严格整数，防止字符串数量被静默转换；来自 JSON 的金额允许先从字符串解析为
`Decimal`，避免直接使用二进制浮点数处理金额。

## 18. 常见问题

| 问题 | 原因 | 处理方式 |
|------|------|----------|
| `Optional[T]` 字段仍提示必填 | v2 中可空不等于可省略 | 声明为 `T | None = None` |
| 多传字段没有报错 | `extra` 默认为 `ignore` | API 入参设置 `ConfigDict(extra="forbid")` |
| 修改属性后出现无效值 | 默认不校验赋值 | 启用 `validate_assignment=True` 或 `frozen=True` |
| `"1"` 被转为整数 `1` | 默认使用宽松模式 | 对模型、字段或调用启用 `strict=True` |
| `BaseSettings` 无法导入 | v2 已移动到独立包 | 安装 `pydantic-settings` 并从中导入 |
| `.dict()`、`.json()` 出现弃用警告 | 使用了 v1 API | 改用 `model_dump()`、`model_dump_json()` |
| `@validator` 出现弃用警告 | 使用了 v1 校验器 | 改用 `@field_validator`、`@model_validator` |
| ORM 对象无法解析 | v2 不再使用 `orm_mode` | 配置 `ConfigDict(from_attributes=True)` |
| 默认值没有被校验 | 默认跳过默认值校验 | 配置 `validate_default=True` |

## 19. v1 到 v2 常用迁移对照

| Pydantic v1 | Pydantic v2 |
|-------------|-------------|
| `parse_obj()` | `model_validate()` |
| `parse_raw()` | `model_validate_json()` |
| `dict()` | `model_dump()` |
| `json()` | `model_dump_json()` |
| `schema()` | `model_json_schema()` |
| `copy()` | `model_copy()` |
| `construct()` | `model_construct()` |
| `@validator` | `@field_validator` |
| `@root_validator` | `@model_validator` |
| `class Config` | `model_config = ConfigDict(...)` |
| `allow_population_by_field_name=True` | `validate_by_name=True`（v2.11+） |
| `orm_mode = True` | `from_attributes=True` |
| `BaseSettings` | `pydantic_settings.BaseSettings` |

旧方法中一部分暂时保留了兼容入口，但会产生弃用警告。新代码应直接使用 v2 API；大型项目迁移时，
先固定依赖版本并参考官方迁移指南逐模块升级。

## 20. 工程实践

- 在 HTTP、消息队列、配置、文件和第三方响应等**系统边界**校验一次，内部业务函数使用已经校验的对象。
- 把输入模型、领域模型、数据库模型和响应模型按职责拆分，避免一个模型承载所有层的需求。
- 声明式约束优先于自定义校验器；字段校验优先于跨字段校验，规则更容易生成 Schema 和复用。
- API 输入通常设置 `extra="forbid"`，尽早发现客户端拼写错误和过期字段。
- 金额使用 `Decimal`，时间明确时区，标识符根据业务选择正整数或 `UUID`。
- 不要对已可信数据反复校验；不要为了速度随意使用跳过校验的 `model_construct()`。
- 不要在校验器中执行数据库查询或网络请求。校验器应快速、确定且尽量无副作用。
- `ValidationError` 属于预期输入错误；转换为稳定的业务错误码，不要向客户端暴露内部堆栈。
- Pydantic 解决运行时数据边界问题，不能替代 mypy 或 Pyright 的静态类型检查。

## 21. 参考资料

- [Pydantic 官方文档](https://docs.pydantic.dev/latest/)
- [Models](https://docs.pydantic.dev/latest/concepts/models/)
- [Fields](https://docs.pydantic.dev/latest/concepts/fields/)
- [Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Serialization](https://docs.pydantic.dev/latest/concepts/serialization/)
- [Strict Mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)
- [TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/)
- [Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic v2 迁移指南](https://docs.pydantic.dev/latest/migration/)

## 22. 延伸阅读

- [[05-python-type-hints|Python 类型提示]]
- [[02-python-oop|Python 面向对象]]
- [[12-dependency-config|Python 依赖管理配置文件]]
