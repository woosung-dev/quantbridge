# H2 Sprint 9 · Phase B — stress_test API + Celery + 9-6 E2 idempotency

**Branch:** `feat/h2s9-stress-api` (from `stage/h2-sprint9` which includes Phase A squash `a0bdf7a`)
**Date:** 2026-04-24
**Master plan:** `/Users/woosung/.claude/plans/h2-sprint-9-validated-ember.md` §Phase B
**Worktree isolation:** YES

## Scope (고정)

1. **stress_test 도메인 API** — Router/Service/Repository 3-Layer. Monte Carlo + Walk-Forward submit/get.
2. **Celery task** — `backend/src/tasks/stress_test_tasks.py` (prefork-safe, lazy init).
3. **Alembic migration** — `stress_tests` 테이블 (+ `backtests` idempotency_payload_hash 컬럼).
4. **9-6 Idempotency E2 upgrade** — `POST /backtests` 에 `body_hash` 비교 + replay 헤더. trading 패턴 그대로 복제.

## Out of scope

- Frontend UI (Phase C)
- Prometheus metrics (Phase D)
- Parameter stability analysis (Sprint 10)

## 도메인 파일 1 — `backend/src/stress_test/models.py`

```python
"""stress_test 도메인 SQLModel."""
# NOTE: from __future__ import annotations 제거 — SQLAlchemy Relationship forward ref 충돌

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class StressTestKind(StrEnum):
    MONTE_CARLO = "monte_carlo"
    WALK_FORWARD = "walk_forward"


class StressTestStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StressTest(SQLModel, table=True):
    __tablename__ = "stress_tests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    backtest_id: UUID = Field(
        sa_column=Column(ForeignKey("backtests.id", ondelete="RESTRICT"), nullable=False, index=True)
    )
    kind: StressTestKind = Field(
        sa_column=Column(SAEnum(StressTestKind, name="stress_test_kind"), nullable=False)
    )
    status: StressTestStatus = Field(
        sa_column=Column(
            SAEnum(StressTestStatus, name="stress_test_status"),
            nullable=False,
            default=StressTestStatus.QUEUED,
        )
    )
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = Field(default=None)
    celery_task_id: str | None = Field(default=None, max_length=64)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False),
    )
    started_at: datetime | None = Field(default=None, sa_column=Column(AwareDateTime(), nullable=True))
    completed_at: datetime | None = Field(default=None, sa_column=Column(AwareDateTime(), nullable=True))

    __table_args__ = (
        Index("ix_stress_tests_user_created", "user_id", "created_at"),
        Index("ix_stress_tests_backtest_id", "backtest_id"),
        Index("ix_stress_tests_status", "status"),
    )
```

## 도메인 파일 2 — `backend/src/stress_test/schemas.py`

```python
"""stress_test Pydantic V2 스키마."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.stress_test.models import StressTestKind, StressTestStatus


class CreateMonteCarloRequest(BaseModel):
    backtest_id: UUID
    n_samples: int = Field(default=1000, ge=100, le=2000)
    seed: int = Field(default=42)


class CreateWalkForwardRequest(BaseModel):
    backtest_id: UUID
    train_bars: int = Field(ge=10, le=10_000)
    test_bars: int = Field(ge=5, le=5_000)
    step_bars: int | None = Field(default=None, ge=1, le=5_000)
    max_folds: int = Field(default=20, ge=1, le=100)


class StressTestCreatedResponse(BaseModel):
    stress_test_id: UUID
    kind: StressTestKind
    status: StressTestStatus
    created_at: datetime


class StressTestDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    backtest_id: UUID
    kind: StressTestKind
    status: StressTestStatus
    params: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
```

## 도메인 파일 3 — `backend/src/stress_test/repository.py`

