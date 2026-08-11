#!/usr/bin/env bash
#
# 소크 무인 감시 — `soak-gate.sh` 를 1 회 부르고 **상태 지문이 바뀔 때만** 텔레그램으로 알린다.
#
# 왜 있나
#   게이트는 30 분마다 돌지만 출력을 journal 에 버릴 뿐이라 **알림이 0 줄**이다. 2026-08-06 20:31
#   사망 → 08-07 09:35 수동 재기동까지 13 시간이 비었고, 그 시간은 C1 에 **소급되지 않는다**
#   (게이트가 매번 「귀속 불가 시간」으로 출력한다). 사람이 알아채는 지연이 곧 [BL-003] 의 비용이다.
#   ★이 스크립트는 **판정 로직을 한 줄도 갖지 않는다.** 게이트의 출력을 읽고 「달라졌나」만 본다.
#
# 사용:
#   scripts/soak-watch.sh              # 1 회 감시 (타이머가 부르는 형태)
#   scripts/soak-watch.sh --dry-run    # 게이트는 부르되 알림은 쏘지 않고 판단만 출력
#   scripts/soak-watch.sh --status     # 마지막 지문 · heartbeat · 타이머 상태
#   scripts/soak-watch.sh --install    # systemd user timer 30 분 (★게이트 타이머는 끈다)
#   scripts/soak-watch.sh --uninstall  # watch 타이머 해제 (게이트 타이머를 되살린다)
#
# 종료 코드: 0 = 감시 주기 정상 수행 / 1 = **감시자 자신이 실패**(알림 전송 실패 · 게이트 부재)
#   ★게이트 판정은 종료 코드로 새어나오지 않는다. 게이트가 FAIL 이어도 **알림이 나갔으면 0** 이다.
#     그래야 systemd 의 빨간불이 「알림이 깨졌다」 하나만 뜻한다. 반대로 게이트 유닛은 UNKNOWN=2 를
#     그대로 내보내 **매 실행이 `Failed`** 로 찍혔다(2026-08-07 실측 8/8) — 그 노이즈를 여기서 끊는다.
#
# ★설계 근거 (전부 이 레포가 실제로 덴 것):
#   · **파이프 금지.** `out="$(...)"` 로 받고 `rc=$?` 를 즉시 보존한다. 파이프가 게이트 종료 코드를
#     가려 red 인 채로 커밋한 사고가 2 회 있었다.
#   · **크래시는 FAIL 이 아니다.** 판정기가 죽으면 `판정:` 이 **빈 값**인 채 exit 1 이 난다 — 진짜
#     FAIL 과 종료 코드가 같다. 판별자는 **C1 앵커 줄의 유무**다(2026-08-07 09:10 실측 캡처).
#   · **지문에 시간값을 넣지 않는다.** C1/C2 는 단조 증가하고 어둠 비율은 같은 날 2.9% → 70.6% 로
#     요동친다(09:41 / 13:11 실측). 넣으면 30 분마다 알림이 온다.
#   · **게이트를 기본 모드로 부른다.** `--no-collect` 는 phantom 아카이브를 안 남겨 게이트와 **다른
#     양**을 재게 되고(분류기가 깨져도 C5 가 ✓ 로 보인다 = fail-open), `--json` 은 last-result 를
#     쓰기 전에 exit 해 운영자의 `soak-gate.sh --status` 를 영구히 낡게 만든다.
#   · **외부 명령엔 반드시 timeout.** 무기한 대기는 표본 수집까지 멈춘다.
#   · **상태 파일을 `.` 로 소싱하지 않는다.** `.soak/session` 이 맨 uuid 로 쓰여 `command not found`
#     로 죽어 있는 것을 2026-08-07 에 실측했다. 여기서는 `key=value` 를 명시적으로 파싱한다.
#   · **토큰은 URL 경로에 있다.** URL 을 echo 하지 않고 `set -x` 를 켜지 않는다
#     (`backend/src/common/telegram_alert.py:52-65` 의 `_safe_err` 가 같은 이유로 존재한다).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
GATE="${SCRIPT_DIR}/soak-gate.sh"

