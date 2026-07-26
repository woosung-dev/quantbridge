# ADR-018: Sprint 12 WebSocket Supervisor + Sprint 15-A/B Architecture Cleanup

> **상태:** 사후 기록 (Sprint 12 = 2026-04-25 / Sprint 15 = 2026-04-28)
> **관련 PRs:** Sprint 12 stage `74fd00a` / Sprint 15 stage TBD
> **관련 LESSON:** LESSON-019 (broken-bug 3rd 재발 → backend.md 트랜잭션 commit 보장 §3 승격)
> **상위 문서:** [`04_architecture/system-architecture.md`](../04_architecture/system-architecture.md), [`04_architecture/data-flow.md`](../04_architecture/data-flow.md)
> **합본 이유:** Sprint 12 의 WS 도입 결정이 ADR 누락 상태였고, Sprint 15-A/B 가 그 후속 cleanup 이라 한 묶음으로 기록

---

## 1. 배경

Sprint 12 는 dogfood 가속을 목적으로 codex Generator-Evaluator 6 게이트 (G0~G4 + revisit, 2.6M tokens) 를 적용하여 24 critical 사전 차단했다. 결과물 (Bybit Private WS supervisor + reconnect + reconcile + Slack alert) 은 머지됐으나 **ADR 번호가 부여되지 않은 상태**로 남았다. 동시에 Sprint 14 머지 직후의 아키텍처 정합성 리뷰 (2026-04-28) 가 두 가지 정리 대상을 발견했다:

1. `backend/src/exchange/` = 4월 15일 Phase 0 스캐폴딩 시 만들어진 8 파일 12 라인 stub. `trading/` 모듈이 거래소 책임 (계정 등록 / 주문 / WS) 을 모두 흡수하면서 dead module 화. 3 sprint 이상 동결.
2. service mutation commit 누락 broken bug 3 회 재발 (Sprint 6 webhook → Sprint 13 OrderService → Sprint 15-A `register()`) — LESSON-019 로 승격.

---

## 2. 결정 요약

| #   | 결정                                                                                                    | 적용 sprint           |
| --- | ------------------------------------------------------------------------------------------------------- | --------------------- |
| D-1 | Bybit Private WS supervisor 패턴 (1→30s exponential reconnect, prefork-incompatible 영역 `--pool=solo`) | Sprint 12 Phase C     |
| D-2 | StateHandler orderLinkId UUID 우선 lookup + orphan_buffer FIFO max 1000                                 | Sprint 12 Phase C     |
| D-3 | Reconciler terminal-evidence-only transition + CCXT unified status 매핑                                 | Sprint 12 Phase C     |
| D-4 | Slack alert per-call httpx + BoundedSemaphore(8) + 15s wait_for + best-effort module-level set          | Sprint 12 Phase A     |
| D-5 | OrderSubmit.client_order_id → CCXT params (orderLinkId/clOrdId) UUID 매핑                               | Sprint 12 Phase C-pre |
| D-6 | `backend/src/exchange/` 도메인 폐기 — `trading/` 흡수로 dead module                                     | Sprint 15-B           |
| D-7 | service mutation commit-spy 회귀 테스트 의무화 (`backend.md` §트랜잭션 commit 보장)                     | Sprint 15-A           |

---

## 3. D-1 ~ D-5: Sprint 12 WebSocket 인프라

### 3.1 Supervisor 패턴

`BybitPrivateStream` 은 단일 task 가 아닌 supervisor + child task 구조. supervisor 는 ConnectionClosed / heartbeat 종료 / auth window 만료 시 1→30s exponential backoff 으로 자동 재시작. `--pool=solo` 강제는 prefork worker 의 `worker_shutdown` hook 이 main process 만 신호 받기 때문 (자식 프로세스의 `_STOP_EVENTS` 미연결 → 그래스풀 종료 실패).

### 3.2 OrderLinkId 매핑

CCXT 어댑터 (`BybitDemo/BybitFutures/Okx`) 가 `params={orderLinkId: str(Order.id)}` 로 UUID 전달. WebSocket order event 가 들어오면 StateHandler 가 orderLinkId UUID 로 local DB row 정확 매핑. orphan event (UUID 없음 또는 미상 매핑) 는 FIFO buffer (max 1000) 로 임시 보존, Reconciler 5분 beat 가 fetchOrder 로 evidence 수집.

### 3.3 Reconciler

Terminal-evidence-only: WebSocket 가 끊긴 동안 발생한 fill/cancel 을 CCXT REST `fetchOrder` 로 확정. unified status 가 `"closed"` + `cumExecQty == quantity` → filled, `"canceled"` → cancelled 등 명확 매핑만 적용. ambiguous (`"open"`, `"submitted"`) 는 손대지 않음.

