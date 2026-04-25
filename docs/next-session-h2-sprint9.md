# 다음 세션 시작 프롬프트 — H2 Sprint 9 (Monte Carlo + Walk-Forward + 관측성 Phase 1)

> **사용법:** 아래 `✂ COPY START` 줄 **다음 줄**부터 `✂ COPY END` 줄 **바로 앞 줄**까지 선택해서 새 세션 입력창에 붙여넣기.
> 바깥쪽 ` ```` ` 펜스는 렌더링 구분용이므로 **포함하지 말 것**.
> 2026-04-24 H2 Sprint 1 머지 직후 기준.

---

<!-- ✂ COPY START ────────────────────────────────────────────────── -->

````
H2 Sprint 9 — Monte Carlo + Walk-Forward Analysis + 관측성 Phase 1

## 전제

H2 Sprint 1 (pine_v2 H2 심화 + Trading UI Kill Switch + dogfood baseline) PR #69 main merged.
남은 H1 게이트: Bybit Demo dogfood 3~4주 (사용자 수동 · 병렬 진행) + Path β Gate-4 nightly (실질 완료).

이번 세션은 **H2 본격 첫 스프린트**. Trust 최우선.
Narrowest wedge persona pain: "백테스트 결과 얼마나 믿을 수 있나?" (overfitting 불안).

## 이번 세션 범위 (H2 Kickoff plan §4 Sprint 9 6 tasks)

- 9-1 Monte Carlo 리샘플링 엔진 (bootstrap 1000회) — 수익률 분포 + 95% CI
- 9-2 Walk-Forward Analysis — train/test window 이동, out-of-sample 성과
- 9-3 Frontend UI — 백테스트 결과 탭에 MC/WFA 섹션 추가 (recharts 3.8.1 재사용)
- 9-4 관측성 Phase 1 — Prometheus metric 5종 실측
- 9-5 Grafana Cloud Free 대시보드 + alert 1개 (order_rejected_rate > 10%)
- 9-6 Idempotency-Key 지원 (POST /backtests) — Beta 전 필수

**Out-of-scope (Sprint 10으로 이관):** parameter stability 분석, Multi-worker split-brain Redis lock, Bayesian 최적화.

## 개발 방법론 (필수)

### 1. superpowers:writing-plans
- Phase별 SDD 작성 → `docs/superpowers/plans/2026-04-??-h2-sprint9-phase-*.md`
- `writing-plans` 스킬 호출해서 Phase A/B/C/D 로 쪼개기 (아래 §Phase 분해)
- 각 Phase SDD는 계약 (타입 시그니처, 파일 경로, 검증 명령) 수준으로 구체적으로

### 2. superpowers:subagent-driven-development
- 각 Phase SDD 완성 후 **worktree isolation** Agent 로 디스패치
- 독립적 Phase는 병렬 워커 (H2 Sprint 1 성공 패턴 재사용). 의존 관계는 직렬
- Agent 프롬프트는 "결과 요약 JSON" 반환 지시 (커밋 해시, 테스트 수, 이슈 목록, 머지 여부)

### 3. superpowers:test-driven-development
- 각 Phase 구현 **전** 테스트 작성 (RED)
- 최소 구현으로 테스트 통과 (GREEN)
- 리팩터링 (REFACTOR)
- Monte Carlo / WFA 는 성질 테스트 (property-based) + golden snapshot 병행
- Coverage target: 신규 코드 90%+

### 4. Generator-Evaluator 패턴 (H2 Sprint 1 성공 모델 재사용)
- 각 Phase 구현 완료 → 3-way blind review
  - **Evaluator 1 (codex CLI, `codex exec`)**: `git diff` + Golden Rules 체크리스트 입력
  - **Evaluator 2 (Agent subagent_type=general-purpose, model=opus)**: 변경 파일 목록만
  - **Evaluator 3 (Agent subagent_type=general-purpose, Sonnet)**: PR 본문 초안 + 테스트 결과 요약만
