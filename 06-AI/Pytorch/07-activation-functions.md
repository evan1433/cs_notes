# PyTorch 激活函数

激活函数为神经网络引入非线性，使其能够学习复杂的模式。

## 一、常用激活函数

### 1.1 ReLU（Rectified Linear Unit）

最常用的激活函数，计算高效。

```python
import torch
import torch.nn as nn

# nn.ReLU
relu = nn.ReLU()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = relu(x)  # tensor([0., 0., 0., 1., 2.])

# torch.relu
output = torch.relu(x)

# inplace 版本（节省内存）
relu = nn.ReLU(inplace=True)
```

**特点：**
- 输出范围：[0, +∞)
- 优点：计算快，缓解梯度消失
- 缺点：存在"死亡ReLU"问题（负数区域梯度为0）

### 1.2 LeakyReLU

解决 ReLU 的"死亡"问题。

```python
leaky_relu = nn.LeakyReLU(negative_slope=0.01)
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = leaky_relu(x)  # tensor([-0.02, -0.01, 0., 1., 2.])

# negative_slope 控制负数区域的斜率
# f(x) = x if x > 0, else negative_slope * x
```

**特点：**
- 输出范围：(-∞, +∞)
- 负数区域有小梯度，避免神经元死亡

### 1.3 PReLU（Parametric ReLU）

可学习的 LeakyReLU。

```python
prelu = nn.PReLU(num_parameters=1)  # 可学习的参数
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = prelu(x)

# num_parameters:
#   1: 所有通道共享一个参数
#   channels: 每个通道一个参数
```

### 1.4 ELU（Exponential Linear Unit）

```python
elu = nn.ELU(alpha=1.0)
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = elu(x)  # tensor([-0.86, -0.63, 0., 1., 2.])

# f(x) = x if x > 0, else alpha * (exp(x) - 1)
```

**特点：**
- 输出均值接近0，有助于学习
- 计算开销比 ReLU 大

### 1.5 GELU（Gaussian Error Linear Unit）

BERT、GPT 等现代架构常用。

```python
gelu = nn.GELU()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = gelu(x)
```

### 1.6 Sigmoid

将输出压缩到 (0, 1) 之间。

```python
sigmoid = nn.Sigmoid()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = sigmoid(x)  # tensor([0.12, 0.27, 0.50, 0.73, 0.88])

# f(x) = 1 / (1 + exp(-x))
```

**特点：**
- 输出范围：(0, 1)
- 缺点：容易梯度消失，输出不以0为中心

### 1.7 Tanh

将输出压缩到 (-1, 1) 之间。

```python
tanh = nn.Tanh()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = tanh(x)  # tensor([-0.96, -0.76, 0., 0.76, 0.96])

# f(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))
```

**特点：**
- 输出范围：(-1, 1)
- 输出以0为中心，比 Sigmoid 好
- 仍有梯度消失问题

### 1.8 Softmax

用于多分类输出层，转换为概率分布。

```python
softmax = nn.Softmax(dim=1)
x = torch.tensor([[1.0, 2.0, 3.0], [1.0, 1.0, 1.0]])
output = softmax(x)
# tensor([[0.09, 0.24, 0.67],
#         [0.33, 0.33, 0.33]])

# torch.softmax
output = torch.softmax(x, dim=1)
```

### 1.9 Softplus

ReLU 的平滑版本。

```python
softplus = nn.Softplus()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = softplus(x)

# f(x) = log(1 + exp(x))
```

### 1.10 Swish / SiLU

```python
silu = nn.SiLU()  # 或 nn.Hardswish()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = silu(x)

# f(x) = x * sigmoid(x)
```

### 1.11 Mish

现代激活函数，性能优于 ReLU。

```python
mish = nn.Mish()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
output = mish(x)

# f(x) = x * tanh(softplus(x))
```

## 二、激活函数选择指南

### 2.1 隐藏层

| 激活函数 | 适用场景 | 说明 |
|---------|---------|------|
| **ReLU** | 默认选择 | 计算快，表现好，从它开始 |
| **LeakyReLU** | ReLU效果不佳时 | 解决神经元死亡问题 |
| **GELU** | Transformer架构 | BERT、GPT等使用 |
| **Mish** | 追求性能 | 计算开销大，效果好 |

### 2.2 输出层

| 激活函数 | 适用场景 |
|---------|---------|
| **无激活** | 回归问题 |
| **Sigmoid** | 二分类问题 |
| **Softmax** | 多分类问题 |
| **Tanh** | 强化学习等需要[-1, 1]输出 |

### 2.3 经验法则

