---
title: React 框架
description: React 19 的核心机制与完整实践：JSX、组件与状态、Hooks 体系、渲染与协调原理、并发特性、Server Components、性能优化与生态选型
tags:
  - frontend
  - react
  - javascript
  - hooks
  - typescript
date: 2026-10-20
aliases:
  - react19
  - react-guide
  - reactjs
---

# React 框架

## 概述

React 是 Meta 开源的 **声明式 UI 库**。它只解决一件事：**把状态映射成界面，并在状态变化时高效地更新界面**。路由、数据请求、状态管理、构建都不在 React 本身范围内，由生态提供。

理解 React 只需抓住三条主线：

1. **UI = f(state)**。同一份 state 永远渲染出同一份 UI，开发者只描述"是什么"，不写"怎么改 DOM"。
2. **组件化 + 单向数据流**。父组件通过 props 向下传递数据，子组件通过回调向上通知，数据只有一条流动方向，因此可预测、可调试。
3. **重渲染是廉价的，DOM 操作才是昂贵的**。React 在内存中重算整棵树的描述（虚拟 DOM / Fiber），再与上一版对比，只对真正变化的部分打补丁。

### 版本现状（本文基于 React 19.3 编写）

| 版本 | 发布时间 | 关键内容 |
|------|----------|----------|
| 19.0 | 2024-12 | Actions、`use()`、`useActionState`、`useOptimistic`、`useFormStatus`、ref 作为 prop、Context 作为 Provider、ref 清理函数 |
| 19.1 | 2025-03 | Owner Stacks 调试、Suspense 与流式渲染改进 |
| 19.2 | 2025-10 | `<Activity>`、`useEffectEvent`、`cacheSignal`、Partial Pre-rendering、Suspense 边界批处理 |
| 19.3 | 2026-09 | `<ViewTransition>` 稳定、Fragment Refs 稳定、Trusted Types 支持、Transition 独立渲染互不影响 |

配套但**独立**的一件事：**React Compiler**（原 React Forget）于 2025-10 发布 v1.0，是一个构建期 Babel 插件，自动做记忆化。它不是 React 19 的内置功能，需要单独安装配置，且对 React 17/18 也可用。

### 适合与不适合

**适合**：交互密集的中后台、编辑器、数据看板、跨端（React Native）、需要庞大生态与招人容易的团队项目。

**不适合**：纯内容展示站点（用 Astro / 静态站更省事）、对包体积极度敏感且无交互的场景、以及无法接受构建链复杂度的极小项目。

### 前置知识

- [[javascript|JavaScript]] 基础（闭包、解构、模块化）
- [[es6|ES6]] 语法（箭头函数、解构、模板字符串）
- [[html|HTML]] / [[css|CSS]]
- 包管理与构建：[[npm|NPM]]、[[vite|Vite 构建工具]]

## 一、快速上手

### 1.1 用脚手架创建项目

```bash
# Vite 模板（纯客户端 SPA，最轻量）
npm create vite@latest my-app -- --template react-ts

# Next.js（带 Server Components / SSR / 路由，新项目主流选择）
npx create-next-app@latest my-app

cd my-app && npm install && npm run dev
```

两者定位不同：Vite 只给你一个客户端渲染的 SPA 壳子，Next.js 提供全栈架构（RSC + Server Actions + 文件路由）。**选型的分水岭是"要不要服务端渲染和数据就近获取"**——不确定时，纯内部系统选 Vite，面向 C 端、有 SEO/首屏要求选 Next.js。

### 1.2 最小工程结构

```text
my-app/
├── index.html            # Vite 入口（不是 src/main.tsx）
├── package.json
├── vite.config.ts
└── src/
    ├── main.tsx          # React 挂载点
    ├── App.tsx
    ├── components/       # 通用组件
    ├── features/         # 按业务域组织（推荐）
    │   └── order/
    │       ├── OrderList.tsx
    │       ├── useOrders.ts
    │       └── api.ts
    └── hooks/            # 跨业务复用的自定义 Hook
```

> **目录组织建议**：不要按"技术角色"（components / hooks / utils 各一个大目录）堆文件，而按**业务特性（feature）**分目录，通用组件才放进 `components/`。一个 feature 目录下的组件、Hook、API 调用一起变更，心智负担小得多。

### 1.3 挂载点

React 19 只有一套客户端 API，即 `createRoot`（`ReactDOM.render` 已于 18 起移除）：

```tsx
// src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

const container = document.getElementById('root');
if (!container) throw new Error('#root not found');

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`StrictMode` 只在开发环境生效，它会**故意重复调用**组件的渲染函数与 Effect（挂载→卸载→再挂载），用来暴露"没有正确清理副作用"和"渲染期做了副作用"这两类问题。生产构建无此行为，也**没有性能开销**。

## 二、JSX

JSX 是语法糖，不是模板字符串。它会被编译成函数调用——React 17 之后使用自动 runtime，无需 `import React`：

```jsx
// 你写的
const el = <h1 className="title">Hello {name}</h1>;

// 编译结果（react/jsx-runtime）
import { jsx } from 'react/jsx-runtime';
const el = jsx('h1', { className: 'title', children: `Hello ${name}` });
```

### 2.1 JSX 与 HTML 的差异

| HTML 写法 | JSX 写法 | 原因 |
|-----------|----------|------|
| `class="box"` | `className="box"` | `class` 是 JS 保留字 |
| `for="id"` | `htmlFor="id"` | 同上 |
| `style="color:red"` | `style={{ color: 'red' }}` | 接收对象，`-` 转驼峰 |
| `onclick="fn()"` | `onClick={fn}` | 传函数引用，不是字符串 |
| `tabindex="0"` | `tabIndex={0}` | 驼峰命名 |
| `<img src="a.png">` | `<img src="a.png" />` | 必须闭合 |
| 多条属性换行 | 同左 | 大括号里是 JS 表达式 |

### 2.2 表达式、条件与列表

```jsx
function OrderPanel({ orders, user }) {
  return (
    <section>
      {/* 1. 任意 JS 表达式 */}
      <h2>{user.name.toUpperCase()} 的订单</h2>

      {/* 2. 条件渲染：&& 适合"有或无" */}
      {orders.length > 0 && <OrderTable orders={orders} />}

      {/* 3. 三元：适合"二选一" */}
      {orders.length > 0 ? <OrderTable orders={orders} /> : <EmptyHint />}

      {/* 4. 列表：key 必须是稳定且唯一的业务 id */}
      {orders.map((order) => (
        <OrderRow key={order.id} order={order} />
      ))}
    </section>
  );
}
```

**关于 `key` 的三条铁律**：

1. 用**业务 id**，不要用数组下标。列表排序、插入、删除时下标会错位，导致 DOM 复用错误（典型表现：输入框内容跟着错位）。
2. `key` 只在**同一父节点的同层兄弟**之间有意义，换个父节点就不冲突。
3. 实在没有 id 时才用下标，且要保证列表**永不重排、永不增删**（如静态配置项）。

### 2.3 Fragment

组件必须返回单个根节点，不想多包一层 `<div>` 时用 Fragment：

```jsx
import { Fragment } from 'react';

function Columns() {
  return (
    <>
      <td>名称</td>
      <td>价格</td>
    </>
  );
}

// 需要 key 时只能用完整写法（短语法不支持属性）
function Rows({ items }) {
  return items.map((item) => (
    <Fragment key={item.id}>
      <dt>{item.term}</dt>
      <dd>{item.desc}</dd>
    </Fragment>
  ));
}
```

React 19.3 起 Fragment 支持 `ref`，即 **Fragment Refs**：

```jsx
// 19.3+：可以把 ref 直接挂在 Fragment 上，拿到一段连续 DOM 的边界
const ref = useRef(null);

<>
  <Fragment ref={ref}>
    <Child />
    <Child />
  </Fragment>
