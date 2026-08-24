# Step 1: `live_signal.py` — 라벨을 가드 안으로

## 읽어야 할 파일

- `apps/api/src/tasks/live_signal.py` — 수리 대상
- `apps/api/src/common/metrics_multiproc.py` — `_count_safely` / `_touch_safely` / `record_metric_safely`
- `apps/api/tests/common/test_labels_outside_guard.py` — step 0 이 만든 검사기(위반 목록의 정본)
- 이전 step 의 `summary` — 파일별 위반 분포

## 배경

직전 회차(n9)가 이 파일의 metric mutation 을 `record_metric_safely(...)` 로 감쌌다. 그 수리는
**절반만 유효하다** — `record_metric_safely` 는 인자를 먼저 평가하므로
`record_metric_safely(qb_x.labels(...).inc)` 에서 `.labels()` 는 가드 **밖**에서 실행된다.

step 0 의 검사기가 이 파일에서 위반을 잡고 있다. **이 step 이 그것을 0 으로 만든다.**
이 파일을 먼저 고치는 이유는 위반이 여기에 집중돼 있고, 뒤 step 들이 같은 실수를 복사하지
않도록 **올바른 형태의 선례를 이 파일에 먼저 세우기 위해서**다.

## 작업

step 0 검사기가 잡는 이 파일의 위반을 **전부** 올바른 형태로 바꾼다.

| 원래 형태 | 바꿀 형태 | 왜 |
| --- | --- | --- |
| `record_metric_safely(C.labels(**kw).inc)` | `_count_safely(C, **kw)` | 라벨 생성 + 증가를 함께 격리 |
| `record_metric_safely(C.labels(**kw).observe, v)` | `record_metric_safely(lambda: C.labels(**kw).observe(v))` | `_count_safely` 는 `.inc()` 전용이라 못 쓴다 |
| `record_metric_safely(C.labels(**kw))` (증가 없음) | `_touch_safely(C, **kw)` | 라벨 실체화만. `_count_safely` 를 쓰면 1 이 올라 계측이 거짓말한다 |

- `_count_safely` / `_touch_safely` 는 `src/common/metrics_multiproc.py` 에서 import 한다.
  이미 import 돼 있으면 재사용해라.
- **라벨이 없는 호출**(`record_metric_safely(gauge.inc)` 처럼 `.labels()` 가 없는 것)은 **건드리지 마라.**
  그 형태는 결함이 아니다.
- 계측의 **의미를 바꾸지 마라** — 증가하던 것은 증가하고, 관측하던 값은 같은 값이어야 한다.
  `_touch_safely` 와 `_count_safely` 를 혼동하면 창 차분이 틀어진다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k labels_outside_guard -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/tasks -q
cd apps/api && uv run ruff check src/tasks/live_signal.py
```

두 번째가 중요하다 — 형태를 바꾸면 census 의 guarded 판정도 함께 움직인다.
census 가 red 면 `_FROZEN_CENSUS` 를 **실측에 맞춰** 고쳐라(항목 삭제/추가. 「0 으로 낮추기」는 안 된다).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **의미 보존 확인** — 바꾼 자리마다 counter 이름·라벨 키·라벨 값이 그대로인지 diff 로 대조해라.
   `_touch_safely` 로 바꾼 자리는 원래 `.inc()` 가 **없었는지** 다시 확인해라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **검사기(`test_labels_outside_guard.py`)를 느슨하게 고치지 마라.** 이유: 이 step 의 목적은
  위반을 없애는 것이지 검사기를 통과시키는 것이 아니다. 검사기 수정이 필요해 보이면 `blocked` 로 멈춰라.
- **`.labels()` 를 지워서 위반을 없애지 마라.** 이유: 라벨은 관측 축이다. 지우면 대시보드가 죽는다.
- **이 step 에서 다른 파일을 고치지 마라.** 이유: step 2~6 이 파일별로 나뉘어 있다.
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축(`CONTEXT.md`·`AGENTS.md`·`apps/api/AGENTS.md`·`apps/web/AGENTS.md`)
  을 수정하지 마라.** 이유: 원장·가드레일은 CONTROL 소관이다.
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
