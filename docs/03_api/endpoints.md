# QuantBridge — API 엔드포인트 스펙

> **아키텍처:** 3-Layer (Router/Service/Repository) — `.ai/rules/backend.md` 참조
> **인증:** Clerk JWT 검증 (자체 토큰 발급 없음)
> **비동기 작업:** Celery (백테스트, 최적화, 스트레스테스트) → 202 Accepted + backtest_id
> **SSOT:** 각 도메인 `backend/src/<domain>/router.py` + 머신 계약은 FastAPI 자동 OpenAPI (`/openapi.json`, dev `/docs`·`/redoc`; prod `_hide_docs`). 본 문서와 코드 충돌 시 코드 우선 — 본 문서는 navigational overview.
> **갱신:** 2026-05-29 audit reconcile (Optimizer/Stress 경로·라이브러리 교정). 일부 섹션은 여전히 Sprint 6 스냅샷일 수 있음 — 정확한 계약은 OpenAPI/router 참조.

### 구현 상태 범례

- ✅ — 구현 + `main.py` 등록됨
- ⏳ — 라우터 스캐폴딩만 존재 (`main.py` 미등록)

---

## 인증 (Auth) — Clerk 기반

> 회원가입/로그인/토큰 갱신은 Clerk가 처리. Backend는 토큰 검증만 수행.

| Method | Path                   | 설명                                           | Auth      | 상태        |
| ------ | ---------------------- | ---------------------------------------------- | --------- | ----------- |
| `GET`  | `/api/v1/auth/me`      | Clerk 토큰 검증 → 현재 사용자 정보             | Required  | ✅ Sprint 3 |
| `POST` | `/api/v1/auth/webhook` | Clerk Webhook → 사용자 생성/업데이트 DB 동기화 | Svix 서명 | ✅ Sprint 3 |

**Webhook 이벤트:**

- `user.created` → users 테이블에 INSERT
- `user.updated` → users 테이블 UPDATE (email, username)
- `user.deleted` → users 테이블 soft delete (is_active = false)

---

## 전략 (Strategies)

| Method   | Path                            | 설명                                | Auth     | 도메인   | 상태          |
| -------- | ------------------------------- | ----------------------------------- | -------- | -------- | ------------- |
| `GET`    | `/api/v1/strategies`            | 내 전략 목록                        | Required | strategy | ✅ Sprint 3   |
| `POST`   | `/api/v1/strategies`            | 새 전략 생성 (Pine Script 업로드)   | Required | strategy | ✅ Sprint 3   |
| `GET`    | `/api/v1/strategies/:id`        | 전략 상세 조회                      | Required | strategy | ✅ Sprint 3   |
| `PUT`    | `/api/v1/strategies/:id`        | 전략 수정                           | Required | strategy | ✅ Sprint 3   |
| `DELETE` | `/api/v1/strategies/:id`        | 전략 삭제 (FK backtest 참조 시 409) | Required | strategy | ✅ Sprint 3/4 |
| `POST`   | `/api/v1/strategies/parse`      | Pine Script 파싱만 수행 (미리보기)  | Required | strategy | ✅ Sprint 3   |
| `POST`   | `/api/v1/strategies/import-url` | TradingView URL로 가져오기          | Required | strategy | ⏳ Sprint 5+  |

**목록 쿼리 파라미터 (`GET /strategies`):**

| 파라미터       | 타입        | 기본값 | 설명                                                                                                                  |
| -------------- | ----------- | ------ | --------------------------------------------------------------------------------------------------------------------- |
| `limit`        | int (1~100) | 20     | 페이지당 항목 수                                                                                                      |
| `offset`       | int (≥0)    | 0      | skip 개수                                                                                                             |
| `page`         | int (≥1)    | _none_ | **Deprecated** (Sprint 5 M4). 들어오면 `(page-1)*limit`로 `offset` 환산. (Sprint 62 기준 fallback 유지 — 아직 미제거) |
| `parse_status` | ParseStatus | null   | 필터: `ok` / `unsupported` / `error`                                                                                  |
| `is_archived`  | bool        | false  | true 시 archive된 전략만                                                                                              |

