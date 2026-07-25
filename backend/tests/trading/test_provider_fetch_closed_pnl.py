# Bybit closedPnl 원본 문자열 정밀도와 주문별 합산을 검증한다.
"""BybitFuturesProvider closedPnl 조회 회귀 테스트."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="test-key", api_secret="test-secret")


def _bybit_mock(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, object]]) -> MagicMock:
    import ccxt.async_support as ccxt_async

    exchange = MagicMock()
    exchange.fetch_positions_history = AsyncMock(return_value=rows)
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))
    return exchange


def _row(order_id: str, pnl: str, **extra: str) -> dict[str, object]:
    return {
        "info": {
            "orderId": order_id,
            "closedPnl": pnl,
            "closedSize": extra.get("closed_size", "0.001"),
            "avgExitPrice": extra.get("avg_exit_price", "100000.5"),
            "updatedTime": extra.get("updated_at_ms", "1720000000000"),
        }
    }


async def test_fetch_closed_pnl_uses_raw_string_and_linear_symbol(
    monkeypatch: pytest.MonkeyPatch, credentials
) -> None:
    from src.trading.providers import BybitFuturesProvider

    exchange = _bybit_mock(monkeypatch, [_row("close-1", "-0.04524449")])
    snapshot = await BybitFuturesProvider().fetch_closed_pnl(
        credentials, "BTC/USDT", order_id="close-1"
    )

    assert snapshot is not None
    assert snapshot.closed_pnl == Decimal("-0.04524449")
    assert snapshot.closed_pnl != Decimal(float("-0.04524449"))
    exchange.fetch_positions_history.assert_awaited_once_with(["BTC/USDT:USDT"], limit=100)
    exchange.close.assert_awaited_once()


async def test_fetch_closed_pnl_sums_matching_rows(monkeypatch: pytest.MonkeyPatch, credentials) -> None:
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(
        monkeypatch,
        [
            _row("close-1", "-1.000000001", closed_size="0.1"),
            _row("other", "99"),
            _row("close-1", "-2.000000002", closed_size="0.2", avg_exit_price="101"),
        ],
    )
    snapshot = await BybitFuturesProvider().fetch_closed_pnl(
        credentials, "BTC/USDT", order_id="close-1"
    )

    assert snapshot is not None
    assert snapshot.closed_pnl == Decimal("-3.00000000")
    assert snapshot.closed_size == Decimal("0.3")
    assert snapshot.avg_exit_price == Decimal("101")


async def test_fetch_closed_pnl_returns_none_when_no_matching_row(
    monkeypatch: pytest.MonkeyPatch, credentials
) -> None:
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(monkeypatch, [_row("another", "-1")])
    assert (
        await BybitFuturesProvider().fetch_closed_pnl(
            credentials, "BTC/USDT", order_id="missing"
        )
        is None
    )


async def test_fetch_closed_pnl_preserves_zero(monkeypatch: pytest.MonkeyPatch, credentials) -> None:
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(monkeypatch, [_row("close-1", "0")])
    snapshot = await BybitFuturesProvider().fetch_closed_pnl(
        credentials, "BTC/USDT", order_id="close-1"
    )
    assert snapshot is not None and snapshot.closed_pnl == Decimal("0.00000000")


async def test_fetch_closed_pnl_supplies_since_and_until_together(
    monkeypatch: pytest.MonkeyPatch, credentials
) -> None:
    from src.trading.providers import _CLOSED_PNL_LOOKBACK_MS, BybitFuturesProvider

    exchange = _bybit_mock(monkeypatch, [])
    since = datetime(2026, 7, 25, 1, tzinfo=UTC)
    await BybitFuturesProvider().fetch_closed_pnl(
        credentials, "BTC/USDT", order_id="close-1", since=since
    )
    kwargs = exchange.fetch_positions_history.await_args.kwargs
    assert kwargs["since"] == int(since.timestamp() * 1000) - _CLOSED_PNL_LOOKBACK_MS
    assert kwargs["limit"] == 100
    assert isinstance(kwargs["params"]["until"], int)


async def test_fetch_closed_pnl_skips_malformed_row_but_keeps_page(
    monkeypatch: pytest.MonkeyPatch, credentials
) -> None:
    """행 하나가 깨져도 같은 페이지의 우리 주문은 계속 찾아낸다."""
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(
        monkeypatch,
        [
            {"info": {"closedPnl": "-1"}},  # orderId 없음
            {"info": {"orderId": "close-1", "closedPnl": ""}},  # closedPnl 없음
            {"info": "not-a-dict"},
            _row("close-1", "-0.5"),
        ],
    )
    snapshot = await BybitFuturesProvider().fetch_closed_pnl(
        credentials, "BTC/USDT", order_id="close-1"
    )

    assert snapshot is not None
    assert snapshot.closed_pnl == Decimal("-0.50000000")


_LINEAR_MARKET = {
    "id": "BTCUSDT",
    "symbol": "BTC/USDT:USDT",
    "base": "BTC",
    "quote": "USDT",
    "settle": "USDT",
    "baseId": "BTC",
    "quoteId": "USDT",
    "settleId": "USDT",
    "type": "swap",
    "spot": False,
    "swap": True,
    "future": False,
    "option": False,
    "contract": True,
    "linear": True,
    "inverse": False,
    "contractSize": 1.0,
    "active": True,
    "precision": {"amount": 0.001, "price": 0.1},
    "limits": {"amount": {}, "price": {}, "cost": {}, "leverage": {}},
    "taker": 0.00055,
    "maker": 0.0002,
    "info": {},
}


@pytest.mark.parametrize("detection_lag_seconds", [0, 300, 1800])
async def test_fetch_closed_pnl_survives_late_fill_detection(
    monkeypatch: pytest.MonkeyPatch, credentials, detection_lag_seconds: int
) -> None:
    """WS 유실 → reconciler(300s 주기) 가 늦게 fill 을 감지해도 거래소 행을 찾아야 한다.

    회귀 방어 대상: ccxt `fetch_positions_history` 는 응답을 `filter_by_since_limit` 로 한 번 더
    거르고, 비교 기준은 Bybit 행의 `createdTime`(거래소 청산 시각)이다. 우리가 넘기는 since 는
    `filled_at`(감지 시각)이라 lookback 여유가 좁으면 ccxt 가 우리 행을 버려 backfill 이 영구
    실패한다. 이 테스트는 mock 이 아니라 **실제 ccxt 필터**를 통과시켜 그 창을 검증한다.
    """
    import ccxt.async_support as ccxt_async

    from src.trading.providers import BybitFuturesProvider

    created_ms = 1_753_400_000_000
    raw_row = {
        "symbol": "BTCUSDT",
        "orderId": "close-1",
        "closedPnl": "-0.04524449",
        "closedSize": "0.001",
        "qty": "0.001",
        "avgEntryPrice": "64118.7",
        "avgExitPrice": "64144",
        "cumEntryValue": "64.1187",
        "cumExitValue": "64.144",
        "side": "Sell",
        "orderType": "Market",
        "execType": "Trade",
        "leverage": "10",
        "createdTime": str(created_ms),
        "updatedTime": str(created_ms + 6),
    }

    real_bybit = ccxt_async.bybit  # 패치 전 원본 클래스 (재귀 방지)

    def _make_exchange(_config: dict[str, object]):
        exchange = real_bybit({"apiKey": "k", "secret": "s"})
        exchange.set_markets([_LINEAR_MARKET])

        async def _closed_pnl(_params: dict[str, object]) -> dict[str, object]:
            return {"retCode": 0, "result": {"list": [raw_row]}}

        exchange.privateGetV5PositionClosedPnl = _closed_pnl
        return exchange

    monkeypatch.setattr(ccxt_async, "bybit", _make_exchange)

    filled_at = datetime.fromtimestamp(
        (created_ms + detection_lag_seconds * 1000) / 1000, tz=UTC
    )
    snapshot = await BybitFuturesProvider().fetch_closed_pnl(
        credentials, "BTC/USDT", order_id="close-1", since=filled_at
    )

    assert snapshot is not None, (
        f"감지 지연 {detection_lag_seconds}s 에서 ccxt 가 행을 걸러냄 — lookback 창이 좁다"
    )
    assert snapshot.closed_pnl == Decimal("-0.04524449")


async def test_fetch_closed_pnl_wraps_ccxt_error(monkeypatch: pytest.MonkeyPatch, credentials) -> None:
    import ccxt.async_support as ccxt_async

    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    exchange = _bybit_mock(monkeypatch, [])
    exchange.fetch_positions_history.side_effect = ccxt_async.NetworkError("offline")
    with pytest.raises(ProviderError, match="NetworkError: offline"):
        await BybitFuturesProvider().fetch_closed_pnl(
            credentials, "BTC/USDT", order_id="close-1"
        )
    exchange.close.assert_awaited_once()
