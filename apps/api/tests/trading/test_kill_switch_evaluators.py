"""KillSwitch evaluator 단독 검증 — timing 없는 결정적 probe."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


@pytest.fixture
async def strat_account(db_session, user, strategy):
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    return strategy, acc


async def _make_filled_order(db_session, strategy, account, *, pnl: Decimal, filled_at: datetime):
    o = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.filled,
        realized_pnl=pnl,
        filled_at=filled_at,
    )
    db_session.add(o)
    await db_session.flush()
    return o


async def test_cumulative_loss_evaluator_not_gated_when_below_threshold(db_session, strat_account):
    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-50"), filled_at=datetime.now(UTC)
    )

    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),
    )
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert result.gated is False


async def test_cumulative_loss_evaluator_gated_when_exceeds(db_session, strat_account):
    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    # 누적 손실 -$1,500 / capital $10,000 = 15% > threshold 10%
    await _make_filled_order(
        db_session,
        strategy,
        account,
        pnl=Decimal("-1500"),
        filled_at=datetime.now(UTC),
    )

    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),
    )
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert result.gated is True
    assert result.trigger_type == "cumulative_loss"
    assert result.trigger_value == Decimal("15.00")
    assert result.threshold == Decimal("10")


async def test_daily_loss_evaluator_sums_today_only(db_session, strat_account):
    """UTC 당일 realized PnL 합만 집계 — 어제 주문은 포함 안 됨."""
    from src.trading.kill_switch import DailyLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)

    # 어제 -$1000 (당일 집계에서 제외)
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-1000"), filled_at=yesterday
    )
    # 오늘 -$400 (< threshold $500)
    await _make_filled_order(db_session, strategy, account, pnl=Decimal("-400"), filled_at=now)

    ev = DailyLossEvaluator(OrderRepository(db_session), threshold_usd=Decimal("500"))
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, now))

    assert result.gated is False


async def test_daily_loss_evaluator_gated_when_today_exceeds(db_session, strat_account):
    from src.trading.kill_switch import DailyLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    now = datetime.now(UTC)

    await _make_filled_order(db_session, strategy, account, pnl=Decimal("-300"), filled_at=now)
    await _make_filled_order(db_session, strategy, account, pnl=Decimal("-300"), filled_at=now)

    ev = DailyLossEvaluator(OrderRepository(db_session), threshold_usd=Decimal("500"))
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, now))

    assert result.gated is True
    assert result.trigger_type == "daily_loss"
    assert result.trigger_value == Decimal("-600")
    assert result.threshold == Decimal("500")


# ── Sprint 8+ dynamic capital_base via BalanceProvider ────────────────


class _StubBalanceProvider:
    """BalanceProvider Protocol fake. 생성 시 지정한 값을 그대로 반환."""

    def __init__(self, value: Decimal | None) -> None:
        self._value = value
        self.call_count = 0

    async def fetch_balance_usdt(self, account_id):
        self.call_count += 1
        return self._value


async def test_cumulative_loss_uses_dynamic_capital_when_provider_returns_value(
    db_session, strat_account
):
    """balance_provider가 $5000 반환 → $1000 손실 = 20% > 10% 임계치 → gated.
    (동일 손실을 config $10000로 계산하면 10% = 경계선이라 통과해야 함에 주의)"""
    from decimal import Decimal

    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-1000"), filled_at=datetime.now(UTC)
    )

    provider = _StubBalanceProvider(Decimal("5000"))
    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),  # config fallback
        balance_provider=provider,
    )
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert result.gated is True
    assert result.trigger_value == Decimal("20.00")
    assert provider.call_count == 1


async def test_cumulative_loss_falls_back_to_config_when_provider_returns_none(
    db_session, strat_account
):
    """provider가 None 반환 (fetch 실패) → config fallback 적용. $1000/$10000 = 10% = 경계.
    threshold=10 strict 초과 조건이므로 통과."""
    from decimal import Decimal

    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-1000"), filled_at=datetime.now(UTC)
    )

    provider = _StubBalanceProvider(None)  # fetch 실패
    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),
        balance_provider=provider,
    )
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert result.gated is False  # 10.00 > 10 이 아니므로 통과
    assert provider.call_count == 1


async def test_cumulative_loss_ignores_zero_or_negative_dynamic_capital(db_session, strat_account):
    """동적 capital이 0 이하로 들어오면 fallback (계좌 이관 중 edge case)."""
    from decimal import Decimal

    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-2000"), filled_at=datetime.now(UTC)
    )

    # balance 0 → 나누기 0 방지 + fallback. config 20000 → 10% = 경계 → 통과
    provider = _StubBalanceProvider(Decimal("0"))
    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("20000"),
        balance_provider=provider,
    )
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert result.gated is False  # fallback 20000 사용 → 10% 경계


# ── Sprint 28 Slice 4 (BL-004) — provider exception resilience ────────────


class _RaisingBalanceProvider:
    """ccxt API 실패 / 타임아웃 / 네트워크 단절 시뮬레이션."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.call_count = 0

    async def fetch_balance_usdt(self, account_id):
        self.call_count += 1
        raise self._exc


