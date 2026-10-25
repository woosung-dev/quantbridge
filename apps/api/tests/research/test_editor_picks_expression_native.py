"""조건식 native 참조의 해시 결박과 기존 parser 전달 계약 회귀. 실제 TV 근거가 아니다."""

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import catalogue, verification
from tools.research.editor_picks.common import sha, write

from scripts.pine_validation.strategy_adapter import adapt_strategy

SOURCE = '//@version=5\nindicator("reference")\nup=close>open\ndown=close<open\n'
EXPRESSIONS = [
    {"direction": "long", "expression": "up and not up[1]"},
    {"direction": "short", "expression": "down and not down[1]"},
]


def expression_item(root):
    (root / "original.pine").write_bytes(SOURCE.encode())
    augmented, bindings, provenance = catalogue.augment_expression_signals(SOURCE, EXPRESSIONS)
    path = root / "augmented/abcdefgh.pine"
    path.parent.mkdir()
    path.write_bytes(augmented.encode())
    provenance["augmented_file"] = "augmented/abcdefgh.pine"
    adapted = adapt_strategy(augmented, bindings, fixed_quantity=None)
    return {
        "id": "abcdefgh", "source_file": "original.pine", "source_sha256": sha(SOURCE.encode()),
        "binding_type": "expression", "expression_bindings": copy.deepcopy(EXPRESSIONS),
        "signal_bindings": bindings, "expression_provenance": provenance,
        "adaptation": adapted.to_dict(), "warmup_bars": 2,
    }, augmented.encode()


def test_expression_native_reference_recreates_bytes_metadata_and_bindings(tmp_path):
    item, expected = expression_item(tmp_path)
    source, reference = verification.native_reference(tmp_path, item)
    assert source == expected
    assert reference["reference_source_sha256"] == sha(expected)
    assert reference["original_source_sha256"] == sha(SOURCE.encode())
    assert reference["reference_scope"] == "appended_reviewed_expression_diagnostics"
    assert reference["diagnostics"] == item["expression_provenance"]["diagnostics"]
    assert item["source_sha256"] != reference["reference_source_sha256"]


@pytest.mark.parametrize("change", ["original", "augmented", "rehash", "expression", "binding", "metadata", "adaptation", "type", "missing"])
def test_expression_reference_rejects_tampering_at_every_contract(tmp_path, change):
    item, augmented = expression_item(tmp_path)
    if change == "original":
        (tmp_path / "original.pine").write_bytes(b"tampered")
    elif change in {"augmented", "rehash"}:
        changed = augmented + b"plot(close)\n"
        (tmp_path / "augmented/abcdefgh.pine").write_bytes(changed)
        if change == "rehash":
            item["expression_provenance"]["augmented_source_sha256"] = sha(changed)
    elif change == "expression":
        item["expression_bindings"][0]["expression"] = "up"
    elif change == "binding":
        item["signal_bindings"][0]["expression"] = "down"
    elif change == "metadata":
        item["expression_provenance"]["native_verified"] = True
    elif change == "adaptation":
        item["adaptation"]["source_sha256"] = item["source_sha256"]
    elif change == "type":
        item["binding_type"] = "call"
    else:
        del item["expression_provenance"]
    with pytest.raises(ValueError):
        verification.native_reference(tmp_path, item)


def test_original_is_checked_before_augmented_or_regeneration(tmp_path, monkeypatch):
    item, _ = expression_item(tmp_path)
    seen = []

    def reject_original(root, path, digest):
        seen.append((path, digest))
        raise ValueError("original mismatch")

    monkeypatch.setattr(verification, "checked_file", reject_original)
    monkeypatch.setattr(catalogue, "augment_expression_signals", lambda *_: pytest.fail("reached regeneration"))
    with pytest.raises(ValueError, match="original mismatch"):
        verification.native_reference(tmp_path, item)
    assert seen == [(item["source_file"], item["source_sha256"])]


