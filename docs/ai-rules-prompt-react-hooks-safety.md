# ai-rules 프로젝트 Claude Code 세션용 프롬프트 (포괄판)

> 사용법: `cd /Users/woosung/project/agy-project/ai-rules && claude`
> 이 파일의 "--- PROMPT START ---" 아래 전체를 복사해서 붙여넣기.

---

## 내부 참고 (프롬프트 붙여넣기 전에)

현재 ai-rules 스캔 결과:
- `.ai/stacks/nextjs/frontend.md` (133줄): React Query / 메모이제이션 가이드 있음, useEffect 안전 규칙 **없음**
- `.ai/stacks/nextjs-shared.md` (190줄): Zod / shadcn / 반응형, hooks 관련 **없음**
- `.ai/common/anti-slop.md` (134줄): 일반 AI slop, React-specific 패턴 **없음** (확인 필요)
- `.ai/common/typescript.md` (28줄): Strict / 네이밍만
- `AGENTS.md` (150줄): 스택 라우팅만, React 패턴 없음
- `.ai/templates/`: `settings.json.example` / `methodology*.md` / `lessons-starter.md` 등
- **ESLint config 템플릿 없음** — 각 프로젝트가 처음부터 설정

---

--- PROMPT START ---

# Context

나는 ai-rules 저장소의 유지관리자다. 2026-04-19 quant-bridge 프로젝트에서 **CPU 100% 무한 렌더 루프로 사용자 시스템이 종료되는 사고**를 겪었고, 이 저장소로 재발 방지 체계를 승격하려고 한다. 중앙 규칙 저장소이므로, 여기 반영된 규칙은 다음 sync 시 모든 Next.js 프로젝트에 배포된다.

단순히 규칙 섹션 하나 추가하는 게 아니라, **이런 클래스의 버그가 구조적으로 불가능하게 만드는 것**이 목표다:
1. 기존 규칙 파일 안의 **나쁜 패턴/표현**이 있으면 교정
2. **강제 린트 설정**을 템플릿으로 제공해서 새 프로젝트가 자동 상속
3. **AI 에이전트가 코드 작성할 때부터** 안전한 패턴을 선택하도록 유도하는 규칙 언어
4. CI / pre-commit / PR template 수준의 **3중 방어선**을 템플릿화

## 사고의 전체 이야기

### 1. 무엇을 만들고 있었나

Next.js 16 App Router + React 19 + Clerk + React Query + shadcn/ui + Base UI 조합으로 Pine Script 파싱 결과를 단계별로 해설하는 대화형 Dialog 컴포넌트. `ParseDialog`가 `result: ParsePreviewResponse` prop을 받아 step machine으로 순회 렌더.

### 2. 1차 구현 (happy path 통과)

```tsx
// parse-dialog.tsx — iter-1, 안전
export function ParseDialog({ open, onOpenChange, result, onSave }: Props) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);

  const clampedIndex = Math.min(index, steps.length - 1);
  const step = steps[clampedIndex] ?? steps[0]!;
  // ... render step ...
}
```

vitest 26/35 green, Playwright live smoke 완주, Clerk 인증 + PUT 200 OK 확인.

### 3. Adversarial Review (Opus + Sonnet) — BUG-A 발견

두 모델이 독립적으로 분석 후 합의:

> "`DialogDescription`이 `index + 1` (unclamped) 을 렌더하므로, `result` prop이 mid-walkthrough에 축소되면 counter가 '5 / 3 단계'처럼 오표시된다."

### 4. 나의 수정 (문제의 원인) — iter-2

BUG-A 방어막으로 두 변경:

```tsx
// ✗ 치명적 실수
import { useEffect, useMemo, useState } from "react";

export function ParseDialog({ result, ... }) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);

  // BUG-A "완전 방어막"이라고 생각했던 useEffect
  // ESLint가 react-hooks/set-state-in-effect 경고했지만
  // "외부 동기화 정당화"라고 판단해서 /* eslint-disable */ 로 override
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setIndex(0);
  }, [result]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // clampedIndex + 1 사용 (counter 일치)
}
```

### 5. result prop의 정체

