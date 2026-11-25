# LSTM（长短期记忆网络）

LSTM（Long Short-Term Memory）是一种特殊的 RNN，能够学习长期依赖关系，解决了传统 RNN 的梯度消失问题。

## 一、基本概念

### 1.1 为什么需要 LSTM？

传统 RNN 的问题：
- **梯度消失**：难以学习长期依赖
- **梯度爆炸**：训练不稳定
- **短期记忆**：只能记住最近的输入

LSTM 的解决方案：
- 引入**细胞状态（Cell State）**传递长期信息
- 使用**门控机制**控制信息流动

### 1.2 LSTM 结构

LSTM 包含三个门：
- **遗忘门（Forget Gate）**：决定丢弃哪些信息
- **输入门（Input Gate）**：决定存储哪些新信息
- **输出门（Output Gate）**：决定输出哪些信息

```
          ┌─────────────────────────────────┐
          │         LSTM Cell               │
          │                                 │
   h_t-1 ─┤  遗忘门    输入门    输出门    ├─ h_t
          │    f_t      i_t       o_t      │
          │                                 │
   c_t-1 ─┤         细胞状态 c_t           ├─ c_t
          └─────────────────────────────────┘
```

### 1.3 门控机制详解

```python
# LSTM 内部计算（简化版）
# 假设输入为 x_t，前一时刻隐藏状态为 h_{t-1}，细胞状态为 c_{t-1}

# 遗忘门：决定从细胞状态中丢弃什么
f_t = sigmoid(W_f · [h_{t-1}, x_t] + b_f)

# 输入门：决定要更新什么值
i_t = sigmoid(W_i · [h_{t-1}, x_t] + b_i)
c_tilde = tanh(W_c · [h_{t-1}, x_t] + b_c)

# 更新细胞状态
c_t = f_t * c_{t-1} + i_t * c_tilde

# 输出门：决定输出什么
o_t = sigmoid(W_o · [h_{t-1}, x_t] + b_o)
h_t = o_t * tanh(c_t)
```

## 二、PyTorch LSTM API

### 2.1 nn.LSTM 基本使用

```python
import torch
import torch.nn as nn

# 定义 LSTM
lstm = nn.LSTM(
    input_size=10,      # 输入特征维度
    hidden_size=20,     # 隐藏状态维度
    num_layers=2,       # LSTM 层数
    batch_first=True,   # 输入形状为 (batch, seq, feature)
    bidirectional=False,# 是否双向
    dropout=0.5         # 层间 dropout
)

# 输入数据
# shape: (seq_len, batch, input_size) 如果 batch_first=False
# shape: (batch, seq_len, input_size) 如果 batch_first=True
input_data = torch.randn(3, 5, 10)  # batch=3, seq_len=5, input_size=10

# 初始隐藏状态和细胞状态
# shape: (num_layers * num_directions, batch, hidden_size)
h0 = torch.randn(2, 3, 20)
c0 = torch.randn(2, 3, 20)

# 前向传播
output, (hn, cn) = lstm(input_data, (h0, c0))

# output: 所有时间步的最后层隐藏状态
# shape: (batch, seq_len, hidden_size * num_directions)
print(f"Output shape: {output.shape}")  # [3, 5, 20]

# hn, cn: 最后一个时间步的所有层隐藏状态和细胞状态
# shape: (num_layers * num_directions, batch, hidden_size)
print(f"Hidden state shape: {hn.shape}")  # [2, 3, 20]
print(f"Cell state shape: {cn.shape}")    # [2, 3, 20]
```

### 2.2 参数详解

```python
lstm = nn.LSTM(
    input_size=10,        # 输入特征维度 x_t 的维度
    hidden_size=20,       # 隐藏状态维度 h_t 的维度
    num_layers=2,         # LSTM 层数，堆叠多个 LSTM
    bias=True,            # 是否使用偏置
    batch_first=True,     # 输入形状：True为(batch, seq, feature)
    dropout=0.5,          # 除最后一层外，每层的 dropout
    bidirectional=False,  # 是否双向 LSTM
    proj_size=0,          # 投影维度（用于减少计算量）
)
```

### 2.3 输出含义

```python
output, (hn, cn) = lstm(input_data)

# output: 所有时间步的输出
# - 用于序列标注任务（如 NER、词性标注）
# - shape: (batch, seq_len, hidden_size * num_directions)

# hn: 最后时刻所有层的隐藏状态
# - 用于序列分类任务
# - shape: (num_layers * num_directions, batch, hidden_size)

# cn: 最后时刻所有层的细胞状态
# - 用于继续处理下一个序列
# - shape: (num_layers * num_directions, batch, hidden_size)
```

