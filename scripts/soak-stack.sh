#!/usr/bin/env bash
#
# 소크 스택 — 워커가 **고정된 커밋 스냅샷**을 돌게 한다. 그래야 `backend/src` 를 편집해도
# 돌고 있는 소크가 죽지 않고, 「이 사망이 어느 버전 것인가」에 답이 있다. ([BL-003] 게이트)
#
# 사용:
#   scripts/soak-stack.sh pin [<commitish>]   # .soak/src 를 그 커밋에서 다시 뜬다 (기본 HEAD)
#   scripts/soak-stack.sh up                  # 3층 compose 로 기동
#   scripts/soak-stack.sh down                # 3층 compose 로 내림
#   scripts/soak-stack.sh commit              # ★소크가 도는 커밋 — 프로세스 기준으로 조회
#   scripts/soak-stack.sh status              # 고정 여부 · 커밋 · 누락 커밋 · 활성 세션 · main 조상
#   scripts/soak-stack.sh ps                  # ★DB 를 안 건드리는 생존 확인 — 0 = 하나라도 running / 1 = 완전 down
#   scripts/soak-stack.sh assert-not-pinned   # Makefile 클로버 가드용 (고정본이 떠 있으면 1)
#
# 종료 코드: 0 = 정상 / 1 = 실패·거부 / 2 = 전제 미충족(측정 못 함)
#
# ★설계 근거 (전부 이 레포가 실제로 덴 것):
#   · **커밋되지 않은 코드를 소크하지 않는다.** `backend/src` 가 dirty 면 pin 을 거부한다 —
#     소크와 작업 트리가 갈리는 순간 「어느 버전이 죽었나」가 판정 비용이 된다.
#   · **파일의 증거와 프로세스의 증거를 구분한다.** `cat /app/src/__soak_commit__` 은
#     파일의 증거일 뿐이다. `commit` 은 **celery MainProcess 의 /proc/<pid>/root** 를 통해
#     읽고, 그 PID 의 시작 시각이 pin 기록 시각보다 뒤인지까지 본다.
#     (md5 일치는 파일의 증거이지 프로세스의 증거가 아니다 — 2026-08-04 교훈)
#   · **경로는 고정이다.** `${QB_SRC_ROOT}` 변수화는 2026-07-29 결정으로 기각됐다
#     (워크트리가 워커를 자기 src 로 돌리게 된다). 여기 내용은 git 커밋에서만 나온다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
STATE_DIR="${ROOT}/.soak"
SRC_DIR="${STATE_DIR}/src"
STAMP_FILE="${SRC_DIR}/__soak_commit__"
PIN_HISTORY="${STATE_DIR}/pin-history.jsonl"
DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
WORKER_CONTAINER="${QB_WORKER_CONTAINER:-quantbridge-worker}"
COMPOSE=(-f "${ROOT}/docker-compose.yml" -f "${ROOT}/docker-compose.isolated.yml" -f "${ROOT}/docker-compose.soak.yml")

# 소크 스택의 mount 인지 판정하는 지문. compose 가 상대경로를 절대경로로 펴므로 그 형태로 본다.
PINNED_MOUNT="${ROOT}/.soak/src"

die() { echo "✗ $1" >&2; exit "${2:-1}"; }

# 창(window) 경계의 SSOT. ★귀속 구간을 여는 것은 `pin` 이 아니라 **`up`** 이다 —
# 스냅샷을 다시 떠도 이미 돌고 있는 프로세스는 구 모듈을 쥐고 있다. `pin` 은 귀속이 흐려지는
# 시점이므로 **닫는다**. 판정은 backend/scripts/soak_gate_predicate.py 가 한다.
_record_event() {  # _record_event <pin|up|down> <sha> <ISO8601Z>
  mkdir -p "${STATE_DIR}"
  printf '{"event":"%s","sha":"%s","at":"%s"}\n' "$1" "$2" "$3" >> "${PIN_HISTORY}"
}

