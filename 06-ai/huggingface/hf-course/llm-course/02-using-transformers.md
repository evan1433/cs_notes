# [本章简介](https://huggingface.co/learn/llm-course/zh-CN/chapter2/1)

🤗 Transformers 库应运而生，就是为了解决这个问题。它的目标是提供一个统一的 API 接口，通过它可以加载、训练和保存任何 Transformer 模型。该库的主要特点有：

- **易于使用**：仅需两行代码，就能下载、加载并使用先进的 NLP 模型进行推理。
- **灵活**：在本质上，所有的模型都是简单的 PyTorch nn.Module 或 TensorFlow tf.keras.Model 类，并可像在各自的机器学习（ML）框架中处理其他模型一样处理它们。
- **简单**：该库几乎没有进行任何抽象化。🤗 Transformers 库一个核心概念是“全在一个文件中”：模型的前向传播完全在一个文件中定义，这使得代码本身易于理解和修改。

# 管道的内部

![](https://huggingface.co/datasets/huggingface-course/documentation-images/resolve/main/en/chapter2/full_nlp_pipeline.svg)

## 使用 tokenizer（ tokenizer ）进行预处理

与其他神经网络一样，Transformer 模型无法直接处理原始文本，因此我们管道的第一步是将文本输入转换为模型能够理解的数字。为此，我们使用 tokenizer（ tokenizer ），它将负责：

- 将输入拆分为单词、子单词或符号（如标点符号），称为 **token**（标记）
- 将每个标记（token）映射到一个数字，称为 **input ID**（inputs ID）
- 添加模型需要的其他输入，例如特殊标记（如 `[CLS]` 和 `[SEP]` ）
	- 位置编码：指示每个标记在句子中的位置。
	- 段落标记：区分不同段落的文本。
	- 特殊标记：例如 [CLS] 和 [SEP] 标记，用于标识句子的开头和结尾。

## 探索模型
### 高维向量
Transformers 模块的矢量输出通常较大。它通常有三个维度：
- **Batch size**（批次大小）：一次处理的序列数（在我们的示例中为 2）。
- **Sequence length**（序列长度）：表示序列（句子）的长度（在我们的示例中为 16）。
- **Hidden size**（隐藏层大小）：每个模型输入的向量维度。

### 模型头：理解数字的意义
## 对输出进行后序处理

# [模型](https://huggingface.co/learn/llm-course/zh-CN/chapter2/3)

## 创建 Transformer 模型

初始化 BERT 模型需要做的第一件事是加载 `Config` 对象：
```python
from transformers import BertConfig, BertModel

# 初始化 Config 类
config = BertConfig()

# 从 Config 类初始化模型
model = BertModel(config)
```
### 使用不同的加载方式
使用默认配置创建模型会使用随机值对其进行初始化：

```python
from transformers import BertConfig, BertModel

config = BertConfig()
model = BertModel(config)

# 模型已随机初始化!
```

这个模型是可以运行并得到结果的，但它会输出胡言乱语；它需要先进行训练才能正常使用。我们可以根据手头的任务从头开始训练模型，但正如你在 [第一章](https://huggingface.co/course/chapter1) 中看到的，这将需要很长的时间和大量的数据，并且产生的碳足迹会对环境产生不可忽视的影响。为了避免不必要的重复工作，能够共享和复用已经训练过的模型是非常重要的。

加载已经训练过的 Transformers 模型很简单——我们可以使用 `from_pretrained()` 方法：

```python
from transformers import BertModel

model = BertModel.from_pretrained("bert-base-cased")
```

现在，此模型已经用 checkpoint 的所有权重进行了初始化。它可以直接用于推理它训练过的任务，也可以在新任务上进行微调。通过使用预训练的权重进行训练，相比于从头开始训练，我们可以迅速获得比较好的结果。

权重已下载并缓存在缓存文件夹中（因此，未来调用 `from_pretrained()` 方法的调用将不会重新下载它们）默认为 `~/.cache/huggingface/transformers` 。你可以通过设置 `HF_HOME` 环境变量来自定义缓存文件夹。

加载模型的标识符可以是 Model Hub 上任何模型的标签，只要它与 BERT 架构兼容。可用的 BERT checkpoint 的完整列表可以在 [这里](https://huggingface.co/models?filter=bert) 找到。

### 保存模型

```python
model.save_pretrained("directory_on_my_computer")
```
### 使用Transformer模型进行推理
### 使用张量作为模型的输入

# [标记器（Tokenizer）](https://huggingface.co/learn/llm-course/zh-CN/chapter2/4)

## 基于单词（Word-based）的 tokenization

## 基于字符（Character-based）的 tokenization

## 基于子词（subword）的 tokenization

### 还有更多！
- Byte-level BPE，用于 GPT-2
- WordPiece，用于 BERT
- SentencePiece or Unigram，用于多个多语言模型

## 加载和保存
```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
```

```python
tokenizer.save_pretrained("directory_on_my_computer")
```

## 编码
将文本翻译成数字被称为编码（encoding）。编码分两步完成：分词，然后转换为 inputs ID。
### tokenization
### 从tokens到inputs ID
## 解码
解码（Decoding） 正好相反：从 inputs ID 到一个字符串。这以通过 `decode()` 方法实现：

```python
decoded_string = tokenizer.decode([7993, 170, 11303, 1200, 2443, 1110, 3014])
print(decoded_string)
```
# [处理多个序列](https://huggingface.co/learn/llm-course/zh-CN/chapter2/5)

## 模型需要一批输入

## 填充输入（Padding）

## 注意力掩码（attention mask）层
注意力掩码（attention mask）是与 inputs ID 张量形状完全相同的张量，用 0 和 1 填充：1 表示应关注相应的 tokens，0 表示应忽略相应的 tokens（即，它们应被模型的注意力层忽视）。

## 更长的句子
对于 Transformers 模型，我们可以通过模型的序列长度是有限的。大多数模型处理多达 512 或 1024 个 的 tokens 序列，当使用模型处理更长的序列时，会崩溃。此问题有两种解决方案：

- 使用支持更长序列长度的模型。
- 截断你的序列。

不同的模型支持的序列长度各不相同，有些模型专门用于处理非常长的序列。例如 [Longformer](https://huggingface.co/transformers/model_doc/longformer) 和 [LED](https://huggingface.co/transformers/model_doc/led) 。如果你正在处理需要非常长序列的任务，我们建议你考虑使用这些模型。

另外，我们建议你通过设定 `max_sequence_length` 参数来截断序列：

```python
sequence = sequence[:max_sequence_length]
```


# 把他们放在一起

## 综合应用

正如我们将在下面的一些例子中看到的，这个函数非常强大。首先，它可以对单个句子进行处理：

```python
sequence = "I've been waiting for a HuggingFace course my whole life."

model_inputs = tokenizer(sequence)
```

它还一次处理多个多个，并且 API 的用法完全一致：

```python
sequences = ["I've been waiting for a HuggingFace course my whole life.", "So have I!"]

model_inputs = tokenizer(sequences)
```

它可以使用多种不同的方法对目标进行填充：
```python
# 将句子序列填充到最长句子的长度
model_inputs = tokenizer(sequences, padding="longest")

# 将句子序列填充到模型的最大长度
# (512 for BERT or DistilBERT)
model_inputs = tokenizer(sequences, padding="max_length")

# 将句子序列填充到指定的最大长度
model_inputs = tokenizer(sequences, padding="max_length", max_length=8)
```

它还可以对序列进行截断：
```python
sequences = ["I've been waiting for a HuggingFace course my whole life.", "So have I!"]

# 将截断比模型最大长度长的句子序列
# (512 for BERT or DistilBERT)
model_inputs = tokenizer(sequences, truncation=True)

# 将截断长于指定最大长度的句子序列
model_inputs = tokenizer(sequences, max_length=8, truncation=True)
```

`tokenizer` 对象可以处理指定框架张量的转换，然后可以直接发送到模型。例如，在下面的代码示例中，我们告诉 tokenizer 返回不同框架的张量 —— `"pt"` 返回 PyTorch 张量， `"tf"` 返回 TensorFlow 张量，而 `"np"` 则返回 NumPy 数组：

```python
sequences = ["I've been waiting for a HuggingFace course my whole life.", "So have I!"]

# 返回 PyTorch tensors
model_inputs = tokenizer(sequences, padding=True, return_tensors="pt")

# 返回 TensorFlow tensors
model_inputs = tokenizer(sequences, padding=True, return_tensors="tf")

# 返回 NumPy arrays
model_inputs = tokenizer(sequences, padding=True, return_tensors="np")
```


## [特殊的 tokens](https://huggingface.co/learn/llm-course/zh-CN/chapter2/6#%E7%89%B9%E6%AE%8A%E7%9A%84%20tokens)

如果我们看一下 tokenizer 返回的 inputs ID，我们会发现它们与之前的略有不同：

```python
sequence = "I've been waiting for a HuggingFace course my whole life."

model_inputs = tokenizer(sequence)
print(model_inputs["input_ids"])

tokens = tokenizer.tokenize(sequence)
ids = tokenizer.convert_tokens_to_ids(tokens)
print(ids)
```


```shell
[101, 1045, 1005, 2310, 2042, 3403, 2005, 1037, 17662, 12172, 2607, 2026, 2878, 2166, 1012, 102]
[1045, 1005, 2310, 2042, 3403, 2005, 1037, 17662, 12172, 2607, 2026, 2878, 2166, 1012]
```


句子的开始和结束分别增加了一个 inputs ID。我们来解码上述的两个 ID 序列，看看是怎么回事：

```
print(tokenizer.decode(model_inputs["input_ids"]))
print(tokenizer.decode(ids))
```


```
"[CLS] i've been waiting for a huggingface course my whole life. [SEP]"
"i've been waiting for a huggingface course my whole life."
```

tokenizer 在开头添加了特殊单词 `[CLS]` ，在结尾添加了特殊单词 `[SEP]` 。这是因为模型在预训练时使用了这些字词，所以为了得到相同的推断结果，我们也需要添加它们。请注意，有些模型不添加特殊单词，或者添加不同的特殊单词；模型也可能只在开头或结尾添加这些特殊单词。无论如何，tokenizer 知道哪些是必需的，并会为你处理这些问题。

## [小结：从 tokenizer 到模型](https://huggingface.co/learn/llm-course/zh-CN/chapter2/6#%E5%B0%8F%E7%BB%93%EF%BC%9A%E4%BB%8E%20tokenizer%20%E5%88%B0%E6%A8%A1%E5%9E%8B)

现在我们已经看到 `tokenizer` 对象在处理文本时的所有步骤，让我们最后再看一次它如何通过 tokenizer API 处理多个序列（填充！），非常长的序列（截断！）以及多种类型的张量：

```python

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSequenceClassification.from_pretrained(checkpoint)
sequences = ["I've been waiting for a HuggingFace course my whole life.", "So have I!"]

tokens = tokenizer(sequences, padding=True, truncation=True, return_tensors="pt")
output = model(**tokens)

```

# 基本用法完成

- 学习了 Transformers 模型的基本构造块。    
- 了解了 Tokenizer 管道的组成。
- 了解了如何在实践中使用 Transformers 模型。
- 学习了如何利用 tokenizer 将文本转换为模型可以理解的张量。
- 设定了 tokenizer 和模型，可以从输入的文本获取预测的结果。
- 了解了 inputs IDs 的局限性，并学习了关于注意力掩码（attention mask）的知识。
- 试用了灵活且可配置的 Tokenizer 方法。