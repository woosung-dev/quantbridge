# Next Session — Testnet Dogfood 풀 준비 + Sprint 9 선행 (14~20h)

> **생성일:** 2026-04-21
> **목적:** 새 세션에서 복사-붙여넣기로 바로 시작 가능한 longrun 프롬프트
> **시간 예산:** 14~20h / 6 PR / 4 Phase
> **사용법:** 새 Claude Code 세션에서 아래 `## 📋 세션 시작 프롬프트 (복사용)` 섹션 전체를 복사해서 첫 메시지로 붙여넣기

---

## 1. 이 세션이 생성된 맥락

이전 세션(2026-04-20 ~ 2026-04-21)에서 H1 Stealth 클로징 5-Step 풀패키지가 완료됨:

- **PR #37** `chore(docs): Bundle 2 클로징 동기화` — TODO/아카이브
- **PR #38** `feat(trading): Kill Switch capital_base 동적 바인딩 + notional check` — 837 tests pass
- **PR #39** `chore(infra): Bybit mainnet dogfood 준비` — runbook + checklist + smoke script
- **PR #40** `docs(roadmap): H2 kickoff plan + H1 클로징 sync`

모두 main에 merge됨. **H1 코드 게이트 100% 완료. 남은 건 dogfood 1~2주만.**

### 핵심 결정 변경 (2026-04-21)

사용자가 **실자본 mainnet dogfood → testnet only 3~4주로 변경** 결정. 이유:

- 기술 검증은 testnet에서 90% 이상 충분
- 실자본 부담 제거
- Beta 오픈(Sprint 11-5) 전에는 극소액 mainnet 1주 별도 진행 검토

따라서 이번 세션 범위는:

1. **roadmap H1→H2 gate 수정** (실자본 → testnet 3~4주)
2. **Testnet dogfood 준비 완성**
3. **Testnet 신뢰도 보강** (fee/funding 시뮬레이션)
4. **Sprint 9 일부 선행** (dogfood 기간 병렬 활용)

---

## 2. Phase 1~4 전체 명세

### Phase 1 — Dogfood 준비 (4~6h, PR-A + PR-B)

| Step | 내용                                                            | 소요 | 결과물                                                                                                                                                    |
| :--: | --------------------------------------------------------------- | :--: | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1   | `docs/00_project/roadmap.md` H1→H2 gate 수정                    | 30분 | "실자본 1주" → "Testnet 3~4주 + 극소액 mainnet 72h 선택"                                                                                                  |
|  2   | `docs/07_infra/bybit-mainnet-checklist.md` 확장                 | 30분 | Testnet 3~4주 섹션 추가 (기존 mainnet 옆에)                                                                                                               |
|  3   | `docs/07_infra/h1-testnet-dogfood-guide.md` **신규**            |  2h  | 전략 선정 · 일일 절차 · 종료 기준 · 리스크 대응 (150~200줄)                                                                                               |
|  4   | `docs/reports/_template-h1-dogfood-retrospective.html` **신규** | 30분 | dogfood 종료 시 바로 작성 가능한 HTML skeleton                                                                                                            |
|  5   | **M1 Credentials.testnet 필드화**                               | 1~2h | `backend/src/trading/providers.py` 하드코딩 `"testnet": True` 해제 → `Credentials.testnet: bool` 필드 + `ExchangeAccount.mode=="live"` 분기 + 회귀 테스트 |

**PR 구성:**

- **PR-A** (docs): Steps 1~4
- **PR-B** (code): Step 5

### Phase 2 — Testnet 신뢰도 보강 (4~6h, PR-C + PR-D)

**목표:** Testnet 약점(fee/funding) 중 2개 시뮬레이션 보강 → 검증률 85% → 92%.

