#!/usr/bin/env bash
#
# herdr 워크트리 함대 부팅 — ★**오케스트레이터가 있는 워크스페이스에 워커 탭을 띄운다.**
#
# 사용법:
#   scripts/herdr-fleet.sh --agent claude:bl537 --agent claude:bl536 --agent codex:impl
#   scripts/herdr-fleet.sh --agent claude:a --agent codex:b --label "QB 실험"
#   scripts/herdr-fleet.sh --agent claude:a --base origin/main --skip-deps
#   scripts/herdr-fleet.sh --layout panes --agent claude:a --agent claude:b   # 한 창 그리드
#   scripts/herdr-fleet.sh --teardown            # 이 워크스페이스의 워커 화면만 닫는다
#
#   `--layout tabs` (기본) — 워커마다 탭 1개:
#   [스페이스: 퀀트브릿지]  ← 오케스트레이터 세션이 이미 있는 그 워크스페이스
#   ┌──────────┬──────────┬──────────┐
#   │ 1 (현재) │ bl537·s1 │ bl536·s2 │  ← 탭. 각 워커 탭 = 워크트리 1벌 = 슬롯 1벌
#   │ CONTROL  │ 워크트리 │ 워크트리 │    (FE 3100+N / BE 8100+N / quantbridge_wN_test)
#   └──────────┴──────────┴──────────┘
#
#   `--layout panes` — 현재 탭을 쪼개 전부 한눈에 (2행 고정 · 열 = ceil(총칸/2) · **열 우선**):
#   ┌──────────┬──────────┬──────────┐
#   │ CONTROL  │ 워커2    │ 워커4    │  창 298×78 이면 각 99×39.
#   ├──────────┼──────────┼──────────┤  ★Claude Code TUI 는 폭 80 미만이면 읽기 힘들다 —
#   │ 워커1    │ 워커3    │          │    워커 4벌(총 5칸)까지가 실용 상한이다.
#   └──────────┴──────────┴──────────┘
#
#   ★**CONTROL 은 따로 만들지 않는다** — 이 스크립트를 돌리는 그 자리(메인 체크아웃, 슬롯 0)가
#     곧 CONTROL 이다. tabs 면 옆 탭, panes 면 같은 화면 좌상단이다.
#
# ★왜 별도 워크스페이스가 아닌가 (2026-07-30 사용자 결정) — 워크스페이스를 새로 만들면
#   오케스트레이터가 있는 스페이스와 **다른 곳**에 뜬다. 진행 상황을 보려면 스페이스를
#   갈아타야 하고, 오케스트레이터 화면에서는 워커가 아예 안 보인다. 탭으로 두면 같은
#   화면의 탭 줄에 나란히 걸리고, CONTROL 이 원래 있던 자리 그대로다.
#
# ★프롬프트는 주입하지 않는다. 부팅까지가 이 스크립트의 일이고, 첫 지시는 사람이 한다.
#   자동 주입이 필요해지면 herdr 가 이미 갖고 있다 (이 스크립트를 고치기 전에 읽어라):
#     herdr agent prompt <pane_id> "<지시>" --wait --until done --timeout 1800000
#     herdr agent wait   <pane_id> --until blocked --timeout 600000
#     herdr agent read   <pane_id> --source recent --lines 200
#   지금 넣지 않는 이유 — 이 레포는 "자동화된 거짓 그린" 을 반복해서 밟았다. 사람이 루프 안에
#   있는 상태로 1단계를 먼저 굳힌다.
#
# ⚠️ CONTROL(= 현재 탭, 메인 체크아웃)이 필요한 이유 — 워크트리에서는 celery 경유 검증
#    (백테스트·라이브신호·옵티마이저)이 **구조적으로 불가능**하다. worker 컨테이너가 메인의
#    `./backend/src` 를 bind-mount 하므로 워크트리 코드는 실행되지 않는다. 테스트는 통과하는데
#    돌아간 게 내 코드가 아닌 침묵 실패다. 상세: docs/reference/worktree-parallel.md §3.

set -euo pipefail

die() { echo "✗ $*" >&2; exit 1; }
ok()  { echo "  ✓ $*"; }

