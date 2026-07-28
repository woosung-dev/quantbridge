# soak 판정표 — live-entry-parity

> 세션 `147d79d2-fd21-4ec4-8ce8-4d8b799f3c0b` · PbR Pivot Reversal · BTC/USDT · 1m · Bybit demo `19a8166a`(쓰기).
> **T0 = 2026-07-28 07:13:33 UTC.** equity baseline 190,530.41528921 USDT.
> before 기준선은 `acceptance.md` §6.5 에서 동결한 값이다.

---

## A. 본체 판정 — 거절률 before/after

| 축               | before                                         | after   |
| ---------------- | ---------------------------------------------- | ------- |
| 조건부 주문 누적 | 67 (filled 7 / **rejected 29** / cancelled 31) | (§C 표) |
| **거절률**       | **43.3%** (29/67)                              | (§C 표) |
| `110093`         | **29건 = rejected 전건**                       | (§C 표) |
| 시장가 전환      | **기능 없음**                                  | (§C 표) |

★ 성공 판정은 **guard 카운터가 아니라 원장**으로 한다. `market_converted` 는 등재 시점의 **결정**이고 실제 발주는 별도 Celery 프로세스에서 일어나 그 뒤에도 거절될 수 있다(codex G1 #10).

## B. ★외부 오라클 — raw HMAC 직접 조회 (ccxt 미경유)

우리 코드도 ccxt 도 거치지 않고 Bybit v5 에 HMAC 서명으로 직접 물었다. 순환 오라클 차단.

```
=== 거래소 체결 (T0+8분 시점) : 4건, 전부 Market / Filled ===
  07:14:57  Sell 0.029 @ 63553      <- 시장가 전환 1
  07:15:51  Buy  0.029 @ 63520.3
  07:18:57  Sell 0.029 @ 63544.8    <- 시장가 전환 2
  07:21:51  Buy  0.029 @ 63506.8

=== 거래소 주문 이력 : 7건 ===
  조건부 3건 -> 전부 status=Deactivated (우리가 취소)
  시장가 4건 -> 전부 status=Filled
  reject=EC_NoError  x 7   <- ★거절 0건
```

★★ **before 에는 조건부 주문의 43%가 `110093` 으로 거절됐다. after 에는 조건부가 거절이 아니라 정상 취소로 끝나고, 돌파 건은 시장가로 실제 체결된다.**

★ DB↔거래소 대조 — 수량이 DB `0.029975` vs 거래소 `0.029` 로 갈리는 행이 있는데 이는 거래소 눈금 절삭이고 이미 문서화된 동작이다(`RestingConditionalEntry` 독스트링 — echo 를 비교에 쓰면 SSOT 가 둘이 된다).

★ 반전 사이징도 정상이었다 — `07:19:55 Buy 0.058` 는 숏 -0.029 에서 롱 +0.029 로 뒤집는 `target - current` 계산 결과다(취소로 종결).

## C. 최종 집계 — T0 `07:13:33` → `08:15` UTC (**62분**)

| 주문 종류                   | filled | submitted | cancelled | **rejected** | `110093`/`110092` |
| --------------------------- | ------ | --------- | --------- | ------------ | ----------------- |
| **CONVERTED**(시장가 전환)  | **5**  | 0         | 0         | **0**        | 0                 |
| conditional(조건부)         | 1      | 1         | 17        | **0**        | **0**             |
| market(엔진 직접 청산/진입) | 3      | 0         | 0         | 2            | 0                 |

### ★본체 판정

| 축                      | before            | after                                |             |
| ----------------------- | ----------------- | ------------------------------------ | ----------- |
| 조건부 주문             | 67                | 19                                   |             |
| **조건부 거절률**       | **43.3%** (29/67) | **0%** (0/19)                        | ✅          |
| `110093`                | **29건**          | **0건**                              | ✅          |
| 시장가 전환             | 기능 없음         | **5건 전부 체결**                    | —           |
| 거래소 오라클(raw HMAC) | —                 | **26 주문 전부 `reject=EC_NoError`** | ✅          |
| kill switch             | 0                 | **0**                                | —           |
| 실현손익                | −2.96 (직전 soak) | **−5.74 USDT** (5 청산)              | 수수료 지배 |

**가설이 맞았다.** stale 기준가가 원인이었고, 실시간 perp last price 로 교체하니 `110093` 이 **29 → 0** 이 됐다. 사라지던 진입은 시장가 전환 5건으로 실제 체결됐다.

★ 남은 거절 2건은 **`110017` reduce-only** 로 이번 건과 무관한 선재 클래스다(§D 참조).

### ★남은 유실 채널의 크기가 처음으로 측정됐다

```
qb_live_conditional_reconcile_errors_total{stage="deferred_market_inflight"}  14
```

**한 시간에 14회.** 시장가 주문이 in-flight 라 reconcile 전체가 건너뛰어진 횟수다(`live_signal.py:244-246`). 조건부 모델에서는 다음 bar 에 다시 등재되므로 무해했지만, **1-shot 전환에서는 유실**이다(codex G1 #2). "드문 일" 이 아니라 **시간당 14회**다 — 이 숫자가 다음 스프린트의 근거다(→ BL 등재).

## D. metric — 보이는가

```
qb_exchange_order_response_total{outcome="accepted",reason="submitted"}          27
qb_exchange_order_response_total{outcome="rejected",reason="reduce_only_violation"} 2
qb_live_conditional_guard_total{outcome="conditional_placed"}   19
qb_live_conditional_guard_total{outcome="market_converted"}      5
qb_live_conditional_guard_total{outcome="convert_suppressed"}    1
qb_live_conditional_guard_total{outcome="breach_with_resting"}   1
qb_live_conditional_guard_total{outcome="breach_reverted"}       0
qb_live_conditional_reconcile_errors_total{stage="deferred_market_inflight"} 14
qb_live_conditional_reconcile_errors_total{stage="positions"}                3
```

### ★★ 적대 검증이 예측한 `110017` 오분류가 실제로 일어났다

거절 2건은 `retMsg = "reduce-only order has same side with current position"` 이다. **"포지션이 0" 이 아니라 "같은 방향이라 거부"** 다.

거래소 실상 렌즈가 이걸 정확히 예측했다 — _"시장가 전환이 포지션을 뒤집으면 구 포지션의 reduce-only 청산 레그가 바로 110017 을 맞는데, 그게 `position_zero` 로 집계돼 전환 부작용이 지표에서 은폐된다."_

**F4 로 `110017` 을 `reduce_only_violation` 으로 정정하지 않았다면 대시보드에서 "포지션이 이미 0이라 무해" 로 읽혔을 것이다.** ccxt 에러맵(`110017 = Reduce-only rule not satisfied` / `110034 = There is no net position`)이 옳았고, 우리 원장의 옛 메시지만 보고 매핑했다면 틀렸을 것이다.

★ 실측 시퀀스 — `07:34:55` 전환(sell) 체결로 라이브가 숏이 된 뒤 `07:36:49` 에 엔진이 **롱을 닫는 reduce-only sell** 을 냈다. 그 순간 **시뮬과 라이브의 포지션 부호가 어긋나 있었다.** 선재 클래스지만(원장에 110017 이 이미 32건) 전환이 노출을 키운다 → BL 등재.

### ★★ `convert_suppressed` 가 실제로 발화했다

적대 검증(시간·경합 렌즈)이 요구한 **cross-bar 이중 진입 억제기**가 soak 첫 몇 분 안에 1회 발화했다. 전환 주문은 `trigger_price=NULL` 이라 다음 tick 의 `actual` 에 영원히 들어오지 않으므로 `return` 만으로는 다음 bar 를 못 막는다는 지적이었다. 이론이 아니라 **실재하는 경합**이었고, 그 수정이 없었으면 같은 진입이 두 번 나갔을 것이다.

### ★`reason="filled"` 는 이 거래소에서 사실상 죽은 버킷이다

Bybit demo 는 시장가 주문도 `create_order` 응답에서 `submitted` 로 돌려주고, 체결 확정은 **WS 가 나중에** 한다(`websocket/state_handler.py:233` · `reconciliation.py:231`). 그래서 `_execute_with_session` 의 `receipt.status == "filled"` 분기가 거의 타지 않는다. **이 거래소에서 "거래소가 수락했다" 의 신호는 `reason="submitted"` 뿐이다.**

★ 이것이 codex G1 검증 #6 의 가치를 사후에 증명한다 — 초안대로 `filled` 만 accepted 로 셌다면 **그 카운터는 영구히 0** 이었고, 보존 관계를 잴 수 없었을 것이다.

### ★metric 을 읽으려면 백엔드를 재기동해야 했다

`/metrics` 가 처음엔 신규 카운터를 **이름만(HELP/TYPE) 노출하고 샘플이 없었다.** 원인은 킥오프 §7 이 경고한 그대로 — 실행 중이던 백엔드가 `PROMETHEUS_MULTIPROC_DIR` 배선 **이전에** 뜬 프로세스라 단일 프로세스 모드였다. 그 상태에서 `/metrics` 는 **API 프로세스 자신의 값만** 보여준다(내가 관측한 ccxt 카운트도 전부 코크핏 페이지가 API 에서 낸 것이었다). 재기동하니 즉시 전부 노출됐다.

★ 진단 도중 **내 판독기가 먼저 틀렸다** — mmap 파일을 직접 열 때 `read_all_values_from_file` 이 4-튜플을 주는데 2-튜플로 풀고 예외를 삼켜, **1389개 파일 전부에서 metric 0개**라는 오답을 얻었다. "시스템이 고장났다" 로 갈 뻔했다. **측정값이 0이면 대상보다 계측기를 먼저 의심해라.**

## E. 화면 검증

`http://localhost:3100/trading` 정체성 프로브 통과(`트레이딩 · QuantBridge`). 활성 세션 1 · 킬 스위치 0 · 콘솔 error 0. §03 열린 포지션에 전환 체결분이 실제로 렌더됐다(`BTC/USDT 숏 0.029 진입가 63553.0`).

## F. 남은 유실 채널 (계측만, 이번에 고치지 않음)

`acceptance.md` §1.5 **G1-A** 참조 — 엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다(`event_loop.py:422` 가 `action="fill"` 을 dispatch 대상에서 제외한다). 이번 스프린트는 **가장 큰 부분(발주 전 돌파)** 을 닫았고 나머지는 보이게 만들었다.
