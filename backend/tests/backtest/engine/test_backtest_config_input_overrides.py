# BacktestConfig.input_overrides 필드 + __post_init__ runtime type validation 검증 (BL-220 Sprint 51)
"""Sprint 51 Slice 1 RED — BacktestConfig.input_overrides 필드 + __post_init__ validation.

codex G.0 P1#4 반영: frozen dataclass 만으론 runtime type reject 불가 →
__post_init__ 검증 추가. invalid type 시 ValueError raise.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.backtest.engine.types import BacktestConfig


class TestInputOverridesField:
    """BacktestConfig.input_overrides 신규 필드 (Sprint 51 BL-220)."""

    def test_input_overrides_default_none(self) -> None:
        """default = None (회귀 0 — 기존 backtest path 변경 X)."""
        cfg = BacktestConfig()
        assert cfg.input_overrides is None

    def test_input_overrides_accepts_int(self) -> None:
        """input.int override = int value 허용."""
        cfg = BacktestConfig(input_overrides={"emaPeriod": 20})
        assert cfg.input_overrides == {"emaPeriod": 20}

    def test_input_overrides_accepts_decimal(self) -> None:
        """input.float override = Decimal value 허용 (Sprint 4 D8 — Decimal-first)."""
        cfg = BacktestConfig(input_overrides={"stopLossPct": Decimal("2.5")})
        assert cfg.input_overrides == {"stopLossPct": Decimal("2.5")}

    def test_input_overrides_accepts_bool(self) -> None:
        """input.bool override = bool value 허용."""
        cfg = BacktestConfig(input_overrides={"useStopLoss": True})
        assert cfg.input_overrides == {"useStopLoss": True}

    def test_input_overrides_accepts_str(self) -> None:
        """input.string override = str value 허용."""
        cfg = BacktestConfig(input_overrides={"timeframe": "1h"})
        assert cfg.input_overrides == {"timeframe": "1h"}

    def test_input_overrides_accepts_multiple_keys(self) -> None:
        """다중 input override (9-cell grid sweep 의 cell 단위)."""
        cfg = BacktestConfig(
            input_overrides={"emaPeriod": 20, "stopLossPct": Decimal("2.0")}
        )
        assert cfg.input_overrides == {"emaPeriod": 20, "stopLossPct": Decimal("2.0")}


class TestInputOverridesValidation:
    """__post_init__ runtime type reject (codex G.0 P1#4)."""

    def test_input_overrides_rejects_object(self) -> None:
        """invalid type (object) → ValueError raise."""
        with pytest.raises(ValueError, match="input_overrides"):
            BacktestConfig(input_overrides={"x": object()})  # type: ignore[dict-item]

    def test_input_overrides_rejects_list(self) -> None:
        """invalid type (list) → ValueError raise."""
        with pytest.raises(ValueError, match="input_overrides"):
            BacktestConfig(input_overrides={"x": [1, 2, 3]})  # type: ignore[dict-item]

    def test_input_overrides_rejects_dict(self) -> None:
        """invalid type (nested dict) → ValueError raise."""
        with pytest.raises(ValueError, match="input_overrides"):
            BacktestConfig(input_overrides={"x": {"nested": True}})  # type: ignore[dict-item]

    def test_input_overrides_rejects_none_value(self) -> None:
        """invalid type (None as value) → ValueError raise."""
        with pytest.raises(ValueError, match="input_overrides"):
            BacktestConfig(input_overrides={"x": None})  # type: ignore[dict-item]


class TestMutationBypassGuard:
    """codex Slice 1 review P1 회귀 가드 — frozen dataclass + mutable dict bypass 차단.

    `__post_init__` 검증 후 dict 방어 복사 + `MappingProxyType` lock.
    caller 가 원본 dict 또는 cfg.input_overrides 를 mutation 시도 시:
      - 원본 dict mutation → cfg.input_overrides 에 영향 없음 (defensive copy)
      - cfg.input_overrides mutation → MappingProxyType raise TypeError
    """

    def test_caller_dict_mutation_does_not_affect_cfg(self) -> None:
        """원본 dict mutation 후 cfg.input_overrides 는 변경되지 않음 (defensive copy)."""
        original = {"emaPeriod": 20}
        cfg = BacktestConfig(input_overrides=original)
        # 원본 mutation (invalid type 주입 시도)
        original["emaPeriod"] = object()  # type: ignore[assignment]
        # cfg 안 dict 는 영향 없음
        assert cfg.input_overrides is not None
        assert cfg.input_overrides["emaPeriod"] == 20

    def test_cfg_input_overrides_is_immutable(self) -> None:
        """cfg.input_overrides mutation 시 TypeError raise (MappingProxyType lock)."""
        cfg = BacktestConfig(input_overrides={"emaPeriod": 20})
        assert cfg.input_overrides is not None
        with pytest.raises(TypeError):
            cfg.input_overrides["emaPeriod"] = object()  # type: ignore[index]


class TestBacktestConfigRegression:
    """codex G.0 P1#5 — default backtest path regression guard.

    input_overrides=None 일 때 기존 BacktestConfig 의 모든 필드 default 가
    Sprint 50 이전과 동일하게 작동 (회귀 0 검증).
    """

    def test_default_config_unchanged(self) -> None:
        """기존 default 필드 값이 변경되지 않음 (Sprint 38 BL-188 v3 정합)."""
        cfg = BacktestConfig()
        assert cfg.init_cash == Decimal("10000")
        assert cfg.fees == 0.001
        assert cfg.slippage == 0.0005
        assert cfg.freq == "1D"
        assert cfg.trading_sessions == ()
        assert cfg.leverage == 1.0
        assert cfg.include_funding is False
        assert cfg.default_qty_type is None
        assert cfg.default_qty_value is None
        assert cfg.live_position_size_pct is None
        assert cfg.sizing_source == "fallback"
        assert cfg.sizing_basis == "fallback_qty1"
        assert cfg.leverage_basis == 1.0
        assert cfg.input_overrides is None  # Sprint 51 BL-220 신규
