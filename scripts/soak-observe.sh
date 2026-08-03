#!/usr/bin/env bash
# 데모 소크 일일 원장 대조 — 읽기 전용. 소크 관측 계층이 레포에 집이 없어 매 회차
# scratchpad 로 다시 지어지던 것을 닫는다(이전 회차 watch_soak.sh / measure_window.sh 는
# 세션 임시 디렉터리에만 있었고 전부 사라졌다).
#
# 사용:
#   scripts/soak-observe.sh --baseline --session <uuid>   # 소크 시작 시 1회
#   scripts/soak-observe.sh                               # 이후 하루 한 번
#
# 설계 원칙 — 전부 이 레포가 실제로 데인 함정에서 나왔다:
#   · 창은 시계가 아니라 **세션 created_at** 으로 잡는다(now()-6h 가 직전 소크 22건을 끌어왔다).
#   · counter 는 **차분만** 본다(출생일 다른 counter 는 절대값이 126 vs 99 로 어긋나도 차분은 일치).
#     이전 스냅샷에 없던 series 는 `after-0` 이 아니라 **NEW** 로 표기한다.
#   · **fail-closed** — 조회 실패는 「이상 없음」이 아니라 UNKNOWN + 비-0 종료다
#     (감시 스크립트가 fail-open 이라 죽은 세션을 「생존」으로 보고한 전례).
#   · **boolean 을 판정에 쓰지 않는다**(`is_active` 는 bare 컬럼이면 t/f, 캐스트하면 true/false).
#     ★단 그 대체를 `deactivated_reason` 으로 두면 안 된다 — 실측 25세션 중 **12세션이
#     `is_active=false` 인데 `deactivated_reason IS NULL`** 이라 죽은 세션이 "살아있음" 으로
#     찍힌다(fail-closed 를 표방한 도구의 fail-open). 판정은 **`deactivated_at`** 으로 하고
#     `is_active` 와 사유는 **읽는 사람에게 보여만 준다**.
#   · `psql -c` 는 **문장 하나씩**(세미콜론 여럿 = 암묵적 단일 트랜잭션).
#   · 집계 JOIN 앞에 **JOIN 없는 count** 를 먼저 찍는다(JOIN 팬아웃이 1건을 14건으로 불렸다).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_DIR="${REPO_ROOT}/.soak"
DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
METRICS_URL="${QB_METRICS_URL:-http://localhost:8100/metrics}"
# 유도 주입 표식 — 이 두 값의 이벤트는 합성이다(H8 분기 유도용). 통계에서 분리해 보여준다.
PROBE_SEQ=9999
PROBE_TRADE_ID="h8_probe"

FAILED=0
BASELINE=0
SESSION_ARG=""

while [ $# -gt 0 ]; do
  case "$1" in
    --baseline) BASELINE=1 ;;
    --session) shift; SESSION_ARG="${1:-}" ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done

# 조회 실패를 「이상 없음」으로 수렴시키지 않는다 — UNKNOWN 은 별도 상태다.
q() {
  local out
  if ! out="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -P pager=off -c "$1" 2>&1)"; then
    echo "  UNKNOWN — psql 실패: ${out}"
    FAILED=1
    return 1
  fi
  printf '%s\n' "${out}"
}

hdr() { printf '\n\033[1m── %s\033[0m\n' "$1"; }

mkdir -p "${STATE_DIR}"

# ── 세션 앵커 ────────────────────────────────────────────────────────────
if [ "${BASELINE}" = "1" ]; then
  [ -n "${SESSION_ARG}" ] || { echo "--baseline 에는 --session <uuid> 가 필요하다" >&2; exit 64; }
  printf 'SESSION_ID=%s\n' "${SESSION_ARG}" > "${STATE_DIR}/session"
  echo "baseline 기록: ${STATE_DIR}/session"
fi

