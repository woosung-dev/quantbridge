"""legacy 확정 손익 적용 interface 의 commit 규약을 검증한다(LESSON-019 commit-spy)."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

from src.trading.services.code_pnl_evidence_service import LedgerPnlService

_NOW = datetime(2026, 7, 25, tzinfo=UTC)


def _repo(*, backfill: list[int] | None = None, resync: list[int] | None = None) -> MagicMock:
    """부모 mock 하나에 붙여 repo 호출 **순서**까지 기록한다."""
    repo = MagicMock()
    repo.backfill_exchange_realized_pnl = AsyncMock(side_effect=backfill or [])
    repo.resync_exchange_realized_pnl = AsyncMock(side_effect=resync or [])
    repo.commit = AsyncMock()
    return repo


def _order(exchange_order_id: str | None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), exchange_order_id=exchange_order_id)


async def test_ledger_sums_backfill_and_resync_then_commit_once() -> None:
    won, lost, no_sum, no_id = _order("won"), _order("lost"), _order("no-sum"), _order(None)
    changed, same = _order("changed"), _order("same")
    repo = _repo(backfill=[1, 0], resync=[1, 0])

    result = await LedgerPnlService(repo).apply_ledger_sums(
        [won, lost, no_sum, no_id],
        {"won": Decimal("-1.5"), "lost": Decimal("2")},
        [changed, same],
        {"changed": Decimal("3"), "same": Decimal("4")},
        _NOW,
    )

    assert (result.applied, result.already_synced, result.resynced) == (1, 1, 1)
    # 원장 합계가 없는 주문·거래소 주문번호가 없는 주문은 repo 를 부르지 않는다.
    assert repo.mock_calls == [
        call.backfill_exchange_realized_pnl(won.id, realized_pnl=Decimal("-1.5"), synced_at=_NOW),
        call.backfill_exchange_realized_pnl(lost.id, realized_pnl=Decimal("2"), synced_at=_NOW),
        call.resync_exchange_realized_pnl(changed.id, realized_pnl=Decimal("3"), synced_at=_NOW),
        call.resync_exchange_realized_pnl(same.id, realized_pnl=Decimal("4"), synced_at=_NOW),
        call.commit(),
    ]
    repo.commit.assert_awaited_once()


async def test_ledger_sums_commit_even_when_nothing_to_apply() -> None:
    """대상 0건이어도 commit 1회 — 스윕의 commit 횟수 계약(원장 upsert + legacy = 2)을 지킨다."""
    repo = _repo()

    result = await LedgerPnlService(repo).apply_ledger_sums([], {}, [], {}, _NOW)

    assert (result.applied, result.already_synced, result.resynced) == (0, 0, 0)
    repo.commit.assert_awaited_once()


async def test_single_backfill_commits_only_when_conditional_update_wins() -> None:
    order_id = uuid4()
    repo = _repo(backfill=[1])

    applied = await LedgerPnlService(repo).backfill_order(
        order_id, realized_pnl=Decimal("-4.2"), synced_at=_NOW
    )

    assert applied is True
    assert repo.mock_calls == [
        call.backfill_exchange_realized_pnl(order_id, realized_pnl=Decimal("-4.2"), synced_at=_NOW),
        call.commit(),
    ]


async def test_single_backfill_does_not_commit_when_already_synced() -> None:
    repo = _repo(backfill=[0])

    applied = await LedgerPnlService(repo).backfill_order(
        uuid4(), realized_pnl=Decimal("0"), synced_at=_NOW
    )

    assert applied is False
    repo.backfill_exchange_realized_pnl.assert_awaited_once()
    repo.commit.assert_not_awaited()
