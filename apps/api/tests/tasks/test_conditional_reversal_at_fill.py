# BL-562 — 조건부 진입의 반전 크기를 **체결 후 실제 포지션**으로 재판정한다.
"""등재 시점 counter(`qb_live_conditional_reversal_total`)는 트리거 전 드리프트에 낡는다.

이 파일이 지키는 계약은 셋이다:
  1. 판정이 **체결 후 포지션**에서 나온다 (등재 시점 값이 아니다).
  2. 증명하지 못하면 **버킷에 넣지 않는다** — 못 잰 **사유별** `unmeasured_*` 로 가른다.
  3. 예약은 **조건부 진입에만** 걸리고, 발화 경로에 편향이 없다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.models import OrderSide, OrderState
from src.trading.providers import PositionInfo
from src.trading.services.conditional_entry_planner import (
    build_conditional_entry_key,
    build_market_converted_entry_key,
)

_FILLED_AT = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
# 조건부 주문이 거래소로 나간 시각. 트리거(체결)는 이보다 나중이다.
_SUBMITTED_AT = datetime(2026, 7, 31, 11, 30, 0, tzinfo=UTC)
_BAR_TIME = datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC)


def _position(
    side: str = "long",
    size: Decimal = Decimal("8"),
    *,
    created_at: datetime | None = _FILLED_AT,
) -> PositionInfo:
    return PositionInfo(size=size, side=side, created_at=created_at)  # type: ignore[arg-type]


def _bucket(
    *,
    position: PositionInfo | None,
    entry_side: OrderSide = OrderSide.buy,
    filled_quantity: Decimal | None = Decimal("16"),
    submitted_at: datetime | None = _SUBMITTED_AT,
) -> str:
    from src.tasks.trading import _reversal_bucket_at_fill

    return _reversal_bucket_at_fill(
        position=position,
        entry_side=entry_side,
        filled_quantity=filled_quantity,
        submitted_at=submitted_at,
    )


# ── 판정 — 체결 후 포지션이 근거다 ──────────────────────────────────────────


def test_reversal_bucket_comes_from_the_position_left_after_the_fill() -> None:
    """★핵심 오라클 — 등재 시점 테스트와 **같은 숫자**로 같은 답이 나와야 한다.

    보유 short 8 에 buy 16 이 체결되면 남는 포지션은 long 8 이다. 16 / 8 = 2 -> `2x`.
    등재 시점 counter 의 오라클(`test_live_signal_conditional_reconcile.py` 의
    `test_reversal_placement_is_counted_with_its_overshoot_bucket`)과 동일하게 2의
    거듭제곱만 쓴다 — 정답 `2x` 는 오답 `1x`/`4x`/`8x+` 와 서로 다르다.
    """
    assert _bucket(position=_position("long", Decimal("8"))) == "2x"


def test_bigger_overshoot_lands_in_a_bigger_bucket() -> None:
    """32 / 8 = 4 -> `4x`. 버킷 경계가 실제로 비율을 따라간다(상수 고정이 아니다)."""
    assert _bucket(position=_position("long", Decimal("8")), filled_quantity=Decimal("32")) == "4x"


def test_flat_entry_is_measured_and_reported_as_not_a_reversal() -> None:
    """대조군 — flat 진입은 체결 수량 == 남은 포지션이라 반전이 아니다.

    ★"안 셈" 이 아니라 `not_reversal` 로 **센다**. 재고 나서 아니었던 것과 아예 못 잰
    것을 같은 침묵에 묻으면 BL-563 이 고친 그 오분류가 그대로 재현된다.
    """
    assert (
        _bucket(position=_position("long", Decimal("16")), filled_quantity=Decimal("16"))
        == "not_reversal"
    )


def test_adding_to_an_existing_same_side_position_is_not_a_reversal() -> None:
    """같은 방향 증량 — 남은 포지션(24)이 체결 수량(16)보다 크다."""
    assert _bucket(position=_position("long", Decimal("24"))) == "not_reversal"


def test_short_reversal_uses_the_short_side_as_the_expected_direction() -> None:
    """sell 체결이면 남는 포지션은 short 다 — 방향 매핑이 뒤집히면 전부 `unmeasured` 가 된다."""
    assert _bucket(position=_position("short", Decimal("8")), entry_side=OrderSide.sell) == "2x"


# ── 증명 못하면 버킷에 넣지 않는다 ──────────────────────────────────────────


def test_missing_position_is_unmeasured_not_a_guess() -> None:
    """포지션이 안 보인다 = "체결 미전파" 와 "체결 직후 청산" 을 구분할 수 없다."""
    assert _bucket(position=None) == "unmeasured_no_position"


def test_position_on_the_opposite_side_means_we_read_a_pre_fill_snapshot() -> None:
    """★반전의 stale read 가 전부 여기로 떨어진다.

    buy 16 이 체결됐는데 포지션이 아직 short 면 그것은 우리 체결 **전** 스냅샷이다.
    이 분기가 없으면 반전을 `not_reversal` 로 오분류할 길이 열린다.
    """
    assert _bucket(position=_position("short", Decimal("8"))) == "unmeasured_pre_fill_read"


def test_reversal_candidate_without_a_creation_timestamp_is_unmeasured() -> None:
    """생성 시각이 없으면 "우리 체결이 만든 포지션" 임을 증명할 수 없다."""
    assert (
        _bucket(position=_position("long", Decimal("8"), created_at=None)) == "unmeasured_no_anchor"
    )


def test_missing_submitted_at_is_unmeasured() -> None:
    """기준 시각이 없으면 하한 자체가 없다."""
    assert (
        _bucket(position=_position("long", Decimal("8")), submitted_at=None)
        == "unmeasured_no_anchor"
    )


def test_stale_read_of_an_add_is_not_promoted_to_a_reversal() -> None:
    """★유일한 위양성 경로를 막는 가드.

    보유 long 8 에 buy 16 을 더하는 **증량**인데 포지션 조회가 체결 전 스냅샷(long 8)을
    주면 8 < 16 이라 반전처럼 보인다. 진짜 반전이면 포지션이 우리 **주문이 나간 뒤**에
    생성되므로, 발주보다 먼저 있던 포지션은 이 체결이 만든 것일 수 없다.
    """
    old = _SUBMITTED_AT - timedelta(hours=3)
    assert (
        _bucket(position=_position("long", Decimal("8"), created_at=old))
        == "unmeasured_position_predates_order"
    )


def test_clock_skew_within_tolerance_still_counts() -> None:
    """거래소 시계가 조금 이르다고 진짜 반전을 버리면 계측이 조용히 0 이 된다."""
    from src.tasks.trading import _REVERSAL_MEASURE_CREATED_TOLERANCE

    skewed = _SUBMITTED_AT - _REVERSAL_MEASURE_CREATED_TOLERANCE + timedelta(milliseconds=1)
    assert _bucket(position=_position("long", Decimal("8"), created_at=skewed)) == "2x"


def test_late_discovery_by_a_fallback_path_still_measures_the_reversal() -> None:
    """★★codex 2차 MAJOR[3] 회귀 — fallback 체결이 구조적으로 전부 탈락하면 안 된다.

    watchdog/reconciler/janitor/sweep 은 실제 체결보다 **한참 뒤**의 `now` 를
    `Order.filled_at` 에 넣는다. 판정 기준을 `filled_at` 으로 잡으면 15분 뒤 발견된
    진짜 반전이 `created_at < filled_at - 2s` 로 **전부** 탈락해, 새 축은 "옮겼다" 는
    착시만 남는다.

    여기서는 실제 체결(=포지션 생성)이 발주 30분 뒤에 일어나고 관측은 그보다 15분 더
    늦은 상황을 만든다. 기준이 `submitted_at` 이면 관측 지연과 무관하게 `2x` 가 나온다.
    """
    real_fill = _SUBMITTED_AT + timedelta(minutes=30)
    assert _bucket(position=_position("long", Decimal("8"), created_at=real_fill)) == "2x"


def test_unknown_filled_quantity_is_unmeasured() -> None:
    assert (
        _bucket(position=_position("long", Decimal("8")), filled_quantity=None)
        == "unmeasured_no_fill_qty"
    )


def test_zero_sized_position_is_unmeasured_not_a_division_error() -> None:
    """0 나눗셈으로 죽으면 체결 후처리가 통째로 깨진다."""
    assert _bucket(position=_position("long", Decimal("0"))) == "unmeasured_no_position"


# ── 예약 — 조건부 진입에만, 체결당 1회 ──────────────────────────────────────


def _enqueue(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    from src.tasks import trading as t

    calls: list[dict] = []
    monkeypatch.setattr(
        t.measure_conditional_reversal_task, "apply_async", lambda **kw: calls.append(kw)
    )
    return calls


def _order(key: str | None, *, reduce_only: bool = False) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), reduce_only=reduce_only, idempotency_key=key)


def test_enqueue_fires_for_conditional_and_market_converted_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """등재 시점 counter 의 모집단(`cond` + `condmkt`)과 같아야 두 축을 나란히 읽는다."""
    from src.tasks import trading as t

    calls = _enqueue(monkeypatch)
    session_id = uuid4()
    cond = build_conditional_entry_key(session_id, "entry", _BAR_TIME, Decimal("100"), Decimal("1"))
    condmkt = build_market_converted_entry_key(
        session_id, "entry", _BAR_TIME, Decimal("100"), Decimal("1")
    )

    t._enqueue_conditional_reversal_measure(_order(cond))
    t._enqueue_conditional_reversal_measure(_order(condmkt))

    assert len(calls) == 2
    assert calls[0]["countdown"] == t._REVERSAL_MEASURE_COUNTDOWN


def test_enqueue_skips_reduce_only_and_non_conditional_orders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """청산 leg·수동/웹훅 주문·시장가 진입은 반전 계측 대상이 아니다."""
    from src.tasks import trading as t

    calls = _enqueue(monkeypatch)
    cond = build_conditional_entry_key(uuid4(), "entry", _BAR_TIME, Decimal("100"), Decimal("1"))

    t._enqueue_conditional_reversal_measure(_order(cond, reduce_only=True))
    t._enqueue_conditional_reversal_measure(_order(None))
    t._enqueue_conditional_reversal_measure(_order("manual-order-key"))
    # 시장가 진입 key — 조건부가 아니라 즉시 체결이라 등재 시점 counter 의 모집단이 아니다.
    t._enqueue_conditional_reversal_measure(_order(f"live:{uuid4()}:2026-07-31T11:00:00:0:entry:e"))

    assert calls == []


# ── 태스크 본체 — 실제로 counter 를 올리는가 ────────────────────────────────


def _sessionmaker(order: SimpleNamespace | None, account: object | None) -> object:
    """`async with sm() as session` 을 흉내낸다."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=account)

    class _CM:
        async def __aenter__(self) -> AsyncMock:
            return session

        async def __aexit__(self, *exc: object) -> bool:
            return False

    def sm() -> _CM:
        return _CM()

    return sm


