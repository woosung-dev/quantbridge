# live-entry-parity — G1 수용 기준 동결 (구현 전 작성)

> 2026-07-28. 브랜치 `feat/live-entry-parity`, 베이스 `main@a24dbc5c`.
> 이 문서는 **구현 전에** 평가자(Claude)가 쓴다. 표적 변이도 여기 있다 — 구현을 보고 만든 변이는 구현에 맞춰지기 때문이다.
> 방법론 = `docs/guides/generator-evaluator-pipeline.md` §G1.

---

## 0. 무엇을 고치는가

라이브 조건부 진입(stop-market)의 **43%가 거래소에 거절**된다(원장 전수 67건 중 29건, 100%가 `retCode 110093`). 가드 `trigger_already_breached`(`conditional_entry_planner.py:187-202`)의 기준가가 **마지막 종료 bar 종가**인데 거래소는 **현재가**로 판정하기 때문이다.

백테스트 엔진은 이 상황을 **다음 bar 시가에 체결**시킨다(`strategy_state.py:67-84`, 갭이면 `min(open, stop)` = `open`). 그러므로 라이브도 **시장가로 전환**하는 것이 패리티다.

---

## 1. 확정된 설계 위험 답 (구현 전 코드 대조 완료)

| #       | 위험                                                 | 확정된 답                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 근거                                                                                                                                                  |
| ------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1      | 시장가 전환의 이중 진입                              | **한 tick 에 전환은 최대 1건, 전환 후 그 tick 의 나머지 등재를 중단**한다. 기존 `fill_confirmed`(`live_signal.py:581-585`)·`cancel_raced`(`:586-591`)·`market_orders_in_flight`(`:244-246`)와 **같은 규칙** — "포지션 스냅샷을 낡게 만드는 일이 생기면 이 tick 은 더 등재하지 않는다"                                                                                                                                                                                                                                                                   | `live_signal.py:238-242` 독스트링이 이 불변식을 명시                                                                                                  |
| **R1b** | ★**멱등키 재사용 = 조용한 무발주**                   | **전환에는 별도 키 네임스페이스**를 쓴다. 호출부가 `body_hash=None` 을 넘기므로(`live_signal.py:648`), 같은 키가 이미 있으면 payload 가 달라도 **conflict 없이 캐시 응답 + dispatch 생략**이다 — 거래소엔 아무것도 안 나가는데 DB·metric 은 "등재됨" 으로 보고한다                                                                                                                                                                                                                                                                                      | **재현 확인** `order_service.py:336-349`                                                                                                              |
| R2      | `to_cancel` 과 발주의 순서                           | **이미 안전하다.** 취소 루프(`:508-578`)가 발주 루프(`:615-650`)보다 먼저이고, `cancel_failed`/`cancel_raced` 면 발주 전에 `return` 한다                                                                                                                                                                                                                                                                                                                                                                                                                | `live_signal.py:579-591`                                                                                                                              |
| **R2b** | ★**resting 조건부가 있는데 돌파면 전환하면 안 된다** | resting 주문은 등재 당시 **미돌파**였다. 지금 돌파라는 건 가격이 그 트리거를 지났다는 뜻이고, 그러면 **거래소가 이미 그 주문을 트리거했을 것**이다. 취소+시장가 = 이중 진입. → **전환은 `matching_actual` 이 빈 경우로 한정**한다. ★관측된 거절 29건은 **전부 이 경우**다(발주 자체가 거절돼 resting 이 된 적이 없다) — 즉 이 한정이 실제 결함을 100% 덮는다. resting 이 있는 돌파는 **기존 동작(취소+등재 생략)을 유지하되 계측**한다                                                                                                                  | **재현 확인** — 포지션 스냅샷(`live_signal.py:457`)이 취소 루프(`:508`)보다 **먼저** 찍힌다                                                           |
| R3      | 전환 주문이 새로 타는 게이트                         | **notional 가드의 기준가가 바뀐다.** 조건부는 `effective_price = req.trigger_price`(REST 없음)인데, 전환 주문은 `trigger_price=None` 이라 **`fetch_mark_price` REST 1회 + `mark * 1.02` 버퍼**를 탄다. live 는 조회 실패 시 `BalanceUnverified`, demo 는 fail-open. ★그리고 `_validate_position_size`(`:107-135`)가 stop 을 `req.trigger_price` 에서 읽으므로 **risk-sizing 가드가 전환 주문에서는 skip 된다**(현재 `risk_percent` 미전달이라 무해하나 의미가 바뀐다 — 주석으로 못박는다)                                                               | `order_service.py:107-135, 224-233, 283-294`                                                                                                          |
| R4      | fail-closed 의 하류 영향                             | 스캐너 오판은 **없다** — 새 행이 안 생기고 resting 조건부는 `list_stuck_submitted` 가 `trigger_price IS NULL` 로 **면제**한다. 전환된 시장가는 `trigger_price IS NULL` 이라 30분 stuck 감지 **대상이 된다(의도된 이득)**. ★**단 구현 형태가 중요하다 — 조기 `return` 으로 만들면 안 된다.** kill switch·세션 비활성·stand-down 은 전부 `desired=[]` + **취소 루프**에 의존하므로(`live_signal.py:292-297, 466-481`), 함수를 일찍 빠져나오면 **위험한 주문이 거래소에 남는다.** fail-closed 는 **`to_place` 를 비우는 것**이지 함수를 멈추는 것이 아니다 | `order_repository.py:611-640` · `live_signal.py:292-297,466-481`                                                                                      |
| R5      | `next_bar_open` 의 라이브 의미                       | **신호가 정확히 한 bar 늦게 나오고 유실되지 않는다.** warmup replay 라 매 tick 큐가 재생되고, bar N 에서 큐된 인텐트는 bar N+1 replay 의 `process_market_intents` 가 시가에 체결한다. 그 bar 가 last bar 이므로 `run_live` 기본 발행 대상이다. ★**단 Track A 는 `next_bar_open` 미지원 — 경고만 남기고 조용히 `bar_close` 로 실행**된다                                                                                                                                                                                                                 | `strategy_state.py:504-545`, `event_loop.py:333-336`, `virtual_strategy.py:213-218`                                                                   |
| R6      | `StrategySettings` 확장 파급                         | **마이그레이션 0.** JSONB + `validate_strategy_settings` 라 기존 행은 필드 부재 → 기본값. `extra="forbid"` 는 입력 미지 키만 막는다. 미러 의무 = `UpdateStrategySettingsRequest`(`schemas.py:134-142`) + `router.py:130` `StrategySettings(**data.model_dump())`. ★**PUT 은 부분 갱신이 아니라 전체 치환**이므로 신규 필드를 안 보내는 클라이언트는 기존 값을 기본값으로 되돌린다 — 계약으로 명시한다. ★FE 함정: `tab-metadata.tsx` 가 `valueAsNumber` 패턴이라 **빈 입력이 `NaN` → 422** 다. nullable 전처리 필수                                      | 소비처 전수 = `live_signal.py:908,1707` · `webhook.py:121-140` · `close_service.py:50` · `live_session_service.py:91` · `backtest/service.py:900-902` |
| **R7**  | ★**전환의 유실 채널**                                | `market_orders_in_flight` 면 reconcile 전체가 deferred 된다(`live_signal.py:244-246`). 조건부 모델에선 무해했다(다음 bar 에 다시 등재). **1-shot 전환에서는 유실**이다 — 다음 bar 엔 sim 이 이미 체결해 `desired` 에서 빠지고, `action="fill"` 은 dispatch 대상이 아니다(`event_loop.py:422`). **고치지 않고 계측한다** — 기존 `stage="deferred_market_inflight"` 카운터를 soak 판정표에 넣는다                                                                                                                                                         | `live_signal.py:244-246` · `event_loop.py:422`                                                                                                        |

