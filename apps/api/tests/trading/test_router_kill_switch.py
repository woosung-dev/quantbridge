"""KillSwitch REST endpoints E2E (T20).

Uses mock_authed_user fixture from conftest.py for auth bypass.
URLs: /api/v1/kill-switch/events (router has no prefix; main.py adds /api/v1).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_list_kill_switch_events(client, mock_authed_user, db_session):
    """GET /api/v1/kill-switch/events returns events."""
    from decimal import Decimal

    from src.strategy.models import ParseStatus, PineVersion, Strategy
    from src.trading.models import KillSwitchEvent, KillSwitchTriggerType

    user = mock_authed_user

    strategy = Strategy(
        user_id=user.id,
        name="s",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15"),
        threshold=Decimal("10"),
    )
    db_session.add(event)
    await db_session.commit()

    resp = await client.get("/api/v1/kill-switch/events?limit=10")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_resolve_kill_switch(
    client, mock_authed_user, db_session, monkeypatch: pytest.MonkeyPatch
):
    """POST /api/v1/kill-switch/events/{event_id}/resolve resolves the event."""
    from decimal import Decimal

    from src.strategy.models import ParseStatus, PineVersion, Strategy
    from src.trading.models import KillSwitchEvent, KillSwitchTriggerType

    user = mock_authed_user

    strategy = Strategy(
        user_id=user.id,
        name="s",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15"),
        threshold=Decimal("10"),
    )
    db_session.add(event)
    await db_session.commit()
    publisher = AsyncMock()
    monkeypatch.setattr("src.trading.router.publish_realtime", publisher)

    resp = await client.post(
        f"/api/v1/kill-switch/events/{event.id}/resolve",
        json={"note": "manual reset"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resolved_at"] is not None
    publisher.assert_awaited_once_with(
        str(user.id),
        "kill_switch_resolved",
        {"event_id": str(event.id), "trigger_type": "cumulative_loss"},
    )
