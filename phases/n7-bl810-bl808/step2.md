# Step 2: bl810-pricing-meter

`/pricing` 세 구성 카드의 **채워진 진행 막대(filled meter)** 3개를 제거한다.
근거 = [BL-810]: 「가격 미정」인데 85.7% / 0% / 0% 막대가 붙어 **신뢰 축에서 오해를 부른다.**

## 읽어야 할 파일

- `apps/web/AGENTS.md` (TS 컨벤션 §7~§11)
- `apps/web/src/app/pricing/page.tsx`
- `apps/web/src/app/pricing/__tests__/page.test.tsx`

## 작업

### ⑴ `<div className="meter">` 블록 3개 제거

실측 좌표 — `src/app/pricing/page.tsx` 의 267 / 325 / 384 줄. 세 곳 모두 아래 모양이다:

```tsx
<div className="meter">
  <span style={{ width: "85.7%" }} />
</div>
```

(각각 `85.7%` / `0%` / `0%`.) **`<div className="meter">` 여는 태그부터 닫는 태그까지 통째로**
지운다. 바로 뒤의 `<p className="plan-meter-foot">…</p>` 문단은 **남긴다** — 그 문단이 분모·분자와
제외 항목을 문장으로 설명하고 있어(예: 「비교표 11개 중 로컬에 해당하는 7개 기준으로 지금 되는 것
6개 (85.7%)」) 정보 축은 그것이 담당한다. 제거 대상은 **막대 그래픽뿐**이다.

`plan-meter-foot` 이라는 클래스 이름도 그대로 둔다 — 이름을 바꾸면 `globals.css` 를 함께 고쳐야
하고, 이 step 의 범위(표현 요소 제거)를 넘는다.

### ⑵ 단위 테스트에 제거를 집행하는 단언 추가

`src/app/pricing/__tests__/page.test.tsx` 에 `it` 하나를 추가한다 (기존 5개 `it` 는 그대로 둔다):

```tsx
it("가격 미정 — 진행 막대 없음 (BL-810)", () => {
  const { container } = render(<PricingPage />);
  expect(container.querySelectorAll(".plan .meter").length).toBe(0);
  // 분모·분자 설명 문장은 남는다 — 정보 축은 그쪽이 담당한다.
  expect(container.querySelectorAll(".plan-meter-foot").length).toBe(3);
});
```

## Acceptance Criteria

```bash
cd apps/web && ! grep -q 'className="meter"' src/app/pricing/page.tsx
cd apps/web && grep -q 'className="meter"' src/features/strategy/components/new/parse-result-panel.tsx
cd apps/web && pnpm vitest run src/app/pricing/__tests__ src/__tests__
cd apps/web && pnpm tsc --noEmit
cd apps/web && pnpm build
```

★두 번째 커맨드는 **음성 대조**다 — 「마케팅 면 한정」이 지켜졌는지, 즉 앱 내부의 `.meter`
소비자가 살아 있는지를 반대 방향으로 잰다. 이것이 실패하면 범위를 넘어 지운 것이다.

## 금지사항

- **`apps/web/src/styles/globals.css` 의 `.meter` 규칙(1393~1402)을 지우지 마라.** 이유 둘:
  ⑴ 그 규칙은 `KITPORT-START`(966) ~ `KITPORT-END`(1876) 경계 **안**이라
  `design-canon-kit-port.test.ts` 가 `_kit.html` 과 바이트 대조한다.
  ⑵ 앱 내부 소비자가 5곳 살아 있다 — `features/trading/components/account-balance-section.tsx` ·
  `features/trading/components/orders/orders-blotter.tsx` · `features/onboarding/components/step-4-result.tsx` ·
  `features/strategy/components/edit/diagnostics-strip.tsx` · `features/strategy/components/new/parse-result-panel.tsx`.
- **`/pricing` 밖의 `.meter` 를 건드리지 마라** — 사용자 결정은 「마케팅 면 한정」이다.
- 비교표(`table.cmp`) 11행 · FAQ 4문항 · 웨이트리스트 폼을 건드리지 마라 — 기존 단위가 그 수를 단언한다.
- `plan-meter-foot` 문단의 **문구와 숫자를 바꾸지 마라.**
- 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
