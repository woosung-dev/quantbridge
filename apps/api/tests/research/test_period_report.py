"""보고서의 단위·미산출·A/B 조합·필터·오프라인 안전·분모 회귀."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
            self.assertEqual(result["progress"]["financial_pending"], 60)
            self.assertEqual(result["progress"]["registration_target_max"], 12)


if __name__ == "__main__":
    unittest.main()
