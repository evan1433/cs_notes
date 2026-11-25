# 多层感知机（MLP）

多层感知机（Multi-Layer Perceptron，MLP）是最基础的神经网络结构，由多个全连接层堆叠而成。

## 一、基本概念

### 1.1 什么是 MLP？

MLP 是一种前馈神经网络，由以下部分组成：
- **输入层**：接收特征
- **隐藏层**：提取特征（可以有多个）
- **输出层**：输出结果

**关键点：** 在隐藏层之间必须添加**激活函数**，否则多层网络等价于单层。

```python
import torch
import torch.nn as nn

# 错误：没有激活函数
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.Linear(256, 128),
    nn.Linear(128, 10)
)
# 等价于 nn.Linear(784, 10)

# 正确：添加激活函数
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
)
```

### 1.2 为什么需要激活函数？

```python
# 没有激活函数
# y = W2 * (W1 * x) = (W2 * W1) * x = W * x
# 多层线性变换仍然等价于单层

# 有激活函数
# y = W2 * relu(W1 * x)
# 引入非线性，可以拟合任意复杂函数
```

## 二、MLP 实现

### 2.1 使用 Sequential

```python
import torch.nn as nn

# 简单 MLP
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
)

# 前向传播
x = torch.randn(32, 784)  # batch_size=32
output = model(x)          # shape: [32, 10]
```

### 2.2 自定义 Module

```python
import torch
import torch.nn as nn

class MLP(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(MLP, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        
        x = self.fc2(x)
        x = self.relu(x)
        x = self.dropout(x)
        
        x = self.fc3(x)
        return x

# 使用
model = MLP(input_size=784, hidden_size=256, num_classes=10)
output = model(torch.randn(32, 784))
```

### 2.3 使用 ModuleList

```python
class FlexibleMLP(nn.Module):
    def __init__(self, layer_sizes):
        """
        layer_sizes: [input_size, hidden1, hidden2, ..., output_size]
        """
        super(FlexibleMLP, self).__init__()
        
        self.layers = nn.ModuleList()
        for i in range(len(layer_sizes) - 1):
            self.layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
        
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        for i, layer in enumerate(self.layers[:-1]):
            x = layer(x)
            x = self.relu(x)
            x = self.dropout(x)
        x = self.layers[-1](x)  # 输出层不加激活
        return x

# 使用
model = FlexibleMLP([784, 512, 256, 128, 10])
```

## 三、完整训练示例

### 3.1 MNIST 分类

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# 数据预处理
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

# 加载数据
train_dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
test_dataset = datasets.MNIST('./data', train=False, transform=transform)

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=1000, shuffle=False)

# 模型定义
class MLP(nn.Module):
    def __init__(self):
        super(MLP, self).__init__()
        self.flatten = nn.Flatten()
        self.layers = nn.Sequential(
            nn.Linear(28*28, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 10)
        )
    
    def forward(self, x):
        x = self.flatten(x)
        x = self.layers(x)
        return x

model = MLP()

# 损失函数和优化器
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 训练函数
def train(model, train_loader, optimizer, criterion, epoch):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    for batch_idx, (data, target) in enumerate(train_loader):
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += (pred == target).sum().item()
        total += target.size(0)
        
        if batch_idx % 100 == 0:
            print(f'Train Epoch: {epoch} [{batch_idx * len(data)}/{len(train_loader.dataset)} '
                  f'({100. * batch_idx / len(train_loader):.0f}%)]\tLoss: {loss.item():.6f}')
    
    return total_loss / len(train_loader), correct / total

# 测试函数
def test(model, test_loader, criterion):
    model.eval()
    test_loss = 0
    correct = 0
    
    with torch.no_grad():
        for data, target in test_loader:
            output = model(data)
            test_loss += criterion(output, target).item()
            pred = output.argmax(dim=1)
            correct += (pred == target).sum().item()
    
    test_loss /= len(test_loader)
    accuracy = correct / len(test_loader.dataset)
    
    print(f'\nTest set: Average loss: {test_loss:.4f}, '
          f'Accuracy: {correct}/{len(test_loader.dataset)} ({100. * accuracy:.2f}%)\n')
    
    return test_loss, accuracy

# 训练循环
for epoch in range(1, 11):
    train_loss, train_acc = train(model, train_loader, optimizer, criterion, epoch)
    test_loss, test_acc = test(model, test_loader, criterion)
    
    print(f'Epoch {epoch}: Train Loss={train_loss:.4f}, Train Acc={train_acc:.4f}, '
          f'Test Loss={test_loss:.4f}, Test Acc={test_acc:.4f}')
```

## 四、常用技巧

### 4.1 Batch Normalization

```python
class MLPWithBN(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(MLPWithBN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.bn2 = nn.BatchNorm1d(hidden_size)
        self.fc3 = nn.Linear(hidden_size, num_classes)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.relu(x)
        
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.relu(x)
        
        x = self.fc3(x)
        return x
```

### 4.2 Dropout

```python
class MLPWithDropout(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes, dropout_prob=0.5):
        super(MLPWithDropout, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_prob),
            nn.Linear(hidden_size, num_classes)
        )
    
    def forward(self, x):
        return self.layers(x)
```

### 4.3 残差连接

```python
class ResidualBlock(nn.Module):
    def __init__(self, hidden_size):
        super(ResidualBlock, self).__init__()
        self.fc1 = nn.Linear(hidden_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        residual = x
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        x += residual  # 残差连接
        x = self.relu(x)
        return x

class ResidualMLP(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes, num_blocks=3):
        super(ResidualMLP, self).__init__()
        
        self.input_layer = nn.Linear(input_size, hidden_size)
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_size) for _ in range(num_blocks)
        ])
        self.output_layer = nn.Linear(hidden_size, num_classes)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.input_layer(x))
        for block in self.blocks:
            x = block(x)
        x = self.output_layer(x)
        return x
