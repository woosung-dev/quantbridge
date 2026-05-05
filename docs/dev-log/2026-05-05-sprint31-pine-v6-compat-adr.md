# Sprint 31 ADR — Pine v5/v6 호환성 정책

- **상태**: Accepted
- **날짜**: 2026-05-05
- **연관 BL**: BL-159 (P2, fix), BL-160 (P3, deferred), BL-161 (P3, ADR)
- **연관 sprint**: Sprint 30 dogfood Day 3 (`docs/dev-log/2026-05-05-sprint30-master-retrospective.md` §4.2)

---

## Context

### 발견 — dogfood Day 3 first impression 손상

사용자가 Sprint 30 작업 후 새 strategy "bs" (Pine v6, `indicator='Buy Sell Signal'`, 12205 chars) 를 등록 → backtest 실행 → runtime fail.

```
PineRuntimeError: Call to 'array.new_float' not supported in current scope
  at backend/src/strategy/pine_v2/interpreter.py:880
```

### 근본 원인 — Coverage Analyzer false negative

Sprint Y1 (`docs/.../sprint_y1_coverage.md`) 에서 도입한 pre-flight Trust Layer 가 `array.*` namespace 를 catch 하지 못함:

1. `coverage.py:_KNOWN_NAMESPACES` 에 `array` / `matrix` / `map` 미등록
2. `_is_pine_namespace("array.new_float")` → `False` (사용자 변수로 오인)
3. `analyze_coverage()` 가 `array.new_float` 를 `unsupported_functions` 에서 skip
4. backtest submit gate 통과 → Celery worker 에서 interpreter 가 runtime raise

**왜 그동안 안 잡혔나**: Sprint 8a~30 dogfood corpus 6 종 (s1_pbr / s2_utbot / s3_rsid / i1_utbot / i2_luxalgo / i3_drfx) 어느 것도 `array.*` 미사용. Pine v5 까지는 array 가 niche 기능이었고, **v6 에서 type system 강화로 `array<float>` 등 generic syntax 가 표준화**되면서 신규 사용자가 자연스럽게 사용.

### Surface Trust Pillar 측면 (Sprint 30 ADR §3 mirror)

dogfood Day 3 첫 5 시나리오 중 1 시나리오가 "사용자 본인 strategy 등록 → backtest 실행" 인데, 이 entry-most 경로에서 실행 직전까지 통과한 후 worker 단에서 silent runtime fail → **first impression 가장 심각하게 손상**. Pine 호환성은 Surface Trust Pillar 의 W7 (사용자 Pine 호환성) 으로 사실상 Sprint 30 §3 surface table 신규 column.

---

## Decision

### D1 — Transpiler 공식 지원 범위 (영구)

| Pine 버전 | 지원 정도       | 정책                                                                      |
| --------- | --------------- | ------------------------------------------------------------------------- |
| v2 / v3   | **Best-effort** | `study()` declaration alias 등 supported. corpus 미보유 → 신뢰도 unknown. |
| v4        | **명시 지원**   | no-namespace alias 8개 (Sprint 21) + `security` (Sprint 29) 등 SUPPORTED. |
| v5        | **명시 지원** ★ | 본 transpiler 의 primary target. corpus 6 종 포함.                        |
| v6        | **Best-effort** | 신규 type system (array/matrix/map generic) 미지원. 사용 시 422 reject.   |

### D2 — BL-159 (Sprint 31 A 본 PR) Coverage Analyzer pre-flight 강화

- `coverage._KNOWN_NAMESPACES` 에 `array` / `matrix` / `map` 등록
- `_PINE_V6_COLLECTION_NAMESPACES` SSOT frozenset 신설 (다른 모듈에서 import 가능)
- `_UNSUPPORTED_WORKAROUNDS` 에 array.new_float / array.push 등 18 항목 안내 추가
- `_CATEGORY_PREFIXES` 에 `array.` / `matrix.` / `map.` → `syntax` (data 가 아닌 syntax 갭)
- 신규 test ≥7 건 (`test_coverage_sprint31_pine_v6.py`): array.new\_<type> catch + push/pop catch + workaround 메시지 + matrix/map generic + dogfood Day 3 사용자 패턴 시뮬레이션 + false-positive 회귀

### D3 — BL-160 (P3, deferred to Sprint 32+) array.\* 부분 지원

Trust Layer 철학상 partial-supported 보다는 명시적 reject 가 우선이지만, dogfood pain 이 누적되면 **Path δ stdlib 확장** 으로 일부 array.\* 함수를 supported 로 승격 가능:

- 후보 1차 (단일 series 로 emulate 가능): `array.new_float(0)` + `array.push` + `array.size` + `array.get(-1)` (deque-like 단일 buffer)
- 후보 제외: `array.sort` / `array.reverse` / `matrix.*` / `map.*` (paradigm 차이로 emulate 비용 큼)

**Trigger 조건**: dogfood week 단위로 `unsupported_functions` 통계상 `array.*` top 3 진입 시 Sprint 32+ 검토.

### D4 — BL-161 (본 ADR) 운영 측정 추가

- Surface Trust Pillar 표 `docs/dev-log/2026-05-05-sprint30-surface-trust-pillar-adr.md` §3 에 W7 column 추가:
  - 측정 항목: "사용자 Pine 호환성 (v6 strategy registration → backtest first response)"
  - 임계: pre-flight 차단 시 422 + workaround 안내 (silent runtime fail 0건)

---

## Consequences

### 즉시 영향

- 사용자 새 Pine v6 strategy 등록 → backtest submit 시 422 + 친절 안내 (interpreter runtime fail 0)
- FE BacktestForm / detail page 의 422 처리 패턴 (Sprint Y1 D2) 이 array.\* 안내까지 자연 노출

### Trade-off

- 일부 Pine v6 strategy 가 단순 array.\* 사용만으로 backtest 차단 — **단기 dogfood pain ↑**, **장기 Trust Layer 정합 ↑** (silent fail 보다 명시 reject 가 우월)
- BL-160 deferred 로 인해 array.\* 사용 strategy 는 Sprint 32+ 까지 dogfood 영역 외

### 후속 의무

1. Sprint 31 dogfood Day 4 (self-assessment) 에서 W7 column 측정 (사용자 본인 strategy 등록 PASS rate)
2. Sprint 32+ kickoff 시 array.\* unsupported top 3 통계로 BL-160 재평가
3. SSOT 4 invariant audit 무결성 — 본 sprint 의 \_PINE_V6_COLLECTION_NAMESPACES 추가는 unsupported namespace 등록이라 SUPPORTED_FUNCTIONS 영향 0

---

## References

- Sprint Y1 회고: `docs/.../sprint_y1_coverage.md` — Trust Layer 패턴 originator
- Sprint 29 ADR: `docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md` — Trust Layer 위반 명시 패턴 reference
- Sprint 30 master retro: `docs/dev-log/2026-05-05-sprint30-master-retrospective.md` §4.2 dogfood Day 3
- Sprint 30 Surface ADR: `docs/dev-log/2026-05-05-sprint30-surface-trust-pillar-adr.md` — W7 column 추가 trigger
