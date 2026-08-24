# Step 3: move-remaining-queries — `kill_switch` · `websocket` 의 쿼리 4건을 옮긴다

## 읽어야 할 파일

- **`phases/n8-common.md`**
- `apps/api/src/trading/kill_switch.py` — 집계 쿼리 2건(`select(func.coalesce(func.sum(Order.realized_pnl), 0))`)
- `apps/api/src/trading/websocket/state_handler.py` — `select(Order)` 1건
- `apps/api/src/trading/websocket/reconciliation.py` — 1건
- `apps/api/src/trading/repositories/order_repository.py` — 집계가 갈 가장 유력한 자리
- `apps/api/src/trading/repositories/kill_switch_event_repository.py`
- `apps/api/tests/trading/` — 기존 회귀

## 작업

남은 위반 4건을 repository 로 옮긴다. Step 2 와 같은 규율이다.

### 집계 쿼리 주의 — 이것이 이 step 의 유일한 함정이다

`kill_switch.py` 의 두 쿼리는 **`func.coalesce(func.sum(...), 0)`** 이다. repository 메서드로
옮길 때 반환 타입을 정확히 지켜라:

- **`Decimal` 을 `float` 으로 바꾸지 마라.** 이유: 손익 집계다. 이 레포는 Decimal-first 다
  (`apps/api/AGENTS.md` §2). `coalesce(..., 0)` 의 0 이 int 로 새지 않게 확인해라.
- **`None` 과 `0` 을 구분하는 의미가 있는지 확인해라.** `coalesce` 가 있으므로 호출부는
  `None` 을 안 받는다는 가정을 할 것이다. 그 가정을 유지해라.

### 동결 목록 갱신

`_FROZEN_VIOLATIONS` 를 **빈 집합**으로 만든다. 그러면 Step 1 의 래칫이 앞으로
**모든 새 위반**을 잡는다.

★비어도 상수를 지우지 마라 — 상수가 사라지면 래칫도 함께 죽는다.

## Acceptance Criteria

```bash
test "$(grep -c 'select(' apps/api/src/trading/kill_switch.py)" -eq 0
test "$(grep -c 'select(' apps/api/src/trading/websocket/state_handler.py)" -eq 0
test "$(grep -c 'select(' apps/api/src/trading/websocket/reconciliation.py)" -eq 0
cd apps/api && uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py -q
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run ruff check src/trading
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. 집계 반환 타입이 `Decimal` 인지 실제로 확인한다(테스트 또는 `python -c` 로 1회).
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **동작을 바꾸지 마라.** 이유: 이동이다. `tests/trading` 이 증인이다.
- **`Decimal` → `float` 변환을 넣지 마라.** 이유: 손익 집계다. 정밀도 손실은 원장에 남는다.
- **`raw SQL` 문자열로 도피하지 마라.** 이유: 경계는 그대로 깨져 있고 AC 만 속인다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
