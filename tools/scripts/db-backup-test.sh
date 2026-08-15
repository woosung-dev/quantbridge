#!/usr/bin/env bash
# db-backup 하네스 — [BL-767] / [ADR-033] 조건 ⑴. 전건 통과 = 종료 코드 0.
#
# 왜 필요한가
#   백업 스크립트의 고장 모드는 **전부 조용하다.** 0바이트 덤프가 쌓여도 디렉터리는 차 보이고,
#   격리 DB 를 백업해도 파일 크기는 그럴듯하고, 원격 업로드가 죽어도 로컬 사본은 남는다.
#   그리고 이 스크립트에는 백업과 무관한 최대 위험이 하나 더 있다 — **컨테이너를 건드리면
#   서버의 24시간 소크 창이 끊긴다.** 그것은 백업 파일을 아무리 봐도 안 보인다.
#
# ★그래서 이 하네스의 뼈대는 **양성 대조 + 음성 대조 쌍**이다. 이 레포는 「검사기가 빈 입력을
#   초록으로 통과」한 사고를 여러 번 겪었다(BL-569 · BL-601 · BL-706 · LESSON-087). 그래서
#   ⑴ 정상 입력이 **초록**인지(판별력 있는 검사기인가)와 ⑵ 각 고장이 **빨강**인지를 같이 잰다.
#   금지어 검출기 자신도 합성 로그로 한 번 발화시켜 「검출기가 죽어서 통과」를 배제한다.
#
# ★판정 로직을 heredoc 에 베끼지 않는다. 임시 트리에 `db-backup.sh` **사본**을 두고 PATH 앞단에
#   가짜 `docker`/`systemctl`/`oci` 를 세워 **진짜 스크립트**를 겨눈다(`soak-stack-test.sh` 수법).
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 2회).
#
# 두 갈래로 나뉜다:
#   A. 스텁 갈래 — docker·DB·네트워크 의존 0. **항상 돈다.**
#   B. 실 DB 갈래 — 로컬 `quantbridge-db` 가 떠 있을 때만. 없으면 skip.
#      ★단 skip 이 전부여서 「0건 실행 초록」이 되면 안 된다 — 마지막에 실행 건수를 세고
#        스텁 갈래가 안 돌았으면 red 다.
#
# 사용법: tools/scripts/db-backup-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
SCRIPT="$ROOT/tools/scripts/db-backup.sh"
[ -f "$SCRIPT" ] || {
  echo "✗ 백업 스크립트가 없다: $SCRIPT" >&2
  exit 1
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
SKIP=0
STUB_GROUP_RAN=0
OUT=""
RC=0

report() { # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-56s %s\n' "$1" "$2"
    printf '%s\n' "RC=$RC OUT=[$OUT]" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-56s\n' "$1"
  fi
}

skip() { # skip <label> <사유>
  SKIP=$((SKIP + 1))
  printf '  ⊘ %-56s %s\n' "$1" "$2"
}

# ══════════════════════════════════════════════════════════════════════════════
# 스텁 트리
# ══════════════════════════════════════════════════════════════════════════════
TREE="$TMP/tree"
TREE_REAL=""
BIN="$TMP/bin"

_build_tree() {
  mkdir -p "$TREE/tools/scripts" "$TREE/apps/api" "$BIN"
  cp "$SCRIPT" "$TREE/tools/scripts/db-backup.sh"
  chmod +x "$TREE/tools/scripts/db-backup.sh"
  TREE_REAL="$(cd "$TREE" && pwd -P)"

  # ── 가짜 docker ──────────────────────────────────────────────────────────────
  # ★모든 호출의 argv 를 통째로 기록한다. 「compose up 을 안 불렀다」는 **기록이 있어야**
  #   말할 수 있다 — 빈 로그로 통과하면 그것이 곧 fail-open 이다.
  cat > "$BIN/docker" << 'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${QB_STUB_LOG:?}"

_sql=""; for _a in "$@"; do _sql="$_a"; done
_db=""; _prev=""; for _a in "$@"; do [ "$_prev" = "-d" ] && _db="$_a"; _prev="$_a"; done

case "$1" in
  version) printf '%s\n' "99.0.0-stub"; exit 0 ;;

  inspect)
    [ "$2" = "${QB_STUB_CONTAINER}" ] || exit 1
    case "$4" in
      *State.Status*) printf '%s\n' "${QB_STUB_STATUS}" ;;
      *Config.Image*) printf '%s\n' "${QB_STUB_IMAGE}" ;;
      *Config.Env*)   printf 'POSTGRES_USER=%s\nPOSTGRES_DB=%s\n' "${QB_STUB_USER}" "${QB_STUB_DBNAME}" ;;
      *) exit 1 ;;
    esac
    exit 0 ;;

  port) printf '127.0.0.1:%s\n' "${QB_STUB_PORT}"; exit 0 ;;

  cp)
    [ "${QB_STUB_CP_RC}" = "0" ] || exit "${QB_STUB_CP_RC}"
    case "$2" in
      *:*) head -c "${QB_STUB_BYTES}" /dev/zero > "$3" ;;   # 컨테이너 → 호스트
      *)   : ;;                                             # 호스트 → 컨테이너 (no-op)
    esac
    exit 0 ;;

  exec)
    case "$3" in
      psql)
        case "$_sql" in
          *current_database\(\)*)
            printf '%s|%s|15.6\n' "${QB_STUB_PROBE_DB}" "${QB_STUB_TSVER}"; exit 0 ;;
          *information_schema.tables*)
            if [ "$_db" = "${QB_STUB_VERIFY_FACTS_DB:-__none__}" ]; then
              printf '%s\n' "${QB_STUB_VERIFY_FACTS}"
            else
              printf '%s\n' "${QB_STUB_FACTS}"
            fi
            exit 0 ;;
          *CREATE\ DATABASE*)   exit "${QB_STUB_CREATEDB_RC}" ;;
          *DROP\ DATABASE*)     exit 0 ;;
          *CREATE\ EXTENSION*)  exit 0 ;;
          *pre_restore*)        printf 't\n'; exit 0 ;;
          *post_restore*)       printf 't\n'; exit 0 ;;
          *) exit 0 ;;
        esac ;;
      pg_dump)    exit "${QB_STUB_PGDUMP_RC}" ;;
      pg_restore)
        case "$4" in
          --list) exit "${QB_STUB_LIST_RC}" ;;
          *)      exit "${QB_STUB_RESTORE_RC}" ;;
        esac ;;
      rm) exit 0 ;;
      *)  exit 0 ;;
    esac ;;

  *) exit 0 ;;
