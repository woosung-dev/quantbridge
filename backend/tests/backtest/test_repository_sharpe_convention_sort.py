# [BL-462] Sharpe 정렬이 등급(degenerate·구 행)과 척도(일간/월간)를 구분하는지 검증.
"""정렬 키 `(등급 ASC, 정규화값 order방향)` 의 회귀망.

여기서 재는 것은 **순서**뿐이다. 저장된 `sharpe_ratio` 값과 응답 payload 는 종전 그대로여야
하고, 그것은 `test_payload_sharpe_ratio_is_not_normalized` 가 따로 잡는다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import Numeric, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.engine.metrics import (
    SHARPE_CONVENTION_DAILY,
    SHARPE_CONVENTION_MONTHLY,
    SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
    SHARPE_CONVENTION_UNAVAILABLE,
)
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.strategy.models import ParseStatus, PineVersion, Strategy

_BASE_TS = datetime(2024, 1, 1, tzinfo=UTC)


def _metrics(value: str, convention: str | None) -> dict[str, Any]:
    """metrics JSONB 한 벌.

    ★`convention is None` 이면 **키를 넣지 않는다.** `{"sharpe_convention": None}` 과
    키 부재는 JSONB 에서 다른 것이고, `serializers.metrics_to_jsonb:160` 이 None 필드의
    키를 생략하므로 구 행에는 키 자체가 없다 — 그게 등급 1 의 실제 모습이다.
    """
    metrics: dict[str, Any] = {
        "total_return": "0.1",
        "max_drawdown": "-0.1",
        "sharpe_ratio": value,
        "num_trades": 3,
    }
    if convention is not None:
        metrics["sharpe_convention"] = convention
    return metrics


async def _seed_rows(
    session: AsyncSession,
    rows: list[tuple[str, dict[str, Any] | None]],
    *,
    user_id: UUID | None = None,
) -> tuple[UUID, dict[str, Backtest]]:
    """(이름, metrics) 목록 → 같은 유저의 백테스트 여러 벌. created_at 은 삽입 순서."""
    if user_id is None:
        user = User(
            id=uuid4(),
            clerk_user_id=f"user_{uuid4().hex[:8]}",
            email=f"{uuid4().hex[:8]}@ex.com",
        )
        session.add(user)
        await session.flush()
        user_id = user.id

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="T",
        pine_source="//@version=5\nstrategy('T')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()

    created: dict[str, Backtest] = {}
    for index, (name, metrics) in enumerate(rows, start=1):
        record = Backtest(
            id=uuid4(),
            user_id=user_id,
            strategy_id=strategy.id,
            symbol=name.upper()[:12],
            timeframe="1h",
            period_start=_BASE_TS,
            period_end=_BASE_TS + timedelta(days=1),
            initial_capital=Decimal("1000"),
            status=BacktestStatus.COMPLETED,
            metrics=metrics,
            equity_curve=[["2024-01-01T00:00:00Z", "1000"]],
            created_at=_BASE_TS + timedelta(minutes=index),
        )
        session.add(record)
        created[name] = record
    await session.flush()
    return user_id, created


async def _ordered_names(
    session: AsyncSession,
    user_id: UUID,
    created: dict[str, Backtest],
    *,
    order: str,
) -> list[str]:
    rows, _ = await BacktestRepository(session).list_by_user(
        user_id, limit=50, offset=0, order_by="sharpe_ratio", order=order
    )
    by_id = {record.id: name for name, record in created.items()}
    return [by_id[row.id] for row in rows]


# --- 양성 대조: 파산 계좌가 정직한 -0.3 위에 오지 않는다 ------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["desc", "asc"])
async def test_bankrupt_account_never_outranks_honest_loss(
    db_session: AsyncSession, order: str
) -> None:
    """degenerate(값 0)는 `order` 와 무관하게 -0.3 아래다.

    등급을 `order` 에 딸려 뒤집으면 `asc` 에서 파산 계좌가 먼저 나온다 — 「모르는 것」은
    「가장 나쁜 것」이 아니므로 그건 틀린 답이다.
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("bankrupt", _metrics("0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY)),
            ("honest", _metrics("-0.3", SHARPE_CONVENTION_MONTHLY)),
        ],
    )
    db_session.expunge_all()

    assert await _ordered_names(db_session, user_id, created, order=order) == [
        "honest",
        "bankrupt",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["desc", "asc"])
