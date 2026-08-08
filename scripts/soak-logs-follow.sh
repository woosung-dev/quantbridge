#!/usr/bin/env bash
#
# [BL-619] 워커 로그를 컨테이너 수명 밖으로 뺀다.
#
# 왜 있나
#   · [BL-619] 본문은 `.soak/logs/follow.sh`를 nohup으로 띄웠다고 적었지만, 서버에는
#     `.soak/logs`가 아예 없었다(2026-08-08 실측). nohup은 머신 재부팅을 넘지 못하고,
#     살아 있는지 확인하는 주체도 없다.
#   · LESSON-078: 아무도 부르지 않는 검사기는 죽은 줄도 모르고 죽는다. 그래서
#     `--status`가 유닛과 로그를 함께 판정 가능한 형태로 보인다.
#   · 이 로그가 없으면 [BL-619] Trigger(다음 창에서 같은 정지가 관측되면)는 구조적으로
#     충족 불가다. 컨테이너 재생성 뒤 `docker logs`는 이전을 보여 주지 않아 2026-08-07에
#     정지 구간을 한 번 이미 잃었다.
#
# 사용:
#   scripts/soak-logs-follow.sh run          # 포그라운드 follow 루프 (서비스가 호출)
#   scripts/soak-logs-follow.sh --install    # OS별 사용자 서비스 설치·즉시 시작
#   scripts/soak-logs-follow.sh --uninstall  # 서비스 해제 (로그·회전본은 보존)
#   scripts/soak-logs-follow.sh --status     # 유닛·로그 상태
#   scripts/soak-logs-follow.sh -h|--help    # 이 사용법
#
# 종료 코드 (`--status`): 0 = 유닛 활성 / 1 = 유닛 부재·비활성 / 2 = 측정 불가
#   ★UNKNOWN을 PASS로 접지 않는다. 「잴 수 없음」과 「없음」은 다른 상태다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
LABEL="dev.quantbridge.soak-logs-follow"     # launchd Label 이자 systemd unit 이름
QB_OS="$(uname -s)"
# soak-gate.sh:32-36과 같은 규칙이다. 이것은 서비스 자신의 stdout/stderr 보관처다.
if [ "${QB_OS}" = "Darwin" ]; then
  LOGDIR="$HOME/Library/Logs/quantbridge"
else
  LOGDIR="${XDG_STATE_HOME:-$HOME/.local/state}/quantbridge"
fi
WORKER_CONTAINER="${QB_WORKER_CONTAINER:-quantbridge-worker}"
LOG_DIR="${ROOT}/.soak/logs"
LOG_FILE="${LOG_DIR}/worker-follow.log"
MAX_BYTES="${QB_FOLLOW_MAX_BYTES:-33554432}"
KEEP="${QB_FOLLOW_KEEP:-3}"
RECONNECT_SEC="${QB_FOLLOW_RECONNECT_SEC:-5}"
CURSOR_FILE="${LOG_DIR}/.follow-cursor"

# 외부 운영 명령은 멈추면 안 된다. GNU timeout이 없는 macOS에서는 같은 제한을 Perl
# 감시자로 구현한다. 어느 것도 없으면 명령을 무기한 실행하지 않고 실패로 돌린다.
_with_timeout() { # _with_timeout <초> <명령> [인자...]
  local seconds="$1"
  shift

  if command -v timeout > /dev/null 2>&1; then
    timeout "${seconds}" "$@"
  elif command -v gtimeout > /dev/null 2>&1; then
    gtimeout "${seconds}" "$@"
  elif command -v perl > /dev/null 2>&1; then
    perl -e '
      my $seconds = shift @ARGV;
      my $pid = fork();
      exit 125 if !defined $pid;
      if ($pid == 0) {
        exec @ARGV;
        exit 127;
      }
      $SIG{ALRM} = sub {
        kill "TERM", $pid;
        select undef, undef, undef, 0.2;
        kill "KILL", $pid;
        waitpid($pid, 0);
        exit 124;
      };
      alarm $seconds;
      waitpid($pid, 0);
      alarm 0;
      exit($? >> 8);
    ' "${seconds}" "$@"
  else
    echo "✗ timeout 명령이 없어 외부 명령을 안전하게 실행할 수 없다." >&2
    return 125
  fi
}

_now() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

_is_timestamp() { # _is_timestamp <RFC3339 Z 시각>
  [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z$ ]]
}

