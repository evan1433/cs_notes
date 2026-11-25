import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"
import { QuartzComponent, QuartzComponentProps } from "./quartz/components/types"
import { repositoryUrl } from "./quartz/components/SiteNav"

const isHome = ({ fileData }: QuartzComponentProps) => fileData.slug === "index"
const homeOnly = (component: QuartzComponent) =>
  Component.ConditionalRender({ component, condition: isHome })
const readingOnly = (component: QuartzComponent) =>
  Component.ConditionalRender({ component, condition: (props) => !isHome(props) })

// components shared across all pages
export const sharedPageComponents: SharedLayout = {
  head: Component.Head(),
  header: [homeOnly(Component.SiteNav())],
  afterBody: [
    homeOnly(
      Component.RecentNotes({
        title: "最近更新",
        dateType: "modified",
        limit: 6,
        showTags: false,
        filter: ({ slug, frontmatter, text }) =>
          Boolean(
            slug &&
            /^(0[1-6]-[^/]+|architecture|sys-analyst)\//.test(slug) &&
            !slug.endsWith("/index") &&
            !slug.endsWith(".excalidraw") &&
            !frontmatter?.draft &&
            (text?.length ?? 0) >= 500
          ),
      }),
    ),
    Component.ConditionalRender({
      condition: ({ fileData }) => fileData.slug === "blog",
      component: Component.RecentNotes({
        title: "全部文章",
        dateType: "published",
        filter: ({ frontmatter }) =>
          Boolean(frontmatter?.published && frontmatter.tags?.includes("technical-blog")),
        limit: Infinity,
        showTags: false,
      }),
    }),
  ],
  footer: Component.Footer({
    links: {
      GitHub: repositoryUrl,
      RSS: "https://evan1433.github.io/cs_notes/index.xml",
    },
  }),
}

// components for pages that display a single page (e.g. a single note)
export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    homeOnly(Component.HomeTopics()),
    ...[Component.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta(), Component.TagList()]
      .map(readingOnly),
  ],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        {
          Component: Component.Search(),
          grow: true,
        },
        { Component: Component.Darkmode() },
        { Component: Component.ReaderMode() },
      ],
    }),
    Component.Explorer({
      title: "导航",
      folderClickBehavior: "link",
      folderDefaultState: "collapsed",
      useSavedState: true,
      sortFn: (a, b) => {
        // Sort with Chinese locale support
        // Keep the Python learning path in filename order while displaying titles.
        if (a.slug.startsWith("02-backend/python/") && b.slug.startsWith("02-backend/python/")) {
          const aOrder = Number(a.slugSegment.match(/^(\d+)-/)?.[1] ?? Infinity)
          const bOrder = Number(b.slugSegment.match(/^(\d+)-/)?.[1] ?? Infinity)
          if (aOrder !== bOrder) return aOrder - bOrder
        }
        return a.displayName.localeCompare(b.displayName, "zh-CN", { numeric: true })
      },
      filterFn: (node) => {
        // Filter out hidden files, tags, and special directories
        const name = node.displayName
        return name !== "tags" && !name.startsWith(".") && !name.startsWith("_")
      },
      mapFn: (node) => {
        return node
      },
      order: ["filter", "map", "sort"],
    }),
  ].map(readingOnly),
  right: [
    Component.DesktopOnly(Component.TableOfContents()),
    Component.Backlinks(),
    Component.Graph({
      localGraph: {
        drag: true,
        zoom: true,
        depth: 1,
        scale: 1.1,
        repelForce: 0.5,
        centerForce: 0.3,
        linkDistance: 30,
        fontSize: 0.6,
        opacityScale: 1,
        showTags: true,
        removeTags: [],
      },
      globalGraph: {
        drag: true,
        zoom: true,
        depth: -1,
        scale: 0.9,
        repelForce: 0.5,
        centerForce: 0.3,
        linkDistance: 30,
        fontSize: 0.6,
        opacityScale: 1,
        showTags: true,
        removeTags: [],
      },
    }),
  ].map(readingOnly),
}

// components for pages that display lists of pages  (e.g. tags or folders)
export const defaultListPageLayout: PageLayout = {
  beforeBody: [Component.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta()],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        {
          Component: Component.Search(),
          grow: true,
        },
        { Component: Component.Darkmode() },
      ],
    }),
    Component.Explorer({
      title: "导航",
      folderClickBehavior: "link",
      folderDefaultState: "collapsed",
      useSavedState: true,
      sortFn: (a, b) => {
        // Keep the Python learning path in filename order while displaying titles.
        if (a.slug.startsWith("02-backend/python/") && b.slug.startsWith("02-backend/python/")) {
          const aOrder = Number(a.slugSegment.match(/^(\d+)-/)?.[1] ?? Infinity)
          const bOrder = Number(b.slugSegment.match(/^(\d+)-/)?.[1] ?? Infinity)
          if (aOrder !== bOrder) return aOrder - bOrder
        }
        return a.displayName.localeCompare(b.displayName, "zh-CN", { numeric: true })
      },
      filterFn: (node) => {
        return node.displayName !== "tags" && !node.displayName.startsWith(".") && !node.displayName.startsWith("_")
      },
      mapFn: (node) => {
        return node
      },
      order: ["filter", "map", "sort"],
    }),
  ],
  right: [],
}
