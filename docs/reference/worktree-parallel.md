# 워크트리 병렬 작업 — 무엇이 되고 무엇이 안 되는가

> 정본. 2026-07-29 실측 기준. 코드와 어긋나면 코드가 맞다.
> 도구: `.worktreeinclude` · `scripts/worktree-bootstrap.sh` · `scripts/herdr-fleet.sh` ·
> `scripts/fleet-dispatch.sh` · `Makefile` 의 `QB_SLOT` / `qb-guard`. 함대 운용은 [`../guides/fleet-orchestration.md`](../guides/fleet-orchestration.md).

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
| `make up` / `seed` / `migrate` 계열                       | **1 (메인 체크아웃만)** | Makefile 가드가 거부 — §2.1                        |

핵심: **격리가 필요한 건 검증 단계뿐이다.** 코드를 쓰고 정적 검사를 돌리는 데까지는 워크트리만 있으면 된다.

실무 상한은 12 이 아니라 **2~4벌**이다 — 한 화면에 그 이상 띄우면 읽히지 않고, `.next` 캐시가
워크트리마다 순증한다(§7). `scripts/herdr-fleet.sh` 는 2×2 라 **워커 1~4** 를 받는다.
워커가 3 이하면 남는 칸이 CONTROL(메인, 슬롯 0)이고, **4 를 주면 CONTROL 칸이 없어져** celery
검증·게이트·머지를 할 자리가 화면에서 사라진다(그때는 경고를 낸다).

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

### 2.1 그건 이제 부탁이 아니라 가드다

위 문장들은 2026-07-28 시점엔 **문서에만** 있었다. 사람은 읽지만 에이전트는 읽지 않고 실행한다.
그래서 `Makefile` 의 `_guard-main-only` 가 **워크트리에서** 아래 타깃을 거부한다.
**종료 코드는 2 다** — 가드 셸 조각은 `exit 1` 이지만 `make` 가 레시피 실패를 2 로 감싼다.
수용 기준에 "exit 1" 이라고 쓰면 실측과 어긋난다(실제로 한 번 어긋났다).

★**가드는 선행 타깃과 레시피 첫 줄 양쪽에 있다.** 한쪽만으로는 각각 구멍이 있다 —
선행만 두면 `make -o _guard-main-only seed` 로 **건너뛸 수 있고**(실측: exit 0 통과, dry-run 이
`seed_dogfood.py --confirm` 이 **공유 앱 DB** 에 돌 것임을 보여줬다), 레시피에만 두면
`up-isolated: metrics-wipe` 처럼 **선행의 부작용이 먼저** 실행된다. 둘이 서로의 구멍을 막는다.

★**판정 기준은 `QB_SLOT` 이 아니라 git 이다.** make 는 명령행 변수를 `-include` 로 읽은 파일보다
우선하므로, 슬롯 변수로 판정하면 **`make QB_SLOT=0 up` 한 줄로 가드가 꺼진다** — 실측으로 슬롯 1
워크트리에서 `make QB_SLOT=0 _guard-main-only` 가 exit 0 을 냈다(codex 리뷰 P1). 지금은
`git rev-parse --absolute-git-dir` 와 `--git-common-dir` 가 갈리는지를 본다. 워크트리에서만 갈리고,
어떤 make 변수로도 못 바꾼다. **인자로 끌 수 있는 가드는 가드가 아니다.**

**선행 타깃이 필요한 이유** — 레시피에만 두면 선행이 이미 돌아간 뒤에 발동한다. 실측에서
`up-isolated` 의 선행 `metrics-wipe` 가 **가드보다 먼저** 돌았고, 그게 워크트리에서
`docker compose ps` 로 writer 를 세는데 **디렉터리 이름에서 유도된 다른 compose 프로젝트**를 보는
바람에 0개로 세어(실측: 워크트리 0 / 메인 4 / 실제 구동 4) fail-closed 분기를 건너뛰고 삭제 분기로 갔다.
`migrate-isolated` 은 선행 `wait-db-isolated` 가 DB 를 30초 폴링한 뒤에야 가드가 떠서, 스택이 내려가
있으면 "DB 가 죽었다" 로 오진하게 만들었다.

| 거부되는 타깃                                                                               | 안 막으면                                                                 |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `up` · `down` · `up-isolated` · `down-isolated` · `up-isolated-build` · `up-isolated-watch` | `container_name` 이 고정이라 남의 스택을 띄우거나 **죽인다**              |
| `migrate` · `migrate-isolated`                                                              | 워크트리 브랜치의 마이그레이션을 **공유 앱 DB** 에 걸어 전원이 뒤집어쓴다 |
| `seed`                                                                                      | 공유 앱 DB 를 갈아엎는다                                                  |

