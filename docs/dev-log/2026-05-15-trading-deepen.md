# Track B `/deepen-modules trading` audit-only (2026-05-15)

> **Date:** 2026-05-15
> **Branch:** `chore/trading-deepen-audit`
> **Trigger:** CLAUDE.md align audit Track B 후속 — `backend/src/trading/` (5,316L / 32 file) 단독 audit
> **Skill:** `deepen-modules` Iron Law 준수 (1 도메인 = 1 audit)
> **Mode:** **audit-only** (code 0 touch, BL 등재 만, dogfood 직전 risk 회피)

---

## 0. Audit 동기

CLAUDE.md align audit (PR #283) Track B 권고 = trading / backtest / optimizer 3 도메인 별 `/deepen-modules` 호출. 본 audit = trading 단독 (Iron Law). dogfood Day 7 인터뷰 직전 (2026-05-16 = 내일) = code touch X = audit only.

---

## 1. Phase 1 — Module Inventory & Depth Mapping

### 1.1 Top-level inventory (5,316L / 32 file)

| File                                | LOC | Public            | 분류                             |
| ----------------------------------- | --- | ----------------- | -------------------------------- |
| `providers.py`                      | 772 | 10 class + 6 func | **Deep** (Protocol + 4 concrete) |
| `models.py`                         | 528 | 16 class          | Schema/Enum SSOT                 |
| `router.py`                         | 401 | 14 endpoint       | Routing dispatcher               |
| `websocket/bybit_private_stream.py` | 319 | 4 class           | WS handler                       |
| `services/order_service.py`         | 268 | 1 class           | Service                          |
| `kill_switch.py`                    | 263 | 7 class           | **Deep** (multi-strategy SSOT)   |
| `repositories/order_repository.py`  | 236 | 1 class           | Data access                      |
| `websocket/reconciliation.py`       | 225 | 2 class           | Reconciler                       |
| `exceptions.py`                     | 224 | 16 class          | Exception SSOT                   |
| `websocket/state_handler.py`        | 221 | 1 class           | State handler                    |
| `schemas.py`                        | 200 | 14 class + 1 func | Pydantic I/O                     |

### 1.2 Deep / Shallow 1차 분류

- **Deep candidates (audit 제외)**: `providers.py` (Protocol + 4 concrete polymorphism, 정합) + `kill_switch.py` (multi-strategy evaluator pattern, 정합)
- **Shallow candidates**: 0 — `exceptions.py` 16 class = 정당한 분류 (data only)
- **Schema/Routing**: models / schemas / router / dependencies = thin wrapper

### 1.3 Multi-exchange dispatcher

**3-tuple dict dispatch pattern** (`registry.py:35-45`) = `(ExchangeName, ExchangeMode, has_leverage) → factory`. **5 entry**. **if-chain 분산 0건**. ✅ Strategy pattern 정합.

분기 site 2건 만 = `schemas.py:26` (OKX 3-factor auth) + `live_session_service.py:89` (Bybit demo gate).

### 1.4 SSOT 검증

- **Triple SSOT**: 0건 (ExchangeName / OrderSide / OrderType / OrderState / KillSwitchTriggerType 모두 `models.py` 단독 정의 + 다른 file import)
- **Public model overlap**: 0건 (Order / OrderSubmit / OrderRequest = 각각 DB / Provider DTO / HTTP DTO 분리 정합)

**Phase 1 결론: trading architectural quality 양호** — Deep module 패턴 잘 적용, dispatch dict, SSOT 중복 0.

---

## 2. Phase 2 — Locality & Coupling Analysis

### 2.1 Co-change cluster (3 month)

| File             | 변경 수 | Cluster                                   |
| ---------------- | ------- | ----------------------------------------- |
| `service.py`     | 15      | service ↔ repository ↔ providers ↔ models |
| `repository.py`  | 11      | (위와 동일)                               |
| `providers.py`   | 11      | (위와 동일)                               |
| `models.py`      | 9       | (위와 동일)                               |
| `kill_switch.py` | 8       | (위와 동일)                               |

**core 4 (service/repository/providers/models) tight coupling = 정합** (도메인 변경 자연 cascade). 분산 isolated subsystem 발견 0.

### 2.2 tasks/trading.py vs trading/ 분리 검증

`tasks/trading.py` 721L. trading 도메인 import 6건 (encryption / exceptions / models / providers / registry / order_repository) — **stable interface 만 import** + 0 circular. Celery layer 정합 분리.

### 2.3 Test coverage (critical gap 발견)

| subsystem              | LOC             | test coverage                 | risk |
| ---------------------- | --------------- | ----------------------------- | ---- |
| `services/`            | 611             | tested (3 service)            | 🟢   |
| `repositories/`        | 782             | tested (4 repo)               | 🟢   |
| **`websocket/`**       | **904 (19.4%)** | **~4%** (2/48 file reference) | 🔴   |
| **`registry.py`**      | **64**          | **0%**                        | 🔴   |
| **`webhook.py`**       | **81**          | **0%**                        | 🔴   |
| `fees.py`              | 55              | 0%                            | 🟡   |
| `reconcile_fetcher.py` | 116             | 0%                            | 🟡   |

총 test:prod ratio = 9,470 : 5,316 = **1.78:1** (전체 양호) 인데 **websocket + dispatch + webhook + fees 4 critical subsystem = 0~4%** 분산.

### 2.4 추가 minor 신호

- **StreamReconciler protocol** websocket 안 별도 정의 (services/protocols.py 외부) = **2x SSOT 소스** (low risk, optional 통합)
- **router.py 401L 14 endpoint 단일 file** — sub-router 분리 가능 (low priority)

---

## 3. Phase 3 — Grilling 결정

### 3.1 ROI 평가 (5 차원)

| 후보                                    | Severity | Locality gain | Leverage | Risk | Test coverage | ROI                 |
| --------------------------------------- | -------- | ------------- | -------- | ---- | ------------- | ------------------- |
| Deep module 더 deep화 (providers split) | 1        | 1             | 1        | 5    | 70%           | **0.6** (X)         |
| websocket test coverage boost           | 9        | 0             | 7        | 2    | 4%            | **0.32** (gap 큼)   |
| registry/webhook/fees test 추가         | 7        | 0             | 5        | 1    | 0%            | **0.0** (gap 최대)  |
| StreamReconciler protocols.py 통합      | 2        | 2             | 1        | 1    | 100%          | **5.0** (low value) |
| router.py sub-router split              | 2        | 3             | 1        | 2    | 80%           | **2.4** (low value) |

### 3.2 Skill STOP condition 매치

> **STOP**: 모든 후보의 test coverage < 70% → "test 우선" 권고로 종료

Deep module deepening 후보 모두 **test coverage <70% subsystem 의존**. skill 명시 = "Deep module 을 더 deep화하지 말 것 — over-engineering 함정". 정합 = **trading audit 종료 + test 우선 권고**.

### 3.3 사용자 결정 (2026-05-15)

★★★★★ "BL 등재 + trading audit 종료" 채택. BL-308/309 신규 P1/P2 등재. StreamReconciler / router split = ROI 낮음 + audit 외 (사용자 결정).

---

## 4. Phase 4 — BL 등재

### BL-308 (P1)

- websocket subsystem test coverage 4% → ≥70% boost
- 904 LOC 도메인 19.4% / silent failure risk (order state cascade 미검증)
- est L (12-16h)
- BL-024 real_broker E2E 묶음 권고

### BL-309 (P2)

- registry / webhook / fees 0% → ≥80% test 추가
- 200L 핵심 dispatch 미검증 / 신규 거래소 추가 시 silent failure
- est M (4-6h)
- BL-308 묶음 권고

---

## 5. 결론

**trading 도메인 architectural quality 양호** — Deep module + dispatch dict + 0 SSOT 중복. **진짜 risk = test coverage gap**.

audit-only mode = code 0 touch. BL-308/309 등재 만 = 다음 sprint prep (Day 7 인터뷰 후 Sprint 61 분기 결정 시 우선순위 input).

**skill 영구 검증**: deepen-modules Iron Law (Deep module 더 deep화 X) + STOP condition (test coverage <70% = test 우선) 정합 작동. **trading audit single domain pilot 완료 (성공 결론)**.

---

## 6. 다음 audit 권고

- **다음 session**: `/deepen-modules backtest` (별도 호출, Iron Law 준수). backtest 4,140L / 17 file (service.py 889L + v2_adapter.py 782L).
- **그 다음**: `/deepen-modules optimizer` (Sprint 54-56 신설 직후 = §7.5 신규 도메인 deepening trigger).
- **본 audit branch**: `chore/trading-deepen-audit` PR 사용자 squash merge 의무.

---

## 7. Self-assessment

**8/10** (3-line 근거):

1. **Iron Law + skill STOP condition 정합** — 후보 ROI 평가 + Deep module 더 deep화 X 결론 + test coverage <70% = test 우선 권고. skill 명세 100% 준수.
2. **architectural debt 적음 결론 영구 기록** — trading 도메인이 의외로 양호하다는 결론 = 향후 audit waste 방지. dispatch dict + 0 SSOT 중복 + Deep module 정합 = 장기 자산.
3. **Test coverage gap 발견 = critical risk surface** — websocket 4% / registry+webhook 0% = silent failure risk. dogfood 직전 차단 path 마련.

**감점 2점:** Phase 2 추가 측정 (multi-file PR pattern 30-day window 안 0건 = 추정만, git-blame 깊이 검증 X). 향후 BL-308 sprint 진입 시 정확한 line-level coverage 측정 의무.