@pytest.mark.asyncio
async def test_task_body_counts_the_bucket_it_measured(monkeypatch: pytest.MonkeyPatch) -> None:
    """★배선 검증 — 순수 함수가 아니라 **프로덕션 경로**가 counter 를 올리는지 본다."""
    from src.tasks import trading as t

    buckets: list[str] = []
    monkeypatch.setattr(t, "_count_reversal_at_fill", buckets.append)

    order_id = uuid4()
    order = SimpleNamespace(
        id=order_id,
        state=OrderState.filled,
        reduce_only=False,
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        filled_at=_FILLED_AT,
        submitted_at=_SUBMITTED_AT,
        filled_quantity=Decimal("16"),
        quantity=Decimal("16"),
    )
    monkeypatch.setattr(
        t,
        "OrderRepository",
        lambda session: SimpleNamespace(get_by_id=AsyncMock(return_value=order)),
    )
    monkeypatch.setattr(
        t,
        "EncryptionService",
        lambda keys: SimpleNamespace(decrypt=lambda blob: "plaintext"),
    )
    account = SimpleNamespace(
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
        passphrase_encrypted=None,
        mode="demo",
    )
    provider = AsyncMock()
    provider.fetch_position = AsyncMock(return_value=_position("long", Decimal("8")))
    # ★[BL-733] 이후 confirmed reversal 은 refresh 를 **예약**한다. stub 하지 않으면 이 단위
    #   테스트가 **실 Redis broker 에 의존**하게 되고, 브로커가 없으면 무관하게 red 가 난다
    #   (2026-08-15 codex Standards-4 — 실제로 그렇게 실패했다).
    monkeypatch.setattr(t.refresh_closed_pnl_task, "apply_async", lambda *a, **kw: None)

    result = await t._measure_conditional_reversal_with_session(
        order_id, _sessionmaker(order, account), provider=provider
    )

    assert result["bucket"] == "2x"
    assert buckets == ["2x"]
    provider.fetch_position.assert_awaited_once()


