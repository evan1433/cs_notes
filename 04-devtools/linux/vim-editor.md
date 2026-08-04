---
title: Vim 与 Neovim 使用手册
description: Vim 核心编辑操作、寄存器、多文件管理、配置，以及 Neovim Lua、LSP、Tree-sitter 和插件用法
tags:
  - linux
  - vim
  - neovim
  - editor
date: 2026-07-23
---

# Vim 与 Neovim 使用手册

Vim 是从 vi 发展而来的模式化文本编辑器。Neovim（命令名为 `nvim`）是 Vim 的分支，保留了绝大多数
编辑命令，并提供 Lua 配置、内置 LSP 客户端、Tree-sitter、异步任务和更完整的扩展 API。

两者最重要的部分不是插件，而是共同的编辑语言：**操作符 + 移动范围 + 次数**。掌握本篇前半部分后，可以在 Vim、Neovim、IDE 的 Vim 模式以及远程服务器中复用同一套操作习惯。

> 本文 Neovim 专属内容以 0.12 系列为准。截至 2026-07-23，最新稳定版为 0.12.4。

## 1. Vim 还是 Neovim

| 对比项 | Vim | Neovim |
|--------|-----|--------|
| 启动命令 | `vim` | `nvim` |
| 用户配置 | `~/.vimrc` | `~/.config/nvim/init.lua` 或 `init.vim` |
| 主要配置语言 | Vimscript、Vim9 script | Lua，也兼容大部分 Vimscript |
| LSP | 通常依赖插件 | 内置 LSP 客户端，语言服务器需另行安装 |
| Tree-sitter | 通常依赖插件 | 内置 Tree-sitter 运行时，额外解析器需安装 |
| 插件 | Vim packages 或插件管理器 | 内置 `vim.pack` 或第三方插件管理器 |
| 外部集成 | Job、Channel 等机制 | RPC、异步任务、可嵌入 UI，API 更统一 |
| 适合场景 | 服务器维护、传统 Vim 配置、最小环境 | 日常开发、现代 IDE 能力、Lua 配置 |

选择建议：

- 远程服务器只保证安装 Vim 时，优先掌握不依赖插件的通用命令。
- 想用 LSP、代码诊断、语义跳转和 Lua 插件生态时，优先选择 Neovim。
- 已有稳定的 `.vimrc` 和插件体系时，不必为了“更新”而立即迁移。
- 初学者可以直接学 Neovim，但应先掌握原生编辑命令，再逐步增加插件。

## 2. 安装与启动

### 2.1 安装

macOS：

```bash
brew install vim
brew install neovim
```

Ubuntu 或 Debian：

```bash
sudo apt update
sudo apt install vim neovim
```

