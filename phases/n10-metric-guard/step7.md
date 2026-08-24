# Step 7: 자기-계상 자리를 census allowlist 로 명문화

## 읽어야 할 파일

- `apps/api/src/common/metrics_multiproc.py` — 특히 `record_metric_safely` 본문의 `except` 절
- `apps/api/tests/common/test_metric_guard_census.py` — 동결 census + 실패 메시지
- 이전 step 의 `summary`

## 배경

`record_metric_safely` 의 `except` 절은 **자기 자신의 실패를 계상**한다
(`qb_metrics_mutation_failed_total.inc()`). census 는 guarded 판정을 **이름 기반**으로 하므로
이 자리를 「가드 밖 mutation」으로 센다 — 그러나 이 자리는:

1. **감싸면 안 된다.** 자기 자신을 부르면 무한 재귀다.
2. **이미 보호돼 있다.** 그 `inc()` 는 자체 `try/except` 안에 있다(같은 함수 안에서 확인해라).

즉 census 가 **안전한 코드를 위반으로 세고 있다.** 앞 step 들이 나머지를 전부 감싸고 나면 이 자리만
남아 「왜 아직 0 이 아닌가」가 영구 질문으로 남는다.

## 작업

이 자리를 **명시적 allowlist 로 승격**한다 — 동결 딕셔너리에 조용히 남겨 두지 말고,
「의도된 예외이고 위반이 아니다」를 검사기가 스스로 말하게 한다.

1. `test_metric_guard_census.py` 에 `_CENSUS_ALLOWLIST` 를 도입한다.
   - 자료형은 `_FROZEN_CENSUS` 와 같은 `(경로, metric) → 건수` 키를 쓴다
   - **각 항목마다 이유를 주석으로 남긴다** — 「무한 재귀」·「자체 try/except 로 이미 보호」
2. census 판정에서 allowlist 항목을 제외한다. 제외 방식은 네 재량이되 **동결의 정확 동등 성질을
   깨지 마라** — allowlist 가 「무엇이든 통과」가 되면 이 검사기의 값이 사라진다.
3. **allowlist 자신을 재는 테스트를 1건 이상 둔다** — 이름에 `census_allowlist` 를 포함시켜라.
   최소 단언: ⑴ allowlist 의 모든 항목이 **실제로 소스에 존재한다**(죽은 항목이 쌓이는 것을 막는다)
   ⑵ allowlist 를 비우면 그 자리가 다시 위반으로 잡힌다(= 판별력 확인. 테스트 안에서 국소적으로 검증)

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k census_allowlist -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/common -k census_allowlist --collect-only -q 2>/dev/null | grep -c '::')" -ge 1
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **allowlist 가 너무 넓지 않은지 확인해라** — 항목 수를 세고 `summary` 에 적어라. 이 회차가 넣는
   항목은 **자기-계상 자리 하나**여야 한다. 둘 이상이 필요해 보이면 그 이유를 `summary` 에 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **allowlist 에 「감싸기 귀찮은 것」을 넣지 마라.** 이유: 이 목록은 「감쌀 수 없는 것」 전용이다.
  감쌀 수 있는데 안 감싼 것을 넣으면 이 검사기가 부채 은닉 장치가 된다.
- **`_FROZEN_CENSUS` 와 `_CENSUS_ALLOWLIST` 를 같은 것으로 합치지 마라.** 이유: 하나는 「아직 안 한 것」,
  다른 하나는 「하지 않기로 한 것」이다. 섞이면 다음 사람이 무엇이 부채인지 못 읽는다.
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축을 수정하지 마라.**
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
