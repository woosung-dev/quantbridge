"""gzip OS 한 바이트만 허용한다. 전략·VM·수치복원·원장 쓰기는 하지 않는다."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("byte9_candidate", HERE.parent / "runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class Byte9Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = {"publication_id": "Synthetic", "code_path": "python", "timeframe": "1h", "period": "P1", "expected": {}}
        self.rows, self.baselines, self.candidates = [], [], []
        for policy in ("A", "B"):
            data = bytearray(gzip.compress(json.dumps({"policy": policy, "metric": 1}).encode(), mtime=0))
            data[9] = 0x13
            baseline = self.root / (policy + "-baseline.gz")
            baseline.write_bytes(data)
            self.baselines.append(bytes(data))
            data[9] = 3
            actual = self.root / (policy + "-actual.gz")
            actual.write_bytes(data)
            self.candidates.append(bytes(data))
            self.case["expected"][policy] = {"request_hash": policy, "result_sha256": runner.sha(baseline)}
            self.rows.append({**{k: self.case[k] for k in ("publication_id", "code_path", "timeframe", "period")}, "policy": policy, "status": "completed", "metrics": {"total_trades": 2}, "request_hash": policy, "result_file": actual.name, "result_sha256": runner.sha(actual)})

    def changed(self, raw):
        path = self.root / self.rows[0]["result_file"]
        path.write_bytes(raw)
        self.rows[0]["result_sha256"] = runner.sha(path)
        return runner.compare_rows(self.rows, self.case, self.root)[0]

    def test_OS_only_equivalence_preserves_actual_SHA_and_mtime(self):
        path = self.root / self.rows[0]["result_file"]
        before = runner.sha(path), path.stat().st_mtime_ns
        comparisons = runner.compare_rows(self.rows, self.case, self.root)
        for result in comparisons:
            self.assertFalse(result["exact"])
            self.assertTrue(result["transport_header_only"])
            self.assertEqual(result["gzip_os_19_sha256"], self.case["expected"][result["policy"]]["result_sha256"])
            self.assertEqual(result["result_sha256"], self.rows[0 if result["policy"] == "A" else 1]["result_sha256"])
        self.assertEqual((runner.sha(path), path.stat().st_mtime_ns), before)

    def test_original_byte_exact_behavior_unchanged(self):
        result = self.changed(self.baselines[0])
        self.assertTrue(result["exact"])
        self.assertFalse(result["transport_header_only"])
        self.assertIsNone(result["gzip_os_19_sha256"])

    def test_every_other_byte_is_rejected(self):
        for offset in range(len(self.candidates[0])):
            if offset == 9:
                continue
            raw = bytearray(self.candidates[0])
            raw[offset] ^= 1
            with self.subTest(offset=offset):
                result = self.changed(raw)
                self.assertFalse(result["exact"] or result["transport_header_only"])

    def test_missing_truncated_or_extended_file_is_rejected(self):
        for raw in [*[(self.candidates[0])[:n] for n in range(11)], self.candidates[0][:-1], self.candidates[0] + b"x"]:
            with self.subTest(length=len(raw)):
                result = self.changed(raw)
                self.assertFalse(result["exact"] or result["transport_header_only"])
        (self.root / self.rows[0]["result_file"]).unlink()
        with self.assertRaises(AssertionError):
            runner.compare_rows(self.rows, self.case, self.root)

    def test_different_payload_with_same_OS_does_not_pass(self):
        raw = bytearray(gzip.compress(b'{"policy": "A", "metric": 2}', mtime=0))
        raw[9] = 3
        result = self.changed(raw)
        self.assertFalse(result["exact"] or result["transport_header_only"])

    def test_request_or_cell_mismatch_never_uses_header_equivalence(self):
        self.rows[0]["request_hash"] = "different-request"
        result = runner.compare_rows(self.rows, self.case, self.root)[0]
        self.assertFalse(result["exact"] or result["transport_header_only"])
        for key, value in (("publication_id", "Other"), ("timeframe", "4h"), ("period", "P2"), ("code_path", "pine")):
            rows = copy.deepcopy(self.rows)
            rows[0][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                runner.compare_rows(rows, self.case, self.root)

    def test_recorded_raw_SHA_cannot_be_replaced_by_baseline(self):
        self.rows[0]["result_sha256"] = self.case["expected"]["A"]["result_sha256"]
        with self.assertRaises(AssertionError):
            runner.compare_rows(self.rows, self.case, self.root)

    def test_streaming_read_only_no_decompression(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("full read forbidden")), patch.object(Path, "write_bytes", side_effect=AssertionError("writes forbidden")), patch.object(gzip, "decompress", side_effect=AssertionError("decompression forbidden")):
            results = runner.compare_rows(self.rows, self.case, self.root)
            self.assertTrue(all(c["transport_header_only"] for c in results))


if __name__ == "__main__":
    unittest.main(verbosity=2)
