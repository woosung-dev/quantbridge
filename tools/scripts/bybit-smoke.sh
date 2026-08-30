#!/usr/bin/env bash
# Bybit Demo smoke — 주문 경로 1회 검증의 **정문**.
#
# 사용:
#   tools/scripts/bybit-smoke.sh                                   # dry-run (기본) · 네트워크 호출 0건
#   tools/scripts/bybit-smoke.sh --env-file ~/quantbridge/.env.demo --market spot --confirm
#
# 종료 코드: 0=검사 통과(또는 실호출 성공) · 1=검사/실행 실패 · 2=사용법 오류
#
# 설계 원칙 — 전부 이 레포가 실제로 데인 함정에서 나왔다:
#   · **`--dry-run` 이 기본이고 그 경로는 네트워크 호출 0건이다.** 이 레포의 초판 dry-run 이
#     거래소를 실제 조회한 전례가 있다(2026-08-07 소크 무인 감시). 그래서 파이썬을 부르는
#     자리를 `_execute()` **한 함수로 몰았고**, dry-run 은 `exit 0` 로 그 앞에서 끝난다.
#     ★★**「프로세스 0건」이 아니다** — dry-run 도 `stat`·`sed`·`head`·`grep` 은 돌린다.
#     전부 로컬 파일만 읽고 소켓을 열지 않는다. (초판 주석이 이것을 "외부 호출 0건" 이라고
#     뭉뚱그려 적어 codex 가 정당하게 반박했다 — 2026-08-09.)
#     ★정적 술어(재현 가능): `uv run` 은 파일에 3번 나오지만 **실행되는 자리는 `_execute()`
#     하나**이고 나머지 둘은 이 주석과 `CMD_DISPLAY` 문자열이다. 감사 명령 =
#       awk '/^_execute\(\)/{f=1} f&&/uv run/{print NR} /^}/{if(f)f=0}' tools/scripts/bybit-smoke.sh
#     이 한 줄만 찍혀야 한다.
#   · **credentials 는 argv 로 넘기지 않는다.** 같은 호스트의 아무 프로세스나 `ps` 로 읽는다.
#     env 로만 건네고, 이 스크립트는 값을 **한 번도 출력하지 않는다**(길이만 보고한다).
#   · **인라인 주석 오염을 검사한다** ([BL-625] 2차 결함) — 이 레포 관례상 env 파일은
#     `KEY=value  # [필수 …]` 로 쓰는데, 값에 주석이나 한글이 섞이면 401 이 아니라 **500** 이
#     난다(`clerk_backend_api` 가 헤더를 ascii 인코딩 → UnicodeEncodeError). 증상이 달라서
#     진단이 늦는다. 여기서 미리 잡는다.
#   · **fail-closed** — 검사 실패는 「이상 없음」이 아니라 비-0 종료다. 파일 부재도 실패다.
#   · env 파일을 `source` 하지 않는다 — 임의 코드 실행 표면이다. 필요한 키만 파싱한다.
#   · 파이프에 넣지 마라 — 종료 코드가 가려진다(이 레포가 반복해 물렸다).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ★도구 버전 핀 — `_execute()` 의 `uv run python scripts/bybit_smoke.py` 는 **실주문 경로**다.
#   어느 uv/venv 로 돌았는지 모르는 채 거래소에 주문을 내지 않는다([BL-785]).
# shellcheck source=tools/scripts/lib/mise-shim-path.sh
. "${SCRIPT_DIR}/lib/mise-shim-path.sh"
qb_pin_tool_path || true

MARKET="linear"
SYMBOL=""
QUANTITY=""
LEVERAGE="1"
ENV_FILE=""
CONFIRM="no"

KEY_VAR="BYBIT_SMOKE_API_KEY"
SECRET_VAR="BYBIT_SMOKE_API_SECRET"

die() {
  printf '✗ %s\n' "$*" >&2
  exit 1
}

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}"
  exit 2
}

