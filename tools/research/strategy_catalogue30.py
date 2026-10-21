"""30개 공개 지표 정의와 프로젝트 연구 변형. 성과·원본 전략 재현을 주장하지 않는다.

reference_spec은 개발 fixture다. 평가의 LLM 입력은 prompt/source_urls뿐이며 정답 명세를
생성 입력에 주입하지 않는다. 독립 oracle는 이 compiler의 출력을 정답으로 사용하지 않는다.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_BASE = "https://www.tradingview.com/support/solutions/"
_DOC = "https://www.tradingview.com/pine-script-docs/concepts/"
RISK_RULE = (
    "완료봉에서 신호를 확정하고 다음 봉 시가에 진입한다. 실제 진입 E와 신호봉/이전 완료봉의 "
    "long 최저 L 또는 short 최고 H를 사용한다. long R=1.1*(E-L), short R=1.1*(H-E); "
    "R<=0이면 진입하지 않는다. SL은 E에서 손실 방향 1R. 최초 수량 50%를 +1.5R에서 한 번 익절한다. "
    "+2R에서 비용 전 본절을 보호하고 2R 거리 trailing을 유리한 방향만 이동한다. "
    "무효화는 잔량 전부 다음 시가 청산. 반대 전체 진입 신호는 잔량 청산 후 반전하며 새 R을 만든다. "
    "동방향 반복 진입은 무시하고 양방향 동시 신호는 보류한다. 신호/HA 합성가격으로 체결하지 않는다."
)


def _ref(series: str, offset: int = 0, output: str = "value") -> dict:
    return {"series": series, "offset": offset, "output": output}


def _constant(value: float) -> dict:
    return {"constant": value}


def _cmp(op: str, left: str | dict, right: str | float | dict) -> dict:
    return {
        "op": op,
        "left": _ref(left) if isinstance(left, str) else left,
        "right": _ref(right)
        if isinstance(right, str)
        else _constant(right)
        if isinstance(right, (int, float))
        else right,
    }


def _all(*conditions: dict) -> dict:
    return {"op": "all", "children": list(conditions)}


def _any(*conditions: dict) -> dict:
    return {"op": "any", "children": list(conditions)}


def _ind(ident: str, kind: str, length: int, **kwargs: Any) -> dict:
    return {"id": ident, "kind": kind, "length": length, **kwargs}


def _spec(
    name: str,
    indicators: list[dict],
    le: dict,
    se: dict,
    li: dict,
    si: dict,
    warmup: int = 200,
) -> dict:
    return {
        "title": name,
        "indicators": indicators,
        "long_entry": le,
        "short_entry": se,
        "long_invalidation": li,
        "short_invalidation": si,
        "warmup_bars": warmup,
    }


# 각 행의 진입/무효화는 저자의 완성 전략이 아니라 이 실험에서 사전 고정한 변형이다.
_ROWS = [
    (
        "01",
        "EMA 20/50 교차",
        "EMA20이 EMA50을 상향 교차",
        "EMA20이 EMA50을 하향 교차",
        "EMA20<EMA50",
        "EMA20>EMA50",
        "43000592270-exponential-moving-average/",
    ),
    (
        "02",
        "EMA 추세 눌림 복귀",
        "EMA20>EMA50, 전봉 C<=전봉 EMA20, 현재 C>EMA20",
        "EMA20<EMA50, 전봉 C>=전봉 EMA20, 현재 C<EMA20",
        "C<EMA50",
        "C>EMA50",
        "43000592270-exponential-moving-average/",
    ),
    (
        "03",
        "Donchian 20 돌파",
        "C가 현재봉 제외 직전20봉 최고가 상향 교차",
        "C가 현재봉 제외 직전20봉 최저가 하향 교차",
        "C<직전20봉 채널 중간값",
        "C>직전20봉 채널 중간값",
        "43000502253-donchian-channels-dc/",
    ),
    (
        "04",
        "Turtle 55/20",
        "C가 현재봉 제외 직전55봉 최고가 상향 교차",
        "C가 현재봉 제외 직전55봉 최저가 하향 교차",
        "C<현재봉 제외 직전20봉 최저가",
        "C>현재봉 제외 직전20봉 최고가",
        "43000502253-donchian-channels-dc/",
    ),
    (
        "05",
        "Supertrend 전환",
        "ATR10x3 Supertrend가 하락에서 상승 regime으로 확정 전환",
        "ATR10x3 Supertrend가 상승에서 하락 regime으로 확정 전환",
        "Supertrend 하락 regime",
        "Supertrend 상승 regime",
        "43000634738-supertrend/",
    ),
    (
        "06",
        "DMI ADX 추세",
        "DMI14 +DI가 -DI 상향 교차하고 ADX14>25",
        "-DI가 +DI 상향 교차하고 ADX14>25",
        "+DI<-DI 또는 ADX<20",
        "-DI<+DI 또는 ADX<20",
        "43000589099-average-directional-index-adx/",
    ),
    (
        "07",
        "Ichimoku 구름 확인",
        "9전환선이 26기준선 상향 교차하고 C가 표시구름 위",
        "9전환선이 26기준선 하향 교차하고 C가 표시구름 아래",
        "기준선 하회 또는 구름 진입",
        "기준선 상회 또는 구름 진입",
        "43000589152-ichimoku-cloud/",
    ),
    (
        "08",
        "Keltner 추세 돌파",
        "C가 EMA20+2ATR20 상향 교차하고 EMA20 상승",
        "C가 EMA20-2ATR20 하향 교차하고 EMA20 하락",
        "C<EMA20",
        "C>EMA20",
        "43000502266-keltner-channels-kc/",
    ),
    (
        "09",
        "Bollinger squeeze 돌파",
        "BB20x2 bandwidth가 이전120봉 최소 이하가 된 후5봉 이내 상단 상향 돌파",
        "같은 squeeze 후5봉 이내 하단 하향 돌파",
        "C<SMA20",
        "C>SMA20",
        "43000501840-bollinger-bands-bb/",
    ),
    (
        "10",
        "ATR 확장 돌파",
        "C가 전봉C+0.5*전봉ATR20 상향 교차",
        "C가 전봉C-0.5*전봉ATR20 하향 교차",
        "C<EMA20",
        "C>EMA20",
        "43000501823-average-true-range-atr/",
    ),
    (
        "11",
        "RSI 중심선 추세",
        "RSI14가50 상향 교차하고 C>EMA200",
        "RSI14가50 하향 교차하고 C<EMA200",
        "RSI<45 또는 C<EMA200",
        "RSI>55 또는 C>EMA200",
        "43000502338-relative-strength-index-rsi/",
    ),
    (
        "12",
        "Stochastic RSI 추세",
        "StochRSI14/14/3/3 K가 D 상향 교차,K<=20,C>EMA200",
        "K가 D 하향 교차,K>=80,C<EMA200",
        "반대K/D교차와 K<50 또는 C<EMA200",
        "반대K/D교차와 K>50 또는 C>EMA200",
        "43000502333-stochastic-rsi-stoch-rsi/",
    ),
    (
        "13",
        "MACD signal 추세",
        "MACD12/26이 signal9 상향 교차하고 C>EMA200",
        "MACD12/26이 signal9 하향 교차하고 C<EMA200",
        "반대교차 또는 C<EMA200",
        "반대교차 또는 C>EMA200",
        "43000502344-moving-average-convergence-divergence-macd-indicator/",
    ),
    (
        "14",
        "MACD 영선 교차",
        "MACD12/26이0 상향 교차",
        "MACD12/26이0 하향 교차",
        "MACD<0",
        "MACD>0",
        "43000502344-moving-average-convergence-divergence-macd-indicator/",
    ),
    (
        "15",
        "ROC 추세 확인",
        "ROC12가0 상향 교차하고 C>SMA50",
        "ROC12가0 하향 교차하고 C<SMA50",
        "ROC<0 또는 C<SMA50",
        "ROC>0 또는 C>SMA50",
        "43000502343-rate-of-change-roc/",
    ),
    (
        "16",
        "RSI 확정 pivot 다이버전스",
        "RSI14의3/3확정pivot에서 가격저점하락/RSI저점상승 후 확인봉C>직전H",
        "가격고점상승/RSI고점하락 후 확인봉C<직전L",
        "둘째 pivot 저점 이탈",
        "둘째 pivot 고점 이탈",
        "43000502338-relative-strength-index-rsi/",
    ),
    (
        "17",
        "Stochastic 추세 재개",
        "Stoch14/3/3 K가D 상향 교차,50<=K<=80,C>EMA200",
        "K가D 하향 교차,20<=K<=50,C<EMA200",
        "반대교차 또는 C<EMA200",
        "반대교차 또는 C>EMA200",
        "43000502332-stochastic-stoch/",
    ),
    (
        "18",
        "CCI 추세 확장",
        "CCI20이+100 상향 교차,C>EMA200",
        "CCI20이-100 하향 교차,C<EMA200",
        "CCI<0 또는 C<EMA200",
        "CCI>0 또는 C>EMA200",
        "43000502001-commodity-channel-index-cci/",
    ),
    (
        "19",
        "Williams R 복귀",
        "WPR14가-80 상향 교차,C>EMA200",
        "WPR14가-20 하향 교차,C<EMA200",
        "WPR<-80 또는 C<EMA200",
        "WPR>-20 또는 C>EMA200",
        "43000501985-williams-r-r/",
    ),
    (
        "20",
        "TSI 추세 전환",
        "TSI25/13이 자신의EMA7 상향 교차,TSI>0",
        "TSI25/13이 자신의EMA7 하향 교차,TSI<0",
        "반대교차 또는 TSI<0",
        "반대교차 또는 TSI>0",
        "43000592290-true-strength-index/",
    ),
    (
        "21",
        "UTC 일중 VWAP 복귀",
        "C>EMA200,UTC일중VWAP 상승,C가VWAP 상향 교차",
        "C<EMA200,UTC일중VWAP 하락,C가VWAP 하향 교차",
        "C<VWAP",
        "C>VWAP",
        "43000502018-volume-weighted-average-price-vwap/",
    ),
    (
        "22",
        "Anchored VWAP 돌파",
        "사전고정UTC anchor AVWAP 상향교차,C>EMA200,C>직전20봉HH",
        "AVWAP 하향교차,C<EMA200,C<직전20봉LL",
        "C<AVWAP",
        "C>AVWAP",
        "43000669764-anchored-vwap-drawing-tool/",
    ),
    (
        "23",
        "OBV 확인 돌파",
        "C>EMA200,C>직전20봉HH,OBV>OBV의SMA20",
        "C<EMA200,C<직전20봉LL,OBV<OBV의SMA20",
        "C<EMA50 또는 OBV<OBV의SMA20",
        "C>EMA50 또는 OBV>OBV의SMA20",
        "43000502593-on-balance-volume-obv/",
    ),
    (
        "24",
        "CMF 추세 재개",
        "EMA20>EMA50,CMF20이+0.05 상향교차",
        "EMA20<EMA50,CMF20이-0.05 하향교차",
        "CMF<0 또는 EMA20<EMA50",
        "CMF>0 또는 EMA20>EMA50",
        "https://help.chaikinanalytics.com/en_US/knowledge-center/chaikin-money-flow",
    ),
    (
        "25",
        "MFI 눌림 복귀",
        "C>상승EMA200,MFI14가20 상향교차",
        "C<하락EMA200,MFI14가80 하향교차",
        "C<EMA200 또는 MFI<20",
        "C>EMA200 또는 MFI>80",
        "43000502348-money-flow-mfi/",
    ),
    (
        "26",
        "Aroon 추세 시작",
        "Aroon25 Up이Down 상향교차,Up>=70,Down<=30",
        "Down이Up 상향교차,Down>=70,Up<=30",
        "Up<50 또는 Down>Up",
        "Down<50 또는 Up>Down",
        "43000501801-aroon-indicator/",
    ),
    (
        "27",
        "선형회귀 채널 복귀",
        "50봉OLS기울기>0,전봉C<=전봉잔차2sd하단,현재C>현재하단",
        "기울기<0,전봉C>=전봉상단,현재C<현재상단",
        "기울기<=0 또는 C<하단",
        "기울기>=0 또는 C>상단",
        "43000644936-linear-regression/",
    ),
    (
        "28",
        "Heikin Ashi 추세 확인",
        "실제C>EMA200,HA양봉2개가처음연속확정",
        "실제C<EMA200,HA음봉2개가처음연속확정",
        "HA음봉 확정",
        "HA양봉 확정",
        _DOC + "non-standard-charts-data/",
    ),
    (
        "29",
        "Chandelier 추세 전환",
        "C가전봉LL22+3ATR22 상향교차,C>EMA200",
        "C가전봉HH22-3ATR22 하향교차,C<EMA200",
        "C<전봉HH22-3ATR22",
        "C>전봉LL22+3ATR22",
        "43000773013-chandelier-exit/",
    ),
    (
        "30",
        "완료4h EMA regime",
        "직전완료4h C>4hEMA200,1hEMA9가EMA21 상향교차",
        "직전완료4h C<4hEMA200,1hEMA9가EMA21 하향교차",
        "완료4h regime하락 또는 1hEMA9<EMA21",
        "완료4h regime상승 또는 1hEMA9>EMA21",
        _DOC + "other-timeframes-and-data/",
    ),
]


def _reference(number: str, name: str) -> dict | None:
    c = _cmp
    e20, e50, e200 = (
        _ind("ema20", "ema", 20),
        _ind("ema50", "ema", 50),
        _ind("ema200", "ema", 200),
    )
    filter_l, filter_s = c("gt", "close", "ema200"), c("lt", "close", "ema200")
    loss_l, loss_s = c("lt", "close", "ema200"), c("gt", "close", "ema200")
    if number in {"01", "02"}:
        le, se = c("cross_up", "ema20", "ema50"), c("cross_down", "ema20", "ema50")
        li, si = c("lt", "ema20", "ema50"), c("gt", "ema20", "ema50")
        if number == "02":
            le = _all(
                c("gt", "ema20", "ema50"),
                c("lte", _ref("close", 1), _ref("ema20", 1)),
                c("gt", "close", "ema20"),
            )
            se = _all(
                c("lt", "ema20", "ema50"),
                c("gte", _ref("close", 1), _ref("ema20", 1)),
                c("lt", "close", "ema20"),
            )
            li, si = c("lt", "close", "ema50"), c("gt", "close", "ema50")
        return _spec(name, [e20, e50], le, se, li, si)
    if number in {"03", "04"}:
        n = 20 if number == "03" else 55
        indicators = [_ind("channel", "donchian", n)]
        li, si = (
            c("lt", "close", _ref("channel", 1)),
            c("gt", "close", _ref("channel", 1)),
        )
        if number == "04":
            indicators.append(_ind("exit_channel", "donchian", 20))
            li, si = (
                c("lt", "close", _ref("exit_channel", 1, "lower")),
                c("gt", "close", _ref("exit_channel", 1, "upper")),
            )
        return _spec(
            name,
            indicators,
            c("cross_up", "close", _ref("channel", 1, "upper")),
            c("cross_down", "close", _ref("channel", 1, "lower")),
            li,
            si,
        )
    if number in {"08", "10"}:
        kind = "keltner" if number == "08" else "atr_breakout"
        indicators = [
            _ind("channel", kind, 20, multiplier=2 if number == "08" else 0.5),
            e20,
        ]
        offset = 0 if number == "08" else 1
        le, se = (
            c("cross_up", "close", _ref("channel", offset, "upper")),
            c("cross_down", "close", _ref("channel", offset, "lower")),
        )
        if number == "08":
            le = _all(le, c("gt", "ema20", _ref("ema20", 1)))
            se = _all(se, c("lt", "ema20", _ref("ema20", 1)))
        return _spec(
            name,
            indicators,
            le,
            se,
            c("lt", "close", "ema20"),
            c("gt", "close", "ema20"),
        )
    if number == "11":
        return _spec(
            name,
            [_ind("rsi", "rsi", 14), e200],
            _all(c("cross_up", "rsi", 50), filter_l),
            _all(c("cross_down", "rsi", 50), filter_s),
            _any(c("lt", "rsi", 45), loss_l),
            _any(c("gt", "rsi", 55), loss_s),
        )
    if number in {"13", "14"}:
        ind = _ind("macd", "macd", 12, slow=26, signal=9)
        right = _ref("macd", output="signal") if number == "13" else 0
        le, se = c("cross_up", "macd", right), c("cross_down", "macd", right)
        li, si = se, le
        indicators = [ind]
        if number == "13":
            indicators.append(e200)
            li, si = _any(li, loss_l), _any(si, loss_s)
            le, se = _all(le, filter_l), _all(se, filter_s)
        else:
            li, si = c("lt", "macd", 0), c("gt", "macd", 0)
        return _spec(name, indicators, le, se, li, si)
    if number == "15":
        indicators = [_ind("roc", "roc", 12), _ind("sma50", "sma", 50)]
        return _spec(
            name,
            indicators,
            _all(c("cross_up", "roc", 0), c("gt", "close", "sma50")),
            _all(c("cross_down", "roc", 0), c("lt", "close", "sma50")),
            _any(c("lt", "roc", 0), c("lt", "close", "sma50")),
            _any(c("gt", "roc", 0), c("gt", "close", "sma50")),
        )
    if number in {"17", "18", "19"}:
        kind, n = {
            "17": ("stochastic", 14),
            "18": ("cci", 20),
            "19": ("williams_r", 14),
        }[number]
        indicators = [
            _ind(
                "osc",
                kind,
                n,
                slow=3,
                signal=3,
                source="hlc3" if kind == "cci" else "close",
            ),
            e200,
        ]
        if number == "17":
            le = _all(
                c("cross_up", "osc", _ref("osc", output="signal")),
                c("gte", "osc", 50),
                c("lte", "osc", 80),
                filter_l,
            )
            se = _all(
                c("cross_down", "osc", _ref("osc", output="signal")),
                c("gte", "osc", 20),
                c("lte", "osc", 50),
                filter_s,
            )
            li, si = (
                _any(c("cross_down", "osc", _ref("osc", output="signal")), loss_l),
                _any(c("cross_up", "osc", _ref("osc", output="signal")), loss_s),
            )
        else:
            up, down = (100, -100) if number == "18" else (-80, -20)
            le, se = (
                _all(c("cross_up", "osc", up), filter_l),
                _all(c("cross_down", "osc", down), filter_s),
            )
            li, si = (
                _any(c("lt", "osc", 0 if number == "18" else -80), loss_l),
                _any(c("gt", "osc", 0 if number == "18" else -20), loss_s),
            )
        return _spec(name, indicators, le, se, li, si)
    if number in {"21", "22"}:
        kind = "vwap" if number == "21" else "anchored_vwap"
        indicator = _ind(
            "vwap", kind, 1, **({"anchor_ms": 1767225600000} if number == "22" else {})
        )
        indicators = [indicator, e200]
        le, se = (
            _all(filter_l, c("cross_up", "close", "vwap")),
            _all(filter_s, c("cross_down", "close", "vwap")),
        )
        if number == "21":
            le = _all(le, c("gt", "vwap", _ref("vwap", 1)))
            se = _all(se, c("lt", "vwap", _ref("vwap", 1)))
        else:
            indicators.append(_ind("channel", "donchian", 20))
            le = _all(le, c("gt", "close", _ref("channel", 1, "upper")))
            se = _all(se, c("lt", "close", _ref("channel", 1, "lower")))
        return _spec(
            name, indicators, le, se, c("lt", "close", "vwap"), c("gt", "close", "vwap")
        )
    if number == "23":
        indicators = [
            e50,
            e200,
            _ind("obv", "obv", 20),
            _ind("channel", "donchian", 20),
        ]
        return _spec(
            name,
            indicators,
            _all(
                filter_l,
                c("gt", "close", _ref("channel", 1, "upper")),
                c("gt", "obv", _ref("obv", output="signal")),
            ),
            _all(
                filter_s,
                c("lt", "close", _ref("channel", 1, "lower")),
                c("lt", "obv", _ref("obv", output="signal")),
            ),
            _any(
                c("lt", "close", "ema50"), c("lt", "obv", _ref("obv", output="signal"))
            ),
            _any(
                c("gt", "close", "ema50"), c("gt", "obv", _ref("obv", output="signal"))
            ),
        )
    if number == "24":
        return _spec(
            name,
            [e20, e50, _ind("cmf", "cmf", 20)],
            _all(c("gt", "ema20", "ema50"), c("cross_up", "cmf", 0.05)),
            _all(c("lt", "ema20", "ema50"), c("cross_down", "cmf", -0.05)),
            _any(c("lt", "cmf", 0), c("lt", "ema20", "ema50")),
            _any(c("gt", "cmf", 0), c("gt", "ema20", "ema50")),
        )
    if number == "25":
        return _spec(
            name,
            [e200, _ind("mfi", "mfi", 14)],
            _all(
                filter_l, c("gt", "ema200", _ref("ema200", 1)), c("cross_up", "mfi", 20)
            ),
            _all(
                filter_s,
                c("lt", "ema200", _ref("ema200", 1)),
                c("cross_down", "mfi", 80),
            ),
            _any(loss_l, c("lt", "mfi", 20)),
            _any(loss_s, c("gt", "mfi", 80)),
        )
    if number == "26":
        up, down = _ref("aroon", output="up"), _ref("aroon", output="down")
        return _spec(
            name,
            [_ind("aroon", "aroon", 25)],
            _all(c("cross_up", up, down), c("gte", up, 70), c("lte", down, 30)),
            _all(c("cross_up", down, up), c("gte", down, 70), c("lte", up, 30)),
            _any(c("lt", up, 50), c("gt", down, up)),
            _any(c("lt", down, 50), c("gt", up, down)),
        )
    if number == "27":
        slope, lower, upper = (
            _ref("reg", output="slope"),
            _ref("reg", output="lower"),
            _ref("reg", output="upper"),
        )
        return _spec(
            name,
            [_ind("reg", "regression", 50)],
            _all(c("gt", slope, 0), c("cross_up", "close", lower)),
            _all(c("lt", slope, 0), c("cross_down", "close", upper)),
            _any(c("lte", slope, 0), c("lt", "close", lower)),
            _any(c("gte", slope, 0), c("gt", "close", upper)),
        )
    if number == "28":

        def bullish(offset: int) -> dict:
            return c("gt", _ref("ha", offset), _ref("ha", offset, "open"))

        def bearish(offset: int) -> dict:
            return c("lt", _ref("ha", offset), _ref("ha", offset, "open"))

        return _spec(
            name,
            [e200, _ind("ha", "heikin_ashi", 1)],
            _all(
                filter_l,
                bullish(0),
                bullish(1),
                c("lte", _ref("ha", 2), _ref("ha", 2, "open")),
            ),
            _all(
                filter_s,
                bearish(0),
                bearish(1),
                c("gte", _ref("ha", 2), _ref("ha", 2, "open")),
            ),
            bearish(0),
            bullish(0),
        )
    if number == "29":
        return _spec(
            name,
            [e200, _ind("ce", "chandelier", 22, multiplier=3)],
            _all(filter_l, c("cross_up", "close", _ref("ce", 1, "upper"))),
            _all(filter_s, c("cross_down", "close", _ref("ce", 1, "lower"))),
            c("lt", "close", _ref("ce", 1, "lower")),
            c("gt", "close", _ref("ce", 1, "upper")),
        )
    return None


def candidates() -> list[dict]:
    result = []
    unsupported = {
        "05": "supertrend regime",
        "06": "DMI ADX",
        "07": "displayed Ichimoku cloud",
        "09": "stateful bandwidth squeeze",
        "12": "StochRSI",
        "16": "confirmed pivot divergence",
        "20": "TSI double smoothing",
        "30": "confirmed higher-timeframe EMA",
    }
    for number, name, long_entry, short_entry, long_exit, short_exit, url in _ROWS:
        rules = {
            "long_entry": long_entry,
            "short_entry": short_entry,
            "long_invalidation": long_exit,
            "short_invalidation": short_exit,
            "execution": "closed_bar_signal_next_open",
            "risk": RISK_RULE,
        }
        details = ""
        if number == "16":
            details = " pivot左右各3봉,확정pivot간격3..60봉,엄격극값,같은값은가장최근확정우선. 확인은pivot확정다음봉한번만."
        if number == "22":
            details = (
                " anchor=2026-01-01T00:00:00Z 사전고정; 최종구간을보고anchor선택금지."
            )
        if number == "30":
            details = " 기준1h에서UTC정렬된직전완료4h만사용;4hEMAseed와warmup동결;현재미완료4h사용금지."
        reference = _reference(number, name)
        limits = [unsupported[number]] if number in unsupported else []
        result.append(
            {
                "id": number,
                "name": name,
                "prompt": f"{name}. Long: {long_entry}. Short: {short_entry}. Long무효화: {long_exit}. Short무효화: {short_exit}.{details} {RISK_RULE}",
                "source_urls": [url if url.startswith("https://") else _BASE + url],
                "source_status": "indicator_definition_project_variant",
                "rules": rules,
                "reference_spec": reference,
                "known_compiler_limits": limits,
            }
        )
    return deepcopy(result)
