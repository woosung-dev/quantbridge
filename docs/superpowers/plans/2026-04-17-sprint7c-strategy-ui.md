# Sprint 7c: Strategy CRUD UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Context

Sprint 6(자동 집행 + Kill Switch + AES-256, PR #9) + Sprint 7a(Bybit Futures + Cross Margin, PR #10)로 **backend 524 tests green**. 반면 **frontend는 Sprint 6에서 만든 `/trading` read-only 3 panel만 존재**하고 Strategy CRUD API(Sprint 3, 완료)의 UI가 없다. 현재 Pine 이터레이션 루프는 `curl + JSON escape + Clerk JWT token`으로 회당 3~10분 마찰 발생.

Sprint 7c는 **pure FE sprint**: Stage 2(2026-04-14)에서 확정된 디자인 시스템(`DESIGN.md`)과 프로토타입 3개(`06-strategies-list.html`, `07-strategy-create.html`, `01-strategy-editor.html`) + `INTERACTION_SPEC.md`를 reference로 `/strategies`, `/strategies/new`, `/strategies/[id]/edit` 3 라우트를 구현한다. Sprint 7b(OKX 멀티 거래소 + Trading Sessions)로 가기 전 FE 부채 1개 해소.

**사전 결정:** [`docs/dev-log/008-sprint7c-scope-decision.md`](../../dev-log/008-sprint7c-scope-decision.md) + writing-plans 세션 decision (2026-04-17)

- **Q1 (Monaco 범위):** **Minimal Pine Monarch tokenizer** — `@monaco-editor/react`에 Pine v5 keyword/function/string/number/comment 5색 토크나이저 등록 (반나절 작업). Plain Monaco은 textarea와 시각적 구분 부재로 탈락, 풀 TextMate grammar는 time box 위반.
- **Q2 (UI primitives):** **shadcn/ui CLI + 필요 컴포넌트만 add** — Button/Card/Tabs/Dialog/Select/Input/Form/DropdownMenu/Badge 9개 + `sonner` 토스트. `src/components/ui/`에 복사됨 (외부 의존 아님).
- **Q3 (라우트):** 3 라우트 분리 (ADR 008 P2 개정안) — Drawer 통합 안함.
- **Q4 (Delete 409 처리):** `DELETE` 응답이 409 `strategy_has_backtests`면 FE에서 archive 제안 다이얼로그 표시 → 확인 시 `PUT {..., is_archived: true}` 전환.
- **Q5 (테스트 전략):** FE testing infra가 아직 없으므로 Sprint 7c는 **manual QA checklist + `pnpm tsc --noEmit` + `pnpm lint`를 primary gate로 사용**. 자동 component test는 Sprint 7d+ 이관.

**Goal:** `/strategies` 페이지에서 전략 목록 CRUD, `/strategies/new`에서 3-step wizard로 Pine source 붙여넣기 → 실시간 파싱 → 메타데이터 저장, `/strategies/[id]/edit`에서 Monaco 탭 UI로 편집/삭제/아카이브. curl 3~10분 루프를 **브라우저 30초 루프**로 단축.

**Architecture:** Next.js 16 App Router `(dashboard)` 라우트 그룹(이미 존재) 하위에 3 라우트 추가. Sprint 6 `/trading` 패턴(`'use client'` + `useQuery` + Zod 런타임 검증 + React Query key factory) 그대로 계승. Monaco는 단 1회 `registerPineLanguage()`를 `<MonacoLoader>` 컴포넌트 마운트에서 idempotent 등록. 파싱은 `useParseStrategy` mutation + `useDebouncedValue` 300ms. Clerk JWT는 `useAuth().getToken()` → `apiFetch(path, { token })` (기존 `lib/api-client.ts` 재사용).

**Tech Stack:** Next.js 16 App Router + TypeScript strict + Tailwind v4 (`@theme`) + React Query 5 + react-hook-form 7 + Zod v4 + @monaco-editor/react (신규) + shadcn/ui (신규 9 컴포넌트) + sonner (신규) + Clerk 6 + Zustand 5 (기존).

**Branch:** `feat/sprint7c-strategy-ui` (main 기반, 사용자 별도 명령 없이 worktree 생성 금지 — superpowers:using-git-worktrees 참조)

**Time box:** 1~1.5주 (Sprint 7b 시작 전 merge). 넘어가면 T5 sub-scope(분석 패널 backtest history stub 등)를 자른다.

---

## Information Architecture (per route)

각 라우트의 visual hierarchy — 구현 시 이 순서대로 prominence 부여. Krug "trunk test" 통과 기준: nav/sidebar 지워도 1) 어느 앱인지(title), 2) 어느 페이지인지(breadcrumb/H1), 3) 지금 할 수 있는 액션(primary CTA) 즉시 파악.

### `/strategies` (목록)

```
┌─ App Shell (sidebar + header) ───────────────────────┐
│  Breadcrumb: "전략"  ·  Header: "내 전략" (H1)       │
│  Sub: "Pine Script 전략을 관리하고 백테스트하세요"    │
│  Primary CTA: [+ 새 전략] ← 우측 상단, blue primary   │
├──────────────────────────────────────────────────────┤
│  [필터 chip: 모두·파싱성공·미지원·실패·보관됨]         │
│  [정렬 dropdown] [그리드/목록 토글]                    │
├──────────────────────────────────────────────────────┤
│  Strategy Card Grid (또는 Table)                      │
│  │ Card 1 │ Card 2 │ Card 3 │   ← 3열 @xl, 2열 @md   │
│  │ Card 4 │ Card 5 │ Card 6 │                        │
├──────────────────────────────────────────────────────┤
│  Pagination: "12개 중 1-12 · [이전] 1/2 [다음]"       │
└──────────────────────────────────────────────────────┘

Prominence 순서: H1 → Primary CTA → Filter chips → Cards → Pagination
```

### `/strategies/new` (3-step wizard)

```
┌─ App Shell ──────────────────────────────────────────┐
│  Breadcrumb: "전략 > 새 전략"  ·  H1: "새 전략 만들기"│
│  Sub: "Pine Script 전략을 업로드하고 자동 파싱 진행"   │
│  Secondary: [저장하고 나가기]   Primary: [다음 단계 →]│  ← 헤더 우측
├──────────────────────────────────────────────────────┤
│  Stepper: (1) 업로드 방식 → (2) 코드 입력 → (3) 확인  │
├──────────────────────────────────────────────────────┤
│  Step content card (max-width 900px, centered)       │
│  ┌─ Step 2 예시 ────────────────────────────────┐    │
│  │ Label + kbd hint                             │    │
│  │ [Monaco editor 400px]                        │    │
│  │ [실시간 파싱 결과 panel]                      │    │
│  │ [← 이전]          [미리보기] [다음 단계 →]    │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘

Prominence 순서: Stepper (어디?) → Step content (무엇?) → Primary action (다음?)
```

### `/strategies/[id]/edit` (편집)

```
┌─ App Shell ──────────────────────────────────────────┐
│  [←] Breadcrumb: "전략 > {name}"  |  parse_status 뱃지│
│  심볼·TF·Pine버전 메타 (mono)  ·  "저장된 지 n분 전"  │
│  우측 action: [백테스트 실행] [삭제]                   │
├──────────────────────────────────────────────────────┤
│  Tabs: [코드] [파싱 결과] [메타데이터]                 │
├──────────────────────────────────────────────────────┤
│  Tab content: 코드 탭 예시 (grid 1fr · 320px @lg)     │
│  ┌─ 저장 상태 hint ─────────────┬─ 파싱 미리보기 ─┐    │
│  │ [Monaco 520px editor]         │ [실시간 panel] │    │
│  └───────────────────────────────┴────────────────┘    │
└──────────────────────────────────────────────────────┘

Prominence 순서: Breadcrumb+이름 → parse_status 뱃지 → 탭 선택 → Monaco
```

각 라우트 **trunk test 통과 조건**: 위 다이어그램의 `Breadcrumb` + `H1` + `Primary CTA` 3개가 sidebar/header 제거 후에도 독립 가시. 구현 시 이 세 요소는 `page.tsx` 상단 16em 이내 렌더.

---

## Interaction State Matrix

6 feature × 6 state. 각 cell은 **유저가 보는 것** 기준 (백엔드 동작 아님).

| Feature | Loading | Empty | Error (4xx) | Error (5xx/network) | Success | Partial |
|---------|---------|-------|-------------|---------------------|---------|---------|
| **List `/strategies`** | 6-card skeleton grid | "첫 전략을 만들어보세요" empty state + 2 CTA | 401→`/sign-in` redirect. 403 shouldn't occur | 빨간 alert "전략 목록을 불러오지 못했습니다" + [다시 시도] 버튼 | 카드 그리드 또는 테이블 | N/A (단일 GET) |
| **Wizard Step 2 parse** | 우측 panel의 pulse dot + "파싱 중..." 라벨 | `pineSource.trim()==""` → "코드를 입력하면..." prompt | 422 파싱 에러 → status=error 뱃지 + 에러 리스트 표시 + [다음 단계] 비활성 | 빨간 alert "파싱 요청 실패 — [재시도]" + Monaco 입력은 유지 | status=ok 뱃지 + entry/exit count + [다음 단계] 활성 | status=unsupported → warning 뱃지 + 미지원 함수 리스트 + [다음 단계] 활성 (저장은 가능) |
| **Wizard Step 3 submit** | 버튼 "생성 중..." + disabled | N/A | 422 Zod → FormMessage 각 필드 inline. 409 name 중복 → name 필드에 setError | toast "생성 실패: 네트워크 오류 — 다시 시도해 주세요" + form 입력 유지 | toast 성공 + `/strategies/[id]/edit` redirect + localStorage clear | redirect 404 → toast "생성됨. 목록에서 확인하세요" + `/strategies` 이동 |
| **Edit 코드 탭 save** | 버튼 "저장 중..." + disabled | N/A | 401→`/sign-in`. 409→archive dialog. 422→inline FormMessage | toast "저장 실패: 네트워크 오류 — 편집 내용 유지됨 [재시도]" | toast "저장되었습니다" + `isDirty=false` | save 성공 but parse_status 변경(ok→error) → warning toast "저장됐으나 파싱 에러가 있습니다" |
| **Edit 메타 탭 save** | 동일 (버튼 spinner) | N/A | 422 → FormMessage inline | toast 재시도 | toast 성공 + form reset dirty | N/A |
| **Delete** | 버튼 "삭제 중..." | N/A | 401→redirect. 403 shouldn't occur | toast "삭제 실패: 네트워크 — [재시도]" + 다이얼로그 열려 있음 | toast + `/strategies` redirect | 409 `strategy_has_backtests` → 다이얼로그가 "archive 제안" phase로 전환 |

### 공통 에러 핸들러 (신규)

`frontend/src/lib/api-client.ts` 확장:

```ts
// ApiError가 HTTP status + 백엔드 code + detail 필드를 모두 노출하도록.
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string | undefined,
    public readonly message: string,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
```

`frontend/src/features/strategy/hooks.ts` 또는 신규 `frontend/src/features/strategy/error-handler.ts`:

```ts
import { toast } from "sonner";
import type { ApiError } from "@/lib/api-client";

export function handleMutationError(err: unknown, ctx: { redirectOn401?: boolean } = { redirectOn401: true }): void {
  const e = err as Partial<ApiError>;
  if (e?.status === 401 && ctx.redirectOn401) {
    // Clerk session 만료 추정. 자동 로그인 페이지로.
    window.location.href = "/sign-in?redirect_url=" + encodeURIComponent(window.location.pathname);
    return;
  }
  if (e?.status === 429) {
    toast.error("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.");
    return;
  }
  if ((e?.status ?? 500) >= 500) {
    toast.error("서버 오류. 잠시 후 다시 시도해 주세요.");
    return;
  }
  // 그 외는 호출부에서 개별 처리 (field mapping 등)
  toast.error(`실패: ${e?.message ?? "알 수 없는 오류"}`);
}
```

모든 `useCreateStrategy` / `useUpdateStrategy` / `useDeleteStrategy`의 `onError`는 먼저 `handleMutationError(err)` 호출 후 필요 시 field mapping 추가.

### Monaco 로딩 실패 fallback

`frontend/src/components/monaco/pine-editor.tsx`에 `loading` 컴포넌트를 실패 detect 가능한 형태로 확장:

```tsx
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  {
    ssr: false,
    loading: () => <div className="h-[400px] animate-pulse rounded-md bg-[#0F172A]" />,
  },
);

// PineEditor 컴포넌트 내부에 ErrorBoundary 래핑 (React 18+)
// Monaco CDN 로딩 실패 시 fallback:
//   <textarea value={value} onChange={...} className="... font-mono" rows={20} />
//   + 경고 alert "에디터 로드 실패 — 기본 입력창으로 전환됩니다"
```

구체 구현: Next.js `error.tsx` boundary 또는 컴포넌트별 `<ErrorBoundary fallback={<PlainTextarea />}>` (react-error-boundary 라이브러리). Sprint 7c 범위: fallback만 스펙, react-error-boundary 설치는 선택 (Monaco CDN 안정성 고려 시 실제 발생 빈도 낮음 → skip 허용).

### Save Conflict (optimistic concurrency)

**Sprint 7c 범위 밖 결정:** 백엔드 Strategy 테이블에 `updated_at` 기반 OCC가 없음. 두 탭 동시 편집은 silent last-write-wins. Sprint 7d+ 후보 (ETag 또는 `If-Unmodified-Since` header 추가).

Sprint 7c는 **최소 mitigation만**: Edit 페이지에서 `useStrategy` refetchInterval 30s → 외부 변경 감지 시 dirty state에서는 toast "이 전략이 다른 곳에서 수정되었습니다. 새로고침 시 현재 편집 내용이 손실될 수 있습니다." (비강제 알림). 구현은 Step 5.2 EditorView의 `useStrategy({ refetchInterval: 30_000 })` 옵션 추가.

---

## User Journey Storyboard

3개 persona × 3단계 time horizon(visceral 5s / behavioral 5m / reflective 5y). 구현 시 이 감정 아크가 유지되도록 microcopy + visual feedback 배치.

### Persona A: First-time user (첫 Pine 등록, 5분 경험)

| Scene | 화면 | 유저 행동 | 유저 감정 | 플랜이 지원하는가? |
|-------|------|---------|---------|------------------|
| 1 | `/strategies` empty | Sidebar "전략" 클릭 | 호기심, 약간 긴장 | ✅ empty state + 2 CTA |
| 2 | 동 | "+ 새 전략 만들기" 클릭 | 결단 | ✅ Primary CTA |
| 3 | `/new` Step 1 | Pine 직접입력 카드 active 확인, 나머지 disabled | "어라, 다른 옵션 곧 나오나?" | ⚠️ "Sprint 7d+" 라벨만 — 유저는 의미 모름 → **"현재는 직접 입력만 지원" 안내 tooltip** 추가 |
| 4 | Step 2 | Pine 코드 붙여넣기 | 긴장 (파싱 실패할까?) | ⚠️ 파싱 중 spinner만 — 첫 경험은 confidence 필요 → **"TradingView 전략 대부분 자동 변환됨" microcopy** 1줄 |
| 5 | Step 2 parse ok | 녹색 뱃지 + count | 안도 (relief) | ⚠️ 너무 차분 → **체크마크 scale-in 200ms** (reduced-motion 시 skip) |
| 6 | Step 3 | 이름/심볼 입력 | 거의 끝, 빠르게 | ✅ short form |
| 7 | `/edit/:id` | "생성되었습니다" toast | 성취감 | ✅ toast + redirect |

**마찰 point:** Scene 3, 4, 5에 microcopy/microanimation 추가 필요 (아래 구현 지시).

### Persona B: Power user (6번째 전략, rapid iteration)

