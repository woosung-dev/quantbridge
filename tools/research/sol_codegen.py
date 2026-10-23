"""Codex 인증을 사용하는 Sol 전용 생성. 생성 코드는 호스트에서 실행하지 않는다."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

MODEL = "gpt-6.1-sol"
EFFORT = "high"
OUTPUT_TOKEN_BUDGET = 16_384
TIMEOUT_SECONDS = 180
CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "source_code": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["source_code", "assumptions"],
    "additionalProperties": False,
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def strict_schema(value: Any) -> Any:
    """구조화 출력은 기본값이 있는 필드도 명시하며 nullable은 그대로 보존한다."""
    if isinstance(value, list):
        return [strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {
        key: strict_schema(item) for key, item in value.items() if key != "default"
    }
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(result.get("properties", {}))
    return result


def generation_usage(events: str) -> tuple[dict[str, int], bool]:
    """프로토콜 로그만 읽고 도구 사용과 토큰 사용을 분리한다."""
    usage: dict[str, int] = {}
    used_tools = False
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            usage = {str(k): int(v) for k, v in event.get("usage", {}).items()}
        item = event.get("item") or {}
        if item.get("type") in {
            "command_execution",
            "mcp_tool_call",
            "web_search",
            "file_change",
        }:
            used_tools = True
    return usage, used_tools


def generate(
    prompt: str,
    destination: Path,
    *,
    schema: dict[str, Any] | None = None,
    timeout: float = TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """고정 모델의 한 번 생성과 증거를 보존한다. 실패도 캐시에 남긴다."""
    chosen_schema = strict_schema(schema or CODE_SCHEMA)
    request = {
        "model": MODEL,
        "effort": EFFORT,
        "prompt": prompt,
        "schema": chosen_schema,
        "timeout": timeout,
        "output_token_budget": OUTPUT_TOKEN_BUDGET,
        "token_limit_enforcement": "post_response_cli_usage",
    }
    job_hash = digest(request)
    destination.mkdir(parents=True, exist_ok=True)
    result_path = destination / "generation.json"
    if result_path.exists():
        cached = json.loads(result_path.read_text())
        if cached.get("job_hash") != job_hash:
            raise ValueError("생성 입력이 다른 기존 디렉터리를 덮어쓸 수 없습니다")
        payload_path = destination / "payload.json"
        if cached["status"] == "completed" and (
            not payload_path.exists()
            or digest(json.loads(payload_path.read_text()))
            != cached.get("payload_hash")
        ):
            raise ValueError("캐시된 생성 산출물 hash가 다릅니다")
        return cached
    request_path = destination / "request.json"
    if request_path.exists():
        if digest(json.loads(request_path.read_text())) != job_hash:
            raise ValueError("중단된 생성 요청의 입력이 다릅니다")
        interrupted = {
            "job_hash": job_hash,
            "model": MODEL,
            "effort": EFFORT,
            "status": "interrupted",
            "error": "이전 호출의 완료 증거가 없어 재호출하지 않습니다",
            "usage": {},
            "usage_unavailable": True,
            "tool_used": None,
            "duration_seconds": timeout,
            "payload_hash": None,
            "token_limit_enforcement": "post_response_cli_usage",
        }
        result_path.write_text(json.dumps(interrupted, ensure_ascii=False, indent=2))
        return interrupted
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2))
    cli = shutil.which("codex")
    if not cli:
        raise RuntimeError("Sol 생성에 필요한 Codex CLI가 없습니다")
    started = time.monotonic()
    status, error, payload = "failed", None, None
    stdout, stderr, usage, used_tools = "", "", {}, False
    # 평가 원문·기준 계산·레포 규칙에 접근하지 않는 별도 작업 디렉터리다.
    with tempfile.TemporaryDirectory(prefix="qb-sol-generation-") as raw:
        workspace = Path(raw)
        schema_path = workspace / "output-schema.json"
        output_path = workspace / "response.json"
        schema_path.write_text(json.dumps(chosen_schema))
        env = {
            k: os.environ[k]
            for k in (
                "PATH",
                "HOME",
                "USER",
                "LANG",
                "TMPDIR",
                "CODEX_HOME",
                "HTTPS_PROXY",
                "HTTP_PROXY",
                "NO_PROXY",
            )
            if k in os.environ
        }
        command = [
            cli,
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--model",
            MODEL,
            "--config",
            f'model_reasoning_effort="{EFFORT}"',
            "--json",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "-",
        ]
        instruction = (
            "도구·검색·셸을 사용하지 마세요. 파일을 읽거나 쓰지 마세요. "
            "주어진 공개 계약만으로 코드를 생성하고 최종 JSON만 반환하세요. "
            "생성한 코드를 실행하지 마세요.\n\n" + prompt
        )
        try:
            with subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workspace,
                env=env,
                start_new_session=True,
            ) as process:
                try:
                    stdout, stderr = process.communicate(instruction, timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate()
                    raise subprocess.TimeoutExpired(
                        command, timeout, output=stdout, stderr=stderr
                    ) from None
                return_code = process.returncode
            usage, used_tools = generation_usage(stdout)
            if return_code:
                error = f"Codex 종료 코드 {return_code}"
            elif used_tools:
                error = "생성 중 금지된 도구 사용"
            elif usage.get("output_tokens", 0) > OUTPUT_TOKEN_BUDGET:
                error = "응답 토큰 예산 초과"
            elif not output_path.exists():
                error = "구조화 생성 응답 없음"
            else:
                payload = json.loads(output_path.read_text())
                if not isinstance(payload, dict):
                    raise ValueError("생성 응답이 JSON 객체가 아닙니다")
                status = "completed"
        except subprocess.TimeoutExpired as exc:
            status, error = "timeout", "생성 전체 시간 초과"
            stdout = (
                (exc.stdout or b"").decode()
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            stderr = (
                (exc.stderr or b"").decode()
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            )
            usage, used_tools = generation_usage(stdout)
        except (OSError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
    (destination / "events.jsonl").write_text(stdout)
    (destination / "stderr.txt").write_text(stderr)
    if payload is not None:
        (destination / "payload.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2)
        )
    result = {
        "job_hash": job_hash,
        "model": MODEL,
        "effort": EFFORT,
        "status": status,
        "error": error,
        "usage": usage,
        "tool_used": used_tools,
        "duration_seconds": time.monotonic() - started,
        "payload_hash": digest(payload) if payload is not None else None,
        "token_limit_enforcement": "post_response_cli_usage",
        "model_attestation": "requested_cli_flag_no_response_model_metadata",
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--schema", type=Path)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(
        Path(__file__).resolve().parents[2] / "runs"
    ):
        parser.error("생성 산출물은 레포 runs/ 안에 둡니다")
    result = generate(
        args.prompt.read_text(),
        args.output,
        schema=json.loads(args.schema.read_text()) if args.schema else None,
    )
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
