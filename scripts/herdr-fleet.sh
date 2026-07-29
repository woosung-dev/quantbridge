#!/usr/bin/env bash
#
# herdr 워크트리 함대 부팅 — 한 화면 2×2. 워커 1~4, 남는 칸은 CONTROL(메인, 슬롯 0).
#
# 사용법:
#   scripts/herdr-fleet.sh --agent claude:bl537 --agent claude:bl536 --agent codex:impl
#   scripts/herdr-fleet.sh --agent claude:a --agent claude:b --agent codex:c --agent codex:review
#     └ 4개면 네 칸 모두 워커고 CONTROL pane 이 없다 (경고가 뜬다)
#   scripts/herdr-fleet.sh --agent claude:a --agent codex:b --label "QB 실험"
#   scripts/herdr-fleet.sh --agent claude:a --base origin/main --skip-deps
#   scripts/herdr-fleet.sh --teardown w7          # 워크스페이스 닫기 (워크트리는 안 지운다)
#
#   ┌───────────────┬───────────────┐
#   │ 에이전트 1    │ 에이전트 2    │   각 칸 = 워크트리 1벌 = 슬롯 1벌
#   │ (워크트리)    │ (워크트리)    │   (FE 3100+N / BE 8100+N / quantbridge_wN_test)
#   ├───────────────┼───────────────┤
#   │ 에이전트 3    │ CONTROL       │   CONTROL = 메인 체크아웃(슬롯 0).
#   │ (워크트리)    │ (메인, 슬롯 0)│   celery 경유 검증·게이트·머지는 여기서만 된다.
#   └───────────────┴───────────────┘
#
# ★프롬프트는 주입하지 않는다. 부팅까지가 이 스크립트의 일이고, 첫 지시는 사람이 한다.
#   자동 주입이 필요해지면 herdr 가 이미 갖고 있다 (이 스크립트를 고치기 전에 읽어라):
#     herdr agent prompt <pane_id> "<지시>" --wait --until done --timeout 1800000
#     herdr agent wait   <pane_id> --until blocked --timeout 600000
#     herdr agent read   <pane_id> --source recent --lines 200
#   지금 넣지 않는 이유 — 이 레포는 "자동화된 거짓 그린" 을 반복해서 밟았다. 사람이 루프 안에
#   있는 상태로 1단계를 먼저 굳힌다.
#
# ⚠️ CONTROL 이 따로 있는 이유 — 워크트리에서는 celery 경유 검증(백테스트·라이브신호·
#    옵티마이저)이 **구조적으로 불가능**하다. worker 컨테이너가 메인의 `./backend/src` 를
#    bind-mount 하므로 워크트리 코드는 실행되지 않는다. 테스트는 통과하는데 돌아간 게 내
#    코드가 아닌 침묵 실패다. 상세: docs/reference/worktree-parallel.md §3.

set -euo pipefail

die() { echo "✗ $*" >&2; exit 1; }
ok()  { echo "  ✓ $*"; }

# 3 이면 2×2 의 남은 한 칸이 CONTROL(메인, 슬롯 0) 이다.
# 4 를 주면 네 칸 모두 워커가 되고 **CONTROL pane 이 없다** — 그때 celery 검증·게이트·머지는
# 오케스트레이터 세션이 `cd <메인>` 으로 직접 해야 한다. 화면에 그 자리가 안 보이므로 경고한다.
MAX_AGENTS=4
SPECS=()
LABEL=""
BASE="origin/main"
CONTROL_AGENT=""
BOOTSTRAP_ARGS=()
TEARDOWN=""

while [ $# -gt 0 ]; do
  case "$1" in
    --agent)         SPECS+=("${2:-}"); shift 2 ;;
    --label)         LABEL="${2:-}"; shift 2 ;;
    --base)          BASE="${2:-}"; shift 2 ;;
    --control-agent) CONTROL_AGENT="${2:-}"; shift 2 ;;
    --skip-deps)     BOOTSTRAP_ARGS+=(--skip-deps); shift ;;
    --teardown)      TEARDOWN="${2:-}"; shift 2 ;;
    -h|--help)       sed -n '2,30p' "$0"; exit 0 ;;
    *)               die "알 수 없는 인자: $1  (--help)" ;;
  esac
