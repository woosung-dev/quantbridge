# QuantBridge — TODO

> **Last Updated:** 2026-07-26 (**live-engine-parity** — 라이브 엔진 인자 4종 패리티 종결)
> **Active Sprint:** **live-engine-parity** — 라이브와 백테스트가 같은 진입·사이징 규칙을 쓰게 만든다
> **Active Branch:** `feat/live-engine-parity`
> **요약:** 화면 총계는 원장 SSOT로 일치시켰고, leverage·세션·pyramiding·사이징 equity 경계를 배선했다. D7의 사이징 자본 일시 함몰은 BL-489로 정직하게 남긴다.

## ⚡ live-engine-parity — `run_live` 인자 4종 패리티와 라이브 원장 신뢰 (2026-07-26)

**스코프.** `run_live` 가 `run_historical` 로 넘기지 않던 사이징 equity 기준·`leverage`·`sessions_allowed`·`pyramiding`을 끝내고, 새로 켜지는 게이트가 무음으로 진입을 삼키지 않게 표면화한다.

### ★핵심 발견

- **preflight 가 킥오프 전제 4건을 반박했다.** carry 후보 `live_signal_states.total_realized_pnl` 은 창 스코프·매 tick 덮어쓰기이고, `Σ orders.realized_pnl` 은 거래소 net과 rejected 추정 PnL이 섞여 둘 다 기각됐다. 라이브 OHLCV의 `RangeIndex` + `timestamp` 는 tz 조건을 no-op으로 만들었고, NaN 기준선 단순 비교는 `InvalidOperation` 을 raise한다.
- **★★D7.** 16:12Z의 3건·`5.16879987` 이 16:49Z의 2건·`4.07002377` 이 될 예측은 맞았지만, 이유는 창 밖 청산이 아니었다. 진입이 창 bar 0에서 EMA를 재현하지 못해 청산도 재현되지 않았고 carry에도 안 들어갔다. 화면은 원장 SSOT로 수리했지만 사이징 자본의 일시 함몰은 남는다.
- **leverage 배선은 게이트만 켜지지 않았다.** `check_liquidations` 도 살아나 실제 reduce-only 주문을 낼 수 있는 머니-패스가 됐다. 따라서 청산 표면화와 "격리 증거금 기준" 고지를 같이 넣었다.

### Completed

- [x] **BL-486 ✅ Resolved.** carry는 append-only `live_signal_events`를 `bar_time < window_start`로 자른 합으로 정했다. `sum_realized_pnl_before`는 **사이징 자본 경계**(`initial_capital`), `sum_realized_pnl_all`은 **상태 행 총계**의 원장 SSOT다. 새 close 이벤트만 `equity_curve`에 append한다.
      ★★**정정 — 상태 행은 화면이 아니다.** 최종 리뷰에서 확인했다. `router.py:474-483`(2026-07-01 dogfood)이 `GET /live-sessions/{id}/state` 응답의 `total_realized_pnl`·`total_closed_trades`·`equity_curve` 를 **체결(`state=filled`) 주문으로 재계산해 덮어쓴다**. 즉 화면은 원래부터 창 드리프트를 타지 않았고, 이번 상태 행 수정은 **내부 정합 + `equity_curve` 무한 증식 차단**(분당 1 포인트 → 청산당 1)이다. **사용자에게 보이는 실제 효과는 `initial_capital` carry = 주문 수량**이다. 아래 dogfood 표의 "화면" 은 전부 **상태 행**으로 읽어야 한다.
- [x] **BL-483 ✅ Resolved.** leverage를 라이브 엔진에 전달하고, 진입 skip을 reason별로 마지막 bar만 표면화했다. 라이브 리포트에서 `has_lastbar_skips=t`, `has_liq=t`, `liquidation_count=0` 을 확인했다.
- [x] **BL-481 ✅ Resolved.** `Strategy.trading_sessions`를 전달하고, 값이 있을 때만 `timestamp`로 tz-aware 인덱스를 복원해 세션 밖 진입을 fail-closed로 막는다.
- [x] **BL-482 ✅ Resolved.** 선언 `pyramiding` cap을 전달하고 cap 미만·초과 양방향 회귀를 뒀다.
- [x] **BL-487 ✅ Resolved.** pool 객체 참조를 붙잡아 `id()` 재사용 flake를 `is not` 단정으로 바꿨다.
- [x] **상태 행**과 원장은 17:10Z·17:23Z·19:02Z 에 연속 일치했다(약 1시간 52분). curve는 청산 0건·tick 24회에서 +0, 청산 1건에서 정확히 +1이었다. ★이 값들은 API 가 덮어쓰므로 화면 렌더값이 아니다(위 정정 참조).
- [x] 변이 10종이 전부 적발됐고 매 변이에서 음성 95/96이 GREEN을 유지했다. `MUTANT` 잔존은 0, 복원은 바이트 동일이다.
- [x] **독립 raw HMAC 오라클** — ccxt·`providers.py` 미경유로 `X-BAPI-SIGN` 을 손서명해 `/v5/position/closed-pnl` 직격. 청산 **5건 전부 DB 와 정확히 일치**(불일치 0). 시뮬 `+1.09877350` vs 거래소 `-1.09767393` 의 부호 반전이 외부 진실로 확정됐다.
- [x] 게이트: BE **3102**(+28) · FE **1156**(+5) · **canon 32** · **e2e:authed 65-0** · ruff·mypy·tsc·lint 0 · 마이그레이션 **0**
      ★ canon 은 처음 **27/32** 가 나왔는데 회귀가 아니라 `baseURL` 기본값 3000 을 다른 앱이 점유한 것이었다. `PLAYWRIGHT_BASE_URL=3100` 재실행으로 32. **통과 27건이 거짓 그린이었다는 게 실패 5건보다 무섭다.**

### 신규 BL 4건

