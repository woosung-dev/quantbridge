"""동결 자연어 규칙의 독립 수식 판정기. 생성 명세·컴파일러·앱 지표를 사용하지 않는다.

history는 현재 완료 봉을 포함한다. 상태에는 이 판정기의 증분 계산만 저장한다.
지원하지 않는 규칙은 hold로 위장하지 않고 OracleUnavailable로 드러낸다.

full 수치 계약 v2: 유한한 신호 비교는 1e-12*max(1,abs(a),abs(b)) 이내를 동률로
본다. 원시 극값의 순서·동률, 봉 수·시간, 분모의 구조적 0은 정확 비교를 유지한다.
평균은 첫 값을 기준으로 중심화한 합을 사용하고 평활은 이전 값에 변화량을 더한다.
따라서 상수 평균·평활과 0 분산/MAD를 보존한다. Decimal 주문·리스크 수식은 별개다.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
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
    return _DEV + _SIMPLE + ("05", "06", "07", "09", "16", "22", "27", "30")


def unsupported_reason(strategy_id: str) -> str | None:
    return None if strategy_id in supported_ids() else "독립 수식 판정기가 아직 구현되지 않았습니다"


def _comparison(a: float, b: float) -> int | None:
    if not math.isfinite(a) or not math.isfinite(b):
        return None
    if abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b)):
        return 0
    return 1 if a > b else -1


def _gt(a: float, b: float) -> bool:
    return _comparison(a, b) == 1


def _lt(a: float, b: float) -> bool:
    return _comparison(a, b) == -1


def _ge(a: float, b: float) -> bool:
    return _comparison(a, b) in (0, 1)


def _le(a: float, b: float) -> bool:
    return _comparison(a, b) in (-1, 0)


def _mean(values: list[float]) -> float:
    """큰 가격의 합을 나누지 않아 동일 상수와 작은 편차를 보존한다."""
    anchor = values[0]
    return anchor + math.fsum(value - anchor for value in values) / len(values)


def _population_std(values: list[float]) -> float:
    offsets = [value - values[0] for value in values]
    center = _mean(offsets)
    return math.sqrt(_mean([(value - center) ** 2 for value in offsets]))


def _cross(a: list[float], b: list[float], *, up: bool = True) -> bool:
    if min(len(a), len(b)) < 2 or not all(
        math.isfinite(v) for v in (a[-2], a[-1], b[-2], b[-1])
    ):
        return False
    return (
        (_le(a[-2], b[-2]) and _gt(a[-1], b[-1]))
        if up
        else (_ge(a[-2], b[-2]) and _lt(a[-1], b[-1]))
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
                _mean([self.fields[key][-1] for key in ("high", "low", "close")])
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
                result.append(_population_std(window))
            else:
                result.append(_mean(window))
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
                result.append(previous + alpha * (value - previous))
            else:
                window = values[max(0, index - length + 1) : index + 1]
                result.append(
                    _mean(window)
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
            elif gain_value == loss_value == 0 or loss_value == 0:
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
        origins = self.cache.setdefault("vwap_origin", [])
        total_value = self.cache.setdefault("vwap_offset", [])
        total_volume = self.cache.setdefault("vwap_volume", [])
        for index in range(len(result), len(self.times)):
            reset = (
                index == 0 or self.times[index].date() != self.times[index - 1].date()
            )
            origin = self.fields["hlc3"][index] if reset else origins[-1]
            origins.append(origin)
            volume = self.fields["volume"][index]
            value = (self.fields["hlc3"][index] - origin) * volume
            total_value.append(value + (0 if reset else total_value[-1]))
            total_volume.append(volume + (0 if reset else total_volume[-1]))
            result.append(
                origin + total_value[-1] / total_volume[-1] if total_volume[-1] > 0 else _NAN
            )
        return result

    def anchored_vwap(self) -> list[float]:
        result = self.cache.setdefault("anchored_vwap", [])
        origins = self.cache.setdefault("anchored_origin", [])
        total_value = self.cache.setdefault("anchored_offset", [])
        total_volume = self.cache.setdefault("anchored_volume", [])
        anchor = datetime(2026, 1, 1, tzinfo=UTC)
        for index in range(len(result), len(self.times)):
            included = self.times[index] >= anchor
            origin = origins[-1] if origins else _NAN
            if included and not math.isfinite(origin):
                origin = self.fields["hlc3"][index]
            origins.append(origin)
            volume = self.fields["volume"][index] if included else 0
            value = (self.fields["hlc3"][index] - origin) * volume if included else 0
            total_value.append((total_value[-1] if total_value else 0) + value)
            total_volume.append((total_volume[-1] if total_volume else 0) + volume)
            result.append(origin + total_value[-1] / total_volume[-1] if total_volume[-1] > 0 else _NAN)
        return result

    def squeeze(self) -> tuple[list[float], list[float]]:
        """현재 제외 유효 BW 120개, 새 event 우선, 이후 1..5봉의 첫 교차만 소비한다."""
        close, basis = self.fields["close"], self.sma(20)
        sd = self.rolling("squeeze_std20", close, 20, "std")
        width = self.derived(
            "squeeze_width",
            lambda i: 4 * sd[i] / basis[i] if basis[i] != 0 else _NAN,
        )
        upper = self.derived("squeeze_upper", lambda i: basis[i] + 2 * sd[i])
        lower = self.derived("squeeze_lower", lambda i: basis[i] - 2 * sd[i])
        valid = self.cache.setdefault("squeeze_valid_width", [])
        events = self.cache.setdefault("squeeze_event", [])
        consumed = self.cache.setdefault("squeeze_consumed", [])
        longs = self.cache.setdefault("squeeze_long", [])
        shorts = self.cache.setdefault("squeeze_short", [])
        for index in range(len(longs), len(close)):
            event = events[-1] if events else _NAN
            used = bool(consumed[-1]) if consumed else False
            if (
                math.isfinite(width[index])
                and len(valid) >= 120
                and _le(width[index], min(valid[-120:]))
            ):
                event, used = float(index), False
            up = down = False
            if not used and math.isfinite(event) and 1 <= index - event <= 5:
                up = _cross(close[index - 1 : index + 1], upper[index - 1 : index + 1])
                down = _cross(close[index - 1 : index + 1], lower[index - 1 : index + 1], up=False)
                used = up or down
            events.append(event)
            consumed.append(float(used))
            longs.append(float(up))
            shorts.append(float(down))
            if math.isfinite(width[index]):
                valid.append(width[index])
        return longs, shorts

    def divergence(self) -> tuple[list[float], list[float], list[float], list[float]]:
        """RSI 엄격 3/3 pivot은 3봉 뒤 확정, 확인은 그 다음 봉 한 번만이다."""
        rsi = self.rsi(14)
        high, low, close = (self.fields[key] for key in ("high", "low", "close"))
        latest_low = self.cache.setdefault("divergence_low_pivot", [])
        latest_high = self.cache.setdefault("divergence_high_pivot", [])
        pending_long = self.cache.setdefault("divergence_pending_long", [])
        pending_short = self.cache.setdefault("divergence_pending_short", [])
        longs = self.cache.setdefault("divergence_long", [])
        shorts = self.cache.setdefault("divergence_short", [])
        long_level = self.cache.setdefault("divergence_long_level", [])
        short_level = self.cache.setdefault("divergence_short_level", [])
        for index in range(len(longs), len(close)):
            previous_long = pending_long[-1] if pending_long else _NAN
            previous_short = pending_short[-1] if pending_short else _NAN
            up = index > 0 and math.isfinite(previous_long) and _gt(close[index], high[index - 1])
            down = index > 0 and math.isfinite(previous_short) and _lt(close[index], low[index - 1])
            longs.append(float(up))
            shorts.append(float(down))
            long_level.append(previous_long if up else long_level[-1] if long_level else _NAN)
            short_level.append(previous_short if down else short_level[-1] if short_level else _NAN)
            first_low = latest_low[-1] if latest_low else _NAN
            first_high = latest_high[-1] if latest_high else _NAN
            bull = bear = _NAN
            pivot = index - 3
            window = rsi[index - 6 : index + 1] if index >= 6 else []
            if len(window) == 7 and all(math.isfinite(value) for value in window):
                neighbours = window[:3] + window[4:]
                if _lt(rsi[pivot], min(neighbours)):
                    if math.isfinite(first_low) and 3 <= pivot - first_low <= 60:
                        first = int(first_low)
                        if _lt(low[pivot], low[first]) and _gt(rsi[pivot], rsi[first]):
                            bull = low[pivot]
                    first_low = float(pivot)
                if _gt(rsi[pivot], max(neighbours)):
                    if math.isfinite(first_high) and 3 <= pivot - first_high <= 60:
                        first = int(first_high)
                        if _gt(high[pivot], high[first]) and _lt(rsi[pivot], rsi[first]):
                            bear = high[pivot]
                    first_high = float(pivot)
            latest_low.append(first_low)
            latest_high.append(first_high)
            pending_long.append(bull)
            pending_short.append(bear)
        return longs, shorts, long_level, short_level

    def ha(self) -> tuple[list[float], list[float]]:
        opens = self.cache.setdefault("ha_open", [])
        closes = self.cache.setdefault("ha_close", [])
        for index in range(len(opens), len(self.times)):
            opens.append(
                _mean([self.fields["open"][index], self.fields["close"][index]])
                if index == 0
                else _mean([opens[-1], closes[-1]])
            )
            closes.append(
                _mean([self.fields[key][index] for key in ("open", "high", "low", "close")])
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

        def formula(index: int) -> float:
            if index < 19:
                return _NAN
            window = typical[index - 19 : index + 1]
            offsets = [value - window[0] for value in window]
            center = _mean(offsets)
            deviation = _mean([abs(value - center) for value in offsets])
            return (
                (offsets[-1] - center) / (0.015 * deviation)
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

    def supertrend(self) -> list[float]:
        atr = self.atr(10)
        upper = self.cache.setdefault("supertrend_upper", [])
        lower = self.cache.setdefault("supertrend_lower", [])
        direction = self.cache.setdefault("supertrend_direction", [])
        close, high, low = (self.fields[key] for key in ("close", "high", "low"))
        for index in range(len(direction), len(self.times)):
            if not math.isfinite(atr[index]):
                upper.append(_NAN)
                lower.append(_NAN)
                direction.append(_NAN)
                continue
            basic_upper = (high[index] + low[index]) / 2 + 3 * atr[index]
            basic_lower = (high[index] + low[index]) / 2 - 3 * atr[index]
            valid_previous = index > 0 and math.isfinite(upper[-1])
            final_upper = (
                basic_upper
                if not valid_previous
                or _lt(basic_upper, upper[-1])
                or _gt(close[index - 1], upper[-1])
                else upper[-1]
            )
            final_lower = (
                basic_lower
                if not valid_previous
                or _gt(basic_lower, lower[-1])
                or _lt(close[index - 1], lower[-1])
                else lower[-1]
            )
            previous = direction[-1] if valid_previous else -1
            current_direction = (
                (1 if _gt(close[index], final_upper) else -1)
                if previous < 0
                else (-1 if _lt(close[index], final_lower) else 1)
            )
            upper.append(final_upper)
            lower.append(final_lower)
            direction.append(current_direction)
        return direction

    def dmi(self) -> tuple[list[float], list[float], list[float]]:
        high, low = self.fields["high"], self.fields["low"]
        plus = self.derived(
            "dm_plus",
            lambda i: (
                max(high[i] - high[i - 1], 0)
                if i and high[i] - high[i - 1] > low[i - 1] - low[i]
                else 0
            ),
        )
        minus = self.derived(
            "dm_minus",
            lambda i: (
                max(low[i - 1] - low[i], 0)
                if i and low[i - 1] - low[i] > high[i] - high[i - 1]
                else 0
            ),
        )
        plus_rma = self.smooth("dm_plus_rma", plus, 14, wilder=True)
        minus_rma = self.smooth("dm_minus_rma", minus, 14, wilder=True)
        atr = self.atr(14)
        plus_di = self.derived(
            "plus_di",
            lambda i: (
                100 * plus_rma[i] / atr[i] if atr[i] > 0 else 0 if atr[i] == 0 else _NAN
            ),
        )
        minus_di = self.derived(
            "minus_di",
            lambda i: (
                100 * minus_rma[i] / atr[i]
                if atr[i] > 0
                else 0
                if atr[i] == 0
                else _NAN
            ),
        )
        dx = self.derived(
            "dmi_dx",
            lambda i: (
                100 * abs(plus_di[i] - minus_di[i]) / (plus_di[i] + minus_di[i])
                if plus_di[i] + minus_di[i] > 0
                else 0
                if plus_di[i] + minus_di[i] == 0
                else _NAN
            ),
        )
        return plus_di, minus_di, self.smooth("adx14", dx, 14, wilder=True)

    def ichimoku(self) -> tuple[list[float], list[float], list[float], list[float]]:
        high, low = self.fields["high"], self.fields["low"]
        midpoints = []
        for length in (9, 26, 52):
            highest = self.rolling(f"ichi_high{length}", high, length, "max")
            lowest = self.rolling(f"ichi_low{length}", low, length, "min")
            midpoints.append(
                self.derived(
                    f"ichi_mid{length}",
                    lambda i, maximum=highest, minimum=lowest: (
                        (maximum[i] + minimum[i]) / 2
                    ),
                )
            )
        tenkan, kijun, span_b = midpoints
        upper = self.derived(
            "ichi_cloud_upper",
            lambda i: (
                max((tenkan[i - 26] + kijun[i - 26]) / 2, span_b[i - 26])
                if i >= 77
                else _NAN
            ),
        )
        lower = self.derived(
            "ichi_cloud_lower",
            lambda i: (
                min((tenkan[i - 26] + kijun[i - 26]) / 2, span_b[i - 26])
                if i >= 77
                else _NAN
            ),
        )
        return tenkan, kijun, upper, lower

    def regression(self) -> tuple[list[float], list[float], list[float]]:
        slopes = self.cache.setdefault("ols_slope", [])
        lower = self.cache.setdefault("ols_lower", [])
        upper = self.cache.setdefault("ols_upper", [])
        for index in range(len(slopes), len(self.times)):
            if index < 49:
                slopes.append(_NAN)
                lower.append(_NAN)
                upper.append(_NAN)
                continue
            prices = self.fields["close"][index - 49 : index + 1]
            offsets = [price - prices[0] for price in prices]
            center = _mean(offsets)
            slope = (
                math.fsum((x - 24.5) * (value - center) for x, value in enumerate(offsets))
                / 10412.5
            )
            endpoint = prices[0] + center + slope * 24.5
            deviation = math.sqrt(_mean([
                (value - (center + slope * (x - 24.5))) ** 2
                for x, value in enumerate(offsets)
            ]))
            slopes.append(slope)
            lower.append(endpoint - 2 * deviation)
            upper.append(endpoint + 2 * deviation)
        return slopes, lower, upper

    def htf_regime(self) -> list[float]:
        result = self.cache.setdefault("htf_regime", [])
        closes = self.cache.setdefault("htf_closes", [])
        for index in range(len(result), len(self.times)):
            timestamp = self.times[index]
            if timestamp.minute or timestamp.second:
                raise OracleUnavailable("완료4h regime에는 UTC 정시 1h 봉이 필요합니다")
            if (
                index >= 3
                and timestamp.hour % 4 == 3
                and all(
                    self.times[index - j] == timestamp - timedelta(hours=j)
                    for j in range(4)
                )
            ):
                closes.append(self.fields["close"][index])
            ema = self.smooth("htf_ema200", closes, 200)
            value = (
                1
                if closes and ema and _gt(closes[-1], ema[-1])
                else -1
                if closes and ema and _lt(closes[-1], ema[-1])
                else 0
            )
            result.append(value)
        return result


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
            _lt(fast[-1], slow[-1]),
            _gt(fast[-1], slow[-1]),
        )
    if ident == "D02":
        upper, lower = data.channel(7)
        middle = (upper[-1] + lower[-1]) / 2
        return (
            _cross(close, upper),
            _cross(close, lower, up=False),
            _lt(current, middle),
            _gt(current, middle),
        )
    if ident == "D03":
        rsi, ema = data.rsi(7), data.ema(15)[-1]
        level = [50.0] * len(close)
        return (
            _cross(rsi, level) and _gt(current, ema),
            _cross(rsi, level, up=False) and _lt(current, ema),
            _lt(rsi[-1], 45) or _lt(current, ema),
            _gt(rsi[-1], 55) or _gt(current, ema),
        )
    if ident == "D04":
        macd, signal = data.macd(3, 7, 2)
        ema = data.ema(15)[-1]
        up, down = _cross(macd, signal), _cross(macd, signal, up=False)
        return (
            up and _gt(current, ema),
            down and _lt(current, ema),
            down or _lt(current, ema),
            up or _gt(current, ema),
        )
    if ident == "D05":
        vwap, ema = data.vwap(), data.ema(15)[-1]
        if not math.isfinite(vwap[-1]) or len(vwap) < 2:
            return False, False, False, False
        return (
            _cross(close, vwap) and _gt(current, ema) and _gt(vwap[-1], vwap[-2]),
            _cross(close, vwap, up=False) and _lt(current, ema) and _lt(vwap[-1], vwap[-2]),
            _lt(current, vwap[-1]),
            _gt(current, vwap[-1]),
        )
    if ident in {"D06", "28"}:
        opens, closes = data.ha()
        bull = [_gt(c, o) for o, c in zip(opens, closes, strict=True)]
        bear = [_lt(c, o) for o, c in zip(opens, closes, strict=True)]
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
            new_bull and _gt(current, ema),
            new_bear and _lt(current, ema),
            bear[-1],
            bull[-1],
        )
    if ident in {"01", "02"}:
        fast, slow = data.ema(20), data.ema(50)
        up, down = _cross(fast, slow), _cross(fast, slow, up=False)
        if ident == "02":
            up = _gt(fast[-1], slow[-1]) and _cross(close, fast)
            down = _lt(fast[-1], slow[-1]) and _cross(close, fast, up=False)
            return up, down, _lt(current, slow[-1]), _gt(current, slow[-1])
        return up, down, _lt(fast[-1], slow[-1]), _gt(fast[-1], slow[-1])
    if ident in {"03", "04"}:
        upper, lower = data.channel(20 if ident == "03" else 55)
        if ident == "03":
            middle = (upper[-1] + lower[-1]) / 2
            return (
                _cross(close, upper),
                _cross(close, lower, up=False),
                _lt(current, middle),
                _gt(current, middle),
            )
        exit_high, exit_low = data.channel(20)
        return (
            _cross(close, upper),
            _cross(close, lower, up=False),
            _lt(current, exit_low[-1]),
            _gt(current, exit_high[-1]),
        )
    if ident in {"08", "10", "29"}:
        if ident == "08":
            ema, atr = data.ema(20), data.atr(20)
            upper = [e + 2 * a for e, a in zip(ema, atr, strict=True)]
            lower = [e - 2 * a for e, a in zip(ema, atr, strict=True)]
            return (
                _cross(close, upper) and len(ema) > 1 and _gt(ema[-1], ema[-2]),
                _cross(close, lower, up=False) and len(ema) > 1 and _lt(ema[-1], ema[-2]),
                _lt(current, ema[-1]),
                _gt(current, ema[-1]),
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
                _lt(current, ema),
                _gt(current, ema),
            )
        high, low = data.channel(22)
        atr, ema = data.atr(22), data.ema(200)[-1]
        upper = [low[i] + 3 * atr[i - 1] if i else _NAN for i in range(len(close))]
        lower = [high[i] - 3 * atr[i - 1] if i else _NAN for i in range(len(close))]
        return (
            _cross(close, upper) and _gt(current, ema),
            _cross(close, lower, up=False) and _lt(current, ema),
            _lt(current, lower[-1]),
            _gt(current, upper[-1]),
        )
    if ident == "09":
        long, short = data.squeeze()
        basis = data.sma(20)[-1]
        return bool(long[-1]), bool(short[-1]), _lt(current, basis), _gt(current, basis)
    if ident == "16":
        long, short, long_level, short_level = data.divergence()
        return bool(long[-1]), bool(short[-1]), _lt(current, long_level[-1]), _gt(current, short_level[-1])
    if ident == "11":
        rsi, ema = data.rsi(14), data.ema(200)[-1]
        mid = [50.0] * len(close)
        return (
            _cross(rsi, mid) and _gt(current, ema),
            _cross(rsi, mid, up=False) and _lt(current, ema),
            _lt(rsi[-1], 45) or _lt(current, ema),
            _gt(rsi[-1], 55) or _gt(current, ema),
        )
    if ident in {"12", "17"}:
        k, d = data.stochastic(rsi=ident == "12")
        ema = data.ema(200)[-1]
        up, down = _cross(k, d), _cross(k, d, up=False)
        if ident == "12":
            return (
                up and _le(k[-1], 20) and _gt(current, ema),
                down and _ge(k[-1], 80) and _lt(current, ema),
                (down and _lt(k[-1], 50)) or _lt(current, ema),
                (up and _gt(k[-1], 50)) or _gt(current, ema),
            )
        return (
            up and _le(50, k[-1]) and _le(k[-1], 80) and _gt(current, ema),
            down and _le(20, k[-1]) and _le(k[-1], 50) and _lt(current, ema),
            down or _lt(current, ema),
            up or _gt(current, ema),
        )
    if ident in {"13", "14"}:
        macd, signal = data.macd(12, 26, 9)
        if ident == "14":
            zero = [0.0] * len(close)
            return (
                _cross(macd, zero),
                _cross(macd, zero, up=False),
                _lt(macd[-1], 0),
                _gt(macd[-1], 0),
            )
        ema = data.ema(200)[-1]
        up, down = _cross(macd, signal), _cross(macd, signal, up=False)
        return (
            up and _gt(current, ema),
            down and _lt(current, ema),
            down or _lt(current, ema),
            up or _gt(current, ema),
        )
    if ident == "15":
        roc = data.derived(
            "roc12", lambda i: 100 * (close[i] / close[i - 12] - 1) if i >= 12 else _NAN
        )
        sma, zero = data.sma(50)[-1], [0.0] * len(close)
        return (
            _cross(roc, zero) and _gt(current, sma),
            _cross(roc, zero, up=False) and _lt(current, sma),
            _lt(roc[-1], 0) or _lt(current, sma),
            _gt(roc[-1], 0) or _gt(current, sma),
        )
    if ident == "18":
        cci, ema = data.cci(), data.ema(200)[-1]
        return (
            _cross(cci, [100.0] * len(close)) and _gt(current, ema),
            _cross(cci, [-100.0] * len(close), up=False) and _lt(current, ema),
            _lt(cci[-1], 0) or _lt(current, ema),
            _gt(cci[-1], 0) or _gt(current, ema),
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
            _cross(wpr, [-80.0] * len(close)) and _gt(current, ema),
            _cross(wpr, [-20.0] * len(close), up=False) and _lt(current, ema),
            _lt(wpr[-1], -80) or _lt(current, ema),
            _gt(wpr[-1], -20) or _gt(current, ema),
        )
    if ident == "20":
        tsi, signal = data.tsi()
        up, down = _cross(tsi, signal), _cross(tsi, signal, up=False)
        return (
            up and _gt(tsi[-1], 0),
            down and _lt(tsi[-1], 0),
            down or _lt(tsi[-1], 0),
            up or _gt(tsi[-1], 0),
        )
    if ident == "21":
        vwap, ema = data.vwap(), data.ema(200)[-1]
        if len(vwap) < 2 or not math.isfinite(vwap[-1]):
            return False, False, False, False
        return (
            _cross(close, vwap) and _gt(current, ema) and _gt(vwap[-1], vwap[-2]),
            _cross(close, vwap, up=False) and _lt(current, ema) and _lt(vwap[-1], vwap[-2]),
            _lt(current, vwap[-1]),
            _gt(current, vwap[-1]),
        )
    if ident == "22":
        vwap, ema = data.anchored_vwap(), data.ema(200)[-1]
        high, low = data.channel(20)
        return (
            _cross(close, vwap) and _gt(current, ema) and _gt(current, high[-1]),
            _cross(close, vwap, up=False) and _lt(current, ema) and _lt(current, low[-1]),
            _lt(current, vwap[-1]),
            _gt(current, vwap[-1]),
        )
    if ident == "23":
        obv = data.obv()
        average = data.rolling("obv_sma20", obv, 20)[-1]
        high, low = data.channel(20)
        ema, ema50 = data.ema(200)[-1], data.ema(50)[-1]
        return (
            _gt(current, ema) and _gt(current, high[-1]) and _gt(obv[-1], average),
            _lt(current, ema) and _lt(current, low[-1]) and _lt(obv[-1], average),
            _lt(current, ema50) or _lt(obv[-1], average),
            _gt(current, ema50) or _gt(obv[-1], average),
        )
    if ident == "24":
        cmf, fast, slow = data.cmf(), data.ema(20)[-1], data.ema(50)[-1]
        return (
            _cross(cmf, [0.05] * len(close)) and _gt(fast, slow),
            _cross(cmf, [-0.05] * len(close), up=False) and _lt(fast, slow),
            _lt(cmf[-1], 0) or _lt(fast, slow),
            _gt(cmf[-1], 0) or _gt(fast, slow),
        )
    if ident == "25":
        mfi, ema = data.mfi(), data.ema(200)
        if len(ema) < 2:
            return False, False, False, False
        return (
            _cross(mfi, [20.0] * len(close))
            and _gt(current, ema[-1])
            and _gt(ema[-1], ema[-2]),
            _cross(mfi, [80.0] * len(close), up=False)
            and _lt(current, ema[-1])
            and _lt(ema[-1], ema[-2]),
            _lt(current, ema[-1]) or _lt(mfi[-1], 20),
            _gt(current, ema[-1]) or _gt(mfi[-1], 80),
        )
    if ident == "26":
        up, down = data.aroon()
        return (
            _cross(up, down) and _ge(up[-1], 70) and _le(down[-1], 30),
            _cross(down, up) and _ge(down[-1], 70) and _le(up[-1], 30),
            _lt(up[-1], 50) or _gt(down[-1], up[-1]),
            _lt(down[-1], 50) or _gt(up[-1], down[-1]),
        )
    if ident == "05":
        direction = data.supertrend()
        changed = len(direction) > 1 and math.isfinite(direction[-2])
        return (
            changed and _lt(direction[-2], 0) and _gt(direction[-1], 0),
            changed and _gt(direction[-2], 0) and _lt(direction[-1], 0),
            _lt(direction[-1], 0),
            _gt(direction[-1], 0),
        )
    if ident == "06":
        plus, minus, adx = data.dmi()
        return (
            _cross(plus, minus) and _gt(adx[-1], 25),
            _cross(minus, plus) and _gt(adx[-1], 25),
            _lt(plus[-1], minus[-1]) or _lt(adx[-1], 20),
            _lt(minus[-1], plus[-1]) or _lt(adx[-1], 20),
        )
    if ident == "07":
        tenkan, kijun, upper, lower = data.ichimoku()
        inside = _le(lower[-1], current) and _le(current, upper[-1])
        return (
            _cross(tenkan, kijun) and _gt(current, upper[-1]),
            _cross(tenkan, kijun, up=False) and _lt(current, lower[-1]),
            _lt(current, kijun[-1]) or inside,
            _gt(current, kijun[-1]) or inside,
        )
    if ident == "27":
        slope, lower, upper = data.regression()
        return (
            _cross(close, lower) and _gt(slope[-1], 0),
            _cross(close, upper, up=False) and _lt(slope[-1], 0),
            _le(slope[-1], 0) or _lt(current, lower[-1]),
            _ge(slope[-1], 0) or _gt(current, upper[-1]),
        )
    if ident == "30":
        regime = data.htf_regime()[-1]
        fast, slow = data.ema(9), data.ema(21)
        return (
            _cross(fast, slow) and _gt(regime, 0),
            _cross(fast, slow, up=False) and _lt(regime, 0),
            _lt(regime, 0) or _lt(fast[-1], slow[-1]),
            _gt(regime, 0) or _gt(fast[-1], slow[-1]),
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
