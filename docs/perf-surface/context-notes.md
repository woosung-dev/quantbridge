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
- baseline BE = **2533 passed, 46 skipped** (298s) — 문서치 정확 일치. drift 0.

## #4. codex G0 판정 = REVISE — 코드 대조 후 반영 (opspack-ws2 선례: 1건 기각)

read-only codex G0(high effort) 결과. 각 finding 코드 대조(§7.3) 후 판정:

- **[P1 기각] "브랜치가 main 아니라 stage/perf-surface"** — codex 가 실제 상태를 정확히 읽음(W0 docs 커밋 후 실행됨). 프롬프트 "zero diff" 프레이밍이 stale 했을 뿐, W0 docs 커밋은 의도된 것. 플랜 결함 아님.
- **[P1 수용] C3 FE 미러 누락** — `frontend/src/features/strategy/schemas.ts:98` StrategyListItemSchema 는 backtest_count 만 extend. `latest_backtest` zod 추가 필요 → **W3 스코프 명시 추가**.
- **[P1 수용] C5 FE 미러 누락** — `frontend/src/features/optimizer/schemas.ts:333` OptimizationRunResponseSchema 에 5 denormalize 필드 없음(list 는 row-level safeParse 로 이 스키마 사용) → **W3 스코프 명시 추가**.
- **[P1 수용] C5 응답 일관성** — `_to_response`(service.py:333) 는 POST/GET/LIST 공유. list_by_user 만 join 하면 GET/POST 는 5필드 None. **결정: `_to_response(run, backtest=None)` optional 파라미터 + list_by_user·get_by_id 둘 다 LEFT JOIN Backtest + submit 은 이미 fetch 한 backtest 전달 → 3경로 모두 일관 채움**(FK 상 backtest 항상 존재). W1 스코프.
- **[P2 수용] C6 stride 마커 보존** — deriveTradeMarkers 는 entry/exit_time 마커 생성. stride 다운샘플이 그 봉 제거 시 마커 분리 → **C6: first/last + entry/exit 봉 보존 의무**.
- **[P2 수용] latest DISTINCT ON tie-breaker** — completed_at nullable(models.py:111) 동률 비결정 → ORDER BY `strategy_id, completed_at DESC NULLS LAST, created_at DESC, id DESC`.
- **[P2 수용] num_trades sort 키** — types.py: num_trades:int(항상), total_trades:int|None(alias). C4 coalesce 대신 **`metrics['num_trades']` 단독**(항상 존재·authoritative).
- **[확인 CONFIRMED] metrics_summary_from_jsonb**: COMPLETED partial metrics 실재 가능(repository.py:97 임의 dict) → `metrics_from_jsonb`(base-5 필수 인덱싱) 재사용 금지, **per-field `.get()` projection**. pack None 은 metrics NULL/비COMPLETED 만.
- **[확인 CONFIRMED]** astext.cast(Numeric)+NULLS LAST / get_range 양끝 포함 / 단방향 import 순환 없음 / DISTINCT ON 선행 ORDER BY 규칙 / 신규 summary 스키마가 test_metrics_field_parity 안 깸(BacktestMetrics+BacktestMetricsOut 만 비교).
