# Step 2: FE 제품 결정 표면 가드의 기록된 사각 — 런타임 문자열과 리소스

## 읽어야 할 파일

- `apps/web/src/lib/__tests__/decision-surface-guard.test.ts` — 가드 본체(90줄).
  `DECISION_SURFACE_PATHS`(10파일) · `FORBIDDEN_ACCOUNT_MODE` · `FORBIDDEN_OUT_OF_SCOPE_EXCHANGE`
- `docs/PRD.md` §0 — **제품 결정 3건**(읽기만. 수정 금지). 이 가드가 지키는 대상이다

## 배경

n7 이 lane→CONTROL 인계로 남긴 기록: **FE decision-surface 가드는 이미지·번역 리소스·런타임 응답
문자열을 못 잡는다.** 지금 가드는 `DECISION_SURFACE_PATHS` 에 **손으로 적은 10개 소스 파일**만
`readFileSync` 로 읽어 금지 문자열을 찾는다.

따라서 새 화면 파일이 같은 문구를 담아도, 그 파일이 목록에 없으면 **조용히 통과**한다.
이것은 이 레포가 반복해 밟은 **「검사기가 보는 표면 < 실제 실패 표면」** 이다.

★가드 자신이 금지 문자열을 `["메인","넷"].join("")` 처럼 **쪼개서** 들고 있다는 점에 주의해라 —
그래야 가드 파일 자신이 자기 검사에 걸리지 않는다. 새 문자열도 같은 규율을 따라라.

## 작업

같은 파일에 축을 추가한다. **새 파일을 만들지 마라** — 이 축의 검사기가 둘이 되면 안 된다.

### ⑴ 목록 기반에서 **디렉터리 스캔**으로 넓힌다

`apps/web/src` 아래의 `.ts`/`.tsx` 를 훑어 금지 문자열 2종을 찾는 축을 추가해라.

**제외해야 하는 것**(이유를 주석으로 남겨라):
- 가드 파일 자신과 `__tests__` 디렉터리 — 금지 문자열의 **정의**가 거기 있다
- `src/app/api/**` 같이 제품 결정 표면이 아닌 곳이 있으면 판단해서 제외하되, **제외 목록은
  짧고 사유가 붙어야 한다**

### ⑵ `DECISION_SURFACE_PATHS` 는 **하한선으로 남긴다**

지우지 마라. 스캔 집합이 그 10개를 **포함하지 않으면 red** 가 되게 단언해라.
이유: 스캔이 어느 날 0파일이 되면(경로 파손·glob 오타) 「위반 0건」이 항진명제로 새는데,
그 10개가 하한선이면 그 사고를 잡는다.

### ⑶ 런타임/리소스 축은 **사각을 고정**한다

이미지 바이너리·번역 리소스·서버 응답 문자열은 정적으로 못 읽는다. 그것을 **닫으려 들지 마라.**
대신 가드 파일 상단 주석에 **무엇을 못 잡는지**를 3줄 이내로 남겨라(참인 문장만).
n7 의 인계 문장을 그대로 쓰면 된다.

### ⑷ 테스트

기존 테스트는 **그대로 둔다.** 추가:

1. `스캔 집합이 하한선 10파일을 포함한다`
2. `스캔한 파일 수가 하한선보다 크다` — ★**양성 대조.** 같지 않고 **더 커야** 스캔이 실제로 넓어진 것이다
3. `금지 문자열을 담은 합성 소스가 위반으로 잡힌다` — ★**판별력.** 실파일을 만들지 말고
   **문자열을 직접 검사 함수에 먹여라**(검사 로직을 파일 읽기와 분리해라)

## Acceptance Criteria

```bash
cd apps/web && pnpm exec vitest run src/lib/__tests__/decision-surface-guard.test.ts
cd apps/web && pnpm exec vitest run src/lib/__tests__/decision-surface-guard.test.ts --reporter=json --outputFile=/tmp/qb-decision-surface.json && node -e "const r=require('/tmp/qb-decision-surface.json');process.exit(r.numTotalTests>=6?0:1)"
cd apps/web && pnpm exec biome check src/lib/__tests__
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째가 **양성 대조**다 — 착수 전 실측 `numTotalTests = 3` 이므로 테스트를 안 늘리면 rc≠0 이다.
`vitest -t <이름>` 은 **매칭이 0건이어도 rc=0**(skip 처리)이라 대조로 못 쓴다 — 2026-08-25 실측.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **판별력을 실파일로 1회 재라** — `src` 아래 아무 컴포넌트에 금지 문구를 임시로 넣고 red 를
   확인한 뒤 **반드시 원복**해라(`git diff --stat`). 합성 문자열만으로는 스캔이 실트리에 닿는지 모른다.
3. **`rm -rf apps/web/.next` 는 하지 마라** — 이 step 은 빌드를 안 돈다. 캐시 표본은 CONTROL 이
   주행 전에 채취한다.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **이미지·번역 리소스·런타임 응답 문자열을 정적으로 잡으려 들지 마라.**
  이유: 정적 분석으로 닿지 않는 표면이다. **사각을 주석으로 고정**하는 것이 이 step 의 범위다.
- **`DECISION_SURFACE_PATHS` 를 삭제하지 마라.** 이유: 스캔이 파손됐을 때 「위반 0건」이
  항진명제로 새는 것을 막는 유일한 하한선이다.
- **제품 문구 자체를 고치지 마라**(화면 텍스트 변경). 이유: 제품 결정 표면은 사용자 소관이다.
  위반을 찾으면 `summary` 에 좌표로 남겨라.
- **`apps/api/**` 를 만지지 마라.** 이유: 다른 lane 의 소유 구역이다.
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
