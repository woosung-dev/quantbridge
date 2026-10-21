"""거래소 호출 없이 누적 체결·보호 ACK·반전·재시작의 안전 경계를 검증한다."""

from decimal import Decimal as D
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.models import LiveRiskState, Order, OrderSide, OrderState, OrderType
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.services.code_risk_service import CodeRiskError, CodeRiskService

BARS = [{"low": D("98"), "high": D("102")}, {"low": D("99"), "high": D("101")}]


@pytest.fixture
def controller():
    stored: dict[str, LiveRiskState] = {}
    repo = AsyncMock(spec=CodeRiskRepository)
    session_id, entry_id = uuid4(), uuid4()
    order = Order(
        id=entry_id,
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D("2"),
        state=OrderState.pending,
    )

    def get(_):
        return stored["state"].model_copy(deep=True) if "state" in stored else None

    def create(state):
        stored["state"] = state.model_copy(deep=True)
        return True

    def cas(state, expected_revision):
        if expected_revision != stored["state"].revision:
            return False
        stored["state"] = state.model_copy(deep=True, update={"revision": expected_revision + 1})
        return True

    repo.get.side_effect = get
    repo.create_if_absent.side_effect = create
    repo.compare_and_swap.side_effect = cas
    repo.get_entry_order.return_value = order
    repo.attach_entry.return_value = True
    return CodeRiskService(repo), repo, stored, session_id, entry_id


async def prepare(controller):
    svc, repo, _stored, session_id, entry_id = controller
    commands = await svc.prepare_entry(
        session_id,
        entry_id,
        direction="long",
        estimated_entry=D("100"),
        quantity=D("2"),
        previous_bars=BARS,
        qty_step=D("0.1"),
        min_qty=D("0.1"),
    )
    repo.commit.assert_awaited_once()
    repo.commit.reset_mock()
    assert commands[0].kind == "submit_entry" and commands[0].payload["stop_loss"] == "97.80"
    return commands


async def fill(controller, *, qty="2", value="204", terminal=True):
    svc, _repo, _stored, session_id, entry_id = controller
    return await svc.record_entry_fill(
        session_id,
        1,
        entry_id,
        cumulative_quantity=D(qty),
        cumulative_value=D(value),
        terminal=terminal,
    )


@pytest.mark.asyncio
async def test_partial_fill_is_protected_before_terminal_and_terminal_vwap_freezes_r(controller):
    svc, repo, stored, session_id, _ = controller
    await prepare(controller)
    commands = await fill(controller, qty="1", value="100", terminal=False)
    repo.commit.assert_awaited_once()
    repo.commit.reset_mock()
    assert stored["state"].fixed_r is None
    assert commands[0].kind == "apply_protection"
    assert commands[0].payload["quantity"] == "1"
    old_token = commands[0].payload["token"]
    assert await fill(controller, qty="0.5", value="50", terminal=False) == []
    assert await fill(controller, qty="1", value="100", terminal=False) == []
    repo.commit.assert_not_awaited()
    commands = await fill(controller)
    state = stored["state"]
    assert state.entry_vwap == D("102") and state.fixed_r == D("4.4")
    assert D(str(commands[0].payload["stop_loss"])) == D("97.60")
    assert D(str(commands[0].payload["tp_price"])) == D("108.600")
    assert D(str(commands[0].payload["trailing_activation"])) == D("110.80")
    assert D(str(commands[0].payload["trailing_distance"])) == D("8.80")
    repo.commit.assert_awaited_once()
    repo.commit.reset_mock()
    assert await svc.acknowledge_protection(session_id, 1, token=str(old_token), success=True) == []
    assert await fill(controller) == []
    assert stored["state"].protection_applied == {}
    assert await svc.request_signal(session_id, 1, "long") == []
    repo.commit.assert_not_awaited()
    assert stored["state"].fixed_r == D("4.4")


@pytest.mark.asyncio
async def test_ack_failure_halts_new_entries_and_restarts_recover_same_flatten_command(controller):
    svc, repo, stored, session_id, _entry_id = controller
    await prepare(controller)
    await fill(controller)
    repo.commit.reset_mock()
    token = str(stored["state"].protection_desired["token"])
    commands = await svc.acknowledge_protection(session_id, 1, token=token, success=False)
    repo.commit.assert_awaited_once()
    assert [command.kind for command in commands] == ["halt_new_entries", "flatten"]
    assert commands[1].payload["reduce_only"] is True
    assert await CodeRiskService(repo).recover(session_id) == commands
    with pytest.raises(CodeRiskError, match="새 진입"):
        await svc.prepare_entry(
            session_id,
            uuid4(),
            direction="short",
            estimated_entry=D("100"),
            quantity=D("2"),
            previous_bars=BARS,
            qty_step=D("0.1"),
            min_qty=D("0.1"),
        )