실측 우회 시도 **12가지 전부 차단** — `QB_SLOT=0` · `-e` · 환경변수 · `MAKEFLAGS=-e` ·
`--always-make` · `-o _guard-main-only` · `-B -o` 조합. 슬롯 0(메인)에서는 `make -n` 출력이
머지된 Makefile 과 **차이 0**.

메시지에 슬롯 번호와 메인 경로가 함께 나온다(`QB_MAIN_ROOT` 는 부트스트랩이 `.worktree-slot` 에 쓴다).

★**`be-isolated` 는 이제 워크트리에서 `migrate-isolated` 를 선행하지 않는다.** 예전엔 사람이
`QB_MIGRATE_DONE=1` 을 매번 붙여서 피해야 했는데, 한 번 빠뜨리면 남이 깨지는 구조였다.
슬롯이 이미 그 정보를 갖고 있으므로 사람에게 의무를 지우지 않는다.
(실측 대조 — 이 변경 전 Makefile 은 슬롯 1 워크트리에서도 `alembic upgrade` 를 걸었다.)

> 슬롯 포트는 **이 프로젝트 밖의 앱과도 부딪힐 수 있다.** 실측에서 3101 을 무관한 `next-server` 가
> 점유하고 있었다. 부트스트랩은 자동 할당 시 `3100+N`/`8100+N` 이 살아 있으면 그 슬롯을 건너뛰고,
> `--slot` 으로 명시 지정한 경우에는 경고만 낸다. 이걸 무시하면 e2e 가 남의 앱을 검사해 거짓 그린이 난다.

### 2.2 Redis lock 은 테스트만 갈라진다

`conftest.py:50` 은 `if not os.environ.get("REDIS_LOCK_URL")` 일 때만 `TEST_REDIS_LOCK_URL` 을 본다.
`.env.local` 에는 `REDIS_LOCK_URL` 이 이미 있으므로, 의무인 `set -a; . ./.env.local` 소싱을 거치면
그 분기가 거짓이 되어 **`TEST_REDIS_LOCK_URL` 은 무시된다.** 그래서 부트스트랩은 `.env.local` 의
**두 키를 모두** `6380/{3+N}` 으로 쓴다.

앱 서버 쪽은 `make be-isolated` 가 `REDIS_LOCK_URL=redis://localhost:6380/3` 을 inline 으로 덮으므로
**런타임 락은 슬롯과 무관하게 공유**된다. 앱 DB 를 공유하는 이상 런타임 락도 공유하는 것이 맞다.
갈라지는 건 pytest 안의 락뿐이다.

### 2.3 herdr — 한 화면 2×2 로 띄우기

`scripts/herdr-fleet.sh` 가 워크트리 생성 → 부트스트랩 → pane 배치 → 에이전트 기동까지 한다.

```bash
# 메인 체크아웃에서
scripts/herdr-fleet.sh --agent claude:bl537 --agent claude:bl536 --agent codex:impl
scripts/herdr-fleet.sh --teardown <workspace_id>
```

```
┌───────────────┬───────────────┐
│ 에이전트 1    │ 에이전트 2    │   각 칸 = 워크트리 = 슬롯 1벌
├───────────────┼───────────────┤
│ 에이전트 3    │ CONTROL       │   CONTROL = 메인(슬롯 0).
│               │ (메인, 슬롯 0)│   celery 검증·게이트·머지 전용
└───────────────┴───────────────┘
```

**프롬프트는 주입하지 않는다.** 부팅까지가 스크립트의 일이고 첫 지시는 사람이 한다.
herdr 는 `agent prompt <t> "<지시>" --wait --until done --timeout <ms>` 로 주입+대기를 한 커맨드에
제공하지만, 이 레포는 "자동화된 거짓 그린" 을 반복해서 밟았다. 사람이 루프 안에 있는 채로 굳힌다.

알아둘 것 세 가지 — 전부 실측으로 밟았다.

1. ★**`herdr worktree create` 는 인자가 없으면 usage 가 아니라 그냥 실행된다.** 전 필드가 optional 이라
   그렇다. 게다가 `--cwd` 가 없으면 **그때 포커스된 workspace 의 레포**에 만든다 — 조사 중 이걸로
   엉뚱한 레포에 워크트리가 생겼다. herdr CLI 의 플래그를 알아보려면 argless 대신 `--bogus` 같은
   무효 플래그를 줘라(그건 usage 를 낸다). 확실한 방법은 `herdr completion zsh` 나 `herdr api schema`.
