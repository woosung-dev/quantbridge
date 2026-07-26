# W5 Sonnet 독립 코드 리뷰 — RerunButton

> Sprint X1+X3 W5, 2026-04-23  
> 리뷰어: Claude Sonnet 4.6 (독립 에이전트)  
> 입력: Plan (`docs/superpowers/plans/2026-04-23-x1x3-w5-rerun-button.md`) + Diff (`/tmp/w5-diff.txt`) + Codex Self-Review (`worktrees/agent-a0d2ef2b/docs/superpowers/reviews/2026-04-23-x1x3-w5-codex-self.md`)

---

## Q1. AC 달성 여부 — 정량 기준

| AC 항목                                                                    | 실제 달성                  | 근거 (file:line)                                                                                            |
| -------------------------------------------------------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 헤더에 "재실행" 버튼 1개, terminal 상태에서만 활성화                       | **PASS**                   | `backtest-detail-view.tsx:94-98` — `TERMINAL_STATUSES.includes(effectiveStatus)` 로 `isEnabled` 결정        |
| 클릭 → `useCreateBacktest.mutate()` → `onSuccess` 시 `router.push` + toast | **PASS**                   | `rerun-button.tsx:25-32, 45-52`                                                                             |
| 버튼 테스트 ≥ 3건 (enabled / disabled / mutate args)                       | **PASS**                   | `rerun-button.test.tsx` 6건 (enabled, disabled, mutate+push+toast, error toast, isPending, invalid capital) |
| `pnpm test -- --run` 151/151 green                                         | **PASS (self-report)**     | codex-self.md: "151/151 PASS" — 독립 실행 불가로 셀프 리포트 기준                                           |
| `pnpm tsc --noEmit` 0 errors                                               | **PASS (self-report)**     | codex-self.md: "0 errors"                                                                                   |
| `pnpm lint` 0 errors                                                       | **PASS (self-report)**     | codex-self.md: "0 errors"                                                                                   |
| mutation pending 동안 버튼 비활성 + Loader2 spinner                        | **PASS**                   | `rerun-button.tsx:34-35, 64-68`                                                                             |
| 에러 시 toast.error "재실행 실패: <message>"                               | **PASS**                   | `rerun-button.tsx:29-31`                                                                                    |
| 새 store/effect 추가 없음                                                  | **PASS** — 단 아래 Q6 참조 | `rerun-button.tsx` 전체에 `useEffect` 없음                                                                  |
| CTA 위치: 헤더 우측, 목록 링크 옆                                          | **PASS**                   | `backtest-detail-view.tsx:93-106` — `flex items-center gap-3` 래퍼에 `RerunButton` 먼저, 목록 링크 뒤       |

**총평: AC 정량 10/10 PASS.** 정성 항목도 모두 충족.

---

## Q2. Spurious PASS — Mock 엄밀성

단위 테스트(`rerun-button.test.tsx`)의 mock 구조를 직접 검토했다.

**강점:**

- `mockMutate`가 `mutate` 내부에서 실제 args를 forwarding 받아 호출된다 (`rerun-button.test.tsx:32-33`).
- 성공 케이스에서 `mockMutate` 인자를 `expect.objectContaining({ strategy_id, symbol, timeframe, period_start, period_end, initial_capital: 10000 })`로 명시 검증 (`rerun-button.test.tsx:97-108`).
- `mockPush`가 정확한 path(`/backtests/new-backtest-id`)로 호출되는지 검증 (`rerun-button.test.tsx:107`).
- `mockToastSuccess`와 `mockToastError` 각각 독립 스파이로 분리되어 교차 오염 없음.
- 에러 케이스에서 `mockPush.not.toHaveBeenCalled()` 명시 (`rerun-button.test.tsx:118`).
- `beforeEach`에서 모든 상태 변수를 리셋 (`rerun-button.test.tsx:64-73`).

**잠재적 spurious PASS 벡터 1건 (minor):**  
`expect.objectContaining()`은 추가 필드를 허용한다. 만약 구현이 의도치 않게 여분의 필드를 전달해도 통과한다. 그러나 `useCreateBacktest`가 `CreateBacktestRequest` 타입으로 강타입 검증되므로, 타입 시스템이 이를 컴파일 에러로 잡는다. 런타임 테스트 단독으로는 spurious PASS 위험이 낮다.

