# PyTorch 张量操作

张量（Tensor）是 PyTorch 中最核心的数据结构，类似于 NumPy 的 ndarray，但支持 GPU 加速和自动求导。

## 一、张量创建

### 1.1 从数据创建

```python
import torch

# 从列表创建
x = torch.tensor([1, 2, 3, 4])
# tensor([1, 2, 3, 4])

# 从嵌套列表创建（矩阵）
x = torch.tensor([[1, 2], [3, 4]])
# tensor([[1, 2],
#         [3, 4]])

# 指定数据类型
x = torch.tensor([1, 2, 3], dtype=torch.float32)
x = torch.tensor([1, 2, 3], dtype=torch.long)
```

### 1.2 创建特殊张量

```python
# 全零张量
x = torch.zeros(3, 4)
# tensor([[0., 0., 0., 0.],
#         [0., 0., 0., 0.],
#         [0., 0., 0., 0.]])

# 全一张量
x = torch.ones(2, 3)

# 单位矩阵
x = torch.eye(3)
# tensor([[1., 0., 0.],
#         [0., 1., 0.],
#         [0., 0., 1.]])

# 未初始化张量（内存中的随机值）
x = torch.empty(2, 3)

# 随机张量 [0, 1) 均匀分布
x = torch.rand(2, 3)

# 随机张量 标准正态分布 N(0, 1)
x = torch.randn(2, 3)

# 指定范围均匀分布
x = torch.arange(0, 10, step=2)
# tensor([0, 2, 4, 6, 8])

# 线性空间
x = torch.linspace(0, 1, steps=5)
# tensor([0.0000, 0.2500, 0.5000, 0.7500, 1.0000])

# 全填充
x = torch.full((2, 3), fill_value=7)
# tensor([[7, 7, 7],
#         [7, 7, 7]])
```

### 1.3 从 NumPy 创建

```python
import numpy as np

# NumPy 数组 → PyTorch 张量
np_array = np.array([1, 2, 3])
x = torch.from_numpy(np_array)

# PyTorch 张量 → NumPy 数组
x = torch.tensor([1, 2, 3])
np_array = x.numpy()
```

### 1.4 类似形状创建

```python
x = torch.tensor([[1, 2], [3, 4]])

# 创建与 x 形状相同的全零张量
y = torch.zeros_like(x)

# 创建与 x 形状相同的全一张量
y = torch.ones_like(x)

# 创建与 x 形状相同的随机张量
y = torch.rand_like(x, dtype=torch.float)
```

## 二、张量属性

```python
x = torch.randn(2, 3, 4)

# 形状
print(x.shape)        # torch.Size([2, 3, 4])
print(x.size())       # torch.Size([2, 3, 4])

# 维度数
print(x.dim())        # 3

# 元素总数
print(x.numel())      # 24 (2*3*4)

# 数据类型
print(x.dtype)        # torch.float32

# 设备（CPU/GPU）
print(x.device)       # cpu 或 cuda:0
```

## 三、张量索引与切片

### 3.1 基本索引

```python
x = torch.tensor([[1, 2, 3], [4, 5, 6]])

# 索引
print(x[0])      # tensor([1, 2, 3])
print(x[0, 1])   # tensor(2)
print(x[0][1])   # tensor(2)

# 切片
print(x[:, 0])       # tensor([1, 4])  第0列
print(x[0, :])      # tensor([1, 2, 3]) 第0行
print(x[0, 1:])     # tensor([2, 3])
```

### 3.2 高级索引

```python
x = torch.arange(12).reshape(3, 4)
# tensor([[ 0,  1,  2,  3],
#         [ 4,  5,  6,  7],
#         [ 8,  9, 10, 11]])

# 用列表索引
print(x[[0, 2], [1, 3]])  # tensor([1, 11])  取 (0,1) 和 (2,3)

# 布尔索引
mask = x > 5
print(x[mask])  # tensor([ 6,  7,  8,  9, 10, 11])

# 条件筛选
print(x[x % 2 == 0])  # tensor([ 0,  2,  4,  6,  8, 10])
```

### 3.3 使用 torch.where

```python
x = torch.tensor([1, 2, 3, 4, 5])

# 条件选择
y = torch.where(x > 3, x, torch.zeros_like(x))
# tensor([0, 0, 0, 4, 5])
```

## 四、维度操作

### 4.1 维度变换

