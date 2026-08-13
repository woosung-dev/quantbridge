# 백테스트 경로는 원장 주입 인자를 **절대 넘기지 않는다** (BL-591 / ADR-022 부수 B)
"""`ledger_seed_legs` 격리 회귀 테스트.

## 왜 필요한가

백테스트와 라이브는 **같은 엔진**(`run_historical`)을 탄다:

    백테스트 : compat.parse_and_run_v2 → track_runner ─┐
                                                       ├→ run_historical()
    라이브   : run_live() ─────────────────────────────┘

원장 주입(`ledger_seed_legs`)이 백테스트 경로로 새면 **골든이 조용히 깨진다** — 같은 입력에
다른 결과가 나오는데 그 원인이 인자 하나라 추적이 어렵다.

지금 그 격리를 지키는 것은 **관례뿐**이다. `run_historical` 이 인자를 공개로 받으므로 누구든
백테스트 호출부에서 채울 수 있다. 이 테스트가 그 관례를 **집행 가능한 계약**으로 바꾼다.

★파일 화이트리스트 방식인 이유 — 「백테스트를 돌려서 결과가 같은지」로는 **인자를 넘기되 빈
값이라 마침 같은 경우**를 못 가른다. 계약은 "결과가 같다" 가 아니라 **"그 경로가 이 인자를
아예 모른다"** 이다.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from src.strategy.pine_v2.event_loop import run_historical, run_live

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
_SYMBOL = "ledger_seed_legs"

# 이 인자를 알아도 되는 파일. **늘리려면 근거를 여기 적어라.**
#   event_loop.py — 인자를 정의하고 주입점(`:192`)을 갖는 곳.
#   live_signal.py — 라이브 tick 에서만 채우는 유일한 호출자.
#   track_runner.py — ★**가드**다(ADR-025, 2026-08-05 추가). 전달하지 않고 **거부한다.**
#     그 파일의 `invoke(**kwargs)` 가 `run_historical` 로 splat 하므로, 백테스트 상류가 이
#     인자를 넘기면 **어느 파일도 이름을 적지 않고** 엔진에 닿는다 — 이 문자열 검사만으로는
#     구조적으로 못 막는다. 거부 동작은
#     `test_conditional_fill_authority_isolation.py::test_backtest_dispatcher_rejects_live_only_kwargs`
#     가 집행한다.
_ALLOWED = {
    "strategy/pine_v2/event_loop.py",
    "strategy/pine_v2/track_runner.py",
    "tasks/live_signal.py",
}


def _files_mentioning_symbol() -> set[str]:
    found: set[str] = set()
    for path in _SRC_ROOT.rglob("*.py"):
        if _SYMBOL in path.read_text(encoding="utf-8"):
            found.add(path.relative_to(_SRC_ROOT).as_posix())
    return found


def test_only_engine_and_live_path_know_the_injection_argument() -> None:
    """★백테스트 경로(`compat` / `track_runner` / `v2_adapter`)가 들어오면 red 다."""
    assert _files_mentioning_symbol() == _ALLOWED


def test_injection_argument_defaults_to_empty_on_both_entrypoints() -> None:
    """넘기지 않으면 주입이 없다 — 격리가 성립하는 근거."""
    for func in (run_historical, run_live):
        parameter = inspect.signature(func).parameters[_SYMBOL]
        assert parameter.default == (), f"{func.__name__} 의 기본값이 빈 튜플이 아니다"


def test_backtest_adapter_does_not_forward_injection() -> None:
    """★백테스트·옵티마이저·스트레스가 **공유하는** 진입점이 이 인자를 모른다.

    `run_backtest_v2` 는 `backtest.engine.run_backtest` 의 실체이고 Optimizer(param combo 마다)
    와 Stress Test(WFO/Param-Stability/Cost cell 마다)가 **같은 함수를 재실행**한다
    (CONTEXT.md Relationships). 여기로 새면 세 소비자가 동시에 오염된다.

    ★`exists()` 로 감싸지 않는다 — 파일이 사라지면 이 검사가 조용히 통과해 버린다.
    실측으로 한 번 밟았다(경로를 `strategy/pine_v2/` 로 잘못 짚어 검사가 무력화됐다).
    """
    adapter = _SRC_ROOT / "backtest" / "engine" / "v2_adapter.py"
    assert adapter.exists(), f"백테스트 진입점을 찾을 수 없다: {adapter}"
    assert _SYMBOL not in adapter.read_text(encoding="utf-8")
