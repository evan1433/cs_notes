---
title: pytest 测试框架
description: 测试发现规则、assert 重写与 pytest.raises、fixture 作用域与 teardown、参数化、内置 fixture、markers 与覆盖率
tags:
  - python
  - pytest
  - testing
date: 2026-11-06
aliases:
  - python-pytest
  - python-testing
---

# pytest 测试框架

> **版本基线**：`pythonpath` 配置项与 `--strict-markers` 在 pytest 7+ 可用；
> 示例在 pytest 9.2.0 + CPython 3.13 实跑验证（18 passed / 1 skipped / 1 xfailed）。

## 1. 与 unittest 的根本差别

pytest 不需要继承 `TestCase`，也不需要 `assertEqual` 这类专用方法——**直接用 `assert`**：

```python
# unittest
class TestTotal(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(calc_total(items), 44.8)

# pytest
def test_basic():
    assert calc_total(items) == 44.8
```

能做到这点的原因是 pytest 会**重写断言字节码**：失败时把每个子表达式的实际值都打印出来，
而原生 `assert` 只能告诉你"这是 False"。

```text
E       assert 40.32 == 44.8
E        +  where 40.32 = calc_total([{'sku': 'A-1', ...}], 0.1)
```

这条重写只在 pytest 自己的导入钩子下生效——**直接 `python test_x.py` 运行不会重写**，
失败信息会退化。所以测试必须用 `pytest` 命令跑。

## 2. 测试发现规则

pytest 靠命名约定收集用例，不符合约定的函数根本不会被执行：

| 对象 | 默认规则 | 说明 |
|------|----------|------|
| 文件 | `test_*.py` 或 `*_test.py` | 其他文件名不收集 |
| 函数 / 方法 | `test_` 开头 | 后面接什么都行 |
| 类 | `Test` 开头，且**不能有 `__init__`** | 有构造函数会被跳过并警告 |
| 类中的方法 | `test_` 开头 | 普通方法即可，不需要继承 |

目录结构建议把源码与测试分开，避免测试文件被误打包：

```text
project/
├── pyproject.toml
├── src/
│   └── order_service/
│       ├── __init__.py
│       └── core.py
└── tests/
    ├── conftest.py
    ├── test_core.py
    └── test_api.py
```

配置文件（`pytest.ini` 或 `pyproject.toml` 的 `[tool.pytest.ini_options]`）：

```ini
[pytest]
testpaths = tests
pythonpath = src
addopts = -ra --strict-markers
markers =
    slow: 耗时超过 1s 的用例
    integration: 需要外部服务
```

`pythonpath = src`（pytest 7+）替代了流行多年的 `conftest.py` 里 `sys.path.insert` 的写法。
实测把 hack 删掉、只留这行配置，18 个用例仍全部通过。它比 `sys.path` hack 好在
**声明式、只有一处、不污染导入顺序**。

> `testpaths` 的作用是限定默认搜索范围。没有它时 pytest 会从当前目录递归，
> 在 `node_modules`、`.venv` 这类目录上浪费大量时间。

## 3. 断言、异常与浮点比较

### 3.1 pytest.raises

```python
import pytest
from order_service.core import InventoryShortage, calc_total, reserve

def test_calc_total_invalid_discount(sample_items):
    with pytest.raises(ValueError, match=r"折扣必须在 \[0,1\) 内"):
        calc_total(sample_items, discount=-0.1)

def test_reserve_raises_with_attrs():
    with pytest.raises(InventoryShortage) as excinfo:
        reserve("A-1", 5, stock=2)
    assert excinfo.value.sku == "A-1"
    assert excinfo.value.requested == 5
```

三个要点：

- **`match` 是正则，不是子串**。上面的 `\[0,1\)` 必须转义括号，否则匹配不到；
  想匹配字面量就用 `re.escape(...)`。
- `excinfo.value` 是异常实例，可以直接断言自定义属性——这比断言消息字符串稳定得多
  （见 [[13-python-exceptions|Python 异常处理]] 6.2）。
- 代码块里如果**没有抛异常**，pytest 会直接判定失败，错误信息是
  `Failed: DID NOT RAISE ValueError`，而不是静默通过。

