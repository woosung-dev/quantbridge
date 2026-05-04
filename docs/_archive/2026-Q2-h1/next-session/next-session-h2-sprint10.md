H2 Sprint 10 — Multi-worker 안정성 + Real broker 테스트 + Rate limiting

## 전제

H2 Sprint 9 (Monte Carlo + Walk-Forward + 관측성 Phase 1 + 9-6 E2 idempotency) 는 `stage/h2-sprint9` 에 4 Phase squash 완료 상태.

Sprint 9 시점 기준선:

- BE 1074 tests / 17 skip / 0 fail
- FE 189 tests
- `/metrics` endpoint + Prometheus 5 metric 실측 가동
- 9-6 Idempotency-Key body_hash replay + conflict 작동
- `stress_tests` 테이블 + Celery task + Frontend UI 완비

H2 Kickoff plan §Sprint 10 (`docs/superpowers/plans/2026-04-20-h2-kickoff.md`) 의 목표:
**Beta 사용자가 붙기 시작하는 시점의 infrastructure hardening.**

Narrowest wedge persona pain: "서버 2 대 이상에서 같은 alert 이 중복 체결?" + "악의적 API 호출 방어?" + "Beta 오픈 전 실제 거래소 E2E 검증?"

---

## 개발 방법론 — **실제 Skill 호출 명시** (Sprint 9 교훈)

Sprint 9 회고: skill 이름을 문서에만 언급하고 실제 `Skill` 툴로 호출하지 않아 방법론 지침이 로드되지 않음. 이번 세션은 단계마다 **실제 Skill 호출** 한다.

### 워크플로우 단계별 Skill 호출 지점

| 단계                                      | Skill 호출                                          | 목적                                  |
| ----------------------------------------- | --------------------------------------------------- | ------------------------------------- |
| 세션 시작 직후                            | `superpowers:using-superpowers` (자동)              | entry point                           |
| 마스터 플랜 작성 전                       | `Skill(superpowers:writing-plans)`                  | Plan → Docs → Review → Implement 루프 |
| Phase SDD 작성 전                         | `Skill(superpowers:writing-plans)` 재호출           | Phase 단위 계약 SDD                   |
| 각 Phase 구현 Agent 디스패치              | `Skill(superpowers:subagent-driven-development)`    | worktree isolation + JSON 출력 계약   |
| 구현 전 TDD 착수                          | `Skill(superpowers:test-driven-development)`        | RED → GREEN → REFACTOR 엄격           |
| Phase B→C+D 병렬 Agent 2 개 디스패치 직전 | `Skill(superpowers:dispatching-parallel-agents)`    | 단일 메시지 병렬 원칙                 |
| 3-way 블라인드 리뷰 요청 전               | `Skill(superpowers:requesting-code-review)`         | review 요청 규약                      |
| 각 Phase 완료 주장 전                     | `Skill(superpowers:verification-before-completion)` | evidence before assertion             |
| worktree 작업 착수 시                     | `Skill(superpowers:using-git-worktrees)`            | safety verification                   |
| 모든 Phase 머지 완료 후                   | `Skill(superpowers:finishing-a-development-branch)` | 통합/정리 결정                        |

### Generator-Evaluator (3-way blind review) — 구체 구현

1. `Skill(superpowers:requesting-code-review)` 호출
2. Agent 가 push 한 diff 저장: `git diff origin/<base>..origin/<feat> > /tmp/<phase>-diff.patch`
3. **Evaluator 1 — codex CLI (foreground)**:

   ```bash
   codex exec --sandbox read-only --skip-git-repo-check "$(cat /tmp/codex-review-prompt.md)" > /tmp/codex-out.txt 2>&1
   ```

   - Prompt 에 diff 파일 참조 (`@/tmp/<phase>-diff.patch`) + Golden Rules 체크리스트
   - **stdin hang 발생 시**: kill + 짧게 재작성 + foreground 재호출. 2 회 실패 시 codex 생략하고 Opus+Sonnet 2-way fallback

