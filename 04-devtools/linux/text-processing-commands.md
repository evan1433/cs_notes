---
title: Linux 文本处理命令
description: Linux sed、awk、cut、wc、sort、uniq、tr、xargs 等文本处理命令的常用语法与实战示例
tags:
  - linux
  - command
  - shell
  - text-processing
date: 2026-07-09
---

# Linux 文本处理命令

Linux 文本处理命令适合处理日志、CSV、配置文件、命令输出等行式文本。
常见思路是：先用 `grep` 筛选行，再用 `cut` / `awk` 提取列，用 `sed` 修改文本，
用 `sort` / `uniq` 聚合，最后用 `wc` 统计结果。

## 1. 准备示例数据

后续示例使用下面的 `access.log` 和 `users.csv`。可以直接复制到终端运行。

```bash
cat > access.log << 'EOF'
10.0.0.1 - - [01/Jul/2026:10:00:01 +0800] "GET /api/users HTTP/1.1" 200 1234
10.0.0.2 - - [01/Jul/2026:10:00:03 +0800] "POST /api/login HTTP/1.1" 401 532
10.0.0.1 - - [01/Jul/2026:10:00:06 +0800] "GET /api/orders HTTP/1.1" 200 2450
10.0.0.3 - - [01/Jul/2026:10:00:09 +0800] "GET /api/users HTTP/1.1" 500 98
10.0.0.2 - - [01/Jul/2026:10:00:12 +0800] "GET /static/app.js HTTP/1.1" 200 8450
EOF

cat > users.csv << 'EOF'
id,name,role,score
1,Alice,admin,95
2,Bob,user,78
3,Carol,user,88
4,David,guest,64
EOF
```

## 2. 总体速查

| 命令 | 作用 | 典型场景 |
| ---- | ---- | -------- |
| `cut` | 按分隔符或字符位置截取字段 | 提取 CSV、`/etc/passwd` 字段 |
| `wc` | 统计行数、单词数、字节数、字符数 | 统计文件大小、结果数量 |
| `sort` | 排序 | 按数字、字段、月份、人类可读大小排序 |
| `uniq` | 处理相邻重复行 | 去重、统计重复次数 |
| `sed` | 流式编辑文本 | 替换、删除、插入、打印指定行 |
| `awk` | 按行按列处理文本 | 提取字段、条件过滤、分组统计 |
| `tr` | 转换或删除字符 | 大小写转换、压缩空格、删除字符 |
| `xargs` | 把输入转换为命令参数 | 批量处理文件、组合命令 |

## 3. cut：按列截取

`cut` 适合处理分隔符明确、结构简单的文本。
它不能很好处理连续空格或复杂引号场景，复杂场景优先用 `awk`。

### 3.1 按分隔符提取字段

```bash
# 提取 CSV 第 2 列 name
cut -d ',' -f 2 users.csv

# 提取第 2 到第 4 列
cut -d ',' -f 2-4 users.csv

# 提取第 1 列和第 3 列
cut -d ',' -f 1,3 users.csv

# 提取 /etc/passwd 中的用户名和 shell
cut -d ':' -f 1,7 /etc/passwd
```

| 选项 | 说明 |
| ---- | ---- |
| `-d` | 指定字段分隔符，默认是 Tab |
| `-f` | 指定字段编号，从 1 开始 |
| `-c` | 按字符位置截取 |
| `--complement` | 反选字段 |

### 3.2 按字符位置截取

```bash
# 截取每行前 10 个字符
cut -c 1-10 access.log

# 截取第 1、3、5 个字符
cut -c 1,3,5 users.csv
```

## 4. wc：统计行数与字符数

`wc` 常用于统计命令输出数量。管线中最常见的是 `wc -l`。

```bash
# 同时显示行数、单词数、字节数
wc access.log

# 只统计行数
wc -l access.log

# 统计匹配 500 的日志行数
grep ' 500 ' access.log | wc -l

# 统计当前目录下 Markdown 文件数量
find . -name '*.md' | wc -l
```

| 选项 | 说明 |
| ---- | ---- |
| `-l` | 行数 |
| `-w` | 单词数 |
| `-c` | 字节数 |
| `-m` | 字符数 |
| `-L` | 最长行长度 |

> **注意**：`wc -c` 统计字节，`wc -m` 统计字符。
> 中文文本在 UTF-8 下一个字符通常占多个字节。

## 5. sort 与 uniq：排序、去重、计数

