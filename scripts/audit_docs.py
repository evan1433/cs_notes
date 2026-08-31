#!/usr/bin/env python3
"""cs_notes 文档体系审计脚本。

检查内容：
  1. front matter 完整性（title / description / tags / date）
  2. 文件命名合规（英文 kebab-case，无中文无空格）
  3. 空壳文档（< 2KB 且未标记 draft，会被发布到站点）
  4. 代码块语言标注率
  5. 知识孤岛（无任何 wiki-link 的文件）
  6. 目录索引覆盖（含 2+ 篇笔记的目录缺 index.md）

用法：
  python3 scripts/audit_docs.py            # 输出完整报告
  python3 scripts/audit_docs.py --fail     # 有严重问题时返回非零退出码（可用于 CI）
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 与 quartz.config.ts ignorePatterns 保持一致，这些目录不参与发布，也无需审计
IGNORED_DIRS = {
    "node_modules", "public", "quartz", ".obsidian", ".git", ".github",
    ".workbuddy", ".codebuddy", "copilot", "prompt", "deploy", "templates",
    "Clippings", "private",
}
IGNORED_FILES = {
    "AGENTS.md", "QWEN.md", "todo.md", "readlist.md", "CONTRIBUTING.md",
    "README.md",
}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
CODE_BLOCK_RE = re.compile(r"```(\w*)")
STUB_BYTES = 2048


def audit() -> dict:
    results = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fn in filenames:
            if not fn.endswith(".md") or fn in IGNORED_FILES:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            with open(full, encoding="utf-8", errors="replace") as f:
                content = f.read()
            size = len(content.encode("utf-8"))
            m = FM_RE.match(content)
            fm = m.group(1) if m else ""
            blocks = CODE_BLOCK_RE.findall(content)
            results.append({
                "path": rel,
                "size": size,
                "has_fm": bool(m),
                "missing_title": not re.search(r"^title:", fm, re.M),
                "missing_desc": not re.search(r"^description:", fm, re.M),
                "missing_tags": not re.search(r"^tags:", fm, re.M),
                "missing_date": not re.search(r"^date:", fm, re.M),
                "draft": re.search(r"^draft:\s*true", fm, re.M) is not None,
                "naming_bad": bool(re.search(r"[\u4e00-\u9fff]", fn)) or " " in fn,
                "n_blocks": len(blocks),
                "n_no_lang": sum(1 for b in blocks if b == ""),
                "n_wikilinks": content.count("[["),
            })

    # 目录索引覆盖
    dirs_with_md = defaultdict(int)
    has_index = set()
    for r in results:
        d = os.path.dirname(r["path"])
        if d:
            dirs_with_md[d] += 1
            if os.path.basename(r["path"]) == "index.md":
                has_index.add(d)
    dirs_without_index = sorted(
        d for d, n in dirs_with_md.items() if n >= 2 and d not in has_index
    )

    stubs = [r["path"] for r in results if r["size"] < STUB_BYTES and not r["draft"]]
    total = len(results)
    return {
        "total_md": total,
        "no_front_matter": sum(1 for r in results if not r["has_fm"]),
        "missing_title": sum(1 for r in results if r["missing_title"]),
        "missing_desc": sum(1 for r in results if r["missing_desc"]),
        "missing_tags": sum(1 for r in results if r["missing_tags"]),
        "missing_date": sum(1 for r in results if r["missing_date"]),
        "naming_violations": [r["path"] for r in results if r["naming_bad"]],
        "stubs_published": stubs,
        "code_blocks_total": sum(r["n_blocks"] for r in results),
        "code_blocks_no_lang": sum(r["n_no_lang"] for r in results),
        "knowledge_islands": sum(1 for r in results if r["n_wikilinks"] == 0),
        "dirs_without_index": dirs_without_index,
        "_results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="cs_notes 文档合规审计")
    parser.add_argument("--fail", action="store_true",
                        help="存在空壳已发布文档或命名违规时返回退出码 1")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()

    s = audit()
    results = s.pop("_results")

    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0

    t = s["total_md"]
    pct = lambda n: f"{n} ({n * 100 // t}%)"
    print("=" * 62)
    print("cs_notes 文档体系审计报告")
    print("=" * 62)
    print(f"内容文件总数:        {t}")
    print(f"缺 front matter:     {pct(s['no_front_matter'])}")
    print(f"缺 title:            {pct(s['missing_title'])}")
    print(f"缺 description:      {pct(s['missing_desc'])}")
    print(f"缺 tags:             {pct(s['missing_tags'])}")
    print(f"缺 date:             {pct(s['missing_date'])}")
    print(f"知识孤岛(0 双链):    {pct(s['knowledge_islands'])}")
    print(f"代码块:              {s['code_blocks_total']} 个，"
          f"其中未标语言 {s['code_blocks_no_lang']} "
          f"({s['code_blocks_no_lang'] * 100 // max(s['code_blocks_total'], 1)}%)")
    print(f"空壳文档(<2KB 未标 draft): {len(s['stubs_published'])} 个 —— 会被发布")
    print(f"命名违规:            {len(s['naming_violations'])} 个")
    for p in s["naming_violations"][:20]:
        print(f"    - {p}")
    if len(s["naming_violations"]) > 20:
        print(f"    ... 其余 {len(s['naming_violations']) - 20} 个")
    print(f"缺索引目录(≥2篇无 index.md): {len(s['dirs_without_index'])} 个")
    for p in s["dirs_without_index"]:
        print(f"    - {p}")

    if args.fail:
        if s["stubs_published"] or s["naming_violations"]:
            print("\n[FAIL] 存在空壳已发布文档或命名违规，详见上文。")
            return 1
    print("\n提示: 修复指引见 CONTRIBUTING.md「文档质量保障」章节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
