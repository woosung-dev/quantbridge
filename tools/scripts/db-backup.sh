#!/usr/bin/env bash
#
# QuantBridge DB 무인 백업 — pg_dump 커스텀 포맷(-Fc) + OCI Object Storage 사본 + 보관 정리.
#
# [BL-767] · [ADR-033](docs/adr/033-db-hosting-self-host-timescaledb.md) 조건 ⑴.
#   self-host TimescaleDB 를 고른 대가가 「백업이 전적으로 우리 책임」이고, ADR 이 없던 것으로
#   지목한 셋이 정확히 이 스크립트의 세 축이다 — ⑴ 스케줄(`--install`) ⑵ 오프서버 보관(OCI)
#   ⑶ **복원 실증**(`verify-restore`).
#   ★**복원을 한 번 실제로 해 보기 전에는 백업이 있다고 말하지 않는다.**
#
# 왜 Makefile 의 db-snapshot 과 따로 있나
#   `mise run db-snapshot`(Makefile:312) 은 **로컬 수동용**이고 그대로 둔다. 그것은
#   `_guard-main-only` + `assert-main-checkout.sh` 를 타고 `docker compose` 로 붙으므로
#   ⑴ 레포 체크아웃이 main 이어야 하고 ⑵ compose 파일 조합에 의존하며 ⑶ 원격 사본·보관
#   정리·타이머가 없다. 서버에서 6시간마다 무인으로 도는 백업은 셋 다 반대를 요구한다 —
#   체크아웃 상태와 무관해야 하고, 지금 떠 있는 컨테이너를 **이름**으로 겨눠야 하고,
#   사람이 없어도 원격에 사본이 남아야 한다. 그래서 별 스크립트다.
#
# 사용:
#   tools/scripts/db-backup.sh run                    # 1회 백업 (타이머가 부르는 형태)
#   tools/scripts/db-backup.sh verify-restore <덤프>  # ★throwaway DB 왕복만. **앱 DB 복구 절차가 아니다**
#   tools/scripts/db-backup.sh --status               # 타이머 · 최근 백업 · 설치본 신선도
#   tools/scripts/db-backup.sh --install              # systemd user timer (03·09·15·21시)
#   tools/scripts/db-backup.sh --uninstall
#
# 환경 변수 (전부 선택):
#   QB_BACKUP_DIR=/opt/backups   QB_BACKUP_RETAIN_DAYS=14   QB_BACKUP_BUCKET=quantbridge-backups
#   QB_BACKUP_PREFIX=            객체 이름 앞에 붙는 경계. **남의 버킷을 빌려 쓸 때 쓴다.**
#                                2026-08-16 실측 — 이 VM 의 Instance Principal 은 `manage objects`
#                                는 있는데 **버킷 생성 권한이 없다**(`bucket create` 409 인데
#                                `bucket get` 은 404 = 존재하지도 않는데 못 만든다). 그래서
#                                `QB_BACKUP_BUCKET=truewords-backups QB_BACKUP_PREFIX=quantbridge`
#                                로 다른 앱 버킷을 공유한다. 전용 버킷이 생기면 prefix 를 비워라.
#   QB_DB_CONTAINER=quantbridge-db   QB_DB_USER=  QB_DB_NAME=  (미지정 시 컨테이너에서 읽는다)
#   QB_SKIP_UPLOAD=1             원격 업로드를 **명시적으로** 건너뛴다 (rc 에 영향 없음)
#   QB_OCI_BIN=/usr/local/bin/oci
#   QB_ALLOW_VERSION_SKEW=1      verify-restore 의 TimescaleDB 버전 대조를 우회
#
# 종료 코드: 0 = 정상 / 1 = 실패·거부 / 2 = 전제 미충족(측정 못 함)
#   ★3 = **로컬 덤프는 정상인데 원격 업로드만 실패**(부분 성공). soak-stack.sh 의 3종 규약을
#     한 칸 넓혔다 — 「덤프가 없다」와 「원격 사본이 없다」는 복구 가능성이 전혀 다른 사건인데
#     둘 다 1 이면 알림을 받은 사람이 무엇이 깨졌는지 모른다. systemd 는 3 도 실패로 세므로
#     OnFailure 알람은 그대로 발화한다 — 즉 「경고로 남기되 조용히 묻지는 않는다」.
#
# ★설계 근거 (앞의 셋은 이 호스트에서 실제로 덴 것이다)
#   · **로그를 /var/log 에 두지 않는다.** 같은 호스트의 truewords 백업이 그것으로 조용히
#     죽었다 — cron 은 ubuntu 로 돌고 /var/log 는 root 전용이라 **리다이렉트가 열리는
#     단계**에서 Permission denied 가 난다. 스크립트가 아예 실행되지 않고 진단할 로그도 안
#     남는다. 여기서는 systemd user unit 을 쓰므로 출력이 전부 journal 로 간다.
#   · ★★**컨테이너를 절대 기동·정지·재시작하지 않는다.** `docker exec` + `docker cp` 뿐이다.
#     서버에서 [BL-003] 24시간 소크 창이 돌고 있고 `up`/`down`/`restart`/`stop`/`start` 는 그
#     창을 **끊는다**. 백업 한 번이 소크 며칠을 지우는 것이 이 스크립트의 최대 위험이라,
#     짝 하네스가 docker 인자를 전수 기록해 금지어 등장 자체를 red 로 잡는다.
#   · **대상을 증명하고 시작한다.** base/isolated/soak compose 가 `container_name:
#     quantbridge-db` 를 공유하므로 "지금 떠 있는 것"이 대상이 된다(Makefile:301-303).
#     이미지가 timescaledb 계열인지 · DB 이름이 맞는지 · published port 가 `.env.local` 의
#     DATABASE_URL 과 같은지까지 본다 (`soak-stack.sh` `_migrate` 와 같은 관용구).
#   · **빈 파일을 남기지 않는다.** 크기 0 이면 지우고 죽는다(Makefile:312-324 와 같은 규칙).
#     0바이트 덤프가 쌓이면 「백업이 있다」가 거짓이 된다.
#   · **자격증명은 파일이 아니라 컨테이너에서 읽는다.** `.env` 는 편집돼도 컨테이너는 기동
#     시점 값을 쥔다 — 파일은 선언이고 컨테이너가 실측이다. 그리고 psql/pg_dump 를 컨테이너
#     안 유닉스 소켓으로 부르므로 비밀번호가 스크립트·유닛·로그 어디에도 등장하지 않는다.
#   · **파이프로 rc 를 가리지 않는다.** `out="$(cmd)" || rc=$?` 로 받는다. 이 레포는 `| tail`
#     이 tail 의 rc 를 읽게 해 정반대 판정을 낸 사고가 두 번 있다.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
BACKUP_DIR="${QB_BACKUP_DIR:-/opt/backups}"
RETAIN_DAYS="${QB_BACKUP_RETAIN_DAYS:-14}"
BUCKET="${QB_BACKUP_BUCKET:-quantbridge-backups}"
# 남의 버킷을 공유할 때의 경계. 비면 버킷 루트에 올린다 (`_upload` 주석 참조).
BACKUP_PREFIX="${QB_BACKUP_PREFIX:-}"
OCI_BIN="${QB_OCI_BIN:-/usr/local/bin/oci}"
ENV_FILE="${QB_ENV_FILE:-${ROOT}/apps/api/.env.local}"