def test_call_reference_keeps_original_bytes_and_no_new_metadata(tmp_path):
    (tmp_path / "original.pine").write_bytes(SOURCE.encode())
    item = {"source_file": "original.pine", "source_sha256": sha(SOURCE.encode())}
    assert verification.native_reference(tmp_path, item) == (SOURCE.encode(), {})


@pytest.mark.parametrize("expression", [False, True])
def test_verify_forwards_exact_reference_to_existing_parser(tmp_path, monkeypatch, expression):
    from scripts.pine_validation import native_capture

    if expression:
        item, expected = expression_item(tmp_path)
    else:
        source = SOURCE + "alertcondition(up)\nalertcondition(down)\n"
        (tmp_path / "original.pine").write_bytes(source.encode())
        bindings = [{"function": "alertcondition", "line": 5 + i, "direction": direction} for i, direction in enumerate(("long", "short"))]
        item = {"id": "abcdefgh", "source_file": "original.pine", "source_sha256": sha(source.encode()), "signal_bindings": bindings, "adaptation": adapt_strategy(source, bindings).to_dict(), "warmup_bars": 2}
        expected = source.encode()
    plan = tmp_path / "plan.json"
    write(plan, {"phase": "full", "jobs": []})
    for timeframe in ("1h", "4h", "1d"):
        write(tmp_path / f"native/abcdefgh/{timeframe}.json", {"raw": timeframe})
    frame = pd.DataFrame(index=pd.date_range("2026-01-01", periods=7, freq="h", tz="UTC"))
    calls = []
    actions = ["hold", "hold", "long", "hold", "short", "hold", "hold"]

    def parse(raw, **kwargs):
        calls.append((raw, kwargs))
        return SimpleNamespace(
            ohlcv=frame, metadata={"unaltered": True},
            window_events=lambda *_: [SimpleNamespace(direction=direction, bar_time=frame.index[index]) for index, direction in ((2, "long"), (4, "short"))],
        )

    monkeypatch.setattr(native_capture, "parse_native_capture", parse)
    monkeypatch.setattr(verification, "frozen_inputs", lambda *_: {"items": [item]})
    monkeypatch.setattr(verification, "require_runtime", lambda: {"pine": "image"})
    monkeypatch.setattr(verification, "receipts", lambda *_: {})
    monkeypatch.setattr(verification, "artifact", lambda *_: ("source", "pine", "digest"))
    monkeypatch.setattr(verification, "session_actions", lambda _a, _b, frame, *_: actions[:len(frame)])
    monkeypatch.setattr(verification, "exact_cells", lambda *_: 36)
    result = verification.verify(tmp_path, "abcdefgh", plan)
    assert len(calls) == 3
    for _, kwargs in calls:
        assert kwargs["source"] == expected
        assert kwargs["signal_bindings"] == verification.native_bindings(item)
        assert kwargs["expected_indicator_id"] == "abcdefgh"
        assert kwargs["expected_symbol"] == "BYBIT:BTCUSDT.P"
        assert kwargs["expected_inputs"] == {}
    for window in result["native_windows"].values():
        assert window["status"] == "checked_partial_window"
        assert window["metadata"] == {"unaltered": True}
        if expression:
            assert window["reference_source_sha256"] == sha(expected)
            assert window["reference_scope"] == "appended_reviewed_expression_diagnostics"
        else:
            assert "reference_source_sha256" not in window
            assert "reference_scope" not in window
    assert result["source_sha256"] == item["source_sha256"]
    # parser 거부를 성공으로 완화하지 않는다.
    monkeypatch.setattr(native_capture, "parse_native_capture", lambda *_a, **_k: (_ for _ in ()).throw(ValueError("raw proof mismatch")))
    rejected = verification.verify(tmp_path, "abcdefgh", plan)
    assert all(w["status"] == "invalid_native_capture" for w in rejected["native_windows"].values())
    assert all(a["status"] == "incomplete" for a in rejected["arms"].values())
