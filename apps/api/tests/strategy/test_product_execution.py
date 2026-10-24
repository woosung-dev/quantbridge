"""제품 실행 객체의 준비·후기 검증·실제 runtime 전달을 외부 transport 대역으로 검증한다."""

from datetime import UTC, datetime
from decimal import Decimal
from threading import get_ident
from unittest.mock import AsyncMock, Mock, call
from uuid import uuid4

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.models import Backtest, BacktestStatus
from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.exceptions import CodeStrategyPolicyError
from src.strategy.models import StrategyVersion
from src.strategy.product_execution import CodeBacktestExecution
from src.strategy.python_runtime.protocol import PythonRuntimeError
from tests.strategy.code_runtime.test_backtest import Tape

D = Decimal


def inputs(timeframe="1h", language="python"):
    code = CodeSnapshot(
        execution_policy="code_v1",
        language=language,
        source_code="unexecuted source carried to the transport fake",
        warmup_bars=2,
        params={"length": 3},
        provenance={"kind": "manual"},
    )
    strategy_id = uuid4()
    version = StrategyVersion(
        strategy_id=strategy_id,
        source_hash=code.source_hash,
        execution_hash=code.execution_hash,
        execution_policy="code_v1",
        language=language,
        source_code=code.source_code,
        warmup_bars=code.warmup_bars,
        params=code.params,
        provenance=code.provenance,
    )
    start = datetime(2026, 1, 3, tzinfo=UTC)
    width = pd.Timedelta(timeframe)
    end = start + 3 * width
    backtest = Backtest(
        user_id=uuid4(),
        strategy_id=strategy_id,
        strategy_version_id=version.id,
        engine_version="code_v1",
        symbol="BTC/USDT",
        timeframe=timeframe,
        period_start=start,
        period_end=end,
        initial_capital=D(10000),
        status=BacktestStatus.QUEUED,
        config={"execution_hash": code.execution_hash},
    )
    parent = pd.DataFrame(
        {"open": D(100), "high": D(101), "low": D(99), "close": D(100), "volume": D(60)},
        index=pd.date_range(start - 2 * width, end, freq=timeframe, inclusive="left"),
    )
    child = pd.DataFrame(
        {"open": D(100), "high": D(101), "low": D(99), "close": D(100), "volume": D(1)},
        index=pd.date_range(start, end, freq="1min", inclusive="left"),
    )
    return backtest, version, parent, child


def config(*, include_funding=False):
    return BacktestConfig(
        freq="1h",
        fees=0,
        slippage=0,
        maker_fee=0,
        default_qty_type="strategy.fixed",
        default_qty_value=10,
        include_funding=include_funding,
    )


@pytest.fixture(autouse=True)
def transport_factory(monkeypatch):
    factory = Mock(side_effect=AssertionError("이 테스트는 실제 격리 실행기를 만들지 않는다"))
    monkeypatch.setattr("src.strategy.code_runtime.session.create_code_transport", factory)
    return factory


@pytest.mark.parametrize("timeframe", ["1h", "4h", "1d"])
async def test_prepare_loads_exact_warmup_range_and_keeps_the_original_frame(
    timeframe, transport_factory
):
    backtest, version, parent, _ = inputs(timeframe)
    provider = AsyncMock()
    provider.get_ohlcv.return_value = parent

    execution = await CodeBacktestExecution.prepare(backtest, version, provider=provider)

    assert execution.signal_ohlcv is parent
    provider.get_ohlcv.assert_awaited_once_with(
        backtest.symbol,
        timeframe,
        backtest.period_start - 2 * pd.Timedelta(timeframe),
        backtest.period_end,
    )
    assert parent.index[-1] == backtest.period_end - pd.Timedelta(timeframe)
    transport_factory.assert_not_called()


@pytest.mark.parametrize("change", ["missing", "duplicate", "reversed", "shifted", "inclusive_end"])
async def test_prepare_rejects_parent_gaps_duplicates_order_and_boundary_changes(change):
    backtest, version, parent, _ = inputs()
    if change == "missing":
        parent = parent.drop(parent.index[2])
    elif change == "duplicate":
        parent = pd.concat([parent.iloc[:2], parent.iloc[1:]])
    elif change == "reversed":
        parent = parent.iloc[::-1]
    elif change == "shifted":
        parent.index += pd.Timedelta(minutes=1)
    else:
        parent = pd.concat([parent, parent.iloc[-1:].set_axis([pd.Timestamp(backtest.period_end)])])
    provider = AsyncMock()
    provider.get_ohlcv.return_value = parent

    with pytest.raises(CodeStrategyPolicyError, match="워밍업과 평가 봉"):
        await CodeBacktestExecution.prepare(backtest, version, provider=provider)

    provider.get_ohlcv.assert_awaited_once()


@pytest.mark.parametrize("field", ["source_hash", "execution_hash"])
async def test_invalid_version_is_rejected_before_parent_query(field):
    backtest, version, _, _ = inputs()
    setattr(version, field, "changed")
    provider = AsyncMock()

    with pytest.raises(CodeStrategyPolicyError):
        await CodeBacktestExecution.prepare(backtest, version, provider=provider)

    provider.get_ohlcv.assert_not_awaited()


async def test_prepare_revalidates_version_after_provider_await():
    backtest, version, parent, _ = inputs()
    provider = AsyncMock()

    async def load(*args):
        version.source_code = "changed while loading parent bars"
        return parent

    provider.get_ohlcv.side_effect = load

    with pytest.raises(CodeStrategyPolicyError):
        await CodeBacktestExecution.prepare(backtest, version, provider=provider)

    provider.get_ohlcv.assert_awaited_once()


