---
title: SQLAlchemy 技术指南
description: SQLAlchemy 2.1 实战指南：Core 与 ORM 分层、声明式模型、Session 工作单元、查询与预加载、事务与乐观锁、异步、连接池、Alembic 迁移及常见坑。
tags:
  - database
  - python
  - sqlalchemy
  - orm
date: 2026-11-05
---

# SQLAlchemy 技术指南

> 面向 Python 3.11+ / SQLAlchemy 2.1 的实战整理，以 **2.0 新式 API**（`select()` + `Mapped` 类型注解）为主线。
> 1.x 的 `session.query()` 仍可用但已非推荐写法，本文只在对比处提及。

## 一、定位与版本现状

SQLAlchemy 不是一个"薄封装 ORM"，而是一套 **数据库工具箱**：底层是可组合的 SQL 表达式语言（Core），上层是可选的 ORM。
两者共用同一套 Engine、连接池与事务机制，因此可以在一套代码里混用"手写 SQL"和"对象映射"。

**版本现状**（2026-11）：

| 版本 | 状态 | 关键变化 |
| --- | --- | --- |
| 2.1.1 | 当前稳定版 | 2026-09-24 发布 2.1.0，`pip install sqlalchemy` 默认装 2.1 |
| 2.0.x | 维护中（2.0.54） | 2.0 系列的安全修复分支 |
| 1.4 | EOL | 不再维护 |

2.1 相对 2.0 的**硬性变化**（升级时必须知道）：

1. **Python 最低版本提到 3.11**，3.10 已 EOL。
2. **`greenlet` 不再默认安装**。异步功能需要 `pip install "sqlalchemy[asyncio]"`，否则 `create_async_engine` 会直接报错。
3. **默认驱动变更**：`postgresql://` 现在默认走 `psycopg`（psycopg 3）而非 `psycopg2`；`oracle://` 默认走 `oracledb`。
   老项目若依赖 psycopg2，URL 要显式写成 `postgresql+psycopg2://`。
4. 新增 `tstring()`：配合 Python 3.14 的 t-string，把 `t"SELECT * FROM t WHERE id={x}"` 自动转成绑定参数，比 `text()` 更安全易读。
5. 新增 `CREATE VIEW` / `CREATE TABLE AS` 的 DDL 构造，以及 `Session.execution_options`（会话级执行选项，查询和 flush 都生效）。

## 二、架构分层：Core 与 ORM

这是理解 SQLAlchemy 的第一道门槛。很多人以为"SQLAlchemy = ORM"，于是把复杂报表查询也硬塞进 ORM，结果又慢又绕。

| 维度 | Core（`sqlalchemy`） | ORM（`sqlalchemy.orm`） |
| --- | --- | --- |
| 抽象对象 | Table、Column、Select、Connection | 类、实例、Session、relationship |
| 心智模型 | 面向"行与列" | 面向"对象与图" |
| SQL 控制力 | 完全可控，能精确表达任意 SQL | 生成 SQL 由映射与加载策略决定 |
| 状态管理 | 无状态，结果即行 | 有 identity map、脏检查、工作单元 |
| 典型场景 | 批量导入、报表聚合、DDL、数据迁移 | 业务 CRUD、领域模型、关联遍历 |
| 性能上限 | 接近手写 SQL | 有映射与追踪开销，需注意 N+1 |

**选型建议**：

- 业务写入与实体读写 → ORM；
- 大报表、跨多表聚合、窗口函数、`INSERT ... SELECT` → Core，或 ORM 里用 `select()` 拼装但**只取需要的列**；
- 两者可在同一 Session 中共存：`session.execute(select(...))` 本身就是 Core 表达式。

## 三、安装与 Engine

```bash
# 同步 + PostgreSQL（psycopg3，2.1 默认）
pip install "sqlalchemy[asyncio]" "psycopg[binary]"

# 仅同步、用 psycopg2（老项目）
pip install sqlalchemy "psycopg2-binary"

# 异步 MySQL / SQLite
pip install "sqlalchemy[asyncio]" aiomysql aiosqlite
```

