# Dogfood Day 3 — Sprint 14 Track UX-2 검증 (pre-merge)

> 2026-04-27. Sprint 14 (`stage/h2-sprint14`) 머지 전 local stage 자동 검증.
> Plan: `~/.claude/plans/quantbridge-sprint-14-track-iterative-puffin.md`
> 이전 dogfood: [`2026-04-26-dogfood-day2.md`](2026-04-26-dogfood-day2.md) (self-assessment 6/10 — gate 1점 차 미통과)

---

## 0. Sync 진단 결과

| 항목                | 상태                                                                             |
| ------------------- | -------------------------------------------------------------------------------- |
| branch              | `stage/h2-sprint14` (3 commits ahead of main: `4d863df` / `c1f9012` / `06dfb11`) |
| backend uvicorn     | 재기동 ✅ (PID 59048/59050, stage/h2-sprint14 코드)                              |
| frontend dev server | 가동 중 (Next.js dev mode 자동 reload, PID 73557)                                |
| docker compose      | db / redis / worker / beat / ws-stream 5/5 Up                                    |
| `/health`           | `{"status":"ok","env":"development"}`                                            |
| pnpm build          | ✅ 16/16 static pages generated (Phase B-3 throw 회피 검증)                      |

---

## 1. Sprint 14 변경 요약

### Phase A (`4d863df`) — TabWebhook hydration race fix (Day 2 Pain #2)

- `tab-webhook.tsx`: `useState(() => readWebhookSecret)` initializer → `useSyncExternalStore` 패턴.
  server snapshot=null + client snapshot read + listeners notify (LESSON-004 정책 안에서 set-state-in-effect 차단 회피).
- `webhook-secret-storage.ts`: `subscribeWebhookSecret` + `notify()` 추가. cache/clear 시 자동 re-render.
- `new/page.tsx`: `useCreateStrategy onSuccess router.push` 에 `?tab=webhook` 추가 — webhook 탭 직접 진입.
- TDD: 4 tests (cached on mount + hide + clear regression).

### Phase B (`c1f9012`) — G.4 P2 잔존 4건 + helper 통합

