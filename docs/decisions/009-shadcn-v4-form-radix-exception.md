# ADR 009 — shadcn/ui v4 Nova Preset 규칙 예외 (form.tsx radix-ui + ui/ 직접 수정)

> **작성일:** 2026-04-17
> **작성 세션:** /superpowers:subagent-driven-development Sprint 7c T1 post-review
> **관련 커밋:** `a6e99e4` (T1 Foundation)
> **적용 규칙:** [`.ai/stacks/nextjs-shared.md`](../../.ai/stacks/nextjs-shared.md) §3 shadcn/ui v4

---

## 배경

Sprint 7c T1 Foundation 구현 중 `pnpm dlx shadcn@latest init` + `add` 실행 과정에서 규칙 위반 2건 발생. 이를 한시적 예외로 승인하고, 규칙 파일에 exception clause를 추가해 장기적으로 관리한다.

### 위반 1 — `form.tsx`가 `radix-ui` umbrella package 사용

- **규칙:** `.ai/stacks/nextjs-shared.md:58` "`@radix-ui/*` 직접 import 금지"
- **실제:** `frontend/src/components/ui/form.tsx:4-5`

  ```tsx
  import type { Label as LabelPrimitive } from "radix-ui"
  import { Slot } from "radix-ui"
  ```

- **원인:** shadcn v4 Nova preset의 component registry에서 `form` 항목이 empty. 구현자가 fallback으로 `https://ui.shadcn.com/r/styles/new-york-v4/form.json`에서 설치 → 이 버전은 `radix-ui` 기반. Nova preset이 Base-UI를 전면 채택했으나 form은 아직 마이그레이션 전.
- **부수 효과:** `package.json`에 `radix-ui ^1.4.3`이 `@base-ui/react ^1.4.0`와 공존. 실제 사용은 `Slot`, `Label` 2개 primitive 뿐 (tree-shaking으로 bundle 임팩트 최소).

### 위반 2 — `frontend/src/components/ui/*.tsx` 직접 수정

- **규칙:** `.ai/stacks/nextjs-shared.md:60` "`components/ui/` 직접 수정 금지 → 래핑 컴포넌트"
- **실제:** T1 Step 1.4b에서 DESIGN.md §7.1 (Button min-height 48px WCAG) + §7.3 (Input) 준수를 위해 4개 파일 수정:
  - `button.tsx` — `buttonVariants` size 토큰 (default h-12, lg h-14, sm 유지, icon size-12)
  - `input.tsx` — `h-10` → `h-12`
  - `textarea.tsx` — `min-h-[60px]` → `min-h-[96px]`
  - (`form.tsx`는 설치 경로 문제로 수정 아님)
- **원인:** Nova preset baseline이 `h-8/h-7/h-9`라 DESIGN.md의 `48px (h-12)`와 괴리. 래핑 컴포넌트 12개 신설 대안은 duplication 막대 + 실질 이득 없음 (모든 Form/CTA가 래핑 사용해야 하므로 shadcn primitive를 직접 쓰는 의미 소실).

---

## 결정

### 예외 1 — `form.tsx`의 `radix-ui` 사용 허용

- **범위:** `frontend/src/components/ui/form.tsx` 단 1개 파일
- **허용 imports:** `radix-ui`에서 `Slot`, `Label` 2개 primitive만
- **다른 shadcn 컴포넌트는 여전히 `@base-ui/react` 사용** (button/card/tabs/dialog/select/input/dropdown-menu/badge/label/textarea/sonner 11개 전부 Base-UI)
- **유효기간:** Sprint 7d+에서 shadcn Nova preset이 Base-UI 기반 form을 shipping할 때 재검토. 당분간은 실용 수용.

### 예외 2 — DESIGN.md 토큰 reconciliation 한해 `ui/` 직접 수정 허용

- **범위:** shadcn 컴포넌트 초기 설치 직후 **1회성** 수정 — Tailwind 클래스(`h-*`, `min-h-*`, `px-*`, `text-*` 등)의 DESIGN.md 값 정합성 확보
- **금지 유지:** 비즈니스 로직·prop 시그니처·동작 변경·신규 기능 추가는 여전히 래핑 컴포넌트로
- **재발 방지:** 향후 `pnpm dlx shadcn@latest add <component>` 실행 후 추가 설치된 컴포넌트가 DESIGN.md와 불일치하면 동일 범위에서 토큰 reconciliation 허용. 각 추가 시 `chore(frontend): shadcn X component added + token reconcile` 커밋으로 한 번에 처리.

---

## 규칙 파일 변경

`.ai/stacks/nextjs-shared.md` §3 shadcn/ui v4 섹션에 exception clause 추가 (본 ADR과 동일 커밋).

---

## 영향 평가

### Bundle size
- `radix-ui` umbrella에서 `Slot`, `Label` 2개만 tree-shaking → gzip ~1KB 미만. 유의미한 영향 없음.

### 번들 분석 확인 필요 여부
- Sprint 7c 말미 `pnpm build` 성공 시 `.next/analyze/`로 확인 가능. 현재 `CLERK_PUBLISHABLE_KEY` 부재로 build 실패 상태 — 해결 후 확인.

### 마이그레이션 경로
- Sprint 7d+ 후보:
  1. shadcn Nova preset registry에 `form` component shipped 여부 정기 확인
  2. 또는 `@base-ui/react`의 `Field` primitive를 활용한 custom `form.tsx` 구현 (react-hook-form `Controller` + Base-UI Field 합성)
- 마이그레이션 완료 시 본 ADR의 예외 1을 폐기 + `radix-ui` 패키지 제거

### 테스트 영향
- T4 (`/strategies/new` Step 3 metadata) + T5 (`/strategies/[id]/edit` metadata 탭)에서 Form 사용 시 Radix/Base-UI 혼용. 시각·동작 동일성 E2E QA에서 확인.

---

## 관련 자산

- 구현 commit: `a6e99e4` (Sprint 7c T1)
- 본 ADR은 규칙 변경 + 예외 rationale. `.ai/stacks/nextjs-shared.md:60~68` 구간이 업데이트 대상.
- 플랜 대상 task: Sprint 7c T4 / T5 (Form 실사용)

---

## 재검토 조건

아래 중 하나라도 참이면 본 ADR 재검토:

1. shadcn Nova preset registry에 Base-UI 기반 `form` 컴포넌트 추가됨
2. `radix-ui` umbrella bundle size가 tree-shaking에도 gzip 10KB 이상 차지
3. `Slot`, `Label` 외 추가 radix primitive가 필요해짐
4. DESIGN.md 토큰이 크게 개편되어 shadcn 컴포넌트 재생성 필요
