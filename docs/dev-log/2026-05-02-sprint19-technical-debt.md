# Sprint 19 — Path C Technical Debt (Sprint 18 후속, BL-081/083/084/085 ✅ Resolved)

> 2026-05-02. Sprint 18 의 BL-080 architectural fix 직후 진행. Sprint 18 G.2 잔존 P2 + 신규 BL 4건 처리하여 dogfood 진입 전 technical debt 제로화.
>
> Master plan: `~/.claude/plans/h2-sprint-19-master.md`
> Sprint 19 prompt: `~/.claude/plans/h2-sprint-19-prompt.md`
> 이전 sprint: [Sprint 18 BL-080 Resolved](./2026-05-02-sprint18-bl080-architectural.md)
> 브랜치: `stage/h2-sprint18` (Sprint 18 + 19 sequential commits, 단일 PR)

---

## 1. 배경 + Path 결정

Sprint 18 가 BL-080 architectural fix 완료 → self-assessment 5/10 → 9/10 → H1→H2 gate 통과. 사용자 결정: 같은 세션에서 Path C (technical debt) 우선 진행 — Path B (1-2주 본인 dogfood) 는 사용자 본인 진행, Path A (Beta 오픈) 는 외부 destructive 다수.

**Scope (4 BL)**:

- BL-081 `_PENDING_ALERTS` gauge + bound/drain
- BL-083 `tests/test_migrations.py` 격리 stack 호환 (psycopg2 sync DSN)
- BL-084 AST audit test (module-level loop-bound state 차단 gate)
- BL-085 prefork smoke integration test (real asyncpg, `@pytest.mark.integration`)

**Out of scope (Sprint 20+)**:

- BL-082 1h prefork soak gate (본인 dogfood 중 측정)
- BL-005 본인 1-2주 dogfood
- Beta 오픈 번들 BL-070~072

---

## 2. codex G.0 결과 (medium reasoning, iter 1, 366k tokens)

**Verdict**: HIGH risk → FIX FIRST. P1 4건 + P2 6건.

| #     | 발견                                                                                              | 적용                                                                                                                          |
| ----- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| P1 #1 | BL-083 helper 만으로 부족 — `test_migrations.py` 가 conftest.DB_URL 우회, 직접 DATABASE_URL 만 봄 | `_resolved_test_db_url()` 함수 도입 (TEST_DATABASE_URL > DATABASE_URL > default). `_alembic_cfg()` + async drift test 가 사용 |
| P1 #2 | BL-085 가 settings.database_url 사용 — prod DB hit + apply_async monkeypatch 필요                 | DSN guard + `_no_op_apply_async` fixture (execute_order/fetch_order_status apply_async no-op)                                 |
| P1 #3 | `pytest_collection_modifyitems` early return — `--run-mutations` 시 integration 도 활성화         | mutation/integration 독립 처리                                                                                                |
| P1 #4 | BL-081 drain + done_callback 중복 dec → gauge 음수                                                | idempotent helper — `if task in set: discard + dec`                                                                           |

P2 6건:

- BL-083: SQLAlchemy URL object 사용 (`make_url().set(drivername=...)`) ✅
- BL-084: AnnAssign + import alias detection ✅
- BL-085: pyproject.toml `integration` marker 등록 (strict) ✅
- BL-085: missing DB → clear fail (silent skip 금지) ✅
- soft cap on \_PENDING_ALERTS — 이관 (Sprint 20+ Grafana alert)
- alert.py docstring 업데이트 — 이관 (P3 nit)

---

## 3. 변경 요약

### Phase A — BL-081: `qb_pending_alerts` gauge + `track_pending_alert()` helper

- `backend/src/common/metrics.py:202` `qb_pending_alerts` Gauge 신규 (16번째 metric).
- `backend/src/common/alert.py:track_pending_alert()` helper — set add + gauge inc + idempotent done_callback (set membership 검사로 두 번째 dec 차단).
- `backend/src/trading/kill_switch.py:225` `_PENDING_ALERTS.add(task) + add_done_callback(_PENDING_ALERTS.discard)` → `track_pending_alert(task)`.
- 신규 5 tests (`tests/common/test_alert_pending_gauge.py`):
  1. `test_track_pending_alert_increments_gauge_and_set` — happy path
  2. `test_track_pending_alert_handles_immediately_completed_task`
  3. `test_track_pending_alert_double_call_is_idempotent`
  4. `test_drain_after_external_discard_does_not_underflow_gauge` — codex P1 #4 회귀 방어
  5. `test_track_pending_alert_with_cancelled_task`

### Phase B — BL-083: alembic test 격리 stack 호환

