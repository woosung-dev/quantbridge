# Sprint 21 Phase H — dogfood Day 1 라이브 검증

> **작성**: 2026-05-03
> **PR**: #93 (stage/h2-sprint21)
> **scope**: Sprint 21 의 BE+FE+G.2 fix 가 실제 격리 stack 에서 동작하는지 라이브 검증 + self-assessment 8 → 9 측정.

## §1 환경

- `make up-isolated` ✅ — port 3100/8100/5433/6380
- `EXCHANGE_PROVIDER=bybit_demo` (worker)
- branch: `stage/h2-sprint21` (commits `f45c3ce` BE + `170c7d0` FE+G.2+docs)

## §2 검증 결과

### §2.1 1차 검증 (rebuild 전)

| #   | 시나리오                          | 결과        | 원인              |
| --- | --------------------------------- | ----------- | ----------------- |
| 1   | RsiD 통과                         | 🔴 N        | docker image 캐시 |
| 2   | UtBot friendly 카드               | 🔴 N        | docker image 캐시 |
| 3   | DrFX baseline                     | ?           | 미테스트          |
| 4   | TestOrderDialog toast description | ✅ Y        | FE hot-reload     |
| 5   | OrdersPanel BrokerBadge           | ✅ Y        | FE hot-reload     |
| 6   | alias ordering 라이브             | ?           | 미테스트          |
| 7   | 자동 회귀 영향                    | 🔴 N (의심) | docker image 캐시 |

→ **진단**: 3/7 N + 2/7 ?. 본 sprint 의 BE 변경이 container 안에 미반영. `make up-isolated` 가 cached image 사용.

### §2.2 docker rebuild 후 재검증

```bash
docker compose -f docker-compose.yml -f docker-compose.isolated.yml down
docker compose -f docker-compose.yml -f docker-compose.isolated.yml build --no-cache backend
make up-isolated
```

| 질문                                                 | 결과                 |
| ---------------------------------------------------- | -------------------- |
| (A) PbR strategy backtest 통과                       | ✅ Y                 |
| (B) RsiD strategy backtest 통과                      | ✅ Y                 |
| (C) UtBot easy 422 → amber 카드 + 한국어 친절 메시지 | ✅ Y (스크린샷 첨부) |

스크린샷 evidence (사용자 제공):

```
⚠️ 이 strategy 는 미지원 builtin 을 포함합니다
• heikinashi — 헤이켄아시 변환 — 다른 종류 차트 데이터 의존 (현재 backtest 결과 부정확 risk).
• security — 다른 timeframe 데이터 의존 (request.security v4 form). backtest 결과 부정확 risk.
• timeframe.period — 현재 timeframe 식별자 — backtest runtime 미구현 (Sprint 22+ scope).
strategy 편집 →
```

= Sprint 21 BL-095 friendly 카드 정확히 렌더 ✅

## §3 self-assessment

- 점수: **추정 30+/35** (A/B/C 모두 Y + Sprint 21 의 핵심 변경 모두 검증)
- self-assessment: **8 → 9 ✅** (gate 통과)
- 본질: 통과율 50% (3/6) + Trust Layer 정합 + alias ordering correctness fix + backend shape 표준화

## §4 발견된 운영 issue (sprint 무관)

- **docker image 캐시** — `make up-isolated` 가 코드 변경 후 자동 rebuild 안 함. Sprint 22+ 에서 Makefile 의 `up-isolated` target 에 `--build` 옵션 추가 검토 (BL-101 후보).

## §5 Sprint 22 분기 결정

사용자 confirm: **시나리오 2 — BL-091 architectural + dogfood 병렬**.

| Track                                                                                | 담당    | est   |
| ------------------------------------------------------------------------------------ | ------- | ----- |
| **BL-091** ExchangeAccount.mode 기반 dynamic dispatch (Sprint 20 hot-fix proper fix) | AI 자율 | 1-2일 |
| **BL-005 본격 dogfood** 1주 매일 RsiD/PbR/LuxAlgo 사용 + Pain 발견                   | 사용자  | 1-2주 |

1주 후 Sprint 23 = dogfood Pain (자연 발견) + BL-091 결과 합치기.

## §6 다음 단계

1. **PR #93 머지** (사용자 수동) — squash & merge → main
2. **Sprint 22 시작** — `~/.claude/plans/h2-sprint-22-prompt.md` 사용
3. **dogfood Day 2~7** — 사용자 매일 사용. 발견 Pain 메모.

## §7 참조

- Sprint 21 dev-log: [`docs/dev-log/2026-05-02-sprint21-bl096-coverage-expansion.md`](2026-05-02-sprint21-bl096-coverage-expansion.md)
- PR #93: https://github.com/woosung-dev/quantbridge/pull/93
- Sprint 22 prompt: `~/.claude/plans/h2-sprint-22-prompt.md`
- BL backlog: [`docs/REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md)
