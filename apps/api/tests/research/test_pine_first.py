"""Pine 우선 선택의 성과 독립성·원장 보존·증거 변조 경계를 검증한다."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import pine_first as policy
from tools.research.period_study.state import identity, read, sha, write


class PineFirstTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        write(self.root / "manifest.json", {"source_count": 1, "expected_cells": 60})
        write(self.root / "pine-first/policy.json", {"policy": policy.POLICY, "source_count": 1})
        self.cell = {"publication_id": "one", "timeframe": "1h", "period": "P1", "policy": "A"}
        self.pine = {
            **self.cell,
            "code_path": "pine",
            "status": "not_run",
            "reason": "reviewed_pine_executable_missing",
        }
        source = self.root / "sources/one.pine"
        source.parent.mkdir()
        source.write_text("//@version=6\nindicator('one')\n")
        self.review = {
            "status": "reviewed",
            "source_sha256": sha(source.read_bytes()),
            "reviewer": "test-reviewer",
            "basis": "원문 대조",
            "signal_mode": "shared_events",
            "signal_bindings": [],
            "inputs": {},
            "warmup_bars": 1000,
            "pine_coverage": {"status": "unsupported", "unsupported_functions": ["ta.vwma"]},
        }
        write(self.root / "reviews/one.json", self.review)
        write(
            self.root / "source_receipts/one.json", {"source_sha256": self.review["source_sha256"]}
        )
        self.files = {}
        for kind in ("1h", "1min", "funding"):
            path = self.root / "data/P1" / f"{kind}.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("trusted fixture bytes\n")
            self.files[kind] = {"path": f"P1/{kind}.csv", "sha256": sha(path.read_bytes())}
        self.dataset = {"warmup_bars": 1000, "files": {"P1": self.files}}
        write(self.root / "data/dataset.json", self.dataset)
        self.checkpoint = "cells/one/pine/1h/P1/A/latest.json"
        write(self.root / self.checkpoint, self.pine)
        self.proof = {
            "policy": policy.POLICY,
            "publication_id": "one",
            "cells": [self.cell],
            "reviewer": "test-reviewer",
            "basis": "원문과 미지원 API 대조",
            "failure_kind": "unsupported_api",
            "failure_stage": "source_compilation",
            "required_inputs_satisfied": True,
            "language_conversion_can_resolve": True,
            "evidence": {
                role: self.ref(path)
                for role, path in {
                    "source": "sources/one.pine",
                    "review": "reviews/one.json",
                    "data": "data/dataset.json",
                    "pine_failure": "reviews/one.json",
                    "checkpoint": self.checkpoint,
                    "policy": "pine-first/policy.json",
                }.items()
            },
        }

    def ref(self, relative):
        return {"path": relative, "sha256": sha((self.root / relative).read_bytes())}

    def eligibility(self):
        write(self.root / "pine-first/eligibility/one.json", self.proof)
        return policy._Evidence(self.root).eligibility(self.pine, self.review)

    def test_known_language_failure_requires_actual_complete_evidence_and_exact_scope(self):
        self.assertTrue(self.eligibility()["eligible"])
        self.proof["cells"][0] = {**self.cell, "policy": "B"}
        self.assertFalse(self.eligibility()["eligible"])

    def test_role_omission_and_source_policy_data_tampering_fail_closed(self):
        original = copy.deepcopy(self.proof)
        for role in policy.EVIDENCE_ROLES:
            with self.subTest(role=role):
                self.proof = copy.deepcopy(original)
                del self.proof["evidence"][role]
                self.assertFalse(self.eligibility()["eligible"])
        self.proof = original
        for relative in ("sources/one.pine", "pine-first/policy.json", "data/P1/funding.csv"):
            path = self.root / relative
            before = path.read_bytes()
            path.write_bytes(before + b"tamper")
            self.assertFalse(self.eligibility()["eligible"])
            path.write_bytes(before)

    def test_infrastructure_data_and_empty_tape_cannot_be_overridden_by_static_unsupported(self):
        for reason in (
            "RuntimeError:docker_missing",
            "frozen_dataset_missing",
            "warmup_extension_missing",
            "shared_signal_tape_unavailable",
            "zero_trades",
            "low_profit",
            "timeout",
            "docker_missing:reviewed_pine_executable_missing",
        ):
            with self.subTest(reason=reason):
                self.pine["reason"] = reason
                write(self.root / self.checkpoint, self.pine)
                self.proof["evidence"]["checkpoint"] = self.ref(self.checkpoint)
                self.assertFalse(self.eligibility()["eligible"])

    def test_unverified_flags_and_unapproved_old_python_success_do_not_count(self):
        forged = {**self.proof, "_verified": True}
        classified = policy.classify_pine_failure(
            self.pine, {**self.review, "pine_first_eligibility": forged}
        )
        self.assertFalse(classified["eligible"])
        python = {**self.cell, "code_path": "python", "status": "completed", "total_return": "99"}
        rows = [self.pine, python]
        before = copy.deepcopy(rows)
        view = policy.build_pine_first_view(self.root, rows)
        self.assertEqual(rows, before)
        self.assertEqual(
            view["progress"]["financial_statuses"],
            {"completed": 0, "failed": 0, "not_run": 1, "pending": 29},
        )
        self.assertEqual(view["progress"]["legacy_python_completed_excluded"], 1)

    def test_pine_second_failure_is_recovery_pending_without_python_financial_attempt(self):
        pine = {
            **self.pine,
            "status": "failed",
            "reason": "PineRuntimeError: UDF local history in loops is not supported",
            "execution_attempt": 2,
        }
        write(self.root / self.checkpoint, pine)
        unavailable = {**self.pine, "policy": "B", "reason": "source_data_unavailable"}
        rows = [pine, unavailable]
        before = copy.deepcopy(rows)
        view = policy.build_pine_first_view(self.root, rows)
        recovered = next(row for row in view["rows"] if row["policy"] == "A")
        self.assertEqual(recovered["status"], "pending")
        self.assertTrue(recovered["recovery_pending"])
        self.assertFalse(recovered["failed_terminal"])
        self.assertEqual(recovered["original_path_status"], "failed")
        self.assertEqual(recovered["reason"], pine["reason"])
        self.assertEqual(recovered["original_path_reason"], pine["reason"])
        self.assertEqual(view["progress"]["financial_recovery_pending"], 1)
        self.assertEqual(view["progress"]["financial_failed_terminal"], 0)
        self.assertEqual(
            view["progress"]["financial_statuses"],
            {"completed": 0, "failed": 0, "not_run": 1, "pending": 29},
        )
        self.assertEqual(rows, before)
        self.assertEqual(read(self.root / self.checkpoint), pine)

    def test_only_verified_python_financial_retry_exhaustion_is_terminal(self):
        pine = {**self.pine, "status": "failed", "execution_attempt": 2}
        proof = {"eligible": True, "_verified": policy._VERIFIED}
        for extra, terminal in (
            ({"execution_attempt": 1, "attempt": 99}, False),
            ({"execution_attempt": 2}, True),
            ({"execution_attempt": 1, "bounded_retries_exhausted": True}, True),
            ({"execution_attempt": 1, "bounded_retries_exhausted": "true"}, False),
        ):
            with self.subTest(extra=extra):
                python = {
                    **self.cell,
                    "code_path": "python",
                    "status": "failed",
                    "reason": "PythonRuntimeError: isolated financial execution failed",
                    "_same_input_verified": policy._VERIFIED,
                    **extra,
                }
                chosen = policy.choose_logical_cell(pine, python, proof)
                self.assertEqual(chosen["status"], "failed" if terminal else "pending")
                self.assertEqual(chosen["recovery_pending"], not terminal)
                self.assertEqual(chosen["failed_terminal"], terminal)
                self.assertEqual(chosen["reason"], python["reason"])
                self.assertEqual(chosen["original_path_status"], "failed")
                self.assertNotIn("total_return", chosen)
                self.assertEqual(python["status"], "failed")
        # 생성 실패나 미승인 대체 행은 금융 재시도 소진의 증거가 아니다.
        unapproved = {**python, "execution_attempt": 2}
        unapproved.pop("_same_input_verified")
        unchanged = policy.choose_logical_cell(self.pine, unapproved, proof)
        self.assertEqual(unchanged["status"], "not_run")
        self.assertEqual(unchanged["reason"], self.pine["reason"])

    def completed_fixture(self, language="pine"):
        code = "compiled source fixture"
        path = self.root / f"adapted/one.{language}"
        path.parent.mkdir(exist_ok=True)
        path.write_text(code)
        self.review.update(
            adapted_file=str(path.relative_to(self.root)), adapted_sha256=sha(path.read_bytes())
        )
        write(self.root / "reviews/one.json", self.review)
        mapping = identity(
            {
                "source_sha256": self.review["source_sha256"],
                "inputs": {},
                "signal_bindings": [],
                "signal_mode": "shared_events",
            }
        )
        images = {"pine": "sha256:pine", "python": "sha256:python"}
        write(self.root / "runtime-smoke.json", {"image_ids": images})
        cell = {**self.cell, "code_path": language}
        self.request = {
            "cell": cell,
            "source_sha256": sha(path.read_bytes()),
            "parameters": {},
            "signal_mode": "shared_events",
            "warmup_bars": 1000,
            "costs": policy.COSTS,
            "mapping_hash": mapping,
            "dataset_sha256": identity(self.dataset),
            "data_files": self.files,
            "implementation": {"fixture": "same"},
            "image_ids": images,
            "policy": {
                "contract_version": 1,
                "exit_policy": "signal_only_v1",
                "reentry_policy": "close_then_reenter_v1",
                "signal_mode": "shared_events",
                "signal_mapping_hash": mapping,
            },
        }
        return self.save_completed(cell)

    def save_completed(self, cell):
        request_hash = identity(self.request)
        folder = "cells/one/" + cell["code_path"] + "/1h/P1/A"
        result_file = folder + "/result.json"
        write(self.root / result_file, {"request": self.request})
        record = {
            **cell,
            "status": "completed",
            "request_hash": request_hash,
            "result_file": result_file,
            "result_sha256": sha((self.root / result_file).read_bytes()),
            "metrics": {"total_return": "-0.5", "closed_episodes": 0},
        }
        write(self.root / folder / f"request-{request_hash}.json", self.request)
        write(self.root / folder / "latest.json", record)
        return {**record, **record["metrics"]}

    def test_verified_pine_wins_with_zero_trades_and_loss_and_result_mutation_excludes_it(self):
        row = self.completed_fixture()
        old_python = {**row, "code_path": "python", "total_return": "100"}
        with patch(
            "tools.research.period_study.controller.implementation",
            return_value={"fixture": "same"},
        ):
            view = policy.build_pine_first_view(self.root, [row, old_python])
            self.assertEqual(view["progress"]["pine_completed"], 1)
            self.assertEqual(view["rows"][0]["total_return"], "-0.5")
            self.assertEqual(view["rows"][0]["closed_episodes"], 0)
            (self.root / row["result_file"]).write_text("changed")
            after = policy.build_pine_first_view(self.root, [row, old_python])
            self.assertEqual(after["progress"]["financial_statuses"]["completed"], 0)
            self.assertEqual(after["progress"]["financial_pending"], 30)

    def test_stale_source_review_and_changed_costs_images_implementation_are_not_current_success(
        self,
    ):
        row = self.completed_fixture()
        for field, value in (
            ("costs", {}),
            ("image_ids", {}),
            ("implementation", {}),
            ("parameters", {"new": 1}),
        ):
            with self.subTest(field=field):
                previous = self.request[field]
                self.request[field] = value
                altered = self.save_completed({**self.cell, "code_path": "pine"})
                with patch(
                    "tools.research.period_study.controller.implementation",
                    return_value={"fixture": "same"},
                ):
                    view = policy.build_pine_first_view(self.root, [altered])
                self.assertEqual(view["progress"]["pine_completed"], 0)
                self.request[field] = previous
        self.save_completed({**self.cell, "code_path": "pine"})
        (self.root / "sources/one.pine").write_text("new source")
        with patch(
            "tools.research.period_study.controller.implementation",
            return_value={"fixture": "same"},
        ):
            self.assertEqual(
                policy.build_pine_first_view(self.root, [row])["progress"]["pine_completed"], 0
            )

    def test_shared_b_runtime_is_not_a_source_execution_failure(self):
        self.pine.update(
            policy="B", status="failed", reason="PineRuntimeError: supported diagnosis"
        )
        proof = {
            **self.proof,
            "failure_kind": "pine_runtime_language",
            "failure_stage": "source_evaluation",
            "_verified": policy._VERIFIED,
        }
        result = policy.classify_pine_failure(
            self.pine, {**self.review, "pine_first_eligibility": proof}
        )
        self.assertEqual(result["reason"], "shared_events_B_does_not_execute_source")

    def python_completed_fixture(self, *, pinned=True):
        row = self.completed_fixture("python")
        self.review.pop("adapted_file")
        self.review.pop("adapted_sha256")
        write(self.root / "reviews/one.json", self.review)
        source = (self.root / "sources/one.pine").read_text()
        generated = "adapted/one.python"
        generated_sha = sha((self.root / generated).read_bytes())
        status = {
            "status": "completed",
            "attempt": 0,
            "source_sha256": self.review["source_sha256"],
            "generated_file": generated,
            "generated_sha256": generated_sha,
            "input_hash": identity(
                {
                    "source": source,
                    "signal_bindings": [],
                    "inputs": {},
                    "signal_mode": "shared_events",
                }
            ),
        }
        approval = {
            "status": "reviewed_for_isolated_execution",
            "reviewer": "test",
            "original_source_sha256": self.review["source_sha256"],
            "generated_sha256": generated_sha,
        }
        write(self.root / "generation/one/status.json", status)
        write(self.root / "generation/one/0/code-review.json", approval)
        self.request["generated_code_review_sha256"] = sha(
            (self.root / "generation/one/0/code-review.json").read_bytes()
        )
        row = self.save_completed({**self.cell, "code_path": "python"})
        self.proof["evidence"]["review"] = self.ref("reviews/one.json")
        self.proof["evidence"]["pine_failure"] = self.ref("reviews/one.json")
        self.proof["python_request_hash"] = row["request_hash"] if pinned else None
        self.eligibility()
        return row, approval

    def test_python_reuse_is_scoped_to_reviewed_request_and_matching_approval(self):
        row, approval = self.python_completed_fixture()
        with patch(
            "tools.research.period_study.controller.implementation",
            return_value={"fixture": "same"},
        ):
            view = policy.build_pine_first_view(self.root, [self.pine, row])
            self.assertEqual(view["progress"]["python_fallback_completed"], 1)
            self.assertEqual(view["rows"][0]["code_path"], "python")
            write(self.root / "report-input.json", {"cells": [self.pine, row]})
            descriptors = []
            self.assertEqual(
                policy.native_code_paths(self.root, "one", "1h", descriptors), ("python",)
            )
            self.assertEqual(descriptors, [self.ref("pine-first/eligibility/one.json")])
            checkpoint = self.root / "cells/one/python/1h/P1/A/latest.json"
            completed_record = read(checkpoint)
            for execution_attempt in (1, 2):
                failed = {
                    key: value
                    for key, value in completed_record.items()
                    if key not in {"result_file", "result_sha256", "metrics"}
                }
                failed.update(
                    status="failed",
                    reason="PythonRuntimeError: isolated financial execution failed",
                    execution_attempt=execution_attempt,
                )
                write(checkpoint, failed)
                # export가 생략하거나 잘못 전달한 retry 번호 대신 실제 checkpoint를 쓴다.
                exported_failure = {**failed, "execution_attempt": 99}
                retries = policy.build_pine_first_view(self.root, [self.pine, exported_failure])
                self.assertEqual(retries["rows"][0]["execution_attempt"], execution_attempt)
                self.assertEqual(
                    retries["rows"][0]["status"],
                    "pending" if execution_attempt == 1 else "failed",
                )
                self.assertEqual(
                    retries["progress"]["financial_recovery_pending"],
                    1 if execution_attempt == 1 else 0,
                )
                self.assertEqual(
                    retries["progress"]["financial_failed_terminal"],
                    0 if execution_attempt == 1 else 1,
                )
                self.assertEqual(read(checkpoint), failed)
            write(checkpoint, completed_record)
            # A에 대한 명시 증거가 B의 기존 성공으로 번지지 않는다.
            b = {**row, "policy": "B"}
            other = policy.build_pine_first_view(self.root, [self.pine, row, b])
            self.assertEqual(other["progress"]["python_fallback_completed"], 1)
            self.assertEqual(other["progress"]["financial_pending"], 29)
            write(
                self.root / "generation/one/0/code-review.json", {**approval, "reviewer": "changed"}
            )
            invalid = policy.build_pine_first_view(self.root, [self.pine, row])
            self.assertEqual(invalid["progress"]["python_fallback_completed"], 0)

    def completion_fixture(self, *, request_change=None, status="completed", execution_attempt=1,
                           failure_reason="PythonRuntimeError: isolated financial execution failed"):
        self.python_completed_fixture(pinned=False)
        self.request.update(request_change or {})
        row = self.save_completed({**self.cell, "code_path": "python"})
        folder = "cells/one/python/1h/P1/A"
        result_file = f"{folder}/result-{row['request_hash']}.json.gz"
        write(self.root / result_file, read(self.root / row["result_file"]))
        record = {
            key: value for key, value in row.items() if key not in row["metrics"]
        }
        record.update(attempt=execution_attempt, result_file=result_file,
                      result_sha256=sha((self.root / result_file).read_bytes()))
        if status == "failed":
            for key in ("result_file", "result_sha256", "metrics"):
                record.pop(key)
            record.update(status="failed", execution_attempt=execution_attempt,
                          reason=failure_reason)
        attempt_file = f"{folder}/attempt-{record['attempt']:03}.json"
        write(self.root / folder / "latest.json", record)
        write(self.root / attempt_file, record)
        self.completion_row = {**record, **record.get("metrics", {})}
        eligibility = self.ref("pine-first/eligibility/one.json")
        job = {
            "publication_id": "one", "code_path": "python", "timeframe": "1h", "period": "P1",
            "policies": ["A"], "eligibility_proofs": [eligibility],
            "policy_sha256": self.ref("pine-first/policy.json")["sha256"],
            "input_evidence": [self.ref(name) for name in (
                "sources/one.pine", "reviews/one.json", "data/dataset.json", "runtime-smoke.json",
                "generation/one/status.json", "generation/one/0/code-review.json", "adapted/one.python",
                "data/P1/1h.csv", "data/P1/1min.csv", "data/P1/funding.csv",
            )],
        }
        job["job_hash"] = identity(job)
        job_file = f"pine-first/jobs/{job['job_hash']}.json"
        write(self.root / job_file, job)
        worker_file = f"pine-first/jobs/{job['job_hash']}/worker-status.json"
        write(self.root / worker_file, {
            "job_hash": job["job_hash"], "status": "completed", "phase": "common_engine_dispatch",
            "run_group_calls": 1, "dispatched_policies": ["A"], "results": [record],
            "selection_evidence": [{"policy": "A", "proof_file": eligibility["path"],
                                    "proof_sha256": eligibility["sha256"]}],
        })
        self.completion = {
            "schema_version": 1, "cell": {**self.cell, "code_path": "python"},
            "request_hash": row["request_hash"], "eligibility": eligibility,
            "job": self.ref(job_file), "worker_status": self.ref(worker_file),
            "checkpoint": self.ref(attempt_file),
            "request": self.ref(f"{folder}/request-{row['request_hash']}.json"),
            **({"result": self.ref(result_file)} if status == "completed" else {}),
        }
        self.completion_path = (
            self.root / "pine-first/completions/one/1h/P1/A"
            / f"{row['request_hash']}-attempt-{record['attempt']:03}.json"
        )
        write(self.completion_path, self.completion)
        return self.completion_row

    def completion_count(self, row):
        with patch("tools.research.period_study.controller.implementation", return_value={"fixture": "same"}):
            return policy.build_pine_first_view(self.root, [self.pine, row])["progress"]["python_fallback_completed"]

    def rewrite_completion_job(self, changes):
        job = read(self.root / self.completion["job"]["path"])
        worker = read(self.root / self.completion["worker_status"]["path"])
        job.update(changes)
        job["job_hash"] = identity({key: value for key, value in job.items() if key != "job_hash"})
        job_path = f"pine-first/jobs/{job['job_hash']}.json"
        worker_path = f"pine-first/jobs/{job['job_hash']}/worker-status.json"
        worker["job_hash"] = job["job_hash"]
        write(self.root / job_path, job)
        write(self.root / worker_path, worker)
        self.completion.update(job=self.ref(job_path), worker_status=self.ref(worker_path))
        write(self.completion_path, self.completion)

    def test_unpinned_new_python_completion_uses_append_only_binding(self):
        row = self.completion_fixture()
        proof_before = (self.root / "pine-first/eligibility/one.json").read_bytes()
        self.assertEqual(self.completion_count(row), 1)
        self.assertEqual((self.root / "pine-first/eligibility/one.json").read_bytes(), proof_before)
        self.completion_path.unlink()
        self.assertEqual(self.completion_count(row), 0)

    def test_completion_legacy_success_path_remains_compatible_without_failed_fallback(self):
        row = self.completion_fixture()
        legacy = self.completion_path.with_name(f"{row['request_hash']}.json")
        self.completion_path.rename(legacy)
        self.assertEqual(self.completion_count(row), 1)
        write(self.completion_path, {"schema_version": 1})
        self.assertEqual(self.completion_count(row), 0)
        row = self.completion_fixture(status="failed", execution_attempt=2)
        self.completion_path.replace(legacy)
        with patch("tools.research.period_study.controller.implementation", return_value={"fixture": "same"}):
            view = policy.build_pine_first_view(self.root, [self.pine, row])
        self.assertEqual(view["progress"]["financial_failed_terminal"], 0)

    def test_unpinned_python_failed_execution_uses_actual_attempt_for_terminal_status(self):
        for execution_attempt in (1, 2):
            with self.subTest(execution_attempt=execution_attempt):
                row = self.completion_fixture(status="failed", execution_attempt=execution_attempt)
                proof_before = (self.root / "pine-first/eligibility/one.json").read_bytes()
                with patch("tools.research.period_study.controller.implementation", return_value={"fixture": "same"}):
                    view = policy.build_pine_first_view(self.root, [self.pine, row])
                self.assertEqual(view["rows"][0]["code_path"], "python")
                self.assertEqual(view["rows"][0]["status"], "pending" if execution_attempt == 1 else "failed")
                self.assertEqual(view["progress"]["financial_failed_terminal"], 0 if execution_attempt == 1 else 1)
                self.assertEqual(view["progress"]["financial_recovery_pending"], 1 if execution_attempt == 1 else 0)
                self.assertEqual((self.root / "pine-first/eligibility/one.json").read_bytes(), proof_before)

    def test_previous_completion_attempt_cannot_substitute_current_execution(self):
        row = self.completion_fixture(status="failed", execution_attempt=2)
        previous = self.completion_path.with_name(f"{row['request_hash']}-attempt-001.json")
        self.completion_path.rename(previous)
        with patch("tools.research.period_study.controller.implementation", return_value={"fixture": "same"}):
            view = policy.build_pine_first_view(self.root, [self.pine, row])
        self.assertEqual(view["progress"]["financial_failed_terminal"], 0)

    def test_runner_unavailable_is_recovery_after_two_attempts_and_reason_is_not_forgeable(self):
        row = self.completion_fixture(status="failed", execution_attempt=2,
                                      failure_reason="PythonRunnerUnavailable:격리 실행기를 시작할 수 없습니다")
        with patch("tools.research.period_study.controller.implementation", return_value={"fixture": "same"}):
            view = policy.build_pine_first_view(self.root, [self.pine, row])
            selected = view["rows"][0]
            self.assertEqual(selected["code_path"], "python")
            self.assertEqual(selected["failure_category"], "infrastructure")
            self.assertEqual(selected["status"], "pending")
            self.assertEqual(view["progress"]["financial_recovery_pending"], 1)
            self.assertEqual(view["progress"]["financial_failed_terminal"], 0)
            forged = {**row, "reason": "PythonRuntimeError: forged strategy execution failure"}
            invalid = policy.build_pine_first_view(self.root, [self.pine, forged])
            self.assertEqual(invalid["progress"]["financial_failed_terminal"], 0)
            self.assertNotEqual(invalid["rows"][0]["code_path"], "python")

    def test_failed_completion_requires_request_scope_worker_and_exact_attempt(self):
        row = self.completion_fixture(status="failed", execution_attempt=2)
        original = copy.deepcopy(self.completion)
        worker_path = self.root / original["worker_status"]["path"]
        worker_before = worker_path.read_bytes()
        for changed in ("request", "cell", "worker", "attempt", "result"):
            with self.subTest(changed=changed):
                value = copy.deepcopy(original)
                if changed == "request":
                    del value["request"]
                elif changed == "cell":
                    value["cell"]["period"] = "P2"
                elif changed == "worker":
                    worker = read(worker_path)
                    worker["status"] = "failed"
                    write(worker_path, worker)
                    value["worker_status"] = self.ref(str(worker_path.relative_to(self.root)))
                elif changed == "attempt":
                    wrong = "cells/one/python/1h/P1/A/attempt-001.json"
                    write(self.root / wrong, read(self.root / original["checkpoint"]["path"]))
                    value["checkpoint"] = self.ref(wrong)
                else:
                    value["result"] = self.ref(original["request"]["path"])
                write(self.completion_path, value)
                with patch("tools.research.period_study.controller.implementation", return_value={"fixture": "same"}):
                    view = policy.build_pine_first_view(self.root, [self.pine, row])
                self.assertEqual(view["progress"]["financial_failed_terminal"], 0)
                worker_path.write_bytes(worker_before)

    def test_completion_roles_and_cell_cannot_be_forged(self):
        row = self.completion_fixture()
        for role in ("eligibility", "job", "worker_status", "checkpoint", "request", "result"):
            with self.subTest(role=role):
                value = copy.deepcopy(self.completion)
                del value[role]
                write(self.completion_path, value)
                self.assertEqual(self.completion_count(row), 0)
        value = copy.deepcopy(self.completion)
        value["cell"]["policy"] = "B"
        write(self.completion_path, value)
        self.assertEqual(self.completion_count(row), 0)

    def test_completion_job_proof_worker_and_result_tampering_is_rejected(self):
        row = self.completion_fixture()
        for role in ("eligibility", "result"):
            with self.subTest(role=role):
                value = copy.deepcopy(self.completion)
                value[role]["sha256"] = "0" * 64
                write(self.completion_path, value)
                self.assertEqual(self.completion_count(row), 0)
        job_path = self.root / self.completion["job"]["path"]
        original = job_path.read_bytes()
        job = read(job_path)
        job["job_hash"] = "0" * 64
        write(job_path, job)
        value = copy.deepcopy(self.completion)
        value["job"] = self.ref(str(job_path.relative_to(self.root)))
        write(self.completion_path, value)
        self.assertEqual(self.completion_count(row), 0)
        job_path.write_bytes(original)
        worker_path = self.root / self.completion["worker_status"]["path"]
        original_worker = worker_path.read_bytes()
        for fields in ({"status": "failed"}, {"phase": "no_new_calculation"}, {"run_group_calls": 0}):
            with self.subTest(fields=fields):
                worker = read(worker_path)
                worker.update(fields)
                write(worker_path, worker)
                value = copy.deepcopy(self.completion)
                value["worker_status"] = self.ref(str(worker_path.relative_to(self.root)))
                write(self.completion_path, value)
                self.assertEqual(self.completion_count(row), 0)
                worker_path.write_bytes(original_worker)

    def test_completion_does_not_bypass_current_inputs_or_explicit_old_pin(self):
        row = self.completion_fixture(request_change={"costs": {**policy.COSTS, "maker": "0"}})
        self.assertEqual(self.completion_count(row), 0)
        row = self.completion_fixture()
        write(self.root / "pine-first/policy.json", {"policy": policy.POLICY, "source_count": 2})
        self.assertEqual(self.completion_count(row), 0)
        write(self.root / "pine-first/policy.json", {"policy": policy.POLICY, "source_count": 1})
        self.proof["python_request_hash"] = "f" * 64
        self.eligibility()
        with patch.object(policy._Evidence, "completion_binding", side_effect=AssertionError("명시 pin에는 진입 금지")) as fallback:
            self.assertEqual(self.completion_count(row), 0)
            fallback.assert_not_called()

    def test_validly_hashed_job_still_requires_scope_policy_and_all_inputs(self):
        row = self.completion_fixture()
        original = copy.deepcopy(self.completion)
        for changes in (
            {"period": "P2"}, {"code_path": "pine"}, {"policies": ["B"]},
            {"eligibility_proofs": []}, {"policy_sha256": "0" * 64}, {"input_evidence": []},
            {"input_evidence": [{"path": "data/P1/1min.csv", "sha256": "0" * 64}]},
        ):
            with self.subTest(changes=changes):
                self.completion = copy.deepcopy(original)
                self.rewrite_completion_job(changes)
                self.assertEqual(self.completion_count(row), 0)

    def test_completion_rejects_foreign_paths_and_different_worker_result_or_proof(self):
        row = self.completion_fixture()
        for role in ("checkpoint", "request", "result"):
            with self.subTest(role=role):
                value = copy.deepcopy(self.completion)
                original = self.root / value[role]["path"]
                foreign = self.root / "foreign" / original.name
                foreign.parent.mkdir(exist_ok=True)
                foreign.write_bytes(original.read_bytes())
                value[role] = self.ref(str(foreign.relative_to(self.root)))
                write(self.completion_path, value)
                self.assertEqual(self.completion_count(row), 0)
        worker_path = self.root / self.completion["worker_status"]["path"]
        original = read(worker_path)
        for changed in ("result", "proof"):
            with self.subTest(changed=changed):
                worker = copy.deepcopy(original)
                if changed == "result":
                    worker["results"][0]["result_sha256"] = "0" * 64
                else:
                    worker["selection_evidence"][0]["proof_sha256"] = "0" * 64
                write(worker_path, worker)
                value = copy.deepcopy(self.completion)
                value["worker_status"] = self.ref(str(worker_path.relative_to(self.root)))
                write(self.completion_path, value)
                self.assertEqual(self.completion_count(row), 0)

    def test_duplicate_rows_rejected_and_native_legacy_is_preserved(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            policy.build_pine_first_view(self.root, [self.pine, self.pine])
        self.assertEqual(policy.native_code_paths(self.root, "one", "1h"), ("pine",))
        (self.root / "pine-first/policy.json").unlink()
        self.assertEqual(policy.native_code_paths(self.root, "one", "1h"), ("pine", "python"))

    def test_shared_b_dependency_requires_actual_matching_A_language_failure(self):
        parent = self.eligibility()
        self.assertTrue(parent["eligible"])
        b = {**self.pine, "policy": "B", "reason": "shared_signal_tape_unavailable"}
        write(self.root / "cells/one/pine/1h/P1/B/latest.json", b)
        proof = {
            **copy.deepcopy(self.proof),
            "cells": [{**self.cell, "policy": "B"}],
            "failure_kind": "shared_signal_dependency",
            "failure_stage": "source_dependency",
            "requires_python_A_signal_tape": True,
        }
        proof["evidence"].update(
            pine_failure=self.ref("cells/one/pine/1h/P1/B/latest.json"),
            checkpoint=self.ref("cells/one/pine/1h/P1/B/latest.json"),
            parent_checkpoint=self.ref(self.checkpoint),
            parent_eligibility=self.ref(parent["proof_file"]),
        )
        path = self.root / "pine-first/eligibility/one/1h/P1/B.json"
        write(path, proof)
        self.assertTrue(policy._Evidence(self.root).eligibility(b, self.review)["eligible"])
        # 정상 Pine A에서 생긴 빈 테이프는 전환의 원인이 되지 않는다.
        write(self.root / self.checkpoint, {**self.pine, "status": "completed"})
        proof["evidence"]["parent_checkpoint"] = self.ref(self.checkpoint)
        write(path, proof)
        self.assertFalse(policy._Evidence(self.root).eligibility(b, self.review)["eligible"])

    def test_orchestration_compatibility_rejects_numeric_or_unarchived_change(self):
        controller = "tools/research/period_study/controller.py"
        before = (
            "def run_group(x):\n cells = [p for p in ('A', 'B')]\n tape = []\n return cells, tape\n"
        )
        after = (
            "def run_group(x, *, policies=('A', 'B'), signal_tape=None):\n"
            " if policies not in (('A','B'), ('A',), ('B',)):\n  raise ValueError('scope')\n"
            " if signal_tape is not None and policies != ('B',):\n  raise ValueError('tape')\n"
            " cells = [p for p in policies]\n tape = signal_tape if signal_tape is not None else []\n return cells, tape\n"
        )
        old = {controller: sha(before.encode()), "engine.py": sha(b"same math")}
        new = {controller: sha(after.encode()), "engine.py": sha(b"same math")}
        for mapping, raw in ((old, before), (new, after)):
            prefix = self.root / "implementation-snapshots" / identity(mapping)
            file = prefix / controller
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(raw)
            (prefix / "engine.py").write_bytes(b"same math")
        receipt = {
            "status": "verified",
            "old_implementation": old,
            "new_implementation": new,
            "changed_files": [controller],
        }
        write(self.root / "pine-first/orchestration-epoch.json", receipt)
        self.assertTrue(policy.compatible_implementation(self.root, old, new))
        self.assertFalse(
            policy.compatible_implementation(self.root, old, {**new, "engine.py": "0" * 64})
        )
        (self.root / "implementation-snapshots" / identity(new) / controller).write_text(
            after + "\nprofit = 100\n"
        )
        self.assertFalse(policy.compatible_implementation(self.root, old, new))

    def test_unverified_pine_completed_without_result_is_pending(self):
        row = {**self.pine, "status": "completed", "total_return": "100"}
        view = policy.build_pine_first_view(self.root, [row])
        self.assertEqual(view["rows"], [])
        self.assertEqual(view["progress"]["financial_pending"], 30)
        self.assertEqual(read(self.root / self.checkpoint)["status"], "not_run")
