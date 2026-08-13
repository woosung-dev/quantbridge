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
    # Sprint 58: fixnan 은 지원됨 → ta.alma (여전히 미지원) 로 대체
    src = """//@version=5
indicator("test")
plot(ta.alma(close, 9, 0.85, 6))
"""
    rep = analyze_coverage(src)
    alma_calls = [c for c in rep.unsupported_calls if c["name"] == "ta.alma"]
    assert alma_calls, "ta.alma 이 unsupported_calls 에 없음"
    assert alma_calls[0]["line"] == 3, f"ta.alma line 정보 부정확: {alma_calls[0]}"


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
    # 값 보존 equality 검증 (codex G0 P2 round-trip edge case)
    for orig, rest in zip(response.unsupported_calls, restored.unsupported_calls):
        assert orig.name == rest.name
        assert orig.line == rest.line
        assert orig.col == rest.col  # None 보존
        assert orig.workaround == rest.workaround  # None 또는 Korean string 보존
        assert orig.category == rest.category


def test_line_ignores_comment_before_actual_call():
    """codex G0 P1: 주석 안의 함수명이 실제 코드 line 보다 먼저 있어도 clean source 기준 line 반환."""
    # Sprint 58: fixnan 은 지원됨 → ta.alma (여전히 미지원) 로 대체
    # line 1: 주석 (ta.alma 포함)
    # line 3: 실제 호출
    src = """// ta.alma(close, 9, 0.85, 6)
indicator("test")
plot(ta.alma(close, 9, 0.85, 6))
"""
    rep = analyze_coverage(src)
    alma_calls = [c for c in rep.unsupported_calls if c["name"] == "ta.alma"]
    assert alma_calls, "ta.alma 이 unsupported_calls 에 없음"
    # 주석이 제거된 clean source 에서 검색 → line 3이 맞음
    assert alma_calls[0]["line"] == 3, (
        f"주석 이후 실제 코드 line 이어야 함 (P1 fix 검증): {alma_calls[0]}"
    )


def test_unsupported_calls_line_is_int_not_none():
    """line 필드는 항상 int (0 = 미발견 fallback). None 이 아님을 보장."""
    src = "fixnan(close)\n"
    rep = analyze_coverage(src)
    for call in rep.unsupported_calls:
        assert isinstance(call["line"], int), f"line 이 int 아님: {call}"
