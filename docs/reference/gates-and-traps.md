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
  ★★**변이 스크립트만의 문제가 아니다. 평범한 여러-단계 편집도 같은 함정이다.** 호출부를 먼저 넣고 헬퍼를 나중에 정의하는 순간, 그 **사이**에 watchfiles 가 중간 상태를 물어 `NameError` 로 평가가 죽고 세션이 fail-closed 비활성화된다. 2026-07-27 실측 — 활성 라이브 세션이 `live_signal_run_live_crash / NameError: name '_pending_fills_blocked_by_session' is not defined` 로 종료됐다(포지션·미체결은 0이라 피해는 없었다). **라이브 경로 모듈(`event_loop.py` / `strategy_state.py` / `tasks/live_signal.py`)을 편집할 때는 활성 세션이 없는지 먼저 확인하거나 beat 를 멈춰라.** 편집이 원자적일 거라고 가정하지 마라.
- ★**`codex exec -s workspace-write` 의 쓰기 루트 = 호출 시점 cwd.** 다른 디렉터리에서 부르면 대상 밖 파일 패치가 권한 거부되고 **0건 변경**으로 조용히 끝난다. 호출 전에 `pwd` 로 리포 루트를 확인해라. 그리고 `codex exec` 는 10분을 넘길 수 있어 Bash 상한(600000ms)에 걸리는데, **그때도 파일은 이미 쓰여 있을 수 있다** — 죽었다고 재실행하기 전에 `git status` 부터 봐라.
- ★**codex 샌드박스는 격리 Postgres(5433)에 못 붙는다.** 실DB 테스트가 `PermissionError` 로 `errors` 에 잡힌다. **메인 세션이 다시 돌려야 진짜 결과가 나온다**(실측: codex "7 errors" → 메인에서 282 passed). 그리고 **codex 자기보고를 재검증해라** — "gates-and-traps 에 승격했다" 고 보고했지만 파일이 미변경인 사례가 있었다.

### 라이브 신호 도메인

- ★**라이브 `live_signal_states.total_realized_pnl` 은 세션 원장이 아니다.** `run_live` 가 **창 안 청산만** 합산해 매 tick 덮어쓰므로 **단조가 아니다**(실측: 3건 `5.16879987` → 2건 `4.07002377`). 세션 손익의 SSOT 는 append-only 인 **`live_signal_events`** 다.
- ★**라이브 OHLCV 프레임은 `RangeIndex` + `timestamp` 컬럼**이다(`_ohlcv_rows_to_dataframe`). 인덱스에 의존하는 엔진 게이트(`sessions_allowed` 계열)는 **예외도 경고도 없이 no-op** 이 된다. 백테스트는 `v2_adapter` 가 422 로 막지만 라이브엔 등가물이 없었다.
- ★**시뮬 PnL 과 거래소 PnL 은 부호까지 다를 수 있다.** 같은 청산이 pine_v2 gross `+1.09877350` vs 거래소 net `-1.09767393` 이었다(수수료 왕복 약 2.057, 손검산 일치, raw HMAC 오라클로 외부 확인). **같은 누적기에 넣지 마라.**
- ★**`leverage` 를 엔진에 넘기면 마진 게이트만 켜지는 게 아니다.** `is_leverage_active` 가 `check_liquidations` 도 함께 켜고, 그건 실제 reduce-only 주문을 내는 **머니-패스 동작**이다. 청산 모델은 isolated 전용이라 cross 계정에는 이르게 발동한다(BL-490).

