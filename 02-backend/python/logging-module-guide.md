---
title: Python logging 模块使用指南
description: Python logging 模块完整用法，涵盖基础配置、Handler、Formatter、Filter 及生产级日志方案
tags:
  - python
  - logging
  - stdlib
date: 2026-05-21
---

## 目录

1. [模块简介](#模块简介)
2. [快速上手](#快速上手)
3. [日志级别](#日志级别)
4. [核心组件](#核心组件)
5. [Handler 详解](#handler-详解)
6. [Formatter 格式化](#formatter-格式化)
7. [Filter 过滤](#filter-过滤)
8. [配置方式](#配置方式)
9. [模块化日志架构](#模块化日志架构)
10. [实用示例](#实用示例)
11. [最佳实践](#最佳实践)
12. [常见问题](#常见问题)

---

## 模块简介

`logging` 是 Python 标准库中用于记录日志的模块，提供了灵活的事件记录系统。相比 `print()` 语句，logging 模块具备以下优势：

- **分级控制**：通过日志级别过滤消息，生产环境只输出重要信息
- **多目标输出**：同时将日志写入控制台、文件、网络等
- **格式化输出**：统一的消息格式，包含时间、级别、模块等上下文
- **线程安全**：内置线程锁，多线程环境下无需额外处理
- **模块隔离**：每个模块可独立配置 logger，互不干扰

### 导入方式

```python
import logging

# 获取模块级 logger（推荐）
logger = logging.getLogger(__name__)
```

> **重要**：永远不要直接使用 `logging.info()` 等模块级函数，应通过 `logging.getLogger(__name__)` 获取 logger 实例，以实现模块化日志管理。

---

## 快速上手

### 最简配置

```python
import logging

# 基本配置：输出到控制台
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

输出示例：

```
2026-05-21 10:30:00,123 - __main__ - DEBUG - 调试信息
2026-05-21 10:30:00,124 - __main__ - INFO - 一般信息
2026-05-21 10:30:00,124 - __main__ - WARNING - 警告信息
2026-05-21 10:30:00,125 - __main__ - ERROR - 错误信息
2026-05-21 10:30:00,125 - __main__ - CRITICAL - 严重错误
```

### 写入文件

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',       # 日志文件路径
    filemode='a',             # 追加模式（默认），'w' 为覆盖
    encoding='utf-8'          # Python 3.9+ 支持指定编码
)

logger = logging.getLogger(__name__)
logger.info("这条消息将写入 app.log 文件")
```

---

## 日志级别

Python 定义了 5 个标准日志级别，从低到高：

| 级别 | 数值 | 适用场景 | 示例 |
|------|------|----------|------|
| `DEBUG` | 10 | 开发调试时的详细信息 | 变量值、函数调用参数 |
| `INFO` | 20 | 确认程序按预期运行的常规信息 | 服务启动、请求完成 |
| `WARNING` | 30 | 表明潜在问题，程序仍可运行 | 配置项缺失使用默认值 |
| `ERROR` | 40 | 严重问题，部分功能失败 | 数据库连接失败 |
| `CRITICAL` | 50 | 严重错误，程序可能无法继续运行 | 磁盘满、内存耗尽 |

### 自定义级别

```python
# 定义新级别（不推荐，除非有充分理由）
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

# 为 logger 添加 trace 方法
def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

import types
logger.trace = types.MethodType(trace, logger)

logger.trace("详细追踪信息")
```

> **注意**：自定义级别会破坏日志生态兼容性，尽量使用标准级别。需要更细粒度控制时，优先使用 Filter 或额外的 logger。

---

## 核心组件

logging 模块采用分层架构，由四大核心组件构成：

```
Logger ──→ Handler ──→ Formatter
  │            │
  └──→ Filter ←┘
```

| 组件 | 职责 | 类比 |
|------|------|------|
| **Logger** | 日志入口，暴露记录接口 | 邮局窗口 |
| **Handler** | 将日志发送到目的地 | 邮递员 |
| **Formatter** | 定义日志的显示格式 | 信件模板 |
| **Filter** | 过滤哪些日志可以被记录 | 门卫 |

### Logger 层级

Logger 采用点号分隔的层级命名，形成父子关系：

```python
# 层级关系示例
app_logger = logging.getLogger('app')                    # 父
api_logger = logging.getLogger('app.api')                 # 子
api_user_logger = logging.getLogger('app.api.user')       # 孙

# 子 logger 的日志会向上传播给父 logger（默认行为）
api_user_logger.info("消息")  # 此消息也会被 app_logger 和 api_logger 的 handler 处理
```

```python
# 关闭传播（子 logger 独立处理日志）
api_logger.propagate = False
```

---

## Handler 详解

Handler 决定日志的去向。一个 Logger 可以绑定多个 Handler，实现同时输出到多个目的地。

### 常用 Handler

| Handler | 用途 | 关键参数 |
|---------|------|----------|
| `StreamHandler` | 输出到控制台 | `stream=sys.stderr`（默认） |
| `FileHandler` | 输出到文件 | `filename`, `mode`, `encoding` |
| `RotatingFileHandler` | 按大小轮转文件 | `maxBytes`, `backupCount` |
| `TimedRotatingFileHandler` | 按时间轮转文件 | `when`, `interval`, `backupCount` |
| `QueueHandler` | 异步日志（配合 QueueListener） | `queue` |
| `NullHandler` | 丢弃所有日志 | 无 |

### StreamHandler — 控制台输出

```python
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 控制台 handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

logger.info("输出到控制台")
```

### FileHandler — 文件输出

```python
# 基本文件输出
file_handler = logging.FileHandler(
    'app.log',
    mode='a',           # 追加模式
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
```

### RotatingFileHandler — 按大小轮转

```python
from logging.handlers import RotatingFileHandler

# 单个文件最大 10MB，保留 5 个备份
rotating_handler = RotatingFileHandler(
    'app.log',
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
rotating_handler.setFormatter(formatter)
logger.addHandler(rotating_handler)

# 轮转后的文件：app.log, app.log.1, app.log.2, ..., app.log.5
```

### TimedRotatingFileHandler — 按时间轮转

```python
from logging.handlers import TimedRotatingFileHandler

# 每天午夜轮转，保留 30 天
timed_handler = TimedRotatingFileHandler(
    'app.log',
    when='midnight',    # 轮转时机
    interval=1,          # 间隔
    backupCount=30,      # 保留份数
    encoding='utf-8'
)
timed_handler.setFormatter(formatter)
logger.addHandler(timed_handler)

# 轮转后的文件：app.log, app.log.2026-05-20, app.log.2026-05-19, ...
```

`when` 参数取值：

| 值 | 含义 | 轮转文件后缀示例 |
|----|------|-----------------|
| `'S'` | 秒 | `app.log.2026-05-21_10-30-00` |
| `'M'` | 分钟 | `app.log.2026-05-21_10-30` |
| `'H'` | 小时 | `app.log.2026-05-21_10` |
| `'D'` | 天 | `app.log.2026-05-21` |
| `'midnight'` | 每天午夜 | `app.log.2026-05-21` |
| `'W0'`~`'W6'` | 每周指定日（0=周一） | `app.log.2026-05-19` |

### QueueHandler — 异步日志

在高并发场景下，同步写日志会阻塞主线程。`QueueHandler` + `QueueListener` 提供异步方案：

```python
import logging
import logging.handlers
import queue

# 创建日志队列
log_queue = queue.Queue(-1)  # 无限大小

# 主线程：使用 QueueHandler（非阻塞）
queue_handler = logging.handlers.QueueHandler(log_queue)

logger = logging.getLogger(__name__)
logger.addHandler(queue_handler)
logger.setLevel(logging.INFO)

# 后台线程：QueueListener 负责实际写入
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setFormatter(formatter)

listener = logging.handlers.QueueListener(
    log_queue,
    file_handler,
    respect_handler_level=True  # 尊重 handler 自身的 level 设置
)
listener.start()

# 程序退出时必须停止 listener
import atexit
atexit.register(listener.stop)

# 在主线程中记录日志（几乎零延迟）
logger.info("异步日志消息")
```

---

## Formatter 格式化

Formatter 控制日志消息的最终输出格式。

### 常用格式占位符

| 占位符 | 含义 | 示例输出 |
|--------|------|----------|
| `%(asctime)s` | 时间戳 | `2026-05-21 10:30:00,123` |
| `%(name)s` | Logger 名称 | `app.api.user` |
| `%(levelname)s` | 级别名称 | `INFO` |
| `%(levelno)d` | 级别数值 | `20` |
| `%(message)s` | 日志消息 | `用户登录成功` |
| `%(filename)s` | 文件名 | `auth.py` |
| `%(lineno)d` | 行号 | `42` |
| `%(funcName)s` | 函数名 | `login` |
| `%(module)s` | 模块名 | `auth` |
| `%(pathname)s` | 完整路径 | `/app/api/auth.py` |
| `%(process)d` | 进程 ID | `12345` |
| `%(processName)s` | 进程名 | `MainProcess` |
| `%(thread)d` | 线程 ID | `140234567890` |
| `%(threadName)s` | 线程名 | `worker-1` |

### 常用格式模板

```python
# 开发环境：详细格式
dev_fmt = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 生产环境：简洁格式
prod_fmt = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# JSON 格式（适合 ELK/Splunk 等日志平台）
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno,
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)
```

---

## Filter 过滤

Filter 提供比日志级别更细粒度的控制，可以基于任意条件决定是否记录日志。

### 基本用法

```python
class LevelFilter(logging.Filter):
    """只允许指定级别的日志通过"""

    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        return record.levelno == self.level

# 只输出 WARNING 级别到特定 handler
warning_handler = logging.StreamHandler()
warning_handler.addFilter(LevelFilter(logging.WARNING))
warning_handler.setFormatter(formatter)
logger.addHandler(warning_handler)
```

### 按模块过滤

```python
class ModuleFilter(logging.Filter):
    """只允许指定模块前缀的日志通过"""

    def __init__(self, prefix):
        super().__init__()
        self.prefix = prefix

    def filter(self, record):
        return record.name.startswith(self.prefix)

# 只记录 app.api 模块的日志
api_handler = logging.FileHandler('api.log', encoding='utf-8')
api_handler.addFilter(ModuleFilter('app.api'))
api_handler.setFormatter(formatter)
logger.addHandler(api_handler)
```

### 添加上下文信息

```python
class ContextFilter(logging.Filter):
    """在日志记录中注入上下文信息"""

    def filter(self, record):
        record.user_id = getattr(record, 'user_id', 'anonymous')
        record.request_id = getattr(record, 'request_id', 'N/A')
        return True

# 使用自定义字段
logger.addFilter(ContextFilter())

formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] [%(user_id)s] [%(request_id)s] %(message)s'
)
handler.setFormatter(formatter)

# 记录时传入上下文
logger.info("用户操作", extra={'user_id': 'u123', 'request_id': 'req456'})
```

---

## 配置方式

logging 模块支持 3 种配置方式，从简单到灵活：

### 1. basicConfig — 适合简单脚本

```python
# 必须在首次调用 logging.info/debug 等函数之前调用
# 且只生效一次（后续调用不会覆盖已有配置）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='app.log',
    filemode='a',
    encoding='utf-8'
)
```

> **注意**：`basicConfig` 仅在根 logger 无 handler 时生效。如果已经创建了 handler（比如第三方库已调用过），再次调用 `basicConfig` 不会产生效果。

### 2. dictConfig — 适合中大型项目（推荐）

```python
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,  # 不禁用已有 logger

    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'app.log',
            'maxBytes': 10485760,   # 10 MB
            'backupCount': 5,
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        'app': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'app.api': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': True,
        },
    },

    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

# 使用
logger = logging.getLogger('app')
logger.info("通过 dictConfig 配置的日志")
```

### 3. fileConfig — 从 INI 文件加载

```ini
# logging.ini
[loggers]
keys=root,app

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=standardFormatter

[logger_root]
level=WARNING
handlers=consoleHandler

[logger_app]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=app
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=standardFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=standardFormatter
args=('app.log', 'a', 10485760, 5, 'utf-8')

[formatter_standardFormatter]
format=%(asctime)s [%(levelname)s] %(name)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
```

```python
import logging.config

logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
```

> **推荐**：新项目优先使用 `dictConfig`，它支持字典嵌套、更具可读性，且与 YAML/JSON 配置文件配合良好。`fileConfig` 使用 INI 格式，功能受限且可读性较差。

### 三种配置方式对比

| 特性 | `basicConfig` | `dictConfig` | `fileConfig` |
|------|--------------|--------------|--------------|
| 复杂度 | 简单 | 中等 | 中等 |
| 多 handler | 不支持 | 支持 | 支持 |
| 多 logger | 不支持 | 支持 | 支持 |
| 配置来源 | 代码内联 | dict / YAML / JSON | INI 文件 |
| 轮转 handler | 不支持 | 支持 | 支持 |
| 适用场景 | 脚本 / 原型 | 生产项目 | 遗留项目 |

---

## 模块化日志架构

在多模块项目中，推荐以下日志架构：

### 项目结构

```
my_app/
├── __init__.py
├── main.py           # 初始化日志配置
├── api/
│   ├── __init__.py
│   └── auth.py       # 使用 logging.getLogger(__name__)
└── core/
    ├── __init__.py
    └── service.py     # 使用 logging.getLogger(__name__)
```

### 入口文件初始化

```python
# main.py
import logging
import logging.config

def setup_logging():
    """应用启动时调用一次"""
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': 'app.log',
                'maxBytes': 10485760,
                'backupCount': 5,
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            'my_app': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False,
            },
        },
        'root': {
            'level': 'WARNING',
        },
    }
    logging.config.dictConfig(config)

# 启动
setup_logging()
```

### 各模块使用

```python
# api/auth.py
import logging

logger = logging.getLogger(__name__)  # logger 名为 'my_app.api.auth'

def login(username, password):
    logger.info(f"用户登录尝试: {username}")
    if authenticate(username, password):
        logger.info(f"用户登录成功: {username}")
        return True
    logger.warning(f"用户登录失败: {username}")
    return False
```

```python
# core/service.py
import logging

logger = logging.getLogger(__name__)  # logger 名为 'my_app.core.service'

def process_data(data):
    logger.debug(f"开始处理数据，大小: {len(data)}")
    try:
        result = transform(data)
        logger.info("数据处理完成")
        return result
    except Exception as e:
        logger.error(f"数据处理失败: {e}", exc_info=True)
        raise
```

---

## 实用示例

### 示例1：多环境配置

```python
import logging
import logging.config
import os

def get_logging_config(env='development'):
    """根据环境返回不同的日志配置"""

    base_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
    }

    if env == 'development':
        base_config.update({
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'detailed',
                    'stream': 'ext://sys.stdout',
                },
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['console'],
            },
        })
    elif env == 'production':
        base_config.update({
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'WARNING',
                    'formatter': 'standard',
                    'stream': 'ext://sys.stderr',
                },
                'file': {
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'detailed',
                    'filename': '/var/log/app/app.log',
                    'when': 'midnight',
                    'backupCount': 30,
                    'encoding': 'utf-8',
                },
            },
            'root': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
            },
        })

    return base_config

# 使用
env = os.getenv('APP_ENV', 'development')
logging.config.dictConfig(get_logging_config(env))
```

### 示例2：结构化 JSON 日志

```python
import logging
import json
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    """输出 JSON 格式日志，适合 ELK / Splunk / Datadog"""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # 合并 extra 字段
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)

        # 异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# 使用
logger = logging.getLogger('app')
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info(
    "订单创建成功",
    extra={'extra_data': {
        'order_id': 'ORD-20260521-001',
        'user_id': 'u123',
        'amount': 99.9,
    }}
)
```

输出：

```json
{"timestamp":"2026-05-21T02:30:00.123456+00:00","level":"INFO","logger":"app","message":"订单创建成功","module":"order","function":"create","line":42,"order_id":"ORD-20260521-001","user_id":"u123","amount":99.9}
```

### 示例3：日志 + 异常通知

```python
import logging
import logging.handlers
import smtplib
from email.mime.text import MIMEText

class EmailHandler(logging.Handler):
    """ERROR 及以上级别发送邮件通知"""

    def __init__(self, mailhost, fromaddr, toaddrs, subject, credentials=None):
        super().__init__()
        self.mailhost = mailhost
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs if isinstance(toaddrs, list) else [toaddrs]
        self.subject = subject
        self.credentials = credentials
        self.setLevel(logging.ERROR)  # 仅处理 ERROR 及以上

    def emit(self, record):
        try:
            msg = MIMEText(self.format(record))
            msg['Subject'] = f"{self.subject} [{record.levelname}]"
            msg['From'] = self.fromaddr
            msg['To'] = ', '.join(self.toaddrs)

            with smtplib.SMTP(self.mailhost) as server:
                if self.credentials:
                    server.login(*self.credentials)
                server.send_message(msg)
        except Exception:
            self.handleError(record)

# 使用
email_handler = EmailHandler(
    mailhost='smtp.example.com',
    fromaddr='alert@example.com',
    toaddrs=['dev-team@example.com'],
    subject='[App Alert]',
    credentials=('user', 'password')
)
email_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s\n%(message)s\n'
    'Location: %(pathname)s:%(lineno)d'
))
logger.addHandler(email_handler)
```

### 示例4：Web 框架集成（FastAPI）

```python
import logging
import logging.config
from fastapi import FastAPI, Request
from contextvars import ContextVar

# 请求 ID 上下文变量
request_id_var: ContextVar[str] = ContextVar('request_id', default='N/A')

class RequestIdFilter(logging.Filter):
    """在每个日志记录中注入 request_id"""

    def filter(self, record):
        record.request_id = request_id_var.get('')
        return True

# 日志配置
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {
            '()': RequestIdFilter,
        },
    },
    'formatters': {
        'with_request': {
            'format': '%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'with_request',
            'filters': ['request_id'],
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

app = FastAPI()

import uuid

@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    logger.info(f"查询用户: user_id={user_id}")
    return {"user_id": user_id, "name": "Test User"}
```

---

## 最佳实践

### 1. 使用 `__name__` 命名 logger

```python
# 正确：模块自动命名
logger = logging.getLogger(__name__)

# 错误：硬编码名称，难以追踪
logger = logging.getLogger('my_logger')
```

### 2. 只在入口配置日志

```python
# main.py（入口）—— 配置日志
import logging.config
logging.config.dictConfig(LOGGING_CONFIG)

# 其他模块 —— 只获取 logger，不做配置
import logging
logger = logging.getLogger(__name__)
```

### 3. 使用 `lazy %` 而非 f-string（性能敏感场景）

```python
# 推荐：延迟格式化，如果日志级别不匹配则不执行字符串拼接
logger.debug("Processing item %s with value %d", item_id, value)

# 也行但不够优化：无论级别是否匹配都会执行 f-string
logger.debug(f"Processing item {item_id} with value {value}")

# 如果格式化开销很小（简单变量），f-string 完全可以接受
logger.info(f"User {user_id} logged in")
```

### 4. 记录异常时使用 `exc_info`

```python
try:
    result = risky_operation()
except ValueError as e:
    # 正确：包含完整堆栈跟踪
    logger.error("操作失败: %s", e, exc_info=True)

    # 也行：logger.exception 自动设置 exc_info=True
    logger.exception("操作失败: %s", e)

    # 错误：丢失堆栈信息
    logger.error(f"操作失败: {e}")
```

### 5. 生产环境使用 RotatingFileHandler

```python
# 正确：自动轮转，避免磁盘写满
handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)

# 危险：日志文件无限增长
handler = FileHandler('app.log')
```

### 6. 关闭第三方库的冗余日志

```python
# 方式1：设置特定库的日志级别
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

# 方式2：在 dictConfig 中配置
'loggers': {
    'urllib3': {
        'level': 'WARNING',
    },
    'matplotlib': {
        'level': 'WARNING',
    },
}
```

### 7. 库作者使用 NullHandler

```python
# my_library/__init__.py
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
```

> 这是最重要的库开发规范：**库代码不应配置日志**，只添加 `NullHandler` 防止"No handler found"警告，将配置权交给使用者。

### 8. 使用 extra 传递结构化数据

```python
# 正确：结构化数据
logger.info(
    "API request completed",
    extra={
        'extra_data': {
            'method': 'GET',
            'path': '/api/users',
            'status': 200,
            'duration_ms': 45,
        }
    }
)

# 避免：把所有信息塞进 message
logger.info("API request: method=GET path=/api/users status=200 duration=45ms")
```

### 9. 避免在日志中记录敏感信息

```python
# 危险：明文记录密码
logger.info(f"User login: {username}, password={password}")

# 正确：脱敏处理
logger.info(f"User login: {username}, token=***")

# 更好：使用 Filter 自动脱敏
class SensitiveDataFilter(logging.Filter):
    SENSITIVE_KEYS = {'password', 'token', 'secret', 'api_key', 'credit_card'}

    def filter(self, record):
        msg = record.getMessage()
        for key in self.SENSITIVE_KEYS:
            # 简单替换（生产环境应使用正则更精确地匹配）
            msg = msg.replace(key, f'{key}=***')
        record.msg = msg
        return True
```

---

## 常见问题

### Q1: `basicConfig` 不生效？

原因：`basicConfig` 仅在根 logger 没有 handler 时生效。如果之前已经调用了 `logging.info()` 等函数，root logger 会自动创建默认 handler，后续 `basicConfig` 就不再起作用。

```python
# 解决：确保 basicConfig 在任何日志调用之前执行
logging.basicConfig(level=logging.INFO)  # 必须是第一行
logger = logging.getLogger(__name__)
logger.info("现在可以正常工作")
```

### Q2: 日志重复输出？

原因：logger 的 `propagate` 属性默认为 `True`，子 logger 的日志会向上传播到父 logger，如果父子都有 handler，就会重复输出。

```python
# 解决方式1：关闭传播
logger.propagate = False

# 解决方式2：只在 root logger 上配 handler，子 logger 不配
```

### Q3: 第三方库日志太多？

```python
# 全局设置第三方库日志级别
logging.getLogger('urllib3').setLevel(logging.WARNING)

# 或在 dictConfig 中：
'loggers': {
    'urllib3': {'level': 'WARNING'},
    'botocore': {'level': 'WARNING'},
    'matplotlib': {'level': 'WARNING'},
}
```

### Q4: 多进程日志如何处理？

`logging` 模块的 handler 不是进程安全的。推荐方案：

```python
# 方案1：每个进程写独立文件
# 简单但需要后续合并

# 方案2：使用 QueueHandler + QueueListener（单进程内多线程安全）
# 多进程时每个进程用独立的 QueueHandler，由监听进程统一写文件

# 方案3：使用 ConcurrentLogHandler（第三方库）
# pip install ConcurrentLogHandler
from cloghandler import ConcurrentRotatingFileHandler
handler = ConcurrentRotatingFileHandler('app.log', 'a', maxBytes=10*1024*1024, backupCount=5)

# 方案4：写 stdout，由进程管理器（supervisor / docker）收集
```

### Q5: 如何动态修改日志级别？

```python
# 修改 logger 级别
logger.setLevel(logging.DEBUG)

# 修改 handler 级别
handler.setLevel(logging.DEBUG)

# 运行时通过信号切换（如 SIGUSR1）
import signal

def toggle_debug(signum, frame):
    current = logger.level
    new_level = logging.DEBUG if current > logging.DEBUG else logging.INFO
    logger.setLevel(new_level)
    logger.info(f"日志级别切换为: {logging.getLevelName(new_level)}")

signal.signal(signal.SIGUSR1, toggle_debug)
```

### Q6: `logging` vs `loguru` vs `structlog`？

| 特性 | `logging` | `loguru` | `structlog` |
|------|-----------|----------|-------------|
| 类型 | 标准库 | 第三方 | 第三方 |
| 配置复杂度 | 较高 | 极低 | 中等 |
| 结构化日志 | 需自定义 | 内置 | 核心特性 |
| 性能 | 好 | 好 | 优秀 |
| 生态兼容 | 所有库 | 需适配 | 需适配 |
| 推荐场景 | 所有项目 | 小型项目 / 快速原型 | 微服务 / 日志平台 |

> **选择建议**：标准库 `logging` 是最稳妥的选择，所有第三方库都使用它，不存在兼容性问题。`loguru` 适合小型项目和脚本，配置更简单。`structlog` 适合对结构化日志有强烈需求的微服务项目。

---

## 总结

`logging` 模块是 Python 应用的日志基础设施，核心要点：

1. **始终用 `logging.getLogger(__name__)`** 获取 logger，而非模块级函数
2. **入口文件统一配置**，模块只获取 logger 不配置
3. **生产环境用 `dictConfig`** 配置多 handler、多 formatter
4. **用 `RotatingFileHandler`** 防止日志文件无限增长
5. **异常日志用 `exc_info=True`** 或 `logger.exception()` 保留堆栈
6. **库作者只加 `NullHandler`**，不做任何日志配置
7. **避免日志重复**：理解 `propagate` 机制，合理规划 handler 分布

---

## See Also

- [[06-python-stdlib|Python 内建模块]] —— `sys.stderr`、`os.getpid()` 等日志常用信息来源
- [[python-f-string-cheatsheet|f-String 速查]] —— 指标与训练日志的格式化写法
- [[os-module-guide|os 模块使用指南]] —— 日志目录创建、权限与轮转文件路径
- [[pydantic-validation|Pydantic 数据类型校验]] —— 结构化日志字段的校验与序列化
- [[python/index|Python 笔记目录]]
