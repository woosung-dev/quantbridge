"""B-3: User function call-site별 ta.* 상태 격리 테스트.

동일 user function을 두 call-site에서 서로 다른 source로 호출 시
각자 독립 EMA 상태를 가져야 함.

a = calcEma(close, 14)
b = calcEma(open, 14)
→ a != b (서로 다른 source → 다른 EMA 결과)
"""

from __future__ import annotations

import math

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.stdlib import StdlibDispatcher


def _make_ohlcv(n: int = 30) -> pd.DataFrame:
    """close != open 이 되도록 의도적으로 다른 값 사용."""
    closes = [100.0 + i * 0.5 for i in range(n)]
    opens = [closes[0]] + [closes[i - 1] + 0.2 for i in range(1, n)]
    return pd.DataFrame(
        {
            "open": opens,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [100.0] * n,
        }
    )


# -------- StdlibDispatcher prefix 단위 테스트 ---------------------------


def test_scoped_node_id_no_prefix() -> None:
    """prefix_stack 비어있으면 원래 node_id 그대로."""
    disp = StdlibDispatcher()
    assert disp._scoped_node_id(42) == 42


def test_scoped_node_id_with_prefix() -> None:
    """prefix 존재 시 scoped id != original id."""
    disp = StdlibDispatcher()
    disp.push_call_prefix("call_site_1")
    scoped = disp._scoped_node_id(42)
    assert scoped != 42


def test_different_prefixes_produce_different_ids() -> None:
    """서로 다른 prefix → 서로 다른 scoped id."""
    disp = StdlibDispatcher()
    disp.push_call_prefix("site_a")
    id_a = disp._scoped_node_id(42)
    disp.pop_call_prefix()

    disp.push_call_prefix("site_b")
    id_b = disp._scoped_node_id(42)
    disp.pop_call_prefix()

    assert id_a != id_b


def test_push_pop_symmetry() -> None:
    """push/pop 후 prefix_stack이 원래 상태로 복원."""
    disp = StdlibDispatcher()
    disp.push_call_prefix("x")
    disp.pop_call_prefix()
    assert len(disp._prefix_stack) == 0
    # 빈 stack → scoped_id == original
    assert disp._scoped_node_id(99) == 99


def test_pop_empty_stack_safe() -> None:
    """빈 stack에서 pop해도 에러 없음."""
    disp = StdlibDispatcher()
    disp.pop_call_prefix()  # 에러 없어야 함


# -------- E2E: 두 call-site EMA 독립성 ----------------------------------


def test_user_fn_two_callsites_independent_ema() -> None:
    """동일 함수 두 call-site에서 다른 source → EMA 결과 독립.

    calcEma(close, 14) != calcEma(open, 14) — 30 bars 실행 후 확인.
    """
    source = """//@version=5
indicator("isolation_test")
calcEma(src, length) =>
    ta.ema(src, length)

a = calcEma(close, 14)
b = calcEma(open, 14)
"""
    ohlcv = _make_ohlcv(30)
    result = run_historical(source, ohlcv)

    a_series = result.var_series.get("a", [])
    b_series = result.var_series.get("b", [])

    assert len(a_series) == 30
    assert len(b_series) == 30

    # warmup 완료 후(14 bar 이후) 값이 서로 다른지 확인
    # (close와 open이 다르므로 EMA도 달라야 함)
    non_nan_pairs = [
        (a, b) for a, b in zip(a_series, b_series) if not (math.isnan(a) or math.isnan(b))
    ]
    assert len(non_nan_pairs) > 0, "EMA warmup 완료 후 non-nan 값이 없음"

    # 적어도 하나는 a != b
    any_different = any(abs(a - b) > 1e-10 for a, b in non_nan_pairs)
    assert any_different, "두 call-site EMA가 동일 — 상태 격리 실패"


def test_user_fn_same_source_same_result() -> None:
    """동일 source를 두 call-site에서 호출하면 동일 결과 (격리는 되되 값은 같음)."""
    source = """//@version=5
indicator("same_source_test")
calcEma(src, length) =>
    ta.ema(src, length)

a = calcEma(close, 5)
b = calcEma(close, 5)
"""
    ohlcv = _make_ohlcv(20)
    result = run_historical(source, ohlcv)

    a_series = result.var_series.get("a", [])
    b_series = result.var_series.get("b", [])

    non_nan_pairs = [
        (a, b) for a, b in zip(a_series, b_series) if not (math.isnan(a) or math.isnan(b))
    ]
    assert len(non_nan_pairs) > 0

    # 같은 source → 값 동일해야 함 (격리 후에도)
    for a, b in non_nan_pairs:
        assert abs(a - b) < 1e-10, f"같은 source인데 다름: {a} vs {b}"


