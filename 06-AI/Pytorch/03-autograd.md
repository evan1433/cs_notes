# PyTorch 自动求导（Autograd）

自动求导是 PyTorch 的核心功能，能够自动计算张量的梯度，是反向传播算法的基础。

## 一、基本概念

### 1.1 计算图

PyTorch 使用**动态计算图（Dynamic Computation Graph）**来跟踪张量运算：

```python
import torch

x = torch.tensor([2.0], requires_grad=True)
y = x * 3
z = y ** 2

print(z.grad_fn)  # <PowBackward0 object>
print(y.grad_fn)  # <MulBackward0 object>
```

计算图结构：
```
x (requires_grad=True)
  ↓ (*3)
y
  ↓ (**2)
z
```

### 1.2 requires_grad

只有设置了 `requires_grad=True` 的张量才会跟踪梯度：

```python
# 创建时指定
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)

# 后续修改
x = torch.tensor([1.0, 2.0, 3.0])
x.requires_grad = True
# 或
x.requires_grad_(True)

# 查看是否需要梯度
print(x.requires_grad)  # True
```

### 1.3 梯度计算

```python
x = torch.tensor([2.0], requires_grad=True)
y = x ** 2 + 2 * x + 1

# 反向传播
y.backward()

# 查看梯度 (dy/dx = 2x + 2 = 2*2 + 2 = 6)
print(x.grad)  # tensor([6.])
```

## 二、backward() 详解

### 2.1 标量输出

```python
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
y = x.sum()

y.backward()
print(x.grad)  # tensor([1., 1., 1.])
```

### 2.2 向量输出 - 需要传入梯度权重

```python
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
y = x * 2  # y = [2, 4, 6]

# 错误：y 不是标量
# y.backward()  # RuntimeError

# 正确：传入梯度权重向量
y.backward(torch.tensor([1.0, 1.0, 1.0]))
print(x.grad)  # tensor([2., 2., 2.])

# 也可以传入不同的权重
x.grad.zero_()  # 清零梯度
y = x * 2
y.backward(torch.tensor([1.0, 0.5, 0.1]))
print(x.grad)  # tensor([2.0, 1.0, 0.2])
```

### 2.3 retain_graph

```python
x = torch.tensor([2.0], requires_grad=True)
y = x ** 2
z = y ** 2

# 第一次反向传播后，计算图会被释放
z.backward()
print(x.grad)  # tensor([32.])

# 如果需要再次反向传播，需要设置 retain_graph=True
x.grad.zero_()
y = x ** 2
z = y ** 2
z.backward(retain_graph=True)  # 保留计算图
z.backward()  # 可以再次调用
```

## 三、梯度控制

### 3.1 torch.no_grad()

在不需要梯度的代码块中使用，可以节省内存：

```python
x = torch.tensor([2.0], requires_grad=True)

# 不跟踪梯度
with torch.no_grad():
    y = x * 2
    print(y.requires_grad)  # False

# 测试模型时常用
model.eval()
with torch.no_grad():
    outputs = model(inputs)
```

### 3.2 detach()

从计算图中分离张量：

```python
x = torch.tensor([2.0], requires_grad=True)
y = x ** 2

# detach 创建新张量，不需要梯度
z = y.detach()
print(z.requires_grad)  # False

# z 不参与反向传播
z1 = z * 2
# z1.backward()  # 错误：没有梯度

# y 仍然可以反向传播
y.backward()
print(x.grad)  # tensor([4.])
```

### 3.3 梯度清零

```python
x = torch.tensor([1.0], requires_grad=True)

# 第一次反向传播
y = x ** 2
y.backward()
print(x.grad)  # tensor([2.])

# 第二次反向传播（梯度会累加！）
z = x ** 3
z.backward()
print(x.grad)  # tensor([5.]) = 2 + 3，累加了！

# 正确做法：清零梯度
x.grad.zero_()
z = x ** 3
z.backward()
print(x.grad)  # tensor([3.])
```

