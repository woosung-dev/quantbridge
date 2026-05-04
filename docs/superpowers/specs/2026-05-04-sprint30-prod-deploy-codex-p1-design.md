# Sprint 30 — Production 배포 + Sprint 29 codex G2 P1 hotfix (Design Spec)

> **Date:** 2026-05-04
> **Sprint:** 30 (Type B — risk-critical, production 배포)
> **Branch:** `stage/h2-sprint30-prod-deploy-codex-p1` @ `dedfb35` (Sprint 29 stage HEAD 위 cascade)
> **Plan v1:** brainstorming session 결과 (D1~D6 + 인프라 결정)
> **Time budget:** 7-13h, 5-6 Slice
> **메타-방법론:** LESSON-037 영구 적용 first sprint (baseline 재측정 preflight 의무)

---

## 1. Context

### 1.1 왜 Sprint 30

Sprint 29 종료 후 본인 dogfood narrowest wedge 도달 (Pine 통과율 5/6 + DrFXGOD 명확 응답 + Trust Layer 보호 production 강제). 다음 자연 trigger = production 배포 + Sprint 29 deferred 정리.

### 1.2 결정 (brainstorming session)

- **D1 scope:** Beta open 인프라 (옵션 A) — 5 옵션 중 narrowest wedge 정합
- **D2 분해:** A2 (BL-070~072 + codex G2 P1 4건) → 사용자 결정으로 **도메인 / Resend deferred** (Sprint 31+) → BL-071 Backend prod + codex G2 P1 4건만
- **D3 실행:** Slice 병렬 활용 (작은 BE → 큰 BE → FE → deploy 마지막)
- **D4 인프라:** GCP Cloud Run (asia-northeast3) / Vercel (frontend) / 도메인 deferred → default URL 사용 / Resend deferred
- **D6 순서:** (S6 ‖ S7) → S4 → S5 → S8 (선택) → S2 deploy 마지막

### 1.3 의도된 outcome

- **Production 배포** — Backend (GCP Cloud Run default URL) + Frontend (Vercel default URL) — Beta tester 외부 접근 가능
- **Sprint 29 codex G2 P1 4건 처리** — FE Zod schema / Backtest 422 schema / unsupported_calls occurrence-based / UtBot e2e vectorbt
- **Beta path A1 진행** — 도메인/Resend 는 Sprint 31+ 로 분리 (manual welcoming + Twitter 캠페인 후 Beta tester 5명 onboarding 후)

---

## 2. Architecture

```
[Sprint 29 deferred] codex G2 P1 4건
  ├─ S4 Backtest 422 schema (BE)
  ├─ S5 FE Zod + UI (depends on S4)
  ├─ S6 unsupported_calls occurrence (BE regex.start())
  └─ S7 UtBot e2e vectorbt (BE BacktestService)

[Beta open 인프라 코어]
  └─ S2 Backend prod (GCP Cloud Run) + Frontend prod (Vercel)
```

### 2.1 Slice 분해 (5-6 Slice)

| Slice  | scope                                                                                                                                     | 시간 | 의존                                        | type     |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------- | -------- |
| **S6** | unsupported_calls occurrence-based (regex.start() line/col, multiple lines 처리)                                                          | 1-2h | 없음                                        | hotfix   |
| **S7** | UtBot e2e fixture 실제 vectorbt run (BacktestService 호출 통합)                                                                           | 1-2h | 없음                                        | hotfix   |
| **S4** | Backtest 422 응답 schema (`unsupported_calls` 포함) + Pydantic round-trip                                                                 | 1-2h | 없음 (BE 영역, S6 와 coverage.py 충돌 가능) | hotfix   |
| **S5** | FE Zod schema 갱신 + UI 표시 (`unsupported_calls` / `dogfood_only_warning` / `degraded_calls`) + ParsePreviewPanel + Backtest reject 알림 | 3-5h | S4                                          | feature  |
| **S8** | workaround 정확도 검증 (ALMA/WMA/OBV) — ADR-009 미니 검토 (선택)                                                                          | 1-2h | 없음                                        | optional |
| **S2** | Backend prod (GCP Cloud Run asia-northeast3) + Frontend prod (Vercel)                                                                     | 2-4h | 모든 code Slice 완료                        | infra    |

총 시간 = 7-13h (S8 포함 시 +1-2h)