# 상태 파일은 **`.soak/` 밖**에 둔다 — 게이트의 표본(gate-samples.jsonl)과 섞이면 안 된다.
# 게이트의 LOGDIR 과 같은 자리를 쓴다(`soak-gate.sh:32-36`).
if [ "$(uname -s)" = "Darwin" ]; then
  _DEFAULT_LOGDIR="${HOME}/Library/Logs/quantbridge"
else
  _DEFAULT_LOGDIR="${XDG_STATE_HOME:-${HOME}/.local/state}/quantbridge"
fi
STATE_FILE="${QB_SOAK_WATCH_STATE:-${_DEFAULT_LOGDIR}/soak-watch.state}"
ENV_FILE="${QB_SOAK_ENV_FILE:-${ROOT}/backend/.env.local}"

TELEGRAM_TIMEOUT="${QB_SOAK_TELEGRAM_TIMEOUT:-15}"
GATE_TIMEOUT="${QB_SOAK_GATE_TIMEOUT:-600}"

UNIT_NAME="dev.quantbridge.soak-watch"
GATE_UNIT="dev.quantbridge.soak-gate"

MODE="watch"
while [ $# -gt 0 ]; do
  case "$1" in
    --install) MODE="install" ;;
    --uninstall) MODE="uninstall" ;;
    --status) MODE="status" ;;
    --dry-run) MODE="dry-run" ;;
    -h | --help)
      sed -n '2,48p' "$0"
      exit 0
      ;;
    *)
      echo "알 수 없는 인자: $1  (--help)" >&2
      exit 1
      ;;
  esac
  shift
done

# ── 상태 파일 (key=value, 소싱하지 않는다) ──────────────────────────────────────
_state_get() { # _state_get <key> → stdout (없으면 빈 문자열)
  [ -f "${STATE_FILE}" ] || return 0
  sed -n "s/^$1=//p" "${STATE_FILE}" | head -1
}

_state_put() { # _state_put <fingerprint> <disq> <heartbeat_date>
  mkdir -p "$(dirname "${STATE_FILE}")" || return 1
  {
    printf 'FINGERPRINT=%s\n' "$1"
    printf 'DISQ=%s\n' "$2"
    printf 'HEARTBEAT_DATE=%s\n' "$3"
  } > "${STATE_FILE}"
}

# ── 알림 ────────────────────────────────────────────────────────────────────────
# 주입 seam: QB_SOAK_NOTIFY_CMD 가 설정되면 curl 대신 그 명령에 본문을 stdin 으로 넘긴다.
# 하네스가 실제 텔레그램을 쏘지 않게 하는 유일한 경로다(`QB_PRE_PUSH_BYPASS` 선례).
_notify() { # _notify <본문>  → 0 = 보냄 / 1 = 실패
  if [ -n "${QB_SOAK_NOTIFY_CMD:-}" ]; then
    printf '%s\n' "$1" | ${QB_SOAK_NOTIFY_CMD}
    return $?
  fi

  # 크레덴셜 — ★절대경로로 소싱한다. `cd backend && . ./.env.local` 은 이미 backend 에 있으면
  #   `cd` 가 실패해 `set -a` 만 건너뛰고 나머지가 이어져 env 가 export 되지 않는다(금지된 형태).
  if [ ! -f "${ENV_FILE}" ]; then
    echo "✗ env 파일이 없다: ${ENV_FILE}" >&2
    return 1
  fi
  # shellcheck disable=SC1090
  (
    set -a
    . "${ENV_FILE}"
    set +a

    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
      echo "✗ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 비어 있다" >&2
      exit 1
    fi

    # ★URL 을 출력하지 않는다 — 경로에 토큰이 들어 있다. 실패해도 curl 이 URL 을 못 뱉게
    #   --output /dev/null 로 막고 상태 코드만 받는다.
    code="$(timeout "${TELEGRAM_TIMEOUT}" curl \
      --silent --show-error --output /dev/null --write-out '%{http_code}' \
      --max-time "${TELEGRAM_TIMEOUT}" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=$1" \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" 2>/dev/null)"
    if [ "${code}" = "200" ]; then
      exit 0
    fi
    echo "✗ 텔레그램 전송 실패 (HTTP ${code:-없음})" >&2
    exit 1
  )
}

