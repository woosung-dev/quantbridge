"""Terra·Antigravity 구독 CLI만 호출한다. 생성 코드는 실행하지 않는다."""

from __future__ import annotations

import ast
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from tools.research.editor_picks.common import (
    MODELS,
    cached,
    immutable,
    lock,
    receipt,
    sha,
    write,
)
from tools.research.sol_codegen import CODE_SCHEMA, generation_usage

CONTRACT = """공개 Pine 원문과 검토된 방향 바인딩을 그대로 재현하세요. 개선·최적화하지 마세요.
Python init(params)->dict(선택), on_bar(ctx,state)->dict 계약을 사용합니다.
ctx['history']는 현재 완료봉까지의 dict 목록이고 ctx['bar']는 현재봉,
ctx['position']은 direction(flat/long/short),size,average_price를 갖습니다.
OHLCV는 decimal 문자열입니다. 필요한 계산은 numpy/pandas/표준 라이브러리로 직접 구현하세요.
반환은 {'action':'hold'|'long'|'short'|'close'} 하나뿐입니다.
원문의 버전별 NA, seed, var 상태, 이전 봉, 동률·교차 조건과 기본 입력을 보존하세요.
같은 방향 신호도 원문 발생 시 그대로 반환하세요. 실행기가 중복 진입을 처리합니다.
SL/TP/수량/펀딩/체결/수익은 구현하지 마세요. 외부 실행기가 공통 정책으로 계산합니다.
미래 데이터·네트워크·파일·도구·검색·셸을 사용하지 마세요. 다른 전략을 만들지 마세요.
JSON 객체 {"source_code":"...","assumptions":["..."]}만 출력하세요.
"""


def parse_stream(stdout: str, arm: str) -> tuple[dict, dict, bool]:
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    if arm == "terra":
        finals = [e for e in events if e.get("type") == "turn.completed"]
        messages = [
            e["item"]["text"]
            for e in events
            if e.get("type") == "item.completed"
            and e.get("item", {}).get("type") == "agent_message"
        ]
        usage, tools = generation_usage(stdout)
        if len(finals) != 1 or len(messages) != 1:
            raise ValueError("Terra의 단일 완료 응답 증거가 없습니다")
        response = messages[0]
    else:
        initials = [e["init"] for e in events if e.get("event") == "init"]
        finals = [e["result"] for e in events if e.get("event") == "result"]
        if (
            len(initials) != 1
            or initials[0].get("model") != MODELS[arm]
            or len(finals) != 1
            or finals[0].get("status") != "SUCCESS"
            or finals[0].get("num_turns") != 1
        ):
            raise ValueError("Gemini의 요청 모델·단일 완료 응답 증거가 없습니다")
        tools = any(
            e.get("event") in {"tool_call", "tool_use", "permission_request"}
            or e.get("step_update", {}).get("step_type")
            not in {None, "user_input", "agent_response", "thought"}
            for e in events
        )
        response, usage = finals[0]["response"], finals[0].get("usage", {})
    if tools:
        raise ValueError("생성 중 도구 사용이 관측됐습니다")
    response = response.strip()
    if response.startswith("```json\n") and response.endswith("\n```"):
        response = response[8:-4]
    payload = json.loads(response)
    if (
        not isinstance(payload, dict)
        or set(payload) != {"source_code", "assumptions"}
        or not isinstance(payload["source_code"], str)
        or not payload["source_code"].strip()
        or len(payload["source_code"].encode()) > 131072
        or not isinstance(payload["assumptions"], list)
        or any(not isinstance(x, str) for x in payload["assumptions"])
    ):
        raise ValueError("생성 JSON이 source_code·assumptions 계약과 다릅니다")
    try:
        ast.parse(payload["source_code"])
    except SyntaxError as error:
        raise ValueError(f"python_syntax: {error.msg} line {error.lineno}") from error
    return payload, usage, tools