4. **Evaluator 2 — Opus blind Agent**:
   ```
   Agent(subagent_type=general-purpose, model=opus, run_in_background=true,
         prompt="파일 경로 목록만 + Golden Rules 요약 + 'fetch content yourself via git show'")
   ```
5. **Evaluator 3 — Sonnet blind Agent**:
   ```
   Agent(subagent_type=general-purpose, model=sonnet, run_in_background=true,
         prompt="PR body 초안만 + edge case 탐색 지시")
   ```
6. PASS 기준: 평균 confidence ≥ 8/10, blocker = 0, major ≤ 2
7. GWF 시: **2 vote 이상 major 만** fix (Sprint 9 Phase B+ 패턴). 단독 major 중 실질 bug 는 선별 포함. minor/nit 은 Follow-up

---

## 이번 세션 범위 (Sprint 10 재정렬 — 5~20h)

### Phase A: 10-1 Multi-worker split-brain Redis lock (4~5h) [critical]

PG advisory lock 은 서버 2+ 대 사이 split-brain 가능.

- `redis-py` 기반 distributed lock (redlock 알고리즘)
- Idempotency-Key + Celery task pickup 3-guard 적용
- PG advisory → Redis 전환 (또는 양자 병행 Redis 우선)

### Phase B: 10-5 Rate limiting middleware (2~3h) [critical]

전체 API 가 rate limit 없음. Beta 오픈 전 필수.

- `slowapi` + Redis storage (Phase A infra 공유)
- per-user 100/min, `POST /backtests` 10/min, `POST /stress-test/*` 5/min
- 429 + `X-RateLimit-*` + `Retry-After`
- Clerk JWT 기반 key. `/metrics`, `/webhooks/*` 는 제외

### Phase C: 10-2 Real broker 테스트 인프라 (4~6h) [Beta prerequisite]

자동화된 E2E 검증.

- `pytest-celery` fixture — Celery worker/broker in-process spawn
- Bybit Demo 주문 fixture — test user + account + strategy seed
- E2E 1 건: TV webhook → OrderService → Bybit Demo create_order → filled 확인
- `pytest --run-real-broker` 플래그로만 실행 (기본 skip)

### Phase D: 10-4 CCXT 계측 per-exchange error rate (1~2h) [Phase 9-D 확장]

Sprint 9 는 latency 만. error rate 필요.

- `qb_ccxt_request_errors_total` Counter (labels: exchange, endpoint, error_class)
- `ccxt_timer` CM 의 except 분기에서 inc
- Grafana panel + alert rule (`error rate > 5%`) 추가

**Out of scope (Sprint 11+ 이관):**

- 10-3 TimescaleDB compression/retention (Beta 규모에서 시급하지 않음)
- US·EU geo-block (Sprint 11)
- 법무/Disclaimer (Sprint 11)

---

## 브랜치 전략 (Option C — Sprint 9 와 동일)

```
main
 └─ stage/h2-sprint10  ← 사용자가 최종 main PR 수동 생성
     ├─ feat/h2s10-redis-lock         (Phase A)
     ├─ feat/h2s10-rate-limit         (Phase B)
     ├─ feat/h2s10-real-broker-tests  (Phase C)
     └─ feat/h2s10-ccxt-metrics-v2    (Phase D)
```

Phase A → B 순차 (Redis 인프라 공유), B 머지 후 C + D **병렬**.

---

## Phase 분해 초안

### Phase A — Redis distributed lock

**위치:** `backend/src/common/redlock.py` (신규)

**핵심 계약:**

- `class RedisLock` — async context manager
- redlock: SET NX PX + unique token + Lua CAS unlock
- 장기 작업 heartbeat (Celery task 내 렉 연장)

**마이그레이션 대상:**

- `backend/src/backtest/repository.py::acquire_idempotency_lock`
- `backend/src/trading/repository.py::acquire_idempotency_lock`
- `backend/src/stress_test/repository.py::acquire_idempotency_lock` (있다면)