```python
"""stress_test Repository. AsyncSession 유일 보유."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import Page
from src.stress_test.models import StressTest, StressTestStatus


class StressTestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, st: StressTest) -> StressTest:
        self.session.add(st)
        await self.session.flush()
        return st

    async def get_by_id(
        self, stress_test_id: UUID, *, user_id: UUID | None = None
    ) -> StressTest | None:
        stmt = select(StressTest).where(StressTest.id == stress_test_id)  # type: ignore[arg-type]
        if user_id is not None:
            stmt = stmt.where(StressTest.user_id == user_id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_backtest(
        self, backtest_id: UUID, user_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[StressTest], int]:
        from sqlalchemy import func
        total_stmt = select(func.count()).select_from(StressTest).where(
            StressTest.backtest_id == backtest_id,  # type: ignore[arg-type]
            StressTest.user_id == user_id,  # type: ignore[arg-type]
        )
        total = (await self.session.execute(total_stmt)).scalar_one()
        stmt = (
            select(StressTest)
            .where(
                StressTest.backtest_id == backtest_id,  # type: ignore[arg-type]
                StressTest.user_id == user_id,  # type: ignore[arg-type]
            )
            .order_by(StressTest.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit).offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def transition_to_running(self, stress_test_id: UUID) -> int:
        stmt = (
            update(StressTest)
            .where(
                StressTest.id == stress_test_id,  # type: ignore[arg-type]
                StressTest.status == StressTestStatus.QUEUED,  # type: ignore[arg-type]
            )
            .values(status=StressTestStatus.RUNNING, started_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def complete(
        self, stress_test_id: UUID, *, result: dict[str, object]
    ) -> int:
        stmt = (
            update(StressTest)
            .where(
                StressTest.id == stress_test_id,  # type: ignore[arg-type]
                StressTest.status == StressTestStatus.RUNNING,  # type: ignore[arg-type]
            )
            .values(
                status=StressTestStatus.COMPLETED,
                result=result,
                completed_at=datetime.now(UTC),
            )
        )
        r = await self.session.execute(stmt)
        return r.rowcount

    async def fail(self, stress_test_id: UUID, *, error: str) -> int:
        stmt = (
            update(StressTest)
            .where(StressTest.id == stress_test_id)  # type: ignore[arg-type]
            .values(
                status=StressTestStatus.FAILED,
                error=error,
                completed_at=datetime.now(UTC),
            )
        )
        r = await self.session.execute(stmt)
        return r.rowcount

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
```

## 도메인 파일 4 — `backend/src/stress_test/dispatcher.py`

```python
"""stress_test task dispatcher — Protocol + Celery + Noop (worker) 구현.

backend/src/backtest/dispatcher.py 패턴 그대로 복제.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class StressTestDispatcher(Protocol):
    def dispatch_monte_carlo(self, stress_test_id: UUID) -> str: ...
    def dispatch_walk_forward(self, stress_test_id: UUID) -> str: ...


class CeleryStressTestDispatcher:
    """HTTP 경로 — Celery task enqueue."""

    def dispatch_monte_carlo(self, stress_test_id: UUID) -> str:
        from src.tasks.stress_test_tasks import run_monte_carlo_task
        r = run_monte_carlo_task.delay(str(stress_test_id))
        return r.id

    def dispatch_walk_forward(self, stress_test_id: UUID) -> str:
        from src.tasks.stress_test_tasks import run_walk_forward_task
        r = run_walk_forward_task.delay(str(stress_test_id))
        return r.id


class NoopStressTestDispatcher:
    """Worker 내부 경로 — enqueue 불필요."""

    def dispatch_monte_carlo(self, stress_test_id: UUID) -> str:
        return ""

    def dispatch_walk_forward(self, stress_test_id: UUID) -> str:
        return ""
```

## 도메인 파일 5 — `backend/src/stress_test/service.py`

**AsyncSession import 절대 금지.** Repository 주입만.

