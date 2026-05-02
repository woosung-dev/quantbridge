# Sprint 20 Dogfood Day 0 — Phase 0 사전 준비 + 1차 broker 호출 검증

> **Sprint**: 20 (Path B 본인 1-2주 dogfood)
> **날짜**: 2026-05-02 KST 20:30 ~ 21:30 (1h)
> **본 dev-log 의 본질**: Phase 0 5단계 사전 준비 + fixture broken bug 발견 → hot-fix → real broker 검증 + Pain 박제.
> **이전 sprint**: PR #91 머지 완료 (Sprint 18 BL-080 + Sprint 19 BL-081/083/084/085 ✅, self-assessment 9/10).
> **다음**: Day 1 (TradingView alert 또는 추가 라이브 시나리오).

---

## §1. 환경 baseline (격리 docker stack)

| 항목                            | 값                | 상태   |
| ------------------------------- | ----------------- | ------ |
| Sprint 18 머지                  | `e55482f`         | ✅     |
| Sprint 19 머지                  | `1f776d0`         | ✅     |
| docs sync                       | `dfb3c75`         | ✅     |
| frontend `localhost:3100`       | 200               | ✅     |
| backend `localhost:8100/health` | 200               | ✅     |
| db (5433) / redis (6380)        | healthy 26h       | ✅     |
| worker / beat / ws-stream       | up 5h             | ✅     |
| DB baseline                     | users:1 외 모두 0 | (깨끗) |

---

## §2. Phase 0 5단계 진행 (Playwright MCP + 사용자 본인)

| 단계                                              | 진행 방식                                       | 결과                                                                                                              |
| ------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1. Bybit Demo 계정 + API key                      | 사용자 본인 (외부)                              | ✅ 발급 완료                                                                                                      |
| 2. ExchangeAccount 등록 (FE Dialog)               | AI Playwright (form fill) + 사용자 (key/secret) | ✅ row 1건, AES-256 암호화 (`api_key_encrypted` 120b / `api_secret_encrypted` 140b / `passphrase_encrypted` NULL) |
| 3. Strategy create + webhook secret               | AI Playwright (3-step wizard 자동)              | ✅ ID `63a4ee38...`, atomic auto-issue 작동 (Sprint 6 broken bug 재발 ❌), webhook_secret_id `0536d704...`        |
| 4. Backtest 1회 (BTC/USDT 1h, 2026-04-02 ~ 05-02) | AI Playwright (form fill + Submit)              | ✅ COMPLETED 2.72s — total -98.42% / Sharpe 0.84 / MDD -115.52% / 29 trades / equity 721 points                   |
| 5. TestOrderDialog smoke (1차 + 2차)              | AI Playwright (form fill) + 사용자 (Submit)     | ⚠️ 1차 fixture, 2차 real broker (§3 참조)                                                                         |

### §2.1 Backtest 결과 발견 — MDD -115% (BL-004 관련 가능성)

EMA crossover 가 4월 변동성에서 over-trading + whip-saw + short entry 의 capital base 초과 손실. BL-004 (KillSwitch capital_base) 의 검증 데이터 후보. **dev-log 박제 — Sprint 21+ 분석**.

---

## §3. Pain 발견 — P1 BL-091 silent fixture fallback

### §3.1 증상

사용자가 TestOrderDialog (1차) 발송 → UI "filled" 표시 → DB `state=filled`. **하지만 broker 까지 안 감**:

| 항목                     | 1차 (fixture)         | 2차 (real broker)                                 |
| ------------------------ | --------------------- | ------------------------------------------------- |
| `exchange_order_id`      | `fixture-1`           | `2206110500927048960` (Bybit 19자리 snowflake ID) |
| `filled_price`           | 50000.00 (mock round) | 78251.70 (실제 BTC 시세 ~$78K, 2026-05-02)        |
| 처리 시간                | 0.13초 (instant mock) | 1.95초 (real CCXT roundtrip)                      |
| `filled_at - created_at` | 0.15초                | 1.71초                                            |
| Bybit 푸시 알림          | ❌                    | ✅ 사용자 받음                                    |

