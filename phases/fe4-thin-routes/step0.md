# Step 0: thin-routes

## 읽어야 할 파일

**이번 테스트의 대상 7개** (전부 `apps/web/src/app/(dashboard)/` 아래):

| 경로                      | 줄  |
| ------------------------- | --- |
| `dashboard/page.tsx`      | 6   |
| `admin/waitlist/page.tsx` | 7   |
| `optimizer/page.tsx`      | 13  |
| `orders/page.tsx`         | 13  |
| `trading/page.tsx`        | 15  |
| `backtests/new/page.tsx`  | 13  |
| `strategies/new/page.tsx` | 13  |

- `apps/web/src/app/__tests__/not-found.test.tsx` — 이 레포의 렌더 관용구
- `apps/web/AGENTS.md` §4 — 「`app/`: 조립층. **비즈니스 로직 금지**」

## 배경

일곱은 **자기 뷰 하나에 렌더를 위임하는 것이 전부**인 라우트 엔트리다. 얇지만 두 가지가 여기 산다:

1. ★★**「어느 라우트가 어느 뷰를 그리는가」** — 이 배선이 어긋나면 URL 은 맞는데 다른 화면이 나온다.
   뷰 컴포넌트 자신의 테스트는 이것을 **절대 못 잡는다**(3차 [BL-815] 가 `OptimizerPageView` ·
   `WaitlistAdminView` 를 이미 덮었지만, 그 뷰가 **어느 라우트에 붙어 있는지**는 아무도 안 쟀다)
2. ★**`metadata.title` 계약** — 2026-08-21 ① 사전 배치 PR 이 `dashboard` · `admin/waitlist` 두 개의
   빠진 `metadata` 를 채웠다. 제목은 **§4.10 「페이지 이름 5축 일치」**(nav · breadcrumb · h1 · 푸터 ·
   `<title>`)대로 각 화면의 h1/셸에서 땄다. 브랜드 접미는 root template 이 붙이므로 **여기엔 순수 페이지명만** 있다

★**착수 전 CONTROL 실측 (2026-08-21):** 일곱 다 **`export default function`(async 아님)** 이고
데이터 페칭도 `params`/`searchParams` 소비도 없다. `getServerAuth` 를 무는 것은 **하나도 없다**.
⇒ RTL 의 `render` 로 그대로 렌더된다.

★**뷰 컴포넌트의 import 경로는 페이지마다 다르다 — 코드를 열어 확인해라.** 여기 옮겨 적지 않는 이유는
**복사하면 낡은 사본이 되기 때문**이다.

## 작업

`apps/web/src/app/(dashboard)/__tests__/thin-routes.test.tsx` **하나**를 신설한다.
일곱 페이지를 default import 하고, 각 페이지가 위임하는 뷰 컴포넌트를 `vi.mock` 으로
**서로 구별되는 마커**(예: `data-testid`)를 렌더하도록 대체한다.
★**일곱 개의 mock 경로를 정확히 쓰는 것이 이 lane 의 실제 작업량**이다 — 코드에서 읽어라.

`afterEach(cleanup)` 을 걸어라 — 일곱을 연속 렌더하므로 안 걸면 앞 페이지의 DOM 이 남아
「다른 뷰가 렌더됐다」를 못 잡는다.

### 최소한 이 아홉을 덮어라 (케이스 ≥9)

1. ★**일곱 다 던지지 않고 렌더된다** — parametrize 로 일곱을 돌려 `render()` 가 성공하고
   `document.body.textContent` 또는 마커가 **비어 있지 않다**. ★**이것이 양성 대조다**
2. ★★**각 페이지가 자기 뷰 **하나**를 렌더한다** — parametrize 로 일곱을 돌려 해당 마커가
   **정확히 1개** 있다
3. ★★**다른 여섯 개의 뷰는 렌더되지 않는다** — 같은 루프에서 **나머지 마커가 0개**임을 함께 단언해라.
   ★**이것이 배선 오결선을 잡는 축이다.** ⑵만 있으면 「모든 페이지가 모든 뷰를 그려도」 통과한다
4. ★**일곱 다 `metadata.title` 이 비어 있지 않은 문자열이다** — parametrize
5. ★★**일곱의 `metadata.title` 이 서로 다르다** — `new Set(titles).size === 7`.
   같은 제목 둘이 생기면 브라우저 탭과 검색 결과에서 두 화면이 구별되지 않는다
6. ★**제목에 브랜드 접미가 들어 있지 않다** — 일곱 다 `"QuantBridge"` 를 **포함하지 않는다**.
   root layout 의 `template: "%s · QuantBridge"` 가 붙이므로 여기 또 적으면 **두 번 나간다**
   (2026-08-21 에 `invite/[token]/page.tsx` 가 실제로 그랬고 ① PR 이 고쳤다)
7. ★**일곱 다 `generateMetadata` 를 쓰지 않는다** — 정적 `metadata` 만 있다. 동적 메타가 필요 없는
   라우트에 `generateMetadata` 가 생기면 정적 최적화가 조용히 풀린다. ★**관측한 대로 박아라 —
   지금 그렇지 않은 페이지가 있으면 단언하지 말고 `summary` 에 적어라**
8. ★**일곱 다 async 함수가 아니다** — `Page.constructor.name` 이 `"AsyncFunction"` 이 아니다.
   (데이터 페칭이 라우트 엔트리로 새어 들어오면 여기서 red 가 난다 — `apps/web/AGENTS.md` §4
   「조립층: 비즈니스 로직 금지」의 기계 판정이다)
9. ★**페이지가 뷰에 props 를 넘기지 않는다** — mock 이 받은 props 가 비어 있다(children 제외).
   ★**관측한 대로 박아라** — 넘기는 페이지가 있으면 그 페이지는 예외로 적고 `summary` 에 남겨라

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/(dashboard)/__tests__/thin-routes.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/(dashboard)/__tests__/thin-routes.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 9
cd apps/web && pnpm exec eslint 'src/app/(dashboard)/__tests__/thin-routes.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★경로에 `(dashboard)` 괄호가 있으므로 **작은따옴표**로 감쌌다. `\"` 로 바꾸지 마라(러너의 `bash -c` 에서 죽는다).
★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **일곱의 (라우트 → 뷰 컴포넌트 → title) 표**를 남겨라.
   ★7·9번에서 예외가 있었으면 반드시 적어라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**대상 7개 `page.tsx` 를 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는
  0줄 변경」이다. 결함은 `summary` 또는 `blocked` 로
- ★**`features/**` 의 뷰 컴포넌트를 수정하지 마라** — 그 뷰들 중 둘(`OptimizerPageView`·`WaitlistAdminView`)은 3차가 이미 테스트로 덮었고 이 lane 소유가 아니다. mock 으로만 대체해라
- ★`apps/web/vitest.config.ts` · `tests/stubs/**` · `tests/setup.ts` **무변경**(8 lane 동시 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- ★**`src/app/(dashboard)/__tests__/` 의 다른 파일을 건드리지 마라** — `error-boundaries.test.tsx`(3차) ·
  `list-prefetch.test.tsx`·`route-params.test.tsx`(같은 회차의 **다른 lane**)가 그 디렉터리에 있다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
