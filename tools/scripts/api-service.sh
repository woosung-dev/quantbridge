#!/usr/bin/env bash
#
# QuantBridge API 유닛 인스톨러 — `quantbridge-api.service` 를 레포가 만든다. ([BL-805])
#
# 왜 있나
#   2026-08-18 n5-ci-truth-close 레인 β 가 런북을 쓰며 실측했다: 서버의 systemd user 유닛
#   6종 중 **다섯은 스크립트의 `--install` 이 heredoc 으로 만드는데**
#   (`db-backup.sh` · `disk-guard.sh` · `soak-watch.sh` · `soak-gate.sh` · `soak-logs-follow.sh`)
#   `quantbridge-api.service` **하나만 예외**였다 — 유닛은 실재하고 running 인데 그것을 만드는
#   코드가 레포에 **0건**이라 **복원할 원본이 없었다.** `better-auth-setup.md:119` 는 배포 절차에서
#   `systemctl --user restart quantbridge-api.service` 를 지시하면서 정작 그 유닛의 출처를
#   말할 수 없는 상태였다. 서버를 다시 세우면 그 자리에서 밟는다.
#   ★[BL-744] 는 이 유닛이 어떻게 죽는지를 이미 보여줬다 — 08-07 기동 프로세스가 **삭제된 cwd**
#     를 붙들고 살아 있었고 `ExecStart` 는 사라져 **죽으면 rc=203/EXEC 영구 실패**였다.
#
# 사용:
#   tools/scripts/api-service.sh --status      # 설치본 신선도 · 유닛 상태
#   tools/scripts/api-service.sh --install     # systemd user service (Type=simple · Restart=always)
#   tools/scripts/api-service.sh --uninstall
#
# 종료 코드: 0 = 정상 / 1 = 실패 · 설치본이 낡음·부재
#
# env:
#   QB_API_HOST      bind 주소. 기본 `127.0.0.1` (서버 실측값 — 앞단이 리버스 프록시다).
#   QB_API_PORT      포트. 기본 `8100` (서버 실측값).
#   QB_API_UVICORN   uvicorn 실행 파일. 기본 `<ROOT>/apps/api/.venv/bin/uvicorn`.
#                    ★**주입 seam** — 하네스가 실제 venv 없이 판정 로직을 겨누는 유일한 경로다.
#
# ★설계 근거
#   · **유닛 이름이 형제들의 `dev.quantbridge.*` 규칙 밖이다.** 형제 5종은 전부
#     `dev.quantbridge.<이름>` 인데 이것만 맨 `quantbridge-api.service` 다 —
#     **서버 실물이 그 이름이고**(`FragmentPath=/home/ubuntu/.config/systemd/user/quantbridge-api.service`),
#     `better-auth-setup.md:119` 를 비롯한 배포 문서·런북이 그 이름을 인용한다. 규칙에 맞추려고
#     이름을 바꾸면 **이 스크립트가 만드는 유닛과 서버에서 도는 유닛이 서로 다른 것**이 되어
#     인스톨러가 있으나 마나가 된다. 이름은 실물을 따르고 예외 사유를 여기 남긴다.
#   · **`Type=simple` + `Restart=always` 다.** 형제 3종(`db-backup`·`disk-guard`·`soak-watch`)은
#     `Type=oneshot` + timer 라 그 모양을 베끼면 안 된다 — 이쪽은 **상주하는 서버 프로세스**이고,
#     같은 모양의 선례는 `soak-logs-follow.sh:214-262` 다. lingering 이 없으면 SSH 가 끊길 때
#     user manager 와 함께 죽으므로 `loginctl enable-linger` 를 시도한다(실패해도 경고만 — 없는
#     호스트에서 설치 자체를 막을 이유는 없다).
#   · **신선도는 `.venv` 경로 대조다.** 형제들의 `--status` 는
#     `ExecStart=/bin/bash <스크립트>` 를 sed 로 파싱하는데(`db-backup.sh:544-583`),
#     이쪽 `ExecStart` 는 `<ROOT>/apps/api/.venv/bin/uvicorn …` 이라 **그 파서를 그대로 못 쓴다.**
#     첫 토큰(= uvicorn 절대경로)을 뽑아 현재 트리의 것과 대조한다.
#     ★이것이 원장이 「`ExecStart` 가 `.venv` 절대경로라 [ADR-029] 류 재배치에 취약하다」고
#       적은 것의 답이다 — 취약함 자체는 없앨 수 없으니(systemd 는 절대경로를 요구한다)
#       **재배치가 일어났다는 사실을 판정 가능하게** 만든다.
#   · **설치 시 uvicorn 실재를 확인하고 없으면 거부한다.** 없는 파일을 가리키는 유닛을 세우면
#     정확히 [BL-744] 의 rc=127/203 좀비가 된다 — 그 상태는 `systemctl` 상 「enabled」로 보인다.
#   · **실패 알림 유닛(`OnFailure=`)은 두지 않았다.** 형제 감시자 2종과 달리 이쪽은
#     `Restart=always` 가 죽음을 스스로 되살리고, API 가 안 뜨는 사실은 `/health` 를 보는 쪽이
#     이미 잡는다. 알림 유닛을 얹으면 재시작마다 발화해 사람이 무시하게 된다.
#   · ★**`--status` 는 축이 넷이다** (2026-08-19 적대 리뷰 4건 수용, [BL-805]).
#     ⑴ **경로** — 설치본 `ExecStart` 의 첫 토큰 = 이 트리의 uvicorn 인가.
#     ⑵ **shebang** — 그 wrapper 첫 줄이 가리키는 **인터프리터가 실재**하는가. venv 는 재배치
#        불가라 체크아웃을 통째로 복사하면 wrapper 는 따라오지만 첫 줄은 **삭제된 옛 venv 의
#        python** 을 가리킨다. `[ -x wrapper ]` 는 그대로 참이고 systemd 는 `203/EXEC` 로 죽는다 —
#        즉 ⑴ 만으로는 [BL-744] 좀비의 한 갈래를 못 잡는다.
#     ⑶ **drop-in 합성** — `<unit>.d/*.conf` 가 `ExecStart` 를 재지정하면 원본 파일은 최신인데
#        실제로 도는 것은 옛 체크아웃이다. 그래서 **파일 축과 `systemctl show` 축을 둘 다** 본다.
#        ★`show -p ExecStart` 값은 **확장 _전_ 문자열**이라 `${VAR}`·`%i` 는 못 편다
#        (`docs/lessons.md` 2026-08-15 반증) — 그런 값이 오면 **판정 불가로 인쇄**하고 넘긴다.
#     ⑷ **활성 상태** — `is-failed`/`is-active`. ⑴~⑶ 이 전부 초록이어도 uvicorn 이 기동 직후
#        죽으면 유닛은 `failed` 다. 「아직 안 떴다(inactive)」와 「failed」는 **다른 상태**라
#        문구를 나눠 인쇄한다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

