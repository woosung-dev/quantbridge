# `live_session_admin flatten` 의 종료 코드 계약 — [BL-661]
#
# 착수 시점에 `_cmd_flatten` 은 **테스트가 0건**이었다. `_cmd_stop` 이 정확히 같은 이유로
# 프로덕션에서 `TypeError` 로 죽은 전례가 있다(`live_session_admin.py:356-359`) — mypy 는
# `src/` 만 보고 `scripts/` 는 안 본다.
from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

import scripts.live_session_admin as admin
from src.trading.models import OrderState
from src.trading.schemas import ClosePositionResponse, RestingEntryOrder
from tests.trading.test_close_service import _conditional, _service


def _process_rc(exc: SystemExit) -> int:
    """`SystemExit` → **실제 프로세스 종료 코드**.

    ★`.code` 를 그대로 보면 안 된다. python 규칙은 `None`→0 · `int`→그 값 ·
    **그 밖(문자열 포함)→1**(메시지는 stderr 로 나간다). 실측으로 확인했다:
    `raise SystemExit('message')` → rc **1** / `raise SystemExit(3)` → rc **3**.
    현행 코드가 `raise SystemExit(f"✗ …")` 만 쓰므로(`:143`·`:328`·`:388`)
    이 구분이 없으면 「3 을 의도했는데 1 이 나온」 상태가 초록으로 통과한다.
    """
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


def _resting(order_id: str = "ex-cond-1") -> dict[str, object]:
    return {
        "order_id": order_id,
        "side": "buy",
        "qty": str(Decimal("0.029")),
        "trigger_price": str(Decimal("100")),
        "order_link_id": "link-1",
    }


def _install(monkeypatch: pytest.MonkeyPatch, *, outcome: object) -> None:
    """`_cmd_flatten` 의 바깥 의존을 전부 페이크로 갈아끼운다. 거래소는 치지 않는다."""
    session = SimpleNamespace(commit=AsyncMock())

    @asynccontextmanager
    async def _ctx():
        yield session

    class _SessionMaker:
        def __call__(self):
            return _ctx()

    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(admin, "create_worker_engine_and_sm", lambda: (engine, _SessionMaker()))

    sess = SimpleNamespace(user_id=uuid4(), id=uuid4())

    async def _load(_session: object, _session_id: UUID) -> object:
        return sess

    monkeypatch.setattr(admin, "_load_session", _load)

    async def _close(_user_id: UUID, _session_id: UUID) -> object:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(
        admin, "_build_close_service", lambda _session: SimpleNamespace(close_position=_close)
    )