Linux 发行版仓库中的 Neovim 可能不是最新稳定版。需要较新 LSP 或 `vim.pack` API 时，应使用
[Neovim 官方安装说明](https://neovim.io/doc/install/)提供的包或压缩文件。

Windows：

```powershell
winget install vim.vim
winget install Neovim.Neovim
```

检查版本和功能：

```bash
vim --version
nvim --version
```

### 2.2 启动方式

```bash
vim                         # 打开空缓冲区
vim notes.md                # 打开或创建文件
vim +42 notes.md            # 打开后跳到第 42 行
vim +/keyword notes.md      # 打开后跳到第一个匹配
vim -R notes.md             # 只读模式
vim file1.md file2.md       # 一次载入多个文件
vim -d old.txt new.txt      # 差异比较模式

nvim .                      # 用 Neovim 打开当前项目目录
nvim --clean notes.md       # 不读取用户配置，便于排查问题
```

后续命令中的 `vim` 均可替换为 `nvim`。

## 3. 模式

Vim 的按键含义取决于当前模式。按 `Esc` 通常可以回到普通模式。

| 模式 | 用途 | 进入方式 | 返回普通模式 |
|------|------|----------|--------------|
| 普通模式 Normal | 移动、删除、复制、跳转、执行编辑命令 | 启动后默认进入 | 已在普通模式 |
| 插入模式 Insert | 像普通编辑器一样输入文字 | `i`、`a`、`o` 等 | `Esc` 或 `Ctrl+[` |
| 可视模式 Visual | 选择字符、整行或矩形区域 | `v`、`V`、`Ctrl+v` | `Esc` |
| 命令行模式 Command-line | 保存、退出、替换、设置选项 | `:`、`/`、`?` | 执行命令或按 `Esc` |
| 替换模式 Replace | 连续覆盖已有字符 | `R` | `Esc` |
| 终端模式 Terminal | 与 Neovim 内置终端交互 | `:terminal` | `Ctrl+\` 后按 `Ctrl+n` |

刚打开编辑器却无法输入文字时，先按 `i`；想停止输入并执行命令时，按 `Esc`。

## 4. 最小生存指南

只记住下面这些按键，就能完成一次基本编辑：

| 按键 | 作用 |
|------|------|
| `i` | 在光标前进入插入模式 |
| `Esc` | 返回普通模式 |
| `h` `j` `k` `l` | 左、下、上、右移动 |
| `x` | 删除一个字符 |
| `dd` | 删除当前行 |
| `yy` | 复制当前行 |
| `p` | 粘贴到光标后 |
| `u` | 撤销 |
| `Ctrl+r` | 重做 |
| `:w` | 保存 |
| `:q` | 退出 |
| `:wq` | 保存并退出 |
| `:q!` | 放弃修改并退出 |

如果不确定自己在哪个模式，按一次 `Esc`，再输入以 `:` 开头的命令。

## 5. Vim 的编辑语法

Vim 命令通常由以下部分组成：

```text
[次数] + 操作符 + [次数] + 移动范围
```

例如：

| 命令 | 拆解 | 作用 |
|------|------|------|
| `dw` | `d` 删除 + `w` 到下一单词 | 删除到下一单词开头 |
| `d$` | `d` 删除 + `$` 到行尾 | 删除到行尾 |
| `c3w` | `c` 修改 + `3w` 三个单词 | 删除三个单词并进入插入模式 |
| `y}` | `y` 复制 + `}` 到下一段 | 复制到下一段 |
| `2dd` | `2` 次 + `dd` 删除整行 | 删除两行 |
| `>}` | `>` 缩进 + `}` 到下一段 | 缩进当前段落 |

常用操作符：

| 操作符 | 含义 |
|--------|------|
| `d` | 删除，并把内容写入寄存器 |
| `c` | 修改：删除后进入插入模式 |
| `y` | 复制（yank）到寄存器 |
| `>` / `<` | 增加或减少缩进 |
| `=` | 按文件类型重新缩进 |
| `g~` | 切换大小写 |
| `gu` / `gU` | 转为小写或大写 |

操作符连续输入两次通常作用于整行，例如 `dd`、`cc`、`yy`、`>>` 和 `==`。

## 6. 光标移动

### 6.1 字符、单词和行

| 按键 | 作用 |
|------|------|
| `h` `j` `k` `l` | 左、下、上、右 |
| `w` / `W` | 下一单词开头；`W` 以空白分隔大单词 |
| `b` / `B` | 上一单词开头 |
| `e` / `E` | 当前或下一单词结尾 |
| `0` | 物理行首 |
| `^` | 当前行第一个非空字符 |
| `$` | 行尾 |
| `g_` | 当前行最后一个非空字符 |
| `gj` / `gk` | 按屏幕显示行向下或向上移动，适合自动换行文本 |

### 6.2 行内查找

| 按键 | 作用 |
|------|------|
| `f{字符}` | 跳到本行下一个指定字符 |
| `F{字符}` | 跳到本行上一个指定字符 |
| `t{字符}` | 跳到下一个指定字符之前 |
| `T{字符}` | 跳到上一个指定字符之后 |
| `;` | 按原方向重复最近一次 `f`、`F`、`t`、`T` |
| `,` | 反方向重复 |

例如在 `user.get_profile()` 的行首按 `f.`，会跳到点号；再按 `dt(` 可以删除到左括号之前。

### 6.3 文件和屏幕跳转

| 按键                  | 作用               |
| ------------------- | ---------------- |
| `gg`                | 文件第一行            |
| `G`                 | 文件最后一行           |
| `{数字}G` 或 `{数字}gg`  | 跳到指定行            |
| `Ctrl+f` / `Ctrl+b` | 向下或向上翻一页         |
| `Ctrl+d` / `Ctrl+u` | 向下或向上翻半页         |
| `H` / `M` / `L`     | 屏幕顶部、中部、底部       |
| `zz` / `zt` / `zb`  | 把当前行置于屏幕中部、顶部、底部 |
| `{` / `}`           | 上一个或下一个段落        |
| `(` / `)`           | 上一个或下一个句子        |
| `%`                 | 跳到匹配的括号、注释或预处理结构 |

### 6.4 跳转历史

| 按键 | 作用 |
|------|------|
| `Ctrl+o` | 回到较旧的跳转位置 |
| `Ctrl+i` | 前往较新的跳转位置；终端中等同于 `Tab` |
| `g;` / `g,` | 跳到上一个或下一个修改位置 |
| `` `. `` | 跳到上一次修改的精确位置 |
| 反引号键 × 2 | 在最近两个跳转位置之间切换 |

## 7. 插入、删除、修改和重复

### 7.1 进入插入模式

| 按键 | 作用 |
|------|------|
| `i` / `a` | 在光标前或后插入 |
| `I` / `A` | 在行首第一个非空字符或行尾插入 |
| `o` / `O` | 在下方或上方新建一行 |
| `s` | 删除当前字符后进入插入模式 |
| `S` 或 `cc` | 清空当前行内容后进入插入模式 |
| `C` | 删除到行尾后进入插入模式 |

### 7.2 常用编辑命令

| 按键 | 作用 |
|------|------|
| `x` / `X` | 删除光标处或光标前字符 |
| `dd` / `D` | 删除整行或删除到行尾 |
| `yy` | 复制整行 |
| `p` / `P` | 在光标后或前粘贴 |
| `r{字符}` | 用一个字符替换光标处字符 |
| `J` | 合并下一行，并在中间补空格 |
| `gJ` | 合并下一行，不补空格 |
| `~` | 切换当前字符大小写 |
| `Ctrl+a` / `Ctrl+x` | 增加或减少光标附近的数字 |
| `u` / `Ctrl+r` | 撤销或重做 |
| `.` | 重复最近一次修改 |

`.` 是最值得培养的习惯之一。例如先用 `ciw` 修改一个单词，再移动到其他单词按 `.`，即可重复修改动作。

## 8. 文本对象

文本对象让操作范围按语义划分，而不是按坐标划分：

```text
操作符 + i（inside，内部）或 a（around，包含边界）+ 对象
```

| 对象 | 示例 | 作用 |
|------|------|------|
| `w` 单词 | `ciw` | 修改当前单词 |
| `W` 大单词 | `daW` | 删除以空白分隔的整个大单词 |
| `"` 双引号 | `ci"` | 修改双引号内部内容 |
| `'` 单引号 | `da'` | 删除单引号及其内容 |
| `(` 或 `)` | `ci(` | 修改圆括号内部内容 |
| `[` 或 `]` | `di[` | 删除方括号内部内容 |
| `{` 或 `}` | `va{` | 选择花括号及其内容 |
| `t` XML/HTML 标签 | `cit` | 修改标签内部内容 |
| `p` 段落 | `dap` | 删除当前段落及周围空白 |
| `s` 句子 | `yis` | 复制当前句子内部 |

`i` 不含分隔符，`a` 通常包含分隔符或相邻空白。代码编辑中常用 `ciw`、`ci"`、`ci(`、`da{`。

## 9. 查找与替换

### 9.1 查找

| 命令 | 作用 |
|------|------|
| `/pattern` | 向后查找 |
| `?pattern` | 向前查找 |
| `n` / `N` | 沿原方向或反方向查找下一个匹配 |
| `*` / `#` | 向后或向前查找光标处完整单词 |
| `g*` / `g#` | 查找光标处文本，不要求完整单词 |
| `:nohlsearch` | 暂时清除搜索高亮，简写 `:noh` |

Vim 使用自己的正则表达式语法。`V` 可以把后续模式按普通文本处理，例如 `/\Vuser.name`。

### 9.2 替换

```vim
:s/old/new/             " 当前行第一个匹配
:s/old/new/g            " 当前行所有匹配
:%s/old/new/g           " 整个文件所有匹配
:%s/old/new/gc          " 整个文件替换，每次确认
:5,20s/old/new/g        " 第 5 至 20 行
:'<,'>s/old/new/g       " 可视选择范围；选中后按 : 会自动带入范围
:%s#old/path#new/path#g " 内容含 / 时可更换分隔符
:%s/\s\+$//e           " 删除行尾空白，e 表示无匹配时不报错
```

确认替换时常用：`y` 替换当前项、`n` 跳过、`a` 替换所有剩余项、`q` 退出。

### 9.3 全局命令

```vim
:g/TODO/print           " 打印包含 TODO 的行
:g/TODO/d               " 删除包含 TODO 的行
:v/ERROR/d              " 删除不包含 ERROR 的行
:g/^$/d                 " 删除所有空行
```

`:g` 选择匹配行后执行 Ex 命令；`:v` 选择不匹配的行。

## 10. 寄存器与系统剪贴板

Vim 的删除、复制和粘贴通过寄存器完成。寄存器不是天然等同于操作系统剪贴板。

| 寄存器 | 访问方式 | 用途 |
|--------|----------|------|
| 无名寄存器 | `""` | 最近一次删除或复制，普通 `p` 默认读取它 |
| 命名寄存器 | `"a` 至 `"z` | 保存自定义内容；大写名称表示追加 |
| 复制寄存器 | `"0` | 最近一次复制内容，不会被普通删除覆盖 |
| 小删除寄存器 | `"-` | 最近一次不含换行的小删除 |
| 黑洞寄存器 | `"_` | 丢弃内容，不污染普通寄存器 |
| 系统剪贴板 | `"+` | 通常对应操作系统 Clipboard |
| 主选择区 | `"*` | X11 Primary Selection；平台行为可能不同 |
| 表达式寄存器 | `"=` | 计算表达式并插入结果 |

常用示例：

```vim
"ayy                   " 复制当前行到寄存器 a
"ap                    " 粘贴寄存器 a
"Ayy                   " 追加当前行到寄存器 a
"_dd                   " 删除当前行但不覆盖普通寄存器
"+y                    " 可视模式下复制到系统剪贴板
"+p                    " 从系统剪贴板粘贴
:registers              " 查看寄存器，简写 :reg
```

若希望普通复制和粘贴默认使用系统剪贴板：

```vim
set clipboard=unnamedplus
```

Linux 终端环境可能需要 `xclip`、`xsel` 或 Wayland 剪贴板工具；Neovim 可通过 `:checkhealth` 检查提供者。

## 11. 可视模式与列编辑

| 按键 | 作用 |
|------|------|
| `v` | 按字符选择 |
| `V` | 按整行选择 |
| `Ctrl+v` | 块选择，即矩形区域 |
| `o` | 在选择区域的两端之间切换 |
| `gv` | 重新选择上一次区域 |

选择后可按 `d`、`y`、`c`、`>`、`<`、`=`、`u`、`U` 执行删除、复制、修改、缩进和大小写转换。

在多行前添加相同文本：

1. 按 `Ctrl+v` 进入块选择。
2. 用 `j`、`k` 选中多行的同一列。
3. 按 `I`，输入要添加的内容。
4. 按 `Esc`，Vim 会把内容应用到所有选中行。

在多行末尾添加内容时，块选择后使用 `A`。

## 12. 文件、缓冲区、窗口和标签页

理解四个概念可以避免“关闭窗口却丢了文件”之类的困惑：

| 概念           | 含义                        |
| ------------ | ------------------------- |
| 文件 File      | 磁盘上的持久化数据                 |
| 缓冲区 Buffer   | 文件加载到内存后的编辑对象             |
| 窗口 Window    | 显示某个缓冲区的视图；一个缓冲区可显示在多个窗口中 |
| 标签页 Tab page | 一组窗口布局，不等同于其他编辑器的单文件标签    |

### 12.1 文件与缓冲区

```vim
:edit path/to/file      " 打开文件，简写 :e
:write                  " 保存，简写 :w
:saveas new-name.txt    " 另存为
:read other.txt         " 把文件内容插入当前缓冲区
:ls                     " 列出缓冲区
:bnext                  " 下一个缓冲区，简写 :bn
:bprevious              " 上一个缓冲区，简写 :bp
:buffer 3               " 打开编号为 3 的缓冲区
:buffer filename        " 按名称打开缓冲区，可按 Tab 补全
:bdelete                " 从缓冲区列表移除当前缓冲区，简写 :bd
:e!                     " 放弃未保存修改并重新载入当前文件
```

`:bd` 关闭缓冲区，`:q` 关闭当前窗口。只有一个窗口时，`:q` 才会退出编辑器。

### 12.2 分屏窗口

```vim
:split file.py          " 水平分屏，简写 :sp
:vsplit file.py         " 垂直分屏，简写 :vsp
Ctrl+w h                " 前往左侧窗口
Ctrl+w j                " 前往下方窗口
Ctrl+w k                " 前往上方窗口
Ctrl+w l                " 前往右侧窗口
Ctrl+w w                " 循环切换窗口
Ctrl+w =                " 所有窗口等宽等高
Ctrl+w _                " 当前窗口高度最大化
Ctrl+w |                " 当前窗口宽度最大化
Ctrl+w c                " 关闭当前窗口
:only                   " 只保留当前窗口
```

### 12.3 标签页

```vim
:tabnew file.py         " 在新标签页打开文件
:tabnext                " 下一个标签页，简写 :tabn
:tabprevious            " 上一个标签页，简写 :tabp
:tabclose               " 关闭当前标签页
:tabs                   " 列出所有标签页
gt                      " 下一个标签页
gT                      " 上一个标签页
```

建议用缓冲区管理文件，用窗口组织同时可见的内容，用标签页保存不同的窗口布局。

## 13. 标记、折叠与宏

### 13.1 标记

| 命令 | 作用 |
|------|------|
| `m{a-z}` | 设置当前文件内的局部标记 |
| `m{A-Z}` | 设置可跨文件跳转的全局标记 |
| `` `{标记} `` | 跳到标记的精确位置 |
| `'{标记}` | 跳到标记所在行的第一个非空字符 |
| `:marks` | 查看标记 |
| `:delmarks a` | 删除标记 a |

常用特殊标记：`` `. `` 是上一次修改位置，`` `^ `` 是上一次退出插入模式的位置，`` `" `` 是上次退出文件的位置。

### 13.2 折叠

| 命令 | 作用 |
|------|------|
| `zf{移动}` | 按移动范围创建手动折叠 |
| `zfap` | 折叠当前段落 |
| `zo` / `zc` | 打开或关闭当前折叠 |
| `za` | 切换当前折叠 |
| `zR` / `zM` | 打开或关闭所有折叠 |

```vim
:set foldmethod=manual  " 手动折叠
:set foldmethod=indent  " 按缩进折叠
:set foldmethod=syntax  " 按 Vim 语法规则折叠
:set foldmethod=expr    " 按表达式折叠，可与 LSP 或 Tree-sitter 集成
```

### 13.3 宏

宏会把按键录制到寄存器：

```text
qa        开始录制到寄存器 a
...       执行一系列可重复操作
q         停止录制
@a        执行宏 a
@@        重复最近执行的宏
10@a      执行宏 a 十次
```

录制宏时优先使用 `0`、`f`、`w` 等可重复定位命令，少依赖固定列位置。配合 `.` 和 `@@` 可以高效处理
结构相似的多行文本。

## 14. 帮助、补全与外部命令

### 14.1 内置帮助

Vim 和 Neovim 的内置帮助比搜索零散配置更可靠：

```vim
:help                    " 打开帮助首页
:help motion.txt         " 移动命令手册
:help registers          " 寄存器帮助
:help :substitute        " Ex 命令前加冒号查询
:help i_CTRL-N           " 插入模式按键以 i_ 开头
:help nvim-from-vim      " Neovim 从 Vim 迁移说明
Ctrl+]                   " 在帮助中进入光标下的链接
Ctrl+o                   " 返回上一位置
```

终端执行 `vimtutor`，或在 Neovim 中执行 `:Tutor`，可以完成交互式入门教程。

### 14.2 内置补全

插入模式常用补全：

| 按键 | 作用 |
|------|------|
| `Ctrl+n` / `Ctrl+p` | 下一个或上一个关键字候选 |
| `Ctrl+x Ctrl+f` | 文件名补全 |
| `Ctrl+x Ctrl+l` | 整行补全 |
| `Ctrl+x Ctrl+o` | omnifunc 全能补全，能力取决于文件类型或 LSP |

### 14.3 外部命令和过滤器

```vim
:!git status             " 临时执行 Shell 命令
:read !date              " 把命令输出插入缓冲区
:%!jq .                  " 用 jq 格式化整个缓冲区
:'<,'>!sort              " 用 sort 处理可视选择区域
:make                    " 执行 makeprg，并把错误写入 quickfix
:copen                   " 打开 quickfix 列表
:cnext                   " 前往下一条 quickfix 结果
```

Neovim 和带终端功能的 Vim 可使用 `:terminal`。在 Neovim 终端模式中按 `Ctrl+\`、`Ctrl+n` 回到普通模式，
随后可以使用窗口切换和复制命令。

## 15. Vim 配置

Vim 用户配置通常位于 `~/.vimrc`。可以通过 `:echo $MYVIMRC` 查看实际加载的文件，并用
`:source $MYVIMRC` 重新加载。

下面是一份克制的基础配置：

```vim
" ~/.vimrc

