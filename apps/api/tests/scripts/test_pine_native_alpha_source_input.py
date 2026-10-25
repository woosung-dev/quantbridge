"""ATR Rope 실제 입력 slot의 alpha와 nz(source) 문맥을 보존한다."""

import hashlib

import pytest

from scripts.pine_validation.native_capture import _frames, parse_native_capture
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, _frame, _payload


def observed(kind):
    raw = _payload()
    if kind == "alpha":
        declaration = 'length = input.color(#004d9233, title="Length")'
        value, wire_value, slot_kind = "rgba(0,77,146,0.2)", 865225984, "color"
    else:
        declaration = 'length = nz(input.source(close, title="Length"))'
        value, wire_value, slot_kind = "close", "close", "source"
    source = SOURCE.replace('length = input.int(2, title="Length")', declaration)
    raw.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = raw["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["inputs"][1].update(type=slot_kind, defval=value)
    raw["resolved_inputs"]["length"] = value
    create = _frames(raw["wire"][0]["data"])[0]
    create["p"][5]["in_0"] = {"v": wire_value, "f": True, "t": slot_kind}
    raw["wire"][0]["data"] = _frame(create)
    return source, raw


def parse(source, raw):
    return parse_native_capture(
        raw,
        source=source.encode(),
        signal_bindings=BINDINGS,
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={},
    )


@pytest.mark.parametrize("kind", ["alpha", "source"])
def test_observed_input_defaults_require_source_meta_resolved_and_wire_agreement(kind):
    # 원시 YYrxRhi9/1h: original75be80ed0a01..., input in_8=865225984.
    source, raw = observed(kind)
    assert len(parse(source, raw).ohlcv) == 2
    create = _frames(raw["wire"][0]["data"])[0]
    create["p"][5]["in_0"]["v"] = 4279900698 if kind == "alpha" else "open"
    raw["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError, match="실제 입력"):
        parse(source, raw)
