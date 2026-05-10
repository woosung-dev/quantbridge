# Sprint 50 — 본인 stress_test dogfood (Phase 2 첫 사용)

> Sprint 42 도입 stress_test 도메인을 Sprint 50 audit + Cost Assumption Sensitivity MVP 후 본인 dogfood. Day 0 = 2026-05-10, Day 7 = 2026-05-16.

## 사용 시나리오 (사용자 manual, 메인 세션 외)

본인 backtest 1개 (Sprint 49 dogfood 본인 backtest 재활용 또는 신규 1개) 위에:

1. **Monte Carlo (n_samples=1000, seed=42)** submit → fan chart + summary table 시각 확인
2. **Walk-Forward (train_bars=200, test_bars=50, max_folds=10)** submit → IS/OOS bar + degradation_ratio 확인
3. **Cost Assumption Sensitivity (fees [0.05/0.10/0.20%] x slippage [0.01/0.05/0.10%], 9-cell)** submit → heatmap 확인 (▲/▼ marker + degenerate cell "—")

## evidence (사용자 manual 첨부)

- 스크린샷 3장 (MC fan + WFA bar + CA heatmap)
- 첨부 위치: `docs/dogfood/sprint50-stress-test-screens/` (사용자 manual)

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
