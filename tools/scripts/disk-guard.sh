#!/usr/bin/env bash
#
# 디스크 사용률 경보 — 임계를 넘으면 텔레그램. **판정은 `df` 한 줄이 전부다.** ([BL-768])
#
# 왜 있나
#   2026-08-14T06:04:11Z 로컬 Docker VM 이 94% 에서 Redis AOF 쓰기에 실패했고 celery 가
#   `Unrecoverable error` 로 **통째 정지**했다([BL-736]). 그 사고는 로컬에서 났지만 서버도
#   구조가 같다 — `quantbridge-redis` 는 `appendonly=yes` 이고(2026-08-16 실측) 소크 스택·
#   백업 덤프·다른 앱 셋이 **디스크 한 벌(/dev/sda1 97G)을 공유**한다. 서버에서 같은 일이 나면
#   24시간 안정성 창이 통째로 날아간다.
#   ★그리고 이 회차가 [BL-767] 로 **백업 파일을 쌓기 시작한다** — 감시 없이 쓰는 쪽만 늘리지 않는다.
#
# 사용:
#   tools/scripts/disk-guard.sh              # 1 회 점검 (타이머가 부르는 형태)
#   tools/scripts/disk-guard.sh --dry-run    # 알림은 쏘지 않고 판단만 출력
#   tools/scripts/disk-guard.sh --status     # 현재 사용률 · 마지막 상태 · **설치본 신선도**
#   tools/scripts/disk-guard.sh --install    # systemd user timer (매시 15분)
#   tools/scripts/disk-guard.sh --uninstall
#
# 종료 코드: 0 = 점검 정상 수행 / 1 = **감시자 자신이 실패**(알림 전송 실패 · df 판독 실패)
#   ★디스크가 임계를 넘었다는 사실은 종료 코드로 새어나오지 않는다 — 알림이 나갔으면 0 이다.
#     그래야 systemd 의 빨간불이 「경보가 깨졌다」 하나만 뜻한다(soak-watch 와 같은 규약).
#
# env:
#   QB_DISK_TARGET     점검 대상 경로. 기본 `/`. 서버는 단일 파일시스템이라 이 하나로 충분하다.
#   QB_DISK_WARN_PCT   임계(%). 기본 80.
#   QB_DISK_STATE      상태 파일 경로.
#   QB_SOAK_ENV_FILE   텔레그램 크레덴셜 파일(soak-watch 와 **같은 이름을 쓴다** — 서버에 파일이
#                      한 벌뿐인데 이름을 둘로 만들면 한쪽만 고쳐진다).
#   QB_DISK_NOTIFY_CMD 주입 seam. 하네스가 실제 텔레그램을 쏘지 않게 하는 유일한 경로.
#
# ★설계 근거
#   · **소크 감시와 분리한다.** soak-watch 에 얹으면 소크가 내려간 순간 디스크 감시도 사라진다.
#     디스크는 소크보다 오래 살아야 하는 축이다.
#   · **알림을 먼저 쏘고 상태를 나중에 저장한다.** 디스크가 꽉 차면 상태 파일 쓰기부터 실패한다 —
#     저장을 먼저 하면 정작 알려야 할 그 순간에 알림 없이 죽는다.
#   · **OK 가 「이어질」 때 조용하다.** heartbeat 를 여기서 또 보내지 않는다(soak-watch 가 이미
#     매일 보낸다). WARN 이 이어지는 동안만 하루 1 회 재고지한다 — 계속 쏘면 사람이 무시하게 된다.
#     ★단 **WARN→OK 전이는 쏜다**(회복 알림). 경보만 받고 회복을 못 받으면 사람은 아직 위험한
#     줄 알고, 다음 경보를 「아까 그거」로 읽는다. 즉 「OK = 무조건 무발화」가 아니다 —
#     발화 조건은 **상태 전이**이지 상태값이 아니다(2026-08-16 codex P2 · 기각. 하네스 ⑥⑦ 이
#     이 둘을 각각 잰다: 전이는 쏘고, 유지는 안 쏜다).
#   · **동시 실행 잠금은 두지 않았다.** 두 인스턴스를 손으로 나란히 띄우면 둘 다 전이 전 상태를
#     읽어 알림이 2 번 나간다(2026-08-16 codex P2 실측). systemd 는 같은 유닛의 중복 기동을
#     막으므로 타이머 경로에서는 발생하지 않고, 대가(락 파일 · 스테일 락 회수)가 알림 1 건보다
#     크다. ★사람이 손으로 돌릴 때만 겹칠 수 있다는 것을 알고 있어라.
#   · **`df -Pk`.** `-P` 는 POSIX 한 줄 출력을 보장해 장치명이 길어도 줄이 안 쪼개지고,
#     `-k` 는 단위를 1K 로 못박는다(macOS 의 `df -P` 기본은 512-byte 블록이라 값이 2 배로 보인다).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

