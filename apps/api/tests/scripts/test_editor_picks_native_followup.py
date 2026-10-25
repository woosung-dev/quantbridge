"""후속 관측 선택·인증·결합의 경계를 전략 실행 없이 검사한다."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "native_followup", ROOT / "tools/scripts/editor-picks-native-followup.py"
)
followup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(followup)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / "research"
    root.mkdir()
    item = {"id": "source01", "source_sha256": "a" * 64, "warmup_bars": 1}
    frozen = {"dataset": {"end": "2026-01-10T00:00:00Z"}}
    provenance = {
        "head": followup.BASE_HEAD,
        "input_sha256": followup.BASE_INPUT,
        "plan_sha256": followup.PLAN_SHA,
        "images": {"pine": "pine-image", "python": "python-image"},
    }
    monkeypatch.setattr(followup, "base", lambda _: (frozen, {"items": [item]}, provenance))
    monkeypatch.setattr(followup, "checkout_head", lambda: followup.BASE_HEAD)
    monkeypatch.setattr(followup.verification, "native_reference", lambda *_: (b"source", {}))
    monkeypatch.setattr(followup.verification, "native_bindings", lambda _: [])
    monkeypatch.setattr(followup, "parse_native_capture", lambda raw, **kwargs: native(raw, kwargs))
    put(root / "full-plan.json", frozen)
    put(root / "cohort.json", {"items": [item]})
    put(
        root / "runtime/manifest.json",
        {"image_ids": {"pine": "pine-image"}, "files": {"runsc": "sha"}},
    )
    put(root / "runtime/source-proof.json", {"head": followup.BASE_HEAD})

    def captures(attempt, *, policy=None, popup=False, count=4):
        result = {}
        for tf in followup.TIMEFRAMES:
            path = put(
                root / f"native-followup-captures/source01/{attempt}/{tf}.json",
                {
                    "collection_policy": followup.NATIVE_POLICY if policy is None else policy,
                    "quota_popup_observed": popup,
                    "count": count,
                },
            )
            result[tf] = {"file": str(path.relative_to(root)), "sha256": followup.digest(path)}
        return result

    def freeze(candidates):
        ledger = put(root / "ledger.json", {"schema_version": 1, "candidates": candidates})
        selection_path = root / "selection.json"
        return followup.freeze(root, ledger, selection_path), selection_path

    return SimpleNamespace(
        root=root, item=item, frozen=frozen, provenance=provenance, captures=captures, freeze=freeze
    )


def native(raw, kwargs):
    assert kwargs["max_total_bars"] == 5000 and kwargs["require_full_prefix"] is True
    if raw["count"] > 5000:
        raise ValueError("5000 초과")
    frame = pd.DataFrame(
        index=pd.date_range("2026-01-01", periods=raw["count"], freq="h", tz="UTC")
    )
    return SimpleNamespace(
        ohlcv=frame,
        metadata={"price_first_bar": str(frame.index[0])},
        window_events=lambda *_: [
            SimpleNamespace(direction="long", bar_time=frame.index[1]),
            SimpleNamespace(direction="short", bar_time=frame.index[-1]),
        ],
    )


def test_first_collection_pass_is_frozen_and_failures_remain(case):
    failed = case.captures(0, popup=True)
    first = case.captures(1)
    later = case.captures(2)
    selection, _ = case.freeze(
        [{"id": "source01", "captures": value} for value in (failed, first, later)]
    )
    assert selection["selected"] == {"source01": 1}
    assert [value["status"] for value in selection["attempts"]] == [
        "collection_failed",
        "selected",
        "not_selected",
    ]
    followup.validate(case.root, selection)
    selection["selected"]["source01"] = 2
    with pytest.raises(ValueError, match="인덱스"):
        followup.validate(case.root, selection)


def test_collection_rejects_price_prefix_discarded_by_old_parser(case, monkeypatch):
    def truncated_prefix(raw, **kwargs):
        observation = native(raw, kwargs)
        observation.metadata["price_first_bar"] = str(
            observation.ohlcv.index[0] - pd.Timedelta(hours=24)
        )
        return observation

    monkeypatch.setattr(followup, "parse_native_capture", truncated_prefix)
    with pytest.raises(ValueError, match="통과한"):
        case.freeze([{"id": "source01", "captures": case.captures(0)}])


@pytest.mark.parametrize("kwargs", [{"count": 5001}, {"popup": True}, {"policy": {}}, {"count": 2}])
def test_collection_rejects_unsupported_observation(case, kwargs):
    with pytest.raises(ValueError, match="통과한"):
        case.freeze([{"id": "source01", "captures": case.captures(0, **kwargs)}])


def test_duplicate_unknown_and_missing_timeframe_are_not_promoted(case):
    captures = case.captures(0)
    with pytest.raises(ValueError, match="중복"):
        case.freeze([{"id": "source01", "captures": captures}] * 2)
    with pytest.raises(ValueError, match="코호트"):
        case.freeze([{"id": "unknown", "captures": captures}])
    with pytest.raises(ValueError, match="통과한"):
        case.freeze([{"id": "source01", "captures": {"1h": captures["1h"]}}])


def test_file_tamper_and_path_escape_fail_before_selection(case):
    captures = case.captures(0)
    (case.root / captures["1h"]["file"]).write_text("tamper")
    with pytest.raises(ValueError):
        case.freeze([{"id": "source01", "captures": captures}])
    captures["1h"]["file"] = "../outside.json"
    with pytest.raises(ValueError):
        case.freeze([{"id": "source01", "captures": captures}])


def test_pack_prepare_roundtrip_keeps_failed_raw_and_rejects_extra(case, tmp_path):
    selected, path = case.freeze(
        [
            {"id": "source01", "captures": case.captures(0, popup=True)},
            {"id": "source01", "captures": case.captures(1)},
        ]
    )
    archive = tmp_path / "overlay.tar.gz"
    proof = followup.pack(case.root, path, archive)
    incoming = tmp_path / "incoming"
    followup.safe_extract(archive, incoming)
    assert proof["selection_sha256"] == followup.identity(selected)
    assert list((incoming / "captures").glob("*.json"))
    followup.prepare(case.root, incoming, proof["selection_sha256"])
    put(incoming / "not-listed.json", {})
    with pytest.raises(ValueError, match="미등재"):
        followup.prepare(case.root, incoming, proof["selection_sha256"])


def test_external_failure_references_are_preserved_without_opening_or_embedding(case, tmp_path):
    reference = {
        "file": "editor-picks-20261025-expansion-v5/browser-queue/native-105.result.json",
        "sha256": "b" * 64,
    }
    selection, path = case.freeze(
        [{"id": "source01", "captures": case.captures(0), "prior_evidence": [reference]}]
    )
    assert selection["external_evidence_references_not_embedded"] is True
    assert selection["attempts"][0]["prior_evidence"] == [reference]
    archive = tmp_path / "reference-only.tar.gz"
    followup.pack(case.root, path, archive)
    with tarfile.open(archive) as packed:
        assert reference["file"] not in packed.getnames()
        assert all(
            name == "selection.json" or name.startswith("captures/") for name in packed.getnames()
        )


@pytest.mark.parametrize(
    "name",
    [
        "/private/raw.json",
        "../raw.json",
        "another-run/raw.json",
        "editor-picks-20261025-expansion-v5/../raw.json",
    ],
)
def test_external_failure_reference_path_is_not_arbitrary(case, name):
    with pytest.raises(ValueError, match="외부"):
        case.freeze(
            [
                {
                    "id": "source01",
                    "captures": case.captures(0),
                    "prior_evidence": [{"file": name, "sha256": "b" * 64}],
                }
            ]
        )


def make_result(case, tmp_path):
    selection, path = case.freeze([{"id": "source01", "captures": case.captures(0)}])
    incoming = tmp_path / "result"
    incoming.mkdir()
    put(incoming / "selection.json", selection)
    put(
        incoming / "terminal.json",
        {
            "run_id": "100",
            "attempt": "1",
            "control_head": followup.BASE_HEAD,
            "selection_sha256": followup.identity(selection),
            "base": selection["base"],
            "helper_sha256": selection["helper_sha256"],
            "returncodes": {"source01": 0},
        },
    )
    put(
        incoming / "runtime-installed.json",
        {
            "images": {"pine": "pine-image"},
            "runtime": {"runsc": "sha"},
            "source_proof": {"head": followup.BASE_HEAD},
        },
    )
    put(
        incoming / "source01.json",
        {
            "id": "source01",
            "source_sha256": case.item["source_sha256"],
            "plan_sha256": followup.PLAN_SHA,
            "images": selection["base"]["images"],
            "native_windows": {
                tf: {
                    "status": "checked_partial_window",
                    "capture_sha256": selection["attempts"][0]["captures"][tf]["sha256"],
                }
                for tf in followup.TIMEFRAMES
            },
        },
    )
    (incoming / "source01.log").write_text("실제 subprocess 로그 대역")
    seal(incoming)
    return incoming, selection, path


def seal(incoming):
    put(
        incoming / "envelope.json",
        {
            "run_id": "100",
            "attempt": "1",
            "files": {
                path.name: followup.digest(path)
                for path in incoming.iterdir()
                if path.name != "envelope.json"
            },
        },
    )


@pytest.mark.parametrize("change", ["plan", "image", "source", "capture", "missing", "code"])
def test_authenticated_result_rechecks_semantic_gates(case, tmp_path, change):
    incoming, _, selection = make_result(case, tmp_path)
    proof = followup.read(incoming / "source01.json")
    if change == "plan":
        proof["plan_sha256"] = "other"
    if change == "image":
        proof["images"]["pine"] = "other"
    if change == "source":
        proof["source_sha256"] = "other"
    if change == "capture":
        proof["native_windows"]["1h"]["capture_sha256"] = "other"
    put(incoming / "source01.json", proof)
    if change == "missing":
        (incoming / "source01.json").unlink()
    if change == "code":
        terminal = followup.read(incoming / "terminal.json")
        terminal["returncodes"]["source01"] = True
        put(incoming / "terminal.json", terminal)
    seal(incoming)
    with pytest.raises(ValueError):
        followup.collect(case.root, incoming, "100", "1", selection)
    assert not (case.root / followup.namespace("100", "1")).exists()


def test_collect_is_immutable_and_bundle_lists_exact_evidence(case, tmp_path):
    incoming, _, selection = make_result(case, tmp_path)
    destination = followup.collect(case.root, incoming, "100", "1", selection)
    before = followup.digest(destination / "envelope.json")
    with pytest.raises(FileExistsError):
        followup.collect(case.root, incoming, "100", "1", selection)
    assert followup.digest(destination / "envelope.json") == before
    with pytest.raises(ValueError):
        followup.collect(case.root, incoming, "101", "1", selection)


def test_wrong_cipher_hash_and_authentication_never_unpack(case, tmp_path, monkeypatch):
    source = tmp_path / "input.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        archive.add(case.root / "full-plan.json", arcname="full-plan.json")
    cipher = tmp_path / "input.enc"
    key = b"k" * 32
    followup.transform("encrypt", source, cipher, key, "context")
    monkeypatch.setenv("EDITOR_PICKS_RESEARCH_KEY", __import__("base64").b64encode(key).decode())
    with pytest.raises(ValueError):
        followup.unpack(cipher, "0" * 64, "EDITOR_PICKS_RESEARCH_KEY", "context", tmp_path / "out")
    from cryptography.exceptions import InvalidTag

    with pytest.raises(InvalidTag):
        followup.unpack(
            cipher, followup.digest(cipher), "EDITOR_PICKS_RESEARCH_KEY", "other", tmp_path / "out"
        )
    assert not (tmp_path / "out").exists()


def test_worker_refuses_economic_results_or_another_checkout(case, monkeypatch):
    selection, _ = case.freeze([{"id": "source01", "captures": case.captures(0)}])
    put(case.root / "native-followup-selection.json", selection)
    monkeypatch.setattr(followup, "require_runtime", lambda: selection["base"]["images"])
    (case.root / "results").mkdir()
    with pytest.raises(ValueError):
        followup.worker(case.root, "100", "1", followup.BASE_HEAD)
    (case.root / "results").rmdir()
    monkeypatch.setattr(followup, "checkout_head", lambda: "other")
    with pytest.raises(ValueError):
        followup.worker(case.root, "100", "1", followup.BASE_HEAD)


def test_derive_rejects_incomplete_economy_before_any_copy(case, tmp_path):
    final = put(case.root / "final.json", {"complete": False})
    with pytest.raises(ValueError, match="경제"):
        followup.derive(case.root, tmp_path / "derived", [], final)
    assert not (tmp_path / "derived").exists()


def test_worker_uses_only_verify_with_sanitized_environment(case, monkeypatch, tmp_path):
    incoming, selection, _ = make_result(case, tmp_path)
    put(case.root / "native-followup-selection.json", selection)
    shutil.copyfile(incoming / "runtime-installed.json", case.root / "runtime-installed.json")
    monkeypatch.setattr(followup, "require_runtime", lambda: selection["base"]["images"])
    monkeypatch.setenv("GH_TOKEN", "test-secret-not-forwarded")
    calls = []

    def verify_only(command, **kwargs):
        assert command[1:3] == ["-m", "tools.research.editor_picks"]
        assert command[5] == "verify"
        assert "execute" not in command
        assert set(kwargs["env"]) <= {
            "PATH",
            "HOME",
            "LANG",
            "TRADING_ENCRYPTION_KEYS",
            "PINE_AST_CACHE_DIR",
        }
        assert "GH_TOKEN" not in kwargs["env"]
        destination = case.root / "verification/source01.json"
        destination.parent.mkdir()
        shutil.copyfile(incoming / "source01.json", destination)
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(followup.subprocess, "run", verify_only)
    terminal = followup.worker(case.root, "100", "1", followup.BASE_HEAD)
    assert terminal["returncodes"] == {"source01": 0}
    assert len(calls) == 1
    archive = tmp_path / "result.tar.gz"
    followup.bundle(case.root, "100", "1", archive)
    with tarfile.open(archive) as packed:
        assert set(packed.getnames()) == {
            "terminal.json",
            "selection.json",
            "runtime-installed.json",
            "source01.json",
            "source01.log",
            "envelope.json",
        }


def economic_final(case):
    provenance = {
        "head": followup.BASE_HEAD,
        "input_sha256": followup.BASE_INPUT,
        "run_id": "40151197662",
        "attempt": "1",
        "plan": "full-plan.json",
        "plan_sha256": followup.PLAN_SHA,
        "shards": 20,
    }
    prefix = case.root / followup.remote_namespace(provenance)
    for shard in range(20):
        path = put(case.root / f"raw/{shard}.json", {"original": shard})
        put(
            prefix / str(shard) / "envelope.json",
            {
                **provenance,
                "shard": shard,
                "files": {str(path.relative_to(case.root)): followup.digest(path)},
            },
        )
    return put(
        prefix / "finalization.json", {"complete": True, "failures": [], "provenance": provenance}
    )


@pytest.mark.parametrize("platform", ("darwin", "linux"))
def test_derive_reuses_existing_reconcile_export_in_separate_root(
    case, tmp_path, monkeypatch, platform
):
    incoming, _, selection_path = make_result(case, tmp_path)
    prefix = followup.collect(case.root, incoming, "100", "1", selection_path)
    final = economic_final(case)
    old = put(case.root / "native-checks/source01.json", {"old": True})
    before = followup.digest(old)
    destination = tmp_path / "derived"
    calls = []
    clone_calls = []
    monkeypatch.setattr(followup.sys, "platform", platform)

    def clone_only(command, **kwargs):
        assert platform == "darwin"
        assert command == ["/bin/cp", "-cR", str(case.root), str(destination)]
        assert kwargs == {"check": True}
        shutil.copytree(case.root, destination)
        clone_calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(followup.subprocess, "run", clone_only)
    monkeypatch.setattr(followup, "install_projection", lambda: None)
    monkeypatch.setattr(
        followup.verification, "reconcile", lambda *args: calls.append(("reconcile", args))
    )
    monkeypatch.setattr(
        followup.verification,
        "export",
        lambda *args: calls.append(("export", args)) or {"count": 0},
    )
    value = followup.derive(
        case.root,
        destination,
        [
            {
                "run_id": "100",
                "attempt": "1",
                "envelope_sha256": followup.digest(prefix / "envelope.json"),
            }
        ],
        final,
    )
    assert [name for name, _ in calls] == ["reconcile", "export"]
    assert all(args == (destination, destination / "full-plan.json") for _, args in calls)
    assert followup.digest(old) == before
    assert followup.read(destination / "native-checks/source01.json")["id"] == "source01"
    assert len(value["economic_envelopes_sha256"]) == 20
    assert len(clone_calls) == (1 if platform == "darwin" else 0)


def test_derive_rejects_old_economic_raw_tamper_before_clone(case, tmp_path):
    final = economic_final(case)
    put(case.root / "raw/19.json", {"tamper": True})
    with pytest.raises(ValueError):
        followup.derive(case.root, tmp_path / "derived", [], final)
    assert not (tmp_path / "derived").exists()


def test_cli_preserves_nonzero_actual_verify_exit(case, monkeypatch):
    monkeypatch.setattr(followup, "worker", lambda *_: {"returncodes": {"source01": 1}})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "followup",
            "worker",
            "--run-dir",
            str(case.root),
            "--run-id",
            "100",
            "--attempt",
            "1",
            "--control-head",
            followup.BASE_HEAD,
        ],
    )
    with pytest.raises(SystemExit) as error:
        followup.main()
    assert error.value.code == 1


def test_cli_bootstraps_isolated_config_without_production_credentials():
    env = {name: value for name, value in os.environ.items() if name in {"PATH", "HOME", "LANG"}}
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/scripts/editor-picks-native-followup.py"), "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--run-dir" in result.stdout
    assert "Field required" not in result.stderr
