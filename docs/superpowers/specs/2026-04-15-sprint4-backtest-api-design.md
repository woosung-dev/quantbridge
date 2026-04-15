# Celery 래퍼 + Backtest 도메인 REST API — 설계 문서

- **작성일:** 2026-04-15
- **단계:** Stage 3 / Sprint 4
- **관련 ADR:** ADR-003 (Pine 런타임 안전성 + 파서 범위)
- **선행 스프린트:** Sprint 3 (Strategy API + Clerk 실배선, merge `3687028`)
- **방법론:** brainstorming → writing-plans → TDD 구현 (Sprint 1/2/3과 동일)
- **시간박스:** 없음. 완료 기준 충족 시 종료.

---

## 1. 목적과 범위

### 1.1 왜 이 스프린트인가

Sprint 2가 순수 함수 `run_backtest(source, ohlcv, config) -> BacktestOutcome`를 완성했고, Sprint 3이 Strategy 도메인 CRUD + Clerk JWT + Alembic 인프라를 실배선했다. 그러나 현재 백테스트는 HTTP 표면이 전무하다 — `src/backtest/{router,service,repository,models,schemas,dependencies}.py` 전부 1-line 스텁이다. 또한 Celery 워커도 구성되지 않아, CLAUDE.md §QuantBridge 고유 규칙(“백테스트/최적화는 반드시 Celery 비동기”)이 아직 엔드투엔드로 실현되지 않았다.

본 스프린트는 이 공백을 메운다:

1. Sprint 2의 순수 엔진을 **Celery task로 래핑**하여 HTTP 비동기 파이프라인을 완성한다
2. Backtest 도메인의 **7개 REST 엔드포인트**를 구현한다 (list/detail/trades/progress/cancel/delete + submit)
3. Sprint 5 `market_data` 도메인 합류를 대비해 **`OHLCVProvider` 인터페이스 + `FixtureProvider` 구현체**를 선점 배치한다
4. Sprint 3에서 이월된 backtest 엔진 follow-up 2건 (**S3-03 커버리지 95%, S3-04 SL ratio 검증**)을 브랜치 초반에 정리한다

S3-05 (`_utcnow()` naive UTC → `DateTime(timezone=True)` 전환)는 migration 재생성 리스크가 있고, TimescaleDB hypertable을 실제로 도입하는 Sprint 5 시점에 묶어 처리하는 것이 응집도가 높으므로 Sprint 5로 이월한다.

### 1.2 완료 기준 (Go / No-Go)

모두 충족 시 스프린트 종료:

1. **S3-04 정리 (필수):** 브랜치 초반 commit로 처리. `_price_to_sl_ratio` 음수 → `ValueError` 전파 테스트
   - **S3-03 (stretch target):** `src/backtest/engine/*` 커버리지 ≥95% 시도. 미달 시 Sprint 4 완료 막지 않음 — 미커버 라인 목록을 §10 Post-Impl Notes에 기록하고 Sprint 5로 이월
2. **7개 엔드포인트 API integration green** (httpx + Dependency override, 실 Celery worker 미사용):
   - `POST /api/v1/backtests` (202 + `backtest_id`) — **canonical 응답 필드는 `backtest_id`** (endpoints.md `task_id` 표현도 함께 수정)
   - `GET /api/v1/backtests` (페이지네이션: `?limit=20&offset=0`)
   - `GET /api/v1/backtests/:id` (결과 조회)
   - `GET /api/v1/backtests/:id/trades` (페이지네이션: `?limit=100&offset=0`)
   - `GET /api/v1/backtests/:id/progress` (경량 상태 조회, stale 플래그 포함)
   - `POST /api/v1/backtests/:id/cancel` (신규 — endpoints.md 갱신. **HTTP 202 Accepted + body `{status: "cancelling", message: "..."}`**)
   - `DELETE /api/v1/backtests/:id` (terminal 상태만)
3. **Ownership 격리:** 타 사용자 backtest 접근 시 404 (Sprint 3 패턴 계승)
4. **Celery 통합:** `src/tasks/{celery_app,backtest}.py` 구성, `asyncio.run()` per-task 패턴, **pool=prefork 고정** (`--pool=prefork` 명시), `run_backtest_task.delay()` → `_execute()` 경로 동작
5. **Alembic round-trip:** upgrade / downgrade / upgrade 3-phase 테스트 통과 (Sprint 3 패턴 재사용)
6. **필수 시나리오 리스트 통과** (산출량 기준이 아닌 커버리지 기준):
   - submit → queued → running → completed (OHLCV fixture 경로)
   - submit → parse_failed (unsupported pine feature)
   - submit → engine error (S3-04 음수 SL ratio 간접 검증)
   - submit → broker down → 503 + DB row 미생성
   - running task cancel → terminal state (`cancelled` or `completed`) 귀결, 중간 상태 미잔류
   - delete terminal / delete non-terminal 409
   - ownership isolation (타 유저 backtest 404)
   - trades pagination + Decimal 문자열 직렬화
   - stale running 탐지 (worker reclaim)
   - Alembic upgrade/downgrade round-trip
7. **로컬 실 broker smoke 필수 3건** (§10 Post-Impl Notes에 각 결과 기록):
   - **S1:** Redis up + worker up: submit → progress polling → completed
   - **S2:** Broker down: submit → 503 + DB row 미생성 확인
   - **S3:** Running task cancel: cancel 후 상태 `cancelled` or `completed`만 존재, 중간 상태 미잔류
   - `docker-compose.yml`에 worker 서비스 없음 → worker는 수동 기동 (§10.1 커맨드 명시)
8. **CI green:** `ruff`/`mypy`/`pytest` 로컬과 CI 모두 pass. `backend` 잡 `alembic upgrade head` 스텝 유지
9. **Stale running 최소 완화:** worker startup 시 `status='running' AND started_at < now()-threshold`인 row를 `failed`로 reclaim하는 one-shot 함수 제공 + `GET /:id/progress`에 파생 `stale` 플래그 노출 (threshold 기본 30분, settings)
10. **docs 동기화:** `endpoints.md`에 `POST /:id/cancel` 반영 + `task_id → backtest_id` 용어 통일, `docs/TODO.md` Sprint 4 완료 표시 + Open Issues 이월

### 1.3 범위 밖 (Out of Scope)

- **S3-05** (`_utcnow()` → `DateTime(timezone=True)`) → Sprint 5
- **market_data router/service 활성화**, 실 OHLCV 수집 (CCXT) → Sprint 5
- **Celery eager mode 테스트** 및 **실 broker pytest-celery integration** 인프라 → Sprint 6 (Optimizer 도입 시점)
- **Stale `running` 상태 cleanup** (beat task) → Sprint 5+
- **Idempotency-Key 헤더** → Sprint 6+
- **Cursor pagination**, 고급 필터 → Sprint 6+
- **Frontend 구현** → Sprint 5+
- **프로덕션 배포, 성능 벤치마크** → Sprint 6+

---

## 2. 아키텍처

### 2.1 도메인 경계

Sprint 4는 `backtest` + `tasks` + `market_data/providers` 3개 영역을 확장. 다른 도메인은 영향 없음.

```
backend/src/
├── tasks/                              [신규 디렉토리]
│   ├── __init__.py                     [신규] celery_app re-export
│   ├── celery_app.py                   [신규] Celery 인스턴스 + 직렬화 설정
│   └── backtest.py                     [신규] run_backtest_task + _execute
│
├── backtest/                           [확장]
│   ├── router.py                       [재작성] 7 endpoints
│   ├── service.py                      [재작성] BacktestService
│   ├── repository.py                   [재작성] BacktestRepository (+rollback)
│   ├── models.py                       [재작성] Backtest + BacktestTrade SQLModel
│   ├── schemas.py                      [재작성] Pydantic V2 입출력 DTO
│   ├── serializers.py                  [신규] metrics/equity_curve JSONB 양방향 helper
│   ├── dependencies.py                 [재작성] DI 조립
│   ├── dispatcher.py                   [신규] TaskDispatcher Protocol (순환 import 방지)
│   ├── exceptions.py                   [신규] BacktestNotFound / StateConflict 등
│   └── engine/                         [유지 + S3-03/04 수정 + trades 추출]
│       ├── adapter.py                  [수정] _price_to_sl_ratio ValueError (S3-04)
│       ├── trades.py                   [신규] extract_trades() — vectorbt → RawTrade
│       ├── types.py                    [수정] BacktestResult.trades 필드 추가
│       ├── __init__.py                 [수정] run_backtest()가 trades도 채움
│       └── ... (나머지 유지)
│
├── strategy/                           [최소 확장 — Sprint 4 회귀 방지]
│   ├── service.py                      [수정] delete()에 backtest 존재 검사 추가
│   ├── exceptions.py                   [수정] StrategyHasBacktests 추가
│   └── ... (나머지 유지)
│
├── market_data/                        [부분 활성화]
│   └── providers/                      [신규 sub-module]
│       ├── __init__.py                 [신규] OHLCVProvider Protocol
│       └── fixture.py                  [신규] FixtureProvider (data/fixtures/ohlcv 읽음)
│
├── common/                             [재사용]
│   └── pagination.py                   (기존 — limit/offset 포맷 그대로)
│
└── main.py                             [수정] backtest router 등록 + worker startup hook

# runtime 자산 (소스 디렉토리 외)
backend/data/                           [신규 디렉토리]
└── fixtures/
    └── ohlcv/
        ├── BTCUSDT_1h.csv              [신규] Sprint 4 fixture
        └── ... (필요 시 추가)
```

