# QuantBridge 전체 정검 보고서 (Full-Project Inspection)

> **일자:** 2026-05-30 · **대상:** `main @ 4aa5c2a` (PR #305~#310 머지 후) · **방식:** `[0]~[5]` 마스터 프로토콜 (컨텍스트 싱크 → 병렬 탐색 → 멀티에이전트 평가자 패널 → MCP Playwright 라이브 → 로컬 CI 재현 → 수정+머지)
> **실행 계획 원본:** `~/.claude/plans/1-staged-conway.md`

---

## 1. Context — 왜 이 정검을 했는가

QuantBridge 는 Beta 본격 진입 결정(2026-05-17) 직후 **money-path 보안 감사(PR #305) → Phase C 배포 준비(#306~#310)** 로 자연 피벗했다. 그 결과 (a) `docs/TODO.md` 가 2026-05-17 에서 멈춰 실제 코드(#305~#310)와 drift 가 생겼고, (b) money-path 만 깊게 감사되어 trading 의 _정확성/커버리지/실패모드_ 축과 optimizer·stress·market_data·frontend 는 미감사 상태였으며, (c) Beta-ready 주장(Composite 7.5, Critical 0)이 #305~#310 이후 재검증되지 않았다.

본 정검은 프로젝트 goal/phase/로드맵 + 아키텍처/기능을 8 차원으로 하나하나 감사하고, adversarial 검증으로 false positive 를 걸러, 발견을 우선순위화한 결과다.

---

## 2. 방법론 (실행 증거)

| 단계                            | 내용                                                                                              | 결과                                                                                                                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[0]` 컨텍스트 싱크             | git/코드 ↔ 메모리·핸드오프 재-베이스라인                                                          | main @ 4aa5c2a clean 확인. **TODO.md stale 확인(1순위 거버넌스 발견)**. #305~310 diff ledger 작성.                                                                           |
| `[1]` 병렬 탐색                 | Explore 3 + Plan 2 에이전트                                                                       | 로드맵·아키텍처·CI/QA 3축 + 평가자패널·fix하네스 설계 확보.                                                                                                                  |
| `[2]` 멀티에이전트 평가자 패널  | 26 auditor(차원×도메인) + 발견당 default-to-refuted refuter + dedup, 별도 fresh-context opus 패널 | **198 에이전트 / ~16.7M 토큰** 분석. auditor 발견 169 → refuter 검증 → **생존 148 / 기각 21**. (워크플로우 조립 단계가 인프라 stall 로 실패 → 트랜스크립트에서 구조화 복구.) |
| `[3]` MCP Playwright 라이브     | 로컬 스택(:8100/:3100) + 테스트 계정 2개                                                          | §6 라이브 QA 섹션.                                                                                                                                                           |
| `[4]` 로컬 CI 재현              | ci.yml 전 step 동일 실행 (격리 5433/6380)                                                         | **베이스라인 green**: BE ruff/mypy clean + **pytest 1850 pass/0 fail**, FE lint/tsc clean + **vitest 716 pass** + build OK.                                                  |
| `[5]` 수정+atomic doc+순차 머지 | 격리 stage 브랜치, TDD, codex gate, 사용자 배치 승인                                              | §8 fix 실행 (진행).                                                                                                                                                          |

> **평가자 분리 + adversarial 검증이 핵심.** 발견한 auditor 와 검증한 refuter 가 서로 다른 fresh-context 에이전트다. refuter 는 "기본 기각" 입장에서 file:line 재현을 강제해 21건을 걸러냈다(§Refuted Appendix). codex 교차검증은 §7.

---

## 3. Decision Log — 선택지 기록 (요청사항)

> "어떤 선택지 A~C 가 있었고 무엇을 골랐나" 를 보고서에서 함께 보기 위함. 계획 단계 확정 12건 + 실행 중 결정.

| ID     | 결정                 | 선택지                                                                   | 채택        | 결정자      | 이유                                                                                                                                                                        |
| ------ | -------------------- | ------------------------------------------------------------------------ | ----------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DEC-1  | 실행 모드            | A)리포트+BL만 ★★★★★ / B)P0만 inline ★★★★ / **C)전부 fix-and-merge ★★**   | **C**       | 사용자      | 모든 code-fixable 수정 희망 (범위는 code-fixable+safe 로 bounding)                                                                                                          |
| DEC-2  | 라이브 Playwright    | **A)포함(계정 준비) ★★★★** / B)계정TBD / C)스킵                          | **A**       | 사용자      | 계정 2개 제공                                                                                                                                                               |
| DEC-3  | 깊이 배분            | **A)리스크 가중 ★★★★★** / B)균등                                         | **A**       | 사용자      | trading/배포/미검증 영역 집중                                                                                                                                               |
| DEC-4  | codex 주입           | A)셀별 / **B)P0·P1 adversarial+최종 synthesis** / C)최종만               | **B**       | AI추천      | 고-blast 지점 cross-model                                                                                                                                                   |
| DEC-5  | codex 예산 cap       | **A)P0/P1 상위 15** / B)무제한 / C)10                                    | **A**       | AI추천      | 0 P0 + 14 P1 → 전량 가능                                                                                                                                                    |
| DEC-6  | CONTESTED            | **A)플래그(차단X)** / B)차단 / C)drop                                    | **A**       | AI추천      | contested = signal                                                                                                                                                          |
| DEC-7  | money vs security PR | **A)분리** / B)번들                                                      | **A**       | AI추천      | 리뷰·롤백 독립                                                                                                                                                              |
| DEC-8  | 동시성               | **A)직렬(CI mutex)** / B)병렬                                            | **A**       | AI추천      | 단일 isolated 스택 5433/6380 충돌                                                                                                                                           |
| DEC-9  | stage push           | **A)QB_PRE_PUSH_BYPASS=1** / B)fix/\* 개명                               | **A**       | AI추천      | Option C 컨벤션 보존                                                                                                                                                        |
| DEC-10 | 감사 차원            | 7축 / **8축(D7 resilience)**                                             | **8축**     | AI추천      | 라이브 트레이딩 실패모드                                                                                                                                                    |
| DEC-11 | trading×보안 깊이    | DEEP / **CONFIRM**                                                       | **CONFIRM** | AI추천      | #305~310 방금 감사                                                                                                                                                          |
| DEC-12 | 최종 머지            | **A)배치 사용자승인(수동 stage→main)** / B)자동                          | **A**       | AI추천+헌법 | Git Safety Protocol                                                                                                                                                         |
| DEC-13 | 워크플로우 실패 복구 | A)재-resume(또 stall) / **B)트랜스크립트 구조화 추출** / C)소규모 재실행 | **B**       | AI추천      | resume 2회 stall → 캐시된 분석 198 에이전트 보존, 추출로 복구                                                                                                               |
| DEC-14 | P1-12 severity       | P0(즉시손실) / **P1(방어심층 갭)**                                       | **P1**      | AI+코드확인 | market order notional skip 은 거래소 margin 체크가 backstop, 의도된 tradeoff(주석 명시)                                                                                     |
| DEC-15 | S2 Trust 정합 방식   | **A)전부 구현 ★★★★★** / B)coverage 제거 ★★ / C)하이브리드(숫자만) ★★★    | **A**       | 사용자      | hl2/hlc3/ohlc4·barstate._ = 자명 정확, str._ = display NOP-safe. 제거(B)는 label/alert 의 str.tostring(backtest 0 영향) 과대차단 + hl2 류 순수 기능손실 = whack-a-mole 재발 |
| DEC-16 | live observability   | **A)S5 이관 ★★★★★** / B)S2 포함 ★★★                                      | **A**       | 사용자      | run_live strict=False silent swallow 는 money path 변경 → DEC-7 분리 + "money path 신중". S2 는 pine_v2 순수(mutation 0) 유지. → BL-362                                     |

---

## 4. 헤드라인 — 직접 코드 확인한 핵심 발견

### 4.1 ✅ P0 = 0 (good news)

#305~310 money-path hardening 이 유효하다. adversarial 패널이 trading 보안 표면을 CONFIRM 모드로 재공격했으나 **즉시 실손실급(P0) 신규 결함 0건**. kill-switch revival·IDOR·precision·notional 모델·stale-RUNNING reclaim 모두 살아있음을 확인.

### 4.2 ⚠️ 단, kill-switch/notional 방어가 *일부 경로*에서 얕다 (P1, 직접 확인)

- **P1-12 (`order_service.py:154-162`, 코드 확인됨):** notional/balance 가드는 `req.price is not None` 일 때만 발화 → **market order(price=None)는 notional 검증 skip**, leverage cap 만 1차 방어. `live_signal` 경로는 전 주문이 market order 라 notional 가드를 항상 우회. 주석에 의도된 tradeoff 로 명시되어 있고 거래소 margin 체크가 backstop 이므로 **P0 아닌 P1**. 개선: market order 는 mark price 로 근사 notional 가드.
- **P1-2 (`router.py`/`webhook.py`, trading/D3):** #305 의 realized_pnl→누적손실 kill-switch revival 이 **webhook 주문 진입 경로에선 realized_pnl 미기록 → 사실상 비활성**. live_signal 경로만 커버. webhook close 주문에 realized_pnl 매핑 필요.
- **P1-14 (`reconcile_fetcher.py:88-104`, trading/D7, BL-308):** `fetch_recent_orders` docstring 은 'closed+canceled' 라지만 `fetch_closed_orders` 만 호출 → **취소 주문 reconcile 누락**(silent). `fetch_canceled_orders` union 필요.

### 4.3 ⚠️ Trust Layer 누출 — 부분실행 금지 invariant 위반 (P1, strategy/D4)

- **P1-10 / P1-13 (`coverage.py` vs `interpreter.py`):** coverage 가 `str.tostring/tonumber/format/length`, `hl2/hlc3/ohlc4`, `barstate.is*` 를 **SUPPORTED 로 표기하지만 interpreter 가 미구현** → `is_runnable=True` 인데 런타임은 `PineRuntimeError` raise(backtest=strict True→FAILED / live=strict False→**silent swallow 후 실행 계속 = 오신호**). ADR-003 "미지원 1개라도 → 전체 Unsupported(부분실행 금지)" 위반. 구현 또는 coverage 에서 제거 둘 중 하나 필수.
- **✅ S2 해소 (DEC-15=A 전부 구현):** 망라 parity 테스트(`test_coverage_interpreter_parity.py` 의 `SUPPORTED_ATTRIBUTES`/`_STRING_FUNCTIONS`/`_MATH_FUNCTIONS` 전수 순회)가 audit 의 hand-found ~10건 + **미발견 18건**(currency.\_ 12 / strategy.commission\__ 3 / barstate 4중 일부 / **math.log10**)까지 총 **28 누출** 검출. interpreter.py 에 전부 구현(hl2/hlc3/ohlc4 = Pine 정의 1:1, barstate._ = bar*index/len 정확, str.* = NOP-safe/정확 parse, currency.\_ = code suffix, commission\_\_ = `_ATTR_CONSTANTS`). TDD RED 28→GREEN. 향후 SUPPORTED 추가분 누출은 본 망라 테스트가 CI 에서 자동 차단(영구 tripwire). live-path silent swallow observability 는 **BL-362(S5 이관, DEC-16=A)**.

### 4.4 ⚠️ 백테스트 지표 정확성 회귀 (P1, backtest/D4)

- **P1-5 (`config_mapper.py` vs `v2_adapter.py`):** `_TIMEFRAME_TO_FREQ` 가 '1m'→'1min' 매핑하는데 `_FREQ_HOURS_V2` 는 '1m' 키만 보유 → sub-hour timeframe 의 **avg_holding_hours 가 1440x/288x/96x 과대 계산**. 24-metric 신뢰성 직접 훼손. 키 체계 통일로 수정.

### 4.5 ⚠️ stress_test config 미전달 (P1, stress/D2, BL-222 follow-up)

- **P1-7 (`stress_test/service.py:295-322`):** `_execute_walk_forward` 가 `run_walk_forward` 에 `backtest_config` 미전달 → WF 의 IS/OOS 백테스트가 부모의 fees/slippage/leverage/sizing 대신 **기본값으로 실행**. Sprint 52 fix 가 WF 를 누락. CA/PS 패턴대로 config 주입.
- **✅ S3 해소:** `_execute_walk_forward` 에 `backtest_config = build_engine_config_from_db(bt)` 추가 + `run_walk_forward(..., backtest_config=backtest_config)` (CA/PS 와 동일). spy 회귀 테스트 2건(`test_execute_walk_forward_propagates_backtest_config` + null-config) — 기존 CA/PS propagation 테스트와 동일 패턴으로 init_cash/freq/fees/slippage/sizing 5필드 보존 검증. TDD RED 2→GREEN, stress_test 91 pass. 근본원인인 4-method boilerplate 중복(P1-9)은 **BL-363(P2 deepening)** 등재 — 현재는 per-engine propagation 테스트(WF+CA+PS)가 drift 가드.

### 4.6 ⚠️ optimizer Genetic 크래시 (P1, optimizer/D4, BL-234)

- **P1-9 (`genetic.py:187-188,318`):** CategoricalField 가 비숫자 문자열 카테고리일 때 `InvalidOperation` 크래시. 검증 거부 또는 str|Decimal 표현 분리 필요.
- **✅ S4 해소 (Option A = 비숫자 reject):** `_validate_genetic_search_pre`(genetic) + `_validate_bayesian_search_pre`(bayesian) 에 `CategoricalField.values` Decimal-parse 검사 추가 → 비숫자면 `InvalidOperation` 크래시(sampling/coerce) 대신 validation 단계에서 **명확한 422**(`values must be numeric (ordinal)`). 두 엔진 동일 정책(bayesian 은 skopt `_coerce_skopt_to_decimal` 크래시도 동일 차단). TDD RED 2→GREEN(`test_categorical_non_numeric_values_rejected` ×2), optimizer 149 pass. **codex review → P2 추가**: `Decimal('NaN'/'Infinity')` 은 parse 통과하나 후속 `int(...)` 런타임 크래시(500) → `is_finite()` 검사 추가(genetic+bayesian) + non-finite reject 테스트 2건(optimizer 151 pass). 진짜 string-label sweep(`['ema','sma']`)은 **BL-364(P2 feature)**. grid_search 는 CategoricalField 전체 거부(무관).

### 4.7 ⚠️ 프론트 거래소 계정 등록 에러 UX (P1, frontend/D8)

- **P1-1 / P1-11 (`register-exchange-account-dialog.tsx`):** API Key/Secret 입력 제출이 try/catch·onError 없음 → 실패 시 무피드백. OKX passphrase 클라 검증 부재(서버 422 비표시). test-order-dialog 의 root.serverError 패턴 재사용으로 수정.
- **P1-8 (`optimizer/page.tsx`):** optimizer 진입이 raw `backtest_id` UUID 직접 paste 요구(picker 부재). `useBacktests({status:'completed'})` Select 로 교체.

---

---

## 7. codex 교차검증 (DEC-4)

> P1 발견 대상 codex challenge(A) + 전체 synthesis gate(B). 결과는 §8 fix PR 단위로 `codex review` G.4 게이트에 연결. (codex 호출 결과는 실행 로그에 누적.)

### S2 codex challenge (adversarial, 769k tokens) — 6 findings, 재검증 후 처리

`stage/fix-trust-layer-leak` diff 를 codex 에 "값 자체가 틀릴 수 있는 지점" 으로 challenge. 6 finding 을 코드 직접 재확인(default-to-refuted) 후:

| #   | codex finding                                             | 재검증                                                                                                     | 처리                                                                                             |
| --- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | `hl2[1]`/`hlc3[1]`/`ohlc4[1]` history 가 na (silent 오값) | ✅ REAL — `_eval_subscript` 가 built-in series 만 history 처리, 합성 source 는 `_var_series` 미존재로 na   | **S2 에서 fix** — `_synthetic_source(name, offset)` helper (current+history 공용). TDD RED→GREEN |
| 2   | strategy.commission\_\* 선언이 PnL 에 미적용              | ⚠️ PRE-EXISTING — `strategy()` NOP 라 kwargs 미평가, 본 변경 이전부터 무시. coverage↔interpreter leak 아님 | out-of-scope — commission 모델링은 BL-186 계열 fidelity                                          |
| 3   | str.format `{0,number,#.##}` 미지원                       | ⚠️ TRUE — display-only NOP 설계, numeric feedback 희귀                                                     | known limitation (note)                                                                          |
| 4   | str.tostring(x, format) 의 format 무시                    | ⚠️ 동상 (display-only)                                                                                     | known limitation (note)                                                                          |
| 5   | barstate.islast = WF slice 마다 endpoint True             | ⚠️ single backtest = 정확(run 의 last bar). WF fold 도 각자 run = 합리적                                   | acceptable (note)                                                                                |
| 6   | barstate.ishistory/isconfirmed hardcoded True             | ⚠️ 기존 `barstate.isrealtime=False`(BL-242b) precedent 와 일관(backtest=전 bar historical)                 | consistent (note)                                                                                |

> codex ROI: 망라 테스트(28 누출)가 못 잡는 **value-correctness 갭(Finding 1, lagged 합성 source)** 추가 검출 → S2 같이 fix. Findings 2~6 은 adversarial 재검증으로 out-of-scope/pre-existing/consistent 판정(scope creep 차단).

## 8. 의사결정 매트릭스 — code-fixable 아닌 항목 (사용자 결정)

> 코드로 못 고치는 항목. P1-6(G8)이 여기 해당. 자동 머지 불가 — 사용자 결정 후 per-fix 루프 재진입.

| ID            | 항목                                 | 왜 code-fixable 아닌가 | 선택지                                                                                | AI 추천                                  | 차단         |
| ------------- | ------------------------------------ | ---------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------- | ------------ |
| **G1**        | TimescaleDB Cloud SQL 미지원         | 호스팅 플랫폼 선택     | a)self-host(VM/Railway/Render) b)관리형(Timescale Cloud) c)hypertable 제거+vanilla PG | **b)관리형** (ops 최소, hypertable 유지) | BL-071       |
| **G7**        | healthz/Celery readiness             | 런타임/ops 정책        | a)liveness-only b)broker ping c)web/worker probe 분리                                 | **c)분리**                               | BL-071       |
| **G8 / P1-6** | Celery 가 Cloud Run HTTP 리스너 필요 | 배포 아키텍처          | a)sidecar HTTP shim b)worker 를 Cloud Run 밖(VM) c)Cloud Run Jobs                     | **b)worker 분리**                        | BL-071       |
| **BL-070**    | 도메인+DNS+Cloudflare                | 외부 구매+DNS 24h      | (사용자 액션)                                                                         | 준비되면 진행                            | BL-072, beta |
| **BL-072**    | Resend 이메일+waitlist               | 외부 SaaS              | a)Resend b)Postmark/SES                                                               | **a)Resend**                             | BL-070 의존  |

