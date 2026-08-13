"""Sprint 21 Phase A.1 — interpreter alias ordering (codex G.0 P1 #1 + #4).

User-defined function 이 v4 alias / stdlib 보다 먼저 dispatch 되어야 함.
사용자가 `abs(x) => x + 1000` 정의 시 alias `abs → math.abs` 가 압도하지 않아야
correctness bug 차단.

dotted method dispatch (예: `strategy.entry()`, `box.set_top()`) 는 plain
identifier 만 처리하는 user_function check 와 무관하게 기존 dispatch path 로
라우팅 (`"." not in name` guard 의무).

근거: codex G.0 round 1 P1 #1 + #4 — coverage `_CALL_RE` 의 user_defs 제외 로직은
preflight 만 보호. runtime 에서 alias 가 먼저 적용되어 user function 미사용.
i3_drfx / s3_rsid corpus 가 통과한 이유는 우연히 alias 와 충돌하는 함수명을 사용 안 했기 때문.
"""

from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.compat import parse_and_run_v2


def _make_min_ohlcv(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [10] * n,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="1min"),
    )


def test_user_defined_abs_overrides_v4_alias() -> None:
    """user `abs(x) =>` 정의 시 v4 alias `abs → math.abs` 압도 차단."""
    pine = """\
//@version=5
strategy("AbsCollision", overlay=true)

abs(x) => x + 1000

var float result = na
result := abs(-5)
"""
    df = _make_min_ohlcv(n=3)
    out = parse_and_run_v2(pine, df, strict=True)
    assert out.track == "S"
    assert out.historical is not None
    rs = out.historical
    series = list(rs.var_series.get("result", []))
    assert series, (
        f"var_series['result'] empty — keys={sorted(rs.var_series.keys())}; "
        f"final_state keys={sorted(rs.final_state.keys())}"
    )
    last = series[-1]
    # user_defined: -5 + 1000 = 995. v4 alias 압도 시: math.abs(-5) = 5.
    assert last == 995, (
        f"expected user-defined abs() result 995 (sentinel x+1000), got {last} "
        f"(likely v4 alias `abs → math.abs` override = 5)"
    )


def test_user_defined_max_overrides_v4_alias() -> None:
    """user `max(a, b) =>` 정의 시 v4 alias `max → math.max` 압도 차단."""
    pine = """\
//@version=5
strategy("MaxCollision", overlay=true)

max(a, b) => a + b + 7000

var float result = na
result := max(2.0, 3.0)
"""
    df = _make_min_ohlcv(n=3)
    out = parse_and_run_v2(pine, df, strict=True)
    assert out.historical is not None
    rs = out.historical
    series = list(rs.var_series.get("result", []))
    assert series, "result series empty"
    last = series[-1]
    # user_defined: 2 + 3 + 7000 = 7005. v4 alias 압도 시: math.max(2,3) = 3.
    assert last == 7005.0, (
        f"expected user-defined max() result 7005.0, got {last} "
        f"(likely v4 alias `max → math.max` override = 3.0)"
    )


def test_dotted_call_unaffected_by_user_function_check() -> None:
    """`strategy.entry()` 같은 dotted call 이 plain user_function check 와 무관.

    dotted name 은 (`"." not in name`) guard 로 user_function check 를 우회 →
    rendering / strategy / method dispatch path 로 정상 라우팅.
    """
    pine = """\
//@version=5
strategy("DottedDispatch", overlay=true)

if bar_index == 1
    strategy.entry("L", strategy.long, qty=1)
"""
    df = _make_min_ohlcv(n=4)
    out = parse_and_run_v2(pine, df, strict=True)
    assert out.historical is not None
    assert out.historical.strategy_state is not None
    state = out.historical.strategy_state
    # entry 가 정상 dispatch 됐다면 trade 1건 또는 position_size 변경
    has_trade = bool(getattr(state, "trades", []))
    pos_size = getattr(state, "position_size", 0)
    assert has_trade or pos_size != 0, (
        f"strategy.entry() dotted dispatch failed: "
        f"trades={getattr(state, 'trades', [])}, position_size={pos_size}"
    )
