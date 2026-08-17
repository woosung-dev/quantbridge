#!/usr/bin/env bash
# 활성 문서의 링크와, 구조 개편 때 폐기한 경로의 재유입만 검사한다.
# archive/dev-log/reports는 각각 읽기 전용 이력·append-only 기록·생성물이므로 대상에서 뺀다.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"

# ★도구 버전 핀 — 아래 「소유자 없는 검사기」 축이 `shutil.which("node")` 로 node 를 찾고
#   `node --check` 로 문법을 잰다([BL-785]). 어느 node 냐에 따라 파싱 결과가 갈릴 수 있고,
#   PATH 에 node 가 아예 없으면 이 축은 **실패로 올라간다**(:231 주석이 그렇게 정했다).
#   mise 가 없는 셸(CI `documentation` job 포함)에서는 경고만 내고 종전대로 PATH 를 쓴다.
# shellcheck source=tools/scripts/lib/mise-shim-path.sh
. "$ROOT/tools/scripts/lib/mise-shim-path.sh"
qb_pin_tool_path || true

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
            if path.suffix in text_suffixes or path.name in {"mise.toml", "Dockerfile"}:
                yield path


broken_links: list[tuple[Path, str]] = []
markdown_roots = [
    docs,
    root / "README.md",
    root / "AGENTS.md",
    root / "CONTEXT.md",
    root / "DESIGN.md",
    root / "apps" / "api" / "README.md",
    root / "apps" / "web" / "README.md",
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
audit_script = root / "tools" / "scripts" / "docs-audit.sh"
for start in (docs, root / "apps" / "api", root / "apps" / "web", root / "tools" / "scripts", root / "mise.toml", root / "infra" / "compose" / "docker-compose.isolated.yml"):
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
    # ★[BL-779] 분할로 생긴 원장 반쪽. 상한을 안 걸면 「원장을 갈랐다」가 곧 「한쪽은 무법지대」다.
    "docs/backlog-resolved.md": 1000,
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
# ★`status.md` 는 2026-08-02 대개편에서 9,071 B 로 잘렸는데 **8일 만에 145,714 B(16배)** 가 됐다.
#   대청소는 한 번 손으로 했고 아무것도 다음 번을 예약하지 않았다 — 위 규율이 여기서 그대로 재발했다.
#   재보니 취소선(사문)은 **1.4%** 뿐이고 질량은 **끝난 회차 회고 산문**이었다. 그래서 상한이 요구하는
#   동작은 「삭제」가 아니라 **강등**이다 — ADR-026 §3 이 이미 규정한 경로(dev-log → lessons 승격 →
#   INDEX 한 줄)를 넘칠 때마다 밟게 한다. 2026-08-10 실측 = 648줄(회고 6블록 48,452자 강등 후).
file_line_caps = {
    "docs/lessons.md": 400,
    "docs/status.md": 700,
}
file_len_hits: list[tuple[str, int, int]] = []
for rel, cap in file_line_caps.items():
    path = root / rel
    if not path.exists():
        continue
    count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if count > cap:
        file_len_hits.append((rel, count, cap))

# ── lessons.md 지식 정본 — ID 유일성/오름차순 + 승격 표 포인터 ───────────
# 왜 있나 (BL-720): `lessons.md` 는 줄 수와 Markdown 링크만 검사했으므로, 승격 표에 이미
# 있는 LESSON ID 를 카드로 다시 올린 중복과 코드 스팬으로 적힌 죽은 승격 포인터가 rc=0 으로
# 통과했다. 표는 "본문은 저기 있다"는 유일한 포인터다.
# ★판정 집합은 카드 헤딩과 승격 표 **둘을 합친다**. 하나만 보면 표↔카드 중복이 다시 샌다.
# ★결번은 정상이다. 금지하는 것은 중복과 카드 헤딩의 역순뿐이다.
lesson_id_hits: list[str] = []
promotion_pointer_hits: list[tuple[str, str]] = []
lessons_md = docs / "lessons.md"
if lessons_md.exists():
    lessons_text = lessons_md.read_text(encoding="utf-8", errors="replace")
    # ★마크다운 장식을 통과시킨다 (2026-08-14 적대 프로브 P1·P2 — 둘 다 **뚫렸다**).
    #   `### [LESSON-101](#lesson-101)` 처럼 **링크로 감싸거나** `| **LESSON-101** |` 처럼
    #   **볼드로 감싸면** 종전 정규식이 ID 를 못 봤고, 그러면 중복이 그대로 통과한다 —
    #   이 축이 막으려는 사고(`8abd0d67` 의 중복 101)의 서식만 바꾼 판이다.
    #   ⇒ ID 앞의 `*`·`[`·공백은 **버린다**. 뒤의 `\b` 는 유지해 `LESSON-1010` 오인을 막는다.
    _LESSON_DECOR = r"[*\[\s]*"
    heading_ids = [
        int(raw)
        for raw in re.findall(rf"^###\s+{_LESSON_DECOR}LESSON-(\d+)\b", lessons_text, re.MULTILINE)
    ]

    # 승격 표만 고른다. 본문 전체의 코드 스팬으로 넓히면 `useEffect`·`H-1` 같은 비경로
    # 표기까지 경로 검사로 오인한다.
    promotion_ids: list[int] = []
    promotion = re.search(r"^## 영구 승격 완료(?:\s|$)", lessons_text, re.MULTILINE)
    promotion_text = ""
    if promotion:
        boundary = re.compile(r"^(?:---\s*$|## )", re.MULTILINE).search(lessons_text, promotion.end())
        promotion_text = lessons_text[promotion.end():boundary.start() if boundary else len(lessons_text)]
        for line in promotion_text.splitlines():
            # ★첫 칸에만 앵커한다 — 장식(`**`·`[`)은 통과시키되 두 번째 칸으로 넘어가지 않는다.
            row = re.match(rf"^\|{_LESSON_DECOR}LESSON-(\d+)\b", line)
            if row:
                promotion_ids.append(int(row.group(1)))

        # ★후보 규칙을 「`/` 를 포함하거나 `.md` 로 끝난다」로만 두면 **오탐 3건**이 난다
        #   (2026-08-14 실측 — 이 축의 첫 판이 정확히 그랬다):
        #     `tests/<domain>/test_*_commits.py`  = 자리표시자 + 글롭  (LESSON-019)
        #     `asyncio.<Semaphore/Lock/Event/Queue>` = 코드 표현식     (LESSON-020)
        #     `/deepen-modules`                   = 슬래시 커맨드      (LESSON-063)
        #   셋 다 **경로가 아니다**. 배제 축은 실패 축과 직교한다 — 죽은 포인터
        #   (`backend/AGENTS.md` · 오타 난 파일명 · 맨 파일명)는 여전히 전부 걸린다.
        for raw_span in re.findall(r"`([^`]+)`", promotion_text):
            candidate = raw_span.strip()
            if "/" not in candidate and not candidate.endswith(".md"):
                continue
            if any(ch in candidate for ch in "<>*?"):
                continue                      # 자리표시자·글롭은 실재를 물을 수 없다
            if candidate.startswith("/"):
                continue                      # 절대경로·슬래시 커맨드는 레포 상대 포인터가 아니다
            if not (root / candidate).exists():
                promotion_pointer_hits.append((candidate, "레포 루트 기준 파일이 없다"))

    all_ids = heading_ids + promotion_ids
    for lesson_id in sorted({value for value in all_ids if all_ids.count(value) > 1}):
        lesson_id_hits.append(
            f"  LESSON-{lesson_id:03d}: 카드 헤딩·승격 표 합계가 {all_ids.count(lesson_id)}개다 (계약 1개)"
        )
    for previous, current in zip(heading_ids, heading_ids[1:]):
        if current < previous:
            lesson_id_hits.append(
                f"  LESSON-{previous:03d} 뒤에 LESSON-{current:03d} 이 왔다 — 카드 헤딩은 오름차순이어야 한다"
            )

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
# ★`apps/web/node_modules` 미설치는 이 게이트의 책임이 아니다(CI `documentation` job 은
#   pnpm install 을 안 한다). 끊긴 지점이 없는 `node_modules` 자체면 건너뛰고,
#   그 위쪽(= 상대 깊이)이 끊겼으면 실패로 올린다. 둘을 구분하는 것이 이 검사의 핵심이다.
orphan_tools = [
    {
        "path": "docs/reference/design/prototypes/shotgun-2026-07/runtime-check.mjs",
        "why": "프로토타입·앱 런타임 검사기 (BL-631)",
    },
    {
        "path": "apps/api/scripts/regen_golden.py",
        "why": "백테스트 골든 재생성/대조기 `--check` (BL-631 계열)",
        "import_root": "apps/api",
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
# ⓪ 표의 **살아 있는** 행이 가리키는 BL id. 아래 zero_table_identity 축이 쓴다.
zero_live_ids: set[str] = set()
zero_table_seen = False
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
        zero_table_seen = True
        # ★취소선 판정은 **후보 셀만** 본다. 행 전체로 재면 다른 셀(「왜 지금」)에 적은
        #   `~~정정 이력~~` 이 살아 있는 후보를 죽은 것으로 읽는다 — 2026-08-11 에 행 G 가
        #   정확히 그 형태였다(후보는 살아 있고 사유 셀만 취소선).
        cand = cells[1] if len(cells) > 1 else ""
        if "~~" in cand:
            continue
        zero_live_ids.update(re.findall(r"BL-\d+", cand))
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
            # ★인라인 코드(백틱) 안이면 **인용**이지 지시가 아니다. 코드펜스와 같은 논리다.
            #   이 줄은 게이트가 자기 작성자를 문 자리에서 나왔다 — 이 규칙을 **설명하는** 문장이
            #   규칙 자신을 `다음 행동 =` 로 인용하는데, 그것까지 세면 규칙을 문서화할 수 없다.
            if line.count("`", 0, hit.start()) % 2 == 1:
                continue
            live.append((lineno, line.strip()[:80]))
    if len(live) > 1:
        entry_hits.append(
            f"살아 있는 「다음 행동 =」이 {len(live)}개다 (계약 ≤1) — "
            "끝난 것은 `~~옛 문장~~ → 날짜 + 새 사실` 로 바꿔라"
        )
        entry_hits.extend(f"  status.md:{n}: {t}" for n, t in live)

# ── 트리거 판정 줄 — ACTIVE/DEFERRED/PARTIAL 섹션마다 정확히 1개 ([BL-695]·[BL-703] · ADR-028 §4) ──
# 왜 있나: 2026-08-10 bl-trigger-triage 가 159/159 를 채웠지만 **그걸 지키는 것이 0** 이었다.
#   다음 회차가 BL 을 등재하면 그 줄 없이 들어가고 「159/159」는 조용히 낡는다. 이 레포는
#   「기록된 규율은 안 지켜진다」를 반복 실측했다(BL-631·LESSON-078 · line_caps 주석).
# ★판정은 `bl-audit.sh --list` 가 정본이다 — 상태줄 파서를 여기서 다시 쓰지 마라. 두 벌이 되면
#   갈라지고, 갈라지는 순간 어느 쪽이 맞는지 아무도 모른다.
# ★**정확히 1개**를 잰다. 0개(규율 누락)와 2개 이상(중복 상태줄과 같은 사고)이 둘 다 실패다.
#
# ★★원장은 **파일 하나가 아니다** ([BL-779], 2026-08-16) — `docs/backlog.md`(열린 것) +
#   `docs/backlog-resolved.md`(RESOLVED 본문). 한쪽만 읽으면 그 파일에 사는 섹션의 판정줄이
#   **0개로 세어져** 없는 위반을 만들거나(반대로) 있는 위반을 놓친다. 두 파일을 합쳐 센다.
# ★**bl-audit 의 rc 를 읽는다.** 종전에는 stdout 만 봤으므로 정본이 죽어도(빈 stdout)
#   「공집합 = 일치」로 조용히 계속 갔다. 정본이 ABORT(3) 면 여기도 ABORT 다 — 이 레포가
#   빈 입력을 「원하는 답」으로 통과시킨 사고를 다섯 번 이상 밟았다 ([LESSON-101]).
verdict_line_hits: list[str] = []
bl_audit = root / "tools" / "scripts" / "bl-audit.sh"
backlog_files = [docs / "backlog.md", docs / "backlog-resolved.md"]
by_verdict: dict[str, set[str]] = {}
verdict_text: dict[str, str] = {}

# ★**정본 스크립트가 없으면 그것도 ABORT 다** (2026-08-16 적대 리뷰 P1). 종전에는
#   `if bl_audit.exists()` 가 거짓이면 아래 두 축(트리거 판정 줄 · ⓪ 표 정체성)이 통째로
#   건너뛰어졌고, 그 상태로 「✓ … are clean」이 찍혔다 — 검사기가 사라진 것과 위반이 없는 것을
#   같은 초록으로 보고한 셈이다. 파일 부재와 rc≠0 은 같은 사건이다.
if not bl_audit.exists():
    print("▶ 원장 판정 — **판정 포기 (ABORT)**")
    print(f"  {bl_audit.relative_to(root)} 가 없다 — 판정 정본이 사라지면 위반은 「0건」이 된다")
    raise SystemExit(3)
dead = [p for p in backlog_files if not p.exists() or p.stat().st_size == 0]
if dead:
    print("▶ 원장 파일 — **판정 포기 (ABORT)**")
    for path in dead:
        print(f"  {path.relative_to(root)} 가 없거나 비었다 — 원장 반쪽이 사라지면 위반은 「0건」이 된다")
    raise SystemExit(3)
need: set[str] = set()
for verdict in ("ACTIVE", "DEFERRED", "PARTIAL"):
    proc = subprocess.run(
        ["bash", str(bl_audit), "--list", verdict],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print("▶ 원장 판정 — **판정 포기 (ABORT)**")
        print(f"  bl-audit.sh --list {verdict} 가 rc={proc.returncode} 로 죽었다 — 빈 stdout 을 공집합으로 읽지 않는다")
        for row in (proc.stderr or proc.stdout).strip().splitlines()[:5]:
            print(f"    | {row}")
        raise SystemExit(3)
    got: set[str] = set()
    for row in proc.stdout.splitlines():
        head = row.split("\t", 1)[0].strip()
        if head.startswith("BL-"):
            got.add(head)
    by_verdict[verdict] = got
    # ★2026-08-11 [BL-703] — PARTIAL 도 의무 대상이다. 종전에는 여기에
    #   `if verdict != "PARTIAL"` 가 있었고, 그래서 PARTIAL 24건이 판정줄 없이 통과했다.
    #   그 면제가 아래 zero_table_identity 의 `PARTIAL ∧ 도래` 를 **구조적 공집합**으로
    #   만들었다 — 술어는 완성돼 있는데 한쪽 입력에 데이터가 생길 수 없었다.
    need |= got

counts: dict[str, int] = {}
for ledger in backlog_files:
    section: str | None = None
    in_fence = False
    for line in ledger.read_text(encoding="utf-8", errors="replace").split("\n"):
        if re.match(r"^[ \t>]*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^### (BL-\d+)", line)
        if m:
            section = m.group(1)
            continue
        if re.match(r"^#{1,2} ", line):
            section = None
            continue
        if section and line.startswith("**트리거 판정:**"):
            counts[section] = counts.get(section, 0) + 1
            verdict_text.setdefault(section, line)

for bl in sorted(need, key=lambda x: int(x[3:])):
    n = counts.get(bl, 0)
    if n != 1:
        verdict_line_hits.append(
            f"  {bl}: `**트리거 판정:**` 줄이 {n}개다 (계약 1개) — "
            f"{'무엇이 막는지 적어라' if n == 0 else 'SSOT 는 하나여야 한다'}"
        )

# ── ⓪ 표 정체성 계약 — 살아 있는 행 == ACTIVE ∪ (PARTIAL ∧ 도래) ([BL-695] 와 같은 처방) ──
# 왜 있나: ⓪ 표 **자신이** 「이 계약에는 아직 소유자가 없다 — 다음 회차가 BL 로 등록해
#   `docs-audit` 축으로 박아라」를 적었다(2026-08-10 status-table-resync). 종전 축은 **행 수 ≥3**
#   하나뿐이라, 종결된 [BL-698]·기각된 [BL-306] 이 살아 있는 행으로 남아 표를 그대로 읽으면
#   **닫힌 결함이 ★★★ 최상위 추천**으로 보이는데도 통과했다.
# ★판정은 `bl-audit.sh --list` 가 정본이다 — 상태줄 파서를 여기서 다시 쓰지 않는다(위 블록과 공용).
# ★★**빈 집합이 「일치」로 새는 것**이 이 레포가 두 번 밟은 함정이다 ⇒ 양쪽이 비면 **rc=3 ABORT**.
#   초록도 빨강도 내지 않고 판정을 포기한다 ([LESSON-101]).
# ★~~PARTIAL 쪽은 지금 구조적으로 공집합이다~~ → **2026-08-11 [BL-703] 이 채웠다.** PARTIAL
#   전건이 판정줄을 갖고 그중 몇 건이 도래다 — 이 축이 두 항을 다 쓰는 것은 그날이 처음이다.
#   ★**여기에 수를 박지 마라.** 착수 당시 「24/24 · 도래 5」로 적었는데 같은 날 [BL-672] 가
#     닫히면서 23/23 · 도래 4 가 됐다(codex P2). 세는 것은 이 스크립트 자신이다.
# ★★**「도래」는 볼드로 쓰지 마라** — 아래 정규식은 `**` 뒤에 곧바로 `도래` 를 요구한다.
#   `**트리거 판정:** **도래** — …` 로 쓰면 **조용히 0 매치**가 되고, 그 항목은 ⓪ 표에서
#   요구되지도 금지되지도 않는다(빈 집합이 「없음」으로 새는 이 레포의 상습 함정).
#   2026-08-11 에 실제로 그렇게 썼다가 대조에서 잡았다.
zero_identity_hits: list[str] = []
if by_verdict:
    arrived_partial = {
        b for b in by_verdict.get("PARTIAL", set())
        if re.match(r"^\*\*트리거 판정:\*\*\s*도래", verdict_text.get(b, ""))
    }
    expected = by_verdict.get("ACTIVE", set()) | arrived_partial
    if not expected and not zero_live_ids:
        print("▶ ⓪ 표 정체성 — **판정 포기 (ABORT)**")
        print("  기대 집합(ACTIVE ∪ PARTIAL∧도래)과 ⓪ 표의 살아 있는 행이 **둘 다 비었다.**")
        print("  빈 입력을 「일치」로 통과시키지 않는다 ([LESSON-101]) — 먼저 확인해라:")
        print("    bash tools/scripts/bl-audit.sh --list ACTIVE      # 정본이 비었나")
        print("    grep -n '^### ⓪' docs/status.md            # 표 헤딩이 살아 있나")
        raise SystemExit(3)
    missing = sorted(expected - zero_live_ids, key=lambda x: int(x[3:]))
    extra = sorted(zero_live_ids - expected, key=lambda x: int(x[3:]))
    for bl in missing:
        why = "ACTIVE" if bl in by_verdict.get("ACTIVE", set()) else "PARTIAL∧도래"
        zero_identity_hits.append(
            f"  {bl}: 원장은 {why} 인데 ⓪ 표에 **살아 있는 행이 없다** — "
            "고를 수 없으면 다음 회차가 못 본다"
        )
    for bl in extra:
        zero_identity_hits.append(
            f"  {bl}: ⓪ 표에 살아 있는데 원장에서는 ACTIVE 도 PARTIAL∧도래 도 아니다 — "
            "끝났으면 `~~취소선~~`, 아니면 상태줄을 고쳐라"
        )

if zero_identity_hits:
    print(
        "▶ ⓪ 표 정체성 — 살아 있는 행 == `bl-audit --list ACTIVE` ∪ (PARTIAL ∧ 도래) "
        "([BL-702] · 손으로 후보를 얹지 마라)"
    )
    for why in zero_identity_hits[:20]:
        print(why)
    if len(zero_identity_hits) > 20:
        print(f"  … 외 {len(zero_identity_hits) - 20}건")

if verdict_line_hits:
    print(
        "▶ 트리거 판정 줄 — ACTIVE/DEFERRED/PARTIAL 은 `**트리거 판정:**` 을 정확히 1개 가진다 "
        "([BL-695]·[BL-703] · ADR-028 §4)"
    )
    for why in verdict_line_hits[:20]:
        print(why)
    if len(verdict_line_hits) > 20:
        print(f"  … 외 {len(verdict_line_hits) - 20}건")

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
        # ★파일마다 내려갈 곳이 다르다. 한 문장으로 뭉치면 다음 사람이 엉뚱한 곳으로 간다.
        where = {
            "docs/lessons.md": "docs/archive/ 로 승격 항목을 내려라",
            "docs/status.md": "끝난 회차 회고를 docs/dev-log/ 로 강등하고 INDEX 에 한 줄 남겨라 (ADR-026 §3)",
        }.get(rel, "승격 대상을 내려라")
        print(f"  {rel}: {count}줄 > 상한 {cap}줄 — {where}")

if lesson_id_hits:
    print("▶ LESSON ID 유일성 + 오름차순 — 카드 헤딩과 영구 승격 표를 합쳐 검사한다 (BL-720)")
    for why in lesson_id_hits[:20]:
        print(why)
    if len(lesson_id_hits) > 20:
        print(f"  … 외 {len(lesson_id_hits) - 20}건")

if promotion_pointer_hits:
    print("▶ 승격 표 포인터 — `## 영구 승격 완료` 표의 경로형 코드 스팬은 실재해야 한다 (BL-720)")
    for candidate, why in promotion_pointer_hits[:20]:
        print(f"  docs/lessons.md: `{candidate}` — {why}")
    if len(promotion_pointer_hits) > 20:
        print(f"  … 외 {len(promotion_pointer_hits) - 20}건")

if orphan_hits:
    print("▶ 소유자 없는 검사기가 기동 불가 (BL-631 — 아무도 안 부르면 죽어도 아무도 모른다)")
    for rel, why in orphan_hits:
        print(f"  {rel}: {why}")

if (
    broken_links or legacy_hits or cap_hits or file_len_hits
    or lesson_id_hits or promotion_pointer_hits or orphan_hits or entry_hits
    or verdict_line_hits or zero_identity_hits
):
    print(
        f"✗ docs-audit failed: links={len(broken_links)}, "
        f"retired_paths={len(legacy_hits)}, long_lines={len(cap_hits)}, "
        f"long_files={len(file_len_hits)}, orphan_tools={len(orphan_hits)}, "
        f"lesson_ids={len(lesson_id_hits)}, promotion_pointers={len(promotion_pointer_hits)}, "
        f"entry_point={len(entry_hits)}, trigger_verdicts={len(verdict_line_hits)}, "
        f"zero_table_identity={len(zero_identity_hits)}"
    )
    raise SystemExit(1)

print(
    "✓ docs-audit: active Markdown links, retired paths, line-length caps, "
    "file-length caps, LESSON ID uniqueness/order, promotion table pointers, orphan tool startup, "
    "status.md entry point, ⓪ table identity, trigger verdict lines are clean"
)
PY
