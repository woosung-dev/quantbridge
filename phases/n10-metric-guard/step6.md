# Step 6: `common/` 2파일 + `tasks/backtest.py` — 가드 밖 metric mutation 감싸기

## 읽어야 할 파일

- `apps/api/src/common/metrics.py` — 수리 대상
- `apps/api/src/common/redlock.py` — 수리 대상
- `apps/api/src/tasks/backtest.py` — 수리 대상
- `apps/api/src/common/metrics_multiproc.py` — `record_metric_safely` · `_count_safely` · `_touch_safely`
- `apps/api/tests/common/test_metric_guard_census.py` — 동결 census(이 축의 정본 계수기)
- `apps/api/tests/common/test_labels_outside_guard.py` — step 0 이 만든 「라벨이 가드 밖」 검사기
- 이전 step 의 `summary` — 남은 위반 분포

## 배경

기술 기반 층이다. `redlock` 은 **분산 락**이라 여기서 예외가 새면 락 획득·해제가 실패한다. `metrics.py` 는 계측 자신이고, `backtest.py` 는 백테스트 태스크 진입점이다.

규칙 정본은 `apps/api/AGENTS.md` §4 「관측 metric」 행이다 — **업무 결과를 보고하는 `try`/`except`
본문에서 metric mutation 을 raw 로 두지 마라.** 이유: metric 실패 예외가 그 handler 로 흘러
업무 결과를 잘못 기록하거나 루프를 중단시킨다(2026-08-24 실측 4건).

## 작업

위 대상 파일에서 **가드 밖 metric mutation 을 전부 감싼다.** 무엇이 남았는지는
`test_metric_guard_census.py` 를 돌려 실패 메시지로 확인해라 — **이 문서에 건수를 적지 않은 것은
의도적이다**(문서의 숫자는 낡는다. 검사기가 정본이다).

형태 선택은 step 1 과 같다:

| 상황 | 쓸 것 |
| --- | --- |
| 라벨 있는 counter 증가 | `_count_safely(C, **labels)` |
| 라벨 있는 histogram 관측 | `record_metric_safely(lambda: C.labels(**labels).observe(v))` |
| 라벨 있는 실체화(증가 없음) | `_touch_safely(C, **labels)` |
| 라벨 **없는** gauge/counter | `record_metric_safely(C.set, v)` / `record_metric_safely(C.inc)` |

★**`record_metric_safely(C.labels(...).inc)` 는 쓰지 마라** — 인자가 먼저 평가돼
`.labels()` 가 가드 밖에서 돈다. step 0 의 검사기가 이 형태를 red 로 잡는다.

감싼 뒤 `_FROZEN_CENSUS` 를 **실측에 맞춰** 갱신한다 — 사라진 항목은 **삭제**하고(0 으로 낮추면
정확 동등 비교에서 여전히 red 다), 남은 항목은 실제 건수로 맞춘다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k labels_outside_guard -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common tests/tasks -q
cd apps/api && uv run ruff check src/common src/tasks/backtest.py
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **의미 보존** — counter 이름·라벨 키·라벨 값이 그대로인지 diff 로 대조한다.
   `_touch_safely` 로 바꾼 자리는 원래 증가가 **없었는지** 다시 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **검사기를 느슨하게 고치지 마라**(`test_metric_guard_census.py` 의 판정 로직 · `test_labels_outside_guard.py`).
  이유: 통과시키는 것이 목적이 아니다. 검사기 수정이 필요해 보이면 `blocked` 로 멈춰라.
  단 `_FROZEN_CENSUS` **값**의 갱신은 이 step 의 정상 산출이다.
- **`.labels()` 를 지워서 위반을 없애지 마라.** 이유: 라벨은 관측 축이다.
- **대상 파일 밖을 고치지 마라.** 이유: 다른 step 이 그 파일을 갖는다.
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축을 수정하지 마라.** 이유: CONTROL 소관이다.
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
