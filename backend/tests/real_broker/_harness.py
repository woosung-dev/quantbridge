# real_broker 세션이 거래소에 무엇도 남기지 않게 하는 자기정리 하네스.
"""real_broker E2E 자기정리 — 2층 구조 (fixture finalizer + sessionfinish 백스톱).

## 왜 모듈 전역 레지스트리인가

`try/finally` 도 fixture finalizer 도 **프로세스가 죽으면 안 돈다**. pytest-timeout 의
기본 `--timeout-method=thread` 는 정확히 그렇게 죽인다(그래서 워크플로가
`--timeout-method=signal` 을 명시한다 — `tests/test_nightly_workflow_contract.py` 가 감사).
그 위에 `pytest_sessionfinish` 백스톱을 한 층 더 둔다. 그런데 이 훅은 **fixture 상태에
접근할 수 없다**. 그래서 등록부를 모듈 전역에 둔다 — fixture 는 `append` 만 하고,
청산 루틴이 `resolved` 를 세운다.

## 순서 계약 — 주석이 아니라 단언으로

    1. deactivate(user_id, session_id)                      # stop
    2. row = session_repo.get_by_id(session_id)
       assert row.is_active is False                        ← 계약을 기계가 검사
    3. close_position(user_id, session_id)                  # flatten (원장 행만 만든다)
       - HTTPException(409, "no_open_position") → 성공으로 흡수 (멱등)
    3.5 _execute_order_now(order_id)                        # ★거래소까지 실제로 보낸다
    4. assert fetch_open_positions(creds, symbol) == []

★**3.5 를 빼면 이 하네스는 거짓 안전망이다** — `close_position` 은 `Order` 행만 남기고
발주는 `execute_order_task.delay` 가 한다. 자세한 근거는 `_execute_order_now` 참조.

★**세션 비활성화는 아무것도 flat 하지 않는다.** 이 레포가 3회 덴 함정이고
`backend/scripts/live_session_admin.py:36-38` 이 같은 말을 한다. 반대로 `close_position` 은
`is_active` 를 보지 않고 `get_by_id` 만 하므로 **비활성 세션도 청산할 수 있다** —
그래서 `stop` → `flatten` 순서가 성립한다.

## 판정 불가 ≠ 이상 없음

`fetch_open_positions` 가 예외를 던지면 그것은 "flat" 이 아니라 **`undecidable`** 이다.
조회 실패를 「생존」이나 「청산됨」 어느 쪽으로도 수렴시키지 않는다 — 이 레포는 조회
실패를 한쪽으로 수렴시켜 3.7시간을 헛돈 전례가 있다. `flat` 이 아닌 모든 결과는
RESIDUAL 로 보고되고 **세션 exit code 를 1 로 만든다.**

## 배선을 여기서 발명하지 않는다

`ClosePositionService` 조립은 `backend/scripts/live_session_admin.py:_build_close_service`
를 **그대로 재사용**한다. 그쪽은 `src/trading/dependencies.py` 의 조립을 옮겨온 것이며,
dependencies 가 바뀌면 그쪽이 바뀌고 여기도 따라간다.

★**단, DSN 기본값 리터럴은 예외이며 이 파일이 3번째 사본이다** — `tests/conftest.py:263`
· `tests/real_broker/conftest.py` · 본 파일 `_effective_db_url`. 셋이 갈라지면 `drop_all`
이 겨냥하는 DB 와 청산이 쓰는 DB 가 달라진다. 하나로 합치는 것이 옳지만 이번 회차 범위
밖이다 — 갈라졌을 때 어디를 봐야 하는지만 여기 적어 둔다.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

if TYPE_CHECKING:  # pragma: no cover - 타입 전용
    from sqlalchemy.ext.asyncio import AsyncSession

CleanupStatus = Literal["flat", "residual", "undecidable"]


@dataclass(slots=True)
class CleanupTarget:
    """청산해야 할 (계정, 심볼, 세션) 하나. fixture 는 이것을 append 만 한다."""

    account_id: UUID
    symbol: str
    live_session_id: UUID
    account_label: str = "(label unknown)"
    resolved: bool = False


@dataclass(slots=True)
class CleanupResult:
    """한 타깃의 청산 결과. `flat` 이 아닌 모든 것이 RESIDUAL 이다."""

    target: CleanupTarget
    status: CleanupStatus
    detail: str
    positions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_clean(self) -> bool:
        return self.status == "flat"


# ★모듈 전역 — `pytest_sessionfinish` 는 fixture 상태에 접근할 수 없다.
REGISTRY: list[CleanupTarget] = []


def register(target: CleanupTarget) -> CleanupTarget:
    """청산 대상 등록. **진입 주문을 내기 전에** 부르는 것이 계약이다."""
    REGISTRY.append(target)
    return target


# --------------------------------------------------------------------------
# ★celery enqueue 차단 — 청산 구간에서 **직접** 재설치한다
# --------------------------------------------------------------------------

# (모듈 경로, task 심볼). 청산 경로가 실제로 건드리는 것들이다:
#   deactivate            → live_signal.sweep_conditional_entries
#   close_position        → trading.execute_order (dispatcher)
#   _async_execute 체결 후 → trading.fetch_order_status · refresh_closed_pnl ·
#                            measure_conditional_reversal
_ENQUEUE_TARGETS: tuple[tuple[str, str], ...] = (
    ("src.tasks.trading", "execute_order_task"),
    ("src.tasks.trading", "fetch_order_status_task"),
    ("src.tasks.trading", "refresh_closed_pnl_task"),
    ("src.tasks.trading", "place_trailing_stop_task"),
    ("src.tasks.trading", "measure_conditional_reversal_task"),
    ("src.tasks.trading", "cancel_order_task"),
    ("src.tasks.conditional_entry_recovery", "conditional_entry_recovery_task"),
    ("src.tasks.live_signal", "sweep_conditional_entries_task"),
    ("src.tasks.live_signal", "dispatch_live_signal_event_task"),
    ("src.tasks.websocket_task", "run_bybit_public_ticker_stream"),
    ("src.tasks.websocket_task", "run_bybit_private_stream"),
)


@contextlib.contextmanager
def enqueue_block() -> Iterator[dict[str, list[Any]]]:
    """`.delay` / `.apply_async` 를 캡처링 no-op 으로 바꾼다 (진입 시) / 되돌린다 (탈출 시).

    ★★**왜 fixture 가 아니라 여기 있는가.** 이전 판은 function-scope autouse fixture 의
    `monkeypatch` 로만 막았다. 그런데 자기정리는 **session fixture teardown(계층 1)** 과
    **`pytest_sessionfinish`(계층 2)** 에서 도는데, function-scope monkeypatch 는 그
    **둘보다 먼저** 원복된다. 실측(2026-08-04):

        TEST-BODY            execute_order_task=BLOCKED  sweep_conditional_entries=BLOCKED
        LAYER1-fixture       execute_order_task=REAL     sweep_conditional_entries=REAL
        LAYER2-sessionfinish execute_order_task=REAL     sweep_conditional_entries=REAL

    ⇒ 청산이 `deactivate` → `sweep_conditional_entries_task.apply_async` 와
    `close_position` → `execute_order_task.delay` 를 **진짜로 발사**한다. 로컬
    `quantbridge-worker` 는 **앱(개발) DB** 를 보므로 `sweep_conditional_entries` 가
    소크 중인 실세션을 훑는다. 그래서 차단을 `run_cleanup` **안**으로 옮겨,
    누가 부르든(계층 1이든 2든) 청산 구간에는 반드시 걸려 있게 했다.

    ★**복원은 `delattr` 이다** — `monkeypatch` 는 undo 시 클래스에서 찾아둔 bound method 를
    **인스턴스 `__dict__` 에 되쓴다**. 그래서 `'delay' in vars(task)` 로 차단 여부를 재면
    원복 후에도 True 가 나온다(이 함정에 실제로 한 번 속았다). 여기서는 원래 인스턴스
    속성이 없었으면 지워서 클래스 구현이 다시 보이게 한다.

    Returns:
        `{celery_task_name.method: [(args, kwargs), ...]}` 캡처 원장.
    """
    captured: dict[str, list[Any]] = {}
    saved: list[tuple[Any, str, Any, bool]] = []

    def _make(label: str) -> Any:
        captured.setdefault(label, [])

        def _noop(*args: object, **kwargs: object) -> None:
            captured[label].append((args, kwargs))
            return None

        return _noop

    try:
        for module_path, attr in _ENQUEUE_TARGETS:
            task = getattr(importlib.import_module(module_path), attr)
            for method in ("delay", "apply_async"):
                had_own = method in vars(task)
                saved.append((task, method, vars(task).get(method), had_own))
                setattr(task, method, _make(f"{task.name}.{method}"))
        yield captured
    finally:
        for task, method, old, had_own in reversed(saved):
            if had_own:
                setattr(task, method, old)
            else:
                vars(task).pop(method, None)


# --------------------------------------------------------------------------
# 배선 seam — 프로덕션 조립을 지연 import 로 감싼 얇은 함수들.
#   ★이 간접층은 「거래소·DB 없이 순서 계약만 구동」하는 임시 리허설을 위해 뒀다.
#     그 리허설은 **레포에 없다**(일회성으로 돌리고 지웠다 — 5케이스 결과는 PR 본문에
#     인용돼 있다). 즉 여기를 갈아끼우는 코드는 지금 저장소에 존재하지 않는다.
# --------------------------------------------------------------------------


def _open_db() -> Any:
    """(engine, sessionmaker). `create_worker_engine_and_sm` 의 얇은 래퍼."""
    from src.tasks._worker_engine import create_worker_engine_and_sm

    return create_worker_engine_and_sm()


def _build_session_service(db: AsyncSession) -> Any:
    """`live_session_admin._cmd_stop` 과 같은 조립.

    `balance_service` / `user_repo` 는 **등재 경로 전용**이라 `deactivate` 에는 필요 없다.
    안 쓰는 의존성을 억지로 만들지 않는다.
    """
    from src.strategy.repository import StrategyRepository
    from src.trading.repositories.exchange_account_repository import (
        ExchangeAccountRepository,
    )
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )
    from src.trading.services.live_session_service import LiveSignalSessionService

    return LiveSignalSessionService(
        repo=LiveSignalSessionRepository(db),
        account_repo=ExchangeAccountRepository(db),
        strategy_repo=StrategyRepository(db),
        balance_service=None,  # type: ignore[arg-type]
    )


def _build_close_service(db: AsyncSession) -> Any:
    """★`scripts/live_session_admin.py` 의 조립을 **재사용**한다 (SSOT 중복 금지)."""
    from scripts.live_session_admin import _build_close_service as build

    return build(db)


def _build_account_service(db: AsyncSession) -> Any:
    from src.trading.dependencies import (
        get_bybit_futures_provider,
        get_encryption_service,
    )
    from src.trading.repositories.exchange_account_repository import (
        ExchangeAccountRepository,
    )
    from src.trading.services.account_service import ExchangeAccountService

    return ExchangeAccountService(
        repo=ExchangeAccountRepository(db),
        crypto=get_encryption_service(),
        bybit_futures_provider=get_bybit_futures_provider(),
    )


def _provider() -> Any:
    from src.trading.dependencies import get_bybit_futures_provider

    return get_bybit_futures_provider()


def _effective_db_url() -> str:
    """`tests/conftest.py:263-267` 과 같은 우선순위의 유효 테스트 DSN."""
    return (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test"
    )


async def _execute_order_now(order_id: UUID) -> None:
    """청산 주문을 **동기적으로** 거래소에 보낸다.

    ★★**이 함수가 없으면 청산은 원장에만 남고 거래소에는 아무것도 안 간다.**
    `ClosePositionService.close_position` 은 `OrderService.execute` 를 타고, 그 끝의
    `_CeleryOrderDispatcher.dispatch_order_execution` 은 `execute_order_task.delay(...)`
    **뿐**이다(`trading/dependencies.py:134-138`). 즉 발주는 워커의 몫이다. 그런데
    이 스위트에서 그 경로는 **양쪽 환경 모두에서 끊겨 있다**:

    - 로컬: `conftest._no_op_enqueue` 가 `.delay` 를 막는다. 막지 않으면 더 나쁘다 —
      떠 있는 `quantbridge-worker` 는 **앱(개발) DB** 를 보므로 `_test` DB 에 있는 주문
      행을 못 찾고, 우리 태스크만 남의 워커에게 새어나간다.
    - CI(`nightly-real-broker.yml`): celery 워커가 **아예 없다**. 태스크는 redis 에
      영원히 남고 포지션은 그대로다.

    ⇒ 그 구간을 여기서 직접 잇는다. `create_worker_engine_and_sm()` 이
    `settings.database_url` 을 읽으므로(`test_prefork_smoke_integration.py:75-80` 선례)
    호출 동안만 유효 테스트 DSN 으로 맞추고 원복한다.
    """
    from src.core import config
    from src.tasks.trading import _async_execute

    previous = config.settings.database_url
    config.settings.database_url = _effective_db_url()
    try:
        await _async_execute(order_id)
    finally:
        config.settings.database_url = previous


def _session_repo(db: AsyncSession) -> Any:
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )

    return LiveSignalSessionRepository(db)


# --------------------------------------------------------------------------
# 청산 오케스트레이션
# --------------------------------------------------------------------------


async def flatten_one(db: AsyncSession, target: CleanupTarget) -> CleanupResult:
    """한 타깃에 대해 stop → (계약 단언) → flatten → verify-flat 을 수행한다.

    예외를 밖으로 던지지 않는다 — 어떤 실패든 `CleanupResult` 로 **기록**되어야
    나머지 타깃의 청산이 이어진다.
    """
    repo = _session_repo(db)

    row = await repo.get_by_id(target.live_session_id)
    if row is None:
        return CleanupResult(
            target=target,
            status="undecidable",
            detail=f"live session {target.live_session_id} 행이 없다 — 청산 주체를 특정할 수 없다",
        )
    user_id = row.user_id

    # 1. stop
    try:
        await _build_session_service(db).deactivate(user_id, target.live_session_id)
    except Exception as exc:
        return CleanupResult(
            target=target,
            status="undecidable",
            detail=f"deactivate 실패: {type(exc).__name__}: {exc}",
        )

    # 2. 계약을 기계가 검사한다 — 세션이 살아 있으면 다음 tick 에 엔진이 다시 진입한다.
    after = await repo.get_by_id(target.live_session_id)
    if after is None or after.is_active is not False:
        return CleanupResult(
            target=target,
            status="undecidable",
            detail=(
                "stop 이 선행되지 않았다 — is_active="
                f"{None if after is None else after.is_active!r}. "
                "세션이 살아 있는 채로 청산하면 다음 tick 에 엔진이 재진입한다."
            ),
        )

    # 3. flatten — 409 no_open_position 은 성공으로 흡수한다(멱등).
    flatten_detail = "close_position 접수"
    order_id: UUID | None = None
    try:
        response = await _build_close_service(db).close_position(user_id, target.live_session_id)
        await db.commit()
        order_id = getattr(response, "order_id", None)
    except Exception as exc:
        detail = getattr(exc, "detail", None) or str(exc)
        if detail == "no_open_position":
            flatten_detail = "이미 flat (no_open_position)"
        else:
            return CleanupResult(
                target=target,
                status="residual",
                detail=f"close_position 실패: {detail}",
            )

    # 3.5 ★원장에만 남은 청산을 거래소까지 보낸다. 이게 없으면 flat 이 되지 않는다.
    if order_id is not None:
        try:
            await _execute_order_now(order_id)
            flatten_detail = f"close_position 발주 완료 (order_id={order_id})"
        except Exception as exc:
            return CleanupResult(
                target=target,
                status="residual",
                detail=(
                    f"청산 주문 {order_id} 이 원장에 남았지만 거래소 발주가 실패했다: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    # 4. verify-flat. ★조회 실패는 "flat" 이 아니라 "판정 불가" 다.
    try:
        creds = await _build_account_service(db).get_credentials_for_order(target.account_id)
        positions = await _provider().fetch_open_positions(creds, target.symbol)
    except Exception as exc:
        return CleanupResult(
            target=target,
            status="undecidable",
            detail=(
                f"{flatten_detail} / 확인 조회 실패: {type(exc).__name__}: {exc} — "
                "flat 인지 아닌지 판정할 수 없다"
            ),
        )

    if positions:
        return CleanupResult(
            target=target,
            status="residual",
            detail=f"{flatten_detail} / 청산 후에도 포지션이 남아 있다",
            positions=tuple(f"{p.side} {p.size}" for p in positions),
        )

    return CleanupResult(target=target, status="flat", detail=flatten_detail)


async def _cleanup_async(targets: list[CleanupTarget]) -> list[CleanupResult]:
    engine, sm = _open_db()
    results: list[CleanupResult] = []
    try:
        async with sm() as db:
            for target in targets:
                try:
                    result = await flatten_one(db, target)
                except Exception as exc:  # 하네스 자신의 결함도 침묵하지 않는다
                    result = CleanupResult(
                        target=target,
                        status="undecidable",
                        detail=f"청산 루틴 자체가 던졌다: {type(exc).__name__}: {exc}",
                    )
                target.resolved = result.is_clean
                results.append(result)
    finally:
        await engine.dispose()
    return results


def run_cleanup(targets: list[CleanupTarget] | None = None) -> list[CleanupResult]:
    """미해결 타깃을 청산한다. 동기 진입점 (fixture teardown / sessionfinish 공용).

    ★**enqueue 차단을 여기서 직접 건다** — 이 함수를 부르는 두 시점(계층 1 fixture
    finalizer · 계층 2 `pytest_sessionfinish`)에서는 테스트 fixture 의 monkeypatch 가
    **이미 원복돼 있다**. 자세한 근거와 실측은 `enqueue_block` 참조.

    ★DB 조립 자체가 실패해도 던지지 않는다 — 그 실패야말로 RESIDUAL 로 **보고돼야**
    하는 사건이다(청산했는지 알 수 없는 상태로 세션이 끝난다).
    """
    pending = [t for t in (REGISTRY if targets is None else targets) if not t.resolved]
    if not pending:
        return []
    try:
        with enqueue_block():
            return asyncio.run(_cleanup_async(pending))
    except Exception as exc:
        return [
            CleanupResult(
                target=t,
                status="undecidable",
                detail=f"청산 인프라 기동 실패: {type(exc).__name__}: {exc}",
            )
            for t in pending
        ]


# --------------------------------------------------------------------------
# 보고 — 사람이 바로 칠 수 있는 커맨드까지 포함한다
# --------------------------------------------------------------------------


def format_residual_report(results: list[CleanupResult]) -> str:
    """RESIDUAL 블록. `flat` 이 아닌 결과만 담는다."""
    dirty = [r for r in results if not r.is_clean]
    if not dirty:
        return ""

    lines = [
        "",
        "=" * 78,
        f"RESIDUAL — real_broker cleanup 이 flat 을 확인하지 못했다 ({len(dirty)}건)",
        "★이것은 「이상 없음」이 아니다. 거래소에 포지션이 남아 있거나, 남았는지 알 수 없다.",
        "=" * 78,
    ]
    for r in dirty:
        t = r.target
        lines += [
            f"  status          : {r.status}",
            f"  account_label   : {t.account_label}",
            f"  account_id      : {t.account_id}",
            f"  symbol          : {t.symbol}",
            f"  live_session_id : {t.live_session_id}",
            f"  positions       : {', '.join(r.positions) if r.positions else '(조회 결과 없음/판정 불가)'}",
            f"  detail          : {r.detail}",
            "  손으로 처리:",
            "    set -a; . backend/.env.local; set +a; cd backend",
            f"    uv run python scripts/live_session_admin.py stop {t.live_session_id} --confirm",
            f"    uv run python scripts/live_session_admin.py flatten {t.live_session_id} --confirm",
            "    uv run python scripts/live_session_admin.py status",
            "-" * 78,
        ]
    return "\n".join(lines)


def emit_residual_report(results: list[CleanupResult]) -> str:
    """RESIDUAL 을 **세 곳에 동시에** 쓴다. 반환값은 기록한 본문(빈 문자열이면 clean).

    1. `sys.stderr` — `| tee` 로 로그·아티팩트에 남는다
    2. `$GITHUB_STEP_SUMMARY` — 실행 페이지 첫 화면
    3. `::error` 어노테이션 — diff 뷰/체크 목록에 붙는다
    """
    report = format_residual_report(results)
    if not report:
        return ""

    print(report, file=sys.stderr, flush=True)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write("\n### ❌ real_broker residual position\n\n```\n")
                fh.write(report)
                fh.write("\n```\n")
        except OSError as exc:  # 요약을 못 써도 stderr 경로는 살아 있어야 한다
            print(f"[harness] step summary 기록 실패: {exc}", file=sys.stderr)

    for r in (r for r in results if not r.is_clean):
        print(
            f"::error title=real_broker residual position::"
            f"{r.status} account={r.target.account_id} symbol={r.target.symbol} "
            f"session={r.target.live_session_id} — {r.detail}",
            file=sys.stderr,
            flush=True,
        )
    return report