### §3.2 Root cause

- `backend/src/tasks/trading.py:_build_exchange_provider()` (line 77-99) — **`settings.exchange_provider` (Pydantic env) 만 보고 dispatch**, ExchangeAccount.mode/exchange 완전 무시
- `docker-compose.yml` worker/beat env 에 `EXCHANGE_PROVIDER` 누락 → Pydantic default `"fixture"` 적용 → `FixtureExchangeProvider()` 반환
- `backend/src/trading/providers.py:105` `FixtureExchangeProvider` 가 정확히 `fixture-{counter}` + `Decimal("50000.00")` 발행

### §3.3 Hot-fix (Sprint 20 Day 0 적용)

| 변경                                                                                         | 파일                                                  |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `EXCHANGE_PROVIDER=fixture` → `bybit_demo`                                                   | `.env` (gitignored)                                   |
| worker/beat env 에 `EXCHANGE_PROVIDER: ${EXCHANGE_PROVIDER:-fixture}` 추가 (누락 root cause) | `docker-compose.yml`                                  |
| recreate worker / beat / ws-stream                                                           | `docker compose -f ... -f ... up -d --force-recreate` |

검증: worker 재기동 후 `EXCHANGE_PROVIDER=bybit_demo` 적용 ✅, 5분 cycle scan_stuck_orders / reconcile_ws_streams 정상.

### §3.4 BL-091 등록 (P1 / M)

`docs/REFACTORING-BACKLOG.md` BL-091 신규. Sprint 21+ proper fix:

- `_get_exchange_provider(account: ExchangeAccount) -> ExchangeProvider` 시그니처 변경
- account 의 `(exchange, mode)` tuple 기반 dynamic dispatch
- `settings.exchange_provider` 는 fallback 또는 deprecation
- 추가 검증 의무: `tests/integration/test_dogfood_live_broker.py` — `exchange_order_id` 가 `fixture-*` 패턴 안 시작하는지 assert

---

## §3.5 6-Backtest 검증 매트릭스 (사용자 pine 폴더 6 파일)

사용자 본인 보관 `tmp_code/pine_code/` 의 6 indicator/strategy 모두 BTC/USDT 1h 6개월 (2025-11-02 ~ 2026-05-02) backtest 시도. parse / runnable / 결과:

| #   | 파일                     | Pine   | 종류      | parse | unsupported | backtest | Trades | Return   | MDD      |
| --- | ------------------------ | ------ | --------- | ----- | ----------- | -------- | ------ | -------- | -------- |
| 1   | PbR strategy easy        | **v6** | strategy  | ✅    | 0           | ✅ 6.82s | 469    | -680.91% | -490.95% |
| 2   | UtBot indicator easy     | v4     | study     | ✅    | 6           | 🔴 422   | —      | —        | —        |
| 3   | UtBot strategy medium    | v4     | strategy  | ✅    | 6           | 🔴 422   | —      | —        | —        |
| 4   | LuxAlgo indicator medium | **v5** | indicator | ✅    | 0           | ✅ 7.31s | 155    | -319.12% | -289.12% |
| 5   | DrFXGOD indicator hard   | **v5** | indicator | ✅    | **39**      | 🔴 422   | —      | —        | —        |
| 6   | RsiD strategy hard       | v4     | strategy  | ✅    | 8           | 🔴 422   | —      | —        | —        |

**성공률**: 2/6 (33%) — PbR + LuxAlgo. **차단**: 4/6 (UtBot×2 + DrFX + RsiD).

### §3.5.1 발견 (BL-096 P1 critical)

흔한 builtin 다수 미지원: `abs` / `max` / `min` / `ta.barssince` / `ta.valuewhen` / `ta.pivothigh/low` / `currency.USD` / `strategy.fixed` / `request.security` / `heikinashi` / `security` / `barcolor` / `label.*` / `box.*` / `str.tostring` / `fixnan` / `barstate.*` / `timeframe.period` / `study` / `timestamp`.

