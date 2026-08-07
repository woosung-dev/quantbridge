# 라이브 평가 공백 재동기화와 orphan close 백스톱을 검증한다.
"""평가 catch-up과 close 포지션 가드의 Celery 경계 동작을 검증한다."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest

import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]

from src.strategy.pine_v2.event_loop import LiveSignal, LiveSignalResult  # noqa: E402
from src.trading.models import (  # noqa: E402
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    LiveSignalInterval,
    OrderSide,
)
from src.trading.repositories.order_repository import LedgerFill  # noqa: E402


class _SessionContext:
    """테스트용 worker AsyncSession context다."""

    def __init__(self, session: AsyncMock) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncMock:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    engine = AsyncMock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(
        live_signal_module,
        "create_worker_engine_and_sm",
        lambda: (engine, lambda: _SessionContext(session)),
    )


def _session(*, last_evaluated_bar_time: datetime | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=True,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        # BL-544 — SessionScope.from_live_session 이 읽는다. 없으면 원장 조회가 조용히
        # AttributeError 로 죽어 "seed 없음" 이 되고, 그러면 seed 테스트가 무엇도 안 잰다.
        deactivated_at=None,
        last_evaluated_bar_time=last_evaluated_bar_time,
        equity_baseline_usdt=Decimal("8192"),
    )


def _position(*, side: str, size: str) -> SimpleNamespace:
    """`fetch_open_positions` 가 실제로 주는 leg 형태 (`ExchangePositionSchema` 부분집합).

    ★예전 픽스처는 `object()` 였다. `_net_position_size` 가 `.side` 를 못 읽어 예외가 났고,
    "거래소에 포지션이 있다" 를 표현하지 못했다 — 픽스처는 그 산출물이 실제로 주는 형태여야 한다.
    """
    return SimpleNamespace(side=side, size=Decimal(size))


def _open_trade(*, trade_id: str, direction: str, qty: float, entry_bar: int) -> dict[str, object]:
    """`Trade.to_dict()` 가 실제로 주는 키 부분집합. ★`qty` 를 빠뜨리면 판정이 못 읽는다."""
    return {"id": trade_id, "direction": direction, "qty": qty, "entry_bar": entry_bar}


def _fill(
    *,
    session_id: object,
    side: OrderSide,
    quantity: str,
    price: str,
    filled_at: datetime,
    trade_id: str = "L",
    reduce_only: bool = False,
    idempotency_key: str | None = None,
) -> LedgerFill:
    """공백 창에서 관측된 체결 1건. key 는 실제 조건부 진입 형식을 쓴다."""
    return LedgerFill(
        order_id=uuid4(),
        idempotency_key=(
            idempotency_key
            if idempotency_key is not None
            else f"live:{session_id}:cond:1785337500:64166.7:{quantity}:{trade_id}"
        ),
        side=side,
        filled_quantity=Decimal(quantity),
        filled_price=Decimal(price),
        filled_at=filled_at,
        reduce_only=reduce_only,
    )


def _resting_entry(
    session_id: object,
    *,
    submitted_at: datetime | None,
    created_at: datetime | None = None,
    trade_id: str = "S",
) -> SimpleNamespace:
    """`list_resting_conditional_entries` 가 주는 미확정 조건부 진입 1건.

    ★`idempotency_key` 는 실제 형식이어야 한다 — 판별자가 `parse_conditional_entry_key` 로
    **세션을 좁히므로**, 형식이 틀리면 그 주문은 "다른 세션의 것" 으로 조용히 버려진다.
    """
    return SimpleNamespace(
        idempotency_key=f"live:{session_id}:cond:1785337500:64472.4:0.058:{trade_id}",
        submitted_at=submitted_at,
        created_at=created_at if created_at is not None else submitted_at,
    )


def _strategy(strategy_id: object, *, fill_timing: str | None = None) -> SimpleNamespace:
    settings: dict[str, object] = {
        "leverage": 2,
        "margin_mode": "cross",
        "position_size_pct": 10.0,
    }
    if fill_timing is not None:
        settings["fill_timing"] = fill_timing
    return SimpleNamespace(
        id=strategy_id,
        settings=settings,
        pine_source="//@version=5\nstrategy('gap')",
        trading_sessions=[],
    )


def _result(
    *,
    last_bar_time: datetime,
    signals: list[LiveSignal],
    open_trades: list[object] | None = None,
    ledger_seed_applied: tuple[str, ...] = (),
) -> LiveSignalResult:
    return LiveSignalResult(
        last_bar_time=last_bar_time,
        signals=signals,
        strategy_state_report={"open_trades": open_trades or []},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
        ledger_seed_applied=ledger_seed_applied,
    )


def _event(signal: LiveSignal, session_id: object) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        session_id=session_id,
        bar_time=signal.bar_time,
        sequence_no=signal.sequence_no,
        action=signal.action,
        trade_id=signal.trade_id,
        status=LiveSignalEventStatus.pending,
        realized_pnl=signal.realized_pnl,
    )


def _install_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sess: SimpleNamespace,
    rows: list[list[object]],
    run_result: LiveSignalResult,
    inserted_events: list[SimpleNamespace],
    fill_timing: str | None = None,
    previous_state: object | None = None,
    ledger_fills: list[LedgerFill] | None = None,
    resting_entries: list[object] | None = None,
) -> tuple[AsyncMock, AsyncMock, list[dict[str, Any]]]:
    """평가 경로를 메모리 의존성으로 고정하고 run_live kwargs를 수집한다."""
    _patch_engine(monkeypatch)
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.get_state = AsyncMock(return_value=previous_state)
    sess_repo.upsert_state = AsyncMock()
    sess_repo.commit = AsyncMock()
    event_repo = AsyncMock()
    event_repo.sum_realized_pnl_before = AsyncMock(return_value=(Decimal("0"), 0))
    event_repo.sum_realized_pnl_all = AsyncMock(return_value=(Decimal("0"), 0))
    event_repo.list_by_session = AsyncMock(return_value=[])
    event_repo.insert_pending_events = AsyncMock(return_value=inserted_events)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_strategy(sess.strategy_id, fill_timing=fill_timing)
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )
    # BL-544 — 공백 재개 경로가 이 원장을 읽는다. 기본값은 "공백 창에 체결 없음" 이라
    # 이 조회를 쓰지 않는 기존 테스트의 의미가 바뀌지 않는다.
    order_repo = AsyncMock()
    order_repo.list_fills_since = AsyncMock(return_value=list(ledger_fills or []))
    # BL-622 — 공백 재동기 **유예** 판별자가 이 조회를 읽는다. 기본값 `[]` 는 "이 세션에
    # 미확정 조건부 진입 없음" 이라 유예가 안 걸리고, 이 인자를 안 쓰는 기존 테스트의
    # 의미가 그대로 유지된다(전부 종전대로 즉시 판정한다).
    order_repo.list_resting_conditional_entries = AsyncMock(
        return_value=list(resting_entries or [])
    )

    import src.strategy.pine_v2.event_loop as event_loop_module
    import src.strategy.repository as strategy_repo_module
    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.live_signal_event_repository as event_repo_module
    import src.trading.repositories.live_signal_session_repository as sess_repo_module
    import src.trading.repositories.order_repository as order_repo_module

    monkeypatch.setattr(order_repo_module, "OrderRepository", MagicMock(return_value=order_repo))
    monkeypatch.setattr(
        sess_repo_module, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
    )
    monkeypatch.setattr(
        event_repo_module, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
    )
    monkeypatch.setattr(
        account_repo_module, "ExchangeAccountRepository", MagicMock(return_value=account_repo)
    )
    monkeypatch.setattr(
        strategy_repo_module, "StrategyRepository", MagicMock(return_value=strategy_repo)
    )
    provider = SimpleNamespace(fetch_ohlcv=AsyncMock(return_value=rows))
    monkeypatch.setattr(celery_module, "get_ccxt_provider_for_worker", lambda: provider)
    captured_kwargs: list[dict[str, Any]] = []

    def fake_run_live(*_args: object, **kwargs: Any) -> LiveSignalResult:
        captured_kwargs.append(kwargs)
        return run_result

    monkeypatch.setattr(event_loop_module, "run_live", fake_run_live)
    monkeypatch.setattr(live_signal_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(live_signal_module, "_reconcile_conditional_entries", AsyncMock())
    monkeypatch.setattr(
        live_signal_module.dispatch_live_signal_event_task, "apply_async", MagicMock()
    )
    monkeypatch.setattr(
        live_signal_module.sweep_conditional_entries_task, "apply_async", MagicMock()
    )
    monkeypatch.setattr(live_signal_module, "send_rule_alert", AsyncMock(return_value={}))
    return sess_repo, event_repo, captured_kwargs


@pytest.mark.asyncio
async def test_strategy_settings_fill_timing_reaches_run_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """전략 설정의 체결 시점이 라이브 인터프리터 호출까지 보존된다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    sess = _session(last_evaluated_bar_time=None)
    _sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0),
        run_result=_result(last_bar_time=t0, signals=[]),
        inserted_events=[],
        fill_timing="next_bar_open",
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["fill_timing"] == "next_bar_open"


