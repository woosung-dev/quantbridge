# Deepen-modules pilot 2차 — trading (Wave 1/2/3 누적 부채)

> **2026-06-26. 트레일링 live-placement 직전.** CLAUDE.md §7.5 = "신규 대량 신설 직후 + stage→main 직후 = `/deepen-modules`". Wave 1/2/3(라이브 TP/SL)로 trading 도메인 코드 급증(`providers.py` 1000 LOC / `tasks/live_signal.py` 776 LOC / `models.py` 584 LOC). **Iron Law = 1 호출 = trading 1 도메인.** Phase 3 사용자 승인 전 코드수정 0 — BL 등재만. 기존 BL-202(provider registry)/BL-203·204(분할, 해소)/BL-205(OrderStatus triple) 와 무중복.

## 방법

3 병렬 Explore agent(providers exit-param depth / live_signal dispatch locality / models+test coverage) + 오케스트레이터 직접 adversarial 검증. agent 2건 과대평가를 코드 대조로 교정 (아래 §교훈).

## Phase 1 — Module Inventory (trading, 6283 LOC)

| 모듈                                               | LOC       | 분류                                              | 비고                                                                                    |
| -------------------------------------------------- | --------- | ------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `providers.py`                                     | 1000      | Mixed (deep biz logic + 2 shallow-interface 부채) | top co-change(18). live money 0(BybitLive=stub), demo 3                                 |
| `tasks/live_signal.py`                             | 776       | Shallow-by-size                                   | `_async_dispatch_event` 205 LOC, 하드코딩 `BybitFuturesProvider()` :655                 |
| `models.py` / `schemas.py`                         | 584 / 230 | Locality (distributed schema)                     | 8 exit 필드 × 3 boundary type + LiveSignalEvent subset                                  |
| `pine_v2/exit_order_mapping.py` / `exit_orders.py` | 91 / 51   | Dead-code orphan                                  | `fill_type_for` 배선(backtest cost SSOT) / `trigger_direction_for`·`map_exit_kind` DEAD |
| `trading/websocket/bybit_private_stream.py`        | 319       | Deep (supervisor+auth+reconcile)                  | fill-detection 토대 — 트레일링 STEP B 가 소비                                           |

## Phase 2 — Verified 부채 후보 (7건)

| #      | 후보                                                       | 분류                           | Sev | Risk | 근거                                                                                                   |
| ------ | ---------------------------------------------------------- | ------------------------------ | --- | ---- | ------------------------------------------------------------------------------------------------------ |
| BL-365 | `trigger_direction_for`/`map_exit_kind` DEAD + 서버 미배선 | dead-code + latent correctness | 7   | 🟢   | `exit_order_mapping.py:48/76` 0 caller. 자율 exit=entry-attached bracket→영향X. manual API=client 공급 |
| BL-366 | live-signal DI 인라인 조립 중복                            | locality + DI-dup              | 6   | 🟡   | `live_signal.py:650-682` vs `dependencies.py get_order_service` — config drift                         |
| BL-367 | `_async_dispatch_event` shallow-by-size                    | shallow-by-size                | 4   | 🟢   | 205 LOC + 8× `mark_failed+commit+metric` 반복                                                          |
| BL-368 | `_merge_exit_params` ccxt-key 누설                         | shallow interface              | 6   | 🟡   | `:135-207` + 3 call site 가 ccxt 키명 문자열 전달                                                      |
| BL-369 | create_order try/except/finally ×3 복붙                    | DRY/locality                   | 5   | 🟡   | `:279-349/431-529/728-795` ~40 LOC 동일                                                                |
| BL-370 | exit-field multi-SSOT                                      | locality                       | 5   | 🟡   | 8 필드 × OrderSubmit/Order/OrderRequest (mixin awkward 주의)                                           |
| BL-371 | ws-stream 고빈도 fill 스트레스                             | hardening                      | 5   | 🟢   | orphan buffer cap 1000 + concurrent 순서 미검증                                                        |

### STOP 조건 재측정 = 해당 없음

deepen skill §3.4 STOP(test coverage <70% → test 우선)을 재측정. Agent 3 의 "order_service risk-sizing <15%" 는 **오판** — `tests/trading/test_risk_sizing.py` 7 test(`_validate_position_size` 핵심 분기 커버)를 누락 카운트. 실측: providers 40-60% / ws-stream 40-50% / live_signal 50-60% / risk-sizing 7 test / exit_order 60-70% — **전부 refactor-safe**. 단 money-path(트레일링) 직전이라 §3.4 의 "risk 회피, BL 등재만 + 리팩터 보류"는 채택.

## Phase 3 — Grilling 결정 로그

- 사용자 결정 = **전부 등재 + 리팩터 트레일링 이후 보류** (옵션 A).
- C1(BL-365 trigger_direction) → 트레일링 STEP B 가 첫 server-side 소비자로 흡수 검토. **단 후속 ccxt 검증 결과 = 트레일링은 trading-stop 엔드포인트(position-inferred)라 triggerDirection 미소비 → BL-365 deferred 확정**(STEP B 미흡수).
- C2~C7 → BL 등재만, money-path churn 직전 회피.

## Phase 4 — 등재

- `backlog.md` P2 = BL-365/366/368/369, P3 = BL-367/370/371.
- Sprint 권고: 트레일링 live-placement 안정화 + stage→main 후, trading deepening sprint 로 BL-366/368/369 묶음(architectural) + BL-367(clean win). BL-365 는 서버 standalone-trigger 발주 시점까지 보류. BL-370 은 over-abstraction 위험 재평가 후. BL-371 은 post-Beta monitor.

## 교훈 (LESSON 후보)

- **AI 누적 money-path 코드 3-콤보 패턴:** "param 배선 완성 + placement 미완 + SSOT helper(`trigger_direction_for`) dead". Wave 1/2/3 가 정확히 이 형태 — 배선은 됐으나 placement/소비가 미완이라 dead helper + latent gap 누적. 신규 도메인 incremental 빌드 시 사전 차단 의무.
- **adversarial 검증이 agent 과대평가 2건 차단:** (1) "trigger_direction 미배선 = 라이브 9/10 correctness bomb" → 자율 경로는 entry-attached bracket 이라 현재 영향 없음(Phase 3 PASS) = latent 로 재분류. (2) "risk-sizing <15% test-first STOP" → `test_risk_sizing.py` 7 test 누락 카운트 = STOP 미발동. **deepen audit 의 agent finding 도 코드 대조 검증 의무**(circular trust 차단, §7.3).

## 다음 audit 권고

`backtest` 또는 `optimizer` 도메인 (Iron Law = 새 session 분리 호출).