esac
STUB
  chmod +x "$BIN/docker"

  # 가짜 systemctl — is-enabled 만 1 을 낸다 (soak-watch-test.sh 와 같은 형태)
  cat > "$BIN/systemctl" << 'STUB'
#!/usr/bin/env bash
case "$*" in
  *is-enabled*) exit 1 ;;
esac
exit 0
STUB
  chmod +x "$BIN/systemctl"

  # 가짜 oci — QB_FAKE_OCI_RC 로 성공/실패를 고르고, QB_FAKE_OCI_LOG 가 있으면 argv 를 남긴다.
  # ★argv 기록이 없으면 「업로드했다」만 알 뿐 **무슨 이름으로** 올렸는지 못 잰다(prefix 축).
  cat > "$BIN/oci-stub" << 'STUB'
#!/usr/bin/env bash
[ -n "${QB_FAKE_OCI_LOG:-}" ] && printf '%s\n' "$*" >> "$QB_FAKE_OCI_LOG"
exit "${QB_FAKE_OCI_RC:-0}"
STUB
  chmod +x "$BIN/oci-stub"

  # .env.local 대역 — DATABASE_URL 포트 대조 축
  printf 'DATABASE_URL=postgresql+asyncpg://quantbridge:pw@localhost:5433/quantbridge\n' \
    > "$TMP/fake.env.local"
  printf 'DATABASE_URL=postgresql+asyncpg://quantbridge:pw@localhost:9999/quantbridge\n' \
    > "$TMP/wrong-port.env.local"
  # ★포트는 맞고 **DB 이름만** 다르다 — 2026-08-16 codex P1 이 연 구멍이다.
  #   한 컨테이너에 DB 가 여럿이면 포트 대조만으로는 앱이 안 쓰는 DB 를 백업하고도 초록이 난다.
  printf 'DATABASE_URL=postgresql+asyncpg://quantbridge:pw@localhost:5433/another_db\n' \
    > "$TMP/wrong-name.env.local"
  # 쿼리스트링이 붙어도 이름을 바르게 떼는지 (음성 대조가 문자열 비교로 새지 않게)
  printf 'DATABASE_URL=postgresql+asyncpg://quantbridge:pw@localhost:5433/quantbridge?sslmode=require\n' \
    > "$TMP/qs.env.local"
  printf 'TELEGRAM_BOT_TOKEN=x\nTELEGRAM_CHAT_ID=y\n' > "$TMP/fake.telegram.env"
}

_reset_stub() {
  export QB_STUB_LOG="$TMP/docker.log"
  export QB_STUB_CONTAINER="quantbridge-db"
  export QB_STUB_STATUS="running"
  export QB_STUB_IMAGE="timescale/timescaledb:2.14.2-pg15"
  export QB_STUB_USER="quantbridge"
  export QB_STUB_DBNAME="quantbridge"
  export QB_STUB_PROBE_DB="quantbridge"
  export QB_STUB_TSVER="2.14.2"
  export QB_STUB_PORT="5433"
  export QB_STUB_FACTS="19|21649|59"
  export QB_STUB_VERIFY_FACTS="19|21649|59"
  export QB_STUB_VERIFY_FACTS_DB="__none__"
  export QB_STUB_BYTES="4096"
  export QB_STUB_CP_RC="0"
  export QB_STUB_PGDUMP_RC="0"
  export QB_STUB_LIST_RC="0"
  export QB_STUB_RESTORE_RC="0"
  export QB_STUB_CREATEDB_RC="0"
  export QB_FAKE_OCI_RC="0"

  export QB_DB_CONTAINER="quantbridge-db"
  export QB_BACKUP_DIR="$TMP/backups"
  export QB_BACKUP_RETAIN_DAYS="14"
  export QB_ENV_FILE="$TMP/fake.env.local"
  export QB_OCI_BIN="/nonexistent-oci"
  export QB_SKIP_UPLOAD="1"
  unset QB_ALLOW_VERSION_SKEW QB_DB_USER QB_DB_NAME
  rm -rf "$TMP/backups"
  mkdir -p "$TMP/backups"
  : > "$TMP/docker.log"
}

_stub_run() { # _stub_run <서브커맨드…>  → $OUT / $RC
  # ★파이프 없음 — 명령 치환의 종료 코드가 곧 스크립트의 종료 코드다.
  OUT="$(PATH="$BIN:$PATH" bash "$TREE/tools/scripts/db-backup.sh" "$@" 2>&1)"
  RC=$?
}

_dumps() { find "$TMP/backups" -maxdepth 1 -name 'quantbridge-*.dump' 2> /dev/null | sort; }
_dump_count() { _dumps | grep -c . || true; }

# ★금지어 검출기. 이 함수 자체를 합성 로그로 한 번 발화시켜 **판별력**을 증명한다.
_forbidden_hits() { # _forbidden_hits <로그파일> → 위반 줄
  grep -E '(^|[[:space:]])(compose[[:space:]]+)?(up|down|restart|stop|start)([[:space:]]|$)' "$1" 2> /dev/null || true
}

echo "══ db-backup 하네스  (임시 사본 · 가짜 docker/systemctl/oci) ══"
echo "  대상: $SCRIPT"
echo

_build_tree

# ══════════════════════════════════════════════════════════════════════════════
# A. 스텁 갈래 — docker·DB·네트워크 의존 0
# ══════════════════════════════════════════════════════════════════════════════
echo "── A. 스텁 갈래 (항상 실행) ──"

