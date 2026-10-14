---
title: Vite 构建工具
description: Vite 的工作机制、CLI 与配置、资源与 CSS 处理、插件体系，以及环境变量与模式（mode）的完整实践
tags:
  - frontend
  - vite
  - build-tools
  - bundler
  - npm
date: 2026-09-15
aliases:
  - vite-env-mode
  - vite-env-and-modes
---

# Vite 构建工具

## 概述

Vite（法语"快"，读作 `/vit/`）是一个基于原生 ESM 的前端构建工具，由 Vue 作者尤雨溪发起。它的核心思路是把"开发"和"构建"拆成两条完全不同的路径：

- **开发期不打包**。浏览器通过 `import` 直接请求源文件，Vite 按需转换并发回，冷启动只跟入口依赖数量有关，项目规模再大也不明显变慢。
- **生产构建才打包**。由 Rolldown 完成 tree-shaking、压缩、代码分割，产出可部署的静态资源。

Vite 8 的关键变化（本文所有结论基于 **Vite 8.3.0** 实测）：

| 环节 | 过去 | Vite 8 |
|------|------|--------|
| 生产打包 | Rollup | **Rolldown** |
| 依赖预构建 | esbuild | **Rolldown** |
| TS/JSX 转换 | esbuild | **Oxc Transformer** |
| CSS 压缩 | esbuild | **Lightning CSS** |
| 打包选项 | `build.rollupOptions` | `build.rolldownOptions` |
| 压缩器 | `esbuild` | `oxc`（`--minify` 默认值） |

因为底层换成了 Rust 实现的 Rolldown + Oxc，Vite 8 里已经没有 `esbuild` 依赖，配置项 `esbuild` 被标记为 **Deprecated**，改名为 `oxc`（内部做转换，旧字段仍可用但会提示）。

**适合的场景**：SPA、MPA、组件库、Node 服务端代码，以及几乎所有现代前端框架（Vue/React/Svelte/Solid）的默认脚手架。

**不太适合**：需要输出多 chunk 且对产物结构有极强控制欲的老项目（Rollup 生态插件有部分尚未迁移到 Rolldown）、以及必须兼容 IE11 这类老浏览器的项目（需 `@vitejs/plugin-legacy` 兜底）。

## 一、安装与快速上手

### 1.1 用脚手架创建项目

```bash
# 交互式选择模板（Vue / React / Svelte / Solid / Vanilla ...）
npm create vite@latest my-app

# 直接指定模板
npm create vite@latest my-app -- --template vue-ts
cd my-app && npm install && npm run dev
```

### 1.2 手动最小工程

Vite 项目没有强制的目录结构，只要有 `index.html` 和 `package.json` 就能跑：

```text
my-vite-app/
├── index.html          # 唯一入口，必须在项目根目录
├── package.json
├── vite.config.ts      # 可选
└── src/
    ├── main.js
    └── styles.css
```

```json
{
  "name": "my-vite-app",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "vite": "^8.3.0"
  }
}
```

```html
<!-- index.html：Vite 的构建入口，而不是 src/main.js -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="stylesheet" href="/src/styles.css" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

> **与 webpack 最大的差异**：入口是 `index.html` 本身。Vite 会扫描 HTML 里的 `<script type="module" src>`、`<link href>`、`<img src>` 等引用并纳入构建图，所以"HTML 里直接写相对路径"就是天然的入口声明。

## 二、CLI 命令与常用参数

| 命令 | 作用 | 默认端口/目录 |
|------|------|--------------|
| `vite` / `vite dev` / `vite serve` | 启动开发服务器（三者等价） | `5173` |
| `vite build` | 生产构建 | 输出 `dist/` |
| `vite preview` | 本地预览构建产物，**不要用于线上** | `4173` |
| `vite optimize` | 手动预构建依赖（已废弃，进程自动完成） | — |

常用参数：

| 参数                        | 适用命令          | 说明                                         |
| ------------------------- | ------------- | ------------------------------------------ |
| `-m, --mode <mode>`       | 全部            | 设置模式，决定加载哪个 `.env` 文件                      |
| `--host [host]`           | dev / preview | 暴露到局域网（`--host 0.0.0.0`）                   |
| `--port <port>`           | dev / preview | 指定端口                                       |
| `--strictPort`            | dev / preview | 端口被占用时直接失败，而不是自动换端口                        |
| `--open [path]`           | dev / preview | 启动后自动打开浏览器                                 |
| `--force`                 | dev           | 忽略缓存重新预构建依赖                                |
| `--base <path>`           | dev / build   | 公共基础路径，默认 `/`                              |
| `--outDir <dir>`          | build         | 输出目录，默认 `dist`                             |
| `--target <target>`       | build         | 转译目标，默认 `baseline-widely-available`        |
| `--minify [minifier]`     | build         | 默认 `oxc`，可选 `terser` / `esbuild` / `false` |
| `--sourcemap [output]`    | build         | 默认 `false`，可 `inline` / `hidden`           |
| `--manifest [name]`       | build         | 输出构建清单 JSON，供后端模板集成                        |
| `-w, --watch`             | build         | 文件变化时重新构建                                  |
| `-c, --config <file>`     | 全部            | 指定配置文件                                     |
| `--configLoader <loader>` | 全部            | `bundle`（默认）\| `runner` \| `native`        |
| `--profile [name]`        | 全部            | 生成 `.cpuprofile` 性能分析文件                    |

```bash
# 局域网调试 + 固定端口
vite --host 0.0.0.0 --port 8080 --strictPort