**在训练循环中：**
```python
for epoch in range(epochs):
    optimizer.zero_grad()      # 清零梯度
    outputs = model(inputs)
    loss = criterion(outputs, labels)
    loss.backward()            # 反向传播
    optimizer.step()           # 更新参数
```

## 四、梯度累积

### 4.1 为什么梯度会累积？

PyTorch 默认会在多次 `backward()` 时累积梯度：

```python
x = torch.tensor([1.0], requires_grad=True)

# 三次反向传播
for _ in range(3):
    y = x ** 2
    y.backward()

print(x.grad)  # tensor([6.]) = 2 + 2 + 2
```

### 4.2 利用梯度累积模拟大 batch

当显存不足时，可以用梯度累积模拟更大的 batch：

```python
batch_size = 32
accumulation_steps = 4
effective_batch = batch_size * accumulation_steps

model.train()
optimizer.zero_grad()

for i, (inputs, labels) in enumerate(dataloader):
    outputs = model(inputs)
    loss = criterion(outputs, labels)
    
    # 归一化损失
    loss = loss / accumulation_steps
    loss.backward()
    
    # 累积 accumulation_steps 步后更新
    if (i + 1) % accumulation_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

## 五、计算图细节

### 5.1 grad_fn 属性

每个张量的 `grad_fn` 记录了创建它的函数：

```python
x = torch.tensor([2.0], requires_grad=True)
y = x * 3
z = y + 2
w = z ** 2

print(x.grad_fn)  # None（叶子节点）
print(y.grad_fn)   # <MulBackward0>
print(z.grad_fn)   # <AddBackward0>
print(w.grad_fn)   # <PowBackward0>
```

### 5.2 叶子节点

叶子节点是计算图的起点，通常是我们创建的张量：

```python
x = torch.tensor([1.0], requires_grad=True)
y = torch.tensor([2.0], requires_grad=True)
z = x * y

print(x.is_leaf)  # True
print(y.is_leaf)  # True
print(z.is_leaf)  # False

# 只有叶子节点的梯度会被保留
z.backward()
print(x.grad)  # tensor([2.])
print(y.grad)  # tensor([1.])
# z.grad 为 None（非叶子节点）
```

### 5.3 retain_grad()

如果想保留非叶子节点的梯度：

```python
x = torch.tensor([1.0], requires_grad=True)
y = x ** 2

y.retain_grad()  # 保留 y 的梯度

z = y ** 2
z.backward()

print(x.grad)  # tensor([4.])
print(y.grad)  # tensor([4.])
```

## 六、高级操作

### 6.1 torch.autograd.grad()

手动计算梯度：

```python
x = torch.tensor([2.0], requires_grad=True)
y = x ** 2
z = y * 3

# 直接计算梯度，不保存到 grad 属性
grad_x = torch.autograd.grad(z, x)[0]
print(grad_x)  # tensor([12.])

# x.grad 仍为 None
print(x.grad)  # None
```

### 6.2 计算高阶导数

```python
x = torch.tensor([2.0], requires_grad=True)
y = x ** 3

# 一阶导数
grad1 = torch.autograd.grad(y, x, create_graph=True)[0]
print(grad1)  # tensor([12.])

# 二阶导数
grad2 = torch.autograd.grad(grad1, x)[0]
print(grad2)  # tensor([12.]) = 6x
```

### 6.3 雅可比矩阵和海森矩阵

```python
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
y = x ** 2

# 计算雅可比矩阵
jacobian = torch.autograd.functional.jacobian(lambda x: x ** 2, x)
print(jacobian)
# tensor([[2., 0., 0.],
#         [0., 4., 0.],
#         [0., 0., 6.]])

# 计算海森矩阵
hessian = torch.autograd.functional.hessian(lambda x: (x ** 2).sum(), x)
print(hessian)
# tensor([[2., 0., 0.],
#         [0., 2., 0.],
#         [0., 0., 2.]])
```

## 七、常见问题

### 7.1 in-place 操作

```python
x = torch.tensor([1.0], requires_grad=True)

# 错误：in-place 操作会破坏计算图
# x += 1  # RuntimeError

# 正确：使用非 in-place 操作
x = x + 1

