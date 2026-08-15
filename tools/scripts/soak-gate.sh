#!/usr/bin/env bash
#
# [BL-003] 「Bybit Demo 1주 안정 운영」 게이트 — **판정기이자 증거 수집기**.
# ★C1 문턱 = **≥24h 창 3회** (2026-08-11 [BL-701]). ~~누적 168h~~ 는 참고값으로만 찍는다.
#
# 사용:
#   tools/scripts/soak-gate.sh                 # 표본을 남기고 판정한다
#   tools/scripts/soak-gate.sh --json          # 판정 JSON 전문
#   tools/scripts/soak-gate.sh --since <ISO>   # 평가 창 시작을 강제 (자기시험·과거 재판정용)
#   tools/scripts/soak-gate.sh --no-collect    # 표본을 남기지 않고 지금 원장으로만 판정
#   tools/scripts/soak-gate.sh --require-windows N --require-continuous N  # ★자기시험 전용
#   tools/scripts/soak-gate.sh --install / --uninstall / --status         # 30분마다 (macOS launchd / 리눅스 systemd user timer)
#   tools/scripts/soak-gate.sh --prune-archives [--confirm]  # 상위집합에 덮인 phantom 아카이브 회수 (기본 dry-run)
#
# 종료 코드: 0 = PASS **만** / 1 = FAIL / 2 = UNKNOWN
#   ★**UNKNOWN 을 PASS 로 접지 않는다.** 이 스크립트의 존재 이유가 그것이다.
#   낱말은 셋뿐이라 `진행중`(시간 부족)과 `측정불가`(잴 수 없음)는 **사유 낱말**로 가른다.
#
# 술어와 창 정의: docs/decisions/024-soak-stability-gate.md
# 계산: apps/api/scripts/soak_gate_predicate.py (순수 함수 — I/O 없음, 손 계산과 대조 가능)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
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
#   `:8100` 리스너 0개). 워커는 같은 counter 를 `apps/api/.metrics` 에 계속 쓰고 있으므로
#   HTTP 를 거치지 않고 거기서 읽는다 — 「API 가 꺼지면 게이트가 장님」이라는 실패 계열이 사라진다.
#   ★`QB_METRICS_URL` 을 **명시하면** 종전대로 HTTP 를 쓴다(원격 데몬 + ssh 터널 운영안 보존).
METRICS_URL="${QB_METRICS_URL:-}"
# ★`/metrics` 는 2026-08-11 부터 **토큰 없이 401** 이다(fail-closed 전환, [BL-704]).
#   HTTP 갈래를 쓰려면 헤더를 보내야 한다 — 안 보내면 401 이 `curl -sf` 실패로 떨어져
#   「지표 취득 실패」가 되고, `-f` 가 없던 절차에서는 401 본문이 **「지표 0건」처럼 읽힌다.**
#   기본 경로(디렉터리 직독)는 인증이 없으므로 영향받지 않는다.
METRICS_HDR=()
_qb_tok="${PROMETHEUS_BEARER_TOKEN:-}"
if [ -z "${_qb_tok}" ] && [ -f "${ROOT}/apps/api/.env.local" ]; then
  _qb_tok="$(sed -n 's/^PROMETHEUS_BEARER_TOKEN=//p' "${ROOT}/apps/api/.env.local" | head -1)"
fi
[ -n "${_qb_tok}" ] && METRICS_HDR=(-H "Authorization: Bearer ${_qb_tok}")

METRICS_DIR="${QB_METRICS_DIR:-${ROOT}/apps/api/.metrics}"

mkdir -p "${STATE_DIR}" "${LOGDIR}"

SINCE=""
AS_JSON=0
COLLECT=1
REQUIRE_HOURS=""
REQUIRE_CONTINUOUS=""
# ★C1 의 진짜 문턱은 이제 이것이다 ([BL-701]) — 자기시험이 낮출 수 있어야 한다.
#   없으면 `--require-hours` 로는 아무것도 못 낮춘다(그 값은 참고용으로 강등됐다).
REQUIRE_WINDOWS=""

