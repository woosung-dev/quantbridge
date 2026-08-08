"""방향 불일치 strike 창 — TTL · 봉 전진 · fail-open 방향의 단위 오라클.

왜 있나
-------
`_judge_direction_strike` 는 **세션을 죽이는 술어**다. 차분 오라클이 이 판정이 tick 에
배선돼 있는지를 재고, 이 파일은 판정 **자체**의 경계를 잰다 — 경계값은 end-to-end 픽스처로
재면 한 케이스당 tick 하나가 필요해 실제로는 재지 못한다.

★**여기서 재는 세 축이 곧 이 수리의 전부다.**
  ① TTL — strike 가 영원히 살면 몇 시간 떨어진 두 관측이 「2회 연속」이 된다.
  ② 봉 전진 — 봉이 안 지났으면 엔진은 skew 를 풀 기회를 한 번도 못 받았다.
  ③ 모름의 방향 — 봉 시각을 못 읽었을 때 **유예가 아니라 킬**이어야 한다(가드 보존).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.tasks.live_signal import (
    _DIRECTION_STRIKE_BAR_KEY,
    _DIRECTION_STRIKE_MAX_BARS,
    _direction_strike_bar,
    _direction_strike_ttl,
    _judge_direction_strike,
)

_BAR = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _judge(
    *,
    previous_strike_bar: datetime | None,
    had_previous_strike: bool = True,
    bar_time: datetime,
    interval_value: str = "1m",
):
    return _judge_direction_strike(
        previous_strike_bar=previous_strike_bar,
        had_previous_strike=had_previous_strike,
        bar_time=bar_time,
        interval_value=interval_value,
    )


# ---------------------------------------------------------------------------
# ① TTL — strike 는 영원히 살지 않는다
# ---------------------------------------------------------------------------


def test_first_observation_is_granted_grace_and_records_its_bar() -> None:
    """1회차는 죽이지 않고 **봉 시각을 남긴다** — 남기지 않으면 TTL 의 기준점이 없다."""
    verdict = _judge(previous_strike_bar=None, had_previous_strike=False, bar_time=_BAR)
    assert verdict.kill is False
    assert verdict.bar == _BAR
    assert verdict.outcome == "direction_transient"


def test_second_observation_inside_the_ttl_kills() -> None:
    """수리의 목적은 킬을 없애는 게 아니다 — 같은 에피소드의 2회차는 그대로 죽인다."""
    verdict = _judge(previous_strike_bar=_BAR, bar_time=_BAR + timedelta(minutes=1))
    assert verdict.kill is True
    assert verdict.outcome == "direction_persisted"
    # ★기준점을 **원래 strike 봉**으로 유지한다. 매 관측마다 갱신하면 TTL 이 영원히
    #   갱신돼 ①이 무효가 된다.
    assert verdict.bar == _BAR


def test_second_observation_past_the_ttl_restarts_the_window() -> None:
    """★D1 — 몇 시간 떨어진 두 관측은 「2회 연속」이 아니다. 1회차로 다시 센다."""
    stale = _BAR + timedelta(hours=5)
    verdict = _judge(previous_strike_bar=_BAR, bar_time=stale)
    assert verdict.kill is False
    assert verdict.outcome == "direction_strike_expired"
    assert verdict.bar == stale, "만료 뒤에는 **이번 봉**이 새 기준점이어야 한다"


@pytest.mark.parametrize(
    ("offset_bars", "expect_kill"),
    [
        (_DIRECTION_STRIKE_MAX_BARS, True),
        (_DIRECTION_STRIKE_MAX_BARS + 1, False),
    ],
)
def test_ttl_boundary_is_max_bars_inclusive(offset_bars: int, expect_kill: bool) -> None:
    """경계 — 상한 **이내**는 죽이고, 넘으면 유예한다.

    ★한쪽만 재면 TTL 을 무한대로 만드는 변이가 통과한다(경계 안 케이스는 원래 kill 이다).
    """
    bar_time = _BAR + timedelta(minutes=offset_bars)
    assert _judge(previous_strike_bar=_BAR, bar_time=bar_time).kill is expect_kill


def test_ttl_scales_with_the_interval_not_the_wall_clock() -> None:
    """★TTL 을 벽시계 절대값으로 잡으면 긴 interval 에서 가드가 통째로 꺼진다.

    같은 3분 간격이 1m 에서는 상한 이내이고 1h 에서는 한 봉도 안 된다 — 어느 쪽도
    만료가 아니어야 한다.
    """
    assert _direction_strike_ttl("1m") == timedelta(minutes=_DIRECTION_STRIKE_MAX_BARS)
    assert _direction_strike_ttl("1h") == timedelta(hours=_DIRECTION_STRIKE_MAX_BARS)
    hourly = _judge(
        previous_strike_bar=_BAR,
        bar_time=_BAR + timedelta(hours=1),
        interval_value="1h",
    )
    assert hourly.kill is True, "1h 전략의 다음 봉은 같은 에피소드다"


def test_unknown_interval_never_expires_the_strike() -> None:
    """봉 길이를 모르면 **오늘 행위 보존**(만료 없음)이다 — 모름으로 가드를 끄지 않는다."""
    assert _direction_strike_ttl("7m") is None
    verdict = _judge(
        previous_strike_bar=_BAR,
        bar_time=_BAR + timedelta(days=3),
        interval_value="7m",
    )
    assert verdict.kill is True


# ---------------------------------------------------------------------------
# ③ 모름의 방향 — 유예가 아니라 킬
# ---------------------------------------------------------------------------


def test_strike_without_a_recorded_bar_still_kills() -> None:
    """★이 수리 이전에 시작된 세션(봉 시각 없음)은 **오늘과 똑같이** 죽는다.

    여기서 유예하면 키 하나가 빠진 리포트만으로 가드를 영구히 끌 수 있다.
    """
    verdict = _judge(previous_strike_bar=None, bar_time=_BAR + timedelta(minutes=1))
    assert verdict.kill is True
    assert verdict.outcome == "direction_persisted"


@pytest.mark.parametrize(
    "report",
    [
        None,
        {},
        {_DIRECTION_STRIKE_BAR_KEY: None},
        {_DIRECTION_STRIKE_BAR_KEY: 12345},
        {_DIRECTION_STRIKE_BAR_KEY: "not-a-timestamp"},
        "not-a-dict",
    ],
)
def test_unreadable_strike_bar_reads_as_none(report: object) -> None:
    """reader 는 형이 깨진 값을 **조용히 통과시키지 않는다** — 전부 None(= 모름)이다."""
    assert _direction_strike_bar(report) is None


def test_naive_strike_bar_is_read_as_utc() -> None:
    """tz 없는 문자열을 그대로 빼면 아래 뺄셈이 TypeError 로 tick 을 죽인다."""
    naive = _direction_strike_bar({_DIRECTION_STRIKE_BAR_KEY: "2026-05-01T12:00:00"})
    assert naive == _BAR


def test_recorded_strike_bar_round_trips() -> None:
    """호출부가 저장하는 형식(isoformat)을 reader 가 그대로 되읽어야 한다."""
    assert _direction_strike_bar({_DIRECTION_STRIKE_BAR_KEY: _BAR.isoformat()}) == _BAR