# 带 sourcemap 的预发布构建
vite build --mode staging --sourcemap --outDir dist-staging

# 分析启动性能瓶颈
vite --profile
```

## 三、开发服务器：原生 ESM 与 HMR

### 3.1 裸模块导入的处理

浏览器不认识 `import { ref } from 'vue'` 这种裸模块说明符，Vite 做了两件事：

1. **预构建（pre-bundle）**：用 Rolldown 把 CommonJS/UMD 依赖转成 ESM，并把零散的小模块合并成单个文件，减少 HTTP 请求数；
2. **重写导入路径**：把 `'vue'` 改写成 `/node_modules/.vite/deps/vue.js?v=f3sf2ebd`。

预构建结果缓存在 `node_modules/.vite`（可通过 `cacheDir` 修改）。`--force` 可以强制忽略缓存重新构建。

### 3.2 HMR

Vite 提供基于原生 ESM 的 HMR API，模块自己声明如何被热替换：

```js
// counter.js
export let count = 0
export function increment() { count++ }

if (import.meta.hot) {
  // 接受自身更新：新模块替换旧模块，回调里拿新导出
  import.meta.hot.accept((newModule) => {
    console.log('count 被替换为', newModule.count)
  })

  // 模块被销毁时清理副作用（定时器、事件监听、socket）
  import.meta.hot.dispose((data) => {
    clearInterval(data.timerId)
  })
}
```

框架场景不用手写：`@vitejs/plugin-vue`、`@vitejs/plugin-react` 已把 HMR 接好。若某模块没有声明 `accept`，Vite 会沿依赖链向上查找接受者，找不到就整页刷新。

### 3.3 冷启动实测

```text
 VITE v8.3.0  dev  ready in 70 ms
 ➜  Local:   http://localhost:5173/
 ➜  Network: use --host to expose
```

小工程启动在 100ms 内，且启动时间与项目总文件数无关——这是"不打包"换来的直接收益。

## 四、配置文件 `vite.config.ts`

### 4.1 三种写法

```ts
// 1. 基础对象
import { defineConfig } from 'vite'

export default defineConfig({
  server: { port: 5173 },
})
```

```ts
// 2. 函数形式：根据 command / mode 返回不同配置
import { defineConfig } from 'vite'

