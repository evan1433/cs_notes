---
title: C 语言核心语法与指针实战
description: 从类型、输入输出、运算符优先级到指针、字符串、结构体与函数指针，用可运行示例打通 C 语言的关键概念。
tags:
  - c
  - backend
  - fundamentals
  - pointers
date: 2026-11-22
aliases:
  - C学习笔记
  - C 语言学习笔记
  - c-language-notes
---

# C 语言核心语法与指针实战

## 概述

C 语言只提供很少的语言机制：基本类型、指针、数组、结构体、函数。
它之所以值得系统学习，是因为内存布局、栈与堆、字符串表示这些"底层事实"在 C 里是可见的、可控的，
而这些事实在其他语言里往往被隐藏起来——遇到性能问题、跨语言调用（FFI）或崩溃排查时，
能否读懂它们决定了你是在猜测还是在推理。

本文按"类型 → 输入输出 → 运算符 → 控制流 → 函数 → 指针 → 字符串 → 结构体与联合 → 复杂声明"的顺序展开，
每个概念都配有可直接编译运行的示例。与原始速记不同的说法会明确标注，方便对照旧笔记复习。
相关底层知识可参阅 [[01-cs-fundamentals/operating-systems|操作系统]] 与 [[01-cs-fundamentals/data-structures|数据结构]]。

## 编译环境与语言标准

C 目前的最新标准是 **C23**（正式名称 ISO/IEC 9899:2024，2024 年 10 月发布），
它新增了 `nullptr`、`constexpr`、`auto`、`typeof`、`_BitInt(N)`、`[[属性]]` 等特性，
并把 `bool`、`true`、`false`、`static_assert` 提升为关键字。
编译器支持情况：GCC 15 起默认就是 C23，Clang 18 起支持 `-std=c23`（更早的版本写作 `-std=c2x`）。
MSVC 支持仍不完整，嵌入式工具链通常更滞后。

实践中建议显式指定标准并打开告警，而不是依赖编译器默认值：

```bash
# 编译并打开常用告警；-pedantic-errors 让非标准扩展直接报错
cc -std=c23 -Wall -Wextra -pedantic-errors hello.c -o hello

# 确认本机编译器版本
cc --version
```

第一个程序：

```c
#include <stdio.h>  /* printf 的声明在这个头文件里 */

int main(void) {
    printf("你好，C！\n");
    return 0;  /* 返回 0 表示正常退出；main 是唯一可以省略 return 的函数 */
}
```

`main` 的标准形式有两种：`int main(void)` 表示不接受参数，`int main(int argc, char *argv[])` 接收命令行参数。
写 `int main()` 在 C23 中含义与 `int main(void)` 相同，但在 C17 及更早的标准里它表示"参数未指定"，
所以跨标准代码建议显式写 `void`。

## 基本类型与数值表示

### 类型、大小与转换说明

`char` 固定占 1 字节，其余类型的大小由实现决定（标准只保证 `char <= short <= int <= long <= long long`）。
下表是 64 位 Linux / macOS（LP64 模型）的典型值，Windows 采用 LLP64，`long` 只有 4 字节：

| 类型 | 典型大小 | 转换说明 | 说明 |
|------|----------|----------|------|
| `char` | 1 字节 | `%c` | 存单个字符，本质是小整数 |
| `short` | 2 字节 | `%hd` | 很少使用 |
| `int` | 4 字节 | `%d` / `%i` | 默认整型 |
| `unsigned int` | 4 字节 | `%u` | 无符号，溢出回绕 |
| `long` | 8 字节（LP64） | `%ld` | Windows 上是 4 字节 |
| `long long` | 8 字节 | `%lld` | 至少 64 位 |
| `size_t` | 8 字节 | `%zu` | `sizeof`、`strlen` 的返回类型，无符号 |
| `float` | 4 字节 | `%f` | 传入 `printf` 时自动提升为 `double` |
| `double` | 8 字节 | `%f` / `%lf` | `scanf` 读 `double` 必须用 `%lf` |
| `long double` | 16 字节 | `%Lf` | 精度最高，平台差异大 |
| 指针 | 8 字节 | `%p` | 打印前应转成 `void *` |

用 `sizeof` 确认而不是背数字，是更可靠的习惯：

```c
#include <stdio.h>

int main(void) {
    printf("char=%zu short=%zu int=%zu long=%zu long long=%zu\n",
           sizeof(char), sizeof(short), sizeof(int), sizeof(long), sizeof(long long));
    printf("float=%zu double=%zu pointer=%zu\n",
           sizeof(float), sizeof(double), sizeof(int *));
    return 0;
}
```

### 整数溢出与无符号回绕

有符号整数溢出是**未定义行为**（undefined behavior），编译器可以假设它不会发生并据此优化，
所以依赖 `x + 1 < x` 这类表达式做溢出检测并不可靠。无符号整数的溢出则是明确定义的"模 2^n 回绕"：

```c
#include <limits.h>
#include <stdio.h>

int main(void) {
    unsigned int u = UINT_MAX;
    printf("%u\n", u + 1);   /* 0：无符号回绕是标准定义好的行为 */

    int big = INT_MAX;
    if (big == INT_MAX) {    /* 先比较再运算，避免触发未定义行为 */
        printf("已经到上限，不能再加\n");
    }
    return 0;
}
```

### 字符与字符串字面量

`char c; c = 'a';` 正确，`c = a;` 和 `c = "a";` 都是错的：
`a` 是未声明的标识符，`"a"` 是 `const char[2]` 类型的字符串字面量（含结尾 `'\0'`），
不能赋给单个 `char`。单引号是字符常量，双引号是字符串字面量，这是 C 里最容易写错的符号。

```c
#include <stdio.h>

int main(void) {
    char letter = 'a';        /* 字符常量，值是 97 */
    const char *word = "a";   /* 字符串，两个字节：'a' 和 '\0' */

    printf("%c %d\n", letter, letter);          /* a 97 */
    printf("%s 字面量大小=%zu\n", word, sizeof("a"));  /* a 字面量大小=2 */
    return 0;
}
```

### 常量：`#define` 与 `const`

