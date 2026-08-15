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
            auth_subject=f"user_{uuid4().hex[:8]}",
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


@pytest.mark.asyncio
async def test_annualization_factor_is_a_square_root(db_session: AsyncSession) -> None:
    """계수가 √252/√12 인지를 **선형 252/12 와 갈라놓고** 못 박는다.

    ★codex 적대 리뷰가 잡은 사각지대(2026-08-11). 실측 — 계수를 `Decimal(252)`/`Decimal(12)`
    로 바꿔도 종전 4케이스는 **8 passed 로 초록**이었다. 위 `..._compared_on_one_scale` 은
    두 계수 아래서 답이 같아 판별력이 0 이다.

    일간 0.05 · 월간 0.7 로 두면 갈라진다.
    - √: 0.05×15.87 = 0.794  <  0.7×3.46 = 2.425  → monthly 가 위
    - 선형: 0.05×252 = 12.6  >  0.7×12 = 8.4      → daily 가 위
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("daily", _metrics("0.05", SHARPE_CONVENTION_DAILY)),
            ("monthly", _metrics("0.7", SHARPE_CONVENTION_MONTHLY)),
        ],
    )
    db_session.expunge_all()

    assert await _ordered_names(db_session, user_id, created, order="desc") == [
        "monthly",
        "daily",
    ]


@pytest.mark.asyncio
async def test_json_null_and_unknown_convention_are_unknown_scale(
    db_session: AsyncSession,
) -> None:
    """JSON `null` 과 모르는 문자열도 등급 1 이다 — 척도를 모르는 것은 매한가지다.

    `->>` 는 키 부재와 JSON null 을 둘 다 SQL NULL 로 준다. 모르는 문자열은 `case` 의
    `else_` 로 떨어진다 — 이건 의도한 설계지 사고가 아니므로 못 박아 둔다.
    """
    json_null = _metrics("50", None)
    json_null["sharpe_convention"] = None
    user_id, created = await _seed_rows(
        db_session,
        [
            ("known", _metrics("0.1", SHARPE_CONVENTION_MONTHLY)),
            ("json_null", json_null),
            ("unknown_string", _metrics("40", "tv_weekly_rfr9")),
            ("bankrupt", _metrics("0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY)),
        ],
    )
    db_session.expunge_all()

    assert await _ordered_names(db_session, user_id, created, order="desc") == [
        "known",
        "json_null",
        "unknown_string",
        "bankrupt",
    ]


@pytest.mark.asyncio
async def test_missing_value_sinks_within_its_grade_not_below_it(
    db_session: AsyncSession,
) -> None:
    """`sharpe_ratio` 값이 없는 행은 **컨벤션이 있어도 목록 전체의 맨 뒤**다 (등급 3).

    ★★**이 테스트는 2026-08-11 에 뒤집혔다.** 초판은 「컨벤션이 있으면 등급 0 이고, 값 없는
    행은 **등급 0 의 맨 뒤**이지 목록의 맨 뒤가 아니다」를 못 박았다. 그것이 **회귀**였다 —
    종전 `sharpe DESC NULLS LAST` 는 값 없는 행을 **전체 맨 뒤**에 뒀고, 등급을 컨벤션으로만
    정하면 아직 결과가 없는 실행(QUEUED/RUNNING/FAILED — `list_by_user` 에 status 필터가
    없다)이 **완료된 degenerate 행과 구 행을 앞지른다.** 아무 결과도 없는 실행이 끝난 실행
    위에 오는 것은 사용자에게 거짓말이다. ⇒ `_SHARPE_GRADE_NO_VALUE = 3`.

    ★등급에 `nulls_last()` 를 얹는 변이는 red 가 **안 난다** — `case(...)` 에 `else_` 가
    있어 등급은 NULL 이 될 수 없고 그 변이는 무의미하다(2026-08-11 실측). 이 주석을
    「그것도 잡는다」로 읽지 마라.
    """
    valueless: dict[str, Any] = {
        "total_return": "0.1",
        "max_drawdown": "-0.1",
        "num_trades": 3,
        "sharpe_convention": SHARPE_CONVENTION_DAILY,
    }
    user_id, created = await _seed_rows(
        db_session,
        [
            ("valued", _metrics("0.1", SHARPE_CONVENTION_DAILY)),
            ("valueless", valueless),
            ("legacy", _metrics("99", None)),
            ("degenerate", _metrics("0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY)),
        ],
    )
    db_session.expunge_all()

    # 등급 0 → 1 → 2 → 3. 값 없는 행이 degenerate·구 행보다 **뒤**여야 한다.
    assert await _ordered_names(db_session, user_id, created, order="desc") == [
        "valued",
        "legacy",
        "degenerate",
        "valueless",
    ]
    # ★`order=asc` 에서도 맨 뒤다 — 「값이 없다」는 「가장 나쁘다」가 아니다.
    assert (await _ordered_names(db_session, user_id, created, order="asc"))[-1] == "valueless"


async def test_future_unavailable_convention_is_graded_degenerate_by_prefix(
    db_session: AsyncSession,
) -> None:
    """아직 존재하지 않는 `unavailable_*` 컨벤션도 **degenerate** 로 떨어져야 한다.

    ★왜 필요한가 — 등급 판정이 상수 정확일치**만** 이면, `engine/metrics.py` 에 5번째
    `unavailable_*` 가 추가되는 순간 그 행이 **조용히 등급 1**(척도 미상)로 가고
    **정직한 음수보다 위**에 온다. 그게 [BL-462] 가 없애려던 거짓말의 재발이다.
    ⇒ 접두 규칙(`convention LIKE 'unavailable%'`)을 OR 로 함께 걸었다.

    ★이 테스트는 **접두 규칙 제거 변이를 잡기 위해** 존재한다. 판별력을 얻으려면 구 행
    (등급 1)이 픽스처에 있고 그 **원값이 degenerate 보다 낮아야** 한다 — 2026-08-11 실측에서
    첫 판(정직한 음수 + 미래 degenerate 두 행)은 변이를 **못 잡았다**. 접두 규칙이 없으면
    미래 degenerate 가 등급 2 대신 등급 1 로 가는데, 등급 1 행이 없으면 등급 1 과 등급 2 의
    상대 순서가 관측되지 않아 두 경우가 **같은 순서**를 낸다.

    구 행 원값 -99 · 미래 degenerate 0 으로 두면:
      접두 있음 → 정직(등급0) · 구행(등급1, -99) · 미래deg(등급2, 0)
      접두 없음 → 정직(등급0) · **미래deg(등급1, 0)** · 구행(등급1, -99)   ← 순서가 뒤집힌다
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("honest_negative", _metrics("-0.3", SHARPE_CONVENTION_DAILY)),
            # 등급 1(척도 미상) — 원값을 degenerate 보다 **낮게** 둬서 판별력을 만든다.
            ("legacy_low", _metrics("-99", None)),
            # 오늘 코드에 없는 이름 — 접두 규칙만이 이걸 degenerate 로 본다.
            ("future_degenerate", _metrics("0", "unavailable_flat_equity")),
        ],
    )
    db_session.expunge_all()

    assert await _ordered_names(db_session, user_id, created, order="desc") == [
        "honest_negative",
        "legacy_low",
        "future_degenerate",
    ]


