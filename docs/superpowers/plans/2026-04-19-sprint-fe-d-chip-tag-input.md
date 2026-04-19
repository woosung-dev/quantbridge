# Sprint FE-D — Strategy form chip-style tag input

**Date**: 2026-04-19
**Branch**: `feat/fe-d-chip-tag-input` (base `stage/fe-polish-b2`)
**Scope SSOT**: `docs/next-session-fe-polish-bundle2-autonomous.md` § "# Sprint FE-D"

## 목표

Strategy 생성 3-step wizard 의 Step 3 (메타데이터) 내 tags 입력을 **comma-split 텍스트 → chip UI** 로 교체. 파워 유저 마찰 해소 + 모바일 실수 입력 가시화.

## 현재 상태

- `frontend/src/app/(dashboard)/strategies/new/_components/step-metadata.tsx:135-150` 에 comma-split `<Input onChange={split comma trim filter}>` 가 유일한 tags 입력
- `form.setValue("tags", tags, { shouldDirty: true })` 로 RHF state 연동
- Zod schema: `CreateStrategyRequestSchema.tags: z.array(z.string()).default([])` (max 제약 없음) — schema 불변
- Badge variant: `default|secondary|destructive|outline|ghost|link` (base-ui + cva)

## 설계

### 1) `frontend/src/features/strategy/components/tag-input.tsx` (신규)

**Props** (controlled):
- `value: string[]`
- `onChange: (next: string[]) => void`
- `placeholder?: string`
- `maxTags?: number` — 옵셔널 상한 (UI 차단). 미지정 시 무한. 테스트에서 `max=5` 시나리오 검증

**State** (내부):
- `draft: string` — 현재 입력 중인 텍스트 (controlled input)

**Key handlers**:
- `Enter` / `,` / `Tab` → `commit()`: `draft.trim()` 이 비어있지 않고 `value.includes(trimmed)` 가 아니며 `maxTags` 미도달이면 `onChange([...value, trimmed])` + `setDraft("")`. `preventDefault()` 호출 (Tab 은 focus 이동 방지).
- `Backspace` + `draft === ""` + `value.length > 0` → `onChange(value.slice(0, -1))`
- 기타 키: 기본 동작

**제거 버튼**: 각 chip 우측 `×` (×는 `×` 문자 또는 lucide `X` 아이콘). 클릭 시 `onChange(value.filter((_, i) => i !== idx))`.

**컨테이너 클래스**: `flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-input px-3 py-2 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2`. 내부 `<input>` 은 `flex-1 min-w-[120px] bg-transparent outline-none`.

**접근성**: chip 컨테이너에 `role="group" aria-label`, 제거 버튼은 `aria-label={\`${tag} 태그 제거\`}`. input 은 form 라벨과 `aria-describedby` 로 연결.

### 2) Form 통합 — `step-metadata.tsx`

`FormItem` 블록 내 `<Input onChange=...>` 를 `<TagInput value={field.value} onChange={field.onChange} placeholder="trend, ema, crossover" />` 로 교체.
- `FormField name="tags"` + `Controller`-style render (이미 RHF `Form`/`FormField` 사용 중 — `control={form.control}` 패스)
- `form.setValue` 수동 호출 제거. RHF 가 관리.
- 기존 Zod resolver 로 submit 시 검증, 라벨 텍스트 `태그` 로 단순화 (comma 힌트는 placeholder 에만).

### 3) Unit test — `frontend/src/features/strategy/components/__tests__/tag-input.test.tsx`

Vitest + @testing-library/react + user-event. Controlled wrapper (`useState`) 로 체크.

| # | 시나리오 | 기대 |
|---|---------|------|
| 1 | "trend" + Enter | value=["trend"], input="" |
| 2 | "ema" + comma | value=["ema"], input="" |
| 3 | 초기 value=["a","b"], 빈 input Backspace | value=["a"] |
| 4 | 초기 value=["trend"], "trend" + Enter | value=["trend"] (중복 차단) |
| 5 | maxTags=5, 이미 5개, "x" + Enter | value 불변 (max 도달) |

추가(권장): chip × 버튼 클릭 시 해당 제거.

## 실행 순서

1. `components/tag-input.tsx` 작성
2. `components/__tests__/tag-input.test.tsx` 작성 (동시 이지만 TDD 는 오버헤드, 구현 직후 테스트)
3. `step-metadata.tsx` 통합 — Badge import 제거 여부 확인 (파싱 요약에서 사용 중, 유지)
4. Self-verify: lint / tsc / test / build
5. Live smoke (Playwright MCP) — `/strategies/new` Step 3 까지 진행 후 시나리오 a–e
6. Evaluator subagent dispatch (superpowers:code-reviewer, isolation=worktree)
7. PR `--base stage/fe-polish-b2`

## 준수

- LESSON-004: `react-hooks/*` eslint-disable 금지. 필요 시 deps 구조 수정
- LESSON-005: query hook 미추가 (TagInput 은 pure UI)
- LESSON-006: render body `ref.current = v` 금지 — TagInput 에 ref 필요 없음
- LESSON-007: dev server orphan 정리
- TS strict: `any` 금지
- shadcn 토큰 (`ring`, `ring-offset`, `input`, `border`) 사용, 하드코딩 색상 금지

## 리스크

- base-ui Badge 에 `onClick`/children 인라인 `<button>` 이 중첩되면 스타일 붕괴 가능 → chip 을 Badge 가 아닌 `<span>` + chip 전용 스타일로 구현 고려. (Badge 는 span 기반이라 내부 button 허용되지만 visual 호환성 우선)
- Tab 키 preventDefault 가 form 내 다른 필드 간 이동을 깨뜨리지 않도록 — draft 가 비어 있으면 preventDefault 하지 않고 commit 도 스킵 (기본 Tab 동작 유지).
