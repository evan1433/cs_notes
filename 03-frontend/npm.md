---
title: NPM 包管理器
description: npm 完整技术文档，涵盖镜像源配置、package.json 字段、语义化版本与依赖范围、lockfile 与依赖树、scripts 生命周期、workspaces、安全审计、发包流程、故障排查与最佳实践
tags:
  - npm
  - frontend
  - nodejs
  - package-manager
  - devtools
date: 2026-09-15
aliases:
  - npm
  - node-package-manager
---

# NPM 包管理器

## 概述

npm（Node Package Manager）是 Node.js 的默认包管理器，由三部分组成：

| 组成           | 说明                                                 |
| ------------ | -------------------------------------------------- |
| **CLI**      | `npm` 命令行工具，随 Node.js 一起安装，负责解析依赖、下载、执行脚本          |
| **Registry** | 包仓库服务，默认是 `https://registry.npmjs.org`，可替换为镜像源或私有源 |
| **Website**  | [npmjs.com](https://www.npmjs.com/)，用于搜索、查看包信息与文档  |

它的核心职责是：**根据 `package.json` 解析依赖图 → 从 registry 下载 tarball → 安装到 `node_modules` → 用 `package-lock.json` 锁定结果**。

> 本文结论基于 **npm 10.x**（本地实测 npm 10.9.7 / Node v22.22.2）的行为；npm 7 之后的重大变更会在文中标注。

### Node 与 npm 的版本对应关系

npm 随 Node 一起分发，但两者是独立演进的，可以单独升级 npm。

| Node 版本 | 通常捆绑的 npm |
|-----------|----------------|
| Node 16 | npm 8 |
| Node 18 | npm 9 / npm 10（后期补丁版本升级） |
| Node 20 LTS | npm 10 |
| Node 22 LTS | npm 10.x（22.22.2 实测为 10.9.7） |
| Node 24 | npm 11+ |

npm 11 起提高了 Node 门槛（不再支持 Node 18），升级前需确认运行环境。

---

## 一、安装与版本管理

### 1.1 检查环境

```bash
node -v              # v22.22.2
npm -v               # 10.9.7
npm config get prefix # 全局包安装目录
which npm            # npm 可执行文件位置
```

### 1.2 升级 / 降级 npm

```bash
# 升级到最新稳定版
npm install -g npm@latest

# 升级到指定版本
npm install -g npm@10.9.7

# 回滚（Windows 上 npm 自身被占用的情况较常见）
npm install -g npm@10
```

> npm 11 起官方推荐用 `npm i -g npm@next` 尝鲜预发布版本，生产环境请固定主版本。

### 1.3 Node 版本管理

不要在系统中直接覆盖 Node，使用版本管理器按项目切换：

```bash
# fnm（推荐，Rust 实现，启动快）
brew install fnm
fnm install 22
fnm use 22
fnm default 22

# nvm（使用最广泛）
nvm install 22
nvm use 22
nvm alias default 22
```

项目根目录放 `.nvmrc` 或 `.node-version` 文件锁定版本：

```text
# .nvmrc
22.22.2
```

### 1.4 Corepack：统一团队包管理器

Node 16.9+ 内置 Corepack，可根据 `package.json` 的 `packageManager` 字段**自动切换正确版本的 pnpm/yarn**，避免"你用 npm 我用 pnpm"导致 lockfile 冲突：

```json
{
  "packageManager": "pnpm@9.12.0"
}
```

```bash
corepack enable       # 注入 shim
corepack prepare pnpm@9.12.0 --activate
```

---

## 二、镜像源与 .npmrc 配置

### 2.1 常用镜像源

| 源 | 地址 |
|----|------|
| npm 官方 | `https://registry.npmjs.org/` |
| 淘宝 npmmirror | `https://registry.npmmirror.com/` |
| 腾讯云 | `https://mirrors.cloud.tencent.com/npm/` |
| CNPM | `https://r.cnpmjs.org/` |
| 华为云 | `https://repo.huaweicloud.com/repository/npm/` |
| 私有 Nexus（示例） | `http://192.168.55.12:8001/nexus/repository/npm-all/` |

### 2.2 基础操作

```bash
# 查询当前使用的镜像源
npm get registry

# 设置为淘宝镜像源
npm config set registry https://registry.npmmirror.com/

# 验证设置
npm get registry

# 还原为官方源
npm config set registry https://registry.npmjs.org/
```

### 2.3 其他配置方式

```bash
# 1) 只对本次命令生效（最安全，不污染配置）
npm install --registry=https://registry.npmmirror.com

# 2) 环境变量（CI 中常用）
npm_config_registry=https://registry.npmmirror.com npm install

# 3) 项目级 .npmrc（提交进仓库，团队统一）
#    项目根目录 .npmrc
registry=https://registry.npmmirror.com/
@mycompany:registry=https://npm.mycompany.com/

# 4) 用 nrm 管理多源
npm i -g nrm
nrm ls
nrm use taobao
nrm test            # 测速，选最快的
```

### 2.4 .npmrc 优先级

从高到低，**上层覆盖下层**：

1. 命令行参数：`--registry=...`
2. 环境变量：`npm_config_xxx`
3. 项目级配置：`./.npmrc`（项目根目录）
4. 用户级配置：`~/.npmrc`
5. 全局配置：`$PREFIX/etc/npmrc`
6. npm 内置默认配置

```bash
npm config ls        # 查看生效配置
npm config ls -l     # 查看全部（含默认值）
npm config edit      # 打开用户级 .npmrc 编辑
npm config delete registry
```

### 2.5 私有源与鉴权

`~/.npmrc` 中写入令牌（**不要提交到仓库**，CI 里用环境变量注入）：

```ini
@mycompany:registry=https://npm.mycompany.com/
//npm.mycompany.com/:_authToken=${NPM_TOKEN}
always-auth=true
```

```bash
# 登录 / 查看身份 / 登出
npm login --registry=https://npm.mycompany.com/
npm whoami
npm logout

# 令牌管理
npm token list
npm token create --read-only
npm token revoke <id>
```

### 2.6 高频实用配置项

```ini
; ~/.npmrc 推荐基线
save-exact=false              ; 是否默认锁死精确版本（库项目建议 true）
engine-strict=true            ; engines 不匹配直接报错，而不是警告
fund=false                    ; 安装时不打印赞助信息
audit=true
prefer-offline=true           ; 优先用本地缓存，加快安装
ignore-scripts=false          ; 安全敏感环境可设 true，禁用生命周期脚本
provenance=true               ; 发布时附带来源证明
```

---

## 三、package.json 详解

### 3.1 创建

```bash
npm init            # 交互式
npm init -y         # 全部使用默认值
npm init vite@latest my-app   # 用脚手架初始化（等价于 npm create）
```

### 3.2 核心字段

| 字段 | 作用 |
|------|------|
| `name` | 包名，小写、可含 `-`/`_`；带作用域写 `@scope/name` |
| `version` | 版本号，必须遵循 SemVer |
| `description` | 一句话描述，影响 npm 搜索结果 |
| `keywords` | 搜索关键词数组 |
| `license` | 许可证，如 `MIT`；私有项目用 `UNLICENSED` |
| `private` | 为 `true` 时禁止 `npm publish`，应用项目必填 |
| `main` | CommonJS 入口（旧规范） |
| `module` | ESM 入口（非官方事实标准） |
| `exports` | 现代条件导出，优先级高于 `main`/`module` |
| `types` / `typings` | TypeScript 类型声明入口 |
| `files` | 白名单，只有列出的文件会被发布 |
| `bin` | 可执行文件映射，安装后生成 `node_modules/.bin` 与全局命令 |
| `scripts` | 脚本命令 |
| `engines` | 声明 Node/npm 版本要求 |
| `packageManager` | 声明包管理器及版本（配合 Corepack） |
| `type` | `commonjs`（默认）或 `module`，决定 `.js` 的模块类型 |
| `sideEffects` | 供打包器 tree-shaking 使用 |
| `publishConfig` | 发布相关配置，如 `registry`、`access` |
| `workspaces` | 声明 monorepo 工作区 |
| `overrides` | 强制覆盖传递依赖的版本 |
| `config` | 自定义配置，脚本中通过 `npm_package_config_xxx` 读取 |

完整示例：

```json
{
  "name": "@mycompany/utils",
  "version": "1.4.2",
  "description": "前端通用工具库",
  "license": "MIT",
  "type": "module",
  "sideEffects": false,
  "main": "./dist/index.cjs",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.mjs",
      "require": "./dist/index.cjs"
    },
    "./package.json": "./package.json"
  },
  "files": ["dist", "README.md"],
  "bin": { "my-cli": "./bin/cli.js" },
  "engines": { "node": ">=18", "npm": ">=9" },
  "packageManager": "npm@10.9.7",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "prepublishOnly": "npm run build"
  }
}
```

### 3.3 用 npm pkg 安全修改

避免手改 JSON 出错：

```bash
npm pkg get name version
npm pkg set scripts.lint="eslint ."
npm pkg set exports.".".import="./dist/index.mjs"
npm pkg delete scripts.temp
npm pkg fix           # 自动修正常见错误（如缺 name/version、bin 类型写错）
```

---

## 四、依赖类型与安装

### 4.1 五类依赖对比

| 字段 | 安装条件 | 典型用途 |
|------|----------|----------|
| `dependencies` | 始终安装 | 运行时必需（`react`、`lodash`） |
| `devDependencies` | 默认安装；`--omit=dev` / `NODE_ENV=production` 时跳过 | 构建、测试、类型（`vite`、`vitest`、`typescript`） |
| `peerDependencies` | npm 7+ **自动安装**；不装会造成版本冲突告警 | 插件声明宿主版本（`eslint-plugin` 依赖 `eslint`） |
| `peerDependenciesMeta` | — | 标记某个 peer 依赖为可选（`optional: true`） |
| `optionalDependencies` | 尽力安装，失败不阻断整体安装 | 平台相关加速包（`fsevents`） |
| `bundleDependencies` | 发布时把依赖打进 tarball | 需要离线可用、或依赖被删风险高的场景 |

### 4.2 安装命令速查

```bash
npm install                    # 按 package.json + lockfile 安装全部依赖
npm i                          # 简写
npm ci                         # 严格按 lockfile 安装（CI 首选，见 §6.3）

npm i lodash                   # 写入 dependencies
npm i -D typescript            # 写入 devDependencies（--save-dev）
npm i -O fsevents              # 写入 optionalDependencies
npm i --save-peer react        # 写入 peerDependencies
npm i -E dayjs                 # 精确版本，不加 ^（--save-exact）
npm i -g pnpm                  # 全局安装
npm i lodash@4.17.21           # 指定版本
npm i lodash@^4                # 指定范围
npm i user/repo github:user/repo   # 从 GitHub 安装
npm i ./local-pkg              # 本地路径（会创建符号链接）

npm uninstall lodash           # 卸载（rm / remove / un 同义）
npm update lodash              # 在 semver 范围内升级
npm i lodash@latest            # 直接升到最新（会改 package.json）
npm outdated                   # 列出可升级的包
```

### 4.3 强制覆盖传递依赖：overrides

当某个深层依赖有漏洞或版本不兼容，且不归你维护时，用 `overrides` 强制统一：

```json
{
  "overrides": {
    "semver": "7.6.0",
    "some-pkg": { "lodash": "4.17.21" },
    "a > b > c": "1.0.0"
  }
}
```

| 包管理器 | 字段名 |
|----------|--------|
| npm | `overrides` |
| yarn | `resolutions` |
| pnpm | `pnpm.overrides` |

改完 `overrides` 必须重新生成 lockfile：

```bash
rm -rf node_modules package-lock.json && npm install
```

---

## 五、语义化版本（SemVer）与版本范围

### 5.1 三段式

```text
主版本号.次版本号.修订号   →   MAJOR.MINOR.PATCH  →  2.13.4
```

- **MAJOR**：不兼容的 API 变更
- **MINOR**：向下兼容的功能新增
- **PATCH**：向下兼容的问题修复
- 预发布：`1.0.0-alpha.1`、`2.0.0-beta.3`（同一版本的预发布 < 正式版）

### 5.2 范围符号

| 写法 | 含义 |
|------|------|
| `1.2.3` | 精确匹配 |
| `^1.2.3` | `>=1.2.3 <2.0.0`（**默认行为**）；`^0.2.3` → `>=0.2.3 <0.3.0`；`^0.0.3` → `>=0.0.3 <0.0.4` |
| `~1.2.3` | `>=1.2.3 <1.3.0`；`~1.2` → `>=1.2.0 <1.3.0`；`~1` → `>=1.0.0 <2.0.0` |
| `1.2.x` / `1.x` / `*` | 任意次要/修订版本 / 任意版本 |
| `>=1.2.3 <2.0.0` | 显式区间 |
| `1.2.3 - 2.3.4` | 闭区间，等价于 `>=1.2.3 <=2.3.4` |
| `^1.2.3 \|\| ^2.0.0` | 或关系 |
| `latest` / `next` | dist-tag，而非版本范围 |

> **注意**：带预发布标签的版本（如 `1.2.3-beta.1`）不会被 `^1.2.3` 这类范围自动匹配，除非范围本身也写了预发布标识。

### 5.3 dist-tag

标签是"版本别名"，默认 `latest`：

```bash
npm dist-tag ls lodash
npm view vue versions --json        # 列出所有版本
npm view vite dist-tags --json
npm i vite@beta                     # 安装 beta 标签指向的版本
```

---

## 六、依赖树、node_modules 与 lockfile

### 6.1 安装算法

1. 解析 `package.json` 中的版本范围
2. 从 registry 获取元数据，构建完整依赖图
3. 计算满足所有范围的版本组合（冲突则报 `ERESOLVE`）
4. 下载 tarball 到缓存（`~/.npm/_cacache`）
5. 解压到 `node_modules`，**扁平化**处理：所有能兼容的包尽量提到顶层；版本冲突时才在子目录嵌套安装
6. 写入 `package-lock.json`

### 6.2 扁平化与幽灵依赖

```
node_modules/
├── lodash/            # 顶层（你声明的）
├── typescript/        # 顶层（你声明的 devDep）
└── ms/                # 顶层（被别的包依赖，被提升上来了）
```

`ms` 虽然不在你的 `package.json` 里，但因为被提升到顶层，**你的代码也能 `import 'ms'`** —— 这就是"幽灵依赖"。一旦依赖结构变化，代码就会崩。

- 排查：`npm ls <pkg>` / `npm explain <pkg>`
- 根治：改用 pnpm（默认严格隔离），或给项目加 lint 规则限制导入

### 6.3 package-lock.json

| lockfileVersion | 对应 npm | 特点 |
|-----------------|----------|------|
| 1 | npm 5/6 | 只有 `dependencies` 树 |
| 2 | npm 7/8 | 同时包含 `packages`（新）和 `dependencies`（兼容旧） |
| 3 | npm 9+ | 只有 `packages`，体积更小（**当前默认**） |

它记录了**每个包的精确版本、下载地址、完整性哈希**，保证不同机器装出同一棵树。

**必须提交到版本库**，不要写进 `.gitignore`。

### 6.4 npm install vs npm ci

| 行为 | `npm install` | `npm ci` |
|------|---------------|----------|
| lockfile 缺失 | 生成新的 | **直接报错**（ENOLOCK） |
| package.json 与 lock 不一致 | 更新 lockfile | **直接报错** |
| node_modules | 增量复用 | **先删除再全量安装** |
| 适用场景 | 本地开发 | CI / 构建 / 生产部署 |

```bash
npm ci --omit=dev        # 生产环境只装运行时依赖
```

### 6.5 依赖树查看与瘦身

```bash
npm ls                     # 完整依赖树
npm ls --depth=0           # 只看直接依赖
npm ls lodash              # 某个包出现在哪
npm explain lodash         # 谁依赖了它（等价于 npm why）
npm dedupe                 # 消除重复依赖，合并可共用的版本
npm prune                  # 移除 package.json 中已删除的包
npm query "*:root > #prod" # 用选择器查询（npm query）
```

---

## 七、npm scripts

### 7.1 基础

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run",
    "lint": "eslint . --ext .js,.ts"
  }
}
```

```bash
npm run dev
npm run build
npm test          # test / start / restart / stop 可省略 run
npm start
npm run           # 列出所有可用脚本
```

### 7.2 pre / post 钩子

任意脚本都可以定义前置与后置钩子：

```json
{
  "scripts": {
    "prebuild": "rimraf dist",
    "build": "vite build",
    "postbuild": "node scripts/report.js"
  }
}
```

`npm run build` 会依次执行 `prebuild → build → postbuild`。

### 7.3 完整生命周期

| 脚本 | 触发时机 |
|------|----------|
| `preinstall` / `install` / `postinstall` | 本包被安装时（含 CI 里的 `npm ci`） |
| `preprepare` / `prepare` / `postprepare` | 本地 `npm install`（无参数）时；`npm publish` / `npm pack` 打包前 |
| `prepublishOnly` | **仅** `npm publish` 之前（构建产物的正确位置） |
| `prepack` / `postpack` | 生成 tarball 前后（含安装 git 依赖时） |
| `prepublish`（已废弃） | 不要用，行为混乱 |
| `preversion` / `version` / `postversion` | `npm version` 前后 |
| `prepublishOnly`、`publish` / `postpublish` | 发布前后 |

> 危险提醒：`postinstall` 会在别人装你的包时**自动执行任意代码**，这是供应链攻击的主要入口。发布包时避免在 `postinstall` 中下载或执行远程脚本。

### 7.4 传参

```bash
npm run build -- --watch          # -- 之后的参数透传给脚本
npm run test -- --coverage -u
```

参数会追加到命令末尾：`vite build --watch`。

### 7.5 脚本中的环境变量

npm 自动注入以 `npm_` 开头的变量：

| 变量 | 含义 |
|------|------|
| `npm_package_name` / `npm_package_version` | 包名与版本 |
| `npm_package_json` | package.json 绝对路径 |
| `npm_lifecycle_event` | 当前执行的脚本名 |
| `npm_config_<key>` | 任意 npm 配置项，如 `npm_config_registry` |
| `npm_package_config_<key>` | `package.json` 中 `config` 字段的值 |
| `npm_execpath` | npm 可执行文件路径（跨包管理器调用时用） |

```json
{
  "config": { "port": "3000" },
  "scripts": { "serve": "node server.js --port $npm_package_config_port" }
}
```

### 7.6 并发与串行

```bash
# 串行（按顺序，前一个失败就停）
npm run lint && npm run build

