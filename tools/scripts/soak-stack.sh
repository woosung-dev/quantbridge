#!/usr/bin/env bash
#
# 소크 스택 — 워커가 **고정된 커밋 스냅샷**을 돌게 한다. 그래야 `apps/api/src` 를 편집해도
# 돌고 있는 소크가 죽지 않고, 「이 사망이 어느 버전 것인가」에 답이 있다. ([BL-003] 게이트)
#
# 사용:
#   tools/scripts/soak-stack.sh pin [<commitish>]   # .soak/src 를 그 커밋에서 다시 뜬다 (기본 HEAD)
#   tools/scripts/soak-stack.sh up                  # 3층 compose 로 기동
#   tools/scripts/soak-stack.sh down                # 3층 compose 로 내림
#   tools/scripts/soak-stack.sh migrate [--confirm] # ★소크 DB 에 alembic head 적용 (기본 dry-run)
#   tools/scripts/soak-stack.sh commit              # ★소크가 도는 커밋 — 프로세스 기준으로 조회
#   tools/scripts/soak-stack.sh status              # 고정 여부 · 커밋 · 누락 커밋 · 활성 세션 · main 조상
#   tools/scripts/soak-stack.sh ps                  # ★DB 를 안 건드리는 생존 확인 — 0 = 하나라도 running / 1 = 완전 down
#   tools/scripts/soak-stack.sh assert-not-pinned   # Makefile 클로버 가드용 (고정본이 떠 있으면 1)
#
# 종료 코드: 0 = 정상 / 1 = 실패·거부 / 2 = 전제 미충족(측정 못 함)
#
# ★설계 근거 (전부 이 레포가 실제로 덴 것):
#   · **커밋되지 않은 코드를 소크하지 않는다.** `apps/api/src` 가 dirty 면 pin 을 거부한다 —
#     소크와 작업 트리가 갈리는 순간 「어느 버전이 죽었나」가 판정 비용이 된다.
#   · **파일의 증거와 프로세스의 증거를 구분한다.** `cat /app/src/__soak_commit__` 은
#     파일의 증거일 뿐이다. `commit` 은 **celery MainProcess 의 /proc/<pid>/root** 를 통해
#     읽고, 그 PID 의 시작 시각이 pin 기록 시각보다 뒤인지까지 본다.
#     (md5 일치는 파일의 증거이지 프로세스의 증거가 아니다 — 2026-08-04 교훈)
#   · **경로는 고정이다.** `${QB_SRC_ROOT}` 변수화는 2026-07-29 결정으로 기각됐다
#     (워크트리가 워커를 자기 src 로 돌리게 된다). 여기 내용은 git 커밋에서만 나온다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
STATE_DIR="${ROOT}/.soak"
SRC_DIR="${STATE_DIR}/src"
STAMP_FILE="${SRC_DIR}/__soak_commit__"
PIN_HISTORY="${STATE_DIR}/pin-history.jsonl"
DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
WORKER_CONTAINER="${QB_WORKER_CONTAINER:-quantbridge-worker}"
COMPOSE=(--project-directory "${ROOT}" -f "${ROOT}/infra/compose/docker-compose.yml" -f "${ROOT}/infra/compose/docker-compose.isolated.yml" -f "${ROOT}/infra/compose/docker-compose.soak.yml")

# 소크 스택의 mount 인지 판정하는 지문. compose 가 상대경로를 절대경로로 펴므로 그 형태로 본다.
PINNED_MOUNT="${ROOT}/.soak/src"

die() { echo "✗ $1" >&2; exit "${2:-1}"; }

