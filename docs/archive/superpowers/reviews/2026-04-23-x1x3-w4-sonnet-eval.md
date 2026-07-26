# W4 Sonnet Independent Evaluation — Sprint X1+X3

**Date:** 2026-04-23
**Reviewer:** claude-sonnet-4-6 (independent, no prior context)
**Worker:** 4 / 5 (Trade Analysis 방향별 breakdown)
**Branch:** `w4/trade-analysis-breakdown`
**Diff:** `/tmp/w4-diff.txt` (530 lines, 6 files)

---

## Executive Summary

| Question               | Verdict                                                                          |
| ---------------------- | -------------------------------------------------------------------------------- |
| Q1: AC 달성?           | **YES** (7+4 tests, tsc/lint clean)                                              |
| Q2: Spurious PASS?     | **CLEAN** — pnl 는 Zod transform 후 number, `Number(t.pnl)` 중복 변환이지만 무해 |
| Q3: TDD?               | **PARTIAL** — FAIL→PASS 전환 evidence 없음 (log 부재)                            |
| Q4: 회귀/충돌?         | **SAFE** — 1-line 변경, W5 header 영역 충돌 없음                                 |
| Q5: Edge 6개 커버?     | **YES** — 6/6 확인                                                               |
| Q6: Disclosure 정확성? | **ACCURATE** — condition 정확, 문구 사실만 표기                                  |
| Q7: Verdict            | **GO_WITH_FIX** (confidence 8/10) — Q8 경계값 미검증 1건                         |
| Q8: 경계값 커버리지    | **GAP 발견** — `trades.length === num_trades` 케이스 미검증                      |

**최종 판정: GO_WITH_FIX (8/10)**

---

## Q1: AC 정량 달성?

**YES.**

Codex self-review (`2026-04-23-x1x3-w4-codex-self.md:84-95`) 보고:

| 항목                    | 목표  | 실제                 |
| ----------------------- | ----- | -------------------- |
| util 단위 테스트        | ≥ 5건 | **7건**              |
| component 테스트        | ≥ 2건 | **4건**              |
| `pnpm test` 전체        | clean | 25 files / 148 tests |
| `pnpm tsc --noEmit`     | clean | 0 errors             |
| `pnpm lint`             | clean | 0 warnings           |
| 기존 TradeAnalysis 회귀 | 0     | 0                    |

diff를 통해 직접 확인된 파일:

- `frontend/src/features/backtest/__tests__/direction-breakdown.test.ts` (신규, 111 lines, 7 test cases) — diff:342
- `frontend/src/app/(dashboard)/backtests/_components/__tests__/trade-analysis.test.tsx` (신규, 83 lines, 4 test cases) — diff:106
- `frontend/src/features/backtest/utils.ts` — `computeDirectionBreakdown` 추가 — diff:458
- `frontend/src/app/(dashboard)/backtests/_components/trade-analysis.tsx` — breakdown section 추가 — diff:208
- `frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx` — 1줄 수정 — diff:195

---

## Q2: Spurious PASS — Number(trade.pnl) Decimal-as-string 처리?

**CLEAN — 그러나 주석 vs 실제 동작에 불일치 있음.**

### 실제 타입 흐름

`TradeItemSchema` (`frontend/src/features/backtest/schemas.ts:151`):

```ts
pnl: decimalString,
```

`decimalString` (`schemas.ts:10-19`)은 `z.string().transform((s) => Number.parseFloat(s))` 형태의 Zod transformer. **BE가 Decimal을 string으로 직렬화하지만 Zod 파싱 이후 `TradeItem.pnl`은 이미 `number` 타입이다.** `z.infer<typeof TradeItemSchema>`의 `pnl` 필드 타입은 `number`.

### utils.ts의 처리

```ts
// utils.ts:516
const raw = Number(t.pnl);
const pnl = Number.isFinite(raw) ? raw : 0;
```

- `t.pnl`이 이미 `number`인 상태에서 `Number(t.pnl)`을 호출하는 것은 항등 변환 — 무해하고 올바르게 동작.
- plan 문서(`plans/...w4...:31`)의 "trade.pnl 이 string 임을 인지" 주석은 **잘못된 가정**. Zod transform 이후 이미 number. 그러나 guard 자체는 안전하므로 false alarm 수준.
- plan의 `Number(t.pnl) || 0` 패턴 대신 실제 구현은 `Number.isFinite(raw) ? raw : 0`으로 더 엄밀하게 처리됨 — 개선된 버전.
- `NaN` guard 테스트 (`direction-breakdown.test.ts:447`): `pnl: Number.NaN`을 직접 주입해 테스트. `Number.NaN`은 Zod 파싱 이후 값이 아니므로 **이 테스트는 실제 런타임 경로를 검증하는 것이 아니라 방어 코드 자체를 검증**하는 것. 실용적으로는 유효.

**결론:** Spurious PASS 없음. `Number()` 이중 변환은 무해하나, 주석과 plan의 "string 임을 인지" 문구는 오해를 유발할 수 있음.

