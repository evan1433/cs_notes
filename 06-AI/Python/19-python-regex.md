---
title: Python 正则表达式
description: re 模块的匹配函数差异、分组与命名组、贪婪懒惰与占有量词、环视、替换与切分、常用模式库，以及灾难性回溯的实测与修正
tags:
  - python
  - regex
  - stdlib
  - text-processing
date: 2026-11-06
aliases:
  - python-re
  - python-regex
---

# Python 正则表达式

> **版本基线**：`re.fullmatch` 3.4；原子组 `(?>...)` 与占有量词 `*+` / `++` / `?+` 3.11；
> `re.NOFLAG` 3.11。示例在本机 CPython 3.13 实跑验证。

## 1. 先建立正确的心智模型

正则不是"字符串查找函数"，而是一台**带回溯的匹配引擎**。这个模型解释了三件常被误解的事：

- 为什么 `re.match` 匹配不到"出现在中间的日期"——它只从位置 0 开始尝试；
- 为什么贪婪模式会吞掉一整行——引擎优先走"尽可能多"的分支；
- 为什么某些模式会让进程卡死——失败时引擎要穷举所有分支组合，复杂度可能是指数级。

与之对应的三个使用原则：

| 原则 | 原因 |
|------|------|
| 先用最窄的函数（`fullmatch` > `match` > `search`） | 减少试错位置，行为也更明确 |
| 能不用嵌套量词就不用 | `(a+)+` 是 ReDoS 的经典形态 |
| 只在循环外 `compile`，或干脆不 compile | `re` 模块内部已有 512 条缓存 |

## 2. 五个匹配函数的区别

这是最容易出错的地方：**`re.match` 是"从开头匹配"，不是"整串匹配"**。

```python
import re

log = "2026-11-06 10:23:45 ERROR order=order-1001 msg=inventory shortage"

re.match(r"\d{4}", log)                       # 匹配：开头就是 2026
re.search(r"\d{4}", log)                      # 匹配：任意位置
re.fullmatch(r"\d{4}-\d{2}-\d{2}", log)       # None：整串不是纯日期
re.fullmatch(r".*", log)                      # 匹配：.* 可以吃掉整串
```

| 函数 | 起点要求 | 终点要求 | 返回 | 典型用途 |
|------|----------|----------|------|----------|
| `match` | 必须是位置 0 | 可提前结束 | `Match` / `None` | 校验前缀、解析已知格式的开头 |
| `search` | 任意位置 | 可提前结束 | `Match` / `None` | 从文本里找第一个出现 |
| `fullmatch` | 位置 0 | 必须到结尾 | `Match` / `None` | **校验整个字符串格式**（3.4+） |
| `findall` | 任意 | 不适用 | 列表 | 提取所有匹配 |
| `finditer` | 任意 | 不适用 | 迭代器（`Match`） | 需要位置、分组信息时 |

`findall` 与 `finditer` 的关键差别：`findall` 只返回字符串（或元组），
**拿不到位置**；要 `span()`、要惰性处理大文本，用 `finditer`。

```python
for m in re.finditer(r"order=(?P<id>[\w-]+)", log):
    print(m.group("id"), m.span())
```

## 3. 分组：从"取到"到"取到每一部分"

### 3.1 捕获组与命名组

```python
pat = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}) "
    r"(?P<time>\d{2}:\d{2}:\d{2}) "
    r"(?P<level>[A-Z]+) "
    r"order=(?P<order>[\w-]+)"
)
m = pat.search(log)

print(m.groupdict())
# {'date': '2026-11-06', 'time': '10:23:45', 'level': 'ERROR', 'order': 'order-1001'}
print(m.groups())          # ('2026-11-06', '10:23:45', 'ERROR', 'order-1001')
print(m.group(2))          # 10:23:45
print(m.group("level"))    # ERROR
print(m.span("order"))     # (32, 42)
```

命名组不是语法糖：`m.group(3)` 在模式改动后会静默指向别的组，而 `m.group("level")` 不会。
超过两个分组时一律用命名组。

### 3.2 非捕获组与反向引用