# 창(window) 경계의 SSOT. ★귀속 구간을 여는 것은 `pin` 이 아니라 **`up`** 이다 —
# 스냅샷을 다시 떠도 이미 돌고 있는 프로세스는 구 모듈을 쥐고 있다. `pin` 은 귀속이 흐려지는
# 시점이므로 **닫는다**. 판정은 apps/api/scripts/soak_gate_predicate.py 가 한다.
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
#   · `apps/api/src`     — `_pin` 이 `git archive <sha> apps/api/src` 로 **실제로 스냅샷하는
#                         유일한 경로**. 여기가 낡으면 소크가 낡은 엔진을 돈다.
#   · `apps/api/scripts` — 판정자 `soak_gate_predicate.py` 가 산다. 고정본 `0c9ccc68` 자신이
#                         이 경로의 커밋이었다(parse_ts python 3.10 수리).
#   · `tools/scripts`   — 게이트 본체 `soak-gate.sh` 와 이 파일이 산다.
#   · `apps/api/alembic` — DB 스키마. `pin` 이 **안 뜨는** 경로이므로 더더욱 감시가 필요하다
#                          (적용 수단은 `soak-stack.sh migrate` — [BL-743]).
#   `pin` 은 통상 HEAD 를 고정하므로 「고정 sha 뒤로 남은 커밋」은 곧 「이 체크아웃이
#   origin/main 보다 뒤처졌다」와 같다. 스냅샷(`apps/api/src`)과 판정기(`scripts` 2종)는
#   **같은 체크아웃**에서 나오므로 둘 다 본다. `docs/`·`apps/web/` 는 뺀다 — 소크의 실행에도
#   판정에도 들어가지 않는다.
#   ★커밋 메시지 접두사로 거르지 마라 — 실측에서 `docs(...)` 2건이 `apps/api/src` 를 고쳤다.
#
# ★★2026-08-15 실측 — 이 목록 자체가 **두 곳에서 침묵하고 있었다** ([BL-743] 곁가지):
#   ⑴ `scripts` 는 [ADR-029] 재배치(2026-08-13)로 **존재하지 않는 경로**가 됐다. 게이트
#      스크립트 변경을 감시하는 축이 그날부터 조용히 죽어 있었다 — 없는 경로의
#      `git log -- <path>` 는 오류가 아니라 **빈 출력**이라 「누락 없음」과 구분되지 않는다.
#   ⑵ `apps/api/alembic` 이 처음부터 없어서, 서버 DB 가 head 보다 뒤처진 채로도
#      「누락 커밋 0개」가 나왔다.
SOAK_WATCHED_PATHS=(apps/api/src apps/api/scripts tools/scripts apps/api/alembic)
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

# ------------------------------------------------- 워커 이미지 신선도
#
# ★**왜 있나** — 2026-08-30 실측: 서버 워커 이미지가 **3주간 낡아** `openai` 가 없었고
#   제거된 Clerk 시절 패키지(`python-jose`·`clerk-backend-api`)를 아직 갖고 있었다.
#   `pin` 이 바꾸는 것은 `.soak/src` 뿐이고 **의존성은 이미지에 구워져 있다.**
#   compose 4서비스에 `image:` 태그가 없고 `up` 은 `--build` 를 안 쓰므로 **재빌드는
#   아무도 안 한다** — 새 런타임 의존성은 사람이 손으로 재빌드하기 전까지 워커에 닿지 않는다.
#   그 드리프트를 잡은 것은 감사 중의 우연이었다. 그래서 판정을 코드로 옮긴다.
#
# ★**3값이다** — `same` / `stale` / **`unknown`**. 이미지를 못 읽었을 때 `same` 으로 접으면
#   낡은 이미지를 「최신」이라 말하게 된다. 「못 봤다」를 「없다」로 접지 마라.