# ── ① 음성 대조: 정상 입력은 **초록**이어야 한다 ────────────────────────────────
#    ★이것이 없으면 「늘 빨강인 검사기」가 아래 양성 케이스를 전건 통과한다 = 판별력 0.
_reset_stub
_stub_run run
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
[ "$(_dump_count)" = "1" ] || _why="${_why}★덤프가 $(_dump_count)개다(기대 1) "
[ -f "$(_dumps | head -1).meta" ] || _why="${_why}★사이드카 메타가 없다 "
printf '%s' "$OUT" | grep -q "백업 완료" || _why="${_why}완료 로그가 없다 "
printf '%s' "$OUT" | grep -q "대상 증명 ✓" || _why="${_why}대상 증명 로그가 없다 "
report "① 음성 대조 — 정상 run 은 rc=0 + 덤프 + 메타" "$_why"

# ── ② ★★소크 창 보호: compose up/down/restart/stop/start 를 한 번도 안 부른다 ──
#    ★이 회차의 핵심 수용 기준이다. 서버에서 24h 소크 창이 돌고 있고 컨테이너를 건드리면
#      그 창이 끊긴다 — 백업 산출물만 봐서는 절대 안 보이는 고장이다.
_why=""
_hits="$(_forbidden_hits "$TMP/docker.log")"
[ -z "$_hits" ] || _why="★금지 동사 호출: $(printf '%s' "$_hits" | tr '\n' ';') "
printf '%s' "$(grep -c 'compose' "$TMP/docker.log" || true)" | grep -qx 0 \
  || _why="${_why}★docker compose 를 불렀다 "
report "② run 은 compose up/down/restart/stop/start 를 안 부른다" "$_why"

# ── ②b 양성 대조: 로그가 **비어서** 통과한 것이 아니다 ──────────────────────────
_why=""
grep -q '^exec quantbridge-db pg_dump' "$TMP/docker.log" || _why="${_why}★pg_dump 호출 기록이 없다 "
grep -q '^cp quantbridge-db:' "$TMP/docker.log" || _why="${_why}★docker cp 기록이 없다 "
grep -q '^inspect quantbridge-db' "$TMP/docker.log" || _why="${_why}★inspect 기록이 없다 "
report "②b 양성 대조 — 스텁 로그에 exec/cp/inspect 가 실제로 남았다" "$_why"

# ── ②c 양성 대조: 금지어 **검출기 자신**이 발화한다 ─────────────────────────────
#    ★검출기가 죽어 있어도 ② 는 초록이다. 합성 로그로 검출기를 한 번 울려 본다.
_why=""
printf 'inspect quantbridge-db --format x\ncompose -f a.yml up -d\n' > "$TMP/synthetic.log"
[ -n "$(_forbidden_hits "$TMP/synthetic.log")" ] || _why="★검출기가 'compose up' 을 못 잡는다 (판별력 0) "
printf 'exec quantbridge-db pg_dump -Fc\ncp quantbridge-db:/tmp/x /out\n' > "$TMP/synthetic2.log"
[ -z "$(_forbidden_hits "$TMP/synthetic2.log")" ] || _why="${_why}★검출기가 정상 로그를 오탐한다 "
report "②c 금지어 검출기 자신의 양성·음성 대조" "$_why"

# ── ③ 대상 증명 — 없는 컨테이너 ────────────────────────────────────────────────
_reset_stub
QB_DB_CONTAINER="not-a-real-container" _stub_run run
_why=""
[ "$RC" -eq 2 ] || _why="종료코드=$RC(기대 2 — 전제 미충족) "
[ "$(_dump_count)" = "0" ] || _why="${_why}★덤프가 만들어졌다 "
report "③ 없는 컨테이너 → rc=2 · 산출물 없음" "$_why"

# ── ④ 대상 증명 — 이미지가 timescaledb 계열이 아니다 ───────────────────────────
#    ★compose 3벌이 `container_name: quantbridge-db` 를 공유하므로 "지금 뜬 것"이 대상이 된다.
#      postgres/pgvector 가 그 이름으로 떠 있으면 덤프는 만들어지지만 쓸모가 없다.
_reset_stub
QB_STUB_IMAGE="postgres:16-alpine" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "timescaledb 계열이 아니다" || _why="${_why}진단 문구가 없다 "
[ "$(_dump_count)" = "0" ] || _why="${_why}★덤프가 만들어졌다 "
report "④ 이미지가 timescaledb 계열이 아니면 rc=1" "$_why"

# ── ⑤ 대상 증명 — current_database() 불일치 ────────────────────────────────────
_reset_stub
QB_STUB_PROBE_DB="quantbridge_test" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "current_database()" || _why="${_why}진단 문구가 없다 "
report "⑤ current_database() 불일치 → rc=1" "$_why"

# ── ⑥ 대상 증명 — timescaledb 확장이 없다 ──────────────────────────────────────
_reset_stub
QB_STUB_TSVER="" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "timescaledb 확장이 없다" || _why="${_why}진단 문구가 없다 "
report "⑥ timescaledb 확장 부재 → rc=1" "$_why"

# ── ⑦ 대상 증명 — DATABASE_URL 이 다른 포트를 가리킨다 ─────────────────────────
_reset_stub
QB_ENV_FILE="$TMP/wrong-port.env.local" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "DATABASE_URL" || _why="${_why}진단 문구가 없다 "
report "⑦ DATABASE_URL 포트 불일치 → rc=1 (앱이 안 쓰는 DB 백업 차단)" "$_why"

# ── ⑦b 음성 대조: 같은 포트면 통과한다 (⑦ 이 늘 빨강인 검사기가 아님) ──────────
_reset_stub
_stub_run run
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
report "⑦b 음성 대조 — 포트가 맞으면 통과" "$_why"

# ── ⑦c ★포트는 맞고 DB **이름**만 다르면 거부한다 (2026-08-16 codex P1) ─────────
#    한 컨테이너에 DB 가 여럿이면 포트 대조만으로는 앱이 안 쓰는 DB 를 떠 놓고 「성공」이라
#    말한다. 엉뚱한 DB 백업은 **실패로 보이지 않는 실패**라 여기서 잡아야 한다.
_reset_stub
QB_ENV_FILE="$TMP/wrong-name.env.local" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "another_db" || _why="${_why}진단에 실제 이름이 없다 "
[ "$(_dump_count)" = "0" ] || _why="${_why}★거부했는데 덤프가 생겼다 "
report "⑦c DB 이름 불일치 → rc=1 (포트만 같은 다른 DB 차단)" "$_why"