# ★값을 받는 옵션은 값 유무를 **먼저** 검사한다 — `shift 2` 는 인자가 하나뿐이면 실패하고
#   `set -e` 가 없으므로 그 실패가 삼켜져 **같은 인자를 무한히 다시 읽는다**
#   (2026-08-09 실측: `--mode` 단독 실행이 10초 타임아웃 rc=124).
need_val() { [[ $# -ge 2 ]] || die "$1 에 값이 없다"; }

ARGV_CREDS="no"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) CONFIRM="no"; shift ;;
    --confirm) CONFIRM="yes"; shift ;;
    --mode) die "--mode 는 지원하지 않는다. Bybit Demo 전용이다" ;;
    --market) need_val "$@"; MARKET="$2"; shift 2 ;;
    --symbol) need_val "$@"; SYMBOL="$2"; shift 2 ;;
    --quantity) need_val "$@"; QUANTITY="$2"; shift 2 ;;
    --leverage) need_val "$@"; LEVERAGE="$2"; shift 2 ;;
    --env-file) need_val "$@"; ENV_FILE="$2"; shift 2 ;;
    --api-key|--api-secret) ARGV_CREDS="yes"; shift 2 ;;
    -h|--help) usage ;;
    *) printf '✗ 알 수 없는 인자: %s\n' "$1" >&2; usage ;;
  esac
done

# credentials 를 argv 로 주는 것은 `ps` 노출이다.
if [[ "${ARGV_CREDS}" == "yes" ]]; then
  die "--api-key/--api-secret 을 argv 로 주지 마라 (ps 노출). --env-file 을 써라"
fi

[[ "${MARKET}" == "spot" || "${MARKET}" == "linear" ]] || die "--market 은 spot|linear (받은 값: ${MARKET})"

# 심볼 기본값은 market 을 따라간다 — linear 에 spot 심볼을 주면 거래소가 조용히 다른 것을 연다.
if [[ -z "${SYMBOL}" ]]; then
  if [[ "${MARKET}" == "spot" ]]; then SYMBOL="BTC/USDT"; else SYMBOL="BTC/USDT:USDT"; fi
fi
# 수량 기본값도 갈린다 (2026-08-09 `load_markets` 실측 · BTC \$64,957):
#   · perp `BTC/USDT:USDT` — min_amount **0.001 BTC**, min_cost 없음 ⇒ 최소 명목 **\$64.96**.
#     단계-1 자본 \$50 으로는 1x 증거금이 모자라므로 spot 을 쓴다.
#   · spot `BTC/USDT` — min_amount 1e-06 은 무의미하고 **min_cost \$5.0** 이 진짜 하한이다.
#     0.0002 BTC = \$13(BTC \$65k) / \$10(BTC \$50k) 로 하한 위에 여유가 있다.
#     ★초판은 0.0001(=\$6.5)이었다 — 하한에 너무 가까웠다.
#     ★BTC 가 \$25,000 아래면 0.0002 도 \$5 미만이 된다. 그때는 --quantity 를 올려라.
if [[ -z "${QUANTITY}" ]]; then
  if [[ "${MARKET}" == "spot" ]]; then QUANTITY="0.0002"; else QUANTITY="0.001"; fi
fi

if [[ -z "${ENV_FILE}" ]]; then
  ENV_FILE="${HOME}/quantbridge/.env.demo"
fi

# ── 검사 (네트워크 호출 0건 · 로컬 stat·sed·grep 은 돈다) ───────────────────────────────────────────────────────
printf '══ bybit-demo-smoke  market=%s  symbol=%s ══\n' "${MARKET}" "${SYMBOL}"

[[ -f "${ENV_FILE}" ]] || die "시크릿 파일이 없다: ${ENV_FILE}  (--env-file 로 지정하거나 runbook §시크릿 절차를 따라라)"

# 권한 — 0600 이 아니면 같은 호스트의 다른 사용자가 실키를 읽는다.
PERM="$(stat -f '%Lp' "${ENV_FILE}" 2>/dev/null || stat -c '%a' "${ENV_FILE}" 2>/dev/null)"
[[ "${PERM}" == "600" ]] || die "시크릿 파일 권한이 ${PERM} 다 — 0600 이어야 한다: chmod 600 ${ENV_FILE}"
printf '  ✓ 파일 %s (0600)\n' "${ENV_FILE}"