# ★유닛 이름은 `dev.quantbridge.*` 규칙의 **의도적 예외**다 — 위 「설계 근거」 첫 항 참고.
#   서버 실물이 이 이름이고 배포 문서가 이 이름을 인용한다. 바꾸지 마라.
UNIT_NAME="quantbridge-api"
UNIT_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"

API_DIR="${ROOT}/apps/api"
HOST="${QB_API_HOST:-127.0.0.1}"
PORT="${QB_API_PORT:-8100}"
UVICORN="${QB_API_UVICORN:-${API_DIR}/.venv/bin/uvicorn}"
METRICS_DIR="${API_DIR}/.metrics"

die() { printf '✗ %s\n' "$1" >&2; exit "${2:-1}"; }

MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --install) MODE="install" ;;
    --uninstall) MODE="uninstall" ;;
    --status) MODE="status" ;;
    -h | --help)
      sed -n '2,65p' "$0"
      exit 0
      ;;
    *)
      echo "알 수 없는 인자: $1  (--help)" >&2
      exit 1
      ;;
  esac
  shift
done

if [ -z "${MODE}" ]; then
  echo "✗ 서브커맨드가 없다 — --status / --install / --uninstall 중 하나가 필요하다 (--help)" >&2
  exit 1
fi

_require_systemctl() {
  command -v systemctl > /dev/null 2>&1 \
    || die "systemctl 이 없다 — 이 경로는 리눅스 전용이다 (macOS 에는 systemd user manager 가 없다)"
}

