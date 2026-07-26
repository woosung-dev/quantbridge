# 게이트와 함정 — 모든 세션이 여는 문서

> 무엇을 돌려야 "통과" 인지와, 통과한 줄 알았는데 아닌 경우들.
> 2026-07-26 신설. 이 내용은 그전까지 스프린트 문서 7개에 복붙되고 있었고,
> `reference/` 에 있던 유일한 진술은 **틀려 있었다** (아래 `pnpm test` 항목).

---

## 1. 통과 가능한 게이트

```bash
QB=/Users/woosung/project/agy-project/quant-bridge

# 인프라 (격리 포트)
cd $QB && make up-isolated && make migrate-isolated

# BE — ruff / mypy / pytest
cd $QB/backend && uv run ruff check .
cd $QB/backend && uv run mypy src/
cd $QB/backend && set -a; source .env.local; set +a; uv run pytest -q

# FE — typecheck / vitest / eslint
cd $QB/frontend && pnpm typecheck
cd $QB/frontend && pnpm test
cd $QB/frontend && pnpm lint
cd $QB/frontend && pnpm build          # Clerk 키 필요

# 디자인 캐논 런타임 (dev 서버 자동 기동, 인증 불요)
cd $QB/frontend && pnpm e2e:design-canon

# e2e authed (frontend/.env.local 에 Clerk 4종 필요, 로컬 전용 — CI 에 없다)
cd $QB/frontend && pnpm e2e:authed
```

`make lint` / `make typecheck` / `make test` 는 위를 FE+BE 로 묶은 것이다. 단 **env 를 source 하지 않으므로** BE pytest 는 셸에 3-env 가 이미 있어야 한다.

## 2. 통과 가능한 게이트가 **아닌** 것

- **`ruff format`** — 이 레포는 포매터를 게이트로 쓰지 않는다.
- **`prettier` / `format:check`** — main 에 선재 red 356 건. 고치라는 신호가 아니다.
- **Pyright / IDE 인라인 진단** — IDE 가 uv 가상환경을 못 잡아 `pandas`·`pydantic`·`celery` 를 "unresolved" 로 표시한다. 권위는 `mypy src/` 다.

## 3. 함정

### 조용히 통과한 것처럼 보이는 것

- **`pnpm test --run` 을 쓰지 마라.** `"test": "vitest run"` 이라 `--run` 이 중복 전달되고 `Unknown option` 으로 죽으면서 **exit code 0** 을 낸다. `pnpm test` 가 정답이다.
  (CI 는 `pnpm test -- --run` 을 쓴다 — `--` 구분자가 있어 동작한다.)
- **`| tail` 로 파이프하지 마라.** 파이프라인 exit code 가 `tail` 것으로 바뀌어 실패가 사라진다.
- **백그라운드 pytest 를 `| tail` 로 감싸면** 끝날 때까지 출력 파일이 비어 있다. 진행 중인지 죽은 건지는 `pgrep -f pytest` 로 본다.
- ★★**e2e 가 남의 앱을 검사할 수 있다.** `frontend/playwright.config.ts` 의 `baseURL` 기본값은 **3000** 인데 격리 스택 FE 는 **3100** 이다. 3000 을 다른 웹앱이 점유하면 캐논이 그 앱을 감사한다. 실측 정체성 프로브:
  ```
  http://localhost:3000  ->  <title>Nexus - AI 챗봇 포털</title>
  http://localhost:3100  ->  <title>QuantBridge</title>
  ```
  `PLAYWRIGHT_BASE_URL=http://localhost:3100` 으로 재실행하면 27/32 가 **32** 가 된다. **실패 5건보다 무서운 건 통과 27건**이다 — 남의 앱 상대 통과라 전부 거짓 그린이었다. **게이트 전에 FE 정체성부터 프로브해라.**

### 환경

- **BE pytest 는 `.env.local` 을 통째로 source 해야 한다.**
  ```bash
  set -a; source .env.local; set +a
  ```
  개별 export 금지. `DATABASE_URL` 만 있으면 `tests/test_migrations.py` 의 `downgrade(base)` 가 **개발 DB 를 향한다** — 실제로 주문 17행과 암호화된 API 키가 전소한 적이 있다. 지금은 `_assert_disposable_database` 가 DSN 이 `_test` 로 안 끝나면 막지만, 가드를 믿지 말고 3-env 를 함께 넣어라.