★ R3 의 귀결 — **전환 주문은 조건부보다 명목이 2% 크게 평가된다.** 경계에서 `NotionalExceeded` 로 갈릴 수 있다. 수용 기준 W2-9 로 고정한다.

★ R5 의 귀결 — Track A + `next_bar_open` 은 **라이브가 조용히 무시**한다. "되는 척" 이므로 계측 의무를 W3-3 으로 고정한다.

★ **R5 의 두 번째 귀결 — `next_bar_open` 은 청산도 한 bar 늦춘다.** `close`/`close_all` 도 같은 인텐트 큐를 탄다(`interpreter.py:1574,1600`). 손절 청산이 1 bar 지연된다는 뜻이다. **기본값을 `bar_close` 로 두는 이유가 이것이고, 문서에 명시한다.**

★ **SSOT 충돌.** 백테스트 `fill_timing` 은 **실행 폼 입력**(`backtest/schemas.py:67`)인데 라이브는 `StrategySettings` 를 읽게 된다. 같은 파라미터에 SSOT 가 둘이면 "백테는 `next_bar_open`, 라이브는 `bar_close`" 가 **조용히** 성립한다. → 라이브 설정을 SSOT 로 두고, **백테스트 폼이 전략 라이브 설정과 다르면 경고 배지**를 띄운다(기존 mirror 배지 패턴 재사용).

---

## 1.5 codex G1 플랜 검증 — 11건 전건 재현 판정

`codex exec -s read-only` 1회. **액면 수용 0건.** 각 항목을 코드로 재현한 뒤 처분했다.

| #   | codex 지적                                                     | 판정                                                                                                                                                 | 처분                                                                                                              |
| --- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | 잔여 `110093` 이 영구 미진입이 된다                            | **재현**                                                                                                                                             | → **G1-A 단일 근본원인**(아래). 계측 + BL 등재, 이번에 안 만든다                                                  |
| 2   | R7(defer)은 계측만으로 유실을 못 막는다                        | **재현**                                                                                                                                             | → G1-A                                                                                                            |
| 3   | 전환 주문의 부분체결이 목표 미달로 고착                        | **재현** — `tasks/trading.py:485-492` 가 `qb_partial_fill_total` 만 올리고 끝난다                                                                    | → G1-A                                                                                                            |
| 4   | R2b 의 "이미 트리거됐을 것" 은 취소↔트리거 경합을 증명 못 한다 | **재현** — 맞다. **기존 동작을 보존**하는 선택이지 증명이 아니다                                                                                     | → G1-A + `breach_with_resting` 계측                                                                               |
| 5   | W2-9 는 미진입을 고정할 뿐 복구하지 않는다                     | **재현** — `live_signal.py:651-656` 이 로그+`stage="place"` 로 삼킨다                                                                                | → G1-A + 카운터 사유 분리                                                                                         |
| 6   | ★**`accepted` 가 `submitted` 성공 경로를 놓친다**              | **재현** — `tasks/trading.py:531-551` 이 별도 성공 경로다                                                                                            | **W1-2 수정**(아래). 치명적이었다                                                                                 |
| 7   | ★**W3-3 Track A 경로는 라이브에 존재하지 않는다**              | **재현** — `run_live` 는 `run_historical` 만 부르고(`event_loop.py:380`), `run_virtual_strategy` 는 `TrackRunner._dispatch_table["A"]` 로만 도달한다 | **W3-3 폐기**                                                                                                     |
| 8   | M8·M9 가 서술만으로는 판별 게이트가 아니다                     | **재현**                                                                                                                                             | **변이 정의 강화**(§6)                                                                                            |
| 9   | `float` 필드가 Decimal-first 규칙 위반                         | **부분** — 규칙은 맞으나 **바로 옆 `position_size_pct` 가 이미 `float`** 다(`schemas.py:119`)                                                        | API 는 `float` 유지(주변 코드 일치), **planner 경계에서 `Decimal(str(x))`** 로 변환 — CLAUDE.md 가 지정한 그 패턴 |
| 10  | ★**보존 관계가 "결정" 을 "성공" 으로 오인**                    | **재현** — `market_converted` 는 결정 시점 카운터이고, dispatch 는 별도 프로세스라 그 뒤에도 거절될 수 있다                                          | **성공 기준을 원장 기반으로 교체**(§6.5)                                                                          |
| 11  | guard metric outcome 집합 자기모순                             | **재현** — 내 문서 오류다. W1-4 는 4개, W2-3a 는 목록 밖 값을 요구했다                                                                               | **5개로 정정**                                                                                                    |

