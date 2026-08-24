# Step 1: contract-guard-and-allowlist — 양방향 가드 + 허용목록

## 읽어야 할 파일

- **`phases/n8-common.md`**
- `apps/api/tests/common/test_env_example_contract.py` — Step 0 산출. 여기에 **추가**한다
- `apps/api/.env.example`
- `apps/api/src/core/config.py`

## 작업

Step 0 의 대조기를 **양방향 가드**로 키운다. 파일은 같은 파일이다.

### 방향 ⑴ — Settings → `.env.example` (누락 탐지)

Step 0 의 `_FROZEN_MISSING_FROM_EXAMPLE` 를 그대로 쓴다. 이 방향이 실사고 축이다.

### 방향 ⑵ — `.env.example` → Settings (사문 탐지)

`.env.example` 에는 있는데 Settings 에 없는 키는 **테스트·툴링 전용**이다.
CONTROL 실측 13건: `BYBIT_DEMO_API_KEY_TEST` · `BYBIT_DEMO_API_SECRET_TEST` · `BYBIT_DEMO_KEY` ·
`BYBIT_DEMO_SECRET` · `BYBIT_SMOKE_API_KEY` · `BYBIT_SMOKE_API_SECRET` · `PINE_ALERT_HEURISTIC_MODE` ·
`PROMETHEUS_MULTIPROC_DIR` · `QB_METRICS_ROLE` · `TEST_DATABASE_URL` · `TEST_REDIS_LOCK_URL` ·
`TRUSTED_PROXIES` · `WAITLIST_ADMIN_EMAILS`.

★**이 목록을 그대로 베끼지 마라.** `TRUSTED_PROXIES` 와 `WAITLIST_ADMIN_EMAILS` 는
**alias 라서 Settings 에 있는 것**이다 — Step 0 의 alias 해소가 옳다면 이 둘은 방향 ⑵ 에
**나타나지 않아야 한다.** 나타난다면 Step 0 의 alias 해소가 틀린 것이니 그것을 먼저 고쳐라.
나머지를 `_ALLOWLIST_NON_SETTINGS` 상수로 동결한다.

### 이 step 이 남겨야 할 테스트 (누적 4개 이상)

3. **방향 ⑵ 가드** — 실측한 「Settings 에 없는 `.env.example` 키」가 `_ALLOWLIST_NON_SETTINGS`
   와 정확히 같다.
4. **allowlist 제어군** — `_ALLOWLIST_NON_SETTINGS` 의 원소가 **모두 실제로 `.env.example` 에
   존재한다.** (죽은 allowlist 항목이 남으면 가드가 조용히 헐거워진다.)

## Acceptance Criteria

```bash
test -f apps/api/tests/common/test_env_example_contract.py
cd apps/api && uv run --env-file .env.local pytest tests/common/test_env_example_contract.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_env_example_contract.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
cd apps/api && uv run --env-file .env.local pytest tests/common -q
git diff --quiet -- apps/api/src
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. `tests/common` 전체가 green 인지 본다 — 이 파일이 다른 census 테스트를 깨뜨리지 않아야 한다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **`.env.example` 과 `config.py` 를 수정하지 마라.** 이유: 이 step 은 가드만 세운다. AC 가 집행한다.
- **allowlist 로 방향 ⑴ 을 덮지 마라.** 이유: 누락 4건은 step 2 에서 **고치는** 것이지 면제하는 것이 아니다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
