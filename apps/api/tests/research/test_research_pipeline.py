"""연구 후보 수, 완전한 데이터, 최종 기간 접근의 회귀 검사. DB 미사용."""

import ast
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import cli, sources
from tools.research.catalogue import candidates, pilot_candidates, source_for
from tools.research.data import validate_candles, validate_funding


def candle_frame():
    return pd.DataFrame(
        {
            "open": ["100"] * 4,
            "high": ["101"] * 4,
            "low": ["99"] * 4,
            "close": ["100"] * 4,
            "volume": ["10"] * 4,
        },
        index=pd.date_range("2026-01-01", periods=4, freq="1h", tz="UTC"),
    )


def test_candidate_count_counts_rules_not_parameter_variations():
    items = candidates()
    assert len(items) == 100
    assert len({(item["filter"], item["signal"]) for item in items}) == 100
    assert len({source_for(item) for item in items}) == 100
    assert all(item["kind"] == "research_hypothesis" and item["source_ids"] == [] for item in items)
    pilot = pilot_candidates()
    assert len(pilot) == 10
    assert len({item["filter"] for item in pilot}) == len({item["signal"] for item in pilot}) == 10
    for item in items:
        ast.parse(source_for(item))


def test_public_metadata_does_not_become_reproduced_rules(monkeypatch):
    renderer = {
        "lockupViewModel": {
            "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
            "contentId": "test-video",
            "metadata": {"lockupMetadataViewModel": {"title": {"content": "EMA + VWAP"}}},
        }
    }
    monkeypatch.setattr(
        sources,
        "read_url",
        lambda _: ("var ytInitialData = " + json.dumps(renderer) + ";").encode(),
    )
    registry = sources.collect_sources()
    assert len(registry["channels"]) == 6
    assert registry["sources"][0]["rules"] is None
    assert registry["sources"][0]["video_timestamps"] == []
    assert registry["sources"][0]["evidence_level"] == "public_listing_metadata_only"
    assert registry["sources"][0]["license"] == "unknown_no_code_reuse_authorized"


@pytest.mark.parametrize("mutation", ["missing_first", "missing_last", "duplicate", "out_of_order"])
def test_incomplete_requested_period_is_blocked(mutation):
    frame = candle_frame()
    if mutation == "missing_first":
        frame = frame.iloc[1:]
    elif mutation == "missing_last":
        frame = frame.iloc[:-1]
    elif mutation == "duplicate":
        frame = pd.concat([frame, frame.iloc[[-1]]])
    else:
        frame = frame.iloc[::-1]
    with pytest.raises(ValueError, match="기간 불일치"):
        validate_candles(
            frame, "1h", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-01T04:00Z")
        )


def test_impossible_high_and_nonfinite_price_are_blocked():
    frame = candle_frame()
    frame.iloc[0, frame.columns.get_loc("high")] = "98"
    with pytest.raises(ValueError, match="불변식"):
        validate_candles(
            frame, "1h", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-01T04:00Z")
        )
    frame = candle_frame()
    frame.iloc[0, frame.columns.get_loc("open")] = "inf"
    with pytest.raises(ValueError, match="숫자"):
        validate_candles(
            frame, "1h", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-01T04:00Z")
        )


def test_actual_funding_gap_is_blocked():
    start = pd.Timestamp("2026-01-01", tz="UTC")
    end = start + pd.Timedelta(days=1)
    funding = pd.Series(
        ["0.0001", "-0.0001"], index=pd.DatetimeIndex([start, start + pd.Timedelta(hours=16)])
    )
    with pytest.raises(ValueError, match="펀딩 정산 누락"):
        validate_funding(funding, start, end, 480)


def test_acceptance_rejects_small_sample_and_missing_cost_data():
    metrics = {
        "total_return": "0.05",
        "profit_factor": "1.2",
        "max_drawdown": "-0.25",
        "funding_data_incomplete": False,
    }
    assert cli.acceptance(metrics, 30)["passed"]
    assert not cli.acceptance(metrics, 29)["passed"]
    assert not cli.acceptance({**metrics, "max_drawdown": "-0.25001"}, 30)["passed"]
    assert cli.acceptance({**metrics, "funding_data_incomplete": None}, 30)["passed"]
    assert not cli.acceptance({**metrics, "funding_data_incomplete": True}, 30)["passed"]
    assert cli.acceptance(metrics, 30)["funding_status"] == "observed_settlements_only"
    assert not cli.acceptance({**metrics, "total_return": "0"}, 30)["passed"]


def test_development_never_overlaps_last_six_months():
    manifest = {"holdout_start": "2026-04-21T00:00:00Z", "end_exclusive": "2026-10-21T00:00:00Z"}
    cells = cli.cells(manifest)
    assert len(cells) * len(candidates()) == 1200
    assert all(
        pd.Timestamp(cell["end_exclusive"]) == pd.Timestamp(manifest["holdout_start"])
        for cell in cells
    )
    assert {cell["months"] for cell in cells} == {3, 6}


def test_resume_uses_final_record_after_interruption(tmp_path):
    journal = tmp_path / "journal.jsonl"
    cli.append_journal(journal, {"job_hash": "a", "status": "running"})
    cli.append_journal(journal, {"job_hash": "a", "status": "timeout"})
    assert cli.read_journal(journal) == {"a": {"job_hash": "a", "status": "timeout"}}


def test_resume_repairs_only_interrupted_tail_and_preserves_evidence(tmp_path):
    journal = tmp_path / "journal.jsonl"
    cli.append_journal(journal, {"job_hash": "a", "status": "completed"})
    with journal.open("ab") as stream:
        stream.write(b'{"job_hash":"b", "status": "run')
    assert set(cli.read_journal(journal)) == {"a"}
    cli.append_journal(journal, {"job_hash": "b", "status": "running"})
    assert set(cli.read_journal(journal)) == {"a", "b"}
    backups = list(tmp_path.glob("journal.jsonl.interrupted-*"))
    assert len(backups) == 1 and backups[0].read_bytes().endswith(b'"run')
    journal.write_bytes(b'{"broken":\n{"job_hash":"b","status":"running"}\n')
    with pytest.raises(ValueError, match="중간"):
        cli.read_journal(journal)


def test_batch_requires_successful_pilot_before_engine_access(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_dataset", lambda _: {})
    monkeypatch.setattr(
        cli, "engine_identity", lambda: pytest.fail("파일럿 전 격리 실행기를 시작하면 안 됩니다")
    )
    with pytest.raises(ValueError, match="pilot"):
        cli.run_batch(tmp_path, pilot=False)


def test_champion_cannot_be_reselected_after_holdout_opened(tmp_path):
    (tmp_path / "holdout-opened.json").write_text("{}")
    with pytest.raises(ValueError, match="한 번만"):
        cli.freeze_champion(tmp_path, "hyp-ema_trend-ema_cross", "BTCUSDT", "1h")
