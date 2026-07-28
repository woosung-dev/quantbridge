# live-entry-parity — 라이브가 백테스트의 진입 절반을 버리는 것을 멈춘다

> 2026-07-28 · 브랜치 `feat/live-entry-parity` · 베이스 `main@a24dbc5c` · 마이그레이션 **0**
> 방법론 = `docs/guides/generator-evaluator-pipeline.md` **3/3 검증 회차 (승격 조건 충족)**
> BL-511(P1) · BL-512(P2) Resolved · 신규 BL-522~525

---

## 1. 무엇이 문제였나

직전 세션이 계기판을 붙이고 1시간 40분 돌렸더니 **발주된 조건부 진입 주문의 절반이 거래소에 거절**되고 있었다. 사유는 100% `retCode 110093` — "떨어질 것을 기대했는데 트리거가 이미 현재가 아래다".

원장 전수(G0 재집계): 조건부 주문 **67건 중 29건 거절 = 43.3%**, 전부 `110093`, 전부 short.

원인은 가드가 쓰는 기준가가 **마지막 종료 bar 종가**(`_last_close_or_none`)인데 거래소는 **현재가**로 판정하는 것이다. 1분봉에서 최대 60초 스테일 → 가드가 체계적으로 뚫린다.

**QuantBridge 의 제품 전제는 백테스트 → 라이브 패리티다.** 백테스트가 의도한 진입의 절반이 라이브에서 조용히 사라지고, 사라졌다는 사실조차 metric 에 안 보였다.

## 2. 무엇을 했나

### BL-511 — 진입 패리티

1. **기준가를 거래소 실시간 perp last price 로 교체.** 주문이 `trigger_by="LastPrice"` 로 나가므로 거래소와 **같은 자**로 재야 한다.
2. **돌파 판정 시 시장가 전환.** 근거는 **우리 백테스트 엔진 코드**다 — `strategy_state.py:67-84` 의 `PendingOrder.try_fill` 은 같은 bar 즉시 체결을 막고, 다음 bar 에서 short 는 `low <= stop` 이면 `min(open, stop)` 에 체결한다. 즉 **돌파 상태면 백테스트는 다음 bar 시가(사실상 시장가)에 체결한다.** 라이브 평가는 bar 마감 직후 도므로 "지금 시장가" ≈ 그 시가다.
   - TV 문서도 같다 — _"When a strategy generates a stop order at a better value than the current market price, it activates the subsequent order without waiting for the market price to reach that value."_ (단 이건 **broker emulator = 백테스트** 규칙이다.)
   - ★**BL-478 의 "(b) 비권장" 판정과 충돌하지 않는다.** 그때의 (b)는 _모든_ stop 진입을 시장가로 근사(트리거 대기 자체 포기)였고, 지금은 **이미 돌파된 건만** 전환한다.
3. **전환은 `matching_actual` 이 빈 경우로 한정.** resting 조건부가 있는데 돌파라면 **거래소가 이미 그 주문을 트리거했을 확률이 높다** — 취소하고 시장가를 내면 이중 진입이다. 관측된 거절 29건은 발주 자체가 거절돼 resting 이 된 적이 없으므로 이 한정이 실제 결함을 100% 덮는다.
4. **사용자 설정 상한** `StrategySettings.max_trigger_breach_pct`(기본 `None` = 무제한 = 백테스트와 동일). 마이그레이션 0(JSONB).
5. **기준가 조회 실패 = 전환만 금지**, 조건부 등재는 bar 종가 폴백으로 계속(사용자 결정).

### BL-512 — 거래소 응답 계측

- `qb_exchange_order_response_total{exchange,outcome,reason}` — **`retCode` 숫자로** 정규화. ★ccxt 예외 클래스로는 안 된다: `110093`(트리거 방향)과 `110017`(reduce-only)이 **둘 다 `InvalidOrder`** 다.
- `outcome` ∈ `accepted|rejected|**unknown**` — ★응답을 못 읽은 것(타임아웃·비CCXT 예외·malformed)을 "거절" 로 세면 **개선치가 오염된다.**
- `qb_live_conditional_guard_total{outcome}` 7종 — 가드 판정을 센다.
- 정상 체결이 `exchange_missing` error 카운터를 올리던 오계상 수정.

### 부수

- `run_live` 에 **`fill_timing` 배선** — 라이브가 항상 `bar_close` 고정이었다(지난 스프린트가 고친 미배선 인자 4종에 이은 **5번째**). `next_bar_open` 은 진입뿐 아니라 **청산도 한 bar 늦춘다**는 사실을 독스트링·UI 에 명시.
- FE — 신규 두 필드 노출 + 백테스트 폼 불일치 배지 + **`.strict()` zod 가 신규 키를 거부해 저장 즉시 화면이 깨지던 P1** 수리.

## 3. ★검증이 구현보다 값이 컸다

### 3.1 적대 검증(거래소 실상 렌즈)이 스프린트를 구했다

