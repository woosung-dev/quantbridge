# Architecture Conformance Audit — 영구 체크리스트

> **목적:** docs/04_architecture/ + .ai/rules/ 가 정의한 아키텍처 / 디자인 패턴이 실제 코드에서 지켜지고 있는지 검증하는 **재실행 가능 체크리스트**.
>
> 매 sprint 회고 또는 Beta 오픈 전 1회 본 문서 전체를 1 hop 으로 재실행 → 정합성 점수 추적.
>
> **마지막 audit:** 2026-05-02 (Sprint 19 종료 후) — 위반 0 / OK 16 / TBD 0 = **100% 정합성** (15 → 16 항목, F17 신규 + A2 ✅ 승격).
> **다음 audit 권장:** Sprint 20+ Beta 오픈 진입 직전.

---

## 빠른 요약 (Sprint 19 갱신)

| 카테고리                              | 항목    | OK     | TBD    | 위반  |
| ------------------------------------- | ------- | ------ | ------ | ----- |
| A. 트랜잭션 / 도메인 boundary         | A1~A4   | 4      | 0      | 0     |
| B. 보안 / 시크릿 / 환경변수           | B5~B8   | 3      | 1 (B5) | 0     |
| C. Async / 비동기 작업                | C9~C10  | 2      | 0      | 0     |
| D. Frontend 패턴                      | D11~D13 | 3      | 0      | 0     |
| E. 금융 정밀도                        | E14~E15 | 2      | 0      | 0     |
| F. Celery prefork-safe (Sprint 18+19) | F17~F18 | 2      | 0      | 0     |
| **합계**                              | **17**  | **16** | **1**  | **0** |

