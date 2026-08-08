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
        "log_coverage": [
            {
                "from": "2026-08-04T10:00:00+00:00",
                "to": "2026-08-04T12:00:00+00:00",
                "classifier_ok": True,
            }
        ],
        "darkness": {"undecidable": 0, "total": 10},
        "db_ok": True,
        "stack_pinned": True,
        "aof_ok": True,
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


def test_parse_ts_reads_every_microsecond_width(gate: Any) -> None:
    """Postgres 는 마이크로초의 뒤 0 을 지운다 — 그래서 자릿수가 1~6 으로 흔들린다.

    `datetime.fromisoformat` 이 임의 자릿수를 받아주기 시작한 것은 **Python 3.11** 부터다.
    3.10 은 3자리/6자리만 허용해 ValueError 로 죽는다. 이 테스트가 없으면 게이트는 개발자의
    Python 버전에 조용히 묶인다 — 2026-08-07 에 실제로 그랬다(맥 3.14 통과 / 서버 3.10 크래시).
    """
    expected = gate.parse_ts("2026-07-27T03:02:25.796480+00:00")
    for text in (
        "2026-07-27T03:02:25.79648+00:00",  # ★5자리 — 서버를 죽인 실제 값
        "2026-07-27 03:02:25.79648+00",  # psql 기본 표기
        "2026-07-27T03:02:25.79648Z",
    ):
        assert gate.parse_ts(text) == expected, text

    # 자릿수를 넘겨도 잘라 읽는다 (나노초 표기 방어)
    assert gate.parse_ts("2026-07-27T03:02:25.7964801+00:00") == expected
    # 소수점이 없는 표기는 그대로다
    assert gate.parse_ts("2026-07-27T03:02:25+00:00").microsecond == 0


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


def test_a_later_archive_relabelling_the_same_observation_disqualifies_it(gate: Any) -> None:
    """★★판별식의 **절단 약점**이 왜 ≤1 표본 주기만 노출되는지를 산문이 아니라 여기서 못박는다.

    회복식(`classify_direction_divergence.py`)은 「같은 스트림의 다음 관측이 바로 다음
    tick 인가」로 판정하므로, **창의 마지막 관측은 후속자가 아직 없어 판정 불가**이고 종전
    식으로 내려간다. 그 순간 라벨이 `replay_lag` 이면 그 실행에서는 실격이 안 잡힌다.

    그런데 `soak-gate.sh` 는 매 실행이 워커 로그를 **통째로** 재분류하고, 게이트는 **모든**
    `.soak/phantom-*.json` 의 verdict 를 **합집합**으로 모은다. 그래서 다음 실행이 같은 `at`
    을 `phantom` 으로 다시 매기면 `window_start` 가 **소급 정정**된다 — 노출은 표본 주기
    (30분) 이하다.

    ★이 성질이 없으면 절단 약점은 영구 fail-open 이다. 그러니 산문으로 두지 않는다.
    """
    older = {"at": "2026-08-04T11:00:00+00:00", "label": "replay_lag", "session_id": "x"}
    newer = {"at": "2026-08-04T11:00:00+00:00", "label": "phantom", "session_id": "x"}

    # 앞 실행만 있으면 무해로 읽힌다 — 그게 절단 순간의 모습이다.
    assert gate.evaluate(_payload(phantom_observations=[older])).verdict == "PASS"

    # 뒤 실행이 같은 관측을 다시 매기면 합집합이 실격을 되찾는다.
    healed = gate.evaluate(_payload(phantom_observations=[older, newer]))
    assert healed.verdict == "FAIL"
    assert healed.conditions["C3_violations"] == ["2026-08-04T11:00:00+00:00 phantom x phantom"]


