"""동결 자연어 규칙의 독립 수식 판정기. 생성 명세·컴파일러·앱 지표를 사용하지 않는다.

history는 현재 완료 봉을 포함한다. 상태에는 이 판정기의 증분 계산만 저장한다.
지원하지 않는 규칙은 hold로 위장하지 않고 OracleUnavailable로 드러낸다.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

_NAN = float("nan")
_DEV = tuple(f"D{i:02}" for i in range(1, 7))
_SIMPLE = (
    "01",
    "02",
    "03",
    "04",
    "08",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "17",
    "18",
    "19",
    "20",
    "21",
    "23",
    "24",
    "25",
    "26",
    "28",
    "29",
)


class OracleUnavailable(ValueError):
    """독립 정의가 없는 전략은 정확하다고 채점할 수 없다."""


def supported_ids() -> tuple[str, ...]:
    return _DEV + _SIMPLE


def unsupported_reason(strategy_id: str) -> str | None:
    return (
        None
        if strategy_id in supported_ids()
        else "독립 수식 판정기가 아직 구현되지 않았습니다"
    )


def _cross(a: list[float], b: list[float], *, up: bool = True) -> bool:
    if min(len(a), len(b)) < 2 or not all(
        math.isfinite(v) for v in (a[-2], a[-1], b[-2], b[-1])
    ):
        return False
    return (
        (a[-2] <= b[-2] and a[-1] > b[-1]) if up else (a[-2] >= b[-2] and a[-1] < b[-1])
    )


class _Math:
    def __init__(self) -> None:
        self.fields: dict[str, list[float]] = {
            key: [] for key in ("open", "high", "low", "close", "volume", "hlc3")
        }
        self.times: list[datetime] = []
        self.cache: dict[str, list[float]] = {}

    def extend(self, history: list[dict[str, Any]]) -> None:
        for bar in history[len(self.times) :]:
            for key in ("open", "high", "low", "close", "volume"):
                self.fields[key].append(float(bar[key]))
            self.fields["hlc3"].append(
                sum(self.fields[key][-1] for key in ("high", "low", "close")) / 3
            )
            self.times.append(
                datetime.fromisoformat(
                    str(bar["timestamp"]).replace("Z", "+00:00")
                ).astimezone(UTC)
            )

    def rolling(
        self,
        key: str,
        values: list[float],
        length: int,
        kind: str = "mean",
        shift: int = 0,
    ) -> list[float]:
        result = self.cache.setdefault(key, [])
        for index in range(len(result), len(values)):
            right = index + 1 - shift
            window = values[right - length : right] if right >= length else []
            if len(window) != length or not all(math.isfinite(v) for v in window):
                result.append(_NAN)
            elif kind == "max":
                result.append(max(window))
            elif kind == "min":
                result.append(min(window))
            elif kind == "std":
                mean = sum(window) / length
                result.append(math.sqrt(sum((v - mean) ** 2 for v in window) / length))
            else:
                result.append(sum(window) / length)
        return result

    def smooth(
        self, key: str, values: list[float], length: int, *, wilder: bool = False
    ) -> list[float]:
        result = self.cache.setdefault(key, [])
        alpha = 1 / length if wilder else 2 / (length + 1)
        for index in range(len(result), len(values)):
            value = values[index]
            previous = result[-1] if result else _NAN
            if not math.isfinite(value):
                result.append(_NAN)
            elif math.isfinite(previous):
                result.append(alpha * value + (1 - alpha) * previous)
            else:
                window = values[max(0, index - length + 1) : index + 1]
                result.append(
                    sum(window) / length
                    if len(window) == length and all(math.isfinite(v) for v in window)
                    else _NAN
                )
        return result

    def ema(self, length: int) -> list[float]:
        return self.smooth(f"ema{length}", self.fields["close"], length)

    def sma(self, length: int) -> list[float]:
        return self.rolling(f"sma{length}", self.fields["close"], length)

    def rsi(self, length: int) -> list[float]:
        close = self.fields["close"]
        gain = self.cache.setdefault("gain", [])
        loss = self.cache.setdefault("loss", [])
        for index in range(len(gain), len(close)):
            change = close[index] - close[index - 1] if index else _NAN
            gain.append(max(change, 0))
            loss.append(max(-change, 0))
        gains = self.smooth(f"gain_rma{length}", gain, length, wilder=True)
        losses = self.smooth(f"loss_rma{length}", loss, length, wilder=True)
        result = self.cache.setdefault(f"rsi{length}", [])
        for index in range(len(result), len(close)):
            gain_value, loss_value = gains[index], losses[index]
            if not math.isfinite(gain_value) or not math.isfinite(loss_value):
                result.append(_NAN)
            elif gain_value == loss_value == 0:
                result.append(100.0)
            elif loss_value == 0:
                result.append(100.0)
            else:
                result.append(100 - 100 / (1 + gain_value / loss_value))
        return result

    def macd(
        self, fast: int, slow: int, signal: int
    ) -> tuple[list[float], list[float]]:
        fast_values, slow_values = self.ema(fast), self.ema(slow)
        line = self.cache.setdefault(f"macd{fast}:{slow}", [])
        for index in range(len(line), len(self.times)):
            line.append(fast_values[index] - slow_values[index])
        return line, self.smooth(f"macdsig{fast}:{slow}:{signal}", line, signal)

    def channel(self, length: int) -> tuple[list[float], list[float]]:
        return (
            self.rolling(f"hh_prev{length}", self.fields["high"], length, "max", 1),
            self.rolling(f"ll_prev{length}", self.fields["low"], length, "min", 1),
        )

    def vwap(self) -> list[float]:
        result = self.cache.setdefault("vwap", [])
        total_value = self.cache.setdefault("vwap_value", [])
        total_volume = self.cache.setdefault("vwap_volume", [])
        for index in range(len(result), len(self.times)):
            reset = (
                index == 0 or self.times[index].date() != self.times[index - 1].date()
            )
            value = self.fields["hlc3"][index] * self.fields["volume"][index]
            volume = self.fields["volume"][index]
            total_value.append(value + (0 if reset else total_value[-1]))
            total_volume.append(volume + (0 if reset else total_volume[-1]))
            result.append(
                total_value[-1] / total_volume[-1] if total_volume[-1] > 0 else _NAN
            )
        return result

    def ha(self) -> tuple[list[float], list[float]]:
        opens = self.cache.setdefault("ha_open", [])
        closes = self.cache.setdefault("ha_close", [])
        for index in range(len(opens), len(self.times)):
            opens.append(
                (self.fields["open"][index] + self.fields["close"][index]) / 2
                if index == 0
                else (opens[-1] + closes[-1]) / 2
            )
            closes.append(
                sum(self.fields[key][index] for key in ("open", "high", "low", "close"))
                / 4
            )
        return opens, closes

    def derived(self, key: str, formula: Any) -> list[float]:
        result = self.cache.setdefault(key, [])
        for index in range(len(result), len(self.times)):
            result.append(float(formula(index)))
        return result

    def atr(self, length: int) -> list[float]:
        high, low, close = (self.fields[key] for key in ("high", "low", "close"))
        tr = self.derived(
            "true_range",
            lambda i: (
                high[i] - low[i]
                if i == 0
                else max(
                    high[i] - low[i],
                    abs(high[i] - close[i - 1]),
                    abs(low[i] - close[i - 1]),
                )
            ),
        )
        return self.smooth(f"atr{length}", tr, length, wilder=True)

    def stochastic(self, *, rsi: bool = False) -> tuple[list[float], list[float]]:
        source = self.rsi(14) if rsi else self.fields["close"]
        top = self.rolling(
            f"stoch_top:{rsi}", source if rsi else self.fields["high"], 14, "max"
        )
        bottom = self.rolling(
            f"stoch_bottom:{rsi}", source if rsi else self.fields["low"], 14, "min"
        )
        raw = self.derived(
            f"stoch_raw:{rsi}",
            lambda i: (
                100 * (source[i] - bottom[i]) / (top[i] - bottom[i])
                if top[i] > bottom[i]
                else _NAN
            ),
        )
        k = self.rolling(f"stoch_k:{rsi}", raw, 3)
        return k, self.rolling(f"stoch_d:{rsi}", k, 3)

    def cci(self) -> list[float]:
        typical = self.fields["hlc3"]
        mean = self.rolling("cci_mean", typical, 20)

        def formula(index: int) -> float:
            if index < 19:
                return _NAN
            deviation = (
                sum(
                    abs(value - mean[index])
                    for value in typical[index - 19 : index + 1]
                )
                / 20
            )
            return (
                (typical[index] - mean[index]) / (0.015 * deviation)
                if deviation > 0
                else 0
            )

        return self.derived("cci20", formula)

    def tsi(self) -> tuple[list[float], list[float]]:
        close = self.fields["close"]
        change = self.derived(
            "momentum", lambda i: close[i] - close[i - 1] if i else _NAN
        )
        absolute = self.derived("abs_momentum", lambda i: abs(change[i]))
        numerator = self.smooth("tsi_num13", self.smooth("tsi_num25", change, 25), 13)
        denominator = self.smooth(
            "tsi_den13", self.smooth("tsi_den25", absolute, 25), 13
        )
        line = self.derived(
            "tsi",
            lambda i: (
                100 * numerator[i] / denominator[i]
                if denominator[i] > 0
                else 0
                if denominator[i] == 0
                else _NAN
            ),
        )
        return line, self.smooth("tsi_signal7", line, 7)

    def obv(self) -> list[float]:
        close, volume = self.fields["close"], self.fields["volume"]
        result = self.cache.setdefault("obv", [])
        for index in range(len(result), len(self.times)):
            sign = (
                0
                if index == 0 or close[index] == close[index - 1]
                else 1
                if close[index] > close[index - 1]
                else -1
            )
            result.append((result[-1] if result else 0) + sign * volume[index])
        return result

    def cmf(self) -> list[float]:
        high, low, close, volume = (
            self.fields[key] for key in ("high", "low", "close", "volume")
        )
        flow = self.derived(
            "cmf_flow",
            lambda i: (
                (2 * close[i] - high[i] - low[i]) / (high[i] - low[i]) * volume[i]
                if high[i] != low[i]
                else 0
            ),
        )
        mean_flow = self.rolling("cmf_mean_flow", flow, 20)
        mean_volume = self.rolling("cmf_mean_volume", volume, 20)
        return self.derived(
            "cmf20",
            lambda i: mean_flow[i] / mean_volume[i] if mean_volume[i] > 0 else _NAN,
        )

    def mfi(self) -> list[float]:
        typical, volume = self.fields["hlc3"], self.fields["volume"]
        positive = self.derived(
            "mfi_positive",
            lambda i: (
                typical[i] * volume[i] if i and typical[i] > typical[i - 1] else 0
            ),
        )
        negative = self.derived(
            "mfi_negative",
            lambda i: (
                typical[i] * volume[i] if i and typical[i] < typical[i - 1] else 0
            ),
        )
        plus = self.rolling("mfi_positive_mean", positive, 14)
        minus = self.rolling("mfi_negative_mean", negative, 14)
        return self.derived(
            "mfi14",
            lambda i: (
                100 - 100 / (1 + plus[i] / minus[i])
                if minus[i] > 0
                else 100
                if minus[i] == 0 and plus[i] > 0
                else _NAN
            ),
        )

    def aroon(self) -> tuple[list[float], list[float]]:
        high, low = self.fields["high"], self.fields["low"]

        def value(index: int, maximum: bool) -> float:
            if index < 25:
                return _NAN
            series = high if maximum else low
            window = series[index - 25 : index + 1]
            extreme = max(window) if maximum else min(window)
            since = next(
                offset
                for offset, price in enumerate(reversed(window))
                if price == extreme
            )
            return 100 * (25 - since) / 25

        return self.derived("aroon_up", lambda i: value(i, True)), self.derived(
            "aroon_down", lambda i: value(i, False)
        )


def _decision(
    long: bool, short: bool, invalid_long: bool, invalid_short: bool, direction: str
) -> str:
    if long and short:
        return "hold"
    if direction == "long":
        return "short" if short else "close" if invalid_long else "hold"
    if direction == "short":
        return "long" if long else "close" if invalid_short else "hold"
    return "long" if long else "short" if short else "hold"


def _conditions(ident: str, data: _Math) -> tuple[bool, bool, bool, bool]:
    close = data.fields["close"]
    current = close[-1]
    if ident == "D01":
        fast, slow = data.sma(3), data.sma(8)
        return (
            _cross(fast, slow),
            _cross(fast, slow, up=False),
            fast[-1] < slow[-1],
            fast[-1] > slow[-1],
        )
    if ident == "D02":
        upper, lower = data.channel(7)
        middle = (upper[-1] + lower[-1]) / 2
        return (
            _cross(close, upper),
            _cross(close, lower, up=False),
            current < middle,
            current > middle,
        )
    if ident == "D03":
        rsi, ema = data.rsi(7), data.ema(15)[-1]
        level = [50.0] * len(close)
        return (
            _cross(rsi, level) and current > ema,
            _cross(rsi, level, up=False) and current < ema,
            rsi[-1] < 45 or current < ema,
            rsi[-1] > 55 or current > ema,
        )
    if ident == "D04":
        macd, signal = data.macd(3, 7, 2)
        ema = data.ema(15)[-1]
        up, down = _cross(macd, signal), _cross(macd, signal, up=False)
        return (
            up and current > ema,
            down and current < ema,
            down or current < ema,
            up or current > ema,
        )
    if ident == "D05":
        vwap, ema = data.vwap(), data.ema(15)[-1]
        if not math.isfinite(vwap[-1]) or len(vwap) < 2:
            return False, False, False, False
        return (
            _cross(close, vwap) and current > ema and vwap[-1] > vwap[-2],
            _cross(close, vwap, up=False) and current < ema and vwap[-1] < vwap[-2],
            current < vwap[-1],
            current > vwap[-1],
        )
    if ident in {"D06", "28"}:
        opens, closes = data.ha()
        bull = [c > o for o, c in zip(opens, closes, strict=True)]
        bear = [c < o for o, c in zip(opens, closes, strict=True)]
        new_bull = (
            len(bull) >= 2
            and bull[-1]
            and bull[-2]
            and not (bull[-3] if len(bull) >= 3 else False)
        )
        new_bear = (
            len(bear) >= 2
            and bear[-1]
            and bear[-2]
            and not (bear[-3] if len(bear) >= 3 else False)
        )
        ema = data.ema(15 if ident == "D06" else 200)[-1]
        return (
            new_bull and current > ema,
            new_bear and current < ema,
            bear[-1],
            bull[-1],
        )
    if ident in {"01", "02"}:
        fast, slow = data.ema(20), data.ema(50)
        up, down = _cross(fast, slow), _cross(fast, slow, up=False)
        if ident == "02":
            up = fast[-1] > slow[-1] and _cross(close, fast)
            down = fast[-1] < slow[-1] and _cross(close, fast, up=False)
            return up, down, current < slow[-1], current > slow[-1]
        return up, down, fast[-1] < slow[-1], fast[-1] > slow[-1]
    if ident in {"03", "04"}:
        upper, lower = data.channel(20 if ident == "03" else 55)
        if ident == "03":
            middle = (upper[-1] + lower[-1]) / 2
            return (
                _cross(close, upper),
                _cross(close, lower, up=False),
                current < middle,
                current > middle,
            )
        exit_high, exit_low = data.channel(20)
        return (
            _cross(close, upper),
            _cross(close, lower, up=False),
            current < exit_low[-1],
            current > exit_high[-1],
        )
    if ident in {"08", "10", "29"}:
        if ident == "08":
            ema, atr = data.ema(20), data.atr(20)
            upper = [e + 2 * a for e, a in zip(ema, atr, strict=True)]
            lower = [e - 2 * a for e, a in zip(ema, atr, strict=True)]
            return (
                _cross(close, upper) and len(ema) > 1 and ema[-1] > ema[-2],
                _cross(close, lower, up=False) and len(ema) > 1 and ema[-1] < ema[-2],
                current < ema[-1],
                current > ema[-1],
            )
        if ident == "10":
            atr, ema = data.atr(20), data.ema(20)[-1]
            upper = [_NAN] + [
                c + 0.5 * a for c, a in zip(close[:-1], atr[:-1], strict=True)
            ]
            lower = [_NAN] + [
                c - 0.5 * a for c, a in zip(close[:-1], atr[:-1], strict=True)
            ]
            return (
                _cross(close, upper),
                _cross(close, lower, up=False),
                current < ema,
                current > ema,
            )
        high, low = data.channel(22)
        atr, ema = data.atr(22), data.ema(200)[-1]
        upper = [low[i] + 3 * atr[i - 1] if i else _NAN for i in range(len(close))]
        lower = [high[i] - 3 * atr[i - 1] if i else _NAN for i in range(len(close))]
        return (
            _cross(close, upper) and current > ema,
            _cross(close, lower, up=False) and current < ema,
            current < lower[-1],
            current > upper[-1],
        )
    if ident == "11":
        rsi, ema = data.rsi(14), data.ema(200)[-1]
        mid = [50.0] * len(close)
        return (
            _cross(rsi, mid) and current > ema,
            _cross(rsi, mid, up=False) and current < ema,
            rsi[-1] < 45 or current < ema,
            rsi[-1] > 55 or current > ema,
        )
    if ident in {"12", "17"}:
        k, d = data.stochastic(rsi=ident == "12")
        ema = data.ema(200)[-1]
        up, down = _cross(k, d), _cross(k, d, up=False)
        if ident == "12":
            return (
                up and k[-1] <= 20 and current > ema,
                down and k[-1] >= 80 and current < ema,
                (down and k[-1] < 50) or current < ema,
                (up and k[-1] > 50) or current > ema,
            )
        return (
            up and 50 <= k[-1] <= 80 and current > ema,
            down and 20 <= k[-1] <= 50 and current < ema,
            down or current < ema,
            up or current > ema,
        )
    if ident in {"13", "14"}:
        macd, signal = data.macd(12, 26, 9)
        if ident == "14":
            zero = [0.0] * len(close)
            return (
                _cross(macd, zero),
                _cross(macd, zero, up=False),
                macd[-1] < 0,
                macd[-1] > 0,
            )
        ema = data.ema(200)[-1]
        up, down = _cross(macd, signal), _cross(macd, signal, up=False)
        return (
            up and current > ema,
            down and current < ema,
            down or current < ema,
            up or current > ema,
        )
    if ident == "15":
        roc = data.derived(
            "roc12", lambda i: 100 * (close[i] / close[i - 12] - 1) if i >= 12 else _NAN
        )
        sma, zero = data.sma(50)[-1], [0.0] * len(close)
        return (
            _cross(roc, zero) and current > sma,
            _cross(roc, zero, up=False) and current < sma,
            roc[-1] < 0 or current < sma,
            roc[-1] > 0 or current > sma,
        )
    if ident == "18":
        cci, ema = data.cci(), data.ema(200)[-1]
        return (
            _cross(cci, [100.0] * len(close)) and current > ema,
            _cross(cci, [-100.0] * len(close), up=False) and current < ema,
            cci[-1] < 0 or current < ema,
            cci[-1] > 0 or current > ema,
        )
    if ident == "19":
        high = data.rolling("wpr_high", data.fields["high"], 14, "max")
        low = data.rolling("wpr_low", data.fields["low"], 14, "min")
        wpr = data.derived(
            "wpr14",
            lambda i: (
                -100 * (high[i] - close[i]) / (high[i] - low[i])
                if high[i] > low[i]
                else _NAN
            ),
        )
        ema = data.ema(200)[-1]
        return (
            _cross(wpr, [-80.0] * len(close)) and current > ema,
            _cross(wpr, [-20.0] * len(close), up=False) and current < ema,
            wpr[-1] < -80 or current < ema,
            wpr[-1] > -20 or current > ema,
        )
    if ident == "20":
        tsi, signal = data.tsi()
        up, down = _cross(tsi, signal), _cross(tsi, signal, up=False)
        return (
            up and tsi[-1] > 0,
            down and tsi[-1] < 0,
            down or tsi[-1] < 0,
            up or tsi[-1] > 0,
        )
    if ident == "21":
        vwap, ema = data.vwap(), data.ema(200)[-1]
        if len(vwap) < 2 or not math.isfinite(vwap[-1]):
            return False, False, False, False
        return (
            _cross(close, vwap) and current > ema and vwap[-1] > vwap[-2],
            _cross(close, vwap, up=False) and current < ema and vwap[-1] < vwap[-2],
            current < vwap[-1],
            current > vwap[-1],
        )
    if ident == "23":
        obv = data.obv()
        average = data.rolling("obv_sma20", obv, 20)[-1]
        high, low = data.channel(20)
        ema, ema50 = data.ema(200)[-1], data.ema(50)[-1]
        return (
            current > ema and current > high[-1] and obv[-1] > average,
            current < ema and current < low[-1] and obv[-1] < average,
            current < ema50 or obv[-1] < average,
            current > ema50 or obv[-1] > average,
        )
    if ident == "24":
        cmf, fast, slow = data.cmf(), data.ema(20)[-1], data.ema(50)[-1]
        return (
            _cross(cmf, [0.05] * len(close)) and fast > slow,
            _cross(cmf, [-0.05] * len(close), up=False) and fast < slow,
            cmf[-1] < 0 or fast < slow,
            cmf[-1] > 0 or fast > slow,
        )
    if ident == "25":
        mfi, ema = data.mfi(), data.ema(200)
        if len(ema) < 2:
            return False, False, False, False
        return (
            _cross(mfi, [20.0] * len(close))
            and current > ema[-1]
            and ema[-1] > ema[-2],
            _cross(mfi, [80.0] * len(close), up=False)
            and current < ema[-1]
            and ema[-1] < ema[-2],
            current < ema[-1] or mfi[-1] < 20,
            current > ema[-1] or mfi[-1] > 80,
        )
    if ident == "26":
        up, down = data.aroon()
        return (
            _cross(up, down) and up[-1] >= 70 and down[-1] <= 30,
            _cross(down, up) and down[-1] >= 70 and up[-1] <= 30,
            up[-1] < 50 or down[-1] > up[-1],
            down[-1] < 50 or up[-1] > down[-1],
        )
    raise OracleUnavailable(f"전략 {ident}: 독립 수식 판정기가 없습니다")


def expected_action(
    strategy_id: str,
    history: list[dict[str, Any]],
    position: dict[str, Any],
    state: dict[str, Any],
) -> str:
    """공개 자연어 규칙만 계산한다. state를 전략 간 공유하지 않는다."""
    if unsupported_reason(strategy_id) is not None:
        raise OracleUnavailable(
            f"전략 {strategy_id}: {unsupported_reason(strategy_id)}"
        )
    if not history:
        return "hold"
    cached = state.get("_independent_oracle")
    if (
        not isinstance(cached, tuple)
        or cached[0] != strategy_id
        or len(cached[1].times) > len(history)
    ):
        cached = strategy_id, _Math()
        state["_independent_oracle"] = cached
    data = cached[1]
    data.extend(history)
    return _decision(
        *_conditions(strategy_id, data), str(position.get("direction", "flat"))
    )


def expected_risk_plan(
    entry: Decimal, previous_bars: list[dict[str, Any]], direction: str
) -> dict[str, Decimal]:
    """손계산용 독립 식. 공통 broker나 swing_risk 함수를 호출하지 않는다."""
    if len(previous_bars) != 2 or direction not in ("long", "short"):
        raise ValueError("완료 두 봉과 long/short 방향이 필요합니다")
    sign = Decimal(1) if direction == "long" else Decimal(-1)
    extreme = (
        min(Decimal(str(bar["low"])) for bar in previous_bars)
        if sign > 0
        else max(Decimal(str(bar["high"])) for bar in previous_bars)
    )
    risk = (entry - extreme) * sign * Decimal("1.1")
    if risk <= 0:
        raise ValueError("극값은 실제 진입가의 손실 방향이어야 합니다")
    return {
        "risk": risk,
        "stop": entry - sign * risk,
        "partial": entry + sign * risk * Decimal("1.5"),
        "activation": entry + sign * risk * 2,
        "distance": risk * 2,
    }