# ── ⑦d 음성 대조: 쿼리스트링이 붙어도 이름을 바르게 떼어 통과한다 ───────────────
#    ★이것이 없으면 ⑦c 는 「'/quantbridge' 문자열이 없으면 무조건 red」인 검사기여도 초록이다.
_reset_stub
QB_ENV_FILE="$TMP/qs.env.local" _stub_run run
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) — 쿼리스트링을 이름의 일부로 읽었다 "
report "⑦d 음성 대조 — DSN 쿼리스트링이 붙어도 통과" "$_why"

# ── ⑧ 덤프 크기 0 → 파일을 남기지 않고 rc=1 ────────────────────────────────────
#    ★0바이트 덤프가 쌓이면 「백업이 있다」가 거짓이 된다 (Makefile:312-324 와 같은 규칙).
_reset_stub
QB_STUB_BYTES="0" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
[ "$(_dump_count)" = "0" ] || _why="${_why}★빈 덤프가 남았다: $(_dumps | tr '\n' ' ') "
[ "$(find "$TMP/backups" -name '*.meta' | grep -c . || true)" = "0" ] || _why="${_why}★메타가 남았다 "
printf '%s' "$OUT" | grep -q "크기가 0" || _why="${_why}진단 문구가 없다 "
report "⑧ 덤프 크기 0 → 파일 미잔존 + rc=1" "$_why"

# ── ⑨ pg_dump 실패 → rc=1 · 산출물 없음 ────────────────────────────────────────
_reset_stub
QB_STUB_PGDUMP_RC="1" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
[ "$(_dump_count)" = "0" ] || _why="${_why}★덤프가 남았다 "
report "⑨ pg_dump 실패 → rc=1 · 산출물 없음" "$_why"

# ── ⑩ 헤더 판독 실패(손상 덤프) → 파일을 지우고 rc=1 ───────────────────────────
_reset_stub
QB_STUB_LIST_RC="1" _stub_run run
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
[ "$(_dump_count)" = "0" ] || _why="${_why}★손상 덤프가 남았다 "
printf '%s' "$OUT" | grep -q "헤더를 못 읽었다" || _why="${_why}진단 문구가 없다 "
report "⑩ pg_restore --list 실패 → 파일 삭제 + rc=1" "$_why"

# ── ⑪ 원격 업로드 실패는 **묻히지 않는다** (rc=3) — 단 로컬 덤프는 남는다 ──────
_reset_stub
QB_SKIP_UPLOAD="0" QB_OCI_BIN="$BIN/oci-stub" QB_FAKE_OCI_RC="1" _stub_run run
_why=""
[ "$RC" -eq 3 ] || _why="종료코드=$RC(기대 3 — 부분 성공) "
[ "$(_dump_count)" = "1" ] || _why="${_why}★로컬 덤프가 사라졌다 "
printf '%s' "$OUT" | grep -q "로컬 백업은 정상" || _why="${_why}진단 문구가 없다 "
report "⑪ 업로드 실패 → rc=3 + 로컬 덤프 보존" "$_why"

# ── ⑪b oci CLI 자체가 없으면 그것도 rc=3 (조용히 넘어가지 않는다) ──────────────
_reset_stub
QB_SKIP_UPLOAD="0" QB_OCI_BIN="/nonexistent-oci" _stub_run run
_why=""
[ "$RC" -eq 3 ] || _why="종료코드=$RC(기대 3) "
[ "$(_dump_count)" = "1" ] || _why="${_why}★로컬 덤프가 사라졌다 "
report "⑪b oci CLI 부재 → rc=3 (원격 사본 0 을 안 숨긴다)" "$_why"

# ── ⑪c 음성 대조: 업로드가 성공하면 rc=0 ───────────────────────────────────────
_reset_stub
QB_SKIP_UPLOAD="0" QB_OCI_BIN="$BIN/oci-stub" QB_FAKE_OCI_RC="0" _stub_run run
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
printf '%s' "$OUT" | grep -q "업로드 완료" || _why="${_why}완료 로그가 없다 "
report "⑪c 음성 대조 — 업로드 성공은 rc=0" "$_why"

# ── ⑪d ★prefix 가 객체 이름에 붙는다 (남의 버킷을 공유할 때의 경계) ────────────
#    2026-08-16 실측: 이 VM 의 Instance Principal 은 버킷 **생성** 권한이 없어
#    (`bucket create` 409 / `bucket get` **404**) 다른 앱 버킷을 빌려 쓴다. 그때 경계가
#    파일명 규칙에만 의존하면 저쪽이 규칙을 바꾸는 순간 섞인다.
_reset_stub
: > "$TMP/oci-argv"
QB_SKIP_UPLOAD="0" QB_OCI_BIN="$BIN/oci-stub" QB_FAKE_OCI_RC="0" \
  QB_FAKE_OCI_LOG="$TMP/oci-argv" QB_BACKUP_PREFIX="quantbridge" _stub_run run
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
grep -q -- '--name quantbridge/quantbridge-' "$TMP/oci-argv" 2> /dev/null \
  || _why="${_why}★객체 이름에 prefix 가 없다: $(sed -n 's/.*--name \([^ ]*\).*/\1/p' "$TMP/oci-argv" | tr '\n' ' ') "
report "⑪d prefix → 객체 이름이 <prefix>/<파일명>" "$_why"

# ── ⑪e 음성 대조: prefix 가 비면 붙이지 않는다 (늘 붙이는 구현이 아님) ─────────
_reset_stub
: > "$TMP/oci-argv"
QB_SKIP_UPLOAD="0" QB_OCI_BIN="$BIN/oci-stub" QB_FAKE_OCI_RC="0" \
  QB_FAKE_OCI_LOG="$TMP/oci-argv" _stub_run run