# 워커가 **실제로 일할 준비가 된** 시각 = celery 기동 배너의 타임스탬프.
#
# ★컨테이너 `StartedAt` 을 쓰면 안 된다 — 실측 2026-08-04: 컨테이너 15:51:22 vs celery
#   ready 15:53:57 로 **2.6분** 벌어진다(그 사이 `uv run` 이 환경을 동기화한다). 그 구간엔
#   아무것도 평가되지 않으므로 창에 넣으면 「돌고 있었다」를 과대계상한다.
# ★재적재 지문이 `watchfiles` 로그가 아니라 celery 배너인 것과 같은 이유다(2026-08-04 교훈).
_worker_ready_at() {  # _worker_ready_at <since ISO8601Z> — 없으면 빈 문자열
  docker logs --timestamps --since "$1" "${WORKER_CONTAINER}" 2>&1 \
    | grep -F 'celery.apps.worker celery@' | grep -F ' ready.' | tail -1 \
    | cut -d' ' -f1 | cut -c1-19 | sed 's/$/Z/'
}

# ------------------------------------------------------------------ 공통 조회

# celery MainProcess 의 PID. prefork 이므로 부모(가장 작은 celery PID)가 MainProcess 다.
# ★`$$` 를 건너뛴다 — 이 스캔 셸의 cmdline 에 매칭 패턴이 문자열로 들어 있어서 **자기 자신을
#   센다**(2026-08-04 실측: PID 집합에 유령 1개가 매번 끼어 "PID 가 바뀌었다"로 오독됐다).
_celery_main_pid() {
  docker exec "${WORKER_CONTAINER}" sh -c \
    'me=$$; for p in /proc/[0-9]*; do pid=${p#/proc/}; [ "$pid" = "$me" ] && continue; c=$(tr "\0" " " < $p/cmdline 2>/dev/null); case "$c" in *bin/celery*) echo "$pid";; esac; done' \
    2>/dev/null | sort -n | head -1
}

# 워커 컨테이너가 지금 `.soak/src` 를 mount 하고 있는가.
_stack_is_pinned() {
  local src
  src="$(docker inspect "${WORKER_CONTAINER}" \
    --format '{{range .Mounts}}{{if eq .Destination "/app/src"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)" || return 1
  [ "${src}" = "${PINNED_MOUNT}" ]
}

# ------------------------------------------------------------------ 누락 커밋 조회
#
# ★「origin/main 의 조상인가」와 「빠뜨린 수리가 있는가」는 **다른 질문**이다.
#   2026-08-07 서버 실측: 고정본 `0c9ccc68` 은 조상 YES 이면서 동시에 [BL-622] gap-resync
#   유예 수리(`175690a7`)를 통째로 빠뜨리고 있었다. `_status` 는 YES 만 말했고 운영자는
#   최신본이 도는 줄 알았다. 조상 여부는 **하한**이지 최신성의 증거가 아니다.
#
# 감시 경로의 근거 (2026-08-08 실측 · `0c9ccc68..origin/main` = 필터 없이 33커밋 → 9커밋):
#   · `backend/src`     — `_pin` 이 `git archive <sha> backend/src` 로 **실제로 스냅샷하는
#                         유일한 경로**. 여기가 낡으면 소크가 낡은 엔진을 돈다.
#   · `backend/scripts` — 판정자 `soak_gate_predicate.py` 가 산다. 고정본 `0c9ccc68` 자신이
#                         이 경로의 커밋이었다(parse_ts python 3.10 수리).
#   · `scripts`         — 게이트 본체 `soak-gate.sh` 와 이 파일이 산다.
#   `pin` 은 통상 HEAD 를 고정하므로 「고정 sha 뒤로 남은 커밋」은 곧 「이 체크아웃이
#   origin/main 보다 뒤처졌다」와 같다. 스냅샷(`backend/src`)과 판정기(`scripts` 2종)는
#   **같은 체크아웃**에서 나오므로 둘 다 본다. `docs/`·`frontend/` 는 뺀다 — 소크의 실행에도
#   판정에도 들어가지 않는다.
#   ★커밋 메시지 접두사로 거르지 마라 — 실측에서 `docs(...)` 2건이 `backend/src` 를 고쳤다.
SOAK_WATCHED_PATHS=(backend/src backend/scripts scripts)
# 운영자가 실제로 읽는 분량. 넘치면 개수만 말한다.
MISSING_LIST_LIMIT=20

