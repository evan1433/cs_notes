#!/usr/bin/env python3
"""检查 cs_notes 的链接健康度：wiki-link、Markdown 相对链接、图片、锚点。

用法:
    python3 scripts/check_links.py          # 静态检查（只看源文件，秒级）
    python3 scripts/check_links.py --built  # 构建产物检查（需先 pnpm build）

为什么不只用静态检查：
Quartz 会把附件名 slug 化（`Pasted image 1.png` → `Pasted-image-1.png`），
并按全库 slug 解析 wiki-link，还会对标题锚点做 slug 化。
所以"文件系统里存在"不等于"站点上不断链"，发布前必须跑 --built。

退出码: 0 无问题; 1 存在断链
"""

import json
import posixpath
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 与 quartz.config.ts 的 ignorePatterns 保持一致：这些目录不参与发布，
# 里面的链接不会渲染成页面链接，因此不需要修。
SKIP_DIRS = {
    "node_modules", "public", "quartz", ".git", ".github", ".obsidian",
    ".devcontainer", ".workbuddy", "templates", "Clippings", "copilot",
    "private", "prompt", ".agents", "inbox",
}

WIKILINK = re.compile(r"\[\[([^\]\n]+)\]\]")
MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
IMG_LINK = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def source_files():
    for p in ROOT.rglob("*.md"):
        if set(p.parts) & SKIP_DIRS:
            continue
        yield p


def strip_noise(text: str) -> str:
    """去掉 front matter、代码块、行内代码——它们里面的 [[...]] 不是链接。"""
    text = FRONT_MATTER.sub("", text)
    text = FENCE.sub("", text)
    return INLINE_CODE.sub("", text)


def parse_wikilink(raw: str):
    """拆出 (目标, 锚点)。表格内 `[[a\\|别名]]` 的 `|` 也是别名分隔符。"""
    body = raw.split("|")[0].rstrip("\\").strip()
    anchor = ""
    if "#" in body:
        body, anchor = body.split("#", 1)
        body, anchor = body.strip(), anchor.strip()
    body = body.split("^")[0].strip()
    return body, anchor


def check_static():
    files = list(source_files())
    stems = {p.stem for p in files}
    # 附件文件名集合：库内非 md 的真实文件（图片、交互图 html 等）。
    # 带显式扩展名的 wiki-link 目标（如 [[attachments/x.png]]、[[...foo.html]]）
    # 不可能出现在 md stems 里，改为按文件名实际存在性解析。
    asset_names = {
        p.name
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix != ".md"
        and not (set(p.parts) & SKIP_DIRS)
        and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
    }
    problems = []

    for path in files:
        body = strip_noise(path.read_text(encoding="utf-8", errors="ignore"))

        for m in WIKILINK.finditer(body):
            target, _anchor = parse_wikilink(m.group(1))
            if not target:
                continue
            last = target.split("/")[-1]
            # 带扩展名 = 附件类目标，按附件集合解析（.md 仍走 stems，不放过 [[foo.md]]）
            if last not in stems and not ("." in last and last in asset_names):
                problems.append((path, m.group(0), "wiki-link 目标不存在"))

        for m in MD_LINK.finditer(body):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = (path.parent / urllib.parse.unquote(href.split("#")[0])).resolve()
            if not target.exists():
                problems.append((path, href, "相对链接目标不存在"))

        for m in IMG_LINK.finditer(body):
            src = m.group(1)
            if src.startswith(("http://", "https://", "data:")):
                continue
            target = (path.parent / urllib.parse.unquote(src)).resolve()
            if not target.exists():
                problems.append((path, src, "图片不存在"))

    return problems