| Time horizon | 행동 | 감정 | 플랜이 지원? |
|-------------|------|------|-------------|
| 5s | `/strategies` → 필터 "파싱 성공" 클릭 | 빠른 검색 완료 | ✅ URL 쿼리 반영 |
| 5m | 기존 전략 열기 → Monaco → 1줄 수정 → ⌘+S → toast → 다음 전략 | 흐름 (flow) 유지 | ✅ ⌘+S 바인딩 + toast |
| 5m | 삭제 실험 전략 → 409 → archive 제안 → 확인 | 의외의 조언이 고마움 | ✅ 409 fallback dialog |
| 5y | "저장 실패" 거의 본 적 없음 | 도구에 대한 신뢰 누적 | ✅ error handler + retry |

**마찰 point:** 없음. 플랜이 이미 power-user flow 최적화. 단 Monaco `⌘+S` 바인딩이 **아직 구현 안 됨** — 현재 저장 버튼 클릭만. 추가 필요.

### Persona C: Failure recovery (Pine 파싱 실패)

| Scene | 유저 행동 | 감정 | 플랜이 지원? |
|-------|---------|------|-------------|
| 1 | Step 2에 Pine 붙여넣기 → parse status=error + L42/67/103 3 에러 | 좌절 | ✅ 에러 리스트 표시 |
| 2 | "이거 고치고 다시 해야 하나? draft 잃나?" | 불안 | ✅ localStorage auto-save (Step 4.9 NEW) |
| 3 | "지원 함수 범위는 어디서 확인?" | 찾는 피로 | ⚠️ **"지원 함수 목록 보기" 링크** Parse Panel 하단에 추가 (Sprint 7d+에서 실제 문서로 연결, 현재는 `docs/dev-log/...`로) |
| 4 | 파싱 status=unsupported (error 아님) | "이대로 저장해도 되나?" | ⚠️ **"지원되지 않는 함수가 있지만 저장 가능 (백테스트 실행 시 제외)" microcopy** 추가 |
| 5 | 이전 단계로 돌아감 | 방향감 유지 | ✅ 이전 버튼 |

**마찰 point:** Scene 3, 4 microcopy 추가 필요.

### Emotional Arc 구현 지시 (코드 변경 지시)

**A. `parse-preview-panel.tsx` 개선 (Step 4.6 코드):**

`result.status === "ok"` 분기에 체크마크 animation + "TradingView 전략 대부분 자동 변환됨" helper text:

```tsx
{result?.status === "ok" && (
  <div className="mt-3 flex items-center gap-2">
    <span
      className="inline-grid size-5 place-items-center rounded-full bg-[color:var(--success)] text-white motion-safe:animate-[scale-in_200ms_ease-out]"
      aria-hidden
    >
      <CheckIcon className="size-3" strokeWidth={3} />
    </span>
    <span className="text-xs text-[color:var(--success)]">
      변환 완료. 바로 저장할 수 있어요.
    </span>
  </div>
)}
```

`globals.css` 추가:

```css
@keyframes scale-in {
  from { transform: scale(0.4); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
```

`result.status === "unsupported"` 분기에 actionable microcopy:

```tsx
<p className="mt-3 text-xs text-[color:var(--text-secondary)]">
  <strong>저장은 가능합니다.</strong> 백테스트 실행 시 해당 함수는 제외되거나 에러를 반환합니다.
  <a className="ml-1 font-medium text-[color:var(--primary)] hover:underline" href="/docs/pine-support" target="_blank" rel="noopener">
    지원 함수 목록 보기 →
  </a>
</p>
```

**B. `step-method.tsx` (Step 4.5) disabled 카드 tooltip:**

```tsx
// Button wrapping with title attribute OR shadcn Tooltip
<button title={opt.disabled ? "현재는 직접 입력만 지원합니다. 파일/URL 업로드는 Sprint 7d+" : undefined} ...>
```

**C. `step-code.tsx` (Step 4.7) 첫 방문자용 helper text:**

Step 2 진입 시 `pineSource.length === 0 && !hasVisited` 상태에서 Monaco 위에 한 줄 helper:

```tsx
{pineSource.length === 0 && (
  <p className="mb-2 text-xs text-[color:var(--text-muted)]">
    💡 TradingView Pine Editor의 코드를 그대로 붙여넣으세요. 대부분 자동 변환됩니다.
  </p>
)}
```

(이모지 `💡`는 DESIGN.md "이모지 금지" 정책 위반 — **Lucide LightbulbIcon으로 교체**. 아래 최종 버전:)

```tsx
{pineSource.length === 0 && (
  <p className="mb-2 flex items-center gap-1.5 text-xs text-[color:var(--text-muted)]">
    <LightbulbIcon className="size-3.5" />
    TradingView Pine Editor의 코드를 그대로 붙여넣으세요. 대부분 자동 변환됩니다.
  </p>
)}
```

**D. Monaco `⌘+S` save 바인딩 (Step 5.3 TabCode):**

`PineEditor`에 `onTriggerSave` prop 추가, `onMount`에서 `editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, onTriggerSave)`. TabCode에서 `onTriggerSave={() => dirty && update.mutate({ pine_source: source })}`.

**E. Delete success toast에 이름 포함 (Step 5.2 EditorView):**

이미 `toast.success("전략이 삭제되었습니다")` — 이름 포함으로 수정: `toast.success(\`"${strategy.name}" 전략이 삭제되었습니다\`)`.

**F. "생성 완료" → Edit 페이지 첫 방문 시 1회성 tour hint (optional, Sprint 7d+로 deferred):**

Edit 페이지 첫 방문에서 "코드 탭에서 ⌘+S로 저장, 파싱 결과 탭에서 에러 확인" 같은 Coachmark. Sprint 7c에서는 skip — 범위 팽창 방지.

---

## AI Slop Mitigation (Pass 4)

### Step 4.5 StepMethod 레이아웃 재설계 (AI 패턴 #2 회피)

3-column symmetric grid → **asymmetric: 1 primary + 2 small chips**. 대칭 깨짐으로 "지금 할 수 있는 것"이 시각적으로 지배.

`frontend/src/app/(dashboard)/strategies/new/_components/step-method.tsx` 구현 지시(**Step 4.5 code 대체**):

```tsx
import { CodeIcon, UploadIcon, LinkIcon, ChevronRightIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function StepMethod(props: {
  method: "direct" | "upload" | "url";
  onMethodChange: (m: "direct" | "upload" | "url") => void;
  onNext: () => void;
}) {
  return (
    <div>
      <h2 className="mb-1 font-display text-lg font-semibold">어떻게 전략을 등록할까요?</h2>
      <p className="mb-5 text-xs text-[color:var(--text-muted)]">
        현재는 직접 입력만 지원합니다.
      </p>

      {/* Active 옵션: full-width primary card */}
      <button
        type="button"
        onClick={() => props.onMethodChange("direct")}
        aria-pressed={props.method === "direct"}
        className="group flex w-full items-center gap-4 rounded-[var(--radius-md)] border-2 border-[color:var(--primary)] bg-[color:var(--primary-light)] p-5 text-left transition hover:border-[color:var(--primary-hover)]"
      >
        <CodeIcon className="size-8 text-[color:var(--primary)]" strokeWidth={1.5} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[color:var(--text-primary)]">Pine Script 직접 입력</span>
            <Badge variant="secondary" className="text-[0.65rem]">권장</Badge>
          </div>
          <p className="mt-0.5 text-xs text-[color:var(--text-secondary)]">
            TradingView에서 코드를 복사해 붙여넣습니다. 실시간 파싱으로 즉시 확인.
          </p>
        </div>
        <ChevronRightIcon className="size-5 text-[color:var(--primary)] transition group-hover:translate-x-0.5" />
      </button>

      {/* Disabled 옵션: 1줄 chip row */}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[color:var(--text-muted)]">
        <span>곧 지원:</span>
        <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] px-2 py-1">
          <UploadIcon className="size-3" />.pine 파일 업로드
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] px-2 py-1">
          <LinkIcon className="size-3" />TradingView URL
        </span>
        <span className="text-[0.65rem] opacity-70">Sprint 7d+</span>
      </div>

      <div className="mt-8 flex justify-end">
        <Button onClick={props.onNext}>다음 단계 →</Button>
      </div>
    </div>
  );
}
```

**왜 이게 AI slop을 피하는가:**
- 대칭 3-card grid → 대칭 깨짐 (1 primary + chip row)
- "icon-circle" 패턴 없음 (raw icon만)
- 유일 active CTA가 명확 (Krug "Don't make me think")
- disabled 옵션을 "곧 지원" chip으로 축소 → 미래 약속이지 현재 선택지 아님을 명시

### Copy Cut (Krug omit-omit-omit)

| 위치 | 기존 | 수정 후 | 절감 |
|------|-----|--------|-----|
| `NewStrategyPage` sub | "Pine Script 전략을 업로드하고 자동 파싱을 진행합니다" | "Pine Script 전략 등록" | 22자→11자 |
| Step 2 label kbd hint | "⌘+Enter 즉시 파싱" | "⌘+Enter 즉시 파싱" | 유지 (기능 hint는 짧아서 보존) |
| Step 3 submit button | "전략 생성" / "생성 중..." | 유지 | OK |
| List page sub | "Pine Script 전략을 관리하고 백테스트하세요" | "Pine Script 전략 관리" | 22자→11자 |

Step 4.3 `NewStrategyPage` 코드 + Step 3.2 `StrategyList` 코드의 sub 문구 위 값으로 교체.

---

## Design System Reconciliation (Pass 5)

DESIGN.md가 SSOT. shadcn/ui 기본값과 충돌하는 4개 지점을 **Task 1 Step 1.3 완료 직후** 반드시 오버라이드.

### 1. 컨테이너 max-width 보정

| 페이지 | 플랜 원안 | DESIGN.md § | 수정 |
|-------|---------|------------|-----|
| `/strategies` list | `max-w-[1200px]` | §4.2 `1200px` 기본 | 유지 ✅ |
| `/strategies/new` wizard | `max-w-[900px]` | §4.2 narrow 720 또는 dash 1000 | **`max-w-[900px]`는 DESIGN.md 외부 값** → 의도적 예외로 처리. 이유: Step 3 metadata form 크기 감안 + 프로토타입 07 원안 `max-width: 900px`. 플랜 유지하되 "DESIGN.md 예외: wizard 전용" 주석 추가. |
| `/strategies/[id]/edit` | `max-w-[1400px]` | §4.2 없음 | **`max-w-[1200px]`로 축소** — DESIGN.md §4.2 기본 컨테이너. 1400은 임의값. |

### 2. Breakpoint 재정렬 (Tailwind v4 @theme)

`frontend/src/app/globals.css`의 `@theme` 블록에 DESIGN.md §4.3 기준 커스텀 breakpoint 등록:

```css
@theme {
  --breakpoint-sm: 375px;   /* DESIGN.md mobile min */
  --breakpoint-md: 768px;   /* DESIGN.md tablet */
  --breakpoint-lg: 1024px;  /* DESIGN.md desktop compact */
  --breakpoint-xl: 1200px;  /* DESIGN.md container max */
  --breakpoint-2xl: 1440px; /* DESIGN.md full desktop */
}
```

**주의:** shadcn/ui 기본 breakpoint와 다름. 플랜 코드의 `md:/xl:` 클래스는 위 커스텀 기준으로 매핑됨 — `xl:grid-cols-3`는 1200px↑에서 활성. 의미는 "데스크톱 compact↑에서 3열".

### 3. Button 터치 타겟 48px

shadcn Button 기본 `h-10(40px)` → DESIGN.md §7.1 `min-height: 48px`. **두 가지 옵션 중 1택:**

- **Option A (권장):** shadcn `Button` 컴포넌트의 `buttonVariants` size 토큰 수정 — `default`를 `h-12 px-6` (48px)로 변경. 전역 영향. `frontend/src/components/ui/button.tsx`에서 직접 수정.
- **Option B:** 플랜의 primary CTA 전부에 `size="lg"` prop 명시. 로컬 영향. shadcn `lg`는 `h-11` (44px) — DESIGN.md 48px 여전히 미달 → `lg` 자체도 수정 필요.

→ **Option A 채택.** `button.tsx`의 `size.default` → `h-12 px-6 text-sm`로 수정, `size.lg` → `h-14 px-8 text-base`로 상향. `size.sm`은 `h-9 px-3`로 유지 (보조 액션용).

### 4. Input 터치 타겟 48px

shadcn Input 기본 `h-10` → DESIGN.md §7.3 `min-height: 48px`. `frontend/src/components/ui/input.tsx`의 루트 className에서 `h-10` → `h-12` 교체. Textarea는 `min-h-[60px]` → `min-h-[96px]` (3줄 기본).

### 5. 구현 시점

위 4개 오버라이드는 **Task 1 Step 1.4 바로 뒤**에 **Step 1.4b (NEW) Design System Override** 로 삽입. shadcn CLI가 컴포넌트 생성 직후 한 번에 처리 — 나중에 건드리면 각 컴포넌트 코드가 여러 차 재편되며 drift 발생.

### 6. 검증

Task 1 Step 1.8 smoke 시 DevTools Elements에서 임의 Button/Input의 computed `min-height` 확인 → `48px` 확증. Lighthouse a11y audit 실행 (Tap targets are sized appropriately) 통과 확인.

---

## Responsive & A11y (Pass 6)

### Responsive 뷰포트별 의도

| 뷰포트 | Breakpoint | `/strategies` | `/strategies/new` | `/strategies/[id]/edit` |
|-------|------------|---------------|-------------------|--------------------------|
| Mobile S | <375px | 카드 1열, `px-4`, 필터 chip 2줄 | Stepper 세로 stack, Monaco `h-[300px]`, 파싱 panel 아래로 내림 | 탭 가로 스크롤, Monaco `h-[320px]`, 우측 panel은 탭 하위로 이동 |
| Mobile | 375~767px | 카드 1열, 테이블 뷰 토글 **숨김** (useless) | 위와 동일. 액션 버튼 full-width | 헤더 액션을 kebab 메뉴로 접기 |
| Tablet | 768~1023px | 카드 2열, 테이블 뷰 토글 표시 | Monaco + 파싱 panel 수직 stack | 탭 content 단일 컬럼, Monaco `h-[400px]` |
| Desktop | 1024~1199px | 카드 2열, sticky 필터 바 | 기본 레이아웃 | `grid-cols-[1fr_280px]` 우측 panel 좁게 |
| Desktop XL | 1200~1439px | 카드 3열 | 기본 | `grid-cols-[1fr_320px]` |
| Desktop 2XL | ≥1440px | 카드 3열, max-width 1200px centered | 동일 | 동일 |

**구체 구현 지시 (플랜 코드 패치):**

- **List page (Step 3.2):** 현재 `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` 유지. 테이블 뷰 토글 — `lg:flex hidden` 처리 (<1024px에서 안 보임). 모바일에서는 그리드 강제.
- **Wizard Stepper (Step 4.4):** 모바일 세로 stack — `flex-col md:flex-row`. 원형 번호는 유지, 라벨 줄바꿈 허용.
- **Step 2 에디터 (Step 4.7):** Monaco `height={height ?? 400}` → 뷰포트 adaptive: `use window.matchMedia("(max-width: 767px)")` 또는 단순히 `className="h-[300px] md:h-[400px] lg:h-[520px]"` wrapper (Monaco는 100% 상속).
- **Edit view (Step 5.2):** `grid-cols-1 lg:grid-cols-[1fr_320px]` — 모바일은 세로 stack, 데스크톱 sidebar.
- **Edit action header (Step 5.2):** 모바일에서 `[백테스트 실행] [삭제]` 두 버튼을 DropdownMenu "⋯" 아이콘 하나로 접기. `hidden md:flex` / `md:hidden`.

### A11y 추가 사양

1. **Skip link** (WCAG 2.4.1 Bypass Blocks):

   `frontend/src/app/(dashboard)/layout.tsx` 또는 `DashboardShell.tsx` 최상단에 추가 (`<body>` 직후):

   ```tsx
   <a
     href="#main-content"
     className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-md focus:bg-[color:var(--primary)] focus:px-4 focus:py-2 focus:text-white"
   >
     본문으로 바로가기
   </a>
   ```

   각 라우트 page.tsx의 main container에 `id="main-content"` 추가.