if [ "$(uname -s)" = "Darwin" ]; then
  _DEFAULT_LOGDIR="${HOME}/Library/Logs/quantbridge"
else
  _DEFAULT_LOGDIR="${XDG_STATE_HOME:-${HOME}/.local/state}/quantbridge"
fi

TARGET="${QB_DISK_TARGET:-/}"
WARN_PCT="${QB_DISK_WARN_PCT:-80}"
STATE_FILE="${QB_DISK_STATE:-${_DEFAULT_LOGDIR}/disk-guard.state}"
ENV_FILE="${QB_SOAK_ENV_FILE:-${ROOT}/apps/api/.env.local}"
TELEGRAM_TIMEOUT="${QB_DISK_TELEGRAM_TIMEOUT:-15}"

UNIT_NAME="dev.quantbridge.disk-guard"
ALARM_UNIT="dev.quantbridge.disk-guard-alarm"

MODE="check"
while [ $# -gt 0 ]; do
  case "$1" in
    --install) MODE="install" ;;
    --uninstall) MODE="uninstall" ;;
    --status) MODE="status" ;;
    --dry-run) MODE="dry-run" ;;
    -h | --help)
      sed -n '2,45p' "$0"
      exit 0
      ;;
    *)
      echo "알 수 없는 인자: $1  (--help)" >&2
      exit 1
      ;;
  esac
  shift
done

# ── 알림 ────────────────────────────────────────────────────────────────────────
NOTIFY_LIB="${QB_NOTIFY_LIB:-${SCRIPT_DIR}/lib/notify-telegram.sh}"
if [ ! -f "${NOTIFY_LIB}" ]; then
  echo "✗ 알림 라이브러리가 없다: ${NOTIFY_LIB}" >&2
  exit 1
fi
# shellcheck source=tools/scripts/lib/notify-telegram.sh
. "${NOTIFY_LIB}"

_notify() { # _notify <본문>  → 0 = 보냄 / 1 = 실패
  QB_NOTIFY_CMD="${QB_DISK_NOTIFY_CMD:-}" \
    QB_NOTIFY_ENV_FILE="${ENV_FILE}" \
    QB_NOTIFY_TIMEOUT="${TELEGRAM_TIMEOUT}" \
    qb_notify_telegram "$1"
}

# ── 상태 파일 (key=value, 소싱하지 않는다) ──────────────────────────────────────
# ★`.` 로 소싱하지 않는다 — 상태 파일이 예상 밖 내용이면 `command not found` 로 죽는다
#   (`.soak/session` 이 맨 uuid 로 쓰여 그렇게 죽어 있던 것을 2026-08-07 에 실측했다).
_state_get() { # _state_get <key> → stdout (없으면 빈 문자열)
  [ -f "${STATE_FILE}" ] || return 0
  sed -n "s/^$1=//p" "${STATE_FILE}" | head -1
}

_state_put() { # _state_put <level> <notified_date>
  mkdir -p "$(dirname "${STATE_FILE}")" || return 1
  {
    printf 'LEVEL=%s\n' "$1"
    printf 'NOTIFIED_DATE=%s\n' "$2"
  } > "${STATE_FILE}"
}

