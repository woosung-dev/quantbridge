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
# 계약과 절차는 docs/reference/operations/workflows/fleet-orchestration.md. 여기 복사하지 않는다 — 두 벌이 되면 갈린다.
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
    (docs/reference/operations/workflows/fleet-orchestration.md §1)."

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
# ★조회 실패는 **`unknown` 으로 수렴**시킨다 (R2-②).
#   이 스크립트는 `set -euo pipefail` 이다. 예전 모양(본문이 파이프라인 한 줄)에서는
#   `herdr pane list` 가 일시적으로 실패하거나 JSON 이 깨지면 `hs="$(agent_status_of "$pane")"` 가
#   실패해 **분배 전체가 즉시 종료**됐다. pane 하나의 조회 오류가 나머지 워커 분배와 R1-② 의
#   실패 요약까지 함께 없앤다. `unknown` 은 이미 "주입하지 않는다" 로 처리되므로(qb_injectable)
#   그 경로로 보내 "실패해도 끝까지 분배한다" 는 규율과 일관되게 만든다.
#
# ★★무엇이 실제로 수렴을 만드는가 (실측으로 확인했다 — 착각하기 쉽다)
#   bash 3.2 에서 `set -e` 는 **명령 치환 서브셸 안에서는 발화하지 않는다.** 즉 이 함수 안의
#   실패한 대입은 함수를 죽이지 않는다. 죽는 지점은 **호출부**다: `$( … )` 의 종료 코드는
#   서브셸의 **마지막 명령** 상태이므로, 본문이 파이프라인으로 끝나면 그 실패가 그대로
#   치환의 상태가 되어 호출부 대입이 실패하고 최상위 errexit 이 발화한다.
#   → **이 함수는 반드시 성공하는 명령(아래 `echo`)으로 끝나야 한다.** 그게 수렴의 본체다.
#     `|| true` 는 보조 방어일 뿐이고, 그것만으로는 이 시나리오를 못 막는다(변이로 확인했다).
#   즉 판정은 반환값이 아니라 **찍은 문자열**로 한다. 마지막 줄을 파이프라인으로 바꾸지 마라.
agent_status_of() {
  local st=""
  st="$(herdr pane list 2>/dev/null | python3 -c '
import json,sys
want=sys.argv[1]
try:
    panes=json.load(sys.stdin)["result"]["panes"]
except Exception:
    print("unknown"); sys.exit(0)
for p in panes:
    if p.get("pane_id")==want:
        print(p.get("agent_status") or "unknown"); break
else:
    print("unknown")
' "$1" 2>/dev/null || true)"
  st="${st%%$'\n'*}"          # 여러 줄이 와도 첫 줄만 (방어)
  # ★이 if 가 이 함수의 **마지막 명령**이어야 한다 (위 주석 — 수렴의 본체다).
  if [ -z "$st" ]; then
    echo unknown
  else
    echo "$st"
  fi
}

# ★주입 가능한 상태 (BL-552 ②-g). `idle` **또는** `done`.
#   계약(docs/reference/operations/workflows/fleet-orchestration.md §2)이 `done` = "**턴**이 끝났다. 태스크 완료가 아니다" 로
#   정의한다 — 즉 입력 대기 상태다. 실측에서 워커가 프롬프트를 받고 아무 작업 없이 턴만 끝내
#   (변경 0·커밋 0·report 0) `done` 이 됐는데 재분배가 `idle 일 때만` 으로 거부돼 `--force` 로
#   뚫어야 했다. 거부해야 하는 것은:
#     working  지금 돌고 있다 → 주입하면 입력이 섞인다
#     blocked  권한 프롬프트에 걸렸다 → 사람이 그 pane 에 가야 한다
#     unknown  herdr 이 에이전트를 못 본다 → 대개 프로세스가 죽었다
qb_injectable() {  # qb_injectable <agent_status>
  case "$1" in
    idle|done) return 0 ;;
    *) return 1 ;;
  esac
}

