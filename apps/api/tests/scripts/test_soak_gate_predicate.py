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
import re
import sys
from datetime import UTC, datetime, timedelta
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
        # ★`require_windows: 1` — C1 은 이제 **창의 개수** 문턱이다 ([BL-701]).
        #   기본값 3 을 그대로 두면 2시간짜리 창 하나뿐인 이 픽스처가 PASS 를 못 낸다.
        "thresholds": {
            "require_hours": 1.0,
            "require_continuous_hours": 1.0,
            "require_windows": 1,
        },
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
            thresholds={
                "require_hours": 0.5,
                "require_continuous_hours": 0.5,
                "require_windows": 1,
            },
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


def test_the_same_observation_in_three_archives_counts_once(gate: Any) -> None:
    """★[BL-626] 매 실행이 워커 로그 전량을 다시 분류해 아카이브를 하나씩 더 남긴다.

    그래서 **한 건의 관측이 아카이브 수만큼** 들어온다. dedup 없이 세면 `총 N건` 이 아카이브
    개수에 비례해 부풀고(실측 2026-08-09 메인 체크아웃 228벌) 읽는 사람은 「관측이 늘고
    있다」로 읽는다. 실격 목록은 원래 `(at, kind, detail)` 로 접히므로 같은 코퍼스에서
    **두 숫자가 어긋난다.** 세는 단위는 아카이브가 아니라 관측이다.

    ★음성 대조는 위 `test_the_report_names_where_an_unreadable_label_came_from` 이다 —
    `at` 이 서로 다른 7건은 여전히 `총 7건` 이어야 한다(dedup 이 1 로 뭉개지 않는다).
    """
    observations = [
        {
            "at": "2026-08-04T11:00:00+00:00",
            "label": "totally_new_label",
            "session_id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
            "archive": f"phantom-2026080{i}T000000Z.json",
            "predicate_version": "2026-08-01-legacy-horizon",
        }
        for i in range(3)
    ]
    verdict = gate.evaluate(
        _payload(phantom_observations=observations, since="2026-08-04T09:00:00+00:00")
    )
    entry = verdict.detail["divergence_labels"]["sources"]["totally_new_label"]
    assert entry["count"] == 1, entry
    # 표본 예산도 같은 관측을 3번 쓰지 않는다 — 가장 오래된 아카이브 하나가 조치의 표적이다.
    assert len(entry["samples"]) == 1, entry
    assert entry["samples"][0]["archive"] == "phantom-20260800T000000Z.json"
    assert "총 " not in verdict.summary, verdict.summary


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
    # ★[BL-701] 이후 C1 도 「창 개수」다 — 재고정이 창을 둘로 쪼개 1.5h 짜리가 하나도 없다.
    assert verdict.conditions["C1_qualifying_windows"] == 0
    assert verdict.verdict == "UNKNOWN"  # 연속도 창 개수도 모자라다


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


def _frozen_bar_payload(sample_ats: list[str], frozen: str) -> dict[str, Any]:
    """bar time 이 `frozen` 에 얼어붙은 세션을 `sample_ats` 시각에 관측한 입력."""
    return _payload(
        samples=[
            {
                "at": at,
                "sessions": [
                    {
                        "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                        "last_evaluated_bar_time": frozen,
                    }
                ],
            }
            for at in sample_ats
        ],
        since="2026-08-04T09:00:00+00:00",
    )


def test_a_stall_no_bigger_than_the_sampling_grid_is_marked_undecidable(gate: Any) -> None:
    """★[BL-653] 성긴 표본(31분)에서 잰 35분 정체는 **크기를 모른다** — 「구분 불가」로 적는다.

    실측 근거: 서버 표본 125건의 간격이 중앙 13.9분 · 최대 31.0분인데 관측된 정체 크기
    다수가 31.0분 = 표본 최대 간격과 정확히 일치했다. 그 숫자는 현상이 아니라 격자다.
    """
    verdict = gate.evaluate(
        _frozen_bar_payload(
            ["2026-08-04T11:00:00+00:00", "2026-08-04T11:31:00+00:00"],
            frozen="2026-08-04T10:56:00+00:00",  # 두 번째 표본에서 lag 35.0분
        )
    )
    line = verdict.conditions["C3_violations"][0]
    assert "tick_stall" in line
    assert "구분 불가" in line, line
    assert "표본 간격 중앙 31.0분/최대 31.0분" in line, line