| 方式 | 示例 | 类型检查 | 作用域 | 建议 |
|------|------|----------|--------|------|
| 宏 | `#define PI 3.1415` | 无，纯文本替换 | 从定义处到文件末尾 | 宏名全大写，仅用于条件编译或需要字符串化的场合 |
| `const` 变量 | `const double pi = 3.1415;` | 有 | 遵守块作用域 | 现代 C 首选，可被调试器看到 |

```c
#include <stdio.h>

#define PI 3.1415              /* 大写是约定，提醒读者这是宏而非变量 */
#define SQUARE(x) ((x) * (x))  /* 宏参数必须加括号，否则 SQUARE(a+1) 会算错 */

int main(void) {
    const double radius = 2.0;
    printf("%.4f\n", PI * radius * radius);
    printf("%d\n", SQUARE(2 + 3));  /* 25；若写成 (x*x) 则变成 2+3*2+3 = 11 */
    return 0;
}
```

## 格式化输入输出

### 转换说明速查

| 说明 | 含义 | 示例输出 |
|------|------|----------|
| `%d` | 十进制有符号整数 | `42` |
| `%o` | 八进制（无前缀） | `52` |
| `%x` / `%X` | 十六进制（小写/大写） | `2a` / `2A` |
| `%#x` | 带 `0x` 前缀的十六进制 | `0x2a` |
| `%f` | 浮点数，默认 6 位小数 | `3.141593` |
| `%.2f` | 保留 2 位小数 | `3.14` |
| `%10.2f` | 总宽 10、保留 2 位小数、右对齐（`␣` 表示空格填充） | `␣␣␣␣␣␣3.14` |
| `%-10.2f` | 同上但左对齐 | `3.14␣␣␣␣␣␣` |
| `%05d` | 宽 5，左侧补 0 | `00042` |
| `%c` | 单个字符 | `a` |
| `%s` | 字符串（遇 `'\0'` 结束） | `hello` |
| `%p` | 指针地址（实现定义格式） | `0x7ffd...` |
| `%zu` | `size_t` | `5` |
| `%%` | 输出一个百分号 | `%` |

### `printf` 的返回值

`printf` 返回**实际写入流的字节数**，出错时返回负值。这个返回值常被忽略，
但它能用来判断输出是否成功：

```c
#include <stdio.h>

int main(void) {
    int written = printf("abc\n");
    printf("上一行输出了 %d 个字节\n", written);   /* 4，含换行符 */
    return 0;
}
```

用 `%n` 也能获取已输出字符数，但它存在安全隐患（格式化字符串攻击的利用点），现代代码不建议使用。

### `scanf` 的返回值

`scanf` 返回**成功赋值的项数**，而不是读到的字符数。若在读到任何项之前就遇到输入失败
（例如格式是 `%d` 而用户输入了 `abc`），返回 `0`；遇到文件结尾则返回 `EOF`（通常是 `-1`）。
因此正确写法是判断返回值，而不是假设变量一定被填上：

```c
#include <stdio.h>

int main(void) {
    int age;
    printf("请输入年龄: ");

    if (scanf("%d", &age) != 1) {   /* 返回 1 表示成功读入一项 */
        fprintf(stderr, "输入不是整数\n");
        return 1;
    }
    printf("年龄 %d\n", age);
    return 0;
}
```

`scanf("%d", &a)` 里的 `&a` 是取地址：`scanf` 需要知道"往哪里写"，所以传的是地址而不是值。
读字符数组时例外，数组名本身已经是地址：`scanf("%19s", name)` 不加 `&`，
并且**一定要限宽**，否则输入超长就会越界写。

### `getchar` 与输入缓冲区

`getchar` 的行为常被误解：它不是"按键就返回一个字符"，而是从 **stdin 缓冲区**读一个字符。
程序调用 `getchar` 时若缓冲区为空，就等待用户输入；用户输入的字符先进入键盘缓冲区，
直到按下回车（回车符 `'\n'` 也进缓冲区）才开始被 `getchar` 逐个读走。
如果用户一次输入了多个字符，其余字符会留在缓冲区里等后续 `getchar` 读取——
后续调用**不会**再等待按键，直到缓冲区被读空。

`getchar` 的返回值是 `int`：正常时是读到的字符（按 `unsigned char` 解释），文件结尾返回 `EOF`（`-1`）。
返回 `int` 而不是 `char`，正是为了让 `EOF` 与任何合法字符值都能区分——把返回值存进 `char`，
在 `char` 为有符号的平台上就永远检测不到 `EOF`。在 glibc 中它还是以宏实现的
（`#define getchar() getc(stdin)`），所以不要写 `&getchar` 这类取函数地址的代码。

```c
#include <stdio.h>

int main(void) {
    int ch;          /* 必须用 int，才能容纳 EOF */
    int lines = 0;
    int others = 0;

    printf("输入若干字符，Ctrl-D 结束：\n");
    while ((ch = getchar()) != EOF) {
        if (ch == '\n') {
            lines++;
        } else {
            others++;
        }
    }
    printf("换行 %d 个，其他字符 %d 个\n", lines, others);
    return 0;
}
```

由此引出一个经典 bug：先用 `scanf` 读数字，再调用 `getchar` 或 `fgets` 读字符时，
会先读到上一次输入留下的换行符。解决办法是在两者之间"吃掉"残留字符：

```c
#include <stdio.h>

int main(void) {
    int age;
    int grade;

    printf("年龄: ");
    if (scanf("%d", &age) != 1) {
        return 1;
    }
    /* scanf 只消费了数字，'\n' 还在缓冲区，必须手动丢弃到行尾 */
    while (getchar() != '\n') {
        ;
    }

    printf("等级(A/B/C): ");
    grade = getchar();
    printf("年龄 %d，等级 %c\n", age, (char)grade);
    return 0;
}
```

### 字符串输出的几种方式

| 函数 | 头文件 | 自动换行 | 是否限宽 | 适用场景 |
|------|--------|----------|----------|----------|
| `printf` | `stdio.h` | 否 | 可用 `%.*s` 限宽 | 需要格式化任意类型 |
| `puts` | `stdio.h` | **是** | 否 | 只输出字符串，且要换行 |
| `fputs` | `stdio.h` | 否 | 否 | 输出到指定流（含文件） |
| `putchar` | `stdio.h` | 否 | — | 输出单个字符 |
| `gets` | 已从标准移除 | — | **不检查边界** | 禁用：C11 起已删除 |
| `fgets` | `stdio.h` | 否（保留输入中的 `\n`） | **是** | 推荐的安全读行方式 |

