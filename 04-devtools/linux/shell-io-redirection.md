---
title: Shell IO 重定向与管线命令
description: Linux Shell 的数据流重定向（stdin/stdout/stderr）、命令执行判断（&&/||）和管线命令（grep/cut/sort/wc/uniq/tee）
tags:
  - linux
  - bash
  - shell
---

# Shell IO 重定向与管线命令

参考：《鸟哥的 Linux 私房菜》第十章

## 1. 数据流重定向

### 1.1 三种数据流

| 数据流 | 代号 | 说明 |
|--------|------|------|
| **stdin** | 0 | 标准输入（键盘输入） |
| **stdout** | 1 | 标准输出（终端屏幕） |
| **stderr** | 2 | 标准错误输出（终端屏幕） |

### 1.2 stdout（标准输出）

```bash
# 覆盖（1 可以省略）
ls / 1> ~/rootfile
ls / > ~/rootfile

# 追加
ls / 1>> ~/rootfile
ls / >> ~/rootfile
```

### 1.3 stderr（标准错误输出）

```bash
# 覆盖
cat ~/files 2> error.log

# 追加
cat ~/files 2>> error.log
```

### 1.4 stdout 和 stderr 分开输出

```bash
# 分别输出到不同文件
find /home -name .bashrc > list_right 2> list_error
```

### 1.5 stdout 和 stderr 输出到同一个文件

```bash
# 方法一
find /home -name .bashrc > list 2>&1

# 方法二（更简洁）
find /home -name .bashrc &> list
```

### 1.6 /dev/null 黑洞

```bash
# 丢弃所有输出
command > /dev/null 2>&1

# 仅丢弃错误输出
command 2> /dev/null
```

### 1.7 stdin（标准输入）

```bash
# 从文件读取输入 <
cat > catfile < ~/.bashrc

# 从脚本中的一段文本读入标准输入 Here Document
cat > catfile << "eof"
第一行
第二行
eof
```

## 2. 命令执行判断

### 2.1 回传值 `$?`

`$?` 表示上一条指令的返回值，执行成功为 0，失败为非 0。

### 2.2 `&&`（AND）

```bash
cmd1 && cmd2
```

1. 若 cmd1 执行成功（`$?=0`），则执行 cmd2
2. 若 cmd1 执行失败（`$?≠0`），则 cmd2 不执行

### 2.3 `||`（OR）

```bash
cmd1 || cmd2
```

1. 若 cmd1 执行成功（`$?=0`），则 cmd2 不执行
2. 若 cmd1 执行失败（`$?≠0`），则执行 cmd2

### 2.4 组合示例

```bash
# 同步后再关机
sync; sync; shutdown -h now

# 命令不存在时安装
command || sudo apt install command
```

## 3. 管线命令

> **注意**：
> - 管线命令 `|` 仅能处理前面一个指令的 **standard output**，对 **standard error** 没有直接处理能力
> - 管线命令后面的命令必须能够接受 **standard input**

### 3.1 grep - 搜索匹配行

```bash
# 基本用法
grep "pattern" filename

# 常用选项
grep -i "pattern" filename    # 忽略大小写
grep -v "pattern" filename    # 反向匹配（显示不匹配的行）
grep -n "pattern" filename    # 显示行号
grep -r "pattern" dir/        # 递归搜索目录
grep -C 3 "pattern" filename  # 显示匹配行前后各 3 行（context）

# 管线组合
cat file.txt | grep "ERROR"
ps aux | grep nginx
```

### 3.2 cut - 提取列

```bash
# 按分隔符提取
echo "hello:world:foo" | cut -d ':' -f 2
# 输出：world

# 提取多个字段
echo "a:b:c:d" | cut -d ':' -f 1,3
# 输出：a:c

# 按字符范围提取
echo "hello" | cut -c 1-3
# 输出：hel
```

### 3.3 sort - 排序

```bash
# 基本排序
sort file.txt

# 按数字排序
sort -n file.txt

# 反向排序
sort -r file.txt

# 按指定列排序
sort -t ':' -k 3 /etc/passwd

# 去重排序
sort -u file.txt
```

### 3.4 wc - 统计

```bash
# 统计行数、单词数、字符数
wc file.txt

# 只统计行数
wc -l file.txt

# 只统计单词数
wc -w file.txt

# 只统计字符数
wc -c file.txt
```

### 3.5 uniq - 去重

```bash
# 去除相邻重复行（通常先排序）
sort file.txt | uniq

# 统计重复次数
sort file.txt | uniq -c

# 只显示重复的行
sort file.txt | uniq -d

# 只显示不重复的行
sort file.txt | uniq -u
```

### 3.6 tee - 双向输出

```bash
# 同时输出到屏幕和文件
ls -l | tee filelist.txt

# 追加模式
ls -l | tee -a filelist.txt

# 提升权限并保存
echo "hello" | sudo tee /root/test.txt
```

> `tee` 会将 stdin 的数据同时输出到 stdout 和指定的文件中。

### 3.7 管线组合示例

```bash
# 统计文件中出现最多的 10 个单词
cat file.txt | tr -s ' ' '\n' | sort | uniq -c | sort -rn | head -10

# 查找进程并统计数量
ps aux | grep java | grep -v grep | wc -l

# 查找大文件并排序
find / -type f -size +100M 2>/dev/null | tee bigfiles.log | sort
```
