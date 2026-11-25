
TRL   https://github.com/huggingface/trl

TRLX https://github.com/CarperAI/trlx

axolotl https://github.com/axolotl-ai-cloud/axolotl

LlamaFactory  https://github.com/hiyouga/LlamaFactory

unsloth    https://github.com/unslothai/unsloth

## LoRA

**全称：** *Low-Rank Adaptation of Large Language Models*（大型语言模型的低秩自适应）。

**简单来说：** 它是一种**极其高效的 AI 模型微调（Fine-tuning）技术**。如果把大模型（如 GPT、Llama 或 Stable Diffusion）比作一本写满知识的**巨型百科全书**，传统的微调是把整本书重写一遍（极其昂贵、耗时）。而 LoRA 就像是在书的旁边贴了一张**便利贴**，只修改或补充特定的内容，而不动原来的书。

**核心特点与优势：**

- **极低的资源消耗：** 传统全量微调需要巨大的显存（VRAM），可能需要几十张 A100 显卡。而 LoRA 可以让普通消费级显卡（如 RTX 3060, 4090）也能训练大模型。
    
- **文件极小：** 训练出来的 LoRA 模型文件通常只有几 MB 到几百 MB，而原始大模型通常是几十 GB。这使得分享和切换风格非常容易。
    
- **不破坏原模型：** 原始模型的权重被冻结（Freeze），LoRA 只是作为一个“外挂”插件存在。你可以给同一个模型挂载不同的 LoRA（例如一个负责画动漫风，一个负责画写实风）。
    
**应用场景：**

- **AI 绘画 (Stable Diffusion)：** 让 AI 学会画特定的角色（如某个动漫人物）、特定的画风（如水墨画、赛博朋克）或特定的构图。
    
- **大语言模型 (LLMs)：** 让通用的 AI（如 Llama 3, Qwen）变成特定领域的专家（如医疗助手、法律顾问、代码生成器）。