```c
#include <stdio.h>

int main(void) {
    char line[16];

    printf("输入一行文字：");
    if (fgets(line, (int)sizeof line, stdin) == NULL) {
        return 1;   /* 读到 EOF 或出错 */
    }
    /* fgets 会把换行符一起读进来，通常需要自己去掉 */
    for (int i = 0; line[i] != '\0'; i++) {
        if (line[i] == '\n') {
            line[i] = '\0';
            break;
        }
    }
    puts(line);   /* puts 自动补换行 */
    return 0;
}
```

## 运算符与优先级

### 优先级总表（由高到低）

| 优先级 | 运算符 | 结合性 | 说明 |
|--------|--------|--------|------|
| 1 | `()` `[]` `->` `.` | 左→右 | 后缀表达式，最高 |
| 2 | `!` `~` `++` `--` 正负号 `*`(解引用) `&`(取地址) `sizeof` `(类型)` | 右→左 | 一元运算符 |
| 3 | `*` `/` `%` | 左→右 | 乘、除、取模 |
| 4 | `+` `-` | 左→右 | 加减 |
| 5 | `<<` `>>` | 左→右 | 移位 |
| 6 | `<` `<=` `>` `>=` | 左→右 | 关系 |
| 7 | `==` `!=` | 左→右 | 相等 |
| 8 | `&` | 左→右 | 按位与 |
| 9 | `^` | 左→右 | 按位异或 |
| 10 | `\|` | 左→右 | 按位或 |
| 11 | `&&` | 左→右 | 逻辑与 |
| 12 | `\|\|` | 左→右 | 逻辑或 |
| 13 | `?:` | 右→左 | 条件运算符 |
| 14 | `=` `+=` `-=` 等 | 右→左 | 赋值 |
| 15 | `,` | 左→右 | 逗号，最低 |

几条值得单独记住的结论：

- `!` 的优先级**高于乘法**，与 `++` 相同，只低于圆括号，所以 `!a * b` 等价于 `(!a) * b`。
- `&&` 高于 `||`，但两者都**低于**关系运算符、**高于**赋值运算符，所以 `a < b && c < d` 无需括号。
- 关系运算符优先级**低于**算术运算符、**高于**赋值运算符，所以 `x = a > b ? a : b` 不必给 `a > b` 加括号。
- `*` 与 `++` 优先级相同，结合方向**从右向左**，因此 `*p++` 等价于 `*(p++)`。
- 不确定就加括号：优先级表是用来读别人代码的，不是用来省括号的。

### 自增自减

`++`/`--` 只作用于一个变量（可以是指针，不能是 `(a+b)++` 这样的表达式）。
前置形式先自增再取值，后置形式先取值再自增：

```c
#include <stdio.h>

int main(void) {
    int y = 2;
    int n = 3;

    int x = (y + n++) * 6;   /* 先取 n 的值 3 参与运算，再让 n 自增 */
    printf("x=%d y=%d n=%d\n", x, y, n);   /* x=30 y=2 n=4 */
    return 0;
}
```

在同一个表达式里对同一变量多次自增（如 `i = i++ + 1`）是未定义行为，不要写这样的代码。

### 条件运算符

`expression1 ? expression2 : expression3` 与 `if/else` 语义相同，但它是**表达式**，可以直接嵌在赋值里：

```c
#include <stdio.h>

int main(void) {
    int score = 78;
    /* 比 if/else 更紧凑，适合"二选一取值" */
    const char *result = score >= 60 ? "及格" : "不及格";
    printf("%s\n", result);
    return 0;
}
```

注意两个分支的类型会做统一转换：`cond ? 1 : 2.0` 的结果是 `double`，
而 `cond ? -1 : 0u` 会把 `-1` 转成无符号，得到一个大正数。

## 流程控制

```c
#include <stdio.h>

int main(void) {
    int total = 0;

    for (int i = 0; i < 10; i++) {
        if (i == 3) {
            continue;   /* 跳过本次循环剩余部分，i=3 不累加 */
        }
        if (i == 7) {
            break;      /* 直接跳出整个循环 */
        }
        total += i;     /* 0+1+2+4+5+6 = 18 */
    }
    printf("total=%d\n", total);

    int n = 0;
    do {
        n++;
    } while (n < 3);    /* 循环体至少执行一次，即使条件一开始为假 */
    printf("n=%d\n", n);
    return 0;
}
```

`switch` 的匹配项必须是整型常量表达式（`case 常量:`），不能是范围或浮点数。
C 的 `switch` **不会自动跳出**，忘记 `break` 会"贯穿"到下一个 `case`——
有时这是有意为之，可用 C23 的 `[[fallthrough]]` 明确表达意图：

```c
#include <stdio.h>

int main(void) {
    int level = 2;
    switch (level) {
        case 1:
            printf("青铜\n");
            break;
        case 2:
            printf("白银\n");
            [[fallthrough]];   /* 明确表示"故意贯穿"，消除编译告警 */
        case 3:
            printf("黄金\n");
            break;
        default:
            printf("未知等级\n");
            break;
    }
    return 0;
}
```

## 函数

### 声明、定义与调用

函数声明（原型）以**分号**结尾，函数定义带函数体、不以分号结尾。漏掉分号是最常见的编译错误之一。

```c
#include <stdio.h>

/* 函数声明（原型）：告诉编译器参数与返回类型，参数名可以省略 */
double average(const int scores[], int count);

int main(void) {
    int scores[] = {80, 95, 72};
    printf("%.2f\n", average(scores, 3));   /* 调用：实参被赋值给形参 */
    return 0;
}

/* 函数定义 */
double average(const int scores[], int count) {
    if (count <= 0) {
        return 0.0;   /* 边界条件必须自己检查，数组参数不携带长度 */
    }
    long sum = 0;
    for (int i = 0; i < count; i++) {
        sum += scores[i];
    }
    return (double)sum / count;
}
```

