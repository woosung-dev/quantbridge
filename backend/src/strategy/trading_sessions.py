"""Trading session gate - hour-of-day filter for backtest + executor (Sprint 7d).

Empty list -> 24h (no filter). Allowed values: asia / london / ny.

Hour ranges are UTC, half-open [start, end) in hours:
- asia   = [0, 7)   - UTC 00:00..06:59  (Asia/Tokyo 09:00-16:00)
- london = [8, 16)  - UTC 08:00..15:59  (Europe/London 08:00-16:00)
- ny     = [13, 20) - UTC 13:00..19:59  (America/New_York 09:00/09:30-16:00;
                     the 13:30 NYSE open is rounded down to the 13:00 bucket -
                     hour-granular by design, pinned in tests.)

The filter is used in two places:
1. Backtest engine - each bar's timestamp hour gates entries.
2. Live executor - the current wall-clock UTC hour gates order acceptance.

Both code paths pass a tz-aware datetime. Naive datetimes raise ValueError to
prevent silent local-time interpretation.
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
        raise ValueError(
            f"unknown trading_sessions: {invalid}. Allowed: {sorted(SESSION_VALUES)}"
        )
    return sessions
