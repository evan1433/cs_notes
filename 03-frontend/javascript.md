---
title: JavaScript
description: JavaScript 基础语法、数据类型、函数、面向对象等核心概念
tags:
  - javascript
  - frontend
  - programming
date: 2024-04-05
---

# JavaScript教程
来源：[`w3cschool js教程`](https://www.w3school.com.cn/js/index.asp)
# js注释

```javascript
// 单行注释
/* 多行注释*/
```

# js变量
```js
var x = 7;
var y = 8;
var z = x + y;
```

变量：一小块存储数据的内存空间。Java 语言是强类型语言，而 JavaScript 是弱类型语言：

- **强类型**：在开辟变量存储空间时，定义了空间将来存储的数据的数据类型，只能存储固定类型的数据
- **弱类型**：在开辟变量存储空间时，不定义空间将来的存储数据类型，可以存放任意类型的数据

JS 原始数据类型（基本数据类型）：

- `number`：数字（整数、小数、`NaN`）
- `string`：字符串
- `boolean`：`true` 和 `false`
- `null`：一个对象为空的占位符
- `undefined`：未定义，变量没有初始化值时默认赋值为 `undefined`

> 注：`typeof null` 运算后得到的是 `object`。

# js let
作用域问题

# js const

# JS运算符

[JS运算符](https://www.w3school.com.cn/js/js_operators.asp)

比较运算符 `==` 与 `===`（全等于）的区别：

1. 类型相同：直接比较（字符串按照字典顺序逐位比较）
2. 类型不同：`==` 先进行类型转换再比较；`===` 先判断类型，类型不一样直接返回 `false`

JS 引擎会自动对运算数进行类型转换：

- 其他类型转 `number`：`string` 按字面值转换（不是数字则转为 `NaN`）；`boolean` 中 `true` 转为 `1`、`false` 转为 `0`
- 其他类型转 `boolean`：`number` 中 `0` 或 `NaN` 为假，其他为真；`string` 中除了空字符串 `""` 其他都是 `true`；`null` 和 `undefined` 都是 `false`；所有对象都为 `true`

三元运算符：`表达式 ? 值1 : 值2`

`switch` 语句在 JS 中可以接受任意的原始数据类型
（Java 中只能接受 `byte int short char`、`Enum`、`String`）。

# [JavaScript数据类型](https://www.w3school.com.cn/js/js_datatypes.asp)

字符串，数值，布尔值，数组，对象

* JavaScript 拥有动态类型

* JavaScript 从左向右计算表达式。不同的次序会产生不同的结果：

```javascript
var x = 911 + 7 +'Porsche'   // 918Prosche
```

* js数组

```javascript
var cars = ["Porsche", "Volvo", "BMW"]
```

* js对象

```javascript
var person = {firstName:"Bill", lastName:"Gates", age:62, eyeColor:"blue"};
```

##  `typeof`  运算符

```js
typeof ""                  // 返回 "string"
typeof "Bill"              // 返回 "string"
typeof "Bill Gates"          // 返回 "string"
```

## `undefined`
在 JavaScript 中，没有值的变量，其值是 `undefined`。typeof 也返回 `undefined`。
```js
var person;                  // 值是 undefined，类型是 undefined。
```
任何变量均可通过设置值为 `undefined` 进行清空。其类型也将是 `undefined`
```js
person = undefined;          // 值是 undefined，类型是 undefined。
```
## 空值

```js
var car = "";                // 值是 ""，类型是 "string"
```

## `null`
在 JavaScript 中，`null` 是 "nothing"。它被看做不存在的事物。

不幸的是，在 JavaScript 中，`null` 的数据类型是对象。

您可以把 `null` 在 JavaScript 中是对象理解为一个 bug。它本应是 `null`。

您可以通过设置值为 `null` 清空对象

```js
var person = null;           // 值是 null，但是类型仍然是对象
```

## Undefined 与 Null 的区别
`Undefined` 与 `null` 的值相等，但类型不相等：

```js
typeof undefined              // undefined
typeof null                   // object
null === undefined            // false
null == undefined             // true
```

* 对象
* 

# JS函数

## 函数声明

```javascript
function functionName (arg1, arg2){
   // code
    return 0;
}
```

函数表达式
```javascript
// 函数表达式 要以分号结尾
var x = function(){ return a*b};
```

```javascript
var x = function (a, b) {return a * b};
var z = x(4, 3);
```


## 函数提升


## 函数调用

* 当事件发生时
* 当JavasScript代码调用时
* 自动的（自调用）

访问没有 () 的函数将返回函数定义

函数是对象
```javascript
function myFunction(a, b) {
    return arguments.length;
}
```

```javascript
function myFunction(a, b) {
    return a * b;
}

var txt = myFunction.toString();
```
## 箭头函数

```javascript
// ES5
var x = function(x, y) {
  return x * y;
}

// ES6
const x = (x, y) => x * y;
```
箭头函数没有自己的 this。它们不适合定义对象方法。

箭头函数未被提升。它们必须在使用前进行定义。

使用 const 比使用 var 更安全，因为函数表达式始终是常量值。

如果函数是单个语句，则只能省略 return 关键字和大括号。因此，保留它们可能是一个好习惯：
```js
const x = (x, y) =>{return x * Y };
```

## 函数参数

## 自执行函数

在 JavaScript 里，自执行函数（Self-Executing Anonymous Function）也被叫做立即调用函数表达式（Immediately Invoked Function Expression，简称 IIFE），它是一种在定义之后马上就会执行的函数。下面将从语法、使用场景、优势几个方面详细介绍。

### 语法
自执行函数的基本语法有两种形式：

#### 形式一：使用括号包裹函数定义和调用
```javascript
(function() {
    // 函数体
    console.log('这是一个自执行函数');
})();
```
在这个例子中，`(function() {... })` 把匿名函数包裹起来，后面紧跟的 `()` 则是用来调用这个函数。

#### 形式二：使用运算符包裹函数调用
```javascript
(function() {
    // 函数体
    console.log('这也是一个自执行函数');
}());
```
这种形式同样是将匿名函数定义后立即调用，只是括号的位置稍有不同。

### 使用场景
#### 1. 创建独立的作用域
```javascript
(function() {
    var privateVariable = '这是一个私有变量';
    console.log(privateVariable);
})();
// 这里无法访问 privateVariable
```
在这个例子中，`privateVariable` 是在自执行函数内部定义的，它属于该函数的局部变量，外部代码无法访问，从而避免了全局变量的污染。

#### 2. 模块模式
```javascript
var myModule = (function() {
    var privateValue = 0;
    function privateFunction() {
        return privateValue;
    }
    return {
        increment: function() {
            privateValue++;
        },
        getValue: function() {
            return privateFunction();
        }
    };
})();

myModule.increment();
console.log(myModule.getValue()); 
```
在这个模块模式的示例中，自执行函数返回一个对象，该对象包含了一些公共方法，这些方法可以访问和操作函数内部的私有变量和函数。

### 优势
- **避免全局变量污染**：自执行函数内部定义的变量和函数不会影响到全局作用域，减少了命名冲突的可能性。
- **封装私有变量和函数**：可以将一些不希望被外部访问的变量和函数封装在自执行函数内部，只暴露必要的接口。
- **代码隔离**：将相关的代码封装在一个独立的作用域中，提高了代码的可维护性和可读性。

综上所述，自执行函数是 JavaScript 中一种非常有用的技术，它可以帮助开发者更好地管理代码和避免潜在的问题。 

`arguments`对象

# JS对象
```javascript
var car = {type = "porsche", model = "911", color:"red"};

var person = {
  firstName: "Bill",
  lastName : "Gates",
  id       : 678,
  fullName : function() {
    return this.firstName + " " + this.lastName;
  }
};
```

## 对象属性


## 对象方法

## 对象构造器


### this关键词
在函数定义中，`this` 引用该函数的“拥有者”。
### 对象定义

## JS对象原型




# JS事件
```html
<!DOCTYPE html>
<html>
<body>

<h1 onclick="this.innerHTML = 'Hello!'">点击此文本！</h1>

</body>
</html>
```

```javascript
<element event = 'some JavaScript code'>
```

* 常见的HTML事件

| 事件 | 描述 |
| ---- | ---- |
| onchange | HTML元素被改变 |
| onclick | 用户点击了HTML元素 |
| ondblclick | 用户双击了HTML元素 |
| onmouseover | 用户把鼠标移动到 HTML 元素上 |
| onmouseout | 用户把鼠标移开 HTML 元素 |
| onmousedown / onmouseup | 鼠标按钮被按下 / 松开 |
| onmousemove | 鼠标被移动 |
| onkeydown / onkeyup / onkeypress | 键盘按键被按下 / 松开 / 按下并松开 |
| onfocus / onblur | 元素获得焦点 / 失去焦点 |
| onload | 浏览器已经完成页面加载 |
| onselect | 文本被选中 |
| onsubmit / onreset | 确认按钮 / 重置按钮被点击 |

事件监听机制的概念：某些组件被执行了某些操作后，触发某些代码的执行。事件源（组件）上发生了某个事件，则触发执行某个监听器代码，将事件、事件源、监听器结合在一起叫注册监听。

## onload 和 onunload 事件

当用户进入后及离开页面时，会触发 `onload` 和 `onunload` 事件。

`onload` 事件可用于检测访问者的浏览器类型和浏览器版本，然后基于该信息加载网页的恰当版本。

`onload` 和 `onunload` 事件可用于处理 cookie。

## onchange 事件

`onchange` 事件经常与输入字段验证结合使用。

下面是一个如何使用 `onchange` 的例子。当用户改变输入字段内容时，会调用 upperCase() 函数。

## onmouseover 和 onmouseout 事件

`onmouseover` 和 `onmouseout` 事件可用于当用户将鼠标移至 HTML 元素上或移出时触发某个函数：

## HTML DOM Event 对象参考手册

如需所有 HTML DOM 事件的列表，请访问我们完整的 [HTML DOM 事件对象参考手册](https://www.w3school.com.cn/jsref/dom_obj_event.asp "HTML DOM Event 对象")。

# [JS字符串](https://www.w3school.com.cn/js/js_string_methods.asp)

* 字符串长度 length

```javascript
var txt = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
vat sln = txt.length
```

* 查找字符串中的字符串  

indexOF()    lastIndexOf()

* 检索字符串中的字符串

search()

* slice()
* substring()
* substr()
* replace()
* toUpperCase()
* toLowerCase()
* concat()
* trim()
* charAt()   charCodeAt()
* split()

# JS数字

JavaScript数值始终是64位的浮点数

## JS数字方法

* `toString()`
* `toExponential()`
*` toFixed()`
* ` toPrecision()
* `valueOf()`

# JS数组

## 数组方法

## 数组排序

## 数组迭代


## 数组和对象的区别

在 JavaScript 中，_数组_使用_数字索引_。

在 JavaScript 中，_对象_使用_命名索引_。

数组是特殊类型的对象，具有数字索引。
# JS日期


# JS 类

# JS Async

# JavaScript HTML DOM
**通过 HTML DOM，JavaScript 能够访问和改变 HTML 文档的所有元素。**

`Document Object Model` 文档对象模型，将标记语言文档的各个组成部分封装为对象，
可以使用这些对象对标记语言文档进行**CRUD**的动态操作。
W3C DOM 标准分为三个部分：核心 DOM（针对任何结构化文档）、XML DOM、HTML DOM。

核心 DOM 模型：

- `Document`：文档对象（通过 `window.document` 或 `document` 获取）
- `Element`：元素对象
- `Attribute`：属性对象
- `Text`：文本对象
- `Comment`：注释对象
- `Node`：节点对象，其他 5 个的父对象

## Document 获取元素

- `getElementById(elementId)`：根据 id 属性值获取元素对象，id 属性值一般唯一
- `getElementsByTagName(tagname)`：根据元素名称获取元素对象们，返回值是一个数组
- `getElementsByClassName(className)`：根据 class 属性值获取元素对象们
- `getElementsByName(elementName)`：根据 name 属性值获取元素对象们

创建其他 DOM 对象：`createAttribute()`、`createComment()`、`createElement()`、`createTextNode()`

## Element 和 Node 操作

`Element` 元素对象的方法：

- `setAttribute()`：设置属性
- `removeAttribute()`：删除属性

`Node` 节点对象（所有 dom 对象都可以被认为是一个节点）：

- `appendChild()`：向节点的子节点列表的结尾添加新的子节点
- `removeChild()`：删除（并返回）当前节点的指定子节点
- `replaceChild()`：用新节点替换一个子节点
- `parentNode`：返回节点的父节点

## innerHTML 与样式控制

标签体的设置和获取：`innerHTML`、`innerText`

控制元素样式：

```javascript
// 方式一：使用元素的 style 属性
div1.style.border = "1px solid red";
div1.style.width = "200px";
// font-size --> fontSize
div1.style.fontSize = "20px";

// 方式二：提前定义好类选择器的样式，通过 className 属性设置其 class 属性值
div1.className = "myClass";
```

# JS Browser BOM
**浏览器对象模型（Browser Object Model (BOM)）允许 JavaScript 与浏览器对话。**

## window

`Window` 对象不需要创建可以直接使用，`window` 引用可以省略：`window.方法名()` 等价于 `方法名()`。

与弹出框有关的方法：

- `alert()`：显示带有一段消息和一个确认按钮的警告框
- `confirm()`：显示带有一段消息以及确认按钮和取消按钮的对话框（确定返回 `true`，取消返回 `false`）
- `prompt()`：显示可提示用户输入的对话框，返回值为用户输入的内容

与打开关闭有关的方法：

- `close()`：关闭浏览器窗口（谁调用我，我关谁）
- `open()`：打开一个新的浏览器窗口，返回新的 `Window` 对象

与定时器有关的方法：

- `setTimeout()`：在指定的毫秒数后调用函数或计算表达式，返回值是唯一标识，用于取消定时器
- `clearTimeout()`：取消由 `setTimeout()` 设置的定时器
- `setInterval()`：按照指定的周期（以毫秒计）来调用函数或计算表达式
- `clearInterval()`：取消由 `setInterval()` 设置的定时器

## screen

## Location

地址栏对象，通过 `window.location` 或 `location` 获取。

- 方法：`reload()` 重新加载当前文档（刷新）
- 属性：`href` 设置或返回完整的 URL

## History

历史记录对象，通过 `window.history` 或 `history` 获取。

- `back()`：加载 history 列表中的前一个 URL
- `forward()`：加载 history 列表中的下一个 URL
- `go(参数)`：加载 history 列表中的某个具体页面（正数前进几个历史记录，负数后退几个）
- `length`：返回当前窗口历史列表中的 URL 数量

## Navigator

## 弹出框

## Timing

## Cookies

# WEB API

# AJAX

# jQuery
jQuery 由 John Resig 于 2006 年创建。它旨在处理浏览器不兼容性并简化 HTML DOM 操作、事件处理、动画和 Ajax。

十多年来，jQuery 一直是世界上最受欢迎的 JavaScript 库。

但是，在 JavaScript Version 5（2009）之后，大多数 jQuery 实用程序都可以通过几行标准 JavaScript 来解决

## jQuery选择器

### 通过id来查找HTML元素

### 通过标签名来查找 HTML 元素

### 通过类名来查找 HTML 元素

### 通过 CSS 选择器查找 HTML 元素

## jQuery HTML

### 设置HTML内容

### 获取 HTML 内容

## jQuery CSS样式
### 隐藏HTML元素

### 显示HTML元素

### 样式化HTML元素

## jQuery HTML DOM

### 删除元素

### 获取父元素


# vue

每个 Vue 应用都需要通过实例化 Vue 来实现。

```javascript
 var vm = new Vue({
        el: '#vue_det',  // 
        data: {
            site: "菜鸟教程",
            url: "www.runoob.com",
            alexa: "10000"
        },
        methods: {
            details: function() {
                return  this.site + " - 学的不仅是技术，更是梦想！";
            }
        }
     	filters:{   // 过滤器
 		}
        computed:{
              site:{
                  // getter
                  get:function(){
     					return  this.xxx
 					}
				  // setter
				  set:function(){                      
                  	}
                  }    
 		}
    })
```



## 缩写 

```html
<!-- 完整语法 -->
<a v-bind:href="url"></a>
<!-- 缩写 -->
<a :href="url"></a>

<!-- 完整语法 -->
<a v-on:click="doSomething"></a>
<!-- 缩写 -->
<a @click="doSomething"></a>
```

## 指令

指令是带有 v- 前缀的特殊属性。

* 使用 v-html 指令用于输出 html 代码
* `v-if`
* `v-else`
* `v-else-if`
* `v-show`
* `v-for`

循环使用 v-for 指令。

v-for 指令需要以 **site in sites** 形式的特殊语法， sites 是源数据数组并且 site 是数组元素迭代的别名。




