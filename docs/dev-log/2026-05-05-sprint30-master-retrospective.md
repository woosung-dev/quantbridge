# Sprint 30 회고 — Surface Hardening + Beta 인프라 하이브리드

**Date:** 2026-05-05
**Status:** Code wrap-up complete · self-assess Day 3 measurement pending
**Theme:** Surface Trust sub-pillar 도입 (ADR-019) + 7 PR Wave 1+2+후처리
**Base → Final:** `8e8e08d` (Sprint 29 #114) → `773424f` (sprint30 mount finalize #122)

---

## 0. Origin

Sprint 29 종료 시점 dogfood Day 2 self-assess **6/10** (H1→H2 게이트 ≥7 미달, 1점차). 외부 LLM YC 브리프 v2 분석 후 사실 검증:

- ✅ PRD spec 인용 정확 (24 metric / 5 config / lightweight-charts 명시)
- ❌ "5/24 노출" 진단 부정확 — 실제 root cause = backend 12개만 구현 + frontend 가정박스 0 + 차트 인터랙션 부족
- ❌ "BL-141 재정의" 무효 (이미 ✅ Resolved Sprint 28)
- 🤷 "60일 Beta open / 5배 가격" 무근거 (H3 격리)

**핵심 진단:** Pine Trust Layer (backend 무결) ≠ Surface Trust (사용자 의사결정 신뢰). Trust Pillar **4 sub-pillar 분할** + Surface Trust 신설 — ADR-019.

---

## 1. Deliverable Evidence

### 1.1 Wave 1 — 4 워커 병렬 (2026-05-05 자율 병렬 실측)

| 워커                                | PR   | Commit    | 내용                                                                                             |
| ----------------------------------- | ---- | --------- | ------------------------------------------------------------------------------------------------ |
| W1 (메인 세션)                      | #119 | `e9424f8` | α 가정 박스 (assumptions-card.tsx) + δ 거래목록 정렬/필터/CSV (utils + trade-table)              |
| W2 (Agent worktree)                 | #120 | `7962b85` | β lightweight-charts wrapper (trading-chart.tsx) + equity-chart-v2 + B&H utility + ADR chart-lib |
| W3 (Agent worktree)                 | #117 | `520bbdb` | γ-BE BacktestMetrics 12→24 + vectorbt extract drift 방어 + serializers backward-compat           |
| W6 (Agent worktree → 메인 세션 fix) | #121 | `21ca3f4` | ε Cloud Run Dockerfile + healthcheck + Alembic advisory lock + Prometheus alert wire             |

### 1.2 Wave 2 — γ-FE + 후처리 (메인 세션)

| 워커               | PR   | Commit    | 내용                                                                               |
| ------------------ | ---- | --------- | ---------------------------------------------------------------------------------- |
| W5 (메인 세션)     | #118 | `d4e5648` | γ-FE 24 metric schema + metrics-detail 17 row + monthly heatmap (graceful degrade) |
| 후처리 (메인 세션) | #122 | `773424f` | EquityChartV2 mount (β v2 활성) + log_level dead config cleanup                    |

### 1.3 ADR & 문서

| PR   | Commit    | 내용                                                                                         |
| ---- | --------- | -------------------------------------------------------------------------------------------- |
| #116 | `2ba8272` | ADR-019 Surface Trust sub-pillar + roadmap.md L43 4 sub-pillar 분할 + H3 행 BL-153 격리 표식 |

---

## 2. Surface Trust 4 측정 기준 (ADR-019)

| 항목                                      | 측정              | 결과                                                                                |
| ----------------------------------------- | ----------------- | ----------------------------------------------------------------------------------- |
| PRD `backtests.results` 24 metric BE+FE   | 카운트            | ✅ 24/24 (Sprint 29 12/24 → Sprint 30 24/24)                                        |
| PRD `backtests.config` 5 가정 FE 노출     | 카운트            | ✅ 5/5 default 표시 (α — graceful degrade. BE config 미응답 시 표준 가정값)         |
| lightweight-charts PRD §Phase 1 주 4 정합 | 부분 마이그레이션 | ✅ Option B (β — neue chart 만, recharts equity-chart 보존). 추후 BL-150 Sprint 31+ |
| dogfood self-assess Day 3 ≥ 7             | 본인 평가         | ⏳ **measurement pending — main 머지 직후 dogfood 1회 실행 후 update**              |

---

## 3. dual metric 종료 게이트 (Sprint 29 표준)

| Metric                  | 통과 기준                         | 결과                                                                                         |
| ----------------------- | --------------------------------- | -------------------------------------------------------------------------------------------- |
| Pine v2 BE 회귀         | 426 passed (regression 0)         | ✅ 426 / 16 skipped (preflight + γ-BE branch + ε branch 모두 정합)                           |
| Backend tests           | 1185+ + 신규 ≥15                  | ✅ **1497 passed** (CI evidence on ε `21ca3f4`) — 신규 18 (γ-BE) + 10 (ε health/config) = 28 |
| Frontend tests          | 243+ + 신규 ≥27                   | ✅ **264 → 304 (+40)** — α 6 + δ 10 + β 12 + γ-FE 12 = 40                                    |
| SSOT 4 invariant        | 4 PASS                            | ✅ preflight 시점 4 / 4                                                                      |
| Bundle size 회귀        | < +200KB                          | ✅ lightweight-charts production.mjs **152KB** (β agent 측정)                                |
| 신규 P0 BL              | = 0                               | ✅ BL-150 (P2) / BL-151 (P3) / BL-153 (P3) — P0 0건                                          |
| 기존 P0 BL 잔여 ≥1 감소 | 진입 BL-003 + BL-005 = 2 → 종료 1 | ⏳ **self-assess Day 3 ≥7 시 BL-005 ✅ Resolved**                                            |
| dogfood self-assess     | ≥ 7                               | ⏳ **measurement pending**                                                                   |

**총평:** 7개 metric 중 5개 ✅ + 2개 self-assess 의존. Codebase 차원 모든 게이트 통과.

---

## 4. 신규 BL (Sprint 31+ 후보)

- **BL-150** (P2) — Equity chart full migration recharts → lightweight-charts (β Option B 점진적 후속, Sprint 31+ deferred). 두 라이브러리 동시 의존 (~430KB) 통합으로 단일 lib + bundle 축소 ~150KB 확보 가능.
- **BL-151** (P3) — `tests/backtest/test_golden_backtest.py` 24 신규 필드 expected 재생성. pine_v2 strategy.exit 지원 시점 trigger.
- **BL-152** ✅ Resolved (Sprint 30-γ-BE `04f754d`) — `total_trades = num_trades` alias 결정. PRD parity 양 키 동시 응답.
- **BL-153** (P3, deferred Sprint H3+) — Strategy DevOps 카테고리 메시징 H3 격리. 외부 LLM 브리프 v2 거절 항목 영구 기록 (가격 5배 클레임 무근거).

### 4.1 본 sprint 발견 + Sprint 31 추적 후보

- **caplog flake root cause** — `kill_switch logger disabled=True` 잔류 (다른 test 영향). ε 의 monkeypatch 우회 fix (`f321825`) 로 working 이지만 진짜 원인 추적 미완. logger config side-effect 인지 conftest 영향인지. **Sprint 31 hardening BL 후보** (P3).
- **log_level dead config** ✅ Resolved (#122 mount finalize). 사용자 LLM 의견 반영해서 cleanup 완료.

---

## 5. 메타-방법론 LESSON

### 5.1 자율 병렬 sprint 패턴 (autonomous-parallel-sprints) 실측

본 sprint 가 **메인 세션 + Agent worktree 3개 + 후처리 + 회고 = 7 PR auto-merge** 패턴으로 진행. Bundle 1·2 (Sprint X1+X3) 보다 큰 scope. 발견 사항:

1. **충돌 회피 의도적 신규 파일 only 패턴** 효과적 — Wave 1 4 워커 (α/β/γ-BE/ε) 가 기존 파일 수정 0 → 충돌 0. EquityChartV2 mount 같은 통합 작업은 메인 세션 후처리.
2. **gh CLI auto-merge --squash --delete-branch** + repo `allow_auto_merge=true` 활성화 (PATCH API) 로 6 PR 자동 머지 가능. 단 stage 브랜치가 worktree 에서 사용 중이면 local delete 실패 (origin 만 deleted, local cleanup 별도).
3. **CI 환경 vs 메인 venv 환경 mismatch** 지속 issue — pre-push hook 이 backend pytest 돌리며 5432/5433 환경 conflict. `--no-verify` 1회 우회 + 사용자 명시 승인 패턴 정착. 근본 fix 는 BL-148 (P3?) 후보.

### 5.2 Agent worktree fix 위임 패턴

ε agent 가 caplog fail 발견 후 fix 요청 받아 monkeypatch 우회 + push. Agent SendMessage 보다 `Agent` tool subagent_type=general-purpose 으로 신규 spawn 한 후 worktree path + branch 명 전달이 자연스러움 (multi-turn agent 활용 가능). **3 차례 Agent ε fix 진행** — 평균 fix duration 3-9분.

### 5.3 외부 LLM 브리프 v2 사실 검증 패턴

**3 Explore agent 병렬** (PRD verification / current FE state / vision/roadmap/BL-141 검증) 으로 600+ 라인 외부 분석 1시간 안에 비판적 검증. 정확 12 / 부정확·과장 8 항목 식별. **사실 클레임 검증 없이 외부 LLM 의견 즉시 반영 금지** 영구 규칙 후보.

---

## 6. Sprint 31 brainstorming hint

### 우선순위 후보

1. **Beta soft-open 인프라** (사용자 §11 Sprint 30 deferred 항목):
   - ζ 도메인 + DNS + Cloudflare (BL-070)
   - ε deploy 단계 — Cloud Run workflow + Secret Manager + min instances (BL-071 잔여 4 sub-task)
   - BL-072 Resend 가입 + DKIM/SPF + 코드 통합

2. **caplog root cause 추적** (Sprint 30 후속) — kill_switch logger disabled=True 잔류 원인 분석. test inter-dependency hardening.

3. **BL-150 Equity chart full migration** (Sprint 30-β Option B 후속) — recharts → lightweight-charts 통합. bundle ~150KB 절감.

4. **dogfood Day 3 self-assess 결과 분기:**
   - ≥7 통과 → BL-005 ✅ → H1→H2 게이트 잔여 = testnet dogfood 누적 + Prometheus alert 실전 발화 → Beta soft-open 진입
   - <7 → Surface Hardening 추가 polish (어떤 surface 가 부족한지 dogfood feedback 기반)

### 권장 (조건부)

- self-assess ≥7 + Beta 인프라 외부 자원 (도메인 등록) 준비 OK → **Sprint 31 = Beta soft-open prereq 정리**
- self-assess <7 → **Sprint 31 = Surface polish + caplog root cause** (H1 stealth 유지)

---

## 7. Cross-link

- ADR-019: [`2026-05-05-sprint30-surface-trust-pillar-adr.md`](2026-05-05-sprint30-surface-trust-pillar-adr.md)
- ADR chart-lib: [`2026-05-05-sprint30-chart-lib-decision.md`](2026-05-05-sprint30-chart-lib-decision.md)
- roadmap.md L43 갱신 (Pillar 4 sub-pillar)
- REFACTORING-BACKLOG.md BL-150 / BL-151 / BL-152 ✅ / BL-153
- Plan: `~/.claude/plans/quantbridge-vectorized-snowglobe.md`
- 외부 LLM YC 브리프 v2 (사실 검증 결과: 정확 12 / 부정확·과장 8) — 메인 세션 대화 archive

---

## 8. dogfood Day 3 self-assess 측정 안내 (사용자 본인 작업)

main `773424f` 머지 후 메인 세션 검증:

1. `make up-isolated` (3100/8100/5433/6380) 또는 `make up`
2. 새 backtest 1건 실행 (예: BTCUSDT 1h, 30일 기간)
3. 결과 페이지 모든 surface 작업 사용:
   - **Overview 탭** — AssumptionsCard 5 row (init/lev/fees/slip/funding) + KPI 5 카드 + EquityChartV2 (B&H 라인 + drawdown area + 거래 마커 + 줌 인터랙션)
   - **성과 지표 탭** — MetricsDetail 17 row (수익성 8 + 위험조정 5 + 거래패턴 5, ★ 마크 = Sprint 30 신규 12)
   - **거래 분석 탭** — Direction breakdown + monthly-returns-heatmap (12×N year grid + 색상 tone + 연 합계)
   - **거래 목록 탭** — TradeTable 5 필드 정렬 + 2 필터 (방향/결과) + CSV export (UTF-8 BOM Excel 호환)
   - **스트레스 테스트 탭** — (Phase C, 본 sprint scope 외)
4. self-assess 점수 기록 (1-10) — 4 surface 작업 모두 사용 후 평가
5. 본 회고 §2 Day 3 row + §3 self-assess row + BL-005 결정 update

**Day 3 측정 후 본 회고 finalize commit 권장.**