export default defineConfig(({ command, mode, isSsrBuild, isPreview }) => {
  if (command === 'serve') {
    return { server: { port: 5173 } }   // 开发
  }
  return { build: { sourcemap: true } } // 构建（command === 'build'）
})
```

```ts
// 3. 异步形式：需要读文件、拉远程配置时
export default defineConfig(async ({ mode }) => {
  const config = await loadRemoteConfig(mode)
  return { define: { __REMOTE__: JSON.stringify(config) } }
})
```

> `command` 的值只有 `serve` 和 `build` 两种；`isSsrBuild` / `isPreview` 可能为 `undefined`，所以要用 `=== true` 显式判断。

### 4.2 常用配置项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `root` | `process.cwd()` | 项目根目录（`index.html` 所在处） |
| `base` | `/` | 公共基础路径，子路径部署必改 |
| `mode` | serve 为 `development`，build 为 `production` | 会同时覆盖两条命令的默认模式 |
| `define` | — | 全局常量替换，值需可 JSON 序列化 |
| `plugins` | `[]` | 插件数组，支持嵌套数组与 Promise |
| `publicDir` | `"public"` | 静态资源目录，原样拷贝到产物根，不做 hash |
| `cacheDir` | `"node_modules/.vite"` | 预构建缓存目录 |
| `resolve.alias` | — | 路径别名，**值必须是绝对路径** |
| `resolve.extensions` | `['.mjs','.js','.mts','.ts','.jsx','.tsx','.json']` | 省略扩展名时的尝试顺序 |
| `resolve.tsconfigPaths` | `false` | 是否启用 tsconfig 的 `paths` |
| `envDir` | `root` | `.env` 文件所在目录，`false` 表示禁用 |
| `envPrefix` | `VITE_` | 暴露给客户端的前缀，**设为 `''` 会直接报错** |
| `appType` | `'spa'` | `spa` \| `mpa` \| `custom` |
| `css.transformer` | `'postcss'` | 可切到 `'lightningcss'` |
| `json.namedExports` | `true` | 支持 `import { field } from './x.json'` |
| `json.stringify` | `'auto'` | 文件大于 10kB 时转成 `JSON.parse("...")`，性能更好 |
| `clearScreen` | `true` | 日志时是否清屏 |

### 4.3 路径别名：两种方案

```ts
// 方案 A：resolve.alias（推荐，Vite 原生）
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
```

```ts
// 方案 B：复用 tsconfig.json 的 paths，避免两处维护
export default defineConfig({
  resolve: { tsconfigPaths: true },
})
```

方案 B 的注意点：`paths` 只对 `tsconfig.json` 的 `files`/`include` 匹配到的文件生效，`include: ["src"]` **不会**匹配 CSS 文件，需要在 include 里显式加 `"src/**/*.css"`；另外 `.less` 文件不支持该特性，得用 `resolve.alias`。

### 4.4 配置文件加载与调试

Vite 8 默认用 Rolldown 把配置文件打包成临时文件再加载（`--configLoader bundle`，临时文件写在 `node_modules/.vite-temp`）。这样一来 `vite.config.ts` 里的断点会映射到打包产物，调试体验差。配合 VS Code 断点调试时改用原生加载：

```bash
vite --configLoader native   # 需要 Node 22.18+，直接执行 TS 源文件
```

## 五、静态资源处理

### 5.1 导入即得 URL

```js
import logoUrl from './assets/logo.svg'

document.getElementById('logo').src = logoUrl
```

小于 `build.assetsInlineLimit`（默认 **4096 字节**）的资源会被内联成 base64 data URI，想彻底禁用内联设为 `0`。

### 5.2 public 目录 vs import

| 方式 | 处理 | 适用 |
|------|------|------|
| `public/` 目录 | 原样拷贝到产物根目录，**不做 hash、不压缩** | `robots.txt`、`favicon.ico`、需要固定 URL 的文件 |
| `import` 引入 | 参与构建，产物名带 hash，自动处理 `base` | 业务图片、字体、需要缓存失效控制的资源 |

### 5.3 查询后缀（Import suffixes）

```js
import assetUrl from './asset.js?url'            // 强制作为 URL 处理
import shaderSource from './shader.glsl?raw'     // 以字符串读入文件内容
import styles from './bar.css?inline'            // 只取 CSS 文本，不注入页面
import Worker from './worker.js?worker'          // 得到 Worker 构造器
import InlineWorker from './worker.js?worker&inline' // 内联为 base64
import workerUrl from './worker.js?worker&url'   // 只要 URL
```

推荐用标准写法创建 Worker，浏览器和构建工具都能识别：

```js
const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' })
```

### 5.4 JSON、glob 导入与动态导入

```js
// JSON：支持命名导入，便于 tree-shaking
import config from './config.json'
import { apiBase } from './config.json'

// import.meta.glob：编译期把目录下所有匹配文件变成懒加载映射
const pages = import.meta.glob('./pages/*.js')
// => { './pages/home.js': () => import('./pages/home.js'), ... }

const eagerPages = import.meta.glob('./pages/*.js', { eager: true })

