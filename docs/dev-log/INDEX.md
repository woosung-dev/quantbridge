# Dev-log Index

> 회고·ADR·dogfood 기록을 **찾기 위한** 색인. 요약은 최근 12회차만 한 줄씩 두고 나머지는 링크만 둔다.
> 이 파일은 매 세션 읽히므로 **줄당 300자 상한**을 `scripts/docs-audit.sh` 가 강제한다 (초과 시 exit 1).
> 압축 전 원문(요약 전문 · H2 Sprint 서사 · Sprint 1-14 매트릭스) = [index-full-2026-08-02.md](../archive/dev-log/index-full-2026-08-02.md).

---

## 최근 12회차

> 13번째가 생기면 **가장 오래된 항목을 아래 「전체 이력」으로 내린다** — 이 섹션은 12개를 넘지 않는다.
> PR 번호는 머지 커밋(`git log`)으로 검증했다 — dev-log 본문은 머지 **전**에 쓰이므로 PR 번호를 담지 않는다.

- **2026-08-02 context-budget-repair** — 문서를 읽는 비용. `INDEX.md` **−89.9%**(151,256→15,334 tok) · 자동 로드 고정비 **−42.2%** · 줄길이 상한 게이트 신설. ★**착수 전제 3건 반증** — `CONTEXT.md`·`.ai/rules` 는 자동 로드가 **아니다** [dev-log](2026-08-02-context-budget-repair.md)
- **2026-08-02 canonical-measurement-surface** — 손 SQL 을 쓸 이유를 없앤 정본 술어 측정 표면 3종. **BL-576 프로덕션 발화 검증 통과**, **BL-577 전제 반증**(가드는 실재했다 — 내용 grep 은 파일명에만 있는 문자열을 못 잡는다), 신규 BL-579. PR #520 — [dev-log](2026-08-02-canonical-measurement-surface.md)
- **2026-08-02 divergence-label-split** — 로그 이벤트 하나가 덮던 발화 8곳을 사건별 6 이름으로 갈라 **BL-576 Resolved**. 판정식 정본을 §G1.1 로 이관 — 살아남은 유일한 완전 판정 표가 OR 버전이었다(삭제에 의한 역선택). PR #519 — [dev-log](2026-08-02-divergence-label-split.md)
- **2026-08-01 entry-completeness-rejudgement** — **4개 채널 중 3개가 유실 채널이 아니었다** ⇒ 「축소」. 층위1 확정 거절률 16.67% → 2.44%. **BL-536 Resolved · BL-522 P1→P2**, 신규 BL-578. PR #518 — [dev-log](2026-08-01-entry-completeness-rejudgement.md)
- **2026-08-01 silent-surface-honesty** — 조용히 실패하는 표면 4건(BL-570/542/571/572). 뿌리는 **RHF 가 defaultValue 를 그대로 setValueAs 에 넘겨 `Number(null) === 0`** — 이 전략은 설정을 저장할 방법이 없었다. 신규 BL-577. PR #517 — [dev-log](2026-08-01-silent-surface-honesty.md)
- **2026-08-01 conditional-fill-visibility** — 기다리는 대신 발화 조건을 만들어 write-back 을 **프로덕션 검증**(거래소 terminal→원장 60초, 사고 때 818초). **BL-566 재판정** 41.6→12.9/h. 신규 BL-567~571. PR #516 — [dev-log](2026-08-01-conditional-fill-visibility.md)
- **2026-07-31 reversal-ledger-sync** — **실주행이 코드 대조 뿌리 가설을 반증** — 엔진이 체결을 13분 38초 몰랐다(리컨사일러가 `filled` 을 7번 확인하고도 미기록). BL-560 수정은 최종 창에서 0회 발화 = 프로덕션 미검증. 신규 BL-565/566. PR #515 — [dev-log](2026-07-31-reversal-ledger-sync.md)
- **2026-07-30 close-mismatch-soak** — **BL-560 실재 확정** — 2.60건/h · 청산 시도의 46.2%. 6/6 전건이 「직전 체결과 같은 방향」 ⇒ 엔진이 자기 반전 체결의 청산 leg 미반영. BL-523 전제 반증 · `bl-audit.sh` 신설. PR #513 — [dev-log](2026-07-30-close-mismatch-soak.md)
- **2026-07-30 close-mismatch-visibility** — **재던 곳에 없었다** — C2 는 유실 채널이 아니라 청산 tick 수. `110017` 두 갈래(same side 9 / position is zero 30)가 한 라벨에 묻혀 화면이 9건 전부를 초록으로 냈다. soak 미실시. PR #511 — [dev-log](2026-07-30-close-mismatch-visibility.md)
- **2026-07-30 live-entry-completeness** — **BL-536 재측정 「축소」** — 유실은 줄어든 게 아니라 원장 밖 한 채널로 수렴(75%). 직전 헤드라인 16.67% 는 에피소드 유실률이 아니라 시도 거절률이었다. PR #509 · #510 — [dev-log](2026-07-30-live-entry-completeness.md)
- **2026-07-30 conditional-entry-alignment** — 착수 preflight 가 전제 2건을 반증. **BL-544**(원장 체결로 엔진 seed) · **BL-484**(세션 종료 사유 영속) 착지. soak 3/3 생존이나 seed 주입 경로는 한 번도 안 밟혔다 → BL-553. PR #506 — [dev-log](2026-07-30-conditional-entry-alignment.md)
- **2026-07-30 engine-exchange-alignment** — **BL-543**(position epoch) 착지 + BL-535 부분. **실주행 soak 이 단위테스트를 반증** — 재생 아티팩트는 사라졌으나 공백 뒤 세션이 정반대 방향으로 사망 ⇒ **BL-544** 신설. PR #503 — [dev-log](2026-07-30-engine-exchange-alignment.md)

