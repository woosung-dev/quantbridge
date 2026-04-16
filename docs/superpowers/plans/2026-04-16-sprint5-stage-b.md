# Sprint 5 Stage B — Infra Hardening + market_data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 4 backtest API의 운영 진입을 위한 4가지 인프라 hardening 완료 — DateTime tz-aware 복구 (S3-05), Engine bar_index fix, market_data 도메인 (TimescaleDB hypertable + CCXT on-demand cache), Celery beat + docker-compose worker 통합.

**Architecture:**
- 모델 레이어 `AwareDateTime` TypeDecorator로 naive datetime ORM 차단 + Pydantic V2 `AwareDatetime` API 경계 강제
- TimescaleDB hypertable (`ts.ohlcv` 스키마, composite PK, 7-day chunk) + Postgres `pg_advisory_xact_lock`로 동시 fetch race 방지
- CCXTProvider = FastAPI lifespan singleton (HTTP request 경로) + Celery worker lazy singleton (worker_shutdown signal로 close)
- TimescaleProvider가 OHLCVProvider Protocol 구현 → backtest 도메인 코드 변경 없이 구현체 교체
- Celery beat로 5분 주기 stale reclaim (worker_ready hook은 dev 안전망으로 유지)

**Tech Stack:**
- Backend: Python 3.12, FastAPI, SQLModel, SQLAlchemy 2.0, asyncpg, Pydantic V2, Celery 5.4+, Redis
- Market Data: CCXT 4.x (async_support), tenacity (재시도), pandas
- DB: PostgreSQL 15 + TimescaleDB 2.14 extension (single instance, ts schema 분리)
- Test: pytest + pytest-asyncio, httpx AsyncClient, mock CCXT

**Spec reference:** `docs/superpowers/specs/2026-04-16-sprint5-stage-b-design.md`

**Branch:** `feat/sprint5-stage-b` (생성 완료, main `b696a70` 기반, spec commit `721dab7`)

---

## 파일 구조 개요

### 신규 생성

```
backend/src/common/datetime_types.py             # AwareDateTime TypeDecorator
backend/src/market_data/constants.py             # Timeframe Literal + normalize_symbol
backend/src/market_data/providers/ccxt.py        # CCXTProvider
backend/src/market_data/providers/timescale.py   # TimescaleProvider

backend/alembic/versions/XXXX_convert_dt_tz.py   # M1 migration
backend/alembic/versions/XXXX_create_ohlcv.py    # M2 migration

backend/Dockerfile                                # worker/beat 컨테이너 (없으면 신규)
docker/db/init/01-extensions.sql                  # TimescaleDB extension + ts schema

backend/tests/market_data/__init__.py
backend/tests/market_data/test_constants.py
backend/tests/market_data/test_ohlcv_repository.py
backend/tests/market_data/test_ccxt_provider.py
backend/tests/market_data/test_timescale_provider.py
backend/tests/market_data/test_ohlcv_provider_contract.py
backend/tests/integration/__init__.py
backend/tests/integration/test_backtest_with_timescale.py
backend/tests/tasks/test_beat_schedule.py
backend/tests/test_strategy_pagination.py
```

### 대규모 재작성 (현재 1-line 스텁)

```
backend/src/market_data/models.py              # OHLCV hypertable
backend/src/market_data/repository.py          # OHLCVRepository
backend/src/market_data/dependencies.py        # get_ohlcv_provider DI
```

### 소규모 수정

```
backend/src/auth/models.py                     # _utcnow 제거 + AwareDateTime
backend/src/strategy/models.py                 # _utcnow 제거 + AwareDateTime
backend/src/backtest/models.py                 # _utcnow 제거 + AwareDateTime
backend/src/auth/schemas.py                    # AwareDatetime
backend/src/strategy/schemas.py                # AwareDatetime
backend/src/backtest/schemas.py                # AwareDatetime + period validation
backend/src/backtest/engine/trades.py          # _resolve_bar_index + 시그니처 변경
backend/src/backtest/engine/__init__.py        # extract_trades 호출부
backend/src/main.py                            # lifespan 추가
backend/src/tasks/celery_app.py                # beat schedule + worker_shutdown
backend/src/tasks/backtest.py                  # provider 직접 조립
backend/src/backtest/dependencies.py           # get_ohlcv_provider 통합
backend/src/strategy/router.py                 # pagination compat (M4)
backend/src/core/config.py                     # ohlcv_provider flag, timescale_url 제거
backend/src/market_data/providers/__init__.py  # Protocol 유지 (변경 최소)
backend/alembic/env.py                         # market_data import
backend/tests/conftest.py                      # _force_fixture_provider + tz-aware fix
backend/tests/test_migrations.py               # ohlcv hypertable round-trip + metadata diff
backend/pyproject.toml                         # ccxt + tenacity 추가
backend/.env.example                           # OHLCV_PROVIDER, DEFAULT_EXCHANGE
docker-compose.yml                             # backend-worker + backend-beat
docs/03_api/endpoints.md                       # market_data 통합 노트 + Strategy pagination 변경
docs/TODO.md                                   # Sprint 5 Stage B 완료 표시
```

---

## 마일스톤 구조

| Milestone | Tasks | 핵심 산출물 |
|-----------|-------|------------|
| **M1** | T1-T10 | DateTime tz-aware + bar_index fix + AwareDateTime guard + metadata diff |
| **M2** | T11-T18 | OHLCV hypertable + Repository + advisory lock |
| **M3** | T19-T28 | CCXTProvider + TimescaleProvider + lifecycle + 통합 |
| **M4** | T29-T33 | Beat + docker-compose worker + Sprint 3 pagination drift |

각 milestone 완료 후 `git push origin feat/sprint5-stage-b` + `gh pr checks` 확인.

---

# Milestone 1 — DateTime tz-aware + bar_index Fix

## Task 1: Engine bar_index Fix (Quick Win)

**Files:**
- Modify: `backend/src/backtest/engine/trades.py`
- Modify: `backend/src/backtest/engine/__init__.py`
- Test: `backend/tests/backtest/engine/test_trades_extract.py`

- [ ] **Step 1: Write failing test for `_resolve_bar_index`**

`backend/tests/backtest/engine/test_trades_extract.py`에 추가:

```python
import numpy as np
import pandas as pd
import pytest

from src.backtest.engine.trades import _resolve_bar_index


def test_resolve_bar_index_with_int():
    idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    assert _resolve_bar_index(3, idx) == 3
    assert _resolve_bar_index(np.int64(5), idx) == 5


def test_resolve_bar_index_with_timestamp():
    idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    ts = pd.Timestamp("2024-01-01 03:00:00", tz="UTC")
    assert _resolve_bar_index(ts, idx) == 3


def test_resolve_bar_index_with_duplicate_timestamp_returns_first():
    # 중복 timestamp 케이스 — get_loc이 slice 반환
    times = [
        pd.Timestamp("2024-01-01 00:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),  # duplicate
        pd.Timestamp("2024-01-01 02:00:00", tz="UTC"),
    ]
    idx = pd.DatetimeIndex(times)
    ts = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")
    assert _resolve_bar_index(ts, idx) == 1


def test_resolve_bar_index_missing_raises_keyerror():
    idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    ts = pd.Timestamp("2030-01-01", tz="UTC")
    with pytest.raises(KeyError):
        _resolve_bar_index(ts, idx)
```

- [ ] **Step 2: Run test — FAIL (function not defined)**

```bash
cd backend && uv run pytest tests/backtest/engine/test_trades_extract.py::test_resolve_bar_index_with_int -v
```

Expected: `ImportError: cannot import name '_resolve_bar_index'`.

- [ ] **Step 3: Implement `_resolve_bar_index`**

`backend/src/backtest/engine/trades.py` 상단 imports에 추가:

```python
from typing import Any
import numpy as np
import pandas as pd
```

함수 추가 (모듈 레벨, `extract_trades` 위에):

```python
def _resolve_bar_index(ts: Any, ohlcv_index: pd.DatetimeIndex) -> int:
    """vectorbt timestamp → ohlcv index position. 중복 timestamp 시 first occurrence 반환."""
    if isinstance(ts, (int, np.integer)):
        return int(ts)
    loc = ohlcv_index.get_loc(ts)
    if isinstance(loc, (int, np.integer)):
        return int(loc)
    if isinstance(loc, slice):
        return int(loc.start)
    if isinstance(loc, np.ndarray):
        # bool mask
        return int(np.argmax(loc))
    raise TypeError(f"Unexpected get_loc return type: {type(loc)}")
```

- [ ] **Step 4: Update `extract_trades` signature + 호출**

`backend/src/backtest/engine/trades.py`의 `extract_trades` 함수 시그니처 변경:

