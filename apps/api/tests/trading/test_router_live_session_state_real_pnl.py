"""GET /api/v1/live-sessions/{id}/state — 실현손익 실체결 기준 재계산 (2026-07-01 dogfood).

`LiveSignalState.total_realized_pnl`/`equity_curve` 는 Pine 시뮬레이션 재생
결과라 실제 거래소 체결과 무관했다. 엔드포인트가 실제 filled 주문 기준으로
재계산해 반환하는지 검증.

Uses mock_clerk_auth fixture from conftest.py for auth bypass.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    LiveSignalState,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)

# BL-445 이후 세션 스코프는 `created_at` 을 하한으로 쓴다. 이 파일의 주문들은
# 2026-07-01 체결이라 세션이 그보다 먼저 시작해 있어야 원래 관심사(시뮬 값이 아니라
# 실체결을 쓰는가)를 검증할 수 있다.
_SESSION_START = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)


async def _seed_session(db_session, user, *, with_state: bool = True):
    strategy = Strategy(
        user_id=user.id,
        name="s",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        created_at=_SESSION_START,
    )
    db_session.add(session)
    await db_session.flush()

    # 시뮬레이션 재생 결과(잘못된 값) — 실제로는 이 값이 그대로 노출되면 안 된다.
    if with_state:
        state = LiveSignalState(
            session_id=session.id,
            last_strategy_state_report={"position_size": 0.0},
            total_closed_trades=153,
            total_realized_pnl=Decimal("-1007.70"),
            equity_curve=[{"timestamp_ms": 1782894780000, "cumulative_pnl": "-1007.70"}],
        )
        db_session.add(state)
    await db_session.commit()
    return strategy, account, session


@pytest.mark.asyncio
async def test_state_uses_real_filled_pnl_not_simulation(client, mock_clerk_auth, db_session):
    """rejected 주문의 시뮬레이션 pnl은 무시하고, filled 주문의 실현손익만 반영."""
    user = mock_clerk_auth
    strategy, account, session = await _seed_session(db_session, user)

    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.rejected,
            realized_pnl=Decimal("-1007.70"),
            filled_at=datetime(2026, 7, 1, 8, 34, 27, tzinfo=UTC),
        )
    )
    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal("42.50"),
            filled_at=datetime(2026, 7, 1, 8, 40, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/live-sessions/{session.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert Decimal(str(body["total_realized_pnl"])) == Decimal("42.50")
    assert body["total_closed_trades"] == 1
    assert len(body["equity_curve"]) == 1
    assert body["equity_curve"][0]["timestamp_ms"] == int(
        datetime(2026, 7, 1, 8, 40, 0, tzinfo=UTC).timestamp() * 1000
    )
    assert Decimal(str(body["equity_curve"][0]["cumulative_pnl"])) == Decimal("42.50")
    # Pine 엔진 내부 상태 표시는 그대로 유지 (변경 대상 아님)
    assert body["last_strategy_state_report"] == {"position_size": 0.0}


@pytest.mark.asyncio
async def test_state_returns_zero_when_no_filled_orders_yet(client, mock_clerk_auth, db_session):
    """체결된 실주문이 아직 없으면(예: 첫 신호가 리젝트) 0으로 보여야 한다."""
    user = mock_clerk_auth
    strategy, account, session = await _seed_session(db_session, user)

    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.rejected,
            realized_pnl=Decimal("-1007.70"),
            filled_at=datetime(2026, 7, 1, 8, 34, 27, tzinfo=UTC),
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/live-sessions/{session.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert Decimal(str(body["total_realized_pnl"])) == Decimal("0")
    assert body["total_closed_trades"] == 0
    assert body["equity_curve"] == []


@pytest.mark.asyncio
async def test_state_pending_returns_unevaluated_zero_response(client, mock_clerk_auth, db_session):
    """세션은 있으나 첫 평가 전이면 404 대신 pending 응답을 반환한다."""
    _, _, session = await _seed_session(db_session, mock_clerk_auth, with_state=False)

    resp = await client.get(f"/api/v1/live-sessions/{session.id}/state")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "session_id": str(session.id),
        "evaluated": False,
        "schema_version": 0,
        "last_strategy_state_report": {},
        "total_closed_trades": 0,
        "total_realized_pnl": "0",
        # BL-458 — 소계도 응답 형태의 일부다. 이 정확-dict 단정이 신규 필드를 그냥
        # 통과시키면 응답 계약 동결이 무의미해지므로 명시적으로 적는다.
        "confirmed_realized_pnl": "0",
        "estimated_realized_pnl": "0",
        "confirmed_closed_trades": 0,
        "estimated_closed_trades": 0,
        "equity_curve": [],
        "updated_at": None,
    }


@pytest.mark.asyncio
async def test_state_missing_or_not_owned_remains_not_found(client, mock_clerk_auth, db_session):
    """없는 세션과 타인 세션은 pending으로 숨기지 않고 404를 유지한다."""
    missing = await client.get(f"/api/v1/live-sessions/{uuid4()}/state")
    assert missing.status_code == 404

    other_user = User(
        clerk_user_id=f"other_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(other_user)
    await db_session.flush()
    _, _, other_session = await _seed_session(db_session, other_user)

    not_owned = await client.get(f"/api/v1/live-sessions/{other_session.id}/state")
    assert not_owned.status_code == 404


@pytest.mark.asyncio
async def test_two_sessions_on_the_same_tuple_get_separate_curves(
    client, mock_clerk_auth, db_session
):
    """BL-445 종단 — 같은 (strategy, account) 위 인접 세션 둘이 서로 다른 커브를 낸다.

    fix 전에는 라우터가 `(strategy_id, exchange_account_id)` 만 넘겨서 두 세션이
    **같은 값**(-30)을 돌려줬다. 리포지터리만 고치고 라우터가 스코프를 안 넘기는
    실수는 이 종단 테스트로만 잡힌다.
    """
    user = mock_clerk_auth
    strategy, account, first = await _seed_session(db_session, user)
    boundary = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)

    # 첫 세션을 경계에서 닫고, 같은 튜플 위에 두 번째 세션을 연다.
    first.is_active = False
    first.deactivated_at = boundary
    second = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        created_at=boundary,
    )
    db_session.add(second)
    await db_session.flush()
    db_session.add(LiveSignalState(session_id=second.id))

    def _filled(pnl: str, filled_at: datetime) -> Order:
        return Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal(pnl),
            filled_at=filled_at,
        )

    db_session.add_all(
        [
            _filled("-10", boundary - timedelta(hours=1)),
            _filled("-20", boundary + timedelta(hours=1)),
        ]
    )
    await db_session.commit()

    first_body = (await client.get(f"/api/v1/live-sessions/{first.id}/state")).json()
    second_body = (await client.get(f"/api/v1/live-sessions/{second.id}/state")).json()

    assert Decimal(str(first_body["total_realized_pnl"])) == Decimal("-10")
    assert Decimal(str(second_body["total_realized_pnl"])) == Decimal("-20")
    assert first_body["total_closed_trades"] == second_body["total_closed_trades"] == 1
    assert len(first_body["equity_curve"]) == len(second_body["equity_curve"]) == 1


@pytest.mark.asyncio
async def test_state_labels_each_curve_point_with_its_provenance(
    client, mock_clerk_auth, db_session
):
    """BL-458 — 커브 포인트마다 그 시점 델타의 출처가 실려야 한다.

    ★이 테스트의 진짜 목적은 **리포지토리의 SQL 술어와 라우터의 파이썬 라벨이 서로
    반전되지 않았는지** 확인하는 것이다. 두 경로는 독립 구현이라 한쪽만 뒤집혀도
    합계는 맞고 라벨만 거짓이 된다 — 그 상태는 화면에서 구분할 수 없다.

    금액을 서로 다르게 심어 어느 쪽이 뒤집혔는지 숫자가 지목하게 한다.
    """
    _, account, session = await _seed_session(db_session, mock_clerk_auth)
    strategy_id = session.strategy_id

    def _order(*, pnl: str, minute: int, synced: bool):
        return Order(
            strategy_id=strategy_id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal(pnl),
            realized_pnl_synced_at=(
                datetime(2026, 7, 1, 9, 0, tzinfo=UTC) if synced else None
            ),
            filled_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC) + timedelta(minutes=minute),
        )

    # 시간 순서대로 추정 → 확정. 라벨이 뒤집히면 순서가 반대로 나온다.
    db_session.add_all(
        [
            _order(pnl="-4", minute=1, synced=False),
            _order(pnl="-2", minute=2, synced=True),
        ]
    )
    await db_session.flush()

    resp = await client.get(f"/api/v1/live-sessions/{session.id}/state")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [p["source"] for p in body["equity_curve"]] == ["estimated", "confirmed"]
    # 누적은 그대로 −4 → −6. 라벨은 가산적이고 산술을 건드리지 않는다.
    # `Numeric(18,8)` 이라 문자열은 `-4.00000000` 로 온다 — 값으로 비교한다.
    assert [Decimal(p["cumulative_pnl"]) for p in body["equity_curve"]] == [
        Decimal("-4"),
        Decimal("-6"),
    ]
    assert Decimal(body["confirmed_realized_pnl"]) == Decimal("-2")
    assert Decimal(body["estimated_realized_pnl"]) == Decimal("-4")
    assert (body["confirmed_closed_trades"], body["estimated_closed_trades"]) == (1, 1)
    # ★항등식 — 소계 합이 게이트가 쓰는 총계와 같다.
    assert Decimal(body["confirmed_realized_pnl"]) + Decimal(
        body["estimated_realized_pnl"]
    ) == Decimal(body["total_realized_pnl"])
