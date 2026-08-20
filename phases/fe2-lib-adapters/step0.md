# Step 0: url-and-resolver

## 읽어야 할 파일

- `apps/web/src/lib/webhook-base.ts` — **대상 ⑴** (25줄)
- `apps/web/src/lib/api-base.ts` — `getWebhookBaseUrl` 이 fallback 으로 부르는 것 (66줄)
- `apps/web/src/lib/__tests__/api-base.test.ts` — ★**`vi.stubEnv` + `vi.resetModules` 관용구의
  정본이다. 이 파일을 먼저 읽고 같은 모양으로 써라**
- `apps/web/src/lib/zod-v4-resolver.ts` — **대상 ⑵** (40줄)
- `apps/web/src/features/onboarding/schemas.ts` — Zod v4 스키마 관용구 (참고)

## 배경

두 대상 다 **순수 어댑터**이고 **테스트 0건**이다. 둘은 서로 무관하지만 같은 모양의 일이라 한 lane 이다.

**⑴ `webhook-base.ts`** — 사용자에게 보여줄 웹훅 URL 을 정한다([BL-268]).
production 은 별도 도메인(`NEXT_PUBLIC_WEBHOOK_BASE_URL`), dev 는 API URL fallback + **`isDev`
배지**. 배지가 틀리면 **사용자가 dev URL 을 프로덕션 웹훅으로 등록**한다.
★이 레포는 base URL 파생에서 이미 데인 적이 있다 — **사본 5벌이 CI 를 190ms 만에 죽였다**
(`e2e/_base-url.ts` 로 파생시켜 고쳤다).

**⑵ `zod-v4-resolver.ts`** — `@hookform/resolvers/zod@3.10.0` 이 Zod v3 의 `error.errors` 를 보는데
v4 는 `error.issues` 를 던지는 호환성 이슈를 우회한다. Phase C 라이브 QA(2026-05-30)에서
**cross-field `superRefine` 이 RHF errors 에 매핑되지 않아 사용자가 아무 피드백도 못 받았다.**
그 수리를 재는 테스트가 0건이다.

## 작업

**테스트 파일 두 개**를 신설한다. 이 lane 이 소유한 파일은 그 둘뿐이다.

### ⑴ `apps/web/src/lib/__tests__/webhook-base.test.ts` (케이스 ≥6)

★**env 는 `vi.stubEnv` + `vi.resetModules()` + 동적 import 로 다뤄라** —
`api-base.test.ts` 가 쓰는 그 관용구다. `getApiBase` 는 모듈 스코프 경고 플래그를 갖고 있어
정적 import 로는 케이스가 서로 오염된다.

1. **explicit env 우선** — `NEXT_PUBLIC_WEBHOOK_BASE_URL=https://hooks.quantbridge.app` ⇒
   `{ url: "https://hooks.quantbridge.app", isDev: false }`. ★`NEXT_PUBLIC_API_URL` 을 **함께 주고도**
   explicit 이 이긴다는 것을 재라
2. **trailing slash strip** — `https://hooks.x.app///` ⇒ `https://hooks.x.app`
3. ★**공백만인 값은 explicit 이 아니다** — `"   "` 이면 **fallback 경로**로 간다
   (`trim().length > 0` 계약). 빈 문자열도 같다
4. ★**`isDev` 3분기를 각각 재라** — fallback 일 때
   ⑴ `http://localhost:8000` → `isDev: true`
   ⑵ `http://127.0.0.1:8000` → `isDev: true`
   ⑶ `http://api.example.com`(원격이지만 평문) → **`isDev: true`** — `startsWith("http://")` 계약이다
5. ★★**음성 대조 — https 원격은 dev 가 아니다** — `NEXT_PUBLIC_API_URL=https://api.quantbridge.app`
   ⇒ `{ url: "https://api.quantbridge.app", isDev: false }`.
   **이 케이스가 없으면 「항상 isDev=true」인 구현도 통과한다**
