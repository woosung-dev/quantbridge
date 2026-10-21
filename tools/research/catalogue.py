"""역할이 다른 필터 10종 × 진입 신호 10종. 숫자만 바꾼 후보는 만들지 않는다."""

from pathlib import Path

FILTERS = {
    "ema_trend": ("EMA 200 추세", "c[-1] > ema(c, 200)", "c[-1] < ema(c, 200)"),
    "sma_trend": ("SMA 200 추세", "c[-1] > mean(c[-200:])", "c[-1] < mean(c[-200:])"),
    "wma_trend": ("WMA 100 추세", "c[-1] > wma(c[-100:])", "c[-1] < wma(c[-100:])"),
    "vwap_value": (
        "거래량 가중 50봉 가격",
        "c[-1] > vwap(h, l, c, v, 50)",
        "c[-1] < vwap(h, l, c, v, 50)",
    ),
    "donchian_mid": (
        "Donchian 50 중간값",
        "c[-1] > (max(h[-50:]) + min(l[-50:])) / 2",
        "c[-1] < (max(h[-50:]) + min(l[-50:])) / 2",
    ),
    "ichimoku_cloud": (
        "과거로부터 26봉 이동한 일목 구름",
        "c[-1] > max(cloud(h, l))",
        "c[-1] < min(cloud(h, l))",
    ),
    "obv_flow": ("OBV 20봉 누적 흐름", "obv(c, v, 20) > 0", "obv(c, v, 20) < 0"),
    "regression_slope": (
        "가격 선형회귀 50봉 기울기",
        "slope(c[-50:]) > 0",
        "slope(c[-50:]) < 0",
    ),
    "kama_trend": ("KAMA 10 효율비 추세", "c[-1] > kama(c)", "c[-1] < kama(c)"),
    "roc_regime": ("63봉 수익률 방향", "c[-1] > c[-64]", "c[-1] < c[-64]"),
}

SIGNALS = {
    "ema_cross": (
        "EMA 9/21 교차",
        "ema(c[:-1], 9) <= ema(c[:-1], 21) and ema(c, 9) > ema(c, 21)",
        "ema(c[:-1], 9) >= ema(c[:-1], 21) and ema(c, 9) < ema(c, 21)",
    ),
    "rsi_recovery": (
        "RSI 14 과매도·과매수 복귀",
        "rsi(c[:-1]) <= 30 < rsi(c)",
        "rsi(c[:-1]) >= 70 > rsi(c)",
    ),
    "stochastic_cross": (
        "Stochastic 14/3 극단 교차",
        "stoch(h[:-1], l[:-1], c[:-1]) <= stoch_d(h[:-1], l[:-1], c[:-1]) and stoch(h, l, c) > stoch_d(h, l, c) and stoch(h, l, c) < 20",
        "stoch(h[:-1], l[:-1], c[:-1]) >= stoch_d(h[:-1], l[:-1], c[:-1]) and stoch(h, l, c) < stoch_d(h, l, c) and stoch(h, l, c) > 80",
    ),
    "cci_recovery": (
        "CCI 20 극단 복귀",
        "cci(h[:-1], l[:-1], c[:-1]) <= -100 < cci(h, l, c)",
        "cci(h[:-1], l[:-1], c[:-1]) >= 100 > cci(h, l, c)",
    ),
    "macd_cross": (
        "MACD 12/26/9 시그널 교차",
        "macd_hist(c[:-1]) <= 0 < macd_hist(c)",
        "macd_hist(c[:-1]) >= 0 > macd_hist(c)",
    ),
    "bollinger_reentry": (
        "Bollinger 20/2 밴드 재진입",
        "c[-2] <= bb(c[:-1], -2) and c[-1] > bb(c, -2)",
        "c[-2] >= bb(c[:-1], 2) and c[-1] < bb(c, 2)",
    ),
    "donchian_breakout": (
        "직전 20봉 Donchian 돌파",
        "c[-1] > max(h[-21:-1])",
        "c[-1] < min(l[-21:-1])",
    ),
    "keltner_breakout": (
        "EMA 20 + ATR 14 × 2 돌파",
        "c[-2] <= ema(c[:-1], 20) + 2 * atr(h[:-1], l[:-1], c[:-1]) and c[-1] > ema(c, 20) + 2 * atr(h, l, c)",
        "c[-2] >= ema(c[:-1], 20) - 2 * atr(h[:-1], l[:-1], c[:-1]) and c[-1] < ema(c, 20) - 2 * atr(h, l, c)",
    ),
    "mfi_recovery": (
        "MFI 14 자금흐름 극단 복귀",
        "mfi(h[:-1], l[:-1], c[:-1], v[:-1]) <= 20 < mfi(h, l, c, v)",
        "mfi(h[:-1], l[:-1], c[:-1], v[:-1]) >= 80 > mfi(h, l, c, v)",
    ),
    "roc_zero": (
        "ROC 12 영점 교차",
        "c[-2] <= c[-14] and c[-1] > c[-13]",
        "c[-2] >= c[-14] and c[-1] < c[-13]",
    ),
}


def candidates() -> list[dict]:
    """영상 재현으로 둔갑시키지 않는 독립 연구 가설 목록."""
    return [
        {
            "id": f"hyp-v2-{filter_id}-{signal_id}",
            "revision": 2,
            "revision_reason": "봉 내부 TP/SL의 펀딩 정산 순서를 추측하지 않고 확정 종가 risk 판정으로 정의",
            "kind": "research_hypothesis",
            "source_ids": [],
            "evidence_level": "unverified_hypothesis",
            "filter": filter_id,
            "signal": signal_id,
            "name": f"{filter_name} + {signal_name}",
            "hypothesis": "추세·가치 필터가 허용하는 방향으로 독립 진입 신호를 사용한다.",
            "exit": "반대 신호·필터 반전 또는 진입가 대비 종가 -2%/+4% 시 다음 시가 청산. 봉 내부 보호주문이 아님",
            "warmup_bars": 200,
            "params": {},
            "status": "untested",
            "license": "project_authored",
        }
        for filter_id, (filter_name, _, _) in FILTERS.items()
        for signal_id, (signal_name, _, _) in SIGNALS.items()
    ]


def pilot_candidates() -> list[dict]:
    """각 필터·진입 신호가 한 번씩 등장하는 10개 파일럿."""
    return [
        item
        for item in candidates()
        if list(FILTERS).index(item["filter"]) == list(SIGNALS).index(item["signal"])
    ]


def source_for(candidate: dict) -> str:
    template = Path(__file__).with_name("strategy_template.py.txt").read_text()
    _, long_filter, short_filter = FILTERS[candidate["filter"]]
    _, long_signal, short_signal = SIGNALS[candidate["signal"]]
    return (
        template.replace("__LONG_FILTER__", long_filter)
        .replace("__SHORT_FILTER__", short_filter)
        .replace("__LONG_SIGNAL__", long_signal)
        .replace("__SHORT_SIGNAL__", short_signal)
    )