def _rows(*times: datetime) -> list[list[object]]:
    return [[int(time.timestamp() * 1000), 1, 2, 0, 1, 100] for time in times]


@pytest.mark.asyncio
async def test_short_gap_catches_up_two_bars_without_duplicate_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1분 결손은 watermark 뒤 두 bar를 한 outbox INSERT로 보낸다."""
    t0 = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    t1, t2 = t0 + timedelta(minutes=1), t0 + timedelta(minutes=2)
    sess = _session(last_evaluated_bar_time=t0)
    signals = [
        LiveSignal("entry", "long", "A", 1.0, 0, bar_time=t1),
        LiveSignal("close", "long", "A", 1.0, 0, bar_time=t2),
    ]
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t1, t2),
        run_result=_result(last_bar_time=t2, signals=signals),
        inserted_events=[_event(signal, sess.id) for signal in signals],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["events_inserted"] == 2
    assert run_kwargs == [
        {
            "initial_capital": 8192.0,
            "live_position_size_pct": 10.0,
            "leverage": 2.0,
            "sessions_allowed": (),
            "pyramiding": None,
            "fill_timing": "bar_close",
            "emit_from_bar_time": t0,
            "position_epoch": t0,
            # ADR-025 — 원장을 **읽었고** 조건부 진입 체결이 없었다. `()` 와 `None`(못 읽었다)
            # 은 다른 상태이고, 여기서 `()` 가 나오는 것이 곧 「원장이 답했다」의 증거다.
            "ledger_conditional_fills": (),
        }
    ]
    payload = event_repo.insert_pending_events.await_args.kwargs["signals"]
    keys = {
        (signal["bar_time"], signal["sequence_no"], signal["action"], signal["trade_id"])
        for signal in payload
    }
    assert len(payload) == len(keys) == 2
    sess_repo.deactivate.assert_not_awaited()


@pytest.mark.asyncio
async def test_long_gap_both_flat_resyncs_without_deactivation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """상한 밖 공백이라도 양쪽 flat이면 마지막 bar만 조용히 이어간다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0)
    sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[_open_trade(trade_id="B", direction="long", qty=1.0, entry_bar=1)],
        ),
        inserted_events=[_event(last_signal, sess.id)],
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert "emit_from_bar_time" not in run_kwargs[0]
    assert run_kwargs[0]["position_epoch"] == t6
    sess_repo.deactivate.assert_not_awaited()
    sess_repo.try_claim_bar.assert_awaited_once_with(sess.id, t6, ANY)


