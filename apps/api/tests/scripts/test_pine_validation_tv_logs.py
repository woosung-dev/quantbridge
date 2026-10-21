"""브라우저 QB1 로그의 파싱·분모·provenance·손계산 UT Bot 대조."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.pine_validation.tv_logs import compare_utbot_logs, export_tv_logs, parse_tv_logs

BASE = datetime(2026, 10, 1, tzinfo=UTC)


def row(index=0, *, buy="false", sell="false", stop="9", atr="1", price=10, **changes):
    fields = [
        str(int((BASE + timedelta(hours=index)).timestamp() * 1000)),
        str(price),
        str(price + 1),
        str(price - 1),
        str(price),
        "1",
        buy,
        sell,
        stop,
        atr,
    ]
    for position, value in changes.items():
        fields[int(position.removeprefix("f"))] = value
    return ",".join(fields) + ";"


def log(*rows):
    return "[1999-01-01T00:00:00.000+09:00]: QB1|" + "".join(rows)


def test_payload_time_is_canonical_and_unsorted_browser_logs_are_sorted():
    dataset = parse_tv_logs([log(row(1, sell="true")), log(row(0, stop="NaN", atr="NaN"))], "1h")
    assert dataset.ohlcv.index[0] == BASE
    assert len(dataset.ohlcv) == 2
    assert dataset.events[0].bar_time == BASE + timedelta(hours=1)
    assert dataset.events[0].confirmed_at == BASE + timedelta(hours=2)
    assert dataset.events[0].display_time == dataset.events[0].bar_time
    assert dataset.metadata["warmup_nan"] == {"stop": 1, "atr": 1}
    assert dataset.metadata["reference_kind"] == "derived_probe"
    assert dataset.metadata["native_original_verified"] is False


@pytest.mark.parametrize(
    "rows, message",
    [
        ([row(), row()], "중복"),
        ([row(), row(buy="true")], "충돌"),
        ([row(), row(2)], "누락"),
        ([row(f0=str(int(BASE.timestamp() * 1000) + 1000))], "시간 격자"),
        ([row(buy="1")], "true 또는 false"),
        ([row(buy="true", sell="true")], "매수·매도"),
        ([row(f1="NaN")], "비유한"),
        ([row(f5="inf")], "비유한"),
        ([row(f2="1")], "OHLC"),
        ([row(), row(1, stop="NaN")], "warmup 뒤"),
        ([row(atr="Infinity")], "비유한"),
    ],
)
def test_malformed_or_incomplete_log_cannot_become_valid_data(rows, message):
    with pytest.raises(ValueError, match=message):
        parse_tv_logs([log(*rows)], "1h")


def test_truncated_payload_and_missing_field_are_errors():
    with pytest.raises(ValueError, match="잘린 로그"):
        parse_tv_logs([log(row()).rstrip(";")], "1h")
    with pytest.raises(ValueError, match="필드"):
        parse_tv_logs([log("1,2,3;")], "1h")
    with pytest.raises(ValueError, match="문자열 배열"):
        parse_tv_logs([], "1h")


def test_export_requires_full_window_and_preserves_warmup(tmp_path):
    dataset = parse_tv_logs([log(row(0), row(1, buy="true"), row(2))], "1h")
    with pytest.raises(ValueError, match="누락"):
        dataset.window(BASE, BASE + timedelta(hours=4))
    paths = export_tv_logs(
        dataset, tmp_path, BASE + timedelta(hours=1), BASE + timedelta(hours=3), prefix="fixture"
    )
    assert len(paths["ohlcv"].read_text().splitlines()) == 4
    events = json.loads(paths["events"].read_text())
    assert len(events) == 1 and events[0]["direction"] == "long"
    metadata = json.loads(paths["metadata"].read_text())
    assert metadata["window"]["bars"] == 2
    assert metadata["warmup_bars_before_window"] == 1
    assert metadata["native_original_verified"] is False


def test_probe_python_comparison_uses_independent_hand_oracle():
    # ATR(1)=[2,4,7,9], stop=[8,9,14,6], 2번 매도·3번 매수.
    rows = [
        row(0, price=10, stop="8", atr="2"),
        row(1, price=13, stop="9", atr="4"),
        row(2, price=7, stop="14", atr="7", sell="true"),
        row(3, price=15, stop="6", atr="9", buy="true"),
    ]
    dataset = parse_tv_logs([log(*rows)], "1h")
    result = compare_utbot_logs(dataset, BASE, BASE + timedelta(hours=4), atr_period=1)
    assert result["signal_comparison"]["status"] == "exact_match"
    assert result["diagnostics"]["stop"]["max_abs_difference"] == 0
    assert result["diagnostics"]["atr"]["max_abs_difference"] == 0
    assert result["native_original_verified"] is False