**가드 기준가가 perp 이 아니라 스팟이었다.** 실거래소 실측:

```
ccxt.market("BTC/USDT")      -> type=spot
ccxt.market("BTC/USDT:USDT") -> type=swap, linear=True
spot last=63561.2   perp last=63526.7   차이 34.50 USDT (0.0543%)
```

우리가 잡으려던 돌파폭은 **중앙값 15.60(0.025%) / 최대 46.50(0.071%)**. **측정 오차가 신호 중앙값보다 컸다.** 그대로 soak 을 돌렸으면 숫자는 나왔겠지만 그 숫자가 무엇을 뜻하는지 알 수 없었다.

덤 — **ccxt ticker 에 `"mark"` 키는 없다**(`info.markPrice` 에 있다). `fetch_mark_price` 는 도입 이래 한 번도 mark 를 읽은 적이 없고 늘 `last` 로 폴백했다(선재 결함, 함께 수리).

### 3.2 G1 플랜 검증이 "계측이 성공을 못 세는 설계" 를 코드 쓰기 전에 잡았다

초안은 "성공 = `filled`" 였다. 그런데 `tasks/trading.py` 에는 **`submitted` 라는 별도 성공 경로**가 있고, **조건부 진입이 정상 등재되면 전부 그 경로**다. soak 실측이 사후 증명했다 — `accepted/submitted` **27** vs `filled` **0**. Bybit demo 는 시장가도 `submitted` 로 응답하고 체결은 WS 가 확정한다. 초안대로 갔으면 그 카운터는 **영구히 0** 이었다.

### 3.3 예측이 라이브에서 실현됐다

거래소 실상 렌즈가 적었다 — _"시장가 전환이 포지션을 뒤집으면 구 포지션의 reduce-only 청산 레그가 바로 110017 을 맞는데, 그게 `position_zero` 로 집계돼 전환 부작용이 지표에서 은폐된다."_

soak 중 정확히 그것이 일어났다. `07:34:55` 전환(sell) 체결로 라이브가 숏이 된 뒤 `07:36:49` 에 엔진이 **롱을 닫는 reduce-only sell** 을 냈고 `110017 "reduce-only order has same side with current position"` 으로 거절됐다. ccxt 에러맵대로 `reduce_only_violation` 으로 정정해뒀기에 **"무해" 로 위장되지 않았다**(`110034` 가 진짜 "포지션 없음" 이다). 그 순간 **시뮬과 라이브의 포지션 부호가 어긋나 있었다** — 선재 클래스지만(원장에 110017 이 이미 32건) 전환이 노출을 키운다.

★**시간·경합 렌즈가 요구한 cross-bar 이중 진입 억제기도 실제로 발화했다** — `qb_live_conditional_guard_total{outcome="convert_suppressed"}` **1**. 전환 주문은 `trigger_price=NULL` 이라 다음 tick 의 `actual` 에 영원히 들어오지 않으므로, `return` 만으로는 다음 bar 를 못 막는다는 지적이었다. **이론이 아니라 실재하는 경합이었고**, 그 수정이 없었으면 같은 진입이 두 번 나갔다.

### 3.4 G6 가 평가자 수선을 잡았다 (8세션 연속 P1)

평가자가 손댄 2줄 중 하나 — `interval_seconds` 를 `[]` → `.get(..., 3600)` 으로 바꾸면서 주석에 "과잉 억제는 안전한 방향" 이라 적었다. **창 크기에는 맞지만 전환 허용 여부에는 틀렸다.** `[]` 는 `KeyError` 로 전환을 통째로 막았는데(fail-closed) `.get` 은 전환을 계속 발주한다. 명시적 감지 + 전환만 차단으로 재정정.

### 3.5 ★반대로 평가자의 계측기가 3번 틀렸다

| #   | 오류                                                        | 오답                                                                       |
| --- | ----------------------------------------------------------- | -------------------------------------------------------------------------- |
| 1   | 변이 M15 를 **취소 루프 뒤**에 주입                         | 그 지점에선 `return` 과 `to_place=()` 가 동치 → "테스트가 약하다" 로 갈 뻔 |
| 2   | 변이 F7 을 두 가드가 **같은 mock** 을 쓰는 상태에서 주입    | 서로를 가려 통과 → 판별 테스트 추가로 해결                                 |
| 3   | `MmapedDict.read_all_values_from_file` 을 **2-튜플로 언팩** | 예외를 삼켜 **"1389개 파일 전부에 metric 0개"** → "시스템 고장" 으로 갈 뻔 |

**셋 다 대상이 아니라 계측기의 결함이었다.** 교훈 — **측정값이 0이거나 변이가 탈출하면, 대상보다 계측기를 먼저 의심해라.**

## 4. soak 판정 (T0 `07:13:33` → `08:15` UTC, 62분)

세션 `147d79d2` · PbR Pivot Reversal · BTC/USDT · 1m · Bybit demo `19a8166a`.