```python
def extract_trades(
    pf: Any,
    ohlcv_index: pd.DatetimeIndex,
) -> list[RawTrade]:
    """vectorbt Portfolio.trades.records_readable → RawTrade list."""
    raw_trades: list[RawTrade] = []
    if not hasattr(pf, "trades") or pf.trades is None:
        return raw_trades

    records = pf.trades.records_readable
    if records is None or len(records) == 0:
        return raw_trades

    for _, row in records.iterrows():
        # ... 기존 로직 (status, direction 등) ...

        raw_trades.append(
            RawTrade(
                trade_index=int(row["Exit Trade Id"]),
                direction=direction,
                status=status,
                entry_bar_index=_resolve_bar_index(row["Entry Timestamp"], ohlcv_index),
                exit_bar_index=_resolve_bar_index(row["Exit Timestamp"], ohlcv_index) if is_closed else None,
                # ... 나머지 동일 ...
            )
        )

    return raw_trades
```

- [ ] **Step 5: Update caller in `engine/__init__.py`**

`backend/src/backtest/engine/__init__.py`에서 `extract_trades(pf)` 호출 부분 찾아서:

```python
# Before
trades = extract_trades(pf)

# After
trades = extract_trades(pf, ohlcv.index)
```

- [ ] **Step 6: Run all tests — verify no regression**

```bash
cd backend && uv run pytest tests/backtest/engine/ -v
```

Expected: 모든 기존 테스트 + 신규 4건 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/backtest/engine/trades.py backend/src/backtest/engine/__init__.py backend/tests/backtest/engine/test_trades_extract.py
git commit -m "$(cat <<'EOF'
fix(engine): bar_index TypeError 수정 — _resolve_bar_index helper 도입

vectorbt가 DatetimeIndex OHLCV에서 Timestamp 반환하는 케이스를
ohlcv.index.get_loc()로 해결. 중복 timestamp slice/ndarray 가드 포함.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: AwareDateTime TypeDecorator 신규 작성

**Files:**
- Create: `backend/src/common/datetime_types.py`
- Test: `backend/tests/common/test_datetime_types.py`

- [ ] **Step 1: Write failing test**

`backend/tests/common/__init__.py` (없으면 빈 파일 생성).

`backend/tests/common/test_datetime_types.py`:

```python
from datetime import UTC, datetime, timezone

import pytest

from src.common.datetime_types import AwareDateTime


class FakeDialect:
    pass


def test_aware_datetime_accepts_utc_aware():
    decorator = AwareDateTime()
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    assert decorator.process_bind_param(ts, FakeDialect()) == ts


def test_aware_datetime_accepts_other_tz():
    decorator = AwareDateTime()
    kst = timezone.utc  # 어떤 tz든 OK (DB에는 UTC로 변환되어 저장)
    ts = datetime(2024, 1, 1, tzinfo=kst)
    assert decorator.process_bind_param(ts, FakeDialect()) == ts


def test_aware_datetime_rejects_naive():
    decorator = AwareDateTime()
    naive = datetime(2024, 1, 1)
    with pytest.raises(ValueError, match="Naive datetime rejected"):
        decorator.process_bind_param(naive, FakeDialect())


def test_aware_datetime_passes_none():
    decorator = AwareDateTime()
    assert decorator.process_bind_param(None, FakeDialect()) is None


def test_aware_datetime_rejects_non_datetime():
    decorator = AwareDateTime()
    with pytest.raises(TypeError, match="Expected datetime"):
        decorator.process_bind_param("2024-01-01", FakeDialect())
```

- [ ] **Step 2: Run test — FAIL**

```bash
cd backend && uv run pytest tests/common/test_datetime_types.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `AwareDateTime`**

`backend/src/common/datetime_types.py`:

```python
"""Custom SQLAlchemy types — naive datetime을 ORM 레이어에서 거부."""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class AwareDateTime(TypeDecorator[datetime]):
    """tz-aware datetime만 허용. naive 입력 시 즉시 ValueError.

    PostgreSQL TIMESTAMPTZ로 매핑. asyncpg가 자동으로 tz-aware datetime 반환.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: Any, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        if value.tzinfo is None:
            raise ValueError(
                f"Naive datetime rejected: {value}. "
                "Use datetime.now(UTC) or attach tzinfo."
            )
        return value
```

- [ ] **Step 4: Run test — PASS**

```bash
cd backend && uv run pytest tests/common/test_datetime_types.py -v
```

Expected: 5건 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/common/datetime_types.py backend/tests/common/
git commit -m "feat(common): AwareDateTime TypeDecorator — naive datetime ORM 차단"
```

---

## Task 3: 도메인 모델 — `_utcnow` 제거 + AwareDateTime 적용

**Files:**
- Modify: `backend/src/auth/models.py`
- Modify: `backend/src/strategy/models.py`
- Modify: `backend/src/backtest/models.py`

- [ ] **Step 1: auth/models.py 변경**

`backend/src/auth/models.py`에서 `_utcnow()` 함수 제거. `Column(DateTime(timezone=True), ...)` → `Column(AwareDateTime(), ...)` 교체.

```python
# 상단 imports
from datetime import UTC, datetime
from src.common.datetime_types import AwareDateTime

# _utcnow 함수 삭제

# Field 변경 예
created_at: datetime = Field(
    default_factory=lambda: datetime.now(UTC),
    sa_column=Column(AwareDateTime(), nullable=False),
)
updated_at: datetime = Field(
    default_factory=lambda: datetime.now(UTC),
    sa_column=Column(AwareDateTime(), nullable=False, onupdate=lambda: datetime.now(UTC)),
)
```

- [ ] **Step 2: strategy/models.py 변경 (동일 패턴)**

`backend/src/strategy/models.py`에 동일하게 적용. `_utcnow` 함수 삭제, `Column(DateTime(...))` → `Column(AwareDateTime())`, `default_factory=lambda: datetime.now(UTC)`.

- [ ] **Step 3: backtest/models.py 변경**

`backend/src/backtest/models.py`에 동일 적용. 영향 컬럼: `Backtest.created_at`, `started_at`, `completed_at`; `BacktestTrade.entry_time`, `exit_time`.

`_utcnow` 함수 + 주석 (line 17-22) 삭제.

- [ ] **Step 4: 테스트 실행 — 회귀 확인 (실패 예상)**

```bash
cd backend && uv run pytest -x --tb=short 2>&1 | head -80
```

Expected: 다수 datetime 비교 테스트 실패 (naive vs tz-aware). 다음 task에서 수정.

- [ ] **Step 5: Commit (테스트 fail 상태로 커밋)**

```bash
git add backend/src/auth/models.py backend/src/strategy/models.py backend/src/backtest/models.py
git commit -m "feat(models): _utcnow 제거 + AwareDateTime 적용 (S3-05)

Sprint 4 임시 workaround 제거. 모든 datetime 컬럼이 TIMESTAMPTZ로 매핑.
다음 commit에서 Alembic migration + 테스트 회귀 fix.
"
```

---

## Task 4: Alembic Migration — DateTime → TIMESTAMPTZ

**Files:**
- Create: `backend/alembic/versions/YYYYMMDD_HHMM_convert_datetime_to_timestamptz.py`

- [ ] **Step 1: Generate migration skeleton**

```bash
cd backend && uv run alembic revision -m "convert_datetime_to_timestamptz"
```

생성된 파일을 spec §M1.2 코드로 채움.

- [ ] **Step 2: Write upgrade**

```python
"""convert datetime to timestamptz