# 고정 sha 이후 origin/main 에 들어온 감시 경로 커밋. 없으면 빈 출력 + 0.
# ★`origin/main` 을 못 읽으면(단일브랜치 클론 · 오프라인 · fetch 전) **재지 못한 것**이다.
#   빈 출력과 구분되도록 **2** 를 돌려준다 — 「빈 출력 + 0」만이 「없다」를 뜻한다.
#
# ★★★2026-08-08 적대 검증이 잡은 fail-open — **낡은 remote-tracking ref 는 조용히 통과한다.**
#   `origin/main` 은 로컬 ref 라 `git fetch` 없이는 갱신되지 않는데 이 레포의 어떤 스크립트도
#   fetch 를 하지 않는다. 실험으로 재현했다 — fetch **전** rc=0 무음 통과 / fetch **후** rc=1 거부.
#   즉 이 가드가 만들어진 계기(서버 체크아웃이 [BL-622] 수리를 빠뜨린 채 「조상: YES」였던 것)와
#   **같은 형상의 환경에서 여전히 통과**했다. ⇒ 재기 전에 **직접 fetch 한다.**
#   ★fetch 실패는 「0」이 아니라 「못 쟀다」(2)다 — 네트워크가 없다고 최신인 것이 아니다.
QB_SOAK_FETCH_TIMEOUT="${QB_SOAK_FETCH_TIMEOUT:-20}"

_missing_commits() {  # _missing_commits <sha> — 0 = 쟀다 / 2 = 못 쟀다
  local to
  # `timeout` 이 없으면(맥 기본) 붙이지 않는다 — 그래도 fetch 는 시도한다.
  to="$(command -v timeout || command -v gtimeout || true)"
  if [ -n "${to}" ]; then
    (cd "${ROOT}" && "${to}" "${QB_SOAK_FETCH_TIMEOUT}" git fetch --quiet origin main >/dev/null 2>&1) || return 2
  else
    (cd "${ROOT}" && git fetch --quiet origin main >/dev/null 2>&1) || return 2
  fi
  (cd "${ROOT}" && git rev-parse --verify --quiet origin/main >/dev/null 2>&1) || return 2
  (cd "${ROOT}" && git log --oneline "$1..origin/main" -- "${SOAK_WATCHED_PATHS[@]}" 2>/dev/null)
}

# 누락 목록을 운영자가 읽을 형태로 찍는다. 상한을 넘으면 나머지는 개수로 접는다.
_print_missing() {  # _print_missing <missing-text> <count>  ★stderr 로 보낼지는 호출부가 정한다
  printf '%s\n' "$1" | head -n "${MISSING_LIST_LIMIT}" | sed 's/^/    /'
  if [ "$2" -gt "${MISSING_LIST_LIMIT}" ]; then
    echo "    … 외 $(($2 - MISSING_LIST_LIMIT))개"
  fi
}

