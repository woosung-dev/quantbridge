"""code_v1 소유권·불변 snapshot·commit과 legacy 우회 방지. DB/작업큐를 쓰지 않는다."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.strategy.code_contract import CodeSnapshot, legacy_pine_source, read_code_version
from src.strategy.code_schemas import SaveCodeStrategyRequest
from src.strategy.code_service import CodeStrategyService
from src.strategy.exceptions import CodeStrategyPolicyError, StrategyNotFoundError
from src.strategy.models import ParseStatus, Strategy, StrategyVersion
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest
from src.strategy.service import StrategyService


def snapshot(**changes):
    return CodeSnapshot.model_validate(
        {
            "execution_policy": "code_v1",
            "language": "python",
            "source_code": 'def on_bar(ctx, state):\n    return {"action": "hold"}\n',
            "warmup_bars": 50,
            "params": {"length": 20},
            "provenance": {"model": "sol-6.1"},
            **changes,
        }
    )


def version(strategy_id, code):
    return StrategyVersion(
        strategy_id=strategy_id,
        pine_source=None,
        source_hash=code.source_hash,
        parser_version="code_v1",
        language=code.language.value,
        source_code=code.source_code,
        execution_policy="code_v1",
        warmup_bars=code.warmup_bars,
        params=code.params,
        provenance=code.provenance,
        execution_hash=code.execution_hash,
    )


def fixture():
    code = snapshot()
    strategy = Strategy(
        user_id=uuid4(),
        name="code",
        parse_status=ParseStatus.unsupported,
        source_language="python",
        execution_policy="code_v1",
    )
    pinned = version(strategy.id, code)
    strategy.strategy_version_id = pinned.id
    repo = AsyncMock()
    repo.create.side_effect = lambda item: item
    repo.find_by_id_and_owner.return_value = strategy
    repo.get_version_by_id.return_value = pinned
    repo.create_code_version.side_effect = lambda *, strategy_id, code: version(strategy_id, code)
    return repo, strategy, pinned


@pytest.mark.asyncio
async def test_create_and_update_append_versions_commit_once_each():
    repo, strategy, original = fixture()
    svc = CodeStrategyService(repo)
    req = SaveCodeStrategyRequest(name="new", code=snapshot())
    created = await svc.create(req, owner_id=strategy.user_id)
    assert created.version.source_hash == snapshot().source_hash
    saved = repo.create.call_args.args[0]
    assert saved.pine_source is None and saved.pine_version is None
    repo.commit.assert_awaited_once()
    repo.commit.reset_mock()
    updated = await svc.update(strategy.id, req, owner_id=strategy.user_id)
    assert updated.version.id != original.id
    assert original.source_code == snapshot().source_code
    repo.commit.assert_awaited_once()
    repo.update.assert_awaited_once()
    assert repo.create_code_version.await_count == 2


@pytest.mark.asyncio
async def test_code_settings_are_validated_saved_and_returned():
    repo, strategy, _ = fixture()
    req = SaveCodeStrategyRequest(
        name="code",
        code=snapshot(),
        settings={
            "leverage": 1,
            "margin_mode": "isolated",
            "position_size_pct": 10,
            "fill_timing": "next_bar_open",
        },
    )
    result = await CodeStrategyService(repo).create(req, owner_id=strategy.user_id)
    assert result.settings is not None and result.settings.position_size_pct == 10
    repo.commit.assert_awaited_once()
    repo.commit.reset_mock()
    updated = await CodeStrategyService(repo).update(strategy.id, req, owner_id=strategy.user_id)
    assert updated.settings.fill_timing == "next_bar_open"
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_owner_has_no_snapshot_or_write_access():
    repo, strategy, _ = fixture()
    repo.find_by_id_and_owner.return_value = None
    other = uuid4()
    with pytest.raises(StrategyNotFoundError):
        await CodeStrategyService(repo).get(strategy.id, owner_id=other)
    repo.find_by_id_and_owner.assert_awaited_once_with(strategy.id, other)
    repo.get_version_by_id.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_code", "changed"),
        ("language", "typescript"),
        ("warmup_bars", 51),
        ("params", {"length": 21}),
        ("provenance", {"model": "other"}),
        ("source_hash", "0" * 64),
        ("execution_hash", "0" * 64),
    ],
)
def test_snapshot_tampering_is_rejected(field, value):
    _, strategy, pinned = fixture()
    setattr(pinned, field, value)
    with pytest.raises(CodeStrategyPolicyError):
        read_code_version(pinned, strategy_id=strategy.id)


def test_allowlist_policy_and_legacy_payload_boundaries():
    for changes in ({"language": "javascript"}, {"execution_policy": None}, {"warmup_bars": 0}):
        with pytest.raises(ValidationError):
            snapshot(**changes)
    with pytest.raises(ValidationError):
        CreateStrategyRequest(name="x", pine_source="x", language="python")
    with pytest.raises(ValidationError):
        UpdateStrategyRequest(source_code="x")
    _, strategy, pinned = fixture()
    for row in (strategy, pinned):
        with pytest.raises(CodeStrategyPolicyError):
            legacy_pine_source(row)


@pytest.mark.asyncio
async def test_legacy_get_and_update_reject_code_before_mutation():
    repo, strategy, _ = fixture()
    svc = StrategyService(repo=repo)
    with pytest.raises(CodeStrategyPolicyError):
        await svc.get(strategy_id=strategy.id, owner_id=strategy.user_id)
    with pytest.raises(CodeStrategyPolicyError):
        await svc.update(
            strategy_id=strategy.id,
            data=UpdateStrategyRequest(name="changed"),
            owner_id=strategy.user_id,
        )
    assert strategy.name == "code"
    repo.update.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_code_submit_requires_optin_and_dispatches_pinned_version():
    strategy_repo, strategy, pinned = fixture()
    repo = AsyncMock()
    dispatcher = Mock()
    dispatcher.dispatch_backtest.return_value = "task-id"
    svc = BacktestService(
        repo=repo, strategy_repo=strategy_repo, ohlcv_provider=AsyncMock(), dispatcher=dispatcher
    )
    req = CreateBacktestRequest(
        strategy_id=strategy.id,
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        fill_timing="next_bar_open",
    )
    with pytest.raises(CodeStrategyPolicyError):
        await svc.submit(req, user_id=strategy.user_id)
    repo.create.assert_not_awaited()
    result = await svc.submit(
        req.model_copy(update={"execution_policy": "code_v1"}), user_id=strategy.user_id
    )
    saved = repo.create.call_args.args[0]
    assert saved.strategy_version_id == pinned.id
    assert saved.engine_version == "code_v1"
    assert saved.config["execution_hash"] == snapshot().execution_hash
    assert result.status.value == "queued"
    dispatcher.dispatch_backtest.assert_called_once_with(saved.id)
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_code_dispatch_failure_rolls_back_without_commit():
    from src.backtest.exceptions import TaskDispatchError

    strategy_repo, strategy, _ = fixture()
    repo = AsyncMock()
    dispatcher = Mock()
    dispatcher.dispatch_backtest.side_effect = RuntimeError("queue unavailable")
    svc = BacktestService(
        repo=repo, strategy_repo=strategy_repo, ohlcv_provider=AsyncMock(), dispatcher=dispatcher
    )
    req = CreateBacktestRequest(
        strategy_id=strategy.id,
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        fill_timing="next_bar_open",
        execution_policy="code_v1",
    )
    with pytest.raises(TaskDispatchError):
        await svc.submit(req, user_id=strategy.user_id)
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_code_worker_unavailable_is_failed_and_never_calls_legacy(monkeypatch):
    import pandas as pd

    from src.backtest.models import Backtest, BacktestStatus
    from src.strategy.python_runtime.protocol import PythonRunnerUnavailable

    strategy_repo, strategy, pinned = fixture()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    bt = Backtest(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        strategy_version_id=pinned.id,
        engine_version="code_v1",
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=start,
        period_end=end,
        initial_capital=Decimal("10000"),
        status=BacktestStatus.QUEUED,
        config={"execution_hash": pinned.execution_hash, "include_funding": False},
    )
    repo = AsyncMock()
    repo.get_by_id.return_value = bt
    repo.transition_to_running.return_value = 1
    repo.fail.return_value = 1
    provider = AsyncMock()
    index = pd.date_range(
        pd.Timestamp(start) - pd.Timedelta(hours=50), end, freq="h", inclusive="left"
    )
    parent = pd.DataFrame(
        {k: [Decimal("100")] * len(index) for k in ("open", "high", "low", "close", "volume")},
        index=index,
    )
    provider.get_ohlcv.side_effect = [parent, parent]
    native = Mock(side_effect=PythonRunnerUnavailable("image unavailable"))
    legacy = Mock(side_effect=AssertionError("legacy must not execute"))
    monkeypatch.setattr("src.strategy.product_execution.run_product_backtest", native)
    monkeypatch.setattr("src.backtest.service.run_backtest", legacy)
    svc = BacktestService(
        repo=repo, strategy_repo=strategy_repo, ohlcv_provider=provider, dispatcher=Mock()
    )
    assert await svc._run(bt.id) == BacktestStatus.FAILED
    assert "image unavailable" in repo.fail.call_args.kwargs["error"]
    legacy.assert_not_called()
    native.assert_called_once()
    assert repo.commit.await_count == 2


@pytest.mark.asyncio
async def test_code_worker_legacy_engine_cannot_execute_code_version():
    from src.backtest.models import Backtest, BacktestStatus

    strategy_repo, strategy, pinned = fixture()
    bt = Backtest(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        strategy_version_id=pinned.id,
        engine_version="pine_v2",
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.QUEUED,
    )
    repo, provider = AsyncMock(), AsyncMock()
    repo.get_by_id.return_value = bt
    repo.fail.return_value = 1
    svc = BacktestService(
        repo=repo, strategy_repo=strategy_repo, ohlcv_provider=provider, dispatcher=Mock()
    )
    assert await svc._run(bt.id) == BacktestStatus.FAILED
    provider.get_ohlcv.assert_not_awaited()
    repo.commit.assert_awaited_once()
