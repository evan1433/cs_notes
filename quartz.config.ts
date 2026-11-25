import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"
import { LegacyAiUrls } from "./quartz/legacy-ai-urls"
import { byDateAndAlphabeticalFolderFirst } from "./quartz/components/PageList"

/**
 * Quartz 4 Configuration for CS Notes
 */
const config: QuartzConfig = {
  configuration: {
    pageTitle: "CS Notes",
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: null,
    locale: "zh-CN",
    baseUrl: "evan1433.github.io/cs_notes",
    ignorePatterns: [
      "private",
      "templates",
      ".obsidian",
      ".agents/**",
      ".devcontainer",
      ".git",
      ".github",
      "Clippings",
      "inbox",
      "copilot",
      "prompt",
      "node_modules",
      "public",
      "quartz",
      "*.skill",
      "*.json",
      "*.ts",
      "*.mjs",
      "*.js",
      "LICENSE*",
      "Dockerfile",
      "*.svg",
      "todo.md",
      "AGENTS.md",
      "QWEN.md"
    ],
    defaultDateType: "modified",
    theme: {
      fontOrigin: "googleFonts",
      cdnCaching: true,
      typography: {
        header: "Noto Sans SC",
        body: "Noto Sans SC",
        code: "IBM Plex Mono",
      },
      colors: {
        lightMode: {
          light: "#fafafa",
          lightgray: "#e2e8f0",
          gray: "#b8b8b8",
          darkgray: "#475569",
          dark: "#0f172a",
          secondary: "#2563eb",
          tertiary: "#64748b",
          highlight: "rgba(91, 143, 230, 0.12)",
          textHighlight: "#fff23688",
        },
        darkMode: {
          light: "#0f1117",
          lightgray: "#2b3440",
          gray: "#646464",
          darkgray: "#94a3b8",
          dark: "#e5e7eb",
          secondary: "#60a5fa",
          tertiary: "#94a3b8",
          highlight: "rgba(91, 143, 230, 0.12)",
          textHighlight: "#b3aa0288",
        },
      },
    },
  },
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      Plugin.CreatedModifiedDate({
        priority: ["frontmatter", "git", "filesystem"],
      }),
      Plugin.SyntaxHighlighting({
        theme: {
          light: "github-light",
          dark: "github-dark",
        },
        keepBackground: false,
      }),
      Plugin.ObsidianFlavoredMarkdown({ enableInHtmlEmbed: true, enableCheckbox: true }),
      Plugin.GitHubFlavoredMarkdown(),
      Plugin.TableOfContents(),
      Plugin.CrawlLinks({ markdownLinkResolution: "shortest" }),
      Plugin.Description(),
      Plugin.Latex({ renderEngine: "katex" }),
    ],
    filters: [Plugin.RemoveDrafts()],
    emitters: [
      Plugin.AliasRedirects(),
      LegacyAiUrls(),
      Plugin.ComponentResources(),
      Plugin.ContentPage(),
      Plugin.FolderPage({
        sort: (a, b) => {
          if (a.slug?.startsWith("02-backend/python/") && b.slug?.startsWith("02-backend/python/")) {
            const aOrder = Number(a.slug.split("/").at(-1)?.match(/^(\d+)-/)?.[1] ?? Infinity)
            const bOrder = Number(b.slug.split("/").at(-1)?.match(/^(\d+)-/)?.[1] ?? Infinity)
            if (aOrder !== bOrder) return aOrder - bOrder
          }
          return byDateAndAlphabeticalFolderFirst(config.configuration)(a, b)
        },
      }),
      Plugin.TagPage(),
      Plugin.ContentIndex({
        enableSiteMap: true,
        enableRSS: true,
      }),
      Plugin.Assets(),
      Plugin.Static(),
      Plugin.Favicon(),
      Plugin.NotFoundPage(),
    ],
  },
}

export default config
