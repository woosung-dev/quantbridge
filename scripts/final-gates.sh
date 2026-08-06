#!/usr/bin/env bash
# 마지막 PR 전 게이트 체인 — 셸로 되는 것은 실행하고, 스킬로만 되는 것은 signal 파일로 강제한다.
#
# 왜 이 스크립트가 있나
#   docs 에 "게이트 8종 생략 금지" 라고 적는 것만으로는 집행되지 않는다 — 이 레포는
#   "수용 기준은 자기 집행되지 않는다"(적어놓고 미이행 2회)를 이미 배웠다. 그래서 실행한다.
#
#   ★2026-08-06 정정 — 원래 여기 적혀 있던 근거는 "CI 는 러너 전역 미할당으로 `steps=0` 에
#   죽는다(billing). 로컬이 유일한 판단 근거" 였다.
#
#   ★★그 전제는 **죽은 게 아니라 휴면이다.** 같은 날 "이제 거짓이다 — CI 는 정상 가동한다
#   (최근 12 run 전건 완주)" 라고 단정했는데 **3시간 22분 뒤 재발했다**: run 31079229987
#   (2026-08-06T07:25:38Z, PR #550) 에서 backend_coverage 와 ci 가 **둘 다 steps=0 · failure**
#   였다(같은 브랜치 직전 run 은 전건 성공). 12 run 은 그 시점의 표본일 뿐이었다.
#   러너 사정은 언제든 돌아온다 — 이 주석을 "없는 위험" 으로 읽지 마라.
#
#   그럼에도 §5 의 "CI 커버리지 잡" 재현은 **기본 skip** 이고 `--with-ci-coverage` 로만 켠다.
#   근거가 러너 가용성이 아니라 **중복**이기 때문이다 — 그것은 §2 의 "BE pytest" 와 같은 스위트를
#   계측만 켜고 두 번째로 도는 순수 중복이었다(로컬 실측 +230s ≈ 9분/회). 나머지 §5 3종은
#   초 단위라 그대로 돈다. ★steps=0 이 다시 보이면 `--with-ci-coverage` 로 되켜라.
#
# 사용법
#   scripts/final-gates.sh --run <name> [--allow-dirty] [--skip-e2e] [--skip-ci-repro]
#                                       [--with-ci-coverage]
#
#   스킬 게이트는 에이전트가 돌린 뒤 아래 파일을 남겨야 통과한다(내용은 근거 요약):
#     .claude/gates/<run>/vercel.ok      /vercel-react-best-practices  (frontend/** diff 있을 때만 필수)
#     .claude/gates/<run>/screen.ok      MCP playwright  또는  gstack /browse  (무엇으로 했는지 적어라)
#     .claude/gates/<run>/codex.ok       /codex 적대 리뷰 — findings 전건 처분 결과
#     .claude/gates/<run>/g9.ok          계획 vs 실제 구현 최종 점검 표
#
# ★BL-549 — 커밋 **전에** 돌리면 거짓 그린이 났다. 영역 판정이 `merge-base..HEAD` diff 라서
#   미커밋 변경이 안 보이고, `fe_diff=0 be_diff=0` 이 되어 lint·type·단위·build 가 전부 `skip` 이
#   된다. 결과표에 FAIL 이 하나도 없으니 **통과처럼 읽힌다.** 그래서 더러운 트리는 기본 거부하고,
#   `--allow-dirty` 를 준 때만 영역 판정을 **워킹트리 기준으로 넓혀서** 돈다.
#
# 종료 코드: 0 = 전건 통과 / 1 = 하나 이상 실패·미확인 또는 더러운 트리 거부
set -uo pipefail

RUN=""; SKIP_E2E=0; SKIP_CI=0; ALLOW_DIRTY=0; WITH_CI_COV=0
while [ $# -gt 0 ]; do
  case "$1" in
    --run) [ $# -ge 2 ] || { echo "--run 에 값이 필요하다" >&2; exit 1; }; RUN="$2"; shift 2 ;;
    --allow-dirty) ALLOW_DIRTY=1; shift ;;
    --skip-e2e) SKIP_E2E=1; shift ;;
    --skip-ci-repro) SKIP_CI=1; shift ;;
    --with-ci-coverage) WITH_CI_COV=1; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