### 3.2 浮点比较用 approx

```python
@pytest.mark.parametrize(("discount", "expected"), [(0.0, 44.8), (0.1, 40.32)])
def test_calc_total_discount(sample_items, discount, expected):
    assert calc_total(sample_items, discount) == pytest.approx(expected)
```

`approx` 默认相对容差 `rel=1e-6`、绝对容差 `abs=1e-12`，失败信息会带上容差范围：

```text
E       assert 1000.0 == 1001.0 ± 0.001001
```

不要写 `round(x, 2) == y` 来绕开浮点问题——它掩盖了误差来源，且换个数量级又会失败。

## 4. fixture：pytest 的核心机制

### 4.1 靠参数名注入

fixture 就是一个被 `@pytest.fixture` 装饰的函数，**测试函数的参数名与 fixture 名一致时自动注入**：

```python
import pytest

@pytest.fixture
def sample_items():
    return [
        {"sku": "A-1", "price": 19.9, "qty": 2},
        {"sku": "B-2", "price": 5.0, "qty": 1},
    ]

def test_calc_total_basic(sample_items):        # 参数名 -> fixture
    assert calc_total(sample_items) == 44.8
```

没有魔法：不用 import，不用注册，名字对上就行。代价是**参数名拼错时不会报错**，
只会被当成缺失的 fixture 而报 `fixture 'x' not found`。

### 4.2 作用域与 teardown

`yield` 之前是 setup，之后是 teardown：

```python
@pytest.fixture(scope="module")
def db():
    order.append("db:setup")
    yield "conn"
    order.append("db:teardown")      # 整个模块结束时执行一次
```

| 作用域 | 生命周期 | 典型用途 |
|--------|----------|----------|
| `function`（默认） | 每个测试函数 | 临时数据、monkeypatch |
| `class` | 每个测试类 | 类内共享的上下文 |
| `module` | 每个测试文件 | 数据库连接、启动服务 |
| `package` | 每个包 | 包级资源 |
| `session` | 整个测试会话 | 一次性容器、全局配置 |

实测的执行序列（`db` 为 module 级、`tx` 为 function 级、`trace` 为 autouse）：

```text
['db:setup',
 'trace:enter', 'tx:begin', 'test_first', 'tx:commit', 'trace:exit',
 'trace:enter', 'tx:begin', 'test_second', 'tx:commit', 'trace:exit', ...]
```

两条规律：**外层作用域只 setup 一次**；**同一作用域内 autouse fixture 先于显式声明的 fixture 执行**。
teardown 严格逆序，所以依赖关系不会在清理阶段被破坏。

### 4.3 conftest.py 的层级

`conftest.py` 不需要 import，pytest 自动加载，且**按目录层级向下继承**：

```text
tests/conftest.py          <- 对所有子目录生效
tests/api/conftest.py      <- 只对 tests/api 下的用例生效，可覆盖上层同名 fixture
```

这条机制的实际用途：把耗时的"启动容器"放在根 conftest 并标 `scope="session"`，
把"造测试数据"放在子目录 conftest 并保持 function 作用域。

> 注意：`conftest.py` 里定义的同名 fixture 会**覆盖**上层，而不是合并。
> 排查"为什么这个 fixture 行为和文档不一样"时，先看有没有同名覆盖。

### 4.4 内置 fixture 速查

| fixture | 返回 | 用途 |
|---------|------|------|
| `tmp_path` | `Path` | 每个用例独立的临时目录，自动清理 |
| `tmp_path_factory` | 工厂 | 创建多个临时目录（session 级） |
| `monkeypatch` | 对象 | 临时改环境变量、属性、`sys.path`、当前目录 |
| `capsys` | 对象 | 捕获 `stdout` / `stderr` |
| `caplog` | 对象 | 捕获 logging 记录，可临时调级别 |
| `request` | 对象 | 访问当前用例元信息、`addfinalizer`、`param` |
| `cache` | 对象 | 跨会话持久化少量数据（如 `--lf` 的实现基础） |

`monkeypatch` 会自动还原，不需要手写 try/finally：