```tsx
// tab-parse.tsx
const preview = usePreviewParse(strategy.pine_source);
//  ^^^^^^^ React Query useQuery
const live = preview.data;  // ParsePreviewResponse | undefined
// ...
{live && <ParseDialog result={live} ... />}
```

`usePreviewParse`는 표준 `useQuery` (`staleTime: Infinity`, structuralSharing 기본).

### 6. 단위 테스트 통과

```tsx
// parse-dialog.test.tsx — 35/35 green
it("resets index when result changes mid-walkthrough", () => {
  const { rerender } = render(<ParseDialog result={longer} ... />);
  fireEvent.click(nextButton);
  rerender(<ParseDialog result={shorter} ... />);
  expect(counter).toHaveText("1 / 2");  // PASS
});
```

vitest jsdom에서 `rerender({ result: newObj })`는 참조 변화 1회만 발생 → 무한 루프 조건 **미재현**. PR 생성 직전까지 이 버그 존재 확인 불가능.

### 7. 사고 발생

PR 전 최종 dev server 실행. TabParse 탭 진입 직후 CPU 100% 폭주 → 수분 내 사용자 시스템 응답 불가. 강제 종료.

### 8. 왜 실제 환경에서만 재현됐나

`useEffect(() => setIndex(0), [result])`가 무한 루프가 되려면 **`result` 참조가 매 렌더 새로 생성**되어야 한다. React Query `structuralSharing`은 "값이 같으면 참조 유지"지만 다음 조건에서 흔들린다:

- **Next.js 16 Fast Refresh** (dev hot-reload) — 모듈 재평가 시 Query 캐시가 새 wrapper 생성
- **React StrictMode 더블 인보크** — useEffect가 두 번 호출되며 참조 타이밍 충돌
- **부모 컴포넌트 재렌더 + 상태 변경** — `dialogOpen` state 변화 시 TabParse 재렌더 → `usePreviewParse` 재호출 → wrapper 객체 새로 생성 (data는 보통 stable이나 예외 케이스 존재)

jsdom 환경의 `rerender`는 이 중 어느 것도 재현하지 않는다.

### 9. 실제 수정

```tsx
// iter-3, 안전
export function ParseDialog({ result, ... }) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);

  // BUG-A 가드: clamp-only. useEffect로 setIndex 리셋은 무한 루프 위험.
  const clampedIndex = Math.min(index, steps.length - 1);
  // ... DialogDescription에서 clampedIndex + 1 사용
}
```

`useEffect` 완전 제거. "reset state on prop change"를 **render-time clamp**로 대체. UX 손실: result 축소 시 intro로 튕기지 않고 마지막 유효 step에 머무름 (오히려 자연스러움).

### 10. 재발 방지 3중 방어선 (quant-bridge PR #24)

- **Rule-level**: `react-hooks/set-state-in-effect` / `exhaustive-deps` / `rules-of-hooks` / `set-state-in-render` 모두 **error 격상** + `@tanstack/eslint-plugin-query` + `eslint-plugin-react-compiler` 통합
- **Process-level**: `.husky/pre-push` typecheck + test gate + PR template hooks 체크박스
- **CI-level**: `eslint-disable .*react-hooks` grep 차단 + Playwright E2E smoke (render storm + console error)

## 네가 할 일 (ai-rules 저장소 수정)

**총 7개 deliverable. 각각 독립 commit 권장.**

### Deliverable 1: `.ai/stacks/nextjs/frontend.md`에 "React Hooks 안전 규칙" 섹션 추가

**먼저 읽기**: 기존 파일 (133줄)의 섹션 구조 파악. "성능 / 리렌더" 섹션이 있으므로 그 근처에 추가가 자연스러울 수도.

**추가할 내용** (섹션 제목: "React Hooks 안전 규칙 — 무한 루프 방지"):

- 사고 사례 요약 1-2문단 (quant-bridge LESSON-004 링크)
- 다음 금지/권장 패턴 표 (구체 코드 포함):

