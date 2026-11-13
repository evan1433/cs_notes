# PyTorch 优化器

优化器负责根据梯度更新模型参数，是训练神经网络的核心组件。

## 一、常用优化器

### 1.1 SGD（随机梯度下降）

最基础的优化器。

```python
import torch
import torch.nn as nn
import torch.optim as optim

model = nn.Linear(10, 1)

# 基础 SGD
optimizer = optim.SGD(model.parameters(), lr=0.01)

# 带动量的 SGD（推荐）
optimizer = optim.SGD(
    model.parameters(),
    lr=0.01,
    momentum=0.9,        # 动量系数
    weight_decay=0.001,  # L2 正则化
    nesterov=True        # Nesterov 动量
)
```

**动量的作用：**
- 加速收敛
- 减少震荡
- 帮助跳出局部最小值

### 1.2 Adam

最常用的自适应学习率优化器。

```python
optimizer = optim.Adam(
    model.parameters(),
    lr=0.001,            # 学习率
    betas=(0.9, 0.999),  # 一阶和二阶矩估计的衰减率
    eps=1e-8,            # 数值稳定性
    weight_decay=0,      # L2 正则化
    amsgrad=False        # AMSGrad 变体
)
```

**特点：**
- 自适应学习率
- 对不同参数使用不同的学习率
- 收敛快，适合大多数任务

### 1.3 AdamW

改进版的 Adam，修复了权重衰减问题。

```python
optimizer = optim.AdamW(
    model.parameters(),
    lr=0.001,
    betas=(0.9, 0.999),
    eps=1e-8,
    weight_decay=0.01,   # 正确实现的权重衰减
    amsgrad=False
)
```

**推荐使用场景：**
- Transformer 模型（BERT、GPT等）
- 需要权重衰减的场景
- 比 Adam 更稳定

### 1.4 RMSprop

适合 RNN 训练。

```python
optimizer = optim.RMSprop(
    model.parameters(),
    lr=0.01,
    alpha=0.99,          # 平滑常数
    eps=1e-8,
    weight_decay=0,
    momentum=0,
    centered=False
)
```

### 1.5 Adagrad

适合稀疏数据。

```python
optimizer = optim.Adagrad(
    model.parameters(),
    lr=0.01,
    lr_decay=0,
    weight_decay=0,
    initial_accumulator_value=0,
    eps=1e-10
)
```

### 1.6 其他优化器

```python
# Adadelta
optimizer = optim.Adadelta(model.parameters(), lr=1.0, rho=0.9)

# Adamax (Adam的无穷范数变体)
optimizer = optim.Adamax(model.parameters(), lr=0.002)

# SparseAdam (稀疏梯度优化)
optimizer = optim.SparseAdam(model.parameters(), lr=0.001)
```

## 二、优化器选择指南

| 优化器 | 适用场景 | 优点 | 缺点 |
|--------|---------|------|------|
| **SGD+Momentum** | 计算机视觉 | 泛化性能好 | 需要调学习率 |
| **Adam** | 默认选择 | 收敛快，自适应 | 可能不收敛 |
| **AdamW** | Transformer | 权重衰减正确 | - |
| **RMSprop** | RNN | 适合非平稳目标 | - |

**经验法则：**
1. **首选 Adam 或 AdamW**：大多数情况表现良好
2. **计算机视觉**：SGD + Momentum 可能效果更好
3. **Transformer**：AdamW
4. **RNN**：RMSprop 或 Adam

## 三、学习率策略

### 3.1 学习率调度器

```python
model = nn.Linear(10, 1)
optimizer = optim.Adam(model.parameters(), lr=0.001)

# StepLR：每 step_size 个 epoch 衰减 gamma
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)

# MultiStepLR：在指定的 epoch 衰减
scheduler = optim.lr_scheduler.MultiStepLR(
    optimizer, 
    milestones=[30, 60, 90], 
    gamma=0.1
)

# ExponentialLR：指数衰减
scheduler = optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.9)

# CosineAnnealingLR：余弦退火
scheduler = optim.lr_scheduler.CosineAnnealingLR(
    optimizer,
    T_max=100,    # 周期
    eta_min=0     # 最小学习率
)

# ReduceLROnPlateau：验证损失不降时衰减
scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode='min',      # 监控指标越小越好
    factor=0.1,      # 衰减因子
    patience=10,     # 等待多少个 epoch
    verbose=True
)

# CosineAnnealingWarmRestarts：带热重启的余弦退火
scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
    optimizer,
    T_0=10,          # 第一次重启周期
    T_mult=2,        # 重启后周期倍数
    eta_min=0
)
```

