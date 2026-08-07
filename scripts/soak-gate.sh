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
#   scripts/soak-gate.sh --install / --uninstall / --status         # 30분마다 (macOS launchd / 리눅스 systemd user timer)
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
# ★스케줄러는 OS 마다 다르다 — macOS 는 launchd, 리눅스(클라우드 소크)는 systemd user timer.
# 판정 술어는 한 줄도 갈리지 않는다. 갈리는 것은 「누가 30분마다 부르나」와 「로그가 어디 쌓이나」뿐이다.
# 스케줄러 경로는 그걸 쓰는 함수 안에서만 산다 — 상단에서 OS 별로 갈리는 것은 LOGDIR 하나뿐이다.
LABEL="dev.quantbridge.soak-gate"   # launchd Label 이자 systemd unit 이름 (둘 다 점을 허용한다)
QB_OS="$(uname -s)"
if [ "${QB_OS}" = "Darwin" ]; then
  LOGDIR="$HOME/Library/Logs/quantbridge"
else
  LOGDIR="${XDG_STATE_HOME:-$HOME/.local/state}/quantbridge"
fi
DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
WORKER_CONTAINER="${QB_WORKER_CONTAINER:-quantbridge-worker}"
REDIS_CONTAINER="${QB_REDIS_CONTAINER:-quantbridge-redis}"
# ★[BL-620] — 기본 취득 경로는 **HTTP 가 아니라 멀티프로세스 디렉터리 직독**이다.
#   소크 스택(`soak-stack.sh up`)은 worker·beat·ws-stream·db·redis 5종만 띄우고 **API
#   컨테이너가 없다**. `/metrics` 를 내주던 것은 호스트 uvicorn 이었고, 그게 안 떠 있으면
#   C5⑷ 가 영구 ✗ 라 **C1/C2 를 다 채워도 PASS 가 구조적으로 불가능**했다(2026-08-07 실측:
#   `:8100` 리스너 0개). 워커는 같은 counter 를 `backend/.metrics` 에 계속 쓰고 있으므로
#   HTTP 를 거치지 않고 거기서 읽는다 — 「API 가 꺼지면 게이트가 장님」이라는 실패 계열이 사라진다.
#   ★`QB_METRICS_URL` 을 **명시하면** 종전대로 HTTP 를 쓴다(원격 데몬 + ssh 터널 운영안 보존).
METRICS_URL="${QB_METRICS_URL:-}"
METRICS_DIR="${QB_METRICS_DIR:-${ROOT}/backend/.metrics}"

mkdir -p "${STATE_DIR}" "${LOGDIR}"

SINCE=""
AS_JSON=0
COLLECT=1
REQUIRE_HOURS=""
REQUIRE_CONTINUOUS=""

_install_systemd() {
  # ★user timer 를 쓴다 — launchd LaunchAgent 와 같은 층(사용자 단위, sudo 불필요)이다.
  # 대신 로그인 세션 없이 돌려면 lingering 이 필요하다. 아래에서 켜고, 실패하면 알려만 준다.
  local paths="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "${unit_dir}"
  cat > "${unit_dir}/${LABEL}.service" <<UNIT_EOF
[Unit]
Description=QuantBridge soak gate ([BL-003] 168h/24h 판정기)

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PATH=${paths}
ExecStart=/bin/bash ${ROOT}/scripts/soak-gate.sh
UNIT_EOF
  cat > "${unit_dir}/${LABEL}.timer" <<UNIT_EOF
[Unit]
Description=QuantBridge soak gate — 30분마다

[Timer]
OnBootSec=1min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
UNIT_EOF
  systemctl --user daemon-reload || { echo "✗ systemctl --user daemon-reload 실패" >&2; exit 1; }
  systemctl --user enable --now "${LABEL}.timer" \
    || { echo "✗ timer enable 실패" >&2; exit 1; }
  # ★lingering 이 없으면 SSH 를 끊는 순간 user manager 가 죽어 timer 도 멈춘다 — 소크에 치명적.
  if ! loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null | grep -qi '^yes$'; then
    if ! loginctl enable-linger "$(id -un)" 2>/dev/null; then
      echo "⚠ lingering 을 못 켰다 — SSH 를 끊으면 timer 가 멈춘다." >&2
      echo "  직접 실행해라: sudo loginctl enable-linger $(id -un)" >&2
    fi
  fi
  echo "✓ 설치 완료 — 30분마다 표본을 남기고 판정한다 (systemd user timer)"
  echo "  ★표본이 없으면 tick 연속성(C4)을 판정할 수 없어 UNKNOWN(측정불가) 이 된다."
  echo "  ★docker 를 sudo 없이 부를 수 있어야 한다: id -nG | grep docker"
  echo "  로그: journalctl --user -u ${LABEL}.service"
  exit 0
}