**TDD 6 건:** basic acquire/release, contention, TTL auto-release, unique token CAS, idempotency migrated, multi-worker split-brain prevented.

**마이그레이션 전략 결정 필요:** 점진적 (PG fallback) vs 완전 교체

### Phase B — Rate limiting middleware

**위치:**

- `backend/src/common/rate_limit.py` (신규, `slowapi` 래퍼)
- `backend/src/main.py` — middleware 등록
- 각 라우터의 `@limiter.limit(...)` 데코레이터

**핵심 계약:** Clerk JWT user_id → rate key. 비인증은 IP fallback. Redis 장애 시 fail-open.

**Per-endpoint limits:**

- `POST /api/v1/backtests`: 10/min
- `POST /api/v1/stress-test/*`: 5/min
- `POST /api/v1/strategies`: 30/min
- GET `/api/v1/**`: 300/min
- `/metrics`, `POST /webhooks/*`: 제외

**TDD 5 건:** limit 초과 429, 타 user 독립, 비인증 IP 기반, 제외 path 무제한, Redis 장애 fail-open.

### Phase C — Real broker E2E 인프라

**위치:**

- `backend/tests/real_broker/` (신규 디렉토리)
- `backend/tests/real_broker/conftest.py` — Bybit Demo credentials env, pytest-celery fixture
- `backend/tests/real_broker/test_webhook_to_filled_e2e.py`
- `backend/pyproject.toml` — `pytest-celery`, marker 추가

**pytest config:**

```toml
[tool.pytest.ini_options]
markers = ["real_broker: requires Bybit Demo credentials (skip by default)"]
```

**`.env.example` 추가:**

```
BYBIT_DEMO_API_KEY_TEST=
BYBIT_DEMO_API_SECRET_TEST=
```

**E2E 시나리오:** test user + Bybit Demo account → webhook TestClient POST → Celery create_order → 5~10s polling → filled 확인 → cleanup.

**CI 연동:** 기본 skip, nightly workflow + 수동 trigger.

### Phase D — CCXT error rate metric

**위치:**

- `backend/src/common/metrics.py` — 1 metric 추가
- `backend/src/trading/providers.py` — `ccxt_timer` CM 확장 (except 분기 inc)
- `docs/07_infra/grafana-cloud-setup.md` — panel + alert rule 추가

**신규 metric:**

```python
qb_ccxt_request_errors_total = Counter(
    "qb_ccxt_request_errors_total",
    "CCXT exchange API errors",
    labelnames=("exchange", "endpoint", "error_class"),
)
```

**`error_class`:** `type(exc).__name__` (e.g., ExchangeError, RateLimitExceeded, InsufficientFunds).

**Grafana alert:** `rate(qb_ccxt_request_errors_total[5m]) / rate(qb_ccxt_request_duration_seconds_count[5m]) > 0.05`

---

## 핵심 참조 문서 (세션 시작 시 필수 선독)

- `docs/superpowers/plans/2026-04-20-h2-kickoff.md` §Sprint 10 (148~164 줄)
- `docs/superpowers/plans/2026-04-24-h2-sprint9-phase-b.md` (idempotency 패턴)
- `backend/src/backtest/repository.py::acquire_idempotency_lock` (PG advisory 현 구현)
- `backend/src/trading/repository.py::acquire_idempotency_lock`
- `backend/src/common/metrics.py` (Phase D 확장 대상)
- `backend/src/trading/providers.py::ccxt_timer` (Phase D 확장 대상)
- `backend/src/tasks/celery_app.py` (Redis 설정)
- `backend/.env.example` (REDIS_URL 기존 확인)
- `AGENTS.md` §현재 작업 (Sprint 9 완료 반영됨)
- `.ai/stacks/fastapi/backend.md` §Router/Service/Repository

---

## 주의사항 (Sprint 9 실측 learnings)

### 구현 함정 (승격 규칙)

