#!/usr/bin/env bash
#
# 워크트리 병렬 작업 부트스트랩 — 새 워크트리를 "실행 가능한" 상태로 만든다.
#
# 사용법:
#   tools/scripts/worktree-bootstrap.sh              # 슬롯 자동 할당 + deps 설치
#   tools/scripts/worktree-bootstrap.sh --slot 2     # 슬롯 지정 (다른 워크트리가 쥔 번호면 거부한다)
#   tools/scripts/worktree-bootstrap.sh --skip-deps  # deps 설치 생략
#   tools/scripts/worktree-bootstrap.sh --skip-db    # 테스트 DB 생성 생략 (문서/계획 전용 워크트리)
#   tools/scripts/worktree-bootstrap.sh --adopt-env  # env 가 없으면 죽지 말고 메인에서 복사해 온다
#                                              # (git worktree add / herdr 로 만든 워크트리용 — §3)
#
# 재실행은 안전하다 — 이미 슬롯이 있으면 그 번호를 유지한다(바뀌면 떠 있는 서버와 어긋난다).
#
# 무엇을 격리하고 무엇을 공유하는가 — 판단 기준은 "이 작업이 남의 상태를 지우는가":
#
#   격리(슬롯별)          공유(스택 1벌)
#   ─────────────────    ──────────────────────────────────────
#   FE 포트 3100+N        Postgres 인스턴스 (host 5433)
#   BE 포트 8100+N        Redis 인스턴스 (host 6380)
#   pytest DB             앱 DB `quantbridge` (마이그레이션·시드 비용이 커서 공유)
#   Redis lock DB (3+N)   celery broker/result (0,1,2)
#
# pytest DB 를 격리하는 이유는 conftest.py 가 세션 시작마다 drop_all + create_all 하기 때문이다.
# 공유하면 두 워크트리가 서로의 테이블을 날린다. 인스턴스가 아니라 DB 이름만 나누면 되므로
# 추가 컨테이너는 필요 없다.
#
# ⚠️ 이 스크립트로도 해결되지 않는 구조적 제약 — docs/development/worktree-parallel.md §3 참조.
#    celery worker 컨테이너가 메인 체크아웃의 `./apps/api/src` 를 bind-mount 하므로,
#    워크트리에서 고친 백엔드 코드는 백테스트/라이브신호/옵티마이저에 반영되지 않는다.

set -euo pipefail

SKIP_DEPS=0
SKIP_DB=0
ADOPT_ENV=0
SLOT=""

while [ $# -gt 0 ]; do
  case "$1" in
    # ★값이 필요한 옵션은 값의 존재를 먼저 확인한다. `--slot` 만 주고 값을 빼면 `shift 2` 가
    #   인자 부족으로 실패하고 `set -e` 가 **메시지 없이** 죽는다(실측: exit 1, 출력 0줄).
    #   호출자는 무엇이 잘못됐는지 알 수 없다.
    --slot)      [ $# -ge 2 ] || { echo "✗ --slot 에 값이 없다 (예: --slot 3)" >&2; exit 2; }
                 SLOT="$2"; shift 2 ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    --skip-db)   SKIP_DB=1; shift ;;
    --adopt-env) ADOPT_ENV=1; shift ;;
    -h|--help)   sed -n '2,30p' "$0"; exit 0 ;;
    *)           echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

die() { echo "✗ $*" >&2; exit 1; }
ok()  { echo "  ✓ $*"; }

# ── 1. 워크트리 안에서 실행되었는지 확인 ────────────────────────────────────
# 메인 체크아웃에서는 git-dir 과 git-common-dir 이 같다. 워크트리에서만 갈라진다.
GIT_DIR="$(git rev-parse --absolute-git-dir)"
GIT_COMMON="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
[ "$GIT_DIR" != "$GIT_COMMON" ] || die "여기는 메인 체크아웃이다. 워크트리 안에서 실행해라.
    워크트리 생성:  git worktree add .claude/worktrees/<이름> -b <브랜치>
    또는 Claude Code 세션에서 EnterWorktree."

WT_ROOT="$(git rev-parse --show-toplevel)"
MAIN_ROOT="$(dirname "$GIT_COMMON")"
cd "$WT_ROOT"