```python
x = torch.arange(12)

# 改变形状
y = x.reshape(3, 4)
y = x.view(3, 4)        # view 要求内存连续

# 自动计算某个维度
y = x.reshape(3, -1)   # 自动计算列数
y = x.reshape(-1, 4)    # 自动计算行数

# 展平
y = x.flatten()         # 展平为1维
y = x.flatten(start_dim=1)  # 从第1维开始展平
```

### 4.2 增加维度

```python
x = torch.tensor([1, 2, 3])  # shape: [3]

# 在指定位置增加维度
y = x.unsqueeze(0)  # shape: [1, 3]
y = x.unsqueeze(1)  # shape: [3, 1]

# None 索引方式
y = x[None, :]      # shape: [1, 3]
y = x[:, None]      # shape: [3, 1]
```

### 4.3 减少维度

```python
x = torch.randn(1, 3, 1, 4)

# 删除所有大小为1的维度
y = x.squeeze()  # shape: [3, 4]

# 删除指定维度
y = x.squeeze(0)  # shape: [3, 1, 4]
y = x.squeeze(2)  # shape: [1, 3, 4]
```

### 4.4 维度转置与置换

```python
x = torch.randn(2, 3, 4)

# 交换两个维度
y = x.transpose(0, 1)  # shape: [3, 2, 4]

# 重新排列所有维度
y = x.permute(2, 0, 1)  # shape: [4, 2, 3]

# 矩阵转置（仅2D）
x = torch.randn(3, 4)
y = x.t()  # 或 x.T，shape: [4, 3]
```

## 五、张量运算

### 5.1 算术运算

```python
x = torch.tensor([1.0, 2.0, 3.0])
y = torch.tensor([4.0, 5.0, 6.0])

# 基本运算
print(x + y)   # 加法
print(x - y)   # 减法
print(x * y)   # 逐元素乘法
print(x / y)   # 逐元素除法
print(x ** 2)  # 幂运算

# 原地运算（带下划线后缀）
x.add_(y)      # x = x + y
x.mul_(2)      # x = x * 2

# 与标量运算
print(x + 10)
print(x * 2)
```

### 5.2 矩阵运算

```python
x = torch.randn(2, 3)
y = torch.randn(3, 4)

# 矩阵乘法
z = torch.matmul(x, y)  # 或 x @ y，shape: [2, 4]
z = torch.mm(x, y)      # 仅适用于2D矩阵

# 批量矩阵乘法
x = torch.randn(10, 2, 3)
y = torch.randn(10, 3, 4)
z = torch.bmm(x, y)     # shape: [10, 2, 4]

# 向量点积
x = torch.tensor([1.0, 2.0, 3.0])
y = torch.tensor([4.0, 5.0, 6.0])
print(torch.dot(x, y))  # tensor(32.)

# 外积
x = torch.tensor([1.0, 2.0])
y = torch.tensor([3.0, 4.0, 5.0])
print(torch.outer(x, y))  # shape: [2, 3]
```

### 5.3 聚合运算

```python
x = torch.randn(2, 3)

# 求和
print(x.sum())           # 所有元素求和
print(x.sum(dim=0))      # 按列求和，shape: [3]
print(x.sum(dim=1))      # 按行求和，shape: [2]
print(x.sum(dim=1, keepdim=True))  # 保持维度，shape: [2, 1]

# 均值
print(x.mean())
print(x.mean(dim=0))

# 最大/最小值
print(x.max())
print(x.max(dim=0))      # 返回 (values, indices)
print(x.min(dim=1))

# 标准差和方差
print(x.std())
print(x.var())

# 乘积
print(x.prod())

# 范数
print(x.norm())          # L2范数
print(x.norm(p=1))       # L1范数
print(x.norm(p='fro'))   # Frobenius范数
```

## 六、拼接与分割

### 6.1 拼接

```python
x = torch.tensor([[1, 2], [3, 4]])
y = torch.tensor([[5, 6], [7, 8]])

# 沿现有维度拼接
z = torch.cat([x, y], dim=0)  # shape: [4, 2]
z = torch.cat([x, y], dim=1)  # shape: [2, 4]

# 沿新维度拼接
z = torch.stack([x, y], dim=0)  # shape: [2, 2, 2]
z = torch.stack([x, y], dim=2)  # shape: [2, 2, 2]
```

### 6.2 分割

