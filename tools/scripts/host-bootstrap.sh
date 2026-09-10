#!/usr/bin/env bash
#
# 호스트 전용 설정 2건을 레포가 갖는다 — daemon.json 로그 상한 · journald 상한 (ADR-043, 2026-09-10)
#
# 왜 있나
#   2026-08-30 감사에서 `/etc/docker/daemon.json`(10m×3)이 **호스트에만** 있고 레포·런북 어디에도 없었다.
#   2026-09-10 재감사에서 journald 가 1.2G 인데 상한이 없었다(기본 = fs 10% ≈ 10G). 서버를 다시 세우면
#   둘 다 조용히 사라진다. 「지우고 다시 만들 수 있는가」가 기준이다 — 1대여도 마찬가지다.
#
# 사용:
#   sudo tools/scripts/host-bootstrap.sh --install   # 두 파일을 쓰고 docker·journald 를 다시 읽힌다
#        tools/scripts/host-bootstrap.sh --status    # 드리프트 — 파일이 레포가 기대하는 내용과 같은가 (rc 1 = 다르다)
#   ★`--install` 은 root 다. 배포 승인 축이다 — 자동 배포(deploy.sh)는 이것을 부르지 않는다.
#   ★daemon.json 을 바꾸면 **기존 컨테이너는 재생성해야** 적용된다(로그 드라이버는 생성 시 고정).
#     compose `x-logging` 이 같은 값을 갖고 있어 우리 컨테이너는 이미 상한이 있다 — 남의 컨테이너는 아니다.
#
# 종료 코드: 0 = 정상 / 1 = 드리프트 있음(--status) 또는 쓰기 실패(--install)

set -uo pipefail

DAEMON_JSON="${QB_HOST_DAEMON_JSON:-/etc/docker/daemon.json}"
JOURNALD_CONF="${QB_HOST_JOURNALD_CONF:-/etc/systemd/journald.conf.d/quantbridge.conf}"

_expected_daemon() {
  cat << 'EOF2'
{
  "log-driver": "json-file",
  "log-opts": {"max-size": "10m", "max-file": "3"}
}
EOF2
}

_expected_journald() {
  cat << 'EOF2'
# quantbridge — tools/scripts/host-bootstrap.sh 가 쓴다. 손으로 고치지 마라(다음 --install 이 덮는다).
[Journal]
SystemMaxUse=500M
EOF2
}

_same() { # _same <path> <expected-fn> → 0 같다 / 1 다르다·없다
  [ -f "$1" ] || return 1
  diff -q <("$2") "$1" > /dev/null 2>&1
}

_status() {
  local rc=0
  if _same "${DAEMON_JSON}" _expected_daemon; then
    echo "  ✓ ${DAEMON_JSON} — 로그 상한 10m×3"
  else
    echo "  ★드리프트: ${DAEMON_JSON} 이 없거나 다르다"; rc=1
  fi
  if _same "${JOURNALD_CONF}" _expected_journald; then
    echo "  ✓ ${JOURNALD_CONF} — SystemMaxUse=500M"
  else
    echo "  ★드리프트: ${JOURNALD_CONF} 이 없거나 다르다"; rc=1
  fi
  if command -v journalctl > /dev/null 2>&1; then
    echo "  journal 사용량: $(journalctl --disk-usage 2> /dev/null | grep -oE '[0-9.]+[GM]' | head -1 || echo '?')"
  fi
  return "${rc}"
}

_install() {
  [ "$(id -u)" = 0 ] || { echo "✗ root 가 아니다 — sudo 로 불러라" >&2; exit 1; }
  mkdir -p "$(dirname "${DAEMON_JSON}")" "$(dirname "${JOURNALD_CONF}")" || exit 1
  local changed=0
  if ! _same "${DAEMON_JSON}" _expected_daemon; then
    _expected_daemon > "${DAEMON_JSON}" || exit 1
    echo "  ✓ 썼다: ${DAEMON_JSON}"; changed=1
    # daemon.json 은 데몬 reload 로 읽힌다(SIGHUP). 재시작이 아니라 컨테이너는 안 끊긴다.
    if command -v systemctl > /dev/null 2>&1; then systemctl kill -s HUP docker 2> /dev/null || true; fi
  fi
  if ! _same "${JOURNALD_CONF}" _expected_journald; then
    _expected_journald > "${JOURNALD_CONF}" || exit 1
    echo "  ✓ 썼다: ${JOURNALD_CONF}"; changed=1
    if command -v systemctl > /dev/null 2>&1; then systemctl restart systemd-journald 2> /dev/null || true; fi
  fi
  [ "${changed}" -eq 1 ] || echo "  ✓ 이미 같다 — 바꾼 것 없음"
  _status
}

case "${1:-}" in
  --install) _install ;;
  --status) _status ;;
  -h | --help | "") sed -n '2,16p' "$0"; exit 0 ;;
  *) echo "알 수 없는 인자: $1 (--help)" >&2; exit 1 ;;
esac
