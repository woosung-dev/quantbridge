# P1-12 (S6, BL-309) — parse_tv_payload error path coverage
"""parse_tv_payload — TradingView webhook payload → OrderRequest 변환의 trust boundary.

audit 2026-05-30 P1-12 / BL-309 — 기존엔 happy-path 1건만 (test_webhook_hmac.py
test_parse_tv_payload_extracts_order_fields) 으로 error path 가 silent 통과 위험.
parametrized 으로 모든 error 분기를 검증해 WebhookUnauthorized 가 throw 되는지 확인.

검증 차원:
- 필수 필드 누락 (KeyError 흡수)
- enum 값 invalid (ValueError 흡수)
- 비숫자 Decimal 변환 실패 (ValueError/TypeError/InvalidOperation 흡수)
- 정상 분기: price 미존재 / price='0' (falsy) / price 양수 string
- type 기본값 'market' 분기
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.trading.exceptions import WebhookUnauthorized
from src.trading.models import OrderSide, OrderType
from src.trading.webhook import parse_tv_payload

# ── 정상 분기 (happy path 확장) ──


def test_type_defaults_to_market_when_omitted():
    """type 누락 시 'market' default — TV alert 의 일반 형태 (대부분 type 미기재)."""
    parsed = parse_tv_payload(
        {"symbol": "BTC/USDT", "side": "buy", "quantity": "0.01"}
    )
    assert parsed.type == OrderType.market


def test_price_omitted_returns_none():
    """price key 자체 누락 → ParsedTradeSignal.price = None (market order)."""
    parsed = parse_tv_payload(
        {"symbol": "BTC/USDT", "side": "buy", "quantity": "0.01", "type": "limit"}
    )
    assert parsed.price is None


def test_price_empty_string_treated_as_none():
    """price='' = falsy → payload.get('price') falsy 분기 → None.

    빈 string 은 Python truthiness 에서 False → if 분기 미진입 → None.
    """
    parsed = parse_tv_payload(
        {"symbol": "BTC/USDT", "side": "buy", "quantity": "0.01", "price": ""}
    )
    assert parsed.price is None


def test_price_zero_string_parses_to_decimal_zero():
    """price='0' = truthy string → Decimal('0').

    Python truthiness 에서 '0' 은 non-empty string → True. parse_tv_payload 는
    Decimal 변환만 수행 — 0 가격 거부 책임은 OrderRequest Field(gt=0) 가 강제.
    """
    parsed = parse_tv_payload(
        {"symbol": "BTC/USDT", "side": "buy", "quantity": "0.01", "price": "0"}
    )
    assert parsed.price == Decimal("0")


def test_price_valid_string_parsed_to_decimal():
    """price='49999.5' → Decimal('49999.5')."""
    parsed = parse_tv_payload(
        {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": "0.01",
            "type": "limit",
            "price": "49999.5",
        }
    )
    assert parsed.price == Decimal("49999.5")


def test_side_case_insensitive():
    """side='BUY' / 'Buy' → lower() 적용 → OrderSide.buy."""
    parsed = parse_tv_payload(
        {"symbol": "BTC/USDT", "side": "BUY", "quantity": "0.01"}
    )
    assert parsed.side == OrderSide.buy


# ── 필수 필드 누락 — KeyError → WebhookUnauthorized ──


@pytest.mark.parametrize(
    "missing_field",
    ["symbol", "side", "quantity"],
)
def test_missing_required_field_raises_webhook_unauthorized(missing_field: str):
    """symbol/side/quantity 누락 시 KeyError → WebhookUnauthorized."""
    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": "0.01",
        "type": "market",
    }
    del payload[missing_field]

    with pytest.raises(WebhookUnauthorized) as exc_info:
        parse_tv_payload(payload)
    assert "Invalid TV payload" in str(exc_info.value)


# ── enum 값 invalid — ValueError → WebhookUnauthorized ──


@pytest.mark.parametrize(
    "invalid_side",
    ["long", "short", "hold", "", "buy_invalid"],
)
def test_invalid_side_raises_webhook_unauthorized(invalid_side: str):
    """OrderSide enum 외 값 → ValueError → WebhookUnauthorized."""
    payload = {
        "symbol": "BTC/USDT",
        "side": invalid_side,
        "quantity": "0.01",
    }
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(payload)


@pytest.mark.parametrize(
    "invalid_type",
    ["stop", "trigger", "conditional", "invalid", ""],
)
def test_invalid_type_raises_webhook_unauthorized(invalid_type: str):
    """OrderType enum 외 값 → ValueError → WebhookUnauthorized."""
    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": "0.01",
        "type": invalid_type,
    }
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(payload)


# ── 비숫자 Decimal 변환 실패 — ValueError/TypeError/InvalidOperation ──


@pytest.mark.parametrize(
    "invalid_quantity",
    ["not-a-number", "abc", "1.2.3", "1,000", ""],
)
def test_invalid_quantity_raises_webhook_unauthorized(invalid_quantity: str):
    """quantity 가 Decimal 변환 불가 → InvalidOperation/ValueError → WebhookUnauthorized."""
    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": invalid_quantity,
    }
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(payload)


@pytest.mark.parametrize(
    "invalid_price",
    ["not-a-number", "abc", "infinity-string", "1,000.5"],
)
def test_invalid_price_raises_webhook_unauthorized(invalid_price: str):
    """price 가 비숫자 string → Decimal InvalidOperation → WebhookUnauthorized.

    falsy 값 ('0', '') 는 별도 분기 (price=None 으로 처리). 여기선 truthy non-numeric.
    """
    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": "0.01",
        "price": invalid_price,
    }
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(payload)


# ── type 변환 실패 (quantity 가 dict/list 등 비-stringifiable) ──


def test_quantity_as_dict_raises_webhook_unauthorized():
    """quantity 가 dict → Decimal(str({...})) 실패 → WebhookUnauthorized."""
    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": {"value": "0.01"},  # 잘못된 형태
    }
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(payload)


def test_side_as_none_raises_webhook_unauthorized():
    """side=None → str(None).lower()='none' → OrderSide('none') ValueError."""
    payload = {
        "symbol": "BTC/USDT",
        "side": None,
        "quantity": "0.01",
    }
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(payload)


# === BL-454 — 심볼 ingress 정규화 ===


def test_parse_normalizes_the_symbol_to_ccxt_unified():
    """TV 는 거래소 원문 티커를 보낸다. 세션 스코프는 정확 문자열 동등이라 여기서 맞춘다.

    이 정규화가 없으면 표기가 어긋난 웹훅 주문이 세션 손익에서 조용히 빠지고
    loss-limit 알림이 fail-open 한다(BL-445 가 넣은 symbol 술어의 대가).
    """
    from src.trading.webhook import parse_tv_payload

    parsed = parse_tv_payload(
        {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "type": "market"}
    )
    assert parsed.symbol == "BTC/USDT"


def test_parse_rejects_and_counts_a_symbol_it_cannot_normalize():
    """★fail-closed + 관측. 거부 자체는 기존 401 계약 그대로다.

    카운터는 "일어나고 있나" 에만 답한다. TV 가 실제로 무슨 문자열을 보내는지는
    `webhook_symbol_normalize_failed` 로그의 원문만 답한다 — `.P` 여부를 1차 출처로
    확인하지 못했으므로 장식 제거를 추측으로 넣지 않고 이 경로로 배운다.
    """
    from src.common.metrics import qb_webhook_symbol_rejected_total
    from src.trading.exceptions import WebhookUnauthorized
    from src.trading.webhook import parse_tv_payload

    before = qb_webhook_symbol_rejected_total._value.get()
    with pytest.raises(WebhookUnauthorized):
        parse_tv_payload(
            {"symbol": "BTCUSDT.P", "side": "buy", "quantity": "1", "type": "market"}
        )
    assert qb_webhook_symbol_rejected_total._value.get() == before + 1