_uninstall_systemd() {
  local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  systemctl --user disable --now "${LABEL}.timer" 2>/dev/null || true
  rm -f "${unit_dir}/${LABEL}.timer" "${unit_dir}/${LABEL}.service"
  systemctl --user daemon-reload 2>/dev/null || true
  echo "✓ 해제 완료 (표본·로그는 남긴다)"
  exit 0
}

_install() {
  [ "${QB_OS}" != "Darwin" ] && _install_systemd
  # ★PATH 를 명시하지 않으면 launchd 가 docker/python3 를 못 찾아 **조용히 실패**한다.
  local paths="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  local plist="$HOME/Library/LaunchAgents/${LABEL}.plist"
  cat > "${plist}" <<PLIST_EOF
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
  launchctl unload "${plist}" 2>/dev/null || true
  launchctl load "${plist}" || { echo "✗ launchctl load 실패" >&2; exit 1; }
  echo "✓ 설치 완료 — 30분마다 표본을 남기고 판정한다"
  echo "  ★표본이 없으면 tick 연속성(C4)을 판정할 수 없어 UNKNOWN(측정불가) 이 된다."
  exit 0
}

_uninstall() {
  [ "${QB_OS}" != "Darwin" ] && _uninstall_systemd
  local plist="$HOME/Library/LaunchAgents/${LABEL}.plist"
  launchctl unload "${plist}" 2>/dev/null || true
  rm -f "${plist}"
  echo "✓ 해제 완료 (표본·로그는 남긴다)"
  exit 0
}

