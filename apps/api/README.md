# QuantBridge — Backend

FastAPI + SQLModel + Celery. 100% 비동기. 도메인별 3-Layer(Router / Service / Repository) 구조다.

- Python 219파일 · 53.7k LOC · 도메인 7 · 테이블 20 · 마이그레이션 45 · pytest 4,026 케이스
- 전체 제품 소개와 최초 셋업은 [루트 README](../../README.md) 참조

---

## 도메인 맵

| 디렉터리 (`src/`) | 역할                                                                              | 3-Layer | LOC   |
| ----------------- | --------------------------------------------------------------------------------- | ------- | ----- |
| `strategy/`       | Pine 전략 CRUD·파싱·버전 + `pine_v2/` 인터프리터 + `convert/`(indicator→strategy) | ✅      | 10.2k |
| `backtest/`       | 백테스트 제출·조회·공유 + `engine/`(pine_v2 결과 → 성과 지표 변환)                | ✅      | 5.4k  |
| `stress_test/`    | 몬테카를로 · 워크포워드 · 비용가정 민감도 · 파라미터 안정성                       | ✅      | 2.7k  |
| `optimizer/`      | 파라미터 최적화 — grid / bayesian / genetic                                       | ✅      | 3.1k  |
| `trading/`        | 거래소 계정 · 주문 · 포지션 · 킬스위치 · 라이브 세션 · 웹훅 · 청산                | ✅      | 15.9k |
| `waitlist/`       | 베타 대기열 신청 + admin 승인 → 초대 발송                                         | ✅      | 0.9k  |
| `auth/`           | 사용자 원장 + 탈퇴 (JWT **검증기는 여기가 아니다** — 아래 참조)                   | ✅      | 0.6k  |
| `market_data/`    | OHLCV provider(CCXT · Timescale · fixture) 공급. **공개 REST 없는 내부 전용**     | repo만  | 0.7k  |
| `realtime/`       | 인증 WebSocket + Redis pubsub fanout + **JWKS 검증기**(`auth.py`)                 | WS only | 0.5k  |
| `health/`         | `/healthz`(Postgres·Redis·Celery 3-dep ping) · `/livez`                           | —       | 0.2k  |
| `tasks/`          | Celery 앱 + 태스크 27개                                                           | —       | 9.6k  |
| `common/`         | 도메인 무지 기반 — DB 세션 · 예외 · Redis · redlock · metrics · rate limit · 알림 | —       | 2.8k  |
| `core/`           | `config.py` 하나 — 전 도메인 `Settings` (pydantic-settings)                       | —       | 0.5k  |
| `scripts/`        | 운영 entrypoint helper (`python -m src.scripts.*` — alembic 락 래퍼 등)           | —       | 0.2k  |

읽을 때 헷갈리기 쉬운 세 가지:

- **`trading/` 만 구조가 다르다** — `service.py`/`repository.py` 가 파일이 아니라 `services/`(13개) · `repositories/`(10개) 디렉터리로 분해돼 있고, `websocket/` 서브패키지를 따로 갖는다
- **JWT 검증기는 `realtime/auth.py`** 한 곳이다. `auth/` 는 사용자 원장만 갖는다 (횡단 관심사라 도메인 밖 — [ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))
- **Service 는 `src.tasks` 를 직접 import 하지 않는다** — 순환 의존을 피하려고 `dispatcher.py` Protocol 로 추상화했다 (`backtest/dispatcher.py` 참조)
- `exchange/` 는 없다 — [ADR-018](../../docs/adr/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) 로 `trading/` 에 통합됐다

---

## API 개요

health 계열을 제외한 전부가 `/api/v1` 프리픽스다. 조립 지점은 `src/main.py` 하나 (`create_app()`).

| 군                 | 대표 경로                                                                                                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| meta               | `GET /health` · `/healthz` · `/livez` · `/metrics` (Prometheus, bearer 인증)                                                                                                 |
| auth               | `GET /api/v1/auth/me` · `DELETE /api/v1/auth/me`                                                                                                                             |
| strategies         | `POST /strategies/parse` · `GET`·`POST /strategies` · `PUT /strategies/{id}/settings` · `POST /strategies/{id}/rotate-webhook-secret` · `POST /strategies/convert-indicator` |
| backtests          | `POST /backtests` (202) · `GET /backtests/{id}/trades` · `/progress` · `POST`·`DELETE /backtests/{id}/share` · `GET /backtests/share/{token}`                                |
| stress-tests       | `POST /stress-tests/{monte-carlo,walk-forward,cost-assumption-sensitivity,param-stability}`                                                                                  |
| optimizer          | `POST /optimizer/runs/{grid-search,bayesian,genetic}` · `GET /optimizer/runs[/{id}]`                                                                                         |
| trading — 웹훅     | `POST /webhooks/{strategy_id}` (TradingView 알림 수신 · rate limit 면제)                                                                                                     |
| trading — 계정     | `POST`·`GET /exchange-accounts` · `GET /exchange-accounts/{id}/balance` · `/positions`                                                                                       |
| trading — 주문     | `GET /orders` · `POST /orders/{id}/cancel` · `POST /liquidation/preview`                                                                                                     |
| trading — 킬스위치 | `GET /kill-switch/events` · `POST /kill-switch/events/{id}/resolve`                                                                                                          |
| trading — 세션     | `POST`·`GET /live-sessions` · `GET /live-sessions/{id}/state` · `POST /live-sessions/{id}/positions/close` · `GET`·`POST`·`DELETE /live-sessions/{id}/alert-rules`           |
| waitlist           | `POST /waitlist` · `GET /waitlist/invite/{token}` · `GET /admin/waitlist` · `POST /admin/waitlist/{id}/approve`                                                              |
| realtime           | `WS /api/v1/realtime/ws` — Origin 검증 + 첫 메시지 JWT 인증 (5초 타임아웃)                                                                                                   |

