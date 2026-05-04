# QuantBridge — Product Roadmap

> **SSOT (2026-05-04 cleanup):** 본 문서가 **Horizon × Pillar 로드맵의 단일 진실 원천**. 관련 ADR: [`../dev-log/010b-product-roadmap.md`](../dev-log/010b-product-roadmap.md) (재작성본, 활성). 1차 초안: [`../dev-log/010-product-roadmap.md`](../dev-log/010-product-roadmap.md) (DEPRECATED).
> **PRD ↔ 본 로드맵 ↔ Phase 매핑 (Phase B 작업):** Phase 정의 = `00_project/phase-vs-sprint-mapping.md` (신규 예정), 도메인 진행도 = `01_requirements/domain-progress-matrix.md` (신규 예정).
>
> **작성일:** 2026-04-17 (초안) · **최종 수정:** 2026-04-21 (testnet dogfood 결정 반영)
> **프레임:** Horizon 3 × Strategy Pillars 하이브리드
> **철학:** Dogfood-first Indie SaaS — "내가 돈 내고 쓰고 싶은 것"이 quality bar
> **현재 단계:** **H1 클로징** — 코드 게이트 전부 merge. **남은 건 Testnet dogfood 3~4주 (+ 선택: 극소액 mainnet 72h)** → H2 진입
> **H2 Kickoff plan:** [`../superpowers/plans/2026-04-20-h2-kickoff.md`](../superpowers/plans/2026-04-20-h2-kickoff.md) — 6 결정 포인트 + Sprint 9~11 분해 + Beta 5~10명 획득 경로

---

## 한 페이지 요약

- **지금 (H1, 0–1.5m):** Sprint 7c(FE) → 7b(OKX) → 8a(DB CHECK) → 8b(capital_base) → **Testnet dogfood 3~4주** (기술 검증 90%+ 충분, 실자본 부담 제거). 선택: Beta 오픈 직전 극소액 mainnet 72h 별도 검토. 외부 공개 없음.
- **다음 (H2, 1.5–4m):** Monte Carlo + Walk-Forward + 관측성 + 파라미터 최적화 + 지인 Beta 5~10명 + US·EU geo-block. Freemium 티어 가설 수립.
- **나중 (H3, 4–9m):** TV 커뮤니티 공개 + 가격 실험 A/B + 첫 $1 유료 사용자.
- **Build in public**: H1부터 Twitter/X 주 1회.
- **Pillar 우선순위**: 🛡 Trust ≥ 🚀 Scale > 💰 Monetize.

---

## 개요

### 왜 이 로드맵이 필요한가

`vision.md`의 Phase 1~4와 `TODO.md` Sprint 추적은 **기술 관점**이다. 본 문서는 거기에 **비즈니스·사용자·수익화 축**을 더해서, "언제 외부에 공개할 것인가", "어떤 기능을 어느 시점에 수익화 후보로 볼 것인가", "규제·법무 리스크를 어떻게 프레이밍할 것인가"를 통합한 **제품 로드맵**이다.

### 핵심 전제

1. **Indie SaaS, dogfood-first** — 메이커 본인이 돈을 내고 쓰고 싶은 품질이 1차 quality bar. 외부 유료 사용자는 품질의 자연 결과.
2. **Primary persona: 파트타임 크립토 트레이더 (Python 가능)** — TV 유료, 자본 $1K~$50K, Pine 작성 가능. `b(퀀트 입문자)`는 H2~H3 고급 분석, `c(자동매매 사용자)`는 H2 멀티 거래소로 자연 흡수.
3. **공격적 페이스** — H1 1.5m / H2 2.5m / H3 5m. 현재 Sprint 속도(1~7a를 2일) 유지 전제. 번아웃·스코프 크립 리스크 모니터링 필수.
4. **규제 프레이밍** — "QuantBridge는 software tool, 자금 custody·fiat·투자 자문 없음". BYOK(Bring Your Own Key) + AES-256 MultiFernet 아키텍처 기반.

---

## Pillar 정의

