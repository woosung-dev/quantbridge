"""거절 시점 복구 배선 — `trigger_breached` 거절이 조건부 진입 복구를 예약하는지 검증한다.

★이 파일이 잡는 결함: 계획기 가드는 **발주 시각에 옳았는데** 거래소가 ~2초 뒤 자기 시각으로
판정해 `110092`/`110093` 으로 거절한다(2026-08-03 소크 실측: 기준가 > 63723.6 이었고 거래소는
63698.8 로 쟀다). 그 거절은 계상만 되고 **아무것도 복구하지 않는다.** 그런데 엔진 포지션은
`run_live` 시뮬이라 주문을 모르고, 거래소가 "current 가 트리거를 지났다" 고 거절했다는 사실
자체가 **그 bar 가 트리거를 찍었다는 증명**이므로 시뮬은 반드시 체결한다(재생 오라클 4/4).
⇒ 엔진만 전진 → `direction` 발산 2회 연속 → 세션 fail-closed 종료.

여기서는 **배선만** 본다(거절 → 복구 예약). 복구 자체의 판정은
`test_conditional_entry_recovery.py` 가 본다. 층을 합치면 어느 쪽이 깨졌는지 못 가른다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import src.tasks.trading as trading_module
from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, ExchangeName, OrderSide, OrderState, OrderType
from src.trading.services.conditional_entry_planner import (
    build_conditional_entry_key,
    build_market_converted_entry_key,
)

# 원장에서 그대로 뜬 실응답. 문자열을 손으로 짓지 않는다 — retMsg 의 깨진 구분자(`??`)까지
# 실물과 같아야 추출기가 프로덕션에서와 같은 경로를 탄다.
_SHORT_BREACH = (  # 2026-08-03 소크를 죽인 그 응답 (order 48c9cdc9)
    'provider_failure: InvalidOrder: bybit {"retCode":110093,"retMsg":"expect Falling, '
    'but trigger_price[637236000] >= current[636988000]??LastPrice","result":{},'
    '"retExtInfo":{},"time":1785772368783}'
)
_LONG_BREACH = (  # 거울 코드 — 2026-07-31 원장 (order ca5dfee4)
    'provider_failure: InvalidOrder: bybit {"retCode":110092,"retMsg":"expect Rising, '
    'but trigger_price[627343000] <= current[627366000]??LastPrice","result":{},'
    '"retExtInfo":{},"time":1785513269000}'
)
_REDUCE_ONLY = (
    'provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"current position '
    'is zero, cannot fix reduce-only order qty","result":{},"retExtInfo":{},'
    '"time":1785035422319}'
)

_SESSION_ID = uuid4()
_BAR_TIME = datetime(2026, 8, 3, 15, 51, tzinfo=UTC)


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _Crypto:
    def __init__(self, _keys: object) -> None:
        pass

    def decrypt(self, _value: object) -> str:
        return "credential"


def _conditional_key() -> str:
    key = build_conditional_entry_key(
        _SESSION_ID, "PivRevSE", _BAR_TIME, Decimal("63723.6"), Decimal("0.058")
    )
    assert key is not None
    return key


def _converted_key() -> str:
    key = build_market_converted_entry_key(
        _SESSION_ID, "PivRevSE", _BAR_TIME, Decimal("63723.6"), Decimal("0.058")
    )
    assert key is not None
    return key


def _order(idempotency_key: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        exchange_account_id=uuid4(),
        # 2026-08-15 적대 리뷰 P1 — 워커가 소유자 활성을 묻기 위해 읽는다.
        # 프로덕션 `Order.strategy_id` 는 FK `ondelete=RESTRICT` 로 NOT NULL 이다.
        strategy_id=uuid4(),
        state=OrderState.pending,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.058"),
        price=None,
        leverage=10,
        margin_mode="cross",
        reduce_only=False,
        trigger_price=Decimal("63723.6"),
        trigger_by="LastPrice",
        take_profit=None,
        stop_loss=None,
        trigger_direction=2,
        oco_group_id=None,
        trailing_stop=None,
        idempotency_key=idempotency_key,
    )


def _account(order: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=order.exchange_account_id,
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"api-key",
        api_secret_encrypted=b"api-secret",
        passphrase_encrypted=None,
        exchange_uid=None,
    )


async def _reject(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: str,
    idempotency_key: str | None,
    rejected_rows: int = 1,
) -> MagicMock:
    """주어진 거절 응답으로 발주를 태우고, 복구 예약 spy 를 돌려준다.

    `rejected_rows` = `transition_to_rejected` 의 CAS rowcount. 0 이면 **다른 경로가 이미
    terminal 전이를 이긴 것**이라 이 호출자는 승자가 아니다.
    """
    order = _order(idempotency_key)
    account = _account(order)
    session = SimpleNamespace(commit=AsyncMock(), get=AsyncMock(return_value=account))
    repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=order),
        # 2026-08-15 적대 리뷰 P1 — 워커가 발주 직전에 소유자 활성을 다시 묻는다.
        # 이 페이크는 「살아 있는 소유자」를 모형한다(프로덕션에서는 FK 가 행의 존재를 보장한다).
        strategy_owner_is_active=AsyncMock(return_value=True),
        transition_to_submitted=AsyncMock(return_value=1),
        transition_to_rejected=AsyncMock(return_value=rejected_rows),
        attach_exchange_order_id=AsyncMock(),
    )
    provider = SimpleNamespace(create_order=AsyncMock(side_effect=ProviderError(response)))

    monkeypatch.setattr(trading_module, "OrderRepository", MagicMock(return_value=repo))
    monkeypatch.setattr(trading_module, "EncryptionService", _Crypto)
    monkeypatch.setattr(
        trading_module,
        "_provider_from_order_snapshot_or_fallback",
        lambda *_args, **_kwargs: provider,
    )
    monkeypatch.setattr(trading_module, "publish_realtime", AsyncMock())

    # ★**helper 를 spy 로 갈아끼우지 않는다.** 이 레포의 enqueue helper 들은
    #   (`_enqueue_trailing_if_intended` · `_enqueue_conditional_reversal_measure`)
    #   판별을 **helper 안에서** 한다. helper 자체를 mock 으로 덮으면 그 판별이 통째로
    #   미검증이 되고, 음성 대조가 "호출부가 거른다" 는 **없는 계약**을 고정해 버린다.
    #   ⇒ 사슬 맨 끝(태스크 dispatch)에 spy 를 건다. 호출부 → helper 가드 → 예약이
    #   전부 실제 코드다. no-op helper 도 여기서 red 로 잡힌다.
    spy = MagicMock()
    try:
        from src.tasks.conditional_entry_recovery import conditional_entry_recovery_task

        monkeypatch.setattr(conditional_entry_recovery_task, "apply_async", spy)
    except ImportError:
        # 수리 전 — 대상 모듈이 없다. spy 는 영원히 안 불린다 = 의도된 red.
        pass

    result = await trading_module._execute_with_session(
        order.id,
        lambda: _SessionContext(session),  # type: ignore[arg-type]
    )
    assert result["state"] == "rejected"
    return spy


# --- M1/M2 배선: 두 방향 모두 복구가 예약돼야 한다 -------------------------------------


@pytest.mark.asyncio
async def test_short_trigger_breach_enqueues_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """110093(short/Falling) 거절 = 2026-08-03 소크 사망 응답 그 자체."""
    spy = await _reject(monkeypatch, response=_SHORT_BREACH, idempotency_key=_conditional_key())
    spy.assert_called_once()


@pytest.mark.asyncio
async def test_long_trigger_breach_enqueues_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """★110092 거울 코드. 이 클래스는 110093 단독이 아니다 — 원장 4건 중 2건이 110092 다.

    계획기 단위 테스트에 short 돌파 케이스가 아예 없었다(전부 long). 방향 비대칭은 이
    레포가 반복해서 데인 축이라 두 방향을 각각 고정한다.
    """
    spy = await _reject(monkeypatch, response=_LONG_BREACH, idempotency_key=_conditional_key())
    spy.assert_called_once()


# --- 음성 대조: 수리 전에도 green 이라 판별력이 없다. 과민 반응 배제용으로만 센다 -------


@pytest.mark.asyncio
async def test_non_breach_rejection_does_not_enqueue_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 110017 은 돌파가 아니다(포지션 0). 복구 대상이 아니다."""
    spy = await _reject(monkeypatch, response=_REDUCE_ONLY, idempotency_key=_conditional_key())
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_non_live_order_breach_does_not_enqueue_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 웹훅/수동 주문은 엔진 시뮬과 짝이 없어 복구 대상이 아니다."""
    spy = await _reject(monkeypatch, response=_SHORT_BREACH, idempotency_key="webhook-manual-1")
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_market_converted_order_breach_does_not_enqueue_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 이미 시장가 전환된 주문(`condmkt`)을 또 복구하면 재귀가 된다."""
    spy = await _reject(monkeypatch, response=_SHORT_BREACH, idempotency_key=_converted_key())
    spy.assert_not_called()