set number                  " 绝对行号
set relativenumber          " 相对行号，便于使用 5j、8k
set cursorline              " 高亮当前行
set scrolloff=5             " 光标上下保留可见行
set signcolumn=yes          " 固定符号列，避免界面左右跳动

set expandtab               " Tab 输入为空格
set tabstop=4               " Tab 显示宽度
set shiftwidth=4            " 自动缩进宽度
set softtabstop=4           " 编辑时的 Tab 宽度
set autoindent

set ignorecase              " 搜索默认忽略大小写
set smartcase               " 搜索词含大写时区分大小写
set incsearch               " 输入搜索词时即时匹配
set hlsearch                " 高亮搜索结果

set undofile                " 持久化撤销历史
set clipboard=unnamedplus   " 普通复制使用系统剪贴板
set mouse=a
set termguicolors

filetype plugin indent on
syntax enable

let mapleader = " "
nnoremap <leader>w :write<CR>
nnoremap <leader>q :quit<CR>
nnoremap <Esc><Esc> :nohlsearch<CR>
```

说明：

- 映射优先使用 `nnoremap`、`inoremap`、`vnoremap` 等非递归形式，避免意外展开其他映射。
- 不建议无条件关闭 swap、backup 和 undo 文件；它们是故障恢复机制，应配置目录而不是全部禁用。
- `clipboard=unnamedplus` 是否可用取决于 Vim 的编译选项和系统剪贴板工具，可用 `:version` 检查。
- 团队项目不要默认启用不可信目录中的 `.vimrc`；模型行和本地配置都可能执行命令。

## 16. Neovim 用法

### 16.1 配置位置与目录结构

Neovim 可以使用 `init.lua` 或 `init.vim`，但同一配置目录中不能同时把两者作为主配置加载。执行
`:echo stdpath('config')` 可以查看当前平台的配置目录。

常见结构：

```text
~/.config/nvim/
├── init.lua
├── lua/
│   ├── options.lua
│   ├── keymaps.lua
│   └── lsp.lua
├── after/
│   └── ftplugin/
│       └── python.lua
└── lsp/
    └── pyright.lua