| Pillar                   | 의미                                                                                   | 우선순위                        |
| ------------------------ | -------------------------------------------------------------------------------------- | ------------------------------- |
| 🛡 **Trust (신뢰)**      | 본인이 실자본 맡겨도 안심되는 품질. 실거래 안정성, 리스크 관리, 백테스트 신뢰성, 보안. | **최우선** — H1에 집중          |
| 🚀 **Scale (확장)**      | 기능·거래소·사용자 확장. Trust 충족 후에만 가속.                                       | 중간                            |
| 💰 **Monetize (수익화)** | 수익화 모델 검증. 가격 실험, 티어 경계, 법무/세무.                                     | **H1 금지** → H2 가설 → H3 실험 |

**원칙:** Trust가 깨지면 Scale/Monetize 정지. 예) mainnet 버그 발견 → H2 Monte Carlo 연기하고 fix 먼저.

---

## Horizon × Pillars 매트릭스

### H1 (0–1.5m) · Stealth, 본인 dogfood

| Pillar      | 작업                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🛡 Trust    | **Sprint 7c** Strategy CRUD UI (plan: [`docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md`](../superpowers/plans/2026-04-17-sprint7c-strategy-ui.md))<br>**Sprint 7b** OKX 통합 + Trading Sessions<br>**Sprint 8a** Binance mainnet DB CHECK constraint + `margin_mode` string↔Literal 경계 검증 ([ADR-007](../dev-log/007-sprint7a-futures-decisions.md) 미해결)<br>**Sprint 8b** Kill Switch `capital_base` 레버리지 반영 검증 (ADR-006 미해결)<br>**Testnet dogfood 3~4주** — Bybit Futures testnet. 기술 검증 90%+ 충분. 선택: Beta 오픈 전 극소액 mainnet 72h |
| 🚀 Scale    | CCXT 계측 초기 (Prometheus 최소)<br>초기 backfill Celery task 분리 (대용량 OHLCV)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 💰 Monetize | ❌ **설계 금지.** 신규 기능에 `[free/paid 후보]` 태그만 부착하여 H2 가설 수립 재료로 축적.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Launch      | Stealth. Twitter/X `#buildinpublic` 주 1회 포스트 시작 (한국어+영어 병기).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

### H2 (1.5–4m) · 지인 Beta 5~10명

| Pillar      | 작업                                                                                                                                                                                                                                                                        |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🛡 Trust    | **Sprint 9** Monte Carlo 1000회 + Walk-Forward 분석<br>관측성 스택 — Prometheus + Grafana + alert 1개 이상 실전 동작<br>Multi-worker split-brain Redis lock (현재 PG advisory만)<br>Real broker 테스트 인프라 (pytest-celery)<br>**Disclaimer + ToS 작성** (법무 자문 권장) |
| 🚀 Scale    | **Sprint 10** 파라미터 최적화 (Grid → Bayesian → Genetic)<br>TimescaleDB compression / retention policy<br>**지인 Beta 5~10명 온보딩**<br>**US·EU geo-block** 구현 (결제 gateway + landing 문구 이중 차단)                                                                  |
| 💰 Monetize | **가설 수립 (실행 아님)**<br>Freemium 티어 경계 — 기본=단일 거래소, Paid=다중 거래소 + 고급 분석(MC/WFA/Bayesian)<br>Gumroad / LemonSqueezy 셋업 검토<br>**한국 세무·사업자 등록 확인** (개인사업자 / 통신판매업 / 부가세)                                                  |
| Launch      | H2 말 지인 Beta 오픈. waitlist 수집 시작. Build in public 주 1회 유지.                                                                                                                                                                                                      |

### H3 (4–9m) · TV 커뮤니티 공개

| Pillar      | 작업                                                                                                                                                                       |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🛡 Trust    | Binance + OKX + Bybit 풀 라이브 안정화<br>(실험 태그) AI 전략 생성·최적화 — [ADR-003](../dev-log/003-pine-runtime-safety-and-parser-scope.md) Pine 보안과의 충돌 검증 선행 |
| 🚀 Scale    | **TV 커뮤니티 공식 공개** (r/TradingView, TV Scripts, Discord 서버)<br>(실험 태그) 전략 마켓플레이스 기초 가설 검증                                                        |
| 💰 Monetize | **가격 실험 A/B** ($19 / $29 / 단일)<br>(실험 태그) 거래소 referral fee share<br>**첫 $1 유료 사용자 목표**                                                                |
| Launch      | TV 커뮤니티 공개 포스트. Post-H3 Product Hunt 런치 준비.                                                                                                                   |