_sha256() {  # _sha256 <file> — stdout = hex. 못 읽으면 빈 문자열 + rc=1
  [ -f "$1" ] || return 1
  if command -v sha256sum > /dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

_worker_image() {  # compose 가 짓는 이름과 같은 규칙(<project>-<service>). project = ROOT 의 basename
  echo "${QB_WORKER_IMAGE:-$(basename "${ROOT}")-backend-worker}"
}

_image_freshness() {  # stdout: "<same|stale|unknown> <image-sha> <repo-sha>"
  local img repo
  repo="$(_sha256 "${ROOT}/apps/api/uv.lock")" || repo=""
  # ★`--network none` — 판정이 네트워크를 타면 안 된다. `--entrypoint ""` 로 role 분기를 건너뛴다.
  img="$(docker run --rm --network none --entrypoint "" "$(_worker_image)" \
    sha256sum /app/uv.lock 2> /dev/null | cut -d' ' -f1)"
  if [ -z "${img}" ] || [ -z "${repo}" ]; then
    printf 'unknown %s %s\n' "${img:--}" "${repo:--}"
  elif [ "${img}" = "${repo}" ]; then
    printf 'same %s %s\n' "${img}" "${repo}"
  else
    printf 'stale %s %s\n' "${img}" "${repo}"
  fi
}

_print_image_freshness() {  # 출력 fd 는 호출부가 정한다
  local line state img repo
  line="$(_image_freshness)"
  state="$(printf '%s' "${line}" | cut -d' ' -f1)"
  img="$(printf '%s' "${line}" | cut -d' ' -f2)"
  repo="$(printf '%s' "${line}" | cut -d' ' -f3)"
  case "${state}" in
    same)
      echo "  이미지 의존성: 레포 uv.lock 과 동일 (${img:0:12})"
      ;;
    stale)
      echo "  이미지 의존성: ★낡았다 — 이미지 ${img:0:12} ≠ 레포 ${repo:0:12}"
      echo "    워커는 이미지에 구워진 venv 로 돈다. 새 런타임 의존성은 재빌드 전까지 안 닿는다."
      echo "    재빌드: docker compose --project-directory \"\${PWD}\" \\"
      echo "              -f infra/compose/docker-compose.yml \\"
      echo "              -f infra/compose/docker-compose.isolated.yml \\"
      echo "              -f infra/compose/docker-compose.soak.yml \\"
      echo "              build backend-worker backend-ws-stream backend-optimizer-heavy backend-beat"
      ;;
    *)
      echo "  이미지 의존성: 측정 못 함 — 이미지($(_worker_image))를 못 읽었다"
      echo "    ★이것은 「동일하다」가 아니다. 이미지가 없거나 docker 를 못 부른 것이다."
      ;;
  esac
}