> **실측 검증:** `/healthz` 가 5s+ 행(HTTP 000, Celery worker 미가동 시) / `/livez` 200 / `/health` 200 / `/startupz`·`/readyz` 404. → G7 readiness 정책이 실제 미정리(probe 가 healthz 면 Cloud Run never-ready). c)분리안 정당성 실증.

## 9. Fix 실행 로드맵 (Phase F — DEC-1 = 전부 fix-and-merge, 리스크 순서)

코드 수정 가능 + safe + test 표현 가능 발견을 격리 stage 브랜치로 수정. 각 테마 = 1 PR = TDD + 로컬 full-CI green + codex review + 사용자 배치 push/merge 승인(Option C).

| 순서 | stage 브랜치                        | 포함 P1/핵심                                                                 | 우선              |
| ---- | ----------------------------------- | ---------------------------------------------------------------------------- | ----------------- |
| S1   | `stage/fix-backtest-metric`         | P1-5 avg_holding_hours 1440x                                                 | P1 정확성         |
| S2   | `stage/fix-trust-layer-leak`        | P1-10/13 coverage↔interpreter 누출 (ADR-003 invariant)                       | P1 신뢰           |
| S3   | `stage/fix-stress-config`           | P1-7 WF backtest_config 미전달 + P1-4 boilerplate                            | P1 정확성         |
| S4   | `stage/fix-optimizer-genetic`       | P1-9 CategoricalField 크래시                                                 | P1 크래시         |
| S5   | `stage/fix-trading-kill-switch`     | P1-2 webhook realized_pnl + P1-12 market notional + P1-14 canceled reconcile | P1 money 방어심층 |
| S6   | `stage/fix-trading-coverage`        | P1-3 parse_tv_payload error 테스트 (BL-309)                                  | P1 커버리지       |
| S7   | `stage/fix-frontend-trading-ux`     | P1-1/11 계정등록 에러 UX + P1-8 optimizer picker                             | P1 UX             |
| S8+  | `stage/fix-p2-*` / `stage/fix-p3-*` | P2 58 + P3 76 도메인별 배치                                                  | P2/P3             |
| —    | (의사결정 매트릭스)                 | G1/G7/G8 + BL-070/072                                                        | 사용자            |

