# 적대 평가가 실증한 결함들의 회귀 가드 — 페이징 축 불일치와 fail-loud 삼킴

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.providers import (
    BybitFuturesProvider,
    Credentials,
    _closed_pnl_snapshot_from_position,
)

# 상수를 피시험 모듈에서 import 하면 값이 8일로 바뀌어도 통과하는 순환 검증이 된다.
# Bybit 문서상 상한을 리터럴로 박아 외부 진실을 도입한다.
SEVEN_DAYS_MS = 604_800_000


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(api_key="test-key", api_secret="test-secret")


def _patch_exchange(monkeypatch: pytest.MonkeyPatch, exchange: MagicMock) -> None:
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))


def _closed_order(order_id: str, *, created_ms: int, updated_ms: int) -> dict[str, object]:
    """며칠 열려 있다가 체결된 브래킷 주문 — createdTime 과 updatedTime 이 크게 벌어진다."""
    return {
        "timestamp": created_ms,
        "info": {
            "orderId": order_id,
            "createType": "CreateByTakeProfit",
            "stopOrderType": "TakeProfit",
            "orderLinkId": "",
            "createdTime": str(created_ms),
            "updatedTime": str(updated_ms),
        },
    }


async def test_closed_order_meta_never_widens_the_window_beyond_the_exchange_limit(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    """커서를 updatedTime 으로 당기면 창이 7일을 넘어 retCode 10001 이 나고 진행이 멈춘다.

    브래킷 TP/SL 은 진입 시 걸어두고 며칠 뒤 체결되므로 updatedTime >= createdTime 이
    크게 벌어진다. 서버 필터(startTime/endTime)와 ccxt filter_by_since_limit 이 모두
    createdTime 축이라 커서도 같은 축이어야 한다.
    """
    start_ms = 10_000_000_000
    end_ms = start_ms + SEVEN_DAYS_MS
    # 창 안에서 생성됐지만 창이 끝난 뒤 체결된 주문 2건.
    page = [
        _closed_order("o-1", created_ms=start_ms + 1_000, updated_ms=end_ms + 500_000),
        _closed_order("o-2", created_ms=start_ms + 2_000, updated_ms=end_ms + 999_000),
    ]
    exchange = MagicMock()
    exchange.fetch_closed_orders = AsyncMock(return_value=page)
    exchange.close = AsyncMock()
    _patch_exchange(monkeypatch, exchange)

    meta = await BybitFuturesProvider().fetch_closed_order_meta(
        credentials, None, start_ms=start_ms, end_ms=end_ms, limit=2
    )

    assert set(meta) == {"o-1", "o-2"}
    untils = [
        call.kwargs["params"]["until"]
        for call in exchange.fetch_closed_orders.await_args_list
    ]
    # 어떤 호출도 거래소 상한을 넘는 창을 보내지 않는다.
    assert all(until - start_ms <= SEVEN_DAYS_MS for until in untils), untils
    # 커서가 앞으로 가면 같은 페이지를 max_pages 만큼 헛돈다.
    assert untils == sorted(untils, reverse=True)
    assert len(untils) == len(set(untils)), f"진행 없는 재조회: {untils}"


async def test_closed_pnl_window_cursor_uses_created_time_axis(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    """closedPnl 페이징도 서버 필터와 같은 createdTime 축으로 당긴다."""
    start_ms = 10_000_000_000
    end_ms = start_ms + SEVEN_DAYS_MS

    def _row(order_id: str, created_ms: int, updated_ms: int) -> dict[str, object]:
        return {
            "info": {
                "orderId": order_id,
                "closedPnl": "-0.01",
                "closedSize": "0.001",
                "avgExitPrice": "64000",
                "symbol": "BTCUSDT",
                "side": "Sell",
                "createdTime": str(created_ms),
                "updatedTime": str(updated_ms),
            }
        }

    full_page = [
        _row("a0", start_ms + 3_000, end_ms + 100_000),
        _row("a1", start_ms + 2_000, end_ms + 200_000),
    ]
    exchange = MagicMock()
    exchange.fetch_positions_history = AsyncMock(side_effect=[full_page, []])
    exchange.close = AsyncMock()
    _patch_exchange(monkeypatch, exchange)

    await BybitFuturesProvider().fetch_closed_pnl_window(
        credentials, None, start_ms=start_ms, end_ms=end_ms, limit=2
    )

    second_until = exchange.fetch_positions_history.await_args_list[1].kwargs["params"]["until"]
    # updatedTime(end_ms+100_000) 이 아니라 createdTime 최솟값 직전이어야 한다.
    assert second_until == start_ms + 2_000 - 1


def test_malformed_existing_field_skips_the_row_instead_of_silently_nulling_it() -> None:
    """closedSize 파싱 실패를 None 으로 삼키면 손익만 합산돼 수량과 모순된 원장 행이 남는다.

    직전 스프린트의 `_decimal_or_none` 공용화가 fail-loud 를 삼킴으로 바꿔 Surface Trust
    회귀를 만든 것과 같은 부류다(§7.3). 기존 3필드는 strict 를 유지한다.
    """
    base = {
        "orderId": "close-1",
        "closedPnl": "-0.04524449",
        "closedSize": "0.001",
        "avgExitPrice": "64144",
        "updatedTime": "1784933322826",
        "symbol": "BTCUSDT",
        "side": "Sell",
    }
    assert _closed_pnl_snapshot_from_position({"info": base}) is not None

    for broken in ("closedSize", "avgExitPrice", "updatedTime"):
        row = dict(base) | {broken: "abc"}
        assert _closed_pnl_snapshot_from_position({"info": row}) is None, broken


def test_new_optional_fields_stay_lenient_so_the_row_survives() -> None:
    """신규 provenance 필드는 부가 정보라 파싱 실패해도 행을 버리지 않는다."""
    row = {
        "orderId": "close-1",
        "closedPnl": "-0.04524449",
        "closedSize": "0.001",
        "avgExitPrice": "64144",
        "updatedTime": "1784933322826",
        "symbol": "BTCUSDT",
        "side": "Sell",
        "avgEntryPrice": "not-a-number",
        "leverage": "6.25",
    }
    snapshot = _closed_pnl_snapshot_from_position({"info": row})
    assert snapshot is not None
    assert snapshot.avg_entry_price is None
    # Bybit UTA 는 소수 레버리지를 낸다. int(str(...)) 로는 조용히 None 이 됐다.
    assert snapshot.leverage == 6
    assert snapshot.closed_pnl == Decimal("-0.04524449")


def test_row_hash_treats_missing_and_empty_field_identically() -> None:
    """거래소가 한 주기엔 빈 문자열을, 다른 주기엔 키를 생략하면 같은 행이 두 번 적재된다.

    그러면 aggregate_closed_pnl 이 두 번 합산해 realized_pnl 이 실제 청산손익의 2배로
    백필되고 kill-switch 가 부풀린 손실로 평가한다. UNIQUE 는 해시가 다르므로 못 막는다.
    """
    from src.trading.models import ExchangeExit

    with_empty = ExchangeExit.compute_row_hash(
        "o-1", "1784933322826", "1784933322826", "0.001", "-0.045", "64118.7", "64144", ""
    )
    with_missing = ExchangeExit.compute_row_hash(
        "o-1", "1784933322826", "1784933322826", "0.001", "-0.045", "64118.7", "64144", None
    )
    assert with_empty == with_missing

    # 값이 실제로 다르면 해시도 달라야 한다.
    other = ExchangeExit.compute_row_hash(
        "o-1", "1784933322826", "1784933322826", "0.002", "-0.045", "64118.7", "64144", None
    )
    assert other != with_missing


def test_row_hash_delimiter_cannot_shift_field_boundaries() -> None:
    """인쇄 가능한 구분자를 쓰면 값 안에 섞여 서로 다른 행이 같은 해시를 얻는다."""
    from src.trading.models import ExchangeExit

    left = ExchangeExit.compute_row_hash("a|b", "c", None, None, None, None, None, None)
    right = ExchangeExit.compute_row_hash("a", "b|c", None, None, None, None, None, None)
    assert left != right


def test_row_hash_requires_an_order_id() -> None:
    """전 필드가 비면 해시가 한 값으로 축퇴해 서로 다른 행이 UNIQUE 에 흡수된다."""
    from src.trading.models import ExchangeExit

    with pytest.raises(ValueError, match="order id"):
        ExchangeExit.compute_row_hash(None, None, None, None, None, None, None, None)
