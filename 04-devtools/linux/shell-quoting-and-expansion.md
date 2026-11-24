---
title: Shell 引号、变量展开与文件名处理
description: $() 命令替换、四种引号规则、参数展开技巧、批量处理文件的安全写法与踩坑清单
tags:
  - linux
  - bash
  - shell
  - quoting
date: 2026-11-20
aliases:
  - shell-quoting
  - shell-expansion
  - bash-pitfalls
---

# Shell 引号、变量展开与文件名处理

覆盖「命令替换 → 引号 → 参数展开 → 文件名 → 批量处理」这条链路。
目标很明确：**让脚本在路径含空格、变量为空、通配无匹配时仍然正确**。

Shell 脚本的 bug 有八成不是因为逻辑写错，而是因为某个变量没加引号、某个 `;` 该是 `&&`、
某个 `$VAR` 为空时变成了一条破坏性命令。

## 1. 命令替换 `$()`

### 1.1 常用命令速查

| 写法 | 作用 |
|------|------|
| `$(date +%F)` | 日期，如 `2026-11-12` |
| `$(date +%s)` | Unix 时间戳，做唯一后缀很稳 |
| `$(date +%Y%m%d-%H%M%S)` | 可读且可排序的时间戳 |
| `$(pwd)` | 当前目录（等价 `$PWD`，但 `$PWD` 不用 fork 子进程） |
| `$(whoami)` / `$USER` | 当前用户 |
| `$(hostname -s)` | 主机名短名 |
| `$(uname -r)` | 内核版本 |
| `$(basename "$path")` | 取文件名 |
| `$(dirname "$path")` | 取目录名 |
| `$(mktemp -d)` | 唯一临时目录，比日期后缀更防冲突 |
| `$(git rev-parse --short HEAD)` | 提交号，打 tag 常用 |
| `$(nproc)` / `$(free -g)` | 核数 / 内存，让脚本自适应机器 |

```bash
# 典型组合：带时间戳的备份
tar czf "backup-$(date +%Y%m%d-%H%M%S).tar.gz" data/

# 建目录后立刻进去（$_ 保存上一条命令的最后一个参数）
mkdir -p "run/$(date +%F)" && cd "$_"
```

> **`$_` 很脆**：它只记"上一条命令的最后一个参数"，中间插任何一条命令都会被覆盖，
> 而且它是 Bash/Zsh 扩展。脚本里更稳的写法是先存变量：
>
> ```bash
> dir="run/$(date +%F)"
> mkdir -p "$dir" && cd "$dir"
> ```

### 1.2 命令替换的两个陷阱

| 陷阱          | 说明                                        | 对策                                                   |
| ----------- | ----------------------------------------- | ---------------------------------------------------- |
| **结果会拆词**   | `$(find . -name '*.log')` 遇到文件名带空格就裂成多个参数 | 改用 `find -print0 \| xargs -0` 或 `while IFS= read -r` |
| **末尾换行被吃掉** | 命令替换会删除所有结尾的 `\n`，需要保留时补一个哨兵字符            | `out=$(cat file; echo x); out=${out%x}`              |
| 反引号难嵌套      | `` `ls \`pwd\`` `` 需要转义                   | 一律用 `$()`，两者等价但 `$()` 可嵌套                            |
| 拆分依赖 `IFS`  | `IFS=,` 会影响后续所有拆词行为                       | 只在局部改：`IFS=, read -ra arr <<< "$line"`               |

```bash
# 反例：文件名带空格时会变成两个参数，第二次 mv 就报错
for f in $(ls *.log); do mv $f backup/; done

# 正解：直接让 shell 展开，不经过命令替换
for f in *.log; do mv -- "$f" backup/; done
```

## 2. 引号规则

`'$date'` 那个坑的根源就在这里。四种写法的差别只有一个：**是否展开、是否拆词**。

```bash
echo '$HOME'    # 字面量 $HOME —— 单引号完全阻止展开
echo "$HOME"    # 展开变量 —— 双引号阻止拆词和通配
echo $HOME      # 展开且拆词/通配（路径含空格会炸）
echo "${HOME}"  # 推荐写法，边界清晰
echo $'a\tb'    # $'...' 支持 \t \n 等 C 风格转义
```