### 2.2 실행 순서 (D6 권장)

```
Phase 1 (BE small): (S6 ‖ S7) 병렬, 1-2h
Phase 2 (BE schema): S4, 1-2h (S6 후 coverage.py 충돌 회피)
Phase 3 (FE): S5, 3-5h (S4 의존)
Phase 4 (선택): S8, 1-2h
Phase 5 (deploy): S2, 2-4h (모든 code 완료 후)
```

---

## 3. Components

### 3.1 Slice S6 — unsupported_calls occurrence-based (1-2h)

**목표:** codex G2 P1-4 fix — 같은 함수가 여러 라인에 있을 때 first 만 반환하던 문제 해결.

**수정 파일:**

- `backend/src/strategy/pine_v2/coverage.py` — `_find_line()` → `_find_occurrences()` 변경
- `analyze_coverage()` — `unsupported_calls` 가 occurrence 기반 (regex.start() per match) 으로 수집

**구현:**

```python
def _find_occurrences(source: str, pattern: str) -> list[tuple[int, int]]:
    """source 에서 pattern 의 모든 occurrence 의 (line, col) 반환 (1-indexed)."""
    escaped = re.escape(pattern)
    occurrences = []
    for m in re.finditer(rf"\b{escaped}\b", source):
        # offset → line/col 변환
        line = source[:m.start()].count('\n') + 1
        last_newline = source.rfind('\n', 0, m.start())
        col = m.start() - last_newline if last_newline != -1 else m.start() + 1
        occurrences.append((line, col))
    return occurrences
```

**TDD:**

- DrFXGOD 의 `fixnan` 같은 multiple line 함수 검출 (line 105 외 추가 위치)
- existing test 회귀 (single occurrence 기존 결과 유지)

### 3.2 Slice S7 — UtBot e2e fixture 실제 vectorbt run (1-2h)

**목표:** codex G2 P1-7 fix — UtBot e2e 가 coverage PASS 만 검증, 실제 backtest 실행 미검증 문제.

**수정 파일:**

- `backend/tests/strategy/pine_v2/test_utbot_strategy_e2e.py` (Sprint 29 신규) — 실제 backtest run 추가
- `backend/tests/strategy/pine_v2/test_utbot_indicator_e2e.py` (Sprint 29 신규) — 동일

**구현 패턴:**

- BacktestService.submit() 호출 (`allow_degraded_pine=True` 명시)
- vectorbt 실행 (Celery task 또는 직접 사용)
- entries/exits 갯수 + equity_curve > 0 검증

**TDD:**

- UtBot indicator: `assert num_trades >= 1`
- UtBot strategy: `assert equity > initial_capital * 0.5` (drawdown 50% 이내 sanity)

### 3.3 Slice S4 — Backtest 422 응답 schema (1-2h)

**목표:** codex G2 P1-5 fix — Backtest reject 응답이 `unsupported_calls` 포함 안 함, parse-preview 만 적용된 문제.

**수정 파일:**

- `backend/src/backtest/exceptions.py` — `StrategyNotRunnable.unsupported_calls: list[UnsupportedCall]` field 추가
- `backend/src/backtest/service.py:_submit_inner` — `coverage.unsupported_calls` 를 exception 에 전달
- `backend/src/main.py` (또는 exception handler) — Pydantic schema 응답 직렬화

**TDD:**

- DrFXGOD strategy backtest submit → 422 응답 안 `unsupported_calls` (28 항목) 포함 verify
- backward-compat — 기존 `unsupported_builtins` 필드도 유지

### 3.4 Slice S5 — FE Zod schema + UI (3-5h)

**목표:** Sprint 29 BE 변경 (`unsupported_calls` / `dogfood_only_warning` / `degraded_calls`) 가 FE 에서 표시되도록 갱신.

**수정 파일:**

- `frontend/src/features/strategy/schemas.ts` — Zod schema:

  ```typescript
  const UnsupportedCallSchema = z.object({
    name: z.string(),
    line: z.number(),
    col: z.number().nullable(),
    workaround: z.string().nullable(),
    category: z.enum(['drawing', 'data', 'syntax', 'math', 'other']),
  });

  // ParsePreviewResponse 에 추가
  unsupported_calls: z.array(UnsupportedCallSchema).default([]),
  dogfood_only_warning: z.string().nullable(),
  ```

