"""GET /api/v1/live-sessions/{id}/outcome-parity 계약 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.engine.types import BacktestConfig
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeExit,
    ExchangeMode,
    ExchangeName,
    ExitAttribution,
    ExitClassification,
    LiveSignalEvent,
    LiveSignalEventStatus,
    LiveSignalInterval,
    LiveSignalSession,
    LiveSignalState,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)

_BASE = datetime(2026, 7, 28, 12, tzinfo=UTC)


async def _create_session(
    db_session: AsyncSession,
    user: User,
    *,
    exchange: ExchangeName = ExchangeName.bybit,
) -> LiveSignalSession:
    strategy = Strategy(
        user_id=user.id,
        name="Parity strategy",
        pine_source="//@version=5\nstrategy('parity')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=exchange,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        created_at=_BASE,
    )
    db_session.add(session)
    await db_session.flush()
    return session


async def _seed_parity_data(
    db_session: AsyncSession,
    user: User,
) -> LiveSignalSession:
    session = await _create_session(db_session, user)
    previous_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        interval=LiveSignalInterval.m1,
        is_active=False,
        created_at=_BASE - timedelta(hours=2),
        deactivated_at=_BASE - timedelta(hours=1),
    )
    db_session.add_all([previous_session, LiveSignalState(session_id=session.id)])
    await db_session.flush()

    session_order = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1"),
        filled_quantity=Decimal("1"),
        state=OrderState.filled,
        realized_pnl=Decimal("7"),
        realized_pnl_synced_at=_BASE + timedelta(minutes=2),
        filled_at=_BASE + timedelta(minutes=1),
    )
    unsynced_session_order = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1"),
        filled_quantity=Decimal("1"),
        state=OrderState.filled,
        realized_pnl=Decimal("999"),
        filled_at=_BASE + timedelta(minutes=2),
    )
    previous_order = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1"),
        filled_quantity=Decimal("1"),
        state=OrderState.filled,
        realized_pnl=Decimal("3"),
        realized_pnl_synced_at=_BASE - timedelta(hours=1, minutes=30),
        filled_at=_BASE - timedelta(hours=1, minutes=30),
    )
    db_session.add_all([session_order, unsynced_session_order, previous_order])
    await db_session.flush()

    db_session.add_all(
        [
            LiveSignalEvent(
                session_id=session.id,
                bar_time=_BASE,
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="session-close",
                qty=Decimal("1"),
                realized_pnl=Decimal("8"),
                status=LiveSignalEventStatus.dispatched,
                order_id=session_order.id,
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=_BASE + timedelta(minutes=1),
                sequence_no=2,
                action="close",
                direction="long",
                trade_id="unsynced-session-close",
                qty=Decimal("1"),
                realized_pnl=Decimal("999"),
                status=LiveSignalEventStatus.dispatched,
                order_id=unsynced_session_order.id,
            ),
            LiveSignalEvent(
                session_id=previous_session.id,
                bar_time=_BASE - timedelta(hours=1, minutes=45),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="previous-close",
                qty=Decimal("1"),
                realized_pnl=Decimal("4"),
                status=LiveSignalEventStatus.dispatched,
                order_id=previous_order.id,
            ),
            ExchangeExit(
                exchange_account_id=session.exchange_account_id,
                exchange_order_id="session-exit",
                row_hash="session-exit-row",
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=Decimal("7"),
                closed_size=Decimal("1"),
                avg_entry_price=Decimal("100"),
                avg_exit_price=Decimal("110"),
                exchange_created_at=_BASE + timedelta(minutes=2),
                classification=ExitClassification.ours,
                matched_order_id=session_order.id,
                attribution_confidence=ExitAttribution.exact,
                raw={"source": "outcome-parity-api-test"},
            ),
        ]
    )
    await db_session.commit()
    return session


@pytest.mark.asyncio
async def test_response_has_three_blocks_and_required_fields(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _seed_parity_data(db_session, mock_clerk_auth)

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    body = response.json()
    assert {
        "session",
        "strategy",
        "unattributed_count",
        "inferred_attribution_count",
        "ledger_supported",
        "strategy_session_count",
        "assumption",
    } <= body.keys()
    for scope in (body["session"], body["strategy"]):
        assert {
            "match_coverage_pct",
            "decomposition_coverage_pct",
            "effective_cost_pct_per_leg",
            "effective_cost_pct_round_trip",
            "edge_pct_round_trip",
            "cost_to_edge_ratio",
            "ledger_only_count",
            "ledger_only_net",
            "sample_required_n",
            "ratio_sample_n",
            "ratio_sample_required_n",
            "ratio_sample_sufficient",
        } <= scope.keys()
        assert "unattributed_count" not in scope
    assert body["unattributed_count"] == 0
    assert body["inferred_attribution_count"] == 0
    assert body["ledger_supported"] is True
    assert body["strategy_session_count"] == 2


@pytest.mark.asyncio
async def test_native_bracket_split_exit_is_summed_in_ledger_only_bucket_and_lowers_coverage(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """로컬 reduce-only 주문 없는 거래소 TP 분할 행은 주문 단위로 합산한다."""
    session = await _seed_parity_data(db_session, mock_clerk_auth)
    exchange_created_at = _BASE + timedelta(minutes=3)
    db_session.add_all(
        [
            ExchangeExit(
                exchange_account_id=session.exchange_account_id,
                exchange_order_id="native-bracket-tp",
                row_hash="native-bracket-tp-primary",
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=Decimal("-1.0"),
                exchange_created_at=exchange_created_at,
                classification=ExitClassification.bracket_tp,
                attributed_strategy_id=session.strategy_id,
                attribution_confidence=ExitAttribution.exact,
                raw={"source": "native-bracket-tp"},
            ),
            ExchangeExit(
                exchange_account_id=session.exchange_account_id,
                exchange_order_id="native-bracket-tp",
                row_hash="native-bracket-tp-mirror",
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=Decimal("-2.0"),
                exchange_created_at=exchange_created_at,
                classification=ExitClassification.bracket_tp,
                attributed_strategy_id=session.strategy_id,
                attribution_confidence=ExitAttribution.exact,
                raw={"source": "native-bracket-tp-mirror"},
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    body = response.json()
    session_scope = body["session"]
    assert session_scope["ledger_only_count"] == 1
    assert Decimal(session_scope["ledger_only_net"]) == Decimal("-3.0")
    assert Decimal(session_scope["match_coverage_pct"]) < Decimal("50")
    assert body["unattributed_count"] == 0


@pytest.mark.asyncio
async def test_inferred_attribution_is_exposed_without_entering_ledger_only(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """검정력 없는 귀속은 진단만 하고 전략 손익 버킷에는 넣지 않는다."""
    session = await _seed_parity_data(db_session, mock_clerk_auth)
    db_session.add(
        ExchangeExit(
            exchange_account_id=session.exchange_account_id,
            exchange_order_id="inferred-bracket",
            row_hash="inferred-bracket-row",
            symbol="BTCUSDT",
            side="Sell",
            closed_pnl=Decimal("-1"),
            exchange_created_at=_BASE + timedelta(minutes=3),
            classification=ExitClassification.bracket_tp,
            attributed_strategy_id=session.strategy_id,
            attribution_confidence=ExitAttribution.inferred,
            raw={"source": "inferred-bracket"},
        )
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["session"]["ledger_only_count"] == 0
    assert body["session"]["inferred_attribution_count"] == 1
    assert body["strategy"]["inferred_attribution_count"] == 1
    assert body["inferred_attribution_count"] == 1


@pytest.mark.asyncio
async def test_ledger_only_is_scoped_per_session_and_strategy_union(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _seed_parity_data(db_session, mock_clerk_auth)
    previous_session = (
        await db_session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.strategy_id == session.strategy_id)
            .where(LiveSignalSession.id != session.id)
        )
    ).scalar_one()
    db_session.add_all(
        [
            ExchangeExit(
                exchange_account_id=session.exchange_account_id,
                exchange_order_id="previous-native-bracket",
                row_hash="previous-native-bracket-row",
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=Decimal("-1"),
                exchange_created_at=previous_session.created_at + timedelta(minutes=30),
                classification=ExitClassification.bracket_tp,
                attributed_strategy_id=session.strategy_id,
                attribution_confidence=ExitAttribution.exact,
                raw={"source": "previous-native-bracket"},
            ),
            ExchangeExit(
                exchange_account_id=session.exchange_account_id,
                exchange_order_id="current-native-bracket",
                row_hash="current-native-bracket-row",
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=Decimal("-2"),
                exchange_created_at=_BASE + timedelta(minutes=3),
                classification=ExitClassification.bracket_tp,
                attributed_strategy_id=session.strategy_id,
                attribution_confidence=ExitAttribution.exact,
                raw={"source": "current-native-bracket"},
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["session"]["ledger_only_count"] == 1
    assert Decimal(body["session"]["ledger_only_net"]) == Decimal("-2")
    assert body["strategy"]["ledger_only_count"] == 2
    assert Decimal(body["strategy"]["ledger_only_net"]) == Decimal("-3")


@pytest.mark.asyncio
async def test_waterfall_closes_on_the_decomposable_subset(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _seed_parity_data(db_session, mock_clerk_auth)

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    scope = response.json()["session"]
    assert scope["decomposable_count"] == 1
    assert Decimal(scope["decomposable_expected_gross"]) + Decimal(
        scope["execution_gap"]
    ) + Decimal(scope["cost"]) == Decimal(scope["decomposable_actual_net"])


@pytest.mark.asyncio
async def test_actual_net_equals_state_confirmed_realized_pnl(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _seed_parity_data(db_session, mock_clerk_auth)

    parity_response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")
    state_response = await client.get(f"/api/v1/live-sessions/{session.id}/state")

    assert parity_response.status_code == 200, parity_response.text
    assert state_response.status_code == 200, state_response.text
    actual_net = Decimal(parity_response.json()["session"]["actual_net"])
    state = state_response.json()
    assert actual_net == Decimal(state["confirmed_realized_pnl"])
    assert actual_net != Decimal(state["total_realized_pnl"])


@pytest.mark.asyncio
async def test_strategy_scope_contains_the_session_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _seed_parity_data(db_session, mock_clerk_auth)

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy"]["matched_count"] >= body["session"]["matched_count"]
    assert body["strategy_session_count"] == 2


@pytest.mark.asyncio
async def test_non_bybit_account_reports_ledger_as_unsupported(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _create_session(
        db_session,
        mock_clerk_auth,
        exchange=ExchangeName.okx,
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    assert response.json()["ledger_supported"] is False


@pytest.mark.asyncio
async def test_assumption_reports_house_defaults(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    session = await _seed_parity_data(db_session, mock_clerk_auth)

    response = await client.get(f"/api/v1/live-sessions/{session.id}/outcome-parity")

    assert response.status_code == 200, response.text
    config = BacktestConfig()
    assumption = response.json()["assumption"]
    assert assumption["source"] == "house_default"
    assert Decimal(assumption["taker_fee_pct"]) == Decimal(str(config.fees)) * Decimal("100")
    assert Decimal(assumption["slippage_pct"]) == Decimal(str(config.slippage)) * Decimal("100")
    assert Decimal(assumption["maker_fee_pct"]) == Decimal(str(config.maker_fee)) * Decimal("100")
    assert Decimal(assumption["implied_round_trip_pct"]) == (
        Decimal(str(config.fees)) + Decimal(str(config.slippage))
    ) * Decimal("2") * Decimal("100")


@pytest.mark.asyncio
async def test_outcome_parity_hides_other_users_session(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    other_user = User(
        clerk_user_id=f"other-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
    )
    db_session.add(other_user)
    await db_session.flush()
    other_session = await _create_session(db_session, other_user)
    await db_session.commit()

    response = await client.get(f"/api/v1/live-sessions/{other_session.id}/outcome-parity")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "live_signal_session_not_found"


@pytest.mark.asyncio
async def test_outcome_parity_returns_not_found_for_missing_session(
    client: AsyncClient,
    mock_clerk_auth,
) -> None:
    response = await client.get(f"/api/v1/live-sessions/{uuid4()}/outcome-parity")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "live_signal_session_not_found"
