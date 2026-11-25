# PyTorch nn.Module 基础

`nn.Module` 是 PyTorch 中所有神经网络的基类，自定义模型都需要继承这个类。

## 一、基本结构

### 1.1 创建自定义模型

```python
import torch
import torch.nn as nn

class SimpleModel(nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        # 定义层
        self.fc1 = nn.Linear(10, 20)
        self.fc2 = nn.Linear(20, 10)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        # 定义前向传播
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

# 创建模型实例
model = SimpleModel()
print(model)
# SimpleModel(
#   (fc1): Linear(in_features=10, out_features=20, bias=True)
#   (fc2): Linear(in_features=10, out_features=10, bias=True)
#   (relu): ReLU()
# )
```

### 1.2 模型的两个核心方法

```python
class MyModel(nn.Module):
    def __init__(self):
        """
        初始化：定义模型的结构和参数
        在这里创建所有的层和参数
        """
        super(MyModel, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(784, 256),
            nn.ReLU(),
            nn.Linear(256, 10)
        )
    
    def forward(self, x):
        """
        前向传播：定义数据如何通过模型
        必须实现这个方法
        """
        return self.layers(x)

# 使用模型
model = MyModel()
x = torch.randn(32, 784)  # batch_size=32, features=784
output = model(x)         # 自动调用 forward 方法
# 等价于 model.forward(x)
```

## 二、模型参数

### 2.1 查看参数

```python
model = nn.Linear(10, 5)

# 查看所有参数
for name, param in model.named_parameters():
    print(f"{name}: shape={param.shape}, requires_grad={param.requires_grad}")
# weight: shape=torch.Size([5, 10]), requires_grad=True
# bias: shape=torch.Size([5]), requires_grad=True

# 仅查看参数值
for param in model.parameters():
    print(param.shape)

# 查看参数数量
total_params = sum(p.numel() for p in model.parameters())
print(f"Total parameters: {total_params}")

# 查看可训练参数数量
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Trainable parameters: {trainable_params}")
```

### 2.2 参数初始化

```python
import torch.nn.init as init

class MyModel(nn.Module):
    def __init__(self):
        super(MyModel, self).__init__()
        self.fc1 = nn.Linear(784, 256)
        self.fc2 = nn.Linear(256, 10)
        
        # 自定义初始化
        self._init_weights()
    
    def _init_weights(self):
        # Xavier/Glorot 初始化
        init.xavier_normal_(self.fc1.weight)
        init.zeros_(self.fc1.bias)
        
        # Kaiming/He 初始化（适合 ReLU）
        init.kaiming_normal_(self.fc2.weight, mode='fan_in', nonlinearity='relu')
        init.zeros_(self.fc2.bias)
    
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        return self.fc2(x)
```

### 2.3 常用初始化方法

```python
import torch.nn.init as init

# Xavier/Glorot 初始化（适合 tanh/sigmoid）
init.xavier_uniform_(tensor, gain=1.0)
init.xavier_normal_(tensor, gain=1.0)

# Kaiming/He 初始化（适合 ReLU/LeakyReLU）
init.kaiming_uniform_(tensor, a=0, mode='fan_in', nonlinearity='leaky_relu')
init.kaiming_normal_(tensor, a=0, mode='fan_in', nonlinearity='leaky_relu')

# 常数初始化
init.constant_(tensor, value=0)
init.ones_(tensor)
init.zeros_(tensor)

# 正态分布初始化
init.normal_(tensor, mean=0.0, std=1.0)

# 均匀分布初始化
init.uniform_(tensor, a=0.0, b=1.0)

# 正交初始化
init.orthogonal_(tensor, gain=1.0)

# 稀疏初始化
init.sparse_(tensor, sparsity=0.1, std=0.01)
```

### 2.4 冻结参数

```python
# 冻结所有参数
for param in model.parameters():
    param.requires_grad = False

# 冻结特定层
for param in model.layer1.parameters():
    param.requires_grad = False

# 解冻所有参数
for param in model.parameters():
    param.requires_grad = True

# 查看哪些层是冻结的
for name, param in model.named_parameters():
    print(f"{name}: requires_grad={param.requires_grad}")
```

## 三、子模块管理

### 3.1 添加子模块

```python
class MyModel(nn.Module):
    def __init__(self):
        super(MyModel, self).__init__()
        
        # 方式1：直接赋值（推荐）
        self.fc1 = nn.Linear(10, 20)
        
        # 方式2：使用 add_module
        self.add_module('fc2', nn.Linear(20, 10))
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.fc2(x)
        return x
```