术语对照：

| 概念 | 出现位置 | 说明 |
|------|----------|------|
| 形参（parameter） | 函数声明/定义 | 函数私有的局部变量，可以省略变量名，只保留类型 |
| 实参（argument） | 函数调用 | 可以是常量、变量或表达式，其值被复制给形参 |
| 主调函数 | 调用方 | 提供实参 |
| 被调函数 | 被调用方 | 接收形参 |

### 参数传递只有值传递

C 没有引用传递。传指针时"看起来能改变外部变量"，本质上仍是把指针的值（地址）复制进形参，
只是通过该地址能访问到调用方的对象：

```c
#include <stdio.h>

void cannot_swap(int a, int b) {
    int t = a;
    a = b;
    b = t;      /* 只交换了副本，调用方不受影响 */
}

void can_swap(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;     /* 通过地址修改调用方的对象 */
}

int main(void) {
    int x = 1;
    int y = 2;
    cannot_swap(x, y);
    printf("cannot_swap 之后: %d %d\n", x, y);   /* 1 2 */
    can_swap(&x, &y);
    printf("can_swap 之后: %d %d\n", x, y);      /* 2 1 */
    return 0;
}
```

### 数组参数会退化为指针

形参写成 `int arr[]` 或 `int arr[10]` 都会被编译器改写成 `int *arr`，数组长度信息**不会**传进函数，
`sizeof arr` 在函数内部得到的是指针大小。这就是为什么传递数组有两种惯例：

1. 传首元素指针 + 元素个数（最常用）：`void show(const int *data, int n);`
2. 传首尾指针，用指针相减求长度：`void show(const int *begin, const int *end);`

```c
#include <stdio.h>

/* 方式二：首尾指针，end 指向最后一个元素的"下一个位置"（半开区间） */
void show(const int *begin, const int *end) {
    for (const int *p = begin; p != end; p++) {
        printf("%d ", *p);
    }
    printf("\n共 %td 个元素\n", end - begin);   /* 指针相减得到元素个数 */
}

int main(void) {
    int data[] = {3, 1, 4, 1, 5};
    show(data, data + sizeof data / sizeof data[0]);
    return 0;
}
```

## 指针

### 指针是什么

指针是一个**值为内存地址的变量**。理解任何变量都可以用四要素拆解：
类型、名称、地址、值。指针只是把这四要素中的"值"限定成了地址。

```c
#include <stdio.h>

int main(void) {
    int b = 42;
    int *a = &b;      /* & 取地址：a 保存 b 的地址 */

    printf("b 的值=%d，b 的地址=%p\n", b, (void *)&b);
    printf("a 的值=%p，*a=%d\n", (void *)a, *a);   /* * 解引用：取该地址上的内容 */

    *a = 100;         /* 通过指针修改 b */
    printf("b 变成 %d\n", b);
    return 0;
}
```

- `&`（地址运算符）后跟变量名，给出该变量的地址。
- `*`（间接/解引用运算符）后跟指针或地址，给出该地址上存储的内容。
- `*` 在声明里表示"这是指针类型"，在表达式里表示"解引用"，同一个符号两种身份，靠上下文区分。

### 指针运算：步长是 `sizeof(所指类型)`

这是原始速记里最容易记岔的一点。**指针加 1 不是地址加 1 字节，而是前进 `sizeof(*p)` 字节**，
即移动到"下一个同类型元素"。这种设计让指针运算与数组下标天然对齐：

```c
#include <stdio.h>

int main(void) {
    int dates[4] = {10, 20, 30, 40};
    int *p = dates;   /* 数组名退化为首元素地址 */

    printf("sizeof(int)=%zu\n", sizeof(int));
    printf("p   = %p\n", (void *)p);
    printf("p+1 = %p\n", (void *)(p + 1));   /* 比 p 大 4 字节，而不是 1 字节 */

    printf("%d %d\n", *(p + 2), p[2]);       /* 30 30：两种写法完全等价 */
    printf("%d %d\n", *p + 2, *(p + 2));     /* 12 30：*p+2 是 (*p)+2 */
    printf("%td\n", &dates[3] - &dates[0]);  /* 3：指针相减得到元素个数 */
    return 0;
}
```

几条恒等式（`dates` 为 `int` 数组）：

| 写法 | 等价形式 | 含义 |
|------|----------|------|
| `dates + 2` | `&dates[2]` | 地址相同 |
| `*(dates + 2)` | `dates[2]` | 内容相同 |
| `*dates + 2` | `(*dates) + 2` | 先取首元素再加 2，`*` 优先级高于 `+` |
| `*p++` | `*(p++)` | 取当前值，再让 `p` 前进一个元素 |
| `(*p)++` | — | 让 `p` 指向的值加 1，`p` 本身不动 |

`*p++` 是遍历时最常用的写法，因为 `*` 与 `++` 优先级相同且从右向左结合：

```c
#include <stdio.h>

int main(void) {
    int data[] = {1, 2, 3};
    int *p = data;

    printf("%d\n", *p++);   /* 1，随后 p 指向 data[1] */
    printf("%d\n", (*p)++); /* 2，然后 data[1] 变成 3 */
    printf("%d\n", *p);     /* 3 */
    return 0;
}
```

### 指针的九种操作

| 操作 | 示例 | 注意 |
|------|------|------|
| 1. 赋值 | `p = &x;` `p = arr;` | 类型必须兼容，否则需显式转换 |
| 2. 解引用 | `*p` | 只能对有效指针解引用 |
| 3. 取地址 | `p = &arr[i];` | 数组元素同样可被取地址 |
| 4. 与整数相加 | `p + 3` | 前进 `3 * sizeof(*p)` 字节 |
| 5. 递增 | `p++` | 同上，前进一个元素 |
| 6. 与整数相减 | `p - 2` | 回退两个元素 |
| 7. 递减 | `p--` | 回退一个元素 |
| 8. 求差 | `p2 - p1` | 结果为 `ptrdiff_t`，两指针须指向同一数组 |
| 9. 比较 | `p1 < p2` | 同一数组内比较才有意义；与 `NULL` 比较用 `==`/`!=` |

### 未初始化指针与空指针