**결론:** Sprint 18+19 의 BL-080 architectural fix + BL-081/083/084/085 technical debt + Sprint 16 BL-010 commit-spy backfill 완료로 정합성 점수 86% → **94% (16/17 OK + 1 TBD)** 도달. 잔여 TBD 1 건 = B5 (PINE_ALERT_HEURISTIC_MODE env 사용 ADR 신설, [BL-050](../REFACTORING-BACKLOG.md#bl-050)) — Sprint 20+ 정리 sprint 시 해소.

---

## A. 트랜잭션 / 도메인 boundary

### A1 — 모든 mutation 메서드는 `commit()` 호출

**검증 출처:** [`.ai/stacks/fastapi/backend.md`](../../.ai/stacks/fastapi/backend.md) §트랜잭션 commit 보장 / [LESSON-019](../../.ai/project/lessons.md#lesson-019)
**근거:** Sprint 6 webhook_secret → Sprint 13 OrderService → Sprint 15 ExchangeAccount = 동일 broken bug 3 회 재발

**검증 명령어:**

```bash
# Service mutation 메서드 추출
rg -n 'async def (create|update|delete|issue|rotate|register|execute|submit)' \
  backend/src/*/service.py

# 해당 메서드 안 commit() 호출 확인
rg -nA 30 'async def create' backend/src/strategy/service.py | grep -E 'commit|return'
```

**기대:** 모든 mutation 메서드의 return 직전에 `await self._repo.commit()` 또는 `await self._session.commit()`.

**2026-04-30 결과:** ✅ OK (8 service.py 검증)

- trading: register/issue/rotate/execute ✓
- strategy: create/update/delete ✓
- backtest: submit ✓
- waitlist: submit_application ✓

---

### A2 — Mutation 메서드별 commit-spy 회귀 테스트

**검증 출처:** LESSON-019, 표준 reference [`backend/tests/trading/test_webhook_secret_commits.py`](../../backend/tests/trading/test_webhook_secret_commits.py)

**검증 명령어:**

```bash
# 도메인별 spy 테스트 존재 여부
ls backend/tests/*/test_*_commits.py

# trading 외 도메인의 AsyncMock spy 패턴 사용 여부
rg -l 'repo.commit.assert_awaited_once|AsyncMock.*commit' backend/tests/
```

**기대:** 6 도메인 (trading / strategy / backtest / waitlist / stress_test / market_data) 모두 mutation 메서드별 spy 테스트 존재. AsyncMock spec 기반.

**2026-04-30 결과:** 🟡 TBD — trading 만 충실 (6 spy). backtest / strategy / waitlist 도메인은 db_session fixture 기반만, spy 회귀 테스트 미발견.

**2026-05-02 결과 (Sprint 16 BL-010 ✅ Resolved):** ✅ **OK** — 4 도메인 commit-spy backfill 완료 (Strategy 4 spy / Backtest 3 spy / Waitlist 2 spy + autouse rate-limiter override / StressTest 2 spy = 11 spy 추가). codex G.0 audit 결과 5 도메인 (Strategy / Backtest / Waitlist / Optimizer / StressTest) 모두 commit 호출 OK = broken bug 0건 confirmed. Optimizer 는 H1 미구현 (스캐폴드만) → 별도 BL.

---

### A3 — `backend/src/exchange/` dead module 부재

**검증 출처:** [ADR-018](../dev-log/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) Sprint 15-B cleanup

**검증 명령어:**

```bash
test -d backend/src/exchange && echo "VIOLATION" || echo "OK"
rg -l 'from src.exchange|import src.exchange' backend/src/ frontend/src/
```

**기대:** 디렉토리 부재 + 0 import.

**2026-04-30 결과:** ✅ OK — 디렉토리 없음, import 0 건.

---

### A4 — Layered architecture (Service → Repository 만 DB 접근)

**검증 출처:** [`docs/02_domain/domain-overview.md`](../02_domain/domain-overview.md) §3 / [`.ai/stacks/fastapi/backend.md`](../../.ai/stacks/fastapi/backend.md) 3-Layer 구조

**검증 명령어:**

```bash
# Service 에서 AsyncSession import 또는 raw SQL 호출 — 위반
rg -n 'AsyncSession|session.execute|session.exec|text\(' backend/src/*/service.py

# Repository 에 SQL 전담 — 정상
rg -n 'session.execute|text\(' backend/src/*/repository.py | wc -l
```

**기대:** service.py 에 0 건. repository.py 만 SQL 보유.

**2026-04-30 결과:** ✅ OK

- service.py 에서 SQL/AsyncSession 직접 사용: 0 건
- repository.py 의 raw SQL: 3 곳 (market_data gap detection, backtest advisory lock, auth.models server_default) — 모두 적절

---

## B. 보안 / 시크릿 / 환경변수

### B5 — `os.environ` / `os.getenv` 직접 호출 (settings 외부)

**검증 출처:** [`.ai/common/global.md`](../../.ai/common/global.md) §4 환경 변수 관리

**검증 명령어:**

```bash
rg -n 'os\.(environ|getenv)' backend/src/ \
  | grep -v 'config.py' | grep -v '__pycache__'
```

**기대:** config.py 외부에서 0 건. (`pydantic_settings.BaseSettings` 객체만 사용)

**2026-04-30 결과:** 🟡 TBD — 1 건 발견:

- `backend/src/strategy/pine_v2/alert_hook.py:216` — `os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")`
- 컨텍스트: Pine 전용 sandbox runtime heuristic. lazy read 명시 (pytest monkeypatch 호환성).
- 평가: 정책 범위 내 허용 — Pine 샌드박스 특수성 + 1 건 제한.

**처리:** [BL-050](../REFACTORING-BACKLOG.md#bl-050) 등록 — ADR 신설 또는 주석 강화로 정당성 명시.

#### B5-ADR — `PINE_ALERT_HEURISTIC_MODE` env 직접 read 정당성 (Sprint 46, 2026-05-09)

**상태:** ✅ Accepted — Sprint 46 W1 (BL-050 resolved)

**결정:** `pine_v2/alert_hook.py` 의 `os.environ.get("PINE_ALERT_HEURISTIC_MODE", ...)` 1 건은 `pydantic_settings.BaseSettings` 마이그레이션 **대상 외**로 유지한다.

**근거 (3):**

1. **Test isolation 요구**: alert heuristic 은 단일 strategy 실행 내에서 mode flip 시나리오 (`strict` ↔ `lenient`) 를 monkeypatch 로 검증한다. `BaseSettings` 는 import time 에 1회 freeze 되므로 `pytest.MonkeyPatch.setenv` 가 무효화된다.
2. **Sandbox 격리**: Pine v2 runtime 은 의도적으로 `Settings()` 의존성을 갖지 않는다 (Tier-0 layer 8 의 격리 원칙, [Sprint 8a Tier-0 후속](../../.ai/project/lessons.md)). settings 주입은 sandbox boundary 위반.
3. **범위 제약**: 1 변수 / 1 호출처 / fallback `"strict"` (안전한 default). 정책 범위 외 확산 위험 없음.

**제약:**

- 추가 env 직접 read 발생 시 **ADR 갱신 의무** (이 ADR 가 1 건 한정).
- Pine v2 외 모듈에서 `os.environ` 직접 호출 발견 시 B5 검증 명령어가 alert.

**대안 검토:**

- `Settings` 주입: test isolation 깨짐 (위 1).
- `functools.lru_cache(maxsize=1)` 래퍼: monkeypatch 후 cache invalidate 추가 step 필요 → 가독성 저하.
- env injection via fixture parameter: alert_hook signature 변경 → caller 4+ 곳 수정 → blast radius 증가.

**Related:** ADR-013 (Mutation policy), [BL-050](../REFACTORING-BACKLOG.md#bl-050)

---

### B6 — AES-256 (Fernet) 암호화 적용

**검증 출처:** CLAUDE.md "거래소 API Key는 AES-256 암호화 저장 (평문 금지)" / [`docs/02_domain/entities.md`](../02_domain/entities.md) ExchangeAccount

**검증 명령어:**

```bash
rg -n 'api_key_encrypted|api_secret_encrypted|passphrase_encrypted' \
  backend/src/trading/models.py
rg -n 'class EncryptionService|Fernet' backend/src/trading/encryption.py
```

**기대:** 3 필드 모두 `bytes` + EncryptionService Fernet 사용.

**2026-04-30 결과:** ✅ OK — `api_key_encrypted: bytes` / `api_secret_encrypted: bytes` / `passphrase_encrypted: bytes | None` (OKX 지원). EncryptionService 존재.

---

### B7 — `.env.example` SSOT 정합성

**검증 출처:** [`.ai/common/global.md`](../../.ai/common/global.md) §4

**검증 명령어:**

```bash
# .env.example 변수 추출
grep -E '^[A-Z_]+=' .env.example | cut -d= -f1 | sort > /tmp/env_keys.txt

# 코드에서 settings 필드 추출 (pydantic-settings)
rg -nE 'class Settings|^\s+[a-z_]+:.*Field' backend/src/core/config.py
```

**기대:** config.py 의 모든 settings 필드가 .env.example 에 정의 (또는 default 값 가짐).

**2026-04-30 결과:** ✅ OK — 16 변수 정합 (BACKTEST_STALE_THRESHOLD_SECONDS / BYBIT_DEMO_API_KEY_TEST / CLERK_SECRET_KEY 등 모두 정의).

---

### B8 — `eval()` / `exec()` 사용처

**검증 출처:** CLAUDE.md "Pine Script → Python 변환 시 `exec()`/`eval()` 절대 금지" / [ADR-003](../dev-log/003-pine-runtime-safety-and-parser-scope.md)

**검증 명령어:**

```bash
rg -nE '\beval\(|\bexec\(' backend/src/ frontend/src/ \
  | grep -v 'eval_expr\|_eval_' | grep -v '__pycache__'
```

**기대:** 0 건 (Pine interpreter 의 `_eval_expr()` 메서드는 AST 기반 안전 평가 — 직접 eval 사용 안 함).

**2026-04-30 결과:** ✅ OK — 위험 사용 0 건.

---

## C. Async / 비동기 작업

### C9 — FastAPI handler 가 무거운 작업 직접 실행 안 함

**검증 출처:** [`docs/04_architecture/system-architecture.md`](system-architecture.md) §4 / CLAUDE.md "백테스트/최적화는 반드시 Celery 비동기"

**검증 명령어:**

```bash
# Backtest router 가 직접 vectorbt 호출하는지
rg -nE 'run_backtest|vectorbt\.|portfolio\.from_signals' backend/src/backtest/router.py

# Service 가 dispatcher 위임하는지
rg -n 'TaskDispatcher|dispatch_backtest' backend/src/backtest/service.py
```

**기대:** router.py 에서 vectorbt 호출 0 건 + service.py 에서 dispatcher 호출.

**2026-04-30 결과:** ✅ OK — `submit_backtest` 가 202 Accepted 반환 + service.submit() → TaskDispatcher.dispatch_backtest_execution() 위임.

---

### C10 — Celery task module-level engine init 금지 (prefork-safe)

**검증 출처:** CLAUDE.md "Celery prefork-safe" / Sprint 4 D3 교훈

**검증 명령어:**

```bash
# Module-level create_async_engine 호출
rg -nE '^[a-z_]+ = create_async_engine|^_engine = create_async_engine' \
  backend/src/tasks/

# Lazy init 함수 패턴
rg -n 'def create_worker_engine_and_sm' backend/src/tasks/
```

**기대:** module-level 0 건 + lazy init 함수 존재.

**2026-04-30 결과:** ✅ OK — `backend/src/tasks/backtest.py:31-40` `create_worker_engine_and_sm()` 매 task 마다 신규 생성. module-level 0 건.

---

## D. Frontend 패턴

### D11 — `useEffect` deps 에 unstable 객체 참조 금지

**검증 출처:** [LESSON-004](../../.ai/project/lessons.md#lesson-004) (CPU 100% set-state-in-effect)

**검증 명령어:**

```bash
# ESLint react-hooks rule 적용 여부
rg -n 'react-hooks/(exhaustive-deps|set-state-in-effect)' frontend/eslint.config.*

# disable 시도 (위반 신호)
rg -nE '// eslint-disable.*react-hooks|/\* eslint-disable.*react-hooks' frontend/src/
```

**기대:** ESLint rule 활성 + disable 0 건.

**2026-04-30 결과:** ✅ OK — `react-hooks/exhaustive-deps` 활성, disable 0 건. `equity-chart.tsx` 가 useMemo + ref + primitive deps 정석 패턴 사용.

---

### D12 — onSuccess plaintext → sessionStorage 캐시 (react-query cache 격리)

**검증 출처:** Sprint 13 패턴, Sprint 14 useSyncExternalStore 보강

**검증 명령어:**

```bash
# webhook-secret-storage 모듈 존재
test -f frontend/src/features/strategy/webhook-secret-storage.ts && echo OK

# react-query cache 가 webhook_secret 포함하는지 (sanitized 검증)
rg -n 'webhook_secret' frontend/src/features/strategy/use-strategies.ts
```

**기대:** sessionStorage 모듈 존재 + react-query cache 에는 sanitized response (webhook_secret 미포함).

**2026-04-30 결과:** ✅ OK — webhook-secret-storage.ts 의 `cacheWebhookSecret` / `subscribeWebhookSecret` 패턴 준수. react-query cache 는 StrategyResponse (no webhook_secret).

---

### D13 — `process.env.NEXT_PUBLIC_API_URL` lazy 패턴 (top-level throw 금지)

**검증 출처:** Sprint 14 codex G.0 P1 #3 (`lib/api-base.ts::getApiBase()`)

**검증 명령어:**

```bash
# Module top-level throw 패턴
rg -nE '^throw|process\.env\.NEXT_PUBLIC_API_URL.*throw' frontend/src/

# api-base helper 존재
test -f frontend/src/lib/api-base.ts && echo OK
rg -n 'export function getApiBase' frontend/src/lib/api-base.ts
```

**기대:** module top-level throw 0 건 + getApiBase() helper 사용.

**2026-04-30 결과:** ✅ OK — api-base.ts:13-33 lazy + 1회 console.error + fallback `http://localhost:8000` + trailing slash strip. 3 사용처 (api-client / test-order-dialog / tab-webhook) 통합.

---

## E. 금융 정밀도

### E14 — Decimal-first 합산 (`Decimal(str(a + b))` 금지)

**검증 출처:** CLAUDE.md "Decimal-first 합산" / Sprint 4 D8 교훈

**검증 명령어:**

```bash
# 위반 패턴: float 공간 합산 후 Decimal 변환
rg -nE 'Decimal\(str\([a-z_]+\s*\+\s*[a-z_]+\)\)' backend/src/

# 정상 패턴: 각자 Decimal 변환 후 합산
rg -nE 'Decimal\(str\([a-z_]+\)\)\s*\+\s*Decimal\(str' backend/src/
```

**기대:** 위반 0 건 + 정상 패턴 다수.

**2026-04-30 결과:** ✅ OK — `backend/src/backtest/engine/trades.py:75` `Decimal(str(row["Entry Fees"])) + Decimal(str(row["Exit Fees"]))` 패턴. 위반 0 건.

---

### E15 — 금액 / 가격 / 수량 필드는 `Decimal` (float 금지)

**검증 출처:** CLAUDE.md "금융 숫자는 `Decimal` 사용 (float 금지)" / [`docs/02_domain/domain-overview.md`](../02_domain/domain-overview.md) §4.5

**검증 명령어:**

```bash
# 모델의 Numeric 컬럼
rg -nE 'Numeric\(\d+,\s*\d+\)' backend/src/*/models.py

# 금융 필드가 float 으로 선언됐는지 (위반 신호)
rg -nE '(price|quantity|amount|leverage|fee).*float' backend/src/*/models.py
```

**기대:** Numeric(N, M) 다수 + 금융 필드의 float 선언 0 건.

**2026-04-30 결과:** ✅ OK — Order 모델의 quantity / price / filled_price / filled_quantity / leverage 모두 `Decimal + Numeric(18, 8)`. float 사용은 Pine rendering NaN 좌표 (gui 시각화) + config 임시 변수만.

---

## F. Celery prefork-safe (Sprint 18+19 신규)

### F17 — `run_in_worker_loop` 의무 (Sprint 18 BL-080)

**검증 출처:** [`docs/04_architecture/system-architecture.md`](system-architecture.md) §7.5 / [`backend/src/tasks/_worker_loop.py`](../../backend/src/tasks/_worker_loop.py) / [Sprint 18 dev-log](../dev-log/2026-05-02-sprint18-bl080-architectural.md)
**근거:** Sprint 17 의 `asyncio.run()` per task 패턴 + module-level async state = 2nd+ task fail (asyncpg `BaseProtocol._on_waiter_completed` stale loop binding). Option C 영속 `_WORKER_LOOP` 통일.

**검증 명령어:**

```bash
# task entry point 의 asyncio.run() 직접 호출 — 2건만 허용
rg -n "asyncio\.run\(" backend/src/tasks/

# _worker_loop.py 의 fallback (1건) + celery_app.py:_on_worker_ready (master 전용 1건) = 정상
# 그 외 위치에서 asyncio.run 발견 시 위반
```

**기대:** asyncio.run 호출 = 2 정확. `_worker_loop.py:138` (fallback) + `celery_app.py:_on_worker_ready` (master 전용 codex G.0 P1 #5).

**2026-05-02 결과:** ✅ **OK** — 9 task entry point (orphan_scanner / trading × 2 / websocket_task × 2 / backtest × 2 / funding / dogfood_report / stress_test_tasks) 모두 `run_in_worker_loop()` 사용. asyncio.run 호출 2건 (fallback + master) 만.

**라이브 evidence:** Sprint 18 후 mixed 30 tasks → 30/30 succeeded by single ForkPoolWorker-2 / 0 raised (Sprint 17 1/3 success → Sprint 18 30/30).

---

### F18 — Module-level asyncio primitive 차단 (Sprint 19 BL-084)

**검증 출처:** [`backend/tests/tasks/test_no_module_level_loop_bound_state.py`](../../backend/tests/tasks/test_no_module_level_loop_bound_state.py) / [Sprint 19 dev-log](../dev-log/2026-05-02-sprint19-technical-debt.md)
**근거:** Sprint 18 영속 `_WORKER_LOOP` 통일로 module-level `asyncio.Semaphore/Lock/Event/Queue` 가 안전해졌으나, 신규 PR 의 추가 패턴 회귀 차단 위해 AST audit gate.

**검증 명령어:**

```bash
# AST audit 실행 — 신규 violation 발견 시 fail
uv run pytest backend/tests/tasks/test_no_module_level_loop_bound_state.py -v
```

**기대:** 4/4 PASSED. allowlist (현재 `_SEND_SEMAPHORE` 1개) 외 위반 0.

**2026-05-02 결과:** ✅ **OK** — `test_no_unallowed_module_level_asyncio_primitives` + `test_audit_targets_cover_known_modules` + `test_audit_detects_synthetic_violation` + `test_allowlisted_modules_have_documented_violations` 모두 통과. allowlist `_SEND_SEMAPHORE` (alert.py:49) 만.

**확장 시 절차:** 새 module-level asyncio object 추가 의도 시 (1) test_no_module_level_loop_bound_state.py 의 `_ALLOWLIST` 갱신 + (2) `.ai/stacks/fastapi/backend.md` §11.2 에 안전 사유 명시 + (3) PR 리뷰 의무.

---

## 추가 검증 권장 (P3)

다음 항목은 본 audit 범위 외이지만 정합성 강화 후보:

| #   | 항목                                         | 검증 방법                                                      | 우선순위           |
| --- | -------------------------------------------- | -------------------------------------------------------------- | ------------------ |
| F1  | Clerk JWT 모든 보호 endpoint 적용            | `rg -nL 'Depends\(get_current_user\)' backend/src/*/router.py` | P3                 |
| F2  | Webhook Svix 서명 검증                       | `rg -n 'svix' backend/src/auth/`                               | P3                 |
| F3  | FK ON DELETE 정책 (CASCADE / RESTRICT)       | Alembic migration 검토                                         | P3                 |
| F4  | 메트릭 카디널리티 < 10k series               | `/metrics` endpoint dump + label cardinality 측정              | P3                 |
| F5  | `page` deprecated 페이지네이션 fallback 제거 | `rg -n 'page=' backend/src/*/router.py`                        | P3 (Sprint 6 약속) |

---

## 운영 규약

### 본 문서 재실행 시점

1. **Sprint 회고 직전** — 회고 metric 의 한 항목으로 "정합성 점수" 추가
2. **Beta 오픈 직전** ([BL-070~072](../REFACTORING-BACKLOG.md)) — 위반 발견 시 차단
3. **Major refactor 직후** — refactor 가 정합성 깨뜨렸는지 확인
4. **신규 도메인 추가 시** — A1~A4 + B5~B8 항목 새 도메인 적용 여부

### 위반 발견 시

1. **위반 라인 + 컨텍스트** 를 본 문서 해당 항목 아래 "위반 이력" 서브섹션에 기록 (날짜 + PR # + 라인)
2. P 레벨 결정:
   - 즉시 fix 필요 (P0 broken bug 패턴) → active TODO 로 등록
   - 후속 sprint 처리 가능 (P1~P2) → [REFACTORING-BACKLOG.md](../REFACTORING-BACKLOG.md) 신규 BL 등록
3. fix PR merge 시 본 문서의 "최근 audit 결과" 갱신

### 변경 이력

- **2026-04-30** — 초기 audit. 15 항목 / 위반 0 / OK 13 / TBD 2 (A2 commit-spy 도메인 확장 → BL-010 / B5 alert_hook env ADR → BL-050).