```python
# 隐藏层：ReLU 或 LeakyReLU
hidden_activation = nn.ReLU()

# 二分类输出
binary_output = nn.Sigmoid()

# 多分类输出（通常与 CrossEntropyLoss 配合，不显式使用）
# CrossEntropyLoss 已内置 softmax
multiclass_output = None  # 线性层直接输出 logits

# 回归输出
regression_output = None  # 不需要激活函数
```

## 三、激活函数可视化

```python
import matplotlib.pyplot as plt
import torch.nn.functional as F

x = torch.linspace(-5, 5, 100)

activations = {
    'ReLU': F.relu(x),
    'LeakyReLU': F.leaky_relu(x, 0.01),
    'Sigmoid': torch.sigmoid(x),
    'Tanh': torch.tanh(x),
    'ELU': F.elu(x),
    'GELU': F.gelu(x),
}

fig, axes = plt.subplots(2, 3, figsize=(12, 8))
for ax, (name, y) in zip(axes.flat, activations.items()):
    ax.plot(x.numpy(), y.numpy())
    ax.set_title(name)
    ax.grid(True)
plt.tight_layout()
plt.show()
```

## 四、实际问题与解决

### 4.1 梯度消失

```python
# 问题：Sigmoid/Tanh 在深层网络中梯度消失
x = torch.tensor([10.0], requires_grad=True)
y = torch.sigmoid(x)
y.backward()
print(x.grad)  # tensor([4.5398e-05])，梯度很小

# 解决：使用 ReLU/GELU
x = torch.tensor([10.0], requires_grad=True)
y = torch.relu(x)
y.backward()
print(x.grad)  # tensor([1.])
```

### 4.2 死亡 ReLU

```python
# 问题：ReLU 神经元可能永远不激活
# 如果权重初始化不当或学习率太大，所有输入都可能为负

# 解决方案
# 1. 使用 LeakyReLU
activation = nn.LeakyReLU(0.01)

# 2. 使用更好的初始化
nn.init.kaiming_normal_(layer.weight, mode='fan_in', nonlinearity='relu')

# 3. 使用较小的学习率
optimizer = optim.Adam(model.parameters(), lr=1e-4)
```

### 4.3 批归一化与激活顺序

```python
# 方式1：Linear -> BN -> ReLU（推荐）
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.BatchNorm1d(256),
    nn.ReLU(),
)

# 方式2：Linear -> ReLU -> BN（较少用）
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.BatchNorm1d(256),
)
```

## 五、高级用法

### 5.1 自定义激活函数

```python
class CustomActivation(nn.Module):
    def __init__(self, alpha=1.0):
        super(CustomActivation, self).__init__()
        self.alpha = alpha
    
    def forward(self, x):
        # 自定义激活函数
        return torch.where(x > 0, x, self.alpha * x)

# 使用
activation = CustomActivation(alpha=0.1)
output = activation(x)
```

### 5.2 函数式 API

```python
import torch.nn.functional as F

x = torch.randn(10, 20)

# 使用函数式 API（不创建模块）
output = F.relu(x)
output = F.leaky_relu(x, negative_slope=0.01)
output = F.elu(x, alpha=1.0)
output = F.gelu(x)
output = torch.sigmoid(x)
output = torch.tanh(x)
output = F.softmax(x, dim=1)
```

### 5.3 In-place 操作

```python
# inplace=True 节省内存，但可能破坏计算图
relu = nn.ReLU(inplace=True)

# 注意：inplace 操作不能用于需要反向传播的中间结果
# 错误示例
x = torch.randn(10, requires_grad=True)
y = F.relu_(x)  # inplace 版本，可能导致错误
```

## 六、激活函数对比表

| 激活函数 | 公式 | 输出范围 | 优点 | 缺点 |
|---------|------|---------|------|------|
| ReLU | max(0, x) | [0, +∞) | 计算快，缓解梯度消失 | 神经元死亡 |
| LeakyReLU | max(αx, x) | (-∞, +∞) | 避免神经元死亡 | 引入超参数 |
| Sigmoid | 1/(1+e^-x) | (0, 1) | 输出有界 | 梯度消失 |
| Tanh | (e^x-e^-x)/(e^x+e^-x) | (-1, 1) | 零中心化 | 梯度消失 |
| ELU | x或α(e^x-1) | (-α, +∞) | 平滑，零中心化 | 计算开销 |
| GELU | x·Φ(x) | ≈(-0.17, +∞) | 平滑，Transformer首选 | 计算开销 |
| Softmax | e^xi/Σe^xj | (0, 1)和为1 | 概率分布 | 多分类专用 |

## 参考资源

- [[06-linear]] - 全连接层
- [[10-mlp]] - 神经网络示例
- [PyTorch 激活函数文档](https://pytorch.org/docs/stable/nn.html#non-linear-activations-weighted-sum-nonlinearity)