### 3.2 使用调度器

```python
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)

for epoch in range(100):
    # 训练
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
    
    # 验证
    val_loss = validate(model, val_loader, criterion)
    
    # 更新学习率
    scheduler.step()
    
    # 如果是 ReduceLROnPlateau
    # scheduler.step(val_loss)
    
    print(f"Epoch {epoch}, LR: {optimizer.param_groups[0]['lr']:.6f}")
```

### 3.3 Warmup

```python
# 手动实现 warmup
def get_lr(optimizer):
    return optimizer.param_groups[0]['lr']

def set_lr(optimizer, lr):
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr

warmup_epochs = 5
base_lr = 0.001

for epoch in range(100):
    # Warmup
    if epoch < warmup_epochs:
        lr = base_lr * (epoch + 1) / warmup_epochs
        set_lr(optimizer, lr)
    else:
        scheduler.step()
    
    print(f"Epoch {epoch}, LR: {get_lr(optimizer):.6f}")

# 使用 LambdaLR 实现 warmup
def warmup_lambda(epoch):
    if epoch < warmup_epochs:
        return (epoch + 1) / warmup_epochs
    return 1.0

scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=warmup_lambda)
```

## 四、参数组

### 4.1 不同参数组使用不同学习率

```python
model = nn.Sequential(
    nn.Linear(10, 20),
    nn.Linear(20, 10)
)

# 不同层使用不同学习率
optimizer = optim.Adam([
    {'params': model[0].parameters(), 'lr': 0.001},
    {'params': model[1].parameters(), 'lr': 0.0001}
])

# 冻结部分参数
for param in model[0].parameters():
    param.requires_grad = False

optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()))
```

### 4.2 访问和修改参数组

```python
# 访问参数组
print(optimizer.param_groups[0]['lr'])
print(optimizer.param_groups[0]['weight_decay'])

# 修改学习率
for param_group in optimizer.param_groups:
    param_group['lr'] = 0.0001

# 或使用调度器
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)
```

## 五、梯度处理

### 5.1 梯度裁剪

防止梯度爆炸。

```python
# 按值裁剪
torch.nn.utils.clip_grad_value_(model.parameters(), clip_value=0.5)

# 按范数裁剪（推荐）
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

# 在训练循环中使用
optimizer.zero_grad()
loss.backward()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```

### 5.2 梯度累积

模拟更大的 batch size。

```python
accumulation_steps = 4

optimizer.zero_grad()

for i, (data, target) in enumerate(train_loader):
    output = model(data)
    loss = criterion(output, target) / accumulation_steps
    loss.backward()
    
    if (i + 1) % accumulation_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

## 六、优化器状态

### 6.1 保存和加载优化器状态

```python
# 保存
checkpoint = {
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'scheduler_state_dict': scheduler.state_dict(),
    'epoch': epoch,
}
torch.save(checkpoint, 'checkpoint.pth')

# 加载
checkpoint = torch.load('checkpoint.pth')
model.load_state_dict(checkpoint['model_state_dict'])
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
epoch = checkpoint['epoch']
```

### 6.2 查看优化器状态

```python
# Adam 优化器保存了每个参数的一阶和二阶矩估计
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 训练几步后
for _ in range(10):
    optimizer.zero_grad()
    loss = criterion(model(x), y)
    loss.backward()
    optimizer.step()

# 查看状态
for name, param in model.named_parameters():
    if param in optimizer.state:
        state = optimizer.state[param]
        print(f"{name}:")
        print(f"  step: {state['step']}")
        print(f"  exp_avg: {state['exp_avg'].shape}")
        print(f"  exp_avg_sq: {state['exp_avg_sq'].shape}")
```

## 七、训练技巧

### 7.1 学习率范围测试

找到最优学习率范围。

```python
import matplotlib.pyplot as plt

lrs = []
losses = []

lr = 1e-7
optimizer = optim.SGD(model.parameters(), lr=lr)