**판정: mock 엄밀성 ADEQUATE. 명시적 spurious PASS 위험 없음.**

---

## Q3. TDD — FAIL First 증거

diff에서 워크플로우를 역추적:

- 계획서 §4 T1 "Step 3 — 실패 확인: FAIL — `RerunButton` import 불가"가 명시되어 있다 (`plan.md:211`).
- codex-self.md에는 "Iteration 1 → GO_WITH_FIX → Iteration 2 → GO_WITH_FIX → Iteration 3 → GO"의 3-pass 이터레이션 기록이 있다 (`codex-self.md:16`).

**그러나:** diff 자체는 단일 커밋 (`5e963da feat(backtest): re-run button in detail header (W5)`)으로, FAIL 커밋이 별도로 존재하지 않는다. TDD FAIL-first는 계획서 명시 사항이지만 git history에서 독립적으로 검증 불가.

**판정: TDD FAIL-first는 계획서 명세에만 존재, git evidence 없음. [가정] 워커가 로컬에서 실행 후 단일 커밋으로 스쿼시했을 가능성이 높으나 단정 불가.**

---

## Q4. 회귀 — 기존 151건 테스트 유지

`backtest-detail-view.tsx` 변경은 diff 기준으로 **8줄 추가 (import 1 + JSX 7)** 뿐이다:

```diff
+import { RerunButton } from "./rerun-button";
...
-        <Link href="/backtests" ...>← 목록</Link>
+        <div className="flex items-center gap-3">
+          <RerunButton ... />
+          <Link href="/backtests" ...>← 목록</Link>
+        </div>
```

기존 useEffect 블록(`backtest-detail-view.tsx:47-52`), Tabs, InProgressCard, ErrorCard, 상태 분기 로직 전혀 건드리지 않았음을 diff에서 확인. `backtest-detail-view.rerun-integration.test.tsx`가 신규로 8건 추가되어 총 151건 = 기존 143건 + 신규 8건으로 해석된다.

**판정: 회귀 위험 없음. 변경 범위가 헤더 JSX에 국한되며 기존 로직 불변.**

---

## Q5. Edge Cases — 7개 시나리오 커버리지

| 시나리오                                               | 커버 | 위치                                                                                                                                         |
| ------------------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| terminal 상태 (completed/failed/cancelled) → 버튼 활성 | PASS | `rerun-button.test.tsx:80-83` (enabled=true) + integration `it.each(["completed","failed","cancelled"])`                                     |
| running → 버튼 비활성                                  | PASS | integration test `it.each(["queued","running","cancelling"])`                                                                                |
| pending → 버튼 비활성                                  | PASS | `rerun-button.test.tsx:121-126` (isPending=true)                                                                                             |
| success → router.push + toast.success                  | PASS | `rerun-button.test.tsx:92-109`                                                                                                               |
| error → toast.error, push 없음                         | PASS | `rerun-button.test.tsx:111-118`                                                                                                              |
| invalid capital (0) → mutate 안 호출 + toast.error     | PASS | `rerun-button.test.tsx:128-137`                                                                                                              |
| effectiveStatus 우선순위 (progress > bt.status)        | PASS | integration: `detail=completed,progress=running → disabled` + `detail=running,progress=completed → enabled` (`integration.test.tsx:105-119`) |

**판정: 계획서 §5 EdgeCases 7개 시나리오 전부 커버.**

---

## Q6. LESSON-004 — useEffect 추가 없음 (grep 증거)

**신규 파일 `rerun-button.tsx`:** `useEffect` 없음을 직접 확인. 파일 내 유일한 "useEffect" 언급은 주석 5번 라인 ("LESSON-004: useEffect 사용 금지")으로, import/호출 없음.

**기존 파일 `backtest-detail-view.tsx`:** W5 커밋 diff에서 `useEffect` 관련 변경줄 없음:

```
git diff HEAD~1 HEAD -- backtest-detail-view.tsx | grep "useEffect"  → (출력 없음)
```