```

`lua/options.lua` 可在 `init.lua` 中用 `require("options")` 加载；`after/ftplugin/python.lua` 只在 Python
缓冲区加载，适合文件类型专属设置。

### 16.2 最小 `init.lua`

```lua
-- ~/.config/nvim/init.lua

vim.g.mapleader = " "
vim.g.maplocalleader = " "

local opt = vim.opt
opt.number = true
opt.relativenumber = true
opt.cursorline = true
opt.scrolloff = 5
opt.signcolumn = "yes"
opt.termguicolors = true
opt.mouse = "a"
opt.clipboard = "unnamedplus"

opt.expandtab = true
opt.tabstop = 4
opt.shiftwidth = 4
opt.smartindent = true

opt.ignorecase = true
opt.smartcase = true
opt.incsearch = true
opt.undofile = true

vim.keymap.set("n", "<leader>w", "<cmd>write<cr>", { desc = "保存文件" })
vim.keymap.set("n", "<leader>q", "<cmd>quit<cr>", { desc = "关闭窗口" })
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<cr>")

vim.api.nvim_create_autocmd("TextYankPost", {
  desc = "短暂高亮刚复制的文本",
  callback = function()
    vim.hl.on_yank({ timeout = 150 })
  end,
})
```

Lua API 常用对应关系：

| Vimscript | Neovim Lua |
|-----------|------------|
| `set number` | `vim.opt.number = true` |
| `let mapleader = " "` | `vim.g.mapleader = " "` |
| `nnoremap ...` | `vim.keymap.set("n", ...)` |
| `autocmd ...` | `vim.api.nvim_create_autocmd(...)` |
| `:colorscheme habamax` | `vim.cmd.colorscheme("habamax")` |
| `expand("%:p")` | `vim.fn.expand("%:p")` |

在 Neovim 中执行 `:source $MYVIMRC` 可重新加载配置。插件和自动命令可能留下状态，复杂改动建议执行
`:restart` 或退出后重开。

### 16.3 插件管理

Neovim 0.12 提供内置 `vim.pack`。下面示例会安装并加载一个同时兼容 Vim 和 Neovim 的包围符编辑插件：

```lua
vim.pack.add({
  {
    src = "https://github.com/tpope/vim-surround",
  },
})
```

首次启动需要 `git` 和网络。插件状态记录在 lockfile 中，应像依赖锁文件一样纳入版本控制。管理命令和
路径以 `:help vim.pack` 为准。

现有配置也常使用 lazy.nvim、mini.deps、packer.nvim 等第三方管理器。不要在同一插件上混用多个管理器；
先从零插件配置开始，只在出现明确需求时添加插件。

### 16.4 内置 LSP

Neovim 是 LSP 客户端，不包含各语言的服务器。以 Python 为例，先安装 Pyright：

```bash
npm install --global pyright
pyright-langserver --version
```

在 Neovim 0.11+ 中可以直接定义并启用配置：

```lua
vim.lsp.config.pyright = {
  cmd = { "pyright-langserver", "--stdio" },
  filetypes = { "python" },
  root_markers = { "pyproject.toml", "setup.py", ".git" },
  settings = {
    python = {
      analysis = {
        typeCheckingMode = "basic",
      },
    },
  },
}

