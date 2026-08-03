"""거절된 조건부 진입의 시장가 복구 판정을 검증한다.

수리 대상: 거래소가 `110092`/`110093` 으로 거절하면 **그 거절 자체가 "bar 가 트리거를
찍었다" 는 증명**이고, 엔진 시뮬은 반드시 그 진입을 체결한다(재생 오라클 4/4 확인).
그런데 오늘은 아무것도 복구하지 않아 엔진만 전진하고 세션이 `direction` 발산으로 죽는다.

복구는 PR #493 이 이미 정의한 **시장가 전환** 그대로다 — 새 정책이 아니라 이미 있는
전환을 "거래소가 돌파를 확인해 준 뒤" 에 집행하는 것뿐이다. 그래서 #493/BL-589 이 세운
안전장치를 **전부 그대로 통과해야 한다**(이중 진입 억제 · 돌파 해소 재확인 · 돌파폭 캡).

★억제(M4)는 `idempotency_key` LIKE 질의에 걸려 있어 **실제 DB 로만 검증된다.** 손으로
조립한 상태는 양방향으로 거짓말한다(2026-08-03 실측 교훈) — 그래서 이 파일은 mock repo 가
아니라 `db_session` 을 쓴다. 거래소 호출과 발주만 대역을 세운다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings as app_settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.tasks import conditional_entry_recovery as recovery_module
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.services.conditional_entry_planner import (
    build_conditional_entry_key,
    build_market_converted_entry_key,
)

_SHORT_BREACH = (  # 2026-08-03 소크를 죽인 실응답 (order 48c9cdc9)
    'provider_failure: InvalidOrder: bybit {"retCode":110093,"retMsg":"expect Falling, '
    'but trigger_price[637236000] >= current[636988000]??LastPrice","result":{},'
    '"retExtInfo":{},"time":1785772368783}'
)
_LONG_BREACH = (  # 2026-07-31 실응답 (order ca5dfee4)
    'provider_failure: InvalidOrder: bybit {"retCode":110092,"retMsg":"expect Rising, '
    'but trigger_price[627343000] <= current[627366000]??LastPrice","result":{},'
    '"retExtInfo":{},"time":1785513269000}'
)
_REDUCE_ONLY = (
    'provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"current position '
    'is zero, cannot fix reduce-only order qty","result":{},"retExtInfo":{},'
    '"time":1785035422319}'
)

_TRIGGER = Decimal("63723.6")
_QTY = Decimal("0.058")


# ★**시각을 모듈 상수로 박지 마라 — import 시점과 실행 시점이 다르다.**
# 두 번 데였다:
#   (1) 고정 상수(2026-08-03 15:51)로 두니 억제 창(`since = bar_time - 2*interval`,
#       `live_signal.py:1447`)이 **벽시계가 흐르는 것만으로** 뒤집혔다(codex G1).
#   (2) 그래서 `now - 1분` 으로 바꿨는데, 그 `now` 는 **모듈 import 시점**이라
#       6분짜리 전체 스위트에서는 실행 시점에 이미 낡아 만료 가드(1 interval)에 걸렸다.
#       파일 단독 실행은 green, 전체 스위트는 red — **격리 실행이 거짓말을 했다.**
# ⇒ 시각은 전부 **fixture 안에서**(= 실행 시점) 만든다. 모듈 최상단에는 두지 않는다.
def _fresh_bar_time() -> datetime:
    """이 테스트가 **실행되는 시점** 기준의 직전 마감 bar."""
    return datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=1)


# 라이브 세션은 이 셋이 필수다(`StrategySettings` — leverage/margin_mode/position_size_pct).
# 빈 dict 는 `validate_strategy_settings` 에서 ValidationError 라 주문이 아예 안 나간다.
_LIVE_SETTINGS: dict[str, object] = {
    "leverage": 10,
    "margin_mode": "cross",
    "position_size_pct": 1.0,
}


class _NoopEngine:
    async def dispose(self) -> None:
        return None


def _fake_create_worker_engine_and_sm(db_session: AsyncSession):
    @asynccontextmanager
    async def _context():
        yield db_session

    class _SessionMaker:
        def __call__(self):
            return _context()

    return lambda: (_NoopEngine(), _SessionMaker())


@pytest.fixture
async def recovery_env(db_session: AsyncSession):
    """User / Strategy / Account / 활성 LiveSignalSession 을 실제로 심는다."""
    crypto = EncryptionService(app_settings.trading_encryption_keys)
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@recovery.local",
    )
    strategy = Strategy(
        user_id=user.id,
        name="breach-recovery",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=dict(_LIVE_SETTINGS),
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("key"),
        api_secret_encrypted=crypto.encrypt("secret"),
        label="breach-recovery",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(strategy)
    await db_session.flush()
    db_session.add(account)
    await db_session.flush()
    live = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=True,
        equity_baseline_usdt=Decimal("190419.28986309"),
    )
    db_session.add(live)
    await db_session.flush()

    bar_time = _fresh_bar_time()

    def _cond_key(session_id=None) -> str:
        key = build_conditional_entry_key(
            session_id or live.id, "PivRevSE", bar_time, _TRIGGER, _QTY
        )
        assert key is not None
        return key

    async def _rejected_order(
        *,
        error_message: str = _SHORT_BREACH,
        side: OrderSide = OrderSide.sell,
        trigger_direction: int = 2,
        state: OrderState = OrderState.rejected,
        idempotency_key: str | None = None,
        trigger_price: Decimal | None = _TRIGGER,
    ) -> Order:
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=side,
            type=OrderType.market,
            quantity=_QTY,
            state=state,
            trigger_price=trigger_price,
            trigger_direction=trigger_direction,
            trigger_by="LastPrice",
            reduce_only=False,
            error_message=error_message,
            idempotency_key=idempotency_key or _cond_key(),
            created_at=datetime.now(UTC),
        )
        db_session.add(order)
        await db_session.flush()
        return order

    async def _existing_converted(created_at: datetime) -> Order:
        key = build_market_converted_entry_key(live.id, "PivRevSE", bar_time, _TRIGGER, _QTY)
        assert key is not None
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=_QTY,
            state=OrderState.submitted,
            reduce_only=False,
            idempotency_key=key,
            created_at=created_at,
        )
        db_session.add(order)
        await db_session.flush()
        return order

    yield SimpleNamespace(
        live=live,
        bar_time=bar_time,
        strategy=strategy,
        account=account,
        rejected_order=_rejected_order,
        existing_converted=_existing_converted,
        cond_key=_cond_key,
    )

    strategy_id, account_id, user_id = strategy.id, account.id, user.id
    await db_session.rollback()
    await db_session.execute(delete(Order).where(Order.strategy_id == strategy_id))
    await db_session.execute(
        delete(LiveSignalSession).where(LiveSignalSession.strategy_id == strategy_id)
    )
    await db_session.execute(delete(ExchangeAccount).where(ExchangeAccount.id == account_id))
    await db_session.execute(delete(Strategy).where(Strategy.id == strategy_id))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.commit()


def _patch(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession, *, last_price: Decimal | None
) -> MagicMock:
    """거래소 조회와 발주만 대역으로 바꾼다. 억제 질의는 실제 DB 를 탄다."""
    monkeypatch.setattr(
        recovery_module,
        "create_worker_engine_and_sm",
        _fake_create_worker_engine_and_sm(db_session),
    )
    monkeypatch.setattr(
        recovery_module,
        "BybitFuturesProvider",
        lambda: SimpleNamespace(fetch_last_price=AsyncMock(return_value=last_price)),
    )
    execute = AsyncMock()
    monkeypatch.setattr(
        recovery_module, "OrderService", MagicMock(return_value=SimpleNamespace(execute=execute))
    )
    return execute


# --- M1 / M2 정상 — 두 방향 모두 시장가로 복구된다 ------------------------------------


@pytest.mark.asyncio
async def test_short_breach_places_market_entry(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1 — 2026-08-03 소크 사망 케이스. 거래소 현재가가 트리거 아래라 여전히 돌파다."""
    order = await recovery_env.rejected_order()
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_placed"
    execute.assert_awaited_once()
    request = execute.await_args.args[0]
    key = execute.await_args.kwargs["idempotency_key"]
    # 시장가로 나가야 한다 — 트리거를 그대로 다시 보내면 거래소가 또 거절한다.
    assert request.type == OrderType.market
    assert request.trigger_price is None
    assert request.trigger_direction is None
    assert request.trigger_by is None
    # side/수량은 거절된 진입 그대로여야 한다(반전 크기를 바꾸면 다른 결함이 된다).
    assert request.side == OrderSide.sell
    assert request.quantity == _QTY
    assert request.reduce_only is False
    # `condmkt` 네임스페이스여야 억제 질의와 진입 완결성 분해가 이 주문을 알아본다.
    assert ":condmkt:" in key


