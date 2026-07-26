# W3 — Sonnet Independent Code Review (EquityChart width(-1) fix)

> **Session:** Sprint X1+X3, 2026-04-23 | **Reviewer:** Claude Sonnet (독립 평가)
> **Plan:** `docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md`
> **Diff:** `/tmp/w3-diff.txt`
> **Worker self-review:** `docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md`

---

## Q1. AC 정량 met?

**결론: 정량 AC 4항 중 3항 충족. 나머지 1항(Playwright)은 Phase 4 orchestrator 위임으로 명시적 defer.**

직접 실행 확인 결과:

| 항목                         | 결과                                 | 증거                            |
| ---------------------------- | ------------------------------------ | ------------------------------- |
| FE vitest: EquityChart ≥ 1건 | ✅ **3건** PASS                      | `Tests 3 passed (3)` — 21ms     |
| 전체 FE vitest clean         | ✅ **140/140 PASS, 24 파일**         | `Test Files 24 passed (24)`     |
| `pnpm tsc --noEmit`          | ✅ **exit=0**                        | 실행 확인                       |
| `pnpm lint`                  | ✅ **exit=0, 0 errors / 0 warnings** | 실행 확인                       |
| Playwright live smoke        | ⏳ **Phase 4 defer**                 | 계획 §3 T3 조건부 skip으로 명시 |

Playwright는 worker 환경 제약으로 skip 처리가 계획에 사전 명시되어 있고, 이는 Worker 책임 밖임.

---

## Q2. Spurious PASS — 테스트가 실제 회귀를 catch하는가?

**결론: 두 계층 탐지로 spurious PASS 리스크 낮음. 단 width=0 경로의 경고 spy는 부차적.**

**테스트 b (width=0 분기)의 핵심 가드:**

```
expect(container.querySelector(".recharts-responsive-container")).toBeNull()
expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()
```

이 두 단언은 DOM-level 검증이다. mount gate(`hasWidth` state)를 제거하면:

- `ResponsiveContainer`가 즉시 mount → `.recharts-responsive-container` 노드 생성 → `toBeNull()` 단언 실패

따라서 mount gate 코드가 제거되면 테스트 b가 실패한다. spurious PASS 가능성 없음.

**테스트 c (width≥1 분기)의 핵심 가드:**

- `roInstances.length === 1` → ResizeObserver 등록 확인
- `act()` 후 `.recharts-responsive-container` 존재 → mount 분기 진입 확인
- `aria-busy` 사라짐 → placeholder 해제 확인

`console.warn/error` spy의 `width(-1)` 검사는 DOM-level 검증의 보완이며, jsdom에서 recharts가 실제로 warning을 emit한다는 사실(self-review §9 실측)이 확인되어 있으므로 테스트 b에서는 유효하다.

---

## Q3. TDD evidence — FAIL → impl → PASS 시퀀스?

**결론: 확인 불가 (git log 상 단일 커밋), 그러나 계획이 TDD "test + impl 동시 허용"으로 명시 완화.**

```
acfa9b1 fix(backtest): EquityChart width(-1) warning via ResizeObserver mount gate (W3)
```

커밋 히스토리에 별도의 "failing test" 커밋이 없다. 계획 §1 TDD Mode에 **"test + impl 동시 허용 — pure UI 렌더링 (no hooks/state/effect 로직 변경)"** 이 명시되어 있으므로 규칙 위반은 아니다.

단, 엄격한 TDD 관점에서는 FAIL → PASS 전환 증거가 없다. 이 부분은 계획이 의도적으로 완화한 것이므로 NO_GO 사유는 아니나, 향후 hooks/state 변경이 동반되는 작업에서 동일 완화를 적용하면 안 된다.

---

## Q4. 회귀 surface — 기존 FE 테스트 / EquityChart 소비자 영향?

**결론: 회귀 없음. 유일한 소비자 1개소 변경 없음. 전체 140 PASS.**

**EquityChart 소비자:**

