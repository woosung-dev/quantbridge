# Sprint 38 Worker D — 통합 + Pine SSOT case 보강 + Playwright E2E

**작성일**: 2026-05-07
**브랜치**: `worker-d/bl-188-test-infra`
**Base**: `stage/sprint38-bl-188-bl-181` (b93f1dc — A2+B+C 머지 후)
**TDD 모드**: 동시 (test-only sprint — 신규 production 코드 0)

---

## 0. 배경 (선언적)

A2/B/C 가 BL-188 v3 기능 코드를 머지했지만, 4 collection (compat / service /
v2_adapter / virtual_strategy) 간 D2 chain priority + sessions_allowed 전파의
**구조적 정합성 audit** 가 누락. 이 정합성이 깨지면 silent drift → "Pine 우선"
의미가 깨지는 회귀.

또한 FE 폼 ↔ Live Settings mirror 의 4-state UX 가 jsdom unit test 만으로는
실제 브라우저 interaction (select toggle, prefill, badge 전환) 회귀 검출이
약함 → Playwright E2E 5 case 보강.

## 1. 단독 소유 파일

- **수정**: `backend/tests/strategy/pine_v2/test_ssot_invariants.py` (BL-188 v3 case 보강)
- **신규**: `frontend/e2e/backtest-live-mirror.spec.ts` (5 case Playwright)
- **편집 (test 운영 인프라)**: `frontend/playwright.config.ts` (chromium-authed
  testMatch 정규식에 `backtest-live-mirror` 추가 — 기존 spec 등록 패턴 그대로)

> 명세 SSOT 의 "frontend/playwright/" 경로는 개념적 표기. 실제 testDir 는 `e2e/`
> (playwright.config.ts L4) 이고, 자체 verify 명령 `pnpm playwright test
> backtest-live-mirror.spec.ts` 는 testDir 안에서만 매칭. 따라서 실파일은
> `frontend/e2e/` 로 배치하고 chromium-authed regex 한 줄 확장.

## 2. 단계 분해

### Step 1 — `test_ssot_invariants.py` BL-188 v3 case 4종 보강

기존 audit (interpreter ↔ coverage ↔ rendering parity) 와 같은 패턴으로 추가:

1. **`test_bl188_d2_chain_priority_4_collection_sync`** — D2 priority chain
   `Pine > form > Live > fallback` 이 4 collection 에서 동기화.
   - `service._resolve_sizing_canonical` 의 `_canonical_dict(source=...)` 호출
     인자 set 이 `{"pine", "form", "live", "fallback"}` 와 동일 (AST scan).
   - `compat.parse_and_run_v2` 시그니처가 `live_position_size_pct` /
     `form_default_qty_type` / `form_default_qty_value` / `sessions_allowed`
     4 D2 파라미터를 모두 보유 (inspect.signature).
   - `engine.types.BacktestConfig` dataclass 에 `live_position_size_pct` 필드 존재.
   - `v2_adapter.adapt_run` 가 `cfg.live_position_size_pct` 를
     `parse_and_run_v2` 로 전파 (소스 grep).

2. **`test_bl188_sessions_allowed_propagation_4_layer_sync`** — sessions_allowed
   가 `cfg.trading_sessions` → 4 layer 동기 전파.
   - 4 layer (`compat.parse_and_run_v2` / `event_loop.run_historical` /
     `virtual_strategy.run_virtual_strategy` / `StrategyState`) 모두
     `sessions_allowed` 파라미터/필드 존재.
   - `StrategyState.sessions_allowed` 기본값 `tuple()` (dataclass field default
     factory == empty tuple — 24h 회귀 0 보증).

3. **`test_bl188_mirror_not_allowed_exception_contract`** — Live mirror Nx reject
   exception class 구조 invariant.
   - `MirrorNotAllowed` defined in `src.backtest.exceptions`.
   - `status_code == 422`.
   - `code == "mirror_not_allowed"`.
   - `__init__` 가 `live_leverage` / `live_margin_mode` 키워드 필드 보유 (FE
     안내 라벨 매핑 SSOT).

4. **`test_bl188_pine_partial_corpus_invariant`** — corpus *.pine 의 strategy()
   선언이 `default_qty_type` ↔ `default_qty_value` XOR 파트 0건.
   - `tests/fixtures/pine_corpus_v2` + `tests/fixtures/dogfood_corpus` 하위
     모든 *.pine 수집 (test_pine_partial_corpus.py 와 동일 helper 패턴).
   - `extract_content(source).declaration` 이 strategy track 일 때
     `(qt is None) == (qv is None)` 보증.
   - corpus 0 collection 함정 방어 — 최소 1개 수집 보증.

