#!/usr/bin/env bash
#
# 함대 워커에 일을 던지고 상태를 본다. 오케스트레이터(CONTROL, 슬롯 0)에서만 돈다.
#
# 사용법:
#   scripts/fleet-dispatch.sh --run <이름>                 # tasks/*.md 를 각 워커 pane 에 주입
#   scripts/fleet-dispatch.sh --run <이름> --status        # 상태 종합 (반복 호출용)
#   scripts/fleet-dispatch.sh --run <이름> --only a,b      # 일부만 재분배
#   scripts/fleet-dispatch.sh --run <이름> --force         # working 중인 워커에도 주입(위험)
#
# 계약과 절차는 docs/guides/fleet-orchestration.md. 여기 복사하지 않는다 — 두 벌이 되면 갈린다.
#
#   .claude/fleet/<run>/tasks/<worker>.md      오케스트레이터가 쓴다 (수용 기준 포함)
#   .claude/fleet/<run>/signals/<worker>.status  워커가 쓴다  running | done | blocked
#   .claude/fleet/<run>/reports/<worker>.md      워커가 쓴다
#
# 워커 이름 = 워크트리 이름 = herdr-fleet.sh --agent <kind>:<이름> 의 그 이름.
# pane 은 이름으로 찾지 않고 **cwd 로 역추적**한다 — pane 라벨은 사람이 바꿀 수 있어 신뢰할 수 없다.

set -euo pipefail

die() { echo "✗ $*" >&2; exit 1; }
ok()  { echo "  ✓ $*"; }

RUN=""; STATUS=0; FORCE=0; ONLY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --run)    RUN="${2:-}"; shift 2 ;;
    --status) STATUS=1; shift ;;
    --force)  FORCE=1; shift ;;
    --only)   ONLY="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) die "알 수 없는 인자: $1  (--help)" ;;
  esac
done
[ -n "$RUN" ] || die "--run <이름> 이 필요하다. (--help)"

command -v herdr >/dev/null 2>&1 || die "herdr 가 없다."
herdr status server >/dev/null 2>&1 || die "herdr 서버가 안 떠 있다."

# 오케스트레이터는 메인 체크아웃이다. 워크트리에서 돌리면 상대 경로가 전부 어긋난다.
GIT_DIR="$(git rev-parse --absolute-git-dir)"
GIT_COMMON="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
[ "$GIT_DIR" = "$GIT_COMMON" ] || die "여기는 워크트리다. 분배는 메인 체크아웃(CONTROL)에서 해라:
    cd $(dirname "$GIT_COMMON")"
MAIN_ROOT="$(git rev-parse --show-toplevel)"
cd "$MAIN_ROOT"

RUN_DIR="$MAIN_ROOT/.claude/fleet/$RUN"
[ -d "$RUN_DIR/tasks" ] || die "$RUN_DIR/tasks 가 없다.
    먼저 오케스트레이터가 워커별 task 파일을 쓴다 — 수용 기준을 착수 전에 동결하는 것이 이 구조의 핵심이다
    (docs/guides/fleet-orchestration.md §1)."
mkdir -p "$RUN_DIR/signals" "$RUN_DIR/reports"

