# Step 0: landing-waitlist

## 읽어야 할 파일

- `apps/web/src/app/page.tsx` (41줄) — 랜딩. **인증 사용자는 `/strategies` 로 redirect 한다**
- `apps/web/src/app/waitlist/page.tsx` (92줄) — 웨이트리스트. `?email=` 프리필
- `apps/web/src/app/invite/[token]/__tests__/page.test.tsx` — ★**async 서버 컴포넌트 관용구**
- `apps/web/src/app/pricing/__tests__/page.test.tsx` — `next/navigation` mock 선례
- `apps/web/src/lib/marketing-canon.ts` — `ROADMAP_DISCLAIMER` (이미 테스트가 있다 — 고치지 마라)

## 배경

둘 다 **로그인 이전에 실제 사용자가 보는 화면**이고 둘 다 `async` 서버 컴포넌트다.

★★**랜딩의 진짜 계약은 렌더가 아니라 갈래다** — `getServerAuth()` 가 `userId` 를 주면
`redirect("/strategies")` 로 **랜딩을 아예 안 그린다.** 이것이 깨지면 이미 로그인한 사용자가
마케팅 페이지에 갇히거나(리다이렉트 소실), 반대로 익명 방문자가 로그인 화면으로 튕긴다(오발화).
`redirect()` 는 **던져서** 제어를 끊는 함수라, mock 도 던지게 만들어야 「호출 뒤에도 렌더가
이어졌다」를 잡을 수 있다.

★**waitlist 의 계약은 프리필 정규화다** — `searchParams.email` 은 `string | string[] | undefined`
가 될 수 있는데 페이지는 `typeof email === "string"` 만 통과시키고 나머지는 **빈 문자열**로 떨어뜨린다.
이 값이 그대로 폼으로 간다.

★**착수 전 CONTROL 실측 (2026-08-21):** 랜딩은 `getServerAuth` 를 물고(`server-only` 별칭은
`vitest.config.ts` 에 이미 있다 — 실측 import 성공), waitlist 는 인증을 **안 문다**.
랜딩의 `metadata` 는 **일부러 없다** — root layout 의 `title.default` 가 `"QuantBridge"` 를 주고,
페이지가 자기 title 을 내보내면 template 이 붙어 `"QuantBridge · QuantBridge"` 가 되기 때문이다
(2026-08-21 ① 사전 배치 PR 의 판단). ★**이것을 결함으로 단언하지 마라 — 지금 동작을 고정해라.**

## 작업

`apps/web/src/app/__tests__/landing-waitlist.test.tsx` **하나**를 신설한다.
`@/lib/auth-server` 와 `next/navigation` 을 mock 한다. 랜딩의 섹션 컴포넌트들은
**mock 해서 식별 가능한 마커를 렌더**하게 하면 트리 검사가 쉬워진다(선택 — 실제 렌더도 좋다).

### 최소한 이 아홉을 덮어라 (케이스 ≥9)

1. ★★**랜딩 — `userId` 가 있으면 `/strategies` 로 redirect 한다.** `redirect` mock 이
   **정확히 1회**, 인자가 `"/strategies"` 다
2. ★★**redirect 뒤에는 랜딩을 그리지 않는다** — `redirect` mock 이 던지도록 만들고, 페이지 호출이
   그 예외로 끝나며 섹션 컴포넌트가 **0회** 렌더된다. ★**이 케이스가 없으면 ⑴은 「불렀다」만 재고
   「끊었다」는 안 잰다** — 실제 Next 는 던져서 끊는다
3. ★★**랜딩 — `userId` 가 `null` 이면 redirect 하지 않고 랜딩을 그린다.** `redirect` **0회** 호출 +
   `document.body.textContent`(또는 `renderToStaticMarkup` 결과)가 비어 있지 않다. **이것이 양성 대조다**
4. ★**랜딩이 `#main-content` 를 갖는다** — root layout 의 skip link 목적지다. 둘 중 하나만 바뀌면
   접근성 우회 링크가 죽는데 각각의 테스트로는 안 잡힌다
5. ★**랜딩의 마케팅 섹션이 전부 렌더된다** — ★**개수를 손으로 세어 적지 마라.** `page.tsx` 를 열어
   실제로 조립된 섹션 컴포넌트를 관측하고 **그 목록 전부**가 렌더됐다고 단언해라(하나 빠지면 잡힌다)
6. ★**랜딩에 `GeoBlockBanner` 가 있다** — 제한 지역 방문자에게 가입 전에 알리는 유일한 자리다
7. ★**waitlist — `?email=a@b.co` 가 폼으로 그대로 간다.** `WaitlistFormCard` 를 mock 해서
   `defaultEmail` prop 이 `"a@b.co"` 인지 본다
8. ★★**waitlist — 배열/미지정은 빈 문자열이 된다.** parametrize 로 최소 3종:
   `undefined` · `["a@b.co"]`(배열) · `{}`(키 없음) → 셋 다 `defaultEmail === ""`.
   ★**배열을 첫 값으로 펴지 않는다는 것이 지금 동작이다** — 관측한 대로 박고, 다르면 `summary` 에 적어라
9. ★**waitlist `metadata` 의 `title`·`description` 이 비어 있지 않다** + ★**랜딩(`app/page.tsx`)은
   `metadata` 를 export 하지 않는다** — 위 배경의 이유를 주석 2줄로 남겨라.
   (root template 이 브랜드를 두 번 붙이는 것을 막는 **의도된** 부재다)

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/__tests__/landing-waitlist.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/__tests__/landing-waitlist.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 9
cd apps/web && pnpm exec eslint 'src/app/__tests__/landing-waitlist.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **5번에서 관측한 랜딩 섹션 컴포넌트 목록**, **8번에서 배열 입력이
   실제로 어떻게 떨어졌는지**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`apps/web/src/app/page.tsx` · `app/waitlist/page.tsx` 를 수정하지 마라.** 이유: 이 회차의 계약은
  「테스트만 추가하고 대상 소스는 0줄 변경」이다. 결함은 `summary` 또는 `blocked` 로
- ★★**마케팅 문구 전문을 테스트에 복사해 오지 마라. 이유:** 개정될 카피라 **항진명제**가 되고
  개정마다 의미와 무관하게 red 가 난다. **구조·컴포넌트 존재·prop 값**만 재라
- ★**`src/lib/__tests__/marketing-canon.test.ts` 를 고치지 마라** — 이미 있고 이 lane 소유가 아니다
- ★`apps/web/vitest.config.ts` · `tests/stubs/**` · `tests/setup.ts` **무변경**(8 lane 동시 — 병합 충돌)
- `features/**` · `components/**` 를 수정하지 마라 — mock 으로만 대체해라
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
