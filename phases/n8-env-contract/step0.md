# Step 0: env-census — Settings ↔ `.env.example` 대조기를 만든다

## 읽어야 할 파일

- **`phases/n8-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- `apps/api/src/core/config.py` — Pydantic Settings 정본
- `apps/api/.env.example` — 설정 견본 정본
- `apps/api/tests/common/test_metric_guard_census.py` — **census + 동결 래칫의 레포 관용구.** 형식을 여기서 배워라

## 배경 — 왜 이 축인가

루트 `AGENTS.md` §3 NEVER: 「`.env.example` 에 없는 환경 변수를 코드에서 참조하지 마라.
**이유:** 배포 호스트가 그 값을 안 넣어 조용히 다르게 동작한다(2026-08-15 `/docs` 인터넷 노출
실사고)」. 이 규칙에 **기계 집행이 없다.**

## 작업

`apps/api/tests/common/test_env_example_contract.py` 를 **새로** 만든다.

이 step 은 **대조기만** 만든다. 위반을 고치지 않는다(고치는 것은 step 2).

### 반드시 `ast` 로 파싱해라 — 문자열 검색 금지

`config.py` 를 `ast.parse` 하고 `ClassDef` 안의 `AnnAssign` 으로 Settings 필드를 뽑아라.

★**alias 를 반드시 해소해라.** CONTROL 실측: `trusted_proxies_raw` 는
`Field(alias="trusted_proxies")` 를 갖고 `.env.example` 에는 `TRUSTED_PROXIES` 로 있다.
**필드 이름만 대조하면 위양성 2건이 난다.** 필드의 유효 env 키 =
`alias` 가 있으면 `alias.upper()`, 없으면 `필드명.upper()` 다.

### 이 step 이 남겨야 할 테스트 (2개 이상)

1. **양성 대조** — 파싱한 Settings 필드가 **35개 이상**이고, `.env.example` 에서 읽은 키가
   **45개 이상**이다. (둘 중 하나가 0이면 파서가 죽은 것이고, 그때 부재 단언은 항진명제가 된다.)
2. **census 고정** — 「Settings 에는 있는데 `.env.example` 에 없는 유효 env 키」 집합을
   모듈 상수 `_FROZEN_MISSING_FROM_EXAMPLE` 로 **동결**하고, 실측 집합이 그것과 같은지 단언한다.

★**동결 집합의 값은 네가 실측해서 채워라.** CONTROL 의 사전 실측은 alias 해소 전 6건이었고
해소 후 **4건**으로 줄었다(`E2E_RATE_LIMIT_EXEMPT_EMAIL` · `OPTIMIZER_STALE_THRESHOLD_SECONDS` ·
`STRESS_TEST_STALE_THRESHOLD_SECONDS` · `DOGFOOD_REPORT_OUTPUT_DIR`). **이 숫자를 믿지 말고
다시 재라.** 실측이 다르면 `summary` 에 차이를 적어라.

## Acceptance Criteria

```bash
test -f apps/api/tests/common/test_env_example_contract.py
cd apps/api && uv run --env-file .env.local pytest tests/common/test_env_example_contract.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_env_example_contract.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 2
git diff --quiet -- apps/api/src
git diff --quiet -- apps/api/.env.example
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **파서가 실제로 닿았는지 증명해라** — 필드 수·키 수 하한 단언이 그 증명이다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`config.py` 를 수정하지 마라.** 이유: 이 step 은 대조기만 만든다. AC 가 `git diff --quiet -- apps/api/src` 로 집행한다.
- **`.env.example` 을 수정하지 마라.** 이유: 같다. step 2 의 일이다.
- **문자열 `grep` 으로 필드를 뽑지 마라.** 이유: alias·주석·여러 줄 `Field(...)` 에서 조용히 틀린다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
