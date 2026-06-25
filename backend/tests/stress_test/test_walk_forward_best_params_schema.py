# C13 — WalkForwardParams.best_params 스키마 검증 (옵티마이저 best-params → OOS 주입)
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.stress_test.schemas import WalkForwardParams


def test_best_params_default_none() -> None:
    p = WalkForwardParams(train_bars=100, test_bars=50)
    assert p.best_params is None


def test_best_params_coerces_to_decimal() -> None:
    # 옵티마이저 best_params 는 JSONB 에 Decimal→str 저장. 숫자/문자 모두 Decimal 로.
    p = WalkForwardParams(
        train_bars=100, test_bars=50, best_params={"fastLen": "10", "slowLen": 40}
    )
    assert p.best_params == {"fastLen": Decimal("10"), "slowLen": Decimal("40")}


def test_best_params_rejects_non_numeric() -> None:
    # categorical string sweep 은 BL-364 deferred — 현재 numeric(Decimal) 만 허용.
    with pytest.raises(ValidationError):
        WalkForwardParams(
            train_bars=100, test_bars=50, best_params={"x": "not-a-number"}
        )