URL 统一格式：`dialect+driver://user:password@host:port/dbname`

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg://app:secret@localhost:5432/app_db",
    echo=False,          # True 打印所有 SQL，调试用
    pool_pre_ping=True,  # 取连接前 ping 一次，避免"连接已被服务端断开"
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,   # 30 分钟回收，规避中间件/LB 的空闲超时
)
```

`Engine` 是**进程级单例**，内部持有连接池；千万不要每个请求 `create_engine` 一次，那等于每次新建连接池。

## 四、声明式模型

2.0 起用 `DeclarativeBase` + `Mapped[...]`，类型注解直接决定列的可空性与类型，不再需要手写 `nullable=`。

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有模型的基类，Alembic 的 target_metadata 指向它。"""


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(50))          # 可空
    bio: Mapped[str | None] = mapped_column(Text())
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    posts: Mapped[list["Post"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text())
    author_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )

    author: Mapped["User"] = relationship(back_populates="posts")
```

**类型注解 → 列类型映射**（最常用的一组）：

| 注解 | 生成的列 |
| --- | --- |
| `Mapped[int]` | `INTEGER NOT NULL` |
| `Mapped[str \| None]` | `VARCHAR NULL`（`Optional` 决定可空） |
| `Mapped[Decimal]` | `NUMERIC`，需显式精度时写 `Numeric(12, 2)` |
| `Mapped[datetime]` | `DATETIME` / `TIMESTAMP`，带时区务必 `DateTime(timezone=True)` |
| `Mapped[bool]` | `BOOLEAN` |
| `Mapped[dict]` / `Mapped[list]` | 需配 `JSON` 或 `JSONB` 类型 |
| `Mapped[bytes]` | `BLOB` / `BYTEA` |

建表（开发期可用，生产用 Alembic）：

```python
Base.metadata.create_all(engine)
```

注意 `create_all` **只建缺失的表，不会改已有表结构**，改字段必须走迁移。

## 五、Session 与工作单元

`Session` 不是"连接"，而是**工作单元（Unit of Work）+ identity map**。它做的事：

1. 缓存已加载对象（同一主键在会话内只有一个实例）；
2. 追踪对象的脏状态（属性改了自动标记待更新）；
3. 在 `flush()` 时按依赖顺序把 INSERT/UPDATE/DELETE 发出去；
4. 在 `commit()` 时提交事务并（默认）让对象过期。

```python
from sqlalchemy.orm import Session, sessionmaker

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Web 场景建议关掉，见下文
    autoflush=False,         # 显式 flush，避免查询触发意外写
)


def create_user(email: str, nickname: str) -> User:
    with SessionLocal.begin() as session:   # 进出自动 commit / rollback
        user = User(email=email, nickname=nickname)
        session.add(user)
        session.flush()                      # 立刻拿到自增 id
        print("new id =", user.id)
        return user
```

### 关键概念对照

| 操作 | 作用 | 何时用 |
| --- | --- | --- |
| `add()` / `add_all()` | 把对象纳入会话托管 | 新增 |
| `flush()` | 把内存变更发到数据库（**不提交**） | 需要自增 ID、需要触发约束校验 |
| `commit()` | 提交事务，默认让对象属性过期 | 一个业务单元结束 |
| `rollback()` | 回滚并清空待写变更 | 异常路径 |
| `expire()` / `expire_all()` | 手动让对象过期，下次访问重新 SELECT | 并发下需读最新值 |
| `refresh(obj)` | 立即重新 SELECT 覆盖属性 | 触发器改了列、需要服务端值 |
| `close()` | 归还连接、清空会话 | 请求结束 |
| `get(Model, pk)` | 按主键查，命中 identity map | 最简单的单行读取 |

