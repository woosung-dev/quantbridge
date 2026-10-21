"""소유권·불변 버전·실행 실패·취소 경합의 실제 저장 경계 검증."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pandas as pd
import pytest

from src.common.exceptions import NotFoundError
from src.python_strategy.data_window import complete_funding, complete_window
from src.python_strategy.exceptions import PythonRunConflict, PythonRunnerUnavailable
from src.python_strategy.repository import PythonStrategyRepository
from src.python_strategy.schemas import (
    PythonBacktestRequest,
    PythonCapabilities,
    SavePythonStrategy,
)
from src.python_strategy.service import PythonStrategyService

SOURCE = 'def on_bar(ctx, state):\n    return {"action": "hold"}\n'


@pytest.fixture
def service(db_session):
    return PythonStrategyService(
        PythonStrategyRepository(db_session),
        Mock(),
        AsyncMock(),
        runner_url="",
        runner_token="",
        dispatch=Mock(),
    )


def request():
    return PythonBacktestRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2025, 1, 1, tzinfo=UTC),
        period_end=datetime(2025, 1, 2, tzinfo=UTC),
    )


async def saved(service, user):
    return await service.save(
        SavePythonStrategy(name="연구", source=SOURCE, warmup_bars=2), user.id
    )


async def test_save_commits_without_executing_source(service, authed_user, monkeypatch):
    commit = AsyncMock(wraps=service.repo.commit)
    monkeypatch.setattr(service.repo, "commit", commit)
    data = SavePythonStrategy(
        name="연구", source='raise RuntimeError("호스트 실행 금지")\n' + SOURCE
    )
    strategy = await service.save(data, authed_user.id)
    assert strategy.source == data.source
    commit.assert_awaited_once()


async def test_edit_preserves_version_used_by_pending_run(service, authed_user, monkeypatch):
    old = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    run = await service.submit(old.id, request(), authed_user.id)
    updated = await service.save(
        SavePythonStrategy(name="수정", source=SOURCE + "# 새 버전\n"), authed_user.id, old.id
    )
    assert old.version_id != updated.version_id
    assert (await service.repo.version(old.version_id)).source == old.source
    assert (await service.get_run(run.id, authed_user.id)).version_id == old.version_id


async def test_other_owner_cannot_get_edit_or_run(service, authed_user):
    strategy = await saved(service, authed_user)
    for operation in (
        service.get(strategy.id, uuid4()),
        service.save(SavePythonStrategy(name="수정", source=SOURCE), uuid4(), strategy.id),
        service.runs(strategy.id, uuid4()),
    ):
        with pytest.raises(NotFoundError):
            await operation


async def test_unconfigured_runner_does_not_enqueue(service, authed_user):
    strategy = await saved(service, authed_user)
    with pytest.raises(PythonRunnerUnavailable):
        await service.submit(strategy.id, request(), authed_user.id)
    service.dispatch.assert_not_called()
    assert not await service.repo.runs(strategy.id, authed_user.id)


async def test_submit_commits_before_dispatch_and_limits_active(service, authed_user, monkeypatch):
    strategy = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    commit = AsyncMock(wraps=service.repo.commit)
    monkeypatch.setattr(service.repo, "commit", commit)
    service.dispatch = Mock(side_effect=lambda _: commit.assert_awaited_once())
    run = await service.submit(strategy.id, request(), authed_user.id)
    assert run.status == "pending"
    with pytest.raises(PythonRunConflict):
        await service.submit(strategy.id, request(), authed_user.id)


async def test_dispatch_failure_is_persisted(service, authed_user, monkeypatch):
    strategy = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    service.dispatch = Mock(side_effect=RuntimeError("broker offline"))
    with pytest.raises(PythonRunnerUnavailable):
        await service.submit(strategy.id, request(), authed_user.id)
    assert (await service.runs(strategy.id, authed_user.id))[0].status == "failed"


async def test_cancel_commits_and_duplicate_task_cannot_claim(service, authed_user, monkeypatch):
    strategy = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    run = await service.submit(strategy.id, request(), authed_user.id)
    commit = AsyncMock(wraps=service.repo.commit)
    monkeypatch.setattr(service.repo, "commit", commit)
    cancelled = await service.cancel(run.id, authed_user.id)
    commit.assert_awaited_once()
    assert cancelled.status == "cancelled"
    assert not await service.repo.transition(run.id, ["pending"], "running")
    await service.execute(run.id)
    assert (await service.get_run(run.id, authed_user.id)).status == "cancelled"


async def test_cancelled_result_cannot_be_overwritten(service, authed_user, monkeypatch):
    strategy = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    run = await service.submit(strategy.id, request(), authed_user.id)
    await service.cancel(run.id, authed_user.id)
    assert not await service.repo.transition(
        run.id, ["running"], "completed", result={"wrong": True}
    )


async def test_version_changed_in_another_tab_requires_review(service, authed_user, monkeypatch):
    strategy = await saved(service, authed_user)
    await service.save(
        SavePythonStrategy(name="수정", source=SOURCE + "# next\n"), authed_user.id, strategy.id
    )
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    with pytest.raises(PythonRunConflict) as exc:
        await service.submit(
            strategy.id,
            request().model_copy(update={"expected_version_id": strategy.version_id}),
            authed_user.id,
        )
    assert exc.value.code == "python_strategy_version_conflict"
    service.dispatch.assert_not_called()


async def test_cancel_pending_to_running_race_reaches_gateway(service, authed_user, monkeypatch):
    import httpx

    strategy = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    run = await service.submit(strategy.id, request(), authed_user.id)
    original_transition = service.repo.transition

    async def raced_transition(run_id, previous, status, **values):
        if previous == ["pending"] and status == "cancelled":
            assert await original_transition(run_id, ["pending"], "running")
            await service.repo.commit()
        return await original_transition(run_id, previous, status, **values)

    reached = []

    def gateway_response(req):
        reached.append(req.url.path)
        return httpx.Response(200, json={"cancelled": True})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(service.repo, "transition", raced_transition)
    monkeypatch.setattr(
        "src.python_strategy.service.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(gateway_response)),
    )
    service.runner_url = "http://runner.invalid"
    result = await service.cancel(run.id, authed_user.id)
    assert result.status == "cancelled"
    assert reached == [f"/v1/backtests/{run.id}/cancel"]


async def test_execute_missing_data_fails_before_runner(service, authed_user, monkeypatch):
    strategy = await saved(service, authed_user)
    monkeypatch.setattr(
        service, "capabilities", AsyncMock(return_value=PythonCapabilities(available=True))
    )
    run = await service.submit(strategy.id, request(), authed_user.id)
    service.provider.get_ohlcv = AsyncMock(return_value=pd.DataFrame())
    runner = Mock(side_effect=AssertionError("자료 검증 전에 호출하면 안 됨"))
    monkeypatch.setattr(
        "src.strategy.python_runtime.client.run_remote_python_backtest_payload", runner
    )
    await service.execute(run.id)
    result = await service.get_run(run.id, authed_user.id)
    assert result.status == "failed" and result.result is None
    runner.assert_not_called()


def frame():
    return pd.DataFrame(
        {name: [Decimal("100")] * 24 for name in ("open", "high", "low", "close", "volume")},
        index=pd.date_range("2025-01-01", periods=24, freq="1h", tz="UTC"),
    )


def test_full_requested_window_cannot_be_silently_shortened():
    data = frame()
    spec = request()
    assert len(complete_window(data, spec.period_start, spec.period_end, "1h")) == 24
    for broken in (data.iloc[1:], data.drop(data.index[5]), pd.concat([data, data.iloc[:1]])):
        with pytest.raises(ValueError):
            complete_window(broken, spec.period_start, spec.period_end, "1h")


def test_funding_missing_settlement_is_not_zero_cost():
    spec = request()
    rates = pd.Series(
        [Decimal("0.001")] * 3, index=pd.date_range(spec.period_start, periods=3, freq="8h")
    )
    assert len(complete_funding(rates, spec.period_start, spec.period_end)) == 3
    with pytest.raises(ValueError, match="펀딩"):
        complete_funding(rates.iloc[1:], spec.period_start, spec.period_end)


@pytest.mark.parametrize(
    "source", ["import os", "def on_bar(:", "async def on_bar(ctx, state): pass"]
)
def test_source_requires_sync_entrypoint(source):
    with pytest.raises(ValueError):
        SavePythonStrategy(name="bad", source=source)


@pytest.mark.parametrize("params", [{"value": float("nan")}, {"value": float("inf")}])
def test_params_cannot_carry_nonfinite_values(params):
    with pytest.raises(ValueError):
        SavePythonStrategy(name="bad", source=SOURCE, params=params)


@pytest.mark.parametrize(
    ("timeframe", "start_hour", "end_hour", "valid"),
    [("1h", 1, 2, False), ("4h", 4, 8, False), ("1h", 0, 1, True), ("1h", 7, 9, True)],
)
def test_requested_window_requires_an_observed_settlement(timeframe, start_hour, end_hour, valid):
    values = {
        "symbol": "BTC/USDT",
        "timeframe": timeframe,
        "period_start": datetime(2025, 1, 1, start_hour, tzinfo=UTC),
        "period_end": datetime(2025, 1, 1, end_hour, tzinfo=UTC),
    }
    if valid:
        assert PythonBacktestRequest(**values).timeframe == timeframe
    else:
        with pytest.raises(ValueError, match="펀딩 정산이 최소 1회"):
            PythonBacktestRequest(**values)


def test_source_utf8_bytes_cannot_exceed_sandbox_protocol_limit():
    with pytest.raises(ValueError, match="UTF-8"):
        SavePythonStrategy(name="large", source=SOURCE + "\n#" + "가" * 44_000)


async def test_authenticated_http_store_and_ownership(client, mock_authed_user):
    saved_response = await client.post(
        "/api/v1/python-strategies", json={"name": "실험", "source": SOURCE}
    )
    assert saved_response.status_code == 201
    data = saved_response.json()
    assert data["source"] == SOURCE and data["version_id"]
    listed = (await client.get("/api/v1/python-strategies")).json()
    assert [row["id"] for row in listed["items"]] == [data["id"]]
    capabilities = await client.get("/api/v1/python-strategies/capabilities")
    assert capabilities.status_code == 200 and capabilities.json()["available"] is False
    response = await client.get(f"/api/v1/python-strategies/{uuid4()}")
    assert response.status_code == 404


async def test_unauthenticated_python_api_is_rejected(client):
    response = await client.get("/api/v1/python-strategies")
    assert response.status_code == 401