```

### 4.4 权重初始化

```python
import torch.nn.init as init

class MLP(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(MLP, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, num_classes)
        
        # 初始化
        self._init_weights()
    
    def _init_weights(self):
        # He 初始化（适合 ReLU）
        init.kaiming_normal_(self.fc1.weight, mode='fan_in', nonlinearity='relu')
        init.zeros_(self.fc1.bias)
        
        # Xavier 初始化
        init.xavier_normal_(self.fc2.weight)
        init.zeros_(self.fc2.bias)
    
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x
```

## 五、超参数选择

### 5.1 网络结构

```python
# 隐藏层大小：通常是输入大小的 2-4 倍或与输入相同
hidden_size = 256  # 或 512, 1024

# 隐藏层数量：通常 2-5 层
num_layers = 3

# 建议：从简单模型开始，逐步增加复杂度
layer_configs = [
    [784, 10],              # 1层
    [784, 256, 10],         # 2层
    [784, 256, 128, 10],    # 3层
]
```

### 5.2 训练参数

```python
# 学习率
learning_rate = 0.001  # Adam 默认
# learning_rate = 0.01  # SGD

# Batch size
batch_size = 64  # 或 128, 256, 512

# Dropout
dropout_prob = 0.2  # 通常 0.2-0.5

# 权重衰减（L2 正则化）
weight_decay = 0.0001
```

## 六、模型评估

### 6.1 模型复杂度

```python
def count_parameters(model):
    """计算模型参数数量"""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total_params, trainable_params

model = MLP(784, 256, 10)
total, trainable = count_parameters(model)
print(f"Total parameters: {total:,}")
print(f"Trainable parameters: {trainable:,}")
```

### 6.2 可视化

```python
from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter('runs/mlp_experiment')

# 记录模型结构
model = MLP()
writer.add_graph(model, torch.randn(1, 784))

# 记录损失和准确率
for epoch in range(epochs):
    # ... 训练代码 ...
    writer.add_scalar('Loss/train', train_loss, epoch)
    writer.add_scalar('Loss/test', test_loss, epoch)
    writer.add_scalar('Accuracy/train', train_acc, epoch)
    writer.add_scalar('Accuracy/test', test_acc, epoch)

writer.close()
```

## 七、常见问题

### 7.1 过拟合

```python
# 症状：训练集准确率高，测试集准确率低
# 解决方法：
# 1. Dropout
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Dropout(0.5),  # 添加 Dropout
    nn.Linear(256, 10)
)

# 2. 权重衰减
optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=0.001)

# 3. 早停
best_val_loss = float('inf')
patience = 10
counter = 0

for epoch in range(epochs):
    # ... 训练和验证 ...
    
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_model.pth')
        counter = 0
    else:
        counter += 1
        if counter >= patience:
            print("Early stopping!")
            break

# 4. 数据增强
transform = transforms.Compose([
    transforms.RandomRotation(10),
    transforms.ToTensor(),
])
```

### 7.2 欠拟合

```python
# 症状：训练集和测试集准确率都很低
# 解决方法：
# 1. 增加模型容量
model = nn.Sequential(
    nn.Linear(784, 512),  # 增加隐藏层大小
    nn.ReLU(),
    nn.Linear(512, 512),
    nn.ReLU(),
    nn.Linear(512, 10)
)

# 2. 增加训练时间
epochs = 50

# 3. 减少正则化
dropout_prob = 0.1  # 降低 dropout
weight_decay = 0.0  # 移除权重衰减

# 4. 使用更好的优化器
optimizer = optim.Adam(model.parameters(), lr=0.001)
```

### 7.3 梯度消失/爆炸

```python
# 解决方法：
# 1. 使用 Batch Normalization
# 2. 使用合适的激活函数（ReLU）
# 3. 使用合适的初始化
init.kaiming_normal_(layer.weight, mode='fan_in', nonlinearity='relu')

# 4. 梯度裁剪
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

## 八、MLP vs 其他模型

| 模型 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **MLP** | 简单、快速 | 不能处理空间结构 | 表格数据、简单分类 |
| **CNN** | 提取空间特征 | 需要更多计算 | 图像、视频 |
| **RNN/LSTM** | 处理序列 | 训练慢 | 文本、时间序列 |
| **Transformer** | 并行、长距离依赖 | 需要大量数据 | NLP、CV |

## 参考资源

- [[06-linear]] - 全连接层
- [[07-activation-functions]] - 激活函数详解
- [[08-loss-functions]] - 损失函数
- [[09-optimizers]] - 优化器
- [[06-ai/pytorch/13-training-pipeline|13-training流程]] - 完整训练示例