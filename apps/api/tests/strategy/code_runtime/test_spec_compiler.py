"""명세의 신뢰 경계와 생성 산출물의 실제 parser 계약을 검증한다."""

from __future__ import annotations

import ast
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from tools.research.strategy_catalogue30 import candidates

from src.strategy.code_runtime.compiler import compile_strategy
from src.strategy.code_runtime.spec import StrategySpec, UnsupportedStrategySpec
from src.strategy.pine_v2.coverage import analyze_coverage


@pytest.fixture
def spec_data() -> dict:
    return deepcopy(candidates()[0]["reference_spec"])


@pytest.mark.parametrize(
    "field,value",
    [("raw_code", "danger()"), ("fill_timing", "bar_close"), ("risk_policy", "omit_stops")],
)
def test_spec_rejects_code_injection_and_execution_contract_changes(
    spec_data: dict, field: str, value: str
) -> None:
    spec_data[field] = value
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(spec_data)


@pytest.mark.parametrize(
    "reference",
    [
        {"series": "missing"},
        {"series": "close", "offset": -1},
        {"series": "ema20", "output": "upper"},
        {"constant": float("nan")},
        {"series": "close", "constant": 1},
        {"series": "__import__('os')"},
    ],
)
def test_spec_rejects_invalid_or_future_references(spec_data: dict, reference: dict) -> None:
    spec_data["long_entry"]["left"] = reference
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(spec_data)


def test_duplicate_indicator_id_is_rejected(spec_data: dict) -> None:
    spec_data["indicators"].append(deepcopy(spec_data["indicators"][0]))
    with pytest.raises(ValidationError, match="중복"):
        StrategySpec.model_validate(spec_data)


def test_condition_complexity_is_bounded(spec_data: dict) -> None:
    condition = {"op": "true"}
    for _ in range(13):
        condition = {"op": "not", "children": [condition]}
    spec_data["long_entry"] = condition
    with pytest.raises(ValidationError, match="깊이"):
        StrategySpec.model_validate(spec_data)


def test_catalogue_has_exactly_30_unique_frozen_rule_sets() -> None:
    rows = candidates()
    assert [row["id"] for row in rows] == [f"{n:02}" for n in range(1, 31)]
    json.dumps(rows, allow_nan=False)
    for row in rows:
        assert row["source_status"] == "indicator_definition_project_variant"
        assert all(
            row["rules"][key]
            for key in (
                "long_entry",
                "short_entry",
                "long_invalidation",
                "short_invalidation",
                "risk",
            )
        )
        assert row["source_urls"]
    rows[0]["rules"]["long_entry"] = "changed"
    assert candidates()[0]["rules"]["long_entry"] != "changed"


_REFERENCES = [row for row in candidates() if row["reference_spec"]]


@pytest.mark.parametrize("row", _REFERENCES, ids=lambda row: row["id"])
def test_supported_python_artifacts_compile_without_execution(row: dict) -> None:
    code = compile_strategy(row["reference_spec"], "python")
    tree = ast.parse(code)
    assert any(isinstance(node, ast.FunctionDef) and node.name == "on_bar" for node in tree.body)
    compile(tree, "generated_strategy", "exec")


@pytest.mark.parametrize("row", _REFERENCES, ids=lambda row: row["id"])
def test_pine_export_is_runnable_or_explicitly_unsupported(row: dict) -> None:
    result = analyze_coverage(compile_strategy(row["reference_spec"], "pine"))
    assert result.is_runnable, result.all_unsupported
    assert not result.has_degraded


def test_unsupported_pattern_is_not_replaced_with_simple_signal(spec_data: dict) -> None:
    spec_data["indicators"][0]["kind"] = "supertrend"
    with pytest.raises(UnsupportedStrategySpec, match="supertrend"):
        compile_strategy(spec_data, "python")


def test_title_is_data_and_cannot_add_python_statements(spec_data: dict) -> None:
    spec_data["title"] = '"); __import__("os").system("touch escaped"); #'
    tree = ast.parse(compile_strategy(spec_data, "python"))
    assignment = tree.body[0]
    assert isinstance(assignment, ast.Assign)
    assert ast.literal_eval(assignment.value)["title"] == spec_data["title"]