| 写法 | 变量展开 | 拆词 / 通配 | 转义序列 | 典型用途 |
|------|---------|------------|---------|---------|
| `'...'` | ❌ | ❌ | ❌ | 字面量、正则、awk 程序 |
| `"..."` | ✅ | ❌ | 部分（`\$ \` \\ \"`） | **默认选择** |
| `...`（不加引号） | ✅ | ✅ 危险 | ❌ | 几乎永远不该用 |
| `$'...'` | ❌ | ❌ | ✅ `\t \n \x41` | 需要真实制表符/换行 |
| `$"..."` | ✅ | ❌ | 同双引号 | 国际化翻译（几乎不用） |

**记忆点：单引号 = 字面量；双引号 = 可展开但不拆词；不加引号 = 最危险。**

单引号里想包含单引号，没法用 `\'` 转义，只能拼：

```bash
echo 'it'\''s'      # it's
```

### 2.1 `$@` 与 `$*` 的引号差异

| 写法 | 展开后的参数列表 | 说明 |
|------|----------------|------|
| `$*` | `a`　`b`　`c`（3 个） | 先拼成一个字符串再拆词，**最危险** |
| `"$*"` | `a b c`（1 个） | 用 `$IFS` 首字符连接 |
| `$@` | `a`　`b`　`c`（3 个） | 与 `$*` 行为相同 |
| `"$@"` | `a b`　`c`（2 个，原样保留） | **转发参数唯一正确写法** |

示例：脚本收到两个参数 `a b` 和 `c`，上表是四种写法各自展开成的参数个数。

```bash
# 包装命令的标准写法：一个字符都不能少
exec "$@"              # 而不是 exec $@
arr=("$@")             # 数组赋值也要引号
```

## 3. 参数展开：不调外部命令处理路径

`basename` / `dirname` 每次都要 fork 子进程，变量里能用内置展开就别调命令。

```bash
f=/data/model.tar.gz

echo "${f##*/}"      # model.tar.gz   去最长前缀 → basename
echo "${f%/*}"       # /data          去最短后缀 → dirname
echo "${f%.tar.gz}"  # /data/model    去掉指定后缀
echo "${f##*.}"      # gz             取扩展名
echo "${f#*/}"       # data/model.tar.gz  去最短前缀（到第一个 /）
echo "${#f}"         # 18             字符串长度
```

### 3.1 四个修饰符别搞混

| 修饰符 | 匹配方向 | 贪婪程度 | 记忆法 |
|--------|---------|---------|--------|
| `${f#pattern}` | 从左（前缀） | 最短 | `#` 靠左，单个 = 少删 |
| `${f##pattern}` | 从左（前缀） | 最长 | `##` = 删狠点 |
| `${f%pattern}` | 从右（后缀） | 最短 | `%` 靠右，单个 = 少删 |
| `${f%%pattern}` | 从右（后缀） | 最长 | `%%` = 删狠点 |

```bash
p=/a/b/c.tar.gz
echo "${p%%.*}"    # /a/b/c       去掉第一个点之后的一切
echo "${p%.*}"     # /a/b/c.tar   只去掉最后一个扩展名
echo "${p%/*}"     # /a/b         目录
echo "${p##*/}"    # c.tar.gz     文件名
```

### 3.2 扩展能力速查

| 写法 | 作用 | 备注 |
|------|------|------|
| `${#var}` | 长度 | 不适用于数组元素整体长度 |
| `${var:2:3}` | 子串 | 负数偏移表示从末尾算 |
| `${var/old/new}` | 替换第一个 | `${var//old/new}` 替换全部 |
| `${var^^}` / `${var,,}` | 转大写 / 转小写 | Bash 4+ |
| `${var:-默认}` | 未设置或为空 → 用默认（**不改原值**） | 最常用 |
| `${var:=默认}` | 未设置或为空 → 赋值并返回 | `: ${PORT:=8080}` 惯用法 |
| `${var:?错误信息}` | 未设置或为空 → 打印信息并退出 | **防删库神器** |
| `${var:+替代}` | 已设置 → 用替代值 | 条件表达式 |
| `${!prefix*}` | 按前缀取变量名 | 反射式用法，少用 |
| `${arr[@]}` | 数组全部元素 | 必须加引号 `"${arr[@]}"` |

```bash
: "${PORT:=8080}"            # 未设置则赋默认值，且不产生输出
echo "${UNSET:-默认}"        # 未设置时用默认，不改原值
: "${DATA_DIR:?必须指定数据目录}"   # 未设置直接退出，避免后面 rm -rf 空路径
```

## 4. 路径与重命名