- `frontend/src/features/backtest/schemas.ts` — Backtest 422 응답 schema (`unsupported_calls`)
- `frontend/src/features/backtest/schemas.ts` — `CreateBacktestRequest.allow_degraded_pine: boolean` 추가
- `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx` — UI 갱신:
  - `dogfood_only_warning` 가 있으면 노란 alert 표시 (heikinashi Trust Layer 위반 안내)
  - `unsupported_calls` 가 있으면 line + workaround 표시 (collapsible list)
- `frontend/src/app/(dashboard)/backtests/new/...` — Backtest reject UI:
  - 422 응답의 `unsupported_calls` 표시
  - `degraded_calls` 가 있으면 명시 동의 checkbox (`allow_degraded_pine=true` 토글)

**TDD:**

- Vitest unit: schema parse 회귀
- Component test: dogfood_only_warning 가 있으면 alert 표시
- Component test: unsupported_calls 표 렌더 + workaround 표시
- Component test: degraded checkbox 동의 후 backtest submit 가능

### 3.5 Slice S8 — workaround 정확도 검증 (선택, 1-2h)

**목표:** codex G2 P1-6 fix — workaround 문구 정확성 검증 (ALMA/WMA/OBV).

**수정 파일:**

- `backend/src/strategy/pine_v2/coverage.py` — `_UNSUPPORTED_WORKAROUNDS` dict 의 ALMA/WMA/OBV 항목 ADR-009 link 추가 또는 정확도 명시
- `docs/dev-log/2026-05-04-sprint30-workaround-accuracy.md` (신규) — workaround 정확도 검증 결과 영구 기록

**구현 (선택):**

- ALMA: ta.sma 근사 정확도 < 1% 검증 fail 시 ADR-009 trigger 명시
- WMA: ta.sma vs ta.ema 근사 비교 결과
- OBV: 단순 누적 sum 정확도

**TDD:**

- 정확도 비교 test (ta.alma vs ta.sma deviation)

### 3.6 Slice S2 — Production 배포 (2-4h)

**목표:** Backend (GCP Cloud Run) + Frontend (Vercel) production 배포.

**수정 파일:**

- `backend/Dockerfile` — production 최적화 (multi-stage build, slim Python)
- `backend/cloudbuild.yaml` (신규) — GCP Cloud Build 또는 직접 deploy 스크립트
- `backend/.env.production.example` — production 환경 변수 list
- `.github/workflows/deploy-backend.yml` (선택) — auto deploy
- `frontend/vercel.json` — deploy config (이미 있을 수 있음)
- `docs/07_infra/production-deploy.md` (신규) — 배포 runbook

**환경 변수 (Cloud Run secrets):**

- `DATABASE_URL` — TimescaleDB Cloud (또는 GCE self-hosted)
- `REDIS_URL` — GCP Memorystore
- `CLERK_SECRET_KEY` — Clerk production keys (사용자 manual)
- `CLERK_PUBLISHABLE_KEY`
- `BYBIT_DEMO_API_KEY` / `BYBIT_DEMO_SECRET`
- `JWT_SECRET`
- `ENCRYPTION_KEY` (AES-256)
- `APP_ENV=production`

**환경 차이:**

- region: `asia-northeast3` (Seoul) latency 최저
- DB / Redis: production instance (별도)
- Clerk: production environment (dev → prod 전환, 사용자 manual)

**TDD:**

- Health check (`GET /health` 200 응답)
- API smoke (Clerk auth + parse-preview default URL)
- careful mode 의무 (downtime risk)

---

## 4. Data Flow

```
사용자 strategy 등록 (FE → BE)
  ↓
parse-preview API
  ├─ unsupported_calls (S6 occurrence-based) — line/col 정확
  ├─ dogfood_only_warning (heikinashi)
  └─ degraded_calls (Trust Layer 보호)
  ↓
FE 표시 (S5)
  ├─ unsupported_calls 표 (line + workaround)
  ├─ dogfood_only_warning alert (노란 경고)
  └─ degraded_calls → backtest 시 allow_degraded_pine 동의 checkbox
  ↓
backtest submit
  ├─ allow_degraded_pine=False + degraded → 422 (S4 응답 schema)
  ├─ allow_degraded_pine=True → 202 + Celery task
  └─ unsupported (1+ 미지원) → 422 + unsupported_calls (S4)
  ↓
vectorbt 실행 (Celery worker)
  └─ S7: UtBot e2e fixture 실제 backtest 검증
```

