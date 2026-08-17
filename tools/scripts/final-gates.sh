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
#   tools/scripts/final-gates.sh --run <name> [--allow-dirty] [--skip-e2e] [--skip-ci-repro]
#                                       [--with-ci-coverage]
#
#   스킬 게이트는 에이전트가 돌린 뒤 아래 파일을 남겨야 통과한다(내용은 근거 요약):
#     .claude/gates/<run>/vercel.ok      /vercel-react-best-practices  (apps/web/** diff 있을 때만 필수)
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

RUN=""; SKIP_E2E=0; SKIP_CI=0; ALLOW_DIRTY=0; WITH_CI_COV=0; MODE="full"; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --run) [ $# -ge 2 ] || { echo "--run 에 값이 필요하다" >&2; exit 1; }; RUN="$2"; shift 2 ;;
    --allow-dirty) ALLOW_DIRTY=1; shift ;;
    --skip-e2e) SKIP_E2E=1; shift ;;
    --skip-ci-repro) SKIP_CI=1; shift ;;
    --with-ci-coverage) WITH_CI_COV=1; shift ;;
    # ★모드 3종은 상호 배타다. 두 번 주면 마지막이 이기는 게 아니라 거부한다 — 어느 쪽이
    #   이겼는지 사람이 못 읽는 상태로 15분을 태우는 것이 이 스크립트의 원래 병이었다.
    --pre-pr)         [ "$MODE" = "full" ] || { echo "✗ 모드는 하나만: 이미 $MODE" >&2; exit 1; }; MODE="pre-pr"; shift ;;
    --deferred-only)  [ "$MODE" = "full" ] || { echo "✗ 모드는 하나만: 이미 $MODE" >&2; exit 1; }; MODE="deferred-only"; shift ;;
    --dry-run)        DRY=1; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
done
[ -n "$RUN" ] || { echo "사용법: $0 --run <name> [--skip-e2e] [--skip-ci-repro]" >&2; exit 1; }
case "$RUN" in *..*|*[!A-Za-z0-9._-]*) echo "--run 은 영숫자·점·밑줄·하이픈만 (.. 금지)" >&2; exit 1 ;; esac
case "$RUN" in eod) echo "✗ --run eod 는 금지다 — 앞 회차 신호를 물려받는다 ([BL-706]). 회차 슬러그를 써라: --run <회차이름>" >&2; exit 1 ;; esac

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"

# ★도구 버전 핀 — 아래 게이트가 부르는 `pnpm`·`uv`·`node` 는 **PATH 가 아니라 `mise.toml`** 이
#   정한다([BL-785] · [ADR-036]). 이 줄이 없으면 같은 커밋이 셸에 따라 다른 판정을 내고,
#   pnpm 8 셸에서는 lockfile diff 가 0 인 브랜치도 `CI frozen-lockfile` 이 red 다.
#   ★가장 먼저 건다 — 아래는 전부 이 PATH 를 물려받는 자식 프로세스다.
# shellcheck source=tools/scripts/lib/mise-shim-path.sh
. "$ROOT/tools/scripts/lib/mise-shim-path.sh"
qb_pin_tool_path || true

if git -C "$ROOT" rev-parse --verify --quiet refs/remotes/origin/main >/dev/null 2>&1; then
  MERGE_BASE="$(git -C "$ROOT" merge-base refs/remotes/origin/main HEAD 2>/dev/null || true)"
  HEAD_SHA="$(git -C "$ROOT" rev-parse --verify --quiet "HEAD^{commit}" 2>/dev/null || true)"
  if [ -n "$MERGE_BASE" ] && [ "$MERGE_BASE" = "$HEAD_SHA" ]; then
    echo "✗ 브랜치 커밋이 0개다 (merge-base == HEAD) — 이 회차의 PR 브랜치에서 머지 전에 final-gates.sh 를 돌려라." >&2
    exit 1
  fi
fi
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
#                   **원래 경로를 버려서** `git mv apps/web/a.ts docs/a.ts` 를 has_fe=0 으로 오판한다
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

# --allow-dirty 면 영역 판정을 **워킹트리까지** 넓힌다 (커밋 안 한 apps/web/ 변경도 FE 게이트를 켠다).
if [ "$ALLOW_DIRTY" -eq 1 ] && [ -n "$DIRTY_PATHS" ]; then
  CHANGED="$CHANGED
$DIRTY_PATHS"
fi

# ★하네스 전용 영역 주입 ([BL-780]) — `--dry-run` 에서만 산다.
#   왜 있나: `final-gates-test.sh` 케이스 ⑩ 의 **음성 대조**(「apps/web·apps/api/src diff 0 이면
#   화면 검증은 필수 아님」)가 종전에는 실행 시점 브랜치의 diff 에 의존했다. 그래서 `apps/web/` 을
#   건드린 브랜치에서는 게이트가 옳게 「필수」라 답하는데 하네스가 그것을 실패로 읽었다.
#   양성 대조는 이미 합성(탐침 파일)이었으므로 **비대칭이 결함**이었다.
# ★`--dry-run` 밖에서는 **거부**한다(무시가 아니다). dry-run 은 아무 게이트도 실행하지 않으므로
#   여기서 영역을 조작해도 거짓 그린이 성립하지 않는다. 실행 모드에서 이 변수를 조용히 먹으면
#   그 순간 이 훅이 게이트 우회로가 된다.
if [ -n "${QB_FG_FAKE_CHANGED+x}" ]; then
  if [ "$DRY" -ne 1 ]; then
    echo "✗ QB_FG_FAKE_CHANGED 는 --dry-run 에서만 쓸 수 있다 (하네스 전용 · [BL-780])." >&2
    exit 1
  fi
  CHANGED="$QB_FG_FAKE_CHANGED"
  echo "  ⚠ 영역 판정을 QB_FG_FAKE_CHANGED 로 대체했다 (하네스 전용 · dry-run 한정)"
fi

