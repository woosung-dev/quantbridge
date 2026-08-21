# Step 0: app-shell

## 읽어야 할 파일

- `apps/web/src/app/layout.tsx` (60줄) · `apps/web/src/app/(dashboard)/layout.tsx` (24줄)
  — **이번 테스트의 대상 2개**
- `apps/web/src/components/providers/server-identity-provider.tsx` — 헤더에 [BL-786] 전말이 있다
- `apps/web/src/lib/brand-palette.ts` — `viewport.themeColor` 의 SSOT
- `apps/web/src/app/__tests__/not-found.test.tsx` — 이 디렉터리의 렌더 관용구
- `apps/web/src/app/invite/[token]/__tests__/page.test.tsx` — **async 서버 컴포넌트** 관용구
  (`const el = await Layout({...})` → `renderToStaticMarkup(el)`)

## 배경

두 레이아웃은 **앱의 조립 계약 자체**다. 화면 컴포넌트는 3차([BL-815])가 채웠지만 **셸은 비어 있었다.**

여기 사는 계약 셋:

1. ★**`metadata.title.template`** — 각 라우트는 **순수 페이지명만** 내보내고 브랜드 접미(`· QuantBridge`)는
   root layout 이 붙인다. 2026-08-21 ① 사전 배치 PR 이 이 규약으로 페이지 7개를 채웠고,
   `invite` 가 브랜드를 **두 번** 붙이던 것을 고쳤다 — **template 이 사라지면 모든 페이지 제목이 브랜드를 잃는다**
2. ★**`viewport.themeColor`** — 다크/라이트 두 값이 `BRAND_PALETTE` 와 동기여야 한다. 하드코딩 hex 가
   섞이면 모바일 브라우저 크롬 색만 조용히 어긋난다
3. ★★**`ServerIdentityProvider` 가 `getServerAuth().userId` 를 받는다** ([BL-786]) — 이것이 빠지면
   React Query 키가 `anon` → 진짜 id 로 흔들려 **목록·배지 요청이 전부 두 번 나간다.**
   **화면은 안 깨진다 — 값만 두 배로 나간다.** 렌더 테스트로는 안 잡히고 이 배선을 직접 봐야 잡힌다

★**착수 전 CONTROL 실측 (2026-08-21):** root layout 은 **동기** 함수, `(dashboard)/layout.tsx` 는
**async** 함수(`await getServerAuth()`)다. `@/lib/auth-server` 는 `import "server-only"` 를 물지만
`vitest.config.ts` 의 `resolve.alias` 가 `tests/stubs/server-only.ts` 로 갈아끼워 **import 된다**(실측).
★그리고 root layout 은 `@/lib/fonts` → `next/font/google` 을 문다 — ① 사전 배치 PR 이
`tests/stubs/next-font-google.ts` 별칭을 세워 두었다. **그 스텁은 요청한 `variable` 값을 그대로 되비춘다.**

## 작업

`apps/web/src/app/__tests__/app-shell.test.tsx` **하나**를 신설한다.

root layout 은 `<html>/<body>` 를 반환하므로 `renderToStaticMarkup` 으로 **문자열**을 얻어 재라
(jsdom `render` 에 넣으면 중첩 `<html>` 이 되어 판별력이 흐려진다).
`(dashboard)/layout.tsx` 는 `getServerAuth` 를 mock 하고 `await Layout({children})` 로 **엘리먼트 트리**를
직접 검사해라 — `ServerIdentityProvider` 의 `userId` prop 을 보는 것이 요점이라 마크업으로는 못 잰다.

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★★**root `metadata.title` 이 `default` + `template` 구조다** — `template` 에 `%s` 자리표가 있고
   브랜드 문자열을 포함한다. ★**정확한 문자열은 코드에서 읽어 그대로 박아라**(추측 금지)
2. ★**`metadata.description` 이 비어 있지 않다**
3. ★★**`viewport.themeColor` 2종이 `BRAND_PALETTE` 와 같은 값이다** — `dark`/`light` 각각
   `BRAND_PALETTE.dark.bg` · `BRAND_PALETTE.light.bg` 를 import 해서 비교해라.
   ★**hex 리터럴을 테스트에 적지 마라** — 항진명제가 되고 팔레트 개정마다 의미 없이 red 가 난다
4. ★**`prefers-color-scheme` 두 media 쿼리가 서로 다르다** — 같은 값이 두 번 들어가면 테마 전환이 죽는다
5. **root layout 이 `lang="ko"` 로 렌더된다** — 스크린리더·번역기가 이것을 읽는다
6. ★**skip link 가 있고 `#main-content` 를 가리킨다** — WCAG 2.4.1 bypass blocks.
   `sr-only` 계열 클래스로 시작해 **포커스 시에만** 보이는 형태인지도 관측해라
7. **root layout 이 자식을 렌더한다** — 넘긴 children 마커가 출력에 있다
8. ★★**`(dashboard)/layout.tsx` 가 `getServerAuth().userId` 를 `ServerIdentityProvider` 로 넘긴다** —
   mock 이 `{userId: "u-42", token: "t"}` 를 주면 provider 의 `userId` prop 이 `"u-42"` 다.
   ★**엘리먼트 트리에서 prop 을 직접 꺼내 비교해라** — 마크업 문자열에는 안 나온다
9. ★★**`userId` 가 `null` 이어도 던지지 않고 `null` 을 그대로 넘긴다** — provider prop 이 `null` 이다.
   (`"anon"` 같은 값으로 바꿔치기하면 [BL-786] 의 「세션 도착 후 세션이 정본」 계약이 깨진다)
10. **`(dashboard)/layout.tsx` 가 자식을 셸 안에 렌더한다** — `DashboardShell` 을 mock 해서
    children 이 그 안으로 들어가는지 확인한다. `ShortcutHelpDialog` 도 함께 렌더되는지 관측해라

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/__tests__/app-shell.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/__tests__/app-shell.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 10
cd apps/web && pnpm exec eslint 'src/app/__tests__/app-shell.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **1번에서 읽은 `template` 문자열 원문**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`apps/web/src/app/layout.tsx` · `(dashboard)/layout.tsx` 를 수정하지 마라.** 이유: 이 회차의
  계약은 「테스트만 추가하고 대상 소스는 0줄 변경」이다. 결함은 `summary` 또는 `blocked` 로
- ★★**`apps/web/vitest.config.ts` · `apps/web/tests/stubs/**`·`tests/setup.ts`를 수정하지 마라.**
이유:`server-only`·`next/font/google` 별칭은 ① 사전 배치 PR 이 세운 **공유 설정**이고,
  8 lane 이 동시에 도는 중이라 건드리면 병합 충돌이 난다. **필요한 것은 이미 다 뚫려 있다**
- ★**`components/providers/**`·`components/layout/**` 를 수정하지 마라** — mock 으로만 대체해라
- ★**`BRAND_PALETTE` 값을 테스트에 리터럴로 복사하지 마라. 이유:** 항진명제가 된다. import 해서 비교해라
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
