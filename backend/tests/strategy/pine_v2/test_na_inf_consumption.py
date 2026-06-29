# BL-376 — pine_v2 na/inf 소비 사이트 robustness 회귀 테스트 (BL-374 후속)
"""BL-376 na/inf consumption-site robustness.

BL-374 가 산술/math _생성_ 사이트의 raw 예외를 na 로 정규화했으나, 그 na/inf 가
_소비_ 되는 다음 사이트는 여전히 raw Python 예외를 던져 run_historical 밖으로
escape 했다 (event_loop 의 `except PineRuntimeError` 가 못 잡음 → 백테스트
parse_failed / 라이브 세션 비활성 BL-362). 본 테스트는 세 소비 사이트를 잠근다.

- Site #1 (na/inf → ta.* length): `int(nan)`(ValueError) / `deque(maxlen=nan|inf)`
  (TypeError) / `int(inf)`(OverflowError) → na 결과 정규화 (백테스트 완주).
- Site #2 (na/inf → strategy.entry qty): 라이브 nan→reject 미러 = 주문 skip.
  특히 *미청산* na-qty 진입이 status=='ok' 인데 equity 가 NaN 으로 무음 오염되던
  잔여를 닫는다 (closed 는 InvalidOperation 으로 깨끗이 실패하던 케이스도 skip 으로 통일).
- Site #3 (non-raising inf → math.floor/ceil/round / subscript offset / timestamp):
  `1e308*10.0` → inf → 소비부 OverflowError. inf 를 na 처럼 정규화 (소비부 가드).

검증 원칙: 정상 경로 회귀 0 + PineRuntimeError/TypeError(BL-362 fail-closed) 전파 유지.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.event_loop import RunResult, run_historical


def ohlcv(n: int = 30) -> pd.DataFrame:
    """단조 증가 close. open=prev_close → bar i>=1 에서 close>open 성립 (진입 체결용)."""
    closes = [100.0 + float(i) for i in range(n)]
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame(
        {
            "open": opens,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [100.0] * n,
        }
    )


IND = '//@version=5\nindicator("t")\n'


def _run_ind(body: str, n: int = 30) -> RunResult:
    """indicator 본문을 실행하고 RunResult 반환 (errors==[] 가 곧 '완주')."""
    return run_historical(IND + body, ohlcv(n))


def _last_x(body: str, n: int = 30) -> Any:
    r = _run_ind(body, n)
    assert r.errors == [], f"escape/divergence: {r.errors}"
    return r.var_series["x"][-1]


def _equity_has_nan(result: object) -> bool:
    """equity_curve(pd.Series of Decimal/float) 에 NaN 이 하나라도 있으면 True."""
    series = result.result.equity_curve  # type: ignore[attr-defined]
    for v in series.tolist():
        try:
            f = float(v)
        except (TypeError, ValueError):
            return True
        if math.isnan(f):
            return True
    return False


# 산술로 생성된 na / inf (리터럴 아님 — 실제 BL-374 산술 경로 통과)
LEN_NA = "1.0 / (close - close)"  # 0/0 → na
LEN_INF = "1e308 * 10.0"  # operator.mul, raise 안 함 → inf

# length 를 소비하는 scalar ta.* 호출 (bb 는 list 반환이라 제외 — int(length) 경로는 wma 가 커버)
_LENGTH_CALLS = [
    "ta.sma(close, L)",
    "ta.ema(close, L)",
    "ta.rma(close, L)",
    "ta.atr(L)",
    "ta.rsi(close, L)",
    "ta.highest(close, L)",
    "ta.lowest(close, L)",
    "ta.change(close, L)",
    "ta.mom(close, L)",
    "ta.hma(close, L)",
    "ta.wma(close, L)",
    "ta.stdev(close, L)",
    "ta.variance(close, L)",
]


# ---------------------------------------------------------------------------
# Site #1 — na / inf / 0 / 음수 length → na 결과 (백테스트 완주, raw 예외 escape 0)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("call", _LENGTH_CALLS)
def test_na_length_ta_completes_and_na(call: str) -> None:
    result = _last_x(f"L = {LEN_NA}\nx = {call}\n")
    assert isinstance(result, float) and math.isnan(result), f"{call} → {result!r}"


@pytest.mark.parametrize("call", _LENGTH_CALLS)
def test_inf_length_ta_completes_and_na(call: str) -> None:
    result = _last_x(f"L = {LEN_INF}\nx = {call}\n")
    assert isinstance(result, float) and math.isnan(result), f"{call} → {result!r}"


@pytest.mark.parametrize("call", _LENGTH_CALLS)
@pytest.mark.parametrize("bad_len", ["0", "-3"])
def test_nonpositive_length_ta_na(call: str, bad_len: str) -> None:
    """length<1 → na (highest/lowest 는 가드 없어 deque(maxlen=0) max(empty) ValueError 였음)."""
    result = _last_x(f"L = {bad_len}\nx = {call}\n")
    assert isinstance(result, float) and math.isnan(result), f"{call} L={bad_len} → {result!r}"


def test_valuewhen_na_occurrence_completes() -> None:
    """ta.valuewhen 의 occurrence(int(args[2])) 가 na → 완주 + na."""
    body = f"occ = {LEN_NA}\nx = ta.valuewhen(close > open, close, occ)\n"
    r = _run_ind(body)
    assert r.errors == [], f"escape: {r.errors}"


def test_pivot_na_length_completes() -> None:
    """ta.pivothigh(left, right) 의 int(left/right) 가 na → 완주."""
    body = f"L = {LEN_NA}\nx = ta.pivothigh(L, 2)\n"
    r = _run_ind(body)
    assert r.errors == [], f"escape: {r.errors}"


def test_normal_length_unaffected() -> None:
    """정상 length 는 회귀 0 — 마지막 bar 에서 실제 값 산출."""
    assert _last_x("x = ta.sma(close, 5)\n") == pytest.approx(127.0)  # mean(125..129)
    assert _last_x("x = ta.highest(close, 5)\n") == pytest.approx(129.0)
    assert _last_x("x = ta.lowest(close, 5)\n") == pytest.approx(125.0)
    assert not math.isnan(float(_last_x("x = ta.wma(close, 5)\n")))
    assert not math.isnan(float(_last_x("x = ta.stdev(close, 5)\n")))


# ---------------------------------------------------------------------------
# Site #3 — non-raising inf → math.floor/ceil/round / subscript / timestamp
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fn", ["math.floor", "math.ceil", "math.round"])
def test_inf_math_floor_ceil_round_is_na(fn: str) -> None:
    result = _last_x(f"x = {fn}({LEN_INF})\n")
    assert isinstance(result, float) and math.isnan(result), f"{fn}(inf) → {result!r}"


def test_inf_subscript_offset_is_na() -> None:
    """close[inf] → int(inf) OverflowError 였음 → na (음수/na offset 과 동일 degrade)."""
    result = _last_x(f"o = {LEN_INF}\nx = close[o]\n")
    assert isinstance(result, float) and math.isnan(result)


def test_inf_timestamp_arg_no_crash() -> None:
    """timestamp(inf, ...) 의 int(val) OverflowError → 완주 (degrade)."""
    r = _run_ind(f"y = {LEN_INF}\nx = timestamp(y, 1, 1, 0, 0)\n")
    assert r.errors == [], f"escape: {r.errors}"


def test_normal_floor_ceil_round_unaffected() -> None:
    assert _last_x("x = math.floor(3.7)\n") == 3
    assert _last_x("x = math.ceil(3.2)\n") == 4
    assert _last_x("x = math.round(3.5)\n") == 4


def test_normal_subscript_unaffected() -> None:
    """정상 정수 offset subscript 회귀 0."""
    assert _last_x("x = close[2]\n") == pytest.approx(127.0)  # 30-bar, close[2] at last = 127


def test_nan_math_and_subscript_still_na() -> None:
    """기존 nan 가드(BL-374)도 유지 — inf 가드 추가가 nan 처리를 깨지 않음."""
    assert math.isnan(float(_last_x("x = math.floor(1.0 / (close - close))\n")))
    assert math.isnan(float(_last_x("o = 1.0 / (close - close)\nx = close[o]\n")))


# ---------------------------------------------------------------------------
# Site #2 — na/non-finite qty → 주문 skip (라이브 reject 미러, money-path)
# ---------------------------------------------------------------------------


def test_na_qty_open_entry_skipped_no_silent_corruption() -> None:
    """미청산 na-qty 진입: 이전엔 status=='ok' + equity NaN 무음오염 → skip 후 무오염."""
    source = (
        '//@version=5\nstrategy("s")\n'
        "q = close[100]\n"  # 30-bar 시리즈에서 na (범위 밖)
        "if bar_index == 1\n"
        '    strategy.entry("L", strategy.long, qty=q)\n'  # 진입 후 절대 청산 안 함
    )
    out = run_backtest_v2(source, ohlcv(30), BacktestConfig())
    assert out.status == "ok", f"status={out.status} error={out.error}"
    assert not _equity_has_nan(out), "skip 후에도 equity NaN 잔존"
    assert out.result is not None and len(out.result.trades) == 0


def test_na_qty_closed_entry_skipped_completes() -> None:
    """체결+청산되는 na-qty 진입: 이전엔 InvalidOperation status='error' → skip 후 완주."""
    source = (
        '//@version=5\nstrategy("s")\n'
        "q = close[100]\n"
        "if close > open\n"
        '    strategy.entry("L", strategy.long, qty=q)\n'
    )
    out = run_backtest_v2(source, ohlcv(30), BacktestConfig())
    assert out.status == "ok", f"status={out.status} error={out.error}"
    assert not _equity_has_nan(out)
    assert out.result is not None and len(out.result.trades) == 0


def test_inf_qty_entry_skipped() -> None:
    """inf qty(1e308*10.0)도 non-finite → skip."""
    source = (
        '//@version=5\nstrategy("s")\n'
        "q = 1e308 * 10.0\n"
        "if close > open\n"
        '    strategy.entry("L", strategy.long, qty=q)\n'
    )
    out = run_backtest_v2(source, ohlcv(30), BacktestConfig())
    assert out.status == "ok", f"status={out.status} error={out.error}"
    assert not _equity_has_nan(out)
    assert out.result is not None and len(out.result.trades) == 0


def test_finite_qty_entry_still_executes() -> None:
    """정상 유한 qty 진입은 그대로 체결 — over-skip 회귀 0."""
    source = (
        '//@version=5\nstrategy("s")\n'
        "if close > open\n"
        '    strategy.entry("L", strategy.long, qty=2.0)\n'
        "if close < open\n"
        '    strategy.close("L")\n'
    )
    out = run_backtest_v2(source, ohlcv(30), BacktestConfig())
    assert out.status == "ok"
    assert out.result is not None and len(out.result.trades) >= 1


def test_na_qty_skip_records_warning() -> None:
    """skip 은 silent 가 아니라 warning 을 남긴다 (라이브 reject 와 운영 parity — G1 P2)."""
    source = (
        '//@version=5\nstrategy("s")\n'
        "q = 1.0 / (close - close)\n"
        "if close > open\n"
        '    strategy.entry("L", strategy.long, qty=q)\n'
    )
    r = run_historical(source, ohlcv(10))
    assert r.errors == []
    ss = r.strategy_state
    assert ss is not None
    warns = " ".join(ss.warnings).lower()
    assert "qty" in warns, f"skip 경고 누락: {ss.warnings}"


# ---------------------------------------------------------------------------
# G1 codex 검증 추가분 — RED 갭 보강 + 회귀 잠금
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("length_expr", [LEN_NA, LEN_INF, "0", "-3"])
def test_bb_bad_length_completes(length_expr: str) -> None:
    """ta.bb 도 int(length)/deque(maxlen=) 경로 — na/inf/<1 → 완주 (G1: bb 누락 보강)."""
    r = _run_ind(f"L = {length_expr}\nx = ta.bb(close, L, 2.0)\n")
    assert r.errors == [], f"bb L={length_expr} escape: {r.errors}"


def test_valuewhen_inf_occurrence_completes() -> None:
    """ta.valuewhen occurrence=inf → int(inf) OverflowError 였음 → 완주 (G1 보강)."""
    r = _run_ind(f"occ = {LEN_INF}\nx = ta.valuewhen(close > open, close, occ)\n")
    assert r.errors == [], f"escape: {r.errors}"


def test_decimal_nonfinite_occurrence_and_length_complete() -> None:
    """G2: Decimal('NaN') occurrence/length(input_overrides) 도 escape 안 함.

    valuewhen 의 occurrence 가드가 isinstance(float) 만 보면 Decimal('NaN') 이 int() 에서
    ValueError 로 escape 한다 (G2 codex 실측). float·Decimal 모두 차단해야 한다.
    length 경로(_coerce_length)는 math.isfinite 라 Decimal 이미 안전 — 동반 잠금.
    """
    occ_src = (
        '//@version=4\nindicator("t")\nocc = input(0)\nx = ta.valuewhen(close > open, close, occ)\n'
    )
    r = run_historical(occ_src, ohlcv(20), input_overrides={"occ": Decimal("NaN")}, strict=False)
    assert r.errors == [], f"valuewhen Decimal NaN occ escaped: {r.errors}"
    len_src = '//@version=4\nindicator("t")\nL = input(5)\nx = ta.sma(close, L)\n'
    r2 = run_historical(len_src, ohlcv(20), input_overrides={"L": Decimal("NaN")}, strict=False)
    assert r2.errors == [], f"sma Decimal NaN length escaped: {r2.errors}"


def test_valuewhen_occurrence_zero_still_works() -> None:
    """occurrence=0 (가장 최근) 은 정상값 — non-finite 가드가 0 을 깨면 안 됨 (G1 P1#2 회귀)."""
    r = _run_ind("x = ta.valuewhen(close > open, close, 0)\n")
    assert r.errors == []
    assert not math.isnan(float(r.var_series["x"][-1]))


def test_pivotlow_and_inf_pivot_complete() -> None:
    """ta.pivotlow + inf pivot length 도 완주 (G1: pivotlow/right/inf 누락 보강)."""
    assert _run_ind(f"L = {LEN_NA}\nx = ta.pivotlow(L, 2)\n").errors == []
    assert _run_ind(f"L = {LEN_INF}\nx = ta.pivothigh(2, L)\n").errors == []


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("math.abs(1e308 * 10.0)", math.inf),  # abs(inf) → inf (na 아님)
        ("math.sign(1e308 * 10.0)", 1),  # sign(inf) → 1
        ("math.max(1e308 * 10.0, 5.0)", math.inf),  # max(inf, x) → inf
    ],
)
def test_inf_nonrounding_math_unchanged(expr: str, expected: object) -> None:
    """floor/ceil/round 만 inf→na. abs/sign/max/min 은 inf 통과 유지 (G1 P1#1 over-catch 차단)."""
    result = _last_x(f"x = {expr}\n")
    if expected is math.inf:
        assert isinstance(result, float) and math.isinf(result), f"{expr} → {result!r}"
    else:
        assert result == expected, f"{expr} → {result!r}"


# NOTE (G1 P1#3/#4 deferred → BL-377): non-finite *order/exit price* (entry stop=inf,
# strategy.exit stop/limit/profit=inf) 은 실측상 raw 예외 escape 가 아니라 status='ok' +
# 무-NaN 의 deterministic false-fill 이라 BL-376 harm class(예외 escape) 밖. 라이브는 이미
# _to_decimal(isfinite) 로 drop. 별도 BL-377 로 등재 (non-finite price → wrong fill).
