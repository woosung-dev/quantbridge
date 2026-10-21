"""API/Celery 프로세스는 인증된 전용 실행기에 요청만 보낸다."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pandas as pd

from src.backtest.engine.types import BacktestConfig, BacktestResult
from src.strategy.python_runtime.protocol import PythonRunnerUnavailable, PythonRuntimeError
from src.strategy.python_runtime.serialization import (
    bars_payload,
    funding_payload,
    json_value,
    result_from_payload,
)


def _headers(token: str) -> dict[str, str]:
    if len(token) < 32:
        raise PythonRunnerUnavailable("Python 실행기 인증 설정이 없습니다")
    return {"Authorization": "Bearer " + token}


def run_remote_python_backtest_payload(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
    funding_rates: pd.Series | None = None,
    params: dict[str, Any] | None = None,
    warmup_bars: int = 0,
    *,
    base_url: str,
    token: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    """반환값은 metrics/trades/equity_curve/config_used/provenance JSON 객체다."""
    try:
        response = httpx.post(
            base_url.rstrip("/") + "/v1/backtests",
            headers=_headers(token),
            timeout=930,
            json={
                "job_id": job_id or str(uuid.uuid4()),
                "source": source,
                "bars": bars_payload(ohlcv),
                "funding": funding_payload(funding_rates),
                "params": params or {},
                "config": json_value(config or BacktestConfig()),
                "warmup_bars": warmup_bars,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("provenance"), dict):
            raise PythonRuntimeError("Python 실행기의 재현 정보가 없습니다")
        result_from_payload(payload)
        return payload
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 503:
            raise PythonRunnerUnavailable("Python 격리 실행기를 사용할 수 없습니다") from exc
        try:
            detail = str(exc.response.json().get("detail", "실행 실패"))[:500]
        except (ValueError, AttributeError):
            detail = "실행 실패"
        raise PythonRuntimeError(
            f"Python 실행기 오류({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise PythonRunnerUnavailable("Python 격리 실행기에 연결하지 못했습니다") from exc


def run_remote_python_backtest(*args: Any, **kwargs: Any) -> BacktestResult:
    return result_from_payload(run_remote_python_backtest_payload(*args, **kwargs))


def cancel_remote_python_backtest(job_id: str, *, base_url: str, token: str) -> None:
    try:
        response = httpx.post(
            base_url.rstrip("/") + f"/v1/backtests/{uuid.UUID(job_id)}/cancel",
            headers=_headers(token),
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PythonRunnerUnavailable("Python 격리 실행기 취소 요청에 실패했습니다") from exc


def runner_available(*, base_url: str, token: str) -> bool:
    try:
        response = httpx.get(base_url.rstrip("/") + "/healthz", headers=_headers(token), timeout=15)
        return response.status_code == 200 and response.json().get("available") is True
    except (httpx.HTTPError, PythonRunnerUnavailable, ValueError):
        return False