// 注意：glob 的参数必须是字面量，不能用变量拼接
```

```js
// 动态导入：变量只能代表一层文件名，必须带扩展名，必须以 ./ 或 ../ 或 # 开头
const name = 'home'
const mod = await import(`./pages/${name}.js`)   // ✅
```

## 六、CSS 处理

| 能力 | 说明 |
|------|------|
| 普通 CSS | `import './a.css'` 通过 `<style>` 注入页面并支持 HMR |
| `@import` 内联 | 内置 `postcss-import`，`url()` 引用会自动重定位（rebasing） |
| PostCSS | 存在有效配置（`postcss.config.js`）时自动启用 |
| CSS 压缩 | 生产构建由 **Lightning CSS** 完成，目标由 `build.cssTarget` 控制 |
| CSS Modules | 文件名以 `.module.css` 结尾 |
| 预处理器 | 内置支持 `.scss/.sass/.less/.styl/.stylus`，但需自行安装对应依赖 |

```js
// CSS Modules
import classes from './example.module.css'
document.getElementById('foo').className = classes.red
```

```css
/* example.module.css */
.red { color: red; }
```

开启驼峰命名后可以用命名导入：

```js
export default defineConfig({
  css: {
    modules: { localsConvention: 'camelCaseOnly' },
  },
})
```

预处理器相关配置：

```ts
export default defineConfig({
  css: {
    // sass-embedded 比 sass 快，建议安装它
    preprocessorOptions: {
      scss: {
        // 向每个 scss 文件注入变量；只放变量，放样式会被重复打包
        additionalData: `$brand: #ff6a00;`,
      },
    },
    devSourcemap: true, // 开发期 CSS sourcemap，默认 false
  },
})
```

> 预处理器依赖单独安装：`npm add -D sass-embedded` / `less` / `stylus`。
> 需要把 CSS 当字符串用而不注入页面时，用 `?inline`；Vite 5 起已移除 CSS 的默认导出。

## 七、TypeScript 支持

Vite 只做**转译**，不做类型检查——Oxc 丢掉了类型信息，换来 `<50ms` 级别的转换速度。

```jsonc
// package.json：类型检查交给 tsc
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "build": "npm run typecheck && vite build"
  }
}
```

需要在 dev 期间实时看到类型错误，用 `vite-plugin-checker` 或 `tsc --noEmit --watch`。

关键约定：

- `isolatedModules` 应设为 `true`（Oxc 逐文件转译，没有全局类型信息）；
- **`tsconfig.json` 里的 `target` 会被 Vite 忽略**：开发期用 `oxc.target`（默认 `esnext`），构建期用 `build.target`（优先级更高）；
- 类型导入请用 `import type { Foo } from './types'`，避免被当成运行时导入保留；
- 在 `tsconfig.json` 的 `compilerOptions.types` 里加 `"vite/client"`（或在 `src/vite-env.d.ts` 写 `/// <reference types="vite/client" />`）才能获得创建 `import.meta.env` 的类型；
- `resolve.tsconfigPaths: true` 才会启用 `paths` 别名。

```ts
// vite-env.d.ts
/// <reference types="vite/client" />

// 自定义 VITE_ 变量的类型提示（文件内不要出现 import 语句，否则类型增强失效）
interface ImportMetaEnv {
  readonly VITE_API_BASE: string
  readonly VITE_APP_TITLE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// define 注入的全局常量也要声明
declare const __APP_VERSION__: string
```

## 八、环境变量与模式（Mode）

这一章是 Vite 项目配置里最容易出错的部分，涉及"npm 参数透传"和"mode 决定加载哪个 env 文件"两层机制。

### 8.1 快速上手：让 Vite 读取 `.env.dev`

```bash
# npm —— 必须加 -- 分隔符
npm run dev -- --mode dev

# pnpm —— 必须【不加】--
pnpm dev --mode dev

# yarn —— 两种写法都可以
yarn dev --mode dev
```

### 8.2 为什么这是最容易踩的坑

`npm run <script>` 后面的参数默认会被 **npm 自己**解析，要用 `--` 声明"后面的参数归脚本"。而 pnpm/yarn 的设计是"脚本名之后的参数全部转发"，加了 `--` 反而会把字面量 `--` 一起传下去——Vite 的 CLI 解析器遇到 `--` 会**停止解析后续选项**。

实测（本机 npm 10.9.7 / pnpm 12.4.1 / yarn 1.22.21，脚本为 `"build": "vite build"`，由 `vite.config` 打印实际 mode）：

| 命令 | 实际 mode | 结果 |
|------|----------|------|
| `npm run build -- --mode dev` | `dev` | ✅ |
| `npm run build --mode dev`（漏 `--`） | `production` | ❌ `--mode` 被 npm 吞掉 |
| `pnpm build --mode dev` | `dev` | ✅ |
| `pnpm build -- --mode dev` | `production` | ❌ **静默失效** |
| `yarn build --mode dev` | `dev` | ✅ |
| `yarn build -- --mode dev` | `dev` | ✅ yarn 1 会剥掉首个 `--` |

脚本实际收到的参数（用打印 `process.argv` 的脚本验证）：

| 命令 | 脚本收到的参数 |
|------|---------------|
| `npm run dev -- --mode dev` | `["--mode", "dev"]` |
| `npm run dev --mode dev` | `["dev"]` |
| `pnpm dev --mode dev` | `["--mode", "dev"]` |
| `pnpm dev -- --mode dev` | `["--", "--mode", "dev"]` |
| `yarn dev --mode dev` / `yarn dev -- --mode dev` | `["--mode", "dev"]` |