- **BL-488 P1.** 평가 갭이 orphan close와 거래소 거부, 시뮬 손익 오염을 만든다.
- **BL-489 P2.** D2 구간에서 사이징 자본이 일시 함몰한다. 화면 총계는 해결됐지만 `initial_capital`은 별도 설계가 필요하다.
- **BL-490 P2.** `margin_mode` 미전달과 isolated 전용 청산 모델 때문에 cross 사용자가 조기 청산될 수 있다.
- **BL-491 P3.** 백테스트 폼이 Live 레버리지를 아직 미러하지 않는다.

### 문서 종결

게이트 운영 지식 6종은 [`reference/gates-and-traps.md`](reference/gates-and-traps.md)에 승격했다. 작업 문서(`checklist.md` · `context-notes.md` · `bl-drafts.md`)는 회고·백로그·정본으로 전부 흡수했고 커밋하지 않았다. **`docs/` 최상위는 10 을 유지한다.** 이력인 아래 `live-entry-wiring` 섹션은 유지한다.

## ⚡ live-entry-wiring — BL-478 (c) 세션 차단 + BL-479 라이브 사이징 (2026-07-26)

**스코프**: 라이브 자동매매는 **진입 주문을 낸 적이 없다.** `strategy.entry(..., stop=)` 는 `PendingOrder` 만 파킹하고 이벤트를 발행하지 않는데(`strategy_state.py:598-609`) 거래소에 그 조건부 주문을 올리는 코드가 없다. 청산만 나가 매번 `110017`. 진입이 열리면 곧바로 수량이 문제가 된다 — `compute_qty()` 가 항상 `1.0`(1 BTC 명목). **기능을 늘리지 않고 거짓말을 멈춘다.**

### ★★사용자 요청 실측이 후보 3 을 반증했다

equity 기준선 후보 3(kill-switch balance provider 재사용)의 **갱신 주기를 먼저 재라**는 지시였고, 답은 "갱신 주기라는 개념이 없다" 였다.

```
account_service.py:126-157  캐시 0줄. TTL·Redis·beat 갱신 태스크 전부 부재
                            매 호출 = DB 2회 + AES 복호화 + ephemeral ccxt -> REST -> close
                            실측 1600ms (BL-476). 독스트링의 "~200ms" 는 8배 낙관
kill_switch.py:106-107      total_pnl >= 0 이면 조기 반환 -> "이미 부르니 공짜" 가 아니다
live_signal.py:873-885      exchange_svc 는 Celery 경계 뒤 dispatch 소속 -> 코드 재사용일 뿐
```

★**지연보다 큰 문제는 시맨틱이었다.** `run_live` 는 warmup replay(300바)라 매 tick 히스토리를 재실행하고 `running_equity` 는 `initial_capital` 에서 시작해 청산 손익을 **다시** 누적한다. 거래소 실잔고는 이미 그 손익이 반영된 값 → **이중 계상**. 300바를 벗어나면 빠지므로 이중 계상량이 시간에 따라 변한다 = 같은 바가 tick 마다 다른 수량. → **세션 시작 1회 스냅샷 + 컬럼 저장**으로 확정(사용자 승인).

★**다만 절반만 닫혔다.** 실잔고 주입에서 오던 이중 계상은 없앴지만 `running_equity` 가 **창 안 청산 손익**을 누적하는 것은 그대로다 → 창이 밀리면 같은 바의 수량이 바뀐다. 최종 codex 리뷰가 잡았고 실측 재현했다(**BL-486**).

### ★탐색이 뒤집은 전제 4건

| 전제                                         | 실측                                                                                                                                                                    |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `s4_hma` 는 명시 `qty=` 라 사이징 **대조군** | ✗ **세 번째 양성.** `capital = strategy.equity` 인데 `running_equity is None` 이면 NaN → BL-376 chokepoint 가 주문을 **skip**. 라이브에서 hma 는 진입 신호가 0 건이었다 |
| 우선순위 사슬을 `compat.py` 에 두고 공유     | ✗ **순환 import** (`compat.py:23` 이 `event_loop` 를 module-level import) → 신규 `sizing.py` 필수                                                                       |
| 잔고 = `fetch_balance_usdt`                  | ✗ 그건 `data["free"]` 만 읽는다. 포지션이 있으면 왜곡 → **`total`** 이 맞다                                                                                             |
| preflight 차단 시 divergence 카운터 inc      | ✗ `common/metrics.py` 의 divergence 카운터 정의 = "0 초과 = 즉시 운영 page". 예상 가능한 사용자 상황은 page 대상 아님                                                   |

### Completed

- [x] **BL-478 (c) Resolved** — `ast_extractor.uses_stop_entry()` 신설(리터럴 `stop=na` 는 인터프리터와 동일하게 제외, 변수 표현식은 보수적 차단). `register()` 가 422 `live_stop_entry_unsupported` 로 거부 + evaluate preflight 가 이미 도는 세션을 자동 종료
- [x] **BL-479 Resolved** — `register()` 가 `AccountBalanceService.get_balance().total` 로 1회 스냅샷 → `live_signal_sessions.equity_baseline_usdt`(`Numeric(18,8)`, nullable) → evaluate 가 `run_live(initial_capital=..., live_position_size_pct=...)` 로 전달. Pine > form > Live 우선순위 사슬이 라이브에서도 성립
- [x] **`pine_v2/sizing.py` 신설** — 우선순위 사슬 SSOT. 백테스트(`compat`)와 라이브(`event_loop`)가 공유. `_extract_default_qty` 는 alias 없이 삭제(SSOT 2개 방지)
- [x] **fail-closed 4종** — `supported=False` / `total is None` / `total <= 0` / `ProviderError`(502를 422로 흡수해 안내 문구가 도달 가능해짐). 통과시키면 `initial_capital=None` → `compute_qty()=1.0` 이라 "고친 척" 이 된다
- [x] **페이징 계약 분리** — 신규 2종은 `qb_live_signal_skipped_total` 만 올리고 `qb_live_signal_divergence_total` 은 **안 올린다**. ★알림 **제목**도 함께 갈랐다 — 카운터가 page 를 안 해도 제목이 "divergence" 면 사람은 제목 보고 호출된다(계약을 반만 고치는 것)
- [x] **FE** — 코크핏 `selected` 를 목록에서 `useMemo` 파생(객체 스냅샷이라 자동 종료 후에도 "돌고 있는 것처럼" 렌더되던 결함) + 중단 안내 · 세션 상세 **기준 자본** 노출(부재는 `—`, 0 위장 금지) · 폼 폴백 문구. ★`FormErrorInline` 교체는 **기각** — 그 컴포넌트가 `detail.detail` 을 안 읽어 기존 422 4종이 조용히 `"API 422 …"` 로 퇴행한다
- [x] 게이트: BE **3074**(+45) · FE **1151**(+7) · canon **32** · **e2e:authed 65-0** · ruff·mypy·tsc·lint 0 · 마이그레이션 **1**