def test_a_stall_many_samples_wide_is_not_marked_undecidable(gate: Any) -> None:
    """★음성 대조 — 촘촘한 표본(60초)에서 잰 같은 정체는 「구분 불가」가 **아니다**.

    이 짝이 없으면 앞 시험은 항진명제다(무조건 붙는 표시는 아무것도 판별하지 않는다).
    """
    verdict = gate.evaluate(
        _frozen_bar_payload(
            [f"2026-08-04T11:0{n}:00+00:00" for n in range(6)],  # 60초 간격 6건
            frozen="2026-08-04T10:26:00+00:00",  # 첫 판정 시점 lag 35.0분
        )
    )
    line = verdict.conditions["C3_violations"][0]
    assert "tick_stall" in line
    assert "구분 불가" not in line, line
    assert "표본 간격 중앙 1.0분/최대 1.0분" in line, line
    assert "크기 35.0배" in line, line


def test_the_terminal_lag_axis_is_never_marked_undecidable(gate: Any) -> None:
    """★종단 lag 은 `deactivated_at`×`last_evaluated_bar_time` — **둘 다 DB 값**이다.

    표본 해상도에 의존하지 않으므로 여기에 「구분 불가」를 붙이면 정확한 값을 깎는 것이다.
    """
    verdict = gate.evaluate(
        _payload(
            sessions=[
                {
                    "id": "0e15c3c0-0000-4000-8000-000000000001",
                    "created_at": "2026-08-04T10:00:00+00:00",
                    "deactivated_at": "2026-08-04T11:00:00+00:00",
                    "deactivated_reason": "user_stopped",
                    "last_evaluated_bar_time": "2026-08-04T10:13:18+00:00",
                    "interval_seconds": 60,
                }
            ],
            samples=[],
            since="2026-08-04T09:00:00+00:00",
        )
    )
    line = verdict.conditions["C3_violations"][0]
    assert "종단 lag 46.7분" in line, line
    assert "구분 불가" not in line, line
    assert "표본 간격" not in line, line


def test_the_report_says_what_resolution_a_clean_run_was_measured_at(gate: Any) -> None:
    """★[BL-653] 「실격 0」이 「정지 없음」으로 읽히지 않게 해상도를 함께 낸다."""
    verdict = gate.evaluate(
        _payload(
            samples=[
                {
                    "at": at,
                    "sessions": [
                        {
                            "id": "39731d57-f3ec-45c4-b4e1-db304c72692e",
                            "last_evaluated_bar_time": at,
                        }
                    ],
                }
                for at in ("2026-08-04T11:00:00+00:00", "2026-08-04T11:10:00+00:00")
            ],
        )
    )
    assert verdict.conditions["C3_ok"] is True
    assert verdict.detail["sample_resolution"] == {
        "samples": 2,
        "median_seconds": 600.0,
        "max_seconds": 600.0,
    }


def test_a_run_without_samples_keeps_the_verdict_json_unchanged(gate: Any) -> None:
    """표본이 없으면 `sample_resolution` 키를 아예 넣지 않는다 (바이트 동일 규율)."""
    verdict = gate.evaluate(_payload(samples=[]))
    assert "sample_resolution" not in verdict.detail


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


# ── 실격 귀속 원장 ([BL-641]) ─────────────────────────────────────────────────
#
# ★이 절 전체가 지키는 것은 **하나**다: 귀속 축은 보고이지 판정이 아니다.
#   게이트를 관대하게 만드는 변경은 [ADR-024] 가 (f)·(g) 에서 두 번 거부했고, 원장이
#   셋째가 되지 않도록 여기서 못 박는다.

LEDGER_DEATH_AT = "2026-08-04T11:00:00+00:00"


def _ledger(cause: str = "operational") -> list[dict[str, Any]]:
    return [
        {"_comment": "스키마 설명 — 파서가 건너뛴다"},
        {
            "at": LEDGER_DEATH_AT,
            "kind": "auto_death",
            "session": "aaaaaaaa",
            "reason": "position_divergence",
            "cause_class": cause,
            "evidence": "테스트",
            "decided": "2026-08-08",
        },
    ]


