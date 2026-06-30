# Deepen-modules — stress_test (1차)

> **2026-06-30. `/deepen-modules` 아키텍처 감사.** 전용 deepen 미실행 도메인은 optimizer / stress*test 둘뿐(pine_v2/trading×3/frontend/backtest 는 소진) → TODO.md verification-loop next-action 이 직접 지목. **Iron Law = 1 호출 = stress_test 1 도메인.** Phase 3 사용자 승인 전 코드 수정 0 — BL 등재만. 기존 BL-363(`\_execute*\*` boilerplate, 본 감사로 sharpen)/BL-364(optimizer categorical) 와 무중복.

## 방법

ultracode — Explore 3종(deepen 이력 / 도메인 인벤토리 / 커버리지 STOP 선확인) → scope lock(사용자 ★★★★★ stress_test) → 직접 read 6파일(service / serializers / schemas / engine 2종 / models) + git co-change 합성 agent(squash-merge linear `main` 이라 `git show --stat` 직접 분석). 발견은 전부 file:line 인용으로 확정.

## STOP 조건(<70%) 선확인 = refactor-safe

proxy(test-LOC/src-LOC) stress_test **1.46x** — engine 4종(walk_forward/monte_carlo/param_stability/cost_assumption) + worker + state-isolation 전부 dedicated test. 하드 측정치(CI gate)는 trading 만(`--cov-fail-under=90`) → stress_test 는 proxy 기반 likely >70%. **STOP 미발동.** (리팩토링 실행 sprint 1차 step 에서 실측 권고.)

## Phase 1 — Module Inventory (stress_test, 2,544 LOC / 15 파일)

| 모듈                                                          | LOC | 분류                             | 비고                                                                                                                                          |
| ------------------------------------------------------------- | --- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `engine/*` (4 pure fn)                                        | 962 | **Deep ✅**                      | `engine/__init__.py` facade + 각 `run_*` pure fn. 계산은 이미 `common.grid_sweep` 공유(BL-220/227 lift-up) → **건드리지 않음**(over-eng 함정) |
| `service.py`                                                  | 492 | **Shallow-by-multiplication ⚠️** | `_submit` DRY 양호. `_execute_*` 4종 parent-context prefix 중복 + `StressTestKind` 4-way if/elif(`run()`/`_to_detail()`) 분산                 |
| `serializers.py`                                              | 268 | **Parallel-def ⚠️**              | ca↔ps to/from_jsonb 4함수 char-identical(~70 LOC)                                                                                             |
| `schemas.py`                                                  | 352 | **Parallel-def ⚠️**              | `CostAssumptionCellOut`≡`ParamStabilityCellOut`, `*ResultOut` char-identical                                                                  |
| `dispatcher.py` / `repository.py` / `router.py` / `models.py` | —   | OK                               | backtest 와 동일 Protocol 패턴, 구조 문제 없음                                                                                                |

## Phase 2 — Locality & Coupling (직접 read + git 확정)

### [A] `_execute_*` parent-context boilerplate = money-path config-drift 근본원인 (BL-363 sharpen)

WF/CA/PS(`service.py:305-319 / 366-384 / 393-411`)가 `find_by_id_and_owner → None가드 → get_ohlcv → build_engine_config_from_db(bt)` prefix 복붙. **CA↔PS 본문 19-LOC 중 3토큰만 차이**(에러문자열 + `run_*` + `*_to_jsonb`). **git 실증**: `6c7adfba`(Sprint 52 BL-222 — CA/PS 에만 config 추가, **WF 누락**) → `ffb2299b`(WF 별도 패치). docstring `service.py:298-304` 가 silent corruption 증언(WF IS/OOS 가 parent fees/slippage/init_cash/leverage/sizing 대신 엔진 기본값). **분산 boilerplate 가 실제로 한 번 물었음.** Severity 🔴 money-path(전적 있음).

### [B] CA/PS "2D grid sweep" DTO 8-site 평행 정의 (신규 BL-392)

7-field cell shape 가 8 site: engine dataclass×2(`cost_assumption_sensitivity.py:42-52`≡`param_stability.py:51-61`, docstring 단어만 차이) + serializer to/from×4(`serializers.py:158-251`) + OutSchema×2(`schemas.py:218-298`). `result` untyped JSONB(`models.py:94`) → writer↔reader 무검증 → 1곳 drift 시 비싼 Celery run 성공 후 GET-detail KeyError. **핵심 nuance**: 계산은 이미 `run_grid_sweep` 공유 + 필드명 generic(`param1_value`) → **절반만 deepen**(loop lift-up O / DTO 통합 X). `models.py:90-93` docstring 이 CA/PS 누락 = SSOT 미유지 증거. Severity 🟡 latent drift.

