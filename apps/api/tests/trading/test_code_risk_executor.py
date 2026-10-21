"""실제 거래소 없이 전달 중단·응답 유실·복구·보호 실패를 검증한다."""

import hashlib
from decimal import Decimal as D
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.code_execution_snapshot import (
    CodeSnapshotError,
    build_code_snapshot,
    validate_code_snapshot,
)
from src.trading.models import (
    CodeRiskCommand,
    ExchangeMode,
    ExchangeName,
    LiveRiskState,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.services.code_risk_executor import CodeRiskExecutor
from src.trading.services.code_risk_service import CodeRiskService


@pytest.fixture
def runtime():
    session = LiveSignalSession(
        user_id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval="1h",
    )
    version = SimpleNamespace(
        id=uuid4(),
        source_code="def on_bar(ctx, state): return {'action':'hold'}",
        language="python",
        execution_policy="code_v1",
        params={},
        warmup_bars=2,
    )
    version.source_hash = hashlib.sha256(version.source_code.encode()).hexdigest()
    account = SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo, read_only=False)
    session.strategy_version_id = version.id
    session.execution_snapshot = build_code_snapshot(
        version=version,
        account=account,
        settings={
            "schema_version": 1,
            "leverage": 1,
            "margin_mode": "cross",
            "position_size_pct": 100,
        },
    )
    entry = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(2),
        state=OrderState.pending,
    )
    state = LiveRiskState(
        session_id=session.id,
        direction="long",
        entry_order_id=entry.id,
        expected_quantity=D(2),
        reference_bars=[{"low": "98", "high": "102"}, {"low": "99", "high": "101"}],
        qty_step=D("0.1"),
        min_qty=D("0.1"),
        provisional_stop=D("97.8"),
    )
    stored = {"state": state}
    outbox: dict[str, CodeRiskCommand] = {}
    repo = AsyncMock(spec=CodeRiskRepository)
    repo.get.side_effect = lambda _: LiveRiskState(**stored["state"].model_dump())
    repo.get_session.return_value = session
    repo.get_version.return_value = version
    repo.get_account.return_value = account

    def cas(current, revision):
        if revision != stored["state"].revision:
            return False
        stored["state"] = LiveRiskState(**{**current.model_dump(), "revision": revision + 1})
        return True

    repo.compare_and_swap.side_effect = cas

    async def enqueue(commands):
        for command in commands:
            outbox.setdefault(command.key, CodeRiskCommand(**command.model_dump()))

    async def claim(_, token):
        for command in outbox.values():
            if command.status == "pending":
                command.status = "running"
                command.lease_token = token
                command.attempts += 1
                return CodeRiskCommand(**command.model_dump())
        return None

    async def finish(key, token, *, status, result=None, error=None):
        command = outbox[key]
        if command.status != "running" or command.lease_token != token:
            return False
        command.status = status
        command.result = result
        command.error = error
        return True

    repo.enqueue_commands.side_effect = enqueue
    repo.claim_command.side_effect = claim
    repo.finish_command.side_effect = finish
    risk = CodeRiskService(repo)
    venue = AsyncMock()
    venue.execute.return_value = {"accepted": True}
    executor = CodeRiskExecutor(repo, risk, venue)
    return executor, risk, repo, venue, stored, outbox, session, version, account


@pytest.mark.asyncio
async def test_committed_outbox_is_recovered_once_after_restart(runtime):
    executor, risk, repo, venue, _, outbox, session, *_ = runtime
    await executor.drain(session.id)
    assert [c.kind for c in outbox.values()] == ["submit_entry"]
    assert next(iter(outbox.values())).status == "applied"
    venue.execute.assert_awaited_once()
    # 같은 desired 상태를 읽는 다른 실행기도 적용된 UUID를 재전송하지 않는다.
    await CodeRiskExecutor(repo, risk, venue).drain(session.id)
    venue.execute.assert_awaited_once()
    assert repo.commit.await_count >= 3


@pytest.mark.asyncio
async def test_tampered_source_stops_new_entry_without_venue_submit(runtime):
    executor, _, _, venue, stored, _, session, version, _ = runtime
    version.source_code += "# tampered"
    await executor.drain(session.id)
    venue.execute.assert_not_awaited()
    assert stored["state"].new_entries_blocked and stored["state"].close_requested
    assert stored["state"].failure_reason == "command_failed:CodeSnapshotError"


@pytest.mark.asyncio
async def test_protection_failure_durably_halts_and_delivers_flatten(runtime):
    executor, risk, _, venue, stored, outbox, session, *_ = runtime
    await risk.record_entry_fill(
        session.id,
        1,
        stored["state"].entry_order_id,
        cumulative_quantity=D(2),
        cumulative_value=D(200),
        terminal=True,
    )

    async def execute(command, *_):
        if command.kind == "apply_protection":
            raise TimeoutError("sensitive provider error must not be stored")
        return {"accepted": True}

    venue.execute.side_effect = execute
    await executor.drain(session.id)
    assert stored["state"].new_entries_blocked
    assert stored["state"].failure_reason == "protection_ack_failed"
    assert any(c.kind == "flatten" and c.status == "applied" for c in outbox.values())
    failed = next(c for c in outbox.values() if c.kind == "apply_protection")
    assert failed.status == "failed" and failed.error == "TimeoutError"