def test_the_attribution_ledger_never_moves_the_verdict(gate: Any) -> None:
    """★핵심 오라클 — 원장을 실어도 C1~C5 는 **비트 단위로 같다**.

    귀속이 판정에 새면 그 순간 이 축은 「통과를 사는 장치」가 된다. 가장 관대한 값
    (`operational`)을 실어도 판정이 안 움직인다는 것이 그 봉쇄의 증거다.
    """
    without = gate.evaluate(_payload(sessions=[DEAD_SESSION]))
    with_ledger = gate.evaluate(
        _payload(sessions=[DEAD_SESSION], disqualification_ledger=_ledger("operational"))
    )

    assert (without.verdict, without.reason_word, without.summary) == (
        with_ledger.verdict,
        with_ledger.reason_word,
        with_ledger.summary,
    )
    assert without.conditions == with_ledger.conditions
    # 원장을 안 실은 실행의 JSON 은 이 기능이 없던 때와 바이트 단위로 같아야 한다.
    assert "disqualification_attribution" not in without.detail
    assert with_ledger.detail["disqualification_attribution"]["counts"]["operational"] == 1


def test_an_unregistered_disqualification_counts_as_undecided(gate: Any) -> None:
    """등재를 빠뜨린 실격은 **관대해지지 않는다** — `undecided` 로 센다."""
    verdict = gate.evaluate(_payload(sessions=[DEAD_SESSION], disqualification_ledger=[]))
    attribution = verdict.detail["disqualification_attribution"]

    assert attribution["counts"] == {"code_defect": 0, "operational": 0, "undecided": 1}
    assert len(attribution["unregistered"]) == 1


@pytest.mark.parametrize(
    "row",
    [
        pytest.param({"at": LEDGER_DEATH_AT, "kind": "auto_death"}, id="cause_class 누락"),
        pytest.param(
            {"at": LEDGER_DEATH_AT, "kind": "auto_death", "cause_class": "ops"},
            id="미지 낱말",
        ),
        pytest.param(
            {"at": "Error", "kind": "auto_death", "cause_class": "operational"},
            id="판독 불가 시각",
        ),
        pytest.param(
            {"kind": "auto_death", "cause_class": "operational"},
            id="시각 누락",
        ),
    ],
)
def test_a_broken_ledger_row_is_never_lenient(gate: Any, row: dict[str, Any]) -> None:
    """★fail-open 봉쇄 변이 — 원장이 깨지는 **모든** 방식이 `undecided` 로 떨어진다.

    깨진 행을 `operational` 로 접으면 「원장을 망가뜨리면 관대해진다」가 되고, 그건
    게이트를 공격하는 가장 싼 경로다.
    """
    verdict = gate.evaluate(_payload(sessions=[DEAD_SESSION], disqualification_ledger=[row]))
    attribution = verdict.detail["disqualification_attribution"]

    assert attribution["counts"]["operational"] == 0
    assert attribution["counts"]["undecided"] == 1
    assert attribution["invalid_ledger_rows"] == 1


def test_a_ledger_row_that_matches_nothing_is_reported_as_stale(gate: Any) -> None:
    """원장에만 있고 실격 목록엔 없는 행은 **원장이 낡았다**는 신호다 — 조용히 두지 않는다."""
    stale = [
        {
            "at": "2020-01-01T00:00:00+00:00",
            "kind": "auto_death",
            "cause_class": "operational",
        }
    ]
    verdict = gate.evaluate(_payload(sessions=[DEAD_SESSION], disqualification_ledger=stale))
    attribution = verdict.detail["disqualification_attribution"]

    assert attribution["stale_ledger_rows"] == ["2020-01-01T00:00:00+00:00 auto_death"]
    assert attribution["counts"]["undecided"] == 1


def test_a_different_kind_at_the_same_instant_needs_its_own_row(gate: Any) -> None:
    """★[BL-633] 의 오염 창이 이 모양이었다 — 같은 초 안에 phantom 과 auto_death 가 같이 났다.

    종류가 다르면 **다른 키**이므로 각자 원장 행이 필요하다. 하나만 등재하면 나머지는
    `undecided` 로 남는다 — 관대해지지 않는다.
    """
    same_moment_phantom = [
        {"at": LEDGER_DEATH_AT, "label": "phantom", "session_id": "aaaaaaaa"},
    ]
    verdict = gate.evaluate(
        _payload(
            sessions=[DEAD_SESSION],
            phantom_observations=same_moment_phantom,
            disqualification_ledger=_ledger("operational"),
        )
    )
    attribution = verdict.detail["disqualification_attribution"]

    assert attribution["total"] == 2
    assert attribution["counts"] == {"code_defect": 0, "operational": 1, "undecided": 1}


