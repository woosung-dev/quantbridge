"""원 데이터/서버 없이 parser preflight의 권한·입력·해시 비교를 검사한다."""

from copy import deepcopy
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


h = module("original_data_preflight_boundary", ROOT / "sol_economic_data_preflight.py")
p = module("original_data_probe_boundary", ROOT / "sol_economic_data_probe.py")


def write(path, value):
    path.write_text(json.dumps(value))


def event():
    return {
        "action": "labeled",
        "number": 925,
        "repository": {"private": False},
        "label": {"name": "sol-economic-data-preflight"},
        "pull_request": {
            "number": 925,
            "user": {"login": "woosung-dev"},
            "head": {
                "ref": "stage/sol-research-arm-runners",
                "repo": {"full_name": h.arm.REPOSITORY},
            },
            "base": {"ref": "stage/sol-strategy-lab"},
        },
    }


def cells(_):
    return [
        {
            "id": f"{family}/{symbol}/{tf}",
            "family": family,
            "symbol": symbol,
            "timeframe": tf,
            "start": "synthetic-start",
            "end": "synthetic-end",
            "execution": family == "minute_execution",
        }
        for family in ("historical_parent", "minute_execution")
        for symbol in ("BTCUSDT", "ETHUSDT")
        for tf in ("1h", "4h", "1d")
    ]


def report(system):
    return {
        "schema_version": 1,
        "status": "DATA_HASHES_ONLY_NO_ECONOMICS",
        "cells": [
            {
                "cell": cell,
                "hashes": {
                    "parent": "a" * 64,
                    "funding_observed": "b" * 64,
                    "execution": "c" * 64 if cell["execution"] else None,
                },
                "rows": [2, 1, 3 if cell["execution"] else None],
            }
            for cell in cells(None)
        ],
        "snapshot_sha256": h.SNAPSHOT_SHA,
        "probe_sha256": h.PROBE_SHA,
        "data_source_sha256": p.DATA_SHA,
        "economics_source_sha256": p.ECONOMICS_SHA,
        "python": "3.12.12",
        "packages": {"numpy": "synthetic", "pandas": "synthetic"},
        "machine": "arm64" if system == "Darwin" else "aarch64",
        "system": system,
        "native_calls": 0,
        "selection_read": False,
        "historical_daily_loaded_for_parser_check_only": True,
    }


