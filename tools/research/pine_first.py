"""기존 원장을 보존하며 Pine 우선 논리 셀과 증거가 있는 대체 경로를 고른다."""

from __future__ import annotations

import ast
import copy
from collections import Counter
from pathlib import Path

from tools.research.period_study.schema import COSTS
from tools.research.period_study.state import checked, identity, read, sha

POLICY = "pine_first_v1"
IDENTITY = ("publication_id", "timeframe", "period", "policy")
LANGUAGE_FAILURES = {"unsupported_syntax", "unsupported_api", "pine_runtime_language"}
EVIDENCE_ROLES = {"source", "review", "data", "pine_failure", "checkpoint", "policy"}
STATUSES = ("completed", "failed", "not_run", "pending")
_VERIFIED = object()
NON_LANGUAGE_REASONS = (
    "missing_source",
    "source_missing",
    "missing_data",
    "dataset_missing",
    "warmup",
    "market_context_unavailable",
    "docker",
    "gvisor",
    "runsc",
    "image_identity",
    "timeout",
    "empty_signal_tape",
    "signal_tape",
    "signal_hash",
    "zero_trade",
    "low_profit",
    "reviewed_pine_executable_missing",
    "broker_feedback",
)


def _key(row: dict) -> tuple:
    return tuple(row.get(name) for name in IDENTITY)


def _metadata_epoch(run: Path, saved: dict, baseline: dict) -> bool:
    controller = "tools/research/period_study/controller.py"
    if saved.keys() != baseline.keys() or any(
        saved[k] != baseline[k] for k in saved if k != controller
    ):
        return False
    for path in (run / "registration-candidates/harness").glob("comparison-*.json"):
        comparison = read(path)
        controllers = []
        for role in ("financial_epoch", "native_epoch"):
            entry = comparison[role]["harness_receipt"]
            receipt = read(checked(run, entry["path"], entry["sha256"]))
            files = {
                item["source_file"]: checked(run, item["path"], item["sha256"])
                for item in receipt["frozen_harness"]
            }
            controllers.append(files[controller])
        if [sha(p.read_bytes()) for p in controllers] != [saved[controller], baseline[controller]]:
            continue
        trees = [ast.parse(p.read_text()) for p in controllers]
        bodies = []
        for tree in trees:
            function = copy.deepcopy(
                next(
                    n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_group"
                )
            )
            removed = 0
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "base"
                    and node.func.attr == "update"
                ):
                    removed += sum(k.arg == "market_context_proof" for k in node.keywords)
                    node.keywords = [k for k in node.keywords if k.arg != "market_context_proof"]
            if removed not in (0, 1):
                return False
            bodies.append(ast.dump(function))
            tree.body = [
                n
                for n in tree.body
                if not isinstance(n, ast.FunctionDef) or n.name not in {"artifact", "run_group"}
            ]
        return bodies[0] == bodies[1] and ast.dump(trees[0]) == ast.dump(trees[1])
    return False


