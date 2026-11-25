# 本章简介
- 如何从模型中心（hub）加载大型数据集
- 如何使用高级的 `Trainer` API 微调一个模型
- 如何使用自定义训练过程
- 如何利用🤗 Accelerate 库在所有分布式设备上轻松运行自定义训练过程

# [预处理数据](https://huggingface.co/learn/llm-course/zh-CN/chapter3/2)

## 处理数据


## 从模型中心（hub）加载数据集
模型中心（hub）不仅仅包含模型，还有许多别的语言的数据集。访问 [Datasets](https://huggingface.co/datasets) 的链接即可进行浏览。我们建议你在完成本节的学习后阅读一下 [加载和处理新的数据集](https://huggingface.co/docs/datasets/loading) 这篇文章，这会让你对 huggingface 的数据集理解更加清晰。
现在让我们使用 MRPC 数据集中的 [GLUE 基准测试数据集](https://gluebenchmark.com/) 作为我们训练所使用的数据集，它是构成 MRPC 数据集的 10 个数据集之一，作为一个用于衡量机器学习模型在 10 个不同文本分类任务中性能的学术基准。

```python
from datasets import load_dataset

raw_datasets = load_dataset("glue", "mrpc")
raw_datasets
```

```shell
DatasetDict({
    train: Dataset({
        features: ['sentence1', 'sentence2', 'label', 'idx'],
        num_rows: 3668
    })
    validation: Dataset({
        features: ['sentence1', 'sentence2', 'label', 'idx'],
        num_rows: 408
    })
    test: Dataset({
        features: ['sentence1', 'sentence2', 'label', 'idx'],
        num_rows: 1725
    })
})
```

## 预处理数据集

```python
def tokenize_function(example):
    return tokenizer(example["sentence1"], example["sentence2"], truncation=True)
```

```python
tokenized_datasets = raw_datasets.map(tokenize_function, batched=True)
tokenized_datasets
```


```shell
DatasetDict({
    train: Dataset({
        features: ['attention_mask', 'idx', 'input_ids', 'label', 'sentence1', 'sentence2', 'token_type_ids'],
        num_rows: 3668
    })
    validation: Dataset({
        features: ['attention_mask', 'idx', 'input_ids', 'label', 'sentence1', 'sentence2', 'token_type_ids'],
        num_rows: 408
    })
    test: Dataset({
        features: ['attention_mask', 'idx', 'input_ids', 'label', 'sentence1', 'sentence2', 'token_type_ids'],
        num_rows: 1725
    })
})
```
## 动态填充


# 使用Trainer API微调模型


## training

## 评估


# 一个完整的训练

## 训练前的准备

## 训练循环

## 评估循环

##  使用🤗Accelerate加速你的训练循环


# [微调，章节回顾！](https://huggingface.co/learn/llm-course/zh-CN/chapter3/5)
# 微调，检查！