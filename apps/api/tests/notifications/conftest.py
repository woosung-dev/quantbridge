"""notifications 테스트 fixture — VAPID 설정을 테스트마다 **명시로** 켜고 끈다.

★루트 conftest 가 `VAPID_*` 를 비우지만, 「꺼져 있다」에 기대는 테스트도 `vapid_off` 로 직접
선언한다 — 기본값이 바뀌어도 이 테스트들이 무엇을 재는지는 바뀌지 않게.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from tests.notifications.helpers import VAPID


@pytest.fixture
def vapid_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.core.config.settings.vapid_public_key", VAPID.public_key)
    monkeypatch.setattr("src.core.config.settings.vapid_private_key", SecretStr(VAPID.private_key))
    monkeypatch.setattr("src.core.config.settings.vapid_subject", VAPID.subject)


@pytest.fixture
def vapid_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.core.config.settings.vapid_public_key", None)
    monkeypatch.setattr("src.core.config.settings.vapid_private_key", None)
    monkeypatch.setattr("src.core.config.settings.vapid_subject", None)