## 三、实战示例

### 3.1 序列分类任务

```python
import torch
import torch.nn as nn

class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_size, num_classes, num_layers=2):
        super(LSTMClassifier, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.5,
            bidirectional=True  # 双向 LSTM
        )
        self.fc = nn.Linear(hidden_size * 2, num_classes)  # *2 因为双向
        self.dropout = nn.Dropout(0.5)
    
    def forward(self, x):
        # x: (batch, seq_len)
        embedded = self.embedding(x)  # (batch, seq_len, embed_dim)
        
        # LSTM
        output, (hn, cn) = self.lstm(embedded)
        
        # 使用最后时刻的隐藏状态
        # hn shape: (num_layers * num_directions, batch, hidden_size)
        # 取最后一层的两个方向的隐藏状态
        hn_forward = hn[-2]  # 前向最后一层
        hn_backward = hn[-1]  # 反向最后一层
        hn_concat = torch.cat((hn_forward, hn_backward), dim=1)
        
        # 或使用 output 的最后一个时间步
        # hn_concat = output[:, -1, :]
        
        hn_concat = self.dropout(hn_concat)
        out = self.fc(hn_concat)
        return out

# 使用
model = LSTMClassifier(vocab_size=10000, embed_dim=128, hidden_size=256, num_classes=2)
x = torch.randint(0, 10000, (32, 100))  # batch=32, seq_len=100
output = model(x)  # (32, 2)
```

### 3.2 序列标注任务

```python
class LSTMTagger(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_size, num_tags, num_layers=2):
        super(LSTMTagger, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Linear(hidden_size * 2, num_tags)
    
    def forward(self, x):
        embedded = self.embedding(x)
        output, _ = self.lstm(embedded)  # output: (batch, seq_len, hidden_size*2)
        logits = self.fc(output)          # (batch, seq_len, num_tags)
        return logits

# 使用
model = LSTMTagger(vocab_size=10000, embed_dim=128, hidden_size=256, num_tags=10)
x = torch.randint(0, 10000, (32, 100))
output = model(x)  # (32, 100, 10)
```

### 3.3 文本生成

```python
class LSTMGenerator(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_size, num_layers=2):
        super(LSTMGenerator, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(embed_dim, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, vocab_size)
        self.hidden_size = hidden_size
        self.num_layers = num_layers
    
    def forward(self, x, hidden=None):
        embedded = self.embedding(x)
        output, hidden = self.lstm(embedded, hidden)
        logits = self.fc(output)
        return logits, hidden
    
    def init_hidden(self, batch_size, device):
        """初始化隐藏状态"""
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(device)
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(device)
        return (h0, c0)
    
    def generate(self, start_token, max_length=100, temperature=1.0):
        """生成文本"""
        self.eval()
        device = next(self.parameters()).device
        hidden = self.init_hidden(1, device)
        
        generated = [start_token]
        current_token = torch.tensor([[start_token]]).to(device)
        
        with torch.no_grad():
            for _ in range(max_length):
                logits, hidden = self(current_token, hidden)
                logits = logits[0, -1, :] / temperature
                probs = torch.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1).item()
                generated.append(next_token)
                current_token = torch.tensor([[next_token]]).to(device)
                
                if next_token == 2:  # 假设 2 是 <EOS>
                    break
        
        return generated

# 使用
model = LSTMGenerator(vocab_size=10000, embed_dim=128, hidden_size=256)
generated_tokens = model.generate(start_token=1, max_length=50)
```

## 四、变体与技巧

### 4.1 双向 LSTM

```python
# 双向 LSTM 同时考虑过去和未来的信息
lstm = nn.LSTM(
    input_size=embed_dim,
    hidden_size=hidden_size,
    bidirectional=True
)

# 输出维度变为 hidden_size * 2
# forward 和 backward 的隐藏状态会拼接在一起
```

### 4.2 多层 LSTM

```python
# 多层 LSTM 提取更高层次的特征
lstm = nn.LSTM(
    input_size=embed_dim,
    hidden_size=hidden_size,
    num_layers=3,  # 3层 LSTM
    dropout=0.3    # 层间 dropout
)
```

### 4.3 Pack Padded Sequence

处理变长序列，提高效率：