vim.lsp.enable("pyright")

vim.keymap.set("n", "gd", vim.lsp.buf.definition, { desc = "跳转到定义" })
vim.keymap.set("n", "K", vim.lsp.buf.hover, { desc = "显示符号文档" })
vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, { desc = "重命名符号" })
vim.keymap.set({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, { desc = "代码操作" })

vim.diagnostic.config({
  virtual_text = true,
  underline = true,
  signs = true,
})
```

也可以安装 `nvim-lspconfig` 获取社区维护的服务器配置，然后执行：

```lua
vim.lsp.enable({ "pyright", "lua_ls", "gopls" })
```

语言服务器的可执行文件仍需单独安装。打开源码后执行 `:checkhealth vim.lsp`，确认服务器是否启动、
项目根目录是否识别正确。

Neovim 0.12 的常用默认 LSP 映射还包括：

| 按键 | 作用 |
|------|------|
| `grn` | 重命名符号 |
| `grr` | 查找引用 |
| `gri` | 跳转到实现 |
| `grt` | 跳转到类型定义 |
| `gra` | 代码操作 |
| `gO` | 文档符号 |

### 16.5 Tree-sitter

Tree-sitter 对源码生成增量语法树，可用于语法高亮、文本对象和结构化选择。Neovim 内置运行时，但只捆绑
少量解析器；其他语言通常通过 `nvim-treesitter` 或系统包安装解析器。

解析器存在时，可为当前缓冲区启用高亮：

```lua
vim.treesitter.start()
```

常用诊断命令：

```vim
:Inspect                  " 查看光标处的高亮捕获
:InspectTree              " 查看当前语法树
:checkhealth vim.treesitter
```

Tree-sitter 与 LSP 职责不同：Tree-sitter 理解当前文件的语法结构；LSP 由语言服务器分析整个项目的符号、
类型、引用和诊断。两者通常同时使用。

### 16.6 Neovim 终端

```vim
:terminal                 " 在当前窗口打开终端
:split | terminal         " 水平分屏打开终端
:vsplit | terminal        " 垂直分屏打开终端
:terminal git status      " 执行命令并保留终端缓冲区
```

终端模式按键：

| 按键 | 作用 |
|------|------|
| `Ctrl+\ Ctrl+n` | 从终端输入状态回到普通模式 |
| `i` | 从普通模式返回终端输入状态 |
| `Ctrl+w h/j/k/l` | 普通模式下切换窗口 |
| `:bd!` | 关闭终端缓冲区；运行中的进程也会终止 |

可添加更顺手的退出映射：

```lua
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "退出终端模式" })
```

### 16.7 从 Vim 迁移到 Neovim

迁移建议：

1. 先用 `nvim --clean` 确认终端、字体和基础操作正常。
2. 把 `.vimrc` 中通用选项逐条改写到 `init.lua`，不要一次复制整个插件体系。
3. 用 `:checkhealth` 检查剪贴板、Python、Node.js、LSP 和 Tree-sitter。
4. 每添加一个插件就重启并验证，避免多个故障叠加。
5. 使用 `:help vim-differences` 查询不兼容项；Neovim 不支持 Vim9 script。

如果暂时保留 Vimscript，可先创建 `~/.config/nvim/init.vim`。确认配置可用后，再按模块逐步迁移到 Lua。

## 17. 常见问题

### 17.1 无法退出

先按 `Esc`，再选择：

```vim
:q       " 没有未保存修改时退出
:wq      " 保存并退出
:q!      " 放弃修改并退出
:qa!     " 放弃所有窗口和缓冲区的修改并退出
```

### 17.2 粘贴后缩进混乱

现代终端通常支持 bracketed paste，不需要手动设置。旧环境可临时使用：

```vim
:set paste
```

粘贴完成后立即恢复：

```vim
:set nopaste
```

优先使用 `"+p` 从系统剪贴板粘贴，避免把终端粘贴误判为连续键入。

