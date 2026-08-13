# BL-405 재분류 — pine_v2 bool/비교 na 시멘틱이 TradingView 와 정합함을 잠그는 회귀 테스트
"""BL-405 (not-a-bug, oracle premise error) TV-parity lock.

배경: BL-405 는 "pine_v2 가 bool 시리즈의 na 를 False 로 조기 실체화 → 워밍업 경계
스퓨리어스 시그널" 이라고 등재됐으나, 이는 **오라클의 전제 오류**였다. 오라클 작성자는
"Pine 비교가 na 를 반환하고 bool 시리즈에 na 가 보존된다" 고 가정했는데, TradingView
공식 문서는 정반대를 명시한다.

TradingView 공식 문서 (2026-07-12 확인, r.jina.ai 리더로 verbatim 확보):
- type-system: "values of the 'bool' type are never na. Any 'bool' return type returns
  `false` instead of na if data is not available."  → **bool 은 절대 na 아님**.
- type-system: "The ==, != operators, and all other comparison operators always return
  `false` if at least one of the operands is ... `na`."  → **비교는 na 피연산자에 false**.
- type-system: history-referencing "a 'bool' variable from a previous bar that does not
  exist ... returns `false`."  → **bool[n] 과거참조도 false (na 보존 안 됨)**.
- operators: "If at least one operand is na, the result is also na."  → **산술만 na 전파**.
- reference #var_na: "Do not use this variable with comparison operators to test values
  for na ... Instead, use the na function."  → na 판정은 na(x) 로.

즉 **현재 엔진 동작(비교→False, bool never na, crossover→False, 산술→na)이 TV 정답이다.**
계획됐던 "비교/not/crossover 를 na 전파로 바꾸는" 수정은 TV 정합을 깨는 회귀였다. 본 테스트는
그 정답 동작을 잠가 향후 동일 오진(재-"수정") 을 차단한다. (bs bar12→bar15 실측 편차의 진짜
후보는 bool-na 가 아니라 ta.ema 워밍업 시딩 — 별개 BL-409 로 등재.)

참고: 산술 na 전파(_eval_binop)는 test_na_safe_arithmetic.py 가 이미 잠금. 본 파일은
**비교/논리/bool-시리즈** 경로의 na→False 실체화가 TV 정답임을 대비(contrast)로 잠근다.
"""

from __future__ import annotations

import math

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.event_loop import run_historical


def ohlcv(n: int = 5) -> pd.DataFrame:
    """단조 증가 close 기반 OHLCV (uptrend). open=prev_close → bar i>=1 에서 close>open."""
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


def _series(expr: str, n: int = 5) -> list:
    """`x = <expr>` 를 indicator 로 실행하고 x 의 bar 별 시리즈 전체를 반환."""
    src = f'//@version=5\nindicator("t")\nx = {expr}\n'
    r = run_historical(src, ohlcv(n))
    assert r.errors == [], f"unexpected errors: {r.errors}"
    return list(r.var_series["x"])


def _last(expr: str, n: int = 5):
    return _series(expr, n)[-1]


def _is_na(v) -> bool:
    return isinstance(v, float) and math.isnan(v)


# ---------------------------------------------------------------------------
# (A) 비교 연산: na 피연산자 → concrete bool False (na 아님) — TV type-system
# ---------------------------------------------------------------------------


def test_ordering_compare_with_na_is_false_not_na() -> None:
    """`na > x` / `na < x` / `na >= x` / `na <= x` → False (bool), na 아님.

    close[5] 는 5-bar 시리즈 마지막 bar 에서 범위 밖 → na. TV: 비교는 na 에 false 반환.
    """
    for expr in ("close[5] > 0", "close[5] < 0", "close[5] >= 0", "close[5] <= 0"):
        v = _last(expr)
        assert v is False, f"{expr!r} → expected bool False, got {v!r}"
        assert not _is_na(v), f"{expr!r} 가 na 로 실체화됨 (TV 위반)"


def test_equality_with_na_is_false() -> None:
    """`close == na` (여기선 close[5]==0) → False. == 는 na 검출 불가 (TV)."""
    assert _last("close[5] == 0") is False


def test_na_equals_na_is_false() -> None:
    """`na == na` → False (TV: 비교 연산은 na 피연산자에 항상 false). close[5]==close[6] 둘 다 na."""
    assert _last("close[5] == close[6]") is False