@pytest.mark.asyncio
async def test_partial_tp_dedup_trailing_and_late_ack_preserve_fixed_r(controller):
    svc, repo, stored, session_id, _ = controller
    await prepare(controller)
    await fill(controller)
    exit_id = uuid4()
    repo.commit.reset_mock()
    await svc.record_exit_fill(
        session_id, 1, exit_id, role="partial_tp", cumulative_quantity=D("0.5")
    )
    repo.commit.assert_awaited_once()
    repo.commit.reset_mock()
    assert (
        await svc.record_exit_fill(
            session_id, 1, exit_id, role="partial_tp", cumulative_quantity=D("0.5")
        )
        == []
    )
    repo.commit.assert_not_awaited()
    await svc.record_exit_fill(
        session_id, 1, exit_id, role="partial_tp", cumulative_quantity=D("1")
    )
    assert stored["state"].position_quantity == D("1")
    assert stored["state"].tp_filled_quantity == D("1")
    assert stored["state"].protection_desired["tp_quantity"] == "0"
    repo.commit.reset_mock()
    await svc.mark_price(session_id, 1, D("110.8"))
    repo.commit.assert_awaited_once()
    assert D(str(stored["state"].protection_desired["stop_loss"])) == D("102")
    await svc.mark_price(session_id, 1, D("114"))
    assert D(str(stored["state"].protection_desired["stop_loss"])) == D("105.20")
    assert stored["state"].fixed_r == D("4.4")
    assert await svc.mark_price(session_id, 1, D("112")) == []


@pytest.mark.asyncio
async def test_reversal_requires_terminal_entry_flat_and_confirmed_cancellation(controller):
    svc, repo, stored, session_id, _ = controller
    await prepare(controller)
    await fill(controller)
    repo.commit.reset_mock()
    commands = await svc.request_signal(session_id, 1, "short")
    repo.commit.assert_awaited_once()
    assert [command.kind for command in commands] == ["flatten"]
    commands = await svc.record_exit_fill(
        session_id, 1, uuid4(), role="close", cumulative_quantity=D("2")
    )
    assert [command.kind for command in commands] == ["cancel_children"]
    commands = await svc.confirm_flat_and_cancelled(session_id, 1, flat=False, cancelled=True)
    assert [command.kind for command in commands] == ["cancel_children"]
    commands = await svc.confirm_flat_and_cancelled(session_id, 1, flat=True, cancelled=True)
    assert [command.kind for command in commands] == ["ready_reversal"]
    assert commands[0].payload == {"direction": "short"}
    repo.get_entry_order.return_value = repo.get_entry_order.return_value.model_copy(
        update={"id": uuid4(), "side": OrderSide.sell}
    )
    new_id = repo.get_entry_order.return_value.id
    await svc.prepare_entry(
        session_id,
        new_id,
        direction="short",
        estimated_entry=D("100"),
        quantity=D("2"),
        previous_bars=BARS,
        qty_step=D("0.1"),
        min_qty=D("0.1"),
    )
    assert stored["state"].generation == 2 and stored["state"].fixed_r is None
    assert (
        await svc.record_exit_fill(session_id, 1, uuid4(), role="close", cumulative_quantity=D("2"))
        == []
    )


@pytest.mark.asyncio
async def test_invalid_terminal_swing_or_unsplittable_partial_fails_closed(controller):
    _svc, _repo, stored, _session_id, _ = controller
    await prepare(controller)
    commands = await fill(controller, value="194")
    assert [command.kind for command in commands] == ["halt_new_entries", "flatten"]
    assert stored["state"].fixed_r is None
    assert stored["state"].position_quantity == D("2")