### 2.2 3-Layer 규칙 준수 (backend.md §3)

- **Router** — HTTP 수신, 스키마 검증, `service` 호출만. 각 핸들러 3~5 LoC
- **Service** — 비즈니스 로직 + 트랜잭션 경계. `AsyncSession` 직접 import 금지. `BacktestRepository` + `StrategyRepository` + `OHLCVProvider` + `TaskDispatcher`를 생성자 주입
- **Repository** — `AsyncSession` 유일 보유. CRUD + 소유권 필터링 쿼리. `commit()`은 service 요청 시에만
- **Dependencies** — `Depends()` 조립 전담. service/repository는 FastAPI 의존성 import 금지

Sprint 3 동일 session 공유 패턴 재사용: `get_backtest_service()`가 `AsyncSession` 1개를 `BacktestRepository`와 `StrategyRepository`에 동일하게 주입해 크로스 레포지토리 트랜잭션 원자성 확보.

### 2.3 Celery 인프라

- **Broker:** Redis (`settings.celery_broker_url` — docker-compose `quantbridge-redis`)
- **Result backend:** Redis (`settings.celery_result_backend`). Sprint 4에서는 `revoke()` 조작과 결과 로깅에만 사용. **Backtest 상태/결과의 SSOT는 PostgreSQL**
- **직렬화:** `task_serializer='json'`, `result_serializer='json'`, `accept_content=['json']`
- **재시도/ack 정책:** `max_retries=0`, `acks_late=False` (stale cleanup 배제 단순화)
- **자동 import:** `celery_app.autodiscover_tasks(['src.tasks'])` 또는 `imports=['src.tasks.backtest']`

### 2.4 Celery worker에서 async DB 접근 패턴

Celery 5.x는 동기 워커만 지원하지만 QuantBridge는 100% async. `asyncio.run()` per-task 패턴으로 통일 (대안 `asgiref.async_to_sync` / 동기 Repository 복제는 Repository 이중화 또는 event loop 소유권 충돌 리스크로 기각):

```python
# src/tasks/backtest.py
@celery_app.task(bind=True, name="backtest.run", max_retries=0)
def run_backtest_task(self, backtest_id: str) -> None:
    asyncio.run(_execute(UUID(backtest_id)))


async def _execute(backtest_id: UUID) -> None:
    """Celery 분리 가능한 async 실행 본체 — 테스트 primary 타겟."""
    async with async_session_maker() as session:
        repo = BacktestRepository(session)
        strategy_repo = StrategyRepository(session)
        provider = FixtureProvider()  # Sprint 4 구현체 직접 생성 (worker-local)
        service = BacktestService(
            repo=repo,
            strategy_repo=strategy_repo,
            ohlcv_provider=provider,
            dispatcher=NoopTaskDispatcher(),  # worker 내부에서는 dispatch 불필요
        )
        await service.run(backtest_id)
```

- `_execute()`가 테스트의 primary target. pytest에서 `await _execute(id)` 직접 호출 → 동일 session 모킹 없이 Postgres savepoint fixture 재사용
- Celery 6 native async 릴리즈 시 `asyncio.run()` 제거만으로 전환 가능

**Worker pool 제약 (중요):**
- `asyncio.run()` per-task 패턴은 **Celery prefork pool 전제**. `gevent`/`eventlet`/`solo` pool과는 event loop 충돌 우려
- worker 기동 명령 고정:
  ```bash
  celery -A src.tasks worker --pool=prefork --concurrency=4 --loglevel=info
  ```
- `async_session_maker`는 모듈 전역에서 생성되지만 `asyncio.run()`이 매 task마다 새 event loop를 만들므로 **engine 자체는 loop-safe**해야 함. SQLAlchemy 2.0 `create_async_engine`은 내부 loop 바인딩이 없으므로 OK. 단, 연결 풀 warmup 비용이 task마다 반복됨 → `NullPool` 사용 시 수용 가능, `AsyncAdaptedQueuePool`은 loop 교차 위험. §10 Post-Impl Notes에 task 평균 latency 관측치 기록

### 2.5 TaskDispatcher Protocol (순환 import 방지)

`BacktestService.submit()`이 Celery task를 enqueue 해야 하지만, `src/backtest/service.py`가 `src/tasks/backtest.py`를 직접 import 하면 **순환 의존** 발생 (tasks가 service를 import하기 때문). 해결:

```python
# src/backtest/dispatcher.py  [신규]
from typing import Protocol
from uuid import UUID

class TaskDispatcher(Protocol):
    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """Enqueue backtest task. Returns celery task id."""
        ...


class CeleryTaskDispatcher:
    """실 구현 — HTTP 경로(dependencies.py)에서만 사용."""
    def dispatch_backtest(self, backtest_id: UUID) -> str:
        from src.tasks.backtest import run_backtest_task  # 지연 import
        async_result = run_backtest_task.delay(str(backtest_id))
        return async_result.id


class NoopTaskDispatcher:
    """Worker 내부 / 테스트용 — dispatch 호출 방지."""
    def dispatch_backtest(self, backtest_id: UUID) -> str:
        raise RuntimeError("NoopTaskDispatcher must not dispatch")
```

- `Service.submit()`는 `dispatcher.dispatch_backtest()` 호출 → 테스트에서 `FakeTaskDispatcher`(고정 task_id 반환) 주입 가능
- `_execute()` 내부의 Service는 submit 경로를 타지 않으므로 `NoopTaskDispatcher`를 받는다

### 2.5 OHLCVProvider Protocol (Sprint 5 대비)

```python
# src/market_data/providers/__init__.py
class OHLCVProvider(Protocol):
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        """DatetimeIndex + [open, high, low, close, volume] 컬럼."""
        ...
```

Sprint 4 구현: `FixtureProvider` — `backend/data/fixtures/ohlcv/{symbol}_{timeframe}.csv` 로드 → 기간 필터링. Sprint 5에서 `TimescaleProvider` 구현체만 추가하면 API 계약/DB 스키마/클라이언트 전부 불변.

**Fixture 위치 레이어 정합:** 초기 설계는 `backend/tests/fixtures/ohlcv/`였으나, runtime 서비스 코드(`FixtureProvider`)가 테스트 디렉토리를 읽는 것은 레이어 위반. **`backend/data/fixtures/ohlcv/`로 배치**하고, 테스트는 동일 경로를 읽거나 `OHLCV_FIXTURE_ROOT` env 로 override.

### 2.6 vectorbt Trades 추출

현재 `run_backtest()`는 `BacktestOutcome(status, parse, result, error)` 반환 — `result.equity_curve` + `result.metrics`만 있고 **trades 없음**. Sprint 4는 이를 확장:

**옵션:**
- (A) `run_backtest()` 리턴 확장 — `BacktestResult`에 `trades: list[RawTrade]` 필드 추가
- (B) Service layer에서 `pf` 재계산 — engine 내부에 `pf`를 export 하거나 adapter를 service가 재실행

**채택 (A):** 엔진 변경 1곳으로 집중, service layer는 DB 매핑만 담당. 엔진이 vectorbt dependency를 온전히 소유.

```python
# src/backtest/engine/types.py 에 추가
@dataclass(frozen=True)
class RawTrade:
    """Engine-level trade record. vectorbt records_readable → 도메인 중립 DTO."""
    trade_index: int
    direction: Literal["long", "short"]
    status: Literal["open", "closed"]
    entry_bar_index: int
    exit_bar_index: int | None
    entry_price: Decimal
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    return_pct: Decimal
    fees: Decimal


@dataclass(frozen=True)
class BacktestResult:
    metrics: BacktestMetrics
    equity_curve: pd.Series
    trades: list[RawTrade]        # 신규
    config_used: BacktestConfig
```

**변환 로직 (`engine/trades.py` 신규):**

```python
def extract_trades(pf: vbt.Portfolio, ohlcv: pd.DataFrame) -> list[RawTrade]:
    """vectorbt Portfolio → RawTrade list. Bar index는 유지 (service가 datetime 변환).

    Decimal 변환 원칙: float 공간에서 arithmetic 수행 전 str() 경유로 Decimal 진입.
    fees 같이 합산이 필요한 필드는 **Decimal 변환 후 합산** — CLAUDE.md 금융 규칙 준수.
    """
    df = pf.trades.records_readable
    raw_trades: list[RawTrade] = []
    for _, row in df.iterrows():
        # fees: Decimal-first 합산 (float 공간 + 후 str 방지 — Codex/Opus 지적)
        fees_total = Decimal(str(row["Entry Fees"])) + Decimal(str(row["Exit Fees"]))

        raw_trades.append(RawTrade(
            trade_index=int(row["Exit Trade Id"]),
            direction="long" if row["Direction"] == "Long" else "short",
            status="closed" if row["Status"] == "Closed" else "open",
            entry_bar_index=int(row["Entry Timestamp"]),
            exit_bar_index=int(row["Exit Timestamp"]) if row["Status"] == "Closed" else None,
            entry_price=Decimal(str(row["Avg Entry Price"])),
            exit_price=Decimal(str(row["Avg Exit Price"])) if row["Status"] == "Closed" else None,
            size=Decimal(str(row["Size"])),
            pnl=Decimal(str(row["PnL"])),
            return_pct=Decimal(str(row["Return"])),
            fees=fees_total,
        ))
    return raw_trades
```