@pytest.mark.parametrize(
    "change", ["saved_hash", "missing_config", "source", "source_hash", "version_hash", "strategy"]
)
async def test_run_revalidates_current_references_before_execution_query(change, transport_factory):
    backtest, version, parent, child = inputs()
    provider = AsyncMock()
    provider.get_ohlcv.side_effect = [parent, child]
    execution = await CodeBacktestExecution.prepare(backtest, version, provider=provider)
    if change == "saved_hash":
        backtest.config["execution_hash"] = "changed after prepare"
    elif change == "missing_config":
        backtest.config = None
    elif change == "source":
        version.source_code = "changed after prepare"
    elif change == "source_hash":
        version.source_hash = "changed after prepare"
    elif change == "version_hash":
        version.execution_hash = "changed after prepare"
    else:
        version.strategy_id = uuid4()

    with pytest.raises(CodeStrategyPolicyError):
        await execution.run(config(), funding_rates=None)

    provider.get_ohlcv.assert_awaited_once()
    transport_factory.assert_not_called()


async def test_strategy_ownership_is_checked_in_run_after_parent_preparation(transport_factory):
    backtest, version, parent, _ = inputs()
    version.strategy_id = uuid4()
    provider = AsyncMock()
    provider.get_ohlcv.return_value = parent
    execution = await CodeBacktestExecution.prepare(backtest, version, provider=provider)

    with pytest.raises(CodeStrategyPolicyError):
        await execution.run(config(), funding_rates=None)

    provider.get_ohlcv.assert_awaited_once()
    transport_factory.assert_not_called()


@pytest.mark.parametrize("language", ["pine", "python", "typescript"])
@pytest.mark.parametrize("include_funding", [False, True])
async def test_run_uses_minute_bars_thread_and_actual_runtime_with_transport_fake(
    language, include_funding, transport_factory
):
    backtest, version, parent, child = inputs(language=language)
    provider = AsyncMock()
    provider.get_ohlcv.side_effect = [parent, child]
    tape = Tape(
        {
            0: {"action": "long"},
            1: {"action": "long"},
            2: {"action": "long"},
            3: {"action": "close"},
        }
    )
    caller_thread = get_ident()
    runtime_threads = []

    def create(selected, bars, *, timeout):
        assert selected == language
        assert bars is parent
        assert timeout == 900
        assert provider.get_ohlcv.await_count == 2
        runtime_threads.append(get_ident())
        return tape

    transport_factory.side_effect = create
    execution = await CodeBacktestExecution.prepare(backtest, version, provider=provider)
    rates = pd.Series([D("0.001")], index=child.index[[90]])

    result = await execution.run(config(include_funding=include_funding), funding_rates=rates)

    assert provider.get_ohlcv.await_args_list == [
        call(
            backtest.symbol,
            "1h",
            backtest.period_start - pd.Timedelta(hours=2),
            backtest.period_end,
        ),
        call(backtest.symbol, "1m", backtest.period_start, backtest.period_end),
    ]
    assert runtime_threads and runtime_threads[0] != caller_thread
    assert tape.messages[0] == {
        "type": "init",
        "protocol": 1,
        "source": version.source_code,
        "params": {"length": 3},
    }
    assert len(tape.messages) == 6
    assert all(message["position"]["direction"] == "flat" for message in tape.messages[1:4])
    assert tape.closed
    assert result.equity_curve.index.equals(child.index)
    assert result.equity_curve.iloc[0] == D(10000)
    assert result.equity_curve.iloc[-1] == D(9999 if include_funding else 10000)
    assert result.metrics.total_funding == (D(1) if include_funding else None)
    assert result.metrics.net_profit_abs == D(-1 if include_funding else 0)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert (trade.entry_bar_index, trade.exit_bar_index) == (60, 120)
    assert (trade.entry_price, trade.exit_price, trade.size) == (D(100), D(100), D(10))
    assert trade.pnl == D(-1 if include_funding else 0)


@pytest.mark.parametrize("phase", ["parent", "execution", "runtime"])
async def test_provider_and_runtime_errors_preserve_the_original_exception(
    phase, transport_factory
):
    backtest, version, parent, child = inputs()
    original = (
        CodeRuntimeError("runner unavailable")
        if phase == "runtime"
        else OSError("data unavailable")
    )
    provider = AsyncMock()
    provider.get_ohlcv.side_effect = (
        [original] if phase == "parent" else [parent, original if phase == "execution" else child]
    )
    transport_factory.side_effect = original

    with pytest.raises(type(original)) as raised:
        execution = await CodeBacktestExecution.prepare(backtest, version, provider=provider)
        await execution.run(config(), funding_rates=None)

    assert raised.value is original
    assert provider.get_ohlcv.await_count == (1 if phase == "parent" else 2)
    if phase != "runtime":
        transport_factory.assert_not_called()


@pytest.mark.parametrize("change", ["missing", "different_high"])
async def test_run_preserves_child_range_and_parent_aggregation_validation(
    change, transport_factory
):
    backtest, version, parent, child = inputs()
    if change == "missing":
        child = child.drop(child.index[70])
    else:
        child.loc[child.index[70], "high"] = D(102)
    provider = AsyncMock()
    provider.get_ohlcv.side_effect = [parent, child]
    execution = await CodeBacktestExecution.prepare(backtest, version, provider=provider)

    with pytest.raises(PythonRuntimeError):
        await execution.run(config(), funding_rates=None)

    transport_factory.assert_not_called()