声明指针不会自动分配目标内存。`int *p;` 之后 `p` 的值是垃圾值，
`*p = 5;` 会写到随机地址，轻则崩溃，重则不报错地破坏其他数据。

```c
#include <stdio.h>

int main(void) {
    int *p = NULL;   /* 初始化为 NULL，让误用至少变成可检测的空指针解引用 */

    if (p == NULL) {
        printf("p 还没有指向任何对象\n");
    }
    /* *p = 5;  解引用空指针会崩溃（段错误），这是"好的"失败方式；
       解引用野指针才是真正危险的，因为它可能悄悄改坏别人的数据。 */
    return 0;
}
```

要进一步使用指针，必须先让它指向有效存储：局部变量（栈）、`malloc` 分配的堆内存，或静态存储。

### `const` 与指针的三种组合

`const` 修饰它左边的东西，若左边没有东西则修饰右边。三种组合含义完全不同：

| 声明 | 谁能变 | 记忆法 |
|------|--------|--------|
| `const int *p` | `p` 可变，`*p` 不可变 | 指向常量的指针（只读视图） |
| `int *const p` | `p` 不可变，`*p` 可变 | 常量指针，必须在声明时初始化 |
| `const int *const p` | 两者都不可变 | 完全只读 |

`const int *a;` 与 `int const *a;` 完全等价。

```c
#include <stdio.h>

int main(void) {
    int value = 1;
    int other = 2;

    const int *p1 = &value;   /* 不能通过 p1 改值，但可以改指向 */
    /* *p1 = 10;  编译错误 */
    p1 = &other;              /* 合法 */

    int *const p2 = &value;   /* 指向固定，值可改 */
    *p2 = 10;                 /* 合法，value 变成 10 */
    /* p2 = &other;  编译错误 */

    const int *const p3 = &value;
    /* *p3 = 1; p3 = &other;  都非法 */

    printf("%d %d\n", *p1, *p3);
    return 0;
}
```

函数参数上的 `const` 是"承诺不修改"的契约：`double average(const int scores[], int n)`
表示函数只读该数组。这只约束函数内部的写法，**并不要求调用方传入常数组**：

```c
#include <stdio.h>

int sum(const int *data, int n) {   /* 承诺：不修改 data 指向的内容 */
    int total = 0;
    for (int i = 0; i < n; i++) {
        total += data[i];
    }
    return total;
}

int main(void) {
    int scores[] = {1, 2, 3};
    printf("%d\n", sum(scores, 3));   /* 传入普通数组完全合法 */
    return 0;
}
```

原则：处理数组时若不修改它，就加 `const`；会修改则不加。这既是文档也是编译期保护。

## 字符串与字符串函数

### 字符数组与字符串的区别

C 没有独立的字符串类型，用**以 `'\0'` 结尾的字符数组**表示字符串。
只有最后一个元素是 `'\0'`（空字符，值为 0）时，它才是字符串；否则只是一个字符数组，
传给 `printf("%s")`、`strlen` 等函数会越界读取直到偶然遇到 0 字节。

```c
#include <stdio.h>
#include <string.h>

int main(void) {
    char greeting[] = "how are you?";    /* 编译器自动补 '\0'，共 13 字节 */
    char letters[] = {'h', 'i'};         /* 只是字符数组，没有 '\0' */

    printf("sizeof=%zu strlen=%zu\n", sizeof greeting, strlen(greeting));  /* 13 12 */
    /* 不要把 letters 当字符串用：strlen(letters) 是未定义行为 */
    printf("letters[0]=%c letters[1]=%c\n", letters[0], letters[1]);
    return 0;
}
```

`sizeof` 是编译期算出的**数组总字节数**，`strlen` 是运行期数到 `'\0'` 为止的**字符个数**。
对指针使用 `sizeof` 得到的是指针大小（8 字节），这是新手最容易踩的坑。

字符串字面量在 C 中是只读的，修改它是未定义行为，所以指针形式要加 `const`：

```c
char editable[] = "example";      /* 拷贝到可写数组，等价于 {'e','x','a','m','p','l','e','\0'} */
const char *readonly = "example"; /* 指向只读区，不能改内容 */
/* readonly[0] = 'E';  未定义行为，通常直接崩溃 */
```

### 常用字符串函数

| 函数 | 原型 | 作用 | 陷阱 |
|------|------|------|------|
| `strlen` | `size_t strlen(const char *s)` | 求长度，不含 `'\0'` | 返回无符号 `size_t`，不要写 `strlen(s) >= 0`（恒真） |
| `strcpy` | `char *strcpy(char *dst, const char *src)` | 复制含 `'\0'` | **不限长**，dst 不够大会溢出 |
| `strncpy` | `char *strncpy(char *dst, const char *src, size_t n)` | 至多复制 n 字节 | n 用尽时**不补 `'\0'`**，需手动终止 |
| `strcat` | `char *strcat(char *dst, const char *src)` | 追加 | **不限长** |
| `strncat` | `char *strncat(char *dst, const char *src, size_t n)` | 追加至多 n 字节并补 `'\0'` | n 是"追加长度"，不是目标缓冲区容量 |
| `strcmp` | `int strcmp(const char *a, const char *b)` | 比较 | 相同返回 0；不同返回两字符 `unsigned char` 差值的**符号** |
| `strncmp` | `int strncmp(const char *a, const char *b, size_t n)` | 只比较前 n 个字符 | 适合比较前缀 |
| `sprintf` | `int sprintf(char *buf, const char *fmt, ...)` | 格式化到字符串 | **不限长**，优先用 `snprintf` |
| `snprintf` | `int snprintf(char *buf, size_t n, const char *fmt, ...)` | 限长格式化 | 返回"本应写入的长度"，可据此判断截断 |

`strcmp` 的返回值不要与 1 或 -1 比较——标准只保证"小于/等于/大于 0"，具体数值由实现决定。
所以原始速记里的"相同则返回 0，不同则返回 ASCII 差值"应理解为：**返回差值的符号**。