```python
"""stress_test service — HTTP submit + Worker execute 경로."""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

import pandas as pd

from src.backtest.models import BacktestStatus
from src.backtest.repository import BacktestRepository
from src.market_data.providers import OHLCVProvider
from src.stress_test.dispatcher import StressTestDispatcher
from src.stress_test.engine import (
    MonteCarloResult,
    WalkForwardResult,
    run_monte_carlo,
    run_walk_forward,
)
from src.stress_test.exceptions import (
    BacktestNotReadyForStress,
    StressTestNotFound,
)
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.repository import StressTestRepository
from src.stress_test.schemas import (
    CreateMonteCarloRequest,
    CreateWalkForwardRequest,
    StressTestCreatedResponse,
    StressTestDetail,
)
from src.strategy.repository import StrategyRepository

logger = logging.getLogger(__name__)


def _mc_result_to_jsonb(r: MonteCarloResult) -> dict[str, object]:
    """Decimal → str, dict[str, list[Decimal]] → dict[str, list[str]]."""
    return {
        "samples": r.samples,
        "ci_lower_95": str(r.ci_lower_95),
        "ci_upper_95": str(r.ci_upper_95),
        "median_final_equity": str(r.median_final_equity),
        "max_drawdown_mean": str(r.max_drawdown_mean),
        "max_drawdown_p95": str(r.max_drawdown_p95),
        "equity_percentiles": {
            k: [str(v) for v in series]
            for k, series in r.equity_percentiles.items()
        },
    }


def _wf_result_to_jsonb(r: WalkForwardResult) -> dict[str, object]:
    return {
        "folds": [
            {
                "fold_index": f.fold_index,
                "train_start": f.train_start.isoformat(),
                "train_end": f.train_end.isoformat(),
                "test_start": f.test_start.isoformat(),
                "test_end": f.test_end.isoformat(),
                "in_sample_return": str(f.in_sample_return),
                "out_of_sample_return": str(f.out_of_sample_return),
                "oos_sharpe": str(f.oos_sharpe) if f.oos_sharpe is not None else None,
                "num_trades_oos": f.num_trades_oos,
            }
            for f in r.folds
        ],
        "aggregate_oos_return": str(r.aggregate_oos_return),
        "degradation_ratio": str(r.degradation_ratio),
        "valid_positive_regime": r.valid_positive_regime,
        "total_possible_folds": r.total_possible_folds,
        "was_truncated": r.was_truncated,
    }


class StressTestService:
    def __init__(
        self,
        *,
        repo: StressTestRepository,
        backtest_repo: BacktestRepository,
        strategy_repo: StrategyRepository,
        ohlcv_provider: OHLCVProvider,
        dispatcher: StressTestDispatcher,
    ) -> None:
        self.repo = repo
        self.backtest_repo = backtest_repo
        self.strategy_repo = strategy_repo
        self.provider = ohlcv_provider
        self.dispatcher = dispatcher

    # --- HTTP submit ---

    async def submit_monte_carlo(
        self, data: CreateMonteCarloRequest, *, user_id: UUID
    ) -> StressTestCreatedResponse:
        bt = await self._ensure_backtest_completed(data.backtest_id, user_id)
        if not bt.equity_curve:
            raise BacktestNotReadyForStress(detail="Backtest has no equity_curve")

        st = StressTest(
            user_id=user_id,
            backtest_id=bt.id,
            kind=StressTestKind.MONTE_CARLO,
            status=StressTestStatus.QUEUED,
            params={"n_samples": data.n_samples, "seed": data.seed},
        )
        await self.repo.create(st)
        task_id = self.dispatcher.dispatch_monte_carlo(st.id)
        st.celery_task_id = task_id
        await self.repo.commit()
        return StressTestCreatedResponse(
            stress_test_id=st.id, kind=st.kind, status=st.status, created_at=st.created_at
        )

    async def submit_walk_forward(
        self, data: CreateWalkForwardRequest, *, user_id: UUID
    ) -> StressTestCreatedResponse:
        bt = await self._ensure_backtest_completed(data.backtest_id, user_id)

        st = StressTest(
            user_id=user_id,
            backtest_id=bt.id,
            kind=StressTestKind.WALK_FORWARD,
            status=StressTestStatus.QUEUED,
            params={
                "train_bars": data.train_bars,
                "test_bars": data.test_bars,
                "step_bars": data.step_bars,
                "max_folds": data.max_folds,
            },
        )
        await self.repo.create(st)
        task_id = self.dispatcher.dispatch_walk_forward(st.id)
        st.celery_task_id = task_id
        await self.repo.commit()
        return StressTestCreatedResponse(
            stress_test_id=st.id, kind=st.kind, status=st.status, created_at=st.created_at
        )

    # --- Worker execute ---

    async def run_monte_carlo(self, stress_test_id: UUID) -> None:
        st = await self.repo.get_by_id(stress_test_id)
        if st is None:
            return
        rows = await self.repo.transition_to_running(stress_test_id)
        if rows == 0:
            return
        await self.repo.commit()
        try:
            bt = await self.backtest_repo.get_by_id(st.backtest_id)
            if bt is None or not bt.equity_curve:
                await self.repo.fail(stress_test_id, error="backtest or equity_curve missing")
                await self.repo.commit()
                return
            # equity_curve JSONB → list[Decimal]
            curve = [Decimal(v) for _ts, v in bt.equity_curve]
            n_samples = int(st.params.get("n_samples", 1000))
            seed = int(st.params.get("seed", 42))
            result = run_monte_carlo(curve, n_samples=n_samples, seed=seed)
            await self.repo.complete(stress_test_id, result=_mc_result_to_jsonb(result))
            await self.repo.commit()
        except Exception as exc:
            logger.exception("monte_carlo_task_failed")
            await self.repo.fail(stress_test_id, error=str(exc))
            await self.repo.commit()

    async def run_walk_forward(self, stress_test_id: UUID) -> None:
        st = await self.repo.get_by_id(stress_test_id)
        if st is None:
            return
        rows = await self.repo.transition_to_running(stress_test_id)
        if rows == 0:
            return
        await self.repo.commit()
        try:
            bt = await self.backtest_repo.get_by_id(st.backtest_id)
            if bt is None:
                await self.repo.fail(stress_test_id, error="backtest missing")
                await self.repo.commit()
                return
            strategy = await self.strategy_repo.find_by_id_and_owner(bt.strategy_id, bt.user_id)
            if strategy is None:
                await self.repo.fail(stress_test_id, error="strategy missing")
                await self.repo.commit()
                return
            ohlcv = await self.provider.get_ohlcv(
                bt.symbol, bt.timeframe, bt.period_start, bt.period_end
            )
            params = st.params
            result = run_walk_forward(
                strategy.pine_source,
                ohlcv,
                train_bars=int(params["train_bars"]),
                test_bars=int(params["test_bars"]),
                step_bars=params.get("step_bars"),
                max_folds=int(params.get("max_folds", 20)),
            )
            await self.repo.complete(stress_test_id, result=_wf_result_to_jsonb(result))
            await self.repo.commit()
        except Exception as exc:
            logger.exception("walk_forward_task_failed")
            await self.repo.fail(stress_test_id, error=str(exc))
            await self.repo.commit()

    # --- HTTP read ---

    async def get(self, stress_test_id: UUID, *, user_id: UUID) -> StressTestDetail:
        st = await self.repo.get_by_id(stress_test_id, user_id=user_id)
        if st is None:
            raise StressTestNotFound()
        return StressTestDetail.model_validate(st)

    # --- helpers ---

    async def _ensure_backtest_completed(self, backtest_id: UUID, user_id: UUID):
        bt = await self.backtest_repo.get_by_id(backtest_id, user_id=user_id)
        if bt is None:
            raise BacktestNotReadyForStress(
                detail=f"Backtest not found or not owned: {backtest_id}",
                status_code=404,
            )
        if bt.status != BacktestStatus.COMPLETED:
            raise BacktestNotReadyForStress(
                detail=f"Backtest must be completed; current: {bt.status.value}"
            )
        return bt
```

