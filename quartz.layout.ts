import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"

// components shared across all pages
export const sharedPageComponents: SharedLayout = {
  head: Component.Head(),
  header: [],
  afterBody: [],
  footer: Component.Footer({
    links: {
      GitHub: "https://github.com/dukechase/cs_notes",
    },
  }),
}

// components for pages that display a single page (e.g. a single note)
export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    Component.ConditionalRender({
      component: Component.Breadcrumbs(),
      condition: (page) => page.fileData.slug !== "index",
    }),
    Component.ArticleTitle(),
    Component.ContentMeta(),
    Component.TagList(),
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
  ],
  right: [
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
    Component.DesktopOnly(Component.TableOfContents()),
    Component.Backlinks(),
  ],
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