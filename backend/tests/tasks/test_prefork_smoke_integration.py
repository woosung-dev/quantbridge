"""Sprint 19 BL-085 — Real-asyncpg prefork smoke integration test.

Sprint 18 의 라이브 30/30 evidence 를 CI 자동화로 흡수. `init_worker_loop()` +
task entry point 호출 N 회 연속 → 모두 succeeded (Sprint 17 의 RuntimeError
"different loop" 회귀 차단).

`@pytest.mark.integration` marker — 기본 skip, `pytest --run-integration` 옵션
또는 nightly workflow 에서만 실행. 격리 docker stack (db 5433, redis 6380) 필요.

codex G.0 P1 #2 (Sprint 19) — Safety guards:
1. DB DSN 이 `quantbridge_test` 또는 `*_test` 형태인지 검증 — prod DB hit 차단.
2. `execute_order_task.apply_async` / `fetch_order_status_task.apply_async`
   monkeypatch 로 no-op — scanner 가 stuck order 발견 시 real broker side
   effect 회피.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator

import pytest

from src.tasks import _worker_loop

pytestmark = pytest.mark.integration


def _verify_test_db_dsn() -> str:
    """codex G.0 P1 #2 + G.2 P1 #2 (Sprint 19) — prod DB 보호.

    `TEST_DATABASE_URL` 또는 `DATABASE_URL` 이 test DB 인지 검증. 미명시 또는
    test DB 가 아니면 명시적 fail (silent skip 금지 — codex P2 권고).

    **codex G.2 P1 #2 fix**: 단순 `"_test" in dsn` substring 검사는 username /
    password / host 의 `_test` 에 false-positive 가능 → `make_url().database`
    로 DB 이름 자체 정확 검증.
    """
    from sqlalchemy.engine import make_url

    dsn = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.fail(
            "BL-085 integration test 는 TEST_DATABASE_URL 또는 DATABASE_URL env 명시 필요. "
            "권장: postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge_test"
        )
    try:
        url = make_url(dsn)
    except Exception as exc:
        pytest.fail(f"BL-085: invalid DSN '{dsn}': {exc}")
    db_name = url.database
    if not db_name:
        pytest.fail(
            f"BL-085: DSN '{dsn}' 의 database name 누락. quantbridge_test 명시 필요."
        )
    if not db_name.endswith("_test"):
        pytest.fail(
            f"BL-085: DSN database='{db_name}' 가 '_test' suffix 아님. "
            "prod DB hit 방지 위해 quantbridge_test 또는 *_test 사용 강제."
        )
    return dsn


@pytest.fixture
def _isolated_worker_loop(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """매 test 시작 시 fresh `_WORKER_LOOP` init / 끝 후 shutdown.

    독립 실행 보장 — 다른 test 가 _WORKER_LOOP 미초기화/잔존 영향 회피.

    settings.database_url override — task entry point 가 `settings.database_url`
    참조 (worker container 의 `DATABASE_URL` env 기반). pytest 환경에서 격리
    stack 의 host port (5433) 사용해야 함.
    """
    test_db_url = _verify_test_db_dsn()
    from src.core import config

    # settings.database_url 직접 monkeypatch (settings 는 frozen 가능 — env 우선)
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    monkeypatch.setattr(config.settings, "database_url", test_db_url, raising=False)

    _worker_loop.shutdown_worker_loop()  # 잔존 정리 (idempotent)
    _worker_loop.init_worker_loop()
    yield
    _worker_loop.shutdown_worker_loop()


@pytest.fixture
def _no_op_apply_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """codex G.0 P1 #2 + G.2 P1 #1 — scanner / watchdog / WS reconcile 의 task
    enqueue 차단 (broker side effect 0).

    real DB 의 stuck pending/submitted order 발견 시 `execute_order_task.apply_async`
    / `fetch_order_status_task.apply_async` 가 broker 호출 chain 시작. 추가:
    `reconcile_ws_streams()` 가 stale Bybit account 발견 시
    `run_bybit_private_stream.delay()` 호출 → real WS task enqueue (codex G.2 P1 #1).

    본 test 는 smoke 만 목적이라 모든 enqueue 경로 no-op.
    """
    from src.tasks import trading, websocket_task

    def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(trading.execute_order_task, "apply_async", _noop)
    monkeypatch.setattr(trading.fetch_order_status_task, "apply_async", _noop)
    # codex G.2 P1 #1: reconcile_ws_streams 의 .delay() 도 차단.
    monkeypatch.setattr(websocket_task.run_bybit_private_stream, "delay", _noop)
    monkeypatch.setattr(
        websocket_task.run_bybit_private_stream, "apply_async", _noop
    )


def test_scan_stuck_orders_three_consecutive_invocations_no_loop_error(
    _isolated_worker_loop: None,
    _no_op_apply_async: None,
) -> None:
    """**Sprint 17 잔존 P1 회귀 방어 (Sprint 18 30/30 evidence 의 CI 자동화)**.

    Option C `_WORKER_LOOP.run_until_complete` 가 3회 연속 호출에서도 stale
    loop binding 안 발생 → 모두 succeeded.
    """
    _verify_test_db_dsn()
    from src.tasks.orphan_scanner import scan_stuck_orders_task

    r1 = scan_stuck_orders_task()
    r2 = scan_stuck_orders_task()
    r3 = scan_stuck_orders_task()

    # 결과 키 존재만 검증 (실제 stuck count 는 0 또는 매번 변할 수 있음).
    for r in (r1, r2, r3):
        assert "pending" in r
        assert "submitted" in r
        assert "interrupted" in r


def test_reclaim_stale_three_consecutive_invocations(
    _isolated_worker_loop: None,
) -> None:
    """control task 회귀 — Sprint 17 dev-log 6h/34/34 success 패턴 유지."""
    _verify_test_db_dsn()
    from src.tasks.backtest import reclaim_stale_running_task

    n1 = reclaim_stale_running_task()
    n2 = reclaim_stale_running_task()
    n3 = reclaim_stale_running_task()

    # int 반환만 검증 — 실제 reclaim count 는 환경 의존.
    assert isinstance(n1, int)
    assert isinstance(n2, int)
    assert isinstance(n3, int)


def test_reconcile_ws_streams_three_consecutive_invocations(
    _isolated_worker_loop: None,
    _no_op_apply_async: None,
) -> None:
    """ws_stream reconcile beat 회귀 — Option C 적용 후 3회 연속 success.

    codex G.2 P1 #1: `_no_op_apply_async` 가 `run_bybit_private_stream.delay()`
    차단 — stale Bybit account 발견 시 real WS task enqueue 회피.
    """
    _verify_test_db_dsn()
    from src.tasks.websocket_task import reconcile_ws_streams

    r1 = reconcile_ws_streams()
    r2 = reconcile_ws_streams()
    r3 = reconcile_ws_streams()

    for r in (r1, r2, r3):
        assert "enqueued" in r
        assert "skipped_active" in r
        assert "total" in r


def test_mixed_task_types_within_same_worker_loop(
    _isolated_worker_loop: None,
    _no_op_apply_async: None,
) -> None:
    """**핵심 회귀 방어** — Sprint 18 30/30 evidence 의 미니어처.

    같은 `_WORKER_LOOP` 안에서 scan + reconcile + reclaim 3 task type 인터리브
    실행. Sprint 17 의 fail 패턴 (다른 task body 의 asyncpg state leakage) 차단
    검증.
    """
    _verify_test_db_dsn()
    from src.tasks.backtest import reclaim_stale_running_task
    from src.tasks.orphan_scanner import scan_stuck_orders_task
    from src.tasks.websocket_task import reconcile_ws_streams

    # 9 호출 (3 cycle x 3 type)
    for _ in range(3):
        scan_stuck_orders_task()
        reconcile_ws_streams()
        reclaim_stale_running_task()


def test_worker_loop_persistent_across_invocations(
    _isolated_worker_loop: None,
    _no_op_apply_async: None,
) -> None:
    """`_WORKER_LOOP` 가 task 호출들 사이에 동일 객체 유지 — Option C 핵심 invariant."""
    _verify_test_db_dsn()
    from src.tasks.orphan_scanner import scan_stuck_orders_task

    captured_loops: list[asyncio.AbstractEventLoop] = []

    async def _capture() -> None:
        captured_loops.append(asyncio.get_running_loop())

    # 호출 1: smoke task
    scan_stuck_orders_task()
    # 호출 2: 직접 coroutine 으로 loop 확인
    _worker_loop.run_in_worker_loop(_capture())
    # 호출 3: smoke task 다시
    scan_stuck_orders_task()
    # 호출 4: 다시 capture
    _worker_loop.run_in_worker_loop(_capture())

    assert len(captured_loops) == 2
    assert captured_loops[0] is captured_loops[1], (
        "Option C 위반: _WORKER_LOOP 가 호출 간에 다른 loop 로 교체됨 (Sprint 17 회귀)"
    )
    assert captured_loops[0] is _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]
