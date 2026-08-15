---
source:
  - https://chatgpt.com/c/6a0fe07b-522c-83ea-ac8e-e193a8007228
tags:
  - k8s
---

当然可以，我帮你整理一份**面向初学者的简洁易懂的 `kubectl` 使用指南**，重点放在日常运维最常用的命令和场景。

---

# **Kubectl 快速使用指南（日常运维版）**

## **1. 基本概念**

- `kubectl`：Kubernetes 命令行工具，用于管理集群资源。
    
- 常见资源类型：
    
    - `pod`：Pod（最小部署单元）
    - `deployment`：部署
    - `service`：服务
    - `namespace`：命名空间
    - `configmap`、`secret`：配置和密钥
        

---

## **2. 查看信息**

### **集群信息**

```bash
kubectl cluster-info            # 查看集群信息
kubectl get nodes               # 查看节点状态
kubectl get namespaces          # 查看命名空间
```

### **资源列表**

```bash
kubectl get pods                # 查看当前命名空间的所有 Pod
kubectl get pods -n <namespace> # 查看指定命名空间的 Pod
kubectl get svc                 # 查看服务
kubectl get deployments         # 查看部署
kubectl get all                 # 查看所有资源（Pod/Service/Deployment等）
```

### **详细信息**

```bash
kubectl describe pod <pod_name>           # 查看 Pod 详细信息
kubectl describe deployment <deploy_name> # 查看部署详细信息
kubectl logs <pod_name>                   # 查看 Pod 日志
kubectl logs -f <pod_name>                # 实时跟踪日志
```

---

## **3. 创建/修改/删除资源**

### **创建资源**

```bash
kubectl apply -f <file.yaml>    # 根据 yaml 文件创建或更新资源
kubectl create deployment <name> --image=<image> # 直接创建部署
```

### **修改资源**

```bash
kubectl edit deployment <deploy_name>  # 编辑资源（会打开编辑器）
kubectl scale deployment <name> --replicas=3  # 修改副本数
```

### **删除资源**

```bash
kubectl delete pod <pod_name>
kubectl delete deployment <deploy_name>
kubectl delete -f <file.yaml>
```

---

## **4. Pod 操作**

```bash
kubectl exec -it <pod_name> -- /bin/bash   # 进入 Pod 容器（交互式）
kubectl port-forward <pod_name> 8080:80   # 本地访问 Pod 服务
kubectl get pods -o wide                   # 查看 Pod 的节点、IP 等详细信息
kubectl top pod                            # 查看 Pod 资源使用情况（需 metrics-server）
kubectl top node                           # 查看节点资源使用
```

---

## **5. Service / 访问相关**

```bash
kubectl get svc
kubectl describe svc <service_name>
kubectl port-forward svc/<service_name> 8080:80
```

---

## **6. Namespace 操作**

```bash
kubectl get ns                       # 查看命名空间
kubectl create ns <namespace_name>   # 创建命名空间
kubectl delete ns <namespace_name>   # 删除命名空间
kubectl get pods -n <namespace>      # 指定命名空间操作资源
```

---

## **7. 高级/实用技巧**

- **查看最近创建的 Pod**    

```bash
kubectl get pods --sort-by=.metadata.creationTimestamp
```

- **查看某类资源所有字段（JSON/YAML）**


```bash
kubectl get pod <pod_name> -o yaml
kubectl get pod <pod_name> -o json
```

- **批量删除资源**    

```bash
kubectl delete pod -l app=myapp   # 删除标签为 app=myapp 的 Pod
```

- **滚动更新**


```bash
kubectl set image deployment/<deploy_name> <container_name>=<new_image>
kubectl rollout status deployment/<deploy_name>   # 查看更新状态
kubectl rollout undo deployment/<deploy_name>    # 回滚更新
```

---

## **8. 小技巧**

- `kubectl get all -n <namespace>`：一次查看所有资源
- `kubectl describe pod <pod_name>`：最详细的状态和事件信息    
- `kubectl logs -f <pod_name>`：调试容器最常用命令    

---
