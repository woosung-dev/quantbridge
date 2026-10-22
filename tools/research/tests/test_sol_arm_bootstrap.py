"""원격 호출 없이 bootstrap의 신뢰 경계만 검산한다."""

import importlib.util
import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / "sol_arm_bootstrap.py"
spec = importlib.util.spec_from_file_location("reviewed_arm_bootstrap", SOURCE)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def archive(path, name, content=b"{}", kind=tarfile.REGTYPE):
    with tarfile.open(path, "w") as out:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.size = len(content) if kind == tarfile.REGTYPE else 0
        out.addfile(member, io.BytesIO(content) if member.size else None)


class BootstrapBoundaryTests(unittest.TestCase):
    def test_observed_backtest_keeps_original_arguments_and_return_identity(self):
        returned = object()
        frame = list(range(201))
        kwargs = {"warmup_bars": 200, "params": {}}
        original = unittest.mock.Mock(return_value=returned)
        records, snapshots = [], []
        observe = bootstrap.observed_backtest(
            original, records, lambda: snapshots.append(json.loads(json.dumps(records)))
        )
        self.assertIs(observe("manual source", "typescript", frame, **kwargs), returned)
        original.assert_called_once_with("manual source", "typescript", frame, **kwargs)
        self.assertEqual([x[0]["status"] for x in snapshots], ["STARTED", "RETURNED"])
        self.assertEqual(records[0]["language"], "typescript")
        self.assertEqual(records[0]["bar_count"], 201)
        self.assertNotIn("manual source", json.dumps(records))

    def test_observed_backtest_reraises_same_exception_and_redacts_private_message(
        self,
    ):
        error = RuntimeError("native synthetic-secret-value problem")
        original = unittest.mock.Mock(side_effect=error)
        records = []
        with patch.dict(bootstrap.os.environ, {"GH_TOKEN": "synthetic-secret-value"}):
            observe = bootstrap.observed_backtest(original, records, lambda: None)
            with self.assertRaises(RuntimeError) as caught:
                observe("manual source", "pine", list(range(201)))
        self.assertIs(caught.exception, error)
        self.assertEqual(original.call_count, 1)
        self.assertEqual(records[0]["status"], "RAISED")
        self.assertEqual(records[0]["error_type"], "RuntimeError")
        self.assertNotIn("synthetic-secret-value", records[0]["private_error"])
        self.assertIn("<redacted>", records[0]["private_error"])
        self.assertIn("completed_at", records[0])

    def diagnostic_fixture(self, base):
        relative = "apps/api/src/strategy/python_runtime/sandbox.py"
        target = base / "bundle/source" / relative
        target.parent.mkdir(parents=True)
        target.write_text(
            'def sandbox_command(image_id: str, name: str) -> list[str]:\n    return [_DOCKER, "run", "--rm", "-i", "--name", name, "--runtime=runsc", "--network=none", "--read-only", "--cpus=1", "--memory=1g", image_id]\n'
        )
        inputs = base / "bundle/inputs"
        inputs.mkdir()
        (inputs / "pending.json").write_text(
            json.dumps(
                {
                    "source_hashes": {relative: bootstrap.sha(target)},
                    "image_ids": {
                        "quantbridge-python-runner:local": "sha256:" + "a" * 64
                    },
                }
            )
        )
        return SimpleNamespace(directory=base), target

    def test_native_diagnostic_uses_original_function_and_private_bounded_output(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            args, source = self.diagnostic_fixture(base)
            secret = "synthetic-redaction-value"
            completed = subprocess.CompletedProcess(
                [], 0, b'{"ready":1}\n', (secret + "z" * 70000).encode()
            )
            environment = {
                "PATH": "/usr/bin",
                "DOCKER_HOST": "unix:///var/run/docker.sock",
            }
            with (
                patch.object(
                    bootstrap.subprocess, "run", return_value=completed
                ) as run,
                patch.dict(bootstrap.os.environ, {"GH_TOKEN": secret}),
            ):
                bootstrap.native_diagnostic(args, environment, base)
            kwargs = run.call_args.kwargs
            self.assertEqual(kwargs["timeout"], 60)
            self.assertTrue(kwargs["capture_output"])
            self.assertEqual(
                json.loads(kwargs["input"])["source"],
                "def on_bar(ctx, state):\n    return {'action': 'hold'}\n",
            )
            self.assertNotIn("GH_TOKEN", kwargs["env"])
            receipt = json.loads((base / "private-native-diagnostic.json").read_text())
            self.assertTrue(receipt["actual_wait_observed"])
            self.assertTrue(receipt["ready"])
            self.assertEqual(receipt["returncode"], 0)
            self.assertLessEqual(len(receipt["stderr"]), 65536)
            self.assertNotIn(secret, receipt["stderr"])
            self.assertEqual(receipt["original_source_sha256"], bootstrap.sha(source))

    def test_native_diagnostic_failure_timeout_and_modified_source_fail_closed(self):
        for mode in ("exit", "timeout", "source"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                args, source = self.diagnostic_fixture(base)
                if mode == "source":
                    source.write_text("changed")
                failure = subprocess.CompletedProcess([], 125, b"", b"native failure")
                effect = (
                    subprocess.TimeoutExpired(
                        ["docker"], 60, output=b"partial", stderr=b"timeout"
                    )
                    if mode == "timeout"
                    else None
                )
                with patch.object(
                    bootstrap.subprocess,
                    "run",
                    return_value=failure,
                    side_effect=effect,
                ) as run:
                    with self.assertRaises((ValueError, RuntimeError)):
                        bootstrap.native_diagnostic(args, {"PATH": "/usr/bin"}, base)
                if mode == "source":
                    self.assertEqual(run.call_count, 0)
                else:
                    receipt = json.loads(
                        (base / "private-native-diagnostic.json").read_text()
                    )
                    self.assertFalse(receipt["ready"])
                    self.assertEqual(receipt["actual_wait_observed"], mode == "exit")

    def revision_fixture(self, base, *, tamper=False, extra=False, wrong_base=False):
        root = base / "root"
        names = {
            "runner/worker.py",
            "runner/protocol.py",
            "runner/coordinator.py",
            "inputs/pending.json",
            "inputs/hidden-frame.json",
            "epoch.json",
        }
        before = {}
        for name in names - {"inputs/hidden-frame.json"}:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"reviewed previous bytes")
            before[name] = bootstrap.sha(target)
        values = {name: b"reviewed new bytes" for name in names}
        revision = {
            "schema_version": 1,
            "epoch_id": "semantic-distributed-v8",
            "base_cipher_sha256": ("b" if wrong_base else "a") * 64,
            "before_files": before,
            "files": {
                name: hashlib.sha256(raw).hexdigest() for name, raw in values.items()
            },
        }
        values["revision.json"] = json.dumps(revision).encode()
        if tamper:
            values["inputs/hidden-frame.json"] = b"unreviewed different data"
        if extra:
            values["source/apps/api/src/unreviewed.py"] = b"unreviewed code"
        archive_path = base / "revision.tar"
        with tarfile.open(archive_path, "w") as bundle:
            for name, raw in values.items():
                item = tarfile.TarInfo(name)
                item.size = len(raw)
                bundle.addfile(item, io.BytesIO(raw))
        return root, archive_path

    def test_reviewed_revision_only_changes_closed_input_provider_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root, archive_path = self.revision_fixture(Path(folder))
            bootstrap.apply_revision(root, archive_path, "a" * 64)
            self.assertEqual(
                (root / "inputs/hidden-frame.json").read_bytes(), b"reviewed new bytes"
            )
            self.assertEqual(
                (root / "runner/worker.py").read_bytes(), b"reviewed new bytes"
            )

    def test_revision_rejects_wrong_data_extra_source_and_wrong_base_before_writing(
        self,
    ):
        for option in ("tamper", "extra", "wrong_base"):
            with self.subTest(option=option), tempfile.TemporaryDirectory() as folder:
                root, archive_path = self.revision_fixture(
                    Path(folder), **{option: True}
                )
                with self.assertRaises(ValueError):
                    bootstrap.apply_revision(root, archive_path, "a" * 64)
                self.assertEqual(
                    (root / "runner/worker.py").read_bytes(), b"reviewed previous bytes"
                )
                self.assertFalse((root / "inputs/hidden-frame.json").exists())

    def test_revision_rejects_changed_previous_input_and_cannot_apply_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            root, archive_path = self.revision_fixture(Path(folder))
            (root / "inputs/pending.json").write_bytes(b"concurrent change")
            with self.assertRaisesRegex(ValueError, "original_file_hash"):
                bootstrap.apply_revision(root, archive_path, "a" * 64)
        with tempfile.TemporaryDirectory() as folder:
            root, archive_path = self.revision_fixture(Path(folder))
            bootstrap.apply_revision(root, archive_path, "a" * 64)
            with self.assertRaisesRegex(ValueError, "base_or_scope"):
                bootstrap.apply_revision(root, archive_path, "a" * 64)

    def test_extract_rejects_path_escape_links_and_devices_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name, kind in (
                ("../escape", tarfile.REGTYPE),
                ("/absolute", tarfile.REGTYPE),
                ("link", tarfile.SYMTYPE),
                ("device", tarfile.CHRTYPE),
            ):
                with self.subTest(name=name):
                    archive(base / "bad.tar", name, kind=kind)
                    with self.assertRaises(ValueError):
                        bootstrap.safe_extract(base / "bad.tar", base / "out")
            self.assertFalse((base / "escape").exists())
            self.assertFalse((base / "out").exists())

    def test_overlay_only_replaces_authenticated_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "root/inputs").mkdir(parents=True)
            (base / "root/inputs/pending.json").write_text('{"old":true}')
            archive(base / "overlay.tar", "inputs/pending.json", b'{"new":true}')
            bootstrap.apply_overlay(base / "root", base / "overlay.tar")
            self.assertEqual(
                json.loads((base / "root/inputs/pending.json").read_text()),
                {"new": True},
            )
            archive(base / "bad.tar", "source/changed.py")
            with self.assertRaises(ValueError):
                bootstrap.apply_overlay(base / "root", base / "bad.tar")

    def test_download_rejects_unpinned_or_other_origin_before_network(self):
        with patch.object(bootstrap.urllib.request, "urlopen") as network:
            for url, checksum in (
                ("https://evil.invalid/input", "a" * 64),
                (
                    "https://github.com/woosung-dev/quantbridge/releases/download/tag/input",
                    "0" * 64,
                ),
            ):
                with self.assertRaises(ValueError):
                    bootstrap.download(url, checksum, Path("unused"))
            network.assert_not_called()

    def test_subprocess_errors_never_include_private_output_and_clean_environment(self):
        response = SimpleNamespace(
            returncode=2, stdout=b"private source", stderr=b"private token"
        )
        with (
            patch.dict(
                os.environ,
                {"SOL_RESEARCH_EPOCH7_KEY": "private-key", "GH_TOKEN": "private-token"},
            ),
            patch.object(bootstrap.subprocess, "run", return_value=response) as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "^bootstrap_subprocess_failed$"):
                bootstrap.checked(["docker", "info"])
            environment = run.call_args.kwargs["env"]
            self.assertNotIn("GH_TOKEN", environment)
            self.assertNotIn("SOL_RESEARCH_EPOCH7_KEY", environment)
            self.assertEqual(environment["DOCKER_HOST"], "unix:///var/run/docker.sock")

    def test_execute_without_claim_cannot_start_worker(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(bootstrap.subprocess, "run") as runner,
        ):
            with self.assertRaisesRegex(ValueError, "immutable_claim_required"):
                bootstrap.run(SimpleNamespace(directory=Path(folder), mode="execute"))
            runner.assert_not_called()

    def test_worker_python_patch_and_all_packages_use_exact_private_pins(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "bundle/inputs").mkdir(parents=True)
            (base / "bundle/inputs/pending.json").write_text(
                '{"python_version":"3.12.12"}'
            )
            (base / "bundle/host-requirements.txt").write_text(
                "numpy==2.3.4\npandas==2.3.3\n"
            )
            with patch.object(
                bootstrap.subprocess, "run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                bootstrap.dependencies(SimpleNamespace(directory=base))
                self.assertEqual(
                    run.call_args_list[0].args[0],
                    ["uv", "venv", "--python", "3.12.12", str(base / "venv")],
                )
                install = run.call_args_list[1].args[0]
                self.assertIn("--no-deps", install)
                self.assertIn(str(base / "venv/bin/python"), install)
                self.assertNotIn("SOL_RESEARCH_EPOCH7_KEY", run.call_args.kwargs["env"])

    def test_cleanup_refuses_unknown_container_without_signalling(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "owned-runtime.json").write_text("{}")
            with patch.object(
                bootstrap, "checked", return_value="abc unrelated-service"
            ) as call:
                with self.assertRaisesRegex(
                    ValueError, "unknown_container_cleanup_refused"
                ):
                    bootstrap.cleanup(SimpleNamespace(directory=base))
                self.assertEqual(call.call_count, 1)

    def test_runtime_enables_containerd_before_loading_exact_oci_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / "bundle"
            (root / "runtime").mkdir(parents=True)
            (root / "runtime/runsc").write_bytes(b"fixed runtime")
            (root / "images.tar").write_bytes(b"fixed OCI archive")
            identities = {
                name: "sha256:" + str(i) * 64
                for i, name in enumerate(("py", "ts", "pine"), 1)
            }
            (root / "epoch.json").write_text(
                json.dumps(
                    {
                        "runtime_files": {
                            "runsc": bootstrap.sha(root / "runtime/runsc")
                        },
                        "images_tar_sha256": bootstrap.sha(root / "images.tar"),
                        "image_ids": identities,
                    }
                )
            )
            calls = []
            info = {"NCPU": 4, "MemTotal": 16 * 1024**3}

            def execute(command):
                calls.append(command)
                if command == ["uname", "-m"]:
                    return "aarch64"
                if command[:2] == ["docker", "info"]:
                    restarted = ["sudo", "systemctl", "restart", "docker"] in calls
                    return json.dumps(
                        {
                            **info,
                            "DriverStatus": [
                                ["driver-type", "io.containerd.snapshotter.v1"]
                            ]
                            if restarted
                            else [],
                        }
                    )
                if command[:3] == ["docker", "image", "inspect"]:
                    return json.dumps(
                        [{"Id": identities[command[-1]], "Architecture": "arm64"}]
                    )
                return ""

            with patch.object(bootstrap, "checked", side_effect=execute):
                bootstrap.runtime(SimpleNamespace(directory=base))
            config = json.loads((base / "daemon.json").read_text())
            self.assertIs(config["features"]["containerd-snapshotter"], True)
            restart = calls.index(["sudo", "systemctl", "restart", "docker"])
            load = next(
                i
                for i, command in enumerate(calls)
                if command[:3] == ["docker", "image", "load"]
            )
            self.assertLess(restart, load)
            self.assertTrue((base / "owned-runtime.json").exists())

    def test_claim_conflict_is_not_retried_or_promoted(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "bundle/inputs").mkdir(parents=True)
            (base / "bundle/runner").mkdir()
            (base / "bundle/inputs/pending.json").write_text("{}")
            (base / "bundle/runner/worker.py").write_text("# trusted")
            (base / "bundle/epoch.json").write_text("{}")
            error = bootstrap.urllib.error.HTTPError(
                "https://uploads.github.com", 422, "exists", {}, None
            )
            args = SimpleNamespace(directory=base, shard=0, run_id="123", release_id=1)
            with (
                patch.dict(os.environ, {"GH_TOKEN": "fake"}),
                patch.object(
                    bootstrap.urllib.request, "urlopen", side_effect=error
                ) as network,
            ):
                with self.assertRaises(bootstrap.urllib.error.HTTPError):
                    bootstrap.claim(args)
                self.assertEqual(network.call_count, 1)
                self.assertFalse((base / "claim.json").exists())
            error.close()


if __name__ == "__main__":
    unittest.main()