# ★도구 버전 핀 — §8 의 `pnpm install --frozen-lockfile` 과 `uv sync` 가 **PATH 가 아니라**
#   `mise.toml` 핀으로 돌아야 한다([BL-785]). pnpm 8 셸에서 부트스트랩하면 lockfileVersion 9.0
#   을 못 읽어 워크트리가 node_modules 없이 만들어지고, 그 원인이 슬롯 문제로 오인된다.
# shellcheck source=tools/scripts/lib/mise-shim-path.sh
. "$WT_ROOT/tools/scripts/lib/mise-shim-path.sh"
qb_pin_tool_path || true
echo "▶ 워크트리 부트스트랩"
echo "  worktree : $WT_ROOT"
echo "  main     : $MAIN_ROOT"
echo "  branch   : $(git branch --show-current)"

# ── 2. 슬롯 번호 결정 ───────────────────────────────────────────────────────
# 슬롯 0 = 메인 체크아웃(3100/8100/quantbridge_test/redis 3). 워크트리는 1부터.
# Redis DB 는 0..15 이고 0,1,2 를 앱/celery 가 쓰므로 슬롯 상한은 12.
# 포트가 살아 있으면 그 슬롯은 피한다. 다른 워크트리가 아니라 **다른 프로젝트**가 잡고 있을 수 있다
# (실측: 이 머신의 3101 을 무관한 next-server 가 점유 중이었다). 그대로 배정하면 `fe-isolated` 가
# 엉뚱한 포트로 밀리고, 더 나쁘게는 e2e 가 남의 앱을 검사해 거짓 그린이 난다(이 레포의 실제 사고 이력).
port_busy() {
  command -v lsof >/dev/null 2>&1 || return 1
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

write_slot_file() {
  cat > "$WT_ROOT/.worktree-slot" <<EOF
# tools/scripts/worktree-bootstrap.sh 생성 — mise.toml 의 task 가 sed 로 읽는다. 커밋 대상 아님.
# ★형식(QB_SLOT = N)은 Makefile 시절 그대로다 — 파싱하는 쪽만 바뀌었다([ADR-036]).
QB_SLOT = $1
EOF
}

# 슬롯 "탐색 → 예약" 은 원자적이어야 한다. 두 워크트리에서 동시에 부트스트랩하면
# 둘 다 아직 리스너도 `.worktree-slot` 도 없는 상태를 보고 같은 번호를 집을 수 있고,
# 그러면 테스트 DB 와 Redis lock DB 가 겹쳐 격리가 통째로 무너진다.
# `mkdir` 은 POSIX 상 원자적이므로 그걸 락으로 쓴다.
SLOT_LOCK="$MAIN_ROOT/.claude/worktrees/.slot-lock"
mkdir -p "$MAIN_ROOT/.claude/worktrees"
_lock_wait=0
while ! mkdir "$SLOT_LOCK" 2>/dev/null; do
  _lock_wait=$((_lock_wait + 1))
  [ "$_lock_wait" -gt 100 ] && die "슬롯 락 획득 실패(10초). 죽은 프로세스가 남긴 락이면: rmdir '$SLOT_LOCK'"
  sleep 0.1
done
trap 'rmdir "$SLOT_LOCK" 2>/dev/null || true' EXIT INT TERM

# 다른 워크트리들이 이미 쥔 슬롯. 자기 것은 뺀다(자기 슬롯은 아래에서 따로 다룬다).
#
# ⚠️ 디렉터리 글롭(`$MAIN_ROOT/.claude/worktrees/*/`)으로 세면 안 된다. 워크트리가 거기에만
#    생긴다는 보장이 없다 — herdr 는 `~/.herdr/worktrees/<repo>/<이름>` 에 만들고(실측),
#    수동 `git worktree add` 는 아무 경로나 받는다. 그것들이 USED 에서 빠지면 같은 번호를
#    두 번 배정하고, 그러면 `quantbridge_w{N}_test` 와 Redis lock DB 가 겹쳐
#    pytest 의 drop_all 과 마이그레이션이 서로를 파괴한다 — 위 락으로 막으려던 바로 그 파괴가
#    다른 경로로 되살아난다. 어떤 워크트리가 존재하는가의 권위 있는 출처는 git 뿐이다.
#
# ⚠️ 스캔은 **fail-closed** 여야 한다. `$(git worktree list ...)` 를 here-doc 안에서 바로
#    쓰면 그 종료 상태가 `while` 의 성공 상태에 먹혀 사라진다. git 이 어떤 이유로든 실패하면
#    (레포 손상 · PATH 오염 · 권한) `USED` 가 조용히 비고, 그러면 **이미 남이 쥔 슬롯을
#    비어 있다고 판단**해 같은 pytest DB 와 Redis lock DB 를 배정한다. 그게 이 락이 막으려던
#    바로 그 파괴다. 그러니 목록을 먼저 받아 상태를 확인하고, 실패면 여기서 죽는다.
_WT_LIST="$(git worktree list --porcelain 2>/dev/null)" \
  || die "git worktree list 실패 — 어떤 슬롯이 쓰이는지 알 수 없다.
    빈 목록을 '아무도 안 쓴다' 로 읽으면 남이 쥔 슬롯을 덮어써 pytest DB 가 서로를 파괴한다.
    레포 상태를 확인하고 다시 실행해라."
_WT_PATHS="$(printf '%s\n' "$_WT_LIST" | sed -n 's/^worktree //p')"
[ -n "$_WT_PATHS" ] || die "git worktree list 가 경로를 하나도 내지 않았다 (메인조차 없다).
    출력 형식이 바뀌었거나 레포가 비정상이다. 슬롯 배정을 진행하지 않는다."

USED=""
while IFS= read -r _wt; do
  [ -n "$_wt" ] || continue
  [ "$_wt" = "$MAIN_ROOT" ] && continue   # 메인은 슬롯 0 고정 (.worktree-slot 이 없으면 mise task 가 0 을 쓴다)
  [ "$_wt" = "$WT_ROOT" ] && continue     # 자기 슬롯은 아래에서 재사용 여부를 따로 판단한다
  [ -f "$_wt/.worktree-slot" ] || continue
  USED="$USED $(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$_wt/.worktree-slot")"
