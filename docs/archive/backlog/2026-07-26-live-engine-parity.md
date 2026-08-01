# 2026-07-26 — Live-engine-parity 완료 BL 상세

> **보관 이유:** `BL-481/482/483/486/487`은 같은 `feat/live-engine-parity` 결과로 해소됐다. live ledger에는 ID·우선순위·결과·근거만 남기고, 문제 재검토에 필요한 원인과 당시 권장 접근은 이 문서에 보존한다.
>
> **스프린트 회고:** [`2026-07-26-live-engine-parity.md`](../../dev-log/2026-07-26-live-engine-parity.md)
> **현재 ledger:** [`backlog.md`](../../backlog.md)

---

## BL-481

**Title:** `sessions_allowed` 가 라이브에 미배선 — 거래 시간대를 제한해도 라이브는 24 시간 진입한다
**Category:** Backend / trading (라이브 게이팅 parity)
**Priority:** P2
**Trigger:** 세션 시간대 제한을 실제로 쓰는 사용자 등장 시
**Est:** S
**출처:** 2026-07-26 live-entry-wiring (BL-479 배선 중 발견)

**원인 / 영향:** 백테스트는 `cfg.trading_sessions → compat.parse_and_run_v2(sessions_allowed=...) → run_historical` 로 entry placement 와 pending fill 양쪽에 게이트를 건다(`compat.py:75`, `event_loop.py:72`). `run_live` 는 그 인자를 넘기지 않으므로 `run_historical` 기본값 `()` 가 적용돼 **24 시간 무제한**이다.

`Strategy.trading_sessions` 컬럼은 존재하고 백테스트는 존중한다. 즉 같은 전략이 백테스트에서는 아시아 세션만 거래하는데 라이브에서는 밤새 진입한다.

BL-188 v3 가 "Live `is_allowed` 와 단일 reference 정합" 을 목표로 했는데 라이브 쪽이 비어 있다.

**권장 접근:** `run_live` 에 `sessions_allowed` 를 추가하고 `live_signal.py` 가 `strategy.trading_sessions` 를 넘긴다. 단 `sessions_allowed` 가 비어 있지 않으면 OHLCV 인덱스가 tz-aware 여야 하므로(`event_loop.py:90-92`) 라이브 DataFrame 구성이 그 조건을 만족하는지 먼저 실측할 것. 회귀 = 허용 세션 밖 bar 에서 진입이 **안 나가는지**와 안 밖 양쪽 단정.

**Risk:** 🟡 (사용자가 명시한 제약을 라이브가 무시한다)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

## BL-482

**Title:** `pyramiding` cap 이 라이브에 미배선 — 같은 전략이 백테스트는 cap, 라이브는 무제한 중첩
**Category:** Backend / trading (라이브 게이팅 parity)
**Priority:** P3
**Trigger:** BL-478 (a) 로 진입이 실제로 열린 뒤
**Est:** S
**출처:** 2026-07-26 live-entry-wiring (BL-479 배선 중 발견)

**원인 / 영향:** `compat.py:101` 이 `strategy(pyramiding=N)` 을 추출해 `run_historical` 로 넘기지만 `run_live` 는 안 넘긴다 → `pyramiding=None` = cap 무효(`event_loop.py:115` 주석이 "None 시 무효" 를 명시).

지금은 진입 자체가 드물어 노출이 적지만, BL-478 (a) 로 조건부 진입이 열리면 같은 방향 포지션이 백테스트가 허용한 것보다 많이 쌓일 수 있다.

**권장 접근:** BL-481 과 같은 배선. `extract_content(source).declaration.pyramiding` 을 `run_live` 로 전달. BL-481 과 한 PR 로 묶는 게 자연스럽다.

**Risk:** 🟢 (진입이 열리기 전까지는 도달 불가)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

## BL-483

**Title:** `leverage` 가 라이브 엔진에 미배선 — 증거금 게이트와 청산가 모델이 L=1 로 no-op
**Category:** Backend / trading (라이브 리스크 게이트)
**Priority:** **P1**
**Trigger:** BL-479 머지 직후 (사이징이 켜지는 순간 증거금 판정이 유의미해진다)
**Est:** M
**출처:** 2026-07-26 live-entry-wiring (BL-479 배선 중 발견)

**원인 / 영향:** `StrategySettings.leverage`(1~125)는 `OrderRequest.leverage`(`live_signal.py:931` 근처)로만 흐르고 `configure_sizing(leverage=...)` 에는 안 들어간다. 그래서 라이브 엔진에서 `is_leverage_active(1.0)` 이 False → `_can_afford_entry` 격리증거금 게이트(`strategy_state.py:374`)와 청산가 모델(BL-186a / BL-480 계열)이 **통째로 no-op** 이다.

결과: **백테스트가 증거금 부족으로 거부할 진입을 라이브는 통과시킨다.**

★**그냥 넘기면 안 된다.** 넘기는 순간 그 게이트가 켜지는데, 증거금 부족 시 진입이 `warnings` 만 남기고 **조용히 skip** 된다. `warnings` 는 divergence 를 트리거하지 않으므로 완전 무음이다. BL-479 가 스코프에서 뺀 이유가 이것이고, 배선하려면 **skip 을 표면화하는 경로를 같이 만들어야 한다.**

