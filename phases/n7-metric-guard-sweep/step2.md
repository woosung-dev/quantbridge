# Step 2: 모양 B — `except` 본문의 metric 이 **예외를 새게 하는** 자리 2곳

## 읽어야 할 파일

- **`phases/n7-common.md`**
- `apps/api/src/trading/realtime_publisher.py:35-60` — **대상 ③**
- `apps/api/src/trading/webhook.py:170-180` — **대상 ④**
- Step 1 이 등재한 `_PROTECTED_SITES` 항목 (**같은 형식으로** 2건 더 넣는다)

## 이 step 이 고치는 것 — 모양 A 와 왜 다른가

모양 A 는 metric 이 **try 본문**에 있어서 실패하면 `except` 로 떨어졌다(업무 결과가 뒤집힘).
모양 B 는 metric 이 **`except` 본문 안**에 있다. 여기서 실패하면 **핸들러 자신이 던지고,
그 예외는 잡아 줄 사람이 없다** — 원래 잡으려던 예외까지 함께 밖으로 샌다.

| # | 자리 | 해악 |
| --- | --- | --- |
| ③ | `realtime_publisher.py:55` `qb_rt_publish_failed_total.inc()` | try@35 · except@52. 발행 실패를 **세다가** 예외가 새서 상위 경로가 죽는다 |
| ④ | `webhook.py:176` `qb_webhook_symbol_rejected_total.inc()` | try@173 · except@175. 심볼 거절을 **세다가** 웹훅 응답 경로가 죽는다 |

★**모양 B 가 더 나쁠 수 있다.** 모양 A 는 잘못된 값이 기록되지만, 모양 B 는 **아무것도
기록되지 않고 요청이 실패**한다. 그리고 원인은 관측 코드다.

## 작업

1. 두 자리를 `record_metric_safely(...)` 로 감싼다 (Step 1 과 같은 관용구).
2. **`_FROZEN_CENSUS` 에서 해당 키 2개를 지운다** — 다시 말하지만 **`: 0` 금지, 키 삭제.**
3. **래칫을 내린다** — `len(_FROZEN_CENSUS) == 38` → **36**,
   `sum(_FROZEN_CENSUS.values()) == 81` → **79**.
4. **두 자리를 `_PROTECTED_SITES` 에 등재한다** (Step 1 과 같은 형식).
5. ★**Step 0 이 심은 「해로운 자리」 목록이 이제 비어야 한다.** 그런데 **빈 목록을 그대로
   통과시키면 안 된다** — 「0건이니 통과」는 대상에 안 닿아도 참이다. 그 테스트를
   **「알려진 해로운 자리 0건 + 스캐너가 훑은 try 수 ≥ N」** 형태로 바꿔라(양성 대조 동반).

## Acceptance Criteria

1. `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py -q`
2. `cd apps/api && test "$(grep -c 'len(_FROZEN_CENSUS) == 36' tests/common/test_metric_guard_census.py)" -ge 1`
3. `cd apps/api && test "$(grep -c 'sum(_FROZEN_CENSUS.values()) == 79' tests/common/test_metric_guard_census.py)" -ge 1`
4. `cd apps/api && uv run --env-file .env.local pytest tests/tasks tests/common tests/trading -q`

## `summary` 에 반드시 담을 것

- 고친 좌표 2개 (재측정값)
- 「해로운 자리 0건」 테스트에 **어떤 양성 대조**를 붙였는지 — 이게 이 step 의 핵심 산출이다
- `_PROTECTED_SITES` 총 건수 (Step 1 의 2건 + 이 step 의 2건)

## 금지사항

- **「해로운 자리 0건」을 양성 대조 없이 단언하지 마라.** 이유: 스캐너가 대상에 안 닿아도
  0건은 참이다. 이 레포가 반복해 밟은 함정이다.
- **`_FROZEN_CENSUS` 항목을 `: 0` 으로 남기지 마라.**
- **래칫 단언을 지워서 통과하지 마라** (AC 2·3 이 잡는다).
- **`apps/api/AGENTS.md` 에 규칙을 등재하지 마라** — `summary` 에 문안만.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