2. **키보드 단축키 도움말** (? key):

   Sprint 7c 범위: **간단한 toast로 대체**. 각 페이지의 ⌘+S / ⌘+Enter 기능 존재는 버튼 툴팁 `title` 속성으로 표시. 공식 help dialog는 Sprint 7d+.

3. **Landmark roles 검증:**
   - `<DashboardShell>` 사이드바에 `<nav aria-label="메인 내비게이션">` 이미 존재 추정 — 구현 시 확인.
   - 각 page.tsx의 main content를 `<main id="main-content" aria-label="{페이지명}">`로 감싸기.
   - `/strategies/[id]/edit`의 탭 영역은 shadcn `<Tabs>` 자동 `role="tablist"` — ✅.

4. **Reduced motion 전역 확증:**

   `globals.css`의 `@media (prefers-reduced-motion: reduce)` 블록이 이미 있는지 확인 (Stage 2 DESIGN.md §8.3). 없으면 추가. 신규 `scale-in` keyframe (Pass 3 microanimation)도 이 블록에 의해 자동 억제되는지 확인.

5. **폼 에러 연결** (WCAG 1.3.1):
   - shadcn `<FormField>`는 `<FormMessage>`에 자동 `aria-describedby` 연결 — ✅ 기본 동작 확인만.

6. **Dialog focus trap + restoration** (WCAG 2.4.3):
   - shadcn `<Dialog>` 기본 동작. 단 `DeleteDialog`의 phase 전환(`confirm` → `archive-fallback`) 시 포커스가 첫 interactive로 이동하도록 phase 변경 시점에 `queueMicrotask(() => dialogRef.querySelector('button')?.focus())` 추가 고려. Sprint 7c 범위: shadcn 기본값으로 충분, phase 전환 시 포커스 손실은 QA에서 확인.

7. **색상 대비 검증 (WCAG AA 4.5:1):**
   - 신규 `data-tone="warning"` ( `#92400E` on `#FEF3C7` ) 대비비 7.3:1 → 통과.
   - DESIGN.md의 light/dark 전부 검증됨 (DESIGN.md §9) — 재확인 불필요.

### Step 5.7 E2E smoke checklist에 추가할 a11y 항목

- [ ] Tab 키로 skip link 포커스 → Enter → #main-content로 이동 확인
- [ ] Dialog 열림 → Tab 순환이 dialog 내부에만 머무름 (focus trap)
- [ ] Dialog 닫힘 → 이전 포커스 element로 복귀
- [ ] VoiceOver (Mac): `/strategies` 방문 → "내 전략, 제목 레벨 1, 다음: 필터 바" 읽힘
- [ ] Chrome Lighthouse a11y score ≥ 95
- [ ] 모바일 뷰포트 375×667에서 Monaco 편집 가능 (2-finger 스크롤 정상)

---

## Unresolved Design Decisions (Pass 7 — resolved)

Design review 중 확정.

| # | 질문 | 결정 | 이유 |
|---|------|------|------|
| P7-1 | Wizard 중단 시 draft 보존 | localStorage auto-save (500ms debounce) + 재진입 복원 다이얼로그 | DB 스키마 무변경 + pure FE 범위 유지. P1 (Pass 1 참조) |
| P7-2 | Step 1 method select 레이아웃 | Asymmetric: 1 primary full-card + 2 small "곧 지원" chips | AI slop 패턴 #2 회피. Krug "Don't make me think". P4 참조 |
| P7-3 | DESIGN.md 토큰 vs shadcn 기본 | shadcn Button/Input을 48px로 오버라이드, Tailwind breakpoint를 DESIGN.md §4.3 매핑 | DESIGN.md = SSOT. P5 참조 |
| P7-4 | Card ⋮ 메뉴 disabled 항목 | 유지 — "복제/공유 (Sprint 7d+)" visible | 로드맵 투명성 > AI slop risk. 유저가 시각적으로 미래 기능 인지 |
| P7-5 | Stepper 뒤로가기 시 completed 상태 | 영구 유지 (한번 완료한 step은 뒤로가도 녹색 유지) | State 관리 간단 + "유효한 입력 완료" 피드백 지속 |
| P7-6 | Tag 입력 UX | comma-split 유지 (Sprint 7c), chip input은 7d+ 후보 | Time box 내 구현 간단. 파워 유저 마찰은 7d+로 이관 |
| P7-7 | Monaco autocomplete 등록 | **명시적 미등록** — Pine Monarch는 syntax highlight만 | 자동완성은 full Pine grammar가 필요. Sprint 7c 범위 밖. `pine-language.ts`에 `// autocomplete: Sprint 7d+` 주석 명시 |
| P7-8 | Symbol/Timeframe 포맷 validation | maxLength만 (백엔드 정책 따름). 거래소별 포맷은 Sprint 7b Trading Sessions에서 처리 | 현재 거래소 선택이 없음. 포맷은 context 의존 |
| P7-9 | localStorage draft + 유저 전환 시 노출 | **AS-IS 허용** — draft key에 user_id를 섞지 않음. 유저 전환은 동일 브라우저 = 동일 사용자 가정 | 동일 장비 공유 시나리오는 본 앱의 target use case 아님. Sprint 7d+에서 Clerk session 만료 시 auto-clear 추가 |
| P7-10 | Save conflict (OCC) | Sprint 7c는 30s refetchInterval + dirty state warning 토스트 | 본격 OCC(ETag / If-Unmodified-Since)는 백엔드 변경 필요 → Sprint 7d+ |

---

## NOT in Scope (Sprint 7c 명시적 제외)

아래 design 관련 항목은 검토 후 **의도적 deferred**. SDD 실행 중 "추가하면 좋겠다" 유혹 발생 시 이 목록 참조.

1. **Coachmark tour** — first-time edit 페이지 단축키 안내 오버레이. 범위 팽창 우려.
2. **Bottom sheet dialog (mobile)** — DeleteDialog가 모바일에서 bottom sheet로 전환. shadcn 기본 center dialog로 7c는 충분.
3. **Chip-style tag input** — comma-split로 감내.
4. **Keyboard shortcut help dialog (?)** — 툴팁으로 감내.
5. **Strategy clone / share** — 메뉴 항목만 disabled로 노출, 기능 0.
6. **Monaco autocomplete** — 명시적 skip (P7-7).
7. **Full OCC save conflict** — Sprint 7c는 notification만, 백엔드 ETag는 7d+.
8. **Analytics panel backtest history** (01 prototype 우측 "최근 백테스트" 카드) — `/backtests` 탭 연결은 Sprint 7b.
9. **전략 타임프레임 pill 라디오** (01 prototype의 6-option TF pills) — 단순 text input으로 축소.
10. **거래소 드롭다운** — 편집 페이지 우측 panel. Sprint 7b Trading Sessions와 함께.

---

## What Already Exists (재사용)

Sprint 7c가 **재구현 금지**하고 기존 자산을 써야 할 것들:

1. **DESIGN.md §2~§13** — 색상/타이포/간격/쉐도우/App Shell 토큰 전부. 하드코딩 금지.
2. **`DashboardShell`** (`frontend/src/components/layout/dashboard-shell.tsx`) — App Shell 이미 완성. Sprint 7c는 Sidebar nav items만 추가.
3. **`apiFetch<T>()`** (`frontend/src/lib/api-client.ts`) — HTTP 래퍼. method/body 지원 확장만.
4. **React Query 패턴** — `/trading` 3-panel에서 검증된 `useQuery` + refetchInterval + Zod 검증 구조. Query key factory 스타일.
5. **`useUiStore`** (Zustand) — sidebar 토글 전역 상태. 재사용.
6. **Clerk `useAuth().getToken()`** — JWT 취득. 새 패턴 도입 금지.
7. **프로토타입 06/07/01 HTML** — 시각 기준. CSS 클래스명은 shadcn+Tailwind로 번역.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR (FULL) | score: 5/10 → 8.7/10, 10 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** DESIGN CLEARED — 7 pass 완료, 10 decision 해결. `/plan-eng-review`는 본 plan에 아키텍처 관점 검증이 필요하면 권장 (선택). Sprint 7a가 pure BE였던 것과 달리 7c는 FE-only로 architecture 단순 → eng review는 optional.


---

## File Structure

### Create (신규 파일)

#### Strategy feature (FSD Lite)
- `frontend/src/features/strategy/schemas.ts` — Zod 스키마 (backend `StrategyResponse` / `ParsePreviewResponse` / `CreateStrategyRequest` 등 런타임 검증)
- `frontend/src/features/strategy/api.ts` — `listStrategies`, `getStrategy`, `createStrategy`, `updateStrategy`, `deleteStrategy`, `parseStrategy` CRUD 함수 (Clerk JWT attach)
- `frontend/src/features/strategy/hooks.ts` — React Query 훅 (`useStrategies`, `useStrategy`, `useCreateStrategy`, `useUpdateStrategy`, `useDeleteStrategy`, `useParseStrategy`) + query key factory
- `frontend/src/features/strategy/utils.ts` — parse status → label/color 매핑, debounce 유틸 등 pure function

#### Pages (라우트)
- `frontend/src/app/(dashboard)/strategies/page.tsx` — 목록 페이지 (Server Component shell + Client list)
- `frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx` — Client list + 필터/정렬/페이지네이션
- `frontend/src/app/(dashboard)/strategies/_components/strategy-card.tsx` — 그리드 뷰 카드
- `frontend/src/app/(dashboard)/strategies/_components/strategy-table.tsx` — 목록 뷰 테이블
- `frontend/src/app/(dashboard)/strategies/_components/strategy-empty-state.tsx` — 빈 상태
- `frontend/src/app/(dashboard)/strategies/new/page.tsx` — 3-step wizard entry
- `frontend/src/app/(dashboard)/strategies/new/_components/wizard-stepper.tsx` — stepper UI
- `frontend/src/app/(dashboard)/strategies/new/_components/step-method.tsx` — Step 1 (입력 방식)
- `frontend/src/app/(dashboard)/strategies/new/_components/step-code.tsx` — Step 2 (Monaco + 실시간 파싱)
- `frontend/src/app/(dashboard)/strategies/new/_components/step-metadata.tsx` — Step 3 (메타데이터 폼 + 최종 확인)
- `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx` — 실시간 파싱 결과 패널
- `frontend/src/app/(dashboard)/strategies/[id]/edit/page.tsx` — 편집 페이지 entry (Server shell)
- `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/editor-view.tsx` — Client wrapper + 탭 상태
- `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-code.tsx` — 코드 탭 (Monaco)
- `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx` — 파싱 결과 탭
- `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-metadata.tsx` — 메타데이터 탭 (react-hook-form)
- `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/delete-dialog.tsx` — 삭제 확인 + 409 archive 분기

#### Monaco
- `frontend/src/components/monaco/pine-language.ts` — `registerPineLanguage()` (Monarch tokenizer + `vs-dark` 커스텀 테마)
- `frontend/src/components/monaco/pine-editor.tsx` — `@monaco-editor/react` 래퍼 (Pine 언어 + JetBrains Mono + 로딩 상태)

#### shadcn/ui (CLI가 자동 생성)
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/card.tsx`
- `frontend/src/components/ui/tabs.tsx`
- `frontend/src/components/ui/dialog.tsx`
- `frontend/src/components/ui/select.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/form.tsx`
- `frontend/src/components/ui/dropdown-menu.tsx`
- `frontend/src/components/ui/badge.tsx`
- `frontend/src/components/ui/label.tsx`
- `frontend/src/components/ui/textarea.tsx`
- `frontend/src/components/ui/sonner.tsx` — `<Toaster>` 프로바이더
- `frontend/components.json` — shadcn 설정 (CLI가 생성)

### Modify (기존 파일)

- `frontend/package.json` — 신규 의존성 추가
- `frontend/src/components/layout/dashboard-shell.tsx` — Sidebar 네비게이션에 "전략" 링크 추가 (DESIGN.md §10.2 순서 2번)
- `frontend/src/app/layout.tsx` — `<Toaster />` (sonner) 추가
- `frontend/src/lib/api-client.ts` — (필요 시) `ApiError` 409 `strategy_has_backtests` 판별용 code 필드 노출 확인 + PUT/DELETE 메서드 지원 확인
- `frontend/src/features/strategy/index.ts` — 현재 `export {};` 빈 파일 → public re-export 추가
- `docs/TODO.md` — Sprint 7c 완료 마크, Sprint 7 Next Actions 업데이트
- `docs/dev-log/008-sprint7c-scope-decision.md` — 상태 `scope 결정 완료` → `구현 완료 (2026-04-XX)`
- `.claude/CLAUDE.md` — "현재 작업" 섹션에 Sprint 7c 항목 추가

---

## Task 1: Foundation — 패키지 설치 + shadcn init + Sidebar nav + Toaster

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/components/layout/dashboard-shell.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/components.json` (shadcn CLI가 생성)
- Create: `frontend/src/components/ui/*.tsx` (shadcn CLI가 생성, 12개)
- Create: `frontend/src/features/strategy/index.ts` (덮어쓰기)

**목표:** 후속 Task의 모든 dependency를 선행 확보. 설치/설정만 수행, 비즈니스 로직 없음.

- [ ] **Step 1.1: 브랜치 생성**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git switch main && git pull
git switch -c feat/sprint7c-strategy-ui
```

Expected: `On branch feat/sprint7c-strategy-ui`, main 기준 HEAD 일치.

- [ ] **Step 1.2: Monaco + sonner + react-hook-form 관련 peer deps 설치**

```bash
cd frontend
pnpm add @monaco-editor/react sonner
pnpm add -D @hookform/resolvers
```

Expected: `package.json` dependencies에 `@monaco-editor/react`, `sonner` 추가. devDependencies에 `@hookform/resolvers` 추가 (`react-hook-form` + `zod` 연결용).

참고: `react-hook-form`, `zod`, `@tanstack/react-query`는 이미 설치됨 (Phase 1 explore 결과).

- [ ] **Step 1.3: shadcn/ui CLI init (Tailwind v4 모드)**

```bash
cd frontend
pnpm dlx shadcn@latest init
```

프롬프트 응답:
- Style: **New York**
- Base color: **Slate** (DESIGN.md primary palette가 blue-600 + slate 계열)
- CSS variables: **Yes**

Expected: `frontend/components.json` 생성, `frontend/src/components/ui/` 디렉토리 생성, `globals.css`에 shadcn 기본 CSS 변수 섹션 추가.

**중요:** init 후 `globals.css`가 덮어써지면 **기존 DESIGN.md 토큰 섹션(Plus Jakarta Sans / Inter / JetBrains Mono 폰트 + Light/Dark 토큰 + `[data-theme="dash"]` 스코핑)을 보존**해야 함. shadcn이 추가한 `--background`, `--foreground` 등 토큰은 기존 `--bg`, `--text-primary`와 공존시키되, 후속 shadcn 컴포넌트는 `--primary`/`--destructive` 등 DESIGN.md 이름 기준으로 리매핑.

Init 직후 `globals.css`에 아래처럼 DESIGN.md 토큰을 shadcn 기본값 위에 **덮어쓰기**:

```css
/* globals.css 내부, shadcn @layer base :root 아래 추가 */
:root {
  /* shadcn 기본값을 DESIGN.md 토큰으로 재정의 */
  --background: #FAFBFC;         /* = --bg */
  --foreground: #0F172A;         /* = --text-primary */
  --primary: #2563EB;            /* DESIGN.md primary */
  --primary-foreground: #FFFFFF;
  --destructive: #DC2626;        /* DESIGN.md destructive */
  --destructive-foreground: #FFFFFF;
  --border: #E2E8F0;             /* DESIGN.md border */
  --ring: #2563EB;               /* focus ring */
  --card: #FFFFFF;
  --card-foreground: #0F172A;
  --muted: #F1F5F9;              /* bg-alt */
  --muted-foreground: #94A3B8;   /* text-muted */
  --radius: 10px;                /* DESIGN.md radius-md */
}
```

- [ ] **Step 1.4: shadcn 9 컴포넌트 + label/textarea/sonner add**

```bash
cd frontend
pnpm dlx shadcn@latest add button card tabs dialog select input form dropdown-menu badge label textarea sonner
```

Expected: `frontend/src/components/ui/` 에 12개 `.tsx` 파일 생성. `sonner.tsx`는 `<Toaster />` 프로바이더 wrapper.

- [ ] **Step 1.5: 루트 레이아웃에 Toaster 추가**

`frontend/src/app/layout.tsx` 수정. 기존 `<html>/<body>` 구조 유지하고 `<Toaster />`만 `body` 내부 최하단에 추가:

```tsx
import { Toaster } from "@/components/ui/sonner";