def test_one_ledger_row_attributes_exactly_one_disqualification(gate: Any) -> None:
    """★한 행은 **하나만** 덮는다 — 같은 `(at, kind)` 실격이 둘이면 나머지는 `undecided` 다.

    실격 dedup 키는 `(at, kind, detail)` 이라 **같은 순간 같은 종류의 서로 다른 세션**은
    둘 다 남는다. 매칭이 행을 소비하지 않으면 원장 한 줄이 그 둘을 통째로 관대하게 만든다 —
    등재 하나로 여러 실격을 사는 경로이므로 fail-open 이다.
    """
    two_sessions_one_instant = [
        {"at": LEDGER_DEATH_AT, "label": "phantom", "session_id": "aaaaaaaa"},
        {"at": LEDGER_DEATH_AT, "label": "phantom", "session_id": "bbbbbbbb"},
    ]
    ledger = [
        {"at": LEDGER_DEATH_AT, "kind": "phantom", "cause_class": "operational"},
    ]
    verdict = gate.evaluate(
        _payload(
            sessions=[DEAD_SESSION],
            phantom_observations=two_sessions_one_instant,
            disqualification_ledger=ledger,
        )
    )
    attribution = verdict.detail["disqualification_attribution"]

    assert attribution["total"] == 3  # phantom 2 + auto_death 1
    assert attribution["counts"]["operational"] == 1
    assert attribution["counts"]["undecided"] == 2


def test_a_matched_ledger_row_is_not_reported_as_stale(gate: Any) -> None:
    """매칭된 행은 소비되므로 `stale` 목록에 남지 않는다.

    ★남으면 「원장이 낡았다」 경고가 **매 실행 거짓으로** 뜨고, 그러면 진짜 낡음이 묻힌다.
    """
    verdict = gate.evaluate(
        _payload(sessions=[DEAD_SESSION], disqualification_ledger=_ledger("code_defect"))
    )
    attribution = verdict.detail["disqualification_attribution"]

    assert attribution["stale_ledger_rows"] == []
    assert attribution["counts"]["code_defect"] == 1


def test_the_shipped_ledger_is_readable_by_the_gate(gate: Any) -> None:
    """레포에 실린 원장이 **이 파서의 어휘**를 지키는지 본다.

    ★원장은 사람이 손으로 쓰는 파일이라 게이트와 갈릴 수 있고, 갈리면 조용히 전부
      `undecided` 가 된다(엄격 쪽이라 안전하지만 **아무 정보도 안 준다**). 여기서 문다.
    """
    import json

    ledger_path = (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "operations"
        / "soak-disqualifications.jsonl"
    )
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    entries = [row for row in rows if "_comment" not in row]

    assert entries, "원장이 비어 있다 — 등재된 실격이 하나도 없다"
    for row in entries:
        assert row["cause_class"] in gate.KNOWN_CAUSE_CLASSES, row
        assert row["kind"] in {"auto_death", "phantom", "tick_stall"}, row
        assert gate.parse_ts(row["at"])
        assert row.get("evidence"), f"근거 없는 귀속은 등재할 수 없다: {row}"


# ── C1 = 자격 창의 개수 ([BL-701] · [ADR-024] §C1 2026-08-11 문턱 교체) ──────