@pytest.fixture
def real_gvisor() -> None:
    """실제 이미지가 있을 때만 실행하며 호스트 fallback은 만들지 않는다."""
    import shutil
    import subprocess

    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker CLI가 없습니다")
    try:
        result = subprocess.run(
            [docker, "info", "--format", "{{json .Runtimes}}"],
            capture_output=True,
            timeout=10,
            check=True,
        )
        if "runsc" not in json.loads(result.stdout):
            pytest.skip("runsc runtime이 없습니다")
        for image in ("quantbridge-python-runner:local", "quantbridge-typescript-runner:local"):
            subprocess.run(
                [docker, "image", "inspect", image], capture_output=True, timeout=10, check=True
            )
    except (OSError, subprocess.SubprocessError, ValueError):
        pytest.skip("연구용 gVisor 실행 이미지를 사용할 수 없습니다")


@pytest.mark.parametrize("language", ["python", "typescript"])
def test_native_artifact_obeys_external_position_invalidation_and_reversal(
    real_gvisor: None, language: str
) -> None:
    from datetime import UTC, datetime, timedelta

    from src.strategy.code_runtime.sandbox import create_transport

    def ref(value: str | int) -> dict:
        return {"series": value} if isinstance(value, str) else {"constant": value}

    def condition(op: str, right: int) -> dict:
        return {"op": op, "left": ref("close"), "right": ref(right)}

    spec = {
        "title": "external position contract",
        "warmup_bars": 1,
        "long_entry": condition("cross_up", 100),
        "short_entry": condition("cross_down", 100),
        "long_invalidation": condition("lt", 101),
        "short_invalidation": condition("gt", 99),
    }
    transport = create_transport(language, timeout=60)
    try:
        assert transport.exchange(
            {
                "type": "init",
                "protocol": 1,
                "language": language,
                "source": compile_strategy(spec, language),
                "params": {},
            }
        ) == {"ready": 1}
        direction = "flat"
        trace = []
        for i, price in enumerate((100, 102, 100, 99, 100)):
            bar = {
                "index": i,
                "timestamp": (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)).isoformat(),
                "open": str(price),
                "high": str(price + 1),
                "low": str(price - 1),
                "close": str(price),
                "volume": "10",
            }
            intent = transport.exchange(
                {
                    "type": "bar",
                    "bar": bar,
                    "position": {
                        "direction": direction,
                        "size": "0" if direction == "flat" else "0.5",
                        "average_price": None if direction == "flat" else "100",
                    },
                }
            )["intent"]
            trace.append(intent["action"])
            if intent["action"] in ("long", "short"):
                direction = intent["action"]
            elif intent["action"] == "close":
                direction = "flat"
        assert trace == ["hold", "long", "close", "short", "close"]
    finally:
        transport.close()


@pytest.mark.parametrize("language", ["pine", "python", "typescript"])
@pytest.mark.parametrize("kind", ["ema", "rsi", "macd"])
def test_indicator_seed_na_and_both_directions_match_frozen_contract(
    real_gvisor: None, language: str, kind: str
) -> None:
    from datetime import UTC, datetime, timedelta

    import pandas as pd

    from src.strategy.code_runtime.pine import PineSignalTransport
    from src.strategy.code_runtime.sandbox import create_transport

    prices = [90, 90, 150, 50] if kind != "rsi" else [100, 100, 100, 90]
    indicator = {
        "id": "indicator",
        "kind": kind,
        "length": 3 if kind == "ema" else 2,
        "slow": 3,
        "signal": 2,
    }
    threshold = 100 if kind == "ema" else 50 if kind == "rsi" else 0
    spec = {
        "title": "frozen SMA seed and NA contract",
        "warmup_bars": 1,
        "indicators": [indicator],
        "long_entry": {
            "op": "gt",
            "left": {"series": "indicator"},
            "right": {"constant": threshold},
        },
        "short_entry": {
            "op": "lt",
            "left": {"series": "indicator"},
            "right": {"constant": threshold},
        },
    }
    bars = [
        {
            "index": i,
            "timestamp": (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)).isoformat(),
            "open": str(p),
            "high": str(p + 1),
            "low": str(p - 1),
            "close": str(p),
            "volume": "10",
        }
        for i, p in enumerate(prices)
    ]
    data = pd.DataFrame(bars, index=pd.date_range("2026-01-01", periods=4, freq="1h", tz="UTC"))
    transport = (
        PineSignalTransport(data) if language == "pine" else create_transport(language, timeout=60)
    )
    try:
        transport.exchange(
            {
                "type": "init",
                "protocol": 1,
                "language": language,
                "source": compile_strategy(spec, language),
                "params": {},
            }
        )
        direction = "flat"
        trace = []
        for bar in bars:
            action = transport.exchange(
                {
                    "type": "bar",
                    "bar": bar,
                    "position": {
                        "direction": direction,
                        "size": "0" if direction == "flat" else "1",
                        "average_price": None if direction == "flat" else "100",
                    },
                }
            )["intent"]["action"]
            trace.append(action)
            if action in ("long", "short"):
                direction = action
        assert trace == ["hold", "hold", "long", "short"]
    finally:
        transport.close()