### ★G1-A — 지적 1·2·3·4·5 는 **하나의 근본원인**이다

> **엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다.**

sim 이 pending stop 을 체결하면(`strategy_state.py:82-83`) 그 주문은 `desired` 에서 사라지고 포지션이 된다. 그런데 `action="fill"` 은 **dispatch 대상이 아니다** — `event_loop.py:422` 가 "broker 가 자체 fill 알림 처리" 를 전제하기 때문이다(BL-478 이 지적한 바로 그 전제). 따라서 그 진입이 라이브에서 어떤 이유로든 완결되지 못하면 — 잔여 거절 · defer · 부분체결 · 취소 경합 · notional 거부 — **다시 시도할 주체가 없다.**

**이번 스프린트의 정직한 위치:**

- 이 결함은 **오늘 이미 100% 발생 중**이다(거절 29건 전부가 이 경로로 유실됐다).
- 전환은 **가장 큰 부분(발주 전 돌파 판정)** 을 닫는다. **전부는 아니다.**
- 나머지는 **계측해서 크기를 재고 BL 로 등재**한다. 이번에 의도 영속화 기계를 새로 만들지 않는다 — 새 상태 저장소는 이 스프린트가 낼 수 있는 가장 큰 위험이고, 크기를 모르는 채로 만들 이유가 없다.
- ★**문서·PR 에 "패리티 격차를 닫았다" 고 쓰지 마라.** "발주 전 돌파로 인한 유실을 닫았고, 잔여 유실 채널 5종을 계측 가능하게 만들었다" 가 사실이다.

## 1.6 G3 적대 검증 — 12건, P1 6건 실재

읽기 전용 서브에이전트 3기(거래소 실상 / 시간·경합 / 백테스트 패리티). 전건 코드 재현 판정.

★★★ **최대 발견 — 기준가가 perp 이 아니라 스팟이었다.** 실거래소 실측(2026-07-28):

```
ccxt.market("BTC/USDT")      -> type=spot
ccxt.market("BTC/USDT:USDT") -> type=swap, linear=True
spot last=63561.2   perp last=63526.7   차이 34.50 USDT (0.0543%)
```

우리가 잡으려는 돌파폭은 **중앙값 15.60 / 최대 46.50**. **측정 오차가 신호 중앙값보다 크다.** 이대로 soak 을 돌렸으면 숫자는 나왔겠지만 그 숫자가 무엇을 뜻하는지 알 수 없었다. → **F1** 로 수리(`_to_bybit_linear_symbol` 적용).

★ **부수 발견** — ccxt ticker 에 `'mark'` 키가 **없다**(실측 `has 'mark'? False`). `fetch_mark_price` 는 도입 이래 한 번도 mark 를 읽은 적이 없고 늘 `last` 로 폴백했다. 기존 notional 가드의 선재 결함이다 → **F2**.

★★ **롱 돌파코드 `110092` 누락.** ccxt 에러맵 실측 — `110092`="expect Rising"(롱), `110093`="expect Falling"(숏). 우리 데이터가 100% short 라 안 보였을 뿐, 롱 진입의 돌파 거절은 전부 `other` 로 떨어졌을 것이다 → **F3**.

| 수리       | 내용                                                                                           |
| ---------- | ---------------------------------------------------------------------------------------------- |
| **F1** P1  | ticker 조회에 `_to_bybit_linear_symbol` 적용 (스팟 → perp)                                     |
| **F2** P2  | mark 는 `info.markPrice` 에서, last 우선순위에서 죽은 `"mark"` 키 제거                         |
| **F3** P1  | `110092` allowlist 추가 + 가드 주석 정정                                                       |
| **F4** P2  | `110017`→`reduce_only_violation`, `110034`→`position_zero`, 잔고 6종·인증/권한 분리            |
| **F5** P1  | retCode 미추출은 `outcome="unknown"` (타임아웃을 "거절" 로 세면 개선치가 오염된다)             |
| **F6** P1  | 전환의 cross-bar 이중 진입 — 원장 억제기(2 bar) + 발주 직전 재확인                             |
| **F7** P1  | 기준가 실패 시 **전환만** 금지, 조건부 등재는 폴백(bar 종가)으로 계속 (사용자 결정)            |
| **F8** P2  | 전환 후 남은 leg 무음 소실 → `deferred_after_market_convert` 카운터                            |
| **F9** P3  | idempotency key 길이 경계를 긴 쪽(`condmkt`) 기준으로 통일                                     |
| **F10** P3 | guard metric help 에 "결정 축" 명시, planner 독스트링에 합집합 논거, 전환 시 `breach_pct` 기록 |

**기각 1건** — "flip 청산 이중 계상". `market_orders_in_flight`(`live_signal.py:244-246`)가 같은 tick 을 이미 막는다. 재현되지 않음.

