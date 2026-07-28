# 워크트리 병렬 작업 — 무엇이 되고 무엇이 안 되는가

> 정본. 2026-07-28 실측 기준. 코드와 어긋나면 코드가 맞다.
> 도구: `.worktreeinclude` · `scripts/worktree-bootstrap.sh` · `Makefile` 의 `QB_SLOT`.

---

## 1. 결론 — 3 티어

| 작업                                                      | 병렬 가능 수            | 필요한 격리                                        |
| --------------------------------------------------------- | ----------------------- | -------------------------------------------------- |
| 코드 작성 · 문서 · 계획                                   | 무제한                  | 없음                                               |
| `ruff` / `eslint` / `mypy` / `tsc`                        | 무제한                  | 없음                                               |
| FE `vitest`                                               | 무제한                  | 없음 (DB 미사용)                                   |
| BE `pytest`                                               | 무제한                  | 테스트 DB 이름 + Redis lock DB (부트스트랩이 자동) |
| 앱 구동 (`be-isolated` / `fe-isolated`) · 브라우저 확인   | 12                      | 포트 (슬롯이 자동)                                 |
| Playwright E2E                                            | 12                      | 포트 + `PLAYWRIGHT_BASE_URL` **명시 필수**         |
| **celery 경유 검증** (백테스트 · 라이브신호 · 옵티마이저) | **1 (메인 체크아웃만)** | 해결 불가 — §3                                     |

핵심: **격리가 필요한 건 검증 단계뿐이다.** 코드를 쓰고 정적 검사를 돌리는 데까지는 워크트리만 있으면 된다.

---

## 2. 스택은 1벌을 공유한다

컨테이너는 **메인 체크아웃에서만** 띄운다. 워크트리에서 `make up-isolated` 를 하면 안 된다.

이유는 `docker-compose.yml` 이 `container_name: quantbridge-db` 처럼 이름을 **고정**하기 때문이다.
`COMPOSE_PROJECT_NAME` 을 바꿔도 `container_name` 은 전역 고정값이라 두 번째 스택은 이름 충돌로 뜨지 않는다.
(`docker-compose.isolated.yml` 머리말도 `base 와 isolated 는 mutually exclusive` 라고 명시한다.)

```
공유 (1벌, 메인에서 기동)          슬롯별 격리
─────────────────────────────    ──────────────────────────
Postgres  host 5433               FE 포트 3100 + N
Redis     host 6380               BE 포트 8100 + N
앱 DB     quantbridge             pytest DB  quantbridge_w{N}_test
celery    broker/result 0,1,2     Redis lock DB  3 + N
```

앱 DB 를 공유하는 이유는 마이그레이션·시드·OHLCV 재수집 비용이 크기 때문이다.
따라서 워크트리에서 **`alembic upgrade` 와 `make seed` 를 돌리면 안 된다.**

> 슬롯 포트는 **이 프로젝트 밖의 앱과도 부딪힐 수 있다.** 실측에서 3101 을 무관한 `next-server` 가
> 점유하고 있었다. 부트스트랩은 자동 할당 시 `3100+N`/`8100+N` 이 살아 있으면 그 슬롯을 건너뛰고,
> `--slot` 으로 명시 지정한 경우에는 경고만 낸다. 이걸 무시하면 e2e 가 남의 앱을 검사해 거짓 그린이 난다.

### 2.1 Redis lock 은 테스트만 갈라진다

`conftest.py:50` 은 `if not os.environ.get("REDIS_LOCK_URL")` 일 때만 `TEST_REDIS_LOCK_URL` 을 본다.
`.env.local` 에는 `REDIS_LOCK_URL` 이 이미 있으므로, 의무인 `set -a; . ./.env.local` 소싱을 거치면
그 분기가 거짓이 되어 **`TEST_REDIS_LOCK_URL` 은 무시된다.** 그래서 부트스트랩은 `.env.local` 의
**두 키를 모두** `6380/{3+N}` 으로 쓴다.

앱 서버 쪽은 `make be-isolated` 가 `REDIS_LOCK_URL=redis://localhost:6380/3` 을 inline 으로 덮으므로
**런타임 락은 슬롯과 무관하게 공유**된다. 앱 DB 를 공유하는 이상 런타임 락도 공유하는 것이 맞다.
갈라지는 건 pytest 안의 락뿐이다.

---

## 3. 해결 불가 — celery worker 는 메인의 코드를 본다