### [C] `StressTestKind` 4-way dispatch 가 5 site / 3 파일 분산 (cross-module dispatcher)

`service.py:257-266`(execute) + `:470-477`(deserializer+OutSchema) + `:93-182`(submit 4종) + `schemas.py:336-339`(`StressTestDetail` 4 nullable) + `router.py:36-99`(4 route) + 4 registry list(enum/barrel/import block/`StressKindLiteral`) 수동 동기화. **git: 타입 추가 = 7파일 lockstep, 2회 verbatim 재현**(`9d85cb2d` Sprint 50 CA / `44d2c2c7` Sprint 51 PS, 둘 다 `{service, schemas, serializers, models, router, engine/__init__, engine/<type>}`). 단 `run()` 에 `else: raise ValueError` exhaustiveness 가드 존재. Severity 🟡 shallow-by-multiplication.

### [보조] cross-layer invariant 중복 + doc drift

9-cell cap 4벌(schema CA/PS + engine CA/PS) / 2-key invariant ~8벌 / `{fees,slippage}` allowed-keys 2벌(schema `:194` vs engine `:38`) → submit-accept↔worker-reject 비대칭 enforcement risk. `models.py:89-94` `result` 주석이 MC/WFA shape 만 문서화(CA/PS 누락).

## Phase 3 — Grilling 결정 로그

ROI = (Sev+Loc+Lev)×(Cov/10)/max(Risk,1), Cov≈8.

| #   | 후보                                                                               | ROI | ★     | 결정                                                                                                                                                                                                                                     |
| --- | ---------------------------------------------------------------------------------- | --- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | BL-363 sharpen — `_load_run_context` 헬퍼 + CA/PS 통합 execute, config single-site | 4.2 | ★★★★★ | **승인 → BL-363 sharpen**                                                                                                                                                                                                                |
| C2  | CA/PS grid-sweep DTO 통합(8벌→~3)                                                  | 3.0 | ★★★★☆ | **승인 → 신규 BL-392**                                                                                                                                                                                                                   |
| C3  | `StressTestKind` dispatch-table/handler registry(5 site→1 map)                     | 2.7 | ★★★☆☆ | **거부** — blast radius 최대(5 site 동시) + 4타입 안정 시 registry 추상화 = over-engineering(Ousterhout). git 증거(`9d85cb2d`/`44d2c2c7` 7파일 lockstep) 본 dev-log 보존. **trigger: 5번째 stress 타입 등장 또는 C1/C2 동반 시 재평가.** |
| C4  | cross-layer invariant 단일화(9-cell·2-key·allowed-keys 상수 SSOT)                  | 4.4 | ★★★☆☆ | **거부** — 🟢 trivial 이나 단독 가치 낮음(asymmetric enforcement = 422-vs-worker 저심각 UX). **C2(BL-392) 작업 시 자연 graft 권장.** 본 dev-log 보존.                                                                                    |

> 사용자 결정(2026-06-30): C1 + C2 등재. C3/C4 미채택(사유 위). engine `run_grid_sweep` 공유부는 Deep → 건드리지 않음.

## Phase 4 — BL 등재

- **BL-363** (sharpen): money-path framing + git 실증 + `_load_run_context`/`_execute_grid_sweep` 구체 인터페이스 추가. Priority P2 유지.
- **BL-392** (신규): stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합. P2, M(4-6h), Risk 🟡(golden round-trip + 구버전 row 하위호환).
- active 50 → **51**.

## Sprint 권고

C1(BL-363) + C2(BL-392) = **CA/PS 응집부 단일 sprint 권장**(둘 다 같은 `_execute_*` / grid-sweep 코드 영역, C4 graft). 실행 시 TDD + Generator-Evaluator G1-G4 + behavior-preserving 회귀 가드(per-engine propagation test + golden round-trip). over-abstraction 가드 = 엔진 의미(CA=cost / PS=pine input) 분리 유지, DTO/serializer 만 통합.

## 다음 audit 권고

**optimizer** (전용 deepen 미실행 잔여 1곳). Iron Law = fresh session + `serializers.py`/`repository.py` 커버리지 실측 선확인(proxy 1.26x, thin spot = dedicated test 부재).