---

## Q3: TDD 증거?

**PARTIAL.**

- Codex self-review에서 Round 1 NO_GO (9/10) → Round 2 NO_GO (0.88) → Round 3 GO (0.96) 순서로 3 iteration 진행된 것이 확인됨 — disclosure 이슈를 codex가 잡아낸 것은 TDD 원칙 준수를 보여줌.
- 그러나 **"Step 2 — 실패 확인"** (plan:138-144)의 `pnpm test -- --run direction-breakdown`에서 FAIL을 먼저 확인했다는 로그 증거가 self-review에 없음.
- self-review (`codex-self.md:84-95`)는 최종 통과 결과만 기록. 중간 FAIL → PASS 전환의 실증은 부재.

**영향:** 낮음 — 최종 결과가 7/7 + 4/4 테스트 pass이고 plan에 TDD 절차가 명시되어 있어 위험도는 제한적.

---

## Q4: 회귀 및 W5 충돌 안전성?

**SAFE.**

### backtest-detail-view.tsx 1-line 변경

diff:199-204:

```diff
-<TradeAnalysis metrics={bt.metrics} />
+<TradeAnalysis metrics={bt.metrics} trades={trades.data?.items} />
```

- `trades` prop이 optional (`readonly TradeItem[] | undefined`)이므로 타입 안전.
- `trades.data?.items`는 `TradeListResponse.items` (= `TradeItem[]`) — `TradeListResponseSchema`(`schemas.ts:171`) 확인됨.
- `trades` RQ 객체는 line 38 (`backtest-detail-view.tsx`)에 이미 존재하므로 신규 fetch 없음.

### W5 충돌

self-review(`codex-self.md:94-99`): W5는 동일 파일 헤더(상단) 영역 수정. W4 변경은 line 152 단일. 컨텍스트 분리 → git auto-merge 가능성 높음. **squash merge clean할 것으로 판단.**

---

## Q5: Edge 6개 커버?

**YES — 6/6.**

| Edge 케이스            | 계획 명시 | 테스트 파일:라인                                                  | 판정 |
| ---------------------- | --------- | ----------------------------------------------------------------- | ---- |
| 빈 trades (`[]`)       | plan:470  | `direction-breakdown.test.ts:374` + `trade-analysis.test.tsx:166` | PASS |
| 단일 trade             | plan:471  | `direction-breakdown.test.ts:425` + `trade-analysis.test.tsx:187` | PASS |
| pnl=0 (무승부)         | plan:472  | `direction-breakdown.test.ts:434`                                 | PASS |
| NaN/비유한값           | plan:473  | `direction-breakdown.test.ts:447`                                 | PASS |
| trades prop undefined  | plan:474  | `trade-analysis.test.tsx:158` (no trades prop)                    | PASS |
| LESSON-004 useMemo dep | plan:475  | `trade-analysis.tsx:247-252` (diff:247) + self-review:77-82       | PASS |

---

## Q6: Disclosure 정확성 (페이지네이션)?

**ACCURATE — Round 2 수정 후 사실만 표기.**

### 조건식 검증

diff:280-286 (trade-analysis.tsx 신규 코드):

```tsx
{
  trades && num_trades > 0 && trades.length < num_trades ? (
    <p className="mt-2 text-xs text-[color:var(--text-muted)]">
      * 표시된 거래 {trades.length}건 기준 (전체 {num_trades}건 중).
    </p>
  ) : null;
}
```

- `num_trades`: `BacktestMetricsOut.num_trades` (`schemas.ts:114`) — BE가 전체 거래 수를 integer로 반환.
- `trades.length`: 현재 200건 cap `TRADE_QUERY = { limit: 200, offset: 0 }` (`backtest-detail-view.tsx:29`).
- `trades.length < num_trades` → 201건 이상일 때만 disclosure 표시. **조건 정확**.
- Round 1 문구의 "거래 목록 탭을 참고하세요" → Round 2에서 "거래 목록 탭도 동일한 200건 cap" 발견 → 사실만 표기로 축소. **올바른 수정**.

### 한계 (수용 가능)

disclosure가 표시될 때 breakdown은 200건 기준 집계임을 사용자에게 알리지만, "더 정확한 데이터를 보는 방법"은 현재 제품에 없음. export 기능이 없으므로 현 상황에서 최선의 처리.

---

## Q7: Verdict

**GO_WITH_FIX (8/10)**

### GO 근거

- 7 util + 4 component tests — AC 초과 달성
- LESSON-004 완벽 준수 (useMemo dep=[trades], useEffect 미사용)
- Decimal string 처리 — Zod transform 이해는 부정확하나 실제 동작은 정확
- disclosure Round 2 수정으로 오해 유발 문구 제거
- backtest-detail-view.tsx 1-line 변경 타입 안전, 회귀 0

### FIX 필요 (Q8에서 상세)

- `trades.length === num_trades` 경계값 케이스 미테스트 (disclosure 미표시 검증 부재)

