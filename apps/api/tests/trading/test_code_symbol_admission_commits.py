"""실제 service 분기에서 등록/신규 진입 가드 순서와 축소 허용을 검증한다."""

from decimal import Decimal as D
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.exceptions import SessionAlreadyActive
from src.trading.services.code_live_execution_service import CodeLiveExecutionService
from src.trading.services.code_risk_service import CodeRiskReconciliationPending
from src.trading.services.live_session_service import LiveSignalSessionService
from tests.trading.test_code_risk_executor import runtime as make_runtime
from tests.trading.test_live_session_commits import (
    _make_account,
    _make_balance_service,
    _make_req,
    _make_strategy,
)


@pytest.fixture
def runtime():
    return make_runtime.__wrapped__()


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("code", [True, False])
async def test_register_admission_precedes_save_and_only_success_commits(
    monkeypatch, allowed, code, runtime
):
    from uuid import uuid4

    user_id = uuid4()
    account, strategy = _make_account(user_id), _make_strategy(user_id)
    *_, live, version, _account = runtime
    if code:
        account.read_only = False
        strategy.execution_policy = "code_v1"
        strategy.settings = live.execution_snapshot["execution_settings"]
    repo, accounts, strategies = AsyncMock(), AsyncMock(), AsyncMock()
    accounts.get_by_id.return_value = account
    strategies.find_by_id_and_owner.return_value = strategy
    strategies.get_version_by_id.return_value = version
    repo.count_active_by_user.return_value = 0
    repo.acquire_code_symbol_admission.return_value = allowed
    repo.save.side_effect = lambda row: row
    sequence = []
    repo.acquire_quota_lock.side_effect = lambda _: sequence.append("quota")
    repo.acquire_code_symbol_admission.side_effect = lambda *args, **kwargs: (
        sequence.append("admission") or allowed
    )
    repo.save.side_effect = lambda row: sequence.append("save") or row
    repo.commit.side_effect = lambda: sequence.append("commit")
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    kick = MagicMock()
    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", kick)
    service = LiveSignalSessionService(
        repo,
        accounts,
        strategies,
        balance_service=_make_balance_service(),
        exclusivity_service=AsyncMock(),
        risk_service=AsyncMock(),
        risk_executor=AsyncMock(),
    )
    req = _make_req(strategy.id, account.id)
    if code:
        from src.trading.schemas import RegisterLiveSessionRequest

        req = RegisterLiveSessionRequest(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTCUSDT",
            interval="1h",
            source_policy="code_v1",
            strategy_version_id=version.id,
        )
    if allowed:
        await service.register(user_id, req)
        assert sequence == ["quota", "admission", "save", "commit"]
        repo.commit.assert_awaited_once()
        kick.assert_called_once()
    else:
        with pytest.raises(SessionAlreadyActive):
            await service.register(user_id, req)
        assert sequence == ["quota", "admission"]
        repo.save.assert_not_awaited()
        repo.commit.assert_not_awaited()
        kick.assert_not_called()
    repo.acquire_code_symbol_admission.assert_awaited_once_with(
        account.id, "BTC/USDT", is_code=code
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", [True, False])
async def test_fresh_entry_rechecks_after_kill_switch_commit_before_saving(runtime, allowed):
    _, _, repo, _, _stored, _, live, *_ = runtime
    repo.get.return_value = None
    repo.get.side_effect = None
    repo.get_order.return_value = None
    repo.has_unsettled_exit_for_account.return_value = False
    sequence = []
    gate, orders, risk, executor = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()

    async def kill_switch(*_):
        sequence.append("kill_switch_commit")
        await repo.commit()

    gate.side_effect = kill_switch
    repo.acquire_entry_admission.side_effect = lambda _: sequence.append("admission") or allowed
    orders.save.side_effect = lambda _: sequence.append("save")

    async def prepare(*args, **kwargs):
        sequence.append("prepare_commit")
        await repo.commit()

    risk.prepare_entry.side_effect = prepare
    service = CodeLiveExecutionService(repo, orders, risk, executor, entry_gate=gate)

    async def run():
        return await service.on_intent(
            live.id,
            "long",
            intent_key="bar",
            estimated_entry=D(100),
            quantity=D(2),
            previous_bars=[{"low": D(98), "high": D(102)}] * 2,
            qty_step=D("0.1"),
            min_qty=D("0.1"),
        )

    if allowed:
        await run()
        assert sequence == ["kill_switch_commit", "admission", "save", "prepare_commit"]
        assert repo.commit.await_count == 2
    else:
        with pytest.raises(CodeRiskReconciliationPending):
            await run()
        assert sequence == ["kill_switch_commit", "admission"]
        orders.save.assert_not_awaited()
        risk.prepare_entry.assert_not_awaited()
        repo.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["hold", "close", "short"])
async def test_existing_exposure_can_be_protected_or_reduced_without_admission(runtime, action):
    _, _, repo, _, stored, _, live, *_ = runtime
    stored["state"].position_quantity = D(2)
    live.is_active = False
    repo.acquire_entry_admission.return_value = False
    orders, risk, executor, gate = (AsyncMock() for _ in range(4))
    await CodeLiveExecutionService(repo, orders, risk, executor, entry_gate=gate).on_intent(
        live.id, action, estimated_entry=D(100)
    )
    risk.request_signal.assert_awaited_once_with(live.id, stored["state"].generation, action)
    risk.mark_price.assert_awaited_once()
    repo.acquire_entry_admission.assert_not_awaited()
    gate.assert_not_awaited()
    orders.save.assert_not_awaited()
    assert executor.drain.await_count == 2
