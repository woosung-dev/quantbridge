#!/usr/bin/env python3
"""문서의 CSS 좌표 드리프트와 죽은 문서 경로를 작게 감사한다."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = Path("tools/scripts/doc-coord-audit.baseline.json")

# 가드레일 4축(CONTEXT.md, AGENTS.md, apps/api/AGENTS.md, apps/web/AGENTS.md)은 lane이
# 고칠 수 없는 파일이다. 수정 가능한 DESIGN.md와 반응형 spec만 시작 대상으로 둔다.
COORDINATE_TARGETS = (
    Path("DESIGN.md"),
    Path("apps/web/e2e/design-canon-responsive.spec.ts"),
)
DEAD_PATH_SOURCE_ROOTS = (
    Path("docs"),
    Path("apps/web/src"),
    Path("apps/api/src"),
)
RETIRED_DOCUMENT_BASENAMES = frozenset({"frontend.md", "nextjs-shared.md"})

FULL_COORDINATE_RE = re.compile(r"(?<![\w.-])globals\.css:\d+(?:-\d+)?")
RELATIVE_COORDINATE_RE = re.compile(r"`:\d+(?:-\d+)?`")
MARKDOWN_PATH_RE = re.compile(
    r"(?<![\w./-])(?P<path>(?:\.\.?/)?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.md)(?![\w/-])"
)
GIT_SHOW_PREFIX_RE = re.compile(r"\bgit\s+show\s+[^\s`]+:$")
GIT_SHA_CONTEXT_RE = re.compile(r"\bgit:[0-9a-f]{7,40}\s+$", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    text: str


def find_coordinate_findings(paths: Iterable[Path]) -> list[Finding]:
    """`globals.css` 좌표와 같은 문단 안의 단독 좌표를 찾는다."""
    findings: list[Finding] = []

    for path in paths:
        has_globals_context = False
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                has_globals_context = False
                continue

            for match in FULL_COORDINATE_RE.finditer(line):
                findings.append(Finding(path, line_number, match.group(0)))

            line_has_globals_context = has_globals_context or "globals.css" in line
            if line_has_globals_context:
                for match in RELATIVE_COORDINATE_RE.finditer(line):
                    findings.append(Finding(path, line_number, match.group(0)))

            has_globals_context = line_has_globals_context

    return findings


def print_coordinate_findings(findings: list[Finding]) -> None:
    if not findings:
        print("✓ globals.css 줄 번호 인용 0건")
        return

    print(f"✗ globals.css 줄 번호 인용 {len(findings)}건")
    for finding in findings:
        print(f"  {relative_to_root(finding.path)}:{finding.line}: {finding.text}")


def relative_to_root(path: Path) -> Path:
    return path.resolve().relative_to(REPO_ROOT)


def target_paths(only: str | None) -> tuple[Path, ...]:
    if only is None:
        return tuple(REPO_ROOT / target for target in COORDINATE_TARGETS)

    requested = Path(only)
    if requested.is_absolute():
        try:
            requested = requested.resolve().relative_to(REPO_ROOT)
        except ValueError as error:
            raise ValueError(f"--only 경로가 레포 밖이다: {only}") from error

    if requested not in COORDINATE_TARGETS:
        targets = ", ".join(str(path) for path in COORDINATE_TARGETS)
        raise ValueError(f"--only 는 감사 대상만 받을 수 있다: {targets}")
    return (REPO_ROOT / requested,)


def load_baseline() -> dict[str, int]:
    path = REPO_ROOT / BASELINE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"baseline 파일이 없다: {BASELINE_PATH}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"baseline JSON 이 올바르지 않다: {BASELINE_PATH}") from error

    counts = payload.get("violations_by_file")
    expected_paths = {str(target) for target in COORDINATE_TARGETS}
    if not isinstance(counts, dict) or set(counts) != expected_paths:
        raise ValueError("baseline violations_by_file 이 감사 대상 전체와 일치하지 않는다")
    if not all(isinstance(count, int) and count >= 0 for count in counts.values()):
        raise ValueError("baseline 위반 수는 0 이상의 정수여야 한다")
    if sum(counts.values()) == 0:
        raise ValueError("착수 baseline 위반 수가 0건이다 — 감사기가 대상에 닿지 않았을 수 있다")
    return counts


def run_check(*, only: str | None, baseline: bool) -> int:
    paths = target_paths(only)
    findings = find_coordinate_findings(paths)
    print_coordinate_findings(findings)

    if not baseline:
        return 0 if not findings else 1

    if only is not None:
        raise ValueError("--baseline 과 --only 는 함께 쓸 수 없다")

    actual = Counter(str(relative_to_root(finding.path)) for finding in findings)
    expected = load_baseline()
    actual_by_file = {str(target): actual[str(target)] for target in COORDINATE_TARGETS}
    if actual_by_file == expected:
        print("✓ baseline 일치 (파일별 위반 수 정확 동등)")
        return 0

    print("✗ baseline 불일치")
    for target in COORDINATE_TARGETS:
        key = str(target)
        print(f"  {key}: expected={expected[key]}, actual={actual_by_file[key]}")
    return 1


def iter_documentation_source_lines() -> Iterable[tuple[Path, int, str]]:
    for source_root in DEAD_PATH_SOURCE_ROOTS:
        absolute_root = REPO_ROOT / source_root
        for path in absolute_root.rglob("*"):
            if not path.is_file():
                continue
            if source_root == Path("docs"):
                if path.suffix != ".md":
                    continue
                include_all_lines = True
            else:
                if path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"} and path.name != ".gitkeep":
                    continue
                include_all_lines = False

            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                stripped = line.lstrip()
                is_comment = stripped.startswith(("#", "//", "/*", "*", "*/"))
                if include_all_lines or is_comment:
                    yield path, line_number, line


def is_retired_document_path(candidate: str) -> bool:
    return candidate == "frontend/AGENTS.md" or Path(candidate).name in RETIRED_DOCUMENT_BASENAMES


def is_historical_reference(line: str, start: int) -> bool:
    prefix = line[:start]
    return bool(GIT_SHOW_PREFIX_RE.search(prefix) or GIT_SHA_CONTEXT_RE.search(prefix))


def find_dead_path_findings() -> list[Finding]:
    findings: list[Finding] = []
    for source_path, line_number, line in iter_documentation_source_lines():
        for match in MARKDOWN_PATH_RE.finditer(line):
            candidate = match.group("path")
            if not is_retired_document_path(candidate) or is_historical_reference(line, match.start()):
                continue
            findings.append(Finding(source_path, line_number, candidate))
    return findings


def run_dead_paths() -> int:
    findings = find_dead_path_findings()
    if not findings:
        print("✓ 철거된 FE 규칙 문서 경로 0건")
        return 0

    print(f"✗ 철거된 FE 규칙 문서 경로 {len(findings)}건")
    for finding in findings:
        print(f"  {relative_to_root(finding.path)}:{finding.line}: {finding.text}")
    return 1


def run_selftest() -> int:
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        positive_full = root / "positive-full.md"
        positive_context = root / "positive-context.md"
        negative_anchor = root / "negative-anchor.md"
        negative_unrelated = root / "negative-unrelated.md"
        positive_full.write_text("globals.css:999\n", encoding="utf-8")
        positive_context.write_text("`globals.css` 문맥의 `:999`\n", encoding="utf-8")
        negative_anchor.write_text("`globals.css` 의 `--sidebar-w` 선언\n", encoding="utf-8")
        negative_unrelated.write_text("`execute.py:44`\n", encoding="utf-8")

        cases = (
            ("globals.css:999 양성", positive_full, 1),
            ("globals.css 문맥 `:999` 양성", positive_context, 1),
            ("앵커 형태 음성", negative_anchor, 0),
            ("무관 파일 좌표 음성", negative_unrelated, 0),
        )
        failed = False
        for label, path, expected_count in cases:
            actual_count = len(find_coordinate_findings((path,)))
            if actual_count == expected_count:
                print(f"✓ selftest {label}")
                continue
            print(f"✗ selftest {label}: expected={expected_count}, actual={actual_count}")
            failed = True
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="globals.css 줄 번호 인용을 검사한다")
    mode.add_argument("--dead-paths", action="store_true", help="철거된 FE 규칙 문서 경로를 검사한다")
    mode.add_argument("--selftest", action="store_true", help="검사기의 양성·음성 판별력을 증명한다")
    parser.add_argument("--baseline", action="store_true", help="동결한 파일별 위반 수와 정확히 대조한다")
    parser.add_argument("--only", help="globals.css 좌표 감사 대상 하나만 검사한다")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if (args.baseline or args.only) and not args.check:
        raise ValueError("--baseline 과 --only 는 --check 에서만 쓸 수 있다")
    if args.baseline and args.only:
        raise ValueError("--baseline 과 --only 는 함께 쓸 수 없다")
    if args.selftest:
        return run_selftest()
    if args.dead_paths:
        return run_dead_paths()
    return run_check(only=args.only, baseline=args.baseline)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"사용법 오류: {error}", file=sys.stderr)
        raise SystemExit(2) from error