**Service 변환:**
```python
# BacktestService._raw_trades_to_models
def _to_models(raw: list[RawTrade], bt_id: UUID, ohlcv_index: pd.DatetimeIndex) -> list[BacktestTrade]:
    """bar index → datetime 복원. ohlcv_index는 period-filter 후 DataFrame의 실 index."""
    return [
        BacktestTrade(
            backtest_id=bt_id,
            trade_index=t.trade_index,
            direction=TradeDirection(t.direction),
            status=TradeStatus(t.status),
            entry_time=ohlcv_index[t.entry_bar_index].to_pydatetime(),
            exit_time=ohlcv_index[t.exit_bar_index].to_pydatetime() if t.exit_bar_index is not None else None,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            size=t.size,
            pnl=t.pnl,
            return_pct=t.return_pct,
            fees=t.fees,
        )
        for t in raw
    ]
```

**주의:**
- `extract_trades()`는 엔진 covered target (S3-03 커버리지에 포함 유리)
- `run_backtest()` 공개 시그니처는 불변 (입력 변경 없음, 리턴 타입만 확장) → Sprint 2 golden 테스트 무회귀

---

## 3. 데이터 모델

> **섹션 번호 주의:** §2에 §2.6(trades 추출) 추가로 trades 추출 설계는 §2에 있음. 본 §3은 DB/스키마 한정.

### 3.1 SQLModel 테이블

```python
# src/backtest/models.py
class BacktestStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"  # transient — §5.2 참조. Worker가 'cancelled'로 최종 전이
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class Backtest(SQLModel, table=True):
    __tablename__ = "backtests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    strategy_id: UUID = Field(
        sa_column=Column(ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True)
    )

    # 입력 파라미터 (불변)
    symbol: str = Field(max_length=32, nullable=False)
    timeframe: str = Field(max_length=8, nullable=False)
    period_start: datetime = Field(nullable=False)
    period_end: datetime = Field(nullable=False)
    initial_capital: Decimal = Field(max_digits=20, decimal_places=8, nullable=False)

    # 실행 상태
    status: BacktestStatus = Field(
        sa_column=Column(SAEnum(BacktestStatus, name="backtest_status"), nullable=False, default=BacktestStatus.QUEUED)
    )
    celery_task_id: str | None = Field(default=None, max_length=64)

    # 결과 (completed 시에만)
    metrics: dict | None = Field(default=None, sa_column=Column(JSONB))
    equity_curve: list | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = Field(default=None, sa_column=Column(String(2000)))

    # Timestamps — Sprint 3 패턴 답습: models.py 파일 상단에 로컬 _utcnow() 정의
    # (S3-05에서 DateTime(timezone=True) 전환 시 일괄 정리)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    trades: list["BacktestTrade"] = Relationship(
        back_populates="backtest",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    __table_args__ = (
        Index("ix_backtests_user_created", "user_id", "created_at"),
        Index("ix_backtests_status", "status"),
    )


class BacktestTrade(SQLModel, table=True):
    __tablename__ = "backtest_trades"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    backtest_id: UUID = Field(
        sa_column=Column(ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    trade_index: int = Field(nullable=False)

    direction: TradeDirection = Field(
        sa_column=Column(SAEnum(TradeDirection, name="trade_direction"), nullable=False)
    )
    status: TradeStatus = Field(
        sa_column=Column(SAEnum(TradeStatus, name="trade_status"), nullable=False)
    )

    entry_time: datetime = Field(nullable=False)
    exit_time: datetime | None = Field(default=None)
    entry_price: Decimal = Field(max_digits=20, decimal_places=8)
    exit_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    size: Decimal = Field(max_digits=20, decimal_places=8)
    pnl: Decimal = Field(max_digits=20, decimal_places=8)
    return_pct: Decimal = Field(max_digits=10, decimal_places=6)
    fees: Decimal = Field(max_digits=20, decimal_places=8, default=Decimal("0"))

    backtest: Backtest = Relationship(back_populates="trades")

    __table_args__ = (
        Index("ix_backtest_trades_backtest_idx", "backtest_id", "trade_index"),
    )
```

### 3.2 Pydantic 스키마 (`src/backtest/schemas.py`)

**페이지네이션 계약 — 현재 `common/pagination.py` 실제 구조:**
```python
# src/common/pagination.py (기존 — 변경 없음)
class PageParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

Sprint 4 전체 페이지네이션은 `limit/offset` 포맷 사용. (Sprint 3 strategy router가 `page/limit` 포맷을 쓰고 있다면 Sprint 3 drift — 본 Sprint 범위 밖이지만 `docs/TODO.md` Open Issues에 기록)

**스키마 목록:**
- `CreateBacktestRequest` — 입력 검증 (`symbol` 3~32자, `timeframe` Literal, `period_end > period_start`, `initial_capital > 0`)
- `BacktestCreatedResponse` — 202 응답 (`backtest_id: UUID`, `status: BacktestStatus`, `created_at: datetime`) — **canonical 필드명은 `backtest_id`** (task_id 필드는 미노출)
- `BacktestProgressResponse` — `GET /:id/progress` 경량 (`backtest_id`, `status`, `started_at`, `completed_at`, `error`, **`stale: bool`** — running 상태가 threshold 초과 시 파생 true)
- `BacktestCancelResponse` — `POST /:id/cancel` 응답 (`backtest_id`, `status='cancelling' | 'cancelled' | 'completed'`, `message`) — **semantics: "cancellation requested"이지 "중지 보장" 아님**
- `BacktestSummary` — 목록 항목 (metrics 미포함)
- `BacktestDetail` — 상세 (`initial_capital`, `metrics`, `equity_curve`, `error`)
- `BacktestMetricsOut` — `engine/types.py::BacktestMetrics` → API 노출 (Decimal → str, Pydantic V2 `@field_serializer` 사용)
- `EquityPoint` — `{timestamp: datetime, value: Decimal}` — **JSON 직렬화 시 timestamp는 ISO 8601 문자열 (e.g. `"2024-06-01T12:00:00Z"`)**
- `TradeItem` — Decimal 문자열 직렬화 (Pydantic V2 `@field_serializer`)
- `Page[TradeItem]` / `Page[BacktestSummary]` — `common/pagination.Page[T]` 재사용

### 3.3 JSONB 직렬화 규약

**`metrics` 컬럼** (dict):
```json
{
  "total_return": "0.184",           // Decimal → str
  "sharpe_ratio": "1.42",
  "max_drawdown": "-0.078",
  "win_rate": "0.56",
  "num_trades": 24
}
```

**`equity_curve` 컬럼** (list of 2-element arrays):
```json
[
  ["2024-01-01T00:00:00Z", "10000.00"],    // [ISO 8601 UTC, Decimal str]
  ["2024-01-01T01:00:00Z", "10012.50"],
  ...
]
```

- 직렬화 helper는 `src/backtest/serializers.py` 신규 — `metrics_to_jsonb()`, `jsonb_to_metrics()`, `equity_curve_to_jsonb()`, `jsonb_to_equity_curve()`
- Service layer에서만 호출 — Repository/Router는 JSONB dict 그대로 통과

**Naive UTC datetime 직렬화 주의사항:**

Sprint 3 `_utcnow()`는 naive UTC datetime 반환 (S3-05 workaround). Python 표준 `datetime.isoformat()`은 **naive에 `Z` 접미사 안 붙음** — `"2024-01-01T00:00:00"` 반환. Spec이 약속한 `"2024-01-01T00:00:00Z"` 포맷을 달성하려면 명시적 변환 필요:

```python
# src/backtest/serializers.py
def _utc_iso(dt: datetime) -> str:
    """naive UTC datetime → ISO 8601 with Z suffix."""
    if dt.tzinfo is not None:
        # tz-aware면 UTC로 변환 후 제거 (방어적)
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc_iso(s: str) -> datetime:
    """'2024-01-01T00:00:00Z' → naive UTC datetime."""
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
```

equity_curve / 기타 timestamp 필드는 이 헬퍼 경유. S3-05(`DateTime(timezone=True)`) 전환 후 일괄 정리 예정.

### 3.4 Alembic Migration

- 단일 revision: `add_backtests_and_trades_tables`
- 생성 대상: 2 테이블, 3 Enum 타입 (backtest_status / trade_direction / trade_status), 3 인덱스, 2 외래키
- FK 정책:
  - `backtests.user_id` → `users.id` **ON DELETE CASCADE**
  - `backtests.strategy_id` → `strategies.id` **ON DELETE RESTRICT** (백테스트 있는 전략은 hard delete 불가 → archive 유도, §4.8 참조)
  - `backtest_trades.backtest_id` → `backtests.id` **ON DELETE CASCADE**
- Sprint 3 CI 스텝 `alembic upgrade head` + round-trip 테스트로 자동 검증
- `started_at` / `completed_at`는 nullable 유지 (server_default/onupdate 미적용). Service layer에서 명시적으로 `_utcnow()` 주입 — Sprint 3 `created_at` 패턴과 일관

---

## 4. 엔드포인트 계약

### 4.1 `POST /api/v1/backtests`

**Request:**
```json
{
  "strategy_id": "uuid",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-06-30T23:59:59Z",
  "initial_capital": "10000.00"
}
```

**Response 202:**
```json
{ "backtest_id": "uuid", "status": "queued", "created_at": "..." }
```

**오류:**
- 404 `strategy_not_found` (Sprint 3 재사용) — 타인 소유 포함
- 400 `ohlcv_fixture_not_found` — Sprint 4 fixture 미보유 심볼
- 422 Pydantic validation (기간 역전, capital ≤ 0 등)
- 503 `task_dispatch_failed` — broker 연결 실패. DB row 롤백

**Service 흐름:**
```python
async def submit(self, data, user):
    strategy = await self.strategy_repo.get_by_id(data.strategy_id, user_id=user.id)
    if strategy is None:
        raise StrategyNotFound()
    bt = await self.repo.create(Backtest(... user_id=user.id))  # flush
    try:
        task_id = self.dispatcher.dispatch_backtest(bt.id)
    except TaskDispatchError:
        await self.repo.rollback()   # BacktestRepository.rollback() 신규 메서드
        raise
    bt.celery_task_id = task_id
    await self.repo.commit()
    return BacktestCreatedResponse(...)
