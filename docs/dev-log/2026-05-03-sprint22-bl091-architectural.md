# Sprint 22 — BL-091 ExchangeAccount.mode dynamic dispatch (architectural proper fix)

**날짜**: 2026-05-03
**브랜치**: `stage/h2-sprint22` (cascade from main `b794538`)
**범위**: BL-091 ✅ Resolved — Sprint 20 hot-fix 의 proper fix
**Self-assessment**: 9/10 유지 목표 (Sprint 21 = 9/10)

---

## §1. 배경 + 결정

### 1.1 Sprint 20 발견

Sprint 20 dogfood Day 0 라이브 시나리오에서 사용자가 `/trading` TestOrderDialog 로 발송 시:

- UI "filled" + DB `state=filled` 표시 ✅
- 그러나 `exchange_order_id='fixture-1'` + `filled_price=50000.00` (round number) = mock 응답 🔴
- **broker 까지 도달 안 함** — `FixtureExchangeProvider` 가 silent 반환

### 1.2 Root cause

`backend/src/tasks/trading.py:69-99` 의 `_get_exchange_provider() / _build_exchange_provider()`:

- `settings.exchange_provider` (Pydantic env, process-wide global) 기반 lazy singleton
- `ExchangeAccount.exchange` (bybit/okx) + `ExchangeAccount.mode` (demo/live) **둘 다 무시**
- multi-account 사용자가 demo / live 동시 운용 시 process env 1개 값으로만 라우팅 → silent broker bypass

### 1.3 Sprint 20 hot-fix 한계

`.env` + docker-compose 에 `EXCHANGE_PROVIDER=bybit_demo` 하드코딩 = mitigation. Account 추가/전환 시 env 재배포 필요. proper fix 아님.

### 1.4 사용자 결정 (AskUserQuestion)

- **Q1 (dispatch key)**: `(account.exchange, account.mode, has_leverage)` 3-tuple — `Order.leverage IS NULL` → spot, NOT NULL + > 0 → futures. Alembic migration 0건. 기존 OrderRequest schema validator 재사용.
- **Q2 (Bybit live)**: `BybitLiveProvider` stub 클래스 + `ProviderError` raise (NotImplementedError 대신 — graceful rejected). BL-003 mainnet runbook 까지 deferred.

---

## §2. codex Generator-Evaluator

### 2.1 G.0 (medium reasoning, 1 iter, ~52k tokens)

**Verdict**: FIX FIRST → plan v2 surgery 후 통과.

**P1 5건 (모두 plan v2 반영)**:

| ID  | 발견                                                                                 | 반영                                                                               |
| --- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| #1  | `BybitLiveProvider` stub 과 dispatch UnsupportedExchangeError 모순 (stub dead code)  | dispatch 가 `(bybit, live, *) → BybitLiveProvider()` 실제 반환                     |
| #2  | dispatch 실패가 `except ProviderError` (line 214) 못 걸려 Order submitted 영구 stuck | `UnsupportedExchangeError(ProviderError)` 로 정의 → graceful rejected              |
| #3  | `BybitLiveProvider` stub 의 `cancel_order` 누락 (Protocol 위반, mypy 깨짐)           | 3 메서드 모두 stub + ProviderError raise                                           |
| #4  | EXCHANGE_PROVIDER 정책 모순 (compose env 유지 + Literal 임의값 거부)                 | docker-compose 운영 env 제거 + .env.example 주석 변경 + config 필드는 dead config  |
| #5  | account.mode race 정책 미정                                                          | router 확인 결과 mode mutation endpoint 부재 (POST/GET/DELETE 만). audit test 추가 |

**P2 5건 (모두 plan v2 반영)**:

- #1: Order.leverage DB CHECK 부재 → `lev > 0` 보정
- #2: monkeypatch 정확 카운트 19+2=21건 (v1 "25+" 부정확)
- #3: e2e webhook test 마이그레이션 전략 명시
- #4: fixture guard test scope 너무 넓음 → narrow expected_class
- #5: trading.py:8 헤더 주석 갱신 누락

### 2.2 G.2 (high reasoning, 1 iter, ~84k tokens)

**Verdict**: PASS (P1 0건).

**P2 5건 결과**:

| ID  | 발견                                                                                                                                               | 본 sprint 처리                                                                                                                       |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| #1  | `test_account_mode_immutable.py` 의 substring `/accounts` 매칭이 실제 라우트 `/exchange-accounts` 부정확 catch                                     | ✅ 즉시 fix — 정확한 prefix `path == "/exchange-accounts" or startswith("/exchange-accounts/")` 로 강화                              |
| #2  | `_has_leverage` 가 string `"0"` / `"5"` 등 비-numeric 입력에 TypeError raise → ProviderError catch 밖 전파                                         | ✅ 즉시 fix — `isinstance(int, Decimal, float)` 가드 + bool 명시 제외. 4 신규 regression test (string/bool/Decimal pos/Decimal zero) |
| #3  | fetch watchdog 가 Order.leverage 현재값 사용 → DB manual mutation 시 spot/futures 잘못 분기                                                        | 🔜 BL-102 신규 (Order 에 dispatch snapshot 저장, P2 M 1-2일)                                                                         |
| #4  | backend/.env.example + runbook.md + bybit-mainnet-checklist.md 의 EXCHANGE_PROVIDER 가 활성 설정처럼 안내됨 (root .env.example 만 deprecated 처리) | ✅ 즉시 fix — 4개 docs 모두 deprecation 주석 동기화                                                                                  |
| #5  | `EXCHANGE_PROVIDER` non-default 값 silent 수용 (startup warning 없음)                                                                              | 🔜 BL-103 신규 (startup warning 또는 필드 제거, P3 S 1-2h)                                                                           |

**False Alarms (G.2 가 직접 검증)**: Vector 4 (live stub graceful catch ✅) / Vector 5 (dispatch raise inside try ✅) / Vector 6 (positional callsite ✅) / Vector 8 (None short-circuit ✅) / Vector 9 (Protocol structural duck-typing ✅) / Vector 10 (queued task order_id 중심, EXCHANGE_PROVIDER 의존 X ✅).

**P2 #1+#2+#4 즉시 fix 후 재실행 결과**: 신규 4 regression test (TestHasLeverageHelper +4) 모두 PASS, audit test path 매칭 정확화.

---

## §3. Implementation (Phase A → D)

### Phase A — Provider factory refactor (~3-4h)

**A.1** `backend/src/trading/exceptions.py` — `UnsupportedExchangeError(ProviderError)` 추가. ProviderError subclass = 기존 try/except 자동 catch.

**A.2** `backend/src/trading/providers.py` — `BybitLiveProvider` 신규 클래스. `create_order` / `cancel_order` / `fetch_order` 3 메서드 모두 `ProviderError("Bybit live (mainnet) 미지원 — BL-003 mainnet runbook 완료 후 활성화")` raise.

**A.3** `backend/src/tasks/trading.py` — 본체 refactor:

- 헤더 docstring update
- `_exchange_provider: ExchangeProvider | None = None` global 제거
- `_get_exchange_provider()` lazy singleton 제거
- `_has_leverage(submit_or_order)` helper (None or 0 → spot, > 0 → futures)
- `_provider_for_account_and_leverage(exchange, mode, has_leverage)` 3-tuple dispatch 본체
- `_build_exchange_provider(account, submit)` public dispatcher
- 호출처 line 198 (`_execute_with_session`) + line 450 (`_fetch_order_status_with_session`) 변경

**A.4** Config + env policy:

- `backend/src/core/config.py:82` — `exchange_provider` field docstring DEPRECATED 마킹
- `docker-compose.yml` — worker + beat 의 `EXCHANGE_PROVIDER` env 줄 제거
- `.env.example:43` — DEPRECATED 주석 추가
- `backend/src/tasks/funding.py:1-6` — docstring update

**A.5** 신규 unit tests `backend/tests/tasks/test_provider_dispatch.py` (27 tests):

- TestProviderDispatchHappyPath: bybit demo spot/futures, okx demo spot
- TestProviderDispatchUnsupported: okx demo futures / binance / okx live → UnsupportedExchangeError
- TestBybitLiveStub: stub 인스턴스 반환 + 3 메서드 ProviderError verifier
- TestHasLeverageHelper: None / 0 / 양수 / 누락 attribute 분류
- TestBuildExchangeProvider: account+submit 자동 dispatch 검증
- E2E rejected verifier: UnsupportedExchangeError + BybitLiveProvider 둘 다 Order.state=rejected
- B.2 narrow guard: 5 parametrize (real account never returns Fixture)

**A.6** 21건 monkeypatch 마이그레이션 (Python regex 자동 변환):

- `_exchange_provider` setattr 19건 → `_provider_for_account_and_leverage` lambda 19건 (test_celery_task.py 5 + test_celery_task_futures.py 1 + test_fetch_order_status_task.py 9 + test_e2e_webhook_to_futures_order.py 1삭제 + test_celery_task_futures.py 1삭제 reset)
- `settings.exchange_provider` setattr 2건 (test_celery_task_futures.py + test_e2e_webhook_to_futures_order.py) → 줄 삭제 + auto-dispatch 의존
- `test_build_exchange_provider_dispatches_bybit_futures` 함수 본문 — ExchangeAccount fixture + OrderSubmit 로 직접 호출 패턴

### Phase B — Audit + guard (~1h)

**B.4** `backend/tests/trading/test_account_mode_immutable.py` — router 의 `/accounts` route 에 PUT/PATCH 부재 audit. 미래 PUT 추가 시 fail → 신규 BL (Order snapshot) 등록 강제.