```python
re.findall(r"(ab)+", "ababab")      # ['ab']      <- 只保留最后一次捕获
re.findall(r"(?:ab)+", "ababab")    # ['ababab']  <- 整体匹配

re.search(r"(\w+) \1", "hello hello").group(0)          # 'hello hello'
re.search(r"(?P<w>\w+) (?P=w)", "world world").group(0)  # 'world world'
```

`(?:...)` 的作用是"分组但不捕获"。它有两个实际收益：`findall` 的结果形状可预期；
以及在大文本上少分配一批 Match 对象。

### 3.3 findall 的结果形状随分组数变化

这是最隐蔽的陷阱之一：

```python
re.findall(r"(\d+)-(\d+)", "1-2 3-4")   # [('1', '2'), ('3', '4')]  两个组 -> 元组
re.findall(r"(\d+)-\d+", "1-2 3-4")     # ['1', '3']                一个组 -> 字符串
re.findall(r"\d+-\d+", "1-2 3-4")       # ['1-2', '3-4']            无组 -> 整段
```

**加一个括号就会改变返回结构**。写解析代码时如果结果"突然变成元组了"，
先数一下模式里有几个捕获组。

## 4. 量词与回溯

### 4.1 贪婪 / 懒惰 / 占有

```python
html = "<b>bold</b><i>italic</i>"

re.findall(r"<.+>", html)     # ['<b>bold</b><i>italic</i>']      贪婪：吃到最后一个 >
re.findall(r"<.+?>", html)    # ['<b>', '</b>', '<i>', '</i>']    懒惰：吃到第一个 >
re.findall(r"<.+>+", html)    # 贪婪结果，但失败后不回溯（占有量词，3.11+）
```

| 量词 | 写法 | 失败时的行为 |
|------|------|--------------|
| 贪婪 | `.*` `+` `{m,n}` | 回退，尝试更短的匹配 |
| 懒惰 | `.*?` `+?` `{m,n}?` | 回退，尝试更长的匹配 |
| 占有（3.11+） | `.*+` `++` `{m,n}+` | **不回退**，失败即整体失败 |
| 原子组（3.11+） | `(?>...)` | 组内不回退 |

占有量词与原子组的意义不是"写法更短"，而是**从结构上消除回溯**，
这直接决定了正则会不会被恶意输入拖死。

### 4.2 灾难性回溯：实测数据

模式 `(a+)+$`，输入是 n 个 `a` 加一个 `b`（注定匹配失败）：

| 输入长度 | 耗时 | 增长 |
|----------|------|------|
| 16 个 a | 1.4 ms | — |
| 18 个 a | 5.6 ms | 4.0x |
| 20 个 a | 22.4 ms | 4.0x |
| 22 个 a | 91.2 ms | 4.1x |

**每多 2 个字符，耗时涨 4 倍**——这就是指数复杂度。多加 30 个字符，
耗时会超过宇宙年龄。这不是理论问题：任何"用户可控字符串 + 嵌套量词"的组合
都是一个可被远程触发的 CPU 炸弹（ReDoS）。

修正方式：

```python
re.match(r"a++$", "a" * 100_000 + "b")     # 线性，实测 0.03 ms
```

对比另一组（`(?:a|aa)+$` 对 24 个 a，失败匹配）：

| 写法 | 耗时 | 结论 |
|------|------|------|
| `(?:a\|aa)+$` | 2.50 ms | 组内二选一 + 外层重复，仍需穷举 |
| `(?>a\|aa)+$` | 0.03 ms | 原子组阻止组内重试，快 80 倍 |

识别 ReDoS 形态的三条规则：

- 量词套量词：`(a+)+`、`(a*)*`、`(\d+)*`；
- 量词套"可匹配空串的组"：`(a?)+`；
- 交替分支有公共前缀，且外层还有量词：`(a|ab)+`。

## 5. 环视：不消耗字符的断言

环视只做"条件判断"，不推进匹配位置，因此适合表达"后面跟着 X"这类约束：

```python
prices = "价格 199 元，折扣 20%"

re.findall(r"\d+(?= 元)", prices)        # ['199']    正向前瞻：后面是" 元"
re.findall(r"(?<=折扣 )\d+", prices)     # ['20']     正向后顾：前面是"折扣 "
re.findall(r"\d+(?! 元|%)", prices)      # ['19', '2'] 负向前瞻：后面不是元/%
```

