# money-path-finish 운영 계약

> 원장 라벨과 세션 스코프, 그리고 **화면 숫자의 신뢰 등급**이 무엇을 주장하고 무엇을 주장하지 않는지의 SSOT. 숫자가 이상해 보일 때 여기부터 읽는다.

---

## 1. 이 스프린트가 바꾼 것 / 안 바꾼 것

| 대상                                  | 위치                                                      | 이번 변경                                              |
| ------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------ |
| 원장 `ours` 라벨                      | `trading/exit_attribution.py` `classify_exit`             | ✅ 형식 판정 → **계정 스코프 실재 확인** (BL-457)      |
| 원장 `inferred` 귀속                  | `tasks/trading.py` `_order_facts` + `attribute_exit` 호출 | ✅ 심볼 공간 정렬 — **죽어 있던 축을 되살림** (BL-464) |
| 세션 등록 심볼                        | `trading/schemas.py` `RegisterLiveSessionRequest.symbol`  | ✅ `NormalizedSymbol` (BL-454)                         |
| TV 웹훅 심볼                          | `trading/webhook.py` `parse_tv_payload`                   | ✅ 같은 정규화 + 거부 관측 (BL-454)                    |
| Site 1 — Kill Switch 누적             | `trading/kill_switch.py:97`                               | **무변경** (BL-446)                                    |
| Site 2 — Kill Switch 일일             | `trading/kill_switch.py:150`                              | **무변경**                                             |
| Site 3 — loss-limit 알림              | `tasks/alert_rules.py` → `realized_pnl_split_for_session` | ✅ 출처 소계 + 한국어 본문 (BL-458)                    |
| Site 4 — 세션 커브 · 대시보드 §01 KPI | `trading/router.py` `get_live_session_state`              | ✅ 포인트별 출처 + 소계 4필드 (BL-458)                 |
| Site 5 — 일일 dogfood 리포트          | `order_repository.get_daily_summary`                      | **무변경** (BL-450)                                    |

**정직한 한 문장** — 관측 표면(Site 3·4)이 자기 신뢰 등급을 말하게 됐다. **실행 게이트(Site 1·2)는 여전히 추정값과 확정값을 섞어 합산한다.** 그건 의도된 것이다(§4).

---

## 2. `ours` 는 이제 무엇을 뜻하는가

`classify_exit` 분기 순서.

```
1. matched_order_id 있음                         → ours      (거래소 주문 id 실측 매칭)
2. meta 없음                                     → unknown
3. orderLinkId 가 UUID + 그 Order 가 계정에 실재  → ours      ★변경점
4-7. createType / stopOrderType 진술              → bracket_tp | bracket_sl | trailing | liquidation
8. orderLinkId 가 UUID 인데 실재 확인 안 됨       → unknown   ★신규
9. createType == createByUser                    → external_manual
10. 그 외                                        → unknown
```

**분기 4-7 이 8 앞에 있는 이유** — 거래소가 진술한 `createType` 은 link-id 형태보다 강한 증거다. 예전 구현은 link-id 분기를 먼저 둬서, UUID 모양 id 를 단 행의 TP/SL/청산 유래를 **버렸다**. 실재 확인을 요구하면서 그 증거가 되살아났다.

**분기 8 이 왜 `external_manual` 이 아닌가** — `external_manual` 은 "사람이 거래소 UI 에서 Close 를 눌렀다" 는 단정이고, **사람은 UUID4 를 타이핑하지 않는다.** 그 문자열은 운영자가 알림 본문에서 읽는 값이라 유령 수동거래를 찾아 헤매게 만든다. 모른다고 말하는 것이 정직하다.

### 실재 확인 쿼리에 `state` 필터가 없는 이유

`OrderRepository.list_existing_ids` 는 술어가 정확히 둘이다 — `exchange_account_id` 와 `id IN (...)`.

