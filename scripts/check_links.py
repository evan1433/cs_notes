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

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 与 quartz.config.ts 的 ignorePatterns 保持一致：这些目录不参与发布，
# 里面的链接不会渲染成页面链接，因此不需要修。
SKIP_DIRS = {
    "node_modules", "public", "quartz", ".git", ".github", ".obsidian",
    ".devcontainer", ".workbuddy", "templates", "Clippings", "copilot",
    "private", "prompt",
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


def ids_of(page: Path, cache: dict) -> set:
    if page not in cache:
        html = page.read_text(encoding="utf-8", errors="ignore")
        cache[page] = set(re.findall(r'id="([^"]+)"', html))
    return cache[page]


def check_built():
    public = ROOT / "public"
    if not public.is_dir():
        print("public/ 不存在，请先运行 pnpm build")
        return None

    problems, cache = [], {}
    pages = list(public.rglob("*.html"))

    for page in pages:
        html = page.read_text(encoding="utf-8", errors="ignore")
        for href in re.findall(r'<a[^>]*href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            path, _, anchor = href.partition("#")
            anchor = urllib.parse.unquote(anchor)
            path = urllib.parse.unquote(path)

            if not path:                     # 同页锚点
                if anchor and anchor not in ids_of(page, cache):
                    problems.append((page, href, "同页锚点不存在"))
                continue

            target = (page.parent / path).resolve()
            # 注意：必须用「追加 .html」而不是 with_suffix，否则
            # agent.excalidraw → agent.html 会误判为断链
            if not target.exists():
                appended = type(target)(str(target) + ".html")
                if appended.exists():
                    target = appended
            if not target.exists() and (target / "index.html").exists():
                target = target / "index.html"
            if not target.exists():
                problems.append((page, href, "目标页不存在"))
                continue
            if anchor and anchor not in ids_of(target, cache):
                problems.append((page, href, "目标页锚点不存在"))

        for src in re.findall(r'<img[^>]+src="([^"]+)"', html):
            if src.startswith(("http://", "https://", "data:")):
                continue
            if not (page.parent / urllib.parse.unquote(src)).resolve().exists():
                problems.append((page, src, "图片在产物中不存在"))

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