UNIT_NAME="dev.quantbridge.db-backup"
ALARM_UNIT="dev.quantbridge.db-backup-alarm"
UNIT_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"

DB_USER=""
DB_NAME=""
TS_VERSION=""
PG_VERSION=""
IMAGE_REF=""
DOCKER=()
SUDO=""
_CONTAINER_TMP=""   # 컨테이너 안에 남긴 임시 파일 (trap 이 지운다)
_VERIFY_DB=""       # verify-restore 가 만든 throwaway DB (trap 이 지운다)

log() { printf '[%s] %s\n' "$(date -u '+%F %T')" "$*"; }
die() { printf '✗ %s\n' "$1" >&2; exit "${2:-1}"; }

# ── docker / sudo 배선 ─────────────────────────────────────────────────────────
# ★서버의 ubuntu 는 docker 그룹에 있어 맨 `docker` 로 닿는다(2026-08-16 실측). 그래서
#   truewords 판처럼 `sudo docker` 를 **박아 두지 않는다** — 박으면 sudo 가 PATH 를 재설정해
#   하네스의 스텁이 안 걸리고, sudo 없는 호스트에서 통째로 못 돈다.
# ★대신 sudo 가 필요한 진짜 이유는 **파일 쪽**이다. /opt/backups 는 root:root drwxr-xr-x 라
#   ubuntu 가 쓸 수 없다. 그래서 「백업 디렉터리에 쓸 수 있나」로 한 번만 판정하고, 필요하면
#   docker 호출까지 통째로 sudo 아래에서 돌린다(root 는 docker 에 늘 닿으므로 안전한 상위집합).
_wire_docker() {
  local dir="${BACKUP_DIR}" fs_needs_sudo=0 docker_needs_sudo=0
  while [ ! -d "${dir}" ] && [ "${dir}" != "/" ]; do dir="$(dirname "${dir}")"; done
  [ -w "${dir}" ] || fs_needs_sudo=1
  docker version --format '{{.Server.Version}}' > /dev/null 2>&1 || docker_needs_sudo=1

  if [ "${fs_needs_sudo}" -eq 1 ] || [ "${docker_needs_sudo}" -eq 1 ]; then
    command -v sudo > /dev/null 2>&1 || die "sudo 가 필요한데 없다 (백업 디렉터리 ${BACKUP_DIR} 에 쓸 수 없거나 docker 에 못 닿는다)" 2
    sudo -n true > /dev/null 2>&1 || die "sudo 가 비밀번호를 요구한다 — 무인 실행이 불가능하다" 2
    SUDO="sudo"
  fi
  # shellcheck disable=SC2206  # SUDO 는 빈 문자열이거나 "sudo" 뿐이라 분할이 의도한 동작이다
  DOCKER=(${SUDO} docker)

  "${DOCKER[@]}" version --format '{{.Server.Version}}' > /dev/null 2>&1 \
    || die "docker 데몬에 못 닿는다 (${SUDO:-비-sudo}) — 백업 대상을 **측정하지 못했다**" 2
}

_docker_inspect() { # _docker_inspect <format> → stdout (없으면 빈 문자열, rc 0)
  "${DOCKER[@]}" inspect "${DB_CONTAINER}" --format "$1" 2> /dev/null || true
}

_psql() { # _psql <db> <sql> → stdout 한 줄. rc 는 psql 의 것이다.
  "${DOCKER[@]}" exec "${DB_CONTAINER}" \
    psql -U "${DB_USER}" -d "$1" -X -q -A -t -v ON_ERROR_STOP=1 -c "$2"
}

