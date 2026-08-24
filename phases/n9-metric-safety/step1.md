# Step 1: raw metric 15건을 `record_metric_safely` 로 감싼다

## 읽어야 할 파일

- `phases/n9-common.md`
- `apps/api/tests/common/test_metric_safety_guard.py` — step 0 이 만든 가드. **위반 목록의 정본이다**
- `apps/api/src/common/metrics_multiproc.py` — `record_metric_safely` 시그니처
- `apps/api/src/tasks/live_signal.py` — 수리 대상
- `apps/api/src/tasks/live_signal.py` 안의 **이미 감싼 4곳** — 관용구를 여기서 베껴라
  (`grep -n record_metric_safely apps/api/src/tasks/live_signal.py`)

## 작업

`raw_metric_sites()` 가 내는 **15건 전부**를 `record_metric_safely` 로 감싼다.
끝나면 그 함수는 **0건**을 내야 한다.

`record_metric_safely(fn, *args)` 는 **호출 가능한 것과 인자**를 받는다 — 호출 결과가 아니다.

```python
# 전
qb_live_signal_skipped_total.labels(reason="eval_error").inc()
# 후
record_metric_safely(qb_live_signal_skipped_total.labels(reason="eval_error").inc)
```

★**`labels(...)` 는 래퍼 밖에 남는다.** `labels()` 는 조회지 mutation 이 아니고, 안으로 넣으면
라벨 조립 실패까지 삼켜 **어느 축이 죽었는지 못 보게 된다.**

★`gauge.set(value)` 는 인자가 있다 — `record_metric_safely(g.set, value)` 형태로 넘겨라.
`record_metric_safely(g.set(value))` 는 **감싸기 전에 이미 호출**되므로 아무것도 보호하지 않는다.

step 0 이 동결한 값 15를 **0 으로 갱신**해라 — 그것이 이 step 의 산출이다.

## Acceptance Criteria

- `cd apps/api && uv run python -c "from tests.common.test_metric_safety_guard import all_metric_sites, raw_metric_sites; import sys; sys.exit(0 if len(all_metric_sites())>=30 and len(raw_metric_sites())==0 else 1)"`
- `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_safety_guard.py -q`
- `cd apps/api && uv run --env-file .env.local pytest tests/tasks -q`
- `cd apps/api && uv run ruff check src/tasks/live_signal.py tests/common/test_metric_safety_guard.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **`all_metric_sites()` 가 여전히 30건 이상인지 확인해라.** 이 수가 떨어졌다면 metric 호출을
   **지운 것**이지 감싼 것이 아니다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **metric 호출을 삭제하지 마라. 이유:** census 를 0 으로 만드는 가장 쉬운 길이 삭제이고, 그것은
  관측을 없애는 것이다. `all_metric_sites() >= 30` AC 가 그 우회로를 막는다.
- **`try`/`except` 구조를 재배치하지 마라. 이유:** 이 파일에는 「어느 계상이 어느 핸들러에 잡히나」를
  동결한 별도 가드가 있다(`apps/api/tests/tasks/test_live_signal_handler_visibility.py` — `try` 본문
  줄 수 천장 225 · 중첩 depth 동결 목록). 본문을 늘리면 그 가드가 red 가 된다.
- **`record_metric_safely` 의 구현을 바꾸지 마라. 이유:** `src/common/` 은 이 lane 의 디렉터리가
  아니고, 다른 호출자 전부의 계약이다.
- 커밋하지 마라(커밋은 러너 소관).
