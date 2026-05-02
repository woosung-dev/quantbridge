# H2 Sprint 21 — BL-096 Coverage Expansion + 422 Shape + Alias Ordering Fix

> **작성**: 2026-05-02 (BE 단계 완료 시점). FE Phase D 는 후속 세션.
> **브랜치**: `stage/h2-sprint21` (cascade from `stage/h2-sprint20`).
> **Path**: B-1 (사용자 confirm). codex G.0 round 1 (RETHINK + P1 9건) → round 2 (GO_WITH_FIXES + 신규 P1 0건).
> **결과**: BE +38 신규 tests + Sprint 8c 회귀 100% PASS (385+/0/16 skip). ruff 0 / mypy 0.

---

## §0. 배경

Sprint 20 Day 0 dogfood 에서 본인 6 pine 중 2/6 = 33% backtest 통과. 핵심 모순:

- RsiD = `s3_rsid` corpus, DrFXGOD = `i3_drfx` corpus = **Sprint 8c strict=True 통과 사례** (252 pine_v2 tests green)
- production parse-preview 는 reject = **검증 corpus vs production supported list 이중 잣대**

추가로 Day 0 7번 N (사용자 "주문창이 안 보여서 된거긴한것 같은데?") = TestOrderDialog success state 부재 + Backtest 422 가 unsupported builtin 목록 친절 표시 안 함.

## §1. codex G.0 Generator-Evaluator 루프

### round 1 (medium, session `019de8f3-3f6d-7833-b5d2-b8f289c7caba`, 397k tokens) — VERDICT: RETHINK

P1 9건 발견:

1. **alias ordering bug** (interpreter.py:597+796) — user_function dispatch 가 v4 alias 보다 뒤. `abs(x) =>` 정의 시 alias `abs → math.abs` 가 압도 → silent correctness bug
2. **NOP-degrade Trust Layer 위반** — coverage.py:70 의 ADR-013 §4 주석이 이미 "partial silentfail → 명시적 unsupported" 로 박힘. heikinashi/security/study graceful degrade 정책은 정면 충돌
3. **prefix scope 폭발** — `_ENUM_PREFIXES` 에 `currency.`/`strategy.`/`timeframe.` 추가 시 false-pass risk
4. P1 #1 의 동일 fix
5. **422 shape 문자열 only** — `{"detail": "Strategy contains unsupported Pine built-ins: ..."}`. FE split parsing 강요
6. **fixture 라이선스 risk** — tmp_code/pine_code 의 LuxAlgo/DrFXGOD 원문 복사
7. (free) `.claude/CLAUDE.md` / `~/.claude/plans/h2-sprint-22-prompt.md` = 외부 디렉토리 수정
8. (free) SLO 80% (5/6) = heikinashi/security false-pass 로만 달성 = fraud
9. (free) `timestamp()` 이미 interpreter:667 존재. "신규 stub" 부정확

### round 2 (medium, session `019de8fb-0c80-77f0-bcdb-99c201b9f070`, 254k tokens) — VERDICT: GO_WITH_FIXES

신규 P1 0건. 1개 minor amendment (user_function lookup 시 `"." not in name` guard 명시) 반영.

## §2. 변경 파일 (BE)

| 파일                                                           | 변경                                                                                                                                                                                                                                    | LOC     |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `src/backtest/exceptions.py`                                   | `StrategyNotRunnable.__init__(detail, *, unsupported_builtins)`                                                                                                                                                                         | +12     |
| `src/main.py`                                                  | `_app_exc_handler` → module-level `app_exc_handler` (test import 가능) + StrategyNotRunnable detail.unsupported_builtins 노출                                                                                                           | +30     |
| `src/backtest/service.py:136`                                  | `raise` 시 `unsupported_builtins=list(coverage.all_unsupported)` 전달                                                                                                                                                                   | +4      |
| `src/strategy/pine_v2/interpreter.py:593+`                     | user_functions 우선 dispatch + `"." not in name` guard. line 796-799 의 중복 dispatch 제거 (unreachable)                                                                                                                                | +9 / -3 |
| `src/strategy/pine_v2/coverage.py`                             | `_V4_ALIASES` +8 (abs/max/min/pivothigh/pivotlow/barssince/valuewhen/timestamp) + 3 explicit constant frozenset (`_CURRENCY_CONSTANTS` 12개 / `_STRATEGY_CONSTANTS_EXTRA` 6개 / `_TIMEFRAME_CONSTANTS` 8개) + `study` declaration alias | +35     |
| `tests/backtest/test_exception_handler.py`                     | 5 신규 (attribute 보유 / default empty / handler list 노출 / 다른 AppException unaffected / empty list key 유지)                                                                                                                        | +110    |
| `tests/strategy/pine_v2/test_user_function_alias_collision.py` | 3 신규 (abs override / max override / dotted dispatch 보호)                                                                                                                                                                             | +110    |
| `tests/strategy/pine_v2/test_coverage_sprint21.py`             | 26 신규 (v4 alias 8 + currency 4+1 + strategy 3+1 + timeframe 3+1 + study NOP + heikinashi/security/request.security 유지 + RsiD integration)                                                                                           | +260    |
| `tests/strategy/pine_v2/test_trust_layer_parity.py`            | P-2 union test 가 신규 3 explicit constant set 포함 (Trust Layer SSOT sync)                                                                                                                                                             | +5 / -2 |
| `tests/strategy/pine_v2/test_dogfood_pine_corpus_e2e.py`       | 4 신규 (RsiD ✅ / UtBot 🔴 Trust Layer / DrFX 🔴 Sprint 22+ scope / 통과율 baseline)                                                                                                                                                    | +120    |
| `tests/fixtures/dogfood_corpus/rsid_minimal.pine`              | QB-authored minimal v4 (8 alias 사용)                                                                                                                                                                                                   | +30     |
| `tests/fixtures/dogfood_corpus/utbot_minimal.pine`             | QB-authored UtBot-style (heikinashi/security reject 회귀)                                                                                                                                                                               | +25     |
| `tests/fixtures/dogfood_corpus/drfx_partial.pine`              | QB-authored DrFX-style baseline (Sprint 22+ scope)                                                                                                                                                                                      | +30     |