done
[ -n "$RUN" ] || { echo "사용법: $0 --run <name> [--skip-e2e] [--skip-ci-repro]" >&2; exit 1; }
case "$RUN" in *[!A-Za-z0-9._-]*) echo "--run 은 영숫자·점·밑줄·하이픈만" >&2; exit 1 ;; esac

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SLOT=0
[ -f "$ROOT/.worktree-slot" ] && SLOT="$(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$ROOT/.worktree-slot" | tr -d ' ')"
: "${SLOT:=0}"
FE_PORT=$((3100 + SLOT))
GATEDIR="$ROOT/.claude/gates/$RUN"
mkdir -p "$GATEDIR"

# diff 범위 — CI path-filter 와 같은 판정
BASE="$(git -C "$ROOT" merge-base origin/main HEAD 2>/dev/null || echo "")"
if [ -n "$BASE" ]; then
  CHANGED="$(git -C "$ROOT" diff --name-only "$BASE"..HEAD)"
else
  CHANGED=""
fi
# ★워킹트리 미커밋 변경 (BL-549).
#   --no-renames    rename 을 `R old -> new` 한 줄이 아니라 D/A 두 줄로 준다. 한 줄로 받아 파싱하면
#                   **원래 경로를 버려서** `git mv frontend/a.ts docs/a.ts` 를 has_fe=0 으로 오판한다
#                   (codex G1 P1 — 실측 확인).
#   core.quotePath=false   비ASCII 경로에 `"\355\225..."` 이스케이프가 붙는 것을 막는다. 공백 포함
#                   경로는 그래도 따옴표가 붙으므로 아래 sed 가 벗긴다. (`-z` 는 쓸 수 없다 —
#                   `$(...)` 명령 치환이 NUL 을 버려서 전 항목이 한 줄로 뭉친다. 실측으로 확인했다.)
# ★실패를 깨끗한 트리로 삼키지 않는다 — 그러면 dirty 거부가 조용히 사라진다 (codex G1 P2).
DIRTY_RAW="$(git -C "$ROOT" -c core.quotePath=false status --porcelain --no-renames 2>/dev/null)" || {
  echo "✗ git status 가 실패했다 — 워킹트리가 깨끗한지 판정할 수 없어 게이트를 신뢰할 수 없다." >&2
  exit 1
}
DIRTY="$(printf '%s\n' "$DIRTY_RAW" | grep -c . || true)"   # ★M1 변이 지점
: "${DIRTY:=0}"
DIRTY_PATHS=""
if [ "$DIRTY" -gt 0 ]; then
  DIRTY_PATHS="$(printf '%s\n' "$DIRTY_RAW" | sed -e '/^$/d' -e 's/^...//' -e 's/^"//' -e 's/"$//')"
fi

# --allow-dirty 면 영역 판정을 **워킹트리까지** 넓힌다 (커밋 안 한 frontend/ 변경도 FE 게이트를 켠다).
if [ "$ALLOW_DIRTY" -eq 1 ] && [ -n "$DIRTY_PATHS" ]; then
  CHANGED="$CHANGED
$DIRTY_PATHS"
fi

has_fe=0; has_be=0
printf '%s\n' "$CHANGED" | grep -q '^frontend/' && has_fe=1
printf '%s\n' "$CHANGED" | grep -q '^backend/'  && has_be=1

NAMES=(); CODES=(); NOTES=()
record() { NAMES+=("$1"); CODES+=("$2"); NOTES+=("${3:-}"); }

run_gate() {  # run_gate <label> <note> <command...>
  local label="$1" note="$2"; shift 2
  printf '\n▶ %s\n' "$label"
  # ★파이프로 감싸지 않는다 — exit code 가 가려진다(실측 사고 이력).
  "$@"
  local rc=$?
  record "$label" "$rc" "$note"
  printf '  → exit=%d\n' "$rc"
}

