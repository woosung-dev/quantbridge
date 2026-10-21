"""runner는 원본 wire를 검증하고 기존 사건 파일의 출처 강도를 구분한다."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from scripts import validate_pine_signals as runner
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, T0, _payload


@pytest.fixture(autouse=True)
def _no_app_backtest(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "compare_app_backtest",
        lambda *args, **kwargs: {"status": "missing_signal_ledger"},
    )


def _case(tmp_path):
    start = datetime.fromtimestamp(T0, UTC)
    frame = pd.DataFrame(
        {
            "time": [(start + timedelta(hours=index)).isoformat() for index in range(3)],
            "open": [100, 101, 102],
            "high": [102, 103, 104],
            "low": [99, 100, 101],
            "close": [101, 102, 103],
            "volume": [10, 11, 12],
        }
    )
    frame.to_csv(tmp_path / "1h.csv", index=False)
    (tmp_path / "source.pine").write_text(SOURCE)
    payload = _payload()
    (tmp_path / "native.json").write_text(json.dumps(payload))
    item = {
        "id": "example",
        "source_file": "source.pine",
        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
        "boosts": 100,
        "signal_bindings": BINDINGS,
        "inputs": {},
        "params": {},
        "tv_events": {"1h": "native.json"},
    }
    manifest = {
        "symbol": "BYBIT:BTCUSDT.P",
        "window": {
            "start": start.isoformat(),
            "end": (start + timedelta(hours=2)).isoformat(),
        },
        "ohlcv": {"1h": "1h.csv"},
    }
    return item, manifest, payload


def test_runner_accepts_verified_raw_capture_and_marks_stronger_provenance(tmp_path) -> None:
    item, manifest, _ = _case(tmp_path)
    row = runner.validate_cell(item, "1h", manifest, tmp_path)
    assert row["tv_verification"] == "raw_capture_checked"
    assert len(row["tv_events"]) == 1
    assert row["tv_events"][0]["direction"] == "long"
    assert row["tv_provenance"]["reference_kind"] == "native_original_partial_window"
    assert "invalid_tv_reference" not in row["failures"]


@pytest.mark.parametrize("tamper", ["source", "metadata", "inputs", "window", "ohlcv"])
def test_runner_rejects_tampered_or_partial_raw_without_legacy_fallback(tmp_path, tamper) -> None:
    item, manifest, payload = _case(tmp_path)
    payload = copy.deepcopy(payload)
    if tamper == "source":
        payload["source_sha256"] = "0" * 64
    elif tamper == "metadata":
        payload["compile_responses"][0]["data"]["result"]["metaInfo"]["styles"]["plot_0"][
            "title"
        ] = "Forged"
    elif tamper == "inputs":
        payload["resolved_inputs"]["length"] = 99
    elif tamper == "window":
        start = datetime.fromtimestamp(T0, UTC)
        manifest["window"]["end"] = (start + timedelta(hours=3)).isoformat()
        payload["observed_at"] = (start + timedelta(hours=3)).isoformat()
    else:
        frame = pd.read_csv(tmp_path / "1h.csv")
        frame["close"] = frame["close"].astype(float)
        frame.loc[0, "close"] = 100.5
        frame.to_csv(tmp_path / "1h.csv", index=False)
    payload["events"] = [{"bar_time": manifest["window"]["start"], "direction": "long"}]
    payload["provenance"] = {
        "kind": "native_original",
        "source_sha256": item["source_sha256"],
        "symbol": manifest["symbol"],
        "timeframe": "1h",
        "inputs": {},
        "window": manifest["window"],
    }
    (tmp_path / "native.json").write_text(json.dumps(payload))
    row = runner.validate_cell(item, "1h", manifest, tmp_path)
    assert "invalid_tv_reference" in row["failures"]
    assert row.get("tv_verification") != "operator_provenance_attestation"
    assert "tv_pine" not in row


def test_legacy_events_are_labeled_operator_attestation(tmp_path) -> None:
    item, manifest, _ = _case(tmp_path)
    start = datetime.fromtimestamp(T0, UTC)
    legacy = {
        "events": [{"bar_time": start.isoformat(), "direction": "long"}],
        "provenance": {
            "kind": "native_original",
            "source_sha256": item["source_sha256"],
            "symbol": manifest["symbol"],
            "timeframe": "1h",
            "inputs": {},
            "window": manifest["window"],
        },
    }
    (tmp_path / "native.json").write_text(json.dumps(legacy))
    row = runner.validate_cell(item, "1h", manifest, tmp_path)
    assert row["tv_verification"] == "operator_provenance_attestation"
