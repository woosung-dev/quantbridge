#!/usr/bin/env bash
#
# 소크 원터치 재기동 — `docs/status.md` 재기동 절차 ⑴~⑻ 을 한 커맨드로.
#
# 왜 있나
#   8 단계를 사람이 밟으면 빠뜨린다. 2026-08-07 09:35 재기동에서 ⑺ 이 누락돼 `.soak/session` 이
#   **맨 uuid** 로 쓰였고, `soak-observe.sh` 는 그 파일을 `.` 로 소싱하므로 `command not found`
#   (rc=127)로 죽어 **일일 원장 대조가 통째로 막혔다.** status.md:54 가 정확히 그 함정을
#   경고하고 있었는데도 그렇게 됐다 — 절차서는 지켜지지 않는다. 스크립트로 만든다.
#
# 사용:
#   scripts/soak-restart.sh              # 기본 = dry-run. 8 단계와 **실제 값**을 출력만 한다
#   scripts/soak-restart.sh --confirm    # 집행
#   scripts/soak-restart.sh --strategy-id <uuid> --account-id <uuid> --confirm
#
# 종료 코드: 0 = 정상 / 1 = 실패·거부 / 2 = 전제 미충족(측정 못 함)
#
# ★설계 근거 (전부 실측):
#   · **⑴ 이 통과하지 못하면 아무것도 하지 않는다.** 세션 `DELETE` 204 는 **아무것도 flat 하지
#     않는다**(0.03 포지션 + resting 조건부 1 건 잔존 전례, 3 회 덴 함정). 자동 flatten 은 **하지
#     않는다** — 실자금이 걸린 청산은 사용자 결정이다.
#   · **`up` 은 세션을 만들지 않는다.** 세션이 0 이면 시계도 0 이다. ⑸ 를 빠뜨리면 스택은 도는데
#     C1 이 안 오른다.
#   · **돌고 있는 고정본 위에는 pin 이 거부된다**(`soak-stack.sh:94-99`, exit 2). 순서는 down → pin → up.
#   · **`up` 은 celery 기동 배너를 최대 600 초 기다린다**(`soak-stack.sh:168-191`). 타임아웃을 걸지 않는다.
#   · **uuid 는 정규식으로 뽑는다.** `✓ 세션 등재: <uuid>` 는 멀티바이트 3 토큰이라
#     `awk '{print $3}'` 이 `등재:` 를 준다.
#   · **`.soak/session` 을 손으로 쓰지 않는다.** ⑺ 의 `soak-observe.sh --baseline` 만이 올바른
#     `SESSION_ID=<uuid>` 형식을 쓴다. `--session` 은 **플래그**다(위치인자면 `unknown arg` exit 64).
#   · **env 는 절대경로로 소싱한다.** `cd backend && set -a; . ./.env.local` 은 이미 backend 에
#     있으면 `cd` 가 실패해 `set -a` 만 건너뛰고 나머지가 이어진다(레포 금지 관용구).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"

CONFIRM=0
STRATEGY_ID=""
ACCOUNT_ID=""
SYMBOL="${QB_SOAK_SYMBOL:-BTC/USDT}"
INTERVAL="${QB_SOAK_INTERVAL:-1m}"

need_val() { [ "$1" -ge 2 ] || {
  echo "✗ $2 에 값이 없다" >&2
  exit 2
}; }

while [ $# -gt 0 ]; do
  case "$1" in
    --confirm)
      CONFIRM=1
      shift
      ;;
    --dry-run)
      CONFIRM=0
      shift
      ;;
    --strategy-id)
      need_val $# --strategy-id
      STRATEGY_ID="$2"
      shift 2
      ;;
    --account-id)
      need_val $# --account-id
      ACCOUNT_ID="$2"
      shift 2
      ;;
    -h | --help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    *)
      echo "알 수 없는 인자: $1  (--help)" >&2
      exit 2
      ;;
  esac
done

die() {
  echo "✗ $1" >&2
  exit "${2:-1}"
}

# ★워크트리에서는 ⑷ 가 반드시 실패한다 — `soak-stack.sh` 의 pin/up/down 이 각각
#   assert-main-checkout 을 부르고 exit 2 를 낸다. 여기서 먼저 막지 않으면 ⑴~⑶ 만 실행하고
#   중간에 죽는다. dry-run 은 워크트리에서도 읽을 수 있게 허용한다.
if [ "${CONFIRM}" = "1" ]; then
  bash "${SCRIPT_DIR}/assert-main-checkout.sh" "soak-restart.sh --confirm" || exit 2
fi

_admin() { # _admin <live_session_admin.py 인자...>
  (
    set -a
    # shellcheck disable=SC1091
    . "${ROOT}/backend/.env.local"
    set +a
    cd "${ROOT}/backend" || exit 1
    uv run python scripts/live_session_admin.py "$@"
  )
}

_q() { docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc "$1" 2>/dev/null; }

MODE_LABEL="dry-run (집행하려면 --confirm)"
[ "${CONFIRM}" = "1" ] && MODE_LABEL="집행"
echo "══ 소크 재기동 — ${MODE_LABEL} ══"
echo

