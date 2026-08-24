# Step 2: fill-env-example — 누락 4건을 견본에 등재한다

## 읽어야 할 파일

- **`phases/n8-common.md`**
- `apps/api/.env.example` — 기존 줄의 **주석 형식·그룹 배치**를 그대로 따른다
- `apps/api/src/core/config.py` — 각 필드의 기본값·설명
- `apps/api/tests/common/test_env_example_contract.py` — Step 0·1 산출

## 작업

Step 0 이 동결한 `_FROZEN_MISSING_FROM_EXAMPLE` 의 키를 `.env.example` 에 **실제로 추가**하고,
동결 집합을 **빈 집합으로 갱신**한다.

각 줄은 기존 관용구를 따른다 — `KEY=<기본값>` + 우측 정렬 주석에 `[기본값 OK]` / `[필수 ...]`
표기. 형식은 `apps/api/.env.example:146`(`TRUSTED_PROXIES=`) 과 `:173`(`WAITLIST_ADMIN_EMAILS=`)
을 보고 맞춰라.

### 값 채우기 규칙 — 벗어나면 안 되는 계약

- **실제 시크릿을 넣지 마라.** 이 파일은 견본이다. 히스토리에 실제 키가 들어간 적이 **2회** 있다.
- **`config.py` 의 기본값과 어긋나는 값을 쓰지 마라.** 견본의 값이 기본값과 다르면 그 자체가
  다음 사고의 씨앗이다. 기본값이 있으면 그 값을, 없으면 빈 값을 쓴다.
- `E2E_RATE_LIMIT_EXEMPT_EMAIL` 은 **production 에서 설정되면 안 되는 값**이다
  (`config.py:440-443` 이 검증한다). 주석에 그 사실을 한 줄로 적어라.

### 동결 집합 갱신

`_FROZEN_MISSING_FROM_EXAMPLE` 를 빈 집합(`frozenset()`)으로 바꾼다. 그러면 Step 1 의
방향 ⑴ 가드가 **앞으로 새 누락을 잡는다.**

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/common/test_env_example_contract.py -q
test "$(grep -c '^E2E_RATE_LIMIT_EXEMPT_EMAIL=' apps/api/.env.example)" -eq 1
test "$(grep -c '^OPTIMIZER_STALE_THRESHOLD_SECONDS=' apps/api/.env.example)" -eq 1
test "$(grep -c '^STRESS_TEST_STALE_THRESHOLD_SECONDS=' apps/api/.env.example)" -eq 1
test "$(grep -c '^DOGFOOD_REPORT_OUTPUT_DIR=' apps/api/.env.example)" -eq 1
cd apps/api && uv run --env-file .env.local pytest tests/common -q
git diff --quiet -- apps/api/src
```

★**AC 의 4개 키 이름은 CONTROL 의 사전 실측이다.** Step 0 의 실측이 다른 집합을 냈다면
**AC 가 틀린 것**이므로 `status:"blocked"` 로 멈추고 `blocked_reason` 에 실측 집합을 적어라.
임의로 키를 만들어 AC 를 통과시키지 마라.

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. `.env.example` 에 **실제 값처럼 보이는 문자열**이 들어가지 않았는지 눈으로 확인한다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **`config.py` 를 수정하지 마라.** 이유: 견본을 코드에 맞추는 것이지 반대가 아니다. AC 가 집행한다.
- **실제 시크릿·토큰·키를 넣지 마라.** 이유: 히스토리에 실제 키가 들어간 사고가 2회 있다.
- **동결 집합을 지우지 말고 빈 집합으로 바꿔라.** 이유: 상수가 사라지면 방향 ⑴ 가드도 함께 죽는다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