**모순**: DrFXGOD = `i3_drfx` 동일 + RsiD = `s3_rsid` 동일 = Sprint 8c 의 strict=True 통과 corpus. **production parse-preview 에서는 reject** = 검증 corpus vs production supported list **이중 잣대** (BL-096 P1).

### §3.5.2 추가 시스템 검증

✅ Pine **v4 + v5 + v6** 모두 파싱 성공 (Sprint 8b/8c v4 위주 검증보다 넓은 호환성)
✅ Sprint Y1 **Coverage Analyzer** pre-flight reject 정상 동작 (4건)
✅ Sprint 8b **VirtualStrategyWrapper** indicator → strategy 자동 wrap (LuxAlgo `Upper Break` / `Lower Break` → 155 trades)
✅ Celery worker prefork-safe loop (BL-080 Sprint 18) — 6.82s / 7.31s / 1.95s × 3 backtest 모두 정상
⚠️ **공통 패턴 — over -100% return** (PbR -680% / EMA -98% / LuxAlgo -319%) → BL-004 capital_base 가정 강한 검증 데이터 (3 데이터 포인트 누적)

### §3.5.3 사용자 본인 6 파일 dogfood 의미

dogfood 본질 = "사용자 본인이 매일 쓰고 싶은 시스템". 본인 보관 6 지표 중 **4건 거부** = **dogfood 의 가장 큰 friction**. Sprint 21 BL-096 우선순위 P1 — 흔한 builtin (`abs`, `max`, `min`, `ta.barssince`, `ta.valuewhen`, `ta.pivothigh/low`) 추가 시 사용자의 dogfood 통과율 33% → 80%+ 예상.

---

## §4. 추가 Pain 발견 (Sprint 21+ 이관 후보)

### §4.1 P2 — `qb_active_orders` filled 후 dec 안 됨

- 현재 `qb_active_orders=2.0` — 1차 + 2차 모두 filled 인데 dec 누적 안 됨
- 추정: BL-027 winner-only dec 가 fixture 1차 때 inc 안 했지만 dec 시도? 또는 state_handler 의 WS event 처리에서 winner-only rowcount 가 0 반환?
- **BL-092 신규 후보** — Sprint 21 분석. `qb_active_orders` 의 invariant ("filled/cancelled 시 dec, pending/submitted 시 inc") 검증.

### §4.2 P3 — TestOrderDialog 성공 시 명시적 confirmation 부재

- Submit 성공 → dialog 자동 닫힘만, toast/inline confirmation 없음
- 사용자 본인 발견: "주문창이 안 보여서.. 된거긴한것 같은데?"
- **BL-093 신규 후보** — Sprint 21 dogfood UX. Submit 성공 시 sonner toast + dialog 안 닫고 success state 표시 (또는 둘 다).

### §4.3 P3 — webhook secret sessionStorage TTL 30분 충돌

- Sprint 13 의 보안 정책 (1회 노출 + sessionStorage TTL 30분) 가 dogfood 시나리오와 충돌
- Strategy create 11:51 → TestOrder 12:24 (33분 경과) → "Webhook secret 캐시 없음. Strategy 페이지에서 Rotate 후 다시 시도" 발생
- 매번 30분 안에 dogfood 사이클 끝내야 한다는 가정 — 실용적이지 않음
- 우회: Rotate 후 새 plaintext sessionStorage 자동 갱신 (Sprint 13 useRotateWebhookSecret hook 정상 작동 ✅)
- **BL-094 신규 후보** — Sprint 21 dogfood UX. 옵션:
  - TTL 30분 → 24h 늘림
  - "secret 다시 보기" 버튼 (boundary: 보안 정책 약화)
  - TestOrderDialog 가 sessionStorage 부재 시 자동 Rotate prompt
  - 또는 의도된 보안 정책 유지 + dogfood 가이드에 "사이클 30분 내" 명시

---

## §5. 운영 관측 (qb\_\* 메트릭)

