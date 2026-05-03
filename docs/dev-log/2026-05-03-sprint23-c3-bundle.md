# Sprint 23 — C-3 묶음 (Pine coverage parity + BL-091 follow-up)

**날짜**: 2026-05-03 (Sprint 22 완료 직후 dogfood 늦추는 동안 cascade)
**브랜치**: `stage/h2-sprint22` (Sprint 22+23 sequential, Sprint 18+19 패턴)
**범위**: BL-098 + BL-099 + BL-101 + BL-102 + BL-103 = **5 BL ✅ Resolved**
**Self-assessment**: 9/10 유지 목표 (Sprint 22 = 9/10 추정, dogfood evidence 미확정)

---

## §1. 배경 + 결정

Sprint 22 BL-091 ✅ Resolved 후 사용자 dogfood Day 2-7 늦추는 동안 같은 세션 적합도 가장 높은 cleanup 묶음 진행. dogfood 재개 시점에 사용자 friction 사전 해소 + Sprint 22 architectural robustness 강화.

**5 BL 묶음**:

- **C-1 (Pine + cleanup)**: BL-098 strategy.exit (NOP + warning) + BL-099 vline + BL-101 Makefile + BL-103 env warning
- **C-2 (BL-091 follow-up)**: BL-102 Order dispatch snapshot — service DI 변경 + 엄격 parser + Alembic + commit-spy

**사용자 결정 (AskUserQuestion)**: C-3 묶음 (Recommended) — 단일 sprint 적정 크기, dogfood Pain 사전 해소 + Sprint 22 robustness 강화 두 트랙 모두.

---

## §2. codex Generator-Evaluator

### 2.1 G.0 (medium reasoning, 1 iter, ~70k tokens)

**Verdict**: FIX FIRST → plan v2 surgery 후 통과.

**P1 4건 (모두 plan v2 반영)**:

| ID  | 발견                                                                                              | 반영                                                                                         |
| --- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| #1  | BL-098 close-fallback semantically unsafe (Pine strategy.exit = exit order 예약, 즉시 close 아님) | Option D NOP + unsupported_kwargs warning. 후속 BL-104 (full PendingExitOrder) 등록          |
| #2  | from_entry 무시 → wrong-id close (Pine 첫 인자 id ≠ close target)                                 | NOP 로 close 자체 회피, from_entry 도 unsupported_kwargs 기록                                |
| #3  | OrderService.execute 가 ExchangeAccount fetch 안 함 → snapshot 만들 정보 부재                     | exchange_service.\_repo.get_by_id 재사용 (기존 DI 그대로, 추가 변경 없음)                    |
| #4  | snapshot decode invalid JSON crash (`bool("false") == True` 위험)                                 | `_parse_order_dispatch_snapshot()` 엄격 helper + `isinstance(bool)` + try/except → None 반환 |

**P2 5건 (모두 plan v2 반영)**:

- #1: BL-102 est M (4-6h) → ~7-8h 상향
- #2: BL-103 warning lifespan 우선 + app_env 조건
- #3: BL-099 test 명 coverage parity 명확화
- #4: BL-101 make help 검증
- #5: Cohesion OK but commit slicing 필수

### 2.2 G.2 (high reasoning, 1 iter, ~94k tokens)

**Verdict**: FIX FIRST → P1 2건 즉시 fix (Phase B.5).

**P1 2건 (Phase B.5 즉시 fix)**:

| ID                     | 발견                                                                                                                                                                                    | 본 sprint 처리                                                                                                                                                                                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| #1 (security critical) | snapshot=`bybit/demo` + account=`bybit/live` 시 BybitDemoProvider 선택 + creds.environment=live → silent live endpoint 호출. snapshot=`bybit` + account=`okx` 시 cross-credentials 위험 | ✅ Phase B.5: `_provider_from_order_snapshot_or_fallback` 가 snapshot vs account drift 검증 → mismatch 시 `UnsupportedExchangeError` raise + `qb_order_snapshot_fallback_total{reason="drift"}` inc. 신규 3 tests (mode/exchange drift reject + no-drift normal) |
| #2                     | strategy.exit NOP warning 이 `state.warnings` 에만 쌓이고 `BacktestOutcome.parse.warnings` 까지 전파 안 됨. coverage supported → status="ok" + warnings empty silent success            | ✅ Phase B.5: `v2_adapter._stub_parse_outcome` 에 `warnings=` 인자 추가 + ok-path 가 `state.warnings` 전달. 사용자가 BacktestOutcome.parse.warnings 통해 strategy.exit NOP 인지 가능                                                                             |