### `expire_on_commit` 为什么建议关

默认 `expire_on_commit=True`：commit 后所有对象属性失效，此时访问 `user.email` 会**再发一次 SELECT**。
如果在事务已提交、连接已归还的连接池边缘访问，就会额外占用连接，Web 高并发下容易放大成连接池耗尽。

```python
session = SessionLocal()
user = User(email="a@b.com")
session.add(user)
session.commit()
print(user.email)   # expire_on_commit=True：这里悄悄多发一条 SELECT
session.close()
```

关掉之后对象保持快照值，代价是**读到的可能不是最新数据**——需要最新值时显式 `session.refresh(obj)`。
语义上更安全的做法是提交后不再复用该对象，让上层重新查询。

## 六、查询

2.0 的查询统一为 `select()` 构造 + `session.execute()` / `session.scalars()`。

```python
from sqlalchemy import func, or_, select

# 单列/单实体：scalars() 直接拿对象
stmt = select(User).where(User.email == "a@b.com")
user = session.scalars(stmt).one_or_none()

# 多列：返回 Row，用 .all() / .first()
stmt = select(User.id, User.email).where(User.id.in_([1, 2, 3]))
for uid, email in session.execute(stmt):
    print(uid, email)

# 条件组合
stmt = (
    select(User)
    .where(User.nickname.is_not(None))          # 判空用 is_() / is_not()
    .where(or_(User.id < 100, User.email.like("%@corp.com")))
    .order_by(User.created_at.desc())
    .limit(20)
    .offset(40)
)

# 聚合
total = session.execute(select(func.count()).select_from(User)).scalar_one()

# JOIN + 分组
stmt = (
    select(User.id, func.count(Post.id).label("post_cnt"))
    .join(Post, Post.author_id == User.id)
    .group_by(User.id)
    .having(func.count(Post.id) > 5)
)
rows = session.execute(stmt).all()
```

### 分页与"总数"要分两条语句

`select(...).limit()` 拿不到总数，需要单独 `count`：

```python
def paginate(session: Session, page: int, size: int = 20):
    total = session.execute(
        select(func.count()).select_from(User)
    ).scalar_one()
    items = session.scalars(
        select(User).order_by(User.id).limit(size).offset((page - 1) * size)
    ).all()
    return items, total
```

深分页（`offset` 很大）在千万级表上会退化为全表扫描，改用 **keyset 分页**：
`where(User.id > last_id).order_by(User.id).limit(size)`。

### 1.x `Query` 与 2.0 `select` 对照

| 1.x | 2.0+ |
| --- | --- |
| `session.query(User).filter(...)` | `session.scalars(select(User).where(...))` |
| `session.query(User).get(1)` | `session.get(User, 1)` |
| `query(func.count(User.id)).scalar()` | `execute(select(func.count())).scalar_one()` |
| `query.join(Post).all()` | `session.scalars(select(User).join(Post)).all()` |
| `query.filter(User.id == 1).one()` | `session.scalars(select(User).where(User.id == 1)).one()` |

## 七、关系映射

### 一对多 / 多对一

上面 `User.posts` 与 `Post.author` 已是标准写法。要点：

- 两端都用 `back_populates`，**必须成对出现**，否则关系不会双向同步；
- `cascade="all, delete-orphan"` 表示"父删子删 + 移出集合即删除"；
- `passive_deletes=True` 配合数据库 `ON DELETE CASCADE`，让删除交给数据库批量完成，而不是 ORM 逐行 DELETE。

### 多对多

```python
from sqlalchemy import Column, Table

post_tag = Table(
    "post_tag",
    Base.metadata,
    Column("post_id", ForeignKey("post.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)


class Post(Base):
    # ... 省略其他列
    tags: Mapped[list[Tag]] = relationship(secondary=post_tag, back_populates="posts")
```

多对多只做关联时无需 `cascade`，删除中间表行由 `passive_deletes` + 外键级联处理。

