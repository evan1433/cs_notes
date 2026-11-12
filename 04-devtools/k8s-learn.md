# harbor镜像仓库

# k8s学习笔记
虚拟机 ip 地址
192.168.56.102  master

192.168.56.103  node1

192.168.56.104  node2

```shell
wget https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo -O /etc/yum.repos.d/docker-ce.repo

yum -y install docker-ce-18.06.1.ce-3.el7


cat > /etc/docker/daemon.json << EOF
{
"registry-mirrors": ["https://b9pmyelo.mirror.aliyuncs.com"]
}
EOF

cat > /etc/yum.repos.d/kubernetes.repo << EOF
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=0
repo_gpgcheck=0
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg
https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg
EOF


kubeadm init \
--apiserver-advertise-address=192.168.56.102 \
--image-repository registry.aliyuncs.com/google_containers \
--kubernetes-version v1.17.0 \
--service-cidr=10.96.0.0/12 \
--pod-network-cidr=10.244.0.0/16
EOF
```

k8s  **Kubernetes1.24版本及以上移除了对docker的直接集成**，使用`containerd`实现。

[【Kubernetes1.26.x：container runtime is not running问题详细排查】_mikasa_akm的博客-CSDN博客](https://blog.csdn.net/weixin_52156647/article/details/129758753)
