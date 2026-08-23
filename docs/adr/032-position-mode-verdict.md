# ADR-032 — 포지션 모드는 one-way 로 유지한다 (헤지 모드 기각)

- **Status:** Accepted (2026-08-14)
- **회차:** money-path-attribution
- **관련:** [BL-438](../backlog.md) · [ADR-025](./025-conditional-fill-ownership.md) · [BL-003](../backlog.md#bl-003)

## Context

[BL-438] 분석 중 `Order.realized_pnl` 백필이 `reduce_only=true` 인 주문만 대상으로 삼아
실현손익의 90.9%를 놓치고 있음이 드러났다. 소크 전략은 **반전 주문**(`sell 0.058 = 2×0.029`)
을 쓰는데 반전에는 `reduce_only` 를 걸 수 없기 때문이다.

여기서 「헤지 모드로 가면 반전이 구조적으로 불가능해지므로 `reduce_only` 가 다시 신뢰
가능해진다」는 갈래가 열렸다. 사용자가 OKX 의 `posSide` 기반 open/close 분리를 근거로
제안했고, 도입 여부를 **실거래소 프로브로** 판정했다.

## Decision

**one-way 모드를 유지한다. 헤지 모드를 도입하지 않는다.**

## 근거 — Bybit demo 실측 (T1~T5, 시험대 `ETHUSDT`)

소크는 `BTC/USDT` 만 돌고 포지션 조회 5개 지점이 전부 심볼 스코프
(`fetch_open_positions(creds, sess.symbol)`)라, `ETHUSDT` 를 시험대로 잡아 소크를 건드리지
않고 판정했다. `switch-mode` 는 심볼 단위가 최우선이라 `BTCUSDT` 모드도 불변이었다.

|        | 검사                                    | 결과                                                          |
| ------ | --------------------------------------- | ------------------------------------------------------------- |
| T1     | 데모에서 `switch-mode(ETHUSDT, mode=3)` | ✅ `retCode 0` — **데모가 심볼 단위 전환을 지원한다**         |
| T2     | long·short 동시 보유                    | ✅ `positionIdx=1 Buy 0.01` + `positionIdx=2 Sell 0.01` 2 leg |
| T3     | 청산에 `reduceOnly` 필수?               | ❌ **불필요 — 공식 문서가 반증됐다**                          |
| **T4** | **`closed-pnl` 이 leg 를 구분?**        | ❌ **구분 못 한다 — 이것이 기각 근거다**                      |
| T5     | 복구                                    | ✅ 잔여 0건 · one-way 복귀 · `BTCUSDT` `positionIdx 0` 불변   |

### T3 — 문서가 틀렸다 (기각 근거가 **아니다**)

Bybit 문서는 `reduceOnly` 에 대해 "You **must** specify it as `true` when you are about to
close/reduce the position" 이라고 적는다. 실측은 반대다:

```
reduceOnly=False 로 positionIdx=1 에 sell 0.01  →  수락됨
그 뒤 포지션: positionIdx=2 Sell 0.01 만 남음   →  long leg 가 청산됐다
```

`(side, positionIdx)` 만으로 열기/닫기가 결정된다 — OKX 의 `(side, posSide)` 와 같은 구조다.
**즉 사용자의 원래 직관이 맞았고, 「Bybit 은 OKX 와 달리 reduceOnly 가 필요하다」는 문서
기반 판단이 거짓이었다.**

### T4 — 그러나 이것이 도입 근거를 없앤다

헤지 모드에서 만든 청산인데 `closed-pnl` 응답 키가 one-way 시절과 **동일한 19종**이다:

```
avgEntryPrice avgExitPrice closeFee closedPnl closedSize createdTime cumEntryValue
cumExitValue execType fillCount leverage openFee orderId orderPrice orderType qty
side symbol updatedTime
```

`positionIdx` 가 **없다.** 그래서 헤지로 가도 "이 손익이 어느 leg 것인가"는 여전히 `orderId`
로 **주문 이력을 조인**해야 안다 — one-way 에서 이미 하는 그 일이다.
⇒ **귀속 이득 = 0.**

그리고 T3 때문에 다른 이득도 사라진다. 헤지에서는 `reduce_only` 가 의미를 잃으므로 "이 주문이
청산했는가"는 `(side, positionIdx)` 조인으로 답해야 하고, 그것은 **원장 조인과 비용이 같다**.

### 대가

반전·순포지션 가정이 **163곳 / 12파일**에 박혀 있고 그중 4개가 `strategy/pine_v2/` 다
(`event_loop.py`·`strategy_state.py`·`stdlib.py`·`alert_hook.py`). **Pine Script 의 도메인
모델 자체가 순포지션이다** — `strategy.position_size` 는 부호 하나 달린 숫자 한 개고 long·short
동시 보유를 표현할 수 없다. 헤지 거부는 이미 계약으로 굳어 있다:
`providers.py:1072` `hedge_mode_unsupported` · `close_service.py:149,153` HTTP **409** ·
`schemas.py:487` `close_blocked_reason` 리터럴 · `conditional_entry_planner.py:381`.

## Consequences

- [BL-438] 의 처방은 **원장 조인**이다 — 백필 대상 선정을 `reduce_only` 가 아니라
  「거래소 원장이 그 주문의 청산 행을 갖고 있는가」로 바꾼다. 이 판정 축은 Bybit
  `closed-pnl`(주문 단위 · 실측 1행/주문, 592/592)과 OKX `fills.fillPnl != 0`
  ("Returns 0 for opening trades") 양쪽에 공통이라 **OKX 합류 시에도 깨지지 않는다.**
- 헤지 모드는 **실행 가능성이 증명된 채로** 보류된다. 재개 조건은 하나 —
  **long·short 을 동시에 굴리는 전략을 지원하기로 결정할 때.** 그때 T1·T2 가 데모에서
  전환·동시보유가 된다는 것을 이미 증언한다. 그건 리팩터가 아니라 **새 기능**이고,
  Pine 전략은 그 요구를 표현할 수 없으므로 먼저 답할 질문은 「어떤 전략이 헤지를
  필요로 하는가」다.
- 프로브가 만든 `ETHUSDT` 청산 2건이 다음 스윕에서 `exchange_exits` 에 `unknown/none`
  으로 들어온다. 우리 앱 주문이 아니므로 `trading.orders` 에 없다 — **결함이 아니다.**

## 부수 실측 (이 프로브가 확정한 것)

- **`closedPnl` 은 수수료 차감 순액이다** — 검산: gross −1.0788 − 수수료 2.0203 = −3.0991.
  요율은 단면 **0.055%** taker(`openFee/cumEntryValue` = `closeFee/cumExitValue`).
- **전환 실패 코드** — `110024` 포지션 있음 · `110028` 미체결 주문 있음 ·
  `110029` 이 심볼 헤지 미지원 · `110025` 변경 없음.
- **ccxt 4.5.49** 가 `set_position_mode(hedged, symbol)` 을 심볼 단위로 지원한다.
- 수수료 지배가 ETH 왕복에서도 재현됐다 — gross `+0.0017` · 수수료 `0.0206` · 순 `−0.0189`
  ([BL-724](../backlog.md)).