## 도메인 파일 6 — `backend/src/stress_test/exceptions.py`

```python
from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class StressTestError(AppException):
    pass


class StressTestNotFound(StressTestError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "stress_test_not_found"
    detail = "Stress test not found"


class StressTestStateConflict(StressTestError):
    status_code = status.HTTP_409_CONFLICT
    code = "stress_test_state_conflict"
    detail = "Stress test state does not allow this action"


class BacktestNotReadyForStress(StressTestError):
    status_code = status.HTTP_409_CONFLICT
    code = "backtest_not_ready_for_stress"
    detail = "Backtest must be completed before stress test"
```

## 도메인 파일 7 — `backend/src/stress_test/router.py`

```python
"""stress_test REST API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.stress_test.dependencies import get_stress_test_service
from src.stress_test.schemas import (
    CreateMonteCarloRequest,
    CreateWalkForwardRequest,
    StressTestCreatedResponse,
    StressTestDetail,
)
from src.stress_test.service import StressTestService

router = APIRouter(prefix="/stress-test", tags=["stress_test"])


@router.post("/monte-carlo", response_model=StressTestCreatedResponse, status_code=202)
async def submit_monte_carlo(
    data: CreateMonteCarloRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_monte_carlo(data, user_id=user.id)


@router.post("/walk-forward", response_model=StressTestCreatedResponse, status_code=202)
async def submit_walk_forward(
    data: CreateWalkForwardRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_walk_forward(data, user_id=user.id)


@router.get("/{stress_test_id}", response_model=StressTestDetail)
async def get_stress_test(
    stress_test_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestDetail:
    return await service.get(stress_test_id, user_id=user.id)
```

## 도메인 파일 8 — `backend/src/stress_test/dependencies.py`