_validate_run_config() {
  case "${MAX_BYTES}" in
    ''|*[!0-9]*)
      echo "✗ QB_FOLLOW_MAX_BYTES 는 0 이상의 정수여야 한다: ${MAX_BYTES}" >&2
      return 1
      ;;
  esac
  case "${KEEP}" in
    ''|0|*[!0-9]*)
      echo "✗ QB_FOLLOW_KEEP 는 1 이상의 정수여야 한다: ${KEEP}" >&2
      return 1
      ;;
  esac
}

_append_log() { # _append_log <한 줄>
  # ★회전 뒤에도 새 본체에 쓰려면 줄마다 다시 연다. `docker ... >> file` 한 번이면
  # mv된 inode로 계속 써 회전이 무의미해진다. 워커 로그는 8시간 5,022줄(약 10줄/분)이라
  # 이 비용은 정지 구간을 잃는 비용보다 작다.
  printf '%s\n' "$1" >> "${LOG_FILE}"
}

_write_cursor() { # _write_cursor <RFC3339 Z 시각>
  _is_timestamp "$1" || return 1
  printf '%s\n' "$1" > "${CURSOR_FILE}"
}

_valid_cursor() {
  local cursor=""
  [ -f "${CURSOR_FILE}" ] || return 0
  IFS= read -r cursor < "${CURSOR_FILE}" || true
  if _is_timestamp "${cursor}"; then
    printf '%s\n' "${cursor}"
  fi
}

_rotate_if_needed() {
  local size
  local index

  [ -f "${LOG_FILE}" ] || return 0
  size="$(wc -c < "${LOG_FILE}")" || {
    echo "✗ 로그 크기를 읽지 못했다: ${LOG_FILE}" >&2
    return 1
  }
  size="${size//[[:space:]]/}"
  case "${size}" in
    ''|*[!0-9]*)
      echo "✗ 로그 크기가 정수가 아니다: ${LOG_FILE}" >&2
      return 1
      ;;
  esac
  [ "${size}" -ge "${MAX_BYTES}" ] || return 0

  rm -f "${LOG_FILE}.${KEEP}" || return 1
  for ((index = KEEP - 1; index >= 1; index--)); do
    if [ -f "${LOG_FILE}.${index}" ]; then
      mv "${LOG_FILE}.${index}" "${LOG_FILE}.$((index + 1))" || return 1
    fi
  done
  mv "${LOG_FILE}" "${LOG_FILE}.1" || return 1
  _append_log "=== [follow] rotated $(_now) (${size} bytes) ==="
}

_consume_logs() {
  local line
  local first_field
  local last_timestamp=""
  local line_count=0

  while IFS= read -r line || [ -n "${line}" ]; do
    _append_log "${line}" || return 1
    first_field="${line%% *}"
    if _is_timestamp "${first_field}"; then
      last_timestamp="${first_field}"
    fi

    line_count=$((line_count + 1))
    if [ "${line_count}" -ge 100 ]; then
      _rotate_if_needed || return 1
      [ -z "${last_timestamp}" ] || _write_cursor "${last_timestamp}" || return 1
      line_count=0
    fi
  done

  [ -z "${last_timestamp}" ] || _write_cursor "${last_timestamp}"
}

_run() {
  local cursor
  local -a docker_args

  _validate_run_config || exit 1
  mkdir -p "${LOG_DIR}" || exit 1

  while true; do
    _rotate_if_needed || exit 1
    _append_log "=== [follow] attach $(_now) container=${WORKER_CONTAINER} ===" || exit 1

    docker_args=(logs -f --timestamps)
    cursor="$(_valid_cursor)"
    # 같은 컨테이너를 `docker restart` 하면 logs가 처음부터 다시 나온다. 마지막으로 기록한
    # RFC3339 시각만 `--since`로 넘겨 중복이 회전 상한을 잡아먹고 부검에서 정지 구간이 두 번
    # 세어지는 일을 막는다. 쓰레기 커서는 docker를 5초 실패 루프에 넣으므로 정규식 통과분만 쓴다.
    if [ -n "${cursor}" ]; then
      docker_args+=(--since "${cursor}")
    fi

    # ★상주 목적의 `docker logs -f`만 timeout 예외다. 나머지 docker/systemctl/launchctl 호출은
    # 모두 제한 시간이 있다. 파이프의 소비자는 줄마다 LOG_FILE을 다시 열어 회전 뒤 새 본체에 쓴다.
    docker "${docker_args[@]}" "${WORKER_CONTAINER}" 2>&1 | _consume_logs || true
    _append_log "=== [follow] detached $(_now) ===" || exit 1
    sleep "${RECONNECT_SEC}"
  done
}

