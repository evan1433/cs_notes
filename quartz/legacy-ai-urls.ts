import { access, copyFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises"
import { dirname, join } from "node:path"
import legacyPaths from "./legacy-ai-paths.json"
import { write } from "./plugins/emitters/helpers"
import { QuartzEmitterPlugin } from "./plugins/types"
import { FilePath, simplifySlug, slugifyFilePath } from "./util/path"

async function supportsCaseSensitivePaths(output: string): Promise<boolean> {
  await mkdir(output, { recursive: true })
  const probe = await mkdtemp(join(output, ".case-check-"))
  try {
    await writeFile(join(probe, "lower"), "")
    return !(await access(join(probe, "LOWER")).then(() => true, () => false))
  } finally {
    await rm(probe, { recursive: true })
  }
}

export const LegacyAiUrls: QuartzEmitterPlugin = () => ({
  name: "LegacyAiUrls",
  async *emit(ctx) {
    const { output, directory } = ctx.argv
    if (!(await supportsCaseSensitivePaths(output))) return

    const site = `https://${ctx.cfg.configuration.baseUrl}/`
    for (const [oldPath, newPath] of Object.entries(legacyPaths)) {
      const from = slugifyFilePath(oldPath as FilePath)
      const to = slugifyFilePath(newPath as FilePath)
      if (!oldPath.endsWith(".md")) {
        const outputPath = join(output, from) as FilePath
        await mkdir(dirname(outputPath), { recursive: true })
        await copyFile(join(directory, newPath), outputPath)
        yield outputPath
        continue
      }

      const target = new URL(simplifySlug(to), site).href
      const quotedTarget = target.replaceAll("&", "&amp;").replaceAll('"', "&quot;")
      yield write({
        ctx,
        slug: from,
        ext: ".html",
        content: `<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="robots" content="noindex">
<link rel="canonical" href="${quotedTarget}">
<meta http-equiv="refresh" content="0; url=${quotedTarget}">
<script>location.replace(${JSON.stringify(target)} + location.search + location.hash)</script>
</head><body><a href="${quotedTarget}">前往新地址</a></body></html>`,
      })
    }
  },
})