def compatible_implementation(run: Path, saved: dict, current: dict) -> bool:
    """선택 인자만 추가한 명시 epoch는 원본 bytes와 한정 AST 비교 후 재사용한다."""
    if saved == current:
        return True
    path = run / "pine-first/orchestration-epoch.json"
    if not path.exists():
        return False
    try:
        proof = read(path)
        controller = "tools/research/period_study/controller.py"
        baseline = proof.get("old_implementation", {})
        if saved != baseline and not _metadata_epoch(run, saved, baseline):
            return False
        if (
            proof.get("status") != "verified"
            or proof.get("new_implementation") != current
            or proof.get("changed_files") != [controller]
            or baseline.keys() != current.keys()
            or any(baseline[k] != current[k] for k in baseline if k != controller)
        ):
            return False
        archives = []
        for mapping in (baseline, current):
            prefix = f"implementation-snapshots/{identity(mapping)}/"
            for name, expected in mapping.items():
                checked(run, prefix + name, expected)
            archives.append(ast.parse((run / prefix / controller).read_text()))
        before, after = archives
        original = next(
            n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == "run_group"
        )
        selected = next(
            n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == "run_group"
        )
        if (
            [arg.arg for arg in selected.args.kwonlyargs] != ["policies", "signal_tape"]
            or [ast.unparse(v) for v in selected.args.kw_defaults] != ["('A', 'B')", "None"]
            or [ast.unparse(n.test) for n in selected.body[:2]]
            != [
                "policies not in (('A', 'B'), ('A',), ('B',))",
                "signal_tape is not None and policies != ('B',)",
            ]
            or not all(isinstance(n.body[0], ast.Raise) and not n.orelse for n in selected.body[:2])
        ):
            return False
        selected.args = copy.deepcopy(original.args)
        selected.body = selected.body[2:]
        changed = set()
        for node in selected.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
                continue
            if node.targets[0].id == "cells":
                if ast.unparse(node.value.generators[0].iter) != "policies":
                    return False
                node.value.generators[0].iter = ast.parse("('A', 'B')", mode="eval").body
                changed.add("cells")
            elif node.targets[0].id == "tape":
                if ast.unparse(node.value) != "signal_tape if signal_tape is not None else []":
                    return False
                node.value = ast.parse("[]", mode="eval").body
                changed.add("tape")
        return changed == {"cells", "tape"} and ast.dump(before) == ast.dump(after)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        return False


def classify_pine_failure(pine_record: dict | None, review: dict) -> dict:
    """순수 분류. 파일 검증 전의 선언만으로 대체 적격을 부여하지 않는다."""
    pine = pine_record or {}
    proof = review.get("pine_first_eligibility", {})
    result = {"eligible": False, "reason": "unverified_language_failure"}
    if pine.get("status") == "completed":
        return {**result, "reason": "pine_completed"}
    if review.get("status") != "reviewed":
        return {**result, "reason": "source_review_not_ready"}
    reason = str(pine.get("reason", "")).lower()
    dependency = (
        proof.get("failure_kind") == "shared_signal_dependency"
        and pine.get("policy") == "B"
        and pine.get("status") == "not_run"
        and reason == "shared_signal_tape_unavailable"
        and review.get("signal_mode") == "shared_events"
        and proof.get("requires_python_A_signal_tape") is True
    )
    # 지원 문법 목록은 실행 파일 부재만으로 생긴 실패와 구별한다.
    if not dependency and (
        any(
            fragment in reason
            for fragment in NON_LANGUAGE_REASONS
            if fragment != "reviewed_pine_executable_missing"
        )
        or (
            "reviewed_pine_executable_missing" in reason
            and proof.get("failure_kind") not in {"unsupported_syntax", "unsupported_api"}
        )
    ):
        return {**result, "reason": "non_language_failure"}
    if (
        pine.get("policy") == "B"
        and pine.get("status") == "failed"
        and review.get("signal_mode") == "shared_events"
    ):
        return {**result, "reason": "shared_events_B_does_not_execute_source"}
    if proof.get("failure_kind") not in LANGUAGE_FAILURES and not dependency:
        return {**result, "reason": "not_a_language_failure"}
    if (
        proof.get("failure_stage") not in {"source_compilation", "source_evaluation"}
        and not dependency
    ):
        return {**result, "reason": "failure_stage_not_language_execution"}
    if (
        pine.get("status") in {"failed", "not_run"}
        and proof.get("failure_kind") in {"unsupported_syntax", "unsupported_api"}
        and "reviewed_pine_executable_missing" not in reason
    ):
        return {**result, "reason": "current_failure_not_known_language_failure"}
    if not (
        proof.get("required_inputs_satisfied") is True
        and proof.get("language_conversion_can_resolve") is True
    ):
        return {**result, "reason": "required_inputs_not_proven"}
    if proof.get("_verified") is not _VERIFIED:
        return result
    return {
        "eligible": True,
        "reason": proof["failure_kind"],
        "evidence": proof["evidence"],
        "proof_file": proof["proof_file"],
        "proof_sha256": proof["proof_sha256"],
        "_verified": _VERIFIED,
        "python_request_hash": proof.get("python_request_hash"),
    }