async def test_daily_monthly_crossover_pins_the_annualization_factor(
    db_session: AsyncSession,
) -> None:
    """일간 계수가 √365 임을 **순위로** 못 박는다 — √252 로 되돌리면 red 다.

    ★이 테스트가 없으면 계수를 되돌려도 아무것도 빨개지지 않는다(2026-08-11 실측: 계수만
    √252 로 바꿔도 전건 초록이었고, 로컬 DB 의 실제 3행은 두 계수에서 **순서가 동일**했다).
    순위가 갈리는 구간은 monthly/daily ∈ (√(252/12), √(365/12)) = **(4.583, 5.514)** 뿐이다.

    daily 0.1 · monthly 0.5 ⇒ 비 5.0 (구간 안):
      √365 → daily 0.1×19.1050 = **1.9105** > monthly 0.5×3.4641 = 1.7321   ⇒ daily 가 위
      √252 → daily 0.1×15.8745 = 1.5875  < monthly 1.7321                   ⇒ monthly 가 위
    """
    user_id, created = await _seed_rows(
        db_session,
        [
            ("daily", _metrics("0.1", SHARPE_CONVENTION_DAILY)),
            ("monthly", _metrics("0.5", SHARPE_CONVENTION_MONTHLY)),
        ],
    )
    db_session.expunge_all()

    assert await _ordered_names(db_session, user_id, created, order="desc") == [
        "daily",
        "monthly",
    ]