```bash
realpath file                # 绝对路径（解析所有符号链接）
readlink -f link             # 解析链接指向的最终目标
readlink link                # 只看一层链接
basename /a/b/c.txt .txt     # c         去后缀
dirname /a/b/c.txt           # /a/b
```

> **macOS 差异**：`readlink -f` 在 BSD `readlink` 上不可用，老系统可改用
> `cd "$(dirname "$f")" && pwd -P`，或 `brew install coreutils` 后用 `grealpath`。

### 4.1 批量改名

`rename` 有两个完全不同的实现，是跨发行版踩坑重灾区：

| 实现 | 语法 | 常见发行版 |
|------|------|-----------|
| Perl 版（`File::Rename`） | `rename 's/old/new/' *.txt` | Debian / Ubuntu |
| util-linux 版 | `rename old new *.txt` | RHEL / Fedora（也可能叫 `prename`） |

```bash
# 不确定环境时，用纯 Bash 循环，零依赖
for f in *.log; do
  mv -- "$f" "${f%.log}.log.bak"
done

# 需要正则替换时先干跑：-n 只打印不执行（Perl 版 rename 支持）
rename -n 's/old/new/' *.txt
```

`mv --` 里的 `--` 表示"选项到此结束"，防止文件名以 `-` 开头被当成参数。

## 5. 批量处理文件的标准姿势

### 5.1 `-exec` 与 `xargs` 怎么选

| 方式 | 写法 | 优点 | 缺点 |
|------|------|------|------|
| `find -exec ... \;` | `find . -name '*.tmp' -exec rm {} \;` | 逐个执行，天然不怕空格 | 每个文件 fork 一次，慢 |
| `find -exec ... +` | `find . -name '*.tmp' -exec rm {} +` | 批量传参，快 | 命令需支持多文件参数 |
| `xargs -0` | `find . -name '*.tmp' -print0 \| xargs -0 rm -f` | 最快，可并行（`-P4`） | 必须配对 `-print0`，否则空格/换行会炸 |
| `while read` | `find ... -print0 \| while IFS= read -r -d '' f` | 循环里可写复杂逻辑 | 稍慢 |

```bash
# 安全三板斧
find . -name '*.tmp' -print           # 1. 干跑，先看会动到哪些文件
find . -name '*.tmp' -exec rm {} +    # 2. 确认后执行（+ 比 \; 快得多）
find . -name '*.tmp' -print0 | xargs -0 rm -f   # 3. 名字可能含空格/换行时用这个
```

```bash
# 需要在循环里做多件事：用 -print0 + read -d ''
find . -name '*.jpg' -print0 |
while IFS= read -r -d '' f; do
  echo "处理: $f"
  convert "$f" "${f%.jpg}.webp"
done
```

> **管道右侧是子 shell**：`find ... | while read ...` 里改的变量在循环外看不到。
> 需要保留结果时用进程替换 `while ... done < <(find ...)`，或把结果写文件。

## 6. 高频踩坑清单

| # | 坑 | 后果 | 正确写法 |
|---|----|------|---------|
| 1 | `mv a/ b` 且 `b` 已存在 | **变成 `b/a` 而不是覆盖**，事后极难发现 | `mv -i`，或先 `ls -d b` 确认，或用 `mv -T` |
| 2 | `rm -rf $DIR/` 而 `$DIR` 为空 | 等价于 `rm -rf /` | `rm -rf "${DIR:?}/"` + 开头 `set -u` |
| 3 | `cd $dir; rm *` | `cd` 失败但 `;` 继续，`rm *` 在**当前目录**执行 | 必须 `&&`；或用 `cd "$dir" \|\| exit 1` |
| 4 | `$date` / `$DATE` 大小写 | Shell 区分大小写，未定义为空，**不会报错** | 开头 `set -u`，变量统一小写 |
| 5 | `rm *.log` 无匹配文件 | 默认原样保留 `*.log` 字面量，报 no such file | `shopt -s nullglob`（展开为空）或 `failglob`（明确报错） |
| 6 | 用变量当命令 `$(echo $CMD)` | 拆词、注入、不可预测 | 用数组 `cmd=(ls -l); "${cmd[@]}"` |
| 7 | `cat x \| cd dir` | 管道在子 shell 里执行，**不影响父进程** | 直接 `cd dir`；管道只用于数据流 |
| 8 | `for f in $(ls)` | 文件名含空格/换行时裂开 | `for f in *` 或 `for f in ./*` |
| 9 | `cat f \| while read` 里 `count++` | 管道右侧子 shell，计数值在外层丢失 | `while ... done < f` 重定向输入 |
| 10 | 变量未加引号 `[ -f $f ]` | `$f` 为空或含空格 → `[: argument expected` | `[ -f "$f" ]`，或改用 `[[ -f $f ]]` |
| 11 | `echo` 处理 `-n` / `-e` 开头内容 | 被当选项吞掉 | 用 `printf '%s\n' "$var"` |
| 12 | 文件名以 `-` 开头 | 被当成命令选项 | 命令加 `--`，或路径写 `./-file` |

