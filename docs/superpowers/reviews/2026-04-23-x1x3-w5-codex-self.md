# W5 Codex Self-Review — RerunButton

> Sprint X1+X3 W5, 2026-04-23 — `feat/x1x3-w5-rerun-button`
> Plan: `docs/superpowers/plans/2026-04-23-x1x3-w5-rerun-button.md`

---

## 최종 평결

**GO (9/10)** — 2회 iteration 후 승격 (GO_WITH_FIX → GO_WITH_FIX → GO)

---

## Iteration 1 — GO_WITH_FIX (8/10)

### 9 checks 결과

| #   | 항목                                                                                               | 결과 |
| --- | -------------------------------------------------------------------------------------------------- | ---- | ---------- | ---- |
| 1   | NO useEffect 추가 (LESSON-004)                                                                     | PASS |
| 2   | router.push 가 click handler / onSuccess 안에서만 호출                                             | PASS |
| 3   | success / error 모두 toast                                                                         | PASS |
| 4   | disabled = `!isEnabled                                                                             |      | isPending` | PASS |
| 5   | initial_capital = `Number()` + `Number.isFinite` + `> 0` 가드                                      | PASS |
| 6   | hooks.ts 변경 없음                                                                                 | PASS |
| 7   | backtest-detail-view.tsx 변경은 헤더 only (Tabs/InProgressCard/ErrorCard/useEffect 블록 unchanged) | PASS |
| 8   | 테스트 mock — mutate args, push args 둘 다 명시 검증                                               | PASS |
| 9   | edge cases — terminal/pending/error/invalid capital                                                | PASS |

### 1차 지적 (minor)

> 부모 통합 커버리지 부족: `RerunButton` 단위 테스트는 `isEnabled=false` prop 만 검증.
> `BacktestDetailView` 가 `effectiveStatus` 를 통해 올바른 `isEnabled` 를 매핑하는지 직접 검증 안 됨.

→ 보완: `backtest-detail-view.rerun-integration.test.tsx` 신규 (terminal 3건 enabled + progress 3건 disabled).

---

## Iteration 2 — GO_WITH_FIX (8/10)

### 2차 지적 (minor)

> integration test 가 `detail.status` 와 `progressStatus` 를 항상 같은 값으로 세팅.
> 부모가 `effectiveStatus = progress.data?.status ?? bt.status` 우선순위를 정확히 쓰는지,
> 아니면 실수로 `bt.status` 만 써도 통과하는 spurious PASS 위험.
>
> 닫으려면 최소 2개 상충 케이스:
>
> - `detail="completed", progress="running"` → disabled
> - `detail="running", progress="completed"` → enabled

→ 보완: 상충 케이스 2건 추가.

---

## Iteration 3 — GO (9/10)

> 추가한 두 상충 케이스로, 이전에 있던 `BacktestDetailView -> RerunButton` 상태 매핑
> 통합 커버리지 갭은 닫혔습니다. `detail.status`와 `progress.status`가 충돌할 때
> 버튼 활성/비활성이 `progress.data?.status ?? bt.status` 우선순위를 따라가는지를
> 직접 증명하므로, 부모가 `bt.status`만 잘못 참조하는 회귀는 이 테스트 세트에서
> 잡힙니다.

**No findings.**

---

## 검증 evidence

```
pnpm test -- --run    => 151/151 PASS (rerun-button 6 + integration 8 포함)
pnpm tsc --noEmit     => 0 errors
pnpm lint             => 0 errors
```

## LESSON-004 evidence

```
git diff stage/x1-x3-indicator-ui...HEAD | grep -c "useEffect"  => 0
```

추가 useEffect 0건. (rerun-button.tsx 코드 주석에 "LESSON-004: useEffect 사용 금지"
문구가 1라인 있을 뿐, 실제 useEffect import / 호출 없음.)

## 변경 파일

- `frontend/src/app/(dashboard)/backtests/_components/rerun-button.tsx` (신규)
- `frontend/src/app/(dashboard)/backtests/_components/__tests__/rerun-button.test.tsx` (신규, 6 tests)
- `frontend/src/app/(dashboard)/backtests/_components/__tests__/backtest-detail-view.rerun-integration.test.tsx` (신규, 8 tests)
- `frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx` (헤더 영역 import + JSX 1블록만)