> **最危险的是 pnpm 那一行**：命令不报错，只是悄悄用了默认模式，于是读到了生产配置。开发服务器上表现为"变量是旧的"，构建时表现为"打进了错误环境的地址"。

**从根上规避**：把模式固化进脚本，调用时就不再需要传参，也就不存在包管理器差异：

```jsonc
{
  "scripts": {
    "dev": "vite",                          // 默认 development，读 .env.development
    "dev:dev": "vite --mode dev",           // 读 .env.dev
    "build": "vite build",                  // 默认 production
    "build:staging": "vite build --mode staging"
  }
}
```

### 8.3 默认 mode 与 `NODE_ENV` 的区别

mode 只决定**加载哪个 `.env` 文件**；`NODE_ENV` 决定 `import.meta.env.PROD` / `DEV`，以及是否走生产压缩与 tree-shaking。两者是独立概念：

| 命令 | `NODE_ENV` | mode |
|------|-----------|------|
| `vite build` | `production` | `production` |
| `vite build --mode development` | `production` | `development` |
| `NODE_ENV=development vite build` | `development` | `production` |
| `NODE_ENV=development vite build --mode development` | `development` | `development` |

| 环境 | `import.meta.env.PROD` | `import.meta.env.DEV` |
|------|------------------------|-----------------------|
| `NODE_ENV=production` | `true` | `false` |
| `NODE_ENV=development` | `false` | `true` |
| `NODE_ENV=其他值` | `false` | `true` |

| 命令 | `import.meta.env.MODE` |
|------|------------------------|
| `--mode production` | `"production"` |
| `--mode development` | `"development"` |
| `--mode staging` | `"staging"` |

想让某个 mode 走开发构建，可以在该 mode 的 env 文件里写 `NODE_ENV=development`。命令行直接写 `NODE_ENV=...` 的好处是 Vite 能**尽早**读到它——因为 `.env` 文件必须等配置求值完成后才加载。

### 8.4 `.env` 文件的加载与优先级

```text
.env                # 所有模式都加载
.env.local          # 所有模式都加载，应被 git 忽略
.env.[mode]         # 仅在指定 mode 下加载
.env.[mode].local   # 仅在指定 mode 下加载，应被 git 忽略
```

优先级从高到低：

1. **进程已有的环境变量**（如 `VITE_X=1 vite build`）
2. `.env.[mode].local`
3. `.env.[mode]`
4. `.env.local`
5. `.env`

实测（`.env` 提供 `VITE_APP_TITLE=Base App` / `VITE_API_HOST=api.example.com`，`.env.dev` 覆盖标题，`.env.dev.local` 覆盖 host）：

```text
$ vite build --mode dev
CFG_MODE>>> dev
LOADED>>> {"TITLE":"Dev App","HOST":"dev-api.local"}
#          ↑ .env.dev      ↑ .env.dev.local

$ vite build
CFG_MODE>>> production
LOADED>>> {"TITLE":"Base App","HOST":"api.example.com"}   # 回落到通用 .env

$ VITE_APP_TITLE=CLI_App vite build --mode dev
LOADED>>> {"TITLE":"CLI_App","HOST":"dev-api.local"}       # 命令行优先级最高
```

开发服务器同样遵守这套规则，且 HTML 里的常量在 dev 期间就已被替换：

```text
$ vite --mode dev
<h1>Dev App</h1>        # index.html 里的 %VITE_APP_TITLE%
```

> `.env` 文件只在 Vite 启动时读取，**修改后必须重启服务**。
> 记得把 `*.local` 加进 `.gitignore`。

相关配置：

```ts
export default defineConfig({
  envDir: './env',                    // .env 目录，默认项目根目录；false 表示禁用
  envPrefix: ['VITE_', 'APP_'],       // 自定义前缀，默认仅 'VITE_'
})
```

> `envPrefix` 设为 `''` 会暴露**所有**变量，Vite 8 检测到该值会**直接抛错**，不再只是警告。要暴露单个无前缀变量，用 `define` 显式注入。

### 8.5 `VITE_` 前缀与客户端暴露

```ini
# .env
VITE_SOME_KEY=123
DB_PASSWORD=foobar
```

```js
console.log(import.meta.env.VITE_SOME_KEY) // "123"
console.log(import.meta.env.DB_PASSWORD)   // undefined
```

三条规则：

1. **值一律是字符串**。`VITE_PORT=3000` 拿到的是 `"3000"`，需要 `Number()` 转换；布尔值同理。
2. **`VITE_` 变量不能放密钥**。它们在构建期被内联进产物，任何人打开 JS 文件都能看到。密钥应在后端或 serverless/edge 函数中下发。
3. **dev 与 build 的替换语义不同**（实测 Vite 8）：