Revision ID: <auto>
Revises: <previous>
Create Date: <auto>
"""
from alembic import op


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

상단에 주석 추가:

```python
"""WARNING: ALTER COLUMN TYPE TIMESTAMPTZ는 ACCESS EXCLUSIVE lock 사용.
현재 테이블은 작아서 무영향. 향후 대용량 테이블에 동일 패턴 적용 금지 (pg_repack 등 별도 전략 필요).
"""
```

- [ ] **Step 3: Apply migration locally**

```bash
docker compose up -d db redis
cd backend && uv run alembic upgrade head
```

Expected: success, 새 migration revision 적용.

- [ ] **Step 4: Test round-trip**

```bash
cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head
```

Expected: 양방향 success.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(alembic): TIMESTAMPTZ migration — 9 컬럼 ALTER COLUMN TYPE"
```

---

## Task 5: Pydantic Schemas — `AwareDatetime` 적용

**Files:**
- Modify: `backend/src/auth/schemas.py`
- Modify: `backend/src/strategy/schemas.py`
- Modify: `backend/src/backtest/schemas.py`

- [ ] **Step 1: auth/schemas.py 변경**

`backend/src/auth/schemas.py`에서 모든 `datetime` 필드를 `AwareDatetime`으로 교체:

```python
from pydantic import AwareDatetime, BaseModel

class CurrentUser(BaseModel):
    ...
    created_at: AwareDatetime  # was: datetime
    updated_at: AwareDatetime
```

- [ ] **Step 2: strategy/schemas.py 변경**

`backend/src/strategy/schemas.py` 동일 적용.

- [ ] **Step 3: backtest/schemas.py 변경**

`backend/src/backtest/schemas.py` 동일 적용. 추가로:

`CreateBacktestRequest`의 `period_start`, `period_end`도 `AwareDatetime`으로 변경 (Task 15 흡수):

```python
class CreateBacktestRequest(BaseModel):
    strategy_id: UUID
    symbol: str = Field(min_length=3, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    period_start: AwareDatetime  # was: datetime
    period_end: AwareDatetime
    initial_capital: Decimal = Field(...)

    @model_validator(mode="after")
    def _validate_period(self) -> Self:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self
```

- [ ] **Step 4: Run schema tests**

```bash
cd backend && uv run pytest tests/auth/ tests/strategy/ tests/backtest/test_schemas.py -v 2>&1 | tail -30
```

Expected: 일부 datetime 비교 테스트 fail (다음 task에서 fix).

- [ ] **Step 5: Commit**

```bash
git add backend/src/auth/schemas.py backend/src/strategy/schemas.py backend/src/backtest/schemas.py
git commit -m "feat(schemas): AwareDatetime 적용 + period validation tz-aware (Task 15 흡수)"
```

---

## Task 6: utcnow() 코드베이스 전수 audit

**Files:**
- Audit: `backend/src/**/*.py`

- [ ] **Step 1: grep for offending patterns**

```bash
cd backend && grep -rn "utcnow()\|datetime\.now()" src --include="*.py" | grep -v "datetime.now(UTC)"
```

Expected: zero hits. 발견 시 다음 step에서 수정.

- [ ] **Step 2: Fix any matches found**

각 발견 site를 `datetime.now(UTC)`로 통일. import에 `from datetime import UTC, datetime` 확인.

- [ ] **Step 3: Re-run grep — confirm zero**

Step 1 명령 재실행. zero matches 확인.

- [ ] **Step 4: Commit (변경이 있을 경우만)**

변경 없으면 skip. 변경 있으면:

```bash
git add backend/src/
git commit -m "fix: utcnow() / datetime.now() audit — UTC 명시 통일"
```

---

## Task 7: Celery task datetime 인자 audit

**Files:**
- Audit: `backend/src/tasks/*.py`

- [ ] **Step 1: Inspect Celery task signatures**

```bash
cd backend && grep -rn "@celery_app.task\|@app.task" src/tasks/
```

각 task 함수 시그니처 확인. datetime 타입 인자가 있는지 점검.

- [ ] **Step 2: Confirm no datetime args in current tasks**

`run_backtest_task(backtest_id: UUID)`, `reclaim_stale_running()` — 둘 다 datetime 인자 없음 (예상). 

발견 시: ISO string으로 직렬화 + 함수 내부에서 `datetime.fromisoformat()`.

- [ ] **Step 3: Document audit result in commit message (no code change)**

변경 없으면 commit skip. 단, plan trail 위해:

```bash
git commit --allow-empty -m "audit(tasks): Celery task datetime 인자 점검 — 현재 task 모두 안전"
```

또는 변경 있으면 적용 후 commit.

---

## Task 8: 테스트 회귀 fix — datetime 비교 패턴

**Files:**
- Modify: `backend/tests/**/*.py` (다수)

- [ ] **Step 1: Run full test suite, capture failures**

```bash
cd backend && uv run pytest 2>&1 | grep -E "FAILED|ERROR" | head -50
```

Expected: datetime 관련 실패 다수.

- [ ] **Step 2: Common fix patterns**

발견되는 패턴별 수정:

1. **Naive datetime literal:** `datetime(2024, 1, 1)` → `datetime(2024, 1, 1, tzinfo=UTC)`
2. **Comparison:** `assert obj.created_at == datetime(2024,1,1)` → tz-aware로 통일
3. **JSON snapshot:** `"2024-01-01T00:00:00"` → `"2024-01-01T00:00:00Z"` 또는 `"+00:00"`
4. **Fixture creation:** test fixture에서 model 생성 시 `datetime.now(UTC)` 명시

- [ ] **Step 3: Iterate until all green**

```bash
cd backend && uv run pytest -x 2>&1 | tail -30
```

각 fail마다 fix 후 재실행.

- [ ] **Step 4: Final full suite**

```bash
cd backend && uv run pytest -v --tb=short 2>&1 | tail -10
```

Expected: 368+ tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/
git commit -m "test: datetime 비교 패턴 tz-aware 통일 — 368+ 테스트 회귀 fix"
```

---

## Task 9: Metadata Diff 검증 추가

**Files:**
- Modify: `backend/tests/test_migrations.py`

- [ ] **Step 1: Read current test_migrations.py**

```bash
cd backend && cat tests/test_migrations.py
```

- [ ] **Step 2: Add metadata diff test**

`backend/tests/test_migrations.py`에 추가:

```python
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# 모델 import (metadata 등록)
from src.auth.models import User  # noqa: F401
from src.strategy.models import Strategy  # noqa: F401
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401


@pytest.mark.asyncio
async def test_alembic_schema_matches_sqlmodel_metadata():
    """alembic upgrade 후 실제 schema와 SQLModel.metadata가 일치하는지 검증."""
    # Alembic이 만든 schema dump (이미 _test_engine fixture에서 적용)
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        alembic_tables = await conn.run_sync(
            lambda sync_conn: {
                t: {c["name"]: str(c["type"]) for c in inspect(sync_conn).get_columns(t)}
                for t in inspect(sync_conn).get_table_names()
            }
        )

    # SQLModel metadata가 만들어야 할 schema
    metadata_tables = {
        t.name: {c.name: str(c.type) for c in t.columns}
        for t in SQLModel.metadata.tables.values()
    }

    # alembic_version 테이블 제외
    alembic_tables.pop("alembic_version", None)

    # 핵심 컬럼 누락 검증 (정확한 type 비교는 PostgreSQL ↔ Python type 차이로 어려움)
    for table_name, metadata_cols in metadata_tables.items():
        assert table_name in alembic_tables, f"Table {table_name} missing in alembic schema"
        alembic_cols = alembic_tables[table_name]
        for col_name in metadata_cols:
            assert col_name in alembic_cols, f"{table_name}.{col_name} missing in alembic"

    await engine.dispose()
```

- [ ] **Step 3: Run new test**

```bash
cd backend && uv run pytest tests/test_migrations.py::test_alembic_schema_matches_sqlmodel_metadata -v
```

Expected: PASS (M1 migration 후라면 일치).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_migrations.py
git commit -m "test(migrations): metadata diff 검증 추가 — alembic vs SQLModel schema drift 감지"
```

---

## Task 10: M1 Milestone Push + CI

- [ ] **Step 1: Final test pass**

```bash
cd backend && uv run pytest -v 2>&1 | tail -5
cd backend && uv run ruff check .
cd backend && uv run mypy src/
```

모두 green 확인.

- [ ] **Step 2: Push branch**

```bash
git push -u origin feat/sprint5-stage-b
```

- [ ] **Step 3: Create draft PR**

```bash
gh pr create --draft --title "[WIP] Sprint 5 Stage B — Infra Hardening + market_data" --body "$(cat <<'EOF'
## Summary

Sprint 5 Stage B 구현 (M1-M4).

### Milestone 진행

- [x] **M1** — DateTime tz-aware + bar_index fix + AwareDateTime guard + metadata diff
- [ ] **M2** — market_data infra (TimescaleDB hypertable + Repository + advisory lock)
- [ ] **M3** — CCXT + TimescaleProvider + lifecycle + backtest 통합
- [ ] **M4** — Beat schedule + docker-compose worker + Sprint 3 pagination drift fix

## Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-16-sprint5-stage-b-design.md`
- Plan: `docs/superpowers/plans/2026-04-16-sprint5-stage-b.md`

## Test Plan

- [ ] M1: 368+ 기존 테스트 + AwareDateTime + bar_index 신규 테스트 모두 PASS
- [ ] M2: ts.ohlcv hypertable 생성 + Repository CRUD + advisory lock 테스트
- [ ] M3: CCXTProvider mock + TimescaleProvider cache hit/miss + backtest E2E
- [ ] M4: docker compose up + beat 5분 주기 + Strategy pagination compat

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 4: Wait for CI checks**

```bash
sleep 30
gh pr checks
```

Expected: 모든 잡 green. 실패 시 즉시 fix.

---

# Milestone 2 — market_data Infrastructure

## Task 11: Dependencies — ccxt + tenacity 추가

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add to pyproject.toml**

`backend/pyproject.toml`의 `dependencies` 섹션에 추가:

```toml
dependencies = [
    # ... existing ...
    "ccxt>=4.0.0",
    "tenacity>=8.0.0",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
cd backend && uv sync
```

Expected: ccxt + tenacity 설치 success.

- [ ] **Step 3: Verify imports**

```bash
cd backend && uv run python -c "import ccxt.async_support; import tenacity; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(deps): ccxt 4.0+ + tenacity 8.0+ 추가 (M2 prep)"
```

---

## Task 12: Docker Init SQL — TimescaleDB extension + ts schema

**Files:**
- Create: `docker/db/init/01-extensions.sql`

- [ ] **Step 1: Create init SQL**

`docker/db/init/01-extensions.sql`:

```sql
-- TimescaleDB extension (필수: 항상 public 스키마에 설치)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 시계열 데이터용 별도 스키마 (일반 테이블과 격리)
CREATE SCHEMA IF NOT EXISTS ts;
```

- [ ] **Step 2: Recreate db container to apply init**

```bash
docker compose down -v db  # volume 제거 (init은 fresh DB에만 실행)
docker compose up -d db
sleep 5
```

- [ ] **Step 3: Verify**

```bash
docker exec quantbridge-db psql -U quantbridge -c "SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';"
docker exec quantbridge-db psql -U quantbridge -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name='ts';"
```

Expected: timescaledb 2.14.x extension + ts schema 존재.

- [ ] **Step 4: Reapply migrations**

```bash
cd backend && uv run alembic upgrade head
```

- [ ] **Step 5: Commit**

```bash
git add docker/db/init/
git commit -m "feat(infra): TimescaleDB extension + ts schema init SQL"
```

---

## Task 13: market_data — constants.py (Timeframe + normalize_symbol)

**Files:**
- Create: `backend/src/market_data/constants.py`
- Test: `backend/tests/market_data/test_constants.py`

- [ ] **Step 1: Write failing test**

`backend/tests/market_data/__init__.py` 생성 (빈 파일).

`backend/tests/market_data/test_constants.py`:

```python
import pytest

from src.market_data.constants import (
    TIMEFRAME_SECONDS,
    VALID_TIMEFRAMES,
    normalize_symbol,
)


def test_valid_timeframes():
    assert VALID_TIMEFRAMES == frozenset({"1m", "5m", "15m", "1h", "4h", "1d"})


def test_timeframe_seconds_consistency():
    assert TIMEFRAME_SECONDS["1m"] == 60
    assert TIMEFRAME_SECONDS["1h"] == 3600
    assert TIMEFRAME_SECONDS["1d"] == 86400


def test_normalize_symbol_already_unified():
    assert normalize_symbol("BTC/USDT") == "BTC/USDT"
    assert normalize_symbol("eth/usdt") == "ETH/USDT"


def test_normalize_symbol_concatenated():
    assert normalize_symbol("BTCUSDT") == "BTC/USDT"
    assert normalize_symbol("ETHUSDC") == "ETH/USDC"
    assert normalize_symbol("SOLUSD") == "SOL/USD"


def test_normalize_symbol_invalid():
    with pytest.raises(ValueError, match="Cannot normalize"):
        normalize_symbol("BTC")
```

- [ ] **Step 2: Run test — FAIL**

```bash
cd backend && uv run pytest tests/market_data/test_constants.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement constants.py**

`backend/src/market_data/constants.py`:

```python
"""market_data 도메인 상수 — Timeframe enum + Symbol 정규화."""
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

    이미 unified면 그대로 (대문자 변환).
    """
    if "/" in symbol:
        return symbol.upper()
    upper = symbol.upper()
    for quote in ("USDT", "USDC", "USD", "BTC", "ETH"):
        if upper.endswith(quote):
            base = upper[: -len(quote)]
            if base:
                return f"{base}/{quote}"
    raise ValueError(f"Cannot normalize symbol: {symbol}")
