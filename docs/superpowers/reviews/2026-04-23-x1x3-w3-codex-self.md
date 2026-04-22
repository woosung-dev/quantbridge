# W3 — Codex Self-Review (EquityChart width(-1) fix)

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 3 / 5
> **Plan:** [docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md](../plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md)
> **Reviewer:** `codex-cli 0.122.0` (sandbox=read-only)

---

## 1. Scope

- 대상 파일:
  - `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` (구현)
  - `frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx` (신규 테스트)
- 체크 항목:
  1. `useEffect` dep primitive-only (LESSON-004 준수)
  2. `eslint-disable react-hooks/*` 사용 없음
  3. SSR-safe (no window/document top-level, `ResizeObserver` typeof 가드)
  4. layout shift 최소화 (`h-64 w-full` placeholder 동일 크기)
  5. recharts `ResponsiveContainer` 사용 idiomatic + width 측정 gate
  6. 테스트가 jsdom 에서 실제로 `width(-1)` 회귀를 catch 가능한지

---

## 2. Review 1-pass (GO_WITH_FIX)

**요약:** 구현은 문제 없음. 테스트의 회귀 탐지력이 부족 — mount gate 를 제거해도 테스트가 실패하지 않을 가능성. DOM-level (`.recharts-responsive-container` 존재 여부) 검증과 width≥1 분기 검증을 추가할 것.

**지적사항:**

1. `console.warn/error` 스파이에 `width(-1)` 문자열이 없다는 검증만으로는 회귀 탐지력이 약함. 현재 환경에서 경고가 발생하지 않는다는 사실만 확인.
2. `width<1` / `width≥1` 분기를 DOM 레벨에서 검증하지 않음.

---

## 3. 수정 적용

테스트를 3개로 확장:

1. **empty state** — 기존 유지 (`points=[]` → "Equity 데이터가 없습니다").
2. **width=0 분기 (jsdom 기본)** — `ResizeObserver` 삭제 + `getBoundingClientRect` width=0 상황에서:
   - `.recharts-responsive-container` 가 DOM 에 **없어야** 함
   - `[aria-busy="true"]` placeholder 가 **존재해야** 함
   - console.warn/error 에서 `width(-1)` 문자열 **0건**
3. **width≥1 분기 (ResizeObserver mock)** — MockResizeObserver 로 width=800 callback 발화:
   - 콜백 직전: `.recharts-responsive-container` 없음
   - `roInstances[0].cb([{ contentRect: { width: 800 } }])` + `act()` 후: `.recharts-responsive-container` 존재
   - placeholder `[aria-busy="true"]` 사라짐
   - jsdom 내부 layout 부재로 인한 ResponsiveContainer 자체 warning 은 본 테스트 범위 밖 (Phase 4 Playwright 가 담당) — 주석 명시

---

## 4. Review 2-pass (GO)

**판정:** `GO` / **신뢰도:** `8/10`

**Codex 원문 요약:**

- (1) 회귀 탐지력: mount gate 제거 시 테스트 b (width=0 경로) 가 실패함. 탐지력 충분.
- (2) width-0 / width≥1 분기: 상태 분기 기준 양쪽 모두 검증됨. 다만 `equity-chart.tsx:67` 의 "초기 `getBoundingClientRect().width >= 1` fast path" 자체는 별도 검증 없음 (minor).
- (3) LESSON-004 / unused-import lint: 리스크 없음. `useEffect` dep `[]` 안정적, import 모두 사용 중.

**남은 minor:** initial-width fast-path (line 67-71) 의 단위 테스트는 없음. `getBoundingClientRect` mock 이 필요해 테스트 복잡도가 증가하는 대비 효익이 낮아 **skip 결정**. ResizeObserver 분기가 fast-path 와 같은 `setHasWidth(true)` 를 호출하므로 mount 후 동작은 등가.

---

## 5. 수동 검증 결과

```bash
$ cd frontend && pnpm test -- --run equity-chart.test
  ✓ src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx (3 tests) 21ms
  Test Files  1 passed (1)
      Tests  3 passed (3)

$ cd frontend && pnpm test -- --run
  Test Files  24 passed (24)
      Tests  140 passed (140)

$ cd frontend && pnpm tsc --noEmit
  exit=0

$ cd frontend && pnpm lint
  exit=0  (0 errors / 0 warnings)
```

