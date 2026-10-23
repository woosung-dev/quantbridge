"""무료 Gemini의 제한된 Python 생성·독립 평가. 완료된 Sol 실험은 실행하지 않는다."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import random
import stat
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

MODELS = (
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)
ATTEMPT_CEILING = 91
MAX_OUTPUT_TOKENS = 16_384
TIMEOUT_SECONDS = 180
SEED = 20261023


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("JSON 객체가 필요합니다")
    return value


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json(path: Path, value: Any, *, immutable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = json.dumps(value, ensure_ascii=False, indent=2)
    if immutable and path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError("동결 입력 또는 기존 증거가 다릅니다")
        return
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if immutable else os.O_TRUNC)
    with os.fdopen(os.open(path, flags, 0o600), "w") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    fsync_directory(path.parent)


def now() -> str:
    return datetime.now(UTC).isoformat()


def validate_free(evidence: dict[str, Any]) -> None:
    if (
        evidence.get("billing_tier_observed") not in ("무료 등급", "Free", "FREE")
        or not evidence.get("project_id")
        or not evidence.get("observed_at_utc")
        or evidence.get("authorized_generation_attempt_ceiling") != ATTEMPT_CEILING
    ):
        raise ValueError("승인된 프로젝트 Free 증거가 필요합니다")


def load_credentials(path: Path):
    """명시된 비밀 파일만 읽으며 기존 환경 변수로 대체하지 않는다."""
    if path.is_symlink():
        raise ValueError("비밀 파일 심볼릭 링크는 허용하지 않습니다")
    path = path.resolve()
    if (
        path.is_symlink()
        or not path.is_relative_to(ROOT)
        or stat.S_IMODE(path.stat().st_mode) != 0o600
        or stat.S_IMODE(path.parent.stat().st_mode) != 0o700
    ):
        raise ValueError("비밀 파일0600·디렉터리0700·워크트리 내부 경로가 필요합니다")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(path)], cwd=ROOT, check=False
    )
    if ignored.returncode != 0:
        raise ValueError("비밀 파일은 gitignore 대상이어야 합니다")
    from dotenv import dotenv_values
    from pydantic import SecretStr

    values = dotenv_values(path, interpolate=False)
    key = values.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("승인된 비밀 파일에 GEMINI_API_KEY가 없습니다")
    return SecretStr(key), hashlib.sha256(path.read_bytes()).hexdigest()


class Ledger:
    """API 호출 전에 예약을 fsync한다. 완료 증거가 없어도 예약은 소비로 남는다."""

    def __init__(self, root: Path):
        self.path = root / "attempts.jsonl"
        self.lock = threading.Lock()
        self.rows = []
        if self.path.exists():
            self.rows = [
                json.loads(line) for line in self.path.read_text().splitlines()
            ]

    def append(self, row: dict[str, Any]) -> None:
        with self.lock:
            with os.fdopen(
                os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "a"
            ) as stream:
                stream.write(
                    json.dumps({"at": now(), **row}, ensure_ascii=False) + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())
            fsync_directory(self.path.parent)
            self.rows.append(row)

    def reserved(self) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["kind"] == "generation_reserved"]


def metadata(root: Path, key, evidence: dict[str, Any]) -> dict[str, Any]:
    """모델 목록 조회는 생성과 분리해 장부에 기록한다."""
    from google import genai
    from google.genai import types

    validate_free(evidence)
    ledger = Ledger(root)
    ledger.append({"kind": "metadata_reserved", "operation": "models.list"})
    try:
        with genai.Client(
            api_key=key.get_secret_value(),
            enterprise=False,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        ) as client:
            models = [
                {
                    "name": item.name,
                    "display_name": item.display_name,
                    "supported_actions": item.supported_actions,
                    "input_token_limit": item.input_token_limit,
                    "output_token_limit": item.output_token_limit,
                }
                for item in client.models.list()
            ]
        result = {
            "project_id": evidence["project_id"],
            "observed_at_utc": now(),
            "models": models,
        }
        write_json(root / "models.json", result, immutable=True)
        ledger.append(
            {
                "kind": "metadata_completed",
                "operation": "models.list",
                "model_count": len(models),
            }
        )
        return result
    except Exception as exc:
        ledger.append({"kind": "metadata_failed", **safe_error(exc)})
        raise RuntimeError(
            "모델 metadata 조회 실패: 안전한 장부를 확인하세요"
        ) from None


def safe_error(exc: Exception) -> dict[str, Any]:
    """SDK 원 예외 본문·URL·키를 로그나 보고서에 복사하지 않는다."""
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    status = status if isinstance(status, int) else None
    category = getattr(exc, "category", None)
    if category is None:
        category = {
            403: "forbidden",
            404: "not_found",
            429: "quota_exhausted",
            400: "validation",
            408: "timeout",
            504: "timeout",
        }.get(status)
    if category is None:
        category = (
            "validation"
            if isinstance(exc, ValueError)
            else "timeout"
            if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower()
            else "provider_error"
        )
    return {
        "error_category": category,
        "status_code": status,
        "error_type": type(exc).__name__,
    }


def contracts():
    from src.strategy.code_generate_prompt import (
        CODE_GENERATION_SCHEMA,
        build_generation_prompt,
    )
    from tools.research.sol_strategy_lab import DEV_CASES

    return CODE_GENERATION_SCHEMA, build_generation_prompt, DEV_CASES


def build_manifest(evidence: dict, quota: dict, listed: dict) -> dict:
    validate_free(evidence)
    quota_project = quota.get("project_id") or quota.get("project", {}).get(
        "project_id"
    )
    if (
        quota_project != evidence["project_id"]
        or listed.get("project_id") != evidence["project_id"]
    ):
        raise ValueError("Free·quota·모델 목록의 프로젝트가 다릅니다")
    external = quota.get("external_generation_attempts", 0)
    if type(external) is not int or not 0 <= external <= ATTEMPT_CEILING:
        raise ValueError("실험 외 생성 시도 수도 전체91회 상한 안에 있어야 합니다")
    schema, prompt_builder, cases = contracts()
    model_order = list(MODELS)
    random.Random(SEED).shuffle(model_order)
    rounds = []
    for round_index in range(13):
        offset = round_index % len(model_order)
        rounds.append(model_order[offset:] + model_order[:offset])
    requests = {}
    for index in range(13):
        if index == 0:
            case_id, repetition, prompt = (
                "availability",
                None,
                "항상 {'action':'hold'}를 반환하는 최소 Python on_bar 함수를 작성하세요.",
            )
        else:
            case_id, prompt = cases[(index - 1) // 2]
            repetition = (index - 1) % 2
        system, user = prompt_builder(prompt)
        requests[str(index)] = {
            "case_id": case_id,
            "repetition": repetition,
            "system": system,
            "user": user,
        }
    return {
        "cohort": "gemini_python_6x2_v1",
        "seed": SEED,
        "models": list(MODELS),
        "rounds": rounds,
        "requests": requests,
        "schema": schema,
        "generation_attempt_ceiling": ATTEMPT_CEILING,
        "external_generation_attempts": external,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "sdk_total_attempts": 1,
        "automatic_retries": 0,
        "concurrency": {"global": 2, "per_model": 1},
        "free_evidence_hash": digest(evidence),
        "quota_evidence": quota,
        "operational_model_budgets": operational_budgets(quota),
        "metadata_hash": digest(listed),
        "listed_models": listed["models"],
        "evaluation": "sol_public_check_and_independent_semantic_numeric_v2_quality90",
        "source_hashes": source_hashes(),
    }


def source_hashes() -> dict[str, str]:
    paths = [
        Path(__file__),
        ROOT / "tools/research/strategy_oracle.py",
        ROOT / "tools/research/sol_semantic_eval.py",
        ROOT / "tools/research/strategy_catalogue30.py",
        ROOT / "tools/research/sol_strategy_lab.py",
        ROOT / "apps/api/src/strategy/code_generate_prompt.py",
        ROOT / "apps/api/src/strategy/code_generate_service.py",
        ROOT / "apps/api/src/strategy/code_schemas.py",
        ROOT / "apps/api/src/strategy/narrative/providers.py",
    ]
    for directory in (
        "apps/api/src/strategy/code_runtime",
        "apps/api/src/strategy/python_runtime",
        "apps/api/src/backtest/engine",
    ):
        paths.extend((ROOT / directory).rglob("*.py"))
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))
    }


def bind_prior_probes(
    manifest: dict, prior_root: Path, current_root: Path, *, key_hash: str
) -> None:
    """요청 형식 오류로 끝난 최초7회를 보존하고 새 품질 생성84회와 예산을 결합한다."""
    prior_root = prior_root.resolve()
    if prior_root == current_root.resolve() or not prior_root.is_relative_to(
        ROOT / "runs"
    ):
        raise ValueError("이전 probe와 후속 cohort는 서로 다른 runs/ 경로여야 합니다")
    previous = read_json(prior_root / "manifest.json")
    credentials_path = prior_root / ".credential-binding.json"
    previous_credentials = read_json(credentials_path)
    if previous_credentials.get("key_file_sha256") != key_hash:
        raise ValueError(
            "후속 cohort는 이전 epoch와 같은 승인 키 파일을 사용해야 합니다"
        )
    ledger = Ledger(prior_root)
    reserved = ledger.reserved()
    completed = [row for row in ledger.rows if row["kind"] == "generation_completed"]
    expected_slots = {f"{model}/0" for model in MODELS}
    if (
        previous.get("external_generation_attempts") != 0
        or set(previous.get("models", [])) != set(MODELS)
        or len(reserved) != 7
        or len(completed) != 7
        or {row["slot"] for row in reserved} != expected_slots
        or {row["slot"] for row in completed} != expected_slots
        or not previous.get("source_hashes")
    ):
        raise ValueError(
            "이전 epoch는 지정7모델의 최초 probe7회만 소비한 상태여야 합니다"
        )
    paths = [
        prior_root / "manifest.json",
        prior_root / "attempts.jsonl",
        credentials_path,
    ]
    for model in MODELS:
        folder = prior_root / "trials" / model / "0"
        generation = read_json(folder / "generation.json")
        reservation = next(row for row in reserved if row["model"] == model)
        completion = next(row for row in completed if row["model"] == model)
        if (
            reservation["slot"] != f"{model}/0"
            or generation.get("status") != "failed"
            or generation.get("status_code") != 400
            or completion.get("status") != "failed"
            or completion.get("status_code") != 400
            or digest(read_json(folder / "request.json"))
            != reservation.get("request_hash")
        ):
            raise ValueError("이전 probe의 요청·400 실패·소비 증거가 일치하지 않습니다")
        paths.extend((folder / "generation.json", folder / "request.json"))
    manifest["cohort"] = "gemini_python_6x2_json_schema_v2"
    manifest["external_generation_attempts"] += 7
    if manifest["external_generation_attempts"] > ATTEMPT_CEILING:
        raise ValueError("이전 소비를 합치면 전체91회 상한을 넘습니다")
    manifest["prior_probes"] = {
        "root": str(prior_root),
        "consumed_generation_attempts": 7,
        "files": {
            str(path.relative_to(prior_root)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in paths
        },
        "source_hashes": previous["source_hashes"],
        "interpretation": "최초 요청 형식400 실패는 보존하며 모델 접근 불가·품질0으로 단정하지 않는다",
    }
    manifest["availability_quality_index"] = 1
    manifest["additional_hold_probe_attempts"] = 0


def verify_prior_probes(manifest: dict) -> None:
    prior = manifest.get("prior_probes")
    if prior:
        for name, checksum in prior["files"].items():
            if (
                hashlib.sha256((Path(prior["root"]) / name).read_bytes()).hexdigest()
                != checksum
            ):
                raise ValueError(
                    "보존한 이전 epoch의 manifest·장부·probe 증거가 바뀌었습니다"
                )


def evaluation_environment() -> dict:
    """현재 endpoint를 조회만 하며 VM·컨테이너·이미지를 기동하거나 바꾸지 않는다."""
    from src.strategy.python_runtime.sandbox import DEFAULT_IMAGE
    from src.strategy.python_runtime.serialization import bars_payload
    from tools.research.sol_semantic_eval import hidden_frame
    from tools.research.sol_strategy_lab import smoke_frame

    runtime = subprocess.run(
        ["docker", "info", "--format", "{{json .Runtimes}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if "runsc" not in json.loads(runtime.stdout):
        raise RuntimeError("gVisor runsc가 없는 endpoint입니다")
    inspected = subprocess.run(
        ["docker", "image", "inspect", DEFAULT_IMAGE, "--format", "{{.Id}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return {
        "docker_endpoint": os.environ.get("DOCKER_HOST", "default"),
        "python_image_id": inspected.stdout.strip(),
        "boundary": "runsc_network_none_readonly_nonroot_1cpu_1g_900seconds",
        "public_data_sha256": digest(bars_payload(smoke_frame())),
        "semantic_data_sha256": digest(bars_payload(hidden_frame())),
        "reference_scope": "independent_signals_shared_broker",
    }


def operational_budgets(evidence: dict) -> dict:
    """지연 관측과 이번 실행의 예약 상한을 구분한다. null을0으로 바꾸지 않는다."""
    result = {}
    for model, row in evidence.get("models", {}).items():
        rpd = row.get("rpd_limit")
        budget = min(13, rpd) if type(rpd) is int and rpd > 0 else 0
        observed_headroom = row.get("rpd_headroom_from_display")
        if type(observed_headroom) is int:
            budget = min(budget, max(0, observed_headroom))
        exact = row.get("rpd_remaining_guaranteed")
        if type(exact) is int:
            budget = min(budget, max(0, exact))
        result[model] = {
            "rpm": row.get("rpm_limit"),
            "tpm": row.get("tpm_limit"),
            "operational_attempt_budget": budget,
            "rpd_remaining_guaranteed": exact,
            "rpd_used_today_exact": row.get("rpd_used_today_exact"),
            "tpd_limit": row.get("tpd_limit"),
            "remaining_tpd": row.get("remaining_tpd"),
            "tpd_status": "UNKNOWN_NOT_DISPLAYED"
            if row.get("tpd_limit") is None
            else "OBSERVED",
            "headroom_is_guaranteed": False,
        }
    return result


def quota_reason(model: str, quota: dict) -> str | None:
    for field in ("rpm", "tpm", "operational_attempt_budget"):
        value = quota.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            return f"missing_or_exhausted_{field}"
    if math.floor(quota["rpm"] * 0.8) < 1:
        return "rpm_safety_margin_below_one"
    del model
    return None


def complete(key, model: str, request: dict, schema: dict):
    from src.strategy.narrative.providers import complete_json

    settings = SimpleNamespace(
        llm_provider_order="gemini", gemini_api_key=key, gemini_model=model
    )
    return complete_json(
        settings,
        system=request["system"],
        user=request["user"],
        schema=schema,
        tool_name="generate_python_strategy",
        max_output_tokens=MAX_OUTPUT_TOKENS,
        timeout_seconds=TIMEOUT_SECONDS,
    )


def validate_payload(value: dict) -> dict:
    from src.strategy.code_generate_service import validate_generated_python

    return validate_generated_python(value).model_dump()


class Runner:
    def __init__(
        self,
        root: Path,
        manifest: dict,
        key,
        *,
        caller=complete,
        clock=time.time,
        sleep=time.sleep,
        payload_validator=validate_payload,
    ):
        self.root, self.manifest, self.key = root, manifest, key
        self.caller, self.clock, self.sleep = caller, clock, sleep
        self.payload_validator = payload_validator
        verify_prior_probes(manifest)
        self.ledger = Ledger(root)
        self.budget_lock = threading.Lock()
        self.stopped = {
            row["model"]: "quota_429_no_retry"
            for row in self.ledger.rows
            if row["kind"] == "generation_completed"
            and (
                row.get("status_code") == 429
                or row.get("error_category") in ("rate_limited", "quota_exhausted")
            )
        }

    def _not_run(self, model: str, index: int, reason: str) -> None:
        path = self.root / "trials" / model / str(index) / "not-run.json"
        write_json(
            path,
            {"model": model, "round": index, "status": "NOT_RUN", "reason": reason},
            immutable=True,
        )

    def attempt(self, model: str, index: int) -> None:
        request = self.manifest["requests"][str(index)]
        slot = f"{model}/{index}"
        folder = self.root / "trials" / model / str(index)
        if (folder / "not-run.json").exists():
            return
        if any(row["slot"] == slot for row in self.ledger.reserved()):
            return
        if self.manifest.get("prior_probes") and index == 0:
            self._not_run(model, index, "prior_epoch_probe_no_additional_hold_probe")
            return
        reason = self.stopped.get(model)
        reset = (
            self.manifest["quota_evidence"].get("quota_day", {}).get("next_reset_utc")
        )
        if (
            reset
            and self.clock()
            >= datetime.fromisoformat(reset.replace("Z", "+00:00")).timestamp()
        ):
            reason = "quota_day_changed_no_automatic_next_day_run"
        quota = self.manifest["operational_model_budgets"].get(model, {})
        reason = reason or quota_reason(model, quota)
        found = next(
            (
                row
                for row in self.manifest["listed_models"]
                if row["name"].removeprefix("models/") == model
            ),
            None,
        )
        if not found or "generateContent" not in (found.get("supported_actions") or []):
            reason = "not_listed_for_text_generation"
        availability_index = self.manifest.get("availability_quality_index", 0)
        if index > availability_index:
            available_path = (
                self.root
                / "trials"
                / model
                / str(availability_index)
                / "generation.json"
            )
            if (
                not available_path.exists()
                or read_json(available_path)["status"] != "completed"
            ):
                reason = reason or "availability_not_passed"
        if reason:
            self._not_run(model, index, reason)
            return
        # UTF-8 byte 수와 schema 및 여유를 사용한 보수적 입력 예약이며 실제 usage와 별도다.
        reserved_tokens = (
            len(json.dumps(request, ensure_ascii=False).encode())
            + len(json.dumps(self.manifest["schema"]).encode())
            + MAX_OUTPUT_TOKENS
            + 4096
        )
        if reserved_tokens > quota["tpm"]:
            self._not_run(model, index, "request_reservation_exceeds_tpm")
            return
        previous = [row for row in self.ledger.reserved() if row["model"] == model]
        while True:
            delay = (
                max(
                    0.0,
                    previous[-1]["epoch"]
                    + 60 / math.floor(quota["rpm"] * 0.8)
                    - self.clock(),
                )
                if previous
                else 0.0
            )
            recent = [row for row in previous if row["epoch"] > self.clock() - 60]
            if (
                sum(row["reserved_tokens"] for row in recent) + reserved_tokens
                > quota["tpm"]
            ):
                delay = max(delay, recent[0]["epoch"] + 60.01 - self.clock())
            if delay <= 0:
                break
            self.sleep(delay)
        with self.budget_lock:
            verify_prior_probes(self.manifest)
            prior = self.ledger.reserved()
            same = [row for row in prior if row["model"] == model]
            if (
                len(prior) + self.manifest["external_generation_attempts"]
                >= ATTEMPT_CEILING
            ):
                self._not_run(model, index, "global_attempt_ceiling")
                return
            if len(same) >= quota["operational_attempt_budget"]:
                self.stopped[model] = "operational_request_budget_exhausted"
            if (
                type(quota.get("remaining_tpd")) is int
                and sum(row["reserved_tokens"] for row in same) + reserved_tokens
                > quota["remaining_tpd"]
            ):
                self.stopped[model] = "daily_token_quota_exhausted"
            if model in self.stopped:
                self._not_run(model, index, self.stopped[model])
                return
            write_json(folder / "request.json", request, immutable=True)
            self.ledger.append(
                {
                    "kind": "generation_reserved",
                    "slot": slot,
                    "model": model,
                    "epoch": self.clock(),
                    "reserved_tokens": reserved_tokens,
                    "request_hash": digest(request),
                }
            )
        started = self.clock()
        result: dict[str, Any] = {
            "model": model,
            "case_id": request["case_id"],
            "repetition": request["repetition"],
            "provider": "gemini",
            "status": "failed",
            "actual_model": None,
            "usage": None,
            "usage_known": False,
        }
        try:
            response = self.caller(self.key, model, request, self.manifest["schema"])
            result.update(
                actual_model=getattr(response, "actual_model", None),
                provider=response.provider,
                finish_reason=getattr(response, "finish_reason", None),
                usage_known=getattr(response, "usage_known", False),
                usage={
                    name: getattr(response, name, None)
                    for name in (
                        "input_tokens",
                        "output_tokens",
                        "thinking_tokens",
                        "total_tokens",
                    )
                },
            )
            for field in ("input_tokens", "output_tokens"):
                result["usage"][field] = getattr(
                    response,
                    f"reported_{field}",
                    getattr(response, field, None) if result["usage_known"] else None,
                )
            if response.provider != "gemini":
                raise ValueError("승인된 provider가 아닙니다")
            write_json(folder / "payload.json", response.payload, immutable=True)
            result["payload_hash"] = digest(response.payload)
            self.payload_validator(response.payload)
            result["status"] = "completed"
        except Exception as exc:
            result.update(safe_error(exc))
            observed = getattr(exc, "metadata", {})
            if isinstance(observed, dict) and observed:
                result.update(
                    actual_model=observed.get("actual_model"),
                    finish_reason=observed.get("finish_reason"),
                    usage_known=observed.get("usage_known", False),
                    diagnostic=observed.get("diagnostic"),
                    error_reason=observed.get("error_reason"),
                    usage={
                        name: observed.get(name)
                        for name in (
                            "input_tokens",
                            "output_tokens",
                            "thinking_tokens",
                            "total_tokens",
                        )
                    },
                )
                for field in ("input_tokens", "output_tokens"):
                    result["usage"][field] = observed.get(
                        f"reported_{field}",
                        observed.get(field) if result["usage_known"] else None,
                    )
            if (
                result["error_category"] in ("quota_exhausted", "rate_limited")
                or result["status_code"] == 429
            ):
                self.stopped[model] = "quota_429_no_retry"
            if index == availability_index:
                self.stopped[model] = "availability_failed"
        result["duration_seconds"] = self.clock() - started
        write_json(folder / "generation.json", result, immutable=True)
        self.ledger.append(
            {
                "kind": "generation_completed",
                "slot": slot,
                "model": model,
                "status": result["status"],
                "duration_seconds": result["duration_seconds"],
                "error_category": result.get("error_category"),
                "status_code": result.get("status_code"),
            }
        )

    def run(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for index, models in enumerate(self.manifest["rounds"]):
                list(pool.map(lambda model: self.attempt(model, index), models))


def evaluate(root: Path) -> None:
    from tools.research.sol_semantic_eval import evaluate as semantic_check
    from tools.research.sol_strategy_lab import public_check

    manifest = read_json(root / "manifest.json")
    verify_prior_probes(manifest)
    if manifest["source_hashes"] != source_hashes():
        raise ValueError("동결한 생성·평가·실행 소스가 바뀌었습니다")
    if manifest["evaluation_environment"] != evaluation_environment():
        raise ValueError("동결한 이미지·endpoint·평가 데이터가 바뀌었습니다")

    def one(job):
        model, index = job
        folder = root / "trials" / model / str(index)
        result_path = folder / "generation.json"
        if not result_path.exists() or read_json(result_path)["status"] != "completed":
            return
        generation, payload = read_json(result_path), read_json(folder / "payload.json")
        if digest(payload) != generation["payload_hash"]:
            raise ValueError("생성 원문 hash가 다릅니다")
        source = payload["source_code"]
        identity = {
            "manifest_hash": digest(manifest),
            "source_hash": hashlib.sha256(source.encode()).hexdigest(),
        }
        output = folder / "evaluation.json"
        if output.exists():
            if read_json(output)["identity"] != identity:
                raise ValueError("평가 캐시의 실행 소스·입력이 다릅니다")
            return
        public = public_check(source, "python")
        semantic = (
            semantic_check(source, "python", generation["case_id"])
            if public["passed"]
            else {}
        )
        # 원 예외 본문은 연구 산출물에서도 복사하지 않는다.
        for section in (public, semantic):
            section.pop("error", None)
        write_json(
            output,
            {"identity": identity, "public": public, "semantic": semantic},
            immutable=True,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(
            pool.map(
                one,
                (
                    (model, index)
                    for model in manifest["models"]
                    for index in range(1, 13)
                ),
            )
        )


def quantile(values: list[float], probability: float):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def report(root: Path) -> dict:
    manifest, ledger = read_json(root / "manifest.json"), Ledger(root)
    verify_prior_probes(manifest)
    if "source_hashes" in manifest and manifest["source_hashes"] != source_hashes():
        raise ValueError("동결한 생성·평가·실행 소스가 바뀌었습니다")
    rows = []
    for model in manifest["models"]:
        scores, times, statuses, errors, usage, actual_models, execution_errors = (
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        )
        generated = public_passes = semantic_passes = evaluated = 0
        not_run_reasons, finish_reasons = [], []
        for index in range(1, 13):
            folder = root / "trials" / model / str(index)
            generation_path = folder / "generation.json"
            generation = read_json(generation_path) if generation_path.exists() else {}
            not_run_path = folder / "not-run.json"
            if not_run_path.exists():
                not_run_reasons.append(read_json(not_run_path)["reason"])
            finish_reasons.append(generation.get("finish_reason"))
            statuses.append(generation.get("status", "NOT_RUN"))
            if "duration_seconds" in generation:
                times.append(generation["duration_seconds"])
            if generation.get("status") == "completed":
                generated += 1
            errors.append(generation.get("error_category"))
            actual_models.append(generation.get("actual_model"))
            usage.append(generation.get("usage"))
            evaluation_path = folder / "evaluation.json"
            quality = None
            if evaluation_path.exists():
                evaluation = read_json(evaluation_path)
                payload = read_json(folder / "payload.json")
                expected_identity = {
                    "manifest_hash": digest(manifest),
                    "source_hash": hashlib.sha256(
                        payload["source_code"].encode()
                    ).hexdigest(),
                }
                if (
                    digest(payload) != generation.get("payload_hash")
                    or evaluation["identity"] != expected_identity
                ):
                    raise ValueError("보고서의 생성·실행 소스 증거가 다릅니다")
                semantic, public = evaluation["semantic"], evaluation["public"]
                evaluated += 1
                public_passes += bool(public.get("passed"))
                semantic_passes += semantic.get("status") == "passed"
                execution_errors.extend(
                    section["error_type"]
                    for section in (public, semantic)
                    if section.get("error_type")
                )
                quality = sum(
                    semantic.get(name, 0)
                    for name in (
                        "contract_points",
                        "ledger_points",
                        "reproducibility_points",
                    )
                ) + (10 if public.get("passed") else 0)
            elif generation.get("status") == "failed":
                quality = 0
            scores.append(quality)
        observed_scores = [value for value in scores if value is not None]
        availability_index = manifest.get("availability_quality_index", 0)
        availability_path = (
            root / "trials" / model / str(availability_index) / "generation.json"
        )
        availability = (
            read_json(availability_path)
            if availability_path.exists()
            else {"status": "NOT_RUN"}
        )
        interrupted = sum(
            row["model"] == model
            and not (root / "trials" / row["slot"] / "generation.json").exists()
            for row in ledger.reserved()
        )
        rows.append(
            {
                "model": model,
                "availability": availability,
                "availability_quality_index": availability_index,
                "prior_failed_probe_attempts": 1 if manifest.get("prior_probes") else 0,
                "expected_artifacts": 12,
                "generated": generated,
                "generation_success_rate": generated / 12,
                "public_success_rate": public_passes / 12,
                "semantic_success_rate": semantic_passes / 12,
                "public_passes": public_passes,
                "semantic_passes": semantic_passes,
                "evaluated": evaluated,
                "not_run_or_interrupted": sum(
                    status == "NOT_RUN" for status in statuses
                ),
                "interrupted_reserved_attempts": interrupted,
                "quality90": sum(observed_scores) / 12
                if len(observed_scores) == 12
                else None,
                "quality90_observed": sum(observed_scores) / len(observed_scores)
                if observed_scores
                else None,
                "generation_seconds_p50": quantile(times, 0.5),
                "generation_seconds_p95": quantile(times, 0.95),
                "observed_latency_count": len(times),
                "errors": {
                    error: errors.count(error) for error in set(errors) if error
                },
                "not_run_reasons": {
                    reason: not_run_reasons.count(reason)
                    for reason in set(not_run_reasons)
                },
                "finish_reasons": {
                    reason: finish_reasons.count(reason)
                    for reason in set(finish_reasons)
                    if reason
                },
                "quota_observation": manifest["quota_evidence"]
                .get("models", {})
                .get(model),
                "operational_budget": manifest.get("operational_model_budgets", {}).get(
                    model
                ),
                "reported_usage": usage,
                "unknown_usage_artifacts": sum(
                    item is None
                    or item.get("input_tokens") is None
                    or item.get("output_tokens") is None
                    for item in usage
                ),
                "actual_models": sorted({model for model in actual_models if model}),
                "unknown_actual_model_artifacts": sum(
                    model is None for model in actual_models
                ),
                "execution_error_types": {
                    error: execution_errors.count(error)
                    for error in set(execution_errors)
                },
                "generation_attempts_including_availability": sum(
                    row["model"] == model for row in ledger.reserved()
                ),
            }
        )
    result = {
        "cohort": manifest["cohort"],
        "models": rows,
        "generation_attempts": len(ledger.reserved()),
        "total_generation_attempts_with_prior": len(ledger.reserved())
        + manifest["external_generation_attempts"],
        "prior_failed_probe_attempts": manifest.get("prior_probes", {}).get(
            "consumed_generation_attempts", 0
        ),
        "attempt_ceiling": ATTEMPT_CEILING,
        "external_generation_attempts": manifest["external_generation_attempts"],
        "cost": "UNKNOWN",
        "selection_changes_default": False,
        "ranking": [
            row["model"]
            for row in sorted(rows, key=lambda row: -(row["quality90"] or 0))
            if row["quality90"] is not None
        ],
        "uncertainty": "6전략×2회 소규모 관측 순위이며 모집단 우월성·수익성·Sol 비교 점수를 주장하지 않는다. 미실행·미평가를 0점으로 채우지 않는다.",
    }
    write_json(root / "report.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("metadata", "run", "evaluate", "report"))
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--free-evidence", type=Path)
    parser.add_argument("--quota-evidence", type=Path)
    parser.add_argument("--models-file", type=Path)
    parser.add_argument("--metadata-project-id")
    parser.add_argument("--prior-probes", type=Path)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not root.is_relative_to(ROOT / "runs"):
        parser.error("산출물은 현재 워크트리의 runs/ 아래에만 기록합니다")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / ".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.stage in ("metadata", "run"):
            if not args.key_file or not args.free_evidence:
                parser.error("승인된 --key-file과 --free-evidence가 필요합니다")
            evidence = read_json(args.free_evidence)
            validate_free(evidence)
            key, key_hash = load_credentials(args.key_file)
            write_json(
                root / ".credential-binding.json",
                {"key_file_sha256": key_hash, "project_id": evidence["project_id"]},
                immutable=True,
            )
            if args.stage == "metadata":
                metadata(root, key, evidence)
            else:
                if not args.quota_evidence:
                    parser.error("생성 전 --quota-evidence가 필요합니다")
                listed = read_json(args.models_file or root / "models.json")
                if "project_id" not in listed and args.metadata_project_id:
                    listed = {**listed, "project_id": args.metadata_project_id}
                manifest = build_manifest(
                    evidence, read_json(args.quota_evidence), listed
                )
                if args.prior_probes:
                    bind_prior_probes(
                        manifest, args.prior_probes, root, key_hash=key_hash
                    )
                manifest["evaluation_environment"] = evaluation_environment()
                write_json(root / "manifest.json", manifest, immutable=True)
                Runner(root, manifest, key).run()
        elif args.stage == "evaluate":
            evaluate(root)
        else:
            print(json.dumps(report(root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