```python
"""stress_test DI 조립. Depends는 여기에서만."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.repository import BacktestRepository
from src.common.database import get_async_session
from src.market_data.dependencies import get_ohlcv_provider
from src.market_data.providers import OHLCVProvider
from src.stress_test.dispatcher import CeleryStressTestDispatcher, NoopStressTestDispatcher
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService
from src.strategy.repository import StrategyRepository


async def get_stress_test_service(
    ohlcv_provider: OHLCVProvider = Depends(get_ohlcv_provider),
    session: AsyncSession = Depends(get_async_session),
) -> StressTestService:
    return StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=CeleryStressTestDispatcher(),
    )


def build_stress_test_service_for_worker(session: AsyncSession) -> StressTestService:
    """Worker 진입 — Noop dispatcher + fixture/timescale OHLCV provider."""
    from src.core.config import settings
    ohlcv_provider: OHLCVProvider
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider
        ohlcv_provider = FixtureProvider(root=settings.ohlcv_fixture_root)
    else:
        from src.market_data.providers.timescale import TimescaleProvider
        from src.market_data.repository import OHLCVRepository
        from src.tasks.celery_app import get_ccxt_provider_for_worker
        ohlcv_provider = TimescaleProvider(
            OHLCVRepository(session),
            get_ccxt_provider_for_worker(),
            exchange_name=settings.default_exchange,
        )
    return StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=NoopStressTestDispatcher(),
    )
```

## Celery tasks — `backend/src/tasks/stress_test_tasks.py`

**prefork-safe (Sprint 4 D3):** 모듈 top-level 에서 AsyncSession / vectorbt import 금지. 함수 내부 지연 import.

```python
"""stress_test Celery task wrappers."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="stress_test.run_monte_carlo", bind=True)
def run_monte_carlo_task(self: object, stress_test_id: str) -> None:
    asyncio.run(_run_monte_carlo_async(UUID(stress_test_id)))


@celery_app.task(name="stress_test.run_walk_forward", bind=True)
def run_walk_forward_task(self: object, stress_test_id: str) -> None:
    asyncio.run(_run_walk_forward_async(UUID(stress_test_id)))


async def _run_monte_carlo_async(stress_test_id: UUID) -> None:
    from src.common.database import async_session_factory
    from src.stress_test.dependencies import build_stress_test_service_for_worker
    async with async_session_factory() as session:
        svc = build_stress_test_service_for_worker(session)
        await svc.run_monte_carlo(stress_test_id)


async def _run_walk_forward_async(stress_test_id: UUID) -> None:
    from src.common.database import async_session_factory
    from src.stress_test.dependencies import build_stress_test_service_for_worker
    async with async_session_factory() as session:
        svc = build_stress_test_service_for_worker(session)
        await svc.run_walk_forward(stress_test_id)
```

## `backend/src/main.py` — router include

기존 `include_router` 블록에 추가:

```python
from src.stress_test.router import router as stress_test_router
app.include_router(stress_test_router, prefix="/api/v1")
```

## Alembic migration 1 — `backend/alembic/versions/20260424_XXXX_add_stress_tests_table.py`

`alembic revision --autogenerate -m "add_stress_tests_table"` 생성. 검토 후 수동 보정 (CASCADE/RESTRICT 방향, enum 이름 일치).

## 9-6 E2 Idempotency upgrade (backtest 도메인)

trading 패턴 그대로 복제. 아래 5 파일 변경.

### `backend/src/backtest/models.py` — 신규 필드

```python
from sqlalchemy import LargeBinary

class Backtest(SQLModel, table=True):
    # ... 기존 필드들 ...
    idempotency_key: str | None = Field(default=None, max_length=128, nullable=True)
    idempotency_payload_hash: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    # __table_args__ 의 UniqueConstraint("idempotency_key") 유지
```

### `backend/alembic/versions/20260424_XXXX_add_backtests_idempotency_payload_hash.py`

```python
def upgrade():
    op.add_column(
        "backtests",
        sa.Column("idempotency_payload_hash", sa.LargeBinary(), nullable=True),
    )

def downgrade():
    op.drop_column("backtests", "idempotency_payload_hash")
```

### `backend/src/backtest/schemas.py` — `BacktestCreatedResponse.replayed: bool = False`

```python
class BacktestCreatedResponse(BaseModel):
    backtest_id: UUID
    status: BacktestStatus
    created_at: datetime
    replayed: bool = False  # 9-6: True 면 Idempotency-Key replay 된 것
```

