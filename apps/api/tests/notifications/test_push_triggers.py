"""트리거 — 체결·거부·Kill Switch·백테스트 종료가 푸시를 **정확히 1번** enqueue 하고,
enqueue 가 터져도 본 경로는 멀쩡하다 (pwa.md §3.5 · §3.6).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest import service as backtest_service_module
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.models import BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.notifications import dispatcher as push_dispatcher
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository
from src.tasks import notifications as push_task
from src.trading import realtime_publisher

_USER_ID = "4a0c7e7e-0000-4000-8000-000000000001"


class _RecordingPool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.calls.append((channel, message))


def _order_payload(state: str) -> dict[str, Any]:
    return {
        "order_id": "order-123",
        "state": state,
        "symbol": "BTC/USDT:USDT",
        "side": "buy",
        "source": "watchdog",
    }


@pytest.fixture
def pool(monkeypatch: pytest.MonkeyPatch) -> _RecordingPool:
    recording = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: recording)
    return recording


@pytest.fixture
def enqueue(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    spy = MagicMock()
    monkeypatch.setattr(realtime_publisher, "enqueue_push", spy)
    return spy


# --- publish_realtime -------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_realtime_enqueues_push_for_filled_order(
    pool: _RecordingPool, enqueue: MagicMock
) -> None:
    await realtime_publisher.publish_realtime(_USER_ID, "order_update", _order_payload("filled"))

    enqueue.assert_called_once_with(
        _USER_ID,
        {
            "title": "주문 체결",
            "body": "BTC/USDT:USDT buy",
            "url": "/trading",
            "tag": "order:order-123",
        },
    )
    assert len(pool.calls) == 1


@pytest.mark.asyncio
async def test_publish_realtime_enqueues_push_for_rejected_order(
    pool: _RecordingPool, enqueue: MagicMock
) -> None:
    await realtime_publisher.publish_realtime(_USER_ID, "order_update", _order_payload("rejected"))

    enqueue.assert_called_once()
    user_id, payload = enqueue.call_args.args
    assert user_id == _USER_ID
    assert payload["title"] == "주문 거부"
    assert payload["tag"] == "order:order-123"


@pytest.mark.asyncio
async def test_publish_realtime_enqueues_push_for_kill_switch(
    pool: _RecordingPool, enqueue: MagicMock
) -> None:
    await realtime_publisher.publish_realtime(
        _USER_ID, "kill_switch", {"event_id": "evt-1", "trigger_type": "daily_loss"}
    )

    enqueue.assert_called_once_with(
        _USER_ID,
        {
            "title": "킬 스위치 발동",
            "body": "일일 손실 한도 초과",
            "url": "/trading",
            "tag": "kill_switch",
        },
    )


def test_kill_switch_push_body_uses_fe_labels_and_falls_back_to_raw() -> None:
    """FE `KS_TRIGGER_LABELS` 3종과 같은 문구 · 모르는 값은 원문."""
    bodies = {
        trigger: push_dispatcher.realtime_push_payload(
            "kill_switch", {"event_id": "e", "trigger_type": trigger}
        )["body"]  # type: ignore[index]
        for trigger in ("daily_loss", "cumulative_loss", "api_error", "brand_new_trigger")
    }

    assert bodies == {
        "daily_loss": "일일 손실 한도 초과",
        "cumulative_loss": "누적 손실 한도 초과",
        "api_error": "거래소 API 오류",
        "brand_new_trigger": "brand_new_trigger",
    }


@pytest.mark.asyncio
async def test_publish_realtime_skips_push_for_invalid_payload(
    pool: _RecordingPool, enqueue: MagicMock
) -> None:
    """계약 검증에 실패한 payload 는 Redis 에도 푸시에도 안 간다("None None" 본문 방지)."""
    await realtime_publisher.publish_realtime(
        _USER_ID, "order_update", {"order_id": "order-1", "state": "filled"}
    )

    enqueue.assert_not_called()
    assert pool.calls == []


@pytest.mark.asyncio
async def test_publish_realtime_skips_push_for_submitted_order(
    pool: _RecordingPool, enqueue: MagicMock
) -> None:
    """submitted·cancelled 주문과 Kill Switch **해제**는 알리지 않는다."""
    await realtime_publisher.publish_realtime(_USER_ID, "order_update", _order_payload("submitted"))
    await realtime_publisher.publish_realtime(_USER_ID, "order_update", _order_payload("cancelled"))
    await realtime_publisher.publish_realtime(
        _USER_ID, "kill_switch_resolved", {"event_id": "evt-1", "trigger_type": "daily_loss"}
    )

    enqueue.assert_not_called()
    assert len(pool.calls) == 3


@pytest.mark.asyncio
async def test_publish_realtime_survives_push_enqueue_failure(
    pool: _RecordingPool, monkeypatch: pytest.MonkeyPatch
) -> None:
    exploding = MagicMock(side_effect=RuntimeError("broker down"))
    monkeypatch.setattr(realtime_publisher, "enqueue_push", exploding)

    await realtime_publisher.publish_realtime(_USER_ID, "order_update", _order_payload("filled"))

    exploding.assert_called_once()
    assert len(pool.calls) == 1


def test_enqueue_push_delays_task_only_when_vapid_configured(
    monkeypatch: pytest.MonkeyPatch, vapid_off: None
) -> None:
    """enqueue 게이트 — 키가 없으면 브로커에 아무것도 안 쌓고, 있으면 정확히 1번 쌓는다."""
    delay = MagicMock()
    monkeypatch.setattr(push_task.send_push_task, "delay", delay)
    payload = {"title": "t", "body": "b", "url": "/dashboard", "tag": "x"}

    push_dispatcher.enqueue_push(_USER_ID, payload)
    delay.assert_not_called()

    from pydantic import SecretStr

    monkeypatch.setattr("src.core.config.settings.vapid_public_key", "pub")
    monkeypatch.setattr("src.core.config.settings.vapid_private_key", SecretStr("priv"))
    monkeypatch.setattr("src.core.config.settings.vapid_subject", "mailto:a@b.c")
    push_dispatcher.enqueue_push(_USER_ID, payload)
    delay.assert_called_once_with(_USER_ID, payload)


# --- BacktestService.run ----------------------------------------------------

# 진입 1회 + 청산 1회 — 이 픽스처에서 엔진이 COMPLETED 로 끝난다(test_warnings_wiring 의 _CLEAN).
_CLEAN_PINE = """//@version=5
strategy("clean")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0)
if bar_index == 3
    strategy.close("L")