# 并行（跨平台）
npm i -D npm-run-all
npm-run-all --parallel dev api        # run-p 简写
npm-run-all --serial lint test build  # run-s 简写

# 或用 concurrently
npm i -D concurrently
concurrently "npm:dev" "npm:watch:*"
```

### 7.7 跨平台兼容

| 问题 | 方案 |
|------|------|
| `NODE_ENV=production` 在 Windows 不识别 | `npm i -D cross-env` → `cross-env NODE_ENV=production node app.js` |
| `rm -rf dist` 在 Windows 不识别 | `npm i -D rimraf` → `rimraf dist`（npm 10+ 也可 `npm pkg` + Node 的 `fs.rm`） |
| 路径分隔符 | 用 `path.join` / `node:` API，不要手写 `\\` |

---

## 八、npx / npm exec / npm create

```bash
npx vite                    # 本地没有就临时下载并执行
npx vite@5 build            # 指定版本，不污染项目
npx --no-install eslint .   # 只使用本地已安装的，缺失就报错
npx -y create-vue@latest    # 自动确认安装

npm exec -- vite --version  # npm exec 是 npx 的正式命令形式
npm create vite@latest      # 等价于 npm init vite@latest
npm init vue@latest         # 实际去执行 create-vue
```

原理：`npm init <name>` 会被解析为 `npm exec create-<name>`。

> 安全提示：`npx` 会自动下载并执行包，**务必确认包名拼写正确**（typosquatting 攻击常通过相似包名投递恶意代码）。

---

## 九、Workspaces（Monorepo）

npm 7 起内置工作区能力，无需引入 lerna/yarn workspace。

```
monorepo/
├── package.json           # { "private": true, "workspaces": ["packages/*"] }
├── package-lock.json      # 单一 lockfile
└── packages/
    ├── ui/
    ├── utils/
    └── app/
