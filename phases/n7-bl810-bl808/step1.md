# Step 1: bl810-landing-step-label

랜딩(`/`) 「작동 방식」 섹션의 **STEP 라벨 장식**(`STEP 1` ~ `STEP 4`)을 제거한다.
근거 = [BL-810] 사용자 결정 「마케팅 면 한정 제거」.

## 읽어야 할 파일

- `apps/web/AGENTS.md` (TS 컨벤션 §7~§11)
- `apps/web/src/features/marketing/components/landing-how-it-works.tsx`
- `apps/web/src/features/marketing/components/__tests__/landing-how-it-works.test.tsx`
- `apps/web/src/styles/globals.css` — 3441~3454 부근(`.lp-steps` / `.lp-step` / `.lp-step-num`)

## 작업

### ⑴ `landing-how-it-works.tsx` — `num` 필드와 라벨 span 제거

현재 구조(실측):

```tsx
interface Step {
  num: string;      // "STEP 1" ~ "STEP 4"
  title: string;
  desc: string;
}

const STEPS: Step[] = [ { num: "STEP 1", title: "전략 등록", desc: "..." }, ... ];

// 렌더:
{STEPS.map((s) => (
  <article key={s.num} className="card lp-step">
    <span className="lp-step-num">{s.num}</span>
    <h3 className="lp-step-title">{s.title}</h3>
    <p className="lp-step-desc">{s.desc}</p>
  </article>
))}
```

바꿀 것:

1. `interface Step` 에서 `num` 필드를 지운다.
2. `STEPS` 4개 항목에서 `num: "STEP N",` 줄을 지운다. **배열 순서는 그대로 둔다** — 순서가
   곧 단계 순서다(문서 문구 「각 단계는 앞 단계의 결과를 그대로 받습니다」가 그것을 전제한다).
3. `<span className="lp-step-num">{s.num}</span>` 줄을 통째로 지운다.
4. `key={s.num}` 이 죽으므로 `key={s.title}` 로 바꾼다 (4개 title 은 서로 다르다: 전략 등록 /
   백테스트 / 최적화와 OOS 검증 / 데모 실행).
5. 파일 첫 줄 한국어 헤더 주석에 STEP 라벨 언급이 있으면 사실과 맞게 고쳐라.

### ⑵ `globals.css` 의 `.lp-step-num` 규칙 제거

`.lp-step-num { ... }` 규칙(3443줄부터 시작하는 블록 전체)을 지운다. **이 규칙의 유일한 소비자가
위에서 지운 span 이므로 이 step 이 만든 고아다.** `.lp-steps` · `.lp-step` · `.lp-step-title` ·
`.lp-step-desc` 는 **남긴다** — 계속 쓰인다.

★이 규칙은 `KITPORT-START`(966) ~ `KITPORT-END`(1876) 경계 **밖**(3443)이라 kit-port 무결성
가드의 대조 대상이 아니다. 그래도 AC 에 `src/__tests__` 전량을 넣어 두었으니 반드시 통과시켜라.

### ⑶ 단위 테스트 갱신

`__tests__/landing-how-it-works.test.tsx` 의 `it("4 단계 카드(.lp-step) + STEP 라벨", ...)`(18줄)이
`screen.getByText("STEP 1")` · `screen.getByText("STEP 4")` 를 단언한다(21~22줄). 이것을
**제거를 집행하는 단언**으로 바꾼다:

```tsx
it("4 단계 카드(.lp-step) — STEP 라벨 없음 (BL-810)", () => {
  const { container } = render(<LandingHowItWorks />);
  expect(container.querySelectorAll(".lp-step").length).toBe(4);
  expect(container.querySelector(".lp-step-num")).toBeNull();
  expect(screen.queryByText(/^STEP /)).toBeNull();
  expect(screen.getByText("전략 등록")).toBeInTheDocument();
  expect(screen.getByText("데모 실행")).toBeInTheDocument();
});
```

`it` 제목에서 「STEP 라벨」이 남지 않게 하라. 기존 `.lp-step` 4개 단언은 살려라.
step 0 이 이미 같은 파일의 다른 `it`(아이브로우)을 고쳤다 — **그 변경을 되돌리지 마라.**

## Acceptance Criteria

```bash
cd apps/web && ! grep -rq 'lp-step-num' src/
cd apps/web && ! grep -rq 'STEP 1' src/features/marketing/
cd apps/web && pnpm vitest run src/features/marketing/components/__tests__ src/__tests__
cd apps/web && pnpm tsc --noEmit
```

## 금지사항

- **`KITPORT-START` ~ `KITPORT-END`(globals.css 966~1876) 안을 건드리지 마라.** 이유:
  `src/__tests__/design-canon-kit-port.test.ts` 가 그 경계 안을 `_kit.html` 과 **주석까지**
  정규화 대조한다. `.lp-step-num`(3443)은 그 밖이므로 제거 대상이고, 그 안은 아니다.
- `.lp-steps` / `.lp-step` / `.lp-step-title` / `.lp-step-desc` 를 지우지 마라 — 살아 있는 소비자가 있다.
- 4단계의 **본문 문구(title·desc)를 바꾸지 마라.** 이 step 은 라벨 장식 제거만 한다.
- `/pricing` 을 건드리지 마라 — step 2 소관이다.
- 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