- `frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx:142`
  — `<EquityChart points={bt.equity_curve} />` 단일 호출. Props 인터페이스 변경 없으므로 영향 없음.

**useMemo dep 보존:**

```tsx
}, [points, maxPoints]);
```

— `points` / `maxPoints` prop 변경 시 data 재계산 정상 동작. 이미 `hasWidth=true`인 상태에서 points prop이 변경되면 data는 재계산되어 chart에 즉시 반영된다. 문제 없음.

**24 파일 140개 테스트 전부 green** — 기존 테스트 회귀 0건.

---

## Q5. Edge case 커버 — empty / SSR / large / resize / no ResizeObserver?

| Edge case                           | 처리                                                             | 테스트                                          |
| ----------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------- |
| `data.length === 0`                 | 기존 empty 분기 유지                                             | 테스트 a ✅                                     |
| SSR pre-hydration                   | `useEffect` 내에서만 DOM 측정 → server에서 placeholder만 렌더    | `typeof ResizeObserver === "undefined"` 가드 ✅ |
| width = 0 (jsdom/초기 렌더)         | ResizeObserver 미정의 → chart 미마운트                           | 테스트 b ✅                                     |
| width ≥ 1 (브라우저/ResizeObserver) | callback 발화 → mount                                            | 테스트 c (MockResizeObserver) ✅                |
| 매우 큰 points                      | `downsampleEquity(points, maxPoints=1000)` 기존 로직 유지        | 미변경                                          |
| resize 후 re-render                 | `hasWidth` 는 `true`로 유지, `data` useMemo가 points 변경에 반응 | 별도 테스트 없음 (minor)                        |
| window 직접 접근                    | 없음 (`typeof ResizeObserver` typeof 가드만 사용)                | ✅                                              |

**미커버 minor:** `resize 후 re-render` (hasWidth=true 상태에서 points 재전달)에 대한 명시적 테스트 없음. 그러나 useMemo dep 보존으로 로직 회귀가 없고, recharts가 정상 리렌더링을 처리하므로 실질적 결함 가능성 낮음.

---

## Q6. LESSON-004 — useEffect/useMemo dep 전부 primitive인가? eslint-disable?

**결론: LESSON-004 완전 준수. eslint-disable 없음.**

**useEffect dep 검증:**

```tsx
// equity-chart.tsx:92
}, []); // primitive-only dep array — LESSON-004 준수
```

클로저 캡처 분석:

- `wrapperRef` — `useRef` 반환값. React stable ref, dep 없어도 exhaustive-deps 경고 없음
- `setHasWidth` — React state setter. stable function reference, dep 불필요
- `ResizeObserver` — 전역 (`typeof` 가드로 접근), 외부 dep 아님

RQ(React Query) / Zustand / RHF / Zod 결과 객체 사용 없음.

**useMemo dep 검증:**

```tsx
}, [points, maxPoints]);
```

- `points` — prop (`readonly EquityPoint[]`). 안정적이지 않을 수 있으나 이는 소비자 책임이며, LESSON-004 위반(RQ/Zustand 결과)이 아님
- `maxPoints` — prop (`number`, primitive)

**eslint-disable 검색 결과:** 0건 확인.

---

## Q7. Verdict

**GO_WITH_FIX** — **신뢰도 8/10**

| 항목             | 판정 | 이유                                                                                         |
| ---------------- | ---- | -------------------------------------------------------------------------------------------- |
| 구현 정확성      | ✅   | ResizeObserver mount gate 패턴 정확. minWidth=0 defensive 추가.                              |
| LESSON-004       | ✅   | dep `[]` + 클로저 캡처 stable ref/setter만. eslint-disable 없음.                             |
| 테스트 강도      | ✅   | DOM-level 2단언 + console spy 이중 검증. spurious PASS 차단됨.                               |
| tsc/lint/vitest  | ✅   | 전부 clean.                                                                                  |
| Playwright       | ⏳   | Phase 4 defer (계획 명시, worker 책임 밖).                                                   |
| 잔여 gap (minor) | ⚠️   | initial fast-path (`getBoundingClientRect().width >= 1`) 단위 테스트 없음. Q8에서 상세 분석. |