# 값만 뽑는다 — source 하지 않는다(임의 코드 실행 표면).
read_key() {
  local var="$1" raw
  raw="$(sed -n "s/^[[:space:]]*${var}[[:space:]]*=//p" "${ENV_FILE}" | head -n 1)"
  # 앞뒤 공백 제거 — `KEY=value ` 의 trailing space 하나면 서명이 어긋나 401 이 난다.
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  printf '%s' "${raw}"
}

RAW_KEY="$(read_key "${KEY_VAR}")"
RAW_SECRET="$(read_key "${SECRET_VAR}")"

check_value() {
  local var="$1" raw="$2"
  [[ -n "${raw}" ]] || die "${var} 가 ${ENV_FILE} 에 없거나 비어 있다"
  # [BL-625] 2차 결함 — 인라인 주석/비-ASCII 가 값에 섞이면 401 이 아니라 500 이 난다.
  # ★비-ASCII 판정은 **`LC_ALL=C` 를 건 grep 으로만** 한다 — case 의 `[![:print:]]` 는
  #   이 맥의 UTF-8 로케일에서 한글을 print 로 보고 통과시켰다(2026-08-09 실측).
  case "${raw}" in
    *"#"*) die "${var} 값에 '#' 이 섞였다 — 인라인 주석을 지워라 ([BL-625])" ;;
  esac
  LC_ALL=C grep -q '[^[:print:]]' <<<"${raw}" && die "${var} 값에 비-ASCII 가 섞였다 ([BL-625])"
  # ★플레이스홀더 패턴 목록은 **완전할 수 없다** — 이것만 믿지 마라.
  #   `REPLACE_ME` 가 초판을 그대로 통과했다(2026-08-09 codex 적대 리뷰). 그래서 패턴에
  #   더하는 것과 별개로 **길이·문자셋** 이라는 구조적 술어를 함께 건다.
  case "${raw}" in
    *PASTE*|*CHANGE*|*change-me*|*placeholder*|*PLACEHOLDER*|*YOUR_*|*REPLACE*|*EXAMPLE*|*example*|*TODO*|*XXX*|*여기에*)
      die "${var} 가 **플레이스홀더 그대로**다 — 실제 키로 바꿔라" ;;
  esac
  # Bybit API key/secret 은 영숫자다. 밑줄·하이픈·공백이 있으면 사람이 쓴 자리표시자다.
  LC_ALL=C grep -Eq '^[A-Za-z0-9]{16,}$' <<<"${raw}" \
    || die "${var} 형식이 Bybit 키 같지 않다 (영숫자 16자 이상이어야 한다 · 길이 ${#raw})"
  printf '  ✓ %s 존재 (길이 %d · 값은 출력하지 않는다)\n' "${var}" "${#raw}"
}

check_value "${KEY_VAR}" "${RAW_KEY}"
check_value "${SECRET_VAR}" "${RAW_SECRET}"

CMD_DISPLAY="uv run python scripts/bybit_smoke.py --market ${MARKET} --symbol ${SYMBOL} --quantity ${QUANTITY} --leverage ${LEVERAGE}"

if [[ "${CONFIRM}" != "yes" ]]; then
  printf '  ── dry-run — 네트워크 호출 0건. 거래소에 아무것도 보내지 않았다.\n'
  printf '  실행될 명령 (credentials 는 env 로만 건넨다 · argv 노출 없음):\n'
  printf '    cd %s/apps/api && %s\n' "${REPO_ROOT}" "${CMD_DISPLAY}"
  printf '\n  실행하려면 --confirm 을 붙여라. Demo 주문이 실제로 생성·취소된다.\n'
  exit 0
fi

# ── 실호출 (여기서만 외부에 나간다) ───────────────────────────────────────────
_execute() {
  cd "${REPO_ROOT}/apps/api" || die "backend 디렉터리 없음"
  BYBIT_SMOKE_API_KEY="${RAW_KEY}" \
  BYBIT_SMOKE_API_SECRET="${RAW_SECRET}" \
    uv run python scripts/bybit_smoke.py \
      --market "${MARKET}" \
      --symbol "${SYMBOL}" \
      --quantity "${QUANTITY}" \
      --leverage "${LEVERAGE}"
}

printf '  ── Bybit Demo 실호출 시작\n'
_execute
RC=$?
printf '\n종료 코드 %d  (0=성공)\n' "${RC}"
exit "${RC}"
