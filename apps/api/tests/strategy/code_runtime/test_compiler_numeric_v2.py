"""수동 수학 fixture만 검사한다. oracle·모델 산출물·실 VM·공통 broker는 사용하지 않는다.

닫힌 compiler의 신뢰된 테스트 산출물을 함수/AST 단위로 검사하며 제품의 호스트 실행
우회 경로를 만들지 않는다. TypeScript native 일치 증거는 별도 gVisor 검사에서 얻는다.
"""

import math
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.strategy.code_runtime.compiler import compile_strategy
from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def spec(indicators=(), **conditions):
    return {
        "title": "manual numeric v2 fixture",
        "warmup_bars": 1,
        "indicators": list(indicators),
        "long_entry": {"op": "false"},
        "short_entry": {"op": "false"},
        **conditions,
    }


def condition(op, left, right):
    return {"op": op, "left": {"series": left}, "right": {"series": right}}


def bars(price, count=40):
    return [
        {
            "index": i,
            "timestamp": pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(hours=i),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 1.0,
        }
        for i in range(count)
    ]


def python_values(definition, rows):
    namespace = {}
    # 임의 코드 입력을 받지 않는다. 위의 수동 typed fixture만 컴파일한다.
    exec(compile_strategy(definition, "python"), namespace)
    state, values, actions = {}, [], []
    for index, row in enumerate(rows):
        actions.append(
            namespace["on_bar"](
                {"bar": row, "history": rows[: index + 1], "position": {"direction": "long"}}, state
            )["action"]
        )
        values.append({key: series[-1] for key, series in state["_qb"]["outputs"].items()})
    return values, actions, namespace


def pine_values(definition, rows):
    tree = parse_to_ast(compile_strategy(definition, "pine"))
    frame = pd.DataFrame(rows)
    context = BarContext(frame)
    store = PersistentStore()
    interpreter = Interpreter(context, store)
    values = []
    while context.advance():
        store.begin_bar()
        interpreter.reset_transient()
        interpreter.begin_bar_snapshot()
        interpreter.execute(tree)
        store.commit_bar()
        interpreter.append_var_series()
        current = {}
        current["_long"] = interpreter._resolve_name("qb_long")
        current["_short"] = interpreter._resolve_name("qb_short")
        for item in definition["indicators"]:
            outputs = {
                "macd": ("value", "signal"),
                "stochastic": ("value", "signal"),
                "regression": ("value", "slope", "upper", "lower"),
                "aroon": ("up", "down"),
            }.get(item["kind"], ("value",))
            for output in outputs:
                name = f"qb_{item['id']}_{output}"
                current[f"{item['id']}.{output}"] = interpreter._resolve_name(name)
        values.append(current)
    return values


@pytest.mark.parametrize("language", ["python", "pine"])
@pytest.mark.parametrize("price", [0.007, 184.1857053266093, 100000.1])
def test_constant_windows_preserve_mean_smoothing_spread_and_regression(language, price):
    indicators = [
        {"id": kind + str(n), "kind": kind, "length": n}
        for kind in ("sma", "ema", "stdev", "cci", "regression", "atr", "rsi")
        for n in (3, 8)
    ] + [
        {"id": "macd", "kind": "macd", "length": 3, "slow": 8, "signal": 3},
        {"id": "ema12", "kind": "ema", "length": 12},
        {"id": "ema26", "kind": "ema", "length": 26},
        {"id": "macd26", "kind": "macd", "length": 12, "slow": 26, "signal": 9},
    ]
    definition = spec(indicators, long_invalidation=condition("lt", "sma3", "sma8"))
    rows = bars(price)
    if language == "python":
        values, actions, namespace = python_values(definition, rows)
        assert actions == ["hold"] * len(rows)
        assert namespace["_qb_mean"]([price] * 3) == price
    else:
        values = pine_values(definition, rows)
    for row in values[10:]:
        for n in (3, 8):
            assert row[f"sma{n}.value"] == row[f"ema{n}.value"] == price
            assert row[f"stdev{n}.value"] == row[f"cci{n}.value"] == row[f"atr{n}.value"] == 0
            assert (
                row[f"regression{n}.value"]
                == row[f"regression{n}.upper"]
                == row[f"regression{n}.lower"]
                == price
            )
            assert row[f"regression{n}.slope"] == 0
            assert row[f"rsi{n}.value"] == 100
        assert row["macd.value"] == row["macd.signal"] == 0
    for n in (3, 8):
        assert all(math.isnan(row[f"sma{n}.value"]) for row in values[: n - 1])
        assert all(math.isnan(row[f"rsi{n}.value"]) for row in values[:n])
    for row in values[34:]:
        assert row["ema12.value"] == row["ema26.value"] == price
        assert row["macd26.value"] == row["macd26.signal"] == 0