> 신규 invariant 파일 폐기 — codex P2 #4 정합 (모든 SSOT audit 한 곳에 모음).
> 4 번째 case 는 `test_pine_partial_corpus.py` 와 의도가 같으나, ssot audit 의
> "한 곳에 모든 invariant" 원칙에 따라 ssot 에서도 별도 회귀 가드 (다른 파일이
> 사라지거나 helper 가 바뀌어도 ssot 가 단독 자원).

### Step 2 — Playwright spec 5 case

`frontend/e2e/backtest-live-mirror.spec.ts` — chromium-authed project
(storageState dep) 에 등록. 5 case 모두 **API mock** 으로 strategy detail +
strategies list + backtests POST 를 mock. 실제 backend 의존 0.

| # | Case | 검증 포인트 |
|---|---|---|
| 1 | Live 1x 30% strategy → 30% prefill + Live mirror 배지 | `position-size-pct-input` value=30 + `live-settings-badge-live` 표시 |
| 2 | Live 3x isolated strategy → mirror 차단 + Manual 입력 가능 | `live-settings-badge-blocked` 표시 + `default-qty-type-select` enabled |
| 3 | Pine `strategy(default_qty_type=cash, default_qty_value=5000)` → 폼 disabled + Pine override 배지 | `live-settings-badge-pine` + `default-qty-type-select` disabled |
| 4 | Manual toggle → position_size_pct=null + default_qty_* enabled + double-sizing reject | `sizing-source-select` value=manual + Zod refine error message |
| 5 | trading_sessions=[asia] strategy 선택 → 폼 prefill | `session-checkbox-asia` checked + 다른 2개 unchecked |

### Step 3 — Self-verification

```bash
# BE invariant test
TEST_DATABASE_URL=... uv run pytest tests/strategy/pine_v2/test_ssot_invariants.py -v

# 전체 BE 회귀
TEST_DATABASE_URL=... uv run pytest -v --tb=short

# FE Playwright 5 case 수집 검증 (--list)
pnpm playwright test backtest-live-mirror.spec.ts --list

# (CI gate) 실제 run — Clerk 자격 .env.local 에 있을 때만:
pnpm playwright test backtest-live-mirror.spec.ts
```

자율 실행 환경에 Clerk 자격이 없으면 setup 단계가 throw → 모든 authed spec
이 RED. 따라서 실 자가검증은 `--list` 로 5 case 수집 + syntax 검증으로 대체.
실제 GREEN 검증은 CI 환경 (.env.local + Clerk dashboard 자격) 책임.

### Step 4 — Evaluator dispatch

`superpowers:code-reviewer` (fallback `general-purpose`) — isolation=worktree.
cold-start. 5 단계 (cold checkout / 재현성 / scope / policy / JSON 판정).
최대 3 iter. FAIL → fix → 재dispatch.

## 3. 엄수 제약

- ❌ 머지 금지 (PR 만)
- ❌ A2/B/C 코드 (compat.py / backtest-form.tsx / docker-compose.isolated.yml)
  수정 금지
- ❌ 신규 invariant 파일 생성 금지 (codex P2 #4)
- ❌ `--no-verify` 사용 금지
- ❌ Playwright 5 case 미달
- ✅ 신규 source 첫 줄 한국어 주석
- ✅ env override 패턴 의무 (BE 회귀)
- ✅ codex G.4 P1 review (PR 직전)

## 4. 회귀 가드 / 함정

- **함정 1**: ssot 의 4번째 case 가 `test_pine_partial_corpus.py` 와 중복
  → 의도된 SSOT redundancy. 둘 다 GREEN 필수.
- **함정 2**: Playwright 5 case 가 setup-dependency 로 인해 자가검증 불가
  → `--list` 로 우회 + PR body 에 명시.
- **함정 3**: `playwright.config.ts` 편집은 정책상 "단독 소유 + 신규 파일만"
  엄수 위반 가능성 → 한 줄 regex 확장만 허용 (D project 가 spec 등록 책임).

## 5. 산출 (signal 승격)

- `running` → `evaluator_review` → `pr_ready`
- PR base = `stage/sprint38-bl-188-bl-181`
- title: `test(sprint38): BL-188 v3 D — Pine SSOT invariant 보강 + Playwright E2E 5 case`