### ★★판별력 증명 — 전체 stash 대신 표적 변이 6종

전체 stash 는 import/TypeError 를 내서 **"심볼이 없다"** 만 증명한다. 행동적 RED 를 만들려고 변이를 넣었다 뺐다.

```
M1 uses_stop_entry -> False   양성 5 FAIL / 음성 17 PASS  <- 과잉차단 아님을 동시 증명
M2 uses_stop_entry -> True    25 FAIL                     <- 음성 케이스가 진짜 판별력을 가짐
M3 compute_qty 의 /100 제거    4 FAIL                      <- 손계산 오라클이 산술을 잡음
M4 total -> free              2 FAIL                      <- 필드 혼동을 잡음
M5 신규 2종도 page             1 FAIL                      <- 카운터 계약을 잡음
M6 initial_capital 미전달      6 FAIL                      <- 배선이 가정이 아니라 증명됨
변이 잔존 0 · 복원 5/5 바이트 동일
```

손계산 오라클은 2의 거듭제곱만 골라 부동소수 오차를 0 으로 만들었다 — `8192 x 50 / 100 / 65536 = 0.0625`. 오답(1.0 / 0.03125 / 6.25 / 0.000625)이 정답과 충돌하지 않는다.

### 실화면 dogfood

- [x] **자동 종료** — `0e15c3c0` 이 마이그레이션 후 첫 tick(30초 내)에 `{'deactivated': 'stop_entry_unsupported'}`. ★이 세션은 **stop-entry 와 NULL baseline 둘 다** 해당인데 근본 원인을 보고했다(설계한 우선순위대로). 화면 "활성 세션" 이 1 → 0
- [x] **차단 문구** — PbR 로 세션 시작 → `live-session-form-error` 에 BE 문구 원문. `"API 422"` 미포함
- [x] **음성 대조군** — EMA 로 바꾸면 **201**, 활성 세션 1. 설정 없을 땐 기존 `StrategySettingsRequired` 문구가 정상 렌더(= `FormErrorInline` 을 기각한 판단이 옳았음을 실화면이 확인)
- [x] **독립 raw HMAC 오라클**(ccxt·`providers.py` 미경유) — `USDT walletBalance 190549.99467459` = DB `equity_baseline_usdt` **바이트 동일**, `retCode 0`
- [x] **M-4 마이그레이션** — 활성 세션이 있는 개발 DB 에서 upgrade → `is_active` 불변, 신규 컬럼 NULL, hydrate 정상. 클린 DB 에서 `downgrade base → upgrade head → downgrade -1 → upgrade head` 왕복 통과

### ★★프로덕션 진입 — 실주문 체결까지 3중 대조

기다렸더니 EMA 크로스가 실제로 났다. **시드로 만들지 않았다.**

```
손계산   190549.99467459 x 1% / 64512.50  = 0.02953691
DB       live_signal_events.qty            = 0.02953691   (action=entry, dispatched)
         orders.quantity                   = 0.02953691   (state=filled)
거래소    qty 0.029 · cumExecQty 0.029 · avgPrice 64484.2 · Filled · retCode 0
         orderId d474e540-… (UUID = linear perp)
```

DB → 거래소 `0.02953691 → 0.029` 차이는 **`amount_to_precision` 절삭**(BTCUSDT linear 수량 스텝 0.001)으로 정확히 설명된다. 실집행 명목 **$1,870** — 미배선이었다면 `1.0` = **$64,484**, **34.5 배**다.

### ★프로덕션 원장의 before / after

같은 계정, 같은 심볼, 같은 날. 수정 전후가 `trading.orders` 에 그대로 남았다.

```
10:02  sell 1.00000000  reduce_only=t  rejected   <- BL-478 증상. 진입이 없으니 청산만 나가 110017
10:17  buy  1.00000000  reduce_only=t  rejected
10:36  buy  1.00000000  reduce_only=t  rejected
11:51  buy  0.02953691  reduce_only=f  filled     <- 수정 후. 진짜 진입 + 자본 기준 수량
```

`1.0`(미배선 fallback) 이 전부 `reduce_only=t` 이고 전부 `rejected` 라는 것이 BL-478 과 BL-479 가
**한 증상의 두 얼굴**이었다는 증거다. 진입이 안 나가니 청산만 남고, 그 청산 수량조차 `1.0` 이었다.

### ★정직하게 남기는 것