def _logical_failure_status(row: dict) -> dict:
    """원시 경로 실패를 복구 대기와 대체 금융 재시도 소진으로 구분한다."""
    if row.get("status") != "failed":
        return row
    infrastructure = row.get("code_path") == "python" and str(row.get("reason", "")).startswith(
        "PythonRunnerUnavailable:"
    )
    terminal = not infrastructure and row.get("code_path") == "python" and (
        (type(row.get("execution_attempt")) is int and row["execution_attempt"] == 2)
        or row.get("bounded_retries_exhausted") is True
    )
    return {
        **row,
        "status": "failed" if terminal else "pending",
        "original_path_status": "failed",
        "original_path_reason": row.get("reason"),
        "recovery_pending": not terminal,
        "failed_terminal": terminal,
        **({"failure_category": "infrastructure"} if infrastructure else {}),
    }


def choose_logical_cell(
    pine: dict | None, python: dict | None, eligibility_proof: dict
) -> dict | None:
    """성과를 보지 않고 한 논리 셀의 실제 경로를 선택한다. 입력은 바꾸지 않는다."""
    if pine and pine.get("status") == "completed" and pine.get("_same_input_verified") is _VERIFIED:
        pine = {k: v for k, v in pine.items() if not k.startswith("_")}
        return {**pine, "selection_reason": "pine_completed"}
    if pine and pine.get("status") == "completed":
        return None
    eligible = (
        eligibility_proof.get("eligible") is True
        and eligibility_proof.get("_verified") is _VERIFIED
    )
    if eligible and python and python.get("_same_input_verified") is _VERIFIED:
        selected = {k: v for k, v in python.items() if not k.startswith("_")}
        return {
            **_logical_failure_status(selected),
            "selection_reason": "python_language_fallback",
            "eligibility_evidence": {
                k: v for k, v in eligibility_proof.items() if not k.startswith("_")
            },
        }
    if pine:
        return _logical_failure_status(
            {**pine, "selection_reason": eligibility_proof.get("reason", "pine_first")}
        )
    return None


