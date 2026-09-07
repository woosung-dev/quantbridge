"""임포트 경로가 coverage 를 **몇 번** 부르는지 고정한다.

왜 시간이 아니라 횟수인가 — [LESSON-131] 이 「소음 폭(±40%)이 주장 효과(21%)보다 컸다」를
기록했다. wall-clock 단언은 CI 부하에 따라 흔들려 회귀를 못 잡거나 없는 회귀를 만든다.
호출 횟수는 결정론적이고, 이 수리가 실제로 걱정하는 것(중복 호출로 임포트가 느려지는 것)을
정확히 겨눈다.

절대 시간은 회차 preflight 에서 한 번 쟀다 — corpus 9벌 합계 **8.6ms**, 최악 단건
`i3_drfx`(38KB) **5.71ms**. `analyze_coverage` 는 AST 가 아니라 정규식이다
(`pine_v2/coverage.py`). 그 수는 커밋 메시지가 갖고 PRD §5 표에는 올리지 않는다
([LESSON-129] — 못 재는 줄은 표에 올리지 않는다).
"""

from __future__ import annotations

import pytest

from src.strategy import service as service_module

_OK = """//@version=5
strategy("ok")
if ta.crossover(close, ta.sma(close, 5))
    strategy.entry("L", strategy.long)
"""


@pytest.mark.asyncio
async def test_create_calls_coverage_exactly_once(client, mock_authed_user, monkeypatch):
    calls: list[str] = []
    real = service_module.analyze_coverage

    def counting(source: str):
        calls.append(source)
        return real(source)

    monkeypatch.setattr(service_module, "analyze_coverage", counting)

    res = await client.post(
        "/api/v1/strategies",
        json={"name": "cost probe", "pine_source": _OK},
    )
    assert res.status_code == 201, res.text
    assert len(calls) == 1, f"임포트 1회당 coverage 1회여야 한다 (실제 {len(calls)})"


@pytest.mark.asyncio
async def test_parse_preview_calls_coverage_exactly_once(client, mock_authed_user, monkeypatch):
    """미리보기도 같은 계약이다 — 위저드는 타이핑마다 이 경로를 친다."""
    calls: list[str] = []
    real = service_module.analyze_coverage

    def counting(source: str):
        calls.append(source)
        return real(source)

    monkeypatch.setattr(service_module, "analyze_coverage", counting)

    res = await client.post("/api/v1/strategies/parse", json={"pine_source": _OK})
    assert res.status_code == 200, res.text
    assert len(calls) == 1, f"미리보기 1회당 coverage 1회여야 한다 (실제 {len(calls)})"