@pytest.mark.asyncio
async def test_task_body_does_not_count_orders_that_are_not_filled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★체결되지 않은 행을 세면 "체결당 1회" 계약이 깨진다 (예약 후 취소된 경우)."""
    from src.tasks import trading as t

    buckets: list[str] = []
    monkeypatch.setattr(t, "_count_reversal_at_fill", buckets.append)

    order_id = uuid4()
    order = SimpleNamespace(id=order_id, state=OrderState.cancelled, reduce_only=False)
    monkeypatch.setattr(
        t,
        "OrderRepository",
        lambda session: SimpleNamespace(get_by_id=AsyncMock(return_value=order)),
    )

    result = await t._measure_conditional_reversal_with_session(
        order_id, _sessionmaker(order, None)
    )

    assert result["skipped"] == "not_filled"
    assert buckets == []


@pytest.mark.asyncio
async def test_exchange_failure_is_unmeasured_not_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    """거래소 장애로 계측이 죽은 것과 반전이 없는 것은 다른 사실이다."""
    from src.tasks import trading as t
    from src.trading.exceptions import ProviderError

    buckets: list[str] = []
    monkeypatch.setattr(t, "_count_reversal_at_fill", buckets.append)

    order_id = uuid4()
    order = SimpleNamespace(
        id=order_id,
        state=OrderState.filled,
        reduce_only=False,
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        filled_at=_FILLED_AT,
        submitted_at=_SUBMITTED_AT,
        filled_quantity=Decimal("16"),
        quantity=Decimal("16"),
    )
    monkeypatch.setattr(
        t,
        "OrderRepository",
        lambda session: SimpleNamespace(get_by_id=AsyncMock(return_value=order)),
    )
    monkeypatch.setattr(
        t, "EncryptionService", lambda keys: SimpleNamespace(decrypt=lambda blob: "plaintext")
    )
    account = SimpleNamespace(
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
        passphrase_encrypted=None,
        mode="demo",
    )
    provider = AsyncMock()
    provider.fetch_position = AsyncMock(side_effect=ProviderError("network down"))

    result = await t._measure_conditional_reversal_with_session(
        order_id, _sessionmaker(order, account), provider=provider
    )

    assert result["bucket"] == "unmeasured_error"
    assert buckets == ["unmeasured_error"]


# ---------------------------------------------------------------------------
# [BL-733] — 반전 leg 의 확정 손익 조회 예약
#
# 반전에는 `reduce_only` 를 걸 수 없으므로(ADR-032) 종전 게이트로는 이 경로에 못 들어왔고,
# 확정 손익이 5분 beat 스윕까지 늦었다. kill-switch 는 그 창 동안 손실을 과소평가한다.
# ★계약은 **셋 다** 다 — 열리는 것 하나, 안 열리는 것 둘.
# ---------------------------------------------------------------------------


def _reversal_order(order_id):
    return SimpleNamespace(
        id=order_id,
        state=OrderState.filled,
        reduce_only=False,
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        filled_at=_FILLED_AT,
        submitted_at=_SUBMITTED_AT,
        filled_quantity=Decimal("16"),
        quantity=Decimal("16"),
    )


def _install_measure_stubs(monkeypatch, order, account):
    from src.tasks import trading as t

    monkeypatch.setattr(t, "_count_reversal_at_fill", lambda bucket: None)
    monkeypatch.setattr(
        t,
        "OrderRepository",
        lambda session: SimpleNamespace(get_by_id=AsyncMock(return_value=order)),
    )
    monkeypatch.setattr(
        t, "EncryptionService", lambda keys: SimpleNamespace(decrypt=lambda blob: "plaintext")
    )
    scheduled: list[dict] = []
    monkeypatch.setattr(
        t.refresh_closed_pnl_task,
        "apply_async",
        lambda *a, **kw: scheduled.append(kw) or None,
    )
    return scheduled


@pytest.mark.asyncio
async def test_confirmed_reversal_schedules_the_closed_pnl_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1 — 반전이 **증명되면** 확정 손익 조회를 예약한다 (5분 스윕을 기다리지 않는다)."""
    from src.tasks import trading as t

    order_id = uuid4()
    order = _reversal_order(order_id)
    account = SimpleNamespace(
        api_key_encrypted=b"k", api_secret_encrypted=b"s", passphrase_encrypted=None, mode="demo"
    )
    scheduled = _install_measure_stubs(monkeypatch, order, account)

    provider = AsyncMock()
    # 체결 16 인데 남은 포지션 8 = 반전(2x 오버슛).
    provider.fetch_position = AsyncMock(return_value=_position("long", Decimal("8")))

    result = await t._measure_conditional_reversal_with_session(
        order_id, _sessionmaker(order, account), provider=provider
    )

    assert result["bucket"] == "2x"
    assert len(scheduled) == 1
    # ★`reversal=True` 가 실제로 실려야 실행측 게이트가 열린다. 예약 사실만 재면
    #   플래그를 빼먹는 회귀를 못 잡는다.
    assert scheduled[0]["kwargs"] == {"reversal": True}


