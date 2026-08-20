# Step 1: delete-fail-closed

## 읽어야 할 파일

- `apps/web/src/lib/auth.ts` — 대상. 이번엔 `user.deleteUser.beforeDelete` (54~92줄 부근)
- `apps/web/src/lib/__tests__/auth-hooks.test.ts` — step 0 이 만든 파일. **여기에 이어 쓴다**

## 배경

★★**탈퇴가 「돈을 멈추는」 경로다.** 우리 API 가 계정 잠금 · 전략 archive · 라이브 세션 전량
비활성 · 웹훅 시크릿 revoke 를 **한 트랜잭션**으로 처리한다(2026-08-15 surface-truth S3 P1 —
그전까지 탈퇴가 돈을 안 멈췄다).

★**`beforeDelete` 에서 부르는 이유**를 주석이 적고 있다 — 클라이언트에게 「우리 API 를 먼저,
그다음 deleteUser」 순서를 맡기면 **그 순서가 지켜지는지 아무도 보증하지 않는다.**
`beforeDelete` 는 **throw 하면 삭제가 중단**되므로 fail-closed 다.
2026-08-17 codex 적대 리뷰가 **이 배선의 부재를 P1** 으로 잡았다 — 엔드포인트는 있었고 **부르는
쪽이 없었다.** 그 수리를 재는 테스트가 지금 0건이다.

★**403 + `auth_user_inactive` 를 통과시키는 것은 멱등성 계약이다**(codex P2). 우리 정리는
커밋됐는데 Better Auth 가 자기 행을 지우다 실패하면, 다음 시도에서 그 사용자는 이미
`is_active=false` 라 이 API 가 403 을 낸다. **그것을 실패로 읽으면 DB 를 손으로 고치기 전에는
영영 지울 수 없는 상태가 된다.**

## 작업

`apps/web/src/lib/__tests__/auth-hooks.test.ts` 에 케이스를 **추가**한다(새 파일 금지).

### 호출 방식

```ts
const beforeDelete = (
  auth as unknown as {
    options: {
      user: {
        deleteUser: {
          beforeDelete: (u: unknown, req?: Request) => Promise<void>;
        };
      };
    };
  }
).options.user.deleteUser.beforeDelete;
```

**두 seam 을 갈아끼운다:**

- `vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never)` —
  ★**진짜 DB 를 치지 마라.** `getToken` 은 세션 조회를 하므로 반드시 spy 로 막는다
- `vi.stubGlobal("fetch", fetchMock)` — 우리 API 호출을 가로챈다.
  ★`afterEach` 에서 `vi.unstubAllGlobals()` + `vi.restoreAllMocks()`

### 최소한 이 여섯을 더 덮어라 (파일 전체 케이스 ≥13)

1. ★**성공 경로** — fetch 가 **204** 를 내면 resolve(throw 없음). 그리고 **호출 형태**를 단언해라:
   메서드 `DELETE` · URL 이 `/api/v1/auth/me` 로 끝난다 · `Authorization: Bearer jwt-x`
2. ★★**403 + `auth_user_inactive` → 통과(멱등)** — body 가
   `{ detail: { code: "auth_user_inactive" } }` 면 resolve.
   이 케이스에 「멱등 — 우리 쪽 정리는 이미 끝났다는 뜻이다(codex P2)」 주석을 달아라
3. ★**403 + 다른 코드 → throw** — `{ detail: { code: "forbidden" } }` 는 **거부**.
   403 전체를 통과시키면 fail-open 이 된다
4. ★**403 + JSON 파싱 실패 → throw** — body 가 JSON 이 아니어도 삼키지 않는다
   (코드가 `.catch(() => null)` 로 받은 뒤 코드 비교에서 떨어지는 경로)
5. ★**500 / 502 → throw** — 메시지에 status 숫자가 들어간다.
   「그 밖에는 삭제를 진행하지 않는다 — 돈이 안 멈춘 채로 인증 사용자가 사라지는 것이 최악」
6. ★**전제 실패 두 방향** — ⑴ `request` 가 `undefined` 면 **fetch 를 부르지 않고** throw
   ⑵ `getToken` 이 `null`(또는 `{token: undefined}`)이면 **fetch 를 부르지 않고** throw.
   ★**둘 다 `expect(fetchMock).not.toHaveBeenCalled()` 를 함께 단언해라** — 토큰 없이 우리 API 를
   치면 401 이 나고 그것을 「실패」로 읽어 fail-closed 인 척하는 우회로가 생긴다

★**음성 대조를 빠뜨리지 마라** — 케이스 3·4·6 이 그것이다. 「전부 통과」와 「전부 거부」는
둘 다 판별력 0 인 모양이다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/auth-hooks.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/auth-hooks.test.ts 2>/dev/null | grep -c ' > ')" -ge 13
cd apps/web && pnpm exec eslint src/lib/__tests__/auth-hooks.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 최종 케이스 수와 **덮지 못한 분기**(있다면)를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/auth.ts` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**진짜 fetch 를 내보내지 마라** — `vi.stubGlobal("fetch", …)` 없이 훅을 부르면 네트워크로 나간다
- ★**진짜 Postgres 에 붙지 마라** — `auth.api.getToken` 은 반드시 spy 로 막는다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- step 0 이 만든 케이스를 지우거나 약화시키지 마라. 케이스 수는 단조 증가여야 한다
- 새 테스트 파일을 만들지 마라 — 이 lane 이 소유한 파일은 `src/lib/__tests__/auth-hooks.test.ts` 하나다
- 커밋하지 마라(커밋은 러너 소관)
