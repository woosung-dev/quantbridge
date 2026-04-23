# ADR-013: Trust Layer CI — 3-Layer Parity (P-1/2/3) 설계

> **상태:** 초안 (Path β Stage 0 — 2026-04-23 작성, Stage 2 구현 완료 시 확정)
> **일자:** 2026-04-23
> **관련 ADR:** [ADR-003](./003-pine-runtime-safety-and-parser-scope.md) (exec 금지), [ADR-004](./004-pine-parser-approach-selection.md) (AST 인터프리터), [ADR-011](./011-pine-execution-strategy-v4.md) (Tier 0~5), [ADR-012](./012-sprint-8a-tier0-final-report.md) (Tier-0 Foundation)
> **상위 문서:** [`docs/04_architecture/trust-layer-architecture.md`](../04_architecture/trust-layer-architecture.md) (Path β Stage 0 산출)
> **관련 Sprint:** Path β (Stage 0 문서 → Stage 1 설계 → Stage 2 구현) + Sprint Y1 Coverage Analyzer prerequisite
> **참조 아키텍처 서베이:** [`docs/superpowers/reports/2026-04-23-architecture-survey.html`](../superpowers/reports/2026-04-23-architecture-survey.html)

---

## 1. 배경 — 왜 지금 Trust Layer CI 인가

