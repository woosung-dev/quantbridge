"""무료 생성의 호출 상한·중단·누락·과금 경계를 네트워크 없이 검증한다."""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research import gemini_python_eval as subject  # noqa: E402


class FakeClock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def response():
    return SimpleNamespace(
        payload={
            "source_code": "def on_bar(ctx, state): return {'action':'hold'}",
            "assumptions": [],
        },
        provider="gemini",
        actual_model="actual-version",
        input_tokens=11,
        output_tokens=17,
        thinking_tokens=3,
        total_tokens=31,
        usage_known=True,
    )


def manifest(external=0):
    quotas = {
        model: {
            "rpm": 15,
            "tpm": 1_000_000,
            "operational_attempt_budget": 13,
            "tpd_status": "UNKNOWN_NOT_DISPLAYED",
        }
        for model in subject.MODELS
    }
    return {
        "cohort": "fake",
        "models": list(subject.MODELS),
        "external_generation_attempts": external,
        "rounds": [list(subject.MODELS) for _ in range(13)],
        "schema": {},
        "quota_evidence": {"models": quotas},
        "operational_model_budgets": quotas,
        "listed_models": [
            {"name": f"models/{model}", "supported_actions": ["generateContent"]}
            for model in subject.MODELS
        ],
        "requests": {
            str(index): {
                "case_id": "availability" if index == 0 else f"D{(index - 1) // 2 + 1:02}",
                "repetition": None if index == 0 else (index - 1) % 2,
                "system": "public",
                "user": "request",
            }
            for index in range(13)
        },
    }


class GeminiEvalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.clock = FakeClock()

    def runner(self, data=None, caller=None):
        return subject.Runner(
            self.root,
            data or manifest(),
            None,
            caller=caller or (lambda *args: response()),
            clock=self.clock,
            sleep=self.clock.sleep,
            payload_validator=lambda value: value,
        )

    def test_missing_quota_never_calls_provider(self):
        data = manifest()
        data["operational_model_budgets"] = {}
        calls = []
        runner = self.runner(data, lambda *args: calls.append(args))
        runner.run()
        self.assertEqual(calls, [])
        self.assertEqual(runner.ledger.reserved(), [])
        self.assertEqual(
            subject.read_json(self.root / "trials" / subject.MODELS[0] / "0/not-run.json")[
                "status"
            ],
            "NOT_RUN",
        )

    def test_all_seven_models_have_exactly_thirteen_slots_and_external_calls_reduce_cap(self):
        calls, active = [], set()
        lock = threading.Lock()

        def fake(key, model, request, schema):
            with lock:
                self.assertNotIn(model, active)
                active.add(model)
                self.assertLessEqual(len(active), 2)
                calls.append(model)
            with lock:
                active.remove(model)
            return response()

        runner = self.runner(manifest(external=10), fake)
        runner.run()
        self.assertEqual(len(calls), 81)
        self.assertEqual(len(runner.ledger.reserved()), 81)
        self.assertTrue(all(calls.count(model) <= 13 for model in subject.MODELS))

    def test_interrupted_reservation_is_consumed_and_never_retried(self):
        calls = []

        def interrupted(*args):
            calls.append(1)
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            self.runner(caller=interrupted).attempt(subject.MODELS[0], 0)
        self.runner(caller=interrupted).attempt(subject.MODELS[0], 0)
        self.assertEqual(calls, [1])
        self.assertEqual(len(subject.Ledger(self.root).reserved()), 1)

    def test_429_remains_stopped_after_process_resume_without_error_body(self):
        calls = []

        class QuotaError(Exception):
            status_code = 429

        def fail_after_probe(*args):
            calls.append(1)
            if len(calls) > 1:
                raise QuotaError("secret-key-and-private-url")
            return response()

        runner = self.runner(caller=fail_after_probe)
        runner.attempt(subject.MODELS[0], 0)
        runner.attempt(subject.MODELS[0], 1)
        self.runner(caller=fail_after_probe).attempt(subject.MODELS[0], 2)
        self.assertEqual(len(calls), 2)
        self.assertNotIn(
            "secret-key", "".join(path.read_text() for path in self.root.rglob("*.json*"))
        )

    def test_rpm_and_token_reservations_wait_before_call(self):
        data = manifest()
        quota = data["quota_evidence"]["models"][subject.MODELS[0]]
        quota.update(rpm=5, tpm=30_000)
        runner = self.runner(data)
        runner.attempt(subject.MODELS[0], 0)
        runner.attempt(subject.MODELS[0], 1)
        rows = runner.ledger.reserved()
        self.assertGreaterEqual(rows[1]["epoch"] - rows[0]["epoch"], 60)

    def test_daily_request_and_token_quotas_cannot_be_exceeded(self):
        data = manifest()
        data["operational_model_budgets"][subject.MODELS[0]]["operational_attempt_budget"] = 1
        runner = self.runner(data)
        runner.attempt(subject.MODELS[0], 0)
        runner.attempt(subject.MODELS[0], 1)
        self.assertEqual(len(runner.ledger.reserved()), 1)
        self.assertEqual(
            subject.read_json(self.root / "trials" / subject.MODELS[0] / "1/not-run.json")[
                "reason"
            ],
            "operational_request_budget_exhausted",
        )

    def test_unknown_quota_dimensions_and_wrong_free_project_are_rejected(self):
        self.assertIsNone(
            subject.quota_reason("m", {"rpm": 5, "tpm": 100000, "operational_attempt_budget": 13})
        )
        with self.assertRaises(ValueError):
            subject.build_manifest({"billing_tier_observed": "paid"}, {}, {})

    def test_dashboard_lag_unknown_daily_usage_does_not_become_zero_or_block_approved_budget(self):
        evidence = {
            "models": {
                "gemini-3.8-flash": {
                    "rpm_limit": 5,
                    "tpm_limit": 250000,
                    "rpd_limit": 20,
                    "rpd_headroom_from_display": 20,
                    "rpd_used_today_exact": None,
                    "rpd_remaining_guaranteed": None,
                }
            }
        }
        budget = subject.operational_budgets(evidence)["gemini-3.8-flash"]
        self.assertEqual(budget["operational_attempt_budget"], 13)
        self.assertIsNone(budget["rpd_remaining_guaranteed"])
        self.assertIsNone(budget["rpd_used_today_exact"])
        self.assertEqual(budget["tpd_status"], "UNKNOWN_NOT_DISPLAYED")
        self.assertIsNone(subject.quota_reason("gemini-3.8-flash", budget))

    def test_partial_usage_preserves_known_input_and_unknown_output(self):
        partial = response()
        partial.usage_known = False
        partial.reported_input_tokens = 23
        partial.reported_output_tokens = None
        self.runner(caller=lambda *args: partial).attempt(subject.MODELS[0], 0)
        result = subject.read_json(self.root / "trials" / subject.MODELS[0] / "0/generation.json")
        self.assertEqual(result["usage"]["input_tokens"], 23)
        self.assertIsNone(result["usage"]["output_tokens"])

    def test_invalid_generated_code_keeps_reported_usage_and_source_without_availability(self):
        def reject(value):
            raise ValueError("invalid generated code")

        runner = self.runner()
        runner.payload_validator = reject
        runner.attempt(subject.MODELS[0], 0)
        runner.attempt(subject.MODELS[0], 1)
        folder = self.root / "trials" / subject.MODELS[0] / "0"
        generation = subject.read_json(folder / "generation.json")
        self.assertEqual(generation["status"], "failed")
        self.assertEqual(generation["usage"]["total_tokens"], 31)
        self.assertEqual(generation["actual_model"], "actual-version")
        self.assertEqual(subject.read_json(folder / "payload.json"), response().payload)
        self.assertEqual(len(runner.ledger.reserved()), 1)

    def test_existing_not_run_is_terminal_when_runner_is_restarted(self):
        data = manifest()
        data["operational_model_budgets"] = {}
        self.runner(data).attempt(subject.MODELS[0], 0)
        calls = []
        self.runner(caller=lambda *args: calls.append(args)).attempt(subject.MODELS[0], 0)
        self.assertEqual(calls, [])

    def test_error_categories_do_not_expose_provider_exception_text(self):
        for code, category in ((403, "forbidden"), (404, "not_found"), (429, "quota_exhausted")):
            exc = RuntimeError("secret")
            exc.code = code
            self.assertEqual(subject.safe_error(exc)["error_category"], category)
        self.assertEqual(subject.safe_error(TimeoutError("secret"))["error_category"], "timeout")
        self.assertEqual(subject.safe_error(ValueError("secret"))["error_category"], "validation")

    def test_report_keeps_unrun_unknown_and_records_actual_model_and_usage(self):
        data = manifest()
        subject.write_json(self.root / "manifest.json", data)
        runner = self.runner(data)
        runner.attempt(subject.MODELS[0], 0)
        runner.attempt(subject.MODELS[0], 1)
        result = subject.report(self.root)
        row = result["models"][0]
        self.assertIsNone(row["quality90"])
        self.assertEqual(row["actual_models"], ["actual-version"])
        self.assertEqual(row["reported_usage"][0]["thinking_tokens"], 3)
        self.assertEqual(result["cost"], "UNKNOWN")
        self.assertEqual(result["ranking"], [])

    def test_symlink_credentials_rejected_before_any_secret_file_read(self):
        target = self.root / "not-secret"
        target.write_text("GEMINI_API_KEY=do-not-read")
        link = self.root / "link"
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "심볼릭"):
            subject.load_credentials(link)

    def test_manifest_order_and_public_contract_are_fixed_without_oracle_leak(self):
        free = {
            "billing_tier_observed": "무료 등급",
            "project_id": "p",
            "observed_at_utc": "2026-10-23T00:00:00Z",
            "authorized_generation_attempt_ceiling": 91,
        }
        quota, listed = {"project_id": "p"}, {"project_id": "p", "models": []}
        cases = [(f"D{index:02}", f"public strategy {index}") for index in range(1, 7)]
        with patch.object(
            subject, "contracts", return_value=({}, lambda text: ("public contract", text), cases)
        ):
            first = subject.build_manifest(free, quota, listed)
            second = subject.build_manifest(free, quota, listed)
        self.assertEqual(first, second)
        self.assertEqual(len(first["rounds"]), 13)
        self.assertEqual(first["requests"]["1"]["user"], "public strategy 1")
        self.assertNotIn("expected_action", json.dumps(first["requests"]))


if __name__ == "__main__":
    unittest.main()
