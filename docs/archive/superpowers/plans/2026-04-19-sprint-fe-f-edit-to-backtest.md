# Sprint FE-F — Edit 페이지 → Backtest 이동 CTA + strategy_id prefill

**Date**: 2026-04-19
**Branch**: `feat/fe-f-edit-to-backtest` (base `stage/fe-polish-b2`)
**Worktree**: `.claude/worktrees/feat+fe-f`
**SSOT**: `docs/next-session-fe-polish-bundle2-autonomous.md` § `Sprint FE-F`

## 목표

`/strategies/[id]/edit` 헤더에 현재 `disabled` 상태로 존재하는 "백테스트 실행" Button 을
**활성화된 Link CTA** 로 전환. 클릭 시 backtest 폼 페이지로 이동하고, `strategy_id` 쿼리
파라미터가 폼의 전략 선택(select)에 자동 프리필된다.

## SSOT 라우트 타이포 재조정

SSOT 및 worker 프롬프트는 `/backtest?strategy_id=${id}` 를 사용하지만, 실제 백테스트
폼 라우트는 `frontend/src/app/(dashboard)/backtests/new/page.tsx` (복수 + `/new`). 싱글러
라우트 `/backtest` 는 존재하지 않으므로 그대로 사용 시 404 → live smoke 실패 → blocked.

**해석**: SSOT 텍스트에서 "기존 백테스트 form 페이지" = `/backtests/new` 가 의도. 타이포
보정 후 최종 링크는 `/backtests/new?strategy_id=${id}`. 이는 Sprint 7c/FE-03 에 남아있는
`router.push(\`/backtest?strategy_id=${id}\`)` 플레이스홀더도 함께 교정한다.

## 변경 파일 (3 수정 + 2 신규)

### 1) `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/editor-view.tsx`

기존 (line 175~183):

```tsx
<Button
  variant="outline"
  onClick={() => router.push(`/backtest?strategy_id=${strategy.id}`)}
  disabled
  title="백테스트 탭은 Sprint 7b에서 연결됩니다"
>
  <PlayIcon className="size-4" />
  백테스트 실행
</Button>
```

→ 변경:

```tsx
<Button
  variant="outline"
  render={<Link href={`/backtests/new?strategy_id=${strategy.id}`} />}
  nativeButton={false}
  aria-label="백테스트 실행"
>
  <PlayIcon className="size-4" />
  백테스트 실행
</Button>
```

- `render` + `nativeButton={false}` 패턴은 파일 내 기존 사용 (line 122~127, 144~146) 과
  동일. shadcn 토큰 준수.
- `disabled` / `title` 제거. 활성화.

### 2) `frontend/src/app/(dashboard)/backtests/_components/backtest-form.tsx`

`"use client"` 파일. `useSearchParams()` 로 `strategy_id` 수신 → `defaultValues.strategy_id`
에 주입.

```tsx
import { useRouter, useSearchParams } from "next/navigation";
// …
export function BacktestForm() {
  const searchParams = useSearchParams();
  const initialStrategyId = searchParams.get("strategy_id") ?? "";
  const router = useRouter();
  // …
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      strategy_id: initialStrategyId,
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "",
      period_end: "",
      initial_capital: 10000,
    },
  });
  // …
}
```

- RHF 의 `defaultValues` 는 초기 렌더 시 1회 적용. 이후 URL 변경은 의도적으로 무시
  (폼이 마운트된 후에는 사용자가 직접 선택할 수 있는 상태).
- `useSearchParams` 는 Next.js router API → React hook 규칙상 컴포넌트 body 에서만
  호출. `render body ref.current =` 패턴 없음 (LESSON-006 무관).
- `useWatch` 로 구독하는 `selectedStrategy` 가 `initialStrategyId` 를 그대로 반영 →
  Select trigger 에 strategy 명이 표시된다 (strategies 데이터 로드 이후).

### 3) `frontend/src/app/(dashboard)/backtests/new/page.tsx` — Suspense 래핑

`useSearchParams` 를 사용하는 클라이언트 컴포넌트는 Next 16 에서 Suspense 경계가
필요하다. `<BacktestForm />` 을 `<Suspense fallback={null}>` 으로 감싸 CSR bailout 을
방지. fallback 은 최소한으로 유지 (≤ 1 tick) — 기존 페이지 레이아웃은 유지.

### 4) (신규) `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/__tests__/editor-view.test.tsx`

검증 포인트:

- 렌더 시 "백테스트 실행" 링크가 `/backtests/new?strategy_id=${id}` href 를 갖는다.
- disabled 가 아니다 (aria-disabled / disabled 속성 부재).

모킹:

- `next/navigation` useRouter/useSearchParams — useSearchParams 는 `new URLSearchParams()`,
  useRouter 는 push/replace vi.fn.
- `@/features/strategy/hooks` useStrategy → fixture strategy 반환.
- `@/features/strategy/edit-store` → 최소 zustand 구현 또는 실제 store 사용 (selectors 만).
- `@clerk/nextjs` 는 useStrategy 내부에서 getToken 호출 여부 확인 후 필요 시 mock.

### 5) (신규) `frontend/src/app/(dashboard)/backtests/_components/__tests__/backtest-form.test.tsx`

검증 포인트:

- `useSearchParams` 가 `strategy_id=abc` 를 반환할 때, `Select` trigger 의 value prop /
  숨김 input 의 value 가 `"abc"` 이다.
- searchParams 없을 때 초기값은 빈 문자열, placeholder "전략을 선택하세요" 가 노출.

모킹:

- `next/navigation` — useSearchParams(), useRouter()
- `@/features/strategy/hooks` useStrategies → items 에 `{ id: "abc", name: "Test" }` 포함
- `@/features/backtest/hooks` useCreateBacktest → no-op
- `@clerk/nextjs` 필요 시

## 구현 순서

1. ✅ editor-view.tsx 수정 (CTA 활성화 + Link 전환)
2. ✅ backtest-form.tsx 수정 (useSearchParams + defaultValues prefill)
3. ✅ backtests/new/page.tsx Suspense 래핑
4. ✅ editor-view.test.tsx 추가
5. ✅ backtest-form.test.tsx 추가
6. ✅ self-verify: lint / tsc / test / build
7. ✅ Playwright live smoke + CPU 샘플링
8. ✅ Evaluator dispatch (subagent isolation=worktree)
9. ✅ PR 생성 (base=stage/fe-polish-b2)

## Guard rails (엄수)

- **LESSON-004**: `react-hooks/*` eslint-disable 금지 — 추가 disable 없음.
- **LESSON-005**: queryKey factory + `makeXxxFetcher` CallExpression — 건드리지 않음
  (기존 BacktestsPage 유지).
- **LESSON-006**: render body `ref.current =` 금지 — 없음.
- **TS strict**: any 금지 — 없음.
- **BE 변경 없음**: scope 외 — frontend 만.
- **shadcn 토큰 준수**: 기존 `render` + `nativeButton` 패턴 재사용.

## Rollback

단일 PR. `git revert` 로 원복 가능. Edit page 의 "백테스트 실행" 버튼은 원래 disabled
상태였으므로 기능적 퇴행 없음.