# ── 대상 증명 ──────────────────────────────────────────────────────────────────
# ★이것이 이 스크립트에서 가장 중요한 절이다. compose 3벌이 같은 `container_name` 을 쓰므로
#   "지금 떠 있는 것"이 대상이 된다 — 격리/테스트 DB 를 떠 놓고 백업을 돌리면 **정상으로
#   보이는 쓸모없는 덤프**가 쌓인다. 조용한 실패라 사고가 날 때까지 아무도 모른다.
_prove_target() {
  local status image probe cur ext ver dburl pub pub_port

  status="$(_docker_inspect '{{.State.Status}}')"
  [ -n "${status}" ] || die "컨테이너 ${DB_CONTAINER} 가 없다 — 백업 대상을 측정하지 못했다" 2
  [ "${status}" = "running" ] || die "컨테이너 ${DB_CONTAINER} 가 running 이 아니다 (${status}) — 기동은 이 스크립트의 일이 아니다" 2

  # ★이미지 계열 확인. `postgres:16` 이나 `pgvector` 가 같은 이름으로 떠 있으면 덤프는
  #   만들어지지만 hypertable 이 없는 다른 DB 다 — 그것을 정상으로 세면 안 된다.
  image="$(_docker_inspect '{{.Config.Image}}')"
  case "${image}" in
    *timescale/timescaledb*) ;;
    *) die "${DB_CONTAINER} 의 이미지가 timescaledb 계열이 아니다: ${image:-(못 읽음)}" 1 ;;
  esac

  # 자격증명은 컨테이너의 Config.Env 에서 읽는다 (파일은 선언, 컨테이너가 실측).
  if [ -z "${DB_USER}" ]; then
    DB_USER="${QB_DB_USER:-$(_docker_inspect '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_USER=//p' | head -1)}"
  fi
  if [ -z "${DB_NAME}" ]; then
    DB_NAME="${QB_DB_NAME:-$(_docker_inspect '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_DB=//p' | head -1)}"
  fi
  [ -n "${DB_USER}" ] && [ -n "${DB_NAME}" ] \
    || die "${DB_CONTAINER} 에서 POSTGRES_USER/POSTGRES_DB 를 못 읽었다 — QB_DB_USER/QB_DB_NAME 으로 명시해라" 2

  # DB 이름 · TimescaleDB 확장 · 서버 버전을 한 번에 실측한다.
  probe=""
  probe="$(_psql "${DB_NAME}" "SELECT current_database()||'|'||coalesce((SELECT extversion FROM pg_extension WHERE extname='timescaledb'),'')||'|'||current_setting('server_version');")" \
    || die "${DB_CONTAINER}/${DB_NAME} 에 psql 로 못 붙었다 — 대상을 측정하지 못했다" 2
  cur="${probe%%|*}"
  ext="$(printf '%s' "${probe}" | cut -d'|' -f2)"
  ver="$(printf '%s' "${probe}" | cut -d'|' -f3)"
  [ "${cur}" = "${DB_NAME}" ] || die "current_database() 가 ${cur} 다 (기대 ${DB_NAME})" 1
  [ -n "${ext}" ] || die "${DB_NAME} 에 timescaledb 확장이 없다 — 대상 DB 가 아니다" 1

  TS_VERSION="${ext}"
  PG_VERSION="${ver}"
  IMAGE_REF="${image}"

  # published port ↔ .env.local DATABASE_URL 대조 (`soak-stack.sh` _migrate 관용구).
  # ★백업은 읽기 전용이라 DDL 만큼 위험하진 않지만, **엉뚱한 DB 를 백업하는 것**은
  #   실패로 보이지 않는 실패다. 그래서 여기서도 잰다. `.env.local` 이 없으면 못 재는
  #   것이므로 경고만 남긴다(레포 체크아웃 없이 도는 배치를 막지 않는다).
  pub="$("${DOCKER[@]}" port "${DB_CONTAINER}" 5432/tcp 2> /dev/null | head -1)" || true
  pub_port="${pub##*:}"
  if [ -f "${ENV_FILE}" ] && [ -n "${pub_port}" ]; then
    dburl="$(sed -n 's/^[[:space:]]*DATABASE_URL=//p' "${ENV_FILE}" | tail -1)"
    if [ -n "${dburl}" ]; then
      case "${dburl}" in
        *":${pub_port}/"*) ;;
        *) die "DATABASE_URL 이 ${DB_CONTAINER}(:${pub_port}) 를 가리키지 않는다 — 앱이 쓰는 DB 가 아닌 것을 백업할 뻔했다" 1 ;;
      esac
      # ★★**포트만으로는 부족하다** (2026-08-16 codex P1 · 채택). `DB_NAME` 은 컨테이너의
      #   `POSTGRES_DB` 에서 오고 `DATABASE_URL` 은 앱이 실제로 접속하는 DB 다 — 한 컨테이너
      #   안에 DB 가 여럿이면 **포트는 같은데 이름이 다를 수 있다**. 그러면 앱이 쓰는
      #   `another_db` 대신 `quantbridge` 를 떠 놓고 「백업 성공」이라고 말한다.
      #   `soak-stack.sh:_migrate` 는 이 대조가 필요 없다 — 거기서는 DSN 을 **직접** 써서
      #   이름이 자동으로 일치한다. 백업만 이름을 딴 데서 얻으므로 여기서 재야 한다.
      dbname="${dburl##*/}"     # 마지막 '/' 뒤
      dbname="${dbname%%\?*}"   # 쿼리스트링 제거
      if [ -n "${dbname}" ] && [ "${dbname}" != "${DB_NAME}" ]; then
        die "DATABASE_URL 의 DB 이름이 '${dbname}' 인데 백업 대상은 '${DB_NAME}' 이다 — 앱이 쓰지 않는 DB 를 백업할 뻔했다 (덮어쓰려면 QB_DB_NAME 을 명시해라)" 1
      fi
    fi
  fi

  log "대상 증명 ✓  ${DB_CONTAINER} / ${DB_NAME} (user=${DB_USER}) · ${image} · pg ${ver} · timescaledb ${ext} · :${pub_port:-?}"
}

# ── 사실 측정 ──────────────────────────────────────────────────────────────────
# tables|ohlcv_rows|chunks. ohlcv 가 없으면 rows = -1 (「0 행」과 「테이블 없음」을 구분한다).
_facts() { # _facts <db>
  _psql "$1" "SELECT (SELECT count(*) FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') AND table_schema NOT LIKE '\\_timescaledb%')||'|'||(CASE WHEN to_regclass('ts.ohlcv') IS NULL THEN -1 ELSE (SELECT count(*) FROM ts.ohlcv) END)||'|'||(SELECT count(*) FROM timescaledb_information.chunks);"
}

