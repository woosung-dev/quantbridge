# ADR 010 — Dev CPU Budget Policy + Next.js Anti-Pattern 15건

> **작성일:** 2026-04-17
> **발견 세션:** Sprint 7c FE Strategy CRUD UI 개발 중 Playwright MCP smoke QA
> **관련 브랜치:** `chore/dev-cpu-optimization` (본 ADR + Turbopack fix)
> **관련 PR:** #13 (Sprint 7c draft) — 별도 merge 가능

---

## 배경

Sprint 7c FE 구현 중 `next-server` Node 프로세스가 **331% CPU (3.3 cores)** + `fseventsd 45% CPU` 폭증. Dev server가 사실상 hang 상태. 사용자 관찰: **동일 `.ai/rules/` 체계를 쓰는 여러 프로젝트에서 CPU 폭증이 반복**. 코드 한 줄마다 체감 느림.

## 증상

| 프로세스 | CPU | 원인 |
|---|---|---|
| `next-server (v16.2.3)` | 331% | Webpack + heavy deps (Monaco) 재컴파일 폭주 |
| `fseventsd` | 45.8% | HMR 파일 watcher 이벤트 과부하 |
| Chrome Helper × N | 5~15%씩 | Playwright Chromium 인스턴스 누적 |

`.next/` 523MB · `node_modules/` 789MB · `globals.css` 353줄. Monaco/Clerk/React Query 조합.

## 근본 원인 (3가지)

### 1) Dev server ↔ LLM edit workflow 격리 부재

- `ralph-loop.md` 기본 `--max-iterations 50` — dev server 구동 중에도 파일 자동 수정 → 매 iteration HMR 재컴파일
- `.ai/templates/settings.json.example`의 PostToolUse `prettier --write` hook — 매 Edit/Write 후 prettier 실행 누적
- AGENTS.md "Atomic Update" — 코드 + docs 동반 수정 → 단일 feature 15~20 파일 변경 → HMR 노이즈 확대

### 2) "완전한 코드 + Atomic Update + 확장성 고려" 트리오

`AGENTS.md:40` **"`...` 처리로 생략하지 않고 완전한 코드를 제공"** + `AGENTS.md:37` **"유지보수 가능한 아키텍처"** 조합이 LLM에:
- 단일 feature = 20~30 파일 변경
- Premature Context API / Provider 계층 abstraction
- `noUncheckedIndexedAccess` strict 옵션과 결합해 복잡 generic 남발 → tsc 비용 ↑

### 3) Rules에 dev performance 의식 전무

- `.ai/stacks/nextjs-shared.md` / `frontend.md` / `fullstack.md` — Turbopack, HMR watch ignore, heavy deps splitting 언급 **0건**
- `.ai/common/typescript.md` — `useEffect` deps 안정화 규칙 **없음** (object literal → infinite re-render loop 위험)
- `.ai/project/lessons.md` — CPU/HMR 관련 학습 **0건** (문제가 지식 자산화 안 됨)

---

## 발견된 Anti-Pattern 15건 (severity별)

### 🔥 Critical (CPU 직접 유발)

1. **`.ai/templates/ralph-loop.md:145` 기본값 `--max-iterations 50`** — Dev server 동시 구동 시 HMR 폭주 (일반성 100%)
2. **`.ai/templates/settings.json.example:3-12` PostToolUse prettier hook** — 매 Edit마다 prettier 실행 누적 (일반성 100%)
3. **`.ai/stacks/nextjs-shared.md` HMR watch 가이드 부재** — node_modules/.next watch 제외 명시 없음 (일반성 100%)
4. **`AGENTS.md:40` "완전한 코드" 원칙** — 파일 변경 범위 2~3배 확대 (일반성 100%)
5. **`.ai/common/typescript.md` useEffect deps 규칙 부재** — object literal inline → re-render loop (일반성 100%)

### Important (간접 CPU 비용)

6. **`AGENTS.md:54-55` Atomic Update** — 코드+문서 동반 수정 → HMR noise
7. **`nextjs-shared.md:40` Zod v4 규칙** — render body에 `z.parse()` 유입 가능성
8. **`fullstack.md:368` 폴링 interval 가이드 없음** — 5초 interval 남용 위험
9. **`.ai/templates/methodology.md` "docs 계속 touch"** — Tailwind/MDX 재스캔 연쇄
10. **`frontend.md:68-69` Query Key factory 가이드 부재** — 캐시 collision → 불필요 refetch

### Minor (체감 작지만 개선 가치)

11. `tsconfig.json` `noUncheckedIndexedAccess` — type guard 남발
12. `methodology-tooled.md:140-145` cmux 병렬 워커 — N개 프로세스 × prettier N회
13. `ralph-prompt.md:26` `.ai/rules/` 전체 읽기 — 매 iteration 디스크 I/O
14. `fullstack.md:378` Zustand 판단 기준 모호 — 전역 상태 남용
15. `fullstack.md:131` 과도한 트랜잭션 scope — DB lock + retry loop

---

## 결정: 3단계 Fix Roadmap

### P0 — 즉시 (이 ADR + 본 브랜치에 적용)

**Turbopack 활성화:**
```json
// package.json
"dev": "next dev --turbopack",
"dev:webpack": "next dev",   // fallback
```

**typedRoutes를 build 타임 한정:**
```ts
// next.config.ts
const isBuild = process.env.NEXT_PHASE === "phase-production-build";
const nextConfig: NextConfig = {
  reactStrictMode: true,
  typedRoutes: isBuild,  // dev에선 false
  // ...
};
```

**`.next/` 캐시 주기적 정리 (주 1회):**
```bash
rm -rf frontend/.next
```

### P1 — 이번 주 (별도 PR, `.ai/` 원본 repo에서)