---

## 전체 이력

> 요약 문장을 두지 않는다 — 상세는 링크 대상에 있다. 자기 dev-log 가 없는 회차는 원문 아카이브로 보낸다.

| 날짜        | 이름                                         | 기록                                                                                                                                            |
| ----------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-07-29  | live-orphan-close                            | [dev-log](2026-07-29-live-orphan-close.md)                                                                                                      |
| 2026-08-01  | entry-completeness-rejudgement 사전등록 감사 | [log](2026-08-01-entry-completeness-rejudgement-prereg-audit.md)                                                                                |
| 2026-07-28  | live-close-completeness                      | [log](2026-07-28-live-close-completeness.md)                                                                                                    |
| 2026-07-28  | live-outcome-parity                          | [log](2026-07-28-live-outcome-parity.md)                                                                                                        |
| 2026-07-28  | live-entry-parity                            | [log](2026-07-28-live-entry-parity.md)                                                                                                          |
| 2026-07-28  | live-ops-hygiene                             | [log](2026-07-28-live-ops-hygiene.md)                                                                                                           |
| 2026-07-28  | live-observability                           | [archive](../archive/dev-log/index-full-2026-08-02.md) · [판정표](../archive/operations/observability/2026-07-28-live-safety-device-verdict.md) |
| 2026-07-27  | live-conditional-hardening                   | [log](2026-07-27-live-conditional-hardening.md)                                                                                                 |
| 2026-07-27  | live-conditional-entry                       | [log](2026-07-27-live-conditional-entry.md)                                                                                                     |
| 2026-07-26  | live-engine-parity                           | [log](2026-07-26-live-engine-parity.md)                                                                                                         |
| 2026-07-26  | live-entry-wiring                            | [log](2026-07-26-live-entry-wiring.md)                                                                                                          |
| 2026-07-26  | BL-474 webhook ingress 패리티                | [log](2026-07-26-bl474-webhook-ingress-parity.md)                                                                                               |
| 2026-07-26  | dogfood-restore                              | [log](2026-07-26-dogfood-restore.md)                                                                                                            |
| 2026-07-26  | money-path-finish                            | [log](2026-07-26-money-path-finish.md)                                                                                                          |
| 2026-07-26  | backtest-trust                               | [log](2026-07-26-backtest-trust.md)                                                                                                             |
| 2026-07-25  | exit-money-path                              | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-25  | exit-attribution                             | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-25  | money-path-accuracy                          | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-25  | close-completeness                           | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-24  | trading-surface-pack                         | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-24  | position-cockpit                             | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-24  | perf-surface                                 | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-24  | opspack-ws2                                  | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-24  | tier-c                                       | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-07-23  | functional-parity                            | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-06-30  | stress_test 1차 deepen                       | [log](2026-06-30-stress_test-deepen.md)                                                                                                         |
| 2026-06-30  | backtest 1차 deepen (ADR-021)                | [log](2026-06-30-backtest-deepen.md)                                                                                                            |
| 2026-06-26  | trading 2차 deepen                           | [log](2026-06-26-trading-deepen-2.md)                                                                                                           |
| 2026-06-26  | 트레일링 라이브 등재                         | [log](2026-06-26-trailing-live-placement.md)                                                                                                    |
| 2026-05-16  | Sprint 60 plan                               | [log](sprint-60-plan.md)                                                                                                                        |
| 2026-05-15  | CLAUDE.md align audit                        | [log](2026-05-15-claudemd-align-audit.md)                                                                                                       |
| 2026-05-15  | Track B trading deepen (audit-only)          | [log](2026-05-15-trading-deepen.md)                                                                                                             |
| 2026-05-14  | Sprint 60 close-out                          | [log](2026-05-14-sprint60-close.md)                                                                                                             |
| 2026-05-13  | Sprint 59 close-out                          | [log](2026-05-13-sprint59-close.md)                                                                                                             |
| 2026-05-12  | Sprint 54 회고                               | [log](2026-05-12-sprint54-close.md)                                                                                                             |
| 2026-05-12  | Sprint 54 Bayesian/Genetic 문법 ADR          | [log](2026-05-12-sprint54-bayesian-genetic-grammar-adr.md)                                                                                      |
| 2026-05-12  | Sprint 58 post — alertcondition() 신호 탐지  | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-05-12  | Sprint 58 post — Pine 호환성 실험            | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |
| 2026-05-11  | Sprint 58 close-out                          | [log](2026-05-11-sprint58-close.md)                                                                                                             |
| 2026-05-11  | Sprint 57 close-out                          | [log](2026-05-11-sprint57-close.md)                                                                                                             |
| 2026-05-11  | Sprint 56 close-out                          | [log](2026-05-11-sprint56-close.md)                                                                                                             |
| 2026-05-11  | Sprint 56 chore prereq CI/CD                 | [log](2026-05-11-sprint56-chore-prereq-cicd.md)                                                                                                 |
| 2026-05-11  | Sprint 55 close-out                          | [log](2026-05-11-sprint55-close.md)                                                                                                             |
| 2026-05-11  | Sprint 55 master                             | [log](2026-05-11-sprint55-master.md)                                                                                                            |
| 2026-05-11  | Sprint 53 회고                               | [log](2026-05-11-sprint53-close.md)                                                                                                             |
| 2026-05-11  | Sprint 52 회고                               | [log](2026-05-11-sprint52-close.md)                                                                                                             |
| 2026-05-11  | Sprint 51 회고                               | [log](2026-05-11-sprint51-close.md)                                                                                                             |
| 2026-05-10  | Sprint 50 회고                               | [log](2026-05-10-sprint50-close.md)                                                                                                             |
| 2026-05-10  | Sprint 49 회고                               | [log](2026-05-10-sprint49-close.md)                                                                                                             |
| 2026-05-09  | Sprint 48 close-out                          | [log](2026-05-09-sprint48-close.md)                                                                                                             |
| 2026-05-09  | Sprint 48 BL-201 audit                       | [log](2026-05-09-sprint48-bl201-audit.md)                                                                                                       |
| 2026-05-09  | Sprint 47 close-out                          | [log](2026-05-09-sprint47-close.md)                                                                                                             |
| 2026-05-09  | Sprint 46 close-out                          | [log](2026-05-09-sprint46-close.md)                                                                                                             |
| 2026-05-09  | Sprint 45 회고                               | [log](2026-05-09-sprint45-close.md)                                                                                                             |
| 2026-05-09  | deepen pilot — pine_v2                       | [log](2026-05-09-pine_v2-deepen-pilot.md)                                                                                                       |
| 2026-05-09  | deepen pilot — trading                       | [log](2026-05-09-trading-deepen.md)                                                                                                             |
| 2026-05-09  | deepen pilot — frontend                      | [log](2026-05-09-frontend-deepen.md)                                                                                                            |
| 2026-05-08  | Sprint 44 close-out                          | [log](2026-05-08-sprint44-close.md)                                                                                                             |
| 2026-05-08  | Sprint 42 master                             | [log](2026-05-08-sprint42-master.md)                                                                                                            |
| 2026-05-08  | Sprint 42 Day 7 midcheck                     | [log](2026-05-08-sprint42-day7-midcheck.md)                                                                                                     |
| 2026-05-07  | Sprint 41 회고                               | [log](2026-05-07-sprint41-master.md)                                                                                                            |
| 2026-05-07  | Sprint 39 회고                               | [log](2026-05-07-sprint39-master.md)                                                                                                            |
| 2026-05-07  | Sprint 38 회고                               | [log](2026-05-07-sprint38-master.md)                                                                                                            |
| 2026-05-06  | Sprint 37 회고                               | [log](2026-05-06-sprint37-master.md)                                                                                                            |
| 2026-05-06  | dogfood Day 7 (Sprint 36)                    | [log](2026-05-06-dogfood-day7-sprint36.md)                                                                                                      |
| 2026-05-05  | Sprint 35 회고                               | [log](2026-05-05-sprint35-master-retrospective.md)                                                                                              |
| 2026-05-05  | office-hours Sprint 35 분기 결정             | [log](2026-05-05-office-hours-sprint-35-decision.md)                                                                                            |
| 2026-05-05  | Sprint 34 회고                               | [log](2026-05-05-sprint34-master-retrospective.md)                                                                                              |
| 2026-05-05  | dogfood Day 6.5                              | [log](2026-05-05-dogfood-day-6.5.md)                                                                                                            |
| 2026-05-05  | dogfood Day 6                                | [log](2026-05-05-dogfood-day6.md)                                                                                                               |
| 2026-05-05  | BL-178 root cause spike                      | [log](2026-05-05-bl178-rootcause-spike.md)                                                                                                      |
| 2026-05-05  | Sprint 33 회고                               | [log](2026-05-05-sprint33-master-retrospective.md)                                                                                              |
| 2026-05-05  | Sprint 32 회고                               | [log](2026-05-05-sprint32-master-retrospective.md)                                                                                              |
| 2026-05-05  | Sprint 31 Day 4 dogfood handoff              | [log](2026-05-05-sprint31-day4-handoff.md)                                                                                                      |
| 2026-05-05  | Sprint 31 Pine v6 호환 ADR                   | [log](2026-05-05-sprint31-pine-v6-compat-adr.md)                                                                                                |
| 2026-05-05  | Sprint 30 회고                               | [log](2026-05-05-sprint30-master-retrospective.md)                                                                                              |
| 2026-05-05  | ADR-019 Surface Trust Pillar                 | [log](2026-05-05-sprint30-surface-trust-pillar-adr.md)                                                                                          |
| 2026-05-05  | Sprint 30 chart lib 결정 ADR                 | [log](2026-05-05-sprint30-chart-lib-decision.md)                                                                                                |
| 2026-05-04  | Sprint 29 회고                               | [log](2026-05-04-sprint29-coverage-hardening.md)                                                                                                |
| 2026-05-04  | Sprint 29 baseline snapshot                  | [log](2026-05-04-sprint29-baseline-snapshot.md)                                                                                                 |
| 2026-05-04  | Sprint 29 v1→v2 pivot                        | [log](2026-05-04-sprint29-v1-to-v2-pivot.md)                                                                                                    |
| 2026-05-04  | Sprint 28 회고                               | [log](2026-05-04-sprint28-retrospective.md)                                                                                                     |
| 2026-05-04  | Sprint 28 kickoff plan                       | [log](2026-05-04-sprint28-kickoff.md)                                                                                                           |
| 2026-05-04  | Sprint 27 Beta prereq hotfix                 | [log](2026-05-04-sprint27-beta-prereq-hotfix.md)                                                                                                |
| 2026-05-04  | Sprint 26 Pine Signal Auto-Trading           | [log](2026-05-04-sprint26-pine-signal-auto-trading.md)                                                                                          |
| 2026-05-04  | dogfood Day 1 — Sprint 27 launch             | [log](2026-05-04-dogfood-day1-sprint27-launch.md)                                                                                               |
| 2026-05-03  | Sprint 25 Hybrid                             | [log](2026-05-03-sprint25-hybrid.md)                                                                                                            |
| 2026-05-03  | Sprint 24b Backend E2E 자동 dogfood          | [log](2026-05-03-sprint24b-auto-dogfood.md)                                                                                                     |
| 2026-05-03  | Sprint 24a WebSocket 안정화                  | [log](2026-05-03-sprint24a-ws-stability.md)                                                                                                     |
| 2026-05-03  | Sprint 23 C-3 묶음                           | [log](2026-05-03-sprint23-c3-bundle.md)                                                                                                         |
| 2026-05-03  | Sprint 22 BL-091 architectural               | [log](2026-05-03-sprint22-bl091-architectural.md)                                                                                               |
| 2026-05-03  | Sprint 21 dogfood Day 1                      | [log](2026-05-03-dogfood-day1-sprint21.md)                                                                                                      |
| 2026-05-02  | Sprint 21 BL-096 coverage expansion          | [log](2026-05-02-sprint21-bl096-coverage-expansion.md)                                                                                          |
| 2026-05-02  | Sprint 20 dogfood Day 0 준비                 | [log](2026-05-02-sprint20-dogfood-day0-setup.md)                                                                                                |
| 2026-05-02  | Sprint 19 technical debt                     | [log](2026-05-02-sprint19-technical-debt.md)                                                                                                    |
| 2026-05-02  | Sprint 18 BL-080 architectural               | [log](2026-05-02-sprint18-bl080-architectural.md)                                                                                               |
| 2026-05-02  | Sprint 17 prefork fix                        | [log](2026-05-02-sprint17-prefork-fix.md)                                                                                                       |
| 2026-05-01  | Sprint 16 live 검증 + backfill               | [log](2026-05-01-sprint16-phase0-live-and-backfill.md)                                                                                          |
| 2026-05-01  | Sprint 15 stuck order watchdog               | [log](2026-05-01-sprint15-watchdog.md)                                                                                                          |
| 2026-04-27  | dogfood Day 3 (Sprint 14)                    | [log](2026-04-27-dogfood-day3.md)                                                                                                               |
| 2026-04-26  | dogfood Day 2 (Sprint 13)                    | [log](2026-04-26-dogfood-day2.md)                                                                                                               |
| 2026-04-25  | dogfood Day 1 (Sprint 12)                    | [log](2026-04-25-dogfood-day1.md)                                                                                                               |
| 2026-04-24~ | dogfood Week 1 — Path β                      | [log](dogfood-week1-path-beta.md)                                                                                                               |
| ~2026-04-23 | Sprint 1-14 회고 위치 매트릭스               | [archive](../archive/dev-log/index-full-2026-08-02.md)                                                                                          |