### 17.3 系统剪贴板不可用

```vim
:echo has('clipboard')    " Vim 是否编译了剪贴板支持
:set clipboard?          " 查看当前选项
:checkhealth             " Neovim 检查剪贴板提供者
```

在 Linux 上安装 `xclip`、`xsel` 或 `wl-clipboard` 后重试。SSH 会话默认访问的是远端剪贴板环境，
不是本机图形界面的剪贴板。

### 17.4 交换文件冲突

看到 `E325: ATTENTION` 时，先确认文件是否正在另一个 Vim 进程中编辑。若上次异常退出，应优先恢复：

```bash
vim -r notes.md
```

检查恢复内容并保存后，再删除遗留的 `.swp` 文件。不要在未确认另一个进程状态时直接删除交换文件。

### 17.5 没有权限保存

退出后使用有权限的命令重新编辑最清晰。若必须保留当前缓冲区，可把内容交给 `sudo tee`：

```vim
:write !sudo tee % >/dev/null
:edit!
```

不要习惯性用 `sudo vim` 编辑普通用户文件，否则可能在项目中留下属于 root 的文件。

### 17.6 编码和换行符

```vim
:set fileencoding?       " 当前文件编码
:set fileformat?         " unix、dos 或 mac
:set fileformat=unix     " 保存为 LF
:set fileformat=dos      " 保存为 CRLF
:edit ++enc=gbk file.txt " 按指定编码重新打开
```

