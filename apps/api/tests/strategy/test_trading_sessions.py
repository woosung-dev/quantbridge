"""Sprint 7d — trading_sessions hour filter unit tests."""
from __future__ import annotations

from datetime import UTC, datetime, timezone

import pytest

from src.strategy.trading_sessions import (
    SESSION_UTC_HOURS,
    TradingSession,
    is_allowed,
    validate_session_names,
)


def _utc(hour: int) -> datetime:
    return datetime(2026, 4, 19, hour, 0, 0, tzinfo=UTC)


def test_empty_sessions_allows_any_hour():
    assert is_allowed([], _utc(0)) is True
    assert is_allowed([], _utc(23)) is True


def test_naive_datetime_raises():
    with pytest.raises(ValueError, match="timezone-aware"):
        is_allowed(["asia"], datetime(2026, 4, 19, 5))


@pytest.mark.parametrize(
    "hour,sessions,expected",
    [
        # 09 UTC → asia 밖(>=7), london 내부 [8,16), ny 밖(<13)
        (9, ["asia"], False),
        (9, ["london"], True),
        (9, ["ny"], False),
        # 14 UTC → london + ny 교집합
        (14, ["asia"], False),
        (14, ["london"], True),
        (14, ["ny"], True),
        (14, ["london", "ny"], True),
        # 22 UTC → 모두 차단
        (22, ["asia", "london", "ny"], False),
        # 0 UTC → asia
        (0, ["asia"], True),
        (0, ["london"], False),
        # 7 UTC → asia 밖 (half-open [0,7))
        (7, ["asia"], False),
        # 8 UTC → london 포함
        (8, ["london"], True),
        # 16 UTC → london 밖 [8,16), ny 내부
        (16, ["london"], False),
        (16, ["ny"], True),
        # 20 UTC → ny 밖 [13,20)
        (20, ["ny"], False),
    ],
)
def test_session_hour_coverage(hour, sessions, expected):
    assert is_allowed(sessions, _utc(hour)) is expected


def test_nonutc_timezone_converted():
    """KST(UTC+9) 14:00 == UTC 05:00 → asia ✓, london ✗."""
    from datetime import timedelta

    kst_tz = timezone(timedelta(hours=9))
    ts = datetime(2026, 4, 19, 14, 0, tzinfo=kst_tz)  # UTC 05:00

    assert is_allowed(["asia"], ts) is True
    assert is_allowed(["london"], ts) is False


def test_unknown_session_name_silently_skipped_in_filter():
    """실행 경로에서는 invalid name이 있어도 crash하지 않고 그냥 무시한다.

    (schema 레이어가 validate_session_names로 입력을 이미 정제함. 이 테스트는
     legacy DB row 등에 대한 방어 동작을 고정.)
    """
    assert is_allowed(["bogus"], _utc(14)) is False
    assert is_allowed(["bogus", "london"], _utc(14)) is True


def test_validate_session_names_accepts_known():
    assert validate_session_names([]) == []
    assert validate_session_names(["asia"]) == ["asia"]
    assert validate_session_names(["asia", "london", "ny"]) == ["asia", "london", "ny"]


def test_validate_session_names_rejects_unknown():
    with pytest.raises(ValueError, match="unknown trading_sessions"):
        validate_session_names(["tokyo"])
    with pytest.raises(ValueError):
        validate_session_names(["asia", "bogus"])


def test_ny_range_rounds_to_hour_bucket():
    """NYSE 13:30 open → spec은 hour-granular로 13:00 bucket에 포함.

    이 동작을 테스트로 pin — 향후 30분 granularity로 바꾸면 테스트가 실패하며
    명시적 결정을 강제.
    """
    assert SESSION_UTC_HOURS[TradingSession.ny] == (13, 20)
    assert is_allowed(["ny"], _utc(13)) is True  # 13:30 open이지만 13시 bucket 허용
    assert is_allowed(["ny"], _utc(12)) is False