_min() { [ "$1" -le "$2" ] && printf '%s' "$1" || printf '%s' "$2"; }
_max() { [ "$1" -ge "$2" ] && printf '%s' "$1" || printf '%s' "$2"; }

# ── run ───────────────────────────────────────────────────────────────────────
_cleanup_container_tmp() {
  [ -n "${_CONTAINER_TMP}" ] || return 0
  "${DOCKER[@]}" exec "${DB_CONTAINER}" rm -f "${_CONTAINER_TMP}" > /dev/null 2>&1 || true
  _CONTAINER_TMP=""
}

_run() {
  local stamp out meta size rc=0 upload_rc=0
  local f_before f_after t_b r_b c_b t_a r_a c_a

  _wire_docker
  _prove_target

  ${SUDO} mkdir -p "${BACKUP_DIR}" || die "백업 디렉터리를 못 만든다: ${BACKUP_DIR}" 2

  stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  out="${BACKUP_DIR}/quantbridge-${stamp}.dump"
  meta="${out}.meta"
  _CONTAINER_TMP="/tmp/qb-backup-${stamp}.dump"
  # shellcheck disable=SC2064  # 지금 값으로 굳혀야 한다 (trap 발화 시점엔 이미 비워졌을 수 있다)
  trap '_cleanup_container_tmp' EXIT

  # ★덤프 **직전**의 사실. pg_dump 는 시작 시점의 일관 스냅샷을 뜨므로 이 값이 덤프 내용에
  #   가장 가깝다. 그런데 소크가 도는 DB 는 덤프 중에도 행이 늘어난다 — 한 번만 재고 등호로
  #   대조하면 verify-restore 가 **살아 있는 백업을 red 로** 만든다. 그래서 앞뒤로 두 번 재고
  #   [min,max] 구간으로 기록한다. 정지한 DB 에서는 구간이 한 점으로 붙어 정확히 등호가 된다.
  f_before="$(_facts "${DB_NAME}")" || die "덤프 전 사실 측정 실패" 2

  log "백업 시작 → ${out}"
  # ★★compose 를 부르지 않는다. exec + cp 뿐이다 (소크 창 보호).
  "${DOCKER[@]}" exec "${DB_CONTAINER}" \
    pg_dump --no-owner --no-acl -Fc -U "${DB_USER}" -d "${DB_NAME}" -f "${_CONTAINER_TMP}" \
    || die "pg_dump 실패" 1

  f_after="$(_facts "${DB_NAME}")" || die "덤프 후 사실 측정 실패" 2

  "${DOCKER[@]}" cp "${DB_CONTAINER}:${_CONTAINER_TMP}" "${out}" \
    || die "덤프를 호스트로 못 꺼냈다 (docker cp)" 1

  # ★무결성은 **컨테이너 안**에서 판독한다 — 호스트에 pg_restore 가 없어도 되게.
  #   여기서 남긴 임시 파일을 그대로 읽으므로 되올릴 필요가 없다.
  "${DOCKER[@]}" exec "${DB_CONTAINER}" pg_restore --list "${_CONTAINER_TMP}" > /dev/null 2>&1 \
    || { ${SUDO} rm -f "${out}"; die "덤프 헤더를 못 읽었다 (pg_restore --list) — 손상된 파일을 남기지 않는다" 1; }

  _cleanup_container_tmp
  trap - EXIT

  # ★크기 0 이면 파일을 지우고 죽는다. 빈 파일이 남으면 「백업이 있다」가 거짓이 된다.
  # ★`sudo wc -c < file` 은 리다이렉트를 **부르는 쪽 권한**으로 연다 — 파일 인자로 줘야
  #   root 로 읽는다. /opt/backups 가 root:root 일 때 이 차이가 드러난다.
  size="$(${SUDO} wc -c "${out}" 2> /dev/null | awk '{print $1}')" || size=0
  if [ -z "${size}" ] || [ "${size}" -le 0 ]; then
    ${SUDO} rm -f "${out}"
    die "덤프 크기가 0 이다 — 빈 파일을 남기지 않는다" 1
  fi

  t_b="${f_before%%|*}"; r_b="$(printf '%s' "${f_before}" | cut -d'|' -f2)"; c_b="$(printf '%s' "${f_before}" | cut -d'|' -f3)"
  t_a="${f_after%%|*}";  r_a="$(printf '%s' "${f_after}"  | cut -d'|' -f2)"; c_a="$(printf '%s' "${f_after}"  | cut -d'|' -f3)"

  # ★사이드카 메타 — verify-restore 의 **기대값**이 여기서 나온다. 이것이 없으면
  #   「복원됐다」는 말할 수 있어도 「무엇이 복원돼야 했나」를 말할 수 없다(= 판별력 0).
  #   덤프와 같은 이름 + `.meta` 라 보관 정리·업로드가 둘을 한 벌로 다룬다.
  ${SUDO} tee "${meta}" > /dev/null << EOF
schema=1
created_at=${stamp}
container=${DB_CONTAINER}
image=${IMAGE_REF}
db=${DB_NAME}
pg_version=${PG_VERSION}
timescaledb_version=${TS_VERSION}
bytes=${size}
tables_min=$(_min "${t_b}" "${t_a}")
tables_max=$(_max "${t_b}" "${t_a}")
ohlcv_rows_min=$(_min "${r_b}" "${r_a}")
ohlcv_rows_max=$(_max "${r_b}" "${r_a}")
chunks_min=$(_min "${c_b}" "${c_a}")
chunks_max=$(_max "${c_b}" "${c_a}")
EOF

  log "백업 완료 (${size} bytes) · 테이블 ${t_b} · ohlcv ${r_b}행 · chunk ${c_b}"

  # ── 원격 사본 ────────────────────────────────────────────────────────────────
  # VM 로컬만으로는 인스턴스·디스크 유실을 못 막는다. 인증은 Instance Principal 이라
  # VM 에 개인키를 두지 않는다(truewords 판과 같다).
  if [ "${QB_SKIP_UPLOAD:-0}" = "1" ]; then
    log "원격 업로드 건너뜀 (QB_SKIP_UPLOAD=1) — 명시적 지시이므로 rc 에 반영하지 않는다"
  elif [ ! -x "${OCI_BIN}" ]; then
    # ★truewords 판은 여기서 조용히 넘어간다. 그러면 「원격 사본이 하나도 없다」가
    #   무기한 안 보인다 — 그래서 여기서는 rc=3 으로 새어나오게 한다.
    log "⚠️ oci CLI 가 없다 (${OCI_BIN}) — 로컬 사본만 있다. 설치하거나 QB_SKIP_UPLOAD=1 로 명시해라"
    upload_rc=3
  else
    if _upload "${out}" && _upload "${meta}"; then
      log "Object Storage 업로드 완료 (bucket=${BUCKET})"
    else
      log "⚠️ Object Storage 업로드 실패 — **로컬 백업은 정상**이다 (bucket=${BUCKET})"
      upload_rc=3
    fi
  fi

  _retain
  return "${upload_rc}"
}

