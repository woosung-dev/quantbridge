# S0 (STOP 해소) — OptimizationRepository 실 DB 회귀: AsyncMock spy 가 못 지키는 SQL 본문 검증
"""OptimizationRepository 실 DB 통합 테스트.

optimizer-deepen S0: repository.py 실측 커버리지 40% (reclaim_stale 만 실 DB 커버,
나머지 8 메서드 본문은 service 테스트의 AsyncMock 으로 대체되어 미실행) → 본 파일이
create / get_by_id / list_by_user / transition_to_running / complete / fail /
commit / rollback 의 SQL 생성 로직을 실 DB (savepoint 격리 db_session) 로 고정한다.

계약 (optimizer-contracts §G):
- list_by_user 반환 = (Sequence, total) 튜플, created_at DESC 정렬, limit/offset 페이징.
- transition_to_running / complete / fail 반환 = rowcount int (조건부 UPDATE race-winner).
- fail 기본 where = status IN (QUEUED, RUNNING) — terminal row 는 건드리지 않음.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.optimizer.models import OptimizationKind, OptimizationRun, OptimizationStatus
from src.optimizer.repository import OptimizationRepository
from tests.stress_test.helpers import seed_user_strategy_backtest


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _make_run(
    user_id: UUID,
    backtest_id: UUID,
    *,
    status: OptimizationStatus = OptimizationStatus.QUEUED,
    created_at: datetime | None = None,
    started_at: datetime | None = None,
) -> OptimizationRun:
    return OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=OptimizationKind.GRID_SEARCH,
        status=status,
        param_space={"schema_version": 1, "parameters": {}},
        created_at=created_at or _utcnow(),
        started_at=started_at,
    )


# --- create / get_by_id ---


@pytest.mark.asyncio
async def test_create_flushes_and_is_readable(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)

    run = await repo.create(_make_run(user.id, backtest.id))

    assert run.id is not None
    loaded = await repo.get_by_id(run.id)
    assert loaded is not None
    assert loaded.status == OptimizationStatus.QUEUED
    assert loaded.param_space == {"schema_version": 1, "parameters": {}}


@pytest.mark.asyncio
async def test_get_by_id_user_filter_blocks_other_user(db_session: AsyncSession) -> None:
    """user_id 필터 분기 — 타 사용자 id 로는 조회 불가 (IDOR 방어 계약)."""
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    run = await repo.create(_make_run(user.id, backtest.id))

    assert await repo.get_by_id(run.id, user_id=user.id) is not None
    assert await repo.get_by_id(run.id, user_id=uuid4()) is None
    # user_id 미지정 = 필터 없음 (worker 경로)
    assert await repo.get_by_id(run.id) is not None


@pytest.mark.asyncio
async def test_get_by_id_missing_returns_none(db_session: AsyncSession) -> None:
    repo = OptimizationRepository(db_session)
    assert await repo.get_by_id(uuid4()) is None


# --- list_by_user ---


@pytest.mark.asyncio
async def test_list_by_user_orders_desc_and_pages(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    base = _utcnow()
    oldest = await repo.create(
        _make_run(user.id, backtest.id, created_at=base - timedelta(minutes=2))
    )
    middle = await repo.create(
        _make_run(user.id, backtest.id, created_at=base - timedelta(minutes=1))
    )
    newest = await repo.create(_make_run(user.id, backtest.id, created_at=base))

    rows, total = await repo.list_by_user(user.id, limit=2, offset=0)
    assert total == 3
    assert [r.id for r in rows] == [newest.id, middle.id]

    rows, total = await repo.list_by_user(user.id, limit=2, offset=2)
    assert total == 3
    assert [r.id for r in rows] == [oldest.id]


@pytest.mark.asyncio
async def test_list_by_user_scopes_to_user_and_backtest(db_session: AsyncSession) -> None:
    """user 스코프 + backtest_id 필터 분기 (count 쿼리 포함 양쪽 적용)."""
    user_a, _, backtest_a = await seed_user_strategy_backtest(db_session)
    user_b, _, backtest_b = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    await repo.create(_make_run(user_a.id, backtest_a.id))
    await repo.create(_make_run(user_a.id, backtest_a.id))
    await repo.create(_make_run(user_b.id, backtest_b.id))

    rows, total = await repo.list_by_user(user_a.id, limit=10, offset=0)
    assert total == 2
    assert {r.user_id for r in rows} == {user_a.id}

    rows, total = await repo.list_by_user(user_a.id, limit=10, offset=0, backtest_id=backtest_a.id)
    assert total == 2
    assert len(rows) == 2

    rows, total = await repo.list_by_user(user_a.id, limit=10, offset=0, backtest_id=uuid4())
    assert total == 0
    assert rows == []


# --- 상태 전이 (조건부 UPDATE race-winner) ---


@pytest.mark.asyncio
async def test_transition_to_running_only_from_queued(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    run = await repo.create(_make_run(user.id, backtest.id))
    started = _utcnow()

    assert await repo.transition_to_running(run.id, started_at=started) == 1
    await db_session.refresh(run)
    assert run.status == OptimizationStatus.RUNNING
    assert run.started_at == started

    # 이미 RUNNING → rowcount 0 (silent skip, race-loser)
    assert await repo.transition_to_running(run.id, started_at=_utcnow()) == 0


@pytest.mark.asyncio
async def test_complete_only_from_running(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    run = await repo.create(_make_run(user.id, backtest.id, status=OptimizationStatus.RUNNING))
    payload = {"kind": "grid_search", "schema_version": 1, "best_cell_index": None}

    assert await repo.complete(run.id, result=payload) == 1
    await db_session.refresh(run)
    assert run.status == OptimizationStatus.COMPLETED
    assert run.result == payload
    assert run.completed_at is not None

    queued = await repo.create(_make_run(user.id, backtest.id))
    assert await repo.complete(queued.id, result=payload) == 0
    await db_session.refresh(queued)
    assert queued.status == OptimizationStatus.QUEUED


@pytest.mark.asyncio
async def test_fail_default_targets_queued_and_running_only(
    db_session: AsyncSession,
) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    queued = await repo.create(_make_run(user.id, backtest.id))
    running = await repo.create(_make_run(user.id, backtest.id, status=OptimizationStatus.RUNNING))
    completed = await repo.create(
        _make_run(user.id, backtest.id, status=OptimizationStatus.COMPLETED)
    )

    assert await repo.fail(queued.id, error_message="boom") == 1
    assert await repo.fail(running.id, error_message="boom") == 1
    # terminal row 보존 — 기본 where = IN (QUEUED, RUNNING)
    assert await repo.fail(completed.id, error_message="boom") == 0

    await db_session.refresh(queued)
    await db_session.refresh(completed)
    assert queued.status == OptimizationStatus.FAILED
    assert queued.error_message == "boom"
    assert queued.completed_at is not None
    assert completed.status == OptimizationStatus.COMPLETED


@pytest.mark.asyncio
async def test_fail_where_status_narrows_transition(db_session: AsyncSession) -> None:
    """where_status 지정 분기 — 지정 상태가 아니면 rowcount 0 + row 무변경."""
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    queued = await repo.create(_make_run(user.id, backtest.id))

    assert (
        await repo.fail(queued.id, error_message="boom", where_status=OptimizationStatus.RUNNING)
        == 0
    )
    await db_session.refresh(queued)
    assert queued.status == OptimizationStatus.QUEUED
    assert queued.error_message is None

    running = await repo.create(_make_run(user.id, backtest.id, status=OptimizationStatus.RUNNING))
    assert (
        await repo.fail(running.id, error_message="boom", where_status=OptimizationStatus.RUNNING)
        == 1
    )


# --- 트랜잭션 helpers ---


@pytest.mark.asyncio
async def test_rollback_discards_uncommitted(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    await db_session.commit()  # seed 를 savepoint 에 고정 (rollback 에 안 쓸려가게)
    repo = OptimizationRepository(db_session)
    run = await repo.create(_make_run(user.id, backtest.id))

    await repo.rollback()

    assert await repo.get_by_id(run.id) is None


@pytest.mark.asyncio
async def test_commit_survives_subsequent_rollback(db_session: AsyncSession) -> None:
    """commit 본문 실행 회귀 — commit 후 rollback 해도 row 잔존 (vacuous 방지).

    적대 리뷰 P2-3: create 는 flush 하므로 commit 없이도 같은 세션 재조회는 성공한다
    — 재조회만으로는 commit 을 검증하지 못함 (mutation probe 실증). savepoint fixture
    에서 commit 유무를 실제로 구별하는 방법 = commit 뒤 rollback 후 재조회
    (commit 이 없었다면 rollback 이 row 를 폐기 — test_rollback_discards_uncommitted
    와 동일 메커니즘의 대우 명제).
    """
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    repo = OptimizationRepository(db_session)
    run = await repo.create(_make_run(user.id, backtest.id))

    await repo.commit()
    await repo.rollback()

    loaded = await repo.get_by_id(run.id)
    assert loaded is not None
    assert loaded.id == run.id
