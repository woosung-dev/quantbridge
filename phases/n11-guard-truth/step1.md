# Step 1: `live-smoke.yml` 이 이름이 약속한 것을 재게 하거나, 이름을 사실로 바꾼다

## 읽어야 할 파일

- `.github/workflows/live-smoke.yml` — 전문(70줄 남짓)
- `apps/web/playwright.config.ts` — `chromium-live-smoke` project 정의(132행 근처)
- `apps/web/e2e/live-smoke.spec.ts` — 그 project 가 실제로 돌리는 spec
- `apps/api/tests/scripts/test_ledger_vitals.py` — `tests/scripts/` 관용구

## 배경 — 실측된 불일치

워크플로우의 이름은 **`Live Dev Smoke (frontend hooks diff)`** 이고 헤더 주석은
「frontend hooks/chart/widget 변경 PR 은 본 워크플로우 PASS 의무」라고 적는다.

실제로는 이렇다(2026-08-24 실측):

- **hooks 판별식이 0줄이다** — 발화 조건은 `paths` glob(`apps/web/src/**/*.ts(x)`, `*.css`,
  `package.json`, `pnpm-lock.yaml`)뿐이다. hooks 를 안 건드린 PR 도 걸리고, 그 이름이 약속하는
  「hooks diff」라는 판별은 어디에도 없다
- 재는 것은 **공개 라우트의 `console.error`** 다. authed 훅은 **0회** 돈다
- **required check 가 아니다**
- base 가 `feat/**` 이면 트리거조차 안 걸린다(`branches: [main, "stage/**"]`)

★**이 워크플로우는 쓸모없지 않다** — 공개 라우트 런타임 크래시를 잡는 일은 실제로 한다.
문제는 **이름과 주석이 다른 것을 약속한다**는 것이다. 다음 회차가 그 문장을 믿고
「hooks 는 CI 가 막아 준다」로 읽는다. 이 레포는 「lint 가 막아 준다」가 거짓이던 문서 5곳을
이미 겪었다.

## 작업

### ⑴ 이름과 주석을 실태에 맞춘다

- `name:` 을 **실제 측정 대상**이 드러나게 고쳐라(공개 라우트 런타임 콘솔 오류 스모크).
  「hooks diff」를 이름에 남기지 마라 — 그 판별이 없다
- 헤더 주석에서 **거짓인 절만** 고쳐라. 배경(BL-157 · LESSON-004 회귀 서사)은 참이므로 **보존**한다.
  ★ 「종전에는 …라고 적혀 있었다」 류 정정 서사를 파일에 쓰지 마라 — 그것이 문서를 다시 살찌운다.
  **참인 문장만 남기고** 서사는 커밋 메시지가 갖는다
- 주석에 **지금 무엇을 안 재는지**를 1~2줄로 명시해라: authed 훅 0회 · required check 아님 ·
  hooks 판별식 없음(발화는 경로 glob)

### ⑵ 그 정합을 기계로 고정한다

`apps/api/tests/scripts/test_live_smoke_workflow.py` 를 신설한다.
**테스트 이름에 `live_smoke_workflow` 를 포함시켜라**(AC 가 `-k live_smoke_workflow` 로 잡는다).
YAML 파싱은 `uv run` 환경의 `yaml` 로 한다(시스템 `python3` 에는 **`yaml` 이 없다** — 2026-08-25 실측).

테스트 3건 이상:

1. `test_live_smoke_workflow_name_does_not_claim_an_absent_hooks_predicate`
   `name` 과 헤더 주석에 「hooks diff」류 약속 문자열이 **없다**.
   ★**양성 대조 동반** — 같은 검사 함수에 그 문자열을 담은 **합성 문자열**을 넣으면 위반으로
   잡히는지 단언해라(실파일이 통과한다는 것만으로는 검사기가 살아 있는지 모른다)
2. `test_live_smoke_workflow_triggers_on_main_and_stage_only`
   `on.pull_request.branches` 가 `[main, "stage/**"]` 임을 단언한다.
   ★이것은 **문서화된 함정의 고정**이다 — base 가 `feat/**` 이면 CI 가 아예 안 돈다
3. `test_live_smoke_workflow_runs_the_declared_playwright_project`
   실행 스텝의 `--project=` 값이 `playwright.config.ts` 에 **실재하는 project 이름**임을 단언한다
   (설정 파일에서 project 이름 목록을 읽어 대조 — 문자열 하드코딩 금지)

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/scripts -k live_smoke_workflow -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/scripts -k live_smoke_workflow --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/scripts -q
cd apps/api && uv run ruff check tests/scripts
```

세 번째는 **무회귀**다 — step 0 이 만든 것과 기존 30여 파일이 함께 돈다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **YAML 이 여전히 유효한지 확인해라** — 이름·주석만 고쳤어도 파싱이 깨지면 CI 가 통째로 죽는다.
   `uv run python -c "import yaml; yaml.safe_load(open(...))"` 로 확인한다.
3. `git diff .github/workflows/live-smoke.yml` 로 **`steps`·`env`·`paths` 가 안 바뀌었는지** 확인해라.
   이 step 은 **동작을 바꾸지 않는다.**
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **워크플로우를 삭제하지 마라.** 이유: 삭제는 CI 표면 결정이라 사용자 소관이다.
  이 step 의 범위는 **이름·주석을 사실로 만드는 것**이다.
- **`steps` · `env` · `paths` · `on` 을 바꾸지 마라**(단언은 하되 수정은 금지).
  이유: 동작 변경은 이름 정합과 다른 결정이고, 한 커밋에 섞이면 나중에 못 가른다.
- **`ci.yml` 을 만지지 마라.** 이유: 유일한 품질 게이트다. 잡 추가·수정은 [ADR-037] 재입힘 규칙 대상이다.
- **hooks 판별식을 새로 구현하지 마라.** 이유: 그것은 게이트 기능 추가이고 이 lane 의 범위 밖이다.
  필요하면 `summary` 에 제안으로 남겨라.
- **`tests/common/**` · `tests/trading/**` · `src/**` 를 만지지 마라.**
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
