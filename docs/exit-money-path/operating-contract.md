# exit-money-path 운영 계약

> 세션 스코프 머니-패스가 **무엇을 세고 무엇을 안 세는지**의 SSOT. 숫자가 이상해 보일 때 여기부터 읽는다.

---

## 1. 이 스프린트가 바꾼 것 / 안 바꾼 것

| 소비처                                | 위치                                                                                                              | 스코프                           | 이번 변경                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------ |
| Site 1 — Kill Switch 누적             | `backend/src/trading/kill_switch.py:97` `CumulativeLossEvaluator`                                                 | 전략 · **전 계정** · **전 기간** | **무변경** (BL-446)                  |
| Site 2 — Kill Switch 일일             | `backend/src/trading/kill_switch.py:150` `DailyLossEvaluator`                                                     | 계정 · **전 전략** · UTC 일      | **무변경**                           |
| Site 3 — loss-limit 알림              | `backend/src/tasks/alert_rules.py:60` → `OrderRepository.realized_pnl_split_for_session` (money-path-finish 개명) | **세션 스코프**                  | ✅ event-join → 세션 스코프          |
| Site 4 — 세션 커브 · 대시보드 §01 KPI | `backend/src/trading/router.py:484` → `OrderRepository.list_filled_realized_for_session`                          | **세션 스코프**                  | ✅ (strategy, account) → 세션 스코프 |
| Site 5 — 일일 dogfood 리포트          | `backend/src/trading/repositories/order_repository.py:376` `get_daily_summary`                                    | **전 테넌트 전역** · UTC 일      | **무변경** (BL-450)                  |

**정직한 한 문장** — 세션 스코프 **관측**(Site 3·4)이 정정됐다. 실행 게이트(Site 1·2)는 무변경이며 여전히 전 기간·계정 전역이다. 일일 리포트(Site 5)도 여전히 전 테넌트 전역이다.

---

## 2. 세션 스코프의 정확한 정의

`SessionScope` (`backend/src/trading/repositories/order_repository.py`) — 생성 경로는 `from_live_session()` 하나뿐이다. SQL 번역은 `_session_scope_where()` **한 곳**에서만 일어난다.

```
Order.strategy_id         == session.strategy_id
Order.exchange_account_id == session.exchange_account_id
Order.symbol              == session.symbol          -- 정확 문자열 동등 (ingress 정규화는 BL-454 가 닫음)
Order.state               == filled
Order.filled_at IS NOT NULL
Order.filled_at >= session.created_at                -- 하한 포함
Order.filled_at <  session.deactivated_at            -- 상한 배제 (활성 세션은 미적용)
```

Site 4 만 추가로 `realized_pnl IS NOT NULL` + `ORDER BY filled_at ASC`.

**이벤트(`live_signal_events`)는 더 이상 관여하지 않는다.** 그것이 BL-444 의 결함이었다 — 이벤트는 dispatch 경로에서만 생기므로 수동 청산과 TV 웹훅 손익이 loss-limit 알림에서 구조적으로 빠졌다.

---

## 3. 수용한 트레이드오프 3종 — "버그처럼 보이지만 계약이다"

### 3.1 늦은 체결은 다음 세션으로 간다 (D4)

창을 `filled_at` 에 걸었으므로, 세션 종료 뒤 체결된 주문은 자기를 만든 세션에 안 들어간다.

- 인접 세션이 있으면 → **다음 세션으로 귀속**
- 없으면 → **어느 세션에도 안 잡힘**

`Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**("terminal_at")이라 창의 정밀도는 관측 지연만큼 흐리다.
고정 위치 — `backend/tests/trading/test_session_scope_money_path.py::test_late_fill_lands_in_the_adjacent_session_not_its_own`.

### 3.2 표기가 다른 주문은 스코프에서 빠진다 — **ingress 는 닫혔다** (D5, money-path-finish 에서 해소)

> ★**2026-07-26 갱신.** 이 절이 기록했던 트레이드오프는 [BL-454](../REFACTORING-BACKLOG.md#bl-454) 가 닫았다. 두 ingress 가 `NormalizedSymbol`(`src/common/normalized_symbol.py`) 로 canonical(`BTC/USDT`) 정규화하므로 **표기가 어긋난 주문이 API 로 들어올 경로가 없다.** 술어의 정확 문자열 동등은 유지되고, 그건 이제 결함이 아니라 계약이다. 아래 원래 서술은 이력으로 남긴다.

`symbol` 은 정확 문자열 동등이다. (당시) ingress 정규화가 **어디에도 없었다** — `RegisterLiveSessionRequest.symbol` 은 길이만 보고(`schemas.py:183`), TV 웹훅은 payload 원문을 그대로 싣는다(`webhook.py:89`). `normalize_symbol`(`market_data/constants.py:18`)은 존재하지만 `src/trading/`·`src/tasks/` 에서 호출 0건이다.

| 쓰기 경로                             | `Order.symbol` 출처       | 세션 심볼과 일치  |
| ------------------------------------- | ------------------------- | ----------------- |
| dispatch (`tasks/live_signal.py:926`) | `sess.symbol` 복사        | 구조적으로 항상   |
| 수동 청산 (`close_service.py:81`)     | `session.symbol` 복사     | 구조적으로 항상   |
| TV 웹훅 (`webhook.py:89`)             | payload 원문 → **정규화** | ✅ BL-454 로 보장 |

얻은 것 — 심볼만 다른 활성 세션 2개가 합법(`uq_live_sessions_active_unique` 에 symbol 포함)이므로, 대시보드 §01 KPI 가 같은 손익을 두 번 더하던 문제가 **FE 변경 없이** 닫혔다.
고정 위치 — 술어 = `test_session_scope_excludes_orders_whose_symbol_string_differs`(개명됨) · ingress 보장 = `test_register_request_normalizes_the_symbol_at_the_boundary` + `test_parse_normalizes_the_symbol_to_ccxt_unified`.

### 3.3 세션 경계는 파이썬 쪽에서 한 번 잡힌다 (TOCTOU)

두 소비처 모두 세션 행을 먼저 읽고 **별도 SELECT** 로 주문을 조회한다. 그 사이 `deactivate` 가 커밋되면 스코프는 여전히 무상한이라 **그 한 번의 계산에** 종료 후 체결이 섞인다.

**변경 전보다는 엄격하다** — 예전에는 창이 아예 없어 항상 전 기간을 포함했다. 이 레이스는 새 코드가 한 번의 계산 동안만 옛 동작을 하게 만들고, 다음 평가/요청에서 자가 교정된다. 두 경로 모두 발주를 막지 않는 읽기 전용이다. 근본 수정(세션↔주문 단일 조인)은 [BL-459](../REFACTORING-BACKLOG.md#bl-459).

### 3.4 수동 청산은 체결 직후에도 0 이다

`ClosePositionService` 는 `realized_pnl` 을 안 싣는다(`close_service.py:78` 의 `OrderRequest` 에 필드 자체가 없다). 값은 나중에 `refresh_closed_pnl_task` → `sweep_closed_pnl` 체인이 백필한다.

**즉 BL-444 는 "보이느냐"를 고쳤지 "언제 보이느냐"를 고치지 않았다.** 스윕이 도착하기 전까지 그 청산은 여전히 0 으로 보인다.

---

## 4. 남아 있는 갭 (이번 범위 밖)

- **펀딩이 라이브 손익에 한 푼도 반영되지 않는다.** `trading.funding_rates` 소비자는 백테스트뿐이고 Bybit `closedPnl` 도 펀딩 미포함 — BL-186.
- **추정값과 확정값이 한 합계에 섞인다.** → **부분 해소 (2026-07-26 money-path-finish, [BL-458](../REFACTORING-BACKLOG.md#bl-458)).** Site 3(알림)·Site 4(커브·KPI)는 이제 출처 소계와 포인트별 라벨을 노출한다. **Site 1·2 게이트와 Site 5 는 여전히 혼재**이고 그건 의도다 — 확정값만으로 좁히면 체결~스윕 도착 구간 손실이 사라지는 fail-open 이다. 상세는 `docs/money-path-finish/operating-contract.md` §4.
- **거래소 네이티브 청산(브래킷/트레일링/청산)은 여전히 머니-패스에 없다** — BL-438 ②. 원장(`trading.exchange_exits`)을 읽는 API·FE 코드는 레포 전체에 0건이고, 이번 스프린트도 만들지 않았다. 따라서 **"합성 Order 금지" 제약은 이번 PR 에서 시험되지 않았다.**
- Site 1 의 분자·분모 시간축 불일치 — BL-446.
- Site 5 의 전 테넌트 전역 스코프 — BL-450.

---

## 5. 운영 레시피

### 소비처 5곳 현재값을 한 번에 재는 SQL

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -c "
SELECT 'S1_cumulative(strategy,all-time)' site, coalesce(sum(realized_pnl),0) val, count(*) n
  FROM trading.orders WHERE state='filled'
UNION ALL SELECT 'S2_daily(account,UTC day)', coalesce(sum(realized_pnl),0), count(*)
  FROM trading.orders WHERE state='filled'
   AND filled_at >= date_trunc('day', now() AT TIME ZONE 'UTC')
   AND filled_at <  date_trunc('day', now() AT TIME ZONE 'UTC') + interval '1 day'
UNION ALL SELECT 'S5_global_daily', coalesce(sum(realized_pnl),0), count(*)
  FROM trading.orders WHERE state='filled'
   AND filled_at >= date_trunc('day', now() AT TIME ZONE 'UTC')
   AND filled_at <  date_trunc('day', now() AT TIME ZONE 'UTC') + interval '1 day';"
```

### 특정 세션의 스코프 합계 (Site 3·4 가 보는 값)

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -c "
SELECT s.id, s.symbol, s.is_active,
       coalesce(sum(o.realized_pnl),0) AS scoped_pnl, count(o.id) AS n
FROM trading.live_signal_sessions s
LEFT JOIN trading.orders o
  ON  o.strategy_id = s.strategy_id
  AND o.exchange_account_id = s.exchange_account_id
  AND o.symbol = s.symbol
  AND o.state = 'filled'
  AND o.filled_at IS NOT NULL
  AND o.filled_at >= s.created_at
  AND (s.deactivated_at IS NULL OR o.filled_at < s.deactivated_at)
GROUP BY s.id, s.symbol, s.is_active ORDER BY s.created_at;"
```

### 테스트 실행 (3-env 의무)

```bash
cd backend && set -a && source .env.local && set +a && uv run pytest -q
```

★ **env 없이 돌리면 conftest 가 `localhost:5432` 로 폴백해 400+ 에러가 난다.** 우리 DB 는 **5433**(2026-07-25 정렬 완료, 5436 으로 되돌리지 말 것).

### 스택

db **5433** · redis **6380** · backend **8100** · frontend **3100** (3000 = nexus-core, 다른 앱).
워커 재빌드 — `docker compose … up -d --build --no-deps backend-worker backend-beat` (`--no-deps` 누락 시 db/redis 가 base 포트로 되돌아간다).