def generate(
    root: Path,
    item: dict,
    arm: str,
    attempt: int = 0,
    public_error: str | None = None,
    timeout: int = 180,
) -> dict:
    if arm not in MODELS or attempt not in (0, 1, 2):
        raise ValueError("두 모델과 최대 세 시도만 허용합니다")
    if (attempt == 0) != (public_error is None):
        raise ValueError("수정 시도에는 공개 구문·프로토콜 오류만 명시해야 합니다")
    source = (root / item["source_file"]).read_bytes().decode()
    if sha(source.encode()) != item["source_sha256"]:
        raise ValueError("공개 Pine 원문 해시가 다릅니다")
    prompt = (
        CONTRACT
        + "\n"
        + json.dumps(
            {
                "source": source,
                "pine_version": item.get("pine_version"),
                "bindings": item["signal_bindings"],
                "inputs": item.get("inputs", {}),
                "public_error": public_error,
            },
            ensure_ascii=False,
        )
    )
    request = {
        "arm": arm,
        "requested_model": MODELS[arm],
        "effort": "high",
        "source_sha256": item["source_sha256"],
        "prompt": prompt,
        "attempt": attempt,
        "timeout_seconds": timeout,
        "schema": CODE_SCHEMA,
        "adapter_sha256": sha(Path(__file__).read_bytes()),
    }
    folder = root / "generation" / item["id"] / arm / str(attempt)
    with lock(folder / ".lock"):
        previous = cached(folder, request)
        if previous is not None:
            return previous
        immutable(folder / "request.json", request)
        started = time.monotonic()
        stdout = stderr = ""
        details = {"actual_model": None, "usage": {}, "error": None}
        with tempfile.TemporaryDirectory(prefix="qb-editor-picks-generation-") as raw:
            workspace = Path(raw)
            schema = workspace / "schema.json"
            write(schema, CODE_SCHEMA)
            env = {
                key: value
                for key, value in os.environ.items()
                if key in {"PATH", "HOME", "USER", "LANG", "TMPDIR", "CODEX_HOME"}
            }
            cli = shutil.which("codex" if arm == "terra" else "agy")
            if cli is None:
                return receipt(
                    folder, request, "blocked", error="subscription_cli_missing"
                )
            if arm == "terra":
                command = [
                    cli,
                    "exec",
                    "--ignore-user-config",
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--model",
                    MODELS[arm],
                    "-c",
                    'model_reasoning_effort="high"',
                    "--json",
                    "--output-schema",
                    str(schema),
                    "-",
                ]
                stdin = prompt
            else:
                command = [
                    cli,
                    "--model",
                    MODELS[arm],
                    "--effort",
                    "high",
                    "--mode",
                    "plan",
                    "--sandbox",
                    "--output-format",
                    "stream-json",
                    "--print-timeout",
                    "0",
                    "--print",
                    prompt,
                ]
                stdin = ""
            try:
                with subprocess.Popen(
                    command,
                    cwd=workspace,
                    env=env,
                    text=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                ) as process:
                    try:
                        stdout, stderr = process.communicate(stdin, timeout=timeout)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            stdout, stderr = process.communicate(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            stdout, stderr = process.communicate()
                        raise TimeoutError("CLI 전체 제한 시간 초과") from None
                if process.returncode or "timeout" in stderr.lower():
                    raise ValueError("CLI 종료 실패 또는 불완전 turn")
                payload, usage, _ = parse_stream(stdout, arm)
                if usage.get("output_tokens", 0) > 16384:
                    raise ValueError("관측 출력 토큰 예산 초과")
                write(folder / "payload.json", payload)
                (folder / "source.py").write_text(payload["source_code"])
                status = "completed"
                details["usage"] = usage
            except (OSError, ValueError, TimeoutError) as error:
                status = "timeout" if isinstance(error, TimeoutError) else "failed"
                details["error"] = str(error)
            (folder / "stdout.jsonl").write_text(stdout)
            (folder / "stderr.txt").write_text(stderr)
        return receipt(
            folder,
            request,
            status,
            duration_seconds=time.monotonic() - started,
            usage_unavailable=not bool(details["usage"]),
            **details,
        )
