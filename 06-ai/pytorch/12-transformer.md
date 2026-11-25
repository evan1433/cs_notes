# Transformer

Transformer 是一种基于注意力机制的架构，彻底改变了 NLP 和计算机视觉领域。它不使用循环结构，完全依赖注意力机制来建模序列依赖关系。

## 一、核心概念

### 1.1 为什么需要 Transformer？

传统模型的局限：
- **RNN/LSTM**：顺序计算，无法并行；长距离依赖问题
- **CNN**：局部感受野，难以捕获长距离依赖

Transformer 的优势：
- **并行计算**：所有位置同时计算
- **长距离依赖**：直接建模任意距离的关系
- **可扩展性**：易于扩展到大模型

### 1.2 架构概览

```
输入嵌入 → 位置编码 → Encoder(多层) → Decoder(多层) → 输出
                         ↓
                    多头注意力
                    前馈网络
                    层归一化
                    残差连接
```

### 1.3 自注意力机制（Self-Attention）

自注意力是 Transformer 的核心，让每个位置都能关注到序列中的所有位置。

```python
# 自注意力计算
# Q (Query), K (Key), V (Value)

Attention(Q, K, V) = softmax(Q @ K^T / sqrt(d_k)) @ V

# Q: 查询矩阵，shape: (batch, seq_len, d_k)
# K: 键矩阵，shape: (batch, seq_len, d_k)
# V: 值矩阵，shape: (batch, seq_len, d_v)
```

**直观理解：**
- Query：我在找什么
- Key：你有什么信息
- Value：你的内容是什么
- Attention：根据匹配程度加权聚合信息

## 二、PyTorch 实现

### 2.1 多头注意力（Multi-Head Attention）

```python
import torch
import torch.nn as nn
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, num_heads):
        super(MultiHeadAttention, self).__init__()
        assert d_model % num_heads == 0
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        # Q, K, V 的线性变换
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        
        # 输出线性变换
        self.W_o = nn.Linear(d_model, d_model)
    
    def forward(self, q, k, v, mask=None):
        batch_size = q.size(0)
        
        # 线性变换
        q = self.W_q(q)  # (batch, seq_len, d_model)
        k = self.W_k(k)
        v = self.W_v(v)
        
        # 分割成多头
        q = q.view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        k = k.view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        v = v.view(batch_size, -1, self.num_heads, self.d_k).transpose(1, 2)
        # shape: (batch, num_heads, seq_len, d_k)
        
        # 注意力分数
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)
        # shape: (batch, num_heads, seq_len, seq_len)
        
        # Mask（可选）
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        
        # Softmax
        attn_weights = torch.softmax(scores, dim=-1)
        
        # 加权求和
        output = torch.matmul(attn_weights, v)
        # shape: (batch, num_heads, seq_len, d_k)
        
        # 拼接多头
        output = output.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        
        # 输出变换
        output = self.W_o(output)
        
        return output, attn_weights

# 使用
mha = MultiHeadAttention(d_model=512, num_heads=8)
x = torch.randn(32, 100, 512)  # batch=32, seq_len=100, d_model=512
output, weights = mha(x, x, x)
print(output.shape)  # (32, 100, 512)
```

### 2.2 位置前馈网络（Position-wise Feed-Forward）

```python
class PositionwiseFeedForward(nn.Module):
    def __init__(self, d_model, d_ff, dropout=0.1):
        super(PositionwiseFeedForward, self).__init__()
        self.fc1 = nn.Linear(d_model, d_ff)
        self.fc2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x
```

### 2.3 位置编码（Positional Encoding）

```python
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000, dropout=0.1):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # 创建位置编码
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        # x: (batch, seq_len, d_model)
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

# 使用
pos_encoder = PositionalEncoding(d_model=512, dropout=0.1)
x = torch.randn(32, 100, 512)
x = pos_encoder(x)
```

### 2.4 Transformer Encoder Layer

```python
class TransformerEncoderLayer(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super(TransformerEncoderLayer, self).__init__()
        
        self.self_attn = MultiHeadAttention(d_model, num_heads)
        self.feed_forward = PositionwiseFeedForward(d_model, d_ff, dropout)
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
    
    def forward(self, x, mask=None):
        # 多头自注意力 + 残差连接 + LayerNorm
        attn_output, _ = self.self_attn(x, x, x, mask)
        x = self.norm1(x + self.dropout1(attn_output))
        
        # 前馈网络 + 残差连接 + LayerNorm
        ff_output = self.feed_forward(x)
        x = self.norm2(x + self.dropout2(ff_output))
        
        return x
```

### 2.5 完整 Transformer Encoder

