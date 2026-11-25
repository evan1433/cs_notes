# PyTorch 数据加载（Dataset & DataLoader）

PyTorch 提供了 `Dataset` 和 `DataLoader` 两个核心类来高效加载和处理数据。

## 一、Dataset 基础

### 1.1 Dataset 抽象类

自定义数据集需要继承 `torch.utils.data.Dataset` 并实现三个方法：

```python
from torch.utils.data import Dataset

class MyDataset(Dataset):
    def __init__(self, data, labels):
        """
        初始化数据集
        """
        self.data = data
        self.labels = labels
    
    def __len__(self):
        """
        返回数据集大小
        """
        return len(self.data)
    
    def __getitem__(self, idx):
        """
        根据索引获取单个样本
        """
        return self.data[idx], self.labels[idx]

# 使用示例
import torch

data = torch.randn(100, 10)  # 100个样本，每个10维
labels = torch.randint(0, 2, (100,))  # 100个标签

dataset = MyDataset(data, labels)
print(len(dataset))  # 100
print(dataset[0])    # (tensor([...]), tensor(1))
```

### 1.2 加载图像数据集

```python
from torch.utils.data import Dataset
from PIL import Image
import os

class ImageDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        """
        Args:
            root_dir: 图像目录路径
            transform: 可选的数据增强
        """
        self.root_dir = root_dir
        self.transform = transform
        self.images = os.listdir(root_dir)
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        img_name = os.path.join(self.root_dir, self.images[idx])
        image = Image.open(img_name)
        
        if self.transform:
            image = self.transform(image)
        
        return image

# 使用示例
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

dataset = ImageDataset('./data/images', transform=transform)
```

### 1.3 加载 CSV 数据集

```python
import pandas as pd
import torch
from torch.utils.data import Dataset

class CSVDataset(Dataset):
    def __init__(self, csv_file, transform=None):
        """
        Args:
            csv_file: CSV文件路径
            transform: 可选的数据变换
        """
        self.data = pd.read_csv(csv_file)
        self.transform = transform
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        # 假设最后一列是标签
        features = self.data.iloc[idx, :-1].values
        label = self.data.iloc[idx, -1]
        
        features = torch.FloatTensor(features)
        label = torch.tensor(label, dtype=torch.long)
        
        if self.transform:
            features = self.transform(features)
        
        return features, label
```

## 二、DataLoader 详解

### 2.1 基本使用

```python
from torch.utils.data import DataLoader

# 创建 DataLoader
dataloader = DataLoader(
    dataset,
    batch_size=32,      # 每批样本数
    shuffle=True,       # 是否打乱
    num_workers=4,      # 数据加载的进程数
    pin_memory=True,    # 锁页内存（加速GPU传输）
)

# 遍历数据
for batch_idx, (data, labels) in enumerate(dataloader):
    print(f"Batch {batch_idx}: data shape = {data.shape}")
    # data shape: torch.Size([32, 10])
```

### 2.2 重要参数详解

```python
dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,           # 训练时打乱，测试时不打乱
    sampler=None,           # 自定义采样策略
    batch_sampler=None,      # 自定义批次采样
    num_workers=4,          # 多进程加载数据
    collate_fn=None,        # 自定义批次整理函数
    pin_memory=True,        # 锁页内存，加速 CPU→GPU
    drop_last=False,        # 是否丢弃不完整的最后一批
    timeout=0,              # 数据加载超时
    worker_init_fn=None,    # worker初始化函数
)
```

### 2.3 collate_fn 自定义批次整理

```python
def collate_fn(batch):
    """
    自定义批次整理函数
    batch: 一个列表，包含 batch_size 个 __getitem__ 返回的值
    """
    data, labels = zip(*batch)
    
    # 自定义处理，如填充序列
    data = torch.nn.utils.rnn.pad_sequence(data, batch_first=True)
    labels = torch.tensor(labels)
    
    return data, labels

dataloader = DataLoader(dataset, batch_size=32, collate_fn=collate_fn)
```

### 2.4 处理变长序列

