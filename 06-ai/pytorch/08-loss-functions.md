# PyTorch 损失函数

损失函数用于衡量模型预测与真实标签之间的差距，指导模型优化方向。

## 一、常用损失函数

### 1.1 均方误差损失（MSE Loss）

回归问题最常用的损失函数。

```python
import torch
import torch.nn as nn

criterion = nn.MSELoss()

pred = torch.tensor([1.0, 2.0, 3.0])
target = torch.tensor([1.5, 2.5, 3.5])

loss = criterion(pred, target)
# loss = mean((pred - target)^2) = mean(0.25) = 0.25

# reduction 参数
criterion = nn.MSELoss(reduction='mean')   # 默认，返回平均值
criterion = nn.MSELoss(reduction='sum')    # 返回总和
criterion = nn.MSELoss(reduction='none')   # 不归约，返回每个元素的损失
```

### 1.2 L1 损失（MAE Loss）

对异常值更鲁棒。

```python
criterion = nn.L1Loss()

pred = torch.tensor([1.0, 2.0, 3.0])
target = torch.tensor([1.5, 2.5, 3.5])

loss = criterion(pred, target)
# loss = mean(|pred - target|) = 0.5

# Smooth L1 Loss（Huber Loss）
criterion = nn.SmoothL1Loss()
# 当 |x-y| < 1 时使用平方，否则使用线性
```

### 1.3 交叉熵损失（CrossEntropyLoss）

**多分类问题最常用**的损失函数。

```python
# 注意：CrossEntropyLoss 内置了 Softmax
# 输入是 logits（未经过 softmax 的值）

criterion = nn.CrossEntropyLoss()

# pred: [batch_size, num_classes]，模型输出的 logits
pred = torch.tensor([[1.0, 2.0, 3.0], [1.0, 1.0, 1.0]])
# target: [batch_size]，类别索引
target = torch.tensor([2, 0])

loss = criterion(pred, target)

# 等价于：
# loss = -log(softmax(pred)[range(batch), target]).mean()
```

**重要参数：**

```python
# 类别权重（处理类别不平衡）
class_weights = torch.tensor([1.0, 2.0, 3.0])  # 第0类权重1，第1类权重2...
criterion = nn.CrossEntropyLoss(weight=class_weights)

# 忽略特定标签（如填充标签）
criterion = nn.CrossEntropyLoss(ignore_index=-100)

# 标签平滑
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
```

### 1.4 二分类交叉熵损失（BCE Loss）

二分类问题使用。

```python
# BCELoss - 输入需要先经过 Sigmoid
criterion = nn.BCELoss()
pred = torch.tensor([0.5, 0.7, 0.3])  # 已经过 sigmoid
target = torch.tensor([1.0, 1.0, 0.0])
loss = criterion(pred, target)

# BCEWithLogitsLoss - 内置 Sigmoid（推荐）
criterion = nn.BCEWithLogitsLoss()
logits = torch.tensor([0.0, 0.8, -0.5])  # 未经过 sigmoid
target = torch.tensor([1.0, 1.0, 0.0])
loss = criterion(logits, target)

# 多标签分类
logits = torch.randn(10, 5)  # 10个样本，5个类别
target = torch.randint(0, 2, (10, 5)).float()  # 多标签
loss = criterion(logits, target)
```

### 1.5 负对数似然损失（NLLLoss）

配合 LogSoftmax 使用。

```python
log_softmax = nn.LogSoftmax(dim=1)
criterion = nn.NLLLoss()

pred = torch.randn(10, 5)
log_probs = log_softmax(pred)
target = torch.randint(0, 5, (10,))

loss = criterion(log_probs, target)

# 等价于 CrossEntropyLoss(pred, target)
# CrossEntropyLoss = LogSoftmax + NLLLoss
```

### 1.6 CTC Loss

序列标注任务（如语音识别）。

```python
criterion = nn.CTCLoss()

# log_probs: [sequence_length, batch_size, num_classes]
log_probs = torch.randn(50, 16, 5).log_softmax(2)
# targets: [batch_size, max_target_length]
targets = torch.randint(1, 5, (16, 30), dtype=torch.long)
# input_lengths: 每个样本的实际长度
input_lengths = torch.full((16,), 50, dtype=torch.long)
# target_lengths: 每个目标序列的实际长度
target_lengths = torch.randint(10, 30, (16,), dtype=torch.long)

loss = criterion(log_probs, targets, input_lengths, target_lengths)
```