### ★평가자가 직접 손댄 줄 — G6 리뷰 범위에 반드시 포함

1. `backend/tests/tasks/test_live_signal_conditional_reconcile.py` — `test_fallback_reference_forbids_conversion_even_if_reprobe_would_succeed` 신규. 변이 F7 이 통과한 이유가 **가드 두 겹이 같은 mock 을 써서 서로를 가린 것**이라, 첫 조회만 실패시키고 재확인은 성공시켜 폴백 판정만 남긴다.
2. `backend/src/tasks/live_signal.py` — `interval_seconds` dict 조회를 `[]` → `.get(..., 3600)`. 미지 interval 이 `KeyError` 로 죽으면 아래 `except` 가 삼켜 **전환이 조용히 사라진다**. 과잉 억제가 안전한 방향이다.

### 변이 결과 (누적)

| 회차 | 변이                   | 결과                                                                                                   |
| ---- | ---------------------- | ------------------------------------------------------------------------------------------------------ |
| W1   | M1~M4, M3b             | 5/5 검출                                                                                               |
| W2   | M5~M11, M13, M14, M15b | 10/10 검출 (M15 1차는 **오조준** — 취소 루프 뒤에 넣어 `return` 과 `to_place=()` 가 동치인 지점이었다) |
| W3   | M12, M16               | 2/2 검출                                                                                               |
| W5   | F1~F4, F7b             | 5/5 검출                                                                                               |
| W5   | F7                     | 1차 **탈출** → 게이트 테스트 추가 후 검출                                                              |

★**교훈 — 변이가 두 구현이 동치인 지점에 떨어지면 아무것도 증명하지 못한다.** 탈출을 보고 "테스트가 약하다" 로 바로 가면 멀쩡한 게이트를 오판한다. **변이가 실제로 무엇을 바꿨는지 먼저 확인해라.**

## 2. 작업 순서 — **계측이 먼저다**

before/after 를 같은 자로 재려면 측정 도구가 수정보다 먼저 들어가야 한다.

| 순서 | 워크스트림                         | codex 세션 |
| ---- | ---------------------------------- | ---------- |
| 1    | **W1 — BL-512 계측**               | 1세션      |
| 2    | **W2 — BL-511 진입 전환**          | 1세션      |
| 3    | **W3 — `fill_timing` 라이브 배선** | 1세션      |

---

## 3. W1 — 거래소 응답 계측 (BL-512)

### 수용 기준

