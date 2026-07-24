<!-- perf-surface 스프린트의 의사결정·발견 기록 (append-only 축적) -->

# perf-surface context-notes

> 결정과 그 근거를 세션 진행 중 계속 append. 다음 세션(사람/AI)이 재유도 없이 이어받도록.

## #1. preflight #0 규명 — 총수익률(+) vs 순손익(−) = 버그 아님 (TODO.md [확인 필요] 닫기 근거)

tier-c/opspack-ws2 에서 이월된 "백테스트 리포트 총수익률(+)인데 순손익(−)" 표면 모순은 **버그가 아니라 시맨틱 차이**다. 2026-07-24 플랜 세션 psql 손계산 2건이 소수 10자리까지 코드와 일치.

- `total_return` = (final_equity − init_cash)/init_cash. equity = init_cash + realized_cum + **unrealized(open_pnl)** − funding_cum (`backend/src/backtest/engine/v2_adapter.py:543`, `:656`). 즉 **기말 미청산 평가손익 + 펀딩 반영**.
- `net_profit_abs` = **closed 거래 pnl 합만** (`v2_adapter.py:712`). `open_pnl`·`total_open_trades` 는 별도 필드(`:727-741`).
- 실증 표본 (BTC/USDT 1h, initial 10000):
  - `4a3bb5d3-911a-48e8-92bb-f979a228308d`: (−1168.80675 + 1552.30466)/10000 = **0.03834979092** (펀딩 0)
  - `8f6ba11a-3993-4881-9d07-057abe7b6d09`: 동일 − 펀딩 71.82070/10000 = **0.03116772140**
- → 이 2건은 §6 dogfood 오라클 표본으로 재사용(미청산 부기 표시 실증, total_open_trades=1). 해소책 = 버그 픽스가 아니라 **미청산 포함 부기/각주**(확정 1).

## #2. 계획단계 전제검증(§7.4 prereq spike) — drift 6종

Explore 3기(BE/FE/canon·docs) 병렬로 핸드오프 전제 전수 검증. 구조 premise 전부 CONFIRMED. 확인된 wording/location drift 6종(확정 결정 불변):

1. **메트릭 키 SSOT = 4-site**(핸드오프 "serializers.py 단일 SSOT" 은 부정확). 정본 dataclass = `engine/types.py:170-248`(BacktestMetrics) + serializers + `schemas.BacktestMetricsOut` + `v2_adapter`, `test_metrics_field_parity` tripwire 강제. W1 `metrics_summary_from_jsonb()` 는 JSONB read-projection 이라 5번째 정의 site 아님 — 단 신규 summary 스키마가 parity tripwire 를 trip 하지 않는지 확인(subset projection 이라 안전 예상).
2. **`decimalString` = string→number**(Decimal→string 아님). FE 요약 필드는 parse 후 number. C1 FE 미러는 기존 `schemas.ts:13-23` helper 재사용.
3. **`useOptimizationRuns` 는 `features/optimizer/hooks.ts:52`**(backtest 아님). 둘 다 현재 order_by 미지원 → W3 이 useBacktests 에 추가. 대시보드 §03 병합은 두 feature 훅 조합(순-신규).
4. **dashboard-cockpit 은 현재 useOptimizationRuns 미사용** → §03 최적화 병합 순-신규. lifecycle-chip 회귀 테스트 = `dashboard-cockpit.test.tsx:271-287`(핸드오프 271-275 오차, 유지).
5. **share 페이지에 trade-table 소비자 없음** — TradeDetailTable 소비자는 TradeDetailShell 단일. share 페이지는 자체 Stat 카드+EquitySparkline. W4 backtestId? optional prop 은 미래대비(단일 소비자), 미니차트 share 지원은 후속 BL.
6. **canon 32 = e2e 게이트**(chromium-design-canon 32 런타임), vitest `design-canon-source.test.ts` diffRatchet 은 별개 게이트. DB 포트 = 이 스택 5436(실행 컨테이너 확인; 커밋 default 5433 은 ffwpu 점유로 remap).

## #3. §0 전제 게이트 실측

- main = `b023ce5`(PR #470), 트리 클린, `stage/perf-surface` 신설.
- 컨테이너 Up: quantbridge-db(5436→5432)·redis(6380→6379)·worker·beat·ws-stream·optimizer-heavy.
- baseline: FE **1044 passed(182 파일)** — 문서치 정확 일치. BE 재측정 진행.
- 앱 서버: FE 3100 + BE 8100 러닝(3000=nexus-core).