_why=""
grep -q -- '--name quantbridge-' "$TMP/oci-argv" 2> /dev/null \
  || _why="이름을 못 읽었다 "
grep -q -- '--name .*/' "$TMP/oci-argv" 2> /dev/null \
  && _why="${_why}★prefix 가 비었는데 슬래시가 들어갔다 "
report "⑪e 음성 대조 — prefix 가 비면 버킷 루트" "$_why"

# ── ⑫ 보관 정리 — 경과분은 지우고 신규분은 남긴다 (양성 + 음성 한 쌍) ──────────
_reset_stub
QB_BACKUP_RETAIN_DAYS="1"
export QB_BACKUP_RETAIN_DAYS
printf 'old\n' > "$TMP/backups/quantbridge-20200101T000000Z.dump"
printf 'old\n' > "$TMP/backups/quantbridge-20200101T000000Z.dump.meta"
printf 'new\n' > "$TMP/backups/quantbridge-29991231T235959Z.dump"
touch -t 202001010000 "$TMP/backups/quantbridge-20200101T000000Z.dump" \
  "$TMP/backups/quantbridge-20200101T000000Z.dump.meta"
_stub_run run
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
[ ! -f "$TMP/backups/quantbridge-20200101T000000Z.dump" ] || _why="${_why}★경과분이 안 지워졌다 "
[ ! -f "$TMP/backups/quantbridge-20200101T000000Z.dump.meta" ] || _why="${_why}★경과분 메타가 안 지워졌다 "
[ -f "$TMP/backups/quantbridge-29991231T235959Z.dump" ] || _why="${_why}★신규분이 지워졌다 "
report "⑫ 보관 정리 — 경과분 삭제 · 신규분 보존" "$_why"

# ── ⑬ 인자 계약 ────────────────────────────────────────────────────────────────
_reset_stub
_stub_run run --typo
_why=""
[ "$RC" -ne 0 ] || _why="★여분 인자를 삼켰다 (rc=0) "
report "⑬ run 이 여분 인자를 삼키지 않는다" "$_why"

_reset_stub
_stub_run --nonsense
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
report "⑬b 알 수 없는 인자 → rc=1" "$_why"

# ⑬c `--help` 가 헤더 주석만 낸다 — 범위가 밀리면 `set -euo` 가 새어 나온다
_reset_stub
_stub_run --help
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
printf '%s' "$OUT" | grep -q "verify-restore" || _why="${_why}사용법이 없다 "
printf '%s' "$OUT" | grep -q "set -euo" && _why="${_why}★sed 범위가 코드까지 먹었다 (헤더 줄 수 변경?) "
printf '%s' "$OUT" | grep -q "BL-767" || _why="${_why}헤더 첫 절이 안 나왔다 (sed 범위 시작이 밀렸다) "
report "⑬c --help 범위가 헤더 주석과 정확히 일치" "$_why"

# ══════════════════════════════════════════════════════════════════════════════
# verify-restore — 스텁 갈래
# ══════════════════════════════════════════════════════════════════════════════
_make_fake_dump() { # _make_fake_dump <경로> [tsver]
  head -c 4096 /dev/zero > "$1"
  cat > "$1.meta" << EOF
schema=1
created_at=20260816T000000Z
container=quantbridge-db
image=timescale/timescaledb:2.14.2-pg15
db=quantbridge
pg_version=15.6
timescaledb_version=${2:-2.14.2}
bytes=4096
tables_min=19
tables_max=19
ohlcv_rows_min=21649
ohlcv_rows_max=21649
chunks_min=59
chunks_max=59
EOF
}

# ── ⑭ 음성 대조: 정상 덤프는 rc=0 ─────────────────────────────────────────────
_reset_stub
_make_fake_dump "$TMP/ok.dump"
_stub_run verify-restore "$TMP/ok.dump"
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
printf '%s' "$OUT" | grep -q "복원 실증 ✓" || _why="${_why}실증 로그가 없다 "
report "⑭ 음성 대조 — 정상 덤프 verify-restore 는 rc=0" "$_why"

# ── ⑭b ★★앱 DB 를 절대 건드리지 않는다 ───────────────────────────────────────
#    ★1벌 공유라 앱 DB 에 restore 하면 소크가 죽는다. 복원 대상은 throwaway 뿐이어야 한다.
_why=""
grep -E '^exec quantbridge-db pg_restore .*-d quantbridge( |$)' "$TMP/docker.log" > /dev/null \
  && _why="${_why}★앱 DB 로 pg_restore 를 불렀다 "
grep -E 'DROP DATABASE' "$TMP/docker.log" | grep -qv 'qb_restore_verify_' \
  && _why="${_why}★throwaway 아닌 DB 를 DROP 했다 "
grep -q 'CREATE DATABASE qb_restore_verify_' "$TMP/docker.log" \
  || _why="${_why}★throwaway DB 를 만든 기록이 없다(로그가 비어 통과한 것 아닌가) "
grep -q 'DROP DATABASE IF EXISTS qb_restore_verify_' "$TMP/docker.log" \
  || _why="${_why}★throwaway DB 를 정리한 기록이 없다 "
report "⑭b verify-restore 는 throwaway DB 만 만들고 지운다" "$_why"

# ── ⑮ ★가장 중요: 손상된 덤프를 거부한다 (스텁 축) ────────────────────────────
_reset_stub
_make_fake_dump "$TMP/broken.dump"
QB_STUB_LIST_RC="1" _stub_run verify-restore "$TMP/broken.dump"
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "손상된 덤프" || _why="${_why}진단 문구가 없다 "
grep -q 'CREATE DATABASE' "$TMP/docker.log" && _why="${_why}★손상 판정 전에 DB 를 만들었다 "
report "⑮ 헤더 판독 실패 덤프 → rc=1 (DB 생성 전에)" "$_why"