# 고정하려는 sha 뒤로 감시 경로 커밋이 남아 있으면 **거부**한다(호출부가 exit 2 를 낸다).
# ★탈출구는 `QB_SOAK_OVERRIDE=1` — 이 파일이 이미 쓰는 관례(`_pin` 의 재고정 가드,
#   `_assert_not_pinned`)를 그대로 따른다. 새 변수를 만들지 않는다.
# ★못 쟀을 때는 **통과**시킨다. 이건 게이트가 아니라 운영자 가드이고, 판정 불가를 차단으로
#   바꾸면 fetch 못 하는 환경에서 `pin` 이 통째로 불가능해진다(`assert-main-checkout.sh` 와
#   같은 판단). 대신 「0 이라는 뜻이 아니다」를 명시적으로 말한다.
_assert_no_missing_commits() {  # <sha> — 0 = 진행해도 된다 / 1 = 거부
  local sha="$1" missing rc count
  missing="$(_missing_commits "${sha}")"
  rc=$?
  if [ "${rc}" -eq 2 ]; then
    echo "⚠ origin/main 을 못 읽어 누락 커밋을 **재지 못했다** (0 이라는 뜻이 아니다)." >&2
    echo "  → 'git fetch origin main' 뒤 다시 해라." >&2
    return 0
  fi
  [ -n "${missing}" ] || return 0

  count="$(printf '%s\n' "${missing}" | wc -l | tr -d ' ')"
  if [ "${QB_SOAK_OVERRIDE:-0}" = "1" ]; then
    echo "⚠ QB_SOAK_OVERRIDE=1 — 누락 커밋 ${count}개를 알고도 고정한다." >&2
    _print_missing "${missing}" "${count}" >&2
    return 0
  fi
  echo "✗ 이 커밋 뒤로 origin/main 에 감시 경로 커밋이 ${count}개 남아 있다 — 낡은 코드를 소크하게 된다." >&2
  echo "  감시 경로: ${SOAK_WATCHED_PATHS[*]}" >&2
  echo "  빠진 것:" >&2
  _print_missing "${missing}" "${count}" >&2
  echo "  → 'git pull --ff-only origin main' 으로 따라잡은 뒤 다시 pin 해라." >&2
  echo "  → 그래도 이 커밋을 고정해야겠으면 QB_SOAK_OVERRIDE=1 을 붙여라." >&2
  return 1
}

# ------------------------------------------------------------------ pin

_pin() {
  local target="${1:-HEAD}"

  bash "${ROOT}/scripts/assert-main-checkout.sh" "soak-stack.sh pin" || exit 2

  # ★★돌고 있는 고정본 위에 다시 pin 하지 않는다.
  #   `.soak/src` 는 **실행 중 컨테이너의 bind mount 원본**이다. 제자리에서 지우고 다시 쓰면
  #   celery 는 이미 구 커밋 모듈을 메모리에 import 한 상태인데 stamp 만 새 SHA 가 된다 ⇒
  #   창이 B 로 기록되는데 실제로는 A(또는 A/B 혼합)가 돈다(codex P1).
  #   ★`commit` 은 파일의 증거일 뿐 import 의 증거가 아니므로 이 어긋남을 잡아내지 못한다.
  if [ "${QB_SOAK_OVERRIDE:-0}" != "1" ] && _stack_is_pinned && [ -n "$(_celery_main_pid)" ]; then
    echo "✗ 고정본 스택이 돌고 있다 — 그 위에 다시 pin 하면 기록 커밋과 실행 코드가 갈린다." >&2
    echo "  현재 고정: $(cut -d' ' -f1 "${STAMP_FILE}" 2>/dev/null || echo '?')" >&2
    echo "  → 'scripts/soak-stack.sh down' 으로 내린 뒤 pin 해라 (연속 창은 끊긴다)." >&2
    exit 2
  fi

  # ★커밋되지 않은 backend/src 를 소크하지 않는다. 이게 이 도구의 존재 이유의 절반이다.
  local dirty
  dirty="$(cd "${ROOT}" && git status --porcelain -- backend/src)"
  if [ -n "${dirty}" ]; then
    echo "✗ backend/src 가 dirty 하다 — 커밋되지 않은 코드를 소크할 수 없다." >&2
    echo "${dirty}" | sed 's/^/    /' >&2
    echo "  → 커밋한 뒤 다시 pin 해라. (소크가 도는 커밋이 조회 가능해야 한다)" >&2
    exit 2
  fi

  local sha branch subject now
  sha="$(cd "${ROOT}" && git rev-parse "${target}")" || die "커밋을 못 찾겠다: ${target}" 2
  branch="$(cd "${ROOT}" && git rev-parse --abbrev-ref HEAD)"
  subject="$(cd "${ROOT}" && git log -1 --format=%s "${sha}")"
  now="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  # ★「origin/main 의 조상」은 「최신」이 아니다 — 위 `_missing_commits` 주석의 실측 참조.
  #   여기서 거부해야 `rm -rf ${SRC_DIR}` 전에 멈춘다(스냅샷을 깨고 나서 알면 늦다).
  _assert_no_missing_commits "${sha}" || exit 2

  rm -rf "${SRC_DIR}"
  mkdir -p "${SRC_DIR}"
  # `git archive` 는 **추적된 파일만** 담는다. backend/src 의 미추적은 __pycache__ 뿐이고
  # 이미지가 PYTHONDONTWRITEBYTECODE=1 이라 없어도 된다(2026-08-04 실측).
  (cd "${ROOT}" && git archive "${sha}" backend/src) | tar -x --strip-components=2 -C "${SRC_DIR}" \
    || die "스냅샷 생성 실패" 1

  [ -f "${SRC_DIR}/tasks/celery_app.py" ] || die "스냅샷이 비었다 — tasks/celery_app.py 가 없다" 1

  printf '%s %s %s %s\n' "${sha}" "${now}" "${branch}" "${subject}" > "${STAMP_FILE}"
  _record_event pin "${sha}" "${now}"

  echo "✓ pin: ${sha}"
  echo "  시각   : ${now}"
  echo "  브랜치 : ${branch}"
  echo "  제목   : ${subject}"
  echo "  파일수 : $(find "${SRC_DIR}" -name '*.py' | wc -l | tr -d ' ')"
  echo "  ★스택이 이미 떠 있으면 반영되지 않는다 — 'soak-stack.sh up' 으로 재기동해라."
}