async def test_grade_layers_are_stacked_before_value(db_session: AsyncSession, order: str) -> None:
    """등급 0 → 1 → 2 순서가 값보다 먼저다.

    구 행(`legacy`)은 척도 미상이라 raw 99 를 들고도 등급 0 위로 못 올라간다.
    `unavailable` 도 `unavailable_nonpositive_equity` 와 같은 등급 2 다.
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("comparable_low", _metrics("-0.3", SHARPE_CONVENTION_MONTHLY)),
            ("comparable_high", _metrics("0.5", SHARPE_CONVENTION_MONTHLY)),
            ("legacy", _metrics("99", None)),
            ("flat", _metrics("0", SHARPE_CONVENTION_UNAVAILABLE)),
        ],
    )
    db_session.expunge_all()

    expected = (
        ["comparable_high", "comparable_low"]
        if order == "desc"
        else [
            "comparable_low",
            "comparable_high",
        ]
    )
    assert await _ordered_names(db_session, user_id, created, order=order) == [
        *expected,
        "legacy",
        "flat",
    ]


@pytest.mark.asyncio
async def test_conventions_are_compared_on_one_scale(db_session: AsyncSession) -> None:
    """일간 0.05(×√252 ≈ 0.794) > 월간 0.2(×√12 ≈ 0.693).

    원값끼리 비교하면 0.05 < 0.2 라 순서가 뒤집힌다 — 정규화를 빼면 red 다.
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("monthly", _metrics("0.2", SHARPE_CONVENTION_MONTHLY)),
            ("daily", _metrics("0.05", SHARPE_CONVENTION_DAILY)),
        ],
    )
    db_session.expunge_all()

    assert await _ordered_names(db_session, user_id, created, order="desc") == [
        "daily",
        "monthly",
    ]
    assert await _ordered_names(db_session, user_id, created, order="asc") == [
        "monthly",
        "daily",
    ]


# --- 음성 대조: 섞이지 않은 데이터셋에서는 신·구 정렬이 완전히 같아야 한다 -------------


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["desc", "asc"])
async def test_homogeneous_dataset_matches_legacy_order(
    db_session: AsyncSession, order: str
) -> None:
    """degenerate 0건 · 구 행 0건 · 컨벤션 1종 → 종전 단일 값 정렬과 **동일**.

    기대 순서를 손으로 적지 않고 **종전 SQL 식을 그대로 실행해** 대조한다. 다르면 이
    변경이 무관한 것까지 흔들고 있다는 뜻이다(항진명제 방지).
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("a", _metrics("1.5", SHARPE_CONVENTION_DAILY)),
            ("b", _metrics("-0.2", SHARPE_CONVENTION_DAILY)),
            ("c", _metrics("0.4", SHARPE_CONVENTION_DAILY)),
            ("d", _metrics("0.4", SHARPE_CONVENTION_DAILY)),
        ],
    )
    db_session.expunge_all()

    legacy_expression = Backtest.metrics["sharpe_ratio"].astext.cast(Numeric)  # type: ignore[index]
    legacy_primary = (
        legacy_expression.asc() if order == "asc" else legacy_expression.desc()
    ).nulls_last()
    legacy_rows = await db_session.execute(
        select(Backtest.id)  # type: ignore[arg-type]
        .where(Backtest.user_id == user_id)  # type: ignore[arg-type]
        .order_by(
            legacy_primary,
            Backtest.created_at.desc(),  # type: ignore[attr-defined]
            Backtest.id.desc(),  # type: ignore[attr-defined]
        )
    )
    by_id = {record.id: name for name, record in created.items()}
    legacy_names = [by_id[row_id] for row_id in legacy_rows.scalars().all()]

    assert await _ordered_names(db_session, user_id, created, order=order) == legacy_names


# --- 저장·표시 규약 불변: 정규화는 ORDER BY 안에만 있다 -------------------------------


@pytest.mark.asyncio
async def test_payload_sharpe_ratio_is_not_normalized(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """API 양성 대조 — 순서는 바뀌고 값은 그대로다.

    `metrics.py:109` 의 "연율화하지 않는다" 는 저장·표시 규약이다. 정렬용 √252·√12 가
    응답 payload 로 새면 여기서 red 가 난다.
    """
    user: User = mock_clerk_auth
    _, created = await _seed_rows(
        db_session,
        [
            ("bankrupt", _metrics("0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY)),
            ("honest", _metrics("-0.3", SHARPE_CONVENTION_DAILY)),
        ],
        user_id=user.id,
    )
    await db_session.commit()

    response = await client.get("/api/v1/backtests?order_by=sharpe_ratio&order=desc")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [
        str(created["honest"].id),
        str(created["bankrupt"].id),
    ]
    assert [item["metrics_summary"]["sharpe_ratio"] for item in items] == ["-0.3", "0"]
    assert [item["metrics_summary"]["sharpe_convention"] for item in items] == [
        SHARPE_CONVENTION_DAILY,
        SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
    ]
