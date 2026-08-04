#!/usr/bin/env bash
#
# [BL-003] 「Bybit Demo 1주(168h) 안정 운영」 게이트 — **판정기이자 증거 수집기**.
#
# 사용:
#   scripts/soak-gate.sh                 # 표본을 남기고 판정한다
#   scripts/soak-gate.sh --json          # 판정 JSON 전문
#   scripts/soak-gate.sh --since <ISO>   # 평가 창 시작을 강제 (자기시험·과거 재판정용)
#   scripts/soak-gate.sh --no-collect    # 표본을 남기지 않고 지금 원장으로만 판정
#   scripts/soak-gate.sh --require-hours N --require-continuous N   # ★자기시험 전용
#   scripts/soak-gate.sh --install / --uninstall / --status         # launchd (30분마다)
#
# 종료 코드: 0 = PASS **만** / 1 = FAIL / 2 = UNKNOWN
#   ★**UNKNOWN 을 PASS 로 접지 않는다.** 이 스크립트의 존재 이유가 그것이다.
#   낱말은 셋뿐이라 `진행중`(시간 부족)과 `측정불가`(잴 수 없음)는 **사유 낱말**로 가른다.
#
# 술어와 창 정의: docs/decisions/024-soak-stability-gate.md
# 계산: backend/scripts/soak_gate_predicate.py (순수 함수 — I/O 없음, 손 계산과 대조 가능)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
STATE_DIR="${ROOT}/.soak"
PIN_HISTORY="${STATE_DIR}/pin-history.jsonl"
SAMPLES="${STATE_DIR}/gate-samples.jsonl"
LOGDIR="$HOME/Library/Logs/quantbridge"
LABEL="dev.quantbridge.soak-gate"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
WORKER_CONTAINER="${QB_WORKER_CONTAINER:-quantbridge-worker}"
METRICS_URL="${QB_METRICS_URL:-http://localhost:8100/metrics}"

mkdir -p "${STATE_DIR}" "${LOGDIR}"

SINCE=""
AS_JSON=0
COLLECT=1
REQUIRE_HOURS=""
REQUIRE_CONTINUOUS=""

_install() {
  # ★PATH 를 명시하지 않으면 launchd 가 docker/python3 를 못 찾아 **조용히 실패**한다.
  local paths="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  cat > "${PLIST}" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${ROOT}/scripts/soak-gate.sh</string>
  </array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>${paths}</string></dict>
  <key>StandardOutPath</key><string>${LOGDIR}/soak-gate.out.log</string>
  <key>StandardErrorPath</key><string>${LOGDIR}/soak-gate.err.log</string>
  <key>WorkingDirectory</key><string>${ROOT}</string>
</dict>
</plist>
PLIST_EOF
  launchctl unload "${PLIST}" 2>/dev/null || true
  launchctl load "${PLIST}" || { echo "✗ launchctl load 실패" >&2; exit 1; }
  echo "✓ 설치 완료 — 30분마다 표본을 남기고 판정한다"
  echo "  ★표본이 없으면 tick 연속성(C4)을 판정할 수 없어 UNKNOWN(측정불가) 이 된다."
  exit 0
}

_uninstall() {
  launchctl unload "${PLIST}" 2>/dev/null || true
  rm -f "${PLIST}"
  echo "✓ 해제 완료 (표본·로그는 남긴다)"
  exit 0
}

