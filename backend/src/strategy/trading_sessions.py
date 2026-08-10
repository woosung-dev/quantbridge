"""Trading session 게이트 - 백테스트 + executor 용 hour-of-day 필터 (Sprint 7d).

빈 리스트 -> 24시간 (필터 없음). 허용 값: asia / london / ny.

시간대는 UTC 기준, half-open [start, end) 구간:
- asia   = [0, 7)   - UTC 00:00..06:59  (Asia/Tokyo 09:00-16:00)
- london = [8, 16)  - UTC 08:00..15:59  (Europe/London 08:00-16:00)
- ny     = [13, 20) - UTC 13:00..19:59  (America/New_York 09:00/09:30-16:00;
                     NYSE 개장 13:30 은 13:00 버킷으로 내림 처리됨 -
                     설계상 시간(hour) 단위이며 테스트에 고정됨.)

이 필터는 두 곳에서 사용된다:
1. 백테스트 엔진 - 각 bar 의 timestamp hour 가 진입을 게이팅한다.
2. 라이브 executor - 현재 wall-clock UTC hour 가 주문 접수를 게이팅한다.

두 경로 모두 tz-aware datetime 을 전달해야 한다. naive datetime 은 암묵적
local-time 해석을 막기 위해 ValueError 를 raise 한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum


class TradingSession(StrEnum):
    asia = "asia"
    london = "london"
    ny = "ny"


# Half-open [start, end) hour ranges in UTC.
SESSION_UTC_HOURS: dict[TradingSession, tuple[int, int]] = {
    TradingSession.asia: (0, 7),
    TradingSession.london: (8, 16),
    TradingSession.ny: (13, 20),
}

SESSION_VALUES: frozenset[str] = frozenset(s.value for s in TradingSession)


def is_allowed(sessions: list[str], ts: datetime) -> bool:
    """True if `ts` falls inside any of the listed sessions.

    - Empty sessions → always True (no filter).
    - Unknown session names are silently skipped (defensive: schema layer already
      validates, but we don't want to crash the executor on legacy data).
    - `ts` must be tz-aware; naïve datetimes raise ValueError to avoid accidental
      local-time interpretation.
    """
    if not sessions:
        return True
    if ts.tzinfo is None:
        raise ValueError("trading_sessions filter requires a timezone-aware datetime")
    hour = ts.astimezone(UTC).hour
    for name in sessions:
        try:
            session = TradingSession(name)
        except ValueError:
            continue
        start, end = SESSION_UTC_HOURS[session]
        if start <= hour < end:
            return True
    return False


def validate_session_names(sessions: list[str]) -> list[str]:
    """Return the list unchanged if all names are valid; else raise ValueError.

    Used by Pydantic validators so that API inputs reject unknown names up front.
    """
    invalid = [s for s in sessions if s not in SESSION_VALUES]
    if invalid:
        raise ValueError(f"unknown trading_sessions: {invalid}. Allowed: {sorted(SESSION_VALUES)}")
    return sessions
