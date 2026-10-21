"""Docker gVisor 전용 전송. 호스트 Python 실행 경로는 존재하지 않는다."""

from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import time
import uuid
from contextlib import suppress
from threading import Lock
from typing import Any

from src.strategy.python_runtime.protocol import (
    MAX_FRAME_BYTES,
    MAX_OUTPUT_BYTES,
    PythonRunnerTimeout,
    PythonRunnerUnavailable,
    PythonRuntimeError,
)

DEFAULT_IMAGE = "quantbridge-python-runner:local"
_DOCKER = shutil.which("docker") or "/usr/bin/docker"


def sandbox_command(image_id: str, name: str) -> list[str]:
    """이미지 ID 를 고정하고 호스트 파일·환경·네트워크를 전달하지 않는다."""
    return [
        _DOCKER,
        "run",
        "--rm",
        "-i",
        "--name",
        name,
        "--runtime=runsc",
        "--network=none",
        "--read-only",
        "--user=10001:10001",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=64",
        "--cpus=1",
        "--memory=1g",
        "--memory-swap=1g",
        "--ulimit=nofile=64:64",
        "--ulimit=core=0:0",
        "--log-driver=none",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--env=OPENBLAS_NUM_THREADS=1",
        "--env=OMP_NUM_THREADS=1",
        "--env=MKL_NUM_THREADS=1",
        *[
            f"--env={key}="
            for key in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "NO_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
                "no_proxy",
            )
        ],
        image_id,
    ]


class DockerPythonTransport:
    """JSONL stdin/stdout, 전체 15분·출력 16MiB. 종료 시 컨테이너도 제거한다."""

    def __init__(self, image: str = DEFAULT_IMAGE, timeout: float = 900) -> None:
        self.name = "qb-python-" + uuid.uuid4().hex
        self.deadline = time.monotonic() + min(timeout, 900)
        self._buffer = bytearray()
        self._output_bytes = 0
        self._process: subprocess.Popen[bytes] | None = None
        self._close_lock = Lock()
        try:
            runtimes = subprocess.run(  # noqa: S603 — 고정 argv, shell 미사용
                [_DOCKER, "info", "--format", "{{json .Runtimes}}"],
                capture_output=True,
                check=True,
                timeout=10,
            )
            if "runsc" not in json.loads(runtimes.stdout):
                raise PythonRunnerUnavailable("gVisor runsc runtime 이 등록되지 않았습니다")
            inspected = subprocess.run(  # noqa: S603 — 이미지는 운영자 설정이며 소스 입력과 분리
                [_DOCKER, "image", "inspect", "--format", "{{.Id}}", image],
                capture_output=True,
                check=True,
                timeout=10,
            )
            self.image_id = inspected.stdout.decode().strip()
            if not self.image_id.startswith("sha256:"):
                raise PythonRunnerUnavailable("격리 이미지 ID 를 확인할 수 없습니다")
            self._process = subprocess.Popen(  # noqa: S603 — 고정 격리 옵션, 이미지 ID 만 전달
                sandbox_command(self.image_id, self.name),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
            assert self._process.stdin is not None and self._process.stdout is not None
            os.set_blocking(self._process.stdin.fileno(), False)
            os.set_blocking(self._process.stdout.fileno(), False)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self.close()
            if isinstance(exc, PythonRuntimeError):
                raise
            raise PythonRunnerUnavailable("격리 실행기를 시작할 수 없습니다") from exc

    def _wait(self, descriptor: int, event: int) -> None:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PythonRunnerTimeout("Python 실행 시간이 900초 한도를 초과했습니다")
        with selectors.DefaultSelector() as selector:
            selector.register(descriptor, event)
            if not selector.select(remaining):
                raise PythonRunnerTimeout("Python 격리 실행 시간이 초과되었습니다")

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise PythonRunnerUnavailable("격리 실행기가 닫혔습니다")
        try:
            data = memoryview((json.dumps(message, allow_nan=False) + "\n").encode())
            while data:
                self._wait(process.stdin.fileno(), selectors.EVENT_WRITE)
                try:
                    data = data[os.write(process.stdin.fileno(), data) :]
                except BlockingIOError:
                    continue
            while b"\n" not in self._buffer:
                self._wait(process.stdout.fileno(), selectors.EVENT_READ)
                try:
                    chunk = os.read(process.stdout.fileno(), 4096)
                except BlockingIOError:
                    continue
                if not chunk:
                    raise PythonRuntimeError("격리 전략 프로세스가 응답 없이 종료되었습니다")
                self._buffer.extend(chunk)
                self._output_bytes += len(chunk)
                if len(self._buffer) > MAX_FRAME_BYTES or self._output_bytes > MAX_OUTPUT_BYTES:
                    raise PythonRuntimeError("격리 전략 출력 한도를 초과했습니다")
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            value = json.loads(line)
            if not isinstance(value, dict):
                raise PythonRuntimeError("격리 전략 응답은 JSON 객체여야 합니다")
            if "error" in value:
                raise PythonRuntimeError("격리 전략 오류: " + str(value["error"])[:500])
            return value
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PythonRuntimeError("격리 전략 JSON 통신에 실패했습니다") from exc

    def close(self) -> None:
        with self._close_lock:
            process = self._process
            self._process = None
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()
            with suppress(OSError, subprocess.SubprocessError):
                subprocess.run(  # noqa: S603 — 자체 생성한 컨테이너 이름만 사용
                    [_DOCKER, "rm", "-f", self.name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                )