`uniq` 只处理相邻重复行，所以通常先 `sort` 再 `uniq`。

### 5.1 sort 常用方式

```bash
# 字典序排序
sort users.csv

# 数字排序
cut -d ',' -f 4 users.csv | tail -n +2 | sort -n

# 数字倒序
cut -d ',' -f 4 users.csv | tail -n +2 | sort -nr

# 按 CSV 第 4 列数字倒序排序，保留表头
head -n 1 users.csv
tail -n +2 users.csv | sort -t ',' -k 4,4nr

# 按人类可读大小排序，例如 10K、2M、1G
du -sh * | sort -hr
```

| 选项 | 说明 |
| ---- | ---- |
| `-n` | 按数字排序 |
| `-r` | 倒序 |
| `-h` | 按人类可读大小排序 |
| `-u` | 排序后去重 |
| `-t` | 指定字段分隔符 |
| `-k` | 指定排序字段 |

### 5.2 uniq 统计重复次数

```bash
# 统计每个 IP 的访问次数
awk '{print $1}' access.log | sort | uniq -c

# 按访问次数倒序
awk '{print $1}' access.log | sort | uniq -c | sort -nr

# 只显示重复出现过的 IP
awk '{print $1}' access.log | sort | uniq -d
```

| 选项 | 说明 |
| ---- | ---- |
| `-c` | 在每行前显示重复次数 |
| `-d` | 只显示重复行 |
| `-u` | 只显示唯一行 |
| `-i` | 忽略大小写 |

## 6. sed：流式编辑文本

`sed` 逐行读取文本并执行编辑命令，适合做**替换、删除、打印**指定行等操作。

### 6.1 替换文本

```bash
# 每行只替换第一个 user 为 member
sed 's/user/member/' users.csv

# 每行替换所有 user 为 member
sed 's/user/member/g' users.csv

# 使用其他分隔符，避免路径中的 / 需要转义
echo '/api/users' | sed 's#/api#/v1/api#'

# 只替换第 2 到第 4 行
sed '2,4s/user/member/g' users.csv
```

### 6.2 删除与打印行

```bash
# 删除第一行表头
sed '1d' users.csv

# 删除空行
sed '/^$/d' file.txt

# 只打印第 2 到第 4 行
sed -n '2,4p' users.csv

# 打印包含 500 的日志行
sed -n '/ 500 /p' access.log
```

### 6.3 原地修改文件

```bash
# GNU sed：直接修改文件
sed -i 's/guest/visitor/g' users.csv

# macOS BSD sed：需要提供备份后缀，空字符串表示不保留备份
sed -i '' 's/guest/visitor/g' users.csv

# 保留 .bak 备份文件
sed -i.bak 's/guest/visitor/g' users.csv
```

> **注意**：`sed -i` 在 GNU/Linux 与 macOS 上行为不同。
> 写脚本时如果要兼容 macOS，建议显式测试。

## 7. awk：按行按列处理

`awk` 把输入拆成记录和字段。默认一行是一条记录，空白字符分隔字段。
`$1` 表示第一列，`$0` 表示整行。

### 7.1 基础字段提取

```bash
# 打印访问日志中的 IP、方法、路径、状态码
awk '{print $1, $6, $7, $9}' access.log

# 指定 CSV 分隔符，打印 name 和 score
awk -F ',' '{print $2, $4}' users.csv

# 跳过表头
awk -F ',' 'NR > 1 {print $2, $4}' users.csv
```

| 内置变量 | 说明 |
| -------- | ---- |
| `$0` | 当前整行 |
| `$1`、`$2` | 第 1 列、第 2 列 |
| `NR` | 已处理的总行号 |
| `NF` | 当前行字段数量 |
| `FS` | 输入字段分隔符 |
| `OFS` | 输出字段分隔符 |

### 7.2 条件过滤

```bash
# 找出分数大于等于 80 的用户
awk -F ',' 'NR > 1 && $4 >= 80 {print $2, $4}' users.csv

# 找出 HTTP 500 日志
awk '$9 == 500 {print $1, $7, $9}' access.log

# 找出 GET 请求
awk '$6 ~ /GET/ {print $1, $7}' access.log
```

### 7.3 聚合统计

```bash
# 统计每个状态码出现次数
awk '{count[$9]++} END {for (code in count) print code, count[code]}' access.log

# 统计总响应字节数
awk '{sum += $10} END {print sum}' access.log

# 计算平均分
awk -F ',' 'NR > 1 {sum += $4; n++} END {print sum / n}' users.csv
```