def _windows_payload(hours: list[float], **overrides: Any) -> dict[str, Any]:
    """`hours` 의 길이마다 **분리된** 창을 하나씩 만든다.

    창을 가르는 것은 `down`/`up` 이다 — 그 사이의 공백은 귀속되지 않으므로 병합되지 않는다.
    세션은 `user_stopped` 로 닫는다(사람이 멈춘 것은 실격이 아니다 — 위 규칙 참조).
    ★C4(표본 공백)를 크게 열어 둔다. 여기서 재려는 것은 **C1 한 축**이고, 24h 창 3개를
      1시간 격자로 덮으려면 표본 72개가 필요해 무엇을 재는 테스트인지 흐려진다.
    """
    base = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    gap = timedelta(minutes=10)

    sessions, pins = [], []
    cursor = base
    for i, h in enumerate(hours):
        start, end = cursor, cursor + timedelta(hours=h)
        sessions.append(
            {
                "id": f"{i:08d}-0000-4000-8000-000000000001",
                "created_at": start.isoformat(),
                "deactivated_at": end.isoformat(),
                "deactivated_reason": "user_stopped",
                "last_evaluated_bar_time": (end - timedelta(seconds=60)).isoformat(),
                "interval_seconds": 60,
            }
        )
        pins.append({"event": "up", "sha": PIN_SHA, "at": start.isoformat()})
        pins.append({"event": "down", "sha": PIN_SHA, "at": end.isoformat()})
        cursor = end + gap

    payload = _payload(
        now=cursor.isoformat(),
        sessions=sessions,
        pin_events=pins,
        samples=[],
        log_coverage=[{"from": base.isoformat(), "to": cursor.isoformat(), "classifier_ok": True}],
        thresholds={
            "require_hours": 1.0,
            "require_continuous_hours": 24.0,
            "require_windows": 3,
            "max_sample_gap_seconds": 10 * 24 * 3600,
        },
    )
    payload.update(overrides)
    return payload


def test_three_full_windows_pass(gate: Any) -> None:
    """양성 대조 — 24h 를 넘긴 창이 3개면 C1 이 찬다."""
    verdict = gate.evaluate(_windows_payload([24.1] * 3))
    assert verdict.conditions["C1_qualifying_windows"] == 3
    assert verdict.conditions["C1_ok"] is True
    assert verdict.verdict == "PASS"


def test_three_almost_full_windows_are_zero_not_three(gate: Any) -> None:
    """★음성 대조 — 23.9h 짜리 창 3개는 **0/3** 이다. 합이 71.7h 라도 아니다.

    이것이 이 술어의 판별력 전부다. 종전 문턱(누적 시간의 합)으로 세면 71.7h 가 쌓인 것으로
    보이지만, **한 번도 24h 를 연속으로 버틴 적이 없다.** 「누적」과 「연속 창의 개수」를
    가르지 못하는 구현은 이 케이스에서 갈린다 ([BL-701] 권장 접근 ⑶ 이 지정한 대조).
    """
    payload = _windows_payload([23.9] * 3)
    verdict = gate.evaluate(payload)

    assert verdict.conditions["C1_cumulative_hours"] == pytest.approx(71.7, abs=1e-3)
    assert verdict.conditions["C1_qualifying_windows"] == 0
    assert verdict.conditions["C1_ok"] is False
    assert verdict.verdict == "UNKNOWN"


def test_a_window_exactly_at_the_bar_qualifies(gate: Any) -> None:
    """경계는 **포함**이다 — 정확히 24.0h 는 자격이 있다(`>=`)."""
    verdict = gate.evaluate(_windows_payload([24.0] * 3))
    assert verdict.conditions["C1_qualifying_windows"] == 3
    assert verdict.conditions["C1_ok"] is True


def test_two_windows_are_not_enough(gate: Any) -> None:
    """2/3 은 진행중이지 통과가 아니다 — 그리고 C2 는 이미 충족이다.

    ★이 갈림이 [BL-701] 의 실제 상태다: 2026-08-11 실측이 `1/3` 이면서 `C2 ✓` 였다.
      C2 만 보고 「24h 를 넘겼으니 됐다」로 읽으면 안 된다.
    """
    verdict = gate.evaluate(_windows_payload([24.1] * 2))
    assert verdict.conditions["C1_qualifying_windows"] == 2
    assert verdict.conditions["C1_ok"] is False
    assert verdict.conditions["C2_ok"] is True
    assert verdict.verdict == "UNKNOWN"


def test_the_verdict_never_states_two_thresholds(gate: Any) -> None:
    """★출력이 문턱을 **하나만** 말한다 ([BL-701] ⑵).

    종전에는 새 문턱이 결정된 뒤에도 판정 문구가 `누적 … / 168h` 를 찍었다. 다음 회차는
    그 줄을 읽고 「아직 41% 다」로 판단한다 — 원장이 회차를 잘못 이끄는 그 병이 판정식
    층에서 재발한 것이다. 누적은 `(참고)` 로만 남는다.
    """
    for payload in (_windows_payload([23.9] * 3), _windows_payload([24.1] * 3)):
        summary = gate.evaluate(payload).summary
        assert "/ 168h" not in summary
        assert "24h 창" in summary
        assert "(참고: 누적" in summary