@pytest.mark.parametrize("strategy_id", ["01", "11", "13"])
def test_compiled_catalogue_languages_share_bipolar_trades_and_risk_ledger(
    real_gvisor: None, strategy_id: str
) -> None:
    import math
    from decimal import Decimal

    import pandas as pd

    from src.backtest.engine.types import BacktestConfig
    from src.strategy.code_runtime.backtest import run_code_backtest
    from src.strategy.python_runtime.serialization import json_value

    # 01/11/13의 long/short가 모두 발생하는 개발용 시세이며 수익성 평가 데이터가 아니다.
    closes = [
        round(100 + 0.18 * (i if i < 350 else 700 - i) + 8 * math.sin(i / 9), 4) for i in range(700)
    ]
    rows = []
    for i, close in enumerate(closes):
        opening = closes[i - 1] if i else close
        rows.append(
            {
                "open": str(opening),
                "high": str(max(opening, close) + 0.5),
                "low": str(min(opening, close) - 0.5),
                "close": str(close),
                "volume": str(100 + i % 17),
            }
        )
    data = pd.DataFrame(
        rows, index=pd.date_range("2026-01-01", periods=len(rows), freq="1h", tz="UTC")
    )
    config = BacktestConfig(
        freq="1h",
        init_cash=Decimal("10000"),
        default_qty_type="strategy.fixed",
        default_qty_value=1,
        fees=0.00055,
        slippage=0.00014,
    )
    spec = next(row["reference_spec"] for row in candidates() if row["id"] == strategy_id)
    outputs = {}
    for language in ("pine", "python", "typescript"):
        trace = []
        result = run_code_backtest(
            compile_strategy(spec, language), language, data, config, trace=trace
        )
        assert {trade.direction for trade in result.trades} == {"long", "short"}
        outputs[language] = {
            "trades": json_value(result.trades),
            "metrics": json_value(result.metrics),
            "trace": trace,
        }
    assert outputs["pine"] == outputs["python"] == outputs["typescript"]


@pytest.mark.parametrize("language", ["pine", "python", "typescript"])
@pytest.mark.parametrize("kind", ["stochastic", "williams_r", "mfi", "cmf"])
def test_zero_denominator_and_absent_money_flow_never_create_signals(
    real_gvisor: None, language: str, kind: str
) -> None:
    from datetime import UTC, datetime, timedelta

    import pandas as pd

    from src.strategy.code_runtime.pine import PineSignalTransport
    from src.strategy.code_runtime.sandbox import create_transport

    threshold = -101 if kind == "williams_r" else -1
    spec = {
        "title": "undefined denominator is NA",
        "warmup_bars": 1,
        "indicators": [{"id": "osc", "kind": kind, "length": 2, "slow": 1, "signal": 1}],
        "long_entry": {"op": "gt", "left": {"series": "osc"}, "right": {"constant": threshold}},
        "short_entry": {"op": "false"},
    }
    # MFI는 거래량이 있어도 가격이 평탄하면 양/음 흐름이 모두 0이다.
    volume = "0" if kind == "cmf" else "10"
    bars = [
        {
            "index": i,
            "timestamp": (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)).isoformat(),
            "open": "100",
            "high": "100",
            "low": "100",
            "close": "100",
            "volume": volume,
        }
        for i in range(5)
    ]
    data = pd.DataFrame(bars, index=pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC"))
    transport = (
        PineSignalTransport(data) if language == "pine" else create_transport(language, timeout=60)
    )
    try:
        transport.exchange(
            {
                "type": "init",
                "protocol": 1,
                "language": language,
                "source": compile_strategy(spec, language),
                "params": {},
            }
        )
        trace = [
            transport.exchange(
                {
                    "type": "bar",
                    "bar": bar,
                    "position": {"direction": "flat", "size": "0", "average_price": None},
                }
            )["intent"]["action"]
            for bar in bars
        ]
        assert trace == ["hold"] * 5
    finally:
        transport.close()
