# 텔레그램 1 회 전송 — **부작용은 curl 하나뿐**. 판정 로직 없음. (BL-768)
#
# 왜 별 파일인가
#   이 배선은 `soak-watch.sh:105` 의 `_notify()` 로 2026-08-07 에 태어나 그 안에서만 살았다.
#   그런데 알림이 필요한 축이 둘이 됐다 — 소크 감시와 **디스크 경보**([BL-768]). 복제하면
#   토큰 취급 규칙(URL 을 찍지 않는다 · `--output /dev/null`)이 두 벌이 되고, 한쪽만 고쳐지는
#   순간 **조용히 새는 쪽**이 생긴다. 선례는 `lib/pre-push-ref-guard.sh` — 시험 가능한 한 벌로 뺀다.
#
# 계약
#   - source 전용이다. 직접 실행하지 마라(진입점이 없다).
#   - bash 전용. 호출자는 `set -uo pipefail` 아래에 있다고 가정한다.
#   - 입력은 인자 1 개(본문)와 아래 env 뿐이고, 출력은 종료 코드다. stdout 에 아무것도 안 쓴다.
#   - ★**URL 을 절대 출력하지 않는다** — 경로에 봇 토큰이 들어 있다. 실패해도 상태 코드만 말한다.
#     (`apps/api/src/common/telegram_alert.py:52-65` 의 `_safe_err` 가 같은 이유로 존재한다.)
#
# env
#   QB_NOTIFY_ENV_FILE  크레덴셜 파일 절대경로 (필수). `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`
#                       를 담고 있어야 한다. ★**통째 소싱**한다 — 이 레포는 변수 단독 주입을
#                       금지한다(AGENTS.md §환경).
#   QB_NOTIFY_TIMEOUT   초. 기본 15. ★외부 명령에 timeout 이 없으면 무기한 대기가 표본 수집까지
#                       멈춘다(2026-08-07 실측).
#   QB_NOTIFY_CMD       주입 seam. 설정되면 curl 대신 이 명령에 본문을 stdin 으로 넘긴다.
#                       하네스가 실제 텔레그램을 쏘지 않게 하는 유일한 경로다.

# qb_notify_telegram <본문> → 0 = 보냄 / 1 = 실패
qb_notify_telegram() {
  local body="$1"
  local env_file="${QB_NOTIFY_ENV_FILE:-}"
  local timeout_s="${QB_NOTIFY_TIMEOUT:-15}"

  # ★인용하지 않는다 — 주입 명령을 인자까지 포함해 단어 분리시키는 것이 의도다.
  if [ -n "${QB_NOTIFY_CMD:-}" ]; then
    printf '%s\n' "${body}" | ${QB_NOTIFY_CMD}
    return $?
  fi

  # 크레덴셜 — ★절대경로로 소싱한다. `cd apps/api && . ./.env.local` 은 이미 그 디렉터리에 있으면
  #   `cd` 가 실패해 `set -a` 만 건너뛰고 나머지가 이어져 env 가 export 되지 않는다(금지된 형태).
  if [ -z "${env_file}" ]; then
    echo "✗ QB_NOTIFY_ENV_FILE 이 비어 있다 — 크레덴셜 파일을 지정해라" >&2
    return 1
  fi
  if [ ! -f "${env_file}" ]; then
    echo "✗ env 파일이 없다: ${env_file}" >&2
    return 1
  fi

  # shellcheck disable=SC1090
  (
    set -a
    . "${env_file}"
    set +a

    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
      echo "✗ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 비어 있다" >&2
      exit 1
    fi

    # ★`--fail` 을 쓰지 않고 `--write-out '%{http_code}'` 로 **직접 판정**한다. `--fail` 은 본문을
    #   버리지만 여기서는 애초에 본문을 안 읽고(`--output /dev/null`) 상태 코드만 본다 — 200 이
    #   아니면 무조건 실패다. 이쪽이 `--fail` 보다 강하다(400/404 를 같은 축으로 잡는다).
    #   ★반대로 systemd 유닛의 **인라인** curl 에는 `--fail` 이 반드시 있어야 한다 — 거기서는
    #   종료 코드가 유일한 신호이고, 없으면 텔레그램이 404 를 줘도 유닛이 `Finished` 로 남는다.
    code="$(timeout "${timeout_s}" curl \
      --silent --show-error --output /dev/null --write-out '%{http_code}' \
      --max-time "${timeout_s}" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${body}" \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" 2> /dev/null)"
    if [ "${code}" = "200" ]; then
      exit 0
    fi
    echo "✗ 텔레그램 전송 실패 (HTTP ${code:-없음})" >&2
    exit 1
  )
}