# 전달 신호 — 강한 쪽부터 본다. (BL-552 ②-a)
#   strong  status 파일이 `pending` 에서 바뀌었다. 워커가 프롬프트를 **읽고** 첫 지시("echo running")를
#           실행했다는 뜻이다. 이 프롬프트에 대한 인과가 있는 유일한 신호다.
#   weak    agent_status 가 `working`. 프롬프트가 제출됐다는 정황이지 이 프롬프트의 증거는 아니다 —
#           그 사이 다른 입력이 워커를 working 으로 만들었을 수도 있다(codex G1 P1 이 지적한 잔여
#           한계다. 분배가 유일한 주입자라는 전제에 기댄다. 더 강하게 하려면 프롬프트에 nonce 를
#           넣고 워커가 그것을 되쓰게 해야 하는데, 프롬프트·워커 계약은 §6 이라 여기서 바꾸지 않는다).
#   none    아직 아무 변화도 없다.
qb_delivery_signal() {  # qb_delivery_signal <pane> <status 파일>
  local sig=""
  if [ -f "$2" ]; then sig="$(tr -d '\n' < "$2" 2>/dev/null || true)"; fi
  if [ -n "$sig" ] && [ "$sig" != "pending" ]; then echo strong; return 0; fi
  if [ "$(agent_status_of "$1")" = "working" ]; then echo weak; return 0; fi
  echo none
}

# ★Enter 를 밀어도 되는 상태인가 (R1-①).
#   `blocked` 면 밀지 않는다 — 그 pane 에 떠 있는 것은 프롬프트 입력창이 아니라 **승인
#   다이얼로그**이고, Enter 는 그 기본 선택을 대신 누르는 행위다. 그건 사람의 결정이다.
#   주입 **전** blocked 는 qb_injectable 이 이미 거른다. 이 함수가 막는 것은 **주입 후 폴링
#   중에 열린** 창이다(좁지만 실재한다).
#
# ★fail-closed 허용목록이다 — `blocked` 만 빼는 방식(`case blocked) …; *) 민다`)은 fail-open
#   이었다 (codex G1 P1). `agent_status_of` 가 herdr 조회 실패·pane 미발견으로 `unknown` 이나
#   빈 값을 내면, **승인 다이얼로그가 떠 있는데 조회만 실패한** 경우까지 Enter 를 밀어버린다.
#   그래서 "안전하다고 **적극적으로 관측된** 상태"(idle·done)에서만 민다.
#   안 밀어서 잃는 것은 자동 복구 한 번(사람이 그 pane 에 가면 된다)이고,
#   잘못 밀어서 잃는 것은 사람의 승인 결정이다. 비대칭이므로 닫는 쪽으로 기운다.
#
# ★잔여 TOCTOU — 이 관측과 실제 send-keys 사이의 창은 없앨 수 없다(herdr 에 "blocked 가
#   아니면 보내라" 는 원자적 primitive 가 없다). 호출부는 관측 직후 **즉시** 보내 창을 최소화한다.
#   그래도 남는 위험은 이 방식의 한계로 받아들인다 — 대안은 Enter 를 아예 안 미는 것이고,
#   그러면 BL-552 의 미제출이 매번 사람 손을 요구한다.
# ★인자는 **이미 읽은 상태 문자열**이다(pane 이 아니다). 호출부가 한 번만 읽어서 넘긴다 —
#   여기서 또 읽으면 판정에 쓴 값과 진단에 찍는 값이 서로 다른 관측이 된다.
# ★qb_injectable 과 본문이 같지만 **합치지 마라.** 지키는 것이 다르다: 저건 "주입해도 되나",
#   이건 "Enter 를 눌러도 되나" 다. 합치면 한쪽 정책만 바꾸고 싶을 때 다른 쪽이 함께 바뀐다.
qb_should_send_enter() {  # qb_should_send_enter <agent_status> → 0 이면 밀어도 된다
  case "$1" in
    idle|done) return 0 ;;
    *) return 1 ;;
  esac
}