# ── ⑮b pg_restore 가 실패해도 throwaway DB 는 반드시 정리된다 (trap) ───────────
_reset_stub
_make_fake_dump "$TMP/failrestore.dump"
QB_STUB_RESTORE_RC="1" _stub_run verify-restore "$TMP/failrestore.dump"
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
grep -q 'DROP DATABASE IF EXISTS qb_restore_verify_' "$TMP/docker.log" \
  || _why="${_why}★실패 경로에서 throwaway DB 가 안 지워졌다 (trap 미작동) "
report "⑮b pg_restore 실패 → rc=1 + throwaway DB 정리(trap)" "$_why"

# ── ⑯ 사이드카 메타가 없으면 fail-open 하지 않는다 (rc=2) ──────────────────────
#    ★기대값 없이 「복원은 됐다」만으로 초록을 내면 **빈 DB 가 복원돼도 통과**한다.
_reset_stub
head -c 4096 /dev/zero > "$TMP/nometa.dump"
_stub_run verify-restore "$TMP/nometa.dump"
_why=""
[ "$RC" -eq 2 ] || _why="종료코드=$RC(기대 2) "
printf '%s' "$OUT" | grep -q "메타가 없다" || _why="${_why}진단 문구가 없다 "
report "⑯ 메타 부재 → rc=2 (기대값 없이 초록을 내지 않는다)" "$_why"

# ── ⑰ TimescaleDB 버전 스큐 → 복원 **전에** 거부 ──────────────────────────────
#    ★덤프와 복원의 확장 버전이 다르면 catalog version mismatch 로 죽는다.
_reset_stub
_make_fake_dump "$TMP/skew.dump" "2.11.0"
_stub_run verify-restore "$TMP/skew.dump"
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "catalog version mismatch" || _why="${_why}진단 문구가 없다 "
grep -q 'CREATE DATABASE' "$TMP/docker.log" && _why="${_why}★버전 대조 전에 DB 를 만들었다 "
report "⑰ TimescaleDB 버전 스큐 → rc=1 (DB 생성 전에)" "$_why"

# ⑰b 탈출구가 실제로 동작한다 (⑰ 이 무조건 빨강이 아님을 보인다)
_reset_stub
_make_fake_dump "$TMP/skew2.dump" "2.11.0"
QB_ALLOW_VERSION_SKEW="1" _stub_run verify-restore "$TMP/skew2.dump"
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
report "⑰b QB_ALLOW_VERSION_SKEW=1 로 강행 가능 (음성 대조)" "$_why"

# ── ⑱ 복원본이 기대와 다르면 red — 「복원은 됐다」로 넘어가지 않는다 ───────────
_reset_stub
_make_fake_dump "$TMP/short.dump"
QB_STUB_VERIFY_FACTS_DB="" QB_STUB_FACTS="19|0|0" _stub_run verify-restore "$TMP/short.dump"
_why=""
[ "$RC" -eq 1 ] || _why="종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q "기대와 다르다" || _why="${_why}진단 문구가 없다 "
printf '%s' "$OUT" | grep -q "ohlcv 0행" || _why="${_why}어느 축이 틀렸는지 안 적었다 "
report "⑱ 복원본 행수/chunk 불일치 → rc=1" "$_why"

# ── ⑲ verify-restore 도 컨테이너를 기동/정지하지 않는다 ───────────────────────
_why=""
_hits="$(_forbidden_hits "$TMP/docker.log")"
[ -z "$_hits" ] || _why="★금지 동사 호출: $(printf '%s' "$_hits" | tr '\n' ';') "
report "⑲ verify-restore 도 compose 동사를 안 부른다" "$_why"

# ══════════════════════════════════════════════════════════════════════════════
# systemd 유닛 산출물
# ══════════════════════════════════════════════════════════════════════════════
_reset_stub
export XDG_CONFIG_HOME="$TMP/xdg"
rm -rf "$TMP/xdg"
QB_ENV_FILE="$TMP/fake.telegram.env" _stub_run --install
UNIT_SVC="$TMP/xdg/systemd/user/dev.quantbridge.db-backup.service"
ALARM_SVC="$TMP/xdg/systemd/user/dev.quantbridge.db-backup-alarm.service"
TIMER="$TMP/xdg/systemd/user/dev.quantbridge.db-backup.timer"

_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
if [ ! -f "$UNIT_SVC" ]; then
  _why="${_why}★서비스 유닛이 안 만들어졌다 "
else
  grep -qxF "ExecStart=/bin/bash $TREE_REAL/tools/scripts/db-backup.sh run" "$UNIT_SVC" \
    || _why="${_why}★ExecStart 가 이 파일이 아니다: $(sed -n 's/^ExecStart=//p' "$UNIT_SVC" | head -1) "
  grep -qxF "OnFailure=dev.quantbridge.db-backup-alarm.service" "$UNIT_SVC" \
    || _why="${_why}★OnFailure 가 없다 — 백업이 죽어도 조용하다 "
fi
report "⑳ --install 의 ExecStart = 현재 스크립트 + OnFailure" "$_why"

# ㉑ 알람 유닛의 두 함정 — `--fail` 과 `$$` 이스케이프
#    ★둘 다 이 레포에서 실제로 알람을 조용히 죽인 적이 있다(2026-08-15 서버 실측).
_why=""
if [ ! -f "$ALARM_SVC" ]; then
  _why="★실패 알림 유닛이 안 만들어졌다 "
else
  grep -q -- '--fail' "$ALARM_SVC" \
    || _why="${_why}★curl 에 --fail 이 없다 (HTTP 오류가 성공으로 보인다) "
  grep -q -- '--show-error' "$ALARM_SVC" \
    && _why="${_why}★--show-error 가 있다 (토큰 유출 경로) "
  grep -qF 'chat_id=$${TELEGRAM_CHAT_ID}' "$ALARM_SVC" \
    || _why="${_why}★chat_id 가 \$\$ 이스케이프가 아니다 (systemd 가 빈 값으로 확장한다) "
  grep -qF 'bot$${TELEGRAM_BOT_TOKEN}' "$ALARM_SVC" \
    || _why="${_why}★봇 토큰이 \$\$ 이스케이프가 아니다 "
  grep -qE '[^$]\$\{TELEGRAM' "$ALARM_SVC" \
    && _why="${_why}★단일 \$ 형태의 TELEGRAM 참조가 남아 있다 "
  grep -q 'TELEGRAM_BOT_TOKEN=x' "$ALARM_SVC" \
    && _why="${_why}★토큰 **값**이 유닛에 박혔다 "
  grep -q -- "$TMP/fake.telegram.env" "$ALARM_SVC" \
    || _why="${_why}★env 파일 경로가 안 박혔다 "