# ── 판독 ────────────────────────────────────────────────────────────────────────
# `df -Pk <경로>` 2 행: Filesystem 1024-blocks Used Available Capacity Mounted-on
# → stdout: "<사용률숫자> <여유KB> <파일시스템> <마운트지점>"  (판독 실패 시 빈 문자열 + rc=1)
_read_disk() {
  local line
  line="$(df -Pk "${TARGET}" 2> /dev/null | awk 'NR==2')" || return 1
  [ -n "${line}" ] || return 1
  printf '%s\n' "${line}" | awk '
    {
      pct = $5; sub(/%$/, "", pct)
      if (pct !~ /^[0-9]+$/) exit 1
      print pct, $4, $1, $6
    }
  '
}

_human_gb() { # <KB> → "12.3G"
  awk -v kb="$1" 'BEGIN { printf "%.1fG", kb / 1048576 }'
}

# ── systemd 설치 ────────────────────────────────────────────────────────────────
_install() {
  if ! command -v systemctl > /dev/null 2>&1; then
    echo "✗ systemctl 이 없다 — 이 설치 경로는 리눅스 전용이다." >&2
    exit 1
  fi
  local unit_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
  mkdir -p "${unit_dir}" || exit 1

  cat > "${unit_dir}/${UNIT_NAME}.service" << EOF
[Unit]
Description=QuantBridge 디스크 사용률 경보 (${TARGET} ≥ ${WARN_PCT}%)
OnFailure=${ALARM_UNIT}.service

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PATH=${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
Environment=QB_DISK_TARGET=${TARGET}
Environment=QB_DISK_WARN_PCT=${WARN_PCT}
ExecStart=/bin/bash ${SCRIPT_DIR}/disk-guard.sh
EOF

  # ★감시자 자신의 죽음을 알리는 축 — soak-watch 와 같은 관용구(`soak-watch.sh:167-194`).
  #   ★★**`$$` 로 이스케이프해야 한다.** systemd 는 `ExecStart` 의 `${VAR}` 를 자기 환경으로
  #   **먼저 확장**하고 미정의 변수는 빈 문자열로 만든다 — 작은따옴표도 막지 못한다. 그러면 URL 이
  #   `…/bot/sendMessage` 가 되어 텔레그램이 **404** 를 준다(2026-08-15 실측).
  #   ★`--fail` 이 있어야 한다 — 없으면 텔레그램이 400 을 줘도 curl 은 rc=0 이고 유닛은
  #   `Finished` 로 남아 「돌았다」와 「도착했다」를 구분할 수 없다.
  #   ★`--show-error` 는 뺀다 — 실패 메시지에 URL(경로에 토큰이 있다)이 실릴 수 있다.
  case "${ENV_FILE}" in
    *"'"*)
      echo "✗ env 파일 경로에 작은따옴표가 있어 유닛을 안전하게 생성할 수 없다: ${ENV_FILE}" >&2
      exit 1
      ;;
  esac
  cat > "${unit_dir}/${ALARM_UNIT}.service" << EOF
[Unit]
Description=QuantBridge 디스크 경보 실패 알림 (감시자 자신이 죽었을 때)

[Service]
Type=oneshot
Environment=PATH=${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
ExecStart=/bin/bash -c 'set -a; . "${ENV_FILE}"; set +a; exec curl --silent --fail --output /dev/null --max-time 15 --data-urlencode "chat_id=\$\${TELEGRAM_CHAT_ID}" --data-urlencode "text=🔴 disk-guard.service 가 실패했다 — 디스크 경보가 끊겼다. journalctl --user -u ${UNIT_NAME}.service -n 20" "https://api.telegram.org/bot\$\${TELEGRAM_BOT_TOKEN}/sendMessage"'
EOF

  # ★`OnCalendar` 다 — `OnUnitActiveSec` 은 **마지막 활성화 기준**이라 사람이 한 번 손으로
  #   돌리면 위상이 밀린다(2026-08-15 [BL-737] 실측: 표본 간격이 53 분까지 벌어졌다).
  #   ★매시 **15 분**에 둔다 — soak-watch 가 00·30 분을 쓰므로 겹치지 않게 어긋낸다.
  cat > "${unit_dir}/${UNIT_NAME}.timer" << 'EOF'
[Unit]
Description=QuantBridge 디스크 경보 — 매시 15분 (벽시계 고정)

[Timer]
OnBootSec=3min
OnCalendar=*:15
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload || exit 1
  systemctl --user enable --now "${UNIT_NAME}.timer" || exit 1
  echo "✓ 설치 완료 — 매시 15분에 ${TARGET} 를 재고 ${WARN_PCT}% 이상이면 알린다"
  echo "  ★OK 일 때는 조용하다. WARN 이 이어지면 하루 1회만 재고지한다."
  echo "  ★감시자 자신이 실패하면 ${ALARM_UNIT}.service 가 텔레그램을 쏜다."
  echo "  로그: journalctl --user -u ${UNIT_NAME}.service"
  exit 0
}

_uninstall() {
  if ! command -v systemctl > /dev/null 2>&1; then
    echo "✗ systemctl 이 없다." >&2
    exit 1
  fi
  systemctl --user disable --now "${UNIT_NAME}.timer" > /dev/null 2>&1
  rm -f "${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user/${ALARM_UNIT}.service"
  systemctl --user daemon-reload > /dev/null 2>&1
  echo "✓ 해제 완료 (상태 파일은 남긴다: ${STATE_FILE})"
  exit 0
}

# ── 설치본 신선도 ───────────────────────────────────────────────────────────────
# ★「타이머가 waiting」은 건강 신호가 아니다. 2026-08-13 재배치([ADR-029]) 후 soak-watch 는
#   **41 시간 동안** 타이머는 정상 waiting 인 채 서비스만 rc=127 로 죽었다([BL-737]).
#   유닛에는 **설치 시점의 절대경로가 구워진다** — 재는 것은 그것이 지금 이 파일인가다.
_check_freshness() { # → 0 = 최신 / 1 = 낡음·부재. 진단은 stdout.
  local unit_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
  local want="${SCRIPT_DIR}/disk-guard.sh"
  local f="${unit_dir}/${UNIT_NAME}.service"
  local got af aenv rc=0

  if [ ! -f "${f}" ]; then
    echo "  ✗ 설치된 유닛이 없다 (${f})"
    return 1
  fi
  got="$(sed -n 's|^ExecStart=/bin/bash \(.*\)$|\1|p' "${f}" | head -1)"
  if [ -z "${got}" ]; then
    echo "  ✗ ExecStart 를 파싱할 수 없다 (${f})"
    return 1
  fi
  if [ ! -f "${got}" ]; then
    echo "  ✗ ExecStart 가 없는 파일을 가리킨다 — 이 유닛은 rc=127 로 죽는다: ${got}"
    rc=1
  fi
  if [ "${got}" != "${want}" ]; then
    echo "  ✗ ExecStart 가 이 파일이 아니다 — 재설치해라 (--install)"
    echo "      설치본: ${got}"
    echo "      현재본: ${want}"
    rc=1
  fi
  [ "${rc}" -eq 0 ] && echo "  ✓ ExecStart = ${got}"

  af="${unit_dir}/${ALARM_UNIT}.service"
  if [ ! -f "${af}" ]; then
    echo "  ✗ 실패 알림 유닛이 없다 (${ALARM_UNIT}.service) — 감시자가 죽어도 조용하다"
    return 1
  fi
  aenv="$(sed -n 's|^ExecStart=.*set -a; \. "\([^"]*\)".*$|\1|p' "${af}" | head -1)"
  if [ -z "${aenv}" ] || [ ! -f "${aenv}" ]; then
    echo "  ✗ 실패 알림 유닛의 env 파일이 없다: ${aenv:-(파싱 실패)}"
    return 1
  fi
  echo "  ✓ 실패 알림 유닛 · env = ${aenv}"
  return "${rc}"
}

_status() {
  local fresh_rc=0 read_out
  echo "── 타이머 ──"
  if command -v systemctl > /dev/null 2>&1; then
    systemctl --user list-timers --all "${UNIT_NAME}.timer" 2> /dev/null | sed -n '2p' \
      || echo "  (조회 실패)"
  else
    echo "  (systemctl 없음)"
  fi
  echo "── 현재 사용률 ──"
  read_out="$(_read_disk)"
  if [ -z "${read_out}" ]; then
    echo "  ✗ df 판독 실패: ${TARGET}"
    fresh_rc=1
  else
    set -- ${read_out}
    printf '  %s%% (여유 %s) · %s → %s · 임계 %s%%\n' "$1" "$(_human_gb "$2")" "$3" "$4" "${WARN_PCT}"
  fi
  echo "── 설치본 신선도 ──"
  _check_freshness || fresh_rc=1
  echo "── 마지막 상태 ──"
  if [ -f "${STATE_FILE}" ]; then
    sed 's/^/  /' "${STATE_FILE}"
  else
    echo "  (없음 — 아직 한 번도 안 돌았다)"
  fi
  exit "${fresh_rc}"
}

case "${MODE}" in
  install) _install ;;
  uninstall) _uninstall ;;
  status) _status ;;