# ------------------------------------------------------------------ up / down

_up() {
  bash "${ROOT}/scripts/assert-main-checkout.sh" "soak-stack.sh up" || exit 2
  [ -f "${STAMP_FILE}" ] || die "고정본이 없다 — 먼저 'soak-stack.sh pin' 을 해라" 2
  mkdir -p "${ROOT}/backend/.metrics" && chmod 0777 "${ROOT}/backend/.metrics"

  # ★스택이 이미 고정본으로 돌고 있으면 **새 창만 연다.**
  #   실격 사건(사망·phantom·정체)은 그 창이 닫힐 때까지 FAIL 로 남는다 — 그래서 「인지했고
  #   다시 시작한다」는 **명시적 행위**가 필요하다. 그 행위가 이것이다. 워커를 재기동할 이유는
  #   없다(사망한 것은 라이브 세션이지 워커가 아니다) — 재기동은 4분짜리 uv 동기화를 부른다.
  local main_pid
  main_pid="$(_celery_main_pid)"
  if _stack_is_pinned && [ -n "${main_pid}" ]; then
    # ★그 프로세스가 **실제로 보는** stamp 가 파일의 stamp 와 같아야만 재사용한다.
    #   다르면 누군가 밑에서 스냅샷을 바꾼 것이고, 그대로 창을 열면 기록 커밋과 실행 코드가
    #   갈린 채 시간이 credit 된다(codex P1). 그 경우엔 재기동 경로로 떨어뜨린다.
    local proc_sha file_sha now_iso
    proc_sha="$(docker exec "${WORKER_CONTAINER}" cat "/proc/${main_pid}/root/app/src/__soak_commit__" 2>/dev/null | cut -d' ' -f1)"
    file_sha="$(cut -d' ' -f1 "${STAMP_FILE}")"
    if [ -n "${proc_sha}" ] && [ "${proc_sha}" = "${file_sha}" ]; then
      now_iso="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      _record_event up "${file_sha}" "${now_iso}"
      echo "✓ 기존 고정본 스택을 재사용하고 **새 창을 열었다** — ${now_iso}"
      echo "  커밋: ${file_sha}  (PID ${main_pid} 가 보는 값과 일치)"
      echo "  ★이전 창의 실격 사건은 이제 FAIL 을 만들지 않는다(누적은 0 에서 다시 센다)."
      return 0
    fi
    echo "⚠ 실행 중 프로세스가 보는 커밋(${proc_sha:-없음})이 고정본(${file_sha})과 다르다 — 재기동한다." >&2
  fi

  local since sha ready waited
  since="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  (cd "${ROOT}" && docker compose "${COMPOSE[@]}" up -d) || die "compose up 실패" 1
  sha="$(cut -d' ' -f1 "${STAMP_FILE}")"

  # ★배너를 기다린다 — `up -d` 는 컨테이너 생성만 기다리고 celery 준비는 안 기다린다.
  #   컨테이너가 새로 만들어지면 `uv run` 이 환경을 동기화하느라 실측 ~2.5분이 든다.
  echo "▶ celery 기동 배너 대기 (최대 600초) …"
  waited=0
  while [ "${waited}" -lt 600 ]; do
    ready="$(_worker_ready_at "${since}")"
    [ -n "${ready}" ] && break
    sleep 5
    waited=$((waited + 5))
  done
  if [ -z "${ready}" ]; then
    echo "✗ 600초 안에 celery 기동 배너가 없다 — 창을 열지 않는다(귀속 불가로 남긴다)." >&2
    echo "  docker logs ${WORKER_CONTAINER} 를 봐라." >&2
    exit 1
  fi

  _record_event up "${sha}" "${ready}"
  echo "✓ 소크 스택 기동 — ${sha}"
  echo "  창 시작(celery ready): ${ready}   [대기 ${waited}초]"
}

