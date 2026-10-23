"""코드 PnL 원격 지연·실패가 legacy 확정과 결과 계측을 뒤로 미루지 않는다."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.exceptions import ProviderError
from tests.tasks.test_closed_pnl_sweep import (
    _account,
    _install_repositories,
    _order,
    _sessionmaker,
    _snapshot,
    _State,
)


@pytest.mark.parametrize("failure", [ProviderError("timeout"), RuntimeError("unexpected")])
async def test_legacy_commit_and_metrics_precede_code_rpc_even_when_it_fails(monkeypatch, failure):
    from src.tasks import trading

    account = _account()
    state = _State([account])
    legacy = _order(account.id, "legacy-exit")
    code = _order(account.id, "code-exit")
    code.risk_context = {"role": "close"}
    code.created_at = code.filled_at
    code.submitted_at = None
    state.unsynced_orders = [legacy]
    state.matched_orders = [legacy]
    _install_repositories(monkeypatch, state)
    installed_repo = trading.OrderRepository

    class CandidateRepository(installed_repo):
        async def list_code_pnl_candidates(self, account_id, *, filled_since):
            return [code]

    monkeypatch.setattr(trading, "OrderRepository", CandidateRepository)
    counted = MagicMock()
    monkeypatch.setattr(trading, "_count_safely", counted)
    monkeypatch.setattr(trading, "_alert_new_exchange_exits", AsyncMock(return_value=False))

    async def code_rpc(*_args, **_kwargs):
        # 원장 upsert와 legacy 금액의 두 commit이 모두 끝난 뒤에야 원격 IO에 도달한다.
        assert state.commits == 2
        assert state.backfills == [(legacy.id, legacy.realized_pnl)]
        assert legacy.realized_pnl_synced_at is not None
        assert any(call.kwargs.get("outcome") == "applied" for call in counted.call_args_list)
        raise failure

    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("legacy-exit", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(return_value={}),
        fetch_code_closed_pnl=AsyncMock(side_effect=code_rpc),
    )
    summary = await trading._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )
    provider.fetch_code_closed_pnl.assert_awaited_once()
    assert summary["backfilled"] == 1 and summary["resynced"] == 0
    assert legacy.realized_pnl_synced_at is not None and state.commits == 2
    assert sum(call.kwargs.get("outcome") == "applied" for call in counted.call_args_list) == 1