### 7.4 BEGIN 与 END

```bash
# 输出表头、内容、汇总
awk -F ',' '
BEGIN {print "name score"}
NR > 1 {print $2, $4; sum += $4; n++}
END {print "avg", sum / n}
' users.csv
```

`BEGIN` 在读取输入前执行，适合初始化变量或打印表头；
`END` 在读取结束后执行，适合输出统计结果。

## 8. tr：转换与删除字符

`tr` 按字符进行转换，常用于大小写转换、删除字符、压缩重复字符。

```bash
# 小写转大写
echo 'hello linux' | tr 'a-z' 'A-Z'

# 删除数字
echo 'user123' | tr -d '0-9'

# 把连续空格压缩为一个空格
echo 'a    b      c' | tr -s ' '

# 把逗号转换为换行
echo 'java,linux,docker' | tr ',' '\n'
```

| 选项 | 说明 |
| ---- | ---- |
| `-d` | 删除指定字符 |
| `-s` | 压缩连续重复字符 |
| `-c` | 取补集 |

## 9. xargs：把输入转换为参数

`xargs` 把标准输入转换为命令行参数，适合把查找结果交给另一个命令处理。

```bash
# 删除当前目录下所有 .tmp 文件
find . -name '*.tmp' -print0 | xargs -0 rm -f

# 每次传入 2 个参数
printf '%s\n' a b c d | xargs -n 2 echo

# 给每个参数套模板
printf '%s\n' alice bob | xargs -I {} echo 'hello {}'
```

> **注意**：处理文件名时优先使用 `find -print0 | xargs -0`，
> 可以正确处理空格、换行等特殊字符。

## 10. 实战组合

### 10.1 统计访问量最高的 IP

```bash
awk '{print $1}' access.log | sort | uniq -c | sort -nr | head -n 10
```

处理流程：

1. `awk '{print $1}'` 提取 IP
2. `sort` 让相同 IP 相邻
3. `uniq -c` 统计次数
4. `sort -nr` 按次数倒序
5. `head -n 10` 取前 10

### 10.2 统计接口访问次数

```bash
awk '{print $7}' access.log | sort | uniq -c | sort -nr
```

### 10.3 统计错误状态码

```bash
awk '$9 >= 400 {count[$9]++} END {for (code in count) print code, count[code]}' access.log
```

### 10.4 批量替换配置文件

```bash
# 把 conf 目录下所有 .conf 文件中的 old.example.com 替换为 new.example.com
find conf -name '*.conf' -print0 | xargs -0 sed -i.bak 's/old\.example\.com/new.example.com/g'
```

### 10.5 提取 CSV 中高分用户

```bash
awk -F ',' 'NR == 1 || $4 >= 80 {print}' users.csv
```

## 11. 选择建议

| 需求 | 推荐命令 |
| ---- | -------- |
| 提取固定分隔符字段 | `cut` |
| 提取并判断字段 | `awk` |
| 复杂分组、求和、平均值 | `awk` |
| 简单替换、删除行 | `sed` |
| 统计行数或结果数量 | `wc -l` |
| 排名、Top N | `sort` + `head` |
| 去重、计数 | `sort` + `uniq -c` |
| 字符级转换 | `tr` |
| 把结果传给另一个命令 | `xargs` |

## 12. 常见坑

| 问题 | 原因 | 解决方式 |
| ---- | ---- | -------- |
| `uniq` 没有去掉所有重复行 | `uniq` 只处理相邻重复行 | 先 `sort` 再 `uniq` |
| `cut -d ' ' -f 2` 结果不稳定 | 多个连续空格会产生空字段 | 使用 `awk '{print $2}'` |
| `sed -i` 在 macOS 报错 | BSD sed 需要备份后缀参数 | 使用 `sed -i '' 's/a/b/g' file` |
| 文件名含空格时 `xargs` 处理失败 | 默认按空白拆分参数 | 使用 `find -print0 \| xargs -0` |
| 中文字符统计不符合预期 | 字节数与字符数不同 | 区分 `wc -c` 与 `wc -m` |

## 13. 参考

- [[shell-io-redirection|Shell IO 重定向与管线命令]]
- [GNU sed manual](https://www.gnu.org/software/sed/manual/sed.html)
- [GNU awk manual](https://www.gnu.org/software/gawk/manual/gawk.html)
- [GNU Coreutils manual](https://www.gnu.org/software/coreutils/manual/coreutils.html)
