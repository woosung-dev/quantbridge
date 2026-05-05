# ADR-019 — Surface Trust sub-pillar 도입 (Sprint 30)

**Date:** 2026-05-05
**Status:** Accepted
**Sprint:** 30 (Surface Hardening + Beta 인프라 하이브리드)
**Cross-link:** `docs/00_project/roadmap.md` §Pillar 정의 / Plan `~/.claude/plans/quantbridge-vectorized-snowglobe.md`

---

## Context

Sprint 29 종료 시점 dogfood Day 2 self-assess **6/10** (H1→H2 게이트 ≥7 미달, 1점차). 외부 LLM YC 브리프 v2 분석 후 사실 검증 결과:

- ✅ PRD `backtests.results` JSONB **24 metric spec** 정확
- ✅ PRD `backtests.config` JSONB **5 가정 spec** 정확 (initial_capital / leverage / fees / slippage / include_funding)
- ✅ Phase 1 §주 4 spec 에 **lightweight-charts 명시** 정확
- ❌ Backend 가 PRD spec 24 중 **12개만 구현** (`BacktestMetrics` dataclass)
- ❌ Frontend 가 `config` 5 가정 **0개 노출** (가정 박스 부재)
- ❌ Equity chart 인터랙션 부족 (recharts crosshair만, B&H 비교 / 거래 마커 / 줌 부재)
- ❌ 거래 목록 200 cap + CSV export 미구현

**기존 Trust Pillar 정의 (roadmap.md L43)** = "본인이 실자본 맡겨도 안심되는 품질. 실거래 안정성, 리스크 관리, 백테스트 신뢰성, 보안" — Backend reliability 중심으로 해석되어 **백테스트 결과 surface 의 사용자 의사결정 신뢰성**이 명시 누락. 그 결과 dogfood Day 2 self-assess 가 backend 무결 (Pine Trust Layer ✅ / 1185 BE tests ✅ / 26h+ Auto-Loop ✅) 에도 6/10 stuck.

## Decision

🛡 Trust Pillar 를 **4 sub-pillar 로 분할**:

1. **Backend Reliability** — 실거래 안정성, Pine Trust Layer, WebSocket 무결, prefork-safe Celery, 24h+ Auto-Loop
2. **Risk Management** — Kill Switch, leverage cap, capital_base 동적, 청산 시뮬레이션
3. **Security** — BYOK + AES-256 MultiFernet, Clerk JWT 검증, secrets manager
4. **Surface Trust (신설)** — 사용자가 백테스트 결과를 자기 자본 의사결정에 쓸 수 있는 quality bar (가정 박스 / 차트 인터랙션 / 24 metric depth / 거래 목록 분석 가능성)

## Surface Trust 측정 기준

| 항목                          | 측정                        | 통과 기준                                                              |
| ----------------------------- | --------------------------- | ---------------------------------------------------------------------- |
| `backtests.results` 24 metric | BE 구현 카운트              | 24/24 (현재 12/24 → Sprint 30-γ-BE 후 24/24)                           |
| `backtests.config` 5 가정     | FE 노출 카운트              | 5/5 (현재 0/5 → Sprint 30-α 후 5/5 default + γ-BE 후 graceful upgrade) |
| 차트 lib                      | PRD §Phase 1 주 4 spec 대비 | lightweight-charts 부분 마이그레이션 (Sprint 30-β Option B)            |
| 거래 목록                     | 정렬/필터/CSV               | 5 필드 정렬 + 2 필터 + UTF-8 BOM CSV (Sprint 30-δ)                     |
| dogfood self-assess Day 3     | 본인 평가                   | ≥ 7 (H1→H2 게이트)                                                     |

## Consequences

**긍정:**

- Sprint 30 Surface Hardening 정당화 — Phase 4 polish 안티패턴 ❌, Trust Pillar 직접 deliverable ✅
- H1→H2 게이트 self-assess ≥7 의 의미 명확화 — "본인 dogfood 가 결과 페이지를 보고 자본 의사결정에 쓸 만한가" 직접 측정
- Sprint 31+ Beta open prereq 평가 시 Surface Trust 회귀 차단 의무 (PRD spec drift 방지)
- 외부 LLM 분석 v2 의 본질적 진단 ("결과 페이지 surface depth 부족") 영구 흡수