### 17.7 Neovim 配置报错

```bash
nvim --clean             # 判断问题是否来自用户配置
nvim --headless '+checkhealth' '+qa'
```

在 Neovim 内执行：

```vim
:messages                " 查看完整错误消息
:checkhealth             " 检查环境和插件依赖
:echo stdpath('config')  " 确认配置目录
:scriptnames             " 查看已加载脚本
```

### 17.8 LSP 没有启动

依次检查：

1. 语言服务器命令是否能在 Shell 中执行。
2. 当前缓冲区的 `:set filetype?` 是否正确。
3. 项目是否包含配置中的 `root_markers`。
4. `:checkhealth vim.lsp` 是否显示配置已启用、客户端已附加。
5. 服务器日志和 `:messages` 是否有启动参数或权限错误。

## 18. 实战练习

新建一个临时文件，把以下文本粘贴进去：

```text
alice,python,3
bob,go,7
carol,rust,2
```

按顺序练习：

1. 用 `gg` 回到第一行，用 `0`、`$`、`w`、`f,` 移动。
2. 在第一行按 `A` 添加 `,active`，按 `Esc` 回到普通模式。
3. 在第二、三行按 `.` 重复添加。
4. 用 `:%s/,/ | /g` 把逗号替换为竖线分隔符。
5. 用 `ggVG=` 重新缩进全文，观察不同文件类型的行为。
6. 用 `yy` 复制一行、`p` 粘贴、`u` 撤销、`Ctrl+r` 重做。
7. 录制一个宏，把每行首字母改成大写，再用 `@@` 重复。
8. 用 `:w practice.txt` 保存，再用 `:q` 退出。

