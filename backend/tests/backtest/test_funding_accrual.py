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

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.engine.v2_adapter import _compute_equity_curve, _funding_cost_by_bar


def _ohlcv_full_8h(closes: list[float]) -> pd.DataFrame:
    """엔진 end-to-end 용 — OHLCV 5컬럼 + tz-aware 8h DatetimeIndex."""
    idx = pd.date_range("2024-01-01T00:00:00Z", periods=len(closes), freq="8h")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        },
        index=idx,
    )


_HODL_SRC = """//@version=5
strategy("HODL")
if bar_index == 1
    strategy.entry("Long", strategy.long)
"""


def test_run_backtest_v2_threads_funding_and_sets_flag() -> None:
    # bar_index==1 진입 후 미청산 → 6 bars(8h) 동안 long 보유. funding 정산 1회(bar2).
    ohlcv = _ohlcv_full_8h([100, 100, 100, 100, 100, 100])
    funding = pd.Series(
        [Decimal("0.001")],
        index=pd.to_datetime(["2024-01-01T16:00:00Z"]),  # bar2
    )
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")

    out_none = run_backtest(_HODL_SRC, ohlcv, cfg)
    out_funded = run_backtest(_HODL_SRC, ohlcv, cfg, funding_rates=funding)

    assert out_none.status == "ok" and out_funded.status == "ok"
    assert out_none.result is not None and out_funded.result is not None
    # 회귀: funding_rates 미전달 → flag None.
    assert out_none.result.metrics.funding_data_incomplete is None
    # 보유 구간[bar1,bar5] 인데 funding 커버 [bar2] 뿐 → 결측 True.
    assert out_funded.result.metrics.funding_data_incomplete is True
    # funding 적용 → long 이 양(+) funding 지불 → 최종 equity 가 None 경로보다 낮음.
    assert out_funded.result.equity_curve.iloc[-1] < out_none.result.equity_curve.iloc[-1]


def test_run_backtest_v2_funding_full_coverage_flag_false() -> None:
    # funding 이 보유 구간 전체(bar1~bar5)를 포괄하면 결측 아님(False).
    ohlcv = _ohlcv_full_8h([100, 100, 100, 100, 100, 100])
    funding = pd.Series(
        [Decimal("0.0001")] * 5,
        index=pd.to_datetime(
            [
                "2024-01-01T08:00:00Z",  # bar1 (entry)
                "2024-01-01T16:00:00Z",  # bar2
                "2024-01-02T00:00:00Z",  # bar3
                "2024-01-02T08:00:00Z",  # bar4
                "2024-01-02T16:00:00Z",  # bar5 (last)
            ]
        ),
    )
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")
    out = run_backtest(_HODL_SRC, ohlcv, cfg, funding_rates=funding)
    assert out.status == "ok" and out.result is not None
    assert out.result.metrics.funding_data_incomplete is False


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


def test_funding_settlement_between_bars_belongs_to_previous_bar() -> None:
    ohlcv = _ohlcv_8h([100, 110, 120])
    trades = [_long_trade(entry_bar=0, exit_bar=None, qty="1", entry="100", exit_=None)]
    funding = pd.Series(
        [Decimal("0.0001")], index=pd.to_datetime(["2024-01-01T04:00:00Z"])
    )

    costs, _ = _funding_cost_by_bar(trades, ohlcv, funding)

    assert costs == [Decimal("0.01"), Decimal("0"), Decimal("0")]


def test_funding_before_first_bar_is_not_attributed() -> None:
    ohlcv = _ohlcv_8h([100, 110])
    trades = [_long_trade(entry_bar=0, exit_bar=None, qty="1", entry="100", exit_=None)]
    funding = pd.Series(
        [Decimal("0.5")], index=pd.to_datetime(["2023-12-31T16:00:00Z"])
    )

    costs, _ = _funding_cost_by_bar(trades, ohlcv, funding)

    assert costs == [Decimal("0"), Decimal("0")]


def test_run_backtest_total_funding_matches_equity_difference() -> None:
    ohlcv = _ohlcv_full_8h([100, 100, 100, 100, 100, 100])
    funding = pd.Series(
        [Decimal("0.0001"), Decimal("0.0002")],
        index=pd.to_datetime(["2024-01-01T16:00:00Z", "2024-01-02T00:00:00Z"]),
    )
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")

    equity_off = run_backtest(_HODL_SRC, ohlcv, cfg)
    equity_on = run_backtest(_HODL_SRC, ohlcv, cfg, funding_rates=funding)

    assert equity_off.result is not None and equity_on.result is not None
    total_funding = equity_on.result.metrics.total_funding
    assert total_funding == Decimal("0.03")
    assert equity_off.result.equity_curve.iloc[-1] - equity_on.result.equity_curve.iloc[-1] == total_funding


def test_empty_funding_with_open_position_reports_zero_total_and_incomplete() -> None:
    ohlcv = _ohlcv_full_8h([100, 100, 100])
    funding = pd.Series([], index=pd.to_datetime([]), dtype=object)
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")

    outcome = run_backtest(_HODL_SRC, ohlcv, cfg, funding_rates=funding)

    assert outcome.result is not None
    assert outcome.result.metrics.total_funding == Decimal("0")
    assert outcome.result.metrics.funding_data_incomplete is True


def test_missing_funding_keeps_metrics_byte_identical_and_total_none() -> None:
    ohlcv = _ohlcv_full_8h([100, 100, 100])
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")

    omitted = run_backtest(_HODL_SRC, ohlcv, cfg)
    explicit_none = run_backtest(_HODL_SRC, ohlcv, cfg, funding_rates=None)

    assert omitted.result is not None and explicit_none.result is not None
    assert omitted.result.metrics == explicit_none.result.metrics
    assert explicit_none.result.metrics.total_funding is None


def test_short_funding_receipt_produces_negative_total() -> None:
    source = """//@version=5
strategy("SHORT")
if bar_index == 1
    strategy.entry("Short", strategy.short)
"""
    ohlcv = _ohlcv_full_8h([100, 100, 100, 100])
    funding = pd.Series(
        [Decimal("0.001")], index=pd.to_datetime(["2024-01-01T16:00:00Z"])
    )
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")

    outcome = run_backtest(source, ohlcv, cfg, funding_rates=funding)

    assert outcome.result is not None
    assert outcome.result.metrics.total_funding == Decimal("-0.1")


def test_precomputed_funding_costs_match_funding_rates_path() -> None:
    ohlcv = _ohlcv_8h([100, 110, 120])
    trades = [_long_trade(entry_bar=0, exit_bar=2, qty="1", entry="100", exit_="120")]
    funding = pd.Series(
        [Decimal("0.0001"), Decimal("0.0002")],
        index=pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T08:00:00Z"]),
    )
    cfg = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="8h")
    costs, _ = _funding_cost_by_bar(trades, ohlcv, funding)

    computed = _compute_equity_curve(trades, ohlcv, cfg, funding_rates=funding)
    precomputed = _compute_equity_curve(trades, ohlcv, cfg, funding_costs=costs)

    assert list(precomputed) == list(computed)
