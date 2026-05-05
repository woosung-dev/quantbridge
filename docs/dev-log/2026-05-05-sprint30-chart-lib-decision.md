# ADR — Chart Library Decision (Sprint 30-β)

- **Date:** 2026-05-05
- **Status:** Accepted
- **Sprint:** 30-β (Surface Hardening)
- **Cross-link:** PRD §Phase 1 주 4 (lightweight-charts 명시) · plan §4 §2.β · roadmap.md Surface Trust sub-pillar (ADR-019)

---

## Context

PRD `docs/01_requirements/PRD.md` §Phase 1 주 4 spec에서 차트 라이브러리로 **lightweight-charts** (TradingView 오픈소스, ~150KB) 를 명시했다. 그러나 Sprint FE-04 (2026-04-19) 에서 dependency 우선순위에 따라 **recharts ^3.8.1** 을 임시 도입했고, 이후 Sprint 22까지 8개월 동안 spec 격차를 해소하지 못했다.

Sprint 30 Surface Hardening 진입 시점:

- recharts 기반 `equity-chart.tsx` 는 안정적 (Sprint 22 width(-1) warning 회귀 차단 완료)
- 그러나 Surface Trust pillar (백테스트 결과를 자기 자본 의사결정에 쓸 신뢰) 충족에 필요한 **거래 마커 / B&H 비교 line / drawdown area** 인터랙션은 recharts 로는 자체 구현 비용이 lightweight-charts 대비 3배 이상 (canvas 직접 그리기 vs 빌트인 setMarkers / addAreaSeries)
- dogfood Day 2 self-assess **6/10** (H1→H2 게이트 ≥7 미달 1점차) 의 핵심 페인 = 차트 인터랙션 깊이 부족

---

## Options

| Option | 설명 | 별점 | 비고 |
|--------|------|------|------|
| **A. 전체 마이그레이션** | 모든 차트 (equity / monte-carlo / walk-forward) 를 lightweight-charts 로 교체 | ★★ | β scope (5일) 잠식, recharts 안정 영역 회귀 위험. monte-carlo 분포 도식은 recharts 가 더 직관적. ROI 부정적 |
| **B. 점진적 도입** ★ 채택 | 신규 차트 (equity-chart-v2 + Sprint 31+ TradingView candle) 만 lightweight-charts. 기존 recharts 차트 보존 (rollback path) | ★★★★★ | 비용 분산. recharts 안정성 + lightweight-charts 강점 (setMarkers / addAreaSeries / fitContent) 즉시 활용. PRD spec 부분 정합 |
| **C. recharts 유지 + spec 갱신** | PRD spec 을 recharts 로 갱신하는 ADR | ★★★ | 보수적 — spec 을 코드에 맞추는 안티패턴. PRD 가 lightweight-charts 를 선택한 이유 (TradingView 친화 UX) 자체를 무효화 |

---

## Decision

**Option B 채택.** Sprint 30-β 안에서:

1. `lightweight-charts@^4.2.0` 를 `frontend/package.json` dependencies 에 추가 (실제 설치 4.2.3)
2. `frontend/src/components/charts/trading-chart.tsx` — wrapper 단일 컴포넌트 (createChart + ResizeObserver + cleanup + Strict Mode 더블 invoke 방어 + a11y `role="img"` + `aria-label`)
3. `frontend/src/app/(dashboard)/backtests/_components/equity-chart-v2.tsx` — equity + B&H benchmark + drawdown area + 거래 마커 합성
4. `frontend/src/features/backtest/utils.ts::computeBuyAndHold` — equity_curve 기반 P0 추정 (옵션 1, linear interpolation). OHLCV 기반 옵션 2 는 Sprint 31+ deferred
5. 기존 `equity-chart.tsx` (recharts) 는 **보존** — rollback path. mount 교체는 메인 세션이 별도 처리 (Wave 1 squash merge 후)

---

## Trade-offs

### 비용

- **Bundle size:** lightweight-charts 4.2.x ≈ 150KB minified (production.mjs). recharts 와 공존 → 두 라이브러리 동시 의존. 단, lightweight-charts 는 신규 차트에서만 import 되므로 code-split 시 영향 제한.
- **테스트 부담:** jsdom 에 canvas 가 없어 `vi.mock('lightweight-charts')` 패턴 의무. 라이브 검증 (dev 5분 smoke) 는 LESSON-004 PR 규약 그대로 적용.
- **API drift 위험:** lightweight-charts v5 가 release 되면 createChart API 변경 가능. 본 ADR 시점 v4.2.3 pin 으로 mitigation. v5 marshal 은 별도 sprint 진행.

### 이득

- TradingView 친화 UX 즉시 도입 — 사용자가 익숙한 줌/팬/crosshair 자연스럽게 동작
- 거래 마커 (entry ▲ / exit ○) 빌트인 setMarkers — recharts 로는 customDot scatter 합성 필요했던 코드 제거
- B&H benchmark 비교 line / drawdown area 가 두 line/area series 추가 호출만으로 가능
- PRD §Phase 1 주 4 spec 부분 정합 (Surface Trust pillar 측정 기준 #3 충족 단초)

---

## Consequences

### Positive

- Sprint 30-β scope (5일) 안에서 spec 격차 부분 해소
- dogfood Day 3 self-assess 회복 (≥7 목표) 의 차트 인터랙션 페인 직접 해소
- 기존 recharts 차트는 그대로 유지되어 회귀 위험 0

### Negative / Mitigation

- **두 라이브러리 동시 의존 (~150KB bundle 증가)** → 본 sprint 종료 시 bundle size 측정 + 200KB 이내 검증. 초과 시 Sprint 31+ 에서 monte-carlo / walk-forward 차트도 lightweight-charts 마이그레이션 후 recharts 제거 결정
- **Strict Mode 더블 invoke 시 chart 누수 위험** → `useEffect` cleanup 에서 `chart.remove()` + `chartRef.current = null` 강제 + 라이브 5분 smoke 의무 (LESSON-004)

---

## Acceptance criteria

- [x] `lightweight-charts@^4.2.0` 설치 성공
- [x] `trading-chart.tsx` 신규 wrapper + vitest ≥4 PASS
- [x] `equity-chart-v2.tsx` 신규 컴포넌트
- [x] `computeBuyAndHold` utility + vitest ≥3 PASS
- [x] 기존 `equity-chart.tsx` 보존 (회귀 0)
- [x] ADR 1 페이지 (현재 문서)
- [ ] 메인 세션이 `backtest-detail-view.tsx` mount 교체 완료 (Wave 1 squash merge 후)
- [ ] dogfood Day 3 라이브 5분 smoke (LESSON-004 PR 규약)

---

## References

- PRD: `docs/01_requirements/PRD.md` §Phase 1 주 4
- plan: `.claude/plans/quantbridge-vectorized-snowglobe.md` §2.β
- LESSON-004: `.ai/project/lessons.md` (useEffect dep 가이드 + 라이브 smoke 의무)
- lightweight-charts docs: https://tradingview.github.io/lightweight-charts/ (v4.2)