```

**Repository `rollback()` 추가 (Sprint 3 패턴 확장):**
```python
# src/backtest/repository.py
class BacktestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        """TaskDispatchError 등 commit 직전 실패 시 in-flight change 되돌림."""
        await self.session.rollback()

    # ... 나머지 CRUD
```

### 4.2 `GET /api/v1/backtests`

- Query: `?limit=20&offset=0` (`common/pagination.PageParams`)
- Response: `Page[BacktestSummary]` (`items`, `total`, `limit`, `offset`)
- Ordering: `created_at DESC`
- 소유자 필터: Repository에서 `WHERE user_id = :user_id`

### 4.3 `GET /api/v1/backtests/:id`

- Response: `BacktestDetail`
- `status != 'completed'`인 경우 `metrics`/`equity_curve`/`trades` 관련 필드 null
- 404 `backtest_not_found` (존재 X or 타 사용자)

### 4.4 `GET /api/v1/backtests/:id/trades`

- Query: `?limit=100&offset=0`
- Response: `Page[TradeItem]`
- Ordering: `trade_index ASC`
- 상태 체크: `completed` 외에는 빈 페이지 반환 (404 대신)

### 4.5 `GET /api/v1/backtests/:id/progress`

- Response: `BacktestProgressResponse` (`status`, `started_at`, `completed_at`, `error`, **`stale: bool`**)
- 경량 조회 — metrics/equity_curve 미포함 (목록 페이지에서 활용)
- **`stale` 계산:** `status IN ('running', 'cancelling') AND started_at IS NOT NULL AND now() - started_at > settings.backtest_stale_threshold_seconds`(기본 1800초=30분)인 경우 파생 `true`. DB 컬럼 아님 — response 조립 시점 계산. `cancelling`도 포함 이유: SIGTERM kill 시 잔류 (§5.2 Scenario E)

### 4.6 `POST /api/v1/backtests/:id/cancel` ⭐ 신규

**Semantics: cancellation request (best-effort). 즉시 중지 보장하지 않음.**

- Body: 없음
- 허용 상태: `queued`, `running`
- 동작:
  1. `service.cancel()` — load + state guard (`raise BacktestStateConflict` if terminal)
  2. `AsyncResult(celery_task_id).revoke(terminate=True)` — **best-effort**. 이미 종료된 task엔 no-op. Worker가 한창 계산 중이면 SIGTERM이 도달해도 엔진 finalizer가 먼저 결과를 쓸 수 있음
  3. `status='cancelling'`로 전이 + commit (즉시 반영 — 사용자는 취소 요청 성공 관측)
  4. Worker의 `_execute()`는 완료 write 직전 **재확인 가드** — 아래 §5.2 재확인 로직 참조
  5. Worker가 최종적으로 `cancelled` 또는 `completed`로 귀결 — 중간 상태(`cancelling`)는 transient
- **응답 HTTP `202 Accepted`** (표준 reason phrase "Accepted" 유지) + body `BacktestCancelResponse { backtest_id, status, message }`:
  ```http
  HTTP/1.1 202 Accepted
  Content-Type: application/json

  { "backtest_id": "uuid", "status": "cancelling",
    "message": "Cancellation requested. Final state will be observable via GET /:id/progress." }
  ```
  **주의:** `cancellation_requested`는 body의 **시맨틱 레이블**(README 용어)이고, HTTP reason phrase는 "Accepted"로 유지. FastAPI 구현 시 `status_code=202` 반환만 하면 됨 (`reason_phrase` 커스터마이즈 금지).
- 오류:
  - 409 `backtest_state_conflict` (이미 terminal)
  - 404 `backtest_not_found`

**endpoints.md 업데이트:** §Backtests 표에 cancel 행 추가 + "202 + task_id"를 "202 + backtest_id"로 일괄 교정.

### 4.7 `DELETE /api/v1/backtests/:id`

- 허용 상태: `completed`, `failed`, `cancelled` (terminal only)
- `running`/`queued`/`cancelling`은 409 `backtest_state_conflict` — "cancel 먼저 수행 + 최종 terminal 대기" 안내
- `backtest_trades`는 CASCADE 자동 삭제
- Response 204 No Content

### 4.8 Strategy Delete 연동 (Sprint 3 회귀 방지)

**배경:** `backtests.strategy_id ON DELETE RESTRICT`로 인해 Sprint 3 `StrategyService.delete()`가 백테스트 있는 전략을 지우려 하면 DB 무결성 예외가 500으로 올라갈 수 있음.

**조치 (Sprint 4 범위 포함):**

1. `StrategyService.delete()`에 **선조회 + IntegrityError 번역** 추가:
   ```python
   from sqlalchemy.exc import IntegrityError
   from asyncpg.exceptions import ForeignKeyViolationError

   async def delete(self, strategy_id: UUID, user_id: UUID) -> None:
       strategy = await self.repo.get_by_id(strategy_id, user_id=user_id)
       if strategy is None:
           raise StrategyNotFound()

       # 선조회 — happy path에서 사용자 친화적 409 제공
       if await self.backtest_repo.exists_for_strategy(strategy_id):
           raise StrategyHasBacktests()

       try:
           await self.repo.delete(strategy.id)
           await self.repo.commit()
       except IntegrityError as exc:
           # TOCTOU race loser — 선조회 이후 cancel 직전 새 backtest가 끼어든 케이스
           await self.repo.rollback()
           if isinstance(exc.orig, ForeignKeyViolationError):
               raise StrategyHasBacktests() from exc
           raise
   ```

2. `BacktestRepository.exists_for_strategy(strategy_id) -> bool` 메서드 추가 (service가 cross-repo 주입). `dependencies.py`의 `get_strategy_service()`는 `BacktestRepository`도 주입 — 동일 session 공유 (backend.md §3 크로스 레포지토리 트랜잭션 패턴)

3. `StrategyHasBacktests` 예외 신규 — `src/strategy/exceptions.py`에 추가:
   ```python
   class StrategyHasBacktests(AppException):
       code = "strategy_has_backtests"
       status_code = 409
       detail = "Strategy has associated backtests. Archive instead of delete."
   ```

4. `StrategyRepository.delete()` 구현 방식 변경 — `await session.delete(strategy)` 대신 `await session.execute(delete(Strategy).where(...))` (bulk delete statement). bulk 방식이라야 FK violation을 statement 시점에서 raise → try/except으로 catch 가능. ORM `session.delete()`는 flush 시점에 violation 발생하는데 이 시점이 더 늦어 catch 경로가 꼬일 수 있음

5. FE/클라이언트 UX 가이드: **전략 삭제 대신 archive 유도** (Strategy 모델에 이미 `is_archived` 존재). Sprint 4 범위에서는 BE 규칙만 구현, FE 메시지/가이드는 Sprint 5+

6. FK RESTRICT는 TOCTOU 방어용으로 유지 — **이중화 경로가 실제로 409로 번역되도록 IntegrityError catch 필수** (Codex/Opus 지적 반영)

**Sprint 3 회귀 테스트:** `tests/strategy/test_delete.py`에 다음 3 케이스 추가:
- 백테스트 없는 strategy → 204 (기존 동작)
- 백테스트 있는 strategy (선조회 hit) → 409 `strategy_has_backtests`
- TOCTOU 시뮬레이션 (mock으로 선조회 false 반환 후 실제 DELETE 시 FK violation) → 409 `strategy_has_backtests`

---

## 5. 데이터 플로우

### 5.1 성공 경로 (Happy Path)

```
Client → POST /backtests
         ├─ Router: CreateBacktestRequest 파싱 → service.submit(data, user)
         │
         ├─ Service.submit():
         │    1. strategy_repo.get_by_id(strategy_id, user_id=user.id) → Strategy or 404
         │    2. repo.create(Backtest(status='queued', ...))      # flush, UUID 확정
         │    3. dispatcher.dispatch_backtest(bt.id)               # Celery.delay()
         │       → Broker(Redis)에 task enqueue, AsyncResult.id 반환
         │    4. bt.celery_task_id = task_id
         │    5. repo.commit()
         │    6. return BacktestCreatedResponse
         │
         └─ HTTP 202 + { backtest_id, status: "queued", created_at }

