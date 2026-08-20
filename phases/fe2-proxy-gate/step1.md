# Step 1: session-redirect

## 읽어야 할 파일

- `apps/web/src/proxy.ts` — 대상. 이번엔 **후반부**(세션 완전 검증 · `/` UX 리다이렉트)
- `apps/web/src/__tests__/proxy-gate.test.ts` — step 0 이 만든 파일. **여기에 이어 쓴다**

## 배경

step 0 은 「어떤 경로가 공개인가」를 고정했다. 이 step 은 **공개가 아닐 때 무슨 일이 일어나는가**와
**두 종류의 세션 검사가 갈리는 지점**을 고정한다.

★**이 파일의 핵심 설계는 세션 검사가 두 가지라는 것이다** — 주석이 그 이유를 적고 있다:

- **보호 라우트** = `auth.api.getSession()` (**DB 까지 완전 검증**). 주석이 `getSessionCookie` 를
  두고 「공식 문서가 "THIS IS NOT SECURE!" 라고 명시한다」며 **인증 게이트로 쓰지 않는다**고 못박았다
- **`/` 의 authed 리다이렉트** = `getSessionCookie` (**쿠키 존재만**). 「보안 게이트가 아니라 UX
  리다이렉트」이고 「공개 라우트에서 DB 를 안 치는 것이 목적」이라 일부러 빠른 판을 쓴다

**둘이 뒤바뀌면 인증 경계가 무너진다**(위조 쿠키로 보호 라우트 통과). 지금 아무 테스트도 이
비대칭을 재지 않는다. 이 step 이 그것을 잰다.

## 작업

`apps/web/src/__tests__/proxy-gate.test.ts` 에 케이스를 **추가**한다(새 파일을 만들지 마라).

### 최소한 이 여섯을 더 덮어라 (파일 전체 케이스 ≥15)

1. **보호 라우트 + 세션 없음 → `/sign-in`** — `getSession` 이 `null` 을 내면 status 307 ·
   `location` 의 pathname 이 `/sign-in`
2. ★**`redirect_url` 이 원래 경로 + 쿼리를 보존한다** — `/backtests/abc?tab=trades` 로 치면
   `location` 의 `redirect_url` 이 정확히 `/backtests/abc?tab=trades`.
   ★**`url.search = ""` 로 기존 쿼리를 비운 뒤 넣는다**는 것도 함께 재라 — `/sign-in` 쪽 쿼리에
   원 요청의 파라미터가 **새어 들어가면 안 된다**(`location.searchParams` 의 키가 `redirect_url` 하나)
3. **보호 라우트 + 세션 있음 → 통과** — `getSession` 이 `{ user: { id: "u1" } }` 를 내면
   리다이렉트 없음(status 200)
4. ★★**보호 라우트는 `getSessionCookie` 를 쓰지 않는다** — 세션 없음 케이스에서
   **`expect(getSessionCookie).not.toHaveBeenCalled()`**. 이것이 「쿠키 존재만 보는 판을 인증
   게이트로 쓰지 않는다」는 계약이고, 뒤집히면 **위조 쿠키로 보호 라우트가 뚫린다**
5. **`/` + 쿠키 있음 → `/strategies`** — `getSessionCookie` 가 truthy 를 내면 307 ·
   pathname `/strategies`. ★그리고 **`getSession` 은 불리지 않는다**(공개 라우트에서 DB 를 안 친다)
6. ★**음성 대조 — `/` + 쿠키 없음 → 리다이렉트 없음** · **`/pricing` + 쿠키 있음 → 리다이렉트
   없음**(이 UX 리다이렉트는 **`/` 에서만** 발화한다. 모든 공개 라우트로 퍼지면 안 된다)

★**`beforeEach` 에서 두 mock 을 `mockReset()` 해라** — 호출 횟수 단언이 앞 케이스에 오염된다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/__tests__/proxy-gate.test.ts
cd apps/web && test "$(pnpm exec vitest list src/__tests__/proxy-gate.test.ts 2>/dev/null | grep -c ' > ')" -ge 15
cd apps/web && pnpm exec eslint src/__tests__/proxy-gate.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 최종 케이스 수와 **덮지 못한 분기**(있다면)를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/proxy.ts` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- step 0 이 만든 케이스를 **지우거나 약화시키지 마라.** 케이스 수는 단조 증가여야 한다
- 새 테스트 파일을 만들지 마라 — 이 lane 이 소유한 파일은 `src/__tests__/proxy-gate.test.ts` 하나다
- 커밋하지 마라(커밋은 러너 소관)