# ── 설치 ────────────────────────────────────────────────────────────────────────
_install() {
  _require_systemctl

  # ★없는 파일을 가리키는 유닛을 세우지 않는다 — 그것이 [BL-744] 의 좀비다.
  # ★안내문(`uv sync`)을 `die` 의 **여러 줄 문자열** 안에 두면 안 된다 —
  #   `tool-pin-audit.sh` 는 줄 단위라 여러 줄 문자열의 둘째 줄을 못 알아보고 거기의
  #   `&& uv sync` 를 **명령 위치의 진짜 호출**로 읽는다(2026-08-19 실측: rc=1).
  #   그 감사기가 안내문을 가르는 축은 「그 줄의 첫 명령이 `echo`/`printf`」이므로
  #   **안내문은 `echo` 줄로 낸다.** 정규식을 피하려고 문구를 비트는 것이 아니라
  #   감사기가 안내문이라고 정의한 형태로 쓰는 것이다 — 이 파일에 진짜 호출을 넣으면
  #   여전히 잡힌다(표적 변이로 실증).
  if [ ! -x "${UVICORN}" ]; then
    echo "✗ uvicorn 이 없거나 실행 권한이 없다: ${UVICORN}" >&2
    echo "  (venv 를 먼저 만들어라: cd ${API_DIR} && uv sync)" >&2
    exit 1
  fi

  # ★**shebang 이 죽은 wrapper 도 「없는 파일을 가리키는 유닛」이다** — 파일은 실재하는데
  #   exec 가 `203/EXEC` 로 죽으니 위 `-x` 검사만으로는 같은 좀비를 그대로 굽는다.
  local sb=""
  sb="$(_check_shebang "${UVICORN}")" \
    || die "uvicorn wrapper 의 shebang 이 죽었다 — 이대로 구우면 203/EXEC 좀비가 된다.
${sb}"

  mkdir -p "${UNIT_DIR}" || die "유닛 디렉터리를 만들 수 없다: ${UNIT_DIR}"
  # PROMETHEUS_MULTIPROC_DIR 는 **존재해야** prometheus multiprocess 모드가 뜬다.
  mkdir -p "${METRICS_DIR}" || die "메트릭 디렉터리를 만들 수 없다: ${METRICS_DIR}"

  # ★`Environment=` 를 두 줄로 나눈 것은 서버 실측(`Environment=A=x B=y` 한 줄)과 **의미가 같다** —
  #   systemd 는 두 표기를 같은 환경으로 편다. 줄을 나누면 값에 공백이 섞여도 안 깨진다.
  cat > "${UNIT_DIR}/${UNIT_NAME}.service" << EOF
[Unit]
Description=QuantBridge API (uvicorn ${HOST}:${PORT})

[Service]
Type=simple
WorkingDirectory=${API_DIR}
Environment=PATH=${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
Environment=PROMETHEUS_MULTIPROC_DIR=${METRICS_DIR}
Environment=QB_METRICS_ROLE=api
ExecStart=${UVICORN} src.main:app --no-server-header --host ${HOST} --port ${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

  systemctl --user daemon-reload || die "systemctl --user daemon-reload 실패"
  systemctl --user enable --now "${UNIT_NAME}.service" || die "service enable 실패"

  # lingering 이 없으면 SSH 가 끊길 때 user manager 와 서비스가 같이 죽는다
  # (`soak-logs-follow.sh:250-259` 와 같은 관용구). 실패해도 설치는 유지한다.
  local linger=""
  linger="$(loginctl show-user "$(id -un)" -p Linger --value 2> /dev/null)" || linger=""
  if ! printf '%s\n' "${linger}" | grep -qi '^yes$'; then
    if ! loginctl enable-linger "$(id -un)" 2> /dev/null; then
      echo "⚠ lingering 을 못 켰다 — SSH 를 끊으면 API 가 멈춘다." >&2
      echo "  직접 실행해라: sudo loginctl enable-linger $(id -un)" >&2
    fi
  fi

  echo "✓ 설치 완료 — ${UNIT_NAME}.service (uvicorn ${HOST}:${PORT})"
  echo "  ExecStart = ${UVICORN}"
  echo '  ★.venv 절대경로가 유닛에 구워진다 — 체크아웃을 옮기면 rc=127 로 죽는다.'
  echo "    옮긴 뒤에는 반드시 --status 로 확인하고 --install 로 다시 구워라."
  echo "  로그: journalctl --user -u ${UNIT_NAME}.service"
}

# ★실패를 삼키지 않는다 (2026-08-19 적대 리뷰). `Restart=always` 라 `disable --now` 가 실패하면
#   **API 는 계속 도는데** 유닛 파일만 사라진다 — 그 뒤에는 `systemctl` 로 멈출 수단도 없다.
#   그 상태를 「✓ 해제 완료」로 인쇄하는 것이 가장 나쁜 조합이라 실패를 모아 rc 에 싣는다.
_uninstall() {
  _require_systemctl
  local rc=0 f="${UNIT_DIR}/${UNIT_NAME}.service"

  if ! systemctl --user disable --now "${UNIT_NAME}.service" > /dev/null 2>&1; then
    if [ -f "${f}" ]; then
      echo "✗ systemctl --user disable --now 실패 — Restart=always 라 API 가 계속 돌 수 있다." >&2
      echo "  확인: systemctl --user status ${UNIT_NAME}.service" >&2
      rc=1
    else
      # 유닛 파일이 애초에 없으면 systemd 는 「Unit file does not exist」로 실패한다.
      # 지울 것이 없는 상태를 실패로 셀 이유는 없다.
      echo "⚠ disable --now 가 실패했지만 유닛 파일이 없다 — 이미 해제된 것으로 본다." >&2
    fi
  fi

  if ! rm -f "${f}" || [ -e "${f}" ]; then
    echo "✗ 유닛 파일을 지우지 못했다: ${f}" >&2
    rc=1
  fi

  if ! systemctl --user daemon-reload > /dev/null 2>&1; then
    echo "✗ systemctl --user daemon-reload 실패 — systemd 가 아직 옛 유닛을 들고 있다." >&2
    rc=1
  fi

  if [ "${rc}" -eq 0 ]; then
    echo "✓ 해제 완료 (메트릭 디렉터리는 남긴다: ${METRICS_DIR})"
  else
    echo "✗ 해제가 불완전하다 — 위 실패를 손으로 처리해라 (메트릭: ${METRICS_DIR})" >&2
  fi
  exit "${rc}"
}

# ── 설치본 신선도 ───────────────────────────────────────────────────────────────
# ★「유닛이 enabled」는 건강 신호가 아니다 ([BL-737] · [BL-744]). 재는 것은 「유닛이 있나」가
#   아니라 **무엇을 가리키나**다. 형제들은 `ExecStart=/bin/bash <스크립트>` 를 파싱하지만
#   이쪽은 `<venv>/bin/uvicorn <args>` 라 **첫 토큰**을 뽑는다.
_installed_execstart() {
  local f="${UNIT_DIR}/${UNIT_NAME}.service"
  [ -f "${f}" ] || return 0
  sed -n 's|^ExecStart=||p' "${f}" | head -1 | awk '{print $1}'
}

# ★wrapper 의 첫 줄이 가리키는 인터프리터가 실재하는가 — `[ -x wrapper ]` 가 못 보는 축.
#   `.venv/bin/uvicorn` 은 `#!<venv>/bin/python` 로 시작하는 **텍스트 스크립트**이고 venv 는
#   재배치 불가다. 체크아웃을 복사해 옮기면 wrapper 는 새 경로에 실재·실행 가능한데 첫 줄은
#   **삭제된 옛 venv** 를 가리켜 systemd 가 `203/EXEC` 로 죽는다.
#   ★판정 불가(바이너리 · `env` 경유)는 **조용히 통과시키지 않고 그 사실을 인쇄**한다.
#   반환: 0 = 정상 또는 판정 불가 / 1 = 인터프리터 부재
_check_shebang() {
  local f="$1" first interp
  first="$(head -1 "${f}" 2> /dev/null)" || first=""

  case "${first}" in
    '#!'*) ;;
    *)
      echo "  · shebang 이 없다 — 네이티브 실행 파일로 본다 (인터프리터 판정 불가)"
      return 0
      ;;
  esac

  # `#!` 뒤 첫 토큰. `#!/usr/bin/env -S python` 처럼 인자가 붙어도 첫 토큰만 본다.
  interp="$(printf '%s\n' "${first#\#!}" | awk '{print $1}')"

  case "${interp}" in
    "")
      echo "  · shebang 이 비었다 (판정 불가): ${first}"
      return 0
      ;;
    env | */env)
      echo "  · shebang 이 \`env\` 를 경유한다 — 실제 인터프리터는 PATH 에 달렸다 (판정 불가)"
      echo "      ${first}"
      return 0
      ;;
  esac

  if [ ! -x "${interp}" ]; then
    echo "  ✗ shebang 이 가리키는 인터프리터가 없다 — 이 유닛은 203/EXEC 로 죽는다"
    echo "      wrapper : ${f}"
    echo "      shebang : ${interp}"
    echo "    → venv 는 재배치 불가다. cd ${API_DIR} && uv sync 로 다시 만든 뒤 --install."
    return 1
  fi

  echo "  ✓ shebang 인터프리터 = ${interp}"
  return 0
}

