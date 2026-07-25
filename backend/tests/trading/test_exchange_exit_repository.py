# 거래소 청산 원장 모델과 리포지터리의 DB 불요 계약을 검증한다

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import Index
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import ExchangeExit, ExitAttribution, ExitClassification
from src.trading.repositories.exchange_exit_repository import ExchangeExitRepository


def test_compute_row_hash_is_deterministic_and_changes_with_source_field() -> None:
    row_hash = ExchangeExit.compute_row_hash(
        "order-1", "100", "101", "2", "3", "4", "5", "6"
    )

    assert row_hash == ExchangeExit.compute_row_hash(
        "order-1", "100", "101", "2", "3", "4", "5", "6"
    )
    assert row_hash != ExchangeExit.compute_row_hash(
        "order-1", "100", "101", "2", "3", "4", "5", "7"
    )


def test_compute_row_hash_normalizes_none_as_empty_string() -> None:
    assert ExchangeExit.compute_row_hash(
        "order-1", None, "", None, "", None, "", None
    ) == ExchangeExit.compute_row_hash("order-1", "", "", "", "", "", "", "")


@pytest.mark.asyncio
async def test_upsert_rows_skips_database_for_empty_input() -> None:
    session_mock = AsyncMock(spec=AsyncSession)
    repository = ExchangeExitRepository(cast(AsyncSession, session_mock))

    assert await repository.upsert_rows([]) == []
    session_mock.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_aggregate_closed_pnl_skips_database_for_empty_order_ids() -> None:
    session_mock = AsyncMock(spec=AsyncSession)
    repository = ExchangeExitRepository(cast(AsyncSession, session_mock))

    assert await repository.aggregate_closed_pnl(uuid4(), []) == {}
    session_mock.execute.assert_not_awaited()


def test_exchange_exit_row_hash_unique_index_contract() -> None:
    index = next(
        item
        for item in ExchangeExit.__table_args__
        if isinstance(item, Index) and item.name == "uq_exchange_exits_row"
    )

    assert index.unique is True
    assert tuple(column.name for column in index.columns) == (
        "exchange_account_id",
        "row_hash",
    )


def test_exit_classification_and_attribution_cardinality_contract() -> None:
    assert {member.value for member in ExitClassification} == {
        "ours",
        "bracket_tp",
        "bracket_sl",
        "trailing",
        "liquidation",
        "external_manual",
        "unknown",
    }
    assert {member.value for member in ExitAttribution} == {"exact", "inferred", "none"}
