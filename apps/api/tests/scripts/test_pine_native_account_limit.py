"""계정 한도는 워밍업·미확정·공통 열 바깥의 수신 봉까지 포함한다."""

from datetime import UTC, datetime

import pytest

from scripts.pine_validation.native_capture import _frames, parse_native_capture
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, T0, _frame, _payload


def capture(count, *, unclosed=False):
    raw = _payload()
    messages = _frames(raw["wire"][1]["data"])
    study = messages[1]["p"][1]["study"]["st"]
    price = messages[2]["p"][1]["chart"]["s"]
    study[:] = [{"i": i, "v": [T0 + i * 3600, i % 2, 101, 100]} for i in range(count)]
    price[:] = [{"i": i, "v": [T0 + i * 3600, 100, 102, 99, 101, 10]} for i in range(count)]
    raw["wire"][1]["data"] = "".join(_frame(message) for message in messages)
    end = T0 + count * 3600 - (3599 if unclosed else 0)
    raw["observed_at"] = datetime.fromtimestamp(end, UTC).isoformat()
    return raw


def parse(raw, limit=5000, *, full_prefix=True):
    return parse_native_capture(
        raw,
        source=SOURCE.encode(),
        signal_bindings=BINDINGS,
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={},
        max_total_bars=limit,
        require_full_prefix=full_prefix,
    )


def test_exact_limit_includes_unclosed_bar_and_does_not_truncate_state_prefix():
    native = parse(capture(5000, unclosed=True))
    assert len(native.ohlcv) == 4999
    assert native.metadata["total_received_bars"] == 5000
    with pytest.raises(ValueError, match="계정 한도"):
        parse(capture(5001, unclosed=True))


def test_excess_price_history_cannot_hide_outside_common_study_rows():
    raw = capture(5001)
    messages = _frames(raw["wire"][1]["data"])
    messages[1]["p"][1]["study"]["st"] = messages[1]["p"][1]["study"]["st"][-2:]
    raw["wire"][1]["data"] = "".join(_frame(message) for message in messages)
    with pytest.raises(ValueError, match="계정 한도"):
        parse(raw)


@pytest.mark.parametrize("limit", [True, 0, -1, 5000.0])
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError, match="양의 정수"):
        parse(capture(2), limit)


def test_other_parser_users_can_explicitly_omit_account_cap():
    assert len(parse(capture(5001), None).ohlcv) == 5001


def test_missing_initial_price_cannot_be_hidden_by_warmup_or_common_intersection():
    raw = capture(3)
    messages = _frames(raw["wire"][1]["data"])
    messages[2]["p"][1]["chart"]["s"] = messages[2]["p"][1]["chart"]["s"][1:]
    raw["wire"][1]["data"] = "".join(_frame(message) for message in messages)
    with pytest.raises(ValueError, match="초기 가격 이력"):
        parse(raw)
    generic = parse(raw, full_prefix=False)
    assert len(generic.ohlcv) == 2
    assert generic.metadata["full_study_prefix_covered"] is False