| Step | 내용                                  | 소요 | 결과물                                                                                                                                                          |
| :--: | ------------------------------------- | :--: | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  6   | **B-1 Fee schedule 정확성 보강**      | 2~3h | `backend/src/trading/fees.py` 신규 — Bybit VIP tier CSV import → maker/taker fee 정확 계산 → `BacktestTrade.fee` post-processing                                |
|  7   | **B-2 Funding rate fetcher**          | 2~3h | `backend/src/trading/funding.py` 신규 + Celery beat (1시간 주기) — CCXT `fetch_funding_rate_history` → DB 저장 → 포지션 PnL 반영                                |
|  8   | **C-1 Dogfood 일일 리포트 자동 생성** | 2~3h | `backend/src/tasks/dogfood_report.py` + Jinja 템플릿 — Celery beat (22:00 UTC) → 오늘 PnL+trades+KS events → HTML 렌더 → `docs/reports/dogfood/YYYY-MM-DD.html` |

**PR 구성:**

- **PR-C** (trading 도메인 확장): Steps 6~7
- **PR-D** (reporting): Step 8

### Phase 3 — Sprint 9 선행 (4~6h, PR-E + PR-F)

**목표:** Sprint 9 task 6개 중 2개 미리 완료. Dogfood 기간(3~4주) 병렬 활용.

| Step | 내용                                 | 소요 | 결과물                                                                                                                             |
| :--: | ------------------------------------ | :--: | ---------------------------------------------------------------------------------------------------------------------------------- |
|  9   | **Sprint 9 writing-plans 세션**      |  1h  | `docs/superpowers/plans/2026-04-21-sprint9-plan.md` — task 9-1~9-6 분해 + 수락 기준                                                |
|  10  | **Sprint 9-6 Idempotency-Key**       |  2h  | `POST /backtests`에 Idempotency-Key header 지원 + body_hash 비교 + 409 conflict. Sprint 6 Trading 패턴 재사용                      |
|  11  | **Sprint 9-1 Monte Carlo 엔진 초안** | 3~4h | `backend/src/backtest/monte_carlo.py` 신규 — bootstrap 1000회 리샘플링 + 95% CI + `run_monte_carlo()` public API + snapshot 테스트 |

**PR 구성:**

- **PR-E** (backtest): Step 10
- **PR-F** (backtest): Step 11

### Phase 4 — Build-in-public + 마무리 (1~2h)

| Step | 내용                     | 소요 | 결과물                                                                           |
| :--: | ------------------------ | :--: | -------------------------------------------------------------------------------- |
|  12  | Twitter/X 첫 포스트 초안 | 30분 | `docs/marketing/2026-04-21-dogfood-start-thread.md` — 한국어 + 영어 (thread 3개) |
|  13  | 세션 종료 상태 대시보드  | 30분 | `docs/reports/2026-04-22-dogfood-start-dashboard.html` 또는 기존 HTML 업데이트   |

---

## 3. PR 전체 구성 (6 PRs)

|    PR    | 제목                                                         | Phase | 소요 | 유형 |
| :------: | ------------------------------------------------------------ | :---: | :--: | :--: |
| **PR-A** | `docs(roadmap+dogfood): H1 gate testnet 대체 + 3~4주 가이드` |   1   | 3~4h | docs |
| **PR-B** | `feat(trading): Credentials.testnet 필드 + mainnet 분기`     |   1   | 1~2h | code |
| **PR-C** | `feat(trading): Fee schedule 정확성 + funding rate fetcher`  |   2   | 4~6h | code |
| **PR-D** | `feat(reporting): Dogfood 일일 리포트 자동 생성`             |   2   | 2~3h | code |
| **PR-E** | `feat(backtest): Idempotency-Key 지원 (Sprint 9-6)`          |   3   |  2h  | code |
| **PR-F** | `feat(backtest): Monte Carlo 리샘플링 엔진 (Sprint 9-1)`     |   3   | 3~4h | code |

---

## 4. 실행 타임라인

| 누적 시간 | Step                                         |  PR  |
| :-------: | -------------------------------------------- | :--: |
|   0~1h    | Step 1~2 (roadmap + checklist)               |  —   |
|   1~3h    | Step 3 (dogfood 가이드)                      |  —   |
|   3~4h    | Step 4 (retro 템플릿) → **PR-A 생성**        | PR-A |
|   4~6h    | Step 5 (Credentials.testnet) → **PR-B 생성** | PR-B |
|   6~9h    | Step 6 (Fee 정확성)                          |  —   |
|   9~12h   | Step 7 (funding rate) → **PR-C 생성**        | PR-C |
|  12~15h   | Step 8 (dogfood 리포트) → **PR-D 생성**      | PR-D |
|  15~16h   | Step 9 (Sprint 9 writing-plans)              |  —   |
|  16~18h   | Step 10 (Idempotency-Key) → **PR-E 생성**    | PR-E |
|  18~21h   | Step 11 (Monte Carlo 초안) → **PR-F 생성**   | PR-F |