# ★drop-in 을 **합성한 뒤**의 ExecStart. 파일 축(`_installed_execstart`)이 못 보는 것을 본다.
#   ★단 이 값은 systemd 의 **파싱 결과 = 확장 _전_ 문자열**이다 (`docs/lessons.md`, 2026-08-15
#     `OnFailure=` 알람 반증). 그래서 파일 축을 대체하지 않고 **더한다**.
_composed_execstart() {
  local raw path
  # 파이프를 쓰지 않는다 — pipefail + SIGPIPE 는 이 레포가 이미 밟은 함정이다.
  raw="$(systemctl --user show -p ExecStart --value "${UNIT_NAME}.service" 2> /dev/null)" || raw=""
  raw="${raw%%$'\n'*}"
  [ -n "${raw}" ] || return 0

  # systemd 실물 형식: `{ path=/x/uvicorn ; argv[]=/x/uvicorn src.main:app ; ignore_errors=no … }`
  case "${raw}" in
    *path=*)
      path="${raw#*path=}"
      path="${path%%;*}"
      ;;
    *) path="${raw}" ;;
  esac
  printf '%s\n' "${path}" | awk '{print $1}'
}

# `${VAR}` · `%i` 같은 미확장 지정자가 남아 있나 — 있으면 문자열 대조가 무의미하다.
_has_specifier() {
  case "$1" in
    *'$'* | *'%'*) return 0 ;;
    *) return 1 ;;
  esac
}