has_fe=0; has_be=0; has_api_src=0
# ★grep -q 금지 (2026-08-13 실측) — pipefail 아래서 -q 는 첫 매치에 조기 종료하고, 목록이 파이프
#   버퍼(64KB)를 넘으면 printf 가 SIGPIPE(141)로 죽어 **매치 성공이 파이프라인 실패**가 된다.
#   이 재배치 PR(1,549 경로·83KB)에서 has_fe/has_be 가 실행마다 뒤집히는 비결정을 실증했다.
#   grep -c 는 입력을 끝까지 읽어 SIGPIPE 가 없다.
fe_n="$(printf '%s\n' "$CHANGED" | grep -c '^apps/web/')"
be_n="$(printf '%s\n' "$CHANGED" | grep -c '^apps/api/')"
# ★`has_be` 보다 좁다 — **API 응답이 바뀔 수 있는가**를 재는 축이다([BL-739]).
#   `apps/api/tests/`·`apps/api/scripts/` 만 바뀐 회차는 화면이 구조적으로 안 바뀐다.
src_n="$(printf '%s\n' "$CHANGED" | grep -c '^apps/api/src/')"
# ★★계약 파일은 `apps/api/` **밖**에 산다 — `contracts/openapi/openapi.json` 만 고친 회차는
#   `be_n=0` 이라 「BE openapi drift」가 `건너뜀` 으로 찍히고 전체가 초록으로 읽힌다.
#   ★2026-08-16 에 `ci.yml` 의 같은 구멍을 막으면서 **이 파일에는 그대로 뒀다**(적대 리뷰가 잡았다).
#   게이트를 붙일 때 「무엇이 그것을 발화시키나」를 한 곳에서만 보면 형제 배선이 남는다.
contracts_n="$(printf '%s\n' "$CHANGED" | grep -c '^contracts/')"
# ★워크플로 축 — FE vitest 의 「CI 실행 표면」 감사가 이 파일들을 **입력으로** 읽는다([BL-789]).
workflows_n="$(printf '%s\n' "$CHANGED" | grep -c '^\.github/workflows/')"
[ "${fe_n:-0}" -gt 0 ] && has_fe=1
[ "${be_n:-0}" -gt 0 ] && has_be=1
[ "${src_n:-0}" -gt 0 ] && has_api_src=1
has_contracts=0
[ "${contracts_n:-0}" -gt 0 ] && has_contracts=1
has_workflows=0
[ "${workflows_n:-0}" -gt 0 ] && has_workflows=1

NAMES=(); CODES=(); NOTES=(); SECS=()
record() { NAMES+=("$1"); CODES+=("$2"); NOTES+=("${3:-}"); SECS+=("${4:-}"); }

# ── 유예 집합 — `--pre-pr` 이 미루고 `--deferred-only` 가 그것만 돈다 ────────────
#
# ★왜 이 여섯인가 (2026-08-14 실측). 전량 1회가 15~20분인데 그 대부분이 이 여섯이고,
#   **CI 가 같은 것을 이미 샤딩해서 돈다**(`ci.yml` 의 `backend`·`backend_coverage`·`e2e` 잡).
#   즉 로컬 전량 실행은 CI 를 직렬로·비샤딩으로 한 번 더 하는 것이었다. 나머지 20종은
#   합쳐도 1분 안쪽이라(FE build 17초가 그중 최장) 중간에 몇 번을 돌려도 싸다.
# ★★그러나 **유예는 면제가 아니다.** 미룬 것을 원장에 적고 종결 문구를 다르게 낸다 —
#   같은 「✓ 전건 통과」를 내면 「초록인데 안 봤다」가 되고, 그게 이 레포가 반복해 덴 병이다.
DEFERRABLE="BE pytest|e2e chromium|e2e design-canon|e2e authed|CI fresh DB alembic|CI 커버리지 잡"
# ★신호 4종도 유예 대상이다. `--pre-pr` 은 「코드가 성립하나」를 묻는 중간 검사라 아직 스킬을
#   안 돌렸을 수 있다. 종결 판정(=신호가 이 회차 것인가)은 `--deferred-only` 가 진다.
DEFERRABLE="$DEFERRABLE|/vercel-react-best-practices|화면 검증 (playwright 또는 /browse)|/codex 적대 리뷰|★G9 계획 vs 실제 구현"
DEFERRED_NAMES=()

is_deferrable() { case "|$DEFERRABLE|" in *"|$1|"*) return 0 ;; *) return 1 ;; esac; }

# 이 모드에서 이 게이트를 도는가. 0=돈다 / 1=이 모드가 미룬다(또는 대상이 아니다)
mode_runs() {
  case "$MODE" in
    full)          return 0 ;;
    pre-pr)        is_deferrable "$1" && return 1 || return 0 ;;
    deferred-only) is_deferrable "$1" && return 0 || return 1 ;;
  esac
}

defer_gate() {  # defer_gate <label> <사유>
  DEFERRED_NAMES+=("$1"); record "$1" "~" "$2"
  printf '\n▶ %s\n  → 유예 (%s)\n' "$1" "$2"
}

run_gate() {  # run_gate <label> <note> <command...>
  local label="$1" note="$2"; shift 2
  if ! mode_runs "$label"; then
    if [ "$MODE" = "pre-pr" ]; then defer_gate "$label" "--pre-pr — push 뒤 --deferred-only 로 돈다"
    else record "$label" "-" "--deferred-only — 이 모드 대상이 아니다"
         printf '\n▶ %s\n  → 건너뜀 (--deferred-only)\n' "$label"; fi
    return
  fi
  if [ "$DRY" -eq 1 ]; then record "$label" "?" "$note (계획)"; printf '\n▶ %s\n  → 계획만 (--dry-run)\n' "$label"; return; fi
  printf '\n▶ %s\n' "$label"
  local t0=$SECONDS
  # ★파이프로 감싸지 않는다 — exit code 가 가려진다(실측 사고 이력).
  "$@"
  local rc=$?
  record "$label" "$rc" "$note" "$((SECONDS-t0))"
  printf '  → exit=%d (%ds)\n' "$rc" "$((SECONDS-t0))"
}

skip_gate() { record "$1" "-" "$2"; printf '\n▶ %s\n  → 건너뜀 (%s)\n' "$1" "$2"; }

DIRTY_NOTE=""
[ "$DIRTY" -gt 0 ] && [ "$ALLOW_DIRTY" -eq 1 ] && DIRTY_NOTE=" (--allow-dirty — 영역 판정에 워킹트리 포함)"
echo "══ final-gates  run=$RUN  slot=$SLOT  base=${BASE:0:8}  fe_diff=$has_fe be_diff=$has_be dirty=$DIRTY$DIRTY_NOTE ══"

