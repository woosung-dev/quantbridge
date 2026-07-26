# 라이브 신호의 기본 주문 수량 우선순위와 자본 기준선을 검증한다.
"""BL-479 — 라이브 기본 주문 수량의 회귀 방어.

손계산 오라클.
자본 8192.00 (2^13) · pct 50.0 · 체결가 65536.00 (2^16)
  8192 x 50 / 100 = 4096.00 (2^12)
  4096 / 65536    = 0.0625  (2^-4)

구별표.
현행 버그(미배선)      1.0
free(4096) 를 썼다면   0.03125
Pine initial_capital   0.0762939453125
leverage 2 를 곱했다면 0.125
pct 를 분수로 봤다면   0.000625
/100 을 빠뜨렸다면     6.25
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_live


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    """closes 리스트로 마지막 bar 진입을 검증할 OHLCV를 만든다."""
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=i) for i in range(len(closes))],
            "open": [closes[0], *closes[:-1]],
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


_LAST_BAR_ENTRY_OHLCV = _ohlcv([65535.0, 65535.0, 65535.0, 65535.0, 65536.0])

_MARKET_ENTRY = """//@version=5
strategy("last bar market entry")
if (close > open)
    strategy.entry("L", strategy.long)
"""

_PINE_PERCENT_ENTRY = """//@version=5
strategy(
    "pine percent",
    default_qty_type=strategy.percent_of_equity,
    default_qty_value=25
)
if (close > open)
    strategy.entry("L", strategy.long)
"""

_PINE_CASH_ENTRY = """//@version=5
strategy("pine cash", default_qty_type=strategy.cash, default_qty_value=1024)
if (close > open)
    strategy.entry("L", strategy.long)
"""

_EXPLICIT_QTY_ENTRY = """//@version=5
strategy("explicit qty")
if (close > open)
    strategy.entry("L", strategy.long, qty=0.5)
"""

# 제수 32768 은 의도적 선택 — 8192 / 32768 = 0.25 라 이 파일의 다른 기대값
# (1.0 fallback / 0.0625 / 0.03125 / 0.015625 / 0.5) 과 하나도 겹치지 않는다.
# 8192 로 나누면 정답이 1.0 이 되어 "미배선 fallback" 과 구별이 안 된다.
_STRATEGY_EQUITY_ENTRY = """//@version=5
strategy("strategy equity")
qty = strategy.equity / 32768
if (close > open)
    strategy.entry("L", strategy.long, qty=qty)