</>;
```

## 三、组件与 Props

### 3.1 函数组件

React 19 的标准写法只有一种：函数组件。类组件仍可用，但不支持 Server Components，新代码不要写。

```tsx
type Order = { id: string; amount: number; status: 'paid' | 'pending' };

type OrderCardProps = {
  order: Order;
  onRefund?: (id: string) => void;
  children?: React.ReactNode;
};

function OrderCard({ order, onRefund, children }: OrderCardProps) {
  return (
    <article>
      <h3>订单 {order.id}</h3>
      <p>金额：¥{order.amount.toFixed(2)}</p>
      <p>状态：{order.status === 'paid' ? '已支付' : '待支付'}</p>
      {onRefund && (
        <button type="button" onClick={() => onRefund(order.id)}>
          申请退款
        </button>
      )}
      {children}
    </article>
  );
}
```

**组件命名必须大写开头**。小写开头的标签被当作原生 HTML 元素处理。

### 3.2 Props 是只读的

Props 单向向下流动，子组件**永远不能修改** `props.xxx`。要改，就由父组件持有 state 并把修改函数传下来：

```tsx
function Parent() {
  const [count, setCount] = useState(0);
  // 父持有数据 + 修改能力，子只负责渲染和触发
  return <Counter value={count} onChange={setCount} />;
}

function Counter({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <button type="button" onClick={() => onChange(value + 1)}>
      {value}
    </button>
  );
}
```

### 3.3 组合优先于配置

React 官方推崇组合（composition）而非继承或"巨型配置组件"。三种常用模式：

```jsx
// 1) children 插槽：最常用，天然避免"配置地狱"
function Card({ title, children, footer }) {
  return (
    <div className="card">
      <header>{title}</header>
      <main>{children}</main>
      <footer>{footer}</footer>
    </div>
  );
}

// 2) 复合组件（Compound Components）：通过 Context 共享隐式状态
function Tabs({ children, value, onChange }) {
  return (
    <TabsContext.Provider value={{ value, onChange }}>{children}</TabsContext.Provider>
  );
}
Tabs.List = TabList;
Tabs.Panel = TabPanel;
// 用法：<Tabs value={v} onChange={setV}><Tabs.List/>...</Tabs>

// 3) Render Props：把"怎么渲染"交给调用方
function MouseTracker({ render }) {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  return <div onMouseMove={(e) => setPos({ x: e.clientX, y: e.clientY })}>{render(pos)}</div>;
}
```

> **拆分时机**：一个组件超过 200 行、出现多个 `useState` 分属不同关注点、或某段 JSX 需要被复用时，就该拆。但不要为了拆而拆——拆分的真正目的是**隔离重渲染范围**和**隔离变化原因**。

## 四、状态管理：useState

### 4.1 基本语义

```jsx
import { useState } from 'react';

function SearchBox() {
  // 参数为初始值（只在首次渲染生效），返回 [当前值, setter]
  const [keyword, setKeyword] = useState('');
  const [page, setPage] = useState(1);

  return (
    <input
      value={keyword}
      onChange={(e) => {
        setKeyword(e.target.value);
        setPage(1); // 改关键词时重置分页
      }}
    />
  );
}
```

关键行为：

- **setter 是异步的**：调用 `setKeyword('a')` 后立刻读 `keyword` 仍是旧值。要在下一次渲染才拿到新值。
- **同名替换，不是合并**：类组件 `this.setState` 会浅合并，函数组件 `useState` 是整体替换。对象 state 要自己展开。
- **相同值会跳过重渲染**：`Object.is` 判定相等则 React 直接跳过（可能仍会多渲染一次以确认）。

### 4.2 函数式更新

新值依赖旧值时，**必须**用函数式更新，否则在快速连续触发（或批处理合并）时会丢更新：

```jsx
// 错误：连点两次只加 1，因为两次闭包里的 count 都是同一个旧值
<button onClick={() => setCount(count + 1)}>+1</button>

// 正确：React 会把更新排进队列，逐个基于前一个结果计算
<button onClick={() => setCount((prev) => prev + 1)}>+1</button>
```

### 4.3 不可变更新

React 靠**引用比较**判断要不要重渲染。直接改对象/数组，引用没变，界面不会更新：

```jsx
const [user, setUser] = useState({ name: '张三', address: { city: '上海' } });
const [list, setList] = useState([1, 2, 3]);

// 对象：展开
setUser({ ...user, name: '李四' });
// 嵌套对象：逐层展开
setUser({ ...user, address: { ...user.address, city: '北京' } });

// 数组
setList([...list, 4]);                       // 追加
setList(list.filter((n) => n !== 2));        // 删除
setList(list.map((n) => (n === 2 ? 20 : n))); // 修改
setList([...list.slice(0, 1), 99, ...list.slice(2)]); // 插入
```

深层嵌套改起来痛苦时，用 [Immer](https://immerjs.github.io/immer/)（Redux Toolkit 内置）或把 state 拆平。

### 4.4 state 放在哪

| 场景 | 放哪 | 说明 |
|------|------|------|
| 只有一个组件用 | 组件内部 `useState` | 默认选择 |
| 兄弟组件共享 | 提升到最近的共同父组件 | "状态提升" |
| 跨越多层、大量组件 | Context 或外部 store | 避免 props 层层透传 |
| 服务端数据（列表、详情） | 数据请求库（TanStack Query / RSC） | **不要**塞进 `useState` |
| 筛选、分页、排序 | URL 查询参数 | 可分享、可后退、可刷新 |
| 表单提交中/结果 | `useActionState` | React 19 内置 |

**反模式：把能算出来的值存进 state**。

```jsx
// 错误：derived state，需要额外的 effect 去同步，容易不一致
const [fullName, setFullName] = useState('');
useEffect(() => setFullName(`${first} ${last}`), [first, last]);

// 正确：渲染期直接算
const fullName = `${first} ${last}`;

// 只有计算很贵时才用 useMemo
const expensive = useMemo(() => heavyCalc(list), [list]);
```

## 五、副作用：useEffect

`useEffect` 的作用是**让组件与外部系统同步**（网络、订阅、DOM 测量、定时器、第三方库实例）。它不是生命周期钩子的等价物，更不是"state 变化时执行代码"的通用入口。

### 5.1 三种依赖形态

```jsx
// 1) 无依赖数组：每次渲染后都执行（几乎总是写错）
useEffect(() => { console.log('每次渲染'); });

// 2) 空数组：只在挂载后执行一次，卸载时清理
useEffect(() => {
  const timer = setInterval(tick, 1000);
  return () => clearInterval(timer); // 清理函数
}, []);

// 3) 有依赖：依赖变了才重新执行（变了先清理旧的，再跑新的）
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/orders?userId=${userId}`, { signal: controller.signal })
    .then((r) => r.json())
    .then(setOrders);
  return () => controller.abort(); // 竞态保护：userId 变了就取消上一个请求
}, [userId]);
```

### 5.2 清理函数

返回的函数在**下一次 effect 执行前**和**组件卸载时**运行。常见清理项：取消请求、清定时器、移除事件监听、断开 WebSocket、销毁第三方实例。

```jsx
useEffect(() => {
  const socket = new WebSocket(url);
  socket.addEventListener('message', onMessage);
  socket.addEventListener('error', onError);
  return () => {
    socket.removeEventListener('message', onMessage);
    socket.removeEventListener('error', onError);
    socket.close();
  };
}, [url, onMessage, onError]);
```

### 5.3 什么时候**不需要** useEffect

| 你以为需要 | 实际做法 |
|------------|----------|
| 根据 props/state 算一个值 | 渲染期直接算，或 `useMemo` |
| 响应按钮点击 | 事件处理函数里写 |
| 重置子组件 state | 换 `key` 让组件重挂载 |
| 表单提交 | `useActionState` / `<form action>` |
| 请求数据 | 优先 Server Components 或 TanStack Query |
| 通知父组件状态变化 | 在事件里调用，不要在 effect 里 `onChange` |

