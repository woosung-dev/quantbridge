"""원격 호출 없이 bootstrap의 신뢰 경계만 검산한다."""

import importlib.util
import io
import json
import os
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
