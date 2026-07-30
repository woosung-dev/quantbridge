#!/usr/bin/env bash
# 마지막 PR 전 게이트 체인 — 셸로 되는 것은 실행하고, 스킬로만 되는 것은 signal 파일로 강제한다.
#
# 왜 이 스크립트가 있나
#   CI 는 러너 전역 미할당으로 `steps=0` 에 죽는다(billing). 로컬이 유일한 판단 근거인데,
#   docs 에 "게이트 8종 생략 금지" 라고 적는 것만으로는 집행되지 않는다 — 이 레포는
#   "수용 기준은 자기 집행되지 않는다"(적어놓고 미이행 2회)를 이미 배웠다. 그래서 실행한다.
#
# 사용법
#   scripts/final-gates.sh --run <name> [--skip-e2e] [--skip-ci-repro]
#
#   스킬 게이트는 에이전트가 돌린 뒤 아래 파일을 남겨야 통과한다(내용은 근거 요약):
#     .claude/gates/<run>/vercel.ok      /vercel-react-best-practices  (frontend/** diff 있을 때만 필수)
#     .claude/gates/<run>/screen.ok      MCP playwright  또는  gstack /browse  (무엇으로 했는지 적어라)
#     .claude/gates/<run>/codex.ok       /codex 적대 리뷰 — findings 전건 처분 결과
#     .claude/gates/<run>/g9.ok          계획 vs 실제 구현 최종 점검 표
#
# 종료 코드: 0 = 전건 통과 / 1 = 하나 이상 실패 또는 미확인
set -uo pipefail

RUN=""; SKIP_E2E=0; SKIP_CI=0
while [ $# -gt 0 ]; do
  case "$1" in
    --run) [ $# -ge 2 ] || { echo "--run 에 값이 필요하다" >&2; exit 1; }; RUN="$2"; shift 2 ;;
    --skip-e2e) SKIP_E2E=1; shift ;;
    --skip-ci-repro) SKIP_CI=1; shift ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
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

be() { cd "$ROOT/backend" || return 1; set -a; . ./.env.local; set +a; "$@"; }

echo "══ final-gates  run=$RUN  slot=$SLOT  base=${BASE:0:8}  fe_diff=$has_fe be_diff=$has_be ══"

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

# ── 5. CI 전용 스텝 재현 (GitHub CI 가 steps=0 으로 죽으므로 여기가 대체) ──
if [ "$SKIP_CI" -eq 1 ]; then
  skip_gate "CI 커버리지 잡" "--skip-ci-repro"; skip_gate "CI fresh DB alembic" "--skip-ci-repro"
  skip_gate "CI frozen-lockfile" "--skip-ci-repro"; skip_gate "CI hooks grep" "--skip-ci-repro"
else
  run_gate "CI 커버리지 잡" "cov-fail-under=90" bash -c '
    cd "$0/backend"; set -a; . ./.env.local; set +a
    uv run pytest -q --cov=src.trading.registry --cov=src.trading.webhook \
      --cov=src.trading.websocket --cov-report=term-missing --cov-fail-under=90' "$ROOT"

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