_install_systemd() {
  # ★user timer 를 쓴다 — launchd LaunchAgent 와 같은 층(사용자 단위, sudo 불필요)이다.
  # 대신 로그인 세션 없이 돌려면 lingering 이 필요하다. 아래에서 켜고, 실패하면 알려만 준다.
  local paths="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  local unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "${unit_dir}"
  cat > "${unit_dir}/${LABEL}.service" <<UNIT_EOF
[Unit]
Description=QuantBridge soak gate ([BL-003] 24h창x3 판정기)

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PATH=${paths}
ExecStart=/bin/bash ${ROOT}/tools/scripts/soak-gate.sh
# 게이트의 종료 코드는 0=PASS / 1=FAIL / 2=UNKNOWN 이지만 systemd 는 0 외를 전부 실패로 본다.
# 그래서 dev.quantbridge.soak-gate.service 가 매 실행 failed 로 남아 status 를 건강 신호로 못 썼다(2026-08-08 실측, 8/8 failed).
SuccessExitStatus=1 2
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
    <string>${ROOT}/tools/scripts/soak-gate.sh</string>
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

_prune_archives() { # $1 = "confirm" 이면 실제로 옮긴다
  # `.soak/phantom-*.json` 회수 ([BL-626]). ★**기본은 dry-run** — 옮기려면 --confirm.
  #
  # ★★**개수 상한은 쓰지 않는다 — 그건 판정을 깎는다.** 아카이브는 커버리지 구간
  #   (`log_from`~`log_to`)을 들고 있고 C1 은 **커버리지가 덮은 시간만** 센다. 실측
  #   2026-08-09(메인 체크아웃 228벌): 「최근 50개만 남긴다」면 커버리지 시작이
  #   `2026-08-04T15:51` → `2026-08-08T18:21` 로 **나흘치가 사라진다.** 168h 게이트를
  #   30분 주기로 채우려면 ~336벌이 필요하므로 어떤 상수 N 도 안전하지 않다.
  #
  # ★그래서 기준은 개수가 아니라 **포함관계**다. 매 실행이 워커 로그 **전량**을 다시
  #   분류하므로, 같은 `(log_from, predicate_version, classifier_ok)` 안에서는 `log_to` 가
  #   가장 늦은 아카이브가 나머지의 **상위집합**이다 — 커버리지도(같은 시작·더 늦은 끝),
  #   verdicts 도(같은 코퍼스·같은 판별식·더 긴 지평). 그것만 남기고 나머지를 옮긴다.
  # ★`predicate_version` 을 키에 넣는 이유 — 새 판별식이 취소한 옛 라벨을 조용히 버리면
  #   합집합 규율([ADR-024] §아카이브 판)이 깨진다. 판이 다르면 다른 그룹이다.
  # ★`log_to` 가 ISO 로 안 읽히는 것은 **절대 회수하지 않는다** — 실측 10벌이 타임스탬프
  #   자리에 문자 `Error` 를 들고 있고(launchd 파손), 그것들은 `unreadable_log_coverage` 로
  #   C5 에 참여한다. 문자열 정렬로 재면 `Error` 가 ISO 보다 크게 나와 성한 것을 버린다.
  # ★지우지 않는다 — `.soak/superseded-<STAMP>/` 로 **옮긴다**. 원자료는 되돌릴 수 있어야 한다.
  local mode="${1:-dry}"
  QB_PRUNE_MODE="${mode}" python3 - "${STATE_DIR}" <<'PY'
import collections, json, os, pathlib, re, shutil, sys

state = pathlib.Path(sys.argv[1])
confirm = os.environ.get("QB_PRUNE_MODE") == "confirm"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T")

groups = collections.defaultdict(list)
frozen = []
for p in sorted(state.glob("phantom-*.json")):
    try:
        blob = json.loads(p.read_text())
    except Exception:
        frozen.append((p, "판독 불가 JSON"))
        continue
    to = str(blob.get("log_to") or "")
    if not ISO.match(to):
        frozen.append((p, f"log_to 가 ISO 가 아니다: {to!r}"))
        continue
    key = (blob.get("log_from"), blob.get("predicate_version"), blob.get("classifier_ok") is True)
    groups[key].append((to, p))

keep, drop = set(), []
for members in groups.values():
    members.sort()
    keep.add(members[-1][1])
    drop.extend(p for _, p in members[:-1])

total = len(list(state.glob("phantom-*.json")))
print(f"아카이브 {total}벌 · 그룹 {len(groups)}개 · 보존 {len(keep)}벌 · 회수 대상 {len(drop)}벌 · 손대지 않음 {len(frozen)}벌")
for p, why in frozen[:3]:
    print(f"  손대지 않음: {p.name} — {why}")
if not confirm:
    for p in drop[:3]:
        print(f"  회수 대상(예): {p.name}")
    print("dry-run — 아무것도 옮기지 않았다. 집행하려면 --prune-archives --confirm")
    raise SystemExit(0)
if not drop:
    print("회수할 것이 없다.")
    raise SystemExit(0)
dest = state / f"superseded-{sorted(p.name for p in drop)[-1][8:24]}"
dest.mkdir(parents=True, exist_ok=True)
for p in drop:
    shutil.move(str(p), str(dest / p.name))
print(f"✓ {len(drop)}벌을 {dest} 로 옮겼다 (지우지 않았다)")
PY
  exit $?
}

while [ $# -gt 0 ]; do
  case "$1" in
    --install) _install ;;
    --uninstall) _uninstall ;;
    --status) _status ;;
    --prune-archives)
      if [ "${2:-}" = "--confirm" ]; then _prune_archives confirm; else _prune_archives dry; fi ;;
    --json) AS_JSON=1 ;;
    --no-collect) COLLECT=0 ;;
    --since) [ $# -ge 2 ] || { echo "--since 에 값이 없다" >&2; exit 1; }; SINCE="$2"; shift ;;
    --require-hours) [ $# -ge 2 ] || { echo "--require-hours 에 값이 없다" >&2; exit 1; }; REQUIRE_HOURS="$2"; shift ;;
    --require-continuous) [ $# -ge 2 ] || { echo "--require-continuous 에 값이 없다" >&2; exit 1; }; REQUIRE_CONTINUOUS="$2"; shift ;;
    --require-windows) [ $# -ge 2 ] || { echo "--require-windows 에 값이 없다" >&2; exit 1; }; REQUIRE_WINDOWS="$2"; shift ;;
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

# 이 실행이 **어느 DB 를 봤는가** — 헤더에 찍는다 ([BL-657])
#
# ★위험은 「틀린다」가 아니라 **「틀린 티가 안 난다」**다. 소크는 클라우드 서버에 있는데
#   같은 스크립트를 로컬에서 돌리면 로컬 docker 의 낡은 `quantbridge-db` 를 재고, 그 결과는
#   오류가 아니라 **정상 서식의 숫자**로 나온다(2026-08-08 실측: C1 1.5574h 로컬 vs 15.5680h 서버).
# ★★**갈리는 축은 `DATABASE_URL` 이 아니다.** C1~C5 의 입력은 위 `_q()` = `docker exec
#   ${DB_CONTAINER} psql` 이므로 축은 「**어느 docker 데몬의 어느 컨테이너**인가」다.
#   `DATABASE_URL` 은 phantom 분류기(:339)만 쓰지만 그 결과가 `unverified_hours` 로 C1 을
#   깎으므로 함께 찍는다 — 둘이 어긋나 있으면 그 사실 자체가 신호다.
# ★비밀번호를 절대 찍지 않는다 — 마지막 `@` 앞을 통째로 버려 host:port/dbname 만 남긴다.
DB_ADDR="$(docker port "${DB_CONTAINER}" 5432/tcp 2>/dev/null | head -1)"
[ -n "${DB_ADDR}" ] || DB_ADDR="(포트 미공개)"
# dbname 은 하드코딩을 믿지 않고 **DB 에게 묻는다**.
# ★`docker exec` 는 OCI 런타임 오류를 **stdout 으로** 낸다(실측: 컨테이너를 바꾸면 헤더에
#   `exec: "psql": executable file not found` 가 그대로 실렸다). 식별자 서식이 아니면 버린다.
DB_NAME_SEEN="$(_q "SELECT current_database();")"
[[ "${DB_NAME_SEEN}" =~ ^[A-Za-z0-9_]+$ ]] || DB_NAME_SEEN="?"
DOCKER_ENDPOINT="${DOCKER_HOST:-ctx:$(docker context show 2>/dev/null)}"
DB_ENV_TARGET=""
if [ -f "${ROOT}/apps/api/.env.local" ]; then
  _dburl="$(grep -E '^[[:space:]]*DATABASE_URL=' "${ROOT}/apps/api/.env.local" | tail -1)"
  _dburl="${_dburl#*=}"
  _dburl="${_dburl%%[[:space:]]*}"   # 인라인 주석·후행 공백 (값에 공백은 없다)
  _dburl="${_dburl//\"/}"
  _dburl="${_dburl//\'/}"
  _dburl="${_dburl##*@}"             # ★자격증명 폐기 (비밀번호에 `@` 가 있어도 안전)
  DB_ENV_TARGET="${_dburl%%\?*}"
fi
[ -n "${DB_ENV_TARGET}" ] || DB_ENV_TARGET="(없음)"

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
bash "${ROOT}/tools/scripts/soak-stack.sh" assert-not-pinned >/dev/null 2>&1 || STACK_PINNED=1

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
#   그 근거(실측 표)는 `apps/api/scripts/redis_aof_readability.py` 에 있고, 실측 캡처 7형이
#   `apps/api/tests/tools/scripts/test_redis_aof_readability.py` 로 동결돼 있다. **여기 복제하지 않는다.**
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
AOF_OK="$(python3 "${ROOT}/apps/api/scripts/redis_aof_readability.py" "${AOF_FILE}")"
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
LOG_NOTE=""
ISO_RE='^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
if [ "${COLLECT}" = "1" ]; then
  LOG_PROBE=""
  LOG_PROBE="$(mktemp "${TMPDIR:-/tmp}/quantbridge-soak-gate.XXXXXX")" || {
    LOG_NOTE="워커 로그 프로브 임시 파일 생성 실패"
  }
  if [ -z "${LOG_NOTE}" ]; then
    docker logs --timestamps --tail 1 "${WORKER_CONTAINER}" > "${LOG_PROBE}" 2>&1
    LOG_RC=$?
    if [ "${LOG_RC}" -eq 0 ]; then
      LOG_LAST="$(head -1 "${LOG_PROBE}" | cut -d' ' -f1)"
      LOG_FIRST="$(docker logs --timestamps "${WORKER_CONTAINER}" 2>&1 | head -1 | cut -d' ' -f1)"
      if ! [[ "${LOG_FIRST}" =~ ${ISO_RE} ]] || ! [[ "${LOG_LAST}" =~ ${ISO_RE} ]]; then
        LOG_NOTE="워커 로그 타임스탬프가 비어 있거나 ISO 8601 형식이 아니다 (처음: ${LOG_FIRST:-없음}, 마지막: ${LOG_LAST:-없음})"
      fi
    else
      LOG_PROBE_REASON="$(head -1 "${LOG_PROBE}")"
      LOG_NOTE="워커 로그 조회 실패 (rc=${LOG_RC}): ${LOG_PROBE_REASON:0:160}"
    fi
  fi
  [ -z "${LOG_PROBE}" ] || rm -f "${LOG_PROBE}"
  if [ -n "${LOG_NOTE}" ]; then
    LOG_FIRST=""
    LOG_LAST=""
    echo "⚠ ${LOG_NOTE}" >&2
  fi

  if [ -z "${LOG_NOTE}" ]; then
    # ★분류기는 backend 의존성(sqlalchemy/asyncpg)과 DATABASE_URL 이 있어야 돈다.
    #   시스템 python3 로 돌리면 조용히 실패해 **verdicts 가 늘 0** 이 된다(실측 2026-08-04).
    #   ★`cd apps/api && set -a; . ./.env.local` 금지 — 이미 backend 면 cd 가 실패해
    #   `set -a` 만 건너뛴다. 절대경로로 소싱한다.
    # 관측 0건이면 분류기는 exit 1 + 텍스트를 낸다 — 그건 실패가 아니라 「phantom 없음」이다.
    # ★`--corpus-end` 로 **Docker 가 보장하는 로그 끝**을 넘긴다. 안 넘기면 분류기가
    #   앱 줄 정규식에서 지평을 유도하는데, 그 포맷은 timezone 을 버리고 UTC 로 강제하며
    #   무타임스탬프 후행 줄이 있으면 지평이 과소평가된다. 회복식은 그 지평으로
    #   「나았다」와 「아직 못 봄」을 가르므로 조용히 판정이 흔들린다(codex P2 2026-08-05).
    ( set -a; . "${ROOT}/apps/api/.env.local"; set +a
      docker logs "${WORKER_CONTAINER}" 2>&1 \
        | (cd "${ROOT}/apps/api" && uv run python scripts/classify_direction_divergence.py \
             --json --corpus-end "${LOG_LAST}" 2>&1)
    ) > "${PHANTOM_JSON}.tmp" 2>/dev/null
  else
    # 타임스탬프 검증 실패 시에는 분류하지 않고 빈 임시 결과만 남긴다.
    : > "${PHANTOM_JSON}.tmp"
  fi
    # ★★분류기 **성공 여부를 따로 기록**한다. 껍데기 아카이브(verdicts 0)를 커버리지로
    #   인정하면 「phantom 없음 + 검증된 로그」로 읽혀 그 시간이 credit 되고 진짜 phantom 도
    #   숨는다 — fail-open 이다(codex P1). 성공의 정의는 둘 중 하나뿐이다:
    #     ⑴ 파싱되는 JSON 을 냈다   ⑵ 「관측이 없다」를 명시적으로 냈다(정상적인 0건)
    #   그 외(의존성·DB·인자 실패)는 `classifier_ok=false` 로 남기고 커버리지에서 제외된다.
  python3 - "${PHANTOM_JSON}.tmp" "${PHANTOM_JSON}" "${LOG_FIRST}" "${LOG_LAST}" "${LOG_NOTE}" <<'PY'
import json, pathlib, sys

src, dst, first, last, log_note = sys.argv[1:6]
raw_text = pathlib.Path(src).read_text() if pathlib.Path(src).exists() else ""
verdicts, ok, note, version = [], False, "", None
if log_note:
    ok, note, first, last = False, log_note, "", ""
else:
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
            "log_from": first or None,
            "log_to": last or None,
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
if not ok and not log_note:
    print(f"⚠ phantom 분류기 실패 — 이 창은 커버리지로 인정되지 않는다: {note}", file=sys.stderr)
PY
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
  METRICS_RAW="$(curl -sf ${METRICS_HDR[@]+"${METRICS_HDR[@]}"} --max-time 20 "${METRICS_URL}" 2>/dev/null)" \
    && [ -n "${METRICS_RAW}" ] && METRICS_RC=0
elif [ -d "${METRICS_DIR}" ]; then
  # ★`timeout` 없이 부르지 마라 — 게이트가 무기한 대기하면 표본 수집까지 멈춘다([BL-594] 교훈).
  METRICS_RAW="$(cd "${ROOT}/apps/api" && PROMETHEUS_MULTIPROC_DIR="${METRICS_DIR}" \
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
  "${REQUIRE_HOURS}" "${REQUIRE_CONTINUOUS}" "${SINCE}" "${SESSIONS_FILE}" "${AOF_OK}" \
  "${REQUIRE_WINDOWS}" \
  "${ROOT}" <<'PY'
import json, pathlib, sys

state = pathlib.Path(sys.argv[1])
now, darkness_raw, db_ok, stack_pinned = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
require_hours, require_continuous, since = sys.argv[6], sys.argv[7], sys.argv[8]
sessions_tsv = pathlib.Path(sys.argv[9]).read_text()
aof_ok = sys.argv[10]
# ★새 인자는 **끝에 붙였다** — 중간에 끼우면 뒤의 인덱스가 전부 밀린다(초판이 그랬다).
require_windows = sys.argv[11]
repo_root = pathlib.Path(sys.argv[12])

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
if require_windows:
    thresholds["require_windows"] = int(require_windows)

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
    # ★실격 귀속 원장 ([BL-641]) — **보고 전용이고 판정에 참여하지 않는다.** 파일이 없으면
    #   빈 목록이 실리고, 그러면 모든 실격이 `undecided` 로 보고된다(엄격 쪽). 이 축이
    #   C1~C5 를 한 글자도 못 바꾼다는 것은 `test_soak_gate_predicate.py` 가 지킨다.
    "disqualification_ledger": read_jsonl(
        repo_root / "docs" / "reference" / "operations" / "soak-disqualifications.jsonl"
    ),
}
if since:
    payload["since"] = since
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
)"
rm -f "${SESSIONS_FILE}"