즉 기존 `useEffect` 블록(`backtest-detail-view.tsx:47-52`)은 이번 커밋 이전(`aad44e2 fix(dogfood): FE detail refetch on terminal`)에 이미 존재했던 코드이며, W5는 이를 추가하지 않았다.

**codex-self.md 보고:**

```
git diff stage/x1-x3-indicator-ui...HEAD | grep -c "useEffect"  => 0
```

이는 W5 커밋 범위에 useEffect 추가 없음을 의미한다.

**`router.push` 호출 위치:** `rerun-button.tsx:27` — `onSuccess` 콜백 안에서 호출. `useEffect` 미사용. LESSON-004 완전 준수.

**판정: LESSON-004 PASS. W5 변경 내 useEffect 신규 추가 없음.**

---

## Q7. 최종 평결

**GO_WITH_FIX (8.5/10)**

GO 판정을 내리기 전에 아래 minor fix 1건을 권고한다.

### 발견 사항

**[FIX-1] initial_capital 타입 불일치 — 테스트 fixture vs 실 스키마**

`BacktestDetail.initial_capital`은 Zod `decimalString`으로 정의되어 있다 (`schemas.ts:133`). `decimalString`은 `z.string().transform(...)` 이므로, 파싱 후 TypeScript 타입은 `number`이다. 그런데 계획서 §4 T1의 초기 test fixture (`plan.md:168`)에서는 `initial_capital: "10000"` (string)으로 작성되어 있었다.

실제 배포된 테스트(`rerun-button.test.tsx:58`)와 integration test(`integration.test.tsx:69`)에서는 `initial_capital: 10000` (number, `as unknown as BacktestDetail`)으로 수정되었다. 이는 올바른 방향이다.

그러나 `as unknown as BacktestDetail` 캐스팅은 타입 안전성을 우회한다. 실제 BE 응답은 Zod parse를 통해 `number`로 변환되므로 런타임에서는 문제없다. 단, fixture의 `as unknown as` 패턴은 미래 스키마 변경 시 타입 에러를 숨길 위험이 있다.

**권고:** `BacktestDetail` fixture 생성을 `BacktestDetailSchema.parse({...})` 방식으로 전환하면 `as unknown as` 없이도 정확한 타입이 보장된다. 현재는 허용 가능한 수준이나, 팀 규칙에 `as unknown as` 사용을 문서화하거나 `zod.parse` 방식으로 마이그레이션 권고.

**[INFO] TDD FAIL-first git evidence 없음** — Q3 참조. 프로세스 위반일 수 있으나, 14건 테스트 품질이 높으므로 현재 버전에서는 블로커로 분류하지 않음.

**[INFO] `timeframe as never` 캐스팅** (`rerun-button.tsx:48`) — BE→FE enum 보장을 가정한 타입 우회. 스키마가 enum을 엄격히 검증한다면 안전하나, 향후 timeframe 확장 시 컴파일 에러 대신 런타임 오류가 될 수 있다. `satisfies` 또는 enum exhaustiveness check 고려 권고 (non-blocking).

---

## Q8. 구현 속도 + 테스트 커버리지 (Sonnet 추가 질문)

### 14건 테스트 충분성 평가

6 unit + 8 integration = 14건. 기능 복잡도 대비 적절한 커버리지다. 특히:

- unit 6건이 `invalid_capital`, `isPending`, `error path`를 독립적으로 커버
- integration 8건이 `effectiveStatus` 우선순위(conflict case 2건 포함)를 직접 검증

### (a) 큰 initial_capital string "99999999.99999999" → Number precision 손실

**검증 여부: 미검증.**

`rerun-button.tsx:40`의 `Number(backtest.initial_capital)`은 `decimalString` transform을 통과한 `number` 값에 한 번 더 `Number()`를 적용한다. `BacktestDetail.initial_capital`은 이미 Zod parse 시 `Number.parseFloat("99999999.99999999")` 변환을 거쳐 JavaScript `number`로 저장된다.

`Number.parseFloat("99999999.99999999")` = `99999999.99999999` (IEEE 754 double, 17자리는 정확히 표현 가능한 범위에 있음). 그러나 소수점 이하 8자리 수량은 `Number`로 완전 표현이 불가능하다. 예: `99999999.99999999` → JS에서 `100000000` (반올림)으로 변환될 수 있다.

