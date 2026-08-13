"""DrFXGOD i3_drfx.pine 의 unsupported_calls schema verify — Sprint 29 Slice B 종료 trigger."""

from pathlib import Path

from src.strategy.pine_v2.coverage import analyze_coverage

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/i3_drfx.pine"


def test_drfx_unsupported_calls_populated():
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert not rep.is_runnable, "DrFXGOD must remain unrunnable (PASS 불가, schema only)"
    assert len(rep.unsupported_calls) > 0, "unsupported_calls 가 채워져야 함"


def test_drfx_each_call_has_name_line_category():
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    for call in rep.unsupported_calls:
        assert call.get("name")
        assert "line" in call and call["line"] >= 0  # 0 = 미발견 fallback
        assert "category" in call and call["category"] in {
            "drawing",
            "data",
            "syntax",
            "math",
            "other",
        }


def test_drfx_workaround_coverage_80_percent():
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    total = len(rep.unsupported_calls)
    with_wa = sum(1 for c in rep.unsupported_calls if c["workaround"])
    pct = with_wa / total * 100 if total else 0
    assert pct >= 80, f"DrFXGOD workaround {pct:.1f}% < 80%"
