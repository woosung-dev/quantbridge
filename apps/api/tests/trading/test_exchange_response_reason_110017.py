"""110017 reduce-only 응답의 머니 패스 갈래를 검증한다."""

from __future__ import annotations

import pytest

from src.common.metrics import _normalize_exchange_order_response_reason

_SAME_SIDE_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"reduce-only order '
    'has same side with current position","result":{},"retExtInfo":{}}'
)
_POSITION_ZERO_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"current position '
    'is zero","result":{},"retExtInfo":{}}'
)
_UNRECOGNIZED_110017_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"reduce-only order '
    'was rejected","result":{},"retExtInfo":{}}'
)


def test_110017_same_side_is_distinguished_from_other_branches() -> None:
    assert _normalize_exchange_order_response_reason(_SAME_SIDE_RESPONSE) == "reduce_only_same_side"
    assert _normalize_exchange_order_response_reason(_POSITION_ZERO_RESPONSE) != "reduce_only_same_side"
    assert (
        _normalize_exchange_order_response_reason(_UNRECOGNIZED_110017_RESPONSE)
        != "reduce_only_same_side"
    )


def test_110017_position_zero_is_distinguished_from_other_branches() -> None:
    assert (
        _normalize_exchange_order_response_reason(_POSITION_ZERO_RESPONSE)
        == "reduce_only_position_zero"
    )
    assert _normalize_exchange_order_response_reason(_SAME_SIDE_RESPONSE) != "reduce_only_position_zero"
    assert (
        _normalize_exchange_order_response_reason(_UNRECOGNIZED_110017_RESPONSE)
        != "reduce_only_position_zero"
    )


def test_110017_unrecognized_message_preserves_residual_bucket() -> None:
    assert (
        _normalize_exchange_order_response_reason(_UNRECOGNIZED_110017_RESPONSE)
        == "reduce_only_violation"
    )
    assert _normalize_exchange_order_response_reason(_SAME_SIDE_RESPONSE) != "reduce_only_violation"
    assert _normalize_exchange_order_response_reason(_POSITION_ZERO_RESPONSE) != "reduce_only_violation"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            'bybit {"retCode":110017,"retMsg":"REDUCE-ONLY order has SAME   SIDE with '
            'current position"}',
            "reduce_only_same_side",
        ),
        (
            'bybit {"retCode":110017,"retMsg":"CURRENT\n POSITION\t IS ZERO"}',
            "reduce_only_position_zero",
        ),
    ],
)
def test_110017_matches_case_and_whitespace_variants(message: str, expected: str) -> None:
    assert _normalize_exchange_order_response_reason(message) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ('bybit {"retCode":110034,"retMsg":"There is no net position"}', "position_zero"),
        ('bybit {"retCode":110092,"retMsg":"expect Rising"}', "trigger_breached"),
        ('bybit {"retCode":110093,"retMsg":"expect Falling"}', "trigger_breached"),
        ("bybit response without a retCode", "unparsed"),
        ('bybit {"retCode":999999,"retMsg":"unknown error"}', "other"),
    ],
)
def test_110017_split_does_not_change_other_retcode_reasons(message: str, expected: str) -> None:
    assert _normalize_exchange_order_response_reason(message) == expected