**중단 지점 후보:** 4h / 6h / 12h / 15h / 18h / 21h. Context fatigue 느끼면 12h(Phase 2 완료) 또는 15h(PR-D 완료)에서 자연 중단.

---

## 5. 실행 지침 (Orchestrator → 사용자)

### 자동 진행 패턴 (이전 H1 클로징 세션과 동일)

- **코드 작성, 파일 생성, 테스트 실행, docs 작성:** 자동 진행 (승인 불필요)
- **커밋, 푸쉬, PR 생성:** 사용자 승인 기반 (Git Safety Protocol)
  - 단, 사용자가 "쭉 진행해도 됨" 승인했으면 Phase 단위로 묶어서 진행 가능
- **중간 체크포인트 (PR-A/B/C/D/E/F 생성 시):** 각 PR URL만 보고, 사용자가 머지 후 다음 Phase 진행

### Git 브랜치 전략

- 각 PR마다 독립 브랜치 (main 기준 분기)
- 이전 PR 사용자 머지 후 main pull → 다음 브랜치 분기
- 예: `docs/h1-gate-testnet-dogfood` (PR-A), `feat/credentials-testnet-field` (PR-B), 등

### 사용자 승인 체크포인트 (필수)

|     시점     | 내용                       | 옵션                             |
| :----------: | -------------------------- | -------------------------------- |
|  시작 직전   | 플랜 확정                  | "쭉 진행" / "Phase 1만" / "수정" |
| Step 4 완료  | PR-A 생성 직전             | 커밋/푸쉬/PR 승인                |
| Step 5 완료  | PR-B 생성 직전             | 동일                             |
| Step 7 완료  | PR-C 생성 직전             | 동일 + 12h 중단 여부             |
| Step 8 완료  | PR-D 생성 직전             | 동일 + 15h 중단 여부             |
| Step 10 완료 | PR-E 생성 직전             | 동일                             |
| Step 11 완료 | PR-F 생성 직전 + 세션 종료 | 최종 승인                        |

### 승인 없이 자동 진행 조건 (메모리 규칙)

- 선택지 2개↑ 제시 시 별점 테이블 필수
- 추천도 차이 **2★ 이상**이면 추천안 자동 진행 (Git Safety 제외)
- 차이 1★ 이하면 사용자 선택 대기

---

## 6. 참조 문서 (필수 읽기)

### 프로젝트 컨텍스트

- `.claude/CLAUDE.md` — 프로젝트 전체 컨텍스트
- `.ai/common/global.md` — 개발 워크플로우
- `.ai/stacks/fastapi/backend.md` — FastAPI + SQLModel 규칙
- `~/.claude/projects/-Users-woosung-project-agy-project-quant-bridge/memory/MEMORY.md` — 사용자 기억

### H1 → H2 전환 관련

- `docs/00_project/roadmap.md` — Horizon × Pillars 로드맵 (수정 대상)
- `docs/superpowers/plans/2026-04-20-h2-kickoff.md` — H2 Sprint 9~11 분해 (Sprint 9-1, 9-6 참조)
- `docs/07_infra/runbook.md` §12 Bybit Testnet → Mainnet 전환
- `docs/07_infra/bybit-mainnet-checklist.md` — mainnet 체크리스트 (확장 대상)

### 상태 대시보드

- `docs/reports/2026-04-21-h1-closing-status-dashboard.html` — 현재 상태 시각화

### Kill Switch + Trading 도메인 (Step 5/6/7/8 참고)

- `backend/src/trading/providers.py` — BybitFuturesProvider (testnet 하드코딩 위치)
- `backend/src/trading/service.py` — ExchangeAccountService.fetch_balance_usdt (Step 6/7 확장 근거)
- `backend/src/trading/kill_switch.py` — CumulativeLossEvaluator (Step 7 funding rate 연동 후보)
- `backend/src/trading/models.py` — ExchangeAccount, Order, OrderState

