# QuantBridge — API 엔드포인트 스펙

> **아키텍처:** 3-Layer (Router/Service/Repository) — `.ai/rules/backend.md` 참조
> **인증:** Clerk JWT 검증 (자체 토큰 발급 없음)
> **비동기 작업:** Celery (백테스트, 최적화, 스트레스테스트) → 202 Accepted + task_id

---

## 인증 (Auth) — Clerk 기반

> 회원가입/로그인/토큰 갱신은 Clerk가 처리. Backend는 토큰 검증만 수행.

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/api/v1/auth/me` | Clerk 토큰 검증 → 현재 사용자 정보 | Required |
| `POST` | `/api/v1/auth/webhook` | Clerk Webhook → 사용자 생성/업데이트 DB 동기화 | Svix 서명 |

**Webhook 이벤트:**
- `user.created` → users 테이블에 INSERT
- `user.updated` → users 테이블 UPDATE (email, username)
- `user.deleted` → users 테이블 soft delete (is_active = false)

---

## 전략 (Strategies)

| Method | Path | 설명 | Auth | 도메인 |
|--------|------|------|------|--------|
| `GET` | `/api/v1/strategies` | 내 전략 목록 (페이지네이션) | Required | strategy |
| `POST` | `/api/v1/strategies` | 새 전략 생성 (Pine Script 업로드) | Required | strategy |
| `GET` | `/api/v1/strategies/:id` | 전략 상세 조회 | Required | strategy |
| `PUT` | `/api/v1/strategies/:id` | 전략 수정 | Required | strategy |
| `DELETE` | `/api/v1/strategies/:id` | 전략 삭제 | Required | strategy |
| `POST` | `/api/v1/strategies/parse` | Pine Script 파싱만 수행 (미리보기) | Required | strategy |
| `POST` | `/api/v1/strategies/import-url` | TradingView URL로 가져오기 | Required | strategy |

---

## 백테스트 (Backtests)

> 백테스트 실행은 Celery 비동기. POST 시 `202 Accepted` + `backtest_id` 반환.

| Method | Path | 설명 | Auth | 비동기 |
|--------|------|------|------|--------|
| `POST` | `/api/v1/backtests` | 백테스트 실행 요청 | Required | **202 + task_id** |
| `GET` | `/api/v1/backtests` | 내 백테스트 목록 | Required | - |
| `GET` | `/api/v1/backtests/:id` | 백테스트 결과 조회 | Required | - |
| `GET` | `/api/v1/backtests/:id/trades` | 개별 거래 내역 (페이지네이션) | Required | - |
| `GET` | `/api/v1/backtests/:id/progress` | 진행률 (polling용, WS 대안) | Required | - |
| `DELETE` | `/api/v1/backtests/:id` | 백테스트 결과 삭제 | Required | - |

---

## 스트레스 테스트 (Stress Tests)

> 모두 Celery 비동기. `202 Accepted` + `stress_test_id` 반환.

| Method | Path | 설명 | Auth | 비동기 |
|--------|------|------|------|--------|
| `POST` | `/api/v1/stress-tests/monte-carlo` | Monte Carlo 시뮬레이션 | Required | **202** |
| `POST` | `/api/v1/stress-tests/walk-forward` | Walk-Forward 분석 | Required | **202** |
| `POST` | `/api/v1/stress-tests/parameter-stability` | 파라미터 안정성 분석 | Required | **202** |
| `GET` | `/api/v1/stress-tests/:id` | 결과 조회 | Required | - |

---

## 최적화 (Optimization)

> Celery 비동기. `202 Accepted`.

| Method | Path | 설명 | Auth | 비동기 |
|--------|------|------|------|--------|
| `POST` | `/api/v1/optimize/grid` | 그리드 서치 | Required | **202** |
| `POST` | `/api/v1/optimize/bayesian` | 베이지안 최적화 (Optuna) | Required | **202** |
| `GET` | `/api/v1/optimize/:id` | 결과 조회 | Required | - |

---

## 거래소 계정 (Exchange Accounts)

> API Key는 AES-256 암호화 저장. 평문 반환 금지.

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/api/v1/exchanges/accounts` | 등록된 거래소 계정 목록 | Required |
| `POST` | `/api/v1/exchanges/accounts` | API Key 등록 (암호화 저장) | Required |
| `DELETE` | `/api/v1/exchanges/accounts/:id` | 계정 삭제 | Required |
| `POST` | `/api/v1/exchanges/accounts/:id/test` | API Key 유효성 테스트 | Required |
| `GET` | `/api/v1/exchanges/accounts/:id/balance` | 잔고 조회 (데모/라이브) | Required |

---

## 트레이딩 (Trading Sessions)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `POST` | `/api/v1/trading/sessions` | 세션 생성 | Required |
| `GET` | `/api/v1/trading/sessions` | 내 세션 목록 | Required |
| `GET` | `/api/v1/trading/sessions/:id` | 세션 상세 | Required |
| `POST` | `/api/v1/trading/sessions/:id/start` | 트레이딩 시작 | Required |
| `POST` | `/api/v1/trading/sessions/:id/stop` | 트레이딩 중지 | Required |
| `POST` | `/api/v1/trading/sessions/:id/kill` | **Kill Switch** (긴급 전체 청산) | Required |
| `GET` | `/api/v1/trading/sessions/:id/trades` | 세션 거래 내역 | Required |
| `GET` | `/api/v1/trading/sessions/:id/performance` | 성과 요약 | Required |
| `GET` | `/api/v1/trading/sessions/:id/comparison` | 백테스트 vs 실제 비교 | Required |

---

## 시장 데이터 (Market Data)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/api/v1/market/symbols` | 지원 심볼 목록 (거래소별) | Required |
| `GET` | `/api/v1/market/ohlcv` | OHLCV 데이터 조회 | Required |
| `GET` | `/api/v1/market/funding-rates` | 펀딩비 데이터 조회 | Required |

---

## 전략 템플릿 (Templates)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/api/v1/templates` | 템플릿 목록 | Required |
| `GET` | `/api/v1/templates/:id` | 템플릿 상세 | Required |
| `POST` | `/api/v1/templates/:id/use` | 템플릿 → 내 전략 생성 | Required |

---

## WebSocket 이벤트

> 연결 시 Clerk JWT 토큰을 query parameter 또는 첫 메시지로 전달

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
