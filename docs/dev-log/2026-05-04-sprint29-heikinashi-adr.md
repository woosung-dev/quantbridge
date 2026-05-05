# ADR — heikinashi Trust Layer 위반 인정 + dogfood-only flag (Sprint 29 Slice A)

> **Date:** 2026-05-04
> **Status:** Accepted (Sprint 29 D1 = (a))
> **BL:** BL-096 partial 의 핵심 결정

## Context

UtBot indicator + UtBot strategy 가 `heikinashi()` 사용. Heikin-Ashi 캔들은 일반 OHLC 와 다른 변환 — `(open+close)/2`, `(open+high+low+close)/4` 등. backtest 가 일반 OHLC 로 실행되면 Pine 원본의 의도와 다른 결과 산출 가능 (거짓 양성 risk).

## Decision

옵션 (a) 채택 — Trust Layer 위반 인정 + dogfood-only flag.

- `heikinashi()` 를 일반 OHLC 그대로 반환 (NOP)
- `CoverageReport.dogfood_only_warning` 필드 추가 — heikinashi 사용 감지 시 "결과가 Pine 원본과 다를 수 있음" warning
- 사용자 명시 동의 후 backtest 실행 (FE 적용 Sprint 30+ deferred)
- ADR-008 Addendum 후보 (Beta open prereq)

## Consequences (긍정)

- UtBot indicator + UtBot strategy 동시 PASS → Sprint 29 통과율 5/6 도달
- dogfood-first indie SaaS 정합 (본인이 거짓 양성 가장 먼저 발견)
- transparency — ADR 영구 기록으로 Trust Layer 위반 명시

## Consequences (부정 / risk)

- heikin-ashi 캔들 ↔ 일반 OHLC 차이로 backtest 결과 거짓 양성 가능
- 사용자가 warning 무시 시 잘못된 전략 검증 risk
- Trust Layer 정합 위반 (architecture.md:286-318)

## Alternatives Considered

- (b) heikinashi reject 유지 — Sprint 29 dual metric (5/6) 미달성
- (c) ohlcv 변환 layer 신설 — scope 6-10h, Sprint 29 over

## Sprint 30+ trigger

ADR-009 Candle transformation layer 신설 — Heikin-Ashi + Renko + Range bar 정확 변환 layer. 본인 dogfood 에서 거짓 양성 발견 시 trigger.

## References

- Spec: `docs/superpowers/specs/2026-05-04-sprint29-coverage-hardening-design.md` D1
- Plan v2.1: `docs/superpowers/plans/2026-05-04-sprint29-coverage-hardening.md` §Slice A
- BL-096 partial: `docs/REFACTORING-BACKLOG.md`
- architecture.md Trust Layer: `docs/04_architecture/pine-execution-architecture.md:286-318`
