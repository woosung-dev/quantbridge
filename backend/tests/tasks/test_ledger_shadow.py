# 슬라이스 1 계측의 계약 검증 — **계측은 발주를 바꾸지 않는다** (BL-591 / ADR-022)
"""`_capture_ledger_shadow` / `_record_ledger_shadow` 단위 테스트.

이 스위트가 지키는 계약 셋:

1. ★**계측 실패가 밖으로 새지 않는다.** 원장 조회든 거래소 조회든 실패하면 그 사실을
   `outcome`/`decision` 으로 **기록**하고 정상 반환한다. 던지면 계측이 발주를 막는 것이 되고,
   그것은 이 레포가 H8 로 이름 붙여 온 결함(계측 실패가 집행을 뒤집는다)과 같은 형태다.
2. ★**`probe_failed` 와 `disagree` 가 갈린다.** 섞으면 조회 장애가 발산으로 둔갑한다.
3. ★**`hold_ticks` 는 연속 `disagree` 길이**이고 해소 시 그 길이가 버킷으로 계상된다 —
   관망 상한 계수의 직접 근거다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.strategy.pine_v2.strategy_state import Direction, LedgerSeedLeg
from src.tasks.live_signal import (
    _capture_ledger_shadow,
    _hold_bucket,
    _LedgerShadow,
    _record_ledger_shadow,
)
from src.trading.ledger_position import LedgerPosition

SESSION_ID = UUID("4bf679af-e535-402e-ba8e-8b91cebe3b51")


def _sess() -> Any:
    # ★`deactivated_at` 을 빠뜨리면 `SessionScope.from_live_session` 이 터져 **원장 조회가
    #   먼저 실패**한다. 그러면 "거래소 실패" 테스트가 실제로는 원장 실패를 보게 되어
    #   판별력이 0 이 된다(실측으로 한 번 밟았다).
    return SimpleNamespace(
        id=SESSION_ID,
        symbol="BTC/USDT",
        exchange_account_id=uuid4(),
        strategy_id=uuid4(),
        user_id=uuid4(),
        created_at=datetime(2026, 8, 4, 0, 0, tzinfo=UTC),
        deactivated_at=None,
    )


def _leg(qty: float = 0.03, direction: Direction = "long") -> LedgerSeedLeg:
    return LedgerSeedLeg(trade_id="t1", direction=direction, qty=qty, entry_price=63000.0)


# ── _hold_bucket ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("ticks", "bucket"),
    [(1, "1"), (2, "2"), (3, "3-5"), (5, "3-5"), (6, "6-15"), (15, "6-15"), (16, "16+")],
)
def test_hold_bucket_boundaries(ticks: int, bucket: str) -> None:
    assert _hold_bucket(ticks) == bucket


# ── _record_ledger_shadow — 판정 ────────────────────────────────────


def _shadow(*, derived: LedgerPosition, exchange_qty: Decimal | None) -> _LedgerShadow:
    """슬라이스 1 계측만 보는 테스트용 생성자.

    ★`conditional_fills` 는 ADR-025 의 **집행** 필드라 기본값을 두지 않았다(「모른다」와
    「비었다」를 접지 않기 위해서다). 이 파일은 그 축을 안 보므로 여기서만 `None` 으로 고정한다 —
    프로덕션 기본값을 만들지 않는다.
    """
    return _LedgerShadow(derived=derived, exchange_qty=exchange_qty, conditional_fills=None)


def _record(shadow: _LedgerShadow, *, engine: Decimal | None = None, prev: Any = None) -> dict:
    report: dict[str, Any] = {}
    _record_ledger_shadow(shadow, engine_position=engine, previous_report=prev, report=report)
    return report["_qb_ledger_shadow"]


def test_agree_when_ledger_matches_exchange() -> None:
    shadow = _shadow(
        derived=LedgerPosition(legs=(_leg(),), outcome="open"),
        exchange_qty=Decimal("0.03"),
    )
    assert _record(shadow)["decision"] == "agree"


def test_disagree_when_exchange_is_flat_but_ledger_is_not() -> None:
    shadow = _shadow(
        derived=LedgerPosition(legs=(_leg(),), outcome="open"),
        exchange_qty=Decimal("0"),
    )
    assert _record(shadow)["decision"] == "disagree"


def test_probe_failed_is_not_disagree() -> None:
    """★섞으면 거래소 조회 장애가 발산으로 둔갑한다."""
    shadow = _shadow(derived=LedgerPosition(legs=(_leg(),), outcome="open"), exchange_qty=None)
    assert _record(shadow)["decision"] == "probe_failed"


def test_undecidable_ledger_is_not_agree_even_if_exchange_flat() -> None:
    """★판정 불가를 flat 으로 접으면 「모른다」가 「비었다」로 둔갑한다."""
    shadow = _shadow(
        derived=LedgerPosition(legs=None, outcome="overflow"), exchange_qty=Decimal("0")
    )
    recorded = _record(shadow)
    assert recorded["decision"] == "undecidable"
    assert recorded["outcome"] == "overflow"
    assert recorded["ledger_net"] is None


def test_flat_ledger_and_flat_exchange_agree() -> None:
    shadow = _shadow(derived=LedgerPosition(legs=(), outcome="flat"), exchange_qty=Decimal("0"))
    assert _record(shadow)["decision"] == "agree"


@pytest.mark.parametrize(
    ("engine", "expected"),
    [(None, "unknown"), (Decimal("0"), "true"), (Decimal("0.03"), "false")],
)
def test_engine_flat_label(engine: Decimal | None, expected: str) -> None:
    """★`agree` 만으로는 「주입 가능 tick」을 못 센다 — 주입은 엔진이 flat 일 때만이다."""
    shadow = _shadow(derived=LedgerPosition(legs=(), outcome="flat"), exchange_qty=Decimal("0"))
    assert _record(shadow, engine=engine)["engine_flat"] == expected


# ── hold_ticks — 관망 상한 계수의 근거 ──────────────────────────────


def test_hold_ticks_accumulates_while_disagreeing() -> None:
    shadow = _shadow(
        derived=LedgerPosition(legs=(_leg(),), outcome="open"), exchange_qty=Decimal("0")
    )
    first = _record(shadow)
    assert first["hold_ticks"] == 1
    second = _record(shadow, prev={"_qb_ledger_shadow": first})
    assert second["hold_ticks"] == 2


def test_hold_ticks_resets_when_resolved() -> None:
    disagreeing = _shadow(
        derived=LedgerPosition(legs=(_leg(),), outcome="open"), exchange_qty=Decimal("0")
    )
    agreeing = _shadow(
        derived=LedgerPosition(legs=(_leg(),), outcome="open"), exchange_qty=Decimal("0.03")
    )
    held = _record(disagreeing)
    resolved = _record(agreeing, prev={"_qb_ledger_shadow": held})
    assert resolved["decision"] == "agree"
    assert resolved["hold_ticks"] == 0


def test_hold_ticks_ignores_malformed_previous_report() -> None:
    """이전 상태를 못 읽어도 던지지 않는다 — 계측은 발주를 막지 않는다."""
    shadow = _shadow(
        derived=LedgerPosition(legs=(_leg(),), outcome="open"), exchange_qty=Decimal("0")
    )
    for prev in (None, {}, {"_qb_ledger_shadow": "not-a-dict"}, {"_qb_ledger_shadow": {}}):
        assert _record(shadow, prev=prev)["hold_ticks"] == 1


def test_record_tolerates_non_dict_report() -> None:
    """report 가 dict 가 아니어도 counter 는 오르고 예외는 안 난다."""
    shadow = _shadow(derived=LedgerPosition(legs=(), outcome="flat"), exchange_qty=Decimal("0"))
    _record_ledger_shadow(shadow, engine_position=None, previous_report=None, report=None)


def test_record_none_shadow_is_noop() -> None:
    report: dict[str, Any] = {}
    _record_ledger_shadow(None, engine_position=None, previous_report=None, report=report)
    assert report == {}


# ── _capture_ledger_shadow — 실패 흡수 ──────────────────────────────


def _patch_exchange(monkeypatch: pytest.MonkeyPatch, *, net: Decimal) -> None:
    """거래소 조회를 성공 경로로 고정한다."""
    import src.trading.providers as providers_module
    import src.trading.services.account_service as account_service_module

    provider = MagicMock()
    provider.fetch_open_positions = AsyncMock(
        return_value=[SimpleNamespace(side="long", size=net, position_idx=0)]
    )
    monkeypatch.setattr(providers_module, "BybitFuturesProvider", lambda *a, **k: provider)
    service = MagicMock()
    service.get_credentials_for_order = AsyncMock(return_value=object())
    monkeypatch.setattr(account_service_module, "ExchangeAccountService", lambda *a, **k: service)


@pytest.mark.asyncio
async def test_capture_happy_path_derives_and_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    """★정상 경로. 이게 없으면 실패-흡수 테스트들이 「무엇이 실패하든 통과」로 퇴화한다."""
    import src.trading.repositories.order_repository as order_repo_module

    repo = MagicMock()
    repo.list_fills_since = AsyncMock(return_value=[])
    monkeypatch.setattr(order_repo_module, "OrderRepository", lambda _s: repo)
    _patch_exchange(monkeypatch, net=Decimal("0.03"))

    shadow = await _capture_ledger_shadow(_sess(), session=MagicMock(), account_repo=MagicMock())
    assert shadow.derived.outcome == "no_fills"
    assert shadow.derived.undecidable is False
    assert shadow.exchange_qty == Decimal("0.03")


@pytest.mark.asyncio
async def test_capture_absorbs_ledger_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """★원장 조회가 터져도 던지지 않는다 — `fetch_failed` 로 기록하고 판정 불가가 된다."""
    import src.trading.repositories.order_repository as order_repo_module

    class _Boom:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("ledger down")

    monkeypatch.setattr(order_repo_module, "OrderRepository", _Boom)
    shadow = await _capture_ledger_shadow(_sess(), session=MagicMock(), account_repo=MagicMock())
    assert shadow.derived.outcome == "fetch_failed"
    assert shadow.derived.undecidable is True


@pytest.mark.asyncio
async def test_capture_absorbs_exchange_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """★거래소 조회가 터져도 던지지 않는다 — `exchange_qty=None`(모름) 으로 남는다."""
    import src.trading.repositories.order_repository as order_repo_module
    import src.trading.services.account_service as account_service_module

    repo = MagicMock()
    repo.list_fills_since = AsyncMock(return_value=[])
    monkeypatch.setattr(order_repo_module, "OrderRepository", lambda _s: repo)

    class _BoomService:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("exchange down")

    monkeypatch.setattr(account_service_module, "ExchangeAccountService", _BoomService)
    shadow = await _capture_ledger_shadow(_sess(), session=MagicMock(), account_repo=MagicMock())
    assert shadow.exchange_qty is None
    assert shadow.derived.outcome == "no_fills"
