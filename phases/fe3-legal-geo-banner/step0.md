# Step 0: legal-and-geo-banner

## 읽어야 할 파일

- `apps/web/src/components/legal-notice-banner.tsx` — **대상 ⑴** (32줄)
- `apps/web/src/components/geo-block-banner.tsx` — **대상 ⑵** (15줄)
- `apps/web/src/lib/legal-links.ts` — 배너가 소비하는 상수 SSOT
- `apps/web/src/components/__tests__/` — 이 디렉터리의 테스트 관용구

## 배경

두 배너 다 **전 페이지 상단에 고정**되고 **테스트가 0건**이다.

- **`LegalNoticeBanner`** — 파일 주석이 「**법적 고지이므로 제거하지 않는다**」고 못박았다.
  `layout.tsx` 가 렌더하므로 이것이 사라지면 **모든 화면에서 고지가 동시에 사라진다.**
- **`GeoBlockBanner`** — 3계층 지역 방어의 **사용자 가시 layer** 다(L1 WAF · L2 `proxy.ts` ·
  L3 `lib/auth.ts` 가입 훅). WAF 에 안 걸린 방문자에게 「가입이 안 된다」를 미리 알린다.

★**두 배너의 값은 「보인다」가 아니라 「무엇을 말하는가」다** — 링크가 죽으면 고지는 장식이 되고,
지역 문구가 실제 정책과 어긋나면 **하지 않을 일을 약속하는 것**이 된다.

## 작업

`apps/web/src/components/__tests__/legal-geo-banner.test.tsx` **하나**를 신설한다.
둘을 직접 import 해 렌더한다. `next/link` 는 vitest 에서 children 을 그대로 렌더하므로 mock 불필요다.

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★**`LegalNoticeBanner` 의 링크 3개가 `LEGAL_LINKS` 를 그대로 쓴다** —
   `lib/legal-links.ts` 를 **import 해서** 세 `href` 를 대조해라.
   ★**경로 문자열(`/disclaimer` 등)을 테스트에 하드코딩하지 마라** — 사본이 되고,
   상수를 고쳐도 테스트가 옛 값을 지켜 **드리프트를 숨긴다**
2. ★★**링크 3개가 서로 다르다** — 세 `href` 의 Set 크기가 3.
   복사 실수로 셋이 같은 곳을 가리키면 두 문서가 도달 불가가 된다
3. ★**고지 문장이 실재한다** — 「투자 자문이 아니」라는 취지가 텍스트에 있다.
   ★**전문을 단언하지 마라** — 핵심 낱말 1~2개로 재라(문구는 개정된다)
4. ★**`role="note"` 다** — 두 배너 다. 스크린리더가 본문과 구분하는 유일한 단서다
5. ★★**링크가 터치 타겟을 가진다** — 세 `a` 가 `LINK_CLASS` 의 `min-h-11`(44px)을 갖는다.
   ★모바일에서 법무 링크를 못 누르면 고지는 **형식만 남는다**. 클래스 문자열로 재라
6. ★**`GeoBlockBanner` 가 지역 정책을 말한다** — 텍스트에 `Asia-Pacific` 이 있고,
   ★**`US` 와 `EU` 가 「가입 불가」 쪽으로 언급된다.** 이것이 `lib/geo.ts` 의 제한 목록
   (US + EU27 + GB)과 **같은 방향**인지가 이 케이스의 뜻이다
7. ★★**음성 대조 — 두 배너는 서로 다르다** — 각각 렌더한 `textContent` 가 다르고,
   `GeoBlockBanner` 에는 **링크가 0개**다(안내 전용). 링크가 생기면 사람이 판정해야 한다
8. ★**양성 대조** — 두 컴포넌트가 함수이고 렌더 결과 `textContent` 가 각각 **20자 이상**이다.
   빈 div 를 통과시키는 상태를 배제한다

★`afterEach(cleanup)` 을 걸어라 — 둘을 연속 렌더한다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/components/__tests__/legal-geo-banner.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/components/__tests__/legal-geo-banner.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 8
cd apps/web && pnpm exec eslint 'src/components/__tests__/legal-geo-banner.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **6번에서 실제로 찾은 지역 낱말**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- 두 배너와 `lib/legal-links.ts` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**`src/lib/__tests__/marketing-canon.test.ts` 를 고치지 마라** — `LEGAL_LINKS` 를 이미
  덮고 있고 이 lane 소유가 아니다
- ★**고지 문구 전문을 복사해 오지 마라** — 항진명제가 되고 개정마다 무의미하게 red 가 난다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