class BuiltPage(HTMLParser):
    def __init__(self, path: Path):
        super().__init__()
        self.ids = set()
        self.links = []
        self.redirect = False
        self.feed(path.read_text(encoding="utf-8", errors="replace"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if element_id := attrs.get("id"):
            self.ids.add(element_id)
        if tag == "a" and (href := attrs.get("href")):
            self.links.append((href, "link"))
        elif tag == "img" and (src := attrs.get("src")):
            self.links.append((src, "image"))
        elif tag == "link" and attrs.get("rel") == "canonical" and (href := attrs.get("href")):
            self.links.append((href, "metadata"))
        elif tag == "meta" and attrs.get("property") == "og:url" and (url := attrs.get("content")):
            self.links.append((url, "metadata"))
        elif tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            if match := re.fullmatch(r"\s*\d+;\s*url=(.+)", attrs.get("content", ""), re.I):
                self.redirect = True
                self.links.append((match[1], "link"))


def built_base_url():
    config = (ROOT / "quartz.config.ts").read_text(encoding="utf-8")
    match = re.search(r"""^\s*baseUrl:\s*["']([^"']+)["']""", config, re.M)
    if not match:
        return None
    url = urllib.parse.urlsplit(f"https://{match[1]}")
    return url if url.hostname else None


def feed_urls(path: Path):
    if path.name == "sitemap.xml":
        selector = ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
    else:
        selector = ".//link"
    root = ET.parse(path)
    return [(node.text.strip(), "metadata") for node in root.findall(selector) if node.text]


def legacy_output_name(source: str) -> str:
    slug = re.sub(r"\s", "-", source).replace("&", "-and-").replace("%", "-percent")
    slug = slug.replace("?", "").replace("#", "")
    return slug.removesuffix(".md") + ".html" if slug.endswith(".md") else slug


def check_built():
    public = ROOT / "public"
    if not public.is_dir():
        print("public/ 不存在，请先运行 pnpm build")
        return None

    base = built_base_url()
    if base is None:
        print("quartz.config.ts 缺少完整站点 baseUrl")
        return None

    files = {path.relative_to(public).as_posix() for path in public.rglob("*") if path.is_file()}
    pages = {name: BuiltPage(public / name) for name in sorted(files) if name.endswith(".html")}
    if "index.html" not in pages:
        print("public/index.html 不存在，请先运行 pnpm build")
        return None

    problems = []
    references = {name: page.links for name, page in pages.items()}
    for name in ("sitemap.xml", "index.xml"):
        try:
            references[name] = feed_urls(public / name)
        except (OSError, ET.ParseError):
            problems.append((public / name, name, "Sitemap 或 RSS 产物缺失或无效"))

    base_path = base.path.rstrip("/")
    # On macOS, legacy aliases or tags can share an output file with the canonical spelling.
    # On GitHub Actions' Linux filesystem, each URL must have an exact match.
    folded_files = {}
    if (public / "INDEX.HTML").is_file():
        folded_files = {name.casefold(): name for name in files}
    else:
        legacy_paths = ROOT / "quartz/legacy-ai-paths.json"
        if legacy_paths.is_file():
            for old_path in json.loads(legacy_paths.read_text(encoding="utf-8")):
                output = legacy_output_name(old_path)
                if output not in files or (output in pages and not pages[output].redirect):
                    problems.append((public / output, old_path, "历史 URL 缺少重定向或附件产物"))
    for name, links in references.items():
        page_url = f"https://{base.netloc}{base_path}/{urllib.parse.quote(name)}"
        redirect = name in pages and pages[name].redirect
        for href, kind in links:
            # Browsers resolve generated links from the current page, including the Pages subpath.
            url = urllib.parse.urlsplit(urllib.parse.urljoin(page_url, href))
            if kind == "metadata" and not redirect:
                if url.netloc != base.netloc or not href.startswith(f"https://{base.netloc}/"):
                    problems.append((public / name, href, "页面元数据 URL 必须使用部署站点的 HTTPS 地址"))
                    continue
            elif url.scheme not in {"http", "https"} or url.netloc != base.netloc:
                continue

            path = posixpath.normpath(urllib.parse.unquote(url.path))
            if path == base_path or path.startswith(f"{base_path}/"):
                relative = path[len(base_path):].lstrip("/")
                candidates = [relative]
                if kind != "image":
                    candidates.extend([posixpath.join(relative, "index.html"), f"{relative}.html"])
                target = next((candidate for candidate in candidates if candidate in files), None)
                if target is None and folded_files:
                    target = next(
                        (
                            folded_files[candidate.casefold()]
                            for candidate in candidates
                            if candidate.casefold() in folded_files
                        ),
                        None,
                    )
            else:
                target = None

            if target is None:
                reason = "图片在产物中不存在" if kind == "image" else "目标页不存在"
                problems.append((public / name, href, reason))
                continue
            anchor = urllib.parse.unquote(url.fragment)
            if anchor and target in pages and anchor not in pages[target].ids:
                problems.append((public / name, href, "目标页锚点不存在"))

    return problems


def main() -> int:
    built = "--built" in sys.argv
    problems = check_built() if built else check_static()
    if problems is None:
        return 1

    label = "构建产物" if built else "静态源文件"
    print(f"检查范围: {label}")

    if not problems:
        print("链接检查通过：0 处断链")
        return 0

    # 按源文件聚合，便于分批修复
    grouped = {}
    for path, ref, reason in problems:
        grouped.setdefault(str(path.relative_to(ROOT)), []).append((ref, reason))

    for src, items in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        print(f"\n{src}  ({len(items)} 处)")
        for ref, reason in items[:10]:
            print(f"    {ref}   [{reason}]")
        if len(items) > 10:
            print(f"    ... 另有 {len(items) - 10} 处")

    print(f"\n合计 {len(problems)} 处问题，涉及 {len(grouped)} 个文件")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
