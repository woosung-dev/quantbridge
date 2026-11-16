"""거래소가 확정한 closedPnl 을 Order 실현손익에 적용하고 commit 한다.

코드 청산은 관측 증거·손익 CAS를 같은 트랜잭션으로 확정하고(`CodePnlEvidenceService`),
legacy 주문은 closed-pnl 원장 합계·단건 조회 금액을 CAS 로 반영한다(`LedgerPnlService`).
원격 조회·metric·알림은 호출자(task)가 갖는다.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from src.trading.models import Order
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


@dataclass(frozen=True, slots=True)
class LedgerPnlApplyResult:
    applied: int
    already_synced: int
    resynced: int


class LedgerPnlService:
    """legacy 주문의 거래소 확정 손익을 CAS 로 반영한다. 원격 조회는 끝난 뒤 받는다."""

    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def apply_ledger_sums(
        self,
        unsynced_orders: Sequence[Order],
        unsynced_sums: Mapping[str, Decimal],
        synced_orders: Sequence[Order],
        synced_sums: Mapping[str, Decimal],
        synced_at: datetime,
    ) -> LedgerPnlApplyResult:
        """원장 합계로 미동기화 주문은 백필, 동기화된 주문은 재동기화하고 항상 한 번 commit한다.

        대상이 0건이어도 commit 한다 — 스윕의 commit 횟수 계약이다.
        """
        applied = already_synced = resynced = 0
        for order in unsynced_orders:
            if order.exchange_order_id is None:
                continue
            realized_pnl = unsynced_sums.get(order.exchange_order_id)
            if realized_pnl is None:
                continue
            if (
                await self._repo.backfill_exchange_realized_pnl(
                    order.id, realized_pnl=realized_pnl, synced_at=synced_at
                )
                == 1
            ):
                applied += 1
            else:
                already_synced += 1
        for order in synced_orders:
            if order.exchange_order_id is None:
                continue
            ledger_pnl = synced_sums.get(order.exchange_order_id)
            if ledger_pnl is None:
                continue
            if (
                await self._repo.resync_exchange_realized_pnl(
                    order.id, realized_pnl=ledger_pnl, synced_at=synced_at
                )
                == 1
            ):
                resynced += 1
        await self._repo.commit()
        return LedgerPnlApplyResult(applied, already_synced, resynced)

    async def backfill_order(
        self, order_id: UUID, *, realized_pnl: Decimal, synced_at: datetime
    ) -> bool:
        """단건 조회 금액을 백필한다. 조건부 UPDATE 가 이긴 경우(1행)에만 commit한다."""
        rows = await self._repo.backfill_exchange_realized_pnl(
            order_id, realized_pnl=realized_pnl, synced_at=synced_at
        )
        if rows == 1:
            await self._repo.commit()
            return True
        return False