async def test_cumulative_loss_falls_back_when_provider_raises(
    db_session, strat_account, monkeypatch
):
    """BL-004 Slice 4 — balance_provider 예외 시 swallow + log + config fallback.

    ccxt API 실패 / 네트워크 단절 / Bybit rate limit 등 edge case 방어.
    KillSwitch evaluation 자체는 절대 fail 금지 (capital safety critical path).

    Sprint 30 ε CI fix: caplog 는 다른 test 의 logger 설정 (예: pytest 내부
    LogCaptureHandler 가 prior test 를 거치며 ``logger.disabled=True`` 로 남기는
    경우) 에 영향을 받아 전체 suite 실행 시 records 가 비는 flake. 동일 디렉토리
    ``test_service_exchange_accounts.py::test_fetch_balance_usdt_returns_none_on_provider_error``
    가 이미 동일 사유로 monkeypatch 패턴을 채택. 같은 패턴 적용.
    """
    from decimal import Decimal

    from src.trading import kill_switch as kill_switch_module
    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-1500"), filled_at=datetime.now(UTC)
    )

    # logger.warning 가로채기 — caplog flake 회피
    captured_warnings: list[str] = []

    def capture_warning(msg: str, *args, **kwargs) -> None:
        # logging 표준 동작 재현: %s 포함 raw template 만 검증 → substring match 안전
        captured_warnings.append(msg if not args else msg % args)

    monkeypatch.setattr(kill_switch_module.logger, "warning", capture_warning)

    # config $10000 → $1500 손실 = 15% > 10% 임계 → gated (fallback 동작 검증)
    provider = _RaisingBalanceProvider(RuntimeError("ccxt timeout"))
    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),
        balance_provider=provider,
    )

    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert result.gated is True
    assert result.trigger_value == Decimal("15.00")
    assert provider.call_count == 1
    # 예외 fallback 시 WARNING 로그 1건
    assert any("balance_provider_failed" in m for m in captured_warnings)


async def test_cumulative_loss_provider_called_on_every_trigger(db_session, strat_account):
    """BL-004 ADR-006 결의: KillSwitch trigger 시점 *매번* fetch (Option A).

    cache 0 — 동일 evaluator instance 가 N 회 evaluate 호출 시 N 회 provider 호출.
    Beta path A1 capital safety 우선 (latency +200ms 수용).
    """
    from decimal import Decimal

    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-100"), filled_at=datetime.now(UTC)
    )

    provider = _StubBalanceProvider(Decimal("10000"))
    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("5000"),  # config (used only on provider fail)
        balance_provider=provider,
    )

    # 3회 평가 → provider 도 3회 호출 (cache 없음 검증)
    for _ in range(3):
        await ev.evaluate(EvaluationContext(strategy.id, account.id, datetime.now(UTC)))

    assert provider.call_count == 3