### Backtest 도메인 (Step 10/11 참고)

- `backend/src/backtest/engine/` — run_backtest() entry point
- `backend/src/backtest/service.py` — BacktestService (Idempotency-Key 패턴)
- `backend/src/tasks/backtest.py` — Celery task (Monte Carlo 연동 고려)

---

## 7. 리스크 & 완화

| 리스크                                  | 발동 조건                       | 완화                                                                            |
| --------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| Fee/funding 구현 복잡도 ↑ → 시간 초과   | Phase 2 Step 6/7 합계 8h 초과   | Fee만 PR-C로 완성, funding은 별도 PR-C2로 분리                                  |
| Monte Carlo snapshot 테스트 결정성 이슈 | numpy 버전 차이로 float 불일치  | `np.random.default_rng(seed=42)` 고정 + `np.testing.assert_allclose(rtol=1e-6)` |
| PR 간 merge conflict                    | Phase 동시 진행 시              | Phase 순서대로 main 머지 후 다음 브랜치 분기 (직렬 실행)                        |
| Context fatigue (15h+)                  | Sprint 9 선행 단계에서 집중력 ↓ | Phase 2 완료(12h) 또는 Phase 3 중 (18h)에서 자연 중단 옵션                      |
| Pre-commit hook `ruff` PATH 실패        | backend venv activate 안 됨     | `export PATH="$(pwd)/backend/.venv/bin:$PATH"` 후 commit                        |

---

## 8. 메모리 규칙 리마인더 (반드시 준수)

아래 규칙은 이 세션 내내 적용됨:

1. **한국어 사용** (사고/대화/문서 전부)
2. **별점 테이블** — 선택지 2개↑ 제시 시 매번
3. **자동 진행 조건** — 추천도 차이 2★↑ 이고 Git Safety 대상 아니면 승인 요청 없이 진행
4. **Dogfood-first indie SaaS** — "내가 돈 내고 쓰고 싶은 것" quality bar
5. **스프린트 너무 짧게 끊지 말 것** — 가능하면 Phase 단위 묶음
6. **방법론 정의 후 반드시 순서대로 실행** — 플랜 기록 ≠ 실행
7. **Git Safety Protocol** — 커밋/푸쉬/머지는 사용자 승인 (단, "쭉 진행" 승인 시 Phase 단위 일괄 가능)
8. **스테이징 브랜치 전략** — main 직접 touch 금지 (기능 브랜치 → PR)

---

## 📋 세션 시작 프롬프트 (복사용)

**아래 블록 전체를 새 Claude Code 세션의 첫 메시지로 복사·붙여넣기 하세요.**

---