```

根 `package.json`：

```json
{
  "name": "monorepo",
  "private": true,
  "workspaces": ["packages/*"],
  "scripts": {
    "build": "npm run build --workspaces --if-present"
  }
}
```

### 常用命令

```bash
npm i lodash -w @my/utils          # 给指定工作区装依赖
npm i @my/utils -w @my/app         # 工作区间互相依赖（会创建符号链接）
npm run dev -w @my/app             # 在指定工作区执行脚本
npm run build --workspaces         # 在所有工作区执行（-ws）
npm run build -ws --if-present     # 没定义该脚本的工作区跳过
npm run test -w packages/*         # 支持 glob
```

实测效果（npm 10.9.7）：工作区包会以符号链接方式挂到根 `node_modules`：

```text
node_modules/
├── pkg-a -> ../packages/a
└── pkg-b -> ../packages/b
```

> **重要差异**：pnpm / yarn 支持的 `workspace:*` 协议写法，**npm 不支持**，会报 `EUNSUPPORTEDPROTOCOL: Unsupported URL Type "workspace:"`。npm 中工作区互相依赖直接写版本范围（如 `"1.2.0"`）即可，npm 会优先链接到本地工作区。

---

## 十、安全与审计

### 10.1 漏洞审计

```bash
npm audit                    # 查看漏洞报告
npm audit --json             # 机器可读，便于 CI 接入
npm audit --omit=dev         # 只看生产依赖（很多 dev 漏洞不影响线上）
npm audit fix                # 自动修复（在 semver 范围内升级）
npm audit fix --force        # 允许跨主版本升级（可能破坏兼容性，慎用）
npm audit signatures         # 校验已安装包registry 签名与来源
```

### 10.2 常见供应链攻击

| 攻击方式 | 说明 | 防护 |
|----------|------|------|
| Typosquatting | 发布 `lodahs`、`crossenv` 等相似名包 | 安装前核对包名与下载量；启用 `npm audit signatures` |
| 依赖混淆 | 私有包名被抢注到公共 registry | 用 `@scope` + scope 级 registry |
| postinstall 木马 | 安装脚本窃取环境变量、token | `npm i --ignore-scripts`；审查 lockfile 变更 |
| 版本投毒 | 在补丁版本中注入恶意代码 | 锁定精确版本 + 定期 review `npm diff` |
| 账号劫持 | 维护者 token 泄露 | 开启 2FA；使用最小权限 token |

加固配置：

```bash
# CI 中禁用生命周期脚本
npm ci --ignore-scripts

# 只安装某个时间点之前发布的版本（规避新投毒版本）
npm i --before=2026-09-01

# 检查两个版本之间的实际代码差异
npm diff --diff=pkg-a@1.0.0 --diff=pkg-a@1.0.1
```

### 10.3 发布来源证明（Provenance）

在 GitHub Actions 中发布时附带构建来源，npmjs.com 会显示"已验证来源"徽章：

```yaml
# .github/workflows/publish.yml
permissions:
  id-token: write   # 必须，用于 OIDC
  contents: read
steps:
  - run: npm publish --provenance --access public
    env:
      NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## 十一、发布包

### 11.1 发布前自检

```bash
npm pack --dry-run           # 预览将要发布的文件清单，不真正打包
npm pack                     # 生成 tarball，可解压验证内容
npm pkg fix                  # 修正 package.json 常见错误
```

控制发布内容（二选一，**`files` 优先于 `.npmignore`**）：

```json
{ "files": ["dist", "bin", "README.md"] }
```

### 11.2 版本与发布

```bash
# 1) 更新版本（自动打 git tag，需工作区干净）
npm version patch        # 1.4.2 → 1.4.3
npm version minor        # 1.4.2 → 1.5.0
npm version major        # 1.4.2 → 2.0.0
npm version prerelease --preid=beta   # 1.4.2 → 1.4.3-beta.0
npm version 2.0.0-beta.1 --no-git-tag-version   # 手动指定，不打 tag

# 2) 预演
npm publish --dry-run

# 3) 正式发布
npm publish                       # 公共包（scoped 包需 --access public）
npm publish --tag beta            # 发布到 beta 标签，不影响 latest
npm publish --provenance          # 带来源证明

# 4) 推送 git
git push && git push --tags
```

### 11.3 标签管理

```bash
npm dist-tag ls my-pkg
npm dist-tag add my-pkg@1.4.3 latest
npm dist-tag rm my-pkg@1.0.0-beta.1 beta
```

### 11.4 撤销与废弃

```bash
npm deprecate my-pkg@"<1.0.0" "存在安全漏洞，请升级到 1.4.3"
npm unpublish my-pkg@1.0.0     # 仅在发布后 72 小时内允许
npm unpublish my-pkg --force   # 全量下架（需满足 npm 政策，通常会被拒绝）
```

> 已发布的版本**不能覆盖重发同一个版本号**，只能发新版本。公共包下架有严格限制，发版前务必 `npm pack --dry-run` 检查。

### 11.5 本地调试未发布的包

```bash
# 方式一：npm link（全局符号链接）
cd my-lib && npm link            # 注册到全局
cd ../my-app && npm link my-lib  # 链接进来
npm unlink my-lib                # 解除

# 方式二（推荐）：file: 协议，显式可控
npm i ../my-lib                  # 写入 "my-lib": "file:../my-lib"

# 方式三：用本地 tarball
npm i ./my-lib-1.0.0.tgz
```

---

## 十二、缓存与离线安装

```bash
npm cache ls              # 列出缓存内容
npm cache verify          # 校验并清理损坏条目（安全，优先用这个）
npm cache clean --force   # 强制清空（遇到 EINTEGRITY 时的兜底手段）
npm config get cache      # 缓存目录，默认 ~/.npm/_cacache
```

```bash
npm i --prefer-offline    # 优先用缓存，缺失再联网
npm i --prefer-online     # 强制校验远端新鲜度
npm i --offline           # 完全离线，缓存缺包直接失败
```

离线/内网环境可自建私有 registry：

```bash
npm i -g verdaccio        # 轻量级私有 npm 仓库，开箱即用
verdaccio                 # 默认监听 http://localhost:4873
npm set registry http://localhost:4873/
```

---

## 十三、常用命令速查表

| 分类 | 命令 |
|------|------|
| 初始化 | `npm init` / `npm init -y` / `npm create vite@latest` |
| 安装 | `npm i` / `npm ci` / `npm i <pkg>` / `npm i -D <pkg>` / `npm i -g <pkg>` |
| 卸载 | `npm un <pkg>` / `npm un -g <pkg>` |
| 更新 | `npm outdated` / `npm update` / `npm i <pkg>@latest` |
| 查询 | `npm ls` / `npm explain <pkg>` / `npm view <pkg> [field]` / `npm search <kw>` |
| 脚本 | `npm run <script>` / `npm test` / `npm start` / `npm run` |
| 执行 | `npx <cmd>` / `npm exec -- <cmd>` |
| 配置 | `npm config get/set/delete/list/edit` |
| package.json | `npm pkg get/set/delete/fix` |
| 缓存 | `npm cache verify` / `npm cache clean --force` |
| 审计 | `npm audit` / `npm audit fix` / `npm fund` |
| 环境诊断 | `npm doctor` / `npm ping` / `npm whoami` |
| 发布 | `npm version <type>` / `npm publish --dry-run` / `npm dist-tag` |
| 打包 | `npm pack` / `npm pack --dry-run` |
| 维护 | `npm dedupe` / `npm prune` / `npm shrinkwrap` |

`npm shrinkwrap` 会把 `package-lock.json` 转为 `npm-shrinkwrap.json`，**后者会随包发布**，用于库项目锁定依赖树（应用项目直接用 lockfile 即可）。

---

## 十四、故障排查

### 14.1 ERESOLVE —— peer 依赖冲突

```text
npm error code ERESOLVE
npm error Could not resolve dependency:
npm error peer react@"^18.0.0" from @some/ui@1.0.0
```

原因：npm 7+ 会自动安装并校验 peerDependencies，两个包要求了不兼容的宿主版本。

```bash
# 方案 1：查明冲突来源
npm explain react

# 方案 2：用 overrides 统一（推荐，可复现）
# package.json
{ "overrides": { "react": "18.3.1" } }

# 方案 3：临时绕过（不推荐长期使用）
npm i --legacy-peer-deps     # 忽略 peer 依赖自动安装
npm i --force                # 忽略所有冲突
```

### 14.2 ETARGET / E404 —— 找不到包或版本

```bash
npm config get registry                  # 大概率是镜像源不同步/混用
npm view <pkg> versions --json           # 确认源上到底有哪些版本
npm i --registry=https://registry.npmjs.org   # 换官方源重试
npm cache clean --force && npm i         # 清缓存后重试
```

### 14.3 EACCES —— 全局安装权限不足

不要把 npm 目录 `chmod 777`，正确做法是改全局前缀到用户目录：

```bash
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

### 14.4 ELIFECYCLE —— 脚本执行失败

```text
npm error code ELIFECYCLE
npm error command failed: node scripts/build.js
```

说明脚本进程以非 0 退出。排查：

```bash
npm run build --loglevel=verbose   # 打印详细日志
node scripts/build.js              # 脱离 npm 直接跑，看真实报错
```

常见原因：`postinstall` 缺少编译工具链、内存不足、脚本路径错误。

### 14.5 gyp ERR / node-gyp 编译失败

原生模块（`node-sass`、`bcrypt`、`canvas`、`sharp`）需要本地编译：

```bash
# macOS
xcode-select --install

# Windows（管理员 PowerShell）
npm i -g windows-build-tools
# 或安装 Visual Studio Build Tools 并勾选 "Desktop development with C++"

# 通用：指定 Python
npm config set python /usr/bin/python3
```

优先选择提供预编译二进制（`prebuild-install`）的替代包，可彻底避开编译。

### 14.6 EINTEGRITY —— 完整性校验失败

```bash
npm cache verify
rm -rf node_modules package-lock.json
npm install
```

### 14.7 EBADENGINE —— Node 版本不满足

```text
npm WARN EBADENGINE Unsupported engine { required: { node: '>=20' } }
```

升级 Node，或在 `~/.npmrc` 设 `engine-strict=true` 将其从警告变为错误（防止误部署）。

### 14.8 网络类错误

| 错误 | 原因 | 处理 |
|------|------|------|
| `ETIMEDOUT` / `ESOCKETTIMEDOUT` | 网络慢、被墙 | 换镜像源；调大 `fetch-timeout` |
| `ENOTFOUND` | registry 域名解析失败 | 检查网络/代理 |
| `CERT_HAS_EXPIRED` | 证书过期或企业代理中间人证书 | `npm config set strict-ssl false`（临时）或配置 `cafile` |
| `UNABLE_TO_VERIFY_LEAF_SIGNATURE` | 代理证书未信任 | `npm config set cafile /path/to/corp-ca.pem` |

公司网络走代理：

```bash
npm config set proxy http://127.0.0.1:7890
npm config set https-proxy http://127.0.0.1:7890
npm config delete proxy        # 取消
```

---

## 十五、npm vs yarn vs pnpm vs bun

| 维度 | npm | yarn (Berry) | pnpm | bun |
|------|-----|--------------|------|-----|
| 安装速度 | 中 | 中 | 快 | 最快 |
| 磁盘占用 | 高（每项目一份） | 高 | 低（硬链接 + 内容寻址全局存储） | 低 |
| 依赖隔离 | 扁平化，有幽灵依赖 | 扁平化 / PnP | **严格**，无幽灵依赖 | 扁平化 |
| lockfile | `package-lock.json` | `yarn.lock` | `pnpm-lock.yaml` | `bun.lockb` |
| workspaces | 支持（`workspace:` 协议不支持） | 支持 | 支持（`workspace:*`） | 支持 |
| 覆盖依赖 | `overrides` | `resolutions` | `pnpm.overrides` | `overrides` |
| 生态兼容 | 最好（默认自带） | 好 | 好（部分老包需 `shamefully-hoist`） | 较好 |
| 学习成本 | 低 | 中 | 中 | 低 |

**选型建议**：

- 小项目、团队协作、希望零配置 → **npm**（Node 自带，最省心）
- 大型 monorepo、磁盘/速度敏感 → **pnpm**
- 追求极致安装速度的新项目 → **bun**（注意运行时兼容性）
- 已有 yarn 工程 → 保持现状，不要混用

> **铁律**：一个项目只用一种包管理器。混用会产生多份 lockfile、依赖树不一致、幽灵依赖等难以排查的问题。可在 `package.json` 声明 `packageManager` + Corepack 强制统一，或用 `only-allow` 在 `preinstall` 阶段拦截。

---

## 十六、最佳实践

### 依赖管理

1. **提交 lockfile**，CI 用 `npm ci` 而非 `npm install`
2. 应用项目锁精确版本或至少锁 minor（`"vite": "~5.4.0"`）
3. 库项目用宽范围 `^` + `peerDependencies`，避免与宿主冲突
4. 定期 `npm outdated` + `npm audit --omit=dev`，不要一次性全量升级
5. 删除依赖后运行 `npm prune`，别只改 `package.json`
6. 一个项目只用一个包管理器，用 `packageManager` 字段锁定

### scripts

7. 构建产物逻辑放 `prepublishOnly`，不要放 `prepare`（后者本地 install 也会跑）
8. 用 `cross-env`、`rimraf` 保证跨平台
9. 长命令拆成脚本文件，`scripts` 里只写调用
10. 传参用 `--`，不要拼字符串

### 安全

11. 不把 token 写进仓库，CI 用 secrets 注入
12. 发布开启 2FA，用 `--provenance`
13. 谨慎安装来路不明的包，注意拼写相近的包名
14. 审查 lockfile 中新增的 `resolved` 地址，防止依赖被劫持到陌生域名
15. 生产安装加 `--omit=dev --ignore-scripts`（确认无原生模块时）

### 工程化

16. `node_modules`、`.npmrc`（含 token 时）进 `.gitignore`
17. 用 `engines` + `.nvmrc` 锁定 Node 版本
18. 应用项目设 `"private": true`，防止误发布
19. 库项目用 `files` 白名单控制发布体积
20. 镜像源配置写进项目 `.npmrc` 并注明，避免团队成员各自不同源

---

## 参考

- [npm 官方文档](https://docs.npmjs.com/)
- [npm CLI 命令参考](https://docs.npmjs.com/cli/v10/commands)
- [package.json 字段说明](https://docs.npmjs.com/cli/v10/configuring-npm/package-json)
- [SemVer 规范](https://semver.org/lang/zh-CN/)
- [npmmirror 镜像站](https://npmmirror.com/)
- [npm 博客与变更日志](https://github.com/npm/cli/releases)
- [[vite|Vite 构建工具]]
- [[es6|ES6]]