@pytest.mark.asyncio
async def test_long_breach_places_market_entry(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M2 — 거울 코드 110092. 원장 4건 중 2건이 이쪽이다."""
    order = await recovery_env.rejected_order(
        error_message=_LONG_BREACH, side=OrderSide.buy, trigger_direction=1
    )
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63740.0"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_placed"
    execute.assert_awaited_once()
    assert execute.await_args.args[0].side == OrderSide.buy


# --- M3 엣지 — 돌파가 해소됐으면 쫓아가지 않는다 --------------------------------------


@pytest.mark.asyncio
async def test_breach_reverted_does_not_place(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M3 — 복구 시점에 가격이 트리거 위로 되돌아왔다면 그 진입은 아직 유효하지 않다.

    ★"주문이 안 나갔다" 만 단언하면 **수리 전에도 참**이라 판별력이 0 이다.
    그래서 판정 라벨을 단언한다 — 그 라벨은 수리 전에 존재조차 하지 않는다.
    """
    order = await recovery_env.rejected_order()
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63800.0"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_reverted"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_trigger_equal_to_current_price_is_still_breached(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M3 경계 — 트리거 == 현재가. 거래소도 우리도 등호를 포함해 판정한다.

    실측 근거: 110092 두 건의 간격이 각각 2.20 / 2.30 USDT 로 사실상 동가였다.
    여기서 부등호가 한쪽만 배타적이면 거래소는 거절하는데 우리는 "해소" 로 읽는다.
    """
    order = await recovery_env.rejected_order()
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=_TRIGGER)

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_placed"
    execute.assert_awaited_once()


# --- M4 엣지 — 이미 전환이 나갔으면 두 번 내지 않는다 ---------------------------------


@pytest.mark.asyncio
async def test_recent_market_conversion_suppresses_recovery(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M4 — PR #493 이 세운 이중 진입 억제를 복구도 통과해야 한다.

    억제 질의는 `idempotency_key` LIKE 라 실제 DB 로만 검증된다.
    """
    order = await recovery_env.rejected_order()
    # 억제 창은 `bar_time - 2 * interval` = bar_time - 120초. 그 안쪽.
    await recovery_env.existing_converted(recovery_env.bar_time - timedelta(seconds=30))
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_suppressed"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_old_market_conversion_does_not_suppress(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M4 대칭 — 창(2 interval) 밖의 오래된 전환은 억제하지 않는다.

    이 짝이 없으면 "항상 억제" 라는 구현도 M4 를 통과한다.
    """
    order = await recovery_env.rejected_order()
    # 창(bar_time - 120초) 바깥. ★벽시계가 아니라 **bar 기준** 상대값이라 시간이 흘러도 안 뒤집힌다.
    await recovery_env.existing_converted(recovery_env.bar_time - timedelta(hours=6))
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_placed"
    execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_breach_exceeding_user_cap_is_not_placed(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """복구도 사용자 `max_trigger_breach_pct` 캡을 그대로 존중한다.

    ★캡의 기본값을 새로 만들지 않는다 — 계획 시점 전환과 **같은 설정 하나**만 본다.
    두 경로가 다른 캡을 쓰면 사용자가 건 한도가 경로에 따라 다르게 걸린다.
    """
    recovery_env.strategy.settings = {**_LIVE_SETTINGS, "max_trigger_breach_pct": 0.001}
    db_session.add(recovery_env.strategy)
    order = await recovery_env.rejected_order()
    await db_session.commit()
    # 63698.8 vs 63723.6 = 0.0389% 돌파 → 0.001% 캡 초과
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "breach_capped"
    execute.assert_not_awaited()


# --- 음성 대조 (수리 전에도 green — 판별력 없음, 과민 반응 배제용) ---------------------


@pytest.mark.asyncio
async def test_reference_price_unavailable_does_not_place(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """기준가를 못 읽으면 쫓아가지 않는다 — 스테일 값으로 시장가를 내지 않는다."""
    order = await recovery_env.rejected_order()
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=None)

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "reference_unavailable"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_breach_rejection_is_not_applicable(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """음성 대조 — 110017 은 돌파가 아니다."""
    order = await recovery_env.rejected_order(error_message=_REDUCE_ONLY)
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "not_applicable"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_session_is_not_applicable(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """음성 대조 — 이미 죽은 세션에 주문을 내면 원장에 유령 포지션이 생긴다."""
    order = await recovery_env.rejected_order()
    recovery_env.live.is_active = False
    recovery_env.live.deactivated_at = datetime.now(UTC)
    db_session.add(recovery_env.live)
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "not_applicable"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_not_rejected_is_not_applicable(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """음성 대조 — 살아 있는 주문을 복구하면 이중 진입이다."""
    order = await recovery_env.rejected_order(state=OrderState.submitted)
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "not_applicable"
    execute.assert_not_awaited()


# --- 지연된 복구는 쫓아가지 않는다 (stale entry) --------------------------------------


@pytest.mark.asyncio
async def test_stale_recovery_is_not_placed(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★복구는 **그 bar 안에서만** 유효하다. 늦게 도는 복구는 시장가를 내면 안 된다.

    복구는 거절된 주문의 **과거** side/수량을 그대로 쓴다. 브로커가 밀려 몇 분 뒤에 돌면
    그 사이 엔진 의도와 거래소 순포지션이 바뀌었을 수 있고, 그때 과거 수량으로 시장가를
    내면 반전 크기가 어긋난다(계획기가 `market_orders_in_flight` 일 때 한 tick 미루는 것도
    같은 이유다 — `live_signal.py:928`). `still_breached` 재확인은 **가격이 되돌아온 경우만**
    막지, 같은 방향으로 더 간 경우는 못 막는다.

    ⇒ 거절 시각으로부터 1 interval 을 넘기면 복구하지 않는다.
    """
    order = await recovery_env.rejected_order()
    # 거절이 1 interval(1m = 60초) 보다 오래됐다.
    order.created_at = datetime.now(UTC) - timedelta(seconds=180)
    db_session.add(order)
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_expired"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_fresh_recovery_within_one_interval_is_placed(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """대칭 짝 — 창 안이면 그대로 복구한다. 없으면 "항상 만료" 구현도 위 테스트를 통과한다."""
    order = await recovery_env.rejected_order()
    order.created_at = datetime.now(UTC) - timedelta(seconds=5)
    db_session.add(order)
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_placed"
    execute.assert_awaited_once()


# --- fail-closed — 되짚을 수 없는 입력에 주문을 내지 않는다 ---------------------------


@pytest.mark.asyncio
async def test_unreadable_bar_epoch_is_not_applicable(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`bar_epoch` 가 정수로 안 읽히면 `condmkt` key 를 만들 수 없다.

    ★파서는 `bar_epoch=None` 을 **관용적으로 허용**한다(BL-544 공백 재개가 legacy key 앞에서
    fail-closed 로 떨어지지 않게 하려고). 그래서 파싱 성공을 key 생성 가능으로 읽으면 안 된다.
    되짚지 못할 key 로 발주하면 우리 주문을 영원히 남의 것으로 본다.
    """
    session_id = recovery_env.live.id
    order = await recovery_env.rejected_order(
        idempotency_key=f"live:{session_id}:cond:not-an-epoch:{_TRIGGER}:{_QTY}:PivRevSE"
    )
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "not_applicable"
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_trigger_price_is_not_applicable(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """트리거가 없으면 돌파 부등식을 세울 수 없다 — 추측하지 말고 서라."""
    order = await recovery_env.rejected_order(trigger_price=None)
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "not_applicable"
    execute.assert_not_awaited()


# --- 계측 실패가 흐름을 바꾸면 안 된다 (H8) ------------------------------------------


@pytest.mark.asyncio
async def test_guard_metric_failure_does_not_change_outcome(
    db_session: AsyncSession, recovery_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★이 레포는 계측 예외가 **거절을 집행으로 뒤집은** 전례가 있다(H8).

    새 label 조합은 multiproc 에서 새 mmap 할당이라 `.labels()` 자체가 던질 수 있다.
    그때도 복구 판정과 발주는 그대로여야 한다.
    """
    order = await recovery_env.rejected_order()
    await db_session.commit()
    execute = _patch(monkeypatch, db_session, last_price=Decimal("63698.8"))

    exploding = MagicMock()
    exploding.labels.side_effect = RuntimeError("mmap allocation failed")
    monkeypatch.setattr(recovery_module, "qb_live_conditional_guard_total", exploding)

    result = await recovery_module._async_recover_breached_entry(str(order.id))

    assert result["outcome"] == "recovery_placed"
    execute.assert_awaited_once()


# --- Celery 등록 — 모듈을 직접 import 하는 테스트는 include 누락을 못 잡는다 ----------


def test_recovery_task_is_registered_in_celery_app() -> None:
    """`include` 에서 빠지면 워커가 태스크를 모르고 **프로덕션에서만** 조용히 실패한다.

    ★`celery_app.tasks` 를 보면 **안 된다.** 이 테스트 모듈이 위에서 복구 모듈을 이미
    import 했으므로 데코레이터가 registry 를 채운다 — `include` 를 통째로 지워도 통과한다
    (codex G6 지적, 실제로 지우고 확인함: 1 passed). 워커는 이 모듈을 import 하지 않으므로
    registry 가 아니라 **`include` 설정**이 프로덕션의 진실이다.
    """
    from src.tasks.celery_app import celery_app

    assert "src.tasks.conditional_entry_recovery" in celery_app.conf.include
