---
title: HTML
description: HTML 基础语法、语义化标签、表单元素、多媒体标签等 Web 核心技术
tags:
  - html
  - frontend
  - web
date: 2024-03-21
---

# HTML

HTML（超文本标记语言）是构建 Web 页面的基础。本文档涵盖 HTML5 的核心概念和常用元素。

## 基础结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>页面标题</title>
</head>
<body>
    <header>
        <h1>网站标题</h1>
        <nav>
            <a href="/">首页</a>
            <a href="/about">关于我们</a>
        </nav>
    </header>

    <main>
        <article>
            <h2>文章标题</h2>
            <p>文章内容...</p>
        </article>

        <aside>
            <h3>侧边栏</h3>
            <p>相关链接...</p>
        </aside>
    </main>

    <footer>
        <p>&copy; 2024 公司名称</p>
    </footer>
</body>
</html>
```

## 语义化标签

HTML5 引入了语义化标签，使文档结构更清晰：

| 标签 | 用途 |
|------|------|
| `<header>` | 页面或区块的头部 |
| `<nav>` | 导航链接 |
| `<main>` | 主要内容区域 |
| `<article>` | 独立文章内容 |
| `<section>` | 文档章节 |
| `<aside>` | 侧边栏 |
| `<footer>` | 页面或区块的底部 |
| `<figure>` | 图表、代码块等独立内容 |
| `<figcaption>` | figure 的标题 |

```html
<article>
    <header>
        <h1>文章标题</h1>
        <time datetime="2024-03-21">2024年3月21日</time>
    </header>
    <section>
        <p>第一段内容...</p>
    </section>
    <section>
        <p>第二段内容...</p>
    </section>
    <footer>
        <p>作者：XXX</p>
    </footer>
</article>
```

## 文本标签

### 标题和段落

```html
<h1>一级标题 - 页面主标题</h1>
<h2>二级标题 - 章节标题</h2>
<h3>三级标题 - 小节标题</h3>
<h4>四级标题</h4>
<h5>五级标题</h5>
<h6>六级标题 - 最小标题</h6>

<p>这是一个段落，用于包含一段独立的文本内容。</p>
<p>另一个段落，浏览器会自动在段落之间添加垂直间距。</p>
```

### 文本格式化

```html
<!-- 强调 -->
<strong>加粗强调</strong>
<em>斜体强调</em>

<!-- 行内元素 -->
<span>无语义行内容器</span>
<a href="https://example.com">链接</a>

<!-- 引用 -->
<blockquote cite="来源URL">
    <p>长引用内容...</p>
</blockquote>
<cite>短引用来源</cite>

<!-- 代码 -->
<code>行内代码</code>
<pre><code>// 预格式化代码块
function hello() {
    console.log('Hello World');
}</code></pre>

<!-- 列表 -->
<ul>
    <li>无序列表项 1</li>
    <li>无序列表项 2</li>
</ul>

<ol>
    <li>有序列表项 1</li>
    <li>有序列表项 2</li>
</ol>

<dl>
    <dt>术语</dt>
    <dd>术语定义</dd>
</dl>
```

## 链接与导航

```html
<!-- 外部链接 -->
<a href="https://example.com" target="_blank" rel="noopener noreferrer">
    访问示例网站
</a>

<!-- 锚点链接 -->
<a href="#section-id">跳转到章节</a>
<h2 id="section-id">章节标题</h2>

<!-- 邮件和电话链接 -->
<a href="mailto:contact@example.com">发送邮件</a>
<a href="tel:+86123456789">拨打电话</a>

<!-- 下载链接 -->
<a href="/files/document.pdf" download="文档.pdf">下载 PDF</a>
```

## 图片和多媒体

```html
<!-- 图片 -->
<img src="image.jpg" alt="图片描述" width="800" height="600">

<!-- 响应式图片 -->
<picture>
    <source srcset="image-768.webp 768w,
                    image-1200.webp 1200w"
            type="image/webp">
    <img src="image.jpg" alt="描述">
</picture>

<!-- 视频 -->
<video controls width="800" poster="thumbnail.jpg">
    <source src="video.mp4" type="video/mp4">
    <source src="video.webm" type="video/webm">
    <track src="subtitles.vtt" kind="subtitles" srclang="zh" label="中文">
    您的浏览器不支持 video 标签。
</video>

<!-- 音频 -->
<audio controls>
    <source src="audio.mp3" type="audio/mpeg">
    <source src="audio.ogg" type="audio/ogg">
    您的浏览器不支持 audio 元素。
</audio>

<!-- 内嵌 iframe -->
<iframe
    src="https://www.youtube.com/embed/VIDEO_ID"
    width="800"
    height="450"
    allowfullscreen>
</iframe>
```

## 表格

```html
<table>
    <thead>
        <tr>
            <th>列标题 1</th>
            <th>列标题 2</th>
            <th>列标题 3</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>单元格 1</td>
            <td>单元格 2</td>
            <td>单元格 3</td>
        </tr>
        <tr>
            <td>单元格 4</td>
            <td colspan="2">跨两列的单元格</td>
        </tr>
    </tbody>
    <tfoot>
        <tr>
            <td>表格脚注</td>
            <td>...</td>
            <td>...</td>
        </tr>
    </tfoot>
