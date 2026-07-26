# `superpowers/reviews/` — x1x3 5 워커 × 4 evaluator cross-validation

> **총 파일:** 20개 · **기간:** 2026-04-23 (단일 일자, 5 워커 L2 Deep Parallel 진행)
> **출처:** Sprint X1+X3 — 5 워커 × 4 evaluator 매트릭스
> **상위 INDEX:** [`../INDEX.md`](../INDEX.md)

## 20 review 매트릭스

5 sprint (W1-W5) × 4 evaluator = 20 파일. 각 sprint 의 plan 은 `../plans/2026-04-23-x1x3-w[1-5]-*.md` 에 위치.

| 워커 (W#) | 주제                     | plan 파일                                              | review 4 파일                                               |
| --------- | ------------------------ | ------------------------------------------------------ | ----------------------------------------------------------- |
| **W1**    | Alert heuristic loose    | `plans/2026-04-23-x1x3-w1-alert-heuristic-loose.md`    | `2026-04-23-x1x3-w1-{codex,codex-self,opus,sonnet}-eval.md` |
| **W2**    | TA SAR Parabolic         | `plans/2026-04-23-x1x3-w2-ta-sar-parabolic.md`         | `2026-04-23-x1x3-w2-{codex,codex-self,opus,sonnet}-eval.md` |
| **W3**    | Equity chart width fix   | `plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md`   | `2026-04-23-x1x3-w3-{codex,codex-self,opus,sonnet}-eval.md` |
| **W4**    | Trade analysis breakdown | `plans/2026-04-23-x1x3-w4-trade-analysis-breakdown.md` | `2026-04-23-x1x3-w4-{codex,codex-self,opus,sonnet}-eval.md` |
| **W5**    | Rerun button             | `plans/2026-04-23-x1x3-w5-rerun-button.md`             | `2026-04-23-x1x3-w5-{codex,codex-self,opus,sonnet}-eval.md` |

## 4 evaluator 패턴

| Evaluator       | 역할                        | 파일 명 패턴       |
| --------------- | --------------------------- | ------------------ |
| **codex-eval**  | Codex CLI (외부)            | `*-codex-eval.md`  |
| **codex-self**  | Codex 자기 평가 (내부 메타) | `*-codex-self.md`  |
| **opus-eval**   | Claude Opus 평가            | `*-opus-eval.md`   |
| **sonnet-eval** | Claude Sonnet 평가          | `*-sonnet-eval.md` |

## 결과 요약 (`reports/` cross-link)

x1x3 최종 합산 결과: [`../reports/2026-04-23-x1x3-final.md`](../reports/2026-04-23-x1x3-final.md)

- 5 sprint 모두 codex+Opus+Sonnet 3-way 합의 1차 PASS
- 사용자 개입 1회 (전체 32분 중 1회 — 자율 병렬 운영 검증됨)
- LESSON-019 commit-spy backfill 후속 → BL-010 등록

## 활용 정책

- 본 디렉토리 review 는 **x1x3 cross-validation 매트릭스 영구 기록** — 향후 같은 패턴 (3-way evaluator) 적용 시 reference.
- 신규 review 는 `dev-log/` 에 sprint 회고와 통합 (별도 디렉토리 비권장).
