"""[BL-783] Stress Test 가 부모 Backtest 에 핀된 StrategyVersion 을 실행하는지 검증한다.

[BL-773](PR #650)이 backtest·optimizer 에 대해 닫은 결함과 동형이다 — 엔진을 재실행하는
경로가 실행 시점의 mutable `Strategy.pine_source` 를 읽으면, 사용자가 제출 후 전략을 수정한
뒤 stress test 를 돌릴 때 **수정본이 실행되고 결과는 옛 백테스트에 매달려 표시된다.**

엔진 재실행 경로는 셋이다 (`service.py`):

- `_execute_walk_forward` → `run_walk_forward_optimization` (optimizer spec 동봉 시)
- `_execute_walk_forward` → `run_walk_forward` (fixed-param / plain)
- `_execute_grid_sweep` → `run_cost_assumption_sensitivity` / `run_param_stability`

셋을 각각 덮는다 — 하나만 고치면 나머지 둘로 결함이 남는다.
Monte Carlo 는 완료된 Backtest 의 equity_curve 를 재표집할 뿐 엔진을 재실행하지 않으므로
대상이 아니다 (`_execute_monte_carlo` 는 strategy 를 아예 로드하지 않는다).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest
from src.strategy.service import StrategyService
from src.stress_test.dispatcher import FakeStressTaskDispatcher
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService

_PINE_A = """//@version=5
strategy("version A")
strategy.entry("A", strategy.long)
"""

_PINE_B = """//@version=5
strategy("version B")
strategy.entry("B", strategy.short)
"""

_PARAM_SPACE_JSONB: dict[str, Any] = {
    "schema_version": 1,
    "objective_metric": "sharpe_ratio",
    "direction": "maximize",
    "max_evaluations": 1,
    "parameters": {"length": {"kind": "integer", "min": 1, "max": 1, "step": 1}},
}


def _make_ohlcv() -> pd.DataFrame:
    idx = pd.date_range(start="2024-01-01", periods=10, freq="1h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0] * 10,
            "high": [101.0] * 10,
            "low": [99.0] * 10,
            "close": [100.5] * 10,
            "volume": [1000.0] * 10,
        },
        index=idx,
    )


async def _seed_backtest_pinned_to_pine_a(
    db_session: AsyncSession,
) -> tuple[Backtest, StrategyRepository]:
    """Pine A 로 제출된 COMPLETED Backtest 를 만들고, 그 뒤 전략을 Pine B 로 수정한다.

    반환된 Backtest 는 `strategy_version_id` 로 A 스냅샷을 가리키고,
    현재 `Strategy.pine_source` 는 B 다.
    """
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
        CreateStrategyRequest(name="stress-versioned", pine_source=_PINE_A),
        owner_id=user.id,
    )

    backtest_repo = BacktestRepository(db_session)
    backtest_service = BacktestService(
        repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=AsyncMock(),
        dispatcher=FakeTaskDispatcher(),
    )
    submitted = await backtest_service.submit(
        CreateBacktestRequest(
            strategy_id=created.id,
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
    assert parent.strategy_version_id is not None, (
        "부모 Backtest 가 제출 시점 스냅샷을 핀하지 않았다 — [BL-773] 전제가 깨졌다"
    )
    parent.status = BacktestStatus.COMPLETED
    parent.completed_at = datetime.now(UTC)
    await db_session.commit()

    await strategy_service.update(
        strategy_id=created.id,
        owner_id=user.id,
        data=UpdateStrategyRequest(pine_source=_PINE_B),
    )
    current = await strategy_repo.find_by_id_and_owner(created.id, user.id)
    assert current is not None
    assert current.pine_source == _PINE_B, "전제 실패 — 전략이 Pine B 로 수정되지 않았다"

    return parent, strategy_repo


def _make_service(db_session: AsyncSession, strategy_repo: Any) -> StressTestService:
    provider = MagicMock()
    provider.get_ohlcv = AsyncMock(return_value=_make_ohlcv())
    return StressTestService(
        repo=StressTestRepository(db_session),
        backtest_repo=BacktestRepository(db_session),
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeStressTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_walk_forward_executes_pinned_strategy_version(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`run_walk_forward` (fixed-param/plain) 경로가 A 를 실행한다."""
    parent, strategy_repo = await _seed_backtest_pinned_to_pine_a(db_session)
    service = _make_service(db_session, strategy_repo)
    st = StressTest(
        id=uuid4(),
        user_id=parent.user_id,
        backtest_id=parent.id,
        kind=StressTestKind.WALK_FORWARD,
        status=StressTestStatus.RUNNING,
        params={"train_bars": 5, "test_bars": 2, "max_folds": 3},
    )

    executed: list[str] = []

    def spy_run(pine_source: str, *_: object, **__: object) -> Any:
        executed.append(pine_source)
        return MagicMock(folds=[], aggregate_oos_return=0.0)

    monkeypatch.setattr("src.stress_test.service.run_walk_forward", spy_run)
    monkeypatch.setattr("src.stress_test.service.wf_result_to_jsonb", lambda _r: {})

    await service._execute_walk_forward(st, parent)

    assert executed == [_PINE_A]


