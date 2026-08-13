# Sprint 53 BL-226 — FE `isFiniteDecimalString` regex 와 정합하는 strict Decimal validator.

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator

# FE mirror: frontend/src/features/backtest/schemas.ts:477-483 `isFiniteDecimalString`
# regex `^-?\d+(\.\d+)?$` 와 정확 정합. `1e-3`, `.5`, `+1`, `NaN`, `Infinity` reject.
_STRICT_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _check_float_finite(v: Decimal) -> None:
    """codex G.4 P1#1 fix — FE `Number.isFinite(Number(s))` BE parity.

    BE Decimal 은 `1e6000` 같은 임의 자릿수 표현 가능. FE 는 IEEE 754 double
    (`Number.MAX_VALUE ~= 1.79e308`) 안 finite check. 일치성 위해 BE 도 동일.
    overflow Decimal → float `inf` → cost/param stability worker 안 silent
    `inf` 전파 차단.
    """
    if not math.isfinite(float(v)):
        raise ValueError(
            f"decimal magnitude overflows IEEE 754 double (got {v!r}). "
            "FE `Number.isFinite` parity (BL-226)."
        )


def _strict_decimal_input(v: object) -> Decimal:
    """Request-boundary 전용 Decimal validator.

    외부 입력 (string) 은 FE regex 정확 mirror. 내부 Decimal 인스턴스도
    canonicalization (finite + no exponent + float-finite) 통과 시에만 허용.

    codex G.0 P1#9 + G.4 P1#1 fix: Decimal passthrough 비대칭 + FE/BE parity 깨짐
    모두 차단. `Decimal("NaN")`, `Decimal("1E+5")`, `"9" * 400` overflow string 모두 reject.
    """
    if isinstance(v, Decimal):
        # 내부 인스턴스 — canonicalization check
        if not v.is_finite():
            raise ValueError(
                f"non-finite Decimal {v!r} (BL-226 canonicalization). "
                "NaN/Infinity는 Request-boundary 에서 reject."
            )
        # canonical form check — str(Decimal('1E+5')) == '1E+5' 같은 exponent repr reject.
        # FE regex 와 정확 mirror: optional sign + digits + optional fraction.
        s = str(v)
        if not _STRICT_DECIMAL_RE.fullmatch(s):
            raise ValueError(
                f"non-canonical Decimal repr {s!r} (BL-226). "
                "FE `isFiniteDecimalString` regex 와 mirror — `1E+5` style exponent reject."
            )
        _check_float_finite(v)
        return v

    # 외부 입력 — string 전용 (codex P1#10: int/float 인스턴스 직접 통과 차단).
    if not isinstance(v, str):
        raise ValueError(
            f"StrictDecimalInput requires str or canonical Decimal (got {type(v).__name__}). "
            "외부 입력은 string 만 — int/float 직접 통과 차단 (precision 손실 회피)."
        )

    if not _STRICT_DECIMAL_RE.fullmatch(v):
        raise ValueError(
            f"strict decimal grammar 위반 {v!r} (BL-226). "
            f"FE `isFiniteDecimalString` regex `^-?\\d+(\\.\\d+)?$` 와 정합 필수 — "
            "`1e-3`, `.5`, `+1`, `NaN`, `Infinity` reject."
        )

    result = Decimal(v)
    # codex G.4 P1#1 — FE `Number.isFinite` parity. `"9" * 400` 같은 huge digit string reject.
    _check_float_finite(result)
    return result


StrictDecimalInput = Annotated[Decimal, BeforeValidator(_strict_decimal_input)]
"""Request-boundary 전용 strict Decimal type.

사용: `param_grid: dict[str, list[StrictDecimalInput]]` (stress_test schemas).
canonical form 만 허용 — FE form 입력 (string) 과 정확 정합.

내부 코드가 `Decimal("10")` 같은 canonical 인스턴스 직접 만들면 통과 OK.
`Decimal("NaN")` / `Decimal("Infinity")` / `Decimal("1E+5")` 같은 non-canonical 인스턴스 reject.

Note: `Decimal("1E-3")` 는 Python 안 자동 정규화 ('0.001') 되어 통과. 큰 양수 exponent
      만 str repr 유지 = `Decimal("1E+5")` style 만 reject (codex G.0 P1#9 의도 정합).
"""