def test_the_window_count_threshold_is_a_named_constant(gate: Any) -> None:
    """N=3 은 `[가정]`이라 한 곳에만 있어야 한다 ([ADR-024] §C1)."""
    assert gate.DEFAULT_REQUIRE_WINDOWS == 3
    # 기본값을 쓰지 않은 실행은 `thresholds_are_default` 가 **거짓**이어야 한다 —
    # 문턱을 낮춰 통과시킨 것이 보고에서 안 보이면 그게 거짓 그린이다.
    lowered = gate.evaluate(_windows_payload([24.1], thresholds={"require_windows": 1}))
    assert lowered.detail["thresholds_are_default"] is False


def test_heterogeneous_windows_count_only_the_ones_over_the_bar(gate: Any) -> None:
    """실제 소크의 모양 — 창 길이는 제각각이고 **문턱을 넘은 것만** 센다.

    2026-08-11 서버 실측이 정확히 이 모양이었다: 귀속 창 `15.3007h · 0.0133h · 53.8225h`.
    창이 3개 있으므로 「3회 달성」으로 읽고 싶어지지만, 24h 를 넘은 것은 **하나뿐**이라 1/3 이다.
    ★C2(최장 53.82h)가 ✓ 인 것과 C1 이 1/3 인 것은 **동시에 참**이다 — 이 갈림을 못 보면
      「24h 넘겼으니 됐다」로 읽는다.
    """
    verdict = gate.evaluate(_windows_payload([15.3007, 0.0133, 53.8225]))

    assert verdict.conditions["C1_qualifying_windows"] == 1
    assert verdict.conditions["C1_ok"] is False
    assert verdict.conditions["C2_ok"] is True
    assert verdict.verdict == "UNKNOWN"


def test_the_shell_reads_only_keys_the_predicate_emits(gate: Any) -> None:
    """`soak-gate.sh` 가 읽는 `conditions` 키가 전부 판정식에 실재하는지 본다.

    ★[BL-701] 이 바로 이 두 층이 갈린 사고였다 — 문서는 새 문턱, 코드는 옛 문턱. 이번엔
      **키 이름**이 갈릴 수 있다: 판정식에서 `C1_required` 를 지웠는데 셸이 그대로 읽으면
      게이트가 서버에서 `KeyError` 로 죽는다. 로컬 pytest 는 셸을 안 부르므로 **초록이다.**
      소유자 없는 계약은 안 지켜진다 — 여기서 문다.
    """
    import re

    shell = (Path(__file__).parents[4] / "tools" / "scripts" / "soak-gate.sh").read_text(
        encoding="utf-8"
    )
    referenced = set(re.findall(r'c\["([A-Za-z0-9_]+)"\]', shell))
    assert referenced, "셸에서 conditions 참조를 하나도 못 찾았다 — 정규식이 낡았다"

    emitted = set(gate.evaluate(_payload()).conditions)
    missing = sorted(referenced - emitted)
    assert not missing, f"셸이 읽는데 판정식이 안 내는 키: {missing}"

    # ★반대 방향도 문다 (codex P2) — 옛 키가 되살아나도 위 검사는 초록이다.
    #   `C1_required` 는 「누적 문턱」을 뜻했고, 되살아나면 소비자가 그걸 문턱으로 읽는다.
    assert "C1_required" not in emitted, "옛 누적 문턱 키가 되살아났다 ([BL-701])"


