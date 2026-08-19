# Step 0: bl810-landing-eyebrow

랜딩(`/`) 마케팅 섹션의 **번호 아이브로우 장식**(`<span className="num">01</span>` ~ `06`)을 제거한다.
근거 = [BL-810] 사용자 결정 「마케팅 면 한정 제거」. 앱 내부(대시보드·리포트)의 캐논은 건드리지 않는다.

## 읽어야 할 파일

- `apps/web/AGENTS.md` (TS 컨벤션 §7~§11)
- `apps/web/src/features/marketing/components/landing-features.tsx`
- `apps/web/src/features/marketing/components/landing-how-it-works.tsx`
- `apps/web/src/features/marketing/components/landing-support.tsx`
- `apps/web/src/features/marketing/components/landing-performance.tsx`
- `apps/web/src/features/marketing/components/landing-faq.tsx`
- `apps/web/src/features/marketing/components/landing-cta.tsx`
- `apps/web/src/features/marketing/components/__tests__/landing-features.test.tsx`
- `apps/web/src/features/marketing/components/__tests__/landing-how-it-works.test.tsx`

## 작업

### ⑴ 6컴포넌트의 `<span className="num">NN</span>` 제거

각 파일에 아래 모양의 블록이 정확히 1개씩 있다 (실측 좌표):

| 파일                       | 줄  | 현재 내용                                   |
| -------------------------- | --- | ------------------------------------------- |
| `landing-features.tsx`     | 85  | `<span className="num">01</span> 기능`      |
| `landing-how-it-works.tsx` | 38  | `<span className="num">02</span> 작동 방식` |
| `landing-support.tsx`      | 11  | `<span className="num">03</span> 지원 현황` |
| `landing-performance.tsx`  | 10  | `<span className="num">04</span> 성능`      |
| `landing-faq.tsx`          | 54  | `<span className="num">05</span> FAQ`       |
| `landing-cta.tsx`          | 28  | `<span className="num">06</span> 시작`      |

각각 아래처럼 바꾼다 — **`<p className="eyebrow">` 자체와 그 뒤 한국어 라벨 텍스트는 남긴다.**

```tsx
// before
<p className="eyebrow">
  <span className="num">01</span> 기능
</p>

// after
<p className="eyebrow">기능</p>
```

`<p>` 안이 텍스트 한 줄만 남으므로 prettier 가 한 줄로 접는 형태가 정본이다.
(형식은 `pnpm prettier --write` 결과에 맡겨라. 직접 정렬하려 애쓰지 마라.)

### ⑵ 단위 테스트 단언 갱신 (2건)

- `__tests__/landing-features.test.tsx:12,15` — `it("section id=features + eyebrow 01", ...)` 안의
  `expect(container.querySelector(".eyebrow .num")?.textContent).toBe("01");`
- `__tests__/landing-how-it-works.test.tsx:12,15` — 같은 모양의 `"02"`

둘 다 **제거를 집행하는 단언으로 바꾼다.** 즉 「번호가 없다 + 라벨 텍스트는 있다」를 검사한다:

```tsx
it("section id=features + 번호 아이브로우 없음 (BL-810)", () => {
  const { container } = render(<LandingFeatures />);
  expect(container.querySelector("#features")).not.toBeNull();
  expect(container.querySelector(".eyebrow .num")).toBeNull();
  expect(container.querySelector(".eyebrow")?.textContent).toBe("기능");
});
```

`it` 제목도 함께 고쳐라 — 「eyebrow 01」이라는 제목이 남으면 다음 세션이 거짓을 읽는다.
기존 `it` 블록의 나머지 단언(`#features` 존재 등)은 그대로 살려라.

## Acceptance Criteria

```bash
cd apps/web && ! grep -rq 'className="num"' src/features/marketing/
cd apps/web && pnpm vitest run src/features/marketing/components/__tests__
cd apps/web && pnpm tsc --noEmit
```

## 금지사항

- **`apps/web/src/styles/globals.css` 를 수정하지 마라.** 이유: `.eyebrow .num` 규칙(1288줄)은
  `KITPORT-START`(966) ~ `KITPORT-END`(1876) 경계 안에 있고, `src/__tests__/design-canon-kit-port.test.ts`
  가 그 경계 안을 `_kit.html` 과 **주석까지 정규화 대조**한다. 한 줄만 지워도 그 가드가 빨개진다.
- **마케팅 밖(`src/features/marketing/` · `src/app/pricing/` 이외)의 `.num` 을 건드리지 마라.**
  이유: `table.trades td.num` 과 백테스트 리포트 셸의 `.section .eyebrow .num` 은 앱 내부 캐논이고,
  e2e `sprint46-tier3-nth.spec.ts:428` 이 `/backtests/<id>` 에서 그 번호 01~10 을 단언한다.
- `/pricing` 을 이 step 에서 건드리지 마라 — step 2 소관이다 (원장이 「셋을 한 커밋에 묶지 마라」).
- 문구·레이아웃·색을 「개선」하지 마라. 이 step 은 장식 요소 **제거**만 한다.
- 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