skip_gate() { record "$1" "-" "$2"; printf '\n▶ %s\n  → 건너뜀 (%s)\n' "$1" "$2"; }

DIRTY_NOTE=""
[ "$DIRTY" -gt 0 ] && [ "$ALLOW_DIRTY" -eq 1 ] && DIRTY_NOTE=" (--allow-dirty — 영역 판정에 워킹트리 포함)"
echo "══ final-gates  run=$RUN  slot=$SLOT  base=${BASE:0:8}  fe_diff=$has_fe be_diff=$has_be dirty=$DIRTY$DIRTY_NOTE ══"

# ★더러운 트리는 기본 거부 (BL-549). 헤더를 먼저 찍고 거부한다 — 왜 멈췄는지가 숫자와 함께 남아야 한다.
if [ "$DIRTY" -gt 0 ] && [ "$ALLOW_DIRTY" -eq 0 ]; then
  echo
  echo "✗ 워킹트리에 미커밋 변경 $DIRTY 건 — 이 상태로는 게이트를 돌리지 않는다."
  echo
  echo "  왜: 영역 판정이 'merge-base(origin/main,HEAD)..HEAD' diff 다. 미커밋 변경은 여기에"
  echo "      안 잡혀서 fe_diff/be_diff 가 0 이 되고, lint·type·단위·build 가 전부 skip 된다."
  echo "      결과표에 FAIL 이 하나도 없으니 **통과처럼 읽힌다** — 그게 BL-549 다."
  echo
  echo "  둘 중 하나를 해라:"
  echo "    1) 커밋하고 다시 돌린다 (권장 — PR 게이트는 커밋된 것을 재는 것이다)"
  echo "    2) $0 --run $RUN --allow-dirty  (영역 판정을 워킹트리 기준으로 넓혀서 돈다)"
  echo
  printf '%s\n' "$DIRTY_PATHS" | sed 's/^/    /'
  exit 1
fi