| 语法 | 名称 | 含义 |
|------|------|------|
| `(?=X)` | 正向前瞻 | 后面必须是 X |
| `(?!X)` | 负向前瞻 | 后面不能是 X |
| `(?<=X)` | 正向后顾 | 前面必须是 X |
| `(?<!X)` | 负向后顾 | 前面不能是 X |

**后顾要求固定宽度**，这是硬限制：

```pycon
>>> re.search(r"(?<=a+)b", "aab")
re.error: look-behind requires fixed-width pattern
```

`a+` 长度不定，无法后顾。需要"前面是若干个 a"时只能改用捕获组：
`re.search(r"a+(b)", "aab").group(1)`。

## 6. 替换与切分

### 6.1 sub 的三种替换方式

```python
# 1) 反斜杠引用（注意用 raw string）
re.sub(r"(\d{4})-(\d{2})-(\d{2})", r"\3/\2/\1", "2026-11-06")   # 06/11/2026

# 2) 命名组引用用 \g<name>，避免 \1 与后续数字混淆
re.sub(pat, r"\g<level> [\g<order>]", log)

# 3) 函数替换：可以做脱敏、大小写、条件逻辑
def mask(m):
    return m.group(0)[:3] + "****"

re.sub(r"1[3-9]\d{9}", mask, "联系 13812345678 或 15900001111")
# 联系 138**** 或 159****
```

`\g<name>` 不是可选写法而是必要写法：`\1` 后面紧跟数字时（如 `\10`）会被解析成第 10 个组。
`sub` 还有 `count` 参数控制替换次数，默认 0 表示全部。

### 6.2 split 遇到捕获组会保留分隔符

```python
re.split(r"[,;]", "a,b;c")        # ['a', 'b', 'c']
re.split(r"([,;])", "a,b;c")      # ['a', ',', 'b', ';', 'c']
```

这个特性常被误当成 bug。需要保留分隔符时用捕获组；不需要时千万别加括号。

## 7. flags 速查

| flag | 简写 | 作用 | 常见误用 |
|------|------|------|----------|
| `re.IGNORECASE` | `re.I` | 忽略大小写 | 在 `[A-Z]` 上以为也生效（生效，但可能不是你要的语义） |
| `re.MULTILINE` | `re.M` | `^` / `$` 匹配每行首尾 | 以为 `$` 能匹配"字符串结尾"（默认才是） |
| `re.DOTALL` | `re.S` | `.` 匹配换行 | 忘记加，导致跨行匹配失败 |
| `re.VERBOSE` | `re.X` | 允许空白与 `#` 注释 | 在 verbose 模式下忘记转义空格 |
| `re.ASCII` | `re.A` | `\d` `\w` `\b` 只按 ASCII 解释 | 处理中文文本时误加，导致中文不再算 `\w` |
| `re.NOFLAG` | — | 显式表示"无 flag"（3.11+） | 与 `0` 等价，可读性更好 |

实测两个容易踩的点：

```python
re.findall(r"^\w+", "line1\nline2")          # ['line1']            默认 ^ 只匹配串首
re.findall(r"^\w+", "line1\nline2", re.M)    # ['line1', 'line2']   每行都算
```

```python
re.match(r"a.b", "a\nb")            # None，. 默认不匹配换行
re.match(r"a.b", "a\nb", re.S)      # 匹配
```

## 8. 编译与缓存

`re` 模块对最近 512 条模式做了缓存，所以 `re.match(pattern, s)` 写在循环里
也不会反复编译——**前提是 pattern 字符串完全相同**：

```pycon
>>> re._MAXCACHE
512
>>> re.compile(r"\d+") is re.compile(r"\d+")
True
```

真正需要显式 `compile` 的两种情况：

- **缓存被击穿**：动态拼接出成百上千种不同模式（此时缓存毫无作用，应改为固定模式）；
- **需要复用 flags 与命名组**：`pat = re.compile(..., re.I)` 后 `pat.search()`，比每次传参清晰。

另外 `re.escape(text)` 把用户输入当字面量匹配，必须用它而不是手写转义：

