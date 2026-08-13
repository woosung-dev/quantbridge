# [BL-466] L=1 에서 자본을 초과해 손실한 실행을 리포트가 고지하는지 못 박는다.
"""승인안 **(c) 리포트 고지** 의 오라클 — 동작은 그대로 두고 고지만 검증한다.

[BL-466] 은 L=1 백테스트가 자본을 무제한 음수로 몰 수 있다고 적었다. 뿌리는 셋이
겹친 것이다 — ① `_can_afford_entry` 가 L=1 에서 즉시 True(마진 개념 없음, #480 TV/MT5
컨벤션) ② L=1 에는 강제청산도 없다 ③ 사이징 미선언 시 `compute_qty` 가 1.0 을 돌려줘
큰 명목이 작은 자본 위에서 돈다.

승인안은 (a) 강제 종료도 (b) 명목 상한도 아닌 **(c)** 다. 그래서 이 파일은 두 가지를
동시에 못 박는다.
  · **동작 불변** — 포지션은 강제로 닫히지 않고 자본은 음수로 남는다.
  · **고지** — 리포트가 「자본을 초과해 손실했다」를 True 로 들고 나간다.

★고지 필드는 새로 만들지 않았다. `mdd_exceeds_capital` 이 **이미 정확히 그 술어**다 —
`max_drawdown < -1` 은 running peak 대비이고 peak >= init_cash > 0 이므로
`(equity_min - peak)/peak < -1  ⟺  equity_min < 0` 로 「자본을 넘어선 손실」과 동치다.
같은 뜻의 boolean 을 하나 더 만들면 리포트만 넓어지고 golden/trust-layer baseline 이
정보 없이 움직인다. 그래서 **재사용하고 여기서 L=1 경로를 고정한다** — 종전 오라클
(`test_mdd_leverage_consistency.py`)은 `RawTrade` 를 손조립해 어댑터 내부 함수를 부르므로
이 경로(사이징 미선언 · 실제 Pine 실행)를 한 번도 밟지 않았다.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2

# 사이징을 선언하지 않는다 → compute_qty()=1.0 → 1 계약이 통째로 자본 위에 얹힌다.
UNSIZED_SOURCE = """//@version=5
strategy("bl466 unsized", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
"""


def _falling_ohlcv() -> pd.DataFrame:
    """64,000 에 진입해 5,000 까지 떨어지는 프레임 — 자본 10,000 을 크게 초과 손실."""
    closes = [64000.0, 64000.0, 50000.0, 40000.0, 30000.0, 20000.0, 10000.0, 5000.0]
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="1D", tz="UTC"),
    )


def _flat_ohlcv() -> pd.DataFrame:
    """자본을 넘지 않는 대조군 — 같은 전략, 완만한 가격."""
    closes = [100.0, 100.0, 99.0, 98.0, 99.0, 100.0, 101.0, 100.0]
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="1D", tz="UTC"),
    )


def _run(ohlcv: pd.DataFrame):
    cfg = BacktestConfig(init_cash=Decimal("10000"), leverage=1.0)
    outcome = run_backtest_v2(UNSIZED_SOURCE, ohlcv, config=cfg)
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    return outcome.result


def test_report_discloses_that_the_run_lost_more_than_its_capital() -> None:
    """고지 — L=1 에서도 자본 초과 손실이 리포트 필드로 나간다."""
    result = _run(_falling_ohlcv())

    assert result.metrics.mdd_exceeds_capital is True
    # 고지가 참인 이유를 같은 단언으로 붙든다 — 플래그만 True 면 우연일 수 있다.
    assert min(result.equity_curve) < 0
    assert result.metrics.max_drawdown < Decimal("-1")


def test_behaviour_is_unchanged_no_forced_close_and_no_liquidation() -> None:
    """(c) 의 핵심 — 고치는 것은 리포트뿐이다. (a)/(b) 였다면 여기가 깨진다."""
    result = _run(_falling_ohlcv())

    # (a) 강제 종료가 아니다 — 포지션은 마지막까지 열려 있다.
    assert [t.status for t in result.trades] == ["open"]
    # (b) 명목 상한이 아니다 — 수량은 여전히 1.0 계약 그대로다.
    assert result.trades[0].size == Decimal("1")
    # L=1 이므로 격리 레버리지 모델(청산)은 아예 돌지 않는다 = 막아줄 장치가 없었다.
    assert result.metrics.liquidation_occurred is None
    # 자본은 음수로 남는다 — 이 실행은 물리적으로 실현 불가능하다는 뜻이다.
    assert result.equity_curve.iloc[-1] < 0


def test_normal_run_does_not_raise_the_disclosure() -> None:
    """음성 대조 — 자본을 안 넘으면 고지가 켜지지 않는다(항상 True 인 플래그가 아니다)."""
    result = _run(_flat_ohlcv())

    assert result.metrics.mdd_exceeds_capital is False
    assert min(result.equity_curve) > 0


def test_disclosure_survives_the_report_round_trip() -> None:
    """고지가 **리포트 스키마로 실제로 나가는지** — JSONB 왕복에서 살아남아야 한다.

    엔진이 True 를 계산해도 직렬화에서 떨어지면 사용자는 못 본다.
    """
    from src.backtest.serializers import metrics_from_jsonb, metrics_to_jsonb

    metrics = _run(_falling_ohlcv()).metrics
    restored = metrics_from_jsonb(metrics_to_jsonb(metrics))

    assert restored.mdd_exceeds_capital is True