滥用 effect 的典型后果：多一次渲染往返、出现"闪烁"、以及难以追踪的无限循环。

### 5.4 useEffectEvent：把"事件"从 Effect 里剥离

19.2 引入。经典问题：Effect 里用到了 `theme`，但 `theme` 变化不应该导致重连。

```jsx
function ChatRoom({ roomId, theme }) {
  // Effect Event：总是读到最新的 props/state，但**不进依赖数组**
  const onConnected = useEffectEvent(() => {
    showNotification('已连接', theme);
  });

  useEffect(() => {
    const conn = createConnection(roomId);
    conn.on('connected', () => onConnected());
    conn.connect();
    return () => conn.disconnect();
  }, [roomId]); // 只有 roomId 变化才重连

  return <div>房间 {roomId}</div>;
}
```

约束：只能在组件/Hook 顶层定义，**只能在 Effect 内部调用**，不能作为 props 传下去。需配合 `eslint-plugin-react-hooks@latest`，否则 linter 会把它误报为缺失依赖。

## 六、Hooks 全景

### 6.1 速查表

| Hook | 作用 | 版本 |
|------|------|------|
| `useState` | 组件内状态 | 16.8 |
| `useEffect` | 与外部系统同步 | 16.8 |
| `useLayoutEffect` | DOM 变更后、绘制前同步执行（测量布局） | 16.8 |
| `useContext` | 读取 Context | 16.8 |
| `useReducer` | 复杂状态逻辑（多字段联动） | 16.8 |
| `useRef` | 跨渲染保存可变值 / 拿 DOM 节点 | 16.8 |
| `useImperativeHandle` | 暴露命令式方法给父组件 | 16.8 |
| `useMemo` / `useCallback` | 记忆化值 / 函数 | 16.8 |
| `useTransition` | 标记非紧急更新 | 18 |
| `useDeferredValue` | 延迟一个值，保持旧内容可见 | 18 |
| `useId` | 生成稳定唯一 id（无障碍、SSR 安全） | 18 |
| `useSyncExternalStore` | 订阅外部数据源 | 18 |
| `useInsertionEffect` | CSS-in-JS 注入样式 | 18 |
| `useOptimistic` | 乐观更新 | 19 |
| `useActionState` | 表单动作的状态与 pending | 19 |
| `useFormStatus` | 子组件读取所在表单的提交状态（react-dom） | 19 |
| `use` | 读取 Promise / Context（可条件调用） | 19 |
| `useEffectEvent` | 从 Effect 中抽出非响应式逻辑 | 19.2 |
| `cacheSignal` | RSC 中获知 `cache()` 生命周期结束 | 19.2 |

### 6.2 useReducer

state 是多字段组合、或更新逻辑需要在多处复用时，比一堆 `useState` 更清晰：

```jsx
function reducer(state, action) {
  switch (action.type) {
    case 'field':
      return { ...state, [action.name]: action.value };
    case 'reset':
      return initialState;
    case 'submit/start':
      return { ...state, submitting: true, error: null };
    case 'submit/done':
      return { ...state, submitting: false };
    default:
      throw new Error(`未知 action: ${action.type}`);
  }
}

const initialState = { name: '', phone: '', submitting: false, error: null };

function Form() {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <input
      value={state.name}
      onChange={(e) => dispatch({ type: 'field', name: 'name', value: e.target.value })}
    />
  );
}
```

> 判断标准：超过 3 个互相关联的 `useState`，或同一个 setter 逻辑要在 3 处以上复用，就换 `useReducer`。

### 6.3 useRef：跨渲染的可变盒子

`useRef` 返回一个 `{ current }` 对象，**引用在整个生命周期内不变**，修改它**不触发重渲染**。

```jsx
function Stopwatch() {
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);

  const start = () => {
    if (timerRef.current) return; // 防重复启动：读的是最新值
    timerRef.current = setInterval(() => setElapsed((t) => t + 1), 1000);
  };
  const stop = () => {
    clearInterval(timerRef.current);
    timerRef.current = null;
  };
  useEffect(() => stop, []); // 卸载时清理

  return <span>{elapsed}s</span>;
}
```

拿 DOM 节点（React 19 起 ref 是普通 prop，函数组件**不再需要** `forwardRef`）：

```jsx
function TextInput({ ref, ...props }) {
  return <input ref={ref} {...props} />;
}

function SearchPage() {
  const inputRef = useRef(null);
  return (
    <>
      <TextInput ref={inputRef} placeholder="搜索订单" />
      <button onClick={() => inputRef.current?.focus()}>聚焦</button>
    </>
  );
}
```

React 19 还支持 **ref 清理函数**——DOM 节点移除时自动调用，替代过去的"在 null 分支里手动清理"：

```jsx
<div
  ref={(node) => {
    const observer = new ResizeObserver(cb);
    observer.observe(node);
    return () => observer.disconnect(); // React 19：返回清理函数
  }}
/>
```

需要向父组件暴露方法时用 `useImperativeHandle`，但**优先用 props 与状态**解决，命令式接口是最后手段：

```jsx
function VideoPlayer({ ref }) {
  const videoRef = useRef(null);
  useImperativeHandle(ref, () => ({
    play: () => videoRef.current?.play(),
    pause: () => videoRef.current?.pause(),
  }), []);
  return <video ref={videoRef} />;
}
```

### 6.4 useMemo / useCallback / memo

三者的唯一目的：**保持引用稳定，让下游能跳过重渲染**。

```jsx
const filtered = useMemo(() => list.filter((i) => i.type === type), [list, type]);
const handleClick = useCallback(() => onSelect(id), [onSelect, id]);
const MemoRow = memo(function Row({ item }) { return <li>{item.name}</li>; });
```

**但不要无脑加**。记忆化本身有成本（比较依赖、占内存），对廉价组件是净亏损。判断标准：

- 只有当子组件被 `memo` 包裹，或值要作为**其他 Hook 的依赖**，或计算确实昂贵（> 1ms）时，才需要 `useMemo/useCallback`。
- 开了 React Compiler 之后，绝大多数手写的 `useMemo/useCallback/memo` 都可以删掉（见第九章）。

### 6.5 useContext 与 Context

Context 用于跨层级传递"全局性"数据（主题、语言、当前用户、权限）。

```jsx
import { createContext, useContext, useState } from 'react';

const ThemeContext = createContext('light');

// React 19：Context 本身就可以当 Provider 用，不用写 .Provider
function App({ children }) {
  const [theme, setTheme] = useState('light');
  return <ThemeContext value={theme}>{children}</ThemeContext>;
}

function Toolbar() {
  const theme = useContext(ThemeContext); // 读取
  return <div className={theme}>工具栏</div>;
}
```

**Context 的性能陷阱**：Provider 的 `value` 一变，所有消费者**全部重渲染**，且无法通过 `memo` 阻断（Context 变化会穿透 memo）。优化手段：

1. 拆分 Context：把"值"和"修改函数"分开（函数通常永不变化）。
2. 用 `useMemo` 包裹 `value`，避免每次渲染产生新对象。
3. 高频变化的数据不要用 Context，改用外部 store（Zustand 等带选择器订阅）。

```jsx
// 拆分成两个：StateContext 常变，ActionsContext 稳定
const CountContext = createContext(0);
const SetCountContext = createContext(() => {});

function Provider({ children }) {
  const [count, setCount] = useState(0);
  const setters = useMemo(() => ({ inc: () => setCount((c) => c + 1) }), []);
  return (
    <SetCountContext value={setters}>
      <CountContext value={count}>{children}</CountContext>
    </SetCountContext>
  );
}
```

### 6.6 useTransition 与 useDeferredValue

并发渲染的两把钥匙：把更新标记为**可中断、可延后**，让输入框始终保持响应。

