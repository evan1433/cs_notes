# Agent Guidelines for cs_notes

This is an **Obsidian knowledge base** containing computer science study notes in Chinese. 
This repository supports both Obsidian viewing and GitHub Pages publishing via Quartz 4.0.

## Repository Structure

```
.
├── 01-cs-fundamentals/       # Computer Science Fundamentals
│   ├── data-structures.md
│   ├── computer-networks.md
│   └── operating-systems.md
├── 02-backend/               # Backend Development
│   ├── java-fundamentals/    # Java fundamentals
│   ├── databases/           # Databases
│   ├── web-servers/         # Web servers & frameworks
│   ├── cloud-native/        # Cloud native & build tools
│   ├── misc-backend/        # Other backend topics
│   ├── middleware/          # Middleware
│   ├── projects/            # Project experiences
│   ├── spring/              # Spring ecosystem
│   └── ssm/                 # SSM integration
├── 03-frontend/             # Frontend Development
├── 04-devtools/             # General Tools & Concepts
├── 05-book-notes/           # Book Notes
├── 06-ai/                   # Artificial Intelligence
├── sys-architect/           # System Architecture
├── sys-analyst/             # System Analyst
├── .obsidian/               # Obsidian config (gitignored)
├── quartz/                  # Quartz 4.0 core components
├── quartz.config.ts         # Quartz configuration
├── quartz.layout.ts         # Layout configuration
├── package.json             # Node.js dependencies
├── index.md                 # Homepage
├── CONTRIBUTING.md          # Documentation standards
└── .markdownlint.json       # Markdown linting rules
```

## Development Environment

### Local Quartz Development

1. Install Node.js 22+ (required by Quartz 4.0)
2. Install dependencies:
   ```bash
   fnm use 22 && corepack enable && pnpm install --frozen-lockfile
   ```
3. Build the site:
   ```bash
   pnpm build
   ```
4. Preview locally at http://localhost:8080:
   ```bash
   pnpm preview
   ```

### Quartz Configuration

- **Config file**: `quartz.config.ts`
- **Layout file**: `quartz.layout.ts`
- **Content directory**: Root folder (`.`)
- **Output directory**: `public/`
- **Base URL**: `/cs_notes/` (for GitHub Pages)

### Key Features Enabled

- **Graph view**: Visual representation of note connections
- **Backlinks**: Automatic backlink detection
- **Wiki-links**: Native `[[filename]]` support
- **Search**: Full-text search
- **Explorer**: File tree navigation
- **Dark mode**: Theme toggle

## Code Style Guidelines

### Markdown Formatting

1. **Headers**: Use `#` for title, `##` for sections, `###` for subsections
2. **Lists**: Use `-` for unordered lists, `1.` for ordered lists
3. **Code blocks**: Use triple backticks with language identifier
   
```java
   public class Example {
       // code here
   }
```
  

4. **Links**: Use Obsidian wiki-links for internal references: `[[filename]]`
5. **External links**: Use `[text](url)` format

### File Organization

1. **Naming**: Use Chinese names with `.md` extension
2. **Location**: Place files in appropriate category folder
3. **Tags**: Use Obsidian tags for cross-referencing: `#tagname`
4. **Links**: Use Obsidian wiki-links for internal references: `[[filename]]`

### Front Matter

Quartz supports the following front matter fields:

```yaml
---
title: 页面标题
date: 2024-01-01
tags:
  - tag1
  - tag2
aliases:
  - 别名
draft: false
---
```

### Content Guidelines

1. **Language**: Primary language is Chinese (中文)
2. **Structure**: Start with overview, then detailed sections
3. **Code examples**: Include practical, runnable examples
4. **References**: Link to official documentation when possible
5. **Updates**: Mark outdated content with `> **注意**: 内容已过时`

### Naming Conventions

- **Files**: Use hyphens for separation: `主题名称.md` (e.g., `spring-boot-2.md`, `java-se.md`)
- **Folders**: Use hyphens: `NN-类别名称/` (e.g., `02-后端/`, `01-Java/`)
- **Images**: Store in `attachments/` subfolder if needed