_warn_if_image_not_fresh() {  # same 이 아닐 때만 stderr 로 찍는다
  local state
  state="$(_image_freshness | cut -d' ' -f1)"
  [ "${state}" = "same" ] && return 0
  {
    echo
    echo "── 워커 이미지 신선도 ──"
    _print_image_freshness
  } >&2
}

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

  bash "${ROOT}/tools/scripts/assert-main-checkout.sh" "soak-stack.sh pin" || exit 2

  # ★★돌고 있는 고정본 위에 다시 pin 하지 않는다.
  #   `.soak/src` 는 **실행 중 컨테이너의 bind mount 원본**이다. 제자리에서 지우고 다시 쓰면
  #   celery 는 이미 구 커밋 모듈을 메모리에 import 한 상태인데 stamp 만 새 SHA 가 된다 ⇒
  #   창이 B 로 기록되는데 실제로는 A(또는 A/B 혼합)가 돈다(codex P1).
  #   ★`commit` 은 파일의 증거일 뿐 import 의 증거가 아니므로 이 어긋남을 잡아내지 못한다.
  if [ "${QB_SOAK_OVERRIDE:-0}" != "1" ] && _stack_is_pinned && [ -n "$(_celery_main_pid)" ]; then
    echo "✗ 고정본 스택이 돌고 있다 — 그 위에 다시 pin 하면 기록 커밋과 실행 코드가 갈린다." >&2
    echo "  현재 고정: $(cut -d' ' -f1 "${STAMP_FILE}" 2>/dev/null || echo '?')" >&2
    echo "  → 'tools/scripts/soak-stack.sh down' 으로 내린 뒤 pin 해라 (연속 창은 끊긴다)." >&2
    exit 2
  fi

  # ★커밋되지 않은 apps/api/src 를 소크하지 않는다. 이게 이 도구의 존재 이유의 절반이다.
  local dirty
  dirty="$(cd "${ROOT}" && git status --porcelain -- apps/api/src)"
  if [ -n "${dirty}" ]; then
    echo "✗ apps/api/src 가 dirty 하다 — 커밋되지 않은 코드를 소크할 수 없다." >&2
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
  # `git archive` 는 **추적된 파일만** 담는다. apps/api/src 의 미추적은 __pycache__ 뿐이고
  # 이미지가 PYTHONDONTWRITEBYTECODE=1 이라 없어도 된다(2026-08-04 실측).
  # ★strip-components 는 아카이브 경로의 **단 수**다 — apps/api/src = 3 (구 backend/src = 2).
  #   ADR-029 재배치 롤아웃에서 2 로 남아 「스냅샷이 비었다」로 실측 발화(2026-08-13 소크 서버).
  (cd "${ROOT}" && git archive "${sha}" apps/api/src) | tar -x --strip-components=3 -C "${SRC_DIR}" \
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
  if [ "$(uname)" = "Darwin" ] && [ "${QB_SOAK_ALLOW_DARWIN:-0}" != "1" ]; then
    die "macOS는 잠들어 celery beat가 진행되지 않는다 — 소크 정본은 서버다. 서버에서 실행하거나 QB_SOAK_ALLOW_DARWIN=1로 명시적으로 우회해라" 2
  fi
  bash "${ROOT}/tools/scripts/assert-main-checkout.sh" "soak-stack.sh up" || exit 2
  [ -f "${STAMP_FILE}" ] || die "고정본이 없다 — 먼저 'soak-stack.sh pin' 을 해라" 2
  mkdir -p "${ROOT}/apps/api/.metrics" && chmod 0777 "${ROOT}/apps/api/.metrics"

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
      _warn_if_image_not_fresh
      return 0
    fi
    echo "⚠ 실행 중 프로세스가 보는 커밋(${proc_sha:-없음})이 고정본(${file_sha})과 다르다 — 재기동한다." >&2
  fi

  local since sha ready waited
  since="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  (cd "${ROOT}" && docker compose "${COMPOSE[@]}" up -d) || die "compose up 실패" 1
  sha="$(cut -d' ' -f1 "${STAMP_FILE}")"

  # ★배너를 기다린다 — `up -d` 는 컨테이너 생성만 기다리고 celery 준비는 안 기다린다.
  #   ★2026-08-30 정정 — 종전 주석은 「컨테이너가 새로 만들어지면 `uv run` 이 환경을
  #   동기화하느라 실측 ~2.5분」이었다. PR #861 이 그 `uv run` 을 지웠다(기동마다 dev 28개를
  #   PyPI 에서 받고 있었다). 이제 배너는 수 초 안에 뜬다 — 600초 상한은 여유로 남긴다.
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
  # ★마지막에 찍는다 — 성공 줄 **위**에 있으면 스크롤에 밀려 아무도 안 읽는다.
  _warn_if_image_not_fresh
}

_down() {
  bash "${ROOT}/tools/scripts/assert-main-checkout.sh" "soak-stack.sh down" || exit 2
  local sha
  sha="$(cut -d' ' -f1 "${STAMP_FILE}" 2>/dev/null || echo '-')"
  (cd "${ROOT}" && docker compose "${COMPOSE[@]}" down) || die "compose down 실패" 1
  _record_event down "${sha}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "✓ 소크 스택 내림"
}