```jsx
function SearchPage() {
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();

  function onChange(e) {
    setKeyword(e.target.value); // 紧急：输入框立刻更新
    startTransition(() => {
      // 非紧急：筛选 1 万条数据，可以被新的输入打断
      setResults(filterBigList(e.target.value));
    });
  }

  return (
    <>
      <input value={keyword} onChange={onChange} />
      {isPending && <Spinner />}
      <ResultList results={results} />
    </>
  );
}
```

`useDeferredValue` 是它的"值版本"——当你拿不到 setter（值来自 props）时使用：

```jsx
function ResultList({ keyword }) {
  const deferredKeyword = useDeferredValue(keyword);
  const isStale = keyword !== deferredKeyword;
  return <ul style={{ opacity: isStale ? 0.6 : 1 }}>{heavyFilter(deferredKeyword)}</ul>;
}
```

> React 19.3 起，各个 Transition **独立渲染**，一个慢 Transition 不再拖住其他无关的 Transition。

### 6.7 useId

生成跨服务端/客户端一致、且不冲突的唯一 id，用于 `label htmlFor`、`aria-describedby` 等：

```jsx
function Field({ label }) {
  const id = useId();
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <input id={id} />
    </>
  );
}
```

不要用它当列表 key（key 应该来自数据）。19.2 起生成的 id 前缀是 `r`（形如 `r1`），在此之前是 `«r»`。

### 6.8 useSyncExternalStore

把 React 之外的可变数据源（Redux store、浏览器 API、第三方库）安全地接入并发渲染。**写库时用，业务代码一般不用**：

```jsx
function useOnlineStatus() {
  return useSyncExternalStore(
    subscribe,   // (onChange) => unsubscribe
    getSnapshot, // () => 当前值，必须返回缓存过的引用
    () => true,  // 服务端渲染时的快照（可选）
  );
}
```

### 6.9 Actions 系列：useActionState / useOptimistic / useFormStatus

这是 React 19 最实用的改动——把"提交中、错误、乐观更新、表单重置"这些样板代码收进框架。

```jsx
import { useActionState } from 'react';

function ChangeName({ name }) {
  // [state, formAction, isPending]
  const [error, submitAction, isPending] = useActionState(
    async (prevState, formData) => {
      const err = await updateName(formData.get('name'));
      return err; // 返回值成为新的 state
    },
    null,
  );

  return (
    <form action={submitAction}>
      <input name="name" defaultValue={name} />
      <button type="submit" disabled={isPending}>{isPending ? '保存中…' : '保存'}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
```

`useOptimistic` 让界面先显示预期结果，请求失败自动回滚：

```jsx
function MessageList({ messages, send }) {
  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages,
    (state, newMessage) => [...state, { ...newMessage, sending: true }],
  );

  async function formAction(formData) {
    const text = formData.get('text');
    addOptimistic({ id: 'tmp', text });      // 立刻上屏
    await send(text);                         // 请求结束后自动回到真实数据
  }

  return (
    <form action={formAction}>
      <input name="text" />
      {optimisticMessages.map((m) => (
        <div key={m.id} style={{ opacity: m.sending ? 0.5 : 1 }}>{m.text}</div>
      ))}
    </form>
  );
}
```

`useFormStatus` 让**深层的提交按钮**自己知道表单是否在提交，不必层层透传 pending：

```jsx
import { useFormStatus } from 'react-dom';

function SubmitButton() {
  const { pending } = useFormStatus(); // 只在 <form> 内部的组件里有效
  return <button type="submit" disabled={pending}>{pending ? '提交中…' : '提交'}</button>;
}
```

### 6.10 use()

`use` 在渲染期读取资源，与 Hook 的区别是**可以条件调用**：

```jsx
import { use } from 'react';

function Comments({ commentsPromise }) {
  // 读 Promise：组件会挂起，由最近的 <Suspense> 显示 fallback
  const comments = use(commentsPromise);
  return comments.map((c) => <p key={c.id}>{c.text}</p>);
}

function Panel({ show, theme }) {
  // 也可以条件调用读 Context（Hook 做不到）
  const value = show ? use(ThemeContext) : null;
  return <div>{value ?? theme}</div>;
}
```

三个要点：

1. `use` 的 Promise 必须由**父组件或缓存层**创建。在渲染里 `use(fetch(url))` 每次都发新请求、永远不 settle，是经典错误。
2. `use` 只能在渲染期调用，不能在事件处理或条件分支外的回调里调用。
3. 读取未缓存的 Promise 时要配合 `Suspense` 使用。

### 6.11 Activity：保留状态的隐藏

19.2 引入，用于"隐藏但保留状态"，替代 `display: none` 或条件渲染：

```jsx
import { Activity } from 'react';

<Activity mode={isVisible ? 'visible' : 'hidden'}>
  <DraftEditor />  {/* hidden 时：DOM 移除、Effect 卸载、状态保留 */}
</Activity>
```

| 方式 | DOM | 状态 | Effect | 适用 |
|------|-----|------|--------|------|
| `{show && <C/>}` | 移除 | 丢失 | 清理 | 默认选择 |
| `display: none` | 保留 | 保留 | 不清理 | 需避免（无障碍与性能问题） |
| `<Activity mode="hidden">` | 移除 | **保留** | 清理 | Tab 面板、多步表单、侧边栏 |

### 6.12 ViewTransition：声明式过渡动画（19.3）

19.3 起稳定，基于浏览器 View Transition API，让元素进入/退出/移动/尺寸变化时自动动画：

```jsx
import { ViewTransition, useState, startTransition } from 'react';

function Expandable() {
  const [show, setShow] = useState(false);
  return (
    <>
      <button
        onClick={() => {
          // 只有标记为 Transition 的更新才会触发动画
          startTransition(() => setShow((v) => !v));
        }}
      >
        {show ? '收起' : '展开'}
      </button>
      {show && (
        <ViewTransition>
          <DetailPanel />
        </ViewTransition>
      )}
    </>
  );
}
```

要点：

- 默认做平滑交叉淡入；可用 View Transition Class 在 CSS 中自定义 `enter` / `exit` / `update` / `share` 四种动画。
- 用 `addTransitionType('next')` 给同一次更新附加类型（如轮播前进/后退方向不同），CSS 中用 `:active-view-transition-type(next)` 区分。
- 包在 `<Suspense>` 外层时，可以在 fallback 切换到真实内容时做动画。
- 目前仅支持 DOM（React Native 支持在开发中）。

### 6.13 自定义 Hook

自定义 Hook 是**复用带状态的逻辑**的唯一方式（注意：不是复用 UI）。命名必须以 `use` 开头，否则 linter 无法校验规则。

```jsx
function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : initialValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}

// 用法：组件里只剩渲染逻辑
function ThemeToggle() {
  const [theme, setTheme] = useLocalStorage('theme', 'light');
  return <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>{theme}</button>;
}
```

### 6.14 Hooks 的两条硬性规则

1. **只能在组件或自定义 Hook 的顶层调用**。不能放在 `if`、`for`、嵌套函数、回调里——Hook 靠**调用顺序**定位状态槽位，顺序错了状态就串位。
2. **只能在函数组件或自定义 Hook 中调用**，普通 JS 函数不行。

用 `eslint-plugin-react-hooks` 自动检查（v6 起默认 flat config，`recommended` 预设已包含编译器规则）：

```bash
npm install -D eslint-plugin-react-hooks@latest
```

## 七、渲染机制与协调原理

理解这一章，前面所有"为什么"都会串起来。

### 7.1 一次更新的三个阶段

```text
1. Trigger（触发）
   setState / props 变化 / context 变化 / 父组件重渲染
        ↓
2. Render（渲染 / 协调）
   调用组件函数 → 得到新的元素树 → 与旧 Fiber 树 diff → 收集副作用
   【并发模式下此阶段可中断、可丢弃、可重做】
        ↓
3. Commit（提交）
   一次性同步执行 DOM 变更 → 运行 layout effect → 浏览器绘制 → 运行 passive effect
   【此阶段不可中断】
```

