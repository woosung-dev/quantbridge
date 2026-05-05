# dogfood Day 6.5 — Sprint 34 mid-dogfood (BL-175 머지 직후 numeric)

**날짜:** 2026-05-05 (Sprint 34, PR #150 BL-175 머지 직후 mid-check)
**환경:** isolated docker (5433/6380) + uvicorn host port 8100 + frontend 3100
**판정:** **PASS** (Surface Trust 차단 작동 + R-2 silent BUG 차단 + P1-3 fail-closed 정책 정상 작동)
**Day 추적:** Day 3=4 → Day 4=5 → Day 5=6~7 borderline → Day 6=5 (regression) → **Day 6.5 PASS** (mid-check, Sprint 33 lesson #1 본 sprint 직접 적용 검증)

---

## 1. mid-dogfood 패턴 — Sprint 33 lesson #1 직접 검증

Sprint 33 dogfood Day 6 = sprint 종료 직후 진행 → BUG 3건 발견 → hotfix 추가 PR 시퀀스 = 후속 sprint scope 침범 risk. **Sprint 34 lesson #1 직접 적용** = sprint 안 mid-check 가 BUG 발견 + 즉시 fix cycle 가능.

본 mid-check = PR #150 (BL-175 본격 fix) 머지 직후. 회귀 0건 + 신규 발견 BL 1건 (BL-178 신규 등록 — OHLCV invalid close root cause, Sprint 35+ 분리).

---

## 2. fixture + 검증 절차 (codex P1-6 numeric 적용)

### 2.1 fixture (Playwright MCP 자동화)

3건 신규 backtest 실행 — strategy 2건 (s1_pbr / s2_utbot, Sprint 33 corpus_v2) + 다양한 timeframe/period:

| backtest_id   | strategy | symbol   | timeframe | period                  | status    | bars | equity_first | equity_last          |
| ------------- | -------- | -------- | --------- | ----------------------- | --------- | ---- | ------------ | -------------------- |
| `ea94e52f...` | s1_pbr   | BTC/USDT | 1h        | 2025-03-01 → 2025-04-01 | completed | 745  | 10000        | -374.85 (자본 초과)  |
| `1c09c372...` | s2_utbot | BTC/USDT | 1h        | 2024-01-01 → 2024-02-01 | completed | 745  | 10000        | -7399.45 (자본 초과) |
| `04559fb1...` | s1_pbr   | BTC/USDT | 4h        | 2024-01-01 → 2024-04-01 | completed | 547  | 10000        | 814.12 (정상)        |

### 2.2 검증 #1-7 (codex P1-6 numeric 의무)

| #     | 검증                                                        | 결과        | 비고                                                                                                                           |
| ----- | ----------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1     | API raw payload `value[0]==initialCapital`                  | N/A         | BH null (모든 backtest)                                                                                                        |
| 2     | bar-by-bar `value[i] == initial * close[i] / close[0]`      | N/A         | BH null                                                                                                                        |
| 3     | ChartLegend BH visible + 색 일치                            | N/A         | BH null 시 hidden 정합                                                                                                         |
| 4     | 차트 BH line 정확 렌더 (strategy line 과 다른 곡선)         | N/A         | BH null 시 미렌더 정합                                                                                                         |
| 5     | 자본 초과 손실 시나리오 (mdd_exceeds_capital=true)          | ✅          | -103.75% / -112.08% / "leverage 1x · 현물 · 자본 초과 손실" inline 표시                                                        |
| **6** | **legacy backward-compat (BH null → 미렌더 + Legend hide)** | ✅ **PASS** | Playwright snapshot 시각 검증 — Legend 안 "Equity (자본 곡선)" + "Drawdown (손실 폭)" 만 표시. **"Buy & Hold" 항목 미표시**    |
| **7** | **P1-3 fail-closed 정책**                                   | ✅ **PASS** | schema `metrics_keys` 안 `buy_and_hold_curve` 추가됨 (R-2 silent BUG 차단) + 값은 null (invalid close 1건 이상 시 fail-closed) |

---

## 3. PR #150 (BL-175) 의 user-facing impact 분석

### 3.1 검증 PASS 항목

- ✅ **R-2 silent BUG 차단** (codex P1-2): API 응답 schema 안 `metrics.buy_and_hold_curve` 필드 추가됨. service.py:551-587 spread 누락 silent BUG 자동 회귀 차단
- ✅ **P1-3 fail-closed 정책**: invalid close 1건이라도 → None 반환 (partial silent line = 거짓 trust 차단)
- ✅ **P1-1 FE wiring**: `equity-chart-v2.tsx` 의 `buyAndHoldCurve` prop + `backtest-detail-view.tsx:160` 호출자 정상 작동
- ✅ **Surface Trust 차단** (Sprint 30 ADR-019): legend 와 chart 데이터 mismatch 영구 차단 — BH null 시 frontend 자동 hide

### 3.2 미검증 항목 (신규 BL 분리)

- ⚠️ **정확한 BH curve 값 표시 = N/A** — production OHLCV 의 fail-closed gate trigger (3개 backtest 모두). 가능성: BTC/USDT TimescaleDB fetch 시 일부 close 가 NaN/<=0 또는 dtype 변환 문제.
- v2_adapter path = production 정합 (vectorbt 제거됨, `run_backtest = run_backtest_v2`). 단 `_v2_buy_and_hold_curve` 가 P1-3 fail-closed 발동.

### 3.3 신규 BL 등록 — BL-178

**BL-178 (P2, Sprint 35+ 분리)** — OHLCV invalid close root cause 분석 + fix.

- 증상: BTC/USDT 1h/4h backtest 3건 모두 `metrics.buy_and_hold_curve = null` (P1-3 fail-closed 발동)
- 의심:
  - timescaledb 안 BTC/USDT bar 일부 누락 → close NaN
  - dtype 변환 시 Decimal(str(NaN)) → NaN 그대로 → fail-closed
  - v2_adapter `_compute_metrics(trades, equity, cfg, ohlcv)` 의 ohlcv 자체가 None 또는 부분 (가능성 낮음 — equity_curve 정상 작동)
- 의무: timescaledb query + ohlcv DataFrame 의 `close.isna().sum()` + `(close <= 0).sum()` 검증
- 추정 시간: M (3-4h)
- 본 sprint 가 아닌 Sprint 35+ 분리 — Surface Trust 차단은 작동 (가짜 data 표시 risk 없음). 정확한 BH 표시는 production-quality 추가 의무

---

## 4. BL-177 marker readability 추가 시각 발견

화면 안 trade marker 가 detail text 풀출력 (예: "L $87,846", "S $87,500" 등 겹쳐 표시) — Sprint 33 dogfood Day 6 발견 BL-177 BUG 재확인. PR #149 (BL-177 dense text shorten) 머지 후 compact mode 적용 시 "L"/"S" 만 표시 + 가독성 개선 expect.

(본 mid-dogfood = PR #150 머지 직후라 PR #149 BL-177 미적용 상태 시각 확인.)

---

## 5. mid-dogfood 패턴 검증 결과 (Sprint 33 lesson #1)

본 mid-dogfood = sprint 안 mid-check 가 BUG 발견 + 즉시 fix cycle 가능 검증:

- **검증 PASS** (Surface Trust 차단 작동, R-2 silent BUG 차단, FE wiring 정상)
- **신규 BL 1건 발견** (BL-178 OHLCV invalid close root cause) — Sprint 35+ 분리 (sprint 안 hotfix 의무 X — 본 sprint 의 Surface Trust 차단 의무는 달성)
- **lesson #1 영구 적용**: sprint 종료 직후 dogfood 시 BUG 발견 hotfix 추가 risk → **mid-sprint dogfood 가 sprint 안에서 fix 또는 BL 분리 결정 가능**. Sprint 34 패턴 검증 PASS

---

## 6. 다음 step

- ✅ **PR #150 (BL-175) 머지 완료** (main @ a796725)
- ✅ **mid-dogfood Day 6.5 PASS**
- ⏳ **PR #149 (BL-177) 머지** — Worker B의 dense text shorten. CI green 확인 후 머지
- ⏳ **PR (retro + AGENTS + BACKLOG)** — Sprint 34 종료 시점

---

## 7. dogfood Day 7 (sprint 끝 종합 self-assess) prereq

mid-dogfood Day 6.5 PASS = sprint 진행 정상. Day 7 = sprint 끝 사용자 종합 점수 (≥7 → Sprint 35 Beta 본격 진입 / <7 → polish iter 3). 본 sprint 의 BL-175 + BL-177 + BL-166 (cancel K-2) + BL-178 신규 등록 효과 종합 평가.

---

## Cross-link

- Plan: `/Users/woosung/.claude/plans/quantbridge-sprint-34-twinkling-quilt.md`
- Sprint 33 dogfood Day 6: `docs/dev-log/2026-05-05-dogfood-day6.md`
- Sprint 33 master retro: `docs/dev-log/2026-05-05-sprint33-master-retrospective.md`
- PR #150 (BL-175): https://github.com/woosung-dev/quantbridge/pull/150
- PR #149 (BL-177): https://github.com/woosung-dev/quantbridge/pull/149
- BL-178 신규 후보: `docs/REFACTORING-BACKLOG.md` (Sprint 34 종료 시 등록)
