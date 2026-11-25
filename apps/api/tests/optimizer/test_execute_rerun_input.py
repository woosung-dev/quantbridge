# OptimizerService._execute 가 재실행 입력 판정(rerun_input) 실패를 드러내는 표면 — DB 없이 잰다
"""`_execute` 의 실패 분기 3개와 legacy 경고 로그명을 고정한다.

`message_internal` 은 `OptimizerService.run` 이 truncate 해 `error_message` 로 넘기는 문자열이라
전문 일치로 잰다.
판정 자체(핀 누락은 fallback 하지 않는다 · 경고가 조회보다 먼저다)는
`tests/backtest/test_rerun_input.py` 가 잰다.
engine_version 가드는 `_execute` 에 인라인이라 거부·통과 양쪽을 여기서 잰다.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backtest.engine import PINE_V2_ENGINE_VERSION
from src.backtest.models import Backtest
from src.optimizer import service as optimizer_service
from src.optimizer.exceptions import OptimizationExecutionError
from src.optimizer.models import OptimizationRun
from src.optimizer.service import OptimizerService


def _make_backtest(*, pinned: bool, engine_version: str | None = None) -> Backtest:
    bt = MagicMock(spec=Backtest)
    bt.id = uuid4()
    bt.user_id = uuid4()
    bt.strategy_id = uuid4()
    bt.strategy_version_id = uuid4() if pinned else None
    bt.engine_version = engine_version
    return cast(Backtest, bt)


def _make_service(*, strategy: Any = None) -> tuple[OptimizerService, AsyncMock, AsyncMock]:
    """`get_version_by_id` 는 None 을 명시한다 — 맨 AsyncMock 은 non-None 을 돌려줘 분기에 못 간다."""
    strategy_repo = AsyncMock()
    strategy_repo.get_version_by_id.return_value = None
    strategy_repo.find_by_id_and_owner.return_value = strategy
    provider = AsyncMock()
    service = OptimizerService(
        repo=AsyncMock(),
        backtest_repo=AsyncMock(),
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=MagicMock(),
    )
    return service, strategy_repo, provider


def _spy_warning(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """caplog 대신 module logger 를 직접 잰다 — 로깅 설정에 따라 caplog 가 비는 일이 없다."""
    spy = MagicMock()
    monkeypatch.setattr(optimizer_service.logger, "warning", spy)
    return spy


async def _execute(service: OptimizerService, bt: Backtest) -> OptimizationExecutionError:
    with pytest.raises(OptimizationExecutionError) as exc_info:
        await service._execute(MagicMock(spec=OptimizationRun), bt)
    return exc_info.value


async def test_unsupported_engine_version_is_rejected_before_any_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bt = _make_backtest(pinned=True, engine_version="code_v1")
    service, strategy_repo, provider = _make_service()
    warning = _spy_warning(monkeypatch)

    exc = await _execute(service, bt)

    assert exc.message_public == "Backtest engine version is not supported for optimization."
    assert exc.message_internal == f"backtest_id={bt.id} engine_version=code_v1"
    strategy_repo.get_version_by_id.assert_not_awaited()
    strategy_repo.find_by_id_and_owner.assert_not_awaited()
    provider.get_ohlcv.assert_not_awaited()
    warning.assert_not_called()


async def test_pine_v2_engine_version_passes_the_guard() -> None:
    """현재 엔진(pine_v2) 행은 가드에서 막히지 않고 다음 판정(핀 조회)까지 간다."""
    bt = _make_backtest(pinned=True, engine_version=PINE_V2_ENGINE_VERSION)
    service, strategy_repo, _provider = _make_service()

    exc = await _execute(service, bt)

    assert exc.message_public == "Strategy version is no longer available for optimization."
    strategy_repo.get_version_by_id.assert_awaited_once_with(
        bt.strategy_version_id, strategy_id=bt.strategy_id
    )


async def test_missing_pinned_version_is_an_error_not_a_silent_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bt = _make_backtest(pinned=True)
    service, strategy_repo, provider = _make_service(strategy=MagicMock())
    warning = _spy_warning(monkeypatch)

    exc = await _execute(service, bt)

    assert exc.message_public == "Strategy version is no longer available for optimization."
    assert exc.message_internal == (
        f"strategy_version_id={bt.strategy_version_id} strategy_id={bt.strategy_id} not found"
    )
    strategy_repo.find_by_id_and_owner.assert_not_awaited()
    provider.get_ohlcv.assert_not_awaited()
    warning.assert_not_called()


async def test_legacy_row_with_missing_strategy_warns_then_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bt = _make_backtest(pinned=False)
    service, strategy_repo, provider = _make_service(strategy=None)
    warning = _spy_warning(monkeypatch)

    exc = await _execute(service, bt)

    assert exc.message_public == "Strategy no longer available for optimization."
    assert exc.message_internal == f"strategy_id={bt.strategy_id} owner={bt.user_id} not found"
    warning.assert_called_once_with(
        "optimizer_run_without_pinned_strategy_version",
        extra={"backtest_id": str(bt.id), "strategy_id": str(bt.strategy_id)},
    )
    strategy_repo.find_by_id_and_owner.assert_awaited_once_with(bt.strategy_id, bt.user_id)
    provider.get_ohlcv.assert_not_awaited()