# ------------------------------------------------------------------ migrate — 스키마 배포
#
# ★**소크 스택에는 migration 적용 단계가 아예 없었다** ([BL-743], 2026-08-15).
#   ⑴ `_pin` 은 `git archive <sha> apps/api/src` 하나만 뜬다(:215) — `alembic/` 은 그 밖이다.
#   ⑵ 소크 compose 6서비스에 **api 롤이 없다.** `run_alembic_with_lock` 을 부르는 유일한 롤이
#      그것인데(`apps/api/docker-entrypoint.sh:77`), celery 서비스는 `command:` override 로
#      롤 분기를 통째로 우회한다(같은 파일 `:117` passthrough).
#   ⇒ 서버 DB 는 만들어진 시점에 멈춰 있었다. migration 이 squash base 하나뿐이던 동안은
#      아무도 몰랐고, 두 번째가 들어오자 드러났다(로컬 20260815_0001 vs 서버 20260801_0001).
#
# ★왜 `up` 에 붙이지 않았나 — 그러면 **창 중 DDL 이 암묵적으로** 돌고 「무엇이 언제 스키마를
#   바꿨나」에 답할 수 없게 된다. `pin` 과 같은 등급의 **명시적 배포 행위**로 둔다.
#   비목표 문구도 그 선을 긋는다(`docs/status.md` ⓵): 생성·로컬 적용은 자유, **서버 적용만 승인**.
# ★기본은 dry-run 이다(`soak-restart.sh` 와 같은 문형). 집행은 `--confirm`.
_migrate() { # _migrate [--confirm]
  local confirm="${1:-}" cur head pending rc after hist_rc dburl pub pub_port
  # ★여분 인자를 삼키지 마라 (codex P2) — `migrate --confirm --typo` 가 조용히 집행되면
  #   운영자는 자기가 준 가드가 걸린 줄 안다. 확인 게이트가 있는 명령일수록 엄격해야 한다.
  case "${confirm}" in
    "" | --confirm) ;;
    *) die "알 수 없는 인자: ${confirm}  (migrate [--confirm])" 1 ;;
  esac
  bash "${ROOT}/tools/scripts/assert-main-checkout.sh" "soak-stack.sh migrate" || exit 2

  cur="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge \
    -Atc "SELECT version_num FROM alembic_version;" 2>/dev/null)"
  [ -n "${cur}" ] || die "DB 의 alembic_version 을 못 읽었다 (${DB_CONTAINER}) — 전제 미충족" 2

  head="$(cd "${ROOT}/apps/api" && uv run alembic heads 2>/dev/null | awk 'NR==1{print $1}')"
  [ -n "${head}" ] || die "레포의 alembic head 를 못 읽었다 — uv/alembic 을 확인해라" 2

  echo "── 소크 DB 스키마 ──"
  echo "  대상       : ${DB_CONTAINER} / quantbridge"
  echo "  현재 revision: ${cur}"
  echo "  레포 head   : ${head}"

  if [ "${cur}" = "${head}" ]; then
    echo "✓ 이미 head 다 — 할 일이 없다."
    return 0
  fi

  # ★`alembic history -r A:B` 는 **A 를 포함**한다 — 즉 `A` 로 *끝나는* 전이(= 이미 적용된 것)가
  #   목록에 끼어든다. 2026-08-15 초판이 그래서 「적용 대기 2 항목」을 찍었는데 실제 대기는 1개였다.
  #   출력은 최신순이므로 `<cur> -> …` 줄까지가 정확히 대기분이고 그 아래는 이미 적용된 것이다.
  # ★★fail-closed — history 가 실패하면(DB revision 이 이 체크아웃의 이력에 없는 경우 등)
  #   **0 항목으로 보인다.** 그것은 「적용할 게 없다」가 아니라 **재지 못한 것**이다(codex P2).
  pending="$(cd "${ROOT}/apps/api" && uv run alembic history -r "${cur}:${head}" 2>&1)"
  hist_rc=$?
  if [ "${hist_rc}" -ne 0 ] || [ -z "${pending}" ]; then
    echo "${pending}" | sed 's/^/    /' >&2
    die "alembic history 를 못 읽었다 (rc=${hist_rc}) — DB revision '${cur}' 이 이 체크아웃의 이력에 없을 수 있다" 2
  fi
  pending="$(printf '%s\n' "${pending}" | awk -v c="${cur}" '{print} $1==c && $2=="->" {exit}')"
  echo "  적용 대기   : $(printf '%s\n' "${pending}" | grep -c '.') 항목"
  printf '%s\n' "${pending}" | sed 's/^/    /'

  # ★**upgrade 대상이 정말 그 DB 인가를 미리 잰다** (codex P1). 사후 재확인만으로는 부족하다 —
  #   `.env.local` 이 다른 DB 를 가리키고 있으면 그 DB 를 **먼저 바꾼 뒤에야** 사후 검사가
  #   실패하고, 그 DDL 은 되돌릴 수 없다. 그래서 published endpoint 로 사전 대조한다.
  dburl="$(sed -n 's/^[[:space:]]*DATABASE_URL=//p' "${ROOT}/apps/api/.env.local" | tail -1)"
  [ -n "${dburl}" ] || die "apps/api/.env.local 에 DATABASE_URL 이 없다" 2
  pub="$(docker port "${DB_CONTAINER}" 5432/tcp 2>/dev/null | head -1)"   # 예: 127.0.0.1:5433
  pub_port="${pub##*:}"
  [ -n "${pub_port}" ] || die "${DB_CONTAINER} 의 published port 를 못 읽었다" 2
  case "${dburl}" in
    *":${pub_port}/"*) ;;
    *) die "DATABASE_URL 이 ${DB_CONTAINER}(:${pub_port}) 를 가리키지 않는다 — 다른 DB 에 DDL 이 갈 뻔했다" 1 ;;
  esac
  echo "  적용 대상   : DATABASE_URL 이 :${pub_port} (= ${DB_CONTAINER}) 를 가리킨다 ✓"

  if [ "${confirm}" != "--confirm" ]; then
    echo
    echo "★ dry-run 이다 — 아무것도 바꾸지 않았다. 집행하려면 --confirm."
    echo "  ★이것은 pin 과 같은 등급의 배포 행위다. 서버 적용은 **사용자 승인**이 선행이다."
    return 0
  fi

  echo
  echo "▶ alembic upgrade head (advisory lock) …"
  # ★`.env.local` 을 **통째** 소싱한다 — DATABASE_URL 단독 주입은 이 레포의 금지 형태다.
  # ★맨 `alembic upgrade head` 를 부르지 않는다 — 레포에 이미 advisory lock 래퍼가 있고
  #   `docker-entrypoint.sh:52-55` 가 같은 것을 쓴다. 맨 호출은 alembic 의 session 시작 전
  #   race window 를 그대로 연다(codex P1). 같은 lock key 를 쓰므로 entrypoint 경로와도 배타적이다.
  (cd "${ROOT}/apps/api" && set -a && . ./.env.local && set +a \
    && uv run python -m src.scripts.run_alembic_with_lock \
      --lock-key "${ALEMBIC_ADVISORY_LOCK_KEY:-1903723824}" --timeout "${ALEMBIC_LOCK_TIMEOUT_S:-30}")
  rc=$?
  [ "${rc}" -eq 0 ] || die "alembic upgrade 실패 (rc=${rc})" 1

  # ★결정적 검증 — **게이트가 보는 그 DB** 를 다시 읽는다. 사전 대조를 통과했더라도
  #   여기서 한 번 더 본다(사전=선언, 사후=실측).
  after="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge \
    -Atc "SELECT version_num FROM alembic_version;" 2>/dev/null)"
  if [ "${after}" != "${head}" ]; then
    die "적용 후에도 ${DB_CONTAINER} 가 ${after:-없음} 다 (기대 ${head}) — 다른 DB 에 적용됐다" 1
  fi
  echo "✓ ${cur} → ${after}  (${DB_CONTAINER} 에서 재확인)"
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

  echo "── 워커 이미지 신선도 ──"
  _print_image_freshness

  echo "── 활성 라이브 세션 ──"
  local active
  active="$(docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc \
    "SELECT count(*) FROM trading.live_signal_sessions WHERE deactivated_at IS NULL;" 2>/dev/null || echo "?")"
  echo "  ${active}"
}