if [ ! -f "${STATE_DIR}/session" ]; then
  echo "UNKNOWN — ${STATE_DIR}/session 없음. 먼저 --baseline --session <uuid> 로 앵커를 박아라." >&2
  exit 3
fi
# shellcheck disable=SC1090
. "${STATE_DIR}/session"
SESSION_ID="${SESSION_ID:?}"

T0="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -At \
      -c "SELECT created_at FROM trading.live_signal_sessions WHERE id = '${SESSION_ID}'" 2>&1)" || {
  echo "UNKNOWN — 세션 앵커 조회 실패: ${T0}" >&2; exit 3; }
[ -n "${T0}" ] || { echo "UNKNOWN — 세션 ${SESSION_ID} 가 DB 에 없다" >&2; exit 3; }

echo "session=${SESSION_ID}"
echo "T0=${T0}   (★창은 시계가 아니라 이 값이다)"
echo "now=$(date -u '+%Y-%m-%d %H:%M:%S+00')"

# ── 1. 세션 생존 ─────────────────────────────────────────────────────────
hdr "1. 세션 생존 (★판정은 deactivated_at — reason 은 NULL 일 수 있다)"
q "SELECT CASE WHEN deactivated_at IS NULL THEN '살아있음' ELSE '죽음' END AS alive,
          coalesce(deactivated_reason, CASE WHEN deactivated_at IS NULL THEN '-'
                                            ELSE '(사유미기록)' END) AS death_reason,
          is_active::text AS is_active,
          to_char(last_evaluated_bar_time, 'YYYY-MM-DD HH24:MI') AS last_bar,
          round(extract(epoch FROM (now() - last_evaluated_bar_time))/60.0) AS bar_age_min,
          round(extract(epoch FROM (now() - created_at))/3600.0, 2) AS soak_hours
     FROM trading.live_signal_sessions WHERE id = '${SESSION_ID}'"

# ── 2. 주문 원장 ─────────────────────────────────────────────────────────
hdr "2. 주문 — 일자 × state (★컬럼은 state, status 아님 / 진입 분모는 여기다)"
q "SELECT date_trunc('day', created_at)::date AS d, state::text, count(*)
     FROM trading.orders WHERE created_at >= timestamptz '${T0}'
    GROUP BY 1, 2 ORDER BY 1 DESC, 3 DESC"

# ── 3. outbox 원장 ───────────────────────────────────────────────────────
hdr "3. live_signal_events — action × status × error (★조건부 진입은 여기를 안 탄다)"
q "SELECT action, status,
          coalesce(substring(error_message from 1 for 40), '-') AS err,
          count(*) FILTER (WHERE NOT (sequence_no = ${PROBE_SEQ} AND trade_id = '${PROBE_TRADE_ID}')) AS real,
          count(*) FILTER (WHERE sequence_no = ${PROBE_SEQ} AND trade_id = '${PROBE_TRADE_ID}') AS probe
     FROM trading.live_signal_events
    WHERE session_id = '${SESSION_ID}'
    GROUP BY 1, 2, 3 ORDER BY 4 DESC, 5 DESC"

# ── 4. counter 차분 ──────────────────────────────────────────────────────
hdr "4. counter 차분 (★절대값 비교 금지 — 이전 스냅샷 대비 변화만)"
SNAP="${STATE_DIR}/snap-$(date -u '+%Y%m%dT%H%M%SZ').txt"
# ★`live_conditional_guard`/`plan_drop_evaluations` 는 BL-589 수리로 시장가 전환이 늘어나는
# 것을 보기 위해 넣었다. 볼 눈금은 `breach_with_resting`(막힌 드롭) 대 `market_converted`(전환).
# 절대값은 출생일이 달라 비교 불가 — **차분만** 본다.
if ! curl -sf --max-time 30 "${METRICS_URL}" \
     | grep -E '^qb_(live_signal_dispatch|live_signal_skipped|live_signal_evaluated|live_signal_divergence|live_conditional_reconcile_errors|live_conditional_guard|live_conditional_plan_drop_evaluations|live_position_divergence|metrics_mutation_failed|metrics_render_fallback)' \
     | sort > "${SNAP}"; then
  echo "  UNKNOWN — ${METRICS_URL} 스크레이프 실패"
  FAILED=1
  rm -f "${SNAP}"