# ★[BL-727] — 맨 `python3` 로 부르면 **맥에서 판정을 못 낸다.** `/usr/bin/python3` 는 3.9.6 이고
#   `soak_gate_predicate.py` 는 `itertools.pairwise`(3.10+)를 쓴다. 죽어도 이 스크립트는 계속
#   진행해 아래에서 **빈 `판정:` 줄**을 인쇄했다 — fail-open 이다(실측 2026-08-14 맥 판독 사망).
#   같은 함정을 `:449` 가 이미 `uv run python` 으로 고치며 「verdicts 가 늘 0 이 된다」고 적어
#   뒀는데 판정 본체에는 적용되지 않았다.
# ★나머지 `python3` 호출 10곳(`:220 :391 :471 :546 :567 :572` + 아래 3곳 + `:745`)은 **그대로
#   둔다** — 전부 stdlib(`json`/`pathlib`/`re`/`collections`)만 쓰고 3.10+ 문법이 없어 3.9 에서도
#   돈다. 3.10+ 를 요구하는 자리는 이 한 곳뿐이다.
# ★`cd apps/api` 가 필요하다 — `uv run` 은 프로젝트 루트에서 venv 를 찾는다(`:459`·`:536` 선례).
#   스크립트 경로는 절대경로라 `cd` 뒤에도 성립한다.
RESULT="$(printf '%s' "${PAYLOAD}" \
  | (cd "${ROOT}/apps/api" && uv run python "${ROOT}/apps/api/scripts/soak_gate_predicate.py"))"
