"""[BL-773] Backtest가 제출 시점 StrategyVersion을 실행하는지 검증한다."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.engine import PINE_V2_ENGINE_VERSION
from src.backtest.engine.types import BacktestOutcome
from src.backtest.models import BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.optimizer.dispatcher import FakeOptimizationTaskDispatcher
from src.optimizer.engine import GridSearchCell, GridSearchResult
from src.optimizer.repository import OptimizationRepository
from src.optimizer.schemas import (
    CreateOptimizationRunRequest,
    OptimizationKindOut,
    ParamSpace,
)
from src.optimizer.service import OptimizerService
from src.strategy.models import StrategyVersion
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest
from src.strategy.service import StrategyService

_PINE_A = """//@version=5
strategy("version A")
strategy.entry("A", strategy.long)
"""

_PINE_B = """//@version=5
strategy("version B")
strategy.entry("B", strategy.short)
"""


@pytest.mark.asyncio
async def test_strategy_current_version_pointer_stays_stable_across_backtest_submissions(
    db_session: AsyncSession,
) -> None:
    """BL-773: latest pointer는 create/update snapshot을 가리키고 submit은 새 version을 만들지 않는다."""
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    strategy_repo = StrategyRepository(db_session)
    strategy_service = StrategyService(repo=strategy_repo)
    created = await strategy_service.create(
        CreateStrategyRequest(name="current-version", pine_source=_PINE_A),
        owner_id=user.id,
    )
    strategy = await strategy_repo.find_by_id_and_owner(created.id, user.id)
    assert strategy is not None
    await db_session.refresh(strategy)
    initial_versions = list(
        (
            await db_session.execute(
                select(StrategyVersion).where(StrategyVersion.strategy_id == strategy.id)
            )
        ).scalars()
    )
    assert len(initial_versions) == 1
    initial_version = initial_versions[0]
    assert strategy.strategy_version_id == initial_version.id

    backtest_service = BacktestService(
        repo=BacktestRepository(db_session),
        strategy_repo=strategy_repo,
        ohlcv_provider=AsyncMock(),
        dispatcher=FakeTaskDispatcher(),
    )
    request = CreateBacktestRequest(
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )
    await backtest_service.submit(request, user_id=user.id)
    await backtest_service.submit(request, user_id=user.id)

    versions_after_submits = list(
        (
            await db_session.execute(
                select(StrategyVersion).where(StrategyVersion.strategy_id == strategy.id)
            )
        ).scalars()
    )
    assert [version.id for version in versions_after_submits] == [initial_version.id]

    await strategy_service.update(
        strategy_id=strategy.id,
        owner_id=user.id,
        data=UpdateStrategyRequest(pine_source=_PINE_B),
    )
    await db_session.refresh(strategy)
    latest_version = await strategy_repo.get_version_by_id(
        strategy.strategy_version_id,
        strategy_id=strategy.id,
    )
    assert latest_version is not None
    assert latest_version.id != initial_version.id
    assert latest_version.pine_source == _PINE_B
    assert strategy.strategy_version_id == latest_version.id


@pytest.mark.asyncio
async def test_worker_executes_strategy_source_pinned_at_submission(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pine A 제출 뒤 Pine B로 수정해도 worker는 A를 실행한다."""
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    strategy_repo = StrategyRepository(db_session)
    strategy_service = StrategyService(repo=strategy_repo)
    created_strategy = await strategy_service.create(
        CreateStrategyRequest(name="versioned", pine_source=_PINE_A),
        owner_id=user.id,
    )
    stored_strategy = await strategy_repo.find_by_id_and_owner(created_strategy.id, user.id)
    assert stored_strategy is not None
    initial_version = await strategy_repo.get_version_by_id(
        stored_strategy.strategy_version_id,
        strategy_id=created_strategy.id,
    )
    assert initial_version is not None
    assert initial_version.source_hash == hashlib.sha256(_PINE_A.encode()).hexdigest()
    assert initial_version.parser_version == "pine_v2"

    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()
    backtest_service = BacktestService(
        repo=BacktestRepository(db_session),
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeTaskDispatcher(),
    )
    submitted = await backtest_service.submit(
        CreateBacktestRequest(
            strategy_id=created_strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            initial_capital=Decimal("10000"),
        ),
        user_id=user.id,
    )

    await strategy_service.update(
        strategy_id=created_strategy.id,
        owner_id=user.id,
        data=UpdateStrategyRequest(pine_source=_PINE_B),
    )

    executed_sources: list[str] = []

    def capture_source(source: str, *_: object, **__: object) -> BacktestOutcome:
        executed_sources.append(source)
        return BacktestOutcome(
            status="error",
            parse=MagicMock(),
            result=None,
            error=RuntimeError("test sentinel"),
        )

    monkeypatch.setattr("src.backtest.service.run_backtest", capture_source)

    await backtest_service.run(submitted.backtest_id)

    assert executed_sources == [_PINE_A]


@pytest.mark.asyncio
async def test_optimizer_executes_parent_backtest_strategy_version(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pine A 백테스트를 부모로 삼은 optimizer는 이후 Pine B가 아니라 A를 실행한다."""
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    strategy_repo = StrategyRepository(db_session)
    strategy_service = StrategyService(repo=strategy_repo)
    created_strategy = await strategy_service.create(
        CreateStrategyRequest(name="optimizer-versioned", pine_source=_PINE_A),
        owner_id=user.id,
    )

    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()
    backtest_repo = BacktestRepository(db_session)
    backtest_service = BacktestService(
        repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeTaskDispatcher(),
    )
    submitted = await backtest_service.submit(
        CreateBacktestRequest(
            strategy_id=created_strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            initial_capital=Decimal("10000"),
        ),
        user_id=user.id,
    )
    parent = await backtest_repo.get_by_id(submitted.backtest_id)
    assert parent is not None
    assert parent.engine_version == PINE_V2_ENGINE_VERSION
    parent.status = BacktestStatus.COMPLETED
    await db_session.commit()

    await strategy_service.update(
        strategy_id=created_strategy.id,
        owner_id=user.id,
        data=UpdateStrategyRequest(pine_source=_PINE_B),
    )

    optimizer_service = OptimizerService(
        repo=OptimizationRepository(db_session),
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeOptimizationTaskDispatcher(),
    )
    param_space = ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 1,
            "parameters": {"length": {"kind": "integer", "min": 1, "max": 1, "step": 1}},
        }
    )
    submitted_run = await optimizer_service.submit_grid_search(
        CreateOptimizationRunRequest(
            backtest_id=parent.id,
            kind=OptimizationKindOut.GRID_SEARCH,
            param_space=param_space,
        ),
        user_id=user.id,
    )

    executed_sources: list[str] = []

    def capture_source(
        _: object,
        pine_source: str,
        *__: object,
        **___: object,
    ) -> GridSearchResult:
        executed_sources.append(pine_source)
        return GridSearchResult(
            param_names=("length",),
            param_values={"length": (Decimal(1),)},
            cells=(
                GridSearchCell(
                    param_values={"length": Decimal(1)},
                    sharpe=Decimal("1"),
                    total_return=Decimal("0"),
                    max_drawdown=Decimal("0"),
                    num_trades=0,
                    is_degenerate=False,
                    objective_value=Decimal("1"),
                ),
            ),
            objective_metric="sharpe_ratio",
            direction="maximize",
            best_cell_index=0,
        )

    monkeypatch.setattr("src.optimizer.service.run_optimizer_by_kind", capture_source)

    await optimizer_service.run(submitted_run.id)

    assert executed_sources == [_PINE_A]