done

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
  herdr workspace close "$TEARDOWN" >/dev/null || die "워크스페이스 $TEARDOWN 닫기 실패"
  ok "워크스페이스 $TEARDOWN 닫음"
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
[ "${#SPECS[@]}" -le "$MAX_AGENTS" ] || die "에이전트는 최대 $MAX_AGENTS 개다 (2×2 니까). 준 개수: ${#SPECS[@]}
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
  case "$name" in */*|.*) die "워크트리 이름에 '/' 나 선행 '.' 는 쓰지 마라: $name" ;; esac

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

# ── 3. 워크스페이스 + 2×2 pane ──────────────────────────────────────────────
# root pane 의 cwd 를 나중에 바꿀 방법이 없으므로, 워크스페이스를 **첫 워크트리 경로로**
# 만들어 root 가 곧 에이전트 1 이 되게 한다. CONTROL 은 split 으로 메인을 잡는다.
[ -n "$LABEL" ] || LABEL="QB fleet"
echo "▶ 워크스페이스"
WS_JSON="$(herdr workspace create --label "$LABEL" --cwd "${PATHS[0]}" --focus)" \
  || die "워크스페이스 생성 실패"
WS_ID="$(json_get "$WS_JSON" result.workspace.workspace_id)" || die "workspace_id 를 못 읽었다: $WS_JSON"
P1="$(json_get "$WS_JSON" result.root_pane.pane_id)"       || die "root pane_id 를 못 읽었다: $WS_JSON"
ok "$LABEL ($WS_ID)  root pane $P1"

# `herdr pane split` 은 right / down 만 지원한다. 2×2 는 오른쪽 한 번 + 각 열 아래 한 번.
split_pane() {  # split_pane <기준 pane> <right|down> <cwd> → 새 pane_id
  _out="$(herdr pane split "$1" --direction "$2" --cwd "$3" --no-focus)" \
    || die "pane split 실패 ($1 $2)"
  json_get "$_out" result.pane.pane_id 2>/dev/null \
    || json_get "$_out" result.pane_id \
    || die "새 pane_id 를 못 읽었다: $_out"
}

PANES=("$P1")
CONTROL_PANE=""
case "${#SPECS[@]}" in
  1) CONTROL_PANE="$(split_pane "$P1" right "$MAIN_ROOT")" ;;
  2) P2="$(split_pane "$P1" right "${PATHS[1]}")"; PANES+=("$P2")
     CONTROL_PANE="$(split_pane "$P2" down "$MAIN_ROOT")" ;;
  3) P2="$(split_pane "$P1" right "${PATHS[1]}")"; PANES+=("$P2")
     P3="$(split_pane "$P1" down "${PATHS[2]}")";  PANES+=("$P3")
     CONTROL_PANE="$(split_pane "$P2" down "$MAIN_ROOT")" ;;
  4) P2="$(split_pane "$P1" right "${PATHS[1]}")"; PANES+=("$P2")
     P3="$(split_pane "$P1" down "${PATHS[2]}")";  PANES+=("$P3")
     P4="$(split_pane "$P2" down "${PATHS[3]}")";  PANES+=("$P4") ;;
esac
if [ -n "$CONTROL_PANE" ]; then
  ok "pane ${#PANES[@]} + CONTROL($CONTROL_PANE)"
else
  ok "pane ${#PANES[@]} — ★CONTROL 없음"
  echo "  ! 네 칸 모두 워커다. celery 경유 검증·게이트·머지를 할 자리가 화면에 없다." >&2
  echo "    오케스트레이터 세션이 'cd $MAIN_ROOT' 로 직접 해야 한다." >&2
fi

# ── 4. 에이전트 기동 + 라벨 ─────────────────────────────────────────────────
echo "▶ 에이전트"
i=0
for p in "${PANES[@]}"; do
  herdr agent start "${NAMES[$i]}" --kind "${KINDS[$i]}" --pane "$p" >/dev/null \
    || die "에이전트 기동 실패: ${NAMES[$i]} (${KINDS[$i]}) @ $p"
  herdr pane rename "$p" "${NAMES[$i]}·s${SLOTS[$i]}·${KINDS[$i]}" >/dev/null || true
  ok "${KINDS[$i]} ${NAMES[$i]} → $p (슬롯 ${SLOTS[$i]})"
  i=$((i + 1))
done

if [ -n "$CONTROL_PANE" ]; then
  if [ -n "$CONTROL_AGENT" ]; then
    herdr agent start control --kind "$CONTROL_AGENT" --pane "$CONTROL_PANE" >/dev/null \
      || die "CONTROL 에이전트 기동 실패"
    ok "$CONTROL_AGENT control → $CONTROL_PANE (슬롯 0)"
  fi
  herdr pane rename "$CONTROL_PANE" "CONTROL·s0·main" >/dev/null || true
elif [ -n "$CONTROL_AGENT" ]; then
  die "--control-agent 는 워커가 4개일 때 쓸 수 없다 (CONTROL pane 이 없다). 워커를 3개로 줄여라."
fi

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
[ -n "$CONTROL_PANE" ] && printf '%-14s %-6s %-6s %-6s %s\n' "$CONTROL_PANE" "0" "3100" "8100" "$MAIN_ROOT (CONTROL)"
cat <<EOF

CONTROL 에서만 되는 것 — celery 경유 검증(백테스트·라이브신호·옵티마이저) · make up/seed/migrate ·
게이트 종합 · 머지. 워크트리 pane 에서 그걸 시도하면 Makefile 가드가 거부한다(make 종료 코드 2).

정리:  scripts/herdr-fleet.sh --teardown $WS_ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
