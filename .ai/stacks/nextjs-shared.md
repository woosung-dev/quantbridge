---
description: Next.js 16 + shadcn/ui v4 + Zod v4 + 반응형 공통 패턴 (frontend.md, fullstack.md에서 참조)
paths:
  - "src/**/*.ts"
  - "src/**/*.tsx"
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Next.js 공통 패턴

> frontend.md와 fullstack.md에서 공통으로 참조하는 패턴.
> Clerk 인증은 각 스택 규칙에서 별도 정의 (FE-only vs Fullstack 패턴이 다름).

---

## 1. Next.js 16 필수 패턴

- `params`, `searchParams`는 **`Promise<>`** 타입 → `await` 필수
- `middleware.ts` 대신 **`proxy.ts`** 사용
- `node_modules/next/dist/docs/` 참조 필수

```typescript
// ✅ Next.js 16
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <Detail id={id} />;
}
```

---

## 2. Zod v4

- `import { z } from "zod/v4"` 필수 (v3 경로 `"zod"` 금지)
- **Schema First:** 타입 중복 선언 금지 → `z.infer<typeof schema>` (필요 시 `z.input`)로 추출하여 재사용
- **Transform 강제:** Form 입력 타입(String)과 API 요청 타입(Number 등)이 다를 경우, `onSubmit` 내부에서 수동 파싱 금지 → 스키마 레벨에서 `.transform()`으로 일원화

```typescript
// ✅ 스키마에서 변환
const priceSchema = z.string().transform((v) => Number(v));

// ❌ onSubmit에서 수동 변환
const handleSubmit = (data: FormData) => {
  api.create({ price: Number(data.price) }); // 금지
};
```

---

## 3. shadcn/ui v4

- 내부 의존성: `@base-ui/react` (Radix UI 아님)
- `@radix-ui/*` 직접 import 금지
  - **예외 (ADR 009, 2026-04-17):** Nova preset registry에 Base-UI 버전이 미포함된 경우에 한해 `radix-ui` umbrella package 허용. 현재 `form.tsx` 1개 파일이 `Slot`/`Label` 2개 primitive만 사용. Sprint 7d+에서 registry 업데이트 시 Base-UI로 마이그레이션
- 추가: `pnpm dlx shadcn@latest add [component]`
- `components/ui/` 직접 수정 금지 → 래핑 컴포넌트
  - **예외 (ADR 009):** 초기 설치 직후 **1회성 DESIGN.md 토큰 reconciliation** 한해 허용 (Tailwind class 높이/간격 등 시각 토큰만). 비즈니스 로직·prop 시그니처·동작 변경은 여전히 래핑 컴포넌트로 처리

---

## 4. 반응형 (Responsive Design)

### 핵심 원칙: Mobile-First

- **기본 스타일 = 모바일(320px~)**, 상위 브레이크포인트로 확장
- 데스크탑 기준으로 먼저 작성하고 나중에 모바일 축소하는 방식 금지
- **적용 대상:** 사용자 대면 페이지는 필수. 어드민/내부 도구는 프로젝트 요구사항에 따름

### 브레이크포인트 기준 (Tailwind v4 기본값)

| 접두사 | 최소 너비 | 주요 용도 |
|--------|----------|----------|
| (없음) | 0px | 모바일 기본 |
| `sm:` | 640px | 소형 태블릿 |
| `md:` | 768px | 태블릿 |
| `lg:` | 1024px | 데스크탑 |
| `xl:` | 1280px | 와이드 |

### 레이아웃 패턴

```tsx
// ✅ 반응형 그리드 — 모바일 1열 → 데스크탑 3열
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

// ✅ Flex 방향 전환 — 모바일 세로 → 데스크탑 가로
<div className="flex flex-col md:flex-row gap-4">

// ✅ 레이아웃 기본 래퍼
<div className="container mx-auto px-4">

// ✅ 모바일/데스크탑 분기
<nav className="hidden md:flex">           {/* 데스크탑 전용 */}
<button className="md:hidden">            {/* 모바일 전용 */}

// ✅ 반응형 타이포그래피
<h1 className="text-2xl md:text-3xl lg:text-4xl font-bold">

// ✅ 테이블 — 가로 스크롤 래퍼 필수
<div className="overflow-x-auto">
  <table className="min-w-[600px] w-full">
```

### 금지 패턴

```tsx
// ❌ 페이지 레이아웃에 고정 너비 — 모바일에서 가로 스크롤 발생
<div className="w-[600px]">
<main className="min-w-[800px]">

// ✅ 최대 너비 제한은 허용 — 콘텐츠 가독성 확보에 유효
<div className="max-w-[600px] w-full">
<article className="max-w-prose">

// ❌ 페이지 레벨에서 브레이크포인트 없는 다열 그리드
<div className="grid-cols-3">          {/* 모바일에서 찌그러짐 */}

// ✅ 소형 컴포넌트 내부 고정 열은 허용
<div className="grid grid-cols-3 gap-1">  {/* 예: 아이콘 3개 나열 */}
```

### 완료 체크리스트

> UI 컴포넌트 작성 후 아래 항목을 자가 검증한다.

- [ ] 페이지 레이아웃에 고정 너비(`w-[Npx]`) 없음 — `max-w-[Npx]`는 허용
- [ ] 다열 그리드/플렉스에 모바일 브레이크포인트 적용 (`grid-cols-1 md:grid-cols-N`)
- [ ] 모바일(320px)에서 가로 스크롤 발생하지 않음
- [ ] 텍스트 오버플로우 처리 (`truncate` 또는 `break-words`)
- [ ] 테이블은 `overflow-x-auto` 래퍼로 감싸기