class DataPreflightTests(unittest.TestCase):
    def test_exact_owner_public_free_attempt_and_label(self):
        environment = {
            "GITHUB_REPOSITORY": h.arm.REPOSITORY,
            "GITHUB_ACTOR": "woosung-dev",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_EVENT_NAME": "pull_request",
            "RUNNER_ENVIRONMENT": "github-hosted",
        }
        h.identity(event(), environment)
        for key, value in (
            ("GITHUB_ACTOR", "other"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("RUNNER_ENVIRONMENT", "self-hosted"),
        ):
            with self.assertRaises(ValueError):
                h.identity(event(), {**environment, key: value})
        value = event()
        value["repository"]["private"] = True
        with self.assertRaises(ValueError):
            h.identity(value, environment)
        value = event()
        value["label"]["name"] = "sol-research-economics-execute"
        with self.assertRaises(ValueError):
            h.identity(value, environment)

    def test_unconfigured_payload_refuses_before_network_or_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            args = SimpleNamespace(
                directory=Path(folder) / "new", data_url="", data_sha256=""
            )
            with (
                patch.object(h.arm, "download") as network,
                self.assertRaises(ValueError),
            ):
                h.prepare(args)
            network.assert_not_called()
            self.assertFalse(args.directory.exists())

    def test_authenticated_archive_extra_link_and_changed_probe_refused(self):
        for bad in (None, "extra", "link", "probe"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                snapshot = {
                    "files": [{"snapshot_path": f"file-{n}.csv"} for n in range(10)],
                    "sources": {"parent": {}, "execution": {}},
                }
                raw = json.dumps(snapshot).encode()
                values = {name: b"synthetic-data" for name in h.names(snapshot)}
                values["data/snapshot.json"] = raw
                values["probe.py"] = (
                    (ROOT / "sol_economic_data_probe.py").read_bytes()
                    if bad != "probe"
                    else b"changed"
                )
                if bad == "extra":
                    values["source/forbidden.py"] = b"forbidden"

                def authenticate(args, action, incoming, destination, context):
                    if context == "input-v7":
                        with tarfile.open(destination, "w"):
                            pass
                    else:
                        with tarfile.open(destination, "w:gz") as archive:
                            for name, value in values.items():
                                member = tarfile.TarInfo(name)
                                member.size = len(value)
                                if bad == "link" and name == "probe.py":
                                    member.type, member.size = tarfile.SYMTYPE, 0
                                archive.addfile(
                                    member,
                                    io.BytesIO(value) if member.isfile() else None,
                                )

                args = SimpleNamespace(
                    directory=root / "new",
                    run_id="123",
                    data_url=h.PREFIX + "data.enc",
                    data_sha256="a" * 64,
                )
                with (
                    patch.object(h.arm, "download"),
                    patch.object(h.arm, "crypto", side_effect=authenticate),
                    patch.object(h, "SNAPSHOT_SHA", hashlib.sha256(raw).hexdigest()),
                ):
                    if bad:
                        with self.assertRaises(ValueError):
                            h.prepare(args)
                        self.assertFalse((args.directory / "data-probe").exists())
                    else:
                        h.prepare(args)
                        self.assertTrue(
                            (args.directory / "data-probe/probe.py").is_file()
                        )

    def test_only_cells_and_frame_hash_ast_are_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tools/research").mkdir(parents=True)
            (root / "tools/research/sol_economics.py").write_text(
                "raise AssertionError('full module executed')\n"
                "def cells(snapshot): return ['original-cell-body']\n"
                "def frame_hash(frame): return 'original-hash-body'\n"
                "def run_job(*a): raise AssertionError('economic called')\n"
            )
            cell_builder, frame_hash = p.original_functions(root, None, None, None)
            self.assertEqual(cell_builder(None), ["original-cell-body"])
            self.assertEqual(frame_hash(None), "original-hash-body")

    def test_exact_thirteen_data_paths_and_no_duplicate_escape(self):
        snapshot = {
            "files": [{"snapshot_path": f"data-{n}.csv"} for n in range(10)],
            "sources": {"parent": {}, "execution": {}},
        }
        self.assertEqual(len(h.names(snapshot)), 13)
        for bad in ("../foreign", "/foreign", "data-0.csv"):
            value = deepcopy(snapshot)
            value["files"][-1]["snapshot_path"] = bad
            with self.assertRaises(ValueError):
                h.names(value)

    def test_loader_twelve_calls_and_hashes_without_economic_function(self):
        calls = []

        def loader(*args, **kwargs):
            calls.append((args, kwargs))
            return [1, 2], [3], [4, 5, 6] if kwargs["execution"] else None

        value = SimpleNamespace(
            load_snapshot=lambda _: {"warmup_bars": 200}, load_economic_cell=loader
        )
        rows = p.observe(
            value,
            cells,
            lambda frame: None if frame is None else "a" * 64,
            Path("synthetic"),
        )
        self.assertEqual(len(rows), 12)
        self.assertEqual(len(calls), 12)
        self.assertTrue(all(call[1]["warmup_bars"] == 200 for call in calls))
        with self.assertRaises(ValueError):
            p.observe(
                value, lambda _: cells(None)[:-1], lambda _: "hash", Path("synthetic")
            )

    def test_native_model_selection_import_and_io_are_denied(self):
        gate = p.DataOnlyImports()
        for name in (
            "src",
            "src.strategy.code_runtime.backtest",
            "tools.research.sol_economics",
            "tools.research.sol_score_report",
            "tools.research.sol_codegen",
            "celery",
            "ccxt",
            "openai",
        ):
            with self.assertRaises(RuntimeError):
                gate.find_spec(name)
        self.assertIsNone(gate.find_spec("tools.research.sol_economic_data"))
        for name in (
            "socket.connect",
            "socket.bind",
            "subprocess.Popen",
            "os.system",
            "os.posix_spawn",
            "os.fork",
        ):
            with self.assertRaises(RuntimeError):
                p.audit(name, ())

    def test_probe_child_no_key_token_docker_or_environment_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "data-probe"
            path.mkdir()
            (path / "probe.py").write_bytes(
                (ROOT / "sol_economic_data_probe.py").read_bytes()
            )
            args = SimpleNamespace(directory=root)
            with (
                patch.dict(
                    os.environ,
                    {"SOL_RESEARCH_EPOCH7_KEY": "SYNTHETIC", "GH_TOKEN": "SYNTHETIC"},
                ),
                patch.object(
                    h.subprocess, "run", return_value=SimpleNamespace(returncode=0)
                ) as child,
            ):
                h.probe(args)
            command = child.call_args.args[0]
            environment = child.call_args.kwargs["env"]
            self.assertNotIn("SOL_RESEARCH_EPOCH7_KEY", environment)
            self.assertNotIn("GH_TOKEN", environment)
            self.assertNotIn("DOCKER_HOST", environment)
            self.assertIn("probe.py", command[2])
            self.assertIs(
                h.arm.load(root / "probe-exit.json")["actual_wait_observed"], True
            )

    def test_cross_os_equal_only_and_missing_conflicting_hash_refusal(self):
        for bad in (None, "different", "missing", "duplicate", "native", "wrong-os"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                local, remote = report("Darwin"), report("Linux")
                if bad == "different":
                    remote["cells"][0]["hashes"]["parent"] = "d" * 64
                if bad == "missing":
                    remote.pop("data_source_sha256")
                if bad == "duplicate":
                    remote["cells"][-1] = remote["cells"][0]
                if bad == "native":
                    remote["native_calls"] = 1
                if bad == "wrong-os":
                    remote["system"] = "Darwin"
                write(root / "local.json", local)
                write(root / "remote.json", remote)
                args = SimpleNamespace(
                    local_result=root / "local.json",
                    remote_result=root / "remote.json",
                    output=root / "compare.json",
                )
                if bad:
                    with self.assertRaises(ValueError):
                        h.compare(args)
                    self.assertFalse(args.output.exists())
                else:
                    h.compare(args)
                    self.assertIn(
                        "NOT_ECONOMIC_COMPLETION", h.arm.load(args.output)["status"]
                    )

    def test_workflow_one_free_host_and_no_runtime_or_economic_path(self):
        text = (
            ROOT.parents[1] / ".github/workflows/sol-economic-data-preflight.yml"
        ).read_text()
        for value in (
            "runs-on: ubuntu-24.04-arm",
            "sol-economic-data-preflight",
            "github.run_attempt == 1",
            "DATA_URL: 'https://github.com/woosung-dev/quantbridge/releases/download/sol-research-epoch7-20261023/economic-data-preflight-v8.enc'",
            "DATA_SHA256: '0c5942f94b7d8a814d4510f37542ccb187e8b0af92769c961c3dd4750d9bcdc7'",
            "github.event.repository.private == false",
        ):
            self.assertIn(value, text)
        for value in (
            "matrix:",
            "docker",
            " run_job",
            "sol_economics.py",
            " runtime",
            "actions/upload-artifact",
        ):
            self.assertNotIn(value, text)


if __name__ == "__main__":
    unittest.main()