@pytest.mark.asyncio
async def test_flatten_cli_still_exits_0_when_truly_flat(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """**음성 대조** — 진짜 flat 이면 종전 그대로 ✓ 를 찍고 조용히 0 으로 끝난다.

    이 경로는 멱등이라 성공으로 읽는 것이 **옳다**. [BL-661] 이 고치는 것은
    「조건부가 남았는데도 같은 문장을 찍는 것」이지 이 문장 자체가 아니다.
    """
    _install(monkeypatch, outcome=HTTPException(status_code=409, detail="no_open_position"))

    await admin._cmd_flatten(uuid4())

    assert "이미 flat" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_flatten_cli_exits_3_when_conditionals_rest(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """★[BL-661] 본체 — 조건부가 남아 있으면 **exit 3** 이고 잔량을 찍는다.

    3 은 「일반 실패(1)」와 구분되는 값이어야 한다. runbook §7 rollback 이
    `flatten` → `status` 순서인데, 「조용히 성공」과 「진짜 실패」와 「flat 아님」이
    같은 코드로 오면 자동화가 분기할 수 없다.
    """
    _install(
        monkeypatch,
        outcome=HTTPException(
            status_code=409,
            detail={
                "code": "resting_conditional_entries",
                "count": 2,
                "orders": [_resting("ex-cond-1"), _resting("ex-cond-2")],
            },
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        await admin._cmd_flatten(uuid4())

    assert _process_rc(exc_info.value) == 3
    out = capsys.readouterr().out
    assert "ex-cond-1" in out and "ex-cond-2" in out, "잔존 주문을 눈으로 볼 수 있어야 한다"
    assert "이미 flat" not in out, "조건부가 남았는데 flat 이라고 찍으면 안 된다"


@pytest.mark.asyncio
async def test_flatten_cli_formats_actual_flat_resting_entry_detail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """BL-672 — 서비스가 실제로 낸 detail 객체를 CLI가 그대로 소비한다."""
    service, user_id, session, _ = _service(
        positions=[], conditional_orders=[_conditional("ex-entry-actual")]
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    _install(monkeypatch, outcome=HTTPException(status_code=409, detail=exc_info.value.detail))

    with pytest.raises(SystemExit) as exit_info:
        await admin._cmd_flatten(uuid4())

    assert _process_rc(exit_info.value) == 3
    out = capsys.readouterr().out
    assert "포지션은 없지만 미체결 진입 주문 1건이 남아 있습니다." in out
    assert "ex-entry-actual" in out


@pytest.mark.asyncio
async def test_flatten_cli_exits_1_on_other_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """**음성 대조** — 그 밖의 실패는 종전대로 1 이다. 3 을 남발하면 분기가 무의미해진다."""
    _install(monkeypatch, outcome=HTTPException(status_code=422, detail="live_mode_stub"))

    with pytest.raises(SystemExit) as exc_info:
        await admin._cmd_flatten(uuid4())

    assert _process_rc(exc_info.value) == 1


@pytest.mark.asyncio
async def test_flatten_cli_reports_accepted_order_on_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """**음성 대조** — 포지션이 있으면 종전 청산 경로가 한 글자도 안 바뀐다."""
    order_id = uuid4()
    _install(
        monkeypatch,
        outcome=ClosePositionResponse(order_id=order_id, state=OrderState.pending),
    )

    try:
        await admin._cmd_flatten(uuid4())
    except SystemExit as exc:
        rc = _process_rc(exc)
    else:
        # `_cmd_flatten` 이 정상 반환하면 `asyncio.run()`의 프로세스 종료 코드는 0이다.
        rc = 0

    assert rc == 0
    assert str(order_id) in capsys.readouterr().out


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("entries", "unknown", "expected_marker"),
    [
        ([RestingEntryOrder(**_resting("ex-entry-remaining"))], False, "ex-entry-remaining"),
        ([], True, "미체결 진입 주문 확인 실패"),
    ],
    ids=["entries-remain", "probe-failed"],
)
async def test_flatten_cli_exits_4_when_order_accepted_but_entries_unresolved(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    entries: list[RestingEntryOrder],
    unknown: bool,
    expected_marker: str,
) -> None:
    """BL-684 — 청산 접수 뒤 잔량·확인 실패는 실패 1이 아닌 전용 종료 코드 4다.

    ★두 시나리오를 **한 함수에 이어 붙이지 않는다** — 앞이 죽으면 뒤가 아예 안 돌아
    「둘 다 초록」과 「앞만 돌고 통과」가 구분되지 않는다.
    ★rc 만 재면 부족하다. **원장 검증 안내가 rc 4 경로에서도 살아 있어야** 한다 —
    잔량이 남은 회차가 그 안내를 가장 필요로 하는데, `raise SystemExit(4)` 를 안내보다
    앞에 두면 정확히 그 상황에서만 사라진다(실제로 그렇게 쓰였던 것을 고쳤다).
    """
    order_id = uuid4()
    _install(
        monkeypatch,
        outcome=ClosePositionResponse(
            order_id=order_id,
            state=OrderState.pending,
            resting_entries=entries,
            resting_entries_unknown=unknown,
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        await admin._cmd_flatten(uuid4())

    assert _process_rc(exc_info.value) == 4
    out = capsys.readouterr().out
    assert "청산 주문 접수" in out
    assert str(order_id) in out
    assert expected_marker in out
    assert "★원장에 남았다" in out, "rc 4 경로에서 원장 검증 안내가 사라지면 안 된다"