_down() {
  bash "${ROOT}/scripts/assert-main-checkout.sh" "soak-stack.sh down" || exit 2
  local sha
  sha="$(cut -d' ' -f1 "${STAMP_FILE}" 2>/dev/null || echo '-')"
  (cd "${ROOT}" && docker compose "${COMPOSE[@]}" down) || die "compose down 실패" 1
  _record_event down "${sha}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "✓ 소크 스택 내림"
}

# ------------------------------------------------------------------ commit — 프로세스의 증거

_commit() {
  local pid stamp_via_proc proc_start pinned_at
  pid="$(_celery_main_pid)"
  [ -n "${pid}" ] || die "celery MainProcess 를 못 찾았다 (컨테이너가 떠 있나?)" 2

  # ① 그 PID 가 보는 파일 — /proc/<pid>/root 는 그 프로세스의 mount namespace 를 통과한다.
  stamp_via_proc="$(docker exec "${WORKER_CONTAINER}" cat "/proc/${pid}/root/app/src/__soak_commit__" 2>/dev/null)"
  [ -n "${stamp_via_proc}" ] || die "PID ${pid} 가 보는 /app/src 에 __soak_commit__ 이 없다 — 고정본이 아니다" 2

  # ② 그 PID 의 시작 시각 (/proc/<pid> 디렉터리 mtime = 프로세스 생성 시각)
  proc_start="$(docker exec "${WORKER_CONTAINER}" sh -c "stat -c %y /proc/${pid}" 2>/dev/null)"
  pinned_at="$(printf '%s' "${stamp_via_proc}" | cut -d' ' -f2)"

  echo "${stamp_via_proc}"
  echo
  echo "── 이 값이 무엇의 증거인가 (합쳐 읽지 마라) ──"
  echo "  ① PID ${pid} 의 mount namespace 를 통해 읽었다 → **그 프로세스가 보는 /app/src** 의 증거"
  echo "  ② PID ${pid} 생성 시각 : ${proc_start}"
  echo "     pin 기록 시각        : ${pinned_at}  (①이 ②보다 앞서야 순서가 맞다)"
  echo "  ★증명하지 않는 것: 그 프로세스가 이 파일들을 실제로 import 했는지는 별도다."
  echo "    (파일은 있는데 구 모듈이 메모리에 남아 있을 가능성은 재기동 순서로만 배제된다)"
}

# ------------------------------------------------------------------ status

