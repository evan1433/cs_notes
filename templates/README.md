# 文档模板库

本目录存放 cs_notes 知识库的标准化文档模板，`templates/` 已在 `quartz.config.ts` 的 `ignorePatterns` 中排除，**不会被发布到站点**。

## 模板选择指南

先判断你要写的笔记属于哪种类型，再取对应模板（参考 [Divio 文档分类法](https://documentation.divio.com/)）：

| 我想写... | 模板 | 特征 |
|-----------|------|------|
| 某个技术概念的原理、机制、对比 | [concept-note.md](./concept-note.md) | 解释"为什么"，面向理解 |
| 搭环境 / 部署服务 / 跑通流程 | [tutorial-note.md](./tutorial-note.md) | 分步操作，面向动手 |
| 命令、参数、配置的快速查阅 | [reference-note.md](./reference-note.md) | 表格为主，面向查阅 |
| 某目录的 index.md | [index-note.md](./index-note.md) | 学习路径 + 笔记索引 |

## 使用方法

```bash
# 1. 复制模板到目标目录（示例：写 vLLM 概念笔记）
cp templates/concept-note.md 06-AI/model_deploy/vllm.md

# 2. 重命名为英文 kebab-case（禁止中文、空格）
# 3. 填写 front matter（title/description/tags/date 必填）
# 4. 删除模板顶部的"使用说明"块
# 5. 完成前保留 draft: true；完成后改为 false 或删除该字段
```

## 硬性检查项（提交前自查）

- [ ] 文件名：英文 kebab-case，无空格无中文
- [ ] front matter：`title` / `description` / `tags` / `date` 四项齐全
- [ ] 代码块：全部标注语言，且实际验证可运行
- [ ] 双向链接：正文至少 2 个 `[[wiki-link]]`，避免知识孤岛
- [ ] 未完成的笔记带 `draft: true`（不发布）

## 批量质量检查

```bash
pnpm docs:audit   # 运行文档合规审计，输出统计报告
```

审计脚本位于 `scripts/audit_docs.py`，检查 front matter 完整率、命名违规、空壳文档、代码块语言标注等指标。