- **수동 `alembic` 은 개발 DB 를 향한다.** 테스트 DB 에 마이그레이션을 돌리려면 `tests.test_migrations._alembic_cfg()` 를 재사용해라 (`_assert_disposable_database` 가 내장돼 있다).
- **`test_migrations.py` 가 `DuplicateColumn` 으로 실패하면 대개 코드 결함이 아니다.** conftest 의 `SQLModel.metadata.create_all` 이 신규 컬럼을 이미 만들어둔 상태에서 `alembic_version` 만 stale 인 경우다. `downgrade base → upgrade head` 로 재구축하면 풀린다.
- compose 는 항상 두 파일을 겹쳐 쓴다. worker 만 재시작할 때는 **`--no-deps`** 를 붙여라.
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.isolated.yml ... --no-deps
  ```
- Docker VM 디스크가 차면 Postgres 가 무한 크래시 루프에 빠진다. **`docker builder prune -f` 만 안전**하다 (볼륨·이미지 prune 금지).
- ★**워커는 `backend/src` 를 `/app/src` 로 bind-mount + watchfiles 로 문다.** 작업 중인 코드가 실거래 세션에 **즉시** 반영된다. 관측에는 유용하지만(수정 전후를 실데이터로 잡을 수 있다) **변이 스크립트를 돌리기 전에는 워커를 멈춰라** — 문법을 깨는 변이면 평가가 예외로 죽고 세션이 자동 비활성화된다.
- ★**`codex exec -s workspace-write` 의 쓰기 루트 = 호출 시점 cwd.** 다른 디렉터리에서 부르면 대상 밖 파일 패치가 권한 거부되고 **0건 변경**으로 조용히 끝난다. 호출 전에 `pwd` 로 리포 루트를 확인해라. 그리고 `codex exec` 는 10분을 넘길 수 있어 Bash 상한(600000ms)에 걸리는데, **그때도 파일은 이미 쓰여 있을 수 있다** — 죽었다고 재실행하기 전에 `git status` 부터 봐라.
- ★**codex 샌드박스는 격리 Postgres(5433)에 못 붙는다.** 실DB 테스트가 `PermissionError` 로 `errors` 에 잡힌다. **메인 세션이 다시 돌려야 진짜 결과가 나온다**(실측: codex "7 errors" → 메인에서 282 passed). 그리고 **codex 자기보고를 재검증해라** — "gates-and-traps 에 승격했다" 고 보고했지만 파일이 미변경인 사례가 있었다.

### 라이브 신호 도메인

- ★**라이브 `live_signal_states.total_realized_pnl` 은 세션 원장이 아니다.** `run_live` 가 **창 안 청산만** 합산해 매 tick 덮어쓰므로 **단조가 아니다**(실측: 3건 `5.16879987` → 2건 `4.07002377`). 세션 손익의 SSOT 는 append-only 인 **`live_signal_events`** 다.
- ★**라이브 OHLCV 프레임은 `RangeIndex` + `timestamp` 컬럼**이다(`_ohlcv_rows_to_dataframe`). 인덱스에 의존하는 엔진 게이트(`sessions_allowed` 계열)는 **예외도 경고도 없이 no-op** 이 된다. 백테스트는 `v2_adapter` 가 422 로 막지만 라이브엔 등가물이 없었다.
- ★**시뮬 PnL 과 거래소 PnL 은 부호까지 다를 수 있다.** 같은 청산이 pine_v2 gross `+1.09877350` vs 거래소 net `-1.09767393` 이었다(수수료 왕복 약 2.057, 손검산 일치, raw HMAC 오라클로 외부 확인). **같은 누적기에 넣지 마라.**
- ★**`leverage` 를 엔진에 넘기면 마진 게이트만 켜지는 게 아니다.** `is_leverage_active` 가 `check_liquidations` 도 함께 켜고, 그건 실제 reduce-only 주문을 내는 **머니-패스 동작**이다. 청산 모델은 isolated 전용이라 cross 계정에는 이르게 발동한다(BL-490).

### 린트가 잡는 문자

- **RUF003** — 주석 안의 `×`(MULTIPLICATION SIGN) 와 `−`(MINUS SIGN) 가 ruff 를 깬다. ASCII `x` 와 `-` 를 써라. 네 번 재발했다. `tests/` · `scripts/` · `alembic/versions/` 는 면제지만 `src/` 는 아니다.
- **디자인 캐논 em-dash 래칫** — `frontend/src/__tests__/design-canon-source.test.ts` 가 노출 산문의 `—` 를 **파일별 정확 카운트로 양방향 동결**한다. 늘어도 줄어도 RED 다. `EM_DASH_ALLOWLIST` 를 올리지 말고 **문구에서 빼라**.
  ★ 이 래칫은 **FE 소스만 스캔한다.** 서버가 보내 화면에 렌더되는 문자열은 안 잡히므로 백엔드 문자열은 사람이 지켜야 한다.

### 언어·타입

- **`bool("false") is True`** — TradingView alert 은 문자열 불리언을 보낸다. 명시 화이트리스트로 방어해라.
- **`getattr(x, "f", False)`** 는 미구현 필드를 정상 False 로 위장한다.

## 4. pre-push 훅

`.husky/pre-push` 는 main worktree 에서:

- `main` / `master` push **영구 차단** (bypass 불가)
- `feat/*` `fix/*` `chore/*` `docs/*` `test/*` `refactor/*` `hotfix/*` 만 허용. 그 외는 `QB_PRE_PUSH_BYPASS=1` 필요
- `frontend/` 변경 시 `pnpm typecheck && pnpm test`
- `backend/` 변경 시 `uv run ruff check . && uv run mypy src/` (**pytest 는 opt-in** — `QB_RUN_PYTEST=1`)
- `backend/.env.local` 에서 **`TEST_` 접두 변수만** 자동 export. `DATABASE_URL` 은 안 들어온다

## 5. 격리 스택

| 항목     | 기본 | 격리 (`make up-isolated`) |
| -------- | ---- | ------------------------- |
| FE       | 3000 | **3100**                  |
| BE       | 8000 | **8100**                  |
| Postgres | 5432 | **5433**                  |
| Redis    | 6379 | **6380**                  |

다른 웹앱과 병렬로 돌릴 때 격리가 디폴트다. 옛 스프린트 문서의 `5436` 표기는 stale — 2026-07-25 포트 정렬 이후 **5433** 이 정답이다.

---

**관리 규약** — 새 스프린트에서 게이트 함정을 발견하면 자기 체크리스트에 적지 말고 **여기에 추가**해라. 그게 이 파일이 존재하는 이유다.