done <<EOF
$_WT_PATHS
EOF

# 재실행이 슬롯을 바꾸면 안 된다. 이미 떠 있는 서버는 옛 포트에 남아 있는데
# env·테스트 DB·슬롯 파일만 새 번호로 갈아타면, 이후 테스트와 E2E 가 서로 다른
# 인스턴스를 보게 된다. 그래서 자기 `.worktree-slot` 이 있으면 그게 기본값이다.
if [ -z "$SLOT" ] && [ -f "$WT_ROOT/.worktree-slot" ]; then
  SLOT="$(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$WT_ROOT/.worktree-slot")"
  [ -n "$SLOT" ] && echo "  · 기존 슬롯 $SLOT 재사용 (이미 부트스트랩된 워크트리)"
fi

if [ -z "$SLOT" ]; then
  for n in 1 2 3 4 5 6 7 8 9 10 11 12; do
    case " $USED " in *" $n "*) continue ;; esac
    if port_busy $((3100 + n)) || port_busy $((8100 + n)); then
      echo "  · 슬롯 $n 건너뜀 — 포트 $((3100 + n))/$((8100 + n)) 중 하나가 이미 사용 중"
      continue
    fi
    SLOT="$n"; break
  done
  [ -n "$SLOT" ] || die "슬롯 1..12 이 모두 사용 중이거나 포트가 점유돼 있다."
else
  case "$SLOT" in ''|*[!0-9]*) die "슬롯은 정수여야 한다: $SLOT" ;; esac
  # 명시 지정(--slot)이든 자기 슬롯 재사용이든, 다른 워크트리가 쥔 번호면 **거부**한다.
  # 포트가 비어 있다고 안전한 게 아니다 — 그 워크트리가 서버를 안 띄웠을 뿐,
  # 같은 `quantbridge_w{N}_test` 와 Redis lock DB 를 공유하게 되어
  # pytest 의 drop_all 과 마이그레이션이 서로를 파괴한다.
  case " $USED " in
    *" $SLOT "*) die "슬롯 $SLOT 은 다른 워크트리가 쓰고 있다 (그쪽 .worktree-slot 에 기록됨).
    다른 번호를 주거나, 그 워크트리를 정리해라: git worktree remove <경로>" ;;
  esac
  # 포트 점유는 남의 앱일 수도 자기 서버 재시작일 수도 있으니 경고만 낸다.
  for p in $((3100 + SLOT)) $((8100 + SLOT)); do
    port_busy "$p" && echo "  ! 경고: 포트 $p 가 이미 사용 중이다. 그 프로세스가 네 것이 아니면 e2e 가 남의 앱을 검사한다."
  done
