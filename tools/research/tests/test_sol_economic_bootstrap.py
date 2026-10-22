"""암호문/프로세스 경계만 합성 입력으로 검사한다. 실제 원격 호출은 없다."""

from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / "sol_economic_bootstrap.py"
spec = importlib.util.spec_from_file_location("economic_bootstrap_boundary", SOURCE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def event():
    return {"action": "labeled", "number": 925, "repository": {"private": False},
            "label": {"name": "sol-research-economics-execute"},
            "pull_request": {"number": 925, "user": {"login": "woosung-dev"},
                "head": {"ref": "stage/sol-research-arm-runners", "repo": {"full_name": b.arm.REPOSITORY}},
                "base": {"ref": "stage/sol-strategy-lab"}}}


class EconomicBootstrapTests(unittest.TestCase):
    def test_public_owner_pr_attempt_label_gate(self):
        environment = {"GITHUB_REPOSITORY": b.arm.REPOSITORY, "GITHUB_ACTOR": "woosung-dev",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_EVENT_NAME": "pull_request", "RUNNER_ENVIRONMENT": "github-hosted"}
        b.validate_identity(event(), environment)
        for key, value in (("GITHUB_ACTOR", "foreign"), ("GITHUB_RUN_ATTEMPT", "2"),
                           ("RUNNER_ENVIRONMENT", "self-hosted")):
            with self.assertRaises(ValueError):
                b.validate_identity(event(), {**environment, key: value})
        for change in ("private", "fork", "label", "number"):
            value = deepcopy(event())
            if change == "private":
                value["repository"]["private"] = True
            elif change == "fork":
                value["pull_request"]["head"]["repo"]["full_name"] = "foreign/fork"
            elif change == "label":
                value["label"]["name"] = "sol-research-arm-execute"
            else:
                value["number"] = 924
            with self.assertRaises(ValueError):
                b.validate_identity(value, environment)

    def test_missing_pins_stop_before_directory_network_or_crypto(self):
        with tempfile.TemporaryDirectory() as folder:
            args = SimpleNamespace(directory=Path(folder) / "new", economic_url="", economic_sha256="",
                overlay_url="", overlay_sha256="", url=b.BASE_URL, sha256=b.BASE_SHA,
                revision_url=b.REVISION_URL, revision_sha256=b.REVISION_SHA)
            with patch.object(b.arm, "download") as download, patch.object(b.arm, "crypto") as crypto:
                with self.assertRaises(ValueError):
                    b.prepare(args)
                download.assert_not_called()
                crypto.assert_not_called()
                self.assertFalse(args.directory.exists())

    def delta(self, root, *, bad=None):
        base, output = root / "base", root / "economic"
        write(base / "inputs/pending.json", {"synthetic": "pending"})
        write(base / "inputs/generation-manifest.json", {"synthetic": "manifest"})
        (base / "source").mkdir()
        (base / "source/module.py").write_text("# synthetic")
        images = {"pine": "image1", "python": "image2", "typescript": "image3"}
        write(base / "epoch.json", {"image_ids": images})
        values = {f"data/csv-{n}.csv": b"synthetic-csv\n" for n in range(10)}
        snapshot = {"files": [{"snapshot_path": f"csv-{n}.csv"} for n in range(10)],
                    "sources": {"parent": {}, "execution": {}}}
        values.update({"data/snapshot.json": json.dumps(snapshot).encode(),
                       "data/parent-manifest.json": b"{}", "data/execution-manifest.json": b"{}"})
        for folder in ("quality-origin", "economic-sealed"):
            for name in ("quality.json", "quality.selection.json", "quality.artifacts.json"):
                values[f"inputs/{folder}/{name}"] = json.dumps({
                    "complete": True, "final_selection_allowed": True, "expected_artifacts": 1350}).encode()
        for name in b.RUNNER_FILES:
            values["runner/" + name] = b"# synthetic-not-executed\n"
        plan = {"epoch_id": "economics-distributed-v8", "cold": True, "automatic_resume": False,
            "quality_exit_evidence": {"quality_driver_sha256": b.QUALITY_SHA, "input_provider_revision": {"epoch": 8}},
            "base_reference": {"pending_sha256": b.arm.sha(base / "inputs/pending.json"),
                               "generation_manifest_sha256": b.arm.sha(base / "inputs/generation-manifest.json")},
            "jobs": [None] * 1440, "image_ids": images,
            "input_files": {name: hashlib.sha256(raw).hexdigest() for name, raw in values.items() if not name.startswith("runner/")},
            "helper_hashes": {name: hashlib.sha256(values["runner/" + name]).hexdigest() for name in b.RUNNER_FILES}}
        values["economic-dispatch.json"] = json.dumps(plan).encode()
        if bad == "extra":
            values["source/unreviewed.py"] = b"# forbidden"
        elif bad == "overwrite":
            (base / "inputs/economic-sealed").mkdir()
            (base / "inputs/economic-sealed/quality.json").write_text("original")
        elif bad == "base":
            (base / "inputs/pending.json").write_text("changed")
        archive = root / "delta.tar"
        with tarfile.open(archive, "w") as bundle:
            for name, raw in values.items():
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                if bad == "link" and name == "runner/worker.py":
                    member.type, member.size = tarfile.SYMTYPE, 0
                bundle.addfile(member, io.BytesIO(raw) if member.isfile() else None)
        return base, archive, output, hashlib.sha256(values["data/snapshot.json"]).hexdigest()

    def test_closed_delta_copy_and_no_overwrite_links_extra_or_wrong_base(self):
        with tempfile.TemporaryDirectory() as folder:
            base, archive, output, checksum = self.delta(Path(folder))
            with patch.object(b, "SNAPSHOT_SHA", checksum):
                plan = b.merge_economic(base, archive, output)
            self.assertEqual(len(plan["jobs"]), 1440)
            self.assertEqual((output / "source/module.py").read_bytes(), (base / "source/module.py").read_bytes())
            self.assertFalse((output / "images.tar").exists())
        for bad in ("extra", "overwrite", "link", "base"):
            with self.subTest(case=bad), tempfile.TemporaryDirectory() as folder:
                base, archive, output, checksum = self.delta(Path(folder), bad=bad)
                with patch.object(b, "SNAPSHOT_SHA", checksum), self.assertRaises(ValueError):
                    b.merge_economic(base, archive, output)
                if bad == "overwrite":
                    self.assertEqual((base / "inputs/economic-sealed/quality.json").read_text(), "original")

    def test_worker_actual_wait_and_no_credential_inheritance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepared = {"host": "remote-04", "run_id": "123", "plan_sha256": "p"}
            write(root / "prepared.json", prepared)
            write(root / "claim.json", {**prepared, "asset_id": 1})
            child = SimpleNamespace(pid=1234, wait=lambda: 0)
            with patch.dict(os.environ, {"SOL_RESEARCH_EPOCH7_KEY": "SYNTHETIC", "GH_TOKEN": "SYNTHETIC"}), \
                    patch.object(b.subprocess, "Popen", return_value=child) as popen:
                b.run(SimpleNamespace(directory=root, shard=3, run_id="123"))
            environment = popen.call_args.kwargs["env"]
            self.assertNotIn("SOL_RESEARCH_EPOCH7_KEY", environment)
            self.assertNotIn("GH_TOKEN", environment)
            self.assertEqual(environment["DOCKER_HOST"], "unix:///var/run/docker.sock")
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            observed = b.arm.load(root / "worker-exit.json")
            self.assertEqual(observed["returncode"], 0)
            self.assertIs(observed["actual_wait_observed"], True)

    def test_claim_missing_prevents_process_and_unknown_wait_prevents_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write(root / "prepared.json", {"host": "remote-01"})
            with patch.object(b.subprocess, "Popen") as popen:
                with self.assertRaises(FileNotFoundError):
                    b.run(SimpleNamespace(directory=root, shard=0, run_id="123"))
                popen.assert_not_called()
            write(root / "worker-exit.json", {"worker_started": True, "actual_wait_observed": False})
            with patch.object(b.arm, "cleanup") as cleanup, self.assertRaises(RuntimeError):
                b.cleanup(SimpleNamespace(directory=root))
            cleanup.assert_not_called()

    def test_reaped_leader_with_live_lanes_prevents_guest_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write(root / "worker-exit.json", {"worker_started": True,
                "actual_wait_observed": True, "worker_pid": 1234})
            with patch.object(b.os, "killpg") as probe, patch.object(b.arm, "cleanup") as clean:
                with self.assertRaises(RuntimeError):
                    b.cleanup(SimpleNamespace(directory=root))
                probe.assert_called_once_with(1234, 0)
                clean.assert_not_called()
            with patch.object(b.os, "killpg", side_effect=ProcessLookupError), patch.object(b.arm, "cleanup") as clean:
                b.cleanup(SimpleNamespace(directory=root))
                clean.assert_called_once()

    def test_gzip_preserves_original_cache_receipt_and_context(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = root / "result/lane-0/cache-0001"
            cache.mkdir(parents=True)
            (cache / ("a" * 64 + ".json")).write_bytes(b"original-cache")
            (root / "result/lane-0/0001.json").write_bytes(b"original-receipt")
            def encryption(args, action, incoming, target, context):
                self.assertEqual((action, context), ("encrypt", "result-v8-economic-3"))
                target.write_bytes(b"synthetic-ciphertext")
            with patch.object(b.arm, "crypto", side_effect=encryption):
                b.pack(SimpleNamespace(directory=root, shard=3, run_id="123"))
            with tarfile.open(root / "economic-result.tar.gz") as bundle:
                self.assertEqual(bundle.extractfile("result/lane-0/0001.json").read(), b"original-receipt")
                self.assertEqual(bundle.extractfile("result/lane-0/cache-0001/" + "a" * 64 + ".json").read(), b"original-cache")
            proof = b.arm.load(root / "pack-ready.json")
            self.assertEqual(proof["asset_name"], "epoch8-economic-3-123.enc")

    def test_oversize_or_absent_pack_proof_prevents_crypto_and_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "private-worker.log").write_bytes(b"original-private-diagnostics")
            args = SimpleNamespace(directory=root, shard=0, run_id="123")
            with patch.object(b.arm, "MAX_ASSET_BYTES", 1), patch.object(b.arm, "crypto") as crypto:
                with self.assertRaises(ValueError):
                    b.pack(args)
                crypto.assert_not_called()
                self.assertFalse((root / "pack-ready.json").exists())
            self.assertEqual((root / "private-worker.log").read_bytes(), b"original-private-diagnostics")
            with patch.object(b.urllib.request, "urlopen") as network:
                b.upload(args)
                network.assert_not_called()

    def test_workflow_keeps_empty_economic_pins_public_free_matrix_and_dedicated_label(self):
        workflow = SOURCE.parents[2] / ".github/workflows/sol-research-economics.yml"
        value = workflow.read_text()
        for required in ("github.event.repository.private == false", "github.run_attempt == 1",
                         "sol-research-economics-execute", "runs-on: ubuntu-24.04-arm",
                         "max-parallel: 40", "ECONOMIC_URL: ''", "ECONOMIC_SHA256: ''",
                         "semantic-execute-v8.enc", "78ab7d23841efa1588d99bf2951002f5927e8d0b2cd04db3f5f22c8461e5e972"):
            self.assertIn(required, value)
        self.assertNotIn("actions/upload-artifact", value)
        self.assertIn("shard: [" + ", ".join(map(str, range(40))) + "]", value)
        self.assertIn("choices=range(40)", SOURCE.read_text())
        self.assertLess(value.index("Reject unconfigured seal"), value.index("mise-action"))


if __name__ == "__main__":
    unittest.main()