```pycon
>>> re.escape("a.b*c(d)")
'a\\.b\\*c\\(d\\)'
```

## 9. 常用模式库

| 目标 | 模式 | 说明 |
|------|------|------|
| 日志行（时间+级别+消息） | `^(\S+ \S+) (\w+) (.*)$` | 配合 `re.M` |
| ISO 日期 | `\d{4}-\d{2}-\d{2}` | 不校验月份范围，仅做结构匹配 |
| 时间 | `\d{2}:\d{2}:\d{2}` | 同上 |
| 手机号（中国大陆） | `1[3-9]\d{9}` | 用 `fullmatch` 校验，`search` 提取 |
| 十六进制颜色 | `#[0-9a-fA-F]{6}\b` | 末尾 `\b` 防止匹配 8 位色值的前 6 位 |
| 键值对 | `(\w+)=("[^"]*"|\S+)` | 先匹配引号包裹，再退回非空白 |
| URL | `https?://[^\s]+` | 宁可宽松，URL 的完整语法不适合用正则表达 |
| 中文 | `[\u4e00-\u9fff]+` | 或直接用 `\w`（默认 Unicode 语义） |

两条使用建议：

- **校验用 `fullmatch`，提取用 `search`/`findall`**。混用会导致"部分匹配也算通过"；
- **不要追求"完美邮箱正则"**。RFC 5322 的完整实现有几千字符且仍会漏判，
  工程上正确做法是"宽松正则 + 发验证邮件"。

## 10. 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| `re.match` 是整串匹配 | 只要求从位置 0 开始，允许提前结束 | 整串校验用 `re.fullmatch` |
| 忘了写 `r""` 前缀 | `"\d"` 在普通字符串里是转义警告或错误字符 | 模式一律用 raw string |
| `.` 能匹配换行 | 默认不匹配 | 需要跨行时加 `re.S` |
| `^` `$` 匹配每行 | 默认只匹配整串首尾 | 多行场景加 `re.M` |
| `\d` 只匹配 0-9 | 默认按 Unicode，会匹配阿拉伯数字等 | 需要仅 ASCII 时加 `re.ASCII` |
| `\w` 只匹配字母数字下划线 | 默认包含中文等 Unicode 字母 | 同上 |
| 字符组里 `-` 不用转义 | `[a-z]` 是区间；要字面 `-` 放首尾或转义 | `[a\-z]` 或 `[-az]` |
| 加括号不影响结果 | 会改变 `findall` 的返回结构，也会改变 `sub` 的引用编号 | 不需要捕获时用 `(?:...)` |
| 用正则解析 HTML / JSON | 嵌套结构 + 转义规则使正则不可靠 | 用专门的解析器（`html.parser`、`json`） |
| 后顾可以任意长度 | 必须固定宽度 | 改用捕获组 |
| 嵌套量词只是写法问题 | 可被构造输入触发指数级回溯（ReDoS） | 用占有量词、原子组，或改写模式 |
| 循环里必须手动 compile | `re` 有 512 条缓存 | 模式固定时无需 compile |

## 11. 与相关概念的关系

- **与 [[13-python-exceptions|Python 异常处理]]**：非法模式抛 `re.error`，
  动态拼接模式时应捕获它并给出可读错误，而不是让服务在启动时崩掉。
- **与 [[17-pytest|pytest 测试]]**：`pytest.raises(..., match=...)` 本身就用正则匹配异常消息，
  所以异常消息里的括号、点号需要考虑转义。
- **与 [[18-debugging-profiling|调试与性能分析]]**：正则卡死表现为"CPU 100% 但无日志"，
  用 `py-spy dump` 能直接看到栈停在 `re` 的匹配函数里。
- **与 [[01-python-basics|Python 基础语法]]**：字符串的 `split` / `replace` / `startswith`
  能解决的问题不要上正则——它们的可读性和性能都更好。

## 参考

- [re — Regular expression operations](https://docs.python.org/3/library/re.html)
- [Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [What's New in Python 3.11 – atomic grouping and possessive quantifiers](https://docs.python.org/3/whatsnew/3.11.html)
- [OWASP ReDoS](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)
- [[06-python-stdlib|Python 内建模块]]
