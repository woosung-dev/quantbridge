# ADR-017: FE Polish Bundle 1/2 묶음 회고 (FE-01~04 + FE-A~F)

> **상태:** 회고 (사후 기록, 2026-04-23 작성)
> **일자:** 2026-04-19 ~ 2026-04-20
> **관련 PRs:** #23~#27 (FE-01~04), #29~#35 (FE-A~F)
> **관련 LESSON:** LESSON-004 (useEffect CPU 100%), LESSON-005 (RQ queryKey userId), LESSON-006 (React Compiler ref mutate)
> **상위 문서:** [`04_architecture/system-architecture.md`](../04_architecture/system-architecture.md)
> **합본 이유:** 10건의 개별 sprint 를 모두 ADR 화하면 잡음 ↑. 공통 주제 (FE UX 완성도 + 자율 병렬 Option C 실증) 으로 묶어 의사결정의 흐름과 학습 정리

---

## 1. 배경

Sprint 7c (Strategy CRUD UI) 이후 dogfood 준비 단계에서 FE 편집 경험이 아직 거친 상태였다. BE 는 Sprint 7d/8c 으로 진전됐으나, FE 는:

- Strategy Edit 의 Pine 이터레이션 UX 파편적
- Backtest UI MVP 부재 (form/polling/chart/table)
- Trading 대시보드 모바일 overflow
- 단축키 / CTA / 삭제 UX 등 **소소한 품질 이슈** 누적

이 모든 이슈를 **H2 Build-in-Public 진입 전** 해소해야 "돈 받고 쓰는 품질" 주관 기준 충족. Sprint 단위로 쪼개면 10건 이상 필요 → 자율 병렬 실행 으로 시간 압축.

---

## 2. 결정 요약

### 2.1 Bundle 구성

**Bundle 1 (FE-01~04)**: 핵심 기능 UX