"""


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "ohlcv"
    root.mkdir()
    rows = ["timestamp,open,high,low,close,volume"]
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(50):
        price = 100 + i * 0.5
        ts = (start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(f"{ts},{price},{price + 1},{price - 1},{price + 0.5},100.0")
    (root / "BTCUSDT_1h.csv").write_text("\n".join(rows))
    return root


class _BrokenProvider:
    async def get_ohlcv(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        raise RuntimeError("ohlcv source unavailable")


async def _submit(
    session: AsyncSession, provider: object
) -> tuple[BacktestService, User, Strategy, object]:
    user = User(id=uuid4(), auth_subject=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@ex.com")
    session.add(user)
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="EMA Crossover",
        pine_source=_CLEAN_PINE,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()
    service = BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=provider,  # type: ignore[arg-type]
        dispatcher=FakeTaskDispatcher(),
    )
    created = await service.submit(
        CreateBacktestRequest(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 2, tzinfo=UTC),
            initial_capital=Decimal("10000"),
        ),
        user_id=user.id,
    )
    await session.commit()
    return service, user, strategy, created.backtest_id


@pytest.mark.asyncio
async def test_backtest_completion_enqueues_push_once(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spy = MagicMock()
    monkeypatch.setattr(backtest_service_module, "enqueue_push", spy)
    service, user, _, backtest_id = await _submit(
        db_session, FixtureProvider(root=_fixture_root(tmp_path))
    )

    await service.run(backtest_id)  # type: ignore[arg-type]
    # 재전달 — 가드가 non-queued 로 건너뛴다. 종료는 1회뿐이므로 푸시도 1번이다.
    await service.run(backtest_id)  # type: ignore[arg-type]

    bt = await service.repo.get_by_id(backtest_id)  # type: ignore[arg-type]
    assert bt is not None and bt.status == BacktestStatus.COMPLETED
    spy.assert_called_once_with(
        str(user.id),
        {
            "title": "백테스트 완료",
            "body": "EMA Crossover",
            "url": f"/backtests/{backtest_id}",
            "tag": f"backtest:{backtest_id}",
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "error_marker"),
    [
        ("ohlcv_fetch_failed", "OHLCV fetch failed"),
        ("engine_error", "engine boom"),
        ("strategy_version_missing", "Strategy version not found"),
    ],
)
async def test_backtest_failure_enqueues_push_once(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    error_marker: str,
) -> None:
    """FAILED 를 기록하는 서로 다른 세 출구가 각각 푸시를 정확히 1번 건다.

    ★`error_marker` 로 **그 입력이 그 출구를 지났는지**를 함께 잰다 — 셋이 한 출구로 모이면
    나머지 둘의 반환값이 틀려도 초록이 된다(AGENTS.md §10 ③).
    """
    spy = MagicMock()
    monkeypatch.setattr(backtest_service_module, "enqueue_push", spy)
    provider: object = (
        _BrokenProvider()
        if failure == "ohlcv_fetch_failed"
        else FixtureProvider(root=_fixture_root(tmp_path))
    )
    service, user, _, backtest_id = await _submit(db_session, provider)
    if failure == "engine_error":
        # 엔진이 error outcome 을 낸 terminal write 분기(`fail(...)` → FAILED).
        monkeypatch.setattr(
            backtest_service_module,
            "run_backtest",
            lambda *_a, **_k: SimpleNamespace(status="error", result=None, error="engine boom"),
        )
    elif failure == "strategy_version_missing":
        # ★FK 가 RESTRICT 라 실제 DELETE 는 거부된다 — 실행 시점 조회가 비는 것으로 삭제를 재현한다.
        monkeypatch.setattr(
            service.strategy_repo, "get_version_by_id", AsyncMock(return_value=None)
        )

    await service.run(backtest_id)  # type: ignore[arg-type]
    await service.run(backtest_id)  # type: ignore[arg-type]

    bt = await service.repo.get_by_id(backtest_id)  # type: ignore[arg-type]
    assert bt is not None and bt.status == BacktestStatus.FAILED
    assert bt.error is not None and error_marker in bt.error
    spy.assert_called_once()
    user_id, payload = spy.call_args.args
    assert user_id == str(user.id)
    assert payload == {
        "title": "백테스트 실패",
        "body": "EMA Crossover",
        "url": f"/backtests/{backtest_id}",
        "tag": f"backtest:{backtest_id}",
    }


@pytest.mark.asyncio
async def test_backtest_survives_push_enqueue_failure(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exploding = MagicMock(side_effect=RuntimeError("broker down"))
    monkeypatch.setattr(backtest_service_module, "enqueue_push", exploding)
    service, _, _, backtest_id = await _submit(
        db_session, FixtureProvider(root=_fixture_root(tmp_path))
    )

    await service.run(backtest_id)  # type: ignore[arg-type]

    exploding.assert_called_once()
    bt = await service.repo.get_by_id(backtest_id)  # type: ignore[arg-type]
    assert bt is not None
    assert bt.status == BacktestStatus.COMPLETED
    assert bt.metrics is not None
    assert bt.completed_at is not None
