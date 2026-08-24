# Step 1: 「해로운 자리 0건」 단언을 손수 고른 4쌍에서 범위 전량으로 넓힌다

## 읽어야 할 파일

- `apps/api/tests/common/test_metric_guard_census.py` — `_HARMFUL_MUTATION_CANDIDATES`(65행 근처) ·
  `_harmful_mutation_sites()` · `test_known_harmful_mutation_sites_are_gone_with_try_scan_control`
- step 0 의 `summary` — in-scope 판정 결과(이 step 의 입력이다)

## 배경

`_harmful_mutation_sites()` 는 **`_HARMFUL_MUTATION_CANDIDATES` 에 있는 (파일, metric) 만** 훑는다:

```python
if (relative_path, metric) not in _HARMFUL_MUTATION_CANDIDATES:
    continue
```

그 집합은 **손으로 고른 4쌍**이다. 즉 「해로운 자리 0건」이라는 이 레포의 가장 강한 단언이
**census 30건 전체를 덮지 않는다.** 새 metric 이 규칙 범위 안에 미가드로 들어와도 그 후보
목록에 이름이 없으면 **조용히 통과**한다.

★이것은 이 레포가 반복해 밟은 「검사기가 보는 표면 < 실제 실패 표면」 패턴이다.

## 작업

### ⑴ 후보 집합을 자동 도출로 바꾼다

`_harmful_mutation_sites()` 의 필터를 **step 0 이 만든 범위 판정**에 연결해라 —
「in-scope 로 판정된 모든 (파일, metric)」 을 훑도록 넓힌다.

`_HARMFUL_MUTATION_CANDIDATES` 를 **지우지 마라.** 그것은 이제 **하한선(제어군)** 으로 남긴다:
자동 도출 집합이 그 4쌍을 **포함하지 않으면 red** 가 되게 단언해라. 이유: 자동 도출이 어느 날
빈 집합이 되면(스캐너 파손) 「0건」이 항진명제로 새는데, 그 4쌍이 하한선이면 그 사고를 잡는다.

### ⑵ 테스트 (이름에 `harmful` 을 포함시켜라 — AC 가 `-k harmful` 로 잡는다)

기존 `test_known_harmful_mutation_sites_are_gone_with_try_scan_control` 은 **그대로 둔다**
(이름·단언 유지 — 그것이 4쌍 제어군이다). 아래를 추가한다:

1. `test_harmful_scan_covers_every_in_scope_census_entry`
   자동 도출 대상 집합 ⊇ step 0 의 in-scope 키 집합
2. `test_harmful_candidate_lower_bound_is_still_covered`
   자동 도출 대상 집합 ⊇ `_HARMFUL_MUTATION_CANDIDATES` (하한선)
3. `test_harmful_sites_are_empty_with_a_positive_control`
   해로운 자리 목록이 비어 있고, **동시에** `_result_reporting_try_count() >= 1` 이다.
   ★두 번째 절이 없으면 「비었다」가 「안 닿았다」와 구별되지 않는다

★**AC 는 `-k harmful` 로 5건 이상을 요구한다.** 기존 것 + 위 3건 + `_HARMFUL_MUTATION_CANDIDATES`
파라미터화 테스트(944행 근처, 4건)로 이미 넘는다. 수집 수가 8 미달이면 네가 뭔가를 지운 것이다.

### ⑶ in-scope 위반이 실제로 있으면

**이 step 에서 고치지 마라.** 목록을 `summary` 에 정확한 좌표(파일:줄:metric)로 남겨라 —
수리는 step 2 다. 이유: 검사기를 넓히는 것과 코드를 고치는 것을 한 커밋에 섞으면
「검사기가 넓어져서 red 인지, 코드가 나빠서 red 인지」를 나중에 못 가른다.

단, 검사기를 넓힌 결과 기존 테스트가 red 가 되면 그 red 는 **정상**이다 — 그 경우
`test_harmful_sites_are_empty_with_a_positive_control` 을 **초록으로 만들려고 단언을 약화하지 마라.**
대신 그 테스트를 step 2 가 닫도록 `summary` 에 적고, AC 가 통과할 최소 형태로 남겨라:
목록이 비지 않으면 그 목록을 **동결 집합과 대조**하는 형태로 쓰고, 동결 집합에 실측 좌표를 넣어라.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k harmful -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/common -k harmful --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **판별력을 재라** — in-scope 인 자리 하나에 미가드 mutation 을 임시로 심고
   `-k harmful` 이 red 가 되는지 확인한 뒤 **반드시 원복**해라(`git diff --stat` 으로 확인).
   red 가 안 나면 넓히기가 실패한 것이다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`src` 를 고치지 마라**(임시 변이는 원복). 이유: 수리는 step 2 소관이다.
- **`_HARMFUL_MUTATION_CANDIDATES` 를 삭제하지 마라.** 이유: 자동 도출이 파손됐을 때
  「0건」이 항진명제로 새는 것을 막는 유일한 하한선이다.
- **단언을 약화해 초록을 만들지 마라.** 이유: 이 lane 의 산출은 초록이 아니라 수치다.
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- **`tests/trading/**` · `tests/scripts/**` 를 만지지 마라.** 이유: 다른 lane 의 소유 구역이다.
- 커밋하지 마라(커밋은 러너 소관).
