"""Dogfood 일일 리포트 태스크 테스트."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Beat schedule 등록 확인
# ---------------------------------------------------------------------------

def test_dogfood_beat_registered():
    from src.tasks import celery_app  # type: ignore[attr-defined]

    schedule = celery_app.conf.beat_schedule
    assert "dogfood-daily-report" in schedule
    entry = schedule["dogfood-daily-report"]
    assert entry["task"] == "reporting.dogfood_daily"


def test_dogfood_task_registered():
    import src.tasks.dogfood_report  # noqa: F401 — 등록 강제
    from src.tasks import celery_app  # type: ignore[attr-defined]

    assert "reporting.dogfood_daily" in celery_app.tasks


# ---------------------------------------------------------------------------
# HTML 렌더링
# ---------------------------------------------------------------------------

def test_render_html_positive_pnl():
    from src.tasks.dogfood_report import ReportData, _render_html

    data = ReportData(
        report_date=date(2026, 4, 21),
        total_pnl=Decimal("12.34"),
        filled_orders=5,
        rejected_orders=1,
        kill_switch_events=[],
    )
    html = _render_html(data)
    assert "12.34" in html
    assert "#4ade80" in html  # 양수 → 초록
    assert "이벤트 없음" in html


def test_render_html_negative_pnl():
    from src.tasks.dogfood_report import ReportData, _render_html

    data = ReportData(
        report_date=date(2026, 4, 21),
        total_pnl=Decimal("-5.00"),
        filled_orders=2,
        rejected_orders=3,
    )
    html = _render_html(data)
    assert "#f87171" in html  # 음수 → 빨간색


def test_render_html_with_ks_events():
    from src.tasks.dogfood_report import KsEventSummary, ReportData, _render_html

    ks = KsEventSummary(
        id=MagicMock(),
        trigger_type="cumulative_loss",
        trigger_value=Decimal("150"),
        threshold=Decimal("100"),
        triggered_at=datetime(2026, 4, 21, 14, 0, tzinfo=UTC),
        resolved=False,
    )
    data = ReportData(
        report_date=date(2026, 4, 21),
        kill_switch_events=[ks],
    )
    html = _render_html(data)
    assert "cumulative_loss" in html
    assert "active" in html


# ---------------------------------------------------------------------------
# write_report — tmp_path로 출력 디렉토리 리다이렉션
# ---------------------------------------------------------------------------

def test_write_report(tmp_path):
    from src.tasks.dogfood_report import _write_report

    with patch("src.tasks.dogfood_report.settings") as mock_settings:
        mock_settings.dogfood_report_output_dir = str(tmp_path / "reports")
        path = _write_report("<html>test</html>", date(2026, 4, 21))

    assert path.exists()
    assert path.name == "2026-04-21.html"
    assert path.read_text() == "<html>test</html>"


# ---------------------------------------------------------------------------
# _async_generate — DB mock
# ---------------------------------------------------------------------------

async def test_async_generate_success(tmp_path):
    from src.tasks.dogfood_report import _async_generate

    mock_order_repo = MagicMock()
    mock_order_repo.get_daily_summary = AsyncMock(return_value=(Decimal("42.0"), 10, 2))

    mock_ks_repo = MagicMock()
    mock_ks_repo.list_by_date = AsyncMock(return_value=[])

    mock_session = MagicMock()
    mock_sm_instance = MagicMock()
    mock_sm_instance.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm_instance.__aexit__ = AsyncMock(return_value=None)
    mock_sm = MagicMock(return_value=mock_sm_instance)

    import src.trading.repository as repo_mod

    orig_order = repo_mod.OrderRepository
    orig_ks = repo_mod.KillSwitchEventRepository
    repo_mod.OrderRepository = lambda s: mock_order_repo  # type: ignore[assignment]
    repo_mod.KillSwitchEventRepository = lambda s: mock_ks_repo  # type: ignore[assignment]

    class _FakeEngine:
        async def dispose(self) -> None:
            pass

    with patch(
        "src.tasks.dogfood_report.create_worker_engine_and_sm",
        return_value=(_FakeEngine(), mock_sm),
    ), patch("src.tasks.dogfood_report.settings") as mock_cfg:
        mock_cfg.dogfood_report_output_dir = str(tmp_path / "reports")
        try:
            result = await _async_generate(date(2026, 4, 21))
        finally:
            repo_mod.OrderRepository = orig_order
            repo_mod.KillSwitchEventRepository = orig_ks

    assert result["filled_orders"] == 10
    assert result["rejected_orders"] == 2
    assert result["total_pnl"] == "42.0"
    assert result["kill_switch_events"] == 0
