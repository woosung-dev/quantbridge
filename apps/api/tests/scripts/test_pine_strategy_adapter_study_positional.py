"""v4 study의 표시용 위치 인자는 이름으로 보존하고 모호한 선언은 거절한다."""

import hashlib

import pytest
from pynescript import ast as A

from scripts.pine_validation.strategy_adapter import StrategyAdapterError, adapt_strategy
from src.strategy.pine_v2.parser_adapter import parse_to_ast


def _adapt(header: str, version: int = 4):
    source = (
        f"//@version={version}\n{header}\n"
        "value = close - open\nplotshape(value > 0)\nplotshape(value < 0)\n"
    )
    result = adapt_strategy(
        source,
        [
            {"function": "plotshape", "line": 4, "column": 0, "direction": "long"},
            {"function": "plotshape", "line": 5, "column": 0, "direction": "short"},
        ],
    )
    assert result.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert "value = close - open\n" in result.strategy_source
    header_node = parse_to_ast(result.strategy_source).body[0].value
    assert isinstance(header_node, A.Call) and header_node.func.id == "strategy"
    return {argument.name: A.unparse(argument.value) for argument in header_node.args}


@pytest.mark.parametrize("overlay", ["false", "true"])
@pytest.mark.parametrize("format_name", ["format.inherit", "format.price", "format.volume"])
@pytest.mark.parametrize("precision", [0, 2, 16])
def test_v4_study_positional_display_values_preserved(overlay, format_name, precision):
    arguments = _adapt(f'study("Fixture", "F", {overlay}, {format_name}, {precision})')
    assert arguments["overlay"] == overlay
    assert arguments["format"] == format_name
    assert arguments["precision"] == str(precision)


@pytest.mark.parametrize(
    "header,expected",
    [
        ('study("Fixture", "F", false)', {"overlay": "false"}),
        (
            'study("Fixture", "F", false, format.price)',
            {"overlay": "false", "format": "format.price"},
        ),
        (
            'study("Fixture", "F", false, precision=2)',
            {"overlay": "false", "precision": "2"},
        ),
    ],
)
def test_v4_study_optional_positional_prefix(header, expected):
    arguments = _adapt(header)
    assert {name: arguments[name] for name in expected} == expected


@pytest.mark.parametrize(
    "header",
    [
        'study("Fixture", "F", 0)',
        'study("Fixture", "F", close > open)',
        'study("Fixture", "F", false, close)',
        'study("Fixture", "F", false, "price")',
        'study("Fixture", "F", false, format.percent)',
        'study("Fixture", "F", false, format.price, true)',
        'study("Fixture", "F", false, format.price, 2.0)',
        'study("Fixture", "F", false, format.price, -1)',
        'study("Fixture", "F", false, format.price, 17)',
        'study("Fixture", "F", false, format.price, close)',
        'study("Fixture", "F", false, overlay=true)',
        'study("Fixture", "F", false, format.price, format=format.volume)',
        'study("Fixture", "F", false, format.price, 2, precision=3)',
        'study("Fixture", shorttitle="F", false)',
        'study("Fixture", "F", false, format.price, 2, scale.left)',
        'study("Fixture", "F", false, format.price, 2, resolution="D")',
        'study("Fixture", "F", false, format.price, 2, unknown=true)',
    ],
)
def test_v4_study_ambiguous_or_unsupported_options_remain_rejected(header):
    with pytest.raises(StrategyAdapterError):
        _adapt(header)


@pytest.mark.parametrize("version", [2, 3, 5])
def test_v4_positional_contract_is_not_assumed_for_other_study_versions(version):
    with pytest.raises(StrategyAdapterError):
        _adapt('study("Fixture", "F", false, format.price, 2)', version)


def test_existing_indicator_positional_overlay_is_preserved():
    assert _adapt('indicator("Fixture", "F", false)', 6)["overlay"] == "false"