_status() {
  echo "── 스택 ──"
  if _stack_is_pinned; then
    echo "  고정본 (soak) — /app/src ← ${PINNED_MOUNT}"
  else
    local src
    src="$(docker inspect "${WORKER_CONTAINER}" \
      --format '{{range .Mounts}}{{if eq .Destination "/app/src"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)"
    echo "  고정본 아님 — /app/src ← ${src:-(mount 없음/컨테이너 없음)}"
  fi

  echo "── 고정 커밋 ──"
  if [ -f "${STAMP_FILE}" ]; then
    cat "${STAMP_FILE}" | sed 's/^/  /'
    local sha
    sha="$(cut -d' ' -f1 "${STAMP_FILE}")"
    if (cd "${ROOT}" && git merge-base --is-ancestor "${sha}" origin/main 2>/dev/null); then
      echo "  origin/main 의 조상: YES — 소크가 도는 코드는 main 에 있다"
    else
      echo "  origin/main 의 조상: NO — 아직 main 에 없는 코드를 소크 중이다"
    fi
    # ★조상이어도 최신은 아니다. 「그 뒤로 무엇이 들어왔나」를 함께 찍는다.
    local missing rc count
    missing="$(_missing_commits "${sha}")"
    rc=$?
    if [ "${rc}" -eq 2 ]; then
      echo "  누락 커밋: 측정 못 함 — origin/main 을 못 읽었다 (0 이라는 뜻이 아니다)"
    elif [ -z "${missing}" ]; then
      echo "  누락 커밋: 0개 — 감시 경로(${SOAK_WATCHED_PATHS[*]})는 origin/main 과 같다"
    else
      count="$(printf '%s\n' "${missing}" | wc -l | tr -d ' ')"
      echo "  누락 커밋: ${count}개 — 감시 경로(${SOAK_WATCHED_PATHS[*]})"
      _print_missing "${missing}" "${count}"
    fi
  else
    echo "  (없음)"
  fi

  echo "── 활성 라이브 세션 ──"
  local active
  active="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc \
    "SELECT count(*) FROM trading.live_signal_sessions WHERE deactivated_at IS NULL;" 2>/dev/null || echo "?")"
  echo "  ${active}"
}

# ------------------------------------------------------------------ ps

_ps() {
  # 스택이 **살아 있나** — 종료 코드가 답이다 (0 = 하나라도 running / 1 = 완전 down) ([BL-656]).
  #
  # ★`status` 로는 이 질문에 답할 수 없다 — 그쪽은 DB 에 `psql` 을 쏘고(down 이면 실패) 산문을
  #   낸다. 재기동 스크립트가 갈래를 고르려면 **파싱 없는 종료 코드**가 필요하다.
  # ★「하나라도 running」이 기준인 이유 — 완전 down 만이 `pin → up` **선행**을 요구한다.
  #   반쯤 떠 있으면 종전 경로(`down → pin → up`)가 그대로 맞다. `down` 이 잔여를 치운다.
  local any=1 name state
  for name in "${DB_CONTAINER}" "${WORKER_CONTAINER}"; do
    state="$(docker inspect "${name}" --format '{{.State.Status}}' 2>/dev/null)"
    echo "  ${name}: ${state:-(없음)}"
    [ "${state}" = "running" ] && any=0
  done
  return "${any}"
}

# ------------------------------------------------------------------ 가드

_assert_not_pinned() {
  if [ "${QB_SOAK_OVERRIDE:-0}" = "1" ]; then
    echo "⚠ QB_SOAK_OVERRIDE=1 — 고정본 스택 보호를 건너뛴다." >&2
    exit 0
  fi
  if _stack_is_pinned; then
    echo "✗ 지금 떠 있는 것은 **소크 고정본 스택**이다 — 이 타깃은 그것을 덮어써 소크를 끊는다." >&2
    echo "  고정 커밋: $(cut -d' ' -f1 "${STAMP_FILE}" 2>/dev/null || echo '?')" >&2
    echo "  → 소크를 끝낼 생각이면 'scripts/soak-stack.sh down' 을 먼저 해라." >&2
    echo "  → 정말 덮어쓰려면 QB_SOAK_OVERRIDE=1 을 붙여라." >&2
    exit 1
  fi
  exit 0
}

# ------------------------------------------------------------------ dispatch

case "${1:-}" in
  pin)               shift; _pin "${1:-HEAD}" ;;
  up)                _up ;;
  down)              _down ;;
  commit)            _commit ;;
  status)            _status ;;
  ps)                _ps ;;
  assert-not-pinned) _assert_not_pinned ;;
  -h|--help)         sed -n '2,26p' "$0" ;;
  *) echo "알 수 없는 인자: ${1:-(없음)} (pin / up / down / commit / status / ps / assert-not-pinned)" >&2; exit 1 ;;
esac
