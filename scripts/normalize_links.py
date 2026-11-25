#!/usr/bin/env python3
"""把 wikilink / md 链接统一改写成「内容根路径」形式。

背景：Quartz 把带斜杠的 wikilink 目标当作内容根相对路径解析，而 Obsidian
把它当作当前文件相对路径。两侧语义不一致，导致 [[python/index]] 这类写法
在 Obsidian 里能跳、在站点上是死链。

统一改写为 [[02-backend/python/index|别名]]（从内容根写起的完整路径），
Obsidian 与 Quartz 都能正确解析。

用法：
  python3 scripts/normalize_links.py --dry-run   # 只报告
  python3 scripts/normalize_links.py --apply     # 实际写入
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 与 quartz.config.ts 的 ignorePatterns 对齐：这些文件不发布，链接过去必然是死链
# （.agents 为技能包自带文档，用相对链接是正确形态，不做 wikilink 化改写）
SKIP_DIRS = {
    "node_modules", "public", "quartz", ".git", ".obsidian", ".workbuddy",
    "templates", "Clippings", "copilot", "private", "prompt", ".github",
    ".agents", "inbox",
}
SKIP_FILES = {"AGENTS.md", "todo.md"}

WIKI = re.compile(r"\[\[([^\]\n]+)\]\]")
MDLINK = re.compile(r"(?<!!)\[([^\]\n]*)\]\(([^)\s]+\.md)(#[^)]*)?\)")


def collect(root: Path) -> dict[str, Path]:
    """md 文件的内容根路径（不含扩展名）-> 文件。"""
    out = {}
    for p in root.rglob("*.md"):
        if set(p.parts) & SKIP_DIRS:
            continue
        if p.name in SKIP_FILES:
            continue
        out[p.relative_to(root).as_posix()[:-3]] = p
    return out


def resolve(target: str, src: Path, root: Path, index: dict[str, Path]) -> str | None:
    """把链接目标解析成内容根路径；解析不到返回 None。"""
    target = target.strip().lstrip("/")
    if not target:
        return None

    # 1. 相对当前文件所在目录（Obsidian 语义）
    rel = (src.parent.relative_to(root) / target).as_posix()
    rel = re.sub(r"/\./", "/", rel)
    parts: list[str] = []
    for seg in rel.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg not in ("", "."):
            parts.append(seg)
    cand = "/".join(parts)
    if cand in index:
        return cand

    # 2. 内容根相对（Quartz 语义）
    if target in index:
        return target

    # 3. 同目录下同名
    same = (src.parent.relative_to(root) / target).as_posix()
    if same in index:
        return same

    # 4. 全库后缀匹配，唯一命中才采用
    hits = [k for k in index if k == target or k.endswith("/" + target)]
    if len(hits) == 1:
        return hits[0]
    return None


def rewrite_line(line: str, src: Path, root: Path, index: dict[str, Path],
                 changes: list[tuple[str, str, str]]) -> str:
    def do_wiki(m: re.Match) -> str:
        raw = m.group(1)
        head, sep, tail = raw.partition("|")
        anchor = ""
        if "#" in head:
            head, anchor = head.split("#", 1)
            anchor = "#" + anchor
        name = head.rstrip("\\").strip()
        if not name:
            return m.group(0)
        resolved = resolve(name, src, root, index)
        if resolved is None or resolved == name:
            return m.group(0)
        if "/" not in name and name not in AMBIGUOUS:
            return m.group(0)      # 裸名本来就能解析，不动
        new = f"[[{resolved}{anchor}{sep}{tail}]]"
        changes.append((str(src.relative_to(root)), m.group(0), new))
        return new

    def do_md(m: re.Match) -> str:
        text, path, tail = m.group(1), m.group(2), m.group(3) or ""
        target = path[:-3]
        resolved = resolve(target, src, root, index)
        if resolved is None:
            return m.group(0)
        # 已经是内容根路径就不动
        if path == resolved + ".md":
            return m.group(0)
        new = f"[[{resolved}{tail}|{text}]]" if text else f"[[{resolved}{tail}]]"
        changes.append((str(src.relative_to(root)), m.group(0), new))
        return new

    line = WIKI.sub(do_wiki, line)
    return MDLINK.sub(do_md, line)


# 全库重名、Quartz 最短名解析会选错的裸名 -> 必须带路径
AMBIGUOUS: set[str] = set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        ap.error("必须指定 --dry-run 或 --apply")

    root = Path(".").resolve()
    index = collect(root)

    from collections import Counter
    stems = Counter(p.stem for p in index.values())
    AMBIGUOUS.update(s for s, n in stems.items() if n > 1)

    total = 0
    files = 0
    for vpath, path in sorted(index.items()):
        src_text = path.read_text(encoding="utf-8", errors="ignore")
        out, changed = [], []
        # 跳过围栏代码与行内代码
        for seg in re.split(r"(```.*?```|`[^`\n]*`)", src_text, flags=re.S):
            if seg.startswith("`"):
                out.append(seg)
                continue
            out.append("\n".join(
                rewrite_line(l, path, root, index, changed) for l in seg.split("\n")
            ))
        if changed:
            files += 1
            total += len(changed)
            print(f"[{vpath}.md] {len(changed)} 处")
            for _, old, new in changed:
                print(f"    - {old}")
                print(f"    + {new}")
            if args.apply:
                path.write_text("".join(out), encoding="utf-8")

    print(f"\n{'已改写' if args.apply else '待改写'}: {total} 处，涉及 {files} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