### `backend/src/backtest/exceptions.py`

`BacktestDuplicateIdempotencyKey` 를 `BacktestIdempotencyConflict` 로 **의미 재정의** — 단순 409 가 아니라 "body_hash mismatch 로 인한 충돌" 전용. 이름 유지는 backward compat 깨뜨리지 않음 (code="backtest_idempotency_conflict").

기존 그대로 유지하되 detail 메시지만 명확화. 새 클래스 추가 불필요.

### `backend/src/backtest/service.py:73-128` — `submit()` 재작성

```python
import hashlib
import json

def _compute_body_hash(data: CreateBacktestRequest, user_id: UUID) -> bytes:
    """sha256(canonical(data | {user_id})) — user 교차 replay 차단."""
    payload = {**data.model_dump(mode="json"), "user_id": str(user_id)}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).digest()


async def submit(
    self,
    data: CreateBacktestRequest,
    *,
    user_id: UUID,
    idempotency_key: str | None = None,
) -> BacktestCreatedResponse:
    body_hash: bytes | None = None
    if idempotency_key is not None:
        body_hash = _compute_body_hash(data, user_id)
        await self.repo.acquire_idempotency_lock(idempotency_key)
        existing = await self.repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            # 기존 row 에 hash 가 없거나 다르면 conflict
            if existing.idempotency_payload_hash != body_hash:
                raise BacktestDuplicateIdempotencyKey(
                    detail=(
                        f"Idempotency-Key '{idempotency_key}' 가 다른 payload 로 재사용됨. "
                        f"existing backtest_id={existing.id}"
                    )
                )
            # 같은 key + 같은 body → replay
            return BacktestCreatedResponse(
                backtest_id=existing.id,
                status=existing.status,
                created_at=existing.created_at,
                replayed=True,
            )

    # 이하 기존 경로 (strategy 검증, coverage, create) — idempotency_payload_hash=body_hash 저장
    # ...
    bt = Backtest(
        # ...
        idempotency_key=idempotency_key,
        idempotency_payload_hash=body_hash,
    )
    # ...
```

### `backend/src/backtest/router.py:27-34` — replay 시 헤더 추가

```python
from fastapi import Response

@router.post("", response_model=BacktestCreatedResponse, status_code=202)
async def submit_backtest(
    data: CreateBacktestRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> BacktestCreatedResponse:
    result = await service.submit(data, user_id=user.id, idempotency_key=idempotency_key)
    if result.replayed:
        response.headers["X-Idempotency-Replayed"] = "true"
    return result
```

## Tests

### Phase B 신규 파일들 (RED → GREEN)

- `backend/tests/stress_test/test_router_monte_carlo_submit.py`
- `backend/tests/stress_test/test_router_walk_forward_submit.py`
- `backend/tests/stress_test/test_router_get_detail_ownership.py`
- `backend/tests/stress_test/test_service_backtest_not_completed.py`
- `backend/tests/stress_test/test_worker_monte_carlo_happy_path.py`
- `backend/tests/stress_test/test_worker_walk_forward_happy_path.py`
- `backend/tests/stress_test/test_worker_failure_path.py`

### 9-6 E2 신규 파일

- `backend/tests/backtest/test_idempotency_e2_replay_same_payload.py` — 같은 key+body → `replayed=True` + `X-Idempotency-Replayed: true`
- `backend/tests/backtest/test_idempotency_e2_conflict_different_payload.py` — 같은 key+다른 body → 409
- `backend/tests/backtest/test_idempotency_e2_backward_compat_null_hash.py` — 기존 row hash=NULL 에 대해 conflict 처리

### 기존 `tests/backtest/test_idempotency.py` 는 유지

simple 버전 테스트는 regression 감지용으로 남김. `replayed=False` 기본 동작이 깨지지 않아야 함.

## 검증 명령

```bash
cd backend
alembic upgrade head  # 2 마이그레이션 적용
ruff check src/stress_test/ src/backtest/ src/tasks/stress_test_tasks.py tests/stress_test/ tests/backtest/
mypy src/stress_test/ src/backtest/ src/tasks/stress_test_tasks.py
pytest tests/stress_test/ tests/backtest/test_idempotency_e2_* -v
# 10+ 신규 테스트 green
pytest -x  # 전체 회귀 1035 + 신규 10 = ~1045 green
```

Smoke (개발 서버):

