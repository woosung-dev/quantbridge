"""원시 gzip의 곡선·판정을 보존하고 receipt의 중복 배열만 제외한다."""

import copy
import gzip
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import sol_economic_data
from tools.research.editor_picks import execution, verification
from tools.research.editor_picks.common import identity, read, sha, write

from src.strategy.code_runtime import backtest
from src.strategy.python_runtime import serialization


@pytest.fixture
def completed(tmp_path, monkeypatch):
    item = {"id": "one", "warmup_bars": 0}
    write(tmp_path / "cohort.json", {"items": [item]})
    job = {"id": "one", "arm": "pine", "timeframe": "1h", "months": 6, "scenario": "baseline"}
    frozen = {
        "cohort_file": "cohort.json",
        "cohort_sha256": sha((tmp_path / "cohort.json").read_bytes()),
        "implementation": {},
        "dataset_sha256": "dataset",
        "dataset": {"end": "2026-10-24T00:00:00+00:00", "warmup": 0},
        "artifacts": {"one": {"pine": {"language": "pine", "source_sha256": "code"}}},
        "jobs": [job],
    }
    end = pd.Timestamp(frozen["dataset"]["end"])
    index = pd.date_range(end - pd.DateOffset(months=6), end, freq="1h", inclusive="left")
    frame = pd.DataFrame(dict.fromkeys(("open", "high", "low", "close", "volume"), 1), index=index)
    payload = {
        "metrics": {
            "total_return": "0.1",
            "sharpe_ratio": "0",
            "sharpe_convention": "tv_monthly_rfr2",
            "drawdown_curve": [["time", "-0.1"]],
            "buy_and_hold_curve": [["time", "0.2"]],
            "custom_metric": ["preserved"],
        },
        "equity_curve": [{"timestamp": "time", "value": "11000"}],
        "trades": [],
        "config_used": {"init_cash": "10000"},
    }
    monkeypatch.setattr(execution, "implementation", lambda: {})
    monkeypatch.setattr(execution, "artifact", lambda *_: ("never executed", "pine", "code"))
    monkeypatch.setattr(
        execution,
        "data",
        lambda *_: {"1h": frame, "1min": frame, "funding": pd.Series(0, index=index)},
    )
    monkeypatch.setattr(backtest, "run_code_backtest", lambda *_, **__: SimpleNamespace(trades=[]))
    monkeypatch.setattr(serialization, "result_payload", lambda _: copy.deepcopy(payload))
    observed = []

    def economic(metrics, closed):
        observed.append(copy.deepcopy(metrics))
        assert metrics["drawdown_curve"] == payload["metrics"]["drawdown_curve"]
        return {"passed": False, "closed": closed}

    monkeypatch.setattr(sol_economic_data, "economic_verdict", economic)
    result = execution.execute_job(tmp_path, frozen, job, {"pine": "image"})
    folder = tmp_path / "results" / result["job_hash"]
    return tmp_path, frozen, result, folder, observed


def test_raw_full_payload_curves_and_economic_inputs_are_preserved(completed):
    _, _, receipt, folder, economic_inputs = completed
    assert receipt["status"] == "completed"
    raw = json.loads(gzip.decompress((folder / "result.json.gz").read_bytes()))
    metrics = raw["result"]["metrics"]
    assert metrics["drawdown_curve"] == [["time", "-0.1"]]
    assert metrics["buy_and_hold_curve"] == [["time", "0.2"]]
    assert receipt["metrics"] == {
        key: value
        for key, value in metrics.items()
        if key not in {"drawdown_curve", "buy_and_hold_curve"}
    }
    assert economic_inputs == [metrics]
    assert receipt["economic_verdict"] == {"passed": False, "closed": 0}
    assert receipt["action_sha256"] == identity([])
    assert receipt["ledger_sha256"] == identity(
        {"trades": raw["result"]["trades"], "equity": raw["result"]["equity_curve"]}
    )
    assert receipt["files"]["result.json.gz"] == sha((folder / "result.json.gz").read_bytes())


@pytest.mark.parametrize("legacy_curves", (False, True))
def test_existing_receipt_reader_accepts_both_new_and_legacy_metrics(completed, legacy_curves):
    root, frozen, receipt, folder, _ = completed
    raw_metrics = json.loads(gzip.decompress((folder / "result.json.gz").read_bytes()))["result"][
        "metrics"
    ]
    if legacy_curves:
        receipt["metrics"] = raw_metrics
        write(folder / "receipt.json", receipt)
    rows = verification.receipts(root, frozen)
    observed = rows[identity(frozen["jobs"][0])]
    assert observed["metrics"] == read(folder / "receipt.json")["metrics"]
    assert observed["action_sha256"] == receipt["action_sha256"]
    assert observed["ledger_sha256"] == receipt["ledger_sha256"]
    assert observed["economic_verdict"] == receipt["economic_verdict"]