```python
class TransformerEncoder(nn.Module):
    def __init__(self, vocab_size, d_model, num_heads, d_ff, num_layers, dropout=0.1):
        super(TransformerEncoder, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoding = PositionalEncoding(d_model, dropout=dropout)
        
        self.layers = nn.ModuleList([
            TransformerEncoderLayer(d_model, num_heads, d_ff, dropout)
            for _ in range(num_layers)
        ])
        
        self.norm = nn.LayerNorm(d_model)
    
    def forward(self, x, mask=None):
        # 嵌入 + 位置编码
        x = self.embedding(x)
        x = self.pos_encoding(x)
        
        # 多层 Transformer
        for layer in self.layers:
            x = layer(x, mask)
        
        x = self.norm(x)
        return x

# 使用
encoder = TransformerEncoder(
    vocab_size=10000,
    d_model=512,
    num_heads=8,
    d_ff=2048,
    num_layers=6
)
x = torch.randint(0, 10000, (32, 100))
output = encoder(x)
print(output.shape)  # (32, 100, 512)
```

## 三、实战示例

### 3.1 文本分类

```python
class TransformerClassifier(nn.Module):
    def __init__(self, vocab_size, d_model, num_heads, d_ff, num_layers, num_classes, dropout=0.1):
        super(TransformerClassifier, self).__init__()
        
        self.encoder = TransformerEncoder(
            vocab_size, d_model, num_heads, d_ff, num_layers, dropout
        )
        
        self.fc = nn.Linear(d_model, num_classes)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x, mask=None):
        # x: (batch, seq_len)
        output = self.encoder(x, mask)  # (batch, seq_len, d_model)
        
        # 使用 [CLS] token 或平均池化
        # output = output[:, 0, :]  # [CLS]
        output = output.mean(dim=1)  # 平均池化
        
        output = self.dropout(output)
        logits = self.fc(output)
        return logits

# 使用
model = TransformerClassifier(
    vocab_size=10000,
    d_model=256,
    num_heads=8,
    d_ff=512,
    num_layers=4,
    num_classes=2
)
x = torch.randint(0, 10000, (32, 100))
output = model(x)
print(output.shape)  # (32, 2)
```

### 3.2 序列标注

```python
class TransformerTagger(nn.Module):
    def __init__(self, vocab_size, d_model, num_heads, d_ff, num_layers, num_tags, dropout=0.1):
        super(TransformerTagger, self).__init__()
        
        self.encoder = TransformerEncoder(
            vocab_size, d_model, num_heads, d_ff, num_layers, dropout
        )
        
        self.fc = nn.Linear(d_model, num_tags)
    
    def forward(self, x, mask=None):
        output = self.encoder(x, mask)  # (batch, seq_len, d_model)
        logits = self.fc(output)         # (batch, seq_len, num_tags)
        return logits
```

### 3.3 使用 PyTorch 内置 Transformer

```python
import torch.nn as nn

# PyTorch 1.9+ 内置 Transformer
transformer = nn.Transformer(
    d_model=512,
    nhead=8,
    num_encoder_layers=6,
    num_decoder_layers=6,
    dim_feedforward=2048,
    dropout=0.1
)

# 输入：src 和 tgt
src = torch.rand(100, 32, 512)  # (seq_len, batch, d_model)
tgt = torch.rand(50, 32, 512)
output = transformer(src, tgt)  # (50, 32, 512)

# 或只使用 Encoder
encoder_layer = nn.TransformerEncoderLayer(d_model=512, nhead=8)
transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=6)
output = transformer_encoder(src)

# 或只使用 Decoder
decoder_layer = nn.TransformerDecoderLayer(d_model=512, nhead=8)
transformer_decoder = nn.TransformerDecoder(decoder_layer, num_layers=6)
output = transformer_decoder(tgt, src)
```

## 四、关键技巧

### 4.1 Mask 机制

```python
# Padding mask（忽略填充位置）
def create_padding_mask(seq, pad_idx=0):
    # seq: (batch, seq_len)
    mask = (seq != pad_idx).unsqueeze(1)  # (batch, 1, seq_len)
    return mask

# Look-ahead mask（解码器中防止看到未来信息）
def create_look_ahead_mask(seq_len):
    mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()
    return mask  # (seq_len, seq_len)

# 组合使用
def create_masks(src, tgt, pad_idx=0):
    # 编码器 mask
    src_mask = create_padding_mask(src, pad_idx)
    
    # 解码器 mask（padding + look-ahead）
    tgt_padding_mask = create_padding_mask(tgt, pad_idx)
    tgt_look_ahead_mask = create_look_ahead_mask(tgt.size(1))
    tgt_mask = tgt_padding_mask & tgt_look_ahead_mask
    
    return src_mask, tgt_mask
```

### 4.2 学习率预热（Warmup）

```python
import math

class WarmupLR:
    """Transformer 原论文的学习率调度"""
    def __init__(self, optimizer, d_model, warmup_steps):
        self.optimizer = optimizer
        self.d_model = d_model
        self.warmup_steps = warmup_steps
        self.steps = 0
    
    def step(self):
        self.steps += 1
        lr = self.d_model ** (-0.5) * min(
            self.steps ** (-0.5),
            self.steps * self.warmup_steps ** (-1.5)
        )
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = lr
        return lr

# 或使用 LambdaLR
def lr_lambda(step):
    d_model = 512
    warmup_steps = 4000
    return d_model ** (-0.5) * min(step ** (-0.5), step * warmup_steps ** (-1.5))

scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
```

