
# 垂类大模型生产系统

AI 基础设施工程师

[IBM-什么是AI基础设施](https://www.ibm.com/cn-zh/think/topics/ai-infrastructure)
[什么是云计算](https://www.ibm.com/cn-zh/think/topics/cloud-computing)


垂直大模型   训练流程 标准化
ai原生架构


基础设施

大模型生命周期
- 数据处理
- 训练/微调
	- 预训练 pre-training
	- 后训练 post-training
		- 微调框架
		- pytorch PEFT/LORA/ QLoRA
- 推理 inference


零样本泛化、少样本 ICL、思维链（CoT）和指令遵循

AI领域快速发展  各种开源项目、标准、生态涌现，各个大厂都在构建自己的生态

做公司级别的标准化统一

# 白皮书

- [AI 云采用框架-阿里云白皮书](https://merak.alicdn.com/aliyundotcom-report/2025-ai-caf.pdf)
- [阿里云AI网络白皮书](https://help.aliyun.com/zh/cloud-network-well-architected-design/alibaba-cloud-ai-network-white-paper)
- [GenAI应用场景与 落地路径白皮书](https://merak.alicdn.com/aliyundotcom-report/gen-ai-application-scenarios-and-implementation-path-white-paper.pdf)

[AI-就绪 - 数据 - 基础设施 - 白皮书](https://e.huawei.com/en/topic/storage/ai-ready-data-infrastructure-white-paper)
AI纪元数据基础设施挑战
- 数据资产管理：企业需要具备多样化的功能，以应对来自多个来源的、不同质量的数据，并支持不同部门之间的完整数据流动。
- 集群利用率:大规模训练集群的计算资源利用率低于50%。这导致计算建设成本高、功耗大。
- 数据一致性:任何用户必须能够在任何时间、任何节点访问最新更新的数据副本。
- 数据韧性:基于AI的应用程序导致新的漏洞，危及韧性。一旦大型AI模型遭受攻击，可能造成数千万美元的损失。

[# AI 原生基础设施概览](https://jimmysong.io/zh/book/ai-handbook/infra/overview/)


生产流程
基模
数据工程
模型微调策略
评估与验证体系

架构层次
# 数据

行业数据 （基础）
- 存储  大数据**存储**
- 处理   pipeline    复用
	- 清洗
	- 脱敏（医疗/金融领域）

# 模型、算法

Why Separate Backbones? 
LLM training and generation have conflicting optimization requirements: 
Training needs gradient computation, large batch processing, and memory-efficient parameter sharding. Generation needs fast token sampling, low latency, and optimized KV-cache management.
大模型为什么训练和推理（生成）分离？LLM 训练和生成具有冲突的优化需求：
训练需要梯度计算、大批量处理和内存高效的参数分片。
生成需要快速 Token 采样、低延迟和优化的 KV 缓存管理。

昇思
https://www.mindspore.cn/   

模型训练/微调
- 模型权重存储
	- pytorch/ huggingface safetensor
	- GGUF
- 基础模型选择
	- 不同业务场景、行业 选择合适的基础模型
- SFT 、RLHF框架 标准   **训练和微调框架**
	- llamaFactoy
	- [unsloth](https://github.com/unslothai/unsloth)  fine-tuning 解决方案
	- **NeMo RL**
	- 
- 验证流程标准化（评估验证体系）
	- 基准测试 行业专用数据集
	- 场景化POC（概念验证）
	- “红队”测试     专门攻击模型的弱点，测试其是否会生成幻觉（Hallucination）或违规建议
部署
- 量化框架 
	- `bitsandbytes`   模型量化库
推理
- 推理引擎
	- vllm
	- llama.cpp
# 智能体

AI应用

RAG
- 索引/预处理
- 检索/生成
知识图谱


未来趋势
1. **从“训练”转向“组装”**：  
    未来的研发可能更多是 **Agent（智能体）** 的编排。一个大模型作为“大脑”，调用多个小工具（计算器、搜索器、专业数据库）来完成复杂任务，而非单纯依赖模型内部参数记忆。
2. **多模态融合 (Multi-modal)**： 
    垂类应用不再局限于文本。
    - _工业_：输入设备震动波形图 + 文本日志 -> 输出故障原因。
    - _教育_：输入手写试卷照片 -> 输出批改结果与知识点分析。
3. **小模型专精化 (Small but Mighty)**：  
    在边缘设备（如工厂工控机、车载终端）上，参数量在 7B-14B 的量化小模型将成为主流，因为它们响应快、成本低、数据不出域。
4. **合规即代码 (Compliance as Code)**：  
    在研发流程中嵌入自动化合规检测脚本，确保模型输出符合《生成式人工智能服务管理暂行办法》及行业


# 研发平台

[阿里人工智能平台PAI-一站式AI研发平台](https://www.alibabacloud.com/help/zh/pai/product-overview/what-is-machine-learning-platform-for-ai/?spm=a2c63.l28256.help-menu-30347.d_0_0.24ac556ftY9gYu)
- 数据标注

[MegaScale: Scaling Large Language Model Training to More Than 10,000 GPUs](https://arxiv.org/abs/2402.15627)
[# 拆解一下字节的烧钱工作，MegaScale！](https://zhuanlan.zhihu.com/p/684712727)
