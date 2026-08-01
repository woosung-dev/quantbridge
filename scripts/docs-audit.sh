#!/usr/bin/env bash
# 활성 문서의 링크와, 구조 개편 때 폐기한 경로의 재유입만 검사한다.
# archive/dev-log/reports는 각각 읽기 전용 이력·append-only 기록·생성물이므로 대상에서 뺀다.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
docs = root / "docs"
frozen = (docs / "archive", docs / "dev-log", docs / "reports")
skip_dirs = {
    ".git", ".claude", ".next", ".turbo", ".venv", "__pycache__", "node_modules",
    "dist", "coverage", "playwright-report", "test-results",
}
text_suffixes = {".css", ".html", ".js", ".json", ".md", ".mjs", ".py", ".sh", ".ts", ".tsx", ".yaml", ".yml"}
link_re = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def is_frozen(path: Path) -> bool:
    return any(path.is_relative_to(directory) for directory in frozen)


def text_files(start: Path):
    if start.is_file():
        yield start
        return
    for directory, names, filenames in __import__("os").walk(start):
        names[:] = [
            name for name in names
            if name not in skip_dirs and not name.startswith(".next")
        ]
        base = Path(directory)
        if is_frozen(base):
            names[:] = []
            continue
        for filename in filenames:
            path = base / filename
            if path.suffix in text_suffixes or path.name in {"Makefile", "Dockerfile"}:
                yield path


broken_links: list[tuple[Path, str]] = []
markdown_roots = [
    docs,
    root / "README.md",
    root / "AGENTS.md",
    root / "CONTEXT.md",
    root / "DESIGN.md",
    root / "backend" / "README.md",
    root / "frontend" / "README.md",
]
for start in markdown_roots:
    for path in text_files(start):
        if path.suffix != ".md" or not path.exists() or is_frozen(path):
            continue
        text = path.read_text(errors="ignore")
        for raw_target in link_re.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http:", "https:", "mailto:", "tel:")):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).resolve().exists():
                broken_links.append((path.relative_to(root), target))

# 이번 lifecycle 재편에서 사라진 위치. archive/dev-log/reports는 과거 원문이므로 검사하지 않는다.
legacy_paths = {
    "docs/reference/infra/": "docs/reference/operations/ 또는 docs/archive/operations/",
    "docs/reference/project/": "docs/reference/product/ 또는 docs/archive/product/",
    "docs/reference/observability/": "docs/reference/operations/ 또는 docs/archive/operations/",
    "docs/reference/prototypes/": "docs/reference/design/prototypes/",
    "docs/reference/worktree-parallel.md": "docs/reference/operations/worktree-parallel.md",
    "docs/reference/supported-indicators.md": "docs/reference/domain/supported-indicators.md",
    "docs/reference/architecture-conformance.md": "docs/archive/architecture/2026-05-29-architecture-conformance-audit.md",
    "docs/reference/pine-coverage-assignment.md": "docs/archive/domain/2026-04-14-pine-coverage-assignment.md",
    "docs/reference/pine-script-analysis.md": "docs/archive/domain/2026-04-14-pine-script-analysis.md",
    "docs/guides/": "docs/reference/operations/workflows/",
}
legacy_hits: list[tuple[Path, str, str]] = []
audit_script = root / "scripts" / "docs-audit.sh"
for start in (docs, root / "backend", root / "frontend", root / "scripts", root / "Makefile", root / "docker-compose.isolated.yml"):
    if not start.exists():
        continue
    for path in text_files(start):
        if is_frozen(path) or path == audit_script:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for legacy, replacement in legacy_paths.items():
            if legacy in text:
                legacy_hits.append((path.relative_to(root), legacy, replacement))

if broken_links:
    print("▶ Broken active Markdown links")
    for path, target in broken_links:
        print(f"  {path}: {target}")

if legacy_hits:
    print("▶ Retired documentation paths in active files")
    for path, legacy, replacement in legacy_hits:
        print(f"  {path}: {legacy} → {replacement}")

if broken_links or legacy_hits:
    print(f"✗ docs-audit failed: links={len(broken_links)}, retired_paths={len(legacy_hits)}")
    raise SystemExit(1)

print("✓ docs-audit: active Markdown links and retired paths are clean")
PY
