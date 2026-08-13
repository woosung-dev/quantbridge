"""B1 — `POST /orders/{id}/cancel` 의 `qb_active_orders.dec()` 고장 주입 (BL-580).

★**이 테스트가 왜 있나.** BL-580 은 이 자리를 「실패로 계상하는 `except` 가 없다」는 이유로
가드 대상에서 뺐다. 그 판정은 **코드 독해**였다. 실제로 주입해 보니 귀결이 달랐다 —
취소는 `repo.commit()`(`router.py:371`)으로 이미 확정되는데 그 **뒤**의 계측이 던지면
핸들러가 통째로 실패하고, 사용자는 **성공한 취소를 실패로 본다**(H1).

사전등록 postcondition (`dev-log/2026-08-03-metric-guard-residual.md` §1.2b B1):
계측이 성공했다면 반드시 일어났을 비-계측 작업 = **HTTP 200 + `OrderResponse` 반환**.

★주입한 stub 이 실제로 호출됐음을 함께 단언한다 — 그것이 없으면 이 테스트는
「프로덕션 라인을 실행하지 않는 단언」과 구별되지 않는다(이 레포가 3번 밟았다).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


async def _pending_order(db_session, user) -> Order:
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(account)
    await db_session.flush()
    strategy = Strategy(
        user_id=user.id,
        name="metric-failure",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.pending,
    )
    db_session.add(order)
    await db_session.commit()
    return order


@pytest.mark.asyncio
async def test_gauge_failure_does_not_report_a_completed_cancel_as_failed(
    client, mock_clerk_auth, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H1 회귀 — mmap 할당 실패가 **확정된 취소**를 실패로 보고하면 안 된다."""
    import src.trading.router as router_module

    order = await _pending_order(db_session, mock_clerk_auth)

    calls: list[str] = []

    def _explode() -> None:
        calls.append("dec")
        raise OSError("mmap allocation failed")

    monkeypatch.setattr(router_module.qb_active_orders, "dec", _explode)

    response = await client.post(f"/api/v1/orders/{order.id}/cancel")

    assert calls == ["dec"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert response.status_code == 200, response.text
    assert response.json()["state"] == OrderState.cancelled.value

    await db_session.refresh(order)
    assert order.state == OrderState.cancelled, "취소는 계측 이전에 이미 확정됐다"