fi
report "㉑ 알람 유닛 · --fail · \$\$ 이스케이프 · 토큰 미포함" "$_why"

# ㉒ 타이머는 **벽시계 고정**이고 truewords(00/06/12/18)와 어긋난다
#    ★존재 확인이 아니라 **집합 동등**으로 잰다 — 「OnCalendar 가 있나」만 보면 두 번째
#      OnCalendar 가 추가돼도, AccuracySec 이 지워져도 통과한다.
_why=""
if [ ! -f "$TIMER" ]; then
  _why="★타이머 유닛이 안 만들어졌다 "
else
  _got="$(sed -n '/^\[Timer\]/,/^\[Install\]/p' "$TIMER" | grep -E '^[A-Za-z]+=' | sort | tr '\n' ' ')"
  _want="AccuracySec=1min OnCalendar=03,09,15,21:00 Persistent=true "
  [ "$_got" = "$_want" ] || _why="★[Timer] 키 집합이 다르다: [$_got] (기대 [$_want]) "
fi
report "㉒ 타이머 [Timer] 집합 동등 — 03·09·15·21시 벽시계 고정" "$_why"

# ㉓ `--status` 음성 대조 → 갓 설치한 것은 신선하다 / 양성 → 옛 경로면 red
_reset_stub
export XDG_CONFIG_HOME="$TMP/xdg"
printf 'x\n' > "$TMP/backups/quantbridge-20260816T000000Z.dump"
_stub_run --status
_why=""
[ "$RC" -eq 0 ] || _why="★갓 설치한 설치본인데 rc=$RC (기대 0 — 판별력 없는 검사기) "
printf '%s' "$OUT" | grep -q "설치본 신선도" || _why="${_why}신선도 절이 없다 "
report "㉓ --status 음성 대조 — 갓 설치한 것은 green" "$_why"

sed -i.bak "s|^ExecStart=/bin/bash .*|ExecStart=/bin/bash $TMP/gone/db-backup.sh run|" "$UNIT_SVC"
_stub_run --status
_why=""
[ "$RC" -eq 1 ] || _why="★ExecStart 가 없는 경로인데 rc=$RC (기대 1) "
printf '%s' "$OUT" | grep -q "rc=127" || _why="${_why}진단 문구가 없다 "
report "㉓b --status 양성 대조 — 옛 경로 설치본은 red" "$_why"

# ㉔ `--uninstall` 이 유닛 3종을 지운다
_reset_stub
export XDG_CONFIG_HOME="$TMP/xdg"
_stub_run --uninstall
_why=""
[ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
[ ! -f "$UNIT_SVC" ] || _why="${_why}★서비스 유닛이 남았다 "
[ ! -f "$ALARM_SVC" ] || _why="${_why}★알람 유닛이 남았다 "
[ ! -f "$TIMER" ] || _why="${_why}★타이머 유닛이 남았다 "
report "㉔ --uninstall 이 유닛 3종을 지운다" "$_why"
unset XDG_CONFIG_HOME

STUB_GROUP_RAN=1

# ══════════════════════════════════════════════════════════════════════════════
# B. 실 DB 갈래 — 로컬 quantbridge-db 가 떠 있을 때만
# ══════════════════════════════════════════════════════════════════════════════
echo
echo "── B. 실 DB 갈래 (컨테이너 없으면 skip) ──"

# ★스텁 갈래가 export 한 QB_* 를 **전부 걷어낸다.** 안 걷으면 실 DB 갈래가 스텁의 잔재를
#   물려받아, 여기서 나는 red 가 어느 갈래 것인지 알 수 없게 된다(뮤테이션 검증 중 실제로
#   겪었다 — 앞 회차가 남긴 throwaway DB 때문에 무관한 변이가 red 로 보였다).
unset QB_STUB_LOG QB_STUB_CONTAINER QB_STUB_STATUS QB_STUB_IMAGE QB_STUB_USER \
  QB_STUB_DBNAME QB_STUB_PROBE_DB QB_STUB_TSVER QB_STUB_PORT QB_STUB_FACTS \
  QB_STUB_VERIFY_FACTS QB_STUB_VERIFY_FACTS_DB QB_STUB_BYTES QB_STUB_CP_RC \
  QB_STUB_PGDUMP_RC QB_STUB_LIST_RC QB_STUB_RESTORE_RC QB_STUB_CREATEDB_RC QB_FAKE_OCI_RC \
  QB_DB_CONTAINER QB_BACKUP_DIR QB_BACKUP_RETAIN_DAYS QB_ENV_FILE QB_OCI_BIN QB_SKIP_UPLOAD

_have_real_db() {
  command -v docker > /dev/null 2>&1 || return 1
  docker version --format '{{.Server.Version}}' > /dev/null 2>&1 || return 1
  [ "$(docker inspect quantbridge-db --format '{{.State.Status}}' 2> /dev/null)" = "running" ] || return 1
  case "$(docker inspect quantbridge-db --format '{{.Config.Image}}' 2> /dev/null)" in
    *timescale/timescaledb*) return 0 ;;
    *) return 1 ;;
  esac
}

_leftover_verify_dbs() {
  docker exec quantbridge-db psql -U quantbridge -d postgres -X -q -A -t \
    -c "SELECT count(*) FROM pg_database WHERE datname LIKE 'qb\\_restore\\_verify\\_%';" 2> /dev/null
}

if ! _have_real_db; then
  skip "㉕ 실 DB run → 덤프 생성" "quantbridge-db 가 없다"
  skip "㉖ 실 덤프 verify-restore → rc=0" "quantbridge-db 가 없다"
  skip "㉗ ★잘라낸 덤프 verify-restore → rc≠0" "quantbridge-db 가 없다"
  skip "㉘ throwaway DB 잔존 0" "quantbridge-db 가 없다"