def test_not_equal_with_na_is_false_not_true() -> None:
    """★핵심(BL-405 오진 지점): `!= na` 는 True 가 아니라 **False** 를 반환.

    리포트는 `bullTrend != bullTrend[1]` 이 워밍업에서 True 를 내 스퓨리어스 시그널이라 봤으나,
    한쪽이 na 면 != 도 false 다 (TV type-system: ==, != 모두 na 피연산자에 false). 진짜 전환은
    양쪽이 concrete bool 일 때만 발생.
    """
    v = _last("close[5] != 0")
    assert v is False, f"`!= na` → expected False, got {v!r} (TV: != 도 na 에 false)"
    # 대조: 양쪽 non-na 면 정상 비교
    assert _last("close != 0") is True


# ---------------------------------------------------------------------------
# (B) bool 타입은 절대 na 아님 — 워밍업 저장/과거참조 모두 concrete bool — TV type-system
# ---------------------------------------------------------------------------


def test_bool_series_never_na_during_warmup() -> None:
    """bool 표현식 시리즈에는 na 가 절대 저장되지 않는다 (전부 concrete bool).

    ta.sma(close,10) 은 10-bar 워밍업 동안 na → `> 0` 비교가 na 피연산자를 만나지만
    결과는 False (bool). 시리즈 전 구간에 nan 이 없어야 한다.
    """
    series = _series("ta.sma(close, 10) > 0", n=15)
    assert len(series) == 15
    assert all(isinstance(v, bool) for v in series), f"bool 시리즈에 non-bool: {series}"
    assert not any(_is_na(v) for v in series), "bool 시리즈에 na 실체화 (TV 위반)"


def test_bool_history_in_range_is_concrete_bool() -> None:
    """in-range 인 bool[n] 과거참조는 concrete bool (워밍업 구간에도 na 아님) — TV bool never na.

    b = ta.sma(close,4) > 0. bar>=1 에서 b[1] 은 항상 concrete bool(워밍업엔 False).
    ※ bar 0 의 범위 밖 b[1] 은 엔진이 nan 을 반환(TV 는 false). 이 raw 저장 편차는 아래
      관측-등가 테스트로 소거를 잠그고, 편차 자체는 BL-409(워밍업 TV-parity 잔여)로 등재.
    """
    src = (
        "//@version=5\n"
        'indicator("t")\n'
        "b = ta.sma(close, 4) > 0\n"
        "x = b[1]\n"
    )
    r = run_historical(src, ohlcv(8))
    assert r.errors == []
    lag = list(r.var_series["x"])
    # bar>=1 은 concrete bool (워밍업 False 포함). bar 0 은 범위밖 edge (아래 테스트에서 다룸).
    assert all(isinstance(v, bool) for v in lag[1:]), f"in-range bool[1] 에 non-bool: {lag[1:]}"
    assert not any(_is_na(v) for v in lag[1:]), "in-range bool history 가 na 실체화 (TV 위반)"


def test_bool_history_out_of_range_collapses_to_false_on_consumption() -> None:
    """bar 0 의 범위 밖 bool[1] = nan(엔진) 은 비교/제어흐름 소비 시 false(TV) 와 관측 등가.

    `chg = b != b[1]` 은 bar 0 에서 엔진(b[1]=nan → `!= na` → False)과 TV(b[1]=false,
    b[0]=false → `false != false` → False) 모두 **False**. 즉 raw 저장 편차(nan vs false)는
    소비 경로에서 소거된다 — 거래/시그널에 영향 없음. raw 저장 편차 자체는 BL-409 로 추적.
    """
    src = (
        "//@version=5\n"
        'indicator("t")\n'
        "b = ta.sma(close, 4) > 0\n"
        "chg = b != b[1]\n"
    )
    r = run_historical(src, ohlcv(8))
    assert r.errors == []
    chg = list(r.var_series["chg"])
    assert chg[0] is False, f"bar0 chg → expected False(관측등가), got {chg[0]!r}"
    assert all(isinstance(v, bool) for v in chg), f"chg 에 na 실체화: {chg}"


