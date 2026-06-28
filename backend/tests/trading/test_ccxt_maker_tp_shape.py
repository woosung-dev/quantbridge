# real-ccxt 4.5.49 create_order_request 검증 — maker-TP bracket 의 request shape (E3 게이트 gap).
"""Phase 3 — _merge_exit_params 가 만든 params 를 실제 ccxt 가 어떻게 변환하는지 검증.

mock 테스트(test_provider_exit_params)는 "우리가 ccxt 에 넘기는 params"만 잠근다 — ccxt 가
그걸 tpOrderType=Limit + tpslMode=Partial + tpSize 로 변환하는지는 못 본다. 이 테스트가 그
seam 을 ccxt 4.5.49 소스로 직접 확인 (네트워크 없음 — create_order_request 는 market stub 후 순수).
"""
from __future__ import annotations

import ccxt


def _bybit_with_linear_market() -> ccxt.bybit:
    ex = ccxt.bybit()
    market = {
        "id": "BTCUSDT",
        "symbol": "BTC/USDT",
        "base": "BTC",
        "quote": "USDT",
        "settle": "USDT",
        "baseId": "BTC",
        "quoteId": "USDT",
        "settleId": "USDT",
        "type": "swap",
        "spot": False,
        "margin": False,
        "swap": True,
        "future": False,
        "option": False,
        "contract": True,
        "linear": True,
        "inverse": False,
        "active": True,
        "taker": 0.00055,
        "maker": 0.0002,
        "contractSize": 1.0,
        "precision": {"amount": 0.001, "price": 0.5},
        "limits": {"amount": {"min": 0.001}, "price": {}, "cost": {}},
        "info": {},
    }
    ex.markets = {"BTC/USDT": market}
    ex.markets_by_id = {"BTCUSDT": [market]}
    ex.options["defaultType"] = "swap"
    return ex


def test_bybit_maker_tp_bracket_becomes_limit_with_partial_size() -> None:
    # _merge_exit_params(partial_size=True) 가 만드는 params (Bybit demo/futures).
    ex = _bybit_with_linear_market()
    params = {
        "reduceOnly": False,
        "takeProfit": {"triggerPrice": "52000", "price": "52000"},
        "tpSize": "0.001",
        "stopLoss": {"triggerPrice": "47000"},
        "slSize": "0.001",
    }
    req = ex.create_order_request("BTC/USDT", "market", "buy", 0.001, None, params, True)

    # maker TP: ccxt 가 price 를 보고 tpOrderType=Limit + tpLimitPrice + tpslMode=Partial 설정.
    assert req.get("tpOrderType") == "Limit"
    assert req.get("tpslMode") == "Partial"
    assert req.get("tpLimitPrice") is not None
    # Partial 모드 필수 size 가 request 에 살아남는지 (누락 시 Bybit 가 엔트리 통째 거부).
    assert req.get("tpSize") == "0.001"
    assert req.get("slSize") == "0.001"
    # 부착 bracket → 정상 order-create 경로 (set-trading-stop 으로 안 샘).
    assert req.get("takeProfit") is not None
    assert req.get("stopLoss") is not None


def test_bybit_taker_sl_only_is_full_mode_no_size() -> None:
    # SL 단독(limit TP 없음) → Full 모드 → tpslMode 미설정 + size 불필요.
    ex = _bybit_with_linear_market()
    params = {"reduceOnly": False, "stopLoss": {"triggerPrice": "47000"}}
    req = ex.create_order_request("BTC/USDT", "market", "sell", 0.001, None, params, True)
    assert req.get("stopLoss") is not None
    assert req.get("tpslMode") != "Partial"
    assert "slSize" not in req


def test_bybit_trailing_routes_to_trading_stop_drops_qty() -> None:
    """STEP B (qa-P2) — set_trading_stop 의 라우팅 전제를 ccxt 4.5.49 소스로 직접 핀.

    {trailingStop} 가 붙은 market create_order 는 별도 주문이 아니라 포지션 trading-stop 으로
    변환된다 — side/qty 드롭(엔드포인트가 포지션에서 추론), trailingStop 만 전송. ccxt 업그레이드가
    이 라우팅을 깨면(=실 market order 로 포지션 flatten/double = money-losing) 이 테스트가 CI 에서
    잡는다. set_trading_stop 의 mock 테스트는 "우리가 넘기는 params"만 잠그고 이 seam 은 못 본다.
    """
    ex = _bybit_with_linear_market()
    req = ex.create_order_request(
        "BTC/USDT", "market", "sell", 0.001, None, {"trailingStop": "150.5"}
    )
    # trading-stop 형태: trailingStop 만 + side/qty/orderType 미전송(일반 주문 아님).
    assert req == {"category": "linear", "symbol": "BTCUSDT", "trailingStop": "150.5"}


def test_bybit_trailing_distance_tick_normalized_survives_routing() -> None:
    """BL-372 — 실 ccxt price_to_precision(coarse distance) → tick 정렬 → trailingStop 으로 보존.

    set_trading_stop 이 price_to_precision 결과를 그대로 넘기므로, 정규화+라우팅 end-to-end 핀
    (mock 테스트는 정규화만, 기존 routing 핀은 이미-정렬 값만 — 이 테스트가 양자화 step 을 실 ccxt 로).
    """
    from decimal import Decimal

    ex = _bybit_with_linear_market()  # precision price tick = 0.5
    normalized = ex.price_to_precision("BTC/USDT", 150.567)  # 150.567 → 150.5
    assert Decimal(normalized) == Decimal("150.5")
    req = ex.create_order_request(
        "BTC/USDT", "market", "sell", 0.001, None, {"trailingStop": normalized}
    )
    assert req == {"category": "linear", "symbol": "BTCUSDT", "trailingStop": normalized}
