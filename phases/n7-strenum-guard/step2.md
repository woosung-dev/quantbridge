# Step 2: 변이 자기검사 — 이 가드가 **실제로 잡는지** 증명한다

## 읽어야 할 파일

- **`phases/n7-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- Step 0·1 이 만든 `apps/api/tests/trading/test_no_strenum_value_access.py`

## 왜 이 step 이 있나

지금 위반은 **0건**이다. 그래서 이 가드는 **초록인 채로 아무것도 안 할 수 있다.**
이 레포는 그 병을 반복해 겪었다 — 「검사기가 빈 입력을 원하는 답으로 통과」시킨 사고가
여러 회차에 걸쳐 있었고, 「변이 N/N red」를 판별력 증거로 잘못 쓴 적도 있다.

**이 step 의 산출은 코드가 아니라 증거다.**

## 작업

1. **변이를 실제로 심어라.** 스코프 안(`apps/api/src/trading/` 또는 `src/tasks/`)의 아무 파일에
   파생 필드 중 하나에 대한 `.value` 접근을 **한 줄 추가**한다.
   예: `ExchangeExit` 행을 다루는 코드에 `_ = row.classification.value`
2. **가드가 red 가 되는지 확인한다.** red 여야 한다.
3. ★**그 변이가 대상에 도달했는지 따로 확인해라.** 스캐너가 그 파일을 실제로 훑었는지
   확인해라 — 도달 못 한 변이의 red 0 은 **무증거**다.
4. **복원한다.** ★`git checkout` **금지** — 커밋 안 된 편집을 같이 날린다.
   **변이 전 스냅샷을 따로 떠 두고 되쓴 뒤 `sha256` 으로 왕복 대조**해라.
5. **음성 대조도 해라** — allowlist 에 있는 자리(`entry_completeness.py` 의 `.channel.value`)와
   스코프 밖(`backtest/service.py` 의 `.status.value`)은 **red 가 되면 안 된다.**
   양성만 재고 음성을 안 재면 「전부 잡는 가드」와 구별이 안 된다.
6. 케이스를 하나 더 추가해 최소 6케이스로 만든다 — **스캐너 자체를 합성 픽스처로 검사**하는
   케이스가 좋다(`test_metric_guard_census.py:360` 의
   `test_census_rule_classifies_the_synthetic_fixture` 가 정본 관용구다).
   ★합성 픽스처는 **실제 소스를 안 건드리고** 판별력을 상시 고정한다 — 변이는 1회성이지만
   이 케이스는 남는다.

## Acceptance Criteria

1. `test -f apps/api/tests/trading/test_no_strenum_value_access.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/trading/test_no_strenum_value_access.py -q`
3. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/trading/test_no_strenum_value_access.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6`
4. `cd apps/api && uv run --env-file .env.local pytest tests/trading -q`
5. `cd apps/api && uv run ruff check tests/trading/test_no_strenum_value_access.py`
6. `cd apps/api && uv run ruff format --check tests/trading/test_no_strenum_value_access.py`
7. `git diff --quiet -- apps/api/src`

★**AC 7 이 변이 복원의 증인이다.** 변이를 심은 채로 두면 이 AC 가 red 다.

## `summary` 에 반드시 담을 것

- **양성**: 어디에 무엇을 심었고, 가드가 어떤 메시지로 red 였는지 (메시지 원문)
- **도달 확인**: 스캐너가 그 파일을 훑었다는 근거
- **음성**: allowlist 자리와 스코프 밖이 red 가 **아니었다**는 확인
- 복원 sha256 왕복 대조 결과
- 합성 픽스처 케이스가 무엇을 고정하는지

## 금지사항

- **변이를 심은 채로 끝내지 마라** (AC 7 이 잡는다).
- **`git checkout` 으로 복원하지 마라.** 이유: 커밋 안 된 편집을 같이 날린다. 스냅샷 되쓰기.
- **「red 가 났으니 됐다」로 끝내지 마라.** 변이가 **대상에 도달했는지**를 따로 확인해야 한다.
  도달 못 한 변이의 red 는 다른 이유로 난 red 일 수 있다.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