### Phase C — codex G.2 challenge (~30min)

진행 중 (백그라운드). 결과는 별도 commit.

### Phase D — docs + commit + PR

- `docs/REFACTORING-BACKLOG.md` BL-091 entry ✅ Resolved 마킹 + Sprint 22 결과 상세화
- 본 dev-log
- CLAUDE.md `## 현재 작업` 섹션 Sprint 22 entry
- Phase 별 commit 분리

---

## §4. 검증 결과

### 자동 검증

```
TEST_DATABASE_URL=...localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=...localhost:6380/3 \
uv run pytest --timeout=120
```

- **1342 passed / 27 skipped / 0 failed** (3분 12초)
- ruff 0 errors
- mypy 0 errors (145 source files)
- 신규 28 tests (test_provider_dispatch.py 27 + test_account_mode_immutable.py 1) 100% pass

### 영향받은 test 파일 회귀

| 파일                                                 | 신규/마이그레이션                            | 결과       |
| ---------------------------------------------------- | -------------------------------------------- | ---------- |
| `tests/tasks/test_provider_dispatch.py`              | 신규 27                                      | ✅ 27 pass |
| `tests/trading/test_account_mode_immutable.py`       | 신규 1                                       | ✅ 1 pass  |
| `tests/trading/test_celery_task.py`                  | 5 monkeypatch migrated                       | ✅ 5 pass  |
| `tests/trading/test_celery_task_futures.py`          | 1 migrated + 1 deleted + 1 rewritten         | ✅ 2 pass  |
| `tests/trading/test_fetch_order_status_task.py`      | 9 monkeypatch migrated (6 multi + 3 single)  | ✅ 13 pass |
| `tests/trading/test_e2e_webhook_to_futures_order.py` | 1 deleted reset + 1 settings setattr deleted | ✅ 1 pass  |

### 라이브 검증 (사용자 dogfood Day 2-7)

본 sprint 머지 직후:

1. `make up-isolated` 격리 stack 재부팅 (env 제거 반영)
2. `docker exec quantbridge-worker env | grep EXCHANGE_PROVIDER` → **결과 없음** 확인
3. `/strategies` 에서 strategy 에 ExchangeAccount(bybit demo) 연결 + TestOrderDialog 발송
4. `exchange_order_id` 가 `bybit-...` 형식 (fixture-\* 패턴 아님) + `filled_price` round number 아님 + Bybit Demo 대시보드 reflects 확인

---

## §5. 신규 BL 등록 / 변동

### 등록

- **BL-102** (P2 M, codex G.2 P2 #3) — Order 에 dispatch 시점 (exchange, mode, has_leverage) snapshot 저장. fetch watchdog 가 Order.leverage 현재값 사용 → DB manual mutation 시 spot/futures 잘못 분기 방어.
- **BL-103** (P3 S, codex G.2 P2 #5) — `EXCHANGE_PROVIDER` non-default startup warning 또는 Sprint 23+ 필드 제거.

### Resolved

- **BL-091** ✅ — ExchangeAccount.mode dynamic dispatch (proper fix)

### 합계

기존 67 BL → Sprint 22 후 **68 BL** (BL-091 ✅ Resolved, BL-102/BL-103 신규 2).

---

## §6. Sprint 23 분기 조건

| 조건                                            | 다음 sprint                           |
| ----------------------------------------------- | ------------------------------------- |
| dogfood Day 2-7 broker evidence ✅ + Pain 0-1건 | Path A Beta 오픈 (BL-070~072)         |
| broker evidence ✅ + Pain 3건+                  | Sprint 23 = dogfood Pain 처리         |
| broker evidence 🔴                              | BL-091 회귀 분석 + 추가 fix           |
| codex G.2 P1 발견                               | Sprint 22 종료 직전 reflective commit |

---

## §7. 참조

- Sprint 22 plan v2: `~/.claude/plans/claude-plans-h2-sprint-22-prompt-md-elegant-cerf.md`
- Sprint 21 dogfood Day 1 dev-log: `docs/dev-log/2026-05-03-dogfood-day1-sprint21.md`
- BL-091 상세: `docs/REFACTORING-BACKLOG.md` BL-091 섹션
- Sprint 20 dogfood Day 0 dev-log: `docs/dev-log/2026-05-02-sprint20-dogfood-day0-setup.md`
- backend.md §11 prefork-safe 패턴: `.ai/stacks/fastapi/backend.md`
- LESSON-019 commit-spy 의무 (관련 없으나 Sprint 22 가 trading.py 만지므로 미래 mutation method 추가 시 적용)

---

## §8. 다음 prompt

`~/.claude/plans/h2-sprint-23-prompt.md` (작성 예정 — Path A/B/C 분기는 dogfood evidence + Pain 누적에 따라 결정).
