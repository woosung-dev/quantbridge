"""BL-530 — 엔진이 재생하는 봉과 주문이 나가는 상품이 같아야 한다.

세 가지를 잠근다.

1. **오라클** — 같은 스톱 가격에 대해 Bybit 스팟 봉과 무기한선물 봉이 **서로 다른 체결
   판정**을 낸다. 픽스처는 거래소 public REST 원본이므로 판정 기준이 엔진 바깥에서 온다
   (`global.md` §7.3 circular oracle 금지).
2. **회귀** — 라이브 평가 경로가 OHLCV 를 **perp 심볼**로 요청한다. ★반드시 실제
   `_evaluate_session_inner` 를 거쳐야 한다 — 테스트가 변환 함수를 스스로 호출하면
   프로덕션 한 줄을 되돌려도 통과하는 거짓 게이트가 된다.
3. **발산 감지** — 방향 불일치만 세션을 죽이고, 나머지 갈래는 관측만 한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from src.common.metrics import (
    qb_live_position_divergence_total,
    qb_live_signal_divergence_total,
)
from src.strategy.pine_v2.event_loop import LiveSignalResult, run_live
from src.tasks.live_signal import (
    _classify_position_divergence,
    _detect_position_divergence,
    _net_position_size,
    _ohlcv_rows_to_dataframe,
    _to_engine_position,
)
from src.trading.models import ExchangeMode, ExchangeName
from tests.fixtures.bybit_spot_vs_perp_bars import (
    BYBIT_PERP_1M_BARS,
    BYBIT_SPOT_1M_BARS,
    DIVERGENT_STOP_PRICE,
    PERP_WINDOW_HIGH,
    SPOT_WINDOW_HIGH,
)
from tests.tasks.test_live_signal_eval_task import (
    _build_session_obj,
    _patch_inner_dependencies,
    celery_module,
    live_signal_module,
)

# 실제 발산 창에서 시뮬이 걸었던 것과 같은 매수 스톱 하나만 둔다. 다른 진입을 섞으면
# 어느 상품이 체결시켰는지가 흐려진다.
_STOP_ENTRY = f"""//@version=5
strategy("stop entry oracle")
if bar_index == 0
    strategy.entry("PivRevLE", strategy.long, qty=1, stop={DIVERGENT_STOP_PRICE})
