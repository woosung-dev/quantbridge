"""코드의 영구 미확정 행이 legacy 백필 예산을 점유하지 않는 실제 SQL 회귀."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.models import (
    ExchangeAccount,
    ExchangeExit,
    ExchangeMode,
    ExchangeName,
    ExitAttribution,
    ExitClassification,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import CodeClosedPnlEvidence, CodeClosedPnlRead, closed_pnl_raw_hash
from src.trading.repositories.order_repository import OrderRepository
from tests.trading import test_code_closed_pnl_evidence as evidence_tests


@pytest.fixture
async def exit_order(db_session, user, strategy):
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
    )
    db_session.add(account)
    await db_session.flush()
    live = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval="1h",
    )
    db_session.add(live)
    await db_session.flush()
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=live.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(1),
        filled_quantity=D(".3"),
        filled_price=D(100),
        filled_at=datetime.now(UTC),
        state=OrderState.cancelled,
        reduce_only=True,
        leverage=1,
        exchange_order_id="exit",
        risk_context={"session_id": str(live.id), "generation": 1, "role": "partial_tp"},
    )
    db_session.add(order)
    await db_session.flush()
    evidence = CodeClosedPnlEvidence(
        account.id,
        "exit",
        "BTCUSDT",
        OrderSide.sell,
        D(".3"),
        D("-1.25"),
        closed_pnl_raw_hash(evidence_tests.raw()),
    )
    return OrderRepository(db_session), live, order, evidence


@pytest.mark.parametrize("limit", [1, 2])
@pytest.mark.parametrize("synced", [False, True])
async def test_legacy_budget_is_independent_of_unresolvable_code_rows(
    db_session, user, strategy, limit, synced
):
    now = datetime.now(UTC)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
    )
    db_session.add(account)
    await db_session.flush()
    legacy, eligible, excluded = [], [], []
    for index, kind in enumerate(
        ["conflict", "expired", "proof", "entry", "native", "ready", "ready", "legacy", "legacy"]
    ):
        code = kind != "legacy"
        context = {"role": "close", "session_id": str(uuid4()), "generation": 1} if code else None
        if kind == "conflict":
            context["pnl_evidence_conflict"] = {"reason": "different_raw_observations"}
        if kind == "proof":
            context["code_pnl_evidence"] = {"raw_hash": "existing"}
        if kind == "entry":
            context["role"] = "entry"
        if kind == "native":
            context["native_origin"] = "bybit_attached_sl"
        # 미확정 코드는 정렬 앞에 있어도 legacy의 별도 예산을 점유하지 않는다.
        age = 8 if kind == "expired" else (10 if kind == "legacy" and synced else 0)
        terminal_at = now - timedelta(days=age, minutes=index)
        identifier = uuid4().hex
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=D(1),
            filled_quantity=D(1),
            filled_price=D(100),
            filled_at=terminal_at,
            state=OrderState.filled,
            reduce_only=kind != "entry",
            exchange_order_id=identifier,
            risk_context=context,
            realized_pnl=D(1) if synced else None,
            realized_pnl_synced_at=now if synced else None,
            created_at=now - timedelta(days=30),
            submitted_at=now - timedelta(days=20),
        )
        db_session.add(order)
        db_session.add(
            ExchangeExit(
                exchange_account_id=account.id,
                exchange_order_id=identifier,
                row_hash=uuid4().hex,
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=D(2),
                closed_size=D(1),
                exchange_created_at=now,
                classification=ExitClassification.ours,
                attribution_confidence=ExitAttribution.exact,
                raw={"orderId": identifier},
            )
        )
        (legacy if not code else eligible if kind == "ready" else excluded).append(order)
    await db_session.flush()
    repo = OrderRepository(db_session)
    legacy_method = (
        repo.list_synced_with_exchange_exit if synced else repo.list_unsynced_with_exchange_exit
    )
    for _ in range(2):
        selected = await legacy_method(account.id, limit=limit)
        assert len(selected) == limit and {o.id for o in selected} <= {o.id for o in legacy}
        code_rows = await repo.list_code_pnl_candidates(
            account.id, filled_since=now - timedelta(days=7), limit=limit
        )
        assert len(code_rows) == limit and {o.id for o in code_rows} <= {o.id for o in eligible}
        assert not {o.id for o in code_rows} & {o.id for o in excluded}
    # 오래 대기했다가 방금 종결된 주문은 생성 시각이 아니라 terminal 창으로 포함된다.
    assert all(o.created_at < now - timedelta(days=7) for o in code_rows)
    assert not await repo.list_code_pnl_candidates(uuid4(), filled_since=now - timedelta(days=7))


@pytest.mark.parametrize("excluded", ["conflict", "expired", "proof", "ready"])
async def test_actual_sweep_code_eligibility_controls_strict_rpc(
    exit_order, db_session, monkeypatch, excluded
):
    from src.tasks import trading
    from tests.tasks.test_exchange_order_response_metric import _Crypto

    repo, _live, order, evidence = exit_order
    now = datetime.now(UTC)
    if excluded == "conflict":
        order.risk_context = {
            **order.risk_context,
            "pnl_evidence_conflict": {"reason": "different_raw_observations"},
        }
    elif excluded == "expired":
        order.filled_at = now - timedelta(days=8)
    elif excluded == "proof":
        assert (
            await repo.backfill_exchange_realized_pnl(
                order.id, realized_pnl=evidence.pnl, synced_at=now, code_evidence=evidence
            )
            == 1
        )
    # 모든 후보에 원장 행이 있으므로 RPC 0건은 원장 누락 때문이 아니다.
    db_session.add(
        ExchangeExit(
            exchange_account_id=order.exchange_account_id,
            exchange_order_id=order.exchange_order_id,
            row_hash=uuid4().hex,
            symbol="BTCUSDT",
            side="Sell",
            closed_pnl=evidence.pnl,
            closed_size=evidence.quantity,
            exchange_created_at=now,
            classification=ExitClassification.ours,
            attribution_confidence=ExitAttribution.exact,
            raw=evidence_tests.raw(),
        )
    )
    await repo.commit()
    provider = AsyncMock()
    provider.fetch_closed_pnl_window.return_value = []
    provider.fetch_code_closed_pnl.return_value = CodeClosedPnlRead(evidence)
    queried_since = []
    candidate_read = OrderRepository.list_code_pnl_candidates

    async def tracked_candidates(self, account_id, *, filled_since, limit=500):
        queried_since.append(filled_since)
        return await candidate_read(self, account_id, filled_since=filled_since, limit=limit)

    monkeypatch.setattr(OrderRepository, "list_code_pnl_candidates", tracked_candidates)
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    monkeypatch.setattr(trading, "_alert_new_exchange_exits", AsyncMock(return_value=False))

    @asynccontextmanager
    async def sm():
        yield db_session

    summary = await trading._sweep_closed_pnl_with_session(sm, provider=provider, now=now)
    assert provider.fetch_code_closed_pnl.await_count == int(excluded == "ready")
    assert summary["backfilled"] == int(excluded == "ready") and summary["resynced"] == 0
    assert len(queried_since) == 1
    assert (
        int(queried_since[0].timestamp() * 1000)
        == int(now.timestamp() * 1000) - trading._EXIT_WINDOW_MS
    )