```python
x = torch.arange(10)

# 均匀分割
chunks = torch.chunk(x, chunks=3, dim=0)
# (tensor([0, 1, 2, 3]), tensor([4, 5, 6, 7]), tensor([8, 9]))

# 按大小分割
chunks = torch.split(x, split_size_or_sections=3, dim=0)
# (tensor([0, 1, 2]), tensor([3, 4, 5]), tensor([6, 7, 8]), tensor([9]))

# 不均匀分割
chunks = torch.split(x, [2, 3, 5], dim=0)
# (tensor([0, 1]), tensor([2, 3, 4]), tensor([5, 6, 7, 8, 9]))
```

## 七、广播机制

广播允许不同形状的张量进行运算。

```python
# 标量与张量
x = torch.tensor([1, 2, 3])
y = x + 10  # 10 广播为 [10, 10, 10]

# 不同形状张量
x = torch.randn(3, 4)
y = torch.randn(1, 4)
z = x + y  # y 广播为 [3, 4]

x = torch.randn(3, 1)
y = torch.randn(1, 4)
z = x + y  # x 广播为 [3, 4]，y 广播为 [3, 4]

# 广播规则
# 1. 从右向左比较维度
# 2. 维度相同或其中一个为1或不存在
# 3. 为1的维度会被扩展
```

## 八、GPU 与设备转移

```python
# 检查 GPU 是否可用
print(torch.cuda.is_available())

# 创建张量时指定设备
x = torch.tensor([1, 2, 3], device='cuda')
x = torch.tensor([1, 2, 3], device='cuda:0')
x = torch.tensor([1, 2, 3], device='cpu')

# 设备转移
x = torch.tensor([1, 2, 3])
x_gpu = x.to('cuda')
x_cpu = x_gpu.to('cpu')

# 或使用 cuda()/cpu()
x_gpu = x.cuda()
x_cpu = x_gpu.cpu()

# 获取设备信息
print(x.device)  # cuda:0 或 cpu
print(torch.cuda.current_device())
print(torch.cuda.get_device_name(0))
```

## 九、常见问题

### 9.1 view vs reshape

```python
x = torch.arange(12).reshape(3, 4)

# view 要求张量在内存中连续
y = x.transpose(0, 1)
# z = y.view(4, 3)  # 报错！transpose后内存不连续
z = y.reshape(4, 3)  # OK，reshape会自动处理

# 推荐使用 reshape，更安全
```

### 9.2 共享内存

```python
x = torch.tensor([1, 2, 3])

# 这些操作共享内存
y = x.view(3, 1)
y = x.reshape(3, 1)
y = x.squeeze()
y[0, 0] = 100
print(x)  # tensor([100, 2, 3])，x也被修改

# 如果需要独立副本
y = x.clone()
y[0] = 100
print(x)  # x 不受影响
```

### 9.3 requires_grad

```python
# 创建需要梯度的张量
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)

# 张量运算
y = x * 2
z = y.sum()

# 反向传播
z.backward()
print(x.grad)  # tensor([2., 2., 2.])

# 不需要梯度的场景
with torch.no_grad():
    y = x * 2

# 分离计算图
y = x.detach()
```

## 十、实用技巧

### 10.1 类型转换

```python
x = torch.tensor([1.5, 2.7, 3.9])

# 转换类型
y = x.long()      # 转为 long (int64)
y = x.int()        # 转为 int (int32)
y = x.float()      # 转为 float (float32)
y = x.double()     # 转为 double (float64)
y = x.to(torch.int32)  # 通用方法
```

### 10.2 张量比较

```python
x = torch.tensor([1, 2, 3])
y = torch.tensor([1, 2, 4])

# 逐元素比较
print(x == y)  # tensor([True, True, False])
print(x > y)   # tensor([False, False, False])

# 判断相等
print(torch.equal(x, y))  # False
print(torch.allclose(x, y, atol=1e-3))  # 近似相等判断

# 找出符合条件的索引
print(torch.nonzero(x > 1))  # tensor([[1], [2]])
```

### 10.3 统计操作

```python
x = torch.randn(3, 4)

# 查找极值索引
print(x.argmax())      # 全局最大值索引
print(x.argmax(dim=0)) # 每列最大值索引
print(x.argmax(dim=1)) # 每行最大值索引

# 排序
values, indices = torch.sort(x, dim=1, descending=True)

# top-k
values, indices = torch.topk(x, k=2, dim=1)
```

## 参考资源

- [[01-vectors]] - 多维张量概念理解
- [[03-autograd]] - 梯度计算
- [PyTorch 官方文档 - Tensor](https://pytorch.org/docs/stable/tensors.html)