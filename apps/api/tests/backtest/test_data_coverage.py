"""요청 기간과 실제 엔진 입력의 차이를 결과까지 보존한다."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from src.backtest.data_coverage import measure_data_coverage
from tests.backtest.test_warnings_wiring import _CLEAN, _run_and_detail


def test_requested_year_with_only_three_months_is_incomplete():
    index = pd.date_range("2024-10-01", "2024-12-31", freq="1h", tz="UTC")
    result = measure_data_coverage(
        index, "1h", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC)
    )
    assert result.actual_start == datetime(2024, 10, 1, tzinfo=UTC)
    assert result.actual_end == datetime(2024, 12, 31, tzinfo=UTC)
    assert result.bar_count == len(index)
    assert result.missing_bars == 274 * 24


def test_middle_gap_is_visible_even_when_endpoints_match():
    index = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    result = measure_data_coverage(
        index.delete(2), "1h", index[0].to_pydatetime(), index[-1].to_pydatetime()
    )
    assert result.expected_bars == 5
    assert result.missing_bars == 1


def test_unaligned_request_counts_only_candle_open_times():
    index = pd.date_range("2024-01-01T01:00Z", periods=2, freq="1h")
    result = measure_data_coverage(
        index,
        "1h",
        datetime(2024, 1, 1, 0, 30, tzinfo=UTC),
        datetime(2024, 1, 1, 2, 30, tzinfo=UTC),
    )
    assert result.expected_bars == 2
    assert result.missing_bars == 0


def test_empty_data_has_no_actual_interval():
    result = measure_data_coverage(
        pd.DatetimeIndex([], tz="UTC"),
        "1h",
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 2, tzinfo=UTC),
    )
    assert result.actual_start is None
    assert result.actual_end is None
    assert result.missing_bars == 25


@pytest.mark.asyncio
async def test_coverage_survives_execution_persistence_and_response(db_session, tmp_path):
    detail = await _run_and_detail(db_session, tmp_path, _CLEAN)
    assert detail.data_coverage is not None
    assert detail.data_coverage.bar_count == 25
    assert detail.data_coverage.missing_bars == 0


@pytest.mark.asyncio
async def test_partial_data_is_persisted_without_relabelling_request(db_session, tmp_path):
    from unittest.mock import AsyncMock

    from tests.backtest.test_warnings_wiring import _request, _seed, _service

    service = _service(db_session, tmp_path)
    user, strategy = await _seed(db_session, _CLEAN)
    request = _request(strategy.id)
    request.period_end = datetime(2024, 12, 31, tzinfo=UTC)
    created = await service.submit(request, user_id=user.id)
    commit_spy = AsyncMock(wraps=service.repo.commit)
    service.repo.commit = commit_spy
    await service.run(created.backtest_id)
    commit_spy.assert_awaited()
    assert commit_spy.await_count == 2  # running 전이와 결과 저장을 각각 확정한다.
    detail = await service.get(created.backtest_id, user_id=user.id)
    assert detail.period_end == request.period_end
    assert detail.data_coverage.bar_count == 50
    assert detail.data_coverage.actual_end == datetime(2024, 1, 3, 1, tzinfo=UTC)
    assert detail.data_coverage.missing_bars == 8761 - 50
    shared = await service.create_share(created.backtest_id, user_id=user.id)
    public = await service.view_share(shared.share_token)
    assert public.data_coverage == detail.data_coverage


def test_daily_grid_uses_utc_even_when_request_has_an_offset():
    index = pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")
    start = datetime.fromisoformat("2024-01-01T09:00:00+09:00")
    end = datetime.fromisoformat("2024-01-02T09:00:00+09:00")
    result = measure_data_coverage(index, "1d", start, end)
    assert result.expected_bars == 2
    assert result.missing_bars == 0


@pytest.mark.parametrize("end_inclusive,expected,missing", [(False, 48, 0), (True, 49, 1)])
def test_complete_48_hours_respects_requested_end_boundary(end_inclusive, expected, missing):
    start = datetime(2026, 4, 11, tzinfo=UTC)
    end = datetime(2026, 4, 13, tzinfo=UTC)
    index = pd.date_range(start, end, freq="1h", inclusive="left")
    result = measure_data_coverage(index, "1h", start, end, end_inclusive=end_inclusive)
    assert result.bar_count == 48
    assert result.expected_bars == expected
    assert result.missing_bars == missing


def test_exclusive_end_still_counts_a_real_middle_gap():
    start = datetime(2026, 4, 11, tzinfo=UTC)
    end = datetime(2026, 4, 13, tzinfo=UTC)
    index = pd.date_range(start, end, freq="1h", inclusive="left").delete(20)
    result = measure_data_coverage(index, "1h", start, end, end_inclusive=False)
    assert result.bar_count == 47
    assert result.expected_bars == 48
    assert result.missing_bars == 1


def test_exclusive_unaligned_end_filters_against_original_utc_timestamp():
    start = datetime.fromisoformat("2026-04-11T09:30:00+09:00")
    end = datetime.fromisoformat("2026-04-11T11:30:00+09:00")
    index = pd.date_range("2026-04-11T01:00Z", periods=2, freq="1h")
    result = measure_data_coverage(index, "1h", start, end, end_inclusive=False)
    assert result.expected_bars == 2  # 02:00도 원 종료 시각 02:30 UTC 이전이다.
    assert result.missing_bars == 0


@pytest.mark.asyncio
async def test_code_coverage_persists_exclusive_evaluation_without_warmup(db_session, monkeypatch):
    from decimal import Decimal
    from unittest.mock import AsyncMock, Mock

    from src.backtest.dispatcher import FakeTaskDispatcher
    from src.backtest.engine.types import BacktestMetrics, BacktestResult
    from src.backtest.models import BacktestStatus
    from src.backtest.repository import BacktestRepository
    from src.backtest.service import BacktestService
    from src.strategy.code_service import CodeStrategyService
    from src.strategy.repository import StrategyRepository
    from tests.backtest.test_code_strategy_version_selection import _code_request, _request, _user

    user = await _user(db_session)
    strategy_repo = StrategyRepository(db_session)
    strategy = await CodeStrategyService(strategy_repo).create(_code_request(), owner_id=user.id)
    request = _request(
        strategy.id,
        period_start=datetime(2026, 4, 11, tzinfo=UTC),
        period_end=datetime(2026, 4, 13, tzinfo=UTC),
        include_funding=False,
    )
    index = pd.date_range(request.period_start, request.period_end, freq="1h", inclusive="left")
    parent_index = pd.date_range(index[0] - pd.Timedelta(hours=50), index[-1], freq="1h")
    parent = pd.DataFrame(
        dict.fromkeys(("open", "high", "low", "close", "volume"), 100), index=parent_index
    )
    provider = AsyncMock()
    provider.get_ohlcv.side_effect = [parent, parent]
    result = BacktestResult(
        metrics=BacktestMetrics(Decimal(0), Decimal(0), Decimal(0), Decimal(0), 0),
        equity_curve=pd.Series([Decimal("10000")] * 48, index=index),
    )
    native = Mock(return_value=result)
    monkeypatch.setattr("src.strategy.product_execution.run_product_backtest", native)
    service = BacktestService(
        repo=BacktestRepository(db_session),
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeTaskDispatcher(),
    )
    submitted = await service.submit(request, user_id=user.id)
    await service.run(submitted.backtest_id)
    detail = await service.get(submitted.backtest_id, user_id=user.id)
    assert detail.status == BacktestStatus.COMPLETED
    native.assert_called_once()
    assert detail.data_coverage.bar_count == 48
    assert detail.data_coverage.expected_bars == 48
    assert detail.data_coverage.missing_bars == 0
    assert detail.data_coverage.actual_start == request.period_start
    assert detail.data_coverage.actual_end == index[-1].to_pydatetime()