## 19. 学习路径

| 阶段 | 重点 |
|------|------|
| 入门 | 模式切换、`hjkl`、`i`、`dd`、`yy`、`p`、`u`、`:wq` |
| 基础 | 操作符 + 移动、次数、搜索替换、文本对象、`.` 重复 |
| 进阶 | 寄存器、宏、标记、跳转列表、缓冲区、窗口、quickfix |
| Vim 配置 | `.vimrc`、非递归映射、文件类型配置、内置帮助 |
| Neovim 配置 | `init.lua`、Lua 模块、LSP、Tree-sitter、`vim.pack` |

推荐顺序是“先减少鼠标依赖，再掌握编辑语法，最后配置插件”。把日常重复操作改写为组合命令，
比一次安装大量插件更能提升效率。

## 20. 参考资料

- [Vim 官方文档入口](https://www.vim.org/docs.php)
- [Vim 在线帮助镜像](https://vimhelp.org/)
- [Neovim 官方用户手册](https://neovim.io/doc/user/)
- [Neovim Lua 配置指南](https://neovim.io/doc/user/lua-guide.html)
- [Neovim LSP 文档](https://neovim.io/doc/user/lsp/)
- [Neovim Tree-sitter 文档](https://neovim.io/doc/user/treesitter/)
- [Neovim 健康检查](https://neovim.io/doc/user/health/)
- [Neovim 安装说明](https://neovim.io/doc/install/)

## 21. 延伸阅读

- [[../tmux|Tmux 使用指南]]
- [[bash-basics|Bash 基础]]
- [[../ide-guide|IDE 使用指南]]