Celery Worker (별도 프로세스, Redis poll)
         ├─ task 픽업 → run_backtest_task(backtest_id)
         │    └─ asyncio.run(_execute(backtest_id))
         │
         ├─ _execute():
         │    async_session_maker() 컨텍스트에서:
         │    1. repo.get(bt_id) → Backtest
         │
         │    2. 재확인 가드 #1 (pickup):
         │       if bt.status == 'cancelling':
         │           # Service.cancel()이 queued→cancelling 전이했고 worker가 늦게 픽업한 케이스
         │           repo.finalize_cancelled(bt.id, completed_at=now, where_status='cancelling')
         │           repo.commit()
         │           return  # 종료 — 엔진 실행 금지
         │       elif bt.status != 'queued':
         │           # 이미 terminal/running (재큐잉?) → 보수적으로 skip
         │           return
         │
         │    3. strategy_repo.get_by_id(bt.strategy_id, user_id=bt.user_id) → Strategy
         │    4. provider.get_ohlcv(bt.symbol, bt.timeframe, bt.period_start, bt.period_end)
         │
         │    5. repo.update_status(bt.id, 'running', started_at=now, where_status='queued')
         │       # 조건부 UPDATE: rows=0이면 (cancel이 선행되어 'cancelling'인 경우)
         │       # → Guard #1로 되돌아가 finalize_cancelled 처리 후 return
         │       if rows == 0:
         │           repo.finalize_cancelled(bt.id, completed_at=now, where_status='cancelling')
         │           repo.commit()
         │           return
         │    6. repo.commit()
         │
         │    7. 재확인 가드 #2 (pre-engine):
         │       bt = repo.get(bt_id)  # re-read
         │       if bt.status == 'cancelling':
         │           repo.finalize_cancelled(bt.id, completed_at=now, where_status='cancelling')
         │           repo.commit()
         │           return
         │
         │    8. outcome = run_backtest(strategy.source, ohlcv, config)
         │       # trades 추출: outcome.result.trades (RawTrade list) — §2.6 참조
         │
         │    9. 재확인 가드 #3 (post-engine, 완료 write 전):
         │       bt = repo.get(bt_id)  # re-read
         │       if bt.status == 'cancelling':
         │           repo.finalize_cancelled(bt.id, completed_at=now, where_status='cancelling')
         │           repo.commit()
         │           return   # ⚠️ return — 아래 complete/fail은 skip (ghost-trade 방지)
         │
         │    10. 완료 write — trades bulk insert와 status UPDATE를 단일 트랜잭션 내에서:
         │        async with repo.session.begin_nested():    # savepoint
         │            match outcome.status:
         │              | 'ok':
         │                  raw_trades = outcome.result.trades
         │                  bt_trades = _to_models(raw_trades, bt.id, ohlcv.index)
         │                  rows = repo.complete(bt.id, metrics, equity_curve,
         │                                       where_status='running')
         │                  if rows == 0:
         │                      # cancel이 이 transaction 직전에 끼어듦 — savepoint rollback
         │                      raise _CancelRace()
         │                  repo.insert_trades_bulk(bt_trades)  # FK는 방금 complete 한 row
         │              | 'parse_failed' | 'error':
         │                  repo.fail(bt.id, error=outcome.error, where_status='running')
         │        # _CancelRace 캐치 → Guard #3 경로 재실행 (finalize_cancelled)
         │    11. repo.commit()
         │
         └─ DB: backtests.status='completed' + backtest_trades bulk insert (성공 시)
            or  backtests.status='cancelled' (cancel 경로)

Client → GET /backtests/:id/progress (폴링)
         └─ status='completed'/'cancelled'/'failed' 관측 → GET /backtests/:id 최종 결과
```

**Repository 신규 메서드 (§4.1과 함께):**
- `finalize_cancelled(bt_id, completed_at, where_status='cancelling') -> int` — 조건부 UPDATE. 반환: affected rows
- `insert_trades_bulk(trades: list[BacktestTrade]) -> None`
- `complete(...)` / `fail(...)` 모두 `where_status` 매개변수 필수 + affected rows 반환

### 5.2 취소 경로 (best-effort semantics)

```
Client (queued/running 상태) → POST /backtests/:id/cancel
         ├─ Service.cancel():
         │    1. repo.get(bt_id, user_id=user.id) → Backtest or 404
         │    2. original_status = bt.status
         │       assert original_status in ('queued', 'running') else raise BacktestStateConflict
         │    3. revoke 호출 — celery_task_id가 있는 경우만:
         │       if bt.celery_task_id:
         │           AsyncResult(bt.celery_task_id, app=celery_app).revoke(terminate=True)
         │       # celery_task_id NULL (dispatch 직후 commit 실패 희박 케이스) → revoke skip,
         │       # worker가 픽업 시 Guard #1이 cancelling 감지 후 finalize
         │    4. repo.update_status(bt.id, 'cancelling',
         │                          where_status_in=(original_status, 'queued', 'running'))
         │       # 조건부 UPDATE — race loser 이미 terminal 전이했으면 rows=0
         │       if rows == 0:
         │           # worker가 cancel 발생 직전에 먼저 완료 write 성공 — 최신 상태 재조회
         │           bt = repo.get(bt_id, user_id=user.id)
         │           raise BacktestStateConflict("Already terminal")  # 409
         │    5. repo.commit()
         │
         └─ 202 Accepted + BacktestCancelResponse { backtest_id, status: "cancelling",
                                                    message: "Cancellation requested. ..." }

Worker 병행 시나리오 (모두 terminal state 수렴):
  A) Worker 아직 시작 안 함 (queued 상태에서 cancel):
     - Cancel: queued → cancelling (조건부 UPDATE 성공)
     - Worker pickup → Guard #1에서 cancelling 감지 → finalize_cancelled → 'cancelled'
     - ✅ 최종: cancelled
  B) Worker가 running 중 (엔진 실행 전):
     - Cancel: running → cancelling
     - Worker Guard #2 (pre-engine) 감지 → finalize_cancelled → 'cancelled'
     - ✅ 최종: cancelled
  C) Worker가 엔진 실행 완료 직후 (complete 직전):
     - Cancel: running → cancelling
     - Worker Guard #3 (post-engine) 감지 → finalize_cancelled → 'cancelled' → return
     - 완료 write/trades bulk 전부 skip (ghost-trade 방지)
     - ✅ 최종: cancelled
  D) Worker가 complete write를 먼저 commit (status='completed'):
     - Cancel: load → status='completed' (terminal) → BacktestStateConflict 409
     - ✅ 최종: completed (사용자는 "too late" 응답)
  E) revoke SIGTERM이 엔진 실행 중 worker를 KILL:
     - 엔진 중간 sudden termination → finally 없음 → row는 'cancelling'으로 잔류
     - **Stale reclaim이 'cancelling' 커버** (§8.3 widening): threshold 초과 시 → 'cancelled'로 정리
     - ✅ 최종: cancelled (지연 발생, threshold에 의존)

최종 귀결 상태 불변식:
  - 모든 경로 최종적으로 'completed' | 'cancelled' | 'failed' 중 하나로 수렴
  - 'cancelling'은 transient — 정상 경로 즉시 전이, 비정상 경로(SIGTERM kill) stale reclaim이 흡수
  - stale 플래그 탐지: status IN ('running', 'cancelling') AND started_at < now() - threshold
```

### 5.3 삭제 경로

```
Client → DELETE /backtests/:id
         ├─ Service.delete():
         │    1. repo.get(bt_id, user_id=user.id) → Backtest or 404
         │    2. assert status in ('completed','failed','cancelled') else 409
         │    3. repo.delete(bt)   # CASCADE로 backtest_trades 자동 정리
         │    4. repo.commit()
         │
         └─ HTTP 204
```

---

## 6. S3-03 / S3-04 Follow-ups (브랜치 초반)

### 6.1 S3-04 — `_price_to_sl_ratio` ValueError (필수)

**현재 동작 (Sprint 3 시점):** `sl_price > close` 시 비율이 음수가 되어 vectorbt에 silent 하게 잘못된 stop 비율 전달 가능.

**수정 (실제 시그니처 준수):** 현재 adapter.py의 함수는 `(sl_price: pd.Series, close: pd.Series) -> pd.Series` 시그니처 (스칼라 Decimal 아님). vectorbt가 vectorized 연산을 받으므로 Series 유지 + 음수 ratio 검출을 vectorized로 수행:

```python
# src/backtest/engine/adapter.py
def _price_to_sl_ratio(sl_price: pd.Series, close: pd.Series) -> pd.Series:
    """가격 기반 stop loss를 close 대비 ratio로 변환.

    sl_price > close (long) 또는 sl_price < close (short 미구현) 시 음수 ratio.
    이 함수는 long만 지원(현재 adapter scope) — 음수 ratio는 사용자 실수로 간주, ValueError.
    """
    ratio = (close - sl_price) / close
    # NaN은 허용 (signal 없는 bar). 음수만 감지
    invalid = ratio.dropna() < 0
    if invalid.any():
        bad_idx = ratio.index[ratio.fillna(0) < 0]
        raise ValueError(
            f"Invalid SL price: sl_price exceeds close at index {list(bad_idx[:3])} "
            f"(would produce negative stop ratio, silent mis-stop). "
            f"Check strategy.exit(stop=...) value."
        )
    return ratio
