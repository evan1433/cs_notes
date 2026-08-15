---
title: Kubernetes (K8s) 学习指南
description: 基于 Kubernetes 官方文档整理的容器编排学习资料，涵盖架构、核心概念、控制器、网络、存储、安全等
tags:
  - kubernetes
  - k8s
  - container
  - cloud-native
  - devops
date: 2026-05-25
---
# Kubernetes (K8s) 学习指南

> 本资料基于 [Kubernetes 官方文档](https://kubernetes.io/docs/) 整理，以通俗易懂的方式讲解核心概念，配合大量 YAML 示例和实战场景。

## 目录

- [1. K8s 概述](#1-k8s-概述)
- [2. 核心架构与组件](#2-核心架构与组件)
- [3. Pod — 最小部署单元](#3-pod--最小部署单元)
- [4. 工作负载控制器](#4-工作负载控制器)
- [5. Service — 服务发现与负载均衡](#5-service--服务发现与负载均衡)
- [6. Ingress — 外部流量入口](#6-ingress--外部流量入口)
- [7. 配置管理：ConfigMap 与 Secret](#7-配置管理configmap-与-secret)
- [8. 存储：Volume、PV、PVC](#8-存储volumepvpvc)
- [9. 命名空间](#9-命名空间)
- [10. 安全机制：RBAC](#10-安全机制rbac)
- [11. Helm 包管理器](#11-helm-包管理器)
- [12. 集群搭建](#12-集群搭建)
- [13. 实战：部署一个完整应用](#13-实战部署一个完整应用)

---

## 1. K8s 概述

### 什么是 Kubernetes？

> Kubernetes 是一个**可移植、可扩展的开源平台**，用于管理容器化的工作负载和服务，既支持声明式配置又支持自动化。 — [Kubernetes 官方文档](https://kubernetes.io/docs/concepts/overview/)

**名称来源**：Kubernetes 源自希腊语，意为"舵手"或"领航员"。缩写 K8s 是因为字母 "K" 和 "s" 之间有 8 个字母。

Google 于 **2014 年**开源，融合了超过 15 年大规模生产环境运行经验。

### 为什么需要 K8s？

回想一下从传统部署到容器的演进：

```
传统部署  →  虚拟化部署  →  容器部署  →  容器编排(K8s)
─────────────────────────────────────────────────────
物理机       VM 隔离        共享 OS          自动化管理
资源浪费     利用率提升      轻量快速         弹性伸缩
手动运维     半自动          标准化           自我修复
```

容器解决了环境一致性问题，但当你有几十上百个容器时，谁来管它们的：
- 调度 — 哪个容器跑在哪个机器上？
- 扩缩 — 流量高了自动加，低了自动减？
- 健康 — 挂了自动重启？
- 网络 — 容器之间怎么通信？
- 存储 — 数据怎么持久化？
- 配置 — 不同环境的配置怎么管理？

这些就是 K8s 解决的问题。

### K8s 不是什么

K8s **不是**传统的 PaaS（平台即服务）：

| ❌ K8s 不做的 | ✅ 你需要的替代方案 |
|-------------|-----------------|
| 不构建源代码 | 用 CI/CD 工具（Jenkins、GitHub Actions） |
| 不提供应用级服务（数据库、缓存等） | 可部署在 K8s 上或使用云服务 |
| 不强制日志/监控方案 | Prometheus + Grafana、ELK Stack |
| 不限制应用类型 | 无状态、有状态、批处理都能跑 |

**K8s 在容器级别运行，提供的是一个编排框架，而不是一个全包式平台。**

---

'## 2. 核心架构与组件

K8s 集群分为两大块：**控制平面（Control Plane）** 和 **工作节点（Node）**。

```
┌──────────────────────────────────────────────────────┐
│                   Control Plane                      │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐         │
│  │API Server│ │ Scheduler │ │Controller Mgr│        │
│  └────┬─────┘ └─────┬─────┘ └──────┬─────┘         │
│       └──────────────┼─────────────┘                │
│                 ┌────┴────┐                          │
│                 │  etcd   │   ← 集群数据存储          │
│                 └─────────┘                          │
└──────────────────────┬───────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  Node 1  │ │  Node 2  │ │  Node 3  │
    │ kubelet  │ │ kubelet  │ │ kubelet  │
    │kube-proxy│ │kube-proxy│ │kube-proxy│
    │Container │ │Container │ │Container │
    │ Runtime  │ │ Runtime  │ │ Runtime  │
    └──────────┘ └──────────┘ └──────────┘
```

### 控制平面组件

| 组件                           | 作用               | 通俗理解                      |
| ---------------------------- | ---------------- | ------------------------- |
| **kube-apiserver**           | 集群统一入口，所有操作都通过它  | 集群的"前台"，接收你的 `kubectl` 命令 |
| **etcd**                     | 分布式键值存储，保存集群所有数据 | 集群的"数据库"，唯一真相来源           |
| **kube-scheduler**           | 为新 Pod 选择合适节点    | 集群的"调度员"，决定 Pod 放哪台机器     |
| **kube-controller-manager**  | 运行各种控制器，维持期望状态   | 集群的"管家"，不断检查实际状态是否符合期望    |
| **cloud-controller-manager** | 与云服务商交互（可选）      | 只有跑在云上才需要                 |

### Node 组件

| 组件 | 作用 | 通俗理解 |
|------|------|---------|
| **kubelet** | 确保 Pod 中的容器正常运行 | 每个节点的"保姆"，听 API Server 指挥 |
| **kube-proxy** | 维护节点网络规则，实现 Service 网络 | 节点上的"网络管理员" |
| **容器运行时** | 真正运行容器的软件 | containerd、CRI-O 等 |

> **注意**：K8s 1.24+ 版本移除了对 Docker 的直接集成，推荐使用 containerd。

---

## 3. Pod — 最小部署单元

### 什么是 Pod？

Pod 是 K8s 中可创建和管理的**最小可部署计算单元**。它是一组（一个或多个）容器的集合，这些容器共享存储和网络资源。

> 可以把 Pod 想象成一个"逻辑主机" — 就像一台虚拟机里跑了多个进程，Pod 里的多个容器共享同一个网络命名空间和存储卷。

### Pod 的本质特征

```
┌─────────────── Pod ───────────────┐
│ 共享网络命名空间（同一个 IP）       │
│  ┌──────────┐  ┌──────────┐      │
│  │ 容器 A   │  │ 容器 B   │      │
│  │ (nginx)  │  │(log-sidecar)│   │
│  └──────────┘  └──────────┘      │
│       │             │             │
│       └──────┬──────┘             │
│        共享存储卷 (Volume)          │
│     localhost 可达                 │
└───────────────────────────────────┘
```

关键特性：
- 同一 Pod 内容器共享**网络**（同一个 IP、端口空间、可通过 `localhost` 通信）
- 同一 Pod 内容器共享**存储**（挂载相同的 Volume）
- Pod 是**短暂**的，会随时被创建和销毁

### 两种使用模式

| 模式 | 描述 | 典型场景 |
|------|------|---------|
| **单容器 Pod** | 最常见，一个 Pod 一个容器 | Web 应用、微服务 |
| **多容器 Pod** | 紧密耦合的容器放一起 | 主应用 + 日志收集 sidecar |

### Pod YAML 详解

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.24
    ports:
    - containerPort: 80
    # 资源限制
    resources:
      requests:           # 调度时保证的最小资源
        memory: "64Mi"
        cpu: "250m"
      limits:             # 允许使用的最大资源
        memory: "128Mi"
        cpu: "500m"
    # 存活探针：检查容器是否还活着
    livenessProbe:
      httpGet:
        path: /healthz
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 10
    # 就绪探针：检查容器是否准备好接收流量
    readinessProbe:
      httpGet:
        path: /ready
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 5
  # 镜像拉取策略
  imagePullPolicy: IfNotPresent  # Always / Never / IfNotPresent
  # 重启策略
  restartPolicy: Always          # Always / OnFailure / Never
```

### 容器探针（Probes）

K8s 提供三种探针来检查容器状态：

| 探针类型 | 作用 | 失败后果 |
|----------|------|---------|
| **livenessProbe** | 检查容器是否**存活** | 容器被杀死并重启 |
| **readinessProbe** | 检查容器是否**就绪**接收流量 | 从 Service 端点移除，不接收请求 |
| **startupProbe** | 检查容器内应用是否**启动完成** | 在这之前，liveness 和 readiness 不会执行 |

探针的三种实现方式：

```yaml
# 方式一：执行命令
livenessProbe:
  exec:
    command:
    - cat
    - /tmp/healthy

# 方式二：HTTP GET 请求
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080

# 方式三：TCP Socket 检查
livenessProbe:
  tcpSocket:
    port: 8080
```

### Pod 的调度控制

#### 节点选择器

```yaml
spec:
  nodeSelector:
    disktype: ssd    # 只调度到有 disktype=ssd 标签的节点
```

#### 节点亲和性（Node Affinity）

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:   # 硬亲和性：必须满足
        nodeSelectorTerms:
        - matchExpressions:
          - key: env
            operator: In
            values: [production, staging]
      preferredDuringSchedulingIgnoredDuringExecution:  # 软亲和性：尽量满足
      - weight: 1
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values: [zone-a]
```

常用操作符：`In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`

#### 污点与容忍（Taint & Toleration）

节点污点让节点"排斥"某些 Pod，Pod 通过容忍来"接受"：

```bash
# 给节点添加污点
kubectl taint node node1 key=value:NoSchedule
```

污点效果：
- **NoSchedule**：不调度新 Pod，但不影响已有 Pod
- **PreferNoSchedule**：尽量不调度
- **NoExecute**：不调度新 Pod，并驱逐已有不匹配的 Pod

```yaml
# Pod 上配置容忍
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
```

---

## 4. 工作负载控制器

> **重要理念**：生产环境中不要直接创建 Pod。用控制器管理 Pod，让控制器负责 Pod 的生命周期、副本数量和更新策略。

### 控制器概览

| 控制器 | 用途 | 适合场景 |
|--------|------|---------|
| **Deployment** | 管理无状态应用 | Web 服务、API、微服务 |
| **StatefulSet** | 管理有状态应用 | 数据库、消息队列 |
| **DaemonSet** | 每个节点运行一个 Pod | 日志收集、监控 Agent |
| **Job** | 一次性任务 | 数据迁移、批处理 |
| **CronJob** | 定时任务 | 定时备份、定时报表 |

### 4.1 Deployment — 无状态应用

Deployment 是**最常用**的控制器，管理无状态应用的部署和更新。

#### 核心 YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3                    # 期望副本数
  selector:
    matchLabels:
      app: nginx                 # 选择器必须匹配 Pod 标签
  template:                      # Pod 模板
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.24
        ports:
        - containerPort: 80
```

#### Deployment 与 ReplicaSet 的关系

```
Deployment
    │
    ├── 创建并管理 ──► ReplicaSet (v1)
    │                      │
    │                      ├── Pod-1
    │                      ├── Pod-2
    │                      └── Pod-3
    │
    └── 更新时创建 ──► ReplicaSet (v2)  # 滚动更新
                           │
                           ├── Pod-4 (新)
                           ├── Pod-5 (新)
                           └── Pod-6 (新)
```

> **不要手动管理 ReplicaSet**，让 Deployment 自动管理。

#### 更新策略

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| **RollingUpdate**（默认） | 逐步替换旧 Pod，零停机 | 大多数场景 |
| **Recreate** | 先全部删除旧 Pod，再创建新 Pod | 不能同时运行新旧版本的场景 |

#### 常用操作

```bash
# 创建 Deployment
kubectl apply -f deployment.yaml

# 查看状态
kubectl get deployments
kubectl get rs
kubectl get pods --show-labels

# 更新镜像（触发滚动更新）
kubectl set image deployment/nginx-deployment nginx=nginx:1.25

# 查看更新历史
kubectl rollout history deployment/nginx-deployment

# 回滚
kubectl rollout undo deployment/nginx-deployment             # 回滚到上一版本
kubectl rollout undo deployment/nginx-deployment --to-revision=2  # 回滚到指定版本

# 扩缩容（不触发更新）
kubectl scale deployment/nginx-deployment --replicas=10

# 暂停/恢复更新
kubectl rollout pause deployment/nginx-deployment
kubectl rollout resume deployment/nginx-deployment
```

### 4.2 StatefulSet — 有状态应用

用于需要持久化存储和稳定网络标识的应用（如数据库）。

#### 与 Deployment 的区别

| 特性      | Deployment                 | StatefulSet                  |
| ------- | -------------------------- | ---------------------------- |
| Pod 命名  | 随机后缀（如 `nginx-7f8b9c-abc`） | 有序序号（如 `mysql-0`, `mysql-1`） |
| 启动/停止顺序 | 并行                         | 按序号顺序                        |
| 网络标识    | 随机 IP                      | 稳定的 DNS 名称                   |
| 存储      | 共享 PVC                     | 每个 Pod 独立 PVC                |

#### StatefulSet 示例

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  ports:
  - port: 80
    name: web
  clusterIP: None          # Headless Service
  selector:
    app: nginx
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: "nginx"     # 必须关联 Headless Service
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:    # 为每个 Pod 自动创建独立 PVC
  - metadata:
      name: www
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi
```

### 4.3 DaemonSet — 守护进程

确保每个节点上运行一个 Pod 副本，常用于日志收集、监控等。

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  labels:
    app: filebeat
spec:
  selector:
    matchLabels:
      app: filebeat
  template:
    metadata:
      labels:
        app: filebeat
    spec:
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:8.0.0
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

### 4.4 Job — 一次性任务

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 1            # 需要成功完成的次数
  parallelism: 1            # 并行运行的 Pod 数
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.34
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
  backoffLimit: 4           # 失败重试次数
```

### 4.5 CronJob — 定时任务

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"          # Cron 表达式：每分钟执行
  concurrencyPolicy: Forbid        # Allow / Forbid / Replace
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.28
            command:
            - /bin/sh
            - -c
            - date; echo Hello from Kubernetes
          restartPolicy: OnFailure
```

Cron 表达式格式：`分 时 日 月 周`

---

## 5. Service — 服务发现与负载均衡

### 为什么需要 Service？

Pod 是短暂的，IP 会变。Service 提供**稳定的访问入口**：

```
┌──────────┐         ┌─────────────────┐        ┌──────────┐
│ 前端 Pod  │ ────►  │    Service      │ ────► │ 后端 Pod  │
│          │        │  (稳定IP+DNS名)   │       │  (IP会变)  │
└──────────┘        └─────────────────┘       └──────────┘
```

> 你不需要修改应用代码来适应 K8s 的服务发现 — 这正是 Service 设计的核心目标。

### Service 的四种类型

| 类型 | 访问范围 | 典型场景 |
|------|----------|---------|
| **ClusterIP**（默认） | 集群内部 | 微服务间通信（如前端调后端 API） |
| **NodePort** | 外部（`NodeIP:30000-32767`） | 开发测试、简单的临时外部访问 |
| **LoadBalancer** | 外部（云负载均衡器） | 生产环境对外暴露服务 |
| **ExternalName** | 集群内部到外部 DNS 映射 | 连接集群外的服务（如外部数据库） |

### Service YAML 示例

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: MyApp   # 选择目标 Pod 的标签
  ports:
  - protocol: TCP
    port: 80            # Service 对外端口
    targetPort: 9376    # Pod 实际监听端口
    name: http
```

### Service 与 Pod 的关系

```
kubectl expose deployment nginx --port=80 --target-port=80 --type=NodePort
```

Service 通过 **label selector** 匹配 Pod：
- Service 定义 `selector: {app: nginx}`
- Pod 带有 `labels: {app: nginx}`
- 自动关联

### Headless Service（无头服务）

把 `clusterIP` 设为 `None`，不分配虚拟 IP，DNS 直接返回所有 Pod 的 IP：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-headless-service
spec:
  clusterIP: None          # 关键
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 9376
```

| | 普通 Service | Headless Service |
|---|---|---|
| ClusterIP | 有 | 无 |
| DNS 解析 | 返回单个 VIP | 返回所有 Pod IP |
| 负载均衡 | 自动 | 客户端自行选择 |

### 服务发现机制

1. **DNS**（推荐）：`<service-name>.<namespace>.svc.cluster.local`
2. **环境变量**：Pod 启动时注入 Service 信息
3. **API 查询**：直接查 K8s API

---

## 6. Ingress — 外部流量入口

### 什么是 Ingress？

Ingress 是管理**外部 HTTP/HTTPS 流量**进入集群的 API 对象。它提供了：

- 基于**域名**和**路径**的智能路由
- SSL/TLS 终止（HTTPS）
- 负载均衡

```
                    外部流量
                       │
                       ▼
                  Ingress（规则引擎）
                  /        \
                 /          \
    foo.com/api    bar.com/web
         │              │
    Service A       Service B
         │              │
    Pod Pod Pod    Pod Pod Pod
```

> **注意**：K8s 现在推荐用 **Gateway API** 替代 Ingress，但 Ingress 仍然是 GA 并广泛使用。

### Ingress 与 Ingress Controller

**仅创建 Ingress 资源没有任何效果**，必须部署 Ingress Controller（如 nginx-ingress、traefik）来实际执行规则。

### Ingress 配置示例

#### 基于路径的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: simple-fanout
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

#### 基于域名的虚拟主机

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: name-based-virtual-hosting
spec:
  ingressClassName: nginx
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
  - host: web.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

#### TLS 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-example
spec:
  tls:
  - hosts:
    - example.com
    secretName: example-tls     # TLS 证书存放在 Secret 中
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
```

### 路径类型

| 类型 | 匹配规则 | 示例 |
|------|---------|------|
| **Prefix** | 前缀匹配 | `/api` 匹配 `/api`、`/api/v1`、`/api/v1/users` |
| **Exact** | 精确匹配 | `/api/v1` 只匹配 `/api/v1` |
| **ImplementationSpecific** | 取决于 Controller 实现 | 灵活性最高 |

---

## 7. 配置管理：ConfigMap 与 Secret

> **核心思想**：将配置与镜像解耦。同一个镜像通过不同配置运行在不同环境。

### ConfigMap — 非敏感配置

存储应用的配置信息，如数据库地址、日志级别、特性开关等。

#### 创建 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: game-config
data:
  # 属性类键值
  player_initial_lives: "3"
  # 文件类键值（多行）
  game.properties: |
    enemy.types=aliens,monsters
    player.maximum-lives=5
    ui.allow.textmode=true
```

从文件创建：

```bash
kubectl create configmap game-config --from-file=game.properties
```

#### 在 Pod 中使用的四种方式

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: game-pod
spec:
  containers:
  - name: game
    image: game:latest
    # 方式1：环境变量
    env:
    - name: PLAYER_LIVES
      valueFrom:
        configMapKeyRef:
          name: game-config      # ConfigMap 名称
          key: player_initial_lives
    # 方式2：整个 ConfigMap 作为环境变量
    envFrom:
    - configMapRef:
        name: game-config
    # 方式3：Volume 挂载（以文件形式）
    volumeMounts:
    - name: config
      mountPath: /etc/game
  volumes:
  - name: config
    configMap:
      name: game-config
```

> **重要**：环境变量方式注入后在 Pod 生命周期内**不会自动更新**，Volume 挂载方式会**自动热更新**。

#### 使用限制

- ConfigMap 数据不超过 **1 MiB**
- 不提供加密，机密数据用 Secret
- Pod 和 ConfigMap 必须在**同一 namespace**

### Secret — 敏感配置

存储密码、Token、证书等敏感信息。

#### Secret 类型

| 类型 | 用途 |
|------|------|
| **Opaque** | 通用密钥（默认） |
| **kubernetes.io/tls** | TLS 证书和私钥 |
| **kubernetes.io/dockerconfigjson** | Docker 镜像仓库认证 |
| **kubernetes.io/basic-auth** | 基础认证凭据 |
| **kubernetes.io/ssh-auth** | SSH 认证凭据 |

#### 创建和使用 Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  username: YWRtaW4=        # base64 编码的 "admin"
  password: cGFzc3dvcmQ=    # base64 编码的 "password"
---
# 在 Pod 中使用
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    image: myapp:latest
    env:
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
    volumeMounts:            # 或作为文件挂载
    - name: secret-volume
      mountPath: /etc/secrets
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-secret
```

### ConfigMap vs Secret 对比

| 维度   | ConfigMap    | Secret            |
| ---- | ------------ | ----------------- |
| 数据性质 | 非机密          | 敏感/机密             |
| 存储加密 | ❌ 明文         | ✅ base64 + 可选静态加密 |
| 大小限制 | ≤ 1 MiB      | ≤ 1 MiB           |
| 典型数据 | 配置文件、环境变量    | 密码、Token、证书       |
| 热更新  | ✅ (Volume方式) | ✅ (Volume方式)      |

---

## 8. 存储：Volume、PV、PVC

### 核心概念

```
管理员                 集群                    用户(开发者)
───────               ──────                  ──────────
创建 PV (存储资源)     绑定过程                 创建 PVC (声明需求)
创建 StorageClass     动态供应                 挂载到 Pod
```

### Volume — Pod 级别的存储

Pod 内容器共享 Volume，Pod 删除时 Volume 通常也删除。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - image: nginx
    name: nginx
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}          # Pod 级别的临时存储
```

常见 Volume 类型：
- `emptyDir`：Pod 存在期间的临时存储
- `hostPath`：挂载宿主机目录
- `configMap` / `secret`：配置/密钥卷
- `persistentVolumeClaim`：持久化存储

### PV (PersistentVolume) 与 PVC (PersistentVolumeClaim)

> **设计理念**：将"存储的提供"与"存储的使用"解耦。管理员管理存储，开发者只需声明需求。

```
开发者视角：我要 5GB 存储，能读写
    │
    ▼ (PVC)
管理员视角：这里有 100GB SSD，RWO 模式
    │
    ▼ (PV)
绑定！Pod 挂载使用
```

#### PV — 集群存储资源

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv0001
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /data/pv0001
```

#### PVC — 存储声明

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myclaim
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 3Gi         # 请求 3GB
```

#### 在 Pod 中使用 PVC

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
  - name: myapp
    image: nginx
    volumeMounts:
    - mountPath: /data
      name: myvolume
  volumes:
  - name: myvolume
    persistentVolumeClaim:
      claimName: myclaim    # 引用 PVC
```

### 访问模式

| 模式 | 缩写 | 说明 |
|------|------|------|
| **ReadWriteOnce** | RWO | 单个节点读写 |
| **ReadOnlyMany** | ROX | 多节点只读 |
| **ReadWriteMany** | RWX | 多节点读写 |
| **ReadWriteOncePod** | RWOP | 单个 Pod 读写（最严格） |

### StorageClass — 动态供应

不想手动创建 PV？用 StorageClass 实现**按需自动创建**：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs    # 供应者（取决于环境）
parameters:
  type: gp3
reclaimPolicy: Delete
---
# PVC 中指定 StorageClass 即可自动创建 PV
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  storageClassName: fast-ssd       # 指定 StorageClass
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### PV 生命周期

| 阶段 | 说明 |
|------|------|
| **Provisioning** | 静态创建或动态供应 PV |
| **Binding** | PVC 绑定到匹配的 PV |
| **Using** | Pod 挂载使用，有保护机制防止误删 |
| **Reclaiming** | PVC 删除后，按回收策略处理 |

回收策略：

| 策略 | 行为 |
|------|------|
| **Retain** | 保留 PV 和数据，管理员手动处理 |
| **Delete** | 同时删除 PV 和外部存储（动态供应默认） |

---

## 9. 命名空间

### 概念

Namespace 用于将集群资源划分为**逻辑上的虚拟集群**，实现资源隔离和多租户。

```bash
kubectl get namespaces
# NAME              STATUS   AGE
# default           Active   10d
# kube-system       Active   10d    # K8s 系统组件
# kube-public       Active   10d
# production        Active   5d     # 生产环境
# development       Active   3d     # 开发环境
```

### 使用场景

```bash
# 在指定 namespace 中操作
kubectl get pods -n production
kubectl apply -f deployment.yaml -n production

# 切换默认 namespace
kubectl config set-context --current --namespace=production
```

### YAML 示例

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
```

---

## 10. 安全机制：RBAC

### RBAC 核心概念

K8s 中通过 **RBAC（基于角色的访问控制）** 管理权限：

```
用户/ServiceAccount ─► Role/ClusterRole ─► 资源操作权限
```

| 概念 | 范围 | 说明 |
|------|------|------|
| **Role** | 命名空间级别 | 定义对特定 namespace 中资源的权限 |
| **ClusterRole** | 集群级别 | 定义对所有 namespace 或集群级别资源的权限 |
| **RoleBinding** | 命名空间级别 | 将 Role 绑定到用户 |
| **ClusterRoleBinding** | 集群级别 | 将 ClusterRole 绑定到用户 |

### RBAC 示例

#### 创建 Role

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
```

#### 创建 RoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: development
subjects:
- kind: User
  name: alice
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## 11. Helm 包管理器

### 什么是 Helm？

Helm 是 K8s 的**包管理器**（类似 npm/pip/apt）。核心概念：

| 概念 | 说明 | 类比 |
|------|------|------|
| **Chart** | 打包好的 K8s YAML 模板集合 | npm 包 |
| **Repository** | Chart 仓库 | npm registry |
| **Release** | Chart 在集群中的运行实例 | 安装后的软件 |

### 基本用法

```bash
# 添加仓库
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 搜索 Chart
helm search repo nginx

# 安装
helm install my-nginx bitnami/nginx

# 查看已安装
helm list

# 升级
helm upgrade my-nginx bitnami/nginx --set replicaCount=3

# 回滚
helm rollback my-nginx 1

# 卸载
helm uninstall my-nginx

# 自定义 values 文件安装
helm install my-app ./my-chart -f values-prod.yaml
```

### Chart 目录结构

```
my-chart/
├── Chart.yaml          # Chart 元信息
├── values.yaml         # 默认配置值
├── templates/          # K8s YAML 模板
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
└── charts/             # 依赖的子 Chart
```

---

## 12. 集群搭建

### 方式一：kubeadm（推荐）

```bash
# Master 节点初始化
kubeadm init \
  --apiserver-advertise-address=<master-ip> \
  --image-repository registry.aliyuncs.com/google_containers \
  --pod-network-cidr=10.244.0.0/16

# 配置 kubectl
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config

# 安装网络插件（如 Flannel）
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml

# Worker 节点加入集群
kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>
```

### 方式二：轻量级方案

```bash
# Minikube — 本地单节点
minikube start

# Kind — 使用 Docker 容器模拟节点
kind create cluster

# k3s — 轻量级 K8s（适合边缘/IoT）
curl -sfL https://get.k3s.io | sh -
```

### 常用集群管理命令

```bash
# 查看节点
kubectl get nodes -o wide

# 查看所有资源
kubectl get all -A

# 查看集群信息
kubectl cluster-info

# 查看事件
kubectl get events --sort-by='.lastTimestamp'
```

---

## 13. 实战：部署一个完整应用

下面用一个典型的 **Web 应用 + 数据库** 场景，展示 K8s 各组件如何协同工作。

### 架构图

```
                    ┌────────────────┐
                    │   Ingress      │
                    │  example.com   │
                    └───────┬────────┘
                            │
                    ┌───────┴────────┐
                    │  Service:web    │
                    │  (ClusterIP)   │
                    └───────┬────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ Web Pod  │   │ Web Pod  │   │ Web Pod  │
     │ (nginx)  │   │ (nginx)  │   │ (nginx)  │
     └─────┬────┘   └─────┬────┘   └─────┬────┘
           │              │              │
           └──────────────┼──────────────┘
                          │
                  ┌───────┴────────┐
                  │  Service:db     │
                  │  (ClusterIP)   │
                  └───────┬────────┘
                          │
                  ┌───────┴────────┐
                  │  MySQL Pod     │
                  │  (StatefulSet) │
                  └───────┬────────┘
                          │
                  ┌───────┴────────┐
                  │  PV / PVC      │
                  │  (持久化存储)    │
                  └────────────────┘
```

### 步骤 1：创建 Namespace

```yaml
# 00-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo-app
```

### 步骤 2：部署 MySQL（StatefulSet + Secret + PVC）

```yaml
# 01-mysql-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: demo-app
type: Opaque
stringData:                        # 明文写入，自动 base64 编码
  root-password: "MySecretPass123"
  database-name: "demo_db"
---
# 02-mysql-statefulset.yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: demo-app
spec:
  ports:
  - port: 3306
  clusterIP: None                  # Headless Service
  selector:
    app: mysql
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: demo-app
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: root-password
        - name: MYSQL_DATABASE
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: database-name
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi
```

### 步骤 3：部署 Web 应用（Deployment + ConfigMap + Service）

```yaml
# 03-web-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-config
  namespace: demo-app
data:
  DB_HOST: "mysql.demo-app.svc.cluster.local"   # Service DNS 名称
  DB_PORT: "3306"
  APP_ENV: "production"
---
# 04-web-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: demo-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: nginx
        image: nginx:1.24
        ports:
        - containerPort: 80
        envFrom:
        - configMapRef:
            name: web-config          # 注入全部配置
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: root-password
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
      # Sidecar：简单的日志收集示例
      - name: log-shipper
        image: busybox:1.36
        command: ["/bin/sh", "-c", "while true; do echo logging...; sleep 60; done"]
---
# 05-web-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: demo-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
    name: http
  type: ClusterIP
```

### 步骤 4：配置 Ingress（外部访问）

```yaml
# 06-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: demo-app
spec:
  ingressClassName: nginx
  rules:
  - host: demo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-app
            port:
              number: 80
```

### 部署与验证

```bash
# 一键部署所有资源
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-mysql-secret.yaml
kubectl apply -f 02-mysql-statefulset.yaml
kubectl apply -f 03-web-config.yaml
kubectl apply -f 04-web-deployment.yaml
kubectl apply -f 05-web-service.yaml
kubectl apply -f 06-ingress.yaml

# 查看部署状态
kubectl get all -n demo-app

# 查看 Pod 日志
kubectl logs -n demo-app -l app=web-app

# 端口转发测试（本地访问）
kubectl port-forward -n demo-app service/web-app 8080:80

# 扩缩容测试
kubectl scale deployment web-app -n demo-app --replicas=5
```

---

## kubectl 常用命令速查

```bash
# ===== 基本操作 =====
kubectl get pods                           # 查看 Pod（当前 namespace）
kubectl get pods -A                        # 查看所有 namespace 的 Pod
kubectl get pods -o wide                   # 显示更多详情（IP、节点等）
kubectl get all                            # 查看所有资源

# ===== 查看详情 =====
kubectl describe pod <pod-name>            # Pod 详细信息（含事件）
kubectl logs <pod-name>                    # 查看日志
kubectl logs -f <pod-name>                 # 实时跟踪日志
kubectl logs <pod-name> -c <container>     # 多容器 Pod 查看特定容器日志
kubectl exec -it <pod-name> -- /bin/bash   # 进入容器

# ===== 创建/更新/删除 =====
kubectl apply -f file.yaml                 # 创建或更新资源
kubectl delete -f file.yaml               # 按文件删除
kubectl delete pod <pod-name>             # 删除 Pod
kubectl delete deployment <name>          # 删除 Deployment

# ===== 扩缩容 =====
kubectl scale deployment <name> --replicas=5

# ===== 更新 =====
kubectl set image deployment/<name> <container>=<new-image>
kubectl rollout status deployment/<name>   # 查看更新状态
kubectl rollout history deployment/<name>  # 查看更新历史
kubectl rollout undo deployment/<name>     # 回滚

# ===== 故障排查 =====
kubectl get events --sort-by='.lastTimestamp'
kubectl describe node <node-name>
kubectl top pods                           # 查看资源使用（需要 Metrics Server）
```

---

## 学习资源

| 资源 | 链接 |
|------|------|
| K8s 官方文档 | https://kubernetes.io/docs/ |
| K8s 中文文档 | https://kubernetes.io/zh-cn/docs/ |
| K8s 互动教程 | https://kubernetes.io/docs/tutorials/kubernetes-basics/ |
| Play with K8s（在线实践） | https://labs.play-with-k8s.com/ |
| CNCF Landscape | https://landscape.cncf.io/ |

---

> **学习建议**：先理解 Pod、Deployment、Service 这三个核心概念，动手部署一个简单应用。然后逐步深入网络（Ingress）、存储（PV/PVC）、配置（ConfigMap/Secret）、安全（RBAC）等进阶主题。K8s 概念虽多，但每个概念解决的都是一个具体问题，带着"它为什么要存在"去理解，会容易很多。