> P0=0 이므로 S1~S7(P1 7테마)이 최우선. 각 테마 머지는 사용자 승인(DEC-12). P2/P3 는 BL 등재 후 도메인별 배치 — 전량 ledger 추적(silent drop 0).

### Fix-and-Merge Ledger

> 베이스라인: BE 1850 PASS / FE 716 PASS @ main `4aa5c2a`. 상태: TODO→BRANCHED→RED→GREEN→LOCAL-GREEN→PUSH-APPROVED→MERGED | USER-DECIDE.

| 테마     | 핵심 발견                                         | 상태                             | 브랜치                        | 비고                                                                                                                                                                                                    |
| -------- | ------------------------------------------------- | -------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1       | P1-5 avg_holding_hours 1440x/288x/96x             | **LOCAL-GREEN** (push 승인 대기) | `stage/fix-backtest-metric`   | v2_adapter + metrics 'min' alias 추가, TDD RED→GREEN 확인 (+3 test)                                                                                                                                     |
| S2       | P1-10/13 Trust Layer 누출 (28 symbols)            | **LOCAL-GREEN** (push 승인 대기) | `stage/fix-trust-layer-leak`  | DEC-15=A 전부 구현. 망라 parity 테스트가 audit 10 + 미발견 18(currency 12/commission 3/math.log10/barstate) = 28 검출. TDD RED 28→GREEN, pine_v2 611 pass 회귀 0. BL-361 Resolved + live-obs BL-362(S5) |
| S3       | P1-7 WF backtest_config 미전달                    | **LOCAL-GREEN** (push 승인 대기) | `stage/fix-stress-config`     | WF 에 build_engine_config_from_db 추가(CA/PS 미러). spy 회귀 2건 RED→GREEN, stress_test 91 pass. boilerplate(P1-9)=BL-363 P2 deepening                                                                  |
| S4       | P1-9 Genetic+Bayesian CategoricalField 크래시     | **LOCAL-GREEN** (push 승인 대기) | `stage/fix-optimizer-genetic` | Option A: 비숫자 categorical reject(genetic+bayesian validation). 크래시→명확한 422. TDD RED 2→GREEN, optimizer 149 pass. string-label sweep=BL-364                                                     |
| S5       | P1-2/12/14 trading kill-switch/notional/reconcile | TODO                             | —                             | money path — 신중                                                                                                                                                                                       |
| S6       | P1-3 parse_tv_payload error 테스트                | TODO                             | —                             | BL-309                                                                                                                                                                                                  |
| S7       | P1-1/11/8 frontend 계정등록 UX + optimizer picker | TODO                             | —                             | 라이브 QA 병행                                                                                                                                                                                          |
| S8+      | P2 58 + P3 76                                     | TODO                             | —                             | 도메인별 배치                                                                                                                                                                                           |
| 매트릭스 | G1/G7/G8 + BL-070/072                             | USER-DECIDE                      | —                             | 코드 불가                                                                                                                                                                                               |

## 10. 결론

- **Beta-ready 재확인:** P0=0. #305~310 hardening 유효. Composite 7.5 주장 유지 가능.
- **단, 7개 P1 테마가 Beta 전 권장 수정** — 특히 Trust Layer 누출(P1-10/13, 잘못된 결과를 정답처럼 노출)과 백테스트 지표 회귀(P1-5)는 제품 신뢰 직결.
- **배포는 여전히 G1/G7/G8 차단** — 코드 아닌 사용자/인프라 결정. `/healthz` 행 실측으로 G7 재확인.
- **거버넌스 drift:** TODO.md 를 #305~310 + 본 정검 반영해 갱신 필요(별도 docs PR).

---

_(아래는 평가자 패널 원시 발견 — refuter 검증 생존분 전량.)_

---

### 발견 요약 (검증 생존 = refuter real/contested)

| 도메인           | P0    | P1     | P2     | P3     | 계      |
| ---------------- | ----- | ------ | ------ | ------ | ------- |
| auth             | 0     | 0      | 2      | 5      | 7       |
| backtest         | 0     | 1      | 0      | 0      | 1       |
| cross            | 0     | 0      | 4      | 3      | 7       |
| deploy           | 0     | 1      | 6      | 4      | 11      |
| frontend         | 0     | 3      | 6      | 9      | 18      |
| market_data      | 0     | 0      | 7      | 4      | 11      |
| optimizer        | 0     | 1      | 12     | 11     | 24      |
| optimizer+stress | 0     | 0      | 1      | 3      | 4       |
| strategy         | 0     | 2      | 1      | 0      | 3       |
| stress_test      | 0     | 2      | 3      | 9      | 14      |
| tasks            | 0     | 0      | 3      | 10     | 13      |
| trading          | 0     | 4      | 13     | 18     | 35      |
| **계**           | **0** | **14** | **58** | **76** | **148** |