_upload() { # _upload <파일>
  # ★`QB_BACKUP_PREFIX` 는 **남의 버킷을 빌려 쓸 때** 경계를 만든다 (2026-08-16 실측).
  #   이 VM 의 Instance Principal 은 `manage objects` 는 있는데 **버킷 생성 권한이 없다** —
  #   `bucket create` 가 409 `BucketAlreadyExists` 를 주는데 `bucket get` 은 **404** 다(즉
  #   존재하지 않는데 못 만든다). 그래서 다른 앱의 `truewords-backups` 를 공유하고 있고,
  #   그때 우리 것의 경계가 **파일명 규칙에만** 의존하면 저쪽이 규칙을 바꾸는 순간 섞인다.
  #   prefix 는 그 결합을 끊고, 나중에 전용 버킷이 생기면 `QB_BACKUP_PREFIX=` 만 비우면 된다.
  #   ★슬래시는 여기서 붙인다 — 호출자가 넣고 안 넣고에 따라 경로가 갈리면 안 된다.
  local name
  name="$(basename "$1")"
  [ -n "${BACKUP_PREFIX}" ] && name="${BACKUP_PREFIX%/}/${name}"
  "${OCI_BIN}" os object put --auth instance_principal \
    --bucket-name "${BUCKET}" --file "$1" --name "${name}" --force > /dev/null 2>&1
}

_retain() {
  local deleted count total
  deleted="$(${SUDO} find "${BACKUP_DIR}" -maxdepth 1 \
    \( -name 'quantbridge-*.dump' -o -name 'quantbridge-*.dump.meta' \) \
    -mtime "+${RETAIN_DAYS}" -print -delete 2> /dev/null | grep -c . || true)"
  count="$(${SUDO} find "${BACKUP_DIR}" -maxdepth 1 -name 'quantbridge-*.dump' 2> /dev/null | grep -c . || true)"
  total="$(${SUDO} du -sh "${BACKUP_DIR}" 2> /dev/null | cut -f1)" || total="?"
  log "${RETAIN_DAYS}일 경과분 ${deleted}개 파일 삭제 · 현재 보관 ${count}개 / ${total:-?}"
}

# ── verify-restore ────────────────────────────────────────────────────────────
# ★★throwaway DB 로만 한다. 앱 DB 는 1벌 공유라 거기 restore 하면 소크가 죽는다.
# ★덤프와 복원의 **확장 버전이 다르면 catalog version mismatch 로 죽는다.**
#   그래서 복원 전에 메타의 timescaledb_version 과 살아 있는 확장 버전을 대조한다.
#
# ★★`timescaledb_pre_restore()` / `post_restore()` — **[확인 필요] 로 남긴다.**
#   [ADR-033] 조건 ⑴ 과 TimescaleDB 문서는 이 둘로 감싸지 않으면 내부 훅(`timescaledb.restoring`
#   GUC) 때문에 복원이 깨진다고 말한다. 그래서 절차에 그대로 넣었다. 그런데 **2026-08-16 에
#   지금 스키마로 실측해 보니 둘의 유무가 관측 가능한 차이를 하나도 만들지 않았다** —
#   pg_dump/pg_restore 각각 rc=0 · stderr 0줄 · `_timescaledb_catalog.chunk` 59 ·
#   `timescaledb_information.chunks` 59 · `ts.ohlcv` 21,649행 · 복원본에 INSERT 하면 새
#   chunk 로 라우팅(59→60) · `drop_chunks()` 정상. 즉 **양쪽이 완전히 같았다.**
#   [가정] 지금 스키마가 hypertable 1개뿐이고 continuous aggregate·압축·정책이 0건이라
#   훅이 할 일이 없어서다([ADR-033] 실측표: 고유 기능 사용처 0건). 그것들이 생기면 달라진다.
#   ⇒ **호출은 유지한다**(문서가 정본이고 비용이 0이다). 다만 짝 하네스는 이 축에 대해
#     **판별력이 없다** — 지워도 39/39 초록이다(실측). 「테스트가 지킨다」고 적지 마라.
_drop_verify_db() {
  [ -n "${_VERIFY_DB}" ] || return 0
  _psql postgres "DROP DATABASE IF EXISTS ${_VERIFY_DB};" > /dev/null 2>&1 \
    || printf '⚠️ throwaway DB 정리 실패 — 손으로 지워라: %s\n' "${_VERIFY_DB}" >&2
  _VERIFY_DB=""
}

