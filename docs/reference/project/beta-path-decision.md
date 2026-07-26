# Beta Open Path Decision Framework

> **목적:** Beta 오픈 시점 + 방식 결정 framework. dogfood Day 7 종료 후 본 문서 기반 결정.
> **SSOT:** Beta path 결정 단일 진실 원천.
> **도입:** Sprint 28 Slice 1b (Phase B.5) — 첫 작성.
> **상위 plan:** [`docs/dev-log/008-sprint7c-scope-decision.md`](../dev-log/008-sprint7c-scope-decision.md) "2026-05-04 Addendum" (Sprint 28 office-hours)

## Path A1 — 자연 시간 1-2주 dogfood + Day 7 dual metric 통과 시 Beta open

### Prereq (모두 충족)

- [x] Sprint 28 Slice 4 (BL-004 KillSwitch capital_base) PR merge
- [ ] Sprint 28 Slice 2 (BL-141 Backtest UI + ts.ohlcv backfill) PR merge
- [ ] Sprint 28 Slice 3 (BL-140b LiveSignal real equity curve BE) PR merge
- [ ] dogfood Day 5-7 자연 사용 (자연 시간 1-2주)
- [ ] dual metric 통과 (self-assess ≥7 + 신규 P0=0 + 기존 P0 잔여 ≥1 감소)

### Duration

- Sprint 28 Slice 2/3/4 완료: 약 1-2주 (15-30h impl)
- dogfood Day 5-7 자연 사용: 약 1-2주
- 총: 2-4주 (Sprint 28 시작 시점부터)

### 예상 BL fix (Beta open 시점)

- BL-141 / BL-140b / BL-004 = Resolved (3건)
- BL-001 / BL-002 / BL-003 = 미해결 (Beta 후 Phase 2 sprint 처리)
- 신규 발견 BL = ≤2 P1 (dual metric gate)

### 리스크

| 리스크                                                 | 가능성 | 완화                                                           |
| ------------------------------------------------------ | ------ | -------------------------------------------------------------- |
| dogfood Day 5-7 critical bug 발견 → dual metric 미통과 | Med    | Path B 로 전환 OR Sprint 29 hotfix sprint                      |
| BL-001/002/003 (existing P0) Beta 중 trigger           | Low    | Beta 5인 = 지인 → 폴리싱 부족 양해 가능. Beta 후 hotfix sprint |
| 외부 5인 의 사용 빈도 부족 (1주 dogfood 적게 함)       | Med    | 인터뷰 의무 (BL-074 Beta 5인 인터뷰)                           |

### 추천도: ★★★★★

사용자 메모리 정합:

- BL-005 (본인 1-2주 dogfood) trigger 도래
- "Sprint 끊지 말 것" — 한 흐름 유지
- "Trust ≥ Scale > Monetize" — Trust 검증 우선
- "Dogfood-first indie SaaS"

## Path B — 극소액 mainnet 72h + 지인 5인 (BL-001/002/003 선처리 후)

### Prereq (모두 충족)

- [ ] Path A1 모든 prereq + 추가:
- [ ] Sprint 29 (BL-001 submitted watchdog)
- [ ] Sprint 30 (BL-002 Day 2 stuck pending)
- [ ] Sprint 31 (BL-003 Bybit mainnet runbook)
- [ ] mainnet 72h 검증 (testnet/mainnet 격차 봉합)

### Duration

- Path A1 종료 후 추가 4-6주
- mainnet 72h: 3일

### 자본 cap

- 사용자 본인 mainnet $100 USDT 한정
- 지인 5인: 각자 자율 결정 ($10-100 권고)

### 리스크

| 리스크                                       | 가능성              | 완화                                  |
| -------------------------------------------- | ------------------- | ------------------------------------- |
| mainnet 72h 자본 손실                        | Low (자본 $100 cap) | KillSwitch 동작 + 자본 cap            |
| Path A1 + Path B 4-6주 추가 → Beta 오픈 지연 | High                | Path A1 단독 진행 (Path B = optional) |

### 추천도: ★★★☆☆ (Path A1 충분 시 불필요)

## 결정 Trigger (dogfood Day 7 종료 시점)

| 시나리오                                                                 | 결정                                          |
| ------------------------------------------------------------------------ | --------------------------------------------- |
| dogfood Day 7 종료 + dual metric 통과 + critical bug 0건                 | **Path A1 진행** (외부 5인 노출)              |
| dogfood Day 7 종료 + critical bug 1건+                                   | **Sprint 29 hotfix sprint → Path A1 재시도**  |
| dogfood Day 7 종료 + dual metric 미통과 (self-assess <7 또는 P0 신규 ≥1) | **Path A1 보류 → 추가 dogfood week + 재평가** |
| 외부 mainnet 검증 의도적 추가 필요 (BL-003 결정 시)                      | **Path B 추가** (Path A1 종료 후)             |

## Trade-off 표

| 차원                     | Path A1                                 | Path B                       |
| ------------------------ | --------------------------------------- | ---------------------------- |
| **Prereq**               | Sprint 28 Slice 2/3/4 + dogfood Day 5-7 | + Sprint 29-31 + mainnet 72h |
| **Duration**             | 2-4주                                   | 6-10주                       |
| **Risk (capital)**       | 0 (testnet)                             | Low ($100 cap)               |
| **Risk (dogfood 단절)**  | Low (자연 시간 사용)                    | Med (4-6주 추가 작업)        |
| **추천도 (사용자 상황)** | ★★★★★ (1순위)                           | ★★★☆☆ (옵션)                 |
| **Beta 오픈 시점**       | 약 2-4주 후                             | 약 6-10주 후                 |

## 결정 후 후속 sprint

### Path A1 결정 시 (Beta open 진입)

- Sprint 29: Beta open 인프라 (BL-070~075) — 도메인 + DNS / Backend production / Resend / 캠페인 / 인터뷰 / H2 게이트
- Sprint 30+: Beta 5인 운영 + 인터뷰 + Phase 2 (Monte Carlo) 시작 검토

### Path B 결정 시

- Sprint 29: BL-001 / BL-002 (P0 처리)
- Sprint 30: BL-003 Bybit mainnet runbook + mainnet 72h 검증
- Sprint 31: Beta open 인프라 + 지인 5인

## 갱신 이력

- 2026-05-04 — Sprint 28 Slice 1b 첫 작성. office-hours Addendum (2026-05-04) Phase 4 결정 = Path A1 추천.