@pytest.mark.asyncio
async def test_plain_entry_does_not_schedule_a_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2 — 순수 entry 는 예약하지 않는다 (거짓 운영자 알림 0).

    ★이것이 「필터만 지우면 더 나빠진다」의 본체다. 정상 선물 entry 는 `closed-pnl` 원장에
    대응 행이 없어 `transient` 4회 재시도 뒤 `_alert_closed_pnl_unbackfilled` 를 낸다.
    """
    from src.tasks import trading as t

    order_id = uuid4()
    order = _reversal_order(order_id)
    account = SimpleNamespace(
        api_key_encrypted=b"k", api_secret_encrypted=b"s", passphrase_encrypted=None, mode="demo"
    )
    scheduled = _install_measure_stubs(monkeypatch, order, account)

    provider = AsyncMock()
    # 체결 16, 포지션 16 = 반전이 아니다(증량이거나 flat 진입).
    provider.fetch_position = AsyncMock(return_value=_position("long", Decimal("16")))

    result = await t._measure_conditional_reversal_with_session(
        order_id, _sessionmaker(order, account), provider=provider
    )

    assert result["bucket"] == "not_reversal"
    assert scheduled == []


@pytest.mark.asyncio
async def test_unmeasured_does_not_schedule_and_is_left_to_the_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-3 — 못 잰 leg 는 예약하지 않는다 (fail-safe · 5분 스윕이 받는다).

    ★모름을 예약으로 접으면 그 leg 가 순수 entry 였을 때 거짓 알림이 난다. 늦는 쪽이
    틀리는 쪽보다 낫다 — 스윕은 원장 기준이라 결국 맞춘다.
    """
    from src.tasks import trading as t

    order_id = uuid4()
    order = _reversal_order(order_id)
    account = SimpleNamespace(
        api_key_encrypted=b"k", api_secret_encrypted=b"s", passphrase_encrypted=None, mode="demo"
    )
    scheduled = _install_measure_stubs(monkeypatch, order, account)

    provider = AsyncMock()
    provider.fetch_position = AsyncMock(return_value=None)  # 포지션을 못 읽었다

    result = await t._measure_conditional_reversal_with_session(
        order_id, _sessionmaker(order, account), provider=provider
    )

    assert result["bucket"] == "unmeasured_no_position"
    assert scheduled == []


def test_confirmed_reversal_predicate_is_not_a_hardcoded_label_list() -> None:
    """★술어가 **「알려진 둘이 아닌 것」**으로 판정하는지 본다.

    오버슛 라벨은 `live_signal._reversal_overshoot_bucket` 이 정하고 늘어날 수 있다.
    라벨 목록을 베껴 두면 새 버킷이 조용히 예약에서 빠진다 — 그 회귀를 이 케이스가 잡는다.
    """
    from src.tasks.trading import _is_confirmed_reversal

    assert _is_confirmed_reversal("2x") is True
    assert _is_confirmed_reversal("8x+") is True
    assert _is_confirmed_reversal("99x-not-yet-invented") is True  # 미래 라벨도 반전이다
    assert _is_confirmed_reversal("not_reversal") is False
    for unmeasured in (
        "unmeasured_no_fill_qty",
        "unmeasured_no_position",
        "unmeasured_pre_fill_read",
        "unmeasured_no_anchor",
        "unmeasured_position_predates_order",
        "unmeasured_error",
    ):
        assert _is_confirmed_reversal(unmeasured) is False