- FE-01: TabParse 1질문 UX (PR #23/#24, ParseDialog 3 iter)
- FE-02: FE tech debt 제로 + CI 복원 (PR #25)
- FE-03: Edit page Zustand lift-up + Save + unload 경고 (PR #27)
- FE-04: Backtest UI MVP (PR #26, form/polling/chart/table)

**Bundle 2 (FE-A~C)**: Polish Bundle 1

- FE-A: Landing `/` + `/dashboard` 일관성 (PR #30)
- FE-B: `/trading` 모바일 overflow + 빈 상태 UX (PR #29)
- FE-C: 단축키 help dialog + draft userId scoping (PR #31)

**Bundle 3 (FE-D~F)**: Polish Bundle 2

- FE-D: Strategy form chip-style tag input (PR #33)
- FE-E: DeleteDialog 모바일 bottom sheet (<768px) (PR #34)
- FE-F: Edit → Backtest CTA + strategy_id prefill (PR #35)

### 2.2 실행 패턴 — 자율 병렬 Option C (Stage Branch)

- **cmux 3 워커** 동시 실행 (각 sprint 독립)
- **Stage Branch (`stage/fe-polish`, `stage/fe-polish-b2`)**: main 직접 touch 금지 + deny 조작 불필요. 워커는 stage/\* 에 push, 사용자가 수동 main merge
- **Signal 기반 IPC**: 완료 시 signal 파일 생성, orchestrator 가 감지 후 다음 바 순으로 merge

### 2.3 test 수 변화

| Sprint     |  FE tests  |
| ---------- | :--------: |
| (FE-01 전) |    ~20     |
| FE-01      |     35     |
| FE-02      |     53     |
| FE-03      |     59     |
| FE-04      |     86     |
| FE-A/B/C   |    110     |
| FE-D       |    118     |
| FE-E       |    124     |
| FE-F       | 128 (현재) |

추가로 FE-04 후속 TradingView-style Backtest Report (PR #50) 에서 **137 tests** (현재 프로젝트 157 tests 는 후속 추가분 포함).

---

## 3. LESSON (영구 규칙화)

### LESSON-004: React `useEffect([objectProp]) + setState` → CPU 100%

- **FE-01 iter-2** 에서 발견. ParseDialog 의 "result prop 축소 시 index 리셋" 방어막으로 `useEffect(() => setIndex(0), [result])` 추가
- 35/35 unit test + design-review live smoke 통과
- PR 직전 dev 서버 CPU 100% 폭주 → 사용자 시스템 종료
- **원인**: `result` 가 React Query `preview.data` 객체 참조. Fast Refresh / StrictMode 더블 인보크에서 참조 흔들림 → dep 인식 → setState → 재렌더 → 무한 루프
- **해결**: useEffect 제거. `clampedIndex = Math.min(index, steps.length - 1)` 로 render-time clamp
- **영구 규칙**: `react-hooks/set-state-in-effect` lint 규칙 disable 금지. RQ/Zustand/RHF/Zod 결과를 `useEffect` dep 로 쓰지 말 것
- **.ai/stacks/nextjs/frontend.md 승격 예정** (Path β Stage 0 C5)

### LESSON-005: React Query queryKey + Clerk JWT

- queryKey 에 `userId` identity만 포함. `getToken()` 직접 포함 금지 (매 호출 새 JWT → 매번 queryKey 달라짐 → 무한 refetch)
- **.ai/stacks/nextjs/frontend.md 승격 예정**

### LESSON-006: React Compiler 와 ref.current

- React Compiler 가 render 중 ref.current 직접 mutate 를 금지 (panic). `useEffect` 내부 또는 이벤트 핸들러에서만 허용
- **.ai/stacks/nextjs/frontend.md 승격 예정**

---

## 4. 자율 병렬 Option C 의 실증 (Sprint Bundle 1/2 평가)

### Bundle 1 실측 (FE-A/B/C 병렬)

- 사용자 개입 1회 ("ok" 1회)
- 총 소요 25분
- Evaluator 3/3 iter=1 PASS
- Blocker 0건

### Bundle 2 실측 (FE-D/E/F 병렬)

- 사용자 개입 0회 (worker prompt 0건)
- 총 소요 16분
- iter=1 3/3 + "ok" 1회 전부 달성
- BUG 3건 발견 (symlink · sig_id · plan dup — 스킬 repo 패치 후보)

### 결론

Option C (Stage Branch) 는 main 직접 touch 없이 충돌 제로로 3 sprint 를 동시에 수행. **자율 병렬의 기본 패턴** 으로 확립 (memory `feedback_merge_strategy_c_default.md` 로 규칙화).

---

## 5. 원안 대비 변경

Sprint 단위 초기 계획 (FE-01~10 개별 sprint) → Bundle 3묶음 (1+2+3) 로 통합. 이유:

- 개별 sprint 승인 체크포인트가 과도하게 많음 (memory `feedback_sprint_cadence.md`)
- 실제 작업 간 독립성 높음 → 병렬 실행 적합

---

## 6. 학습 (메타)

### L-1: 자율 병렬 Option C (Stage Branch) 를 default 로

- main 직접 touch 금지, deny 조작 불필요, stage/<theme> 경유 + 사용자 stage→main 수동
- Bundle 1/2 실측: 20h 추정 시간 → 25m+16m 로 ~33x 단축
- B/A (main touch) 는 보조 옵션으로만

### L-2: FE-specific LESSON 은 stack rule 로 승격해야 반복 방지

- LESSON-004/005/006 모두 Next.js + React 컴파일러 조합 특유의 함정
- `.ai/project/lessons.md` 에만 있으면 이 프로젝트만 방어. `.ai/stacks/nextjs/frontend.md` 로 승격해야 향후 FE 프로젝트에도 전파
- Path β Stage 0 C5 에서 공식 승격

### L-3: CPU 100% 같은 dev-only 이슈는 vitest 로 못 잡는다

- vitest jsdom 은 Fast Refresh / StrictMode 더블 인보크 조합 재현 못 함
- **hooks diff 가 있는 PR 은 live smoke 필수** — PR 템플릿에 체크박스 추가 고려

### L-4: Bundle 3묶음 전략은 Trust Pillar 완성 단계에서 효과적

- 독립적 소규모 개선을 한 번에 묶어서 dogfood 진입 장애물 제거
- 단, 공통 의존 (예: Zustand store 구조) 이 있으면 conflict → dependency graph 사전 확인 필요

---

## 7. 영향

### 코드

- FE: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/*`, `backtests/`, `trading/` 광범위 touch
- 신규 컴포넌트: ParseDialog, SessionChips, SaveBar, BacktestChart (recharts 3.8.1), ShortcutsHelpDialog, TagChipInput, DeleteBottomSheet
- Zustand: `draftStore` lift-up + userId scoping

### 테스트

- FE tests 20 → 128 (+108) 누적. 보수적으로 각 sprint 당 ~10 test.
- vitest jsdom + Playwright E2E (`pnpm e2e`) 조합

### 문서

- (본 ADR 로 공식 회고). `.ai/project/lessons.md` 의 LESSON-004/005/006 → `.ai/stacks/nextjs/frontend.md` 승격 (Path β S0-C5)

---

## 8. 다음 단계

- [x] LESSON-004/005/006 `.ai/stacks/nextjs/frontend.md` 승격 (Path β S0-C5)
- [x] 자율 병렬 Option C default 화 (memory 규칙화 완료)
- [ ] FE Sprint cadence 재검토 — 묶음 vs 개별 가이드라인 정리 (Path γ 이후)

---

## 9. 변경 이력

| 날짜       | 사유                  | 변경                                                     |
| ---------- | --------------------- | -------------------------------------------------------- |
| 2026-04-23 | 최초 작성 (사후 회고) | Path β Stage 0 Wave B. 10건 sprint 를 3 Bundle 묶음 회고 |
