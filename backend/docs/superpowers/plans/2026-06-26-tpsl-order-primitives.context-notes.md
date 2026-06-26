# Context Notes — TP/SL Order Primitives (Wave 1)

작업 중 내린 결정과 근거를 계속 append.

## D1 — 프리미티브 = OrderSubmit 필드 + params, 신규 enum 0
`OrderType`(market|limit) 은 건드리지 않는다. 트리거/bracket 주문도 `type=market|limit` + ccxt unified params 로 표현. Order 테이블은 안전한 ADD COLUMN.

## D2 — ccxt 4.5.49 unified param 실측 (추측 금지)
`.venv/.../ccxt/async_support/bybit.py` `create_order_request` (3924~4163), `okx.py` (2970~3160) 소스 직접 grep/read 로 param 계약 확정. 표는 plan 문서 참조. 핵심: `reduceOnly`(bool), `triggerPrice`(scalar), `takeProfit`/`stopLoss`(object `{"triggerPrice":..}`) 는 Bybit·OKX 양쪽 동일 unified shape. `triggerBy` 는 Bybit 전용(extend pass-through), OKX 미주입.

## D3 — Decimal→str 주입
param 값은 `str(Decimal)` 로 주입(float 금지). ccxt `get_price`/`price_to_precision` 가 str 수용. 기존 `_to_exchange_precision` 도 str 제출.

## D4 — byte-identical 회귀 보존
`_merge_exit_params` 는 값이 None/False 면 키 미포함. params 가 비면 create_order 5-arg 호출(기존). client_order_id 만 있으면 `{"orderLinkId"|"clOrdId"}` 만(기존 테스트 그대로 통과).

## D5 — min-notional 배선 위치
order_service 의 기존 notional-MAX 가드(160-215) 직후, 동일 `effective_price`/`notional` 재사용. min cost 는 신규 `ExchangeAccountService.fetch_min_notional`(provider `fetch_min_notional` = load_markets→`limits.cost.min`) 로 조회. None → skip(fail-open, fetch_mark_price 패턴 mirror). leverage 게이트 안이라 futures 경로(money path) 적용.

## D6 — exit_order_mapping 은 순수함수 (Wave 2 배치 분리)
`map_exit_kind` 는 `ExitOrderKind`→`ExitOrderPrimitive` 매핑만. 실제 주문 placement(triggerDirection 결정 포함)는 Wave 2. fill_type 은 `exit_orders.fill_type_for` 와 1:1 assert 로 백테스트↔라이브 정합 고정. `ExitOrderKind` import 재사용(중복 정의 0).

## D7 — 정직 고지 (PR 본문 의무)
standalone linear triggerPrice 는 `triggerDirection` 도 필요(bybit.py:4113) — Wave 2 책임. 프리미티브는 param shape 단위검증까지, 실거래소 round-trip 은 demo 키 필요 → follow-up.

## 최종 상태 (6 commit 완료)
- 4360f3c Task1 fields+migration / 38fd0a5 Task2 provider params / 581ed09 Task3 close reduce-only / 7ac40e3 Task4 min-notional / 6b5d834 Task5 exit mapping / 2e020d3 Task6 idempotency.
- self-verify: ruff check . PASS / mypy src/ 181 files PASS / pytest tests/trading 350 pass / tasks+mapping 22 pass / alembic up→down(0)→up(5) round-trip PASS.
- 실DB = qb-fund-pg(5436) throwaway `qb_w1_test` + redis 6382. roundtrip DB drop 완료.