# ★더러운 트리는 기본 거부 (BL-549). 헤더를 먼저 찍고 거부한다 — 왜 멈췄는지가 숫자와 함께 남아야 한다.
#   단 `--dry-run` 은 **아무것도 돌리지 않으므로** 거짓 그린이 성립하지 않는다. BL-549 가 막으려는
#   것은 「안 돈 게이트가 통과로 읽히는 것」인데, dry-run 은 자기가 안 돌았다고 표에 적는다.
if [ "$DIRTY" -gt 0 ] && [ "$ALLOW_DIRTY" -eq 0 ] && [ "$DRY" -eq 0 ]; then
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
  run_gate "BE ruff"    "apps/api/**"  bash -c 'cd "$0/apps/api" && uv run ruff check .' "$ROOT"
  run_gate "BE mypy"    "apps/api/**"  bash -c 'cd "$0/apps/api" && uv run mypy src/'   "$ROOT"
else
  skip_gate "BE ruff" "backend diff 0"; skip_gate "BE mypy" "backend diff 0"
fi
# ★OpenAPI 계약 drift — 커밋된 `contracts/openapi/openapi.json` 이 코드 산출물과 같은가.
#   [ADR-031] 이 남긴 배선을 2026-08-16 에 붙였다. 배선 첫 실행이 **실제 drift 1건**을 잡았다
#   (ADR-034 회차에서 `DELETE /auth/me` 독스트링이 바뀌었는데 계약을 재생성하지 않았다).
#   ★★영역 판정이 `has_be` **단독이면 안 된다** — 계약 파일은 `apps/api/` 밖에 있어서
#     `contracts/` 만 고친 회차가 이 게이트를 건너뛴다. `ci.yml` 과 같은 축으로 맞춘다.
#   ★env 통째 소싱이 전제다 — `trading_encryption_keys` 가 기본값 없는 필수 필드다.
#     `.env.local` 이 없으면 `&&` 체인이 끊겨 rc≠0 으로 **소리 내며** 실패한다(실측 확인).
if [ "$has_be" -eq 1 ] || [ "$has_contracts" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "BE openapi drift" "apps/api/**|contracts/**" \
    bash -c 'cd "$0/apps/api" && set -a && . ./.env.local && set +a && uv run python scripts/export_openapi.py --check' "$ROOT"
else
  skip_gate "BE openapi drift" "backend·contracts diff 0"
fi
if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "FE typecheck" "apps/web/**" bash -c 'cd "$0/apps/web" && pnpm typecheck' "$ROOT"
  run_gate "FE lint"      "apps/web/**" bash -c 'cd "$0/apps/web" && pnpm lint'      "$ROOT"
  # ★캐논 가드 3종이 **몇 파일을 실제로 읽는가**를 기준선과 대조한다([ADR-035]).
  #   그 가드들은 스캔 대상을 경로로 정의해서, 파일을 옮기고 목록을 안 고치면 **빈 스코프로
  #   초록**이 난다. 계측기가 인쇄만 하면 아무도 안 보므로 여기서 rc 로 받는다.
  run_gate "FE 캐논 스코프 인구조사" "apps/web/**" \
    bash -c 'cd "$0/apps/web" && node scripts/canon-scope-census.mjs' "$ROOT"
else
  skip_gate "FE typecheck" "frontend diff 0"; skip_gate "FE lint" "frontend diff 0"
  skip_gate "FE 캐논 스코프 인구조사" "frontend diff 0"
fi

# ★BL 감사 — docs/ 만 읽으므로 영역 판정·cd 와 무관하게 항상 돈다 (BL-564).
#   ★파이프를 붙이지 마라. run_gate 가 rc 를 직접 읽는다.
run_gate "BL 감사" "backlog.md + backlog-resolved.md" bash "$ROOT/tools/scripts/bl-audit.sh"

# ★위 게이트의 **중복 검사 자체**를 재는 하네스 (BL-569). 원장이 깨끗하면 중복 탐지 로직을
#   통째로 지워도 "BL 감사" 는 초록이다 — 실제 사고를 막는 코드인데 되돌려도 아무도 못 잡는다.
#   임시 트리 fixture 로 그 회귀를 잡는다. 실제 `docs/` 는 건드리지 않는다.
run_gate "BL 감사 하네스" "tools/scripts/bl-audit.sh" bash "$ROOT/tools/scripts/bl-audit-test.sh"

# [BL-706] 신호 신선도 판별력을 회차 종료 게이트에 연결한다.
run_gate "신호 신선도 하네스" "tools/scripts/signal-check.sh" bash "$ROOT/tools/scripts/signal-check-test.sh"

# ★도구 버전 핀 잔존 감시 ([BL-785]). 위 `qb_pin_tool_path` 는 **이 스크립트에만** 걸린다 —
#   새 스크립트나 되돌린 스크립트가 핀 밖에서 `pnpm`·`uv`·`node` 를 부르면 그 순간부터
#   같은 커밋이 셸에 따라 다른 판정을 낸다. 그게 다시 들어오는 것을 여기서 막는다.
#   ★docs/ 도 apps/ 도 안 읽으므로 영역 판정과 무관하게 항상 돈다.
run_gate "도구 핀 감사" "tools/scripts/**/*.sh + .husky/*" bash "$ROOT/tools/scripts/tool-pin-audit.sh" --root "$ROOT"
run_gate "도구 핀 감사 하네스" "tools/scripts/tool-pin-audit.sh" bash "$ROOT/tools/scripts/tool-pin-audit-test.sh"

# ★소크 재기동 갈래 하네스 ([BL-656]). 이 게이트가 붙은 이유가 그 BL 의 교훈이다 —
#   2026-08-08 에 「unquoted heredoc 안 백틱 정적 카운트 0건으로 동결」이라 **기록만 하고**
#   동결 장치를 안 뒀더니 하루 만에 백틱 1쌍이 되돌아와 dry-run 이 자기 설명문을 실행했다.
#   「이미 up」/「완전 down」 두 갈래의 호출 **순서**와 그 정적 카운트를 함께 잡는다.
#   실제 소크·docker·거래소를 건드리지 않는다 (mktemp 트리 + PATH 앞단 가짜).
run_gate "소크 재기동 하네스" "tools/scripts/soak-restart.sh" bash "$ROOT/tools/scripts/soak-restart-test.sh"

# ★tombstone (2026-08-13, [ADR-030]). 여기 있던 「함대 분배 하네스」(`fleet-dispatch-test.sh`)를
#   `herdr-fleet.sh`·`fleet-dispatch.sh` 와 함께 제거했다 — 조종 장치 축 회수.
#   원문 = `git show c3a39d0d:tools/scripts/fleet-dispatch-test.sh`. 근거 = `docs/decisions/030-harness-pilot-verdict.md`

# ★소스 헤더 감사 + 그 하네스 ([BL-307]). 둘을 **함께** 건다 — 감사기만 걸면 레포가 이미
#   0건이라 판정 로직을 통째로 지워도 초록이다(BL-569 가 `bl-audit` 에서 겪은 것과 같은 모양).
#   ★하네스를 여기 안 걸면 호출자가 0이 되어 아무도 안 돌린다 — 구 `fleet-dispatch-test` 가
#   바로 그 상태였고 BL-601 이 그래서 이 자리를 만들었다 (그 하네스 자신은 2026-08-13
#   [ADR-030] 으로 함대와 함께 제거됐다 — **교훈만 남긴다**).
#   (2026-08-10 `/code-review` Standards 축 H2 「고아 하네스」 검출.)
run_gate "소스 헤더 감사" "tools/scripts/header-audit.sh" bash "$ROOT/tools/scripts/header-audit.sh"
run_gate "소스 헤더 하네스" "tools/scripts/header-audit.sh" bash "$ROOT/tools/scripts/header-audit-test.sh"

# ★무조건 skip 래칫 (2026-08-11 ledger-truth). `@pytest.mark.skip` 데코레이터 개수를 동결한다.
#   여기 걸린 이유 — 2026-05-14 에 「Sprint 61 follow-up」 사유로 심긴 5건이 **Sprint 61 이
#   2026-05-17 에 끝나고도 3개월** 살아남았다. 대응 BL 은 0건이었고 어느 게이트도 안 물었다.
#   pytest 는 skip 을 초록으로 보고하므로 **꺼진 테스트는 통과와 구분되지 않는다.**
#   ★~~별도 하네스를 두지 않는다 — 판정 입력이 「한 줄 문자열과 정수 둘」이라 프로세스 안에서
#   끝나고, 하네스를 만들면 그 자체가 또 하나의 고아 스크립트가 된다.~~
#   → **2026-08-11 [BL-705] 로 반증됐다.** 그 자기검사는 판정 함수와 정규식만 덮고 **스캔층을
#   한 줄도 안 덮는다** — 하한이 두 스코프 **합계**였던 탓에 위반이 사는 `apps/api/tests`(505)가
#   통째로 안 스캔돼도 `apps/api/src`(217)가 합계 하한을 넘겨 **「위반 0건 ✓ rc=0」** 이었다.
#   스캔층은 **파일 트리 fixture 없이는 검사할 수 없다**(그게 `bl-audit-test`·`header-audit-test`
#   가 임시 트리를 쓰는 이유다). 그래서 아래 하네스가 생겼다 — 실제 `apps/api/` 는 안 건드린다.
run_gate "무조건 skip 래칫" "tools/scripts/skip-ratchet.sh" bash "$ROOT/tools/scripts/skip-ratchet.sh"
run_gate "무조건 skip 하네스" "tools/scripts/skip-ratchet.sh" bash "$ROOT/tools/scripts/skip-ratchet-test.sh"

# ★문서 감사 — 죽은 링크 · retired path · **요약 줄 길이 상한**.
#   CI 의 documentation 잡(`mise run docs-audit`)이 같은 것을 돌지만 그건 **PR 을 연 뒤**다.
#   줄 길이 회귀는 문서를 만지는 그 회차가 만들고 그 회차가 못 보므로, PR 전에 물게 한다
#   (2026-08-02 context-budget-repair: INDEX.md 한 줄이 4,607자였고 아무 게이트도 안 물었다).
run_gate "문서 감사" "docs/**" bash "$ROOT/tools/scripts/docs-audit.sh"

# ★위 게이트의 **⓪ 표 정체성 축** 을 재는 하네스 ([BL-702]) — `bl-audit-test` 와 같은 이유다.
#   레포의 ⓪ 표가 이미 원장과 일치하므로 정체성 판정을 통째로 지워도 「문서 감사」는 초록이다.
#   ★특히 이 축이 막는 사고는 **빈 입력이 「일치」로 새는 것**이고, 그 rc=3 경로는 정상 레포에서는
#   절대 발화하지 않는다 — 하네스만이 밟을 수 있다. 여기 안 걸면 호출자가 0이 된다(BL-601 의 그 상태).
run_gate "문서 감사 하네스" "tools/scripts/docs-audit.sh" bash "$ROOT/tools/scripts/docs-audit-test.sh"

# ★고아 하네스 2종을 여기 붙인다 (2026-08-11 실측). 둘 다 레포에 **존재하고 초록인데
#   호출자가 0** 이었다 — 구 `fleet-dispatch-test` 가 BL-601 이전에 있던 바로 그 상태다.
#   아무도 안 부르는 검사기는 죽어도 아무도 모르고, 그 사이 문서는 「하네스가 있다」를 계속 인용한다
#   (BL-631 · LESSON-078). 합쳐 3.2초라 안 걸 이유가 없었다.
run_gate "소크 감시 하네스" "tools/scripts/soak-watch.sh" bash "$ROOT/tools/scripts/soak-watch-test.sh"
run_gate "pre-push 가드 하네스" ".husky/pre-push" bash "$ROOT/tools/scripts/pre-push-guard-test.sh"
run_gate "메인 체크아웃 가드 하네스" "tools/scripts/assert-main-checkout.sh" bash "$ROOT/tools/scripts/assert-main-checkout-test.sh"
# ★2026-08-16 [ADR-033] 조건 3종의 하네스. **지은 자리에서 바로 등록한다** — 위 주석의 「고아 하네스」가
#   생기는 경로가 정확히 「등록을 다음 회차로 미루는 것」이다.
#   ★`db-backup-test` 는 로컬 `quantbridge-db` 가 있으면 실 DB 갈래(㉕~㉘)까지 돈다. 없으면 그 넷만
#   skip 하고 스텁 갈래 35건은 항상 돈다(실행 0건이면 스스로 rc≠0 — 「전부 skip 인데 초록」 방지).
run_gate "DB 백업 하네스" "tools/scripts/db-backup.sh" bash "$ROOT/tools/scripts/db-backup-test.sh"
run_gate "디스크 경보 하네스" "tools/scripts/disk-guard.sh" bash "$ROOT/tools/scripts/disk-guard-test.sh"

# ── 2. 단위 ───────────────────────────────────────────────────────
# ★env 소싱 의무 + cd 절대경로. `pnpm test --run` 은 Unknown option — `pnpm test` 가 이미 vitest run.
# ★★영역 판정을 붙였다 (2026-08-14 · [BL-723]). 종전에는 **무조건** 돌았다 — `BE ruff`·`BE mypy` 는
#   `has_be` 에 걸려 있는데 **가장 비싼 BE 게이트만 안 걸려** 있었다. 앱 코드 diff 가 0 인 회차
#   (docs·tools 만 고친 브랜치)에서 실측 **357초**가 그냥 탔고, 같은 회차에 CI 는 `backend` 잡을
#   **skip** 했다. 즉 로컬이 CI 보다 더 돌면서 잴 것은 없었다.
# ★`|| [ -z "$BASE" ]` = 다른 영역 게이트와 같은 fail-safe 관용구. merge-base 실패 시 돈다.
if [ "$has_be" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "BE pytest" "env 소싱" bash -c 'cd "$0/apps/api"; set -a; . ./.env.local; set +a; uv run pytest -q' "$ROOT"
else
  skip_gate "BE pytest" "backend diff 0"
fi
# ★★워크플로 diff 도 FE vitest 를 발화시킨다 (2026-08-17 적대 리뷰 P1, [BL-789]).
#   `apps/web/src/__tests__/e2e-project-wiring.test.ts` 의 「CI 실행 표면」 감사는 **입력이
#   `.github/workflows/*.yml`** 이다. `has_fe` 만 보면 **워크플로만 고친 회차에서 그 감사가
#   skip** 되고, `--project=` 배선을 지우거나 오타를 내도 로컬 게이트가 초록이다 —
#   가드가 자기 위협모델에 대해 fail-open 이 된다. `ci.yml` 의 `frontend:` 필터에도 같은
#   경로를 넣었다(두 곳이 따로 노는 것을 막는다).
#   ★`has_fe` 자체를 안 넓힌 이유: FE build 와 e2e 3레그까지 같이 발화하면 워크플로 한 줄
#   고칠 때마다 수 분이 탄다. 발화 이유가 다른 게이트는 조건도 다르게 둔다(`has_api_src` ·
#   `has_contracts` 와 같은 결).
if [ "$has_fe" -eq 1 ] || [ "$has_workflows" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "FE vitest" "pnpm test" bash -c 'cd "$0/apps/web" && pnpm test' "$ROOT"
else
  skip_gate "FE vitest" "frontend diff 0 · 워크플로 diff 0"
fi

# ── 3. build ──────────────────────────────────────────────────────
# ★`|| [ -z "$BASE" ]` 는 다른 FE 게이트(:142 :144 :167)와 같은 관용구다. build 에만 빠져
#   있었다 — `merge-base origin/main HEAD` 가 실패하면 CHANGED 가 비어 has_fe=0 이 되고
#   FE build 만 **조용히 skip** 된다. 나머지 넷은 그때 fail-safe 로 돌게 막아 뒀다.
if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "FE build" "외부 인증 키 불요(ADR-034)" bash -c 'cd "$0/apps/web" && pnpm build' "$ROOT"
else
  skip_gate "FE build" "frontend diff 0"
fi

# ── 4. e2e ────────────────────────────────────────────────────────
# ★PLAYWRIGHT_BASE_URL 없으면 3000 의 남의 앱을 검사한다(거짓 그린 사고 이력).
#
# ★[BL-556] `e2e chromium` = `pnpm e2e` = `--project=chromium` = `e2e/smoke.spec.ts` **3 test**
#   (랜딩 렌더 · /strategies→sign-in 리다이렉트 · 랜딩 콘솔 에러 0). CI(`ci.yml:342-344`)는
#   이미 돌리는데 로컬 게이트에만 없었다. 종전 문서 5곳이 「4건」이라 적었으나 `--list` 실측은 3 이다.
#   영역(has_fe)과 서버(정체성 프로브)는 직교하므로 **중첩**한다. 조건식이 두 번 나오는 것은
#   의도다: 세 분기 전부에서 표의 행 순서(chromium → design-canon → authed)를 고정한다.
#
# ★★★**세 레인 전부 영역 판정에 건다 (2026-08-14 · [BL-723]).** 종전에는 `chromium` 만 걸려 있고
#   `design-canon`·`authed` 는 **무조건** 돌았다. 사유는 「`authed` 는 backend 변경도 문다」였고
#   그 사유는 **맞다** — 틀린 것은 처방이다. `has_fe` 하나로 못 재는 것이지 「무조건」이 답이 아니다.
#   앱 코드 diff 가 0 인 회차에서 실측 **authed 268초 + design-canon 42초**가 그냥 탔다.
#     chromium     — 랜딩·리다이렉트·콘솔. BE·DB·인증 무결합  ⇒ `has_fe`
#     design-canon — hermetic `file://` 대비 측정([BL-708]). 서버 무결합 ⇒ `has_fe`
#     authed       — 로그인 후 **데이터 화면**까지 간다. BE 가 죽으면 화면이 빈다([BL-707] 이
#                    정확히 이 축에서 잡혔다 — 콘솔 `ERR_CONNECTION_REFUSED` 109건)
#                                                        ⇒ `has_fe` **또는** `has_be`
#   ★영역 판정은 **모드 판정보다 먼저** 온다 — 잴 것이 없는 레인은 유예 원장에도 안 올라간다.
#     (그래야 `--pre-pr` 유예 수 == `--deferred-only` 실행 수라는 상보성이 유지된다. 하네스 ③④)
e2e_area() {   # 0 = 잴 것이 있다 / 1 = 영역이 비었다
  case "$1" in
    "e2e authed") [ "$has_fe" -eq 1 ] || [ "$has_be" -eq 1 ] || [ -z "$BASE" ] ;;
    *)            [ "$has_fe" -eq 1 ] || [ -z "$BASE" ] ;;
  esac
}
e2e_area_note() {
  case "$1" in
    "e2e authed") echo "frontend·backend diff 0" ;;
    *)            echo "frontend diff 0" ;;
  esac
}
# ★★모드·dry-run 판정은 **정체성 프로브보다 먼저** 온다 (2026-08-14, CI 가 잡았다).
#   아래 프로브 실패 분기는 `record` 를 **직접** 부르므로 `run_gate` 의 모드 디스패치와
#   `--dry-run` 을 **둘 다 우회**한다. 그대로 두면 서버가 없는 환경(CI · 개발 중인 로컬)에서
#   `--pre-pr` 이 e2e 를 DEFER 가 아니라 **FAIL** 로 적어, 「중간에 싸게 돌린다」는 이 모드의
#   존재 이유가 무너진다. 프로브 자체가 curl 이라 dry-run 에서 도는 것도 「계획만」과 어긋난다.
if [ "$DRY" -eq 1 ]; then
  # ★계획 표에서도 **모드별 마크가 실행 때와 같아야** 한다. 여기서 유예를 skip 으로 적으면
  #   `--pre-pr` 의 유예 수와 `--deferred-only` 의 실행 수가 어긋나 분할 상보성이 깨진다
  #   (하네스 케이스 ③④ 가 그것을 잡는다 — 실제로 이 줄을 그렇게 잡았다).
  for _g in "e2e chromium" "e2e design-canon" "e2e authed"; do
    if ! e2e_area "$_g";            then record "$_g" "-" "$(e2e_area_note "$_g")"
    elif mode_runs "$_g";           then record "$_g" "?" "e2e (계획)"
    elif [ "$MODE" = "pre-pr" ];    then record "$_g" "~" "--pre-pr — push 뒤 --deferred-only 로 돈다"
    else                                 record "$_g" "-" "--deferred-only — 이 모드 대상이 아니다"; fi
  done
