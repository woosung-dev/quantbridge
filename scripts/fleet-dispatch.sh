#!/usr/bin/env bash
#
# 함대 워커에 일을 던지고 상태를 본다. 오케스트레이터(CONTROL, 슬롯 0)에서만 돈다.
#
# 사용법:
#   scripts/fleet-dispatch.sh --run <이름>                 # tasks/*.md 를 각 워커 pane 에 주입
#   scripts/fleet-dispatch.sh --run <이름> --status        # 상태 종합 (반복 호출용)
#   scripts/fleet-dispatch.sh --run <이름> --only a,b      # 일부만 재분배
#   scripts/fleet-dispatch.sh --run <이름> --force         # idle 이 아닌 워커에도 주입(입력이 섞인다)
#
# 계약과 절차는 docs/guides/fleet-orchestration.md. 여기 복사하지 않는다 — 두 벌이 되면 갈린다.
#
# ★워커가 만지는 것은 **전부 그 워커의 워크트리 안**이다:
#
#   <메인>/.claude/fleet/<run>/tasks/<worker>.md   오케스트레이터가 쓰는 원본 (SSOT)
#   <워크트리>/.claude/fleet/<run>/task.md         분배가 복사해 넣는다 (워커가 읽는 것)
#   <워크트리>/.claude/fleet/<run>/status          워커가 쓴다  running | done | blocked
#   <워크트리>/.claude/fleet/<run>/report.md       워커가 쓴다
#
# 메인에 두지 않는 이유 — codex 워커는 `-s workspace-write` 샌드박스라 **워크스페이스 밖 쓰기가
# 거부된다.** 실측에서 codex 두 기가 임무를 다 끝내고도 `operation not permitted` 로 보고 파일도
# `blocked` 기록도 못 남겨 **결과가 통째로 유실**됐다. 워크트리 안으로 옮기면 codex 는 좁은
# 샌드박스 그대로 보고할 수 있고, "워커는 자기 워크트리만 만진다" 는 불변식도 강해진다.
# (`.claude/*` 는 gitignore 라 브랜치가 더러워지지 않는다.)
#
# 워커 이름 = 워크트리 이름 = herdr-fleet.sh --agent <kind>:<이름> 의 그 이름.
# pane 은 이름으로 찾지 않고 **cwd 로 역추적**한다 — pane 라벨은 사람이 바꿀 수 있어 신뢰할 수 없다.

set -euo pipefail

die() { echo "✗ $*" >&2; exit 1; }
ok()  { echo "  ✓ $*"; }

RUN=""; STATUS=0; FORCE=0; ONLY=""

# 값이 필요한 옵션은 값의 존재를 먼저 본다 — `--run` 만 주고 값을 빼면 `shift 2` 가 실패해
# `set -e` 로 **메시지 없이** 죽는다(worktree-bootstrap.sh 에서 codex 가 잡은 것과 같은 패턴).
need_val() { [ "$1" -ge 2 ] || { echo "✗ $2 에 값이 없다" >&2; exit 2; }; }

while [ $# -gt 0 ]; do
  case "$1" in
    --run)    need_val $# --run;  RUN="$2"; shift 2 ;;
    --status) STATUS=1; shift ;;
    --force)  FORCE=1; shift ;;
    --only)   need_val $# --only; ONLY="$2"; shift 2 ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) die "알 수 없는 인자: $1  (--help)" ;;
  esac
done
[ -n "$RUN" ] || die "--run <이름> 이 필요하다. (--help)"
# ★RUN 은 경로 조각으로 그대로 쓰인다. `--run ../../../b` 를 주면 워커 A 의 출력 경로가
#   워커 B 의 워크트리로 정규화되고, A 에게 B 의 task/status/report 를 읽고 쓰라는 프롬프트가
#   나간다 — 산출물 격리 계약이 통째로 깨진다 (codex 리뷰 P2). 식별자만 받는다.
case "$RUN" in
  *[!A-Za-z0-9._-]*|.*|"") die "--run 은 영숫자·점·밑줄·하이픈만 쓸 수 있다 (경로 조각 금지): $RUN" ;;
esac

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

# 워커 산출물이 놓이는 곳 — 그 워커의 **워크트리 안**이다 (머리말 참조).
wt_out() { printf '%s/.claude/fleet/%s' "$MAIN_ROOT/.claude/worktrees/$1" "$RUN"; }