---

## 5. Error Handling

| 상황                                         | 처리                                                                                           |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **production deploy 실패** (S2)              | careful mode + rollback 절차. Cloud Run revision 회귀                                          |
| **DB migration prod fail**                   | alembic upgrade head 실패 시 rollback. 2-step deploy 패턴 (코드 deploy → migration → 재verify) |
| **Clerk prod key 미설정**                    | env validation 시점 fail-fast (uvicorn 시작 실패)                                              |
| **default URL CORS**                         | `NEXT_PUBLIC_API_URL` Cloud Run URL 명시. CORS 허용 origin (Vercel default URL)                |
| **degraded_calls 명시 동의 누락** (S4)       | 422 + 사용자에게 명확 안내 (FE checkbox 표시)                                                  |
| **multiple line occurrence regex 충돌** (S6) | 기존 single occurrence test 회귀 0                                                             |

---

## 6. Testing Strategy / Dual Metric

### 6.1 정량 metric

| Metric                      | 통과 기준                                              | 측정                                 |
| --------------------------- | ------------------------------------------------------ | ------------------------------------ |
| Production deploy           | Backend + Frontend default URL 200 응답                | curl health check                    |
| Pine 통과율                 | 진입 5/6 → 종료 5/6 (regression 0)                     | analyze_coverage 6 fixture           |
| DrFXGOD response            | 28 unsupported_calls (S6 occurrence 적용 후 변동 가능) | test_drfx_response_schema.py         |
| FE Zod schema parse         | 모든 신규 필드 round-trip                              | Vitest                               |
| Backtest 422 응답 schema    | unsupported_calls / degraded_calls 포함                | test_backtest_reject.py              |
| UtBot e2e 실제 vectorbt run | num_trades >= 1                                        | test*utbot*\*\_e2e.py                |
| Self-assessment             | ≥ 7/10                                                 | dev-log frontmatter                  |
| 신규 BL                     | P0=0, P1≤2                                             | sprint 안 추가                       |
| 기존 P0 잔여                | ≤ 2 (BL-003/005 deferred)                              | sprint 종료 카운트                   |
| BE regression               | 1448/1448 (Pine v2 + backtest)                         | pytest (DB env 1 ERROR pre-existing) |
| FE regression               | 257/257 + S5 신규 component test                       | pnpm test                            |
| ruff/mypy/tsc/eslint        | 0/0/0/0                                                | make be-check && make fe-check       |

### 6.2 검증 명령

```bash
# 0. baseline 재측정 (LESSON-037 영구 적용 first sprint)
cd backend && PYTHONPATH=. .venv/bin/python -c "..."  # 5/6 통과율 anchor

# 1. S6 unsupported_calls occurrence
cd backend && pytest tests/strategy/pine_v2/test_drfx_response_schema.py -v

# 2. S7 UtBot e2e vectorbt
cd backend && pytest tests/strategy/pine_v2/test_utbot_*_e2e.py -v

# 3. S4 Backtest 422 schema
cd backend && pytest tests/backtest/test_strategy_not_runnable.py -v

# 4. S5 FE Zod schema + UI
cd frontend && pnpm test -- features/strategy/schemas
cd frontend && pnpm test -- ParsePreviewPanel

# 5. 전체 BE/FE regression
cd backend && pytest -v
cd frontend && pnpm test

# 6. S2 production deploy verify
curl -s https://quantbridge-xxxxxx.run.app/health  # backend
curl -s https://quantbridge.vercel.app  # frontend
```

### 6.3 메타-방법론 (Sprint 30 의무)

- **LESSON-037 baseline 재측정 preflight (영구 적용 first sprint)**
- LESSON-033 Sprint type 분류 = B (risk-critical, production)
- LESSON-035 dual metric (third validation, Sprint 30 = third)
- LESSON-036 Slice cascade Option C (영구 승격 trigger 도달 — Sprint 25/28/29/30 = 4회 누적)
- codex G0 (Slice S5 schema 직후) 의무
- codex challenge G2 (production deploy 직전 의무) — Trust Layer / 보안 / 환경 변수
- /review (PR squash merge 전 의무)
- verification-before-completion (production smoke + 1448 BE regression)
- careful mode (Sprint 30 type B, production downtime risk)

