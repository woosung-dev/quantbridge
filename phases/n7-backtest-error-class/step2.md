# Step 2: 변이 + 음성 대조 — 이 그물이 **양쪽을** 재는지 증명한다

## 읽어야 할 파일

- **`phases/n7-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- Step 0·1 이 키운 `apps/api/tests/backtest/engine/test_fault_injection.py`
- `apps/api/src/backtest/engine/v2_adapter.py`

## 왜 이 step 이 있나

이 lane 의 변경은 **한 줄**이다. 한 줄짜리 변경일수록 「테스트가 그 줄을 실제로 재는가」가
불확실하다. 그리고 이 lane 은 **양방향** 계약을 갖는다:

- **양성** — 예상 못 한 예외는 `error` 여야 한다 (새 계약)
- **음성** — `SyntaxError` 는 여전히 `parse_failed` 여야 한다 (안 잃은 것)

**음성을 안 재면 「전부 error 로 만들었다」와 구별이 안 된다.**

## 작업

1. **변이 ⑴ (되돌리기)** — `v2_adapter.py` 의 catch-all 을 `"parse_failed"` 로 **되돌린다.**
   Step 1 이 뒤집은 테스트가 **red** 여야 한다. red 가 아니면 그 테스트는 그 줄을 안 재는 것이다.
2. **변이 ⑵ (과잉 적용)** — `SyntaxError` 분기(`:126`)도 `"error"` 로 바꾼다.
   Step 0 이 심은 **음성 대조 케이스가 red** 여야 한다. red 가 아니면 「진짜 파싱 실패를
   잃었다」를 아무도 못 잡는다.
3. ★**두 변이가 각각 대상에 도달했는지 확인해라.** 도달 못 한 변이의 red 0 은 무증거다.
4. **복원한다.** ★`git checkout` **금지** — 스냅샷 되쓰기 + `sha256` 왕복 대조.
5. 케이스를 하나 더 추가해 **최소 11건**으로 만든다. 좋은 후보:
   `service.py` 가 사용자에게 보이는 문구(`engine status=…`)에 **`parse_failed` 가 안 나오는**
   것을 임의 런타임 예외 경로에서 확인하는 케이스 — 이 lane 의 **실제 사용자 영향**을 고정한다.

## Acceptance Criteria

1. `cd apps/api && uv run --env-file .env.local pytest tests/backtest/engine/test_fault_injection.py -q`
2. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/backtest/engine/test_fault_injection.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 11`
3. `cd apps/api && uv run --env-file .env.local pytest tests/backtest -q`
4. `cd apps/api && uv run ruff check src/backtest/engine/v2_adapter.py tests/backtest/engine/test_fault_injection.py`
5. `cd apps/api && uv run ruff format --check tests/backtest/engine/test_fault_injection.py`

## `summary` 에 반드시 담을 것

- **변이 ⑴/⑵ 각각**: 무엇을 바꿨고 어떤 테스트가 어떤 메시지로 red 였는지 (메시지 원문)
- **도달 확인** 근거 2건
- 복원 sha256 왕복 대조 결과
- 마지막 케이스가 고정하는 **사용자 영향**이 무엇인지 한 줄

## 금지사항

- **변이를 심은 채로 끝내지 마라.** 복원 후 AC 전건 green 이어야 한다.
- **`git checkout` 으로 복원하지 마라** — 커밋 안 된 편집을 같이 날린다.
- **「red 가 났으니 됐다」로 끝내지 마라** — 변이가 **대상에 도달**했는지 따로 확인해라.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
