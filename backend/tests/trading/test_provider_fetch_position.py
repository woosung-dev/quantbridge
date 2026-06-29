# STEP B — BybitFuturesProvider.fetch_position (stale-position 가드용 현재 포지션 조회).
"""place_trailing_stop 가 체결 후 trailing 부착 전 현재 포지션을 확인(stale/flip/flat 차단).
ccxt fetch_positions([symbol]) → 정규화 PositionInfo(size>0, side) 또는 None(무포지션).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="test-key", api_secret="test-secret")


def _bybit_mock(monkeypatch, positions):
    mock_exchange = MagicMock()
    mock_exchange.fetch_positions = AsyncMock(return_value=positions)
    mock_exchange.close = AsyncMock()
    mock_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_cls)
    return mock_exchange


async def test_fetch_position_long(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(monkeypatch, [{"contracts": 0.001, "side": "long", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None
    assert pos.size == Decimal("0.001")
    assert pos.side == "long"


async def test_fetch_position_none_when_flat(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    # size 0 포지션만 → None.
    _bybit_mock(monkeypatch, [{"contracts": 0.0, "side": "long", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is None


async def test_fetch_position_none_when_empty(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(monkeypatch, [])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is None


async def test_fetch_position_short(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    m = _bybit_mock(monkeypatch, [{"contracts": 0.5, "side": "short", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None and pos.side == "short" and pos.size == Decimal("0.5")
    # linear symbol 정규화 + 정리.
    m.fetch_positions.assert_awaited_once_with(["BTC/USDT:USDT"])
    m.close.assert_awaited()


# BL-372 same-side stale — raw Bybit info.createdTime(ms epoch str, ADD 시 불변) →
# PositionInfo.created_at(aware UTC). reopen 식별 불변식의 입력.
#   ccxt normalized `timestamp` 가 아니라 raw createdTime 사용(G1: 버전별 timestamp 가
#   updatedTime 에서 채워지면 ADD 오탐 — raw createdTime 이 robust).
async def test_fetch_position_maps_created_at_from_info(monkeypatch, credentials):
    from datetime import UTC, datetime

    from src.trading.providers import BybitFuturesProvider

    ms = 1657711949928
    # 의도적으로 top-level timestamp 는 다른 값(updatedTime 류) → raw createdTime 만 써야 함.
    _bybit_mock(
        monkeypatch,
        [
            {
                "contracts": 0.001,
                "side": "long",
                "timestamp": 9999999999999,  # ccxt normalized — 사용하면 안 됨
                "info": {"createdTime": str(ms)},
            }
        ],
    )
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None
    assert pos.created_at == datetime.fromtimestamp(ms / 1000, tz=UTC)  # info.createdTime 출처
    assert pos.created_at.tzinfo is not None  # aware (naive 비교 TypeError 방지)


async def test_fetch_position_created_at_none_when_no_created_time(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    # info.createdTime 결측 → created_at None → 상위 가드가 side-only degrade.
    _bybit_mock(monkeypatch, [{"contracts": 0.001, "side": "long", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None
    assert pos.created_at is None


async def test_fetch_position_created_at_none_when_empty_created_time(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    # Bybit 가 빈 문자열/0 을 줄 수 있음 → None (defensive).
    _bybit_mock(monkeypatch, [{"contracts": 0.001, "side": "long", "info": {"createdTime": ""}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None
    assert pos.created_at is None


# _parse_position_created_at 방어 분기 직접 단위 테스트 (G3 — ms<=0 / except 분기 mutation 커버).
def test_parse_position_created_at_variants():
    from datetime import UTC, datetime

    from src.trading.providers import _parse_position_created_at

    ms = 1657711949928
    # 정상 createdTime
    assert _parse_position_created_at({"info": {"createdTime": str(ms)}}) == datetime.fromtimestamp(
        ms / 1000, tz=UTC
    )
    # createdAt fallback (createdTime 부재 시, ccxt USDC 형태)
    assert _parse_position_created_at({"info": {"createdAt": str(ms)}}) == datetime.fromtimestamp(
        ms / 1000, tz=UTC
    )
    # 결측/빈값/0/음수/비정상 → None (degrade)
    assert _parse_position_created_at({"info": {}}) is None
    assert _parse_position_created_at({}) is None
    assert _parse_position_created_at({"info": {"createdTime": ""}}) is None
    assert _parse_position_created_at({"info": {"createdTime": "0"}}) is None
    assert _parse_position_created_at({"info": {"createdTime": "-5"}}) is None
    assert _parse_position_created_at({"info": {"createdTime": "not-a-number"}}) is None
    assert _parse_position_created_at({"info": {"createdTime": None}}) is None
