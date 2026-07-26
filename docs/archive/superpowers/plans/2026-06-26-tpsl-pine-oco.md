# OCO TP/SL Exit Orders + Interface Lock (T0-pine-oco) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. 정석 TDD (test-first). 각 동작 RED → 최소 GREEN → refactor. 7 semantic commit, 각 green 후 다음.

**Goal:** pine_v2 인터프리터에 OCO TP/SL exit order 를 구현해 백테스트가 손익보호를 정직하게 시뮬하고, 그 코드가 Wave 1 라이브 주문이 import 할 frozen 계약을 제공한다.

**Architecture:** 신규 `exit_orders.py` 가 exit-order 종류 + 동시-체결 우선순위 SSOT (Wave1 import용 frozen 계약). `StrategyState` 에 `pending_exits` (entry_id → exit bracket) 분리 슬롯 추가 — 기존 `pending_orders`(entry stop) 경로는 byte-identical 보존. 이벤트 루프가 매 bar 시작 `check_exit_fills` 호출 (entry fill 검사 직후). 비용은 기존 `_leg_cost` SSOT 로 exit-leg maker/taker 라우팅.

**Tech Stack:** Python 3.12, pytest, pine_v2 인터프리터, Decimal(cost 경계만), float(pine_v2 가격 관례).

## Global Constraints

- demo-only / 실자금 0. migration 0 (`ExitOrderKind` = in-memory enum). 신규 Celery task 0. exec/eval 금지.
- 금융 숫자: pine_v2 `PendingOrder`/`Trade` 의 기존 float 관례 존중. Decimal 경계 = cost SSOT `_leg_cost` 뿐.
- 신규 파일 첫줄 한국어 역할주석. 사고/문서 한국어, 네이밍/커밋 영어.
- **회귀 게이트:** 신규 동작은 전부 `kind is not None` / `pending_exits` 비어있지 않음 / `pyramiding is not None` 뒤로 gate. default 미설정 시 `check_pending_fills`/`entry` byte-identical.
- 커밋 trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **anti-circular golden (LESSON-039):** 손계산 오라클 먼저 RED → 엔진 일치 확인 → 그 후에만 expected.json 재생성. 엔진으로 엔진 검증 금지.

---

## File Structure

- Create `backend/src/strategy/pine_v2/exit_orders.py` — exit-order kind enum + same-bar fill priority SSOT (frozen 계약).
- Modify `backend/src/strategy/pine_v2/strategy_state.py` — `ExitOrder` dataclass + `pending_exits` 슬롯 + `place_exit` / `check_exit_fills` + pyramiding cap.
- Modify `backend/src/strategy/pine_v2/interpreter.py` — `strategy.exit` NOP 교체 (1296-1324).
- Modify `backend/src/strategy/pine_v2/event_loop.py` — 매 bar `check_exit_fills` 호출 + pyramiding 스레딩.
- Modify `backend/src/strategy/pine_v2/ast_extractor.py` — `DeclarationInfo.pyramiding` 추출.
- Modify `backend/src/strategy/pine_v2/compat.py` / `track_runner.py` / `virtual_strategy.py` — pyramiding 스레딩 (필요한 곳만).
- Modify `backend/src/backtest/engine/v2_adapter.py` — exit-leg `fill_type` 라우팅 (`Trade.exit_kind` 기반).
- Modify `backend/src/backtest/engine/types.py` — (필요 시) RawTrade exit_kind 필드.
- Tests: `test_exit_order_interface_lock.py` / `test_exit_orders_oco.py` / `test_strategy_exit_interpreter.py` / `test_exit_leg_cost_split.py` / `test_golden_oracle_ema_sltp.py`.

---

### Task C1: exit-order kind + same-bar fill-priority SSOT (interface lock)

**Files:**

- Create: `backend/src/strategy/pine_v2/exit_orders.py`
- Test: `backend/tests/strategy/pine_v2/test_exit_order_interface_lock.py`

**Interfaces — Produces (★ Wave1 frozen 계약):**

- `class ExitOrderKind(str, Enum)`: `TAKE_PROFIT="take_profit"`, `STOP_LOSS="stop_loss"`, `TRAILING_STOP="trailing_stop"`.
- `SAME_BAR_FILL_PRIORITY: tuple[ExitOrderKind, ...] = (STOP_LOSS, TRAILING_STOP, TAKE_PROFIT)`.
- `def fill_type_for(kind: ExitOrderKind) -> str` — TAKE_PROFIT→"maker", STOP_LOSS/TRAILING_STOP→"taker".
- `def pessimistic_fill_order(kinds: Iterable[ExitOrderKind]) -> list[ExitOrderKind]` — SAME_BAR_FILL_PRIORITY 순 정렬 (안정·중복 보존).

- [ ] Step1 RED: enum values / priority tuple / fill_type_for maker·taker / pessimistic_fill_order ordering lock test.
- [ ] Step2 run → FAIL (module missing).
- [ ] Step3 GREEN: implement module.
- [ ] Step4 run → PASS.
- [ ] Step5 commit `feat(pine_v2): exit-order kind + same-bar fill-priority SSOT (interface lock)`.

### Task C2: PendingOrder/ExitOrder exit kind + limit-fill branch + trailing slot