| 상황 | ❌ 금지 | ✅ 권장 | 이유 |
|---|---|---|---|
| prop 변경 시 state 리셋 | `useEffect(() => setX(0), [prop])` | render-time 공식 패턴 OR `key={propId}` OR derived state | CPU 100% 무한 루프 |
| derived state 계산 | `useEffect(() => setDerived(compute(prop)), [prop])` | `const derived = useMemo(() => compute(prop), [prop])` | 불필요 re-render + 1tick 지연 |
| effect dep에 객체 prop | `useEffect(..., [obj])` | `useEffect(..., [obj.id, obj.length])` 등 scalar | 참조 불안정 |
| React Query data dep | `useEffect(..., [query.data])` | `useEffect(..., [query.dataUpdatedAt])` (timestamp) | structuralSharing도 Fast Refresh에서 흔들림 |
| Zustand store 구독 | `const store = useStore()` | `const value = useStore((s) => s.value, shallow)` | 전체 구독 시 모든 set에 재렌더 |
| RHF watch | `const values = watch()` + `useEffect(..., [values])` | `watch("field")` 또는 `subscribe` API | `watch()` 반환은 매 렌더 새 객체 |
| Zod runtime parse | `const data = schema.parse(raw)` JSX 내부 | `const data = useMemo(() => schema.parse(raw), [raw])` | 매 렌더 새 객체 |

- **ESLint 규칙 disable 금지 목록**:
  - `react-hooks/set-state-in-effect` → 절대 override 금지
  - `react-hooks/rules-of-hooks` → 절대 override 금지
  - `react-hooks/exhaustive-deps` → intentional disable 시 PR 리뷰 필수 + reason comment

- **단위 테스트의 한계**:
  - vitest jsdom은 Fast Refresh / StrictMode 더블 인보크 / React Query 캐시 흐름을 재현 못 함
  - hooks diff 는 **반드시 dev server 5분 이상 실사용 + CPU 100% 없음 확인** (Activity Monitor / `top`)
  - React DevTools Profiler "Highlight updates when components render" 활용
  - Playwright E2E smoke 자동화 (template 6 참조)