# ------------------------------------------------------------------ ps

_ps() {
  # 스택이 **살아 있나** — 종료 코드가 답이다 ([BL-656]).
  #   0 = 하나라도 running / 1 = 완전 down / **2 = 못 쟀다**(데몬에 못 닿는다).
  #
  # ★`status` 로는 이 질문에 답할 수 없다 — 그쪽은 DB 에 `psql` 을 쏘고(down 이면 실패) 산문을
  #   낸다. 재기동 스크립트가 갈래를 고르려면 **파싱 없는 종료 코드**가 필요하다.
  # ★「하나라도 running」이 기준인 이유 — 완전 down 만이 `pin → up` **선행**을 요구한다.
  #   반쯤 떠 있으면 종전 경로(`down → pin → up`)가 그대로 맞다. `down` 이 잔여를 치운다.
  #
  # ★★★**2 가 없으면 이 함수는 fail-open 이다** (2026-08-09 CONTROL 통합 리뷰에서 실측).
  #   `docker inspect` 는 「데몬에 못 닿는다」와 「그런 컨테이너가 없다」를 **둘 다 exit 1** 로 낸다
  #   — 구분이 불가능하다. 그래서 `DOCKER_HOST` 나 docker context 가 어긋나면 **살아 있는 스택이
  #   「완전 down」으로 보인다.** 그 오독은 `soak-restart.sh` 에서 `down` 을 건너뛰고 곧장 `pin` 을
  #   부르는데, `_pin` 의 보호(`:182` 「돌고 있는 고정본 위엔 pin 금지」)는 `_stack_is_pinned`
  #   ·`_celery_main_pid` 로 판정하고 **그 둘도 같은 docker 로 간다** ⇒ 탐지기가 틀린 바로 그
  #   조건에서 가드도 함께 눈이 먼다. **한 실패 모드가 탐지와 보호를 동시에 끈다.**
  #   결과는 `.soak/src` 를 **살아 있는 컨테이너의 bind mount 원본 자리에서 덮어쓰는 것**이고,
  #   그건 `:177-187` 이 P1 이라고 적어 둔 바로 그 사고다(창은 B 로 기록되는데 실제로는 A 가 돈다).
  #   ★이 레포에 전례가 있다 — 클라우드 이관에서 `DOCKER_HOST` 원격 때문에 `stack_pinned` 가
  #   영구 false 였다. 가정이 아니라 이미 밟은 조건이다.
  #   ★종전 경로에는 이 구멍이 없었다 — 항상 `down` 을 먼저 했고 docker 가 죽어 있으면 그 `down`
  #   이 실패해 die 했다(fail-closed). 구멍은 「완전 down 갈래」와 함께 새로 생겼다.
  # ★판별자는 `docker version` 이다 — 서버 필드를 물으므로 **데몬 도달성만** 잰다
  #   (실측: 도달 불가 exit 1 · 정상 exit 0 · 없는 컨테이너로는 흔들리지 않는다).
  if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    echo "  ✗ docker 데몬에 못 닿는다 — 스택 생존을 **측정하지 못했다**" >&2
    echo "    DOCKER_HOST=${DOCKER_HOST:-(미설정)} · context=$(docker context show 2>/dev/null || echo '?')" >&2
    echo "    → 이것을 '완전 down' 으로 읽으면 살아 있는 스택 위에 pin 이 떨어진다. 부르는 쪽은 멈춰라." >&2
    return 2
  fi
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
    echo "  → 소크를 끝낼 생각이면 'tools/scripts/soak-stack.sh down' 을 먼저 해라." >&2
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
  migrate)           shift; [ "$#" -le 1 ] || die "인자가 너무 많다: $* (migrate [--confirm])" 1; _migrate "${1:-}" ;;
  commit)            _commit ;;
  status)            _status ;;
  ps)                _ps ;;
  assert-not-pinned) _assert_not_pinned ;;
  -h|--help)         sed -n '2,26p' "$0" ;;
  *) echo "알 수 없는 인자: ${1:-(없음)} (pin / up / down / migrate / commit / status / ps / assert-not-pinned)" >&2; exit 1 ;;
esac
