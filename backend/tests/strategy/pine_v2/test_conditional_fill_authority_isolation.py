# 백테스트 경로는 원장 체결 권한을 **절대 넘기지 않는다** (ADR-025 / BL-595)
"""`ledger_conditional_fills` / `conditional_fill_authority` 격리 회귀 테스트.

## 왜 필요한가 — 이 위험은 **가정이 아니라 실측**이다

조건부 체결 로직(`strategy_state.check_pending_fills`)은 백테스트와 라이브가 **공유**한다:

    백테스트 : compat.parse_and_run_v2 → track_runner ─┐
                                                       ├→ run_historical() → check_pending_fills()
    라이브   : run_live() ─────────────────────────────┘

2026-08-05 회차가 [BL-595] 형 A 를 최소 모형으로 **주입해서** 확인했다 — **12개 테스트가 죽었고
그중 하나가 Trust Layer 골든** `test_p3_execution_metrics_match_golden[s1_pbr]` 이다.
`run_live` 를 한 번도 안 부르면서. ★그리고 그게 우연이 아니다: 소크가 돌리는 라이브 전략의
`pine_source` 가 골든 코퍼스 `s1_pbr.pine` 과 **md5 동일**이다.

⇒ 이 인자가 백테스트 경로로 새면 골든·Optimizer·Stress Test 가 **동시에** 오염된다.

★파일 화이트리스트 방식인 이유는 `test_ledger_seed_isolation.py` 와 같다 — 「백테스트를 돌려서
결과가 같은지」로는 **인자를 넘기되 마침 빈 값이라 같은 경우**를 못 가른다. 계약은 "결과가
같다" 가 아니라 **"그 경로가 이 인자를 아예 모른다"** 이다.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from src.strategy.pine_v2.event_loop import run_historical, run_live

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"

# 라이브 전용 심볼 셋. 하나라도 백테스트 쪽에 나타나면 red 다.
#   ledger_conditional_fills    — `run_live` 의 공개 인자 (평평한 체결 목록)
#   conditional_fill_authority  — `run_historical`/`check_pending_fills` 가 받는 봉별 권한자
#   LedgerConditionalFill       — 그 원소 타입
_SYMBOLS = (
    "ledger_conditional_fills",
    "conditional_fill_authority",
    "LedgerConditionalFill",
)

# 이 심볼을 알아도 되는 파일. **늘리려면 근거를 여기 적어라.**
#   strategy_state.py — 타입과 권한자를 정의하고 `check_pending_fills` 분기를 갖는 곳.
#   event_loop.py     — 두 진입점의 인자를 정의하고 봉 귀속(`_build_conditional_fill_authority`).
#   live_signal.py    — 라이브 tick 에서만 원장을 읽어 채우는 유일한 호출자.
_ALLOWED = {
    "strategy/pine_v2/strategy_state.py",
    "strategy/pine_v2/event_loop.py",
    "tasks/live_signal.py",
}


def _files_mentioning(symbol: str) -> set[str]:
    found: set[str] = set()
    for path in _SRC_ROOT.rglob("*.py"):
        if symbol in path.read_text(encoding="utf-8"):
            found.add(path.relative_to(_SRC_ROOT).as_posix())
    return found


def test_only_engine_and_live_path_know_the_authority_symbols() -> None:
    """★백테스트 경로(`compat` / `track_runner` / `v2_adapter`)가 들어오면 red 다."""
    for symbol in _SYMBOLS:
        assert _files_mentioning(symbol) <= _ALLOWED, f"{symbol} 이 화이트리스트 밖으로 샜다"


def test_symbols_are_actually_present() -> None:
    """★공허화 방지 — 이름이 바뀌면 위 검사가 「아무 데도 없다」로 조용히 통과한다."""
    for symbol in _SYMBOLS:
        assert _files_mentioning(symbol), f"{symbol} 이 src 어디에도 없다 — 검사가 공허하다"


def test_authority_defaults_to_none_on_both_entrypoints() -> None:
    """★기본값은 `()` 가 아니라 `None` 이다 — 3-상태를 2-상태로 접으면 안 된다.

    `None` = 「원장을 못 읽었다」(시뮬로 되돌린다) · `()` = 「원장이 답했는데 체결이 없다」
    (아무것도 체결하지 않는다). 기본값이 `()` 였다면 백테스트가 **조건부 진입을 영원히
    체결하지 못하는** 엔진이 된다.
    """
    assert inspect.signature(run_live).parameters["ledger_conditional_fills"].default is None
    assert (
        inspect.signature(run_historical).parameters["conditional_fill_authority"].default is None
    )


def test_check_pending_fills_defaults_to_simulation() -> None:
    """엔진 안쪽 seam 도 같은 기본값이어야 격리가 성립한다."""
    from src.strategy.pine_v2.strategy_state import StrategyState

    parameter = inspect.signature(StrategyState.check_pending_fills).parameters[
        "conditional_fill_authority"
    ]
    assert parameter.default is None


def test_backtest_adapter_does_not_forward_the_authority() -> None:
    """★백테스트·옵티마이저·스트레스가 **공유하는** 진입점이 이 인자를 모른다.

    `run_backtest_v2` 는 `backtest.engine.run_backtest` 의 실체이고 Optimizer(param combo 마다)
    와 Stress Test(WFO/Param-Stability/Cost cell 마다)가 **같은 함수를 재실행**한다
    (CONTEXT.md Relationships). 여기로 새면 세 소비자가 동시에 오염된다.

    ★`exists()` 로 감싸지 않는다 — 파일이 사라지면 이 검사가 조용히 통과해 버린다.
    """
    adapter = _SRC_ROOT / "backtest" / "engine" / "v2_adapter.py"
    assert adapter.exists(), f"백테스트 진입점을 찾을 수 없다: {adapter}"
    body = adapter.read_text(encoding="utf-8")
    for symbol in _SYMBOLS:
        assert symbol not in body


def test_virtual_strategy_track_a_is_not_silently_diverged() -> None:
    """★Track A(`run_virtual_strategy`)는 `run_historical` 을 안 타고 `check_pending_fills` 를
    직접 부른다(`virtual_strategy.py:230`). 그쪽이 이 인자를 **안 넘긴다**는 것이 계약이다 —
    Track A 는 라이브 경로가 아예 없기 때문이다([ADR-023] §폭발 반경 3). 넘기기 시작하면
    라이브 전용 동작이 백테스트 Track A 로 새므로 여기서 red 를 낸다.
    """
    virtual = _SRC_ROOT / "strategy" / "pine_v2" / "virtual_strategy.py"
    assert virtual.exists(), f"Track A 진입점을 찾을 수 없다: {virtual}"
    body = virtual.read_text(encoding="utf-8")
    for symbol in _SYMBOLS:
        assert symbol not in body