# ── systemd 설치 ────────────────────────────────────────────────────────────────
_install() {
  if ! command -v systemctl > /dev/null 2>&1; then
    echo "✗ systemctl 이 없다 — 이 설치 경로는 리눅스 전용이다." >&2
    exit 1
  fi
  local unit_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
  mkdir -p "${unit_dir}" || exit 1

  # ★게이트와 같은 PATH 를 명시한다. 비로그인 셸은 uv 가 없어 phantom 분류기가 실패하고
  #   그 구간이 커버리지에서 잘려나간다(2026-08-07 실측 8 분 손실).
  cat > "${unit_dir}/${UNIT_NAME}.service" << EOF
[Unit]
Description=QuantBridge soak watch (게이트 1회 호출 + 지문 변화 시 텔레그램)

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PATH=${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
ExecStart=/bin/bash ${SCRIPT_DIR}/soak-watch.sh
EOF

  # ★주기를 30 분에서 바꾸지 마라 — 표본 간격이 곧 C4 판정 대상이다(기본 한계 60 분).
  cat > "${unit_dir}/${UNIT_NAME}.timer" << 'EOF'
[Unit]
Description=QuantBridge soak watch — 30분마다

[Timer]
OnBootSec=2min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload || exit 1

  # ★게이트 타이머를 끈다. 둘이 같이 돌면 `.soak/gate-samples.jsonl` 경합 + phantom 아카이브
  #   이중 생성이 난다(게이트에는 flock 이 없다 — 2026-08-07 실측으로 확인).
  if systemctl --user is-enabled "${GATE_UNIT}.timer" > /dev/null 2>&1; then
    systemctl --user disable --now "${GATE_UNIT}.timer" > /dev/null 2>&1
    echo "  ✓ ${GATE_UNIT}.timer 를 껐다 (watch 가 게이트를 대신 부른다)"
  fi

  systemctl --user enable --now "${UNIT_NAME}.timer" || exit 1
  echo "✓ 설치 완료 — 30분마다 게이트를 부르고 지문 변화만 알린다"
  echo "  ★게이트는 기본(수집) 모드로 불린다 — 표본과 phantom 아카이브는 계속 쌓인다."
  echo "  로그: journalctl --user -u ${UNIT_NAME}.service"
  exit 0
}

_uninstall() {
  if ! command -v systemctl > /dev/null 2>&1; then
    echo "✗ systemctl 이 없다." >&2
    exit 1
  fi
  systemctl --user disable --now "${UNIT_NAME}.timer" > /dev/null 2>&1
  # ★게이트 타이머를 되살린다 — 안 그러면 표본 수집이 통째로 멈춘다.
  systemctl --user enable --now "${GATE_UNIT}.timer" > /dev/null 2>&1 \
    && echo "  ✓ ${GATE_UNIT}.timer 를 되살렸다"
  systemctl --user daemon-reload > /dev/null 2>&1
  echo "✓ 해제 완료 (상태 파일은 남긴다: ${STATE_FILE})"
  exit 0
}

_status() {
  echo "── watch 타이머 ──"
  if command -v systemctl > /dev/null 2>&1; then
    systemctl --user list-timers --all "${UNIT_NAME}.timer" 2>/dev/null | sed -n '2p' \
      || echo "  (조회 실패)"
    printf '  게이트 타이머: '
    systemctl --user is-enabled "${GATE_UNIT}.timer" 2>/dev/null || echo "disabled/없음"
  else
    echo "  (systemctl 없음)"
  fi
  echo "── 마지막 지문 ──"
  if [ -f "${STATE_FILE}" ]; then
    sed 's/^/  /' "${STATE_FILE}"
  else
    echo "  (없음 — 아직 한 번도 안 돌았다)"
  fi
  exit 0
}

case "${MODE}" in
  install) _install ;;
  uninstall) _uninstall ;;
  status) _status ;;
