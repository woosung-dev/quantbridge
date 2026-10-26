"""ARM pilot의 파일/metadata 경계만 TEMP로 검증한다. Docker·모델·원문 실행은 없다."""

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location("staging_" + name, HERE.parent / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap, runner, package = (load(n) for n in ("bootstrap", "runner", "package"))


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def archive(self, members):
        path = self.root / "fixture.tar"
        with tarfile.open(path, "w") as stream:
            for name, kind in members:
                info = tarfile.TarInfo(name)
                info.type = kind
                if kind == tarfile.SYMTYPE:
                    info.linkname = "../outside"
                    stream.addfile(info)
                else:
                    info.size = 3
                    stream.addfile(info, io.BytesIO(b"abc"))
        return path

    def test_archive_traversal_symlink_duplicate_and_env_rejected(self):
        for members in [
            [("../outside", tarfile.REGTYPE)], [("/absolute", tarfile.REGTYPE)],
            [("link", tarfile.SYMTYPE)], [("x", tarfile.REGTYPE), ("./x", tarfile.REGTYPE)],
            [("input/.env.local", tarfile.REGTYPE)],
        ]:
            target = self.root / ("extracted" + str(len(list(self.root.glob("extracted*")))))
            with self.subTest(members=members), self.assertRaises(AssertionError):
                bootstrap.safe_extract(self.archive(members), target)
            self.assertFalse((self.root / "outside").exists())

    def test_manifest_exact_sha_extra_files_and_baseline_bytes(self):
        root = self.root / "files"
        root.mkdir()
        source = root / "input.txt"
        source.write_bytes(b"public fixture")
        manifest = {"files": {"input.txt": bootstrap.sha(source)}}
        (root / "pilot.json").write_text(json.dumps(manifest))
        self.assertEqual(bootstrap.verify_files(root), manifest)
        source.write_bytes(b"tampered")
        with self.assertRaises(AssertionError):
            bootstrap.verify_files(root)
        source.write_bytes(b"public fixture")
        for name in ("extra", ".env", "input-run/cells/x/latest.json", "result-abc.json.gz"):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fixture")
            with self.subTest(name=name), self.assertRaises(AssertionError):
                bootstrap.verify_files(root)
            manifest["files"][name] = bootstrap.sha(target)
            (root / "pilot.json").write_text(json.dumps(manifest))
            if name != "extra":
                with self.assertRaises(AssertionError):
                    bootstrap.verify_files(root)
            manifest["files"].pop(name)
            target.unlink()
            (root / "pilot.json").write_text(json.dumps(manifest))

    def test_all_sha_helpers_stream_without_read_bytes(self):
        path = self.root / "large-public-fixture"
        raw = b"0123456789" * 100000
        path.write_bytes(raw)
        expected = hashlib.sha256(raw).hexdigest()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("not streaming")):
            for module in (bootstrap, runner, package):
                self.assertEqual(module.sha(path), expected)

    def test_secret_environment_and_env_file_guard(self):
        with patch.dict(os.environ, {"DOCKER_HOST": "unix:///var/run/docker.sock"}, clear=True):
            runner.guard_environment(self.root)
            for name in ("GH_TOKEN", "GITHUB_TOKEN", runner.SECRET, "SOL_RESEARCH_EPOCH7_KEY"):
                with self.subTest(name=name), patch.dict(os.environ, {name: "synthetic-test-only"}), self.assertRaises(AssertionError):
                    runner.guard_environment(self.root)
            with patch.dict(os.environ, {"DOCKER_HOST": "tcp://unexpected"}), self.assertRaises(AssertionError):
                runner.guard_environment(self.root)
            (self.root / ".env.fixture").write_text("not a credential")
            with self.assertRaises(AssertionError):
                runner.guard_environment(self.root)

    def rows(self):
        case = {"publication_id": "Synthetic", "code_path": "python", "timeframe": "1h", "period": "P1", "expected": {}}
        rows = []
        for policy in ("A", "B"):
            path = self.root / (policy + ".json.gz")
            path.write_bytes((policy + " public synthetic result").encode())
            digest = runner.sha(path)
            case["expected"][policy] = {"request_hash": policy, "result_sha256": digest}
            rows.append({**{k: case[k] for k in ("publication_id", "code_path", "timeframe", "period")}, "policy": policy, "status": "completed", "metrics": {"total_trades": 2}, "request_hash": policy, "result_file": path.name, "result_sha256": digest})
        return rows, case

    def test_exact_two_nonzero_completed_rows_and_oracle_mismatch(self):
        rows, case = self.rows()
        self.assertTrue(all(v["exact"] for v in runner.compare_rows(rows, case, self.root)))
        for wrong in ([], rows[:1], rows + rows[:1], rows[::-1]):
            with self.subTest(length=len(wrong)), self.assertRaises(AssertionError):
                runner.compare_rows(wrong, case, self.root)
        for key, value in (("status", "failed"), ("publication_id", "Other"), ("policy", "B"), ("timeframe", "4h")):
            wrong = copy.deepcopy(rows)
            wrong[0][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                runner.compare_rows(wrong, case, self.root)
        for trades in (0, True, "2"):
            wrong = copy.deepcopy(rows)
            wrong[0]["metrics"]["total_trades"] = trades
            with self.subTest(trades=trades), self.assertRaises(AssertionError):
                runner.compare_rows(wrong, case, self.root)
        case["expected"]["A"]["request_hash"] = "oracle mismatch"
        self.assertFalse(runner.compare_rows(rows, case, self.root)[0]["exact"])

    def test_row_result_sha_and_path_escape_rejected(self):
        rows, case = self.rows()
        for key, value in (("result_sha256", "0" * 64), ("result_file", "../outside.json.gz")):
            wrong = copy.deepcopy(rows)
            wrong[0][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                runner.compare_rows(wrong, case, self.root)

    def test_observer_isolation_config_and_owned_container_lifecycle(self):
        inspect = {"name": "synthetic-owned", "image_id": "sha256:fixture", "runtime": "runsc", "network": "none", "readonly": True, "nano_cpus": 1000000000, "memory": 1073741824, "memory_swap": 1073741824}
        events = [{"action": "create", "container_id": "owned", "inspect": inspect}, {"action": "destroy", "container_id": "owned"}]
        self.assertTrue(runner.verify_observation(events, "sha256:fixture", 1, [], []))
        for field, value in (("runtime", "runc"), ("network", "host"), ("readonly", False), ("image_id", "other"), ("nano_cpus", 2000000000), ("memory", 1), ("memory_swap", -1)):
            wrong = copy.deepcopy(events)
            wrong[0]["inspect"][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                runner.verify_observation(wrong, "sha256:fixture", 1, [], [])
        for wrong, count, before, after in (([], 1, [], []), (events[:1], 1, [], []), (events * 2, 2, [], []), (events, 1, ["foreign"], []), (events, 1, [], ["leaked"])):
            with self.subTest(count=count, before=before, after=after), self.assertRaises(AssertionError):
                runner.verify_observation(wrong, "sha256:fixture", count, before, after)

    def test_package_rejects_baseline_duplicate_env_and_wrong_sha(self):
        source = self.root / "public.txt"
        source.write_text("synthetic public input")
        image = self.root / "fake-image-bytes"
        image.write_bytes(b"not a real Docker image")
        runtime = self.root / "runtime"
        runtime.mkdir()
        plan = self.root / "plan.json"
        for member, digest, duplicate in (("input-run/cells/x/latest.json", package.sha(source), False), (".env", package.sha(source), False), ("ok.txt", "0" * 64, False), ("ok.txt", package.sha(source), True)):
            entries = [{"source": str(source), "member": member, "sha256": digest}]
            if duplicate:
                entries *= 2
            plan.write_text(json.dumps({"local_files": entries, "runtime_files": {}}))
            output = self.root / "output.tar"
            with self.subTest(member=member, duplicate=duplicate), patch.object(sys, "argv", ["package", str(plan), "--images", str(image), "--runtime", str(runtime), "--output", str(output)]), self.assertRaises(AssertionError):
                package.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
