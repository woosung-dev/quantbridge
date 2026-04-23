# 2026-04-23 Documentation Audit — Path β Stage 0 메타 회고

> **작성일:** 2026-04-23
> **맥락:** Path β 진행 중 "코드 작성 전 문서 선행" 사용자 지시 → Stage 0 로 정비 수행
> **산출물:** 9 파일 신규 + 5 파일 수정 (ADR-010 rename 포함)
> **관련 플랜:** `~/.claude/plans/file-users-woosung-project-agy-project-q-humming-dewdrop.md`

---

## 1. 감사 트리거

Path β (Trust Layer CI) 를 본격 착수하기 전에 사용자가 명시:

> "바로 코드를 작성하는게 아니라 docs/ 문서를 작성해줄래? 해당 부분 기존에 빼먹어서 문서화가 안된부분도 있을텐데 해당 부분에 대한것도 가능하면 업데이트 해주면 좋겠어"

즉 **2 개의 요구**:

1. Path β 자체의 설계 문서를 먼저 쓸 것 (구현 전 ADR 확정)
2. 그동안 누락된 문서 부채를 함께 정비할 것

Explore 에이전트로 `docs/` 전체를 스캔한 결과, **13 개 sprint (7d, 8b, 8c, Y1, FE-01~04, FE-A~F, X1+X3) 가 `dev-log/` 또는 `superpowers/reports/` 에 회고 기록 없음** + **ADR-010 번호 중복** 발견.

---

## 2. 수행 작업

### 2.1 신규 (9 파일)

| 파일                                                    |   분류    | 성격                     |
| ------------------------------------------------------- | :-------: | ------------------------ |
| `dev-log/013-trust-layer-ci-design.md`                  |    ADR    | Path β 핵심 설계         |
| `dev-log/014-sprint-8b-8c-pine-v2-expansion.md`         | 회고 ADR  | 합본 (중복 제거)         |
| `dev-log/015-sprint-7d-okx-sessions.md`                 | 회고 ADR  | 단일 sprint              |
| `dev-log/016-sprint-y1-coverage-analyzer.md`            | 회고 ADR  | Trust Layer prerequisite |
| `dev-log/017-fe-polish-bundle-1-2-retro.md`             | 회고 ADR  | 10 sprint 묶음           |
| `04_architecture/trust-layer-architecture.md`           | 아키텍처  | Tier-2 의 실용화         |
| `01_requirements/trust-layer-requirements.md`           | 요구사항  | SLO 정량화               |
| `guides/dogfood-checklist.md`                           |  가이드   | 일일 기록 시트           |
| `superpowers/reports/2026-04-23-documentation-audit.md` | 메타 회고 | 본 문서                  |

### 2.2 수정 (5 파일)

| 파일                                             | 변경                                                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `dev-log/010-dev-cpu-budget.md` → `010a-*`       | rename (번호 중복)                                                                               |
| `dev-log/010-product-roadmap.md` → `010b-*`      | rename (번호 중복)                                                                               |
| `00_project/vision.md`                           | 010 → 010b 참조 갱신 + ADR 범위 001~010 → 001~012                                                |
| `00_project/roadmap.md`                          | 010 → 010b 참조 갱신 (2 곳)                                                                      |
| `04_architecture/pine-execution-architecture.md` | Y1 Coverage Analyzer (§2.0.4a) + 3-Track dispatcher (§2.1.6a) 섹션 추가 + 용어집 확장 + 변경이력 |
| `TODO.md`                                        | Path β Stage 0/1/2 섹션 + Y1 완료 반영 + LLM 후보 L-1/L-2/L-3 + Path γ/δ 후보                    |
| `.ai/stacks/nextjs/frontend.md`                  | §3 "React Hooks 안전 규칙 H-1/H-2/H-3" 섹션 추가 (LESSON-004/005/006 승격)                       |
| `.ai/project/lessons.md`                         | LESSON-004/005/006 에 "[승격 완료 2026-04-23]" 표시                                              |

### 2.3 작업 경로 (플랜 대비)

| 플랜 Wave                     | 항목 수 |          실제 완수           |
| ----------------------------- | :-----: | :--------------------------: |
| Wave A (신규 Trust Layer 4건) |    4    |             4 ✅             |
| Wave B (누락 회고 4~5건)      |    5    | 5 ✅ (회고 4 + 본 감사 보고) |
| Wave C (정리 · 동기화 5건)    |    5    |             5 ✅             |
| 총                            |   14    |          **14 ✅**           |

---

## 3. 발견

### 3.1 문서 부채 규모 (감사 전)

