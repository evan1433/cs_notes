---
title: Helm 使用指南
description: Kubernetes 包管理器 Helm 的核心概念、Chart 开发、模板语法、常用命令及最佳实践
tags:
  - helm
  - kubernetes
  - k8s
  - cloud-native
  - devops
date: 2026-08-20
---
# Helm 使用指南

> Helm 是 Kubernetes 的**包管理器**，类似于 Ubuntu 的 `apt`、Node.js 的 `npm`、Python 的 `pip`。它将一组 K8s 资源（Deployment、Service、ConfigMap 等）打包为一个 **Chart**，实现一键安装、升级、回滚和卸载。

## 目录

- [1. 为什么需要 Helm](#1-为什么需要-helm)
- [2. 核心概念](#2-核心概念)
- [3. 安装 Helm](#3-安装-helm)
- [4. Chart 目录结构](#4-chart-目录结构)
- [5. Chart.yaml 详解](#5-chartyaml-详解)
- [6. values.yaml — 配置值文件](#6-valuesyaml--配置值文件)
- [7. 模板语法](#7-模板语法)
- [8. 常用命令速查](#8-常用命令速查)
- [9. 仓库管理](#9-仓库管理)
- [10. 实战：从零创建一个 Chart](#10-实战从零创建一个-chart)
- [11. Release 管理：安装、升级、回滚](#11-release-管理安装升级回滚)
- [12. Hooks — 生命周期钩子](#12-hooks--生命周期钩子)
- [13. 子 Chart 与依赖管理](#13-子-chart-与依赖管理)
- [14. Library Chart — 可复用模板库](#14-library-chart--可复用模板库)
- [15. 最佳实践](#15-最佳实践)
- [16. 常见问题排查](#16-常见问题排查)

---

## 1. 为什么需要 Helm

### 纯 YAML 的痛点

在没有 Helm 之前，部署一个应用到 K8s 需要手动管理大量 YAML 文件：

```
my-app/
├── namespace.yaml
├── configmap.yaml
├── secret.yaml
├── deployment.yaml
├── service.yaml
├── ingress.yaml
├── hpa.yaml
└── pdb.yaml
```

问题显而易见：

| 痛点       | 说明                                    |
| -------- | ------------------------------------- |
| **环境差异** | dev / staging / prod 需要不同配置，维护多套 YAML |
| **版本管理** | 升级时手动改镜像 tag，回滚全凭记忆                   |
| **依赖管理** | 应用依赖 Redis、MySQL，需分别部署                |
| **复用困难** | 团队 A 的部署方案团队 B 无法直接复用                 |

### Helm 的解决思路

Helm 用**模板 + 变量**的方式，将"固定结构"和"可变配置"分离：

```
Chart (模板 + 默认值)  +  values.yaml (环境配置)  →  最终 YAML  →  K8s 集群
     ↑                       ↑                        ↑              ↑
   固定不变              按环境切换              Helm 渲染生成         部署运行
```

一句话总结：**Helm 让你用一套模板，通过不同配置值，部署到不同环境，并管理整个生命周期。**

---

## 2. 核心概念

| 概念 | 说明 | 类比 |
|------|------|------|
| **Chart** | 一组 K8s 资源的模板包 | npm 包 / apt 包 |
| **Repository** | 存放和分发 Chart 的仓库 | npm registry / Docker Hub |
| **Release** | Chart 安装到集群后的运行实例 | 已安装的软件实例 |

三者的关系：

```
开发者 ──创建──► Chart ──推送到──► Repository
                                    │
                              用户搜索 & 下载
                                    │
                              helm install
                                    │
                                    ▼
                              Release (运行实例)
                              ┌──────────────┐
                              │ my-app-v1     │
                              │ Deployment    │
                              │ Service       │
                              │ ConfigMap     │
                              └──────────────┘
```

> 同一个 Chart 可以安装多次，每次产生一个独立的 Release。比如用同一个 Redis Chart 在不同 namespace 安装 `redis-cache` 和 `redis-queue` 两个实例。

---

## 3. 安装 Helm

### 方式一：Homebrew（macOS）

```bash
brew install helm
```

### 方式二：官方脚本

```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 方式三：二进制下载

从 [Helm Releases](https://github.com/helm/helm/releases) 下载对应平台的二进制文件，解压后放到 `PATH` 中。

### 验证安装

```bash
helm version
# version.BuildInfo{Version:"v3.x.x", GitCommit:"...", GitTreeState:"clean", GoVersion:"go1.x"}
```

> **注意**：Helm 3 不再需要 Tiller（Helm 2 的服务端组件），所有操作都在客户端完成，通过 kubeconfig 直接与 K8s API 通信。因此使用前确保 `kubectl` 已正确配置。

---

## 4. Chart 目录结构

```
my-chart/
├── Chart.yaml              # Chart 元信息（名称、版本、描述）
├── values.yaml             # 默认配置值
├── values-prod.yaml        # 生产环境配置（自定义）
├── values-dev.yaml         # 开发环境配置（自定义）
├── charts/                 # 依赖的子 Chart（手动放置或 helm dep update 拉取）
│   └── redis-17.x.x.tgz
├── templates/              # K8s 资源模板
│   ├── _helpers.tpl        # 公共模板片段（命名模板）
│   ├── deployment.yaml     # Deployment 模板
│   ├── service.yaml        # Service 模板
│   ├── ingress.yaml        # Ingress 模板
│   ├── configmap.yaml      # ConfigMap 模板
│   ├── NOTES.txt           # 安装后提示信息（展示给用户）
│   └── tests/              # 测试模板
│       └── test-connection.yaml
├── templates/NOTES.txt     # 安装完成后的输出提示
├── .helmignore             # Helm 打包时忽略的文件
├── README.md               # Chart 说明文档
├── LICENSE                 # 许可证
└── crds/                   # 自定义资源定义（CRD）
```

### 各文件职责

| 文件/目录 | 是否必需 | 说明 |
|-----------|----------|------|
| `Chart.yaml` | ✅ | Chart 的元信息 |
| `values.yaml` | ✅ | 默认配置值 |
| `templates/` | ✅ | 模板文件目录 |
| `templates/_helpers.tpl` | 推荐 | 定义可复用的命名模板 |
| `templates/NOTES.txt` | 可选 | 安装后展示的使用提示 |
| `charts/` | 可选 | 子 Chart 依赖 |
| `.helmignore` | 可选 | 打包忽略列表 |
| `crds/` | 可选 | 自定义资源定义 |

---

## 5. Chart.yaml 详解

`Chart.yaml` 是 Chart 的元信息文件，定义了名称、版本等关键信息。

```yaml
apiVersion: v2                          # Chart API 版本（v2 用于 Helm 3）
name: my-app                            # Chart 名称（必需）
description: A Helm chart for my app    # 描述
type: application                        # Chart 类型：application（默认）或 library
version: 1.0.0                          # Chart 版本（必需，SemVer 格式）
appVersion: "2.5.0"                     # 应用版本（仅展示用，不参与 Chart 版本管理）
icon: https://example.com/icon.png      # 图标 URL
home: https://example.com               # 项目主页
keywords:                               # 关键词（便于搜索）
  - web
  - api
maintainers:                            # 维护者信息
  - name: duke
    email: duke@example.com
sources:                                # 源码仓库
  - https://github.com/example/my-app
dependencies:                           # 依赖的子 Chart
  - name: redis
    version: 17.x.x
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled            # 通过 values 控制是否启用
    alias: redis-cache                  # 别名（同一 Chart 多实例时使用）
```

### version 与 appVersion 的区别

| 字段 | 作用 | 变更时机 |
|------|------|---------|
| `version` | **Chart 本身的版本**，Helm 用它管理 Release 历史 | 模板或配置有变化时递增 |
| `appVersion` | **应用版本**，仅作信息展示，不影响 Helm 行为 | 应用版本升级时更新 |

```
Chart v1.0.0 → appVersion: "2.5.0"     # 首次发布
Chart v1.0.1 → appVersion: "2.5.0"     # 修了模板 bug，应用没变
Chart v1.1.0 → appVersion: "2.6.0"     # 应用升级到 2.6.0
```

---

## 6. values.yaml — 配置值文件

`values.yaml` 定义了模板中使用的默认变量。通过覆盖这些变量，可以实现不同环境的差异化部署。

### 基本结构

```yaml
# 镜像配置
image:
  repository: nginx
  tag: "1.24"
  pullPolicy: IfNotPresent

# 副本数
replicaCount: 3

# Service 配置
service:
  type: ClusterIP
  port: 80

# 资源限制
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

# Ingress 配置
ingress:
  enabled: true
  className: nginx
  host: app.example.com
  tls:
    enabled: true
    secretName: app-tls

# 依赖控制
redis:
  enabled: true          # 控制子 Chart 是否安装
```

### 值的优先级（从高到低）

```
helm install --set              ← 最高优先级
    │
    ▼
helm install -f custom.yaml     ← 自定义 values 文件
    │
    ▼
父 Chart values.yaml            ← Chart 默认值
    │
    ▼
子 Chart values.yaml            ← 最低优先级
```

```bash
# 用默认值安装
helm install my-app ./my-chart

# 覆盖单个值
helm install my-app ./my-chart --set replicaCount=5

# 使用自定义 values 文件
helm install my-app ./my-chart -f values-prod.yaml

# 多个 values 文件（后者覆盖前者）
helm install my-app ./my-chart -f values-base.yaml -f values-prod.yaml

# 组合使用（--set 优先级最高）
helm install my-app ./my-chart -f values-prod.yaml --set image.tag=2.0.0
```

### --set 语法详解

```bash
# 简单值
--set image.tag=2.0.0

# 嵌套值（对应 values.yaml 中的嵌套结构）
--set service.port=8080

# 数组（对应 values.yaml 中的列表）
--set env[0].name=DEBUG --set env[0].value=true

# 数组简写（逗号分隔）
--set env={DEBUG=true,LOG_LEVEL=info}

# 转义特殊字符（逗号本身用 \,）
--set "labels.team=dev\,ops"
```

---

## 7. 模板语法

Helm 使用 Go template 语法，并扩展了 Sprig 函数库。模板文件放在 `templates/` 目录下，扩展名为 `.yaml`。

### 基本变量引用

```yaml
# values.yaml
# image:
#   repository: nginx
#   tag: "1.24"

# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.image.repository }}    # 引用值：nginx
spec:
  template:
    spec:
      containers:
      - image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        # 结果：nginx:1.24
```

### 内置对象

| 对象 | 说明 | 示例 |
|------|------|------|
| `.Values` | values.yaml 中的值 | `{{ .Values.replicaCount }}` |
| `.Release` | 当前 Release 信息 | `{{ .Release.Name }}` |
| `.Chart` | Chart.yaml 中的元信息 | `{{ .Chart.Version }}` |
| `.Files` | Chart 中的文件 | `{{ .Files.Get "config.ini" }}` |
| `.Capabilities` | K8s 集群能力信息 | `{{ .Capabilities.KubeVersion }}` |
| `.Template` | 当前模板信息 | `{{ .Template.Name }}` |

### .Release 对象常用字段

```yaml
metadata:
  name: {{ .Release.Name }}              # Release 名称（如 my-app）
  namespace: {{ .Release.Namespace }}     # 命名空间
  labels:
    helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}    # 固定为 "Helm"
```

### 管道（Pipeline）

管道将前一个函数的输出作为后一个函数的输入，类似 Unix 管道：

```yaml
# 嵌套写法
name: {{ quote .Values.appName }}

# 管道写法（更易读）
name: {{ .Values.appName | quote }}

# 多级管道
chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
```

常用模板函数：

| 函数 | 说明 | 示例 |
|------|------|------|
| `quote` | 用双引号包裹 | `{{ "hello" \| quote }}` → `"hello"` |
| `default` | 设置默认值 | `{{ .Values.port \| default "80" }}` |
| `lower` / `upper` | 大小写转换 | `{{ "HELLO" \| lower }}` → `hello` |
| `replace` | 字符串替换 | `{{ "v1.0" \| replace "v" "" }}` → `1.0` |
| `trunc` | 截断字符串 | `{{ "abcdef" \| trunc 3 }}` → `abc` |
| `trimPrefix` | 去除前缀 | `{{ "v1.0" \| trimPrefix "v" }}` → `1.0` |
| `b64enc` / `b64dec` | Base64 编解码 | `{{ .Values.password \| b64enc }}` |
| `indent` | 缩进 N 个空格 | `{{ .Values.config \| indent 4 }}` |
| `nindent` | 换行+缩进 | `{{ .Values.labels \| nindent 4 }}` |
| `contains` | 包含检查 | `{{ if contains "prod" .Values.env }}` |
| `join` | 列表拼接 | `{{ join "," .Values.hosts }}` |

### 条件判断

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}-ingress
spec:
  rules:
  - host: {{ .Values.ingress.host }}
{{- end }}
```

```yaml
# if / else if / else
{{- if eq .Values.env "production" }}
  replicas: 5
{{- else if eq .Values.env "staging" }}
  replicas: 2
{{- else }}
  replicas: 1
{{- end }}
```

> **关于 `{{-` 和 `-}}`**：`-` 表示去除模板指令前后的空白字符（换行和空格）。不加的话，渲染后的 YAML 会多出空行，虽然不影响功能但不整洁。

### 循环（range）

```yaml
# values.yaml
# env:
#   - name: DEBUG
#     value: "true"
#   - name: LOG_LEVEL
#     value: "info"

# templates/deployment.yaml
env:
{{- range .Values.env }}
  - name: {{ .name }}
    value: {{ .value | quote }}
{{- end }}

# 渲染结果：
# env:
#   - name: DEBUG
#     value: "true"
#   - name: LOG_LEVEL
#     value: "info"
```

遍历键值对：

```yaml
{{- range $key, $val := .Values.labels }}
  {{ $key }}: {{ $val | quote }}
{{- end }}
```

### 命名模板（define / include / template）

在 `_helpers.tpl` 中定义可复用的模板片段：

```yaml
{{/*
公共标签
*/}}
{{- define "my-chart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end -}}
```

在其他模板中使用：

```yaml
# include 方式（推荐，支持管道）
metadata:
  labels:
    {{- include "my-chart.labels" . | nindent 4 }}

# template 方式（不支持管道）
metadata:
  labels:
    {{- template "my-chart.labels" . }}
```

> `include` 比 `template` 更灵活，因为它可以配合管道函数使用（如 `nindent`），推荐始终使用 `include`。

### with 作用域

`with` 可以改变 `.` 的指向，简化深层引用：

```yaml
{{- with .Values.image }}
image: "{{ .repository }}:{{ .tag }}"
pullPolicy: {{ .pullPolicy }}
{{- end }}

# 等价于
image: "{{ $.Values.image.repository }}:{{ $.Values.image.tag }}"
pullPolicy: {{ $.Values.image.pullPolicy }}
```

> `with` 内部无法直接访问外层作用域的 `.`，需要用 `$`（根上下文）来访问。例如 `{{ $.Release.Name }}`。

### required 函数

强制用户提供某个值，否则报错：

```yaml
image:
  repository: {{ .Values.image.repository | required "image.repository is required!" }}
```

### 注释

```yaml
{{/* 这是一个模板注释，不会出现在渲染结果中 */}}

{{- /*
多行模板注释
不会被渲染到最终 YAML 中
*/ -}}
```

---

## 8. 常用命令速查

### Chart 管理

```bash
# 创建新 Chart（生成标准目录结构）
helm create my-chart

# 验证 Chart 格式
helm lint my-chart

# 打包 Chart（生成 .tgz 文件）
helm package my-chart

# 打包时自动更新依赖
helm package my-chart --dependency-update

# 将 Chart 推送到 OCI 仓库
helm push my-chart-1.0.0.tgz oci://registry.example.com/charts
```

### Release 生命周期

```bash
# 安装 Chart
helm install [RELEASE_NAME] [CHART] [flags]
helm install my-app ./my-chart                        # 本地 Chart
helm install my-app bitnami/nginx                     # 仓库 Chart
helm install my-app ./my-chart -n my-namespace        # 指定 namespace

# 查看已安装的 Release
helm list                                             # 当前 namespace
helm list -A                                          # 所有 namespace
helm list -n my-namespace                             # 指定 namespace

# 升级（已安装则更新，未安装则新建）
helm upgrade my-app ./my-chart -f values-prod.yaml

# 升级并安装（如果不存在则自动安装，推荐）
helm upgrade --install my-app ./my-chart -f values-prod.yaml

# 查看 Release 历史
helm history my-app

# 回滚到指定版本
helm rollback my-app 2

# 卸载
helm uninstall my-app
helm uninstall my-app --keep-history                  # 保留历史（方便回滚）
```

### 查看 Release 信息

```bash
# 查看 Release 状态
helm status my-app

# 查看生成的所有 K8s 资源
helm get manifest my-app

# 查看 Release 的 values
helm get values my-app                                # 用户提供的值
helm get values my-app --all                          # 所有值（含默认值）

# 查看 Release 的 notes（NOTES.txt 渲染结果）
helm get notes my-app

# 查看 Release 的 hooks
helm get hooks my-app
```

### 模板渲染与调试

```bash
# 渲染模板（不安装，仅查看最终 YAML）
helm template my-app ./my-chart

# 渲染时覆盖值
helm template my-app ./my-chart -f values-prod.yaml --set replicaCount=5

# 只渲染指定模板文件
helm template my-app ./my-chart --show-only templates/deployment.yaml

# 调试模式（安装时显示渲染结果，不会真正部署）
helm install my-app ./my-chart --debug --dry-run
```

### 其他常用命令

```bash
# 查看依赖
helm dependency list my-chart
helm dependency update my-chart                # 按 Chart.yaml 中的 dependencies 拉取子 Chart

# 拉取远程 Chart 到本地
helm pull bitnami/nginx
helm pull bitnami/nginx --version 15.0.0       # 指定版本
helm pull bitnami/nginx --untar                 # 拉取并解压

# 搜索
helm search hub nginx                          # 搜索 Artifact Hub
helm search repo nginx                         # 搜索已添加的仓库
```

---

## 9. 仓库管理

### 添加和移除仓库

```bash
# 添加仓库
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add stable https://charts.helm.sh/stable
helm repo add incubator https://charts.helm.sh/incubator

# 查看已添加的仓库
helm repo list

# 更新仓库索引（获取最新 Chart 列表）
helm repo update

# 移除仓库
helm repo remove bitnami
```

### 搜索 Chart

```bash
# 在 Artifact Hub 上搜索
helm search hub nginx

# 在本地已添加的仓库中搜索
helm search repo nginx

# 查看所有版本
helm search repo nginx --versions

# 查看 Chart 的可配置项（values）
helm show values bitnami/nginx

# 查看 Chart 的 README
helm show readme bitnami/nginx

# 查看 Chart.yaml 内容
helm show chart bitnami/nginx

# 查看所有信息
helm show all bitnami/nginx
```

### OCI 仓库（Helm 3.8+）

Helm 3.8 开始原生支持 OCI（Open Container Initiative）仓库，与 Docker Registry 兼容：

```bash
# 登录 OCI 仓库
helm registry login registry.example.com

# 拉取 Chart
helm pull oci://registry.example.com/charts/nginx --version 15.0.0

# 推送 Chart（需先 package）
helm package my-chart
helm push my-chart-1.0.0.tgz oci://registry.example.com/charts

# 直接从 OCI 安装
helm install my-app oci://registry.example.com/charts/nginx --version 15.0.0
```

### 搭建私有 Chart 仓库

使用 [ChartMuseum](https://github.com/helm/chartmuseum) 快速搭建：

```bash
# 启动 ChartMuseum（Docker 方式）
docker run --rm -d \
  -p 8080:8080 \
  -v $(pwd)/charts:/charts \
  -e STORAGE=local \
  -e STORAGE_LOCAL_ROOTDIR=/charts \
  ghcr.io/helm/chartmuseum:v0.16.0

# 添加私有仓库
helm repo add myrepo http://localhost:8080

# 推送 Chart（需安装 helm-cm-push 插件）
helm cm-push my-chart-1.0.0.tgz myrepo
```

---

## 10. 实战：从零创建一个 Chart

### 创建并初始化

```bash
# 生成标准目录结构
helm create web-app
cd web-app

# 查看生成的结构
tree web-app
```

### 简化后的 Chart 结构

下面创建一个精简版的 Web 应用 Chart，展示核心用法：

```
web-app/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    └── NOTES.txt
```

### Chart.yaml

```yaml
apiVersion: v2
name: web-app
description: A simple web application Helm chart
type: application
version: 1.0.0
appVersion: "1.0.0"
```

### values.yaml

```yaml
replicaCount: 2

image:
  repository: nginx
  tag: "1.25"
  pullPolicy: IfNotPresent

nameOverride: ""
fullnameOverride: ""

service:
  type: ClusterIP
  port: 80

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 250m
    memory: 256Mi

# 应用配置
appConfig:
  logLevel: info
  features:
    - caching
    - metrics

# 可选 Ingress
ingress:
  enabled: false
  className: ""
  host: chart-example.local
```

### templates/_helpers.tpl

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "web-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "web-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "web-app.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{ include "web-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "web-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "web-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

### templates/configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "web-app.fullname" . }}
  labels:
    {{- include "web-app.labels" . | nindent 4 }}
data:
  LOG_LEVEL: {{ .Values.appConfig.logLevel | quote }}
  features.yaml: |
    {{- range .Values.appConfig.features }}
    - {{ . }}
    {{- end }}
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "web-app.fullname" . }}
  labels:
    {{- include "web-app.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "web-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "web-app.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - containerPort: {{ .Values.service.port }}
          name: http
        envFrom:
        - configMapRef:
            name: {{ include "web-app.fullname" . }}
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        livenessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
```

### templates/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "web-app.fullname" . }}
  labels:
    {{- include "web-app.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
  - port: {{ .Values.service.port }}
    targetPort: http
    protocol: TCP
    name: http
  selector:
    {{- include "web-app.selectorLabels" . | nindent 4 }}
```

### templates/NOTES.txt

```text
Thank you for installing {{ .Chart.Name }}!

Your application is being deployed as a Helm release named "{{ .Release.Name }}".

1. Get the application URL by running these commands:
{{- if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get --namespace {{ .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "web-app.fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "ClusterIP" .Values.service.type }}
  kubectl port-forward --namespace {{ .Release.Namespace }} service/{{ include "web-app.fullname" . }} 8080:{{ .Values.service.port }}
  echo "Visit http://127.0.0.1:8080"
{{- end }}
```

### 验证和部署

```bash
# 验证 Chart 格式
helm lint web-app

# 渲染预览（不安装）
helm template my-app web-app

# 模拟安装（dry-run）
helm install my-app web-app --dry-run --debug

# 正式安装
helm install my-app web-app -n default

# 安装到指定 namespace
helm install my-app web-app -n production -f values-prod.yaml

# 查看 Release
helm list

# 查看 Release 状态
helm status my-app
```

---

## 11. Release 管理：安装、升级、回滚

Helm 的 Release 管理是其核心价值之一。每次安装或升级都会产生一个**修订版本号**（revision），可以随时回滚。

### 生命周期流程

```
install ──► revision 1
    │
  upgrade ──► revision 2
    │
  upgrade ──► revision 3
    │
  rollback 2 ──► revision 4（内容同 revision 2）
    │
  uninstall ──► 清除所有历史（除非 --keep-history）
```

### 升级策略

```bash
# 直接升级
helm upgrade my-app ./web-app -f values-prod.yaml

# upgrade --install（推荐：不存在则安装，存在则升级）
helm upgrade --install my-app ./web-app -f values-prod.yaml

# 等待所有资源就绪
helm upgrade --install my-app ./web-app --wait --timeout 5m

# 原子部署（失败则自动回滚）
helm upgrade --install my-app ./web-app --atomic --timeout 5m

# 强制更新（删除并重建资源）
helm upgrade my-app ./web-app --force
```

### 回滚

```bash
# 查看历史
helm history my-app
# REVISION        STATUS          CHART           DESCRIPTION
# 1               superseded      web-app-1.0.0   Install complete
# 2               superseded      web-app-1.0.0   Upgrade complete
# 3               deployed        web-app-1.0.0   Upgrade complete

# 回滚到上一版本
helm rollback my-app 2

# 回滚后也会产生新的 revision 号
helm history my-app
# REVISION        STATUS          CHART           DESCRIPTION
# 1               superseded      web-app-1.0.0   Install complete
# 2               superseded      web-app-1.0.0   Upgrade complete
# 3               superseded      web-app-1.0.0   Rollback to 2
# 4               deployed        web-app-1.0.0   Rollback to 2
```

### 升级时保留自定义值

```bash
# 升级时自动继承上次的用户值（不指定 -f 或 --set）
helm upgrade my-app ./web-app --reuse-values

# 升级时重置为默认值，仅保留部分自定义
helm upgrade my-app ./web-app --reset-values --set replicaCount=5
```

### 安装/升级时自动创建 Namespace

```bash
helm install my-app ./web-app -n production --create-namespace
```

---

## 12. Hooks — 生命周期钩子

Helm Hooks 允许在 Release 生命周期的特定阶段执行操作，如安装前初始化、升级后清理等。

### Hook 类型

| Hook | 触发时机 | 典型用途 |
|------|---------|---------|
| `pre-install` | 渲染模板后、K8s 资源创建前 | 生成密钥、检查前置条件 |
| `post-install` | 所有资源创建后、Release 标记为 deployed 前 | 通知、注册服务 |
| `pre-delete` | 执行删除操作前 | 备份数据 |
| `post-delete` | 删除所有资源后 | 清理外部资源 |
| `pre-upgrade` | 升级渲染后、资源更新前 | 数据库备份 |
| `post-upgrade` | 升级完成后 | 烟雾测试 |
| `pre-rollback` | 回滚前 | 检查兼容性 |
| `post-rollback` | 回滚后 | 通知 |

### Hook 示例

```yaml
# templates/post-install-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "web-app.fullname" . }}-init
  labels:
    {{- include "web-app.labels" . | nindent 4 }}
  annotations:
    # 标记为 post-install hook
    "helm.sh/hook": post-install
    # hook 权重（数字越小越先执行）
    "helm.sh/hook-weight": "0"
    # hook 执行后删除策略：before-hook-creation / hook-succeeded / hook-failed
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    metadata:
      labels:
        {{- include "web-app.selectorLabels" . | nindent 8 }}
    spec:
      restartPolicy: Never
      containers:
      - name: init-job
        image: busybox:1.36
        command:
        - /bin/sh
        - -c
        - |
          echo "Running post-install hook for {{ .Release.Name }}"
          # 这里可以执行数据库迁移、初始化配置等操作
```

### Hook 的执行顺序

```
helm install
     │
     ├─ 渲染所有模板
     ├─ 执行 pre-install hooks（按 hook-weight 排序）
     ├─ 创建 Release 中的常规资源（Deployment、Service 等）
     ├─ 等待资源就绪（如果 --wait）
     ├─ 执行 post-install hooks
     └─ 标记 Release 为 deployed
```

> Hook 本质上是普通的 K8s 资源（通常是 Job），通过 `helm.sh/hook` 注解来标记它们为 hook，Helm 会按序执行并在完成后根据删除策略清理它们。

---

## 13. 子 Chart 与依赖管理

### 在 Chart.yaml 中声明依赖

```yaml
# Chart.yaml
apiVersion: v2
name: my-app
version: 1.0.0
dependencies:
  - name: redis
    version: "17.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled              # 通过 values 控制是否安装
    alias: redis-cache                     # 别名（同一 Chart 安装多实例）
    import-values:                        # 导入子 Chart 的值到父 Chart
      - child: master.service.ports.redis
        parent: redisServicePort
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
```

### 拉取依赖

```bash
# 根据 Chart.yaml 中的 dependencies 拉取子 Chart
helm dependency update my-app

# 查看依赖列表
helm dependency list my-app
```

执行后会在 `charts/` 目录下生成 `.tgz` 文件：

```
my-app/
├── Chart.yaml
├── values.yaml
└── charts/
    ├── redis-17.x.x.tgz
    └── postgresql-12.x.x.tgz
```

### 在 values.yaml 中配置子 Chart

```yaml
# values.yaml
# 父 Chart 自己的值
replicaCount: 3

# 子 Chart redis 的值（通过名称或别名引用）
redis:
  enabled: true
  auth:
    enabled: true
    password: "my-redis-password"
  architecture: standalone

# 使用别名安装第二个 redis 实例
redis-cache:
  enabled: true
  architecture: replication

# 子 Chart postgresql 的值
postgresql:
  enabled: true
  auth:
    postgresPassword: "pg-password"
    database: "mydb"
```

### 子 Chart 模板中访问父值

子 Chart **默认无法访问**父 Chart 的 `.Values`。如果需要：

```yaml
# 父 Chart 的 values.yaml 中定义全局值
global:
  imageRegistry: registry.example.com
  storageClass: fast-ssd

# 子 Chart 的模板中可以直接访问
{{ .Values.global.imageRegistry }}
```

> `global` 是特殊保留字，父 Chart 和所有子 Chart 都可以访问。

---

## 14. Library Chart — 可复用模板库

从 Helm 3 开始，支持 **Library Chart**（类型为 `library`），用于定义可被其他 Chart 通过 `include` / `template` 复用的模板片段，但不安装任何 K8s 资源。

### 创建 Library Chart

```yaml
# Chart.yaml
apiVersion: v2
name: my-common-library
description: Common template snippets for my charts
type: library                  # 关键：类型为 library
version: 1.0.0
```

### 定义公共模板

```yaml
# templates/_deployment.tpl
{{/*
Standard Deployment template
*/}}
{{- define "common.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    {{- include "common.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount | default 1 }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
      - name: {{ .Release.Name }}
        image: {{ .Values.image | default "nginx:latest" }}
{{- end }}
```

### 在应用 Chart 中引用

```yaml
# 应用 Chart 的 Chart.yaml
apiVersion: v2
name: my-app
version: 1.0.0
dependencies:
  - name: my-common-library
    version: "1.0.0"
    repository: "file://../my-common-library"

# 应用 Chart 的 templates/deployment.yaml
{{ include "common.deployment" . }}
```

---

## 15. 最佳实践

### Chart 设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 一个 Chart 只部署一个应用或一组紧密相关的服务 |
| **合理默认值** | 默认值应能直接在 minikube/kind 上跑起来 |
| **可配置性** | 通过 values 暴露关键配置，避免硬编码 |
| **向后兼容** | Chart 版本升级时尽量保持 values 向后兼容 |

### values 命名规范

```yaml
# ✅ 推荐：扁平且清晰的命名
image:
  repository: nginx
  tag: "1.24"

service:
  type: ClusterIP
  port: 80

# ❌ 避免：过度嵌套
app:
  deployment:
    container:
      image:
        repository: nginx
```

### 资源标签标准

遵循 [K8s 推荐标签](https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/)：

```yaml
labels:
  app.kubernetes.io/name: {{ include "my-chart.name" . }}
  app.kubernetes.io/instance: {{ .Release.Name }}
  app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
  app.kubernetes.io/managed-by: {{ .Release.Service }}
  app.kubernetes.io/component: web       # 组件角色：web / db / cache
  helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
```

### CI/CD 中的 Helm 工作流

```bash
# 1. 验证 Chart
helm lint my-chart

# 2. 渲染检查（可选）
helm template my-chart -f values-prod.yaml

# 3. 打包
helm package my-chart --version $CI_COMMIT_TAG

# 4. 推送到仓库
helm push my-chart-$CI_COMMIT_TAG.tgz oci://registry.example.com/charts

# 5. 部署到集群（原子部署 + 超时 + 等待就绪）
helm upgrade --install my-app \
  oci://registry.example.com/charts/my-chart \
  --version $CI_COMMIT_TAG \
  -f values-prod.yaml \
  --namespace production \
  --create-namespace \
  --atomic \
  --timeout 10m \
  --wait
```

### 安全最佳实践

```bash
# 1. 不要在 values.yaml 中存储敏感信息
# ✅ 使用外部 Secret 管理（External Secrets Operator / Sealed Secrets）
# ❌ password: "s3cr3t"  ← 不要这样做

# 2. 使用 --dry-run 检查渲染结果
helm install my-app ./my-chart --dry-run --debug

# 3. 查看已安装 Release 的值时注意敏感信息
helm get values my-app --all   # 会显示 secret 值

# 4. 使用 Chart 签名验证（provenance）
helm verify my-chart-1.0.0.tgz
```

### Chart 测试

```bash
# Chart 内置测试（在 templates/tests/ 下定义）
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ .Release.Name }}-test"
  annotations:
    "helm.sh/hook": test
spec:
  containers:
  - name: wget
    image: busybox:1.36
    command: ['wget']
    args: ['{{ .Release.Name }}:{{ .Values.service.port }}']
  restartPolicy: Never

# 运行测试
helm test my-app
```

---

## 16. 常见问题排查

### 模板渲染错误

```bash
# 使用 dry-run + debug 查看详细错误
helm install my-app ./my-chart --dry-run --debug

# 单独渲染模板定位问题
helm template my-app ./my-chart --debug

# 只渲染指定文件
helm template my-app ./my-chart --show-only templates/deployment.yaml
```

常见模板错误：

| 错误 | 原因 | 解决 |
|------|------|------|
| `nil pointer evaluating interface{}` | 引用了不存在的值 | 用 `default` 函数提供默认值 |
| YAML 渲染有空行/缩进错误 | 模板指令产生多余空白 | 使用 `{{-` 和 `-}}` 去除空白 |
| `map has no key` | values 中缺少字段 | 检查 values 结构或添加 `default` |

### Release 卡在 pending-install / pending-upgrade

当安装或升级过程中断，Release 可能卡在中间状态：

```bash
# 查看卡住的 Release
helm list -a                  # -a 显示所有状态

# 强制回滚
helm rollback my-app <previous-revision> --force

# 如果无法回滚，手动清理
kubectl delete secret -l owner=helm -l status=pending -l name=my-app -n <namespace>
```

### 子 Chart 值不生效

```bash
# 检查子 Chart 名称是否与 Chart.yaml 中 dependencies 一致
# 检查是否已执行 helm dependency update
helm dependency update my-app
```

### 查看 Helm 渲染的最终 YAML

```bash
# 对比本地修改与线上部署的差异
diff <(helm get manifest my-app) <(helm template my-app ./my-chart -f values-prod.yaml)
```

### 清理与卸载

```bash
# 卸载 Release（删除所有 K8s 资源）
helm uninstall my-app -n production

# 卸载但保留历史
helm uninstall my-app --keep-history

# 查看残留的 Helm Secrets（Release 历史存储在 Secret 中）
kubectl get secrets -n production -l owner=helm

# 清理指定 Release 的所有历史
kubectl delete secret -l owner=helm -l name=my-app -n production
```

---

## 学习资源

| 资源 | 链接 |
|------|------|
| Helm 官方文档 | https://helm.sh/docs/ |
| Helm 中文文档 | https://helm.sh/zh/docs/ |
| Chart 模板指南 | https://helm.sh/docs/chart_template_guide/ |
| Sprig 函数文档 | https://helm.sh/docs/chart_template_guide/function_list/ |
| Artifact Hub（Chart 搜索） | https://artifacthub.io/ |
| Bitnami Charts | https://github.com/bitnami/charts |
| Helm 官方仓库 | https://github.com/helm/helm |

---

> **学习建议**：先用 `helm create` 生成一个默认 Chart，读懂每一行模板。然后用 `helm template` 反复渲染调试，观察变量替换和管道函数的效果。最后尝试从 Artifact Hub 搜索并安装一个常用 Chart（如 Redis / Nginx），对比官方 Chart 的结构来学习最佳实践。Helm 的核心在于**模板引擎**，掌握 Go template + Sprig 函数，就能应对绝大多数场景。