6. ★**env 가 아예 없을 때** — 둘 다 미설정이면 `getApiBase()` 의 fallback(`http://localhost:8000`)을
   타고 `isDev: true`. ★**fallback URL 문자열을 이 테스트에 하드코딩하지 말고**
   `getApiBase()` 를 함께 import 해 **그 반환값과 같은지**로 재라(사본을 만들지 않는다)

### ⑵ `apps/web/src/lib/__tests__/zod-v4-resolver.test.ts` (케이스 ≥6)

`zodV4Resolver(schema)` 가 낸 resolver 를 **직접 부른다**(`resolver(values, undefined, {} as never)`).
react-hook-form 을 렌더하지 마라 — 이 lane 은 순수 어댑터만 잰다.

1. **성공** — 스키마를 만족하는 값 ⇒ `{ values: <parsed>, errors: {} }`.
   ★`values` 가 **파싱 결과**(변환·기본값 적용본)인지 재라 — 입력 그대로가 아니다
2. **실패 — flat key 매핑** — `z.object({ email: z.email() })` 에 `"nope"` ⇒
   `values` 가 `{}` 이고 `errors.email` 이 `{ type: <code>, message: <문자열> }`
3. ★**중첩 path 는 점으로 join 된다** — `z.object({ a: z.object({ b: z.string() }) })` ⇒
   키가 **`"a.b"`**(`issue.path.join(".")` 계약)
4. ★★**같은 path 는 첫 issue 가 이긴다** — 한 필드에 issue 가 2개 붙는 스키마를 만들고
   (예: `z.string().min(5).regex(/^\d+$/)` 에 `"ab"`), `errors[path]` 의 `message` 가
   **첫 issue 의 것**임을 단언한다(`if (!errors[path])` 계약). ★issue 가 실제로 2개인지도
   `schema.safeParse(...)` 로 함께 확인해라 — 1개면 이 케이스는 아무것도 안 잰다
5. ★★**`superRefine` custom issue 가 매핑된다** — cross-field 검증
   (`.superRefine((v, ctx) => ctx.addIssue({ code: "custom", path: ["confirm"], message: "…" }))`)
   에서 `errors.confirm` 이 나온다. **이것이 이 파일이 존재하는 이유다** — 2026-05-30 라이브 QA 에서
   사용자가 무피드백을 받은 그 경로다
6. ★**음성 대조 — 성공 시 errors 가 비어 있다** — `Object.keys(errors).length === 0`.
   그리고 실패 시 `values` 가 `{}` 다. 두 방향을 다 재야 「항상 실패」 구현이 걸린다
7. ★**비동기 스키마도 받는다** — `.refine(async () => false)` 가 붙은 스키마로도 resolver 가
   resolve 되고 errors 가 채워진다(`safeParseAsync` 계약)

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/webhook-base.test.ts src/lib/__tests__/zod-v4-resolver.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/webhook-base.test.ts 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/zod-v4-resolver.test.ts 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && pnpm exec eslint src/lib/__tests__/webhook-base.test.ts src/lib/__tests__/zod-v4-resolver.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★2·3번 AC 는 **파일별 양성 대조**다. 한 파일에 몰아 쓰면 다른 파일이 비어도 통과하므로 갈라 뒀다.
착수 시점 두 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 파일별 케이스 수와 **⑵-4 에서 실제로 issue 가 2개였는지**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/webhook-base.ts` · `api-base.ts` · `zod-v4-resolver.ts` 를 **수정하지 마라.**
  결함은 `summary` 한 줄로
- ★**`src/lib/__tests__/api-base.test.ts` 를 고치지 마라** — 이미 9 케이스로 커버돼 있고
  이 lane 의 소유가 아니다
- ★**`vi.stubEnv` 를 쓴 뒤 `vi.unstubAllEnvs()` 로 되돌려라** — 전역 env 오염이 다른 테스트
  파일까지 번진다(같은 vitest 프로세스를 공유한다)
- ★**react-hook-form 을 렌더하지 마라** — 순수 어댑터만 잰다. 컴포넌트 렌더는 다른 축이다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 두 테스트 파일이 각자 자기 헬퍼를 갖는다.
  이 lane 안에서도 마찬가지다(파일을 셋으로 늘리지 마라)
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
