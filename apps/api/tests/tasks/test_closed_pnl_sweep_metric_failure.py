"""B10~B15 — `_sweep_closed_pnl_with_session` 의 raw `qb_closed_pnl_backfill_total` 고장 주입 (BL-580).

★**이 6곳은 백로그가 사유를 적어 두지 않은 자리다.** BL-580 표는 `trading.py` 에 대해
`_refresh_closed_pnl_with_session` 7곳만 이름을 댔지만, 같은 파일·같은 metric 의 census
항목은 **15곳**이다. 나머지 8곳(여기 6곳 + `refresh_closed_pnl_task` 2곳)은 어느 문서에도
근거가 없었다. 그래서 함께 잰다.

★★**6곳이 모두 도달 가능한 것은 아니다** — `:1879`/`:1884` 두 분기는 프로덕션에서
**구조적으로 도달 불가**이고(각 테스트 docstring 참조), 아래 하네스가 프로덕션 계약을 깨서
분기를 만든다. **그 둘은 「판정 보류」이며 유해성의 증거가 아니다.** 실측된 유해는 나머지 4곳이다.

★**이 함수의 계정 루프에는 「한 계정이 죽어도 나머지는 처리한다」는 불변식이 있다**
(`test_closed_pnl_sweep.py::test_sweep_isolates_one_account_failure` 가 지킨다). 그런데
그 불변식을 지키는 `except Exception:`(`:2143`)의 **첫 줄 `:2144` 가 같은 metric 의 raw** 다.
계측 API 가 지속 실패하면 handler 자신이 다시 던져 **루프 전체가 중단**된다 — 사전등록 **H4**.

★**주입 모델을 밝힌다.** 판별력은 「계측 API 가 **지속** 실패한다」를 전제로 한다(mmap 할당
실패·디스크 압박은 그런 성질이다). 첫 호출만 실패하고 회복되는 모델이면 `:2144` 가 삼켜
루프가 이어진다 — codex G1 MINOR 지적을 그대로 문서에 남긴다.

★`:2138`/`:2140` 은 `for _ in range(n)` 안이라 **fixture 가 `n == 1` 을 고정해야** 「stub 이
정확히 1회 호출됐다」 규율이 성립한다(codex G1 MAJOR). 아래 두 테스트가 그 조건을 명시한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.common.metrics import qb_closed_pnl_backfill_total
from src.trading.models import ExchangeName
from tests.tasks.test_closed_pnl_sweep import (
    _account,
    _install_repositories,
    _order,
    _sessionmaker,
    _snapshot,
    _State,
)

_NOW = datetime(2026, 7, 25, tzinfo=UTC)


def _explode_labels(calls: list[str]):
    def _labels(*_args: object, **_kwargs: object) -> object:
        calls.append("labels")
        raise OSError("mmap allocation failed")

    return _labels


def _quiet_provider() -> SimpleNamespace:
    return SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[]),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )


@pytest.mark.asyncio
async def test_non_bybit_account_skip_does_not_stop_the_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B10 (`trading.py:1879`) — 미지원 거래소 계정 skip 분기.

    ★★**판정 보류 — 이 분기는 프로덕션에서 구조적으로 도달 불가다** (2026-08-03 codex G6
    BLOCKING, 코드 대조 확인). 계정 목록은
    `ExchangeAccountRepository.list_by_exchange(ExchangeName.bybit)` 가 `WHERE exchange == bybit`
    로 걸러 오므로 `account.exchange != bybit` 는 참이 될 수 없다.
    **아래 하네스는 그 계약을 깨는 fake repo 로 분기를 만든다.**

    ⇒ 이 테스트를 「계측 실패가 실제로 계정 루프를 죽였다」의 증거로 **인용하지 마라.**
    증거 능력은 「이 방어 분기가 언젠가 도달 가능해지면 그때 안전하다」까지다.
    실측된 H4 는 B15(`:2144`)가 담당한다 — 그 자리는 provider 예외로 실제 도달한다.
    """
    import src.tasks.trading as trading_mod

    foreign = _account()
    foreign.exchange = ExchangeName.okx
    state = _State([foreign, _account()])
    _install_repositories(monkeypatch, state)
    provider = _quiet_provider()
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=_NOW
    )

    assert calls, "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert provider.fetch_closed_pnl_window.await_count == 1, (
        "미지원 계정을 건너뛴 뒤 두 번째 계정은 자기 창을 처리해야 한다"
    )
    assert summary["accounts"] == 2