else
  PREV="$(ls -1 "${STATE_DIR}"/snap-*.txt 2>/dev/null | grep -v "$(basename "${SNAP}")" | tail -1 || true)"
  if [ -z "${PREV}" ]; then
    echo "  (첫 스냅샷 — 차분 없음). 기록: ${SNAP##*/}, $(wc -l < "${SNAP}" | tr -d ' ') series"
  else
    echo "  이전: ${PREV##*/}  →  현재: ${SNAP##*/}"
    awk '
      NR==FNR { v=$NF; $NF=""; prev[$0]=v; seen[$0]=1; next }
              { v=$NF; $NF=""; k=$0
                if (!(k in seen))      { printf "  NEW      %s = %s\n", k, v; n++ }
                else if (prev[k] != v) { printf "  Δ %+8g  %s : %s -> %s\n", v-prev[k], k, prev[k], v; n++ }
                cur[k]=1 }
      END     { for (k in seen) if (!(k in cur)) { printf "  MISSING  %s (이전 %s) ★스냅샷 유실 의심\n", k, prev[k]; n++ }
                if (n == 0) print "  (변화 없음 — 카운터가 하나도 안 움직였다. 세션 생존을 먼저 의심해라)" }
    ' "${PREV}" "${SNAP}"
  fi
fi

# ── 5. H8 불변식 ─────────────────────────────────────────────────────────
hdr "5. H8 불변식 — 「거절로 기록됐는데 주문이 나갔다」 (정상=0행)"
echo "  분모(JOIN 없이 먼저 센다 — JOIN 팬아웃 방지):"
q "SELECT count(*) AS close_position_flat_events
     FROM trading.live_signal_events
    WHERE session_id = '${SESSION_ID}'
      AND status = 'failed' AND error_message = 'close_position_flat'"
echo "  위반 행:"
q "SELECT left(e.id::text, 8) AS event, e.sequence_no, e.trade_id,
          left(o.id::text, 8) AS \"order\", o.state::text, o.reduce_only
     FROM trading.live_signal_events e
     JOIN trading.orders o
       ON o.idempotency_key = 'live:' || e.session_id
        || ':' || to_char(e.bar_time AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS+00:00')
        || ':' || e.sequence_no || ':' || e.action || ':' || e.trade_id
    WHERE e.session_id = '${SESSION_ID}'
      AND e.status = 'failed' AND e.error_message = 'close_position_flat'"

# ── 6. /metrics 디렉터리 ─────────────────────────────────────────────────
hdr "6. /metrics 멀티프로세스 디렉터리 (BL-581 Trigger = 20000 파일)"
if [ -d "${REPO_ROOT}/backend/.metrics" ]; then
  printf '  files=%s  size=%s\n' \
    "$(find "${REPO_ROOT}/backend/.metrics" -maxdepth 1 -type f -name '*.db' | wc -l | tr -d ' ')" \
    "$(du -sh "${REPO_ROOT}/backend/.metrics" | cut -f1)"
else
  echo "  UNKNOWN — backend/.metrics 없음"
  FAILED=1
fi

if [ "${FAILED}" != "0" ]; then
  printf '\n\033[1;31m✗ 일부 조회가 실패했다 — 위 UNKNOWN 을 「이상 없음」으로 읽지 마라.\033[0m\n'
  exit 3
fi
printf '\n\033[1;32m✓ 전 항목 조회 성공.\033[0m 이상이 없으면 아무것도 고치지 마라 — 시계를 세우는 게 더 비싸다.\n'
