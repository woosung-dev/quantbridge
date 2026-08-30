# QuantBridge — 데이터 흐름

> **목적:** 도메인별 주요 시퀀스 다이어그램.
> **상위 문서:** [`system-architecture.md`](./system-architecture.md), 도메인 경계는 [`domain-overview.md`](../domain/domain-overview.md).

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
    participant Engine as pine_v2 인터프리터
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
    W->>Engine: run_backtest_v2(strategy/AST, ohlcv, params)
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
- startup hook과 Celery Beat가 함께 reclaim한다. Beat 주기는 `tasks/celery_app.py`가 정한다.
- 멀티 워커 split-brain 방어 (Sprint 5+ #13): `inspect().active()` 또는 Redis lock

---

## 5. Auth — self-host Better Auth ([ADR-034](../adr/034-auth-self-host-better-auth.md))

★**Next 앱이 인증 서버 본체다.** 외부 인증 벤더도, lifecycle webhook 도 없다.
★**두 구간의 자격증명이 다르다** — 브라우저↔Next 는 **세션 쿠키**, Next↔FastAPI 는 **Bearer JWT**.
★**백엔드는 비밀을 하나도 쥐지 않는다** — 검증은 JWKS 공개키로만 한다(`realtime/auth.py:1-2`).

```mermaid
sequenceDiagram
    actor User
    participant FE as Next (Better Auth 서버)
    participant API as FastAPI

    User->>FE: POST /api/auth/sign-in/email
    FE->>FE: auth_user / auth_session 조회·발급
    FE-->>User: 세션 쿠키

    User->>FE: GET /api/auth/token (쿠키 동반)
    FE-->>User: EdDSA 서명 JWT (iss = aud = BETTER_AUTH_URL)

    User->>API: GET /api/v1/auth/me\nAuthorization: Bearer <JWT>
    API->>FE: GET /api/auth/jwks (kid 별 캐시, lifespan 3600s)
    FE-->>API: 공개키
    API->>API: JWT 검증 (signature · exp · iss · aud)
    API->>API: sub 추출 → get_or_create (JIT 프로비저닝)
    API-->>User: 200 + user payload
```

**lifecycle 동기화 — webhook 이 아니라 세 경로다.**

| 사건      | 경로                                                                                                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 가입      | FastAPI 가 첫 인증 요청에서 `sub` 로 **JIT 생성**한다 (`auth/service.py` `get_or_create`, 호출은 `realtime/auth.py`)                                   |
| 정보 변경 | ★**같은 `get_or_create` 가 매 요청에서 동기화한다** — JWT 의 `email`·`username`·`country` 를 DB 행과 비교해 **다를 때만** `update_profile()` 을 부른다 |
| 탈퇴      | `DELETE /api/v1/auth/me` → `auth/service.py:131` `deactivate_account`. 이후 그 `sub` 의 JWT 는 `UserInactiveError` 로 막힌다 (`realtime/auth.py:186`)  |

★**JWKS 호출은 rate limit 안쪽에 둔다.** `PyJWKClient` 는 **미상 `kid` 에 음성 캐시가 없어**
같은 가짜 kid 를 10번 보내면 JWKS 를 **11번** 가져온다 — `Authorization: Bearer <아무거나>` 만으로
1:1 증폭이다(`realtime/auth.py:113-117`).

---

## 6. OHLCV cache flow (Sprint 5 M3 ✅)

> 별도 sync API/UI는 없다. **Backtest가 OHLCV를 요청하는 시점에 cache → CCXT fallback**으로 채우며, `TimescaleProvider`가 on-demand로 처리한다.

```mermaid
sequenceDiagram
    participant Backtest as BacktestService<br/>(또는 Celery task)
    participant TP as TimescaleProvider
    participant Repo as OHLCVRepository
    participant TS as ts.ohlcv hypertable
    participant CCXT as CCXTProvider

    Backtest->>TP: get_ohlcv(symbol, tf, start, end)
    TP->>Repo: acquire_fetch_lock(symbol, tf, start, end)
    Repo->>TS: SELECT pg_advisory_xact_lock(hashtext(key))
    Note over Repo,TS: 동시 fetch 직렬화 — tx commit 시 자동 해제

    TP->>Repo: find_gaps(symbol, tf, start, end, tf_sec)
    Repo->>TS: WITH expected AS (generate_series ...) EXCEPT ohlcv → island grouping
    TS-->>Repo: list[(gap_start, gap_end)]

    alt gaps 존재 (cache miss/partial)
        loop 각 gap
            TP->>CCXT: fetch_ohlcv(symbol, tf, gap_start, gap_end)
            CCXT->>CCXT: pagination + tenacity retry + closed bar 필터
            CCXT-->>TP: raw bars[ts_ms, o, h, l, c, v]
            TP->>Repo: insert_bulk(rows) — ON CONFLICT DO NOTHING
            Repo->>TS: INSERT idempotent
        end
        TP->>Repo: commit() → advisory lock 해제
    end

    TP->>Repo: get_range(symbol, tf, start, end)
    Repo->>TS: SELECT ... WHERE time BETWEEN ... ORDER BY time
    TS-->>Repo: list[OHLCV]
    TP-->>Backtest: pd.DataFrame[time index, open/high/low/close/volume float]
```

### 핵심 결정 (Sprint 5 M3)

- **on-demand cache-first** — Backtest 실행 시점에 필요한 구간만 fetch. 별도 동기화 task 없음.
- **gap 계산은 Postgres가 책임** — `generate_series + EXCEPT + ROW_NUMBER` island grouping (FE/BE 가공 없음).
- **idempotent insert** — `ON CONFLICT DO NOTHING`. UPDATE 안 함 (CCXT 데이터는 immutable past data).
- **동시 fetch race** — `pg_advisory_xact_lock(hashtext(key))`. 같은 (symbol, tf, period) lock 보유 중인 타 트랜잭션은 대기. tx commit 시 해제.
- **closed bar filter** — CCXTProvider가 `last_closed_ts = (now // tf_sec) * tf_sec - tf_sec` 이하만 반환 (진행 중 캔들 제외).
- **provider lifecycle** — HTTP는 FastAPI lifespan singleton, Worker는 prefork-safe lazy + worker_shutdown close ([`system-architecture.md`](./system-architecture.md) §lifecycle 참조).

---

## 7. Polling + Bybit Private WebSocket (Sprint 12 도입 ✅)

### 7.1 백테스트 진행 — 폴링 유지

`GET /backtests/:id/progress` 1~2초 간격 폴링. 단순 + 캐시 친화적 + 부담 낮음. WS 로 마이그 안 함.

### 7.2 Trading 주문 체결 — Bybit Private WebSocket (Sprint 12 Phase C)

```mermaid
sequenceDiagram
    participant W as ws-stream Worker<br/>(prefork + Redis lease)
    participant Sup as BybitPrivateStream<br/>supervisor
    participant Stream as websockets connection
    participant SH as StateHandler<br/>(transport adapter)
    participant SVC as WS order/reconcile service
    participant Repo as OrderRepository
    participant DB as PostgreSQL
    participant Beat as Celery Beat (5분)
    participant Rec as Reconciler
    participant CCXT as open/recent orders REST

    Beat->>W: reconcile_ws_streams: 없는 stream만 재-enqueue
    W->>Sup: private stream task 시작
    Sup->>Stream: connect + auth (60s startup timeout)
    Stream-->>Sup: subscribed (order topic)

    Note over Sup,Stream: 정상 흐름 — order event 수신
    Stream-->>SH: order event {orderLinkId=UUID, status, ...}
    SH->>SVC: callback(account_id, payload)
    SVC->>Repo: local order lookup + terminal transition
    Repo->>DB: SELECT / conditional UPDATE
    alt UUID 매핑 OK
        SVC->>Repo: commit
        SVC->>SVC: commit 뒤 winner 효과<br/>(realtime·metric·후속 task)
    else UUID 미상
        SVC->>SVC: 즉시 폐기 — orphan arrival + discarded{reason}
    end

    Note over Sup,Stream: 끊김 — supervisor 재시작
    Stream-xSup: ConnectionClosed / heartbeat 종료
    Sup->>Sup: 1→30s exponential backoff
    Sup->>Stream: reconnect + reauth
    Sup->>Sup: qb_ws_reconnect_total.inc()

    Note over Sup,Rec: first connect·reconnect 뒤 reconciliation (30초 debounce)
    Sup->>Rec: reconcile callback
    Rec->>SVC: callback(account_id)
    SVC->>Repo: local pending/submitted 조회
    SVC->>CCXT: fetch_open_orders + fetch_recent_orders
    CCXT-->>SVC: snapshot
    alt terminal evidence
        SVC->>Repo: conditional UPDATE + commit
        SVC->>SVC: commit 뒤 winner 효과
    else local order not in snapshot
        SVC->>SVC: state 유지 + unknown metric + alert
    end
```

### 7.3 핵심 결정 (Sprint 12)

- **supervisor 패턴** — supervisor task 가 child stream task 의 종료를 감지하여 자동 재시작 (1→30s exponential)
- **prefork + Redis lease** — stream task 중복은 분산 lease로 막고 worker child의 영속 loop에서 실행한다.
- **OrderLinkId UUID 매핑** — CCXT 어댑터가 `params={orderLinkId: str(Order.id)}` 전달. `StateHandler`는 DB를 직접 만지지 않고 서비스 callback으로 넘긴다.
- **즉시 orphan 폐기** — 재생 버퍼는 호출자가 없어 삭제했다. 종결 이벤트와 무해한 비종결 이벤트는 `reason` label로 구분해 관측한다.
- **terminal-evidence-only transition** — Reconciliation service는 명확한 terminal snapshot만 반영하고, 모호하거나 없는 행은 상태를 바꾸지 않는다.
- **best-effort Slack alert** — KillSwitch event save 직후 alert task. alert 실패 ≠ KillSwitch 차단

### 7.4 신규 metrics

§7.2 시퀀스 안에 표시. 카탈로그는 [`system-architecture.md`](./system-architecture.md) §8.

### 7.5 제품 경계

- private WebSocket은 **Bybit Demo 계정만** 연결한다. 과거 live/OKX 행은 보존하되 stream 재등록·자격증명 복호화 전에 차단한다.
- 공개 ticker·과거 OHLCV/funding 수집은 사용자 private egress와 별도 경계다.

---

## 8. 페이지네이션 패턴

| API                         | 패턴                                  | 비고                                          |
| --------------------------- | ------------------------------------- | --------------------------------------------- |
| `GET /strategies`           | `limit` + `offset` (Sprint 5 M4 통일) | `page`는 deprecated fallback (Sprint 6+ 제거) |
| `GET /backtests`            | `limit` + `offset` (Sprint 4 표준)    | `common/pagination.py`                        |
| `GET /backtests/:id/trades` | `limit` + `offset`                    | 동일                                          |

> ✅ Sprint 5 M4 T32 완료: 모든 list endpoint `limit/offset` 표준 + `page` legacy fallback.

---

## 8.5 Worker Loop + Multi-Task Lifecycle (Sprint 18 BL-080 ✅)

> 상세 패턴: [`system-architecture.md`](./system-architecture.md) §7.5. 회고: `docs/dev-log/2026-05-02-sprint18-bl080-architectural.md`.

Sprint 18 의 Option C 영속 `_WORKER_LOOP` 채택으로, **동일 worker child 가 mixed task type 을 sequential 처리** 가능 (Sprint 17 까지의 task 별 process isolation 가정 폐기). asyncpg connection 의 transport waiter 가 1st task loop 에 stale binding 되는 문제를 영속 loop 통일로 해소.

```mermaid
sequenceDiagram
    participant M as Celery Master
    participant C as ForkPoolWorker-N (prefork child)
    participant L as _WORKER_LOOP (asyncio.new_event_loop)
    participant T1 as Task A: scan_stuck_orders
    participant T2 as Task B: reconcile_ws_streams
    participant T3 as Task C: reclaim_stale_running

    M->>C: fork()
    Note over C: worker_process_init signal
    C->>L: init_worker_loop() — set_event_loop(loop)
    C->>C: reset_redis_lock_pool() (parent fork stale FD 폐기)

    Note over M,C: Beat schedule 5분 cycle 시작

    M-->>C: Task A delivered
    C->>L: run_in_worker_loop(_async_scan_stuck_orders())
    L->>T1: run_until_complete
    T1-->>L: {pending: 0, submitted: 0, interrupted: 0}
    L-->>C: 반환

    M-->>C: Task B delivered (mixed type, 같은 child)
    C->>L: run_in_worker_loop(_reconcile_async())
    L->>T2: run_until_complete
    T2-->>L: {enqueued: [], skipped_active: [], total: 0}
    L-->>C: 반환

    M-->>C: Task C delivered
    C->>L: run_in_worker_loop(reclaim_stale_running())
    L->>T3: run_until_complete (asyncpg connection 재사용 — 같은 loop bind)
    T3-->>L: 0
    L-->>C: 반환

    Note over C: worker_max_tasks_per_child=250 도달
    Note over C: worker_process_shutdown signal
    C->>L: shutdown_worker_loop()
    Note over L: pending task cancel + asyncgens drain<br/>+ default executor shutdown + close()
    C->>M: child 종료
    M->>C: 새 child fork (반복)
```

### 핵심 invariant

- **모든 prefork child task body 가 같은 `_WORKER_LOOP` 사용** — asyncpg/SQLAlchemy/Redis pool/CCXT client 의 internal loop reference 가 stale 되지 않음.
- **`worker_max_tasks_per_child=250`** (Sprint 18 보수) — child rotation 으로 memory bloat 방어. Sprint 20+ BL-082 1h soak gate 후 1000 검토.
- **per-call `create_worker_engine_and_sm()` + finally `engine.dispose()` 그대로 유지** — connection pool 누수 방어 (loop binding 과 별개).
- **`run_bybit_private_stream` (long-running)** 은 별도 `ws_stream` queue + `--pool=solo` worker 분리 (Sprint 12 패턴 유지). 같은 child 에 short task 안 옴.
- **Sprint 19 BL-085** integration test 가 본 lifecycle 의 회귀 자동화: `init_worker_loop()` → 3 task type x 3 cycle = 9 호출 → 모두 succeeded.

---

## 9. 에러 응답 패턴 (참조)

상세는 [`system-architecture.md`](./system-architecture.md) §5. 모든 도메인 예외는 `code` 필드 포함 JSON.

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
- **2026-05-02** — §8.5 Worker Loop + Multi-Task Lifecycle (Sprint 18 BL-080) 추가. 영속 `_WORKER_LOOP` 패턴 시퀀스 다이어그램.
