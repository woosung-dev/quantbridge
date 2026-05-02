"""Dogfood 일일 리포트 자동 생성 Celery 태스크.

Beat schedule: 매일 22:00 UTC (celery_app.py에 등록).
출력: HTML 파일 → settings.dogfood_report_output_dir/<YYYY-MM-DD>.html

ReportData 집계:
- OrderRepository.get_daily_summary() → total_pnl, filled_count, rejected_count
- KillSwitchEventRepository.list_by_date() → ks_events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

logger = logging.getLogger(__name__)


# Celery prefork 워커의 event loop 재사용 버그 (PR #51) 방지를 위해
# 전역 engine cache 를 두지 않고 매 task 호출마다 새 engine 을 생성한 뒤
# try/finally 로 dispose 한다.
def create_worker_engine_and_sm() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """매 호출마다 새 engine + async_sessionmaker 튜플 반환.

    호출자는 engine 을 finally 에서 dispose 해야 한다. 테스트에서는 이 함수를
    monkeypatch 로 대체 가능.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


# ---------------------------------------------------------------------------
# ReportData
# ---------------------------------------------------------------------------


@dataclass
class KsEventSummary:
    id: UUID
    trigger_type: str
    trigger_value: Decimal
    threshold: Decimal
    triggered_at: datetime
    resolved: bool


@dataclass
class ReportData:
    report_date: date
    total_pnl: Decimal = Decimal("0")
    filled_orders: int = 0
    rejected_orders: int = 0
    kill_switch_events: list[KsEventSummary] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@shared_task(name="reporting.dogfood_daily", max_retries=0)  # type: ignore[untyped-decorator]
def dogfood_daily_report_task(report_date_iso: str | None = None) -> dict[str, Any]:
    """일일 리포트 생성. report_date_iso 미지정 시 어제(UTC) 날짜 사용."""
    if report_date_iso:
        report_date = date.fromisoformat(report_date_iso)
    else:
        report_date = datetime.now(UTC).date()
        # 22:00 UTC에 실행 → 당일 리포트 (오늘 0:00~22:00 포함)
    # Sprint 18 BL-080: asyncio.run → run_in_worker_loop (Option C).
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_generate(report_date))


async def _async_generate(report_date: date) -> dict[str, Any]:
    from src.trading.repository import KillSwitchEventRepository, OrderRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            order_repo = OrderRepository(session)
            ks_repo = KillSwitchEventRepository(session)

            total_pnl, filled, rejected = await order_repo.get_daily_summary(report_date)
            ks_events_raw = await ks_repo.list_by_date(report_date)
    finally:
        await engine.dispose()

    ks_events = [
        KsEventSummary(
            id=ev.id,
            trigger_type=ev.trigger_type.value,
            trigger_value=ev.trigger_value,
            threshold=ev.threshold,
            triggered_at=ev.triggered_at,
            resolved=ev.resolved_at is not None,
        )
        for ev in ks_events_raw
    ]

    data = ReportData(
        report_date=report_date,
        total_pnl=total_pnl,
        filled_orders=filled,
        rejected_orders=rejected,
        kill_switch_events=ks_events,
    )

    html = _render_html(data)
    output_path = _write_report(html, report_date)

    logger.info(
        "dogfood_report_generated",
        extra={
            "date": str(report_date),
            "filled": filled,
            "rejected": rejected,
            "pnl": str(total_pnl),
            "ks_events": len(ks_events),
            "output": str(output_path),
        },
    )
    return {
        "date": str(report_date),
        "total_pnl": str(total_pnl),
        "filled_orders": filled,
        "rejected_orders": rejected,
        "kill_switch_events": len(ks_events),
        "output_path": str(output_path),
    }


def _render_html(data: ReportData) -> str:
    pnl_color = "#4ade80" if data.total_pnl >= 0 else "#f87171"
    pnl_sign = "+" if data.total_pnl >= 0 else ""
    rejected_color = "#f87171" if data.rejected_orders > 0 else "#e2e8f0"
    ks_color = "#f87171" if data.kill_switch_events else "#e2e8f0"
    ks_rows = ""
    for ev in data.kill_switch_events:
        resolved_badge = (
            '<span style="color:#4ade80">✓ resolved</span>'
            if ev.resolved
            else '<span style="color:#f87171">● active</span>'
        )
        ks_rows += (
            f"<tr><td>{ev.trigger_type}</td>"
            f"<td>{ev.trigger_value}</td>"
            f"<td>{ev.threshold}</td>"
            f"<td>{ev.triggered_at.strftime('%H:%M UTC')}</td>"
            f"<td>{resolved_badge}</td></tr>"
        )

    if data.kill_switch_events:
        ks_table = (
            "<table><thead><tr>"
            "<th>Type</th><th>Value</th><th>Threshold</th><th>Time</th><th>Status</th>"
            f"</tr></thead><tbody>{ks_rows}</tbody></table>"
        )
    else:
        ks_table = '<p class="empty">이벤트 없음</p>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dogfood Daily Report — {data.report_date}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0b1020;color:#e2e8f0;font-family:'Inter',system-ui,sans-serif;padding:2rem}}
    h1{{font-size:1.5rem;font-weight:700;margin-bottom:.25rem}}
    .subtitle{{color:#64748b;font-size:.875rem;margin-bottom:2rem}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin-bottom:2rem}}
    .card{{background:#111827;border:1px solid #1e293b;border-radius:.75rem;padding:1.25rem}}
    .card-label{{color:#64748b;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem}}
    .card-value{{font-size:1.75rem;font-weight:700}}
    table{{width:100%;border-collapse:collapse;background:#111827;border-radius:.75rem;overflow:hidden}}
    th,td{{padding:.75rem 1rem;text-align:left;border-bottom:1px solid #1e293b;font-size:.875rem}}
    th{{color:#64748b;font-weight:600;text-transform:uppercase;font-size:.75rem}}
    .section-title{{font-size:1rem;font-weight:600;margin:1.5rem 0 .75rem}}
    .empty{{color:#475569;text-align:center;padding:2rem}}
  </style>
</head>
<body>
  <h1>QuantBridge Dogfood Daily Report</h1>
  <p class="subtitle">{data.report_date} UTC — 자동 생성</p>

  <div class="grid">
    <div class="card">
      <div class="card-label">Realized PnL</div>
      <div class="card-value" style="color:{pnl_color}">{pnl_sign}{data.total_pnl} USDT</div>
    </div>
    <div class="card">
      <div class="card-label">Filled Orders</div>
      <div class="card-value">{data.filled_orders}</div>
    </div>
    <div class="card">
      <div class="card-label">Rejected Orders</div>
      <div class="card-value" style="color:{rejected_color}">{data.rejected_orders}</div>
    </div>
    <div class="card">
      <div class="card-label">Kill Switch Events</div>
      <div class="card-value" style="color:{ks_color}">{len(data.kill_switch_events)}</div>
    </div>
  </div>

  <p class="section-title">Kill Switch Events</p>
  {ks_table}
</body>
</html>"""


def _write_report(html: str, report_date: date) -> Path:
    """HTML 파일을 출력 디렉토리에 저장."""
    output_dir = Path(settings.dogfood_report_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{report_date}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