```python
from torch.nn.utils.rnn import pad_sequence

class TextDataset(Dataset):
    def __init__(self, texts, labels):
        self.texts = [torch.tensor(t) for t in texts]
        self.labels = labels
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        return self.texts[idx], self.labels[idx]

def collate_fn(batch):
    texts, labels = zip(*batch)
    
    # 填充到相同长度
    texts_padded = pad_sequence(texts, batch_first=True, padding_value=0)
    labels = torch.tensor(labels)
    
    # 记录实际长度（用于pack_padded_sequence）
    lengths = torch.tensor([len(t) for t in texts])
    
    return texts_padded, labels, lengths

dataloader = DataLoader(dataset, batch_size=32, collate_fn=collate_fn)
```

## 三、数据预处理

### 3.1 torchvision.transforms

```python
from torchvision import transforms

# 常用图像变换
transform = transforms.Compose([
    # 调整大小
    transforms.Resize(256),
    transforms.CenterCrop(224),
    
    # 数据增强
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    
    # 转换为张量
    transforms.ToTensor(),
    
    # 归一化
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

# 训练集和测试集使用不同的变换
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

test_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
```

### 3.2 自定义变换

```python
class CustomTransform:
    def __init__(self, probability=0.5):
        self.probability = probability
    
    def __call__(self, x):
        # 实现变换逻辑
        if torch.rand(1) < self.probability:
            x = x * 2  # 示例：随机乘以2
        return x
    
    def __repr__(self):
        return f"CustomTransform(probability={self.probability})"

# 使用自定义变换
transform = transforms.Compose([
    transforms.ToTensor(),
    CustomTransform(probability=0.3),
])
```

## 四、数据采样

### 4.1 随机采样

```python
from torch.utils.data import RandomSampler, SequentialSampler

# 随机采样
sampler = RandomSampler(dataset)
dataloader = DataLoader(dataset, sampler=sampler, batch_size=32)

# 顺序采样
sampler = SequentialSampler(dataset)
dataloader = DataLoader(dataset, sampler=sampler, batch_size=32)
```

### 4.2 加权采样（处理类别不平衡）

```python
from torch.utils.data import WeightedRandomSampler
import numpy as np

# 计算每个样本的权重
class_counts = np.array([100, 200, 50])  # 每类样本数
class_weights = 1.0 / class_counts  # 类别权重
sample_weights = [class_weights[label] for label in dataset.labels]

sampler = WeightedRandomSampler(
    weights=sample_weights,
    num_samples=len(dataset),  # 采样总数
    replacement=True,          # 是否放回采样
)

dataloader = DataLoader(dataset, sampler=sampler, batch_size=32)
```

### 4.3 分层采样

```python
from torch.utils.data import SubsetRandomSampler
from sklearn.model_selection import train_test_split

# 划分训练集和验证集
indices = list(range(len(dataset)))
train_idx, val_idx = train_test_split(
    indices, 
    test_size=0.2, 
    stratify=dataset.labels,  # 分层采样
    random_state=42
)

train_sampler = SubsetRandomSampler(train_idx)
val_sampler = SubsetRandomSampler(val_idx)

train_loader = DataLoader(dataset, sampler=train_sampler, batch_size=32)
val_loader = DataLoader(dataset, sampler=val_sampler, batch_size=32)
```

## 五、内置数据集

### 5.1 torchvision 数据集

```python
from torchvision import datasets

# MNIST
train_dataset = datasets.MNIST(
    root='./data',
    train=True,
    download=True,
    transform=transforms.ToTensor(),
)

# CIFAR-10
train_dataset = datasets.CIFAR10(
    root='./data',
    train=True,
    download=True,
    transform=transforms.ToTensor(),
)

# ImageNet（需要下载）
dataset = datasets.ImageNet(
    root='./data',
    split='train',
    transform=transforms.ToTensor(),
)

# ImageFolder（自定义图像数据集）
dataset = datasets.ImageFolder(
    root='./data/train',
    transform=transforms.ToTensor(),
)
# 目录结构应为：
# ./data/train/
#   ├── class1/
#   │   ├── img1.jpg
#   │   └── img2.jpg
#   └── class2/
#       ├── img3.jpg
#       └── img4.jpg
```

### 5.2 torchtext 数据集

```python
from torchtext.datasets import AG_NEWS, IMDB

# AG_NEWS 新闻分类
train_iter = AG_NEWS(split='train')

# IMDB 情感分析
train_iter = IMDB(split='train')
```