> 총 auditor 발견 169 → refuter 검증 후 생존 148 / 기각 21. (P0 = 0 — #305~310 hardening 효과.)

### P1 발견 상세 (14건) — Beta 차단급

**P1-1 · backtest/D4** — `backend/src/backtest/config_mapper.py:24-31 (_TIMEFRAME_TO_FREQ) vs backend/src/backtest/engine/v2_adapter.py:446-459 (_FREQ_HOURS_V2)`

- 주장: 24-metric 정확성 회귀 (avg*holding_hours): production v2 경로에서 1m/5m/15m timeframe 의 avg_holding_hours 가 1440x/288x/96x 과대 계산. timeframe_to_freq() 가 '1m'->'1min', '5m'->'5min', '15m'->'15min' 로 매핑하는데, \_v2_avg_holding_hours() 가 호출하는 \_freq_to_hours_v2() 의 dict \_FREQ_HOURS_V2 는 키가 '1m'/'5m'/'15m' (NOT '1min'/'5min'/'15min') 라서 매핑 미스 → 24.0h fallback 사용. 즉 1m 에서 보유 bar 수 * (1/60)h 가 되어야 하는데 bar 수 \_ 24h 로 계산
- 수정: \_FREQ_HOURS_V2 에 '1min'/'5min'/'15min'(+'30min') 키 추가하거나, \_TIMEFRAME_TO_FREQ 가 \_FREQ_HOURS_V2 키 체계('1m'/'5m'/'15m')와 동일 alias 를 쓰도록 통일. 단 pandas resample('ME')/pct_change 등은 '1min' 같은 pandas offset alias 가 필요할 수 있으므로 두 매핑(pandas offset vs h
- 검증: votes=2 / ['real'] · BL: 신규

**P1-2 · deploy/D7 [코드수정불가→의사결정]** — `backend/docker-entrypoint.sh:65-117`

- 주장: The entrypoint role dispatch has NO `ws-stream` deploy parity problem for Cloud Run AND the worker/beat/ws-stream/optimizer-heavy roles produce containers with NO HTTP listener. Cloud Run service contract requires the container to listen on $PORT within the startup timeout, otherwise the revision is marked failed. The worker (L80), ws-stream (L88), optimizer-heavy (L97), and beat (L106) cases all
- 수정: Add a minimal sidecar HTTP listener (or a thin http.server thread) to non-api roles so Cloud Run port contract is satisfied, OR host worker/beat/ws-stream on Compute Engine VM / a platform that does not require an HTTP listener (per runbook
- 검증: votes=2 / ['real'] · BL: cloud-run-runbook G8 (P0 blocker, unresolved)

**P1-3 · frontend/D8** — `src/features/trading/components/register-exchange-account-dialog.tsx:53-60 (onSubmit) + hooks.ts:232-249 (useRegisterExchangeAccount)`

- 주장: 거래소 계정 등록(고위험: API Key/Secret 입력) 제출이 `await register.mutateAsync(...)` 를 try/catch 없이 호출하고, useRegisterExchangeAccount 뮤테이션에는 onError 가 없다(onSuccess 만 존재). 등록 실패(잘못된 키/네트워크/422) 시 promise rejection 이 unhandled 로 끝나 사용자에게 어떤 피드백도 표시되지 않고 다이얼로그도 닫히지 않는다(성공 경로에서만 setOpen(false)). 사용자는 실패를 인지하지 못함.
- 수정: onSubmit 에 try/catch + form.setError('root') 또는 useRegisterExchangeAccount 에 onError: (e)=>toast.error(...) 추가. test-order-dialog 의 root.serverError 패턴 재사용.
- 검증: votes=2 / ['real'] · BL: 신규(trading 계정 등록 error UX)

**P1-4 · frontend/D8** — `src/app/(dashboard)/optimizer/page.tsx:36-42, 65-82`

- 주장: Optimizer 진입 동작이 raw `backtest_id (COMPLETED)` UUID 를 텍스트 input 에 직접 paste 하도록 요구한다(placeholder='backtest_id (COMPLETED)'). 도메인 전체(optimizer/\_components)에 backtest 선택 picker/select 가 존재하지 않음(grep useBacktests/Select.\*backtest = 0건). 일반 사용자는 COMPLETED backtest 의 UUID 를 알 길이 없어 페이지에서 진행 불가능한 dead-end. /optimizer 는 사이드바 노출 페이지.
- 수정: useBacktests({status:'completed'}) 기반 Select(label=strategy명+심볼+기간, value=id) 로 교체. SelectWithDisplayName 패턴(live-session-form 이 이미 사용) 재사용해 raw UUID 노출도 동시 차단.
- 검증: votes=2 / ['real'] · BL: BL-350/354 계열(optimizer Surface/UX)

**P1-5 · frontend/D4** — `/Users/woosung/project/agy-project/quant-bridge/frontend/src/features/trading/components/register-exchange-account-dialog.tsx:53-60 (onSubmit), 55-62 schema in schemas.ts`

- 주장: OKX 계정 등록 시 passphrase 누락이 클라이언트에서 검증되지 않고, 서버 422 에러가 화면에 표시되지 않는다. schemas.ts:61 `passphrase: z.string().nullable()` 는 OKX 일 때 passphrase 를 요구하지 않는데, 백엔드(backend/src/trading/schemas.py:25-27 `_require_passphrase_for_okx`)는 OKX+passphrase 없음을 `ValueError('OKX accounts require a passphrase')` → 422 로 거부한다. 또한 onSubmit(line 53-60)은 `await register.mutateAsync(...)` 를 try/catch 없이 호출하고 dialog 에 serv
- 수정: (1) RegisterAccountRequestSchema 에 superRefine 추가: exchange==='okx' && !passphrase → addIssue(path:['passphrase']). (2) onSubmit 을 try/catch 로 감싸 register error 를 inline alert(예: serverError state 또는 form.setError('root.serverError'))로 표시.
- 검증: votes=2 / ['real'] · BL: BL-309 (registry/webhook/fees 미커버 영역) 또는 trading form 신규

**P1-6 · optimizer/D4** — `backend/src/optimizer/engine/genetic.py:187-188, 318`

- 주장: CategoricalField for Genetic crashes with InvalidOperation when category values are non-numeric strings. \_validate_genetic_search_pre requires input.string for CategoricalField (line 164), and CategoricalField.values is typed list[str] (schemas.py:88) intended for string labels like ['ema','sma']. But \_sample_individual does out[var_name]=Decimal(str(rng.choice(field.values))) (line 188) and \_gaus
- 수정: Either reject non-numeric CategoricalField values in \_validate_genetic_search_pre, or change the individual representation to carry str|Decimal for categorical dims instead of forcing Decimal. The current dict[str,Decimal] contract is incom
- 검증: votes=2 / ['real'] · BL: BL-234

**P1-7 · strategy/D4** — `backend/src/strategy/pine_v2/coverage.py:124-133 (_STRING_FUNCTIONS) vs interpreter.py:783 / 855-923 (_NOP_NAMES) / 929`

- 주장: Same Trust Layer leak class for string functions: coverage.\_STRING_FUNCTIONS marks `str.tostring`, `str.tonumber`, `str.format`, `str.length`, and bare `tonumber` as SUPPORTED (folded into SUPPORTED_FUNCTIONS at coverage.py:294-307), but the interpreter only handles bare `tostring` (interpreter.py:783). For `str.tostring(x)` the call has a dot, so \_eval_call reaches the handle.method dispatch (int
- 수정: Add `str.tostring`, `str.tonumber`, `str.format`, `str.length`, `tonumber` to interpreter \_NOP_NAMES (returning a stub str/None like the existing bare `tostring` branch), or give them explicit branches mirroring the `tostring` handler at in
- 검증: votes=2 / ['real'] · BL: none (new BL warranted)

**P1-8 · strategy/D4** — `backend/src/strategy/pine_v2/coverage.py:310-330 (_SERIES_ATTRS) vs interpreter.py:195 (_BUILTIN_SERIES) / 1030-1099 (_eval_attribute)`

- 주장: Trust Layer leak / partial-execution-invariant defeat: coverage.\_SERIES_ATTRS marks `hl2`, `hlc3`, `ohlc4`, `barstate.isfirst`, `barstate.islast`, `barstate.ishistory`, `barstate.isconfirmed` as SUPPORTED, so analyze_coverage().is_runnable==True for a strategy whose only exotic reference is one of these. But the interpreter never handles them: `hl2`/`hlc3`/`ohlc4` are bare Names that fall through
- 수정: Either (a) implement hl2=(high+low)/2, hlc3=(high+low+close)/3, ohlc4=(open+high+low+close)/4 in \_resolve_name and barstate.isfirst=(bar_index==0)/islast=(bar_index==len-1)/ishistory=True/isconfirmed=True in \_eval_attribute; OR (b) remove t
- 검증: votes=1 / ['real'] · BL: BL-242b (barstate/timeframe series attrs) — likely incomplete; new BL warranted for hl2/hlc3/ohlc4 + barstate confirmation states

**P1-9 · stress_test/D2** — `backend/src/stress_test/service.py:279-322, 324-386`

- 주장: 4 engine 의 worker entry (_execute_\*) 가 동일 boilerplate(strategy 소유 검증 → ohlcv 로드 → param 파싱 → 엔진 호출 → to_jsonb) 를 반복하지만 추상화 없이 4개 메서드로 복붙되어 있다. WF/CA/PS 3개는 거의 동일한 strategy.find_by_id_and_owner + provider.get_ohlcv(symbol/timeframe/period) 전처리를 갖는다(line 298-306 vs 333-343 vs 366-374). 이 중복이 stress-D2-arch-1(WF config 누락) 같은 drift 의 직접 원인 — CA/PS 에는 build_engine_config_from_db 추가했지만 동일 구조의 WF 에는 누락.
- 수정: 공통 전처리(_load_strategy_and_ohlcv(bt) → (pine_source, ohlcv, config)) helper 추출 → 각 \_execute_\* 가 엔진 호출+직렬화만 담당. config 빌드를 helper 에 넣으면 WF 누락도 구조적으로 차단.
- 검증: votes=2 / ['real'] · BL: BL-222 / 신규 stress deepen BL

**P1-10 · stress_test/D2** — `backend/src/stress_test/service.py:295-322`

- 주장: \_execute_walk_forward 가 run_walk_forward 를 호출하면서 backtest_config 를 전달하지 않는다. 엔진(walk_forward.py:137)은 `cfg = backtest_config or BacktestConfig()` 로 fallback 하므로, WF 의 IS/OOS 백테스트가 부모 backtest 의 fees/slippage/init_cash/leverage/sizing 5필드/trading_sessions 를 전부 무시하고 엔진 기본값(fees=?, slippage=?, init_cash=default)으로 실행된다. Sprint 52 BL-222 P1 이 CA(line 348)와 PS(line 379)에는 build_engine_config_from_db(bt
- 수정: \_execute_walk_forward 에 `backtest_config = build_engine_config_from_db(bt)` 추가 후 run_walk_forward(..., backtest_config=backtest_config) 로 전달. CA/PS 와 동일 패턴. 회귀 방지로 부모 config 보존 검증 테스트 추가.
- 검증: votes=2 / ['real'] · BL: BL-222 (follow-up — Sprint 52 fix 의 WF 누락분)

**P1-11 · trading/D3** — `backend/src/trading/router.py:107-115`

- 주장: #305 kill-switch revival (realized_pnl 기록 → CumulativeLoss/DailyLoss evaluator 가 SUM 으로 손실 차단) 이 webhook 주문 진입 경로에서는 죽어있다. receive_webhook 가 OrderRequest 를 조립할 때 realized_pnl(그리고 leverage/margin_mode)을 채우지 않는다. realized_pnl 은 live_signal 경로(tasks/live_signal.py:676, pine_v2 engine 의 close-signal 계산)에서만 Order 에 기록된다(grep 확인: src/trading/websocket/\* + tasks/trading.py 어디에도 realized_pnl write 없음). 따라
- 수정: parse_tv_payload(webhook.py:70) 또는 receive_webhook 에서 TV payload 의 close/realized 필드를 OrderRequest.realized_pnl 로 매핑하거나, webhook close 주문에 대해 별도 realized_pnl 산출 경로(WS reconciler 가 fill 시 진입가 대비 청산 PnL 계산)를 두어 kill-switch SUM 대상이 비지 않도록 한다.
- 검증: votes=2 / ['real'] · BL: BL-309 (registry/webhook/fees coverage)

**P1-12 · trading/D5** — `backend/src/trading/webhook.py:70-81`

- 주장: parse_tv_payload() 는 외부 신뢰 불가 TradingView payload 를 OrderRequest 로 변환하는 LLM/외부 trust boundary 인데 테스트가 happy-path 1건(test_parse_tv_payload_extracts_order_fields)뿐이다. error 경로 — symbol/side/quantity 누락(KeyError), 잘못된 side/type enum 값(ValueError), 비숫자 quantity/price(Decimal InvalidOperation→ValueError/TypeError) → WebhookUnauthorized raise — 가 전혀 테스트되지 않는다. grep 결과 tests/ 전체에서 parse_tv_payload 사용은 단
- 수정: test_webhook_hmac.py(또는 신규 test_parse_tv_payload.py)에 parametrized error 케이스 추가 — 필수필드 누락/invalid side/invalid type/비숫자 quantity/잘못된 price 각각 `pytest.raises(WebhookUnauthorized)` + price 미존재 시 None 분기 + price='0'(falsy) 분기까지.
- 검증: votes=1 / ['real'] · BL: BL-309

**P1-13 · trading/D3** — `backend/src/trading/services/order_service.py:158-192`

- 주장: notional/balance 가드(CF5/MP-3)는 req.price is not None 일 때만 enforce 한다(line 161). market order(price=None)는 notional 검증을 완전히 건너뛰고 leverage cap 만 1차 방어로 남는다(line 154-157 주석에 명시). live_signal 경로는 모든 주문이 OrderType.market + price=None(tasks/live_signal.py:670,673)이므로 자동매매로 들어오는 주문은 notional 가드가 항상 무력화된다. 즉 자본 대비 과도한 포지션을 진입가 불확실성만으로 통과시킬 수 있어, #305/CF5 의 notional 보호가 라이브 시그널 경로에서는 실효성이 거의 없다.
- 수정: market order 의 경우 fetch_ohlcv 마지막 종가 또는 fetch_ticker mark price 를 notional 추정가로 사용해 근사 notional 가드 적용(보수적 버퍼 추가). 또는 live_signal dispatch 에서 position_size_pct 기반 사전 qty 상한을 잔고로 환산해 강제.
- 검증: votes=2 / ['real'] · BL: 신규

**P1-14 · trading/D7** — `backend/src/trading/websocket/reconcile_fetcher.py:88-104, 7, 91`

- 주장: fetch_recent_orders 의 docstring(line 7, 91)은 'closed + canceled' 를 가져온다고 명시하지만 실제로는 exchange.fetch_closed_orders 만 호출(line 101). Bybit V5/CCXT 에서 사용자/시스템이 취소한 주문은 fetch_closed_orders 가 반환하지 않고 fetch_canceled_orders 로 별도 조회해야 한다(거래소별 상이). 결과: Reconciler.run 에서 거래소가 cancel 한 local active order 가 exch_open 에도 없고 exch_recent(closed only)에도 없음 → \_find_match 실패 → \_handle_unknown 으로 빠져 state 유지 + reconci
- 수정: fetch_recent_orders 에서 fetch_closed_orders + fetch_canceled_orders 둘 다 호출해 union 반환(CCXT has['fetchCanceledOrders'] 가드). 또는 Bybit V5 fetchOrders(openOnly=0) 단일 호출로 전체 history. 미지원 시 docstring 을 closed-only 로 정정하고 cancelled 미탐지 한계 명시.
- 검증: votes=2 / ['real'] · BL: BL-308

### P2 발견 (58건) — 도메인별

**auth** (2)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/waitlist/dependencies.py:32-36`[:60] | get_email_service 가 settings.resend_api_key 빈 값일 때 'dev-empty-key' placeholder 를 주입(dependencies.py:36). Email | - |
| 2 | `backend/src/auth/service.py:90-91`[:60] | Geo-block(US/EU/UK 규제 차단) 우회 2 경로. (1) handle_clerk_event 는 event_type=='user.created' 일 때만 RESTRICTED_COUNTRI | - |

**cross** (4)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/health/router.py:48`[:60] | HEALTHZ_CELERY_TIMEOUT_S is read via os.environ.get('HEALTHZ_CELERY_TIMEOUT_S', '12.0') (bypassing the Setting | (new — golden-rule env violation) |
| 2 | `docs/TODO.md:3-8`[:60] | TODO.md header is stale by 8 merged PRs. Declares 'Last Updated: 2026-05-17', 'Active Branch: main (PR #288 + | (new — governance drift, no existing BL) |
| 3 | `docs/REFACTORING-BACKLOG.md:107, 211-231`[:60] | BL-308 is listed as active P1 with '현 상태: ...3 file... 안 test 2/48 file 만 reference = ~4% 추정 coverage' (L220). | BL-308 |
| 4 | `docs/REFACTORING-BACKLOG.md:8-9`[:60] | REFACTORING-BACKLOG.md header is stale: '최종 갱신: 2026-05-17', 'main @ 36bb4e0', '45 active BL'. HEAD is now 4aa | (new — governance drift) |

**deploy** (6)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/core/config.py:42, 273, 298-347`[:60] | #308 prod validator does NOT guard DATABASE_URL or FRONTEND_URL, both of which default to localhost. `database | - |
| 2 | `backend/src/health/router.py:157`[:60] | /healthz readiness probe HARD-requires celery_workers >= 1 to return 200 (`healthy = pg_status == 'ok' and red | BL-310 (healthz/livez split, partial) + cloud-run-runbook G7 |
| 3 | `backend/src/core/config.py:298-347`[:60] | #308 prod secret validator only blocks EMPTY clerk_secret_key, not dev-tier test keys. `_enforce_production_sa | - |
| 4 | `backend/Dockerfile:64-69`[:60] | No HEALTHCHECK instruction in Dockerfile, and worker/beat/ws-stream/optimizer-heavy roles run celery with no H | - |
| 5 | `backend/docker-entrypoint.sh:65-72, 113-116`[:60] | #308 DATABASE_URL fail-fast guard is ALIVE but has a coverage hole: it only fires when ROLE ($1) is one of api | - |
| 6 | `backend/docker-entrypoint.sh:63-72`[:60] | The DATABASE_URL fail-fast guard only triggers for the exact tokens `api|worker|beat|ws-stream|optimizer-heavy | cloud-run-runbook G9 (ws-stream role) related |

**frontend** (6)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `src/app/(dashboard)/optimizer/_components/grid-search-form.tsx, bayesian-search-form.tsx, genetic-search-form.tsx:grid:109,213-216 · bayesian:130,265-272 · genetic:170,331-338`[:60] | 세 optimizer 제출 form 모두 submit 실패 시 `setErrMsg(e instanceof Error ? e.message : String(e))` 로 raw error 를 그대로 r | BL-350/354 (optimizer Zod error 도배 ★★★ 공통, form 잔존분) |
| 2 | `src/app/(dashboard)/optimizer/_components/grid-search-form.tsx, bayesian-search-form.tsx, genetic-search-form.tsx:grid:184-191 · bayesian:236-243 · genetic:302-309 (remove ✕ 버튼)`[:60] | 파라미터 row 제거 '✕' 버튼이 `px-2 py-1 text-xs` 로 약 24px 높이 — 모바일 터치 타깃 44pt 미달. exchange-accounts-panel 의 삭제 버튼은 size | BL-356~359 (touch ≥44pt 계열) |
| 3 | `src/features/trading/components/exchange-accounts-panel.tsx:121-129 (deleteAccount.mutate) + hooks.ts:251-263 (useDeleteExchangeAccount)`[:60] | 거래소 계정 삭제 버튼이 `deleteAccount.mutate(a.id)` 를 onError 없이 호출한다(뮤테이션도 onSuccess 만). 삭제 실패 시 사용자에게 아무 피드백 없음 — 행 그 | 신규(trading 계정 삭제 error UX) |
| 4 | `src/app/(dashboard)/optimizer/page.tsx, grid-search-form.tsx, bayesian-search-form.tsx, genetic-search-form.tsx:page:29-31,37,52-54 · grid:117,138,157 · bayesian:172,205 · genetic:177,275`[:60] | Optimizer 페이지/폼 전체가 내부 API 계약 용어를 사용자에게 그대로 노출한다: 'backtest_id (COMPLETED)', 'var_name (pine input)', 'objecti | BL-350/354 / 내부용어 노출 ★★★ 공통(BL-265/280/303 계열) |
| 5 | `src/app/(dashboard)/optimizer/_components/optimizer-run-detail.tsx:16-22`[:60] | Run detail 의 query error 분기가 '상세 로드 실패: {error.message}' 로 raw error.message 를 노출한다. useOptimizationRun 은 getO | BL-350/354 계열(optimizer Surface Trust 잔존) |
| 6 | `src/features/live-sessions/components/live-session-detail.tsx:41-50, 93`[:60] | `timelineData` is built inline on every render via buildActivityTimeline()/buildActivityTimelineWithEquity() w | BL-308 (live-sessions/websocket coverage area) |

**market_data** (7)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/market_data/providers/ccxt.py:155-172`[:60] | pagination 루프가 매 page 마다 hardcoded `await asyncio.sleep(0.1)` 를 무조건 호출(enableRateLimit=True 와 중복) + page 를 순차 | BL-309 |
| 2 | `backend/src/market_data/repository.py:23-42`[:60] | get_range 가 [period_start, period_end] 전 구간을 `result.scalars().all()` 로 Python list 전량 적재, 이어 timescale.\_to_da | BL-309 |
| 3 | `backend/src/market_data/providers/timescale.py:58-67 (gap fetch loop) + repository.py:44-51 (insert_bulk ON CONFLICT DO NOTHING)`[:60] | 거래소에 실제로 데이터가 없는 timestamp (상장 이전 구간, 거래소 다운타임, 미래/현재 진행 bar, 또는 fetch 가 빈 list 반환) 에 대해 negative-cache 가 전혀 없 | BL-309 |
| 4 | `backend/src/backtest/schemas.py:94-98`[:60] | 백테스트 OHLCV 범위에 상한 cap 이 전혀 없다. `_validate_period` 는 `period_end > period_start` 만 검증 — 최대 일수/최대 bar 수 제한 없음. o | BL-309 |
| 5 | `backend/src/market_data/repository.py:30-42 (get_range time <= period_end 양끝 포함)`[:60] | get_range 는 [period_start, period_end] 양끝 포함 (>= start AND <= end). find_gaps 의 generate_series(:start,:end,.. | BL-309 |
| 6 | `backend/src/market_data/repository.py:65-99 (find_gaps generate_series) + caller backend/src/tasks/market_data_backfill.py:99-101 + backend/src/market_data/providers/timescale.py:54-56`[:60] | find_gaps 의 generate_series(:start, :end, interval) 는 caller 가 넘긴 raw period_start 를 grid 기점으로 삼는다. 하지만 DB 에 저 | BL-309 (registry/fees/webhook 0% coverage 인접 — market_data gap coverage) |
| 7 | `backend/src/market_data/providers/timescale.py:78-92 (_to_db_rows open/high/low/close/volume = b[1..5])`[:60] | docstring 은 'Decimal 변환' 이라 주장하지만 실제로는 CCXT 가 준 Python float (b[1]..b[5]) 를 Numeric(18,8) 컬럼에 그대로 바인딩한다. Decim | MP-4 (Decimal→float CCXT 경계 hardening) 의 미적용 잔여 경계 — OHLCV ingest |

**optimizer** (12)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/optimizer/service.py:239-307`[:60] | _execute_grid_search / \_execute_bayesian / \_execute_genetic 3개 메서드가 strategy 로드(find_by_id_and_owner+None시 Opt | 신규 BL (arch-3 동반) |
| 2 | `backend/src/optimizer/service.py:204-211, 86-132`[:60] | Dispatcher kind 분기가 if-elif 체인으로 2곳에 분산 — (1) service.run() 204-209 의 worker-side kind→_execute\_\_ 분기, (2) subm | 신규 BL |
| 3 | `backend/tests/optimizer/test_grid_search_engine.py:165-183`[:60] | Grid Search engine 의 run*grid_search() end-to-end success path 가 전혀 테스트되지 않음. 유일한 run_grid_search 호출은 line 179 | BL-309 (test coverage gap) |
| 4 | `backend/tests/optimizer/test_bayesian_engine.py:348-366 (대상 src/optimizer/engine/bayesian.py)`[:60] | Bayesian executor 의 입력 검증 분기 5개 중 4개가 미테스트. bayesian.py:341 schema_version!=2 reject, :348 bayesian_n_initial* | BL-309 |
| 5 | `backend/src/optimizer/engine/bayesian.py:241-255`[:60] | *coerce_skopt_to_decimal 가 CategoricalField string 값에 Decimal(str(v)) 적용(253-254) — CategoricalField.values 는 | 신규 BL |
| 6 | `backend/tests/optimizer/test_genetic_engine.py + test_bayesian_engine.py:전체 (대상 genetic.py:127-168, bayesian.py:196-238)`[:60] | 3 engine 공통의 pre-validation(\_validate*_\_search_pre) reject 경로 — 미지원 pine built-in(coverage.is_runnable=False), | BL-309 |
| 7 | `backend/src/optimizer/engine/grid_search.py:96-103, 86-93, 251 (호출 순서)`[:60] | \_expand_decimal_field / \_expand_integer_field 가 (min, max, step) 전 범위를 list[Decimal] 로 eager materialize 한다. 이 | none |
| 8 | `backend/tests/optimizer/test_genetic_engine.py:237-263 (대상 genetic.py:284-323)`[:60] | Genetic \_gaussian_mutation 의 CategoricalField 분기와 degenerate-span IntegerField 분기가 미테스트. TestGaussianMutation( | BL-309 |
| 9 | `backend/src/optimizer/engine/grid_search.py + bayesian.py + genetic.py:grid_search.py:265, bayesian.py:275-278, genetic.py:331-334`[:60] | Dead degeneracy branch — 3개 엔진 모두 'metrics.sharpe_ratio is None' 을 degenerate 판정에 사용하나, SSOT 엔진 v2_adapter.\_sh | 신규 BL |
| 10 | `backend/tests/optimizer/test_bayesian_engine.py:374-377 (대상 src/optimizer/engine/bayesian.py)`[:60] | Bayesian acquisition UCB → LCB 부호 변환(bayesian.py:374-377: skopt_acq = 'LCB' if bayesian_acquisition=='UCB' els | BL-309 |
| 11 | `backend/src/optimizer/engine/bayesian.py:179-184, 233-238, 253-254`[:60] | Bayesian CategoricalField with non-numeric string values produces a Decimal coercion crash, and the encoding=' | BL-234 |
| 12 | `backend/src/optimizer/engine/bayesian.py:396-444 (loop); genetic.py:508-554; grid_search.py:255-284`[:60] | 전 엔진(Grid/Bayesian/Genetic)이 매 cell/iteration 마다 run_backtest(pine_source, ...) 를 새로 호출하고, run_backtest → pars | BL-237 |

**optimizer+stress** (1)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/tasks/stress_test_tasks.py:21`[:60] | stress_test.run Celery task has NO soft_time_limit/time_limit, while optimizer.run has soft_time_limit=600/tim | BL-237 |

**strategy** (1)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/strategy/pine_v2/event_loop.py:111-148 (run_historical) / 219 + tasks/live_signal.py:333 (run_live path)`[:60] | Observability gap that turns the two SUPPORTED-vs-runtime divergences above into SILENT money-path failures ra | none (new BL warranted) |

**stress_test** (3)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/stress_test/service.py:246-258, 445-464`[:60] | StressTestKind → handler 디스패치가 동일 도메인 안에서 2곳에 중복된 if-elif 체인으로 흩어져 있다. run() (line 247-258: MONTE*CARLO/WALK_F | BL-203/204 (trading dispatcher deepen) 와 동류 — stress 용 신규 BL 후보 |
| 2 | `backend/tests/stress_test/:test_worker_monte_carlo_happy_path.py / test_worker_walk_forward_happy_path.py (CA·PS 부재)`[:60] | Worker run-path(StressTestService.run → \_execute*\*)에 대한 DB-레벨 happy-path 테스트가 MONTE_CARLO 와 WALK_FORWARD 에는 존재 | BL-223 |
| 3 | `backend/tests/stress_test/engine/test_cost_assumption_sensitivity.py:121-134`[:60] | Cost Assumption Sensitivity 의 핵심 가치(=비용 가정 sweep)를 검증하는 테스트가 0건. 모든 CA 엔진 테스트는 SHAPE(9 cell 개수, key 검증, degene | BL-223 |

**tasks** (3)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/tasks/trading.py:246-319`[:60] | execute_order_task 는 max_retries=0 이지만 celery_app.py:64-65 의 전역 task_acks_late=True + task_reject_on_worker_lo | BL-308 인접(trading 신뢰성 test) |
| 2 | `backend/src/tasks/_ws_lease.py:37 (_DEFAULT_TTL_MS=60000) + websocket_task.py:338`[:60] | On a hard worker death (SIGKILL / OOM / power loss) the heartbeat loop and WsLease.**aexit** never run, so the | BL-308 |
| 3 | `backend/src/tasks/stress_test_tasks.py:21-29`[:60] | run_stress_test_task 에 soft_time_limit / time_limit 가 전혀 없다. optimizer_tasks.run_optimization_task 는 BL-237 으로 | 신규(BL-237 mirror 권고) |

**trading** (13)
| # | 위치 | 주장 (요약) | BL |
|---|------|-------------|----|
| 1 | `backend/src/trading/webhook.py:54-61`[:60] | WebhookService.verify() 의 두 미검증 경로: (1) decrypt 실패 — candidate 의 secret*encrypted 가 손상/다른 Fernet 키로 암호화된 경우 se | BL-309 |
| 2 | `backend/src/trading/websocket/state_handler.py:102-105, 39-44`[:60] | PartiallyFilled 은 WS handler(\_BYBIT_TERMINAL_MAP 미포함, line 102-104)와 Reconciler(\_STATUS_MAP 미포함) 양쪽에서 MVP skip | BL-309 |
| 3 | `backend/src/trading/websocket/reconcile_fetcher.py:88-104`[:60] | fetch_recent_orders 가 fetch_closed_orders(limit=50) 단일 페이지만 조회. 페이지네이션/since 파라미터 없음. 장시간 disconnect(예: 워커 재시작 | BL-308 |
| 4 | `backend/src/trading/websocket/bybit_private_stream.py:218, 224, 270`[:60] | \_supervisor_loop 의 reconnect backoff(line 218 backoff=1.0)가 connect 성공(line 224) 후 1.0 으로 reset 되지 않는다. line 2 | BL-308 |
| 5 | `backend/src/trading/webhook.py:78`[:60] | parse_tv_payload 의 price 추출이 truthiness 검사(`if payload.get("price")`)를 사용한다. TradingView alert 가 `price` 를 숫자 | BL-309 |
| 6 | `backend/src/trading/services/account_service.py:88-105, 49-73`[:60] | fetch_balance_usdt 가 동기 HTTP 주문 생성 critical path 에서 CCXT `fetch_balance` 실 네트워크 호출(~200ms, docstring 자인)을 트리거한 | BL-309 |
| 7 | `backend/src/trading/services/order_service.py:158`[:60] | notional 게이트가 market order(price=None)를 완전히 건너뛴다(`req.price is not None` 조건). 주석은 'leverage cap 으로만 1차 방어'라 하지 | BL-309 |
| 8 | `backend/src/trading/services/order_service.py:109, 137, 163`[:60] | 단일 order-creation 요청에서 동일 ExchangeAccount row 를 분리된 SELECT 로 최대 4회 중복 조회한다 (N+1 형태). (1) ownership gate `self. | BL-309 |
| 9 | `backend/src/trading/services/order_service.py:85-316`[:60] | OrderService._execute_inner 책임 과다 (shallow-but-wide / God method). 단일 메서드 ~230L 안에 7개의 독립 검증 게이트(TRD-4 ownersh | BL-204 |
| 10 | `backend/src/trading/websocket/state_handler.py:187-197`[:60] | WS Filled event 처리 시 \_apply_transition 의 filled 분기가 payload 의 closedPnl 을 읽지 않고 transition_to_filled(realized* | BL-308 |
| 11 | `backend/src/trading/kill_switch.py:100, 155`[:60] | Repository layer 우회 (Golden Rule 위반: DB 접근은 Repository 만) + 로직 중복. CumulativeLossEvaluator/DailyLossEvaluator | BL-309 |
| 12 | `backend/src/trading/services/order_service.py:108-143`[:60] | 정보 누출 (Ousterhout information leakage) — OrderService 가 협력 service 의 private attribute 를 뚫고 DB 접근한다. `await se | BL-203 |
| 13 | `backend/src/trading/websocket/bybit_private_stream.py:173-196, 182`[:60] | \_receive_loop 는 msg.get('topic') != 'order' 인 메시지를 전부 무시(line 182). Bybit V5 private WS 의 pong(op=pong) 및 subs | BL-308 |

### P3 발견 (76건) — 압축 (polish/convention/maintainability)

- **auth** (5): service.py:90-91; dependencies.py:52-63; service.py:84-93; dependencies.py:27-29; dependencies.py:45-50
- **cross** (3): docker-entrypoint.sh:91-101; .env.example:1-15, 37-38; .env.example:(whole file — CF3 vars absent)
- **deploy** (4): router.py:65-69; main.py:200-202; config.py:139-142, 298-347; docker-entrypoint.sh:16-29, 88-105
- **frontend** (9): equity-chart.tsx:1-92 (whole file); step-3-backtest.tsx:63-83; bayesian-search-form.tsx, genetic-search-form.tsx, grid-search-form.tsx:bayesian:203-227 · genetic:274-295 · grid:156-183 (parameter row inputs/selects); editor-view.tsx:75-82; kill-switch-panel.tsx:58-60; draft.ts:175-180 (useAutoSaveDraft debounce effect); hooks.ts:147-183 (useOrders dep-less toast effect); stress-test-panel.tsx:23,27,185,192 (+ equity-chart-v2.tsx, monaco/pine-editor.tsx); kill-switch-panel.tsx:61-68 (resolve button), hooks.ts:202-219 useResolveKillSwitchEvent
- **market_data** (4): repository.py:65-99; models.py:22 (Index ix_ohlcv_symbol_tf_time_desc) + alembic 20260416_1458:47-52; timescale.py:94-117 (\_to_dataframe float(r.open) 등); repository.py:44-51
- **optimizer** (11): genetic.py:227-259; grid_search.py:266-276; test_bayesian_engine.py + test_genetic_engine.py:340-385 / 484-509; test_grid_search_engine.py:전체; bayesian.py + genetic.py:bayesian.py:62-64, genetic.py:67-69, schemas.py:152; grid_search.py + bayesian.py + genetic.py:grid_search.py:255-276, bayesian.py:258-311, genetic.py:329-389; genetic.py + schemas.py:genetic.py:476-488, schemas.py:148; bayesian.py:80-87, 167-176, 387-400; genetic.py:395-422, 413-419; test_bayesian_engine.py:196-211, 273-283 (대상 bayesian.py:281); grid_search.py:86-103, 167-173
- **optimizer+stress** (3): .env.example:97; optimizer_tasks.py:28; celery_app.py:71
- **stress_test** (9): walk_forward.py:139-145; :test_cost_assumption_sensitivity.py:84-118 / param_stability (부재); monte_carlo.py:35-39 (\_max_drawdown), 38; test_worker_failure_path.py:1-50; cost_assumption_sensitivity.py:78-91 (\_validate via pre_validate) vs grid_sweep.py:75-81; test_cost_assumption_sensitivity.py:50-135 (whole file); engine backend/src/stress_test/engine/cost_assumption_sensitivity.py:137-164; cost_assumption_sensitivity.py:66-75 (\_build_config), specifically 74-75; cost_assumption_sensitivity.py:129-146; cost_assumption_sensitivity.py:132-135
- **tasks** (10): live_signal.py:466-469; live_signal.py:183-204; \_ws_lease.py:187-204; celery_app.py:29-39; celery_app.py:63-68; celery_app.py:182-194; websocket_task.py:336-343; celery_app.py:197-222; websocket_task.py:45-67, 199-200, 290-293; live_signal.py:487-489
- **trading** (18): order_service.py:147; fees.py:54; funding.py:76-93; providers.py:744; fees.py:55; registry.py:8-18; webhook.py:43-61; order_service.py:10-12, 49-63; router.py:243-290; reconcile_fetcher.py:88-104; reconcile_fetcher.py:66-73, 88-97; fees.py:1-7; order_service.py:108; order_service.py:171; reconciliation.py:98-114, 141-153; state_handler.py:133-141, 98; fees.py:54; registry.py:1-64

### Refuted Appendix (21건) — adversarial refuter 가 기각

- ~~market_data/P3~~ `backend/src/market_data/providers/ccxt.py:58, 73`: `asyncio.get_event_loop()` 를 .exchange property(매 \_fetch_page 호출 = 매 page 마다)와 close() 에서 → **기각**: REFUTED — no DeprecationWarning is emitted on the actual code paths, and no per-page no-running-loop context exists.

Code facts (read direc

- ~~optimizer/P3~~ `backend/src/optimizer/engine/bayesian.py:379-385, `: skopt GP base_estimator 의 tell() 은 매 iteration 마다 Gaussian Process 를 누적 관측치 전체로 재적합(refit) → **기각**: 주장의 알고리즘 서술(skopt GP base_estimator 가 tell() 마다 누적 관측치 전체로 GP refit, Cholesky O(m^3))은 정확하다. bayesian.py:381 base_estimator="GP", :444 optim
- ~~deploy/P2~~ `backend/src/tasks/celery_app.py:197-222`: @worker_ready fires the 3-domain stale-RUNNING reclaim (backtest/optimizer/stress) on EVER → **기각**: The factual MECHANISM in the claim is correct, but the severity-bearing RISK (unsafe race over RUNNING rows / actionable defect) is refuted
- ~~trading/P3~~ `backend/src/trading/providers.py:108`: \_to_exchange_precision 가 market BUY 주문의 amount 를 항상 base-currency precision(amount_to_prec → **기각**: 구조적 주장 자체(옵션 분기 없음)는 사실이나, auditor 가 제시한 두 구체 오동작은 둘 다 재현 불가 → REFUTED.

[코드 trace — 확인된 사실]

- backend/src/trading/providers.py:108 `amount
- ~~tasks/P2~~ `backend/src/tasks/live_signal.py:349-360`: \_evaluate_session_inner 의 신규 event 판별이 existing_events = event_repo.list_by_session(sess.i → **기각**: 주장 기각. 1000-cap 이 new_events 오분류를 유발하는 경로가 닫혀 있다.

핵심 반박 = insert_pending_events 반환 범위. backend/src/trading/repositories/live_signal_event_r

- ~~frontend/P2~~ `/Users/woosung/project/agy-project/quant-bridge/fr`: exchange / mode Select 가 `defaultValue={field.value}` (uncontrolled) 로 바인딩됨. onSubmit 성공 후 → **기각**: 주장의 사실 전제(uncontrolled defaultValue 바인딩)는 맞으나, 핵심 추론이 Base UI Dialog 의 mount lifecycle 을 누락하여 사용자 가시 버그가 재현되지 않음. REFUTED.

확인된 사실:

1. regis

- ~~stress_test/P3~~ `backend/src/stress_test/engine/cost_assumption_sen`: \_build_config 가 Decimal fees/slippage 를 BacktestConfig 경계에서 float() 로 캐스팅(line 74-75: `fee → **기각**: 주장의 핵심 실패 메커니즘이 재현 불가 = REFUTED.

1. float() 캐스팅 위치 확인 (사실): cost_assumption_sensitivity.py:74-75 `BacktestConfig(fees=float(fees), slippage

- ~~trading/P1~~ `backend/src/trading/services/order_service.py:142`: has_leverage 판정 로직 중복 + 의미 불일치 (divergent duplication). order_service.py:142 는 dispatch_sn → **기각**: Claimed runtime impact (snapshot vs fallback path produce different Spot/Futures dispatch for the SAME order) cannot be reproduced. The dupl
- ~~trading/P2~~ `backend/src/trading/providers.py:107-114`: MP-4 precision 가드(amount_to_precision/price_to_precision, #307)는 3개 live provider(BybitDem → **기각**: 주장의 사실 골격은 맞으나, 핵심 severity 명제("정밀도 미적용 amount 가 거래소로 제출되는 silent path")는 실제 ccxt 4.5.49(.venv 설치본) 동작으로 반증됨.

검증된 사실:

- providers.py:107-11
- ~~trading/P2~~ `backend/src/trading/equity_calculator.py:63`: recompute_equity_curve 가 입력 closed_pnls 의 timestamp ASC 정렬을 '가정'만 하고 강제/정렬하지 않는다. 호출처(live → **기각**: 주장의 함수-단위 사실은 맞으나 인과 사슬(실제 버그 트리거)이 거짓이라 REFUTED.

[함수 사실 — 맞음] /Users/woosung/project/agy-project/quant-bridge/backend/src/trading/equity_c

- ~~market_data/P2~~ `backend/src/market_data/repository.py:83-99 (find_`: find_gaps 가 반환하는 (gap_start, gap_end) 는 '누락된 bar timestamp' 의 최소/최대값이다 (둘러싼 존재 bar 가 아니라 빈 → **기각**: 코드를 직접 읽어 검증한 결과, 주장의 두 하위 케이스가 모두 성립하지 않는다.

확인된 사실(주장 일부 정확):

- find_gaps 가 '누락된 bar timestamp' 의 MIN/MAX 를 반환하는 것은 맞다. repository.py:67-7
- ~~tasks/P2~~ `backend/src/stress_test/service.py:259-266`: stress_test_tasks 가 호출하는 StressTestService.run 의 실패 경로가 error=str(exc) 를 그대로 DB error_mess → **기각**: 주장의 핵심 전제(optimizer 는 public/internal 분리로 내부 detail 이 사용자 노출 error_message 로 leak 되지 않는다 vs stress 는 leak 된다)가 코드상 거짓이다. 두 도메인은 사용자 노출 측면에서
- ~~optimizer/P3~~ `backend/src/optimizer/engine/bayesian.py:388-391, `: Normal-prior RNG determinism is coupled to skopt's RNG by reusing the same seed (42) for b → **기각**: 코드를 직접 읽고 확인한 결과 이것은 버그가 아니다. 주장 자체가 "No incorrect output", "Determinism (the stated goal) holds", "no functional bug" 라고 자인하므로 real bug 기준(
- ~~tasks/P3~~ `backend/src/tasks/celery_app.py:215`: @worker_ready \_on_worker_ready uses asyncio.run(\_reclaim()) per domain, creating+tearing d → **기각**: 주장의 사실 관계는 정확하나 "현재 버그"가 아니라 반사실(counterfactual) 가정에 의존하는 maintainability 관찰이므로 기각.

검증한 file:line 사실:

1. backend/src/tasks/celery_app.py:20

- ~~stress_test/P3~~ `backend/src/stress_test/engine/param_stability.py:`: input.int 정수 검증이 음수 Decimal 에서 truncation-toward-zero 와 일치하지 않을 수 있는 경계. 검증은 `v != Decimal → **기각**: 주장(검증↔적용 캐스팅 정합 integration gap, 실제 버그 가능성)을 기각한다. 검증과 적용이 동일한 int() toward-zero 캐스팅을 사용하므로 mismatch 가 원천적으로 불가능하고, auditor 가 "부재"라고 한 oracl
- ~~optimizer/P2~~ `backend/tests/optimizer/test_bayesian_engine.py:22`: degenerate penalty(\_DEGENERATE_PENALTY=+1e10)의 direction 안전성 어서션이 약함. test_degenerate_retu → **기각**: 주장의 핵심 "버그 가설"(minimize 방향에서 penalty +1e10 이 실제 양수 objective 보다 작으면 degenerate cell 이 best 로 선출될 수 있다)은 코드 구조상 성립하지 않는다. 따라서 "penalty > 실제 최
- ~~trading/P3~~ `backend/src/trading/providers.py:107`: \_to_exchange_precision 가 create_order 마다 `await exchange.load_markets()` 를 호출한다. ephemeral → **기각**: 주장은 "load_markets 가 주문마다 네트워크 round-trip 1회를 추가한다"고 프레이밍하지만, CCXT 의 create_order 가 이미 내부적으로 load_markets 를 무조건 호출하므로 추가 round-trip 이 발생하지 않는
- ~~tasks/P2~~ `backend/src/tasks/orphan_scanner.py:81-95`: \_async_scan_stuck_orders unconditionally calls execute_order_task.apply_async for EVERY st → **기각**: FACTUAL HALF TRUE, HARM CLAIM REFUTED.

The literal observation is accurate: backend/src/tasks/orphan_scanner.py:81-95 unconditionally calls

- ~~stress_test/P3~~ `backend/tests/stress_test/engine/test_walk_forward`: WFA degradation 테스트가 circular oracle. aggregate_oos_return 을 '엔진이 산출한 folds 의 OOS 평균'과 비교( → **기각**: claim 의 전제 = "test_walk_forward_degradation.py 단일 파일만 검토" 한 결과로, 실제로는 같은 디렉터리의 sibling 테스트들이 모든 주장 항목을 hand-computed oracle 로 직접 검증한다.

1. d

- ~~trading/P2~~ `backend/src/trading/registry.py:35-64`: registry.py 의 dispatch() / PROVIDER_REGISTRY 에 대한 직접(direct) 단위 테스트가 0건이다. grep 결과 src/tes → **기각**: FACTUAL CORE CONFIRMED, BUG ARGUMENT SELF-REFUTING.

Verified facts:

- `grep -rn 'from src.trading.registry|PROVIDER_REGISTRY' backend/tests
- ~~optimizer/P2~~ `backend/src/optimizer/engine/genetic.py:186, 284-3`: DecimalField sampling and gaussian mutation drop into float space, violating the Decimal-f → **기각**: 주장의 코드 인용은 verbatim 정확하나, "버그/Golden Rule 위반"이라는 결론은 재현 불가 → REFUTED.

확인된 사실 (file:line):

- genetic.py:186 `Decimal(str(rng.uniform(float(f