elif ! mode_runs "e2e authed"; then   # 세 레인은 같은 유예 집합이라 한 번에 가른다
  for _g in "e2e chromium" "e2e design-canon" "e2e authed"; do
    if ! e2e_area "$_g"; then skip_gate "$_g" "$(e2e_area_note "$_g")"
    elif [ "$MODE" = "pre-pr" ]; then defer_gate "$_g" "--pre-pr — push 뒤 --deferred-only 로 돈다"
    else record "$_g" "-" "--deferred-only — 이 모드 대상이 아니다"
         printf '\n▶ %s\n  → 건너뜀 (--deferred-only)\n' "$_g"; fi
  done
elif ! e2e_area "e2e chromium" && ! e2e_area "e2e authed"; then
  # ★세 레인 전부 잴 것이 없다 — **정체성 프로브(curl)도 돌리지 않는다.** 종전에는 docs 만 고친
  #   회차에서 서버가 없으면 e2e 가 FAIL 로 적혔다. 잴 것이 없는데 서버를 요구하는 것은 결함이다.
  for _g in "e2e chromium" "e2e design-canon" "e2e authed"; do
    skip_gate "$_g" "$(e2e_area_note "$_g")"
  done
elif [ "$SKIP_E2E" -eq 1 ]; then
  skip_gate "e2e chromium" "--skip-e2e"
  skip_gate "e2e design-canon" "--skip-e2e"; skip_gate "e2e authed" "--skip-e2e"