테스트에서 이 케이스를 커버하지 않는다. 단, **production 결함 가능성은 낮다**: 백테스트 `initial_capital`은 사용자가 입력 폼(`CreateBacktestRequest.initial_capital: z.number().positive()`)을 통해 이미 JS number로 제출하므로, BE 응답의 `initial_capital`은 원래 number의 직렬화 결과다. 8자리 소수점 이하 자본을 입력하는 유스케이스는 현실적으로 발생하지 않는다 (암호화폐 거래에서 최소 단위 = USDT 0.01 수준).

**결론:** 이론적 precision 손실은 존재하나 현실적 production 결함 가능성은 낮음. 테스트 추가는 선택사항.

### (b) 더블클릭 race condition

**검증 여부: 미검증. Production 결함 가능성 더 높음.**

`rerun-button.tsx`에는 debounce나 double-click 방지 로직이 없다. 클릭 핸들러(`handleClick`)는 동기 함수이고, `isPending` 체크가 있다:

```tsx
const isDisabled = !isEnabled || isPending;
```

그러나 이 비활성화는 **React 렌더링 사이클 이후에 반영**된다. 빠른 더블클릭 시나리오:

1. 1번 클릭 → `handleClick` 실행 → `mutate()` 호출 → mutation 시작 → React가 re-render로 `isPending=true` 세팅
2. React re-render 전에 2번 클릭 → `isPending`이 아직 `false`이므로 `isDisabled=false` → `mutate()` 재호출

결과: 동일 파라미터의 백테스트가 2번 생성될 수 있다.

**대응책 2가지:**

| 방법                         | 구현                                                                                     | 트레이드오프                                      |
| ---------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `useRef` guard (즉시 효과)   | `const pendingRef = useRef(false); handleClick에서 pendingRef.current 체크 후 true 세팅` | LESSON-004 위반 없음 (ref는 useEffect 아님), 간단 |
| `useMutation isPending` 신뢰 | React 18 concurrent 모드에서 동기 클릭은 보통 한 프레임 내 처리                          | 환경에 따라 불충분                                |

**권고:** 현재 코드는 `disabled={isDisabled}` HTML 속성에 의존하나, React re-render 지연으로 더블클릭이 통과할 수 있다. `useRef` 기반 즉시 가드 추가를 권고. 단, 이는 minor fix (backtest 중복 생성은 서버에서 허용하며 별도 사이드이펙트가 크지 않음).

### 어느 것이 production 결함 가능성이 높은가?

**(b) 더블클릭 race가 더 높다.**

- (a) precision 손실: 현실적 유스케이스(소수점 8자리 초기 자본)가 거의 없음. dogfood 환경에서 재현 불가.
- (b) 더블클릭: 일반 사용자가 버튼이 반응하지 않는다고 느껴 빠르게 2번 누르는 행동은 흔함. 특히 네트워크 느린 환경에서 mutation 시작이 늦을 때 더 빈번. 중복 백테스트 2개 생성 → 혼란 + Celery 워커 리소스 낭비.

---

## 종합 요약

| 항목              | 결과                                          |
| ----------------- | --------------------------------------------- |
| AC 달성           | 10/10 PASS                                    |
| Mock 엄밀성       | ADEQUATE                                      |
| TDD FAIL-first    | git evidence 없음 (process gap, non-blocking) |
| 회귀 위험         | 없음                                          |
| Edge case 7개     | 전부 커버                                     |
| LESSON-004        | PASS (W5 내 useEffect 신규 추가 0건)          |
| Double-click race | 미커버 (minor, production 결함 가능성 있음)   |
| Precision loss    | 미커버 (낮은 현실적 리스크)                   |

**최종 판정: GO_WITH_FIX (8.5/10)**  
Fix: 더블클릭 race 방지 `useRef` guard (optional) + `as unknown as` fixture 개선 (optional).  
코드 품질, LESSON-004 준수, effectiveStatus 우선순위 통합 커버리지 모두 양호. 머지 가능하나 더블클릭 guard는 후속 PR에서 처리 권고.
