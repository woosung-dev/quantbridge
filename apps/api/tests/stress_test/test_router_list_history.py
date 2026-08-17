"""[BL-414] GET /stress-tests?backtest_id= — 한 백테스트의 이력을 실 DB 로 재는 회귀.

★왜 mock 이 아니라 실 DB 인가. [BL-470] 에서 캐논 감사 9건이 **빈 DB 에서 조용히
통과**했다. "2건 이상일 때 2건이 보인다" 는 2건이 실제로 있는 상태에서만 증거가 된다.
여기서 세우는 것은 그 상태다 — 같은 백테스트에 실행 3건, 다른 백테스트에 1건.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.stress_test.dependencies import get_stress_test_service
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from tests.stress_test.helpers import make_service, seed_user_strategy_backtest


@pytest.mark.asyncio
async def test_list_returns_full_history_for_one_backtest(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user: User,
) -> None:
    _, _, backtest = await seed_user_strategy_backtest(db_session)
    _, _, other_backtest = await seed_user_strategy_backtest(db_session)

    def add(
        backtest_id, kind: StressTestKind, status: StressTestStatus, result: dict | None
    ) -> StressTest:
        st = StressTest(
            id=uuid4(),
            user_id=mock_authed_user.id,
            backtest_id=backtest_id,
            kind=kind,
            status=status,
            params={},
            result=result,
        )
        db_session.add(st)
        return st

    add(
        backtest.id,
        StressTestKind.MONTE_CARLO,
        StressTestStatus.COMPLETED,
        {"max_drawdown_p95": "-0.31"},
    )
    add(backtest.id, StressTestKind.WALK_FORWARD, StressTestStatus.FAILED, None)
    add(backtest.id, StressTestKind.PARAM_STABILITY, StressTestStatus.QUEUED, None)
    # 다른 백테스트의 실행 — 필터가 살아 있으면 응답에 안 들어온다.
    add(
        other_backtest.id,
        StressTestKind.MONTE_CARLO,
        StressTestStatus.COMPLETED,
        {"max_drawdown_p95": "-0.99"},
    )
    await db_session.flush()

    service, _ = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service
    try:
        resp = await client.get(f"/api/v1/stress-tests?backtest_id={backtest.id}")
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3

    by_kind = {item["kind"]: item for item in body["items"]}
    assert set(by_kind) == {"monte_carlo", "walk_forward", "param_stability"}

    # 완료 행은 지표를 갖고, 실패·대기 행은 **키 자체가 null** 이다 (0 이 아니다).
    assert by_kind["monte_carlo"]["headline_metric"] == {
        "key": "max_drawdown_p95",
        "value": "-0.31",
    }
    assert by_kind["walk_forward"]["headline_metric"] is None
    assert by_kind["param_stability"]["headline_metric"] is None