@pytest.mark.asyncio
async def test_unsupported_provider_skip_does_not_stop_the_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B11 (`trading.py:1884`) — provider 미지원 skip 분기.

    ★★**판정 보류 — 도달 불가** (codex G6 BLOCKING). `BybitFuturesProvider` 에는 `__init__`
    자체가 없다(`providers.py`) — 생성자가 `UnsupportedExchangeError` 를 낼 수 없다.
    **아래 하네스는 팩토리를 통째로 갈아끼워 분기를 만든다.** B10 과 같은 인용 제한을 받는다.
    """
    import src.tasks.trading as trading_mod
    from src.trading.exceptions import UnsupportedExchangeError

    state = _State([_account(), _account()])
    _install_repositories(monkeypatch, state)
    attempts: list[int] = []

    def _factory() -> object:
        attempts.append(1)
        raise UnsupportedExchangeError(("bybit", "demo", True))

    monkeypatch.setattr(trading_mod, "BybitFuturesProvider", _factory)
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=None, now=_NOW
    )

    assert calls, "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert len(attempts) == 2, "두 번째 계정도 자기 provider 를 시도해야 한다"
    assert summary["accounts"] == 2


@pytest.mark.asyncio
async def test_malformed_row_skip_still_persists_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B12 (`trading.py:1967`) — 적재 불가 행 하나가 그 계정의 원장 적재 전체를 날리면 안 된다.

    ★이 자리는 `upsert_rows` + `commit`(`:2037-2039`) **앞**이다. 그래서 사전등록의 H3
    (「내구 쓰기 앞이라 rollback 된다」)이 아니라 **H7** — 되돌릴 전이가 없고, **아직 일어나지
    않은 적재가 통째로 중단된다**(codex G1 BLOCKING#1 로 라벨을 갈랐다).
    코드 자신이 `_order_facts` docstring 에 같은 위험을 적어 뒀다.
    """
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[
                _snapshot("missing-time", created_at_ms=None),
                _snapshot("valid", created_at_ms=1),
            ]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=_NOW
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert summary["inserted"] == 1
    assert [row.exchange_order_id for row in state.rows] == ["valid"]


@pytest.mark.asyncio
async def test_closed_pnl_metric_failure_does_not_escape_and_persists_valid_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """라벨 mmap 실패가 유효한 청산 원장 적재를 멈추지 않는다."""
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[
                _snapshot("missing-time", created_at_ms=None),
                _snapshot("valid", created_at_ms=1),
            ]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=_NOW
    )

    assert calls == ["labels"], "계측 라벨 생성 실패가 실제 보호 지점을 지나야 한다"
    assert summary["inserted"] == 1
    assert [row.exchange_order_id for row in state.rows] == ["valid"]


@pytest.mark.asyncio
async def test_applied_count_failure_does_not_lose_the_new_exit_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B13 (`trading.py:2138`) — commit(:2132) 뒤지만 `_alert_new_exchange_exits`(:2141) **앞**이다.

    ★fixture 가 `applied + resynced == 1` 과 `already_synced == 0` 을 고정한다 —
    `for _ in range(n)` 이라 이 조건에서만 「stub 정확히 1회」가 성립한다.
    """
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    state.unsynced_orders = [_order(account.id, "split-close")]
    _install_repositories(monkeypatch, state)
    alert = AsyncMock(return_value=False)
    monkeypatch.setattr(trading_mod, "_alert_new_exchange_exits", alert)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("split-close", created_at_ms=2, closed_pnl="-0.03")]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=_NOW
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert summary["backfilled"] == 1, "fixture 전제: applied + resynced == 1"
    # 신규 외부 청산 알림이 계측 실패로 사라지면 안 된다.
    alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_already_synced_count_failure_does_not_lose_the_new_exit_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B14 (`trading.py:2140`) — 같은 자리의 `already_synced` 분기.

    ★fixture 가 `already_synced == 1` 과 `applied + resynced == 0` 을 고정한다.
    조건부 UPDATE 가 지도록 `backfill_exchange_realized_pnl` 이 0 을 돌려준다.
    """
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    state.unsynced_orders = [_order(account.id, "split-close")]
    _install_repositories(monkeypatch, state)

    installed_repo = trading_mod.OrderRepository

    class _LosingRepo:
        def __init__(self, session: object) -> None:
            self._inner = installed_repo(session)

        def __getattr__(self, name: str) -> object:
            return getattr(self._inner, name)

        async def backfill_exchange_realized_pnl(self, *_a: object, **_kw: object) -> int:
            return 0  # 조건부 UPDATE 가 졌다 → already_synced

    monkeypatch.setattr(trading_mod, "OrderRepository", _LosingRepo)
    alert = AsyncMock(return_value=False)
    monkeypatch.setattr(trading_mod, "_alert_new_exchange_exits", alert)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("split-close", created_at_ms=2, closed_pnl="-0.03")]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=_NOW
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert summary["backfilled"] == 0, "fixture 전제: applied + resynced == 0"
    alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_account_failure_handler_does_not_stop_the_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B15 (`trading.py:2144`) — 계정 격리를 지키는 `except` 의 **첫 줄**이 raw 계측이다.

    기존 `test_sweep_isolates_one_account_failure` 는 **provider** 예외를 주입하지 계측을
    주입하지 않는다 — 그래서 이 결함을 못 잡는다(codex G1 MAJOR). 여기서 계측을 주입한다.
    """
    import src.tasks.trading as trading_mod

    state = _State([_account(), _account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(side_effect=[RuntimeError("first failed"), []]),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=_NOW
    )

    assert calls, "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert provider.fetch_closed_pnl_window.await_count == 2, (
        "첫 계정이 죽어도 둘째 계정은 자기 창을 처리해야 한다 (계정 격리 불변식)"
    )
    assert summary["accounts"] == 2