- ★**조건부(트리거) 주문은 `submitted` 로 몇 시간씩 산다.** `orphan_scanner` 의 30분 stuck 판정과 watchdog 이 그것을 "terminal 증거 미수신" 으로 오판해 **30분마다 CRITICAL 알림이 영구 반복**된다. `list_stuck_submitted` 계열은 `trigger_price IS NULL` 로 면제해야 한다. 면제의 의미는 "미발동을 stuck 으로 보지 않는다" 이지 "추적하지 않는다" 가 아니다.
- ★**`OrderService.execute` 는 같은 `idempotency_key` 를 다시 보면 거래소로 dispatch 하지 않고 캐시 응답을 돌려준다**(`order_service.py:417-419`). 취소 후 같은 의도로 재등재할 때 키가 같으면 **거래소엔 아무것도 안 올라가는데 DB 와 metric 은 "등재됨" 이라고 보고**한다. 라이브 키가 `bar_time` 을 싣는 이유가 이것이다 — 재등재 가능한 키에는 bar 를 넣어라.
- ★**`Order.idempotency_key` 는 `VARCHAR(200)`.** 초과하면 `StringDataRightTruncation` 이 상위 `except` 에 삼켜져 "장전됐다고 믿는데 거래소엔 없는" 상태가 된다. 키에 값을 싣기 전에 길이를 검사해라. 그리고 **`datetime.isoformat()` 은 `:` 를 포함**하므로 `:` 로 split 하는 키 형식에 넣지 마라(epoch 초를 써라).
- ★**`except` 블록도 실패 경로다.** `session.rollback()` 이 ORM 객체를 expire 시킨 뒤 `logger.exception(extra={"id": str(obj.id)})` 를 하면 lazy refresh 가 동기 컨텍스트에서 IO 를 시도해 `MissingGreenlet` 으로 **에러 핸들러 자신이 크래시한다**. 루프 안 예외 처리가 필요하면 ORM 속성을 `try` **밖에서 미리 확보**해라.
- ★**bybit ccxt 는 `precisionMode = TICK_SIZE`** 라 `market["precision"]["amount"]` 는 소수 자릿수가 아니라 **스텝 크기**다(BTCUSDT 0.001). 단 `limits.amount.min` 과 항상 같지는 않다.
- ★**이미 돌파된 트리거는 거래소가 거부한다** — `retCode 110093`. 롱 stop 은 트리거가 > 현재가, 숏 stop 은 < 현재가여야 한다. pine_v2 는 `low <= stop` 을 즉시 체결로 보므로 이 지점에서 시뮬과 거래소가 갈린다.
- ★**codex 프롬프트의 "변경 파일 정확히 N개" 는 신규 작업 파일에만 걸어라.** 그 변경이 깨뜨리는 기존 테스트를 파일 수에 안 넣으면 codex 가 **질문하고 멈춘다**(실측: G7 첫 실행 0건 변경). "부수 정합성 수정은 승인된 것으로 간주" 를 함께 적어라.
- ★**변이가 실제로 의미를 바꾸는지 먼저 확인해라.** `x=None or (...)` 는 Python 에서 `(...)` 라 no-op 이고, 그걸 모르면 "테스트 구멍" 으로 오판한다.

### 린트가 잡는 문자

- **RUF003** — 주석 안의 `×`(MULTIPLICATION SIGN) 와 `−`(MINUS SIGN) 가 ruff 를 깬다. ASCII `x` 와 `-` 를 써라. 네 번 재발했다. `tests/` · `scripts/` · `alembic/versions/` 는 면제지만 `src/` 는 아니다.
- **디자인 캐논 em-dash 래칫** — `frontend/src/__tests__/design-canon-source.test.ts` 가 노출 산문의 `—` 를 **파일별 정확 카운트로 양방향 동결**한다. 늘어도 줄어도 RED 다. `EM_DASH_ALLOWLIST` 를 올리지 말고 **문구에서 빼라**.
  ★ 이 래칫은 **FE 소스만 스캔한다.** 서버가 보내 화면에 렌더되는 문자열은 안 잡히므로 백엔드 문자열은 사람이 지켜야 한다.

### 언어·타입

- **`bool("false") is True`** — TradingView alert 은 문자열 불리언을 보낸다. 명시 화이트리스트로 방어해라.
- **`getattr(x, "f", False)`** 는 미구현 필드를 정상 False 로 위장한다.