```python
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

# 假设有序列长度信息
sequences = torch.randn(10, 20, 128)  # batch=10, seq_len=20, embed_dim=128
lengths = torch.tensor([20, 18, 15, 12, 10, 8, 6, 4, 2, 1])  # 每个序列的实际长度

# 打包
packed = pack_padded_sequence(sequences, lengths.cpu(), batch_first=True, enforce_sorted=False)

# 通过 LSTM
lstm = nn.LSTM(128, 256, batch_first=True)
output_packed, (hn, cn) = lstm(packed)

# 解包
output, _ = pad_packed_sequence(output_packed, batch_first=True)

# output shape: (10, 20, 256)，但填充位置的值为 0
```

### 4.4 Attention 机制

```python
class LSTMWithAttention(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_size, num_classes):
        super(LSTMWithAttention, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(embed_dim, hidden_size, batch_first=True, bidirectional=True)
        self.attention = nn.Linear(hidden_size * 2, 1)
        self.fc = nn.Linear(hidden_size * 2, num_classes)
    
    def forward(self, x):
        embedded = self.embedding(x)  # (batch, seq_len, embed_dim)
        output, _ = self.lstm(embedded)  # (batch, seq_len, hidden_size*2)
        
        # Attention weights
        attn_weights = torch.softmax(self.attention(output), dim=1)  # (batch, seq_len, 1)
        
        # Context vector
        context = torch.sum(attn_weights * output, dim=1)  # (batch, hidden_size*2)
        
        out = self.fc(context)
        return out
```

## 五、LSTM vs GRU vs RNN

| 特性 | RNN | LSTM | GRU |
|------|-----|------|-----|
| **门控** | 无 | 3个门 | 2个门 |
| **参数量** | 少 | 多 | 中等 |
| **计算速度** | 快 | 慢 | 中等 |
| **长程依赖** | 差 | 好 | 好 |
| **训练难度** | 难 | 中等 | 容易 |

```python
# GRU 示例
gru = nn.GRU(input_size=128, hidden_size=256, num_layers=2, batch_first=True)
output, hn = gru(input_data)  # GRU 只有 hn，没有 cn
```

## 六、常见问题

### 6.1 梯度消失/爆炸

```python
# 解决方法：
# 1. 梯度裁剪
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)

# 2. 合适的初始化
for name, param in model.named_parameters():
    if 'weight_ih' in name:
        nn.init.xavier_uniform_(param.data)
    elif 'weight_hh' in name:
        nn.init.orthogonal_(param.data)
    elif 'bias' in name:
        param.data.fill_(0)
        # LSTM 特殊：设置遗忘门偏置为 1
        n = param.size(0)
        param.data[n//4:n//2].fill_(1)

# 3. Layer Normalization
lstm = nn.LSTM(input_size, hidden_size)
ln = nn.LayerNorm(hidden_size)
```

### 6.2 训练速度慢

```python
# 解决方法：
# 1. 使用 pack_padded_sequence
# 2. 减少 num_layers
# 3. 使用较小的 hidden_size
# 4. 使用 GPU
model = model.to('cuda')

# 5. 考虑使用 GRU 替代 LSTM
gru = nn.GRU(input_size, hidden_size, num_layers)
```

### 6.3 处理长序列

```python
# 解决方法：
# 1. Truncated BPTT（截断反向传播）
seq_len = 100
chunk_size = 20

for i in range(0, seq_len, chunk_size):
    chunk = x[:, i:i+chunk_size, :]
    output, hidden = lstm(chunk, hidden)
    loss = criterion(output, target[:, i:i+chunk_size])
    loss.backward()

# 2. 使用 Attention 机制
# 3. 使用 Transformer
```

## 七、最佳实践

### 7.1 超参数选择

```python
# 常用配置
hidden_size = 256      # 通常 128-512
num_layers = 2         # 通常 1-3 层
dropout = 0.3          # 0.2-0.5
learning_rate = 0.001  # Adam

# 序列长度
max_seq_len = 100      # 根据任务调整
```

### 7.2 训练技巧

```python
# 1. 使用 teacher forcing（训练时）
teacher_forcing_ratio = 0.5

def train(input, target, model):
    use_teacher_forcing = random.random() < teacher_forcing_ratio
    
    if use_teacher_forcing:
        # 使用真实目标作为下一时刻输入
        output, hidden = model(target)
    else:
        # 使用模型输出作为下一时刻输入
        output, hidden = model(input)
```

## 参考资源

- [[10-mlp]] - 基础神经网络
- [[12-transformer]] - 注意力机制
- [PyTorch LSTM 文档](https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html)
- [Understanding LSTM Networks](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)