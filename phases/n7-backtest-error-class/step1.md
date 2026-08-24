# Step 1: catch-all 을 `"error"` 로 — 「모를 때 사용자 탓으로 돌리지 않는다」

## 읽어야 할 파일

- **`phases/n7-common.md`**
- `apps/api/src/backtest/engine/v2_adapter.py:144-151` — **고칠 자리**
- `apps/api/src/backtest/service.py:415-425` — 이 값이 **사용자에게 어떻게 보이는지**
- Step 0 이 키운 `apps/api/tests/backtest/engine/test_fault_injection.py`

## 설계 결정 (CONTROL 이 정했다 — 임의로 바꾸지 마라)

**`:144` 의 `except Exception` 을 `status="error"` 로 바꾼다.** 그게 전부다.

**왜 「단계를 알아내서 나눈다」가 아닌가:**
파싱과 실행은 `compat.parse_and_run_v2` **한 함수 안**에 있어서 `v2_adapter` 에서는 어느
단계에서 터졌는지 알 수 없다. 알아내려면 `src/strategy/pine_v2/`(**Pine 인터프리터 SSOT**)를
고쳐야 하고 그건 이 회차가 감당할 폭발 반경이 아니다.

**왜 `"error"` 가 옳은 기본값인가:**
`parse_failed` 는 **「당신의 Pine 스크립트가 파싱에 실패했다」**는 구체적 주장이다.
`error` 는 **「실행이 실패했다」**는 약한 주장이다. 우리가 원인을 모를 때 **강한 주장을
사용자 쪽으로 돌리는 것**이 결함이다. 모르면 약한 쪽이 정직하다.

**진짜 파싱 실패는 안 잃는다:** `SyntaxError`(`:126`)가 그대로 `parse_failed` 를 낸다.
`classify` 의 unknown track 은 `ValueError`(`:135`)가 잡는다. 즉 **`parse_failed` 는 생산자를
계속 갖는다** — AC 가 `grep -c 'parse_failed' … -ge 1` 로 그것을 집행한다.

## 작업

1. `v2_adapter.py:144-151` 의 `status="parse_failed"` 를 `status="error"` 로 바꾼다.
   ★로거 이름(`v2_adapter_parse_failed_unexpected`)도 실태에 맞게 고쳐라 —
   **이름이 거짓이면 로그를 읽는 사람이 또 오진한다.**
2. ★**주석을 남겨라** — 「왜 모를 때 `error` 인가」를 한두 줄로. 다음 사람이 이걸
   「분류가 게을러서」로 읽고 되돌리는 것을 막는다.
3. **`test_fault_injection.py:41-51` 의 기대를 뒤집는다.**
   `test_parse_and_run_v2_raises_becomes_parse_failed` → 이름과 단언을 `error` 로.
   ★**이건 회귀가 아니라 「고쳐야 할 red」다.** 그 테스트는 결함을 계약으로 고정하고 있었다.
4. 케이스를 하나 더 추가한다 — **임의 런타임 예외**(예: `KeyError`)가 `error` 가 되는 것.

## Acceptance Criteria

1. `cd apps/api && uv run --env-file .env.local pytest tests/backtest/engine/test_fault_injection.py -q`
2. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/backtest/engine/test_fault_injection.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10`
3. `cd apps/api && uv run --env-file .env.local pytest tests/backtest -q`
4. `cd apps/api && test "$(grep -c 'parse_failed' src/backtest/engine/v2_adapter.py)" -ge 1`

★**AC 4 는 양성 대조다** — `parse_failed` 를 통째로 지워 「오분류 없음」을 만드는 우회로를 막는다.
★**AC 3 은 backtest 전량 회귀다** — 이 변경이 다른 곳을 깨는지 본다.

## `summary` 에 반드시 담을 것

- 실제로 고친 좌표 (줄 번호는 움직인다)
- **뒤집은 테스트의 이름 before/after** 와, 그것이 왜 회귀가 아닌지
- `AC 3` 에서 **함께 red 가 난 다른 테스트가 있었는지** — 있었으면 그 목록과 처리
- 로거 이름을 무엇으로 바꿨는지

## 금지사항

- **`parse_failed` 를 코드에서 통째로 없애지 마라** (AC 4 가 잡는다). `SyntaxError` 분기는 옳다.
- **`src/strategy/pine_v2/` 를 고치지 마라** — Pine 인터프리터 SSOT, 범위 밖.
- **`types.py` 의 Literal 을 줄이지 마라.** 이유: `parse_failed` 는 여전히 생산된다.
- **`.skip`/`xfail` 로 기존 테스트를 넘기지 마라.** 뒤집을 테스트는 **고쳐서** 뒤집어라.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