esac

# ── 감시 1 회 ───────────────────────────────────────────────────────────────────
if [ ! -f "${GATE}" ]; then
  echo "✗ 게이트 스크립트가 없다: ${GATE}" >&2
  exit 1
fi

# ★파이프 없음. 명령 치환의 종료 코드를 즉시 보존한다.
OUT="$(timeout "${GATE_TIMEOUT}" bash "${GATE}" 2>&1)"
RC=$?

# ── 지문 추출 ───────────────────────────────────────────────────────────────────
# ★`[✓✗]` 같은 **멀티바이트 괄호 표현식을 쓰지 않는다.** systemd 서비스는 LANG 이 없어 LC_ALL=C
#   로 돌 수 있고, 그러면 괄호 안이 바이트 단위로 쪼개져 매치가 깨진다. 리터럴 문자열 매치는
#   로케일과 무관하게 안전하므로 앵커는 전부 리터럴로 잡는다.
VERDICT="$(printf '%s\n' "${OUT}" | sed -n 's/^판정: \([A-Z][A-Z]*\).*/\1/p' | head -1)"
DISQ="$(printf '%s\n' "${OUT}" | sed -n 's/^.*C3 실격 사건  *\([0-9][0-9]*\)건.*/\1/p' | head -1)"
WINDOWS="$(printf '%s\n' "${OUT}" | sed -n 's/^  귀속 창 \([0-9][0-9]*\)개:.*/\1/p' | head -1)"
C5="$(printf '%s\n' "${OUT}" | sed -n 's/^.*C5 측정 무결  *\(.*\)$/\1/p' | head -1)"
# ★앵커에 **C1 줄의 서식**을 넣지 마라 — 재는 것은 「그 줄이 있나」(= 게이트가 판정까지
#   갔나)이지 「무엇이라고 적혀 있나」가 아니다. 2026-08-11 [BL-701] 이 C1 문턱을
#   「누적 시간」에서 「자격 창 개수」로 바꾸면서 그 줄이 `C1 누적` → `C1 24h 창` 이 됐고,
#   종전 앵커 `C1 누적` 은 **매 실행을 크래시로 오판**하게 돼 있었다. 게다가 이 하네스의
#   픽스처는 옛 서식의 **얼린 캡처**라 그 오판을 못 잡는다 — 초록인 채로 무인 감시가 죽는다.
#   ⇒ 라벨(`C1`)만 잡는다. 문턱을 또 바꿔도 이 줄은 안 깨진다.
#   ★단 **너무 넓어도 안 된다** — 출력 아무 데나 `C1 ` 이 있으면(traceback 본문 등)
#     크래시를 정상으로 읽는다(codex P2). 조건 줄의 **모양**(`✓`/`✗` + `C1 `)까지 요구하고,
#     그 뒤의 서식(누적/창 개수)에는 결합하지 않는다 — 그 둘은 다른 요구다.
C1_ANCHOR="$(printf '%s\n' "${OUT}" | sed -n 's/^  [✓✗] \(C1\) .*/\1/p' | head -1)"

# 크래시 판별 — ★종료 코드로는 FAIL 과 구분되지 않는다. C1 앵커 줄의 유무가 판별자다.
CRASH=0
if [ -z "${C1_ANCHOR}" ] || [ -z "${VERDICT}" ]; then
  CRASH=1
fi

if [ "${CRASH}" = "1" ]; then
  FINGERPRINT="CRASH"
else
  FINGERPRINT="${VERDICT}|${DISQ}|${WINDOWS}|${C5}"
fi

PREV_FP="$(_state_get FINGERPRINT)"
PREV_DISQ="$(_state_get DISQ)"
PREV_HB="$(_state_get HEARTBEAT_DATE)"
TODAY="$(date -u '+%F')"