### 懒加载策略 `lazy=`

| 取值 | 行为 | 适用 |
| --- | --- | --- |
| `"select"`（默认） | 首次访问属性时发 SELECT | 单体脚本，交互式使用 |
| `"selectin"` | 需要时用 `IN` 一次性批量加载 | 列表页遍历关联 |
| `"joined"` | 随主查询 LEFT JOIN 出来 | 多对一（N:1） |
| `"raise"` | 访问即抛异常 | **大型项目推荐**，强制显式预加载 |
| `"noload"` | 返回空集合 | 极少用，容易出逻辑 bug |

生产建议：核心模型统一设 `lazy="raise"`，把 N+1 变成**开发期报错**而不是线上慢查询。

## 八、N+1 与预加载

N+1 是 ORM 第一大性能事故：查 100 个用户，再逐个访问 `user.posts`，就是 1 + 100 条 SQL。

```python
# 反例：N+1
users = session.scalars(select(User).limit(100)).all()
for u in users:
    print(len(u.posts))     # 每个用户一条 SELECT

# 正例：selectinload（集合，1 + 1 条 SQL）
from sqlalchemy.orm import selectinload

stmt = select(User).options(selectinload(User.posts)).limit(100)
users = session.scalars(stmt).all()

# 正例：joinedload（多对一，1 条 SQL）
from sqlalchemy.orm import joinedload

stmt = select(Post).options(joinedload(Post.author)).limit(100)
posts = session.scalars(stmt).all()
```

### 三种加载方式对比

| 方式 | 生成 SQL | 特点 | 适用关系 |
| --- | --- | --- | --- |
| `joinedload` | 主查询 LEFT OUTER JOIN | 一条 SQL，但集合会产生笛卡尔膨胀 | 多对一、一对一 |
| `selectinload` | 主查询 + `WHERE id IN (...)` | 两条 SQL，无膨胀，IN 参数过多时需分批 | 一对多、多对多 |
| `subqueryload` | 主查询 + 子查询 | 已被 `selectinload` 取代 | 遗留场景 |
| `raiseload("*")` | 不查，访问即抛错 | 防漏网之鱼 | 兜底开关 |

**判断口诀**：目标是"一个"用 `joinedload`，目标是"一堆"用 `selectinload`。

嵌套两层时组合使用（避免 joinedload 套集合）：

```python
stmt = select(User).options(
    selectinload(User.posts).selectinload(Post.tags),
)
```

## 九、事务、并发与乐观锁

### 事务边界

```python
# 方式一：上下文管理器，异常自动回滚
with SessionLocal.begin() as session:
    session.add(order)
    session.add(log)

# 方式二：手动控制 + 保存点（部分回滚）
with SessionLocal() as session:
    with session.begin():
        session.add(order)
        try:
            with session.begin_nested():   # SAVEPOINT
                session.add(risky_record)
        except IntegrityError:
            pass                            # 只回滚保存点，外层继续
```

原则：**一个业务用例一个事务**，事务里不要做网络调用、不要等用户输入。

### 隔离级别

```python
engine = create_engine(url, isolation_level="REPEATABLE READ")
# 或单次连接
with engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn:
    ...
```

### 乐观锁

并发更新同一行时，用版本号避免"后写覆盖先写"：

```python
class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text())
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}
```

SQLAlchemy 会把 UPDATE 改写成
`UPDATE document SET ... , version = version + 1 WHERE id = ? AND version = ?`，
若影响行数为 0 则抛 `StaleDataError`，上层可提示"数据已被他人修改，请刷新"。

### 条件更新（避免读-改-写竞态）

```python
from sqlalchemy import update

result = session.execute(
    update(Account)
    .where(Account.id == 1, Account.balance >= 100)
    .values(balance=Account.balance - 100)
)
if result.rowcount == 0:
    raise ValueError("余额不足或账户不存在")
```