// 기존 RootLayout 함수 내부 return 문 수정
return (
  <html lang="ko">
    <body className={...}>
      <ClerkProvider>
        <QueryProvider>
          {children}
          <Toaster position="top-center" richColors closeButton />
        </QueryProvider>
      </ClerkProvider>
    </body>
  </html>
);
```

**주의:** 기존 `ClerkProvider`, `QueryProvider` 배치는 현재 코드 확인 후 보존. Toaster는 항상 가장 바깥쪽(모달보다 위 z-index).

- [ ] **Step 1.6: Sidebar에 "전략" 네비게이션 링크 추가**

`frontend/src/components/layout/dashboard-shell.tsx` 수정. 현재 주석으로 비어있는 nav 섹션(explore 결과)을 DESIGN.md §10.2 순서대로 채우되, **Sprint 7c에서 활성화는 전략/트레이딩 2개만** (나머지는 `disabled` 스타일 + `aria-disabled="true"`).

```tsx
// dashboard-shell.tsx 내부 sidebar <nav> 안에 배치
const navItems = [
  { href: "/dashboard", label: "대시보드", icon: HomeIcon, disabled: true },
  { href: "/strategies", label: "전략", icon: CodeIcon, disabled: false },
  { href: "/templates", label: "템플릿", icon: LayersIcon, disabled: true },
  { href: "/backtests", label: "백테스트", icon: BarChartIcon, disabled: true },
  { href: "/trading", label: "트레이딩", icon: ZapIcon, disabled: false },
  { href: "/exchanges", label: "거래소", icon: GlobeIcon, disabled: true },
] as const;
```

`aria-current="page"` 는 `usePathname().startsWith(item.href)`로 판정. disabled 항목은 `<span>` 렌더 + `cursor-not-allowed opacity-50` + tooltip "곧 출시".

아이콘은 `lucide-react`가 이미 설치돼있는지 `package.json` 먼저 확인. 없으면 `pnpm add lucide-react` 선행.

- [ ] **Step 1.7: features/strategy 진입점 재생성**

`frontend/src/features/strategy/index.ts` 덮어쓰기:

```ts
// Sprint 7c: Strategy domain public surface.
export * from "./schemas";
export * from "./api";
export * from "./hooks";
```

schemas/api/hooks 파일은 Task 2에서 생성. 이 시점에는 TypeScript 컴파일 에러가 나므로 index.ts는 **Task 2 완료 후 작성**해도 되지만, 파일 경로를 plan에서 고정해두기 위해 신규 생성 시점에 skeleton으로 만들고 Task 2에서 본 구현을 채운다. Step 2.0을 참조.

- [ ] **Step 1.8: 타입 체크 + 린트 + 개발 서버 smoke**

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm dev
```

브라우저에서 `http://localhost:3000/trading` 접속 → 기존 3 panel 정상 렌더링 + Sidebar에 "전략"/"트레이딩" 2개가 활성 상태인지 시각 확인. "전략" 링크 클릭 시 `/strategies` 404 (Task 3 전이므로 정상).

Expected: tsc/lint clean, 개발 서버 에러 없음, 기존 trading 패널 regression 없음.

- [ ] **Step 1.9: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add frontend/package.json frontend/pnpm-lock.yaml frontend/components.json frontend/src/components/ui/ frontend/src/app/layout.tsx frontend/src/components/layout/dashboard-shell.tsx frontend/src/features/strategy/index.ts frontend/src/app/globals.css
git commit -m "feat(frontend): Sprint 7c T1 — Monaco/shadcn/sonner 설치 + Sidebar에 전략 링크 + Toaster"
```

---

## Task 2: API client + Zod schemas + React Query hooks

**Files:**
- Create: `frontend/src/features/strategy/schemas.ts`
- Create: `frontend/src/features/strategy/api.ts`
- Create: `frontend/src/features/strategy/hooks.ts`
- Create: `frontend/src/features/strategy/utils.ts`
- Modify: `frontend/src/features/strategy/index.ts` (Task 1에서 skeleton만 만든 경우 본 구현)

**목표:** `/strategies` 라우트 이하 모든 페이지가 이 모듈 하나로 backend Strategy API를 호출. Clerk JWT는 `useAuth().getToken()` → `apiFetch({ token })` 경로로 전달.

**Reference:** Sprint 6 `/trading` 페이지의 `useQuery` + Zod 패턴 그대로 (Phase 1 explore agent 보고). `lib/api-client.ts`의 `apiFetch<T>()`와 `ApiError` 재사용.

- [ ] **Step 2.1: Zod schemas 생성 (backend 명세 완전 매칭)**

Create `frontend/src/features/strategy/schemas.ts`:

```ts
import { z } from "zod";

// Backend ParseStatus / PineVersion enum
export const ParseStatusSchema = z.enum(["ok", "unsupported", "error"]);
export type ParseStatus = z.infer<typeof ParseStatusSchema>;

export const PineVersionSchema = z.enum(["v4", "v5"]);
export type PineVersion = z.infer<typeof PineVersionSchema>;

// Backend ParseError 매칭
export const ParseErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  line: z.number().int().nullable(),
});
export type ParseError = z.infer<typeof ParseErrorSchema>;

// POST /strategies/parse 응답
export const ParsePreviewResponseSchema = z.object({
  status: ParseStatusSchema,
  pine_version: PineVersionSchema,
  warnings: z.array(z.string()).default([]),
  errors: z.array(ParseErrorSchema).default([]),
  entry_count: z.number().int().default(0),
  exit_count: z.number().int().default(0),
});
export type ParsePreviewResponse = z.infer<typeof ParsePreviewResponseSchema>;

// Strategy 상세 응답 (GET/POST/PUT)
export const StrategyResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  pine_source: z.string(),
  pine_version: PineVersionSchema,
  parse_status: ParseStatusSchema,
  // backend가 JSON으로 저장한 list[dict] — UI에서는 ParseError로 좁혀 사용.
  parse_errors: z.array(z.record(z.string(), z.unknown())).nullable(),
  timeframe: z.string().nullable(),
  symbol: z.string().nullable(),
  tags: z.array(z.string()).default([]),
  is_archived: z.boolean(),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
});
export type StrategyResponse = z.infer<typeof StrategyResponseSchema>;

// 목록 응답 (pine_source 제외)
export const StrategyListItemSchema = StrategyResponseSchema.omit({
  pine_source: true,
  description: true,
});
export type StrategyListItem = z.infer<typeof StrategyListItemSchema>;

export const StrategyListResponseSchema = z.object({
  items: z.array(StrategyListItemSchema),
  total: z.number().int(),
  page: z.number().int(),
  limit: z.number().int(),
  total_pages: z.number().int(),
});
export type StrategyListResponse = z.infer<typeof StrategyListResponseSchema>;

// Create/Update request — FE form에서 사용
export const CreateStrategyRequestSchema = z.object({
  name: z.string().min(1).max(120),
  description: z.string().max(2000).nullable().optional(),
  pine_source: z.string().min(1),
  timeframe: z.string().max(16).nullable().optional(),
  symbol: z.string().max(32).nullable().optional(),
  tags: z.array(z.string()).default([]),
});
export type CreateStrategyRequest = z.infer<typeof CreateStrategyRequestSchema>;

export const UpdateStrategyRequestSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  description: z.string().max(2000).nullable().optional(),
  pine_source: z.string().min(1).optional(),
  timeframe: z.string().max(16).nullable().optional(),
  symbol: z.string().max(32).nullable().optional(),
  tags: z.array(z.string()).optional(),
  is_archived: z.boolean().optional(),
});
export type UpdateStrategyRequest = z.infer<typeof UpdateStrategyRequestSchema>;

// 목록 쿼리 파라미터
export const StrategyListQuerySchema = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0),
  parse_status: ParseStatusSchema.optional(),
  is_archived: z.boolean().default(false),
});
export type StrategyListQuery = z.infer<typeof StrategyListQuerySchema>;
```

- [ ] **Step 2.2: API client 생성**

Create `frontend/src/features/strategy/api.ts`:

```ts
import { apiFetch } from "@/lib/api-client";
import {
  type CreateStrategyRequest,
  type ParsePreviewResponse,
  ParsePreviewResponseSchema,
  type StrategyListQuery,
  type StrategyListResponse,
  StrategyListResponseSchema,
  type StrategyResponse,
  StrategyResponseSchema,
  type UpdateStrategyRequest,
} from "./schemas";

/**
 * Clerk JWT를 token 파라미터로 주입. 호출부는 useAuth().getToken() 결과를 넘긴다.
 * 응답은 Zod로 런타임 검증 — backend drift 즉시 탐지.
 */

export async function listStrategies(
  query: StrategyListQuery,
  token: string | null,
): Promise<StrategyListResponse> {
  const params: Record<string, string> = {
    limit: String(query.limit),
    offset: String(query.offset),
    is_archived: String(query.is_archived),
  };
  if (query.parse_status) params.parse_status = query.parse_status;

  const raw = await apiFetch<unknown>("/api/v1/strategies", {
    method: "GET",
    params,
    token: token ?? undefined,
  });
  return StrategyListResponseSchema.parse(raw);
}

export async function getStrategy(
  id: string,
  token: string | null,
): Promise<StrategyResponse> {
  const raw = await apiFetch<unknown>(`/api/v1/strategies/${id}`, {
    method: "GET",
    token: token ?? undefined,
  });
  return StrategyResponseSchema.parse(raw);
}

export async function createStrategy(
  body: CreateStrategyRequest,
  token: string | null,
): Promise<StrategyResponse> {
  const raw = await apiFetch<unknown>("/api/v1/strategies", {
    method: "POST",
    body,
    token: token ?? undefined,
  });
  return StrategyResponseSchema.parse(raw);
}

export async function updateStrategy(
  id: string,
  body: UpdateStrategyRequest,
  token: string | null,
): Promise<StrategyResponse> {
  const raw = await apiFetch<unknown>(`/api/v1/strategies/${id}`, {
    method: "PUT",
    body,
    token: token ?? undefined,
  });
  return StrategyResponseSchema.parse(raw);
}

export async function deleteStrategy(
  id: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`/api/v1/strategies/${id}`, {
    method: "DELETE",
    token: token ?? undefined,
  });
}

export async function parseStrategy(
  pine_source: string,
  token: string | null,
): Promise<ParsePreviewResponse> {
  const raw = await apiFetch<unknown>("/api/v1/strategies/parse", {
    method: "POST",
    body: { pine_source },
    token: token ?? undefined,
  });
  return ParsePreviewResponseSchema.parse(raw);
}
```

**주의:** `apiFetch` 현재 시그니처가 `method`/`body` 파라미터를 지원하는지 `lib/api-client.ts` 확인 필요. 미지원 시 Task 2 Step 2.2에서 아래 두 가지 중 하나 선택:
- (a) `apiFetch`를 method/body 지원하도록 확장 (후속 feature에서도 재사용)
- (b) 본 api.ts에서 `fetch()` 직접 호출로 fallback

권장: (a). `lib/api-client.ts`의 `apiFetch` 옵션에 `method?: "GET"|"POST"|"PUT"|"DELETE"` 기본 "GET" + `body?: unknown` 추가. JSON 직렬화 + `Content-Type: application/json` 헤더 자동 주입. 이 변경은 Sprint 6 trading 호출처에 영향 없음(기본값 GET).

- [ ] **Step 2.3: React Query 훅 생성**

Create `frontend/src/features/strategy/hooks.ts`:

```ts
"use client";

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from "@tanstack/react-query";
import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  listStrategies,
  parseStrategy,
  updateStrategy,
} from "./api";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
  StrategyListQuery,
  StrategyListResponse,
  StrategyResponse,
  UpdateStrategyRequest,
} from "./schemas";

// Query key factory — `/trading` 패턴 계승.
export const strategyKeys = {
  all: ["strategies"] as const,
  lists: () => [...strategyKeys.all, "list"] as const,
  list: (query: StrategyListQuery) => [...strategyKeys.lists(), query] as const,
  details: () => [...strategyKeys.all, "detail"] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
};

export function useStrategies(
  query: StrategyListQuery,
  options?: Omit<UseQueryOptions<StrategyListResponse>, "queryKey" | "queryFn">,
) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: strategyKeys.list(query),
    queryFn: async () => listStrategies(query, await getToken()),
    staleTime: 30_000,
    ...options,
  });
}

export function useStrategy(id: string | undefined) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: id ? strategyKeys.detail(id) : ["strategies", "detail", "disabled"],
    queryFn: async () => getStrategy(id!, await getToken()),
    enabled: Boolean(id),
  });
}

export function useCreateStrategy(
  options?: UseMutationOptions<StrategyResponse, Error, CreateStrategyRequest>,
) {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body) => createStrategy(body, await getToken()),
    onSuccess: (data, vars, ctx) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists() });
      options?.onSuccess?.(data, vars, ctx);
    },
    ...options,
  });
}

export function useUpdateStrategy(
  id: string,
  options?: UseMutationOptions<StrategyResponse, Error, UpdateStrategyRequest>,
) {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body) => updateStrategy(id, body, await getToken()),
    onSuccess: (data, vars, ctx) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists() });
      qc.setQueryData(strategyKeys.detail(id), data);
      options?.onSuccess?.(data, vars, ctx);
    },
    ...options,
  });
}

export function useDeleteStrategy(
  options?: UseMutationOptions<void, Error, string>,
) {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id) => deleteStrategy(id, await getToken()),
    onSuccess: (data, id, ctx) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists() });
      qc.removeQueries({ queryKey: strategyKeys.detail(id) });
      options?.onSuccess?.(data, id, ctx);
    },
    ...options,
  });
}

export function useParseStrategy(
  options?: UseMutationOptions<ParsePreviewResponse, Error, string>,
) {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (pine_source) => parseStrategy(pine_source, await getToken()),
    ...options,
  });
}
```

- [ ] **Step 2.4: utils — parse status helpers + debounce hook**

Create `frontend/src/features/strategy/utils.ts`:

```ts
import { useEffect, useState } from "react";
import type { ParseStatus } from "./schemas";

/** parse_status → UI 라벨/배지 색상 매핑 */
export const PARSE_STATUS_META: Record<
  ParseStatus,
  { label: string; tone: "success" | "warning" | "destructive" }
> = {
  ok: { label: "파싱 성공", tone: "success" },
  unsupported: { label: "미지원", tone: "warning" },
  error: { label: "파싱 실패", tone: "destructive" },
};

/** 값이 `delayMs` 동안 변하지 않을 때만 업데이트되는 debounced 값. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

/** DELETE 응답이 409 strategy_has_backtests인지 판별 */
export function isStrategyHasBacktestsError(err: unknown): boolean {
  // ApiError는 lib/api-client.ts 정의. status + code 노출 확인 필요.
  if (!err || typeof err !== "object") return false;
  const e = err as { status?: number; code?: string };
  return e.status === 409 && e.code === "strategy_has_backtests";
}
```

**주의:** `ApiError`의 `code` 필드가 아직 노출되지 않았다면 `lib/api-client.ts`에서 응답 body의 `code` 필드를 `ApiError` 인스턴스에 저장하도록 확장. FastAPI 에러 본문은 `{ detail: { code, ... } }` 또는 `{ code, detail }` 형태 — backend `exceptions.py` 확인 후 매칭.

- [ ] **Step 2.5: 타입 체크 + 린트**

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
```

