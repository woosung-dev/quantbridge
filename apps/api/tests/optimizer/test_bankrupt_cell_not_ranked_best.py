"""파산한 계좌를 「최적」으로 뽑지 않는다 — sharpe degeneracy 게이트가 convention 을 읽는다.

★**무엇이 잘못돼 있었나** (2026-08-30 아키텍처 감사 gap sweep, CONTROL 골든 코퍼스로 재실측).

`sharpe_ratio()` 는 equity 가 0 이하로 내려간 실행에 **`Decimal("0")` + convention
`unavailable_nonpositive_equity`** 를 돌려준다(`backtest/engine/metrics.py:127-128`).
그 함수의 docstring 이 계약을 못 박는다 — 「degenerate 는 **값 0 과 convention** 으로 구분한다」.
즉 **값만 보면 파산과 「잔잔했다」가 같은 0 이다.**

그런데 세 엔진의 degenerate 게이트는 `num_trades == 0` **하나만** 봤다. 두 번째 절
`metrics.sharpe_ratio is None` 은 `types.py:180` 이 `sharpe_ratio: Decimal`(비-옵셔널)이라
**죽은 가지**이고, `sharpe_ratio()` docstring 자신이 그것을 「현재 dead branch」라 적어 두었다.

⇒ `objective_metric="sharpe_ratio"` + `direction="maximize"` 에서 **파산 셀(0.0)이 생존-손실
셀(음수)을 이긴다.** 레포의 골든 코퍼스가 그대로 그 짝을 갖고 있다:

| 케이스                | sharpe      | 거래 | total_return | convention                      |
| --------------------- | ----------- | ---- | ------------ | ------------------------------- |
| `s2_utbot`            |  0.00000000 | 433  | **-2.98**    | `unavailable_nonpositive_equity` |
| `s4_hma_curvature`    | -7.58833734 | 243  | -0.67        | `tv_monthly_rfr2`               |

★루트 `AGENTS.md` §1 = 「핵심은 기능 수가 아니라 **결과와 가정이 얼마나 정직하게 보이는가**」.
[BL-398] 이 없애려던 거짓말과 같은 종류다 — 그쪽은 수식, 이쪽은 게이트다.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.backtest.engine.metrics import (
    SHARPE_CONVENTION_MONTHLY,
    SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
    SHARPE_CONVENTION_UNAVAILABLE,
)
from src.backtest.engine.types import BacktestMetrics
from src.optimizer.engine._common import _objective_from_metrics, pick_best_index

# 골든 코퍼스 `tests/fixtures/pine_corpus_v2/baseline_metrics.json` 실측값.
_BANKRUPT = {
    "total_return": Decimal("-2.98222648"),
    "sharpe_ratio": Decimal("0.00000000"),
    "max_drawdown": Decimal("-1.5"),
    "win_rate": Decimal("0.3"),
    "num_trades": 433,
    "sharpe_convention": SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
}
_SOLVENT_LOSING = {
    "total_return": Decimal("-0.67327506"),
    "sharpe_ratio": Decimal("-7.58833734"),
    "max_drawdown": Decimal("-0.7"),
    "win_rate": Decimal("0.4"),
    "num_trades": 243,
    "sharpe_convention": SHARPE_CONVENTION_MONTHLY,
}


def _metrics(**overrides: object) -> BacktestMetrics:
    return BacktestMetrics(**{**_SOLVENT_LOSING, **overrides})  # type: ignore[arg-type]


def test_bankrupt_cell_has_no_sharpe_objective() -> None:
    """파산 셀은 sharpe 목적함수에서 **점수를 받지 못한다**(None = degenerate)."""
    value = _objective_from_metrics(_metrics(**_BANKRUPT), objective_metric="sharpe_ratio")

    assert value is None


def test_solvent_losing_cell_keeps_its_negative_sharpe() -> None:
    """★음성 대조 — 멀쩡한 셀의 음수 sharpe 까지 버리면 게이트가 과잉이다."""
    value = _objective_from_metrics(_metrics(), objective_metric="sharpe_ratio")

    assert value == Decimal("-7.58833734")


def test_bankrupt_cell_does_not_win_maximize_against_a_solvent_loser() -> None:
    """이 회차의 본체 — 파산 파라미터가 「최적」으로 뽑히지 않는다."""
    bankrupt = _objective_from_metrics(_metrics(**_BANKRUPT), objective_metric="sharpe_ratio")
    solvent = _objective_from_metrics(_metrics(), objective_metric="sharpe_ratio")

    best = pick_best_index([(0, bankrupt), (1, solvent)], direction="maximize")

    assert best == 1


@pytest.mark.parametrize(
    "convention", [SHARPE_CONVENTION_NONPOSITIVE_EQUITY, SHARPE_CONVENTION_UNAVAILABLE]
)
def test_every_unavailable_convention_is_degenerate_for_sharpe(convention: str) -> None:
    """`unavailable*` 는 「잰 값이 없다」는 뜻이다 — 그 0 을 점수로 쓰지 않는다."""
    value = _objective_from_metrics(
        _metrics(sharpe_ratio=Decimal("0"), sharpe_convention=convention),
        objective_metric="sharpe_ratio",
    )

    assert value is None


def test_other_objectives_are_untouched_by_the_sharpe_convention() -> None:
    """★게이트는 **sharpe 목적함수에만** 걸린다 — total_return 은 파산 셀도 정직한 실측값이다."""
    bankrupt = _metrics(**_BANKRUPT)

    assert _objective_from_metrics(bankrupt, objective_metric="total_return") == Decimal(
        "-2.98222648"
    )
    assert _objective_from_metrics(bankrupt, objective_metric="max_drawdown") == Decimal("-1.5")


def test_zero_trade_cell_stays_degenerate() -> None:
    """★기존 게이트를 잃지 않았다 — 거래 0건은 그대로 degenerate."""
    value = _objective_from_metrics(
        _metrics(num_trades=0, sharpe_convention=SHARPE_CONVENTION_MONTHLY),
        objective_metric="sharpe_ratio",
    )

    assert value is None


# ── grid 경로 ────────────────────────────────────────────────────────────────
# ★grid 는 자기 docstring 에서 「degenerate 게이트가 bayesian/genetic 보다 넓다
#   (num_trades==0 **or sharpe None**)」고 주장했다. 그 두 번째 절은 `sharpe_ratio` 가
#   비-옵셔널 `Decimal` 이라 **죽은 가지**이므로 실제로는 셋이 똑같았다.


def _grid_cell(*, sharpe, num_trades=433, is_degenerate=False):
    from src.optimizer.engine.grid_search import GridSearchCell

    return GridSearchCell(
        param_values={"length": Decimal("14")},
        sharpe=sharpe,
        total_return=Decimal("-2.98222648"),
        max_drawdown=Decimal("-1.5"),
        num_trades=num_trades,
        is_degenerate=is_degenerate,
        objective_value=None,
    )


def test_grid_bankrupt_cell_has_no_sharpe_objective() -> None:
    from src.optimizer.engine.grid_search import _cell_objective_value

    value = _cell_objective_value(
        _grid_cell(sharpe=Decimal("0")),
        objective_metric="sharpe_ratio",
        sharpe_unavailable=True,
    )

    assert value is None


def test_grid_solvent_cell_keeps_its_sharpe() -> None:
    """★음성 대조 — convention 이 멀쩡하면 grid 도 값을 그대로 쓴다."""
    from src.optimizer.engine.grid_search import _cell_objective_value

    value = _cell_objective_value(
        _grid_cell(sharpe=Decimal("-7.58833734")),
        objective_metric="sharpe_ratio",
        sharpe_unavailable=False,
    )

    assert value == Decimal("-7.58833734")


def test_grid_other_objectives_ignore_the_sharpe_convention() -> None:
    from src.optimizer.engine.grid_search import _cell_objective_value

    value = _cell_objective_value(
        _grid_cell(sharpe=Decimal("0")),
        objective_metric="total_return",
        sharpe_unavailable=True,
    )

    assert value == Decimal("-2.98222648")
