"""원시 gzip의 곡선·판정을 보존하고 receipt의 중복 배열만 제외한다."""

import copy
import gzip
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import sol_economic_data
from tools.research.editor_picks import compact, execution, remote, verification
from tools.research.editor_picks.common import identity, read, sha, write
from tools.research.editor_picks.crypto import transform

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


def compact_receipt(completed):
    root, frozen, _, folder, _ = completed
    expected = {
        "head": "a" * 40,
        "run_id": "123",
        "attempt": "1",
        "shards": 1,
        "shard": 0,
        "input_sha256": "b" * 64,
        "plan": "pilot-plan.json",
        "plan_sha256": identity(frozen),
    }
    prefix = remote.remote_namespace(expected) / "0"
    paths = {str(path.relative_to(root)): path for path in folder.iterdir() if path.is_file()}
    envelope = root / "envelope.json"
    write(
        envelope,
        {**expected, "files": {name: sha(path.read_bytes()) for name, path in paths.items()}},
    )
    archive = root / "full.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name, path in paths.items():
            bundle.add(path, arcname=name)
        bundle.add(envelope, arcname=str(prefix / "envelope.json"))
    stage = root / "compact-stage"
    compact.prepare(archive, expected, stage)
    body = b"synthetic separately preserved encrypted full result"
    part = {
        "name": "full.enc",
        "bytes": len(body),
        "sha256": sha(body),
        "asset_id": 1,
        "browser_download_url": "https://github.com/woosung-dev/quantbridge/releases/download/editor-picks-research-20261024/full.enc",
    }
    compact_archive = root / "compact.tar.gz"
    compact.seal(
        stage,
        {"schema_version": 1, "bytes": len(body), "sha256": sha(body), "parts": [part]},
        compact_archive,
    )
    cipher = root / "compact.enc"
    key = bytes(32)
    transform(
        "encrypt",
        compact_archive,
        cipher,
        key,
        "editor-picks-20261024/compact-result/" + identity(expected),
    )
    target = root / "collected"
    compact.collect(
        compact_archive,
        target,
        expected,
        [
            {
                "id": 1,
                "name": part["name"],
                "size": part["bytes"],
                "digest": "sha256:" + part["sha256"],
                "state": "uploaded",
                "browser_download_url": part["browser_download_url"],
            }
        ],
        cipher,
        sha(cipher.read_bytes()),
    )
    return target, key, expected


def test_receipts_accept_only_authenticated_remote_raw_and_keep_financial_values(completed):
    _, frozen, receipt, folder, _ = completed
    local = verification.receipts(completed[0], frozen)[identity(frozen["jobs"][0])]
    assert local["raw_result_storage"] == "local_full_payload"
    target, key, expected = compact_receipt(completed)
    assert not (target / folder.relative_to(completed[0]) / "result.json.gz").exists()
    with pytest.raises(ValueError):
        verification.receipts(target, frozen)
    with compact.context(target, key, expected):
        remote_row = verification.receipts(target, frozen)[identity(frozen["jobs"][0])]
        assert remote_row["raw_result_storage"] == "authenticated_remote_payload"
        for field in ("metrics", "action_sha256", "ledger_sha256", "economic_verdict", "files"):
            assert remote_row[field] == receipt[field]
        wrong = copy.deepcopy(frozen)
        wrong["artifacts"]["one"]["pine"]["source_sha256"] = "changed"
        # 계획 SHA도 바꾸면 해당 receipt 자체가 다른 계획이므로 읽히지 않는다.
        assert verification.receipts(target, wrong) == {}
    with pytest.raises(ValueError):
        verification.receipts(target, frozen)


@pytest.mark.parametrize("name", ("request.json", "signals.json.gz", "receipt.json"))
def test_compact_context_never_replaces_required_receipt_evidence(completed, name):
    target, key, expected = compact_receipt(completed)
    folder = completed[3].relative_to(completed[0])
    (target / folder / name).unlink()
    with pytest.raises((OSError, ValueError)), compact.context(target, key, expected):
        verification.receipts(target, completed[1])


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