fi

case "$SLOT" in ''|*[!0-9]*) die "슬롯은 정수여야 한다: $SLOT" ;; esac
[ "$SLOT" -ge 1 ] && [ "$SLOT" -le 12 ] || die "슬롯은 1..12 범위여야 한다 (0 은 메인 체크아웃 예약): $SLOT"

# 락을 놓기 **전에** 기록한다 — 다음 부트스트랩이 이 번호를 USED 로 보게 하는 것이 예약이다.
write_slot_file "$SLOT"
rmdir "$SLOT_LOCK" 2>/dev/null || true
trap - EXIT INT TERM
FE_PORT=$((3100 + SLOT))
BE_PORT=$((8100 + SLOT))
LOCK_DB=$((3 + SLOT))
# ⚠️ 이름은 반드시 `_test` 로 끝나야 한다. `tests/test_migrations.py:59` 의
# `_assert_disposable_database` 가 그 접미사가 아니면 RuntimeError 로 거부한다 —
# 그 테스트가 `downgrade base` 로 전 테이블을 드롭하기 때문에 개발 DB 를 겨냥하는 것을
# 막는 가드다. `quantbridge_test_w1` 같은 순서로 지으면 5 개 테스트가 통째로 깨진다(실측).
TEST_DB="quantbridge_w${SLOT}_test"
echo "  slot     : $SLOT  (FE $FE_PORT / BE $BE_PORT / $TEST_DB / redis lock $LOCK_DB)"

# ── 3. .worktreeinclude 가 실제로 동작했는지 검증 ───────────────────────────
# 이 셋이 없으면 워크트리는 부팅 자체가 불가능하다. 조용히 넘어가면 안 된다.
#
# `.worktreeinclude` 는 **Claude Code 의 `EnterWorktree` 기능이지 git 기능이 아니다.**
# `git worktree add` 나 herdr 로 만든 워크트리에는 적용되지 않으므로 아래 검증이 die 한다.
# 사람에겐 그게 맞다(무엇이 왜 없는지 봐야 한다). 하지만 비대화형 호출자 — fleet 스크립트나
# 에이전트 — 에겐 그냥 정지다. `--adopt-env` 는 그때 쓰라고 있다.
#
# ★목록의 SSOT 는 `.worktreeinclude` 하나뿐이다. 여기에 파일 이름을 다시 적으면 두 벌이 되어
#   언젠가 갈린다 (한쪽에만 추가된 파일이 조용히 안 따라가는 형태로).
adopt_env() {
  # 목록은 **이 워크트리** 것을 읽는다 — `.worktreeinclude` 는 트래킹되는 파일이고,
  # "무엇이 있어야 하는가" 를 정하는 건 지금 체크아웃된 브랜치이기 때문이다.
  # 메인 체크아웃은 다른(더 오래된) 브랜치에 있을 수 있다 — 실제로 이 스크립트를 처음 돌렸을 때
  # 메인이 아직 머지 전 커밋이라 파일이 없었다. 복사해 오는 **내용**만 메인 것이다.
  _list="$WT_ROOT/.worktreeinclude"
  [ -f "$_list" ] || _list="$MAIN_ROOT/.worktreeinclude"   # 브랜치가 이 파일보다 오래된 경우
  [ -f "$_list" ] || die "$WT_ROOT/.worktreeinclude 도 $MAIN_ROOT/.worktreeinclude 도 없다 — 복사할 목록이 없다."
  echo "▶ --adopt-env — $_list 기준으로 $MAIN_ROOT 에서 복사"
  while IFS= read -r _pat || [ -n "$_pat" ]; do
    case "$_pat" in ''|'#'*) continue ;; esac
    _rel="${_pat#/}"   # 선행 `/` 는 "레포 루트 고정" 이라는 gitignore 표기일 뿐이다
    # glob 은 지원하지 않는다. 조용히 건너뛰면 그 파일이 없는 채로 부팅되므로 시끄럽게 알린다.
    case "$_rel" in
      *'*'*|*'?'*|*'['*)
        echo "  ! glob 은 --adopt-env 가 다루지 않는다 (수동 복사 필요): $_rel" >&2; continue ;;
    esac
    [ -e "$WT_ROOT/$_rel" ] && continue
    if [ -f "$MAIN_ROOT/$_rel" ]; then
      mkdir -p "$(dirname "$WT_ROOT/$_rel")"
      cp -p "$MAIN_ROOT/$_rel" "$WT_ROOT/$_rel"
      ok "복사 $_rel"
    else
      # 메인에도 없으면 복사로는 못 고친다. 아래 검증이 필수 파일인지 판정한다.
      echo "  ! 메인에도 없다, 건너뜀: $_rel" >&2
    fi
  done < "$_list"
}
if [ "$ADOPT_ENV" -eq 1 ]; then adopt_env; fi