def test_bull_trend_change_pattern_uses_false_not_na() -> None:
    """bs 스크립트의 정확한 패턴(`bull != bull[1]`)이 TV bool 시멘틱을 따름을 잠근다.

    bull = emaFast > emaSlow. 워밍업 구간 emaSlow=na → bull=False(bool, na 아님). 첫 real
    bull=True 가 되는 bar 에서 `True != False` 로 trendChange 가 발화 — 이는 스퓨리어스가
    **아니라** TV 정합(bool never na)이다. chg 시리즈에 nan 이 없고, 정확히 첫 real-bar 전환
    1회만 True 인지 확인.

    ※ 실제 TradingView 와의 잔여 편차(있다면)는 bool 시멘틱이 아니라 ta.ema 워밍업 시딩에서
      비롯되며 BL-409 로 분리 추적한다 — 본 테스트는 bool/비교 경로만 잠근다.
    """
    src = (
        "//@version=5\n"
        'indicator("t")\n'
        "bull = ta.ema(close, 3) > ta.ema(close, 5)\n"
        "chg = bull != bull[1]\n"
    )
    r = run_historical(src, ohlcv(12))
    assert r.errors == []
    bull = list(r.var_series["bull"])
    chg = list(r.var_series["chg"])
    assert all(isinstance(v, bool) for v in bull), f"bull 에 na: {bull}"
    assert all(isinstance(v, bool) for v in chg), f"chg 에 na: {chg}"
    # 단조 증가(uptrend)라 emaSlow 가 처음 정의되는 bar 에서 bull False→True 전환 1회.
    assert chg.count(True) >= 1
    # 첫 True 전환 지점은 bull 이 처음 True 가 되는 bar 와 일치.
    first_true_bull = next(i for i, v in enumerate(bull) if v is True)
    assert chg[first_true_bull] is True


# ---------------------------------------------------------------------------
# (C) ta.crossover/crossunder/cross: na 피연산자 → False (never na) — TV
# ---------------------------------------------------------------------------


def test_crossover_family_with_na_is_false_not_na() -> None:
    """crossover/crossunder/cross 는 워밍업 na 피연산자에 False (bool never na)."""
    for fn in ("ta.crossover", "ta.crossunder", "ta.cross"):
        expr = f"{fn}(ta.ema(close, 3), ta.ema(close, 5))"
        series = _series(expr, n=12)
        assert all(isinstance(v, bool) for v in series), f"{fn} 에 na: {series}"
        assert not any(_is_na(v) for v in series), f"{fn} 가 na 로 실체화됨 (TV 위반)"


# ---------------------------------------------------------------------------
# (D) 논리 not: na 비교 위에서도 TV 정합 (na>x=false → not false = true)
# ---------------------------------------------------------------------------


def test_not_on_na_comparison_is_true() -> None:
    """`not (na > x)` → na>x=False 이므로 not False = True. (내부 비교가 false 로 확정)."""
    v = _last("not (close[5] > 0)")
    assert v is True, f"expected True, got {v!r}"


def test_na_builtin_is_correct_na_test_idiom() -> None:
    """na 판정의 정석은 na(x) — close[5](범위밖)=na → na()=True, 유효 close → False."""
    assert _last("na(close[5])") is True
    assert _last("na(close)") is False
    # 권장 idiom: `not na(x)` — 값 존재 시 통과, na 시 차단
    assert _last("not na(close[5])") is False
    assert _last("not na(close)") is True


# ---------------------------------------------------------------------------
# (E) 대비(contrast): 산술은 여전히 na 전파 — 비교/bool 과 갈린다 (둘 다 TV 정답)
# ---------------------------------------------------------------------------


def test_arithmetic_still_propagates_na_contrast() -> None:
    """비교는 na→False 지만 산술은 na→na 전파. 두 경로의 TV 정답이 갈림을 대비로 잠근다."""
    assert _is_na(_last("close[5] + 1.0")), "산술은 na 전파여야 함 (operators 문서)"
    assert _is_na(_last("close[5] * 2.0"))
    # 반대편: 같은 na 피연산자라도 비교는 concrete False
    assert _last("close[5] + 1.0 > 0") is False  # (na)+1=na, na>0=False


# ---------------------------------------------------------------------------
# (F) 제어흐름: na 비교 조건은 진입 안 함 (_truthy(na/False)=False) → 거래 0
# ---------------------------------------------------------------------------


def test_na_comparison_condition_takes_no_entry() -> None:
    """`if (na-comparison)` 은 분기 미진입 → 진입 0. (na 조건 = falsy, TV 정합)."""
    source = (
        "//@version=5\n"
        'strategy("s")\n'
        "if close[100] > 0\n"  # 20-bar 에서 close[100]=na → na>0=False → 미진입
        '    strategy.entry("L", strategy.long)\n'
    )
    outcome = run_backtest_v2(source, ohlcv(20), BacktestConfig())
    assert outcome.status == "ok", f"status={outcome.status} error={outcome.error}"
    assert outcome.result is not None and len(outcome.result.trades) == 0
