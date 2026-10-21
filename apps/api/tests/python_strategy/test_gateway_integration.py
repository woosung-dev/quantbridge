"""API·실제 HTTP/gVisor·DB 결과 저장의 경계를 함께 검증한다."""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pandas as pd
import pytest

from src.python_strategy.dependencies import get_python_strategy_service
from src.python_strategy.repository import PythonStrategyRepository
from src.python_strategy.service import PythonStrategyService

SOURCE = """def on_bar(ctx, state):
    if ctx["bar"]["index"] == 2:
        return {"action": "long"}
    if ctx["bar"]["index"] == 12:
        return {"action": "close"}
    return {"action": "hold"}
"""

# 사용자 소스가 아닌 고정된 gateway 시작 코드다. 토큰 값은 argv/로그에 넣지 않는다.
_GATEWAY_LAUNCHER = """
import pathlib
import sys
import uvicorn
from src.strategy.python_runtime.gateway import create_app
token = pathlib.Path(sys.argv[1]).read_text().strip()
uvicorn.run(create_app(token), fd=int(sys.argv[2]), workers=1, access_log=False)
"""
_API_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
async def isolated_gateway(tmp_path: Path) -> AsyncGenerator[tuple[str, str], None]:
    """기존 실행기를 쓰지 않고 동적 loopback 소켓을 자식에게 넘긴다."""
    token = secrets.token_urlsafe(48)
    token_file = tmp_path / "runner-token"
    token_file.write_text(token)
    token_file.chmod(0o600)
    log_path = tmp_path / "gateway.log"
    # 앱/DB 시크릿을 독립 gateway에 복제하지 않으며 Docker 접속 대상은 유지한다.
    inherited = (
        "PATH",
        "HOME",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
    )
    environment = {key: os.environ[key] for key in inherited if key in os.environ}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener, log_path.open("wb") as log:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        assert port != 8190
        process = await asyncio.to_thread(
            subprocess.Popen,
            [sys.executable, "-c", _GATEWAY_LAUNCHER, str(token_file), str(listener.fileno())],
            cwd=_API_ROOT,
            env=environment,
            pass_fds=(listener.fileno(),),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        url = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 45
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                while time.monotonic() < deadline:
                    assert process.poll() is None, log_path.read_text()
                    try:
                        response = await client.get(
                            f"{url}/healthz", headers={"Authorization": f"Bearer {token}"}
                        )
                        if response.status_code == 200 and response.json().get("available") is True:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("독립 gVisor gateway 준비 실패: " + log_path.read_text())
            yield url, token
        finally:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait, timeout=5)


@pytest.mark.integration
async def test_api_submission_real_gateway_and_completed_database_result(
    app, client, db_session, mock_authed_user, isolated_gateway
):
    runner_url, runner_token = isolated_gateway
    start, end = datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 1, 2, tzinfo=UTC)
    warmup_start = datetime(2024, 12, 31, 22, tzinfo=UTC)
    prices = [Decimal(100 + index) for index in range(26)]
    frame = pd.DataFrame(
        {
            "open": prices,
            "high": [price + 1 for price in prices],
            "low": [price - 1 for price in prices],
            "close": prices,
            "volume": [Decimal("100")] * 26,
        },
        index=pd.date_range(warmup_start, periods=26, freq="1h"),
    )
    rates = pd.Series(
        [Decimal("0.0001"), Decimal("0.0002"), Decimal("0.0003")],
        index=pd.date_range(start, periods=3, freq="8h"),
        dtype=object,
    )
    provider, funding_repo, dispatch = Mock(), Mock(), Mock()
    provider.get_ohlcv = AsyncMock(return_value=frame)
    funding_repo.get_funding_series = AsyncMock(return_value=rates)
    service = PythonStrategyService(
        PythonStrategyRepository(db_session),
        provider,
        funding_repo,
        runner_url=runner_url,
        runner_token=runner_token,
        dispatch=dispatch,
    )
    app.dependency_overrides[get_python_strategy_service] = lambda: service
    try:
        capability = await client.get("/api/v1/python-strategies/capabilities")
        assert capability.status_code == 200
        assert capability.json()["available"] is True
        saved_response = await client.post(
            "/api/v1/python-strategies",
            json={"name": "실제 격리 실행 검증", "source": SOURCE, "warmup_bars": 2},
        )
        assert saved_response.status_code == 201, saved_response.text
        saved = saved_response.json()
        source_hash = hashlib.sha256(SOURCE.encode()).hexdigest()
        assert saved["source_hash"] == source_hash
        request = {
            "expected_version_id": saved["version_id"],
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }
        route = f"/api/v1/python-strategies/{saved['id']}/backtests"
        conflict = await client.post(route, json={**request, "expected_version_id": str(uuid4())})
        assert conflict.status_code == 409
        # 실행 API에 자동매매 승인 같은 별도 권한을 끼워 넣을 수 없다.
        unsupported = await client.post(route, json={**request, "auto_trade": True})
        assert unsupported.status_code == 422
        dispatch.assert_not_called()
        submitted = await client.post(route, json=request)
        assert submitted.status_code == 202, submitted.text
        run = submitted.json()
        assert run["status"] == "pending" and run["result"] is None
        assert run["version_id"] == saved["version_id"]
        dispatch.assert_called_once_with(run["id"])

        changed = await client.put(
            f"/api/v1/python-strategies/{saved['id']}",
            json={
                "name": "실행 후 편집",
                "source": 'def on_bar(ctx, state): return {"action": "hold"}',
                "warmup_bars": 2,
            },
        )
        assert changed.status_code == 200
        assert changed.json()["version_id"] != saved["version_id"]
        # Celery를 거치지 않고 동일 작업 본문을 호출한다. 원격 client/HTTP는 실제 경로다.
        await service.execute(UUID(run["id"]))
        persisted_run = await service.repo.run(UUID(run["id"]))
        assert persisted_run is not None
        db_session.expire(persisted_run)
        completed_response = await client.get(f"/api/v1/python-strategies/backtests/{run['id']}")
        assert completed_response.status_code == 200
        completed = completed_response.json()
        assert completed["status"] == "completed", completed
        assert completed["version_id"] == saved["version_id"]
        assert completed["completed_at"] and completed["error"] is None
        result = completed["result"]
        assert result["provenance"]["source_hash"] == source_hash
        assert result["provenance"]["runner_image_id"].startswith("sha256:")
        assert len(result["provenance"]["environment_digest"]) == 64
        assert result["config_used"]["fill_timing"] == "next_bar_open"
        assert result["config_used"]["include_funding"] is True
        assert result["validation"] == {"status": "research_only", "holdout_passed": False}
        assert len(result["equity_curve"]) == 24
        assert len(result["trades"]) == 1
        trade = result["trades"][0]
        assert trade["status"] == "closed" and trade["direction"] == "long"
        assert trade["entry_bar_index"] == 1 and trade["exit_bar_index"] == 11
        assert trade["entry_phase"] == trade["exit_phase"] == "bar_open"
        assert Decimal(trade["entry_price"]) == Decimal("103")
        assert Decimal(trade["exit_price"]) == Decimal("113")
        assert Decimal(result["metrics"]["total_funding"]) > 0
        provider.get_ohlcv.assert_awaited_once_with("BTC/USDT", "1h", warmup_start, end)
        funding_repo.get_funding_series.assert_awaited_once_with(
            "bybit", "BTC/USDT:USDT", start, end
        )
    finally:
        app.dependency_overrides.pop(get_python_strategy_service, None)
