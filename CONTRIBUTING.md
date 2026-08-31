# Contributing Guide

Thank you for contributing to CS Notes! This guide covers everything you need to know about writing, organizing, and maintaining documentation for this knowledge base.

## Table of Contents

- [Quick Start](#quick-start)
- [Naming Conventions](#naming-conventions)
- [Front Matter](#front-matter)
- [Document Structure](#document-structure)
- [Code Examples](#code-examples)
- [Links and References](#links-and-references)
- [Tags and Categories](#tags-and-categories)
- [Quality Standards](#quality-standards)
- [Git Workflow](#git-workflow)

---

## Quick Start

### Adding a New Note

1. Create a file in the appropriate category folder
2. Add front matter metadata (see [Front Matter](#front-matter))
3. Follow the document structure template (see [Document Structure](#document-structure))
4. Commit with a descriptive message

```bash
# Example: Adding a new Java note
git checkout -b docs/add-java-stream-api
# Create file: 02-backend/java-fundamentals/java-streams.md
git add 02-backend/java-fundamentals/java-streams.md
git commit -m "docs(backend): add Java Streams API guide"
git push origin docs/add-java-stream-api
```

### Updating Existing Notes

```bash
git checkout -b docs/update-redis-commands
# Edit the file
git commit -m "docs(backend): update Redis command reference with new cluster commands"
git push origin docs/update-redis-commands
```

---

## Naming Conventions

### Directory Names

Use **kebab-case** with numbered prefixes for main categories:

| English | Chinese (Old) | Notes |
|---------|--------------|-------|
| `01-cs-fundamentals/` | 01-计算机基础/ | CS core concepts |
| `02-backend/` | 02-后端/ | Backend development |
| `03-frontend/` | 03-前端/ | Frontend development |
| `04-devtools/` | 04-通用/ | Tools & utilities |
| `05-book-notes/` | 05-读书笔记/ | Book reading notes |
| `06-ai/` | 06-AI/ | AI & Machine Learning |
| `sys-analyst/` | 系统分析师/ | System Analyst certification |
| `sys-architect/` | 系统架构师/ | System Architect certification |

Subdirectories use kebab-case without numbers:

```
02-backend/
├── java-fundamentals/
├── databases/
├── middleware/
├── spring/
└── ssm/
```

### File Names

**All files use English kebab-case names** (no spaces, no Chinese characters):

| Correct | Incorrect |
|---------|-----------|
| `data-structures.md` | 数据结构.md |
| `java-se.md` | 01-Java-SE.md |
| `vue3-core-concepts.md` | Vue3.md |
| `computer-networks.md` | 计算机网络.md |
| `git-advanced.md` | git-高级.md |

**Rules:**
- No spaces in filenames (use `-` as separator)
- No Chinese characters in filenames
- Use descriptive, searchable English names
- Keep names concise but meaningful
- Index files are always `index.md`

### Code/Language Names

Technology names in content can use Chinese + English (e.g., "Java 基础语法", "Spring Boot 实战"), but filenames must be English only.

---

## Front Matter

Every content file should include YAML front matter:

```yaml
---
title: Page Title (Chinese, for display)
description: One-sentence description for SEO and search results.
tags:
  - tag1
  - tag2
date: YYYY-MM-DD
aliases:
  - alternative-name
  - old-filename
draft: false
---
```

### Field Specifications

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Display title in Chinese |
| `description` | Recommended | Used in search results and meta tags |
| `tags` | Recommended | Lowercase, hyphen-separated |
| `date` | Yes | Last modified date (YYYY-MM-DD) |
| `aliases` | Optional | Alternative filenames for redirects |
| `draft` | Optional | `true` hides from published site |

### Examples

**Java Note:**
```yaml
---
title: Java SE 核心语法
description: Java 基本语法、数据类型、面向对象核心概念详解
tags:
  - java
  - backend
  - fundamentals
date: 2024-03-21
---
```

**AI Note:**
```yaml
---
title: PyTorch 自动求导机制
description: 深入理解 PyTorch autograd 计算图与自动微分原理
tags:
  - python
  - pytorch
  - deep-learning
date: 2024-03-20
aliases:
  - pytorch-autograd
---
```

---

## Document Structure

### Standard Template

```markdown
---
title: Topic Title
description: Brief description.
tags: [tag1, tag2]
date: YYYY-MM-DD
---

# Topic Title

## Overview (2-3 sentences)

Explain what this topic is about and why it matters.

## Prerequisites

- [Link to prerequisite topic](path)
- Basic understanding of X

## Core Concepts

### Concept 1

Explain with code examples.

```language
// Runnable code example
const example = "with language tag";
```

### Concept 2

Continue with detailed explanation.

## Advanced Topics

For advanced usage patterns.

## Common Patterns

Show frequently used patterns with examples.

## Troubleshooting

Common pitfalls and solutions.

| Error | Cause | Solution |
|-------|-------|----------|
| `Error X` | Y | Z |

## See Also

- [[related-document|Related Topic]]
- [External Resource](https://example.com)
```

### Structure Guidelines

1. **One concept per section** — Don't mix installation, configuration, and usage in one section
2. **Use hierarchical headings** — `#` for title, `##` for major sections, `###` for subsections
3. **Include practical examples** — Every technical concept needs runnable code
4. **Add comparison tables** — When there are multiple approaches or options
5. **Cross-reference related content** — Use `[[wiki-links]]` to connect related notes

### Content Types

| Type | Purpose | Structure |
|------|---------|-----------|
| **Tutorial** | Learning-oriented | Step-by-step, outcome-focused |
| **How-to Guide** | Task-oriented | Practical, problem-solution |
| **Reference** | Information-oriented | Complete, accurate, well-organized |
| **Explanation** | Understanding-oriented | Conceptual, discusses "why" |

---

## Code Examples

### Requirements

- **Must be runnable** — All code snippets must work when copied
- **Include language tags** — Use triple backticks with language identifier
- **Add explanatory comments** — Explain "why" not just "what"
- **Use realistic examples** — Avoid `foo`, `bar`, `example123`

### Good Example

```java
// Use try-with-resources for automatic resource management
try (BufferedReader reader = new BufferedReader(
        new FileReader("data.txt"))) {
    String line;
    while ((line = reader.readLine()) != null) {
        processLine(line);
    }
} catch (IOException e) {
    logger.error("Failed to read file", e);
}
```

### Error Documentation

When documenting errors:

```markdown
## Common Errors

### NullPointerException

**Cause**: Calling a method on a null object reference.

**Solution**: Add null checks before method calls:

```java
if (object != null) {
    object.doSomething();
}
```
```

---

## Links and References

### Internal Links (WikiLinks)

Use Obsidian-style wiki-links for internal references:

```markdown
# Link to another document
[[data-structures]]

# Link with custom text
[[data-structures|Tree and Binary Tree]]

# Link to specific section
[[java-se#Exception Handling]]

# Link to directory index
[[java-fundamentals/index|Java Fundamentals]]
```

### External Links

Use standard Markdown links for external resources:

```markdown
[Official Documentation](https://docs.example.com)
[MDN Web Docs](https://developer.mozilla.org)
```

### Link Best Practices

- Prefer wiki-links for internal references (enables Quartz backlink tracking)
- Always verify external links are current
- Use descriptive link text (not "click here")
- Link to concepts before explaining them

---

## Tags and Categories

### Tag Taxonomy (Three-Level System)

| Level | Examples | Purpose |
|-------|----------|---------|
| **Domain** | java, python, frontend, ai, database, devops | Primary category |
| **Technology** | spring-boot, vue3, pytorch, redis, docker | Specific tech stack |
| **Concept** | concurrency, design-patterns, distributed-system | Abstract concepts |

### Tag Usage

```yaml
tags:
  - java           # Domain
  - spring-boot    # Technology
  - dependency-injection  # Concept
```

### Directory vs. Tags

- **Directories** — Primary organization (what major area)
- **Tags** — Cross-cutting concerns (what topics span multiple areas)

---

## Quality Standards

### Minimum Content Requirements

A document is considered complete when it has:

- [ ] Front matter with title and date
- [ ] At least 2 substantive sections (not just headings)
- [ ] At least one working code example (for technical topics)
- [ ] No broken internal or external links
- [ ] Chinese content (this is a Chinese-language knowledge base)

### Content Density Guidelines

| Document Type | Minimum Size | Expected Size |
|--------------|-------------|---------------|
| Quick reference | 200 chars | 500-1KB |
| Core concept | 2KB | 5-10KB |
| Deep dive / Tutorial | 5KB | 10-50KB |

### Draft Mode

Use `draft: true` for:

- Work-in-progress documents
- Outlines and skeletons
- Content that's not yet ready for publication

```yaml
---
title: Work in Progress
draft: true
---
```

Documents with `draft: true` are excluded from the published site (handled by Quartz RemoveDrafts plugin).

---

## 文档质量保障（Docs Quality Gates）

> 本节是文档体系的执行层：模板保证"生而合规"，审计保证"持续合规"。

### 写新笔记：从模板开始

所有新笔记从 `templates/` 目录的对应模板创建，不要从空白文件开始：

| 笔记类型 | 模板 | 适用场景 |
|----------|------|----------|
| 概念解释 | `templates/concept-note.md` | 原理、机制、方案对比 |
| 实战教程 | `templates/tutorial-note.md` | 搭环境、部署、跑通流程 |
| 速查参考 | `templates/reference-note.md` | 命令、参数、配置手册 |
| 目录索引 | `templates/index-note.md` | 各目录的 index.md |

选择依据见 [templates/README.md](templates/README.md)。模板已内置 front matter、
双向链接占位、排错表格等必备结构，复制后按指引填写即可。

### 提交前自查清单

```bash
npm run docs:audit   # 一键检查全库合规情况
```

审计脚本（`scripts/audit_docs.py`）检查六类问题：

1. **front matter 完整性** —— title / description / tags / date 缺失率
2. **命名合规** —— 中文或含空格的文件名
3. **空壳文档** —— 小于 2KB 且未标 `draft: true`（会被发布成"空页面"）
4. **代码块语言标注率** —— 未标注语言的代码块无法获得语法高亮
5. **知识孤岛** —— 全文没有任何 `[[wiki-link]]` 的笔记（图谱中断点）
6. **目录索引覆盖** —— 含 2 篇以上笔记却没有 index.md 的目录

CI 场景使用 `npm run docs:audit:fail`，存在空壳已发布文档或命名违规时返回非零退出码。

### 存量修复优先级

面对历史欠账，按以下顺序修（性价比从高到低）：

1. **空壳文档补 `draft: true`** —— 一行 front matter，立刻消除发布站上的空页面
2. **命名违规重命名** —— 中文/空格文件名 → 英文 kebab-case，同时在 front matter
   `aliases` 中保留旧名，避免旧链接失效（wiki-link 引用需同步更新）
3. **缺索引目录补 index.md** —— 用 `templates/index-note.md` 创建
4. **高频文档补 front matter** —— 先补访问量高的目录，再逐步覆盖
5. **知识孤岛补双向链接** —— 修一篇链一篇，不必一次性补完

---

## Git Workflow

### Branch Naming

```bash
docs/add-{topic}           # Adding new content
docs/update-{topic}        # Updating existing content
docs/fix-{issue}          # Fixing errors
docs/refactor-{folder}     # Restructuring content
```

### Commit Messages

Follow conventional commits with `docs:` prefix:

```bash
docs(ai): add PyTorch LSTM implementation guide
docs(backend): update Redis cluster configuration
docs(frontend): expand Vue3 composition API section
docs(fundamentals): add red-black tree visualization
fix(java): correct typo in concurrent-hash-map
refactor(sys-analyst): rename files to English
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**: `docs`, `fix`, `refactor`
- **scope**: affected area (backend, frontend, ai, etc.)
- **subject**: brief description (imperative mood, no period)
- **body**: detailed explanation (optional)
- **footer**: breaking changes, issue references (optional)

---

## Quick Reference

### Directory Quick Map

```
cs_notes/
├── 01-cs-fundamentals/    # Data structures, networks, OS
├── 02-backend/           # Java, databases, middleware, Spring
├── 03-frontend/           # HTML, CSS, JS, Vue, React
├── 04-devtools/           # Git, Docker, Linux, K8s
├── 05-book-notes/         # Book reading notes
├── 06-ai/                 # ML, DL, LLM, PyTorch
├── sys-analyst/           # System Analyst certification
└── sys-architect/         # System Architect certification
```

### File Naming Cheatsheet

| Chinese | English | Example |
|---------|---------|---------|
| 数据结构 | data-structures | `data-structures.md` |
| Java基础 | java-fundamentals | `java-se.md` |
| 计算机网络 | computer-networks | `computer-networks.md` |
| Vue3 | vue3 | `vue3-core-concepts.md` |
| 操作系统 | operating-systems | `operating-systems.md` |

---

## Questions?

- Check existing notes in the same category for style reference
- Review [AGENTS.md](../AGENTS.md) for project conventions
- Look at [README.md](../README.md) for overall project context

Happy documenting!
