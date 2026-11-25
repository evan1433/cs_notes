FSDP
Fully Sharded Data Parallel  **完全分片数据并行**

FSDP的核心思想是“分片”（Sharding），就是将模型的参数、梯度和优化器状态像切蛋糕一样，均匀地切分到所有GPU上[](https://developer.baidu.com/article/detail.html?id=7306091)。每个GPU只负责存储和管理自己的一小片。

它的工作流程可以用以下步骤来理解：

1. **训练前**：每个GPU只保存模型的一部分参数（例如，一个100层模型，8个GPU可能每个只存12-13层的参数）[](https://machinelearningmastery.com/train-your-large-model-on-multiple-gpus-with-fully-sharded-data-parallelism/)。
    
2. **前向计算时**：当需要计算某一层（如第1层）时，所有GPU通过通信（All-Gather）将自己手上关于这一层的参数碎片汇集起来，在每个GPU上临时重建一个完整的第1层，进行计算[](https://machinelearningmastery.com/train-your-large-model-on-multiple-gpus-with-fully-sharded-data-parallelism/)[](https://www.mindspore.cn/technology-blogs/zh/2026-3-30)。
    
3. **计算完成后**：该层计算完毕，立即丢弃刚刚重建的完整参数，释放显存，各个GPU又只保留自己原有的那一小片[](https://machinelearningmastery.com/train-your-large-model-on-multiple-gpus-with-fully-sharded-data-parallelism/)[](https://www.mindspore.cn/technology-blogs/zh/2026-3-30)。
    
4. **反向传播与更新**：反向传播时，重复上述的汇集与丢弃过程。计算出梯度后，通过Reduce-Scatter操作将梯度也进行分片同步，每个GPU只更新自己负责的那片参数[](https://machinelearningmastery.com/train-your-large-model-on-multiple-gpus-with-fully-sharded-data-parallelism/)[](https://www.mindspore.cn/technology-blogs/zh/2026-3-30)。


DDP   
Distributed Data Parallel (分布式数据并行)
- **模型复制**：在每个GPU上复制一份完整的模型参数。
    
- **数据切分**：将一个大的训练批次（batch）切分成多个小份，分发给不同的GPU[](https://cloud.tencent.com.cn/document/product/851/103087)。
    
- **梯度同步**：每个GPU独立计算其分配到的数据的梯度，然后通过 **ring-all-reduce** 等高效通信算法在所有GPU之间同步梯度，确保每个GPU上的模型参数保持一致更新[](https://cloud.tencent.com.cn/document/product/851/103087)。
    

简而言之，DDP是一种**数据并行**策略，通过增加GPU数量来提升训练吞吐量，从而大幅缩短大模型的训练时间。但它有一个前提：单个模型的参数需要能够完整放入一张GPU的显存中[](https://docs.databricks.com/aws/en/machine-learning/ai-runtime/examples/gpu-ddp)。


DeepSpeed-zero2

DeepSpeed-zero3