- `backend/tests/conftest.py` `_to_psycopg2_url(asyncpg_url)` helper — `sqlalchemy.engine.make_url` + asyncpg-only param 제거 (`server_settings`, `command_timeout`, `ssl_negotiation`) + drivername `postgresql+psycopg2`.
- `backend/tests/test_migrations.py` `_resolved_test_db_url()` 함수 도입 — `TEST_DATABASE_URL > DATABASE_URL > default` 우선순위. `_alembic_cfg()` + async drift test 가 직접 사용.
- 격리 stack 환경에서 4 fail (test_alembic_roundtrip, \_schema_matches_sqlmodel_metadata, \_trading_schema_round_trip, \_trading_orders_idempotency_unique) → **0 fail**.

### Phase C — BL-084: AST audit test

- `backend/tests/tasks/test_no_module_level_loop_bound_state.py` 신규.
- 검사 대상: `src/tasks/*.py` + `src/common/alert.py` + `src/common/redis_client.py`.
- AST 분석: `Module.body` 의 `Assign` + `AnnAssign` 의 `value=Call(asyncio.<Semaphore|Lock|Event|Queue|...>)`.
- import alias 지원 (`from asyncio import Semaphore as S`, `import asyncio as aio`).
- Allowlist: `_SEND_SEMAPHORE` (Sprint 18 `_WORKER_LOOP` 통일로 안전).
- 4 tests:
  1. `test_no_unallowed_module_level_asyncio_primitives` — main audit
  2. `test_audit_targets_cover_known_modules` — sanity check
  3. `test_audit_detects_synthetic_violation` — self-test
  4. `test_allowlisted_modules_have_documented_violations` — stale allowlist 방어

### Phase D — BL-085: prefork smoke integration test