@pytest.mark.asyncio
async def test_long_gap_exchange_flat_realigns_stored_epoch_to_last_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """state 행이 있어도 장기 공백의 실제 flat은 저장 epoch 대신 마지막 bar를 쓴다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    stored_epoch = t0 - timedelta(hours=1)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[_open_trade(trade_id="B", direction="long", qty=1.0, entry_bar=1)],
        ),
        inserted_events=[_event(last_signal, sess.id)],
        previous_state=SimpleNamespace(
            last_strategy_state_report={"_qb_position_epoch": stored_epoch.isoformat()},
            equity_curve=None,
        ),
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["position_epoch"] == t6
    assert run_kwargs[0]["position_epoch"] != stored_epoch
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_gap_keeps_stored_epoch_when_state_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """짧은 공백은 저장된 epoch을 유지해 장기 flat realign과 구분한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=1)
    stored_epoch = t0 - timedelta(hours=1)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0, bar_time=t1)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t1),
        run_result=_result(last_bar_time=t1, signals=[last_signal]),
        inserted_events=[_event(last_signal, sess.id)],
        previous_state=SimpleNamespace(
            last_strategy_state_report={"_qb_position_epoch": stored_epoch.isoformat()},
            equity_curve=None,
        ),
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["position_epoch"] == stored_epoch
    assert run_kwargs[0]["position_epoch"] != t1
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_position_mismatch_without_ledger_basis_deactivates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — 거래소만 보유하고 **원장에 근거가 없으면** 계속 세션을 중단한다.

    BL-544 가 바꾼 것은 "원장이 설명하는 보유분" 뿐이다. 설명 없는 보유분까지 통과시키면
    seed 는 사라지고 판정만 넓힌 것이 되어, 시끄러운 사망이 조용한 고아로 바뀐다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        ledger_fills=[],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await asyncio.sleep(0)

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    assert "ledger_seed_legs" not in run_kwargs[0]
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_long_gap_position_mismatch_explained_by_ledger_survives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★BL-544 재현 — 공백 중 체결된 조건부 진입은 원장으로 seed 되어 세션이 산다.

    실측 원장 그대로다(세션 1178787c, 2026-07-29): buy `filled_quantity=0.029`
    `filled_price=64166.9`, `filled_at` 이 `last_evaluated_bar_time` 이후. 거래소도 같은
    포지션을 들고 있다. 예전에는 이 상태가 `gap_resync_position_mismatch` 로 죽었다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "L", 0.029, 0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            # 엔진 훅이 채택한 결과 — entry_bar 는 마지막 bar 지만 거래소에 이미 있다.
            open_trades=[_open_trade(trade_id="L", direction="long", qty=0.029, entry_bar=1)],
            ledger_seed_applied=("L",),
        ),
        inserted_events=[_event(last_signal, sess.id)],
        ledger_fills=[
            _fill(
                session_id=sess.id,
                side=OrderSide.buy,
                quantity="0.029",
                price="64166.9",
                filled_at=t0 + timedelta(minutes=3),
            )
        ],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()
    legs = run_kwargs[0]["ledger_seed_legs"]
    assert [(leg.trade_id, leg.direction, leg.qty, leg.entry_price) for leg in legs] == [
        ("L", "long", 0.029, 64166.9)
    ]


