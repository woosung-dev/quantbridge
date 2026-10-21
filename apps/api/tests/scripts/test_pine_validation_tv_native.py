"""원본 study 식별·확정 봉·plot/alert 사건·원시 응답 보존 검증. 외부 호출 없음."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from scripts.pine_validation.tv_native import (
    compare_native_events,
    compare_native_ohlcv,
    export_native_capture,
    export_native_reference,
    load_native_capture,
    parse_native_capture,
)

BASE = datetime(2026, 10, 1, tzinfo=UTC)
SOURCE = b'//@version=4\r\nstudy("fixture")\r\n'
COMPILED = SOURCE.replace(b"\r\n", b"\n")


def payload():
    return {
        "capture": "Playwright CDP observed UI-generated native chart study response",
        "symbol": "BYBIT:BTCUSDT.P",
        "timeframe": "1h",
        "study_id": "fixture-study",
        "observed_at": (BASE + timedelta(hours=3, minutes=30)).isoformat(),
        "inputs": {"a": 1, "c": 10, "h": False},
        "source_sha256": hashlib.sha256(SOURCE).hexdigest(),
        "compiled_source_sha256": hashlib.sha256(COMPILED).hexdigest(),
        "compiled_source_matches_original_lf_normalized": True,
        "plot_columns": [
            "time",
            "buy_plotshape",
            "sell_plotshape",
            "barcolor_0",
            "barcolor_1",
            "long_alertcondition",
            "short_alertcondition",
        ],
        "rows": [
            [
                int((BASE + timedelta(hours=i)).timestamp()),
                int(i in (1, 3)),
                int(i == 2),
                1e100,
                1,
                int(i in (1, 3)),
                int(i == 2),
            ]
            for i in range(4)
        ],
        "ohlcv": [],
    }


def parse(data=None, **kwargs):
    return parse_native_capture(
        data or payload(), source=SOURCE, compiled_source=COMPILED, **kwargs
    )


def test_native_source_mapping_and_unconfirmed_event_are_explicit():
    capture = parse(
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={"a": 1, "c": 10, "h": False},
    )
    assert capture.metadata["raw_rows"] == 4
    assert capture.metadata["closed_rows"] == 3
    assert capture.metadata["excluded_unconfirmed_rows"] == 1
    assert [(event.bar_time, event.direction) for event in capture.events] == [
        (BASE + timedelta(hours=1), "long"),
        (BASE + timedelta(hours=2), "short"),
    ]
    assert capture.events[0].confirmed_at == BASE + timedelta(hours=2)
    assert capture.events[0].display_time == BASE + timedelta(hours=1)
    assert capture.metadata["source_provenance"]["study_id"] == "fixture-study"
    assert capture.metadata["native_original_source_verified"] is True
    with pytest.raises(ValueError, match="수집 시점"):
        capture.window_events(BASE, BASE + timedelta(hours=4))


@pytest.mark.parametrize(
    "change,message",
    [
        ({"source_sha256": "0" * 64}, "hash"),
        ({"compiled_source_matches_original_lf_normalized": False}, "무수정"),
        ({"capture": "derived QB1 probe"}, "출처"),
        ({"study_id": ""}, "study_id"),
        ({"inputs": {"a": 1, "c": 10}}, "a/c/h"),
        ({"inputs": {"a": 1, "c": 10, "h": 0}}, "입력 타입"),
        ({"plot_columns": ["unknown"]}, "컬럼 순서"),
    ],
)
def test_unverified_native_provenance_is_not_accepted(change, message):
    data = payload()
    data.update(change)
    with pytest.raises(ValueError, match=message):
        parse(data)


def test_matching_hash_claim_cannot_hide_modified_compiled_source():
    changed = COMPILED + b"plot(close)\n"
    data = payload()
    data["compiled_source_sha256"] = hashlib.sha256(changed).hexdigest()
    with pytest.raises(ValueError, match="무수정"):
        parse_native_capture(data, source=SOURCE, compiled_source=changed)


@pytest.mark.parametrize(
    "kind,message",
    [
        ("plot_alert", "불일치"),
        ("nonbinary", "0/1"),
        ("duplicate", "중복"),
        ("gap", "누락"),
        ("offgrid", "격자"),
    ],
)
def test_native_signal_integrity_and_grid_are_required(kind, message):
    data = payload()
    if kind == "plot_alert":
        data["rows"][1][5] = 0
    elif kind == "nonbinary":
        data["rows"][0][1] = 0.5
    elif kind == "duplicate":
        data["rows"][1][0] = data["rows"][0][0]
    elif kind == "gap":
        data["rows"].pop(1)
    else:
        data["rows"][0][0] += 1
    with pytest.raises(ValueError, match=message):
        parse(data)


def test_export_preserves_raw_bytes_and_only_writes_closed_window_events(tmp_path):
    raw = json.dumps(payload(), indent=2).encode() + b"\n"
    source, compiled, response = (
        tmp_path / name for name in ("original.pine", "compiled.pine", "response.json")
    )
    source.write_bytes(SOURCE)
    compiled.write_bytes(COMPILED)
    response.write_bytes(raw)
    capture = load_native_capture(response, source_path=source, compiled_source_path=compiled)
    paths = export_native_capture(capture, tmp_path / "export", BASE, BASE + timedelta(hours=3))
    assert paths["raw"].read_bytes() == raw == response.read_bytes()
    assert len(json.loads(paths["events"].read_text())) == 2
    assert (
        json.loads(paths["metadata"].read_text())["raw_capture_sha256"]
        == hashlib.sha256(raw).hexdigest()
    )


def test_full_native_probe_python_pine_crosscheck_cannot_pass_missing_reference():
    capture = parse()
    references = dict.fromkeys(("probe", "python", "pine"), capture.events)
    result = compare_native_events(capture, references, BASE, BASE + timedelta(hours=3))
    assert result["status"] == "exact_match" and result["native_original_verified"] is True
    assert len(result["comparisons"]) == 6
    references["pine"] = copy.copy(capture.events[:-1])
    result = compare_native_events(capture, references, BASE, BASE + timedelta(hours=3))
    assert result["status"] == "mismatch" and result["native_original_verified"] is False
    with pytest.raises(ValueError, match="세 참조"):
        compare_native_events(capture, {"python": []}, BASE, BASE + timedelta(hours=3))


def test_cli_reference_export_requires_full_match_and_preserves_binding(tmp_path):
    capture = parse()
    references = dict.fromkeys(("probe", "python", "pine"), capture.events)
    path = tmp_path / "reference.json"
    export_native_reference(capture, path, references, BASE, BASE + timedelta(hours=3))
    result = json.loads(path.read_text())
    assert result["provenance"]["kind"] == "native_original"
    assert result["provenance"]["inputs"] == {"a": 1, "c": 10, "h": False}
    assert result["provenance"]["source_sha256"] == hashlib.sha256(SOURCE).hexdigest()
    original_export = path.read_bytes()
    references["pine"] = []
    with pytest.raises(ValueError, match="완전 일치"):
        export_native_reference(capture, path, references, BASE, BASE + timedelta(hours=3))
    assert path.read_bytes() == original_export


def test_missing_native_ohlcv_is_not_an_exact_data_parity_pass():
    data = payload()
    index = pd.date_range(BASE, periods=3, freq="h")
    reference = pd.DataFrame(
        {"open": [10] * 3, "high": [11] * 3, "low": [9] * 3, "close": [10] * 3, "volume": [1] * 3},
        index=index,
    )
    result = compare_native_ohlcv(
        parse(data), reference, BASE, BASE + timedelta(hours=3), reference_symbol="BYBIT:BTCUSDT.P"
    )
    assert result["status"] == "unverified" and result["missing_native_bars"] == 3
    data["ohlcv"] = [[int(at.timestamp()), 10, 11, 9, 10, 1] for at in index]
    result = compare_native_ohlcv(
        parse(data), reference, BASE, BASE + timedelta(hours=3), reference_symbol="BYBIT:BTCUSDT.P"
    )
    assert result["status"] == "exact_match"
    data["ohlcv"][1][4] = 10.5
    result = compare_native_ohlcv(
        parse(data), reference, BASE, BASE + timedelta(hours=3), reference_symbol="BYBIT:BTCUSDT.P"
    )
    assert result["status"] == "mismatch" and result["mismatches"][0]["field"] == "close"