```
QuantBridge H1 Stealth 클로징 후 longrun 세션 시작할게.

## 컨텍스트

2026-04-20~21 이전 세션에서 H1 Stealth 클로징 5-Step 풀패키지 완료.
- PR #37~#40 모두 main merged
- Kill Switch capital_base 동적 바인딩 완료 (PR #38)
- Bybit mainnet 준비 문서/스크립트 완료 (PR #39)
- H2 kickoff plan 완료 (PR #40)

## 결정 변경

실자본 mainnet dogfood → **testnet only 3~4주**로 변경.
이유: 기술 검증은 testnet에서 90%+ 충분. 실자본 부담 제거.
Beta 오픈 전 극소액 mainnet 1주는 별도 검토.

## 이번 세션 목표 (14~20h / 6 PR)

**Phase 1 Dogfood 준비 (4~6h, PR-A + PR-B):**
- roadmap.md H1→H2 gate 수정 (실자본 → testnet 3~4주)
- bybit-mainnet-checklist.md 확장
- h1-testnet-dogfood-guide.md 신규
- dogfood retrospective HTML template
- M1 Credentials.testnet 필드화 PR

**Phase 2 Testnet 신뢰도 보강 (4~6h, PR-C + PR-D):**
- Fee schedule 정확성 (Bybit VIP tier CSV → maker/taker 정확 계산)
- Funding rate fetcher (CCXT 주기 조회 + PnL 반영)
- Dogfood 일일 리포트 자동 생성 (Celery beat + HTML)

**Phase 3 Sprint 9 선행 (4~6h, PR-E + PR-F):**
- Sprint 9 writing-plans (task 9-1~9-6 분해)
- Sprint 9-6 Idempotency-Key 구현
- Sprint 9-1 Monte Carlo 엔진 초안

**Phase 4 마무리 (1~2h):**
- Twitter/X 첫 포스트 초안
- 상태 대시보드 업데이트

## 실행 지침

- **쭉 진행해도 됨** (중간 승인 요청 최소화)
- 커밋/푸쉬/PR 생성 시점에만 승인 필요
- 각 Phase 완료 시 PR URL + 간략 상태 보고
- Context fatigue 느끼면 12h(Phase 2 완료) 또는 15h(PR-D 완료)에서 자연 중단

## 상세 플랜

전체 상세 plan: `docs/next-session-testnet-dogfood-longrun.md` 참조.
이 파일의 §1~§7을 먼저 읽고 Phase 1 Step 1부터 시작해줘.

## 우선 해야 할 것

1. `docs/next-session-testnet-dogfood-longrun.md` 전체 읽기
2. 현재 main 상태 확인 (`git status`, `git log --oneline -5`)
3. Phase 1 Step 1 (roadmap.md 수정) 착수
4. TaskCreate로 4 Phase를 task 4개로 트래킹
5. 진행 중 각 PR 생성 시 URL 보고
```

---

## 9. 실행 팁 (Orchestrator 참고)

### Phase 1 집중 포인트

- roadmap.md gate 수정 시 기존 조건 3개(실자본 1주 + KS/leverage/AES 검증 + Prometheus alert) 중 1번만 변경
- dogfood 가이드는 기존 bybit-mainnet-checklist의 "Testnet Smoke" 섹션을 확장하는 방향
- Credentials.testnet 필드화는 `Credentials` dataclass에 `testnet: bool = True` 추가 + BybitFuturesProvider에서 `testnet` 값 분기

### Phase 2 집중 포인트

- Fee schedule: Bybit USDT Perp maker 0.02% / taker 0.055% 기본 (VIP 0 tier)
- Funding rate: 8시간마다 fetch. `trading.funding_rates` 테이블 신규 or existing 활용
- Dogfood 리포트: 기존 `docs/reports/*.html` 스타일 재사용. Jinja2 template

### Phase 3 집중 포인트

- Idempotency-Key: Sprint 6 Trading의 `idempotency_key` + `idempotency_payload_hash` 패턴 재사용 (trading.orders 테이블 참조)
- Monte Carlo: `numpy.random.default_rng(seed=42)` 결정성 확보. 1000회 bootstrap으로 95% CI 계산. `run_monte_carlo(equity_curve: list[Decimal]) -> MonteCarloResult`

### 중간 휴식 포인트

- Phase 1 완료 (6h): "Phase 1 끝. Phase 2 진행?" 1회 확인
- Phase 2 완료 (12h): "Phase 2 끝. Phase 3 진행 or 세션 종료?" 1회 확인
- Phase 3 완료 (18h): "Phase 3 끝. Phase 4 진행 or 세션 종료?" 1회 확인

---

## 10. 세션 종료 기준

**최소 성공 (Phase 1 완료, 6h):**

- PR-A + PR-B 생성
- roadmap gate 수정 + Credentials.testnet 필드화 완료
- 사용자가 testnet dogfood 시작 가능한 상태

**중간 성공 (Phase 2 완료, 12h):**

- PR-A~D 생성
- Fee/funding 시뮬레이션 + 일일 리포트 완료
- Dogfood 신뢰도 92% 상승

**풀 성공 (Phase 3~4 완료, 18~20h):**

- PR-A~F 전부 생성
- Sprint 9-1, 9-6 선행 완료
- Dogfood 시작 + Sprint 9 나머지 task만 남음

---

## 변경 이력

- **2026-04-21** — 초안 작성. 이전 H1 클로징 5-Step 완료 후 testnet only dogfood 결정에 따른 longrun 플랜.
