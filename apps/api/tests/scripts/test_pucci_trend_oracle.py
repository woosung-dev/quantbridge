"""Pucci 원문의 허용폭 단위와 신호 상태·가격 필터를 손계산한다."""

import pandas as pd

from scripts.pine_validation.oracles import compute_oracle


def candles() -> pd.DataFrame:
    close = [10] * 7 + [30, 20, 6.25, 30, 1, 1]
    return pd.DataFrame(
        {
            "open": close,
            "high": [10] * 7 + [31, 21, 7, 31, 14, 14],
            "low": [10] * 7 + [14, 15, 6, 15, 1, 1],
            "close": close,
            "volume": [1] * len(close),
        },
        index=pd.date_range("2020-01-01", periods=len(close), freq="h", tz="UTC"),
    )


def test_state_suppresses_repeated_conditions_and_survives_a_neutral_bar():
    frame = candles()
    # EMA7[7:12]=15,16.25,13.75,17.8125,13.609375. 9번은 중립, 10번은 재매수 조건이다.
    events = compute_oracle("pucci_trend", frame, {"period": 7})
    assert [(event.bar_time, event.direction) for event in events] == [
        (frame.index[7], "long"),
        (frame.index[11], "short"),
    ]


def test_actual_high_low_filter_delays_events_until_an_allowed_candle():
    frame = candles()
    frame.loc[frame.index[7], "low"] = 30  # EMA=15보다 봉 전체가 위다: 매수 금지.
    frame.loc[frame.index[11], "high"] = 1  # EMA=13.609375보다 봉 전체가 아래다: 매도 금지.
    enabled = compute_oracle("pucci_trend", frame, {"period": 7})
    disabled = compute_oracle("pucci_trend", frame, {"period": 7, "use_price_filter": False})
    assert [(event.bar_time, event.direction) for event in enabled] == [
        (frame.index[8], "long"),
        (frame.index[12], "short"),
    ]
    assert [(event.bar_time, event.direction) for event in disabled] == [
        (frame.index[7], "long"),
        (frame.index[11], "short"),
    ]


def test_tolerance_uses_original_thousand_denominator_despite_basis_points_label():
    prices = [10] * 7 + [10.5]
    frame = pd.DataFrame(
        dict.fromkeys(("open", "high", "low", "close", "volume"), prices),
        index=pd.date_range("2020-01-01", periods=len(prices), freq="h", tz="UTC"),
    )
    # EMA=10.125, SMA=10.071428…: 차이는 0.532%, 원문 tolerance15=1.5%보다 작다.
    assert compute_oracle("pucci_trend", frame, {"period": 7, "use_price_filter": False}) == []
    no_tolerance = compute_oracle(
        "pucci_trend", frame, {"period": 7, "tolerance": 0, "use_price_filter": False}
    )
    assert [(event.bar_time, event.direction) for event in no_tolerance] == [
        (frame.index[7], "long")
    ]