**체크리스트 (섹션 말미)**:
```markdown
### hooks 변경 PR 체크리스트
- [ ] 객체/배열 prop을 useEffect dep로 쓰지 않음 (scalar 분해)
- [ ] `eslint-disable react-hooks/*` 주석 없음
- [ ] RQ `data` / Zustand full store / RHF `watch()` / Zod `.parse()` 결과를 useEffect dep에 쓰지 않음
- [ ] dev server 5분 실사용 + CPU 100% 없음 확인
- [ ] Profiler로 불필요 재렌더 없음 확인 OR React Compiler 활성
```

### Deliverable 2: `.ai/stacks/nextjs-shared.md` 점검 + 필요 시 연결

**먼저 읽기**: 190줄 파일. 'React Query' / 'Zustand' / 'Zod' / 'React Hook Form' 섹션이 있다면 Deliverable 1의 관련 행 (RQ / Zustand / RHF / Zod) 으로 **crosslink 추가**.

예시 추가 문구: "> Hook safety 사용법은 [frontend.md §React Hooks 안전 규칙](./nextjs/frontend.md#react-hooks-안전-규칙) 참조."

기존 문구 중 다음 패턴이 있다면 **교정**:
- "useEffect로 server state 동기화" — 명시적으로 "React Query가 담당, useEffect 불필요" 로 교정
- "watch() 로 폼 값 감시" — `subscribe` API 또는 field-scope `watch("field")` 권장으로 교정

### Deliverable 3: `.ai/stacks/nextjs-fullstack/fullstack.md` 점검 (읽기 후 판단)

fullstack.md에 `useState`, `useEffect`, `useRef` 언급이 있음 (176줄). 현재 표가 Server/Client 경계 설명 수준이라면 그대로 두되, useEffect **사용 기준** 지침이 없으면 Deliverable 1 링크 추가.

### Deliverable 4: `.ai/templates/` 에 ESLint 설정 템플릿 신규 생성

**파일**: `.ai/templates/eslint-config-nextjs.mjs`

```javascript
// Next.js 16 + React 19 프로젝트용 flat config 템플릿.
// `frontend/eslint.config.mjs` 에 이 파일을 복사하거나 extend.
//
// LESSON-004 (quant-bridge 2026-04-19 CPU 100% 사고) 기반 강화:
// - react-hooks/* 규칙 모두 error (disable 시 무한 루프 위험)
// - @tanstack/eslint-plugin-query: queryKey 일관성 검증
// - eslint-plugin-react-compiler: React 19 hooks 안전성 자동 검증

import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import queryPlugin from "@tanstack/eslint-plugin-query";
import reactCompiler from "eslint-plugin-react-compiler";

export default [
  ...nextCoreWebVitals,
  ...nextTypescript,
  ...queryPlugin.configs["flat/recommended"],
  {
    plugins: {
      "react-hooks": reactHooks,
      "react-compiler": reactCompiler,
    },
    rules: {
      // ★ 무한 루프 방어선 (disable 절대 금지)
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "react-hooks/set-state-in-effect": "error",
      "react-hooks/set-state-in-render": "error",
      // React 19 컴파일러 호환성
      "react-compiler/react-compiler": "error",
      // queryKey 일관성
      "@tanstack/query/exhaustive-deps": "error",
    },
  },
  prettier,
  {
    ignores: [".next/**", "node_modules/**", "dist/**", "coverage/**"],
  },
  {
    rules: {
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports" },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
];
```

**README에 해당 파일 언급 추가** (README의 "새 프로젝트 부트스트랩" 섹션 아래에):
```
# Next.js 프로젝트 lint 강화 (LESSON-004 방어선)
cp .ai/templates/eslint-config-nextjs.mjs frontend/eslint.config.mjs
pnpm add -D eslint-plugin-react-hooks @tanstack/eslint-plugin-query eslint-plugin-react-compiler
```

### Deliverable 5: `.ai/common/anti-slop.md` 에 React 안티패턴 추가

**먼저 읽기** (134줄). 현재 anti-slop 파일이 주로 AI 생성 코드의 generic slop (중복, 의미없는 comment 등) 을 다룬다면, 새 섹션 "React/Next.js 안티패턴" 추가:

- `useEffect` 로 derived state 계산 (useMemo로 대체)
- `useEffect` 로 prop → state 동기화 (render-time 패턴 또는 key reset)
- `useEffect` dep 에 object/array literal 직접 기입
- `/* eslint-disable react-hooks/* */` 주석 삽입
- React Query `data` 참조를 useEffect dep로 사용
- "just in case" 불필요한 `useCallback` / `useMemo` (React Compiler 활성 시 역효과)
- Zustand 전체 store 구독 (selector 없이)

**원칙 문구**: "AI가 useEffect 를 쓸 때는 먼저 'derived state로 가능한가?' 를 물어야 한다. Effect는 외부 시스템(DOM, timer, subscription) 동기화에만 사용한다."

### Deliverable 6: `.ai/templates/methodology.md` + `methodology-tooled.md` 에 "hooks diff → live smoke" 단계 추가

**먼저 읽기**. 개발 방법론 설명 중 "test" 단계 근처에 다음 추가:

> **Frontend hooks 변경 시 추가 검증**
>
> useEffect / useState / 커스텀 훅 / React Query / Zustand / RHF 수정이 diff에 포함되면:
> 1. `pnpm lint` + `pnpm test` (기본)
> 2. `pnpm build` (prod 번들 회귀 검증)
> 3. **dev server 5분 이상 실사용** (Activity Monitor로 CPU 100% 감시)
> 4. Playwright E2E smoke 실행 (render storm / console error 검출)
> 5. React DevTools Profiler 로 불필요 재렌더 없음 확인
>
> unit test 통과만으로 ship 금지. jsdom은 Fast Refresh / StrictMode / React Query 조합 실전 동작 재현 못 함. (ref: quant-bridge LESSON-004)

### Deliverable 7: `.ai/templates/settings.json.example` 점검

**먼저 읽기**. Claude Code hooks 설정 예시가 있을 것. `PostToolUse` 에 **"Frontend hooks diff 시 경고"** 훅 추가 고려:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if git diff HEAD -- 'frontend/**/*.ts' 'frontend/**/*.tsx' 2>/dev/null | grep -qE 'useEffect|useState|useRef|useMemo|useCallback'; then echo '⚠️ hooks 변경 감지. PR 전 dev server 5분 live smoke 필수 (LESSON-004).'; fi"
          }
        ]
      }
    ]
  }
}
```