# ── 전제: 재기동 파라미터를 원장에서 딴다 ───────────────────────────────────────
# ★하드코딩하지 않는다. 최근 세션 행이 정본이다(2026-08-07 실측: 재기동 3 회 전부 동일).
if [ -z "${STRATEGY_ID}" ] || [ -z "${ACCOUNT_ID}" ]; then
  ROW="$(_q "SELECT strategy_id || ' ' || exchange_account_id || ' ' || symbol || ' ' || interval
             FROM trading.live_signal_sessions ORDER BY created_at DESC LIMIT 1")"
  if [ -n "${ROW}" ]; then
    [ -n "${STRATEGY_ID}" ] || STRATEGY_ID="$(printf '%s' "${ROW}" | cut -d' ' -f1)"
    [ -n "${ACCOUNT_ID}" ] || ACCOUNT_ID="$(printf '%s' "${ROW}" | cut -d' ' -f2)"
    SYMBOL="$(printf '%s' "${ROW}" | cut -d' ' -f3)"
    INTERVAL="$(printf '%s' "${ROW}" | cut -d' ' -f4)"
    echo "  파라미터 출처: 원장 최근 세션 행"
  elif [ "${CONFIRM}" = "1" ]; then
    die "원장에 세션이 하나도 없다 — --strategy-id / --account-id 를 직접 줘라" 2
  else
    # dry-run 은 DB 없이도 절차를 보여줄 수 있어야 한다(워크트리·다른 머신).
    STRATEGY_ID="${STRATEGY_ID:-<원장 최근 세션에서 조회>}"
    ACCOUNT_ID="${ACCOUNT_ID:-<원장 최근 세션에서 조회>}"
    echo "  파라미터 출처: 원장 조회 실패 — dry-run 이라 자리표시로 계속한다"
  fi
fi
echo "  strategy=${STRATEGY_ID}"
echo "  account =${ACCOUNT_ID}"
echo "  symbol  =${SYMBOL}  interval=${INTERVAL}"
echo

# ── dry-run: 8 단계를 출력만 하고 끝낸다 ────────────────────────────────────────
# ★dry-run 은 **아무것도 실행하지 않는다.** ⑴ 은 거래소에 포지션을 조회하는 외부 호출이라
#   「출력만」이라는 계약을 깬다. 실제 flat 여부는 --confirm 이 첫 단계로 직접 확인한다.
if [ "${CONFIRM}" != "1" ]; then
  cat << EOF
⑴ live_session_admin.py status 로 FLAT=YES 확인
   ★세션 DELETE 204 는 아무것도 flat 하지 않는다 (3회 덴 함정)
   ★status 는 포지션만 본다 — resting 조건부 주문은 세지 않는다
     cd ${ROOT}/backend && uv run python scripts/live_session_admin.py status --symbol ${SYMBOL}

⑵ FLAT=NO 면 stop → flatten (★순서가 중요하다 — 세션이 살아 있으면 다음 tick 에 재진입한다)
     … live_session_admin.py stop    <session_id> --confirm
     … live_session_admin.py flatten <session_id> --confirm
   ★이 스크립트는 자동 flatten 을 하지 않는다. FLAT=NO 면 그 자리에서 멈춘다.

⑶ 사용자 승인 (= --confirm)

⑷ soak-stack.sh down → pin → up
   ★돌고 있는 고정본 위엔 pin 이 거부된다(exit 2) · up 은 celery 배너를 최대 600초 기다린다

⑸ live_session_admin.py start --strategy-id ${STRATEGY_ID} --account-id ${ACCOUNT_ID} \\
     --symbol ${SYMBOL} --interval ${INTERVAL} --confirm
   ★up 은 세션을 만들지 않는다. 세션 0 = 시계 0

⑹ 새 세션 uuid 를 정규식으로 추출 + 원장 대조
   ★'✓ 세션 등재: <uuid>' 는 멀티바이트 3토큰이라 awk \$3 은 '등재:' 를 준다

⑺ soak-observe.sh --baseline --session <uuid>
   ★이것만이 SESSION_ID=<uuid> 형식을 쓴다. 손으로 쓰면 소싱이 rc=127 로 죽는다
   ★--session 은 플래그다. 위치인자로 주면 unknown arg (exit 64)

⑻ soak-gate.sh 로 창 확인
   ★C2(최장 연속)는 리셋된다. C1(누적)은 유지된다

══ dry-run 종료 — 아무것도 실행하지 않았다. 집행하려면 --confirm ══
EOF
  exit 0
fi

# ── ⑴ FLAT=YES 확인 ─────────────────────────────────────────────────────────────
echo "⑴ live_session_admin.py status 로 FLAT=YES 확인"
echo "   ★세션 DELETE 204 는 아무것도 flat 하지 않는다 (3회 덴 함정)"
STATUS_OUT="$(_admin status --symbol "${SYMBOL}" 2>&1)"
STATUS_RC=$?
printf '%s\n' "${STATUS_OUT}" | sed 's/^/   | /'
if [ "${STATUS_RC}" -ne 0 ]; then
  die "status 조회 실패 — flat 여부를 모른 채 재기동하지 않는다" 2
