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

### 거래소 실상 (2026-07-28 live-entry-parity, 실거래소 실측)

- ★★**ccxt 에서 `BTC/USDT` 는 perp 이 아니라 스팟이다.** linear perp 는 `BTC/USDT:USDT` 이고 변환기가 이미 있다(`providers.py` `_to_bybit_linear_symbol`). 실측:
  ```
  ccxt.market("BTC/USDT")      -> type=spot
  ccxt.market("BTC/USDT:USDT") -> type=swap, linear=True
  spot last=63561.2  perp last=63526.7  차이 34.50 USDT (0.0543%)
  ```
  **`fetch_ticker` 를 원문 심볼로 부르면 다른 자산의 가격을 읽는다.** 트리거 판정처럼 bp 단위가 중요한 곳에서는 신호보다 오차가 커진다(실측: 오차 0.054% vs 잡으려던 돌파폭 중앙값 0.025%).
- ★**ccxt ticker 에 `"mark"` 키는 없다.** mark price 는 `ticker["info"]["markPrice"]` 다. `ticker.get("mark")` 는 항상 `None` 이라 `fetch_mark_price` 는 도입 이래 늘 `last` 로 폴백해 왔다.
- ★**돌파 거절코드는 방향별로 다르다** — `110092` = "expect Rising"(**롱** stop), `110093` = "expect Falling"(**숏** stop). 한쪽만 allowlist 에 넣으면 절반을 놓친다.
- ★**`110017` 은 "포지션 0" 이 아니라 "reduce-only 규칙 위반"** 이다(ccxt 에러맵). "포지션 없음" 은 `110034` 다. 우리 원장의 옛 메시지만 보고 매핑하면 **포지션 반전 부작용이 "무해" 로 위장**된다(실측으로 재현됨 — `"reduce-only order has same side with current position"`).
- ★**Bybit demo 는 시장가 주문도 `create_order` 응답에서 `submitted` 로 준다.** 체결 확정은 WS 가 나중에 한다(`websocket/state_handler.py` · `reconciliation.py`). 따라서 "거래소가 수락했다" 를 `filled` 로만 세면 **그 카운터는 영구히 0** 이다.

### 검증이 무언가를 증명하지 못하는 세 가지 방식 (2026-07-28 live-outcome-parity, 한 스프린트에서 3회)

- ★★★**필터는 그 필터가 배제하는 것이 픽스처에 있어야만 증명된다.** 한 스프린트에서 **세 번** 같은 유형으로 탈출했다:
  1. 파생값 직접 단언이 없어 **항등식이 어떤 값이든 통과** (`execution_gap` 이 피연산자에서 파생되므로 자기 자신을 증명한다)
  2. 픽스처에 `entry` 이벤트가 없어 **`action == 'close'` 필터가 no-op**
  3. 픽스처에 미동기 주문이 없어 **`realized_pnl_synced_at IS NOT NULL` 필터가 no-op**
     → 그 필터는 화면이 동어반복이 되는 것을 막는 유일한 방어선이었다.
     **생성자가 쓰는 픽스처는 자연히 happy path 만 담는다. 무언가를 _제외하는_ 규칙은 구조적으로 검증되지 않는다.**
- ★★**항등식은 정합성 검사가 아니다.** `a + (b-a) + (c-b) == c` 는 산술적으로 항상 참이다. 그런 형태를 게이트로 쓰면
  조인이 틀려도 통과한다. 검사는 **"어떤 관측이 그 계산에 들어갔는가"**(coverage)로 해야 한다.
- ★★**커버리지를 하나로 뭉치지 마라.** `matched / (matched + 미매칭)` 은 **분해가 하나도 안 돼도 100%** 가 된다
  (undecomposed 가 matched 의 부분집합이므로). 실측: 매칭 21 · 분해가능 0 → 커버리지 100%. 청산 원장이
  `now - 7일` 부터만 적재되므로 **7일 지난 세션은 전부 그 상태**가 된다. 매칭/분해 두 축으로 쪼개라.
- ★★**"처분했다" 고 문서에 적은 것이 처분되지 않을 수 있다.** 리뷰 지적 D5(네이티브 브래킷 청산 누락)를
  "`actual_only` 가 net 금액도 갖게 한다" 로 처분했다고 적었으나, `actual_only = A \\ M` 이고 `A` 는 확정 **주문**
  집합이라 주문이 없는 청산은 애초에 A 에 없었다. **처분 문장이 아니라 코드로 재확인해라.**

