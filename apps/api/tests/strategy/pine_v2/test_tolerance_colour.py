"""상태 fingerprint는 색 표기 identity와 공개 채널을 결정적으로 보존한다."""

import hashlib
from decimal import Decimal

from src.strategy.pine_v2.rendering import color_call, color_literal
from tests.strategy.pine_v2._tolerance import _normalize_for_json, digest_sequence


def test_colour_canonical_form_is_explicit_and_deterministic():
    colour = color_literal("#10203080", 5)
    assert _normalize_for_json(colour) == {
        "$pine_color": {
            "schema_version": 1,
            "identity": ["hex", "#10203080"],
            "red": 16,
            "green": 32,
            "blue": 48,
            "alpha": "0.50196078",
            "version": 5,
        }
    }
    assert digest_sequence({"a": colour, "b": [colour]}) == digest_sequence(
        {"b": [colour], "a": colour}
    )


def test_version_specific_identity_is_not_reduced_to_channels():
    assert digest_sequence(color_literal("#ffffff", 5)) != digest_sequence(
        color_literal("#FFFFFF", 5)
    )
    assert digest_sequence(color_literal("#ffffff", 6)) == digest_sequence(
        color_literal("#FFFFFF", 6)
    )
    literal = color_literal("#FFFFFF", 5)
    rgba = color_call("color.rgb", {"red": 255, "green": 255, "blue": 255}, 5)
    assert (literal.red, literal.green, literal.blue, literal.alpha) == (
        rgba.red,
        rgba.green,
        rgba.blue,
        rgba.alpha,
    )
    assert digest_sequence(literal) != digest_sequence(rgba)


def test_non_colour_canonical_bytes_remain_unchanged():
    expected = b'{"a":["1.25000000",true,null,null],"b":"0.50000000"}'
    value = {"b": 0.5, "a": [Decimal("1.25"), True, None, float("nan")]}
    assert digest_sequence(value) == "sha256:" + hashlib.sha256(expected).hexdigest()
