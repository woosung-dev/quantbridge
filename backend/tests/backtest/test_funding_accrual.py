# C6 funding accrual — 8h 정산 경계 보유 포지션 funding 차감 손계산 oracle + 결측 flag.
"""C6 (정직성 번들 Slice 4) — perp funding accrual 엔진 코어.

grounding: funding 인제스션(trading.funding_rates)은 존재하나 backtest 엔진 경로엔
미배선이었다(`include_funding` 죽은 토글). 본 테스트는 엔진 funding 코어를 손계산
oracle 로 고정한다(circular oracle 회피 — 엔진 실행 없이 RawTrade + ohlcv + funding
직접 구성). 서비스 DB 로딩/거래소 선택/FE 배너 배선은 사용자 체크포인트로 이연.

funding 부호: long 은 rate>0 시 지불(equity↓), short 은 반대.
cost = notional(close*qty) * rate * direction_sign. equity 에서 누적 차감.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.engine.v2_adapter import _compute_equity_curve, _funding_cost_by_bar


def _ohlcv_8h(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01T00:00:00Z", periods=len(closes), freq="8h")
    return pd.DataFrame({"close": closes}, index=idx)


def _long_trade(*, entry_bar: int, exit_bar: int | None, qty: str, entry: str, exit_: str | None) -> RawTrade:
    return RawTrade(
        trade_index=0,
        direction="long",
        status="closed" if exit_bar is not None else "open",
        entry_bar_index=entry_bar,
        exit_bar_index=exit_bar,
        entry_price=Decimal(entry),
        exit_price=Decimal(exit_) if exit_ is not None else None,
        size=Decimal(qty),
        pnl=Decimal("0"),
        return_pct=Decimal("0"),
        fees=Decimal("0"),
    )


def test_funding_two_settlements_hand_oracle() -> None:
    # 3 bars @ 8h, close=[100,110,120]. long qty=1 entry bar0 → exit bar2 (bar0,1 보유).
    # funding settlement: bar0 rate=0.0001, bar1 rate=0.0002.
    #   bar0: 100*1*0.0001*(+1) = 0.01
    #   bar1: 110*1*0.0002*(+1) = 0.022
    #   bar2: 포지션 exit (exit_bar_index=2<=2) → 0
    ohlcv = _ohlcv_8h([100, 110, 120])
    trades = [_long_trade(entry_bar=0, exit_bar=2, qty="1", entry="100", exit_="120")]
    funding = pd.Series(
        [Decimal("0.0001"), Decimal("0.0002")],
        index=pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T08:00:00Z"]),
    )
    costs, incomplete = _funding_cost_by_bar(trades, ohlcv, funding)
    assert costs == [Decimal("0.01"), Decimal("0.022"), Decimal("0")]
    # 보유 구간 [bar0,bar2]=[00:00,16:00] 인데 funding 커버 [00:00,08:00] → 16:00 결측.
    assert incomplete is True


def test_funding_beyond_window_not_attributed_to_last_bar() -> None:
    # 백테스트 window 밖(마지막 bar 시각 초과) 정산은 마지막 bar 에 오귀속 안 됨.
    ohlcv = _ohlcv_8h([100, 110])  # bars @ 00:00, 08:00
    trades = [_long_trade(entry_bar=0, exit_bar=None, qty="1", entry="100", exit_=None)]
    funding = pd.Series(
        [Decimal("0.0001"), Decimal("0.5")],
        index=pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-05T00:00:00Z"]),
    )
    costs, _ = _funding_cost_by_bar(trades, ohlcv, funding)
    # bar0: 100*1*0.0001 = 0.01. 2024-01-05 정산(window 밖)은 무시 — last bar 오귀속 X.
    assert costs == [Decimal("0.01"), Decimal("0")]


def test_funding_short_receives_when_rate_positive() -> None:
    # short 포지션은 rate>0 시 funding 수취 → cost 음수(equity↑).
    ohlcv = _ohlcv_8h([100, 110])
    short = RawTrade(
        trade_index=0, direction="short", status="open",
        entry_bar_index=0, exit_bar_index=None,
        entry_price=Decimal("100"), exit_price=None, size=Decimal("2"),
        pnl=Decimal("0"), return_pct=Decimal("0"), fees=Decimal("0"),
    )
    funding = pd.Series(
        [Decimal("0.001")],
        index=pd.to_datetime(["2024-01-01T00:00:00Z"]),
    )
    costs, _ = _funding_cost_by_bar([short], ohlcv, funding)
    # bar0: 100*2*0.001*(-1) = -0.2 (수취)
    assert costs[0] == Decimal("-0.2")


def test_funding_missing_data_flags_when_no_rates() -> None:
    # 보유 포지션 있는데 funding 데이터 0 → 결측 flag (0 묵살 금지).
    ohlcv = _ohlcv_8h([100, 110])
    trades = [_long_trade(entry_bar=0, exit_bar=1, qty="1", entry="100", exit_="110")]
    empty = pd.Series([], index=pd.to_datetime([]), dtype=object)
    _, incomplete = _funding_cost_by_bar(trades, ohlcv, empty)
    assert incomplete is True


def test_funding_full_coverage_not_incomplete() -> None:
    # funding 이 보유 구간 전체를 포괄하면 결측 아님.
    ohlcv = _ohlcv_8h([100, 110])
    trades = [_long_trade(entry_bar=0, exit_bar=1, qty="1", entry="100", exit_="110")]
    funding = pd.Series(
        [Decimal("0.0001"), Decimal("0.0001")],
        index=pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T08:00:00Z"]),
    )
    _, incomplete = _funding_cost_by_bar(trades, ohlcv, funding)
    assert incomplete is False


def test_equity_curve_funding_none_is_regression_zero() -> None:
    # funding_rates=None → 기존 동작 byte-identical (회귀 0).
    ohlcv = _ohlcv_8h([100, 110, 120])
    trades = [_long_trade(entry_bar=0, exit_bar=2, qty="1", entry="100", exit_="120")]
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")
    base = _compute_equity_curve(trades, ohlcv, cfg)
    with_none = _compute_equity_curve(trades, ohlcv, cfg, funding_rates=None)
    assert list(base) == list(with_none)


def test_equity_curve_funding_reduces_equity() -> None:
    # funding 적용 시 long 보유 equity 가 누적 funding 만큼 감소.
    ohlcv = _ohlcv_8h([100, 110, 120])
    trades = [_long_trade(entry_bar=0, exit_bar=2, qty="1", entry="100", exit_="120")]
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")
    funding = pd.Series(
        [Decimal("0.0001"), Decimal("0.0002")],
        index=pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T08:00:00Z"]),
    )
    base = _compute_equity_curve(trades, ohlcv, cfg)
    funded = _compute_equity_curve(trades, ohlcv, cfg, funding_rates=funding)
    # bar0: -0.01 누적 / bar1: -(0.01+0.022) 누적 / bar2: 동일 누적(추가 정산 없음).
    assert funded.iloc[0] == base.iloc[0] - Decimal("0.01")
    assert funded.iloc[1] == base.iloc[1] - Decimal("0.032")
    assert funded.iloc[2] == base.iloc[2] - Decimal("0.032")