"""


def _run_engine(bars: list[list[float]]) -> LiveSignalResult:
    """라이브 경로와 **같은** 변환을 거쳐 엔진에 넣는다."""
    frame = _ohlcv_rows_to_dataframe([list(row) for row in bars])
    assert isinstance(frame, pd.DataFrame)
    return run_live(_STOP_ENTRY, frame)


def _position_counter(category: str) -> float:
    return qb_live_position_divergence_total.labels(category=category)._value.get()


def _blocked_counter(category: str) -> float:
    return qb_live_signal_divergence_total.labels(stage="position", category=category)._value.get()


# ── 1. 오라클 — 거래소 원본 봉이 판정 기준 ────────────────────────────


class TestInstrumentOracle:
    def test_fixture_windows_straddle_the_stop_price(self) -> None:
        """픽스처가 판별력을 갖는지 먼저 확인한다 — 배제 대상이 실제로 들어 있어야 한다."""
        assert max(row[2] for row in BYBIT_SPOT_1M_BARS) == SPOT_WINDOW_HIGH
        assert max(row[2] for row in BYBIT_PERP_1M_BARS) == PERP_WINDOW_HIGH
        # 스톱이 두 창 사이에 놓여야 이 오라클이 무언가를 말한다.
        assert PERP_WINDOW_HIGH < DIVERGENT_STOP_PRICE <= SPOT_WINDOW_HIGH

    def test_spot_bars_open_a_position_the_perp_never_opens(self) -> None:
        """★핵심 — 같은 전략·같은 스톱인데 스팟 봉만 포지션을 연다.

        실측 51건 중 46건(엔진만 포지션을 믿는 갈래)의 발생 기전이 이것이다.
        """
        spot_position = _to_engine_position(_run_engine(BYBIT_SPOT_1M_BARS).strategy_state_report)
        perp_position = _to_engine_position(_run_engine(BYBIT_PERP_1M_BARS).strategy_state_report)

        assert spot_position is not None and perp_position is not None
        assert spot_position > 0, "스팟 봉은 63541.7 을 찍으므로 스톱이 체결돼야 한다"
        assert perp_position == 0, "perp 봉은 63499.4 까지라 스톱에 닿지 않는다"

    def test_the_divergence_is_the_dangerous_class(self) -> None:
        """엔진이 롱을 믿는데 거래소가 숏이면 `direction` — 유일한 fail-closed 대상이다."""
        engine_long = _to_engine_position(_run_engine(BYBIT_SPOT_1M_BARS).strategy_state_report)
        assert engine_long is not None and engine_long > 0

        # 그 창에서 거래소가 실제로 들고 있던 것은 숏이었다(원장 `condmkt sell` 6건).
        assert _classify_position_divergence(engine_long, Decimal("-0.029")) == "direction"
        # 거래소가 flat 이면 close 가 무해하게 거절되는 갈래다.
        assert _classify_position_divergence(engine_long, Decimal("0")) == "engine_only"


# ── 2. 회귀 — 라이브 평가가 실제로 perp 를 요청하는가 ─────────────────


def _strategy_stub(session_obj: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=session_obj.strategy_id,
        settings={"leverage": 1, "margin_mode": "cross", "position_size_pct": 10.0},
        pine_source="//@version=5\nstrategy('x')",
        trading_sessions=[],
    )


async def _run_evaluate(monkeypatch: pytest.MonkeyPatch, *, symbol: str) -> AsyncMock:
    """실제 `_evaluate_session_inner` 를 돌리고 CCXT provider mock 을 돌려준다.

    OHLCV 를 빈 리스트로 두면 fetch 직후 early-return 한다 — 이 테스트가 묻는 것은
    **어떤 심볼로 물었는가** 하나뿐이라 그 뒤 경로를 끌고 올 이유가 없다.
    """
    session_obj = _build_session_obj()
    session_obj.symbol = symbol
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=session_obj)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=_strategy_stub(session_obj))
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )

    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        ohlcv_rows=[],
    )

    # ⚠️ `import src.tasks.celery_app as X` 는 Celery 인스턴스로 평가된다
    # (`src/tasks/__init__.py` 재export). sibling 테스트의 sys.modules 우회를 그대로 쓴다.
    provider = celery_module.get_ccxt_provider_for_worker()
    await live_signal_module._evaluate_session_inner(session_obj.id, "1m")
    return provider


class TestLiveFetchesPerpBars:
    @pytest.mark.asyncio
    async def test_evaluate_requests_perpetual_symbol(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`sess.symbol` 을 그대로 넘기면 스팟 봉이 온다 — perp 로 변환돼야 한다."""
        provider = await _run_evaluate(monkeypatch, symbol="BTC/USDT")

        provider.fetch_ohlcv.assert_awaited_once()
        requested = provider.fetch_ohlcv.await_args.args[0]
        assert requested == "BTC/USDT:USDT", (
            "엔진 봉이 주문 상품과 달라지면 유령 포지션이 생긴다 (BL-530)"
        )

    @pytest.mark.asyncio
    async def test_already_perpetual_symbol_is_idempotent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """이미 perp 형태면 `:USDT` 를 두 번 붙이지 않는다."""
        provider = await _run_evaluate(monkeypatch, symbol="BTC/USDT:USDT")

        assert provider.fetch_ohlcv.await_args.args[0] == "BTC/USDT:USDT"


# ── 3. 발산 감지 ───────────────────────────────────────────────────────