### 수정이 새 표면을 만든다 (2026-07-28)

- ★★★**리뷰 지적을 고친 diff 를 다시 리뷰해라.** live-outcome-parity 에서 G6 P1 수리가 **새 P1 을 세 개** 만들었고
  재리뷰가 두 번째 HOLD 를 냈다. 1차 리뷰가 잡은 것은 1차 수정에서 재발하지 않았다 — **새로 만든 표면에서 났다.**
- ★★★**레포가 이미 배운 버그를 되살리지 마라.** ledger dedup 에 `max(closed_pnl)` 을 썼는데,
  `providers.py` 의 `aggregate_closed_pnl_by_order` docstring 이 **정확히 그 실패 모드**를 이미 적어두고 있었다
  ("마지막 행만 취하면 부분 손익이 영구 고정된다"). 집계 규칙을 새로 쓰기 전에 **같은 데이터에 대한 기존 헬퍼를 먼저 찾아라.**
  ★건수는 맞고 금액만 틀리므로 커버리지 같은 파생은 **정상처럼 보인다.**
- ★★★**동결 스펙을 넓혔으면 그 문서를 갱신해라 — 아니면 삭제할 때 근거가 사라진다.** live-outcome-parity 는
  G1 에서 "변경하려면 사유를 이 문서에 남긴다" 고 스스로 규정해놓고 스코프를 **두 번** 넓히고도(도달 경로 신설 ·
  fail-closed 조건 3->5) 문서를 갱신하지 않은 채 G8 에서 삭제했다. 2축 리뷰가 그 이탈을 전부 잡아냈고,
  "왜 넓혔는가" 를 dev-log 에서 역추적해야 했다.
- ★★★**수용 기준 문서는 자기 집행되지 않는다.** 한 스프린트에서 **두 번** — G1 에 "이렇게 한다" 고 적은 항목이
  구현에 반영되지 않은 채 게이트를 통과했다(브래킷 청산 `actual_only` 편입 · `inferred` 귀속 격리).
  둘 다 **최종 리뷰가 잡았다.** 수용 기준을 쓴 것과 그것이 코드에 있는 것은 다른 사건이다 —
  **G3 코드 대조에서 수용 기준을 한 줄씩 짚어 확인해라.**
- ★★**코드가 스스로 봉인한 값을 우회하지 마라.** `exit_attribution.attribute_exit` 은 주석으로
  "`inferred` 는 검정력이 없다. **리스크 게이트 입력으로 절대 쓰지 않는다**" 를 명시하는데,
  신규 집계가 `attributed_strategy_id` 를 `attribution_confidence` 확인 없이 써서 그 봉인을 뚫었다.
  **`*_confidence` / `*_source` 류 판별자가 있는 컬럼은 값만 읽지 말고 판별자를 함께 읽어라.**
- ★★**"처분했다" 는 문장은 처분의 증거가 아니다.** 리뷰 지적을 처분 표에 "인정 -> 처분" 으로 적었는데
  실제 코드는 그 결함을 그대로 갖고 있던 사례가 났다(`actual_only = A \\ M` 인데 `A` 가 주문 집합이라
  주문 없는 청산은 애초에 A 에 없었다). **처분 문장이 아니라 코드로 재확인해라.**

### 통계 게이트 (2026-07-28)

- ★★**표본 자신에서 유도한 임계는 표본이 작을 때 오히려 열린다.** `required_n = (k x sd / |mean|)^2` 는
  **평균의 정밀도**를 재는데, n 이 작으면 **sd 추정 자체가 신뢰할 수 없다.** 실측: n=3, sd=0.159, mean=-0.921
  → `required_n = 1` → 게이트 통과. 하한을 **데이터가 아니라 추정량의 요구조건**(CLT)에서 가져와라.
- ★**짝지어진 값을 독립 표본으로 다루지 마라.** gross 와 수수료는 같은 주문에서 나온다. 두 평균의 간격을
  독립 표본처럼 재면 틀린다. 올바른 통계량은 **차이 자체**(= net) 한 표본이다.
