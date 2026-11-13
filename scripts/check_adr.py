#!/usr/bin/env python3
"""校验 ADR（架构决策记录）的完整性。

检查四件事：
  1. 必备章节是否齐全（缺任一章说明决策没想清楚）
  2. 状态值是否合法
  3. 候选方案表是否至少 2 行（只有 1 个方案说明没做对比）
  4. 是否写明了否决理由（只写结论的 ADR 无法自我辩护）

用法：
    python3 scripts/check_adr.py sys-architect/decisions
    python3 scripts/check_adr.py sys-architect/decisions --strict   # CI 用，有问
                                                                   # 题即返回非零

退出码：0 = 全部合规；1 = 存在不完整 ADR（--strict 时任何警告也算失败）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ("背景与约束", "决策", "候选方案与否决理由", "后果", "验证方式")
VALID_STATUS = {"proposed", "accepted", "rejected", "deprecated", "superseded"}


def table_rows(section_body: str) -> int:
    """统计 markdown 表格的数据行数（剔除表头与分隔行）。"""
    rows = [ln for ln in section_body.splitlines() if ln.lstrip().startswith("|")]
    return max(len(rows) - 2, 0)


def check(path: Path) -> tuple[list[str], list[str]]:
    """返回 (错误, 警告)。错误 = 结构不合规；警告 = 质量建议。"""
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED_SECTIONS:
        if not re.search(rf"^##\s+{name}\s*$", text, re.M):
            errors.append(f"缺章节「{name}」")

    status = re.search(r"\|\s*\*\*状态\*\*\s*\|\s*([^|\n]+)", text)
    if not status:
        errors.append("缺元信息表中的「状态」行")
    else:
        # 状态允许带补充说明，如 "superseded by ADR-007"，只校验首个词
        value = status.group(1).strip().split()[0].lower()
        if value not in VALID_STATUS:
            errors.append(f"状态值非法：{value}（可选：{'/'.join(sorted(VALID_STATUS))}）")

    options = re.search(
        r"^##\s+候选方案与否决理由\s*$(.*?)(?=^##\s)", text, re.M | re.S
    )
    if options:
        if table_rows(options.group(1)) < 2:
            errors.append("候选方案少于 2 个，无法证明做过对比")
        if "否决" not in options.group(1):
            warnings.append("候选方案未写明否决理由")

    if re.search(r"^###\s+负面\s*$", text, re.M) is None:
        warnings.append("未写「负面后果」，通常意味着风险没想透")

    if not re.search(r"复审触发条件", text):
        warnings.append("未定义复审触发条件，决策将无法随约束变化而重评")

    return errors, warnings


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2

    root = Path(argv[0])
    strict = "--strict" in argv
    if not root.is_dir():
        print(f"目录不存在：{root}")
        return 2

    files = sorted(root.glob("adr-*.md"))
    if not files:
        print(f"{root} 下没有 adr-*.md")
        return 2

    failed = 0
    print(f"{'ADR':<42}{'错误':<6}{'警告':<6}")
    print("-" * 56)
    for path in files:
        errors, warnings = check(path)
        print(f"{path.name:<42}{len(errors):<6}{len(warnings):<6}")
        for item in errors:
            print(f"    [错误] {item}")
        for item in warnings:
            print(f"    [警告] {item}")
        if errors or (strict and warnings):
            failed += 1

    print("-" * 56)
    print(f"共 {len(files)} 篇，{len(files) - failed} 篇通过")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