RC=$?
# ★fail-closed. **rc 로 판정하지 마라** — `main()` 은 PASS=0 · FAIL=1 · 측정불가=2 를 돌려주므로
#   비-0 은 정상 판정이다. 「판정기가 죽었다」의 유일한 증거는 **출력이 비었다** 는 것이다.
if [ -z "${RESULT}" ]; then
  echo "✗ 판정기가 아무것도 내지 않았다 (rc=${RC}) — 빈 '판정:' 을 찍는 대신 여기서 멈춘다" >&2
  echo "  맥에서 3.9 로 떨어졌는지 확인해라: (cd ${ROOT}/apps/api && uv run python -V)" >&2
  exit 1
fi

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
if [ -z "${REQUIRE_HOURS}${REQUIRE_CONTINUOUS}${REQUIRE_WINDOWS}${SINCE}" ] && [ "${COLLECT}" = "1" ]; then
  printf '%s  %s %s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "${VERDICT}" "${WORD}" "${SUMMARY}" \
    > "${LOGDIR}/soak-gate-last-result"
fi

if [ -n "${REQUIRE_HOURS}${REQUIRE_CONTINUOUS}${REQUIRE_WINDOWS}" ]; then
  echo "⚠⚠ 문턱이 기본값이 아니다 (--require-hours='${REQUIRE_HOURS}' --require-continuous='${REQUIRE_CONTINUOUS}' --require-windows='${REQUIRE_WINDOWS}')"
  echo "   이 실행은 **자기시험**이다. 게이트 판정으로 인용하지 마라."