**P2 4건 결과**:

- #1: account fetch transaction 밖 + None 시 FK violation → BL-105 신규 (Sprint 24+)
- #2: Alembic ADD COLUMN race (TOCTOU) → BL-106 신규 (`IF NOT EXISTS` 또는 `DuplicateColumn` catch, P3)
- #3: downgrade unconditional drop → BL-106 묶음
- #4: strategy.exit warnings 매 bar dedupe → BL-104 (full PendingExitOrder) 묶음

**False Alarms (G.2 가 직접 검증)**: #2 Alembic table rewrite (nullable + no default) / #4 JSONB enum (writer 가 .value 사용) / #5 bool check (isinstance(1, bool)==False) / #6 lifespan multi-worker noisy / #8 metric cardinality 2 series / #9 detached lazy load (scalar JSONB) / #10 Makefile build cache (정상 동작) — 모두 non-issue.

---

## §3. Implementation

### Phase A — Quick wins (~3h)

**A.1 BL-099 vline NOP**:

- `interpreter.py:_NOP_NAMES` 에 `"vline"` 1줄 추가
- 신규 test `test_vline_coverage_interpreter_parity_nop` (1 test)

**A.2 BL-098 strategy.exit NOP** (codex G.0 P1 #1+#2 회피):

- `interpreter.py:_eval_call` dispatch 에 `"strategy.exit"` 추가 (`("strategy.entry", "strategy.close", "strategy.close_all", "strategy.exit")`)
- `_exec_strategy_call` body 에 strategy.exit handler — close 호출 안 함, id/from_entry/모든 kwargs 를 `strategy.warnings` 에 기록
- 신규 tests 3건 (NOP / from_entry/limit/stop/profit 기록 / when=false skip)

**A.3 BL-101 Makefile**:

- `up-isolated-build` 신규 타깃 (`docker compose ... up -d --build`)
- `make help` 안내 추가
- `.PHONY` 등록

**A.4 BL-103 EXCHANGE_PROVIDER lifespan warning** (codex G.0 P2 #2):

- `main.py:lifespan` 에 one-shot warning + `app_env in (staging, production)` 조건
- 신규 tests 3건 (production warning emitted / development silent / fixture default silent)

### Phase B — BL-102 snapshot (~7-8h)

**B.1 Order model + Alembic**:

- `models.py` 에 `dispatch_snapshot: dict[str, object] | None` JSONB 컬럼 추가
- Alembic migration `20260503_0001_add_orders_dispatch_snapshot.py` (idempotent ADD COLUMN with information_schema check)
- 격리 stack (5433) 에서 upgrade/downgrade 양방향 검증 ✅

**B.2 OrderService snapshot 채움** (codex G.0 P1 #3):

- `_execute_inner` 시작 직후 `self._exchange_service._repo.get_by_id(req.exchange_account_id)` 호출 (기존 DI 재사용, 추가 의존성 0)
- snapshot dict 미리 만들어 양쪽 INSERT 분기 (idempotent + non-idempotent) 모두에서 동일 사용
- exchange_service=None (test 환경) → snapshot=None graceful (legacy fallback 자동 동작)

**B.3 엄격 parser + helper** (codex G.0 P1 #4):

- `tasks/trading.py` 에 `_parse_order_dispatch_snapshot(raw)` (엄격 검증, KeyError/ValueError → None, isinstance(bool) 강제 — `bool("false") == True` 회피)
- `_provider_from_order_snapshot_or_fallback(order, account, submit)` (snapshot 우선, 부재/invalid 시 metric inc + legacy fallback)
- `qb_order_snapshot_fallback_total{reason}` Counter (label cardinality 2: missing|invalid)
- 호출처 line ~257 (\_async_execute) + line ~502 (\_async_fetch_order_status) 모두 새 helper 호출

**B.4 신규 tests + 기존 회귀**:

- `test_dispatch_snapshot_priority.py` 17 tests (parse strict 10 + snapshot priority 2 + legacy fallback 3 + Order column sanity 2)
- `test_order_service_dispatch_snapshot.py` 3 tests (snapshot fill spy when exchange_service injected / futures leverage / None when missing)
- 기존 OrderService.execute commit-spy (test_webhook_secret_commits.py:164) 자동 회귀 방어

---

## §4. 검증 결과

### 자동 검증

```
TEST_DATABASE_URL=...localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=...localhost:6380/3 \
uv run pytest --timeout=120
```

(회귀 결과 별도 보고)

- ruff 0 / mypy 0 (145 source files)
- Alembic upgrade/downgrade 양방향 격리 stack 검증 ✅
- 신규 31 tests (vline+strategy.exit 4 + lifespan warning 3 + dispatch snapshot priority 17 + OrderService snapshot fill 3 + ... ) 100% pass

### 라이브 검증

- `make up-isolated-build` 신규 타깃 동작 (BL-101)
- staging/production app_env 시 worker startup log 에 EXCHANGE_PROVIDER deprecation warning (BL-103)
- 사용자 dogfood Day 2-7 시 strategy.exit 사용 indicator 가 backtest 진입 가능 (NOP) + warnings 표시
- Order create 후 DB 에 dispatch_snapshot JSONB 저장 확인:
  ```sql
  SELECT id, dispatch_snapshot FROM trading.orders ORDER BY created_at DESC LIMIT 5;
  ```

---

## §5. 신규 BL 등록 / 변동

### 등록

- **BL-104** (P2 M, codex G.0 P1 #1+#2 + G.2 P2 #4 후속) — strategy.exit full PendingExitOrder 구현 (target price trigger + 매 bar warnings dedupe). Sprint 23 은 NOP, dogfood 사용자 strategy.exit 쓰는 indicator 의 backtest 결과는 entry-only + BacktestOutcome.warnings 노출.
- **BL-105** (P2 S, codex G.2 P2 #1) — OrderService.execute account fetch transaction 안으로 이동 + missing 시 AccountNotFound. 현재 transaction 밖 fetch + None graceful (snapshot=NULL legacy fallback) → DELETE race 시 FK violation 500 위험.
- **BL-106** (P3 S, codex G.2 P2 #2+#3) — Alembic 20260503_0001 의 information_schema check + unconditional drop 을 PostgreSQL `IF NOT EXISTS` / `IF EXISTS` 로 교체. concurrent migration runner TOCTOU 회피.

### Resolved

- BL-098 strategy.exit interpreter dispatch ✅
- BL-099 vline interpreter NOP ✅
- BL-101 Makefile up-isolated-build ✅
- BL-102 Order dispatch snapshot + drift reject (codex G.2 P1 #1 fix) ✅
- BL-103 EXCHANGE_PROVIDER lifespan warning ✅

### 합계

기존 68 BL → Sprint 23 후 **66 BL** (5 ✅ Resolved + 3 신규 BL-104/BL-105/BL-106).

---

## §6. Sprint 24+ 분기 조건

| 조건                                                   | 다음 sprint                                       |
| ------------------------------------------------------ | ------------------------------------------------- |
| 사용자 dogfood Day 2-7 broker evidence ✅ + Pain 0-1건 | Path A Beta 오픈 (BL-070~072)                     |
| broker evidence ✅ + Pain 3건+                         | dogfood Pain 처리 sprint                          |
| broker evidence 🔴                                     | BL-091/BL-102 회귀 분석                           |
| 사용자 dogfood 본격 진입 안 함 (계속 늦춤)             | Path C 추가 cleanup (BL-011~016 WebSocket 안정화) |

---

## §7. 참조

- Sprint 23 plan v2: `~/.claude/plans/h2-sprint-23-c3-bundle.md`
- Sprint 22 dev-log: `docs/dev-log/2026-05-03-sprint22-bl091-architectural.md`
- BL 상세: `docs/REFACTORING-BACKLOG.md`
- backend.md §11 prefork-safe / LESSON-019 commit-spy: `.ai/stacks/fastapi/backend.md`