- `backend/tests/tasks/test_prefork_smoke_integration.py` 신규.
- `@pytest.mark.integration` marker + `--run-integration` flag (mirror `--run-mutations`).
- DSN guard (`_verify_test_db_dsn`): `make_url(dsn).database` 가 `_test` suffix 검증 (codex G.2 P1 #2 fix — substring 검사 회피).
- `_isolated_worker_loop` fixture: `init/shutdown_worker_loop` + `monkeypatch.setattr(config.settings, "database_url", test_db_url)`.
- `_no_op_apply_async` fixture: `execute_order_task / fetch_order_status_task / run_bybit_private_stream` 의 `apply_async + delay` 모두 no-op (codex G.2 P1 #1 fix — WS reconcile 의 `.delay()` 추가).
- 5 tests: scan x3 / reclaim x3 / reconcile x3 / mixed 9 (3x3) / loop persistence.
- `--run-integration` + 격리 stack 환경에서 5/5 PASSED. default 실행 시 5/5 SKIPPED (정상).

---

## 4. codex G.2 결과 (high reasoning, iter 1, 397k tokens)

**Verdict**: HIGH → FIX. P1 critical 2건 즉시 fix.

| #     | 발견                                                                                                                                                              | 적용                                                                                                                                                                                                |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1 #1 | BL-085 의 "broker side effect 0" 가 false — `reconcile_ws_streams()` 가 `run_bybit_private_stream.delay()` 호출, stale Bybit account 발견 시 real WS task enqueue | `_no_op_apply_async` fixture 에 `websocket_task.run_bybit_private_stream.delay/apply_async` no-op 추가. `test_reconcile_ws_streams_three_consecutive_invocations` 에 `_no_op_apply_async` 의존 추가 |
| P1 #2 | DSN guard substring `"_test" in dsn` 가 username/password/host 의 `_test` 에 false-positive                                                                       | `make_url(dsn).database.endswith("_test")` 정확 검증                                                                                                                                                |

**P2 (5건)**:

- AST audit factory function miss — Sprint 20 이관 (사람 검토 보완)
- AST audit target list manual curated — Sprint 20 `src/tasks/**/*.py` glob 검토
- `drain_pending_alerts()` helper — Sprint 20 (현재 production drain 사용처 없음)
- system-architecture.md metrics docs stale (qb_pending_alerts 누락) — **본 sprint 흡수**
- integration smoke mutates `_test` DB — 본 dev-log 명시화로 흡수

**False alarms (8/10 vector)**: V1, V2, V4, V5, V6, V7, V9, V10 — codex 가 명시 evidence 로 안전 확인.

---

## 5. 자동 검증 + 라이브 회귀

| 항목                                        | 결과                                                                                 |
| ------------------------------------------- | ------------------------------------------------------------------------------------ |
| ruff check src/ tests/                      | ✅ All checks passed (Sprint 19 추가 1 SIM105 fix 후 0)                              |
| mypy src/                                   | ✅ no issues (145 source files)                                                      |
| 신규 tests                                  | ✅ **18 PASS** (BL-081 5 + BL-084 4 + BL-085 5 + Sprint 18 worker_loop 12 회귀 유지) |
| 전체 pytest (격리 stack env)                | ✅ **1278 passed / 0 failed / 27 skipped** (Sprint 18 1269 + Sprint 19 +9)           |
| BL-085 integration with `--run-integration` | ✅ **5/5 PASSED** + DSN guard negative case fail 정상                                |
| 라이브 scan_stuck_orders x3                 | ✅ **3/3 succeeded / 0 raised** (Sprint 18 30/30 패턴 유지)                          |

---

## 6. self-assessment (Sprint 18 9/10 → Sprint 19 9/10)

self-assessment 자체는 변화 없음 (가중치 항목 동일). Sprint 19 는 technical debt 해소이므로 Sprint 18 의 watchdog/retry/Pain/quality 점수에 영향 X.

| 평가 항목                   | 가중치 | Sprint 18 | Sprint 19                                         |
| --------------------------- | ------ | --------- | ------------------------------------------------- |
| watchdog 라이브 동작 신뢰도 | 4      | 4/4       | 4/4                                               |
| retry/alert 정확도          | 2      | 1/2       | 1/2 (alert chain 도달은 사용자 dogfood 검증 대상) |
| Pain 발견                   | 2      | 2/2       | 2/2                                               |
| 매일 사용 quality           | 2      | 2/2       | 2/2                                               |
| **합계**                    | **10** | **9/10**  | **9/10**                                          |

**Beta 오픈 confidence**: 1 단계 ↑ — technical debt 제로 + CI 자동화 (BL-085 integration) 로 회귀 방어 수립.

---

## 7. Sprint 20+ 이관 BL

| ID                 | 제목                                                                 | 우선순위 | est                                  |
| ------------------ | -------------------------------------------------------------------- | -------- | ------------------------------------ |
| BL-081 ✅ Resolved | gauge + helper (본 sprint)                                           | —        | —                                    |
| BL-083 ✅ Resolved | alembic test 격리 호환 (본 sprint)                                   | —        | —                                    |
| BL-084 ✅ Resolved | AST audit test (본 sprint)                                           | —        | —                                    |
| BL-085 ✅ Resolved | prefork integration test (본 sprint)                                 | —        | —                                    |
| **BL-082**         | 1h prefork soak gate + RSS slope (max_tasks_per_child 250→1000 검증) | P2       | M (3-4h) — 본인 dogfood 중 자연 측정 |
| **BL-086 (신규)**  | AST audit factory function detection (codex G.2 P2 #1)               | P3       | S (1-2h)                             |
| **BL-087 (신규)**  | AST audit target glob `src/tasks/**/*.py` (codex G.2 P2 #2)          | P3       | S (30min)                            |
| **BL-088 (신규)**  | `drain_pending_alerts()` helper (codex G.2 P2 #3)                    | P3       | S (1h)                               |
| **BL-089 (신규)**  | `qb_pending_alerts` Grafana alert wire-up (>50 임계)                 | P2       | S (1-2h)                             |
| **BL-090 (신규)**  | `tests/db_url.py` 분리 (codex G.2 P3 #1)                             | P3       | S (30min)                            |
| BL-005             | 본인 1-2주 dogfood (live broker)                                     | P1       | 1-2주 (gate 통과로 trigger 도래)     |
| BL-070~072         | Beta 오픈 번들                                                       | P1       | 12-20h                               |

---

## 8. 머지 권장

- ✅ Sprint 19 4 BL 모두 ✅ Resolved
- ✅ codex G.0 medium iter 1 (366k tokens) — P1 4 + P2 6 모두 plan/code 반영
- ✅ codex G.2 high iter 1 (397k tokens) — P1 critical 2건 즉시 fix, P2 일부 흡수 + 일부 Sprint 20 이관
- ✅ ruff 0 / mypy 0 / 1278 pytest passed
- ✅ Sprint 18 + 19 sequential commits, 단일 PR (`stage/h2-sprint18` 브랜치)
- ✅ 라이브 회귀 (Sprint 18 30/30 패턴) 유지

**라이브 운영 영향**: BL-081 의 `track_pending_alert` migration — kill_switch.py path 만 영향, 의미 동일 + gauge 추가 (관측성 ↑). 다른 변경 (BL-083/084/085) 은 test 만 영향 → 운영 영향 0.

**다음**: 사용자 stage→main PR + Sprint 20 진입 (Path B 본인 dogfood 1-2주 권장 — H1→H2 gate ≥9 라이브 검증). prompt: `~/.claude/plans/h2-sprint-20-prompt.md`.
