"""오프라인 검증 CLI의 실패 판정·전체 표본 분모·시간창을 확인한다."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import validate_pine_signals as V
from scripts.pine_validation.models import SignalEvent

SOURCE = '//@version=5\nindicator("Fixture")\nplotshape(close > open)\nplotshape(close < open)\n'


def fixture_manifest(
    directory: Path,
    count: int = 1,
    days: int = 4,
    *,
    start: datetime | None = None,
    sparse: bool = False,
) -> Path:
    start = start or datetime(2020, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=days)
    (directory / "source.pine").write_text(SOURCE)
    csv_files, references = {}, {}
    for timeframe, seconds in V.TIMEFRAMES.items():
        times = pd.date_range(start, end, freq=pd.Timedelta(seconds=seconds), inclusive="left")
        frame = pd.DataFrame(
            {
                "time": [at.isoformat() for at in times],
                "open": 100,
                "high": 102,
                "low": 98,
                "close": [
                    100 if sparse and i > 1 else 101 if i % 2 == 0 else 99
                    for i in range(len(times))
                ],
                "volume": 1,
            }
        )
        csv_files[timeframe] = f"{timeframe}.csv"
        frame.to_csv(directory / csv_files[timeframe], index=False)
        references[timeframe] = f"{timeframe}.events.json"
        events = [
            {
                "bar_time": at.isoformat(),
                "direction": "long" if i % 2 == 0 else "short",
                "confirmed_at": (at + pd.Timedelta(seconds=seconds)).isoformat(),
                "display_time": at.isoformat(),
            }
            for i, at in enumerate(times)
            if not sparse or i < 2
        ]
        (directory / references[timeframe]).write_text(
            json.dumps(
                {
                    "events": events,
                    "provenance": {
                        "kind": "native_original",
                        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
                        "native_original_verified": True,
                        "symbol": "BYBIT:BTCUSDT.P",
                        "timeframe": timeframe,
                        "inputs": {},
                        "window": {"start": start.isoformat(), "end": end.isoformat()},
                    },
                }
            )
        )
    items = []
    for index in range(count):
        source = SOURCE if index == 0 else SOURCE + f"// Fixture publication {index}\n"
        source_file = "source.pine" if index == 0 else f"source-{index}.pine"
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        (directory / source_file).write_text(source)
        item_references = references.copy()
        if index:
            for timeframe, filename in references.items():
                payload = json.loads((directory / filename).read_text())
                payload["provenance"]["source_sha256"] = source_hash
                item_references[timeframe] = f"{timeframe}-{index}.events.json"
                (directory / item_references[timeframe]).write_text(json.dumps(payload))
        items.append(
            {
                "id": f"fixture-{index}",
                "title": f"Fixture {index}",
                "url": f"https://www.tradingview.com/script/TEST{index:04d}-Fixture/",
                "author": "fixture",
                "boosts": 100,
                "observed_at": "2020-01-06T00:00:00Z",
                "source_file": source_file,
                "source_sha256": source_hash,
                "signal_bindings": [
                    {"function": "plotshape", "line": 3, "direction": "long"},
                    {"function": "plotshape", "line": 4, "direction": "short"},
                ],
                "oracle": "fixture",
                "inputs": {},
                "params": {},
                "tv_events": item_references,
            }
        )
    path = directory / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "symbol": "BYBIT:BTCUSDT.P",
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "ohlcv": csv_files,
                "indicators": items,
            }
        )
    )
    return path


def fake_execute(source, frame, inputs, timeframe):
    trace = []
    for index, (at, row) in enumerate(frame.iterrows()):
        for line, active in ((3, row["close"] > row["open"]), (4, row["close"] < row["open"])):
            trace.append(
                SimpleNamespace(
                    function="plotshape",
                    source_line=line,
                    source_column=0,
                    bar_index=index,
                    bar_open_time=at.to_pydatetime(),
                    value=bool(active),
                    marker_offset=0,
                )
            )
    return SimpleNamespace(signal_trace=trace, errors=[], bars_processed=len(frame))


def fake_oracle(name, frame, params):
    step = frame.index[1] - frame.index[0]
    return [
        SignalEvent(
            at.to_pydatetime(),
            "long" if row["close"] > row["open"] else "short",
            confirmed_at=(at + step).to_pydatetime(),
            display_time=at.to_pydatetime(),
        )
        for at, row in frame.iterrows()
        if row["close"] != row["open"]
    ]


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(V, "execute_pine", fake_execute)
    monkeypatch.setattr(V, "compute_oracle", fake_oracle)
    monkeypatch.setattr(V, "compare_app_backtest", lambda *args, **kwargs: {"status": "exact_match"})


def test_app_backtest_mismatch_blocks_validation(tmp_path, offline, monkeypatch):
    path = fixture_manifest(tmp_path)
    monkeypatch.setattr(V, "compare_app_backtest", lambda *args, **kwargs: {"status": "mismatch"})
    report = V.run_validation(path)
    assert report["app_backtest_exact_pairs"] == 0
    assert all(row["status"] == "app_mismatch" for row in report["results"])
    assert all("app_mismatch" in row["failures"] for row in report["results"])


def test_app_backtest_receives_whole_warmup_history(tmp_path, offline, monkeypatch):
    path = fixture_manifest(tmp_path)
    for timeframe, seconds in V.TIMEFRAMES.items():
        filename = tmp_path / f"{timeframe}.csv"
        frame = pd.read_csv(filename)
        warmup = frame.iloc[[0]].copy()
        warmup["time"] = (pd.Timestamp(frame.iloc[0]["time"]) - pd.Timedelta(seconds=seconds)).isoformat()
        pd.concat([warmup, frame]).to_csv(filename, index=False)
    observed = []

    def compare(source, frame, inputs, timeframe, events, *, window_start, window_end):
        assert "strategy(" in source
        assert inputs == {}
        assert frame.index[0] < window_start
        assert events[0].bar_time == frame.index[0]
        observed.append(timeframe)
        return {"status": "exact_match"}

    monkeypatch.setattr(V, "compare_app_backtest", compare)
    report = V.run_validation(path)
    assert observed == list(V.TIMEFRAMES)
    assert report["app_backtest_exact_pairs"] == 3


def test_ten_indicators_and_all_three_timeframes_are_required(tmp_path, offline):
    start, cutoff = V.required_window()
    path = fixture_manifest(
        tmp_path, count=10, days=(cutoff - start).days, start=start, sparse=True
    )
    report = V.run_validation(path)
    assert report["status"] == "passed"
    assert (report["expected_pairs"], report["evaluated_pairs"], report["exact_pairs"]) == (
        30,
        30,
        30,
    )
    partial = V.run_validation(path, limit=9)
    assert partial["status"] == "incomplete"
    assert (partial["expected_pairs"], partial["evaluated_pairs"], partial["exact_pairs"]) == (
        30,
        27,
        27,
    )


def test_small_fixture_window_never_satisfies_strict_completion(tmp_path, offline):
    path = fixture_manifest(tmp_path, count=10)
    report = V.run_validation(path)
    assert report["exact_pairs"] == 30
    assert report["status"] == "incomplete"
    assert report["completion_failures"] == ["window_not_recent_calendar_year"]


def test_duplicate_sources_remain_diagnostic_rows_and_cannot_fill_the_denominator(
    tmp_path, monkeypatch
):
    path = fixture_manifest(tmp_path, count=10)
    data = json.loads(path.read_text())
    start, end = V.required_window()
    data["window"] = {"start": start.isoformat(), "end": end.isoformat()}
    data["indicators"][1]["source_sha256"] = data["indicators"][0]["source_sha256"]
    path.write_text(json.dumps(data))
    monkeypatch.setattr(
        V,
        "validate_cell",
        lambda item, tf, manifest, base: {
            "indicator_id": item["id"],
            "timeframe": tf,
            "status": "exact_match",
            "failures": [],
        },
    )
    report = V.run_validation(path)
    assert report["status"] == "incomplete"
    assert report["evaluated_pairs"] == 30
    assert report["exact_pairs"] == 27
    assert report["unique_sources"] == 9
    assert "duplicate_sources" in report["completion_failures"]
    assert {
        row["duplicate_source_of"] for row in report["results"] if "duplicate_source_of" in row
    } == {"fixture-0"}


def test_calendar_year_window_uses_last_closed_utc_daily_bar():
    assert V.required_window(datetime(2026, 10, 20, 15, tzinfo=UTC)) == (
        datetime(2025, 10, 20, tzinfo=UTC),
        datetime(2026, 10, 20, tzinfo=UTC),
    )


def test_url_query_variants_cannot_inflate_distinct_publications(tmp_path):
    path = fixture_manifest(tmp_path, count=10)
    data = json.loads(path.read_text())
    for index, item in enumerate(data["indicators"]):
        item["url"] = f"https://www.tradingview.com/script/ABC12345?variant={index}"
    path.write_text(json.dumps(data))
    with pytest.raises(V.ManifestError, match="publication id"):
        V.run_validation(path)


@pytest.mark.parametrize("missing", ["ohlcv", "tv_events", "oracle"])
def test_missing_evidence_never_counts_as_exact(tmp_path, offline, missing):
    path = fixture_manifest(tmp_path)
    data = json.loads(path.read_text())
    if missing == "ohlcv":
        data["ohlcv"] = {}
    else:
        data["indicators"][0][missing] = {} if missing == "tv_events" else None
    path.write_text(json.dumps(data))
    report = V.run_validation(path)
    assert report["status"] == "incomplete"
    assert report["exact_pairs"] == 0
    assert all(row["status"].startswith("missing_") for row in report["results"])


@pytest.mark.parametrize(
    "mode", ["missing", "derived_probe", "wrong_hash", "reviewed_unverified", "reviewed_verified"]
)
def test_tv_provenance_keeps_derived_and_unverified_references_out_of_exact(
    tmp_path, offline, mode
):
    path = fixture_manifest(tmp_path)
    data = json.loads(path.read_text())
    for filename in data["indicators"][0]["tv_events"].values():
        reference = tmp_path / filename
        payload = json.loads(reference.read_text())
        if mode == "missing":
            payload = payload["events"]
        elif mode == "derived_probe":
            payload["provenance"]["kind"] = "derived_probe"
        elif mode == "wrong_hash":
            payload["provenance"]["source_sha256"] = "0" * 64
        else:
            payload["provenance"].update(
                kind="reviewed_port", native_original_verified=mode == "reviewed_verified"
            )
        reference.write_text(json.dumps(payload))
    report = V.run_validation(path)
    assert all(row["tv_pine"]["status"] == "exact_match" for row in report["results"])
    expected = "exact_match" if mode == "reviewed_verified" else "unverified_tv_reference"
    assert {row["status"] for row in report["results"]} == {expected}


@pytest.mark.parametrize("field", ["symbol", "timeframe", "inputs", "window"])
@pytest.mark.parametrize("missing", [False, True])
def test_wrong_or_missing_tv_context_never_counts_as_exact(tmp_path, offline, field, missing):
    path = fixture_manifest(tmp_path)
    data = json.loads(path.read_text())
    replacements = {
        "symbol": "BYBIT:ETHUSDT.P",
        "timeframe": "5m",
        "inputs": {"h": True},
        "window": {"start": "2020-01-02T00:00:00Z", "end": "2020-01-05T00:00:00Z"},
    }
    for filename in data["indicators"][0]["tv_events"].values():
        reference = tmp_path / filename
        payload = json.loads(reference.read_text())
        if missing:
            del payload["provenance"][field]
        else:
            payload["provenance"][field] = replacements[field]
        reference.write_text(json.dumps(payload))
    report = V.run_validation(path)
    assert all(row["tv_pine"]["status"] == "exact_match" for row in report["results"])
    assert {row["status"] for row in report["results"]} == {"unverified_tv_reference"}


@pytest.mark.parametrize(
    "change,status",
    [("hash", "source_hash_mismatch"), ("boosts", "insufficient_boosts"), ("gap", "invalid_ohlcv")],
)
def test_source_eligibility_and_complete_ohlcv_are_checked(tmp_path, offline, change, status):
    path = fixture_manifest(tmp_path)
    data = json.loads(path.read_text())
    if change == "hash":
        data["indicators"][0]["source_sha256"] = "0" * 64
    elif change == "boosts":
        data["indicators"][0]["boosts"] = 99
    else:
        for filename in data["ohlcv"].values():
            frame = pd.read_csv(tmp_path / filename).drop(index=1)
            frame.to_csv(tmp_path / filename, index=False)
    path.write_text(json.dumps(data))
    assert {row["status"] for row in V.run_validation(path)["results"]} == {status}


@pytest.mark.parametrize(
    ("extra_source", "status"),
    [
        ("period = timeframe.period\n", "exact_match"),
        (
            'other = request.security(syminfo.tickerid, "D", close)\n',
            "missing_degraded_execution_evidence",
        ),
    ],
)
def test_explicit_timeframe_context_only_resolves_period_degradation(
    tmp_path, offline, extra_source, status
):
    path = fixture_manifest(tmp_path)
    source = SOURCE + extra_source
    (tmp_path / "source.pine").write_text(source)
    data = json.loads(path.read_text())
    data["indicators"][0]["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    for filename in data["indicators"][0]["tv_events"].values():
        reference = tmp_path / filename
        payload = json.loads(reference.read_text())
        payload["provenance"]["source_sha256"] = data["indicators"][0]["source_sha256"]
        reference.write_text(json.dumps(payload))
    path.write_text(json.dumps(data))
    assert {row["status"] for row in V.run_validation(path)["results"]} == {status}


def test_no_signal_and_one_sided_signal_cannot_pass(tmp_path, offline, monkeypatch):
    path = fixture_manifest(tmp_path)
    for direction in (None, "long"):

        def execute(source, frame, inputs, timeframe):
            result = fake_execute(source, frame, inputs, timeframe)
            for event in result.signal_trace:
                event.value = direction == "long" and event.source_line == 3
            return result

        monkeypatch.setattr(V, "execute_pine", execute)
        report = V.run_validation(path)
        assert report["exact_pairs"] == 0
        required = "no_signal" if direction is None else "one_sided_signal"
        assert all(required in row["failures"] for row in report["results"])


def test_binding_preserves_evaluation_and_offset_display_times():
    at = datetime(2020, 1, 1, tzinfo=UTC)
    trace = [
        SimpleNamespace(
            function="plotarrow",
            source_line=3,
            source_column=0,
            bar_open_time=at,
            value=value,
            marker_offset=-2,
        )
        for value in (None, float("nan"), False, 0, True, 2, -3)
    ]
    events = V.bind_events(
        trace,
        [{"function": "plotarrow", "line": 3, "direction": "short", "when": "negative"}],
        "1h",
    )
    assert len(events) == 1
    assert events[0].bar_time == at
    assert events[0].confirmed_at == at + timedelta(hours=1)
    assert events[0].display_time == at - timedelta(hours=2)


def test_window_end_is_closed_bar_cutoff(tmp_path):
    path = fixture_manifest(tmp_path)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    cutoff = start + timedelta(hours=2, minutes=30)
    frame = V.load_ohlcv(path.parent / "1h.csv", "1h", start, cutoff)
    assert list(frame.index) == [pd.Timestamp(start), pd.Timestamp(start + timedelta(hours=1))]


@pytest.mark.parametrize(
    "window",
    [
        {},
        {"start": "2020-01-01", "end": "2020-01-05"},
        {"start": "2020-01-05T00:00:00Z", "end": "2020-01-01T00:00:00Z"},
    ],
)
def test_invalid_window_is_manifest_error(tmp_path, window):
    path = fixture_manifest(tmp_path)
    data = json.loads(path.read_text())
    data["window"] = window
    path.write_text(json.dumps(data))
    with pytest.raises(V.ManifestError):
        V.run_validation(path)


def test_unclosed_daily_cutoff_is_rejected_before_execution(tmp_path):
    path = fixture_manifest(tmp_path)
    data = json.loads(path.read_text())
    data["window"]["end"] = (V.required_window()[1] + timedelta(hours=1)).isoformat()
    path.write_text(json.dumps(data))
    with pytest.raises(V.ManifestError, match="cutoff"):
        V.run_validation(path)


def test_cli_writes_report_and_keeps_small_fixture_incomplete(tmp_path, offline, monkeypatch):
    path = fixture_manifest(tmp_path)
    runs = tmp_path / "runs"
    monkeypatch.setattr(V, "RUNS_DIR", runs)
    output = runs / "validation"
    assert V.main(["--manifest", str(path), "--output", str(output)]) == 1
    assert json.loads((output / "report.json").read_text())["exact_pairs"] == 3
    assert "전체 30개 중 일치 3개" in (output / "summary.md").read_text()
    with pytest.raises(SystemExit) as exc:
        V.main(["--manifest", str(path), "--output", str(tmp_path / "outside")])
    assert exc.value.code == 2


def test_real_pine_signal_trace_is_used_without_state_buffer(tmp_path, monkeypatch):
    path = fixture_manifest(tmp_path, days=24)
    monkeypatch.setattr(V, "compute_oracle", fake_oracle)
    report = V.run_validation(path)
    assert report["exact_pairs"] == 3
    assert len(report["results"][0]["pine_events"]) == 576


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_cannot_expand_outside_the_bounded_batch(tmp_path, limit):
    path = fixture_manifest(tmp_path)
    with pytest.raises(V.ManifestError, match="limit"):
        V.run_validation(path, limit=limit)


def test_cli_invalid_manifest_writes_failure_artifacts_with_exit_two(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text('{"version": 1}')
    runs = tmp_path / "runs"
    monkeypatch.setattr(V, "RUNS_DIR", runs)
    output = runs / "invalid"
    assert V.main(["--manifest", str(path), "--output", str(output)]) == 2
    assert json.loads((output / "report.json").read_text())["status"] == "invalid_manifest"


@pytest.fixture
def runtime_degraded_manifest(tmp_path):
    path = fixture_manifest(tmp_path)
    source = SOURCE + (
        'h = input(false)\nother = h ? security(heikinashi(syminfo.tickerid), "D", close) : close\n'
    )
    (tmp_path / "source.pine").write_text(source)
    data = json.loads(path.read_text())
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    data["indicators"][0]["source_sha256"] = source_hash
    for filename in data["indicators"][0]["tv_events"].values():
        reference = tmp_path / filename
        payload = json.loads(reference.read_text())
        payload["provenance"]["source_sha256"] = source_hash
        reference.write_text(json.dumps(payload))
    path.write_text(json.dumps(data))
    return path


def test_static_degraded_without_runtime_evidence_fails_closed(runtime_degraded_manifest, offline):
    report = V.run_validation(runtime_degraded_manifest)
    assert report["exact_pairs"] == 0
    assert {row["status"] for row in report["results"]} == {"missing_degraded_execution_evidence"}
    assert all("unexecuted_degraded_calls" not in row for row in report["results"])


def test_executed_degraded_call_rejects_matching_signals(
    runtime_degraded_manifest, offline, monkeypatch
):
    def execute(source, frame, inputs, timeframe):
        result = fake_execute(source, frame, inputs, timeframe)
        result.degraded_calls_seen = ["request.security"]
        return result

    monkeypatch.setattr(V, "execute_pine", execute)
    report = V.run_validation(runtime_degraded_manifest)
    assert report["exact_pairs"] == 0
    assert {row["status"] for row in report["results"]} == {"degraded_pine_executed"}
    assert all(row["degraded_calls_seen"] == ["request.security"] for row in report["results"])
    assert all("pine_events" not in row for row in report["results"])


def test_real_unexecuted_degraded_branch_has_explicit_empty_runtime_evidence(
    runtime_degraded_manifest, monkeypatch
):
    monkeypatch.setattr(V, "compute_oracle", fake_oracle)
    report = V.run_validation(runtime_degraded_manifest)
    assert report["exact_pairs"] == 0
    assert {row["status"] for row in report["results"]} == {"unreviewed_degraded_branch"}
    assert all(row["degraded_calls_seen"] == [] for row in report["results"])
    assert all("unexecuted_degraded_calls" not in row for row in report["results"])


def test_static_unsupported_remains_blocked_before_runtime(runtime_degraded_manifest, monkeypatch):
    path = runtime_degraded_manifest
    source_path = path.parent / "source.pine"
    source = source_path.read_text() + "unknown = request.unsupported(close)\n"
    source_path.write_text(source)
    data = json.loads(path.read_text())
    data["indicators"][0]["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    path.write_text(json.dumps(data))

    def execute(*args, **kwargs):
        pytest.fail("정적 미지원 Pine은 인터프리터 실행 전에 거부되어야 합니다")

    monkeypatch.setattr(V, "execute_pine", execute)
    report = V.run_validation(path)
    assert report["exact_pairs"] == 0
    assert {row["status"] for row in report["results"]} == {"unsupported_pine"}
    assert all("request.unsupported" in row["unsupported"] for row in report["results"])


def test_reviewed_source_hash_and_false_default_allow_only_proven_unexecuted_branch(
    runtime_degraded_manifest, monkeypatch
):
    data = json.loads(runtime_degraded_manifest.read_text())
    monkeypatch.setattr(V, "_REVIEWED_UTBOT_SHA256", data["indicators"][0]["source_sha256"])
    monkeypatch.setattr(V, "compute_oracle", fake_oracle)
    report = V.run_validation(runtime_degraded_manifest)
    assert report["exact_pairs"] == 3
    assert all(row["degraded_calls_seen"] == [] for row in report["results"])
    assert all(
        row["unexecuted_degraded_calls"] == ["heikinashi", "security"] for row in report["results"]
    )


@pytest.mark.parametrize("override", [0, None])
def test_reviewed_hash_does_not_accept_non_boolean_false_input(
    runtime_degraded_manifest, monkeypatch, override
):
    data = json.loads(runtime_degraded_manifest.read_text())
    data["indicators"][0]["inputs"] = {"h": override}
    runtime_degraded_manifest.write_text(json.dumps(data))
    monkeypatch.setattr(V, "_REVIEWED_UTBOT_SHA256", data["indicators"][0]["source_sha256"])
    report = V.run_validation(runtime_degraded_manifest)
    assert report["exact_pairs"] == 0
    assert {row["status"] for row in report["results"]} == {"unreviewed_degraded_branch"}