class _Evidence:
    """보고서 한 번 안에서만 파일 SHA 조회를 재사용한다."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.cache: dict[tuple, Path] = {}
        self.implementation: dict | None = None
        self.compatibility: dict[str, bool] = {}

    def check(self, entry: dict) -> Path:
        relative, expected = entry["path"], entry["sha256"]
        if not isinstance(relative, str) or not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("invalid_evidence_reference")
        candidate = (self.root / relative).resolve()
        info = candidate.stat()
        key = (relative, expected, info.st_mtime_ns, info.st_size)
        if key not in self.cache:
            self.cache[key] = checked(self.root, relative, expected)
        return self.cache[key]

    def eligibility(self, cell: dict, review: dict) -> dict:
        pid, timeframe, period, policy = _key(cell)
        specific = (
            self.root / "pine-first/eligibility" / pid / timeframe / period / f"{policy}.json"
        )
        path = (
            specific if specific.exists() else self.root / "pine-first/eligibility" / f"{pid}.json"
        )
        if not path.exists():
            return classify_pine_failure(cell, review)
        try:
            proof = read(path)
            if (
                proof.get("policy") != POLICY
                or proof.get("publication_id") != pid
                or not proof.get("reviewer")
                or not proof.get("basis")
                or {name: cell[name] for name in IDENTITY} not in proof.get("cells", [])
            ):
                raise ValueError("eligibility_scope_mismatch")
            evidence = proof["evidence"]
            if not evidence.keys() >= EVIDENCE_ROLES:
                raise ValueError("eligibility_evidence_missing")
            files = {role: self.check(entry) for role, entry in evidence.items()}
            if (
                files["policy"] != self.root / "pine-first/policy.json"
                or read(files["policy"]).get("policy") != POLICY
            ):
                raise ValueError("eligibility_policy_mismatch")
            if (
                files["review"] != self.root / "reviews" / f"{pid}.json"
                or read(files["review"]) != review
            ):
                raise ValueError("eligibility_review_mismatch")
            if files["source"] != self.root / "sources" / f"{pid}.pine" or sha(
                files["source"].read_bytes()
            ) != review.get("source_sha256"):
                raise ValueError("eligibility_source_mismatch")
            if files["data"] != self.root / "data/dataset.json":
                raise ValueError("eligibility_dataset_mismatch")
            dataset = read(files["data"])
            data_files = dataset["files"][period]
            for kind in (timeframe, "1min", "funding"):
                self.check(
                    {
                        "path": "data/" + data_files[kind]["path"],
                        "sha256": data_files[kind]["sha256"],
                    }
                )
            # 선언한 언어 원인은 명시적인 실패/정적 지원 판정과 결박한다.
            failure = read(files["pine_failure"])
            if failure.get("status") == "completed":
                raise ValueError("pine_failure_is_completed")
            if cell.get("status") in {"failed", "not_run"}:
                actual = (
                    self.root / "cells" / pid / "pine" / timeframe / period / policy / "latest.json"
                )
                if (
                    files["checkpoint"] != actual
                    or _key(read(actual)) != _key(cell)
                    or read(actual).get("code_path") != "pine"
                    or read(actual).get("status") != cell.get("status")
                    or read(actual).get("reason") != cell.get("reason")
                ):
                    raise ValueError("pine_checkpoint_mismatch")
            elif not (
                failure.get("pine_coverage", {}).get("status") == "unsupported"
                and files["pine_failure"] == files["review"]
            ):
                raise ValueError("explicit_pine_failure_missing")
            if proof.get("failure_kind") in {"unsupported_syntax", "unsupported_api"}:
                coverage = failure.get("pine_coverage", {})
                if not (
                    coverage.get("status") == "unsupported"
                    and (
                        coverage.get("unsupported_functions")
                        or coverage.get("unsupported_attributes")
                    )
                ):
                    raise ValueError("known_unsupported_feature_missing")
            elif proof.get("failure_kind") == "pine_runtime_language":
                reason = str(failure.get("reason", ""))
                if not (
                    failure.get("status") in {"failed", "not_run"}
                    and failure.get("publication_id") == pid
                    and failure.get("code_path") == "pine"
                    and proof.get("matched_failure_reason") == reason
                    and reason
                    and proof.get("language_diagnosis_file") in evidence
                ):
                    raise ValueError("runtime_language_diagnosis_missing")
                diagnosis = read(files[proof["language_diagnosis_file"]])
                if diagnosis.get("source_sha256") != review["source_sha256"] or diagnosis.get(
                    "executable_sha256"
                ) != review.get("adapted_sha256", review.get("executable_sha256")):
                    raise ValueError("runtime_diagnosis_source_mismatch")
                request = read(files["pine_failure_request"])
                if (
                    identity(request) != failure.get("request_hash")
                    or request.get("source_sha256") != diagnosis["executable_sha256"]
                    or request.get("cell", {}).get("publication_id") != pid
                    or request.get("cell", {}).get("code_path") != "pine"
                ):
                    raise ValueError("runtime_failure_request_mismatch")
            elif proof.get("failure_kind") == "shared_signal_dependency":
                if (
                    policy != "B"
                    or review.get("signal_mode") != "shared_events"
                    or cell.get("status") != "not_run"
                    or cell.get("reason") != "shared_signal_tape_unavailable"
                ):
                    raise ValueError("not_a_shared_signal_dependency")
                parent = {**cell, "policy": "A"}
                parent_checkpoint = (
                    self.root / "cells" / pid / "pine" / timeframe / period / "A/latest.json"
                )
                if files["parent_checkpoint"] != parent_checkpoint:
                    raise ValueError("dependency_parent_checkpoint_mismatch")
                parent = read(parent_checkpoint)
                if parent.get("status") == "completed":
                    raise ValueError("successful_pine_A_cannot_trigger_python_B")
                approved = self.eligibility(parent, review)
                if (
                    not approved.get("eligible")
                    or files["parent_eligibility"] != self.root / approved["proof_file"]
                    or evidence["parent_eligibility"]["sha256"] != approved["proof_sha256"]
                ):
                    raise ValueError("dependency_A_language_failure_not_verified")
            request_hashes = proof.get("python_request_hashes", {})
            proof.update(
                python_request_hash=request_hashes.get(
                    "/".join(_key(cell)), proof.get("python_request_hash")
                ),
                _verified=_VERIFIED,
                proof_file=str(path.relative_to(self.root)),
                proof_sha256=sha(path.read_bytes()),
            )
            return classify_pine_failure(cell, {**review, "pine_first_eligibility": proof})
        except (OSError, ValueError, KeyError, TypeError) as error:
            return {"eligible": False, "reason": f"invalid_eligibility_evidence:{error}"}

    def completion_binding(
        self, row: dict, proof: dict, record: dict, request: dict, folder: Path
    ) -> dict:
        """해시가 미지정된 기존 적격 proof에 새 실제 실행 근거만 덧붙인다."""
        pid, tf, period, selected_policy = _key(row)
        request_hash = record["request_hash"]
        prefix = f"pine-first/completions/{pid}/{tf}/{period}/{selected_policy}/{request_hash}"
        if type(record.get("attempt")) is not int or record["attempt"] < 1:
            raise ValueError("completion_attempt_missing")
        relative = f"{prefix}-attempt-{record['attempt']:03}.json"
        if not (self.root / relative).exists() and record.get("status") == "completed":
            relative = f"{prefix}.json"
        descriptor = {"path": relative, "sha256": sha((self.root / relative).read_bytes())}
        binding = read(self.check(descriptor))
        if not isinstance(binding, dict):
            raise ValueError("completion_binding_must_be_object")
        cell = {**dict(zip(IDENTITY, _key(row), strict=True)), "code_path": "python"}
        eligibility = {"path": proof["proof_file"], "sha256": proof["proof_sha256"]}
        if (
            proof.get("_verified") is not _VERIFIED
            or proof.get("python_request_hash") is not None
            or type(binding.get("schema_version")) is not int
            or binding["schema_version"] != 1
            or binding.get("cell") != cell
            or binding.get("request_hash") != request_hash
            or binding.get("eligibility") != eligibility
            or record.get("status") not in ("completed", "failed")
        ):
            raise ValueError("completion_scope_or_eligibility_mismatch")
        roles = ("eligibility", "job", "worker_status", "checkpoint", "request")
        if record["status"] == "completed":
            roles += ("result",)
        elif "result" in binding or any(key in record for key in ("result_file", "result_sha256")):
            raise ValueError("failed_completion_cannot_claim_result")
        files = {
            role: self.check(binding[role])
            for role in roles
        }
        if read(files["eligibility"]).get("python_request_hash") is not None:
            raise ValueError("completion_cannot_replace_explicit_request_pin")
        checkpoint_paths = {folder / "latest.json"}
        if type(record.get("attempt")) is int and record["attempt"] > 0:
            checkpoint_paths.add(folder / f"attempt-{record['attempt']:03}.json")
        if (
            files["checkpoint"] not in checkpoint_paths
            or read(files["checkpoint"]) != record
            or files["request"] != folder / f"request-{request_hash}.json"
            or read(files["request"]) != request
        ):
            raise ValueError("completion_checkpoint_or_request_mismatch")
        if record["status"] == "completed" and (
            files["result"] != folder / f"result-{request_hash}.json.gz"
            or binding["result"] != {
                "path": record["result_file"], "sha256": record["result_sha256"]
            }
        ):
            raise ValueError("completion_result_mismatch")
        if identity(request) != request_hash:
            raise ValueError("completion_request_hash_mismatch")
        job = read(files["job"])
        if not isinstance(job, dict):
            raise ValueError("completion_job_must_be_object")
        job_hash = job.get("job_hash")
        if (
            not isinstance(job_hash, str)
            or len(job_hash) != 64
            or any(char not in "0123456789abcdef" for char in job_hash)
            or identity({key: value for key, value in job.items() if key != "job_hash"}) != job_hash
            or files["job"] != self.root / "pine-first/jobs" / f"{job_hash}.json"
            or any(job.get(key) != cell[key] for key in (*IDENTITY[:3], "code_path"))
            or job.get("policies") not in [["A"], ["B"], ["A", "B"]]
            or selected_policy not in job["policies"]
            or not isinstance(job.get("eligibility_proofs"), list)
            or eligibility not in job["eligibility_proofs"]
            or job.get("policy_sha256") != sha((self.root / "pine-first/policy.json").read_bytes())
            or not isinstance(job.get("input_evidence"), list)
            or not job["input_evidence"]
        ):
            raise ValueError("completion_job_identity_or_inputs_mismatch")
        for entry in [*job["input_evidence"], *job["eligibility_proofs"]]:
            self.check(entry)
        worker = read(files["worker_status"])
        if not isinstance(worker, dict):
            raise ValueError("completion_worker_must_be_object")
        if (
            files["worker_status"] != self.root / "pine-first/jobs" / job_hash / "worker-status.json"
            or worker.get("job_hash") != job_hash
            or worker.get("status") != "completed"
            or worker.get("phase") != "common_engine_dispatch"
            or type(worker.get("run_group_calls")) is not int
            or worker["run_group_calls"] < 1
            or not isinstance(worker.get("results"), list)
            or sum(value == record for value in worker["results"]) != 1
            or not isinstance(worker.get("selection_evidence"), list)
            or not any(
                isinstance(value, dict)
                and value.get("policy") == selected_policy
                and value.get("proof_file") == eligibility["path"]
                and value.get("proof_sha256") == eligibility["sha256"]
                for value in worker["selection_evidence"]
            )
        ):
            raise ValueError("completion_worker_dispatch_mismatch")
        if sha((self.root / relative).read_bytes()) != descriptor["sha256"]:
            raise ValueError("completion_changed_during_verification")
        return descriptor

    def verified_row(self, row: dict, proof: dict, review: dict) -> dict:
        """기존 성공은 양 언어 모두 현재 원문·입력·결과 SHA를 검증해 재사용한다."""
        language = row["code_path"]
        if language == "python" and not proof.get("eligible"):
            return row
        if row.get("status") != "completed" and language == "pine":
            return row
        try:
            pid, tf, period, policy = _key(row)
            if review.get("status") != "reviewed":
                raise ValueError("source_review_not_ready")
            self.check({"path": f"sources/{pid}.pine", "sha256": review["source_sha256"]})
            folder = self.root / "cells" / pid / language / tf / period / policy
            record = read(folder / "latest.json")
            request = read(folder / f"request-{record['request_hash']}.json")
            if identity(request) != record["request_hash"]:
                raise ValueError("request_hash_mismatch")
            completion = None
            if language == "python" and proof.get("python_request_hash") != record["request_hash"]:
                if proof.get("python_request_hash") is not None:
                    raise ValueError("reviewed_reuse_request_missing")
                completion = self.completion_binding(row, proof, record, request, folder)
            for key in (*IDENTITY, "code_path", "status", "result_sha256", "reason"):
                if row.get(key) != record.get(key):
                    raise ValueError("export_checkpoint_mismatch")
            dataset = read(self.root / "data/dataset.json")
            mapping = identity(
                {
                    "source_sha256": review["source_sha256"],
                    "inputs": review.get("inputs", {}),
                    "signal_bindings": review["signal_bindings"],
                    "signal_mode": review["signal_mode"],
                }
            )
            if (
                request.get("mapping_hash") != mapping
                or request.get("parameters") != review.get("inputs", {})
                or request.get("signal_mode") != review["signal_mode"]
                or request.get("warmup_bars") != review.get("warmup_bars", 1000)
                or request.get("dataset_sha256") != identity(dataset)
                or request.get("costs") != COSTS
                or request.get("cell")
                != {**dict(zip(IDENTITY, _key(row), strict=True)), "code_path": language}
                or request.get("policy")
                != {
                    "contract_version": 1,
                    "exit_policy": "signal_only_v1" if policy == "A" else "swing_two_bar_v1",
                    "reentry_policy": "close_then_reenter_v1",
                    "signal_mode": review["signal_mode"],
                    "signal_mapping_hash": mapping,
                }
            ):
                raise ValueError("current_input_mismatch")
            from tools.research.period_study.controller import artifact, implementation

            if self.implementation is None:
                self.implementation = implementation()
            saved = request.get("implementation", {})
            implementation_key = identity(saved)
            if implementation_key not in self.compatibility:
                self.compatibility[implementation_key] = compatible_implementation(
                    self.root, saved, self.implementation
                )
            if not self.compatibility[implementation_key]:
                raise ValueError("current_implementation_mismatch")
            runtime = read(self.root / "runtime-smoke.json")
            if request.get("image_ids") != runtime.get("image_ids"):
                raise ValueError("current_runner_image_mismatch")
            _, source_hash, current_review = artifact(self.root, self.root, {"id": pid}, language)
            if (
                request.get("source_sha256") != source_hash
                or request.get("generated_code_review_sha256")
                != current_review.get("generated_code_review_sha256")
                or request.get("market_context_proof") != current_review.get("market_context_proof")
            ):
                raise ValueError("current_executable_or_approval_mismatch")
            expected_files = dict(dataset["files"][period])
            if review.get("warmup_bars", 1000) > dataset["warmup_bars"]:
                expected_files[tf] = read(
                    self.root / "data/extensions" / period / f"{tf}-{review['warmup_bars']}.json"
                )
            if request.get("data_files") != expected_files:
                raise ValueError("current_period_data_files_mismatch")
            for kind in (tf, "1min", "funding"):
                entry = request["data_files"][kind]
                self.check({"path": "data/" + entry["path"], "sha256": entry["sha256"]})
            if row.get("status") == "completed":
                result = read(
                    self.check({"path": record["result_file"], "sha256": record["result_sha256"]})
                )
                if result.get("request") != request:
                    raise ValueError("result_request_mismatch")
                if (
                    language == "python"
                    and policy == "B"
                    and review["signal_mode"] == "shared_events"
                ):
                    parent_folder = self.root / "cells" / pid / "python" / tf / period / "A"
                    parent_row = read(parent_folder / "latest.json")
                    pine_parent = self.root / "cells" / pid / "pine" / tf / period / "A/latest.json"
                    original = (
                        read(pine_parent)
                        if pine_parent.exists()
                        else {
                            **dict(zip(IDENTITY, _key(row), strict=True)),
                            "policy": "A",
                            "code_path": "pine",
                            "status": "pending",
                        }
                    )
                    parent_proof = self.eligibility(original, review)
                    verified = self.verified_row(parent_row, parent_proof, review)
                    if (
                        parent_row.get("status") != "completed"
                        or verified.get("_same_input_verified") is not _VERIFIED
                    ):
                        raise ValueError("shared_python_B_requires_verified_python_A")
                    parent_result = read(
                        self.check(
                            {
                                "path": parent_row["result_file"],
                                "sha256": parent_row["result_sha256"],
                            }
                        )
                    )
                    if (
                        not parent_result.get("signals")
                        or result.get("signals") != parent_result["signals"]
                    ):
                        raise ValueError("shared_python_B_signal_tape_mismatch")
            for metric, value in record.get("metrics", {}).items():
                if metric in row and row[metric] != value:
                    raise ValueError("exported_metric_mismatch")
            return {
                **row,
                **({"completion_binding": completion} if completion is not None else {}),
                "execution_attempt": record.get("execution_attempt"),
                "bounded_retries_exhausted": record.get("bounded_retries_exhausted") is True,
                "_same_input_verified": _VERIFIED,
            }
        except (OSError, ValueError, KeyError, TypeError):
            return row


def build_pine_first_view(run: Path, exported_rows: list[dict]) -> dict:
    """실제 선택 행과 42k 논리 분모를 반환한다. 원본 원장은 수정하지 않는다."""
    run = Path(run)
    policy_path = run / "pine-first/policy.json"
    policy = read(policy_path) if policy_path.exists() else {"policy": POLICY}
    manifest = read(run / "manifest.json") if (run / "manifest.json").exists() else {}
    count = policy.get("source_count", manifest.get("source_count", 0))
    if not count and (run / "catalogue.json").exists():
        count = len(read(run / "catalogue.json").get("items", []))
    grouped: dict[tuple, dict] = {}
    for row in exported_rows:
        paths = grouped.setdefault(_key(row), {})
        if row["code_path"] in paths:
            raise ValueError("duplicate_financial_cell")
        paths[row["code_path"]] = row
    evidence = _Evidence(run)
    selected, eligibility_counts = [], Counter()
    for key, paths in sorted(grouped.items()):
        pine, python = paths.get("pine"), paths.get("python")
        reference = pine or {**python, "status": "pending", "code_path": "pine"}
        review_path = run / "reviews" / f"{key[0]}.json"
        review = read(review_path) if review_path.exists() else {}
        proof = evidence.eligibility(reference, review)
        eligibility_counts[proof["reason"]] += 1
        if pine:
            pine = evidence.verified_row(pine, proof, review)
        if python:
            python = evidence.verified_row(python, proof, review)
        chosen = choose_logical_cell(pine, python, proof)
        if chosen is not None:
            selected.append(chosen)
    counts = Counter(row.get("status", "pending") for row in selected)
    if set(counts) - set(STATUSES):
        raise ValueError("unknown_financial_status")
    target = count * 30
    if len(selected) > target:
        raise ValueError("logical_financial_target_exceeded")
    counts["pending"] += target - len(selected)
    raw_counts = Counter(row.get("status", "pending") for row in exported_rows)
    pine_completed = sum(r["status"] == "completed" and r["code_path"] == "pine" for r in selected)
    python_completed = sum(
        r["status"] == "completed" and r["code_path"] == "python" for r in selected
    )
    excluded = (
        sum(r["status"] == "completed" and r["code_path"] == "python" for r in exported_rows)
        - python_completed
    )
    return {
        "rows": selected,
        "policy": {**policy, "eligibility_reasons": dict(eligibility_counts)},
        "progress": {
            "financial_target": target,
            "financial_recorded": len(selected),
            "financial_statuses": {s: counts[s] for s in STATUSES},
            "financial_pending": counts["pending"],
            "financial_recovery_pending": sum(
                row.get("recovery_pending") is True for row in selected
            ),
            "financial_failed_terminal": counts["failed"],
            "failed_terminal_definition": (
                "적격·동일 입력이 검증된 Python 금융 실행의 execution_attempt=2 또는 "
                "bounded_retries_exhausted=true인 실패만 최종 금융 실패다. "
                "PythonRunnerUnavailable 인프라 실패는 재시도 소진 후에도 복구 대기다. "
                "Pine 경로 실패·생성 실패·자료 부재·변환 부적격은 최종 금융 실패가 아니다."
            ),
            "pine_completed": pine_completed,
            "python_fallback_completed": python_completed,
            "legacy_financial_target": manifest.get("expected_cells", count * 60),
            "legacy_financial_recorded": len(exported_rows),
            "legacy_financial_statuses": dict(raw_counts),
            "legacy_python_completed_excluded": excluded,
        },
    }


def native_code_paths(
    run: Path, pid: str, timeframe: str, evidence_out: list | None = None
) -> tuple[str, ...]:
    """정책 이전 native 재현은 보존하고 현재는 실제 선택 경로만 검증한다."""
    run = Path(run)
    policy_file = run / "pine-first/policy.json"
    if not policy_file.exists():
        return ("pine", "python")
    if read(policy_file).get("policy") != POLICY:
        raise ValueError("unknown_execution_policy")
    exported = read(run / "report-input.json") if (run / "report-input.json").exists() else {}
    rows = [
        r
        for r in exported.get("cells", [])
        if r.get("publication_id") == pid and r.get("timeframe") == timeframe
    ]
    view = build_pine_first_view(run, rows)
    if evidence_out is not None:
        for row in view["rows"]:
            proof = row.get("eligibility_evidence", {})
            if row["code_path"] == "python" and proof.get("proof_file"):
                descriptor = {"path": proof["proof_file"], "sha256": proof["proof_sha256"]}
                if descriptor not in evidence_out:
                    evidence_out.append(descriptor)
    selected = {r["code_path"] for r in view["rows"]}
    # 아직 대체 실행이 선택되지 않은 범위는 원문 경로를 우선한다.
    return (
        tuple(p for p in ("pine", "python") if p in selected) if "python" in selected else ("pine",)
    )