Expected: clean. `useDebouncedValue` / `strategyKeys` / `isStrategyHasBacktestsError` 등 미사용 export는 다음 Task에서 사용될 예정이므로 lint rule `no-unused-exports`가 켜져있으면 예외 처리.

- [ ] **Step 2.6: Manual smoke — 브라우저 DevTools에서 직접 호출**

개발 서버 구동 후 DevTools Console에서:

```js
// 로그인 상태에서
const token = await window.Clerk.session.getToken();
const r = await fetch("/api/v1/strategies?limit=20&offset=0&is_archived=false", {
  headers: { Authorization: `Bearer ${token}` },
});
console.log(r.status, await r.json());
```

Expected: `200`, `{ items: [], total: 0, ... }` (또는 기존 전략 있으면 그대로).
이 단계는 backend 배선 검증용 (Clerk JWT → backend dependency까지 정상 통과 확인).

- [ ] **Step 2.7: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add frontend/src/features/strategy/ frontend/src/lib/api-client.ts
git commit -m "feat(frontend): Sprint 7c T2 — Strategy Zod 스키마 + apiFetch 기반 CRUD + React Query 훅"
```

---

## Task 3: `/strategies` 목록 페이지

**Files:**
- Create: `frontend/src/app/(dashboard)/strategies/page.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/_components/strategy-card.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/_components/strategy-table.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/_components/strategy-empty-state.tsx`

**Reference prototype:** `docs/prototypes/06-strategies-list.html` — 그리드/목록 뷰 토글, 상태 필터 chips, 정렬 드롭다운, 페이지네이션, 카드(이름/심볼/TF/parse_status 배지/태그/수정 시간/액션 메뉴), 빈 상태(환영 일러스트 + CTA 2개).

**Interaction ref:** `INTERACTION_SPEC.md` §06 — 케밥 메뉴(복제/삭제/보관), 카드 클릭 → `/strategies/[id]/edit`, "+ 새 전략" → `/strategies/new`, 페이지네이션은 실제 쿼리 (offset/limit).

- [ ] **Step 3.1: Server entry page**

Create `frontend/src/app/(dashboard)/strategies/page.tsx`:

```tsx
import type { Metadata } from "next";
import { StrategyList } from "./_components/strategy-list";

export const metadata: Metadata = {
  title: "전략 | QuantBridge",
};

export default function StrategiesPage() {
  return <StrategyList />;
}
```

서버 컴포넌트는 metadata만. 데이터 fetching은 Client에서 React Query (Sprint 6 `/trading` 패턴 계승 — Phase 1 explore 결론).

- [ ] **Step 3.2: StrategyList Client wrapper**

Create `frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { PlusIcon, LayoutGridIcon, ListIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useStrategies } from "@/features/strategy/hooks";
import type { ParseStatus, StrategyListQuery } from "@/features/strategy/schemas";
import { StrategyCard } from "./strategy-card";
import { StrategyTable } from "./strategy-table";
import { StrategyEmptyState } from "./strategy-empty-state";

const PAGE_SIZE = 20;
type ViewMode = "grid" | "list";
type StatusFilter = "all" | ParseStatus | "archived";

export function StrategyList() {
  const [view, setView] = useState<ViewMode>("grid");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);

  const query = useMemo<StrategyListQuery>(() => {
    const q: StrategyListQuery = {
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
      is_archived: status === "archived",
    };
    if (status === "ok" || status === "unsupported" || status === "error") {
      q.parse_status = status;
    }
    return q;
  }, [page, status]);

  const { data, isLoading, isError, refetch } = useStrategies(query);

  if (isError) {
    return (
      <section className="p-8">
        <p className="text-destructive">전략 목록을 불러오지 못했습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          다시 시도
        </Button>
      </section>
    );
  }

  const totalPages = data?.total_pages ?? 0;
  const isEmpty = !isLoading && (data?.items.length ?? 0) === 0 && page === 0 && status === "all";

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      {/* 헤더 */}
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-[color:var(--text-primary)]">
            내 전략
          </h1>
          <p className="text-sm text-[color:var(--text-secondary)]">
            Pine Script 전략을 관리하고 백테스트하세요
          </p>
        </div>
        <Button asChild>
          <Link href="/strategies/new">
            <PlusIcon className="size-4" />새 전략
          </Link>
        </Button>
      </header>

      {/* 필터 / 뷰 토글 */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <FilterChips value={status} onChange={(s) => { setStatus(s); setPage(0); }} />
        <div className="ml-auto flex items-center gap-2">
          <Select defaultValue="updated_desc">
            <SelectTrigger className="h-9 w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated_desc">최근 수정순</SelectItem>
              <SelectItem value="updated_asc">오래된 순</SelectItem>
              <SelectItem value="name_asc">이름순</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex rounded-md border border-[color:var(--border)]">
            <Button
              size="icon"
              variant={view === "grid" ? "default" : "ghost"}
              className="rounded-r-none"
              aria-label="그리드 뷰"
              onClick={() => setView("grid")}
            >
              <LayoutGridIcon className="size-4" />
            </Button>
            <Button
              size="icon"
              variant={view === "list" ? "default" : "ghost"}
              className="rounded-l-none"
              aria-label="목록 뷰"
              onClick={() => setView("list")}
            >
              <ListIcon className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* 로딩 / 빈 상태 / 콘텐츠 */}
      {isLoading ? (
        <ListSkeleton view={view} />
      ) : isEmpty ? (
        <StrategyEmptyState />
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {data!.items.map((s) => <StrategyCard key={s.id} strategy={s} />)}
        </div>
      ) : (
        <StrategyTable items={data!.items} />
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={data!.total}
          limit={data!.limit}
          onPage={setPage}
        />
      )}
    </div>
  );
}

// ---- local sub-components (same file) ----

