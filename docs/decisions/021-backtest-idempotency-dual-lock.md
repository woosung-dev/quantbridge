# ADR-021: backtest 제출 멱등성 — Redis + PG advisory dual-lock 유지 (단일 unit 통합 거부)

> **상태:** 확정 (Accepted)
> **일자:** 2026-06-30
> **출처:** 2026-06-30 verification loop / backtest-deepen ([`2026-06-30-backtest-deepen.md`](../dev-log/2026-06-30-backtest-deepen.md)) 의 후보 C3 — improve-codebase-architecture audit 가 제안, codex challenge 가 KILL.
> **관련:** [`backtest/service.py:99-144`](../../backend/src/backtest/service.py) (Redis mutex + replay) · `service.py:904-914` (body-hash) · [`backtest/repository.py:245-263`](../../backend/src/backtest/repository.py) (PG advisory lock)

---

## 배경

backtest deepen 감사가 "제출 멱등성 결정이 4 조각(Redis 분산 mutex / module-level body-hash / PG advisory lock / replay 조회)에 흩어져 Locality 가 깨졌다"며, 이를 **하나의 멱등 결정 unit 으로 응집**하는 deepening 후보(C3)를 올렸다. repository.py 주석이 split 계약을 직접 서술할 만큼 분산이 명시적이다.

## 결정

**통합하지 않는다.** Redis mutex + body-hash + PG advisory lock + replay 의 현재 2-layer 분산 구조를 유지한다.

## 근거 (왜 통합을 거부하는가)

codex adversarial challenge + 코드 대조 결과:

- **의도적 layered 설계** — Redis lock(빠른 분산 mutex, best-effort) + PG advisory lock(authority, 트랜잭션 경계 내 직렬화)은 **서로 다른 실패 모드를 덮는 belt-and-suspenders** 다. Redis 가 죽어도 PG advisory 가 중복 작업을 막는다. 단일 unit 으로 묶으면 이 2-layer 방어의 독립성이 흐려진다.
- **잘 테스트됨** — body-hash/replay 단위 테스트 + 멱등 경로 통합 테스트가 이미 존재. 통합 리팩터는 **risk 를 삭제하지 않고 추상화만 추가**한다(Ousterhout deletion test 실패 — 복잡도가 한 곳에 모이지 않고 단지 이동).
- **money-path 인접** — 중복 백테스트 제출 → 중복 Celery 작업. 동작 보존 검증 비용이 locality 이득보다 크다.

## 대안 (거부됨)

- _단일 `IdempotencyDecision` unit (Repository 를 끼고 도는 진입점)_ — codex 판정 = over-engineering. 2-layer 의 독립 실패 방어를 단일 추상 뒤로 숨기면 미래 디버깅 시 어느 layer 가 작동했는지 불투명.

## 결과

- 향후 architecture audit / deepen 세션은 **backtest 멱등성 통합을 재제안하지 않는다.** 분산은 결함이 아니라 의도된 2-layer 방어다.
- 단, codex 가 별개로 지적한 **Redis×PG race + replay 결합 경로의 integration 테스트 gap** 은 유효 → 통합이 아니라 _race 재현 테스트 보강_ 으로 별도 처리(필요 시 P3 BL).
- 본 ADR 은 "분산 idempotency = 의도" 라는 load-bearing 맥락을 보존해 동일 후보의 반복 제안을 차단한다.