- **Decimal-first 합산** (Sprint 4 D8)
- **Celery prefork-safe** — `create_async_engine()` / vectorbt lazy init (Sprint 4 D3)
- 환경변수 하드코딩 금지, `.env.example` 미등록 var 참조 금지
- Decimal 사용 (금액), Celery 비동기 (백테스트)

### Redis 함정 (Sprint 10 신규)

- **fail-open vs fail-closed**: rate limit 은 fail-open (경고 + 통과), idempotency lock 은 fail-closed (서비스 중단). 명시 선택.
- **Redlock 알고리즘**: 공식 spec 준수. Beta 규모는 단일 Redis 허용 (Sentinel/Cluster 는 Sprint 11+).
- **Lua unlock script**: CAS 로 token 검증 후 DEL. raw DEL 금지 (wrong-release).

### Evaluator 운영 (Sprint 9 실측)

- **codex CLI stdin hang** 반복 — foreground 실행 + 짧은 prompt + 행 감지 시 kill + 재시도. 2 회 실패 시 Opus+Sonnet 2-way fallback.
- **Agent prompt 짧고 명확하게** — "pytest still running" timeout 방지. 긴 코드는 SDD 참조로.
- **pre-commit hook** — worktree 에 node_modules / backend/.venv symlink 필수.
- **pre-push hook** — 신규 브랜치는 `@{u}..` empty → pytest/ruff 미실행. Agent 가 local 검증 증거 (test count, coverage) JSON 명시 강제.

### 병렬 worker 조합

- Phase A → B 순차 (Redis infra 공유)
- Phase B 머지 후 Phase C + Phase D **단일 메시지 2 Agent 병렬** (`Skill(superpowers:dispatching-parallel-agents)` 먼저 호출)

---

## 커밋 단위 초안

```
c1 feat(infra): Redis distributed lock (redlock) — Phase A
c2 refactor(idempotency): PG advisory → Redis lock — Phase A
c3 feat(infra): rate limiting middleware — slowapi + Redis — Phase B
c4 feat(tests): real broker E2E — pytest-celery + Bybit Demo — Phase C
c5 feat(observability): CCXT per-exchange error rate metric — Phase D
c6 docs(observability): Grafana error rate panel + alert rule — Phase D
```

---

## 시작 시퀀스

1. 본 프롬프트 + `AGENTS.md` + `docs/superpowers/plans/2026-04-20-h2-kickoff.md` §Sprint 10 읽기
2. Plan mode 진입 → **`Skill(superpowers:writing-plans)` 호출** → 마스터 플랜 `/Users/woosung/.claude/plans/h2-sprint-10-<code>.md` 작성
3. `AskUserQuestion` 으로 3 핵심 scope 결정:
   - Redis lock: 점진적 (PG fallback 유지) vs 완전 교체?
   - Rate limit default: 엄격 vs 완화?
   - Real broker CI: nightly-only vs PR optional?
4. ExitPlanMode
5. **Phase A:**
   - `Skill(superpowers:writing-plans)` → Phase A SDD
   - `Skill(superpowers:test-driven-development)` + `Skill(superpowers:subagent-driven-development)` + `Skill(superpowers:using-git-worktrees)` → Agent 디스패치
   - `Skill(superpowers:requesting-code-review)` → 3-way Evaluator
   - iter-1 fix (2 vote 이상 major)
   - `Skill(superpowers:verification-before-completion)` → squash merge + push
6. **Phase B:** 동일 패턴 반복
7. **Phase C + D:**
   - `Skill(superpowers:dispatching-parallel-agents)` 호출
   - 단일 메시지 2 Agent 병렬 디스패치
8. 모든 Phase 완료 후 `Skill(superpowers:finishing-a-development-branch)` → stage/h2-sprint10 → main PR 사용자 수동

**첫 질문 금지** — 파일 읽고 Plan mode 진입부터 시작. 질문 필요 시 `AskUserQuestion` 툴.