### 1.7 三元组损失（Triplet Margin Loss）

用于度量学习、人脸识别等。

```python
criterion = nn.TripletMarginLoss(margin=1.0, p=2)

anchor = torch.randn(10, 128)
positive = torch.randn(10, 128)  # 与 anchor 同类
negative = torch.randn(10, 128)  # 与 anchor 不同类

loss = criterion(anchor, positive, negative)
# loss = max(d(a, p) - d(a, n) + margin, 0)
```

### 1.8 余弦嵌入损失

```python
criterion = nn.CosineEmbeddingLoss(margin=0.0)

x1 = torch.randn(10, 128)
x2 = torch.randn(10, 128)
y = torch.tensor([1, -1, 1, -1, 1, -1, 1, -1, 1, -1])  # 1相似，-1不相似

loss = criterion(x1, x2, y)
```

## 二、损失函数选择指南

### 2.1 回归问题

| 损失函数 | 适用场景 | 特点 |
|---------|---------|------|
| MSELoss | 默认选择 | 对异常值敏感 |
| L1Loss | 有异常值 | 对异常值鲁棒 |
| SmoothL1Loss | 平衡选择 | 结合MSE和L1优点 |

```python
# 回归问题示例
model = nn.Linear(10, 1)
criterion = nn.MSELoss()

for epoch in range(epochs):
    pred = model(x)
    loss = criterion(pred, target)
    loss.backward()
    optimizer.step()
```

### 2.2 分类问题

| 任务类型 | 推荐损失函数 |
|---------|------------|
| 二分类 | BCEWithLogitsLoss |
| 多分类 | CrossEntropyLoss |
| 多标签分类 | BCEWithLogitsLoss |

```python
# 多分类示例
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Linear(256, 10)  # 输出 logits，不需要 softmax
)
criterion = nn.CrossEntropyLoss()

for epoch in range(epochs):
    logits = model(x)
    loss = criterion(logits, target)  # target 是类别索引
    loss.backward()
    optimizer.step()
```

### 2.3 序列问题

| 任务类型 | 推荐损失函数 |
|---------|------------|
| 序列分类 | CrossEntropyLoss |
| 序列标注 | CrossEntropyLoss |
| CT C任务 | CTCLoss |
| 序列相似度 | TripletMarginLoss |

## 三、高级用法

### 3.1 类别不平衡处理

```python
import numpy as np
from sklearn.utils.class_weight import compute_class_weight

# 计算类别权重
labels = [...]  # 所有标签
class_weights = compute_class_weight('balanced', classes=np.unique(labels), y=labels)
class_weights = torch.tensor(class_weights, dtype=torch.float)

# 使用权重
criterion = nn.CrossEntropyLoss(weight=class_weights)

# 或使用 Focal Loss（自定义）
class FocalLoss(nn.Module):
    def __init__(self, alpha=1, gamma=2, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
    
    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        return focal_loss
```

### 3.2 标签平滑

```python
# 内置标签平滑（PyTorch >= 1.10）
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

# 手动实现
def label_smoothing_loss(pred, target, num_classes, smoothing=0.1):
    """
    pred: [batch_size, num_classes]
    target: [batch_size]
    """
    confidence = 1.0 - smoothing
    smooth_value = smoothing / (num_classes - 1)
    
    # 构建平滑标签
    one_hot = torch.zeros_like(pred).scatter(1, target.unsqueeze(1), 1)
    smooth_labels = one_hot * confidence + (1 - one_hot) * smooth_value
    
    loss = -torch.sum(smooth_labels * F.log_softmax(pred, dim=1), dim=1)
    return loss.mean()
```

### 3.3 多任务损失

```python
class MultiTaskLoss(nn.Module):
    def __init__(self, task_weights=None):
        super(MultiTaskLoss, self).__init__()
        self.task_weights = task_weights or [1.0, 1.0]
    
    def forward(self, pred1, target1, pred2, target2):
        loss1 = nn.CrossEntropyLoss()(pred1, target1)
        loss2 = nn.MSELoss()(pred2, target2)
        
        total_loss = self.task_weights[0] * loss1 + self.task_weights[1] * loss2
        return total_loss, loss1, loss2

# 使用
criterion = MultiTaskLoss(task_weights=[1.0, 0.5])
total_loss, loss1, loss2 = criterion(pred1, target1, pred2, target2)
```

### 3.4 自定义损失函数

