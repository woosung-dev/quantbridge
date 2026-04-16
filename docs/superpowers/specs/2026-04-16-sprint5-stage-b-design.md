# Sprint 5 Stage B — Infra Hardening + market_data 도메인 Design

> **상태:** Draft (2026-04-16)
> **선행:** Sprint 5 Stage A (docs 채우기) merge `7ee6ac0`, Sprint 4 PR #3 merge `777e623`
> **방법론:** `docs/guides/sprint-kickoff-template.md` (Full 2-stage review, milestone push, D1~D10)
> **관련:**
> - Sprint 4 spec §10.5 (Sprint 5 이관 목록)
> - Sprint 4 spec §11.2 (Open Issues #1, #2, #6, #9, #10, #11, #13)
> - `docs/TODO.md` §Sprint 5+ 이관

---

## 1. 컨텍스트

Sprint 4가 backtest API + Celery 비동기 파이프라인을 출시했지만, 운영 진입을 위해 다음 4가지 미해결 영역이 남아 있다.

1. **Datetime 일관성 부재 (S3-05):** asyncpg가 tz-aware datetime을 `TIMESTAMP WITHOUT TIME ZONE` 컬럼에 거부하는 문제로, 현재 `_utcnow()` workaround로 모든 datetime을 naive UTC로 강제 저장. 이는 TimescaleDB hypertable(`TIMESTAMPTZ` 전제)을 도입할 수 없는 차단 요인이며, 다중 timezone 시나리오 확장도 불가하다.

2. **Engine bar_index TypeError:** `engine/trades.py:68`에서 vectorbt가 DatetimeIndex OHLCV와 함께 사용될 때 `Entry Timestamp`를 `pd.Timestamp`로 반환하는데 `int()`로 강제 변환하여 실패. 현재 L4 smoke test가 `COMPLETED | FAILED` 둘 다 허용하며 우회 중이며, engine 정상 경로가 검증되지 않은 상태.

3. **OHLCV 실데이터 부재:** Sprint 4는 `FixtureProvider` (CSV) 기반으로만 동작. 운영 시나리오에서는 CCXT를 통한 실거래소 데이터 수집 + TimescaleDB hypertable 저장 + on-demand cache 전략이 필요. backtest 도메인이 이미 `OHLCVProvider` Protocol에 의존하므로 구현체 교체로 통합 가능.

4. **Stale reclaim + 운영 자동화:** 현재 stale 방어는 worker 기동 시 1회 reclaim만 존재. 주기적 cleanup beat task 부재. 또한 docker-compose에 worker 서비스가 없어 수동 기동이 필요하여 운영 부담 증가. 추가로 Sprint 3에서 발생한 Strategy router pagination drift (`page/limit` vs Sprint 4의 `limit/offset`)는 API contract 비일관성으로 누적 부담.

이 4가지를 4개 마일스톤으로 해결하여, 운영 진입 가능한 OHLCV 파이프라인 + 안정적인 비동기 인프라를 확보한다.

---

## 2. 완료 기준 (Go / No-Go)

모두 충족 시 Stage B 종료:

1. **M1 (Datetime + Engine):**
   - `_utcnow()` 함수 0개 잔존, 모든 DateTime 컬럼 `TIMESTAMPTZ`
   - Engine smoke 시나리오에서 `COMPLETED` 반환 + bar_index 정수값 정상
   - Pydantic schemas에서 모든 datetime 필드가 `AwareDatetime` 타입
   - Alembic upgrade head + downgrade -1 round-trip 통과
   - 기존 368+ 테스트 회귀 없음

2. **M2 (market_data Infrastructure):**
   - `ts.ohlcv` hypertable 생성 + `chunk_time_interval = INTERVAL '7 days'`
   - `Numeric(18, 8)` 컬럼 적용 + composite PK `(time, symbol, timeframe)`
   - `OHLCVRepository` CRUD + `pg_advisory_xact_lock` 동시 fetch 보호
   - Alembic migration upgrade/downgrade round-trip 통과 (hypertable drop 포함)

3. **M3 (CCXT + TimescaleProvider + 통합):**
   - `CCXTProvider` pagination + tenacity 재시도 + `exchange.timeout=30000` 구현
   - `TimescaleProvider` cache → CCXT fallback fetch + closed bar 필터
   - FastAPI `lifespan`에서 CCXTProvider singleton + 종료 시 close
   - Celery worker `worker_shutdown` signal에서 CCXTProvider close
   - `settings.ohlcv_provider: Literal["fixture", "timescale"]` config flag
   - backtest E2E: BTCUSDT 1h 1주일 → CCXT fetch → DB 저장 → backtest 실행 → COMPLETED

4. **M4 (Beat + docker-compose + Sprint 3 drift):**
   - `docker compose up` 한 번으로 worker + beat 자동 기동
   - beat가 5분 주기 reclaim task enqueue 검증 (로그)
   - Strategy router `page/limit` → `limit/offset` 통일 + 호환성 fallback 또는 deprecation 명시

5. **CI 전체 green:** ruff / mypy / pytest / alembic upgrade head 모두 통과

---

## 3. 범위 밖 (Out of Scope)

- **Idempotency-Key 지원** (`POST /backtests`) → Sprint 6+
- **Real broker integration 테스트 인프라** (pytest-celery) → Sprint 6
- **CCXT 호출 계측** (Prometheus/logfire) → Sprint 6
- **초기 backfill Celery task 분리** → Sprint 6
- **Compression / retention policy** → Sprint 6 (운영 1개월 내 합의)
- **Multi-worker split-brain Redis lock** → Sprint 6+ (현재는 단일 beat + advisory lock으로 대응)
- **FE Strategy delete UX** (archive 유도) → Sprint 5+ FE 작업
- **Task 14/19/21 Minor improvements** (BacktestRepository session.refresh, exists_for_strategy EXISTS, fixture 통합) → Sprint 6 cleanup
- **Optimizer / Trading 도메인** → Sprint 6+

---

## 4. 마일스톤별 설계

### M1 — DateTime tz-aware + bar_index Fix + Metadata Diff 검증

#### M1.1 Engine bar_index Fix (Task 1, 빠른 진전감)

**현재 (`backend/src/backtest/engine/trades.py:68`):**
```python
entry_bar_index=int(row["Entry Timestamp"]),
exit_bar_index=int(row["Exit Timestamp"]) if is_closed else None,
```

**수정:**
- `extract_trades(...)` 시그니처에 `ohlcv_index: pd.DatetimeIndex` 파라미터 추가
- 호출부 (`backend/src/backtest/engine/__init__.py`)도 함께 수정하여 `ohlcv.index`를 전달
- `int(...)` 대신 다음 패턴 사용:
  ```python
  def _resolve_bar_index(ts: Any, ohlcv_index: pd.DatetimeIndex) -> int:
      if isinstance(ts, (int, np.integer)):
          return int(ts)
      loc = ohlcv_index.get_loc(ts)
      if not isinstance(loc, (int, np.integer)):
          # 중복 timestamp 발생 — first occurrence 사용
          if isinstance(loc, slice):
              return int(loc.start)
          # ndarray (mask) — first True
          import numpy as np
          return int(np.argmax(loc))
      return int(loc)
  ```
- 호출:
  ```python
  entry_bar_index=_resolve_bar_index(row["Entry Timestamp"], ohlcv_index),
  exit_bar_index=_resolve_bar_index(row["Exit Timestamp"], ohlcv_index) if is_closed else None,
  ```

**테스트:**
- 기존 `test_run_happy_path`: `COMPLETED | FAILED` 허용 → `COMPLETED` only로 강화 + bar_index 값 검증
- `tests/backtest/engine/test_extract_trades.py` 신규: 중복 timestamp fixture로 `_resolve_bar_index` slice/ndarray 분기 커버

#### M1.2 DateTime tz-aware 전환 (S3-05)

**모델 변경 (3개 도메인 모두):**

```python
# Before
def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

class Backtest(SQLModel, table=True):
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(), nullable=False))

# After
class Backtest(SQLModel, table=True):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
```

영향 파일:
- `backend/src/auth/models.py` (User.created_at, updated_at)
- `backend/src/strategy/models.py` (Strategy.created_at, updated_at)
- `backend/src/backtest/models.py` (Backtest.created_at, started_at, completed_at; BacktestTrade.entry_time, exit_time)

**`_utcnow()` 함수 제거 (3개 모듈 모두).**

**ORM 레이어 naive 거부 가드 (Opus 검토 반영):**

`backend/src/common/datetime_types.py` 신규:
```python
from datetime import datetime, UTC
from typing import Any
from sqlalchemy import DateTime, TypeDecorator

class AwareDateTime(TypeDecorator[datetime]):
    """tz-aware datetime만 허용 (UTC 외 tz도 OK, DB는 UTC로 정규화 저장). naive datetime 입력 시 즉시 ValueError."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value)}")
        if value.tzinfo is None:
            raise ValueError(
                f"Naive datetime rejected: {value}. Use datetime.now(UTC) or AwareDatetime."
            )
        return value
```

모든 모델의 `Column(DateTime(timezone=True))` → `Column(AwareDateTime())` 교체 (강제).

**Alembic migration:**

```python
# backend/alembic/versions/YYYYMMDD_HHMM_convert_datetime_to_timestamptz.py

def upgrade() -> None:
    # users
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'")
    # strategies
    op.execute("ALTER TABLE strategies ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE strategies ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'")
    # backtests
    op.execute("ALTER TABLE backtests ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtests ALTER COLUMN started_at TYPE TIMESTAMPTZ USING started_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtests ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC'")
    # backtest_trades
    op.execute("ALTER TABLE backtest_trades ALTER COLUMN entry_time TYPE TIMESTAMPTZ USING entry_time AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtest_trades ALTER COLUMN exit_time TYPE TIMESTAMPTZ USING exit_time AT TIME ZONE 'UTC'")

def downgrade() -> None:
    # 역방향: TIMESTAMPTZ → TIMESTAMP (UTC 기준 strip)
    op.execute("ALTER TABLE backtest_trades ALTER COLUMN exit_time TYPE TIMESTAMP USING exit_time AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtest_trades ALTER COLUMN entry_time TYPE TIMESTAMP USING entry_time AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtests ALTER COLUMN completed_at TYPE TIMESTAMP USING completed_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtests ALTER COLUMN started_at TYPE TIMESTAMP USING started_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE backtests ALTER COLUMN created_at TYPE TIMESTAMP USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE strategies ALTER COLUMN updated_at TYPE TIMESTAMP USING updated_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE strategies ALTER COLUMN created_at TYPE TIMESTAMP USING created_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMP USING updated_at AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP USING created_at AT TIME ZONE 'UTC'")
```

**주석 명시:** `ALTER COLUMN TYPE TIMESTAMPTZ USING ... AT TIME ZONE 'UTC'`는 `ACCESS EXCLUSIVE` lock 사용. 현재 테이블 크기 작아 무영향이나, 향후 대용량 테이블에 동일 패턴 적용 금지 (pg_repack 등 별도 전략 필요).

#### M1.3 Pydantic Schemas tz-aware 직렬화

영향 파일: `backend/src/backtest/schemas.py`, `backend/src/strategy/schemas.py`, `backend/src/auth/schemas.py`

```python
# Before
from datetime import datetime
class BacktestSummary(BaseModel):
    created_at: datetime  # naive 허용

# After
from pydantic import AwareDatetime
class BacktestSummary(BaseModel):
    created_at: AwareDatetime  # tz-aware 강제, ISO 8601 +00:00 직렬화
```

**Task 15 (Sprint 4 이관) 처리:** `CreateBacktestRequest`의 `period_start`, `period_end`도 `AwareDatetime`으로 변경하여 client에서 tz-aware datetime 명시적 요구.

#### M1.4 utcnow() 코드베이스 전수 audit (Opus 검토 반영)

```bash
# 색출 대상
grep -rn "utcnow\|datetime.now()" backend/src --include="*.py"
```

발견되는 모든 `utcnow()` (Python 3.12 deprecated) 또는 `datetime.now()` (UTC 미명시)을 `datetime.now(UTC)`로 통일. 잠복 버그 색출 작업.

#### M1.5 Celery Task datetime 인자 audit (Opus 검토 반영)

`backend/src/tasks/backtest.py`에서 Celery task가 datetime 인자를 받지 않는지 확인. 현재는 `backtest_id: UUID`만 전달하므로 문제 없을 가능성 높음 — 명시적 검증.

#### M1.6 Metadata Diff 검증 추가 (M2 흡수분)

`backend/tests/test_migrations.py`에 추가:
```python
async def test_models_match_alembic_schema(_test_engine):
    """SQLModel.metadata와 alembic upgrade 후 실제 DB schema가 일치하는지 검증."""
    # 1. alembic upgrade head 적용된 DB의 schema dump
    # 2. SQLModel.metadata.create_all로 생성된 schema dump
    # 3. diff 비교 (sqlalchemy.schema CompareTablesGenerator 또는 단순 column dict 비교)
    # 4. 차이 발견 시 명확한 메시지로 fail
```

drift 감지가 conftest 전환 없이 round-trip + diff 두 경로로 보강됨.

---

### M2 — market_data Infrastructure (Hypertable + Repository + Advisory Lock)

#### M2.1 Infrastructure 셋업

**dependencies:**
```toml
# backend/pyproject.toml 추가
dependencies = [
    ...
    "ccxt>=4.0.0",
    "tenacity>=8.0.0",  # CCXT 재시도용 (M3에서 사용)
]
```

**docker-compose 변경:**

`docker/db/init/01-extensions.sql` 신규:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE SCHEMA IF NOT EXISTS ts;
```

`docker-compose.yml`에는 이미 `./docker/db/init:/docker-entrypoint-initdb.d:ro` 마운트 존재 (확인 완료).

**config 단순화:**
- `backend/src/core/config.py`에서 `timescale_url` 제거 (단일 DB로 통일)
- `database_url`만 사용. ts 스키마는 모델에서 명시.
- `ohlcv_provider: Literal["fixture", "timescale"] = "fixture"` 추가 (M3에서 활용)
- `default_exchange: str = "bybit"` 이미 존재
- `.env.example`: `TIMESCALE_URL` 항목 제거 (있다면), `OHLCV_PROVIDER=fixture` 기본값 추가

#### M2.2 OHLCV Hypertable 모델

`backend/src/market_data/models.py`:

```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime  # M1.2 산출물


class OHLCV(SQLModel, table=True):
    __tablename__ = "ohlcv"
    __table_args__ = (
        Index("ix_ohlcv_symbol_tf_time_desc", "symbol", "timeframe", "time"),  # 최신 캔들 조회 패턴
        {"schema": "ts"},
    )

    time: datetime = Field(
        sa_column=Column(AwareDateTime(), primary_key=True, nullable=False)
    )
    symbol: str = Field(primary_key=True, max_length=32)  # CCXT unified format: "BTC/USDT"
    timeframe: str = Field(primary_key=True, max_length=8)  # Literal["1m","5m","15m","1h","4h","1d"]
    exchange: str = Field(max_length=32, nullable=False)  # "bybit", "binance", etc.

    open: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    high: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    low: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    close: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    volume: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
```

**Index 순서 명시:** `(symbol, timeframe, time DESC)` — "특정 심볼/타임프레임의 최신 캔들 N개" 패턴 최적화.

#### M2.3 Alembic Migration

```python
# backend/alembic/versions/YYYYMMDD_HHMM_create_ohlcv_hypertable.py

from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # 1. 일반 테이블 생성
    op.create_table(
        "ohlcv",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("open", sa.Numeric(18, 8), nullable=False),
        sa.Column("high", sa.Numeric(18, 8), nullable=False),
        sa.Column("low", sa.Numeric(18, 8), nullable=False),
        sa.Column("close", sa.Numeric(18, 8), nullable=False),
        sa.Column("volume", sa.Numeric(18, 8), nullable=False),
        sa.PrimaryKeyConstraint("time", "symbol", "timeframe"),
        schema="ts",
    )
    op.create_index(
        "ix_ohlcv_symbol_tf_time_desc",
        "ohlcv",
        ["symbol", "timeframe", "time"],
        schema="ts",
    )

    # 2. hypertable 변환
    op.execute(
        "SELECT create_hypertable('ts.ohlcv', 'time', "
        "chunk_time_interval => INTERVAL '7 days', "
        "if_not_exists => TRUE);"
    )


def downgrade() -> None:
    # hypertable drop은 일반 drop_table로 가능 (TimescaleDB가 chunk 자동 정리)
    op.drop_index("ix_ohlcv_symbol_tf_time_desc", table_name="ohlcv", schema="ts")
    op.drop_table("ohlcv", schema="ts")
```

**alembic env.py 등록:**
```python
# backend/alembic/env.py 추가
from src.market_data import models as _market_data_models  # noqa: F401
```

#### M2.4 Repository

`backend/src/market_data/repository.py`:

```python
from datetime import datetime
from typing import Any
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.market_data.models import OHLCV


class OHLCVRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_range(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[OHLCV]:
        stmt = (
            select(OHLCV)
            .where(
                OHLCV.symbol == symbol,
                OHLCV.timeframe == timeframe,
                OHLCV.time >= period_start,
                OHLCV.time <= period_end,
            )
            .order_by(OHLCV.time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert_bulk(self, ohlcv_rows: list[dict[str, Any]]) -> None:
        """ON CONFLICT DO NOTHING — idempotent insert."""
        if not ohlcv_rows:
            return
        stmt = insert(OHLCV).on_conflict_do_nothing(
            index_elements=["time", "symbol", "timeframe"]
        )
        await self.session.execute(stmt, ohlcv_rows)

    async def find_gaps(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
        timeframe_seconds: int,
    ) -> list[tuple[datetime, datetime]]:
        """Postgres generate_series로 gap 추출."""
        # 가장 정확한 방법: SQL EXCEPT로 expected vs actual 비교
        sql = text(
            """
            WITH expected AS (
                SELECT generate_series(:start, :end, make_interval(secs => :tf_sec)) AS t
            ),
            missing AS (
                SELECT t FROM expected
                EXCEPT
                SELECT time FROM ts.ohlcv
                WHERE symbol = :symbol AND timeframe = :timeframe
                  AND time BETWEEN :start AND :end
            ),
            grouped AS (
                SELECT t,
                       t - (ROW_NUMBER() OVER (ORDER BY t) * make_interval(secs => :tf_sec)) AS grp
                FROM missing
            )
            SELECT MIN(t) AS gap_start, MAX(t) AS gap_end
            FROM grouped
            GROUP BY grp
            ORDER BY gap_start;
            """
        )
        result = await self.session.execute(
            sql,
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "start": period_start,
                "end": period_end,
                "tf_sec": timeframe_seconds,
            },
        )
        return [(row.gap_start, row.gap_end) for row in result.fetchall()]

    async def acquire_fetch_lock(
        self, symbol: str, timeframe: str, period_start: datetime, period_end: datetime
    ) -> None:
        """동시 fetch 방지 — pg_advisory_xact_lock (트랜잭션 종료 시 자동 해제)."""
        # hash 키 생성 (안정적인 lock key)
        key_str = f"ohlcv:{symbol}:{timeframe}:{period_start.isoformat()}:{period_end.isoformat()}"
        # PostgreSQL bigint range로 hash
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": key_str},
        )

    async def commit(self) -> None:
        await self.session.commit()
```

#### M2.5 Symbol/Timeframe 정규화

`backend/src/market_data/constants.py` 신규:

```python
from typing import Literal, get_args

Timeframe = Literal["1m", "5m", "15m", "1h", "4h", "1d"]

TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

VALID_TIMEFRAMES: frozenset[str] = frozenset(get_args(Timeframe))


def normalize_symbol(symbol: str) -> str:
    """CCXT unified format으로 정규화. 'BTCUSDT' → 'BTC/USDT'.

    이미 unified면 그대로 반환. 거래소별 변환은 CCXTProvider에서 처리.
    """
    if "/" in symbol:
        return symbol.upper()
    # 휴리스틱: USDT/USD/USDC 등 quote 자동 분리
    for quote in ("USDT", "USDC", "USD", "BTC", "ETH"):
        if symbol.upper().endswith(quote):
            base = symbol[: -len(quote)]
            return f"{base.upper()}/{quote}"
    raise ValueError(f"Cannot normalize symbol: {symbol}")
```

#### M2.6 테스트

- `tests/market_data/test_ohlcv_repository.py`:
  - `get_range` (boundary 포함/미포함)
  - `insert_bulk` ON CONFLICT (중복 row 거부)
  - `find_gaps` (전체 누락, 부분 누락, 경계 누락)
  - `acquire_fetch_lock` (동시 호출 시 두 번째가 대기 — 트랜잭션 격리 검증)
- `tests/market_data/test_constants.py`: `normalize_symbol` (unified, BTCUSDT, edge case)
- `tests/test_migrations.py`: `ts.ohlcv` hypertable 생성/drop round-trip

**중요:** market_data 테스트는 실제 PostgreSQL + TimescaleDB 필요. Docker 컨테이너 기반 fixture로 실행.

---

### M3 — CCXT + TimescaleProvider + Backtest 통합

#### M3.1 CCXTProvider

`backend/src/market_data/providers/ccxt.py`:

```python
import asyncio
import logging
from datetime import datetime, UTC
from typing import Any

import ccxt.async_support as ccxt_async
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class CCXTProvider:
    """CCXT raw OHLCV fetch — pagination + 재시도 + lifecycle 관리."""

    def __init__(self, exchange_name: str = "bybit") -> None:
        cls = getattr(ccxt_async, exchange_name)
        self.exchange = cls(
            {
                "enableRateLimit": True,
                "timeout": 30000,  # 30초 (default 10초는 pagination 중 자주 실패)
                "options": {"defaultType": "spot"},
            }
        )

    async def close(self) -> None:
        """리소스 해제 — lifespan 종료 또는 worker_shutdown에서 호출."""
        await self.exchange.close()

    @retry(
        retry=retry_if_exception_type(
            (ccxt_async.NetworkError, ccxt_async.RateLimitExceeded, ccxt_async.ExchangeNotAvailable)
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _fetch_page(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[list[float]]:
        """단일 페이지 fetch — tenacity 재시도 적용."""
        return await self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
        max_pages: int = 1000,
    ) -> list[list[float]]:
        """전체 범위 fetch — pagination cursor 전진 + 중복 제거.

        반환: [[timestamp_ms, open, high, low, close, volume], ...]
        """
        # closed bar만 — 진행 중 bar 제외
        from src.market_data.constants import TIMEFRAME_SECONDS
        tf_sec = TIMEFRAME_SECONDS[timeframe]
        now_ts = int(datetime.now(UTC).timestamp())
        last_closed_ts = (now_ts // tf_sec) * tf_sec - tf_sec
        actual_until_ms = min(int(until.timestamp() * 1000), last_closed_ts * 1000)

        since_ms = int(since.timestamp() * 1000)
        all_bars: list[list[float]] = []
        seen_timestamps: set[int] = set()
        page_count = 0
        limit = 1000  # 거래소 max (bybit 1000, binance 1000, kraken 720 등)

        while since_ms <= actual_until_ms and page_count < max_pages:
            page = await self._fetch_page(symbol, timeframe, since_ms, limit)
            if not page:
                break

            new_bars = [b for b in page if b[0] not in seen_timestamps and b[0] <= actual_until_ms]
            if not new_bars:
                break

            all_bars.extend(new_bars)
            seen_timestamps.update(b[0] for b in new_bars)

            last_ts = new_bars[-1][0]
            since_ms = last_ts + tf_sec * 1000  # 다음 페이지 cursor
            page_count += 1

            # rate limit 자체 throttle (CCXT enableRateLimit + 보수적 추가 sleep)
            await asyncio.sleep(0.1)

        if page_count >= max_pages:
            logger.warning(
                "ccxt_fetch_max_pages_reached",
                extra={"symbol": symbol, "timeframe": timeframe, "pages": page_count},
            )

        return all_bars
```

#### M3.2 TimescaleProvider

`backend/src/market_data/providers/timescale.py`:

```python
from datetime import datetime
import pandas as pd

from src.market_data.constants import TIMEFRAME_SECONDS, normalize_symbol
from src.market_data.models import OHLCV
from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.repository import OHLCVRepository


class TimescaleProvider:
    """OHLCVProvider 구현 — DB cache → CCXT fallback fetch + advisory lock."""

    def __init__(
        self,
        repo: OHLCVRepository,
        ccxt_provider: CCXTProvider,
        exchange_name: str = "bybit",
    ) -> None:
        self.repo = repo
        self.ccxt = ccxt_provider
        self.exchange_name = exchange_name

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        symbol = normalize_symbol(symbol)
        tf_sec = TIMEFRAME_SECONDS[timeframe]

        # 1. advisory lock — 동시 fetch race 방지
        await self.repo.acquire_fetch_lock(symbol, timeframe, period_start, period_end)

        # 2. lock 획득 후 cache 재확인 (다른 트랜잭션이 이미 fetch 완료했을 수 있음)
        gaps = await self.repo.find_gaps(symbol, timeframe, period_start, period_end, tf_sec)

        # 3. 빈 구간만 CCXT fetch
        for gap_start, gap_end in gaps:
            raw = await self.ccxt.fetch_ohlcv(symbol, timeframe, gap_start, gap_end)
            rows = self._to_db_rows(raw, symbol, timeframe)
            await self.repo.insert_bulk(rows)

        if gaps:
            await self.repo.commit()

        # 4. 최종 cache 조회 → DataFrame 반환
        cached = await self.repo.get_range(symbol, timeframe, period_start, period_end)
        return self._to_dataframe(cached)

    def _to_db_rows(
        self, raw: list[list[float]], symbol: str, timeframe: str
    ) -> list[dict]:
        from datetime import datetime, UTC
        return [
            {
                "time": datetime.fromtimestamp(b[0] / 1000, tz=UTC),
                "symbol": symbol,
                "timeframe": timeframe,
                "exchange": self.exchange_name,
                "open": b[1],
                "high": b[2],
                "low": b[3],
                "close": b[4],
                "volume": b[5],
            }
            for b in raw
        ]

    @staticmethod
    def _to_dataframe(rows: list[OHLCV]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume"]
            ).astype(float)
        df = pd.DataFrame(
            [
                {
                    "time": r.time,
                    "open": float(r.open),
                    "high": float(r.high),
                    "low": float(r.low),
                    "close": float(r.close),
                    "volume": float(r.volume),
                }
                for r in rows
            ]
        )
        df = df.set_index("time").sort_index()
        return df
```

#### M3.3 Lifecycle 관리

**FastAPI lifespan (singleton):**

`backend/src/main.py` 수정:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.market_data.providers.ccxt import CCXTProvider
from src.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ohlcv_provider == "timescale":
        app.state.ccxt_provider = CCXTProvider(exchange_name=settings.default_exchange)
    else:
        app.state.ccxt_provider = None
    yield
    if app.state.ccxt_provider:
        await app.state.ccxt_provider.close()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, ...)
    ...
```

**Celery worker singleton:**

`backend/src/tasks/celery_app.py` 추가:
```python
from celery.signals import worker_shutdown

_ccxt_provider: CCXTProvider | None = None

def get_ccxt_provider_for_worker() -> CCXTProvider:
    global _ccxt_provider
    if _ccxt_provider is None:
        from src.market_data.providers.ccxt import CCXTProvider
        from src.core.config import settings
        _ccxt_provider = CCXTProvider(exchange_name=settings.default_exchange)
    return _ccxt_provider

@worker_shutdown.connect
def _on_worker_shutdown(sender=None, **kwargs):
    """Worker 종료 시 CCXT 리소스 해제."""
    import asyncio
    if _ccxt_provider is not None:
        try:
            asyncio.run(_ccxt_provider.close())
        except Exception:
            logger.exception("ccxt_close_failed_on_shutdown")
```

#### M3.4 Dependency 조립

`backend/src/market_data/dependencies.py`:

```python
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.core.config import settings
from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.providers.fixture import FixtureProvider
from src.market_data.repository import OHLCVRepository


async def get_ccxt_provider(request: Request) -> CCXTProvider:
    return request.app.state.ccxt_provider


async def get_ohlcv_provider(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """Config flag로 fixture vs timescale 전환."""
    if settings.ohlcv_provider == "fixture":
        return FixtureProvider(root=settings.ohlcv_fixture_root)
    repo = OHLCVRepository(session)
    ccxt = await get_ccxt_provider(request)
    return TimescaleProvider(repo, ccxt, exchange_name=settings.default_exchange)
```

`backend/src/backtest/dependencies.py` 변경:
```python
# Before
def _ohlcv_provider() -> OHLCVProvider:
    return FixtureProvider(...)

async def get_backtest_service(...):
    return BacktestService(
        ...,
        ohlcv_provider=_ohlcv_provider(),
        ...
    )

# After
from src.market_data.dependencies import get_ohlcv_provider

async def get_backtest_service(
    ...,
    ohlcv_provider = Depends(get_ohlcv_provider),
):
    return BacktestService(
        ...,
        ohlcv_provider=ohlcv_provider,
        ...
    )
```

**Celery task에서는 Depends 사용 불가** — `tasks/backtest.py`에서 직접 조립:

```python
# backend/src/tasks/backtest.py 의 _execute() 내부
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.providers.fixture import FixtureProvider
from src.market_data.repository import OHLCVRepository

async def _execute(backtest_id: UUID) -> None:
    async with async_session_factory() as session:
        ...
        if settings.ohlcv_provider == "fixture":
            provider = FixtureProvider(root=settings.ohlcv_fixture_root)
        else:
            from src.tasks.celery_app import get_ccxt_provider_for_worker
            ccxt = get_ccxt_provider_for_worker()
            provider = TimescaleProvider(
                OHLCVRepository(session), ccxt, exchange_name=settings.default_exchange
            )
        ...
```

#### M3.5 테스트

- `tests/market_data/test_ccxt_provider.py`:
  - Mock `ccxt.async_support.bybit` (또는 `aioresponses`로 HTTP mock)
  - pagination 검증 (3 pages 이상)
  - tenacity 재시도 (NetworkError → 최대 5회 시도)
  - closed bar 필터 (현재 진행 중 candle 제외)
  - timeout 동작
- `tests/market_data/test_timescale_provider.py`:
  - Mock CCXTProvider + 실 DB
  - cache hit (CCXT 호출 없음)
  - partial cache + gap fetch
  - advisory lock (concurrent calls — second waits)
  - normalize_symbol 호출 검증
- `tests/integration/test_backtest_with_timescale.py` (신규):
  - `OHLCV_PROVIDER=timescale` env로 backtest E2E
  - Mock CCXT (실제 거래소 호출 금지) — fixture data를 CCXT response로 mock
  - submit → CCXT fetch (mock) → DB 저장 → backtest 실행 → COMPLETED 검증

#### M3.6 OHLCVProvider Protocol contract test

`tests/market_data/test_ohlcv_provider_contract.py`:
```python
import pytest
from src.market_data.providers import OHLCVProvider

@pytest.mark.parametrize("provider_factory", [
    "fixture_provider_factory",
    "timescale_provider_factory",
])
async def test_provider_returns_dataframe_with_expected_schema(provider_factory, request):
    """모든 OHLCVProvider 구현체가 동일 계약 준수."""
    factory = request.getfixturevalue(provider_factory)
    provider = factory()
    df = await provider.get_ohlcv("BTC/USDT", "1h", start, end)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert set(df.columns) >= {"open", "high", "low", "close", "volume"}
```

---

### M4 — Beat Task + Docker-compose Worker + Sprint 3 Pagination Drift

#### M4.1 Celery Beat Schedule

`backend/src/tasks/celery_app.py` 추가:

```python
celery_app.conf.beat_schedule = {
    "reclaim-stale-backtests": {
        "task": "src.tasks.backtest.reclaim_stale_running",
        "schedule": 300.0,  # 5분 주기
        "options": {
            "expires": 240,  # 4분 내 처리 안 되면 폐기 (다음 주기에서 재시도)
        },
    },
}
```

기존 `reclaim_stale_running()` 함수 재사용 (Sprint 4 D9 NULL fallback 적용된 함수).

`@worker_ready` 훅은 **유지** — beat 부재 시(예: dev 환경) 안전망 역할.

#### M4.2 Backend Dockerfile

`backend/Dockerfile` (없으면 신규):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 코드 복사
COPY . .

# 기본 명령 (worker/beat/api로 override)
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### M4.3 Docker-compose Worker + Beat 추가

`docker-compose.yml` 추가:

```yaml
backend-worker:
  build:
    context: ./backend
  container_name: quantbridge-worker
  command: uv run celery -A src.tasks.celery_app worker --loglevel=info --pool=prefork --concurrency=2
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-quantbridge}:${POSTGRES_PASSWORD:-password}@db:5432/${POSTGRES_DB:-quantbridge}
    CELERY_BROKER_URL: redis://redis:6379/1
    CELERY_RESULT_BACKEND: redis://redis:6379/2
    OHLCV_PROVIDER: ${OHLCV_PROVIDER:-fixture}
    DEFAULT_EXCHANGE: ${DEFAULT_EXCHANGE:-bybit}
  restart: unless-stopped
  networks:
    - quantbridge

backend-beat:
  build:
    context: ./backend
  container_name: quantbridge-beat
  command: uv run celery -A src.tasks.celery_app beat --loglevel=info --schedule=/data/celerybeat-schedule
  depends_on:
    redis:
      condition: service_healthy
  environment:
    CELERY_BROKER_URL: redis://redis:6379/1
    CELERY_RESULT_BACKEND: redis://redis:6379/2
  volumes:
    - beat-data:/data
  restart: unless-stopped
  networks:
    - quantbridge

volumes:
  db-data:
  redis-data:
  beat-data:
```

**단일 beat 인스턴스 보장:** `restart: unless-stopped` + 단일 컨테이너 정의. multi-beat 시 중복 schedule 발동 방지.

#### M4.4 Sprint 3 Strategy Router Pagination Drift Fix

현재 `backend/src/strategy/router.py`에서 `page` + `limit` 사용 중 (Sprint 3 시점 결정).
Sprint 4 backtest router는 `limit` + `offset` 사용 (`common/pagination.Page` 표준).

**전략:** 호환성 fallback 1단계 deprecation

```python
# backend/src/strategy/router.py
@router.get("", response_model=Page[StrategySummary])
async def list_strategies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    page: int | None = Query(None, deprecated=True, description="Deprecated: use offset"),
    ...
):
    if page is not None:
        # Deprecation: page → offset 자동 변환 + warning header
        offset = (page - 1) * limit
        # response header에 X-Deprecation 추가
    ...
```

**FE 영향:** Strategy list 호출하는 frontend 코드 grep 후 `limit/offset`으로 변경 (또는 backwards compat fallback에 의존). 호환성 fallback은 1 sprint 후 제거.

#### M4.5 테스트 환경 기본값

**conftest 정책:** 모든 unit/integration test는 `settings.ohlcv_provider = "fixture"` 강제 (CCXT 외부 호출 금지). `tests/market_data/test_timescale_provider.py` 등 명시적으로 timescale provider를 테스트하는 경우만 `settings.ohlcv_provider = "timescale"` + mock CCXT로 격리.

```python
# backend/tests/conftest.py 추가
@pytest.fixture(autouse=True)
def _force_fixture_provider(monkeypatch):
    """기본은 fixture provider — 명시적 override 시에만 timescale."""
    monkeypatch.setattr("src.core.config.settings.ohlcv_provider", "fixture")
```

#### M4.6 테스트

- `tests/tasks/test_beat_schedule.py`:
  - beat schedule 검증 (`reclaim-stale-backtests` 등록 확인)
  - schedule interval 300s 검증
- `tests/test_strategy_pagination.py` 추가:
  - 새 `limit/offset` 경로 검증
  - 기존 `page` 경로 자동 변환 검증 (deprecation 동작 확인)

---

## 5. 데이터 플로우

### 5.1 OHLCV Cache 경로 (M3 핵심)

```
Client → POST /backtests
         └─ Backtest dispatcher → Celery worker
            └─ _execute(backtest_id):
               1. async_session_factory() 컨텍스트
               2. provider = TimescaleProvider(repo, ccxt_singleton)
               3. ohlcv_df = await provider.get_ohlcv(symbol, tf, start, end)
                  ├─ acquire advisory lock (symbol+tf+range hash)
                  ├─ find_gaps via SQL generate_series + EXCEPT
                  ├─ if gaps:
                  │    for (gap_start, gap_end) in gaps:
                  │        raw = await ccxt.fetch_ohlcv(...)  # pagination 내부
                  │        await repo.insert_bulk(rows)  # ON CONFLICT DO NOTHING
                  │    await repo.commit()
                  └─ return DataFrame from cached
               4. run_backtest(strategy.source, ohlcv_df, config)  # vectorbt
               5. ... (Sprint 4 동일 경로)
```

### 5.2 Lifecycle 경로

```
FastAPI startup:
  lifespan() → app.state.ccxt_provider = CCXTProvider(...) (if timescale)

FastAPI shutdown:
  lifespan finally → await app.state.ccxt_provider.close()

Celery worker startup:
  prefork master → worker child → first task → get_ccxt_provider_for_worker() (lazy)

Celery worker shutdown:
  worker_shutdown signal → _on_worker_shutdown → asyncio.run(_ccxt_provider.close())

Celery beat startup:
  docker compose → backend-beat container → beat process → 5분마다 reclaim_stale_running enqueue
```

---

## 6. 마이그레이션 순서 (Implementation 순서)

```
M1 (10 task)
  M1.1 bar_index fix (1 task — quick win)
  M1.2 DateTime tz-aware 모델 변경 + AwareDateTime TypeDecorator
  M1.3 Pydantic schemas AwareDatetime + Task 15 (period validation)
  M1.4 utcnow audit
  M1.5 Celery datetime audit
  M1.6 Alembic migration + downgrade
  M1.7 metadata diff 검증 추가
  M1.8 기존 테스트 회귀 fix
  M1.9 신규 테스트 (bar_index, AwareDateTime)
  M1.10 milestone push + CI green

M2 (8 task)
  M2.1 ccxt + tenacity dependency + docker init SQL
  M2.2 OHLCV 모델 (Numeric(18,8) + composite PK + ts schema)
  M2.3 Alembic migration (create_hypertable + drop downgrade)
  M2.4 OHLCVRepository (get_range, insert_bulk, find_gaps SQL, advisory lock)
  M2.5 constants.py (Timeframe Literal, normalize_symbol)
  M2.6 repository 테스트
  M2.7 hypertable migration round-trip 테스트
  M2.8 milestone push + CI green

M3 (10 task)
  M3.1 CCXTProvider (pagination + tenacity + closed bar filter + timeout)
  M3.2 TimescaleProvider (cache → fetch → advisory lock 워크플로)
  M3.3 lifespan singleton + worker_shutdown
  M3.4 dependencies.py (config flag 분기)
  M3.5 backtest dependencies 통합 + Celery task 직접 조립
  M3.6 CCXTProvider 테스트 (mock CCXT)
  M3.7 TimescaleProvider 테스트 (cache hit/miss/lock)
  M3.8 Backtest E2E with TimescaleProvider (mock CCXT)
  M3.9 OHLCVProvider Protocol contract 테스트
  M3.10 milestone push + CI green

M4 (5 task)
  M4.1 Celery beat schedule + Dockerfile
  M4.2 docker-compose worker + beat 서비스
  M4.3 Strategy router pagination drift + deprecation
  M4.4 테스트 (beat schedule, pagination compat)
  M4.5 milestone push + CI green
```

---

## 7. 리스크 및 완화

| 리스크 | 영향 | 확률 | 완화 |
|--------|------|------|------|
| asyncpg + TIMESTAMPTZ 마이그레이션 후 기존 테스트 대규모 회귀 | 고 | 중 | M1.8에서 datetime 비교 패턴 grep + tz-aware로 일괄 변경. AwareDateTime TypeDecorator로 잠복 버그 즉시 catch |
| `_resolve_bar_index` 중복 timestamp/slice 처리 누락 | 중 | 저 | 명시적 타입 가드 + slice/ndarray 테스트 fixture |
| TimescaleDB hypertable 생성 시 search_path/스키마 순서 문제 | 중 | 중 | docker init SQL이 Alembic보다 먼저 실행됨을 docker-compose mount로 보장 + 통합 테스트 |
| CCXT 거래소 API 변경 (필드명 등) | 중 | 저 | CCXT unified API 사용 (거래소별 차이 흡수). exchange_name config로 전환 가능 |
| 동시 fetch race로 거래소 ban | 고 | 중 | `pg_advisory_xact_lock` + tenacity rate limit 재시도 |
| CCXTProvider lifecycle 누수 | 중 | 중 | FastAPI lifespan + worker_shutdown 둘 다 명시. 로그 기반 검증 |
| beat 중복 실행 (multi-beat) | 중 | 저 | docker-compose 단일 beat 컨테이너 명시 + spec out-of-scope로 multi-beat 금지 |
| Sprint 3 pagination drift fix가 FE 깨뜨림 | 저 | 중 | `page` → `offset` 자동 변환 fallback 1단계 유지 + deprecation header |
| 모든 작업이 1 sprint 내 완료 어려움 | 중 | 중 | M3가 가장 큼 — milestone push로 부분 진행도 main 반영 가능. 필요 시 M4를 다음 sprint로 이관 |

---

## 8. Open Issues / Sprint 6+ 이관

- **Idempotency-Key 지원** (`POST /backtests`)
- **Real broker integration 테스트 인프라** (pytest-celery)
- **CCXT 호출 계측** (Prometheus/logfire 카운터)
- **초기 backfill Celery task 분리** (1년치 등 대량 fetch)
- **Compression / retention policy** (운영 1개월 후 합의)
- **Multi-worker split-brain Redis lock** (horizontal scaling 시)
- **FE Strategy delete UX** (archive 유도)
- **Task 14/19/21 Minor improvements** (BacktestRepository session.refresh, exists_for_strategy EXISTS, fixture 통합)

---

## 9. 검증 방법 (E2E)

### 9.1 Local Dev
```bash
# 1. 인프라
docker compose up -d  # db + redis + worker + beat 모두 자동

# 2. M1 검증 — DateTime 마이그레이션
cd backend
uv run alembic upgrade head
uv run pytest tests/test_migrations.py -v
uv run pytest -k "datetime or timestamptz" -v

# 3. M2 검증 — hypertable
docker exec quantbridge-db psql -U quantbridge -c "SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'ohlcv';"

# 4. M3 검증 — CCXT + 백테스트 E2E
export OHLCV_PROVIDER=timescale
export DEFAULT_EXCHANGE=bybit
uv run pytest tests/integration/test_backtest_with_timescale.py -v

# 5. M4 검증 — beat 동작
docker logs quantbridge-beat | grep "reclaim-stale-backtests"  # 5분마다 enqueue
docker logs quantbridge-worker | grep "reclaim_stale_running"  # 실행 확인
```

### 9.2 CI (`.github/workflows/ci.yml` 영향)

기존 backend 잡에 추가:
- TimescaleDB 컨테이너 (timescale/timescaledb:2.14.2-pg15) 사용
- `alembic upgrade head` (이미 있음) — hypertable 생성 검증 포함
- `pytest tests/market_data/` 신규 추가
- `pytest --cov=src.market_data` (coverage gate 미설정, 측정만)

---

## 10. Post-Implementation Notes (작성 예정)

(Stage B 완료 후 실측 데이터 + 회귀 + 학습 사항 기록)

- [ ] M1 회귀 fix 통계 (몇 개 테스트 영향?)
- [ ] M2 hypertable 실제 row 수 + chunk 수
- [ ] M3 첫 CCXT fetch latency + cache hit ratio
- [ ] M4 beat 발동 빈도 + reclaim 통계
- [ ] CI 시간 변화 (TimescaleDB 도입 영향)
- [ ] Sprint 6+ 이관 추가 항목

---

## 변경 이력

- **2026-04-16:** 초판 작성. brainstorming 단계 외부 검토 (Opus M1 + M3) 반영. Codex 검토는 사용 한도 초과로 패스. Option C 채택 (M2 → M1 흡수, M3 분할).