def test_finite_predicates_and_crosses_share_the_same_relative_band():
    _, _, namespace = python_values(spec(), bars(100, 1))
    compare = namespace["_qb_compare"]
    assert compare(0, 1e-12) == 0
    assert compare(0, math.nextafter(1e-12, math.inf)) == -1
    for price in (0.007, 184.1857053266093):
        assert compare(price, math.nextafter(price, math.inf)) == 0
        epsilon = 1e-12 * max(1, abs(price))
        assert compare(price, price + 2 * epsilon) == -1
        assert compare(price, price - 2 * epsilon) == 1
    for value in (math.nan, math.inf, -math.inf):
        assert compare(value, 0) is None and compare(0, value) is None
    definition = spec(
        long_entry=condition("cross_up", "close", "open"),
        short_entry=condition("cross_down", "close", "open"),
    )
    rows = bars(100, 5)
    for row, delta in zip(rows, (0.5e-10, 0.8e-10, 2e-10, 0.5e-10, -2e-10), strict=True):
        row["close"] += delta
    namespace = {}
    exec(compile_strategy(definition, "python"), namespace)
    state, actions = {}, []
    for i, row in enumerate(rows):
        actions.append(
            namespace["on_bar"](
                {"bar": row, "history": rows[: i + 1], "position": {"direction": "flat"}}, state
            )["action"]
        )
    assert actions == ["hold", "hold", "long", "hold", "short"]
    observed = pine_values(definition, rows)
    assert [bool(row["_long"]) for row in observed] == [False, False, True, False, False]
    assert [bool(row["_short"]) for row in observed] == [False, False, False, False, True]
    invalid = spec(long_entry=condition("gt", "close", "open"))
    for value in (math.nan, math.inf, -math.inf):
        row = bars(1.0, 1)
        row[0]["close"] = value
        assert pine_values(invalid, row)[0]["_long"] is False


@pytest.mark.parametrize("language", ["python", "pine"])
def test_na_window_and_exact_small_positive_denominators_are_not_constant_zero(language):
    definition = spec(
        [
            {"id": "stoch", "kind": "stochastic", "length": 2, "slow": 3, "signal": 1},
            {"id": "wpr", "kind": "williams_r", "length": 2},
            {"id": "mfi", "kind": "mfi", "length": 2},
            {"id": "aroon", "kind": "aroon", "length": 2},
        ]
    )
    flat = bars(1.0, 8)
    positive = bars(1.0, 8)
    for row in positive:
        row.update(high=1 + 2**-45, close=1 + 2**-46)
    if language == "python":
        invalid = python_values(definition, flat)[0]
        finite = python_values(definition, positive)[0]
    else:
        invalid, finite = pine_values(definition, flat), pine_values(definition, positive)
    assert all(
        math.isnan(row["stoch.value"])
        and math.isnan(row["wpr.value"])
        and math.isnan(row["mfi.value"])
        for row in invalid
    )
    assert finite[-1]["stoch.value"] == 50 and finite[-1]["wpr.value"] == -50
    assert finite[-1]["aroon.up"] == finite[-1]["aroon.down"] == 100
    # 유효 raw 값 사이의 0분모 NA도 smoothing 창에서 제거하거나 상수 0으로 위장하지 않는다.
    mixed = bars(1.0, 10)
    for i, row in enumerate(mixed):
        if i not in (4, 5):
            row.update(high=1 + 2**-45, close=1 + 2**-46)
    observed = (
        python_values(definition, mixed)[0]
        if language == "python"
        else pine_values(definition, mixed)
    )
    assert all(math.isnan(row["stoch.value"]) for row in observed[5:8])
    assert observed[8]["stoch.value"] == 50


