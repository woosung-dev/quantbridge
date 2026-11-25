# 완료된 Backtest 를 같은 조건으로 다시 돌릴 때의 입력 판정 (stress_test · optimizer 공용)
"""「이 Backtest 를 다시 돌리려면 어떤 source 를 엔진에 넘기나」의 판정부.

stress_test 와 optimizer 가 같은 규칙을 각자 사본으로 갖고 있었고, 그 구조에서 핀 결함이
한 번 드리프트했다(backtest·optimizer 에서 닫은 뒤 stress_test 에 동형으로 남음 — BL-783).
`config_mapper.py` 와 같은 방향(stress_test/optimizer → backtest)의 module-level helper 다.

여기는 **판정만** 한다. 실패를 어떤 예외·문구·로그로 드러낼지는 호출자마다 다르고
(stress_test 는 `ValueError`, optimizer 는 `OptimizationExecutionError`) 그 표면은 DB 에
저장되는 error 문자열까지 이어지므로 호출자가 그대로 변환한다.

`BacktestService._run` 의 핀 해석은 execution-policy mismatch 검사와 code 경로가 얽힌
변형이라 이 module 을 쓰지 않는다.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from src.backtest.engine import PINE_V2_ENGINE_VERSION
from src.backtest.models import Backtest
from src.strategy.code_contract import legacy_pine_source
from src.strategy.repository import StrategyRepository


class RerunSourceUnavailable(Enum):
    """핀된 source 를 내지 못한 사유 — 예외·문구는 호출자가 만든다."""

    STRATEGY_VERSION_MISSING = "strategy_version_missing"
    STRATEGY_MISSING = "strategy_missing"


def is_rerunnable_engine_version(bt: Backtest) -> bool:
    """재실행 경로는 pine_v2 엔진만 안다. NULL 은 engine_version 도입 이전 행이다."""
    return bt.engine_version in (None, PINE_V2_ENGINE_VERSION)


async def resolve_pinned_pine_source(
    bt: Backtest,
    strategy_repo: StrategyRepository,
    *,
    on_legacy_fallback: Callable[[], None],
) -> str | RerunSourceUnavailable:
    """부모 Backtest 에 핀된 불변 스냅샷의 Pine source 를 돌려준다.

    실행 시점의 mutable `Strategy.pine_source` 를 읽으면, 제출 후 전략을 수정한 사용자의
    재실행에서 **수정본이 돌고 결과는 옛 Backtest 에 매달려 표시된다.** 그래서:

    - 핀(`strategy_version_id`)이 있으면 그 스냅샷만 쓴다. 핀이 있는데 행이 없으면
      현재 Strategy 로 떨어지지 않고 `STRATEGY_VERSION_MISSING` 을 낸다.
    - 핀이 NULL 인 legacy 행만 현재 Strategy 로 떨어진다. 그 직전에 `on_legacy_fallback`
      을 부른다 — 흔적(호출자 이름의 경고 로그)이 조회 실패와 무관하게 남아야 한다.
    """
    strategy_version = await strategy_repo.get_version_by_id(
        bt.strategy_version_id,
        strategy_id=bt.strategy_id,
    )
    if strategy_version is not None:
        return legacy_pine_source(strategy_version)
    if bt.strategy_version_id is not None:
        return RerunSourceUnavailable.STRATEGY_VERSION_MISSING

    on_legacy_fallback()
    strategy = await strategy_repo.find_by_id_and_owner(bt.strategy_id, bt.user_id)
    if strategy is None:
        return RerunSourceUnavailable.STRATEGY_MISSING
    return legacy_pine_source(strategy)


__all__ = [
    "RerunSourceUnavailable",
    "is_rerunnable_engine_version",
    "resolve_pinned_pine_source",
]