@pytest.mark.asyncio
async def test_long_gap_ledger_seed_closed_by_strategy_still_survives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """채택한 포지션을 마지막 bar 에서 전략이 닫아도 세션은 살아 그 close 를 발행한다.

    판정이 outbox INSERT 앞에 있어, 이걸 불일치라고 부르면 세션이 죽고 **그 close 가 영원히
    안 나간다** — 채택해 놓고 못 닫는 최악의 결말이다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    close_signal = LiveSignal("close", "long", "L", 0.029, 0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        # 전략이 닫았으므로 open_trades 는 비었다. 거래소에는 아직 그대로 있다.
        run_result=_result(
            last_bar_time=t6,
            signals=[close_signal],
            open_trades=[],
            ledger_seed_applied=("L",),
        ),
        inserted_events=[_event(close_signal, sess.id)],
        ledger_fills=[
            _fill(
                session_id=sess.id,
                side=OrderSide.buy,
                quantity="0.029",
                price="64166.9",
                filled_at=t0 + timedelta(minutes=3),
            )
        ],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fill_kwargs",
    [
        pytest.param({"reduce_only": True}, id="reduce_only"),
        pytest.param({"idempotency_key": "someone-elses-key"}, id="foreign_key"),
    ],
)
async def test_long_gap_inadmissible_ledger_window_still_deactivates(
    monkeypatch: pytest.MonkeyPatch, fill_kwargs: dict[str, Any]
) -> None:
    """자동 재구성 대상이 아닌 창은 채택하지 않고 기존 fail-closed 판정으로 떨어진다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        ledger_fills=[
            _fill(
                session_id=sess.id,
                side=OrderSide.buy,
                quantity="0.029",
                price="64166.9",
                filled_at=t0 + timedelta(minutes=3),
                **fill_kwargs,
            )
        ],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    assert "ledger_seed_legs" not in run_kwargs[0]
    sess_repo.deactivate.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_hedged_exchange_legs_still_deactivate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hedge 양다리는 순포지션이 0 으로 상쇄되므로 순포지션 일치만으로 통과시키지 않는다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, _event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
    )
    _patch_positions(
        monkeypatch,
        positions=[_position(side="long", size="1"), _position(side="short", size="1")],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_position_fetch_failure_deactivates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """거래소 조회 실패는 flat으로 간주하지 않아 장기 공백을 fail-closed 처리한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
    )
    _patch_positions(monkeypatch, positions=Exception("boom"))

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_long_gap_defers_judgement_while_ledger_still_catching_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★BL-622 재현 — 미확정 조건부 진입이 남아 있으면 판정을 **미룬다**.

    실측(세션 c160a1a9, 2026-08-06): 거래소는 조건부 매도를 `20:17:19.519` 에 체결했는데
    우리 원장은 `20:31:51.622` 에야 `filled` 로 기록했고, 판정은 그 **3.5초 전**인
    `20:31:48.126` 에 났다. 그 순간 원장은 아직 `submitted` 라 seed 가 비었고, 엔진은 반전
    전 포지션을 든 채 거래소와 대조돼 **정상인데도** 세션이 죽었다(19.42h 소크 창 폐기).

    셋업은 바로 위 `..._without_ledger_basis_deactivates` 와 **미확정 주문 1건만** 다르다 —
    그 한 건이 사망을 유예로 바꾼다.

    ★★★`try_claim_bar` 를 **부르지 않았다**는 단언이 이 수리의 핵심이다. claim 은 성공 시
    `last_evaluated_bar_time` 을 전진시키므로, claim 뒤에서 미루면 다음 tick 의 공백이 5분
    안으로 줄어 **재동기 판정이 다시는 안 걸린다**(가드가 조용히 영구 OFF).
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        ledger_fills=[],
        # 실측 나이 16분 58초 — janitor 문턱(30분) 안이다.
        resting_entries=[
            _resting_entry(sess.id, submitted_at=datetime.now(UTC) - timedelta(minutes=17))
        ],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"skipped": "gap_resync_pending_ledger"}
    sess_repo.try_claim_bar.assert_not_awaited()
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_long_gap_judgement_resumes_once_ledger_caught_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★BL-622 회복 — 주문이 종결되면 유예가 풀리고 그 tick 이 온전히 판정된다.

    유예는 **끈적하지 않다**: 미확정 목록이 비는 순간 종전 경로가 그대로 돌아온다. 여기서는
    원장이 따라잡아 seed 가 서므로 세션이 살고 이벤트도 나간다 — 유예가 그 창의 이벤트를
    먹지 않는다는 뜻이다(claim 전에 미뤘으므로 봉이 소비되지 않았다).
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "L", 0.029, 0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[_open_trade(trade_id="L", direction="long", qty=0.029, entry_bar=1)],
            ledger_seed_applied=("L",),
        ),
        inserted_events=[_event(last_signal, sess.id)],
        ledger_fills=[
            _fill(
                session_id=sess.id,
                side=OrderSide.buy,
                quantity="0.029",
                price="64166.9",
                filled_at=t0 + timedelta(minutes=3),
            )
        ],
        # 주문이 `filled` 로 종결돼 더 이상 미확정이 아니다.
        resting_entries=[],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    sess_repo.try_claim_bar.assert_awaited_once()
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_other_session_resting_entry_does_not_defer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — **다른 세션**의 미확정 주문은 이 세션의 판정을 미루지 못한다.

    `list_resting_conditional_entries` 는 (strategy, account) 단위라 형제 세션의 주문도
    함께 온다. 그것까지 유예 근거로 삼으면 남의 주문 하나로 이 세션의 fail-closed 가 꺼진다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        ledger_fills=[],
        resting_entries=[
            _resting_entry(uuid4(), submitted_at=datetime.now(UTC) - timedelta(minutes=17))
        ],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_long_gap_stops_deferring_once_the_defer_budget_is_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조(상한) — 유예를 `_MAX_GAP_RESYNC_DEFERS` 만큼 썼으면 더 안 미루고 판정한다.

    ★**상한을 「주문 나이」로 재지 않는 이유가 이 테스트의 존재 이유다.** 조건부 진입은
    트리거를 기다리며 **정상적으로** 오래 쉰다(실측: 사망 세션 118건 · 평균 resting 563초 ·
    벽시계의 **95.1%** 를 덮는다). 나이로 끊으면 「거의 항상 미룰 수 있음」이 되어 진짜
    발산까지 30분 미뤄진다. 재는 것은 주문의 나이가 아니라 **우리가 몇 번 미뤘는가**다.

    여기서는 직전 리포트가 이미 상한만큼의 유예를 들고 있으므로, 미확정 주문이 **그대로
    있어도** 종전 경로로 떨어져 fail-closed 가 집행된다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        ledger_fills=[],
        # 미확정 주문은 아직 있다 — 끊는 것은 주문이 아니라 예산이다.
        resting_entries=[
            _resting_entry(sess.id, submitted_at=datetime.now(UTC) - timedelta(minutes=1))
        ],
        previous_state=SimpleNamespace(
            last_strategy_state_report={
                live_signal_module._GAP_RESYNC_DEFER_KEY: (
                    live_signal_module._MAX_GAP_RESYNC_DEFERS
                )
            },
            equity_curve=None,
        ),
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.try_claim_bar.assert_awaited_once()
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_deferring_carries_the_previous_report_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★유예는 카운터를 올리되 **직전 리포트를 통째로 이어받는다.**

    `upsert_state` 는 리포트를 교체하므로, 새 dict 로 덮으면 `_qb_position_epoch` 같은
    가드 상태가 이 tick 에 조용히 사라진다 — 그러면 다음 tick 의 epoch 판정이 달라진다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    stored_epoch = datetime(2026, 4, 30, tzinfo=UTC)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        ledger_fills=[],
        resting_entries=[
            _resting_entry(sess.id, submitted_at=datetime.now(UTC) - timedelta(minutes=1))
        ],
        previous_state=SimpleNamespace(
            last_strategy_state_report={
                "_qb_position_epoch": stored_epoch.isoformat(),
                live_signal_module._GAP_RESYNC_DEFER_KEY: 1,
            },
            equity_curve=None,
        ),
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.029")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"skipped": "gap_resync_pending_ledger"}
    sess_repo.upsert_state.assert_awaited_once()
    written = sess_repo.upsert_state.await_args.kwargs["last_strategy_state_report"]
    # 카운터는 1 → 2 로 오르고, 직전 epoch 은 살아남는다.
    assert written[live_signal_module._GAP_RESYNC_DEFER_KEY] == 2
    assert written["_qb_position_epoch"] == stored_epoch.isoformat()


@pytest.mark.asyncio
async def test_new_session_never_catches_up_warmup_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """신규 세션은 300 bar warmup에 신호가 있어도 마지막 bar만 발행한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    sess = _session(last_evaluated_bar_time=None)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0)
    _sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t0 + timedelta(minutes=1)),
        run_result=_result(last_bar_time=t0 + timedelta(minutes=1), signals=[last_signal]),
        inserted_events=[_event(last_signal, sess.id)],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["events_inserted"] == 1
    assert "emit_from_bar_time" not in run_kwargs[0]


