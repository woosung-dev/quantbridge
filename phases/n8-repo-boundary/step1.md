# Step 1: guard-and-frozen-census — 동결 래칫으로 가드를 세운다

## 읽어야 할 파일

- **`phases/n8-common.md`**
- `apps/api/tests/common/test_repository_boundary_guard.py` — Step 0 산출. 여기에 **추가**한다
- `apps/api/tests/common/test_metric_guard_census.py` — 동결 래칫 형식의 정본

## 작업

Step 0 의 census 를 **래칫(ratchet)** 으로 바꾼다. 파일은 같은 파일이다.

### 동결 상수

Step 0 이 실측한 위반 목록을 `_FROZEN_VIOLATIONS` 로 동결한다. 원소는
`(파일경로, 함수명, 대략 줄번호가 아니라 안정적인 식별자)` 형태가 좋다 —
★**줄번호를 키로 쓰지 마라.** step 2·3 이 코드를 옮기면 줄번호가 밀려 가드가
「고쳤는데 red」가 된다. 파일 + 함수명으로 식별해라.

### 래칫의 두 방향

- **새 위반 금지** — 실측 집합 ⊄ `_FROZEN_VIOLATIONS` 이면 red.
- **죽은 동결 금지** — `_FROZEN_VIOLATIONS` 의 원소 중 실측에 없는 것이 있으면 red.
  ★이것이 step 2·3 을 **강제**하는 장치다: 위반을 고치면 동결 목록도 함께 줄여야 green 이 된다.

### 이 step 이 남겨야 할 테스트 (누적 4개 이상)

3. **래칫 ⑴** — 실측 위반이 동결 집합의 부분집합이다.
4. **래칫 ⑵** — 동결 집합의 모든 원소가 실측에 실재한다(죽은 동결 0).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
cd apps/api && uv run --env-file .env.local pytest tests/common -q
git diff --quiet -- apps/api/src
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. 동결 원소의 식별자에 **줄번호가 없는지** 확인한다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **`apps/api/src` 를 수정하지 마라.** 이유: 이 step 은 가드만 세운다. AC 가 집행한다.
- **동결 집합을 「전부 허용」으로 쓰지 마라.** 이유: 그러면 래칫이 아니라 면제가 된다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