OpenAPI 계약(`contracts/openapi/openapi.json`)이 레포에 커밋돼 있고, `mise run openapi-check` 가 drift 를 2단(전량 + orval 부분집합)으로 검사한다.

---

## `pine_v2` 인터프리터

이 레포의 심장. `src/strategy/pine_v2/` 에 22모듈 8.3k LOC. **백테스트와 라이브 신호가 같은 코드로 돈다** ([ADR-011](../../docs/adr/011-pine-execution-strategy-v4.md)).

| 파일                  | 역할                                                                     |
| --------------------- | ------------------------------------------------------------------------ |
| `interpreter.py`      | AST 위 bar-by-bar tree-walking 인터프리터 (핵심)                         |
| `strategy_state.py`   | Pine `strategy.*` 실행 상태 — entry/close/exit · 포지션 · 에쿼티         |
| `event_loop.py`       | OHLCV DataFrame 위 봉 단위 이벤트 루프 드라이버                          |
| `stdlib.py`           | `ta.*` stateful 지표 구현 (AST node id 별 독립 상태)                     |
| `coverage.py`         | **실행 전** 미지원 builtin 전수 탐지 — all-or-nothing 판정               |
| `ast_classifier.py`   | Track S/A/M 판정 — S=`strategy()` 선언 / A=indicator+alert / M=지표 통과 |
| `virtual_strategy.py` | Track A 가상 strategy 래퍼 — indicator + alertcondition 을 자동매매로    |
| `parser_adapter.py`   | ★pynescript 호출의 **유일한 지점**                                       |

**지원 범위** — `ta.*` 23종(sma·ema·rma·atr·rsi·crossover·bb·sar·hma·obv 등) · `array.*` 16종 · utility 3종(`na`/`nz`/`fixnan`) · plot 19 · input 12 · math 14 · string 6. 허용 집합의 SSOT 는 `_names.py` + `coverage.py` 다.

★**라이선스 경계가 설계 제약이다.** 파서인 pynescript 는 LGPL-3.0 이라 **PyPI 의존성으로만** 쓰고 소스를 복사하지 않는다. `import pynescript` 는 `parser_adapter.py` 한 파일에서만 허용된다 — 다른 파일에 쓰지 마라.

★**`exec()` / `eval()` 절대 금지** ([ADR-003](../../docs/adr/003-pine-runtime-safety-and-parser-scope.md)).

---

## 기술 스택

| 영역              | 기술 / 버전                                                          |
| ----------------- | -------------------------------------------------------------------- |
| 언어              | Python `>=3.12,<3.13` (상한은 의도적 — 없으면 uv 가 3.13 을 고른다)  |
| 프레임워크        | FastAPI `>=0.115` · uvicorn `>=0.32` (100% async)                    |
| ORM               | SQLModel `>=0.0.22` + SQLAlchemy `2.0` (asyncpg)                     |
| 검증 · 설정       | Pydantic `v2` · pydantic-settings                                    |
| DB · 마이그레이션 | PostgreSQL 15 + TimescaleDB `2.14` · Alembic `>=1.13`                |
| 비동기 작업       | Celery `>=5.4` + Redis `>=5.1`                                       |
| Pine              | pynescript `==0.3.0` (핀 고정 · LGPL)                                |
| 수치              | pandas `>=2.2` · NumPy `>=1.26` · scikit-optimize (Bayesian)         |
| 거래소            | CCXT `>=4` · websockets                                              |
| 보안              | PyJWT[crypto] (EdDSA/JWKS) · cryptography (Fernet AES-256) · slowapi |
| 관측              | prometheus-client (multiproc)                                        |
| 테스트 · 품질     | pytest `>=8.3` (+asyncio·cov·timeout) · fakeredis · Ruff · mypy      |

---

## 시작하기

```bash
uv sync
cp .env.example .env.local      # backend 전용 env (pydantic-settings 자동 로드)
uv run uvicorn src.main:app --no-server-header --reload --host 0.0.0.0 --port 8000
```

> 루트에서 `mise run be` 로도 같은 서버가 뜬다. 인프라(Postgres·Redis·워커)까지 한 번에 띄우려면 `mise run dev`.

### 개발 도구