@pytest.mark.asyncio
async def test_both_degenerate_conventions_sink_below_a_legacy_row(
    db_session: AsyncSession,
) -> None:
    """`unavailable` 과 `unavailable_nonpositive_equity` 는 같은 등급 2 — 구 행보다 아래다."""
    user_id, created = await _seed_rows(
        db_session,
        [
            ("flat", _metrics("0", SHARPE_CONVENTION_UNAVAILABLE)),
            ("bankrupt", _metrics("0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY)),
            ("legacy", _metrics("-999", None)),
        ],
    )
    db_session.expunge_all()

    ordered = await _ordered_names(db_session, user_id, created, order="desc")
    assert ordered[0] == "legacy"  # raw -999 인데도 degenerate 위다
    assert set(ordered[1:]) == {"flat", "bankrupt"}


@pytest.mark.asyncio
async def test_grade_order_survives_pagination(db_session: AsyncSession) -> None:
    """페이지를 잘라 이어붙여도 전체 정렬과 같다 — 등급이 페이지 안에서만 도는 게 아니다."""
    user_id, created = await _seed_rows(
        db_session,
        [
            ("bankrupt", _metrics("0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY)),
            ("legacy", _metrics("99", None)),
            ("low", _metrics("-0.3", SHARPE_CONVENTION_MONTHLY)),
            ("high", _metrics("0.5", SHARPE_CONVENTION_MONTHLY)),
        ],
    )
    db_session.expunge_all()

    repo = BacktestRepository(db_session)
    by_id = {record.id: name for name, record in created.items()}
    paged: list[str] = []
    for offset in (0, 2):
        rows, total = await repo.list_by_user(
            user_id, limit=2, offset=offset, order_by="sharpe_ratio", order="desc"
        )
        assert total == 4
        paged.extend(by_id[row.id] for row in rows)

    assert paged == ["high", "low", "legacy", "bankrupt"]


# --- 음성 대조: 섞이지 않은 데이터셋에서는 신·구 정렬이 완전히 같아야 한다 -------------


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["desc", "asc"])
async def test_homogeneous_dataset_matches_legacy_order(
    db_session: AsyncSession, order: str
) -> None:
    """degenerate 0건 · 구 행 0건 · 컨벤션 1종 → 종전 단일 값 정렬과 **동일**.

    기대 순서를 손으로 적지 않고 **종전 SQL 식을 그대로 실행해** 대조한다. 다르면 이
    변경이 무관한 것까지 흔들고 있다는 뜻이다(항진명제 방지).

    ★★**기수 assert 가 없으면 이 테스트는 픽스처 0행에서 `[] == []` 로 초록이다.**
    2026-08-11 실측 — `_seed_rows` 를 0행으로 강제하니 이 파일의 다른 6건은 전부 red 인데
    이 2건(`desc`/`asc`)만 통과했다. 양변이 **둘 다 쿼리 산출물**이라 빈 입력이 「일치」로
    샌다. 이 레포가 반복해서 밟은 그 함정이 **음성 대조 자신**에서 재발한 자리다
    ([LESSON-101]). ⇒ 아래 `_EXPECTED_ROWS` 하한을 먼저 못 박는다.
    """
    _EXPECTED_ROWS = 4
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

    # ★빈 입력 방벽 — 이 둘이 없으면 `[] == []` 로 초록이 샌다(위 독스트링).
    assert len(legacy_names) == _EXPECTED_ROWS, (
        f"종전 정렬이 {len(legacy_names)}행을 냈다 (기대 {_EXPECTED_ROWS}) — "
        "픽스처가 비었으면 아래 대조는 무증거다"
    )
    actual_names = await _ordered_names(db_session, user_id, created, order=order)
    assert len(actual_names) == _EXPECTED_ROWS, (
        f"신 정렬이 {len(actual_names)}행을 냈다 (기대 {_EXPECTED_ROWS})"
    )
    assert actual_names == legacy_names


# --- 저장·표시 규약 불변: 정규화는 ORDER BY 안에만 있다 -------------------------------


@pytest.mark.asyncio
async def test_payload_sharpe_ratio_is_not_normalized(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user,
) -> None:
    """API 양성 대조 — 순서는 바뀌고 값은 그대로다.

    `metrics.py:109` 의 "연율화하지 않는다" 는 저장·표시 규약이다. 정렬용 √252·√12 가
    응답 payload 로 새면 여기서 red 가 난다.
    """
    user: User = mock_authed_user
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
