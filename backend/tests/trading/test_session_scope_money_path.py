# 세션 스코프 머니-패스 대조군 — 틀린 술어와 맞는 술어가 서로 다른 값을 내도록 실 DB 로 고정한다

"""BL-444 / BL-445 control group.

측정 시점(2026-07-25) 개발 DB 는 orders 0 행이라 소비처 5 곳이 전부 "0 위에서 0"
을 합산했다. `0 → 0` 은 검증이 아니다 — 틀린 술어와 맞는 술어가 같은 답을 내기
때문이다. 그래서 이 파일은 손익을 2 의 거듭제곱 × 서로 다른 소수부로 심어
**어떤 부분집합 합계도 유일**하게 만든다. 틀린 답이 나오면 그 숫자가 어느 술어를
잘못 넣었는지 스스로 지목한다.

고정하는 계약 4 종.

1. BL-445 목격자 — 같은 `(strategy, account)` 위 세션 3 개가 fix 전에는 **동일한**
   커브를 돌려준다.
2. D4 (`filled_at` 반열림) — 늦은 체결 O3 는 자기를 만든 S1 이 아니라 **인접한 S2**
   로 귀속된다. 인접 세션이 없으면 어디에도 안 잡힌다. 수용한 트레이드오프다.
3. D5 (`symbol` 정확 문자열 동등) — 형식이 다른 O11(`"BTCUSDT"`)은 세션 스코프에서
   빠진다. ingress 정규화가 없기 때문이며 이것도 수용한 트레이드오프다.
4. 가드레일 — Site 1 / 2 / 5 는 이번 스프린트 범위 밖이므로 fix 전후 **값이 같아야**
   한다. 세 값을 서로 다르게 배치해, 누가 Site 1 에 계정 필터를 · Site 2 에 전략
   필터를 · Site 5 에 테넌트 필터를 "친절하게" 넣으면 숫자로 드러나게 했다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.kill_switch import (
    CumulativeLossEvaluator,
    DailyLossEvaluator,
    EvaluationContext,
)
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEvent,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.order_repository import OrderRepository, SessionScope

# 두 시각 모두 같은 UTC 일에 둔다 — Site 2 / Site 5 의 일일 창이 전 주문을 덮어야
# 가드레일이 "스코프" 만 검사하고 "날짜" 를 섞지 않는다.
T0 = datetime(2026, 7, 20, 6, 0, tzinfo=UTC)
T2 = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
DAY = date(2026, 7, 20)

BTC = "BTC/USDT"
ETH = "ETH/USDT"
# ingress 정규화가 없어서 TV 웹훅이 실을 수 있는 다른 표기 (D5 가 수용한 구멍).
BTC_UNNORMALIZED = "BTCUSDT"


@dataclass(frozen=True, slots=True)
class _Seed:
    user_id: UUID
    strategy_id: UUID
    other_strategy_id: UUID
    account_id: UUID
    other_account_id: UUID
    session_closed: LiveSignalSession  # S1 — S·A·BTC, [T0, T2), 비활성
    session_active: LiveSignalSession  # S2 — S·A·BTC, [T2, ∞), 활성 (S1 과 정확히 인접)
    session_eth: LiveSignalSession  # S3 — S·A·ETH, [T0, ∞), 활성 (심볼 누출 탐침)
    orders: dict[str, Order]  # "o1".."o11"


async def _seed_money_path(db_session: AsyncSession) -> _Seed:
    """세션 3 개 + 주문 11 건. 손익은 2 의 거듭제곱이라 부분합이 유일하다."""
    user = User(
        clerk_user_id=f"money-path-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    def _strategy(name: str) -> Strategy:
        return Strategy(
            user_id=user.id,
            name=name,
            pine_source="//@version=5\nstrategy('scope')",
            pine_version=PineVersion.v5,
            parse_status=ParseStatus.ok,
        )

    def _account() -> ExchangeAccount:
        return ExchangeAccount(
            user_id=user.id,
            exchange=ExchangeName.bybit,
            mode=ExchangeMode.demo,
            api_key_encrypted=b"k",
            api_secret_encrypted=b"s",
        )

    strategy = _strategy("scope target")
    other_strategy = _strategy("scope other")
    account = _account()
    other_account = _account()
    db_session.add_all([strategy, other_strategy, account, other_account])
    await db_session.flush()

    # S1 은 비활성이라 partial unique(`uq_live_sessions_active_unique`) 가 S2 와
    # 충돌하지 않는다. S3 는 심볼이 달라 활성 두 개가 합법이다 — 이 합법성이 바로
    # 대시보드 §01 KPI 이중 계상의 원인이다.
    session_closed = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=BTC,
        interval=LiveSignalInterval.m5,
        is_active=False,
        created_at=T0,
        deactivated_at=T2,
    )
    session_active = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=BTC,
        interval=LiveSignalInterval.m5,
        created_at=T2,
    )
    session_eth = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=ETH,
        interval=LiveSignalInterval.m5,
        created_at=T0,
    )
    db_session.add_all([session_closed, session_active, session_eth])
    await db_session.flush()

    def _order(
        *,
        pnl: str,
        filled_at: datetime | None,
        symbol: str = BTC,
        state: OrderState = OrderState.filled,
        strategy_id: UUID | None = None,
        account_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> Order:
        return Order(
            strategy_id=strategy_id or strategy.id,
            exchange_account_id=account_id or account.id,
            symbol=symbol,
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=state,
            realized_pnl=Decimal(pnl),
            filled_at=filled_at,
            created_at=created_at or (filled_at or T0),
        )

    o1 = _order(pnl="-1.00000001", filled_at=T0 + timedelta(minutes=1))
    o2 = _order(pnl="-2.00000002", filled_at=T0 + timedelta(minutes=2))
    # 늦은 체결 — S1 이 만들었지만(created 가 S1 창 안) 체결은 S1 종료 뒤다.
    o3 = _order(
        pnl="-4.00000004",
        filled_at=T2 + timedelta(seconds=30),
        created_at=T2 - timedelta(seconds=30),
    )
    o4 = _order(pnl="-8.00000008", filled_at=T2 + timedelta(minutes=1))
    o5 = _order(pnl="-16.00000016", filled_at=T2 + timedelta(minutes=2))
    o6 = _order(pnl="-32.00000032", filled_at=T0 + timedelta(minutes=3), symbol=ETH)
    o7 = _order(pnl="-64.00000064", filled_at=T0 - timedelta(hours=1))
    o8 = _order(
        pnl="-128.00000128",
        filled_at=T2 + timedelta(minutes=3),
        state=OrderState.rejected,
    )
    o9 = _order(
        pnl="-256.00000256",
        filled_at=T0 + timedelta(minutes=4),
        account_id=other_account.id,
    )
    o10 = _order(
        pnl="-512.00000512",
        filled_at=T0 + timedelta(minutes=5),
        strategy_id=other_strategy.id,
    )
    o11 = _order(
        pnl="-1024.00001024",
        filled_at=T0 + timedelta(minutes=6),
        symbol=BTC_UNNORMALIZED,
    )
    db_session.add_all([o1, o2, o3, o4, o5, o6, o7, o8, o9, o10, o11])
    await db_session.flush()

    # 이벤트는 dispatch 경로에서만 생긴다 — O2/O3/O5/O6/O7/O9/O10/O11 은 수동 청산·
    # TV 웹훅·타 스코프라 이벤트가 없다. 그게 BL-444 의 구멍이다.
    db_session.add_all(
        [
            LiveSignalEvent(
                session_id=session_closed.id,
                bar_time=T0,
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="o1",
                qty=Decimal("1"),
                order_id=o1.id,
            ),
            LiveSignalEvent(
                session_id=session_active.id,
                bar_time=T2,
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="o4",
                qty=Decimal("1"),
                order_id=o4.id,
            ),
            LiveSignalEvent(
                session_id=session_active.id,
                bar_time=T2,
                sequence_no=2,
                action="close",
                direction="long",
                trade_id="o8-rejected",
                qty=Decimal("1"),
                order_id=o8.id,
            ),
        ]
    )
    await db_session.flush()

    return _Seed(
        user_id=user.id,
        strategy_id=strategy.id,
        other_strategy_id=other_strategy.id,
        account_id=account.id,
        other_account_id=other_account.id,
        session_closed=session_closed,
        session_active=session_active,
        session_eth=session_eth,
        orders={
            "o1": o1,
            "o2": o2,
            "o3": o3,
            "o4": o4,
            "o5": o5,
            "o6": o6,
            "o7": o7,
            "o8": o8,
            "o9": o9,
            "o10": o10,
            "o11": o11,
        },
    )


# ── Site 3 / Site 4 — 이번 스프린트가 바꾸는 두 소비처 ──────────────────────────


@pytest.mark.asyncio
async def test_site3_now_sees_manual_close_and_webhook_orders(db_session: AsyncSession) -> None:
    """BL-444 — 이벤트가 없는 수동 청산·TV 웹훅 손익이 loss-limit 합계에 들어온다.

    fix 전 event-join 값은 S1 = -1.00000001 (O1 만) · S2 = -8.00000008 (O4 만) ·
    S3 = 0 (이벤트 0 건) 이었다. 세 숫자 전부 바뀐다.
    """
    seed = await _seed_money_path(db_session)
    repo = OrderRepository(db_session)

    # O1(dispatch) + O2(수동 청산, 이벤트 없음). 예전엔 O2 가 통째로 안 보였다.
    assert await repo.sum_filled_realized_pnl_for_session(
        SessionScope.from_live_session(seed.session_closed)
    ) == Decimal("-3.00000003")
    # O3(늦은 체결) + O4(dispatch) + O5(TV 웹훅, 이벤트 없음).
    assert await repo.sum_filled_realized_pnl_for_session(
        SessionScope.from_live_session(seed.session_active)
    ) == Decimal("-28.00000028")
    # 이벤트가 하나도 없는 세션도 이제 자기 심볼 체결(O6)을 본다.
    assert await repo.sum_filled_realized_pnl_for_session(
        SessionScope.from_live_session(seed.session_eth)
    ) == Decimal("-32.00000032")


@pytest.mark.asyncio
async def test_site4_three_sessions_no_longer_share_one_curve(
    db_session: AsyncSession,
) -> None:
    """BL-445 — 같은 (strategy, account) 위 세 세션이 각자 다른 커브를 갖는다.

    fix 전에는 셋 다 -1151.00001151 (8 행) 로 **문자 그대로 같은 행 집합**이었다.
    """
    seed = await _seed_money_path(db_session)
    repo = OrderRepository(db_session)

    curves = {
        name: await repo.list_filled_realized_for_session(SessionScope.from_live_session(sess))
        for name, sess in (
            ("s1", seed.session_closed),
            ("s2", seed.session_active),
            ("s3", seed.session_eth),
        )
    }
    totals = {
        name: sum((Decimal(str(o.realized_pnl)) for o in orders), Decimal("0"))
        for name, orders in curves.items()
    }

    assert totals == {
        "s1": Decimal("-3.00000003"),
        "s2": Decimal("-28.00000028"),
        "s3": Decimal("-32.00000032"),
    }
    assert [len(curves[k]) for k in ("s1", "s2", "s3")] == [2, 3, 1]

    id_sets = [{o.id for o in curves[k]} for k in ("s1", "s2", "s3")]
    assert id_sets[0].isdisjoint(id_sets[1])
    assert id_sets[0].isdisjoint(id_sets[2])
    assert id_sets[1].isdisjoint(id_sets[2])

    # 커브 x 축은 여전히 filled_at ASC 다.
    for orders in curves.values():
        stamps = [o.filled_at for o in orders]
        assert stamps == sorted(stamps)  # type: ignore[type-var]


@pytest.mark.asyncio
async def test_late_fill_lands_in_the_adjacent_session_not_its_own(
    db_session: AsyncSession,
) -> None:
    """D4 계약 — `filled_at` 반열림이라 늦은 체결은 자기를 만든 세션이 아니라 다음 세션 것이다.

    O3 는 S1 창 안에서 발주(`created_at` = T2−30s)됐지만 체결은 S1 종료 뒤(T2+30s)다.
    수용한 트레이드오프이며, 인접 세션이 없었다면 **어느 세션에도 안 잡힌다.**
    """
    seed = await _seed_money_path(db_session)
    repo = OrderRepository(db_session)
    late_fill = seed.orders["o3"]

    s1_ids = {
        o.id
        for o in await repo.list_filled_realized_for_session(
            SessionScope.from_live_session(seed.session_closed)
        )
    }
    s2_ids = {
        o.id
        for o in await repo.list_filled_realized_for_session(
            SessionScope.from_live_session(seed.session_active)
        )
    }

    assert late_fill.created_at < seed.session_closed.deactivated_at  # type: ignore[operator]
    assert late_fill.id not in s1_ids, "상한이 반열림이라 자기 세션에서 빠진다"
    assert late_fill.id in s2_ids, "인접 세션이 흡수한다 — 없으면 영구 미귀속"


@pytest.mark.asyncio
async def test_symbol_mismatch_drops_the_webhook_order_from_every_session(
    db_session: AsyncSession,
) -> None:
    """D5 계약 — ingress 정규화가 없어 표기가 다른 TV 웹훅 주문은 스코프에서 빠진다.

    fix 전에는 심볼 술어가 없어 O11 이 세 세션 모두에 들어갔다. 이제 전부 빠진다.
    반대로 Site 1/2/5 가드레일에는 여전히 잡히므로 "행이 사라진 게 아니라 세션
    스코프 밖으로 나간 것" 임이 숫자로 구분된다.
    """
    seed = await _seed_money_path(db_session)
    repo = OrderRepository(db_session)
    mismatched = seed.orders["o11"]

    assert mismatched.symbol == BTC_UNNORMALIZED
    assert mismatched.symbol != seed.session_closed.symbol
    for sess in (seed.session_closed, seed.session_active, seed.session_eth):
        ids = {
            o.id
            for o in await repo.list_filled_realized_for_session(
                SessionScope.from_live_session(sess)
            )
        }
        assert mismatched.id not in ids


# ── Site 1 / 2 / 5 가드레일 — 이번 스프린트 범위 밖. fix 전후 값이 같아야 한다 ──


@pytest.mark.asyncio
async def test_guardrail_site1_cumulative_stays_strategy_wide_all_time(
    db_session: AsyncSession,
) -> None:
    """Site 1 은 전략 스코프 · 전 기간 그대로다. 계정 필터가 끼면 숫자가 달라진다."""
    seed = await _seed_money_path(db_session)

    # capital_base=100 이면 loss_percent 가 |합계| 와 같은 눈금이 되어 읽기 쉽다.
    evaluator = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("0"),
        capital_base=Decimal("100"),
    )
    result = await evaluator.evaluate(
        EvaluationContext(strategy_id=seed.strategy_id, account_id=seed.account_id, now=T2)
    )

    assert result.gated is True
    # O1..O7 + O11 (계정 A) + O9 (계정 A2) — 계정을 가리지 않는다.
    # 계정 필터가 끼면 1151.00, 심볼 필터가 끼면 383.00 이 나온다.
    assert result.trigger_value == Decimal("1407.00")


@pytest.mark.asyncio
async def test_guardrail_site2_daily_stays_account_wide_across_strategies(
    db_session: AsyncSession,
) -> None:
    """Site 2 는 계정 스코프 · UTC 일 그대로다. 전략 필터가 끼면 숫자가 달라진다."""
    seed = await _seed_money_path(db_session)

    evaluator = DailyLossEvaluator(OrderRepository(db_session), threshold_usd=Decimal("0"))
    result = await evaluator.evaluate(
        EvaluationContext(strategy_id=seed.strategy_id, account_id=seed.account_id, now=T2)
    )

    assert result.gated is True
    # O1..O7 + O11 (전략 S) + O10 (전략 S2) — 전략을 가리지 않는다.
    # 전략 필터가 끼면 -1151.00001151 이 나온다.
    assert result.trigger_value == Decimal("-1663.00001663")


@pytest.mark.asyncio
async def test_guardrail_site5_daily_summary_stays_global(db_session: AsyncSession) -> None:
    """Site 5 는 전 테넌트 전역 그대로다. 계정/전략/유저 필터가 끼면 숫자가 달라진다."""
    await _seed_money_path(db_session)

    total, filled, rejected = await OrderRepository(db_session).get_daily_summary(DAY)

    # 그날 체결된 10 건 전부. O7 도 같은 UTC 일이라 들어온다.
    assert total == Decimal("-1919.00001919")
    assert filled == 10
    assert rejected == 1