> ✅ 페이지네이션 drift 해소 (Sprint 5 M4 T32): Strategy / Backtest 모두 `limit/offset` 표준. `page`는 호환 fallback만 유지.

---

## 백테스트 (Backtests)

> 백테스트 실행은 Celery 비동기. POST 시 `202 Accepted` + `backtest_id` 반환.

| Method   | Path                             | 설명                                            | Auth     | 비동기                 |
| -------- | -------------------------------- | ----------------------------------------------- | -------- | ---------------------- |
| `POST`   | `/api/v1/backtests`              | 백테스트 실행 요청                              | Required | **202 + backtest_id**  |
| `GET`    | `/api/v1/backtests`              | 내 백테스트 목록 (`?limit=20&offset=0`)         | Required | -                      |
| `GET`    | `/api/v1/backtests/:id`          | 백테스트 결과 조회                              | Required | -                      |
| `GET`    | `/api/v1/backtests/:id/trades`   | 개별 거래 내역 (`?limit=100&offset=0`, max 500) | Required | -                      |
| `GET`    | `/api/v1/backtests/:id/progress` | 진행률 + `stale` flag (polling용)               | Required | -                      |
| `POST`   | `/api/v1/backtests/:id/cancel`   | 실행 중 백테스트 취소 (best-effort)             | Required | **202 + `cancelling`** |
| `DELETE` | `/api/v1/backtests/:id`          | 백테스트 결과 삭제 (terminal only)              | Required | **204**                |

---

## 스트레스 테스트 (Stress Tests) — ✅ Sprint 50-52 구현

> 코드 prefix: `/stress-tests` (**복수**). 모두 Celery 비동기 (202 + stress_test_id).

| Method | Path                                               | 설명                                 | Auth     | 비동기  |
| ------ | -------------------------------------------------- | ------------------------------------ | -------- | ------- |
| `POST` | `/api/v1/stress-tests/monte-carlo`                 | Monte Carlo (equity-curve bootstrap) | Required | **202** |
| `POST` | `/api/v1/stress-tests/walk-forward`                | Walk-Forward 분석                    | Required | **202** |
| `POST` | `/api/v1/stress-tests/cost-assumption-sensitivity` | 비용 가정 민감도                     | Required | **202** |
| `POST` | `/api/v1/stress-tests/param-stability`             | 파라미터 안정성 (grid sweep)         | Required | **202** |
| `GET`  | `/api/v1/stress-tests`                             | 내 stress test 목록 (paginated)      | Required | -       |
| `GET`  | `/api/v1/stress-tests/:id`                         | 결과 조회                            | Required | -       |

---

## 최적화 (Optimization) — ✅ Sprint 54-57 구현 (ADR-013)

> 코드 prefix: `/optimizer`. Celery 비동기 (202 + run_id). 라이브러리: **scikit-optimize** (Bayesian), 자체구현 GA (Genetic). Optuna 아님.

| Method | Path                                 | 설명                                 | Auth     | 비동기  |
| ------ | ------------------------------------ | ------------------------------------ | -------- | ------- |
| `POST` | `/api/v1/optimizer/runs/grid-search` | 그리드 서치                          | Required | **202** |
| `POST` | `/api/v1/optimizer/runs/bayesian`    | 베이지안 최적화 (scikit-optimize)    | Required | **202** |
| `POST` | `/api/v1/optimizer/runs/genetic`     | 유전 알고리즘 (self-impl)            | Required | **202** |
| `GET`  | `/api/v1/optimizer/runs/:id`         | 결과 조회                            | Required | -       |
| `GET`  | `/api/v1/optimizer/runs`             | 내 optimization run 목록 (paginated) | Required | -       |

---

## Trading (Sprint 6) — ✅ 구현 완료

