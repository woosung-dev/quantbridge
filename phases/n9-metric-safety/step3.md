# Step 3: [BL-547] 매 tick seed 재도출 + 자기 종결

## 읽어야 할 파일

- `phases/n9-common.md`
- `docs/backlog.md` 의 `### BL-547` 절 — 권장 접근과 **「남는 구멍」** 문장
- `apps/api/src/tasks/live_signal.py` — step 2 가 넣은 `_LEDGER_SEED_SINCE_KEY` 와 읽기 헬퍼
- `apps/api/src/trading/repositories/order_repository.py` — `list_fills_since` · `SessionScope` ·
  `LEDGER_FILL_SCAN_LIMIT`

## 작업

step 2 는 marker 를 **쓰기만** 했다. 이 step 이 그것을 **읽어 쓴다**.

1. **매 tick 재도출** — marker 가 있으면, 공백 tick 이 아니어도 그 창(`since=marker`)의 원장에서
   seed 를 **다시 도출**한다. 도출 경로는 기존 `_ledger_gap_seed` 를 **재사용**해라 — 두 번째
   구현을 만들지 마라.
2. **자기 종결** — 그 창의 순포지션이 0 이 되면 marker 를 지운다. 지우는 것도 `sanitized_report`
   경유다(step 2 와 같은 자리).
3. **실패는 조용히 fail-open** — 재도출 조회가 실패하면 marker 를 **남긴 채** seed 없음으로
   떨어뜨린다. 이유: marker 를 지워 버리면 다음 tick 이 창을 영영 잃는다.

## 벗어나면 안 되는 계약

- **seed 를 거래소에서 가져오지 마라.** 이유: 대조가 동어반복이 되어 가드가 통째로 사라진다
  (`_probe_gap_resync_state` 의 docstring 이 이미 경고한다). seed 의 출처는 **원장**이다.
- **기존 공백 tick 경로의 동작을 바꾸지 마라.** 이 step 은 「공백이 아닌 tick 에도 seed 가 있다」를
  추가하는 것이지, 공백 tick 판정을 바꾸는 것이 아니다.
- **`LEDGER_FILL_SCAN_LIMIT` 오버플로 처리를 그대로 유지해라** — 기존 호출부가
  `fills[:LIMIT]` 와 `overflowed=len(fills) > LIMIT` 을 넘긴다. 재도출도 같아야 한다.
- **부분 청산은 창이 `inadmissible` 이 되어 seed 가 끊긴다** — 원장이 「남는 구멍」으로 적어 둔
  기지의 한계다. **고치려 들지 마라.** 대신 그 경로에 도달했을 때 marker 가 어떻게 되는지를
  테스트로 **고정**하고, `summary` 에 그 선택을 적어라.

## 테스트

step 2 의 `ledger_seed_watermark` 이름 규칙을 유지해 **최소 2개를 더한다**(합계 ≥4):

3. marker 가 있는 **비공백** tick 이 seed 를 재도출한다 — `list_fills_since` 가 `since=marker` 로 불린다
4. 창의 순포지션이 0 이 되면 marker 가 리포트에서 **사라진다**(자기 종결)

★가능하면 다섯 번째로 **재도출 조회 실패 시 marker 가 살아남는다**를 넣어라 — 이것이 fail-open
계약의 유일한 증인이다.

## Acceptance Criteria

- `cd apps/api && uv run --env-file .env.local pytest tests/tasks -q -k 'ledger_seed_watermark'`
- `-k 'ledger_seed_watermark'` 로 수집되는 테스트 ≥4
- `cd apps/api && uv run --env-file .env.local pytest tests/tasks -q`
- `cd apps/api && uv run ruff check src/tasks/live_signal.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **metric 가드와 handler-visibility 가드를 둘 다 돌려라** —
   `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_safety_guard.py tests/tasks/test_live_signal_handler_visibility.py -q`.
   후자는 `try` 본문 줄 수 천장(225)을 잰다 — 새 코드를 `try` 안에 인라인하면 red 가 된다.
   그때는 본문을 늘리지 말고 **조각을 함수로 빼라**.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`_ledger_gap_seed` 를 복제하지 마라. 이유:** 두 벌이 되면 판정 규칙이 갈라지고, 그 갈라짐은
  조용하다. 재사용해라.
- **alembic migration 을 만들지 마라. 이유:** step 2 와 같다 — 마이그레이션 0 이 이 설계의 전제다.
- **부분 청산 구멍을 메우려고 창 판정을 바꾸지 마라. 이유:** 그것은 이 항목의 범위 밖이고, 원장이
  기지의 한계로 적어 둔 것이다. 바꾸면 이 회차가 측정하지 않은 축을 건드린다.
- 커밋하지 마라(커밋은 러너 소관).
