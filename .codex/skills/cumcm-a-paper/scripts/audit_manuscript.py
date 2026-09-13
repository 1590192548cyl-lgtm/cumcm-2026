#!/usr/bin/env python3
"""Static checks for editable Chinese CUMCM manuscript sources.

Supports Markdown, TeX, and plain text. The report is advisory: official rules,
model correctness, numerical evidence, citations, and final PDF rendering still
require human or workflow-level review.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


EXPECTED_SECTIONS = {
    "abstract": re.compile(r"摘(?:\\(?:quad|hspace\{[^}]*\})|\s)*要"),
    "keywords": re.compile(r"关键词|关键字"),
    "problem": re.compile(r"问题重述|问题提出"),
    "analysis": re.compile(r"问题分析|问题重述与分析"),
    "assumptions": re.compile(r"模型假设|问题假设"),
    "symbols": re.compile(r"符号说明|符号表|主要符号"),
    "model": re.compile(r"(?:模型(?:的)?(?:建立|构建))|\\section\{[^}]*模型[^}]*\}"),
    "results": re.compile(r"结果|计算表明|模型求解"),
    "evaluation": re.compile(r"模型评价|模型的评价|模型总结|模型优点|模型局限|优缺点"),
    "references": re.compile(r"参考文献|thebibliography"),
}
PLACEHOLDER_PATTERNS = {
    "TODO/FIXME": re.compile(r"\b(?:TODO|FIXME|TBD)\b", re.I),
    "Chinese placeholder": re.compile(r"待补|待定|待验证|此处插入|尚未完成"),
    "question marks": re.compile(r"\?{3,}|？{3,}"),
    "template X": re.compile(r"(?<![A-Za-z])X{2,}(?![A-Za-z])", re.I),
}
UNICODE_MATH = re.compile(r"[∂∑∏√∞≈≠≤≥∈∫]", re.UNICODE)
ABSOLUTE_PATH = re.compile(r"/(?:Users|home|opt|var|tmp)/[^\s}\]]+")


def line_numbers(text: str, pattern: re.Pattern[str]) -> list[int]:
    return [index for index, line in enumerate(text.splitlines(), 1) if pattern.search(line)]


def extract_labels(text: str) -> tuple[list[str], list[str]]:
    labels = re.findall(r"\\label\{([^}]+)\}", text)
    refs = re.findall(r"\\(?:ref|eqref|autoref|cref|Cref)\{([^}]+)\}", text)
    return labels, refs


def audit(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    labels, refs = extract_labels(text)
    label_counts = Counter(labels)
    missing_sections = [
        key for key, pattern in EXPECTED_SECTIONS.items()
        if not pattern.search(text)
    ]
    placeholders = {
        name: line_numbers(text, pattern)
        for name, pattern in PLACEHOLDER_PATTERNS.items()
        if pattern.search(text)
    }
    unicode_math_lines = line_numbers(text, UNICODE_MATH)
    absolute_paths = sorted(set(ABSOLUTE_PATH.findall(text)))
    dollar_count = len(re.findall(r"(?<!\\)\$", text))
    begin_envs = Counter(re.findall(r"\\begin\{([^}]+)\}", text))
    end_envs = Counter(re.findall(r"\\end\{([^}]+)\}", text))

    blockers = []
    warnings = []
    if dollar_count % 2:
        blockers.append("Unbalanced unescaped '$' math delimiters.")
    if begin_envs != end_envs:
        blockers.append("LaTeX begin/end environment counts do not match.")
    if placeholders:
        blockers.append("Unresolved placeholders remain in the manuscript.")
    if set(refs) - set(labels):
        blockers.append("Some LaTeX references have no matching label.")
    if missing_sections:
        warnings.append("Expected competition-paper sections are missing; verify whether the official template or task justifies this.")
    if unicode_math_lines:
        warnings.append("Unicode math symbols found; convert formulas to LaTeX unless they occur in quoted source material.")
    if absolute_paths:
        warnings.append("Absolute filesystem paths found; use project-relative paths in repository sources.")
    if any(count > 1 for count in label_counts.values()):
        blockers.append("Duplicate LaTeX labels found.")
    if set(labels) - set(refs):
        warnings.append("Some LaTeX labels are never referenced.")

    return {
        "file": str(path),
        "characters": len(text),
        "lines": len(text.splitlines()),
        "missing_sections": missing_sections,
        "placeholders": placeholders,
        "unicode_math_lines": unicode_math_lines,
        "absolute_paths": absolute_paths,
        "latex": {
            "unescaped_dollar_count": dollar_count,
            "duplicate_labels": sorted(label for label, count in label_counts.items() if count > 1),
            "missing_labels_for_refs": sorted(set(refs) - set(labels)),
            "unreferenced_labels": sorted(set(labels) - set(refs)),
            "begin_environments": dict(begin_envs),
            "end_environments": dict(end_envs),
        },
        "figure_mentions": len(re.findall(r"图\s*\d+|Figure\s*\d+", text, re.I))
        + len(re.findall(r"\\(?:ref|autoref|cref|Cref)\{fig:[^}]+\}", text)),
        "table_mentions": len(re.findall(r"表\s*\d+|Table\s*\d+", text, re.I))
        + len(re.findall(r"\\(?:ref|autoref|cref|Cref)\{tab:[^}]+\}", text)),
        "citation_markers": len(re.findall(r"\\cite\w*\{|\[\d+(?:[-,]\d+)*\]", text)),
        "blockers": blockers,
        "warnings": warnings,
        "status": "FAIL" if blockers else "REVIEW" if warnings else "PASS_STATIC",
        "scope_note": "Static checks do not verify model correctness, numerical provenance, citation truth, official formatting, or rendered PDF quality.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manuscript", type=Path, help="Markdown, TeX, or plain-text manuscript source")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    if not args.manuscript.is_file():
        parser.error(f"not a file: {args.manuscript}")
    report = audit(args.manuscript)
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None))
    return 2 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