- 13 sprint 가 ADR 또는 완료보고서 없이 merge
- `dev-log/` 번호 체계에 충돌 1 건 (`010-*` 2 개)
- Sprint Y1 (PR #61) 이 merge 됐는데 TODO.md `현재 세션 작업` 라인이 갱신 안 된 상태
- `04_architecture/pine-execution-architecture.md` 가 Sprint 8c 의 3-Track dispatcher 와 Y1 Coverage Analyzer 를 반영 안 함

### 3.2 관찰 — "왜 문서 부채가 쌓였는가"

| 원인                                                                         | 관찰                                                                                                           |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Sprint 완료 직후 **의무적 회고 단계 부재**                                   | `/superpowers:writing-plans` 는 sprint **시작** 전 plan 을 강제하지만, sprint **완료** 시 회고는 강제되지 않음 |
| 자율 병렬 sprint (FE-A~F) 는 squash merge 되어 PR description 에만 내용 남음 | PR 본문 ≠ 검색 가능한 `docs/` 문서. 시간 지나면 context 유실                                                   |
| ADR 번호 수동 할당                                                           | sprint 병렬 실행 시 같은 번호 취득 위험 — 실제 010 중복이 그렇게 발생                                          |
| memory (`MEMORY.md`) 와 `docs/dev-log/` 이중 기록                            | memory 는 "conversation 용", dev-log 는 "repo 영구 기록". 둘을 동시에 유지 안 하면 한쪽 drift                  |

### 3.3 문서 작성 원칙 (본 감사에서 준수)

- 한국어 (CLAUDE.md 언어 정책)
- 사실 vs 가정 구분 (`[가정]`, `[확인 필요]` 라벨)
- 기존 문서 확장 우선, 신규 파일은 역할이 명확할 때만
- 교차 참조는 상대 경로, 깨진 링크 없게
- 회고 ADR 은 **결정 근거 + 학습 중심** — PR diff 복붙 금지

---

## 4. 제안 — 향후 sprint 말 자동 회고 템플릿

### 4.1 체크리스트 (sprint 종료 시 의무)

- [ ] `dev-log/NNN-sprint-<id>-retro.md` 작성 (2~3 페이지)
  - 배경, 결정 요약, 테스트 결과, 학습 (L-1, L-2, ...), 영향, 다음 단계
- [ ] `TODO.md` 의 Sprint 섹션에 완료 표시 + PR 번호
- [ ] Memory (`MEMORY.md`) 에 한 줄 항목 추가 (있을 때)
- [ ] 관련 아키텍처 문서에 섹션 추가 (필요 시)

### 4.2 ADR 번호 할당 규약

- **단일 sprint**: 다음 번호 사용 (예: 현재 017 다음 = 018)
- **복수 sprint 합본**: "A-B 합본" 표기 (예: 014 = 8b+8c)
- **번호 충돌 발견 시**: 즉시 rename (`NNNa` / `NNNb`) + 모든 참조 일괄 갱신

### 4.3 자동화 후보 (H2 이후 검토)

- **pre-merge hook**: PR 에 `docs/dev-log/NNN-*` 또는 `docs/superpowers/reports/` 포함 여부 검증 (skip label 허용)
- **ADR 번호 lint**: `ls docs/dev-log/ | cut -c1-3 | sort | uniq -d` 가 empty 아니면 CI red
- **memory → dev-log 변환 스크립트**: `MEMORY.md` 의 sprint 완료 항목에서 회고 ADR 초안 생성

---

## 5. 회고 (메타의 메타)

### L-1: 코드 선행 ↔ 문서 선행 의 트레이드오프

- 코드 선행 장점: 실제 구현 세부가 문서에 자연스럽게 반영됨
- 문서 선행 장점: ADR 의 **결정 근거** 가 구현 중 변질되지 않음. Path β 의 Tier-2 재정의 (P-4 → 미래 이연) 같은 중요한 판단이 문서로 먼저 명시
- **판단**: 아키텍처 급 결정 (ADR) 은 **문서 선행**, 개별 기능 구현은 코드 선행

### L-2: 누락 회고를 몰아서 쓰는 피로감

- 13 sprint 를 한 번에 몰아서 회고 작성 → 작성자 기억력 부담 + memory/MEMORY.md 를 강하게 의존
- **교훈**: sprint 말 의무 회고 (§4.1) 체계화가 필수. "밀리면 아예 안 쓴다" 의 tragedy of commons

### L-3: 아키텍처 survey 의 효용성

- `2026-04-23-architecture-survey.html` 이 Path β 의 결정 근거로 활용됨
- 이런 survey 를 **sprint 끝마다** 축소 버전으로 생성하면 다음 sprint 기획 품질 ↑
- H2 이후 도입 검토

### L-4: "사용자 지시" 로부터 얻은 레슨

- 사용자가 `ExitPlanMode` 를 reject 하며 "docs 먼저" 를 명시하지 않았다면 구현 직행 → 본 감사 누락
- **교훈**: 대규모 아키텍처 sprint 시작 전, AI 가 **자율적으로** "문서 현황 감사" 를 제안해야 함. 사용자 상기 의존은 취약

---

## 6. Gate-0 준비 상태

- [x] 14 항목 모두 완수
- [x] 번호 충돌 0 건 확인
- [x] 참조 링크 의도된 것만 갱신 (codex-eval 과거 artifact 는 역사 보존)
- [x] ADR 템플릿 일관 (ADR-013~017 모두 상태/일자/관련 ADR/변경이력 섹션 포함)
- [ ] Gate-0 evaluator (codex 단일) 실행 → 다음 단계

---

## 7. 다음 단계

- [ ] Gate-0 실행 — codex evaluator (G0-A 마크다운 lint, G0-B ADR 정합, G0-C 번호 충돌, G0-D 참조 링크, G0-E dogfood 중복, G0-F 통합 판정)
- [ ] Gate-0 통과 시 Stage 1 (Design, Day 3) 진입
- [ ] H2 이후: §4 자동화 후보 검토 (pre-merge hook, ADR lint)