> Sprint 6 Trading 데모 MVP. Exchange Account + Webhook + Order + Kill Switch.
> API Key는 AES-256-GCM 암호화 저장 (EncryptionService). 평문 반환 금지.
>
> **라이브 손익보호 (Wave 1/2/3 + STEP B):** `/orders` 응답이 exit 프리미티브(`take_profit`/`stop_loss`/`trailing_stop` 등) 운반. **TP/SL bracket** 은 entry 주문에 거래소-네이티브로 부착(maker-TP Partial). **트레일링** 은 신규 public 엔드포인트 없음 — 체결 후 내부 Celery follow-on(`trading.place_trailing_stop`)이 `set_trading_stop`(Bybit trading-stop 엔드포인트)으로 포지션에 부착(상세 [`dev-log/2026-06-26-trailing-live-placement.md`](../dev-log/2026-06-26-trailing-live-placement.md)).

| Method   | Path                                            | 설명                                                                                                                                                 | 인증        |
| -------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `POST`   | `/api/v1/exchange-accounts`                     | 계정 등록 (AES-256 암호화 저장)                                                                                                                      | Clerk JWT   |
| `GET`    | `/api/v1/exchange-accounts`                     | 본인 계정 목록 (masked API key)                                                                                                                      | Clerk JWT   |
| `DELETE` | `/api/v1/exchange-accounts/{id}`                | 계정 삭제                                                                                                                                            | Clerk JWT   |
| `POST`   | `/api/v1/webhooks/{strategy_id}?token=<hmac>`   | TV Alert 수신, Idempotency-Key header                                                                                                                | HMAC-SHA256 |
| `GET`    | `/api/v1/orders?limit&offset`                   | 본인 주문 목록                                                                                                                                       | Clerk JWT   |
| `GET`    | `/api/v1/orders/{id}`                           | 주문 상세                                                                                                                                            | Clerk JWT   |
| `POST`   | `/api/v1/orders/{id}/cancel`                    | 주문 취소 — pending: 즉시 DB cancel (200); submitted(거래소 live): `cancel_order_task` 위임 **202** (거래소 취소 성공 시에만 cancelled, CF4/PR #305) | Clerk JWT   |
| `GET`    | `/api/v1/kill-switch/events?limit&offset`       | Kill Switch 이벤트 감사                                                                                                                              | Clerk JWT   |
| `POST`   | `/api/v1/kill-switch/events/{id}/resolve`       | Kill Switch 수동 해제                                                                                                                                | Clerk JWT   |
| `POST`   | `/api/v1/strategies/{id}/rotate-webhook-secret` | Webhook secret rotate                                                                                                                                | Clerk JWT   |

---

## 거래소 계정 (Exchange Accounts) — ⏳ Sprint 7+ (확장)

> Sprint 6에서 기본 CRUD 구현 완료. Sprint 7+에서 test/balance 등 확장.

| Method | Path                                    | 설명                    | Auth     |
| ------ | --------------------------------------- | ----------------------- | -------- |
| `POST` | `/api/v1/exchange/accounts/:id/test`    | API Key 유효성 테스트   | Required |
| `GET`  | `/api/v1/exchange/accounts/:id/balance` | 잔고 조회 (데모/라이브) | Required |

---

## 트레이딩 세션 — ⚠ 경로 변경됨: 실제는 `/live-sessions` (Sprint 26 자동매매)

> **2026-05-29:** 아래 `/trading/sessions/*` 는 **원래 계획(미구현)**. 실제 구현된 자동매매 세션은 `/api/v1/live-sessions` (LiveSignalSession) — `POST/GET/DELETE /live-sessions`, `GET /live-sessions/:id/state`, `GET /live-sessions/:id/events`. start/stop 분리 없이 register/deactivate(=DELETE) 모델. Kill Switch 는 `/kill-switch/events/*` (별도).

| Method | Path                                       | 설명                             | Auth     |
| ------ | ------------------------------------------ | -------------------------------- | -------- |
| `POST` | `/api/v1/trading/sessions`                 | 세션 생성                        | Required |
| `GET`  | `/api/v1/trading/sessions`                 | 내 세션 목록                     | Required |
| `GET`  | `/api/v1/trading/sessions/:id`             | 세션 상세                        | Required |
| `POST` | `/api/v1/trading/sessions/:id/start`       | 트레이딩 시작                    | Required |
| `POST` | `/api/v1/trading/sessions/:id/stop`        | 트레이딩 중지                    | Required |
| `POST` | `/api/v1/trading/sessions/:id/kill`        | **Kill Switch** (긴급 전체 청산) | Required |
| `GET`  | `/api/v1/trading/sessions/:id/trades`      | 세션 거래 내역                   | Required |
| `GET`  | `/api/v1/trading/sessions/:id/performance` | 성과 요약                        | Required |
| `GET`  | `/api/v1/trading/sessions/:id/comparison`  | 백테스트 vs 실제 비교            | Required |

---

## 시장 데이터 (Market Data) — 내부 전용 (공개 REST endpoint 없음, 0 routes)

> **2026-05-29:** 아래 경로는 **미구현** — `market_data/router.py` 에 라우트 0개. OHLCV 는 backtest 엔진이 `TimescaleProvider` 로 내부 호출(CCXT fallback fetch + TimescaleDB 적재). 공개 API 필요 시 신규 구현.

> 코드 prefix: `/market-data`.

| Method | Path                                | 설명                              | Auth     |
| ------ | ----------------------------------- | --------------------------------- | -------- |
| `GET`  | `/api/v1/market-data/symbols`       | 지원 심볼 목록 (거래소별)         | Required |
| `GET`  | `/api/v1/market-data/ohlcv`         | OHLCV 데이터 조회                 | Required |
| `POST` | `/api/v1/market-data/sync`          | OHLCV 동기화 트리거 (Celery, 202) | Required |
| `GET`  | `/api/v1/market-data/funding-rates` | 펀딩비 데이터 조회                | Required |

---

## 전략 템플릿 (Templates) — ⏳ 미구현 (phantom — 라우트 0개)

| Method | Path                        | 설명                  | Auth     |
| ------ | --------------------------- | --------------------- | -------- |
| `GET`  | `/api/v1/templates`         | 템플릿 목록           | Required |
| `GET`  | `/api/v1/templates/:id`     | 템플릿 상세           | Required |
| `POST` | `/api/v1/templates/:id/use` | 템플릿 → 내 전략 생성 | Required |

---

## WebSocket 이벤트 — ⏳ 미구현 (설계 명세만; 클라이언트 WS 엔드포인트 없음)

> **2026-05-29:** 아래 `ws://api/ws` 프로토콜은 **계획 명세** — 서버에 client-facing WebSocket route 가 없다 (`@app.websocket` 0개). 현재 백테스트 진행률은 **HTTP 폴링** (`GET /backtests/:id/progress`). `tasks/websocket_task.py` 는 거래소 데이터 ingest 용(`ws_stream` queue)으로, 본 client 프로토콜과 무관.
>
> 연결 시 (계획) Clerk JWT 토큰을 query parameter 또는 첫 메시지로 전달

```
ws://api/ws?token={clerk_jwt}

# 클라이언트 → 서버 (구독)
subscribe_backtest_progress(backtest_id)
subscribe_trading_session(session_id)
subscribe_market_data(exchange, symbol, timeframe)

# 서버 → 클라이언트 (이벤트)
backtest_progress(backtest_id, progress, status)
backtest_completed(backtest_id, results_summary)
trade_opened(session_id, trade_data)
trade_closed(session_id, trade_data)
position_update(session_id, position_data)
pnl_update(session_id, pnl_data)
risk_alert(session_id, alert_type, message)
kill_switch_triggered(session_id, reason)
```

---

## 3-Layer 구조 매핑

각 도메인은 아래 구조를 따릅니다 (`.ai/rules/backend.md` 참조):

```
backend/src/{domain}/
├── router.py        # HTTP만 — Pydantic 검증 → service 호출. 10줄 이내. DB 접근 금지
├── service.py       # 비즈니스 로직 — AsyncSession 금지. Repository 호출
├── repository.py    # DB 쿼리만 — 유일한 AsyncSession 사용처
├── schemas.py       # Pydantic V2 요청/응답 스키마
├── models.py        # SQLModel 모델
└── dependencies.py  # Depends() 조립 (session, service, repo 주입)
```

**Cross-domain 트랜잭션:** 동일 AsyncSession을 여러 Repository에 공유하여 Service에서 하나의 commit으로 처리.