```text
# 开发期：Vite 在每个模块顶部注入一行真实的对象字面量
import.meta.env = {"BASE_URL":"/","DEV":true,"MODE":"dev","PROD":false,"SSR":false,"VITE_APP_TITLE":"Dev App"};
console.log("MODE =", import.meta.env.MODE, "| TITLE =", import.meta.env.VITE_APP_TITLE)
```

```text
# 构建期：静态成员访问被内联成字面量（可被 tree-shaking 裁剪）
console.log(`静态访问:`,`Dev App`)

# 构建期：动态 key 访问会把整个 env 对象内联进产物，运行时才求值
console.log(`动态访问:`,{BASE_URL:`/`,DEV:!1,MODE:`dev`,PROD:!0,SSR:!1,VITE_APP_TITLE:`Dev App`}[key])
```

也就是说 `import.meta.env[key]` 这类动态访问**能工作**，代价是**所有 `VITE_` 变量都会被塞进产物**，既失去了按需裁剪，也扩大了泄露面。要按需保留就用静态成员访问 `import.meta.env.VITE_XXX`。

### 8.6 在 `vite.config` 中读取环境变量

配置求值时 `.env` 还没加载（因为加载哪些文件取决于 `root`、`envDir`、`mode` 等配置项本身），所以 `vite.config` 里读不到 `.env` 的值，必须显式调用 `loadEnv`：

```ts
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // 第三个参数传 '' 表示加载全部变量，不受 VITE_ 前缀限制
  const env = loadEnv(mode, process.cwd(), '')

  return {
    server: {
      port: env.APP_PORT ? Number(env.APP_PORT) : 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    define: {
      // 把无前缀变量显式暴露给客户端（谨慎：会进产物）
      __APP_ENV__: JSON.stringify(env.APP_ENV),
    },
  }
})
```

如果只需要把 `.env` 的值传给业务代码，配置里什么都不用写——Vite 会自动加载并通过 `import.meta.env` 暴露。

### 8.7 HTML 中的常量替换

```html
<h1>Vite is running in %MODE%</h1>
<p>API: %VITE_API_BASE%</p>
```

不存在的常量（如 `%NON_EXISTENT%`）会被原样保留、不做替换；而 JS 中访问 `import.meta.env.NON_EXISTENT` 会得到 `undefined`。

## 九、构建与产物

### 9.1 默认构建行为

```bash
$ vite build
dist/index.html                0.13 kB │ gzip: 0.13 kB
dist/assets/index-BV0OlOky.js  0.87 kB │ gzip: 0.52 kB
✓ built in 13ms
```

| 项 | 默认值 |
|----|--------|
| 输出目录 | `dist` |
| 资源目录 | `dist/assets` |
| 内联阈值 | 4096 字节 |
| 压缩器 | `oxc` |
| sourcemap | `false` |
| 浏览器目标 | Baseline Widely Available：Chrome/Edge ≥ 111、Firefox ≥ 114、Safari ≥ 16.4 |

`build.target` 最低可设 `es2015`，但即便设得更低，Vite 仍要求 Chrome ≥ 64 / Firefox ≥ 67 / Safari ≥ 11.1 / Edge ≥ 79，因为它依赖原生 ESM 动态导入与 `import.meta`。**Vite 只做语法转换，不含 polyfill**；需要兼容更老的浏览器，用 `@vitejs/plugin-legacy`。

### 9.2 多页应用

```ts
import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    rolldownOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        nested: resolve(import.meta.dirname, 'nested/index.html'),
      },
    },
  },
})
```

> HTML 入口的 key 名会被忽略，Vite 按文件解析后的 id 决定产物目录结构，以保持与 dev server 一致。若配置了 `root`，`resolve` 的第一个参数要补上 `root`。

### 9.3 库模式

```ts
import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    lib: {
      entry: resolve(import.meta.dirname, 'lib/main.js'),
      name: 'MyLib',
      fileName: 'my-lib',       // 扩展名由 Vite 自动补
    },
    rolldownOptions: {
      external: ['vue'],        // 不要把框架打进来
      output: { globals: { vue: 'Vue' } },
    },
  },
})
```

单入口产出 `es` + `umd`，多入口产出 `es` + `cjs`，格式可通过 `build.lib.formats` 调整。若库里有 CSS，会额外产出 `dist/my-lib.css`，需要在 `package.json` 的 `exports` 中单独暴露：