- **W1-1** `qb_exchange_order_response_total{exchange, outcome, reason}` 신설 (`common/metrics.py`). `reason` 은 저-카디널리티 정규화 — Bybit retCode allowlist + `other` 버킷.
  ★**최종 계약(W5 반영, codex G6 #6 로 정정)** — `outcome` ∈ `accepted | rejected | **unknown**` (3). `reason` = `trigger_breached · reduce_only_violation · position_zero · insufficient_balance · auth_failed · permission_denied · rate_limited · other · unparsed · rejected_at_submission · filled · submitted` (12). 상한 = exchange(≤4) x 3 x 12 = **144 series**. 초안의 "outcome 2 / reason 8" 은 W5 이전 값이다.
- **W1-2** inc 지점 **4곳** (`tasks/trading.py`):
  - `ProviderError` 거절 경로 (`:403-419`) → `outcome="rejected"`, reason = retCode 매핑
  - `receipt.status == "rejected"` (`:508-529`) → `outcome="rejected"`, `reason="rejected_at_submission"`
  - `receipt.status == "filled"` (`:433-460`) → `outcome="accepted"`, `reason="filled"`
  - ★**`receipt.status == "submitted"` (`:531-551`) → `outcome="accepted"`, `reason="submitted"`** — **이 경로를 빼면 안 된다.** 거래소가 수락했지만 아직 체결 전인 상태이고, **조건부 진입이 정상 등재되면 전부 이 경로**다(`attach_exchange_order_id` + watchdog enqueue). 여기를 놓치면 "수락" 카운터가 사실상 0 이 되어 보존 관계를 못 잰다
- **W1-3** `reason` 정규화 함수는 **retCode 를 문자열에서 추출**한다. `110093 → trigger_breached`, `110017 → position_zero`, 잔고부족 → `insufficient_balance`, 권한 → `permission_denied`, 그 외 → `other`. 선례 = `_normalize_error_class`(`metrics.py:139-187`).
- **W1-4** `qb_live_conditional_guard_total{outcome}` 신설. 허용 집합 밖 라벨을 거부하는 테스트를 함께 넣어라.
  ★**최종 계약(W5 반영, codex G6 #6 로 정정)** — `outcome` ∈ `conditional_placed | market_converted | breach_capped | breach_with_resting | reference_unavailable | **convert_suppressed** | **breach_reverted**` (**7개**). 초안의 4개 → G1 #11 로 5개 → W5 의 이중 진입 억제기·재확인으로 7개가 됐다.
  ★**이 목록이 세 번 어긋났다.** 문서의 라벨 집합은 코드와 갈라지기 쉬우므로, 권위는 `common/metrics.py` 의 `_LIVE_CONDITIONAL_GUARD_OUTCOMES` 이고 이 문서는 그 사본이다.
- **W1-5** ★**정상 체결이 error 카운터를 올리는 것을 멈춘다.** `live_signal.py:407-409` — `probe.status == "filled"` 인데 `stage="exchange_missing"` 을 무조건 `.inc()` 한다. 체결 확인 시에는 올리지 않는다.

### red → green 테스트

| 파일                                                                | 테스트                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/tests/tasks/test_exchange_order_response_metric.py` (신규) | `test_provider_error_rejection_increments_with_reason` · `test_110093_maps_to_trigger_breached_reason` · `test_unknown_retcode_falls_back_to_other` · `test_successful_fill_increments_accepted` · `test_rejected_at_submission_increments` |
| `backend/tests/tasks/test_live_signal_conditional_reconcile.py`     | `test_confirmed_fill_does_not_increment_exchange_missing` (신규)                                                                                                                                                                            |

패턴은 `tests/trading/test_order_rejected_metric.py` 의 before/after delta(`counter._value.get()`) 를 그대로 쓴다.

### 판별력 증명 — 실거래소 원문 픽스처 (외부 오라클)

우리 원장에서 뽑은 **실제 Bybit 응답 3종**이다. `reason` 정규화 테스트는 이 문자열을 그대로 입력으로 쓴다 — 우리가 지어낸 문자열로 우리 파서를 검증하면 circular oracle 이다.

```text
provider_failure: InvalidOrder: bybit {"retCode":110093,"retMsg":"expect Falling, but trigger_price[633023000] >= current[632859000]??LastPrice","result":{},"retExtInfo":{},"time":1785212835243}
provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"current position is zero, cannot fix reduce-only order qty","result":{},"retExtInfo":{},"time":1785035422319}
provider_failure: PermissionDenied: bybit {"retCode":10005,"retMsg":"Invalid API-key, IP, or permissions for action.","result":{},"retExtInfo":{},"time":1785034847821}
```

★★ **이 세 줄이 BL-512 의 존재 이유를 증명한다** — 앞의 둘은 **ccxt 예외 클래스가 똑같이 `InvalidOrder`** 다. 즉 기존 `qb_ccxt_request_errors_total{error_class="InvalidOrder"}` 는 "트리거 방향 오류" 와 "포지션이 이미 0" 을 **같은 버킷**에 넣는다. **정규화는 예외 클래스가 아니라 `retCode` 를 봐야 한다.**

★ 파싱 주의 — `retMsg` 에 `>`(escaped `>`) 와 `??LastPrice` 같은 깨진 구분자가 들어 있다. **`retMsg` 를 파싱하지 말고 `retCode` 숫자만 뽑아라.**

---

## 4. W2 — 진입 패리티 (BL-511)

### 수용 기준

- **W2-1** 가드 기준가 = **거래소 실시간 last price**. `trigger_by="LastPrice"` 와 같은 자여야 한다. `fetch_mark_price` 는 `mark` 우선이라 **그대로 쓰지 않는다** — last 우선 조회 경로를 만든다(`providers.py:1756-1803` 본문 공유, 키 우선순위 인자화).
- **W2-2** ★**조회 위치.** `_reconcile_conditional_entries` 의 **조기 return(`live_signal.py:283-284`) 이후**에 조회한다. stop-entry 를 안 쓰는 전략이 REST 비용을 물면 안 된다. 현재 `_last_close_or_none(df)` 는 호출부(`:1346-1356`)에서 모든 세션에 대해 계산되고 있다.
- **W2-3** 돌파 판정 시 = **시장가 전환**. `PlannedConditionalEntry` 에 전환 표식을 더하고, 발주 시 `trigger_price=None, trigger_direction=None, trigger_by=None` 인 `OrderRequest` 를 만든다(`live_signal.py:617-631`).
- **W2-3a** ★**전환은 `matching_actual` 이 빈 경우로 한정**한다(R2b). resting 조건부가 있는데 돌파면 **기존 동작(취소 + 등재 생략)을 유지**하고 `qb_live_conditional_guard_total{outcome="breach_with_resting"}` 로 **계측만** 한다. 이 스프린트에서 그 경로의 동작은 바꾸지 않는다.
- **W2-3b** ★**전환 주문의 idempotency key 는 별도 네임스페이스**를 쓴다(R1b). 조건부는 `live:{sid}:cond:...`, 전환은 `live:{sid}:condmkt:...`. 같은 키를 재사용하면 **거래소로 dispatch 되지 않고 캐시 응답이 돌아온다.** 키 길이 200자 상한(`_IDEMPOTENCY_KEY_MAX_LENGTH`) 검사는 그대로 태운다. `parse_conditional_entry_key` 는 `cond` 만 인식하므로 전환 주문이 resting 조건부로 오인되지 않는다 — **이 성질을 테스트로 못박는다.**
- **W2-4** ★**전환 후 그 tick 의 나머지 등재를 중단**한다(R1).
- **W2-5** (W2-3a 로 대체 — 전환 경로에는 취소가 없다.)
- **W2-6** **사용자 상한** — `StrategySettings.max_trigger_breach_pct: float | None = None`(**None = 무제한 = 기본값**). 돌파폭 `abs(reference - stop) / reference * 100` 이 상한 초과면 전환하지 않고 divergence `breach_exceeds_cap` + `qb_live_conditional_guard_total{outcome="breach_capped"}`.
  - ★**타입 결정**(codex G1 #9) — API/설정 필드는 **`float` 을 유지**한다. 바로 옆 `position_size_pct` 가 이미 `float` 이고(`schemas.py:119`) 한 모델 안에서 타입을 섞는 것이 더 나쁘다. **대신 planner 경계에서 `Decimal(str(value))` 로 변환**한다 — CLAUDE.md 가 지정한 바로 그 패턴이다(float 공간 연산 후 변환 금지). 돌파폭 비교는 **전부 `Decimal` 공간**에서 한다.
  - ★`None`(무제한)과 `0`을 구분해라. `0` 은 입력 자체를 거부한다(`gt=0`).
- **W2-7** **기준가 조회 실패 = fail-closed.** ★**`to_place` 를 비우는 방식이어야 한다. 함수를 조기 `return` 하면 안 된다**(R4) — kill switch·세션 비활성·stand-down 의 취소 경로가 함께 죽어 위험한 주문이 거래소에 남는다. divergence `reference_price_unavailable` + 카운터.
- **W2-8** `UpdateStrategySettingsRequest` 미러 + FE 스키마·폼 반영. **PUT = 전체 치환** 계약을 문서화한다. FE 빈 입력은 `NaN` 이 아니라 `null` 로 보낸다.
- **W2-9** 전환 주문은 notional 가드에서 `mark * 1.02` 로 평가된다(R3). 경계에서 조건부는 통과하고 전환은 거부되는 케이스를 **테스트로 고정**한다. `_validate_position_size` 가 전환 주문에서 skip 되는 것도 주석으로 못박는다.

- **W2-10** ★**유실 채널을 구분해서 센다**(G1-A). 지금은 발주 루프의 모든 실패가 `stage="place"` 한 버킷에 들어간다(`live_signal.py:651-656`). 전환 주문의 실패와 조건부 주문의 실패를 **구분**하고, 사전 게이트 거부(`NotionalExceeded`/`MinNotionalNotMet`/`BalanceUnverified`)를 일반 예외와 **구분**해라. 그래야 soak 후에 "무엇이 얼마나 유실됐는가" 를 물을 수 있다. **고치는 게 아니라 보이게 하는 것이 이번 범위다.**

### ★W2 구현 형태 — 가드에서 `continue` 하지 말고 **플래그로 흘려보내라**

현재 가드(`:187-202`)는 `continue` 로 루프를 빠져나간다. 전환을 **그 자리에서 발행하면 안 된다** — 아래 안전장치들을 전부 건너뛰기 때문이다.

| 가드 이후에 있는 것               | 위치       | 건너뛰면 생기는 일                               |
| --------------------------------- | ---------- | ------------------------------------------------ |
| 거래소 눈금 미만 목표 차단        | `:210-222` | 화면엔 "대기 중" 인데 주문은 안 나가는 "되는 척" |
| 수량 0 = no-op + resting 걷어내기 | `:224-246` | 거래소만 목표를 넘어간다                         |
| **side 불일치 차단**              | `:248-263` | 방향이 뒤집힌 실주문                             |

**요구 형태:**

1. 가드는 `breached` 여부만 계산한다.
2. `breached` **and** `matching_actual` 이 **비어 있지 않다** → 기존 동작 유지(divergence + `to_cancel` + `continue`) + `qb_live_conditional_guard_total{outcome="breach_with_resting"}`.
3. `breached` **and** `matching_actual` 이 **비어 있다** → 상한 검사. 초과면 divergence `breach_exceeds_cap` + `continue`. 통과면 **`convert_to_market = True` 로 두고 그대로 아래로 흘려보낸다.**
4. `PlannedConditionalEntry` 생성 지점(`:265-273`)에서 그 플래그를 실어 보낸다.
5. `matching_actual` 이 비어 있으므로 `:274-277`(`len(matching_actual) != 1`) 분기를 그대로 타서 **취소 0건 + 등재 1건**이 된다. 새 분기를 만들 필요가 없다.

★ 이 형태의 이점 — 전환 주문이 **기존 안전 검사 전부를 통과한 뒤에만** 만들어진다. 변이 M14 가 검증하는 것이 정확히 이 성질이다.

### red → green 테스트

| 파일                                                            | 테스트                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/tests/trading/test_conditional_entry_planner.py`       | `test_breached_trigger_without_resting_converts_to_market` · **`test_breached_trigger_with_resting_cancels_and_does_not_convert`**(W2-3a) · `test_breach_within_cap_still_converts` · `test_breach_exceeding_cap_is_not_placed` · `test_cap_none_means_unlimited` · **음성** `test_reachable_trigger_still_places_conditional`(기존 유지)                                                                                                                       |
| `backend/tests/tasks/test_live_signal_conditional_reconcile.py` | `test_reference_price_comes_from_exchange_last_not_bar_close` · **`test_reference_price_failure_still_runs_cancels`**(W2-7/R4) · `test_market_conversion_stops_further_placements_in_tick` · `test_converted_order_has_no_trigger_fields` · **`test_converted_order_uses_distinct_idempotency_namespace`**(W2-3b) · **`test_converted_key_is_not_parsed_as_resting_conditional`** · `test_reference_price_not_fetched_when_no_conditional_work`(W2-2 비용 회귀) |
| `backend/tests/trading/test_service_orders_notional.py`         | **`test_converted_market_entry_uses_mark_buffer_not_trigger_price`**(W2-9 경계)                                                                                                                                                                                                                                                                                                                                                                                 |
| `backend/tests/trading/test_provider_last_price.py` (신규)      | `test_last_price_prefers_last_over_mark` · `test_last_price_returns_none_on_provider_error`                                                                                                                                                                                                                                                                                                                                                                     |
| `backend/tests/strategy/test_strategy_settings.py`              | `test_max_trigger_breach_pct_defaults_to_none` · `test_legacy_settings_without_new_fields_still_parse` · `test_update_request_mirrors_settings_fields`                                                                                                                                                                                                                                                                                                          |

### 외부 오라클

- 거절 메시지 자체가 오라클이다 — `retMsg` 가 `trigger_price[...]` 와 `current[...]` 를 **둘 다** 싣는다. 전환 판정이 옳았는지 그 두 값으로 사후 대조한다.
- 전환 체결가는 Bybit `/v5/execution/list` 로 **독립 조회**해 의도 트리거가와의 차이를 3중 대조(손계산 = DB = 거래소)한다.

---

## 5. W3 — `fill_timing` 라이브 배선

### 수용 기준

- **W3-1** `run_live`(`event_loop.py:315-325`)에 `fill_timing` 인자 추가 → `run_historical` 전달. 기본값은 현재 동작인 `"bar_close"`.
- **W3-2** `StrategySettings.fill_timing: Literal["bar_close","next_bar_open"] = "bar_close"` 추가 → 라이브 평가에서 `run_live` 로 배선.
- ~~**W3-3** Track A + `next_bar_open` 계측~~ — ★**폐기**(codex G1 #7, 재현 확인). 그 경로는 **라이브에 존재하지 않는다** — `run_live` 는 `run_historical` 만 부르고(`event_loop.py:380`), Track A 경고가 있는 `run_virtual_strategy` 는 `TrackRunner._dispatch_table["A"]` 로만 도달한다(`track_runner.py:43-46`). 즉 라이브는 Track A 를 그 경로로 실행하지 않는다. **없는 경로에 계측을 붙이면 영원히 0 인 카운터가 남는다.** 대신 "라이브가 Track A 를 어떻게 다루는가" 를 별건 BL 로 등재한다.
- **W3-4** ★**SSOT 충돌 표면화.** 라이브 설정이 SSOT 이고, 백테스트 폼의 `fill_timing` 이 전략 라이브 설정과 다르면 **경고 배지**를 띄운다(기존 mirror 배지 패턴 재사용, `live-settings-mirror.test.tsx` 에 케이스 추가).
- **W3-5** 문서에 **`next_bar_open` 은 진입뿐 아니라 청산도 한 bar 늦춘다**는 사실을 명시한다(`interpreter.py:1574,1600` — `close`/`close_all` 도 같은 인텐트 큐).

### red → green 테스트

| 파일                                                                 | 테스트                                                                                                                                           |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `backend/tests/strategy/pine_v2/test_run_live_fill_timing.py` (신규) | `test_next_bar_open_delays_entry_by_exactly_one_bar` · `test_bar_close_is_default_and_unchanged` · `test_next_bar_open_does_not_lose_the_signal` |
| `backend/tests/tasks/test_live_signal_*.py`                          | `test_strategy_settings_fill_timing_reaches_run_live`                                                                                            |

★ **soak 으로는 검증되지 않는다** — PbR 은 `stop=` 진입이라 `fill_timing` 이 적용되지 않는다(`interpreter.py:1527` 이 `stop is None` 일 때만 인텐트 큐로 보낸다). 결정론 픽스처가 유일한 증명이다.

---

## 6. 표적 변이 M1..M12 (구현 전 동결) + 음성 대조 N1..N4

변이·복원은 **문자열 치환 쌍**으로 한다. **`git checkout <file>` 금지** — 이번 스프린트 신규 코드가 함께 날아간다. 마지막에 **복원 확인 실행** 필수.

| ID      | 변이                                                            | 뒤집혀야 할 테스트                                                                                                                                                                   |
| ------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **M1**  | `reason` 정규화에서 `110093` 매핑 제거 → 전부 `other`           | `test_110093_maps_to_trigger_breached_reason`                                                                                                                                        |
| **M2**  | `ProviderError` 경로의 카운터 `.inc()` 삭제                     | `test_provider_error_rejection_increments_with_reason`                                                                                                                               |
| **M3**  | 성공 경로의 `outcome="accepted"` 를 `"rejected"` 로             | `test_successful_fill_increments_accepted`                                                                                                                                           |
| **M4**  | W1-5 수정을 되돌려 체결에도 `exchange_missing` 을 올림          | `test_confirmed_fill_does_not_increment_exchange_missing`                                                                                                                            |
| **M5**  | 기준가 조회를 다시 `_last_close_or_none(df)` 로                 | `test_reference_price_comes_from_exchange_last_not_bar_close`                                                                                                                        |
| **M6**  | last 우선 조회의 키 순서를 `("mark","last")` 로 되돌림          | `test_last_price_prefers_last_over_mark`                                                                                                                                             |
| **M7**  | 전환 시 `trigger_price` 를 그대로 실어 보냄                     | `test_converted_order_has_no_trigger_fields`                                                                                                                                         |
| **M8**  | 전환 후 `return` 제거 → 같은 tick 에 계속 등재                  | `test_market_conversion_stops_further_placements_in_tick` — ★**픽스처가 독립 전환 후보를 2건 이상 담아야 한다.** 1건이면 `return` 유무가 결과를 안 바꿔 변이가 통과한다(codex G1 #8) |
| **M9**  | 상한 비교를 `>` → `>=` 로 (경계 오프바이원)                     | `test_breach_within_cap_still_converts` — ★**픽스처의 돌파폭이 상한과 정확히 같아야 한다**(예: cap `0.05`, 돌파폭 `0.05`). 같지 않으면 `>`/`>=` 가 구분되지 않는다(codex G1 #8)      |
| **M10** | 상한 `None` 을 0 으로 취급 → 전건 차단                          | `test_cap_none_means_unlimited`                                                                                                                                                      |
| **M11** | 기준가 `None` 일 때 fail-open(그냥 등재)                        | `test_reference_price_failure_still_runs_cancels` 의 등재 단언                                                                                                                       |
| **M12** | `run_live` 가 `fill_timing` 을 받되 `run_historical` 에 안 넘김 | `test_next_bar_open_delays_entry_by_exactly_one_bar`                                                                                                                                 |
| **M13** | 전환 키를 조건부와 **같은** 네임스페이스로 되돌림               | `test_converted_order_uses_distinct_idempotency_namespace`                                                                                                                           |
| **M14** | `matching_actual` 이 있어도 전환하도록 조건 제거                | `test_breached_trigger_with_resting_cancels_and_does_not_convert`                                                                                                                    |
| **M15** | 기준가 실패를 **조기 `return`** 으로 구현                       | `test_reference_price_failure_still_runs_cancels`                                                                                                                                    |

### 음성 대조 (green 을 유지해야 한다 — 과잉차단 배제)

| ID     | 상태                                        | 기대                               |
| ------ | ------------------------------------------- | ---------------------------------- |
| **N1** | 트리거가 도달 가능(정상 방향)               | 조건부 그대로 등재, 전환 0         |
| **N2** | `desired` 와 `local_orders` 모두 비어 있음  | **REST 조회 0회** (W2-2 비용 회귀) |
| **N3** | 레거시 `strategy.settings` (신규 필드 없음) | 파싱 성공 + 기본값                 |
| **N4** | `fill_timing` 미지정                        | `bar_close` 로 기존과 동일 동작    |

★ **STOP 조건** — 변이가 아무 테스트도 뒤집지 못하면 그건 게이트가 아니다. 승인하지 말고 이 문서로 되돌아온다.

---

## 6.5 before 원장 스냅샷 (동결 — soak 대조 기준선)

`2026-07-28 05:53:18 UTC` 실측. 이 시각 이후에 생긴 조건부 주문만 after 다.

| 항목                    | 값                                             |
| ----------------------- | ---------------------------------------------- |
| 조건부 주문 누적        | **67** (filled 7 · rejected 29 · cancelled 31) |
| `110093` 누적           | **29** (= rejected 전건)                       |
| **거절률**              | **43.3%** (29/67)                              |
| 마지막 조건부 주문      | `2026-07-28 04:27:13 UTC`                      |
| soak 창 한정(직전 세션) | 38건 중 거절 19 = **50%**                      |

after 집계 SQL:

```sql
SELECT state, count(*), count(*) FILTER (WHERE error_message LIKE '%110093%') AS e110093
FROM trading.orders
WHERE trigger_price IS NOT NULL AND created_at > TIMESTAMPTZ '2026-07-28 05:53:18+00'
GROUP BY state ORDER BY state;
```

★★ **보존 관계는 원장으로 잰다 — guard 카운터로 재지 마라**(codex G1 #10, 재현 확인). `market_converted` 는 **결정 시점** 카운터다. 실제 발주는 DB commit 뒤 **별도 Celery 프로세스**에서 일어나고(`order_service.py:422-434`) 그 뒤에도 `ProviderError` 로 거절될 수 있다(`tasks/trading.py:403-420`). 결정을 성공으로 읽으면 **"고쳤다" 를 스스로 증명하는 순환 오라클**이 된다.

원장 기준 판정 — 전환 주문은 `trigger_price IS NULL` + `idempotency_key LIKE 'live:%:condmkt:%'` 로 식별한다:

```sql
-- 조건부 (트리거 발주)
SELECT 'conditional' AS kind, state, count(*),
       count(*) FILTER (WHERE error_message LIKE '%110093%') AS e110093
FROM trading.orders
WHERE trigger_price IS NOT NULL AND created_at > TIMESTAMPTZ '2026-07-28 05:53:18+00'
GROUP BY 1,2
UNION ALL
-- 전환 (시장가 발주)
SELECT 'converted', state, count(*), 0
FROM trading.orders
WHERE idempotency_key LIKE 'live:%:condmkt:%' AND created_at > TIMESTAMPTZ '2026-07-28 05:53:18+00'
GROUP BY 1,2;
```

**성공 = 조건부 거절이 유의하게 줄고, 그 감소분이 전환 주문의 `filled`(거절 아님)로 나타난다.** 전환이 늘었는데 그것도 거절이면 고친 게 아니다.
★ **유실 채널도 함께 읽는다**(R7) — `qb_live_conditional_reconcile_errors_total{stage="deferred_market_inflight"}`.

★★ **metric 은 before/after 대조가 불가능하다.** `2026-07-28 05:53 UTC` 실측 — `/metrics` 에 노출된 조건부 계열은 `qb_live_conditional_sweep_filled_total` **하나뿐**이고 `qb_ccxt_request_errors_total{error_class="InvalidOrder"}` 도 **없다**. 직전 soak 이후 multiproc 디렉터리가 비워졌기 때문이다(`make be-isolated` 가 전체 스택 기동 시 wipe). 따라서 **before 의 권위는 원장(DB)뿐**이고, metric 은 (a) 실거래소 원문 픽스처 단위 테스트로 파서 판별력을 증명하고 (b) after soak 에서 절대값을 읽는 용도다. **"metric 이 줄었다" 를 근거로 쓰지 마라.**

## 7. 게이트 baseline (2026-07-28 실측)

BE **3277** / FE **1182** / e2e authed **65** · canon **32** · CI전용 **4** / ruff·mypy(209)·tsc·eslint 0 / 마이그레이션 **0**.

```bash
cd backend && set -a; source .env.local; set +a; uv run pytest -q   # 3-env 통째 소싱 필수
cd frontend && pnpm test                                           # --run 금지
PLAYWRIGHT_BASE_URL=http://localhost:3100 pnpm e2e:authed          # 3000 은 남의 앱(Nexus)
```

## 8. codex 태스크 스펙 고정 문구

- _"DB 의존 테스트는 평가자가 돌린다. 네 샌드박스는 `localhost:5433` 에 접속 못 한다. **돌리지 못한 것을 통과했다고 쓰지 마라.**"_
- _"스펙 밖 리팩토링 금지. 부수 정합성 수정(기존 테스트 시그니처 조정 등)은 승인된 것으로 간주한다."_
- _"`.ai/rules/` 레이어 규칙 준수 — Repository-only DB 접근 · 금융 숫자 `Decimal` · Celery prefork-safe(모듈 import 시점 무거운 객체 생성 금지)."_
- _"`docs/reference/gates-and-traps.md` 를 읽어라. 특히 RUF003(주석의 `×`·`−` 금지) 과 `Order.idempotency_key` VARCHAR(200) 상한."_