"""


def _entry_qty(source: str, **kwargs: float) -> float:
    """마지막 bar의 단일 진입 신호 수량을 반환한다."""
    result = run_live(source, _LAST_BAR_ENTRY_OHLCV, **kwargs)
    assert len(result.signals) == 1
    return result.signals[0].qty


def test_run_live_without_sizing_still_qty_one() -> None:
    """사이징 인자가 없으면 기존 호환 동작인 qty 1.0을 유지한다."""
    assert _entry_qty(_MARKET_ENTRY) == 1.0


def test_run_live_with_equity_and_pct_sizes_position() -> None:
    """8192의 50%를 65536 체결가로 나눈 손계산 결과는 정확히 0.0625다."""
    assert _entry_qty(_MARKET_ENTRY, initial_capital=8192.0, live_position_size_pct=50.0) == 0.0625


def test_run_live_pine_declaration_wins_over_live_pct() -> None:
    """Pine 25% 선언은 Live 50%보다 우선하여 qty 0.03125를 만든다."""
    assert (
        _entry_qty(_PINE_PERCENT_ENTRY, initial_capital=8192.0, live_position_size_pct=50.0)
        == 0.03125
    )


def test_run_live_cash_tier() -> None:
    """Pine cash 1024는 체결가 65536에서 qty 0.015625를 만든다."""
    assert _entry_qty(_PINE_CASH_ENTRY, initial_capital=8192.0) == 0.015625


def test_run_live_pct_without_capital_raises() -> None:
    """자본 기준선 없는 Live 퍼센트는 qty 1.0으로 조용히 진행하지 않고 실패한다."""
    with pytest.raises(ValueError):
        run_live(_MARKET_ENTRY, _LAST_BAR_ENTRY_OHLCV, live_position_size_pct=50.0)


def test_run_live_explicit_qty_literal_unaffected_by_sizing() -> None:
    """명시 리터럴 qty는 사이징을 켜도 덮어쓰지 않아 0.5를 유지한다."""
    assert (
        _entry_qty(
            _EXPLICIT_QTY_ENTRY,
            initial_capital=8192.0,
            live_position_size_pct=50.0,
        )
        == 0.5
    )


def test_run_live_leverage_does_not_multiply_quantity() -> None:
    """BL-186a에 따라 레버리지는 주문 수량이 아닌 증거금·청산가에만 영향을 준다."""
    assert _entry_qty(_MARKET_ENTRY, initial_capital=8192.0, live_position_size_pct=50.0) == 0.0625


def test_run_live_strategy_equity_entry_is_skipped_without_capital() -> None:
    """`strategy.equity` 파생 수량은 자본 기준선이 없으면 진입 자체가 발행되지 않는다.

    `interpreter.py:1322-1326` 이 `running_equity is None` 에 `float("nan")` 을 돌려주고,
    BL-376 chokepoint (`strategy_state.py:592`) 가 non-finite qty 주문을 skip 한다.
    즉 라이브에서 이런 전략은 신호가 0 건이었다 — 화면상 "돌고 있음" 인데 진입이 없다.
    사이징 미배선의 두 번째 얼굴이라 여기 고정한다.
    """
    result = run_live(_STRATEGY_EQUITY_ENTRY, _LAST_BAR_ENTRY_OHLCV)
    assert result.signals == []
    assert any("non-finite qty" in w for w in result.strategy_state_report["warnings"])


def test_run_live_strategy_equity_entry_recovers_with_capital() -> None:
    """자본 기준선을 주면 같은 전략이 손계산값 0.25 로 진입한다 (8192 / 32768)."""
    assert _entry_qty(_STRATEGY_EQUITY_ENTRY, initial_capital=8192.0) == 0.25


_WARMUP_CLOSE_THEN_ENTRY = """//@version=5
strategy("warmup pnl drift")
if (bar_index == 1)
    strategy.entry("A", strategy.long)
if (bar_index == 2)
    strategy.close("A")
if (close > open and bar_index > 2)
    strategy.entry("L", strategy.long)
"""


def test_run_live_qty_drifts_with_warmup_window_KNOWN_LIMITATION() -> None:
    """★알려진 한계 — 같은 마지막 바인데 warmup 창 내용에 따라 수량이 달라진다 (BL-486).

    `configure_sizing` 이 `running_equity = initial_capital` 로 시작하고
    `strategy_state.py:668` 이 청산 손익을 누적하는데, `run_live` 는 warmup replay 라
    그 누적 범위가 **300 바 롤링 창**이다. 세션 나이가 창보다 짧으면 창 누적 = 세션 누적이라
    정확하지만, 넘어가면 오래된 거래가 창 밖으로 밀리며 같은 신호의 수량이 바뀐다.

    이 테스트는 **바람직한 동작을 고정하는 것이 아니라** 그 한계를 조용히 드리프트하지
    못하게 못 박는 것이다. 고치려면 "라이브 사이징의 equity 는 무엇인가"(세션 시작 고정 /
    세션 누적 / 실잔고 추종)를 먼저 정해야 하고, 그건 BL-486 의 결정 사항이다.
    미배선 시절의 `1.0`(모든 상황에서 틀림)보다는 낫지만 아직 완결이 아니다.
    """
    with_close = _ohlcv([100.0, 100.0, 200.0, 65535.0, 65536.0])
    without_close = _ohlcv([65535.0, 65535.0, 65535.0, 65535.0, 65536.0])

    def last_entry_qty(frame: pd.DataFrame) -> float:
        result = run_live(
            _WARMUP_CLOSE_THEN_ENTRY, frame, initial_capital=8192.0, live_position_size_pct=50.0
        )
        entries = [s for s in result.signals if s.action == "entry"]
        assert len(entries) == 1
        return entries[0].qty

    # 창 안 청산(+1600 손익)이 running_equity 를 8192 -> 12288 로 밀어 올린다.
    assert last_entry_qty(with_close) == 0.09375
    # 같은 마지막 바인데 청산이 창 밖이면 스냅샷 그대로다.
    assert last_entry_qty(without_close) == 0.0625
