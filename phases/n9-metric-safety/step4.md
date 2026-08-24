# Step 4: 변이 자기점검 — 두 가드가 실제로 잡는지 증명한다

## 읽어야 할 파일

- `phases/n9-common.md`
- `apps/api/tests/common/test_metric_safety_guard.py` — step 0 이 세운 가드
- step 2·3 이 만든 `ledger_seed_watermark` 테스트들

## 작업

**이 step 은 새 기능을 만들지 않는다.** 앞 step 들이 세운 검사가 **판별력이 있는지**를 변이로 잰다.
「N개 통과」는 검사가 옳다는 증거가 아니다 — 위반을 심었을 때 **red 가 나야** 증거다.

각 변이는 ⑴ 심고 ⑵ 검사가 red 인지 확인하고 ⑶ **반드시 원복**한다.
원복 확인은 `git diff --quiet -- apps/api` 로 해라 — 눈으로 보지 마라.

### 심을 변이 4종

| # | 어디에 | 무엇을 | 기대 |
| --- | --- | --- | --- |
| 1 | `live_signal.py` 의 이미 감싼 호출 하나 | `record_metric_safely(...)` 를 벗겨 raw 로 되돌린다 | `raw_metric_sites()` 가 1건 → 가드 red |
| 2 | `live_signal.py` | `try` **밖**에 raw metric 호출을 하나 추가 | 가드는 **green 이어야 한다**(음성 대조 — 규칙은 try/except 본문 한정이다) |
| 3 | seed 재도출 경로 | `since=marker` 를 `since=None` 으로 바꾼다 | `ledger_seed_watermark` 테스트 red |
| 4 | 자기 종결 경로 | 순포지션 0 일 때 marker 를 지우는 분기를 제거 | `ledger_seed_watermark` 테스트 red |

★**변이 2는 green 이 정답이다.** 전건 red 를 기대하지 마라 — 규칙보다 넓게 잡는 가드는
관계없는 코드를 막는다. 이 음성 대조가 그 과잉을 잰다.

★**변이가 red 를 안 냈다면 그것이 이 step 의 산출이다.** 숨기지 말고 `summary` 에 정확히 적어라 —
「변이 N 이 초록으로 빠져나갔다. 원인 = …」. 가드를 급히 넓히지 말고 **사실을 남겨라.**

## `summary` 에 반드시 담을 것

- 변이 4종의 결과(각각 red/green 과 기대와의 일치 여부)
- step 3 의 「부분 청산 → 창 inadmissible」에서 marker 를 어떻게 처리하기로 했는지
- 가드가 **못 잡는 것**(별칭·동적 접근·다른 파일 등) — 다음 사람이 이 가드를 과신하지 않도록

## Acceptance Criteria

- `cd apps/api && uv run python -c "from tests.common.test_metric_safety_guard import all_metric_sites, raw_metric_sites; import sys; sys.exit(0 if len(all_metric_sites())>=30 and len(raw_metric_sites())==0 else 1)"`
- `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_safety_guard.py tests/tasks -q`
- `cd apps/api && uv run ruff check src/tasks/live_signal.py tests/common/test_metric_safety_guard.py`
- `cd apps/api && uv run ruff format --check tests/common/test_metric_safety_guard.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **변이를 전부 원복했는지 `git diff` 로 확인해라.** 변이가 남은 채 커밋되면 러너는 AC 만 보고
   통과시킬 수 있다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **변이를 원복하지 않은 채 끝내지 마라. 이유:** 러너의 AC 는 변이가 남았는지 안 본다.
- **변이가 초록으로 빠져나갔을 때 가드를 넓혀서 덮지 마라. 이유:** 급히 넓힌 가드는 관계없는 코드를
  막고, 그 사실은 다음 회차에 발견된다. 사실을 `summary` 에 남기는 것이 이 step 의 산출이다.
- **`xfail(strict=True)` 를 쓰지 마라. 이유:** 그것은 「제품 코드가 틀렸다」를 원장에 박는 주장이고
  코드 대조 없이 쓰면 AC·변이·diff 세 층이 전부 통과시킨다(2026-08-21 실증).
- 커밋하지 마라(커밋은 러너 소관).