echo "▶ env 파일 (.worktreeinclude 복사분)"
MISSING=""
for f in apps/api/.env.local apps/web/.env.local .env; do
  if [ -f "$f" ]; then ok "$f"; else MISSING="$MISSING $f"; fi
done
if [ -n "$MISSING" ]; then
  echo "  ✗ 누락:$MISSING" >&2
  echo "    → .worktreeinclude 가 적용되지 않았다 (수동 git worktree add / herdr 로 만들었거나 구버전 CLI)." >&2
  echo "    자동 복구:  $0 --adopt-env" >&2
  echo "    수동 복구:" >&2
  for f in $MISSING; do echo "      cp '$MAIN_ROOT/$f' '$WT_ROOT/$f'" >&2; done
  die "env 없이는 진행 불가."
fi
[ -f .claude/settings.local.json ] || {
  mkdir -p .claude
  cp "$MAIN_ROOT/.claude/settings.local.json" .claude/settings.local.json 2>/dev/null \
    && ok ".claude/settings.local.json (수동 복사)" \
    || echo "  ! .claude/settings.local.json 없음 — 권한 프롬프트가 늘어난다 (치명적이지 않음)"
}
# 루트 lockfile 이 없으면 아래 §8 의 `pnpm install --frozen-lockfile` 이 실패하고,
# 훅이 무력화된 채 커밋이 통과하는 워크트리가 만들어진다(실측). 수동 워크트리 경로에서
# 특히 잘 빠지므로 여기서 메꾼다.
[ -f pnpm-lock.yaml ] || {
  cp "$MAIN_ROOT/pnpm-lock.yaml" pnpm-lock.yaml 2>/dev/null \
    && ok "pnpm-lock.yaml (수동 복사)" \
    || echo "  ! 루트 pnpm-lock.yaml 없음 — pre-commit 훅(lint-staged)이 조용히 죽는다"
}

# ── 4. 심볼릭 링크 복구 ─────────────────────────────────────────────────────
# .worktreeinclude 는 심볼릭을 스킵한다. 스택 규칙은 ADR-027 부터 `apps/api/AGENTS.md` 등
# 실파일이라 체크아웃에 포함된다 — 여기서 만들 것은 CLAUDE.md 링크뿐이다.
echo "▶ 심볼릭 링크"
[ -e .claude/CLAUDE.md ] || { ln -s ../AGENTS.md .claude/CLAUDE.md && ok ".claude/CLAUDE.md -> ../AGENTS.md"; }
[ -e .claude/CLAUDE.md ] && ok "이미 존재 (변경 없음)"

# ── 5. 백엔드 테스트 env 를 슬롯 값으로 재작성 ──────────────────────────────
# 앱 `DATABASE_URL` 은 건드리지 않는다 (공유).
#
# `sed -i` 는 못 쓴다 — BSD(macOS)는 빈 인자를 요구하고 GNU(Linux)는 그 빈 문자열을
# 파일명으로 읽어 죽는다. 양쪽에서 도는 awk 경유로 치환하고, 파일을 갈아끼우지 않고
# 내용만 덮어써 `.env.local` 의 퍼미션(시크릿 파일이다)을 보존한다.
set_env_var() {
  key="$1"; val="$2"; file="$3"
  tmp="$(mktemp)" || die "mktemp 실패"
  if grep -q "^${key}=" "$file"; then
    awk -v k="$key" -v v="$val" '
      index($0, k "=") == 1 && !done { print k "=" v; done = 1; next }
      { print }
    ' "$file" > "$tmp" || { rm -f "$tmp"; die "$key 치환 실패"; }
    cat "$tmp" > "$file"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
  rm -f "$tmp"
}

