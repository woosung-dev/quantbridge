"""ParsePreviewResponse.declaration / .inputs 계약 회귀 ([ADR-040] Stage 1).

`ast_extractor.extract_content()` 는 선언부와 input 선언 전량을 이미 뽑고 있었는데
응답에 실리지 않아 FE 가 파라미터 표를 못 그렸다(`diagnostics-strip.tsx` 의 「파라미터」
탭이 빈 슬롯으로 대기 중이었다). 이 파일은 그 노출이 살아 있는지와,
**구조 추출 실패가 파싱 판정을 뒤집지 않는지**를 고정한다.
"""

from __future__ import annotations

import pytest

RSI_V5 = """//@version=5
strategy("RSI Mean Reversion", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=30, pyramiding=2)
length = input.int(14, title="RSI Length", minval=1)
oversold = input.float(30.0, title="Oversold")
useFilter = input.bool(true, title="Use Filter")
label = input.string("A", title="Label")
r = ta.rsi(close, length)
if ta.crossover(r, oversold) and useFilter
    strategy.entry("long", strategy.long)
if r > 70
    strategy.close("long")
"""

# 파싱 자체가 깨지는 소스 — `_parse` 가 status=error 를 내고 구조는 비어야 한다.
BROKEN = """//@version=5
strategy(  <<< not pine at all
"""


@pytest.mark.asyncio
async def test_parse_preview_exposes_declaration(client, mock_authed_user):
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": RSI_V5})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"

    decl = body["declaration"]
    assert decl is not None
    assert decl["kind"] == "strategy"
    assert decl["title"] == "RSI Mean Reversion"
    # ★sizing 3종은 백테스트 가정 카드가 읽는 값이라 문자열 원형 그대로 노출한다.
    assert decl["default_qty_type"] == "strategy.percent_of_equity"
    assert decl["default_qty_value"] == "30"
    assert decl["pyramiding"] == 2


@pytest.mark.asyncio
async def test_parse_preview_exposes_inputs_with_var_name_and_type(client, mock_authed_user):
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": RSI_V5})
    assert res.status_code == 200
    inputs = res.json()["inputs"]

    by_name = {i["var_name"]: i for i in inputs}
    assert set(by_name) == {"length", "oversold", "useFilter", "label"}

    # ★`var_name` 은 장식이 아니라 override 키다 — Optimizer / Param-Stability 의
    #   pre-validate 가 `extract_content().inputs` 의 이 이름으로 대조하고
    #   (`optimizer/engine/grid_search.py` `_validate_grid_search_pre`),
    #   엔진은 `input_overrides[var_name]` 으로 값을 갈아끼운다.
    assert by_name["length"]["input_type"] == "int"
    assert by_name["length"]["defval"] == "14"
    assert by_name["length"]["title"] == "RSI Length"
    assert by_name["oversold"]["input_type"] == "float"
    assert by_name["useFilter"]["input_type"] == "bool"
    assert by_name["label"]["input_type"] == "string"

    # 선언 순서를 보존한다 — 표가 소스 순서대로 읽혀야 한다.
    assert [i["var_name"] for i in inputs] == ["length", "oversold", "useFilter", "label"]


@pytest.mark.asyncio
async def test_structure_extraction_failure_does_not_flip_the_verdict(client, mock_authed_user):
    """★구조 추출은 판정자가 아니다.

    `extract_content` 는 파싱 실패 시 예외를 던진다. 그 예외가 새어 나가면 파싱 프리뷰
    엔드포인트가 500 이 되어, **문법이 틀렸다는 정보를 사용자가 못 받는다.**
    """
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": BROKEN})
    assert res.status_code == 200
    body = res.json()

    assert body["status"] == "error"  # 판정은 살아 있다
    assert body["declaration"] is None  # 구조는 조용히 비었다
    assert body["inputs"] == []


@pytest.mark.asyncio
async def test_v4_no_namespace_input_is_reported_as_generic(client, mock_authed_user):
    """★v4 `input(...)` 은 `input_type="generic"` 이고 **Optimizer 가 스윕하지 못한다**.

    `_validate_grid_search_pre` 가 `input_type not in {"int","float"}` 을 거부하기
    때문이다(BL-225). 화면은 이 입력을 **숨기지 말고 「스윕 불가」로 표시**해야 한다 —
    표에서 빠지면 사용자는 파라미터가 없는 전략이라고 읽는다.
    """
    v4 = '//@version=4\nstrategy("v4")\nlen = input(14, title="Length")\nplot(sma(close, len))\n'
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": v4})
    assert res.status_code == 200
    inputs = res.json()["inputs"]

    assert len(inputs) == 1
    assert inputs[0]["var_name"] == "len"
    assert inputs[0]["input_type"] == "generic"
