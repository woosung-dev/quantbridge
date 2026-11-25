# StressTestService 실행 경로가 재실행 입력 판정(rerun_input) 실패를 드러내는 표면 — DB 없이 잰다
"""엔진을 재실행하는 3개 kind 의 실패 문구(`kind_label` 포함 전문)와 legacy 경고 로그명을 고정한다.

`ValueError` 의 문자열은 `StressTestService.run` 이 그대로 실패 사유로 넘기므로 전문 일치로 잰다.
판정 자체(핀 누락은 fallback 하지 않는다 · 경고가 조회보다 먼저다)는
`tests/backtest/test_rerun_input.py` 가, 핀된 스냅샷이 실제로 실행되는지는
`test_strategy_version_pinning.py` 가 잰다.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backtest.models import Backtest
from src.stress_test import service as stress_service
from src.stress_test.models import StressTest
from src.stress_test.service import StressTestService

_KINDS = [
    ("_execute_walk_forward", "walk-forward"),
    ("_execute_cost_assumption_sensitivity", "cost assumption sensitivity"),
    ("_execute_param_stability", "param stability"),
]


def _make_backtest(*, pinned: bool) -> Backtest:
    bt = MagicMock(spec=Backtest)
    bt.id = uuid4()
    bt.user_id = uuid4()
    bt.strategy_id = uuid4()
    bt.strategy_version_id = uuid4() if pinned else None
    return cast(Backtest, bt)


def _make_service() -> tuple[StressTestService, AsyncMock, AsyncMock]:
    """두 조회 모두 None 을 명시한다 — 맨 AsyncMock 은 non-None 을 돌려줘 실패 분기에 못 간다."""
    strategy_repo = AsyncMock()
    strategy_repo.get_version_by_id.return_value = None
    strategy_repo.find_by_id_and_owner.return_value = None
    provider = AsyncMock()
    service = StressTestService(
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
    monkeypatch.setattr(stress_service.logger, "warning", spy)
    return spy


async def _execute(service: StressTestService, entry: str, bt: Backtest) -> ValueError:
    with pytest.raises(ValueError) as exc_info:
        await getattr(service, entry)(MagicMock(spec=StressTest), bt)
    return exc_info.value


@pytest.mark.parametrize(("entry", "kind_label"), _KINDS)
async def test_missing_pinned_version_names_the_kind_and_never_falls_back(
    entry: str, kind_label: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bt = _make_backtest(pinned=True)
    service, strategy_repo, provider = _make_service()
    warning = _spy_warning(monkeypatch)

    exc = await _execute(service, entry, bt)

    assert str(exc) == f"Strategy version no longer available for {kind_label}"
    strategy_repo.find_by_id_and_owner.assert_not_awaited()
    provider.get_ohlcv.assert_not_awaited()
    warning.assert_not_called()


@pytest.mark.parametrize(("entry", "kind_label"), _KINDS)
async def test_legacy_row_with_missing_strategy_warns_then_fails(
    entry: str, kind_label: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bt = _make_backtest(pinned=False)
    service, strategy_repo, provider = _make_service()
    warning = _spy_warning(monkeypatch)

    exc = await _execute(service, entry, bt)

    assert str(exc) == f"Strategy no longer available for {kind_label}"
    warning.assert_called_once_with(
        "stress_test_run_without_pinned_strategy_version",
        extra={"backtest_id": str(bt.id), "strategy_id": str(bt.strategy_id)},
    )
    strategy_repo.find_by_id_and_owner.assert_awaited_once_with(bt.strategy_id, bt.user_id)
    provider.get_ohlcv.assert_not_awaited()
