from datetime import UTC, datetime, timedelta, timezone

import pytest

from src.common.datetime_types import AwareDateTime


class FakeDialect:
    pass


def test_aware_datetime_accepts_utc_aware():
    decorator = AwareDateTime()
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    assert decorator.process_bind_param(ts, FakeDialect()) == ts


def test_aware_datetime_accepts_other_tz():
    decorator = AwareDateTime()
    # 어떤 tz든 OK (DB에는 UTC로 변환되어 저장) — KST(+09:00)로 검증
    kst = timezone(timedelta(hours=9))
    ts = datetime(2024, 1, 1, tzinfo=kst)
    assert decorator.process_bind_param(ts, FakeDialect()) == ts


def test_aware_datetime_rejects_naive():
    decorator = AwareDateTime()
    naive = datetime(2024, 1, 1)
    with pytest.raises(ValueError, match="Naive datetime rejected"):
        decorator.process_bind_param(naive, FakeDialect())


def test_aware_datetime_passes_none():
    decorator = AwareDateTime()
    assert decorator.process_bind_param(None, FakeDialect()) is None


def test_aware_datetime_rejects_non_datetime():
    decorator = AwareDateTime()
    with pytest.raises(TypeError, match="Expected datetime"):
        decorator.process_bind_param("2024-01-01", FakeDialect())
