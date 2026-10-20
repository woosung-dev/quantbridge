"""원문 고정 20/50 대 200 SMA 교차 4개를 지속 표식과 구분한다."""

import pandas as pd

from scripts.pine_validation.oracles import compute_oracle


def test_four_alerts_preserve_both_same_bar_crosses_without_seven_bar_hold():
    # 200개 10 뒤 20개 20: 첫 상승 봉에서 두 fast SMA가 동시에 slow를 넘는다.
    # 이어 1로 하락하면 20 SMA는 10번째, 50 SMA는 23번째 하락 봉에서 교차한다.
    prices = [10] * 200 + [20] * 20 + [1] * 23
    frame = pd.DataFrame(
        dict.fromkeys(("open", "high", "low", "close", "volume"), prices),
        index=pd.date_range("2020-01-01", periods=len(prices), freq="h", tz="UTC"),
    )
    events = compute_oracle("multi_sma_cross", frame)
    assert [(event.bar_time, event.direction) for event in events] == [
        (frame.index[200], "long"),
        (frame.index[200], "long"),
        (frame.index[229], "short"),
        (frame.index[242], "short"),
    ]
