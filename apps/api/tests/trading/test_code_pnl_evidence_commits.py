"""코드 손익 관측 interface의 증거 보존과 단일 commit을 검증한다."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.models import Order
from src.trading.providers import CodeClosedPnlRead
from src.trading.services.code_pnl_evidence_service import (
    CodePnlEvidenceService,
    CodePnlObservation,
)
from tests.trading import test_code_closed_pnl_evidence as evidence_tests

prepared = evidence_tests.prepared
exit_order = evidence_tests.exit_order


async def test_initial_evidence_is_committed_once(exit_order, db_session, monkeypatch):
    repo, _live, order, evidence = exit_order
    commit = AsyncMock(wraps=db_session.commit)
    monkeypatch.setattr(db_session, "commit", commit)

    result = await CodePnlEvidenceService(repo).apply(
        [CodePnlObservation(order.id, CodeClosedPnlRead(evidence), datetime.now(UTC))]
    )

    assert (result.applied, result.already_synced, result.resynced) == (1, 0, 0)
    assert result.pending_order_ids == ()
    commit.assert_awaited_once()
    await db_session.refresh(order)
    assert order.realized_pnl == evidence.pnl
    assert order.risk_context["code_pnl_evidence"]["raw_hash"] == evidence.raw_hash

    commit.reset_mock()
    repeated = await CodePnlEvidenceService(repo).apply(
        [CodePnlObservation(order.id, CodeClosedPnlRead(evidence), datetime.now(UTC))]
    )
    assert (repeated.applied, repeated.already_synced, repeated.resynced) == (0, 1, 0)
    commit.assert_awaited_once()


@pytest.mark.parametrize("conflict", [False, True])
async def test_pending_observation_does_not_discard_other_evidence(
    exit_order, db_session, monkeypatch, conflict
):
    repo, _live, pending_order, evidence = exit_order
    accepted = Order(
        **{
            **pending_order.model_dump(),
            "id": uuid4(),
            "exchange_order_id": "accepted-exit",
        }
    )
    db_session.add(accepted)
    await repo.commit()
    accepted_evidence = replace(evidence, order_id="accepted-exit")
    commit = AsyncMock(wraps=db_session.commit)
    monkeypatch.setattr(db_session, "commit", commit)

    result = await CodePnlEvidenceService(repo).apply(
        [
            CodePnlObservation(
                pending_order.id,
                CodeClosedPnlRead(observed_hashes=(evidence.raw_hash,), conflict=conflict),
                datetime.now(UTC),
            ),
            CodePnlObservation(
                accepted.id, CodeClosedPnlRead(accepted_evidence), datetime.now(UTC)
            ),
        ]
    )

    assert (result.applied, result.already_synced, result.resynced) == (1, 0, 0)
    assert result.pending_order_ids == (pending_order.id,)
    commit.assert_awaited_once()
    await db_session.refresh(pending_order)
    await db_session.refresh(accepted)
    assert pending_order.realized_pnl is None and accepted.realized_pnl == evidence.pnl
    assert bool(pending_order.risk_context.get("pnl_evidence_conflict")) is conflict


async def test_resync_updates_only_changed_amount_and_commits_once(
    exit_order, db_session, monkeypatch
):
    repo, _live, order, evidence = exit_order
    original_time = datetime.now(UTC) - timedelta(hours=1)
    order.realized_pnl, order.realized_pnl_synced_at = Decimal("99"), original_time
    await repo.save(order)
    await repo.commit()
    commit = AsyncMock(wraps=db_session.commit)
    monkeypatch.setattr(db_session, "commit", commit)
    observation = CodePnlObservation(
        order.id, CodeClosedPnlRead(evidence), datetime.now(UTC), "resync"
    )

    result = await CodePnlEvidenceService(repo).apply([observation])

    assert (result.applied, result.already_synced, result.resynced) == (0, 0, 1)
    commit.assert_awaited_once()
    await db_session.refresh(order)
    assert order.realized_pnl == evidence.pnl and order.realized_pnl_synced_at > original_time
    commit.reset_mock()
    repeated = await CodePnlEvidenceService(repo).apply([observation])
    assert (repeated.applied, repeated.already_synced, repeated.resynced) == (0, 0, 0)
    commit.assert_awaited_once()


async def test_commit_failure_does_not_report_applied_evidence(exit_order, db_session, monkeypatch):
    repo, _live, order, evidence = exit_order
    commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    monkeypatch.setattr(db_session, "commit", commit)

    with pytest.raises(RuntimeError, match="commit failed"):
        await CodePnlEvidenceService(repo).apply(
            [CodePnlObservation(order.id, CodeClosedPnlRead(evidence), datetime.now(UTC))]
        )

    commit.assert_awaited_once()
