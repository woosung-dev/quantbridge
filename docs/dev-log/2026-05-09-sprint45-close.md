# Sprint 45 close-out — Surgical Cleanup (#4 + #3, #1 skip)

**머지 일자**: 2026-05-09
**main HEAD**: `8d23210` (PR #226 squash)
**전 단계 main**: `4ce4d02` (Sprint 44 close-out doc PR #225)
**원래 Sprint 44 코드 main**: `51eca89` (PR #224, fidelity iter 2 + cross-page polish)

## 산출 요약

Sprint 44 deferred 항목 surgical cleanup. 1 worker 단일 작업 (자율 병렬 cmux 불필요). 분량 추정 3-5h, 실 소요 ~2h.

| Phase                                      | 결과         | 분량 | 비고                                                                     |
| ------------------------------------------ | ------------ | ---- | ------------------------------------------------------------------------ |
| Phase 0 (kickoff baseline)                 | ✅           | 5m   | vitest 603 / tsc clean / lint clean / build pass / dev clean             |
| Phase 1 (#4 dashboard-shell 추출)          | ✅           | 1h   | 235L → 60L slim Shell + 3 신규 (Sidebar 79L / Header 51L / NavList 102L) |
| Phase 2 (verification gate)                | ✅           | 10m  | 603 PASS / tsc clean / lint clean / build pass (회귀 0)                  |
| Phase 3 (#3 codex G.4 review timeboxed 4h) | ✅ GATE PASS | 10m  | P1 = 0 / P2 = 1 (Sprint 46 큐)                                           |
| Phase 4 (close-out)                        | ✅           | 30m  | 본 doc + BL 등재 + LESSON 후보 + MEMORY                                  |

**합계**: 1 PR (#226) / 5 files / +250 / -190 lines (delta +60) / 회귀 0 / **603 → 603 PASS** (refactor only).

## #1 71007 skip 결정 (사용자 ★★★★★, 2026-05-09)

Sprint 44 close-out doc 의 71007 warnings memo 가 production 영향이 있는 issue 처럼 표기됐지만, baseline 검증 결과 IDE-only 진단으로 확인됨:

- 71007 = `INVALID_CLIENT_ENTRY_PROP` (Next.js TypeScript plugin 코드, `node_modules/next/dist/server/typescript/constant.js`)
- `pnpm build` / `pnpm tsc --noEmit` / `pnpm lint` / `pnpm dev` 모두 clean (warning 0건)
- production / CI 영향 0
- VS Code Next.js TS plugin 화면에만 표시되는 진단으로 추정

**fix 적용 = unwarranted change** (CLAUDE.md "Read Errors, Don't Guess" 위반). Sprint 44 close-out doc memo 갱신으로 종결.

## #4 dashboard-shell.tsx 추출 (LESSON-054 deferred)

### 분리 구조 (235 → 60 + 79 + 51 + 102 = 292 LOC)

| 신규 컴포넌트           | LOC | 책임                                                     | Props                                         |
| ----------------------- | --- | -------------------------------------------------------- | --------------------------------------------- |
| `DashboardShell` (slim) | 60  | useUiStore + usePathname + derivePageTitle + composition | `{ children: ReactNode }`                     |
| `DashboardSidebar`      | 79  | 로고 + NavList + footer dock(UserButton)                 | `{ sidebarOpen, pathname }`                   |
| `DashboardHeader`       | 51  | 모바일 햄버거 + 페이지 타이틀 slot + 모바일 UserButton   | `{ sidebarOpen, onToggleSidebar, pageTitle }` |
| `DashboardNavList`      | 102 | NavItem[] 6개 + pathname 기반 isActive 로직              | `{ sidebarOpen, pathname }`                   |

### Sprint 44 wc1 inline polish 보존 (회귀 0)

- Active state 정합: `bg-[color:var(--primary-light)] text-[color:var(--primary)] font-medium border-l-[3px] border-[color:var(--primary)] pl-[9px]` (DESIGN.md §10.2)
- Hover transition: `motion-safe transition-[background-color,color,padding-left] duration-200` cubic-bezier 표준
- 모바일 햄버거: Menu lucide icon + 44×44 hit area + bg-alt hover transition 150ms

### 검증 (Phase 2 자동 게이트)

- `pnpm test`: **603 PASS / 117 files** (회귀 0)
- 기존 `dashboard-shell.test.tsx` 5 tests 모두 PASS (DashboardShell integration behavior 보존 검증)
- `pnpm tsc --noEmit`: clean
- `pnpm lint`: clean
- `pnpm build`: Next.js 16 strict 통과

## #3 codex G.4 review (timeboxed 4h, 실 소요 ~10m)

대상 diff: Sprint 44+45 합산 = `0ae3564..8d23210` (89 files / +1250 lines).

`codex review --base 0ae3564 --title "Sprint 44+45 합산 review" -c model_reasoning_effort=high --enable web_search_cached`

**GATE: PASS** (P1 = 0건).

### P2 finding 1건 (Sprint 46 큐 등재)

- **[P2] qb-form-slide-down animation truncation** — `frontend/src/styles/globals.css:582`
  - `both` fill mode + `FormErrorInline` 의 `overflow-hidden` 조합
  - 600px 초과 콘텐츠 영구 truncation
  - 영향: Pine Script 다수 미지원 함수 발견 시 unsupported-builtins 에러의 actionable hint list 잘림
  - Sprint 44 wc2/wc3 cross-page polish 누적의 미세 regression
  - Sprint 46 후보 BL 등재 (BL-195)

## 사용자 결정 (2026-05-09)

- **Sprint 45 방향** = ★★★ "Sprint 44 deferred cleanup ONLY" 후 → ★★★★★ Plan agent 권장 3-item 정제 (#1+#3+#4) 후 → ★★★★★ baseline 결과 반영 #1 skip → 최종 = #4 + #3 + Sprint 44 close memo 갱신
- **codex review 순서** = ★★★★★ "PR squash merge 먼저 + main 에서 review" (Sprint 44 패턴 동등)
- **commit 패턴** = ★★★★★ "2개 semantic commit + push + PR (표준)" — `docs(sprint44-close)` + `refactor(layout)` split
- **Manual browser smoke** = 생략 (visual 변경 0 + vitest 5 PASS + build 통과)

## 보존된 비즈니스 로직 (회귀 0건)

- Sprint 41-B2 sidebar 220px / collapsed 64px / 모바일 hidden
- Sprint 42-polish-3 화이트 모드 통일 (`[data-theme="dash"]` scope 제거 그대로)
- Sprint 44-WC1 active 정합 + hover transition + 햄버거 hit area
- pathname 기반 isActive 로직 (effect 없음, render-time clamp 패턴)
- DESIGN.md §10.2 prototype 06 정합 (border-left + padding-left compensation)
- Clerk UserButton 통합 (sidebar footer + 모바일 헤더 우측)

## LESSON 신규 후보 (gitignored 등재 예정)

**LESSON-057 후보** (Next.js 16 71007 IDE-only 진단 검증 패턴):

- 71007 = `INVALID_CLIENT_ENTRY_PROP` (Next.js TypeScript plugin)
- production / CI 영향 검증 없이 fix 적용 = CLAUDE.md "Read Errors, Don't Guess" 위반
- baseline 측정 게이트 = `pnpm build` + `pnpm tsc --noEmit` + `pnpm lint` + `pnpm dev` 모두 clean = IDE-only 진단 결론
- Sprint 45 적용 사례 = #1 skip 결정 (사용자 ★★★★★)
- 향후 IDE 진단 메모는 baseline 재현 검증 후 fix 우선순위 판정 의무

**LESSON-058 후보** (codex review CLI mutual exclusion):

- `codex review` 의 `[PROMPT]` 와 `--base <BRANCH>` 는 mutually exclusive
- focus context 전달 시 `--title "<focus>"` 옵션 사용 (review summary 에 표시)
- 또는 base 만 사용 후 codex 자동 review (focus 없음)
- /codex skill 의 "filesystem boundary 항상 prepend" 지침은 codex review subcommand 에서 적용 불가 — codex exec mode 만 적용

## 영구 자산 추가

- `frontend/src/components/layout/dashboard-shell.tsx` (235 → 60, slim composition root)
- `frontend/src/components/layout/dashboard-sidebar.tsx` (79 LOC, 신규)
- `frontend/src/components/layout/dashboard-header.tsx` (51 LOC, 신규)
- `frontend/src/components/layout/dashboard-nav-list.tsx` (102 LOC, 신규 — `navItems` const + NavList 분리, 향후 router 추가 시 본 파일에서 변경)
- `docs/dev-log/2026-05-08-sprint44-close.md` 71007 IDE-only memo 갱신

## 주의 / 미해결 (Sprint 46+ 이관)

- **BL-195 신규** [P2] `qb-form-slide-down` truncation (codex review 발견)
- **#2 Playwright 16 시나리오** — dogfood Phase 2 critical bug 발견 시 trigger
- **#5 Dark mode toggle (단독 sprint)** — Tailwind v4 `@variant dark` / `[data-theme="dark"]` 전략 사전 결정 + ~40 file 마이그레이션 + ThemeProvider + toggle UI (8-12h)
- **dogfood Phase 2 본격 운영** — 사용자 manual (본인 Day 2~7 + micro-cohort 카톡 DM, 1-2주 wall-clock)
- **#1 71007** — IDE 환경에서 재현 시 별도 BL 등재 후 처리

## 다음 분기 (Sprint 46 trigger)

Sprint 45 surgical cleanup 완료 + visual fidelity 누적 + dashboard-shell 추출 모두 정합. Sprint 46 = **dogfood Phase 2 결과 (1-2주 wall-clock) 따라 결정**:

- **dogfood 통과** (critical bug 0 + NPS ≥7) → Sprint 46 = **Beta 본격 진입** (BL-070~075 도메인 + DNS / Backend 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)
- **회귀 발견** → Sprint 46 = polish iter (해당 hotfix)
- **mainnet trigger 도래** → Sprint 46 = BL-003 / BL-005 mainnet 본격 (사용자 결정)
- **Dark mode toggle 도전** → Sprint 46 = LESSON-054 all-or-nothing 단독 sprint (~40 file)

dogfood data 가 없는 상태에서 Sprint 46 = 다른 surgical cleanup 추가 가능 (BL-195 + Playwright 16 시나리오 + dark mode 일부) — 하지만 dogfood 운영 우선이 우선순위 정합.

## 다음 세션 시작 prompt

```
Sprint 46 진행해줘
```

memory `MEMORY.md` 의 most-recent sprint entry (Sprint 45 완료) 자동 추적. /context-restore 사용 금지.
