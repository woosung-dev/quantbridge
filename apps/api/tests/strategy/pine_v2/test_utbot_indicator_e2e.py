"""UtBot indicator e2e backtest stable PASS — Sprint 29 Slice A 종료 trigger."""

from pathlib import Path

from src.strategy.pine_v2.coverage import analyze_coverage

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/i1_utbot.pine"


def test_utbot_indicator_coverage_runnable():
    """UtBot indicator (i1_utbot.pine) 가 Slice A 후 0 unsupported."""
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert rep.is_runnable, (
        f"UtBot indicator must be runnable after Slice A. "
        f"unsupported_functions={rep.unsupported_functions}, "
        f"unsupported_attributes={rep.unsupported_attributes}"
    )


def test_utbot_indicator_dogfood_warning_present():
    """heikinashi 사용 → dogfood_only_warning 채워짐."""
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert rep.dogfood_only_warning is not None, (
        "UtBot indicator 가 heikinashi 사용 시 warning 필드 채워야 함"
    )