`docker-compose.isolated.yml` 이 worker 4 종에 `./backend/src:/app/src:ro` 를 bind-mount 한다.
경로가 **컨테이너를 띄운 디렉터리 기준**이므로, 컨테이너를 메인에서 띄운 이상 worker 는 항상 메인의 `src` 를 실행한다.

→ **워크트리에서 백엔드 코드를 고쳐도 백테스트·라이브신호·옵티마이저에는 반영되지 않는다.**
→ 게다가 §2 때문에 워크트리에서 자기 스택을 새로 띄울 수도 없다.

이건 침묵 실패다. 테스트는 통과하는데 실행된 코드가 내 코드가 아니다.
**celery 를 타는 검증은 메인 체크아웃으로 돌아가서 한다.** 워크트리는 그 코드를 *작성*하는 데까지만 쓴다.

---

## 4. pytest DB 분리 — 이름은 반드시 `_test` 로 끝나야 한다

### 4.1 명명 규칙 (어기면 5 개 테스트가 깨진다)

```
quantbridge_w{N}_test      ✅
quantbridge_test_w{N}      ❌ RuntimeError · 실측으로 5 failed
```

`tests/test_migrations.py:59` 의 `_assert_disposable_database` 가 DB 이름이 `_test` 로 끝나지 않으면
`RuntimeError` 로 거부한다. 그 테스트가 **`downgrade base` 로 전 테이블을 드롭**하기 때문에,
개발 DB 를 겨냥한 실행을 막는 가드다. 순서를 뒤집어 짓지 마라.

### 4.2 새 슬롯 DB 에는 alembic 스탬프가 필요하다

`CREATE DATABASE` 만 하고 두면 `alembic_version` 이 없다. 그러면 `test_migrations` 의 `downgrade base`
가 no-op 이 되고, `conftest` 가 `create_all` 로 만들어 둔 테이블 위로 `upgrade head` 가 겹쳐
`DuplicateTable: relation "users" already exists` 로 **5 건이 깨진다**(실측).

부트스트랩이 DB 생성 직후 `alembic upgrade head` 를 한 번 찍어 이를 막는다.
대상은 **슬롯 테스트 DB** 이므로 공유 앱 DB 와 무관하다.
`alembic_version` 은 SQLModel metadata 밖이라 이후 `drop_all` 이 지우지 않는다.

### 4.3 공유하면 위험한가 — 실측과 그 해석

2026-07-28 실측 (3 회, 전부 같은 `quantbridge_test` 공유):

| 실험                                              | 결과                                    |
| ------------------------------------------------- | --------------------------------------- |
| 짧은 세트 2 개 동시 시작                          | 양쪽 6 passed                           |
| 워크트리 `tests/trading`(17s) + 메인 20s 뒤 진입  | 756 passed / 4 passed                   |
| 워크트리 `tests` 전체(4분 6초) + 메인 60s 뒤 진입 | 3341 passed / 4 passed                  |
| 메인 wall clock (3s 뒤 진입, 공유 DB)             | 5.81s — 단독 baseline 5.25s 대비 +0.56s |

3 회 모두 통과했지만 **"안전하다"로 읽으면 안 된다.** 통과한 이유는 타이밍이 비껴간 것뿐이고,
`test_migrations.py` 가 `downgrade base` 로 **전 테이블을 실제로 드롭**하는 경로가 존재한다.
그 창에 다른 워크트리의 세션이 걸리면 그쪽은 원인을 알 수 없는 빨간불을 받는다.
(이 사실은 슬롯 DB 명명 실수로 게이트가 5 failed 를 뱉었을 때 드러났다 — 실험만으로는 못 봤다.)

분리를 유지하는 근거:

1. **실제 파괴 경로가 있다** — 위의 `downgrade base`. 확률이 낮을 뿐 구조적으로 존재한다.
2. **분리 비용이 0** — `CREATE DATABASE` 한 줄, 부트스트랩이 자동. 컨테이너 추가 없음. 스키마는 `create_all` 이 만들어 alembic 도 불필요.
3. **실패 원인 판별** — 공유 상태에서 빨간불이 뜨면 내 코드 탓인지 남의 드롭 탓인지 구분할 수 없다.

---

## 5. 사용법

### 새 워크트리

```bash
# Claude Code 세션에서 (.worktreeinclude 가 자동 적용된다)
#   EnterWorktree

# 또는 수동
git worktree add .claude/worktrees/<이름> -b <브랜치>

# 어느 쪽이든 부트스트랩은 필수
cd .claude/worktrees/<이름>
./scripts/worktree-bootstrap.sh              # 슬롯 자동 할당 + deps
./scripts/worktree-bootstrap.sh --skip-deps  # 문서/계획 전용
```