async def test_daily_loss_uses_exchange_backfilled_manual_close_pnl(db_session, strat_account):
    """수동 청산은 생성 시 realized_pnl이 NULL이어도 backfill 뒤 거래소 값으로 한 번 집계한다.

    이는 pine_v2 추정값 대신 확정 closedPnl이 Kill Switch 손실 판단을 바꾸는 의도적 money-path 변경이다.
    """
    from src.trading.kill_switch import DailyLossEvaluator, EvaluationContext
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    now = datetime.now(UTC)
    manual_close = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.filled,
        reduce_only=True,
        exchange_order_id="manual-close-1",
        realized_pnl=None,
        filled_at=now,
    )
    db_session.add(manual_close)
    await db_session.flush()
    repo = OrderRepository(db_session)
    assert (
        await repo.backfill_exchange_realized_pnl(
            manual_close.id, realized_pnl=Decimal("-600"), synced_at=now
        )
        == 1
    )
    await db_session.commit()

    result = await DailyLossEvaluator(repo, threshold_usd=Decimal("500")).evaluate(
        EvaluationContext(strategy.id, account.id, now)
    )
    assert result.gated is True
    # DailyLossEvaluator 는 부호 있는 당일 합계를 그대로 trigger_value 로 돌려준다.
    assert result.trigger_value == Decimal("-600")


# ── [BL-726] rejected 주문의 realized_pnl 은 SUM 에 들어가면 안 된다 ──────────


async def test_evaluators_exclude_rejected_orders_carrying_an_estimated_pnl(
    db_session, strat_account
):
    """[BL-726] 판정 — `state == filled` 필터가 옳다.

    서버 DB 실측에 `rejected` + `reduce_only=true` + `realized_pnl` 채움 46건 / **+55.32
    USDT** 가 있었다. 「값이 채워졌다(=청산으로 봤다)」와 「rejected(=발주 실패)」가 모순으로
    보이지만, `Order.realized_pnl` 은 **생성 시점**(`order_service.py`, `state=pending`)에
    TradingView alert 가 준 **추정치**로 쓰이고, 거래소 확정치를 넣는 유일한 경로
    `backfill_exchange_realized_pnl` 은 `state == filled` 를 요구한다 — 즉 그 값은
    **체결된 적 없는 주문의 추정치**다.

    ★부호가 **+** 라 SUM 에 넣으면 손실이 줄어 보인다. 게이트를 느슨하게 만드는 방향이라
    이 회귀는 「안 들어간다」를 양쪽 evaluator 에서 함께 고정한다.
    """
    from src.trading.kill_switch import (
        CumulativeLossEvaluator,
        DailyLossEvaluator,
        EvaluationContext,
    )
    from src.trading.repositories.order_repository import OrderRepository

    strategy, account = strat_account
    now = datetime.now(UTC)

    # 실현된 손실 −100 (filled).
    await _make_filled_order(db_session, strategy, account, pnl=Decimal("-100"), filled_at=now)

    # 발주가 거부됐지만 생성 시점 추정치 +90 을 그대로 들고 있는 행.
    rejected = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.rejected,
        reduce_only=True,
        realized_pnl=Decimal("90"),
        filled_at=now,
    )
    db_session.add(rejected)
    await db_session.flush()
    await db_session.commit()

    repo = OrderRepository(db_session)

    # ⑴ Strategy 축 — 손실이 −100 그대로여야 한다. +90 이 섞이면 −10 이 되어
    #    문턱 5%(=1,000 중 50)를 못 넘고 게이트가 열린다.
    cumulative = await CumulativeLossEvaluator(
        repo, threshold_percent=Decimal("5"), capital_base=Decimal("1000")
    ).evaluate(EvaluationContext(strategy.id, account.id, now))
    assert cumulative.gated is True
    assert cumulative.trigger_value == Decimal("10.00")  # |−100| / 1000 * 100

    # ⑵ 계정 축 — 당일 합계도 −100 이어야 한다.
    daily = await DailyLossEvaluator(repo, threshold_usd=Decimal("50")).evaluate(
        EvaluationContext(strategy.id, account.id, now)
    )
    assert daily.gated is True
    assert daily.trigger_value == Decimal("-100")