```python
class DiceLoss(nn.Module):
    """用于图像分割的 Dice Loss"""
    def __init__(self, smooth=1.0):
        super(DiceLoss, self).__init__()
        self.smooth = smooth
    
    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        
        pred_flat = pred.view(-1)
        target_flat = target.view(-1)
        
        intersection = (pred_flat * target_flat).sum()
        dice = (2.0 * intersection + self.smooth) / (
            pred_flat.sum() + target_flat.sum() + self.smooth
        )
        
        return 1.0 - dice

class IoULoss(nn.Module):
    """IoU Loss for segmentation"""
    def __init__(self, smooth=1.0):
        super(IoULoss, self).__init__()
        self.smooth = smooth
    
    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        
        intersection = (pred * target).sum()
        union = pred.sum() + target.sum() - intersection
        
        iou = (intersection + self.smooth) / (union + self.smooth)
        return 1.0 - iou
```

## 四、损失函数监控

### 4.1 记录损失值

```python
train_losses = []
val_losses = []

for epoch in range(epochs):
    # 训练
    model.train()
    epoch_loss = 0
    for data, target in train_loader:
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    
    train_loss = epoch_loss / len(train_loader)
    train_losses.append(train_loss)
    
    # 验证
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for data, target in val_loader:
            output = model(data)
            val_loss += criterion(output, target).item()
    
    val_loss /= len(val_loader)
    val_losses.append(val_loss)
    
    print(f"Epoch {epoch}: Train Loss = {train_loss:.4f}, Val Loss = {val_loss:.4f}")
```

### 4.2 使用 TensorBoard

```python
from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter('runs/experiment_1')

for epoch in range(epochs):
    # ... 训练代码 ...
    
    writer.add_scalar('Loss/train', train_loss, epoch)
    writer.add_scalar('Loss/val', val_loss, epoch)

writer.close()
```

## 五、常见问题

### 5.1 维度不匹配

```python
# 错误：CrossEntropyLoss 需要 target 是类别索引
pred = torch.randn(10, 5)  # [batch, num_classes]
target = torch.randn(10, 5)  # 错误！应该是 [batch]
loss = criterion(pred, target)  # RuntimeError

# 正确
target = torch.randint(0, 5, (10,))  # 类别索引
loss = criterion(pred, target)

# 或者使用 one-hot
target_onehot = torch.zeros(10, 5).scatter(1, target.unsqueeze(1), 1)
```

### 5.2 输出未归一化

```python
# CrossEntropyLoss 不需要手动 softmax
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Linear(256, 10)  # 输出 logits
)
criterion = nn.CrossEntropyLoss()
logits = model(x)
loss = criterion(logits, target)  # 正确

# 错误：手动 softmax
logits = model(x)
probs = torch.softmax(logits, dim=1)  # 不需要！
loss = criterion(probs, target)  # 结果错误
```

### 5.3 损失为 NaN

```python
# 可能原因
# 1. 学习率太大
# 2. 梯度爆炸
# 3. 输入包含 NaN

# 检查
if torch.isnan(loss):
    print("Loss is NaN!")
    print(f"Input NaN: {torch.isnan(x).any()}")
    print(f"Output NaN: {torch.isnan(output).any()}")

# 解决
# 1. 降低学习率
optimizer = optim.Adam(model.parameters(), lr=1e-4)

# 2. 梯度裁剪
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

# 3. 检查数据
x = torch.nan_to_num(x, nan=0.0)
```

## 六、损失函数对比

| 损失函数 | 公式 | 适用场景 | 输出要求 |
|---------|------|---------|---------|
| MSELoss | (y-y')^2 | 回归 | 任意 |
| L1Loss | \|y-y'\| | 回归(鲁棒) | 任意 |
| CrossEntropyLoss | -Σy·log(y') | 多分类 | logits |
| BCELoss | -[y·log(y')+(1-y)·log(1-y')] | 二分类 | [0,1] |
| BCEWithLogitsLoss | BCE+Sigmoid | 二分类 | logits |
| NLLLoss | -Σy·log(y') | 多分类 | log概率 |
| CTCLoss | -log(Σ正确路径) | 序列标注 | log概率 |

## 参考资源

- [[09-optimizers]] - 参数优化
- [[06-ai/pytorch/13-training-pipeline|13-training流程]] - 完整训练示例
- [PyTorch 损失函数文档](https://pytorch.org/docs/stable/nn.html#loss-functions)