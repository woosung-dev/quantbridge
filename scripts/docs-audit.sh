#!/usr/bin/env bash
# 활성 문서의 링크와, 구조 개편 때 폐기한 경로의 재유입만 검사한다.
# archive/dev-log/reports는 각각 읽기 전용 이력·append-only 기록·생성물이므로 대상에서 뺀다.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
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

# ── 줄 길이 상한 ────────────────────────────────────────────────
# 왜 있나 (2026-08-02 context-budget-repair 실측):
#   grep 은 매치된 **줄 전체**를 준다. 그래서 긴 줄 하나가 곧 대량 읽기다.
#   `INDEX.md` 는 205,511자를 208줄에 담고 있었고(줄 하나 최대 4,607자),
#   직전 회차의 `head -20 INDEX.md; grep …` **한 번이 16,104자**를 물어
#   그 세션 최대 단일 tool_result 였다. 기록된 규율은 안 지켜진다 — 게이트로 막는다.
# ★`docs/dev-log` 는 위 링크 검사에서 frozen 으로 빠지지만, `INDEX.md` 는
#   append-only 이력이 아니라 **매 세션 읽히는 인덱스**다. 여기서는 명시 대상으로 넣는다.
# ★문자 수로 잰다. `awk length()` 는 로케일에 따라 바이트를 세어 한국어에서 1.4배 부풀린다.
line_caps = {
    "docs/dev-log/INDEX.md": 300,
    "docs/backlog.md": 1000,
    "docs/roadmap.md": 1000,
}
cap_hits: list[tuple[str, int, int, int]] = []
for rel, cap in line_caps.items():
    path = root / rel
    if not path.exists():
        continue
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
        if len(line) > cap:
            cap_hits.append((rel, lineno, len(line), cap))

# ── 파일 줄 수 상한 ────────────────────────────────────────────
# ★위 `line_caps` 는 **한 줄의 문자 수** 상한이다. 여기 `file_line_caps` 는 **파일 전체의 줄 수**
#   상한 — 이름이 비슷하지만 재는 양이 다르다. 헷갈리면 둘 중 하나가 조용히 무의미해진다.
# 왜 있나: `docs/lessons.md` 는 자기 머리글에 「본 파일 한계 400 lines」를 적어두고도
#   **어떤 게이트도 그걸 강제하지 않았다.** 기록된 규율은 안 지켜진다 — 게이트로 막는다
#   (ADR-026 §3: 회고는 반증 카드 → lessons 승격 → 넘치면 archive 강등).
# ★상한을 올려 통과시키지 마라. 넘쳤다는 것은 승격 대상이 밀렸다는 신호다.
file_line_caps = {
    "docs/lessons.md": 400,
}
file_len_hits: list[tuple[str, int, int]] = []
for rel, cap in file_line_caps.items():
    path = root / rel
    if not path.exists():
        continue
    count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if count > cap:
        file_len_hits.append((rel, count, cap))

# ── 소유자 없는 검사기 — 존재 + 기동 가능 확인 ─────────────────
# 왜 있나 (BL-631 · LESSON-078):
#   `runtime-check.mjs` 는 `pnpm test` · CI · docs-audit 어디도 부르지 않았다. 그래서 docs/ 재편
#   커밋 fcc36bf7 이 이 파일을 두 단계 깊은 곳으로 옮겼을 때 playwright import 의 상대 깊이가
#   안 따라와 `ERR_MODULE_NOT_FOUND` 로 **기동조차 못 하는 채** 방치됐고, 그 사이 문서는
#   「17벌 17/17 PASS」를 계속 인용했다. 뿌리는 경로가 아니라 **소유자 부재**다.
# ★여기서 playwright 브라우저를 띄우지 않는다 — docs-audit 은 빠른 게이트다.
#   재는 것은 셋뿐이다: ⑴ 파일이 실재하는가 ⑵ 문법이 파싱되는가 ⑶ 임포트 대상이 디스크에 있는가.
#   ⑶ 이 정확히 위 사고의 모양이다 — 문법은 멀쩡했고 **해석**만 깨져 있었다.
# ★`regen_golden.py --check` 를 여기서 **실행하지는 않는다** — 그건 골든 케이스 전량 백테스트라
#   빠른 게이트가 아니고 backend 가상환경(pandas·uv)을 요구한다. 여기서 막는 것은 그 앞 단계,
#   즉 "부르려는 순간 ImportError 로 죽는" 상태다. 실행 소유자는 별도 게이트가 맡아야 한다.
# ★`node` 가 없으면 **실패**로 올린다(측정불가 ≠ 통과). 조용히 건너뛰면 검사가 죽은 줄도 모른다.
#   [가정] GitHub `ubuntu-latest` 러너 이미지에는 node 가 PATH 에 있다 — 이 레포에서 실행으로
#   확인한 적은 없다. 만약 CI `documentation` job 이 여기서 빨개지면 그 job 에
#   `actions/setup-node` 를 더해라. 상한처럼 **검사를 끄지 마라.**
# ★`frontend/node_modules` 미설치는 이 게이트의 책임이 아니다(CI `documentation` job 은
#   pnpm install 을 안 한다). 끊긴 지점이 없는 `node_modules` 자체면 건너뛰고,
#   그 위쪽(= 상대 깊이)이 끊겼으면 실패로 올린다. 둘을 구분하는 것이 이 검사의 핵심이다.
orphan_tools = [
    {
        "path": "docs/reference/design/prototypes/shotgun-2026-07/runtime-check.mjs",
        "why": "프로토타입·앱 런타임 검사기 (BL-631)",
    },
    {
        "path": "backend/scripts/regen_golden.py",
        "why": "백테스트 골든 재생성/대조기 `--check` (BL-631 계열)",
        "import_root": "backend",
        "packages": ("src", "scripts", "tests"),
    },
]