- ★**분모가 무엇인지 라벨에 적어라.** `cost / round_trip_notional` 에서 분모가 두 leg 합이면 그 값은 **편도**다.
  왕복 가정(0.30%)과 나란히 놓으면 **2배 어긋난 비교**가 된다. 실측에서 화면이 편도 0.06% 를 왕복 0.30% 와 비교했다.
- ★**`Decimal` 기본 컨텍스트는 prec=28 이다.** `Numeric(18,8)` 곱은 최대 36 유효숫자라 조용히 반올림된다.
  금융 파생 모듈은 `localcontext(Context(prec=50))` 로 감싸라. ★그리고 **테스트도 같은 컨텍스트에서 비교**해야 한다 —
  기본 컨텍스트로 항등식을 재계산하면 마지막 자리가 어긋나 거짓 red 가 난다.

### 원장을 읽을 때 (2026-07-30 close-mismatch-visibility)

- ★★★**`orders.filled_at` 은 이름과 달리 terminal_at 이다** — 체결뿐 아니라 **취소·거절 시각도**
  여기 들어간다(`models.py:293-296` 주석이 이미 그렇게 적었다). 그리고 **한 주문의 terminal 과
  다음 주문의 `created_at` 을 섞지 마라.** 실측 사고 — `0.058` 주문이 09:09:46 까지 살아 있다고
  적었는데 그건 **다음 주문의 생성 시각**이었고 실제 terminal 은 09:07:40 이었다(1m49s vs 3분).
- ★★**라이브 진입 key 는 형식이 둘이다.** 조건부 = `live:<sess>:cond:<bar_epoch>:<stop>:<qty>:<trade_id>`,
  시장가 = `live:<sess>:<bar_time ISO>:<seq>:<action>:<trade_id>`. `split_part` 로 한 형식만
  가정해 자르면 **다른 형식이 조용히 오분류**된다(실측: 21행을 `cond` 로 읽었는데
  `LIKE ':cond:%'` 카운트는 0이었다). **분해 결과를 쓰기 전에 원문을 한 번 출력해라.**
  귀속의 권위는 `conditional_entry_planner.parse_live_entry_key` **하나**다.
- ★★★**같은 에러 코드 안의 갈래가 위험도가 다르면 그 코드는 라벨이 될 수 없다.**
  `110017` 이 `same side`(★엔진↔거래소 **반대 방향**) 9건과 `current position is zero`(무해) 30건을
  한 라벨에 담고 있었다. **무해가 3배라 위험이 수적으로 묻혔고** counter 는 계속 "유령 포지션" 만
  가리켰다. 이 저장소가 `110017` 로 이 교훈을 **두 번째** 받은 것이다.
- ★★**`live_signal_events` 는 진입을 세지 않는다.** `entry`/`close` 시장가만 담고
  **조건부 진입은 거치지 않는다**. 그래서 `bool(new_events)` 로 만든 판정
  (`deferred_market_inflight`)은 stop-entry 전략에서 **사실상 「청산 tick 수」** 다.
  ★그 counter 는 `desired` 를 **읽기 전에** 오르므로 **미룰 진입이 0건이어도 발화한다.**
  **분모를 확인하지 않은 비중(예: "합의 75%")은 측정이 아니다.**

### 측정 도구가 먼저 틀린다 (2026-07-30 — 한 회차에 **6번**)

> ★평가자의 계측기가 6번 먼저 틀렸고 **6/6 전부 "코드가 틀렸다" 로 갈 뻔했다.** 유형이 반복된다.

- ★★**출력을 자르면 코드가 틀린 것처럼 보인다.** `final-gates.sh` 의 `skip_gate` 는 라벨(`▶ BE ruff`)을
  먼저 찍고 **다음 줄에** `→ 건너뜀` 을 찍는다. `head -3` 으로 자르면 "돌면 안 되는 게 돌았다" 로 읽힌다.
- ★★**표적 변이 앵커 3대 오류** — ① 앵커 문자열이 **유일하지 않음**(치환이 여러 곳에 먹어 의미가 흐려진다)
  ② **주석**을 앵커로 잡음(코드가 아니라 문서를 바꿨으니 당연히 green) ③ 정의와 사용처를 **함께** 바꾼
  **동치 rename**(이름만 바뀌고 동작은 같다). 셋 다 "탈출" 로 보고될 뻔했다.
  → **변이를 넣기 전에 `text.count(old) == 1` 을 단언하고, 그 앵커가 실제 판정 지점인지 눈으로 확인해라.**