- **플랜의 대안 하나가 틀렸다** — "신호 없이도 `last_strategy_state_report.running_equity` 로 배선을 증명한다" 고 적었는데 `to_report()` 에 그 키가 없다(7개 키뿐). 결국 진짜 신호를 기다려서 증명했다.
- **지금 `total == free`** (`totalPositionIM: 0`). dogfood 만으로는 둘을 구별할 수 없고, 그걸 증명한 건 **M4 변이뿐**이다.
- **배포 순서는 마이그레이션이 먼저다.** 워커가 신규 코드인데 DB 에 컬럼이 없던 몇 분 동안 `UndefinedColumnError` 로 전 세션 평가가 실패했다(실측). fail-closed 지만 시끄럽다.

### 신규 BL 5건

- **[BL-481]** P2 `sessions_allowed` 라이브 미배선 — 거래 시간대를 제한해도 라이브는 24h 진입
- **[BL-482]** P3 `pyramiding` cap 라이브 미배선
- **[BL-483]** **P1** `leverage` 라이브 마진게이트 미배선 — 백테스트가 거부할 진입을 라이브가 통과시킨다. ★그냥 넘기면 안 된다: 증거금 부족 skip 이 `warnings` 로만 남아 **완전 무음**이라 표면화 경로를 같이 만들어야 한다
- **[BL-484]** P2 자동 중단 **사유**가 화면에 안 남는다(알림 채널 전용)
- **[BL-485]** P3 `FormErrorInline` 이 `detail.detail` 폴백을 안 해 공통 컴포넌트를 못 쓴다
- **[BL-487]** P3 `test_get_pool_safe_across_event_loops` 가 `id()` 재사용에 취약한 선재 flake — pool 객체를 붙잡지 않고 `id()` 만 비교해 CPython 이 주소를 재사용하면 random RED. 전체 스위트에서 1회 관측, 격리 실행과 재실행은 통과
- **[BL-486]** **P1** ★라이브 사이징 equity 가 **300바 롤링 창**에 따라 변한다 — 같은 마지막 바에서 창 안 청산 유무로 `qty 0.09375 vs 0.0625`(**50% 차이**) 실측. 미배선 `1.0` 보다는 낫지만 완결이 아니다. KNOWN_LIMITATION 테스트로 못 박아 조용한 드리프트를 차단했고, 고치려면 라이브 equity 시맨틱((a) 세션 고정 / (b) 세션 누적 / (c) 실잔고 추종)을 먼저 정해야 한다

### 문서 종결 (sprint-template §9)

강등 2(`dogfood-restore` · `live-entry-wiring` → `archive/sprints/`) + 승격 1(**`reference/gates-and-traps.md`** — 게이트 지식이 7개 스프린트 문서에 복붙되고 있었다) → **`docs/` 최상위 12 → 10**. `README.md` 에 `<테마>/` 지위 명문화.

---

## ⚡ 체크리스트 A — BL-474 webhook ingress 패리티 (2026-07-26)

**스코프**: [`docs/archive/sprints/dogfood-restore/checklist.md`](archive/sprints/dogfood-restore/checklist.md) §A. #481 출처 라벨·#477 SessionScope 를 화면에서 보려면 linear perp **진입 → 청산 → 스윕 확정**이 실제로 일어나야 하는데, 그 경로를 테스트 주문 도구가 막고 있었다.

### ★진단이 한 겹 더 깊었다 — 다이얼로그가 아니라 webhook ingress

`router.py:138-147` 이 `OrderRequest` 를 7개 필드로만 조립하고 `parse_tv_payload`(`webhook.py:118-125`)가 6개 키만 읽어 **한 자리에서 3건이 동시에 버려졌다**.

```
leverage / margin_mode   해결 자체를 안 함        → has_leverage=false → spot
reduce_only              프론트는 보냄, 파서가 안 읽음 → 청산 확정 경로 전체가 막힘
take_profit / stop_loss  프론트는 보냄, 파서가 안 읽음 → UI 입력이 거짓말
```

★**leverage 만 고쳤으면 A 는 안 열렸다** — `tasks/trading.py:1342` 가 `not order.reduce_only` 로 조기 반환하고 스윕 쿼리도 `reduce_only IS TRUE` 를 요구한다. 그 플래그 없이는 다이얼로그 청산이 영원히 `realized_pnl_synced_at` 을 못 받는다.

### ★★체크리스트 자신의 함정 문구가 틀렸다

`checklist.md:108` 은 "레버리지 1 → `has_leverage=False` → spot" 이라 적었는데 **같은 문서 §A 표는 정반대**(`leverage=1 … → linear perp`)였다. 코드가 심판 — `order_service.py:194` = `req.leverage is not None and req.leverage > 0`, `tasks/trading.py:135` = `return lev > 0` → **1이면 linear**. 진짜 원인은 값이 1이어서가 아니라 **아무 값도 안 보내서**다. 관측에서 원인을 성급히 일반화한 사례로 문서에 정정 기록.

### Completed