else
  title="$(curl -s "http://localhost:$FE_PORT" 2>/dev/null | grep -o '<title>[^<]*</title>' | head -1)"
  if printf '%s' "$title" | grep -q 'QuantBridge'; then
    echo "  정체성 프로브 OK — :$FE_PORT $title"
    if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
      run_gate "e2e chromium" ":$FE_PORT" env PLAYWRIGHT_BASE_URL="http://localhost:$FE_PORT" \
        bash -c 'cd "$0/apps/web" && pnpm e2e' "$ROOT"
    else
      skip_gate "e2e chromium" "frontend diff 0"
    fi
    if e2e_area "e2e design-canon"; then
      run_gate "e2e design-canon" ":$FE_PORT" env PLAYWRIGHT_BASE_URL="http://localhost:$FE_PORT" \
        bash -c 'cd "$0/apps/web" && pnpm e2e:design-canon' "$ROOT"
    else
      skip_gate "e2e design-canon" "$(e2e_area_note "e2e design-canon")"
    fi
    if e2e_area "e2e authed"; then
      run_gate "e2e authed" ":$FE_PORT" env PLAYWRIGHT_BASE_URL="http://localhost:$FE_PORT" \
        bash -c 'cd "$0/apps/web" && pnpm e2e:authed' "$ROOT"
    else
      skip_gate "e2e authed" "$(e2e_area_note "e2e authed")"
    fi
  else
    if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
      record "e2e chromium" 1 "정체성 프로브 실패 — :$FE_PORT 가 QuantBridge 가 아니다"
    else
      skip_gate "e2e chromium" "frontend diff 0"
    fi
    if e2e_area "e2e design-canon"; then
      record "e2e design-canon" 1 "정체성 프로브 실패 — :$FE_PORT 가 QuantBridge 가 아니다"
    else
      skip_gate "e2e design-canon" "$(e2e_area_note "e2e design-canon")"
    fi
    if e2e_area "e2e authed"; then
      record "e2e authed" 1 "정체성 프로브 실패"
    else
      skip_gate "e2e authed" "$(e2e_area_note "e2e authed")"
    fi
    printf '\n▶ e2e\n  → FAIL: :%s 에서 QuantBridge 를 못 찾았다 (got: %s). 서버를 띄우고 다시 돌려라.\n' "$FE_PORT" "${title:-없음}"
  fi