### 3.2 访问子模块

```python
model = nn.Sequential(
    nn.Linear(10, 20),
    nn.ReLU(),
    nn.Linear(20, 10)
)

# 通过名称访问
print(model[0])       # Linear(10, 20)
print(model._modules)  # 字典形式的所有模块

# 遍历所有子模块
for name, module in model.named_modules():
    print(f"{name}: {module}")

# 遍历直接子模块
for module in model.children():
    print(module)

# 获取所有子模块列表
modules = list(model.modules())
children = list(model.children())
```

### 3.3 ModuleList 和 ModuleDict

```python
# ModuleList：类似于列表的模块容器
class MyModel(nn.Module):
    def __init__(self, layer_sizes):
        super(MyModel, self).__init__()
        self.layers = nn.ModuleList([
            nn.Linear(layer_sizes[i], layer_sizes[i+1])
            for i in range(len(layer_sizes)-1)
        ])
    
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

# ModuleDict：类似于字典的模块容器
class MyModel(nn.Module):
    def __init__(self):
        super(MyModel, self).__init__()
        self.layers = nn.ModuleDict({
            'encoder': nn.Linear(10, 20),
            'decoder': nn.Linear(20, 10),
        })
    
    def forward(self, x):
        x = self.layers['encoder'](x)
        x = self.layers['decoder'](x)
        return x

# 注意：普通列表/字典中的模块不会被注册
# 错误示范
class BadModel(nn.Module):
    def __init__(self):
        super(BadModel, self).__init__()
        self.layers = [nn.Linear(10, 20)]  # 不会被注册！
```

## 四、Sequential 容器

### 4.1 基本使用

```python
# 方式1：按顺序传入
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
)

# 方式2：使用 OrderedDict
from collections import OrderedDict
model = nn.Sequential(OrderedDict([
    ('fc1', nn.Linear(784, 256)),
    ('relu1', nn.ReLU()),
    ('fc2', nn.Linear(256, 128)),
    ('relu2', nn.ReLU()),
    ('fc3', nn.Linear(128, 10))
]))

# 访问层
print(model[0])         # 第一个层
print(model.fc1)       # 通过名称访问（需要使用 OrderedDict）
print(model._modules)  # 所有模块
```

### 4.2 Sequential vs 自定义 Module

```python
# Sequential：简单、快速，适合顺序结构
model = nn.Sequential(
    nn.Linear(10, 20),
    nn.ReLU(),
    nn.Linear(20, 10)
)

# 自定义 Module：灵活，适合复杂结构
class MyModel(nn.Module):
    def __init__(self):
        super(MyModel, self).__init__()
        self.fc1 = nn.Linear(10, 20)
        self.fc2 = nn.Linear(20, 10)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        # 可以实现复杂的控制流
        x = self.fc1(x)
        if x.sum() > 0:  # 条件分支
            x = self.relu(x)
        else:
            x = x * 2
        x = self.fc2(x)
        return x
```

## 五、模型训练与评估模式

### 5.1 train() 和 eval()

```python
model = nn.Sequential(
    nn.Linear(10, 20),
    nn.BatchNorm1d(20),  # BatchNorm 行为在训练和评估时不同
    nn.ReLU(),
    nn.Dropout(0.5),     # Dropout 在训练和评估时行为不同
    nn.Linear(20, 10)
)

# 训练模式
model.train()
# Dropout 生效
# BatchNorm 使用当前 batch 统计量

# 评估模式
model.eval()
# Dropout 关闭
# BatchNorm 使用全局统计量

# 训练循环
for epoch in range(epochs):
    model.train()  # 训练模式
    for data, target in train_loader:
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
    
    model.eval()  # 评估模式
    with torch.no_grad():
        for data, target in val_loader:
            output = model(data)
            # 验证代码
```

### 5.2 受影响的层

```python
# Dropout
dropout = nn.Dropout(0.5)
model.train()
output1 = dropout(torch.ones(10))  # 部分元素置0

model.eval()
output2 = dropout(torch.ones(10))  # 所有元素不变

# BatchNorm
bn = nn.BatchNorm1d(10)
model.train()
# 使用当前 batch 的均值和方差

model.eval()
# 使用全局的 running_mean 和 running_var
```

## 六、设备管理

### 6.1 模型移动到 GPU