---

## 7. Decisions (확정)

| ID              | 결정                                                                                                    | 근거                                              |
| --------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **D1**          | Sprint 30 scope = Beta open 인프라 (옵션 A) → 도메인/Resend deferred → A2-rev (Backend prod + codex P1) | narrowest wedge 도달 후 production 자연 trigger   |
| **D2**          | 5-6 Slice (S2 + S4-S8)                                                                                  | codex P1 4건 + production 통합                    |
| **D3**          | 도메인 deferred → Sprint 31+                                                                            | 사용자 명시 (Beta open 시 default URL 충분)       |
| **D3-Resend**   | Resend deferred → Sprint 31+                                                                            | 사용자 명시 (수동 onboarding 가능)                |
| **D4 backend**  | GCP Cloud Run (asia-northeast3)                                                                         | `.ai/stacks/fastapi/backend.md` 명시              |
| **D4 frontend** | Vercel (default URL)                                                                                    | rules 명시                                        |
| **D6 순서**     | (S6 ‖ S7) → S4 → S5 → S8 → S2 deploy                                                                    | DB env 충돌 회피 + deploy 마지막 (re-deploy 없음) |

---

## 8. 종료 trigger

**모든 조건 AND:**

- [ ] S6 + S7 + S4 + S5 commit + push (Sprint 30 stage cascade)
- [ ] S5 FE 갱신 — `unsupported_calls` / `dogfood_only_warning` / `degraded_calls` UI 표시
- [ ] S2 production deploy — Backend Cloud Run + Frontend Vercel default URL 정상
- [ ] Pine 통과율 5/6 regression 0 (Sprint 29 결과 유지)
- [ ] DrFXGOD response 28 unsupported_calls (S6 occurrence-based)
- [ ] BE 1448 regression + FE 257 regression
- [ ] codex challenge G2 (production deploy 직전)
- [ ] /review (PR squash merge 전)
- [ ] PR 생성 + 사용자 squash merge → main
- [ ] §14 종료 시점 docs update (CLAUDE.md / dev-log retrospective / INDEX / lessons.md / TODO)

**Sprint 31+ 진입 가능 시점:** BL-003 Bybit mainnet runbook (Bybit Demo 1주 안정 후) / 도메인 + Resend 통합 / BL-073 Twitter 캠페인 / BL-074 인터뷰.

---

## 9. References

### 9.1 Sprint 29 (직전)

- Plan: `docs/superpowers/plans/2026-05-04-sprint29-coverage-hardening.md`
- Spec: `docs/superpowers/specs/2026-05-04-sprint29-coverage-hardening-design.md`
- Retrospective: `docs/dev-log/2026-05-04-sprint29-coverage-hardening.md`
- PR #114: https://github.com/woosung-dev/quantbridge/pull/114

### 9.2 영구 규칙

- `.claude/CLAUDE.md` Pine 영구 규칙
- `.ai/stacks/fastapi/backend.md` GCP Cloud Run + Docker
- `.ai/stacks/nextjs/frontend.md` Vercel
- `.ai/project/lessons.md` LESSON-037 영구 적용

### 9.3 BL audit (Sprint 30 진입)

- BL-070 도메인+DNS → **Sprint 31+ deferred** (사용자 결정)
- BL-071 Backend prod → **Sprint 30 처리 (S2)**
- BL-072 Resend → **Sprint 31+ deferred** (사용자 결정)
- BL-073 Twitter 캠페인 → 사용자 manual, BL-070~072 후
- BL-074 인터뷰 → 사용자 manual, BL-073 후
- BL-075 H2 게이트 → BL-005 self-assess ≥7 후 (trigger 미도래)
- codex G2 P1 4건 → **Sprint 30 처리 (S4/S5/S6/S7)**
- codex G2 P1-6 workaround 정확도 → **Sprint 30 선택 (S8)** 또는 ADR-009 deferred

### 9.4 LESSON 적용

- **LESSON-037** baseline 재측정 preflight (영구 적용 first sprint)
- LESSON-033 Sprint type 분류 = B (third validation)
- LESSON-035 dual metric (third validation)
- LESSON-036 Slice cascade Option C (4th 누적, 영구 적용)

---

**End of Sprint 30 design spec.**