- B-1: `test-order-dialog.tsx` onSubmit 의 `crypto.subtle.sign` / `randomUUID` try/catch 추가 → form error inline + dialog 유지.
- B-2: `useStrategies` / `useExchangeAccounts` 에 `retry: 1` + `exchange-accounts-panel.tsx` isLoading skeleton + isError retry 버튼.
- B-3: `lib/api-base.ts` (신규) `getApiBase()` helper — 3 곳 통합 (api-client / test-order-dialog / tab-webhook). top-level throw 금지 (codex G.0 P1 #3) + fallback + 1회 console.error.
- B-4: `readErrorBody` 8KB cap + JSON detail 정규화. apiFetch + TestOrderDialog 양쪽 재사용.
- TDD: +11 tests (api-base 8 + WebCrypto 1 + ExchangeAccounts loading-error 2).

### Phase C (`06dfb11`) — broker fill 거짓 양성 fix (codex G.0 P1 #1)

- `tasks/trading.py::_async_execute` receipt.status 분기 도입:
  - `"filled"` → `transition_to_filled` (기존 동작 유지)
  - `"rejected"` → `transition_to_rejected` (신규)
  - `"submitted"` → `attach_exchange_order_id` 만 호출, submitted 유지 (WS event / reconciler 가 terminal evidence 시 전이)
- `repository.py::attach_exchange_order_id` 신규 — submitted 상태 유지하면서 exchange_order_id 만 update.
- TDD: +3 tests (submitted 유지 + rejected 전이 + Sprint 13 LESSON commit spy ≥ 2).

---

## 2. 자동 검증 결과 (CI 동등)

| 항목                                | 결과                                                        |
| ----------------------------------- | ----------------------------------------------------------- |
| `cd backend && uv run pytest -q`    | ✅ **1185 passed** (Sprint 13 1181 → +4) / 18 skip / 0 fail |
| `cd backend && uv run ruff check .` | ✅ All checks passed                                        |
| `cd backend && uv run mypy src/`    | ✅ Success: no issues found in 151 source files             |
| `cd frontend && pnpm vitest run`    | ✅ **243 passed** (Sprint 13 232 → +11) / 0 fail            |
| `cd frontend && pnpm lint`          | ✅ 0 errors / 0 warnings                                    |
| `cd frontend && pnpm tsc --noEmit`  | ✅ no errors                                                |
| `cd frontend && pnpm build`         | ✅ 16/16 static pages generated (Phase B-3 검증)            |

**LESSON-004 준수**: 모든 hooks diff (useSyncExternalStore + retry + skeleton) 가 lint pass. Phase A 의 useEffect 시도가 `react-hooks/set-state-in-effect` 차단 → useSyncExternalStore 로 정석 우회 (Codex 권장 패턴).

---

## 3. DB / 메트릭 스냅샷

```
exchange_accounts: 1 row (bpt-demo, bybit/demo)
webhook_secrets: 3 rows (active 2 — Sprint 13 atomic create + rotate 누적)
orders: 1 row (Day 2 stuck pending — Sprint 15 watchdog 대상)

qb_active_orders 0.0
qb_ws_orphan_buffer_size 0.0
qb_ws_reconcile_skipped_total 0.0
qb_ws_duplicate_enqueue_total 0.0
qb_ws_reconnect_total (부재)         ← G.0 P1 #2 정합 (active session 없으면 inc 안 됨, healthy run 의 정상 0)
qb_ws_reconcile_unknown_total (부재) ← 동일
```

**Day 2 stuck pending order (`13705a91-...`) 분석**: Day 2 dev-log §2.4 의 hotfix 후 INSERT + COMMIT 됐으나 state=pending 그대로 14h+. dispatch 또는 worker 처리 누락. 즉 OrderService outer commit fix 외 별도 broken bug 잔존. **Sprint 15 watchdog (codex G.2 P1 #1) follow-up 으로 해소** — `provider.fetch_order` interface + `fetch_order_status_task` Celery + orphan-submitted scanner beat.

ws-stream worker 로그: `trading.run_bybit_private_stream` task registered, ready. active session 없어서 task enqueue 미발생 (정상 no-op).

---

## 4. 라이브 시나리오 — 사용자 브라우저 검증 필요

다음 SLO 는 사용자가 브라우저에서 직접 검증해야 self-assessment 측정 가능:

| #   | 시나리오                                        | Pass 조건                                                                                                  |
| --- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 1   | Strategy create → atomic webhook_secret         | DB webhook_secrets +1 + sessionStorage plaintext 캐시                                                      |
| 2   | TabWebhook rotate                               | DB rotate +1 (active 2개) + amber card plaintext 갱신                                                      |
| 3   | TestOrderDialog (Bybit Demo)                    | Order pending → submitted (REST 30s) → filled / rejected (WS 60s, status="open" 이면 submitted 유지)       |
| 4   | Backtest 422 inline                             | 시작일/종료일 빈 채 submit → "시작일을 입력하세요" inline (mode:'onChange')                                |
| 5   | WS metric                                       | active session 발생 시 `qb_ws_orphan_buffer_size 0` + `qb_active_orders` ↑ ↓ 정상                          |
| 6   | **Phase A — TabWebhook hydration**              | strategy 생성 직후 redirect → URL `?tab=webhook` 자동 진입 + amber card **즉시** 표시 (Day 2 Pain #2 해소) |
| 7   | **Phase A — close → remount 회귀**              | amber card hide → 새로고침 → sessionStorage 정리 검증 → amber card 부재 유지                               |
| 8   | **Phase B — TestOrderDialog WebCrypto**         | (HTTPS 안전 환경) 정상 발송 / (HTTP local 시) "암호화 처리 실패" inline error + dialog 유지                |
| 9   | **Phase C — broker submitted 거짓 filled 회귀** | Bybit Demo 응답이 status="open" 이면 DB `state=submitted` (forced filled 안 됨, exchange_order_id 만 저장) |
| 10  | self-assessment                                 | **사용자 입력 — ≥ 7/10 시 H1→H2 gate 통과**                                                                |

**옵션 drill (시간 남으면)**: `docker compose restart backend-ws-stream` → `qb_ws_reconnect_total` +1 확인 (강제 disconnect 후 supervisor 재연결).

---

## 5. Sprint 15 follow-up (codex G.2 challenge 발견)

### G.2 P1 #1 — submitted 영구 고착 watchdog (silent data corruption 위험)

**상황**: Phase C fix 후 `receipt.status="submitted"` 분기는 attach 만 함. terminal 전이는 WS event 또는 reconciler beat 책임. 그러나:

- `tasks/websocket_task.py:208-250 reconcile_ws_streams` 는 stream 재시작만, orphan submitted Order 전이 안 함
- `reconciliation.py` 는 stream connect/reconnect 시점에만 실행
- OKX 어댑터 (Sprint 7d) 는 private WS 미보유 → WS 경로 자체 없음

**위험**: WS event 유실 / OKX / Bybit 응답 손상 시 DB 가 영원히 submitted 고착 → PnL / kill switch / dogfood report 가 거래소 현실과 다름.

**Sprint 14 시간 한계로 미해결**. dogfood Day 3 의 Bybit Demo + WS 정상 동작 시 영향 적음. 거짓 양성 (filled 위장) 보다 영구 submitted 가 안전 (사용자가 거래소 직접 확인 후 수동 reconcile 가능).

**Sprint 15 fix 계획**:

1. `provider.fetch_order(creds, exchange_order_id)` interface 추가 (Bybit / OKX / Fixture). CCXT `fetch_order(id, symbol)` 호출
2. `tasks/trading.py::fetch_order_status_task` 신규 — terminal 이면 transition. 미체결이면 backoff (15s → 30s → 60s) retry
3. `_async_execute` submitted 분기에서 `fetch_order_status_task.apply_async(countdown=15)` enqueue
4. `tasks/orphan_submitted_scanner` 별도 Celery beat (5분마다) — 30분 이상 submitted 주문 감지 → Slack alert + Sentry warn

**참조**: codex G.2 challenge findings (session `019dca46-ff2b-7a63-bce5-b45f8ed45442`, 2026-04-27).

---

## 6. 머지 권장 결정 (사용자 라이브 검증 후)

- 자동 검증 100% PASS (1185 BE / 243 FE / lint 0 / tsc 0 / build OK)
- codex G.0 P1 3건 + 부수 발견 모두 plan 반영 + 적용
- codex G.2 P1 #1 Sprint 15 이관 (plan 명시)
- Sprint 13 LESSON 적용 (BE TDD commit spy ≥ 2)

**자동 검증 기준 머지 권장**.

라이브 시나리오 6-9 의 결과 + self-assessment ≥ 7/10 확인 시 **H1→H2 gate 통과**.

self-assessment < 7/10 시 Sprint 15 우선순위:

1. submitted watchdog (G.2 P1 #1)
2. Day 2 stuck pending order analysis + cleanup
3. 추가 라이브 발견 사항

---

## 7. 자동 검증 자기 평가 (라이브 미수행)

- Sprint 13 6/10 → Sprint 14 Phase A/B/C 적용 후 자동 검증 100% PASS.
- Phase A hydration race + Phase B P2 4건 + Phase C broker 거짓 양성 모두 fix.
- 라이브 self-assessment 는 사용자 브라우저 실측 후 측정.

---

## 8. 다음 세션 prompt

`~/.claude/plans/h2-sprint-15-prompt.md` 신규 작성 예정 — Sprint 15 우선순위:

1. **submitted watchdog (G.2 P1 #1)** — `provider.fetch_order` + Celery follow-up + orphan scanner. ~3-4h
2. **Day 2 stuck pending order analysis** — service dispatch path 추적 + 별도 broken bug 가능성
3. dogfood Day 3 라이브 결과 반영 (사용자 self-assessment + 발견 Pain)

self-assessment ≥ 7/10 시 H2 본격 진입 — Beta 사용자 onboarding (waitlist) + 추가 도메인 (OKX private WS / partial fill / Sentry / Grafana).