판단 기준: 이 훅이 template에 자연스럽게 녹아들지 애매하면 skip하고 README `생산성 습관` 섹션에 언급만.

### Deliverable 8 (optional): `AGENTS.md` 핵심 규칙에 1줄 추가

`AGENTS.md` 에 "Frontend hooks 변경 금지/권장 패턴은 `.ai/stacks/nextjs/frontend.md` §React Hooks 안전 규칙 참조. ESLint `react-hooks/*` override 금지." 만 간결히.

## 작업 방식 가이드

1. **기존 파일을 먼저 전부 읽는다.** 내가 제시한 내용이 이미 있거나 중복되면 병합 / 교정 형태로.
2. **각 Deliverable을 독립 commit**. 커밋 메시지:
   - `docs(nextjs): React Hooks 안전 규칙 섹션 추가 (LESSON-004)`
   - `docs(nextjs-shared): hooks safety crosslink 추가`
   - `feat(templates): eslint-config-nextjs.mjs 신규 (LESSON-004 방어)`
   - `docs(anti-slop): React 안티패턴 섹션 추가`
   - `docs(methodology): hooks diff live smoke 단계 추가`
3. **내가 준 표/체크리스트/코드가 어색한 한국어면 다듬어라.** 직역 티 나지 않게.
4. **실제 테스트 불가능한 가이드는 쓰지 마라.** "Activity Monitor로 CPU 확인" 같이 실제로 할 수 있는 것만.
5. **완료 후 변경 파일 목록 + 각 커밋 SHA를 내게 보고.**

## 나쁜 패턴 교정 원칙

기존 ai-rules 파일에서 다음 패턴이 보이면 **교정**:

| 발견 패턴 | 교정 방향 |
|---|---|
| "useEffect로 server state fetch" | React Query가 처리. Effect 금지 |
| "useEffect로 state 동기화" | derived state / render-time 패턴으로 |
| "watch()로 폼 값 감시" | `subscribe` / scoped `watch("field")` |
| `/* eslint-disable */` 를 예시로 보여주는 경우 | 예시 자체 삭제 또는 "이렇게 하지 말 것"으로 |
| "이런 경우엔 exhaustive-deps 끌 수 있다" | 제거. 예외 없이 지킨다. |

## 참고 자료

- React 공식 "You Might Not Need an Effect": https://react.dev/learn/you-might-not-need-an-effect
- React 공식 "Adjusting state on prop change" (render-time 패턴): https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
- React Compiler: https://react.dev/learn/react-compiler
- 실제 사고: quant-bridge PR #23 (feat) / PR #24 (guardrails) — `.ai/project/lessons.md` LESSON-004
- 사고 당시 코드 변화 범위:
  - bad commit: quant-bridge `559b291` (useEffect 추가)
  - fix commit: quant-bridge `994f79b` (useEffect 제거)

--- PROMPT END ---

---

## 사용 방법 정리

1. 새 터미널에서:
   ```bash
   cd /Users/woosung/project/agy-project/ai-rules
   claude
   ```

2. 위 "--- PROMPT START ---" 부터 "--- PROMPT END ---" 까지 전체 복사 후 붙여넣기
3. Claude Code가 8개 deliverable을 순차 실행 (각각 독립 commit)
4. 완료 후 `git log --oneline` 으로 생성된 commit 확인
5. 필요 시 `git push origin main` 으로 ai-rules 저장소에 반영

## 이 프롬프트를 수정해서 쓰려면

- Deliverable 수 줄이고 싶으면 (예: 빠르게 1,4만): 해당 deliverable만 남기고 나머지 섹션 삭제
- 톤을 더 간결하게: "사고의 전체 이야기" 섹션을 요약 3문단으로 축약
- 여러 스택 동시 (flutter 등): 각 stacks/ 파일에 동일한 메시지 적용하라고 명시
