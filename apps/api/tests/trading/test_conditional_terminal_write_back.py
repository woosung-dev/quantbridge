"""BL-560 — 확인된 terminal 을 **실제 DB 행에** 기록하는지 검증한다 (mock 아님).

리컨사일러 쪽 테스트는 `OrderRepository` 를 mock 으로 갈아끼우므로 "호출했다" 까지만
증명한다. 이 파일은 그 아래를 real DB 로 받는다 — 조건부 UPDATE 가 정말 행을 뒤집는지,
그리고 **단일행 승자 규약**이 중복 처리를 정말 막는지.

두 파일을 합치면 mock 만 검사하는 구간이 없다:
  리컨사일러(프로덕션 함수) → 헬퍼 호출  [tests/tasks/test_live_signal_conditional_reconcile.py]
  헬퍼 → 실제 행 전이 + 승자 규약        [이 파일]
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks.live_signal import _write_back_confirmed_terminal
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.conditional_entry_planner import build_conditional_entry_key


@pytest.fixture
async def account(db_session: AsyncSession, user) -> ExchangeAccount:
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


async def _submitted_order(
    db_session: AsyncSession, strategy, account
) -> tuple[OrderRepository, Order]:
    """`submitted` 상태의 조건부 진입 1건. 전이 가드가 보는 출발 상태다."""
    repo = OrderRepository(db_session)
    saved = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.029"),
            state=OrderState.pending,
        )
    )
    await repo.transition_to_submitted(saved.id, submitted_at=datetime.now(UTC))
    await repo.commit()
    return repo, saved


def _probe(status: str) -> SimpleNamespace:
    return SimpleNamespace(
        exchange_order_id="9c7aef0b",
        status=status,
        filled_price=Decimal("64000"),
        filled_quantity=Decimal("0.029"),
        raw={},
    )


def _hook_order(order: Order) -> SimpleNamespace:
    """후속 훅이 no-op 이 되는 형태 — 행 전이만 보는 테스트용."""
    return SimpleNamespace(id=order.id, trailing_stop=None, reduce_only=False)


def _trailing_hook_order(order: Order) -> SimpleNamespace:
    """트레일링 의도가 **있는** entry — `_enqueue_trailing_if_intended` 가 실제로 예약한다.

    ★`trailing_stop=None` 픽스처만 쓰면 훅 호출을 통째로 지워도 테스트가 전부 통과한다
    (codex 3차 리뷰가 잡은 거짓 그린). 의도가 있어야 훅이 관측 가능해진다.
    """
    return SimpleNamespace(id=order.id, trailing_stop=Decimal("120"), reduce_only=False)


def _reduce_only_hook_order(order: Order) -> SimpleNamespace:
    """reduce-only 청산 — `_enqueue_closed_pnl_refresh` 가 실제로 예약한다."""
    return SimpleNamespace(id=order.id, trailing_stop=None, reduce_only=True)


def _conditional_hook_order(order: Order) -> SimpleNamespace:
    """조건부 진입 key 를 **실제로** 들고 있는 형태 — BL-562 반전 계측의 통과 조건.

    `_enqueue_conditional_reversal_measure` 는 `parse_live_entry_key` 로 `cond`/`condmkt`
    만 통과시킨다. 임의 문자열을 넣으면 게이트에서 걸려 예약이 안 되고, 그러면 배선을
    지워도 테스트가 통과한다 — instrument 워커가 자기 janitor 테스트에서 밟은 함정이다.
    """
    key = build_conditional_entry_key(
        uuid4(), "entry", datetime(2026, 5, 1, 12, 0, tzinfo=UTC), Decimal("100"), Decimal("1")
    )
    assert key is not None
    return SimpleNamespace(
        id=order.id, trailing_stop=None, reduce_only=False, idempotency_key=key
    )


async def test_confirmed_fill_actually_flips_the_row(db_session, strategy, account) -> None:
    """★거래소가 체결이라고 답한 순간 우리 행도 `filled` 가 된다.

    이게 되기 전에는 `filled_at` 이 스윕까지 비어 있었고, `list_fills_since` 가 읽지
    못해 엔진 원장이 낡은 채로 돌았다 — 그게 `110017 same side` 의 뿌리였다.
    """
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "filled"
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.filled
    assert fetched.exchange_order_id == "9c7aef0b"
    assert fetched.filled_price == Decimal("64000")
    assert fetched.filled_at is not None  # ← 13분 공백을 만들던 바로 그 컬럼


async def test_second_write_back_loses_and_changes_nothing(
    db_session, strategy, account
) -> None:
    """★중복 처리 금지 — 승자 규약을 real SQL 로 확인한다.

    watchdog · WS · 스윕 · 리컨사일러가 같은 주문을 동시에 본다. 두 번째 호출이
    rowcount 0 을 받아 None 을 돌려주지 않으면 gauge 가 두 번 내려가고
    trailing/closed-pnl 훅이 두 번 걸린다.
    """
    repo, order = await _submitted_order(db_session, strategy, account)
    first = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )
    assert first == "filled"
    before = await repo.get_by_id(order.id)
    assert before is not None
    filled_at_before = before.filled_at

    second = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert second is None  # 패자
    after = await repo.get_by_id(order.id)
    assert after is not None
    assert after.filled_at == filled_at_before  # 덮어쓰지도 않았다


async def test_confirmed_reject_flips_the_row_too(db_session, strategy, account) -> None:
    """거절도 기록한다 — 안 하면 그 행이 `submitted` 로 남아 trade_id 가 영구 no-op 이 된다."""
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("rejected"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "rejected"
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.rejected


async def test_unknown_probe_status_writes_nothing(db_session, strategy, account) -> None:
    """★음성 대조군 — terminal 이 아닌 상태는 손대지 않는다."""
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("submitted"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won is None
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.submitted


# ── 체결 후속 훅 (BL-560, codex 3차 리뷰 [6]) ────────────────────────────────
#
# ★write-back 은 "행을 뒤집는 것" 으로 끝나지 않는다. 그 체결이 트레일링 의도 entry 면
# 거래소에 트레일링을 붙여야 하고(무방비 포지션 방지), reduce-only 청산이면 확정 손익을
# 다시 읽어야 한다(kill-switch 입력). 훅 호출을 지워도 통과하던 상태였다.


async def test_fill_enqueues_trailing_when_the_entry_intended_one(
    db_session, strategy, account, monkeypatch
) -> None:
    """★트레일링 의도가 있는 체결은 `place_trailing_stop` 을 실제로 예약한다.

    ★변이 표적 — `live_signal.py` 의 `_enqueue_trailing_if_intended(hook_order)` 를
    지우면 이 단언이 실패해야 한다. 거래소 경계(`apply_async`)만 대체하고 그 위
    프로덕션 경로(`_write_back_confirmed_terminal` → `_enqueue_trailing_if_intended`)는
    그대로 지나간다.
    """
    import src.tasks.trading as trading_module

    enqueued: list[list[str]] = []
    monkeypatch.setattr(
        trading_module.place_trailing_stop_task,
        "apply_async",
        lambda *_a, **kw: enqueued.append(kw["args"]),
    )
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_trailing_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "filled"
    assert enqueued == [[str(order.id)]]


async def test_fill_enqueues_closed_pnl_refresh_for_reduce_only(
    db_session, strategy, account, monkeypatch
) -> None:
    """★reduce-only 체결은 확정 손익 재조회를 실제로 예약한다 (kill-switch 입력).

    ★변이 표적 — `_enqueue_closed_pnl_refresh(hook_order)` 를 지우면 실패해야 한다.
    """
    import src.tasks.trading as trading_module

    enqueued: list[list[str]] = []
    monkeypatch.setattr(
        trading_module.refresh_closed_pnl_task,
        "apply_async",
        lambda *_a, **kw: enqueued.append(kw["args"]),
    )
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_reduce_only_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "filled"
    assert enqueued == [[str(order.id)]]


async def test_fill_enqueues_reversal_measure_for_a_conditional_entry(
    db_session, strategy, account, monkeypatch
) -> None:
    """★BL-562 반전 계측이 이 경로에서도 예약된다 (stage 통합 충돌 해소분).

    `instrument` 워커가 체결 전이 승자 6곳에 배선했는데, 그중 스윕 자리를 내가
    `_write_back_confirmed_terminal` 로 흡수했고 리컨사일러 자리는 아예 새로 생겼다.
    훅 테이블에 넣지 않으면 그 두 자리가 **조용히 미계측**으로 남는다 — instrument 가
    방금 자기 브랜치에서 잡은 결함을 머지에서 재도입하는 셈이다.

    ★변이 표적 — 훅 테이블에서 `("reversal_measure", ...)` 를 빼면 실패해야 한다.
    """
    import src.tasks.trading as trading_module

    enqueued: list[list[str]] = []
    monkeypatch.setattr(
        trading_module.measure_conditional_reversal_task,
        "apply_async",
        lambda *_a, **kw: enqueued.append(kw["args"]),
    )
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_conditional_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "filled"
    assert enqueued == [[str(order.id)]]


async def test_non_fill_terminal_enqueues_no_hooks(
    db_session, strategy, account, monkeypatch
) -> None:
    """★음성 대조군 — 거절은 체결이 아니므로 훅을 걸지 않는다.

    이게 없으면 위 테스트들이 "terminal 이면 무조건 훅" 이라는 오답도 통과시킨다.
    """
    import src.tasks.trading as trading_module

    enqueued: list[str] = []
    for task, label in (
        (trading_module.place_trailing_stop_task, "trailing"),
        (trading_module.refresh_closed_pnl_task, "closed_pnl"),
        (trading_module.measure_conditional_reversal_task, "reversal_measure"),
    ):
        monkeypatch.setattr(
            task, "apply_async", lambda *_a, _label=label, **_kw: enqueued.append(_label)
        )
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("rejected"),
        hook_order=_conditional_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "rejected"
    assert enqueued == []


async def test_hook_enqueue_failure_does_not_lose_the_committed_transition(
    db_session, strategy, account, monkeypatch
) -> None:
    """★broker 장애가 나도 전이는 살아 있고 호출자는 정상 복귀한다 (codex 3차 [3]).

    전이는 이미 커밋됐으니 되돌릴 수 없다. 여기서 예외를 올리면 호출자의 전역 catch 가
    그 tick 을 통째로 끝내 **리컨사일러의 취소 루프**와 **스윕의 `filled` 계측/로그**까지
    사라진다 — 원장을 앞당긴 대가로 다른 것이 빠지면 순이득이 아니다.

    ★`won == "filled"` 반환이 곧 스윕 계측이 살아남는다는 뜻이다(codex 3차 [5]).
    """
    import src.tasks.trading as trading_module

    def _broker_down(*_a: object, **_kw: object) -> None:
        raise RuntimeError("broker unreachable")

    monkeypatch.setattr(
        trading_module.place_trailing_stop_task, "apply_async", _broker_down
    )
    monkeypatch.setattr(
        trading_module.refresh_closed_pnl_task, "apply_async", _broker_down
    )
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_trailing_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "filled"  # ← 호출자가 계측·로그를 계속 남길 수 있다
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.filled