| 메트릭                          | baseline (Phase 0 전) | dogfood Day 0 종료 | 비고                                           |
| ------------------------------- | --------------------- | ------------------ | ---------------------------------------------- |
| `qb_active_orders`              | 0.0                   | **2.0**            | filled 후 dec 미발생 — BL-092 후보             |
| `qb_pending_alerts`             | 0.0                   | 0.0                | Sprint 19 BL-081 신규 gauge, KillSwitch 미발화 |
| `qb_ws_orphan_buffer_size`      | 0                     | 0                  | Sprint 12 supervisor 정상                      |
| `qb_ws_reconcile_skipped_total` | 0                     | 0                  | reconcile 정상                                 |
| `qb_ws_duplicate_enqueue_total` | 0                     | 0                  | Sprint 12 idempotency 정상                     |

worker 5분 cycle (BL-080 prefork-safe loop 검증):

```
[12:17~12:27] backtest.reclaim_stale × 2  → succeeded
[12:17~12:27] trading.reconcile_ws_streams × 2  → succeeded (ws_stream_reenqueued)
[12:17~12:27] trading.scan_stuck_orders × 2  → succeeded {pending: 0, submitted: 0, interrupted: 0}
[12:21] trading.fetch_funding_rates × 2 (BTC, ETH)  → succeeded in 1.75s
[12:27] trading.execute_order  → succeeded in 1.95s (real broker, exchange_order_id 2206110500927048960)
```

ws-stream:

- `wss://stream-demo.bybit.com/v5/private connected` ✅ (reconnect_count=0)
- 1.95초 후 DB state=filled 됐으니 WS event 정상 처리 (단 verbose log 미출력)

---

## §6. 검증 시스템 컴포넌트 (Phase 0 + Day 0)