### 게이트가 **거짓 red** 를 내는 경로 (2026-07-27 live-conditional-hardening)

- ★**dev 서버의 Turbopack CSS 캐시는 오래 살아남고, e2e 는 그 stale 자산을 검사한다.** `PLAYWRIGHT_BASE_URL=http://localhost:3100` 은 **실행 중인 dev 서버**를 재사용하므로, 그 서버가 옛 CSS 를 서빙하면 이미 고친 캐논이 다시 red 로 나온다. 거짓 그린만 조심할 게 아니다.
  - **판별법 = 세 층 대조.** ① 소스(`globals.css`) ② 프로덕션 빌드(`.next/static/chunks/*.css`) ③ **dev 서버가 실제로 서빙하는 것**. ③만 다르면 캐시다.
  - 서빙본 확인은 CSSOM 이 아니라 **원문 fetch** 로 해라 — `document.styleSheets` 순회는 inline sheet 를 놓치거나 `cssRules` 접근이 막힐 수 있어 "매치 규칙 0개" 같은 오답을 준다. `fetch(sheet.href).then(r => r.text())` 후 정규식으로 규칙을 찾아라.
  - 실측 — 소스·프로덕션 빌드에는 `.pager-nums{flex-wrap:wrap}` 이 있고 dev 서빙본에는 **없었다**. 프로덕션 빌드를 별도 포트에 띄워 재실행하니 그 캐논이 통과했다.
  - **이 함정의 4차 재발이다.** 앞선 세 번은 "고쳐도 적용이 안 된다" 는 인상으로 나타났다.
  - ★**복구 = 재기동뿐.** dev 서버를 죽이고 다시 띄운 뒤 같은 명령을 돌리니 코드 변경 0으로 **64/1 → 65-0** 이 됐다. `.next` 캐시를 **실행 중인 서버 밑에서 지우면** `routes-manifest.json` ENOENT 로 그 서버가 500 을 내니, 지우지 말고 **재기동**해라.
- ★**프로덕션 빌드로 e2e:authed 를 대신 돌리면 다른 것이 깨진다.** 그 suite 는 로컬 dev 전용이다(빌드 타임 env·Clerk storageState 전제). 프로덕션 실행은 **"코드가 맞다" 의 증명**으로만 쓰고, 게이트 숫자는 dev 서버를 재기동한 뒤 다시 재라.

### 캐시·주기 (2026-07-27 live-conditional-hardening)

- ★**새 Redis 캐시 키를 만들면 "누가 이 키를 지우는가" 를 같은 PR 에서 답하라.** 계정 스코프 포지션 캐시를 넣으면서 무효화 경로를 안 만들었고, 기존 세션 키 삭제는 **활성 세션 순회**라 활성 0건이면 아무것도 안 지웠다 — 그런데 그 기능이 존재하는 이유가 정확히 "활성 세션 0건" 상태였다. 결과는 청산 직후 15초 동안 **닫은 포지션이 살아 있는 청산 버튼과 함께 다시 렌더**.
  - ★**React Query invalidate 는 서버 캐시를 지우지 않는다.** 쿼리 키를 잘 배치해도 재조회가 서버 TTL 캐시에 적중하면 낡은 값이 그대로 온다. "무효화는 이미 맞다" 를 쓰기 전에 **양쪽 층을 다 확인**하라.
  - ★**dogfood 통과가 커버리지가 아니다.** 이 결함은 dogfood 를 통과했다 — 청산 후 확인까지 30초 넘게 걸려 15초 TTL 창을 못 밟았을 뿐이다.
- ★**"tick 간격" 을 상수의 근거로 삼기 전에 그 tick 이 실제로 언제 도는지 읽어라.** 라이브 평가는 beat 가 60초마다 fire 하지만 `no_new_bar` 조기 return 때문에 reconcile 은 **bar 마다**(1m/5m/15m/1h) 돈다. 60초를 전제로 잡은 3분 게이트는 1h 세션에서 보호값이 0이었다.
- ★**나이로 "사라졌다" 를 판정하지 마라.** 주문의 나이(`submitted_at`)와 부재의 나이는 다른 값이다. 조건부 주문은 정의상 오래 resting 한다. 부재는 **거래소에 직접 물어**(`fetch_order`) terminal 인지 확인하는 것이 유일하게 옳다.