fi
if [ -n "${SINCE}" ]; then
  echo "⚠ 평가 창 시작을 강제했다 (--since ${SINCE}) — 기본 T0 가 아니다."
fi

printf '\n══ [BL-003] 소크 안정 게이트 ══\n'
# ★[BL-657] — 이 줄이 없으면 인용된 출력만 보고 로컬/서버를 가를 수 없다. 판정에는 참여하지 않는다.
printf '대상: %s %s/%s · docker %s · 실행 %s · 분류기 %s\n' \
  "${DB_CONTAINER}" "${DB_ADDR}" "${DB_NAME_SEEN}" "${DOCKER_ENDPOINT}" "$(hostname)" "${DB_ENV_TARGET}"
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


print("  %s C1 %.0fh 창    %d / %d회   (참고: 누적 %.4fh)" % (mark(c["C1_ok"]), c["C1_window_hours"], c["C1_qualifying_windows"], c["C1_required_windows"], c["C1_cumulative_hours"]))
print("  %s C2 최장 연속  %.4fh / %.0fh" % (mark(c["C2_ok"]), c["C2_longest_hours"], c["C2_required"]))
print("  %s C3 실격 사건  %d건" % (mark(c["C3_ok"]), len(c["C3_violations"])))
for v in c["C3_violations"][:5]:
    print("        · %s" % v)