def _patch_positions(
    monkeypatch: pytest.MonkeyPatch, *, positions: list[object] | Exception
) -> None:
    """장기 resync와 dispatch close 가드가 공유하는 거래소 포지션 조회를 대체한다."""
    provider = SimpleNamespace(fetch_open_positions=AsyncMock())
    if isinstance(positions, Exception):
        provider.fetch_open_positions.side_effect = positions
    else:
        provider.fetch_open_positions.return_value = positions

    import src.trading.providers as providers_module
    import src.trading.services.account_service as account_service_module

    monkeypatch.setattr(providers_module, "BybitFuturesProvider", lambda: provider)
    monkeypatch.setattr(
        account_service_module.ExchangeAccountService,
        "get_credentials_for_order",
        AsyncMock(return_value=object()),
    )


def _dispatch_event(*, action: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        session_id=uuid4(),
        bar_time=datetime(2026, 5, 1, 12, tzinfo=UTC),
        sequence_no=0,
        action=action,
        direction="long",
        trade_id="L",
        qty=Decimal("1"),
        comment="",
        status=LiveSignalEventStatus.pending,
        realized_pnl=None,
        take_profit=None,
        stop_loss=None,
        trailing_stop=None,
    )


def _install_dispatch(
    monkeypatch: pytest.MonkeyPatch, *, event: SimpleNamespace
) -> tuple[AsyncMock, list[object]]:
    """dispatch의 DB/service 경계를 fake로 두고 execute 호출만 수집한다."""
    _patch_engine(monkeypatch)
    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_failed = AsyncMock(return_value=1)
    event_repo.mark_dispatched = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()
    sess = _session(last_evaluated_bar_time=None)
    sess.id = event.session_id
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=_strategy(sess.strategy_id))
    calls: list[object] = []

    class OrderServiceSpy:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def execute(self, request: object, **_kwargs: object) -> tuple[SimpleNamespace, bool]:
            calls.append(request)
            return SimpleNamespace(id=uuid4()), False

    import src.strategy.repository as strategy_repo_module
    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.kill_switch_event_repository as kse_repo_module
    import src.trading.repositories.live_signal_event_repository as event_repo_module
    import src.trading.repositories.live_signal_session_repository as sess_repo_module
    import src.trading.repositories.order_repository as order_repo_module
    import src.trading.services.order_service as order_service_module

    monkeypatch.setattr(
        event_repo_module, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
    )
    monkeypatch.setattr(
        sess_repo_module, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
    )
    monkeypatch.setattr(
        strategy_repo_module, "StrategyRepository", MagicMock(return_value=strategy_repo)
    )
    monkeypatch.setattr(
        account_repo_module, "ExchangeAccountRepository", MagicMock(return_value=AsyncMock())
    )
    monkeypatch.setattr(
        kse_repo_module, "KillSwitchEventRepository", MagicMock(return_value=AsyncMock())
    )
    monkeypatch.setattr(order_repo_module, "OrderRepository", MagicMock(return_value=AsyncMock()))
    monkeypatch.setattr(order_service_module, "OrderService", OrderServiceSpy)
    return event_repo, calls