_status() {
  local got want="${UVICORN}" rc=0
  local f="${UNIT_DIR}/${UNIT_NAME}.service"

  echo "── 설치본 신선도 ──"
  got="$(_installed_execstart)"
  if [ -z "${got}" ]; then
    echo "  ✗ 설치된 유닛이 없다 (${f})"
    echo "    → tools/scripts/api-service.sh --install"
    rc=1
  elif [ ! -x "${got}" ]; then
    echo "  ✗ ExecStart 가 없는 파일을 가리킨다 — 이 유닛은 rc=127 로 죽는다: ${got}"
    echo "    → 체크아웃을 옮겼거나 venv 가 지워졌다. --install 로 다시 구워라."
    rc=1
  elif [ "${got}" != "${want}" ]; then
    echo "  ✗ ExecStart 가 이 트리의 venv 가 아니다 — 재설치해라 (--install)"
    echo "      설치본: ${got}"
    echo "      현재본: ${want}"
    rc=1
  else
    echo "  ✓ ExecStart = ${got}"
  fi

  # ★경로가 맞아도 wrapper 의 shebang 은 따로 봐야 한다 — 위 「설계 근거」 ⑵.
  if [ -n "${got}" ] && [ -x "${got}" ]; then
    _check_shebang "${got}" || rc=1
  fi

  echo "── drop-in 합성 ──"
  local dropin_dir="${UNIT_DIR}/${UNIT_NAME}.service.d" dropins="" p comp
  if [ -d "${dropin_dir}" ]; then
    for p in "${dropin_dir}"/*.conf; do
      [ -e "${p}" ] || continue
      dropins="${dropins} $(basename "${p}")"
    done
    if [ -n "${dropins}" ]; then
      echo "  · drop-in:${dropins}   (${dropin_dir})"
    else
      echo "  · drop-in 디렉터리는 있지만 .conf 가 없다: ${dropin_dir}"
    fi
  else
    echo "  · drop-in 없음"
  fi

  if ! command -v systemctl > /dev/null 2>&1; then
    echo "  · systemctl 이 없어 합성값을 못 읽는다 (판정 불가 — 파일 축만 유효)"
  else
    comp="$(_composed_execstart)"
    if [ -z "${comp}" ]; then
      echo "  · systemd 가 이 유닛을 안 읽고 있다 — 합성 ExecStart 가 비었다 (판정 불가)"
    elif _has_specifier "${comp}"; then
      echo "  · 합성값에 미확장 지정자가 남아 있다 — 문자열 대조 판정 불가: ${comp}"
    elif [ "${comp}" != "${want}" ]; then
      echo "  ✗ 합성 후 ExecStart 가 이 트리의 venv 가 아니다 — drop-in 이 재지정했을 수 있다"
      echo "      합성본: ${comp}"
      echo "      현재본: ${want}"
      echo "    → systemctl --user cat ${UNIT_NAME}.service 로 무엇이 덮는지 봐라."
      rc=1
    else
      echo "  ✓ 합성 후 ExecStart = ${comp}"
    fi
  fi

  echo "── 유닛 상태 ──"
  if ! command -v systemctl > /dev/null 2>&1; then
    echo "  systemctl 이 없다 (리눅스 전용)"
  else
    # ★「경로가 맞다」는 「돌고 있다」가 아니다. uvicorn 이 기동 직후 죽으면 앞 축은 전부
    #   초록인 채 유닛만 failed 다 — 그 상태가 rc=0 이면 이 스크립트는 거짓말을 한다.
    local state=""
    state="$(systemctl --user is-active "${UNIT_NAME}.service" 2> /dev/null)" || true
    [ -n "${state}" ] || state="unknown"

    if systemctl --user is-failed "${UNIT_NAME}.service" > /dev/null 2>&1; then
      echo "  ✗ 유닛이 failed 다 — 기동은 했는데 죽었다 (ExecStart 가 맞아도 이렇게 된다)"
      echo "    → journalctl --user -u ${UNIT_NAME}.service -n 50 --no-pager"
      rc=1
    elif [ "${state}" = "active" ]; then
      echo "  ✓ active"
    else
      echo "  ✗ 설치는 됐는데 활성이 아니다 (${state}) — failed 와는 다른 상태다"
      echo "    → systemctl --user start ${UNIT_NAME}.service"
      rc=1
    fi

    systemctl --user status --no-pager "${UNIT_NAME}.service" 2> /dev/null | sed -n '1,5p' \
      || echo "  (상세 조회 실패)"
  fi

  exit "${rc}"
}

case "${MODE}" in
  install) _install ;;
  uninstall) _uninstall ;;
  status) _status ;;
esac