- [x] **BL-474 Resolved** — `WebhookService.resolve_trading_params()` 신설. `Strategy.settings` 가 SSOT(`live_signal.py:931-932` / `close_service.py:86-92` 와 동일), 미설정·무효는 **422 fail-closed**, HMAC 검증 **뒤에** 호출(응답코드로 settings 유무 탐지 차단). `reduce_only`(+`bool("false")` 함정 방어)·TP/SL·`risk_percent` 파서 통과.
- [x] **FE** — 라우팅 배지(`Linear Perp · 2x · isolated`) · settings 없을 때 422 경고(**차단은 안 함** — 공개 ingress 라 서버가 권위) · 미리보기 레버리지 기본값 = 전략 설정 · `reduce_only` 시 `realized_pnl` 입력(추정/확정 대조용) · secret 안내문에 §05 Webhook 카드 명시
- [x] **신규 [BL-475]** — risk% 사이징 모드는 한 번도 작동한 적 없었다(`quantity` 누락 401 + 백엔드는 상한만 검사). 문구 정정 + 수량·손절가 필수화 + `risk_percent` 배선
- [x] **Sprint 7a 부채 청산** — `test_e2e_webhook_to_futures_order.py` 독스트링이 "Sprint 7b 로 분리" 라 적어둔 HTTP→ccxt 전 구간 테스트
- [x] **RED 증명 22건**(parse 17 · router 4 · e2e 1) + FE 신규 7건은 `git stash` 로 프로덕션만 되돌려 RED 재현
- [x] 게이트: BE **3029**(+24) · FE **1136**(+6) · ruff·mypy·tsc·lint 0 · 마이그레이션 **0**
- [x] **실화면 dogfood — Bybit 데모 실주문 4건.** 결정적 증거는 **주문 ID 형식**이었다: 수정 전 `2267433208968908032`(숫자형=spot) → 수정 후 `0a245783-f809-…`(UUID=linear). 거래소가 시장 유형이 바뀌었다고 말해주는 외부 증거다
- [x] **출처 라벨 혼재 상태 포착** — 청산에 추정 `-9.99` 주입(확정값과 우연히 같아질 수 없게) → 04:30:00 화면에 **`거래소 확정 -0.05935440` / `추정 -9.99000000`** 동시 표시 → 8초 뒤 확정 `-0.12772399`(두 청산의 정확한 합). `confirmed + estimated == total` 화면에서 성립. 대시보드 §01 KPI foot(`splitComplete`)도 렌더
- [x] **독립 HMAC 오라클** — ccxt·`providers.py` 미경유로 `/v5/position/closed-pnl` 직격. `orders.realized_pnl` · `exchange_exits.closed_pnl` · 거래소 원문 **3중 일치**
- [x] 라우팅 배지 · settings 없는 전략 422 경고 · 미리보기 레버리지 기본값 실화면 확인. 콘솔 error 0

### ★신규 BL 2건 (dogfood 실측이 만든 것)

- **[BL-476] 지연 +4.8초 실측** — `fetch_mark_price 1663ms · fetch_min_notional 1549ms · fetch_balance_usdt 1600ms`. leverage 가 채워지며 notional 가드가 webhook 에서 처음 도달 가능해진 대가. ★**게이트는 provider 를 stub 으로 갈아끼우므로 영원히 0ms** — 프로덕션에서만 보이는 회귀라 예상만 하지 않고 쟀다
- **[BL-477] 청산 원장 유령 `unknown`** — API 키 2개가 같은 Bybit 서브계정을 가리켜 같은 청산이 2행 적재. 07-24 행도 같은 패턴이라 **선재**. 금액은 안전(`aggregate_closed_pnl` 계정 스코프 + 세션 손익은 `orders.realized_pnl` 을 셈 — 실측 확인). 영향은 귀속/알림 표면뿐

---

## ⚡ 체크리스트 B — pine_v2 ↔ 거래소 발산 (조사 완료, 2026-07-26)

### ★★가설이 틀렸다 — "상태가 롤백 안 된다" 가 아니라 **진입이 나간 적이 없다**

체크리스트 B 는 "발주 실패 후 pine_v2 상태가 롤백되는가" 를 물었다. 답은 "롤백 경로 0" 이지만 **그게 원인이 아니었다.**

```
strategy.entry(..., stop=)  →  PendingOrder 파킹 + return None   (이벤트 미발행)
                            →  체결 시 event_action="fill"
run_live                    →  fill 은 dispatch 대상에서 제외      ← event_loop.py:287-288
독스트링                     →  "broker 가 자체 fill 알림 처리"
실측                        →  live_signal.py 에 trigger_price 참조 0건
```

**broker 에 그 stop 주문을 올린 적이 없다.** 그래서 진입 이벤트가 0건이고, 반전 시 생기는 `close` 만 나가서 매번 110017. 라이브 세션 `0e15c3c0` 의 주문 전량이 `reduce_only=true`·`rejected` 이고 **진입 주문은 한 건도 없다** — 이게 그 증거였는데 "사이징 문제" 로 읽었다.

**영향 범위는 `stop=` 진입 전략 한정.** 시장가 진입은 `strategy_state.py:634-642` 가 `event_action="entry"` 를 정상 발행한다. 시드 `s1_pbr` 은 진입 2개가 전부 `stop=` 이라 100% 이 경로.

### 등재한 BL

- **[BL-478] P1** — stop-entry 전략은 라이브에서 진입이 구조적으로 안 나간다. 최소 정직안 = 그런 전략의 세션 시작을 **차단하고 이유를 표시**(지금은 조용히 안 되면서 되는 척)
- **[BL-479] P1** — 라이브 사이징 미배선. `run_live` 가 사이징 인자 없이 `run_historical` 호출 → `compute_qty()` 항상 `1.0`. `position_size_pct` 는 라이브에서 **아무 데서도 안 읽힌다**(유일한 소비처 `compat.parse_and_run_v2` 의 프로덕션 호출자는 백테스트 어댑터 하나). Pine `default_qty_type` 선언조차 무시됨
- **[BL-480] P2 → ✅ Resolved** — ★**화면이 발산을 은폐했다.** 백엔드는 정확히 알고(실측 `verdict="local_only"` + `PivRevLE long qty 1 @ 64557.51`) 프론트에 문구도 있었는데, 행 생성이 `positions` 순회라 **`local_only` = `positions` 빈 배열**인 그 순간에만 렌더 불가였다. `divergences` 를 세션 단위로 건져 올려 수정. **실화면 확인** — _"BTC/USDT · PbR Pivot Reversal · 전략에만 열린 거래가 있습니다. 전략 보고: PivRevLE 롱 1 거래소 보고 포지션은 0건입니다."_ RED 7건 선확인. ★근본 원인(BL-478 진입 미발주)은 그대로 — **화면이 숨기지 않게** 만든 것뿐

### 확인된 설계 사실 (결함 아님)

