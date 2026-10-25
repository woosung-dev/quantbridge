"""v4 별칭은 기존 TA 계산으로 연결하고 공식 인자명을 보존한다.

공식 이름/cum 인자명 근거:
https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-5/
공식 v4 여섯 함수의 인자명 근거:
https://pl.tradingview.com/pine-script-reference/v4/
"""

import pandas as pd
import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def run(expression, *, version=4):
    close = [12.0, 15.0, 13.0, 18.0, 16.0, 19.0, 14.0, 21.0] * 3
    frame = pd.DataFrame(
        {
            "open": close,
            "close": close,
            "high": [value + 2 for value in close],
            "low": [value - 3 for value in close],
            "volume": [float(index + 1) for index in range(len(close))],
        }
    )
    return run_historical(
        f'//@version={version}\nstudy("alias fixture")\n'
        f"src=bar_index == 8 ? na : close\nvalue={expression}\n",
        frame,
        strict=True,
    ).var_series["value"]


@pytest.mark.parametrize(
    "expression",
    [
        "stoch(src,high,low,4)",
        "cum(src)",
        "linreg(src,4,1)",
        "vwma(src,4)",
        "roc(src,4)",
        "cci(src,4)",
        "hma(src,4)",
    ],
)
def test_v4_alias_preserves_namespaced_series_and_na(expression):
    assert analyze_coverage(f"//@version=4\nstudy('fixture')\nx={expression}").is_runnable
    assert run(expression) == pytest.approx(run(f"ta.{expression}", version=5), nan_ok=True)


def test_v4_cum_uses_original_x_keyword_without_mutating_source_contract():
    assert run("cum(x=src)") == pytest.approx(run("cum(src)"), nan_ok=True)


@pytest.mark.parametrize(
    "expression,positional",
    [
        ("stoch(length=4,low=low,high=high,source=src)", "stoch(src,high,low,4)"),
        ("linreg(offset=1,length=4,source=src)", "linreg(src,4,1)"),
        ("vwma(length=4,source=src)", "vwma(src,4)"),
        ("roc(length=4,source=src)", "roc(src,4)"),
        ("cci(length=4,source=src)", "cci(src,4)"),
        ("hma(length=4,source=src)", "hma(src,4)"),
    ],
)
def test_verified_v4_keywords_are_reordered(expression, positional):
    assert run(expression) == pytest.approx(run(positional), nan_ok=True)


@pytest.mark.parametrize("version", [4, 5, 6])
def test_namespaced_hma_reorders_verified_keywords(version):
    assert run("ta.hma(length=4,source=src)", version=version) == pytest.approx(
        run("ta.hma(src,4)", version=version), nan_ok=True
    )


@pytest.mark.parametrize(
    "expression,reason",
    [
        ("cum(source=src)", "unknown argument"),
        ("cum(src,x=src)", "duplicate or excess"),
        ("cum()", "missing required"),
        ("ta.cum(x=src)", "unknown argument"),
        ("stoch(source=src,peak=high,valley=low,period=4)", "unknown argument"),
        ("hma(src,source=src)", "duplicate or excess"),
        ("hma(src,period=4)", "unknown argument"),
        ("ta.hma(src,source=src)", "duplicate or excess"),
        ("ta.hma(src,period=4)", "unknown argument"),
        ("ta.hma(src)", "missing required"),
        ("ta.hma(src,4,5)", "duplicate or excess"),
        ("ta.hma(source=src,4)", "positional argument after keyword"),
    ],
)
def test_argument_errors_fail_before_silent_positional_dispatch(expression, reason):
    with pytest.raises(PineRuntimeError, match=reason):
        run(expression)
