# Deepen-modules — backtest (1차, verification loop)

> **2026-06-30. verification loop (methodology-tooled Stage 0/4) 의 아키텍처 감사 단계.** trading 은 이미 3회 deepen(05-09/05-15/06-26-deepen-2) 소진 + deepen-2 L53 가 "다음=backtest/optimizer" 권고 → **frame change 로 감사 대상을 trading → backtest 재조정**(사용자 재결정). backtest 는 미감사 도메인. **Iron Law = 1 호출 = backtest 1 도메인.** Phase 3 사용자 승인 전 코드 수정 0 — BL 등재만. 기존 BL-383(catch-all)/BL-236(objective_metric)/BL-362(run_live divergence) 와 무중복.

## 방법

ultracode Workflow — 4 병렬 Explore agent(v2_adapter / service+config / support modules / test-surface) + 합성 agent(dedup + 5축 점수) → 후보 6종. 이후 **codex challenge**(adversarial, 실제 파일·테스트 전수 정독, 540k tokens)로 over-engineering 살처분. codex 발견은 직접 코드 검증 후 반영(§7.3 circular-trust 차단).

## Phase 1 — Module Inventory (backtest, 3851 LOC)

| 모듈                                                    | LOC            | 분류                                         | 비고                                       |
| ------------------------------------------------------- | -------------- | -------------------------------------------- | ------------------------------------------ |
| `engine/v2_adapter.py`                                  | 964            | god-file (orchestration + finance math 혼재) | V2RunResult→BacktestOutcome + 지표 10 함수 |
| `service.py`                                            | 914            | mixed (submit gate + idempotency + sizing)   | config_mapper/dispatcher/serializer 추출됨 |
| `schemas.py` / `engine/types.py`                        | 351 / 214      | multi-SSOT (BacktestMetrics 평행 정의)       | + serializers + `_to_detail` = 4 site      |
| `repository.py`                                         | 322            | deep (PG advisory idempotency)               | Redis mutex 와 2-layer 방어                |
| `serializers.py` / `config_mapper.py` / `dispatcher.py` | 197 / 117 / 56 | 이미 추출된 deep helper                      | deletion test 통과 — 비등재                |

## Phase 2 — 후보 6종 → codex challenge 처분

| 후보                                 | 처분            | 근거                                                                                                             |
| ------------------------------------ | --------------- | ---------------------------------------------------------------------------------------------------------------- |
| C4 sizing-canonical typed seam       | **KEEP (최강)** | `dict[str,Any]` key drift → silent 잘못된 sizing(money-path)                                                     |
| C2 BacktestMetrics 4-site multi-SSOT | **KEEP (강화)** | codex 가 4번째 site `_to_detail` 추가 발견, field-parity 무검증                                                  |
| C1 finance-math 추출                 | **KEEP (정정)** | codex DOWNGRADE 는 phantom `engine/metrics.py` 오인 → **직접 검증 = 부재**, math 전부 v2_adapter L707-912 → KEEP |
| C6 exit `fill_type` 중복 위임        | **KEEP**        | v2_adapter:265/:568 char-identical, 주석 SSOT 주장과 코드 불일치                                                 |
| C5 equity↔PnL reconciliation oracle  | **DOWNGRADE**   | golden/cost invariant 일부 존재 → 좁은 closed/no-funding oracle 만                                               |
| C3 idempotency dual-lock 통합        | **KILL**        | 의도적 layered(Redis+PG belt-and-suspenders) + 잘 테스트됨 = over-engineering → [ADR-021]                        |

## STOP 조건 재측정 = 해당 없음

deepen STOP(coverage <70% → test 우선)을 재측정. backtest 는 46 test(3.3x) — v2_adapter(golden oracle + metrics_real_extract) / serializers(round-trip 2종) / service(submit/resolve 단위 다수) 전부 refactor-safe. 단 C3(idempotency Redis×PG race 결합) + C5(cross-stage reconciliation)는 module-wide STOP 이 아니라 **좁은 경로 test-first** 성격(C3 는 KILL, C5 는 oracle 선작성으로 등재).

## Phase 3 — Grilling 결정 로그

- 사용자 결정 = **생존 5건 전부 등재**(C1/C2/C4/C5/C6) + **C3 = ADR 기록**(load-bearing 거부, 재제안 차단).
- 우선순위 = C4/C2 P2(money-path/hardening), C1/C6/C5 P3.

## Phase 4 — 등재

- `backlog.md` P2 = **BL-387**(C4 sizing typed seam) / **BL-388**(C2 metrics 4-SSOT), P3 = **BL-389**(C1 metrics 추출) / **BL-390**(C6 fill_type 위임) / **BL-391**(C5 reconciliation oracle). 45 → 50 active.
- [ADR-021](../decisions/021-backtest-idempotency-dual-lock.md) — C3 idempotency dual-lock 유지(통합 거부) 기록.
- Sprint 권고: backtest deepening sprint 에 BL-387(money-path 우선) + BL-388 묶음, BL-389+391 묶음(metrics 추출 + reconciliation oracle 동반), BL-390 clean win.

## 교훈 (LESSON 후보)

- **codex challenge 의 factual 오인 차단 (§7.3 재확인):** codex 가 phantom `engine/metrics.py` 존재를 근거로 C1 을 DOWNGRADE → `ls` 1줄 검증으로 부재 확인 → KEEP 정정. **adversarial 모델의 finding 도 코드 대조 검증 의무**(circular-trust 차단). 동시에 codex 가 C2 를 강화(4번째 site 발견) + C3 를 정당하게 KILL — adversarial 의 순효과는 명확히 양(+).
- **over-deepened 도메인 frame change:** plan 의 god-file 랭킹(trading providers/tasks)이 3회 deepen 이력을 몰랐음 → prereq 스파이크(§7.4)가 재등재 위험 차단 + 대상 재조정. **deepen 전 dev-log 이력 grep 의무.**

## 다음 audit 권고

`optimizer` 또는 `stress_test` 도메인 (Iron Law = 새 session 분리 호출). optimizer 는 genetic/bayesian coverage <70% 가능성 → STOP(test-first) 선확인 권장.