**부정 / Trade-off:**

- Pillar 정의 단순성 약화 (1 → 4 sub-pillar) — 다음 office-hours 시 표 시인성 회귀 monitoring
- Surface Trust 가 H1 stealth 정책 (build-in-public 절제) 와 충돌 가능성 — 본 ADR 은 H2 Beta open 시 build-in-public 자산화 의도이지 H1 마케팅 강화 아님 명시

## H3 격리 표식 (별도 명시)

본 sprint 가 거절한 항목 — 절대 H1/H2 진입 금지:

- **Strategy DevOps 메시징** (TV Trust Layer → CI/CD for Algo Trading 카테고리 이동) — H3 가격 실험 단계 의제. roadmap.md H3 Trust 행에 격리 표식 추가
- **"백테스트 → 60일 안 Beta open"** 공격적 일정 — 무근거 가설, 거절
- **"$99~$149 가격" 메시징 변경만으로 5배 상승** 클레임 — H3 가격 실험에서 데이터 검증

이 H3 의제들은 **BL-153 (P3, deferred Sprint H3+)** 으로 격리. 본 ADR 부록 cross-link.

## Alternatives considered

| Alternative                                                        | 거절 이유                                                                                                       |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| **A.** Pillar 분할 안 하고 단일 Trust 안에서 surface 작업 진행     | dogfood self-assess 부진의 root cause 가 Pillar 정의에서 invisible. 작업 누적 시 "polish 안티패턴" 평가 위험    |
| **B.** 별도 새 Pillar (예 🎨 Surface) 신설                         | Trust 우선 (Trust ≥ Scale > Monetize) 원칙과 충돌. Surface 가 자기 자본 의사결정 신뢰의 일부이지 별도 가치 아님 |
| **C.** 외부 LLM 브리프의 "Strategy DevOps 카테고리 이동" 통째 수용 | 무근거 가격 클레임 + H3 의제 H1 침범. 본 ADR 은 surface depth 만 격상, 메시징 변경 거절                         |

## Cross-link

- `docs/00_project/roadmap.md` §Pillar 정의 (L43 갱신 후)
- `docs/REFACTORING-BACKLOG.md` BL-150 ~ BL-153 (Sprint 30+ 후속)
- `~/.claude/plans/quantbridge-vectorized-snowglobe.md` §3 Surface Trust Pillar 갱신
- PRD `backtests.results` JSONB 24 필드 spec / §Phase 1 주 4 / §UI 가이드라인
- 외부 LLM YC 브리프 v2 (사실 검증 결과 정확 12 / 부정확·과장 8) — 메인 세션 대화 archive

## Sprint 30 deliverable evidence (인용)

- α (가정 박스): commit `3d88104` — assumptions-card.tsx + BacktestConfigSchema (5 row 표시 + graceful upgrade 패턴)
- β (lightweight-charts): commit `30c9041` — trading-chart.tsx wrapper + equity-chart-v2 + B&H + drawdown area + 거래 마커 + ADR `2026-05-05-sprint30-chart-lib-decision.md`
- γ-BE (24 metric): commit `04f754d` — BacktestMetrics +12 Optional + extract_metrics vectorbt drift 방어 (try/except None fallback) + monthly_returns/drawdown_curve 직렬화 + 18 신규 pytest
- δ (거래 목록): commit `3d88104` (W1 묶음) — 정렬 5 필드 + 필터 2 + UTF-8 BOM CSV export
- ε (Backend prod 인프라 코드): commit `dead5c9` — Cloud Run target Dockerfile + production guard config + healthcheck + Alembic advisory lock + Prometheus alert wire (qb_pending_alerts > 50 critical)

종료 게이트: dogfood Day 3 self-assess ≥7 측정 + dual metric (Sprint 29 표준) + bundle size 회귀 < +200KB.