@pytest.mark.parametrize("language", ["python", "pine"])
def test_raw_extreme_selection_does_not_use_predicate_epsilon(language):
    definition = spec([{"id": "aroon", "kind": "aroon", "length": 2}])
    rows = bars(1.0, 3)
    rows[0]["high"] += 2**-45
    values = (
        python_values(definition, rows)[0]
        if language == "python"
        else pine_values(definition, rows)
    )
    assert values[-1]["aroon.up"] == 0
    assert values[-1]["aroon.down"] == 100


@pytest.mark.parametrize("language", ["python", "pine"])
@pytest.mark.parametrize("price", [0.007, 184.1857053266093])
def test_positive_constant_true_range_rma_remains_constant(language, price):
    definition = spec([{"id": "atr", "kind": "atr", "length": 3}])
    rows = bars(price, 12)
    for row in rows:
        row["high"] = 2 * price
    values = (
        python_values(definition, rows)[0]
        if language == "python"
        else pine_values(definition, rows)
    )
    assert all(math.isnan(row["atr.value"]) for row in values[:2])
    assert all(row["atr.value"] == price for row in values[2:])


def test_typescript_numeric_helpers_pass_the_installed_strict_compiler(tmp_path):
    root = Path(__file__).resolve().parents[5]
    compiler = root / "apps/web/node_modules/typescript/bin/tsc"
    if not compiler.is_file():
        pytest.skip("고정 TypeScript compiler가 설치되지 않았습니다")
    source = tmp_path / "numeric.ts"
    source.write_text(
        compile_strategy(spec([{"id": "ema", "kind": "ema", "length": 3}]), "typescript")
    )
    # 타입 검사만 수행한다. 생성된 JavaScript를 host에서 실행하지 않는다.
    result = subprocess.run(
        [
            str(compiler),
            "--strict",
            "--target",
            "ES2022",
            "--noEmit",
            "--skipLibCheck",
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("language", ["python", "pine"])
def test_stable_update_preserves_real_memory_and_nonconstant_population_statistics(language):
    definition = spec(
        [
            {"id": "ema", "kind": "ema", "length": 3},
            {"id": "sd", "kind": "stdev", "length": 3},
            {"id": "reg", "kind": "regression", "length": 3},
        ]
    )
    rows = bars(1.0, 7)
    for row in rows[3:]:
        row.update(open=2.0, high=2.0, low=2.0, close=2.0)
    values = (
        python_values(definition, rows)[0]
        if language == "python"
        else pine_values(definition, rows)
    )
    assert [row["ema.value"] for row in values[2:]] == [1, 1.5, 1.75, 1.875, 1.9375]
    linear = bars(1.0, 3)
    for i, row in enumerate(linear, 1):
        row.update(open=float(i), high=float(i), low=float(i), close=float(i))
    result = (
        python_values(definition, linear)[0][-1]
        if language == "python"
        else pine_values(definition, linear)[-1]
    )
    assert result["sd.value"] == pytest.approx(math.sqrt(2 / 3))
    assert result["reg.value"] == result["reg.upper"] == result["reg.lower"] == 3
    assert result["reg.slope"] == 1