**"渲染"不等于"更新 DOM"**。组件函数被调用了，不代表 DOM 变了——diff 后无差异就不动 DOM。这也是为什么 React 敢让你随便重渲染。

### 7.2 Fiber 架构

Fiber 是 React 16 起的内部数据结构，本质是一个**带指针的链表节点**，每个节点对应一个组件或 DOM 元素：

```text
FiberNode {
  type, key,                 // 元素类型与身份
  stateNode,                 // 对应的真实 DOM 或类组件实例
  return / child / sibling,  // 父 / 第一个子 / 下一个兄弟（构成树）
  memoizedState,             // 该组件的 Hook 链表头
  alternate,                 // 指向另一棵树上的对应节点（双缓冲）
  flags,                     // 需要执行的副作用标记（插入/更新/删除）
  lanes,                     // 优先级
}
```

关键设计：

- **树变链表**：把递归遍历改成可随时中断/恢复的循环，这是并发渲染能实现的基础。
- **双缓冲**：同时存在 `current`（屏幕上）和 `workInProgress`（正在构建）两棵树，构建完成后一次性切换指针。
- **Hook 存在 Fiber 上**：`memoizedState` 是一条单向链表，每个 Hook 一个节点——这就是"Hook 必须按固定顺序调用"的根本原因。

### 7.3 协调算法（Diff）

React 的 diff 不是暴力树比对，而是基于两条启发式假设，把复杂度从 O(n³) 降到 O(n)：

1. **不同类型的元素产生不同的树**：`<div>` 变 `<span>`，整个子树销毁重建，状态全丢。
2. **同层节点靠 `key` 识别身份**：没有 key 就按位置比对。

```text
旧: <ul>           新: <ul>
      <li key="a">       <li key="c">   ← key 变了位置，React 移动 DOM 节点而非重建
      <li key="b">       <li key="a">
      <li key="c">       <li key="b">
```

**组件实例是否保留，取决于它在树中的位置和类型**：

```jsx
// 位置/类型相同 → 同一个实例，state 保留
{isAdmin ? <Panel /> : <Panel />}

// 类型不同 → 卸载旧的、挂载新的，state 丢失
{isAdmin ? <AdminPanel /> : <UserPanel />}

// 想强制重置某个组件的状态 → 换 key
<UserForm key={userId} userId={userId} />
```

### 7.4 自动批处理

React 18 起，所有更新（**包括** Promise 回调、`setTimeout`、原生事件里的）都会自动合并成一次渲染：

```jsx
function handleClick() {
  setA(1);
  setB(2);
  setC(3);
} // 只触发一次重渲染

fetch('/api').then(() => {
  setA(1);
  setB(2);
}); // React 18+ 同样只渲染一次（18 之前是两次）
```

需要跳过批处理、强制同步读取 DOM 时用 `flushSync`（慎用，会破坏并发收益）：

```jsx
import { flushSync } from 'react-dom';
flushSync(() => setCount(1)); // 立刻同步提交
```

### 7.5 并发渲染（Concurrent Rendering）

核心思想：**渲染可中断**。React 把更新分成不同优先级（lane）：

| 优先级 | 来源 | 行为 |
|--------|------|------|
| 同步 | `flushSync`、离散输入（点击、按键） | 立刻完成，不可中断 |
| 默认 | `setState` 普通更新 | 正常调度 |
| Transition | `startTransition` / `useDeferredValue` | 可中断、可延后、可被后续更新抢占 |

一次 Transition 渲染进行到一半时来了新的输入，React 会**丢弃**已做的一半工作，重新开始。这就是为什么 `startTransition` 能让大数据量筛选下的输入框不卡顿。

### 7.6 Suspense

组件在渲染中"挂起"（读取未就绪的 Promise），React 就显示最近的 `Suspense` fallback，就绪后再渲染真实内容：

```jsx
<Suspense fallback={<Skeleton />}>
  <OrderDetail id={id} />   {/* 内部 use(fetchOrder(id)) 会挂起 */}
</Suspense>
```

要点：

- 配合 `startTransition` 可以避免"加载中"闪烁——切换时保留旧界面，新内容就绪后一次性替换。
- 嵌套 Suspense 形成分级的加载边界，配合 SSR 可实现流式输出。
- 数据请求库（TanStack Query、RSC）内置了 Suspense 支持。

### 7.7 StrictMode 的双调用

开发环境 StrictMode 会把**渲染函数**和**Effect**各跑两次，用来暴露副作用写在错误位置的问题。若你的代码在 StrictMode 下报错或行为异常（如请求发了两次、计数器加了 2），那说明副作用没写对——**不要靠去掉 StrictMode 来"解决"**。

## 八、事件与表单

### 8.1 合成事件

React 用**事件委托**：不在每个元素上绑监听，而是在根节点统一代理，事件对象经过一层包装（SyntheticEvent）。

```jsx
function Toolbar() {
  function handleClick(e) {
    e.preventDefault();   // 阻止默认行为
    e.stopPropagation();  // 阻止冒泡
    console.log(e.nativeEvent); // 原始 DOM 事件
  }
  return <button onClick={handleClick}>保存</button>;
}
```

| 常用事件 | 说明 |
|----------|------|
| `onClick` / `onDoubleClick` | 点击 |
| `onChange` | 注意：对 input 而言等价于原生 `input` 事件，每次输入都触发 |
| `onInput` | 与 `onChange` 在 React 中行为一致 |
| `onSubmit` | 表单提交（记得 `preventDefault`） |
| `onKeyDown` / `onKeyUp` / `onKeyPress` | 键盘 |
| `onFocus` / `onBlur` | 焦点（React 中也会冒泡） |
| `onMouseEnter` / `onMouseLeave` | 悬停（不冒泡） |
| `onScroll` | 滚动（不冒泡） |

**必须传函数引用**：`onClick={handleClick}` 正确，`onClick={handleClick()}` 会在渲染时立刻执行。要传参就包一层箭头函数 `onClick={() => handle(id)}`。

需要捕获阶段时用 `onClickCapture`。

### 8.2 受控组件 vs 非受控组件

```jsx
// 受控：value 来自 state，每次输入都更新 state（默认推荐）
function Controlled() {
  const [value, setValue] = useState('');
  return <input value={value} onChange={(e) => setValue(e.target.value)} />;
}

// 非受控：让 DOM 自己持有值，提交时再读（表单很大、或要减少重渲染时用）
function Uncontrolled() {
  const ref = useRef(null);
  return (
    <form
      action={(formData) => {
        console.log(formData.get('email')); // 直接读 FormData
      }}
    >
      <input name="email" ref={ref} defaultValue="" />
    </form>
  );
}
```

| 对比 | 受控 | 非受控 |
|------|------|--------|
| 值来源 | React state | DOM |
| 实时校验 | 容易 | 需额外监听 |
| 重渲染次数 | 每次输入 | 无 |
| 适用 | 需要联动、格式化、校验的表单 | 大表单、文件上传、集成第三方库 |

### 8.3 React 19 的表单动作

`<form action={fn}>` 里传入函数后，React 会自动处理 pending、错误、以及**提交成功后重置非受控表单**：

```jsx
function Subscribe() {
  const [state, subscribe] = useActionState(async (prev, formData) => {
    try {
      await api.subscribe(formData.get('email'));
      return { ok: true };
    } catch (e) {
      return { ok: false, message: e.message };
    }
  }, {});

  return (
    <form action={subscribe}>
      <input name="email" type="email" required />
      <button>订阅</button>
      {state.ok && <p>订阅成功</p>}
      {state.message && <p role="alert">{state.message}</p>}
    </form>
  );
}
```

需要手动重置时调用 `requestFormReset`（react-dom）。表单里也支持 `<button formAction={fn}>` 让不同按钮触发不同动作。

## 九、性能优化

### 9.1 先测量，再优化

性能问题的 90% 来自"渲染范围过大"，而不是"渲染次数太多"。定位手段：

