# Step 3: mutation-selfcheck — 가드가 실제로 잡는지 증명한다

## 읽어야 할 파일

- **`phases/n8-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- `apps/api/tests/common/test_env_example_contract.py` — Step 0~2 산출
- `apps/api/src/core/config.py` · `apps/api/.env.example`

## 작업

가드의 **판별력**을 변이로 증명하고, 그 증명을 테스트로 남긴다.

### 변이 2종 — 심고, red 를 확인하고, 반드시 복원한다

- **변이 ⑴ 누락 방향** — `config.py` 에 새 Settings 필드를 하나 추가한다
  (예: `n8_mutation_probe: str = Field(default="")`). 가드가 **red** 여야 한다.
- **변이 ⑵ 사문 방향** — `.env.example` 에서 allowlist 에 없는 키 한 줄을 지운다.
  가드가 **red** 여야 한다.

★**복원은 SHA 로 확인해라.** 변이 전에 `shasum -a 256 apps/api/src/core/config.py
apps/api/.env.example` 을 찍어 두고, 복원 후 같은 명령이 **같은 해시**를 내는지 본다.
2026-08-16 에 복원 확인이 항진명제였던 사고가 있다 — 비교 대상이 자기 자신이면 언제나 통과한다.

★**변이가 red 를 못 만들면 그것은 「안 잡혔다」가 아니라 「변이가 대상에 안 닿았다」일 수 있다.**
둘을 구분해라 — 가드가 그 파일을 실제로 읽었는지(파일 수·필드 수 하한)를 먼저 확인한다.

### 이 step 이 남겨야 할 테스트 (누적 6개 이상)

5. **alias 해소 회귀** — `Field(alias=...)` 를 가진 필드의 유효 env 키가 alias 를 따른다는 것을
   `config.py` 의 실제 필드(`trusted_proxies_raw` · `waitlist_admin_emails_raw`)로 단언한다.
   이 둘이 방향 ⑴·⑵ 어디에도 안 나타나야 한다.
6. **파서 음성 대조** — Settings 가 아닌 클래스의 `AnnAssign` 이 필드로 잘못 수집되지 않는지,
   또는 주석 처리된 `.env.example` 줄(`# KEY=...`)이 키로 수집되지 않는지 중 **하나**를 단언한다.

변이 결과는 `summary` 에 적어라 — 어느 변이가 어느 테스트를 어떤 메시지로 red 로 만들었는지.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/common/test_env_example_contract.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_env_example_contract.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run --env-file .env.local pytest tests/common -q
cd apps/api && uv run ruff check tests/common/test_env_example_contract.py
cd apps/api && uv run ruff format --check tests/common/test_env_example_contract.py
git diff --quiet -- apps/api/src
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. **변이 복원을 SHA 로 확인한다.** `git diff --quiet -- apps/api/src` 가 AC 에 있는 이유가 이것이다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **변이를 커밋에 남기지 마라.** 이유: AC 의 `git diff --quiet` 가 집행한다.
- **`xfail` 을 쓰지 마라.** 이유: `xfail(strict=True)` 는 「제품 코드가 틀렸다」를 원장에 박는 주장이고,
  이 회차엔 그렇게 주장할 근거가 없다. 2026-08-21 에 phantom `xfail` 1건이 AC·변이·diff 세 층을 전부 통과했다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