def test_the_shell_passes_as_many_argv_as_the_payload_builder_reads(gate: Any) -> None:
    """`soak-gate.sh` 의 payload 빌더가 받는 인자 수와 읽는 최대 인덱스가 맞는지 본다.

    ★[BL-701] 구현 중 실제로 깨뜨렸다 — `--require-windows` 를 인자 목록 **중간**에 끼웠더니
      뒤의 `repo_root` 인덱스가 밀렸다. 이 heredoc 은 docker+DB 가 있어야 돌아서 로컬
      pytest 가 **한 번도 부르지 않는다** ⇒ 서버에서만 `IndexError` 로 죽고, 그때는
      무인 감시가 그걸 「게이트 크래시」로 알린다. 정합만이라도 여기서 문다.
    ★`gate` 픽스처를 쓰지 않지만 파라미터로 받는다 — 이 파일의 다른 케이스와 같은 모양을
      유지해 「왜 이것만 다르지」를 없앤다.
    """
    import re

    shell = (Path(__file__).parents[4] / "tools" / "scripts" / "soak-gate.sh").read_text(
        encoding="utf-8"
    )
    head = shell.index('PAYLOAD="$(python3 - \\')
    fence = shell.index("<<'PY'", head)
    passed = len(re.findall(r'"\$\{[A-Z_]+\}"', shell[head:fence]))
    body = shell[fence : fence + 2000]
    read_max = max(int(m) for m in re.findall(r"sys\.argv\[(\d+)\]", body))

    assert passed == read_max, (
        f"셸이 {passed}개를 넘기는데 파이썬은 argv[{read_max}] 까지 읽는다 — "
        "새 인자는 **목록 끝에** 붙여라"
    )

    # ★개수만 재면 `ROOT` 와 `REQUIRE_WINDOWS` 를 **서로 바꿔도 초록**이다 (codex P2).
    #   순서까지 못박는다 — 위치가 어긋나면 서버에서 경로를 문턱으로 읽는다.
    order = re.findall(r'"\$\{([A-Z_]+)\}"', shell[head:fence])
    assert order[-2:] == ["REQUIRE_WINDOWS", "ROOT"], (
        f"인자 꼬리가 {order[-2:]} 다 — REQUIRE_WINDOWS 다음이 ROOT 여야 한다"
    )


def test_coverage_gaps_do_not_forge_three_runs_out_of_one(gate: Any) -> None:
    """★한 번의 실행이 **커버리지 공백** 때문에 3회로 세어지면 안 된다 (codex P1, 2026-08-11).

    `restrict()` 는 커버리지가 덮은 조각만 남기므로, 커버리지에 내부 공백이 있으면 **하나의
    귀속 구간**이 여러 조각으로 쪼개진다. 옛 C1(합)에서는 무해했고 C2(max)에서는 오히려
    보수적이었지만, 새 C1(개수)에서는 **셈을 부풀린다.**

    그러면 「측정이 나쁠수록 점수가 오른다」가 된다 — 정확히 fail-open 이다. 그리고 문턱의
    뜻도 무너진다: 「3회」는 **세 번의 독립된 생존 시행**을 요구하는 것이지, 한 번의 실행을
    관측 공백으로 토막 낸 것이 아니다.

    ⇒ 자격 창은 **귀속 구간당 최대 1개**로 센다. 구간을 가르는 것은 `down`/`up`·재고정·실격
    같은 **운영 사건**이지 관측 공백이 아니다.
    """
    base = datetime(2026, 8, 1, tzinfo=UTC)
    end = base + timedelta(hours=74)
    payload = _payload(
        now=end.isoformat(),
        sessions=[
            {
                "id": "aaaaaaaa-0000-4000-8000-000000000001",
                "created_at": base.isoformat(),
                "deactivated_at": end.isoformat(),
                "deactivated_reason": "user_stopped",
                "last_evaluated_bar_time": (end - timedelta(seconds=60)).isoformat(),
                "interval_seconds": 60,
            }
        ],
        pin_events=[
            {"event": "up", "sha": PIN_SHA, "at": base.isoformat()},
            {"event": "down", "sha": PIN_SHA, "at": end.isoformat()},
        ],
        samples=[],
        # 0~24h · 25~49h · 50~74h — 각 조각이 24h 이고 사이에 1h 공백이 둘 있다.
        log_coverage=[
            {
                "from": (base + timedelta(hours=a)).isoformat(),
                "to": (base + timedelta(hours=b)).isoformat(),
                "classifier_ok": True,
            }
            for a, b in ((0, 24), (25, 49), (50, 74))
        ],
        thresholds={
            "require_hours": 1.0,
            "require_continuous_hours": 24.0,
            "require_windows": 3,
            "max_sample_gap_seconds": 10 * 24 * 3600,
        },
    )
    verdict = gate.evaluate(payload)

    assert verdict.conditions["C1_qualifying_windows"] == 1, (
        "커버리지 공백이 단일 실행을 3회로 위조했다 — 측정이 나쁠수록 점수가 오른다"
    )
    assert verdict.conditions["C1_ok"] is False
    assert verdict.verdict == "UNKNOWN"


# ── [BL-748] C4 의 공허 통과 ─────────────────────────────────────────────────