class TestClassifyPositionDivergence:
    """분류 규칙 — 변이(부호 뒤집기 / 허용오차 ∞ / 허용오차 0)를 잡는 지점이다."""

    def test_both_flat_is_not_divergence(self) -> None:
        assert _classify_position_divergence(Decimal("0"), Decimal("0")) is None

    def test_identical_positions_are_not_divergence(self) -> None:
        assert _classify_position_divergence(Decimal("0.029"), Decimal("0.029")) is None

    def test_opposite_sides_are_direction(self) -> None:
        assert _classify_position_divergence(Decimal("0.029"), Decimal("-0.029")) == "direction"
        assert _classify_position_divergence(Decimal("-0.029"), Decimal("0.029")) == "direction"

    def test_engine_only_and_exchange_only_are_distinct(self) -> None:
        assert _classify_position_divergence(Decimal("0.029"), Decimal("0")) == "engine_only"
        assert _classify_position_divergence(Decimal("0"), Decimal("0.029")) == "exchange_only"

    def test_same_side_materially_different_size(self) -> None:
        """부분체결 — 실측 조합(전환 주문 0.001 vs 목표 0.029)."""
        assert _classify_position_divergence(Decimal("0.029"), Decimal("0.001")) == "size"

    def test_quantization_is_not_a_divergence(self) -> None:
        """★정상 상태에서 발화하면 counter 가 아무것도 말하지 않게 된다.

        실측값 그대로 — 엔진은 float 누적, 거래소는 수량 step(0.001) 양자화라
        **의도가 같아도 두 값은 절대 같아지지 않는다.** 정확 비교였다면 매 tick 발화했다.
        """
        engine = Decimal("-0.029910810628287526")  # 실측 `live_signal_states`
        exchange = Decimal("-0.029")  # 실측 거래소 포지션
        assert _classify_position_divergence(engine, exchange) is None

    def test_dust_below_api_quantum_is_flat_not_a_direction(self) -> None:
        """★허용오차 0 변이 검출 — 8자리 아래 잔재를 방향으로 읽으면 과잉차단이다."""
        assert _classify_position_divergence(Decimal("1E-9"), Decimal("-1E-9")) is None

    def test_real_positions_at_the_api_quantum_still_diverge(self) -> None:
        """★허용오차 ∞ 변이 검출 — 주문 가능한 최소 수량은 flat 으로 삼키면 안 된다."""
        assert _classify_position_divergence(Decimal("1E-8"), Decimal("-1E-8")) == "direction"


class TestDetectPositionDivergence:
    """fetch → 순포지션 → 분류 배선이 실제로 이어지는지."""

    @staticmethod
    def _patch_exchange(
        monkeypatch: pytest.MonkeyPatch, *, positions: list[object] | Exception
    ) -> None:
        import src.trading.encryption as encryption_mod
        import src.trading.providers as providers_mod
        import src.trading.services.account_service as account_service_mod

        provider = AsyncMock()
        if isinstance(positions, Exception):
            provider.fetch_open_positions = AsyncMock(side_effect=positions)
        else:
            provider.fetch_open_positions = AsyncMock(return_value=positions)
        monkeypatch.setattr(
            providers_mod, "BybitFuturesProvider", MagicMock(return_value=provider)
        )
        monkeypatch.setattr(encryption_mod, "EncryptionService", MagicMock())
        service = MagicMock()
        service.get_credentials_for_order = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(
            account_service_mod, "ExchangeAccountService", MagicMock(return_value=service)
        )

    @pytest.mark.asyncio
    async def test_opposite_side_is_detected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_exchange(
            monkeypatch, positions=[SimpleNamespace(side="short", size=Decimal("0.029"))]
        )
        sess = SimpleNamespace(id=uuid4(), symbol="BTC/USDT", exchange_account_id=uuid4())

        result = await _detect_position_divergence(
            sess, Decimal("0.029"), account_repo=AsyncMock()
        )
        assert result == "direction"

    @pytest.mark.asyncio
    async def test_probe_failure_is_fail_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """거래소를 못 읽었다는 사실이 세션 사망으로 바뀌면 안 된다."""
        self._patch_exchange(monkeypatch, positions=RuntimeError("bybit down"))
        sess = SimpleNamespace(id=uuid4(), symbol="BTC/USDT", exchange_account_id=uuid4())
        before = _position_counter("probe_failed")

        result = await _detect_position_divergence(
            sess, Decimal("0.029"), account_repo=AsyncMock()
        )

        assert result is None
        assert _position_counter("probe_failed") == before + 1


