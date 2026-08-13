#!/usr/bin/env bash
# fleet-dispatch.sh 의 판정 술어 하네스 — BL-552 · R1-①. 전건 통과 = 종료 코드 0.
#
# 왜 이런 모양인가
#   `fleet-dispatch.sh` 는 실제 herdr 함대(= CONTROL 자리)가 없으면 통째로 돌 수 없다. 그러나
#   **판정 술어**는 herdr 없이도 시험할 수 있다 — `agent_status_of` 하나만 stub 하면 된다.
#   그래서 함수를 **실제 파일에서 sed 로 떼어내** 실행한다. 복사해 두지 않는 이유는 명백하다:
#   복사본은 원본과 갈린다. 원본에서 함수 이름이 바뀌면 이 하네스는 추출 실패로 **크게 죽는다**.
#
# ★이 하네스가 잡는 것 / 못 잡는 것
#   잡는다   qb_injectable(주입 허용 상태) · qb_delivery_signal(강/약/없음) ·
#            qb_poll_delivery(상한 폴링) · qb_should_send_enter(R1-① blocked 가드)
#   못 잡는다 워커 루프의 제어 흐름(R1-② 실패 수집·요약·종료 코드) · herdr 실호출.
#            그건 CONTROL 이 실경로에서 잰다.
#
# 사용법: tools/scripts/fleet-dispatch-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
SRC="$ROOT/tools/scripts/fleet-dispatch.sh"
[ -f "$SRC" ] || { echo "✗ 원본이 없다: $SRC" >&2; exit 1; }

# 실제 파일에서 술어만 떼어낸다. 하나라도 못 찾으면 그 자리에서 죽는다 —
# 조용히 0 건을 시험하고 green 을 찍는 것이 이 레포가 반복해서 밟은 함정이다.
FNS="$(mktemp)"
trap 'rm -f "$FNS"' EXIT
for _f in qb_injectable qb_should_send_enter qb_delivery_signal qb_poll_delivery; do
  if ! sed -n "/^$_f() {/,/^}/p" "$SRC" | grep -q .; then
    echo "✗ $SRC 에서 $_f 를 못 떼어냈다 — 이름이 바뀌었나? 하네스를 갱신해라." >&2
    exit 1
  fi
  sed -n "/^$_f() {/,/^}/p" "$SRC" >> "$FNS"
done

# stub — herdr 를 부르지 않는다. FAKE_STATUS 로 pane 상태를 주입한다.
FAKE_STATUS="idle"
agent_status_of() { echo "$FAKE_STATUS"; }
sleep() { :; }                        # 폴링 대기 제거 (로직만 본다)
# shellcheck source=/dev/null
. "$FNS"

PASS=0; FAIL=0
t() {  # t <label> <실측> <기대>
  if [ "$2" = "$3" ]; then
    PASS=$((PASS + 1)); printf '  ✓ %-52s %s\n' "$1" "$3"
  else
    FAIL=$((FAIL + 1)); printf '  ✗ %-52s 기대=%s 실측=%s\n' "$1" "$3" "$2"
  fi
}
yn() { if "$@"; then echo yes; else echo no; fi; }

echo "══ fleet-dispatch 판정 술어 하네스 (herdr stub) ══"
echo

# ── 주입 허용 상태 (②-g) ─────────────────────────────────────────────────────
for s in idle done; do
  t "qb_injectable $s" "$(yn qb_injectable "$s")" yes
done
for s in working blocked unknown ""; do
  t "qb_injectable '$s'" "$(yn qb_injectable "$s")" no
done

# ── R1-① Enter 가드 ──────────────────────────────────────────────────────────
# ★blocked pane 에 Enter 를 밀면 승인 다이얼로그의 기본 선택을 대신 누른다. 밀지 않아야 한다.
# 인자는 pane 이 아니라 **이미 읽은 상태 문자열**이다 (호출부가 한 번만 읽는다).
t "qb_should_send_enter blocked → 밀지 않는다 (R1-①)" "$(yn qb_should_send_enter blocked)" no
# ★fail-closed 허용목록 — 상태를 못 읽었으면(unknown/빈 값) 승인 창이 떠 있는지 알 수 없다.
#   "blocked 만 빼기" 는 fail-open 이었다 (codex G1 P1).
for s in unknown "" working weird; do
  t "qb_should_send_enter '$s' → 밀지 않는다 (fail-closed)" "$(yn qb_should_send_enter "$s")" no