for batch in train_loader:
    optimizer.zero_grad()
    loss = criterion(model(batch[0]), batch[1])
    loss.backward()
    optimizer.step()
    
    lrs.append(lr)
    losses.append(loss.item())
    
    lr *= 1.1
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
    
    if lr > 10 or loss.item() > 10:
        break

plt.plot(lrs, losses)
plt.xscale('log')
plt.xlabel('Learning Rate')
plt.ylabel('Loss')
plt.show()
```

### 7.2 差分学习率

不同层使用不同学习率。

```python
# 预训练模型微调
model = models.resnet50(pretrained=True)

# 冻结早期层
for param in model.conv1.parameters():
    param.requires_grad = False
for param in model.bn1.parameters():
    param.requires_grad = False
for param in model.layer1.parameters():
    param.requires_grad = False

# 不同层使用不同学习率
optimizer = optim.Adam([
    {'params': model.layer2.parameters(), 'lr': 1e-4},
    {'params': model.layer3.parameters(), 'lr': 1e-4},
    {'params': model.layer4.parameters(), 'lr': 1e-4},
    {'params': model.fc.parameters(), 'lr': 1e-3},  # 分类层学习率大
])
```

### 7.3 Lookahead 优化器

```python
# 需要安装: pip install lookahead
from lookahead import Lookahead

base_optimizer = optim.Adam(model.parameters(), lr=0.001)
optimizer = Lookahead(base_optimizer, k=5, alpha=0.5)

# 或手动实现
class Lookahead(torch.optim.Optimizer):
    def __init__(self, optimizer, k=5, alpha=0.5):
        self.optimizer = optimizer
        self.k = k
        self.alpha = alpha
        self.param_groups = optimizer.param_groups
        self.state = {}
        
        for group in optimizer.param_groups:
            for p in group['params']:
                self.state[p] = {'slow': p.data.clone()}
        
        self.counter = 0
    
    def step(self, closure=None):
        self.optimizer.step(closure)
        self.counter += 1
        
        if self.counter % self.k == 0:
            for group in self.param_groups:
                for p in group['params']:
                    slow = self.state[p]['slow']
                    slow.add_(self.alpha, p.data - slow)
                    p.data.copy_(slow)
```

## 八、常见问题

### 8.1 学习率太大

```python
# 症状：损失 NaN 或震荡
# 解决：降低学习率
optimizer = optim.Adam(model.parameters(), lr=1e-4)  # 从 1e-3 降到 1e-4

# 使用学习率范围测试找到合适的范围
```

### 8.2 学习率太小

```python
# 症状：收敛太慢
# 解决：增加学习率或使用 warmup
optimizer = optim.Adam(model.parameters(), lr=1e-3)
```

### 8.3 不收敛

```python
# 检查梯度
for name, param in model.named_parameters():
    if param.grad is not None:
        print(f"{name}: grad_norm = {param.grad.norm().item()}")

# 尝试不同的优化器
# SGD -> Adam
# Adam -> AdamW

# 使用学习率调度
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)
```

## 九、完整训练示例

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# 模型
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Linear(256, 10)
)

# 优化器
optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)

# 学习率调度器
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)

# 损失函数
criterion = nn.CrossEntropyLoss()

# 数据加载
train_loader = DataLoader(...)
val_loader = DataLoader(...)

# 训练循环
for epoch in range(100):
    # 训练
    model.train()
    for data, target in train_loader:
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        
        # 梯度裁剪
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
    
    # 验证
    model.eval()
    val_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in val_loader:
            output = model(data)
            val_loss += criterion(output, target).item()
            pred = output.argmax(dim=1)
            correct += (pred == target).sum().item()
    
    val_loss /= len(val_loader)
    accuracy = correct / len(val_loader.dataset)
    
    # 更新学习率
    scheduler.step()
    
    print(f"Epoch {epoch}: Loss={val_loss:.4f}, Acc={accuracy:.4f}, LR={optimizer.param_groups[0]['lr']:.6f}")
```

## 参考资源

- [[08-loss-functions]] - 损失函数详解
- [[13-training流程]] - 训练示例
- [PyTorch 优化器文档](https://pytorch.org/docs/stable/optim.html)
- [学习率调度器文档](https://pytorch.org/docs/stable/optim.html#how-to-adjust-learning-rate)