1. **React DevTools Profiler**：录制交互，看每个组件的实际渲染耗时与重渲染原因（"Why did this render?"）。
2. **Performance Tracks**（19.x）：DevTools 的 Performance 面板里会显示 React 自己的调度轨道（组件渲染、Effect、Transition）。
3. **Highlight updates**：DevTools 里勾选后，重渲染的组件会闪烁高亮，一眼看出范围。

### 9.2 React Compiler（首选方案）

React Compiler v1.0（2025-10）在构建期自动插入记忆化，覆盖手写 Hook 做不到的场景（JSX 内联箭头函数、提前 return 之后定义的值）。开启后绝大多数 `useMemo`/`useCallback`/`memo` 可以直接删掉。

Vite 项目：

```bash
npm install -D --save-exact babel-plugin-react-compiler@latest eslint-plugin-react-hooks@latest
```

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react({
      babel: {
        // 必须排在其他 Babel 插件之前，编译器需要看到原始源码
        plugins: ['babel-plugin-react-compiler'],
      },
    }),
  ],
});
```

Next.js 项目：

```ts
// next.config.ts
const nextConfig = {
  experimental: { reactCompiler: true },
};
```

渐进式接入（老项目推荐）：

```ts
// babel.config.js
module.exports = {
  plugins: [
    [
      'babel-plugin-react-compiler',
      { compilationMode: 'annotation' }, // 只编译带 'use memo' 指令的文件
    ],
  ],
};
```

```jsx
// 只对加了指令的文件生效，逐个文件验证
'use memo';
export function OrderList({ orders }) { /* ... */ }
```

验证是否生效：

- React DevTools 组件名旁出现 **Memo ✨** 徽章。
- 构建产物中出现 `import { c as _c } from "react/compiler-runtime"`。

注意事项：

- 编译器**只优化遵守 React 规则**的组件；有违规（渲染期改 state、改 ref、随意 mutate props）时会跳过该文件并在 ESLint 报错——这是安全的，不是 bug。
- 测试覆盖不足时，把 `babel-plugin-react-compiler` 锁到**精确版本**（不要 `^`），避免小版本改变记忆化行为。
- 例外仍需手写 `useMemo`：当**引用相等是正确性要求**时（例如某个值要作为 Effect 依赖，或传给未编译的第三方库）。
- 单个组件想排除编译：在函数体第一行加 `'use no memo'`。

### 9.3 手写优化清单（未启用编译器时）

| 问题 | 手段 |
|------|------|
| 父组件重渲染导致整个子树跟着渲染 | 子组件 `memo` + props 引用稳定 |
| 传给 memo 子组件的回调/对象每次都新建 | `useCallback` / `useMemo` |
| 昂贵的列表计算 | `useMemo` |
| 一次更新引发连锁多次渲染 | 合并 state、用 `useReducer` |
| 长列表渲染卡顿 | 虚拟滚动（`@tanstack/react-virtual`、`react-window`） |
| 首屏包体积过大 | `lazy` + `Suspense` 路由级代码分割 |
| 输入卡顿 | `useTransition` / `useDeferredValue` |
| Context 变动打爆全局 | 拆分 Context、改用带选择器的 store |
| 图表/编辑器频繁重挂载 | 稳定 `key`、`<Activity>` 保活 |

路由级代码分割：

```jsx
import { lazy, Suspense } from 'react';

const OrderDetail = lazy(() => import('./features/order/OrderDetail'));

<Suspense fallback={<PageSkeleton />}>
  <OrderDetail />
</Suspense>;
```

### 9.4 常见"伪优化"

- 给每个函数都套 `useCallback`：比较依赖本身也有成本，往往得不偿失。
- 用 `useMemo` 缓存 JSX：不如直接把 JSX 抽成 `memo` 组件。
- 靠 `useRef` 存 state 逃避重渲染：界面不会更新，属于 bug 而非优化。
- 为了"少渲染一次"把逻辑写进 `useEffect`：只会多一轮渲染。

## 十、状态管理选型

### 10.1 先分类，再选型

2026 年的共识是：**先把状态分类，绝大多数"全局状态"其实不该进全局 store**。

| 类型 | 例子 | 推荐方案 |
|------|------|----------|
| 服务端状态 | 订单列表、用户详情 | Server Components（框架内）或 TanStack Query |
| URL 状态 | 筛选、分页、排序、搜索 | 路由的 search params（如 `nuqs`） |
| 表单状态 | 输入值、校验错误 | `useActionState` 或 React Hook Form |
| UI 状态 | 弹窗开关、侧边栏折叠、主题 | 就近 `useState`；跨层多则 Context 或 Zustand |

判断口诀：**能放在最近共同父组件就别全局，能放 URL 就别放内存，能由服务端直出就别客户端请求**。

### 10.2 方案对比

| 方案 | 体积 | 样板代码 | 擅长 | 适用 |
|------|------|----------|------|------|
| `useState` + 提升 | 0 | 无 | 局部状态 | 默认 |
| Context + useReducer | 0 | 中 | 低频全局数据（主题、权限、语言） | 中小项目 |
| Zustand | ~1KB | 极少 | 客户端 UI 状态、选择器精细订阅 | 大多数项目的全局 store |
| Jotai / Valtio | 小 | 少 | 原子化 / 响应式代理 | 细粒度更新 |
| Redux Toolkit | ~14KB | 多 | 严格结构、时间旅行调试、RTK Query | 大型长周期项目、已有 Redux 资产 |
| TanStack Query | 中 | 少 | 服务端数据缓存、失效、重试、分页 | **服务端状态首选** |
| XState | 中 | 多 | 复杂流程状态机 | 多步骤、易错流程 |

Zustand 示例：

```jsx
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useCartStore = create(
  persist(
    (set) => ({
      items: [],
      add: (item) => set((s) => ({ items: [...s.items, item] })),
      clear: () => set({ items: [] }),
    }),
    { name: 'cart' },
  ),
);

// 用选择器订阅，只在该字段变化时重渲染
function CartBadge() {
  const count = useCartStore((s) => s.items.length);
  return <span>{count}</span>;
}
```

> **SSR 提醒**：持久化状态（localStorage）不要在首次渲染读取，否则服务端与客户端输出不一致会触发 hydration mismatch。应在挂载后再读，或用 `skipHydration`。

## 十一、React 19 服务端能力

这部分依赖框架（Next.js App Router、React Router、TanStack Start）提供打包与运行时；纯 Vite SPA 用不到。

### 11.1 两种组件与两个指令

| 概念 | 标记 | 运行环境 | 能力 |
|------|------|----------|------|
| Server Component | 默认，无需指令 | 服务端（构建期或请求期） | 直连数据库/文件系统、async 组件、不打包进客户端 |
| Client Component | 文件顶部 `'use client'` | 服务端预渲染 + 浏览器水合 | `useState`/`useEffect`、事件、浏览器 API |
| Server Action | 函数体顶部 `'use server'` | 服务端 | 被客户端调用的函数，用于变更数据 |

**常见误解**：`'use server'` 不用于标记 Server Component，它只标记 Server Action。

```jsx
// app/orders/page.tsx —— Server Component：可以 async，直接查库
import { db } from '@/lib/db';
import RefundButton from './RefundButton'; // Client Component

export default async function OrdersPage() {
  const orders = await db.order.findMany({ take: 20 });
  return (
    <ul>
      {orders.map((o) => (
        <li key={o.id}>
          {o.title}
          <RefundButton orderId={o.id} action={refundOrder} />
        </li>
      ))}
    </ul>
  );
}
```

```jsx
// app/orders/actions.ts
'use server';

export async function refundOrder(orderId) {
  await db.order.update({ where: { id: orderId }, data: { status: 'refunded' } });
  revalidatePath('/orders');
}
```

```jsx
// app/orders/RefundButton.tsx
'use client';
import { useActionState } from 'react';

