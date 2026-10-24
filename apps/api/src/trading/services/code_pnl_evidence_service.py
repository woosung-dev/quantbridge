"""코드 청산의 관측 증거·손익 CAS를 같은 트랜잭션으로 확정한다."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from src.trading.providers import CodeClosedPnlRead
from src.trading.repositories.order_repository import OrderRepository


@dataclass(frozen=True, slots=True)
class CodePnlObservation:
    order_id: UUID
    read: CodeClosedPnlRead
    observed_at: datetime
    mode: Literal["initial", "resync"] = "initial"


@dataclass(frozen=True, slots=True)
class CodePnlApplyResult:
    applied: int
    already_synced: int
    resynced: int
    pending_order_ids: tuple[UUID, ...]


class CodePnlEvidenceService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def apply(self, observations: Sequence[CodePnlObservation]) -> CodePnlApplyResult:
        """원격 조회가 끝난 관측만 받고, 충돌 사실도 금액과 함께 한 번 commit한다."""
        applied = already_synced = resynced = 0
        pending = []
        for observation in observations:
            read = observation.read
            conflict = await self._repo.mark_code_pnl_conflict(
                observation.order_id, read.observed_hashes, invalid=read.conflict
            )
            evidence = read.evidence
            if conflict or evidence is None:
                pending.append(observation.order_id)
            if evidence is None:
                continue
            if observation.mode == "initial":
                rows = await self._repo.backfill_exchange_realized_pnl(
                    observation.order_id,
                    realized_pnl=evidence.pnl,
                    synced_at=observation.observed_at,
                    code_evidence=evidence,
                )
                if rows == 1:
                    applied += 1
                else:
                    already_synced += 1
            elif (
                await self._repo.resync_exchange_realized_pnl(
                    observation.order_id,
                    realized_pnl=evidence.pnl,
                    synced_at=observation.observed_at,
                    code_evidence=evidence,
                )
                == 1
            ):
                resynced += 1
        await self._repo.commit()
        return CodePnlApplyResult(applied, already_synced, resynced, tuple(pending))
