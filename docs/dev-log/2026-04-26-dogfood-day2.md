# Dogfood Day 2 — Sprint 13 Track UX 검증 (pre-merge)

> 2026-04-26. Sprint 13 Track UX 머지 전 stage/h2-sprint13 local 검증.
> Plan: `~/.claude/plans/sprint-13-cryptic-castle.md` (V2.1)

---

## 0. Sync 진단 결과

| 항목                | 상태                                                                  |
| ------------------- | --------------------------------------------------------------------- |
| branch              | `stage/h2-sprint13` (local checkout)                                  |
| backend uvicorn     | 재기동 ✅ (PID 86853, stage 코드 반영)                                |
| frontend dev server | 재기동 ✅ (`.env.local` 에 `NEXT_PUBLIC_ENABLE_TEST_ORDER=true` 추가) |
| docker compose      | db / redis / worker / beat / ws-stream 5개 Up                         |
| `/health`           | `{"status":"ok"}`                                                     |

---

## 1. 시나리오 6건 검증 결과

| #   | 시나리오                                   | 결과                | 핵심 증거                                                                                                         |
| --- | ------------------------------------------ | ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | Strategy 신규 생성 → atomic webhook_secret | ✅ PASS             | DB `webhook_secrets` row 1건 (atomic auto-issue) + sessionStorage 캐시 plaintext 43자, TTL 29.5분                 |
| 2   | TabWebhook rotate                          | ✅ PASS             | DB 2 rows (1 revoked + 1 active, **rotate Sprint 6 broken bug fix 영구 저장 확정**), amber card + plaintext 일치  |
| 3   | TestOrderDialog (Bybit Demo)               | ✅ PASS (hotfix 후) | **broken bug 1건 발견** + 즉시 fix 후 재검증 → INSERT + COMMIT + 201 + DB row 영구 저장                           |
| 4   | Backtest 422 inline error                  | ✅ PASS             | 빈 시작일/종료일 submit → "시작일을 입력하세요" / "종료일을 입력하세요" inline 즉시 표시 (mode:'onChange' 동작)   |
| 5   | WS metric                                  | ✅ PASS             | `qb_ws_orphan_buffer_size 0.0` + `qb_active_orders 1.0` (시나리오 3 의 INSERT 가 active_orders gauge inc 한 증거) |
| 6   | self-assessment                            | ⏳ 사용자 입력 대기 | (아래 §3 참조)                                                                                                    |

---

## 2. 결정적 발견 — OrderService outer commit 누락 (Sprint 6 broken bug 와 동일 패턴)

### 2.1 발견 경위

시나리오 3 첫 발송 직후 검증:

- BE log: `INSERT INTO trading.orders ...` ✅ + `201 Created` 응답 ✅
- DB count: **0** ❌
- session 종료 시 `ROLLBACK` 으로 INSERT 미저장

### 2.2 Root cause

`backend/src/trading/service.py::OrderService._execute_inner` (line 405) 의
`async with self._session.begin_nested():` 컨텍스트 exit 은 SAVEPOINT release
만 수행. Outer transaction 은 commit 호출 없으면 `get_async_session()` 의
`session.close()` 시 자동 ROLLBACK.

기존 line 405 주석 `"context exit -> commit (lock 해제, row visible)"` 은
**거짓**. begin_nested 의 exit 은 nested savepoint commit 일 뿐, outer
transaction 과 다름.

이는 Sprint 6 의 `WebhookSecretService.issue/rotate` broken bug 와 정확히 동일
패턴. Sprint 13 Phase A.1.1 에서 `WebhookSecretService` 만 fix 했으나
`OrderService` 에도 같은 패턴 잔존했음을 codex G.0 / G.2 / G.4 모두 못 발견.

### 2.3 Fix

```python
# OrderService._execute_inner, after begin_nested 컨텍스트 exit
await self._session.commit()  # outer transaction commit (Sprint 13 hotfix)
```

회귀 mock spy test 추가: `test_order_service_execute_calls_outer_commit` —
`session.commit()` 호출 자체를 강제 검증. db_session fixture 의 same-session
read-back 으로는 broken 못 잡는 한계 회피 (Phase A.1.1 spy 패턴 확장).

### 2.4 검증 (재발송 후)

```
2026-04-26 23:27:25,021 INSERT INTO trading.orders ...
2026-04-26 23:27:25,030 COMMIT          ← Hotfix 적용 후 추가됨
DB row: 13705a91-8a85-4115-a165-484d312b9b35 (BTCUSDT buy 0.001, pending) ✅
qb_active_orders 1.0                     ← Sprint 9 Phase D inc 동작 확정
```

### 2.5 Production 영향 평가

**없음**. dogfood Day 1 에서 webhook_secrets 0건이라 webhook 호출 자체가 한
번도 발생 안 함 → Order INSERT 도 발생 안 함 → broken 영향 없음. Sprint 13
머지 시점에 fix 가 같이 가야 prod webhook 호출 시 정상 동작.