Sprint Y1 (PR #61) 의 **Pre-flight Coverage Analyzer** 로 **사용자 facing trust** (whack-a-mole 종식, 422 reject, UI 경고 박스) 가 확립됐다. 하지만 **엔지니어 facing silent regression** 을 막을 안전망은 아직 없다. 현재 상황:

| 영역                                                             | 현재 상태                                              | 공백                                            |
| ---------------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| pynescript AST 노드 수/타입 합치                                 | ✅ `test_pynescript_baseline_parity.py` 로 검증        | 부모-자식 edge shape 까진 미검증                |
| coverage.py `SUPPORTED_FUNCTIONS` ↔ interpreter/stdlib 실제 구현 | ❌ 수동 동기화 (LLM/사람이 3 파일 동시 갱신)           | 오차 발견 방법 = 런타임 실패                    |
| 6 corpus × metrics 재현성                                        | ⚠️ E2E 테스트는 있지만 "trade 수 ≥1" 류 weak assertion | **숫자 편차 게이트 없음 — Path β 의 핵심 공백** |
| PyneCore transformers 이식 (ADR-011 §4 Tier-2 원본 정의)         | ❌ 미이식 (persistent.py 의미론만 차용)                | 완전 Tier-2 실현의 prerequisite                 |

stdlib 의 **단 한 줄 수정** (예: `ta.rsi` 의 warm-up 기간을 14 → 15 로 오타) 이 6 corpus 의 `total_return` 을 조용히 -2% 흔들어도 현재 CI 는 **green** 일 수 있다. ADR-011 §4 Tier-2 는 "상대 오차 <0.1% 게이트" 를 명시했으나 Phase -1 실측 (2026-04-18) 결과 **PyneCore CLI 는 PyneSys 상용 API 의존** 으로 독립 오라클 불가. 비교 기준점을 재정의해야 한다.

---

## 2. 결정 요약 (한 줄)

> **ADR-011 §4 Tier-2 를 "3-Layer Parity" (P-1 AST Shape + P-2 Coverage SSOT Sync + P-3 Execution Golden) 로 실용화하여 Path β Stage 2 에 구현한다. PyneCore transformers 이식 기반의 P-4 (Reference Execution Oracle) 는 후속 Sprint (Path γ 이후) 로 이연한다.**

|    Layer     | 비교 대상                                                                            |         Path β 포함          |
| :----------: | ------------------------------------------------------------------------------------ | :--------------------------: |
|   **P-1**    | `pynescript==0.3.0` AST 노드 수/타입/edge shape ⟺ `baseline.json`                    |      ✅ 기존 test 확장       |
|   **P-2**    | `coverage.SUPPORTED_FUNCTIONS/ATTRIBUTES` ⟺ `interpreter/stdlib` 리플렉션            |           ✅ 신규            |
|   **P-3**    | 6 corpus × 고정 OHLCV → `BacktestOutcome.metrics` digest 골든 diff (상대 오차 <0.1%) |        ✅ 신규 (핵심)        |
| P-4 (future) | QB Tier-0 실행 결과 ⟺ PyneCore transformers 이식본 실행 결과                         | ❌ 이연 (PyneCore 이식 선행) |

---

## 3. 고려한 대안

| 대안                                                      |  채택   | 사유                                                                                       |
| --------------------------------------------------------- | :-----: | ------------------------------------------------------------------------------------------ |
| **A. PyneCore transformers 선이식 후 full Tier-2 CI**     |   ❌    | Path β 1주 범위 초과. 라이선스 격리, API 통합, 추가 테스트까지 고려 시 3~4주 필요          |
| **B. QB 결과 vs pynescript AST 만 비교 (AST Shape only)** |   ❌    | pynescript 는 파서일 뿐. 실행 엔진 없음 → 실행 결과 오차는 못 잡음                         |
| **C. 6 corpus × 수동 expected_metrics.json 골든**         | 🟡 기반 | 재현성 확보. 그러나 corpus 가 변할 때 수동 갱신 피로                                       |
| **D. Option C + 갱신 스크립트 (`--confirm` 게이트)**      |   ✅    | 수동 갱신 자동화 + 승인 플래그로 오남용 방지                                               |
| **E. Mutation-based oracle-of-oracle**                    | ✅ 보조 | CI 가 실제로 regression 을 잡는지 검증하는 **메타 게이트**. 8개 hand-crafted mutation 샘플 |
| **F. LLM 기반 결과 해석/비교**                            |   ❌    | ADR-011 §7 LLM 원샷 거부 원칙 연장. Trust Layer 가 LLM 노이즈 섞이면 신뢰도 역행           |

**선택**: D (Option C + 갱신 스크립트) + E (Mutation Oracle 보조). P-1/2/3 3-Layer 로 분해하고, P-3 가 D 에 해당.

---

## 4. 설계 상세

### 4.1 P-1 — AST Shape Parity

**목적**: pynescript 버전 업그레이드 또는 corpus 변경 시 AST 구조 drift 를 CI 에서 감지.

**구현**:

- 기존 `backend/tests/strategy/pine_v2/test_pynescript_baseline_parity.py` 확장
- `baseline.json` 항목 확장: 기존 `node_count` + `node_type_histogram` → **추가** `edge_digest` (부모-자식 관계의 sha256)
- `parent→child` 정렬된 튜플 리스트 직렬화 → `hashlib.sha256(json.dumps(..., sort_keys=True)).hexdigest()`
- 6 corpus 전원 pass 필수

**잡아내는 것**:

- pynescript 메이저/마이너 업그레이드 시 AST 구조 변경 (예: `BinaryOp` → `BinOp`)
- corpus 파일 의도치 않은 수정 (`.pine` 오타 commit)

**못 잡는 것**: 실행 결과 편차 (P-3 담당).

### 4.2 P-2 — Coverage SSOT Sync

**목적**: `coverage.SUPPORTED_FUNCTIONS` 가 실제 `interpreter/stdlib` 의 구현 항목과 동기화 유지.

**구현** (신규 `test_coverage_ssot_sync.py`):

- Import `pine_v2.coverage as cov`, `pine_v2.interpreter as interp`, `pine_v2.stdlib as sl`
- 실제 dispatch 실체 수집 (codex Gate-1 W-C1 반영 — 2026-04-23 실측 확인):
  - **`interp._STDLIB_NAMES`** (set, `interpreter.py:684~`) — 현재 실체인 SSOT
  - **`sl.StdlibDispatcher.call()`** (`stdlib.py:538~`) — if-elif 체인 dispatch
  - `interp._handle_plot_nop / _handle_alert / _handle_input` 등 NOP 핸들러
  - 과거 언급된 `TA_CALLABLES / MATH_CALLABLES` 등 dict 기반 dispatch 는 **존재하지 않음** —
    Stage 2 구현자는 `_STDLIB_NAMES` 를 SSOT 로 사용하거나 `StdlibDispatcher.call`
    소스를 AST 파싱 중 택 1
- 양방향 assertion:
  - `cov.SUPPORTED_FUNCTIONS ⊆ {실제 바인딩된 것 ∪ NOP 허용 목록}` (coverage 가 거짓말 안 함)
  - `{실제 구현된 것 ∪ NOP} ⊆ cov.SUPPORTED_FUNCTIONS` (구현은 있는데 coverage 가 모르는 상태 차단)
- `SUPPORTED_ATTRIBUTES` 도 동일 패턴

**잡아내는 것**:

- "stdlib 에 새 함수 추가했는데 coverage.py 갱신 누락" → 사용자가 parse_preview 에서 경고 못 봄
- "coverage.py 에는 있는데 stdlib 구현 삭제" → 런타임 `NotImplementedError`

**못 잡는 것**: 구현은 있는데 semantic 이 틀린 경우 (P-3 담당).

### 4.3 P-3 — Execution Golden (핵심)

**목적**: stdlib / interpreter / strategy_state 의 **실행 결과 편차** 를 매 commit 에서 감지.

**Fixed OHLCV**:

- `backend/tests/fixtures/pine_corpus_v2/corpus_ohlcv_frozen.parquet`
- BTCUSDT 1h, 2024-01-01 00:00:00 UTC ~ 2024-06-30 23:00:00 UTC (약 4,320 bars)
- 출처: Bybit public klines (데이터 검증 후 고정). 파일 해시를 ADR 부록에 기록

**Baseline 형식** (`baseline_metrics.json`):

```json
{
  "schema_version": 1,
  "ohlcv_sha256": "abc123...",
  "pine_v2_commit": "08c6388",
  "generated_at": "2026-04-24T00:00:00Z",
  "corpora": {
    "s1_pbr": {
      "metrics": {
        "total_return": "0.1532",
        "sharpe_ratio": "1.2041",
        "max_drawdown": "0.0832",
        "win_rate": "0.52",
        "num_trades": 47,
        "profit_factor": "1.35",
        "sortino_ratio": "1.6221",
        "calmar_ratio": "1.84",
        "avg_win": "0.0151",
        "avg_loss": "-0.0098",
        "long_count": 47,
        "short_count": 0
      },
      "var_series_digest": "sha256:...",
      "trades_digest": "sha256:...",
      "warnings_digest": "sha256:..."
    },
    "s2_utbot": { ... },
    "s3_rsid": { ... },
    "i1_utbot": { ... },
    "i2_luxalgo": { ... },
    "i3_drfx": { "note": "Skipped — is_runnable=false per Y1 Coverage Analyzer" }
  }
}
```

**Decimal-first 규칙 준수**: metrics 는 `str(Decimal)` 로 직렬화. 비교 시 `Decimal(str(expected))` vs `Decimal(str(actual))` (LESSON Sprint 4 D8).

**허용 오차** (신규 유틸 `backend/tests/strategy/pine_v2/_tolerance.py`):

```python
def within_tolerance(actual: Decimal, expected: Decimal) -> bool:
    if expected == 0:
        return abs(actual) < Decimal("0.001")
    rel_err = abs((actual - expected) / expected)
    abs_err = abs(actual - expected)
    return rel_err < Decimal("0.001") or abs_err < Decimal("0.001")
```

(max(상대 0.1%, 절대 0.001) — 작은 값에 대해 상대 오차가 과민반응하지 않도록)

**Digest 기반 배열 비교**: `var_series`, `trades`, `warnings` 는 길이가 수백~수천. 전체 JSON diff 은 git 친화적이지 않으니 sha256 digest 만 baseline 에 저장. 실패 시 artifact 로 전체 dump 업로드 (GitHub Actions `upload-artifact`) 하여 원인 파악.

**Regen 스크립트** (`backend/scripts/regen_trust_layer_baseline.py`):

- CLI: `python scripts/regen_trust_layer_baseline.py --confirm [--corpus s1_pbr]`
- `--confirm` 없으면 `sys.exit(1)` + 에러 메시지 "의도된 baseline 갱신임을 명시하려면 --confirm 플래그가 필요합니다"
- git diff 로 변경 범위를 사람이 확인 후 PR 에 포함
- 실행 시 pine_v2 HEAD 커밋 해시를 baseline 에 기록

### 4.4 Mutation Oracle (보조, P-3 품질 검증)

**목적**: "P-1/2/3 이 실제로 regression 을 잡는가?" 를 증명.

**8개 hand-crafted mutation 세트** (신규 `test_mutation_oracle.py`, default skip):

|  #  | Mutation                                             |     예상 포착 Layer     |
| :-: | ---------------------------------------------------- | :---------------------: |
| M1  | `ta.sma` window off-by-one (`length` → `length - 1`) |           P-3           |
| M2  | `ta.rsi` division-by-zero guard 제거                 |           P-3           |
| M3  | `strategy.entry` 반환값 None → False                 |  P-2 (리플렉션) or P-3  |
| M4  | `ta.crossover` 경계 조건 `>` → `>=`                  |           P-3           |
| M5  | `position_size` 부호 반전 (long 포지션이 음수)       |           P-3           |
| M6  | Decimal → float 암묵적 leak (`Decimal(str(a+b))`)    | P-3 (상대 오차 >0.001%) |
| M7  | `persistent.rollback_bar` 누락 (var 갱신 미반영)     |           P-3           |
| M8  | alert hook 중복 등록 (같은 조건 2회 발화)            |   P-3 (trades_digest)   |

**CI 포함 여부**: default **skip** (실행 시간 +2분). `pytest --run-mutations` 수동 실행 또는 nightly workflow. 기본값은 nightly — Gate-1 결정 대기.

**성공 기준**: 8 개 중 ≥7 개를 P-1/2/3 중 **최소 1 레이어** 가 포착 (Gate-2 G2-C).

### 4.5 CI 배치

`.github/workflows/ci.yml` 의 backend job **내부 step** 으로 추가 (별도 job 생성 안 함, 서비스 컨테이너 재사용):

```yaml
- name: Trust Layer Parity
  working-directory: backend
  run: |
    uv run pytest -v \
      tests/strategy/pine_v2/test_pynescript_baseline_parity.py \
      tests/strategy/pine_v2/test_coverage_ssot_sync.py \
      tests/strategy/pine_v2/test_execution_golden.py \
      --timeout=120
  timeout-minutes: 5
```

**목표 시간**: ≤3분. 측정 후 초과 시 corpus subset marker (`@pytest.mark.trust_layer_full`) 도입 — PR 은 subset (s1+s2+i2), nightly 는 full.

---

## 5. 성공 기준 (SLO)

|   #   | 기준                                                     | 측정법                                      | Gate |
| :---: | -------------------------------------------------------- | ------------------------------------------- | :--: |
| SLO-1 | P-1 AST Shape 6/6 corpus green                           | `pytest test_pynescript_baseline_parity.py` | G2-A |
| SLO-2 | P-2 Coverage SSOT 양방향 assertion green                 | `pytest test_coverage_ssot_sync.py`         | G2-A |
| SLO-3 | P-3 Execution Golden 상대 오차 <0.1% 또는 절대 <0.001    | `pytest test_execution_golden.py`           | G2-A |
| SLO-4 | CI 실행 시간 ≤3분 (backend job Trust Layer step)         | GitHub Actions 실측                         | G2-B |
| SLO-5 | Mutation 8개 중 ≥7개 포착                                | `pytest --run-mutations`                    | G2-C |
| SLO-6 | `regen_trust_layer_baseline.py` 가 `--confirm` 없이 실패 | subprocess 테스트                           | G2-D |
| SLO-7 | 기존 trading/backtest suite regression 0건               | 전체 `pytest -v`                            | G2-F |

SLO-1~3 는 main merge 게이트. SLO-4 초과 시 subset marker 도입 (degrade, not block).

---

## 6. 영향 범위

### 코드

- 신규: `test_coverage_ssot_sync.py`, `test_execution_golden.py`, `test_mutation_oracle.py`, `_tolerance.py`
- 수정: `test_pynescript_baseline_parity.py` (edge digest 추가), `.github/workflows/ci.yml` (step 1개)
- 데이터: `baseline_metrics.json` (6 corpus × metrics), `corpus_ohlcv_frozen.parquet` (~2MB)
- 스크립트: `backend/scripts/regen_trust_layer_baseline.py`

### 테스트

- 기존 254 pine_v2 tests → +10~20 tests 예상 (~264~274)
- 기존 시간에 +3분 이내 추가 (CI 통산 <20분 유지)

### 문서

- `docs/04_architecture/trust-layer-architecture.md` (신규, 이 ADR 의 상위 아키텍처 요약)
- `docs/01_requirements/trust-layer-requirements.md` (신규, SLO)
- `docs/TODO.md` 에 P-4 (PyneCore 이식) 를 Path γ 로 tracking

### 운영

- stdlib/interpreter/coverage 변경 시 **3 파일 동시 PR** 규칙은 그대로지만, 누락이 CI 에서 자동 포착
- baseline 갱신은 `regen_*.py --confirm` 으로 명시적 증거 남김 (PR diff 리뷰 가능)

---

## 7. 거부된 대안 (명시)

| 대안                                    | 거부 사유                                                                                                                                                  |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Option A (PyneCore 선이식)**          | Path β 1주 범위 초과. transformers/ 의 persistent.py/series.py/security.py 3 모듈 이식 + 라이선스 NOTICE + API 통합 + 테스트까지 3~4주. Path γ 이후로 이연 |
| **TradingView 공식 API 호출**           | TV ToS 회색지대, 속도/레이트, 인증 비용. Trust Layer 로는 부적합                                                                                           |
| **vectorbt.signals golden 비교**        | ADR-011 에서 vectorbt 는 "지표 계산 전용" 으로 강등. Signal/strategy 계산에 의존 금지                                                                      |
| **pytest-snapshot / syrupy 라이브러리** | 의존성 추가 대비 이득 적음. hand-rolled digest 로 충분                                                                                                     |
| **매 metric 개별 파일로 저장**          | 파일 수 폭증 (6 corpus × 13 metric = 78). 단일 JSON 유지가 git diff 친화                                                                                   |
| **Baseline 을 DB 에 저장**              | 재현성/버전관리 어려움. 파일 + git 이 SSOT 원칙                                                                                                            |

---

## 8. 다음 단계

### Path β Stage 1 (Design, Day 3) ✅ 완료 (2026-04-23)

- [x] `test_trust_layer_parity.py` 스켈레톤 + `_tolerance.py` stub (Stage 2 에서 채움)
- [x] `baseline_metrics.schema.json` (JSON Schema Draft 2020-12, `tool_versions` 포함)
- [x] Day 3 오픈 질문 결정 → §10.1 참조
- [ ] Gate-1 evaluator (codex + opus 2중 blind) — 다음 단계

### Path β Stage 2 (Implement, Day 4~7)

- [ ] 8 단계 커밋 (corpus_ohlcv_frozen → baseline_metrics → P-1 → P-2 → P-3 → mutation → CI → ADR 보강)
- [ ] Gate-2 evaluator

### Path γ 이후 (P-4, ~3주)

- [ ] PyneCore `transformers/persistent.py` + `series.py` + `security.py` 참조 이식
- [ ] NOTICE 파일 + Apache 2.0 원본 헤더 유지
- [ ] `test_pynecore_reference_oracle.py` 추가 → **ADR-011 Tier-2 완전 구현**
- [ ] 본 ADR 을 "P-1/2/3/4 full Tier-2" 로 amend

---

## 9. 신뢰도

**Path β Stage 0 초안 시점: 7/10.** 상승 근거:

- ADR-011 §4 Tier-2 정의 + §13 Phase -1 실측 결과와 정합
- 기존 `test_pynescript_baseline_parity.py` + `coverage.py` SSOT 가 이미 존재 → 확장형 설계
- Decimal-first 원칙 + 허용 오차 공식이 명확
- Mutation Oracle 로 CI 자체의 품질 게이트 존재

하락 근거:

- P-4 (full Tier-2) 미포함 — "실행 결과 비교" 가 QB 자체 비교 (golden) 에 머무름. 논리적 오라클 부재
- Mutation 8개가 실제 production regression 을 대표하는지 샘플링 오류 가능
- corpus 6 종이 실사용 패턴 전체의 proxy 로 충분한지 미검증 (TV 프로파일링 Path γ 에서 보완)

**Gate-2 통과 후 예상 신뢰도: 8.5/10.** Path γ (P-4 추가) 이후: 9.5/10.

---

## 10. 오픈 이슈

1. **Baseline regen 주기 정책**: stdlib 의미 변경 PR 마다 regen 의무화? 아니면 main merge 시점에만?
   - 잠정: **stdlib 의미 변경 PR 마다 regen + `--confirm` diff 를 PR 리뷰어 승인 필수**. 메커니즘은 CODEOWNERS 또는 수동 규약.
2. **corpus 6 종 미만으로 Path β 시작 (i3_drfx 제외 → 5 종)**: Y1 Coverage 가 reject 하는 i3_drfx 는 baseline 에 `"note": "Skipped"` 로 기록만. 실행 테스트 X.
3. **pynescript 버전 고정 정책**: 현재 `==0.3.0`. P-1 은 이 버전 기준 baseline. 업그레이드는 별도 PR + baseline 동시 갱신.

### 10.1 Stage 1 에서 확정 (2026-04-23)

Stage 1 Day 3 오픈 질문 3 개 결정 + Gate-0 Opus evaluator Warning (W2/W3/W4/W5) 반영.

|                  #                  | 결정                                                               | 근거                                                                             |
| :---------------------------------: | ------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
|     **Q1** Evaluator 실행 방식      | **병렬** (codex + opus 동시)                                       | Gate-0 에서 병렬 2중 blind 성공 (confidence 8/10, 8.5/10). 속도 + 편향 완화 양립 |
|   **Q2** Mutation Oracle CI 포함    | **Nightly only** (`--run-mutations` 수동 또는 `schedule` workflow) | CI 시간 예산 (≤3분, SLO TL-E-4) 초과 방지. 실패 시 GitHub issue 자동 생성        |
| **Q3** `baseline_metrics.json` 포맷 | **plain JSON** (msgpack/pickle 금지)                               | `git diff` 가능 → PR 리뷰 가치가 속도 절감보다 큼. Decimal 은 문자열로 직렬화    |

**Opus Warning 반영**:

|   #    | Warning                                                       | 반영 위치                                                                                                                      |
| :----: | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **W2** | Mutation M3 (strategy.entry 반환값) 가 "P-2 or P-3" 분류 모호 | `test_trust_layer_parity.py` 주석에 "Stage 2 실측 후 재분류" 명시. 현재는 양쪽 layer 중 하나라도 포착하면 PASS (SLO ≥7/8 기준) |
| **W3** | Dogfood D-C 판정 1주 sample size 불충분                       | `docs/guides/dogfood-checklist.md` §3.3 에 "1~2주차는 관찰, **3주차부터 판정**" 단서 추가 (별도 커밋)                          |
| **W4** | Decimal `getcontext().prec` 정책 문서화 누락                  | `_tolerance.py` 파일 docstring 에 "기본 `prec = 28` 유지 — metric 범위 [1e-4, 1e1] 에서 충분" 명시                             |
| **W5** | `baseline_metrics.json` schema 에 외부 의존 버전 미기록       | `baseline_metrics.schema.json` 에 `tool_versions.pynescript / python` 필수 필드 추가. regen 시 자동 기록                       |

**Stage 2 전 남은 결정 (Gate-1 에서 확정 대상)**:

- Mutation 8 개에 **가중치** 도입 여부: **등가 가중 유지 확정** (Gate-1 codex + opus 양쪽 동의).
  근거: (1) 8/8 → 7/8 → 6/8 drift 를 트렌드로 보는 게 가치, 가중치 도입 시 해석 왜곡.
  (2) M6/M8 모두 P-3 digest diff 로 탐지는 binary — 가중치 무관.
  (3) ≥7/8 "1개 허용" 의 실용 buffer 가 가중치 없을 때 가장 선명.
- baseline_metrics 의 `schema_version` 업그레이드 (1→2) 시 **migration 정책** 부재. Stage 2 에서 v1 확정 후 v2 migration 규약 별도 ADR.

### 10.2 Decimal 문자열 정규화 규약 (Gate-1 opus W-1 반영)

Gate-1 에서 발견: `DecimalString` 패턴 `^-?\d+(\.\d+)?$` 는 `"0.0832"` / `"0.08320"` / `"0.083200000"` 모두 valid → regen 스크립트가 trailing zero 를 어떻게 출력하느냐에 따라 **git diff 가짜 변경** 발생 위험. requirements §5.2 "변경 크기 > 5% 시 PR 설명 의무" 프로세스가 노이즈로 마비 가능.

**확정 규약** (Stage 2 에서 `backend/scripts/regen_trust_layer_baseline.py` 및 `_tolerance.py` 에 반영):

1. **Decimal 직렬화 포맷**: `f"{Decimal(str(value)):.8f}"` — 고정 소수점 **8자리** 로 zero-pad.
   (예: `Decimal("0.0832")` → `"0.08320000"`, `Decimal("1.5")` → `"1.50000000"`)
2. **정수 지표** (`num_trades`, `long_count`, `short_count`): JSON `integer` 타입 그대로 (포맷 규약 없음).
3. **NaN / None 처리**: `sharpe_ratio` 등 sample 부족 시 JSON `null` — 문자열 `"NaN"` 금지.
4. **비교 시 trailing zero 무시**: `within_tolerance(Decimal(str(a)), Decimal(str(b)))` 는 Decimal 자체 같음성 기반이므로 0 수 무관.
5. **8자리 소수 선택 근거**: Bybit 최소 tick 은 8 자리 (`.00000001` BTC) → 금융 도메인 자연수. metric 범위 [1e-4, 1e1] 에서 충분한 해상도.

**영향**: Stage 2 P-3 구현 시 baseline 생성 스크립트가 이 규약 강제 + Stage 2 첫 commit 에 정규화 유틸 추가.

---

## 11. Amendment History

| 날짜           | 사유                                       | 변경                                                                                                                                                 |
| -------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-23     | 최초 초안                                  | Path β Stage 0 에서 작성. Stage 2 구현 완료 시 "구현 결과" 섹션 추가 예정                                                                            |
| 2026-04-23     | Stage 1 Design 완료                        | §8 체크 갱신 + §10.1 "Stage 1 에서 확정" (Q1/Q2/Q3 + Opus W2/W3/W4/W5 반영)                                                                          |
| **2026-04-23** | **Gate-1 PASS (codex 7.5/10 + opus 8/10)** | **§4.2 실체 정정 (`_STDLIB_NAMES + StdlibDispatcher.call`, codex W-C1) + §10.1 Mutation 등가 가중 확정 + §10.2 Decimal 정규화 규약 신규 (opus W-1)** |
