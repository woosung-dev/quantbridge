# Step 0: census 실패 메시지 수리 + 「라벨이 가드 밖」 축 신설

## 읽어야 할 파일

- `apps/api/tests/common/test_metric_guard_census.py` — 이 축의 **유일한** 검사기(동결 census)
- `apps/api/src/common/metrics_multiproc.py` — 가드 3종 정의(`record_metric_safely` · `_count_safely` · `_touch_safely`)
- `apps/api/tests/tasks/test_closed_pnl_sweep_metric_failure.py` — 고장 주입 선례(`.labels()` 에 주입한다)
- `apps/api/AGENTS.md` §4 「관측 metric」 행 — 규칙 원문

## 배경 (이 step 이 왜 먼저인가)

이 회차는 가드 밖 metric mutation 을 감싸는 회차다. 그런데 **지금 상태로 착수하면 두 가지가 조용히 깨진다.**

**⑴ census 실패 메시지가 틀린 복구 지시를 한다.**
`_census_failure_message` 는 감소한 항목에 대해 「이 항목을 0 으로 낮춰라」라고 출력한다.
그러나 `_FROZEN_CENSUS` 는 `dict` 이고 비교는 `actual == _FROZEN_CENSUS` 정확 동등이다 —
`Counter()` 와 `{'k': 0}` 은 **같지 않다**(python 3.12 실측). 0 으로 낮추면 여전히 red 다.
올바른 복구는 **항목 삭제**다. 메시지를 그대로 따르면 무인 세션이 재시도 한도를 태운다.

**⑵ 「감쌌다」의 절반이 가짜다.**
`record_metric_safely(fn, *args)` 는 **인자를 먼저 평가**한다. 따라서

```python
record_metric_safely(qb_x.labels(reason="y").inc)   # ← .labels() 가 가드 **밖**에서 실행된다
```

는 `.labels()` 가 던지는 예외(멀티프로세스 모드에서 새 라벨 조합은 그 시점에 mmap 파일을
늘리므로 디스크 full·권한 오류가 가능하다)를 **막지 못한다**. 이것은 추측이 아니라
`_count_safely` 의 docstring 자신이 적어 둔 경고다(「`.inc()` 만 감싸면 절반만 막는 것」).

올바른 형태는 둘 중 하나다:

```python
_count_safely(qb_x, reason="y")            # 라벨 + 증가를 함께 격리 (권장)
record_metric_safely(lambda: qb_x.labels(reason="y").observe(v))   # 지연 평가
```

★**그리고 census 는 이 결함을 못 잡는다** — `_guarded_node_ids` 가 가드 호출의 **인자 서브트리
전체**를 guarded 로 세기 때문에, 위의 잘못된 형태도 「감싸졌다」로 계상된다. 즉 이 축을 안 세우고
step 1~6 을 진행하면 **lane 이 초록을 내면서 결함을 복제한다.**

## 작업

### ⑴ `_census_failure_message` 수리

감소한 항목에 대한 복구 지시를 「**그 항목을 `_FROZEN_CENSUS` 에서 삭제해라**」로 고쳐라.
증가한 항목의 지시(감싸라)는 그대로 둔다. 메시지에 「0 으로 낮춰라」가 남아 있으면 안 된다.

### ⑵ 새 검사기 `apps/api/tests/common/test_labels_outside_guard.py` 신설

**규칙** — `record_metric_safely(<expr>)` 의 첫 인자가 `ast.Lambda` 가 **아니면서** 그 서브트리에
`.labels(` 호출을 포함하면 위반이다.

- 스캔 대상은 `apps/api/src` 전량
- **`ast.Lambda` 는 제외한다** — 지연 평가라 `.labels()` 가 가드 안에서 돈다. 이것이 정답 형태다
- 동결 방식은 census 와 같게 한다: `_FROZEN_LABELS_OUTSIDE_GUARD: dict[str, int]` 에
  `{경로: 건수}` 를 담고 **정확 동등** 비교한다. **수치는 네가 직접 측정해서 넣어라 —
  이 문서에 적힌 숫자를 옮기지 마라.**
- 실패 메시지는 ⑴ 과 같은 규율을 따른다(삭제/추가를 정확히 지시)

**테스트는 최소 2건이다:**

1. `test_labels_outside_guard_matches_the_frozen_set` — 위반 집합이 동결과 정확히 같다
2. `test_lambda_wrapped_labels_are_not_flagged` — ★**음성 대조.** `record_metric_safely(lambda: ...)`
   형태는 위반으로 잡히지 **않아야** 한다. 이 트리에 그 형태가 실재하므로(직접 세라) 그 건수를
   함께 단언해 검사기가 「전부 잡는」 항진명제가 아님을 증명한다

### ⑶ 착수 전 red 를 측정해 `summary` 에 남겨라

새 검사기의 동결 수치가 **0 이 아니어야 한다** — 0 이면 검사기가 대상에 닿지 않은 것이다.
파일별 분포를 `summary` 에 적어라. 다음 step 들이 그 목록을 소비한다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k labels_outside_guard -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/common -k labels_outside_guard --collect-only -q 2>/dev/null | grep -c '::')" -ge 2
```

세 번째는 **양성 대조**다 — 테스트를 안 쓰면 `-k` 가 0건을 수집해 rc≠0 이 된다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. 새 검사기를 **일부러 깨뜨려 봐라** — `src` 어딘가에 `record_metric_safely(qb_x.labels(a="b").inc)`
   를 임시로 심고 red 가 나는지, 되돌리면 green 인지 확인하고 **반드시 원복**해라.
   원복 확인은 `git diff --stat` 으로 한다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`_FROZEN_CENSUS` 의 값을 이 step 에서 바꾸지 마라.** 이유: 이 step 은 아직 아무것도 안 감쌌다.
  값이 바뀌면 그것은 측정이 아니라 조작이다.
- **두 번째 AST census 스크립트를 만들지 마라.** 이유: `test_metric_guard_census.py` 가 이미 그
  스크립트다. 검사기가 둘이면 동결 수치의 진실이 둘이 된다.
- **`src` 의 동작 코드를 이 step 에서 고치지 마라**(임시 변이는 반드시 원복). 이유: 이 step 의 산출은
  검사기이고, 수리는 step 1 부터다.
- **`docs/status.md`·`docs/backlog.md`·`CONTEXT.md`·`AGENTS.md`·`apps/api/AGENTS.md`·`apps/web/AGENTS.md`
  를 수정하지 마라.** 이유: 원장과 가드레일은 CONTROL 소관이다.
- **최상위 `phases/index.json` 을 수정하지 마라.** 이유: 병렬 lane 이 공유하는 유일한 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
