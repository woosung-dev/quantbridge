"""Alert Hook 추출 + 메시지 분류기 v0 회귀.

Day 3 스냅샷 `alert_hook_report.json`과 완전 일치해야 한다.
추가: `classify_message` 유닛 테스트로 규칙 엣지 검증.

본 테스트의 가치는 단순 회귀 고정이 아니라 **ADR-011 §2.1.2 분류기 정확도 가정**
(키워드 매칭 80% 이상)을 6 corpus + 10 alert 실데이터로 유지하는 것.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.strategy.pine_v2.alert_hook import (
    SignalKind,
    classify_message,
    collect_alerts,
)

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_REPORT: dict[str, list[dict]] = json.loads(
    (_CORPUS_DIR / "alert_hook_report.json").read_text()
)


@pytest.mark.parametrize("script_name", sorted(_REPORT.keys()))
def test_collect_alerts_matches_baseline(script_name: str) -> None:
    source = (_CORPUS_DIR / f"{script_name}.pine").read_text()
    actual = [h.to_dict() for h in collect_alerts(source)]
    expected = _REPORT[script_name]

    assert actual == expected, (
        f"{script_name}: alert 추출/분류 드리프트\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}"
    )


def test_total_alert_count_across_corpus() -> None:
    """ADR-011 §2.1 Alert Hook 사전 조사: Track A 3종에서 alert 총 10개."""
    total = sum(len(hooks) for hooks in _REPORT.values())
    assert total == 10, f"corpus 총 alert는 Phase -1 snapshot 기준 10개 (실측 {total})"


def test_classify_coverage_v0() -> None:
    """분류 커버리지: 10 alert 중 unknown은 0 (N=10 한계 인정)."""
    unknown_count = 0
    for hooks in _REPORT.values():
        for h in hooks:
            if h["signal"] == SignalKind.UNKNOWN.value:
                unknown_count += 1
    assert unknown_count == 0, (
        f"분류 커버리지 100% 기대 (N=10). unknown {unknown_count}개 — 규칙 보강 필요"
    )


@pytest.mark.parametrize(("message", "expected"), [
    ("BUY", SignalKind.LONG_ENTRY),
    ("buy at market", SignalKind.LONG_ENTRY),
    ("SELL", SignalKind.SHORT_ENTRY),
    ("매수 진입", SignalKind.LONG_ENTRY),
    ("매도 청산", SignalKind.SHORT_EXIT),
    ("Close Long", SignalKind.LONG_EXIT),
    ("exit short now", SignalKind.SHORT_EXIT),
    ("Price broke the trendline", SignalKind.INFORMATION),
    ("pivot high detected", SignalKind.INFORMATION),
    ('{"action":"buy"}', SignalKind.LONG_ENTRY),
    ('{"action":"sell","size":1}', SignalKind.SHORT_ENTRY),
    ('{"action":"close_long"}', SignalKind.LONG_EXIT),
    ("", SignalKind.UNKNOWN),
    ("hello world", SignalKind.UNKNOWN),
])
def test_classify_message_keyword_rules(message: str, expected: SignalKind) -> None:
    assert classify_message(message) == expected


def test_information_takes_precedence_over_direction_keyword() -> None:
    """LuxAlgo 'Price broke the down-trendline upward'는 information으로 분류되어야.
    'down'이나 'up' 같은 방향성 키워드가 있어도 'break/trendline'이 우선."""
    msg = "Price broke the down-trendline upward"
    assert classify_message(msg) == SignalKind.INFORMATION


def test_i3_drfx_alert_2_has_message_condition_mismatch() -> None:
    """i3_drfx alert #2: 메시지 'BUY' + condition 'bear' — 소스 불일치 (또는 저자 의도).
    메시지 전용 분류기는 long_entry로 판정하나 condition 기준으론 short.
    Tier-1 condition-trace(ADR-011 §2.1.3)가 필요한 근거 사례."""
    drfx = _REPORT["i3_drfx"]
    alert_2 = next(h for h in drfx if h["index"] == 2)
    assert alert_2["message"] == "BUY"
    assert alert_2["condition_expr"] == "bear"
    assert alert_2["signal"] == SignalKind.LONG_ENTRY.value  # 메시지 기반 v0 결과
