# Worker A2 Plan — BL-188 v3 BE Chain Live + Entry/Fill Gate

작성일: 2026-05-07
브랜치: `worker-a2/bl-188-be-chain-and-entry-fill-gate`
base: `origin/stage/sprint38-bl-188-bl-181` (b61b16c)
명세 SSOT: `~/.claude/plans/context-restore-jazzy-charm.md` § A2

## 목표

Sprint 37 A1 의 sizing canonical helper + Live mirror schema + 422 예외 (3) 를 토대로,
backtest v2 path 가 실제로 4-tier chain 의 Live tier 를 propagate 하고 (D2),
trading_sessions 가 entry placement 와 fill 양쪽에 적용되도록 (E3 Live parity) 확장.

핵심 invariant:
- 단일 reference (`src.strategy.trading_sessions.is_allowed`) 만 호출 — backtest v2 와 Live 가 동일 함수 사용.
- tz-naive sessions-only fail-closed — sessions 활성 + naive index → BacktestError 422.
- silent skip 의미: entry 시 placement 안 됨 (equity/state 0 영향), fill 시 fill skip + order 다음 bar 로 carry-over.

## TDD 모드 = 정석

본 sprint 변경은 BE event_loop / state machine / financial number 가 직접 영향 → LESSON 위험 지대.
- 신규 6 tests 가 spec → 구현이 spec 충족.
- 기존 1646 baseline regression 0 의무.

## 단계 분해 (각 단계 후 빠른 회귀)

### 단계 1 — `compat.py:parse_and_run_v2` 시그니처 확장

- `live_position_size_pct` (Optional[Decimal]) + `sessions_allowed` (tuple[str, ...]) 신규 인자.
- D2 chain: Pine > form > Live > None — A1 helper 가 이미 결정. compat 은 결정된 값을 propagate.
- `initial_capital is None` 시 Live tier silent skip 방지 → assert.
- 회귀: `pytest -k "test_compat OR test_run_v2_signature" -q`

### 단계 2 — `v2_adapter.py:run_backtest_v2` propagation + tz-naive fail-closed

- `cfg.live_position_size_pct` + `cfg.trading_sessions` propagate.
- tz-naive sessions-only reject:
  ```python
  if cfg.trading_sessions:
      if not isinstance(cfg.ohlcv.index, pd.DatetimeIndex):
          raise BacktestError("trading_sessions 활성 시 OHLCV index 가 DatetimeIndex 의무")
      if cfg.ohlcv.index.tz is None:
          raise BacktestError("trading_sessions 활성 시 OHLCV index 가 tz-aware 의무")
  ```
- v2_adapter 기존 `trading_sessions` warning 제거 (구현 완료).
- 회귀: `pytest backend/tests/backtest/test_v2_adapter*.py -q`

### 단계 3 — `event_loop.py:StrategyState.sessions_allowed` 필드

```python
@dataclass
class StrategyState:
    ...
    sessions_allowed: tuple[str, ...] = ()
```
event_loop init 시 cfg.trading_sessions 로 주입.

### 단계 4 — Entry hook (Track S + Track A)

- `interpreter.py:1039` `_exec_strategy_call("strategy.entry")` 호출 직전 silent skip.
- `virtual_strategy.py:141` alert hook 동일 패턴.
- 단일 reference: `from src.strategy.trading_sessions import is_allowed`.

### 단계 5 — Fill hook (`check_pending_fills`)

- `event_loop.py:96` + `virtual_strategy.py:184` — pending order fill 시 disallowed session 이면 fill skip + carry-over.

### 단계 6 — 신규 6 tests (각 첫 줄 한국어 주석 의무)

1. `tests/strategy/pine_v2/test_default_qty_priority_chain.py` — D2 chain 4 case (Pine 명시 / form 명시 / Live 1x / fallback) + Pine partial reject
2. `tests/backtest/test_trading_sessions_v2_entry_gate.py` — placement gate
3. `tests/backtest/test_trading_sessions_v2_fill_gate.py` — fill gate
4. `tests/backtest/test_trading_sessions_live_parity.py` — backtest entry hour set == Live `is_allowed` parity
5. `tests/backtest/test_trading_sessions_tz_naive_reject.py` — sessions 활성 + naive index → 422
6. `tests/strategy/pine_v2/test_pine_partial_corpus.py` — corpus AST scan: partial declaration strategy 0건 검증

### 단계 7 — Self-verification

- ruff check . → 0
- mypy src/ → 0
- pytest 전체 → 1652+ PASS / 42 skipped / 0 failed / 0 errors

### 단계 8 — Evaluator dispatch (cold-start, isolation=worktree)

PASS 시 PR. FAIL 시 actionable_issues 반영 후 재 dispatch (max 3).

## 위험 / 가드

- **trading_sessions empty → 회귀 금지**: sessions 비어있으면 reject 하지 말 것 (entry/fill 모두 통과).
- **Pine partial strategy() reject** — A1 의 `PinePartialDeclaration` 422 가 SSOT. 신규 corpus test 는 0건 검증.
- **entry/fill hook 위치** — interpreter.py:1039, virtual_strategy.py:141, :184, event_loop.py:96 (다른 위치 = FAIL).
- **service mutation 0건** — A2 scope 는 compat / interpreter / event_loop / virtual_strategy / v2_adapter 만. LESSON-019 commit spy 의무 없음.
- **금융 숫자 = Decimal** — sizing 관련 신규 코드 float 금지.

## 종료 조건

- 신규 6 tests + 기존 1646 = 1652+ green
- Evaluator PASS
- codex G.4 P1 review 0 critical
- PR 생성 (base = stage/sprint38-bl-188-bl-181) + sig pr_ready + sig pr <num>
