# Step 2: 범위 판정을 결론으로 바꾼다 — 수리하거나, census 를 규칙 범위로 좁힌다

## 읽어야 할 파일

- step 0 · step 1 의 `summary` — in-scope 목록과 해로운 자리 목록이 이 step 의 입력이다
- `apps/api/tests/common/test_metric_guard_census.py`
- `apps/api/src/common/metrics_multiproc.py` — 정답 형태 2종(`_count_safely` · `lambda` 지연 평가)
- `apps/api/AGENTS.md` §4 — 규칙 원문

## 작업 — 갈래가 둘이다. step 0 의 측정이 갈래를 정한다

### 갈래 ⓐ — in-scope 위반이 1건 이상이다

그 자리들을 감싸라. 정답 형태는 둘뿐이다:

```python
_count_safely(qb_x, reason="y")                                    # 라벨+증가를 함께 격리 (권장)
record_metric_safely(lambda: qb_x.labels(reason="y").observe(v))   # 지연 평가
```

★**`record_metric_safely(qb_x.labels(...).inc)` 로 쓰지 마라.** 이유: 인자가 **먼저 평가**되므로
`.labels()` 가 가드 **밖**에서 돈다(멀티프로세스 모드에서 새 라벨 조합은 그 시점에 mmap 을 늘린다).
이 형태는 `tests/common/test_labels_outside_guard.py` 가 이미 red 로 잡는다.

수리 후:
- `_FROZEN_CENSUS` 와 `_FROZEN_CENSUS_SCOPE` 를 **실측으로 갱신**한다(감소한 항목은 **삭제** —
  0 으로 낮추면 정확 동등 비교가 여전히 red 다. 실패 메시지가 그렇게 지시한다)
- **metric 을 삭제해서 수치를 줄이지 마라.** 제거·추가 1:1 대조를 `summary` 에 적어라

### 갈래 ⓑ — in-scope 위반이 0건이다

이때 [BL-520] 은 **닫힐 자격이 있다.** 다만 「범위 밖 30건」을 그냥 두면 다음 회차가 또
같은 것을 센다. 다음을 해라:

- `_FROZEN_CENSUS` 위 주석에 **이 집합은 규칙 범위(결과 보고 `try` 본문)의 상위집합이며
  규칙 위반 건수가 아니다** 를 명시한다(2~4줄. 서사 금지 — 참인 문장만)
- 범위 판정 축(step 0)이 그것을 기계로 지킨다는 것을 그 주석이 가리키게 한다

★**어느 갈래든 `summary` 에 「BL-520 판정 = RESOLVED 후보 / 수리 완료」 중 하나를 명시해라.**
원장 문장은 CONTROL 이 쓴다 — 너는 근거만 넘긴다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/tasks -q
cd apps/api && uv run ruff check src tests/common
```

두 번째는 **회귀 방어**다 — `src/tasks/**` 가 census 상위 파일이라 수리가 그쪽 동작을 깨뜨렸는지 본다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. 갈래 ⓐ 였다면 **감싼 자리마다 변이를 심어 red 를 확인**해라(가드를 임시로 풀고 census 가
   red 가 되는지). 원복은 스냅샷 되쓰기로 하고 `git diff --stat` 으로 확인한다.
3. 갈래 ⓑ 였다면 **주석이 참인지** 다시 대조해라 — 「범위 밖」이라 적은 근거가 step 0 의
   양성 대조를 통과한 측정인지 확인한다.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **metric 을 삭제해 census 수치를 줄이지 마라.** 이유: 관측을 잃고 수치만 좋아지는 것이
  이 축에서 가장 나쁜 결과다.
- **`docs/backlog.md` 에 판정을 쓰지 마라.** 이유: 원장은 CONTROL 소관이고 단일 파일이라 충돌한다.
- **celery 경유 검증을 하지 마라**(백테스트·라이브신호·옵티마이저 실행). 이유: worker 컨테이너가
  **메인의 `apps/api/src`** 를 mount 하므로 워크트리에서는 **내 코드가 아니라 메인 코드가 돈다** — 침묵 실패다.
- **`mise run up`/`down`/`migrate`/`seed` 를 하지 마라.** 이유: 컨테이너·앱 DB 는 1벌 공유다.
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- **`tests/trading/**` · `tests/scripts/**` 를 만지지 마라.** 이유: 다른 lane 의 소유 구역이다.
- 커밋하지 마라(커밋은 러너 소관).
