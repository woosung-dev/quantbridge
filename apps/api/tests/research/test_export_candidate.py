"""서버 반영 검토 묶음이 동결 코드·원본 평가와 연결되는지 검사한다."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import export_candidate as exporter
from tools.research.catalogue import candidates, source_for
from tools.research.cli import acceptance
from tools.research.data import digest, json_write


@pytest.fixture
def evaluated_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    monkeypatch.setattr(exporter, "load_dataset", lambda _: {})
    root = tmp_path / "runs" / "research"
    root.mkdir(parents=True)
    (root / "results").mkdir()
    candidate = candidates()[0]
    source = source_for(candidate)
    json_write(root / "dataset.json", {"frozen": True})
    engine = {"image_id": "sha256:frozen"}
    json_write(root / "batch.json", {"status": "completed", "completed": 1200, "engine": engine})
    champion = {
        "candidate": candidate,
        "source": source,
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "dataset_sha256": digest(root / "dataset.json"),
        "engine": engine,
    }
    json_write(root / "champion.json", champion)
    json_write(root / "holdout-opened.json", {"champion_sha256": digest(root / "champion.json")})
    metrics = {
        "total_return": "-0.01",
        "profit_factor": "0.9",
        "max_drawdown": "-0.1",
        "funding_data_incomplete": None,
    }
    records = []
    for months in (3, 6):
        for cost in (1, 2):
            row = {
                "job_hash": f"job-{months}-{cost}",
                "status": "completed",
                "stage": "holdout",
                "candidate_id": candidate["id"],
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "dataset_sha256": champion["dataset_sha256"],
                "engine": engine,
                "cell": {"months": months, "symbol": "BTCUSDT", "timeframe": "1h"},
                "cost_multiplier": cost,
                "metrics": metrics,
                "acceptance": acceptance(metrics, 30),
            }
            path = root / "results" / f"{months}-{cost}.json"
            json_write(path, {**row, "trades": [{"status": "closed"}] * 30})
            records.append(
                {**row, "result_path": str(path.relative_to(root)), "result_sha256": digest(path)}
            )
    json_write(
        root / "holdout.json",
        {
            "status": "completed",
            "thresholds_passed": False,
            "promotion_blockers": ["retrospective_not_untouched"],
            "records": records,
        },
    )
    return root, tmp_path / "runs" / "review"


def test_failed_candidate_exports_for_review_without_promotion(evaluated_candidate):
    root, output = evaluated_candidate
    manifest = exporter.export_candidate(root, output)
    assert manifest["review_only"] and not manifest["automatic_promotion"]
    assert not manifest["thresholds_passed"]
    payload = json.loads((output / "save-request.json").read_text())
    assert payload["source"] == (output / "strategy.py").read_text()
    assert all(digest(output / path) == value for path, value in manifest["files"].items())
    assert not list(output.rglob("*.csv"))
    with pytest.raises(ValueError, match="새 출력"):
        exporter.export_candidate(root, output)


@pytest.mark.parametrize("mutation", ["source", "result", "summary", "path"])
def test_tampered_evidence_cannot_create_review_bundle(evaluated_candidate, mutation):
    root, output = evaluated_candidate
    if mutation == "source":
        path = root / "champion.json"
        data = json.loads(path.read_text())
        data["source"] += "\n# altered\n"
    else:
        path = root / "holdout.json"
        data = json.loads(path.read_text())
        if mutation == "result":
            result = root / data["records"][0]["result_path"]
            result.write_text(result.read_text() + " ")
        elif mutation == "path":
            data["records"][0]["result_path"] = "../outside.json"
        else:
            data["thresholds_passed"] = True
    json_write(path, data)
    with pytest.raises(ValueError):
        exporter.export_candidate(root, output)
    assert not output.exists()
