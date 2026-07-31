"""StrategySettings의 라이브 조건부 진입 상한 설정을 검증한다."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.strategy.schemas import (
    StrategySettings,
    UpdateStrategySettingsRequest,
    validate_strategy_settings,
)


def _settings_data() -> dict[str, object]:
    return {
        "leverage": 2,
        "margin_mode": "cross",
        "position_size_pct": 10,
    }


def test_max_trigger_breach_pct_defaults_to_none() -> None:
    settings = StrategySettings(**_settings_data())

    assert settings.max_trigger_breach_pct is None


def test_fill_timing_defaults_to_bar_close() -> None:
    settings = StrategySettings(**_settings_data())
    update = UpdateStrategySettingsRequest(**_settings_data())

    assert settings.fill_timing == "bar_close"
    assert update.fill_timing == "bar_close"


def test_legacy_settings_without_new_field_still_parse() -> None:
    settings = validate_strategy_settings(_settings_data())

    assert settings is not None
    assert settings.max_trigger_breach_pct is None


def test_legacy_settings_without_fill_timing_still_parse() -> None:
    settings = validate_strategy_settings(_settings_data())

    assert settings is not None
    assert settings.fill_timing == "bar_close"


def test_update_request_mirrors_settings_fields() -> None:
    data = {**_settings_data(), "max_trigger_breach_pct": 0.5}

    settings = StrategySettings(**data)
    update = UpdateStrategySettingsRequest(**data)

    assert update.model_dump() == settings.model_dump()


def test_zero_cap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StrategySettings(**_settings_data(), max_trigger_breach_pct=0)
    with pytest.raises(ValidationError):
        UpdateStrategySettingsRequest(**_settings_data(), max_trigger_breach_pct=0)


def test_invalid_fill_timing_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StrategySettings(**_settings_data(), fill_timing="same_bar")
    with pytest.raises(ValidationError):
        UpdateStrategySettingsRequest(**_settings_data(), fill_timing="same_bar")


def test_max_reversal_overshoot_ratio_defaults_to_none() -> None:
    """★기본 비활성 — 캡이 조용히 켜지면 기존 세션의 반전 진입이 말없이 사라진다."""
    settings = StrategySettings(**_settings_data())
    update = UpdateStrategySettingsRequest(**_settings_data())

    assert settings.max_reversal_overshoot_ratio is None
    assert update.max_reversal_overshoot_ratio is None


def test_legacy_settings_without_reversal_cap_still_parse() -> None:
    """`extra="forbid"` 스키마에 필드를 더해도 기존 JSONB 는 그대로 파싱돼야 한다."""
    settings = validate_strategy_settings(_settings_data())

    assert settings is not None
    assert settings.max_reversal_overshoot_ratio is None


def test_update_request_mirrors_reversal_cap() -> None:
    data = {**_settings_data(), "max_reversal_overshoot_ratio": 2.0}

    settings = StrategySettings(**data)
    update = UpdateStrategySettingsRequest(**data)

    assert settings.max_reversal_overshoot_ratio == 2.0
    assert update.model_dump() == settings.model_dump()


def test_zero_reversal_cap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StrategySettings(**_settings_data(), max_reversal_overshoot_ratio=0)
    with pytest.raises(ValidationError):
        UpdateStrategySettingsRequest(**_settings_data(), max_reversal_overshoot_ratio=0)