```python
def test_load_timeout_env(monkeypatch):
    monkeypatch.setenv("ORDER_TIMEOUT", "7")
    assert load_timeout() == 7
    monkeypatch.delenv("ORDER_TIMEOUT")
    assert load_timeout() == 30

def test_load_timeout_uses_context(monkeypatch):
    with monkeypatch.context() as m:      # 只在这个块内生效
        m.setenv("ORDER_TIMEOUT", "9")
        assert load_timeout() == 9
    assert load_timeout() == 30
```

`monkeypatch.context()` 适合"只在一个断言段里改配置"的场景；直接调用 `setenv` 则是
整个用例有效、结束时统一还原。

`caplog` 必须显式调级别，否则 `INFO` 以下可能被 root logger 的默认级别过滤：

```python
import logging

def test_logs_capture(caplog):
    logger = logging.getLogger("order_service")
    with caplog.at_level(logging.WARNING, logger="order_service"):
        logger.warning("库存不足 sku=%s", "A-1")
    assert "库存不足" in caplog.text
    assert caplog.records[0].levelname == "WARNING"
```

`tmp_path` 与 `monkeypatch` 组合，可以测"读写配置文件"而不碰真实路径：

```python
@pytest.fixture
def temp_config(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[db]\nhost = 'localhost'\n", encoding="utf-8")
    return cfg
```

## 5. 参数化

一份逻辑、多组数据，避免复制粘贴出一堆 `test_xxx_1`、`test_xxx_2`：

```python
@pytest.mark.parametrize(
    ("discount", "expected"),
    [(0.0, 44.8), (0.1, 40.32), (0.5, 22.4)],
    ids=["无折扣", "九折", "五折"],
)
def test_calc_total_discount(sample_items, discount, expected):
    assert calc_total(sample_items, discount) == pytest.approx(expected)
```

| 特性 | 写法 | 说明 |
|------|------|------|
| 多参数 | `("a", "b")` 作为第一个参数 | 元组解包到函数签名 |
| 可读 ID | `ids=[...]` | 报告里显示"九折"而不是 `discount1` |
| 单参数 | `@pytest.mark.parametrize("x", [1, 2])` | 直接给值列表 |
| 组合 | 叠加两个 `parametrize` | 生成笛卡尔积，数量爆炸要当心 |
| 带标记 | `pytest.param(1, marks=pytest.mark.slow)` | 只给某一组数据打标 |
| 间接参数化 | `indirect=["fixture_name"]` | 把参数传给 fixture 而不是测试函数 |

笛卡尔积是最容易失控的地方：3 个参数各 5 个取值就是 125 个用例。
真需要组合时，优先拆成"核心路径 + 边界单独测"。

## 6. 选择、跳过与标记

### 6.1 常用命令行开关

| 命令 | 作用 |
|------|------|
| `pytest -q` | 精简输出 |
| `pytest -x` | 第一个失败就停 |
| `pytest -k "discount and not invalid"` | 按名称表达式筛选用例 |
| `pytest -m "not slow"` | 按 marker 筛 |
| `pytest --lf` | 只跑上次失败的（last-failed） |
| `pytest --ff` | 先跑上次失败的，再跑其余 |
| `pytest -s` | 不捕获输出（`print` 直接可见） |
| `pytest --collect-only -q` | 只看会收集到哪些用例，不执行 |

`-k` 的实测效果：

```console
$ pytest -q -k "discount and not invalid"
3 passed, 17 deselected
```

### 6.2 跳过与预期失败

```python
@pytest.mark.skip(reason="等待库存服务提供批量接口")
def test_batch_reserve():
    ...

@pytest.mark.skipif(os.name == "nt", reason="路径断言只在 POSIX 下成立")
def test_posix_only(temp_config):
    assert "/" in str(temp_config)

@pytest.mark.xfail(reason="浮点累加不精确，待改为 Decimal", strict=True)
def test_float_precision():
    assert 0.1 + 0.2 == 0.3
```

| 标记 | 语义 | 测试通过时 | 测试失败时 |
|------|------|-----------|-----------|
| `skip` | 无条件跳过 | 跳过 | 跳过 |
| `skipif` | 条件跳过 | 视条件 | 视条件 |
| `xfail`（默认） | 预期失败 | XPASS，不算失败 | XFAIL，不算失败 |
| `xfail(strict=True)` | 预期失败，且必须失败 | **XPASS(strict) 判为失败** | XFAIL |