### 4.3 Label Smoothing

```python
# PyTorch 1.10+ 内置
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

# 手动实现
class LabelSmoothingLoss(nn.Module):
    def __init__(self, classes, smoothing=0.1):
        super(LabelSmoothingLoss, self).__init__()
        self.confidence = 1.0 - smoothing
        self.smoothing = smoothing
        self.classes = classes
    
    def forward(self, pred, target):
        pred = pred.log_softmax(dim=-1)
        with torch.no_grad():
            true_dist = torch.zeros_like(pred)
            true_dist.fill_(self.smoothing / (self.classes - 1))
            true_dist.scatter_(1, target.unsqueeze(1), self.confidence)
        return torch.mean(torch.sum(-true_dist * pred, dim=-1))
```

## 五、Transformer 变体

### 5.1 BERT（仅 Encoder）

```python
# BERT 使用双向 Transformer Encoder
# 用于文本分类、命名实体识别等

class BERTModel(nn.Module):
    def __init__(self, vocab_size, d_model, num_heads, d_ff, num_layers, num_classes):
        super(BERTModel, self).__init__()
        
        self.encoder = TransformerEncoder(
            vocab_size, d_model, num_heads, d_ff, num_layers
        )
        
        # [CLS] token 分类
        self.classifier = nn.Linear(d_model, num_classes)
    
    def forward(self, x):
        output = self.encoder(x)
        cls_output = output[:, 0, :]  # [CLS] token
        logits = self.classifier(cls_output)
        return logits
```

### 5.2 GPT（仅 Decoder）

```python
# GPT 使用单向 Transformer Decoder
# 用于文本生成

class GPTModel(nn.Module):
    def __init__(self, vocab_size, d_model, num_heads, d_ff, num_layers):
        super(GPTModel, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoding = PositionalEncoding(d_model)
        
        decoder_layer = nn.TransformerDecoderLayer(d_model, num_heads, d_ff)
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers)
        
        self.fc_out = nn.Linear(d_model, vocab_size)
    
    def forward(self, x):
        # 使用 look-ahead mask
        mask = create_look_ahead_mask(x.size(1))
        
        embedded = self.embedding(x)
        embedded = self.pos_encoding(embedded)
        
        output = self.decoder(embedded, embedded, tgt_mask=mask)
        logits = self.fc_out(output)
        return logits
```

### 5.3 ViT（Vision Transformer）

```python
class VisionTransformer(nn.Module):
    def __init__(self, img_size=224, patch_size=16, d_model=768, num_heads=12, 
                 d_ff=3072, num_layers=12, num_classes=1000):
        super(VisionTransformer, self).__init__()
        
        self.patch_embed = nn.Conv2d(3, d_model, kernel_size=patch_size, stride=patch_size)
        num_patches = (img_size // patch_size) ** 2
        
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, d_model))
        
        encoder_layer = nn.TransformerEncoderLayer(d_model, num_heads, d_ff)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
        self.head = nn.Linear(d_model, num_classes)
    
    def forward(self, x):
        # x: (batch, 3, 224, 224)
        batch_size = x.size(0)
        
        # Patch embedding
        x = self.patch_embed(x)  # (batch, d_model, H/P, W/P)
        x = x.flatten(2).transpose(1, 2)  # (batch, num_patches, d_model)
        
        # Add [CLS] token
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        
        # Add position embedding
        x = x + self.pos_embed
        
        # Transformer encoder
        x = self.encoder(x)
        
        # Classification
        x = x[:, 0]  # [CLS] token
        x = self.head(x)
        return x
```

## 六、训练技巧

### 6.1 梯度裁剪

```python
# Transformer 容易梯度爆炸
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

### 6.2 初始化

```python
def init_weights(model):
    for p in model.parameters():
        if p.dim() > 1:
            nn.init.xavier_uniform_(p)
```

### 6.3 混合精度训练

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

for batch in train_loader:
    optimizer.zero_grad()
    
    with autocast():
        output = model(batch)
        loss = criterion(output, target)
    
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
```

## 七、Transformer vs 其他模型

| 特性 | RNN/LSTM | CNN | Transformer |
|------|----------|-----|-------------|
| **并行性** | 低 | 高 | 高 |
| **长距离依赖** | 弱 | 中 | 强 |
| **训练速度** | 慢 | 快 | 快 |
| **参数量** | 中 | 中 | 大 |
| **可解释性** | 低 | 中 | 高（注意力图） |

## 参考资源

- [[11-lstm]] - 循环神经网络
- [[07-activation-functions]] - GELU 等
- [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [The Annotated Transformer](https://nlp.seas.harvard.edu/2018/04/03/attention.html)
- [PyTorch Transformer 文档](https://pytorch.org/docs/stable/nn.html#transformer)