---

## 가드레일

- **H1에 Monetize 작업 금지** — 태깅은 허용, 구현·가격 책정·결제 셋업은 H2로 연기.
- **Scope creep 차단** — Sprint 7c에서 잘라낸 항목(전략 versioning / inline backtest / ExchangeAccount UI)은 H2 재평가 전까지 재도입 금지. [ADR-008](../dev-log/008-sprint7c-scope-decision.md) 참조.
- **Trust 우선 인터럽트** — mainnet 실거래 중 버그·데이터 손실·security 이슈 발견 시 현재 Sprint 즉시 중단, 해당 Pillar fix 우선.
- **Dogfood 체크** — H1 종료 시점에 본인이 주 3회 이상 QuantBridge를 쓰지 않았다면 Trust 정의 재검토.

---

## Checkpoint (단계별 전환 조건)

### H1 → H2 전환 조건 (모두 충족)

- [ ] **Testnet dogfood 3~4주 무사고 운영** (선택: 극소액 mainnet 72h 추가 검증)
- [ ] Kill Switch · leverage cap · AES-256 재검증 pass
- [ ] Prometheus alert 1개 이상 실전 동작 (예: 주문 실패율 > 5%)

### H2 → H3 전환 조건 (모두 충족)

- [ ] 지인 Beta 5명 중 3명 이상 1주 연속 사용
- [ ] Monte Carlo / Walk-Forward 본인 사용 1회 이상
- [ ] Freemium 티어 경계 결정 (구현 전)

### H3 성공 정의 (2개 이상 달성)

- [ ] 첫 $1 유료 사용자 확보
- [ ] TV 커뮤니티 공개 포스트 1건 이상
- [ ] MRR 검증 가능한 가설 1개 (증명 불필요, 데이터 수집 가능한 수준)

---

## 리스크 & 대응

| 리스크                                                                                    | 발동 조건                               | 대응                                                                                  |
| ----------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------- |
| **번아웃** (9m 공격적 페이스)                                                             | Sprint 3개 연속 overrun                 | H2/H3 time-box 10% 확장 허용. 주 1일 휴식 규칙.                                       |
| **외부 demand 없음 지속** ([ADR-008](../dev-log/008-sprint7c-scope-decision.md) red flag) | H2 말 Beta 5명 미확보                   | Launch 전략 재검토 — Build in public 비중↑, 타깃 페르소나 재정렬.                     |
| **규제 변화** (한국 특금법 개정 등)                                                       | 2026년 내 금융 당국 발표                | BYOK/tool-framed 프레이밍 재검토. 최악의 경우 글로벌 타깃만 유지 (KR 차단).           |
| **Dogfood 불일치**                                                                        | H1 종료 시점 본인 사용 빈도 주 3회 미만 | NoCode 편집 UX 집중으로 "통합·속도" 가치 재증명. Python-capable 페르소나 가설 재검토. |
| **Trust 회귀**                                                                            | mainnet 실거래 중 데이터 손실·버그      | 현 Sprint 즉시 중단. Post-mortem ADR 작성. 외부 공개 시점 연기.                       |

---

## TODO.md 매핑 (참조용)

`docs/TODO.md`의 Pending 항목이 본 로드맵 6칸 중 어디에 속하는지 명시 (out of roadmap이면 별도 태그):