done
for s in idle done; do
  t "qb_should_send_enter $s → 민다" "$(yn qb_should_send_enter "$s")" yes
done

# ── 전달 신호 ────────────────────────────────────────────────────────────────
SF="$(mktemp)"
printf 'pending\n' > "$SF"; FAKE_STATUS=idle
t "pending + idle" "$(qb_delivery_signal p1 "$SF")" none
FAKE_STATUS=working
t "pending + working" "$(qb_delivery_signal p1 "$SF")" weak
printf 'running\n' > "$SF"; FAKE_STATUS=idle
t "running + idle (강한 신호 우선)" "$(qb_delivery_signal p1 "$SF")" strong
printf 'blocked\n' > "$SF"
t "status=blocked + idle" "$(qb_delivery_signal p1 "$SF")" strong
printf '' > "$SF"; FAKE_STATUS=idle
t "빈 파일 + idle (미기록을 전달로 보지 않는다)" "$(qb_delivery_signal p1 "$SF")" none
t "파일 없음 + idle" "$(qb_delivery_signal p1 /nonexistent/qb-x)" none

# ── 상한 폴링 ────────────────────────────────────────────────────────────────
printf 'pending\n' > "$SF"; FAKE_STATUS=idle
t "qb_poll_delivery 6회 전부 none" "$(qb_poll_delivery p1 "$SF" 6)" none
FAKE_STATUS=working
t "qb_poll_delivery working" "$(qb_poll_delivery p1 "$SF" 6)" weak
rm -f "$SF"

# ── R2-② 조회 실패 수렴 ───────────────────────────────────────────────────────
# ★여기서는 stub 이 아니라 **원본의 agent_status_of** 를 쓴다. `herdr` 를 실패하는 셸 함수로
#   갈아끼워, 조회 실패가 `unknown` 으로 수렴하고 `set -euo pipefail` 아래에서도 스크립트가
#   계속 도는지 본다(예전에는 여기서 분배 전체가 죽었다).
REAL_ASO="$(mktemp)"
trap 'rm -f "$FNS" "$REAL_ASO"' EXIT
sed -n '/^agent_status_of() {/,/^}/p' "$SRC" > "$REAL_ASO"
[ -s "$REAL_ASO" ] || { echo "✗ agent_status_of 를 못 떼어냈다" >&2; exit 1; }

# herdr 를 주어진 본문으로 갈아끼우고, **원본 스크립트와 같은 옵션**(set -euo pipefail)에서
# 원본 agent_status_of 를 돌린다. 죽으면 "survived" 가 안 찍히므로 그것으로 판정한다.
# ★JSON 은 **픽스처 파일**로 준다. 본문에 JSON 을 인라인하면 중첩 인용이 조용히 깨진다 —
#   초안에서 `echo "{\"result\"…}"` 로 넣었다가 정상 JSON 케이스가 unknown 을 내고도 통과처럼
#   보였다(실측). 인용을 없애는 것이 유일한 확실한 수정이다.
r2_probe() {  # r2_probe <herdr 본문> [픽스처 파일] → "<상태> survived"  (죽으면 빈 문자열)
  QB_HERDR_BODY="$1" QB_FIXTURE="${2:-}" QB_ASO="$REAL_ASO" /usr/bin/env bash -c '
    set -euo pipefail
    eval "herdr() { $QB_HERDR_BODY; }"
    . "$QB_ASO"
    st="$(agent_status_of p1)"
    printf "%s survived\n" "$st"
  ' 2>/dev/null
}

FX_OK="$(mktemp)"
printf '%s\n' '{"result":{"panes":[{"pane_id":"p1","agent_status":"working"}]}}' > "$FX_OK"
FX_OTHER="$(mktemp)"
printf '%s\n' '{"result":{"panes":[{"pane_id":"other","agent_status":"idle"}]}}' > "$FX_OTHER"