브랜치가 이 스크립트를 포함하기 전 시점(구 베이스)에서 만든 워크트리라면
`../../../scripts/worktree-bootstrap.sh` 처럼 메인 체크아웃의 것을 직접 호출해도 된다 — cwd 기준으로 동작한다.

수동 `git worktree add` 는 `.worktreeinclude` 를 적용하지 **않는다** (그건 Claude Code 기능이지 git 기능이 아니다).
그 경우 부트스트랩이 fail-closed 로 멈추고 수동 복사 명령을 출력한다.

### 워크트리 안에서

```bash
# BE 테스트 — env 소싱 필수 (AGENTS.md §BE pytest)
cd backend && set -a; . ./.env.local; set +a; uv run pytest

# 서버 — 포트는 .worktree-slot 이 결정한다
make be-isolated QB_MIGRATE_DONE=1   # 8100 + N
make fe-isolated                     # 3100 + N

# E2E — 이 변수 없으면 3000 의 남의 앱을 검사한다 (실제 거짓 그린 사고 이력)
PLAYWRIGHT_BASE_URL=http://localhost:310N pnpm e2e
```

> ⚠️ **`QB_MIGRATE_DONE=1` 은 워크트리에서 의무다.** `be-isolated` 는 `migrate-isolated` 를 선행하는데,
> 그 대상이 **공유 앱 DB** 다. 워크트리 브랜치에 새 마이그레이션이 있으면 다른 워크트리와 메인이 그걸 뒤집어쓴다.
> 마이그레이션을 실제로 적용해야 하는 작업이라면 워크트리가 아니라 메인 체크아웃에서 해라.

### 정리

```bash
git worktree remove .claude/worktrees/<이름>
docker exec quantbridge-db psql -U quantbridge -d postgres -c 'DROP DATABASE quantbridge_w<N>_test'
```

---

## 6. 워크트리로 따라가지 않는 것

`.claude/*` 가 통째로 gitignore 이고 env 도 전부 무시 대상이라, 아래는 `.worktreeinclude` 가 복사한다.

| 파일                          | 없으면                                                                                                |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| `backend/.env.local`          | uvicorn·pytest 가 5432 로 붙어 격리 스택을 못 찾는다                                                  |
| `frontend/.env.local`         | Clerk 키 부재로 dev 서버가 부팅 중 죽고 `e2e:authed` 전멸                                             |
| `.env`                        | `make up-isolated` 가 POSTGRES\_\* 를 못 읽는다                                                       |
| `.claude/settings.local.json` | 워크트리 세션에서 권한 프롬프트가 폭증한다                                                            |
| `/pnpm-lock.yaml`             | 루트 `pnpm install` 이 lockfile 없이 돌아, **pre-commit 훅이 `lint-staged` 를 못 찾고 조용히 죽는다** |

**심볼릭 링크는 `.worktreeinclude` 로 복사되지 않는다** (Claude Code 가 건너뛴다).
`.claude/rules -> ../.ai/rules` 와 `.claude/CLAUDE.md -> ../AGENTS.md` 는 부트스트랩이 재생성한다.

루트 `CLAUDE.md` 는 git 이 심볼릭(mode 120000)으로 트래킹하므로 워크트리가 알아서 만든다.
`.claude/skills/` 는 0B (전역 `~/.claude/skills` 사용) 라 복사 대상이 아니다.

---

## 7. 디스크 비용 (실측)

| 항목                    | 크기 | 비고                                               |
| ----------------------- | ---- | -------------------------------------------------- |
| `.git`                  | 77M  | 워크트리끼리 **공유**                              |
| `backend/.venv`         | 809M | `uv sync` **1.04초** — 전역 캐시 하드링크          |
| `frontend/node_modules` | 997M | pnpm 전역 store 하드링크                           |
| `frontend/.next`        | 1.5G | 워크트리마다 **순증** — dev 서버를 띄운 워크트리만 |

표시 용량 대부분은 하드링크라 실디스크 증가는 그보다 작다. 순증하는 건 `.next` 빌드 캐시다.
Docker VM 디스크 포화가 Postgres 를 크래시 루프에 빠뜨린 이력이 있으므로,
워크트리를 늘리기 전에 여유를 확인하고 쓰지 않는 워크트리는 `git worktree remove` 로 지운다.
