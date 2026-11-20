---
title: Linux 学习笔记
description: Linux 学习笔记总入口，内容已拆分到 linux/ 子目录
tags:
  - linux
---

# Linux Learning Notes

参考：《鸟哥的 Linux 私房菜》

> 详细内容已拆分到 [[04-devtools/linux/index|linux/]] 子目录中，请前往查看。

## 快速导航

- [[bash-basics|Bash 基础]]
- [[ls-command|ls 命令详解]]
- [[find-command|find 命令详解]]
- [[du-command|du 命令详解]]
- [[ln-links|ln 链接用法]]
- [[netstat-ss-command|netstat 与 ss 命令详解]]
- [[user-group-management|用户与用户组管理]]
- [[file-permissions|文件权限管理]]
- [[fhs-directory-layout|FHS 目录配置]]
- [[vim-editor|Vim 与 Neovim 使用手册]]
- [[compression-packaging|文件压缩与打包]]
- [[shell-io-redirection|Shell IO 重定向与管线]]
- [[process-management|进程管理]]
- [[systemctl|systemctl 与 systemd 服务管理]]
- [[supervisord|Supervisor 进程管理]]

## SSH 远程复制

```bash
scp /path/to/local/file username@remote_host:/path/to/remote/directory/
```