```

**주의:** 기존 adapter.py 호출 사이트 `kwargs["sl_stop"] = _price_to_sl_ratio(signal.sl_stop, ohlcv["close"])`는 변경 없음 — Series 입출력 그대로.

**전파 경로:** `run_backtest()` `try/except Exception` 블록이 이미 존재 (엔진 `__init__.py` line 43-55) → `ValueError` catch → `BacktestOutcome(status='error', error=str(exc))` 반환. Service 레이어에서 Backtest row `status='failed'` + `error="invalid SL price: ..."` 저장.

**테스트:** `tests/backtest/engine/test_adapter.py`에 음수 ratio 케이스 1건 추가.

**수행 시점:** 브랜치 1st commit. correctness fix — 본 API 작업이 이 clamp를 간접 트리거할 수 있으므로 선행 우선.

### 6.2 S3-03 — 엔진 커버리지 95% (stretch target, 비차단)

**현재 커버리지:** `src/backtest/engine/*` 91%

**미커버 추정 영역:**
- `parse_and_run()` 예외 (unsupported feature, 파서 크래시 등 이미 status 반환하므로 엔진 측에서 catch되는 분기)
- `vbt.Portfolio.from_signals` 예외 (예: 전 bar NaN, 빈 entries)
- `extract_metrics` 0-trade 케이스 (division by zero 방어)
- **§2.6 `extract_trades()` 신규 로직** — open/closed trade 분기, 빈 DataFrame, size=0 edge

**테스트:** `tests/backtest/engine/test_fault_injection.py` 신규 파일. 각 분기당 1~2 case (총 4~6건).

**Gate 정책 (Codex 권고 반영):**
- `--cov-fail-under=95`는 **Sprint 4 CI gate에서 제외**
- 대신 `pytest --cov=src.backtest.engine`로 측정하되 strict gate 아님 — Sprint 4 종료 시점 실측값을 §10 Post-Impl Notes에 기록
- 미달 시 남은 미커버 라인 목록을 Sprint 5 first task로 이관

**수행 시점:** 브랜치 2nd commit (기능 작업 전) — S3-04 뒤 최소 fault injection만 추가. 95% 달성은 본 API 작업의 간접 커버리지 상승에 의존.

---

## 7. OHLCV Fixture 규약

### 7.1 파일 경로

`backend/data/fixtures/ohlcv/{SYMBOL}_{TIMEFRAME}.csv`

**레이어 경계:** 초기 설계는 `backend/tests/fixtures/`였으나 runtime 서비스(FixtureProvider)가 테스트 디렉토리를 읽는 것은 레이어 위반. runtime 자산은 `backend/data/`에 배치. 테스트는 동일 경로를 읽거나 `OHLCV_FIXTURE_ROOT` env로 override.

예:
- `BTCUSDT_1h.csv`
- `BTCUSDT_1d.csv` (optional)

### 7.2 CSV 포맷

```csv
timestamp,open,high,low,close,volume
2024-01-01T00:00:00Z,42000.0,42500.0,41800.0,42300.0,120.5
2024-01-01T01:00:00Z,42300.0,42400.0,42100.0,42200.0,98.2
...
```

- `timestamp` 컬럼 필수, ISO 8601 UTC
- `FixtureProvider.get_ohlcv()`가 `pd.read_csv(parse_dates=['timestamp'], index_col='timestamp')` 후 period 범위 필터링
- 기존 `tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv`는 **손대지 않음** (Sprint 2 golden 유지)

### 7.3 Sprint 4 제공 범위

- 최소 1개 `BTCUSDT_1h.csv` (기간 커버: 2024-01-01 ~ 2024-12-31, 하루 24 row × 365 ≈ 8760 row)
- 실제 OHLCV는 합성 또는 공개 데이터 스냅샷 (CCXT 미사용 — Sprint 5 범위)

### 7.4 환경변수 override

`OHLCV_FIXTURE_ROOT` (optional) — `.env.example`에 설명 추가. 테스트에서 `tmp_path` 주입 가능.

---

## 8. 에러 처리 & 엣지 케이스

### 8.1 도메인 예외 → HTTP

| 예외 | 코드 | HTTP | 상황 |
|------|------|------|------|
| `BacktestNotFound` | `backtest_not_found` | 404 | 존재 X 또는 타인 소유 |
| `BacktestStateConflict` | `backtest_state_conflict` | 409 | cancel은 queued/running만, delete는 terminal만 |
| `OHLCVFixtureNotFound` | `ohlcv_fixture_not_found` | 400 | 요청한 (symbol, timeframe) fixture 없음 |
| `TaskDispatchError` | `task_dispatch_failed` | 503 | Redis 연결 실패 등 |
| `StrategyNotFound` (Sprint 3) | `strategy_not_found` | 404 | 제출 시 전략 조회 실패 |
| `StrategyHasBacktests` (신규, §4.8) | `strategy_has_backtests` | 409 | 삭제 시 연결된 backtest 존재 — archive 유도 |

`AppException.code` 패턴은 Sprint 3 확립 — `main.py` 글로벌 핸들러 재사용.

### 8.2 동시성 레이스 (강화)

**Cancel vs Complete race (§5.2 재확인 가드 3단계):**
- `service.cancel()`은 status를 'cancelling'(transient)으로 set — worker에게 "완료 write 금지" 신호
- Worker `_execute()`는 3개 guard로 이를 존중:
  - Guard #1 (pickup 직후): `status='queued'`가 아니면 skip
  - Guard #2 (엔진 시작 직전): `status='cancelling'`이면 mark_cancelled + return
  - Guard #3 (엔진 완료 직후): `status='cancelling'`이면 완료 write 대신 mark_cancelled
- 완료/실패 write는 모두 **조건부 UPDATE** (`WHERE id=:id AND status='running'`). rows=0 시 "preempted by cancel" 로그

**Submit → dispatch 레이스:**
- `repo.create()` flush → `dispatch_backtest()` → commit을 단일 트랜잭션. dispatch 실패 시 **`repo.rollback()`** (신규 메서드, §4.1) 호출 + `TaskDispatchError` raise → 503
- dispatch 성공 후 commit 실패 시 Worker가 존재하지 않는 row ID로 실행 → `_execute()`에서 `BacktestNotFound` → task 실패 로그만 (기능 영향 없음)

**Revoke 도중 task 종료:**
- `revoke(terminate=True)`는 best-effort:
  - 이미 종료된 task엔 no-op
  - prefork worker에서 SIGTERM이 child process로 전달되지만 타이밍 불확정
  - 엔진이 한창 계산 중이면 finalizer가 먼저 결과 write 시도 → 조건부 UPDATE + Guard #3으로 수습
- API 응답 시맨틱은 **HTTP 202 Accepted** + body `status: "cancelling"` — "취소 접수"이지 "즉시 중지"가 아님

### 8.3 Worker 크래시 — Stale running 완화 (Sprint 4 포함)

Codex 피드백 반영: 아무 완화 없이 Open Issue로만 미루면 사용자 영구 polling 유발 → correctness 문제.

**Sprint 4 최소 완화 (필수):**

1. **Worker startup reclaim (one-shot 함수):**
   ```python
   # src/tasks/backtest.py
   async def reclaim_stale_running() -> int:
       """Worker 기동 시 호출. stale running/cancelling row → failed/cancelled 전환.
       Returns: reclaimed row 개수."""
       threshold = settings.backtest_stale_threshold_seconds  # 기본 1800 (30분)
       cutoff = _utcnow() - timedelta(seconds=threshold)
       async with async_session_maker() as session:
           # running 초과 → failed
           running_result = await session.execute(
               update(Backtest)
               .where(Backtest.status == BacktestStatus.RUNNING)
               .where(Backtest.started_at < cutoff)
               .values(
                   status=BacktestStatus.FAILED,
                   error="Stale running — reclaimed by worker startup",
                   completed_at=_utcnow(),
               )
           )
           # cancelling 초과 → cancelled (§5.2 Scenario E, SIGTERM kill 수습)
           cancelling_result = await session.execute(
               update(Backtest)
               .where(Backtest.status == BacktestStatus.CANCELLING)
               .where(Backtest.started_at < cutoff)
               .values(
                   status=BacktestStatus.CANCELLED,
                   completed_at=_utcnow(),
               )
           )
           await session.commit()
           return running_result.rowcount + cancelling_result.rowcount
   ```

2. **Worker 기동 hook 실제 코드 스텁** — Celery `@worker_ready` signal에 연결:
   ```python
   # src/tasks/celery_app.py
   from celery.signals import worker_ready

   @worker_ready.connect
   def _on_worker_ready(sender, **_):
       """Worker 기동 시 stale reclaim 1회 자동 실행.
       @worker_ready는 Celery master 프로세스 1회 — prefork 자식마다 아님."""
       import asyncio
       from src.tasks.backtest import reclaim_stale_running
       reclaimed = asyncio.run(reclaim_stale_running())
       if reclaimed:
           logger.info("stale_reclaim_done", extra={"reclaimed_count": reclaimed})
   ```

3. **API 파생 `stale` 플래그** (§3.2):
   - `GET /:id/progress` 응답에 `stale: bool` 포함
   - 계산식: `stale = (status IN ('running', 'cancelling') AND started_at IS NOT NULL AND now() - started_at > settings.backtest_stale_threshold_seconds)`
   - DB 컬럼 아님 — response 조립 시 파생. FE/CLI가 "이 백테스트는 정체된 것으로 보임" 시각적 표시 가능

**Config (Settings 클래스 신규 필드):**

```python
# src/core/config.py 추가
class Settings(BaseSettings):
    # ... 기존 필드
    backtest_stale_threshold_seconds: int = Field(
        default=1800,
        description="running/cancelling 상태 몇 초 초과 시 stale로 판정 (worker reclaim + stale 플래그). 기본 30분.",
    )
```

`.env.example`에 추가:
```env
BACKTEST_STALE_THRESHOLD_SECONDS=1800
```

**설정 이름 통일:** 본 문서 전체에서 `backtest_stale_threshold_seconds` 하나만 사용 (§3.2 `BacktestProgressResponse.stale` 계산식, §4.5 `stale` 플래그, §8.3 reclaim 함수 모두 이 이름).

**Beat task (주기적 cleanup)은 Sprint 5+**로 이관 — Sprint 4는 startup reclaim + 파생 플래그로 최소 completeness 확보. **Multi-worker split-brain은 Sprint 4 범위 밖** (docker-compose worker 서비스 미추가, 단일 Celery 프로세스 전제) — Open Issue #13 참조.

### 8.4 CASCADE 대량 삭제

- Sprint 4 기준 backtest당 trade 수십 건 — 무시 가능
- Sprint 6+ 대규모 경우 배치 삭제 고려

### 8.5 JSONB 직렬화 규약 요약 (§3.3 상세)

- `metrics` — Decimal → str dict
- `equity_curve` — `[[ISO 8601 UTC str, Decimal str], ...]`
- Service layer `src/backtest/serializers.py`에 4개 helper (Decimal/datetime 양방향 변환)
- Repository/Router는 JSONB dict 그대로 통과

---

## 9. 테스트 전략

### 9.1 계층

**L1 — 유닛 (빠름, 대다수)**
- `tests/backtest/test_service.py` — `submit/run/cancel/delete/list/get` 각 경로
- `tests/backtest/test_repository.py` — CRUD, list_by_user, update_status 조건부 쿼리
- `tests/backtest/test_exceptions.py` — 예외 매핑
- `tests/backtest/engine/test_fault_injection.py` — S3-03
- `tests/backtest/engine/test_adapter.py` — S3-04 음수 ratio
- `tests/market_data/test_fixture_provider.py` — CSV 로드 / 기간 필터 / 파일 누락

**L2 — Task (async helper 직접 await)**
- `tests/tasks/test_backtest_task.py`:
  - 성공 경로 (queued → running → completed, metrics + trades 저장)
  - Parse 실패 (status=failed, error 문자열 저장)
  - Engine ValueError (S3-04 간접 검증 — 음수 SL 포함 전략 제출 → failed)
  - Guard #1 (pickup 시 이미 cancelling): task skip, row 불변
  - Guard #2 (엔진 시작 직전 cancelling): mark_cancelled
  - Guard #3 (엔진 완료 직후 cancelling): 완료 write 대신 mark_cancelled
  - Stale reclaim: 기동 시 `reclaim_stale_running()` 호출 후 threshold 초과 row → failed 전환

**L3 — API integration (httpx + Dependency override, Sprint 3 conftest 재사용)**
- `tests/api/test_backtests_submit.py` — 202 / 422 / 404 / 400 / 503(broker down 시뮬) / ownership
- `tests/api/test_backtests_list.py` — pagination(limit/offset) + ownership
- `tests/api/test_backtests_detail.py` — status별 응답 스키마 + `stale` 플래그
- `tests/api/test_backtests_cancel.py` — state guard + revoke 호출(mock) + 202 cancellation_requested
- `tests/api/test_backtests_delete.py` — terminal only + CASCADE + `cancelling` 상태에서 409
- `tests/api/test_backtests_trades.py` — pagination + Decimal 문자열 + bar index → datetime 복원
- `tests/api/test_strategy_delete_with_backtests.py` — Sprint 3 회귀 방지. 백테스트 있으면 409 `strategy_has_backtests`

**L4 — 로컬 수동 smoke (필수 3건, §10 Post-Impl Notes 기록)**
- **S1 (Happy Path):** Redis up + worker up → `POST /backtests` → `GET /:id/progress` 폴링 → `completed`
- **S2 (Broker down):** Redis 중지 → `POST /backtests` → **503 `task_dispatch_failed`** + DB row 미생성 확인
- **S3 (Running cancel):** `POST /backtests` → running 확인 → `POST /:id/cancel` → 최종 state `cancelled` or `completed` 확인, `cancelling` 중간 상태 잔류 없음

Worker 기동 커맨드 (docker-compose에 worker 서비스 아직 없음):
```bash
docker compose up -d quantbridge-db quantbridge-redis
cd backend && uv run celery -A src.tasks worker --pool=prefork --concurrency=4 --loglevel=info
# 별 터미널에서:
cd backend && uv run uvicorn src.main:app --reload
```

### 9.2 필수 시나리오 체크리스트 (산출량 아닌 커버리지)

(§1.2 Go/No-Go #6과 동일 — 여기 재언급은 구현 가이드용)

- ✅ submit → queued → running → completed (fixture OHLCV 경로)
- ✅ submit → parse_failed (unsupported pine feature)
- ✅ submit → engine error (S3-04 음수 SL 간접)
- ✅ submit → 503 (broker down)
- ✅ running cancel → terminal 수렴, 중간 상태 미잔류
- ✅ delete terminal OK / delete non-terminal 409
- ✅ ownership (타 유저 404)
- ✅ trades pagination + Decimal 문자열
- ✅ stale running (worker reclaim)
- ✅ Alembic round-trip
- ✅ Sprint 3 strategy delete 회귀 (백테스트 있으면 409)

### 9.3 커버리지 목표 (non-gate)

엔진 모듈 이외에는 strict gate 없음. 실측치만 기록.

| 모듈 | 목표 | gate 여부 |
|------|------|-----------|
| `src/backtest/engine/*` | ≥95% (S3-03 stretch) | ❌ non-blocking — §6.2 |
| `src/backtest/service.py` | ≥90% | ❌ |
| `src/backtest/repository.py` | ≥90% | ❌ |
| `src/backtest/router.py` | ≥85% | ❌ |
| `src/tasks/backtest.py` | ≥80% | ❌ |
| `src/market_data/providers/fixture.py` | ≥90% | ❌ |

### 9.4 DB 격리

Sprint 3에서 구축된 `conftest.py` savepoint fixture 재사용 (SQLAlchemy 2.0 + asyncpg + NullPool + event listener 패턴). Sprint 4의 새 migration 반영만 확인.

**Backtest 모델 import 추가 (필수):** `SQLModel.metadata.create_all()`은 import된 모델만 테이블 생성. Sprint 3 패턴대로 `conftest.py` 상단에 신규 import 추가:

```python
# backend/tests/conftest.py 상단
from src.auth.models import User            # noqa: F401 (Sprint 3 기존)
from src.strategy.models import Strategy    # noqa: F401 (Sprint 3 기존)
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401 (Sprint 4 신규)
```

누락 시 `test_*_backtests_*.py` 전부 `no such table: backtests` 오류로 실패.

**Alembic vs `SQLModel.metadata.create_all()` drift 위험 (Codex 지적):**
- 현 conftest는 create_all() 기반. Sprint 3에서도 동일 — Sprint 5 TimescaleDB 도입 시점에 Alembic-based conftest 전환 예정 (Open Issue #9)
- Sprint 4는 round-trip 테스트 + CI `alembic upgrade head` 스텝으로 drift 감지를 비동기 커버. migration 파일 자체의 정확성은 CI가 보증

---

## 10. Post-Impl Notes (구현 중/후 채움)

### 10.1 Smoke 3건 결과
- [ ] S1 Happy Path: `POST /backtests` → progress 폴링 → completed (수행 커맨드 + response 캡처)
- [ ] S2 Broker down: Redis 중지 후 submit → 503 확인 + DB row 없음 확인
- [ ] S3 Running cancel: submit → cancel → 최종 state 확인, `cancelling` 잔류 없음 확인

### 10.2 엔진/Follow-up
- [x] S3-04 ValueError 도달 테스트 케이스 목록 — `TestPriceToSlRatio` 4건 (`test_valid_positive_ratio`, `test_nan_preserved`, `test_negative_ratio_raises`, `test_all_nan_no_error`)
- [x] **S3-04 side-effect (Task 1 구현 중 발견):** `to_portfolio_kwargs`의 `sl_stop`/`tp_limit`에 `.where(signal.entries)` 마스킹 추가. 이유: Sprint 2 `_carry_bracket`이 sl_price를 non-entry bars로 carry-forward → 새 ValueError가 golden fixture(`ema_cross_atr_sltp_v5`)의 46개 non-entry bars에서 음수 ratio 감지 → 골든 테스트 실패. **Pine semantics(`strategy.exit`은 entry 시점 stop 가격)와 실제로 정합**. 수치 회귀 없이 golden expected metrics 통과 확인 (commit `5519b76`). 기존 `test_adapter_converts_sl/tp_*` 2건도 새 시맨틱에 맞게 업데이트.
- [x] **S3-03 커버리지 실측치 (전/후 %):** 91% → **91%** (fault injection 4건 추가해도 유지 — 기존 테스트가 이미 동일 분기 커버하고 있었음). 95% stretch 미달 → **Sprint 5 이관**. 미커버 라인 4개 영역:
  - `engine/__init__.py:80` — `_as_series(DataFrame)` 분기 (pf.value()가 DataFrame 반환하는 edge case)
  - `engine/__init__.py:83` — `_as_series(기타 타입)` fallback 분기
  - `engine/trades.py:40-43` — open trade (미청산 포지션) 추출 분기 (기존 fixture는 모두 closed trade만 있음)
  - `engine/trades.py:54` — pnl_pct 계산 분기 (추가 케이스 필요)

  Sprint 5에서 해당 분기 명시적으로 트리거하는 fixture/mock 구성 후 95% 달성 예정.

### 10.3 Celery 운영 관찰
- [ ] `asyncio.run()` per-task 평균 latency (task 10회 평균)
- [ ] `async_session_maker` 연결 warmup 비용 체감
- [ ] `revoke(terminate=True)` 실측 동작 (guard #1~#3 진입 빈도)
- [ ] Worker startup `reclaim_stale_running()` 반환값 (최초 기동 시 몇 건)

### 10.4 문서/CI
- [ ] Alembic round-trip 결과
- [ ] 최종 테스트 개수 + 통과 여부
- [ ] `endpoints.md` 갱신 (cancel 추가 + task_id → backtest_id)
- [ ] `docs/TODO.md` Sprint 4 완료 표시 + Sprint 5 이월 목록

### 10.5 Sprint 5 이관 목록 (구현 중 발견)

**Retroactive review (D) 에서 발견된 Important 항목 (Sprint 4 critical fix 제외, Sprint 5 backlog):**

- [ ] **Task 14**: `BacktestRepository.create()`에 `session.refresh()` 추가 (Sprint 3 `StrategyRepository.create()` 패턴과 통일). 현재는 `flush()`만 호출 — DB default/trigger 값이 즉시 반영되지 않을 수 있음.
- [ ] **Task 14**: `fail()`, `insert_trades_bulk()`, `delete()` 단위 테스트 추가 (현재 조건부 UPDATE `fail()`은 happy path만, `insert_trades_bulk`/`delete`는 미커버).
- [ ] **Task 14**: `test_complete_conditional`에 wrong-status에서 rows=0 검증 케이스 추가.
- [ ] **Task 14**: `test_list_by_user_pagination`에 offset 동작 검증 추가.
- [ ] **Task 9**: `metrics_to_jsonb()` `num_trades: int` 왜 str가 아닌지 주석 추가 (cardinality 필드, precision 필드 아님).
- [ ] **Task 9**: `equity_curve_to_jsonb()`의 `pd.Timestamp(str(ts))` → `ts.to_pydatetime()` 직접 변환으로 리팩토링 (2-hop 변환 → 1-hop).
- [ ] **Task 9**: edge case 테스트 추가 — 빈 Series, NaN, microsecond precision, 큰 Decimal 값.
- [ ] **Task 9**: `equity_curve_from_jsonb` docstring에 "DB trusted input, no validation" 명시.
- [ ] **Task 16**: `@worker_ready` signal handler의 `except Exception:` silencing 의도 주석 추가 ("stale reclaim은 best-effort; worker 계속 실행 허용").
- [ ] **Task 8**: Alembic migration의 FK 중복 인덱스 cleanup (`ix_backtests_strategy_id`, `ix_backtests_user_id`가 FK index와 중복 — PostgreSQL 자동 deduplication되나 cosmetic).
- [ ] **Task 8**: Alembic migration 인덱스 naming 일관성 (일부 `op.f()` auto-name, 일부 explicit) — explicit로 통일 권장.
- [ ] **Task 15**: CreateBacktestRequest에 tz-aware vs naive datetime validation 추가 (`_utcnow()` naive 전제 명시).

**Fixed in Sprint 4 (critical):**
- [x] **Task 14 critical bug**: `reclaim_stale()` cancelling 경로가 `started_at=NULL`(QUEUED→CANCELLING 케이스) 영영 미처리 → `created_at` 기준 fallback 추가. 회귀 테스트 `test_reclaim_stale_cancelling_with_null_started_at` 추가.

---

## 11. 리스크 & Open Issues

### 11.1 Sprint 4 리스크

| 리스크 | 확률 | 영향 | 완화 |
|--------|------|------|------|
| Celery 직렬화 회귀 (UUID/Decimal) | 중 | 고 | L4 smoke 필수 3건. Sprint 6에 pytest-celery integration 인프라 도입 |
| `asyncio.run()` + Celery pool 충돌 | 저 | 고 | **pool=prefork 고정** (§2.4). `_execute()` 내부 추가 `asyncio.run()` 금지 |
| revoke(terminate) 불안정 | 중 | 중 | 3-guard 재확인(§5.1) + 조건부 UPDATE + stale reclaim |
| Stale running (worker crash) | 중 | 중 | **Sprint 4 포함 — startup reclaim + stale 플래그**(§8.3). Beat task는 Sprint 5+ |
| Strategy FK RESTRICT로 Sprint 3 회귀 | 저 | 중 | **§4.8 — StrategyService 선조회 + 409 추가. 회귀 테스트 1건** |
| vectorbt trades 추출 난이도 | 중 | 중 | §2.6 엔진 내 `extract_trades()` + RawTrade DTO로 격리. bar index → datetime은 Service |
| 페이지네이션 계약 drift (Sprint 3 page/limit vs Sprint 4 limit/offset) | 중 | 저 | **Sprint 4는 common/pagination 고정 사용.** Sprint 3 router drift는 Open Issue로 |
| OHLCV fixture 파싱 실패 | 저 | 중 | FixtureProvider 단위 테스트 |
| Alembic migration 회귀 | 저 | 고 | CI round-trip 게이트 유지 |
| S3-03 95% 미달성 | 중 | 저 | **non-blocking 정책**(§6.2). 미커버 라인 Sprint 5 이관 |
| Cancel race 미흡 | 저 | 중 | 3-guard + transient `cancelling` 상태 + 202 cancellation_requested semantics |

### 11.2 Open Issues → Sprint 5+

1. **S3-05** (`_utcnow()` → `DateTime(timezone=True)`) — TimescaleDB hypertable 도입 전 필수. Sprint 5 첫 task
2. **Stale `running` beat cleanup** — startup reclaim은 Sprint 4 포함, 주기적 cleanup은 Sprint 5+
3. **Idempotency-Key 지원** (`POST /backtests`) — Sprint 6+
4. **Real broker integration 테스트 인프라** (pytest-celery + CI 분리 잡) — Sprint 6 Optimizer 합류 시 필수
5. **Celery eager mode 테스트** — Sprint 5 범위에서 재검토
6. **OHLCV 실데이터 (CCXT)** — Sprint 5 market_data
7. **BacktestTrade cursor pagination** — Sprint 6+ 대규모 분석 쿼리 성능 이슈 시
8. **DELETE 대량 삭제 성능** — Sprint 6+
9. **conftest Alembic-based 전환** — 현 `SQLModel.metadata.create_all()` drift 위험. Sprint 5에서 Alembic-based fixture로 전환
10. **Sprint 3 Strategy router pagination drift** (`page/limit` → `limit/offset` 통일) — Sprint 5
11. **docker-compose worker 서비스 추가** — Sprint 4는 수동 기동. Sprint 5+ compose 통합
12. **FE strategy delete UX** (archive 유도 메시지/흐름) — Sprint 5+
13. **Multi-worker split-brain reclaim** — Sprint 4는 단일 Celery master 프로세스 + prefork child 풀 전제(`docker-compose.yml`에 worker 서비스 미추가). 여러 Celery 프로세스로 수평 확장 시 `@worker_ready`가 각 프로세스에서 발동 → legit running 중인 다른 프로세스의 task를 stale로 잘못 reclaim 가능. Sprint 5+에서 `celery_app.control.inspect().active()` 체크 또는 Redis-based lock으로 보호 필요
14. **Engine float64 → Decimal 경계 문서화** — `extract_trades()`에서 Decimal-first 합산 원칙 적용. 엔진 내부 float64 연산은 boundary 전까지 유지. 향후 엔진 교체/확장 시 이 경계 규칙 재확인

---

## 12. 참고

- **선행 스프린트 spec:**
  - Sprint 1 (Pine Parser MVP): `docs/superpowers/specs/2026-04-15-pine-parser-mvp-design.md`
  - Sprint 2 (vectorbt engine + SignalResult): `docs/superpowers/specs/2026-04-15-vectorbt-signal-fill-design.md`
  - Sprint 3 (Strategy API + Clerk): `docs/superpowers/specs/2026-04-15-sprint3-strategy-api-design.md`
- **API 명세:** `docs/03_api/endpoints.md` §Backtests (본 스프린트에서 `POST /:id/cancel` 추가)
- **도메인 규칙:** `CLAUDE.md` §QuantBridge 고유 규칙 (Celery 비동기 필수, Decimal, AES-256)
- **ADR-003:** `docs/dev-log/003-pine-runtime-safety-and-parser-scope.md`
- **Backend rules:** `.ai/stacks/fastapi/backend.md` §8 비동기 장기 작업 패턴
- **선행 구현:**
  - Sprint 2 `run_backtest()`: `backend/src/backtest/engine/__init__.py`
  - Sprint 3 Strategy Repository/Service: `backend/src/strategy/{repository,service}.py`
