# QuantBridge — TODO

> **Last Updated:** 2026-07-26 (dogfood-restore 체크리스트 **A** — BL-474 webhook ingress 패리티)
> **Active Sprint:** **dogfood-restore 체크리스트 A** — 테스트 주문이 라이브와 같은 시장(linear perp)으로 나가게 해 출처 라벨 검증을 연다
> **Active Branch:** `feat/bl-474-webhook-ingress-parity` (main @ `a716ef3` 베이스)

## ⚡ 체크리스트 A — BL-474 webhook ingress 패리티 (2026-07-26)

**스코프**: [`docs/dogfood-restore/checklist.md`](dogfood-restore/checklist.md) §A. #481 출처 라벨·#477 SessionScope 를 화면에서 보려면 linear perp **진입 → 청산 → 스윕 확정**이 실제로 일어나야 하는데, 그 경로를 테스트 주문 도구가 막고 있었다.

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

**이 스프린트는 여기서 닫는다.** 잔여 전량은 [`docs/live-entry-wiring/checklist.md`](live-entry-wiring/checklist.md) 로 이관 — 조사는 끝났고 남은 건 **결정 + 구현**이다.

- [x] **PR [#484](https://github.com/woosung-dev/quantbridge/pull/484)** `feat/bl-474-webhook-ingress-parity` → main — **squash 는 사용자**
- [ ] **다음 세션 = `docs/live-entry-wiring/checklist.md`.** 첫 step = **BL-478 선택지 (a)/(b)/(c) 사용자 결정** — 라이브 매매 시맨틱을 바꾸므로 blocking 이다. 권고 = (c) 먼저(거짓말을 즉시 멈추고 (a) 설계 시간을 번다), (b) 는 백테스트↔라이브 일치를 조용히 깨므로 비권장

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
- [ ] **다음 세션 = [`docs/dogfood-restore/checklist.md`](dogfood-restore/checklist.md)** — 사용자 확정. (A) **BL-474** 테스트 주문 다이얼로그가 spot 으로 나가는 것 먼저 → 고치면 perp 진입→청산을 결정적으로 만들 수 있어 **출처 라벨·SessionScope 화면 검증이 열린다** (B) pine_v2 시뮬 상태 ↔ 거래소 포지션 발산 조사(`retCode 110017`, 수량 1.0 사이징 미반영 의혹 포함)
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