echo "▶ apps/api/.env.local 슬롯 반영"
TEST_DB_URL="postgresql+asyncpg://quantbridge:password@localhost:5433/${TEST_DB}"
TEST_LOCK_URL="redis://localhost:6380/${LOCK_DB}"

set_env_var TEST_DATABASE_URL "$TEST_DB_URL" apps/api/.env.local
ok "TEST_DATABASE_URL → $TEST_DB"

# ⚠️ `TEST_REDIS_LOCK_URL` 만 써서는 격리가 **작동하지 않는다.** `conftest.py:50` 은
#    `if not os.environ.get("REDIS_LOCK_URL")` 일 때만 TEST_ 값을 본다. `.env.local` 에는
#    `REDIS_LOCK_URL` 이 이미 있으므로, 의무인 `set -a; . ./.env.local` 소싱을 거치면
#    그 분기가 거짓이 되어 모든 워크트리가 lock DB 3 을 계속 공유한다.
#    그래서 둘 다 쓴다. 앱 서버 쪽은 `mise run be-isolated` 가 inline 으로 3 을 덮으므로
#    런타임 락은 공유 그대로다 — 앱 DB 를 공유하니 런타임 락도 공유하는 것이 맞다.
set_env_var TEST_REDIS_LOCK_URL "$TEST_LOCK_URL" apps/api/.env.local
set_env_var REDIS_LOCK_URL "$TEST_LOCK_URL" apps/api/.env.local
ok "REDIS_LOCK_URL + TEST_REDIS_LOCK_URL → db $LOCK_DB"

# ── 6. mise task 가 읽을 슬롯 파일 ──────────────────────────────────────────
# 실제 기록은 §2 의 락 안에서 이미 끝났다(예약이 곧 기록이다). 여기서는 확인만 한다.
[ -f .worktree-slot ] || die ".worktree-slot 이 없다 — 슬롯 예약이 실패했다."
ok ".worktree-slot (QB_SLOT=$SLOT)"

# ── 7. 테스트 DB 생성 + alembic 초기 스탬프 (멱등) ──────────────────────────
# 일반 테스트의 스키마는 conftest.py 가 metadata.create_all 로 만들지만, 그것만으로는 부족하다.
#
# ⚠️ 갓 만든 DB 에는 `alembic_version` 이 없다. 그 상태로 두면 `tests/test_migrations.py` 의
#    `downgrade base` 가 no-op 이 되고, conftest 가 create_all 로 만들어 둔 테이블 위에
#    `upgrade head` 가 CREATE TABLE 을 시도해 `DuplicateTable: relation "users" already exists`
#    로 5 개가 깨진다(실측). 그래서 생성 직후 alembic 을 한 번 찍어 버전 테이블을 심는다.
#    `alembic_version` 은 SQLModel metadata 밖이라 conftest 의 drop_all 이 지우지 않는다.
echo "▶ 테스트 DB"
if [ "$SKIP_DB" -eq 1 ]; then
  ok "--skip-db — 이 워크트리에서 pytest 는 돌지 않는다"
elif ! docker exec quantbridge-db pg_isready -U quantbridge -d quantbridge >/dev/null 2>&1; then
  # 여기서 경고만 하고 성공 종료하면 안 된다. 슬롯 테스트 DB 없이 "준비 완료" 를 찍으면
  # 호출자(사람이든 자동화든)는 부트스트랩이 끝난 줄 알지만 pytest 는 즉시 실패한다.
  die "quantbridge-db 컨테이너가 안 떠 있어 슬롯 테스트 DB 를 만들 수 없다.
    메인 체크아웃에서 'mise run up-isolated' 를 먼저 실행하고 이 스크립트를 다시 돌려라.
    (DB 가 필요 없는 문서·계획 전용 워크트리라면 --skip-db)"
