# TP/SL Wave 2 — W-B Liquidation Price (calc + live endpoint)

날짜 2026-06-26 · 워커 liquidation · base `stage/tpsl-wave2`

## 목표
청산가(liquidation price)를 **on-the-fly 순수 계산**으로 노출. demo-only, 실자금 0, 모델/마이그레이션 0. calc + display 만 (주문 차단 guard 없음 = YAGNI + disjoint 충돌회피).

## disjoint 계약 (충돌 0)
- `schemas.py` / `services/order_service.py` / `models.py` / alembic **미편집**.
- 편집 허용 = 신규 파일 + `router.py`(엔드포인트 추가) + `dependencies.py`(DI) + 신규 test.

## 공식 (Bybit USDT 무기한 linear, isolated, 단일 tier 단순화)
- IMR(initial margin rate) = 1/leverage
- Long(buy)  liq = entry × (1 − IMR + MMR)
- Short(sell) liq = entry × (1 + IMR − MMR)
- MMR 출처 = ccxt market leverage tier `maintenanceMarginRate`(Bybit raw `maintenanceMargin`). 검증: `ccxt 4.5.49 bybit.py:8217`. **fraction 표기 강제**(0.005 = 0.5%). 기본값 = BTCUSDT 최저위험 tier 0.005.
- 단순화 한계(정직 고지): 단일 tier MMR 상수, 펀딩/수수료/파산수수료 제외, mark-가격 근사로 entry 사용. tier 테이블 = follow-up BL.

## Scope (semantic commit 순서)
1. `feat(trading): liquidation price pure calculator (Bybit USDT perp MMR)`
   - NEW `src/trading/liquidation.py` — 순수함수 `calculate_liquidation_price(entry_price, side, leverage, maintenance_margin_rate) -> Decimal` + `liquidation_distance_pct`. Decimal 전구간.
   - 경계: leverage ≤ 0, entry ≤ 0, MMR < 0 → `ValueError`(거래소 거부 의미).
   - test = 손계산 oracle (외부 hand-computed, circular 금지): long/short × leverage 다수.
2. `feat(trading): live liquidation price endpoint + response schema (new file)`
   - NEW `src/trading/liquidation_schemas.py` — `LiquidationPreviewRequest` + `LiquidationInfoResponse`(symbol, entry_price, side, leverage, liquidation_price, maintenance_margin_rate, distance_pct). Pydantic V2.
   - NEW `src/trading/services/liquidation_service.py` — thin, **AsyncSession import 0**(pure calc), repository 0. commit-spy 불필요(순수 read).
   - `router.py` 인증 엔드포인트 `POST /liquidation/preview`(main.py 가 `/api/v1` prefix 추가 → 실제 `/api/v1/liquidation/preview`) ≤10줄 → service 위임. 입력은 명시 파라미터만 → 소유 리소스 fetch 없음 = IDOR 표면 0(get_current_user 인증은 유지).
   - `dependencies.py` `get_liquidation_service`.
3. (stretch, defer 가능) backtest liq sim — capacity 없으면 BL 등재 후 defer. P0 = 1+2.

## 검증
- `uv run ruff check . && uv run mypy src/ && uv run pytest tests/trading -q`
- Evaluator(콜드스타트, code-reviewer) → PASS 시 PR(base `stage/tpsl-wave2`).