class TestDivergenceFailClosed:
    """평가 루프의 처분 — 방향만 죽이고 나머지는 관측한다."""

    @staticmethod
    async def _evaluate_with_divergence(
        monkeypatch: pytest.MonkeyPatch,
        *,
        category: str | None,
        position_size: float,
        previously_seen: bool = False,
    ) -> dict[str, object]:
        session_obj = _build_session_obj()
        sess_repo = AsyncMock()
        sess_repo.get_by_id = AsyncMock(return_value=session_obj)
        sess_repo.try_claim_bar = AsyncMock(return_value=True)
        sess_repo.deactivate = AsyncMock(return_value=1)
        sess_repo.commit = AsyncMock()
        sess_repo.get_state = AsyncMock(
            return_value=SimpleNamespace(
                last_strategy_state_report={"_qb_direction_mismatch_seen": previously_seen},
                equity_curve=None,
            )
        )

        strategy_repo = AsyncMock()
        strategy_repo.find_by_id_and_owner = AsyncMock(return_value=_strategy_stub(session_obj))
        account_repo = AsyncMock()
        account_repo.get_by_id = AsyncMock(
            return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
        )
        event_repo = AsyncMock()
        event_repo.list_by_session = AsyncMock(return_value=[])
        event_repo.insert_pending_events = AsyncMock(return_value=[])

        bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
        _patch_inner_dependencies(
            monkeypatch,
            sess_repo=sess_repo,
            event_repo=event_repo,
            account_repo=account_repo,
            strategy_repo=strategy_repo,
            ohlcv_rows=[[int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100]],
            run_live_result=LiveSignalResult(
                last_bar_time=bar_time,
                signals=[],
                strategy_state_report={"open_trades": [], "position_size": position_size},
                total_closed_trades=0,
                total_realized_pnl=Decimal("0"),
            ),
        )
        monkeypatch.setattr(live_signal_module, "publish_realtime", AsyncMock())
        monkeypatch.setattr(
            live_signal_module, "_reconcile_conditional_entries", AsyncMock()
        )
        monkeypatch.setattr(
            live_signal_module,
            "_detect_position_divergence",
            AsyncMock(return_value=category),
        )
        result = await live_signal_module._evaluate_session_inner(session_obj.id, "1m")
        result["_deactivated_calls"] = sess_repo.deactivate.await_count
        return result

    @pytest.mark.asyncio
    async def test_persisted_direction_mismatch_deactivates_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """직전 평가에서도 반대편이었으면 스스로 풀리는 상태가 아니다 — 차단."""
        before = _blocked_counter("direction")

        result = await self._evaluate_with_divergence(
            monkeypatch, category="direction", position_size=0.029, previously_seen=True
        )

        assert result["deactivated"] == "position_divergence"
        assert result["_deactivated_calls"] == 1
        assert _blocked_counter("direction") == before + 1

    @pytest.mark.asyncio
    async def test_first_direction_mismatch_is_not_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """★실측 회귀 — 거래소는 bar 안에서 스톱을 트리거하고 엔진은 bar 종가에만 평가한다.

        2026-07-28 soak: 거래소가 17:46:28 에 롱으로 체결됐는데 엔진이 평가한 bar 는
        17:45 종가라 아직 숏이었다. 초판 가드는 이 **한 bar 짜리 skew** 로 살아 있는
        세션을 죽였다. 첫 관측은 유예해야 한다.
        """
        before_blocked = _blocked_counter("direction")
        before_transient = _position_counter("direction_transient")

        result = await self._evaluate_with_divergence(
            monkeypatch, category="direction", position_size=0.029, previously_seen=False
        )

        assert "deactivated" not in result
        assert result["_deactivated_calls"] == 0
        assert _blocked_counter("direction") == before_blocked
        assert _position_counter("direction_transient") == before_transient + 1

    @pytest.mark.asyncio
    async def test_engine_only_is_observed_but_not_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """★유령 포지션은 close 가 무해하게 거절된다 — 죽이면 상시 사망한다."""
        before = _position_counter("engine_only")

        result = await self._evaluate_with_divergence(
            monkeypatch, category="engine_only", position_size=0.029
        )

        assert "deactivated" not in result
        assert result["_deactivated_calls"] == 0
        assert _position_counter("engine_only") == before + 1


class TestNetPositionSize:
    """reconciler 사이징과 발산 감지가 같은 산술을 쓰는지 잠근다."""

    def test_long_and_short_net_out(self) -> None:
        positions = [
            SimpleNamespace(side="long", size=Decimal("0.03")),
            SimpleNamespace(side="short", size=Decimal("0.01")),
        ]
        assert _net_position_size(positions) == Decimal("0.02")

    def test_empty_is_flat(self) -> None:
        assert _net_position_size([]) == Decimal("0")

    def test_unknown_side_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown position side"):
            _net_position_size([SimpleNamespace(side="sideways", size=Decimal("1"))])