export default function RefundButton({ orderId, action }) {
  const [err, run, pending] = useActionState(async () => {
    try { await action(orderId); return null; } catch (e) { return e.message; }
  }, null);
  return <button onClick={run} disabled={pending}>{pending ? '处理中' : '退款'}</button>;
}
```

### 11.2 能力边界

| 能力 | Server Component | Client Component |
|------|------------------|------------------|
| `useState` / `useEffect` / 事件 | 不可用 | 可用 |
| `async` 组件 + `await` | 可用 | 不可用 |
| 访问数据库 / 读文件 / 密钥 | 可用 | 不可用 |
| 使用浏览器 API | 不可用 | 可用 |
| 代码进入客户端 bundle | 否（零 JS） | 是 |
| 渲染 Client Component | 可以（通过 children/import） | — |
| 被 Client Component 导入 | 只能通过 props/children 传入 | — |

**边界规则**：`'use client'` 是"进入客户端的入口"，从该模块 import 的所有模块都会成为客户端代码。因此**不要在 Client Component 里 import 服务端专用代码**；需要混合时，把 Server Component 作为 `children` 传进去。

### 11.3 流式渲染与 Suspense

Server Components 配合 Suspense 实现流式输出：先发静态骨架，数据就绪后再补送片段，无需等最慢的接口。

```jsx
export default function Page() {
  return (
    <>
      <Header />
      <Suspense fallback={<OrdersSkeleton />}>
        <Orders />   {/* 慢查询，单独流式送达 */}
      </Suspense>
      <Suspense fallback={<StatsSkeleton />}>
        <Stats />
      </Suspense>
    </>
  );
}
```

静态生成使用 `react-dom/static` 的 `prerender`（19 新增），它会等所有数据加载完再输出：

```js
import { prerender } from 'react-dom/static';

const { prelude } = await prerender(<App />, { bootstrapScripts: ['/main.js'] });
```

### 11.4 cacheSignal

19.2 新增，仅用于 Server Components。它返回一个 `AbortSignal`，在 `cache()` 作用域结束（渲染完成/取消/出错）时触发，用来取消已经不需要的后端请求：

```jsx
import { cache, cacheSignal } from 'react';

const dedupedFetch = cache(fetch);

async function Dashboard() {
  const data = await dedupedFetch(url, { signal: cacheSignal() });
  return <Chart data={await data.json()} />;
}
```

## 十二、错误边界与异常

渲染期抛出的错误会**让整棵组件树卸载**。生产环境表现为白屏，必须用错误边界兜住。

```jsx
import { Component } from 'react';

class ErrorBoundary extends Component {
  state = { error: null };

  // 子组件渲染出错时被调用，返回值用于更新 state
  static getDerivedStateFromError(error) {
    return { error };
  }

  // 上报日志
  componentDidCatch(error, info) {
    reportError(error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <section role="alert">
          <h2>页面出错了</h2>
          <pre>{this.state.error.message}</pre>
          <button onClick={() => this.setState({ error: null })}>重试</button>
        </section>
      );
    }
    return this.props.children;
  }
}

// 按区块包裹，避免一处出错整页崩
<ErrorBoundary><OrderList /></ErrorBoundary>
<ErrorBoundary><Stats /></ErrorBoundary>
```

错误边界**无法捕获**：

- 事件处理函数里的错误（用普通 `try/catch`）
- 异步代码（`setTimeout`、Promise 回调）里的错误
- 服务端渲染的错误
- 错误边界自身抛出的错误

因此 `async` 逻辑要自己 `try/catch`；用 Server Actions 时，抛出的错误会沿最近的边界上抛，可配合 `useActionState` 捕获后展示。

错误边界目前**只能用类组件写**（或直接用 `react-error-boundary` 库）。边界的粒度 = 故障的影响范围，建议按页面区块而非整站设置。

## 十三、TypeScript 实践

React 19 配套 `@types/react@19`。

### 13.1 组件与 Props

```tsx
// 用 type 定义 props，children 用 ReactNode
type ButtonProps = {
  variant?: 'primary' | 'ghost';
  onClick?: () => void;
  children: React.ReactNode;
};

function Button({ variant = 'primary', onClick, children }: ButtonProps) {
  return <button className={variant} onClick={onClick}>{children}</button>;
}

// 需要透传原生属性时，extend 原生类型
type InputProps = React.ComponentPropsWithoutRef<'input'> & { label: string };

function LabeledInput({ label, ...rest }: InputProps) {
  return <label>{label}<input {...rest} /></label>;
}
```

### 13.2 事件与 ref 类型

```tsx
function Form() {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
  };
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log(e.target.value);
  };
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <form onSubmit={handleSubmit}>
      <input ref={inputRef} onChange={handleChange} />
    </form>
  );
}
```

| 常用类型 | 用途 |
|----------|------|
| `React.ReactNode` | 任何可渲染内容（含字符串、null） |
| `React.ReactElement` | JSX 元素 |
| `React.ComponentPropsWithoutRef<'button'>` | 提取原生元素 props |
| `React.ComponentRef<'input'>` | 提取 ref 类型 |
| `React.PropsWithChildren<P>` | 给 props 补 children |
| `React.FC<Props>` | 一般**不推荐**（对 children 与泛型支持差） |

### 13.3 Hooks 的类型

```tsx
// useState 能从初始值推断，复杂情况显式标注
const [user, setUser] = useState<User | null>(null);

// useReducer：给 action 用可辨识联合，switch 里能收窄类型
type Action = { type: 'add'; item: Item } | { type: 'clear' };
function reducer(state: Item[], action: Action): Item[] { /* ... */ }

// 自定义 Hook 返回元组时，用 as const 固定为元组而非数组
function useToggle(initial = false) {
  const [on, setOn] = useState(initial);
  return [on, () => setOn((v) => !v)] as const;
}
```

### 13.4 泛型组件

```tsx
type ListProps<T> = {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  getKey: (item: T) => string;
};

function List<T>({ items, renderItem, getKey }: ListProps<T>) {
  return <ul>{items.map((i) => <li key={getKey(i)}>{renderItem(i)}</li>)}</ul>;
}

// 调用时自动推断
<List items={orders} getKey={(o) => o.id} renderItem={(o) => o.title} />
```

## 十四、测试

2026 年的主流组合：**Vitest（单元/组件）+ Testing Library（断言）+ Playwright（E2E）+ MSW（接口 mock）**。

```bash
npm install -D vitest @testing-library/react @testing-library/user-event jsdom @vitest/coverage-v8
```

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts', // 引入 @testing-library/jest-dom
  },
});
```

```tsx
// OrderCard.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import OrderCard from './OrderCard';

describe('OrderCard', () => {
  it('点击退款按钮时回调订单 id', async () => {
    const onRefund = vi.fn();
    render(<OrderCard order={{ id: 'A1', amount: 99, status: 'paid' }} onRefund={onRefund} />);

    await userEvent.click(screen.getByRole('button', { name: '申请退款' }));
    expect(onRefund).toHaveBeenCalledWith('A1');
  });
});
```

原则：

- **按用户能感知的方式查询**（角色、文本、label），不查 class 或内部实现。
- 测行为而非实现细节，避免断言 state 或组件内部方法。
- 涉及异步更新用 `await screen.findByText(...)` 或 `waitFor`。
- 表单、交互用 `userEvent`（比 `fireEvent` 更接近真实操作）。

## 十五、常见坑与排错