@pytest.mark.asyncio
async def test_successful_ack_commits_and_cas_conflict_never_returns_commands(controller):
    svc, repo, stored, session_id, _ = controller
    await prepare(controller)
    await fill(controller)
    token = str(stored["state"].protection_desired["token"])
    repo.commit.reset_mock()
    assert await svc.acknowledge_protection(session_id, 1, token=token, success=True) == []
    repo.commit.assert_awaited_once()
    assert stored["state"].protection_applied == stored["state"].protection_desired
    repo.commit.reset_mock()
    repo.compare_and_swap.side_effect = None
    repo.compare_and_swap.return_value = False
    with pytest.raises(CodeRiskError, match="CAS"):
        await svc.request_signal(session_id, 1, "close")
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_entry_attach_race_rolls_back_instead_of_committing_unprotected_order(controller):
    _svc, repo, *_ = controller
    repo.attach_entry.return_value = False
    with pytest.raises(CodeRiskError, match="임시 SL"):
        await prepare(controller)
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_partial_that_cannot_split_halts_and_flattens(controller):
    _svc, _repo, stored, _session_id, _entry_id = controller
    await prepare(controller)
    stored["state"].qty_step = D("1")
    stored["state"].min_qty = D("1")
    commands = await fill(controller, qty="1", value="100")
    assert [command.kind for command in commands] == ["halt_new_entries", "flatten"]
    assert stored["state"].failure_reason == "terminal_partial_fill_cannot_split"


@pytest.mark.asyncio
async def test_late_entry_fill_after_terminal_is_recorded_but_never_changes_fixed_r(controller):
    _svc, _repo, stored, _session_id, _entry_id = controller
    await prepare(controller)
    await fill(controller, qty="1", value="100")
    fixed_r = stored["state"].fixed_r
    commands = await fill(controller, qty="2", value="204")
    assert stored["state"].cumulative_quantity == D("2")
    assert stored["state"].position_quantity == D("2")
    assert stored["state"].fixed_r == fixed_r
    assert [command.kind for command in commands] == ["halt_new_entries", "flatten"]


@pytest.mark.asyncio
async def test_exit_overfill_fails_closed_without_restoring_position(controller):
    svc, _repo, stored, session_id, _ = controller
    await prepare(controller)
    await fill(controller)
    commands = await svc.record_exit_fill(
        session_id, 1, uuid4(), role="partial_tp", cumulative_quantity=D("1.1")
    )
    assert stored["state"].position_quantity == D("0.9")
    assert [command.kind for command in commands] == ["halt_new_entries", "flatten"]


@pytest.mark.asyncio
async def test_short_risk_trails_in_favorable_direction_only(controller):
    svc, repo, stored, session_id, entry_id = controller
    repo.get_entry_order.return_value = repo.get_entry_order.return_value.model_copy(
        update={"side": OrderSide.sell}
    )
    await svc.prepare_entry(
        session_id,
        entry_id,
        direction="short",
        estimated_entry=D("100"),
        quantity=D("2"),
        previous_bars=BARS,
        qty_step=D("0.1"),
        min_qty=D("0.1"),
    )
    await fill(controller, value="200")
    assert stored["state"].fixed_r == D("2.2")
    await svc.mark_price(session_id, 1, D("95.6"))
    assert D(str(stored["state"].protection_desired["stop_loss"])) == D("100")
    await svc.mark_price(session_id, 1, D("92"))
    assert D(str(stored["state"].protection_desired["stop_loss"])) == D("96.4")
    assert await svc.mark_price(session_id, 1, D("94")) == []


@pytest.mark.asyncio
async def test_late_tp_after_observed_flat_only_settles_once_and_preserves_reversal(controller):
    svc, _repo, stored, session_id, _ = controller
    await prepare(controller)
    await fill(controller, qty="2", value="200")
    await svc.request_signal(session_id, 1, "short")
    await svc.confirm_flat_and_cancelled(session_id, 1, flat=True, cancelled=True)
    identifier = uuid4()
    await svc.record_exit_fill(
        session_id, 1, identifier, role="partial_tp", cumulative_quantity=D(1)
    )
    state = stored["state"]
    assert state.position_quantity == 0 and state.tp_filled_quantity == 1
    assert (
        state.pending_reversal == "short"
        and state.cancels_confirmed
        and not state.new_entries_blocked
    )
    assert (
        await svc.record_exit_fill(
            session_id, 1, identifier, role="partial_tp", cumulative_quantity=D(1)
        )
        == []
    )
    # 실제 누적 청산 총량이 진입 총량을 넘는 모순은 여전히 차단한다.
    await svc.record_exit_fill(session_id, 1, uuid4(), role="close", cumulative_quantity=D(2))
    assert stored["state"].new_entries_blocked