---

## Q8 (Sonnet 추가 질문): 테스트 커버리지 충분성

### (a) trades가 200개 정확히일 때 disclosure가 안 뜨는가?

**GAP — 미검증.**

disclosure 조건은 `trades.length < num_trades` (strict less-than). `trades.length === num_trades` (예: 200건이 전체 거래)일 때 disclosure는 미표시 — 이는 올바른 동작이다. 그러나 **이 경계값 케이스는 어떤 테스트에서도 검증되지 않음**.

구체적으로:

- 컴포넌트 테스트 `trade-analysis.test.tsx`의 4개 케이스는 모두 trades 배열 길이가 `METRICS.num_trades(=3)`보다 작거나 비어있는 경우만 다룸.
- `trades.length === num_trades` (예: trades 3건, num_trades 3) → disclosure 미표시 경로는 happy path이지만 **명시적 assertion이 없음**.
- 반면 `trades.length < num_trades` → disclosure 표시 경로도 컴포넌트 테스트에서 미검증 (direction-breakdown 유틸 테스트에는 없고 컴포넌트 테스트도 num_trades=3이고 trades 1-3건이므로 disclosure 표시 케이스를 설정하려면 num_trades를 더 크게 설정해야 함).

**실제로 `trade-analysis.test.tsx`의 "renders direction breakdown when trades provided" (`trade-analysis.test.tsx:172`)**: `METRICS.num_trades = 3`, trades 3건 제공 — `3 < 3`이 false → disclosure 미표시. 하지만 이 케이스에서 disclosure가 없다는 assertion이 없음. disclosure가 표시되는 버그가 생겨도 이 테스트는 통과함.

### (b) trades > num_trades인 황당 케이스

**defensive 처리 부재. 그러나 실제 발생 불가.**

BE 구현상 paging API가 전체보다 더 많은 trades를 반환할 수 없음 (`total` 필드 기반 consistent). 발생 시 `trades.length < num_trades`가 false → disclosure 미표시 → 사용자는 "전체 데이터"로 오인. 코드 수준 방어 없음.

### 둘 중 production 결함 가능성 더 높은 것

**(a)가 더 높다.**

이유:

1. `trades.length === num_trades`는 **정상 케이스** (200건 미만 백테스트)에서 항상 발생하는 경로. disclosure 미표시가 올바른 동작이지만, 향후 조건식을 실수로 `<=`로 바꾸거나 반전시키면 정상 케이스에서 항상 disclosure가 표시되는 UX 버그가 발생할 수 있고 현재 어떤 테스트도 이를 잡지 못함.
2. (b)는 BE 버그 없이는 발생 불가하므로 실질적 위험도는 낮음.

### 권장 Fix (GO_WITH_FIX 사유)

```tsx
// trade-analysis.test.tsx 추가 케이스

it("does NOT show disclosure when trades.length equals num_trades", () => {
  const trades: TradeItem[] = [
    mkTrade({ direction: "long", pnl: 10 }),
    mkTrade({ direction: "long", pnl: -5 }),
    mkTrade({ direction: "short", pnl: 20 }),
  ]; // 3건 == METRICS.num_trades(3)
  render(<TradeAnalysis metrics={METRICS} trades={trades} />);
  expect(screen.queryByText(/표시된 거래/)).not.toBeInTheDocument();
});

it("shows disclosure when trades.length is less than num_trades", () => {
  const metricsMore = { ...METRICS, num_trades: 10 }; // 전체 10건
  const trades = [mkTrade({ direction: "long", pnl: 10 })]; // 1건만 제공
  render(<TradeAnalysis metrics={metricsMore} trades={trades} />);
  expect(screen.getByText(/표시된 거래 1건 기준/)).toBeInTheDocument();
  expect(screen.getByText(/전체 10건 중/)).toBeInTheDocument();
});
```

이 2건 추가 시 disclosure 로직의 boundary condition이 완전히 커버됨.

---

## 종합 판단

**GO_WITH_FIX (confidence 8/10)**

- 핵심 기능(방향별 승률/avgPnl 계산), LESSON-004 준수, 타입 안전성, 회귀 방지 모두 양호.
- Q8(a) disclosure boundary test 2건 추가 후 ship 권장.
- 추가 없이 ship할 경우에도 현재 disclosure 버그는 없으며, 향후 수정 시 회귀 위험만 존재 — risk level: low.

| 항목              | 평가                                                 |
| ----------------- | ---------------------------------------------------- |
| LESSON-004        | PASS                                                 |
| Decimal precision | PASS (Zod transform 이해 오류 있으나 동작은 correct) |
| Edge 6개          | PASS                                                 |
| Disclosure        | PASS                                                 |
| Boundary test     | GAP (disclosure `=` vs `<` 미검증)                   |
| W5 충돌 위험      | 없음                                                 |
| TDD 엄밀도        | PARTIAL (최종 green 확인, 중간 FAIL log 부재)        |