`list_by_exchange_order_ids` 가 이미 `state == filled` 로 매칭을 시도하므로, 분기 3 에 도달하는 행은 **정의상 그 매칭에 실패한 주문**이다(`submitted` · 부분체결 후 `cancelled` · `pending` 중 프로세스 사망). `state` 필터를 넣으면 이 확인이 존재하는 이유인 모집단을 정확히 배제해 **진짜 우리 청산을 외부 청산으로 뒤집고 운영자를 호출한다.**

같은 이유로 `list_filled_for_attribution`(= `filled` + `limit=500`)의 결과를 재사용하는 것도 틀린 해법이다. **백로그 BL-457 의 원래 "권장 접근" 이 그걸 권했고, 그 조언은 정정했다.**

고정 위치 — `tests/trading/test_repository_orders.py::test_list_existing_ids_is_state_agnostic_and_account_scoped` · `tests/tasks/test_closed_pnl_sweep.py::test_sweep_claims_an_unmatched_row_as_ours_when_the_order_row_exists`.

### 감수한 것 — 혼재 vintage 컬럼

사용자 결정에 따라 **기존 원장 4행은 재분류하지 않았다.** 즉 `trading.exchange_exits.classification` 에는 컷오버 전 `ours` 3행이 남아 있고, 컷오버 후 코드라면 그 3행은 `unknown` 이다.

이유 — 그 3행의 `order_link_id` UUID 는 계정 재등록 전 우리 주문이었을 개연성이 높은데 Order 이력이 사라져 증명할 수 없다. 재분류는 원장에 **새 거짓을 쓰는 셈**이다. 운영자 알림은 신규 행에만 발화하므로 실질 영향은 0 이다.

**컷오버 = PR #481 머지 시점.** 그 이전 `created_at` 행의 라벨은 형식 판정 산물로 읽어야 한다.

---

## 3. 심볼 canonical

**canonical = `BTC/USDT`(CCXT unified spot).** 선택이 아니라 강제다 — `providers._to_bybit_linear_symbol` 이 `:USDT` 를 합성하는데 그 함수가 `"/" not in symbol` 이면 원문을 그대로 통과시킨다. 즉 원문 `BTCUSDT` 는 **linear 어댑터를 우회**해 조용히 잘못된 market 으로 라우팅된다.

| 공간        | 표기            | 쓰는 곳                                     |
| ----------- | --------------- | ------------------------------------------- |
| 우리 테이블 | `BTC/USDT`      | `Order.symbol` · `LiveSignalSession.symbol` |
| 거래소 원장 | `BTCUSDT`       | `ExchangeExit.symbol` · closed-pnl 스냅샷   |
| ccxt perp   | `BTC/USDT:USDT` | provider 경계에서 합성                      |
| WS 토픽     | `BTCUSDT`       | `to_bybit_raw_symbol`                       |

**규칙 한 문장 — 원장은 거래소 공간, 우리 테이블은 canonical 공간, `_order_facts` 가 유일한 건널목이다.**

`ExchangeExit.symbol` 을 원문으로 남긴 이유 — 거래소 미러다. `row_hash` 가 원문 필드로 계산되고, 모듈이 이미 ccxt 반전을 피하려 `info.side` 를 원문 그대로 저장하며, `aggregate_closed_pnl` 은 `exchange_order_id` 로만 조인해 심볼 조인이 없다.

### 정규화 실패는 거부한다 (fail-closed)

`normalize_symbol_input` 이 거부하는 것 — 문자열 아님 · 공백 · `BASE/QUOTE` 형태 아님 · settle ≠ quote 인 콜론 표기(`BTC/USD:BTC` = coin-margined) · 정규화 후 32자 초과.

**★`.P` / `PERP` / 거래소 접두 같은 장식 제거를 넣지 않았다.** TradingView 가 `{{ticker}}` 로 Bybit 퍼프에서 정확히 무엇을 보내는지(`BTCUSDT` 인지 `BTCUSDT.P` 인지) 1차 출처로 확인하지 못했다. 확인 전에 추측 코드를 넣는 대신 fail-closed 로 두고 **관측**한다.