# 워커 목록 = tasks/*.md 의 basename. --only 로 좁힐 수 있다.
WORKERS=()
for f in "$RUN_DIR"/tasks/*.md; do
  [ -f "$f" ] || continue
  n="$(basename "$f" .md)"
  # 워커 이름도 경로 조각이 된다 (tasks/<n>.md → <워크트리>/.claude/fleet/<run>/).
  case "$n" in *[!A-Za-z0-9._-]*|.*) die "워커 이름에 경로 문자를 쓸 수 없다: $n" ;; esac
  if [ -n "$ONLY" ]; then
    case ",$ONLY," in *",$n,"*) ;; *) continue ;; esac
  fi
  WORKERS+=("$n")
done
[ "${#WORKERS[@]}" -gt 0 ] || die "대상 워커가 없다 (tasks/*.md 확인, --only 는 '$ONLY')."

# pane 을 cwd 로 역추적한다. 같은 cwd 가 둘이면 어느 쪽인지 모르므로 die 한다.
# ★에이전트가 **붙어 있는** pane 만 후보다. cwd 만 보면, 그 워크트리를 cwd 로 둔 채 남아 있는
#   오래된 workspace 의 셸 pane 하나에 프롬프트가 그대로 주입된다 (codex 리뷰 P2).
#   후보가 0 개거나 2 개 이상이면 실패한다 — 어디로 갈지 모르는 상태로 주입하지 않는다.
#   workspace_id 도 함께 내보내 호출자가 워커들이 한 화면에 있는지 대조하게 한다.
pane_of() {  # pane_of <워크트리 절대경로> → "<pane_id> <workspace_id>"
  herdr pane list 2>/dev/null | python3 -c '
import json,sys
want=sys.argv[1]
hits=[p for p in json.load(sys.stdin)["result"]["panes"]
      if p.get("cwd")==want and p.get("agent")]
if len(hits)!=1: sys.exit(1)
print(hits[0]["pane_id"], hits[0].get("workspace_id",""))
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
    _pw="$(pane_of "$wt" || true)"; pane="${_pw%% *}"
    hs="-"; [ -n "$pane" ] && hs="$(agent_status_of "$pane")"
    out="$(wt_out "$w")"
    sig="-"; [ -f "$out/status" ] && sig="$(tr -d '\n' < "$out/status")"
    rep="-"; [ -s "$out/report.md" ] && rep="있음"
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

  _pw="$(pane_of "$wt")" || die "$w 의 pane 을 못 찾았다 (cwd=$wt, 에이전트가 붙은 pane 기준).
    함대가 떠 있는지 확인해라: herdr pane list
    (에이전트 없는 셸 pane 은 후보에서 뺀다 — stale workspace 에 잘못 주입되는 것을 막는다.)"
  pane="${_pw%% *}"; pane_ws="${_pw##* }"
  # 워커들이 **한 화면**에 있어야 한다. 서로 다른 workspace 에 흩어져 있으면 그중 하나는
  # 오래된 함대의 잔재일 가능성이 크고, 그쪽으로 주입하면 엉뚱한 에이전트가 일을 받는다.
  if [ -z "${FLEET_WS:-}" ]; then
    FLEET_WS="$pane_ws"
  elif [ "$pane_ws" != "$FLEET_WS" ]; then
    die "$w 의 pane($pane)이 다른 workspace($pane_ws)에 있다 — 나머지 워커는 $FLEET_WS 다.
    오래된 함대가 남아 있을 수 있다. 정리하고 다시 띄워라: herdr workspace list"
  fi

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

  # task 원본은 메인에 두되 **워크트리로 복사**한다. 워커가 읽고 쓰는 것이 전부 자기 워크트리
  # 안에 있어야 codex 의 `-s workspace-write` 샌드박스에서도 보고가 남는다.
  OUT="$(wt_out "$w")"
  mkdir -p "$OUT"
  # 이름 검증을 통과했더라도, 실제 경로가 그 워크트리 **안**인지 한 번 더 확인한다.
  # 심볼릭 링크나 미래의 이름 규칙 변경이 이 불변식을 조용히 깨는 것을 막는다.
  _out_real="$(cd "$OUT" && pwd -P)" || die "$w 출력 경로를 정규화할 수 없다: $OUT"
  _wt_real="$(cd "$wt" && pwd -P)"   || die "$w 워크트리를 정규화할 수 없다: $wt"
  case "$_out_real/" in
    "$_wt_real"/*) ;;
    *) die "$w 의 출력 경로가 워크트리 밖이다 — 분배를 중단한다.
    출력: $_out_real
    워크트리: $_wt_real" ;;
  esac
  cp "$RUN_DIR/tasks/$w.md" "$OUT/task.md"

  # ★`pending` 은 **주입 전에** 쓴다. 주입 뒤에 쓰면, 지시대로 즉시 `running` 을 쓴 워커의 값을
  #   덮어써서 폴링이 오랫동안 거짓 `pending` 을 보여준다 (codex 리뷰 P2).
  printf 'pending\n' > "$OUT/status"

  # 계약은 프롬프트에 복사하지 않는다. 읽게 시킨다 — 복사하면 두 벌이 되어 갈린다.
  read -r -d '' PROMPT <<EOF || true
너는 fleet 워커 '$w' 다. 워크트리 $wt (슬롯 $slot) 에서만 작업한다.
아래 경로는 전부 그 워크트리 안이다 — 밖으로 나가지 마라.

다음을 순서대로 읽고 그대로 수행해라:
  1) $CONTRACT  — §1 역할 · §3 라우팅 · §7 워커 규칙
  2) $OUT/task.md  — 네 임무와 수용 기준

시작하면 즉시:
  echo running > $OUT/status

끝나면 $OUT/report.md 에 보고를 쓰고:
  echo done > $OUT/status

커밋까지만 한다. 푸시·PR·머지는 오케스트레이터 몫이다. 사용자에게 질문하지 마라 —
판단이 막히면 blocked 를 쓰고 이유를 보고에 남겨라.
EOF

  # 상태 확인과 주입 사이에 워커가 working 으로 바뀔 수 있다(TOCTOU — codex 리뷰 P2).
  # 창을 없앨 수는 없지만 주입 **직전에** 한 번 더 봐서 크게 줄인다.
  if [ "$FORCE" -ne 1 ]; then
    hs2="$(agent_status_of "$pane")"
    [ "$hs2" = "idle" ] || die "$w ($pane) 가 확인 직후 '$hs2' 로 바뀌었다 — 주입을 취소했다.
    다시 시도하거나, 정말 넣어야 하면 --force."
  fi
  herdr agent prompt "$pane" "$PROMPT" >/dev/null || die "$w 주입 실패 ($pane)"
  ok "$w → $pane (슬롯 $slot)"
done

echo
echo "폴링:  scripts/fleet-dispatch.sh --run $RUN --status"
