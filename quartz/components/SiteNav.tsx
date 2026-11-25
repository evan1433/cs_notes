import { FullSlug, resolveRelative } from "../util/path"
import Darkmode from "./Darkmode"
import Search from "./Search"
import { QuartzComponent, QuartzComponentConstructor } from "./types"

const links: { label: string; slug: FullSlug }[] = [
  { label: "首页", slug: "index" as FullSlug },
  { label: "知识库", slug: "knowledge/index" as FullSlug },
  { label: "学习路线", slug: "paths/index" as FullSlug },
  { label: "项目实践", slug: "projects/index" as FullSlug },
  { label: "关于", slug: "about" as FullSlug },
]

export const repositoryUrl = "https://github.com/evan1433/cs_notes"

export default (() => {
  const SearchControl = Search()
  const ThemeControl = Darkmode()
  const SiteNav: QuartzComponent = (props) => {
    const { slug } = props.fileData
    const menuLinks = links.map(({ label, slug: target }) => (
      <a
        href={resolveRelative(slug!, target)}
        aria-current={slug === target ? "page" : undefined}
      >
        {label}
      </a>
    ))
    return (
      <div class="site-nav">
        <a class="site-brand" href={resolveRelative(slug!, links[0].slug)}>
          Evan <span>/</span> CS Notes
        </a>
        <nav class="site-nav-links" aria-label="站点导航">{menuLinks}</nav>
        <div class="site-nav-actions">
          <SearchControl {...props} />
          <ThemeControl {...props} />
          <a class="site-nav-github" href={repositoryUrl}>GitHub</a>
        </div>
        <details class="site-nav-menu">
          <summary>菜单</summary>
          <nav aria-label="移动端站点导航">{menuLinks}</nav>
        </details>
      </div>
    )
  }

  SiteNav.css = [SearchControl.css, ThemeControl.css].join("\n")
  SiteNav.afterDOMLoaded = SearchControl.afterDOMLoaded
  SiteNav.beforeDOMLoaded = ThemeControl.beforeDOMLoaded
  return SiteNav
}) satisfies QuartzComponentConstructor