### 6.1 坑 1、坑 2 展开说明

```bash
# 坑 1：mv 到已存在的目录 ≠ 覆盖
mkdir -p a/inner b
mv a b            # 结果不是 b 变成 a，而是 b/a/inner
mv -T a b         # -T 把目标当普通文件处理，存在则报错，才是"覆盖"

# 坑 2：空变量的毁灭性
DIR=""
rm -rf $DIR/      # → rm -rf /   （历史上真实发生过的生产事故）
rm -rf "${DIR:?}" # → 直接退出：DIR: parameter null or not set
```

## 7. 写脚本前的护身符

### 7.1 开头三件套

```bash
#!/usr/bin/env bash
set -euo pipefail   # 出错即停 / 未定义变量报错 / 管道任一环节失败即失败
IFS=$'\n\t'         # 收窄默认拆词字符（谨慎：会影响所有未加引号的展开）
```

| 选项 | 作用 | 坑 |
|------|------|-----|
| `-e` | 命令返回非 0 立即退出 | 在 `if`、`while`、`&&`、`\|\|`、`!` 上下文中**不生效** |
| `-u` | 引用未定义变量报错 | `"$@"`（无参数）在 bash 4.4 前会报错，用 `"${@:-}"` |
| `-o pipefail` | 管道整体返回最后一个非 0 退出码 | 与 `grep` 无匹配（返回 1）配合时注意 |

### 7.2 临时目录与清理

```bash
#!/usr/bin/env bash
set -euo pipefail

# mktemp -d 生成唯一目录，比 date 后缀更防冲突
workdir=$(mktemp -d)
# 无论正常结束还是被中断，都清理
trap 'rm -rf "$workdir"' EXIT INT TERM

echo "工作目录: $workdir"
```

### 7.3 静态检查

```bash
# 装一次即可；能查出未加引号的变量、失效的 cd、误用的 glob
shellcheck script.sh

# 只看 error 级别，CI 里用
shellcheck -S error script.sh
```

`shellcheck` 的 `SC2086`（未加引号导致拆词）就是本文档一半内容的自动检查版。
把它加进 CI，这类问题基本不会上线。

## 8. 速查表

| 目的 | 写法 |
|------|------|
| 取文件名 / 目录 | `${f##*/}` / `${f%/*}` |
| 去扩展名 | `${f%.*}` |
| 取扩展名 | `${f##*.}` |
| 未设置给默认 | `${var:-默认}` |
| 强制要求非空 | `${var:?错误信息}` |
| 遍历文件（安全） | `for f in ./*; do ...; done` |
| 遍历 find 结果（安全） | `find ... -print0 \| while IFS= read -r -d '' f` |
| 批量删除（安全） | `find ... -print` → 确认 → `-exec rm {} +` |
| 参数透传 | `"$@"` |
| 打印变量（防选项） | `printf '%s\n' "$var"` |
| 选项终止符 | `mv -- "$f" dest/` |

## 相关笔记

- [[bash-basics|Bash 基础]] — 变量、引号、数组、条件、循环的入门语法
- [[shell-io-redirection|Shell IO 重定向与管线]] — 管道与重定向的机制，理解"管道子 shell"的前提
- [[find-command|find 命令详解]] — `-exec`、`-print0` 与批量操作的完整参数
- [[text-processing-commands|Linux 文本处理命令]] — sed/awk 与 `while read` 的组合用法
- [[file-permissions|文件权限管理]] — 批量操作前的属主与权限确认

## 参考

- [Bash 手册：Shell Parameter Expansion](https://www.gnu.org/software/bash/manual/bash.html#Shell-Parameter-Expansion)
- [Bash 手册：Quoting](https://www.gnu.org/software/bash/manual/bash.html#Quoting)
- [ShellCheck 错误码索引](https://www.shellcheck.net/wiki/)
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