```c
#include <stdio.h>
#include <string.h>

int main(void) {
    char name[8];
    const char *source = "how are you?";

    /* 危险写法：strcpy(name, source) 会写 13 字节到 8 字节缓冲区，导致栈溢出 */
    strncpy(name, source, sizeof name - 1);
    name[sizeof name - 1] = '\0';   /* strncpy 在截断时不补 '\0'，必须手动补 */
    printf("name=%s\n", name);

    char message[32];
    int year = 2026;
    int needed = snprintf(message, sizeof message, "C 标准更新于 %d 年", year);
    if (needed < 0) {
        fprintf(stderr, "格式化失败\n");
    } else if ((size_t)needed >= sizeof message) {
        fprintf(stderr, "内容被截断，需要 %d 字节\n", needed);
    }
    printf("%s\n", message);

    if (strcmp("abc", "abc") == 0) {
        printf("两个字符串相同\n");
    }
    if (strncmp("prefix-1", "prefix-2", 7) == 0) {
        printf("前缀相同\n");
    }
    return 0;
}
```

### 用指针遍历字符串

判断条件写成 `while (*s)` 即可：当 `s` 指向结尾的空字符时 `*s` 为 0，条件为假，循环结束。
这是 C 里最地道的写法之一：

```c
#include <stdio.h>

void print_upper(const char *s) {
    while (*s) {                 /* 遇 '\0' 时 *s 为 0，循环自然结束 */
        char c = *s;
        if (c >= 'a' && c <= 'z') {
            c = (char)(c - 'a' + 'A');   /* ASCII 中大小写字母相差 32 */
        }
        putchar(c);
        s++;
    }
    putchar('\n');
}

int main(void) {
    print_upper("hello, c");
    return 0;
}
```

## 结构体

### 声明、定义与初始化

```c
#include <stdio.h>

/* 1. 声明结构类型（此时还没有分配内存） */
struct book {
    char title[40];
    char author[20];
    float price;
    int year;
};

int main(void) {
    /* 2. 定义变量并用初始化列表赋值，各初始化项用逗号分隔 */
    struct book first = {"C 程序设计语言", "K&R", 45.0f, 1988};

    /* 3. 结构数组：每个元素都是完整的 struct book */
    struct book shelf[2] = {
        {"现代操作系统", "Tanenbaum", 89.0f, 2014},
        {"算法导论", "Cormen", 128.0f, 2022},
    };

    /* 4. 结构嵌套：成员本身可以是另一个结构类型 */
    struct library {
        struct book featured;
        int total;
    } lib = {first, 3};

    /* 5. 成员访问用点号，逐级深入 */
    printf("%s / %s / %.1f\n", first.title, first.author, first.price);
    printf("第二本: %s\n", shelf[1].title);
    printf("特藏: %s，共 %d 本\n", lib.featured.title, lib.total);

    /* 6. 结构可以整体赋值（逐成员复制），但不能用 == 比较 */
    struct book copy = first;
    printf("副本: %s\n", copy.title);
    /* if (first == copy) 非法：标准未定义结构体的 == 运算 */

    return 0;
}
```

成员访问的层级递进可以这样记：`struct book` 是类型，`first` 是变量，`first.title` 是数组成员，
`first.title[0]` 是该数组的第一个字符。

结构可以整体赋值（逐成员复制，含成员里的数组），但**数组本身不能整体赋值**：

```c
struct book a = first;      /* 合法：结构整体复制 */
int src[3] = {1, 2, 3};
int dst[3];
/* dst = src;              非法：数组名不是可修改的左值 */
for (int i = 0; i < 3; i++) {
    dst[i] = src[i];        /* 只能逐元素复制，或用 memcpy */
}
```

### 结构体指针与 `->`

`->` 是"解引用 + 取成员"的合并写法：`p->price` 等价于 `(*p).price`。
`(*p).price` 的括号不能省，因为 `.` 的优先级高于 `*`。

```c
#include <stdio.h>

struct point {
    int x;
    int y;
};

int main(void) {
    struct point origin = {0, 0};
    struct point *p = &origin;    /* 数组元素则写 p = &path[0] */

    p->x = 3;                     /* 等价于 (*p).x = 3 */
    p->y = 4;
    printf("(%d, %d)\n", p->x, p->y);

    /* 结构数组的指针运算同样以整个结构体为单位步进 */
    struct point path[] = {{1, 1}, {2, 2}};
    struct point *q = path;
    printf("第二个点: (%d, %d)\n", (q + 1)->x, q[1].y);
    return 0;
}
```

### 向函数传递结构：三种方式对比

| 方式 | 写法 | 开销 | 能否修改调用方数据 | 适用场景 |
|------|------|------|--------------------|----------|
| 传成员 | `sum(v.a, v.b)` | 只复制需要的字段 | 否 | 结构很大但只需少量字段 |
| 传地址 | `sum(&v)` | 只复制一个指针 | **能**（加 `const` 则不能） | **推荐**，大结构体的默认选择 |
| 传整个结构 | `sum(v)` | 复制全部成员 | 否（改的是副本） | 结构很小（如两个 `int`） |

```c
#include <stdio.h>

struct rectangle {
    double width;
    double height;
};

/* 传地址 + const：大结构体的标准写法，既不复制也不修改 */
double area(const struct rectangle *r) {
    return r->width * r->height;
}

/* 传整个结构：函数拿到副本，修改不影响调用方 */
void inflate(struct rectangle r) {
    r.width *= 2;
    r.height *= 2;
}

int main(void) {
    struct rectangle box = {3.0, 4.0};
    printf("面积 %.1f\n", area(&box));

    inflate(box);
    printf("inflate 之后仍是 %.1f x %.1f\n", box.width, box.height);
    return 0;
}
```

函数参数和返回值都可以是结构体，结构体指针也支持这种双向通信。
不过返回大结构体会产生复制开销，实践中更常用"出参指针"来返回多个结果。

### 内存对齐与 `sizeof`

结构体大小不等于成员大小之和：编译器会在成员之间插入填充字节，使每个成员都对齐到自身大小的整数倍。
这也是为什么调整成员顺序可以减小结构体体积：