| TODO 항목                                          | Horizon | Pillar      | 비고                                                               |
| -------------------------------------------------- | ------- | ----------- | ------------------------------------------------------------------ |
| Bybit testnet Live smoke test (실 API key)         | H1      | Trust       | 사용자 수동 확인 대기. PR #39에 smoke script 추가 (2026-04-20)     |
| Trading Sessions 도메인 확장                       | H1      | Trust       | ✅ Sprint 7d 완료 (2026-04-19, PR #28)                             |
| OKX 멀티 거래소                                    | H1      | Trust       | ✅ Sprint 7d 완료 (2026-04-19, PR #28)                             |
| Kill Switch `capital_base` 동적 바인딩             | H1      | Trust       | ✅ 완료 (2026-04-20, PR #38) — notional check + fetch_balance_usdt |
| `margin_mode` DB CHECK constraint                  | H1      | Trust       | Sprint 8a (mainnet 전, 별도 PR)                                    |
| Bybit v5 "not modified" error handling             | H1      | Trust       | Sprint 8a 부속 (mainnet 전)                                        |
| WebSocket 실시간 주문 상태                         | H2      | Scale       | 관측성 스택과 함께                                                 |
| CSO-5 Frontend dev CVEs                            | H2      | Trust       | 보안 유지보수                                                      |
| Rate limiting middleware                           | H2      | Trust       | Beta 전 필수 (Sprint 10)                                           |
| Prometheus/Grafana 계측                            | H1/H2   | Scale/Trust | H1 metric 5종 문서화 ✅ (PR #39). H2 Sprint 9 계측 실행            |
| Idempotency-Key for `POST /backtests`              | H2      | Trust       | Beta 전 권장 (Sprint 9)                                            |
| Real broker 테스트 인프라 (pytest-celery)          | H2      | Trust       | Beta 전 필수 (Sprint 10)                                           |
| 초기 backfill Celery task 분리                     | H1      | Scale       | 대용량 OHLCV 대비                                                  |
| TimescaleDB compression/retention                  | H2      | Scale       | Sprint 10                                                          |
| Multi-worker split-brain Redis lock                | H2      | Trust       | Beta 전 권장 (Sprint 10)                                           |
| FE Strategy delete UX (archive)                    | H1      | Trust       | ✅ Sprint 7c 내 완료                                               |
| conftest 완전 Alembic 전환                         | H2      | Scale       | Beta 전 테스트 안정성                                              |
| DB 호스팅 결정 (TODO Questions Q1)                 | H2      | Scale       | Beta 전 필수                                                       |
| 배포 전략 결정 (TODO Questions Q2)                 | H2      | Scale       | Beta 전 필수                                                       |
| Socket.IO vs WebSocket (TODO Questions Q3)         | H2      | Scale       | 실시간 기능 도입 시                                                |
| Credentials.testnet 필드화 (mainnet 전환)          | H1      | Trust       | dogfood 직전 단발 PR (PR #39 §12.1)                                |
| autonomous-parallel-sprints 스킬 patch (BUG-1/2/3) | H1      | Scale       | LESSON-007/008/009 기반. `~/.claude/skills/` (별도 repo)           |

**Out of roadmap** (의식적 제외):

- Web3 / 온체인 자동매매 — `vision.md` 비범위 유지
- 멀티 사용자 실시간 협업 — `vision.md` 비범위 유지
- 옵션/선물 외 파생상품 — `vision.md` 비범위 유지
- 모바일 네이티브 앱 — 반응형 웹만, `vision.md` 비범위 유지
- 회계/세무 리포트 — 외부 도구 연동 권장

---

## 참조 문서

- **비전 / 타깃 사용자**: [`vision.md`](./vision.md)
- **Sprint 추적**: [`TODO.md`](../TODO.md) — Completed / Next Actions / Blocked / Questions
- **프레임·철학 근거**: [`dev-log/010b-product-roadmap.md`](../dev-log/010b-product-roadmap.md) (ADR)
- **Sprint 7c scope (H1)**: [`dev-log/008-sprint7c-scope-decision.md`](../dev-log/008-sprint7c-scope-decision.md)
- **요구사항 상세**: [`01_requirements/requirements-overview.md`](../01_requirements/requirements-overview.md)
- **배포 플랜**: [`07_infra/deployment-plan.md`](../07_infra/deployment-plan.md)
- **관측성 플랜**: [`07_infra/observability-plan.md`](../07_infra/observability-plan.md)

## 변경 이력

- **2026-04-17** — 초안. Horizon × Pillars 프레임, Indie SaaS dogfood-first 철학 확정. 11개 입력값 결정([ADR-010b](../dev-log/010b-product-roadmap.md) 참조).
- **2026-04-20** — H1 클로징 sync. Sprint 7d/8c/Kill Switch capital_base/mainnet 준비 완료 반영. H2 kickoff plan 링크 추가 (`docs/superpowers/plans/2026-04-20-h2-kickoff.md`). TODO.md 매핑 업데이트.
- **2026-04-21** — Testnet dogfood 결정 반영. H1→H2 gate: "실자본 1주" → "Testnet 3~4주 + 선택 mainnet 72h". 이유: 기술 검증 90%+ testnet 충분, 실자본 부담 제거.