- PASS 기준: 평균 confidence ≥ 8/10, blocker 0, major ≤ 2
- GWF (Go With Fix) 수신 시: 지적 항목만 단독 fix 커밋 → re-evaluate. 최대 3 iter
- 3회 FAIL 시: 해당 항목만 분리하여 후속 PR 이관

## 브랜치 전략 (Option C)

```
main
 └─ stage/h2-sprint9  ← 사용자가 최종 main PR 수동 생성
     ├─ feat/h2s9-stress-test-engine     (9-1, 9-2 엔진 + service)
     ├─ feat/h2s9-stress-test-api        (9-1, 9-2 router + schemas + Celery task + idempotency 9-6)
     ├─ feat/h2s9-frontend-mcwfa-ui      (9-3)
     └─ feat/h2s9-observability          (9-4, 9-5)
```

Phase A (엔진) → Phase B (API+Idempotency) 직렬.
Phase C (FE), Phase D (관측성)는 Phase B 머지 후 병렬.

## Phase 분해 초안 (writing-plans 스킬에서 확정)

### Phase A — Monte Carlo + Walk-Forward 엔진 (9-1, 9-2)

**위치:** `backend/src/stress_test/engine/`

**핵심 계약:**
- `run_monte_carlo(equity_curve, *, n_samples=1000, seed=42) -> MonteCarloResult`
  → 기존 `backend/src/backtest/monte_carlo.py` (stub 77 lines) 를 `stress_test/engine/monte_carlo.py`로 이관·확장
- `run_walk_forward(strategy_id, ohlcv, *, train_window, test_window, step) -> WalkForwardResult`
- 모든 금액은 `Decimal` (float 금지 — Golden Rule), seed 고정으로 snapshot 테스트 가능
- `MonteCarloResult`: samples, ci_lower_95, ci_upper_95, median_final_equity, max_drawdown_mean, max_drawdown_p95, **equity_curves_percentiles** (p5/p25/p50/p75/p95 time series)
- `WalkForwardResult`: folds (list of {train_range, test_range, in_sample_return, out_of_sample_return, oos_sharpe}), aggregate_oos_return, degradation_ratio (IS/OOS)

**기존 자산 재사용:**
- `backend/src/backtest/engine/metrics.py` — Sharpe, max_drawdown 계산 로직 재사용
- `backend/src/backtest/engine/types.py` — BacktestResult 타입
- vectorbt vectorized portfolio — WFA train run 에 재사용

**TDD 순서:**
1. `test_monte_carlo_deterministic_with_seed.py` — seed=42 → 동일 결과 (snapshot)
2. `test_monte_carlo_ci_bounds.py` — lower ≤ median ≤ upper 불변
3. `test_monte_carlo_sample_count.py` — n_samples=1000 → returns 분포 길이 정합
4. `test_walk_forward_no_lookahead.py` — test window 가 train window 이후인지 (반례: lookahead bias)
5. `test_walk_forward_degradation_ratio.py` — IS/OOS 비율 정상 계산

**성능 가드:** 1년 1H 백테스트 MC 1000회 < 10 초 (Numba 미사용). 초과 시 batch 벡터화 또는 500회 감소 옵션 (H2 Kickoff §리스크).

### Phase B — stress_test API + Celery Task + Idempotency (9-1, 9-2, 9-6)

**위치:** `backend/src/stress_test/{router,service,repository,schemas,dependencies,tasks}.py`

**엔드포인트 (endpoints.md §stress_test 참조):**
- `POST /api/v1/stress-test/monte-carlo` → 202 Accepted + task_id (Celery)
- `POST /api/v1/stress-test/walk-forward` → 202 Accepted + task_id
- `GET /api/v1/stress-test/:id` → 결과 조회 + status (pending|running|completed|failed)

**도메인 규칙 준수:**
- Router → Service → Repository 3-Layer. AsyncSession은 Repository만
- service.py 는 AsyncSession import 금지 (`.ai/stacks/fastapi/backend.md` §3)
- Celery prefork-safe (Sprint 4 D3 교훈) — 모듈 import 시점 무거운 객체 생성 금지, lazy init