def test_the_union_never_retracts_a_phantom_once_archived(gate: Any) -> None:
    """★음성 대조 — 방향은 **한쪽뿐**이다. 뒤 실행이 무해로 바꿔도 실격은 안 사라진다.

    이게 「옛 아카이브를 `.soak/superseded-<판>/` 로 **옮겨야** 개선이 게이트에 반영된다」
    ([ADR-024] §아카이브 판)의 코드 쪽 근거다. 판별식을 고치는 것만으로는 취소되지 않는다.
    """
    phantom = {"at": "2026-08-04T11:00:00+00:00", "label": "phantom", "session_id": "x"}
    retraction = {"at": "2026-08-04T11:00:00+00:00", "label": "replay_lag", "session_id": "x"}

    assert gate.evaluate(_payload(phantom_observations=[phantom, retraction])).verdict == "FAIL"


# ── 라벨 어휘 ([BL-596]) ─────────────────────────────────────────────────────


def test_an_unknown_label_is_measurement_failure_not_silence(gate: Any) -> None:
    """★게이트가 **모르는 라벨**을 조용히 무해로 접지 않는다 ([BL-596]).

    판별식은 2026-08-05 하루에만 두 번 바뀌었다(봉경계식 → 재무장식 → 회복식). 라벨 어휘가
    분류기 쪽에서 늘어났는데 게이트가 그걸 모르면 **그 관측 전부가 무해**가 되고, 실격을
    놓치면 `window_start` 가 앞당겨져 누적이 는다 — 정확히 fail-open 이다.

    ★단 **소급 실격도 아니다.** 모르는 라벨은 「그게 유령이었는지 아닌지 우리가 모른다」이지
    「유령이었다」가 아니다. 그래서 C3 는 비고 C5(측정 무결성)가 떨어진다.
    """
    verdict = gate.evaluate(
        _payload(
            phantom_observations=[
                {"at": "2026-08-04T11:00:00+00:00", "label": "totally_new_label", "session_id": "x"}
            ],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"
    assert verdict.conditions["C5"]["divergence_labels_readable"] is False
    assert verdict.detail["divergence_labels"]["unknown"] == ["totally_new_label"]
    # 실격으로 세지도 않는다 — T0 는 그대로다
    assert verdict.conditions["C3_violations"] == []
    assert verdict.detail["window_start"] == "2026-08-04T09:00:00+00:00"


def test_unattributed_stops_the_clock_instead_of_passing(gate: Any) -> None:
    """`unattributed` 는 「판정하지 못했다」이지 「무해하다」가 아니다 ([BL-596]).

    세션 소유 체결이 없어(운영자 청산 등) 어느 식도 판정하지 못한 관측이다. 무해로 접으면
    그 발산은 아무 데도 안 잡힌다. **어휘 밖 라벨과 같은 갈래로 떨어지되**, 보고에서는
    갈라 보인다 — 조치가 다르기 때문이다(어휘 밖 = 게이트를 분류기에 맞춰라 /
    `unattributed` = 그 발산은 사람이 봐야 한다).
    """
    verdict = gate.evaluate(
        _payload(
            phantom_observations=[
                {"at": "2026-08-04T11:00:00+00:00", "label": "unattributed", "session_id": "x"}
            ],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"
    assert verdict.conditions["C5"]["divergence_labels_readable"] is False
    buckets = verdict.detail["divergence_labels"]
    assert buckets["undecidable"] == ["unattributed"]
    assert buckets["unknown"] == []


def test_an_observation_without_a_label_is_not_readable_either(gate: Any) -> None:
    """`label` 키가 아예 없는 아카이브 항목도 무해가 아니다 — 「모른다」쪽으로 떨어진다.

    현행 분류기는 언제나 `label` 을 쓰지만(`as_dict`), 게이트는 **옛 판의 아카이브**도 같이
    읽는다. 형태가 다른 항목을 조용히 무해로 접으면 그게 곧 fail-open 이다.
    """
    verdict = gate.evaluate(
        _payload(
            phantom_observations=[{"at": "2026-08-04T11:00:00+00:00", "session_id": "x"}],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "UNKNOWN"
    assert verdict.detail["divergence_labels"]["unknown"] == [""]


def test_the_report_names_where_an_unreadable_label_came_from(gate: Any) -> None:
    """★라벨 이름만으로는 **조치를 고를 수 없다** — 출처가 같이 나와야 한다 (codex P1).

    「frozenset 에 등재한다」와 「구판 아카이브를 `.soak/superseded-<판>/` 로 옮긴다」는 서로
    다른 조치인데, 게이트 출력이 라벨 이름만 주면 운영자가 둘을 가를 수 없다. 그래서
    `scripts/soak-gate.sh` 가 합병 때 `archive`/`predicate_version` 을 붙이고 판정기는 그것을
    **라벨별로** 되돌려준다. ★같은 관측이 매 실행 재분류로 수백 건 불어나므로 표본은 상한을
    두고 총계를 따로 낸다.
    """
    observations = [
        {
            "at": f"2026-08-04T11:0{i}:00+00:00",
            "label": "totally_new_label",
            "session_id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
            "archive": f"phantom-2026080{i}T000000Z.json",
            "predicate_version": "2026-08-01-legacy-horizon",
        }
        for i in range(7)
    ]
    verdict = gate.evaluate(
        _payload(phantom_observations=observations, since="2026-08-04T09:00:00+00:00")
    )
    entry = verdict.detail["divergence_labels"]["sources"]["totally_new_label"]

    # 총계는 전량, 표본은 상한까지만
    assert entry["count"] == 7
    assert len(entry["samples"]) == gate.MAX_UNREADABLE_LABEL_SAMPLES
    assert entry["samples"][0] == {
        "archive": "phantom-20260800T000000Z.json",
        "predicate_version": "2026-08-01-legacy-horizon",
        "at": "2026-08-04T11:00:00+00:00",
        "session": "39731d57",
    }
    # 요약 줄만 보는 실행(`--json` 아님)에서도 첫 출처가 보인다
    assert "phantom-20260800T000000Z.json" in verdict.summary
    assert "총 7건" in verdict.summary


def test_a_source_less_observation_still_reports_what_it_has(gate: Any) -> None:
    """출처 필드가 없는 payload(손으로 만든 것 · 옛 아카이브)도 판정은 그대로 간다.

    없는 필드는 **빼고** 낸다 — `archive=None` 같은 항목을 보고에 실으면 「출처가 있는데
    비었다」로 읽힌다.
    """
    verdict = gate.evaluate(
        _payload(
            phantom_observations=[{"at": "2026-08-04T11:00:00+00:00", "label": "unattributed"}],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "UNKNOWN"
    assert verdict.detail["divergence_labels"]["sources"]["unattributed"]["samples"] == [
        {"at": "2026-08-04T11:00:00+00:00"}
    ]


def test_an_unreadable_label_never_downgrades_a_disqualification(gate: Any) -> None:
    """★래칫 — 어휘 검사는 **관대해지는 방향으로 쓰이지 않는다.**

    실격(FAIL)과 측정 무결성 실패(UNKNOWN)가 같은 창에 있으면 **FAIL 이 이긴다.** 반대로
    접으면 모르는 라벨 하나를 섞는 것만으로 진짜 유령이 UNKNOWN 으로 덮인다.
    """
    verdict = gate.evaluate(
        _payload(
            phantom_observations=[
                {"at": "2026-08-04T11:00:00+00:00", "label": "phantom", "session_id": "x"},
                {
                    "at": "2026-08-04T11:10:00+00:00",
                    "label": "totally_new_label",
                    "session_id": "x",
                },
            ],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    assert verdict.verdict == "FAIL"
    assert verdict.conditions["C5"]["divergence_labels_readable"] is False


@pytest.mark.parametrize(
    ("label", "expected_verdict", "expected_hours"),
    [
        (None, "PASS", 2.0),
        ("replay_lag", "PASS", 2.0),
        # 회고 실행(`--since`)은 창을 강제하므로 T0 리셋이 없다 — 실격이어도 누적은 2.0h 다
        ("phantom", "FAIL", 2.0),
    ],
)
def test_known_labels_only_is_judged_exactly_as_before(
    gate: Any, label: str | None, expected_verdict: str, expected_hours: float
) -> None:
    """★동결 — 현행 코퍼스(라벨이 `phantom`/`replay_lag` 뿐)의 판정은 [BL-596] 수리 전후
    **완전히 같다.**

    어휘 검사는 새 갈래를 **추가**할 뿐 기존 갈래를 건드리지 않는다. 이 케이스가 없으면
    「모르는 라벨을 잡았다」는 개선이 조용히 아는 라벨의 판정까지 바꿔도 안 보인다.
    """
    observations = (
        []
        if label is None
        else [{"at": "2026-08-04T11:00:00+00:00", "label": label, "session_id": "x"}]
    )
    verdict = gate.evaluate(
        _payload(phantom_observations=observations, since="2026-08-04T09:00:00+00:00")
    )
    assert verdict.verdict == expected_verdict
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(expected_hours)
    assert verdict.conditions["C5"]["divergence_labels_readable"] is True
    assert verdict.detail["divergence_labels"] == {
        "undecidable": [],
        "unknown": [],
        "sources": {},
    }


@pytest.mark.parametrize(
    "key",
    ["db_ok", "stack_pinned", "aof_ok"],
)
def test_integrity_failure_is_unknown_never_pass(gate: Any, key: str) -> None:
    """★조회 실패를 「이상 없음」으로 접지 않는다."""
    verdict = gate.evaluate(_payload(**{key: False}))
    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"


def test_readable_aof_is_required_for_pass(gate: Any) -> None:
    """[BL-594] redis 가 재기동 가능해야 PASS 다 — 「지금 떠 있다」로는 부족하다.

    AOF 는 **기동 시에만** 읽힌다. healthcheck(`redis-cli ping`)는 떠 있는 프로세스에만
    물으므로 판독 불가 AOF 를 6일 동안 못 봤다(실측 2026-08-05: 35.6MB 중 86.6% 판독 불가).
    소크 창 안에 호스트 재부팅이 들어오면 그 순간 워커가 안 뜬다.
    """
    ok = gate.evaluate(_payload())
    assert ok.conditions["C5"]["aof_ok"] is True
    assert ok.verdict == "PASS"

    broken = gate.evaluate(_payload(aof_ok=False))
    assert broken.conditions["C5"]["aof_ok"] is False
    assert broken.verdict == "UNKNOWN"
    assert "aof_ok" in broken.summary


def test_absent_aof_key_is_not_a_pass(gate: Any) -> None:
    """★키가 없으면 「이상 없음」이 아니라 **측정 못 했다**이다 (fail-closed).

    수집기(`soak-gate.sh`)가 이 필드를 못 채우는 갈래 — docker exec 실패, 컨테이너 부재,
    옛 payload — 가 전부 여기로 온다. 기본값을 `True` 로 두면 수집이 죽은 채 게이트가
    초록으로 남는다(fail-open).
    """
    payload = _payload()
    payload.pop("aof_ok")

    verdict = gate.evaluate(payload)
    assert verdict.conditions["C5"]["aof_ok"] is False
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
                {
                    "from": "2026-08-04T10:00:00+00:00",
                    "to": "2026-08-04T11:30:00+00:00",
                    "classifier_ok": True,
                }
            ],
        )
    )
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(1.5)
    assert verdict.detail["unverified_hours"] == pytest.approx(0.5)


# ── codex 적대 리뷰(2026-08-05)가 낸 거짓 PASS 경로 ──────────────────────────


def test_concurrent_sessions_do_not_double_count(gate: Any) -> None:
    """★두 세션이 같은 시간에 살아 있어도 그 시간은 **한 번만** 센다.

    유저당 활성 세션이 5개까지 허용되므로(CONTEXT.md), 단순 합산이면 세션 2개로 84시간 만에
    168h 를 만들 수 있다. codex 적대 리뷰가 잡은 P1 이고 실제로 도달 가능한 경로다.
    """
    twin = {
        "id": "bbbbbbbb-0000-4000-8000-000000000002",
        "created_at": "2026-08-04T10:00:00+00:00",
        "deactivated_at": None,
        "deactivated_reason": None,
        "last_evaluated_bar_time": "2026-08-04T11:58:00+00:00",
        "interval_seconds": 60,
    }
    base = _payload()
    both = gate.evaluate(_payload(sessions=[*base["sessions"], twin]))
    assert both.conditions["C1_cumulative_hours"] == pytest.approx(2.0)
    assert both.conditions["C2_longest_hours"] == pytest.approx(2.0)


def test_time_before_the_operator_reopens_is_not_credited(gate: Any) -> None:
    """★실격 시점에 **이미 열려 있던** 귀속 구간은 세지 않는다.

    죽은 뒤 운영자가 알아채기 전까지 흐른 시간이 PASS 누적에 들어가면 안 된다. 새 창을 여는
    `soak-stack.sh up` 이 인지 행위이므로, 그 뒤에 시작한 구간만 유효하다.
    """
    verdict = gate.evaluate(
        _payload(
            sessions=[
                DEAD_SESSION,
                {
                    "id": "bbbbbbbb-0000-4000-8000-000000000002",
                    "created_at": "2026-08-04T11:05:00+00:00",
                    "deactivated_at": None,
                    "deactivated_reason": None,
                    "last_evaluated_bar_time": "2026-08-04T11:58:00+00:00",
                    "interval_seconds": 60,
                },
            ],
            # 사망(11:00) 뒤로도 같은 귀속 구간이 열려 있다 — 새 `up` 이 없다
            pin_events=[{"event": "up", "sha": PIN_SHA, "at": "2026-08-04T10:00:00+00:00"}],
        )
    )
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(0.0)
    assert verdict.verdict == "FAIL"


def test_broken_classifier_archive_is_not_coverage(gate: Any) -> None:
    """★분류기가 깨져서 만든 껍데기 아카이브를 「검증됨」으로 읽지 않는다 (fail-open 방지).

    실측 2026-08-05: 시스템 python3 로 돌렸더니 분류기가 조용히 실패해 verdicts 가 늘 0 이었다.
    그걸 커버리지로 인정하면 그 시간이 credit 되고 진짜 phantom 도 숨는다.
    """
    verdict = gate.evaluate(
        _payload(
            log_coverage=[
                {
                    "from": "2026-08-04T10:00:00+00:00",
                    "to": "2026-08-04T12:00:00+00:00",
                    "classifier_ok": False,
                }
            ],
        )
    )
    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(0.0)
    assert verdict.conditions["C5"]["phantom_archive"] is False
    assert verdict.verdict == "UNKNOWN"


def test_empty_sample_does_not_fill_another_sessions_gap(gate: Any) -> None:
    """★다른 세션의 row 가 없는 표본은 그 세션의 공백을 메우지 못한다.

    활성 세션 조회가 실패해 `sessions: []` 로 기록된 표본이 모든 세션의 C4 를 통과시키던
    경로다(codex P1). 표본은 그 세션의 row 를 담고 있을 때만 증거다.
    """
    verdict = gate.evaluate(
        _payload(
            samples=[{"at": "2026-08-04T11:00:00+00:00", "sessions": []}],
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


# ── 판독 불가 로그 커버리지 ([BL-003]) ──────────────────────────────────────


def test_unparseable_log_coverage_yields_measurement_unavailable(
    gate: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """이 수리는 PASS 를 더 어렵게 만든다. 게이트가 더 자주 UNKNOWN 에 머무는 것은 퇴보가
    아니라 의도다 — 되돌리지 마라.

    판독 불가 시각은 수집 실패이지 검증된 빈 로그가 아니다. 판정과 CLI 종료 코드가 모두
    `측정불가` 계약을 지켜야 운영자가 실격과 구별할 수 있다.
    """
    from io import StringIO

    polluted = _payload(log_coverage=[{"from": "Error", "to": "Error", "classifier_ok": True}])
    verdict = gate.evaluate(polluted)

    assert verdict.verdict == "UNKNOWN"
    assert verdict.reason_word == "측정불가"
    report = verdict.detail["unreadable_log_coverage"]
    assert report["count"] == 1
    assert report["samples"] == [{"from": "Error", "to": "Error"}]

    stdin = StringIO(gate.json.dumps(polluted))
    stdout = StringIO()
    monkeypatch.setattr(gate.sys, "stdin", stdin)
    monkeypatch.setattr(gate.sys, "stdout", stdout)

    assert gate.main() == 2
    assert gate.json.loads(stdout.getvalue())["reason_word"] == "측정불가"


def test_unparseable_log_coverage_does_not_credit_time(gate: Any) -> None:
    """이 수리는 PASS 를 더 어렵게 만든다. 게이트가 더 자주 UNKNOWN 에 머무는 것은 퇴보가
    아니라 의도다 — 되돌리지 마라.

    판독 불가 항목만 있을 때는 0시간이고, 정상 2시간과 섞여도 추가 시간을 credit 하지 않는다.
    """
    unreadable = {"from": "Error", "to": "Error", "classifier_ok": True}

    only_unreadable = gate.evaluate(_payload(log_coverage=[unreadable]))
    clean_payload = _payload()
    clean = gate.evaluate(clean_payload)
    mixed = gate.evaluate(_payload(log_coverage=[*clean_payload["log_coverage"], unreadable]))

    assert only_unreadable.conditions["C1_cumulative_hours"] == 0.0
    assert mixed.conditions["C1_cumulative_hours"] == clean.conditions["C1_cumulative_hours"]


def test_disqualification_outranks_measurement_unavailable(gate: Any) -> None:
    """이 수리는 PASS 를 더 어렵게 만든다. 게이트가 더 자주 UNKNOWN 에 머무는 것은 퇴보가
    아니라 의도다 — 되돌리지 마라.

    진짜 phantom 실격은 같은 입력의 판독 불가 커버리지보다 항상 앞선다.
    """
    verdict = gate.evaluate(
        _payload(
            phantom_observations=[
                {"at": "2026-08-04T11:00:00+00:00", "label": "phantom", "session_id": "x"}
            ],
            log_coverage=[{"from": "Error", "to": "Error", "classifier_ok": True}],
            since="2026-08-04T09:00:00+00:00",
        )
    )

    assert verdict.verdict == "FAIL"
    assert verdict.reason_word == "실격"


def test_measurement_unavailable_never_precedes_the_disqualification_check(gate: Any) -> None:
    """이 수리는 PASS 를 더 어렵게 만든다. 게이트가 더 자주 UNKNOWN 에 머무는 것은 퇴보가
    아니라 의도다 — 되돌리지 마라.

    네 조합은 C3 실격이 판독 불가 분기보다 먼저임을 고정하고, FAIL에서도 오염 보고가 남는지
    확인한다.
    """
    phantom = [{"at": "2026-08-04T11:00:00+00:00", "label": "phantom", "session_id": "x"}]
    unreadable = [{"from": "Error", "to": "Error", "classifier_ok": True}]
    cases = {
        (False, False): (_payload(), ("PASS", "")),
        (False, True): (_payload(log_coverage=unreadable), ("UNKNOWN", "측정불가")),
        (True, False): (
            _payload(phantom_observations=phantom, since="2026-08-04T09:00:00+00:00"),
            ("FAIL", "실격"),
        ),
        (True, True): (
            _payload(
                phantom_observations=phantom,
                log_coverage=unreadable,
                since="2026-08-04T09:00:00+00:00",
            ),
            ("FAIL", "실격"),
        ),
    }

    verdicts = {combination: gate.evaluate(payload) for combination, (payload, _) in cases.items()}

    assert {
        combination: (verdict.verdict, verdict.reason_word)
        for combination, verdict in verdicts.items()
    } == {combination: expected for combination, (_, expected) in cases.items()}
    assert verdicts[(True, True)].detail["unreadable_log_coverage"]["count"] == 1