```

- [ ] **Step 4: Run test — PASS**

```bash
cd backend && uv run pytest tests/market_data/test_constants.py -v
```

Expected: 5건 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/market_data/constants.py backend/tests/market_data/
git commit -m "feat(market_data): Timeframe Literal + normalize_symbol util"
```

---

## Task 14: market_data Models — OHLCV Hypertable

**Files:**
- Modify: `backend/src/market_data/models.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Replace stub with OHLCV model**

`backend/src/market_data/models.py`:

```python
"""market_data 도메인 SQLModel — OHLCV TimescaleDB hypertable."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class OHLCV(SQLModel, table=True):
    """OHLCV bar — TimescaleDB hypertable (ts.ohlcv).

    PK: (time, symbol, timeframe) — TimescaleDB는 모든 UNIQUE 제약에 partition key 포함 요구.
    """

    __tablename__ = "ohlcv"
    __table_args__ = (
        # 보조 인덱스 — 최신 캔들 조회 패턴 최적화
        Index("ix_ohlcv_symbol_tf_time_desc", "symbol", "timeframe", "time"),
        {"schema": "ts"},
    )

    time: datetime = Field(
        sa_column=Column(AwareDateTime(), primary_key=True, nullable=False)
    )
    symbol: str = Field(primary_key=True, max_length=32)
    timeframe: str = Field(primary_key=True, max_length=8)
    exchange: str = Field(max_length=32, nullable=False)

    open: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    high: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    low: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    close: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    volume: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
```

- [ ] **Step 2: Register in alembic env.py**

`backend/alembic/env.py`의 model imports 섹션에 추가:

```python
from src.market_data import models as _market_data_models  # noqa: F401
```

- [ ] **Step 3: Verify import**

```bash
cd backend && uv run python -c "from src.market_data.models import OHLCV; print(OHLCV.__tablename__, OHLCV.__table_args__)"
```

Expected: `ohlcv (Index..., {'schema': 'ts'})`.

- [ ] **Step 4: Commit**

```bash
git add backend/src/market_data/models.py backend/alembic/env.py
git commit -m "feat(market_data): OHLCV hypertable model — Numeric(18,8) + composite PK + ts schema"
```

---

## Task 15: Alembic Migration — create ohlcv hypertable

**Files:**
- Create: `backend/alembic/versions/YYYYMMDD_HHMM_create_ohlcv_hypertable.py`

- [ ] **Step 1: Generate migration**

```bash
cd backend && uv run alembic revision -m "create_ohlcv_hypertable"
```

생성된 파일을 다음으로 교체:

```python
"""create ohlcv hypertable