**Idempotency (9-6):**
- `POST /api/v1/backtests` 에 `Idempotency-Key` 헤더 지원
- 기존 trading/orders idempotency 패턴 재사용 (`backend/src/trading/` 참고)
- advisory lock + body_hash 저장 → 같은 키 + 같은 body → 기존 결과 반환

### Phase C — Frontend MC/WFA UI (9-3)

**위치:**
- `frontend/src/features/backtest/components/stress-test-panel.tsx` (신규)
- `frontend/src/features/backtest/hooks.ts` (확장)
- `frontend/src/features/backtest/schemas.ts` (MonteCarloResult / WalkForwardResult zod)

**UI 요구사항:**
- 백테스트 상세 페이지에 "Stress Test" 탭 추가 (기존 탭 구조 확장)
- Monte Carlo: recharts AreaChart (p5~p95 fan chart) + median line + CI 표시
- Walk-Forward: recharts BarChart (fold별 IS vs OOS return) + degradation ratio 텍스트
- 실행 버튼 → `POST /stress-test/monte-carlo` → polling 으로 상태 업데이트
- 진행 중일 때 skeleton, 에러 시 retry 버튼

**LESSON-004 준수:**
- `useEffect` dep 에 React Query `data` 객체 직접 사용 금지 (H-1)
- 폴링은 기존 `useOrders` 패턴 (refetchInterval + dep array 없는 sync useEffect) 재사용
- `react-hooks/exhaustive-deps` disable 절대 금지

### Phase D — 관측성 Phase 1 (9-4, 9-5)

**위치:**
- `backend/src/common/metrics.py` (신규, `prometheus_client`)
- `backend/pyproject.toml` — `prometheus-client` dep 추가
- Grafana Cloud Free 계정 설정 (사용자 수동)

**Prometheus metric 5종:**
1. `qb_backtest_duration_seconds` (histogram) — 백테스트 실행 시간
2. `qb_order_rejected_total` (counter, labels=[exchange, reason]) — 주문 거부
3. `qb_kill_switch_triggered_total` (counter, labels=[trigger_type]) — Kill Switch 발동
4. `qb_ccxt_request_duration_seconds` (histogram, labels=[exchange, endpoint]) — 거래소 API latency
5. `qb_active_orders` (gauge) — 현재 pending+submitted 주문 수

**Endpoint:** `GET /metrics` (Prometheus text format), Clerk 인증 제외

**Grafana alert:**
- `rate(qb_order_rejected_total[5m]) / rate(qb_orders_total[5m]) > 0.1` → alert
- Grafana Cloud Free 웹훅 (Slack / Discord) 설정

**검증:**
- `curl localhost:8000/metrics` → 5 metric line 포함
- 테스트 이벤트 1건 발동 후 Grafana 패널에서 카운터 증가 확인 (사용자 수동 smoke)

## 핵심 참조 문서 (세션 시작 시 필수 선독)

- `docs/superpowers/plans/2026-04-20-h2-kickoff.md` §4 Sprint 9 (12~170줄)
- `docs/02_domain/domain-overview.md` §stress_test
- `docs/03_api/endpoints.md` §stress_test (75~85줄)
- `backend/src/backtest/monte_carlo.py` (기존 stub, 77줄)
- `backend/src/stress_test/` 스캐폴딩 (대부분 1줄 — 채워야 함)
- `backend/src/backtest/engine/metrics.py` (Sharpe, MDD 재사용)
- `AGENTS.md` §현재 작업 (H2 Sprint 1 완료 반영됨)
- `.ai/stacks/fastapi/backend.md` §3 아키텍처 (Router/Service/Repository)
- `.ai/stacks/nextjs/frontend.md` §React Hooks 안전 규칙 H-1~H-4

## 주의사항 (H2 Sprint 1 실측 learnings)

