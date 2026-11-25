import { FullSlug, resolveRelative } from "../util/path"
import { QuartzComponent, QuartzComponentConstructor } from "./types"

const ExcalidrawPreview: QuartzComponent = ({ ctx, fileData }) => {
  const slug = fileData.slug
  if (!slug?.endsWith(".excalidraw")) return null

  const preview = (slug.slice(0, -".excalidraw".length) + ".png") as FullSlug
  if (!ctx.allSlugs.includes(preview)) return null

  return (
    <figure class="excalidraw-preview">
      <img
        src={resolveRelative(slug, preview)}
        alt={fileData.frontmatter?.title ?? "Excalidraw 图示"}
        decoding="async"
      />
    </figure>
  )
}

ExcalidrawPreview.css = `
.excalidraw-preview {
  margin: 1.5rem 0;
}

.excalidraw-preview img {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 0.625rem;
}
`

export default (() => ExcalidrawPreview) satisfies QuartzComponentConstructor
