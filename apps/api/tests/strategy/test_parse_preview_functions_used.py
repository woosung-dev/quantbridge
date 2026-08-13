"""ParsePreviewResponse.functions_used 필드 회귀 테스트.

Sprint 7b (ISSUE-004): UI 파싱 결과 탭에서 '감지된 지표/전략 콜' 섹션
렌더링을 위해 응답 DTO에 functions_used 노출.
"""
from __future__ import annotations

import pytest

EMA_CROSS_V5 = """//@version=5
strategy("EMA Cross", overlay=true)
fast = ta.ema(close, 9)
slow = ta.ema(close, 21)
longCond = ta.crossover(fast, slow)
exitCond = ta.crossunder(fast, slow)
if longCond
    strategy.entry("long", strategy.long)
if exitCond
    strategy.close("long")
"""


@pytest.mark.asyncio
async def test_parse_preview_returns_functions_used(client, mock_clerk_auth):
    res = await client.post(
        "/api/v1/strategies/parse", json={"pine_source": EMA_CROSS_V5}
    )
    assert res.status_code == 200
    body = res.json()

    assert body["status"] == "ok"
    assert "functions_used" in body
    functions = body["functions_used"]
    assert isinstance(functions, list)

    # validate_functions는 AST의 FnCall 전부를 수집 (ta.ema, ta.crossover, strategy.entry 등)
    assert "ta.ema" in functions
    assert "ta.crossover" in functions
    assert "strategy.entry" in functions

    # 결정적 정렬 보장 (supported_feature_report는 sorted(used))
    assert functions == sorted(functions)


@pytest.mark.asyncio
async def test_parse_preview_functions_used_empty_on_lex_error(
    client, mock_clerk_auth
):
    res = await client.post(
        "/api/v1/strategies/parse", json={"pine_source": "!!!@#$"}
    )
    assert res.status_code == 200
    body = res.json()

    assert body["status"] == "error"
    # parser가 tokenize/parse 단계에서 실패하면 functions_used는 빈 리스트.
    assert body["functions_used"] == []
