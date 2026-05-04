"""Sprint 21 Phase C — dogfood pine corpus integration regression.

본인 6 indicator 의 builtin coverage 패턴을 QB-authored minimal pine 으로 재현.
Sprint 21 fix 후 RsiD-style 은 supported, UtBot-style 은 Trust Layer 정합 reject,
DrFX-style 은 Sprint 22+ scope baseline 검증.

라이선스 회피 (codex G.0 P1 #6): 사용자 보관 LuxAlgo / DrFXGOD / UtBot 원문 미복사.
fixture 모두 QB 자체 작성.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.strategy.pine_v2.coverage import analyze_coverage

_FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "dogfood_corpus"


@pytest.fixture(scope="module")
def rsid_minimal() -> str:
    return (_FIXTURE_DIR / "rsid_minimal.pine").read_text()


@pytest.fixture(scope="module")
def utbot_minimal() -> str:
    return (_FIXTURE_DIR / "utbot_minimal.pine").read_text()


@pytest.fixture(scope="module")
def drfx_partial() -> str:
    return (_FIXTURE_DIR / "drfx_partial.pine").read_text()


def test_rsid_minimal_is_runnable_after_sprint21_fix(rsid_minimal: str) -> None:
    """RsiD-style 의 8 unsupported (abs/barssince/currency.USD/max/min/pivothigh/
    pivotlow/strategy.fixed/valuewhen) 모두 supported. SLO 50% 달성 핵심.
    """
    r = analyze_coverage(rsid_minimal)
    assert r.is_runnable, (
        f"RsiD-minimal should pass after Sprint 21 v4 alias + explicit constant expansion. "
        f"unsupported_functions={r.unsupported_functions}, "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


def test_utbot_minimal_runnable_after_sprint29_slice_a(
    utbot_minimal: str,
) -> None:
    """Sprint 29 Slice A: UtBot-style 은 heikinashi (a) + security graceful → RUNNABLE.

    Sprint 21 Trust Layer reject 정책 → Sprint 29 (a) 결정으로 전환.
    heikinashi 는 dogfood_only_warning 채워짐 (Trust Layer 위반 명시).
    참고: docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md
    """
    r = analyze_coverage(utbot_minimal)
    assert r.is_runnable, (
        f"UtBot-minimal should be RUNNABLE after Sprint 29 Slice A. "
        f"unsupported_functions={r.unsupported_functions}, "
        f"unsupported_attributes={r.unsupported_attributes}"
    )

    all_unsupported = set(r.all_unsupported)
    # Sprint 29 Slice A: heikinashi + security 이제 supported
    assert "heikinashi" not in all_unsupported
    assert "security" not in all_unsupported

    # Sprint 21 신규 fix 된 항목은 unsupported 에서 제외 — supported 로 분류
    assert "max" not in all_unsupported
    assert "min" not in all_unsupported
    assert "study" not in all_unsupported
    # Sprint 29 Slice A: timeframe.period 이제 supported (interpreter._eval_attribute 구현)
    assert "timeframe.period" not in all_unsupported

    # heikinashi 사용 → dogfood_only_warning 채워짐
    assert r.dogfood_only_warning is not None, (
        "UtBot-minimal 이 heikinashi 사용 → dogfood_only_warning 필드 채워야 함"
    )


def test_drfx_partial_baseline_for_sprint22(drfx_partial: str) -> None:
    """DrFXGOD-style 의 box.* / label.* / ta.alma 등은 Sprint 22+ scope (미처리).

    Sprint 21 baseline: 본 fixture 의 unsupported 카운트를 기록 → Sprint 22 진입 시
    baseline 대비 감소율 측정.
    Sprint 29 갱신: barcolor + request.security + timeframe.period 이제 SUPPORTED.
    """
    r = analyze_coverage(drfx_partial)
    assert not r.is_runnable, "DrFX-partial should NOT be runnable (Sprint 22+ scope)"

    all_unsupported = set(r.all_unsupported)
    # Sprint 22+ scope — 다음 builtin 들은 reject 유지 기대 (box.set_top 등)
    expected_sprint22_unsupported = {
        "box.set_top",  # method dispatch 미지원
    }
    found_sprint22 = expected_sprint22_unsupported & all_unsupported
    assert found_sprint22, (
        f"Expected at least one Sprint 22+ scope unsupported (e.g., box.set_top), "
        f"found {found_sprint22}. "
        f"all_unsupported={sorted(all_unsupported)}"
    )

    # Sprint 21 fix 된 control items 는 supported
    assert "max" not in all_unsupported, (
        "Sprint 21 fixed `max` should be supported in DrFX-partial baseline."
    )
    # Sprint 29 Slice A: barcolor + request.security 이제 SUPPORTED
    assert "barcolor" not in all_unsupported, (
        "Sprint 29 Slice A: barcolor should now be supported."
    )
    assert "request.security" not in all_unsupported, (
        "Sprint 29 Slice A: request.security should now be supported."
    )
    # Sprint 29 Slice A: timeframe.period 이제 SUPPORTED (interpreter 구현)
    assert "timeframe.period" not in all_unsupported, (
        "Sprint 29 Slice A: timeframe.period should now be supported."
    )


def test_dogfood_corpus_pass_rate_sprint29_baseline(
    rsid_minimal: str, utbot_minimal: str, drfx_partial: str
) -> None:
    """SLO 회귀: Sprint 29 Slice A 후 통과율 갱신.

    Sprint 21: RsiD ✅ + UtBot 🔴 (Trust Layer) + DrFX 🔴 (Sprint 22+) = 1/3 corpus
    Sprint 29 Slice A: UtBot → ✅ (heikinashi (a) + security graceful) = 2/3 corpus.
    DrFX 는 여전히 미처리 항목 잔존 → 🔴.
    PbR + LuxAlgo + RsiD (Sprint 20 ✅) + UtBot indicator/strategy (Sprint 29 ✅) = 5/6 전체 corpus.
    """
    sources = [
        ("rsid", rsid_minimal),
        ("utbot", utbot_minimal),
        ("drfx", drfx_partial),
    ]
    runnable = [name for name, src in sources if analyze_coverage(src).is_runnable]
    expected = ["rsid", "utbot"]  # Sprint 29 Slice A: UtBot 추가
    assert runnable == expected, (
        f"Sprint 29 SLO: RsiD + UtBot should be runnable. "
        f"actual_runnable={runnable}, expected={expected}"
    )