---

## 3. self-assessment

> **본인 매일 사용 가능성: 6 / 10** (사용자 답변 2026-04-26).
>
> H1→H2 gate 통과 조건: ≥ 7/10. **1점 차로 미통과**.
>
> Day 1: 3/10 → Day 2: **6/10 (+3 점프)**. Sprint 13 Track UX 가 통계적으로 의미 있는
> 개선 (Trading entry path 부재 → 정식 entry 추가 + Sprint 6 broken bug 2건 fix).
>
> 6점의 의미:
>
> - Trading entry 자체는 동작 (시나리오 3 PASS)
> - Backtest UX 개선 (시나리오 4 PASS)
> - 매일 사용 까지는 1단계 부족 (TabWebhook hydration / broker 체결 미검증 / 다른 도메인 대기)
>
> **결정**: H1→H2 gate 미통과. PR #78 머지 OK 이지만 **Sprint 14 Track UX-2 우선**
> (Day 2 신규 Pain #2 + G.4 P2 잔존 4건 → dogfood Day 3 재평가).

---

## 4. 발견된 Pain (dogfood Day 2 신규)

| #   | 등급      | 설명                                                                                     | 처리                                                |
| --- | --------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | 🔴 결정적 | `OrderService._execute_inner` outer commit 누락 (Sprint 6 동일 패턴)                     | **즉시 fix** (commit `42c6575`)                     |
| 2   | 🟡 중     | `TabWebhook` mount 시 sessionStorage 캐시 plaintext 미표시 — SSR/CSR hydration race 추정 | Sprint 14 이관: useEffect mount-once read 추가 검토 |
| 3   | 🟢 낮     | `redis_lock_pool_ping_failed action_required=true` startup race (dogfood Day 1 와 동일)  | 기존 Sprint 14 follow-up                            |

---

## 5. Sprint 14 Track 후보 (Day 2 결과 기반)

self-assessment ≥ 7/10 시:

- **Track A (WS 안정화)** — Sprint 12 leftover (prefork+Redis lease, partial fill table, OKX private WS)
- **Track DX (관측성/CI hardening)** — Grafana Cloud, Sentry, build pipeline 강화

self-assessment < 7/10 시:

- **Track UX-2** — Day 2 신규 Pain #2 (TabWebhook sessionStorage hydration) + Sprint 13 G.4 P2 잔존 (4건) 합쳐 진행

공통 hotfix:

- Sprint 13 G.4 P2: WebCrypto error / loading-error UX / API_URL trailing slash / response.text size cap

---

## 6. 메트릭 스냅샷

```
qb_ws_orphan_buffer_size 0.0
qb_ws_reconcile_skipped_total 0.0
qb_ws_duplicate_enqueue_total 0.0
qb_active_orders 1.0
```

active session 부재로 qb_ws_reconnect_total / orphan_event_total 등은 미노출
(counter never-incremented). 정상 no-op.

---

## 7. 6 체크리스트 자동 답변

1. dogfood 며칠째: **2일** (Day 1: 부분 진행 / Day 2: 전체 검증)
2. WS reconnect_count 추이: **0** (active session 부재)
3. Slack alert 횟수: **0**
4. 본인 매일 사용 가능성: **6/10** (Day 1 3 → +3 점프, gate 1점 차 미통과)
5. Beta 사용자 onboarding: **0명** (waitlist 미오픈)
6. 가장 답답했던 pain top 1: **OrderService outer commit broken bug** (사용자 검증 없으면 prod 머지 후 발견됐을 위험) → fix 완료

---

## 8. 머지 권장 결정 — Sprint 14 Track UX-2 우선

- self-assessment **6/10** (gate 미통과)
- **PR #78 머지 OK** — Sprint 13 자체는 진전. Sprint 6 broken bug 두 군데 fix 가
  prod webhook 호출 시점에 필요 (즉, 머지 안 하면 prod webhook 깨진 채 유지).
- **Sprint 14 Track UX-2** (다음 세션) 권장 scope:
  - Day 2 Pain #2: TabWebhook 진입 시 sessionStorage 캐시 plaintext 미표시
  - G.4 P2 잔존 4건: WebCrypto error 처리 / loading-error UX / API_URL trailing slash / response.text size cap
  - broker 체결 검증 (Bybit Demo 인증 + 실제 주문 1건 체결 + filled 전이)
- 다음 세션 prompt: `~/.claude/plans/h2-sprint-14-prompt.md` (작성 예정)

---

## 9. 다음 세션 prompt

`~/.claude/plans/dogfood-day2-prompt.md` 는 이미 작성됨 — Day 2 종료 후 갱신:

- **Sprint 13 부분 진행 결과 요약**
- self-assessment 측정값 + Track 결정
- Sprint 14 진입 시 prompt: `h2-sprint-14-prompt.md`