- API → Pydantic 이 **422**.
- 웹훅 → 기존 `WebhookUnauthorized`(401) 경로 유지 + `qb_webhook_symbol_rejected_total` + `webhook_symbol_normalize_failed` 로그(원문 64자).
- **카운터는 "일어나고 있나" 에만 답한다. TV 가 무슨 포맷을 보내는지는 로그만 답한다.** 첫 실사용 때 그 로그가 진짜 포맷을 알려주면 그때 장식 목록을 넣는다.

지금 fail-closed 가 공짜인 근거 — 착수 시점 `trading.orders` 0행 · `live_signal_sessions` 0행 · 웹훅 경로 실사용 0.

### ★의도된 동작 변경 — 활성 세션 유니크 충돌

`uq_live_sessions_active_unique(user_id, strategy_id, exchange_account_id, symbol) WHERE is_active`.

정규화 전에는 `BTCUSDT` 와 `BTC/USDT` 가 **서로 다른 문자열**이라 같은 시장에 활성 세션 2개가 합법이었고, 대시보드 §01 KPI 가 활성 세션 손익을 단순 합산하므로 **같은 손익을 두 번 더했다**. 정규화가 두 표기를 한 문자열로 붕괴시키므로 이제 충돌한다 — **예전에 201 이던 등록이 `SessionAlreadyActive`(4xx)가 된다.**

결함이 아니라 수정의 요점이다. `live_signal_sessions` 0행이라 배포 시 unique 위반도 백필도 없다. 부수 효과 2건도 개선이다 — WS 토픽이 같은 시장에 1개로 줄고, `provider.fetch_ohlcv(sess.symbol, …)` 가 항상 ccxt-unified 를 받는다.

고정 위치 — `tests/trading/test_session_scope_money_path.py::test_normalized_symbols_collide_on_the_active_unique_index`.

---

## 4. 신뢰 등급 — 화면 숫자가 주장하는 것과 안 하는 것

`Order.realized_pnl_synced_at` 이 출처 마커다. **NULL = pine_v2 추정 · 값 있음 = 거래소 확정 `closedPnl`.**

### 알 수 있는 것

- 한 세션의 실현 손익 중 거래소가 확정한 몫과 아직 추정인 몫 — **금액과 거래 수 모두**. 세션 상세 칩 · 대시보드 §01 KPI foot · loss-limit 알림 본문.
- 단일 세션 커브에서 **어느 구간이 추정인지**(흐린 색).
- loss-limit 알림에서 **손익이 아직 도착하지 않은 체결이 몇 건인지** → 경고된 손실이 과소평가일 수 있다는 사실.

### 알 수 없는 것 (의도된 한계)

- **Kill Switch 게이트는 여전히 추정과 확정을 섞는다.** Site 1·2 는 `realized_pnl` 을 무차별 합산하고 이 PR 이 건드리지 않았다. 화면의 "확정 −5 · 추정 −7" 로 **무엇이 주문을 막았는지 추론할 수 없다.** 의도적이다 — 자본 보호 게이트를 확정값만으로 좁히면 체결부터 스윕 도착까지의 손실이 통째로 사라지는 **fail-open** 이고, 추정 오차(수수료·슬리피지 수준)가 배제 오차(100%)보다 낫다.
- **포트폴리오 곡선의 어느 구간이 추정인지.** `mergeCumulativeCurves` 는 각 세션의 마지막 누적값을 carry-forward 해 더하므로, 한 병합 지점의 값은 대부분 **과거 거래에서 실려온 값의 합**이다. 그걸 "이 시점의 출처" 로 칠하면 적극적으로 틀린다. 그래서 곡선은 집계 수준으로만 고지하고 구간별 표시는 세션 상세에서 한다.
- **확정값이 _옳은지_.** `confirmed` 는 "스윕이 거래소 원장 값을 썼다" 는 뜻이고 "그 값이 정확하다" 는 뜻이 아니다. `closedPnl` 은 **펀딩을 포함하지 않는다**(BL-186).
- 일일 dogfood 리포트(Site 5)도 여전히 혼재이고 전 테넌트 전역이다(BL-450).
- `LiveSignalState.total_realized_pnl`/`equity_curve` 영속 컬럼은 100% pine 시뮬레이션이며 `/state` 가 그 둘을 **버린다** — 계측 대상이 아니다.

