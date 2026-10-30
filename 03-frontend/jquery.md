---
title: jQuery
description: jQuery 核心函数、对象转换、选择器、属性操作与 AJAX 用法
tags:
  - jquery
  - frontend
  - javascript
date: 2026-10-30
---

# jQuery

jQuery 由 John Resig 于 2006 年创建，旨在处理浏览器不兼容性并简化 HTML DOM 操作、事件处理、动画和 Ajax。
十多年来一直是世界上最受欢迎的 JavaScript 库。

> **注意**：在 JavaScript ES5（2009）之后，大多数 jQuery 实用程序都可以通过几行标准 JavaScript 来解决。
> 现代项目通常直接使用 `fetch` / axios，jQuery 多见于维护旧系统（如 JSP 页面）时使用。

## 核心函数 $

`$` 是 jQuery 的核心函数，能完成 jQuery 的很多功能。`$()` 就是调用 `$` 这个函数：

1. 传入参数为**函数**时：表示页面加载完成之后执行，相当于 `window.onload = function(){}`
2. 传入参数为 **HTML 字符串**时：会创建这个 HTML 标签对象
3. 传入参数为**选择器字符串**时：
    - `$("#id属性值")`：id 选择器，根据 id 查询标签对象
    - `$("标签名")`：标签名选择器
    - `$(".class属性值")`：class 选择器
4. 传入参数为 **DOM 对象**时：会把这个 dom 对象转换为 jQuery 对象

## jQuery 对象和 DOM 对象的区分与转换

jQuery 对象的本质是 dom 对象的数组 + jQuery 提供的一系列功能函数。

- DOM 对象转 jQuery 对象（重点）：`$(DOM对象)`
- jQuery 对象转 DOM 对象（重点）：`jQuery对象[下标]` 取出相应的 DOM 对象

## jQuery 选择器

- 基本选择器
- 层级选择器
- 过滤选择器

## jQuery 属性操作

| 属性 | 说明 | 备注 |
| -------- | ----------------------- | ---------------------- |
| `html()` | 设置和获取起始标签和结束标签中的内容 | 跟 dom 属性 `innerHTML` 一样 |
| `text()` | 设置和获取起始标签和结束标签中的文本 | 跟 dom 属性 `innerText` 一样 |
| `val()` | 设置和获取表单项的 value 属性值 | 跟 dom 属性 `value` 一样 |
| `attr()` | 设置和获取属性的值 | |
| `prop()` | 设置和获取属性的值 | |

## jQuery 中的 AJAX

AJAX 即 `Asynchronous JavaScript And XML`（异步 JavaScript 和 XML），指一种创建交互式网页应用的网页开发技术：浏览器通过 js 异步发起请求，局部更新页面。

- Ajax 请求的局部更新，**浏览器地址栏不会发生变化**
- 局部更新不会舍弃原来页面的内容

> Java 服务端配合 AJAX 返回 json 数据的做法见 [[java-web|Java Web 开发]]。

### $.ajax

`$.ajax(url, type, data, success, dataType)`

| 参数 | 意义 | 备注 |
| -------- | --------------------- | ----------------------------------------------- |
| url | 表示请求的地址 | |
| type | 表示请求的类型 GET 或 POST 请求 | |
| data | 表示发送给服务器的数据 | 格式有两种：1. `name=value&name=value` 2. `{key:value}` |
| success | 请求成功，响应的回调函数 | |
| dataType | 响应的数据类型 | 常用的数据类型有：`text` 表示纯文本、`xml` 表示 xml 数据、`json` 表示 json 对象 |

### $.get / $.post / $.getJSON

- `$.get(url, data, callback, type)`
- `$.post(url, data, callback, type)`
  - url：请求的 url 地址
  - data：发送的数据
  - callback：成功的回调函数
  - type：返回的数据类型
- `$.getJSON(url, data, callback)`

## 相关资源

- [[javascript|JavaScript]]
- [[json|JSON]]