fi

# ── 4b. 화면 증거 팩 ([BL-797]) ────────────────────────────────────
#
# ★결함: `apps/web/` 을 바꾼 PR 이 머지될 때 리뷰어가 얻는 것이 **코드 diff 뿐**이었다.
#   무엇이 어떻게 달라 보이는지도, 그 대가(번들·요청 수)가 얼마인지도 아무 데도 안 남았다.
#   [BL-662~665] 가 `/dashboard` 를 −181.5kB 줄인 수치는 PR 에 없고, [BL-786] 의 라우트 감소는
#   CONTROL 이 대조 빌드를 두 번 돌려 겨우 찾아냈다 — 그 회차 레인 보고서는 「추가 비용 없음」이었다.
#
# ★영역 판정은 **기존 `has_fe` 를 그대로 쓴다**(AC-6). 새 판정식을 만들면 두 축이 따로 늙는다.
#   `|| [ -z "$BASE" ]` 도 다른 FE 게이트와 같은 관용구다.
#
# ★★**자리가 §4 뒤인 것은 의도다.** playwright 는 setup 에서 그 project 의 `outputDir` 을 통째로
#   지우는데, 위 e2e 세 레그는 `PW_ARTIFACT_RUN` 없이 돌아 기본 `test-results/` 를 쓴다.
#   이 레그를 앞에 두면 그 셋이 이 회차의 스크린샷·trace 를 지운다([LESSON-117]).
#   여기서는 `PW_ARTIFACT_RUN="$RUN"` 으로 회차 폴더에 격리하고, 그 폴더는 뒤에 아무도 안 건드린다.
#
# ★**유예 집합에 넣지 않았다.** 이것이 없으면 화면을 바꾼 PR 이 증거 없이 지나가는데, 그것이
#   바로 이 게이트가 막으려는 상태다. 대가는 실측 ~50초(자체 `next build` 25초 포함)다.
#   ★★빌드를 §3 것과 공유하지 않는 이유: 공유하면 「§3 이 실패했거나 그 사이 트리가 바뀐」 창이
#   열리고, 그 창이 곧 [BL-706] 이 닫은 게이트 신선도 구멍이다. 30초로 그 구멍을 안 판다.
if [ "$has_fe" -eq 1 ] || [ -z "$BASE" ]; then
  run_gate "화면 증거 팩" "before=origin/main · 공개 라우트" \
    env PW_ARTIFACT_RUN="$RUN" bash -c 'cd "$0/apps/web" && pnpm screen-evidence' "$ROOT"