### Error Handling in Code Examples

When including code examples:

1. Show error cases and how to handle them
2. Include comments explaining "why" not just "what"
3. Use realistic examples, not `foo`/`bar`

## 文档体系标准

本项目遵循 **CONTRIBUTING.md** 中定义的文档标准。完整规范请参考 [CONTRIBUTING.md](./CONTRIBUTING.md)。

### 快速规范要点

#### 文件命名（英文 kebab-case）

| 类型 | 规则 | 示例 |
|------|------|------|
| 目录 | 英文 kebab-case，可选数字前缀 | `01-cs-fundamentals/`, `java-fundamentals/` |
| 文件 | 英文 kebab-case，无空格，无中文 | `data-structures.md`, `vue3-core-concepts.md` |
| 索引页 | 统一 `index.md` | `01-cs-fundamentals/index.md` |

**禁止**：
- 文件名含空格（如 `01 HTML.md`）
- 文件名含中文（如 `数据结构.md`）
- 中英混用（如 `01-Java-SE.md`）

#### Front Matter（必需）

```yaml
---
title: 页面标题（中文）
description: 一句话描述（用于 SEO）
tags:
  - tag1
  - tag2
date: YYYY-MM-DD
---
```

#### 内容要求

- **核心文档**：≥ 2 个实质性章节 + 至少 1 个可运行代码示例
- **占位文档**：添加 `draft: true`，不填充内容不发布
- **代码块**：必须标注语言（```java, ```python 等）

#### 链接规范

- **内部链接**：使用 WikiLink 格式 `[[filename]]`
- **外部链接**：使用标准 Markdown `[文字](URL)` 格式
- **跨语言链接**：`[[data-structures|数据结构]]`

#### 标签体系

采用三级标签系统：

| 级别 | 示例 | 用途 |
|------|------|------|
| 领域标签 | java, python, frontend, ai | 主分类 |
| 技术标签 | spring-boot, vue3, pytorch | 技术栈 |
| 概念标签 | concurrency, distributed-system | 抽象概念 |

---

## Git Workflow

```bash
# Add new notes
git add "02-后端/08-spring/新笔记.md"
git commit -m "docs: add notes on [topic]"

# Update existing notes
git commit -m "docs: update [topic] with [specific change]"
```

## Common Tasks

### Adding a New Note

1. Create file in appropriate folder: `02-backend/spring/new-topic.md`
2. Add front matter and content (see [Documentation Standards](#文档体系标准))
3. Run linter: `markdownlint "02-backend/spring/new-topic.md"`
4. Commit with message: `docs(backend): add notes on new topic`

### Updating Existing Note

1. Edit file
2. Run linter to check
3. Commit with descriptive message: `docs(scope): update topic with changes`

### Building and Deploying

```bash
# Build for production
pnpm build

# Preview locally
pnpm preview

# Deploy: push to master branch, GitHub Actions will auto-deploy
git push origin master
```

> **Note**: All documentation standards and naming conventions are defined in [CONTRIBUTING.md](./CONTRIBUTING.md).

## Notes

- Quartz 4.0 for GitHub Pages publishing
- Optimized for Obsidian vault usage
- All markdown files should pass markdownlint checks
- Wiki-links are automatically resolved by Quartz

## Quartz Publishing Notes

### Front Matter

For proper rendering, markdown files can include:

```yaml
---
title: 页面标题
date: 2024-01-01
tags: [tag1, tag2]
---
```

### Ignored Files

The following are excluded from Quartz build (see `quartz.config.ts`):
- `.obsidian/` - Obsidian config
- `.github/` - GitHub workflows
- `node_modules/` - NPM packages
- `quartz/` - Quartz core
- `copilot/` - Custom prompts
- `prompt/` - Prompt templates
- `*.json`, `*.ts`, `*.js` - Config files

### Navigation Structure

Navigation is provided by the Explorer component, which displays a file tree sorted alphabetically with Chinese locale support.
