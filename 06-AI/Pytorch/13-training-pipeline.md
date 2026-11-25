---
title: PyTorch 模型训练完整流程
description: 从数据准备到模型保存与部署的 PyTorch 端到端训练流程
tags:
  - pytorch
  - training
aliases:
  - 06-AI/Pytorch/13-training流程
---

# PyTorch 模型训练完整流程

本文档详细介绍从数据准备到模型部署的完整训练流程。

## 一、整体流程概览

```
1. 数据准备
   ├── 数据收集与清洗
   ├── 数据预处理
   ├── 数据增强
   └── 创建 Dataset 和 DataLoader

2. 模型构建
   ├── 定义模型结构
   ├── 初始化参数
   └── 移动到 GPU

3. 训练准备
   ├── 定义损失函数
   ├── 定义优化器
   └── 定义学习率调度器

4. 训练循环
   ├── 前向传播
   ├── 计算损失
   ├── 反向传播
   └── 参数更新

5. 验证与测试
   ├── 验证集评估
   ├── 测试集评估
   └── 保存最佳模型

6. 模型保存与部署
   ├── 保存模型
   ├── 模型加载
   └── 模型推理
```

## 二、完整代码示例

### 2.1 数据准备

```python
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, datasets

# 图像数据预处理
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224),      # 随机裁剪
    transforms.RandomHorizontalFlip(),      # 随机翻转
    transforms.ColorJitter(0.4, 0.4, 0.4), # 颜色抖动
    transforms.ToTensor(),                  # 转为张量
    transforms.Normalize(                   # 归一化
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

val_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# 加载数据集
train_dataset = datasets.CIFAR10(
    root='./data',
    train=True,
    download=True,
    transform=train_transform
)

val_dataset = datasets.CIFAR10(
    root='./data',
    train=False,
    download=True,
    transform=val_transform
)

# 创建数据加载器
train_loader = DataLoader(
    train_dataset,
    batch_size=64,
    shuffle=True,
    num_workers=4,
    pin_memory=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=64,
    shuffle=False,
    num_workers=4,
    pin_memory=True
)

print(f"训练集大小: {len(train_dataset)}")
print(f"验证集大小: {len(val_dataset)}")
```

### 2.2 模型构建

```python
import torch.nn as nn
import torch.nn.functional as F

class SimpleCNN(nn.Module):
    def __init__(self, num_classes=10):
        super(SimpleCNN, self).__init__()
        
        # 卷积层
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        
        # 池化层
        self.pool = nn.MaxPool2d(2, 2)
        
        # 全连接层
        self.fc1 = nn.Linear(128 * 4 * 4, 512)
        self.fc2 = nn.Linear(512, num_classes)
        
        # Dropout
        self.dropout = nn.Dropout(0.5)
        
        # 批归一化
        self.bn1 = nn.BatchNorm2d(32)
        self.bn2 = nn.BatchNorm2d(64)
        self.bn3 = nn.BatchNorm2d(128)
    
    def forward(self, x):
        # 卷积块 1
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        
        # 卷积块 2
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        
        # 卷积块 3
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        
        # 展平
        x = x.view(-1, 128 * 4 * 4)
        
        # 全连接层
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        
        return x

# 创建模型
model = SimpleCNN(num_classes=10)

# 统计参数数量
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"总参数: {total_params:,}")
print(f"可训练参数: {trainable_params:,}")
```

### 2.3 训练准备

```python
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR

# 设备配置
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

# 移动模型到设备
model = model.to(device)

# 损失函数
criterion = nn.CrossEntropyLoss()

# 优化器
optimizer = optim.AdamW(
    model.parameters(),
    lr=0.001,
    weight_decay=0.01
)

# 学习率调度器
scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)

# 梯度裁剪阈值
max_grad_norm = 1.0
```

### 2.4 训练函数

```python
def train_one_epoch(model, train_loader, criterion, optimizer, device, max_grad_norm):
    """训练一个 epoch"""
    model.train()
    
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (inputs, targets) in enumerate(train_loader):
        # 移动数据到设备
        inputs, targets = inputs.to(device), targets.to(device)
        
        # 清零梯度
        optimizer.zero_grad()
        
        # 前向传播
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        
        # 反向传播
        loss.backward()
        
        # 梯度裁剪
        if max_grad_norm > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        
        # 参数更新
        optimizer.step()
        
        # 统计
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()
        
        # 打印进度
        if batch_idx % 100 == 0:
            print(f'  Batch {batch_idx}/{len(train_loader)}, '
                  f'Loss: {loss.item():.4f}, '
                  f'Acc: {100.*correct/total:.2f}%')
    
    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100. * correct / total
    
    return epoch_loss, epoch_acc
```

### 2.5 验证函数

```python
def validate(model, val_loader, criterion, device):
    """验证模型"""
    model.eval()
    
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            
            # 前向传播
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            
            # 统计
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
    
    epoch_loss = running_loss / len(val_loader)
    epoch_acc = 100. * correct / total
    
    return epoch_loss, epoch_acc
```

### 2.6 主训练循环