| 症状 | 原因 | 解决 |
|------|------|------|
| 界面不更新 | 直接 mutate 了对象/数组，引用没变 | 返回新对象/新数组 |
| 连点只加 1 | 用了 `setCount(count+1)` 闭包旧值 | 函数式更新 `setCount(p => p+1)` |
| 列表项内容错位 | `key` 用了数组下标 | 用业务 id |
| Effect 无限循环 | 依赖里放每次渲染都新建的对象/函数 | 用 `useMemo`/`useCallback` 稳定依赖，或去掉依赖 |
| 请求发了两次 | StrictMode 开发环境故意双调用 | 属正常；确保有清理逻辑（AbortController） |
| 请求结果串台 | 快速切换参数时旧请求后到 | AbortController 取消，或用请求库 |
| 闭包读到旧值 | 回调捕获了渲染时的变量 | 函数式更新、或把值放进 ref |
| Hydration mismatch | 服务端/客户端输出不一致 | 不用 `Date.now()`/`Math.random()`；浏览器 API 只在 Effect 里用；`<suppressHydrationWarning>` 仅作兜底 |
| Context 一改全网重渲染 | Provider value 每次新建 + 消费者过多 | 拆分 Context、`useMemo` 包裹 value、改用带选择器的 store |
| `use` 一直挂起 | 在渲染里直接 `use(fetch(url))`，每次新 Promise | Promise 提到父组件/缓存层创建 |
| `useEffectEvent` 报错 | 在 Effect 外调用或作为 props 传递 | 只能在 Effect 内调用；升级 eslint 插件 |
| 输入框卡顿 | 大数据量渲染阻塞 | `useTransition` / `useDeferredValue` / 虚拟滚动 |
| 组件状态莫名丢失 | 父组件条件渲染导致类型/位置变化 | 保持类型一致，或用 `key` 显式控制重置 |
| `Cannot update a component while rendering` | 渲染期调用了 setter | 把更新放进事件或 Effect |
| 第三方库报 React 版本冲突 | 依赖锁了旧版 peer | 用 `resolutions`/`overrides` 或升级库 |

### 15.1 闭包陷阱详解

```jsx
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      // 永远读到首次渲染的 count = 0，界面停在 1
      setCount(count + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []); // 依赖为空 → effect 只创建一次，闭包被冻结

  // 方案 A（推荐）：函数式更新，根本不依赖外部值
  // setCount(c => c + 1)

  // 方案 B：把 count 放进依赖，定时器会被反复重建（适合依赖真实变化的场景）
  // 方案 C：用 ref 保存最新值，effect 里读 ref.current
}
```

### 15.2 Effect 依赖该怎么写

```jsx
// 原则：effect 内部用到的每个响应式值都要进依赖，让 linter 帮你检查
// 处理方式优先级：
// 1. 值其实不该触发重跑 → useEffectEvent
// 2. 值是对象/函数且每次新建 → useMemo/useCallback 稳定它，或把它移到 effect 外
// 3. 只需要初始值 → 用 ref 保存，不进依赖
// 4. 实在不行才 eslint-disable，并写注释说明为什么
```

## 十六、生态与选型

| 领域 | 主流选择 | 备选 |
|------|----------|------|
| 元框架（全栈） | Next.js（App Router） | TanStack Start、React Router（框架模式） |
| 路由（SPA） | TanStack Router（类型安全） | React Router v8 |
| 服务端数据 | TanStack Query | SWR、RTK Query |
| 表单 | React Hook Form + Zod | `useActionState`（简单场景） |
| 样式 | Tailwind CSS | CSS Modules、vanilla-extract |
| UI 组件 | shadcn/ui + Radix | MUI、Ant Design（中后台）、Headless UI |
| 全局状态 | Zustand | Redux Toolkit、Jotai |
| 表格 | TanStack Table | AG Grid（企业级） |
| 虚拟滚动 | `@tanstack/react-virtual` | react-window |
| 动画 | Motion（原 Framer Motion） | React 19.3 `<ViewTransition>`（原生过渡） |
| 测试 | Vitest + Testing Library + Playwright + MSW | Jest（存量项目） |
| 组件文档 | Storybook | 应用内 `/playground` 路由（更轻） |

### 16.1 React 与 Vue 3 对比

| 维度 | React 19 | Vue 3 |
|------|----------|-------|
| 心智模型 | UI = f(state)，重渲染整棵子树 | 响应式依赖追踪，精确更新 |
| 模板 | JSX（JS 优先，表达力强） | 模板 + 指令（HTML 优先，上手快） |
| 更新粒度 | 组件级，需手动/编译器优化 | 组件内依赖级，默认更细 |
| 状态 | `useState` 等 Hook | `ref` / `reactive` |
| 副作用 | `useEffect`（依赖需手动声明） | `watch` / `watchEffect`（自动收集依赖） |
| 服务端能力 | RSC + Server Actions（需框架） | Nuxt（SSR/ISR） |
| 生态规模 | 最大（含 React Native） | 较大，国内中后台占比高 |
| 学习曲线 | 概念多（Hook 规则、并发、记忆化） | 相对平缓 |

选择建议：团队已有技术栈、需要 React Native、或做重交互复杂应用 → React；追求上手快、模板化、国内中后台 → Vue。两者在能力上已高度趋同，差异主要在**表达方式**与**生态**。参见 [[vue3|Vue 3]]。

### 16.2 与构建工具的关系

React 本身不含构建能力。Vite 负责开发服务器与打包（见 [[vite|Vite 构建工具]]），TypeScript/JSX 由构建链转换，React Compiler 作为 Babel 插件挂在构建链上。包管理见 [[npm|NPM]]。

## 十七、升级到 React 19

```bash
npm install react@19 react-dom@19
npm install -D @types/react@19 @types/react-dom@19
npx react-codemod@latest react-19   # 自动改造已废弃 API
```

主要破坏变更：

| 变更 | 影响 | 处理 |
|------|------|------|
| `ReactDOM.render` 移除 | 入口代码 | 改用 `createRoot` |
| `forwardRef` 不再必要 | 组件签名 | ref 作为普通 prop（codemod 可自动迁移） |
| `propTypes` / `defaultProps`（函数组件）移除 | 校验与默认值 | 用 TypeScript、用默认参数 |
| 字符串 ref、`React.createFactory` 移除 | 老 API | 改为回调 ref / JSX |
| `useFormState` 更名 | react-dom | 改用 `useActionState` |
| Context 用法 | `<C.Provider>` | 可改用 `<C value>` |
| `useId` 前缀变化 | 测试快照 | 更新快照（`«r»` → `r`） |
| 水合错误信息改进 | 无 | 报错更清晰，直接看 diff |

升级顺序建议：**先升级 React 本身 → 跑测试 → 再启用 React Compiler → 最后引入 RSC/Server Actions**。前三步互相独立，可分批上线。

## 十八、Checklist：写 React 组件的自我检查

- [ ] state 是否放在了能放的最低层级？有没有把可推导的值存进 state？
- [ ] 有没有为了"响应变化"而滥用 `useEffect`？
- [ ] 列表 `key` 用的是业务 id 吗？
- [ ] 更新对象/数组时返回的是新引用吗？
- [ ] 新值依赖旧值时用了函数式更新吗？
- [ ] Effect 的依赖是否完整且正确？有没有该用 `useEffectEvent` 的地方？
- [ ] 有异步操作时是否做了取消/清理？
- [ ] 组件拆分后，重渲染范围是否被控制在必要范围内？
- [ ] 有没有把服务端状态、URL 状态错当客户端全局状态？
- [ ] 关键区块是否包了错误边界与 Suspense？

## 参见

- [[javascript|JavaScript]]
- [[javascript-tutorial|JavaScript 教程]]
- [[es6|ES6]]
- [[vite|Vite 构建工具]]
- [[npm|NPM]]
- [[vue3|Vue 3]]
- [[html|HTML]]
- [[css|CSS]]
- [[json|JSON]]

## 外部资源

- [React 官方文档](https://react.dev/) —— 新版文档，含大量交互式示例
- [React 中文文档](https://zh-hans.react.dev/)
- [React 19 发布公告](https://react.dev/blog/2024/12/05/react-19)
- [React 19.2 发布公告](https://react.dev/blog/2025/10/01/react-19-2)
- [React 19.3 发布公告](https://react.dev/blog/2026/09/09/react-19-3)
- [React Compiler 文档](https://react.dev/learn/react-compiler)
- [React 19 升级指南](https://react.dev/blog/2024/12/05/react-19-upgrade-guide)
