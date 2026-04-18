# ai-rules 프로젝트에 보낼 프롬프트

> 아래 블록을 `cd ../ai-rules && claude`에 그대로 붙여넣기. 한 세션 분량.

---

## 컨텍스트

나는 ai-rules 저장소의 유지관리자다. 방금 quant-bridge 프로젝트에서 실제 발생한 CPU 100% 사고를 겪었고, 이 저장소의 `.ai/stacks/nextjs/frontend.md`에 **재발 방지 규칙**을 추가하려고 한다. ai-rules는 Next.js / FastAPI / Flutter 프로젝트에 sync 배포되는 규칙 허브이므로, 여기 추가된 규칙은 여러 프로젝트에 전파된다.

## 사고 요약 (2026-04-19, quant-bridge Sprint FE-01)

### 어떤 기능?

Next.js 16 App Router FE에서 Pine Script 파싱 결과를 단계별 대화형 Dialog로 해설하는 컴포넌트. React Query + shadcn Dialog + Base UI를 조합.

핵심 파일: `ParseDialog` 컴포넌트 — result prop (React Query의 `preview.data`)을 받아 step machine으로 순차 렌더.

### 어떤 버그?

cross-model adversarial review (Opus + Sonnet)가 BUG-A를 발견:

> "DialogDescription이 `index + 1` (unclamped)을 렌더하므로, `result` prop이 mid-walkthrough에서 축소되면 counter가 '5 / 3 단계'처럼 잘못 표시된다."

### 내가 한 수정 (문제의 원인)

BUG-A 방어막으로 두 가지 변경:
1. DialogDescription: `index + 1` → `clampedIndex + 1` (OK, 올바른 수정)
2. **result prop 변경 시 index 리셋** (문제의 원인):

```tsx
// parse-dialog.tsx — 사고 유발 코드
import { useEffect, useMemo, useRef, useState } from "react";

export function ParseDialog({ open, onOpenChange, result, onSave }) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);

  // ⚠️ 이 useEffect가 CPU 100% 유발
  // ESLint가 `react-hooks/set-state-in-effect` 경고를 냈지만
  // "외부 동기화 정당화"라는 명분으로 override
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setIndex(0);
  }, [result]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const clampedIndex = Math.min(index, steps.length - 1);
  // ... rendering code
}
```

result prop은 React Query `preview.data`에서 옴:

```tsx
// tab-parse.tsx
const preview = usePreviewParse(strategy.pine_source);
const live = preview.data;
// ...
{live && <ParseDialog result={live} ... />}
```

`usePreviewParse`는 표준 `useQuery` (staleTime: Infinity, structuralSharing 기본 on).

### 왜 무한 루프가 되는가?

1. React Query의 `data`는 **보통** 동일 참조를 반환 (structuralSharing). 하지만 다음 조건에서 참조가 흔들림:
   - Next.js 16 Fast Refresh (dev mode hot-reload)
   - React StrictMode 의 effect 더블 인보크
   - 상위 컴포넌트 재렌더 시 useQuery wrapper 객체 재생성
2. `[result]` dep이 새 참조로 감지되면 `setIndex(0)` 발동
3. 재렌더 → Query 훅이 또 호출됨 → wrapper 재생성 → 새 참조 → dep 또 변경 → `setIndex(0)` 또 호출
4. **무한 렌더 루프 → CPU 100%**

### 왜 단위 테스트는 통과했나?

```tsx
// parse-dialog.test.tsx — 35/35 green
it("resets index when result changes", () => {
  const { rerender } = render(<ParseDialog result={longer} ... />);
  fireEvent.click(nextButton);
  rerender(<ParseDialog result={shorter} ... />);
  expect(counter).toBe("1 / 2");  // 통과
});
```

vitest jsdom은 React Query 없이 순수 `rerender(...)`로 1회 참조 변화만 발생 → 루프 조건 미재현. **단위 테스트는 이 클래스의 버그를 검출 못 함.**

### 최종 해결

useEffect 완전 제거. clamp-only로 방어:

```tsx
export function ParseDialog({ open, onOpenChange, result, onSave }) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);
  const savedRef = useRef(false);

  // BUG-A 가드: clamp-only. useEffect로 setIndex 리셋은 무한 루프 위험.
  const clampedIndex = Math.min(index, steps.length - 1);
  const step = steps[clampedIndex] ?? steps[0]!;
  // counter도 clampedIndex + 1 사용 → 항상 steps.length와 동기화
```

UX 차이: result 축소 시 "intro로 리셋" 대신 "마지막 유효 step에 머무름". UX 손실 거의 없음, CPU 안정성 확보.

## 네가 할 일

`.ai/stacks/nextjs/frontend.md`에 **"React Hooks 안전 규칙"** 섹션을 추가 (또는 해당 주제 섹션이 있으면 확장). 적어도 다음 6개 하위 규칙을 포함해야 한다:

### 1. ESLint 규칙 disable 금지 목록

```ts
// eslint.config.mjs — 권장 overrides
rules: {
  "react-hooks/set-state-in-effect": "error",  // default warn → error로 격상
  "react-hooks/exhaustive-deps": "error",
  "react-hooks/rules-of-hooks": "error",
}
```

**절대 override 금지:**
- `react-hooks/set-state-in-effect` — 이 규칙을 우회하면 무한 루프 위험이 항상 존재
- `react-hooks/rules-of-hooks` — hooks 호출 순서 보장

**의도적 override 허용 (단, PR 리뷰 + reason comment 필수):**
- `react-hooks/exhaustive-deps` — 드물게 justify 가능하나 대부분 패턴 변경으로 해결

### 2. "Reset state on prop change" 패턴 규칙

금지:
```tsx
// ❌ CPU 100% 위험
useEffect(() => setX(init), [prop]);
```

권장 1 — render-time 조정 (React 공식 docs 패턴):
```tsx
const [state, setState] = useState(init);
const [prevProp, setPrevProp] = useState(prop);
if (prevProp !== prop) {
  setPrevProp(prop);
  setState(init);  // React가 재시작 render로 처리
}
```

권장 2 — key reset:
```tsx
<Component key={propId} />  // prop 변경 시 전체 remount
```

권장 3 — derived state (가장 단순):
```tsx
const clampedState = clampValue(internalState, derivedFromProps);
// state 자체를 유지하고 계산 시점에 clamp
```

### 3. 라이브러리별 참조 불안정성 경고 맵

| 라이브러리 | 불안정 조건 | 안전 사용법 |
|---|---|---|
| **React Query** | `data` 참조가 Fast Refresh / StrictMode 에서 흔들림. `isPending`, `isFetching` 등 boolean은 안정 | useEffect dep로는 `.data`를 쓰지 말 것. 필요하면 `.dataUpdatedAt` (timestamp) 사용 |
| **Zustand** | `useStore(selector)` 없이 store 전체 구독 시 모든 set 호출마다 재렌더 | 반드시 selector + shallow 사용. `useStore((s) => s.value, shallow)` |
| **React Hook Form** | `watch()` 반환이 매 렌더 새 객체 | useEffect dep 금지. `watch("fieldName")` 단일 필드로 좁히거나 `subscribe` API |
| **Zod** | `schema.parse(raw)` 매 호출 새 객체 | `useMemo(() => schema.parse(raw), [raw])` 또는 모듈 레벨에서 한 번만 parse |
| **Framer Motion / animations** | `useMotionValue` 등 mutable ref는 안정, 반환 객체는 불안정 | 문서의 stable/unstable 구분 확인 |

### 4. useEffect 4대 원칙 (React 18+ 공식 기조)

1. **외부 시스템 동기화에만 사용** — DOM API, subscription, timer, cleanup 필요한 리소스
2. **컴포넌트 내부 상태 파생 금지** — `useMemo`, `useState` initializer, render-time 계산으로 대체
3. **setState in effect는 값 비교 후 조건부** — `if (newValue !== currentValue) setValue(newValue)`
4. **Object/Array dep 금지, scalar 선호** — `[obj.id]`, `[list.length]`, `[data?.updatedAt]`

### 5. 권장 ESLint 플러그인

```bash
pnpm add -D eslint-plugin-react-hooks \
           @tanstack/eslint-plugin-query \
           eslint-plugin-react-compiler
```