_verify_cleanup() {
  local rc=$?
  _drop_verify_db
  _cleanup_container_tmp
  return "${rc}"
}

_verify_restore() { # _verify_restore <덤프 파일>
  local dump="$1" meta stamp got t r c
  local want_ts m_tables_min m_tables_max m_rows_min m_rows_max m_chunks_min m_chunks_max
  local live_ts fail=""

  [ -n "${dump}" ] || die "덤프 파일 경로가 필요하다 (verify-restore <덤프>)" 1
  [ -f "${dump}" ] || die "덤프 파일이 없다: ${dump}" 1
  [ -s "${dump}" ] || die "덤프 파일이 비었다: ${dump}" 1
  meta="${dump}.meta"
  # ★메타가 없으면 **기대값이 없다.** 「복원은 됐다」만으로 초록을 내면 빈 DB 가 복원돼도
  #   통과한다 — 이 레포가 여러 번 덴 「검사기가 빈 입력을 초록으로 통과」 그 모양이다.
  #   그래서 fail-open 하지 않고 전제 미충족(2)으로 죽는다.
  [ -f "${meta}" ] || die "사이드카 메타가 없다: ${meta} — 기대값 없이는 복원을 판정할 수 없다" 2

  want_ts="$(sed -n 's/^timescaledb_version=//p' "${meta}" | head -1)"
  m_tables_min="$(sed -n 's/^tables_min=//p' "${meta}" | head -1)"
  m_tables_max="$(sed -n 's/^tables_max=//p' "${meta}" | head -1)"
  m_rows_min="$(sed -n 's/^ohlcv_rows_min=//p' "${meta}" | head -1)"
  m_rows_max="$(sed -n 's/^ohlcv_rows_max=//p' "${meta}" | head -1)"
  m_chunks_min="$(sed -n 's/^chunks_min=//p' "${meta}" | head -1)"
  m_chunks_max="$(sed -n 's/^chunks_max=//p' "${meta}" | head -1)"
  [ -n "${m_tables_min}" ] && [ -n "${m_rows_min}" ] && [ -n "${m_chunks_min}" ] \
    || die "메타에 기대값이 없다: ${meta}" 2

  _wire_docker
  _prove_target

  live_ts="${TS_VERSION}"
  if [ -n "${want_ts}" ] && [ "${want_ts}" != "${live_ts}" ]; then
    if [ "${QB_ALLOW_VERSION_SKEW:-0}" = "1" ]; then
      log "⚠️ TimescaleDB 버전이 다르다 (덤프 ${want_ts} vs 복원 ${live_ts}) — QB_ALLOW_VERSION_SKEW=1 로 강행한다"
    else
      die "TimescaleDB 버전 불일치: 덤프 ${want_ts} vs 복원 대상 ${live_ts} — catalog version mismatch 로 복원이 죽는다. 같은 버전 이미지에서 복원해라 (강행: QB_ALLOW_VERSION_SKEW=1)" 1
    fi
  fi

  stamp="$(date -u '+%Y%m%d%H%M%S')_$$"
  _VERIFY_DB="qb_restore_verify_${stamp}"
  # ★이름 가드. 앱 DB 를 겨눌 수 있는 경로를 문법으로 닫는다 — 이 스크립트에서 DROP DATABASE 를
  #   부르는 자리는 여기 하나뿐이고, 그 대상은 반드시 이 접두사를 가진다.
  case "${_VERIFY_DB}" in
    qb_restore_verify_[0-9]*) ;;
    *) die "throwaway DB 이름이 규약을 벗어났다: ${_VERIFY_DB}" 1 ;;
  esac
  [ "${_VERIFY_DB}" != "${DB_NAME}" ] || die "throwaway DB 이름이 앱 DB 와 같다 — 거부한다" 1

  _CONTAINER_TMP="/tmp/qb-verify-${stamp}.dump"
  trap '_verify_cleanup' EXIT

  "${DOCKER[@]}" cp "${dump}" "${DB_CONTAINER}:${_CONTAINER_TMP}" \
    || die "덤프를 컨테이너로 못 넣었다 (docker cp)" 1

  # 헤더 판독 — 잘린 파일은 여기서 걸린다(실측: truncated → rc=1).
  "${DOCKER[@]}" exec "${DB_CONTAINER}" pg_restore --list "${_CONTAINER_TMP}" > /dev/null 2>&1 \
    || die "덤프 헤더를 못 읽었다 — 손상된 덤프다: ${dump}" 1

  log "throwaway DB 생성: ${_VERIFY_DB}"
  _psql postgres "CREATE DATABASE ${_VERIFY_DB};" > /dev/null || die "throwaway DB 생성 실패" 1
  _psql "${_VERIFY_DB}" "CREATE EXTENSION IF NOT EXISTS timescaledb;" > /dev/null 2>&1 \
    || die "throwaway DB 에 timescaledb 확장을 못 만들었다" 1
  _psql "${_VERIFY_DB}" "SELECT timescaledb_pre_restore();" > /dev/null \
    || die "timescaledb_pre_restore() 실패 — 문서가 요구하는 단계다(효과는 :348-358 [확인 필요])" 1

  "${DOCKER[@]}" exec "${DB_CONTAINER}" \
    pg_restore --no-owner --no-acl -U "${DB_USER}" -d "${_VERIFY_DB}" "${_CONTAINER_TMP}" \
    || die "pg_restore 실패 — 이 덤프로는 복원할 수 없다: ${dump}" 1

  _psql "${_VERIFY_DB}" "SELECT timescaledb_post_restore();" > /dev/null \
    || die "timescaledb_post_restore() 실패" 1

  got="$(_facts "${_VERIFY_DB}")" || die "복원본의 사실을 못 읽었다" 1
  t="${got%%|*}"; r="$(printf '%s' "${got}" | cut -d'|' -f2)"; c="$(printf '%s' "${got}" | cut -d'|' -f3)"

  [ "${t}" -ge "${m_tables_min}" ] && [ "${t}" -le "${m_tables_max}" ] \
    || fail="${fail}테이블 ${t}개 (기대 ${m_tables_min}~${m_tables_max}) "
  [ "${r}" -ge "${m_rows_min}" ] && [ "${r}" -le "${m_rows_max}" ] \
    || fail="${fail}ohlcv ${r}행 (기대 ${m_rows_min}~${m_rows_max}) "
  [ "${c}" -ge "${m_chunks_min}" ] && [ "${c}" -le "${m_chunks_max}" ] \
    || fail="${fail}chunk ${c}개 (기대 ${m_chunks_min}~${m_chunks_max}) "

  if [ -n "${fail}" ]; then
    die "복원본이 기대와 다르다 — ${fail}" 1
  fi

  log "복원 실증 ✓  테이블 ${t} · ohlcv ${r}행 · chunk ${c} (덤프 ${dump})"
  return 0
}