**Files:**

- Modify: `backend/src/strategy/pine_v2/strategy_state.py`
- Test: `backend/tests/strategy/pine_v2/test_exit_orders_oco.py`

**Interfaces — Produces:**

- `@dataclass ExitOrder`: `from_entry`, `position_direction: Direction`, `kind: ExitOrderKind`, `stop_price: float|None`, `limit_price: float|None`, `trail_offset: float|None`, `placed_bar: int`, runtime `trail_anchor: float|None`. method `update_trailing(high, low)` + `try_fill_exit(bar, open_, high, low) -> float|None`.
- limit-fill: long TP limit → high>=limit → fill at max(open*, limit) (gap-through→open). long SL stop → low<=stop → fill at min(open*, stop). short 대칭.
- `StrategyState.pending_exits: dict[str, list[ExitOrder]]` (keyed by from_entry).

- [ ] Step1 RED: ExitOrder fill branch (TP/SL gap-through), trailing ratchet (불리방향 고정) unit tests.
- [ ] Step2 FAIL. Step3 GREEN. Step4 PASS. Step5 commit.

### Task C3: implement strategy.exit (TP/SL/trail binding) — replace NOP (BL-104)

**Files:**

- Modify: `backend/src/strategy/pine_v2/interpreter.py:1296-1324`
- Modify: `backend/src/strategy/pine_v2/strategy_state.py` (place_exit)
- Modify: `backend/src/strategy/pine_v2/event_loop.py` (check_exit_fills 호출)
- Test: `backend/tests/strategy/pine_v2/test_strategy_exit_interpreter.py`

**Behavior:** profit/limit→TP limit, loss/stop→SL stop, trail_points/trail_offset→trailing. from_entry="" → 전체 open. when=False skip. 재호출 = 같은 (from_entry,id) 브래킷 replace. NOP 경고 문자열 제거 → real-exit assert.

- [ ] Step1 RED: strategy.exit places bracket → next bar fills at target. Step2 FAIL. Step3 GREEN. Step4 PASS. Step5 commit.

### Task C4: OCO sibling-cancel + pessimistic same-bar TP/SL determinism

**Files:**

- Modify: `backend/src/strategy/pine_v2/strategy_state.py`
- Test: `backend/tests/strategy/pine_v2/test_exit_orders_oco.py`

**Behavior:** one leg fills → sibling bracket purge. same-bar TP+SL both trigger → SL 우선(pessimistic, SAME_BAR_FILL_PRIORITY). 반대신호 청산 시 OCO purge. session-disallowed bar → exit carry-over.

- [ ] RED → FAIL → GREEN → PASS → commit.

### Task C5: pyramiding cap in DeclarationInfo + entry enforcement

**Files:**

- Modify: `ast_extractor.py` (DeclarationInfo.pyramiding 추출), `compat.py`/`track_runner.py`/`virtual_strategy.py`/`event_loop.py` (스레딩), `strategy_state.py` (entry cap).
- Test: `backend/tests/strategy/pine_v2/test_strategy_exit_interpreter.py` (pyramiding overflow skip).

**Behavior:** `pyramiding is not None` 시에만 enforce. 같은 direction open 수 >= cap → 신규 entry skip. None → byte-identical.

- [ ] RED → FAIL → GREEN → PASS → commit.

### Task C6: exit-leg maker/taker cost split via \_leg_cost SSOT

**Files:**

- Modify: `backend/src/strategy/pine_v2/strategy_state.py` (Trade.exit_kind 태그), `backend/src/backtest/engine/v2_adapter.py` (exit leg fill_type 라우팅).
- Test: `backend/tests/backtest/test_exit_leg_cost_split.py`

**Behavior:** Trade 가 exit_kind 보유 → v2_adapter exit leg `fill_type=fill_type_for(exit_kind)`. C14 불변식 `total_fees+total_slippage==Σ per-trade (fee+slip)` 보존. exit_kind None → taker (byte-identical).

- [ ] RED → FAIL → GREEN → PASS → commit.

### Task C7: golden hand-oracle for EMA-SLTP; un-skip + regenerate golden (BL-022)

**Files:**

- Create: `backend/tests/backtest/test_golden_oracle_ema_sltp.py` (손계산 오라클, 통제된 소형 OHLCV)
- Modify: `backend/tests/backtest/engine/test_golden_backtest.py:19-21` (skip 해제)
- Regenerate: `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/expected.json`

**anti-circular:** 손계산 오라클 먼저 RED (작은 통제 시나리오 손계산값 하드코딩) → 엔진 출력이 손계산과 일치 확인 → **그 후에만** 전체 golden expected.json 을 (신뢰된) 엔진으로 재생성 + skip 해제.

- [ ] Step1 RED: 손계산 오라클 (engine 미사용 기대값). Step2 FAIL. Step3: 엔진이 일치. Step4 PASS. Step5: expected.json 재생성 + unskip. Step6 commit.

### 회귀 게이트 (전 task 공통)

- `test_no_exit_orders_regression`: strategy.exit 없는 전략 → pending_exits empty → 기존과 byte-identical.
- "NOP 경고 문자열" assert 하던 기존 테스트 → real-exit assert 전환 (C3 commit 에 열거).