```python
import time
from datetime import datetime

def train_model(model, train_loader, val_loader, criterion, optimizer, 
                scheduler, device, num_epochs, save_dir='./checkpoints'):
    """完整训练流程"""
    
    # 创建保存目录
    import os
    os.makedirs(save_dir, exist_ok=True)
    
    # 记录
    train_losses, train_accs = [], []
    val_losses, val_accs = [], []
    
    best_val_acc = 0.0
    best_epoch = 0
    
    start_time = time.time()
    
    for epoch in range(1, num_epochs + 1):
        epoch_start = time.time()
        
        print(f'\nEpoch {epoch}/{num_epochs}')
        print('-' * 50)
        
        # 训练
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device, max_grad_norm
        )
        train_losses.append(train_loss)
        train_accs.append(train_acc)
        
        # 验证
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        val_losses.append(val_loss)
        val_accs.append(val_acc)
        
        # 更新学习率
        scheduler.step()
        current_lr = optimizer.param_groups[0]['lr']
        
        # 打印结果
        epoch_time = time.time() - epoch_start
        print(f'Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%')
        print(f'Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
        print(f'Learning Rate: {current_lr:.6f}')
        print(f'Epoch Time: {epoch_time:.2f}s')
        
        # 保存最佳模型
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'best_val_acc': best_val_acc,
                'train_loss': train_loss,
                'val_loss': val_loss,
            }
            
            save_path = os.path.join(save_dir, f'best_model.pth')
            torch.save(checkpoint, save_path)
            print(f'✓ 保存最佳模型 (Val Acc: {best_val_acc:.2f}%)')
        
        # 定期保存检查点
        if epoch % 10 == 0:
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
            }
            save_path = os.path.join(save_dir, f'checkpoint_epoch_{epoch}.pth')
            torch.save(checkpoint, save_path)
    
    total_time = time.time() - start_time
    
    print('\n' + '=' * 50)
    print('训练完成！')
    print(f'总训练时间: {total_time/60:.2f} 分钟')
    print(f'最佳验证准确率: {best_val_acc:.2f}% (Epoch {best_epoch})')
    print('=' * 50)
    
    # 返回训练历史
    history = {
        'train_loss': train_losses,
        'train_acc': train_accs,
        'val_loss': val_losses,
        'val_acc': val_accs,
        'best_val_acc': best_val_acc,
        'best_epoch': best_epoch,
    }
    
    return history

# 开始训练
history = train_model(
    model=model,
    train_loader=train_loader,
    val_loader=val_loader,
    criterion=criterion,
    optimizer=optimizer,
    scheduler=scheduler,
    device=device,
    num_epochs=50,
    save_dir='./checkpoints'
)
```

## 三、可视化与分析

### 3.1 训练曲线可视化

```python
import matplotlib.pyplot as plt

def plot_training_history(history):
    """绘制训练历史"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # 损失曲线
    ax1.plot(history['train_loss'], label='Train Loss')
    ax1.plot(history['val_loss'], label='Val Loss')
    ax1.xlabel('Epoch')
    ax1.ylabel('Loss')
    ax1.title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True)
    
    # 准确率曲线
    ax2.plot(history['train_acc'], label='Train Acc')
    ax2.plot(history['val_acc'], label='Val Acc')
    ax2.xlabel('Epoch')
    ax2.ylabel('Accuracy (%)')
    ax2.set_title('Training and Validation Accuracy')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('training_history.png', dpi=150)
    plt.show()

plot_training_history(history)
```

### 3.2 TensorBoard 可视化

```python
from torch.utils.tensorboard import SummaryWriter

def train_with_tensorboard(model, train_loader, val_loader, ...):
    writer = SummaryWriter('runs/experiment_1')
    
    for epoch in range(num_epochs):
        # ... 训练代码 ...
        
        # 记录损失和准确率
        writer.add_scalar('Loss/train', train_loss, epoch)
        writer.add_scalar('Loss/val', val_loss, epoch)
        writer.add_scalar('Accuracy/train', train_acc, epoch)
        writer.add_scalar('Accuracy/val', val_acc, epoch)
        writer.add_scalar('Learning_rate', current_lr, epoch)
        
        # 记录参数分布
        for name, param in model.named_parameters():
            writer.add_histogram(name, param, epoch)
            if param.grad is not None:
                writer.add_histogram(f'{name}.grad', param.grad, epoch)
    
    writer.close()

# 查看 TensorBoard
# tensorboard --logdir=runs
```

### 3.3 模型分析

```python
from sklearn.metrics import confusion_matrix, classification_report
import numpy as np

def evaluate_model(model, test_loader, device, class_names):
    """详细评估模型"""
    model.eval()
    
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # 分类报告
    print("分类报告:")
    print(classification_report(all_labels, all_preds, target_names=class_names))
    
    # 混淆矩阵
    cm = confusion_matrix(all_labels, all_preds)
    
    plt.figure(figsize=(10, 8))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion Matrix')
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45)
    plt.yticks(tick_marks, class_names)
    
    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.savefig('confusion_matrix.png', dpi=150)
    plt.show()
    
    return all_preds, all_labels

# 评估
class_names = ['airplane', 'automobile', 'bird', 'cat', 'deer',
               'dog', 'frog', 'horse', 'ship', 'truck']
all_preds, all_labels = evaluate_model(model, val_loader, device, class_names)
```