# 或使用 in-place 操作前检查
x.data += 1  # 不推荐，可能导致梯度计算错误
```

### 7.2 张量 vs 标量

```python
x = torch.tensor([1.0, 2.0], requires_grad=True)
y = x * 2

# 错误：y 不是标量
# y.backward()

# 正确方法1：求和变成标量
y.sum().backward()

# 正确方法2：传入梯度向量
x.grad.zero_()
y = x * 2
y.backward(torch.tensor([1.0, 1.0]))
```

### 7.3 requires_grad 的传播

```python
x = torch.tensor([1.0], requires_grad=True)
y = torch.tensor([2.0])  # 不需要梯度

z = x + y
print(z.requires_grad)  # True，继承自 x

# 两个都不需要梯度
x = torch.tensor([1.0])
y = torch.tensor([2.0])
z = x + y
print(z.requires_grad)  # False
```

### 7.4 GPU 上的梯度

```python
# GPU 张量
x = torch.tensor([1.0], requires_grad=True, device='cuda')
y = x ** 2
y.backward()

print(x.grad)  # 梯度在同一个设备上
print(x.grad.device)  # cuda:0
```

## 八、调试技巧

### 8.1 检查梯度

```python
# 检查梯度是否为 None
for name, param in model.named_parameters():
    if param.grad is None:
        print(f"{name} has no gradient")

# 检查梯度是否过小/过大
for name, param in model.named_parameters():
    if param.grad is not None:
        grad_norm = param.grad.norm().item()
        print(f"{name}: grad_norm = {grad_norm}")
```

### 8.2 梯度裁剪

防止梯度爆炸：

```python
# 方法1：按值裁剪
torch.nn.utils.clip_grad_value_(model.parameters(), clip_value=0.5)

# 方法2：按范数裁剪
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

# 在训练中使用
optimizer.zero_grad()
loss.backward()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```

### 8.3 梯度钩子

```python
x = torch.tensor([1.0], requires_grad=True)

def grad_hook(grad):
    print(f"梯度: {grad}")
    return grad * 2  # 可以修改梯度

# 注册钩子
handle = x.register_hook(grad_hook)

y = x ** 2
y.backward()
# 输出: 梯度: tensor([2.])
print(x.grad)  # tensor([4.]) = 2 * 2

# 移除钩子
handle.remove()
```

## 九、实际应用

### 9.1 手动实现反向传播

```python
# 简单的线性回归
w = torch.tensor([0.0], requires_grad=True)
b = torch.tensor([0.0], requires_grad=True)

x_data = torch.tensor([1.0, 2.0, 3.0])
y_data = torch.tensor([2.0, 4.0, 6.0])

lr = 0.1

for epoch in range(100):
    # 前向传播
    y_pred = w * x_data + b
    loss = ((y_pred - y_data) ** 2).mean()
    
    # 反向传播
    loss.backward()
    
    # 手动更新参数
    with torch.no_grad():
        w -= lr * w.grad
        b -= lr * b.grad
    
    # 清零梯度
    w.grad.zero_()
    b.grad.zero_()
    
    if epoch % 20 == 0:
        print(f"Epoch {epoch}: loss = {loss.item():.4f}, w = {w.item():.2f}, b = {b.item():.2f}")

print(f"最终: w = {w.item():.2f}, b = {b.item():.2f}")
```

### 9.2 使用优化器

```python
import torch.nn as nn
import torch.optim as optim

model = nn.Linear(1, 1)
optimizer = optim.SGD(model.parameters(), lr=0.01)
criterion = nn.MSELoss()

for epoch in range(100):
    optimizer.zero_grad()      # 清零梯度
    outputs = model(inputs)    # 前向传播
    loss = criterion(outputs, labels)  # 计算损失
    loss.backward()            # 反向传播
    optimizer.step()           # 更新参数
```

## 参考资源

- [[02-tensor-operations]] - 张量基础操作
- [[09-optimizers]] - 参数优化
- [PyTorch 自动求导官方文档](https://pytorch.org/docs/stable/autograd.html)