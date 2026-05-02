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


def test_utbot_minimal_rejects_heikinashi_and_security_trust_layer(
    utbot_minimal: str,
) -> None:
    """UtBot-style 은 Trust Layer 정합 reject — heikinashi / security 가 unsupported.

    codex G.0 P1 #2: NOP-degrade 거부. 사용자가 UtBot 못 쓰는 것이 잘못된 결과 통과보다
    안전 (silent corruption 방지). Sprint 22+ 의 strict toggle 로 옵션 검토.
    """
    r = analyze_coverage(utbot_minimal)
    assert not r.is_runnable, "UtBot-minimal should NOT be runnable (Trust Layer)"

    all_unsupported = set(r.all_unsupported)
    assert "heikinashi" in all_unsupported, (
        f"heikinashi must be flagged unsupported. all_unsupported={all_unsupported}"
    )
    assert "security" in all_unsupported, (
        f"security (no-namespace) must be flagged unsupported. all_unsupported={all_unsupported}"
    )

    # Sprint 21 신규 fix 된 항목은 unsupported 에서 제외 — supported 로 분류
    assert "max" not in all_unsupported
    assert "min" not in all_unsupported
    assert "timeframe.period" not in all_unsupported
    assert "study" not in all_unsupported


def test_drfx_partial_baseline_for_sprint22(drfx_partial: str) -> None:
    """DrFXGOD-style 의 box.* / label.* / barcolor / request.security 는 Sprint 22+ scope.

    Sprint 21 baseline: 본 fixture 의 unsupported 카운트를 기록 → Sprint 22 진입 시
    baseline 대비 감소율 측정.
    """
    r = analyze_coverage(drfx_partial)
    assert not r.is_runnable, "DrFX-partial should NOT be runnable (Sprint 22+ scope)"

    all_unsupported = set(r.all_unsupported)
    # Sprint 22+ scope — 다음 builtin 들은 reject 유지 기대
    expected_sprint22_unsupported = {
        "request.security",
        "barcolor",
        "box.set_top",  # method dispatch 미지원
        "label.set_xy",
    }
    found_sprint22 = expected_sprint22_unsupported & all_unsupported
    assert found_sprint22, (
        f"Expected at least one Sprint 22+ scope unsupported (e.g., box.* / label.* / "
        f"barcolor / request.security), found {found_sprint22}. "
        f"all_unsupported={sorted(all_unsupported)}"
    )

    # Sprint 21 fix 된 control items 는 supported
    assert "max" not in all_unsupported, (
        "Sprint 21 fixed `max` should be supported in DrFX-partial baseline."
    )
    assert "timeframe.period" not in all_unsupported


def test_dogfood_corpus_pass_rate_50_percent_baseline(
    rsid_minimal: str, utbot_minimal: str, drfx_partial: str
) -> None:
    """SLO 회귀: 본인 6 pine 통과율 33% → 50% (3/6, RsiD only).

    Sprint 21 corpus = RsiD ✅ + UtBot 🔴 (Trust Layer) + DrFX 🔴 (Sprint 22+).
    PbR + LuxAlgo 는 Sprint 20 Day 0 에서 이미 ✅ — SLO 3/6 = 50%.
    """
    sources = [
        ("rsid", rsid_minimal),
        ("utbot", utbot_minimal),
        ("drfx", drfx_partial),
    ]
    runnable = [name for name, src in sources if analyze_coverage(src).is_runnable]
    expected = ["rsid"]
    assert runnable == expected, (
        f"Sprint 21 SLO: only RsiD-minimal should be runnable. "
        f"actual_runnable={runnable}, expected={expected}"
    )
