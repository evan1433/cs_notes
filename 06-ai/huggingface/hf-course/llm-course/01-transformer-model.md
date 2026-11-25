
# Transformers能做什么

[🤗 Transformers 库](https://github.com/huggingface/transformers) 提供了创建和使用这些共享模型的功能。 [Hugging Face 模型中心（以下简称“Hub”）](https://huggingface.co/models) 包含数千个任何人都可以下载和使用的预训练模型。你还可以将自己的模型上传到 Hub！

## 使用 pipelines

```python
from transformers import pipeline

classifier = pipeline("sentiment-analysis")
classifier("I've been waiting for a HuggingFace course my whole life.")
```

```shell
[{'label': 'POSITIVE', 'score': 0.9598047137260437}]
```
# Transformers 是如何工作的？


## 一点 Transformers 的发展历史


![](https://huggingface.co/datasets/huggingface-course/documentation-images/resolve/main/en/chapter1/transformers_chrono.svg)


[Transformer 架构](https://arxiv.org/abs/1706.03762) 于 2017 年 6 月提出。原本研究的重点是翻译任务。随后推出了几个有影响力的模型，包括
- **2018 年 6 月**： [GPT](https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf) ，第一个预训练的 Transformer 模型，用于各种 NLP 任务并获得极好的结果
- **2018 年 10 月**： [BERT](https://arxiv.org/abs/1810.04805) ，另一个大型预训练模型，该模型旨在生成更好的句子摘要（下一章将详细介绍！）
- **2019 年 2 月**： [GPT-2](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf) ，GPT 的改进（并且更大）版本，由于道德问题没有立即公开发布
- **2019 年 10 月**： [DistilBERT](https://arxiv.org/abs/1910.01108) ，BERT 的提炼版本，速度提高 60％，内存减轻 40％，但仍保留 BERT 97％ 的性能
- **2019 年 10 月**： [BART](https://arxiv.org/abs/1910.13461) 和 [T5](https://arxiv.org/abs/1910.10683) ，两个使用与原始 Transformer 模型原始架构的大型预训练模型（第一个这样做）
- **2020 年 5 月**， [GPT-3](https://arxiv.org/abs/2005.14165) ，GPT-2 的更大版本，无需微调即可在各种任务上表现良好（称为零样本学习）

## 迁移学习


# “编码器”模型



# "解码器"模型


# 序列到序列模型


# 偏见和局限性

# 总结