t "R2-② herdr 실패(종료 1) → unknown + 계속 돈다" \
  "$(r2_probe 'return 1')" "unknown survived"
t "R2-② herdr 가 JSON 아닌 쓰레기 → unknown + 계속 돈다" \
  "$(r2_probe 'echo not-json')" "unknown survived"
t "R2-② herdr 가 빈 출력 → unknown + 계속 돈다" \
  "$(r2_probe 'true')" "unknown survived"
t "R2-② 정상 JSON 이면 그 값을 낸다 (계측기 판별력)" \
  "$(r2_probe 'cat "$QB_FIXTURE"' "$FX_OK")" "working survived"
t "R2-② 정상 JSON 인데 그 pane 이 없으면 unknown" \
  "$(r2_probe 'cat "$QB_FIXTURE"' "$FX_OTHER")" "unknown survived"
rm -f "$FX_OK" "$FX_OTHER"

# ── R2-① 구조 검사 (주입 안 할 워커의 산출물을 건드리지 않는다) ────────────────
# ★루프 본체는 herdr 함대와 메인 체크아웃이 없으면 못 돌린다(워크트리에서 스크립트가 스스로
#   거부한다). 그래서 **소스 순서**를 단언한다 — G6 codex 가 이 결함을 찾은 방법과 같다.
#   R1 에서 상태 검사를 아래로 옮기다 `cp task.md` 를 넘어가 데이터 유실을 만들었으므로,
#   "검사가 모든 쓰기보다 앞" 을 구조로 못박는다.
ln_of() { grep -nF "$1" "$SRC" | head -1 | cut -d: -f1; }
_l_check="$(ln_of 'if ! qb_injectable "$hs" && [ "$FORCE" -ne 1 ]; then')"
_l_cp="$(ln_of 'cp "$RUN_DIR/tasks/$w.md" "$OUT/task.md"')"
_l_status="$(ln_of "printf 'pending\\n' > \"\$OUT/status\"")"
_l_mkdir="$(ln_of 'mkdir -p "$OUT"')"
for _pair in "cp_task:$_l_cp" "status_pending:$_l_status" "mkdir:$_l_mkdir"; do
  _nm="${_pair%%:*}"; _ln="${_pair##*:}"
  if [ -z "$_l_check" ] || [ -z "$_ln" ]; then
    FAIL=$((FAIL + 1)); printf '  ✗ %-52s 앵커를 못 찾았다 (check=%s %s=%s)\n' \
      "R2-① 상태검사 < $_nm" "${_l_check:-없음}" "$_nm" "${_ln:-없음}"
  elif [ "$_l_check" -lt "$_ln" ]; then
    PASS=$((PASS + 1)); printf '  ✓ %-52s %s\n' "R2-① 상태검사($_l_check) < $_nm($_ln)" "순서 OK"
  else
    FAIL=$((FAIL + 1)); printf '  ✗ %-52s ★쓰기가 검사보다 앞이다 = 데이터 유실\n' \
      "R2-① 상태검사($_l_check) < $_nm($_ln)"
  fi
done

# 건너뛰기 분기 안에서 워커 파일에 쓰지 않는지 — "아무것도 건드리지 마라" 를 직접 단언한다.
_skip_block="$(sed -n "${_l_check:-1},/^  fi$/p" "$SRC")"
if printf '%s' "$_skip_block" | grep -q '> *"\$OUT/'; then
  FAIL=$((FAIL + 1)); printf '  ✗ %-52s ★건너뛰기 분기가 워커 파일에 쓴다\n' "R2-① 건너뛴 워커에 쓰기 없음"
else
  PASS=$((PASS + 1)); printf '  ✓ %-52s %s\n' "R2-① 건너뛴 워커에 쓰기 없음" 'OUT 쓰기 0건'
fi

echo
echo "══════════════════════════════════════════"
printf '  통과 %d · 실패 %d\n' "$PASS" "$FAIL"
echo "══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과  (★루프 제어 흐름과 herdr 실호출은 CONTROL 검증 몫)"
