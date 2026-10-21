"""실제 Pine·Python·TypeScript 소스의 공통 원장 일치. 연구 VM에서 명시 실행한다."""

from __future__ import annotations

import unittest
from typing import Any

import pytest

from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.python_runtime.serialization import json_value
from tests.strategy.code_runtime import test_sandbox
from tests.strategy.code_runtime.test_backtest import cfg, frame


@pytest.mark.integration
def test_three_executable_languages_share_fills_and_position_feedback() -> None:
    try:
        test_sandbox.RealGvisorTests.setUpClass()
    except unittest.SkipTest as exc:
        pytest.skip(str(exc))
    sources = {
        "pine": """//@version=5
strategy("common risk")
if bar_index == 1
    strategy.entry("L", strategy.long)
if strategy.position_size == 5 and bar_index == 2
    strategy.close("L")
if strategy.position_size == 0 and bar_index == 3
    strategy.entry("S", strategy.short)
if strategy.position_size < 0 and bar_index == 4
    strategy.close("S")
""",
        "python": """def on_bar(ctx,state):
 i=ctx['bar']['index']
 p=ctx['position']
 if i==1: return {'action':'long'}
 if i==2 and p['size']=='5.0': return {'action':'close'}
 if i==3 and p['direction']=='flat': return {'action':'short'}
 if i==4 and p['direction']=='short': return {'action':'close'}
 return {'action':'hold'}
""",
        "typescript": """export function onBar(ctx:Context,state:Record<string,unknown>):Intent {
 const i=ctx.bar.index,p=ctx.position;
 if(i===1)return {action:'long'};
 if(i===2&&Number(p.size)===5)return {action:'close'};
 if(i===3&&p.direction==='flat')return {action:'short'};
 if(i===4&&p.direction==='short')return {action:'close'};
 return {action:'hold'};
}""",
    }
    bars = frame(
        [
            (100, 110, 90, 100),
            (100, 110, 91, 100),
            (100, 117, 100, 117),
            (117, 119, 115, 118),
            (118, 119, 117, 118),
            (118, 119, 117, 118),
        ]
    )
    outputs: dict[str, dict[str, Any]] = {}
    for language, source in sources.items():
        trace: list[dict[str, Any]] = []
        result = run_code_backtest(source, language, bars, cfg(fees=0.001), trace=trace)
        outputs[language] = {
            "trades": json_value(result.trades),
            "metrics": json_value(result.metrics),
            "trace": trace,
        }
    assert outputs["pine"] == outputs["python"] == outputs["typescript"]
    assert len(outputs["pine"]["trades"]) == 2
    assert [event["kind"] for event in outputs["pine"]["trace"] if event["type"] == "fill"] == [
        "entry",
        "partial_tp",
        "close",
        "entry",
        "close",
    ]
