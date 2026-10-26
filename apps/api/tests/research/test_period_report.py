"""보고서의 단위·미산출·A/B 조합·필터·오프라인 안전·분모 회귀."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.period_report import CORE_JS, derived_activity, generate


class PeriodReportTests(unittest.TestCase):
    def javascript(self, expression):
        result = subprocess.run(
            [
                "node",
                "-e",
                CORE_JS
                + "\nconst core=module.exports;\nprocess.stdout.write(JSON.stringify("
                + expression
                + "));",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_ratio_is_scaled_once_and_percent_is_not_rescaled(self):
        values = self.javascript(
            "[core.scaled('0.125','ratio'),core.scaled('-0.2','ratio_negative'),core.scaled('62.5','percent_0_100'),core.scaled('1.5','ratio_or_null')]"
        )
        self.assertEqual(values, [12.5, -20, 62.5, 1.5])

    def test_null_and_failed_metrics_stay_unavailable_and_sort_last(self):
        result = self.javascript(
            "(() => {const rows=[{key:'zero',A:{status:'completed',total_return:'0'}},{key:'missing',A:{status:'completed',total_return:null}},{key:'failed',A:{status:'failed',total_return:'99'}}];return {values:[core.number(null),core.number(''),core.number('NaN'),core.scaled('1',null)],asc:[...rows].sort((a,b)=>core.compare(a,b,'A.total_return','asc',{total_return:'ratio'})).map(r=>r.key),desc:[...rows].sort((a,b)=>core.compare(a,b,'A.total_return','desc',{total_return:'ratio'})).map(r=>r.key)}})()"
        )
        self.assertEqual(result["values"], [None, None, None, None])
        self.assertEqual(result["asc"][0], "zero")
        self.assertEqual(result["desc"][0], "zero")

    def test_pairing_separates_timeframe_period_path_and_signal_mode(self):
        result = self.javascript(
            "(() => {const row={publication_id:'one',code_path:'pine',timeframe:'1h',period:'P1',signal_mode:'shared_events',policy:'A'};const groups=core.groups([row,{...row,policy:'B'},{...row,timeframe:'4h'},{...row,period:'P2'},{...row,code_path:'python'},{...row,signal_mode:'position_feedback'}]);return {count:groups.length,paired:groups.filter(g=>g.A&&g.B).length}})()"
        )
        self.assertEqual(result, {"count": 5, "paired": 1})

    def test_pine_a_and_python_b_never_form_one_comparison_pair(self):
        result = self.javascript(
            "(() => {const row={publication_id:'one',timeframe:'1h',period:'P1',signal_mode:'shared_events',status:'completed'};const groups=core.groups([{...row,code_path:'pine',policy:'A'},{...row,code_path:'python',policy:'B'}]);return {count:groups.length,paired:groups.filter(g=>g.A&&g.B).length}})()"
        )
        self.assertEqual(result, {"count": 2, "paired": 0})

    def test_filters_and_numeric_bounds_use_the_selected_policy_and_status(self):
        result = self.javascript(
            "(() => {const g={title:'Test Alpha',publication_id:'one',kind:'indicators',code_path:'pine',timeframe:'1h',period:'P1',signal_mode:'shared_events',A:{status:'completed',total_return:'0.1'},B:{status:'failed',total_return:'100'}};const f={query:'alpha',kind:'indicators',code_path:'pine',timeframe:'1h',period:'P1',signal_mode:'shared_events',metric:'total_return',min:5,max:15};const u={total_return:'ratio'};return [core.matches(g,f,u),core.matches(g,{...f,policy:'B'},u),core.matches(g,{...f,status:'failed'},u),core.matches(g,{...f,min:11},u),core.matches(g,{...f,timeframe:'4h'},u)]})()"
        )
        self.assertEqual(result, [True, False, False, False, False])

    def test_activity_uses_fill_intervals_and_does_not_double_count_same_minute(self):
        def fill(episode, minute, kind, quantity, phase="bar_open"):
            return {
                "episode_id": episode,
                "timestamp": f"2024-01-01T00:{minute:02d}:00+00:00",
                "kind": kind,
                "quantity": str(quantity),
                "phase": phase,
            }

        entries = [
            fill(1, 0, "entry", 2),
            fill(1, 2, "partial_tp", 1, "intrabar_scenario"),
            fill(1, 3, "close", 1),
            fill(2, 3, "entry", 1),
            fill(2, 3, "close", 1, "intrabar_scenario"),
            fill(3, 8, "entry", 1),
        ]
        result = derived_activity(
            entries, "2024-01-01T00:00:00+00:00", "2024-01-01T00:10:00+00:00", 2, 10
        )
        self.assertEqual(result["exposure_held_minutes"], 6)
        self.assertEqual(result["exposure_pct"], "60")
        self.assertEqual(result["trade_frequency_30d"], "8640")
        empty = derived_activity(
            [], "2024-01-01T00:00:00+00:00", "2024-01-01T00:10:00+00:00", 0, 10
        )
        self.assertEqual(empty["exposure_pct"], "0")
        with self.assertRaises(ValueError):
            derived_activity(
                entries, "2024-01-01T00:00:00+00:00", "2024-01-01T00:10:00+00:00", 2, 9
            )

    def fixture(self, root):
        run, output = root / "run", root / "output"
        run.mkdir()
        output.mkdir()
        (run / "catalogue.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "id": "one",
                            "publication_id": "one",
                            "title": "</script><img src=x onerror=alert(1)>",
                            "kind": "indicators",
                            "url": "https://www.tradingview.com/script/one/",
                        }
                    ]
                }
            )
        )
        (run / "manifest.json").write_text(
            json.dumps(
                {
                    "source_count": 1,
                    "expected_cells": 60,
                    "costs": {
                        "taker": "0.00020",
                        "maker": "0.00010",
                        "slippage": "0.00010",
                    },
                    "periods": [
                        {
                            "id": "P1",
                            "start": "2024-01-01T00:00:00+00:00",
                            "end_exclusive": "2024-07-01T00:00:00+00:00",
                        }
                    ],
                }
            )
        )
        (run / "report-input.json").write_text(
            json.dumps({"cells": [], "units": {"total_return": "ratio"}})
        )
        return run, output

    def test_offline_embedded_data_cannot_close_script_and_links_are_relative(self):
        with tempfile.TemporaryDirectory() as name:
            run, output = self.fixture(Path(name))
            # 비교표의 악성 제목도 내장 JSON 안에서 실행 문맥을 벗어날 수 없다.
            (run / "report-input.json").write_text(
                json.dumps(
                    {
                        "cells": [
                            {
                                "publication_id": "one",
                                "title": "</script><img src=x onerror=alert(1)>",
                                "code_path": "pine",
                                "timeframe": "1h",
                                "period": "P1",
                                "policy": "A",
                                "status": "not_run",
                            }
                        ],
                        "units": {"total_return": "ratio"},
                    }
                )
            )
            generate(run, output)
            document = (output / "report.html").read_text()
            self.assertNotIn("</script><img", document)
            self.assertIn("\\u003c/script\\u003e", document)
            self.assertIn("connect-src 'none'", document)
            self.assertNotIn("<script src=", document)
            self.assertNotIn("@import", document)
            self.assertIn('role="region"', document)
            self.assertIn('tabindex="0"', document)
            self.assertIn('href="ledgers/fills.csv"', document)
            self.assertTrue((output / "ledgers/fills.csv").is_file())

    def test_progress_distinguishes_receipts_files_native_pass_and_registration(self):
        with tempfile.TemporaryDirectory() as name:
            run, output = self.fixture(Path(name))
            for folder in [
                "sources",
                "source_receipts",
                "native-verification",
                "registration",
                "generation/one",
            ]:
                (run / folder).mkdir(parents=True)
            source = b"source"
            (run / "sources/one.pine").write_bytes(source)
            (run / "source_receipts/one.json").write_text(
                json.dumps(
                    {
                        "id": "one",
                        "status": "captured",
                        "source_file": "sources/one.pine",
                        "source_sha256": hashlib.sha256(source).hexdigest(),
                    }
                )
            )
            (run / "generation/one/status.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "generated_file": "missing.py",
                        "generated_sha256": "a" * 64,
                    }
                )
            )
            (run / "native-verification/one-1h.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "evidence_verified": True,
                        "evidence": [{"path": "missing.png", "sha256": "a" * 64}],
                    }
                )
            )
            (run / "registration/one.json").write_text(json.dumps({"status": "registered"}))
            result = generate(run, output)
            self.assertEqual(result["report_kind"], "progress")
            self.assertEqual(result["progress"]["source_captured_verified"], 1)
            self.assertEqual(result["progress"]["generation_verified"], 0)
            self.assertEqual(result["progress"]["native_passed"], 0)
            self.assertEqual(result["progress"]["registered"], 0)
            self.assertEqual(result["progress"]["financial_target"], 30)
            self.assertEqual(result["progress"]["financial_pending"], 30)
            self.assertEqual(result["progress"]["legacy_financial_target"], 60)
            self.assertEqual(result["progress"]["registration_target_max"], 6)
            self.assertEqual(result["progress"]["legacy_registration_target_max"], 12)

    def policy_progress(self):
        return {
            "financial_target": 30,
            "financial_recorded": 1,
            "financial_statuses": {"completed": 0, "failed": 1, "not_run": 0, "pending": 29},
            "financial_pending": 29,
            "pine_completed": 0,
            "python_fallback_completed": 0,
            "legacy_financial_target": 60,
            "legacy_financial_recorded": 2,
            "legacy_financial_statuses": {"failed": 1, "completed": 1},
            "legacy_python_completed_excluded": 1,
        }

    def test_primary_rows_use_policy_view_and_legacy_python_result_remains_downloadable(self):
        with tempfile.TemporaryDirectory() as name:
            run, output = self.fixture(Path(name))
            base = {
                "publication_id": "one",
                "timeframe": "1h",
                "period": "P1",
                "policy": "A",
                "signal_mode": "shared_events",
            }
            rows = [
                {**base, "code_path": "pine", "status": "failed"},
                {**base, "code_path": "python", "status": "completed"},
            ]
            (run / "report-input.json").write_text(json.dumps({"cells": rows}))

            def selected_view(_run, exported_rows):
                return {
                    "rows": [exported_rows[0]],
                    "progress": self.policy_progress(),
                    "policy": {"version": "pine_first_v1"},
                }

            with patch(
                "tools.research.period_report.build_pine_first_view", side_effect=selected_view
            ):
                result = generate(run, output)
            self.assertEqual(result["cells"], 1)
            current = json.loads((output / "selected-financial-cells.json").read_text())
            legacy = json.loads((output / "financial-cells.json").read_text())
            self.assertEqual([row["code_path"] for row in current["cells"]], ["pine"])
            self.assertEqual([row["code_path"] for row in legacy["cells"]], ["pine", "python"])
            self.assertTrue((output / "selected-financial-cells.csv").is_file())
            self.assertTrue((output / "financial-cells.csv").is_file())
            self.assertNotIn(
                "selection_reason",
                (output / "financial-cells.csv").read_text(encoding="utf-8-sig").splitlines()[0],
            )
            self.assertIn(
                "selection_reason",
                (output / "selected-financial-cells.csv").read_text(encoding="utf-8-sig").splitlines()[0],
            )
            document = (output / "report.html").read_text()
            self.assertIn("현재 금융 분모 30셀 · 과거 양언어 계획 60셀", document)
            self.assertIn("현재 미선택 Python 완료 1셀", document)
            self.assertIn("실패 1 · 미실행 0 · 대기 29", document)
            self.assertIn("2. 원문 신호 매핑", document)
            self.assertNotIn("2. Python 생성", document)
            self.assertIn('href="selected-financial-cells.csv"', document)
            embedded = document.split('<script id="report-data" type="application/json">')[1].split(
                "</script>"
            )[0]
            self.assertEqual(len(json.loads(embedded)["cells"]), 1)

    def test_missing_or_inconsistent_policy_denominator_cannot_publish_a_report(self):
        for kind in ("missing", "status_total", "success_paths", "pending"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                run, output = self.fixture(Path(name))
                progress = self.policy_progress()
                if kind == "missing":
                    del progress["financial_target"]
                elif kind == "status_total":
                    progress["financial_target"] = 31
                elif kind == "success_paths":
                    progress["python_fallback_completed"] = 1
                else:
                    progress["financial_pending"] = 28
                with (
                    patch(
                        "tools.research.period_report.build_pine_first_view",
                        return_value={"rows": [], "progress": progress, "policy": {}},
                    ),
                    self.assertRaises(ValueError),
                ):
                    generate(run, output)
                self.assertFalse((output / "report.html").exists())

    def test_unverified_pine_completion_is_preserved_but_not_current_success(self):
        with tempfile.TemporaryDirectory() as name:
            run, output = self.fixture(Path(name))
            row = {
                "publication_id": "one",
                "code_path": "pine",
                "timeframe": "1h",
                "period": "P1",
                "policy": "A",
                "status": "completed",
                "total_return": "100",
            }
            (run / "report-input.json").write_text(json.dumps({"cells": [row]}))
            result = generate(run, output)
            self.assertEqual(result["progress"]["pine_completed"], 0)
            self.assertEqual(result["progress"]["financial_statuses"]["completed"], 0)
            self.assertEqual(result["progress"]["legacy_financial_statuses"]["completed"], 1)
            audit = json.loads((output / "financial-cells.json").read_text())
            self.assertEqual(audit["cells"][0]["status"], "completed")
            selected = json.loads((output / "selected-financial-cells.json").read_text())
            self.assertFalse(any(item["status"] == "completed" for item in selected["cells"]))

    def test_direct_cli_can_import_policy_helper(self):
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[4] / "tools/research/period_report.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--run-root", result.stdout)

    def test_static_classification_and_generation_are_not_review_approval(self):
        with tempfile.TemporaryDirectory() as name:
            run, output = self.fixture(Path(name))
            for folder in ["sources", "source_receipts", "reviews", "generation/one/0"]:
                (run / folder).mkdir(parents=True)
            source_hash = hashlib.sha256(b"source").hexdigest()
            generated_hash = hashlib.sha256(b"generated").hexdigest()
            (run / "sources/one.pine").write_bytes(b"source")
            (run / "generation/one/0/source.py").write_bytes(b"generated")
            (run / "source_receipts/one.json").write_text(
                json.dumps(
                    {
                        "id": "one",
                        "status": "captured",
                        "source_file": "sources/one.pine",
                        "source_sha256": source_hash,
                    }
                )
            )
            review = {
                "id": "one",
                "status": "pending_review",
                "source_sha256": source_hash,
                "reviewer": "reviewer",
                "basis": "원문 대조",
                "signal_bindings": [],
            }
            (run / "reviews/one.json").write_text(json.dumps(review))
            (run / "generation/one/status.json").write_text(
                json.dumps(
                    {
                        "publication_id": "one",
                        "status": "completed",
                        "generated_file": "generation/one/0/source.py",
                        "generated_sha256": generated_hash,
                    }
                )
            )
            result = generate(run, output)["progress"]
            self.assertEqual(result["review_records"], 1)
            self.assertEqual(result["review_completed"], 0)
            self.assertEqual(result["review_pending"], 1)
            self.assertEqual(result["generation_verified"], 1)
            self.assertEqual(result["generation_review_approved"], 0)
            review.update(status="reviewed", signal_bindings=[{"direction": "long"}])
            (run / "reviews/one.json").write_text(json.dumps(review))
            code_review = {
                "status": "reviewed_for_isolated_execution",
                "generated_sha256": generated_hash,
                "original_source_sha256": source_hash,
                "reviewer": "reviewer",
                "checks": ["원문 대조"],
            }
            (run / "generation/one/0/code-review.json").write_text(json.dumps(code_review))
            result = generate(run, output)["progress"]
            self.assertEqual(result["review_completed"], 1)
            self.assertEqual(result["generation_review_approved"], 1)
            code_review["generated_sha256"] = "0" * 64
            (run / "generation/one/0/code-review.json").write_text(json.dumps(code_review))
            self.assertEqual(generate(run, output)["progress"]["generation_review_approved"], 0)
            document = (output / "report.html").read_text()
            self.assertIn("정적 분류 기록 1", document)
            self.assertIn("매핑 확정 1", document)
            self.assertNotIn("방향 매핑 검토", document)


if __name__ == "__main__":
    unittest.main()