else
  # ★㉘ 이 **이번 실행의 누수**만 재게 하려면 앞선 실행의 잔재를 먼저 걷어야 한다.
  #   지우기 전에 반드시 소리 내어 말한다 — 조용히 지우면 누수가 영영 안 보인다.
  _stale="$(docker exec quantbridge-db psql -U quantbridge -d postgres -X -q -A -t \
    -c "SELECT datname FROM pg_database WHERE datname LIKE 'qb\\_restore\\_verify\\_%';" 2> /dev/null)"
  if [ -n "$_stale" ]; then
    printf '  ⚠️ 앞선 실행이 남긴 throwaway DB 를 걷어낸다 (이번 실행의 누수와 섞이지 않게):\n'
    printf '%s\n' "$_stale" | sed 's/^/       /'
    printf '%s\n' "$_stale" | while read -r _d; do
      [ -n "$_d" ] && docker exec quantbridge-db psql -U quantbridge -d postgres -X -q -A -t \
        -c "DROP DATABASE IF EXISTS ${_d};" > /dev/null 2>&1
    done
  fi

  REAL_DIR="$TMP/real-backups"
  rm -rf "$REAL_DIR"
  mkdir -p "$REAL_DIR"
  _real_run() { # _real_run <서브커맨드…>
    OUT="$(QB_BACKUP_DIR="$REAL_DIR" QB_SKIP_UPLOAD=1 QB_BACKUP_RETAIN_DAYS=14 \
      QB_DB_CONTAINER=quantbridge-db QB_ENV_FILE="$ROOT/apps/api/.env.local" \
      bash "$SCRIPT" "$@" 2>&1)"
    RC=$?
  }

  # ㉕ 진짜 pg_dump — 컨테이너를 안 건드리고 덤프가 나온다
  _real_run run
  REAL_DUMP="$(find "$REAL_DIR" -maxdepth 1 -name 'quantbridge-*.dump' | head -1)"
  _why=""
  [ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
  [ -n "$REAL_DUMP" ] || _why="${_why}★덤프가 안 나왔다 "
  [ -n "$REAL_DUMP" ] && [ -s "$REAL_DUMP" ] || _why="${_why}★덤프가 비었다 "
  [ -n "$REAL_DUMP" ] && [ -f "$REAL_DUMP.meta" ] || _why="${_why}★메타가 없다 "
  report "㉕ 실 DB run → 덤프 + 메타 (컨테이너 미조작)" "$_why"

  # ㉖ 음성 대조 — 멀쩡한 덤프는 실제로 복원되고 사실이 일치한다
  if [ -n "$REAL_DUMP" ]; then
    # ☹ **이 하네스가 못 재는 축** — `timescaledb_pre_restore()`/`post_restore()` 의 유무.
    #   2026-08-16 실측: 지금 스키마에서는 둘을 지워도 pg_restore rc=0 · stderr 0줄 ·
    #   chunk 59 · 21,649행 · INSERT 라우팅 정상으로 **완전히 같다**(하네스도 39/39 초록).
    #   그러니 「이 테스트가 pre_restore 를 지킨다」고 읽지 마라 — 지키는 것은 문서뿐이다.
    #   continuous aggregate·압축·정책이 생기면 그때 판별력이 생길 수 있다(그때 다시 재라).
    _real_run verify-restore "$REAL_DUMP"
    _why=""
    [ "$RC" -eq 0 ] || _why="종료코드=$RC(기대 0) "
    printf '%s' "$OUT" | grep -q "복원 실증 ✓" || _why="${_why}실증 로그가 없다 "
    report "㉖ 음성 대조 — 실 덤프 verify-restore rc=0" "$_why"

    # ㉗ ★★양성 대조 — 잘라낸 덤프는 반드시 빨강이어야 한다. 이 하네스의 존재 이유다.
    head -c 100000 "$REAL_DUMP" > "$TMP/real-trunc.dump"
    cp "$REAL_DUMP.meta" "$TMP/real-trunc.dump.meta"
    _real_run verify-restore "$TMP/real-trunc.dump"
    _why=""
    [ "$RC" -ne 0 ] || _why="★잘라낸 덤프인데 rc=0 이다 (검사기가 아무것도 안 본다) "
    report "㉗ ★잘라낸 덤프 verify-restore → rc≠0" "$_why"

    # ㉘ 실패 경로를 지나온 뒤에도 throwaway DB 가 남아 있으면 안 된다
    _why=""
    _left="$(_leftover_verify_dbs)"
    [ "$_left" = "0" ] || _why="★qb_restore_verify_% DB 가 ${_left:-?}개 남았다 "
    report "㉘ throwaway DB 잔존 0 (trap 정리)" "$_why"
  else
    skip "㉖ 실 덤프 verify-restore → rc=0" "㉕ 에서 덤프가 안 나왔다"
    skip "㉗ ★잘라낸 덤프 verify-restore → rc≠0" "㉕ 에서 덤프가 안 나왔다"
    skip "㉘ throwaway DB 잔존 0" "㉕ 에서 덤프가 안 나왔다"
  fi
fi

# ══════════════════════════════════════════════════════════════════════════════
echo
EXECUTED=$((PASS + FAIL))
echo "실행 ${EXECUTED}건 (통과 ${PASS} / 실패 ${FAIL}) · skip ${SKIP}건"

# ★「전부 skip 이라 초록」을 막는다. 스텁 갈래는 의존이 0 이므로 **언제나** 돌아야 한다.
if [ "$EXECUTED" -eq 0 ] || [ "$STUB_GROUP_RAN" -ne 1 ]; then
  echo "✗ 실행된 검사가 없다 — 「0건 실행 초록」은 통과가 아니다" >&2
  exit 1
fi

if [ "$FAIL" -ne 0 ]; then
  echo "✗ db-backup 하네스 실패 (${FAIL}건 실패 / ${PASS}건 통과)" >&2
  exit 1
fi
echo "✓ db-backup 하네스 전건 통과 (${PASS}건 · skip ${SKIP}건)"