```ts
// eslint.config.mjs
import reactHooks from "eslint-plugin-react-hooks";
import queryPlugin from "@tanstack/eslint-plugin-query";
import reactCompiler from "eslint-plugin-react-compiler";

export default [
  ...reactHooks.configs["recommended-latest"],
  ...queryPlugin.configs["flat/recommended"],
  reactCompiler.configs.recommended,
];
```

- **@tanstack/eslint-plugin-query**: React Query 특화 규칙 (stable queryKey, 캐시 키 고유성 등)
- **eslint-plugin-react-compiler**: React 19 컴파일러가 최적화 가능한 형태인지 검증 — 이걸 통과하면 hooks 안전성도 대부분 자동 확보

### 6. "단위 테스트만 믿지 말 것" 규칙

- vitest jsdom은 **Next.js Fast Refresh / StrictMode / React Query 실제 동작 재현 못 함**
- hooks 조합 변경 시 **반드시 dev server live smoke**:
  - 최소 5분 실제 브라우저에서 사용 (Playwright MCP 또는 수동)
  - Activity Monitor / `top` 으로 CPU 사용률 확인 (100% 지속되면 loop 의심)
  - React DevTools Profiler로 "Highlight updates when components render" 켜고 관찰
- CI가 unit test 통과 = "회귀 없음" 증거, live smoke = "작동함" 증거. **둘 다 필요**

### 체크리스트 추가

섹션 끝에 다음을 추가:

```markdown
### hooks diff 체크리스트 (PR 전 필수)

- [ ] ESLint `react-hooks/*` 규칙 모두 error 수준인가?
- [ ] useEffect dep 배열에 객체/배열 prop이 있는가? → scalar로 바꿀 수 있는지 검토
- [ ] `set-state-in-effect` 경고를 disable했는가? → 즉시 패턴 변경 (무한 루프 위험)
- [ ] React Query `.data`, Zustand full-store, RHF `watch()`, Zod `.parse()` 결과가 dep에 있는가? → 금지
- [ ] dev server에서 5분 이상 실제 사용 + CPU 관찰했는가? → unit test만으로 ship 금지
- [ ] StrictMode가 production 빌드에서도 들어가 있는지 확인 (dev에서만 검출되는 버그 방지)
```

## 작업 방식

1. **기존 `.ai/stacks/nextjs/frontend.md`를 먼저 읽어서** 톤/포맷/섹션 구조 파악
2. 기존 규칙과 충돌하지 않게 조화롭게 섹션 추가
3. 위 6개 규칙을 자연스러운 흐름으로 재구성 (내가 준 순서가 최적은 아닐 수 있음)
4. 각 규칙마다 **구체적 코드 예시** 포함 (추상 원칙만 쓰지 말 것)
5. 가능하면 `.ai/common/typescript.md`의 기존 네이밍/strict 규칙과 연결
6. 작성 완료 후:
   - **이 규칙이 적용됐다면 이번 사고를 어떻게 방지할 수 있었는지** 예시로 본문에 한 번 언급
   - 기존 규칙 파일의 업데이트 history 관리 방식(있다면) 준수
7. 커밋 메시지: `feat(rules): React Hooks 안전 규칙 — useEffect + setState 무한 루프 방지`

## 참고 자료

- React 공식: https://react.dev/learn/you-might-not-need-an-effect
- React 공식: https://react.dev/reference/react/useEffect#removing-unnecessary-object-dependencies
- React 19 Compiler: https://react.dev/learn/react-compiler
- 실제 사고 케이스: quant-bridge `feat+sprint-fe-01-tabparse-1q` 브랜치 `994f79b` 커밋 (fix 내역) + `a211a51..08a1206` 커밋 범위 (버그 도입 ~ 발견 ~ 수정)

## 질문 허용

- 기존 `.ai/stacks/nextjs/frontend.md`의 섹션 구조를 보고 **어디에 삽입할지 확실치 않으면 물어볼 것** (start / middle / end)
- 내 6개 규칙 중 **일부를 다른 파일로 분리해야 한다고 판단되면 제안할 것** (예: eslint config는 `.ai/templates/`)
- anti-slop 파일과 중복 우려가 있으면 플래그