### 5.3 torchaudio 数据集

```python
from torchaudio.datasets import SPEECHCOMMANDS, LIBRISPEECH

# 语音命令数据集
dataset = SPEECHCOMMANDS(root='./data', download=True)
```

## 六、数据集划分

### 6.1 random_split

```python
from torch.utils.data import random_split

# 随机划分
train_size = int(0.8 * len(dataset))
val_size = int(0.1 * len(dataset))
test_size = len(dataset) - train_size - val_size

train_dataset, val_dataset, test_dataset = random_split(
    dataset,
    [train_size, val_size, test_size],
    generator=torch.Generator().manual_seed(42)  # 固定随机种子
)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32)
test_loader = DataLoader(test_dataset, batch_size=32)
```

### 6.2 手动划分

```python
from torch.utils.data import Subset

# 根据索引划分
train_dataset = Subset(dataset, train_indices)
val_dataset = Subset(dataset, val_indices)
test_dataset = Subset(dataset, test_indices)
```

## 七、多进程加载

### 7.1 num_workers 设置

```python
# num_workers = 0: 主进程加载（慢，但调试方便）
dataloader = DataLoader(dataset, batch_size=32, num_workers=0)

# num_workers > 0: 多进程加载（快，但需要注意）
dataloader = DataLoader(dataset, batch_size=32, num_workers=4)

# 经验法则：num_workers = 4 * GPU数量
dataloader = DataLoader(dataset, batch_size=32, num_workers=4)
```

### 7.2 注意事项

```python
# Windows 下多进程需要放在 if __name__ == '__main__': 中
if __name__ == '__main__':
    dataloader = DataLoader(dataset, batch_size=32, num_workers=4)
    for batch in dataloader:
        pass

# 多进程下的随机性
def worker_init_fn(worker_id):
    np.random.seed(torch.initial_seed() % (2**32))

dataloader = DataLoader(
    dataset,
    batch_size=32,
    num_workers=4,
    worker_init_fn=worker_init_fn,
)
```

## 八、内存优化

### 8.1 流式加载大数据集

```python
class StreamDataset(Dataset):
    """对于大数据集，不一次性加载到内存"""
    
    def __init__(self, file_list):
        self.file_list = file_list
    
    def __len__(self):
        return len(self.file_list)
    
    def __getitem__(self, idx):
        # 每次只加载一个文件
        data = self.load_file(self.file_list[idx])
        return data
    
    def load_file(self, file_path):
        # 实现文件加载逻辑
        with open(file_path, 'r') as f:
            data = f.read()
        return data
```

### 8.2 缓存机制

```python
from functools import lru_cache

class CachedDataset(Dataset):
    def __init__(self, data_paths):
        self.data_paths = data_paths
    
    def __len__(self):
        return len(self.data_paths)
    
    def __getitem__(self, idx):
        return self.load_data(idx)
    
    @lru_cache(maxsize=1000)  # 缓存最近的1000个样本
    def load_data(self, idx):
        # 加载逻辑
        return load_file(self.data_paths[idx])
```

## 九、完整示例

```python
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

class CustomDataset(Dataset):
    def __init__(self, data, labels, transform=None):
        self.data = data
        self.labels = labels
        self.transform = transform
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        sample = self.data[idx]
        label = self.labels[idx]
        
        if self.transform:
            sample = self.transform(sample)
        
        return sample, label

# 创建数据集
train_data = torch.randn(1000, 3, 32, 32)
train_labels = torch.randint(0, 10, (1000,))

train_dataset = CustomDataset(
    train_data, 
    train_labels,
    transform=transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
)

# 创建数据加载器
train_loader = DataLoader(
    train_dataset,
    batch_size=32,
    shuffle=True,
    num_workers=4,
    pin_memory=True,
)

# 训练循环
for epoch in range(10):
    for batch_idx, (data, labels) in enumerate(train_loader):
        # 训练代码
        pass
```

## 参考资源

- [[06-ai/pytorch/13-training-pipeline|13-training流程]] - 完整训练示例
- [PyTorch Dataset 文档](https://pytorch.org/docs/stable/data.html)
- [torchvision Transforms](https://pytorch.org/vision/stable/transforms.html)