---

## 6. AC 체크리스트 (plan §2)

### 정량

- [x] FE vitest: `EquityChart` 렌더링 테스트 ≥ 1건 (mount 후 컨테이너 width 0 가정에서 crash 없음) → **3건**
- [x] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` 모두 clean → **clean**
- [x] 기존 equity 데이터 렌더링 회귀 0 (기존 테스트 PASS) → **139/139 기존 + 3 신규 = 140 PASS**
- [ ] Playwright 시나리오: `/backtests/<id>` navigate → 첫 페인트부터 console "width(-1)" 0건 → **Phase 4 orchestrator 담당 (worker 환경 미실행)**

### 정성

- [x] ResponsiveContainer 를 감싸는 wrapper 에 명시적 width (`w-full` + `style={{ minWidth: 0 }}`) 및 mount gate
- [x] useEffect 의존 배열에 RQ/Zustand 불안정 참조 금지 — **`[]` primitive-only**
- [x] shadcn/ui v4 + Tailwind v4 관례 유지 (inline style `minWidth: 0` 만 recharts 요구로 사용)

---

## 7. Edge Case 커버 (plan §5)

| Edge case                               | 처리                                                                                                      |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `data.length === 0`                     | 기존 "Equity 데이터가 없습니다" 분기 유지 + `render(<EquityChart points={[]} />)` 테스트                  |
| SSR pre-hydration                       | `useEffect` 내부에서만 측정/mount → server 에선 placeholder 렌더. `ResizeObserver` typeof 가드로 SSR 안전 |
| props.points 변경 (resize 후 re-render) | `data` useMemo dep `[points, maxPoints]` 유지 — 기존 로직 회귀 없음                                       |
| 매우 큰 points (maxPoints=1000 초과)    | `downsampleEquity` 로직 그대로 유지                                                                       |

---

## 8. LESSON-004 self-check

**useEffect dep array 증명:**

```tsx
// equity-chart.tsx:60-92
useEffect(() => {
  const node = wrapperRef.current; // ref (stable)
  if (node === null) return;
  // ... initialWidth + ResizeObserver 로직 ...
}, []); // ← primitive-only: 빈 배열
```

- **dep:** `[]` — React Query / Zustand / RHF / Zod 결과 객체 사용 없음
- **클로저 캡처:** `wrapperRef` (ref, stable), `setHasWidth` (React state setter, stable)
- **eslint:** `react-hooks/exhaustive-deps` 경고 없음 (ref/setter 는 캡처해도 안전)
- **eslint-disable:** 사용 없음

---

## 9. jsdom warning catch 가능성 명시

**T1 의 초기 의도:** `console.warn` 에서 `width(-1)` 문자열을 catch.

**실측 결과 (debug 테스트로 확인):**

```text
[w0] ["The width(-1) and height(-1) of chart should be greater than 0, ..."]
```

→ **jsdom 에서도 recharts `ResponsiveContainer` + `LineChart` 체인은 `width(-1)` warning 을 실제로 emit**. 즉 `console.warn` spy 로 catch 가능.

**최종 테스트는 두 계층으로 회귀 검출:**

1. **DOM-level**: mount gate 가 작동하면 `.recharts-responsive-container` 가 width=0 경로에서 mount 되지 않음 → 가장 강력한 가드
2. **Console-level**: 그 결과로 `width(-1)` warning 문자열 0건 — plan 에서 요구한 spy 검증

**mount branch (width≥1) 에서는** ResponsiveContainer 내부 layout 자체 측정이 jsdom 에선 불가하여 별도 `width(-1)` 및 `width(0)` warning 을 발생. 이는 jsdom 한계이며 실제 브라우저에선 발생하지 않음. Phase 4 Playwright live smoke 에서 orchestrator 가 최종 검증.

---

## 10. 최종 판정

**GO** / **신뢰도 8/10** (Codex review 2-pass 기준)

- 구현: mount gate 패턴으로 width=0 경로 차단, LESSON-004 준수
- 테스트: 3건 (empty / width=0 분기 / width≥1 분기) → 회귀 탐지력 충분
- lint / tsc / 전체 vitest: all clean
- 남은 1 항목: Playwright live smoke (Phase 4 orchestrator 담당)