```bash
uvicorn src.main:app --reload --port 8000 &
# Terminal 2:
curl -X POST -H "Idempotency-Key: test-key-1" -H "Content-Type: application/json" \
     -d '{"strategy_id":"...","symbol":"BTC/USDT",...}' \
     http://localhost:8000/api/v1/backtests
# 재호출 → 202 + X-Idempotency-Replayed: true
curl -X POST http://localhost:8000/api/v1/stress-test/monte-carlo \
     -H "Content-Type: application/json" \
     -d '{"backtest_id":"...","n_samples":1000}'
# 202 + stress_test_id
curl http://localhost:8000/api/v1/stress-test/<id>
# detail
```

## 커밋 (Agent 재량, 권장 2 커밋)

```
c1 feat(stress-test): API + Celery task + models + migration (Phase B)

- domain: router/service/repository/schemas/models/dependencies/exceptions
- Celery task (prefork-safe, lazy init)
- StressTest table + JSONB params/result columns
- alembic migration 1

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

c2 feat(backtest): 9-6 Idempotency-Key E2 upgrade — body_hash + replay (Phase B)

- backtest.models: idempotency_payload_hash LargeBinary
- service.submit: hash 비교 → replay or conflict
- router: X-Idempotency-Replayed 헤더
- schemas: replayed: bool 필드
- alembic migration 2
- tests: replay + conflict + null-hash backward compat

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Golden Rules 체크리스트

- [ ] AsyncSession 은 Repository 만. service.py / router.py import 금지.
- [ ] Celery task prefork-safe (모듈 top-level 에서 DB engine / vectorbt import 금지, 함수 내부 lazy import).
- [ ] Decimal-first 합산 (`Decimal(str(...))`). `Decimal(str(a+b))` 금지.
- [ ] 환경변수 하드코딩 없음, `.env.example` 업데이트 (필요 시).
- [ ] `from __future__ import annotations` (models.py 제외 — forward ref 충돌).
- [ ] 9-6 upgrade 는 **기존 row hash=NULL 을 conflict 로 처리** (가장 안전).
- [ ] Alembic 마이그레이션 2 개 생성 후 수동 검토 (autogenerate 결과 그대로 쓰지 말 것).
- [ ] ruff / mypy green.
- [ ] pytest 전체 green (Phase A 1035 + 신규 ~15 = ~1050).

## Agent 디스패치 계약

**isolation:** worktree. base: `stage/h2-sprint9` (a0bdf7a Phase A squash 포함).
**branch:** `feat/h2s9-stress-api`.

**Output JSON:**

```json
{
  "branch": "feat/h2s9-stress-api",
  "commits": ["<sha1>", "<sha2>"],
  "files_added": ["..."],
  "files_modified": ["..."],
  "migrations": ["<filename1>", "<filename2>"],
  "tests_added": <int>,
  "tests_total_after": <int>,
  "coverage_stress_test_pct": "<float>",
  "coverage_backtest_delta_pct": "<float>",
  "issues": ["..."],
  "ready_for_evaluator": true
}
```

## 리스크 & 가정

| 리스크                                                                                 | 대응                                                                                                                     |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| WFA `run_backtest` 를 loop 내에서 호출 → Celery task 장시간 (1년 1H, 20 fold ≈ 20~60s) | `CELERYD_TASK_TIME_LIMIT` 기본 600s 로 충분. 초과 시 `max_folds` 하향.                                                   |
| `equity_curve` JSONB → list[Decimal] 파싱 시 format 차이                               | `backend/src/backtest/serializers.py::equity_curve_to_jsonb` 읽어 reverse parser 작성. `[[timestamp, value], ...]` 형식. |
| Alembic autogenerate 가 기존 users/backtests FK 를 누락                                | revision 검토 필수. Head base 는 `20260422_0925_remove_testnet_exchange_mode`.                                           |
| 9-6 backward compat — 기존 backtest row `idempotency_payload_hash=NULL`                | 테스트로 강제: `None != body_hash` → `BacktestDuplicateIdempotencyKey` 던지는 것이 맞다.                                 |
| [가정] JSONB 에 Decimal string 저장                                                    | Decimal 은 JSON native 타입 아님 → 문자열로 직렬화. Phase C FE 에서 `Number(str)` 또는 `new Decimal(str)` 변환.          |

## 삭제 불필요

Phase B 는 순수 신규 + 기존 파일 확장. 삭제 파일 없음.