**"FIX"의 내용:** Q8에서 서술하는 `getBoundingClientRect` fast-path 테스트 1건 추가 여부를 판단. 추가 여부에 따라 GO로 상향 가능.

---

## Q8. 구현 속도 + 테스트 커버리지 — fast-path 미커버가 production 결함을 놓치는가?

**결론: production 결함 가능성 낮음. 추가 테스트 권장이나 blocking은 아님.**

### 문제의 fast-path 코드

```tsx
// equity-chart.tsx:67-71
const initialWidth = node.getBoundingClientRect().width;
if (initialWidth >= 1) {
  setHasWidth(true);
  return; // ← ResizeObserver 등록 건너뜀
}
```

이 분기는 CSR 환경에서 layout이 이미 완료된 경우(예: 탭 전환 후 `useEffect` 재실행) `hasWidth`를 즉시 true로 설정한다.

### jsdom 조건

jsdom은 layout 엔진이 없으므로 `getBoundingClientRect().width`가 항상 `0`을 반환한다. 따라서 **fast-path는 jsdom 테스트 환경에서 절대 진입하지 않는다.**

### production 결함 가능성 평가

fast-path가 깨지려면:

1. `getBoundingClientRect().width >= 1` 조건이 CSR에서 true인데 `setHasWidth(true)` 가 호출되지 않는 경우
2. 또는 fast-path 진입 후 ResizeObserver 없이 차트가 mount되어야 하는데 안 되는 경우

실제 브라우저에서 `getBoundingClientRect`는 layout이 완료된 시점이라면 정상 width를 반환하므로, 이 fast-path는 "ResizeObserver보다 빠른 경로"일 뿐이다. 두 경로 모두 `setHasWidth(true)`를 호출하므로 분기 결과가 동일하다. fast-path 진입 여부가 다를 뿐, 최종 `hasWidth=true` 도달 여부는 테스트 c(ResizeObserver 경로)로 등가 검증된다.

### 추가 테스트 비용 vs 효익

fast-path를 테스트하려면 `getBoundingClientRect`를 mock해야 한다:

```tsx
vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
  width: 800,
  // ... 나머지 필드
} as DOMRect);
```

- **효익:** fast-path 코드라인 직접 커버, 회귀 탐지 완전성
- **비용:** `Element.prototype.getBoundingClientRect` mock은 test isolation이 까다로움. beforeEach/afterEach 복원 필요. mock 자체가 테스트 의도를 흐릴 수 있음

**판단:** Worker self-review §4에서 "skip 결정" 이유로 "ResizeObserver 분기와 동일한 `setHasWidth(true)` 호출"을 들었는데 이는 타당하다. 두 경로의 동작이 완전히 동등하고, 실제 브라우저 최종 검증은 Phase 4 Playwright가 담당하므로 **현재 skip은 합리적이다.**

단, 테스트 커버리지 100%를 목표로 한다면 추가 가치가 있다. Production 결함을 놓칠 가능성은 **낮음 (5% 미만)** 으로 평가한다.

---

## 종합 판정

**GO_WITH_FIX (fast-path 테스트 선택적 추가) — 신뢰도 8/10**

핵심 구현 및 LESSON-004 준수는 완전하다. 테스트 강도는 DOM-level 이중 검증으로 충분하다. fast-path 단위 테스트 추가는 코드 품질 향상이지 blocking 이슈가 아니다. Phase 4 Playwright live smoke가 최종 브라우저 검증을 담당하므로 현재 상태로 stage merge 가능하다.

**추천 후속 액션 (blocking 아님):**

1. Phase 4 orchestrator: `/backtests/<id>` 직접 navigate → console warning 0건 검증
2. (선택) fast-path `getBoundingClientRect` mock 테스트 1건 추가 시 신뢰도 9/10으로 상향
