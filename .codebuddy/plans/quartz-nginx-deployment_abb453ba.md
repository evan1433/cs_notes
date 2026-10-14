---
name: quartz-nginx-deployment
overview: 将 Quartz 4.0 生成的静态站点部署到服务器，使用 Nginx 提供服务，并针对纯文档无登录场景制定安全防护方案
todos:
  - id: create-nginx-config
    content: 创建 Nginx 安全加固配置文件（含 HTTPS、安全头、Gzip、SPA 路由、限流）
    status: completed
  - id: create-nginx-subpath-config
    content: 创建子路径部署 Nginx 配置文件（baseUrl=/cs_notes/ 场景）
    status: completed
  - id: create-deploy-script
    content: 创建一键部署脚本（本地构建 + rsync 推送到服务器）
    status: completed
  - id: create-ssl-setup
    content: 创建 SSL 证书安装脚本（Let's Encrypt + 自动续期）
    status: completed
  - id: create-robots-txt
    content: 创建 robots.txt 爬虫控制文件
    status: completed
  - id: update-quartz-config
    content: 可选：修改 quartz.config.ts baseUrl 适配根路径部署，并更新 deploy.yml
    status: completed
---

## 产品概述

将 Quartz 4.0 生成的静态文档站点部署到自有服务器，使用 Nginx 作为 Web 服务器，并针对纯文档无登录场景进行安全加固。

## 核心功能

- 分析纯静态文档网站无登录场景下的安全风险（内容抓取、敏感信息暴露、DDoS、热链等）
- 提供对应的安全防护措施（HTTPS、安全头、限流、访问控制等）
- 编写完整的 Nginx 配置文件（含安全加固、Gzip 压缩、SPA 路由支持）
- 编写一键部署脚本（本地构建 + 传输到服务器）
- 可选：配置 SSL 证书（Let's Encrypt）和自动续期
- 可选：调整 baseUrl 配置以适配自建服务器部署路径

## 技术栈

- **Web 服务器**: Nginx（部署在用户自有 Linux 服务器上）
- **静态站点生成**: Quartz 4.0（已有，`npm run build` 输出到 `public/`）
- **SSL 证书**: Let's Encrypt + Certbot（推荐）
- **部署方式**: SSH + rsync（本地构建后推送到服务器）

## 实现方案

### 整体策略

在本地（或 CI）执行 `npm run build` 生成 `public/` 目录的纯静态文件，通过 rsync 传输到服务器指定目录，由 Nginx 提供静态文件服务。核心工作是编写安全加固的 Nginx 配置和自动化部署脚本。

### 关键技术决策

1. **baseUrl 处理**: 当前 `quartz.config.ts` 中 baseUrl 为 `/cs_notes/`（适配 GitHub Pages）。自建服务器有两种选择：

- 方案 A：部署到根路径 `/`，需修改 baseUrl 为 `/`（推荐，URL 更简洁）
- 方案 B：保持 `/cs_notes/` 子路径部署，Nginx 中对应配置 `location /cs_notes/`
- 计划中提供两种配置，默认推荐方案 A

2. **SPA 路由支持**: Quartz 启用了 `enableSPA: true`，Nginx 需配置 `try_files $uri $uri/ /index.html` 以支持前端路由

3. **安全加固层级**: 分为基础必做（HTTPS、安全头、隐藏版本号）和进阶可选（限流、IP 黑名单、敏感路径访问控制）

### 性能与可靠性

- 启用 Gzip/Brotli 压缩减少传输体积（静态资源压缩率可达 60-70%）
- 配置长期缓存（静态资源 hash 文件名，可设置 1 年缓存）
- Nginx 本身无状态，纯静态服务可靠性极高

## 实现细节

### 安全风险与防护措施

| 风险 | 说明 | 防护措施 |
| --- | --- | --- |
| 内容抓取/爬虫 | 笔记内容被批量爬取 | robots.txt 限制、限流 |
| 敏感内容暴露 | sys-analyst/sys-architect 考试资料公开 | 可选 IP 白名单或 HTTP Basic Auth |
| DDoS/暴力请求 | 大量请求消耗带宽和连接 | Nginx 限流（limit_req/limit_conn） |
| 热链盗用 | 其他网站直接引用资源 | Referer 检查防盗链 |
| 目录列表泄露 | 暴露文件结构 | 关闭 autoindex |
| 中间人攻击 | HTTP 明文传输 | HTTPS + HSTS |
| 服务器信息泄露 | Nginx 版本号暴露 | server_tokens off |
| 点击劫持 | 页面被嵌入 iframe | X-Frame-Options 头 |
| XSS（低风险） | 搜索为纯客户端，风险极低 | CSP 安全头 |
| 源码泄露 | .git 等敏感目录可访问 | Nginx deny 规则 |


### 目录结构

```
cs_notes/
├── deploy/                          # [NEW] 部署相关文件
│   ├── nginx.conf                   # [NEW] Nginx 完整配置文件（安全加固版），包含 HTTPS、安全头、Gzip、SPA 路由、限流、防盗链等配置
│   ├── nginx-subpath.conf           # [NEW] Nginx 子路径部署配置（baseUrl=/cs_notes/ 场景），与 nginx.conf 结构一致但适配子路径
│   ├── deploy.sh                    # [NEW] 一键部署脚本，执行本地构建 + rsync 传输到服务器，支持参数指定服务器地址和路径
│   ├── setup-ssl.sh                 # [NEW] SSL 证书安装脚本，使用 certbot 自动获取 Let's Encrypt 证书并配置自动续期
│   └── robots.txt                   # [NEW] 搜索引擎爬虫控制文件，限制敏感路径的爬取
├── quartz.config.ts                 # [MODIFY] 如选择根路径部署，需将 baseUrl 从 "/cs_notes/" 改为 "/"
└── .github/workflows/deploy.yml     # [MODIFY] 新增自建服务器部署 workflow（可选，保留原 GitHub Pages 部署）
```

### 核心配置要点

- **Nginx 配置**: 监听 80/443 端口，443 配置 SSL，HTTP 自动跳转 HTTPS，SPA fallback，静态资源长缓存，安全响应头
- **部署脚本**: 支持环境变量配置服务器地址，rsync 增量同步，构建前检查 Node.js 版本
- **robots.txt**: 允许搜索引擎爬取公开内容，禁止爬取敏感路径（如 sys-analyst、sys-architect）