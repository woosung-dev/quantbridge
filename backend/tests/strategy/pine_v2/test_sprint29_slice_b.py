"""Slice B — Coverage schema 확장 + DrFXGOD line-numbered 응답."""

from pathlib import Path

from src.strategy.pine_v2.coverage import analyze_coverage


def test_unsupported_calls_field_exists():
    """CoverageReport.unsupported_calls 필드가 있어야 함 (Slice B 신규)."""
    src = "fixnan(close)\n"
    rep = analyze_coverage(src)
    assert hasattr(rep, "unsupported_calls"), "CoverageReport.unsupported_calls 필드 부재"


def test_unsupported_calls_has_line_info():
    """unsupported_calls 안 항목이 name + line 포함."""
    src = """//@version=5
indicator("test")
plot(fixnan(close))
"""
    rep = analyze_coverage(src)
    fixnan_calls = [c for c in rep.unsupported_calls if c["name"] == "fixnan"]
    assert fixnan_calls, "fixnan 이 unsupported_calls 에 없음"
    assert fixnan_calls[0]["line"] == 3, f"fixnan line 정보 부정확: {fixnan_calls[0]}"


def test_drfx_unsupported_workaround_coverage():
    """DrFXGOD ~28 unsupported (Slice C 후) 의 80% 가 workaround 포함."""
    src = (Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/i3_drfx.pine").read_text()
    rep = analyze_coverage(src)

    total = len(rep.unsupported_calls)
    with_workaround = sum(1 for c in rep.unsupported_calls if c["workaround"])
    coverage_pct = with_workaround / total * 100 if total else 0

    assert coverage_pct >= 80, (
        f"DrFXGOD workaround coverage {coverage_pct:.1f}% < 80%. "
        f"missing workaround: {[c['name'] for c in rep.unsupported_calls if not c['workaround']]}"
    )


def test_pydantic_response_round_trip():
    """analyze_coverage 결과 → Pydantic serialize → JSON deserialize 정합."""
    from src.strategy.schemas import CoverageReportResponse, UnsupportedCallResponse

    src = (Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/i3_drfx.pine").read_text()
    rep = analyze_coverage(src)

    response = CoverageReportResponse(
        is_runnable=rep.is_runnable,
        used_functions=list(rep.used_functions),
        used_attributes=list(rep.used_attributes),
        unsupported_functions=list(rep.unsupported_functions),
        unsupported_attributes=list(rep.unsupported_attributes),
        unsupported_calls=[UnsupportedCallResponse(**c) for c in rep.unsupported_calls],
        dogfood_only_warning=getattr(rep, "dogfood_only_warning", None),
    )

    # Round-trip: serialize → deserialize
    json_str = response.model_dump_json()
    restored = CoverageReportResponse.model_validate_json(json_str)
    assert restored.is_runnable == response.is_runnable
    assert len(restored.unsupported_calls) == len(response.unsupported_calls)