# --- CAS 승자만 예약한다 ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_cas_loser_does_not_enqueue_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """`transition_to_rejected` 가 0 이면 다른 경로가 이미 이겼다 — 승자만 후처리한다.

    같은 자리의 `qb_active_orders.dec` 도 `rows == 1` 로 막혀 있다(`trading.py:449`).
    패자까지 예약하면 같은 진입에 복구 시장가가 **두 번** 나간다.
    """
    spy = await _reject(
        monkeypatch, response=_SHORT_BREACH, idempotency_key=_conditional_key(), rejected_rows=0
    )
    spy.assert_not_called()


# --- 예약 helper 자체의 계약 (spy 로 가리면 이 부분이 통째로 미검증이 된다) -------------


def test_enqueue_helper_dispatches_the_recovery_task(monkeypatch: pytest.MonkeyPatch) -> None:
    """helper 가 no-op 이거나 인자가 틀려도 위 배선 테스트는 전부 green 이다.

    ★그래서 helper **자신**의 계약을 따로 고정한다 — 실제로 복구 태스크를
    `[str(order.id)]` 로 enqueue 하는가.
    """
    from src.tasks.conditional_entry_recovery import conditional_entry_recovery_task

    order = _order(_conditional_key())
    apply_async = MagicMock()
    monkeypatch.setattr(conditional_entry_recovery_task, "apply_async", apply_async)

    trading_module._enqueue_breach_recovery(order, "trigger_breached")

    apply_async.assert_called_once()
    assert apply_async.call_args.kwargs["args"] == [str(order.id)]
