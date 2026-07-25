# 청산 원장 계약을 실 DB 로 검증한다 — mock 은 UNIQUE·Decimal·NOT NULL 을 못 지킨다

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.models import (
    ExchangeAccount,
    ExchangeExit,
    ExchangeMode,
    ExchangeName,
    ExitAttribution,
    ExitClassification,
)
from src.trading.repositories.exchange_exit_repository import ExchangeExitRepository

_BASE = datetime(2026, 7, 20, tzinfo=UTC)


async def _make_account(session: AsyncSession) -> ExchangeAccount:
    user = User(
        clerk_user_id=f"exit-ledger-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    session.add(user)
    await session.flush()
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    session.add(account)
    await session.flush()
    return account


def _row(
    account_id: object,
    *,
    order_id: str,
    closed_pnl: str,
    created_at: datetime,
    row_hash: str | None = None,
) -> ExchangeExit:
    return ExchangeExit(
        exchange_account_id=account_id,  # type: ignore[arg-type]
        exchange_order_id=order_id,
        row_hash=row_hash
        or ExchangeExit.compute_row_hash(
            order_id, str(int(created_at.timestamp() * 1000)), None, None, closed_pnl, None, None, None
        ),
        symbol="BTCUSDT",
        side="Sell",
        closed_pnl=Decimal(closed_pnl),
        closed_size=Decimal("0.001"),
        avg_entry_price=Decimal("62846.2"),
        avg_exit_price=Decimal("62734.2"),
        exchange_created_at=created_at,
        exchange_updated_at=created_at,
        classification=ExitClassification.external_manual,
        attribution_confidence=ExitAttribution.none,
        raw={"orderId": order_id, "closedPnl": closed_pnl},
    )


@pytest.mark.asyncio
async def test_upsert_rows_is_idempotent_across_repeated_windows(db_session: AsyncSession) -> None:
    """같은 창을 다시 훑어도 두 번째부터는 새 행이 없다 — 알림 재발화의 종료 조건이다."""
    account = await _make_account(db_session)
    repo = ExchangeExitRepository(db_session)
    rows = [
        _row(account.id, order_id="o-1", closed_pnl="-0.18106922", created_at=_BASE),
        _row(account.id, order_id="o-2", closed_pnl="-0.12145747", created_at=_BASE + timedelta(minutes=15)),
    ]

    first = await repo.upsert_rows(rows)
    assert sorted(first) == sorted(row.row_hash for row in rows)

    second = await repo.upsert_rows(rows)
    assert second == []


@pytest.mark.asyncio
async def test_upsert_rows_rejects_duplicate_row_hash_at_database_level(
    db_session: AsyncSession,
) -> None:
    """멱등성은 애플리케이션 가드가 아니라 DB UNIQUE 가 지킨다."""
    account = await _make_account(db_session)
    repo = ExchangeExitRepository(db_session)
    await repo.upsert_rows([_row(account.id, order_id="o-1", closed_pnl="-1", created_at=_BASE)])
    await db_session.flush()

    duplicate = _row(account.id, order_id="o-1", closed_pnl="-1", created_at=_BASE)
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_aggregate_closed_pnl_sums_split_rows_as_decimal(db_session: AsyncSession) -> None:
    """분할 행 합산이 float 로 새면 머니-패스가 정밀도를 잃는다."""
    account = await _make_account(db_session)
    other = await _make_account(db_session)
    repo = ExchangeExitRepository(db_session)
    await repo.upsert_rows(
        [
            _row(account.id, order_id="split", closed_pnl="-1.50000000", created_at=_BASE),
            _row(
                account.id,
                order_id="split",
                closed_pnl="-2.25000000",
                created_at=_BASE + timedelta(seconds=1),
            ),
            _row(other.id, order_id="split", closed_pnl="-99.00000000", created_at=_BASE),
        ]
    )

    sums = await repo.aggregate_closed_pnl(account.id, ["split"])
    assert sums["split"] == Decimal("-3.75000000")
    assert isinstance(sums["split"], Decimal)
    # 다른 계정의 같은 orderId 가 섞이면 남의 손실이 우리 리스크 게이트로 들어온다.
    assert await repo.aggregate_closed_pnl(account.id, ["split"]) != await repo.aggregate_closed_pnl(
        other.id, ["split"]
    )


@pytest.mark.asyncio
async def test_raw_column_rejects_null_instead_of_storing_json_null(
    db_session: AsyncSession,
) -> None:
    """`Order.webhook_payload` 는 None 이 JSONB 'null' 로 저장돼 IS NULL 술어가 무력해졌다.

    원장의 provenance 는 같은 함정을 반복하면 안 되므로 NOT NULL + none_as_null 로 fail-loud 한다.
    """
    account = await _make_account(db_session)
    row = _row(account.id, order_id="o-1", closed_pnl="-1", created_at=_BASE)
    row.raw = None  # type: ignore[assignment]
    db_session.add(row)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_unique_index_exists_in_the_physical_schema(db_session: AsyncSession) -> None:
    """모델 metadata 가 아니라 실제 DB 에 UNIQUE 가 걸려 있는지 본다."""
    result = await db_session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = 'trading' AND tablename = 'exchange_exits' "
            "AND indexname = 'uq_exchange_exits_row'"
        )
    )
    indexdef = result.scalar_one()
    assert "UNIQUE" in indexdef
    assert "exchange_account_id" in indexdef and "row_hash" in indexdef
