---
title: CSS
description: CSS 样式基础、选择器、布局、Flexbox、Grid 等样式技术
tags:
  - css
  - frontend
  - web-design
date: 2024-04-06
---

[MDN CSS](https://developer.mozilla.org/zh-CN/docs/Learn/CSS)

# CSS样式基础


## CSS选择器

### 选择器是什么

### 选择器列表
```css
h1, .special {
  color: blue;
}

```

#### 选择器的种类

类型 类 ID 选择器

标签选择器

伪类与伪元素

运算符
 
类型选择器（标签名选择器或者是元素选择器）

```css
p {
	font-size: 10
}
```

id 选择器

```css
#id {
  color: red;
}
```

class 选择器

```css
.class {
  color: blue;
}
```

组合选择器：让多个选择器共用一个 css 样式代码

```css
选择器1, 选择器2, 选择器3 {
  key: value;
}
```

## CSS 与 HTML 的结合方式

1. 在标签的 `style` 属性上设置 `key:value` 修改标签样式（内联样式）
2. 在 head 标签中，使用 `style` 标签来定义各种自己需要的 css 样式

    ```html
    <style type="text/css">
    div {
      border: 1px solid red;
    }
    span {
      border: 1px solid red;
    }
    </style>
    ```

3. 把 css 样式写成一个单独的 css 文件，再通过 link 标签引入即可复用

    ```html
    <link rel="stylesheet" type="text/css" href="./styles.css" />
    ```

常用样式：`color: red`、`width: 19px`、`height: 20px`

## 属性选择器

### 存否和值选择器

| 选择器              | 示例                              | 描述                                                                                                           |
| ---------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `[attr]`         | `a[title]`                      | 匹配带有一个名为_attr_的属性的元素——方括号里的值。                                                                                |
| `[attr=value]`   | `a[href="https://example.com"]` | 匹配带有一个名为_attr_的属性的元素，其值正为_value_——引号中的字符串。                                                                   |
| `[attr~=value]`  | `p[class~="special"]`           | 匹配带有一个名为_attr_的属性的元素，其值正为_value_，或者匹配带有一个_attr_属性的元素，其值有一个或者更多，至少有一个和_value_匹配。<br><br>注意，在一列中的好几个值，是用空格隔开的。 |
| `[attr\|=value]` | `div[lang\|="zh"]`              | 匹配带有一个名为_attr_的属性的元素，其值可正为_value_，或者开始为_value_，后面紧随着一个连字符。                                                   |
|                  |                                 |                                                                                                              |
### 子字符串匹配选择器

## 伪类和伪元素

### 什么是伪类

## 关系选择器
### 后代选择器

### 子代关系选择器
### 领接兄弟

### 通用兄弟



## 盒模型


## 层叠、优先级和继承


## css值和单位

## 在CSS中调整大小


## 背景与边框

## 溢出的内容

## 图像、媒体和表单元素

## 样式化表格


## 调试CSS

## 基本的CSS理解

## 创建精美的信纸

## 一个漂亮的盒子


# CSS文本样式



# CSS排版

