"""`bayesian_n_initial_random` 상한이 FE 와 같은 값인지 얼린다.

★**왜 생겼나** (2026-08-30 계약 감사) — BE 는 `le=50`, FE 는 **세 층 전부 100** 이었다:
`features/optimizer/schemas.ts:138` · `bayesian-search-form.tsx`(`.max(100, …)`) ·
`makeOptimizerFormBaseFields(100)`. 그래서 51~100 을 넣으면 사용자가 FE 검증 3중을
전부 통과한 뒤 서버에서 **422** 를 맞았다 — 폼은 「괜찮다」고 말하고 서버만 거절하는 상태다.

★이 테스트는 **숫자 하나를 두 곳에 적어 두는 대신 계약을 얼린다.** FE 상한을 바꾸려면 여기가 먼저 빨개진다.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.optimizer.schemas import ParamSpace

# FE 가 선언한 상한. `apps/web/src/features/optimizer/schemas.ts` 의 `.max(...)` 와 같아야 한다.
_FE_DECLARED_MAX = 100


def _param_space(n_initial_random: int) -> dict[str, object]:
    return {
        "schema_version": 2,
        "objective_metric": "sharpe_ratio",
        "direction": "maximize",
        "max_evaluations": _FE_DECLARED_MAX,
        "parameters": {"length": {"kind": "integer", "min": 1, "max": 10, "step": 1}},
        "bayesian_n_initial_random": n_initial_random,
    }


@pytest.mark.parametrize("value", [1, 50, 51, _FE_DECLARED_MAX])
def test_values_the_frontend_accepts_are_accepted_by_the_backend(value: int) -> None:
    space = ParamSpace.model_validate(_param_space(value))

    assert space.bayesian_n_initial_random == value


@pytest.mark.parametrize("value", [0, _FE_DECLARED_MAX + 1])
def test_values_outside_the_shared_bound_are_rejected(value: int) -> None:
    """★음성 대조 — 상한을 지운 변이가 초록으로 빠져나가지 못하게 한다."""
    with pytest.raises(ValidationError):
        ParamSpace.model_validate(_param_space(value))