```c
#include <stdio.h>

struct wasteful {
    char flag;    /* 1 字节，后面补 3 字节 */
    int count;    /* 4 字节 */
    char tag;     /* 1 字节，后面补 3 字节 */
};

struct compact {
    int count;    /* 4 字节 */
    char flag;    /* 1 字节 */
    char tag;     /* 1 字节，后面补 2 字节 */
};

int main(void) {
    printf("wasteful=%zu compact=%zu\n", sizeof(struct wasteful), sizeof(struct compact));
    return 0;   /* 典型输出：12 和 8 */
}
```

### 结构体里存字符串：字符数组 vs 字符指针

| 写法 | 内存归属 | 能否直接赋值 | 风险 |
|------|----------|--------------|------|
| `char name[40]` | 数组内嵌在结构体里 | 需 `strncpy` | 有固定上限，但不涉及生命周期问题 |
| `char *name` | 只存一个地址，指向别处 | 可直接赋值指针 | 指向的字符串可能已失效，或忘记 `free` |

推荐用字符数组。结构体内的指针**只应管理那些已经分配、且生命周期明确的字符串**。
若一定要动态分配，`malloc` 与 `free` 必须成对出现：

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct person {
    int id;
    char *name;   /* 指向堆上的内存，生命周期需自己管理 */
};

int main(void) {
    struct person p;
    p.id = 1;

    /* +1 是给结尾的 '\0' 留位置；strlen 返回 size_t，无需强制转换 */
    p.name = malloc(strlen("Ada Lovelace") + 1);
    if (p.name == NULL) {
        fprintf(stderr, "内存分配失败\n");
        return 1;
    }
    strcpy(p.name, "Ada Lovelace");   /* 容量已确认足够，此处 strcpy 是安全的 */

    printf("%d: %s\n", p.id, p.name);

    free(p.name);      /* 成对释放，避免内存泄漏 */
    p.name = NULL;     /* 释放后置空，防止后续误用悬空指针 */
    return 0;
}
```

## 联合体与枚举

### 联合体 `union`

`union` 的所有成员**共享同一块内存**，大小等于最大成员的大小。任一时刻只有一个成员的值有意义，
写入一个成员会覆盖其他成员。它适合表达"同一位置可能是不同类型"的场景：

```c
#include <stdio.h>

union value {
    int i;
    float f;
    char bytes[4];
};

int main(void) {
    union value v;
    printf("sizeof(union value)=%zu\n", sizeof v);   /* 4，等于最大成员 */

    v.i = 0x41424344;
    printf("按 int 读: %d\n", v.i);
    printf("按字节读: %c%c%c%c\n", v.bytes[0], v.bytes[1], v.bytes[2], v.bytes[3]);
    /* 小端机器上输出 DCBA，这正是"成员共享内存"的直接证据 */

    v.f = 1.0f;      /* 写入 f 会覆盖 i 的内容 */
    printf("按 float 读: %.1f\n", v.f);
    return 0;
}
```

实际工程中 `union` 常与"类型标记"字段配合，表示一个带标签的变体类型：

```c
#include <stdio.h>

enum kind { KIND_INT, KIND_DOUBLE, KIND_TEXT };

struct tagged {
    enum kind type;      /* 标记当前 union 里存的是哪种类型 */
    union {
        int i;
        double d;
        const char *s;
    } as;
};

void print_tagged(const struct tagged *t) {
    switch (t->type) {
        case KIND_INT:
            printf("int: %d\n", t->as.i);
            break;
        case KIND_DOUBLE:
            printf("double: %.2f\n", t->as.d);
            break;
        case KIND_TEXT:
            printf("text: %s\n", t->as.s);
            break;
    }
}

int main(void) {
    struct tagged a = {KIND_DOUBLE, {.d = 3.14}};   /* 指定初始化器 */
    print_tagged(&a);
    return 0;
}
```

### 枚举 `enum`

枚举把一组相关的整型常量命名，默认从 0 开始依次递增，也可显式赋值（后续未赋值的元素继续递增）：

```c
#include <stdio.h>

/* 默认值：RED=0, GREEN=1, BLUE=2 */
enum color { RED, GREEN, BLUE };

/* 显式赋值：LOW=1, MEDIUM=5, HIGH=6 */
enum priority { LOW = 1, MEDIUM = 5, HIGH };

int main(void) {
    enum color c = GREEN;
    printf("GREEN=%d HIGH=%d\n", c, HIGH);   /* 1 和 6 */

    /* 用枚举做 switch 分支，编译器可对遗漏的分支给出告警 */
    switch (c) {
        case RED:
            printf("红\n");
            break;
        case GREEN:
            printf("绿\n");
            break;
        case BLUE:
            printf("蓝\n");
            break;
    }
    return 0;
}
```

C23 起枚举可以指定底层类型（`enum status : unsigned char { ... }`），使大小可控，
这在跨平台协议与嵌入式场景很有用。注意枚举常量本质仍是 `int`，C 不会阻止你给它赋任意整数。

### `typedef`

`typedef` 为类型创建别名，常用来省去 `struct`/`union`/`enum` 关键字，或简化复杂声明：

```c
#include <stdio.h>

typedef struct {
    int x;
    int y;
} point_t;   /* 匿名结构 + typedef，之后可直接写 point_t p; */

typedef unsigned char byte;

int main(void) {
    point_t p = {1, 2};
    byte b = 255;

    printf("(%d, %d) %u\n", p.x, p.y, b);
    printf("sizeof(point_t)=%zu\n", sizeof(point_t));
    return 0;
}
```

`typedef` 定义的是类型别名而不是新类型，所以 `point_t` 与对应的匿名结构完全兼容。
命名上加 `_t` 后缀能让人一眼看出这是类型名。

## 复杂声明：`*`、`()`、`[]` 的优先级

三个符号的优先级关系决定了所有复杂声明的含义：

- `()` 函数 与 `[]` 数组的优先级**相同**，都从左向右结合；
- 二者都**高于** `*` 指针。

因此读声明的顺序是：先找到变量名，向右看（是函数还是数组），再向左看（返回/元素类型），遇到括号就跳出来继续。

| 声明 | 读法 |
|------|------|
| `int *p[10]` | `[]` 先结合：p 是数组，元素是 `int *` → **指针数组** |
| `int (*p)[10]` | 括号强制 `*` 先结合：p 是指针，指向 `int[10]` → **数组指针** |
| `int *f(void)` | `f` 是函数，返回 `int *` → **返回指针的函数** |
| `int (*f)(void)` | `f` 是指针，指向返回 `int` 的函数 → **函数指针** |

### 函数指针

函数名在表达式中会退化为指向该函数的指针，所以把函数名直接赋给同类型的函数指针是合法的：

```c
#include <stdio.h>