`.ai/`는 gitignored라 본 프로젝트에서 commit 불가. User의 main `.ai/` repo에서 별도 브랜치로 적용 후 배포:

1. **`.ai/stacks/nextjs-shared.md` 상단에 "Dev Performance" 섹션 신설**
   - Turbopack 기본 (`next dev --turbopack`)
   - `typedRoutes: isBuild`
   - `webpack: { watchOptions: { ignored: ['**/node_modules', '**/.next'] } }`
   - Tailwind v4 `@source` directive 권장

2. **`.ai/common/typescript.md` 하단에 "React Hook Deps 안정화" 섹션 신설**
   ```markdown
   ## 3. React Hook Dependencies (Client Components)

   ### useEffect / useCallback deps 안정화
   - Object literal / inline function을 deps에 두지 말 것
   - useMemo로 dependency 객체 메모이제이션
   
   ✅ const filters = useMemo(() => ({ status: "active" }), []);
   ❌ useEffect(() => { fetch({ status: "active" }) }, []);  // inline object
   ```

3. **`.ai/templates/settings.json.example` PostToolUse prettier hook을 주석 처리(opt-in)**

### P0 적용 결과 (2026-04-17 session2)

**Sprint 7c 후속 세션에서 context7 감사와 병행 처리:**

- ✅ P0 Turbopack/typedRoutes: 선행 세션에서 이미 적용 (commit e68a541, c568528)
- ✅ `QueryProvider` SSR-aware 패턴 추가 (context7 TanStack 공식) — `typeof window` 분기 + browser singleton. 이전 `useState` 패턴은 suspense boundary 부재 시 client 리셋 위험
- ✅ `step-code.tsx:28-37` useEffect deps 안정화 — `useRef(props.onParsed)` 캡슐화로 부모 re-render마다 parse mutation 재호출되던 잠재적 무한 루프 차단 (본 ADR #5 예제와 동일 패턴)
- ✅ Trading 모듈 폴링 완화 — 5s/10s → **30s** + `q.state.status === "error"`일 때 자동 일시 정지 (ADR 권장 ≥30초 준수)
- ✅ Trading 모듈 구조 재편 — `features/trading/{schemas.ts, query-keys.ts, hooks.ts, components/, index.ts}`. 기존 `features/trading/*.tsx`에서 `fetch()` 직접 호출하던 anti-pattern 제거 (Clerk JWT 주입 누락 보안 문제 동시 해소)
- ✅ `app/(dashboard)/error.tsx`, `strategies/{loading,error}.tsx` 추가 — Next.js 규약 기반 Suspense/ErrorBoundary 라우트 경계
- ✅ `strategies/page.tsx` 서버 prefetch + `HydrationBoundary` PoC — Clerk `auth()` 서버측 토큰으로 초기 waterfall 해소

**검증:** `pnpm tsc --noEmit` ✅ / `pnpm lint` ✅ / `pnpm test` 7/7 ✅

### P2 — Sprint 7d+ 이관

4. **`AGENTS.md:40` "완전한 코드" → "YAGNI-first"로 문구 완화**
5. **`AGENTS.md:54-55` Atomic Update 분리 허용** (code/docs 별도 commit OK)
6. **`.ai/templates/ralph-loop.md` 기본값 `--max-iterations 50 → 20`** + "dev server OFF 시에만 실행" 경고
7. **`.ai/stacks/fullstack.md` 폴링 interval 명시** (≥30초, 단기는 WebSocket/SSE)
8. **`.ai/project/lessons.md`에 "CPU 부하 anti-pattern" 섹션 신설** — 본 15건을 지식 자산으로 승격

---

## Dev CPU Budget 정책

각 프로젝트가 다음 기준 유지:

| 측정 | 목표 | Warning | Critical |
|---|---|---|---|
| `next-server` CPU (idle) | < 20% | 20~100% | > 100% |
| `next-server` CPU (HMR 직후) | < 100% | 100~200% | > 200% |
| `.next/` 크기 | < 200MB | 200~500MB | > 500MB |
| HMR cycle 시간 | < 300ms | 300~1000ms | > 1s |
| `fseventsd` CPU | < 10% | 10~30% | > 30% |

Critical 초과 시 **즉시** 본 ADR 참조 + fix 체크리스트 적용.

---

## 영향

- **이 프로젝트:** Turbopack 전환 즉시 `next-server` CPU 50% 이하로 떨어질 것으로 기대 (Next.js 공식 benchmark 5~10배 개선 보고)
- **다른 프로젝트:** `.ai/rules/` P1/P2 적용 후 반복 안 됨. User의 "여러 프로젝트에서 재현" 이슈가 해소
- **LLM이 짜는 코드 품질:** "완전한 코드" 완화가 YAGNI 유도 → dev loop 빨라짐

---

## 재검토 조건

1. Turbopack이 Next.js 16.2.3에서 Monaco/Clerk와 호환성 이슈 발생 시 → `dev:webpack` fallback
2. `typedRoutes: isBuild`로 dev에서 type-safe route 경고 누락 체감 큼 → 수동 검사 script 추가
3. User의 `.ai/rules/` 원본이 P1/P2 적용 완료 → 본 ADR의 roadmap 섹션을 "완료"로 업데이트

---

## 관련 자산

- Sprint 7c PR #13 (Strategy CRUD UI) — 본 CPU 분석이 Playwright MCP smoke 중에 도출됨
- `AGENTS.md` — 본 ADR이 지적하는 anti-pattern 1, 4, 6의 위치
- `.ai/stacks/` — P1 수정 대상 (별도 repo 작업)
- `docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md` — design review 7-pass 중 CPU 언급 없었던 회고 증거
