"""Sprint 26 — `live_signal.dispatch_event` (per-event dispatch task) 단위 테스트.

검증 범위:
- missing event → skipped='missing'
- already dispatched → skipped='already_terminal' (duplicate apply_async 방어)
- session_inactive → mark_failed + commit
- 정상 dispatch → OrderService.execute → mark_dispatched + order_id
- KillSwitchActive → mark_failed + raise + outcome='kill_switched'
- sessions_port DI 검증 (P1 #5 _StrategySessionsAdapter 의무 주입)
- idempotency_key 형식 검증 (P2 #5 sequence_no 포함)

Sprint 18 BL-080 prefork-safe — `create_worker_engine_and_sm` mock 주입.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# src/tasks/__init__.py reexport 회피 — sys.modules 우회
import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401

live_signal_module = sys.modules["src.tasks.live_signal"]

from src.trading.exceptions import KillSwitchActive  # noqa: E402
from src.trading.models import (  # noqa: E402
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    OrderSide,
    OrderType,
)

# ── Helpers ─────────────────────────────────────────────────────────────


def _make_engine_sm_mocks(session_mock: AsyncMock) -> tuple[Any, Any]:
    engine = AsyncMock()
    engine.dispose = AsyncMock()

    class _SMContext:
        async def __aenter__(self) -> AsyncMock:
            return session_mock

        async def __aexit__(self, *_exc: object) -> None:
            return None

    def _sm_factory() -> _SMContext:
        return _SMContext()

    return engine, _sm_factory


def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    session = AsyncMock()
    engine, sm_factory = _make_engine_sm_mocks(session)
    monkeypatch.setattr(
        live_signal_module, "create_worker_engine_and_sm", lambda: (engine, sm_factory)
    )
    return session


def _patch_repos(
    monkeypatch: pytest.MonkeyPatch,
    *,
    event_repo: AsyncMock | None = None,
    sess_repo: AsyncMock | None = None,
    strategy_repo: AsyncMock | None = None,
    order_repo: AsyncMock | None = None,
    account_repo: AsyncMock | None = None,
    kse_repo: AsyncMock | None = None,
) -> None:
    """import 위치는 _async_dispatch_event 함수 내부 (lazy)."""
    import src.strategy.repository as strategy_repo_mod
    import src.trading.repository as trading_repo_mod

    if event_repo is not None:
        monkeypatch.setattr(
            trading_repo_mod, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
        )
    if sess_repo is not None:
        monkeypatch.setattr(
            trading_repo_mod, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
        )
    if strategy_repo is not None:
        monkeypatch.setattr(
            strategy_repo_mod, "StrategyRepository", MagicMock(return_value=strategy_repo)
        )
    if order_repo is not None:
        monkeypatch.setattr(
            trading_repo_mod, "OrderRepository", MagicMock(return_value=order_repo)
        )
    if account_repo is not None:
        monkeypatch.setattr(
            trading_repo_mod, "ExchangeAccountRepository", MagicMock(return_value=account_repo)
        )
    if kse_repo is not None:
        monkeypatch.setattr(
            trading_repo_mod, "KillSwitchEventRepository", MagicMock(return_value=kse_repo)
        )


def _build_pending_event() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        session_id=uuid4(),
        bar_time=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        sequence_no=0,
        action="entry",
        direction="long",
        trade_id="L",
        qty=Decimal("1.0"),
        comment="",
        status=LiveSignalEventStatus.pending,
    )


def _build_active_session(strategy_id: UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=strategy_id,
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        is_active=True,
    )


# ── Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_event_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_engine(monkeypatch)
    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=None)
    _patch_repos(monkeypatch, event_repo=event_repo)

    res = await live_signal_module._async_dispatch_event(uuid4())
    assert res == {"skipped": "missing"}


@pytest.mark.asyncio
async def test_already_terminal_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """status != pending → skipped (duplicate apply_async)."""
    _patch_engine(monkeypatch)
    event = _build_pending_event()
    event.status = LiveSignalEventStatus.dispatched
    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    _patch_repos(monkeypatch, event_repo=event_repo)

    res = await live_signal_module._async_dispatch_event(event.id)
    assert res["skipped"] == "already_terminal"


@pytest.mark.asyncio
async def test_session_inactive_marks_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_engine(monkeypatch)
    event = _build_pending_event()
    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_failed = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(
            id=event.session_id, user_id=uuid4(), is_active=False
        )
    )
    _patch_repos(monkeypatch, event_repo=event_repo, sess_repo=sess_repo)

    res = await live_signal_module._async_dispatch_event(event.id)
    assert res == {"failed": "session_inactive"}
    event_repo.mark_failed.assert_awaited_once()
    event_repo.commit.assert_awaited_once()  # LESSON-019 spy


@pytest.mark.asyncio
async def test_dispatch_success_marks_dispatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 OrderService.execute → mark_dispatched + order_id 채워짐.

    P1 #5 sessions_port DI 검증 + P2 #5 idempotency_key sequence_no 포함.
    """
    _patch_engine(monkeypatch)
    event = _build_pending_event()
    sess = _build_active_session(uuid4())
    sess.id = event.session_id

    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_dispatched = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()

    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 5, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
        )
    )

    order_repo = AsyncMock()
    account_repo = AsyncMock()
    kse_repo = AsyncMock()

    _patch_repos(
        monkeypatch,
        event_repo=event_repo,
        sess_repo=sess_repo,
        strategy_repo=strategy_repo,
        order_repo=order_repo,
        account_repo=account_repo,
        kse_repo=kse_repo,
    )

    # OrderService.execute mock — sessions_port 가 주입됐는지 spy
    captured_kwargs: dict[str, Any] = {}
    captured_idempotency_key: list[str] = []

    class _OrderServiceSpy:
        def __init__(self, **kwargs: Any) -> None:
            captured_kwargs.update(kwargs)

        async def execute(
            self, req: Any, *, idempotency_key: str | None, body_hash: bytes | None = None
        ) -> tuple[Any, bool]:
            captured_idempotency_key.append(idempotency_key or "")
            return (
                SimpleNamespace(id=uuid4(), state="pending", side=req.side),
                False,
            )

    import src.trading.service as trading_service_mod
    monkeypatch.setattr(trading_service_mod, "OrderService", _OrderServiceSpy)

    # Other deps (KillSwitchService etc) → no-op stubs (OrderService spy 가 직접 reject 안 함)
    import src.trading.kill_switch as kill_switch_mod
    monkeypatch.setattr(kill_switch_mod, "KillSwitchService", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "CumulativeLossEvaluator", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "DailyLossEvaluator", MagicMock())

    res = await live_signal_module._async_dispatch_event(event.id)
    assert "dispatched" in res
    event_repo.mark_dispatched.assert_awaited_once()
    event_repo.commit.assert_awaited_once()  # LESSON-019 spy

    # P1 #5 — sessions_port DI 의무 (None 이면 OrderService 가 trading_sessions guard 우회)
    assert "sessions_port" in captured_kwargs
    assert captured_kwargs["sessions_port"] is not None

    # P2 #5 — idempotency_key sequence_no 포함
    assert len(captured_idempotency_key) == 1
    key = captured_idempotency_key[0]
    assert f":{event.sequence_no}:" in key, f"sequence_no 가 idempotency_key 에 누락: {key}"
    assert f":{event.action}:" in key
    assert event.trade_id in key