int add(int a, int b) { return a + b; }
int multiply(int a, int b) { return a * b; }

/* 声明一个函数指针类型：接收两个 int，返回 int */
typedef int (*binop)(int, int);

int apply(binop op, int a, int b) {
    return op(a, b);   /* 通过指针调用；写成 (*op)(a, b) 也完全等价 */
}

int main(void) {
    /* 声明函数指针并赋值，类型必须匹配 */
    int (*pfunction)(int, int) = add;

    printf("%d\n", pfunction(2, 3));      /* 5 */
    printf("%d\n", (*pfunction)(2, 3));   /* 5，两种调用写法等价 */

    /* 用函数指针数组做分派表，替代冗长的 switch */
    binop table[] = {add, multiply};
    printf("%d\n", apply(table[1], 4, 5));   /* 20 */
    return 0;
}
```

函数指针最典型的用途是给 `qsort` 传比较函数：

```c
#include <stdio.h>
#include <stdlib.h>

/* 比较函数必须符合 int (*)(const void *, const void *) 的签名 */
int compare_int(const void *a, const void *b) {
    int lhs = *(const int *)a;
    int rhs = *(const int *)b;
    return (lhs > rhs) - (lhs < rhs);   /* 只返回 -1/0/1，避免减法溢出 */
}

int main(void) {
    int data[] = {5, 2, 9, 1};
    size_t n = sizeof data / sizeof data[0];

    qsort(data, n, sizeof data[0], compare_int);
    for (size_t i = 0; i < n; i++) {
        printf("%d ", data[i]);
    }
    printf("\n");
    return 0;
}
```

## 常见错误与排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `Segmentation fault` | 解引用空指针/野指针、数组越界、栈溢出 | 用 `-g` 编译后跑 `lldb`/`gdb`，或用 `-fsanitize=address` 定位 |
| `printf` 打出乱码或多读字符 | 字符数组缺 `'\0'`，被当字符串处理 | 保证缓冲区末尾有 `'\0'`，或改用 `fwrite` |
| `scanf` 之后 `getchar` 读到空行 | 上一次输入留下的 `'\n'` 还在缓冲区 | 循环 `while (getchar() != '\n')` 清空到行尾 |
| 用 `strlen(s) < 0` 判断恒为假 | `strlen` 返回无符号 `size_t` | 与 0 比较，或先转 `long` |
| 函数里 `sizeof` 得到 8 而非数组长度 | 数组形参已退化为指针 | 额外传长度参数 |
| 结构体 `sizeof` 比成员之和大 | 内存对齐产生填充 | 属正常行为；按大小降序排列成员可减少填充 |
| `printf("%d", 3.14)` 输出诡异数字 | 格式说明与实参类型不匹配（UB） | `double` 用 `%f`，`size_t` 用 `%zu` |
| 修改字符串字面量后崩溃 | 字面量位于只读段 | 需要修改就复制到数组：`char buf[] = "text";` |
| `malloc` 后忘记 `free` 或提前 `free` | 内存泄漏 / 悬空指针 | 成对使用，释放后立即置 `NULL` |
| 链接错误 `undefined reference to 'xxx'` | 只声明未定义，或漏了 `-lm` 之类的库 | 检查定义是否存在、链接参数是否完整 |

编译期把告警当错误、运行期打开 sanitizer，能提前消灭上面一大半问题：

```bash
cc -std=c23 -Wall -Wextra -Wpedantic -Wconversion -g demo.c -o demo
cc -std=c23 -fsanitize=address,undefined -g demo.c -o demo   # 检查越界与未定义行为
```

## C 与其他语言的关系

| 维度 | C | 对比对象 |
|------|---|----------|
| 类型检查 | 弱类型，隐式转换多 | [[go-language-basics\|Go]] 严格，数值转换必须显式 |
| 内存管理 | 手工 `malloc`/`free` | Go 有 GC；Rust 用所有权在编译期检查 |
| 字符串 | `char *` + `'\0'`，无长度 | Python 的 `str` 自带长度且不可变 |
| 错误处理 | 返回错误码，无异常 | Go 的显式 `error` 返回值，思路与 C 接近 |
| 编译产物 | 直接生成机器码，可静态链接 | 因此常被用作跨语言 ABI 的基础 |

C 是几乎所有运行时的底层：CPython 解释器、JVM、Linux 内核、SQLite 都用 C 写成。
理解了 C 的内存模型（栈帧、指针、数组退化），再看 [[01-cs-fundamentals/operating-systems|操作系统]] 里的进程与虚拟内存、
[[01-cs-fundamentals/data-structures|数据结构]] 里的链表与动态数组，很多实现细节就不必死记了。

## See Also

- [[go-language-basics|Go 语言入门]]：同为编译型语言，对比着读更能体会 C 的"显式"风格
- [[01-cs-fundamentals/data-structures|数据结构]]：链表、哈希表等结构的 C 实现基础
- [[01-cs-fundamentals/operating-systems|操作系统]]：进程地址空间、栈与堆的划分
- [[linux|Linux 基础]]：`gcc`、`gdb`、`valgrind` 的使用场景
- [[02-backend/index|后端开发目录]]

## 参考

- [cppreference: C 语言](https://en.cppreference.com/w/c) —— 标准库与语法最权威的在线参考
- [C23 草案 N3220](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf) —— 与正式标准几乎一致的最终工作草案
- [GCC 标准选项](https://gcc.gnu.org/onlinedocs/gcc/C-Dialect-Options.html) —— `-std=` 取值与各标准差异
- [Clang 用户手册](https://clang.llvm.org/docs/UsersManual.html) —— Clang 对 C23 的支持范围
- Brian W. Kernighan, Dennis M. Ritchie. *The C Programming Language*, 2nd ed.
- Jens Gustedt. *Modern C*, 2nd ed. (2025) —— 免费在线版覆盖 C23
