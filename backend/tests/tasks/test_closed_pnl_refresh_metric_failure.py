"""B1~B7 — `_refresh_closed_pnl_with_session` 의 raw `qb_closed_pnl_backfill_total` 고장 주입 (BL-580).

★**BL-580 이 이 7곳을 뺀 근거를 여기서 판정한다.** 백로그가 적은 문장은 이것이었다 —
「`backfill_exchange_realized_pnl` 이 `realized_pnl_synced_at IS NULL` 을 갖고 있어 재시도가
`already_synced` 로 수렴한다. DB 는 이미 정확하고 귀결은 거짓 알림 1건」.

**그 논거가 적용되는 자리는 7곳 중 :1528 하나뿐이다** (2026-08-03 코드 대조):

- **:1470 · :1474 · :1477 · :1498 · :1505** — 수렴을 만드는 그
  `backfill_exchange_realized_pnl`(`order_repository.py:729`)을 **한 번도 호출하지 않는**
  종결 skip 경로다. 적용될 대상 자체가 없다.
- **:1530(`already_synced`)** 은 수렴이 아니라 **고정점 실패**다 — 재시도해도 같은 줄에서
  다시 던진다.
- **:1528** 만 논거대로다. 단 그 자리도 commit 이 **이미 끝난 뒤**라, 던지면 확정된 backfill 이
  task 실패로 보고된다(사전등록 **H1**).

7곳 공통 귀결은 **H6** — 정상 종결이 task 실패로 오분류돼 `refresh_closed_pnl_task`
(`max_retries=4`)가 재시도한다. 그래서 사이트별 postcondition = **함수가 그 dict 를
「반환」한다**(예외로 승격되지 않는다).

주입은 `.inc` 가 아니라 **`.labels` 를 폭파**시킨다 — 새 라벨 조합이 mmap 을 늘리는 시점이
`.labels()` 이라 `.inc` 만 감싼 반쪽 수리를 통과시키지 않기 위해서다.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.metrics import qb_closed_pnl_backfill_total
from tests.tasks.test_closed_pnl_refresh_commits import (
    _account,
    _order,
    _patch_crypto,
    _sessionmaker,
)


def _explode_labels(calls: list[str]):
    def _labels(*_args: object, **_kwargs: object) -> object:
        calls.append("labels")
        raise OSError("mmap allocation failed")

    return _labels


def _snapshot(value: str = "-4.2"):
    from src.trading.providers import ClosedPnlSnapshot

    return ClosedPnlSnapshot("bybit-close-1", Decimal(value), None, None, None)


def _provider(snapshot: Any = None) -> MagicMock:
    return MagicMock(fetch_closed_pnl=AsyncMock(return_value=snapshot))


@pytest.mark.asyncio
async def test_missing_exchange_order_id_still_returns_terminal_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B1 (`trading.py:1470`) — 거래소 주문번호 없음은 **데이터 이상이지만 종결**이다."""
    import src.tasks.trading as trading_mod

    order = _order()
    order.exchange_order_id = None
    session = MagicMock()
    monkeypatch.setattr(
        trading_mod,
        "OrderRepository",
        lambda _s: MagicMock(get_by_id=AsyncMock(return_value=order)),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=_provider()
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["skipped"] == "no_exchange_order_id"


@pytest.mark.asyncio
async def test_missing_account_still_returns_terminal_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B2 (`trading.py:1474`) — 계정 행이 사라진 경우도 재시도해봐야 달라지지 않는다."""
    import src.tasks.trading as trading_mod

    order = _order()
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    monkeypatch.setattr(
        trading_mod,
        "OrderRepository",
        lambda _s: MagicMock(get_by_id=AsyncMock(return_value=order)),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=_provider()
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["skipped"] == "account_missing"


@pytest.mark.asyncio
async def test_unsupported_exchange_still_returns_terminal_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B3 (`trading.py:1477`) — bybit 아님/leverage 없음은 영구 미지원이다."""
    import src.tasks.trading as trading_mod

    order = _order()
    order.leverage = None
    session = MagicMock()
    session.get = AsyncMock(return_value=_account())
    monkeypatch.setattr(
        trading_mod,
        "OrderRepository",
        lambda _s: MagicMock(get_by_id=AsyncMock(return_value=order)),
    )
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=_provider()
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["skipped"] == "unsupported_exchange"


@pytest.mark.asyncio
async def test_credential_decrypt_failure_still_returns_terminal_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B4 (`trading.py:1498`) — 키 회전 실패.

    ★코드 주석이 「계정 전체가 영향받으므로 metric 으로 **반드시** 표면화한다」고 적어 둔
    자리다. 그 metric 이 던지면 표면화는커녕 종결 자체가 예외로 바뀐다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    session = MagicMock()
    session.get = AsyncMock(return_value=_account())
    monkeypatch.setattr(
        trading_mod,
        "OrderRepository",
        lambda _s: MagicMock(get_by_id=AsyncMock(return_value=order)),
    )
    crypto = MagicMock()
    crypto.decrypt.side_effect = ValueError("key rotated")
    monkeypatch.setattr(trading_mod, "EncryptionService", MagicMock(return_value=crypto))
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=_provider()
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["skipped"] == "decrypt_failed"


@pytest.mark.asyncio
async def test_missing_filled_at_still_returns_terminal_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B5 (`trading.py:1505`) — 체결 시각 없음."""
    import src.tasks.trading as trading_mod

    order = _order()
    order.filled_at = None
    session = MagicMock()
    session.get = AsyncMock(return_value=_account())
    monkeypatch.setattr(
        trading_mod,
        "OrderRepository",
        lambda _s: MagicMock(get_by_id=AsyncMock(return_value=order)),
    )
    _patch_crypto(monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=_provider()
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["skipped"] == "no_filled_at"


@pytest.mark.asyncio
async def test_applied_backfill_is_not_reported_as_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B6 (`trading.py:1528`) — **commit(:1527) 이 이미 끝난 뒤**의 계측 실패.

    확정된 손익 교체가 task 실패로 보고된다(사전등록 **H1**). 백로그의 「`already_synced`
    수렴」 논거가 유일하게 성립하는 자리이기도 하다 — 재시도하면 DB 는 맞다. 그러나
    **거래소 REST 재호출 1회**를 더 하고 라벨은 `applied` 대신 `already_synced` 로 남는다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()
    repos = iter(
        [
            MagicMock(get_by_id=AsyncMock(return_value=order)),
            MagicMock(backfill_exchange_realized_pnl=AsyncMock(return_value=1)),
        ]
    )
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: next(repos))
    _patch_crypto(monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=_provider(_snapshot())
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["applied"] is True
    # 계측 실패 전에 내구화는 이미 끝났다.
    second.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_already_synced_is_not_reported_as_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B7 (`trading.py:1530`) — 조건부 UPDATE 가 진 경우.

    ★여기가 「수렴」의 **고정점**이다. 이 줄이 던지면 재시도해도 같은 줄에서 다시 던져
    영원히 수렴하지 못한다 — 백로그 문장이 정확히 뒤집히는 자리다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()
    repos = iter(
        [
            MagicMock(get_by_id=AsyncMock(return_value=order)),
            MagicMock(backfill_exchange_realized_pnl=AsyncMock(return_value=0)),
        ]
    )
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: next(repos))
    _patch_crypto(monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(qb_closed_pnl_backfill_total, "labels", _explode_labels(calls))

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=_provider(_snapshot("0"))
    )

    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["skipped"] == "already_synced"
    second.commit.assert_not_awaited()