这比 `obj.balance -= 100` 安全得多——后者在并发下会丢更新。

## 十、异步

2.1 起异步是可选依赖，必须装 `sqlalchemy[asyncio]`（内部仍依赖 greenlet 做同步/异步切换）。

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

async_engine = create_async_engine(
    "postgresql+psycopg://app:secret@localhost:5432/app_db",  # psycopg3 支持异步
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, autoflush=False
)


async def get_user(user_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        return await session.get(User, user_id)
```

驱动选择：

| 数据库 | 异步驱动 | URL 前缀 |
| --- | --- | --- |
| PostgreSQL | psycopg 3 | `postgresql+psycopg://` |
| PostgreSQL | asyncpg（性能更高，类型更严格） | `postgresql+asyncpg://` |
| MySQL | aiomysql / asyncmy | `mysql+aiomysql://` |
| SQLite | aiosqlite | `sqlite+aiosqlite://` |

> `postgresql+asyncpg://` 不支持 URL 里的 `?sslmode=` 参数，SSL 需通过 `connect_args={"ssl": ...}` 传。

### 异步三条铁律

1. **所有 IO 都要 `await`**：`await session.execute(...)`、`await session.commit()`、`await session.flush()`。
2. **不能用隐式懒加载**。访问未预加载的关系会抛 `MissingGreenlet`，必须 `selectinload` / `joinedload` 显式加载。
3. **不要跨 `await` 复用同一个 Session**——`AsyncSession` 不是并发安全的，用 `async with` 保证每个协程独立会话。

## 十一、连接池

默认 `QueuePool`（SQLite 的 `:memory:` 用 `SingletonThreadPool`，文件库用 `NullPool` 以外场景需注意）。

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `pool_size` | 5 | 常驻连接数 |
| `max_overflow` | 10 | 峰值可临时超出的数量，上限 = 两者之和 |
| `pool_timeout` | 30 | 取连接等待秒数，超时抛 `TimeoutError` |
| `pool_recycle` | -1 | 连接最大存活秒数，防止被服务端/LB 掐断 |
| `pool_pre_ping` | False | 取连接前先探测，代价是一次轻量往返 |
| `pool_use_lifo` | False | 改为后进先出，空闲连接更少、更适合突发流量 |

**容量估算**：`pool_size + max_overflow` 是**单进程**上限。
多副本部署时总连接数 = 单进程上限 × 副本数，必须小于数据库 `max_connections` 减去运维预留。
32 副本 × (5+10) = 480，已经能打满默认 `max_connections=100` 的 PG。

## 十二、Alembic 迁移

Alembic 是 SQLAlchemy 官方迁移工具，模型即事实来源，靠 autogenerate 生成差异脚本。

```bash
pip install alembic
alembic init migrations          # 生成 migrations/ 目录
```

`migrations/env.py` 关键改动：

```python
from myapp.models import Base

config = context.config
target_metadata = Base.metadata       # 让 autogenerate 知道模型长什么样

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,            # 检测列类型变化
            compare_server_default=True,  # 检测默认值变化
        )
        with context.begin_transaction():
            context.run_migrations()
```

```bash
alembic revision --autogenerate -m "add user.balance"
alembic upgrade head
alembic downgrade -1
```

**autogenerate 的盲区**（必须人工复核）：

- 列重命名会被识别成「删一列 + 加一列」，导致数据丢失；
- `Enum`、`CheckConstraint` 的变更经常漏检；
- 索引改名、`server_default` 的细微差异可能误报；
- 数据迁移（回填、拆表）不会生成，需手写 `op.execute()`。

生产纪律：**迁移脚本入库、按序执行、上线前在影子库跑一遍**，禁止手工改线上表结构。

## 十三、FastAPI 集成范例

```python
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@app.get("/users/{user_id}")
async def read_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.posts))
    )
    user = await session.scalar(stmt)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return {"email": user.email, "post_count": str(len(user.posts))}
```

要点：

- 依赖里 `yield` 会话，FastAPI 会在响应结束时关闭，天然对齐请求生命周期；
- 会话**不要**放进全局变量或模块级单例；
- 写操作在依赖里显式 `await session.commit()`，或用装饰器/中间件统一提交，避免"两个地方都提交"。

## 十四、常见坑与避雷清单

| # | 坑 | 现象 | 解法 |
| --- | --- | --- | --- |
| 1 | 每个请求 `create_engine` | 连接数暴涨、握手开销大 | Engine 进程级单例 |
| 2 | Session 长期存活 | 内存涨、脏数据累积、长事务锁表 | 请求级生命周期 |
| 3 | `expire_on_commit=True` 后访问属性 | 无意中多发 SELECT | `expire_on_commit=False` 或提交后重新查 |
| 4 | 循环里访问关系属性 | N+1 慢查询 | `selectinload` / `joinedload`，或 `lazy="raise"` |
| 5 | 异步里隐式懒加载 | `MissingGreenlet` | 显式预加载 |
| 6 | `== None` 比较 | 生成 `= NULL`，永远不成立 | 用 `.is_(None)` / `.is_not(None)` |
| 7 | 字符串拼 SQL | SQL 注入 | 用 Core 表达式或 `text()` + `bindparam` |
| 8 | 大量单条 INSERT | 慢、日志爆炸 | `session.execute(insert(User), [dict, ...])` 批量 |
| 9 | 忘记 `flush()` 就用自增 ID | `id` 为 `None` | 先 `flush()` |
| 10 | SQLite 多线程共享连接 | `check_same_thread` 报错 | 每线程独立连接或改 PG |

批量写入示例（2.0 ORM bulk insert，走 executemany）：

```python
from sqlalchemy import insert

session.execute(
    insert(User),
    [
        {"email": "a@b.com", "nickname": "A"},
        {"email": "c@d.com", "nickname": "B"},
    ],
)
session.commit()
```

需要拿回自增 ID 时用 `insert(User).returning(User.id)`（PG / SQLite 3.35+ / MySQL 8 支持）。

### SQLite 的两个必设项

```python
from sqlalchemy import event

engine = create_engine("sqlite:///app.db")

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")   # SQLite 默认不校验外键
    cursor.execute("PRAGMA journal_mode=WAL")  # 读写并发更好
    cursor.close()
```

## 十五、完整可运行示例

```python
"""最小可运行 demo：SQLite + 2.1 风格 API。"""
from sqlalchemy import ForeignKey, String, create_engine, func, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
)


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "author"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    books: Mapped[list["Book"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(back_populates="books")


engine = create_engine("sqlite:///:memory:", echo=False)
Base.metadata.create_all(engine)

with Session(engine) as session:
    ada = Author(name="Ada", books=[Book(title="Notes on Analytics")])
    bob = Author(name="Bob", books=[Book(title="SQL in Practice")])
    session.add_all([ada, bob])
    session.commit()

    stmt = (
        select(Author)
        .options(selectinload(Author.books))
        .order_by(Author.name)
    )
    for author in session.scalars(stmt):
        titles = ", ".join(b.title for b in author.books)
        print(f"{author.name}: {titles}")

    total = session.execute(select(func.count()).select_from(Book)).scalar_one()
    print("books =", total)
```

## 十六、参考

- 官方文档：<https://docs.sqlalchemy.org/en/21/>
- 2.1 迁移指南：<https://docs.sqlalchemy.org/en/21/changelog/migration_21.html>
- ORM 快速入门：<https://docs.sqlalchemy.org/en/21/orm/quickstart.html>
- Alembic 文档：<https://alembic.sqlalchemy.org/>
- 相关笔记：[[postgresql|PostgreSQL 基础]]、[[postgresql-advanced|PostgreSQL 特性与实战]]、[[mysql|MySQL 技术指南]]