```python
# 检查 GPU 是否可用
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 移动模型
model = MyModel()
model = model.to(device)

# 移动数据
x = torch.randn(32, 10)
x = x.to(device)

# 前向传播
output = model(x)
```

### 6.2 多 GPU 训练

```python
# DataParallel（单机多卡）
model = MyModel()
if torch.cuda.device_count() > 1:
    model = nn.DataParallel(model)
model = model.to('cuda')

# DistributedDataParallel（推荐，更高效）
# 需要配合 torch.distributed 使用
model = MyModel()
model = nn.parallel.DistributedDataParallel(model, device_ids=[local_rank])
```

## 七、模型保存与加载

### 7.1 保存整个模型

```python
# 保存
torch.save(model, 'model.pth')

# 加载
model = torch.load('model.pth')
model.eval()
```

### 7.2 只保存参数（推荐）

```python
# 保存
torch.save(model.state_dict(), 'model_params.pth')

# 加载
model = MyModel()
model.load_state_dict(torch.load('model_params.pth'))
model.eval()
```

### 7.3 保存检查点

```python
# 保存检查点
checkpoint = {
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'loss': loss,
}
torch.save(checkpoint, 'checkpoint.pth')

# 加载检查点
model = MyModel()
optimizer = optim.Adam(model.parameters())
checkpoint = torch.load('checkpoint.pth')
model.load_state_dict(checkpoint['model_state_dict'])
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
epoch = checkpoint['epoch']
loss = checkpoint['loss']
```

### 7.4 跨设备加载

```python
# GPU → CPU
model.load_state_dict(torch.load('model.pth', map_location='cpu'))

# GPU 0 → GPU 1
model.load_state_dict(torch.load('model.pth', map_location={'cuda:0': 'cuda:1'}))
```

## 八、钩子（Hooks）

### 8.1 前向钩子

```python
model = nn.Sequential(
    nn.Linear(10, 20),
    nn.ReLU(),
    nn.Linear(20, 10)
)

def forward_hook(module, input, output):
    print(f"{module.__class__.__name__}: output shape = {output.shape}")

# 注册钩子
handle = model[0].register_forward_hook(forward_hook)

# 前向传播时会触发钩子
x = torch.randn(5, 10)
output = model(x)  # 会打印输出形状

# 移除钩子
handle.remove()
```

### 8.2 反向钩子

```python
def backward_hook(module, grad_input, grad_output):
    print(f"{module.__class__.__name__}: grad_output shape = {grad_output[0].shape}")

# 注册反向钩子
handle = model[0].register_backward_hook(backward_hook)

# 反向传播时会触发钩子
output = model(x)
loss = output.sum()
loss.backward()  # 会打印梯度形状

# 移除钩子
handle.remove()
```

## 九、自定义层

### 9.1 自定义无参数层

```python
class CustomReLU(nn.Module):
    def __init__(self, threshold=0.0):
        super(CustomReLU, self).__init__()
        self.threshold = threshold
    
    def forward(self, x):
        return torch.where(x > self.threshold, x, torch.zeros_like(x))

# 使用
model = nn.Sequential(
    nn.Linear(10, 20),
    CustomReLU(threshold=0.0),
    nn.Linear(20, 10)
)
```

### 9.2 自定义有参数层

```python
class CustomLinear(nn.Module):
    def __init__(self, in_features, out_features):
        super(CustomLinear, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        
        # 创建参数
        self.weight = nn.Parameter(torch.randn(out_features, in_features))
        self.bias = nn.Parameter(torch.randn(out_features))
    
    def forward(self, x):
        return x @ self.weight.t() + self.bias

# 使用
layer = CustomLinear(10, 5)
output = layer(torch.randn(32, 10))
```

### 9.3 自定义损失函数

```python
class CustomLoss(nn.Module):
    def __init__(self, reduction='mean'):
        super(CustomLoss, self).__init__()
        self.reduction = reduction
    
    def forward(self, pred, target):
        loss = (pred - target) ** 2
        
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss

# 使用
criterion = CustomLoss()
loss = criterion(pred, target)
```

## 参考资源

- [[06-linear]] - 全连接层
- [[07-activation-functions]] - 激活函数详解
- [[06-AI/Pytorch/13-training-pipeline|13-training流程]] - 训练示例
- [PyTorch nn.Module 文档](https://pytorch.org/docs/stable/generated/torch.nn.Module.html)