# 탭이라 화면 분할 제약은 없지만, 한 사람이 동시에 감독할 수 있는 수를 넘기지 않는다.
# 슬롯(포트·테스트 DB)도 워커마다 1벌씩 소모한다.
MAX_AGENTS=4
SPECS=()
LABEL=""
BASE="origin/main"
BOOTSTRAP_ARGS=()
TEARDOWN=""
# tabs = 워커마다 탭 1개(기존 동작, 기본값) / panes = 현재 탭을 쪼개 그리드로 한눈에.
LAYOUT="tabs"

# 값이 필요한 옵션은 값의 존재를 먼저 본다 — 값을 빼면 `shift 2` 가 실패해 `set -e` 로
# **의도한 진단 대신** 셸 오류만 남기고 죽는다 (codex 리뷰 P2).
need_val() { [ "$1" -ge 2 ] || { echo "✗ $2 에 값이 없다" >&2; exit 2; }; }

while [ $# -gt 0 ]; do
  case "$1" in
    --agent)         need_val $# --agent;         SPECS+=("$2"); shift 2 ;;
    --label)         need_val $# --label;         LABEL="$2"; shift 2 ;;
    --base)          need_val $# --base;          BASE="$2"; shift 2 ;;
    --layout)        need_val $# --layout;        LAYOUT="$2"; shift 2 ;;
    --skip-deps)     BOOTSTRAP_ARGS+=(--skip-deps); shift ;;
    --teardown)      TEARDOWN=1; shift ;;
    -h|--help)       sed -n '2,45p' "$0"; exit 0 ;;
    *)               die "알 수 없는 인자: $1  (--help)" ;;
  esac
done

case "$LAYOUT" in
  tabs|panes) : ;;
  *) die "--layout 은 tabs 또는 panes 다 (받은 값: $LAYOUT)" ;;
esac

command -v herdr >/dev/null 2>&1 || die "herdr 가 없다. brew 로 설치돼 있어야 한다."
herdr status server >/dev/null 2>&1 || die "herdr 서버가 안 떠 있다. 터미널에서 'herdr' 를 한 번 띄워라."

# 소켓 API 응답에서 값 하나 꺼내기. herdr 는 전 서브커맨드가 JSON 을 stdout 으로 낸다.
# 실패를 조용히 빈 문자열로 넘기지 않는다 — 여기서 놓치면 엉뚱한 pane 에 에이전트가 뜬다.
json_get() {  # json_get <json> <dotted.path>
  python3 -c '
import json,sys
doc=json.loads(sys.argv[1])
cur=doc
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict) or k not in cur:
        sys.exit(1)
    cur=cur[k]
print(cur)
' "$1" "$2"
}

