import { FullSlug, resolveRelative } from "../util/path"
import { repositoryUrl } from "./SiteNav"
import { QuartzComponent, QuartzComponentConstructor } from "./types"

const topics = [
  { title: "AI 与大模型", slug: "06-ai/index", description: "LLM、Agent、训练与推理部署。" },
  { title: "后端工程", slug: "02-backend/index", description: "Java、Python、数据库与中间件。" },
  { title: "系统架构", slug: "architecture/index", description: "系统设计、架构决策与案例。" },
  { title: "计算机基础", slug: "01-cs-fundamentals/index", description: "数据结构、操作系统与计算机网络。" },
]

const HomeTopics: QuartzComponent = ({ fileData }) => {
  const href = (target: string) => resolveRelative(fileData.slug!, target as FullSlug)

  return (
    <>
      <section class="home-hero" aria-labelledby="home-title">
        <h1 id="home-title">探索技术，记录思考。</h1>
        <p>我是 Evan。这是我的个人技术主页，记录 AI、后端工程和系统架构的学习路线、原理笔记与工程实践。</p>
        <div class="home-hero-actions">
          <a class="home-primary" href={href("knowledge/index")}>探索知识库</a>
          <a class="home-secondary" href={repositoryUrl}>GitHub</a>
        </div>
      </section>
      <section aria-labelledby="home-topics-title">
        <h2 id="home-topics-title">探索技术领域</h2>
        <div class="home-topic-grid">
          {topics.map(({ title, slug, description }) => (
            <a class="home-topic" href={href(slug)}>
              <h3>{title}</h3>
              <p>{description}</p>
            </a>
          ))}
        </div>
      </section>
    </>
  )
}

export default (() => HomeTopics) satisfies QuartzComponentConstructor