# ── 알림 판단 ───────────────────────────────────────────────────────────────────
REASONS=""
_add() { REASONS="${REASONS}${REASONS:+$'\n'}· $1"; }

if [ "${CRASH}" = "1" ]; then
  # ★「게이트가 죽었다」는 「소크가 죽었다」와 다른 사건이다. 절대 FAIL 로 보고하지 않는다.
  _add "게이트 크래시 — 판정 불가 (종료 코드 ${RC})"
else
  case "${VERDICT}" in
    FAIL) _add "판정 FAIL — 실격 사건이 났다" ;;
  esac
  if [ -n "${PREV_DISQ}" ] && [ -n "${DISQ}" ] && [ "${DISQ}" -gt "${PREV_DISQ}" ] 2>/dev/null; then
    _add "실격 +$((DISQ - PREV_DISQ)) (${PREV_DISQ} → ${DISQ})"
  fi
  if [ "${WINDOWS}" = "0" ]; then
    _add "활성 귀속 창 0 — 세션이 없다. 세션 0 = 시계 0"
  fi
  case "${C5}" in
    *"=✗"*) _add "C5 측정 무결 위반 — ${C5}" ;;
  esac
fi

CHANGED=0
if [ "${FINGERPRINT}" != "${PREV_FP}" ]; then
  CHANGED=1
  if [ -n "${PREV_FP}" ]; then
    _add "지문 변화: ${PREV_FP} → ${FINGERPRINT}"
  else
    _add "감시 시작 — 첫 지문: ${FINGERPRINT}"
  fi
fi

HEARTBEAT=0
if [ -z "${REASONS}" ] && [ "${PREV_HB}" != "${TODAY}" ]; then
  HEARTBEAT=1
  _add "heartbeat — 이상 없음 (${FINGERPRINT})"
fi

# ── 발화 ────────────────────────────────────────────────────────────────────────
EXIT=0
if [ -n "${REASONS}" ]; then
  if [ "${CRASH}" = "1" ]; then
    HEAD="🔴 [소크] 게이트 크래시"
  elif [ "${VERDICT}" = "FAIL" ]; then
    HEAD="🔴 [소크] FAIL"
  elif [ "${HEARTBEAT}" = "1" ]; then
    HEAD="🟢 [소크] heartbeat"
  else
    HEAD="🟠 [소크] 상태 변화"
  fi

  BODY="${HEAD}
${REASONS}

$(printf '%s\n' "${OUT}" | sed -n '/══ \[BL-003\]/,$p' | head -20)"

  if [ "${MODE}" = "dry-run" ]; then
    echo "── [dry-run] 보냈을 알림 ──"
    printf '%s\n' "${BODY}"
  else
    if ! _notify "${BODY}"; then
      EXIT=1
    fi
  fi
else
  if [ "${MODE}" = "dry-run" ]; then
    echo "── [dry-run] 무발화 (지문 무변화: ${FINGERPRINT}) ──"
  fi
fi

# 상태 갱신. ★heartbeat 날짜는 **어떤 알림이든 실제로 나간 날** 전진시킨다 — heartbeat 의 뜻은
#   「오늘 나한테서 아무 소식도 못 들었다」이지 「오늘 heartbeat 를 안 보냈다」가 아니다.
#   heartbeat 갈래에서만 전진시켰더니 **변화 알림 바로 다음 주기에 heartbeat 가 또 나갔다**
#   (하네스 ①·⑦ 가 잡았다). 전송 실패 시에는 전진시키지 않는다 — 그날 소식이 실제로 0 이므로.
NEW_HB="${PREV_HB}"
if [ -n "${REASONS}" ] && [ "${EXIT}" = "0" ] && [ "${MODE}" != "dry-run" ]; then
  NEW_HB="${TODAY}"
fi
if [ "${MODE}" != "dry-run" ]; then
  _state_put "${FINGERPRINT}" "${DISQ:-0}" "${NEW_HB}"
fi

exit "${EXIT}"