_status() {
  echo "── launchd ──"
  launchctl list 2>/dev/null | grep -F "${LABEL}" || echo "  (등록 안 됨)"
  echo "── 최근 판정 ──"
  [ -f "${LOGDIR}/soak-gate-last-result" ] && cat "${LOGDIR}/soak-gate-last-result" || echo "  (없음)"
  echo "── 표본 ──"
  if [ -f "${SAMPLES}" ]; then
    echo "  $(wc -l < "${SAMPLES}" | tr -d ' ')건 · 최근 $(tail -1 "${SAMPLES}" | sed 's/.*"at":"\([^"]*\)".*/\1/')"
  else
    echo "  (없음)"
  fi
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --install) _install ;;
    --uninstall) _uninstall ;;
    --status) _status ;;
    --json) AS_JSON=1 ;;
    --no-collect) COLLECT=0 ;;
    --since) [ $# -ge 2 ] || { echo "--since 에 값이 없다" >&2; exit 1; }; SINCE="$2"; shift ;;
    --require-hours) [ $# -ge 2 ] || { echo "--require-hours 에 값이 없다" >&2; exit 1; }; REQUIRE_HOURS="$2"; shift ;;
    --require-continuous) [ $# -ge 2 ] || { echo "--require-continuous 에 값이 없다" >&2; exit 1; }; REQUIRE_CONTINUOUS="$2"; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
  shift
done

# ---------------------------------------------------------------- 수집

# 조회 실패를 「이상 없음」으로 수렴시키지 않는다 — 실패는 C5 위반이고 UNKNOWN 이다.
DB_OK=1
_q() {
  docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc "$1" 2>/dev/null || {
    DB_OK=0
    return 1
  }
}

NOW="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc "SELECT now();" 2>/dev/null)"
[ -n "${NOW}" ] || { DB_OK=0; NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"; }

# 세션 원장. ★생존 판정은 `deactivated_at` — `is_active`/`reason` 은 판정에 쓰지 않는다.
SESSIONS_TSV="$(_q "
SELECT id, created_at, COALESCE(deactivated_at::text,''), COALESCE(deactivated_reason,''),
       COALESCE(last_evaluated_bar_time::text,''),
       CASE interval WHEN '1m' THEN 60 WHEN '5m' THEN 300 WHEN '15m' THEN 900 WHEN '1h' THEN 3600 ELSE 60 END
FROM trading.live_signal_sessions ORDER BY created_at;")"

# 활성 세션 (표본용)
ACTIVE_TSV="$(_q "
SELECT id, COALESCE(last_evaluated_bar_time::text,'')
FROM trading.live_signal_sessions WHERE deactivated_at IS NULL;")"

# 스택이 고정본인가 — C5⑵
STACK_PINNED=0
bash "${ROOT}/scripts/soak-stack.sh" assert-not-pinned >/dev/null 2>&1 || STACK_PINNED=1

# 표본 append (창 안 tick 연속성의 유일한 증거원)
if [ "${COLLECT}" = "1" ]; then
  {
    printf '{"at":"%s","sessions":[' "${NOW}"
    first=1
    while IFS='|' read -r sid bar; do
      [ -n "${sid}" ] || continue
      [ "${first}" = "1" ] || printf ','
      first=0
      if [ -n "${bar}" ]; then
        printf '{"id":"%s","last_evaluated_bar_time":"%s"}' "${sid}" "${bar}"
      else
        printf '{"id":"%s","last_evaluated_bar_time":null}' "${sid}"
      fi
    done <<< "${ACTIVE_TSV}"
    printf ']}\n'
  } >> "${SAMPLES}"
fi

# phantom 분류 — 워커 로그는 컨테이너 수명에 묶인다. 그래서 매 실행마다 보존한다.
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
PHANTOM_JSON="${STATE_DIR}/phantom-${STAMP}.json"
LOG_FIRST=""
LOG_LAST=""
if [ "${COLLECT}" = "1" ]; then
  LOG_FIRST="$(docker logs --timestamps "${WORKER_CONTAINER}" 2>&1 | head -1 | cut -d' ' -f1)"
  LOG_LAST="$(docker logs --timestamps "${WORKER_CONTAINER}" 2>&1 | tail -1 | cut -d' ' -f1)"
  if [ -n "${LOG_FIRST}" ] && [ -n "${LOG_LAST}" ]; then
    # ★분류기는 backend 의존성(sqlalchemy/asyncpg)과 DATABASE_URL 이 있어야 돈다.
    #   시스템 python3 로 돌리면 조용히 실패해 **verdicts 가 늘 0** 이 된다(실측 2026-08-04).
    #   ★`cd backend && set -a; . ./.env.local` 금지 — 이미 backend 면 cd 가 실패해
    #   `set -a` 만 건너뛴다. 절대경로로 소싱한다.
    # 관측 0건이면 분류기는 exit 1 + 텍스트를 낸다 — 그건 실패가 아니라 「phantom 없음」이다.
    ( set -a; . "${ROOT}/backend/.env.local"; set +a
      docker logs "${WORKER_CONTAINER}" 2>&1 \
        | (cd "${ROOT}/backend" && uv run python scripts/classify_direction_divergence.py --json 2>/dev/null)
    ) > "${PHANTOM_JSON}.tmp" 2>/dev/null
    python3 - "${PHANTOM_JSON}.tmp" "${PHANTOM_JSON}" "${LOG_FIRST}" "${LOG_LAST}" <<'PY' || rm -f "${PHANTOM_JSON}.tmp"
import json, sys, pathlib
src, dst, first, last = sys.argv[1:5]
try:
    raw = json.loads(pathlib.Path(src).read_text())
    verdicts = raw.get("verdicts", [])
except Exception:
    verdicts = []
pathlib.Path(dst).write_text(json.dumps(
    {"log_from": first, "log_to": last,
     "verdicts": [{"at": v.get("at"), "label": v.get("label"),
                   "session_id": v.get("session_id")} for v in verdicts]},
    ensure_ascii=False))
pathlib.Path(src).unlink(missing_ok=True)
PY
  fi
fi

# 어둠 비율 — 보고 전용(문턱 없음). 스크레이프 **실패**는 C5⑷ 위반이다.
#
# ★파이프 안에서 curl 의 rc 를 잃으면 안 된다 — 실측 2026-08-04: 죽은 포트를 가리켰는데
#   파이프 끝 python 이 `{"undecidable":0,"total":0}` 을 내서 **fail-open** 이 됐다
#   (측정 불가가 「어둠 0%」로 읽혔다). 그래서 curl 을 먼저 세우고 rc 를 본다.
#   ★단 `total=0` 자체는 정상일 수 있다 — counter 가 아직 한 번도 발화하지 않은 경우다.
#     그 둘을 구분해야 한다: 스크레이프 실패 = null(측정불가) / counter 부재 = 0/0(표본 없음).
METRICS_RAW=""
if METRICS_RAW="$(curl -sf --max-time 20 "${METRICS_URL}" 2>/dev/null)"; then
  DARKNESS="$(printf '%s' "${METRICS_RAW}" | python3 -c '
import re, sys, json
und = {"overflow","foreign_fill","close_without_open","duplicate_open","unreadable"}
tot = 0.0; bad = 0.0
for line in sys.stdin:
    m = re.match(r"^qb_live_ledger_derive_total\{outcome=\"([^\"]+)\"\}\s+([0-9.eE+-]+)", line)
    if not m: continue
    v = float(m.group(2)); tot += v
    if m.group(1) in und: bad += v
json.dump({"undecidable": bad, "total": tot}, sys.stdout)
')"
  [ -n "${DARKNESS}" ] || DARKNESS="null"
else
  DARKNESS="null"
fi

# ---------------------------------------------------------------- 판정

PAYLOAD="$(python3 - <<PY
import json, os, pathlib, sys

state = pathlib.Path("${STATE_DIR}")

sessions = []
for line in """${SESSIONS_TSV}""".splitlines():
    parts = line.split("|")
    if len(parts) < 6 or not parts[0]:
        continue
    sessions.append({
        "id": parts[0],
        "created_at": parts[1],
        "deactivated_at": parts[2] or None,
        "deactivated_reason": parts[3] or None,
        "last_evaluated_bar_time": parts[4] or None,
        "interval_seconds": int(parts[5]),
    })

def read_jsonl(path):
    out = []
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out

pin_events = read_jsonl(state / "pin-history.jsonl")
samples = read_jsonl(state / "gate-samples.jsonl")

phantoms, coverage = [], []
for p in sorted(state.glob("phantom-*.json")):
    try:
        blob = json.loads(p.read_text())
    except Exception:
        continue
    if blob.get("log_from") and blob.get("log_to"):
        coverage.append({"from": blob["log_from"], "to": blob["log_to"]})
    for v in blob.get("verdicts", []):
        if v.get("at"):
            phantoms.append(v)

thresholds = {}
if "${REQUIRE_HOURS}":
    thresholds["require_hours"] = float("${REQUIRE_HOURS}")
if "${REQUIRE_CONTINUOUS}":
    thresholds["require_continuous_hours"] = float("${REQUIRE_CONTINUOUS}")

payload = {
    "now": """${NOW}""".strip(),
    "sessions": sessions,
    "pin_events": pin_events,
    "samples": samples,
    "phantom_observations": phantoms,
    "log_coverage": coverage,
    "darkness": json.loads("""${DARKNESS}""") if """${DARKNESS}""".strip() != "null" else None,
    "db_ok": ${DB_OK} == 1,
    "stack_pinned": ${STACK_PINNED} == 1,
    "thresholds": thresholds,
}
if "${SINCE}":
    payload["since"] = "${SINCE}"
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
)"

RESULT="$(printf '%s' "${PAYLOAD}" | python3 "${ROOT}/backend/scripts/soak_gate_predicate.py")"
RC=$?

if [ "${AS_JSON}" = "1" ]; then
  printf '%s\n' "${RESULT}"
  exit "${RC}"
fi

VERDICT="$(printf '%s' "${RESULT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["verdict"])')"
WORD="$(printf '%s' "${RESULT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason_word"])')"
SUMMARY="$(printf '%s' "${RESULT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["summary"])')"

# ★자기시험 실행(`--require-*` / `--since`)은 운영 상태 파일을 덮지 않는다.
#   덮으면 `--status` 가 문턱 0.1h 짜리 PASS 를 현행 판정으로 보여준다(실측 오독 1회).
if [ -z "${REQUIRE_HOURS}${REQUIRE_CONTINUOUS}${SINCE}" ]; then
  printf '%s  %s %s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "${VERDICT}" "${WORD}" "${SUMMARY}" \
    > "${LOGDIR}/soak-gate-last-result"
fi

if [ -n "${REQUIRE_HOURS}${REQUIRE_CONTINUOUS}" ]; then
  echo "⚠⚠ 문턱이 기본값이 아니다 (--require-hours='${REQUIRE_HOURS}' --require-continuous='${REQUIRE_CONTINUOUS}')"
  echo "   이 실행은 **자기시험**이다. 게이트 판정으로 인용하지 마라."
fi
if [ -n "${SINCE}" ]; then
  echo "⚠ 평가 창 시작을 강제했다 (--since ${SINCE}) — 기본 T0 가 아니다."
fi

printf '\n══ [BL-003] 소크 안정 게이트 ══\n'
printf '판정: %s %s\n' "${VERDICT}" "${WORD}"
printf '%s\n\n' "${SUMMARY}"

RESULT_FILE="$(mktemp)"
printf '%s' "${RESULT}" > "${RESULT_FILE}"
python3 - "${RESULT_FILE}" <<'PY'
import json, pathlib, sys

r = json.loads(pathlib.Path(sys.argv[1]).read_text())
c, d = r["conditions"], r["detail"]


def mark(ok):
    return "✓" if ok else "✗"


print("  %s C1 누적       %.4fh / %.0fh" % (mark(c["C1_ok"]), c["C1_cumulative_hours"], c["C1_required"]))
print("  %s C2 최장 연속  %.4fh / %.0fh" % (mark(c["C2_ok"]), c["C2_longest_hours"], c["C2_required"]))
print("  %s C3 실격 사건  %d건" % (mark(c["C3_ok"]), len(c["C3_violations"])))
for v in c["C3_violations"][:5]:
    print("        · %s" % v)
print("  %s C4 표본 공백  %d건" % (mark(c["C4_ok"]), len(c["C4_sample_gaps"])))
for g in c["C4_sample_gaps"][:3]:
    print("        · %s" % g)
print("  %s C5 측정 무결  %s" % (mark(c["C5_ok"]), " ".join("%s=%s" % (k, mark(v)) for k, v in c["C5"].items())))
print()
print("  창 시작: %s   현재: %s" % (d["window_start"], d["now"]))
print("  귀속 창 %d개:" % len(d["windows"]))
for w in d["windows"]:
    print("        · %s %s %s ~ %s  %.4fh" % (w["session"], w["sha"], w["from"], w["to"], w["hours"]))
print("  ★귀속 불가 시간(계상 안 함): %.2fh" % d["unattributed_hours"])
print("  ★phantom 미검증이라 잘려나간 시간: %.4fh" % d.get("unverified_hours", 0.0))
dk = d.get("darkness")
if dk and dk.get("ratio") is not None:
    print("  어둠 비율(보고 전용): %.1f%%  (%.0f/%.0f)" % (dk["ratio"] * 100, dk["undecidable"], dk["total"]))
elif dk:
    print("  어둠 비율(보고 전용): 표본 없음 (derive_total 미발화 — 유도 계측이 아직 안 돌았다)")
else:
    print("  어둠 비율: ✗ 계산 실패 (C5 위반)")
if not d["thresholds_are_default"]:
    print("  ⚠ 문턱이 기본값이 아니다 — 자기시험 실행이다")
print("  전 이력 실격 사건 %d건" % len(d["disqualifications_all_time"]))
for v in d["disqualifications_all_time"]:
    print("        · %s" % v)
PY
rm -f "${RESULT_FILE}"
printf '\n종료 코드 %s  (0=PASS 만 · 1=FAIL · 2=UNKNOWN)\n' "${RC}"
exit "${RC}"
