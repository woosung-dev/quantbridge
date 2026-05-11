# Sprint 57 Close-out — BL-234 + BL-237 Optimizer Polish

> **Date:** 2026-05-11
> **Branch:** `feat/sprint-57-optimizer-polish` → main @`38016bf` (local merge)
> **Active BL 변화:** 91 → 89 (BL-234 Resolved + BL-237 Resolved, -2 net)

---

## 1. 완료 요약

Sprint 55/56에서 의도적으로 남긴 Optimizer 3가지 누락 기능을 활성화하고, cap 50 제한 완화를 위한 인프라를 구축했다.

| BL     | 기능                                                                                | status          |
| ------ | ----------------------------------------------------------------------------------- | --------------- |
| BL-234 | Bayesian prior=normal sampler + CategoricalField one_hot + Genetic selection_method | **✅ Resolved** |
| BL-237 | optimizer_heavy Celery queue + soft_time_limit=600 + cap 50→100 + Docker worker     | **✅ Resolved** |

---

## 2. 기술 결정 기록

### 2.1 prior=normal inject 패턴

skopt는 `prior="normal"`을 지원하지 않는다. 두 가지 접근이 있었다:

- **A) custom skopt Dimension 서브클래스**: 복잡도 높음, skopt 내부 의존
- **B) ask() 후 inject**: `optimizer.ask()` 항상 호출 (내부 `_n_initial_points` 정상 감소), random phase에서만 normal-prior 차원값을 N(loc, scale) clip으로 교체

**채택: B**. 이유: ask() 호출 유지로 skopt 상태 일관성 보장. 코드 변경 최소.

### 2.2 \_roulette_select rank-based

fitness-proportionate(실제 objective 비율) 대신 rank-based 채택:

- fitness-proportionate: 음수 fitness 시 음수 확률 발생 → 처리 복잡
- rank-based: 항상 양수 확률, 수치 안정성 보장

### 2.3 cap 50→100 전제조건

`optimizer_heavy` dedicated worker 없이 100 eval = default queue 블로킹 위험 (100 eval × ~5s = 500s+). BL-237 먼저 인프라 구축 후 상수 변경 순서로 진행.

### 2.4 alembic migration 없음

`CategoricalField.encoding`, `genetic_selection_method` 모두 `param_space` JSONB 필드 내부. DB column 변경 없음. Pydantic default 값으로 backward-compat 보장.

---

## 3. 검증 evidence

```
BE optimizer:  139 passed (baseline 115 → +24 신규, 0 fail)
FE vitest:     680 passed (0 fail)
BE ruff:       all checks passed
BE mypy:       no errors (cast(Decimal, ...) 패턴으로 type-safe)
FE tsc:        0 errors
FE lint:       0 errors
Docker:        backend-optimizer-heavy 서비스 포함 확인
alembic:       migration 없음
```

---

## 4. LESSON-067 5차 검증

Sprint 57 단일 worker 실측 시간 (7 Slice):

- estimate: ~6-12h (BL-234 S ~4-8h + BL-237 S ~2-4h)
- 실측: **~3-4h** (wall-clock)

LESSON-067 후보 누적: Sprint 39 / 54 / 55 / 56 / 57 = **5/5 검증**.

패턴: 단일 worker + 명확한 scope + 기존 패턴 재사용 = estimate의 30~50% 실측.

---

## 5. 커밋 히스토리

```
38016bf feat(sprint57): BL-234 + BL-237 Optimizer Polish — merge
aa2dc05 docs(optimizer): ADR-013 §9 amendment — BL-234 + BL-237 Sprint 57
0a4fb93 feat(optimizer): BL-234+237 FE — genetic_selection_method form + max_evaluations cap 100
b8a286b feat(optimizer): BL-237 Docker — optimizer_heavy dedicated worker (prefork, concurrency=1)
596af61 feat(optimizer): BL-237 Celery — optimizer_heavy queue + soft_time_limit=600 + cap 50→100
b47f6a8 feat(optimizer): BL-234 Genetic — roulette selection (rank-based)
93a7c03 feat(optimizer): BL-234 Bayesian — prior=normal inject sampler + CategoricalField one_hot transform
ac7d736 feat(optimizer): BL-234 schema — CategoricalField.encoding + genetic_selection_method + E1 guard
```

---

## 6. Sprint 58 다음 분기

Day 7 인터뷰 (2026-05-16) 결과 따라:

- NPS ≥7 + bug 0 + 본인 의지 → Beta 본격 (BL-070~075)
- Optimizer 계속 → BL-235 N-dim viz / BL-236 objective 자유화
- mainnet → BL-003/BL-005