# 고정 상한 폴링. herdr-fleet.sh 의 "기동 뒤 herdr 이 아직 그 pane 을 에이전트로 보는가" 재확인과
# 같은 모양이다 (②-e — 새 방식을 발명하지 않는다).
qb_poll_delivery() {  # qb_poll_delivery <pane> <status 파일> <시도 횟수> → strong|weak|none
  local sig="none" i
  for i in $(seq 1 "$3"); do
    sig="$(qb_delivery_signal "$1" "$2")"
    [ "$sig" = "none" ] || break
    sleep 1
  done
  echo "$sig"
}

# ── --status ────────────────────────────────────────────────────────────────
# herdr agent_status 는 **프로세스**가 살아 있는지, signal 은 **일**이 어디까지 갔는지를 말한다.
# 둘은 다르다. 나란히 보여준다.
if [ "$STATUS" -eq 1 ]; then
  # 커밋 수는 origin/main 대비다. 워커 base 가 origin/main 이 아니면(예: 스택 브랜치) 그 차이도
  # 함께 세므로, 이 숫자를 "워커가 만든 커밋 수" 로 읽지 마라. 판정은 diff 로 한다.
  printf '%-12s %-9s %-9s %-18s %-16s %-7s %s\n' WORKER PANE HERDR SIGNAL DELIVERY REPORT "BRANCH(vs origin/main)"
  for w in "${WORKERS[@]}"; do
    wt="$MAIN_ROOT/.claude/worktrees/$w"
    _pw="$(pane_of "$wt" || true)"; pane="${_pw%% *}"
    hs="-"; [ -n "$pane" ] && hs="$(agent_status_of "$pane")"
    out="$(wt_out "$w")"
    sig="-"; [ -f "$out/status" ] && sig="$(tr -d '\n' < "$out/status")"
    # ★R1-③ — 통합 안 한 `done` 이 재분배로 덮였으면 **여기서 보여준다.** 보존만 하고 표에
    #   안 띄우면 아무도 안 보고, 그건 마커를 잃은 것과 같다 (codex G1 P1).
    #   현재 status 가 이미 `done` 이면 새 세대가 그 자리를 대신하므로 표시하지 않는다.
    if [ -f "$out/status.prev" ] && [ "$sig" != "done" ]; then
      sig="$sig(prev:done)"
    fi
    dlv="-"; [ -f "$out/delivery" ] && dlv="$(tr -d '\n' < "$out/delivery")"
    rep="-"; [ -s "$out/report.md" ] && rep="있음"
    br="-"
    if git rev-parse --verify --quiet "wt/$w" >/dev/null; then
      br="wt/$w($(git rev-list --count "origin/main..wt/$w" 2>/dev/null || echo '?'))"
    fi
    printf '%-12s %-9s %-9s %-18s %-16s %-7s %s\n' "$w" "${pane:--}" "$hs" "$sig" "$dlv" "$rep" "$br"
  done
  echo
  echo "  herdr blocked = 대개 권한 프롬프트다. 워커가 스스로 못 푼다 — 그 pane 에 사람이 가야 한다."
  echo "  signal done + report 있음 → 통합 대상 (docs/reference/operations/workflows/fleet-orchestration.md §5)"
  echo "  ★(prev:done) = 통합 안 한 done 마커가 재분배로 덮였다 (status.prev 보존). 그 회차 산출을"
  echo "    통합했는지 확인하고, 마쳤으면 <워크트리>/.claude/fleet/$RUN/status.prev 를 지워라."
  echo "  DELIVERY = 분배가 본 **전달** 결과 (BL-552). undelivered = 프롬프트가 제출되지 않았다."
  echo "    unverified = --force 로 넣어 확인을 생략했다 → 그 pane 은 사람이 직접 봐라."
  echo "    no_enter_* = Enter 를 안전하게 밀 수 없었다(blocked/unknown) → 그 pane 을 사람이 봐라."
  exit 0
fi

