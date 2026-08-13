# NormalizedSymbol Request-boundary validator 단위 검증 (BL-454).

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from src.common.normalized_symbol import NormalizedSymbol


class _M(BaseModel):
    """Pydantic test wrapper."""

    v: NormalizedSymbol


class _Bounded(BaseModel):
    """실제 ingress 와 동일한 조합 — BeforeValidator + str 길이 제약."""

    v: NormalizedSymbol = Field(min_length=1, max_length=32)


# === 정규화 ===


def test_normalizes_concatenated_to_ccxt_unified() -> None:
    assert _M.model_validate({"v": "BTCUSDT"}).v == "BTC/USDT"


def test_is_idempotent_on_already_unified() -> None:
    assert _M.model_validate({"v": "BTC/USDT"}).v == "BTC/USDT"


def test_uppercases_and_trims() -> None:
    assert _M.model_validate({"v": " btc/usdt "}).v == "BTC/USDT"
    assert _M.model_validate({"v": "solusdt"}).v == "SOL/USDT"


def test_collapses_ccxt_perpetual_to_its_linear_market() -> None:
    """우리가 직접 만드는 표기다(`to_ccxt_perpetual_symbol`). 추측이 아니다."""
    assert _M.model_validate({"v": "BTC/USDT:USDT"}).v == "BTC/USDT"


def test_collapses_the_slashless_colon_form_without_producing_garbage() -> None:
    """★`normalize_symbol` 단독으로는 `BTCUSDT:USDT` → `BTCUSDT:/USDT` 쓰레기가 나온다.

    slash 가 없으니 quote 접미 매칭이 `USDT` 를 잡고 base 가 `BTCUSDT:` 가 되기
    때문이다. 콜론을 먼저 분해해야 그 트랩이 닫힌다.
    """
    assert _M.model_validate({"v": "BTCUSDT:USDT"}).v == "BTC/USDT"


# === 거부 ===


def test_rejects_inverse_settle_instead_of_coercing_it_to_linear() -> None:
    """`BTC/USD:BTC` 는 coin-margined 다. linear 로 붕괴시키면 다른 시장이 된다."""
    with pytest.raises(ValidationError):
        _M.model_validate({"v": "BTC/USD:BTC"})


def test_rejects_tradingview_style_decoration() -> None:
    """★TV 가 퍼프에서 `.P` 를 붙이는지 1차 출처로 확인하지 못했다.

    확인 전에는 장식 제거를 추측으로 넣지 않고 fail-closed 로 둔다. 거부는 카운터와
    로그로 관측하므로 첫 실사용 때 실제 포맷을 배운다.
    """
    for raw in ("BTCUSDT.P", "BTC/USDT.P", "BYBIT:BTCUSDT", "BTCPERP"):
        with pytest.raises(ValidationError):
            _M.model_validate({"v": raw})


def test_rejects_unrecognizable_and_empty_input() -> None:
    for raw in ("BTC", "", "   ", "BTC-USDT", "/USDT", "USDT"):
        with pytest.raises(ValidationError):
            _M.model_validate({"v": raw})


def test_rejects_non_string_input() -> None:
    """JSON 숫자가 문자열로 저장되는 경로를 막는다."""
    for raw in (123, None, ["BTC/USDT"], {"symbol": "BTC/USDT"}):
        with pytest.raises(ValidationError):
            _M.model_validate({"v": raw})


# === 길이 제약 순서 (BeforeValidator 가 먼저 돈다) ===


def test_length_bound_applies_to_the_normalized_value() -> None:
    """★정규화는 길이를 늘린다(`BTCUSDT` 7 → `BTC/USDT` 8).

    그래서 컬럼 폭은 정규화 **후** 값에 걸려야 한다. 이 단정이 BeforeValidator 가 str
    제약보다 먼저 돈다는 것을 증명한다 — 추론으로 넘기지 않는다.
    """
    with pytest.raises(ValidationError):
        _Bounded.model_validate({"v": "A" * 30 + "USDT"})


def test_bounded_model_accepts_a_normal_symbol() -> None:
    assert _Bounded.model_validate({"v": "BTCUSDT"}).v == "BTC/USDT"
