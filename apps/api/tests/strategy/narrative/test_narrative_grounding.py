"""[ADR-040] 해설 층 — **근거 없는 문장은 존재하지 않는다**.

★서버가 버리는 이유. 규칙이 클라이언트에도 살면 언젠가 한쪽만 고쳐지고, 그때 화면은 근거 없는
LLM 문장을 판정처럼 그린다. 이 제품에서 그 값은 음수다([ADR-040] · [ADR-020] §3 F).
"""

from __future__ import annotations

from src.strategy.narrative.service import NarrativeService, number_source

SOURCE = """//@version=5
strategy("RSI")
length = input.int(14)
r = ta.rsi(close, length)
if r < 30
    strategy.entry("long", strategy.long)
"""


def _svc() -> NarrativeService:
    return NarrativeService.__new__(NarrativeService)  # provider 를 안 부르는 순수 경로만 쓴다


def test_notes_without_evidence_are_dropped():
    raw = {
        "summary": "RSI 과매도 반전 전략입니다.",
        "style": "mean_reversion",
        "assumptions": [
            {"text": "근거 있음", "pine_lines": [5]},
            {"text": "근거 없음", "pine_lines": []},
        ],
        "risks": [{"text": "빈 텍스트", "pine_lines": [3]}],
    }
    raw["risks"].append({"text": "", "pine_lines": [3]})

    out = _svc()._build(raw, SOURCE, "h" * 64, provider="anthropic")

    assert [n.text for n in out.assumptions] == ["근거 있음"]
    assert [n.text for n in out.risks] == ["빈 텍스트"]
    assert out.dropped_ungrounded == 2


def test_lines_outside_the_source_are_dropped_not_clamped():
    """★없는 줄을 지어내면 버린다. **자르지 않는다** — 6번 줄을 5번으로 고쳐 주면 거짓이 참이 된다."""
    raw = {
        "summary": "s",
        "style": "other",
        "assumptions": [
            {"text": "지어낸 줄만", "pine_lines": [999]},
            {"text": "섞임", "pine_lines": [4, 999]},
        ],
        "risks": [],
    }
    out = _svc()._build(raw, SOURCE, "h" * 64, provider="gemini")

    assert [n.text for n in out.assumptions] == ["섞임"]
    assert out.assumptions[0].pine_lines == [4]  # 실재하는 것만 남는다
    assert out.dropped_ungrounded == 1


def test_unknown_style_falls_back_instead_of_leaking_to_the_screen():
    """닫힌 집합 밖의 값이 오면 `other` 다 — 화면이 무한한 라벨을 다루지 않는다."""
    raw = {"summary": "s", "style": "제가 만든 유형", "assumptions": [], "risks": []}
    assert _svc()._build(raw, SOURCE, "h" * 64, provider="anthropic").style == "other"


def test_malformed_payload_does_not_raise():
    """★LLM 이 스키마를 어겨도 500 이 되면 안 된다 — 화면은 결정론 층으로 이미 완결돼 있다."""
    out = _svc()._build({}, SOURCE, "h" * 64, provider="gemini")
    assert out.summary == ""
    assert out.assumptions == []
    assert out.style == "other"


def test_source_is_numbered_so_the_model_has_coordinates_to_cite():
    numbered = number_source(SOURCE)
    assert numbered.splitlines()[0] == "1: //@version=5"
    assert numbered.splitlines()[4] == "5: if r < 30"