**누적 BE +38 신규 tests**. 라이선스: 사용자 보관 LuxAlgo/DrFXGOD/UtBot 원문 미복사.

## §3. 검증 결과

### 자동 (CI green)

- `pytest tests/backtest/test_exception_handler.py tests/strategy/pine_v2/test_user_function_alias_collision.py tests/strategy/pine_v2/test_coverage_sprint21.py tests/strategy/pine_v2/test_trust_layer_parity.py tests/strategy/pine_v2/test_dogfood_pine_corpus_e2e.py` → **54 passed / 8 skip / 0 fail**
- `pytest tests/strategy/pine_v2/` (Sprint 8c 회귀 + Sprint 21 신규) → **388 passed / 16 skip / 0 fail**
- `ruff check` / `mypy src/main.py src/strategy/pine_v2/coverage.py src/strategy/pine_v2/interpreter.py src/backtest/exceptions.py` → **0/0**

### Trust Layer 정합

- heikinashi / security (no-namespace) / request.security 모두 unsupported 유지 (ADR-013 §4)
- 본인 UtBot indicator easy/medium 통과 포기 — silent corruption risk 보다 explicit reject 우선
- Sprint 22+ 의 strict toggle (degraded_builtins 별도 카테고리) 옵션 보전

### SLO

- 본인 6 pine 통과율 33% → **50% (3/6, +1 RsiD)**
- self-assessment 8 → 9 의 본질은 **신뢰** (alias ordering correctness fix + backend shape 표준화 + Trust Layer 정합)
- 통과율 절대값 < 신뢰 향상

## §4. 사용자 라이브 검증 절차 (Phase H 후속)

```bash
# 1. 격리 docker stack 가동
make up-isolated

# 2. localhost:3100/strategies/new
#    - 본인 RsiD strategy paste → parse_preview ✅ 확인
#    - Backtest 시도 → ✅ 통과 + trade 발생

# 3. 본인 UtBot indicator easy/medium paste → parse_preview 🔴 + unsupported 목록에
#    heikinashi, security 명시 표시 확인 (Trust Layer)

# 4. self-assessment 갱신 (8 → 9 회복 검증)
```

## §5. Phase D — FE BL-093+095 ✅ 완료

**파일** (4 source + 3 test):

- `frontend/src/lib/unsupported-builtin-hints.ts` 신규 — heikinashi/security/request.security/timeframe.\* 등 friendly mapping (corruption / noop / alternative 카테고리 분기)
- `frontend/src/features/trading/components/test-order-dialog.tsx` — `await res.json()` body 의 `id` 캡처 → `toast.success("테스트 주문 발송됨", { description: "#" + id.slice(-8) })`. body parse 실패 시 idempotency_key fallback (`client #${slice(-8)}`)
- `frontend/src/features/trading/components/orders-panel.tsx` — 7번째 컬럼 `Broker ID` + `<BrokerBadge orderId={...} />` (fixture-\* 오렌지 mock vs broker 녹색 시각 분기, codex G.2 P2 — UUID 판정 X)
- `frontend/src/app/(dashboard)/backtests/_components/backtest-form.tsx` — 422 응답의 `err.detail?.detail?.unsupported_builtins` (구조화 list) 직접 접근 → `getUnsupportedBuiltinHints()` 변환 → inline 카드 + edit link. 빈 list 또는 detail 부재 시 fallback root.serverError

**Tests** (8 신규):

- `__tests__/test-order-dialog.test.tsx`: +1 happy path with json body — toast description 에 broker order id slice(-8) 검증
- `__tests__/OrdersPanel.test.tsx`: +3 broker evidence 시나리오 (null / fixture-\* / real broker)
- `__tests__/backtest-form.test.tsx`: +4 422 패턴 (구조화 list / 빈 list / detail 부재 / non-422)

**자동 검증**: FE 251 passed / 0 fail. tsc 0 / eslint 0 / pnpm build OK.

## §6. Phase E — codex G.2 Challenge

**G.2 (high reasoning, iter cap 2, 808k tokens)** — VERDICT: GO_WITH_FIXES + 신규 P1 3건 발견.

