# [视觉大模型的预训练范式演进：从架构革新到自监督学习的深度探索](https://chat.z.ai/c/70abf89c-cb89-4d27-b149-485d3cf789ce)

## 视觉Transformer的奠基与预训练的初始探索

在深度学习的历史长河中，卷积神经网络（CNN）凭借其内在的归纳偏置（Inductive Bias），如局部性（Locality）和空间不变性（Spatial Invariance），长期以来主导着计算机视觉领域[[0](https://www.v7labs.com/blog/vision-transformer-guide)]。**CNN架构**通过层层堆叠的卷积核和池化层，能够有效地从图像中提取从低级边缘、角点到高级语义特征的层次化表示，这一特性与人类视觉系统的感知机制高度吻合，使其在图像分类、目标检测、语义分割等众多任务中取得了辉煌成就。然而，CNN的这一强先验假设也构成了其发展的“玻璃天花板”。尽管其在处理局部信息时表现出色，但在建模图像中长距离依赖关系时，CNN则需要通过深层结构和巨大的感受野来间接实现，这不仅增加了模型的复杂度和计算成本，也可能导致信息在传递过程中的损失或稀释。随着模型规模的不断扩大和数据集的持续增长，研究者们开始反思：是否存在一种更具扩展性、能够更直接地捕捉全局上下文信息的视觉模型架构？这一思考催生了自然语言处理（Natural Language Processing, NLP）领域与计算机视觉（Computer Vision, CV）领域的一次深刻交汇。2017年，Transformer架构凭借其核心的自注意力机制（Self-Attention Mechanism）在机器翻译等NLP任务上取得了突破性进展，其能够动态地计算序列中任意两个元素之间的依赖关系，从而完美地解决了长距离依赖建模问题。这一成功为视觉领域的研究者提供了全新的灵感：如果将图像视为一个序列，Transformer是否也能在视觉任务中大放异彩？正是在这一背景下，**Vision Transformer（ViT）** 应运而生，它标志着视觉模型设计理念的一次根本性变革——从依赖人工设计的归纳偏置转向了更为通用的、数据驱动的序列建模范式[0](https://www.v7labs.com/blog/vision-transformer-guide)。

Vision Transformer的核心思想在于将标准的Transformer编码器直接应用于图像，其实现过程包含一系列关键的预处理步骤。首先，一幅输入图像被分割成一系列固定大小的、不重叠的**图像块（Image Patches）**。例如，对于一张224x224像素的图像，若使用16x16的图像块大小，则会得到196个图像块。每个图像块随后被展平成一个一维向量，并通过一个可学习的线性投影层映射到一个高维的嵌入空间（Embedding Space），形成所谓的“**Patch Embeddings**”。这一过程类似于NLP中将单词转换为词向量（Word Embeddings），它将原始的像素信息转化为模型可以处理的语义表示。为了保留图像块在原始图像中的位置信息，ViT还引入了一组可学习的位置嵌入（Position Embeddings），并将其加到对应的Patch Embeddings上。这使得模型能够区分不同位置的图像块，并理解图像的空间结构。最后，与NLP中的Transformer类似，一个特殊的`[class]`标记（Token）被添加到这个图像块序列的开头。这个`[class]`标记对应的最终输出状态，被视为整个图像的聚合表示，并被用于图像分类等任务的最终预测[[0](https://www.v7labs.com/blog/vision-transformer-guide)]。通过这一系列精巧的设计，ViT成功地将二维图像问题转化为一维序列问题，从而能够直接利用强大的Transformer架构进行建模。然而，这种架构的通用性也带来了新的挑战。与CNN不同，ViT缺乏对图像的内在先验知识，它需要从头开始学习图像的空间结构和局部特征。这意味着ViT对数据的规模和质量有着极高的依赖性。在数据量有限的情况下，ViT的表现往往不如同等规模的CNN，因为CNN的归纳偏置为其提供了良好的初始化和正则化。只有当预训练数据集的规模达到数千万甚至上亿张图像时，ViT才能充分展现其强大的学习能力，并在各种图像分类基准测试上稳定地超越CNN模型[[5](https://www.articsledge.com/post/vision-transformer-vit)]。这一发现深刻揭示了ViT的“规模法则”（Scaling Law）：模型的性能与其规模（包括参数量、计算量和数据量）之间存在强相关性。ViT的出现，不仅为视觉领域提供了一种全新的、极具扩展性的骨干网络（Backbone），更重要的是，它开启了一个关于如何有效预训练这些大规模模型的时代。它将研究的焦点从“设计更好的网络架构”部分转移到了“如何利用海量数据进行高效预训练”，为后续一系列自监督学习和多模态学习方法的爆发奠定了坚实的基础。

ViT的提出，虽然在架构上实现了从CNN到Transformer的跨越，但其预训练方式在初期仍然遵循着传统的监督学习范式，即在带有大规模人工标注的数据集（如ImageNet-21K、JFT-300M等）上进行图像分类任务的预训练[[7](https://viso.ai/deep-learning/vision-transformer-vit)]。这种**监督预训练（Supervised Pre-training）** 的目标是让模型学习到能够正确区分数千个甚至数万个类别的视觉特征。通过最小化预测类别与真实类别之间的交叉熵损失（Cross-Entropy Loss），模型被迫学习到对下游任务（如图像分类、目标检测）有用的通用表示。预训练完成后，模型通常会在特定的下游任务数据集上进行**微调（Fine-tuning）**，即使用较小的学习率在下游任务的数据上继续训练模型的部分或全部参数，以使其适应新的任务分布。这种“预训练-微调”（Pre-train and Fine-tune）的范式已经成为深度学习领域，特别是视觉领域的标准流程。然而，监督预训练的局限性也日益凸显。最核心的问题在于其对海量高质量标注数据的极度依赖。人工标注数据不仅成本高昂、耗时耗力，而且其覆盖的语义范围和领域多样性也受到限制。例如，ImageNet虽然包含超过1400万张图像和2万多个类别，但其类别体系仍然相对固定，无法覆盖现实世界中无穷无尽的视觉概念。这种局限性使得通过监督预训练学到的视觉表示可能存在偏见，并且难以泛化到那些在预训练数据集中罕见或完全不存在的视觉领域或概念。此外，监督学习任务（如图像分类）本身可能并非学习丰富视觉表示的最优途径。模型可能只学习到区分不同类别所需的最小化特征，而忽略了图像中其他丰富的高层语义信息和纹理、形状等细节。这种“知其然，而不知其所以然”的学习方式，限制了模型表示能力的上限。
因此，研究者们开始积极探索摆脱对人工标注依赖的预训练方法，即**自监督学习（Self-Supervised Learning, SSL）**。自监督学习的核心思想是从数据自身中构造监督信号，通过设计各种“代理任务”（Proxy Tasks）来让模型学习有用的表示。在ViT的背景下，这意味着利用图像本身的结构和信息，而不依赖任何人工标签，来训练模型。这一探索催生了视觉预训练领域的两大主流技术路线：一是以**掩码建模（Masked Modeling）** 为代表的方法，其灵感来源于NLP领域的BERT；二是以**对比学习（Contrastive Learning）** 为代表的方法，其目标是拉近相似样本的表示，推远不相似样本的表示。ViT的通用架构为这两大路线的蓬勃发展提供了理想的试验场，因为它不像CNN那样具有强烈的归纳偏置，能够更灵活地适应各种自监督预训练目标，从而从海量无标注数据中挖掘出更深层次的视觉知识。

## CLIP：多模态对比学习的范式革命

在Vision Transformer为视觉模型架构带来革新，并引发对自监督预训练深度思考的同时，另一条影响深远的探索路径正在悄然兴起，它试图打破视觉和语言两大模态之间的壁垒，从更广阔的跨模态数据中学习。这条路径的集大成者，便是由OpenAI提出的**CLIP（Contrastive Language–Image Pre-training）** 模型[30](https://openai.com/index/clip)。CLIP的出现，不仅在技术上实现了重大突破，更在理念上对视觉预训练的范式进行了一次深刻的革命。它不再将视觉视为一个孤立的领域，而是将其与自然语言这一承载着丰富语义知识的媒介紧密结合，通过学习图像和文本之间的对应关系，来获得前所未有的强大视觉理解能力和泛化性。CLIP的核心思想异常简洁而优雅：给定一个包含（图像，文本）对的庞大数据集，模型需要学习判断哪些文本描述与哪些图像是匹配的[[33](https://arxiv.org/abs/2103.00020)]。这个任务被称为对比学习，其目标不是去识别图像中的具体物体（如“猫”或“狗”），而是去学习一个嵌入空间，在这个空间中，匹配的图像和文本对的表示向量在几何上相互靠近，而不匹配的图像和文本对的表示向量则相互远离。这种学习方式巧妙地利用了互联网上几乎无穷无尽的、自然存在的图像-文本配对数据，例如网页中的图片及其标题、社交媒体上的图片及其描述等。这些数据的海量性和多样性，远超任何人工构建的标注数据集，为CLIP提供了前所未有的“养料”。

CLIP的架构设计也充分体现了其多模态的特性。它包含两个独立的编码器：一个图像编码器（Image Encoder）和一个文本编码器（Text Encoder）[[31](https://en.wikipedia.org/wiki/Contrastive_Language-Image_Pre-training)]。图像编码器可以采用如ViT或ResNet等主流的视觉骨干网络，负责将输入的图像映射为一个高维的特征向量。文本编码器则通常采用Transformer架构，负责将输入的文本描述也映射为一个相同维度的高维特征向量。在预训练过程中，CLIP使用一个名为InfoNCE的对比损失函数。具体来说，对于一个批次（Batch）中的N个（图像，文本）对，CLIP会计算所有图像特征和所有文本特征之间的N x N个余弦相似度（Cosine Similarity）。对于任何一个正确的（图像i，文本i）对，其目标是最大化它们之间的相似度，同时最小化图像i与批次中所有其他不匹配文本（文本j，j≠i）的相似度，以及文本i与批次中所有其他不匹配图像（图像j，j≠i）的相似度。通过这种方式，模型被迫学习到图像内容和文本语义之间深刻的对齐关系。图像编码器不仅要理解图像中包含了什么，还要以一种与文本编码器理解语言的方式相兼容的方式进行理解。例如，模型不仅需要学会识别出“一只柯基犬在草地上追球”的图像，还要将这幅图像的表示与“一只柯基犬在草地上追球”这句话的表示紧密联系起来。

CLIP这种预训练范式带来的最引人注目的成果是其卓越的**零样本迁移学习（Zero-shot Transfer**）能力[[32](https://github.com/openai/CLIP)]。在传统的“预训练-微调”范式中，预训练模型需要在下游任务的有标签数据上进行微调才能适应新任务。而CLIP则完全跳过了微调步骤。在预训练完成后，CLIP可以直接应用于各种图像分类任务，而无需任何任务特定的训练。其实现方式非常巧妙：对于一个给定的图像分类任务，CLIP会为每个类别构造一个文本提示（Prompt），例如“A photo of a {class}”。然后，它使用预训练好的文本编码器为所有这些类别的文本提示计算特征向量。同时，它使用图像编码器为待分类的图像计算特征向量。最后，通过计算图像特征向量与所有类别文本特征向量的相似度，并将相似度最高的文本提示所对应的类别作为图像的预测结果。这种“将图像分类任务转化为图像-文本匹配任务”的方式，使得CLIP展现出了惊人的灵活性和泛化能力。它在包括ImageNet在内的数十个图像分类基准测试上，仅通过零样本学习就取得了可与当时最先进的、经过完全监督预训练和微调的模型相媲美的性能[[30](https://openai.com/index/clip)]。这证明了CLIP通过大规模对比学习学到的视觉表示具有极强的通用性和鲁棒性。

CLIP的成功标志着视觉预训练进入了一个全新的阶段。它证明了，通过利用海量、嘈杂但多样化的自然语言监督，可以学习到远超传统监督学习的视觉概念。其意义是多方面的：首先，它极大地扩展了视觉模型的“词汇量”。传统模型的识别能力受限于预训练数据集的类别数量，而CLIP的识别能力理论上受限于其文本编码器的词汇量，可以覆盖成千上万甚至更多的概念。其次，它为视觉模型带来了前所未有的开放性（Open Vocabulary）和可组合性（Compositionality）。由于CLIP理解语言，它可以处理那些在预训练中从未见过的、由多个词组合而成的新概念，例如“一个戴着帽子的、骑在自行车上的大象”。最后，CLIP的成功也为后续的视觉-语言多模态大模型（如DALL-E系列、Stable Diffusion等）的诞生铺平了道路，它提供了一种强大的、将视觉和语义对齐的表示空间，成为连接这两个模态的关键桥梁。然而，CLIP也并非完美无瑕。其对比学习范式在处理一些需要精细视觉辨别或结构化理解的任务时，可能不如专门设计的掩码建模方法。此外，CLIP的性能也高度依赖于预训练数据的规模和质量，以及文本提示的设计。尽管如此，CLIP作为多模态对比学习的里程碑，其核心思想——从跨模态的关联中学习——已经深刻地改变了我们对如何构建强大视觉系统的认知，并成为了后续众多视觉基础模型发展的重要基石。

## DINO与iBOT：自监督掩码建模的深度演化

在CLIP通过多模态对比学习开辟新天地的同时，另一股强大的力量在纯视觉的自监督学习领域内涌动并走向成熟。这股力量聚焦于一个核心思想：**掩码建模（Masked Modeling）**，即像NLP领域的BERT一样，通过遮盖输入的一部分并迫使模型去预测被遮盖的内容，从而学习到深层的、结构化的数据表示。这一路线在视觉领域的探索中，诞生了两个里程碑式的模型：**DINO（Self-Distillation with NO labels）** 和**iBOT（Image BERT Pre-Training with Online Tokenizer）**。它们共同代表了自监督视觉预训练从初步尝试到高度精密化的演进过程，展示了如何在没有人工标注和跨模态信号的情况下，仅从图像本身中挖掘出极其丰富和鲁棒的视觉信息。DINO的提出，是自监督视觉学习领域的一次关键突破。它引入了一种名为**自蒸馏（Self-Distillation）** 的创新训练机制，巧妙地利用了知识蒸馏的思想，但无需一个预先训练好的“教师”模型[[26](https://towardsdatascience.com/dino-a-foundation-model-for-computer-vision-4cb08e821b18)]。DINO的架构包含两个结构完全相同但参数不同的网络：一个“学生”网络和一个“教师”网络。学生网络的参数通过梯度下降进行更新，而教师网络的参数则通过学生网络参数的指数移动平均（Exponential Moving Average, EMA）进行平滑更新。这种动量编码器（Momentum Encoder）的设计使得教师网络的更新更加稳定，能够为学生网络提供更一致、更可靠的指导信号。

DINO的训练过程是一个经典的“在线蒸馏”过程。首先，对同一张输入图像，应用两种不同的数据增强（Data Augmentation）策略，生成两个不同的“视图”（Views）。这两个视图被分别送入学生网络和教师网络，得到两个输出特征。DINO的核心目标是最小化这两个输出分布在特定维度（通常是[class]标记的输出）上的KL散度（Kullback–Leibler Divergence）。换句话说，学生网络被训练去模仿教师网络在经过不同数据增强后的图像视图上产生的输出。这种自对比机制迫使模型学习到那些在不同视角、不同光照、不同遮挡条件下都保持不变的核心图像特征，从而学习到高度不变和鲁棒的视觉表示[[23](https://www.emergentmind.com/topics/dinov2-based-approaches)]。DINO的一个非凡特性是，它能够自发地在没有任何监督信号的情况下，学习到图像的语义分割（Semantic Segmentation）。研究者发现，仅仅通过DINO进行预训练，ViT模型的不同“头”（Head）就会自动关注到图像中的不同物体，并且其最后一个注意力图（Attention Map）能够清晰地勾勒出物体的边界。这一“涌现属性”（Emergent Property）证明了DINO学到的表示不仅仅是像素级的统计规律，而是具有深刻语义理解能力的特征。

在DINO的基础上，DINOv2进一步将这一思想推向了极致，旨在构建一个真正意义上的视觉基础模型（Vision Foundation Model）[[20](https://arxiv.org/abs/2304.07193)]。DINOv2的核心洞察是，自监督方法的质量高度依赖于训练数据的规模和多样性。为此，研究者们精心策划并构建了一个包含1.42亿张图像的、经过高度筛选和整理的私有数据集。通过在这个海量且多样化的数据集上进行DINO风格的预训练，DINOv2学习到了极其强大和通用的视觉特征。这些特征的强大之处在于，它们可以直接用于各种下游计算机视觉任务（如分类、分割、目标检测、深度估计等），而无需进行微调，仅需在这些任务的特征之上训练一个简单的线性分类器即可取得顶尖性能[[22](https://github.com/facebookresearch/dinov2)]。DINOv2的成功标志着，纯视觉的自监督预训练已经能够产生与CLIP等多模态模型相媲美，甚至在某些纯视觉任务上更优的通用表示，为构建不依赖语言的视觉“大脑”提供了可能。

与DINO的自蒸馏并行发展的，是另一条以掩码图像建模（Masked Image Modeling, MIM）为核心的路线，其直接继承了BERT的“填空”思想。这条路线的早期探索者包括**BEiT**（BERT Pre-Training of Image Transformers）和**MAE**（Masked AutoEncoders）[[50](https://arxiv.org/abs/2106.08254)]。BEiT是第一个成功将BERT范式应用于ViT的模型，它没有直接预测被遮盖图像块的像素值，而是预测这些图像块的“视觉令牌”（Visual Tokens）[[54](https://medium.com/@deepsiya10/day-10-beit-bert-meets-vision-ad381757a71d)]。这些视觉令牌是通过一个离线训练的、离散的码本（Codebook）（如dVAE）将图像块量化得到的。预测离散的令牌比预测连续的像素值被认为是一个更高级、更具语义性的任务。而MAE则提出了一种极其高效的非对称编码器-解码器设计[[45](https://www.emergentmind.com/topics/masked-autoencoder-mae-pretraining-strategy)]。它只将一小部分（如25%）的可见图像块送入编码器进行特征提取，然后将编码器的输出与被遮盖的图像块的位置信息拼接在一起，送入一个轻量级的解码器来重建原始图像[[48](https://sh-tsang.medium.com/review-masked-autoencoders-are-scalable-vision-learners-b7c42910f7b4)]。这种设计大大降低了预训练的计算成本，使得训练超大规模的ViT模型成为可能。

iBOT（Image BERT Pre-Training with Online Tokenizer）则可以看作是BEiT和DINO思想的集大成者，它将掩码建模与自蒸馏机制巧妙地融合在一起[[10](https://arxiv.org/abs/2111.07832)]。iBOT的核心创新在于其“在线令牌器”（Online Tokenizer）。与BEiT使用离线、固定的码本不同，iBOT的令牌器是在训练过程中与学生网络一起端到端学习的。这个令牌器本质上就是一个目标网络，其结构与学生网络的编码器类似。iBOT的训练过程包含两个并行的目标：第一个目标是经典的掩码图像建模。学生网络接收被高度遮盖（如遮盖75%）的图像，并尝试预测被遮盖区域的视觉令牌，而这些令牌是由教师网络（作为在线令牌器）从原始的、未遮盖的图像中生成的。第二个目标是DINO式的自蒸馏目标，即让学生网络在全局图像层面（如[class]标记的输出）模仿教师网络的输出[[11](https://sh-tsang.medium.com/brief-review-ibot-image-bert-pre-training-with-online-tokenizer-85c32e47fee6)]。通过这种双重目标的联合优化，iBOT同时获得了两方面的好处：掩码建模迫使模型学习图像的局部细节和结构信息，而自蒸馏则保证了模型学习到的全局表示的鲁棒性和一致性。iBOT的成功证明了，将不同的自监督学习范式进行有机结合，能够产生1+1>2的效果，从而学习到更全面、更强大的视觉表示。从DINO的自蒸馏到iBOT的在线令牌器与掩码建模的融合，我们看到了一条清晰的演进路径：自监督学习的设计变得越来越精密，越来越能够从数据中榨取出有价值的监督信号，最终目标是构建一个能够像人类一样，仅通过观察世界就能深刻理解其内在规律的智能系统。

## 融合与展望：迈向统一的视觉基础模型

随着Vision Transformer（ViT）架构的确立，以及CLIP、DINO和iBOT等预训练范式的蓬勃发展，视觉大模型的研究进入了一个百家争鸣的黄金时代。然而，在经历了初期的爆炸式创新后，一个自然的问题浮出水面：这些看似不同、各有所长的预训练方法，是否存在某种内在的联系，能否被融合成一个更强大、更统一的框架？对这一问题的探索，引领着视觉预训练领域向着更高层次的集成化和通用化迈进，其最终目标是构建能够胜任任何视觉任务的“视觉基础模型”（Vision Foundation Model）。在这一融合与展望的浪潮中，EVA（Exploring the Limits of Masked Visual Representation Learning at Scale）系列模型的出现，为我们揭示了一条极具前景的融合路径，它巧妙地桥接了以CLIP为代表的多模态对比学习与以iBOT为代表的掩码建模之间的鸿沟。

EVA的核心思想可以被概括为“站在巨人的肩膀上”。研究者们认识到，像CLIP这样通过海量图像-文本对齐数据预训练出的模型，其图像编码器已经学习到了极其丰富且与语义紧密关联的视觉特征[[64](https://openaccess.thecvf.com/content/CVPR2023/papers/Fang_EVA_Exploring_the_Limits_of_Masked_Visual_Representation_Learning_at_CVPR_2023_paper.pdf)]。这些特征本身就是一种高质量的、蕴含语义信息的“监督信号”。那么，我们能否直接利用这些强大的特征作为掩码建模的重建目标呢？这正是EVA所做的。EVA采用了一个经典的ViT作为其骨干网络，但其预训练任务却不再是预测像素或离散的视觉令牌，而是直接预测被遮盖图像块所对应的CLIP图像编码器的输出特征[[67](https://arxiv.org/abs/2211.07636)]。具体来说，在预训练过程中，EVA的编码器接收一幅被部分遮盖的图像，并基于可见的图像块来预测那些被遮盖区域的特征。这个预测的目标，就是预训练好的CLIP图像编码器在处理完整、未遮盖图像时，在对应位置输出的特征向量。

这种设计带来了多方面的深刻优势。首先，它极大地提升了掩码建模任务的语义层次。与重建原始像素或简单的离散令牌相比，重建CLIP特征意味着模型需要学习理解和预测那些与高级概念（如物体、属性、场景）相关联的表示。这迫使EVA的编码器不仅要学习图像的低级纹理和形状，更要学习其高层语义内容。其次，EVA实现了知识的有效蒸馏和迁移。它将CLIP通过海量多模态数据学习到的宝贵知识，以一种高效的方式“蒸馏”到了一个纯视觉的ViT模型中。这使得EVA能够继承CLIP强大的开放词汇理解能力和泛化性，同时又保持了ViT架构的简洁和高效。EVA的后续版本，如EVA-02，进一步扩展和深化了这一思想，通过在更大规模的数据和更先进的CLIP教师模型（如EVA-CLIP）上进行预训练，取得了更加卓越的性能，证明了这一范式的强大可扩展性[[62](https://www.sciencedirect.com/science/article/abs/pii/S0262885624002762)]。EVA的成功，标志着视觉预训练进入了一个“后元学习”的时代：我们不再仅仅从原始数据中学习，而是开始从其他已经强大的预训练模型中学习，形成了一种模型之间知识传承和迭代的良性循环。

展望未来，视觉大模型及其预训练方式的发展正朝着几个清晰而激动人心的方向演进。
**首先是模型的持续规模化。** 无论是DINOv2通过扩大数据集实现的“数据规模定律”，还是EVA通过蒸馏CLIP实现的“知识规模定律”，都印证了“规模即智能”这一趋势。未来，我们将看到参数量达到数十亿甚至上百亿的视觉模型，它们将在更加庞大和多样的数据上进行预训练，从而获得前所未有的视觉认知能力。
**其次是多模态融合的深化。** CLIP开创了图像与文本的对齐，而未来的模型将致力于融合更多模态的信息，如音频、视频、3D、传感器数据等。例如，NeRF-MAE已经开始探索将掩码建模思想应用于3D神经场（Neural Radiance Fields, NeRF）的预训练，这预示着自监督学习将突破2D图像的界限，走向对三维动态世界的理解[[40](https://arxiv.org/abs/2404.01300)]。
**第三是预训练范式的统一与自动化。** 从DINO的自蒸馏，到iBOT的在线令牌器，再到EVA的特征重建，我们看到预训练目标的设计变得越来越复杂和精巧。未来的一个重要方向是开发能够自动发现或生成最优预训练任务的算法，让模型能够根据数据和目标，自适应地设计其学习策略。
**最后，也是最重要的，是向通用人工智能（Artificial General Intelligence, AGI）的迈进。** 视觉基础模型正逐渐成为构建AGI不可或缺的“眼睛”和“视觉皮层”。它们提供的不仅仅是像素识别能力，而是一种对世界的结构化、语义化的理解。这种理解是机器人与环境交互、智能体进行复杂推理和规划的基础。从ViT的架构革新，到CLIP的跨模态对齐，再到DINO、iBOT和EVA在自监督领域的深度演化，我们见证的不仅仅是一系列模型的迭代，更是一场关于如何让机器“看见”并“理解”这个世界的认知革命。这场革命远未结束，它正引领着我们向着构建真正具备通用视觉智能的终极目标，坚定而有力地迈进。

# 参考文献

[0] Vision Transformer: What It Is & How It Works [2024 Guide]. https://www.v7labs.com/blog/vision-transformer-guide.

[1] Pre-training of Lightweight Vision Transformers on Small. https://arxiv.org/abs/2402.03752.

[2] Vision transformer-based visual language understanding. https://www.sciencedirect.com/science/article/pii/S1110016824004873.

[3] Accelerating Augmentation Invariance Pretraining. https://neurips.cc/virtual/2024/poster/94817.

[4] Evaluation of effectiveness of pre-training method in chest. https://www.tandfonline.com/doi/full/10.1080/21681163.2024.2345823.

[5] What is a Vision Transformer (ViT)? Complete Guide 2026. https://www.articsledge.com/post/vision-transformer-vit.

[6] Domain-Specific Vision Transformer Pre-Training with. https://dl.acm.org/doi/10.1145/3704137.3704168.

[7] Vision Transformers (ViT) in Image Recognition. https://viso.ai/deep-learning/vision-transformer-vit.

[8] An Explanation of the Vision Transformer (ViT) Paper. https://medium.com/codex/an-explanation-of-the-vision-transformer-vit-paper-8cdd399741aa.

[9] lucidrains/vit-pytorch: Implementation of Vision Transformer. https://github.com/lucidrains/vit-pytorch.

[10] iBOT: Image BERT Pre-Training with Online Tokenizer. https://arxiv.org/abs/2111.07832.

[11] iBOT: Image BERT Pre-Training with Online Tokenizer | by Sik. https://sh-tsang.medium.com/brief-review-ibot-image-bert-pre-training-with-online-tokenizer-85c32e47fee6.

[12] iBOT: Image BERT Pre-Training with Online Tokenizer. https://huggingface.co/papers/2111.07832.

[13] bytedance/ibot: iBOT :robot:: Image BERT Pre-Training with. https://github.com/bytedance/ibot.

[14] [PDF] iBOT: Image BERT Pre-Training with Online Tokenizer. https://www.semanticscholar.org/paper/iBOT%3A-Image-BERT-Pre-Training-with-Online-Tokenizer-Zhou-Wei/9653c070724e44f023e8cc3ec79f0b9e6d59480d.

[15] IBOT ImageBertPreTrainingWithOnlineTokenizer | PDF. https://www.scribd.com/document/835721965/IBOT-ImageBertPreTrainingWithOnlineTokenizer.

[16] Self-distillation improves self-supervised learning for DNA. https://www.sciencedirect.com/science/article/pii/S0893608024009079.

[17] Enhancing Few-Shot Medical Image Classification with. https://2025.ic-dsp.org/wp-content/uploads/2025/05/2025156473-1.pdf.

[18] Abstract. https://arxiv.org/html/2601.11719v1.

[19] SSL with Vision Transformers. https://rohitbandaru.github.io/blog/SSL-with-Vision-Transformers.

[20] [2304.07193] DINOv2: Learning Robust Visual Features. https://arxiv.org/abs/2304.07193.

[21] Foundation vision models in agriculture: DINOv2, LoRA. https://www.sciencedirect.com/science/article/abs/pii/S0168169925010063.

[22] PyTorch code and models for the DINOv2 self-supervised. https://github.com/facebookresearch/dinov2.

[23] DINOv2-Based Approaches Overview. https://www.emergentmind.com/topics/dinov2-based-approaches.

[24] DINOv2: Self-supervised Learning Model Explained. https://encord.com/blog/dinov2-self-supervised-learning-explained.

[25] Self-Distillation with No Labels (DINO) & DINOV2 - Jehill Parikh. https://jehillparikh.medium.com/improved-image-encoding-using-transformers-self-distillation-with-no-labels-dino-dinov2-79ac5b6cac06.

[26] DINO - A Foundation Model for Computer Vision. https://towardsdatascience.com/dino-a-foundation-model-for-computer-vision-4cb08e821b18.

[27] Examining vision foundation models for classification and. https://www.aanda.org/articles/aa/full_html/2025/11/aa53691-25/aa53691-25.html.

[28] Learning EEG Foundation Models via Hierarchical Self-. https://papers.miccai.org/miccai-2025/paper/3347_paper.pdf.

[29] Accessing Vision Foundation Models via ImageNet-1K. https://openreview.net/forum?id=LC6ZtQV6u2.

[30] CLIP: Connecting text and images. https://openai.com/index/clip.

[31] Contrastive Language-Image Pre-training. https://en.wikipedia.org/wiki/Contrastive_Language-Image_Pre-training.

[32] openai/CLIP. https://github.com/openai/CLIP.

[33] Learning Transferable Visual Models From Natural. https://arxiv.org/abs/2103.00020.

[34] Building a Tiny CLIP: Contrastive Image-Text Learning. https://medium.com/@varun_54675/building-a-tiny-clip-contrastive-image-text-learning-from-scratch-0ca31bf40c65.

[35] A History of CLIP Model Training Data Advances. https://voxel51.com/blog/a-history-of-clip-model-training-data-advances.

[36] CLIP: Contrastive Language–Image Pre-Training. https://viso.ai/deep-learning/clip-machine-learning.

[37] CLIP by Hand ✍️ - by Prof. Tom Yeh. https://www.byhand.ai/p/clip.

[38] Training a CLIP Model from Scratch for Text-to-Image. https://learnopencv.com/clip-model.

[39] CLIP Contrastive Language–Image Pre-Training Model. https://blog.roboflow.com/openai-clip.

[40] NeRF-MAE: Masked AutoEncoders for Self-Supervised 3D. https://arxiv.org/abs/2404.01300.

[41] Masked Autoencoders are Secretly Efficient Learners. https://ieeexplore.ieee.org/document/10677918.

[42] Efficient MAE Towards Large-Scale Vision Transformers. https://openaccess.thecvf.com/content/WACV2024/html/Han_Efficient_MAE_Towards_Large-Scale_Vision_Transformers_WACV_2024_paper.html.

[43] How Effective is Pre-training of Large Masked. https://bmva-archive.org.uk/bmvc/2024/workshops/MVEO/paper5.pdf.

[44] Irrelevant Patch-Masked Autoencoders for Enhancing. https://www.sciencedirect.com/science/article/abs/pii/S0950705124015703.

[45] MAE Pretraining Strategy. https://www.emergentmind.com/topics/masked-autoencoder-mae-pretraining-strategy.

[46] Self-Guided Masked Autoencoder - NIPS. https://proceedings.neurips.cc/paper_files/paper/2024/file/6c4a1a3cbe70ef36d7d6332166bba77d-Paper-Conference.pdf.

[47] Self Pre-Training with Masked Autoencoders for Medical. https://bmi.stonybrookmedicine.edu/node/865.

[48] Review — Masked Autoencoders Are Scalable Vision Learners. https://sh-tsang.medium.com/review-masked-autoencoders-are-scalable-vision-learners-b7c42910f7b4.

[49] NeRF-MAE: Masked AutoEncoders for Self-Supervised 3D. https://nerf-mae.github.io.

[50] BEiT: BERT Pre-Training of Image Transformers. https://arxiv.org/abs/2106.08254.

[51] A Mix-and-Mask Approach to Self-Supervised Image Pretraining. https://cs231n.stanford.edu/2024/papers/a-mix-and-mask-approach-to-self-supervised-image-pretraining.pdf.

[52] BEiT. https://huggingface.co/docs/transformers/en/model_doc/beit.

[53] BEiT v2: Masked Image Modeling with Vector-Quantized. https://www.semanticscholar.org/paper/BEiT-v2%3A-Masked-Image-Modeling-with-Visual-Peng-Dong/599be9043ef3571f65758cf36e184c9dc1781baf.

[54] 📦 Day 10 — BEiT: BERT Meets Vision | by Deepali Mishra. https://medium.com/@deepsiya10/day-10-beit-bert-meets-vision-ad381757a71d.

[55] BEiT v2: Masked Image Modeling with Vector-Quantized. https://www.researchgate.net/publication/362693900_BEiT_v2_Masked_Image_Modeling_with_Vector-Quantized_Visual_Tokenizers.

[56]  `[22.08]` BEiT v2. https://docsaid.org/en/papers/vision-transformers/beit-v2.

[57] Medicinal plant recognition based on Vision Transformer. https://www.sciencedirect.com/science/article/pii/S187705092400351X.

[58] Masked Channel Modeling Enables Vision Transformers to. https://pmc.ncbi.nlm.nih.gov/articles/PMC12385973.

[59] Open-Vocabulary Panoptic Segmentation Using BERT Pre. https://arxiv.org/abs/2412.18917.

[60] arXiv:2402.04252v1 [cs.CV] 6 Feb 2024. https://arxiv.org/pdf/2402.04252.

[61] EVA: Exploring the Limits of Masked Visual Representation. https://www.researchgate.net/publication/373309883_EVA_Exploring_the_Limits_of_Masked_Visual_Representation_Learning_at_Scale.

[62] EVA-02: A visual representation for neon genesis. https://www.sciencedirect.com/science/article/abs/pii/S0262885624002762.

[63] EVA: Exploring the Limits of Masked Visual Representation. https://www.connectedpapers.com/main/78281482c1fdad8e167bab39cc9955c73d58ae8f/EVA%3A-Exploring-the-Limits-of-Masked-Visual-Representation-Learning-at-Scale/graph.

[64] EVA: Exploring the Limits of Masked Visual Representation. https://openaccess.thecvf.com/content/CVPR2023/papers/Fang_EVA_Exploring_the_Limits_of_Masked_Visual_Representation_Learning_at_CVPR_2023_paper.pdf.

[65] Efficient Vision-Language pre-training via domain-specific. https://aclanthology.org/2024.emnlp-main.454.pdf.

[66] Masked Image Modeling: A Survey. https://link.springer.com/article/10.1007/s11263-025-02524-1.

[67] EVA: Exploring the Limits of Masked Visual Representation. https://arxiv.org/abs/2211.07636.

[68] Improving Visual Comprehension via Token Reconstruction for. https://www.semanticscholar.org/paper/ViCToR%3A-Improving-Visual-Comprehension-via-Token-Xie-Yang/5f4fa6d9c4b97b8e1650195e643a0b4f8c71829e.

[69] Classification Done Right for Vision-Language Pre-Training. https://proceedings.neurips.cc/paper_files/paper/2024/file/aee5298251a418aad89618cf6b5e7ccc-Paper-Conference.pdf.