</table>
```

## 表单

```html
<form action="/submit" method="POST">
    <!-- 文本输入 -->
    <label for="username">用户名:</label>
    <input type="text" id="username" name="username" required>

    <!-- 邮箱输入 -->
    <label for="email">邮箱:</label>
    <input type="email" id="email" name="email">

    <!-- 密码输入 -->
    <label for="password">密码:</label>
    <input type="password" id="password" name="password">

    <!-- 数字输入 -->
    <label for="age">年龄:</label>
    <input type="number" id="age" name="age" min="0" max="150">

    <!-- 日期输入 -->
    <label for="birthday">生日:</label>
    <input type="date" id="birthday" name="birthday">

    <!-- 单选按钮 -->
    <fieldset>
        <legend>性别</legend>
        <input type="radio" id="male" name="gender" value="male">
        <label for="male">男</label>
        <input type="radio" id="female" name="gender" value="female">
        <label for="female">女</label>
    </fieldset>

    <!-- 复选框 -->
    <input type="checkbox" id="subscribe" name="subscribe">
    <label for="subscribe">订阅 newsletter</label>

    <!-- 下拉选择 -->
    <label for="country">国家:</label>
    <select id="country" name="country">
        <option value="">请选择</option>
        <option value="cn">中国</option>
        <option value="us">美国</option>
        <option value="jp">日本</option>
    </select>

    <!-- 文本域 -->
    <label for="message">留言:</label>
    <textarea id="message" name="message" rows="4" cols="50"></textarea>

    <!-- 提交按钮 -->
    <button type="submit">提交</button>
    <button type="reset">重置</button>
</form>
```

### 表单提交的规则

`form` 标签中 `action` 属性设置提交的服务器地址，`method` 属性设置提交方式 `GET`（默认值）或 `POST`。

表单提交时，数据没有发送给服务器的三种情况：

1. 表单项没有 `name` 属性值
2. 单选、复选、下拉列表中的 `option` 标签都需要添加 `value` 属性，以便发送给服务器
3. 表单项不在提交的 `form` 标签中

- `GET` 请求的特点：
    1. 浏览器地址栏中的地址是：`action` 属性值 [+?+请求参数]，请求参数格式为 `name=value&name=value`
    2. 不安全
    3. 有数据长度的限制
- `POST` 请求的特点：
    1. 浏览器地址栏中只有 `action` 属性值
    2. 相对于 `GET` 请求要安全
    3. 理论上没有数据长度的限制

### 表格的跨行跨列

`colspan` 属性设置跨列，`rowspan` 属性设置跨行：

```html
<table border="1">
    <tr>
        <td colspan="2">跨两列</td>
        <td>1.3</td>
    </tr>
    <tr>
        <td rowspan="2">跨两行</td>
        <td>2.2</td>
    </tr>
    <tr>
        <td>3.2</td>
    </tr>
</table>
```

## 全局属性

所有 HTML 元素都支持的属性：

| 属性 | 说明 |
|------|------|
| `id` | 元素唯一标识符 |
| `class` | CSS 类名（可多个，用空格分隔） |
| `style` | 内联样式 |
| `title` | 鼠标悬停显示的提示文本 |
| `data-*` | 自定义数据属性 |
| `accesskey` | 键盘快捷键 |
| `contenteditable` | 是否可编辑 |
| `hidden` | 隐藏元素 |
| `lang` | 语言代码 |
| `dir` | 文本方向 (ltr/rtl) |

```html
<!-- 自定义数据属性 -->
<div id="user" data-user-id="12345" data-role="admin">
    用户信息
</div>

<script>
const user = document.getElementById('user');
const userId = user.dataset.userId; // "12345"
const role = user.dataset.role;    // "admin"
</script>
```

## 无障碍 (Accessibility)

```html
<!-- 添加语义和 aria 属性 -->
<nav aria-label="主导航">
    <ul>
        <li><a href="/" aria-current="page">首页</a></li>
    </ul>
</nav>

<!-- 图片 alt 文本 -->
<img src="chart.png" alt="2024年销售趋势图，显示同比增长 25%">

<!-- 表单关联 -->
<label for="email">邮箱地址</label>
<input type="email" id="email" aria-describedby="email-help">
<p id="email-help">请输入有效的邮箱地址</p>

<!-- 按钮 vs 链接 -->
<button onclick="toggleMenu()">打开菜单</button>
<a href="/page">访问页面</a>
```

## SEO 基础

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>页面标题 - 网站名称</title>
    <meta name="description" content="页面描述，150-160字符最佳">
    <meta name="keywords" content="关键词1, 关键词2, 关键词3">
    <meta name="author" content="作者名">

    <!-- Open Graph -->
    <meta property="og:title" content="分享标题">
    <meta property="og:description" content="分享描述">
    <meta property="og:image" content="图片URL">
    <meta property="og:url" content="页面URL">

    <!-- 规范链接 -->
    <link rel="canonical" href="规范URL">

    <!-- Favicon -->
    <link rel="icon" href="/favicon.ico">
</head>
```

## 相关资源

- [[css|CSS 样式]]
- [[javascript|JavaScript]]
- [MDN Web Docs - HTML](https://developer.mozilla.org/zh-CN/docs/Learn/HTML)