# ── 1. lint / type ────────────────────────────────────────────────
if [ "$has_be" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "BE ruff"    "backend/**"  bash -c 'cd "$0/backend" && uv run ruff check .' "$ROOT"
  run_gate "BE mypy"    "backend/**"  bash -c 'cd "$0/backend" && uv run mypy src/'   "$ROOT"
else
  skip_gate "BE ruff" "backend diff 0"; skip_gate "BE mypy" "backend diff 0"
fi
if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "FE typecheck" "frontend/**" bash -c 'cd "$0/frontend" && pnpm typecheck' "$ROOT"
  run_gate "FE lint"      "frontend/**" bash -c 'cd "$0/frontend" && pnpm lint'      "$ROOT"
else
  skip_gate "FE typecheck" "frontend diff 0"; skip_gate "FE lint" "frontend diff 0"
fi

# ★BL 감사 — docs/ 만 읽으므로 영역 판정·cd 와 무관하게 항상 돈다 (BL-564).
#   ★파이프를 붙이지 마라. run_gate 가 rc 를 직접 읽는다.
run_gate "BL 감사" "docs/backlog.md" bash "$ROOT/scripts/bl-audit.sh"

# ★위 게이트의 **중복 검사 자체**를 재는 하네스 (BL-569). 원장이 깨끗하면 중복 탐지 로직을
#   통째로 지워도 "BL 감사" 는 초록이다 — 실제 사고를 막는 코드인데 되돌려도 아무도 못 잡는다.
#   임시 트리 fixture 로 그 회귀를 잡는다. 실제 `docs/` 는 건드리지 않는다.
run_gate "BL 감사 하네스" "scripts/bl-audit.sh" bash "$ROOT/scripts/bl-audit-test.sh"

# ★문서 감사 — 죽은 링크 · retired path · **요약 줄 길이 상한**.
#   CI 의 documentation 잡(`make docs-audit`)이 같은 것을 돌지만 그건 **PR 을 연 뒤**다.
#   줄 길이 회귀는 문서를 만지는 그 회차가 만들고 그 회차가 못 보므로, PR 전에 물게 한다
#   (2026-08-02 context-budget-repair: INDEX.md 한 줄이 4,607자였고 아무 게이트도 안 물었다).
run_gate "문서 감사" "docs/**" bash "$ROOT/scripts/docs-audit.sh"

# ── 2. 단위 ───────────────────────────────────────────────────────
# ★env 소싱 의무 + cd 절대경로. `pnpm test --run` 은 Unknown option — `pnpm test` 가 이미 vitest run.
run_gate "BE pytest" "env 소싱" bash -c 'cd "$0/backend"; set -a; . ./.env.local; set +a; uv run pytest -q' "$ROOT"
if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "FE vitest" "pnpm test" bash -c 'cd "$0/frontend" && pnpm test' "$ROOT"
else
  skip_gate "FE vitest" "frontend diff 0"
fi

# ── 3. build ──────────────────────────────────────────────────────
if [ "$has_fe" -eq 1 ]; then
  run_gate "FE build" "Clerk 키 필요" bash -c 'cd "$0/frontend" && pnpm build' "$ROOT"
else
  skip_gate "FE build" "frontend diff 0"
fi

# ── 4. e2e ────────────────────────────────────────────────────────
# ★PLAYWRIGHT_BASE_URL 없으면 3000 의 남의 앱을 검사한다(거짓 그린 사고 이력).
if [ "$SKIP_E2E" -eq 1 ]; then
  skip_gate "e2e design-canon" "--skip-e2e"; skip_gate "e2e authed" "--skip-e2e"
else
  title="$(curl -s "http://localhost:$FE_PORT" 2>/dev/null | grep -o '<title>[^<]*</title>' | head -1)"
  if printf '%s' "$title" | grep -q 'QuantBridge'; then
    echo "  정체성 프로브 OK — :$FE_PORT $title"
    run_gate "e2e design-canon" ":$FE_PORT" env PLAYWRIGHT_BASE_URL="http://localhost:$FE_PORT" \
      bash -c 'cd "$0/frontend" && pnpm e2e:design-canon' "$ROOT"
    run_gate "e2e authed" ":$FE_PORT" env PLAYWRIGHT_BASE_URL="http://localhost:$FE_PORT" \
      bash -c 'cd "$0/frontend" && pnpm e2e:authed' "$ROOT"
  else
    record "e2e design-canon" 1 "정체성 프로브 실패 — :$FE_PORT 가 QuantBridge 가 아니다"
    record "e2e authed"       1 "정체성 프로브 실패"
    printf '\n▶ e2e\n  → FAIL: :%s 에서 QuantBridge 를 못 찾았다 (got: %s). 서버를 띄우고 다시 돌려라.\n' "$FE_PORT" "${title:-없음}"
  fi
fi

# ── 5. CI 전용 스텝 재현 ────────────────────────────────────────────
# ★"CI 커버리지 잡" 만 기본 skip 이다 (2026-08-06). 위 §2 "BE pytest" 가 이미 같은 스위트를
#   돌았고, 여기는 거기에 계측만 얹어 **두 번째로** 도는 것이었다 — 로컬 실측 무계측 298.97s
#   vs 계측 529.16s (배율 1.770) ⇒ 회당 ~9분이 순수 중복이었다. 커버리지 래칫(BL-308/309)은
#   CI 의 `backend-coverage` 잡이 3 샤드를 `coverage combine` 해서 집행한다.
#   ★그래도 남겨 두는 이유 — CI 를 못 믿을 사정이 생기면 `--with-ci-coverage` 로 되켠다.
#   나머지 3종(fresh DB alembic / frozen-lockfile / hooks grep)은 초 단위라 **그대로 돈다**.
if [ "$SKIP_CI" -eq 1 ]; then
  skip_gate "CI 커버리지 잡" "--skip-ci-repro"; skip_gate "CI fresh DB alembic" "--skip-ci-repro"
  skip_gate "CI frozen-lockfile" "--skip-ci-repro"; skip_gate "CI hooks grep" "--skip-ci-repro"
else
  if [ "$WITH_CI_COV" -eq 1 ]; then
    run_gate "CI 커버리지 잡" "cov-fail-under=90" bash -c '
      cd "$0/backend"; set -a; . ./.env.local; set +a
      uv run pytest -q --cov=src.trading.registry --cov=src.trading.webhook \
        --cov=src.trading.websocket --cov-report=term-missing --cov-fail-under=90' "$ROOT"
  else
    skip_gate "CI 커버리지 잡" "기본 skip — CI backend-coverage 잡이 집행한다 (--with-ci-coverage 로 켠다)"
  fi

  # fresh throwaway DB — 개발 DB 를 향하지 않게 이름을 고정하고, 반드시 _test 로 끝낸다.
  run_gate "CI fresh DB alembic" "throwaway" bash -c '
    db="quantbridge_ci_repro_test"
    docker exec quantbridge-db psql -U quantbridge -d postgres -q -c "DROP DATABASE IF EXISTS $db;" >/dev/null || exit 1
    docker exec quantbridge-db psql -U quantbridge -d postgres -q -c "CREATE DATABASE $db;" >/dev/null || exit 1
    cd "$0/backend"; set -a; . ./.env.local; set +a
    DATABASE_URL="postgresql+asyncpg://quantbridge:password@localhost:5433/$db" uv run alembic upgrade head' "$ROOT"

  run_gate "CI frozen-lockfile" "pnpm" bash -c 'cd "$0/frontend" && pnpm install --frozen-lockfile' "$ROOT"

  run_gate "CI hooks grep" "rules-of-hooks 차단" bash -c '
    cd "$0/frontend"
    if grep -rn "eslint-disable.*react-hooks/rules-of-hooks" src/; then
      echo "rules-of-hooks eslint-disable 가 발견됐다 — CI 가 차단한다"; exit 1
    fi' "$ROOT"
fi

# ── 6. 스킬 게이트 — signal 파일로만 통과한다 ────────────────────
check_signal() {  # check_signal <label> <file> <required 0|1> <why>
  local label="$1" f="$GATEDIR/$2" req="$3" why="$4"
  if [ -s "$f" ]; then
    record "$label" 0 "signal: $2"
  elif [ "$req" -eq 0 ]; then
    skip_gate "$label" "$why"
  else
    record "$label" 1 "★미확인 — $2 를 남겨라"
    printf '\n▶ %s\n  → FAIL: %s 가 없다. 스킬을 돌린 뒤 근거 요약을 그 파일에 적어라.\n' "$label" "$f"
  fi
}
check_signal "/vercel-react-best-practices" "vercel.ok" "$has_fe" "frontend diff 0"
check_signal "화면 검증 (playwright 또는 /browse)" "screen.ok" 1 ""
check_signal "/codex 적대 리뷰" "codex.ok" 1 ""
check_signal "★G9 계획 vs 실제 구현" "g9.ok" 1 ""

# ── 결과 ──────────────────────────────────────────────────────────
echo
echo "══════════════════ 결과 ══════════════════"
if [ "$DIRTY" -gt 0 ]; then
  printf "  %-4s  %-38s %s\n" "DIRT" "워킹트리 미커밋 $DIRTY 건" \
    "--allow-dirty — 영역 판정에 포함됨. 이 결과는 커밋되지 않은 코드의 것이다."
fi
fail=0
for i in "${!NAMES[@]}"; do
  c="${CODES[$i]}"
  if [ "$c" = "-" ]; then mark="skip"
  elif [ "$c" = "0" ]; then mark="PASS"
  else mark="FAIL"; fail=$((fail+1)); fi
  printf "  %-4s  %-38s %s\n" "$mark" "${NAMES[$i]}" "${NOTES[$i]}"
done
echo "═════════════════════════════════════════"
if [ "$fail" -gt 0 ]; then
  echo "✗ ${fail} 건 실패/미확인 — PR 을 만들지 마라."
  exit 1
fi
echo "✓ 전건 통과. ★단 이 스크립트는 '돌렸다' 만 보증한다 — 숫자가 baseline 과 맞는지는 사람이 본다."