✅ Strategy CRUD + Pine v4 파싱 (`v2_adapter_ok` log)
✅ Webhook secret atomic auto-issue (Sprint 13)
✅ Webhook secret Rotate + sessionStorage 자동 갱신 (Sprint 13)
✅ Backtest form prefill + 422 inline 미발생 (Sprint 13 Phase C)
✅ Celery worker prefork-safe loop (Sprint 18 BL-080)
✅ pine_v2 dispatcher (`v2_adapter_ok`)
✅ vectorbt 결과 + recharts equity curve + tooltip
✅ HMAC-SHA256 (browser Web Crypto API → backend `X-Signature` 검증)
✅ TestOrderDialog KS bypass guard (Sprint 13 G.4 P1 #5 fix)
✅ AES-256 GCM 암호화 (api_key 120b / api_secret 140b)
✅ ExchangeAccountService.register() commit (Sprint 15-A LESSON-019 검증)
✅ **BybitDemoProvider real CCXT roundtrip** (hot-fix 후, 1.95초)
✅ **WS supervisor stream-demo.bybit.com 연결 + state transition**
⚠️ qb_active_orders dec 누락 (Pain α)
⚠️ TestOrderDialog 성공 confirmation 부재 (Pain β)
⚠️ webhook secret sessionStorage TTL 30분 (Pain γ)
🔴 silent fixture fallback (Pain P1 — hot-fix 적용, BL-091 등록)

---

## §7. self-assessment — 사용자 본인 채점 (2026-05-02 KST 22:00)

### §7.1 사용자 친화 8 항목 (jargon 배제 — Y/N/P)

| #   | 질문                                                                      | 답    | 비고                                                                                       |
| --- | ------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------ |
| 1   | 거래소 계정 등록 (`/trading` Dialog) — 끝까지 됐고 안전해 보임?           | **Y** | bybit demo + AES-256                                                                       |
| 2   | Strategy 만들기 (3-step wizard) — Pine 붙여넣고 저장까지 막힘 없음?       | **Y** | v4/v5/v6 모두 파싱                                                                         |
| 3   | webhook URL/Secret 받기 (?tab=webhook amber card) — 1회 노출 정책 합리적? | **Y** | 단 TTL 30분 (BL-094) — dogfood 사이클 내 OK                                                |
| 4   | Backtest 결과 보기 (5탭 + Equity Curve) — 6개월 결과 신뢰됨?              | **P** | 결과 시각화 OK / 하지만 over -100% MDD (BL-004) 신뢰도 의심                                |
| 5   | TestOrderDialog 발사 (실제 Bybit Demo broker) — 진짜 broker 갔다고 확신?  | **Y** | hot-fix 후 1.95s + Bybit 푸시 알림 받음                                                    |
| 6   | 본인 보관 indicator 6개 중 backtest 되는 비율 — 만족?                     | **N** | 2/6 = 33% (PbR + LuxAlgo). UtBot×2 + DrFX + RsiD 거부 (BL-096)                             |
| 7   | Bybit Demo UI 와 일치 확인 — **우리 UI 안에서** 쉽게 확인 됐나?           | **N** | 우리 UI 안 broker 도달 evidence 부재 → demo.bybit.com 직접 가서 확인 (BL-093+095 superset) |
| 8   | **이 시스템 매일 1시간 쓰고 싶나?** ⭐ Sprint 20 본질                     | **P** | 가능성 봤지만 본인 indicator 못 쓰는 큰 막힘 (BL-096 P1)                                   |

**총: Y×5, P×2, N×2** = 5/8 완전 OK + 2/8 부분 + 2/8 미달.

### §7.2 가중치 환산

| 항목                                     | 가중치 | 답 매핑 | 점수     | 비고                                                                               |
| ---------------------------------------- | ------ | ------- | -------- | ---------------------------------------------------------------------------------- |
| watchdog (계정 등록 + 주문 발사 안정성)  | 4      | 1Y + 5Y | **4/4**  | scan_stuck_orders 5min cycle + BL-080 prefork-safe 8 backtest 안정                 |
| retry/alert (UI 안에서 broker 도달 확인) | 2      | 5Y + 7N | **1/2**  | 발사는 Y / 우리 UI 안 evidence N → BL-093+095 superset                             |
| Pain 발견 (의무)                         | 2      | BL 6건  | **2/2**  | BL-091 + BL-096 + BL-092~095 — **풍성**                                            |
| 매일 사용 quality                        | 2      | 8P      | **1/2**  | 가능성 봤지만 본인 indicator 못 쓰는 큰 막힘                                       |
| **합계**                                 | **10** |         | **8/10** | Sprint 18~19 **9/10** vs 라이브 Day 0 **8/10** = 자동 9 → 라이브 8 (자연스러움 -1) |

### §7.3 결정적 신호 (Sprint 21 분기 근거)

- **N×2 (6번 indicator + 7번 UI evidence)** = Sprint 21 **P1 우선순위 명확**
  - **BL-096 (Coverage Analyzer 좁음, 33% 통과)** = dogfood 매일 사용 가장 큰 friction
  - **BL-093+095 superset (UI broker 도달 evidence)** = Sprint 21 frontend P1
- **P×1 (8번 매일 사용)** = 8/10 정확히 일치. 본인 indicator 통과율 33% → 80%+ 가 핵심 trigger
- gate ≥7 통과 = **dogfood 진행 OK**, 단 Sprint 21 BL-096 P1 우선

### §7.4 Sprint 21 분기 권장 (별점)

| Path                                    | 별점  | 적합도                                                                                                             |
| --------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------ |
| **B-1. BL-096 + BL-093+095 우선 (1주)** | ★★★★★ | Day 0 N×2 직접 해소. 통과율 33% → 80%+ + UI broker evidence. **self-assessment 8 → 9+ 회복** + 본인 매일 사용 가능 |
| B-2. BL-091 architectural (1-2일)       | ★★★★  | Sprint 20 hot-fix 의 proper fix (account.mode 기반 dynamic dispatch). 즉시 risk 낮지만 architectural 의무          |
| C. Path A Beta 오픈 진입                | ★★    | 8/10 → 본인 매일 사용 P 상태에서 외부 노출은 시기상조. BL-096 fix 후 권장                                          |

---

## §8. Sprint 21+ 이관 BL (Day 0 발견 누적)

| ID                 | 제목                                                                                          | Priority | est                   | trigger                                             |
| ------------------ | --------------------------------------------------------------------------------------------- | -------- | --------------------- | --------------------------------------------------- |
| BL-091 ✅ 등록     | ExchangeAccount.mode 무시 + EXCHANGE_PROVIDER env 누락 silent fixture fallback                | **P1**   | M (1-2일)             | Sprint 21 진입 즉시                                 |
| **BL-096 ✅ 등록** | **Coverage Analyzer supported list 좁음 + Sprint 8c corpus 이중 잣대** (pine 6/6 중 4 reject) | **P1**   | M (1주)               | Sprint 21 우선 — **dogfood 통과율 33% → 80%+ 목표** |
| BL-092 ✅ 등록     | `qb_active_orders` filled 후 dec 누락                                                         | P2       | S (분석 + 1-line fix) | Sprint 21 분석                                      |
| BL-093 ✅ 등록     | TestOrderDialog 성공 confirmation (toast/inline)                                              | P3       | S (1h)                | dogfood UX nit                                      |
| BL-094 ✅ 등록     | webhook secret sessionStorage TTL vs dogfood UX                                               | P3       | S (정책 결정 후)      | 정책 결정 후                                        |
| BL-095 ✅ 등록     | Backtest 422 inline detail 미흡                                                               | P3       | S (1h)                | Sprint 21 FE                                        |
| BL-004 (기존)      | KillSwitch capital_base 가정 — short over -100% MDD                                           | P0       | M                     | dogfood 누적 데이터 (3 포인트)                      |

---

## §9. 다음 단계 (Day 1+)

1. **사용자 self-assessment 채점** → 본 dev-log §7 갱신 + commit
2. **Bybit Demo UI 직접 확인 ✅ 완료 (사용자 본인)** — Trade History 의 4 항목 모두 우리 DB 와 정확히 일치:
   - Qty `0.001000 BTC` ↔ DB `0.00100000` ✅
   - Filled Price `78,251.7 USDT` ↔ DB `78251.70000000` ✅
   - Transaction Time `2026-05-02 21:27:45 KST` ↔ DB `12:27:45.525242+00 UTC` (= 21:27:45 KST) ✅
   - Order ID `27048960` (Bybit UI truncate 8자리) ↔ DB `2206110500927048960` (Snowflake 19자리 suffix match) ✅
   - 별도 `Transaction ID: 01987565` = execution/trade ID (1 order = N trades 가능, normal Bybit 모델)
   - **3-way 일치 (DB ↔ 우리 UI ↔ Bybit Demo UI) 검증 완료 — broker 도달 100% 확정**
3. **Day 1 (별도 dev-log)**:
   - TradingView alert 설정 (외부, 사용자 본인) — webhook URL + secret `Eb1GVaHX...kj8` 사용
   - 또는 추가 TestOrderDialog smoke (sell, partial fill 등)
   - 매일 1~2 trade 실 사용 + qb\_\* 메트릭 모니터링
4. **Pain α 분석** — `qb_active_orders` invariant 검증 (BL-092 분리 결정)
5. **Day 8+ BL-082 1h soak gate** — `docker stats backend-worker` RSS slope < 50MB/h

---

## §10. Atomic Update (본 sprint 운영)

- 본 dev-log: `docs/dev-log/2026-05-02-sprint20-dogfood-day0-setup.md` ✅
- 백로그: `docs/REFACTORING-BACKLOG.md` BL-091 등록 ✅
- 코드: `docker-compose.yml` worker/beat 에 `EXCHANGE_PROVIDER` env 라인 추가 ✅
- 환경: `.env` `EXCHANGE_PROVIDER=bybit_demo` (gitignored, no commit)
- 다음: 사용자 self-assessment 후 `stage/h2-sprint20` 브랜치 + commit + 사용자 stage→main PR

---

## §11. Git plan

- 브랜치: `stage/h2-sprint20` (Sprint 19 의 `stage/h2-sprint18` sequential pattern 준수)
- commit message: `H2 Sprint 20 Day 0 — BL-091 fixture provider hot-fix + Phase 0 + first real broker smoke`
- main 직접 push 금지 — 사용자 수동 stage→main PR