| 축                          | before            | after                                |
| --------------------------- | ----------------- | ------------------------------------ |
| 조건부 주문                 | 67                | 19                                   |
| **거절률**                  | **43.3%** (29/67) | **0%** (0/19)                        |
| **`110093`**                | **29건**          | **0건**                              |
| 시장가 전환                 | 기능 없음         | **5건 전부 체결**                    |
| **거래소 오라클(raw HMAC)** | —                 | **26주문 전부 `reject=EC_NoError`**  |
| kill switch                 | 0                 | 0                                    |
| 실현손익                    | −2.96(직전)       | **−5.74 USDT** (5 청산, 수수료 지배) |

**가설이 맞았다.**

### 외부 오라클 원문 (raw HMAC, ccxt 미경유)

우리 코드도 ccxt 도 거치지 않고 Bybit v5 에 HMAC 서명으로 직접 물었다 — 순환 오라클 차단.

```
=== 거래소 주문 이력 (T0 이후) : 26건 ===  reject=EC_NoError x 26
  07:14:01  Buy  0.029  status=Deactivated  trigger=63653      <- 조건부, 우리가 취소
  07:14:57  Sell 0.029  status=Filled       trigger=-          <- ★시장가 전환 1
  07:15:51  Buy  0.029  status=Filled       trigger=-
  07:17:55  Buy  0.029  status=Deactivated  trigger=63587.8
  07:18:57  Sell 0.029  status=Filled       trigger=-          <- ★시장가 전환 2
  07:19:55  Buy  0.058  status=Deactivated  trigger=63587.8    <- 반전 사이징(target-current)
  ...
조건부 -> 전부 Deactivated(정상 취소).  시장가 -> 전부 Filled.  거절 0건.
```

★ DB↔거래소 수량이 `0.029975` vs `0.029` 로 갈리는 행이 있는데 이는 **거래소 눈금 절삭**이고 이미 문서화된 동작이다(`RestingConditionalEntry` 독스트링 — echo 를 비교에 쓰면 SSOT 가 둘이 된다).

### 화면 검증

`http://localhost:3100/trading` 정체성 프로브 통과. 활성 세션 1 · 킬 스위치 0 · **콘솔 error 0** · §03 열린 포지션에 전환 체결분이 실제로 렌더(`BTC/USDT 숏 0.029 진입가 63553.0`). ★중간에 콘솔 error 17건이 보였으나 전부 `ERR_CONNECTION_REFUSED` — **내가 metric 배선을 위해 백엔드를 재기동한 창**의 것이고 앱 결함이 아니었다(재적재 후 0).

### ★metric 을 읽으려면 백엔드를 재기동해야 했다

`/metrics` 가 처음엔 신규 카운터를 **이름만(HELP/TYPE) 노출하고 샘플이 없었다.** 원인은 킥오프 §7 이 경고한 그대로 — 실행 중이던 백엔드가 `PROMETHEUS_MULTIPROC_DIR` 배선 **이전에** 뜬 프로세스라 단일 프로세스 모드였고, 그 상태에서 `/metrics` 는 **API 프로세스 자신의 값만** 보여준다. 그때 내가 "worker metric 이 전파된다" 는 근거로 삼은 ccxt 카운트도 사실은 **코크핏 페이지가 API 에서 낸 것**이었다.

### 남은 유실 채널의 크기가 처음 측정됐다

```
qb_live_conditional_reconcile_errors_total{stage="deferred_market_inflight"}  14
```

**시간당 14회.** 시장가 주문이 in-flight 라 reconcile 전체가 건너뛰어진 횟수다. 조건부 모델에선 다음 bar 에 재등재되므로 무해했지만 **1-shot 전환에서는 유실**이다 → **BL-522(P1)**.

★**이번 스프린트는 그것을 고치지 않았다.** 의도 영속화는 새 상태 저장소이고, 크기를 모르는 채 만드는 것이 최대 위험이었다. 이제 숫자가 있다.

## 5. 정직한 위치

**"패리티 격차를 닫았다" 고 쓰면 거짓이다.** 사실은:

- **발주 전 돌파로 인한 유실을 닫았다** (`110093` 29 → 0).
- **잔여 유실 채널 5종을 계측 가능하게 만들었다** (BL-522 에 크기와 함께 등재).

## 6. 게이트

BE **3341**(baseline 3277, +64) / 커버리지 래칫 **93.14%** / FE **1191**(baseline 1182, +9) / ruff·mypy(209)·typecheck·lint **0** / `pnpm build` ✓ / e2e:authed **65** · canon **32** / rules-of-hooks 통과 / **마이그레이션 0**.

변이 **누적 21종 전건 판별**(W1 5 · W2 10 · W3 2 · W6 3, 탈출 3건은 전부 계측기 결함으로 재조준 후 검출).

codex 세션 **7회** — 플랜 검증 1(G1) + 구현 4(W1~W4) + 수리 2(W5 적대검증 · W6 최종리뷰).
