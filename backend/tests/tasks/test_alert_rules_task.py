# 손실 규칙 beat 태스크의 임계치·throttle·잔고 fallback을 검증한다

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.trading.models import AlertChannel
from src.trading.repositories.order_repository import SessionRealizedPnl


class _Engine:
    async def dispose(self) -> None:
        return None


class _Redis:
    def __init__(self) -> None:
        self.keys: set[bytes] = set()

    async def set(self, key, _value, *, nx=False, ex=None):  # type: ignore[no-untyped-def]
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


def _worker_factory():
    @asynccontextmanager
    async def _ctx():
        yield object()

    class _SM:
        def __call__(self):
            return _ctx()

    return _Engine(), _SM()


def _rule(threshold: str = "10"):
    # SessionScope.from_live_session 이 읽는 필드를 전부 갖춘 가짜 세션.
    # 필드가 빠지면 AttributeError 로 시끄럽게 죽으므로 조용한 통과가 없다.
    live_session = SimpleNamespace(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        created_at=datetime(2026, 7, 20, 6, 0, tzinfo=UTC),
        deactivated_at=None,
    )
    return (
        SimpleNamespace(
            id=uuid4(), threshold_percent=Decimal(threshold), channel=AlertChannel.slack
        ),
        live_session,
    )


def _patch_task(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rule,
    pnl: Decimal,
    balance: Decimal | None = Decimal("100"),
) -> list[dict]:
    import src.tasks.alert_rules as task

    monkeypatch.setattr(task, "create_worker_engine_and_sm", _worker_factory)

    class _Rules:
        def __init__(self, _session) -> None:
            pass

        async def list_active_loss_rules_with_sessions(self):
            return [rule]

    class _Orders:
        def __init__(self, _session) -> None:
            pass

        async def realized_pnl_split_for_session(self, scope):
            # 태스크가 세션 행이 아니라 스코프 값 객체를 넘기는지 여기서 고정한다.
            assert scope.symbol == "BTC/USDT"
            assert scope.ended_at is None
            # BL-458 — 게이트가 쓰는 값은 확정+추정 합계다. 절반씩 나눠 담아
            # 태스크가 `.total` 을 쓰는지(한쪽만 보지 않는지) 고정한다.
            half = Decimal(str(pnl)) / Decimal("2")
            return SessionRealizedPnl(
                confirmed=half,
                estimated=Decimal(str(pnl)) - half,
                confirmed_count=1,
                estimated_count=1,
                unrecorded_count=0,
            )

    class _Accounts:
        def __init__(self, *_args) -> None:
            pass

        async def fetch_balance_usdt(self, _account_id):
            if isinstance(balance, Exception):
                raise balance
            return balance

    calls: list[dict] = []

    async def _send(_settings, **kwargs):
        calls.append(kwargs)
        return {"slack": True}

    monkeypatch.setattr(task, "AlertRuleRepository", _Rules)
    monkeypatch.setattr(task, "OrderRepository", _Orders)
    monkeypatch.setattr(task, "ExchangeAccountService", _Accounts)
    monkeypatch.setattr(task, "send_rule_alert", _send)
    return calls


@pytest.mark.asyncio
async def test_loss_rule_fires_at_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.alert_rules as task

    calls = _patch_task(monkeypatch, rule=_rule(), pnl=Decimal("-10"))
    monkeypatch.setattr(task, "_get_redis_lock_pool_for_alert", _Redis)
    assert await task._async_evaluate_loss_rules() == {"evaluated": 1, "fired": 1}
    # BL-444 — 스코프가 바뀌었으므로 사용자가 읽는 문구도 함께 바뀌어야 한다.
    assert "전략·계정·심볼" in calls[0]["message"]
    # BL-458 — 신뢰 등급이 본문에 드러나야 한다. 어휘는 FE 블로터 칩과 같은 두 단어다.
    assert "거래소 확정" in calls[0]["message"]
    assert "추정" in calls[0]["message"]
    context = calls[0]["context"]
    # ★기존 6 키는 기계 판독용이라 하나도 사라지면 안 된다. 신규 키를 더하면서
    # 기존 키를 흘리는 회귀가 조용히 통과하지 못하게 전수로 고정한다.
    assert set(context) == {
        "rule_id",
        "session_id",
        "total_realized_pnl",
        "loss_percent",
        "threshold_percent",
        "scope",
        "confirmed_realized_pnl",
        "estimated_realized_pnl",
        "confirmed_count",
        "estimated_count",
        "unrecorded_count",
    }
    assert context["scope"] == (
        "session strategy+account+symbol, filled_at within session window"
    )
    # 소계 합이 게이트가 쓴 합계와 같아야 한다 — 라벨은 가산적이다.
    assert Decimal(context["confirmed_realized_pnl"]) + Decimal(
        context["estimated_realized_pnl"]
    ) == Decimal(context["total_realized_pnl"])


@pytest.mark.asyncio
async def test_loss_rule_does_not_fire_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.alert_rules as task

    calls = _patch_task(monkeypatch, rule=_rule(), pnl=Decimal("-9"))
    monkeypatch.setattr(task, "_get_redis_lock_pool_for_alert", _Redis)
    assert await task._async_evaluate_loss_rules() == {"evaluated": 1, "fired": 0}
    assert calls == []


@pytest.mark.asyncio
async def test_loss_rule_second_evaluation_is_throttled(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.alert_rules as task

    calls = _patch_task(monkeypatch, rule=_rule(), pnl=Decimal("-10"))
    pool = _Redis()
    monkeypatch.setattr(task, "_get_redis_lock_pool_for_alert", lambda: pool)
    await task._async_evaluate_loss_rules()
    assert (await task._async_evaluate_loss_rules())["fired"] == 0
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_loss_rule_uses_config_capital_when_balance_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.alert_rules as task

    calls = _patch_task(
        monkeypatch,
        rule=_rule("0.01"),
        pnl=Decimal("-10"),
        balance=RuntimeError("provider unavailable"),
    )
    monkeypatch.setattr(task, "_get_redis_lock_pool_for_alert", _Redis)
    await task._async_evaluate_loss_rules()
    assert calls, "balance failure must use configured capital fallback rather than skip"