_warn_docker() {
  if ! command -v docker > /dev/null 2>&1; then
    echo "⚠ docker 가 PATH에 없다 — 소크가 꺼져 있어도 설치는 유지한다." >&2
  elif ! _with_timeout 10 docker container inspect "${WORKER_CONTAINER}" > /dev/null 2>&1; then
    echo "⚠ 워커 컨테이너가 아직 없다: ${WORKER_CONTAINER} — 소크 기동 뒤 재접속한다." >&2
  fi
}

_install_systemd() {
  local paths="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

  if ! command -v systemctl > /dev/null 2>&1; then
    echo "✗ systemctl 이 없다 — 이 설치 경로는 리눅스 전용이다." >&2
    exit 1
  fi
  mkdir -p "${unit_dir}" || exit 1
  cat > "${unit_dir}/${LABEL}.service" <<UNIT_EOF
[Unit]
Description=QuantBridge soak worker log follow ([BL-619] 정지 구간 로그 보존)

[Service]
Type=simple
WorkingDirectory=${ROOT}
Environment=PATH=${paths}
ExecStart=/bin/bash ${ROOT}/scripts/soak-logs-follow.sh run
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
UNIT_EOF

  # user manager는 system docker.service와 순서를 맞추지 못해 After=가 무언의 no-op다.
  # Restart=always와 run 내부 재접속 루프가 Docker 기동 지연을 대신 흡수한다.
  _with_timeout 15 systemctl --user daemon-reload \
    || { echo "✗ systemctl --user daemon-reload 실패" >&2; exit 1; }
  _with_timeout 15 systemctl --user enable --now "${LABEL}.service" \
    || { echo "✗ service enable 실패" >&2; exit 1; }

  # lingering이 없으면 SSH가 끊길 때 user manager와 서비스가 같이 죽어 nohup과 다를 바 없다.
  local linger=""
  linger="$(_with_timeout 10 loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null)" || linger=""
  if ! printf '%s\n' "${linger}" | grep -qi '^yes$'; then
    if ! _with_timeout 10 loginctl enable-linger "$(id -un)" 2>/dev/null; then
      echo "⚠ lingering 을 못 켰다 — SSH 를 끊으면 service 가 멈춘다." >&2
      echo "  직접 실행해라: sudo loginctl enable-linger $(id -un)" >&2
    fi
  fi

  # gate/watch와 자원을 다투지 않는 독립 로그 보존기라 남의 유닛을 끄지 않는다.
  _warn_docker
  echo "✓ 설치 완료 — 워커 로그를 컨테이너 밖에 연속 보존한다 (systemd user service)"
  echo "  로그: journalctl --user -u ${LABEL}.service"
  exit 0
}

_uninstall_systemd() {
  local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

  _with_timeout 15 systemctl --user disable --now "${LABEL}.service" > /dev/null 2>&1 || true
  rm -f "${unit_dir}/${LABEL}.service"
  _with_timeout 15 systemctl --user daemon-reload > /dev/null 2>&1 || true
  echo "✓ 해제 완료 (로그·회전본은 남긴다: ${LOG_DIR})"
  exit 0
}

_install() {
  [ "${QB_OS}" != "Darwin" ] && _install_systemd

  # launchd PATH를 명시하지 않으면 docker를 못 찾아 조용히 실패한다.
  local paths="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  local plist="$HOME/Library/LaunchAgents/${LABEL}.plist"
  mkdir -p "$HOME/Library/LaunchAgents" "${LOGDIR}" || exit 1
  cat > "${plist}" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${ROOT}/scripts/soak-logs-follow.sh</string>
    <string>run</string>
  </array>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>${paths}</string></dict>
  <key>StandardOutPath</key><string>${LOGDIR}/soak-logs-follow.out.log</string>
  <key>StandardErrorPath</key><string>${LOGDIR}/soak-logs-follow.err.log</string>
  <key>WorkingDirectory</key><string>${ROOT}</string>
</dict>
</plist>
PLIST_EOF

  _with_timeout 15 launchctl unload "${plist}" > /dev/null 2>&1 || true
  _with_timeout 15 launchctl load "${plist}" || { echo "✗ launchctl load 실패" >&2; exit 1; }
  _warn_docker
  echo "✓ 설치 완료 — 워커 로그를 컨테이너 밖에 연속 보존한다 (launchd LaunchAgent)"
  exit 0
}

