---
title: Vue 2
description: Vue 2 基础语法、组件系统、路由、状态管理
tags:
  - vue2
  - frontend
  - javascript
date: 2024-04-12
---

# vue

参考资料

- [尚硅谷-vue 课程](https://www.bilibili.com/video/BV1Zy4y1K7SH/?share_source=copy_web&vd_source=e65574be5c4ff436d099ae0526b97fd9)
- [vu2 api doc](https://cn.vuejs.org/api/)
- [vue2 router](https://router.vuejs.org/zh)

**学习 Vue 之前需要掌握的 JavaScript 基础知识：[[es6|ES6]]**



# 第1章 VUE basic

## 初识Vue

1. 想让`Vue`工作，就必须创建一个`Vue`实例，且要传入一个**配置对象**；
2. `root`容器里的代码依然符合`html`规范，只不过混入了一些特殊的Vue语法；
3. `root`容器里的代码被称为【Vue模板】；
4. `Vue`实例和容器是一一对应的；
5. 真实开发中只有一个Vue实例，并且会配合着组件一起使用；
6. `{{xxx}}`中的`xxx`要写`js`表达式，且`xxx`可以自动读取到`data`中的所有属性；
7. 一旦`data`中的数据发生改变，那么页面中用到该数据的地方也会自动更新；

注意区分：js表达式 和 js代码(语句)

1. 表达式：一个表达式会产生一个值，可以放在任何一个需要值的地方：
    - `a`
    - `a+b`
    - `demo(1)`
    - `x === y ? 'a' : 'b'`

2. js代码(语句)
    - `if(){}`
    - `for(){}`

## 模版语法

Vue模板语法有2大类：

1. 插值语法：
   - 功能：用于解析标签体内容。
   - 写法：`{{xxx}}`，`xxx`是`js`表达式，且可以直接读取到`data`中的所有属性。

2. 指令语法：
   - 功能：用于解析标签（包括：标签属性、标签体内容、绑定事件.....）。
   - 举例：`v-bind:href="xxx"`或 简写为`:href="xxx"`，`xxx`同样要写`js`表达式，且可以直接读取到`data`中的所有属性。
   - 备注：Vue中有很多的指令，且形式都是：`v-????`，此处我们只是拿v-bind举个例子。

```html
<div id="root">
 <h1>插值语法</h1>
 <h3>你好，{{name}}</h3>
 <hr/>
 <h1>指令语法</h1>
 <a v-bind:href="school.url.toUpperCase()" 
  x="hello">点我去{{school.name}}学习1
 </a>
 <a :href="school.url" x="hello">点我去{{school.name}}学习2</a>
</div>
```

## 数据绑定

el 和 data 的两种写法

```javascript
const v = new Vue({
 //el:'#root', //第一种写法
 data:{
  name:'尚硅谷'
 }
})
v.mount('#root') //第二种写法
```

```javascript
new Vue({
 el:'#root',
 //data的第一种写法：对象式
 /* data:{
 name:'尚硅谷'
 } */
 //data的第二种写法：函数式
 data(){
  console.log('@@@',this) //此处的this是Vue实例对象
  return{
   name:'尚硅谷'
  }
 }
})
```

## 理解mvvm

model

model-view

view

## 数据代理

### Object.defineProperty

```js
let number = 18
let person = {
 name:'张三',
 sex:'男',
}
Object.defineProperty(person,'age',{
 // value:18,
 // enumerable:true, //控制属性是否可以枚举，默认值是false
 // writable:true, //控制属性是否可以被修改，默认值是false
 // configurable:true //控制属性是否可以被删除，默认值是false
 //当有人读取person的age属性时，get函数(getter)就会被调用，且返回值就是age的值
 
 get(){
 console.log('有人读取age属性了')
 return number
 },
 //当有人修改person的age属性时，set函数(setter)就会被调用，且会收到修改的具体值
 
 set(value){
 console.log('有人修改了age属性，且值是',value)
 number = value
 }
})
console.log(Object.keys(person))
```

`Object.keys`不会输出defineProperty的属性

数据代理：通过一个对象代理对另一个对象中属性的操作

## 事件处理

1. 使用`v-on:xxx` 或 `@xxx`绑定事件，其中`xxx`是事件名；
2. 事件的回调需要配置在`methods`对象中，最终会在vm上；
3. `methods`中配置的函数，不要用箭头函数！否则`this`就不是`vm`了；
4. `methods`中配置的函数，都是被Vue所管理的函数，`this`的指向是`vm` 或 组件实例对象；
5. `@click="demo"` 和 `@click="demo($event)"` 效果一致，但后者可以传参；

### Vue中的事件修饰符

1. `prevent`：阻止默认事件（常用）；
2. `stop`：阻止事件冒泡（常用）；
3. `once`：事件只触发一次（常用）；
4. `capture`：使用事件的捕获模式；
5. `self`：只有event.target是当前操作的元素时才触发事件；
6. `passive`：事件的默认行为立即执行，无需等待事件回调执行完毕；

### 键盘事件

1. Vue中常用的按键别名：
   - 回车 => `enter`
   - 删除 => `delete` (捕获“删除”和“退格”键)
   - 退出 => `esc`
   - 空格 => `space`
   - 换行 => `tab`(特殊，必须配合keydown去使用)
   - 上 => `up`
   - 下 => `down`
   - 左 => `left`
   - 右 => `right`
2. Vue未提供别名的按键，可以使用按键原始的key值去绑定，但注意要转为kebab-case（短横线命名）
3. 系统修饰键（用法特殊）：`ctrl`、`alt`、`shift`、`meta`
   1. 配合`keyup`使用：按下修饰键的同时，再按下其他键，随后释放其他键，事件才被触发。
   2. 配合`keydown`使用：正常触发事件。
   3. 也可以使用`keyCode`去指定具体的按键（不推荐）
   4. `Vue.config.keyCodes.自定义键名 = 键码`，可以去定制按键别名

## 计算属性

计算属性：

1. 定义：要用的属性不存在，要通过已有属性计算得来。
2. 原理：底层借助了`Objcet.defineproperty`方法提供的`getter`和`setter`。
3. `get`函数什么时候执行？
    1. 初次读取时会执行一次。
    2. 当依赖的数据发生改变时会被再次调用。
4. 优势：与`methods`实现相比，内部有缓存机制（复用），效率更高，调试方便。
5. 备注：
    1. 计算属性最终会出现在vm上，直接读取使用即可。
    2. 如果计算属性要被修改，那必须写set函数去响应修改，且set中要引起计算时依赖的数据发生改变

```js
const vm = new Vue({
 el:'#root',
 data:{
  firstName:'张',
  lastName:'三'
 },
 computed:{
  //完整写法
  fullName:{
   get(){
    console.log('get被调用了')
    return this.firstName + '-' + this.lastName
   },
   set(value){
    console.log('set',value)
    const arr = value.split('-')
    this.firstName = arr[0]
    this.lastName = arr[1]
   }，
  },
  //简写
  fullName(){
   console.log('get被调用了')
   return this.firstName + '-' + this.lastName
  }
 }
})
```

## 监视属性

监视属性`watch`：

1. 当被监视的属性变化时, 回调函数自动调用, 进行相关操作
2. 监视的属性必须存在，才能进行监视！！
3. 监视的两种写法：
    1. `new Vue`时传入`watch`配置
    2. 通过`vm.$watch`监视

```js
const vm = new Vue({
 el:'#root',
 data:{
  isHot:true,
  numbers:{
   a:1,
   b:1,
   c:{
   d:{
    e:100
   }
  }} 
 },
 computed:{
 info(){
  return this.isHot ? '炎热' : '凉爽'
 }
 },
 methods: {
  changeWeather(){
  this.isHot = !this.isHot
  }
 },
 watch:{
  isHot:{
   immediate:true, //初始化时让handler调用一下
   //handler什么时候调用？当isHot发生改变时。
   handler(newValue,oldValue){
   console.log('isHot被修改了',newValue,oldValue)
   }
  },
  numbers:{
   deep: ture,
   hadler(){
    console.log('numbers changed!')
   }
  }
 }
})
```

```js
vm.$watch('isHot',{
 immediate:true, //初始化时让handler调用一下
 //handler什么时候调用？当isHot发生改变时。
 handler(newValue,oldValue){
 console.log('isHot被修改了',newValue,oldValue)
}
})
```

watch
`deep`
`immediate`
深度监视

## 绑定样式

1. class样式
 写法`:class="xxx"` xxx可以是字符串、对象、数组。
 字符串写法适用于：类名不确定，要动态获取。
 对象写法适用于：要绑定多个样式，个数不确定，名字也不确定。
 数组写法适用于：要绑定多个样式，个数确定，名字也确定，但不确定用不用。
2. style样式

`:style="{fontSize: xxx}"` 其中xxx是动态值。

`:style="[a,b]"` 其中a、b是样式对象。

## 条件渲染

`v-if`
`v-show`

1. v-if
    - `v-if="表达式"`
    - `v-else-if="表达式"`
    - `v-else="表达式"`

    - 适用于：切换频率较低的场景。
    - 特点：不展示的DOM元素直接被移除。
    - 注意：`v-if`可以和:`v-else-if`、`v-else`一起使用，但要求结构不能被“打断”。

2. v-show
    - v-show="表达式"
    - 适用于：切换频率较高的场景。
    - 特点：不展示的DOM元素未被移除，仅仅是使用样式隐藏掉

3. 备注：使用v-if的时，元素可能无法获取到，而使用v-show一定可以获取到。

## 列表渲染

v-for指令:

1. 用于展示列表数据
2. 语法：`v-for="(item, index) in items" :key="item.id"`
3. 可遍历：数组、对象、字符串（用的很少）、指定次数（用的很少）

```html
<li v-for:"(p,index) in persons" :key="p.id">
 {{p.name}} --- {{p.age}}
<li>
```

key的作用和原理

面试题：react、vue中的key有什么作用？（key的内部原理）

1. 虚拟DOM中key的作用：
key是虚拟DOM对象的标识，当数据发生变化时，Vue会根据【新数据】生成【新的虚拟DOM】,
随后Vue进行【新虚拟DOM】与【旧虚拟DOM】的差异比较，比较规则如下：

2. 对比规则：
    1. 旧虚拟DOM中找到了与新虚拟DOM相同的key：
        1. 若虚拟DOM中内容没变, 直接使用之前的真实DOM！
        2. 若虚拟DOM中内容变了, 则生成新的真实DOM，随后替换掉页面中之前的真实DOM。
    2. 旧虚拟DOM中未找到与新虚拟DOM相同的key，创建新的真实DOM，随后渲染到到页面。

3. 用index作为key可能会引发的问题：
   1. 若对数据进行：逆序添加、逆序删除等破坏顺序操作:会产生没有必要的真实DOM更新 ==> 界面效果没问题, 但效率低。
   2. 如果结构中还包含输入类的DOM：会产生错误DOM更新 ==> 界面有问题。
4. 开发中如何选择key?:
    1. 最好使用每条数据的唯一标识作为key, 比如id、手机号、身份证号、学号等唯一值。
    2. 如果不存在对数据的逆序添加、逆序删除等破坏顺序操作，仅用于渲染列表用于展示，使用index作为key是没有问题的。

列表过滤

```js
new Vue({
 el:'#root',
 data:{
  keyWord:'',
  persons:[
  {id:'001',name:'马冬梅',age:19,sex:'女'},
  {id:'002',name:'周冬雨',age:20,sex:'女'},
  {id:'003',name:'周杰伦',age:21,sex:'男'},
  {id:'004',name:'温兆伦',age:22,sex:'男'} ]
 },
 
 computed:{
  filPerons(){
  return this.persons.filter((p)=>{
   return p.name.indexOf(this.keyWord) !== -1
  })
  if(this.sortType){
   arr.sort((p1,p2)=>{
   return this.sortType === 1 ? p2.age-p1.age : p1.age-p2.age
   })
  }
  return arr
 }
})
```

Vue.set

Vue监视数据的原理：

1. vue会监视data中所有层次的数据。
2. 如何监测对象中的数据？
    1. 通过`setter`实现监视，且要在`new Vue`时就传入要监测的数据。
        1. 对象中后追加的属性，Vue默认不做响应式处理
        2. 如需给后添加的属性做响应式，请使用如下API：
            - `Vue.set(target，propertyName/index，value)`
            - `vm.$set(target，propertyName/index，value)`
3. 如何监测数组中的数据？ 通过包裹数组更新元素的方法实现，本质就是做了两件事：
    1. 调用原生对应的方法对数组进行更新。
    2. 重新解析模板，进而更新页面。
4. 在Vue修改数组中的某个元素一定要用如下方法：
    1. 使用这些API:`push()、pop()、shift()、unshift()、splice()、sort()、reverse()`
    2. `Vue.set()`或 `vm.$set()`

特别注意：`Vue.set()` 和 `vm.$set()` 不能给vm 或 vm的根数据对象 添加属性！！！

## 收集表单数据

todo

## 过滤器

定义：对要显示的数据进行特定格式化后再显示（适用于一些简单逻辑的处理）。
语法：

1. 注册过滤器：`Vue.filter(name,callback)` 或 `new Vue{filters:{}}`
2. 使用过滤器：`{{ xxx | 过滤器名}} 或 v-bind:属性 = "xxx | 过滤器名"`
备注：
    1. 过滤器也可以接收额外参数、多个过滤器也可以串联
    2. 并没有改变原本的数据, 是产生新的对应的数据

## 内置指令

`v-text`
`v-html`
`v-clock`
`v-once`
`v-pre`

| 指令      | 简写  | 描述         | eg                               |
| ------- | --- | ---------- | -------------------------------- |
| v-text  |     | 普通文本       |                                  |
| v-model |     | 双向绑定       |                                  |
| v-html  |     | 真正的html    | `<span v-html="rawHtml"></span>` |
| v-on    | @   | 绑定事件       |                                  |
| v-show  |     |            |                                  |
| v-if    |     |            |                                  |
| v-for   |     |            |                                  |
| v-bind  | :   | 作用在html属性上 |                                  |

修饰符

## 自定义指令

需求1：定义一个`v-big`指令，和`v-text`功能类似，但会把绑定的数值放大10倍。
需求2：定义一个`v-fbind`指令，和`v-bind`功能类似，但可以让其所绑定的input元素默认获取焦点。

自定义指令总结：
一、定义语法：

1. 局部指令：

    ```js
    new Vue({ new Vue({

    directives:{指令名:配置对象} 或 directives{指令名:回调函数}

    }) })
    ```

2. 全局指令：

    ```js
    Vue.directive(指令名,配置对象) 或 Vue.directive(指令名,回调函数)
    ```

二、配置对象中常用的3个回调：

1. `bind`：指令与元素成功绑定时调用。
2. `inserted`：指令所在元素被插入页面时调用。
3. `update`：指令所在模板结构被重新解析时调用。

三、备注：

1. 指令定义时不加v-，但使用时要加v-；
2. 指令名如果是多个单词，要使用`kebab-case`命名方式，不要用`camelCase`命名。

## 生命周期

生命周期：

1. 又名：生命周期回调函数、生命周期函数、生命周期钩子。
2. 是什么：Vue在关键时刻帮我们调用的一些特殊名称的函数。
3. 生命周期函数的名字不可更改，但函数的具体内容是程序员根据需求编写的。
4. 生命周期函数中的`this`指向是`vm` 或 组件实例对象`vc`。

![lifecycle](https://v2.cn.vuejs.org/images/lifecycle.png)

[vue 生命周期钩子](https://v2.cn.vuejs.org/v2/api/#%E9%80%89%E9%A1%B9-%E7%94%9F%E5%91%BD%E5%91%A8%E6%9C%9F%E9%92%A9%E5%AD%90)

- 初始化显示
  - `beforeCreate`
  - `created`
  - `beforeMount`
  - `mounted`
- 更新状态
  - `beforeUpdate`
  - `updated`
- 激活
  - `activated`   被 keep-alive 缓存的组件激活时调用。
  - `deactivated`    被 keep-alive 缓存的组件失活时调用。
- 销毁
  - `beforeDestroy`
  - `destroyed`

`mounted` //Vue完成模板的解析并把初始的真实DOM元素放入页面后（挂载完毕）调用mounted

```js
new Vue({
 el:'#root',
 // template:`
 //  <div>
 //      <h2>当前的n值是：{{n}}</h2>
 //      <button @click="add">点我n+1</button>
 //  </div>
 // `,
 data:{
  n:1
 },
 methods: {
  add(){
   console.log('add')
   this.n++
  },
  bye(){
   console.log('bye')
   this.$destroy()
  }
 },
 watch:{
  n(){
   console.log('n变了')
  }
 },
 beforeCreate() {
  console.log('beforeCreate')
 },

 created() {
  console.log('created')
 },
 beforeMount() {
  console.log('beforeMount')
 },
 mounted() {
  console.log('mounted')
 },
 beforeUpdate() {
  console.log('beforeUpdate')
 },
 updated() {
  console.log('updated')
 },
 beforeDestroy() {
  console.log('beforeDestroy')
 },
 destroyed() {
  console.log('destroyed')
 },
})
```

常用的生命周期钩子：

1. `mounted:` 发送ajax请求、启动定时器、绑定自定义事件、订阅消息等【初始化操作】。
2. `beforeDestroy`: 清除定时器、解绑自定义事件、取消订阅消息等【收尾工作】。

关于销毁Vue实例

1. 销毁后借助Vue开发者工具看不到任何信息。
2. 销毁后自定义事件会失效，但原生DOM事件依然有效。
3. 一般不会在`beforeDestroy`操作数据，因为即便操作数据，也不会再触发更新流程了。

# 第2章 组件化编程

## 非单文件组件

## 单文件组件

- 组成
  - 模版 `template`
  - `js`
  - 样式`css`

# 第3章 使用Vue脚手架

使用vue.config.js可以对脚手架进行个性化定制，详情见：[Vue-Cli](https://cli.vuejs.org/zh)

## 脚手架开发

初始化脚手架

`npm install -g @vue/cli`
`vue create projectname`
`npm run serve`
`npm inspect -> output.js

模版项目结构
![模版项目结构](https://duke-1258882975.cos.ap-guangzhou.myqcloud.com/picture/202406291050014.png)
`main.js` 是项目的入口

`render`函数完成了这个功能：将App组件放入容器中

App.vue

vue.config.js
vue inspect > output.js
npm  类似于`maven`，是js依赖包的管理工具
`packege.json`  类似与maven 项目中的pom.xml  定义了项目的依赖等信息

```json
{  
  "name": "projectname",  
  "version": "1.0.0",  
  "description": "",  
  "main": "index.js",  
  "scripts": {  
    "test": "echo \"Error: no test specified\" && exit 1"  },  
  "keywords": [],  
  "author": "",  
  "license": "ISC",  
  "dependencies": {  
    "jquery": "^3.6.1"  
  }  
}
```

## ref属性

在模版标签或html标签内 添加`ref`属性   给节点打标签
在vm实例内部可以通过`this.$refs.name`获得真实的dom对象或组件实例对象。

## props配置

父组件中使用组件名创建子组件实例，通过标签属性传值。
子组件接收props的几种方式

```js
 //简单声明接收
 // props:['name','age','sex']
 //接收的同时对数据进行类型限制
 /* props:{
  name:String,
  age:Number,
  sex:String
 } */
 //接收的同时对数据：进行类型限制+默认值的指定+必要性的限制
 props:{
  name:{
   type:String, //name的类型是字符串
   required:true, //name是必要的
  },
  age:{
   type:Number,
   default:99 //默认值
  },
  sex:{
   type:String,
   required:true
  }
 }
```

## `mixin`混入(合)

1. 功能：可以把多个组件共用的配置提取成一个混入对象
2. 使用方式：

- 第一步定义mixin混合：

```js
{
 data(){....},
 methods:{....},
 create:{ ... }
 ....
}
```

- 第二步使用混入：
  - 全局混入：`Vue.mixin(xxx)`​
  - 局部混入：`mixins:['xxx']`

## 插件

1. Vue 插件是一个包含 install 方法的对象
2. 通过 install 方法给 Vue 或 Vue 实例添加方法, 定义全局指令等
`plugin.js`

```js
export default {
    install(Vue,x,y,z){
        console.log(x,y,z)
        //全局过滤器
        Vue.filter('mySlice',function(value){
            return value.slice(0,4)
        }) 
        //定义全局指令
        Vue.directive('fbind',{
            //指令与元素成功绑定时（一上来）
            bind(element,binding){
                element.value = binding.value
            },
            //指令所在元素被插入页面时
            inserted(element,binding){
                element.focus()
            },
            //指令所在的模板被重新解析时
            update(element,binding){
                element.value = binding.value
            }
        })
        //定义混入
        Vue.mixin({
            data() {
                return {
                    x:100,
                    y:200
                }
            },
        })
        //给Vue原型上添加一个方法（vm和vc就都能用了）
        Vue.prototype.hello = ()=>{alert('你好啊')}
    }
}
```

```js
import plugins from './plugins'
Vue.use(plug)
```

# todo案例

组件化编码流程（通用）

1. 实现静态组件：抽取组件，使用组件实现静态页面效果
2. 展示动态数据
    1. 数据的类型、名称是什么
    2. 数据存储在哪个组件
3. 交互--从绑定事件监听开始

## scpoed

## 本地存储

```js
localStorage.setItem
localStorage.getItem

sessionStorage.setItem
sessionStorage.getItem
```

## 组件自定义事件

1. 绑定事件监听

    ```js
    <Header @addTodo="addTodo"/>
    ```

    或者

    ```js
    <Header ref="header"/> 
    this.$refs.header.$on('addTodo', this.addTodo)
    ```

2. 触发事件
`this.$emit('addTodo', todo)`

## 全局事件总线

1. Vue 原型对象上包含事件处理的方法
    1. `$on(eventName, listener)`: 绑定自定义事件监听
    2. `$emit(eventName, data)`: 分发自定义事件
    3. `$off(eventName)`: 解绑自定义事件监听
    4. `$once(eventName, listener)`: 绑定事件监听, 但只能处理一次
2. 所有组件实例对象的原型对象的原型对象就是 Vue 的原型对象
    1. 所有组件对象都能看到 Vue 原型对象上的属性和方法
    2. `Vue.prototype.$bus = new Vue()`, 所有的组件对象都能看到`$bus` 这个属性 对象
3. 全局事件总线
    1. 包含事件处理相关方法的对象(只有一个)
    2. 所有的组件都可以得到

```javascript
//创建vm
new Vue({
 el:'#app',
 render: h => h(App),
 beforeCreate() {
  Vue.prototype.$bus = this //安装全局事件总线
 },

})
```

在组件上定义`$on` 和 `$emit`方法进行数据传输

1. 指定事件总线对象

    ```js
    new Vue({
    beforeCreate () { // 尽量早的执行挂载全局事件总线对象的操作 
    Vue.prototype.$globalEventBus = this 
    }, 
    }).$mount('#root')
    ```

2. 绑定事件

    ```js
    this.$globalEventBus.$on('deleteTodo', this.deleteTodo)
    ```

3. 触发事件

    ```js
    this.$globalEventBus.$emit('deleteTodo', this.index)
    ```

4. 解绑事件

    ```js
    this.$globalEventBus.$off('deleteTodo')
    ```

## 消息发布与订阅

消息订阅与发布 `pubsub-js`

## nextTick

<https://v2.cn.vuejs.org/v2/api/#vm-nextTick>

# 第4章 Vue中的ajax

## 配置代理服务器

解决浏览器 跨域问题

### 方法一

```json
// vue.config.js
{ 
//开启代理服务器（方式一）
 devServer: { 
  proxy: 'http://localhost:5000'
 }
}
```

### 方法二

```json
// vue.config.js
{
 //开启代理服务器（方式二）
 devServer: {
  proxy: {
   '/atguigu': { 
    target: 'http://localhost:5000',  
    pathRewrite:{'^/atguigu':''},   
    // ws: true, //用于支持websocket  
    // changeOrigin: true //用于控制请求头中的host值  
   },  
   '/demo': {  
    target: 'http://localhost:5001', 
    pathRewrite:{'^/demo':''},  
    // ws: true, //用于支持websocket  
    // changeOrigin: true //用于控制请求头中的host值 
   }
  }
 
 }
}
```

vue-resource

## 插槽

### 作用

父组件向子组件传递带数据的标签，当一个组件有不确定的结构时, 就需要使用 `slot` 技术，注意：插槽内容是在父组件中编译后, 再传递给子组件的。

### 分类

### 使用方式

默认插槽

```vue
<slot>
```

具名插槽

作用域插槽

# 第5章 Vuex

概念：专门在 Vue 中实现集中式状态（数据）管理的一个 Vue 插件，对 vue 应 用中多个组件的共享状态进行集中式的管理（读/写），也是一种组件间通信的方 式，且适用于任意组件间通信。

什么时候用`Vuex`

1. 多个组件依赖于同一状态
2. 来自不同组件的行为需要变更同一状态

`Vuex`工作原理图
![vuex工作原理图](https://duke-1258882975.cos.ap-guangzhou.myqcloud.com/picture/202406291119772.png)

1. `state`  用于存储数据
2. `action`中调用`commit`
3. `mutation`  用于操作数据（state）

组件中`this.$store.dispatch（'actionName',data）`  触发`action`

```js
//准备actions——用于响应组件中的动作
const actions = {
    /* jia(context,value){
        console.log('actions中的jia被调用了')
        context.commit('JIA',value)
    },
    jian(context,value){
        console.log('actions中的jian被调用了')
        context.commit('JIAN',value)
    }, */
    jiaOdd(context,value){
        console.log('actions中的jiaOdd被调用了')
        if(context.state.sum % 2){
            context.commit('JIA',value)
        }
    },
    jiaWait(context,value){
        console.log('actions中的jiaWait被调用了')
        setTimeout(()=>{
            context.commit('JIA',value)
        },500)
    }
}

//准备mutations——用于操作数据（state）
const mutations = {
    JIA(state,value){
        console.log('mutations中的JIA被调用了')
        state.sum += value
    },
    JIAN(state,value){
        console.log('mutations中的JIAN被调用了')
        state.sum -= value
    }
}
//准备state——用于存储数据
const state = {
    sum:0 //当前的和
}

//创建并暴露store
export default new Vuex.Store({
    actions,
    mutations,
    state,
    getters
})
```

`action`  用于响应组件中的动作

## Getters

```js
//准备getters——用于将state中的数据进行加工
const getters = {
    bigSum(state){
        return state.sum*10
    }
}
```

## mapState  mapState

- `mapState`
- `mapGettes`

## mapActions mapMutations

- `mapActions`
- `mapMutations`

```js
import {mapState,mapGetters,mapMutations,mapActions} from 'vuex'
export default {
 name:'Count',
 data() {
  return {
   n:1, //用户选择的数字
  }
 },
 computed:{
 //靠程序员自己亲自去写计算属性
 /* sum(){
  return this.$store.state.sum
 },
 school(){
  return this.$store.state.school
 },
 subject(){
  return this.$store.state.subject
 }, */
 //借助mapState生成计算属性，从state中读取数据。（对象写法）
 // ...mapState({he:'sum',xuexiao:'school',xueke:'subject'}),
 //借助mapState生成计算属性，从state中读取数据。（数组写法）
 ...mapState(['sum','school','subject']),
 
 /* ******************************************************************** */
 /* bigSum(){
  return this.$store.getters.bigSum
 }, */
 //借助mapGetters生成计算属性，从getters中读取数据。（对象写法）
 // ...mapGetters({bigSum:'bigSum'})
 //借助mapGetters生成计算属性，从getters中读取数据。（数组写法）
 ...mapGetters(['bigSum'])
 },
 methods: {
  //程序员亲自写方法
  /* increment(){
   this.$store.commit('JIA',this.n)
  },
  decrement(){
   this.$store.commit('JIAN',this.n)
  }, */
  //借助mapMutations生成对应的方法，方法中会调用commit去联系mutations(对象写法)
  ...mapMutations({increment:'JIA',decrement:'JIAN'}),
  //借助mapMutations生成对应的方法，方法中会调用commit去联系mutations(数组写法)
  // ...mapMutations(['JIA','JIAN']),
  /* ************************************************* */
  //程序员亲自写方法
  /* incrementOdd(){
  this.$store.dispatch('jiaOdd',this.n)
  },
  incrementWait(){
   this.$store.dispatch('jiaWait',this.n)
  }, */
  //借助mapActions生成对应的方法，方法中会调用dispatch去联系actions(对象写法)
  ...mapActions({incrementOdd:'jiaOdd',incrementWait:'jiaWait'})
  //借助mapActions生成对应的方法，方法中会调用dispatch去联系actions(数组写法)
  // ...mapActions(['jiaOdd','jiaWait'])
 },

}
```

## vuex模块化编码

`namespaced: true`

# 第 6 章：vue-router

## 6.1 相关理解

### 6.1.1 vue-router 的理解

Vue 的一个插件库，专门用来实现 SPA 应用

### 6.1.2 对 SPA 应用的理解

1. 单页 Web 应用（single page web application，SPA）。
2. 整个应用只有一个完整的页面。
3. 点击页面中的导航链接不会刷新页面，只会做页面的局部更新。
4. 数据需要通过 ajax 请求获取。

### 6.1.3 路由的理解

1. 什么是路由?
    1. 一个路由就是一组映射关系（key - value）
    2. `key` 为路径, `value` 可能是 `function` 或 `component`
2. 路由分类
    1. 后端路由：
        1. 理解：`value` 是 `function`, 用于处理客户端提交的请求。
        2. 工作过程：服务器接收到一个请求时, 根据请求路径找到匹配的函数 来处理请求, 返回响应数据。
    2. 前端路由：
        1. 理解：`value` 是 `component`，用于展示页面内容。
        2. 工作过程：当浏览器的路径改变时, 对应的组件就会显示。

## 基本路由

路由器 `router`
路由 `route`
很多组`route` 组成了一个`router`
总结：编写使用路由的3步

1. 定义路由组件
2. 注册路由
3. 使用路由

```js
//创建并暴露一个路由器

export default new VueRouter({
routes:[
 {
  path:'/about',
  component:About
 },
 {
  path:'/home',
  component:Home
 }
 ]
})
```

```html
<router-link class="list-group-item" 
    active-class="active" 
    to="/home">Home
</router-link>

<router-view></router-view>
```

嵌套（多级）路由

```js
//创建并暴露一个路由器

export default new VueRouter({
 routes:[
  {
   path:'/about',
   component:About
  },
  {
   path:'/home',
   component:Home,
   children:[
    {
     path:'news',  // 子路由不用斜杠开头
     component:News,
    },
    {
     path:'message',
     component:Message,
    }
   ]
  }
 ]
})
```

- 路由的`query`参数

```vue
<!-- 跳转路由并携带query参数，to的字符串写法 -->
<!-- <router-link :to="`/home/message/detail?id=${m.id}&title=${m.title}`">{{m.title}}</router-link>&nbsp;&nbsp; -->
<!-- 跳转路由并携带query参数，to的对象写法 -->

<router-link 
  :to="{
  path:'/home/message/detail',
  query:{
    id:m.id,
    title:m.title
   }
  }">
{{m.title}}
</router-link>
```

- 命名路由
name

```vue
<!-- 跳转路由并携带query参数，to的字符串写法 -->
<!-- <router-link :to="`/home/message/detail?id=${m.id}&title=${m.title}`">{{m.title}}</router-link>&nbsp;&nbsp; -->
<!-- 跳转路由并携带query参数，to的对象写法 -->
<router-link :to="{
 name:'xiangqing',
 query:{
 id:m.id,
 title:m.title
}
}">
{{m.title}}
</router-link>
```

- params参数   `pathparameter`

```vue
<!-- 跳转路由并携带params参数，to的字符串写法 -->
<!-- <router-link :to="`/home/message/detail/${m.id}/${m.title}`">{{m.title}}</router-link>&nbsp;&nbsp; -->
<!-- 跳转路由并携带params参数，to的对象写法 -->

<router-link :to="{
 name:'xiangqing',
 params:{
 id:m.id,
 title:m.title
}
}">
{{m.title}}
</router-link>
```

- 路由props

```js
//props的第一种写法，值为对象，该对象中的所有key-value都会以props的形式传给Detail组件。
// props:{a:1,b:'hello'}
//props的第二种写法，值为布尔值，若布尔值为真，就会把该路由组件收到的所有params参数，以props的形式传给Detail组件。
// props:true
//props的第三种写法，值为函数
props($route){
 return {
  id:$route.query.id,
  title:$route.query.title,
  a:1,
  b:'hello'
 }
}
```

router-link的`replaces`属性

- 类型: `boolean`
- 默认值: `false`
    设置 `replace` 属性的话，当点击时，会调用 `router.replace()` 而不是 `router.push()`，于是导航后不会留下 history 记录。

```vue
<router-link :to="{ path: '/abc'}" replace></router-link>
```

编程式路由导航
在组件方法中`this.$router.push()`

- `router.push(location, onComplete?, onAbort?)`
- `router.replace(location, onComplete?, onAbort?)`

相关 API：

1. `this.$router.push(path)`: 相当于点击路由链接(可以返回到当前路由界面)
2. `this.$router.replace(path)`: 用新路由替换当前路由(不可以返回到当前路由界面)
3. `this.$router.back()`: 请求(返回)上一个记录路由
4. `this.$router.go(-1)`: 请求(返回)上一个记录路由
5. `this.$router.go(1)`: 请求下一个记录路由
缓存路由组件
`<keepAlive>`

路由组件 的切换会导致旧组件的销毁和组件的创建（生命周期）
两个新的生命周期钩子

- `activate`
- `deactivate`

## 路由守卫

全局路由守卫

```js
//全局前置路由守卫————初始化的时候被调用、每次路由切换之前被调用
router.beforeEach((to,from,next)=>{
console.log('前置路由守卫',to,from)
 if(to.meta.isAuth){ //判断是否需要鉴权
  if(localStorage.getItem('school')==='atguigu'){
  next()
  }else{
  alert('学校名不对，无权限查看！')
  }
 }else{
  next()
 }
})

//全局后置路由守卫————初始化的时候被调用、每次路由切换之后被调用
router.afterEach((to,from)=>{
console.log('后置路由守卫',to,from)
document.title = to.meta.title || '硅谷系统'
})
```

独享路由守卫   单独在路由守卫中配置(router里的一个配置项)

```js
{
 name:'xinwen',
 path:'news',
 component:News,
 meta:{isAuth:true,title:'新闻'},
 beforeEnter: (to, from, next) => {
  console.log('独享路由守卫',to,from)
  if(to.meta.isAuth){ //判断是否需要鉴权
   if(localStorage.getItem('school')==='atguigu'){
    next()
   }else{
    alert('学校名不对，无权限查看！')
   }
  }else{
   next()
  }
 }
}
```

组件内路由守卫

```js
//通过路由规则，进入该组件时被调用
beforeRouteEnter (to, from, next) {
 console.log('About--beforeRouteEnter',to,from)
 if(to.meta.isAuth){ //判断是否需要鉴权
  if(localStorage.getItem('school')==='atguigu'){
   next()
  }else{
   alert('学校名不对，无权限查看！')
  }
 }else{
 next()
 }
},
//通过路由规则，离开该组件时被调用
beforeRouteLeave (to, from, next) {
 console.log('About--beforeRouteLeave',to,from)
 next()
}
```

`history`模式和`hash`模式

## Axios