print("  %s C4 표본 공백  %d건" % (mark(c["C4_ok"]), len(c["C4_sample_gaps"])))
for g in c["C4_sample_gaps"][:3]:
    print("        · %s" % g)
# ★[BL-653] — 「C3 실격 0」은 「정지가 없었다」가 아니다. 이 해상도보다 짧은 정체는 구조적으로 안 보인다.
res = d.get("sample_resolution")
if res:
    print(
        "        표본 해상도: %d건 · 간격 중앙 %.1f분/최대 %.1f분 (이보다 짧은 tick 정체는 판별 불가)"
        % (res["samples"], res["median_seconds"] / 60.0, res["max_seconds"] / 60.0)
    )
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

# ★귀속은 **보고 전용**이다 — 위 C1~C5 는 이 블록이 있든 없든 같은 값이다 ([BL-641]).
att = d.get("disqualification_attribution")
if att:
    n = att["counts"]
    print("  ★실격 귀속(보고 전용 · 판정 불참): 코드 결함 %d · 운영 사고 %d · 미판정 %d"
          % (n.get("code_defect", 0), n.get("operational", 0), n.get("undecided", 0)))
    if att["unregistered"]:
        print("        원장 미등재 %d건 — undecided 로 센다 "
              "(docs/reference/operations/soak-disqualifications.jsonl)" % len(att["unregistered"]))
    # ★「원장이 낡았다」로 단정하지 마라 ([BL-751], 2026-08-15). 이 판독은 **한 호스트의 DB**
    #   만 보고, 원장은 서버·로컬 맥 두 소크의 사건을 함께 담는다. 실제로 2026-08-15 판독이
    #   찍던 1건은 로컬 맥 세션(e9c504f1, 08-14T12:26 사망)이라 서버 DB 에 있을 수 없었다 —
    #   낡은 것이 아니라 **여기서 볼 수 없는 것**이다. 매 판독마다 거짓을 말하면 다음 사람이
    #   진짜 stale 을 만났을 때도 그 줄을 넘긴다.
    if att["stale_ledger_rows"]:
        print("        ⚠ 원장에 있으나 이 판독의 실격 목록에 없는 행 %d건 — "
              "다른 호스트의 소크이거나 원장이 낡은 것이다: %s"
              % (len(att["stale_ledger_rows"]), ", ".join(att["stale_ledger_rows"][:3])))
    if att["invalid_ledger_rows"]:
        print("        ⚠ 판독 불가 원장 행 %d건 — undecided 로 센다" % att["invalid_ledger_rows"])

