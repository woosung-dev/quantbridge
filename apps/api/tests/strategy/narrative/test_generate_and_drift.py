"""[ADR-041] 자연어 → 전략 생성 · **드리프트 탐지기**.

★이 파일이 잠그는 것 넷.
 ⑴ **판정을 LLM 이 하지 않는다** — `analyze_coverage` all-or-nothing 이 낸다.
 ⑵ **미지원이 있으면 실행 불가로 표시**되고 무엇이 막았는지 나온다.
 ⑶ 드리프트 탐지기가 **항등에서 0**(안 그러면 항상 「다르다」라 쓸모없다).
 ⑷ 드리프트 탐지기가 **진짜 다른 전략을 잡는다**(양성 대조).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from src.strategy.narrative.generate_service import (
    _TOOL_NAME,
    GenerateService,
    _identifiers,
    detect_drift,
)
from src.strategy.narrative.schemas import GenerateStrategyRequest
from src.strategy.pine_v2.py_renderer import render_python

RUNNABLE_PINE = """//@version=5
strategy("RSI Reversion", overlay=true)
length = input.int(14, title="RSI Length")
oversold = input.float(30.0, title="Oversold")
r = ta.rsi(close, length)
if ta.crossover(r, oversold)
    strategy.entry("long", strategy.long)
if r > 70
    strategy.close("long")
"""

UNSUPPORTED_PINE = """//@version=5
strategy("Needs supertrend")
[st, dir] = ta.supertrend(3.0, 10)
if close > st
    strategy.entry("long", strategy.long)
"""


def _settings() -> Any:
    return SimpleNamespace(
        llm_provider_order="anthropic",
        anthropic_api_key=SecretStr("k"),
        openai_api_key=None,
        gemini_api_key=None,
        anthropic_model="claude-sonnet-4-6",
        openai_model="gpt-4.1-mini",
        gemini_model="gemini-3.7-flash",
    )


def _patch_anthropic(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> None:
    """★provider 배선은 이제 `providers.complete_json` 이 갖는다.

    그 층의 계약(순서·건너뛰기·스키마 강제·예외 미반사)은 `test_provider_selection.py` 가 잰다.
    여기서는 **판정과 드리프트**만 재므로 provider 는 스텁으로 고정한다.
    """

    class _Messages:
        def create(self, **kwargs: Any) -> Any:
            assert kwargs["tool_choice"] == {"type": "tool", "name": _TOOL_NAME}
            block = SimpleNamespace(type="tool_use", name=_TOOL_NAME, input=payload)
            return SimpleNamespace(content=[block])

    monkeypatch.setattr(
        "src.strategy.narrative.providers.anthropic.Anthropic",
        lambda api_key: SimpleNamespace(messages=_Messages()),
    )


def test_verdict_comes_from_coverage_not_from_the_model(monkeypatch: pytest.MonkeyPatch):
    """★모델이 뭐라 하든 판정은 `analyze_coverage` 가 낸다."""
    _patch_anthropic(
        monkeypatch,
        {
            "pine_source": RUNNABLE_PINE,
            "python_view": render_python(RUNNABLE_PINE).code,
            "notes": ["손절이 없습니다."],
        },
    )
    out = GenerateService(_settings()).generate(
        GenerateStrategyRequest(prompt="RSI 과매도에 롱, 70에 청산", symbol="BTC/USDT")
    )

    assert out.is_runnable is True
    assert out.unsupported == []
    assert out.notes == ["손절이 없습니다."]
    assert out.drift is not None


def test_unsupported_output_is_rejected_and_says_what_blocked_it(monkeypatch: pytest.MonkeyPatch):
    """★[ADR-003] 결정 2 동형 — 미지원 1개라도 있으면 실행 불가다."""
    _patch_anthropic(
        monkeypatch,
        {"pine_source": UNSUPPORTED_PINE, "python_view": "def on_bar(): pass", "notes": []},
    )
    out = GenerateService(_settings()).generate(
        GenerateStrategyRequest(prompt="슈퍼트렌드 돌파 전략 만들어줘")
    )

    assert out.is_runnable is False
    assert "ta.supertrend" in out.unsupported
    # ★못 도는 Pine 은 렌더 기준선이 될 수 없다 — 대조를 시도조차 하지 않는다.
    assert out.drift is None


def test_drift_is_zero_when_the_two_artifacts_agree():
    """★항등 검사. 여기서 0이 안 나오면 탐지기가 **항상 「다르다」**라 쓸모가 없다."""
    report = detect_drift(pine_source=RUNNABLE_PINE, llm_python=render_python(RUNNABLE_PINE).code)
    assert report.diverged is False
    assert report.only_in_llm == []
    assert report.only_in_rendered == []


def test_drift_catches_a_genuinely_different_strategy():
    """★양성 대조. 위 항등 초록이 「탐지기가 죽어서」가 아님을 증명한다."""
    report = detect_drift(
        pine_source=RUNNABLE_PINE,
        llm_python="def on_bar():\n    z = ta.macd(close, 12, 26)\n    if z > 0:\n        buy_now()\n",
    )
    assert report.diverged is True
    assert "ta.macd" in report.only_in_llm
    # 정본은 언제나 렌더링본이다 — 화면이 그것을 제시할 수 있어야 한다.
    assert "ta.rsi" in report.rendered_python


def test_render_commentary_does_not_leak_into_the_identifier_set():
    """★렌더러가 붙인 주석이 식별자로 새면 **모든 전략이 어긋난 것**이 된다.

    ★첫 판의 이 테스트는 한국어 주석으로 쟀는데 판별력이 0이었다 — 한국어는 애초에 식별자
    정규식(`[A-Za-z_]…`)에 안 걸려서, 주석 제거를 죽이는 변이를 심어도 15/15 초록이었다
    (2026-08-27). 주석 제거가 실제로 지키는 것은 **ASCII 단어**다:
    헤더 해설의 `Pine`·`Python`·`pine_v2` 와 `[원문 보존]` 주석 안의 **원본 Pine 식별자**.
    """
    rendered = render_python(RUNNABLE_PINE).code
    idents = _identifiers(rendered)

    # 해설 문장의 단어가 전략의 식별자로 둔갑하면 안 된다.
    for word in ("Pine", "Python", "pine_v2"):
        assert word in rendered, f"{word} 가 해설에 없다 — 이 케이스는 대조가 못 된다"
        assert word not in idents, f"{word} 가 식별자로 샜다"

    # 진짜 식별자는 살아 있어야 한다(음성 대조의 짝).
    assert "ta.rsi" in idents


def test_preserved_original_pine_in_comments_does_not_count_as_drift():
    """★`[원문 보존]` 주석 안에는 **원본 Pine 코드**가 통째로 들어간다.

    그것을 세면 못 옮긴 노드가 있는 전략은 **항상 어긋난 것**으로 나온다.
    """
    source = '//@version=5\nindicator("A")\narr = array.new_float()\nfor v in arr\n    x = v\n'
    rendered = render_python(source).code
    assert "[원문 보존]" in rendered, "이 케이스가 보존 경로를 안 지났다 — 대조가 못 된다"

    idents = _identifiers(rendered)
    # 보존 주석 안의 `v`·`x` 는 렌더된 코드에 없으므로 식별자로 세면 안 된다.
    assert "v" not in idents
    assert "x" not in idents
    assert "array.new_float" in idents  # 실제 코드 줄의 식별자는 산다