orphan_hits: list[tuple[str, str]] = []


def first_missing(target: Path) -> Path:
    """존재하지 않는 target 에서 **처음으로 없어지는** 조상을 돌려준다 (부모는 실재)."""
    probe = target
    while probe != probe.parent and not probe.parent.exists():
        probe = probe.parent
    return probe


def check_mjs(rel: str, path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        # ★측정불가는 통과가 아니다. 조용히 건너뛰면 이 축이 죽은 검사가 된다.
        orphan_hits.append((rel, "node 를 찾을 수 없어 문법을 재지 못했다 (측정불가 = 실패)"))
    else:
        done = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
        if done.returncode != 0:
            orphan_hits.append((rel, f"node --check 실패: {done.stderr.strip().splitlines()[0] if done.stderr.strip() else done.returncode}"))
    text = path.read_text(encoding="utf-8", errors="replace")
    for spec in re.findall(r"""(?:from|import)\s*\(?\s*['"](\.[^'"]+)['"]""", text):
        target = (path.parent / spec).resolve()
        if target.exists():
            continue
        missing = first_missing(target)
        if missing.name == "node_modules":
            continue  # 의존성 미설치 — 이 게이트의 책임이 아니다
        orphan_hits.append((rel, f"import '{spec}' 이 해석되지 않는다 (끊긴 지점: {missing})"))


def check_py(rel: str, path: Path, import_root: Path, packages: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        compile(text, str(path), "exec")
    except SyntaxError as exc:
        orphan_hits.append((rel, f"파이썬 문법 오류: {exc.msg} (line {exc.lineno})"))
        return
    for dotted in re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", text, re.MULTILINE):
        head = dotted.split(".", 1)[0]
        if head not in packages:
            continue  # 서드파티·표준 라이브러리는 여기서 재지 않는다
        base = import_root.joinpath(*dotted.split("."))
        if base.with_suffix(".py").exists() or (base / "__init__.py").exists():
            continue
        orphan_hits.append((rel, f"import '{dotted}' 이 {import_root.name}/ 아래에 없다"))


for tool in orphan_tools:
    rel = str(tool["path"])
    path = root / rel
    if not path.exists():
        orphan_hits.append((rel, f"파일이 없다 — {tool['why']}"))
        continue
    if path.suffix == ".mjs":
        check_mjs(rel, path)
    elif path.suffix == ".py":
        check_py(rel, path, root / str(tool["import_root"]), tuple(tool["packages"]))
    else:
        # ★모르는 확장자를 조용히 통과시키면 표에 줄을 더하는 것만으로 검사가 꺼진다.
        orphan_hits.append((rel, f"'{path.suffix}' 를 기동 확인할 줄 모른다 — 검사 분기를 먼저 추가해라"))

# ── dev-log/INDEX.md 의 링크 ────────────────────────────────────
# 위 링크 검사는 `docs/dev-log` 를 frozen 으로 스킵한다(append-only 이력이라). 그런데 INDEX.md 는
# 이력이 아니라 **매 세션 읽히는 색인**이고, 2026-08-02 압축 이후 상세의 상당수가
# `docs/archive/dev-log/index-full-2026-08-02.md` 링크 너머에 있다. 그 링크가 깨지면
# 「압축이 곧 삭제」가 되는데 어떤 게이트도 물지 않았다 — 명시 대상으로 넣는다.
index_md = docs / "dev-log" / "INDEX.md"
if index_md.exists():
    text = index_md.read_text(encoding="utf-8", errors="replace")
    for raw_target in link_re.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if not target or target.startswith(("#", "http:", "https:", "mailto:", "tel:")):
            continue
        target = target.split("#", 1)[0]
        if target and not (index_md.parent / target).resolve().exists():
            broken_links.append((index_md.relative_to(root), target))

# ── 진입점 최신성 — `docs/status.md` ([BL-643] · §G8 7필드 계약) ──────
# 왜 있나: 그 블록은 [ADR-026]·§G8 상 **다음 세션의 유일한 진입점**인데, 2026-08-08 실측에서
#   이미 끝난 일을 지시하는 「다음 행동」이 2곳 살아 있는 동안 `bl-audit`·`docs-audit` 이
#   **둘 다 exit 0** 이었다. 산문 처방은 그때가 세 번째였다(§G8 2026-07-27 · PR #562).
#
# ★★재는 것은 **구문**이지 낱말이 아니다. [BL-643] 이 기록한 초안은 「다음 행동」이라는
#   **낱말**을 셌고, 그래서 규칙을 _설명하는_ 문장("살아 있는 「다음 행동」은 0개가 정상이다")
#   까지 물어 오탐했다. 실행 지시는 레포 관례상 언제나 `다음 행동 = …` 형태다 — `=` 를 요구하면
#   설명 문장 2건이 자동으로 빠진다. 2026-08-08 음성 대조:
#     ce583eef^ (수리 전)  살아 있는 `다음 행동 =` **2건**  ← 진성 검출
#     275d76a4 / HEAD      살아 있는 `다음 행동 =` **0건**  ← 오탐 0
#
# ★★★**파일 전체로 센다 — 블록별이 아니다.** 위 2건은 서로 **다른 섹션**에 하나씩 있었다.
#   §G8 문구대로 「블록당 1개」로 세면 각 1건이라 **그 사고가 그대로 통과한다.**
#
# ★정직하게: 이것은 **모순(다중성) 탐지기이지 낡음 탐지기가 아니다.** 낡은 것이 하나뿐이면
#   여전히 통과한다. 어구를 「다음 스텝」 등으로 바꿔도 눈이 먼다([BL-643] 미탐 2종).
entry_hits: list[str] = []
status_md = docs / "status.md"
if not status_md.exists():
    entry_hits.append("docs/status.md 가 없다 — 진입점 자체가 사라졌다")
else:
    status_lines = status_md.read_text(encoding="utf-8", errors="replace").split("\n")

    # ⑴ ⓪ 다음 후보 표 — 후보가 3개 미만이면 「고르는 자리」가 아니다.
    in_zero, in_fence, candidate_rows = False, False, 0
    for line in status_lines:
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("###"):
            in_zero = line.lstrip("# ").startswith("⓪")
            continue
        if not in_zero or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= {"-", ":"} and c for c in cells):
            continue  # 구분선
        if cells and cells[0] in {"#", ""}:
            continue  # 헤더
        candidate_rows += 1
    if candidate_rows < 3:
        entry_hits.append(
            f"⓪ 다음 후보 표의 행이 {candidate_rows}개다 (계약 ≥3) — "
            "고를 수 없는 표는 진입점이 아니다"
        )

    # ⑵ 살아 있는 「다음 행동 = …」 ≤1. 취소선(`~~`) 안이면 끝난 것이다.
    live: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(status_lines, 1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for hit in re.finditer(r"다음 행동\s*(?:=|＝)", line):
            # 매치 앞의 `~~` 가 홀수면 취소선 안 — 이미 끝난 지시다.
            if line.count("~~", 0, hit.start()) % 2 == 1:
                continue
            live.append((lineno, line.strip()[:80]))
    if len(live) > 1:
        entry_hits.append(
            f"살아 있는 「다음 행동 =」이 {len(live)}개다 (계약 ≤1) — "
            "끝난 것은 `~~옛 문장~~ → 날짜 + 새 사실` 로 바꿔라"
        )
        entry_hits.extend(f"  status.md:{n}: {t}" for n, t in live)

if entry_hits:
    print("▶ 진입점 최신성 — docs/status.md 가 §G8 7필드 계약을 어긴다 ([BL-643])")
    for why in entry_hits:
        print(f"  {why}")

if broken_links:
    print("▶ Broken active Markdown links")
    for path, target in broken_links:
        print(f"  {path}: {target}")

if legacy_hits:
    print("▶ Retired documentation paths in active files")
    for path, legacy, replacement in legacy_hits:
        print(f"  {path}: {legacy} → {replacement}")

if cap_hits:
    print("▶ 줄 길이 상한 초과 (grep 한 줄이 곧 대량 읽기다)")
    for rel, lineno, length, cap in cap_hits[:20]:
        print(f"  {rel}:{lineno}: {length}자 > 상한 {cap}자")
    if len(cap_hits) > 20:
        print(f"  … 외 {len(cap_hits) - 20}줄")

if file_len_hits:
    print("▶ 파일 줄 수 상한 초과 (한 줄의 길이가 아니라 **파일 전체의 줄 수**다)")
    for rel, count, cap in file_len_hits:
        print(f"  {rel}: {count}줄 > 상한 {cap}줄 — docs/archive/ 로 승격 항목을 내려라")

if orphan_hits:
    print("▶ 소유자 없는 검사기가 기동 불가 (BL-631 — 아무도 안 부르면 죽어도 아무도 모른다)")
    for rel, why in orphan_hits:
        print(f"  {rel}: {why}")

if broken_links or legacy_hits or cap_hits or file_len_hits or orphan_hits or entry_hits:
    print(
        f"✗ docs-audit failed: links={len(broken_links)}, "
        f"retired_paths={len(legacy_hits)}, long_lines={len(cap_hits)}, "
        f"long_files={len(file_len_hits)}, orphan_tools={len(orphan_hits)}, "
        f"entry_point={len(entry_hits)}"
    )
    raise SystemExit(1)

print(
    "✓ docs-audit: active Markdown links, retired paths, line-length caps, "
    "file-length caps, orphan tool startup, status.md entry point are clean"
)
PY