# 워커 목록 = tasks/*.md 의 basename. --only 로 좁힐 수 있다.
WORKERS=()
for f in "$RUN_DIR"/tasks/*.md; do
  [ -f "$f" ] || continue
  n="$(basename "$f" .md)"
  if [ -n "$ONLY" ]; then
    case ",$ONLY," in *",$n,"*) ;; *) continue ;; esac
  fi
  WORKERS+=("$n")
done
[ "${#WORKERS[@]}" -gt 0 ] || die "대상 워커가 없다 (tasks/*.md 확인, --only 는 '$ONLY')."

# pane 을 cwd 로 역추적한다. 같은 cwd 가 둘이면 어느 쪽인지 모르므로 die 한다.
pane_of() {  # pane_of <워크트리 절대경로> → pane_id
  herdr pane list 2>/dev/null | python3 -c '
import json,sys
want=sys.argv[1]
hits=[p for p in json.load(sys.stdin)["result"]["panes"] if p.get("cwd")==want]
if len(hits)!=1: sys.exit(1)
print(hits[0]["pane_id"])
' "$1"
}
agent_status_of() {
  herdr pane list 2>/dev/null | python3 -c '
import json,sys
want=sys.argv[1]
for p in json.load(sys.stdin)["result"]["panes"]:
    if p.get("pane_id")==want:
        print(p.get("agent_status","unknown")); break
else:
    print("unknown")
' "$1"
}

# ── --status ────────────────────────────────────────────────────────────────
# herdr agent_status 는 **프로세스**가 살아 있는지, signal 은 **일**이 어디까지 갔는지를 말한다.
# 둘은 다르다. 나란히 보여준다.
if [ "$STATUS" -eq 1 ]; then
  # 커밋 수는 origin/main 대비다. 워커 base 가 origin/main 이 아니면(예: 스택 브랜치) 그 차이도
  # 함께 세므로, 이 숫자를 "워커가 만든 커밋 수" 로 읽지 마라. 판정은 diff 로 한다.
  printf '%-12s %-9s %-9s %-10s %-7s %s\n' WORKER PANE HERDR SIGNAL REPORT "BRANCH(vs origin/main)"
  for w in "${WORKERS[@]}"; do
    wt="$MAIN_ROOT/.claude/worktrees/$w"
    pane="$(pane_of "$wt" || true)"
    hs="-"; [ -n "$pane" ] && hs="$(agent_status_of "$pane")"
    sig="-"; [ -f "$RUN_DIR/signals/$w.status" ] && sig="$(tr -d '\n' < "$RUN_DIR/signals/$w.status")"
    rep="-"; [ -s "$RUN_DIR/reports/$w.md" ] && rep="있음"
    br="-"
    if git rev-parse --verify --quiet "wt/$w" >/dev/null; then
      br="wt/$w($(git rev-list --count "origin/main..wt/$w" 2>/dev/null || echo '?'))"
    fi
    printf '%-12s %-9s %-9s %-10s %-7s %s\n' "$w" "${pane:--}" "$hs" "$sig" "$rep" "$br"
  done
  echo
  echo "  herdr blocked = 대개 권한 프롬프트다. 워커가 스스로 못 푼다 — 그 pane 에 사람이 가야 한다."
  echo "  signal done + report 있음 → 통합 대상 (docs/guides/fleet-orchestration.md §5)"
  exit 0
fi

# ── 분배 ────────────────────────────────────────────────────────────────────
echo "▶ 분배 — run '$RUN'"
for w in "${WORKERS[@]}"; do
  wt="$MAIN_ROOT/.claude/worktrees/$w"
  [ -d "$wt" ] || die "워크트리가 없다: $wt
    먼저 띄워라: scripts/herdr-fleet.sh --agent claude:$w ..."
  [ -f "$wt/.worktree-slot" ] || die "$w 에 슬롯이 없다 — 부트스트랩이 안 됐다."
  slot="$(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$wt/.worktree-slot")"

  pane="$(pane_of "$wt")" || die "$w 의 pane 을 못 찾았다 (cwd=$wt).
    함대가 떠 있는지 확인해라: herdr pane list"

  # working 중에 주입하면 입력이 섞인다. idle 이 아니면 거부한다.
  hs="$(agent_status_of "$pane")"
  if [ "$hs" != "idle" ] && [ "$FORCE" -ne 1 ]; then
    die "$w ($pane) 상태가 '$hs' 다 — idle 일 때만 주입한다.
    working 이면 아직 일하는 중이고, blocked 면 권한 프롬프트에 걸려 사람이 눌러야 한다.
    그래도 넣으려면 --force (입력이 섞일 수 있다)."
  fi

  # ★계약 문서는 **워커 워크트리** 것을 가리킨다. 메인 경로를 가리키면 안 된다 —
  #   `docs/guides/fleet-orchestration.md` 는 트래킹 파일이고, 메인 체크아웃은 전혀 다른
  #   (더 오래된) 브랜치에 있을 수 있다. 실제로 첫 실전에서 그 경로가 존재하지 않아
  #   두 워커가 모두 "없는 파일을 읽으라는 지시" 를 받았다(워커가 스스로 적발해 보고했다).
  #   존재를 여기서 확인해 그 침묵 실패를 막는다.
  CONTRACT="$wt/docs/guides/fleet-orchestration.md"
  [ -f "$CONTRACT" ] || die "$w 의 브랜치에 계약 문서가 없다: $CONTRACT
    base 가 이 문서를 포함한 커밋이어야 한다. 워커에게 없는 파일을 읽으라고 시키면
    워커는 제 나름대로 해석하고, 그건 계약이 아니다."

  # 계약은 프롬프트에 복사하지 않는다. 읽게 시킨다 — 복사하면 두 벌이 되어 갈린다.
  read -r -d '' PROMPT <<EOF || true
너는 fleet 워커 '$w' 다. 워크트리 $wt (슬롯 $slot) 에서만 작업한다.

다음을 순서대로 읽고 그대로 수행해라:
  1) $CONTRACT  — §1 역할 · §3 라우팅 · §7 워커 규칙
  2) $RUN_DIR/tasks/$w.md  — 네 임무와 수용 기준

시작하면 즉시:
  echo running > $RUN_DIR/signals/$w.status

끝나면 $RUN_DIR/reports/$w.md 에 보고를 쓰고:
  echo done > $RUN_DIR/signals/$w.status

커밋까지만 한다. 푸시·PR·머지는 오케스트레이터 몫이다. 사용자에게 질문하지 마라 —
판단이 막히면 blocked 를 쓰고 이유를 보고에 남겨라.
EOF

  herdr agent prompt "$pane" "$PROMPT" >/dev/null || die "$w 주입 실패 ($pane)"
  printf 'pending\n' > "$RUN_DIR/signals/$w.status"
  ok "$w → $pane (슬롯 $slot)"
done

echo
echo "폴링:  scripts/fleet-dispatch.sh --run $RUN --status"