**권장 접근:** (1) `run_live` 에 `leverage` 전달 (2) `_can_afford_entry` skip 을 `warnings` 가 아니라 관측 가능한 신호로 승격 — preflight 카테고리 또는 `qb_live_signal_skipped_total` reason (3) 회귀 = 증거금 부족 진입이 skip 되고 **그 사실이 화면/메트릭에 보이는지** 양쪽 단정.

**Risk:** 🔴 (백테스트가 거부할 포지션을 라이브가 연다)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

## BL-486

**Title:** 라이브 사이징 equity 가 **300바 롤링 창**에 따라 변한다 — 같은 신호가 볼 때마다 다른 수량
**Category:** Backend / trading (라이브 사이징 정합)
**Priority:** **P1**
**Trigger:** 세션이 warmup 창(1m 기준 5시간)보다 오래 살기 시작할 때. 즉 **지금 바로**
**Est:** M
**출처:** 2026-07-26 live-entry-wiring 최종 codex diff 리뷰 → 실측 재현

**원인 / 영향:** BL-479 가 `initial_capital` 을 배선하면서 `configure_sizing` 이 `running_equity = initial_capital` 로 시작하고, `strategy_state.py:668` 이 청산 손익을 누적한다. 백테스트에서는 이게 정확하다(inception 부터 전부 replay 하므로 누적 = 전체 손익).

**라이브는 warmup replay 라 누적 범위가 300 바 롤링 창이다.** 세션 나이가 창보다 짧으면 창 누적 = 세션 누적이라 정확하지만, 넘어가면 오래된 거래가 창 밖으로 밀리며 **같은 바의 수량이 바뀐다.**

실측 재현 (`tests/strategy/pine_v2/test_run_live_sizing.py::test_run_live_qty_drifts_with_warmup_window_KNOWN_LIMITATION`):

```
같은 마지막 바(종가 65536) · 같은 initial_capital=8192 · 같은 pct=50
  창 안에 청산 1건(+4096)  ->  qty 0.09375
  그 청산이 창 밖          ->  qty 0.0625      (50% 차이)
```

**미배선 시절의 `1.0`(모든 상황에서 틀림)보다는 낫지만 완결이 아니다.** BL-479 는 수량을 자본에 연동시켰고, 이 항목은 그 자본이 무엇이어야 하는지를 정한다.

**권장 접근:** 먼저 **시맨틱 결정**이 필요하다 — 셋 중 하나다.

- (a) **세션 시작 고정** — `running_equity` 를 라이브에서 누적하지 않는다. 결정적이지만 복리가 없고, 오래된 세션은 낡은 잔고로 사이징한다
- (b) **세션 누적** — `initial_capital = 스냅샷 + 창 이전 세션 실현손익`(DB 의 세션 손익을 이미 갖고 있다). 백테스트와 가장 가깝지만 실현손익(실제)과 replay 손익(시뮬)을 섞는다
- (c) **실잔고 추종** — 매 tick 조회. 지연(1.6s/tick)에 더해 실잔고에 이미 반영된 손익을 replay 가 다시 더하는 **이중 계상**이 생긴다 (BL-479 가 이 이유로 기각했다)

권고 = **(b)**. 다만 "실현/시뮬 혼합" 을 화면에 고지해야 한다. 어느 쪽이든 회귀는 위 KNOWN_LIMITATION 테스트를 **뒤집어** 같은 바가 창과 무관하게 같은 수량을 내는지 단정하는 형태가 된다.

**Risk:** 🔴 (주문 수량이 조용히 변한다. 머니-패스)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

## BL-487

**Title:** `test_get_pool_safe_across_event_loops` 가 `id()` 재사용에 취약 — 전체 스위트에서 random RED
**Category:** Test / 인프라 (flake)
**Priority:** P3
**Trigger:** CI 가 이유 없이 빨개질 때
**Est:** S
**출처:** 2026-07-26 live-entry-wiring 최종 게이트 (전체 스위트 1회 관측, 격리 실행·재실행은 통과)

**원인 / 영향:** `tests/common/test_redis_client.py:44` 가 두 `asyncio.run` 의 pool 인스턴스가 다름을 `assert first != second` 로 단정하는데, `_touch()` 가 **`id(pool)` 만 반환하고 pool 객체 자체는 붙잡지 않는다.** 첫 pool 이 GC 되면 CPython 이 같은 주소를 재사용할 수 있고 그때 `id` 가 같아진다.

즉 테스트가 검증하려는 것("reset 후 새 인스턴스")은 옳지만 **측정 도구가 틀렸다.** 이 스프린트 변경과 무관한 선재 결함이고, `pytest-randomly` 로 실행 순서/할당 패턴이 바뀔 때 드물게 드러난다.

**권장 접근:** `id()` 대신 **객체 참조 자체를 반환해 붙잡고** `assert first is not second` 로 단정한다. 두 객체가 동시에 살아 있으면 주소 재사용이 원천 불가능하다.

**Risk:** 🟢 (테스트 전용. 프로덕션 영향 없음)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)