else
  skip_gate "화면 증거 팩" "frontend diff 0"
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
      cd "$0/apps/api"; set -a; . ./.env.local; set +a
      uv run pytest -q --cov=src.trading.registry --cov=src.trading.webhook \
        --cov=src.trading.websocket --cov-report=term-missing --cov-fail-under=90' "$ROOT"
  else
    skip_gate "CI 커버리지 잡" "기본 skip — CI backend-coverage 잡이 집행한다 (--with-ci-coverage 로 켠다)"
  fi

  # fresh throwaway DB — 개발 DB 를 향하지 않게 이름을 고정하고, 반드시 _test 로 끝낸다.
  # ★[BL-782] `alembic check` 를 여기에 붙였다. 「어느 DB 에 대고 재는가」의 정본이 바로 이
  #   migration-only DB 이기 때문이다 — 개발 DB 는 `create_all` 이력이 섞여 있어 같은 명령이
  #   rc=0 을 내고(2026-08-17 실측), 그 rc=0 이 [BL-770] 을 닫았다. 프로덕션 스키마를 만드는
  #   유일한 경로가 migration 이므로 여기서 나는 drift 만이 배포에서 실제로 터진다.
  #   ★`TIMESCALE_URL` 도 같이 덮는다 — `.env.local` 에서 이미 개발 DB 로 전개된 값이 남는다.
  run_gate "CI fresh DB alembic" "throwaway + drift check" bash -c '
    db="quantbridge_ci_repro_test"
    docker exec quantbridge-db psql -U quantbridge -d postgres -q -c "DROP DATABASE IF EXISTS $db;" >/dev/null || exit 1
    docker exec quantbridge-db psql -U quantbridge -d postgres -q -c "CREATE DATABASE $db;" >/dev/null || exit 1
    cd "$0/apps/api"; set -a; . ./.env.local; set +a
    export DATABASE_URL="postgresql+asyncpg://quantbridge:password@localhost:5433/$db"
    export TIMESCALE_URL="$DATABASE_URL"
    uv run alembic upgrade head || exit 1
    uv run alembic check' "$ROOT"

  run_gate "CI frozen-lockfile" "pnpm" bash -c 'cd "$0/apps/web" && pnpm install --frozen-lockfile' "$ROOT"

  run_gate "CI hooks grep" "rules-of-hooks 차단" bash -c '
    cd "$0/apps/web"
    if grep -rn "eslint-disable.*react-hooks/rules-of-hooks" src/; then
      echo "rules-of-hooks eslint-disable 가 발견됐다 — CI 가 차단한다"; exit 1
    fi' "$ROOT"
fi

# ── 6. 스킬 게이트 — signal 파일로만 통과한다 ────────────────────
# ★모드 디스패치는 `check_signal` **밖**에 둔다. 그 함수의 배선(=`record`/`skip_gate` 를 정확히
#   1회 부른다)은 `signal-check-test.sh` 케이스 ㉑㉒㉓ 이 호출 횟수로 고정한 계약이라,
#   본문에 분기를 더하면 그 하네스가 red 가 된다 — 2026-08-14 에 실제로 그렇게 잡혔다.
signal_gate() {  # signal_gate <label> <file> <required 0|1> <why>
  if ! mode_runs "$1"; then
    if [ "$MODE" = "pre-pr" ]; then defer_gate "$1" "--pre-pr — 신호는 종결 시점에 잰다"
    else record "$1" "-" "--deferred-only — 이 모드 대상이 아니다"; fi
    return
  fi
  # ★required 를 사유에 노출한다([BL-739]). 다른 게이트는 dry-run 계획 표에 이미 skip 사유를
  #   보여주는데 신호만 그것을 삼켜서, 「이 회차에 이 신호가 필수인가」를 **잴 방법이 없었다.**
  #   `check_signal` 호출 횟수는 안 바뀐다 — `signal-check-test.sh` ㉑㉒㉓ 의 계약은 그대로다.
  if [ "$DRY" -eq 1 ]; then
    if [ "$3" -eq 0 ]; then record "$1" "?" "신호 $2 (계획 · 필수 아님: $4)"
    else record "$1" "?" "신호 $2 (계획 · 필수)"; fi
    return
  fi
  check_signal "$@"
}