### 세 번째 상태 — 손익이 아직 없는 체결

`ClosePositionService` 는 `realized_pnl` 없이 주문을 넣고 스윕이 나중에 채운다. 그 행은 **확정도 추정도 아니다** — 셀 숫자가 없다. 두 값 라벨 체계로 표현할 수 없으므로 **개수로만** 표면화한다.

- **Site 3 알림은 본다** — `unrecorded_count` 를 세고 "실제 손실이 더 클 수 있다" 고 말한다.
- **Site 4 는 보지 않는다** — `list_filled_realized_for_session` 이 `realized_pnl IS NOT NULL` 필터라 오늘도 그 행이 없다(선재·가드레일 고정). 거기서 세려면 `/state` 폴링마다 집계 쿼리가 하나 더 붙는다. **추가 왕복 0 을 택했다.** 패리티가 필요해지면 라우터에서 `realized_pnl_split_for_session(scope)` 를 그 카운트용으로만 호출하는 한 줄 + 5번째 응답 필드가 폴백이다.

### `inferred` 귀속을 되살린 것은 승인이 아니다

`attribute_exit` 은 스스로 "실측 표본 4건에서 4/4 였지만 활성 세션이 사실상 하나였다 — **검정력이 없다**" 고 적고 있다. 이 축이 안전한 이유는 **`attributed_strategy_id` 독자가 레포 전체에 0** 이기 때문뿐이다.

`qb_exchange_exit_attribution_total{confidence}` 는 BL-438 ② 가 이걸 머니-패스 입력으로 승격하기 **전에** 실제 inferred 비율을 재기 위해 존재한다. 그 수치 없이 승격하지 말 것.

---

## 5. 운영 레시피

```sql
-- 원장 라벨 분포 + 실재 확인 실패 흔적
SELECT classification, count(*), count(matched_order_id) AS matched,
       count(order_link_id) AS has_link, count(attributed_strategy_id) AS attributed
FROM trading.exchange_exits GROUP BY classification ORDER BY 2 DESC;

-- 세션 손익 출처 분해 (Site 3·4 와 같은 스코프)
SELECT o.symbol,
       sum(o.realized_pnl) FILTER (WHERE o.realized_pnl_synced_at IS NOT NULL) AS confirmed,
       sum(o.realized_pnl) FILTER (WHERE o.realized_pnl_synced_at IS NULL)     AS estimated,
       count(*) FILTER (WHERE o.realized_pnl IS NULL)                          AS unrecorded
FROM trading.orders o
JOIN trading.live_signal_sessions s
  ON s.strategy_id = o.strategy_id
 AND s.exchange_account_id = o.exchange_account_id
 AND s.symbol = o.symbol
WHERE o.state = 'filled' AND o.filled_at >= s.created_at
  AND (s.deactivated_at IS NULL OR o.filled_at < s.deactivated_at)
  AND s.id = '<session-id>'
GROUP BY o.symbol;

-- 미정규화 심볼이 남아 있는지 (정규화 후에는 0 이어야 한다)
SELECT 'orders' t, count(*) FROM trading.orders WHERE symbol NOT LIKE '%/%'
UNION ALL SELECT 'sessions', count(*) FROM trading.live_signal_sessions WHERE symbol NOT LIKE '%/%';
```

**볼 메트릭** — `qb_exchange_exit_link_unverified_total`(오르면 우리 주문 이력 손실 또는 외부 도구가 UUID client id 사용) · `qb_exchange_exit_attribution_total{confidence}` · `qb_webhook_symbol_rejected_total`(오르면 `webhook_symbol_normalize_failed` 로그에서 TV 실제 포맷 확인).