esac

# ── 점검 1 회 ───────────────────────────────────────────────────────────────────
if ! printf '%s' "${WARN_PCT}" | grep -Eq '^[0-9]+$'; then
  echo "✗ QB_DISK_WARN_PCT 가 숫자가 아니다: ${WARN_PCT}" >&2
  exit 1
fi

READ_OUT="$(_read_disk)"
if [ -z "${READ_OUT}" ]; then
  echo "✗ df 판독 실패 — 경로가 없거나 출력 형식이 예상과 다르다: ${TARGET}" >&2
  exit 1
fi
set -- ${READ_OUT}
PCT="$1"
AVAIL_KB="$2"
FS="$3"
MOUNT="$4"

if [ "${PCT}" -ge "${WARN_PCT}" ]; then
  LEVEL="WARN"
else
  LEVEL="OK"
fi

PREV_LEVEL="$(_state_get LEVEL)"
PREV_DATE="$(_state_get NOTIFIED_DATE)"
TODAY="$(date -u '+%F')"

# ── 발화 판단 ───────────────────────────────────────────────────────────────────
# OK 유지 = 무발화. 전이(OK↔WARN)는 즉시. WARN 유지는 하루 1 회 재고지.
BODY=""
if [ "${LEVEL}" = "WARN" ]; then
  if [ "${PREV_LEVEL}" != "WARN" ]; then
    BODY="🟠 [디스크] ${MOUNT} ${PCT}% — 임계 ${WARN_PCT}% 를 넘었다
