"""6개월 독립 행렬은12셀을 요구하며 과거36셀 계약을 바꾸지 않는다."""

import importlib.util
import itertools
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tools.research.editor_picks import common, execution, verification


def matrix():
    jobs = [
        {"id": "one", "arm": a, "timeframe": t, "months": 6, "scenario": s}
        for a, t, s in itertools.product(common.ARMS, common.TIMEFRAMES, common.SCENARIOS)
    ]
    return {
        "phase": "full",
        "periods": [6],
        "jobs": jobs,
        "expected_cells": 36,
        "artifacts": {"one": {}},
    }


class PeriodContractTests(unittest.TestCase):
    def test_legacy_and_declared_counts(self):
        self.assertEqual(common.economic_cells_per_arm({}), 36)
        self.assertEqual(common.economic_cells_per_arm(matrix()), 12)

    def test_incomplete_duplicate_foreign_period_and_order_reject(self):
        variants = []
        for periods in [[], [12], [6, 12], [6, 12, 24], [6.0]]:
            f = matrix()
            f["periods"] = periods
            variants.append(f)
        f = matrix()
        f["jobs"].pop()
        f["expected_cells"] -= 1
        variants.append(f)
        f = matrix()
        f["jobs"][0] = f["jobs"][1]
        variants.append(f)
        f = matrix()
        f["jobs"][0]["months"] = 12
        variants.append(f)
        f = matrix()
        f["jobs"][0]["months"] = 6.0
        variants.append(f)
        f = matrix()
        f["jobs"].reverse()
        variants.append(f)
        f = matrix()
        f["artifacts"]["missing"] = {}
        variants.append(f)
        f = matrix()
        f["expected_cells"] = True
        variants.append(f)
        for f in variants:
            with self.subTest(profile=f.get("periods")), self.assertRaises(ValueError):
                common.economic_cells_per_arm(f)

    def test_new_full200_is7200_default_is21600(self):
        def fake_artifact(root, item, arm):
            if arm == "gemini":
                raise ValueError("completed_generation_missing")
            return "trusted fixture", "pine" if arm == "pine" else "python", "a" * 64

        for months, count in [(None, 21600), (6, 7200)]:
            with tempfile.TemporaryDirectory() as d:
                r = Path(d)
                common.write(
                    r / "cohort.json",
                    {"target": 200, "items": [{"id": f"fixture{i}"} for i in range(200)]},
                )
                common.write(r / "data/dataset.json", {})
                with (
                    patch.object(execution, "artifact", fake_artifact),
                    patch.object(execution, "implementation", return_value={"trusted": "fixture"}),
                ):
                    f = execution.plan(r, months=months)
                self.assertEqual(f["expected_cells"], count)
                self.assertEqual(len(f["jobs"]), count)
                self.assertEqual(f.get("periods"), [6] if months else None)
                self.assertNotIn("execution_workers", f)
                self.assertEqual(common.economic_cells_per_arm(f), 12 if months else 36)

    def test_whole_source_filter_rejects_against_cohort(self):
        with self.assertRaises(ValueError):
            common.economic_cells_per_arm(matrix(), {"target": 2, "items": [{"id": "one"}, {"id": "missing"}]})

    def test_cli_preserves_default_kwargs_and_passes_selected_period(self):
        from tools.research.editor_picks import __main__ as cli

        for option in [[], ["--months", "6"]]:
            with tempfile.TemporaryDirectory() as d, patch.object(
                sys, "argv", ["editor-picks", "--run-dir", d, "plan", *option]
            ), patch.object(
                execution, "plan", return_value={"expected_cells": 36, "phase": "full"}
            ) as planned, patch.object(cli, "run_dir", return_value=Path(d)), patch("builtins.print"):
                self.assertEqual(cli.main(), 0)
                kwargs = {"workers": 1, **({"months": 6} if option else {})}
                planned.assert_called_once_with(Path(d), False, **kwargs)

    def test_invalid_option_rejects_before_inputs(self):
        for months, pilot in [(12, False), (True, False), (6.0, False), (6, True)]:
            with self.assertRaises(ValueError):
                execution.plan(Path("/unused"), pilot, months=months)

    def test_execution_rejects_filtered_plan_before_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            f = matrix()
            f["jobs"].pop()
            common.write(r / "plan.json", f)
            with patch.object(execution, "require_runtime") as runtime:
                with self.assertRaises(ValueError):
                    execution.execute(r, r / "plan.json")
                runtime.assert_not_called()

    def test_reconcile_twelve_complete_and_eleven_incomplete(self):
        import pytest

        spec = importlib.util.spec_from_file_location(
            "trusted_reconcile_fixture", Path(__file__).with_name("test_editor_picks_reconcile.py")
        )
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        with tempfile.TemporaryDirectory() as d, pytest.MonkeyPatch.context() as monkeypatch:
            r = Path(d)
            path, f, completed = fixtures.evidence(r, monkeypatch)
            f["periods"] = [6]
            f["jobs"] = [j for j in f["jobs"] if j["months"] == 6]
            f["expected_cells"] = len(f["jobs"])
            common.write(path, f)
            allowed = {common.identity(j) for j in f["jobs"]}
            for key in list(completed):
                if key not in allowed:
                    completed.pop(key)
            p = r / "native-checks/one.json"
            raw = common.read(p)
            raw["plan_sha256"] = common.identity(f)
            common.write(p, raw)
            before = p.read_bytes()
            self.assertEqual(verification.reconcile(r, path)["passed_arms"], 2)
            proof = common.read(r / "verification/one.json")
            self.assertEqual(proof["arms"]["terra"]["exact_economic_cells"], 12)
            self.assertEqual(proof["arms"]["terra"]["expected_economic_cells"], 12)
            terra = next(j for j in f["jobs"] if j["arm"] == "terra")
            completed.pop(common.identity(terra))
            self.assertEqual(verification.reconcile(r, path)["passed_arms"], 1)
            self.assertEqual(
                common.read(r / "verification/one.json")["arms"]["terra"]["status"], "incomplete"
            )
            self.assertEqual(p.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