# -------- [BL-846] 같은 줄의 두 호출 ------------------------------------


def _one_line_vs_two_line_z(length: int = 5, bars: int = 30) -> tuple[list[float], list[float]]:
    """같은 두 호출을 한 줄 / 두 줄에 두고 각각의 `z` 시리즈를 돌려준다."""
    body = f"""f(src) =>
    ta.ema(src, {length})
"""
    one_line = f"""//@version=5
indicator("one_line")
{body}
z = f(close) + f(open)
"""
    two_line = f"""//@version=5
indicator("two_line")
{body}
a = f(close)
b = f(open)
z = a + b
"""
    ohlcv = _make_ohlcv(bars)
    return (
        run_historical(one_line, ohlcv).var_series.get("z", []),
        run_historical(two_line, ohlcv).var_series.get("z", []),
    )


def test_two_callsites_on_one_line_do_not_share_ta_state() -> None:
    """[BL-846] 줄바꿈은 의미를 바꾸지 않는다 — 한 줄 두 호출도 상태가 독립이어야 한다.

    ★수리 전에는 red 였다. 호출부 격리 키가 `node_id or lineno` 였는데 `pynescript` 의 `Call`
    에는 `node_id` 가 없고(`_attributes` = lineno/col_offset/end_*), `lineno` 는 1 이상이라
    항상 truthy 라 `id(call_node)` 폴백에 **영원히 도달하지 않았다**. 그래서 한 줄의 두 호출이
    같은 prefix → `StdlibDispatcher._scoped_node_id` 가 같은 슬롯을 내줬고 `ta.ema` 버퍼가
    뒤섞여 **둘 다 틀린 값**이 나왔다(예외도 경고도 없다).

    ★단언을 `col_offset` 이 아니라 **의미**로 세운 이유 — 키 구성을 다음 사람이 바꿔도
    계약이 살아남게 하려는 것이다.
    ★기존 `test_user_fn_two_callsites_independent_ema`(두 줄)는 수리 전에도 초록이었으므로
    **음성 대조**다. 그리고 위쪽 `test_different_prefixes_produce_different_ids` 는
    `StdlibDispatcher` 를 직접 부르는 단위 테스트라 **인터프리터가 실제로 서로 다른 prefix 를
    만드는지**를 안 잰다 — 이 결함이 정확히 그 사각에 있었다.
    """
    one_line_z, two_line_z = _one_line_vs_two_line_z()

    assert len(one_line_z) == len(two_line_z) == 30

    non_nan = [
        (o, t) for o, t in zip(one_line_z, two_line_z) if not (math.isnan(o) or math.isnan(t))
    ]
    assert len(non_nan) > 0, "warmup 후 non-nan 값이 없다 — 이 단언은 무증거다"

    mismatches = [(i, o, t) for i, (o, t) in enumerate(non_nan) if abs(o - t) > 1e-9]
    assert not mismatches, (
        f"한 줄 두 호출이 두 줄과 다른 값을 낸다 — ta.* 상태 슬롯 공유: {mismatches[:3]}"
    )


def test_two_callsites_on_one_line_are_not_identical_to_each_other() -> None:
    """양성 대조 — 위 테스트가 「둘 다 똑같이 망가져서」 통과하지 않는지 잰다.

    서로 다른 source 를 주므로 두 호출의 EMA 는 달라야 하고, 따라서 `z = f(close) + f(open)`
    는 `2 * f(close)` 와 달라야 한다. 이 대조가 없으면 두 경로가 **같은 방식으로 틀려도**
    위 단언이 초록이다.
    """
    source = """//@version=5
indicator("one_line_positive_control")
f(src) =>
    ta.ema(src, 5)

z = f(close) + f(open)
w = f(close) + f(close)
"""
    result = run_historical(source, _make_ohlcv(30))
    z_series = result.var_series.get("z", [])
    w_series = result.var_series.get("w", [])

    non_nan = [(a, b) for a, b in zip(z_series, w_series) if not (math.isnan(a) or math.isnan(b))]
    assert len(non_nan) > 0
    assert any(abs(a - b) > 1e-9 for a, b in non_nan), (
        "f(close)+f(open) 이 f(close)+f(close) 와 같다 — 호출부 격리가 통째로 죽었다"
    )