### 3.4 Slack alert

KillSwitch.ensure_not_gated() 가 event save 직후 alert task 발송. per-call httpx client (FastAPI lifecycle 와 독립) + BoundedSemaphore(8) 로 동시성 제한 + 15s `asyncio.wait_for` timeout. best-effort policy — module-level `_PENDING_ALERTS` set 으로 task strong ref 보존, alert 실패가 KillSwitch 로직을 막지 않음.

### 3.5 신규 metrics

- `qb_ws_orphan_event_total{exchange,reason}`
- `qb_ws_orphan_buffer_size{exchange}`
- `qb_ws_reconcile_unknown_total{exchange}`
- `qb_ws_reconcile_skipped_total{exchange,reason}`
- `qb_ws_duplicate_enqueue_total{exchange}`
- `qb_ws_reconnect_total{exchange,reason}`

---

## 4. D-6: `backend/src/exchange/` 폐기

### 4.1 사실

| 파일              | 라인 | 내용                                         |
| ----------------- | ---- | -------------------------------------------- |
| `__init__.py`     | 1    | 빈 docstring                                 |
| `dependencies.py` | 1    | 빈 docstring                                 |
| `exceptions.py`   | 1    | 빈 docstring                                 |
| `models.py`       | 1    | 빈 docstring                                 |
| `repository.py`   | 1    | 빈 docstring                                 |
| `router.py`       | 5    | `APIRouter(prefix="/exchange")` (등록 안 됨) |
| `schemas.py`      | 1    | 빈 docstring                                 |
| `service.py`      | 1    | 빈 docstring                                 |

`grep -rn "from src\.exchange\|import src\.exchange"` 결과 0건. `main.py` 가 router 미등록.

### 4.2 사유

거래소 관련 모든 책임이 `trading/` 모듈에 흡수됨:

- `trading/models.py::ExchangeAccount` — 계좌 모델
- `trading/service.py::ExchangeAccountService` — 계좌 등록 / credentials
- `trading/providers.py` — Bybit/OKX/Binance 어댑터
- `trading/websocket/` — Sprint 12 Private WS

별도 `exchange/` 도메인 모듈 유지는 잘못된 future-proofing. 4월 15일 Phase 0 Sprint 1~3 진행 도중 trading 으로 단일 도메인 통합 결정이 묵시적으로 내려졌으나 빈 폴더가 동결됨.

### 4.3 결정

**삭제** (Sprint 15-B). 향후 별도 모듈이 필요하면 그때 추가.

---

## 5. D-7: 트랜잭션 commit 보장 (LESSON-019)

### 5.1 패턴 발견

`get_async_session()` (`backend/src/common/database.py:26`) 의 `expire_on_commit=False` + autocommit OFF 라 service 가 명시적 `commit()` 호출 안 하면 request 종료 시 ROLLBACK. `db_session` fixture 기반 통합 테스트는 conftest 트랜잭션 안에서 read-your-writes 로 통과 = false-positive.

| sprint      | 위반 메서드                         | 발견 경로                              |
| ----------- | ----------------------------------- | -------------------------------------- |
| Sprint 6    | `WebhookSecretService.issue/rotate` | dogfood Day 1 webhook_secrets 0건      |
| Sprint 13   | `OrderService.execute` outer commit | dogfood Day 2 첫 webhook 호출          |
| Sprint 15-A | `ExchangeAccountService.register`   | Sprint 14 머지 후 아키텍처 정합성 리뷰 |

3회 재발 = 코드 리뷰 + 통합 테스트만으로는 차단 안 됨 실측 증명.

### 5.2 결정

`backend.md` §트랜잭션 commit 보장 신규 섹션 승격. **모든 service mutation 메서드는 AsyncMock spy 회귀 테스트 1건 의무**. 표준 reference: `backend/tests/trading/test_webhook_secret_commits.py` 의 3 spy 테스트.

---

## 6. 추적

- Sprint 12 supervisor / reconcile 의 prefork+Redis lease 패턴 확장 → Sprint 13+ 이관 (현재 `--pool=solo` 우회)
- partial fill cumExecQty tracking → Sprint 13+ 이관
- auth circuit breaker (1h TTL) → Sprint 13+ 이관
- OKX Private WS 어댑터 → Sprint 13+ 이관
- service mutation spy backfill — Sprint 15+ dette 항목으로 추적 (모든 기존 service 메서드 audit)

---

## 7. 변경 이력

- **2026-04-28** — 초안 작성 (Sprint 15-B 머지 직전, Sprint 12 사후 ADR + Sprint 15 cleanup 묶음)