function FilterChips(props: {
  value: StatusFilter;
  onChange: (v: StatusFilter) => void;
}) {
  const items: Array<{ id: StatusFilter; label: string }> = [
    { id: "all", label: "모두" },
    { id: "ok", label: "파싱 성공" },
    { id: "unsupported", label: "미지원" },
    { id: "error", label: "파싱 실패" },
    { id: "archived", label: "보관됨" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => {
        const active = it.id === props.value;
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => props.onChange(it.id)}
            aria-pressed={active}
            className={
              "rounded-full border px-3 py-1 text-xs font-medium transition " +
              (active
                ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] text-[color:var(--primary)]"
                : "border-[color:var(--border)] text-[color:var(--text-secondary)] hover:bg-[color:var(--bg-alt)]")
            }
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

function Pagination(props: {
  page: number;
  totalPages: number;
  total: number;
  limit: number;
  onPage: (p: number) => void;
}) {
  const from = props.page * props.limit + 1;
  const to = Math.min((props.page + 1) * props.limit, props.total);
  return (
    <nav className="mt-8 flex items-center justify-between" aria-label="페이지 탐색">
      <p className="text-sm text-[color:var(--text-secondary)]">
        {props.total}개 중 {from}–{to} 표시
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={props.page === 0}
          onClick={() => props.onPage(props.page - 1)}
        >
          이전
        </Button>
        <span className="text-sm font-mono">
          {props.page + 1} / {props.totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={props.page + 1 >= props.totalPages}
          onClick={() => props.onPage(props.page + 1)}
        >
          다음
        </Button>
      </div>
    </nav>
  );
}

function ListSkeleton({ view }: { view: ViewMode }) {
  return (
    <div
      className={
        view === "grid"
          ? "grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3"
          : "flex flex-col gap-2"
      }
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-36 animate-pulse rounded-[var(--radius-lg)] bg-[color:var(--bg-alt)]"
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 3.3: StrategyCard (그리드 뷰 카드)**

Create `frontend/src/app/(dashboard)/strategies/_components/strategy-card.tsx`:

```tsx
"use client";

import Link from "next/link";
import { MoreVerticalIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function StrategyCard({ strategy }: { strategy: StrategyListItem }) {
  const meta = PARSE_STATUS_META[strategy.parse_status];
  return (
    <Card className="group relative transition hover:-translate-y-0.5 hover:shadow-[var(--card-shadow-hover)]">
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div className="min-w-0">
          <Link
            href={`/strategies/${strategy.id}/edit`}
            className="text-base font-semibold text-[color:var(--text-primary)] hover:text-[color:var(--primary)]"
          >
            {strategy.name}
          </Link>
          <p className="mt-1 flex items-center gap-1 font-mono text-xs text-[color:var(--text-muted)]">
            <span>{strategy.symbol ?? "심볼 없음"}</span>
            <span>·</span>
            <span>{strategy.timeframe ?? "TF 없음"}</span>
            <span>·</span>
            <span>Pine {strategy.pine_version}</span>
          </p>
        </div>
        <RowActions id={strategy.id} />
      </CardHeader>
      <CardContent className="pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" data-tone={meta.tone}>
            {meta.label}
          </Badge>
          {strategy.is_archived && <Badge variant="secondary">보관됨</Badge>}
          {strategy.tags.slice(0, 3).map((t) => (
            <Badge key={t} variant="secondary" className="font-normal">
              {t}
            </Badge>
          ))}
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between pt-0 text-xs text-[color:var(--text-muted)]">
        <time dateTime={strategy.updated_at}>
          {new Intl.DateTimeFormat("ko-KR", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }).format(new Date(strategy.updated_at))}
        </time>
        <Link
          href={`/strategies/${strategy.id}/edit`}
          className="font-medium text-[color:var(--primary)] hover:underline"
        >
          편집 →
        </Link>
      </CardFooter>
    </Card>
  );
}

function RowActions({ id }: { id: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="카드 액션 메뉴">
          <MoreVerticalIcon className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link href={`/strategies/${id}/edit`}>편집</Link>
        </DropdownMenuItem>
        <DropdownMenuItem disabled>복제 (Sprint 7d+)</DropdownMenuItem>
        <DropdownMenuItem disabled>공유 (Sprint 7d+)</DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={`/strategies/${id}/edit?action=archive`}>보관</Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={`/strategies/${id}/edit?action=delete`}>삭제</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

**주의:** 보관/삭제 액션은 query param으로 `/edit` 페이지에 위임 (T5에서 처리). 카드에서 직접 mutation 호출 안 함 — 리스트 컨텍스트에서 확인 다이얼로그 + 에러 토스트 UX가 복잡해지기 때문.

- [ ] **Step 3.4: StrategyTable (목록 뷰)**

Create `frontend/src/app/(dashboard)/strategies/_components/strategy-table.tsx`:

```tsx
"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function StrategyTable({ items }: { items: StrategyListItem[] }) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white">
      <table className="w-full text-sm">
        <thead className="bg-[color:var(--bg-alt)] text-xs uppercase tracking-wide text-[color:var(--text-secondary)]">
          <tr>
            <th scope="col" className="px-4 py-3 text-left">이름</th>
            <th scope="col" className="px-4 py-3 text-left">심볼 / TF</th>
            <th scope="col" className="px-4 py-3 text-left">상태</th>
            <th scope="col" className="px-4 py-3 text-left">수정</th>
            <th scope="col" className="sr-only">액션</th>
          </tr>
        </thead>
        <tbody>
          {items.map((s) => {
            const meta = PARSE_STATUS_META[s.parse_status];
            return (
              <tr key={s.id} className="border-t border-[color:var(--border)] hover:bg-[color:var(--bg-alt)]">
                <td className="px-4 py-3">
                  <Link href={`/strategies/${s.id}/edit`} className="font-medium hover:text-[color:var(--primary)]">
                    {s.name}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[color:var(--text-muted)]">
                  {s.symbol ?? "—"} · {s.timeframe ?? "—"} · v{s.pine_version.slice(1)}
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" data-tone={meta.tone}>{meta.label}</Badge>
                </td>
                <td className="px-4 py-3 text-xs text-[color:var(--text-muted)]">
                  {new Date(s.updated_at).toLocaleString("ko-KR")}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/strategies/${s.id}/edit`} className="text-[color:var(--primary)] hover:underline">
                    편집 →
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3.5: StrategyEmptyState**

Create `frontend/src/app/(dashboard)/strategies/_components/strategy-empty-state.tsx`:

```tsx
import Link from "next/link";
import { CodeIcon, PlusIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function StrategyEmptyState() {
  return (
    <div className="mx-auto max-w-md rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-dark)] bg-white p-10 text-center">
      <div className="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-[color:var(--primary-light)] text-[color:var(--primary)]">
        <CodeIcon className="size-7" strokeWidth={1.5} />
      </div>
      <h2 className="font-display text-lg font-semibold text-[color:var(--text-primary)]">
        첫 전략을 만들어보세요
      </h2>
      <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
        TradingView에서 작성한 Pine Script를 붙여넣거나, 미리 준비된 템플릿에서 시작할 수 있습니다.
      </p>
      <div className="mt-6 flex justify-center gap-2">
        <Button asChild>
          <Link href="/strategies/new"><PlusIcon className="size-4" />새 전략 만들기</Link>
        </Button>
        <Button variant="outline" disabled>템플릿 둘러보기 (Sprint 7d+)</Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3.6: Badge `data-tone` 스타일 (globals.css)**

`frontend/src/app/globals.css`에 아래 규칙 추가 (shadcn Badge를 DESIGN.md 톤으로 확장):

```css
[data-tone="success"] {
  background-color: var(--success-light);
  color: var(--success);
  border-color: transparent;
}
[data-tone="warning"] {
  background-color: #FEF3C7;
  color: #92400E;
  border-color: transparent;
}
[data-tone="destructive"] {
  background-color: var(--destructive-light);
  color: var(--destructive);
  border-color: transparent;
}
```

- [ ] **Step 3.7: 타입/린트 + 브라우저 smoke**

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm dev
```

브라우저:
1. `/strategies` 접속 → 빈 상태 카드 렌더링 확인 (신규 유저 가정).
2. 기존 전략이 있으면 그리드 뷰 + 카드 필드(이름/심볼/TF/parse_status 배지/tags/수정시간/편집 링크) 모두 정상.
3. 상태 필터 chip 클릭 → 네트워크 요청 `parse_status=...`가 query string에 반영되는지 DevTools Network 확인.
4. 목록 뷰 토글 → 테이블 렌더링.
5. 페이지네이션(전략 21개 이상일 때) → offset 이동 확인.
6. 반응형: 1024px 이하에서 2열, 768px 이하 1열.

- [ ] **Step 3.8: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add frontend/src/app/\(dashboard\)/strategies/ frontend/src/app/globals.css
git commit -m "feat(frontend): Sprint 7c T3 — /strategies 목록 페이지 (그리드/목록/필터/페이지네이션)"
```

---

## Task 4: `/strategies/new` 3-step Wizard (Monaco + 실시간 파싱)

**Files:**
- Create: `frontend/src/app/(dashboard)/strategies/new/page.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/new/_components/wizard-stepper.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/new/_components/step-method.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/new/_components/step-code.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/new/_components/step-metadata.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx`
- Create: `frontend/src/components/monaco/pine-language.ts`
- Create: `frontend/src/components/monaco/pine-editor.tsx`

**Reference:** `docs/prototypes/07-strategy-create.html` 구조 그대로 — stepper 3단계(업로드 방식 → 코드 입력 → 메타데이터+확인), Monaco 스타일 에디터 + 실시간 파싱 패널, ⌘+Enter 파싱 트리거.
**Interaction ref:** `INTERACTION_SPEC.md` §07 — debounce 300ms → `POST /strategies/parse`, Step 1은 직접입력만 active (파일/URL 업로드는 disabled + notice), Step 3 제출 → `POST /strategies` → `/strategies/[id]/edit` 이동.

- [ ] **Step 4.1: Pine Monarch 토크나이저 등록**

Create `frontend/src/components/monaco/pine-language.ts`:

```ts
import type { Monaco } from "@monaco-editor/react";

let _registered = false;

/** idempotent — Monaco 인스턴스에 Pine v5 언어를 1회만 등록. */
export function registerPineLanguage(monaco: Monaco): void {
  if (_registered) return;

  monaco.languages.register({ id: "pine" });

  monaco.languages.setMonarchTokensProvider("pine", {
    defaultToken: "",
    tokenPostfix: ".pine",

    keywords: [
      "strategy", "indicator", "library",
      "if", "else", "for", "to", "by", "while", "switch", "case", "default",
      "true", "false", "na",
      "var", "varip", "input",
      "and", "or", "not",
      "break", "continue", "return",
      "export", "import", "method", "type",
    ],

    // Pine v5 주요 built-in 함수 (접두어 포함). Monarch 매칭은 dotted 식별자 단위.
    functions: [
      "ta.sma", "ta.ema", "ta.wma", "ta.rsi", "ta.macd", "ta.atr", "ta.stoch",
      "ta.crossover", "ta.crossunder", "ta.highest", "ta.lowest", "ta.change",
      "strategy.entry", "strategy.exit", "strategy.close", "strategy.cancel",
      "input.int", "input.float", "input.bool", "input.string", "input.timeframe",
      "math.abs", "math.max", "math.min", "math.round",
      "plot", "plotshape", "plotchar", "hline",
      "request.security",
    ],

    operators: ["=", "==", "!=", "<", ">", "<=", ">=", "+", "-", "*", "/", "%", ":=", "?", ":"],

    symbols: /[=><!~?:&|+\-*/^%]+/,

    tokenizer: {
      root: [
        [/\/\/.*$/, "comment"],
        [/"([^"\\]|\\.)*$/, "string.invalid"],
        [/"/, { token: "string.quote", bracket: "@open", next: "@string" }],
        [/\d+\.\d+([eE][-+]?\d+)?/, "number.float"],
        [/\d+/, "number"],
        [/[a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)+/, {
          cases: {
            "@functions": "type.identifier",
            "@default": "identifier",
          },
        }],
        [/[a-zA-Z_]\w*/, {
          cases: {
            "@keywords": "keyword",
            "@default": "identifier",
          },
        }],
        [/@symbols/, {
          cases: {
            "@operators": "operator",
            "@default": "",
          },
        }],
        [/[{}()[\]]/, "@brackets"],
        [/[,.;]/, "delimiter"],
        [/\s+/, "white"],
      ],
      string: [
        [/[^\\"]+/, "string"],
        [/\\./, "string.escape"],
        [/"/, { token: "string.quote", bracket: "@close", next: "@pop" }],
      ],
    },
  });

  // DESIGN.md editor 토큰 색상 (07-strategy-create.html `--syntax-*` 변수 참조)
  monaco.editor.defineTheme("pine-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: "64748B", fontStyle: "italic" },
      { token: "keyword", foreground: "FB923C" },
      { token: "type.identifier", foreground: "60A5FA" },
      { token: "identifier", foreground: "F8FAFC" },
      { token: "string", foreground: "4ADE80" },
      { token: "string.quote", foreground: "4ADE80" },
      { token: "string.escape", foreground: "4ADE80" },
      { token: "number", foreground: "C084FC" },
      { token: "number.float", foreground: "C084FC" },
      { token: "operator", foreground: "CBD5E1" },
    ],
    colors: {
      "editor.background": "#1E293B",
      "editor.foreground": "#E2E8F0",
      "editor.lineHighlightBackground": "#0F172A",
      "editorLineNumber.foreground": "#475569",
      "editorGutter.background": "#0F172A",
    },
  });

  _registered = true;
}
```

- [ ] **Step 4.2: PineEditor 컴포넌트**

Create `frontend/src/components/monaco/pine-editor.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import type { OnMount } from "@monaco-editor/react";
import { registerPineLanguage } from "./pine-language";

// Monaco는 bundle size가 커서 client-only + dynamic import.
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  { ssr: false, loading: () => <div className="h-[400px] animate-pulse rounded-md bg-[#0F172A]" /> },
);

export interface PineEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  onTriggerParse?: () => void;
}

export function PineEditor(props: PineEditorProps) {
  const handleMount: OnMount = (editor, monaco) => {
    registerPineLanguage(monaco);
    // ⌘+Enter / Ctrl+Enter → 상위로 파싱 트리거 delegate.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      props.onTriggerParse?.();
    });
  };

  return (
    <MonacoEditor
      height={props.height ?? 400}
      defaultLanguage="pine"
      theme="pine-dark"
      value={props.value}
      onChange={(v) => props.onChange(v ?? "")}
      onMount={handleMount}
      options={{
        readOnly: props.readOnly,
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        fontSize: 13,
        lineHeight: 20,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        tabSize: 4,
        renderLineHighlight: "line",
        smoothScrolling: true,
        padding: { top: 16, bottom: 16 },
      }}
    />
  );
}
```

- [ ] **Step 4.3: Wizard page shell + 상태 머신**

Create `frontend/src/app/(dashboard)/strategies/new/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useCreateStrategy } from "@/features/strategy/hooks";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
} from "@/features/strategy/schemas";
import { WizardStepper } from "./_components/wizard-stepper";
import { StepMethod } from "./_components/step-method";
import { StepCode } from "./_components/step-code";
import { StepMetadata } from "./_components/step-metadata";

type Step = 1 | 2 | 3;
type Method = "direct" | "upload" | "url";

export default function NewStrategyPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [method, setMethod] = useState<Method>("direct");
  const [pineSource, setPineSource] = useState("");
  const [lastParse, setLastParse] = useState<ParsePreviewResponse | null>(null);

  const create = useCreateStrategy({
    onSuccess: (data) => {
      toast.success(`"${data.name}" 전략이 생성되었습니다`);
      router.push(`/strategies/${data.id}/edit`);
    },
    onError: (err) => {
      toast.error(`생성 실패: ${err.message}`);
    },
  });

  const onSubmit = (meta: Omit<CreateStrategyRequest, "pine_source">) => {
    create.mutate({ ...meta, pine_source: pineSource });
  };

  return (
    <div className="mx-auto max-w-[900px] px-6 py-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl font-bold">새 전략 만들기</h1>
        <p className="text-sm text-[color:var(--text-secondary)]">
          Pine Script 전략을 업로드하고 자동 파싱을 진행합니다
        </p>
      </header>

      <WizardStepper current={step} />

      <section className="mt-6 rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white p-8 shadow-[var(--card-shadow)]">
        {step === 1 && (
          <StepMethod
            method={method}
            onMethodChange={setMethod}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <StepCode
            pineSource={pineSource}
            onPineSourceChange={setPineSource}
            onParsed={setLastParse}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <StepMetadata
            lastParse={lastParse}
            submitting={create.isPending}
            onBack={() => setStep(2)}
            onSubmit={onSubmit}
          />
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 4.4: WizardStepper**

Create `frontend/src/app/(dashboard)/strategies/new/_components/wizard-stepper.tsx`:

```tsx
import { CheckIcon } from "lucide-react";

export function WizardStepper({ current }: { current: 1 | 2 | 3 }) {
  const steps = [
    { n: 1, label: "업로드 방식" },
    { n: 2, label: "코드 입력" },
    { n: 3, label: "확인" },
  ] as const;
  return (
    <nav className="flex items-start justify-between gap-2" aria-label="전략 생성 진행 단계">
      {steps.map((s, i) => {
        const completed = s.n < current;
        const active = s.n === current;
        return (
          <div key={s.n} className="flex flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              {i > 0 && (
                <div
                  className={
                    "h-0.5 flex-1 " +
                    (s.n <= current ? "bg-[color:var(--success)]" : "bg-[color:var(--border)]")
                  }
                />
              )}
              <div
                aria-current={active ? "step" : undefined}
                className={
                  "mx-2 grid size-10 place-items-center rounded-full border-2 font-mono text-sm font-semibold " +
                  (completed
                    ? "border-[color:var(--success)] bg-[color:var(--success)] text-white"
                    : active
                      ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_0_0_4px_rgba(37,99,235,0.15)]"
                      : "border-[color:var(--border)] bg-white text-[color:var(--text-muted)]")
                }
              >
                {completed ? <CheckIcon className="size-4" /> : s.n}
              </div>
              {i < steps.length - 1 && (
                <div
                  className={
                    "h-0.5 flex-1 " +
                    (s.n < current ? "bg-[color:var(--success)]" : "bg-[color:var(--border)]")
                  }
                />
              )}
            </div>
            <p
              className={
                "mt-2 text-xs font-medium " +
                (active ? "text-[color:var(--primary)]" : "text-[color:var(--text-secondary)]")
              }
            >
              {s.label}
            </p>
          </div>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 4.5: StepMethod (Step 1 — 입력 방식)**

Create `frontend/src/app/(dashboard)/strategies/new/_components/step-method.tsx`:

```tsx
import { CodeIcon, UploadIcon, LinkIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

type Method = "direct" | "upload" | "url";

export function StepMethod(props: {
  method: Method;
  onMethodChange: (m: Method) => void;
  onNext: () => void;
}) {
  const options: Array<{ id: Method; label: string; icon: typeof CodeIcon; desc: string; disabled: boolean }> = [
    { id: "direct", label: "Pine Script 직접 입력", icon: CodeIcon, desc: "에디터에 코드를 붙여넣습니다", disabled: false },
    { id: "upload", label: ".pine 파일 업로드", icon: UploadIcon, desc: "Sprint 7d+에서 지원 예정", disabled: true },
    { id: "url", label: "TradingView URL 가져오기", icon: LinkIcon, desc: "Sprint 7d+에서 지원 예정", disabled: true },
  ];
  return (
    <div>
      <h2 className="mb-4 font-display text-lg font-semibold">어떤 방식으로 전략을 등록할까요?</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {options.map((opt) => {
          const Icon = opt.icon;
          const active = opt.id === props.method;
          return (
            <button
              key={opt.id}
              type="button"
              disabled={opt.disabled}
              onClick={() => !opt.disabled && props.onMethodChange(opt.id)}
              className={
                "flex flex-col items-start gap-2 rounded-[var(--radius-md)] border-2 p-4 text-left transition " +
                (opt.disabled
                  ? "cursor-not-allowed border-[color:var(--border)] opacity-50"
                  : active
                    ? "border-[color:var(--primary)] bg-[color:var(--primary-light)]"
                    : "border-[color:var(--border)] hover:border-[color:var(--primary)]")
              }
            >
              <Icon className="size-6 text-[color:var(--primary)]" />
              <span className="font-semibold text-[color:var(--text-primary)]">{opt.label}</span>
              <span className="text-xs text-[color:var(--text-secondary)]">{opt.desc}</span>
            </button>
          );
        })}
      </div>
      <div className="mt-8 flex justify-end">
        <Button onClick={props.onNext} disabled={props.method !== "direct"}>
          다음 단계 →
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4.6: ParsePreviewPanel**

Create `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx`:

```tsx
"use client";

import { Badge } from "@/components/ui/badge";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function ParsePreviewPanel({
  result,
  loading,
}: {
  result: ParsePreviewResponse | null;
  loading: boolean;
}) {
  return (
    <aside
      aria-live="polite"
      aria-label="실시간 파싱 결과"
      className="rounded-[var(--radius-md)] border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] p-5"
    >
      <header className="mb-3 flex items-center gap-2">
        <span
          aria-hidden
          className={
            "block size-2 rounded-full " +
            (loading ? "animate-pulse bg-[color:var(--primary)]" : "bg-[color:var(--success)]")
          }
        />
        <h3 className="font-display text-sm font-bold text-[color:var(--primary)]">
          {loading ? "파싱 중..." : "실시간 파싱 결과"}
        </h3>
      </header>

      {!result && !loading && (
        <p className="text-xs text-[color:var(--text-secondary)]">
          코드를 입력하면 자동으로 파싱 결과가 표시됩니다.
        </p>
      )}

      {result && (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge variant="outline" data-tone={PARSE_STATUS_META[result.status].tone}>
              {PARSE_STATUS_META[result.status].label}
            </Badge>
            <Badge variant="secondary">Pine {result.pine_version}</Badge>
          </div>
          <dl className="grid grid-cols-2 gap-y-2 text-xs">
            <dt className="text-[color:var(--text-secondary)]">진입 신호</dt>
            <dd className="text-right font-mono font-semibold">{result.entry_count}</dd>
            <dt className="text-[color:var(--text-secondary)]">청산 신호</dt>
            <dd className="text-right font-mono font-semibold">{result.exit_count}</dd>
          </dl>
          {result.warnings.length > 0 && (
            <div className="mt-3">
              <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                경고 ({result.warnings.length})
              </h4>
              <ul className="mt-1 space-y-1 text-xs text-[color:var(--text-secondary)]">
                {result.warnings.slice(0, 5).map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}
          {result.errors.length > 0 && (
            <div className="mt-3">
              <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--destructive)]">
                에러 ({result.errors.length})
              </h4>
              <ul className="mt-1 space-y-1 text-xs text-[color:var(--destructive)]">
                {result.errors.slice(0, 5).map((e, i) => (
                  <li key={i}>
                    {e.line !== null && <span className="font-mono">L{e.line}: </span>}
                    {e.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
```

- [ ] **Step 4.7: StepCode (Step 2 — Monaco + 실시간 파싱)**

Create `frontend/src/app/(dashboard)/strategies/new/_components/step-code.tsx`:

```tsx
"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { PineEditor } from "@/components/monaco/pine-editor";
import { useParseStrategy } from "@/features/strategy/hooks";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { useDebouncedValue } from "@/features/strategy/utils";
import { ParsePreviewPanel } from "./parse-preview-panel";

export function StepCode(props: {
  pineSource: string;
  onPineSourceChange: (v: string) => void;
  onParsed: (r: ParsePreviewResponse | null) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const debounced = useDebouncedValue(props.pineSource, 300);
  const parse = useParseStrategy({
    onSuccess: (data) => props.onParsed(data),
    onError: () => props.onParsed(null),
  });

  // 자동 파싱: debounced 값이 비어있지 않을 때만
  useEffect(() => {
    if (debounced.trim().length === 0) {
      props.onParsed(null);
      return;
    }
    parse.mutate(debounced);
    // parse.mutate의 reference는 매 render 바뀌므로 eslint-disable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  const canProceed =
    parse.data?.status === "ok" || parse.data?.status === "unsupported";

  return (
    <div>
      <h2 className="mb-2 font-display text-lg font-semibold">Pine Script 코드</h2>
      <p className="mb-4 text-xs text-[color:var(--text-muted)]">
        <kbd className="rounded border border-[color:var(--border)] bg-[color:var(--bg-alt)] px-1.5 py-0.5 font-mono text-[0.7rem]">
          ⌘+Enter
        </kbd>{" "}
        즉시 파싱
      </p>
      <PineEditor
        value={props.pineSource}
        onChange={props.onPineSourceChange}
        onTriggerParse={() => debounced.trim() && parse.mutate(debounced)}
        height={400}
      />
      <div className="mt-5">
        <ParsePreviewPanel result={parse.data ?? null} loading={parse.isPending} />
      </div>
      <div className="mt-8 flex items-center justify-between">
        <Button variant="ghost" onClick={props.onBack}>← 이전</Button>
        <Button onClick={props.onNext} disabled={!canProceed}>
          다음 단계 →
        </Button>
      </div>
    </div>
  );
}
```

**주의:** `canProceed`는 `ok` + `unsupported`까지 허용. `unsupported`는 유효한 Pine이지만 백테스트만 불가 — CRUD 저장은 가능 (backend 허용). `error`는 진행 불가.

- [ ] **Step 4.8: StepMetadata (Step 3 — 폼 + 확인)**

Create `frontend/src/app/(dashboard)/strategies/new/_components/step-metadata.tsx`:

```tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  CreateStrategyRequestSchema,
  type CreateStrategyRequest,
  type ParsePreviewResponse,
} from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

type MetadataForm = Omit<CreateStrategyRequest, "pine_source">;

export function StepMetadata(props: {
  lastParse: ParsePreviewResponse | null;
  submitting: boolean;
  onBack: () => void;
  onSubmit: (meta: MetadataForm) => void;
}) {
  const form = useForm<MetadataForm>({
    resolver: zodResolver(CreateStrategyRequestSchema.omit({ pine_source: true })),
    defaultValues: {
      name: "",
      description: "",
      symbol: "",
      timeframe: "",
      tags: [],
    },
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(props.onSubmit)}
        className="space-y-6"
      >
        <h2 className="font-display text-lg font-semibold">메타데이터 입력</h2>

        {/* 파싱 요약 (읽기전용) */}
        {props.lastParse && (
          <div className="rounded-[var(--radius-md)] border border-[color:var(--border)] bg-[color:var(--bg-alt)] p-4 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                data-tone={PARSE_STATUS_META[props.lastParse.status].tone}
              >
                {PARSE_STATUS_META[props.lastParse.status].label}
              </Badge>
              <Badge variant="secondary">Pine {props.lastParse.pine_version}</Badge>
              <span className="text-xs text-[color:var(--text-secondary)]">
                진입 {props.lastParse.entry_count} · 청산 {props.lastParse.exit_count}
              </span>
            </div>
          </div>
        )}

        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>이름 *</FormLabel>
              <FormControl>
                <Input placeholder="예: MA Crossover Strategy" maxLength={120} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>설명</FormLabel>
              <FormControl>
                <Textarea
                  rows={3}
                  placeholder="전략의 핵심 아이디어를 간단히..."
                  maxLength={2000}
                  {...field}
                  value={field.value ?? ""}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="symbol"
            render={({ field }) => (
              <FormItem>
                <FormLabel>심볼</FormLabel>
                <FormControl>
                  <Input placeholder="BTC/USDT" maxLength={32} {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="timeframe"
            render={({ field }) => (
              <FormItem>
                <FormLabel>타임프레임</FormLabel>
                <FormControl>
                  <Input placeholder="1h, 4h, 1D" maxLength={16} {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* 태그: 간단히 comma-separated 문자열을 배열로 변환 */}
        <FormItem>
          <FormLabel>태그 (쉼표로 구분)</FormLabel>
          <FormControl>
            <Input
              placeholder="trend, ema, crossover"
              onChange={(e) => {
                const tags = e.target.value
                  .split(",")
                  .map((t) => t.trim())
                  .filter(Boolean);
                form.setValue("tags", tags, { shouldDirty: true });
              }}
            />
          </FormControl>
        </FormItem>

        <div className="flex items-center justify-between pt-4">
          <Button type="button" variant="ghost" onClick={props.onBack}>
            ← 이전
          </Button>
          <Button type="submit" disabled={props.submitting}>
            {props.submitting ? "생성 중..." : "전략 생성"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
```

- [ ] **Step 4.9 (NEW): Wizard draft auto-save (localStorage)**

Wizard 중단 시 입력 손실 방지. Step 2 pine_source + Step 3 metadata를 500ms debounce로 localStorage에 기록, 재진입 시 복원 제안.

Create `frontend/src/features/strategy/draft.ts`:

```ts
"use client";

import { useEffect, useState } from "react";

const DRAFT_KEY = "sprint7c:strategy-wizard-draft:v1";
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30일

export interface WizardDraft {
  version: 1;
  savedAt: number;
  method: "direct" | "upload" | "url";
  pineSource: string;
  metadata: {
    name?: string;
    description?: string;
    symbol?: string;
    timeframe?: string;
    tags?: string[];
  };
}

export function loadWizardDraft(): WizardDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WizardDraft;
    if (parsed.version !== 1) return null;
    if (Date.now() - parsed.savedAt > TTL_MS) {
      window.localStorage.removeItem(DRAFT_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveWizardDraft(draft: Omit<WizardDraft, "version" | "savedAt">) {
  if (typeof window === "undefined") return;
  const payload: WizardDraft = { version: 1, savedAt: Date.now(), ...draft };
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(payload));
  } catch {
    // quota exceeded 등 무시 — wizard는 draft 없이도 동작
  }
}

export function clearWizardDraft() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(DRAFT_KEY);
}

/** 입력 state를 500ms debounce로 자동 저장. */
export function useAutoSaveDraft(draft: Omit<WizardDraft, "version" | "savedAt">) {
  useEffect(() => {
    const t = setTimeout(() => saveWizardDraft(draft), 500);
    return () => clearTimeout(t);
  }, [draft]);
}
```

`NewStrategyPage` (Step 4.3 code 수정):

```tsx
// 기존 useState 선언들 아래에 추가
const [restorePromptOpen, setRestorePromptOpen] = useState(false);
const [availableDraft, setAvailableDraft] = useState<WizardDraft | null>(null);

useEffect(() => {
  const d = loadWizardDraft();
  if (d && (d.pineSource.trim().length > 0 || d.metadata.name)) {
    setAvailableDraft(d);
    setRestorePromptOpen(true);
  }
}, []);

// auto-save (모든 step)
useAutoSaveDraft({
  method,
  pineSource,
  metadata: {}, // Step 3에서 form 값 덮어쓰기 — StepMetadata에서 onChange로 동기화
});

// create.onSuccess 핸들러에 clearWizardDraft() 추가
const create = useCreateStrategy({
  onSuccess: (data) => {
    clearWizardDraft();
    toast.success(`"${data.name}" 전략이 생성되었습니다`);
    router.push(`/strategies/${data.id}/edit`);
  },
  // ...
});
```

복원 다이얼로그 (`Dialog` 컴포넌트 사용, NewStrategyPage 하단에 추가):

```tsx
<Dialog open={restorePromptOpen} onOpenChange={setRestorePromptOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>이어서 작성하시겠어요?</DialogTitle>
      <DialogDescription>
        {availableDraft && `${new Date(availableDraft.savedAt).toLocaleString("ko-KR")}에 작성 중이던 초안이 있습니다.`}
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="ghost" onClick={() => { clearWizardDraft(); setRestorePromptOpen(false); }}>
        새로 시작
      </Button>
      <Button onClick={() => {
        if (availableDraft) {
          setMethod(availableDraft.method);
          setPineSource(availableDraft.pineSource);
          setStep(availableDraft.pineSource ? 2 : 1);
        }
        setRestorePromptOpen(false);
      }}>
        이어서 작성
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**주의:** StepMetadata form 값도 draft에 포함하려면 react-hook-form의 `watch()`를 상위로 전달하거나, StepMetadata 내부에서 `useAutoSaveDraft(form.watch())` 호출. 구현 시 한 쪽 선택.

**Acceptance (Step 5.7 E2E smoke checklist에 추가):**
- Pine 코드 입력 → 브라우저 새로고침 → 복원 다이얼로그 표시 → "이어서 작성" → Step 2에 코드 유지.
- 생성 완료 후 `/strategies/new` 재접속 → 다이얼로그 안 뜸 (clearWizardDraft).
- 30일 지난 draft는 자동 삭제 (TTL).

- [ ] **Step 4.10: 타입/린트 + 브라우저 smoke (전체 wizard 플로우)**

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm dev
```

브라우저 수동 시나리오:
1. `/strategies/new` 접속 → Step 1 렌더링. 직접입력 카드 active, 나머지 2개 disabled + opacity 50%.
2. "다음" 클릭 → Step 2. Monaco 에디터 나타남 + Pine Monarch 하이라이트 (keyword 오렌지, string 녹색, number 보라 등) 육안 확인.
3. `docs/prototypes/07-strategy-create.html`의 샘플 Pine 코드 붙여넣기 → 300ms 후 `POST /strategies/parse` 네트워크 호출 + 오른쪽 패널에 `ok` + entry/exit count 표시.
4. 코드를 잠깐 "asdf" 같은 garbage로 바꾸면 status=`error` 배지 + 에러 메시지 리스트, "다음" 비활성화.
5. 정상 코드 복귀 → "다음" 활성화 → Step 3.
6. 이름 빈칸 제출 시도 → Zod validation 에러 메시지 표시.
7. 이름/심볼/TF 기입 → "전략 생성" → 성공 토스트 + `/strategies/{id}/edit`로 리다이렉트 (Task 5에서 구현 — 404지만 URL은 확인).
8. `/strategies` 돌아가서 목록에 신규 전략 나타남.

- [ ] **Step 4.11: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add frontend/src/app/\(dashboard\)/strategies/new/ frontend/src/components/monaco/ frontend/src/features/strategy/draft.ts
git commit -m "feat(frontend): Sprint 7c T4 — /strategies/new 3-step wizard + Monaco Pine Monarch + 실시간 파싱 + localStorage draft"
```

---

## Task 5: `/strategies/[id]/edit` 편집 페이지 + Delete 409 fallback + 문서 업데이트

**Files:**
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/page.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/editor-view.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-code.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-metadata.tsx`
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/delete-dialog.tsx`
- Modify: `docs/TODO.md`
- Modify: `docs/dev-log/008-sprint7c-scope-decision.md`
- Modify: `.claude/CLAUDE.md`

**Reference:** `docs/prototypes/01-strategy-editor.html` — 상단 탭 3개(코드/파싱/메타데이터) + 우측 분석 패널(파라미터/리스크/백테스트 이력). Sprint 7c 범위: **탭 3개 + 저장/삭제/아카이브만**. 우측 분석 패널은 **stub** ("백테스트 이력은 Sprint 7b에서 /backtest 탭과 함께 연결" 안내).

**Interaction ref:** `INTERACTION_SPEC.md` §01 — 저장은 PATCH(본 구현은 PUT), 백테스트 실행은 `/backtest?strategy_id=:id` 네비게이션 stub, 탭 전환은 URL 쿼리 동기화(?tab=code|parse|metadata).

- [ ] **Step 5.1: Server page + 404 처리**

Create `frontend/src/app/(dashboard)/strategies/[id]/edit/page.tsx`:

```tsx
import { notFound } from "next/navigation";
import { EditorView } from "./_components/editor-view";

export default async function StrategyEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // UUID 포맷 검증 — 잘못된 URL은 즉시 404.
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    notFound();
  }
  return <EditorView id={id} />;
}
```

- [ ] **Step 5.2: EditorView — 탭 상태 + 레이아웃**

Create `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/editor-view.tsx`:

```tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeftIcon, PlayIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStrategy } from "@/features/strategy/hooks";
import { PARSE_STATUS_META } from "@/features/strategy/utils";
import { TabCode } from "./tab-code";
import { TabParse } from "./tab-parse";
import { TabMetadata } from "./tab-metadata";
import { DeleteDialog } from "./delete-dialog";

type TabKey = "code" | "parse" | "metadata";

export function EditorView({ id }: { id: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const initialTab = (params.get("tab") as TabKey) || "code";
  const [tab, setTab] = useState<TabKey>(initialTab);
  const [deleteOpen, setDeleteOpen] = useState(params.get("action") === "delete");

  const { data: strategy, isLoading, isError } = useStrategy(id);

  // URL 쿼리 ?action=archive/delete 초기 처리
  useEffect(() => {
    const action = params.get("action");
    if (action === "delete") setDeleteOpen(true);
    if (action === "archive") {
      // 아카이브는 별도 다이얼로그 없이 즉시 PUT — DeleteDialog의 archive fallback 재사용
      setDeleteOpen(true);
    }
  }, [params]);

  if (isLoading) {
    return <div className="p-8"><div className="h-96 animate-pulse rounded-md bg-[color:var(--bg-alt)]" /></div>;
  }
  if (isError || !strategy) {
    return (
      <div className="p-8">
        <p className="text-destructive">전략을 불러오지 못했습니다.</p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/strategies">목록으로</Link>
        </Button>
      </div>
    );
  }

  const meta = PARSE_STATUS_META[strategy.parse_status];

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      <header className="mb-5 flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="icon" asChild aria-label="목록으로">
          <Link href="/strategies"><ArrowLeftIcon className="size-4" /></Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-xl font-bold">{strategy.name}</h1>
          <p className="flex items-center gap-2 text-xs text-[color:var(--text-muted)]">
            <Badge variant="outline" data-tone={meta.tone}>{meta.label}</Badge>
            <span className="font-mono">
              {strategy.symbol ?? "—"} · {strategy.timeframe ?? "—"} · Pine {strategy.pine_version}
            </span>
            {strategy.is_archived && <Badge variant="secondary">보관됨</Badge>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => router.push(`/backtest?strategy_id=${strategy.id}`)}
            disabled
            title="백테스트 탭은 Sprint 7b에서 연결됩니다"
          >
            <PlayIcon className="size-4" />백테스트 실행
          </Button>
          <Button variant="outline" onClick={() => setDeleteOpen(true)}>
            <Trash2Icon className="size-4" />삭제
          </Button>
        </div>
      </header>

      <Tabs value={tab} onValueChange={(v) => { setTab(v as TabKey); router.replace(`?tab=${v}`); }}>
        <TabsList>
          <TabsTrigger value="code">코드</TabsTrigger>
          <TabsTrigger value="parse">파싱 결과</TabsTrigger>
          <TabsTrigger value="metadata">메타데이터</TabsTrigger>
        </TabsList>
        <TabsContent value="code" className="mt-4">
          <TabCode strategy={strategy} />
        </TabsContent>
        <TabsContent value="parse" className="mt-4">
          <TabParse strategy={strategy} />
        </TabsContent>
        <TabsContent value="metadata" className="mt-4">
          <TabMetadata strategy={strategy} />
        </TabsContent>
      </Tabs>

      <DeleteDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        strategyId={strategy.id}
        strategyName={strategy.name}
        onDone={() => {
          toast.success("전략이 삭제되었습니다");
          router.push("/strategies");
        }}
        onArchived={() => {
          toast.success("전략이 보관되었습니다");
          setDeleteOpen(false);
          router.refresh();
        }}
      />
    </div>
  );
}
```

- [ ] **Step 5.3: TabCode — Monaco + 저장**

Create `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-code.tsx`:

```tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { SaveIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PineEditor } from "@/components/monaco/pine-editor";
import { useParseStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { ParsePreviewPanel } from "../../../new/_components/parse-preview-panel";

export function TabCode({ strategy }: { strategy: StrategyResponse }) {
  const [source, setSource] = useState(strategy.pine_source);
  const dirty = source !== strategy.pine_source;
  const parse = useParseStrategy();
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs text-[color:var(--text-muted)]">
            ⌘+S 저장 · ⌘+Enter 파싱 미리보기
          </p>
          <Button
            onClick={() => update.mutate({ pine_source: source })}
            disabled={!dirty || update.isPending}
          >
            <SaveIcon className="size-4" />
            {update.isPending ? "저장 중..." : "저장"}
          </Button>
        </div>
        <PineEditor
          value={source}
          onChange={setSource}
          onTriggerParse={() => source.trim() && parse.mutate(source)}
          height={520}
        />
      </div>
      <ParsePreviewPanel result={parse.data ?? null} loading={parse.isPending} />
    </div>
  );
}
```

- [ ] **Step 5.4: TabParse — 저장된 parse_status 상세 표시**

Create `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx`:

```tsx
"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const meta = PARSE_STATUS_META[strategy.parse_status];
  const errors = strategy.parse_errors ?? [];
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Badge variant="outline" data-tone={meta.tone}>{meta.label}</Badge>
          <Badge variant="secondary">Pine {strategy.pine_version}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
          <div>
            <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">버전</dt>
            <dd className="mt-1 font-mono">Pine {strategy.pine_version}</dd>
          </div>
          <div>
            <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">아카이브 상태</dt>
            <dd className="mt-1">{strategy.is_archived ? "보관됨" : "활성"}</dd>
          </div>
        </dl>
        {errors.length > 0 && (
          <div>
            <h3 className="text-sm font-bold text-[color:var(--destructive)]">
              저장 당시 에러 ({errors.length})
            </h3>
            <ul className="mt-2 space-y-1 text-xs">
              {errors.map((e, i) => (
                <li key={i} className="rounded border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-2 font-mono">
                  {JSON.stringify(e)}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="text-xs text-[color:var(--text-muted)]">
          ※ 실시간 파싱은 코드 탭의 우측 패널을 참조하세요. 이 탭은 <strong>저장 시점에 스냅샷된</strong> 결과입니다.
        </p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5.5: TabMetadata — react-hook-form + PUT**

Create `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-metadata.tsx`:

```tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useUpdateStrategy } from "@/features/strategy/hooks";
import {
  type StrategyResponse,
  UpdateStrategyRequestSchema,
  type UpdateStrategyRequest,
} from "@/features/strategy/schemas";

export function TabMetadata({ strategy }: { strategy: StrategyResponse }) {
  const form = useForm<UpdateStrategyRequest>({
    resolver: zodResolver(UpdateStrategyRequestSchema),
    defaultValues: {
      name: strategy.name,
      description: strategy.description ?? "",
      symbol: strategy.symbol ?? "",
      timeframe: strategy.timeframe ?? "",
      tags: strategy.tags,
    },
  });
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("메타데이터가 저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((v) => update.mutate(v))} className="max-w-2xl space-y-5">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>이름</FormLabel>
              <FormControl><Input {...field} value={field.value ?? ""} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>설명</FormLabel>
              <FormControl><Textarea rows={3} {...field} value={field.value ?? ""} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="symbol"
            render={({ field }) => (
              <FormItem>
                <FormLabel>심볼</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ""} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="timeframe"
            render={({ field }) => (
              <FormItem>
                <FormLabel>타임프레임</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ""} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormItem>
          <FormLabel>태그 (쉼표로 구분)</FormLabel>
          <FormControl>
            <Input
              defaultValue={strategy.tags.join(", ")}
              onChange={(e) => {
                const tags = e.target.value.split(",").map((t) => t.trim()).filter(Boolean);
                form.setValue("tags", tags, { shouldDirty: true });
              }}
            />
          </FormControl>
        </FormItem>
        <div className="pt-2">
          <Button type="submit" disabled={!form.formState.isDirty || update.isPending}>
            {update.isPending ? "저장 중..." : "변경사항 저장"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
```

- [ ] **Step 5.6: DeleteDialog — 409 시 archive fallback**

Create `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/delete-dialog.tsx`:

```tsx
"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useDeleteStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import { isStrategyHasBacktestsError } from "@/features/strategy/utils";

export function DeleteDialog(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyId: string;
  strategyName: string;
  onDone: () => void;
  onArchived: () => void;
}) {
  const [phase, setPhase] = useState<"confirm" | "archive-fallback">("confirm");
  const del = useDeleteStrategy({
    onSuccess: props.onDone,
    onError: (err) => {
      if (isStrategyHasBacktestsError(err)) {
        setPhase("archive-fallback");
      }
    },
  });
  const update = useUpdateStrategy(props.strategyId, {
    onSuccess: props.onArchived,
  });

  return (
    <Dialog open={props.open} onOpenChange={(o) => {
      props.onOpenChange(o);
      if (!o) setPhase("confirm");
    }}>
      <DialogContent>
        {phase === "confirm" ? (
          <>
            <DialogHeader>
              <DialogTitle>"{props.strategyName}"를 삭제할까요?</DialogTitle>
              <DialogDescription>
                되돌릴 수 없습니다. 이 전략과 연관된 백테스트가 있으면 삭제 대신 보관을 제안합니다.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => props.onOpenChange(false)}>
                취소
              </Button>
              <Button
                variant="destructive"
                disabled={del.isPending}
                onClick={() => del.mutate(props.strategyId)}
              >
                {del.isPending ? "삭제 중..." : "삭제"}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>삭제할 수 없습니다</DialogTitle>
              <DialogDescription>
                이 전략에 연관된 백테스트가 있습니다. 대신 <strong>보관</strong>하면
                목록에서 숨기지만 백테스트 기록은 유지됩니다.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => props.onOpenChange(false)}>
                취소
              </Button>
              <Button
                disabled={update.isPending}
                onClick={() => update.mutate({ is_archived: true })}
              >
                {update.isPending ? "보관 중..." : "보관"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 5.7: 타입/린트 + 전체 E2E 브라우저 smoke**

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm dev
```

**전체 E2E 수동 시나리오 (Manual QA Checklist — Sprint 7c acceptance):**

1. **Create flow:**
   - `/strategies/new` 접속 → Step 1 → Step 2 (Pine 샘플 붙여넣기) → 파싱 `ok` → Step 3 (name/symbol/timeframe 입력) → 제출.
   - 토스트 "전략이 생성되었습니다" + `/strategies/[id]/edit` 리다이렉트.

2. **Edit — 코드 탭:**
   - Monaco에 기존 코드 로드 + 하이라이트 확인.
   - 한 줄 수정 → "저장" 활성 → 클릭 → 토스트 "저장되었습니다".
   - ⌘+Enter → 우측 패널 파싱 결과 업데이트.

3. **Edit — 파싱 결과 탭:**
   - 저장 시점 status/version 표시.
   - parse_errors 있으면 에러 목록.

4. **Edit — 메타데이터 탭:**
   - 이름 변경 → "변경사항 저장" → 토스트.
   - 페이지 새로고침 → 변경 유지.

5. **Delete (백테스트 없는 전략):**
   - "삭제" → 확인 다이얼로그 → "삭제" → 토스트 + `/strategies` 리다이렉트.
   - 목록에서 제거됨.

6. **Delete (백테스트 있는 전략) — 409 fallback:**
   - 백테스트 연결된 전략으로 시도 (Sprint 4/5에서 만든 전략이 있으면 활용).
   - "삭제" 클릭 → 409 응답 → 다이얼로그가 "삭제할 수 없습니다 / 보관" 단계로 전환.
   - "보관" 클릭 → 토스트 "보관되었습니다" + 목록에서 "보관됨" 필터로 이동 시 확인.

7. **필터/목록 회귀:**
   - 상태 필터 chip 전환 → `parse_status=` 쿼리 반영.
   - 페이지네이션 정상 작동.
   - 그리드/목록 뷰 토글 정상.

8. **a11y smoke:**
   - Tab 키로 전체 페이지 이동 시 focus 표시 가시적.
   - Dialog 열림 시 포커스가 다이얼로그 내부에 trap됨.
   - VoiceOver(Mac) 또는 Windows Narrator로 "내 전략" 제목 + 버튼 라벨 읽힘.

9. **반응형:**
   - 1440/1024/768px 뷰포트 시각 확인. Monaco는 768px 이하에서 세로 스크롤 허용.

**Expected:** 모든 항목 pass. 실패 항목은 debug 후 fix commit.

- [ ] **Step 5.8: `docs/TODO.md` 업데이트**

기존 `### Sprint 7 Next Actions` 섹션 상단에 추가:

```markdown
- [x] Strategy CRUD UI (목록/생성 3-step/편집 3탭 + delete 409 archive fallback) — Sprint 7c ✅ 완료 (2026-04-XX)
```

"Sprint 8+ 후보"에 추가 (기존 항목 뒤):

```markdown
- [ ] Strategy template gallery (`/templates`) — Sprint 7c에서 placeholder만 처리
- [ ] Strategy clone + share — Sprint 7c에서 드롭다운만 disabled (design review P7-4)
- [ ] Backtest run from /strategies/[id]/edit — `/backtest?strategy_id=` 연결 (Sprint 7b/7d 후보)
- [ ] FE component test infra (Vitest + @testing-library/react) — Sprint 7c 이관
```

**Design review Pass 7 이월 — Sprint 7d+ FE design debt (batch 추가):**

```markdown
### Sprint 7c 이후 FE Design Debt (design review 2026-04-17 기록)

- [ ] Chip-style tag input (type + Enter + Backspace 제거) — 현재 comma-split. 파워 유저 마찰. Context: plan P7-6, 2~4시간
- [ ] Coachmark tour — first-visit edit 페이지의 ⌘+S/Enter 단축키 1회성 overlay. Context: plan Persona C storyboard
- [ ] Save conflict OCC — 백엔드 ETag 또는 `If-Unmodified-Since` header 도입 후 FE에서 409 Conflict 분기. Context: plan P7-10, 스키마 변경 필요
- [ ] Bottom sheet dialog (mobile <768px) — DeleteDialog가 thumb-reach 위해 하단 시트로 전환. Context: plan P6 Responsive
- [ ] Monaco Pine autocomplete — Pine v5 builtin 함수 자동완성 등록. Context: plan P7-7, full grammar 선행 필요
- [ ] Full Pine TextMate grammar — 현재 5색 Monarch → 전체 keyword + builtin + operator 완전 grammar. 3~5일. Context: plan P7-7
- [ ] Keyboard shortcut help dialog (? key) — 전역 단축키 목록 모달. Context: plan P6 a11y §2
- [ ] localStorage draft user_id scoping — Clerk session 만료 시 draft auto-clear + user_id key prefix. Context: plan P7-9
```

- [ ] **Step 5.9: `docs/dev-log/008-sprint7c-scope-decision.md` 상태 업데이트**

frontmatter 수정:

```markdown
> **상태:** ✅ 구현 완료 (2026-04-XX)
> **구현 브랜치:** feat/sprint7c-strategy-ui
> **관련 PR:** #11 (예정)
> **관련 plan:** [`docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md`](../superpowers/plans/2026-04-17-sprint7c-strategy-ui.md)
```

본문 말미 "Approach 비교" 아래 "실행 결과" 섹션 신규 추가:

```markdown
## 실행 결과 (2026-04-XX)

- **Monaco Q1 최종 결정:** Minimal Pine Monarch tokenizer (writing-plans 세션 decision). 반나절 투자, keyword/function/string/number/comment 5색.
- **UI primitives:** shadcn/ui CLI + 12 컴포넌트 + sonner (Button/Card/Tabs/Dialog/Select/Input/Form/DropdownMenu/Badge/Label/Textarea/Sonner).
- **Delete 409 fallback:** `strategy_has_backtests` 감지 시 다이얼로그가 "삭제 → 보관 제안"으로 phase 전환.
- **Quantitative gain:** 기존 curl flow ~5분 → 브라우저 flow ~30초 (10배 단축). 측정 근거: T1 시작 전 선행 assignment로 사용자가 기록.
```

- [ ] **Step 5.10: `.claude/CLAUDE.md` "현재 작업" 업데이트**

기존 "다음:" 라인 직전에 추가:

```markdown
- Sprint 7c FE 따라잡기 (Strategy CRUD UI) ✅ 완료 (2026-04-XX, PR #11 — 3 라우트 + Monaco Pine Monarch + shadcn/ui 12개 + sonner + Delete 409 archive fallback)
```

"다음:" 라인을 수정:

```markdown
- **다음:** Sprint 7b (OKX 멀티 거래소 + Trading Sessions) → Sprint 8+ (Binance mainnet 실거래 + Kill Switch capital_base 동적 바인딩)
```

- [ ] **Step 5.11: 최종 타입/린트/전수 smoke**

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm test 2>&1 || echo "tests skipped — FE test infra not configured, Sprint 7c uses manual QA"
```

Expected: tsc/lint clean. Test command는 infra 미설치 시 skip 메시지 노출 — OK.

- [ ] **Step 5.12: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add frontend/src/app/\(dashboard\)/strategies/\[id\]/ docs/TODO.md docs/dev-log/008-sprint7c-scope-decision.md .claude/CLAUDE.md
git commit -m "feat(frontend): Sprint 7c T5 — /strategies/[id]/edit 3탭 + delete 409 archive fallback + docs"
```

---

## Verification (End-to-End 최종 검증)

### 1. 정량 지표 (선행 assignment — ADR 008 §선행 Assignment)

- **Baseline (T1 착수 전):** 사용자가 curl + JSON escape + Clerk token으로 Pine 전략 1개 등록 → parse → 백테스트 시작까지 초 단위 기록.
- **After Sprint 7c:** `/strategies/new` 3-step wizard + `/strategies/[id]/edit` 저장까지 동일 플로우 초 단위 재측정.
- **Acceptance:** 최소 **3배 이상 단축**. 미달 시 원인 분석 (네트워크 / 서버 지연 / UI 느림) 후 fix.

### 2. TypeScript + Lint + 개발 서버

```bash
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm dev
```

Expected: clean, 개발 서버 에러 없음.

### 3. Manual QA checklist (Step 5.7 전체)

9개 시나리오 모두 pass. 한 개라도 실패 시 별도 fix commit.

### 4. Backend 회귀 없음

```bash
cd backend
pytest -v
```

Expected: 기존 524 tests 모두 PASS (Sprint 7a 이후 baseline 유지). Sprint 7c는 FE만 변경하므로 BE 테스트 수 변화 없어야 정상.

### 5. Git 상태

```bash
git log --oneline main..feat/sprint7c-strategy-ui
# 5개 커밋 예상 (T1/T2/T3/T4/T5)
```

---

## Security / a11y 체크리스트

- [ ] **Clerk JWT 노출 금지:** `getToken()` 결과는 `apiFetch` 호출 범위 내에서만 사용. console.log 금지. `localStorage`에 저장 금지.
- [ ] **XSS:** Pine source는 Monaco 내에서만 표시, `dangerouslySetInnerHTML` 사용 금지.
- [ ] **CSRF:** Next.js App Router + Clerk은 SameSite cookie + Authorization header 조합 — 별도 토큰 불필요.
- [ ] **a11y:**
  - [ ] 모든 `<button>` / 아이콘 버튼에 `aria-label`
  - [ ] `<Dialog>`는 shadcn이 `aria-modal`, focus trap 자동 처리 — 확인만.
  - [ ] Tab order가 시각 순서와 일치 (Step 5.7 §8).
  - [ ] WCAG AA 대비 — DESIGN.md 이미 검증됨.
  - [ ] `prefers-reduced-motion` — shadcn/Monaco 기본 준수 확인.

---

## Sprint 7c Out-of-scope (명시적 제외)

ADR 008 § "결정: Strategy CRUD UI 단독" 기반. 아래는 **의도적 제외**:

- 주문 생성 폼 (candidate 1) — 현재 `/trading` read-only + curl로 감내.
- ExchangeAccount 등록 UI (candidate 3) — 1회 셋업, psql로 감내.
- OrderList 상세 + 필터 (candidate 4) — pgAdmin/logs/auto test로 커버됨.
- 분석 패널 backtest history (01-strategy-editor.html 우측 하단) — Sprint 7b에서 `/backtests` 탭 연결 시 처리.
- Strategy versioning (commit-style) — ADR 008 Approach C 탈락.
- Inline backtest run UI — `/backtest` 별도 페이지로 navigate (Q3 결정).
- Strategy clone / share / template — drop-down에 disabled로만 노출.
- FE component/e2e test 자동화 — infra 미구비, 매뉴얼 QA로 대체.

---

## 참고 파일

- Scope 결정: [`docs/dev-log/008-sprint7c-scope-decision.md`](../../dev-log/008-sprint7c-scope-decision.md)
- 선례 plan: [`docs/superpowers/plans/2026-04-17-sprint7a-bybit-futures.md`](./2026-04-17-sprint7a-bybit-futures.md)
- 디자인 시스템 SSOT: [`DESIGN.md`](../../../DESIGN.md)
- 프로토타입:
  - `docs/prototypes/06-strategies-list.html`
  - `docs/prototypes/07-strategy-create.html`
  - `docs/prototypes/01-strategy-editor.html`
  - `docs/prototypes/INTERACTION_SPEC.md`
- Backend API: `backend/src/strategy/router.py`, `backend/src/strategy/schemas.py`, `backend/src/strategy/pine/__init__.py`
- 기존 FE 패턴 참조: `frontend/src/app/trading/page.tsx` (React Query + Zod + `apiFetch`)
- 기존 FE App Shell: `frontend/src/components/layout/dashboard-shell.tsx`

---

## 실행 준비 체크 (플랜 수락 후)

1. 현재 main 기반 새 브랜치 생성: `git switch -c feat/sprint7c-strategy-ui`
2. T1 착수 전에 **선행 assignment 완료**: curl 기준 baseline 초 단위 기록 (ADR 008 §선행 Assignment).
3. SDD 실행: `superpowers:subagent-driven-development` 또는 inline: `superpowers:executing-plans`.