# ── systemd 설치 ──────────────────────────────────────────────────────────────
_install() {
  command -v systemctl > /dev/null 2>&1 || die "systemctl 이 없다 — 이 설치 경로는 리눅스 전용이다" 1
  mkdir -p "${UNIT_DIR}" || die "유닛 디렉터리를 못 만든다: ${UNIT_DIR}" 1
  case "${ENV_FILE}" in
    *"'"*) die "env 파일 경로에 작은따옴표가 있어 유닛을 안전하게 생성할 수 없다: ${ENV_FILE}" 1 ;;
  esac

  # ★PATH 를 명시한다. 비로그인 셸에는 /usr/local/bin 이 없어 oci 를 못 찾고, 그러면
  #   원격 사본이 조용히 사라진다(= rc=3 이 매번 뜬다).
  cat > "${UNIT_DIR}/${UNIT_NAME}.service" << EOF
[Unit]
Description=QuantBridge DB 백업 (pg_dump -Fc + OCI Object Storage 사본)
OnFailure=${ALARM_UNIT}.service

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PATH=/usr/local/bin:${HOME}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin
Environment=QB_BACKUP_DIR=${BACKUP_DIR}
Environment=QB_BACKUP_RETAIN_DAYS=${RETAIN_DAYS}
Environment=QB_BACKUP_BUCKET=${BUCKET}
Environment=QB_BACKUP_PREFIX=${BACKUP_PREFIX}
Environment=QB_DB_CONTAINER=${DB_CONTAINER}
ExecStart=/bin/bash ${SCRIPT_DIR}/db-backup.sh run
EOF

  # ★알람 유닛 — `soak-watch.sh:174-194` 를 그대로 물려받는다. 두 함정이 있고 둘 다 이
  #   레포에서 실제로 알람을 조용히 죽였다:
  #   ★★**`$$` 이스케이프.** systemd 는 ExecStart 의 `${VAR}` 를 **자기 환경으로 먼저
  #     확장**하고 미정의 변수는 **빈 문자열**로 만든다 — 작은따옴표도 막지 못한다. 그러면
  #     URL 이 `…/bot/sendMessage` 가 되어 텔레그램이 404 를 준다(2026-08-15 서버 실측).
  #     systemd 에서 리터럴 `$` 는 `$$` 다.
  #   ★**`--fail`.** 없으면 텔레그램이 400/404 를 줘도 curl 은 rc=0 이고 유닛은 `Finished`
  #     로 남는다. 「알람이 돌았다」와 「알람이 도착했다」가 구분되지 않는다.
  #   ★`--show-error` 는 뺀다 — 실패 메시지에 URL(경로에 토큰이 있다)이 실릴 수 있다.
  #   ★토큰은 유닛에 박지 않는다 — `.env.local` 을 그 자리에서 소싱한다.
  cat > "${UNIT_DIR}/${ALARM_UNIT}.service" << EOF
[Unit]
Description=QuantBridge DB 백업 실패 알림

[Service]
Type=oneshot
Environment=PATH=/usr/local/bin:${HOME}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin
ExecStart=/bin/bash -c 'set -a; . "${ENV_FILE}"; set +a; exec curl --silent --fail --output /dev/null --max-time 15 --data-urlencode "chat_id=\$\${TELEGRAM_CHAT_ID}" --data-urlencode "text=🔴 ${UNIT_NAME}.service 가 실패했다 — DB 백업이 깨졌거나 원격 사본이 없다. journalctl --user -u ${UNIT_NAME}.service -n 40" "https://api.telegram.org/bot\$\${TELEGRAM_BOT_TOKEN}/sendMessage"'
EOF

  # ★**벽시계 고정.** `OnUnitActiveSec` 은 마지막 활성화 기준이라 사람이 손으로 한 번 돌리면
  #   위상이 밀린다(2026-08-15 [BL-737] 실측: 소크 표본 간격이 53분까지 벌어졌다).
  # ★**03·09·15·21시.** 같은 호스트의 truewords 백업이 00/06/12/18 을 쓴다 — 겹치면 두 pg_dump
  #   가 같은 디스크·같은 업로드 대역을 동시에 쓴다. 3시간 어긋나게 둔다.
  # ★`Persistent=true` 로 재부팅·정지 구간에서 놓친 발화를 따라잡는다.
  cat > "${UNIT_DIR}/${UNIT_NAME}.timer" << 'EOF'
[Unit]
Description=QuantBridge DB 백업 — 03·09·15·21시 (벽시계 고정, truewords 00/06/12/18 과 어긋나게)