@pytest.mark.asyncio
async def test_stale_protection_command_is_superseded(runtime):
    executor, risk, _repo, venue, stored, outbox, session, *_ = runtime
    await risk.record_entry_fill(
        session.id,
        1,
        stored["state"].entry_order_id,
        cumulative_quantity=D(1),
        cumulative_value=D(100),
        terminal=False,
    )
    await risk.record_entry_fill(
        session.id,
        1,
        stored["state"].entry_order_id,
        cumulative_quantity=D(2),
        cumulative_value=D(200),
        terminal=True,
    )
    await executor.drain(session.id)
    protection = [c for c in outbox.values() if c.kind == "apply_protection"]
    assert [c.status for c in protection] == ["superseded", "applied"]
    assert venue.execute.await_count == 1
    assert stored["state"].protection_applied == stored["state"].protection_desired


@pytest.mark.asyncio
async def test_emergency_flatten_survives_invalid_snapshot_and_inactive_session(runtime):
    executor, risk, _, venue, stored, _, session, *_ = runtime
    await risk.record_entry_fill(
        session.id,
        1,
        stored["state"].entry_order_id,
        cumulative_quantity=D(2),
        cumulative_value=D(200),
        terminal=True,
    )
    await risk.request_signal(session.id, 1, "close")
    session.execution_snapshot = {}
    session.is_active = False
    await executor.drain(session.id)
    assert [call.args[0].kind for call in venue.execute.await_args_list] == ["flatten"]


def test_snapshot_is_pinned_to_actual_source_version_and_finite_params(runtime):
    *_, session, version, account = runtime
    snapshot = session.execution_snapshot
    assert snapshot is not None
    assert (
        validate_code_snapshot(snapshot, version=version, version_id=version.id, account=account)
        == snapshot
    )
    for changed in (
        {"version_id": str(uuid4())},
        {"language": "typescript"},
        {"params": {"x": 1}},
        {"warmup_bars": True},
        {"market_type": "spot"},
        {"source_hash": "0" * 64},
    ):
        with pytest.raises(CodeSnapshotError):
            validate_code_snapshot(
                {**snapshot, **changed}, version=version, version_id=version.id, account=account
            )
    account.read_only = None
    with pytest.raises(CodeSnapshotError):
        validate_code_snapshot(snapshot, version=version, version_id=version.id, account=account)


@pytest.mark.asyncio
async def test_new_generation_requires_fresh_matching_reversal_intent(runtime):
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.code_live_execution_service import CodeLiveExecutionService

    _executor, _risk, repo, _venue, stored, _outbox, session, *_ = runtime
    state = stored["state"]
    state.entry_terminal = True
    state.cancels_confirmed = True
    state.pending_reversal = "short"
    risk, executor, orders, gate = (
        AsyncMock(),
        AsyncMock(),
        AsyncMock(spec=OrderRepository),
        AsyncMock(),
    )
    service = CodeLiveExecutionService(repo, orders, risk, executor, entry_gate=gate)
    repo.get_order.return_value = None
    args = {
        "intent_key": "2026-10-22T00:00:00Z",
        "estimated_entry": D(100),
        "quantity": D(2),
        "previous_bars": [{"low": D(98), "high": D(102)}, {"low": D(99), "high": D(101)}],
        "qty_step": D("0.1"),
        "min_qty": D("0.1"),
    }
    await service.on_intent(session.id, "hold")
    await service.on_intent(session.id, "long", **args)
    orders.save.assert_not_awaited()
    await service.on_intent(session.id, "short", **args)
    gate.assert_awaited_once_with(session.strategy_id, session.exchange_account_id)
    orders.save.assert_awaited_once()
    assert orders.save.await_args.args[0].side == OrderSide.sell
    assert risk.prepare_entry.await_args.kwargs["previous_bars"] == args["previous_bars"]


@pytest.mark.asyncio
async def test_register_builds_server_snapshot_and_rejects_unpinned_source_before_balance(
    runtime, monkeypatch
):
    from src.trading.exceptions import InvalidStrategySettings
    from src.trading.schemas import RegisterLiveSessionRequest
    from src.trading.services.live_session_service import LiveSignalSessionService

    *_, session, version, account = runtime
    account.id = session.exchange_account_id
    account.user_id = session.user_id
    repo, account_repo, strategy_repo, balance, exclusivity = (AsyncMock() for _ in range(5))
    repo.count_active_by_user.return_value = 0
    repo.save.side_effect = lambda value: value
    account_repo.get_by_id.return_value = account
    settings = {
        "schema_version": 1,
        "leverage": 1,
        "margin_mode": "cross",
        "position_size_pct": 100,
    }
    strategy_repo.find_by_id_and_owner.return_value = SimpleNamespace(
        id=session.strategy_id, settings=settings, execution_policy="code_v1"
    )
    strategy_repo.get_version_by_id.return_value = version
    balance.get_balance.return_value = SimpleNamespace(supported=True, total=D(1000))
    service = LiveSignalSessionService(
        repo,
        account_repo,
        strategy_repo,
        balance_service=balance,
        exclusivity_service=exclusivity,
        risk_service=AsyncMock(),
        risk_executor=AsyncMock(),
    )
    monkeypatch.setattr(
        "src.tasks.websocket_task.run_bybit_public_ticker_stream.delay", lambda: None
    )
    req = RegisterLiveSessionRequest(
        strategy_id=session.strategy_id,
        exchange_account_id=account.id,
        symbol=session.symbol,
        interval="1h",
        source_policy="code_v1",
        strategy_version_id=version.id,
        execution_snapshot={**session.execution_snapshot, "execution_settings": {"leverage": 999}},
    )
    result = await service.register(session.user_id, req)
    assert result.execution_snapshot["execution_settings"]["leverage"] == 1
    assert result.strategy_version_id == version.id
    repo.commit.assert_awaited_once()
    balance.get_balance.reset_mock()
    version.source_code += "# changed"
    with pytest.raises(InvalidStrategySettings):
        await service.register(session.user_id, req)
    balance.get_balance.assert_not_awaited()
