"""실제 unW의 전역 단일 숫자 리터럴 투명도만 정적 fill에 연결한다."""

import pytest

from scripts.pine_validation.native_capture import (
    _readonly_globals,
    _source_calls,
    _static_fill_color,
)


def fill_source(declaration="tpf = 85", extra=""):
    return f"""//@version=5
indicator("readonly transparency")
chm1 = #ff0000
{declaration}
{extra}
a = plot(close)
b = plot(open)
fill(a,b,color.new(chm1,tpf),title="Extra High heatmap zone")
"""


def resolved(source):
    _, _, fills = _source_calls(source)
    return _static_fill_color(fills[0], 5, _readonly_globals(source))


@pytest.mark.parametrize("value,alpha", [(0, "1"), (85, "0.15"), (100, "0"), (85.5, "0.145")])
def test_readonly_literal_transparency_uses_exact_css_alpha(value, alpha):
    assert resolved(fill_source(f"tpf = {value}")) == f"rgba(255,0,0,{alpha})"


@pytest.mark.parametrize(
    "declaration,extra",
    [
        ("tpf = true", ""),
        ("tpf = input.int(85)", ""),
        ("tpf = 80+5", ""),
        ("tpf = -1", ""),
        ("tpf = 101", ""),
        ("tpf = 85", "tpf := 50"),
        ("tpf = 85", "if close>open\n    tpf := 50"),
        ("tpf = 85", "if close>open\n    tpf += 1"),
        ("tpf = 85", "f(tpf) => tpf"),
        ("tpf = 85", "f() =>\n    tpf = 40\n    tpf"),
        ("tpf = 85", "for tpf = 0 to 1\n    x = tpf"),
        ("if close>open\n    tpf = 85", ""),
        ("tpf() => 85", ""),
        ("other = 85\ntpf = other", ""),
    ],
)
def test_dynamic_mutable_local_or_ambiguous_transparency_remains_rejected(declaration, extra):
    with pytest.raises(ValueError):
        resolved(fill_source(declaration, extra))
