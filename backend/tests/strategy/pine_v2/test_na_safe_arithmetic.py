# BL-374 — pine_v2 산술/math 도메인 오류의 na 시맨틱 회귀 테스트 (TradingView 정합 + BL-362 fail-closed 유지)
"""BL-374 na-safe arithmetic.

TradingView Pine 의미상 0 나눗셈 / 음수 sqrt / log 도메인 / overflow 는 모두
`na` (float nan) 다. 기존 인터프리터는 raw `ZeroDivisionError` / `ValueError` /
`OverflowError` 를 던졌고, 이들은 `PineRuntimeError` 가 아니라서 event_loop 의
`except PineRuntimeError` 가 못 잡아 run_historical 밖으로 escape →
백테스트 FAILED + 라이브 세션 비활성(BL-362) 을 유발했다.

본 테스트는 다음을 잠근다.
- (a) 산술/math 도메인 예외 → na (조용히, 백테스트 계속 진행).
- (b) overflow → na (inf 가 아님), bigint/complex 무음 오염 차단.
- (c) 정상 산술은 그대로 동작 (회귀 0).
- (d) 중간 bar 0 나눗셈에도 full 백테스트 완주 (BL-362 회귀 오라클).
- (e) 진짜 logic 오류(미지원 함수)·TypeError 는 여전히 전파 (fail-closed 유지).
- (f) scope 밖 na 사이징은 무음 오염 0 — "깨끗한 실패" (BL-376 이연 안전성 근거).
- (g) na 정규화는 숫자 산술에만 — 문자열 % 등 타입 오용은 fail-closed 유지 (G2 over-catch 차단).
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError, _na_safe


def ohlcv(n: int = 5) -> pd.DataFrame:
    """단조 증가 close 기반 OHLCV. open=prev_close → bar i>=1 에서 close>open 성립."""
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


def _last_x(expr: str) -> float:
    """`x = <expr>` 를 indicator 로 실행하고 마지막 bar 의 x 값을 반환."""
    src = f'//@version=5\nindicator("t")\nx = {expr}\n'
    r = run_historical(src, ohlcv())
    assert r.errors == [], f"unexpected errors: {r.errors}"
    return r.var_series["x"][-1]


# ---------------------------------------------------------------------------
# (a)/(b) 도메인 / 0-나눗셈 / overflow / bigint / complex → na
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    [
        "1.0 / 0.0",  # ZeroDivisionError (float div)
        "5 % 0",  # ZeroDivisionError (integer modulo)
        "math.sqrt(-1)",  # ValueError: math domain error
        "math.log(0)",  # ValueError: math domain error
        "math.log(-1)",  # ValueError: math domain error
        "math.log10(0)",  # ValueError: math domain error
        "math.exp(1000)",  # OverflowError: math range error
        "math.pow(10, 1000)",  # OverflowError (math.pow) — bigint 무음오염 차단
        "math.pow(-1.0, 0.5)",  # ValueError (math.pow 음수밑 분수승) — complex 무음오염 차단
    ],
)
def test_domain_and_div_errors_are_na(expr: str) -> None:
    result = _last_x(expr)
    assert isinstance(result, float)
    assert math.isnan(result), f"{expr!r} → expected nan, got {result!r}"


def test_overflow_is_na_not_inf() -> None:
    """overflow 는 +inf 가 아니라 na 여야 한다 (inf 는 하류 지표를 조용히 오염)."""
    result = _last_x("math.exp(1000)")
    assert math.isnan(result)
    assert not math.isinf(result)


def test_pow_bigint_is_na_not_int() -> None:
    """math.pow(10, 1000) 이 1001자리 int 로 무음 오염되지 않고 na (math.pow 전환 효과)."""
    result = _last_x("math.pow(10, 1000)")
    assert isinstance(result, float)
    assert math.isnan(result)


def test_two_arg_log_base_one_is_na() -> None:
    """math.log(x, base=1) → log(x)/log(1)=x/0 → ZeroDivisionError → na (2-인자 형태도 래핑)."""
    assert math.isnan(_last_x("math.log(8.0, 1.0)"))
    assert math.isnan(_last_x("math.log(8.0, 1)"))


# ---------------------------------------------------------------------------
# _na_safe 화이트박스 — complex 가드 + 예외 분류 직접 잠금 (vacuous 방지)
# ---------------------------------------------------------------------------


def test_na_safe_helper_contract() -> None:
    """_na_safe 헬퍼 화이트박스 잠금.

    Pine 문법에 `**` 파워 연산자가 없어(pynescript SyntaxError) complex 결과를 내는
    binop 경로는 소스로 도달 불가하고, math.pow 는 음수밑 분수승에서 complex 가 아니라
    ValueError 를 던진다. 따라서 _na_safe 의 `isinstance(result, complex)` 가드는
    소스 경로로 절대 닿지 않는 방어선이다. 헬퍼를 직접 호출해 분기를 모두 잠근다.
    """
    # complex 결과 → na (`**` 연산자가 내는 음수밑 분수승)
    assert math.isnan(_na_safe(lambda: (-2.0) ** 0.5))
    # ArithmeticError (ZeroDivision / Overflow) → na
    assert math.isnan(_na_safe(lambda: 1.0 / 0.0))
    assert math.isnan(_na_safe(lambda: math.exp(1000)))
    # ValueError (domain error) → na
    assert math.isnan(_na_safe(lambda: math.sqrt(-1.0)))
    # 정상 값 passthrough (가짜로 삼키지 않음)
    assert _na_safe(lambda: 42.0) == 42.0
    # TypeError 는 안 잡음 → 전파 (fail-closed)
    with pytest.raises(TypeError):
        _na_safe(lambda: "a" + 1)  # type: ignore[operator]

    # PineRuntimeError(RuntimeError) 는 안 잡음 → 전파 (fail-closed)
    def _raise_pine() -> float:
        raise PineRuntimeError("boom")

    with pytest.raises(PineRuntimeError):
        _na_safe(_raise_pine)


# ---------------------------------------------------------------------------
# 추가 엣지 — 런타임 산출 0 나눗셈 / na 전파 / float modulo
# ---------------------------------------------------------------------------


def test_zero_over_zero_binop_chain_is_na() -> None:
    """런타임 산출 0 으로 나누기 (상수 아닌 표현식 경로)."""
    # (close - close) / (close - close) = 0.0 / 0.0 → ZeroDivisionError → nan
    assert math.isnan(_last_x("(close - close) / (close - close)"))


def test_float_modulo_by_zero_is_na() -> None:
    assert math.isnan(_last_x("5.0 % 0.0"))


def test_na_safe_result_propagates_through_outer_op() -> None:
    """_na_safe 가 만든 na 가 상위 연산으로 정상 전파 (operand-na 조기반환과 결합)."""
    assert math.isnan(_last_x("(1.0 / 0.0) + 5.0"))
    assert math.isnan(_last_x("100.0 + math.sqrt(-1)"))
    assert math.isnan(_last_x("math.log(0) * 2.0"))


def test_na_operand_short_circuits_before_compute() -> None:
    """피연산자 na 조기 반환 경로가 _na_safe 도입 후에도 보존 (binop + math 양쪽)."""
    # close[5] 는 5-bar 시리즈에서 na → na / 5.0 = na (compute 호출 전 조기 반환)
    assert math.isnan(_last_x("close[5] / 5.0"))
    # math.* 의 any(_is_na(a)) 조기 반환도 보존
    assert math.isnan(_last_x("math.sqrt(close[5])"))


# ---------------------------------------------------------------------------
# (c) 정상 산술은 영향 없음
# ---------------------------------------------------------------------------


def test_normal_arithmetic_unaffected() -> None:
    assert _last_x("10.0 / 2.0") == 5.0
    assert _last_x("math.sqrt(16.0)") == 4.0
    pow_val = _last_x("math.pow(2.0, 10.0)")
    assert pow_val == 1024.0
    assert isinstance(pow_val, float)  # math.pow 는 int 가 아닌 float 반환
    assert _last_x("math.log(1.0)") == 0.0
    assert _last_x("math.exp(0.0)") == 1.0
    assert _last_x("math.log10(1000.0)") == pytest.approx(3.0)
    assert _last_x("math.log(math.exp(1.0))") == pytest.approx(1.0)
    assert _last_x("7 % 3") == 1  # 정상 정수 모듈로 (raw 통과)
    assert _last_x("7.0 % 2.0") == 1.0  # 정상 float 모듈로


# ---------------------------------------------------------------------------
# (d) BL-362 회귀 오라클 — 중간 bar 0-나눗셈에도 full 백테스트 완주
# ---------------------------------------------------------------------------


def test_full_backtest_completes_with_div_by_zero_midstream() -> None:
    source = (
        "//@version=5\n"
        'strategy("bt")\n'
        "denom = close - close\n"  # 항상 0
        "x = 1.0 / denom\n"  # 매 bar ZeroDivisionError → na
        "plot(x)\n"
        "if close > open\n"
        '    strategy.entry("L", strategy.long)\n'
    )
    r = run_historical(source, ohlcv(20))
    assert r.errors == [], f"divergence swallowed escape: {r.errors}"
    assert r.bars_processed == 20
    assert len(r.var_series["x"]) == 20
    assert all(math.isnan(v) for v in r.var_series["x"]), r.var_series["x"]


# ---------------------------------------------------------------------------
# (e) 진짜 logic 오류 / TypeError 는 여전히 전파 (fail-closed 유지)
# ---------------------------------------------------------------------------


def test_logic_errors_still_propagate() -> None:
    """미지원 math 함수 = PineRuntimeError 전파 유지. _na_safe 는 안 삼킴."""
    src = '//@version=5\nindicator("t")\nx = math.not_a_real_function(1)\n'
    with pytest.raises(PineRuntimeError):
        run_historical(src, ohlcv())


def test_unsupported_attribute_call_still_propagates() -> None:
    """math.* 가 아닌 미지원 호출도 fail-closed 유지 (raw 예외 흡수가 과확장 안 됨)."""
    src = '//@version=5\nindicator("t")\nx = foo.bar(1)\n'
    with pytest.raises(PineRuntimeError):
        run_historical(src, ohlcv())


def test_type_errors_still_propagate() -> None:
    """타입 오류(문자열/숫자)는 na 로 삼키지 않음 — TypeError 는 _na_safe 비대상."""
    src = '//@version=5\nindicator("t")\nx = "abc" / 2.0\n'
    with pytest.raises(TypeError):
        run_historical(src, ohlcv())


# ---------------------------------------------------------------------------
# (f) 한계 잠금 — na qty 사이징은 무음 오염 없이 깨끗이 실패 (BL-376 이연 안전성)
# ---------------------------------------------------------------------------


def test_na_qty_fails_cleanly_no_silent_corruption() -> None:
    """strategy.entry(qty=na) 가 실제 체결되면 백테스트는 깨끗이 실패 — 절대 status=='ok' 아님.

    BL-376 으로 이연한 qty=na 시나리오의 안전성 근거. 무음으로 잘못된 결과
    (status=='ok' + nan PnL)를 내지 않고, _compute_metrics 의 Decimal 비교에서
    decimal.InvalidOperation 으로 깨끗이 실패(status='error')한다.

    주의: 진입이 *실제로 체결*돼야 이 안전성이 발현된다. 매 bar `close > open` 이
    참인 시계열(ohlcv 의 단조 증가 open)을 써 bar 1+ 에서 진입을 체결시킨다.
    """
    source = (
        "//@version=5\n"
        'strategy("s")\n'
        "q = close[100]\n"  # 20-bar 시리즈에서 na (범위 밖)
        "if close > open\n"
        '    strategy.entry("L", strategy.long, qty=q)\n'
    )
    outcome = run_backtest_v2(source, ohlcv(20), BacktestConfig())
    # 무음 오염 0 잠금: 절대 status=="ok" 가 아니어야 한다 (깨끗한 실패).
    assert outcome.status != "ok", f"na qty silently produced ok outcome: {outcome.status}"
    assert outcome.status == "error"
    assert "InvalidOperation" in str(outcome.error or "")


# ---------------------------------------------------------------------------
# (g) na 정규화는 숫자 산술에만 — 문자열 % 등 타입 오용은 fail-closed 유지 (G2 over-catch 차단)
# ---------------------------------------------------------------------------


def test_string_modulo_misuse_stays_fail_closed() -> None:
    """문자열 % (잘못된 포맷)는 na 로 삼키지 않고 ValueError 로 전파.

    _eval_binop 의 _na_safe 래핑을 모든 연산자에 무차별 적용하면 operator.mod 의
    문자열 포맷 ValueError(`"%" % 2` → incomplete format)까지 na 로 흡수돼 타입 오용이
    silent 화된다 (G2 codex challenge 발견). na 정규화는 숫자 피연산자에만 적용되어
    문자열 오용은 fail-closed 로 전파됨을 잠근다.
    """
    src = '//@version=5\nindicator("t")\nx = "%" % 2\n'
    with pytest.raises(ValueError):
        run_historical(src, ohlcv())


def test_string_concat_unaffected() -> None:
    """정상 문자열 연산(비-숫자 Add)은 numeric 가드로 그대로 동작 (회귀 0)."""
    src = '//@version=5\nindicator("t")\nx = "a" + "b"\n'
    r = run_historical(src, ohlcv())
    assert r.errors == []
    assert r.var_series["x"][-1] == "ab"
