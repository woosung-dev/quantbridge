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


def ta_rsi(
    state: IndicatorState, node_id: int, source: float, length: int
) -> float:
    """Relative Strength Index (Wilder's smoothing 근사)."""
    if length <= 0:
        return float("nan")
    slot = state.buffers.setdefault(node_id, {
        "prev_src": float("nan"),
        "avg_gain": float("nan"),
        "avg_loss": float("nan"),
        "warmup_gain": [],
        "warmup_loss": [],
    })
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


def ta_highest(
    state: IndicatorState, node_id: int, source: float, length: int
) -> float:
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length))
    buf.append(source)
    if len(buf) < length:
        return float("nan")
    return max(buf)


def ta_lowest(
    state: IndicatorState, node_id: int, source: float, length: int
) -> float:
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
    """
    slot = state.buffers.setdefault(node_id, {"history": []})
    hist: list[float] = slot["history"]
    cond_bool = bool(cond) if not _is_na(cond) else False
    if cond_bool and source is not None and not _is_na(source):
        hist.insert(0, float(source))
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
        highs[:] = highs[-2 * window:]

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
        lows[:] = lows[-2 * window:]

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


def ta_change(
    state: IndicatorState, node_id: int, source: float, length: int = 1
) -> float:
    """source - source[length]."""
    buf: deque[float] = state.buffers.setdefault(node_id, deque(maxlen=length + 1))
    buf.append(source)
    if len(buf) <= length:
        return float("nan")
    return source - buf[0]


def ta_stdev(
    state: IndicatorState, node_id: int, source: float, length: int
) -> float:
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


def ta_variance(
    state: IndicatorState, node_id: int, source: float, length: int
) -> float:
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


# -------- 유틸 (na / nz) ------------------------------------------------


def fn_na(x: Any) -> bool:
    """Pine `na(x)` — nan 여부 반환."""
    return _is_na(x)


def fn_nz(x: Any, replacement: Any = 0.0) -> Any:
    """Pine `nz(x, y=0)` — x가 na면 y 반환."""
    if _is_na(x):
        return replacement
    return x


# -------- 디스패치 테이블 ----------------------------------------------


@dataclass
class StdlibDispatcher:
    """Pine 함수명 → 호출 로직. Interpreter가 Call 노드 해석 시 사용."""

    state: IndicatorState = field(default_factory=IndicatorState)

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
        """func_name이 ta.* 또는 na/nz이면 호출, 아니면 KeyError."""
        if func_name == "ta.sma":
            return ta_sma(self.state, node_id, *args)
        if func_name == "ta.ema":
            return ta_ema(self.state, node_id, *args)
        if func_name == "ta.atr":
            (length,) = args
            return ta_atr(self.state, node_id, length, high, low, close_prev)
        if func_name == "ta.rsi":
            return ta_rsi(self.state, node_id, *args)
        if func_name == "ta.crossover":
            return ta_crossover(self.state, node_id, *args)
        if func_name == "ta.crossunder":
            return ta_crossunder(self.state, node_id, *args)
        if func_name == "ta.highest":
            return ta_highest(self.state, node_id, *args)
        if func_name == "ta.lowest":
            return ta_lowest(self.state, node_id, *args)
        if func_name == "ta.change":
            length = args[1] if len(args) >= 2 else 1
            return ta_change(self.state, node_id, args[0], int(length))
        if func_name == "ta.stdev":
            return ta_stdev(self.state, node_id, args[0], int(args[1]))
        if func_name == "ta.variance":
            return ta_variance(self.state, node_id, args[0], int(args[1]))
        if func_name == "ta.pivothigh":
            # Pine: pivothigh(left, right) OR pivothigh(source, left, right)
            if len(args) == 2:
                left, right = int(args[0]), int(args[1])
                src_val = high
            else:
                src_val = args[0] if not _is_na(args[0]) else high
                left, right = int(args[1]), int(args[2])
            return ta_pivothigh(self.state, node_id, left, right, src_val)
        if func_name == "ta.pivotlow":
            if len(args) == 2:
                left, right = int(args[0]), int(args[1])
                src_val = low
            else:
                src_val = args[0] if not _is_na(args[0]) else low
                left, right = int(args[1]), int(args[2])
            return ta_pivotlow(self.state, node_id, left, right, src_val)
        if func_name == "ta.barssince":
            return ta_barssince(self.state, node_id, args[0])
        if func_name == "ta.valuewhen":
            # args: (cond, source, occurrence)
            occ = int(args[2])
            return ta_valuewhen(self.state, node_id, args[0], args[1], occ)
        if func_name == "na":
            return fn_na(args[0] if args else float("nan"))
        if func_name == "nz":
            if len(args) == 1:
                return fn_nz(args[0])
            return fn_nz(args[0], args[1])
        raise KeyError(func_name)