# ── teardown ────────────────────────────────────────────────────────────────
# 워크트리는 **지우지 않는다.** 에이전트가 커밋 안 한 작업을 들고 있을 수 있고, 그걸 날리는
# 판단은 사람 몫이다. 화면만 닫고 지우는 명령을 출력한다.
if [ -n "$TEARDOWN" ]; then
  # ★워커 화면만 닫는다 — 오케스트레이터(현재) 자리는 절대 닫지 않는다.
  #   판별은 **cwd 가 이 레포의 `.claude/worktrees/` 아래인 pane** 으로 한다. 라벨로 고르면
  #   사람이 이름을 바꾼 순간 못 찾고, 워크스페이스를 통째로 닫으면 오케스트레이터가 함께 죽는다.
  #
  #   ★`--layout` 을 다시 줄 필요가 없다 — **어디에 있는지로** 결정한다:
  #     · 워커가 **내 탭 안의 pane**(panes 모드)  → `herdr pane close`
  #     · 워커가 **다른 탭**(tabs 모드)           → `herdr tab close` (탭째)
  #   그래서 tabs/panes 를 섞어 띄웠어도 한 번의 --teardown 으로 전부 정리된다.
  _cur="$(herdr pane current)" || die "현재 pane 을 못 읽었다 — herdr 세션 안에서 실행해라"
  _ws="$(json_get "$_cur" result.pane.workspace_id 2>/dev/null || json_get "$_cur" result.workspace_id)"
  _me="$(json_get "$_cur" result.pane.tab_id 2>/dev/null || json_get "$_cur" result.tab_id)"
  _mypane="$(json_get "$_cur" result.pane.pane_id 2>/dev/null || json_get "$_cur" result.pane_id)"
  _root="$(git rev-parse --show-toplevel)"
  _closed=0
  _seen_tabs=""
  while IFS='	' read -r _pane _tab _cwd; do
    [ -n "$_pane" ] || continue
    # ★현재 pane 은 어떤 경우에도 닫지 않는다 (cwd 필터가 이미 걸러야 하지만 이중 방어).
    [ "$_pane" != "$_mypane" ] || continue
    if [ "$_tab" = "$_me" ]; then
      herdr pane close "$_pane" >/dev/null 2>&1 \
        && { ok "pane $_pane 닫음 ($_cwd)"; _closed=$((_closed + 1)); }
    else
      case " $_seen_tabs " in *" $_tab "*) continue ;; esac
      _seen_tabs="$_seen_tabs $_tab"
      herdr tab close "$_tab" >/dev/null 2>&1 \
        && { ok "탭 $_tab 닫음 ($_cwd)"; _closed=$((_closed + 1)); }
    fi
  done < <(herdr pane list 2>/dev/null | python3 -c '
import json, sys
ws, root = sys.argv[1], sys.argv[2]
for p in json.load(sys.stdin)["result"]["panes"]:
    if p.get("workspace_id") != ws:
        continue
    cwd = p.get("cwd") or ""
    if not cwd.startswith(root + "/.claude/worktrees/"):
        continue
    pane, tab = p.get("pane_id"), p.get("tab_id")
    if pane and tab:
        print(f"{pane}\t{tab}\t{cwd}")
' "$_ws" "$_root")
  [ "$_closed" -gt 0 ] || echo "  (닫을 워커 화면이 없다 — 이미 정리됐거나 다른 워크스페이스다)"
  cat <<'EOF'

워크트리는 남겨뒀다 (커밋 안 한 작업이 있을 수 있다). 확인하고 직접 지워라:
  git worktree list
  git -C <워크트리> status --short          # 비어 있는지 먼저 봐라
  git worktree remove <워크트리>
  git branch -d <브랜치>
  docker exec quantbridge-db psql -U quantbridge -d postgres -c 'DROP DATABASE quantbridge_w<N>_test'
EOF
  exit 0
fi

[ "${#SPECS[@]}" -gt 0 ] || die "에이전트를 하나 이상 줘라: --agent claude:<이름>  (--help)"

# ★인자 검증은 **부작용 전에** 끝낸다. 워크트리를 만들다가 3번째에서 죽으면 반쯤 만들어진
#   상태가 남는다. 아래 두 검사는 아무것도 만들기 전에 전건을 본다.
_seen=""
for spec in "${SPECS[@]}"; do
  case "$spec" in
    *:*) _k="${spec%%:*}"; _n="${spec#*:}" ;;
    *)   die "--agent 는 KIND:이름 형식이다 (예: claude:bl537). 받은 값: $spec" ;;
  esac
  [ -n "$_k" ] && [ -n "$_n" ] || die "--agent 값이 비었다: $spec"
  case "$_n" in */*|.*) die "워크트리 이름에 '/' 나 선행 '.' 는 쓰지 마라: $_n" ;; esac
  # 이름이 곧 워크트리이고 워크트리가 곧 슬롯이다. 같은 이름을 두 번 주면 두 pane 의 두
  # 에이전트가 **같은 워크트리와 같은 슬롯 테스트 DB** 를 공유한다 — 동시에 같은 파일을 고치고
  # 서로의 pytest DB 를 drop_all 한다. 슬롯 격리 전체가 그 순간 무의미해진다 (codex 리뷰 P2).
  case " $_seen " in
    *" $_n "*) die "--agent 이름이 중복이다: $_n
    이름 하나가 워크트리 하나이고 슬롯 하나다. 두 에이전트가 같은 워크트리와 같은 pytest DB 를
    공유하면 서로의 파일을 덮어쓰고 서로의 테이블을 드롭한다." ;;
  esac
  _seen="$_seen $_n"
done
[ "${#SPECS[@]}" -le "$MAX_AGENTS" ] || die "에이전트는 최대 $MAX_AGENTS 개다. 준 개수: ${#SPECS[@]}
    더 필요하면 함대를 하나 더 띄워라 — 한 화면에 6칸을 넣으면 아무것도 안 읽힌다."

# ── 1. 메인 체크아웃에서만 ──────────────────────────────────────────────────
# 워크트리를 만들고 컨테이너 상태를 보는 일이라 메인이 기준점이어야 한다.
GIT_DIR="$(git rev-parse --absolute-git-dir)"
GIT_COMMON="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
[ "$GIT_DIR" = "$GIT_COMMON" ] || die "여기는 워크트리다. 함대는 메인 체크아웃에서 띄워라:
    cd $(dirname "$GIT_COMMON") && scripts/herdr-fleet.sh ..."
MAIN_ROOT="$(git rev-parse --show-toplevel)"
cd "$MAIN_ROOT"

# 메인 체크아웃이 지금 어떤 브랜치인지는 상관없다 — 다른 세션이 다른 작업 중일 수 있고,
# 실제로 그런 상태에서 이 스크립트가 돌아야 한다. 중요한 건 워크트리가 갈라져 나올 **base** 다.
# 부트스트랩 존재 여부는 아래에서 생성된 워크트리마다 확인한다.
git rev-parse --verify --quiet "$BASE" >/dev/null || die "base ref '$BASE' 를 찾을 수 없다. --base 로 지정해라 (예: --base origin/main)."

echo "▶ herdr 함대"
echo "  main   : $MAIN_ROOT"
echo "  base   : $BASE ($(git rev-parse --short "$BASE"))"
echo "  agents : ${SPECS[*]}"

# ── 2. 워크트리 생성 + 부트스트랩 ───────────────────────────────────────────
# 슬롯 배정은 부트스트랩이 락 안에서 한다. 여기서 번호를 정하지 않는다 —
# 두 군데가 각자 정하면 그 순간 레지스트리가 두 벌이 된다.
KINDS=(); NAMES=(); PATHS=(); SLOTS=()
for spec in "${SPECS[@]}"; do
  case "$spec" in
    *:*) kind="${spec%%:*}"; name="${spec#*:}" ;;
    *)   die "--agent 는 KIND:이름 형식이다 (예: claude:bl537). 받은 값: $spec" ;;
  esac
  [ -n "$kind" ] && [ -n "$name" ] || die "--agent 값이 비었다: $spec"

  wt="$MAIN_ROOT/.claude/worktrees/$name"
  if [ -d "$wt" ]; then
    ok "워크트리 재사용 $name"
  else
    branch="wt/$name"
    if git rev-parse --verify --quiet "$branch" >/dev/null; then
      git worktree add "$wt" "$branch" >/dev/null || die "워크트리 생성 실패: $name"
      ok "워크트리 생성 $name (기존 브랜치 $branch)"
    else
      git worktree add "$wt" -b "$branch" "$BASE" >/dev/null || die "워크트리 생성 실패: $name"
      ok "워크트리 생성 $name ($branch ← $BASE)"
    fi
  fi

  # `.worktreeinclude` 는 Claude Code 의 EnterWorktree 기능이라 `git worktree add` 에는
  # 적용되지 않는다. --adopt-env 가 그 자리를 메운다 (없으면 부트스트랩이 fail-closed 로 죽는다).
  [ -x "$wt/scripts/worktree-bootstrap.sh" ] \
    || die "$name 의 브랜치에 scripts/worktree-bootstrap.sh 가 없다 — base 가 너무 오래됐다."
  ( cd "$wt" && ./scripts/worktree-bootstrap.sh --adopt-env "${BOOTSTRAP_ARGS[@]+"${BOOTSTRAP_ARGS[@]}"}" ) \
    || die "$name 부트스트랩 실패 — 위 출력을 봐라. 슬롯 없이 pane 을 띄우면 포트와 테스트 DB 가 겹친다."

  slot="$(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$wt/.worktree-slot" 2>/dev/null || true)"
  [ -n "$slot" ] || die "$name 에 슬롯이 기록되지 않았다."
  KINDS+=("$kind"); NAMES+=("$name"); PATHS+=("$wt"); SLOTS+=("$slot")
done

# ── 3. 현재 워크스페이스에 워커 자리 ────────────────────────────────────────
# root pane 의 cwd 를 나중에 바꿀 방법이 없으므로, 워크스페이스를 **첫 워크트리 경로로**
# 만들어 root 가 곧 에이전트 1 이 되게 한다. CONTROL 은 split 으로 메인을 잡는다.
[ -n "$LABEL" ] || LABEL="QB fleet"
echo "▶ 워크스페이스"
# ★워크스페이스를 만들지 않는다. 이 스크립트를 돌리는 **현재 탭의 워크스페이스**에 워커 탭을
#   이어 붙인다. 그러면 오케스트레이터(=이 탭, 메인 체크아웃, 슬롯 0)와 워커가 **같은 화면의
#   탭 줄**에 나란히 걸리고, CONTROL 을 따로 만들 필요가 없다.
#
#   ⚠️ `herdr pane current` 는 **이 스크립트를 실행한 그 pane** 을 돌려준다. 오케스트레이터가
#      메인 체크아웃에 있는지는 위 §1 이 이미 강제했다(git-dir == git-common-dir).
CUR_JSON="$(herdr pane current)" || die "현재 pane 을 못 읽었다 — herdr 세션 안에서 실행해라"
WS_ID="$(json_get "$CUR_JSON" result.pane.workspace_id 2>/dev/null \
  || json_get "$CUR_JSON" result.workspace_id)" \
  || die "현재 워크스페이스를 못 읽었다: $CUR_JSON"
CONTROL_PANE="$(json_get "$CUR_JSON" result.pane.pane_id 2>/dev/null \
  || json_get "$CUR_JSON" result.pane_id)" || die "현재 pane_id 를 못 읽었다"
ok "워크스페이스 $WS_ID 에 워커를 붙인다 (CONTROL = 현재 pane $CONTROL_PANE, 메인 슬롯 0, layout=$LAYOUT)"

# `herdr tab create` 는 응답에 `root_pane` 을 함께 준다 — pane 을 따로 찾을 필요가 없다.
# (cwd 로 역추적하면 같은 워크트리를 가리키는 낡은 pane 과 헷갈릴 수 있다.)
new_tab_pane() {  # new_tab_pane <cwd> <label> → 새 pane_id
  _out="$(herdr tab create --workspace "$WS_ID" --cwd "$1" --label "$2" --no-focus)" \
    || die "탭 생성 실패 ($2 → $1)"
  json_get "$_out" result.root_pane.pane_id \
    || die "새 탭의 pane_id 를 못 읽었다: $_out"
}

# ★`--ratio` 는 **쪼개지는(기존) pane 이 남기는** 비율이다 — 실측: 폭 298 을 `--ratio 0.25` 로
#   오른쪽 분할하면 기존이 75, 새 pane 이 223 이 된다. 추측하지 말고 이 규약을 지켜라.
split_pane() {  # split_pane <pane> <right|down> <ratio> <cwd> → 새 pane_id
  _out="$(herdr pane split --pane "$1" --direction "$2" --ratio "$3" --cwd "$4" --no-focus)" \
    || die "pane 분할 실패 ($1 → $2, ratio=$3, cwd=$4)"
  json_get "$_out" result.pane.pane_id \
    || die "새 pane_id 를 못 읽었다: $_out"
}

# n 등분 중 하나를 떼어낼 때 기존 pane 이 남겨야 할 비율 = 1/n.
_split_ratio() { awk -v n="$1" 'BEGIN { printf "%.6f", 1 / n }'; }

# panes 모드 배치 — CONTROL 을 좌상단으로 두고 **먼저 열로 쪼갠 뒤 각 열을 아래로** 쪼갠다.
# 반대 순서(행 먼저)로 하면 열 경계가 행마다 어긋나 그리드가 되지 않는다.
#
#   총 칸 = 워커 수 + 1(CONTROL). 2행 고정, 열 = ceil(총칸/2), 채우기는 **열 우선**.
#   워커 4벌이면:  ┌─────────┬─────────┬─────────┐
#                  │ CONTROL │ 워커2   │ 워커4   │   각 99×39 (창 298×78 실측)
#                  ├─────────┼─────────┼─────────┤
#                  │ 워커1   │ 워커3   │         │   마지막 열은 칸이 남으면 안 쪼갠다
#                  └─────────┴─────────┴─────────┘
grid_panes() {  # PATHS/NAMES/SLOTS 를 읽어 PANES 를 채운다
  local total rows cols base rem j c cap i_cell head cur cap_j
  total=$(( ${#PATHS[@]} + 1 ))
  rows=2; [ "$total" -le 2 ] && rows=1
  cols=$(( (total + rows - 1) / rows ))
  base=$(( total / cols )); rem=$(( total % cols ))

  # 1) 열 머리 — CONTROL 에서 오른쪽으로 cols-1 번. 각 열의 **첫 칸** cwd 를 그때 넣는다.
  local heads=("$CONTROL_PANE") caps=()
  for (( j = 0; j < cols; j++ )); do
    cap=$base; [ "$j" -lt "$rem" ] && cap=$(( cap + 1 ))
    caps+=("$cap")
  done
  cur="$CONTROL_PANE"; i_cell=${caps[0]}   # 열 0 이 이미 소비한 칸 수 (CONTROL 포함)
  for (( j = 1; j < cols; j++ )); do
    cur="$(split_pane "$cur" right "$(_split_ratio $(( cols - j + 1 )))" "${PATHS[$(( i_cell - 1 ))]}")"
    heads+=("$cur")
    i_cell=$(( i_cell + caps[j] ))
  done

  # 2) 각 열을 아래로 — 열의 2번째 칸부터. 워커 순서는 열 우선으로 이어붙는다.
  PANES=()
  i_cell=0
  for (( j = 0; j < cols; j++ )); do
    cap_j=${caps[$j]}
    head="${heads[$j]}"
    if [ "$j" -gt 0 ]; then PANES+=("$head"); fi   # 열 머리 = 그 열의 첫 워커 (열 0 은 CONTROL)
    for (( c = 1; c < cap_j; c++ )); do
      # 이 칸에 들어갈 워커의 전역 인덱스: 지금까지 배치한 워커 수
      head="$(split_pane "$head" down "$(_split_ratio $(( cap_j - c + 1 )))" "${PATHS[${#PANES[@]}]}")"
      PANES+=("$head")
    done
  done
}

PANES=()
if [ "$LAYOUT" = "panes" ]; then
  grid_panes
  ok "워커 pane ${#PANES[@]}개 생성 (현재 탭 그리드)"
else
  i=0
  for _p in "${PATHS[@]}"; do
    PANES+=("$(new_tab_pane "$_p" "${NAMES[$i]}·s${SLOTS[$i]}")")
    i=$((i + 1))
  done
  ok "워커 탭 ${#PANES[@]}개 생성"
fi
[ "${#PANES[@]}" -eq "${#PATHS[@]}" ] \
  || die "배치 수가 안 맞는다: pane ${#PANES[@]} vs 워크트리 ${#PATHS[@]} (layout=$LAYOUT)"

# ── 4. 에이전트 기동 + 라벨 ─────────────────────────────────────────────────
#
# ★kind 마다 승인 정책이 다르다. claude 는 `.worktreeinclude` 가 복사한
#   `.claude/settings.local.json` 의 allow 목록을 상속받아 그냥 돈다. codex 는 그런 게 없어서
#   **첫 명령부터 승인 프롬프트로 멈춘다**(실측 — 두 codex 워커가 `echo running > …` 에서 정지).
#   그래서 codex 에는 승인·샌드박스 정책을 명시로 준다.
#   ⚠️ `-s workspace-write` 는 **워크스페이스(=워크트리) 밖 쓰기와 네트워크를 막는다.** 그게
#      의도다 — 워커는 자기 워크트리만 만져야 한다. 대신 codex 워커에게 DB 를 타는 검증을
#      시키면 안 된다(localhost TCP 가 Operation not permitted 로 막힌다 — 실측).
#      docs/guides/fleet-orchestration.md §3 의 라우팅 표를 봐라.
agent_args_for() {
  case "$1" in
    codex) printf '%s\n' -a never -s workspace-write ;;
    *)     : ;;
  esac
}

echo "▶ 에이전트"
i=0
for p in "${PANES[@]}"; do
  _extra=()
  while IFS= read -r _a; do [ -n "$_a" ] && _extra+=("$_a"); done < <(agent_args_for "${KINDS[$i]}")

  # ★`tab create` 가 반환한 직후의 pane 은 아직 셸 초기화 중일 수 있다.
  #   그때 기동하면 `agent_pane_busy: not an available shell` 로 실패한다(실측). 순수한 레이스라
  #   잠깐 뒤 재시도하면 붙는다. 죽기 전에 몇 번 기다려 본다.
  _started=0; _err=""
  for _try in 1 2 3 4 5 6 7 8; do
    if [ "${#_extra[@]}" -gt 0 ]; then
      _err="$(herdr agent start "${NAMES[$i]}" --kind "${KINDS[$i]}" --pane "$p" -- "${_extra[@]}" 2>&1)" \
        && { _started=1; break; }
    else
      _err="$(herdr agent start "${NAMES[$i]}" --kind "${KINDS[$i]}" --pane "$p" 2>&1)" \
        && { _started=1; break; }
    fi
    case "$_err" in
      *agent_pane_busy*|*"not an available shell"*) sleep 2 ;;
      # ★이전 함대를 안 닫으면 같은 이름의 에이전트가 살아 있어 여기서 죽는다(실측).
      #   herdr 는 이름을 전역으로 잡으므로 워크스페이스가 달라도 충돌한다. 재시도로 안 풀린다.
      *agent_name_taken*)
        die "에이전트 이름 '${NAMES[$i]}' 이 이미 쓰이고 있다 — **이전 함대가 아직 살아 있다.**
    herdr 는 에이전트 이름을 전역으로 잡는다(워크스페이스가 달라도 충돌한다).
    위 에러의 workspace_id / pane_id 를 보고 그 화면을 먼저 닫아라:
      herdr workspace close <그 workspace_id>     # 옛 2×2 함대 잔재라면
      scripts/herdr-fleet.sh --teardown           # 이 워크스페이스의 워커 탭이라면
    ★닫기 전에 그 워커가 커밋 안 한 작업을 들고 있지 않은지 먼저 봐라:
      git -C $MAIN_ROOT/.claude/worktrees/${NAMES[$i]} status --short
    원문: $_err" ;;
      *) break ;;
    esac
  done
  [ "$_started" -eq 1 ] || die "에이전트 기동 실패: ${NAMES[$i]} (${KINDS[$i]}) @ $p
    $_err"

  # ★기동 성공 반환값만 믿으면 안 된다. 실측 — codex 가 기동 직후 **스스로 업데이트하고
  #   "Please restart Codex" 로 종료**했는데, 이 스크립트는 "✓ codex 기동" 이라고 보고했다.
  #   거짓 그린이다. 잠깐 뒤 herdr 이 아직 그 pane 을 에이전트로 보는지 확인한다.
  _alive=""
  for _try in 1 2 3 4 5 6; do
    _alive="$(herdr pane list 2>/dev/null | python3 -c '
import json,sys
want=sys.argv[1]
for p in json.load(sys.stdin)["result"]["panes"]:
    if p.get("pane_id")==want:
        print(p.get("agent","")); break
' "$p")"
    [ -n "$_alive" ] && break
    sleep 1
  done
  [ -n "$_alive" ] || die "${NAMES[$i]} ($p) 에 에이전트가 살아 있지 않다 — 기동 직후 종료했다.
    pane 을 직접 봐라: herdr pane read $p --source recent --lines 30
    (codex 는 보류 중이던 자기 업데이트를 설치하고 재시작을 요구하며 죽는 경우가 있다 — 실측.
     그때는 이 스크립트를 한 번 더 돌리면 된다.)"

  herdr pane rename "$p" "${NAMES[$i]}·s${SLOTS[$i]}·${KINDS[$i]}" >/dev/null || true
  ok "${KINDS[$i]} ${NAMES[$i]} → $p (슬롯 ${SLOTS[$i]}, agent=$_alive)"
  i=$((i + 1))
done

# CONTROL 은 이 스크립트를 돌린 그 탭이다 — 새로 만들지도, 이름을 바꾸지도 않는다.
# (사람이 붙여 둔 탭 이름을 스크립트가 덮어쓰면 안 된다.)

# ── 5. 요약 ─────────────────────────────────────────────────────────────────
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf '%-14s %-6s %-6s %-6s %s\n' "PANE" "SLOT" "FE" "BE" "CWD"
i=0
for p in "${PANES[@]}"; do
  printf '%-14s %-6s %-6s %-6s %s\n' \
    "$p" "${SLOTS[$i]}" "$((3100 + SLOTS[i]))" "$((8100 + SLOTS[i]))" "${PATHS[$i]}"
  i=$((i + 1))
done
printf '%-14s %-6s %-6s %-6s %s\n' "$CONTROL_PANE" "0" "3100" "8100" "$MAIN_ROOT (CONTROL = 현재 자리)"
cat <<EOF

CONTROL 에서만 되는 것 — celery 경유 검증(백테스트·라이브신호·옵티마이저) · make up/seed/migrate ·
게이트 종합 · 머지. 워크트리 pane 에서 그걸 시도하면 Makefile 가드가 거부한다(make 종료 코드 2).

정리:  scripts/herdr-fleet.sh --teardown        # 워커 화면만 닫는다 (CONTROL 자리는 유지)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
