"""버전 표기 없는 Pine의 v1 기본값과 구형 표시 상수를 확인한다."""

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, PineRuntimeError, pine_version_from_ast
from src.strategy.pine_v2.parser_adapter import parse_to_ast


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10.0, 11.0],
            "high": [12.0, 13.0],
            "low": [9.0, 10.0],
            "close": [11.0, 12.0],
            "volume": [1.0, 1.0],
        }
    )


def test_versionless_source_uses_v1_and_legacy_display_constants() -> None:
    source = 'study("Legacy")\nplot(close, color=fuchsia, style=line)\nplot(close, style=circles)\n'
    assert pine_version_from_ast(parse_to_ast(source)) == 1
    assert not run_historical(source, _frame()).errors


def test_explicit_modern_version_keeps_bare_color_undefined() -> None:
    with pytest.raises(PineRuntimeError, match="Undefined name: fuchsia"):
        run_historical('//@version=4\nstudy("Modern")\nplot(close, color=fuchsia)\n', _frame())


def test_direct_bar_context_default_remains_six() -> None:
    bar = BarContext(_frame(), timeframe="1d")
    assert bar.pine_version == 6
    assert bar._timeframe_attributes["timeframe.period"] == "1D"
