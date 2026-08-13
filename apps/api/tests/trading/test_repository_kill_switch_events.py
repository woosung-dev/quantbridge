"""KillSwitchEventRepository — spec §2.2 trigger_type별 매칭 규칙."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from uuid import uuid4

from src.trading.models import KillSwitchEvent, KillSwitchTriggerType


async def test_get_active_returns_none_when_no_events(db_session, strategy):
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
    repo = KillSwitchEventRepository(db_session)
    assert await repo.get_active(strategy_id=strategy.id, account_id=uuid4()) is None


async def test_get_active_matches_cumulative_loss_by_strategy(db_session, strategy):
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository

    repo = KillSwitchEventRepository(db_session)
    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15.0"),
        threshold=Decimal("10.0"),
    )
    await repo.save(event)
    await repo.commit()

    # 동일 strategy 매칭 → hit
    active = await repo.get_active(strategy_id=strategy.id, account_id=uuid4())
    assert active is not None
    assert active.trigger_type == KillSwitchTriggerType.cumulative_loss


async def test_get_active_matches_daily_loss_by_account(db_session, user):
    from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository

    account = ExchangeAccount(
        user_id=user.id, exchange=ExchangeName.bybit, mode=ExchangeMode.demo,
        api_key_encrypted=b"k", api_secret_encrypted=b"s",
    )
    db_session.add(account)
    await db_session.flush()

    repo = KillSwitchEventRepository(db_session)
    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.daily_loss,
        exchange_account_id=account.id,
        trigger_value=Decimal("600"),
        threshold=Decimal("500"),
    )
    await repo.save(event)
    await repo.commit()

    active = await repo.get_active(strategy_id=uuid4(), account_id=account.id)
    assert active is not None
    assert active.trigger_type == KillSwitchTriggerType.daily_loss


async def test_get_active_skips_resolved(db_session, strategy):
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository

    repo = KillSwitchEventRepository(db_session)
    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15"), threshold=Decimal("10"),
        resolved_at=datetime.now(UTC),
    )
    await repo.save(event)
    await repo.commit()

    active = await repo.get_active(strategy_id=strategy.id, account_id=uuid4())
    assert active is None


async def test_resolve_event_sets_resolved_at(db_session, strategy):
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository

    repo = KillSwitchEventRepository(db_session)
    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15"), threshold=Decimal("10"),
    )
    saved = await repo.save(event)
    await repo.commit()

    rowcount = await repo.resolve(saved.id, note="manual unlock")
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.resolved_at is not None
    assert fetched.resolution_note == "manual unlock"


async def test_list_recent_returns_ordered(db_session, strategy):
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository

    repo = KillSwitchEventRepository(db_session)
    for threshold in [Decimal("10"), Decimal("20"), Decimal("30")]:
        await repo.save(KillSwitchEvent(
            trigger_type=KillSwitchTriggerType.cumulative_loss,
            strategy_id=strategy.id,
            trigger_value=threshold + 1, threshold=threshold,
        ))
    await repo.commit()

    recent = await repo.list_recent(limit=10, offset=0)
    assert len(recent) >= 3
    # 최신이 먼저
    for a, b in pairwise(recent):
        assert a.triggered_at >= b.triggered_at


async def test_resolve_truncates_long_note(db_session, strategy):
    """T9 review I2: resolution_note > 500 chars must be pre-truncated (matches T8 defensive pattern)."""
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository

    repo = KillSwitchEventRepository(db_session)
    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15"), threshold=Decimal("10"),
    )
    saved = await repo.save(event)
    await repo.commit()

    # 600-char note → must be truncated to 500 at repository layer
    long_note = "x" * 600
    rowcount = await repo.resolve(saved.id, note=long_note)
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.resolution_note is not None
    assert len(fetched.resolution_note) == 500
    assert fetched.resolution_note == "x" * 500