2. **함대는 `herdr worktree create` 를 쓰지 않는다.** 그건 워크트리마다 **자기 workspace 와 tab 을 새로
   만들어서**(실측) 한 화면 2×2 라는 목표와 정면으로 싸운다. 생성은 `git worktree add`, 배치는
   `herdr pane split --cwd` 로 나눈다. workspace 는 하나다.
3. **`herdr pane split` 의 방향은 `right` / `down` 뿐이다.** 2×2 는 오른쪽 한 번 + 각 열 아래 한 번.

`.worktreeinclude` 는 **Claude Code 의 `EnterWorktree` 기능이지 git 기능이 아니다.** herdr 나 수동
`git worktree add` 로 만든 워크트리에는 적용되지 않으므로 부트스트랩을 `--adopt-env` 로 부른다
(§6). 함대 스크립트는 항상 그렇게 부른다.

---

## 3. 해결 불가 — celery worker 는 메인의 코드를 본다

`docker-compose.isolated.yml` 이 worker 4 종에 `./backend/src:/app/src:ro` 를 bind-mount 한다.
경로가 **컨테이너를 띄운 디렉터리 기준**이므로, 컨테이너를 메인에서 띄운 이상 worker 는 항상 메인의 `src` 를 실행한다.

→ **워크트리에서 백엔드 코드를 고쳐도 백테스트·라이브신호·옵티마이저에는 반영되지 않는다.**
→ 게다가 §2 때문에 워크트리에서 자기 스택을 새로 띄울 수도 없다.

이건 침묵 실패다. 테스트는 통과하는데 실행된 코드가 내 코드가 아니다.
**celery 를 타는 검증은 메인 체크아웃으로 돌아가서 한다.** 워크트리는 그 코드를 *작성*하는 데까지만 쓴다.

> ★**이 선은 2026-07-29 사용자 결정으로 확정됐다 — 우회하지 마라.** bind-mount 소스를 env 로
> 변수화하거나(`${QB_SRC_ROOT}`) 호스트에서 워크트리 전용 celery worker 를 띄우는 안이 검토됐고,
> **오버엔지니어링으로 기각**됐다. 스택 복제(`container_name` 제거 + `COMPOSE_PROJECT_NAME`) 도
> 마찬가지다 — 2~3벌 규모엔 과하고, 무엇보다 **Bybit demo 계정이 1개**라 라이브 dogfood 는
> 스택을 복제해도 여전히 배타적이다(reconciler 가 계정 전체 순포지션을 본다 — BL-496 사고 이력).
> 함대의 CONTROL pane 이 그 자리를 대신한다(§2.3).

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

### 4.4 누가 어느 슬롯을 쥐고 있는가 — 출처는 `git` 이다

부트스트랩은 `git worktree list --porcelain` 으로 **모든** 워크트리 경로를 얻은 뒤 각 경로의
`.worktree-slot` 을 읽는다. 디렉터리 글롭으로 세지 않는다.

★**초판(2026-07-28)은 `$MAIN_ROOT/.claude/worktrees/*/.worktree-slot` 글롭이었고 그게 버그였다.**
워크트리가 거기에만 생긴다는 보장이 없다 — herdr 는 `~/.herdr/worktrees/<repo>/<이름>` 에 만들고,
수동 `git worktree add` 는 아무 경로나 받는다. 그것들이 안 보이면 같은 번호를 두 번 배정하고,
그러면 §4.3 이 막으려던 바로 그 파괴(`quantbridge_w{N}_test` 공유 + Redis lock DB 공유)가
락을 우회해 되살아난다.

실측 판별력 (2026-07-29) — 레포 **밖**에 슬롯 3 을 쥔 워크트리를 두고 새 부트스트랩을 돌렸을 때:

| 코드                       | 배정된 슬롯         |
| -------------------------- | ------------------- |
| 현재 (`git worktree list`) | **4** (3 을 건너뜀) |
| 초판 (디렉터리 글롭)       | **3** — 충돌 재현   |

---

## 5. 사용법

### 새 워크트리

```bash
# 여러 벌을 한 화면에 — 워크트리 생성부터 에이전트 기동까지 한 번에 (§2.3)
scripts/herdr-fleet.sh --agent claude:bl537 --agent codex:impl

# Claude Code 세션에서 (.worktreeinclude 가 자동 적용된다)
#   EnterWorktree

# 또는 수동
git worktree add .claude/worktrees/<이름> -b <브랜치>

# 어느 쪽이든 부트스트랩은 필수
cd .claude/worktrees/<이름>
./scripts/worktree-bootstrap.sh                          # 슬롯 자동 할당 + deps
./scripts/worktree-bootstrap.sh --adopt-env              # env 가 안 따라온 워크트리 (수동/herdr)
./scripts/worktree-bootstrap.sh --skip-deps --skip-db    # 문서/계획 전용
./scripts/worktree-bootstrap.sh --slot 3                 # 슬롯 지정
```