```json
{
  "name": "my-lib",
  "type": "module",
  "files": ["dist"],
  "main": "./dist/my-lib.umd.cjs",
  "module": "./dist/my-lib.js",
  "exports": {
    ".": {
      "import": "./dist/my-lib.js",
      "require": "./dist/my-lib.umd.cjs"
    },
    "./style.css": "./dist/my-lib.css"
  }
}
```

> 库模式会静态替换 `import.meta.env.*`，但**不会**替换 `process.env.*`，以便使用方自行控制。若不希望如此，用 `define: { 'process.env.NODE_ENV': '"production"' }` 显式替换。

### 9.4 代码分割

Vite 8 的代码分割改为 Rolldown 的 `output.codeSplitting`（对应旧版的 `manualChunks`）：

```ts
export default defineConfig({
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          // 具体规则见 https://rolldown.rs/in-depth/manual-code-splitting
        },
      },
    },
  },
})
```

### 9.5 部署路径与 `base`

```ts
export default defineConfig({ base: '/cs_notes/' })  // 子路径部署
```

JS 导入的资源 URL、CSS 里的 `url()`、HTML 中的资源引用都会被自动改写。运行时动态拼接 URL 时用 `import.meta.env.BASE_URL`——它是构建期静态替换的，必须原样书写（`import.meta.env['BASE_URL']` 这种写法在有静态替换优化的场景下不可靠）。不确定部署路径时可用相对 base：`base: './'`。

如果需要"HTML、hash 资源、public 文件分三处部署"，用实验性的 `experimental.renderBuiltUrl` 按 `hostType` 返回不同 URL。

### 9.6 动态导入的加载失败兜底

新版部署上线后，旧 chunk 可能已被删除，此时仍在旧页面的用户会触发动态导入失败。监听 `vite:preloadError` 处理：

```js
window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  window.location.reload()   // 常见做法：刷新页面拉取新版本
})
```

配套地，HTML 文件应设置 `Cache-Control: no-cache`，否则用户可能一直引用旧资源。

### 9.7 监听重建

```bash
vite build --watch
```

配置文件及其依赖的改动需要重启构建，不会触发热重建。

## 十、插件机制

插件是一个带 `name` 字段的对象，通过返回钩子介入构建流程：

```js
// 一个仅在生产构建生效的插件骨架
export default function myPlugin(options = {}) {
  let isBuild = false

  return {
    name: 'my-plugin',
    enforce: 'pre',        // 'pre' | 'post'，调整执行顺序
    apply: 'build',        // 'build' | 'serve' | 函数，控制生效命令

    config(config) {},          // 修改用户配置（返回对象会合并）
    configResolved(resolved) {},  // 配置解析完成，可读取最终配置

    resolveId(source, importer) {},  // 自定义模块解析
    load(id) {},                     // 自定义模块内容读取
    transform(code, id) {
      if (!id.endsWith('.custom')) return
      return { code: transformed, map: null }
    },

    configureServer(server) {},       // 扩展 dev server 中间件
    transformIndexHtml(html) {},      // 改写 index.html
    handleHotUpdate(ctx) {},          // 自定义 HMR 行为
  }
}
```

常见插件：

| 插件 | 用途 |
|------|------|
| `@vitejs/plugin-vue` | Vue SFC 支持 |
| `@vitejs/plugin-react` | React 支持（含 Fast Refresh） |
| `@vitejs/plugin-legacy` | 为不支持原生 ESM 的浏览器产出 legacy chunk 与 polyfill |
| `vite-plugin-checker` | 开发期实时上报 TS / ESLint 错误 |
| `unplugin-auto-import` / `unplugin-vue-components` | API 与组件自动导入 |
| `vite-plugin-compression` | 产出 gzip / brotli 预压缩文件 |

> Rolldown 与 Rollup 的插件 API 高度兼容，但并非 100% 等价。迁移老项目时若某个 Rollup 插件报错，先查它是否已声明支持 Rolldown。

## 十一、与其他工具对比

| 维度 | Vite 8 | webpack 5 | Rspack | Parcel 2 |
|------|--------|-----------|--------|----------|
| 开发启动 | 原生 ESM，不打包 | 全量打包 + 缓存 | 全量打包（Rust） | 按需编译 |
| 底层实现 | Rolldown + Oxc（Rust） | JS | Rust | Rust |
| 配置复杂度 | 低 | 高 | 中（兼容 webpack 配置） | 极低（零配置） |
| 生态成熟度 | 快速上升 | 最成熟 | 中 | 中 |
| 典型场景 | 新项目默认选择 | 存量项目、深度定制 | webpack 项目的性能升级 | 快速原型 |

