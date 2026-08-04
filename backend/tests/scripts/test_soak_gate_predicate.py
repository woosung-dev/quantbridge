"""[BL-003] 「1주 안정 운영」 술어를 못박는다 ([ADR-024]).

## 왜 지금 쓰나

게이트의 값이 아니라 **정의**가 이 회차의 산출물이다. 정의가 코드에만 있으면 다음 회차가
「그때는 이렇게 셌던 것 같다」로 흘러간다. 여기서 창·리셋·낱말 매핑을 고정한다.

특히 세 가지를 못박는다:

1. **UNKNOWN 을 PASS 로 접지 않는다** — 이 게이트의 존재 이유다.
2. **귀속되지 않은 시간은 세지 않는다** — 어느 커밋이 돌았는지 답할 수 없으면 0 이다.
   (실측 2026-08-04: 전 이력 56.7h 중 귀속 가능 0.46%)
3. **살아 있는 세션의 종단 lag 으로 실격시키지 않는다** — 재기동 직후에는 정상적으로 여러 봉
   뒤처졌다가 따라잡는다. 그 순간을 찍으면 거짓 실격이 되고 실격은 누적을 0 으로 되돌린다.

★**이 테스트는 DB 픽스처를 쓰지 않는다** — `conftest._test_engine` 은 autouse 가 아니라
`drop_all` 이 돌지 않는다. 소크가 살아 있어도 안전하다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from src.trading.models import SessionDeactivationReason

PIN_SHA = "f5f0688621a81af882427e2ec2cc12bc1f216871"


def _load_module() -> Any:
    """술어 모듈 동적 import (`sys.path` 오염 회피 — tests/scripts 선례)."""
    script_path = Path(__file__).parents[2] / "scripts" / "soak_gate_predicate.py"
    spec = importlib.util.spec_from_file_location("soak_gate_predicate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate() -> Any:
    return _load_module()


def _payload(**overrides: Any) -> dict[str, Any]:
    """기본 = 「고정본 스택에서 세션 하나가 2시간 무사고로 돌았다」."""
    base: dict[str, Any] = {
        "now": "2026-08-04T12:00:00+00:00",
        "sessions": [
            {
                "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                "created_at": "2026-08-04T10:00:00+00:00",
                "deactivated_at": None,
                "deactivated_reason": None,
                "last_evaluated_bar_time": "2026-08-04T11:58:00+00:00",
                "interval_seconds": 60,
            }
        ],
        "pin_events": [{"event": "up", "sha": PIN_SHA, "at": "2026-08-04T10:00:00+00:00"}],
        "samples": [
            {
                "at": "2026-08-04T11:00:00+00:00",
                "sessions": [
                    {
                        "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                        "last_evaluated_bar_time": "2026-08-04T10:58:00+00:00",
                    }
                ],
            }
        ],
        "phantom_observations": [],
        "log_coverage": [{"from": "2026-08-04T10:00:00+00:00", "to": "2026-08-04T12:00:00+00:00"}],
        "darkness": {"undecidable": 0, "total": 10},
        "db_ok": True,
        "stack_pinned": True,
        "thresholds": {"require_hours": 1.0, "require_continuous_hours": 1.0},
    }
    base.update(overrides)
    return base


# ── 정본 대조 ────────────────────────────────────────────────────────────────


def test_automatic_reasons_match_the_enum(gate: Any) -> None:
    """자동 사망 목록은 `SessionDeactivationReason` 에서 `user_stopped` 를 뺀 것이다.

    술어 모듈은 앱 코드를 import 하지 않는 **순수 함수**라 값을 복제한다. 복제본이 정본과
    갈리면 「사람이 멈춤」을 자동 사망으로 세거나 그 반대가 된다 — 둘 다 카운터를 망친다.
    """
    canonical = {r.value for r in SessionDeactivationReason} - {"user_stopped"}
    assert set(gate.AUTOMATIC_DEATH_REASONS) == canonical


# ── 낱말 매핑 ────────────────────────────────────────────────────────────────


def test_pass_requires_everything(gate: Any) -> None:
    verdict = gate.evaluate(_payload())
    assert verdict.verdict == "PASS"
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(2.0)


DEAD_SESSION = {
    "id": "aaaaaaaa-0000-4000-8000-000000000001",
    "created_at": "2026-08-04T10:00:00+00:00",
    "deactivated_at": "2026-08-04T11:00:00+00:00",
    "deactivated_reason": "position_divergence",
    "last_evaluated_bar_time": "2026-08-04T10:59:00+00:00",
    "interval_seconds": 60,
}


def test_auto_death_is_fail_and_resets(gate: Any) -> None:
    """자동 사망은 실격이고, 그 시각이 새 T0 가 되어 이전 시간을 전부 버린다."""
    # 회고 실행(`--since`)은 그 창 전체를 본다 — 사망이 창 안에 있으므로 FAIL
    retro = gate.evaluate(_payload(sessions=[DEAD_SESSION], since="2026-08-04T09:00:00+00:00"))
    assert retro.verdict == "FAIL"
    assert retro.reason_word == "실격"

    # 기본 실행은 T0 가 사망 시각으로 당겨져 이전 1시간이 **전부 사라진다**
    default = gate.evaluate(_payload(sessions=[DEAD_SESSION]))
    assert default.verdict == "FAIL"
    assert default.conditions["C1_cumulative_hours"] == pytest.approx(0.0)


def test_default_run_fails_while_the_death_is_in_the_open_window(gate: Any) -> None:
    """★기본 실행이 FAIL 을 **낼 수 있어야** 한다.

    실측 2026-08-04: 소크가 38분 만에 죽었는데 판정이 `UNKNOWN 진행중` 이었다 —
    `window_start` 가 곧 마지막 사건 시각이라 「그 시각 **초과**」 필터가 항상 비었다.
    지금 열려 있는 귀속 구간 안의 사건은 스택을 다시 올릴 때까지 FAIL 로 남아야 한다.
    """
    verdict = gate.evaluate(_payload(sessions=[DEAD_SESSION]))
    assert verdict.verdict == "FAIL"


def test_restarting_the_stack_opens_a_clean_window(gate: Any) -> None:
    """재기동은 「인지했고 새 창을 연다」는 명시적 행위다 — 그 뒤로는 FAIL 이 아니다."""
    verdict = gate.evaluate(
        _payload(
            sessions=[
                DEAD_SESSION,
                {
                    "id": "bbbbbbbb-0000-4000-8000-000000000002",
                    "created_at": "2026-08-04T11:10:00+00:00",
                    "deactivated_at": None,
                    "deactivated_reason": None,
                    "last_evaluated_bar_time": "2026-08-04T11:58:00+00:00",
                    "interval_seconds": 60,
                },
            ],
            pin_events=[
                {"event": "up", "sha": PIN_SHA, "at": "2026-08-04T10:00:00+00:00"},
                {"event": "down", "sha": PIN_SHA, "at": "2026-08-04T11:05:00+00:00"},
                {"event": "up", "sha": PIN_SHA, "at": "2026-08-04T11:10:00+00:00"},
            ],
            samples=[
                {
                    "at": "2026-08-04T11:30:00+00:00",
                    "sessions": [
                        {
                            "id": "bbbbbbbb-0000-4000-8000-000000000002",
                            "last_evaluated_bar_time": "2026-08-04T11:28:00+00:00",
                        }
                    ],
                }
            ],
            thresholds={"require_hours": 0.5, "require_continuous_hours": 0.5},
        )
    )
    assert verdict.verdict == "PASS"
    # 사망 이후(11:10~12:00)만 세어진다 — 사망 전 1시간은 T0 리셋으로 버려진다
    # (보고값은 4자리 반올림 = 0.36초 해상도)
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(50 / 60, abs=1e-4)


def test_user_stopped_is_not_a_disqualification(gate: Any) -> None:
    """사람이 멈춘 것은 실격이 아니다 — 연속 창만 끊고 누적은 잇는다."""
    payload = _payload(
        sessions=[
            {
                "id": "aaaaaaaa-0000-4000-8000-000000000001",
                "created_at": "2026-08-04T10:00:00+00:00",
                "deactivated_at": "2026-08-04T11:00:00+00:00",
                "deactivated_reason": "user_stopped",
                "last_evaluated_bar_time": "2026-08-04T10:59:00+00:00",
                "interval_seconds": 60,
            }
        ],
        samples=[],
        thresholds={"require_hours": 1.0, "require_continuous_hours": 1.0},
    )
    verdict = gate.evaluate(payload)
    assert verdict.conditions["C3_ok"] is True
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(1.0)


def test_phantom_is_a_disqualification_but_replay_lag_is_not(gate: Any) -> None:
    """`replay_lag` 는 7/7 자가치유였다 — 무해 갈래를 사망 조건에 넣지 않는다."""
    harmless = gate.evaluate(
        _payload(
            phantom_observations=[
                {"at": "2026-08-04T11:00:00+00:00", "label": "replay_lag", "session_id": "x"}
            ],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert harmless.verdict == "PASS"

    fatal = gate.evaluate(
        _payload(
            phantom_observations=[
                {"at": "2026-08-04T11:00:00+00:00", "label": "phantom", "session_id": "x"}
            ],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert fatal.verdict == "FAIL"


@pytest.mark.parametrize(
    "key",
    ["db_ok", "stack_pinned"],
)
def test_integrity_failure_is_unknown_never_pass(gate: Any, key: str) -> None:
    """★조회 실패를 「이상 없음」으로 접지 않는다."""
    verdict = gate.evaluate(_payload(**{key: False}))
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"


def test_missing_darkness_is_unknown(gate: Any) -> None:
    """`/metrics` 스크레이프 실패는 「어둠 0%」가 아니라 측정 불가다 (fail-open 방지)."""
    verdict = gate.evaluate(_payload(darkness=None))
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"


def test_short_window_is_unknown_not_fail(gate: Any) -> None:
    """시간이 모자란 것은 실패가 아니다 — 그러나 PASS 도 아니다."""
    verdict = gate.evaluate(_payload(thresholds={"require_hours": 168.0}))
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "진행중"


# ── 창(window) 규칙 ──────────────────────────────────────────────────────────


def test_unpinned_time_is_never_counted(gate: Any) -> None:
    """고정본이 아니면 **어느 커밋이 돌았는지 답할 수 없다** — 그 시간은 0 이다.

    실측 2026-08-04: 이 규칙 하나가 전 이력 56.70h 중 56.44h(99.5%)를 걸러냈다.
    """
    verdict = gate.evaluate(_payload(pin_events=[]))
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(0.0)
    assert verdict.detail["unattributed_hours"] == pytest.approx(2.0)
    assert verdict.verdict == "UNKNOWN"


def test_repin_breaks_continuity_but_keeps_cumulative(gate: Any) -> None:
    """재고정은 연속 창을 끊는다 — 같은 커밋이 24h 돌았다는 주장을 지키기 위해서다."""
    verdict = gate.evaluate(
        _payload(
            pin_events=[
                {"event": "up", "sha": "a" * 40, "at": "2026-08-04T10:00:00+00:00"},
                {"event": "pin", "sha": "b" * 40, "at": "2026-08-04T11:00:00+00:00"},
                {"event": "up", "sha": "b" * 40, "at": "2026-08-04T11:00:00+00:00"},
            ],
            thresholds={"require_hours": 1.0, "require_continuous_hours": 1.5},
        )
    )
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(2.0)
    assert verdict.conditions["C2_longest_hours"] == pytest.approx(1.0)
    assert verdict.verdict == "UNKNOWN"  # 누적은 찼지만 연속이 모자라다


def test_unverified_tail_is_trimmed_not_credited(gate: Any) -> None:
    """phantom 관측이 안 덮은 구간은 「위반」이 아니라 **안 세어진다**(구조적 방어)."""
    verdict = gate.evaluate(
        _payload(
            log_coverage=[
                {"from": "2026-08-04T10:00:00+00:00", "to": "2026-08-04T11:30:00+00:00"}
            ],
        )
    )
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(1.5)
    assert verdict.detail["unverified_hours"] == pytest.approx(0.5)


# ── tick 연속성 (C4) ─────────────────────────────────────────────────────────


def test_terminal_lag_disqualifies_an_ended_session(gate: Any) -> None:
    """실측 `0e15c3c0` — 8.65h 돌았지만 마지막 46.7분은 평가가 멈춰 있었다."""
    verdict = gate.evaluate(
        _payload(
            sessions=[
                {
                    "id": "0e15c3c0-0000-4000-8000-000000000001",
                    "created_at": "2026-08-04T10:00:00+00:00",
                    "deactivated_at": "2026-08-04T11:00:00+00:00",
                    "deactivated_reason": "user_stopped",
                    "last_evaluated_bar_time": "2026-08-04T10:13:18+00:00",  # 46.7분 뒤처짐
                    "interval_seconds": 60,
                }
            ],
            samples=[],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "FAIL"
    assert "tick_stall" in verdict.conditions["C3_violations"][0]


def test_live_session_catching_up_is_not_disqualified(gate: Any) -> None:
    """★재기동 직후 5봉 뒤처진 상태를 실격으로 세면 안 된다 (실측 2026-08-04 스택 교체).

    실격은 누적을 0 으로 되돌리므로 거짓 양성 하나가 168h 를 통째로 날린다.
    """
    verdict = gate.evaluate(
        _payload(
            sessions=[
                {
                    "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                    "created_at": "2026-08-04T10:00:00+00:00",
                    "deactivated_at": None,
                    "deactivated_reason": None,
                    "last_evaluated_bar_time": "2026-08-04T11:55:00+00:00",  # 5분 뒤처짐
                    "interval_seconds": 60,
                }
            ],
        )
    )
    assert verdict.conditions["C3_ok"] is True
    assert verdict.verdict == "PASS"


def test_frozen_bar_time_across_samples_disqualifies(gate: Any) -> None:
    """반대로 **두 표본에서 bar time 이 얼어붙으면** 정체다 — 그건 실격이다."""
    frozen = "2026-08-04T10:30:00+00:00"
    verdict = gate.evaluate(
        _payload(
            samples=[
                {
                    "at": "2026-08-04T11:00:00+00:00",
                    "sessions": [
                        {
                            "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                            "last_evaluated_bar_time": frozen,
                        }
                    ],
                },
                {
                    "at": "2026-08-04T11:30:00+00:00",
                    "sessions": [
                        {
                            "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                            "last_evaluated_bar_time": frozen,
                        }
                    ],
                },
            ],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "FAIL"
    assert "tick_stall" in verdict.conditions["C3_violations"][0]


def test_sample_gap_is_unknown_not_pass(gate: Any) -> None:
    """표본이 드물면 그 구간의 tick 연속성을 **판정할 수 없다** — PASS 로 접지 않는다."""
    verdict = gate.evaluate(
        _payload(
            samples=[],
            thresholds={
                "require_hours": 1.0,
                "require_continuous_hours": 1.0,
                "max_sample_gap_seconds": 1800,
            },
        )
    )
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"
    assert verdict.conditions["C4_sample_gaps"]
