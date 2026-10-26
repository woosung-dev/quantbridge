"""실제 코드 실행 경로의 취소 경쟁·실패·원장 commit 순서를 검증한다."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pandas as pd
import pytest

from src.backtest.models import Backtest, BacktestStatus
from src.backtest.service import BacktestService
from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.models import StrategyVersion


class ExecutionCase:
    """Repository·시세·격리 transport의 실제 관찰점만 대역 처리한다."""

    def __init__(
        self, monkeypatch, *, cancel=None, failure=None, lose_terminal=False, funding=False, research=None
    ):
        self.events = []
        self.cancel = cancel
        self.failure = failure
        self.lose_terminal = lose_terminal
        self.reads = 0
        code = CodeSnapshot(
            execution_policy="code_research_v1" if research else "code_v1",
            language="python",
            source_code="transport fake only",
            warmup_bars=2,
            provenance={"research_execution": research} if research else {"kind": "manual"},
        )
        strategy_id = uuid4()
        version = StrategyVersion(
            strategy_id=strategy_id,
            pine_source=None,
            source_hash=code.source_hash,
            language="python",
            source_code=code.source_code,
            execution_policy=code.execution_policy,
            warmup_bars=code.warmup_bars,
            params=code.params,
            provenance=code.provenance,
            execution_hash=code.execution_hash,
        )
        start = datetime(2026, 1, 1, tzinfo=UTC)
        self.bt = Backtest(
            user_id=uuid4(),
            strategy_id=strategy_id,
            strategy_version_id=version.id,
            engine_version=code.execution_policy,
            symbol="BTC/USDT",
            timeframe="1h",
            period_start=start,
            period_end=start + timedelta(hours=3),
            initial_capital=Decimal("10000"),
            status=BacktestStatus.CANCELLING if cancel == "pickup" else BacktestStatus.QUEUED,
            config={
                "execution_hash": code.execution_hash,
                "include_funding": funding,
                "fees": 0,
                "slippage": 0,
                "default_qty_type": "strategy.fixed",
                "default_qty_value": 1,
                "fill_timing": "next_bar_open",
            },
        )
        if research:
            self.bt.config["research_execution"] = research
            self.bt.config["risk_policy"] = research["exit_policy"]
        self.parent = self._frame(pd.date_range(start - timedelta(hours=2), periods=5, freq="h"))
        self.minutes = self._frame(pd.date_range(start, periods=180, freq="min"))
        self.repo = AsyncMock()
        self.repo.get_by_id.side_effect = self._get
        self.repo.transition_to_running.side_effect = self._running
        self.repo.finalize_cancelled.side_effect = self._cancelled
        self.repo.complete.side_effect = self._complete
        self.repo.fail.side_effect = self._fail
        self.repo.commit.side_effect = lambda: self.events.append("commit")
        self.repo.insert_trades_bulk.side_effect = lambda _: self.events.append("trades")
        self.provider = SimpleNamespace(get_ohlcv=AsyncMock(side_effect=self._ohlcv))
        strategy_repo = AsyncMock()
        strategy_repo.get_version_by_id.return_value = version
        strategy_repo.find_by_id_and_owner.return_value = SimpleNamespace(name="code")
        self.funding = AsyncMock()
        self.funding.get_funding_series.side_effect = self._funding
        self.service = BacktestService(
            repo=self.repo,
            strategy_repo=strategy_repo,
            ohlcv_provider=self.provider,
            dispatcher=Mock(),
            funding_repo=self.funding,
        )
        self.push = Mock()
        monkeypatch.setattr("src.backtest.service.enqueue_push", self.push)
        self.legacy = Mock(side_effect=AssertionError("legacy must not execute"))
        monkeypatch.setattr("src.backtest.service.run_backtest", self.legacy)
        monkeypatch.setattr(
            "src.strategy.code_runtime.session.create_code_transport", lambda *args, **kwargs: self
        )

    @staticmethod
    def _frame(index):
        return pd.DataFrame(
            {
                "open": Decimal(100),
                "high": Decimal(101),
                "low": Decimal(99),
                "close": Decimal(100),
                "volume": Decimal(1),
            },
            index=index,
        )

    async def _get(self, identifier, *, defer_equity_curve=False):
        assert identifier == self.bt.id
        if not defer_equity_curve:
            self.reads += 1
            if (self.cancel == "pre_engine" and self.reads == 2) or (
                self.cancel == "post_engine" and self.reads == 3
            ):
                self.bt.status = BacktestStatus.CANCELLING
        return self.bt

    async def _running(self, identifier, *, started_at):
        self.events.append("running")
        self.bt.status = (
            BacktestStatus.CANCELLING if self.cancel == "cas" else BacktestStatus.RUNNING
        )
        return 0 if self.cancel == "cas" else 1

    async def _cancelled(self, identifier, *, completed_at):
        self.events.append("cancelled")
        self.bt.status = BacktestStatus.CANCELLED
        return 1

    async def _complete(self, identifier, **kwargs):
        self.events.append("complete")
        self.bt.status = (
            BacktestStatus.CANCELLING if self.lose_terminal else BacktestStatus.COMPLETED
        )
        return 0 if self.lose_terminal else 1

    async def _fail(self, identifier, *, error, where_status=None):
        self.events.append("fail")
        if where_status is not None:
            assert self.bt.status == where_status
        self.bt.error = error
        self.bt.status = BacktestStatus.CANCELLING if self.lose_terminal else BacktestStatus.FAILED
        return 0 if self.lose_terminal else 1

    async def _ohlcv(self, symbol, timeframe, start, end):
        phase = "minutes" if timeframe == "1m" else "parent"
        self.events.append(phase)
        if self.failure == phase:
            raise RuntimeError(f"{phase} unavailable")
        return self.minutes if phase == "minutes" else self.parent

    async def _funding(self, **kwargs):
        self.events.append("funding")
        if self.failure == "funding":
            raise RuntimeError("funding unavailable")
        return pd.Series([Decimal("0")], index=self.minutes.index[[0]], dtype=object)

    def exchange(self, message):
        if message["type"] == "init":
            self.events.append("runtime")
            if self.failure == "runtime":
                raise CodeRuntimeError("runtime unavailable")
            return {"ready": 1}
        action = {2: "long", 3: "close"}.get(message["bar"]["index"], "hold")
        return {"intent": {"action": action}}

    def close(self):
        self.events.append("cleanup")


@pytest.mark.asyncio
@pytest.mark.parametrize("funding", [False, True])
async def test_complete_and_trade_insert_share_terminal_commit(monkeypatch, funding):
    case = ExecutionCase(monkeypatch, funding=funding)
    await case.service.run(case.bt.id)
    prefix = ["parent", "running", "commit"] + (["funding"] if funding else [])
    assert case.events == [*prefix, "minutes", "runtime", "cleanup", "complete", "trades", "commit"]
    assert case.bt.status == BacktestStatus.COMPLETED
    assert case.repo.commit.await_count == 2
    assert len(case.repo.insert_trades_bulk.call_args.args[0]) == 1
    coverage = case.repo.complete.call_args.kwargs["data_coverage"]
    assert coverage["bar_count"] == coverage["expected_bars"] == 3
    assert coverage["missing_bars"] == 0
    assert len(case.repo.complete.call_args.kwargs["equity_curve"]) == 180
    case.repo.fail.assert_not_awaited()
    case.push.assert_called_once()
    case.legacy.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cancel", "events"),
    [
        ("pickup", ["cancelled", "commit"]),
        ("cas", ["parent", "running", "cancelled", "commit"]),
        ("pre_engine", ["parent", "running", "commit", "cancelled", "commit"]),
        (
            "post_engine",
            ["parent", "running", "commit", "minutes", "runtime", "cleanup", "cancelled", "commit"],
        ),
    ],
)
async def test_each_cancel_phase_stops_at_its_own_guard(monkeypatch, cancel, events):
    case = ExecutionCase(monkeypatch, cancel=cancel)
    await case.service.run(case.bt.id)
    assert case.events == events
    assert case.bt.status == BacktestStatus.CANCELLED
    case.repo.finalize_cancelled.assert_awaited_once()
    case.repo.complete.assert_not_awaited()
    case.repo.insert_trades_bulk.assert_not_awaited()
    case.repo.fail.assert_not_awaited()
    assert case.repo.commit.await_count == events.count("commit")
    case.push.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "events", "error"),
    [
        ("parent", ["parent", "fail", "commit"], "OHLCV fetch failed: parent unavailable"),
        (
            "minutes",
            ["parent", "running", "commit", "minutes", "fail", "commit"],
            "minutes unavailable",
        ),
        (
            "runtime",
            ["parent", "running", "commit", "minutes", "runtime", "cleanup", "fail", "commit"],
            "runtime unavailable",
        ),
    ],
)
async def test_failure_keeps_its_phase_error_and_commit(monkeypatch, failure, events, error):
    case = ExecutionCase(monkeypatch, failure=failure)
    await case.service.run(case.bt.id)
    assert case.events == events
    assert case.bt.status == BacktestStatus.FAILED
    assert case.bt.error == error
    assert case.repo.commit.await_count == events.count("commit")
    kwargs = case.repo.fail.call_args.kwargs
    assert kwargs.get("where_status") == (BacktestStatus.QUEUED if failure == "parent" else None)
    case.repo.complete.assert_not_awaited()
    case.repo.insert_trades_bulk.assert_not_awaited()
    case.push.assert_called_once()
    case.legacy.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "minutes"])
async def test_terminal_cas_loss_cancels_without_trade_write_or_push(monkeypatch, failure):
    case = ExecutionCase(monkeypatch, failure=failure, lose_terminal=True)
    await case.service.run(case.bt.id)
    terminal = ["fail"] if failure else ["runtime", "cleanup", "complete"]
    assert case.events == [
        "parent",
        "running",
        "commit",
        "minutes",
        *terminal,
        "cancelled",
        "commit",
    ]
    assert case.bt.status == BacktestStatus.CANCELLED
    case.repo.finalize_cancelled.assert_awaited_once()
    case.repo.insert_trades_bulk.assert_not_awaited()
    assert case.repo.commit.await_count == 2
    case.push.assert_not_called()


@pytest.mark.asyncio
async def test_funding_failure_stays_outside_execution_failure_handler(monkeypatch):
    case = ExecutionCase(monkeypatch, failure="funding", funding=True)
    with pytest.raises(RuntimeError, match="funding unavailable"):
        await case.service.run(case.bt.id)
    assert case.events == ["parent", "running", "commit", "funding"]
    assert case.bt.status == BacktestStatus.RUNNING
    case.repo.commit.assert_awaited_once()
    case.repo.fail.assert_not_awaited()
    case.repo.complete.assert_not_awaited()
    case.push.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("exit_policy", ["signal_only_v1", "swing_two_bar_v1"])
async def test_research_policy_reaches_actual_engine_and_keeps_terminal_commit(monkeypatch, exit_policy):
    from src.strategy.code_runtime.backtest import run_code_backtest
    from src.strategy.research_contract import ResearchExecution

    policy = {
        "contract_version": 1,
        "exit_policy": exit_policy,
        "reentry_policy": "close_then_reenter_v1",
        "signal_mode": "shared_events",
        "signal_mapping_hash": "a" * 64,
    }
    case = ExecutionCase(monkeypatch, research=policy)
    engine = Mock(wraps=run_code_backtest)
    monkeypatch.setattr("src.strategy.product_execution.run_code_backtest", engine)
    await case.service.run(case.bt.id)
    assert case.bt.status == BacktestStatus.COMPLETED
    assert engine.call_args.kwargs["research_policy"] == ResearchExecution.model_validate(policy)
    assert case.bt.config["research_execution"] == policy
    assert case.repo.commit.await_count == 2
    assert exit_policy in case.repo.complete.call_args.kwargs["warnings"][0]
    case.legacy.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("engine_policy", ["code_v1", "pine_v2"])
async def test_research_version_cannot_enter_another_engine_policy(monkeypatch, engine_policy):
    policy = {
        "contract_version": 1,
        "exit_policy": "signal_only_v1",
        "reentry_policy": "close_then_reenter_v1",
        "signal_mode": "shared_events",
        "signal_mapping_hash": "a" * 64,
    }
    case = ExecutionCase(monkeypatch, research=policy)
    case.bt.engine_version = engine_policy
    await case.service.run(case.bt.id)
    assert case.bt.status == BacktestStatus.FAILED
    assert case.bt.error == "Strategy version execution policy mismatch"
    assert case.events == ["fail", "commit"]
    case.legacy.assert_not_called()
