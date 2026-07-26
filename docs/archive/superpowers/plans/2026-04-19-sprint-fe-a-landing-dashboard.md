# Sprint FE-A — Landing CTA + `/dashboard` redirect

- **Scope SSOT**: `docs/next-session-fe-polish-autonomous.md § # Sprint FE-A`
- **Branch**: `feat/fe-a-landing-dashboard` (base `stage/fe-polish`)
- **Worktree**: `.claude/worktrees/feat+fe-a`
- **Issues**: ISSUE-002 (landing 미인증 UX) · ISSUE-009 (/dashboard scaffold 불일치)
- **기대 commit**: 3

## 문제

1. 미인증 랜딩(`/`)에 "Stage 0 scaffold" 배지 노출, CTA 없음 → 전환 경로 부재
2. 인증된 사용자가 `/` 진입 시 landing 이 그대로 보임 → `/strategies` 로 자동 유도 필요
3. `/dashboard` 는 scaffold placeholder 만 있고 실제 기능 없음 → `/strategies` 로 redirect 해 단일 홈 경로 유지

## 구현

### A. `frontend/src/app/page.tsx` — 서버 컴포넌트 landing

- `async` 로 변경, `auth()` from `@clerk/nextjs/server` 호출
- `userId` truthy → `redirect("/strategies")` (next/navigation)
- 미인증 UI:
  - "Stage 0 scaffold" 배지 삭제
  - Hero copy (기존 h1 유지, 한 줄 sub copy)
  - shadcn `Button asChild` + `<Link href="/sign-in">시작하기</Link>`
- DESIGN.md 기본 primary variant. 반응형 유지(mx-auto max-w-[1200px]).

### B. `frontend/src/app/(dashboard)/dashboard/page.tsx` — redirect

- `export default function DashboardPage() { redirect("/strategies"); }`
- metadata 없음(redirect 이므로 title 불필요).

### 분리된 commit 안(3개)

1. `feat(fe-a): / landing Clerk auth redirect + 시작하기 CTA`
2. `feat(fe-a): /dashboard → /strategies redirect`
3. `chore(fe-a): writing-plans plan doc`

## 검증

### 로컬 (self-verify)

- `pnpm lint` 0/0
- `pnpm tsc --noEmit`
- `pnpm test -- --run` (기존 landing/dashboard 관련 unit test 영향 없음 확인)
- `pnpm build`

### Live smoke (Playwright)

- a) `/` 미인증 → "시작하기" 버튼 visible, Console error 0
- b) `/dashboard` → `/strategies` redirect (middleware 가 auth gate)
- CPU 샘플 6×10s, 80% 초과 0건

### Evaluator (subagent)

- `superpowers:code-reviewer` dispatch (isolation=worktree)
- PASS 시만 PR create (base `stage/fe-polish`)

## LESSON 체크

- LESSON-004: `react-hooks/*` disable 없음 ✓ (서버 컴포넌트, hooks 미사용)
- LESSON-005: queryFn 변경 없음 ✓
- LESSON-006: render body ref mutation 없음 ✓
- LESSON-007: dev server/mcp-chrome 정리 명령 보유 ✓

## 리스크

- e2e `smoke.spec.ts` 의 landing 테스트는 "Stage 0 scaffold" 문자열을 assert 하지 않으므로 무영향. 네트워크 요청 <50 개 조건은 유지.
- 인증 사용자가 `/` 진입 시 redirect 발생 — e2e 는 Clerk 로그인 세션 없이 실행되므로 기존 테스트 통과.