- ★★**두 원장을 비교할 때 시각을 맞춰라.** 원장 `cancelled` 9(10:06)와 counter `replaced` 11(10:20)을
  대조해 "부등식 위반" 을 의심했으나, **같은 시점**에서는 `14 >= 14` 로 정확히 성립했다.
  누적 counter 와 DB 를 비교할 때 **관측 시각이 다르면 그 비교는 무의미하다.**
- ★★**감시 스크립트도 fail-open 이 된다.** soak 감시가 **종료된 세션을 "생존" 으로** 보고했다 —
  `psql` 이 실패하면 빈 문자열이 되어 사망 판정(`= "f"`)에 안 걸리고 하트비트로 넘어갔다.
  **조회 실패를 "이상 없음" 으로 수렴시키지 마라** — 판정 불가는 별도 상태여야 한다.
- ★★★**서로 다른 시점에 도입된 counter 는 절대값 비교가 구조적으로 불가능하다.** 같은 사건을 세는
  두 counter 가 **126 vs 99** 로 어긋났는데, 원인은 로직이 아니라 **출생일**이었다
  (`qb_live_conditional_placed_total` PR #489 / `qb_live_conditional_guard_total` PR #493, **하루 차**).
  **차분에서는 정확히 일치한다.** 절대값을 나란히 놓는 순간 그 표는 거짓말한다.

### 측정 도구가 먼저 틀린다 (2026-07-30 close-mismatch-soak — 또 **2번**)

> ★**0 이든 큰 수든, 숫자를 보면 계측기를 먼저 의심해라.** 이 레포에서 **7번째**다.

- ★★★**JOIN 이 카운트를 조용히 뻥튀긴다.** soak 감시가 `same_side=14` 로 보고했으나 실제는 **1건**이었다.
  `orders JOIN live_signal_sessions ON exchange_account_id` 이 그 계정의 **세션 14개만큼 행을 곱했다**.
  사전등록 판정(V3)을 **오판할 뻔했다**. → **집계 쿼리에 JOIN 을 넣기 전에 `count(*)` 를 JOIN 없이 한 번 재라.**
- ★★**정규화 함수 프로브는 그 함수가 받는 **실제 형태**로 넣어라.** `_normalize_exchange_order_response_reason`
  에 산문(`"bybit 110017 reduce-only ... same side"`)을 넣어 3건 전부 `unparsed` 가 나왔고 "배선이 죽었다" 로
  읽힐 뻔했다. 실제 패턴은 `"retCode"\s*:\s*(\d+)` — **호출부가 넘기는 것은 `str(e)` 의 JSON 본문**이다.
- ★★**`prometheus_client` 는 첫 `.labels()` 증가 전까지 child series 를 만들지 않는다.** 그래서
  "신규 라벨이 `/metrics` 에 **샘플과 함께** 보일 것" 같은 사전등록 문턱은 **발화 전에는 구조적으로 충족 불가**다
  (재기동해도 안 뜬다). → 문턱은 **코드 sentinel(러닝 워커 안에서 import 해 호출)** 과 **사후 발화** 로 갈라 써라.
- ★**before 스냅샷에 그 series 가 없으면 `after - 0` 은 차분이 아니라 절대값이다.** 리포트에 그 사실을 적어라.

### 게이트가 "돌렸다" 만 보증한다 (2026-07-30)

- ★★**`final-gates.sh` 는 exit code 만 기록한다 — 테스트 개수를 찍지 않는다.** 스크립트 자신이 마지막 줄에
  그렇게 경고한다. **baseline 대조는 사람이 따로 해야 한다**(이번에 문서의 `FE 1231` 이 stale 이었고
  main 을 직접 재보니 **1232** 였다). **baseline 은 언제나 대조 대상이다.**
- ★★**`pnpm e2e`(chromium 4건)는 게이트 체인 밖이 맞다.** 게이트가 도는 것은
  `chromium-design-canon` · `chromium-authed` 라는 **다른 프로젝트**다. 게이트 로그에 `e2e ... PASS` 가
  보인다고 BL-556 의 수동 1회가 면제되지 않는다.
- ★**`pnpm test --run` 은 Unknown option.** 이 레포는 `pnpm test`(= `vitest run`).
- ★**`EXIT=$?` 를 파이프 뒤에 쓰면 마지막 명령(`tail`)의 종료코드를 읽는다.** `bl-audit.sh` 를 exit 0 으로
  오판할 뻔했다. 종료코드가 판정인 스크립트는 **파이프 없이** 돌리고 그 다음 줄에서 `$?` 를 읽어라.
- ★**`git merge-tree` 는 커밋을 받는다.** 트리 해시를 넘기면 거짓 충돌처럼 보인다.
  브랜치 2개가 각각 main 에 clean 하고 **변경 파일 집합이 disjoint** 면 순차 머지도 clean 이다.

### 신규 BE 필드는 FE `.strict()` 스키마와 **항상** 대조해라 (2026-07-30, codex 적대 리뷰 MAJOR)

> ★★★**읽기 경로가 정상인 것은 쓰기 경로가 정상이라는 증거가 아니다.**

`StrategySettings` 에 필드를 추가하면 BE 가 그것을 **`default=None` 으로 emit** 하고
`strategy/service.py` 의 `update_settings` 가 `settings.model_dump()` 를 **그대로 JSONB 에 저장**한다.
FE `StrategySettingsSchema` 는 `.strict()` 라 모르는 키에서 **파싱이 실패**한다
⇒ **설정을 한 번만 저장해도 그 전략의 FE 파싱이 영구히 깨진다.**

★**GET 응답에는 그 키가 없어서**(BE 가 DB JSONB 를 그대로 돌려준다) **화면을 3개 돌아도 안 잡힌다.**
저장 경로에서만 터진다. 실제로 워커·평가자 둘 다 "동작 영향 없음" 으로 오판했고 codex 가 잡았다.
→ **BE 설정 스키마에 필드를 더하면 같은 PR 에서 `frontend/src/features/strategy/schemas.ts` 를 고쳐라.**

### 측정 도구가 먼저 틀린다 (2026-07-28)

- ★★**`/metrics` 가 HELP/TYPE 만 보이고 샘플이 없으면 백엔드를 재기동해라.** `PROMETHEUS_MULTIPROC_DIR` 배선 **이전에** 뜬 프로세스는 단일 프로세스 모드라 **자기 값만** 노출한다. 그 상태에서 관측한 worker metric 처럼 보이는 값들이 사실은 API 프로세스 자신의 것일 수 있다.
- ★★**`MmapedDict.read_all_values_from_file` 은 4-튜플을 준다.** `for k, v in ...` 로 풀면 `ValueError` 가 나고, 그걸 `except: pass` 로 삼키면 **"1389개 파일 전부에 metric 0개"** 라는 오답이 나온다. **측정값이 0이면 대상보다 계측기를 먼저 의심해라.**
- ★★**변이가 두 구현이 동치인 지점에 떨어지면 아무것도 증명하지 못한다.** "fail-closed 를 조기 `return` 으로" 변이를 **취소 루프 뒤**에 넣었더니 `to_place=()` 와 의미가 같아 통과했다. 앞으로 옮기니 즉시 잡혔다. **탈출을 보고 "테스트가 약하다" 로 바로 가지 마라 — 변이가 실제로 무엇을 바꿨는지 먼저 봐라.** (같은 회차에서 2번 발생: 다른 하나는 두 가드가 같은 mock 을 써서 서로를 가린 경우였다.)
- ★**변이 대상 테스트 파일을 맞게 골라라.** 리포지토리 SQL 을 겨눈 변이를 서비스 테스트(리포지토리를 mock 함)로 재면 영원히 통과한다.

### 셸·게이트가 거짓 red 를 내는 경로 (2026-07-28)

- ★★**Bash 도구의 cwd 는 호출 간 유지된다.** `cd backend && set -a; . ./.env.local; set +a; uv run pytest` 를 **두 번째로** 부르면 `cd backend` 가 실패하고 `&&` 때문에 **`set -a` 가 안 돈다.** env 가 export 되지 않아 `localhost:5432` 로 붙고 대량 에러가 난다 — 코드 결함처럼 보이는 거짓 red 다. **절대경로로 `cd` 해라.**
- ★★**부분 선택 실행은 격리가 깨진다.** `pytest tests/tasks/x.py tests/trading/ tests/strategy/` 조합에서 **30건이 실패**했지만 같은 테스트를 단건으로 돌리면 통과하고 **전체 스위트도 통과**한다. 판정 권위는 **전체 스위트**다.

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

### 계기(instrument) — 어떤 상품의 가격을 보고 있는가 (2026-07-28)

- ★★★**"같은 심볼" 이 같은 상품이라는 뜻이 아니다.** `ccxt` 인스턴스의 `defaultType` 이 심볼 해석을 바꾼다. 이 저장소에서 `BTC/USDT` 는 **스팟**, `BTC/USDT:USDT` 가 **무기한선물**이다. `market_data/providers/ccxt.py` 는 `defaultType: "spot"` 이고 `trading/providers.py` 의 `BybitFuturesProvider` 는 `"linear"` 다 — **두 모듈이 같은 문자열을 서로 다른 상품으로 읽는다.**
  - 그래서 라이브 엔진이 **스팟 봉을 재생하면서 perp 에 주문을 냈다**(BL-530). 실측 괴리는 **25~42 USDT (0.04~0.066%)** 로 지속적이고 **한쪽으로 치우친다** — 스팟이 위. 매수 스톱은 시뮬에서만 걸리고 매도 스톱은 거래소에서만 걸리는 **방향성 편향**이 된다.
  - 결정적 증거: 2026-07-28 08:06 UTC 스팟 고가가 **63541.7** 로 시뮬 스톱과 **소수점까지 일치**했는데 같은 분 perp 고가는 **63499.4**. 픽스처로 고정했다(`tests/fixtures/bybit_spot_vs_perp_bars.py`).
  - ★**BL-511 이 같은 결함을 가드 기준가에서 한 번 고쳤는데도 엔진 봉은 그대로였다.** 계기 정렬은 **한 사이트씩** 고쳐지므로, 가격을 읽는 새 코드를 쓸 때마다 _"이건 어느 상품인가"_ 를 되물어라. 실측 대조 1회(`category=spot` vs `category=linear` kline)면 끝난다.
- ★**시뮬 포지션과 거래소 포지션은 자동으로 수렴하지 않는다.** `run_live` 는 OHLCV 재생만 하고 거래소 포지션을 **입력으로 받지 않는다**. 진입이 라이브에서 유실되면 그 유령 포지션은 영원히 남고, 이후 close 는 전부 거절된다(`110017 current position is zero`). 방향까지 어긋나면 `reduce_only=True` 하나가 **반대 방향 포지션 증가**를 막는 유일한 방벽이다.
  - 관측 지점 = `qb_live_position_divergence_total{category}` + `qb_live_signal_divergence_total{stage="position"}`. 진단 SQL 은 [`live-close-diagnostics.md`](live-close-diagnostics.md).

## 3.5 컨텍스트 예산 — 세션이 새는 두 채널

> 2026-07-28 승격. 직전 회차가 이 규칙을 **참조는 했으나 이 파일에 없었다** — 핸드오프가 "여기 있다" 고 적었지만 실제로는 없었고, 이번에 실제로 넣는다.

- ★**서브에이전트는 파일이 아니라 상한으로 답한다.** 이 저장소의 읽기 전용 서브에이전트(`Explore`)는 **Write 도구가 없다.** "리포트를 파일에 써라" 는 지시는 실패하고 전문이 반환값으로 돌아온다(단일 최대 소모원). **반환값 줄 수 상한을 명시해라** — "30줄 이내 / 발견마다 3줄 / 코드 덤프 금지" 가 실제로 먹는다.
- ★**Monitor 는 변화 감지가 아니라 위험 신호 + 하트비트다.** 즉시 발화는 **작업을 죽이는 사건만**(세션 비활성화 · kill switch · DNS 실패). 진행 상황은 **10~15분 하트비트 1줄**. 판단 기준 = _"이 발화를 보고 내가 뭘 할 것인가?"_
- worker 로그 전문 금지 — `grep -c` / `sort | uniq -c` 집계만.
- 문서 파일은 `head`/`sed -n` 에 **`cut -c1-200`** 을 붙여라. 이 저장소 dev-log·backlog 는 행 하나가 3,000자다.
- ★**codex 산출물(`*-codex.txt`)은 tool-trace 가 수십만 줄이다.** 최종 답변만 뽑아라 — `awk '/^\[P[123]\]/{f=1} f'` 같은 패턴으로 자른다. 통째로 읽지 마라.

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
