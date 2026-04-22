# W4 Codex Self-Review — Sprint X1+X3

**Date:** 2026-04-23
**Worker:** 4 / 5 (Trade Analysis 방향별 breakdown)
**Branch:** `w4/trade-analysis-breakdown`
**Plan:** [`docs/superpowers/plans/2026-04-23-x1x3-w4-trade-analysis-breakdown.md`](../plans/2026-04-23-x1x3-w4-trade-analysis-breakdown.md)
**Reviewer:** codex CLI 0.122.0 (gpt-5)

---

## 결과 요약

| Round | Verdict | Confidence | Action               |
| ----- | ------- | ---------- | -------------------- |
| 1     | NO_GO   | 9/10       | scope-aware fix 적용 |
| 2     | NO_GO   | 0.88       | disclosure 문구 축소 |
| 3     | **GO**  | 0.96       | 통과                 |

**최종 판정: GO (96%)**

---

## Round 1 — NO_GO (9/10)

### Finding (high)

방향별 성과가 전체 거래가 아닌 첫 페이지 200건 (`TRADE_QUERY = { limit: 200, offset: 0 }`) 기준으로만 계산됨. 거래가 201건 이상이면 부분집합 기준으로 왜곡되어 사용자가 잘못된 의사결정을 할 수 있음.

### 통과한 검증 항목

- (1) `computeDirectionBreakdown` 순수성 — 입력 mutate 없음, 외부 상태 접근 없음
- (2) `TradeAnalysis` `trades` optional + 백워드 호환 — `undefined`/빈 배열 시 신규 section 미렌더
- (3) `useMemo` dep `[trades]` only — LESSON-004 준수, RQ result object 직접 사용 안 함
- (4) TS strict / `any` 없음
- (5) Tailwind v4 토큰 패턴이 인접 컴포넌트와 일치
- (6) Edge case (빈/단일/혼합/NaN/zero pnl/undefined) 모두 커버

### Round 1 Fix

- `trade-analysis.tsx` breakdown section 하단에 conditional 안내 추가
- 조건: `trades && num_trades > 0 && trades.length < num_trades`
- 초기 문구: `* 표시된 거래 {trades.length}건 기준 (전체 {num_trades}건 중). 정확한 전체 방향별 성과는 거래 목록 탭을 참고하세요.`

---

## Round 2 — NO_GO (0.88)

### Finding

첫 fix 의 disclosure 가 "거래 목록 탭" 을 안내하지만, **거래 목록 탭도 동일한 200건 cap** (`trade-table.tsx:118` 의 `최대 {TRADE_LIMIT}건만 표시`). 사용자를 여전히 잘못된 위치로 안내함.

### Codex 권장

1. 문구를 사실대로 축소: `* 표시된 거래 N건 기준 (전체 M건 중).` ← 채택
2. 또는 실제 해결 경로 명시 (내보내기 등). ← 미채택 (현 product 에 export 기능 없음)

### Round 2 Fix

- 문구 축소: `* 표시된 거래 {trades.length}건 기준 (전체 {num_trades}건 중).`
- 내부 주석에 "거래 목록 탭도 동일한 200건 cap 을 가지므로 거기로 안내하지 않고 사실만 표기" 명시 (rationale 보존)

---

## Round 3 — GO (0.96)

### 확인된 사실

- 사용자 노출 문구에서 탭 참조 제거 완료
- 조건식 `trades.length < num_trades` 정확 (전체와 일치 시 안내 미표시)
- Round 2 NO_GO 핵심 사유 해소
- 추가 NO_GO 사유 없음

### 잔여 [가정]

- `num_trades` 가 metrics 의 전체 거래 수를 정확히 나타내고, `trades` 가 표시 subset 이라는 현재 계약 유지 — BE schema 확인됨 (true).

---

## LESSON-004 Self-Check

- `TradeAnalysis` 의 `useMemo` dep array: **`[trades]` only** ✅
- `trades` 는 부모 (`backtest-detail-view.tsx`) 에서 `trades.data?.items` 로 추출되어 prop 으로 전달 — React Query result 객체 자체는 컴포넌트 boundary 를 넘지 않음
- React Query 는 동일 cache 의 array 를 같은 reference 로 유지 (refetch 전까지) — useMemo 가 매 render 마다 재실행되지 않음
- `useEffect` 미사용 ✅

---

## AC 정량 달성

| 항목                    | 목표  | 실제                                                         |
| ----------------------- | ----- | ------------------------------------------------------------ |
| util 단위 테스트        | ≥ 5건 | **7건** (기본 5 + zero pnl + NaN guard)                      |
| component 테스트        | ≥ 2건 | **4건** (no-trades / empty-array / mixed / single-direction) |
| `pnpm test` 전체        | clean | 25 files / 148 tests pass                                    |
| `pnpm tsc --noEmit`     | clean | 0 errors                                                     |
| `pnpm lint`             | clean | 0 warnings                                                   |
| 기존 TradeAnalysis 회귀 | 0     | 0 (no-trades regression test 통과)                           |

---

## 충돌 surface (W5 와 공유)

`backtest-detail-view.tsx`: 정확히 1줄 변경 (line 152)

- before: `<TradeAnalysis metrics={bt.metrics} />`
- after: `<TradeAnalysis metrics={bt.metrics} trades={trades.data?.items} />`

W5 는 동일 파일의 헤더(상단) 영역 수정 예정 — 이 변경과 컨텍스트가 분리되어 git auto-merge 가능성 높음. 충돌 발생 시 orchestrator 가 양쪽 변경 모두 보존하는 방향으로 resolve.
