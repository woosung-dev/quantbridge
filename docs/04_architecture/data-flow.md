# QuantBridge — 데이터 흐름

> **목적:** 도메인별 주요 시퀀스 다이어그램.
> **상위 문서:** [`system-architecture.md`](./system-architecture.md), 도메인 경계는 [`02_domain/domain-overview.md`](../02_domain/domain-overview.md).

---

## 1. Strategy CRUD (Sprint 3)

```mermaid
sequenceDiagram
    actor User
    participant FE as Next.js (FE)
    participant API as FastAPI Router
    participant SVC as StrategyService
    participant Parser as Pine Parser
    participant Repo as StrategyRepository
    participant DB

    User->>FE: Pine 코드 입력
    FE->>API: POST /strategies/parse {raw_source}
    API->>SVC: parse_preview(raw_source)
    SVC->>Parser: parse(raw_source)
    Parser-->>SVC: ParseOutcome (status, unsupported_calls, parsed_result)
    SVC-->>FE: 200 { parse_status, ... }

    User->>FE: 저장 클릭
    FE->>API: POST /strategies {name, raw_source, ...}
    API->>SVC: create(user_id, data)
    SVC->>Parser: parse(raw_source)
    Parser-->>SVC: ParseOutcome
    SVC->>Repo: save(Strategy(...))
    Repo->>DB: INSERT
    Repo-->>SVC: Strategy
    SVC->>Repo: commit()
    SVC-->>FE: 201 + Strategy
```

### 주요 가드

- 미지원 함수 1개 이상 → `parse_status=UNSUPPORTED` 저장 (저장 자체는 허용, 백테스트 시 거부)
- `name` 중복 시 unique 제약 위반 → 409

---

## 2. Backtest 비동기 실행 (Sprint 4)

```mermaid
sequenceDiagram
    actor User
    participant FE
    participant Router as backtest/router
    participant SVC as BacktestService
    participant Repo as BacktestRepository
    participant DB
    participant Disp as TaskDispatcher
    participant Redis
    participant W as Celery Worker
    participant Engine as vectorbt engine
    participant OHLCV as OHLCVProvider

    User->>FE: 백테스트 설정 + 제출
    FE->>Router: POST /backtests {strategy_id, symbol, period, ...}
    Router->>SVC: submit(user_id, data)
    SVC->>Repo: create(Backtest(status=QUEUED))
    Repo->>DB: INSERT
    SVC->>Repo: commit()
    SVC->>Disp: dispatch(backtest_id)
    Disp->>Redis: enqueue task
    SVC-->>FE: 202 + {backtest_id}

    Note over W,Engine: 워커 비동기 실행
    W->>Redis: consume
    W->>Repo: get(backtest_id) [Guard #1]
    alt cancellation_requested → finalize_cancelled
    end
    W->>Repo: update(status=RUNNING) [조건부]
    W->>OHLCV: load(symbol, timeframe, period)
    OHLCV-->>W: DataFrame
    W->>Repo: get(backtest_id) [Guard #2]
    alt cancellation_requested → finalize_cancelled
    end
    W->>Engine: run_backtest(strategy_python, ohlcv, params)
    Engine-->>W: BacktestResult (metrics, equity_curve, trades)
    W->>Repo: get(backtest_id) [Guard #3]
    alt cancellation_requested → discard + finalize_cancelled
    end
    W->>Repo: complete(metrics, equity_curve)\n+ insert_trades_bulk(trades)\n[단일 트랜잭션]
    Repo->>DB: UPDATE + INSERT
    W->>Repo: commit()

    User->>FE: 진행 상태 확인 (polling)
    FE->>Router: GET /backtests/:id/progress
    Router->>SVC: get_progress(user_id, backtest_id)
    SVC->>Repo: get(backtest_id)
    SVC-->>FE: 200 {status, progress, ...}
```

### 주요 가드/규칙

- 워커는 `_execute()` 진입 시 `if bt is None: logger.error + return` (assert 금지)
- 조건부 UPDATE rows=0 → `finalize_cancelled` fallback 호출
- 완료 + trades insert는 단일 트랜잭션 (atomicity)
- prefork-safe: SQLAlchemy engine은 lazy init (모듈 import 시점 호출 금지)

---

## 3. Cancel Race (3-Guard Pattern)

```mermaid
sequenceDiagram
    actor User
    participant FE
    participant Router
    participant SVC as BacktestService
    participant Repo
    participant DB
    participant W as Celery Worker

    User->>FE: 취소 클릭
    FE->>Router: POST /backtests/:id/cancel
    Router->>SVC: cancel(user_id, backtest_id)
    SVC->>Repo: get(backtest_id)
    alt status terminal (COMPLETED/FAILED/CANCELLED)
        SVC-->>Router: 409 backtest.cancellation_already_terminal
    else
        SVC->>Repo: update(status=CANCELLING, cancellation_requested_at=now)
        Repo->>DB: UPDATE
        SVC->>Repo: commit()
        SVC-->>FE: 202 {cancellation_requested: true}
    end

    Note over W: 워커가 다음 guard 도달 시 처리
    alt Guard #1 (pickup 직전)
        W->>Repo: 조건부 UPDATE WHERE status='cancelling'
        W->>Repo: finalize_cancelled (status=CANCELLED)
    else Guard #2 (pre-engine)
        W->>W: engine 호출 직전 체크
        W->>Repo: finalize_cancelled
    else Guard #3 (post-engine)
        W->>W: 결과 폐기
        W->>Repo: finalize_cancelled
    else 조건부 UPDATE rows=0
        W->>Repo: finalize_cancelled fallback (logger.error 후 강제 CANCELLED)
    end
```