## 四、模型保存与加载

### 4.1 保存模型

```python
# 保存完整模型
torch.save(model, 'model_complete.pth')

# 只保存参数（推荐）
torch.save(model.state_dict(), 'model_weights.pth')

# 保存检查点
checkpoint = {
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'scheduler_state_dict': scheduler.state_dict(),
    'loss': loss,
    'best_acc': best_acc,
}
torch.save(checkpoint, 'checkpoint.pth')
```

### 4.2 加载模型

```python
# 加载完整模型
model = torch.load('model_complete.pth')

# 加载参数
model = SimpleCNN(num_classes=10)
model.load_state_dict(torch.load('model_weights.pth'))
model.eval()

# 加载检查点并继续训练
model = SimpleCNN(num_classes=10)
optimizer = optim.AdamW(model.parameters())

checkpoint = torch.load('checkpoint.pth')
model.load_state_dict(checkpoint['model_state_dict'])
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
start_epoch = checkpoint['epoch']
loss = checkpoint['loss']

# 继续训练
model.train()
```

### 4.3 跨设备加载

```python
# GPU → CPU
model.load_state_dict(torch.load('model.pth', map_location='cpu'))

# GPU 0 → GPU 1
model.load_state_dict(torch.load('model.pth', map_location={'cuda:0': 'cuda:1'}))

# 自动选择设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.load_state_dict(torch.load('model.pth', map_location=device))
```

## 五、模型推理

### 5.1 单张图片推理

```python
from PIL import Image

def predict_single_image(model, image_path, transform, device, class_names):
    """单张图片预测"""
    model.eval()
    
    # 加载图片
    image = Image.open(image_path).convert('RGB')
    
    # 预处理
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    # 预测
    with torch.no_grad():
        output = model(input_tensor)
        probs = torch.softmax(output, dim=1)
        _, pred = torch.max(probs, 1)
    
    # 获取结果
    predicted_class = class_names[pred.item()]
    confidence = probs[0, pred.item()].item()
    
    print(f"预测类别: {predicted_class}")
    print(f"置信度: {confidence:.4f}")
    
    # 显示前3个预测
    top3_probs, top3_indices = torch.topk(probs[0], 3)
    print("\nTop-3 预测:")
    for i in range(3):
        print(f"  {class_names[top3_indices[i]]}: {top3_probs[i]:.4f}")
    
    return predicted_class, confidence

# 使用
image_path = 'test_image.jpg'
predict_single_image(model, image_path, val_transform, device, class_names)
```

### 5.2 批量推理

```python
def batch_predict(model, dataloader, device):
    """批量预测"""
    model.eval()
    
    all_preds = []
    all_probs = []
    
    with torch.no_grad():
        for inputs, _ in dataloader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            probs = torch.softmax(outputs, dim=1)
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
    
    return np.array(all_preds), np.array(all_probs)
```

## 六、高级技巧

### 6.1 早停（Early Stopping）

```python
class EarlyStopping:
    def __init__(self, patience=10, min_delta=0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.early_stop = False
    
    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0
        
        return self.early_stop

# 使用
early_stopping = EarlyStopping(patience=10)

for epoch in range(num_epochs):
    # ... 训练 ...
    
    if early_stopping(val_loss):
        print("早停触发！")
        break
```

### 6.2 混合精度训练

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

def train_with_amp(model, train_loader, criterion, optimizer, device):
    model.train()
    
    for inputs, targets in train_loader:
        inputs, targets = inputs.to(device), targets.to(device)
        
        optimizer.zero_grad()
        
        # 自动混合精度
        with autocast():
            outputs = model(inputs)
            loss = criterion(outputs, targets)
        
        # 缩放梯度
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
```

### 6.3 梯度累积

```python
accumulation_steps = 4

optimizer.zero_grad()

for i, (inputs, targets) in enumerate(train_loader):
    inputs, targets = inputs.to(device), targets.to(device)
    
    outputs = model(inputs)
    loss = criterion(outputs, targets) / accumulation_steps
    loss.backward()
    
    if (i + 1) % accumulation_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

## 七、完整项目模板

```python
# 项目结构
"""
project/
├── data/
│   ├── train/
│   └── val/
├── models/
│   └── model.py
├── utils/
│   ├── dataset.py
│   └── utils.py
├── configs/
│   └── config.py
├── train.py
├── test.py
└── inference.py
"""

# train.py
"""
完整训练脚本模板，包含：
- 参数解析
- 数据加载
- 模型构建
- 训练循环
- 验证
- 保存检查点
- 可视化
"""
```

## 参考资源

- [[04-data-loading]] - 数据处理
- [[05-nn-module]] - 模型构建
- [[08-loss-functions]] - 损失函数
- [[09-optimizers]] - 优化器
- [PyTorch 官方教程](https://pytorch.org/tutorials/)