check_signal() {  # check_signal <label> <file> <required 0|1> <why>
  local label="$1" f="$2" req="$3" why="$4" out rc
  # ★두 줄로 나눈다. `local out="$(...)"` 는 rc 가 **local 의 것**(항상 0)이라 전건 PASS 가 된다.
  out="$(bash "$ROOT/tools/scripts/signal-check.sh" --root "$ROOT" --run "$RUN" "$f")"   # ★파이프 금지
  rc=$?
  if [ "$rc" -eq 0 ]; then
    record "$label" 0 "$out"                       # → `signal: g9.ok @ 25e96fb7 [head] — …`
  elif [ "$rc" -eq 3 ]; then
    # ★판정 불가(git 이상)는 req=0 이어도 skip 으로 낮추지 않는다 — fail-open 금지 (G6 F4).
    record "$label" "$rc" "★$out"
    printf '\n▶ %s\n  → FAIL: %s\n' "$label" "$out"
  elif [ "$req" -eq 0 ]; then
    skip_gate "$label" "$why · $out"               # 필수 아님 → FAIL 로 올리지 않고 사유를 남긴다
  else
    record "$label" "$rc" "★$out"
    printf '\n▶ %s\n  → FAIL: %s\n' "$label" "$out"
    printf '     신호 파일: %s\n' "$ROOT/.claude/gates/$RUN/$f"
    printf '     첫 줄에 `commit: %s` 를 적어라 — 신호는 **무엇을 검증했는지** 말해야 한다 ([BL-706]).\n' \
      "$(git -C "$ROOT" rev-parse HEAD)"
  fi
}
signal_gate "/vercel-react-best-practices" "vercel.ok" "$has_fe" "frontend diff 0"
# ★[BL-739] — 종전엔 리터럴 `1` 이라, 바로 윗줄이 `frontend diff 0` 으로 skip 되는 그 회차에서
#   아랫줄만 FAIL 이 났다(같은 FE 축인데 한쪽만 조건부 = 비대칭).
#   ★단 `$has_fe` 로 바꾸면 **BE 가 화면을 깨는 경우**를 놓친다([BL-707]: CORS·포트가 어긋나면
#   화면은 「데이터 없음」으로 보인다). 그래서 술어는 `apps/api/src` 까지 포함한다 —
#   `src/` 가 0줄이면 API 응답이 바뀔 수 없고, 그때만 검증 대상이 구조적으로 부재하다.
screen_req=0
{ [ "$has_fe" -eq 1 ] || [ "$has_api_src" -eq 1 ]; } && screen_req=1
signal_gate "화면 검증 (playwright 또는 /browse)" "screen.ok" "$screen_req" "apps/web/ · apps/api/src/ diff 0"
signal_gate "/codex 적대 리뷰" "codex.ok" 1 ""
signal_gate "★G9 계획 vs 실제 구현" "g9.ok" 1 ""

# ── 결과 ──────────────────────────────────────────────────────────
echo
echo "══════════════════ 결과 ══════════════════"
if [ "$DIRTY" -gt 0 ]; then
  printf "  %-4s  %-38s %s\n" "DIRT" "워킹트리 미커밋 $DIRTY 건" \
    "--allow-dirty — 영역 판정에 포함됨. 이 결과는 커밋되지 않은 코드의 것이다."
fi
fail=0; total_s=0
for i in "${!NAMES[@]}"; do
  c="${CODES[$i]}"
  if   [ "$c" = "-" ]; then mark="skip"
  elif [ "$c" = "~" ]; then mark="DEFER"
  elif [ "$c" = "?" ]; then mark="plan"
  elif [ "$c" = "0" ]; then mark="PASS"
  else mark="FAIL"; fail=$((fail+1)); fi
  el=""; [ -n "${SECS[$i]}" ] && { el="$(printf '%4ds' "${SECS[$i]}")"; total_s=$((total_s+SECS[i])); }
  printf "  %-5s %-6s %-38s %s\n" "$mark" "$el" "${NAMES[$i]}" "${NOTES[$i]}"
done
echo "═════════════════════════════════════════"
[ "$total_s" -gt 0 ] && printf "  실행 합계 %ds (%dm%02ds) — 어느 게이트가 비싼지는 위 열이 말한다\n" \
  "$total_s" "$((total_s/60))" "$((total_s%60))"

# ── 유예 원장 — 미룬 것은 파일로 남는다. 「초록인데 안 봤다」를 막는 유일한 장치다 ──
LEDGER="$ROOT/.claude/gates/$RUN/deferred.txt"
if [ "$DRY" -eq 1 ]; then
  echo "▶ --dry-run — 계획만 출력했다. 아무 게이트도 돌지 않았다."
  exit 0
fi

if [ "$fail" -gt 0 ]; then
  echo "✗ ${fail} 건 실패/미확인 — PR 을 만들지 마라."
  exit 1
fi

case "$MODE" in
  pre-pr)
    mkdir -p "$(dirname "$LEDGER")"
    { echo "run: $RUN"; echo "sha: $(git -C "$ROOT" rev-parse HEAD)"; echo "mode: pre-pr";
      echo "# 아래는 --pre-pr 이 **미룬** 게이트다. push 뒤 --deferred-only 로 돌려서 이 파일을 지워라.";
      printf '%s\n' "${DEFERRED_NAMES[@]}"; } > "$LEDGER"
    echo "✓ pre-PR 통과 — 단 **${#DEFERRED_NAMES[@]}종을 아직 안 돌렸다.** 이것은 종결 판정이 아니다."
    printf '    %s\n' "${DEFERRED_NAMES[@]}"
    echo
    echo "  다음: PR 을 올린 뒤 CI 와 **나란히** 로컬에서"
    echo "    $0 --run $RUN --deferred-only"
    echo "  유예 원장: ${LEDGER#$ROOT/}"
    ;;
  deferred-only)
    rm -f "$LEDGER"
    echo "✓ 유예분 통과 — 유예 원장 해제. 이제 종결 조건이 전부 충족됐다."
    echo "  ★단 이 스크립트는 '돌렸다' 만 보증한다 — 숫자가 baseline 과 맞는지는 사람이 본다."
    ;;
  *)
    rm -f "$LEDGER"
    echo "✓ 전건 통과. ★단 이 스크립트는 '돌렸다' 만 보증한다 — 숫자가 baseline 과 맞는지는 사람이 본다."
    ;;
esac
