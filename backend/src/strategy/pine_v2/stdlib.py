"""Pine `ta.*` stdlib 구현 (Week 2 Day 3).

bar-by-bar 이벤트 루프와 호환되는 stateful 지표.
각 지표 호출 지점(AST node id)마다 독립 상태 유지 — 같은 `ta.sma(close, 14)`가
두 번 등장해도 서로 다른 ring buffer.

구현 9개:
- ta.sma(source, length)         — 단순 이동평균
- ta.ema(source, length)         — 지수 이동평균 (alpha = 2/(length+1))
- ta.atr(length)                 — Average True Range (high-low + gap)
- ta.rsi(source, length)         — Relative Strength Index
- ta.crossover(a, b)             — a가 b를 상향 돌파 이번 bar
- ta.crossunder(a, b)            — a가 b를 하향 돌파
- ta.highest(source, length)     — 최근 length bars 최댓값
- ta.lowest(source, length)      — 최근 length bars 최솟값
- ta.change(source, length=1)    — source - source[length]

유틸:
- nz(x, replacement=0) — na면 replacement 반환
- na(x) — nan 여부

범위 밖 (Week 2 Day 4+ 또는 Week 3):
- ta.pivothigh/pivotlow (복잡한 lookback confirmation)
- ta.valuewhen, ta.barssince 등 상태 의존 검색
- request.security (MTF, H2+)
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any


def _is_na(x: Any) -> bool:
    return isinstance(x, float) and math.isnan(x)


@dataclass
class IndicatorState:
    """per-call-site 지표 상태 저장소. key = AST node id."""

    # 일반 버퍼 (ring or dict 등 지표별 자유)
    buffers: dict[int, Any] = field(default_factory=dict)


# -------- 이동평균 -----------------------------------------------------


def ta_sma(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """단순 이동평균. length 이하 샘플이면 na."""
    if length <= 0:
        return float("nan")
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    if _is_na(source):
        # Pine: SMA는 na 포함 시 na 반환 (엄격)
        buf.append(source)
        return float("nan")
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    return sum(buf) / length


def ta_ema(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """지수 이동평균. 첫 값 = SMA(length), 이후 = alpha*src + (1-alpha)*prev."""
    if length <= 0:
        return float("nan")
    slot = state.buffers.setdefault(node_id, {"prev": float("nan"), "warmup": []})
    if _is_na(source):
        return float(slot["prev"])
    warmup = slot["warmup"]
    if _is_na(slot["prev"]):
        warmup.append(source)
        if len(warmup) < length:
            return float("nan")
        seed = sum(warmup) / length
        slot["prev"] = seed
        return float(seed)
    alpha = 2.0 / (length + 1.0)
    ema = alpha * source + (1.0 - alpha) * slot["prev"]
    slot["prev"] = ema
    return float(ema)


def ta_rma(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """Wilder Running Moving Average (alpha = 1/length, EMA-style smoothing).

    첫 값 = SMA(length) seed, 이후 = (prev * (length-1) + source) / length.
    Pine v5 ta.rma 호환. Sprint X1+X3 dogfood follow-up (i3_drfx ta.rma 의존).
    """
    if length <= 0:
        return float("nan")
    slot = state.buffers.setdefault(node_id, {"prev": float("nan"), "warmup": []})
    if _is_na(source):
        return float(slot["prev"])
    warmup = slot["warmup"]
    if _is_na(slot["prev"]):
        warmup.append(source)
        if len(warmup) < length:
            return float("nan")
        seed = sum(warmup) / length
        slot["prev"] = seed
        return float(seed)
    rma = (slot["prev"] * (length - 1) + source) / length
    slot["prev"] = rma
    return float(rma)


# -------- 변동성 / 범위 ------------------------------------------------


def ta_atr(
    state: IndicatorState,
    node_id: int,
    length: int,
    high: float,
    low: float,
    close_prev: float,
) -> float:
    """Average True Range. True Range = max(high-low, |high-prev_close|, |low-prev_close|)."""
    if length <= 0:
        return float("nan")
    tr = high - low
    if not _is_na(close_prev):
        tr = max(tr, abs(high - close_prev), abs(low - close_prev))
    # Rolling mean
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    buf.append(tr)
    if len(buf) < length:
        return float("nan")
    return sum(buf) / length


# -------- RSI ----------------------------------------------------------


def ta_rsi(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """Relative Strength Index (Wilder's smoothing 근사)."""
    if length <= 0:
        return float("nan")
    slot = state.buffers.setdefault(
        node_id,
        {
            "prev_src": float("nan"),
            "avg_gain": float("nan"),
            "avg_loss": float("nan"),
            "warmup_gain": [],
            "warmup_loss": [],
        },
    )
    prev = slot["prev_src"]
    slot["prev_src"] = source
    if _is_na(prev):
        return float("nan")
    change = source - prev
    gain = max(change, 0.0)
    loss = max(-change, 0.0)

    if _is_na(slot["avg_gain"]):
        slot["warmup_gain"].append(gain)
        slot["warmup_loss"].append(loss)
        if len(slot["warmup_gain"]) < length:
            return float("nan")
        slot["avg_gain"] = sum(slot["warmup_gain"]) / length
        slot["avg_loss"] = sum(slot["warmup_loss"]) / length
    else:
        # Wilder smoothing
        slot["avg_gain"] = (slot["avg_gain"] * (length - 1) + gain) / length
        slot["avg_loss"] = (slot["avg_loss"] * (length - 1) + loss) / length

    if slot["avg_loss"] == 0.0:
        return 100.0
    rs = slot["avg_gain"] / slot["avg_loss"]
    return float(100.0 - (100.0 / (1.0 + rs)))


# -------- crossover / crossunder ---------------------------------------


def ta_crossover(state: IndicatorState, node_id: int, a: float, b: float) -> bool:
    """a가 b를 상향 돌파 이번 bar: 이전에는 a <= b, 지금은 a > b."""
    slot = state.buffers.setdefault(node_id, {"prev_a": float("nan"), "prev_b": float("nan")})
    prev_a = slot["prev_a"]
    prev_b = slot["prev_b"]
    slot["prev_a"] = a
    slot["prev_b"] = b
    if _is_na(prev_a) or _is_na(prev_b) or _is_na(a) or _is_na(b):
        return False
    return prev_a <= prev_b and a > b


def ta_crossunder(state: IndicatorState, node_id: int, a: float, b: float) -> bool:
    """a가 b를 하향 돌파: 이전에는 a >= b, 지금은 a < b."""
    slot = state.buffers.setdefault(node_id, {"prev_a": float("nan"), "prev_b": float("nan")})
    prev_a = slot["prev_a"]
    prev_b = slot["prev_b"]
    slot["prev_a"] = a
    slot["prev_b"] = b
    if _is_na(prev_a) or _is_na(prev_b) or _is_na(a) or _is_na(b):
        return False
    return prev_a >= prev_b and a < b


# -------- highest / lowest ---------------------------------------------


def ta_highest(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    return max(buf)


def ta_lowest(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    return min(buf)


# -------- barssince / valuewhen (Sprint 8c) ---------------------------
#
# 상태 의존 검색: s3_rsid 계열 전략이 필수로 사용.
# - barssince: 조건이 마지막으로 true였던 시점 이후 경과 bar 수.
# - valuewhen: 조건이 occurrence번째로 true였을 때의 source 값.


def ta_barssince(state: IndicatorState, node_id: int, cond: Any) -> float:
    """Pine `ta.barssince(cond)` — cond가 마지막 true였던 시점 이후 bar 수.

    - true 발생 bar: 0 반환.
    - 이전에 true 없음: nan 반환 (Pine v5 na 호환).
    """
    slot = state.buffers.setdefault(node_id, {"since": None})
    cond_bool = bool(cond) if not _is_na(cond) else False
    if cond_bool:
        slot["since"] = 0
        return 0
    if slot["since"] is None:
        return float("nan")
    slot["since"] += 1
    return int(slot["since"])


_VALUEWHEN_MAX_HIST: int = 500


def ta_valuewhen(
    state: IndicatorState,
    node_id: int,
    cond: Any,
    source: Any,
    occurrence: int,
) -> float:
    """Pine `ta.valuewhen(cond, source, occurrence)` — occurrence번째 최근 cond=true 시점의 source.

    occurrence=0: 가장 최근 true 시점의 source.
    occurrence=1: 그 이전 true 시점.
    history 부족 시 nan.

    deque(maxlen=500) + appendleft O(1). list.insert(0, ...) O(n) 대비 성능 개선.
    음수 occurrence → nan. float occurrence → int 변환.
    """
    if not isinstance(occurrence, int):
        occurrence = int(occurrence)
    if occurrence < 0:
        return float("nan")
    slot = state.buffers.setdefault(node_id, {"history": deque(maxlen=_VALUEWHEN_MAX_HIST)})
    hist: deque[float] = slot["history"]
    cond_bool = bool(cond) if not _is_na(cond) else False
    if cond_bool and source is not None and not _is_na(source):
        hist.appendleft(float(source))
    if occurrence >= len(hist):
        return float("nan")
    return hist[occurrence]


# -------- pivot high / pivot low ---------------------------------------


def ta_pivothigh(
    state: IndicatorState,
    node_id: int,
    left: int,
    right: int,
    high: float,
) -> float:
    """Pine `ta.pivothigh(left, right)` — pivot high 감지.

    현재 bar N에서 "바 N-right가 pivot high인가?" 검사:
    - high[right] > high[right+1..right+left]  (왼쪽 left 바들보다 높음)
    - high[right] > high[0..right-1]           (오른쪽 right 바들보다 높음)

    반환: pivot 감지되면 high[right] (= pivot 가격), 아니면 nan.
    """
    slot = state.buffers.setdefault(node_id, {"highs": []})
    highs = slot["highs"]
    highs.append(high)

    window = left + right + 1
    if len(highs) < window:
        return float("nan")
    if len(highs) > 2 * window:
        highs[:] = highs[-2 * window :]

    pivot_idx = len(highs) - right - 1
    pivot_val = highs[pivot_idx]

    for i in range(max(0, pivot_idx - left), pivot_idx):
        if highs[i] >= pivot_val:
            return float("nan")
    for i in range(pivot_idx + 1, len(highs)):
        if highs[i] >= pivot_val:
            return float("nan")
    return float(pivot_val)


def ta_pivotlow(
    state: IndicatorState,
    node_id: int,
    left: int,
    right: int,
    low: float,
) -> float:
    """Pine `ta.pivotlow(left, right)` — pivot low 감지 (pivothigh의 대칭)."""
    slot = state.buffers.setdefault(node_id, {"lows": []})
    lows = slot["lows"]
    lows.append(low)

    window = left + right + 1
    if len(lows) < window:
        return float("nan")
    if len(lows) > 2 * window:
        lows[:] = lows[-2 * window :]

    pivot_idx = len(lows) - right - 1
    pivot_val = lows[pivot_idx]

    for i in range(max(0, pivot_idx - left), pivot_idx):
        if lows[i] <= pivot_val:
            return float("nan")
    for i in range(pivot_idx + 1, len(lows)):
        if lows[i] <= pivot_val:
            return float("nan")
    return float(pivot_val)


# -------- change -------------------------------------------------------


def ta_change(state: IndicatorState, node_id: int, source: float, length: int = 1) -> float:
    """source - source[length]."""
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length + 1))
    buf.append(source)
    if len(buf) <= length:
        return float("nan")
    return source - buf[0]


def ta_stdev(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """슬라이딩 윈도우 표준편차 (모집단). warmup < length → nan."""
    if length <= 0:
        return float("nan")
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    if _is_na(source):
        buf.append(source)
        return float("nan")
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    m = sum(buf) / length
    var = sum((x - m) ** 2 for x in buf) / length
    return math.sqrt(var)


def ta_variance(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """슬라이딩 윈도우 분산 (모집단). warmup < length → nan."""
    if length <= 0:
        return float("nan")
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    if _is_na(source):
        buf.append(source)
        return float("nan")
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    m = sum(buf) / length
    return sum((x - m) ** 2 for x in buf) / length


# -------- Parabolic SAR (Wilder 1978) ----------------------------------
#
# Sprint X1+X3 W2 — i3_drfx 의 ta.sar 호출 dispatch 공백 해소.
# 기존 stdlib pattern (state.buffers[node_id] dict slot) 을 mirror 하기 위해
# SarState dataclass + ta_sar 함수 두 가지를 모두 제공:
#   - 단위 테스트는 SarState 를 직접 만들어 ta_sar(state, h, l, ...) 호출
#   - dispatcher 는 state.buffers.setdefault(node_id, SarState()) 로 slot 보관 후 위임


@dataclass
class SarState:
    """Parabolic SAR 계산 상태 — bar-by-bar 유지.

    최초 1 bar 는 추세 결정용 warmup (nan 반환).
    두 번째 bar 에서 prev_high 와 비교해 추세 방향 + 초기 SAR/EP 결정.

    Wilder 규칙상 SAR 는 직전 2 bar 의 low(uptrend)/high(downtrend) 보다
    공격적이지 않아야 하므로 prev/prev2 두 단계 high/low 를 보관.
    """

    is_initialized: bool = False
    is_uptrend: bool = True  # True=long bias, False=short bias
    sar: float = float("nan")
    extreme_point: float = float("nan")  # uptrend=max high, downtrend=min low
    acceleration_factor: float = 0.02
    prev_high: float = float("nan")  # t-1
    prev_low: float = float("nan")  # t-1
    prev2_high: float = float("nan")  # t-2 (Wilder 2-bar clamp)
    prev2_low: float = float("nan")  # t-2


def ta_sar(
    state: SarState,
    high: float,
    low: float,
    start: float = 0.02,
    increment: float = 0.02,
    maximum: float = 0.2,
) -> float:
    """Wilder Parabolic SAR — bar-by-bar 계산.

    알고리즘:
    - 추세별 SAR_t+1 = SAR_t + AF * (EP - SAR_t)
    - SAR 는 직전 2 bar 의 low(uptrend)/high(downtrend) 를 침범하지 않도록 clamp
    - low(uptrend) 또는 high(downtrend) 가 SAR 를 침범 → 반전 → 새 SAR = 직전 EP
    - EP 갱신 시마다 AF += increment (단, ≤ maximum)

    nan high/low 는 nan 반환 + 상태 갱신 생략 (다음 bar 에 영향 없음).
    """
    if math.isnan(high) or math.isnan(low):
        return float("nan")

    # warmup: 첫 valid bar — 상태만 기록
    if not state.is_initialized:
        state.prev_high = high
        state.prev_low = low
        state.is_initialized = True
        return float("nan")

    # 두 번째 valid bar: 추세 결정 + 초기 SAR/EP 설정
    if math.isnan(state.sar):
        if high >= state.prev_high:
            state.is_uptrend = True
            state.sar = state.prev_low  # uptrend 초기 SAR = 이전 low
            state.extreme_point = max(high, state.prev_high)
        else:
            state.is_uptrend = False
            state.sar = state.prev_high  # downtrend 초기 SAR = 이전 high
            state.extreme_point = min(low, state.prev_low)
        state.acceleration_factor = start
        # prev2 ← bar t-1 (init step 직전), prev ← 이번 bar (bar 1)
        state.prev2_high = state.prev_high
        state.prev2_low = state.prev_low
        state.prev_high = high
        state.prev_low = low
        return state.sar

    # 일반 bar: Wilder 규칙
    prev_sar = state.sar
    prev_ep = state.extreme_point
    af = state.acceleration_factor

    if state.is_uptrend:
        new_sar = prev_sar + af * (prev_ep - prev_sar)
        # Wilder 규칙: SAR 는 직전 2 bar 의 low 보다 높을 수 없음.
        # (이번 bar 의 low 는 반전 판정용 — clamp 대상이 아님)
        new_sar = min(new_sar, state.prev_low)
        if not math.isnan(state.prev2_low):
            new_sar = min(new_sar, state.prev2_low)
        # 반전 체크: 이번 low 가 새 SAR 를 침범
        if low < new_sar:
            # 하락 반전: 새 추세의 SAR = 직전 EP, EP = 이번 low
            state.is_uptrend = False
            state.sar = prev_ep
            state.extreme_point = low
            state.acceleration_factor = start
        else:
            state.sar = new_sar
            if high > prev_ep:
                state.extreme_point = high
                state.acceleration_factor = min(af + increment, maximum)
    else:
        new_sar = prev_sar + af * (prev_ep - prev_sar)
        # Wilder 규칙: SAR 는 직전 2 bar 의 high 보다 낮을 수 없음.
        new_sar = max(new_sar, state.prev_high)
        if not math.isnan(state.prev2_high):
            new_sar = max(new_sar, state.prev2_high)
        # 반전 체크: 이번 high 가 새 SAR 를 침범
        if high > new_sar:
            state.is_uptrend = True
            state.sar = prev_ep
            state.extreme_point = high
            state.acceleration_factor = start
        else:
            state.sar = new_sar
            if low < prev_ep:
                state.extreme_point = low
                state.acceleration_factor = min(af + increment, maximum)

    state.prev2_high = state.prev_high
    state.prev2_low = state.prev_low
    state.prev_high = high
    state.prev_low = low
    return state.sar


# -------- 유틸 (na / nz) ------------------------------------------------


def fn_na(x: Any) -> bool:
    """Pine `na(x)` — nan 여부 반환."""
    return _is_na(x)


def fn_nz(x: Any, replacement: Any = 0.0) -> Any:
    """Pine `nz(x, y=0)` — x가 na면 y 반환."""
    if _is_na(x):
        return replacement
    return x


# -------- Sprint 58 BL-241 — 신규 TA 함수 --------------------------------


def ta_wma(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """Weighted Moving Average — weights 1,2,...,length (최신 = length)."""
    length = int(length)  # Pine may pass float (e.g. tclength/2)
    if length <= 0:
        return float("nan")
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    if _is_na(source):
        return float("nan")
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    denom = length * (length + 1) / 2
    return sum((i + 1) * v for i, v in enumerate(buf)) / denom


def ta_cross(state: IndicatorState, node_id: int, a: float, b: float) -> bool:
    """True when a crosses b in either direction (crossover or crossunder)."""
    slot = state.buffers.setdefault(node_id, {"prev_a": float("nan"), "prev_b": float("nan")})
    prev_a, prev_b = slot["prev_a"], slot["prev_b"]
    slot["prev_a"], slot["prev_b"] = a, b
    if _is_na(prev_a) or _is_na(prev_b) or _is_na(a) or _is_na(b):
        return False
    return (prev_a <= prev_b and a > b) or (prev_a >= prev_b and a < b)


def ta_mom(state: IndicatorState, node_id: int, source: float, length: int = 1) -> float:
    """Momentum = source - source[length]."""
    length = int(length)  # Pine may pass float
    if length <= 0:
        return float("nan")
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length + 1))
    if _is_na(source):
        return float("nan")
    buf.append(source)
    if len(buf) < length + 1:
        return float("nan")
    return float(buf[-1]) - float(buf[0])


def fn_fixnan(state: IndicatorState, node_id: int, source: float) -> float:
    """최근 non-nan 값 반환 (source가 nan이면 이전 유효값 유지)."""
    slot = state.buffers.setdefault(node_id, {"last_valid": float("nan")})
    if not _is_na(source):
        slot["last_valid"] = source
    return float(slot["last_valid"])


def _wma_from_deque(buf: deque[float], source: float, length: int) -> float:
    """ta_hma 내부용 WMA helper — 독립 deque 사용."""
    if _is_na(source):
        return float("nan")
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    denom = length * (length + 1) / 2
    return float(sum((i + 1) * v for i, v in enumerate(buf)) / denom)


def ta_hma(state: IndicatorState, node_id: int, source: float, length: int) -> float:
    """Hull Moving Average = WMA(2*WMA(src, n/2) - WMA(src, n), floor(sqrt(n)))."""
    length = int(length)  # Pine may pass float
    if length <= 0:
        return float("nan")
    half_len = max(1, length // 2)
    sqrt_len = max(1, math.floor(math.sqrt(length)))
    slot = state.buffers.setdefault(
        node_id,
        {
            "h": deque(maxlen=half_len),
            "f": deque(maxlen=length),
            "s": deque(maxlen=sqrt_len),
        },
    )
    wma_half = _wma_from_deque(slot["h"], source, half_len)
    wma_full = _wma_from_deque(slot["f"], source, length)
    diff = float("nan") if (_is_na(wma_half) or _is_na(wma_full)) else 2.0 * wma_half - wma_full
    return _wma_from_deque(slot["s"], diff, sqrt_len)


def ta_bb(
    state: IndicatorState,
    node_id: int,
    source: float,
    length: int,
    mult: float = 2.0,
) -> list[float]:
    """Bollinger Bands. Returns [upper, basis, lower]."""
    length = int(length)  # Pine may pass float
    nan = float("nan")
    if length <= 0:
        return [nan, nan, nan]
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    if _is_na(source):
        return [nan, nan, nan]
    buf.append(source)
    if len(buf) < length:
        return [nan, nan, nan]
    mean = sum(buf) / length
    variance = sum((x - mean) ** 2 for x in buf) / length
    std = math.sqrt(variance)
    return [mean + mult * std, mean, mean - mult * std]


def ta_obv(
    state: IndicatorState,
    node_id: int,
    close: float,
    volume: float,
    prev_close: float,
) -> float:
    """On Balance Volume (누적). prev_close=nan인 경우 첫 바로 간주."""
    slot = state.buffers.setdefault(node_id, {"obv": 0.0})
    if _is_na(close) or _is_na(volume):
        return float(slot["obv"])
    if not _is_na(prev_close):
        if close > prev_close:
            slot["obv"] += volume
        elif close < prev_close:
            slot["obv"] -= volume
    return float(slot["obv"])


# -------- 디스패치 테이블 ----------------------------------------------


@dataclass
class StdlibDispatcher:
    """Pine 함수명 → 호출 로직. Interpreter가 Call 노드 해석 시 사용.

    call-site 상태 격리:
    - _prefix_stack: 현재 user function 호출 체인의 call-site prefix 스택.
    - push/pop으로 user function 진입/탈출 시 관리.
    - _scoped_node_id: prefix + node_id의 해시 조합으로 call-site별 독립 state slot 생성.
    """

    state: IndicatorState = field(default_factory=IndicatorState)

    def __post_init__(self) -> None:
        self._prefix_stack: list[str] = []

    def push_call_prefix(self, prefix: str) -> None:
        """user function 진입 시 call-site prefix push."""
        self._prefix_stack.append(prefix)

    def pop_call_prefix(self) -> None:
        """user function 탈출 시 call-site prefix pop."""
        if self._prefix_stack:
            self._prefix_stack.pop()

    def _scoped_node_id(self, node_id: int) -> int:
        """call-site prefix를 반영한 scoped node id.

        prefix_stack이 비어있으면 원래 node_id 그대로 반환 (top-level 호출).
        user function 내부라면 prefix hash와 node_id를 조합해 독립 slot 생성.
        """
        if not self._prefix_stack:
            return node_id
        prefix_hash = hash("::".join(self._prefix_stack)) & 0xFFFF_FFFF
        return (prefix_hash << 32) | (node_id & 0xFFFF_FFFF)

    def call(
        self,
        func_name: str,
        node_id: int,
        args: list[Any],
        *,
        high: float = float("nan"),
        low: float = float("nan"),
        close_prev: float = float("nan"),
    ) -> Any:
        """func_name이 ta.* 또는 na/nz이면 호출, 아니면 KeyError.

        scoped_id: user function 호출 체인의 call-site prefix를 반영한 node_id.
        top-level 호출 시 원래 node_id 그대로 사용 (backward compatible).
        """
        scoped_id = self._scoped_node_id(node_id)
        if func_name == "ta.sma":
            return ta_sma(self.state, scoped_id, *args)
        if func_name == "ta.ema":
            return ta_ema(self.state, scoped_id, *args)
        if func_name == "ta.rma":
            return ta_rma(self.state, scoped_id, *args)
        if func_name == "ta.atr":
            (length,) = args
            return ta_atr(self.state, scoped_id, length, high, low, close_prev)
        if func_name == "ta.rsi":
            return ta_rsi(self.state, scoped_id, *args)
        if func_name == "ta.crossover":
            return ta_crossover(self.state, scoped_id, *args)
        if func_name == "ta.crossunder":
            return ta_crossunder(self.state, scoped_id, *args)
        if func_name == "ta.highest":
            return ta_highest(self.state, scoped_id, *args)
        if func_name == "ta.lowest":
            return ta_lowest(self.state, scoped_id, *args)
        if func_name == "ta.change":
            length = args[1] if len(args) >= 2 else 1
            return ta_change(self.state, scoped_id, args[0], int(length))
        if func_name == "ta.stdev":
            return ta_stdev(self.state, scoped_id, args[0], int(args[1]))
        if func_name == "ta.variance":
            return ta_variance(self.state, scoped_id, args[0], int(args[1]))
        if func_name == "ta.pivothigh":
            # Pine: pivothigh(left, right) OR pivothigh(source, left, right)
            if len(args) == 2:
                left, right = int(args[0]), int(args[1])
                src_val = high
            else:
                src_val = args[0] if not _is_na(args[0]) else high
                left, right = int(args[1]), int(args[2])
            return ta_pivothigh(self.state, scoped_id, left, right, src_val)
        if func_name == "ta.pivotlow":
            if len(args) == 2:
                left, right = int(args[0]), int(args[1])
                src_val = low
            else:
                src_val = args[0] if not _is_na(args[0]) else low
                left, right = int(args[1]), int(args[2])
            return ta_pivotlow(self.state, scoped_id, left, right, src_val)
        if func_name == "ta.sar":
            # Pine: ta.sar(start, increment, maximum) — high/low 는 dispatcher 가 주입
            start = float(args[0]) if len(args) >= 1 else 0.02
            increment = float(args[1]) if len(args) >= 2 else 0.02
            maximum = float(args[2]) if len(args) >= 3 else 0.2
            sar_state = self.state.buffers.setdefault(scoped_id, SarState())
            return ta_sar(sar_state, high, low, start, increment, maximum)
        if func_name == "ta.barssince":
            return ta_barssince(self.state, scoped_id, args[0])
        if func_name == "ta.valuewhen":
            # args: (cond, source, occurrence)
            occ = int(args[2])
            return ta_valuewhen(self.state, scoped_id, args[0], args[1], occ)
        if func_name == "na":
            return fn_na(args[0] if args else float("nan"))
        if func_name == "nz":
            if len(args) == 1:
                return fn_nz(args[0])
            return fn_nz(args[0], args[1])
        # Sprint 58 BL-241 — 신규 TA 함수
        if func_name == "ta.wma":
            return ta_wma(self.state, scoped_id, *args)
        if func_name == "ta.cross":
            return ta_cross(self.state, scoped_id, *args)
        if func_name == "ta.mom":
            return ta_mom(self.state, scoped_id, *args)
        if func_name == "fixnan":
            return fn_fixnan(self.state, scoped_id, *args)
        if func_name == "ta.hma":
            return ta_hma(self.state, scoped_id, *args)
        if func_name == "ta.bb":
            return ta_bb(self.state, scoped_id, *args)
        if func_name == "ta.obv":
            # attribute 경로 (interpreter._eval_attribute) 외 함수 호출 경로도 지원
            return ta_obv(self.state, scoped_id, *args)
        raise KeyError(func_name)