@pytest.mark.asyncio
async def test_close_with_explicitly_flat_exchange_is_not_dispatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """close의 0건 응답은 실패 전이하고 OrderService.execute를 호출하지 않는다."""
    event = _dispatch_event(action="close")
    event_repo, calls = _install_dispatch(monkeypatch, event=event)
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._async_dispatch_event(event.id)

    assert result == {"failed": "close_position_flat"}
    assert calls == []
    event_repo.mark_failed.assert_awaited_once_with(event.id, error="close_position_flat")


@pytest.mark.asyncio
async def test_close_position_lookup_failure_is_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """close 포지션 조회 예외는 정당한 청산을 막지 않는다."""
    event = _dispatch_event(action="close")
    _event_repo, calls = _install_dispatch(monkeypatch, event=event)
    _patch_positions(monkeypatch, positions=RuntimeError("exchange down"))

    result = await live_signal_module._async_dispatch_event(event.id)

    assert "dispatched" in result
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_entry_does_not_fetch_positions(monkeypatch: pytest.MonkeyPatch) -> None:
    """진입은 REST 지연을 피하려고 포지션 조회를 절대 열지 않는다."""
    event = _dispatch_event(action="entry")
    _event_repo, calls = _install_dispatch(monkeypatch, event=event)
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._async_dispatch_event(event.id)

    assert "dispatched" in result
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_long_gap_exchange_flat_realigns_epoch_instead_of_deactivating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """거래소 flat 장기 공백은 마지막 bar epoch으로 정렬해 정상 진행한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "B", 1.0, 0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[],
        ),
        inserted_events=[_event(last_signal, sess.id)],
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["position_epoch"] == t6
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_exchange_flat_with_carried_position_still_deactivates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """마지막 bar 이전 entry는 epoch 배선 회귀를 잡기 위해 계속 fail-closed 한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "B", 1.0, 0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[_open_trade(trade_id="B", direction="long", qty=1.0, entry_bar=0)],
        ),
        inserted_events=[_event(last_signal, sess.id)],
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_upsert_records_position_epoch(monkeypatch: pytest.MonkeyPatch) -> None:
    """성공 평가 state JSONB는 다음 재생이 재사용할 epoch을 보존한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    sess = _session(last_evaluated_bar_time=None)
    sess_repo, _event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0),
        run_result=_result(last_bar_time=t0, signals=[]),
        inserted_events=[],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    report = sess_repo.upsert_state.await_args.kwargs["last_strategy_state_report"]
    assert report["_qb_position_epoch"] == t0.isoformat()


@pytest.mark.asyncio
async def test_long_gap_partially_filled_then_cancelled_entry_is_seeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★R1-③(a) — 부분체결 뒤 취소된 조건부 진입도 seed 되어 세션이 산다.

    거래소에는 부분 포지션(0.009)이 남는데 주문 상태는 `cancelled` 다. 원장 조회가 그 행을
    못 보던 동안 엔진은 flat 으로 seed 되어 `gap_resync_position_mismatch` 로 죽었다 —
    BL-544 가 고치려던 그 실패의 형제 케이스다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "L", 0.009, 0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[_open_trade(trade_id="L", direction="long", qty=0.009, entry_bar=1)],
            ledger_seed_applied=("L",),
        ),
        inserted_events=[_event(last_signal, sess.id)],
        ledger_fills=[
            _fill(
                session_id=sess.id,
                side=OrderSide.buy,
                quantity="0.009",
                price="64166.9",
                filled_at=t0 + timedelta(minutes=3),
            )
        ],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.009")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()
    assert [leg.qty for leg in run_kwargs[0]["ledger_seed_legs"]] == [0.009]


@pytest.mark.asyncio
async def test_long_gap_cancellation_without_fill_is_not_seeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★R1-③(b) 음성 대조 — 체결분 없는 취소는 원장 근거가 아니다.

    조회가 그 행을 걸러내므로 창은 비어 있고, 거래소가 non-flat 이면 **계속 죽어야 한다.**
    여기서 살아나면 취소된 주문을 포지션으로 지어낸 것이다.
    """
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
        # 조회 술어가 걸러낸 결과 = 빈 창.
        ledger_fills=[],
    )
    _patch_positions(monkeypatch, positions=[_position(side="long", size="0.009")])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    assert "ledger_seed_legs" not in run_kwargs[0]
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()
