# Trust Layer 요구사항 · SLO · 수용 기준

> **SSOT (2026-05-04 cleanup):** 본 문서가 **Trust Layer 요구사항/SLO 의 단일 진실 원천**. 아키텍처: [`04_architecture/trust-layer-architecture.md`](../04_architecture/trust-layer-architecture.md) (3-Layer Parity 설계), ADR: [`dev-log/013-trust-layer-ci-design.md`](../dev-log/013-trust-layer-ci-design.md) (결정 근거).
>
> **상태:** Path β Stage 0 초안 (2026-04-23). Stage 2 구현 + Gate-2 통과 시 **확정**.
> **상위 문서:** [`04_architecture/trust-layer-architecture.md`](../04_architecture/trust-layer-architecture.md), [`dev-log/013-trust-layer-ci-design.md`](../dev-log/013-trust-layer-ci-design.md), [`dev-log/016-sprint-y1-coverage-analyzer.md`](../dev-log/016-sprint-y1-coverage-analyzer.md)
> **관련 Sprint:** Path β · 관련 PR: Stage 2 에서 작성 예정
> **상호 참조:** [`trading-demo-baseline.md`](./trading-demo-baseline.md) (dogfood 체결 baseline), [`pine-coverage-assignment.md`](./pine-coverage-assignment.md) (coverage SSOT)

---

## 1. 대상 범위

Trust Layer 요구사항은 **두 축** 을 포괄한다:

| 축              | 대상                                             | 출발 Sprint        | SLO 담당 섹션 |
| --------------- | ------------------------------------------------ | ------------------ | :-----------: |
| 사용자 facing   | Pre-flight Coverage Analyzer (Y1), 422 Reject UX | Sprint Y1 (PR #61) |      §2       |
| 엔지니어 facing | 3-Layer Parity CI (P-1/2/3) + Mutation Oracle    | Path β             |    §3, §4     |

본 문서는 **축 2 (엔지니어 facing)** 에 집중한다. 축 1 SLO 는 간단히 §2 에 참조.

---

## 2. 축 1 — 사용자 facing SLO (Y1 Sprint, 이미 충족)

|   ID   | 요구사항                                                                                     | 측정                                                        |       현재 상태       |
| :----: | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | :-------------------: |
| TL-U-1 | 전략 등록 시 unsupported 함수/속성을 **사전에** 사용자에게 노출                              | `parse_preview` 응답의 `coverage.unsupported_builtins` 필드 |        ✅ (Y1)        |
| TL-U-2 | `is_runnable=false` 전략의 backtest 요청은 **422 StrategyNotRunnable** 로 차단               | `POST /backtests` 응답 status code                          |        ✅ (Y1)        |
| TL-U-3 | 사용자 facing 에러 메시지는 한국어 + 미지원 항목 목록 + 문서 링크 포함                       | UX 검수                                                     | ✅ (Y1, FE 경고 박스) |
| TL-U-4 | `SUPPORTED_FUNCTIONS` 갱신 시 사용자에게 즉시 반영 (재파싱 불필요 — 다음 parse_preview 부터) | 수동 검증                                                   |          ✅           |

**Y1 종료 조건 (이미 달성)**: 6 corpus 중 i3_drfx 가 명확히 422 reject, 나머지 5 는 green parse.

---

## 3. 축 2 — 엔지니어 facing SLO (Path β 대상)

### 3.1 SLO 매트릭스

|     ID     | 요구사항                                                        | 측정법                                      |                 목표값                  | Gate | 비고                       |
| :--------: | --------------------------------------------------------------- | ------------------------------------------- | :-------------------------------------: | :--: | -------------------------- |
| **TL-E-1** | P-1 AST Shape Parity 6/6 corpus green                           | `pytest test_pynescript_baseline_parity.py` |                100% pass                | G2-A | pynescript==0.3.0 기준     |
| **TL-E-2** | P-2 Coverage SSOT Sync 양방향 assertion green                   | `pytest test_coverage_ssot_sync.py`         |                100% pass                | G2-A | 리플렉션 기반              |
| **TL-E-3** | P-3 Execution Golden 상대 오차 < 0.1% **or** 절대 < 0.001       | `pytest test_execution_golden.py`           |   6 corpus (i3_drfx 제외 5) 전원 통과   | G2-A | Decimal-first              |
| **TL-E-4** | Trust Layer CI step 실행 시간                                   | GitHub Actions 실측                         |                  ≤ 3분                  | G2-B | 초과 시 subset marker 도입 |
| **TL-E-5** | Mutation Oracle 포착률                                          | `pytest --run-mutations`                    |                  ≥ 7/8                  | G2-C | 메타 게이트                |
| **TL-E-6** | Baseline regen 스크립트는 `--confirm` 없이 실패                 | subprocess 테스트                           |              exit code ≠ 0              | G2-D | 오남용 방지                |
| **TL-E-7** | 기존 trading/backtest suite regression 0건                      | `pytest -v backend/tests/` 전체             |               0 failures                | G2-F |                            |
| **TL-E-8** | `coverage.SUPPORTED_FUNCTIONS` 와 `stdlib` 실제 바인딩 delta 0  | P-2 자동                                    |                delta = 0                | G2-A | Y1 prerequisite 정합       |
| **TL-E-9** | Trust Layer 관련 문서 (ADR-013, 아키텍처, 요구사항) 갱신 동기화 | G2-G 수동                                   | reviewer 가 문서만 읽고 regen 실행 가능 | G2-G |                            |

### 3.2 허용 오차 공식 (Decimal-first)

```python
ABS_TOL = Decimal("0.001")
REL_TOL = Decimal("0.001")  # 0.1%

def within_tolerance(actual, expected):
    abs_err = abs(Decimal(str(actual)) - Decimal(str(expected)))
    if abs_err < ABS_TOL:
        return True
    if Decimal(str(expected)) == 0:
        return False
    return (abs_err / abs(Decimal(str(expected)))) < REL_TOL
```

**원칙**: `max(절대 0.001, 상대 0.1%)`. 이유:

- 작은 값 (예: `profit_factor ≈ 0.00001`) 은 상대 오차가 과민 반응
- 큰 값 (예: `total_return ≈ 10.0`) 은 절대 오차가 과소 반응
- Sprint 4 D8 Decimal-first 합산 규칙 연장 — 모든 중간 계산 `Decimal(str(x))` 경유

---

## 4. 수용 기준 (Acceptance Criteria)

### 4.1 Path β 완료 조건 (Gate-2 통과)

모든 TL-E-1 ~ TL-E-9 을 **동시 만족**. 어느 하나라도 실패 시 **main merge 금지**.

#### 4.1.1 Mutation 측정 불가 = scope-reducing 정책 (BL-057, Sprint 46, ADR-013 follow-up)

**규칙:** Mutation Oracle (TL-E-5) 가 새 P-1/2/3 layer 또는 신규 mutation 케이스에서 **측정 불가** (instrumentation 실패 / sandbox eval 미가용 / coverage 도구 mismatch) 로 판정될 경우, **해당 layer 또는 케이스를 scope-reducing** 한다 — Gate-2 hard-block 으로 승격하지 않는다.

**근거 (3):**

1. **불확실성 회피**: 측정 불가 ≠ mutation 미감지. Hard-block 승격 시 false-positive 차단으로 PR throughput 손상.
2. **CLAUDE.md ADR-013 정합**: "측정 불가능한 SLO 는 PR 차단 사유가 될 수 없다" 원칙의 mutation domain 적용.
3. **선례**: Sprint Path β Stage 2c 1차 (2026-04-23, 4/8 감지) → 2차 (2026-04-23, 8/8 감지) — "측정 가능 영역만 측정" 으로 점진 확장하여 false-fail 0 달성.

**적용 절차:**

1. Mutation 측정 실패 layer / 케이스 식별 → `docs/01_requirements/trust-layer-requirements.md` §4.2 표에 1 row 추가 (SLO + 실패 사유 + scope-reducing 결정).
2. `pytest.mark.skip(reason="mutation instrumentation unavailable — see TL §4.1.1")` 으로 명시적 skip.
3. nightly Mutation Oracle 보고서에서 **분모 차감** (4/8 → 4/7 처럼 측정 가능 mutation 기준 비율 산정).
4. 분기별 review 시 instrumentation 복구 가능성 재평가 (skip 해제 시도).

**Anti-pattern:** Mutation 미감지 = Gate-2 fail 자동 적용 (false-fail 양산 → developer trust 손상).

**Related:** ADR-013 (CLAUDE.md), [B5-ADR](../04_architecture/architecture-conformance.md#b5-adr), [BL-057](../REFACTORING-BACKLOG.md#bl-057)


### 4.2 Degrade 허용 (SLO 초과 시)

| SLO                      | 실패 시 조치                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------- |
| TL-E-4 (실행 시간)       | `@pytest.mark.trust_layer_full` marker 도입. PR 은 subset (s1+s2+i2), nightly 는 full |
| TL-E-5 (mutation < 7/8)  | 어느 layer 가 못 잡았는지 식별 → P-1/2/3 강화 1 iter. 그래도 실패 시 mutation 재설계  |
| TL-E-8 (SSOT drift 발견) | 즉시 coverage.py 또는 stdlib 중 옳은 쪽 기준 수정. PR 에 diff 포함                    |

### 4.3 Hard Block (타협 불가)

- TL-E-1, TL-E-2, TL-E-3, TL-E-7, TL-E-9 — 실패 시 Path β 미완료.
- TL-E-6 — `--confirm` 우회 버그 발견 시 즉시 hotfix.

---

## 5. 모니터링 & 알림

### 5.1 CI 단계별

| 단계                             | 알림                                                            | 대상        |
| -------------------------------- | --------------------------------------------------------------- | ----------- |
| P-1/2/3 fail                     | GitHub PR status red + 실패 layer 로그                          | PR 작성자   |
| Mutation Oracle < 7/8 (nightly)  | GitHub issue 자동 생성 (`trust-layer/mutation-regression` 라벨) | 개발자 본인 |
| pynescript 업그레이드로 P-1 fail | PR 내 artifact 에 AST diff 업로드                               | PR 작성자   |

### 5.2 Baseline 변화 감시

- `baseline_metrics.json` 의 git diff 는 **항상 PR 리뷰 대상**
- 변경 크기 > 5% (metric 별) 시 PR 설명에 **변경 근거** 명시 의무
- 악의적/무의식적 baseline 우회 (`--confirm` 없이 직접 편집) 을 방지하려면 pre-commit hook 또는 CODEOWNERS 적용 (Path β 외 검토)

---

## 6. 운영 절차 (Stage 2 완료 후)

### 6.1 일상 PR

1. 개발자가 `stdlib.py` 수정 PR 작성
2. CI 의 Trust Layer step 이 자동 실행 (~3분)
3. P-3 red → `python scripts/regen_trust_layer_baseline.py --confirm --corpus <id>` 실행
4. `git diff baseline_metrics.json` 로 의도한 변경만 포함됐는지 확인
5. diff 를 PR 에 commit, 변경 근거를 PR description 에 명시
6. 리뷰어 approval 후 merge

### 6.2 pynescript 버전 업그레이드

1. `pyproject.toml` 업그레이드 PR
2. P-1 red 예상 → AST diff 분석
3. Semantic 영향 없으면: `baseline.json` regen + PR 에 근거 서술
4. Semantic 영향 있으면: interpreter 대응 → P-2/3 모두 regen

### 6.3 Nightly Mutation Oracle

- GitHub Actions `schedule` (매일 02:00 UTC) workflow
- 실패 시 issue 자동 생성
- Gate-2 TL-E-5 의 지속 감시

---

## 7. 명시적 비요구 사항 (Out of Scope — Path β)

- **P-4 (PyneCore transformers 이식본 vs QB 실행 결과)** — Path γ 이후 (Apache 2.0 이식 3~4주)
- **MTF (`request.security`) 검증** — pine_v2 미구현 기능. Path γ+ 대상
- **실시간 재실행 (live mode) 비교** — 현재 event_loop 는 historical 만 지원
- **TradingView 공식 결과와의 비교** — ToS 회색지대 + 수동 비용. 분기 1회 샘플 10개 정도만
- **FE 레벨 Trust Layer** (사용자가 backtest 결과 신뢰도를 UI 에서 확인) — Sprint Y2 후보
- **LLM 기반 Trust 보조** (L-1 Pine 요약, L-2 결과 해석) — 분리된 Sprint 후보

---

## 8. 용어집

| 용어                   | 정의                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------ |
| **3-Layer Parity**     | P-1 AST Shape + P-2 Coverage SSOT Sync + P-3 Execution Golden 의 묶음                |
| **Execution Golden**   | 6 corpus × 고정 OHLCV 에서 얻은 metrics 의 스냅샷 baseline                           |
| **Mutation Oracle**    | P-1/2/3 의 감지력을 메타 검증하는 8개 hand-crafted mutation 세트                     |
| **SSOT Sync**          | `coverage.py` 의 SUPPORTED 집합 ⟺ `stdlib/interpreter` 실제 구현의 양방향 일치 검증  |
| **P-4**                | PyneCore transformers 이식본을 reference oracle 로 활용하는 미래 layer (Path γ 이후) |
| **`--confirm` 게이트** | Baseline regen 시 명시적 승인 플래그. 없으면 스크립트 실패                           |

---

## 9. 변경 이력

| 날짜       | 사유      | 변경                                                           |
| ---------- | --------- | -------------------------------------------------------------- |
| 2026-04-23 | 최초 초안 | Path β Stage 0. Stage 2 완료 시 TL-E-1~9 실측값 부록 추가 예정 |
