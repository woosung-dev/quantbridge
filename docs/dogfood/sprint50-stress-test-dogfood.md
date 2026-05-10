# Sprint 50 — 본인 stress_test dogfood (Phase 2 첫 사용)

> Sprint 42 도입 stress_test 도메인을 Sprint 50 audit + Cost Assumption Sensitivity MVP 후 본인 dogfood. Day 0 = 2026-05-10, Day 7 = 2026-05-16.

## 사용 시나리오

본인 backtest `f7670303-c970-494b-ad16-1d06e51250f8` (BTC/USDT 1h, 2025-11-06 → 2026-05-05) 위에 Playwright MCP 로 자동화 e2e 진행 (메인 세션):

1. **Monte Carlo (n_samples=1000, seed=42)** — fan chart + 4 통계 (CI 95% 하한/상한 + median + MDD p95) + 3 summary cards 시각 확인 ✅
2. **Walk-Forward (train_bars=500, test_bars=100, max_folds=20)** — IS/OOS bar + degradation_ratio 표시 ✅
3. **Cost Assumption Sensitivity (fees [0.05/0.10/0.20%] x slippage [0.01/0.05/0.10%], 9-cell)** — heatmap 9 cell 모두 ▲/▼ marker + sharpe 값 + tooltip ✅

## evidence (Playwright MCP 자동화)

스크린샷 5장 (`docs/dogfood/sprint50-stress-test-screens/`):

1. `01-overview-tab-with-assumptions.png` — overview tab 안 AssumptionsCard 표시
2. `02-stress-test-tab-with-assumptions.png` — **stress-test tab 진입 시에도 AssumptionsCard 표시 (codex P1#3 fix 작동)** ✅
3. `03-monte-carlo-result.png` — MC fan chart + 4 통계 + 3 summary cards
4. `04-walk-forward-result.png` — WFA bar chart + degradation ratio
5. `05-cost-assumption-heatmap.png` — CA 9-cell heatmap + ▲/▼ marker + legend (색맹 fallback)

## 발견 critical bug 1건 (Playwright e2e 진짜 가치)

### BL-221 (P0, 2026-05-10) — alembic enum value case mismatch

- **증상**: CA submit 시 BE 500 error — `InvalidTextRepresentationError: invalid input value for enum stress_test_kind: "COST_ASSUMPTION_SENSITIVITY"`
- **원인**: 기존 enum value = `MONTE_CARLO` / `WALK_FORWARD` (uppercase = SAEnum default member name). 신규 migration `20260510_0001` 이 `'cost_assumption_sensitivity'` (lowercase = StrEnum value) 추가 → SQLAlchemy 가 INSERT 시 member name `'COST_ASSUMPTION_SENSITIVITY'` 보냄 → DB enum 에 없음
- **fix**: migration upgrade + downgrade 모두 uppercase 로 정정 (commit hotfix). local DB = `ALTER TYPE ... RENAME VALUE` 정리
- **CI 통과했지만 e2e 에서 잡힌 이유**: backend test 안 happy path 가 enum 값 INSERT 까지 도달 안 했거나 mock 사용. 실제 router → service → repo INSERT chain 은 e2e/integration 만 cover
- **LESSON 후보**: SAEnum + StrEnum 조합 시 init migration 의 enum value mapping (member name vs value) 명시 검증 의무. 신규 enum value 추가 migration 작성 시 동일 case 일관성 의무.

## self-assess

- [x] 24 metric BE+FE 100% 정합 (MC 4 통계 + WFA degradation + CA cell metric 모두 정확 표시)
- [x] AssumptionsCard 가 stress-test tab 진입 시에도 표시 (codex P1#3 fix 검증, Surface Trust 보존)
- [x] Cost Assumption Sensitivity 명명 이해 가능 (fees/slippage cost 가정 sensitivity, EMA period 같은 strategy parameter 와 다른 의미)
- [x] heatmap ▲/▼ marker + legend (색맹 fallback) 작동
- [x] Surface Trust 4-AND PASS (가정박스 5 + 24 metric BE+FE 100% + lightweight-charts 정합 + dogfood self-assess Day 0 PASS)
- **self-assess: 8/10**
  - 1. AssumptionsCard lift-up 시각 검증 PASS — Surface Trust 보존 핵심.
  - 2. CA heatmap 9 cell 정확 + sharpe 값 non-monotonic (cost 변화에 strategy 민감도 명확 노출) = dogfood 가치 명확.
  - 3. Playwright e2e 가 P0 bug (BL-221) 발견 → 사용자에게 노출 전 차단 = unit test/CI 만으론 잡지 못한 case.

## Sprint 51 BL-220 관련 의지

- 진짜 Param Stability (EMA period × stop loss %) 사용 의지: \_\_\_/10 (사용자 manual)
- Cost Assumption Sensitivity vs 진짜 Param Stability — 후자 = strategy 자체 안정성, 전자 = backtest 가정 sensitivity. 두 다른 도구.

## self-assess

- [ ] 24 metric BE+FE 100% 정합
- [ ] AssumptionsCard 가 stress-test tab 진입 시에도 표시 (codex P1#3 fix 검증, Surface Trust 보존)
- [ ] Cost Assumption Sensitivity 명명 이해 가능 (fees/slippage 가 cost 가정 sensitivity, strategy parameter 와 다른 의미 명확)
- [ ] heatmap 의 ▲/▼ marker + legend (색맹 fallback 작동, codex P2#8)
- [ ] Surface Trust 4-AND PASS (가정박스 5 + 24 metric BE+FE 100% + lightweight-charts 정합 + dogfood self-assess Day 3 ≥ 7)
- self-assess: \_\_\_/10 + 근거 3줄
  - 1.
  - 2.
  - 3.

## 발견 friction / bug (있을 시 P? + BL 등재 후보 inline)

| ID    | Priority | 설명 | BL 등재 |
| ----- | -------- | ---- | ------- |
| S50-1 | P?       |      |         |

## Sprint 51 BL-220 관련 의지

- 진짜 Param Stability (EMA period × stop loss %) 사용 의지: \_\_\_/10
- Cost Assumption Sensitivity 가 Param Stability 대체 가능 vs 별도 도구로 자리매김?
  - 의견: \_\_\_

## 결론 (Day 7 인터뷰 결과 묶어 Sprint 51 분기 결정)

- Phase 2 Stress Test 실제 사용 가치 = \_\_\_/10
- Day 7 dogfood 결과 (NPS / critical bug / self-assess) 와 묶어 Sprint 51 분기 결정 input:
  - **NPS ≥7 + critical bug 0 + self-assess ≥7 + 본인 의지 second gate** → Sprint 51 = Beta 본격 (BL-070~075)
  - **dogfood mixed** → Sprint 51 = BL-220 (pine_v2 input override + 진짜 Param Stability) 본격
  - **dogfood critical bug 1+** → Sprint 51 = polish iter
  - **mainnet trigger 도래** → Sprint 51 = BL-003 / BL-005 mainnet