_status() {
  # ★OS 를 안 가르면 리눅스에서 timer 가 멀쩡히 도는데도 「등록 안 됨」이 뜬다 — 거짓 상태 보고다.
  if [ "${QB_OS}" = "Darwin" ]; then
    echo "── launchd ──"
    launchctl list 2>/dev/null | grep -F "${LABEL}" || echo "  (등록 안 됨)"
  else
    echo "── systemd user timer ──"
    if systemctl --user is-active --quiet "${LABEL}.timer" 2>/dev/null; then
      systemctl --user list-timers --no-pager --no-legend "${LABEL}.timer" 2>/dev/null \
        | sed 's/^/  /' || true
      loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null | grep -qi '^yes$' \
        || echo "  ⚠ lingering 꺼짐 — SSH 끊기면 멈춘다 (sudo loginctl enable-linger $(id -un))"
    else
      echo "  (등록 안 됨)"
    fi
  fi
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
#
# ★★`DB_OK=0` 을 함수 **안**에서 세우면 안 된다 — `X="$(_q ...)"` 는 command substitution
#   이라 서브셸에서 돌고 대입이 부모로 전파되지 않는다(실측: `DB_OK` 가 1 로 남는다).
#   그래서 함수는 **종료 코드만** 내고, 부모가 `|| DB_OK=0` 으로 받는다(codex P1).
DB_OK=1
_q() {
  docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc "$1" 2>/dev/null
}

NOW="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc "SELECT now();" 2>/dev/null)"
[ -n "${NOW}" ] || { DB_OK=0; NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"; }

# 세션 원장. ★생존 판정은 `deactivated_at` — `is_active`/`reason` 은 판정에 쓰지 않는다.
SESSIONS_TSV="$(_q "
SELECT id, created_at, COALESCE(deactivated_at::text,''), COALESCE(deactivated_reason,''),
       COALESCE(last_evaluated_bar_time::text,''),
       CASE interval WHEN '1m' THEN 60 WHEN '5m' THEN 300 WHEN '15m' THEN 900 WHEN '1h' THEN 3600 ELSE 60 END
FROM trading.live_signal_sessions ORDER BY created_at;")" || DB_OK=0

# 활성 세션 (표본용). ★이 조회가 실패했는데 위가 성공하면 빈 표본이 기록되고, 그 빈 표본이
#   모든 세션의 C4 공백을 메운다 — 그래서 실패 시 표본을 **아예 남기지 않는다**.
ACTIVE_OK=1
ACTIVE_TSV="$(_q "
SELECT id, COALESCE(last_evaluated_bar_time::text,'')
FROM trading.live_signal_sessions WHERE deactivated_at IS NULL;")" || { DB_OK=0; ACTIVE_OK=0; }

# 스택이 고정본인가 — C5⑵
STACK_PINNED=0
bash "${ROOT}/scripts/soak-stack.sh" assert-not-pinned >/dev/null 2>&1 || STACK_PINNED=1

# redis AOF 판독성 — C5⑸ ([BL-594])
#
# 재는 것은 「redis 가 떠 있는가」가 아니라 **「지금 재기동하면 뜨는가」**다. AOF 는
# **기동 시에만** 읽히고 healthcheck(`redis-cli ping`)는 떠 있는 프로세스에만 물으므로,
# 판독 불가 AOF 위에서도 ping 은 PONG 이다 — 실측으로 그렇게 6일을 갔다(2026-08-05,
# 35.6MB 중 86.6% 판독 불가). 소크 창 안에 호스트 재부팅이 들어오면 그때 워커가 안 뜬다.
#
# ★`--fix` 를 절대 넘기지 않는다. 읽기 전용이다 (실측: `--fix` 없이 돌린 전후로 AOF
#   3파일의 md5·크기·mtime 이 전부 불변).
# ★★**종료 코드는 판별식이 될 수 없다** — 꼬리 절단은 exit 1 인데 서버는 뜬다. 판정 규칙과
#   그 근거(실측 표)는 `backend/scripts/redis_aof_readability.py` 에 있고, 실측 캡처 7형이
#   `backend/tests/scripts/test_redis_aof_readability.py` 로 동결돼 있다. **여기 복제하지 않는다.**
# ★수집이 어떤 이유로든 실패하면 `aof_ok=0` 이다. redis 가 안 뜨는 것과 못 재는 것은
#   구분되지 않지만, **둘 다 「재기동 내성을 증명하지 못했다」**이고 방향은 fail-closed 다.
# ★★**외부 실행에 시간 제한을 건다** — docker daemon 이나 볼륨 I/O 가 멈추면 게이트 전체가
#   무기한 대기해 **표본 수집까지 함께 멈춘다**(fail-closed 조차 아니다). 30초는 실측
#   소요(수십 ms, 35MB AOF 에서도 1초 미만)에 비해 넉넉하다. 타임아웃이면 `__rc` 마커가
#   안 남으므로 분류기가 그대로 `0` 을 낸다. (`timeout` 가드는 `pre-push-guard-test.sh` 선례)
AOF_OK=0
AOF_TIMEOUT_BIN=""
for _c in timeout gtimeout; do
  if command -v "${_c}" >/dev/null 2>&1; then AOF_TIMEOUT_BIN="${_c}"; break; fi
done

AOF_RAW=""
if [ -n "${AOF_TIMEOUT_BIN}" ]; then
  AOF_RAW="$("${AOF_TIMEOUT_BIN}" 30 docker exec "${REDIS_CONTAINER}" sh -c '
  m=/data/appendonlydir/appendonly.aof.manifest
  [ -f "$m" ] || { echo "__missing=$m"; exit 0; }
  echo "__last_incr=$(grep " type i" "$m" | tail -1 | cut -d" " -f2)"
  redis-check-aof "$m" 2>&1
  echo "__rc=$?"
' 2>/dev/null)"
else
  # 시간 제한 없이 도는 것보다 **못 쟀다**가 낫다 — 무기한 대기는 소크 증거를 함께 멈춘다.
  echo "⚠ timeout(coreutils) 이 없다 — AOF 판독 검사를 건너뛴다. C5⑸ 는 측정 불가다." >&2
fi

AOF_FILE="$(mktemp)"
printf '%s' "${AOF_RAW}" > "${AOF_FILE}"
AOF_OK="$(python3 "${ROOT}/backend/scripts/redis_aof_readability.py" "${AOF_FILE}")"
[ "${AOF_OK}" = "1" ] || AOF_OK=0
rm -f "${AOF_FILE}"

# 표본 append (창 안 tick 연속성의 유일한 증거원)
if [ "${COLLECT}" = "1" ] && [ "${ACTIVE_OK}" = "1" ]; then
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
    # ★`--corpus-end` 로 **Docker 가 보장하는 로그 끝**을 넘긴다. 안 넘기면 분류기가
    #   앱 줄 정규식에서 지평을 유도하는데, 그 포맷은 timezone 을 버리고 UTC 로 강제하며
    #   무타임스탬프 후행 줄이 있으면 지평이 과소평가된다. 회복식은 그 지평으로
    #   「나았다」와 「아직 못 봄」을 가르므로 조용히 판정이 흔들린다(codex P2 2026-08-05).
    ( set -a; . "${ROOT}/backend/.env.local"; set +a
      docker logs "${WORKER_CONTAINER}" 2>&1 \
        | (cd "${ROOT}/backend" && uv run python scripts/classify_direction_divergence.py \
             --json --corpus-end "${LOG_LAST}" 2>&1)
    ) > "${PHANTOM_JSON}.tmp" 2>/dev/null
    # ★★분류기 **성공 여부를 따로 기록**한다. 껍데기 아카이브(verdicts 0)를 커버리지로
    #   인정하면 「phantom 없음 + 검증된 로그」로 읽혀 그 시간이 credit 되고 진짜 phantom 도
    #   숨는다 — fail-open 이다(codex P1). 성공의 정의는 둘 중 하나뿐이다:
    #     ⑴ 파싱되는 JSON 을 냈다   ⑵ 「관측이 없다」를 명시적으로 냈다(정상적인 0건)
    #   그 외(의존성·DB·인자 실패)는 `classifier_ok=false` 로 남기고 커버리지에서 제외된다.
    python3 - "${PHANTOM_JSON}.tmp" "${PHANTOM_JSON}" "${LOG_FIRST}" "${LOG_LAST}" <<'PY'
import json, pathlib, sys

src, dst, first, last = sys.argv[1:5]
raw_text = pathlib.Path(src).read_text() if pathlib.Path(src).exists() else ""
verdicts, ok, note, version = [], False, "", None
try:
    blob = json.loads(raw_text)
    verdicts = blob.get("verdicts", [])
    version = blob.get("predicate_version")
    ok, note = True, "json"
except Exception:
    if "관측이 없다" in raw_text:
        # 관측 0건은 실패가 아니다. 판을 못 읽었으므로 version 은 None 으로 남긴다 —
        # 이 아카이브는 커버리지만 제공하고 라벨 판정에는 기여하지 않는다.
        ok, note = True, "no-observations"
    else:
        note = (raw_text.strip().splitlines() or ["(빈 출력)"])[-1][:200]
pathlib.Path(dst).write_text(
    json.dumps(
        {
            "log_from": first,
            "log_to": last,
            "classifier_ok": ok,
            "classifier_note": note,
            # ★판별식의 판. 아카이브들이 서로 다른 판이면 게이트가 **옛 라벨을 영원히
            #   합집합에 남긴다** — 판을 올렸으면 옛 아카이브를 옮겨야 한다(아래 경고).
            "predicate_version": version,
            "verdicts": [
                {"at": v.get("at"), "label": v.get("label"), "session_id": v.get("session_id")}
                for v in verdicts
            ],
        },
        ensure_ascii=False,
    )
)
pathlib.Path(src).unlink(missing_ok=True)
if not ok:
    print(f"⚠ phantom 분류기 실패 — 이 창은 커버리지로 인정되지 않는다: {note}", file=sys.stderr)
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
#   ★취득 실패의 정의는 **경로와 무관하게 같아야 한다** — rc 가 0 이어도 **본문이 비면
#     null** 이다. 두 갈래 모두 `[ -n ... ]` 를 건다. 예전엔 직독 갈래에만 걸려 있었고,
#     그래서 `200 + 빈 본문`(API 가 뜨는 중이거나 mmap 이 비었을 때)이 `측정불가` 가 아니라
#     `0/0 표본없음` 으로 읽히는 **fail-open** 이 HTTP 쪽에만 남아 있었다. 이 파일이 산
#     구분이 바로 그 둘이므로 비대칭을 남기면 안 된다.
METRICS_RAW=""
METRICS_RC=1
if [ -n "${METRICS_URL}" ]; then
  METRICS_RAW="$(curl -sf --max-time 20 "${METRICS_URL}" 2>/dev/null)" \
    && [ -n "${METRICS_RAW}" ] && METRICS_RC=0
elif [ -d "${METRICS_DIR}" ]; then
  # ★`timeout` 없이 부르지 마라 — 게이트가 무기한 대기하면 표본 수집까지 멈춘다([BL-594] 교훈).
  METRICS_RAW="$(cd "${ROOT}/backend" && PROMETHEUS_MULTIPROC_DIR="${METRICS_DIR}" \
    timeout 120 uv run python -c '
import sys
from prometheus_client import CollectorRegistry, generate_latest, multiprocess

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)
sys.stdout.buffer.write(generate_latest(registry))
' 2>/dev/null)" && [ -n "${METRICS_RAW}" ] && METRICS_RC=0
fi
if [ "${METRICS_RC}" = "0" ]; then
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

# ★값을 파이썬 **소스 안으로 확장하지 않는다.** `<<PY`(비인용 heredoc)로 psql 출력과 CLI
#   인자를 코드 문자열에 끼워 넣으면 개행·따옴표 하나가 프로그램 구조를 바꾼다(codex P2).
#   heredoc 은 `<<'PY'` 로 인용하고, 값은 **argv 와 stdin(TSV)** 으로만 넘긴다.
# ★TSV 를 stdin 으로 넘길 수 없다 — `python3 - <<'PY'` 는 **stdin 을 프로그램으로 읽는다**.
#   파이프를 붙이면 heredoc 이 이기고 세션 목록이 조용히 비어버린다(실측: auto_death 실격이
#   통째로 사라졌다). 그래서 TSV 도 **파일 경로**로 넘긴다.
SESSIONS_FILE="$(mktemp)"
printf '%s' "${SESSIONS_TSV}" > "${SESSIONS_FILE}"
PAYLOAD="$(python3 - \
  "${STATE_DIR}" "${NOW}" "${DARKNESS}" "${DB_OK}" "${STACK_PINNED}" \
  "${REQUIRE_HOURS}" "${REQUIRE_CONTINUOUS}" "${SINCE}" "${SESSIONS_FILE}" "${AOF_OK}" <<'PY'
import json, pathlib, sys

state = pathlib.Path(sys.argv[1])
now, darkness_raw, db_ok, stack_pinned = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
require_hours, require_continuous, since = sys.argv[6], sys.argv[7], sys.argv[8]
sessions_tsv = pathlib.Path(sys.argv[9]).read_text()
aof_ok = sys.argv[10]

sessions = []
for line in sessions_tsv.splitlines():
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

phantoms, coverage, versions = [], [], set()
for p in sorted(state.glob("phantom-*.json")):
    try:
        blob = json.loads(p.read_text())
    except Exception:
        continue
    if blob.get("log_from") and blob.get("log_to"):
        coverage.append({
            "from": blob["log_from"],
            "to": blob["log_to"],
            # 옛 아카이브에는 이 필드가 없다 — 없으면 인정하지 않는다(fail-closed).
            "classifier_ok": blob.get("classifier_ok") is True,
        })
    if blob.get("verdicts"):
        versions.add(blob.get("predicate_version"))
    for v in blob.get("verdicts", []):
        if v.get("at"):
            # ★출처를 붙인다 ([BL-596]) — 판독 불가 라벨이 게이트를 `측정불가` 로 세울 때
            #   운영자가 「frozenset 등재」와 「구판 아카이브 이동」 중 무엇을 해야 하는지는
            #   **어느 파일의 어느 판이었나**로만 갈린다. 기존 키는 안 건드리고 필드만 더한다.
            v.setdefault("archive", p.name)
            v.setdefault("predicate_version", blob.get("predicate_version"))
            phantoms.append(v)

# ★★아카이브들이 **현행이 아닌 판별식**으로 매긴 라벨을 들고 있으면 알려야 한다.
#   실격 사건은 `(시각, 종류, 상세)` 로만 dedup 되므로, 판별식을 개선해 `phantom` 하나를
#   취소해도 **옛 아카이브의 그 라벨이 합집합에 영원히 남는다**(실측 2026-08-05: 교체 후
#   4건이 그렇게 남았다). 방향은 fail-closed 라 거짓 PASS 는 안 되지만, **개선이 게이트에
#   반영되지 않는다.** 조용히 두지 않는다 — 옮기라고 말한다.
#
# ★★`len(versions) > 1` 로 판정하면 안 된다 — **남은 아카이브가 전부 구버전이면 집합
#   크기가 1 이라 경고가 안 뜬다**(codex challenge 2026-08-05 적발). 기준은 **현행 판**이고,
#   현행 판은 이 실행이 방금 남긴 아카이브가 가지고 있다(가장 최근 = 지금 분류기의 판).
current_version = None
for p in sorted(state.glob("phantom-*.json"), reverse=True):
    try:
        blob = json.loads(p.read_text())
    except Exception:
        continue
    if blob.get("verdicts") and blob.get("predicate_version"):
        current_version = blob["predicate_version"]
        break
stale = {v for v in versions if v != current_version} if current_version else versions
if stale:
    print(
        "⚠⚠ phantom 아카이브가 현행이 아닌 판별식으로 매겨져 있다 — 현행 "
        + f"{current_version!r}, 남아 있는 것: "
        + ", ".join(sorted(repr(v) for v in stale))
        + "\n   옛 라벨이 실격 목록에 그대로 남아 개선이 반영되지 않는다. 옛 아카이브를 "
        ".soak/superseded-<판>/ 로 옮겨라 (ADR-024 §아카이브 판).",
        file=sys.stderr,
    )

thresholds = {}
if require_hours:
    thresholds["require_hours"] = float(require_hours)
if require_continuous:
    thresholds["require_continuous_hours"] = float(require_continuous)

payload = {
    "now": now.strip(),
    "sessions": sessions,
    "pin_events": pin_events,
    "samples": samples,
    "phantom_observations": phantoms,
    "log_coverage": coverage,
    "darkness": json.loads(darkness_raw) if darkness_raw.strip() != "null" else None,
    "db_ok": db_ok == "1",
    "stack_pinned": stack_pinned == "1",
    "aof_ok": aof_ok == "1",
    "thresholds": thresholds,
}
if since:
    payload["since"] = since
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
)"
rm -f "${SESSIONS_FILE}"

RESULT="$(printf '%s' "${PAYLOAD}" | python3 "${ROOT}/backend/scripts/soak_gate_predicate.py")"
RC=$?

if [ "${AS_JSON}" = "1" ]; then
  printf '%s\n' "${RESULT}"
  exit "${RC}"
fi

VERDICT="$(printf '%s' "${RESULT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["verdict"])')"
WORD="$(printf '%s' "${RESULT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason_word"])')"
SUMMARY="$(printf '%s' "${RESULT}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["summary"])')"

# ★자기시험·조사 실행은 운영 상태 파일을 덮지 않는다.
#   `--require-*`/`--since` 는 문턱·창을 바꾸고, `--no-collect` 는 증거를 안 남기는 조사
#   실행이다(장애 주입 시험도 여기 온다). 어느 쪽이든 `--status` 가 그걸 현행 판정으로
#   보여주면 오독이다 — 실측으로 두 번 밟았다(문턱 0.1h PASS · 주입한 `측정불가`).
#   `last-result` 는 **증거를 남기는 운영 실행**의 기록이다.
if [ -z "${REQUIRE_HOURS}${REQUIRE_CONTINUOUS}${SINCE}" ] && [ "${COLLECT}" = "1" ]; then
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