> Sprint 4 §5.1 패턴. transient `CANCELLING` + 3 guard 위치 + fallback finalize.

---

## 4. Stale Reclaim (Worker Crash 복구)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat (Sprint 5+)
    participant W as Celery Worker (startup)
    participant Repo
    participant DB

    Note over W: 워커 시작 시
    W->>Repo: reclaim_stale_running()
    Repo->>DB: SELECT WHERE status IN ('running', 'cancelling')\nAND COALESCE(started_at, created_at) < now - threshold
    DB-->>Repo: stale rows
    Repo->>DB: UPDATE status='failed', error_reason='stale_reclaimed'
    Repo->>Repo: commit()

    Note over Beat: Sprint 5+ 주기 실행 (5분)
    Beat->>Repo: reclaim_stale_running() 동일 호출
```

### 규칙 (Sprint 4 D9)

- `running` + `cancelling` 양쪽 모두 reclaim 대상
- `cancelling` 케이스: `started_at NULL` (QUEUED→CANCELLING) → `created_at` fallback
- 현재: startup hook only. Sprint 5에서 beat 추가.
- 멀티 워커 split-brain 방어 (Sprint 5+ #13): `inspect().active()` 또는 Redis lock

---

## 5. Clerk Auth + Webhook (Sprint 3)

```mermaid
sequenceDiagram
    actor User
    participant FE
    participant Clerk
    participant API as FastAPI

    User->>FE: 로그인 폼
    FE->>Clerk: 인증
    Clerk-->>FE: 세션 + JWT

    FE->>API: GET /auth/me\nAuthorization: Bearer <JWT>
    API->>Clerk: JWKS 가져오기 (캐시)
    Clerk-->>API: 공개키
    API->>API: JWT 검증 (signature, exp, iss)
    API->>API: user_id 추출
    API-->>FE: 200 + user payload

    Note over Clerk,API: lifecycle 동기화 (Webhook)
    User->>Clerk: 회원가입 / 정보 변경 / 탈퇴
    Clerk->>API: POST /webhooks/clerk\n(Svix 서명 + timestamp)
    API->>API: Svix 서명 검증 (replay 방지)
    alt event = user.created
        API->>API: User INSERT
    else event = user.updated
        API->>API: User UPDATE
    else event = user.deleted
        API->>API: User DELETE (CASCADE → strategies/backtests/...)
    end
    API-->>Clerk: 200 OK
```

---

## 6. CCXT OHLCV 동기화 (Sprint 5 예정)

```mermaid
sequenceDiagram
    actor User
    participant FE
    participant Router as market_data/router
    participant SVC as MarketDataService
    participant Disp as TaskDispatcher
    participant Redis
    participant W as Celery Worker
    participant CCXT as ccxt.async_support
    participant Repo as MarketDataRepository
    participant TS as TimescaleDB hypertable

    User->>FE: 심볼·타임프레임·기간 입력
    FE->>Router: POST /market-data/sync {exchange, symbol, timeframe, start, end}
    Router->>SVC: enqueue_sync(user_id, data)
    SVC->>Disp: dispatch(sync_task_id)
    Disp->>Redis: enqueue
    SVC-->>FE: 202 + {task_id}

    W->>Redis: consume
    loop until end
        W->>CCXT: fetch_ohlcv(symbol, timeframe, since, limit=1000)
        CCXT-->>W: candles[]
        W->>Repo: upsert_bulk(candles)
        Repo->>TS: INSERT ... ON CONFLICT DO UPDATE
        alt rate limit
            W->>W: backoff sleep
        end
    end

    Note over W,Repo: 완료 후 sync 메타 업데이트 (last_sync_at)
```

> [가정] 동기화 메타 테이블 / 중복 처리 정책은 Sprint 5 spec에서 확정.

---

## 7. 상태 폴링 vs WebSocket (현재/계획)

### 현재 (Sprint 4)

- 백테스트 진행: `GET /backtests/:id/progress` 폴링 (예: 1~2초 간격)
- 단순, 캐시 친화적, 부담 낮음

### Sprint 7+ 예정

- WebSocket 채널: `/ws/sessions/:id` (트레이딩 세션 PnL/체결 push)
- Zustand 캐시 (React Query와 분리, CLAUDE.md 규칙)

---

## 8. 페이지네이션 패턴

| API | 패턴 | 비고 |
|-----|------|------|
| `GET /strategies` | `page` + `limit` (Sprint 3 drift) | Sprint 5에서 `limit + offset` 통일 예정 |
| `GET /backtests` | `limit` + `offset` (Sprint 4 표준) | `common/pagination.py` |
| `GET /backtests/:id/trades` | `limit` + `offset` | 동일 |

> Sprint 5 이관 항목 #10: Strategy router pagination drift 통일.

---

## 9. 에러 응답 패턴 (참조)

상세는 [`system-architecture.md`](./system-architecture.md) §5. 모든 도메인 예외는 `code` 필드 포함 JSON.

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