# ── 분배 ────────────────────────────────────────────────────────────────────
# ★워커 하나의 실패로 루프 안에서 죽지 않는다 (R1-②). 워커 2/5 에서 죽으면 3~5 는 주입조차
#   안 되고 1~2 는 이미 돌고 있어 함대가 반쪽이 된다. 끝까지 분배하고 마지막에 한 번에 판정한다.
#   여기 모이는 것: 주입 가능 상태 아님 · TOCTOU 전이 · 주입 명령 실패 · Enter 불가 · 미제출.
#   (워크트리 부재·슬롯 부재·pane 부재·workspace 불일치·계약 문서 부재·출력 경로 이탈은 그대로
#    즉시 die 한다 — 그건 워커별 실패가 아니라 **함대 전제 위반**이라 나머지도 같이 틀렸다.)
FAILED=(); RESULTS=()
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

  # ★계약 문서는 **워커 워크트리** 것을 가리킨다. 메인 경로를 가리키면 안 된다 —
  #   `docs/reference/operations/workflows/fleet-orchestration.md` 는 트래킹 파일이고, 메인 체크아웃은 전혀 다른
  #   (더 오래된) 브랜치에 있을 수 있다. 실제로 첫 실전에서 그 경로가 존재하지 않아
  #   두 워커가 모두 "없는 파일을 읽으라는 지시" 를 받았다(워커가 스스로 적발해 보고했다).
  #   존재를 여기서 확인해 그 침묵 실패를 막는다.
  CONTRACT="$wt/docs/reference/operations/workflows/fleet-orchestration.md"
  [ -f "$CONTRACT" ] || die "$w 의 브랜치에 계약 문서가 없다: $CONTRACT
    base 가 이 문서를 포함한 커밋이어야 한다. 워커에게 없는 파일을 읽으라고 시키면
    워커는 제 나름대로 해석하고, 그건 계약이 아니다."

  # ★★주입 가능 상태 검사는 **어떤 쓰기보다도 먼저** 한다 (R2-①).
  #   working 중에 주입하면 입력이 섞인다. 주입 가능 상태(idle · done)가 아니면 이 워커를 건너뛴다.
  #
  #   ★이 검사가 `cp task.md` **뒤**에 있으면 데이터 유실이다 — 요약에는 "건너뛰었다" 로 찍히는데
  #   실제로는 **진행 중인 워커가 읽던 지시가 새 내용으로 바뀐다.** R1 에서 검사를 경로 검증 뒤로
  #   내리다가 `cp` 까지 넘어가 그 결함을 내가 만들었고, G6 codex 가 잡았다.
  #   → 건너뛸 워커에는 **아무것도 쓰지 않는다**: task.md 도, status 도, delivery 도, mkdir 도.
  #     `delivery` 조차 쓰지 않는 이유 — 그 워커는 **지금 돌고 있는 회차**의 `delivery=ok` 를
  #     들고 있다. 그걸 `not_injectable_working` 으로 덮으면 정상 진행 중인 회차의 기록이 사라져
  #     `--status` 가 거짓을 말한다. 이번 회차에 안 넣었다는 사실은 **아래 요약표와 종료 코드**로
  #     보고한다(R1-② 규율과 같다 — 조용히 성공으로 넘기지 않는다).
  #
  #   ★여기서 die 하지 않는다 (codex G1 P1). 워커 B 가 이 검사에서 걸리면 C 는 주입조차 못 받는데,
  #   같은 상태가 몇 밀리초 뒤 TOCTOU 재검사에서 걸렸다면 아래는 수집하고 계속 갔다 — **시간
  #   차이만으로 동작이 갈리는** 경계였다. 두 검사를 같은 처분으로 맞춘다.
  hs="$(agent_status_of "$pane")"
  if ! qb_injectable "$hs" && [ "$FORCE" -ne 1 ]; then
    echo "  ✗ $w ($pane) 상태가 '$hs' 다 — idle 또는 done 일 때만 주입한다. 이 워커는 건너뛴다."
    echo "    working=아직 일하는 중 / blocked=권한 프롬프트(사람이 눌러야 한다) / unknown=대개 죽었다"
    echo "    (done 은 주입 가능하다 — '턴이 끝났다' 는 뜻이고 태스크 완료가 아니다. §2)"
    echo "    ★이 워커의 파일은 아무것도 건드리지 않았다 (task.md·status·delivery 전부 그대로)."
    echo "    그래도 넣으려면 --force (입력이 섞일 수 있다)."
    FAILED+=("$w|$pane|not_injectable($hs)")
    RESULTS+=("$w|$pane|$slot|not_injectable_$hs")
    continue
  fi

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

  # ★파일 소유 규칙 — 누가 언제 무엇을 쓰는가 (BL-552 ②-f)
  #   status    `pending` 은 **분배가 주입 전에** 쓴다. 주입 뒤에 쓰면 지시대로 즉시 `running` 을
  #             쓴 워커의 값을 덮어써서 폴링이 오랫동안 거짓 `pending` 을 보여준다 (codex 리뷰 P2).
  #             그 뒤로는 **워커만** 쓴다: running | done | blocked.
  #   delivery  **분배만** 쓴다. pending → ok | undelivered | unverified.
  #             ★전달 실패를 `status` 에 쓰지 않는 이유 — 셸의 "읽어서 pending 인지 보고 나서 쓰기" 는
  #             원자적이지 않아서, 그 사이에 워커가 쓴 `running` 을 덮을 수 있다 (codex G1 P1).
  #             파일을 갈라두면 그 레이스가 **구조적으로** 없다. 그리고 `pending` 만 보면 미제출과
  #             정상 대기가 구분되지 않는다는 BL-552 의 관측 혼동도 이 열이 해소한다.
  #   status.prev  **분배만** 쓴다. 아래 R1-③ 을 봐라.
  #
  # ★R1-③ — `done` 마커를 덮기 전에 보존한다.
  #   `qb_injectable` 이 `done` 을 주입 가능으로 보는 것은 옳다(§2: done = 턴이 끝났다). 그런데
  #   분배는 `status` 를 `pending` 으로 되돌리고 `task.md` 를 덮으므로, **아직 통합하지 않은**
  #   워커에 재분배하면 `--status` 가 통합 대상 판정에 쓰는 그 `done` 마커가 사라진다
  #   (`report.md` 만 남아 짝이 안 맞는다). 그래서 값을 `status.prev` 로 옮기고 경고를 찍는다.
  #   ★워커의 `status` 소유 규칙은 깨지 않는다 — 나는 **읽어서 다른 파일에 복사**할 뿐이고,
  #   `status` 에 쓰는 값은 여전히 주입 전 `pending` 하나다.
  _prev_status=""
  [ -f "$OUT/status" ] && _prev_status="$(tr -d '\n' < "$OUT/status")"
  # ★`status.prev` 를 **지우지 않는다** (codex G1 P1). 지우면 자연스러운 재시도가 증거를 없앤다:
  #   A 회차 done(미통합) → 재분배가 done 을 prev 로 옮김 → 주입 실패 → 안내대로 `--only` 재시도
  #   → 이때 status 는 이미 `pending` 이라 "prev 를 새로 쓸 조건" 이 아니고, 지우기만 하면
  #   A 의 완료 증거가 영구히 사라진다. 새 `done` 을 만났을 때만 덮어써서 세대를 올린다.
  #   ★이 파일은 **사람이 통합 후 지운다** — `--status` 가 그때까지 계속 보여준다.
  if [ "$_prev_status" = "done" ]; then
    printf 'done\n' > "$OUT/status.prev"
    echo "  ⚠ $w 의 기존 status 가 'done' 이었다 — 재분배가 그 마커를 덮는다."
    echo "    통합(§5)을 아직 안 했다면 지금 이 워커는 '통합 대상' 표시를 잃는다."
    echo "    보존: $OUT/status.prev  (report.md 는 그대로 남아 있다)"
    echo "    통합을 마쳤으면 그 파일을 지워라 — 안 지우면 --status 가 계속 (prev:done) 을 보여준다."
  fi
  printf 'pending\n' > "$OUT/status"
  printf 'pending\n' > "$OUT/delivery"

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
  # ★여기서도 죽지 않는다 (R1-②) — 이 워커 하나 때문에 나머지 워커가 분배를 못 받으면 안 된다.
  if [ "$FORCE" -ne 1 ]; then
    hs2="$(agent_status_of "$pane")"
    if ! qb_injectable "$hs2"; then
      printf 'not_injected\n' > "$OUT/delivery"
      echo "  ✗ $w ($pane) 가 확인 직후 '$hs2' 로 바뀌었다 — 주입을 취소했다."
      echo "    다시 시도하거나, 정말 넣어야 하면 --force."
      FAILED+=("$w|$pane|not_injected($hs2)")
      RESULTS+=("$w|$pane|$slot|not_injected")
      continue
    fi
    hs="$hs2"   # 전달 확인의 기준은 **주입 직전** 상태다
  fi
  if ! herdr agent prompt "$pane" "$PROMPT" >/dev/null; then
    printf 'inject_failed\n' > "$OUT/delivery"
    echo "  ✗ $w ($pane) 주입 명령 자체가 실패했다 (herdr agent prompt)."
    FAILED+=("$w|$pane|inject_failed")
    RESULTS+=("$w|$pane|$slot|inject_failed")
    continue
  fi

  # ── 전달 확인 (BL-552) ──────────────────────────────────────────────────────
  # 왜 — 실측에서 `herdr agent prompt` 가 0 을 반환했는데 pane 입력창에
  # `❯ [Pasted text #2 +14 lines]` 가 그대로 남고 에이전트는 `idle` 이었다. 스크립트는
  # `✓ bl544 → wM:p1` 로 **성공을 보고**했고, 상태표는 `HERDR=idle / SIGNAL=pending` 이라
  # 정상 대기와 구분되지 않았다. 첫 분배는 정상이었으니 레이스다. ★조용히 성공을 보고하지 않는다.
  #
  # ★성공 판정은 **주입 전 상태**로 갈린다:
  #   주입 전 idle · done                      → 확인 **의무**. working 관측(weak) 또는
  #                                              status 가 pending 에서 바뀜(strong).
  #   주입 전 working · blocked · unknown      → 확인 **생략** (--force 전용 경로).
  #     working 은 이미 working 이라 전환을 볼 수 없고, blocked 는 사람이 눌러야 working 이 된다.
  #     여기서 확인을 강제하면 **거짓 실패**가 난다 — 그래서 생략하고, 대신 생략했다고 경고를 찍는다.
  if qb_injectable "$hs"; then
    _sig="$(qb_poll_delivery "$pane" "$OUT/status" 6)"
    if [ "$_sig" = "none" ]; then
      # ★R1-① — Enter 를 밀기 **직전에** 상태를 다시 읽는다.
      #   주입 **전** blocked 는 위 qb_injectable 이 이미 걸렀다. 문제는 **주입 후 폴링 6초 사이**다.
      #   그 창에서 워커가 권한 프롬프트에 걸리면(blocked) 이 Enter 는 프롬프트를 재촉하는 게 아니라
      #   **승인 다이얼로그의 기본 선택을 대신 눌러준다.** 창은 좁지만 실재하고, 누르는 대상이
      #   승인 다이얼로그다 — 그건 사람의 결정이다. 밀지 않는다.
      _hs_now="$(agent_status_of "$pane")"      # 한 번만 읽어 판정과 진단에 같은 값을 쓴다
      if qb_should_send_enter "$_hs_now"; then
        # ★관측과 send-keys 사이에 아무것도 끼우지 않는다 — 잔여 TOCTOU 창을 최소화한다.
        herdr pane send-keys "$pane" Enter >/dev/null 2>&1 || true
        echo "  … $w ($pane) 가 안 움직여 Enter 를 한 번 밀었다 (BL-552)"
        _sig="$(qb_poll_delivery "$pane" "$OUT/status" 4)"
      else
        printf 'no_enter_%s\n' "$_hs_now" > "$OUT/delivery"
        echo "  ⚠ $w ($pane) 상태가 '$_hs_now' 다 — Enter 를 **밀지 않았다** (R1-①)."
        echo "    blocked 면 Enter 가 승인 다이얼로그의 기본 선택을 대신 누른다. 그건 사람 몫이다."
        echo "    unknown 이면 상태를 못 읽은 것이다 — 승인 창이 떠 있는지 알 수 없으니 밀지 않는다."
        echo "    사람이 할 일: 그 pane 을 직접 봐라 (승인 프롬프트면 처리, 죽었으면 재기동)."
        FAILED+=("$w|$pane|no_enter($_hs_now)")
        RESULTS+=("$w|$pane|$slot|no_enter_$_hs_now")
        continue
      fi
    fi
    if [ "$_sig" = "none" ]; then
      printf 'undelivered\n' > "$OUT/delivery"
      echo "  ✗ $w ($pane) 에 프롬프트가 제출되지 않았다 — Enter 를 밀어도 상태가 안 바뀐다 (BL-552)."
      echo "    pane 입력창에 '[Pasted text …]' 가 붙어 있을 가능성이 크다."
      echo "    기록: $OUT/delivery = undelivered  (status 는 워커 소유라 건드리지 않았다)"
      FAILED+=("$w|$pane|undelivered")
      RESULTS+=("$w|$pane|$slot|undelivered")
      continue
    fi
    printf 'ok\n' > "$OUT/delivery"
    ok "$w → $pane (슬롯 $slot, 전달=$_sig)"
    RESULTS+=("$w|$pane|$slot|$_sig")
  else
    printf 'unverified\n' > "$OUT/delivery"
    echo "  ⚠ $w → $pane (슬롯 $slot) — 주입 전 상태가 '$hs' 라 전달 확인을 **생략했다** (--force)."
    echo "    working 은 전환을 볼 수 없고 blocked 는 사람이 눌러야 풀린다 — 확인하면 거짓 실패가 난다."
    echo "    이 워커만은 pane 을 직접 봐라: herdr pane read $pane --source recent --lines 30"
    RESULTS+=("$w|$pane|$slot|unverified")
  fi
