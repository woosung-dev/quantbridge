# 트레일링 live-placement — 결정 기록 (STEP B)

> **2026-06-26.** 데모-우선 라이브 손익보호의 마지막 기능 갭 = 트레일링 live-placement. Phase 3(PR #364, `main @e2ff6c2`)가 라이브 exit-level surfacing + maker bracket 까지 실증 → 트레일링만 잔존(param 배선됨, placement 미구현, 가드만 존재). 본 문서 = 코드 기준 결정 기록(2차 deepen audit `2026-06-26-trading-deepen-2.md` 와 한 세션).

## 핵심 결정과 근거

### 1. 트레일링 = 별도 주문이 아니라 **포지션 속성** → trading-stop 엔드포인트

ccxt 4.5.49 가 `trailingStop`/`trailingAmount` param 이 붙은 `create_order` 를 Bybit **`privatePostV5PositionTradingStop`** 엔드포인트로 라우팅한다(`bybit.py:3892` `isTrailingOrder`, `:3898-3899` route). 그 분기는 `side`/`qty` 를 드롭(`:4100-4101`)하고 `request['trailingStop']`(+옵션 `activePrice`)만 전송 — whole-position, 방향은 Bybit 가 포지션에서 추론. 따라서 entry create_order 에 trailingStop 을 실으면 entry 자체가 trading-stop 호출로 변질되어 깨지고, SL 동반 시 `bybit.py:3987-3989` `InvalidOrder` hard-reject. → **트레일링은 포지션 open 후 별도 호출.**

### 2. 왜 post-fill Celery follow-on 인가 (동기 인라인/full-OrderService 가 아니라)

- 시장가 entry 도 Bybit demo 가 `"open"`/WaitForFill 로 줄 수 있음(`tasks/trading.py:354-360`) → **동기 인라인만으론 보호 공백**(money-path hole). 그래서 **fill-transition** 을 트리거로 사용.
- fill-transition 은 3 경로(동기 `tasks/trading.py` / WS `state_handler.py` / watchdog `tasks/trading.py`). 전부 **winner-only**(`order_repository` `transition_to_filled` 가 `state==submitted` rowcount==1) → 정확히 1곳만 enqueue = **구조적 dedup(멱등 컬럼 불필요 → 마이그레이션 0)**.
- full `OrderService.execute` 재사용 거부 — 보호 trailing 은 risk-reducing 인데 kill-switch 가 차단하면 포지션 무방비. position-attribute 를 fill-able 주문처럼 다루는 impedance mismatch. → **전용 task + 직접 `provider.set_trading_stop`** (kill-switch/risk 우회).

### 3. triggerDirection 불필요 (사실 — 조건부 아님)

native trailing 은 trading-stop 엔드포인트(position-inferred)라 방향 미산정 필요. ccxt `bybit.py:4106-4116` 의 `triggerDirection` 요구 분기(`elif isTriggerOrder and not endpointIsTradingStop`)는 trailing 에선 **미도달**. → `exit_order_mapping.trigger_direction_for`(BL-365)는 **트레일링에 미소비, deferred 확정**. `set_trading_stop` 은 triggerDirection 미전송. 또한 `reduceOnly`/`triggerBy` 는 이 엔드포인트 no-op → speculative 미전송(데모 round-trip 으로 실제 수용 shape 확정).

### 4. entry-injection 차단 (COUPLED)

(a) `live_signal.py` dispatch 가 entry 의 `event.trailing_stop` 를 `Order.trailing_stop` 에 영속(follow-on 이 읽음) + (b) `tasks/trading.py` 가 entry(`reduce_only=False`) OrderSubmit 의 trailing 을 `None` 으로(create_order 미주입) + (c) `_merge_exit_params` 가 `trailingStop` 을 `reduce_only` 일 때만 emit(defense-in-depth). (a) 없이 (b) = 영속 안 됨, (b) 없이 (a) = entry 깨짐. 회귀 테스트로 "entry create_order params 에 trailingStop 부재" 불변식 고정.

### 5. 실패 = loud(침묵 금지) + stale-position 가드

- `place_trailing_stop_task` 실패 분류: **110017/position-zero/flat = benign**(log+metric, no-retry, no-alert) / **network·exchange = 포지션 무방비 → bounded Celery retry(3×) + 최종 실패 시 critical alert**. 침묵 시 무방비 포지션이 신호 없이 방치 = money-path hole.
- **stale-position 가드**: placement 전 `fetch_position` → size>0 + side 가 entry 포지션 방향과 일치할 때만. 체결→placement 사이 close+reopen flip 시 stale task 가 신규 포지션에 오부착하는 것 차단.

### 6. 가드 단계적 해제

`live_signal.py:689-699` 가드는 유지 — `trailing + SL 없음`(무방비 윈도) entry 는 여전히 거부(stage 2). `trailing + SL` 은 허용(SL bracket 이 fill→placement 윈도 보호) + 영속.

## 검증

- 단위/회귀 TDD: `set_trading_stop`/`fetch_position` param shape + entry-injection 불변식 + place_trailing_stop 6 케이스(happy long/short, position flat/flip/zero benign, network raise) + 3-enqueue helper gating + FE tpsl-cell 렌더. BE trading+tasks 563 pass / ruff·mypy(184) clean / FE 59 pass.
- 3-평가자 사전 plan review + 구현 후 재게이트(codex + 빈컨텍스트 Opus 2).
- 데모 round-trip D-script `scripts/verify_trailing_live_placement.py` — **독립 fetch_positions** PRE/ACT/POST 로 false-PASS 차단(미부착/거리 10x/SL clobber/flip/shrink). selftest 9/9. 실 Bybit demo 발주는 사용자 키 보유 시 직접 실행.

## 잔여 / deferred

- BL-365 `trigger_direction_for` 배선 — 서버 standalone-trigger 발주 시점까지(트레일링 미소비).
- OCO-on-fill sibling-cancel(Phase 3 이연 유지).
- 실자금 cutover(Wave 3) — 범위 밖.
