# Step 0: 동결 census 30건이 규칙 범위 안인지 측정한다

## 읽어야 할 파일

- `apps/api/tests/common/test_metric_guard_census.py` — 이 축의 **유일한** 검사기. 특히
  `_FROZEN_CENSUS`(87행 근처) · `_result_reporting_try_count()` · `_nearest_result_reporting_try_shape()` ·
  `_handler_reports_business_result()` · `_HARMFUL_MUTATION_CANDIDATES`(65행 근처)
- `apps/api/AGENTS.md` §4 「관측 metric」 행 — **규칙 원문이자 범위 정의**
- `apps/api/src/common/metrics_multiproc.py` — 가드 3종(`record_metric_safely` · `_count_safely` · `_touch_safely`)

## 배경 (이 step 이 이 lane 의 전부다)

원장 [BL-520] 이 지금 열려 있는 이유는 **딱 하나의 미측정** 때문이다.

규칙(`apps/api/AGENTS.md` §4)의 범위는 「**업무 결과를 보고하는 `try`·`except` 본문**」이다.
그런데 `_FROZEN_CENSUS` 는 **그 밖까지 센다** — `src` 전량의 미가드 mutation 을 전부 담는다.
현재 동결값은 **17키 · 합계 30건**이다(`test_unguarded_mutation_counts_match_the_frozen_census`
가 그 두 수를 직접 단언한다).

즉 지금 상태는 이렇다:

- 「해로운 자리 0건」 단언(`test_known_harmful_mutation_sites_are_gone_with_try_scan_control`)은
  **손으로 고른 후보 4쌍**(`_HARMFUL_MUTATION_CANDIDATES`)만 본다
- 나머지 **30건이 규칙 범위 안인지 밖인지 아무도 안 쟀다**

⇒ 이 측정 하나가 [BL-520] 을 가른다. **전부 범위 밖이면 RESOLVED**, 하나라도 안이면 수리 대상이다.

★**이 회차의 산출은 「초록」이 아니라 「수치」다.** 30건 각각에 대해 범위 판정을 남겨라.

## 작업

`apps/api/tests/common/test_metric_guard_census.py` 안에 **범위 판정 축**을 신설한다.
파일을 새로 만들지 마라 — 스캐너가 이미 그 파일에 있다.

### ⑴ 판정 함수

`_FROZEN_CENSUS` 의 각 키(파일, metric)에 대해, 그 파일에서 해당 metric 의 **미가드** mutation
노드를 찾아 `_nearest_result_reporting_try_shape(node, parents)` 를 돌려라.

- 반환이 `None` 이면 **범위 밖**(out-of-scope)
- 반환이 `"A"`/`"B"` 등 모양 문자열이면 **범위 안**(in-scope)

같은 (파일, metric) 에 mutation 이 여러 건이면 **건별로** 판정한다 — 합계만 보면 위치를 잃는다
(그 함정은 파일 714행 근처 주석이 이미 경고하고 있다).

### ⑵ 판정 결과를 동결한다

`_FROZEN_CENSUS_SCOPE: dict[tuple[str, str], tuple[int, int]]` 를 신설해
`{(경로, metric): (in_scope 건수, out_of_scope 건수)}` 를 담아라.
**수치는 네가 직접 측정해 넣어라 — 이 문서에 적힌 숫자를 옮기지 마라.**
불변식: 모든 키에 대해 `in_scope + out_of_scope == _FROZEN_CENSUS[키]`.

### ⑶ 테스트 3건 (이름에 반드시 `census_scope` 를 포함시켜라 — AC 가 `-k census_scope` 로 잡는다)

1. `test_census_scope_classification_matches_the_frozen_map`
   실측 판정 맵이 `_FROZEN_CENSUS_SCOPE` 와 **정확 동등**이다
2. `test_census_scope_totals_reconcile_with_the_census`
   모든 키에서 `in + out == _FROZEN_CENSUS[키]` 이고, 두 맵의 **키 집합이 같다**
3. `test_census_scope_scanner_is_not_vacuous` — ★**양성 대조.**
   `_result_reporting_try_count()` 가 **1 이상**이고, 합성 픽스처(파일 안에 이미 있는
   `test_census_rule_classifies_the_synthetic_fixture` 패턴 재사용)에서 in-scope 판정이
   실제로 나온다. 이 단언이 없으면 「전부 범위 밖」이 **스캐너가 안 닿은 것**과 구별되지 않는다

### ⑷ `summary` 에 반드시 남길 것

- **in-scope 총 건수 · out-of-scope 총 건수**
- in-scope 가 1건 이상이면 **파일·metric·줄번호 목록 전량** (step 1·2 가 이 목록을 소비한다)
- in-scope 가 0건이면 그 사실과 근거(양성 대조가 통과했다는 것)를 명시해라

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k census_scope -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/common -k census_scope --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
```

세 번째는 **양성 대조**다 — 테스트를 안 쓰면 `-k` 가 0건을 수집해 rc≠0 이 된다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. **스캐너를 일부러 속여 봐라** — `src` 의 미가드 mutation 하나를 `try:` 로 감싸고
   `except` 본문에 `logger.error("... failed ...")` 를 임시로 넣어 그 건이 in-scope 로
   **넘어가는지** 확인하고 **반드시 원복**해라. 원복 확인은 `git diff --stat` 으로 한다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`src` 의 동작 코드를 이 step 에서 고치지 마라**(임시 변이는 반드시 원복).
  이유: 이 step 의 산출은 **측정**이고, 측정 대상을 바꾸면 그 측정은 무효다.
- **`_FROZEN_CENSUS` 의 값을 바꾸지 마라.** 이유: 아직 아무것도 안 감쌌다. 값이 바뀌면 조작이다.
- **두 번째 AST census 스크립트를 만들지 마라.** 이유: 검사기가 둘이면 동결 수치의 진실이 둘이 된다.
- **`docs/**` · `CONTEXT.md` · 루트/하위 `AGENTS.md` 를 수정하지 마라.**
  이유: 원장과 가드레일은 CONTROL 소관이고, 단일 파일이라 lane 끼리 충돌한다.
- **최상위 `phases/index.json` 을 수정하지 마라.** 이유: 병렬 lane 이 공유하는 유일한 파일이다.
- **`tests/trading/**` · `tests/scripts/**` 를 만지지 마라.** 이유: 다른 lane 의 소유 구역이다.
- 커밋하지 마라(커밋은 러너 소관).