选择建议：新项目直接用 Vite；老 webpack 项目若只是嫌慢，优先试 Rspack（配置迁移成本最低）；需要极度定制产物结构时再考虑回到 Rollup/Rolldown 裸用。

## 十二、常见问题排错

| 现象 | 原因 | 解决 |
|------|------|------|
| `.env.dev` 的值读不到 | npm 少了 `--` 分隔符 | 改 `npm run dev -- --mode dev` |
| pnpm 下 `--mode` 无效且不报错 | pnpm 把字面量 `--` 透传给 Vite，cac 停止解析选项 | 去掉 `--`：`pnpm dev --mode dev` |
| 变量值为 `undefined` | 变量名缺少 `VITE_` 前缀 | 改名，或配置 `envPrefix` |
| `VITE_PORT=3000` 拿到字符串 | env 值一律解析为字符串 | 显式 `Number()` 转换 |
| 改了 `.env` 不生效 | `.env` 只在启动时加载 | 重启 dev server |
| 配置了 `envPrefix: ''` 直接报错 | Vite 8 禁止该值以防敏感信息泄露 | 用 `define` 显式注入需要的变量 |
| 生产环境某个环境变量为 `undefined` | 用了动态 key 访问且依赖静态替换优化 | 改为静态成员访问 `import.meta.env.VITE_XXX` |
| 构建产物里出现密钥 | 密钥用了 `VITE_` 前缀 | 去掉前缀，改从后端下发 |
| 依赖改了没生效 | 预构建缓存过期判断失误 | `vite --force` 或删除 `node_modules/.vite` |
| `import xxx from 'cjs-lib'` 报错 | 该 CommonJS 依赖未正确预构建 | 加入 `optimizeDeps.include` |
| 子路径部署后白屏、资源 404 | `base` 未设置 | 设 `base: '/子路径/'`，或改相对 base |
| `import.meta.env.BASE_URL` 取不到 | 静态替换必须原样书写 | 不要用 `import.meta.env['BASE_URL']` |
| 大图片被打成 base64，产物体积暴涨 | 未超过 `assetsInlineLimit` | 调小该阈值或设为 `0` |
| HMR 不触发、总是整页刷新 | 模块未声明 `accept`，或导出未变更 | 在模块内加 `import.meta.hot.accept()` |
| `tsc` 报错但 dev 不报 | Vite 只转译不检查类型 | 加 `tsc --noEmit` 或 `vite-plugin-checker` |
| `tsconfig` 的 `target` 无效 | Vite 忽略它 | 用 `oxc.target`（dev）和 `build.target`（build） |
| `paths` 别名不生效 | 未开启 `resolve.tsconfigPaths` | 置为 `true`，或改用 `resolve.alias` |
| CSS 里 `@` 别名不生效 | `include` 未覆盖 CSS 文件 | 在 `include` 中显式加 `"src/**/*.css"` |
| Windows 上 `NODE_ENV=x vite` 失败 | 原生 shell 不支持内联环境变量 | 用 `cross-env`，或启用 pnpm 的 `shellEmulator` |

## 十三、完整配置示例

```ts
// vite.config.ts —— 别名 + 代理 + 环境变量 + 多页 + 产物分析
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [vue()],

    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },

    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version ?? '0.0.0'),
    },

    server: {
      port: env.APP_PORT ? Number(env.APP_PORT) : 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },

    css: {
      devSourcemap: true,
      modules: { localsConvention: 'camelCaseOnly' },
    },

    build: {
      outDir: command === 'build' ? 'dist' : 'dist-dev',
      sourcemap: mode !== 'production',
      assetsInlineLimit: 2048,
      rolldownOptions: {
        input: {
          main: resolve(import.meta.dirname, 'index.html'),
          admin: resolve(import.meta.dirname, 'admin/index.html'),
        },
      },
    },
  }
})
```

```jsonc
// package.json
{
  "scripts": {
    "dev": "vite",
    "dev:dev": "vite --mode dev",
    "build": "npm run typecheck && vite build",
    "build:staging": "vite build --mode staging",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview"
  }
}
```

## 参见

- [[npm|NPM]]
- [[vue3|Vue 3]]
- [[javascript|JavaScript]]
- [[es6|ES6]]
- [Vite 官方文档](https://vite.dev/guide/)
- [Vite 环境变量与模式](https://vite.dev/guide/env-and-mode)
- [Vite 配置参考](https://vite.dev/config/)
- [Rolldown 文档](https://rolldown.rs/)
- [npm run-script 文档](https://docs.npmjs.com/cli/v10/commands/npm-run-script)
- [pnpm run 文档](https://pnpm.io/cli/run)