@pytest.mark.asyncio
async def test_kill_switch_active_marks_failed_and_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KillSwitchActive raise → mark_failed(error='kill_switched') + commit + raise."""
    _patch_engine(monkeypatch)
    event = _build_pending_event()
    sess = _build_active_session(uuid4())
    sess.id = event.session_id

    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_failed = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()

    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 5, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
        )
    )

    _patch_repos(
        monkeypatch,
        event_repo=event_repo,
        sess_repo=sess_repo,
        strategy_repo=strategy_repo,
        order_repo=AsyncMock(),
        account_repo=AsyncMock(),
        kse_repo=AsyncMock(),
    )

    class _OrderServiceKS:
        def __init__(self, **_: Any) -> None:
            pass

        async def execute(self, *_a: Any, **_kw: Any) -> tuple[Any, bool]:
            raise KillSwitchActive("Kill Switch active for cumulative_loss")

    import src.trading.service as trading_service_mod
    monkeypatch.setattr(trading_service_mod, "OrderService", _OrderServiceKS)

    import src.trading.kill_switch as kill_switch_mod
    monkeypatch.setattr(kill_switch_mod, "KillSwitchService", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "CumulativeLossEvaluator", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "DailyLossEvaluator", MagicMock())

    with pytest.raises(KillSwitchActive):
        await live_signal_module._async_dispatch_event(event.id)

    event_repo.mark_failed.assert_awaited_once()
    _args, kwargs = event_repo.mark_failed.await_args
    assert kwargs.get("error") == "kill_switched"
    event_repo.commit.assert_awaited_once()  # LESSON-019


# ── Helper unit tests ───────────────────────────────────────────────────


def test_signal_to_order_side_entry_long() -> None:
    assert live_signal_module._signal_to_order_side("entry", "long") == OrderSide.buy


def test_signal_to_order_side_entry_short() -> None:
    assert live_signal_module._signal_to_order_side("entry", "short") == OrderSide.sell


def test_signal_to_order_side_close_long() -> None:
    assert live_signal_module._signal_to_order_side("close", "long") == OrderSide.sell


def test_signal_to_order_side_close_short() -> None:
    assert live_signal_module._signal_to_order_side("close", "short") == OrderSide.buy


def test_signal_to_order_side_unsupported_raises() -> None:
    with pytest.raises(ValueError, match="action"):
        live_signal_module._signal_to_order_side("fill", "long")


def test_build_idempotency_key_includes_sequence_no() -> None:
    """P2 #5 — idempotency_key 에 sequence_no 포함 (같은 bar entry+close 분리)."""
    sess_id = uuid4()
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    key1 = live_signal_module._build_idempotency_key(
        session_id=sess_id, bar_time=bar_time, sequence_no=0, action="entry", trade_id="L"
    )
    key2 = live_signal_module._build_idempotency_key(
        session_id=sess_id, bar_time=bar_time, sequence_no=1, action="close", trade_id="L"
    )
    assert key1 != key2
    assert ":0:" in key1
    assert ":1:" in key2


# Suppress unused imports
_ = (UTC, datetime, OrderType, ExchangeMode, ExchangeName)
