# Step 0: route-params

## 읽어야 할 파일

- `apps/web/src/app/(dashboard)/backtests/[id]/page.tsx` (19줄) ·
  `apps/web/src/app/(dashboard)/optimizer/[id]/page.tsx` (19줄) ·
  `apps/web/src/app/(dashboard)/strategies/[id]/edit/page.tsx` (19줄) — **이번 테스트의 대상 3개**
- `apps/web/src/app/invite/[token]/__tests__/page.test.tsx` — ★**이 레포의 서버 컴포넌트 테스트
  관용구다**(`const el = await Page({ params: Promise.resolve({...}) })`). 같은 모양으로 써라
- `apps/web/src/app/pricing/__tests__/page.test.tsx` — `next/navigation` mock 선례

## 배경

셋은 **동적 세그먼트를 해석해 뷰에 넘기는 라우트 엔트리**다. 얇지만 **분기가 하나 있다** —
`strategies/[id]/edit` 는 **UUID 형식이 아니면 `notFound()`** 로 즉시 404 를 낸다(BE 왕복 전 early return).

★**착수 전 CONTROL 실측 (2026-08-21):** 셋 다 `export default async function` 이고
`await params` 로 id 를 꺼낸다. `backtests/[id]` 와 `optimizer/[id]` 는 `metadata` 를 갖고,
`strategies/[id]/edit` 는 2026-08-21 ① 사전 배치 PR 에서 `title: "전략 편집"` 이 생겼다.
데이터 페칭도 `headers()` 호출도 셋 다 없다 — **params 해석과 위임이 전부다.**

★**prop 이름이 셋 다 다르다. 코드를 열어 확인하고 관측한 것을 박아라** — 손으로 추측해 적지 마라.

## 작업

`apps/web/src/app/(dashboard)/__tests__/route-params.test.tsx` **하나**를 신설한다.
세 페이지를 default import 하고, 각 뷰 컴포넌트(`BacktestDetailView` · `OptimizerRunDetail` ·
`EditorView`)를 `vi.mock` 으로 **받은 props 를 그대로 드러내는 마커**로 대체한다.

`next/navigation` 은 `notFound` 를 **던지는 함수**로 mock 한다 — 실제 Next 런타임처럼 제어를
끊어야 「호출 뒤에도 렌더가 이어졌다」를 잡을 수 있다.

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★**세 페이지 전부 `await params` 의 `id` 를 뷰로 그대로 넘긴다** — parametrize 로 셋을 돌려
   전달된 prop 값이 입력 id 와 **글자까지 같다**. ★prop 이름은 페이지마다 다르니 **코드에서 읽어라**
2. ★**세 페이지가 `params` Promise 를 실제로 await 한다** — `params` 에 지연 해석되는 Promise
   (예: `new Promise(r => setTimeout(() => r({id}), 0))`)를 줘도 정상 동작한다.
   동기 객체만 넣고 통과하면 Next.js 16 계약(§7 `params` 는 `Promise<>`)을 안 잰 것이다
3. ★★**`strategies/[id]/edit` — 유효한 UUID 는 통과한다.** 소문자 v4 형식 1건으로 `EditorView` 가 렌더되고
   `notFound` 가 **0회** 호출된다
4. ★★**대문자 UUID 도 통과한다** — 정규식에 `i` 플래그가 있다. 이것이 없으면 대문자 URL 이 404 가 된다
5. ★★**UUID 가 아니면 `notFound()` 를 부른다** — 최소 4종을 parametrize 로 돌려라:
   빈 문자열 · `"abc"` · **하이픈 없는 32자 hex** · **하이픈 위치가 틀린 36자**.
   ⑶ 과 ⑷ 는 「길이만 본다」·「hex 만 본다」 같은 느슨한 검사를 잡는 케이스다
6. ★**`notFound()` 뒤에 뷰를 렌더하지 않는다** — `notFound` 가 던진 뒤 `EditorView` mock 이
   **0회** 호출됐다. (`notFound()` 를 부르고 그냥 지나가면 잘못된 id 로 화면이 그려진다)
7. **`backtests/[id]` · `optimizer/[id]` 는 형식 검증을 하지 않는다** — 임의 문자열 id 를 줘도
   `notFound` 없이 뷰가 렌더된다. ★**이것을 결함으로 단언하지 마라** — 지금 동작을 고정하는 것이고,
   두 페이지의 404 는 뷰/BE 가 낸다. 그 사정을 주석으로 남겨라
8. ★**세 페이지의 `metadata.title` 이 비어 있지 않고 서로 다르다** — 셋을 import 해서 재라.
   (① 사전 배치 PR 이 `strategies/[id]/edit` 에 넣은 것을 여기서 고정한다)
9. ★**뷰에 넘어가는 prop 이 id **하나뿐**이 아닌지 관측해라** — 각 페이지가 실제로 넘기는 props 를
   전부 찍어 `summary` 에 적고, 테스트에는 **관측한 그대로** 단언해라
10. ★**id 에 URL 인코딩 문자가 들어가도 페이지가 던지지 않는다** — `"a%2Fb"` 같은 값으로
    `backtests/[id]` 를 호출해 렌더가 성공한다. (라우터가 이미 디코딩한 값을 준다는 전제를 고정한다)

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/(dashboard)/__tests__/route-params.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/(dashboard)/__tests__/route-params.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 10
cd apps/web && pnpm exec eslint 'src/app/(dashboard)/__tests__/route-params.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★경로에 `(dashboard)` 괄호가 있으므로 **작은따옴표**로 감쌌다. `\"` 로 바꾸지 마라(러너의 `bash -c` 에서 죽는다).
★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **9번에서 관측한 세 페이지의 실제 prop 목록**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**대상 3개 `page.tsx` 를 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는
  0줄 변경」이다. 결함을 발견하면 **고치지 말고 `summary` 에 적거나 `blocked` 로 멈춰라**
- ★**UUID 정규식을 테스트 파일에 복사해 오지 마라. 이유:** 대상과 같은 식을 두 곳에 두면
  **항진명제**가 된다. 입력 문자열로만 재라
- ★`apps/web/vitest.config.ts` · `apps/web/tests/setup.ts` **무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `features/**` 의 뷰 컴포넌트를 수정하지 마라 — mock 으로만 대체해라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