_uninstall() {
  [ "${QB_OS}" != "Darwin" ] && _uninstall_systemd

  local plist="$HOME/Library/LaunchAgents/${LABEL}.plist"
  _with_timeout 15 launchctl unload "${plist}" > /dev/null 2>&1 || true
  rm -f "${plist}"
  echo "✓ 해제 완료 (로그·회전본은 남긴다: ${LOG_DIR})"
  exit 0
}

_status_systemd() {
  local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  local result=1

  if ! command -v systemctl > /dev/null 2>&1; then
    echo "유닛: 측정 불가"
    return 2
  fi
  _with_timeout 10 systemctl --user is-active --quiet "${LABEL}.service" > /dev/null 2>&1
  result=$?
  case "${result}" in
    0)
      echo "유닛: 활성"
      return 0
      ;;
    3|4)
      if [ -f "${unit_dir}/${LABEL}.service" ]; then
        echo "유닛: 등록됨 · 비활성"
      else
        echo "유닛: 등록 안 됨"
      fi
      return 1
      ;;
    *)
      echo "유닛: 측정 불가"
      return 2
      ;;
  esac
}

_status_launchd() {
  local plist="$HOME/Library/LaunchAgents/${LABEL}.plist"
  local output
  local result

  if ! command -v launchctl > /dev/null 2>&1; then
    echo "유닛: 측정 불가"
    return 2
  fi
  output="$(_with_timeout 10 launchctl print "gui/${UID}/${LABEL}" 2>/dev/null)"
  result=$?
  if [ "${result}" -eq 0 ]; then
    if [[ "${output}" == *"state = running"* ]]; then
      echo "유닛: 활성"
      return 0
    fi
    echo "유닛: 등록됨 · 비활성"
    return 1
  fi
  if [ "${result}" -eq 113 ]; then
    if [ -f "${plist}" ]; then
      echo "유닛: 등록됨 · 비활성"
    else
      echo "유닛: 등록 안 됨"
    fi
    return 1
  fi
  echo "유닛: 측정 불가"
  return 2
}

_last_log_timestamp() {
  local line
  local first_field
  local last_timestamp=""

  [ -f "${LOG_FILE}" ] || return 0
  while IFS= read -r line || [ -n "${line}" ]; do
    first_field="${line%% *}"
    if _is_timestamp "${first_field}"; then
      last_timestamp="${first_field}"
    fi
  done < "${LOG_FILE}"
  printf '%s\n' "${last_timestamp}"
}

_status() {
  local unit_result
  local size=0
  local rotation_count=0
  local index
  local last_timestamp

  echo "── 유닛 ──"
  if [ "${QB_OS}" = "Darwin" ]; then
    _status_launchd
  else
    _status_systemd
  fi
  unit_result=$?

  if [ -f "${LOG_FILE}" ]; then
    size="$(wc -c < "${LOG_FILE}")" || size=0
    size="${size//[[:space:]]/}"
    case "${size}" in
      ''|*[!0-9]*) size=0 ;;
    esac
  fi
  for ((index = 1; index <= KEEP; index++)); do
    [ -f "${LOG_FILE}.${index}" ] && rotation_count=$((rotation_count + 1))
  done
  last_timestamp="$(_last_log_timestamp)"
  [ -n "${last_timestamp}" ] || last_timestamp="(없음)"

  echo "── 로그 ──"
  echo "로그: ${LOG_FILE}"
  echo "크기: ${size}바이트 · 회전본 ${rotation_count}개"
  echo "마지막 줄 시각: ${last_timestamp}"
  return "${unit_result}"
}

_usage() {
  sed -n '3,24p' "$0"
}

case "${1:-}" in
  run)
    [ "$#" -eq 1 ] || { echo "run 은 인자를 받지 않는다. (--help)" >&2; exit 1; }
    _run
    ;;
  --install)
    [ "$#" -eq 1 ] || { echo "--install 은 인자를 받지 않는다. (--help)" >&2; exit 1; }
    _install
    ;;
  --uninstall)
    [ "$#" -eq 1 ] || { echo "--uninstall 은 인자를 받지 않는다. (--help)" >&2; exit 1; }
    _uninstall
    ;;
  --status)
    [ "$#" -eq 1 ] || { echo "--status 는 인자를 받지 않는다. (--help)" >&2; exit 1; }
    _status
    exit $?
    ;;
  -h|--help)
    [ "$#" -eq 1 ] || { echo "--help 는 인자를 받지 않는다." >&2; exit 1; }
    _usage
    exit 0
    ;;
  '')
    _usage >&2
    exit 1
    ;;
  *)
    echo "알 수 없는 인자: $1  (--help)" >&2
    exit 1
    ;;
esac