---

## ADR + 사후 회고 (번호순, 신뢰도 높은 결정 기록)

- 021 — backtest 제출 멱등성 Redis + PG advisory dual-lock 유지 (단일 unit 통합 거부, 2026-06-30 backtest-deepen C3 KILL) — [`021-backtest-idempotency-dual-lock.md`](../decisions/021-backtest-idempotency-dual-lock.md)
- 020 — Trust Layer CI — 3-Layer Parity (P-1/2/3) 설계 (구 ADR-013, 2026-05-29 renumber — Optimizer ADR-013 과 ID 충돌 해소) — [`020-trust-layer-ci-design.md`](../decisions/020-trust-layer-ci-design.md)
- 018 — Sprint 12 WebSocket Supervisor + Sprint 15-A/B Architecture Cleanup — [`018-sprint12-ws-supervisor-and-exchange-stub-removal.md`](../decisions/018-sprint12-ws-supervisor-and-exchange-stub-removal.md)
- 017 — FE Polish Bundle 1/2 묶음 회고 (FE-01~04 + FE-A~F) — [`017-fe-polish-bundle-1-2-retro.md`](../decisions/017-fe-polish-bundle-1-2-retro.md)
- 016 — Sprint Y1 Pre-flight Pine Coverage Analyzer (Trust Layer 사용자 축) — [`016-sprint-y1-coverage-analyzer.md`](../decisions/016-sprint-y1-coverage-analyzer.md)
- 015 — Sprint 7d 회고 (OKX Adapter + Trading Sessions + Passphrase 암호화) — [`015-sprint-7d-okx-sessions.md`](../decisions/015-sprint-7d-okx-sessions.md)
- 014 — Sprint 8b + 8c 합본 회고 (pine_v2 Tier-1 래퍼 + 3-Track Dispatcher) — [`014-sprint-8b-8c-pine-v2-expansion.md`](../decisions/014-sprint-8b-8c-pine-v2-expansion.md)
- ~~013~~ — Trust Layer CI → **ADR-020 으로 renumber** (2026-05-29, Optimizer ADR-013 과 충돌 해소). 위 020 항목 참조
- 012 — Sprint 8a Tier-0 Final Report (Week 1-3 완주, v3.0) — [`012-sprint-8a-tier0-final-report.md`](../decisions/012-sprint-8a-tier0-final-report.md)
- 011 — Pine Script 실행 전략 v4 (Alert Hook Parser + 3-Track Architecture) — [`011-pine-execution-strategy-v4.md`](../decisions/011-pine-execution-strategy-v4.md)
- 010b — Product Roadmap 프레임 & 입력 결정 (재작성본, canonical) — [`010b-product-roadmap.md`](../decisions/010b-product-roadmap.md)
- 010a — Dev CPU Budget Policy + Next.js Anti-Pattern 15건 — [`010a-dev-cpu-budget.md`](../decisions/010a-dev-cpu-budget.md)
- ~~010~~ — Product Roadmap 1차 초안 (DEPRECATED, 2026-05-15 cleanup git rm — git history 보존, 010b 가 canonical)
- 009 — shadcn/ui v4 Nova Preset 규칙 예외 (form.tsx radix-ui + ui/ 직접 수정) — [`009-shadcn-v4-form-radix-exception.md`](../decisions/009-shadcn-v4-form-radix-exception.md)
- 008 — Sprint 7c FE 따라잡기 — 스코프 결정 기록 — [`008-sprint7c-scope-decision.md`](../decisions/008-sprint7c-scope-decision.md)
- 007 — Sprint 7a Bybit Futures + Cross Margin — 사전 결정 기록 — [`007-sprint7a-futures-decisions.md`](../decisions/007-sprint7a-futures-decisions.md)
- 006 — Sprint 6 Trading 데모 설계 리뷰 결과 + 3 핵심 의사결정 — [`006-sprint6-design-review-summary.md`](../decisions/006-sprint6-design-review-summary.md)
- 005 — DateTime tz-aware + AwareDateTime TypeDecorator 도입 — [`005-datetime-tz-aware.md`](../decisions/005-datetime-tz-aware.md)
- 004 — Pine 파서 접근법 선택 근거 — [`004-pine-parser-approach-selection.md`](../decisions/004-pine-parser-approach-selection.md)
- 003 — Pine 런타임 안전성 + 파서 범위 결정 — [`003-pine-runtime-safety-and-parser-scope.md`](../decisions/003-pine-runtime-safety-and-parser-scope.md)
- 002 — 병렬 스캐폴딩 전략 — [`002-parallel-scaffold-strategy.md`](../decisions/002-parallel-scaffold-strategy.md)
- 001 — 기술 스택 결정 — [`001-tech-stack.md`](../decisions/001-tech-stack.md)

---

## 운영 규칙

- 신규 dev-log 작성 시 본 INDEX 에도 한 줄 추가 (시간 역순 또는 번호순 위치 유지)
- ★**요약 줄 상한 300자.** 초과하면 `scripts/docs-audit.sh` 가 exit 1 로 막는다 — grep 한 줄이 곧 대량 읽기다
- ★**요약은 「최근 12회차」에만 둔다.** 13번째가 생기면 가장 오래된 항목을 「전체 이력」(날짜·이름·링크만)으로 내린다
- AGENTS.md 의 "현재 작업" 섹션은 **활성 sprint 1개 + 직전 완료 sprint 1개 + 다음 분기** 만 inline. 그 외 모든 회고는 본 INDEX 에서 발견
- BL ID 가 부여된 follow-up 은 [`docs/backlog.md`](../backlog.md) 에서 추적
- Sprint 1-14 의 별도 dev-log 가 없는 항목은 [원문 아카이브의 "Sprint 1-14 매트릭스"](../archive/dev-log/index-full-2026-08-02.md) 에서 ADR/spec/plan/dogfood 위치 cross-link

---

★압축 전 요약 원문 = [../archive/dev-log/index-full-2026-08-02.md](../archive/dev-log/index-full-2026-08-02.md)