- 상태 쓰기가 dispatch 보다 **먼저**고 그 사이 Celery 경계가 2개 — 거래소 결과를 알 수 없는 게 정상이다(transactional outbox)
- Option B(warmup replay)라 매 tick `run_historical` 재실행 → **되먹일 자리 자체가 없다**. 되먹여도 다음 tick 이 덮어쓴다
- 재동기화 경로(`Reconciler`·`orphan_scanner`·`resync_exchange_realized_pnl`)는 전부 **orders 만** 본다. 포지션/시뮬 재동기화는 없다
- `router.py:504-544` 가 응답 시점에 체결 주문으로 PnL 을 재계산하는 건 **read-side mask** 다 — DB 의 `total_realized_pnl -175.82` 는 그대로 남아 있다

### Next Actions

**이 스프린트는 여기서 닫는다.** 잔여 전량은 [`docs/archive/sprints/live-entry-wiring/checklist.md`](archive/sprints/live-entry-wiring/checklist.md) 로 이관 — 조사는 끝났고 남은 건 **결정 + 구현**이다.

- [x] **PR [#484](https://github.com/woosung-dev/quantbridge/pull/484)** `feat/bl-474-webhook-ingress-parity` → main — **squash 는 사용자**
- [ ] **다음 세션 = `docs/archive/sprints/live-entry-wiring/checklist.md`.** 첫 step = **BL-478 선택지 (a)/(b)/(c) 사용자 결정** — 라이브 매매 시맨틱을 바꾸므로 blocking 이다. 권고 = (c) 먼저(거짓말을 즉시 멈추고 (a) 설계 시간을 번다), (b) 는 백테스트↔라이브 일치를 조용히 깨므로 비권장

---

## ⚡ dogfood-restore 스프린트 (2026-07-26)

**스코프**: #477·#480·#481 이 전부 **실화면 dogfood 없이** 닫혔고(07-25 DB 전소로 `ts.ohlcv` 0행 → 백테스트 불가), 세 스프린트 분량 신뢰 작업이 우리가 쓴 테스트로만 검증돼 있었다 — §7.3 이 금지하는 circular oracle. (A) 복원 경로 + (B) 실화면 검증 + (C) e2e 소생. 마이그레이션 **0**.

### ★§0.5 실측이 킥오프 전제를 3건 정정했다

```
"authed 13 spec 실패" = 파일 수를 테스트 수로 오독. 실제 = 13파일/64테스트 중
  하드 실패 6, 나머지 57 은 page.route 목킹이라 빈 DB 에서도 통과.
  ★진짜 문제는 따로 — 캐논 감사 9건이 StateBox 만 감사하며 조용히 통과(BL-470).

복원은 거의 공짜 — TimescaleProvider 가 cache-first + live CCXT fill 이라
  백테스트 1회가 곧 시딩. 실측 9,337행 · 갭 0.

프로즌 픽스처는 현재 경로에서 도달 불가 — FixtureProvider 가 canonical
  `BTC/USDT` 의 슬래시를 경로로 해석(BL-468).
```

### ★★워커가 구 코드였다 — 그래서 legacy 행이 공짜였다

착수 시 `quantbridge-worker` 가 `b97ac57`(#480) **8시간 전** 이미지로 돌고 있었다(§7.2 위반). 덕분에 **조작 0의 진짜 pre-#480 행**을 얻었다 — 계획했던 "`metrics` 에서 마커만 SQL 로 제거" 는 오히려 **부정직**했다(신 컨벤션 숫자에 구 기준 각주가 붙는다). 순서가 비가역이라 legacy 를 먼저 돌리고 워커를 bind-mount 로 교체했다(재빌드 0).

### ★★dogfood 가 P1 을 잡았다 — 파산한 계좌에 양수 샤프

`_periodic_returns` 가 `prev == 0` 만 막고 **`prev < 0` 을 안 막아** 자본이 음수면 부호가 뒤집힌다 → **더 잃을수록 수익률이 양수**. 실측 = 10,000 → **-207,968**(총수익률 **-2179.68%**) 실행의 월간 수익률 13개 중 11개가 양수, **샤프 +0.029**. BL-398(#480)이 없애려던 거짓말의 다른 얼굴(그쪽은 수식, 이쪽은 분모 부호).

**★committed Trust Layer baseline 이 이걸 담고 있었다** — `s1_pbr` baseline 샤프 **+0.600** · 소르티노 **+2.349**(총수익률 -536%). 코퍼스 5종 중 4종이 음수 자본이고 **골든이 깨진 것도 정확히 그 4종**(거래 0인 `i2_luxalgo` 만 무관). baseline 재생성 diff = **12 메트릭 키 중 2개**(sharpe/sortino)·해당 4종 한정, `ohlcv_sha256` 불변.

### Completed

- [x] **S0 환경** — `docker builder prune -f`(8.9G→12.9G) · **`ts.ohlcv` hypertable 복구**(dev DB 만 평범한 테이블이었다, test DB 는 정상 = 07-25 사고 잔재. 0행이라 무료) · BE 8100 기동
- [x] **S1 `make seed`** — `backend/scripts/seed_dogfood.py`. **실 서비스 계층 + 실 Celery** 경유(HTTP/auth 만 우회 — clerk SDK 가 `azp` 클레임을 필수로 요구해 헤드리스 HTTP 시딩이 구조적으로 불가). 함정 3종을 상수로 박음(canonical `BTC/USDT` · 격자 정렬 UTC · `exchange` NOT NULL). **멱등**
- [x] **S2 커버리지** — 전략 3 / 백테스트 6 / 거래 3,194 / OHLCV 9,337 / optimizer 1. 샤프 4상태 전부 + 100x 청산 503
- [x] **S3 외부 오라클 대조**(엔진 미개입) — 샤프 **양 컨벤션 독립 재계산 일치**(구 수식 6.66e-16, 신 수식 1.5e-05) · legacy↔monthly **에쿼티 9,337 포인트 바이트 동일**(격차 42배가 전부 컨벤션) · 청산수 **엔진 503 = trades 테이블 503**, 1x 대조군 0 · 청산가 **롱 최대 0.995000 / 숏 최소 1.005000 = 손수식 정확 일치**(유리한 체결 0건)
- [x] **S5 결함 수정 4건** — **D1** 샤프 raw 렌더 **5곳**(계획은 4곳, CSV export 를 놓쳤다) → `describeSharpe` 경유 + 소스 스캔 가드 · **D2** 전체 원장 청산 사유 열(리포트 미리보기는 최신 25건 한정이라 503 청산이 안 보였다) · **BL-465** 음수 자본 가드 · **BL-467** optimizer-heavy OHLCV env
- [x] 게이트: BE **3005**(+5) · FE **1125**(+1) · ruff/mypy/tsc/lint 0 · **canon 32 불변** · build ok · **마이그레이션 0**
- [x] **e2e:authed 65 passed / 0 failed** — 빈 DB 하드 실패 6건 전부 초록
- [x] 실브라우저(MCP Playwright) — 전략목록 degenerate `—` · 목록 5행 각 컨벤션 각주 · **혼재 정렬 고지 발화** · 전체 원장 "청산 사유" 열 · 콘솔 error 0

### ★사용자가 알아야 할 것

**Bybit demo API 키가 죽었다.** ws-stream 실측 — `00:45:02Z ws_stream_auth_failed … Params Error` → `ws_circuit_opened`(1h). 시계 드리프트는 배제(호스트·컨테이너·Bybit 서버 시각 일치). **키 재등록 전까지 S4(실주문 머니-패스 dogfood)는 불가** — #481 출처 라벨과 #477 SessionScope 는 여전히 화면 미검증이다.

### ★S4 실주문 — 진단 정정 + 부분 완주

**"키 만료" 진단이 틀렸다.** 독립 HMAC 오라클로 REST 를 치니 **양쪽 키 모두 `retCode 0`**(자산 846,921.08). 진짜 원인은 **우리 WS 인증 `expires` 창이 +1s** 라 왕복 지연에 먹힌 것(**BL-473 Resolved**, 통제 실험 +1s 실패 / +10s·+60s 성공). 사용자에게 불필요한 키 재등록을 시켰다. 새 키는 `readOnly: 1` 로 생성돼 거래 불가였고 기존 키로 진행했다.

**검증됨** — Bybit 데모 **실주문 체결**(독립 오라클로 거래소 확인) · **BL-454 심볼 정규화 실경로 작동**(다이얼로그 `BTCUSDT` → `Order.symbol` canonical `BTC/USDT`) · 라이브 신호 경로 종단(`live_signal_events` dispatched + 주문 연결 + pine_v2 추정 손익) · **D3 수정 화면 확인**(`API 422 …` → `Cannot normalize symbol: BTCUSDT.P`).

**★신규 발견 BL-474** — 테스트 주문 다이얼로그는 `has_leverage=false` 라 **spot** 으로, 라이브 신호는 `true` 라 **linear perp** 로 나간다. 청산 원장·코크핏은 linear 만 보므로 **이 도구로 머니-패스를 dogfood 하면 조용히 아무것도 검증하지 못한다.**

### Blocked

- **출처 라벨(#481)·SessionScope(#477) 화면 검증** — linear perp 체결이 청산까지 가야 확정/추정이 섞인다. 라이브 세션은 1분마다 평가 중이나 PbR 피벗 신호 미발생(`events_inserted: 0`). 시드로 만들면 조작이라 하지 않음

### Next Actions

- [x] **PR [#482](https://github.com/woosung-dev/quantbridge/pull/482)** `stage/dogfood-restore` → main — **squash 는 사용자**
- [ ] **다음 세션 = [`docs/archive/sprints/dogfood-restore/checklist.md`](archive/sprints/dogfood-restore/checklist.md)** — 사용자 확정. (A) **BL-474** 테스트 주문 다이얼로그가 spot 으로 나가는 것 먼저 → 고치면 perp 진입→청산을 결정적으로 만들 수 있어 **출처 라벨·SessionScope 화면 검증이 열린다** (B) pine_v2 시뮬 상태 ↔ 거래소 포지션 발산 조사(`retCode 110017`, 수량 1.0 사이징 미반영 의혹 포함)
- [ ] (선택) 최종 codex 누적 diff 리뷰

---

---

## 완결 스프린트 이력

2026-07-26 이전 스프린트 섹션은 **[`archive/status-history.md`](./archive/status-history.md)** 로 분리했다.
회고가 있는 스프린트는 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 도 함께 본다.

## 상시 활성 컨텍스트 (영구 기록 외 발견 패턴)

- `dogfood Day N` 노트는 sprint 묶음과 별개로 `dev-log/` 에 단독 파일로 보관
- BL-005 (본인 1-2 주 dogfood) trigger 도래 후 H1→H2 gate (self-assessment ≥7) 가 재평가 기준
- `make up-isolated` (3100 / 8100 / 5433 / 6380) 가 다른 웹앱 병렬 시 디폴트
- **Pine SSOT 4 invariant audit** (`tests/strategy/pine_v2/test_ssot_invariants.py`) — supported list 추가 시 4 collection 동시 갱신 의무 자동 검증
- **Surface Trust sub-pillar (Sprint 30 ADR-019)** — Backend Reliability + Risk Management + Security + Surface Trust (가정박스 / 차트 / 24 metric / 거래목록). 측정: PRD 24 metric BE+FE 100% / config 5 가정 FE 100% / lightweight-charts 정합 / dogfood self-assess Day 3 ≥7
- **자율 병렬 sprint Agent worktree 패턴** — 충돌 회피 신규 파일 only / 통합 작업은 메인 세션 후처리 / gh CLI auto-merge --squash / `--no-verify` 1 회 우회 사용자 명시 승인 패턴

---

## 활성 BL 요약 (상세는 [`backlog.md`](./backlog.md))

> 본 sprint kickoff 시 백로그 review 의무. 자연어 표현은 컨텍스트 복원성 위해 sprint 회고 안에 유지하되, 새 항목 추가 시 BL ID 부여 후 등록.

핵심 cross-link (Sprint 59 PR-D 트리아주 후):

- **P0 active**: [BL-003](./backlog.md#bl-003) Bybit mainnet runbook
- **P1 active**: [BL-014](./backlog.md#bl-014) partial fill / [BL-015](./backlog.md#bl-015) OKX WS / [BL-022](./backlog.md#bl-022) golden 재생성 / [BL-023](./backlog.md#bl-023) KIND-B/C / [BL-024](./backlog.md#bl-024) real_broker E2E / [BL-025](./backlog.md#bl-025) autonomous-parallel patch / [BL-026](./backlog.md#bl-026) mutation fixture
- **P2 active**: [BL-186](./backlog.md#bl-186) full leverage model / [BL-190](./backlog.md#bl-190) PDF export / [BL-195](./backlog.md#bl-195) form animation / [BL-235](./backlog.md#bl-235) N-dim viz / [BL-236](./backlog.md#bl-236) objective whitelist
- **Deferred milestone** ([`_deferred.md`](archive/refactoring-backlog/_deferred.md)): BL-005 본인 dogfood / BL-070~075 Beta 본격 진입 / BL-145 EffectiveLeverageEvaluator
- **Archived 138건** ([`_archived.md`](archive/refactoring-backlog/_archived.md)): 모든 ✅ Resolved + Sprint 16~30 stale follow-up + P3 전부
- **정합성 audit:** [`04_architecture/architecture-conformance.md`](reference/architecture-conformance.md) — 15 항목 영구 체크리스트

---

## Test Skip / xfail 추적표 (Sprint 15-C 신설, 2026-04-28)

> 18 skip + 0 fail (Sprint 14 기준). "이 skip 이 왜 존재 + 언제 해소" 명시. 신규 skip 추가 시 본 표 업데이트 의무.

| #    | 위치                                                                                   | 종류                     | 사유                                                                                 | 해소 트리거                                                                  |
| ---- | -------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 1    | `tests/backtest/engine/test_golden_backtest.py:19`                                     | `pytestmark.skip`        | legacy golden expectations — pine_v2 `strategy.exit` 지원 + expected 재생성 필요     | pine_v2 strategy.exit 도입 후 golden 재생성                                  |
| 2    | `tests/real_broker/test_webhook_to_filled_e2e.py:31`                                   | `pytestmark.real_broker` | nightly E2E (Bybit Demo 실 호출). `--run-real-broker` flag + `BYBIT_DEMO_*` env 필요 | 매일 nightly cron (`.github/workflows/nightly-real-broker.yml`)              |
| 3    | `tests/real_broker/conftest.py:43`                                                     | `skip_marker`            | 위 #2 의 conftest fallback (env 미주입 시 collection-time skip)                      | 동일                                                                         |
| 4-7  | `tests/strategy/pine_v2/test_trust_layer_parity.py:251/334/357/421`                    | `skipif`                 | Trust Layer fixture (`regen_trust_layer_baseline.py` / 8 mutation set) 미생성        | Path β Stage 2c 2 차 mutation 8/8 도달 (2026-04-23 완료, 회귀로 활성화 검토) |
| 8    | `tests/strategy/pine_v2/test_trust_layer_parity.py:405`                                | `pytest.mark.skip`       | Mutation oracle 은 nightly workflow 또는 `--run-mutations` 수동 (CI default 차단)    | nightly mutation workflow 또는 manual gate                                   |
| 9-15 | `tests/strategy/pine_v2/test_mutation_oracle.py:147/179/212/253/296/328/376/414` (8건) | `skipif`                 | mutation fixture 미생성 시 collection skip                                           | Stage 2c 2 차 fixture 활성화 후 사용 가능 (현재 안전 fallback)               |
| 16   | `tests/strategy/pine_v2/test_mutation_oracle.py:213`                                   | `xfail(strict=False)`    | KIND=B/C 가 NaN-tolerance 한계로 mutation 구분 못 함. strict=False 로 명시           | KIND-B/C 분류 정밀도 향상 (Trust Layer v2 검토)                              |
| 17   | `tests/conftest.py:93`                                                                 | `skip_mutation` autouse  | 모든 `@pytest.mark.mutation` 자동 skip (CI default), `--run-mutations` 시 활성화     | pytest collection-time guard (영구)                                          |
| 18   | (집계 차이)                                                                            | xfail/skip 누적          | pytest collection-time 자동 분기 (real_broker / mutation 기본 차단)                  | 표 업데이트 의무                                                             |

**카테고리:**

- 영구 (정상): #2, #3, #8, #17 — opt-in flag 가 정확한 안전장치
- fixture 활성화 후 자동 해소: #4-7, #9-15 — Path β Stage 2c 2 차 후 회귀 검토 → [BL-026](./backlog.md#bl-026)
- dette: #1 (golden 재생성) → [BL-022](./backlog.md#bl-022) / #16 (KIND-B/C 정밀도) → [BL-023](./backlog.md#bl-023)

**관리 규약:** 신규 skip 추가 시 본 표 동일 PR 업데이트 / 매 sprint 끝 fixture 카테고리 재검토.

---

## Blocked

(현재 없음 — Sprint 58 종료)

---

## Questions

(없음 — 활성 질문 시 추가)

---

## Next Actions

- Sprint 59 진입 = Day 7 인터뷰 2026-05-16 결과 분석 후 결정
- Tier 1 refactor audit (현재 진행 중) → 사용자 승인 후 commit + PR