· 여유 $(_human_gb "${AVAIL_KB}") · ${FS}
· 디스크가 차면 Redis AOF 쓰기가 실패하고 celery 가 통째로 멈춘다([BL-736] 실사고).
· 회수: docker system prune / 오래된 백업 덤프 / 로그"
  elif [ "${PREV_DATE}" != "${TODAY}" ]; then
    BODY="🟠 [디스크] ${MOUNT} ${PCT}% — 임계 초과가 이어지고 있다 (재고지)
· 여유 $(_human_gb "${AVAIL_KB}") · ${FS}"
  fi
elif [ "${PREV_LEVEL}" = "WARN" ]; then
  BODY="🟢 [디스크] ${MOUNT} ${PCT}% — 임계 ${WARN_PCT}% 아래로 회복
· 여유 $(_human_gb "${AVAIL_KB}") · ${FS}"
fi

EXIT=0
NEW_DATE="${PREV_DATE}"

if [ -n "${BODY}" ]; then
  if [ "${MODE}" = "dry-run" ]; then
    echo "── [dry-run] 보냈을 알림 ──"
    printf '%s\n' "${BODY}"
  else
    # ★알림을 **먼저** 쏜다. 상태 파일 쓰기는 디스크가 꽉 차면 실패하는 축이라
    #   순서를 뒤집으면 정작 알려야 할 순간에 조용히 죽는다.
    if _notify "${BODY}"; then
      NEW_DATE="${TODAY}"
    else
      EXIT=1
    fi
  fi
else
  if [ "${MODE}" = "dry-run" ]; then
    echo "── [dry-run] 무발화 (${LEVEL} ${PCT}% · 임계 ${WARN_PCT}%) ──"
  fi
fi

if [ "${MODE}" != "dry-run" ]; then
  _state_put "${LEVEL}" "${NEW_DATE}" || EXIT=1
fi

exit "${EXIT}"