done

# ── 분배 요약 (R1-②) ────────────────────────────────────────────────────────
# ★실패해도 루프 안에서 죽지 않았다. 워커 2/5 에서 죽으면 3~5 는 주입조차 안 되고
#   1~2 는 이미 돌고 있어 **함대가 반쪽**이 된다. 끝까지 분배하고 여기서 한 번에 판정한다.
echo
echo "── 분배 결과"
printf '  %-12s %-9s %-5s %s\n' WORKER PANE SLOT DELIVERY
for _r in ${RESULTS[@]+"${RESULTS[@]}"}; do
  IFS='|' read -r _rw _rp _rs _rd <<< "$_r"
  printf '  %-12s %-9s %-5s %s\n' "$_rw" "$_rp" "$_rs" "$_rd"
done
echo "  strong=워커가 status 를 갱신했다 / weak=agent_status 가 working 으로 바뀌었다"
echo "  unverified=--force 로 확인 생략 / undelivered·blocked_no_enter=사람이 그 pane 에 가야 한다"

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo
  echo "✗ 전달 실패 ${#FAILED[@]} 건 — 나머지 워커 분배는 끝까지 했다."
  for _f in "${FAILED[@]}"; do
    IFS='|' read -r _fw _fp _fr <<< "$_f"
    echo "    $_fw ($_fp) — $_fr"
    echo "      herdr pane read $_fp --source recent --lines 30"
    [ "$_fr" = "undelivered" ] && echo "      herdr pane send-keys $_fp Enter"
  done
  _retry=""
  for _f in "${FAILED[@]}"; do
    _retry="${_retry:+$_retry,}${_f%%|*}"
  done
  echo "  ★조용히 성공을 보고하지 않는다 (BL-552). 위 워커만 --only 로 다시 분배해라:"
  echo "    scripts/fleet-dispatch.sh --run $RUN --only $_retry"
  exit 1
fi

echo
echo "폴링:  scripts/fleet-dispatch.sh --run $RUN --status"