def test_c4_does_not_pass_when_there_is_no_window_to_look_at(gate: Any) -> None:
    """귀속 창이 0개면 C4 는 「이상 없다」가 아니라 **판정 불가**다.

    종전 `C4_ok = not gaps` 는 볼 창이 없을 때 루프가 0회라 빈 리스트를 얻고 **통과**했다.
    2026-08-15 실측이 그 증상을 그대로 보여줬다 — 같은 출력에 「C4 표본 공백 0건 ✓」와
    「표본 간격 최대 326.4분」이 함께 찍혔고, 상위 공백 5개(최대 1524.5분)가 전부 귀속 구간
    **바깥**이라 한 건도 세지지 않았다. 「볼 게 없다」가 「정상」으로 보고되는 fail-open 이다.
    """
    payload = _payload(pin_events=[])  # `up` 이 없으면 귀속 구간이 안 열린다

    verdict = gate.evaluate(payload)

    assert verdict.conditions["C4_no_window"] is True
    assert verdict.conditions["C4_ok"] is False, "볼 창이 없는데 C4 가 통과했다 (fail-open)"
    assert verdict.conditions["C4_sample_gaps"] == [], (
        "공백이 있는 것이 아니라 잴 자리가 없는 것이다"
    )
    assert verdict.verdict == "UNKNOWN"
    assert "귀속 창이 0개" in verdict.summary, (
        "「공백 0건」과 「볼 창 0개」가 같은 문장으로 찍히면 운영자가 정상으로 읽는다"
    )


def test_c4_still_passes_on_a_normal_reading(gate: Any) -> None:
    """★음성 대조 — [BL-748] 수리가 정상 판독까지 죽이면 안 된다.

    이게 없으면 `C4_ok = False` 로 고정해도 위 테스트가 통과한다(판별력 0).
    """
    verdict = gate.evaluate(_payload())

    assert verdict.conditions["C4_no_window"] is False
    assert verdict.conditions["C4_ok"] is True
    assert verdict.conditions["C4_sample_gaps"] == []
    assert verdict.verdict == "PASS", f"정상 판독이 {verdict.verdict} 로 뒤집혔다"


def test_darkness_that_is_not_a_dict_fails_c5_instead_of_passing_it(gate: Any) -> None:
    """`darkness_computed` 는 **dict 인가**를 묻는다 — `is not None` 이 아니다 ([BL-748]).

    종전에는 dict 가 아닌 값이 오면 C5 는 ✓ 인데 `_darkness_report` 는 None 을 내서
    셸이 「어둠 비율: ✗ 계산 실패 (C5 위반)」을 찍었다. **판정과 표시가 서로 다른 말을 한다.**
    """
    verdict = gate.evaluate(_payload(darkness="계산 실패"))

    assert verdict.conditions["C5"]["darkness_computed"] is False
    assert verdict.conditions["C5_ok"] is False
    assert verdict.verdict == "UNKNOWN"


def test_the_shell_and_the_predicate_agree_on_what_darkness_counts(gate: Any) -> None:
    """어둠 분자 집합이 **두 곳에 복제**돼 있다 — 갈리면 조용히 다른 것을 센다 ([BL-748]).

    `soak-gate.sh` 는 `python3 -c` 인라인으로 계산하므로 술어 모듈을 import 하지 않는다
    (그 인라인은 시스템 python 이고 술어는 `uv run python` 이다). 코드를 합칠 수 없으니
    **동등성을 여기서 못박는다.** 종전에는 술어 쪽 상수가 아무도 참조하지 않는 죽은 값이라
    셸만 고쳐도 아무 신호가 없었다.
    """
    shell = Path(__file__).parents[4] / "tools" / "scripts" / "soak-gate.sh"
    assert shell.is_file(), f"셸 게이트를 못 찾았다: {shell}"

    match = re.search(r"^\s*und = \{(.+?)\}\s*$", shell.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None, (
        "`und = {...}` 리터럴을 못 찾았다 — 셸이 바뀌었으면 이 테스트를 고쳐라"
    )
    shell_set = frozenset(re.findall(r'"([^"]+)"', match.group(1)))

    assert shell_set, "셸 리터럴을 빈 집합으로 읽었다 — 이 단언은 판별력이 없다"
    assert shell_set == gate.UNDECIDABLE_DERIVE_OUTCOMES, (
        f"셸({sorted(shell_set)})과 술어({sorted(gate.UNDECIDABLE_DERIVE_OUTCOMES)})가 갈렸다"
    )