### 변이 검증 (2026-07-27)

- ★**변이 스크립트에 `git checkout <file>` 을 넣지 마라.** 그 파일에 있던 **이번 스프린트 신규 코드까지 함께 사라진다**. 실제로 신규 repository 메서드가 통째로 날아갔고, "복원 확인" 단계에서 테스트가 여전히 red 인 것을 보고서야 알았다. 변이·복원은 **문자열 치환 쌍**으로 하고, 마지막에 **반드시 복원 확인 실행**을 넣어라.
- ★**픽스처 기본값은 게이트가 닫히는 쪽으로 둬라.** 나이 게이트를 넣을 때 `submitted_at` 기본값을 "방금" 으로 뒀다. 늙은 값이 기본이었으면 무관한 테스트들이 조용히 제거 경로를 타고, 변이가 아무것도 뒤집지 못했을 것이다.

### 추론 (2026-07-27)

- ★**"그 코드 경로의 흔적이 원장에 없다" 는 "그 코드가 호출된 적 없다" 가 아니다.** 조건부 UPDATE 가 경합에 **패배**하면 `rowcount=0` 이라 행에 아무것도 쓰지 않는다. 최종 행만 보고 "미주행" 을 결론내면 성공 경로와 시도 횟수를 혼동한 것이다. 호출·패배를 세려면 **전용 metric** 이 필요하다.

## 3.5 컨텍스트 예산 (2026-07-28 live-observability 실측 승격)

> 위임·집계 규율은 **실제로 작동한다** — 이번 세션은 codex 산출물 **239,167줄 중 ~300줄(0.1%)** 만, soak 샘플 9,143줄 중 델타 요약 2회만, `tasks/` 6,342 LOC 는 **0줄** 올렸다.
> 소모는 **규칙이 없던 채널**에서 났다. 아래 둘이 그 채널이다.

### ★서브에이전트는 컨텍스트가 아니라 **파일로** 답한다

읽기 전용 조사·적대 검증 에이전트를 띄울 때, 프롬프트에 **반드시** 넣어라:

> **전체 리포트는 `<스크래치패드>/<이름>.md` 에 써라. 반환값은 30줄 이하 요약 + 그 파일 경로만 준다.**

- "120줄 이내로 압축해라" 같은 **상한은 강제력이 없다** — 실제로 6기가 100~200줄 조밀한 마크다운을 반환했고 그게 이번 세션 최대 단일 소모원이었다.
- 요약만 읽고, 근거가 필요할 때 그 파일을 `grep` 한다. 대부분은 grep 조차 안 하게 된다.
- ★이건 **품질 손실이 아니다.** 에이전트는 같은 조사를 하고, 결론도 같다. 달라지는 건 그 결론이 어디에 놓이느냐뿐이다.

### ★Monitor 는 "변화마다" 가 아니라 **"위험 신호 + 하트비트"**

- 카운터가 1~2분마다 바뀌는 대상(주문 수 등)에 **변화 감지 발화**를 걸면 90분에 30회 발화하고, 매 발화가 **한 턴 전체**(이벤트 + 시스템 리마인더 + 응답)를 소비한다. 이번 세션에서 그 30회 중 **의미 있었던 건 1건**(세션 비활성화)이었다.
- 즉시 발화는 **작업을 죽이는 사건만** — 세션 비활성화 · kill switch 발화 · 외부 의존성 실패(DNS 등).
- 진행 상황은 **10~15분 하트비트 1줄**로 충분하다.
- 판단: _"이 발화를 보고 내가 무언가를 할 것인가?"_ 아니면 발화 대상이 아니다.

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