**재실행은 안전하다.** 이미 슬롯이 있으면 그 번호를 유지한다 — 재실행이 슬롯을 바꾸면
이미 떠 있는 서버는 옛 포트에 남고 env·테스트 DB·Makefile 만 새 번호로 갈아타서,
이후 테스트와 E2E 가 서로 다른 인스턴스를 보게 된다.

`--slot N` 으로 **다른 워크트리가 쥔 번호를 지정하면 거부한다.** 그쪽이 서버를 안 띄워
포트가 비어 있어도 마찬가지다 — 포트가 아니라 `quantbridge_w{N}_test` 와 Redis lock DB 가
겹치는 것이 문제이고, 그러면 pytest 의 `drop_all` 과 마이그레이션이 서로를 파괴한다.

컨테이너가 안 떠 있으면 부트스트랩은 **실패로 끝난다**(`--skip-db` 로 명시 우회 가능).
경고만 하고 "준비 완료" 를 찍으면 슬롯 테스트 DB 없이 성공한 것처럼 보이고 pytest 가 즉시 깨진다.

브랜치가 이 스크립트를 포함하기 전 시점(구 베이스)에서 만든 워크트리라면
`../../../scripts/worktree-bootstrap.sh` 처럼 메인 체크아웃의 것을 직접 호출해도 된다 — cwd 기준으로 동작한다.

수동 `git worktree add` 와 herdr 는 `.worktreeinclude` 를 적용하지 **않는다** (그건 Claude Code 기능이지
git 기능이 아니다). 그 경우 부트스트랩은 fail-closed 로 멈춘다 — 사람에겐 그게 맞다.

**`--adopt-env` 는 그때 쓴다.** `.worktreeinclude` **자체를 목록으로 읽어** 메인에서 복사한다.
목록을 스크립트에 다시 적지 않는 이유는 두 벌이 되면 언젠가 갈리기 때문이다(한쪽에만 추가된 파일이
조용히 안 따라가는 형태로). 목록은 **이 워크트리** 것을 읽는다 — 무엇이 있어야 하는지 정하는 건 지금
체크아웃된 브랜치이고, 메인은 더 오래된 브랜치에 있을 수 있다(실측으로 그 상태를 밟았다).
glob 패턴은 다루지 않고 시끄럽게 건너뛴다.

### 워크트리 안에서

```bash
# BE 테스트 — env 소싱 필수 (AGENTS.md §BE pytest)
cd backend && set -a; . ./.env.local; set +a; uv run pytest

# 서버 — 포트는 .worktree-slot 이 결정한다
make be-isolated                     # 8100 + N (마이그레이션 선행은 슬롯≠0 이면 자동으로 빠진다)
make fe-isolated                     # 3100 + N

# E2E — 이 변수 없으면 3000 의 남의 앱을 검사한다 (실제 거짓 그린 사고 이력)
PLAYWRIGHT_BASE_URL=http://localhost:310N pnpm e2e
```

> **`QB_MIGRATE_DONE=1` 은 이제 필요 없다** (2026-07-29). 예전엔 워크트리에서 매번 붙여야 했고
> 한 번 빠뜨리면 워크트리 브랜치의 마이그레이션이 **공유 앱 DB** 에 걸렸다. §2.1 참조.
> 마이그레이션을 실제로 적용해야 하는 작업이면 여전히 메인 체크아웃에서 해라 — 가드가 거부한다.

### 정리

```bash
# 함대로 띄웠다면 화면부터
scripts/herdr-fleet.sh --teardown <workspace_id>

# 워크트리 자체는 항상 손으로 확인하고 지운다 — 에이전트가 커밋 안 한 작업을 들고 있을 수 있다
git -C .claude/worktrees/<이름> status --short
git worktree remove .claude/worktrees/<이름>
git branch -d wt/<이름>
docker exec quantbridge-db psql -U quantbridge -d postgres -c 'DROP DATABASE quantbridge_w<N>_test'
```

---

## 6. 워크트리로 따라가지 않는 것

`.claude/*` 가 통째로 gitignore 이고 env 도 전부 무시 대상이라, 아래는 `.worktreeinclude` 가 복사한다
(`EnterWorktree` 로 만들 때). 그 밖의 경로 — herdr · 수동 `git worktree add` — 에서는 부트스트랩의
`--adopt-env` 가 **같은 파일을 목록으로 읽어** 복사한다. 여기와 스크립트에 목록이 따로 있지 않다.

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
