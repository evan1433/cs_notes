---
title: Bash 基础
description: Linux Bash Shell 的基本用法，包括变量、引号、数组、脚本参数、条件判断、循环和函数
tags:
  - linux
  - bash
  - shell
---

# Bash 基础

参考：《鸟哥的 Linux 私房菜》

## 1. Shell 与 Bash

查看系统支持的 Shell：

```bash
cat /etc/shells
```

查看当前使用的 Shell：

```bash
echo $SHELL
```

脚本声明（Shebang）：

```bash
#!/bin/bash
```

## 2. 变量

### 2.1 基本赋值

```bash
x=1
y="this is a string"
echo $x
echo $y
```

```bash
[dmtsai@study ~]$ name=VBird
[dmtsai@study ~]$ echo $name
VBird
```

> **注意**：赋值时等号两边**不能有空格**。

### 2.2 引号区别

```bash
# **双引号会"解析"变量，而单引号会把所有内容当作"纯文本"**
# 双引号
[dmtsai@study ~]$ myname="$name its me"
[dmtsai@study ~]$ echo $myname
VBird its me

# 单引号
[dmtsai@study ~]$ myname='$name its me'
[dmtsai@study ~]$ echo $myname
$name its me
```

### 2.3 数组

```bash
arr=(1 2 3 4)
echo ${arr[@]}
echo ${arr[0]}

files=$(ls)
echo ${files[@]}
```

### 2.4 环境变量

```bash
export MY_ENV=1000
echo $MY_ENV
```

### 2.5 变量默认值

```bash
# 默认值 但不赋值
echo ${var1:-"hello1"}
# 默认值 且赋值
echo ${var2:="hello2"}
```

### 2.6 删除变量

```bash
unset varname
```

## 3. 脚本参数

```bash
# 脚本名称
echo $0
# 脚本第一个参数
echo $1
echo $2
echo $3
# 脚本参数个数
echo $#
```

## 4. 命令别名与历史命令

```bash
# 设置别名
alias ll='ls -l'

# 取消别名
unalias ll
```

## 5. 条件判断

```bash
a=1
b=2
if [ $a -gt $b ]; then
  echo "a 更大"
else
  echo "a 更小"
fi
```

## 6. 循环

### for 循环

```bash
for num in 1 2 3 4 5; do
  echo "this is : $num"
done

for file in $(ls); do
  echo $file
done
```

### while 循环

```bash
num=1
while (($num < 5)); do
  echo $num
  let "num++"
done
```

## 7. 函数

```bash
function bidaxiao(){
  if [ $1 -gt $2 ]; then
    echo "big"
  else
    echo "small"
  fi
}

bidaxiao 1 3
```

## 8. Shell 变量功能

```bash
echo $PATH
echo ${PATH}
```

## 9. 数据流重定向与管线

详见 [[shell-io-redirection|Shell IO 重定向与管线命令]]

## 10. 相关笔记

- [[shell-quoting-and-expansion|Shell 引号、变量展开与文件名处理]] — 引号与展开的进阶用法、批量处理文件的安全写法与踩坑清单
- [[find-command|find 命令详解]] — 与 `-exec`、`-print0` 配合的批量操作
- [[text-processing-commands|Linux 文本处理命令]] — sed、awk、xargs 实战
