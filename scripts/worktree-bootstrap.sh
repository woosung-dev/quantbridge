#!/usr/bin/env bash
#
# 워크트리 병렬 작업 부트스트랩 — 새 워크트리를 "실행 가능한" 상태로 만든다.
#
# 사용법:
#   scripts/worktree-bootstrap.sh              # 슬롯 자동 할당 + deps 설치
#   scripts/worktree-bootstrap.sh --slot 2     # 슬롯 지정
#   scripts/worktree-bootstrap.sh --skip-deps  # deps 설치 생략 (문서/계획 전용 워크트리)
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
# ⚠️ 이 스크립트로도 해결되지 않는 구조적 제약 — docs/reference/worktree-parallel.md §3 참조.
#    celery worker 컨테이너가 메인 체크아웃의 `./backend/src` 를 bind-mount 하므로,
#    워크트리에서 고친 백엔드 코드는 백테스트/라이브신호/옵티마이저에 반영되지 않는다.

set -euo pipefail

SKIP_DEPS=0
SLOT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --slot)      SLOT="${2:-}"; shift 2 ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
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

if [ -z "$SLOT" ]; then
  USED=""
  for f in "$MAIN_ROOT"/.claude/worktrees/*/.worktree-slot; do
    [ -f "$f" ] || continue
    [ "$f" = "$WT_ROOT/.worktree-slot" ] && continue
    USED="$USED $(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$f")"
  done
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
  # 명시 지정은 존중하되(자기 서버를 재시작하는 경우가 있다) 조용히 넘어가지는 않는다.
  for p in $((3100 + SLOT)) $((8100 + SLOT)); do
    port_busy "$p" && echo "  ! 경고: 포트 $p 가 이미 사용 중이다. 그 프로세스가 네 것이 아니면 e2e 가 남의 앱을 검사한다."
  done
fi
case "$SLOT" in ''|*[!0-9]*) die "슬롯은 정수여야 한다: $SLOT" ;; esac
[ "$SLOT" -ge 1 ] && [ "$SLOT" -le 12 ] || die "슬롯은 1..12 범위여야 한다 (0 은 메인 체크아웃 예약): $SLOT"

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
echo "▶ env 파일 (.worktreeinclude 복사분)"
MISSING=""
for f in backend/.env.local frontend/.env.local .env; do
  if [ -f "$f" ]; then ok "$f"; else MISSING="$MISSING $f"; fi
done
if [ -n "$MISSING" ]; then
  echo "  ✗ 누락:$MISSING" >&2
  echo "    → .worktreeinclude 가 적용되지 않았다 (수동 git worktree add 로 만들었거나 구버전 CLI)." >&2
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

# ── 4. 심볼릭 링크 복구 ─────────────────────────────────────────────────────
# .worktreeinclude 는 심볼릭을 스킵한다. 대상(.ai/rules)은 트래킹되므로 링크만 다시 건다.
echo "▶ 심볼릭 링크"
[ -e .claude/rules ] || { ln -s ../.ai/rules .claude/rules && ok ".claude/rules -> ../.ai/rules"; }
[ -e .claude/CLAUDE.md ] || { ln -s ../AGENTS.md .claude/CLAUDE.md && ok ".claude/CLAUDE.md -> ../AGENTS.md"; }
[ -e .claude/rules ] && [ -e .claude/CLAUDE.md ] && ok "이미 존재 (변경 없음)"

# ── 5. 백엔드 테스트 env 를 슬롯 값으로 재작성 ──────────────────────────────
# 앱 DATABASE_URL 은 건드리지 않는다 (공유). TEST_ 두 개만 슬롯화한다.
echo "▶ backend/.env.local 슬롯 반영"
TEST_DB_URL="postgresql+asyncpg://quantbridge:password@localhost:5433/${TEST_DB}"
TEST_LOCK_URL="redis://localhost:6380/${LOCK_DB}"
if grep -q '^TEST_DATABASE_URL=' backend/.env.local; then
  sed -i '' -E "s|^TEST_DATABASE_URL=.*|TEST_DATABASE_URL=${TEST_DB_URL}|" backend/.env.local
else
  printf '\nTEST_DATABASE_URL=%s\n' "$TEST_DB_URL" >> backend/.env.local
fi
ok "TEST_DATABASE_URL → $TEST_DB"
if grep -q '^TEST_REDIS_LOCK_URL=' backend/.env.local; then
  sed -i '' -E "s|^TEST_REDIS_LOCK_URL=.*|TEST_REDIS_LOCK_URL=${TEST_LOCK_URL}|" backend/.env.local
else
  printf 'TEST_REDIS_LOCK_URL=%s\n' "$TEST_LOCK_URL" >> backend/.env.local
fi
ok "TEST_REDIS_LOCK_URL → db $LOCK_DB"

# ── 6. Makefile 이 읽을 슬롯 파일 ───────────────────────────────────────────
cat > .worktree-slot <<EOF
# scripts/worktree-bootstrap.sh 생성 — Makefile 이 -include 로 읽는다. 커밋 대상 아님.
QB_SLOT = $SLOT
EOF
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
if ! docker exec quantbridge-db pg_isready -U quantbridge -d quantbridge >/dev/null 2>&1; then
  echo "  ! quantbridge-db 컨테이너가 안 떠 있다 — 메인 체크아웃에서 'make up-isolated' 후 재실행."
  echo "    (다른 단계는 완료됐다. DB 생성만 남았다.)"
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
    (cd backend && DATABASE_URL="$TEST_DB_URL" uv run alembic upgrade head >/dev/null 2>&1) \
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
  (cd frontend && pnpm install --frozen-lockfile) && ok "frontend/node_modules"
  (cd backend && uv sync) && ok "backend/.venv"
fi

# ── 9. 요약 ─────────────────────────────────────────────────────────────────
cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
슬롯 $SLOT 준비 완료 — $WT_ROOT

  BE 테스트   cd backend && set -a; . ./.env.local; set +a; uv run pytest
              (env 소싱 필수 — AGENTS.md §BE pytest. 안 하면 5432 로 붙는다)
  BE 서버     make be-isolated QB_MIGRATE_DONE=1   → http://localhost:$BE_PORT
              (이 변수가 없으면 migrate-isolated 가 선행돼 공유 앱 DB 에 alembic 이 걸린다)
  FE 서버     make fe-isolated      → http://localhost:$FE_PORT
  E2E         PLAYWRIGHT_BASE_URL=http://localhost:$FE_PORT pnpm e2e
              (이 변수 없으면 3000 의 남의 앱을 검사한다 — 실제 사고 이력 있음)

이 워크트리에서 하면 안 되는 것:
  ✗ make up / up-isolated       → container_name 충돌. 컨테이너는 메인 체크아웃에서만.
  ✗ alembic upgrade / make seed → 앱 DB 는 공유다. 다른 워크트리가 깨진다.
  ✗ celery 경유 검증(백테스트·라이브신호·옵티마이저)
                                → worker 가 메인의 src 를 mount 한다. 네 코드가 안 돈다.
                                   그 검증은 메인 체크아웃으로 돌아가서 해라.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