| 발견                                                                                                                                                                                                                                         | 분류                       | 처리                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **P1 #1 `timeframe.*` false-pass** — Sprint 21 v2 plan 에 추가한 `_TIMEFRAME_CONSTANTS` 가 coverage supported 였지만 interpreter `_eval_attribute` 의 `timeframe.*` runtime 평가 미구현 = preflight pass 후 runtime fail (silent corruption) | Sprint 21 직접 신규 추가분 | **즉시 fix** (frozenset 빈 세트로 회수) + dogfood corpus test 갱신 + friendly hints 의 `timeframe.*` noop 추가 |
| P1 #2 `strategy.exit` coverage/interpreter parity (pre-existing)                                                                                                                                                                             | Sprint Y1 부터 잔존        | **BL-098 분리** Sprint 22+                                                                                     |
| P1 #3 `vline` coverage/interpreter parity (pre-existing)                                                                                                                                                                                     | Sprint Y1 부터 잔존        | **BL-099 분리** Sprint 22+                                                                                     |

**P2** (해소 또는 Sprint 22+):

- `unsupported-builtin-hints.ts` 의 `max/min/abs` 권장 hint 부정확 (Sprint 21 alias ordering fix 후 user function 우선 → 충돌 risk 사라짐) → **즉시 정정** (3 hint 제거, generic fallback 활용)
- BrokerBadge `title` 의 broker order id privacy → Sprint 22+ (스크린캡처 risk, secret 은 아님)
- `api-client.ts:53` 의 nested `detail.code` 미추출 (`ApiError.code = "unknown_error"` 항상) → Sprint 22+ (현재 BacktestForm 영향 작음)
- QB-authored fixture test 가 "at least one Sprint 22+ unsupported" 만 검증 → expected unsupported 전체 set 회귀로 강화 (Sprint 22+)

**G.2 후속 자동 검증** (P1 #1 fix 후): BE 388 회귀 + Sprint 21 신규 50+8 tests / 0 fail. FE 251 / 0 fail. tsc/eslint/ruff/mypy 0/0/0/0.

## §7. 신규 BL 등록 (codex G.2 분리)

| ID                     | 제목                                                                                                     | Priority | est                        |
| ---------------------- | -------------------------------------------------------------------------------------------------------- | -------- | -------------------------- |
| **BL-097** ✅ Resolved | interpreter alias ordering correctness — user_functions 우선 dispatch                                    | P1       | (Sprint 21 Phase A.1 흡수) |
| **BL-098**             | `strategy.exit` coverage/interpreter parity — coverage supported / interpreter dispatch 미구현           | P1       | S (1h)                     |
| **BL-099**             | `vline` coverage/interpreter parity — coverage supported / `_NOP_NAMES` 미포함                           | P1       | S (30m)                    |
| **BL-100**             | `timeframe.*` runtime NOP — interpreter `_eval_attribute` 추가 또는 strict toggle 설계 후 supported 전환 | P2       | M (2-4h)                   |

## §8. 후속 (Phase G + H)

1. **Phase G — commit + PR**
   - FE + docs sync + G.2 fix 묶음 commit (BE 는 이미 commit `f45c3ce`)
   - 사용자 수동 stage→main PR

2. **Phase H — 사용자 라이브 self-assessment**
   - `make up-isolated` → `localhost:3100/strategies/new` → 본인 RsiD strategy paste → parse_preview ✅ + backtest ✅ 검증
   - UtBot easy/medium → 422 inline 카드 + heikinashi/security/timeframe.period 친절 표시 확인
   - TestOrderDialog → toast description broker id slice 노출 확인 + OrdersPanel BrokerBadge 시각 분기 확인
   - 8 → 9 회복 검증 (Trust Layer 정합 + alias ordering correctness + backend shape 표준화 의 trust signal)
   - `docs/dev-log/2026-05-XX-dogfood-day1-sprint21.md` 작성

## §6. Sprint 22+ 이관

| 조건                                                        | trigger                                                                                           |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| RsiD ✅ 라이브 + UtBot reject 친절 표시 + self-assessment 9 | Sprint 22 = B-2 (BL-091 architectural) 또는 strict toggle (heikinashi/security degraded_builtins) |
| RsiD 도 fail                                                | alias ordering fix 회귀 분석 + currency/strategy/timeframe explicit set 보강                      |
| UI broker evidence 7번 N → Y 회복                           | Sprint 22 진입 OK                                                                                 |

## §7. 참조

- master plan v2.1: `~/.claude/plans/parsed-skipping-marshmallow.md` (codex G.0 round 1+2 반영)
- codex G.0 round 1 transcript: 397k tokens, RETHINK + P1 9건
- codex G.0 round 2 transcript: 254k tokens, GO_WITH_FIXES + neue P1 0건
- ADR-013 (Trust Layer 정합): `docs/dev-log/013-*.md`
- Sprint 8c 회고: memory `project_sprint8c_complete.md`
- Sprint 20 Day 0: `docs/dev-log/2026-05-02-sprint20-dogfood-day0-setup.md`

## End-of-dev-log