```bash
uv run ruff check .        # 린트
uv run ruff format .       # 포맷
uv run mypy src            # 타입 체크
uv run pytest              # 테스트 (아래 환경 주의 참조)
```

---

## 비동기 작업 (Celery)

태스크 27개 · beat 스케줄 15건 · 큐 3종(`default` / `ws_stream` / `optimizer_heavy`).

| 군             | 태스크                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 장기 작업 실행 | `backtest.run` · `optimizer.run` · `stress_test.run` (+ 각 `reclaim_stale`)                                                           |
| 트레이딩 집행  | `trading.execute_order` · `fetch_order_status` · `cancel_order` · `place_trailing_stop` · `refresh_closed_pnl`                        |
| 트레이딩 복구  | `trading.scan_stuck_orders`(30분+ 멈춘 주문 자동 reconcile) · `live_signal.recover_breached_entry` · `janitor_conditional_entries`    |
| 라이브 시그널  | `live_signal.evaluate_all`(60초) · `dispatch_event`(transactional outbox) · `dispatch_pending`                                        |
| 수집 · 리포트  | `trading.fetch_funding_rates` · `trading.run_bybit_{private,public}_stream` · `alert_rules.evaluate_loss` · `reporting.dogfood_daily` |

★**모든 태스크 진입점은 `asyncio.run()` 대신 `run_in_worker_loop()` 를 쓴다.** prefork 워커에서 asyncpg 커넥션이 죽은 이벤트 루프에 묶여 2번째 태스크부터 조용히 실패하는 문제 때문이다. 상세 규약은 [`AGENTS.md`](AGENTS.md) §9.

---

## 데이터베이스 & 마이그레이션

- 테이블 20개 (`users` · `strategies` · `backtests` · `orders` · `live_signal_sessions` · `kill_switch_events` 등) + Better Auth 5테이블
- OHLCV 는 **TimescaleDB hypertable** `ts.ohlcv` (7일 chunk). 일반 테이블에 시계열을 넣지 않는다

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

> ★**`downgrade` 는 `-x allow_destructive=1` 없이 죽는다.** `alembic/env.py` 가 downgrade 만 골라 막는다 — 2026-07-25 에 이 경로로 로컬 개발 DB 가 전소한 뒤 세운 가드다. 되돌리기 전에 먼저 `mise run db-snapshot`.

```bash
uv run alembic -x allow_destructive=1 downgrade -1
```

`models.py` 를 바꾸면 **반드시** 마이그레이션을 생성해 같은 커밋에 넣는다. 컬럼 삭제는 2단계 배포(코드에서 사용 중단 → 다음 배포에서 삭제).

---

## 테스트

`test_*.py` 488파일 / `def test_*` 4,026개.

| 디렉터리                  | 파일 수                                                                                            |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| `tests/trading/`          | 116 (+ websocket 8)                                                                                |
| `tests/strategy/pine_v2/` | 87                                                                                                 |
| `tests/tasks/`            | 52                                                                                                 |
| `tests/backtest/`         | 47 (+ engine 13)                                                                                   |
| `tests/stress_test/`      | 23 (+ engine 16)                                                                                   |
| 그 외                     | common 21 · strategy 16 · optimizer 14 · scripts 12 · api 11 · auth 7 · market_data 7 · waitlist 6 |

마커 3종 — `mutation`(nightly) · `real_broker`(`--run-real-broker`, Bybit Demo 자격증명 필요) · `integration`(`--run-integration`, 실제 DB/Redis).

### ★ 환경 주의 — 가장 값비싼 함정

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest
```

**`.env.local` 을 통째로 소싱해라.** `DATABASE_URL` 만 단독으로 주입하면 세션 픽스처의 `drop_all` 이 **개발 DB 를 겨냥한다.** 서브에이전트·스크립트에서도 마찬가지다. 상세는 [`gates-and-traps.md`](../../docs/development/gates-and-traps.md) §환경.

또 하나 — **판정 명령에 파이프를 붙이지 마라.** `uv run pytest ... | tail -3` 은 pytest 가 아니라 `tail` 의 종료 코드를 읽어서, 실패한 테스트를 초록으로 보고한다.

---

## 핵심 규칙

- **AsyncSession 은 Repository 만 보유한다.** Service 는 Repository 를 주입받고 트랜잭션 경계만 담당
- **commit 은 Service 가 명시적으로.** mutation 메서드마다 `repo.commit()` 호출을 검증하는 spy 테스트가 의무다 (누락은 request 종료 시 조용히 ROLLBACK 된다)
- **`.dict()` 금지** → `.model_dump()`. **`session.exec()` 금지** → `await session.execute(...)`
- **금융 숫자는 `Decimal`.** float 금지, 합산도 Decimal 공간에서
- **거래소 API Key 는 Fernet 암호화 저장.** 평문 컬럼 금지
- **백테스트·최적화는 반드시 Celery.** API 핸들러에서 직접 실행 금지

전체 규칙은 [`AGENTS.md`](AGENTS.md) 가 정본이다.