[Timer]
OnCalendar=03,09,15,21:00
AccuracySec=1min
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload || die "daemon-reload 실패" 1
  systemctl --user enable --now "${UNIT_NAME}.timer" || die "타이머 enable 실패" 1
  echo "✓ 설치 완료 — 03·09·15·21시(로컬 시각)에 백업한다"
  echo "  백업 위치 : ${BACKUP_DIR}/quantbridge-<UTC 스탬프>.dump (+ .meta)"
  echo "  원격 버킷 : ${BUCKET}"
  echo "  보관 기간 : ${RETAIN_DAYS}일"
  echo "  ★실패하면 ${ALARM_UNIT}.service 가 텔레그램을 쏜다 (rc=3 = 원격 사본만 실패 포함)."
  echo "  로그: journalctl --user -u ${UNIT_NAME}.service"
}

_uninstall() {
  command -v systemctl > /dev/null 2>&1 || die "systemctl 이 없다" 1
  systemctl --user disable --now "${UNIT_NAME}.timer" > /dev/null 2>&1 || true
  rm -f "${UNIT_DIR}/${UNIT_NAME}.timer" "${UNIT_DIR}/${UNIT_NAME}.service" "${UNIT_DIR}/${ALARM_UNIT}.service"
  systemctl --user daemon-reload > /dev/null 2>&1 || true
  echo "✓ 해제 완료 (백업 파일은 남긴다: ${BACKUP_DIR})"
}

# ── status ────────────────────────────────────────────────────────────────────
# ★「타이머가 waiting」은 건강 신호가 아니다 ([BL-737], 2026-08-15). 2026-08-13 재배치가
#   스크립트를 옮기자 soak-watch 유닛은 41시간 동안 rc=127 로 죽었고 알림은 0줄이었다.
#   재는 것은 「유닛이 있나」가 아니라 **무엇을 가리키나**다.
_installed_execstart() {
  local f="${UNIT_DIR}/${UNIT_NAME}.service"
  [ -f "${f}" ] || return 0
  sed -n 's|^ExecStart=/bin/bash \(.*\) run$|\1|p' "${f}" | head -1
}

_status() {
  local got want="${SCRIPT_DIR}/db-backup.sh" rc=0 last count total af

  echo "── 설치본 신선도 ──"
  got="$(_installed_execstart)"
  if [ -z "${got}" ]; then
    echo "  ✗ 설치된 유닛이 없다 (${UNIT_DIR}/${UNIT_NAME}.service)"
    rc=1
  else
    if [ ! -f "${got}" ]; then
      echo "  ✗ ExecStart 가 없는 파일을 가리킨다 — 이 유닛은 rc=127 로 죽는다: ${got}"
      rc=1
    elif [ "${got}" != "${want}" ]; then
      echo "  ✗ ExecStart 가 이 파일이 아니다 — 재설치해라 (--install)"
      echo "      설치본: ${got}"
      echo "      현재본: ${want}"
      rc=1
    else
      echo "  ✓ ExecStart = ${got}"
    fi
    af="${UNIT_DIR}/${ALARM_UNIT}.service"
    if [ ! -f "${af}" ]; then
      echo "  ✗ 실패 알림 유닛이 없다 — 백업이 죽어도 조용하다 (${af})"
      rc=1
    else
      echo "  ✓ 실패 알림 유닛 있음"
    fi
  fi

  echo "── 타이머 ──"
  if command -v systemctl > /dev/null 2>&1; then
    systemctl --user list-timers "${UNIT_NAME}.timer" --no-pager 2> /dev/null || echo "  (조회 실패)"
  else
    echo "  systemctl 이 없다 (리눅스 전용)"
  fi

  echo "── 백업 파일 (${BACKUP_DIR}) ──"
  if [ -d "${BACKUP_DIR}" ]; then
    # shellcheck disable=SC2012  # 파일명이 `quantbridge-<UTC 스탬프>.dump` 로 고정이라 안전하다
    last="$(ls -1t "${BACKUP_DIR}"/quantbridge-*.dump 2> /dev/null | head -1)" || true
    count="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'quantbridge-*.dump' 2> /dev/null | grep -c . || true)"
    total="$(du -sh "${BACKUP_DIR}" 2> /dev/null | cut -f1)" || total="?"
    echo "  보관 ${count}개 / ${total:-?}"
    if [ -n "${last:-}" ]; then
      echo "  최근: ${last}"
      # ★`[ -f x ] && cmd` 를 쓰면 안 된다 — set -e 아래에서 **조건이 거짓일 때 목록 자체가
      #   rc=1** 이라 스크립트가 거기서 죽는다. if 로 쓴다.
      if [ -f "${last}.meta" ]; then sed 's/^/        /' "${last}.meta"; fi
    else
      echo "  ✗ 백업 파일이 하나도 없다"
      rc=1
    fi
  else
    echo "  ✗ 디렉터리가 없다"
    rc=1
  fi

  return "${rc}"
}

# ── dispatch ──────────────────────────────────────────────────────────────────
case "${1:-}" in
  run)
    [ "$#" -eq 1 ] || die "run 은 인자를 받지 않는다 (--help)" 1
    _run
    ;;
  verify-restore)
    shift
    [ "$#" -eq 1 ] || die "verify-restore 는 덤프 파일 하나를 받는다 (--help)" 1
    _verify_restore "$1"
    ;;
  --install)
    [ "$#" -eq 1 ] || die "--install 은 인자를 받지 않는다 (--help)" 1
    _install
    ;;
  --uninstall)
    [ "$#" -eq 1 ] || die "--uninstall 은 인자를 받지 않는다 (--help)" 1
    _uninstall
    ;;
  --status)
    [ "$#" -eq 1 ] || die "--status 는 인자를 받지 않는다 (--help)" 1
    _status
    ;;
  -h | --help)
    sed -n '2,59p' "$0"   # ★헤더 주석에 줄을 더하면 이 범위를 함께 옮겨라 (짝 하네스가 잰다)
    ;;
  *)
    echo "알 수 없는 인자: ${1:-(없음)}  (run / verify-restore <덤프> / --install / --uninstall / --status / --help)" >&2
    exit 1
    ;;
esac
