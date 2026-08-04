# real_broker 스위트의 안전장치 — DSN 하드가드 · enqueue 차단 · 2층 자기정리.
"""real_broker pytest 플러그인.

`--run-real-broker` 플래그로만 실행되는 실거래소 스위트의 안전장치를 모은다.

기본 동작:
- `pytest` → real_broker marker 테스트 전부 **skip** (deselect 아님 — 스위트에 보여야 한다)
- `pytest --run-real-broker` → 실행. credentials 없으면 `pytest.fail` (명시적 호출 + 키 부재 = 사용자 오류)

★**자격증명 부재의 skip 은 여기서 하지 않는다.** 그건 워크플로 레벨의 책임이다
(`nightly-real-broker.yml` 의 preflight → `has_creds` 게이팅). 두 층이 같은 일을 하면
어느 쪽이 판단했는지 알 수 없어진다 — 여기서는 **명시적으로 불렀는데 키가 없다** 만 다룬다.

## ★가정하면 안 되는 것

`tests/conftest.py` 의 autouse `_force_fixture_provider` 는 **`settings.ohlcv_provider`
하나만** 건드린다(`tests/conftest.py:399-405`). 그것은 OHLCV 조회 경로를 fixture 로
돌릴 뿐 **거래 CCXT 호출을 막지 않는다.** "글로벌 conftest 가 외부 호출을 차단한다" 고
가정하지 마라 — 이 디렉터리의 테스트는 실제로 Bybit 에 붙는다.

## 주의 — 글로벌 conftest 와의 hook 공존

`tests/conftest.py` 에 `pytest_addoption`(`--run-mutations` 등) 과
`pytest_collection_modifyitems` 가 이미 있다. 본 파일은 다른 옵션/마커만 다루므로
pytest hook 체인 상 충돌 없이 병렬 등록된다.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

import pytest

from tests.real_broker import _harness
from tests.real_broker._harness import CleanupTarget

# --------------------------------------------------------------------------
# ★★DSN 하드 가드 — 최상단. 다른 어떤 것보다 먼저 판정한다.
# --------------------------------------------------------------------------


def _effective_test_dsn() -> str:
    """`tests/conftest.py` 와 **같은 우선순위**로 유효 DSN 을 고른다.

    ★우선순위를 그대로 베끼는 것이 중요하다. 두 env 를 각각 검사하면, 슬롯 워크트리처럼
    `DATABASE_URL` 은 개발 DB 를 가리키고 `TEST_DATABASE_URL` 만 `_test` 인 정상 배치에서
    거짓 중단이 난다. 판정 대상은 **실제로 `drop_all` 이 겨냥할 그 DSN 하나**다
    (`tests/conftest.py:263-267`).
    """
    return (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test"
    )


def pytest_configure(config: pytest.Config) -> None:
    """`_test` 가 아닌 DB 를 물고 있으면 **세션을 즉시 끝낸다**.

    근거: `tests/conftest.py` 의 세션 픽스처가 `SQLModel.metadata.drop_all` 을 돌린다.
    `TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 있으면 그것이 개발 DB 를 가리켜
    **개발 DB 테이블이 전부 날아간 전례**가 있다(`AGENTS.md` §BE pytest — env 소싱 의무).

    ★`substring "_test"` 검사가 아니라 `make_url().database` 로 **DB 이름 자체**를 본다 —
    username / password / host 에 `_test` 가 있으면 substring 검사는 통과해 버린다
    (`tests/tasks/test_prefork_smoke_integration.py:30-62` 의 codex G.2 P1 #2 교훈).

    ★`pytest.exit` 이지 `pytest.fail` 이 아니다. 하나의 테스트가 실패하는 것이 아니라
    **세션이 계속되면 안 되는 상황**이다.
    """
    from sqlalchemy.engine import make_url

    dsn = _effective_test_dsn()
    try:
        db_name = make_url(dsn).database
    except Exception as exc:
        pytest.exit(
            f"[real_broker] DSN 파싱 실패 — TEST_DATABASE_URL/DATABASE_URL 확인: {exc}",
            returncode=3,
        )
    if not db_name or not db_name.endswith("_test"):
        pytest.exit(
            "[real_broker] 중단 — 유효 DSN 의 database="
            f"'{db_name}' 가 '_test' 로 끝나지 않는다.\n"
            "  tests/conftest.py 의 세션 픽스처가 이 DB 에 SQLModel.metadata.drop_all 을 "
            "돌린다. 개발 DB 를 물고 있으면 테이블이 전부 날아간다.\n"
            "  해소: `set -a; . backend/.env.local; set +a` 로 TEST_DATABASE_URL 을 export 해라.",
            returncode=3,
        )


# --------------------------------------------------------------------------
# 옵션 · 수집 제어
# --------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """`--run-real-broker` 플래그 등록 (opt-in, default=False)."""
    parser.addoption(
        "--run-real-broker",
        action="store_true",
        default=False,
        help="run tests marked 'real_broker' (requires Bybit Demo credentials)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """`--run-real-broker` 없으면 real_broker marker 아이템에 skip 마커를 **주입**한다.

    ★deselect 가 아니라 skip 이다 — 기본 스위트에서 **수집되고 skipped 로 보고**돼야
    「이 스위트가 존재한다」는 사실이 숫자로 남는다.
    """
    if config.getoption("--run-real-broker"):
        return
    skip_marker = pytest.mark.skip(
        reason="real_broker: requires --run-real-broker flag + Bybit Demo credentials"
    )
    for item in items:
        if "real_broker" in item.keywords:
            item.add_marker(skip_marker)


# --------------------------------------------------------------------------
# 자격증명
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def bybit_demo_test_credentials() -> tuple[str, str]:
    """`BYBIT_DEMO_API_KEY_TEST` / `BYBIT_DEMO_API_SECRET_TEST` 를 읽는다.

    `--run-real-broker` 경로에서만 호출된다. 그 플래그를 **명시적으로** 주고 키가 없는
    것은 사용자 오류이므로 skip 이 아니라 `pytest.fail` 이다.
    """
    key = os.environ.get("BYBIT_DEMO_API_KEY_TEST", "").strip()
    secret = os.environ.get("BYBIT_DEMO_API_SECRET_TEST", "").strip()
    if not key or not secret:
        pytest.fail(
            "real_broker E2E 는 BYBIT_DEMO_API_KEY_TEST + BYBIT_DEMO_API_SECRET_TEST "
            "env 가 필요하다.\n"
            "  CI: repo secret 으로 주입한다 (nightly-real-broker.yml 의 preflight 가 "
            "부재를 먼저 판정하므로, 여기까지 왔다면 워크플로 게이팅이 깨진 것이다).\n"
            "  로컬: backend/.env.local 에 두 값을 넣고 `set -a; . ./.env.local; set +a`.\n"
            "  ★Bybit demo(api-demo.bybit.com)와 testnet(api-testnet.bybit.com)은 별개 "
            "플랫폼이고 키 네임스페이스가 다르다 — demo 키를 발급해라."
        )
    return key, secret


# --------------------------------------------------------------------------
# ★enqueue 차단 — 로컬 워커가 우리 태스크를 실제로 집어간다
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_op_enqueue(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """모든 celery enqueue 경로를 **캡처링 no-op** 으로 만든다.

    ★로컬에는 `quantbridge-worker` 컨테이너가 떠 있고 6380 브로커를 **실제로 소비 중**이다.
    이 fixture 를 빼면 우리 테스트가 **앱(개발) DB 를 보는 워커에게 태스크를 던진다** —
    `_test` DSN 가드를 통과해도 그쪽으로 새어나간다.

    ★`dependencies.py` 를 고치지 않는다. `_CeleryOrderDispatcher` 를 mock 으로 갈아끼우는
    대신 **task 객체의 `.delay` / `.apply_async` 자체**를 패치한다 ⇒ 프로덕션 배선이
    그대로 실행되면서 인자까지 검증할 수 있다(판별력이 오히려 올라간다).

    autouse 다 — 실거래소 스위트에서 이걸 빠뜨릴 여지를 남기지 않는다.

    Returns:
        `{task_name: [(args, kwargs), ...]}` 캡처 원장.
    """
    from src.tasks import conditional_entry_recovery, live_signal, trading, websocket_task

    captured: dict[str, list[Any]] = {}

    def _make(label: str) -> Callable[..., None]:
        captured.setdefault(label, [])

        def _noop(*args: object, **kwargs: object) -> None:
            captured[label].append((args, kwargs))
            return None

        return _noop

    targets: list[tuple[Any, tuple[str, ...]]] = [
        (trading.execute_order_task, ("delay", "apply_async")),
        (trading.fetch_order_status_task, ("delay", "apply_async")),
        (trading.refresh_closed_pnl_task, ("delay", "apply_async")),
        (trading.place_trailing_stop_task, ("delay", "apply_async")),
        (
            conditional_entry_recovery.conditional_entry_recovery_task,
            ("delay", "apply_async"),
        ),
        # `LiveSignalSessionService.deactivate` 가 stop 직후 이걸 enqueue 한다
        # (`live_session_service.py:212-216`) — 자기정리 경로에서 반드시 걸린다.
        (live_signal.sweep_conditional_entries_task, ("delay", "apply_async")),
        (websocket_task.run_bybit_public_ticker_stream, ("delay", "apply_async")),
        (websocket_task.run_bybit_private_stream, ("delay", "apply_async")),
    ]
    for task, methods in targets:
        for method in methods:
            monkeypatch.setattr(task, method, _make(f"{task.name}.{method}"))
    return captured


# --------------------------------------------------------------------------
# 자기정리 — 계층 1 (fixture finalizer)
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def broker_flat_guard() -> Iterator[Callable[..., CleanupTarget]]:
    """청산 대상을 등록하고, 세션 끝에 stop → flatten → verify-flat 을 돌린다.

    ★**진입 주문을 내기 전에 등록해라.** 등록이 주문보다 늦으면 그 사이에 죽은 세션은
    아무도 청산하지 않는다.

    ★`try/finally` 를 쓰지 않는다 — `--timeout-method=thread` 로 timeout 이 떨어지면
    프로세스가 죽어 finally 가 아예 안 돈다. 그래서 등록부는 **모듈 전역**
    (`_harness.REGISTRY`)에 두고, `pytest_sessionfinish` 백스톱이 한 층 더 받는다.

    ★보고와 exit code 는 **여기서 하지 않는다** — 백스톱이 유일한 보고 주체다
    (두 곳이 보고하면 같은 잔여가 두 번 세어진다).
    """

    def _register(
        *,
        account_id: UUID,
        symbol: str,
        live_session_id: UUID,
        account_label: str = "(label unknown)",
    ) -> CleanupTarget:
        return _harness.register(
            CleanupTarget(
                account_id=account_id,
                symbol=symbol,
                live_session_id=live_session_id,
                account_label=account_label,
            )
        )

    yield _register
    _harness.run_cleanup()


# --------------------------------------------------------------------------
# 자기정리 — 계층 2 (백스톱). ★cleanup 실패는 잡은 red 다.
# --------------------------------------------------------------------------


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """계층 1 이 못 돈 잔여를 재시도하고, 남으면 **세션을 red 로 만든다**.

    `pytest_sessionfinish` 는 fixture 상태에 접근할 수 없으므로 `_harness.REGISTRY`
    (모듈 전역)를 읽는다. 계층 1 이 정상 종료했으면 `resolved=True` 라 여기서 할 일이 없다.

    ★**판정 불가 ≠ 이상 없음.** 조회가 실패해 flat 인지 알 수 없는 것도 RESIDUAL 이다.
    ★**테스트가 전부 green 이어도 cleanup 이 실패하면 red 다** — 거래소에 포지션을 남긴 채
    "통과" 라고 보고하는 것이 이 스위트가 낼 수 있는 최악의 거짓말이다.
    """
    results = _harness.run_cleanup()
    if not results:
        return
    if _harness.emit_residual_report(results):
        session.exitstatus = 1