# ★자격 판정 — 「지금 `up` 을 눌러도 되나」를 사람 머릿속이 아니라 여기서 답한다 ([BL-003]).
#   `up` 은 진행 중인 귀속 구간을 **닫는다**. 자격을 얻기 전에 누르면 그때까지 번 시간이
#   창 0회로 소멸한다 — 27.4h 를 돌리고도 C1 이 0/3 이던 2026-08-13 창이 그 값이다.
#   ★판독 전용이다. 이 스크립트는 `up` 을 누르지 않는다 — 여는 것은 사람의 명시적 행위로 남긴다.
el = d.get("window_eligibility")
if el:
    print()
    print("  ▶ 새 창을 열어도 되나 (판독 전용 — 누르는 것은 사람이다)")
    if not el["open"]:
        print("        ? 판정 불가 — 지금 열려 있는 귀속 구간이 없다.")
        print("          `soak-stack.sh up` 이 구간을 열기 전에는 시간이 계상되지 않는다.")
    elif el["disqualified_in_window"]:
        print("        ✗ 자격 없음 — 이 창 안에서 실격이 났다. 누적은 이미 0 으로 리셋됐다.")
        print("          지금 `up` 을 누르는 것이 곧 「인지했고 새 창을 연다」는 행위다.")
    elif el["qualified"]:
        print("        ✓ 자격 획득 — 연속 %.4fh ≥ %.0fh · 실격 0."
              % (el["longest_hours"], el["required_hours"]))
        print("          지금 `up` 을 눌러도 **손실 0** 이다 — 이 창은 자격 %d회로 확정돼 남는다."
              % el["at_risk_windows"])
    else:
        print("        ✗ 아직 자격 없음 — 연속 %.4fh / %.0fh · 남은 %.4fh"
              % (el["longest_hours"], el["required_hours"], el["remaining_hours"]))
        print("          지금 `up` 을 누르면 이 %.4fh 는 창 0회로 소멸한다." % el["at_risk_hours"])
        print("          지금 실격이 나면 잃는 것: 이 창 %.4fh + 확정된 자격 창 %d회"
              % (el["at_risk_hours"], el["at_risk_windows"]))
PY
rm -f "${RESULT_FILE}"
printf '\n종료 코드 %s  (0=PASS 만 · 1=FAIL · 2=UNKNOWN)\n' "${RC}"
exit "${RC}"
