# 엔진 경고가 계산된 자리에서 죽지 않고 원장·응답까지 도달한다 (2026-08-15 · U8).
"""백테스트 경고 배선 — **순수 함수가 아니라 배선을 잰다.**

**고치기 전에 무슨 일이 벌어졌나.** `v2_adapter.py:218-221` 은 주석에서
「사용자가 silent success 받지 않도록 `BacktestOutcome.parse.warnings` 로 노출」이라고
스스로 적어 뒀다. 그런데 그 노출을 **받는 소비자가 없었다** — `BacktestService` 는
`outcome.parse` 를 한 번도 참조하지 않았고(grep 0건), 경고는 계산된 자리에서 사라졌다.

★**엔진을 실제로 태운다.** `run_backtest` 를 mock 하면 「배선이 있다」가 아니라 「내가 준
값을 그대로 돌려준다」만 증명된다. 여기서는 진짜 Pine 소스를 진짜 엔진에 넣고,
DB 를 거쳐 `_to_detail` 응답까지 따라간다. 이 회차의 위험 4번이 「레인 C 는 배선이
주제다 — 순수 함수 테스트는 배선의 증거가 아니다」였다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import TaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.serializers import dedupe_engine_warnings
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository

# `trail_points=` 는 여전히 미지원이라 엔진이 「무시했다」 경고를 낸다.
# ★`limit=` 을 쓰지 않는다 — 그건 이제 지원 대상이고 다른 경고를 낸다(아래 별도 케이스).
_NOISY = """//@version=5
strategy("noisy")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0, trail_points=5.0)
"""

# 지정가 진입 — 백테스트와 라이브가 다르게 행동한다는 사실을 경고로 선언한다.
_LIMIT_ENTRY = """//@version=5
strategy("limit entry")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0, limit=50.0)
"""

# ★음성 대조 — 경고가 없는 전략. 이게 없으면 「항상 경고를 채워 넣기」로도 통과한다.
_CLEAN = """//@version=5
strategy("clean")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0)
if bar_index == 3
    strategy.close("L")
"""


class _FakeDispatcher(TaskDispatcher):
    def dispatch_backtest(self, backtest_id: object) -> str:  # type: ignore[override]
        return "task-id"


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


async def _seed(session: AsyncSession, source: str) -> tuple[User, Strategy]:
    user = User(id=uuid4(), auth_subject=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@ex.com")
    session.add(user)
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="warnings wiring",
        pine_source=source,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()
    return user, strategy


def _service(session: AsyncSession, tmp_path: Path) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=_fixture_root(tmp_path)),
        dispatcher=_FakeDispatcher(),
    )


def _request(strategy_id: object) -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )


async def _run_and_detail(session: AsyncSession, tmp_path: Path, source: str):
    svc = _service(session, tmp_path)
    user, strategy = await _seed(session, source)
    created = await svc.submit(_request(strategy.id), user_id=user.id)
    await session.commit()
    await svc.run(created.backtest_id)
    return await svc.get(created.backtest_id, user_id=user.id)


@pytest.mark.asyncio
async def test_engine_warnings_reach_the_detail_response(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """★양성 — 엔진이 낸 경고가 DB 를 거쳐 응답까지 온다."""
    detail = await _run_and_detail(db_session, tmp_path, _NOISY)

    assert detail.warnings, "엔진 경고가 응답에 도달하지 않았다 (계산되고 버려졌다)"
    assert any("trail_points" in w for w in detail.warnings), (
        f"어떤 경고인지가 남아야 한다: {detail.warnings}"
    )


@pytest.mark.asyncio
async def test_limit_entry_declares_the_live_difference(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """★지정가 진입은 **백테스트와 라이브가 다르다**는 사실을 선언한다.

    말하지 않으면 사용자는 백테스트 곡선을 라이브의 예고로 읽는다. 이 문장이 리포트 ⑨ 로
    나가고, 라이브 차단(`limit_entry_unsupported_live`)과 **같은 사실**을 가리킨다.
    """
    detail = await _run_and_detail(db_session, tmp_path, _LIMIT_ENTRY)

    assert detail.warnings is not None
    assert any("라이브 실행에서는 안전상 해당 진입을 차단합니다" in w for w in detail.warnings), (
        f"지정가 진입의 라이브 차단이 선언되지 않았다: {detail.warnings}"
    )


@pytest.mark.asyncio
async def test_clean_strategy_keeps_warnings_empty(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """★음성 대조 — 경고 없는 전략은 **빈 배열**이다.

    이게 없으면 「항상 뭔가 채워 넣기」로도 위 두 테스트가 통과한다(판별력 0).
    그리고 `[]`(경고 없음)와 `None`(이 컬럼 이전 실행 = 모른다)은 다른 값이다.
    """
    detail = await _run_and_detail(db_session, tmp_path, _CLEAN)

    assert detail.warnings == [], f"깨끗한 전략에 경고가 붙었다: {detail.warnings}"


@pytest.mark.asyncio
async def test_legacy_rows_report_unknown_not_empty(db_session: AsyncSession) -> None:
    """★`None` 과 `[]` 의 구분 — 컬럼 이전 행은 「모른다」로 남는다.

    빈 배열로 backfill 하면 「경고 없이 돌았다」는 **거짓**을 원장에 쓰게 된다.
    과거 실행의 경고는 엔진 상태가 없어 복원할 수 없다.
    """
    from src.backtest.models import Backtest, BacktestStatus

    svc = BacktestService(
        repo=BacktestRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        ohlcv_provider=None,  # type: ignore[arg-type]
        dispatcher=_FakeDispatcher(),
    )
    legacy = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )

    detail = svc._to_detail(legacy)

    assert detail.warnings is None, "컬럼 이전 행은 `[]`(경고 없음)가 아니라 `None`(모른다)이다"


def test_dedupe_keeps_first_seen_order_and_caps_with_a_visible_note() -> None:
    """엔진 경고는 **bar 마다** 쌓인다 — 원장에 그대로 넣으면 응답·화면이 함께 부푼다.

    ★자른 사실을 **말한다.** 조용히 자르면 화면이 「이게 전부」라고 거짓말한다 —
    이 회차가 고치는 병이 정확히 그 침묵이다.
    """
    repeated = ["같은 경고"] * 1000
    assert dedupe_engine_warnings(repeated) == ["같은 경고"]

    # 첫 등장 순서 보존 — 정렬하면 「전략이 무엇을 먼저 했는가」라는 정보가 사라진다.
    assert dedupe_engine_warnings(["b", "a", "b", "c"]) == ["b", "a", "c"]

    many = [f"경고 {i}" for i in range(60)]
    capped = dedupe_engine_warnings(many)
    assert len(capped) == 51
    assert capped[:50] == many[:50]
    assert "10건이 더 있습니다" in capped[-1], f"잘린 사실을 말해야 한다: {capped[-1]}"