### 구현 함정
- **Decimal-first 합산**: `Decimal(str(a)) + Decimal(str(b))` (Sprint 4 D8 교훈)
- **Celery prefork-safe**: `create_async_engine()` / vectorbt 는 lazy init. 모듈 import 시점 호출 금지
- **seed=42 고정**: MC resampling 은 pytest snapshot 가능하도록 결정적
- **Golden Rules**:
  - 환경변수 하드코딩 금지
  - `.env.example`에 없는 변수 code 참조 금지 (smoke test: `grep` 검증)
  - 금융 숫자 Decimal (float 금지)
  - 백테스트는 Celery 비동기 (직접 실행 금지)

### Evaluator 운영 learnings (iter-1 실측)
- codex CLI 는 `.ai/stacks/nextjs/frontend.md` H-1 같은 **프로젝트 규칙**을 엄격히 적용 → FE hook 작성 시 `useEffect` dep 에 `query.data` 절대 금지
- Opus blind (파일 목록만) 는 **경로 컨벤션** 감지에 강함 → `features/*` vs `app/*/_components/` 경계 미리 확인
- Sonnet blind (PR 본문만) 는 **엣지 케이스 누락**을 잘 찾음 → PR 본문에 알고리즘 가정 (seed, window 크기, degradation 정의) 명시

### 병렬 worker 조합
- Agent worktree isolation (H2 Sprint 1 에서 Phase B/C 병렬 성공)
- stage/h2-sprint9 이 다른 worktree 에서 체크아웃되면 → 해당 worktree 경로에서 직접 merge
- pre-push hook: `backend/` 변경 시 `ruff check + pytest` 자동 실행 (~3분). `frontend/` 변경 시 `eslint` 만 (빠름)

## 커밋 단위 초안

```
c1 feat(stress-test): Monte Carlo engine — bootstrap 1000회 + CI + equity percentiles (Phase A)
c2 feat(stress-test): Walk-Forward Analysis — rolling train/test + degradation ratio (Phase A)
c3 feat(stress-test): API router + Celery task + schemas (Phase B)
c4 feat(backtest): Idempotency-Key 지원 (POST /backtests) (Phase B, 9-6)
c5 feat(frontend-bt): stress-test panel — MC fan chart + WFA bar chart (Phase C)
c6 feat(observability): Prometheus metrics 5종 + /metrics endpoint (Phase D)
c7 docs(observability): Grafana Cloud Free 대시보드 + alert 1개 설정 runbook (Phase D)
```

## 시작 시퀀스

1. `superpowers:writing-plans` 스킬 호출 → Phase A 부터 SDD 작성
2. Phase A SDD 검토 (사용자 승인) → `superpowers:test-driven-development` 스킬 호출 → 테스트 먼저 작성
3. `superpowers:subagent-driven-development` 스킬 호출 → Agent worktree 디스패치
4. 구현 완료 → 3-way Evaluator → iter-1 fix 필요 시 처리
5. Phase B/C/D 반복

**첫 질문 금지** — 플랜 파일 먼저 읽고 시작. 질문 필요 시 `AskUserQuestion` 툴 사용.
````

<!-- ✂ COPY END ──────────────────────────────────────────────────── -->

---

## 체크리스트 (세션 마감 시)

- [ ] Phase A/B/C/D 4개 SDD 작성 완료 (`docs/superpowers/plans/2026-04-??-h2-sprint9-phase-*.md`)
- [ ] 각 Phase 3-way Evaluator PASS (blocker 0, major ≤ 2)
- [ ] Backend 전체 pytest green (1015 + Sprint 9 신규)
- [ ] Frontend 전체 pnpm test green (173 + Sprint 9 신규)
- [ ] mypy 0 에러 / ruff clean / lint clean
- [ ] stage/h2-sprint9 → main PR 생성
- [ ] CI 전체 green
- [ ] AGENTS.md §현재 작업 Sprint 9 완료 추가
- [ ] MC/WFA 본인 사용 1회 이상 (주관 평가 기록 `docs/dev-log/`)