Revision ID: <auto>
Revises: <previous>
Create Date: <auto>
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # 1. 일반 테이블 생성 (ts schema)
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

    # 2. hypertable 변환 — chunk 7일 단위
    op.execute(
        "SELECT create_hypertable('ts.ohlcv', 'time', "
        "chunk_time_interval => INTERVAL '7 days', "
        "if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.drop_index("ix_ohlcv_symbol_tf_time_desc", table_name="ohlcv", schema="ts")
    op.drop_table("ohlcv", schema="ts")
```

- [ ] **Step 2: Apply migration**

```bash
cd backend && uv run alembic upgrade head
```

Expected: success.

- [ ] **Step 3: Verify hypertable**

```bash
docker exec quantbridge-db psql -U quantbridge -c "SELECT hypertable_schema, hypertable_name, num_chunks FROM timescaledb_information.hypertables WHERE hypertable_name='ohlcv';"
```

Expected: `ts | ohlcv | 0` (0 chunks 초기 상태).

- [ ] **Step 4: Test round-trip**

```bash
cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head
```

Expected: 양방향 success.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(alembic): ts.ohlcv hypertable migration — 7-day chunk + composite PK"
```

---

## Task 16: OHLCVRepository

**Files:**
- Modify: `backend/src/market_data/repository.py`
- Test: `backend/tests/market_data/test_ohlcv_repository.py`

- [ ] **Step 1: Write failing test**

`backend/tests/market_data/test_ohlcv_repository.py`:

```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.market_data.repository import OHLCVRepository


@pytest.mark.asyncio
async def test_insert_bulk_and_get_range(db_session: AsyncSession):
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        {
            "time": base + timedelta(hours=i),
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "exchange": "bybit",
            "open": Decimal("40000.0"),
            "high": Decimal("41000.0"),
            "low": Decimal("39000.0"),
            "close": Decimal("40500.0"),
            "volume": Decimal("100.0"),
        }
        for i in range(5)
    ]
    await repo.insert_bulk(rows)
    await repo.commit()

    fetched = await repo.get_range("BTC/USDT", "1h", base, base + timedelta(hours=4))
    assert len(fetched) == 5
    assert fetched[0].time == base


@pytest.mark.asyncio
async def test_insert_bulk_on_conflict_do_nothing(db_session: AsyncSession):
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    row = {
        "time": base,
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "exchange": "bybit",
        "open": Decimal("40000"),
        "high": Decimal("40000"),
        "low": Decimal("40000"),
        "close": Decimal("40000"),
        "volume": Decimal("1"),
    }
    await repo.insert_bulk([row])
    await repo.commit()
    # 두 번째 insert — 중복, ON CONFLICT DO NOTHING으로 silently skip
    await repo.insert_bulk([row])
    await repo.commit()

    fetched = await repo.get_range("BTC/USDT", "1h", base, base + timedelta(hours=1))
    assert len(fetched) == 1


@pytest.mark.asyncio
async def test_find_gaps_full_missing(db_session: AsyncSession):
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    gaps = await repo.find_gaps("BTC/USDT", "1h", base, base + timedelta(hours=4), 3600)
    # 전체 누락 → 1개의 큰 gap
    assert len(gaps) == 1
    assert gaps[0][0] == base
```

- [ ] **Step 2: Run test — FAIL**

```bash
cd backend && uv run pytest tests/market_data/test_ohlcv_repository.py -v
```

Expected: ImportError or method not implemented.

- [ ] **Step 3: Implement Repository**

`backend/src/market_data/repository.py`:

```python
"""OHLCV Repository — TimescaleDB hypertable 접근."""
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
                OHLCV.symbol == symbol,  # type: ignore[arg-type]
                OHLCV.timeframe == timeframe,  # type: ignore[arg-type]
                OHLCV.time >= period_start,  # type: ignore[arg-type, operator]
                OHLCV.time <= period_end,  # type: ignore[arg-type, operator]
            )
            .order_by(OHLCV.time)  # type: ignore[arg-type]
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
        """Postgres generate_series로 expected vs actual gap 추출."""
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
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """동시 fetch race 방지 — pg_advisory_xact_lock (트랜잭션 종료 시 자동 해제)."""
        key = f"ohlcv:{symbol}:{timeframe}:{period_start.isoformat()}:{period_end.isoformat()}"
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": key},
        )

    async def commit(self) -> None:
        await self.session.commit()
```

- [ ] **Step 4: Run test — PASS**

```bash
cd backend && uv run pytest tests/market_data/test_ohlcv_repository.py -v
```

Expected: 3건 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/market_data/repository.py backend/tests/market_data/test_ohlcv_repository.py
git commit -m "feat(market_data): OHLCVRepository — get_range + insert_bulk + find_gaps + advisory_lock"
```

---

## Task 17: Advisory Lock 동시성 테스트

**Files:**
- Modify: `backend/tests/market_data/test_ohlcv_repository.py`

- [ ] **Step 1: Add concurrency test**

`backend/tests/market_data/test_ohlcv_repository.py`에 추가:

```python
import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.mark.asyncio
async def test_acquire_fetch_lock_blocks_concurrent_call(_test_engine):
    """첫 번째 lock holder가 트랜잭션 commit/rollback 전까지 두 번째는 대기."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    completed_order: list[str] = []

    async def first_lock_holder():
        async with _test_engine.connect() as conn:
            tx = await conn.begin()
            session = async_sessionmaker(bind=conn, expire_on_commit=False)()
            repo = OHLCVRepository(session)
            await repo.acquire_fetch_lock("BTC/USDT", "1h", base, base + timedelta(hours=1))
            completed_order.append("first_acquired")
            await asyncio.sleep(0.5)  # hold the lock
            await tx.commit()
            completed_order.append("first_released")

    async def second_lock_holder():
        await asyncio.sleep(0.1)  # ensure first goes first
        async with _test_engine.connect() as conn:
            tx = await conn.begin()
            session = async_sessionmaker(bind=conn, expire_on_commit=False)()
            repo = OHLCVRepository(session)
            await repo.acquire_fetch_lock("BTC/USDT", "1h", base, base + timedelta(hours=1))
            completed_order.append("second_acquired")
            await tx.commit()

    await asyncio.gather(first_lock_holder(), second_lock_holder())

    assert completed_order == ["first_acquired", "first_released", "second_acquired"]
```

- [ ] **Step 2: Run test**

```bash
cd backend && uv run pytest tests/market_data/test_ohlcv_repository.py::test_acquire_fetch_lock_blocks_concurrent_call -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/market_data/test_ohlcv_repository.py
git commit -m "test(market_data): advisory_lock 동시성 검증 (lock holder 순서 보장)"
```

---

## Task 18: M2 Milestone Push + CI

- [ ] **Step 1: Final test pass**

```bash
cd backend && uv run pytest -v 2>&1 | tail -10
cd backend && uv run ruff check . && uv run mypy src/
```

- [ ] **Step 2: Update PR description M2 checkbox**

```bash
gh pr edit --body "$(gh pr view --json body -q .body | sed 's/- \[ \] \*\*M2\*\*/- [x] **M2**/')"
```

- [ ] **Step 3: Push + check CI**

```bash
git push
sleep 30
gh pr checks
```

Expected: 모든 잡 green.

---

# Milestone 3 — CCXT + TimescaleProvider + Backtest 통합

## Task 19: Config — ohlcv_provider flag 추가

**Files:**
- Modify: `backend/src/core/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add ohlcv_provider flag**

`backend/src/core/config.py`의 `Settings` 클래스에 추가:

```python
from typing import Literal

class Settings(BaseSettings):
    # ... existing ...
    ohlcv_provider: Literal["fixture", "timescale"] = "fixture"
    default_exchange: str = "bybit"

    # timescale_url 제거 (단일 DB로 통일) — 이미 있는 경우만
```

기존에 `timescale_url` 필드 있으면 제거. database_url로 통일.

- [ ] **Step 2: Update .env.example**

`backend/.env.example`에 추가:

```bash
# OHLCV 데이터 소스: fixture (CSV) | timescale (CCXT + TimescaleDB)
OHLCV_PROVIDER=fixture
DEFAULT_EXCHANGE=bybit
```

기존 `TIMESCALE_URL` 항목 있으면 제거.

- [ ] **Step 3: Verify**

```bash
cd backend && uv run python -c "from src.core.config import settings; print(settings.ohlcv_provider, settings.default_exchange)"
```

Expected: `fixture bybit`.

- [ ] **Step 4: Commit**

```bash
git add backend/src/core/config.py backend/.env.example
git commit -m "feat(config): ohlcv_provider Literal flag + default_exchange (timescale_url 제거)"
```

---

## Task 20: CCXTProvider 구현

**Files:**
- Create: `backend/src/market_data/providers/ccxt.py`
- Test: `backend/tests/market_data/test_ccxt_provider.py`

- [ ] **Step 1: Write failing test (mock-based)**

`backend/tests/market_data/test_ccxt_provider.py`:

```python
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.market_data.providers.ccxt import CCXTProvider


@pytest.mark.asyncio
async def test_fetch_ohlcv_pagination_advances_cursor(monkeypatch):
    """3 pages of 1000 bars — cursor 전진 + 중복 제거 검증."""
    provider = CCXTProvider("bybit")
    page1 = [[i * 60_000 + 1_704_067_200_000, 1, 2, 0, 1, 1] for i in range(1000)]
    page2 = [[(i + 1000) * 60_000 + 1_704_067_200_000, 1, 2, 0, 1, 1] for i in range(1000)]
    page3 = [[(i + 2000) * 60_000 + 1_704_067_200_000, 1, 2, 0, 1, 1] for i in range(500)]
    pages = [page1, page2, page3, []]
    mock_fetch = AsyncMock(side_effect=pages)
    monkeypatch.setattr(provider, "_fetch_page", mock_fetch)

    since = datetime(2024, 1, 1, tzinfo=UTC)
    until = datetime(2024, 1, 3, tzinfo=UTC)
    bars = await provider.fetch_ohlcv("BTC/USDT", "1m", since, until)

    assert len(bars) == 2500
    assert mock_fetch.call_count >= 3

    await provider.close()


@pytest.mark.asyncio
async def test_fetch_ohlcv_filters_unclosed_bars(monkeypatch):
    """현재 진행 중 bar (last_closed_ts 초과)는 제외."""
    provider = CCXTProvider("bybit")
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    # bars: past closed + current (open) bar
    bars_in = [
        [now_ms - 120_000, 1, 1, 1, 1, 1],  # 2분 전 — closed
        [now_ms - 60_000, 1, 1, 1, 1, 1],   # 1분 전 — boundary
        [now_ms, 1, 1, 1, 1, 1],            # 진행 중 — exclude
    ]
    monkeypatch.setattr(provider, "_fetch_page", AsyncMock(side_effect=[bars_in, []]))

    bars = await provider.fetch_ohlcv(
        "BTC/USDT", "1m",
        datetime.fromtimestamp((now_ms - 200_000) / 1000, tz=UTC),
        datetime.fromtimestamp((now_ms + 60_000) / 1000, tz=UTC),
    )
    # 진행 중 bar는 제외 — 최대 2개
    assert len(bars) <= 2
    assert all(b[0] < now_ms for b in bars)

    await provider.close()
```

- [ ] **Step 2: Run test — FAIL**

```bash
cd backend && uv run pytest tests/market_data/test_ccxt_provider.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement CCXTProvider**

`backend/src/market_data/providers/ccxt.py`:

```python
"""CCXTProvider — raw OHLCV fetch from exchange (pagination + 재시도)."""
import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import ccxt.async_support as ccxt_async
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.market_data.constants import TIMEFRAME_SECONDS

logger = logging.getLogger(__name__)


class CCXTProvider:
    """CCXT raw OHLCV fetch — pagination + tenacity 재시도 + lifecycle 관리."""

    def __init__(self, exchange_name: str = "bybit") -> None:
        cls = getattr(ccxt_async, exchange_name)
        self.exchange = cls(
            {
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {"defaultType": "spot"},
            }
        )

    async def close(self) -> None:
        """리소스 해제 — lifespan 종료 또는 worker_shutdown에서 호출."""
        await self.exchange.close()

    @retry(
        retry=retry_if_exception_type(
            (
                ccxt_async.NetworkError,
                ccxt_async.RateLimitExceeded,
                ccxt_async.ExchangeNotAvailable,
            )
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _fetch_page(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[list[Any]]:
        return await self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
        max_pages: int = 1000,
    ) -> list[list[Any]]:
        """전체 범위 fetch — pagination + 중복 제거 + closed bar 필터.

        반환: [[timestamp_ms, open, high, low, close, volume], ...]
        """
        tf_sec = TIMEFRAME_SECONDS[timeframe]
        now_ts = int(datetime.now(UTC).timestamp())
        last_closed_ts = (now_ts // tf_sec) * tf_sec - tf_sec
        actual_until_ms = min(int(until.timestamp() * 1000), last_closed_ts * 1000)

        since_ms = int(since.timestamp() * 1000)
        all_bars: list[list[Any]] = []
        seen_timestamps: set[int] = set()
        page_count = 0
        limit = 1000

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
            since_ms = last_ts + tf_sec * 1000
            page_count += 1

            await asyncio.sleep(0.1)  # 보수적 throttle

        if page_count >= max_pages:
            logger.warning(
                "ccxt_fetch_max_pages_reached",
                extra={"symbol": symbol, "timeframe": timeframe, "pages": page_count},
            )

        return all_bars
```

- [ ] **Step 4: Run test — PASS**

```bash
cd backend && uv run pytest tests/market_data/test_ccxt_provider.py -v
```

Expected: 2건 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/market_data/providers/ccxt.py backend/tests/market_data/test_ccxt_provider.py
git commit -m "feat(market_data): CCXTProvider — pagination + tenacity 재시도 + closed bar 필터"
```

---

## Task 21: TimescaleProvider 구현

**Files:**
- Create: `backend/src/market_data/providers/timescale.py`
- Test: `backend/tests/market_data/test_timescale_provider.py`

- [ ] **Step 1: Write failing test**

`backend/tests/market_data/test_timescale_provider.py`:

```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.repository import OHLCVRepository


@pytest.mark.asyncio
async def test_get_ohlcv_full_cache_hit_no_ccxt_call(db_session):
    """모든 데이터가 cache에 있으면 CCXT 호출 0회."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    rows = [
        {
            "time": base + timedelta(hours=i), "symbol": "BTC/USDT", "timeframe": "1h",
            "exchange": "bybit", "open": Decimal("1"), "high": Decimal("1"),
            "low": Decimal("1"), "close": Decimal("1"), "volume": Decimal("1"),
        }
        for i in range(5)
    ]
    await repo.insert_bulk(rows)
    await repo.commit()

    mock_ccxt = AsyncMock(spec=CCXTProvider)
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")
    df = await provider.get_ohlcv("BTC/USDT", "1h", base, base + timedelta(hours=4))

    assert len(df) == 5
    mock_ccxt.fetch_ohlcv.assert_not_called()