else
  EXISTS="$(docker exec quantbridge-db psql -U quantbridge -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${TEST_DB}'" 2>/dev/null || true)"
  if [ "$EXISTS" = "1" ]; then
    ok "$TEST_DB (이미 존재)"
  else
    docker exec quantbridge-db psql -U quantbridge -d postgres -c "CREATE DATABASE ${TEST_DB}" >/dev/null
    ok "$TEST_DB 생성"
  fi
  STAMPED="$(docker exec quantbridge-db psql -U quantbridge -d "${TEST_DB}" -tAc \
    "SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'" 2>/dev/null || true)"
  if [ "$STAMPED" = "1" ]; then
    ok "alembic_version (이미 존재)"
  else
    (cd apps/api && DATABASE_URL="$TEST_DB_URL" uv run alembic upgrade head >/dev/null 2>&1) \
      && ok "alembic upgrade head → $TEST_DB" \
      || die "alembic upgrade 실패 — test_migrations 5 건이 DuplicateTable 로 깨진다."
  fi
fi

# ── 8. 의존성 ───────────────────────────────────────────────────────────────
# node_modules ~997M / .venv ~970M. pnpm 은 전역 store hardlink, uv 는 전역 cache 라
# 디스크 실사용은 표시 용량보다 훨씬 작지만, .next 빌드 캐시(~1.5G)는 워크트리마다 순증한다.
if [ "$SKIP_DEPS" -eq 1 ]; then
  echo "▶ 의존성 — --skip-deps (문서/계획 전용 워크트리)"
else
  echo "▶ 의존성 설치"
  # 루트 devDependencies (husky/lint-staged/prettier) — 빠뜨리면 pre-commit 훅이
  # `Command "lint-staged" not found` 로 죽고, 훅이 무력화된 채로 커밋이 통과한다(실측).
  pnpm install --frozen-lockfile >/dev/null 2>&1 && ok "루트 node_modules (husky/lint-staged)" \
    || echo "  ! 루트 pnpm install 실패 — pre-commit 훅이 무력화된다. pnpm-lock.yaml 복사 여부를 확인해라."
  (cd apps/web && pnpm install --frozen-lockfile) && ok "apps/web/node_modules"
  (cd apps/api && uv sync) && ok "apps/api/.venv"
fi

# ── 9. 요약 ─────────────────────────────────────────────────────────────────
cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
슬롯 $SLOT 준비 완료 — $WT_ROOT

  BE 테스트   cd apps/api && set -a; . ./.env.local; set +a; uv run pytest
              (env 소싱 필수 — AGENTS.md §BE pytest. 안 하면 5432 로 붙는다)
  BE 서버     mise run be-isolated      → http://localhost:$BE_PORT
              (슬롯 ≠ 0 이면 migrate-isolated 선행이 자동으로 빠진다 — QB_MIGRATE_DONE 불필요)
  FE 서버     mise run fe-isolated      → http://localhost:$FE_PORT
              (★BE 와 짝으로 띄워라 — authed e2e 는 두 task 가 BETTER_AUTH_URL 을 같은 값으로
               덮어야 돈다. 어긋나면 403 INVALID_ORIGIN 또는 전건 401 이다, [BL-781])
  E2E         cd apps/web && pnpm e2e            # authed 는 pnpm e2e:authed
              (base URL 은 e2e/_base-url.ts 가 .worktree-slot 을 읽어 $FE_PORT 로 스스로 정한다.
               PLAYWRIGHT_BASE_URL 은 슬롯 파일 밖의 대상을 겨눌 때만 준다)

이 워크트리에서 막혀 있는 것 (assert-main-checkout.sh 가드가 거부한다 — 종료 코드 1):
  ✗ mise run up / down / up-isolated / down-isolated  → container_name 고정. 스택은 메인에서만.
  ✗ mise run migrate / migrate-isolated / seed        → 앱 DB 는 공유다. 다른 워크트리가 깨진다.

막을 수 없는 것 — 스스로 지켜야 한다:
  ✗ celery 경유 검증(백테스트·라이브신호·옵티마이저)
       worker 컨테이너가 메인의 src 를 mount 하므로 **네 코드가 아니라 메인 코드가 돈다.**
       테스트는 통과하는데 실행된 게 내 코드가 아닌 침묵 실패다. 메인 체크아웃에서 해라.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