`strict=True` 是推荐配置：它能在 bug 修好之后提醒你"该把这个 xfail 删掉了"。
不加 strict 时，用例悄悄开始通过也不会有人发现，测试语义就烂掉了。

### 6.3 未注册的 marker 会报错

开启 `--strict-markers` 后，用了没在配置里声明的 marker 会在**收集阶段**直接中断：

```text
ERROR collecting tests/test_marker.py
'unknown_marker' not found in `markers` configuration option
Interrupted: 1 error during collection
```

这是一条好的约束：marker 拼错（`@pytest.mark.slwo`）时不会静默失效，
`-m slow` 也不会莫名其妙一个用例都选不中。

## 7. 覆盖率

```console
$ pip install pytest-cov
$ pytest --cov=order_service --cov-report=term-missing
```

实测输出（`core.py` 共 18 条语句）：

```text
Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
src/order_service/core.py          18      1    94%   26
TOTAL                              18      1    94%
```

`Missing` 列直接给出未覆盖行号，比百分比有用得多。本例第 26 行是
`return stock - requested`——只测了"库存不足"分支，没测成功路径。

关于覆盖率的三个判断：

- **行覆盖率不等于分支覆盖率**。`if` 两个分支都执行过，但组合条件可能从未同时为真；
  需要更严格时开 `--cov-branch`。
- **90% 以上的边际收益很低**，剩下的往往是异常处理、防御性分支；
  真正该盯的是"核心业务逻辑是否全部覆盖"。
- **不要为了数字写断言**。`assert True` 也能提高覆盖率，但它的价值是零。

## 8. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| 直接 `python test_x.py` 跑 | 断言重写不生效，失败信息退化 | 统一用 `pytest` 命令 |
| 测试之间共享可变全局状态 | 执行顺序一变就失败，且难以复现 | 每个用例自带 fixture，或 function 作用域 |
| fixture 里写断言 | fixture 报错会被当成"用例错误"而非失败，定位困难 | 断言放测试函数体 |
| 用例依赖执行顺序 | pytest 默认按文件与定义顺序跑，但 `-k`/`-x`/并行都会打破 | 用例必须独立可单跑 |
| 用 `sleep` 等异步结果 | 慢且不稳定 | 用轮询 + 超时，或事件/回调 |
| 只 mock 不验证真实契约 | mock 与真实实现漂移后测试仍绿 | 关键路径保留集成测试 |
| 测试文件重名（不同目录都叫 `test_utils.py`） | 没有 `__init__.py` 时导入冲突 | 加 `__init__.py`，或改用唯一文件名 |
| `conftest.py` 里 `sys.path.insert` | 隐式、难排查、污染导入顺序 | 用 `pythonpath = src` 或 `pip install -e .` |
| `match` 当成子串匹配 | 它是正则，括号、点号都要转义 | `match=re.escape("...")` |
| `xfail` 不加 `strict` | 修好后无人清理，测试语义腐化 | 默认 `strict=True` |

## 9. 与相关概念的关系

- **与 [[13-python-exceptions|Python 异常处理]]**：`pytest.raises(..., match=...)` 用正则匹配
  异常消息，所以异常消息要稳定、可预期；断言自定义异常属性比断言消息更可靠。
- **与 [[14-context-managers|Python 上下文管理器]]**：fixture 的 `yield` 结构与
  `@contextmanager` 同构；`monkeypatch.context()` 本身就是上下文管理器。
- **与 [[16-pathlib|pathlib]]**：`tmp_path` 返回 `Path` 对象，临时文件的读写可以直接用
  pathlib API，不必拼字符串。
- **与 [[15-python-concurrency|Python 并发与并行]]**：并发测试要避免依赖时序；
  `pytest-xdist` 并行执行时会打破"用例按顺序跑"的隐含假设。

## 参考

- [pytest 官方文档](https://docs.pytest.org/en/stable/)
- [How to invoke pytest](https://docs.pytest.org/en/stable/how-to/run.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/)
- [[12-dependency-config|依赖管理配置文件]]