@pytest.mark.asyncio
async def test_walk_forward_optimization_executes_pinned_strategy_version(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`run_walk_forward_optimization` (true WFO) 경로가 A 를 실행한다."""
    parent, strategy_repo = await _seed_backtest_pinned_to_pine_a(db_session)
    service = _make_service(db_session, strategy_repo)
    st = StressTest(
        id=uuid4(),
        user_id=parent.user_id,
        backtest_id=parent.id,
        kind=StressTestKind.WALK_FORWARD,
        status=StressTestStatus.RUNNING,
        params={
            "train_bars": 5,
            "test_bars": 2,
            "max_folds": 3,
            "optimizer_param_space": _PARAM_SPACE_JSONB,
            "optimizer_kind": "grid_search",
        },
    )

    executed: list[str] = []

    def spy_run(pine_source: str, *_: object, **__: object) -> Any:
        executed.append(pine_source)
        return MagicMock(folds=[], aggregate_oos_return=0.0)

    monkeypatch.setattr("src.stress_test.service.run_walk_forward_optimization", spy_run)
    monkeypatch.setattr("src.stress_test.service.wf_result_to_jsonb", lambda _r: {})

    await service._execute_walk_forward(st, parent)

    assert executed == [_PINE_A]


@pytest.mark.asyncio
async def test_cost_assumption_executes_pinned_strategy_version(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`run_cost_assumption_sensitivity` (grid sweep) 경로가 A 를 실행한다."""
    parent, strategy_repo = await _seed_backtest_pinned_to_pine_a(db_session)
    service = _make_service(db_session, strategy_repo)
    st = StressTest(
        id=uuid4(),
        user_id=parent.user_id,
        backtest_id=parent.id,
        kind=StressTestKind.COST_ASSUMPTION_SENSITIVITY,
        status=StressTestStatus.RUNNING,
        params={"param_grid": {"fees": ["0.001", "0.002"], "slippage": ["0.0005"]}},
    )

    executed: list[str] = []

    def spy_run(pine_source: str, *_: object, **__: object) -> Any:
        executed.append(pine_source)
        return MagicMock(param1_name="fees", param2_name="slippage", cells=[])

    monkeypatch.setattr("src.stress_test.service.run_cost_assumption_sensitivity", spy_run)
    monkeypatch.setattr("src.stress_test.service.grid_metrics_result_to_jsonb", lambda _r: {})

    await service._execute_cost_assumption_sensitivity(st, parent)

    assert executed == [_PINE_A]


@pytest.mark.asyncio
async def test_param_stability_executes_pinned_strategy_version(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`run_param_stability` (grid sweep) 경로가 A 를 실행한다."""
    parent, strategy_repo = await _seed_backtest_pinned_to_pine_a(db_session)
    service = _make_service(db_session, strategy_repo)
    st = StressTest(
        id=uuid4(),
        user_id=parent.user_id,
        backtest_id=parent.id,
        kind=StressTestKind.PARAM_STABILITY,
        status=StressTestStatus.RUNNING,
        params={"param_grid": {"emaPeriod": ["10", "20"], "stopLossPct": ["0.5"]}},
    )

    executed: list[str] = []

    def spy_run(pine_source: str, *_: object, **__: object) -> Any:
        executed.append(pine_source)
        return MagicMock(param1_name="emaPeriod", param2_name="stopLossPct", cells=[])

    monkeypatch.setattr("src.stress_test.service.run_param_stability", spy_run)
    monkeypatch.setattr("src.stress_test.service.grid_metrics_result_to_jsonb", lambda _r: {})

    await service._execute_param_stability(st, parent)

    assert executed == [_PINE_A]


@pytest.mark.asyncio
async def test_legacy_backtest_without_pinned_version_falls_back_and_warns(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`strategy_version_id` NULL 인 legacy 행은 현재 Strategy 로 떨어지되 경고를 남긴다.

    이 경로는 결과가 옛 백테스트에 매달린 채 다른 소스로 실행되는 그 결함 자체다.
    폴백을 막을 수는 없으므로(핀할 스냅샷이 아예 없다) 검출 가능성만이라도 남긴다 —
    로그가 없으면 발생 사실이 결과·로그·메트릭 어디에도 흔적을 남기지 않는다.
    """
    parent, strategy_repo = await _seed_backtest_pinned_to_pine_a(db_session)
    parent.strategy_version_id = None  # PR #650 이전에 생성된 행
    await db_session.flush()

    service = _make_service(db_session, strategy_repo)
    st = StressTest(
        id=uuid4(),
        user_id=parent.user_id,
        backtest_id=parent.id,
        kind=StressTestKind.WALK_FORWARD,
        status=StressTestStatus.RUNNING,
        params={"train_bars": 5, "test_bars": 2, "max_folds": 3},
    )

    executed: list[str] = []

    def spy_run(pine_source: str, *_: object, **__: object) -> Any:
        executed.append(pine_source)
        return MagicMock(folds=[], aggregate_oos_return=0.0)

    monkeypatch.setattr("src.stress_test.service.run_walk_forward", spy_run)
    monkeypatch.setattr("src.stress_test.service.wf_result_to_jsonb", lambda _r: {})

    with caplog.at_level(logging.WARNING, logger="src.stress_test.service"):
        await service._execute_walk_forward(st, parent)

    # 핀할 스냅샷이 없으니 현재 소스(B)로 떨어진다 — 그 사실이 로그에 남아야 한다.
    assert executed == [_PINE_B]
    warnings = [
        record
        for record in caplog.records
        if record.message == "stress_test_run_without_pinned_strategy_version"
    ]
    assert len(warnings) == 1, (
        "legacy 폴백이 흔적을 안 남겼다 — 이 경로가 발생해도 검출 가능성이 0이다"
    )
    assert warnings[0].levelno == logging.WARNING


@pytest.mark.asyncio
async def test_missing_pinned_version_is_an_error_not_a_silent_fallback(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """핀된 version_id 가 있는데 그 행이 없으면 현재 소스로 조용히 떨어지지 않는다.

    ★이 상태는 **오늘의 DB 에서는 도달 불가**다 — `backtests.strategy_version_id` 의 FK 가
    `ondelete="RESTRICT"` 라 참조된 스냅샷은 지워지지 않는다(실측: 존재하지 않는 UUID 를
    넣으려 하면 `ForeignKeyViolationError`). 그래서 이 케이스만 repo 를 mock 으로 세운다.
    가드는 방어용이고 optimizer(`src/optimizer/service.py`)의 같은 가드와 짝이다 —
    없으면 「핀이 있는데 못 찾음」이 「현재 소스로 실행」과 구분되지 않는다.
    """
    parent, _ = await _seed_backtest_pinned_to_pine_a(db_session)
    assert parent.strategy_version_id is not None

    strategy_repo = AsyncMock()
    strategy_repo.get_version_by_id = AsyncMock(return_value=None)
    strategy_repo.find_by_id_and_owner = AsyncMock(
        side_effect=AssertionError("핀이 있는데 현재 Strategy 로 떨어졌다")
    )

    service = _make_service(db_session, strategy_repo)
    st = StressTest(
        id=uuid4(),
        user_id=parent.user_id,
        backtest_id=parent.id,
        kind=StressTestKind.WALK_FORWARD,
        status=StressTestStatus.RUNNING,
        params={"train_bars": 5, "test_bars": 2, "max_folds": 3},
    )

    executed: list[str] = []

    def spy_run(pine_source: str, *_: object, **__: object) -> Any:
        executed.append(pine_source)
        return MagicMock(folds=[], aggregate_oos_return=0.0)

    monkeypatch.setattr("src.stress_test.service.run_walk_forward", spy_run)
    monkeypatch.setattr("src.stress_test.service.wf_result_to_jsonb", lambda _r: {})

    with pytest.raises(ValueError, match="Strategy version no longer available"):
        await service._execute_walk_forward(st, parent)

    assert executed == [], "에러여야 할 자리에서 엔진이 돌았다"