fi
FLAT="$(printf '%s\n' "${STATUS_OUT}" | sed -n 's/^FLAT=\(.*\)$/\1/p' | tail -1)"
if [ "${FLAT}" != "YES" ]; then
  echo
  echo "⑵ FLAT=${FLAT:-불명} — **여기서 멈춘다.** 자동 flatten 은 하지 않는다."
  echo "   사람이 판단하고 직접 실행해라 (★순서는 stop → flatten):"
  ACTIVE="$(_q "SELECT id FROM trading.live_signal_sessions WHERE deactivated_at IS NULL LIMIT 1")"
  echo "     cd ${ROOT}/backend && uv run python scripts/live_session_admin.py stop    ${ACTIVE:-<session_id>} --confirm"
  echo "     cd ${ROOT}/backend && uv run python scripts/live_session_admin.py flatten ${ACTIVE:-<session_id>} --confirm"
  echo "   ★status 는 포지션만 본다 — resting 조건부 주문은 세지 않는다. 거래소에서 눈으로 확인해라."
  exit 1
fi
echo "   ✓ FLAT=YES"
echo
echo "⑵ (건너뜀 — 이미 flat 이다)"
echo
echo "⑶ 사용자 승인 — ✓ --confirm"
echo

# ── ⑷ down → pin → up ───────────────────────────────────────────────────────────
echo "⑷ soak-stack.sh down → pin → up"
bash "${SCRIPT_DIR}/soak-stack.sh" down || die "down 실패" 1
bash "${SCRIPT_DIR}/soak-stack.sh" pin || die "pin 실패 (돌고 있는 고정본 위인가? backend/src 가 dirty 한가?)" 1
echo "   … up 은 celery 기동 배너를 최대 600초 기다린다"
bash "${SCRIPT_DIR}/soak-stack.sh" up || die "up 실패 — 창을 열지 않았다" 1
echo

# ── ⑸ 세션 등재 ─────────────────────────────────────────────────────────────────
echo "⑸ live_session_admin.py start (★up 은 세션을 만들지 않는다. 세션 0 = 시계 0)"
START_OUT="$(_admin start --strategy-id "${STRATEGY_ID}" --account-id "${ACCOUNT_ID}" \
  --symbol "${SYMBOL}" --interval "${INTERVAL}" --confirm 2>&1)"
START_RC=$?
printf '%s\n' "${START_OUT}" | sed 's/^/   | /'
[ "${START_RC}" -eq 0 ] || die "세션 등재 실패" 1
echo

# ── ⑹ uuid 추출 ─────────────────────────────────────────────────────────────────
echo "⑹ 새 세션 uuid 추출 (정규식 — awk \$3 은 '등재:' 를 준다)"
NEW_ID="$(printf '%s\n' "${START_OUT}" \
  | grep -Eo '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)"
[ -n "${NEW_ID}" ] || die "세션 uuid 를 못 읽었다" 1
# 원장 대조 — 출력만 믿지 않는다.
DB_ID="$(_q "SELECT id FROM trading.live_signal_sessions WHERE id = '${NEW_ID}'")"
[ "${DB_ID}" = "${NEW_ID}" ] || die "추출한 uuid 가 원장에 없다: ${NEW_ID}" 1
echo "   ✓ ${NEW_ID} (원장 대조 완료)"
echo

# ── ⑺ baseline 앵커 ─────────────────────────────────────────────────────────────
echo "⑺ soak-observe.sh --baseline --session ${NEW_ID}"
echo "   ★이것만이 SESSION_ID=<uuid> 형식을 쓴다. 손으로 쓰면 소싱이 rc=127 로 죽는다."
bash "${SCRIPT_DIR}/soak-observe.sh" --baseline --session "${NEW_ID}" || die "baseline 앵커 실패" 1
# 형식 단언 — 이 회차가 고치려는 바로 그 사고를 재발 방지한다.
if ! grep -q '^SESSION_ID=' "${ROOT}/.soak/session" 2>/dev/null; then
  die ".soak/session 이 SESSION_ID= 형식이 아니다 — soak-observe.sh 가 안 썼다" 1
fi
echo "   ✓ $(cat "${ROOT}/.soak/session")"
echo

# ── ⑻ 창 확인 ───────────────────────────────────────────────────────────────────
echo "⑻ soak-gate.sh 로 창 확인"
GATE_OUT="$(bash "${SCRIPT_DIR}/soak-gate.sh" 2>&1)"
GATE_RC=$?
printf '%s\n' "${GATE_OUT}" | sed 's/^/   | /'
echo
echo "══ 재기동 완료 — 세션 ${NEW_ID} · 게이트 종료 코드 ${GATE_RC} ══"
echo "  ★C2(최장 연속)는 리셋됐다. C1(누적)은 유지된다."
exit 0