@pytest.mark.asyncio
async def test_get_ohlcv_partial_cache_fetches_gaps(db_session):
    """부분 cache → gap만 CCXT fetch."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    # bars 0,1,2 있음 — bars 3,4 없음 (gap)
    rows = [
        {
            "time": base + timedelta(hours=i), "symbol": "BTC/USDT", "timeframe": "1h",
            "exchange": "bybit", "open": Decimal("1"), "high": Decimal("1"),
            "low": Decimal("1"), "close": Decimal("1"), "volume": Decimal("1"),
        }
        for i in range(3)
    ]
    await repo.insert_bulk(rows)
    await repo.commit()

    mock_ccxt = AsyncMock(spec=CCXTProvider)
    # CCXT가 bars 3,4 반환 (timestamp_ms로)
    base_ms = int((base + timedelta(hours=3)).timestamp() * 1000)
    mock_ccxt.fetch_ohlcv.return_value = [
        [base_ms + i * 3_600_000, 1, 1, 1, 1, 1] for i in range(2)
    ]
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    df = await provider.get_ohlcv("BTC/USDT", "1h", base, base + timedelta(hours=4))
    assert len(df) == 5
    mock_ccxt.fetch_ohlcv.assert_called_once()
```

- [ ] **Step 2: Run — FAIL**

```bash
cd backend && uv run pytest tests/market_data/test_timescale_provider.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement TimescaleProvider**

`backend/src/market_data/providers/timescale.py`:

```python
"""TimescaleProvider — DB cache → CCXT fallback fetch + advisory lock."""
from datetime import UTC, datetime
from typing import Any

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

        # 2. lock 획득 후 gap 재조회 (다른 트랜잭션이 이미 fetch 완료했을 수 있음)
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
        self, raw: list[list[Any]], symbol: str, timeframe: str
    ) -> list[dict[str, Any]]:
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
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).astype(float)
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

- [ ] **Step 4: Run test — PASS**

```bash
cd backend && uv run pytest tests/market_data/test_timescale_provider.py -v
```

Expected: 2건 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/market_data/providers/timescale.py backend/tests/market_data/test_timescale_provider.py
git commit -m "feat(market_data): TimescaleProvider — cache → CCXT fallback + advisory lock"
```

---

## Task 22: FastAPI Lifespan — CCXTProvider Singleton

**Files:**
- Modify: `backend/src/main.py`

- [ ] **Step 1: Add lifespan**

`backend/src/main.py` 수정:

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """CCXTProvider singleton 관리."""
    if settings.ohlcv_provider == "timescale":
        from src.market_data.providers.ccxt import CCXTProvider
        app.state.ccxt_provider = CCXTProvider(exchange_name=settings.default_exchange)
    else:
        app.state.ccxt_provider = None

    yield

    if getattr(app.state, "ccxt_provider", None) is not None:
        await app.state.ccxt_provider.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantBridge",
        # ... existing kwargs ...
        lifespan=lifespan,
    )
    # ... existing setup ...
    return app
```

- [ ] **Step 2: Run app, verify no startup errors**

```bash
cd backend && timeout 5 uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 2>&1 | head -10
```

Expected: `Application startup complete` 로그.

- [ ] **Step 3: Run app tests**

```bash
cd backend && uv run pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/src/main.py
git commit -m "feat(main): lifespan — CCXTProvider singleton (timescale provider일 때만 init)"
```

---

## Task 23: Celery Worker Singleton + worker_shutdown

**Files:**
- Modify: `backend/src/tasks/celery_app.py`

- [ ] **Step 1: Add worker singleton helpers**

`backend/src/tasks/celery_app.py`에 추가:

```python
from celery.signals import worker_shutdown

_ccxt_provider: object | None = None  # CCXTProvider | None — 순환 import 방지로 lazy


def get_ccxt_provider_for_worker():
    """Worker 프로세스 lazy singleton (prefork-safe)."""
    global _ccxt_provider
    if _ccxt_provider is None:
        from src.market_data.providers.ccxt import CCXTProvider
        _ccxt_provider = CCXTProvider(exchange_name=settings.default_exchange)
    return _ccxt_provider


@worker_shutdown.connect  # type: ignore[untyped-decorator]
def _on_worker_shutdown(sender: object = None, **_kwargs: object) -> None:
    """Worker 종료 시 CCXTProvider 리소스 해제."""
    global _ccxt_provider
    if _ccxt_provider is not None:
        try:
            asyncio.run(_ccxt_provider.close())
        except Exception:
            logger.exception("ccxt_close_failed_on_shutdown")
        finally:
            _ccxt_provider = None
```

- [ ] **Step 2: Verify import**

```bash
cd backend && uv run python -c "from src.tasks.celery_app import get_ccxt_provider_for_worker; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/tasks/celery_app.py
git commit -m "feat(tasks): Celery worker CCXTProvider lazy singleton + worker_shutdown close"
```

---

## Task 24: Dependencies — get_ohlcv_provider DI

**Files:**
- Modify: `backend/src/market_data/dependencies.py`

- [ ] **Step 1: Implement DI assembly**

`backend/src/market_data/dependencies.py`:

```python
"""market_data DI 조립 — config flag로 fixture vs timescale 전환."""
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.core.config import settings


async def get_ccxt_provider(request: Request) -> Any:
    """FastAPI lifespan에서 init된 singleton."""
    return request.app.state.ccxt_provider


async def get_ohlcv_provider(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """OHLCVProvider 구현체 — config flag로 분기."""
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider
        return FixtureProvider(root=settings.ohlcv_fixture_root)

    from src.market_data.providers.timescale import TimescaleProvider
    from src.market_data.repository import OHLCVRepository

    ccxt = await get_ccxt_provider(request)
    repo = OHLCVRepository(session)
    return TimescaleProvider(repo, ccxt, exchange_name=settings.default_exchange)
```

- [ ] **Step 2: Verify import**

```bash
cd backend && uv run python -c "from src.market_data.dependencies import get_ohlcv_provider; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/market_data/dependencies.py
git commit -m "feat(market_data): get_ohlcv_provider DI — config flag fixture/timescale 분기"
```

---

## Task 25: Backtest Dependencies + Celery Task 통합

**Files:**
- Modify: `backend/src/backtest/dependencies.py`
- Modify: `backend/src/tasks/backtest.py`

- [ ] **Step 1: Update backtest/dependencies.py**

`backend/src/backtest/dependencies.py`에서:

```python
# Before
def _ohlcv_provider() -> OHLCVProvider:
    return FixtureProvider(...)

async def get_backtest_service(
    session: AsyncSession = Depends(get_async_session),
) -> BacktestService:
    return BacktestService(
        ...,
        ohlcv_provider=_ohlcv_provider(),
        ...
    )

# After
from src.market_data.dependencies import get_ohlcv_provider

async def get_backtest_service(
    session: AsyncSession = Depends(get_async_session),
    ohlcv_provider = Depends(get_ohlcv_provider),
) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=CeleryTaskDispatcher(),
    )
```

- [ ] **Step 2: Update tasks/backtest.py — _execute provider 조립**

`backend/src/tasks/backtest.py`의 `_execute()` 함수에서 provider 조립 부분 수정:

```python
# Before — 어떤 형태든 FixtureProvider 직접 생성
provider = FixtureProvider(...)

# After
from src.core.config import settings
from src.market_data.repository import OHLCVRepository

if settings.ohlcv_provider == "fixture":
    from src.market_data.providers.fixture import FixtureProvider
    provider = FixtureProvider(root=settings.ohlcv_fixture_root)
else:
    from src.tasks.celery_app import get_ccxt_provider_for_worker
    from src.market_data.providers.timescale import TimescaleProvider
    ccxt = get_ccxt_provider_for_worker()
    provider = TimescaleProvider(
        OHLCVRepository(session), ccxt, exchange_name=settings.default_exchange
    )
```

- [ ] **Step 3: Run backtest tests — verify no regression**

```bash
cd backend && uv run pytest tests/backtest/ -v 2>&1 | tail -10
```

Expected: 모두 PASS (fixture provider 경로 유지).

- [ ] **Step 4: Commit**

```bash
git add backend/src/backtest/dependencies.py backend/src/tasks/backtest.py
git commit -m "feat(backtest): get_ohlcv_provider DI 통합 — Celery task에서도 config flag 분기"
```

---

## Task 26: conftest — fixture provider 강제

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add autouse fixture**

`backend/tests/conftest.py`에 추가:

```python
@pytest.fixture(autouse=True)
def _force_fixture_provider(monkeypatch):
    """모든 unit/integration test는 fixture provider 강제 (CCXT 외부 호출 금지).

    명시적으로 timescale 테스트하는 경우만 monkeypatch 해제 필요.
    """
    monkeypatch.setattr("src.core.config.settings.ohlcv_provider", "fixture")
```

- [ ] **Step 2: Run full suite**

```bash
cd backend && uv run pytest -v 2>&1 | tail -10
```

Expected: 모두 PASS. 어떤 테스트도 우연히 timescale provider를 호출하지 않음.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test(conftest): _force_fixture_provider autouse — CCXT 외부 호출 차단"
```

---

## Task 27: Backtest E2E with TimescaleProvider (Mock CCXT)

**Files:**
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_backtest_with_timescale.py`

- [ ] **Step 1: Write E2E test**

`backend/tests/integration/test_backtest_with_timescale.py`:

```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.backtest.models import Backtest, BacktestStatus
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.repository import OHLCVRepository


@pytest.mark.asyncio
async def test_backtest_with_timescale_provider_e2e(
    db_session, monkeypatch, authed_user
):
    """TimescaleProvider 경로로 backtest E2E (mock CCXT)."""
    monkeypatch.setattr("src.core.config.settings.ohlcv_provider", "timescale")

    # CCXT mock — 작은 합성 OHLCV 반환
    base = datetime(2024, 1, 1, tzinfo=UTC)
    base_ms = int(base.timestamp() * 1000)
    mock_bars = [
        [base_ms + i * 3_600_000, 100.0 + i, 105.0 + i, 95.0 + i, 102.0 + i, 1000.0]
        for i in range(168)  # 1주일치 1h
    ]
    mock_ccxt = AsyncMock(spec=CCXTProvider)
    mock_ccxt.fetch_ohlcv.return_value = mock_bars

    repo = OHLCVRepository(db_session)
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    # Provider 직접 호출 (Celery task 우회 — 빠른 검증)
    df = await provider.get_ohlcv("BTC/USDT", "1h", base, base + timedelta(days=7))
    assert len(df) >= 168
    assert "open" in df.columns
    assert "close" in df.columns

    # CCXT 호출 1회 + DB 저장 확인
    mock_ccxt.fetch_ohlcv.assert_called()
    cached = await repo.get_range("BTC/USDT", "1h", base, base + timedelta(days=7))
    assert len(cached) == 168
```

- [ ] **Step 2: Run test**

```bash
cd backend && uv run pytest tests/integration/test_backtest_with_timescale.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/
git commit -m "test(integration): backtest E2E with TimescaleProvider (mock CCXT)"
```

---

## Task 28: M3 Milestone Push + CI

- [ ] **Step 1: OHLCVProvider Protocol contract test (옵션)**

Spec §M3.6의 `test_ohlcv_provider_contract.py`는 시간 허용 시 추가 (스킵 가능 — fixture/timescale 별도 테스트로 충분 커버).

- [ ] **Step 2: Final test pass**

```bash
cd backend && uv run pytest -v 2>&1 | tail -10
cd backend && uv run ruff check . && uv run mypy src/
```

- [ ] **Step 3: Update PR M3 checkbox + push**

```bash
git push
sleep 30
gh pr checks
```

Expected: 모든 잡 green.

---

# Milestone 4 — Beat Task + Docker-compose Worker + Sprint 3 Pagination Drift

## Task 29: Celery Beat Schedule

**Files:**
- Modify: `backend/src/tasks/celery_app.py`

- [ ] **Step 1: Add beat_schedule**

`backend/src/tasks/celery_app.py`의 `celery_app.conf.update(...)` 다음에 추가:

```python
celery_app.conf.beat_schedule = {
    "reclaim-stale-backtests": {
        "task": "src.tasks.backtest.reclaim_stale_running",
        "schedule": 300.0,  # 5분 주기
        "options": {
            "expires": 240,  # 4분 내 처리 안 되면 폐기
        },
    },
}
```

- [ ] **Step 2: Verify schedule registration**

```bash
cd backend && uv run python -c "from src.tasks.celery_app import celery_app; print(celery_app.conf.beat_schedule)"
```

Expected: `{'reclaim-stale-backtests': {...}}`.

- [ ] **Step 3: Add test**

`backend/tests/tasks/test_beat_schedule.py`:

```python
def test_reclaim_stale_beat_registered():
    from src.tasks.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "reclaim-stale-backtests" in schedule
    entry = schedule["reclaim-stale-backtests"]
    assert entry["task"] == "src.tasks.backtest.reclaim_stale_running"
    assert entry["schedule"] == 300.0
```

- [ ] **Step 4: Run test**

```bash
cd backend && uv run pytest tests/tasks/test_beat_schedule.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tasks/celery_app.py backend/tests/tasks/test_beat_schedule.py
git commit -m "feat(tasks): Celery beat schedule — reclaim_stale_running 5분 주기"
```

---

## Task 30: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile` (없으면)

- [ ] **Step 1: Check existing Dockerfile**

```bash
ls backend/Dockerfile 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

존재 시 step 2 skip, 미존재 시 작성.

- [ ] **Step 2: Create Dockerfile**

`backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 설치 (캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 코드 복사
COPY . .

# 기본 명령 — docker-compose에서 worker/beat/api로 override
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Build test**

```bash
cd backend && docker build -t quantbridge-backend:test .
```

Expected: build success.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat(infra): backend Dockerfile (worker/beat/api 공용)"
```

---

## Task 31: Docker-compose Worker + Beat 추가

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add worker + beat services**

`docker-compose.yml`의 `services:` 섹션에 추가 (db/redis 다음):

```yaml
  backend-worker:
    build:
      context: ./backend
    container_name: quantbridge-worker
    command: uv run celery -A src.tasks.celery_app worker --loglevel=info --pool=prefork --concurrency=2
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
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
      redis: { condition: service_healthy }
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    volumes:
      - beat-data:/data
    restart: unless-stopped
    networks:
      - quantbridge
```

`volumes:` 섹션에 추가:

```yaml
volumes:
  db-data:
  redis-data:
  beat-data:
```

- [ ] **Step 2: Validate compose file**

```bash
docker compose config | head -30
```

Expected: yaml parse success.

- [ ] **Step 3: Up + verify**

```bash
docker compose up -d
sleep 10
docker compose ps
```

Expected: 5 services UP (db, redis, backend-worker, backend-beat, [api 있으면]).

- [ ] **Step 4: Verify beat scheduling**

```bash
sleep 60  # beat가 첫 schedule 발동하기까지 대기
docker logs quantbridge-beat | grep "reclaim-stale-backtests" | head -3
docker logs quantbridge-worker | grep "reclaim_stale_running" | head -3
```

Expected: beat에서 schedule 발동 + worker에서 task 실행 로그.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(infra): docker-compose backend-worker + backend-beat 통합"
```

---

## Task 32: Strategy Router Pagination Drift Fix

**Files:**
- Modify: `backend/src/strategy/router.py`
- Test: `backend/tests/test_strategy_pagination.py`

- [ ] **Step 1: Inspect current router**

```bash
cd backend && cat src/strategy/router.py | head -80
```

`page` + `limit` 사용 부분 확인.

- [ ] **Step 2: Write compat test (failing)**

`backend/tests/test_strategy_pagination.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_strategy_list_with_offset(client: AsyncClient, mock_clerk_auth):
    """새로운 limit/offset 경로."""
    res = await client.get("/api/v1/strategies?limit=10&offset=20")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_strategy_list_with_legacy_page(client: AsyncClient, mock_clerk_auth):
    """기존 page 경로 — 자동 변환 fallback."""
    res = await client.get("/api/v1/strategies?limit=10&page=3")
    assert res.status_code == 200
    # page=3, limit=10 → offset=20 동작 검증 (응답 검증은 fixture에 따라)
```

- [ ] **Step 3: Update router**

`backend/src/strategy/router.py`의 list endpoint:

```python
from fastapi import Query

@router.get("", response_model=Page[StrategySummary])
async def list_strategies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    page: int | None = Query(
        None,
        deprecated=True,
        description="Deprecated: use offset (= (page-1)*limit). 1 sprint 후 제거.",
    ),
    user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> Page[StrategySummary]:
    if page is not None:
        # 호환성 fallback: page → offset 변환
        offset = (page - 1) * limit if page > 0 else 0
    return await service.list(user_id=user.id, limit=limit, offset=offset)
```

기존 service signature가 `limit/offset` 받는지 확인 — 안 받으면 service도 변경.

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/test_strategy_pagination.py -v
cd backend && uv run pytest tests/strategy/ -v 2>&1 | tail -10
```

Expected: 신규 + 기존 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/strategy/router.py backend/tests/test_strategy_pagination.py
git commit -m "fix(strategy): pagination drift — limit/offset 표준화 + page deprecation fallback"
```

---

## Task 33: M4 Milestone — Final Push + PR Ready + TODO 업데이트

**Files:**
- Modify: `docs/TODO.md`
- Modify: `docs/03_api/endpoints.md`

- [ ] **Step 1: Update TODO.md**

`docs/TODO.md`에 추가 (Sprint 5 Stage B 섹션):

```markdown
### Sprint 5 Stage B — Infra Hardening + market_data ✅ 완료 (2026-04-XX)

- [x] **M1:** DateTime tz-aware 복구 (S3-05) + Engine bar_index fix + AwareDateTime guard + metadata diff
- [x] **M2:** market_data 인프라 (TimescaleDB hypertable + Repository + advisory lock + Numeric(18,8) + 정규화)
- [x] **M3:** CCXT + TimescaleProvider + lifecycle (lifespan singleton + worker_shutdown) + backtest 통합
- [x] **M4:** Beat schedule + docker-compose worker/beat + Sprint 3 pagination drift fix

PR: https://github.com/woosung-dev/quantbridge/pull/<N>
```

기존 "Sprint 5+ 이관" 섹션의 완료 항목 [x] 표시.

- [ ] **Step 2: Update endpoints.md**

`docs/03_api/endpoints.md`에:
- Strategy list: `?page=` deprecated, `?limit=&offset=` 권장 명시
- 새 OHLCVProvider 통합 noted (REST API 미공개, 내부 backtest 경로 전용)

- [ ] **Step 3: Final test + lint**

```bash
cd backend && uv run pytest -v 2>&1 | tail -5
cd backend && uv run ruff check . && uv run mypy src/
```

- [ ] **Step 4: Update PR description (모든 milestone [x])**

```bash
gh pr edit --body "$(cat <<'EOF'
## Summary

Sprint 5 Stage B 완료 — Sprint 4 backtest API의 운영 진입을 위한 infra hardening + market_data 도메인.

### Milestone 진행

- [x] **M1** — DateTime tz-aware + bar_index fix + AwareDateTime guard + metadata diff
- [x] **M2** — market_data infra (TimescaleDB hypertable + Repository + advisory lock)
- [x] **M3** — CCXT + TimescaleProvider + lifecycle + backtest 통합
- [x] **M4** — Beat schedule + docker-compose worker + Sprint 3 pagination drift fix

## 주요 변경

- 모든 datetime 컬럼 TIMESTAMPTZ 전환 + AwareDateTime TypeDecorator로 naive 차단
- vectorbt bar_index TypeError 해결 (`_resolve_bar_index` helper)
- TimescaleDB ts.ohlcv hypertable + Numeric(18,8) + composite PK
- CCXTProvider pagination + tenacity 재시도 + closed bar 필터
- TimescaleProvider cache→fetch + Postgres advisory_lock으로 동시 fetch race 방지
- FastAPI lifespan + Celery worker_shutdown으로 CCXT lifecycle 안전 관리
- Celery beat 5분 주기 stale reclaim
- docker-compose worker/beat 통합 (단일 `docker compose up`)
- Strategy router pagination drift fix (page → offset deprecation fallback)

## Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-16-sprint5-stage-b-design.md`
- Plan: `docs/superpowers/plans/2026-04-16-sprint5-stage-b.md`

## Test Plan

- [x] M1: 368+ 기존 테스트 + AwareDateTime + bar_index 신규 테스트 PASS
- [x] M2: ts.ohlcv hypertable round-trip + Repository CRUD + advisory lock 동시성 테스트
- [x] M3: CCXTProvider mock + TimescaleProvider cache hit/miss + backtest E2E
- [x] M4: docker compose up + beat 5분 주기 + Strategy pagination compat

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Mark PR ready**

```bash
gh pr ready
```

- [ ] **Step 6: Final push + CI confirmation**

```bash
git add docs/TODO.md docs/03_api/endpoints.md
git commit -m "docs(sprint5-stage-b): TODO + endpoints 갱신, Sprint 5 Stage B 완료 표시"
git push
sleep 60
gh pr checks
```

Expected: 모든 CI 잡 green. 사용자 승인 후 merge.

---

## 검증 (E2E Manual)

```bash
# 1. 인프라
docker compose up -d
docker compose ps  # 5 services UP

# 2. M1 검증
cd backend && uv run alembic upgrade head
uv run pytest -k "datetime or timestamptz or bar_index" -v

# 3. M2 검증
docker exec quantbridge-db psql -U quantbridge -c "SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name='ohlcv';"
uv run pytest tests/market_data/ -v

# 4. M3 검증
uv run pytest tests/integration/test_backtest_with_timescale.py -v
# (선택) 실제 CCXT 호출 — 사용자 승인 시
# OHLCV_PROVIDER=timescale uv run python -c "..."

# 5. M4 검증
docker logs quantbridge-beat | grep "reclaim-stale-backtests"
docker logs quantbridge-worker | grep "reclaim_stale"
curl 'http://localhost:8000/api/v1/strategies?limit=10&offset=0'  # 새 경로
curl 'http://localhost:8000/api/v1/strategies?limit=10&page=2'    # 호환 경로
```

---

## Open Issues / Sprint 6+ 이관

- Idempotency-Key 지원 (`POST /backtests`)
- Real broker integration 테스트 인프라 (pytest-celery)
- CCXT 호출 계측 (Prometheus/logfire)
- 초기 backfill Celery task 분리
- Compression / retention policy
- Multi-worker split-brain Redis lock
- FE Strategy delete UX
- Task 14/19/21 Minor improvements (BacktestRepository session.refresh, exists_for_strategy EXISTS, fixture 통합)
