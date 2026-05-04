# Sprint 종료 Sweep 템플릿

> **목적:** Sprint 종료 시 회고 + dual metric 측정 + dev-log 작성을 표준화한다.
> **짝:** [`sprint-kickoff-template.md`](./sprint-kickoff-template.md) (시작 시 사용).
> **도입:** Sprint 28 Slice 1a (Phase C.1 prototype) — 첫 검증 케이스.
> **승격 경로:** Sprint 29+ 회고에서 동일 frontmatter 4 신규 필드 적용 시 영구 규칙 승격.

## 사용법

새 sprint 회고 작성 시 본 템플릿을 `docs/dev-log/{YYYY-MM-DD}-sprint{N}-{theme}.md` 로 복사 + frontmatter 채움. 본문 섹션은 sprint 별 조정.

---

## Frontmatter (필수 8 필드)

```markdown
> **Sprint 번호:** Sprint N
> **시작일:** YYYY-MM-DD
> **종료일:** YYYY-MM-DD
> **Branch:** stage/<theme> 또는 feat/<theme>
> **PR:** #N (또는 cascade: #N1 / #N2 / ...)
> **Sprint type:** A (신규 기능) / B (BL fix risk-critical) / C (dogfood hotfix 압축) / D (docs only 면제) ← Sprint 28 신규 정책
> **office-hours 진행 여부:** Y (Step 0 office-hours 재진행 — Q4/Q5 답 부분 무효화 시) / N ← Sprint 28 신규 정책
> **Self-assessment:** N/10 (근거 ≥3 줄, 본문 §6 참조)
> **신규 BL count:** P0=N / P1=N / P2=N / P3=N (sprint 안 새로 발견된 항목만)
> **기존 P0 잔여:** sprint 진입 시점 vs 종료 시점 (≥1 감소 = dual metric 통과)
```

> **Sprint type 정책 (영구 규칙 후보, Sprint 28 도입):**
>
> - **Type A** (신규 기능 / 도메인 확장) → brainstorming **의무** 45-60분 + writing-plans + codex G0
> - **Type B** (BL fix / technical debt risk-critical) → brainstorming **권고** 30분 + writing-plans + codex G0
> - **Type C** (dogfood hotfix) → brainstorming **압축** 15분 + writing-plans + codex G0
> - **Type D** (docs / cleanup only) → brainstorming **면제** + writing-plans 직접 + codex G0 면제

## 본문 섹션

### §1 — 목표 + 결과물

- 진입 시점 목표 (kickoff 회의록 또는 plan 인용)
- 실제 결과물 (Slice / PR / commit / tests count)
- 격차 사유 (시간 over-run / scope 변경 / blocker 등)

### §2 — Codex Gates (sprint 단위)

| Gate                          | 적용 여부     | 결과 (PASS/FAIL) | 결과 링크 / 발견 P1 / P2  |
| ----------------------------- | ------------- | ---------------- | ------------------------- |
| **G.0 Plan eval**             | Y/N (Type 별) | PASS / FAIL      | (artifact 또는 commit)    |
| **G.2 Implementation review** | Y/N           | PASS / FAIL      | (PR comment 또는 dev-log) |
| **G.4 P2 issue 처리**         | Y/N           | PASS / FAIL      | (BL 등록 vs 즉시 fix)     |

> **codex hang 발생 시:** Claude self-review (G0 evaluator pattern adapted) 가 fallback. 기록에 명시.

### §3 — dev-log 링크 + 관련 문서

- 본 sprint 의 plan: `docs/superpowers/specs/...` 또는 `~/.claude/plans/...`
- 관련 ADR: `docs/dev-log/...`
- 관련 BL: `docs/REFACTORING-BACKLOG.md` Resolved/신규 등록

### §4 — BL 신규 등록

| BL ID  | 분류 | 설명 | 발견 시점          | 우선도  |
| ------ | ---- | ---- | ------------------ | ------- |
| BL-XXX | P?   | ...  | Slice N or Stage N | trigger |

### §5 — Lessons 신규 (영구 규칙 승격 후보)

| Lesson 번호 | 내용 | 발견 sprint / context | 승격 여부                                            |
| ----------- | ---- | --------------------- | ---------------------------------------------------- |
| LESSON-XXX  | ...  | ...                   | `.ai/project/lessons.md` 또는 `.ai/common/global.md` |

### §6 — Dual Metric 측정 (의무, Sprint 28 도입)

| Metric                             | 측정 결과                                             | 통과 기준            | PASS/FAIL |
| ---------------------------------- | ----------------------------------------------------- | -------------------- | --------- |
| **Self-assessment**                | N/10 + 근거 (3 줄)                                    | ≥7 (H1→H2 gate)      | ✅/❌     |
| **신규 BL count (sprint 안 발견)** | P0=N / P1=N                                           | P0=0 신규, P1≤2 신규 | ✅/❌     |
| **기존 P0 잔여 (cumulative)**      | 진입 N건 → 종료 N건                                   | ≥1 감소              | ✅/❌     |
| **divergence 검출**                | self-assess ≥7 AND 신규 P0=0 AND 기존 P0 잔여 ≥1 감소 | 셋 모두 PASS         | ✅/❌     |

> **Sprint 27 회피 사례:** self-assess 8.0 + 4 P0 BL divergence 시 sprint 미완 판정. dual metric 도입 이유.

### §7 — Sprint type / office-hours / 메타-방법론 self-check

- [ ] Sprint type 분류 (A/B/C/D) frontmatter 명시
- [ ] office-hours 재진행 여부 (Q4/Q5 답 3개월+ 경과 + dogfood 누적 시) Y/N 명시
- [ ] dual metric 측정 + retrospective 작성
- [ ] 메타-방법론 정책 4종 적용 검증 (Sprint type / office-hours / dual metric / Era 1 brainstorming 회복)

### §8 — Trailer (다음 sprint 후보)

- 다음 sprint 후보 (이관 BL / 신규 도메인 / Beta path 결정)
- TODO.md 갱신 (메타 헤더 4 필드 — Last Updated / Active Sprint / Recent BLs / Next Trigger)
- INDEX.md 갱신 (sprint 매트릭스 추가)
- 본 회고 dev-log 자체가 sprint-template.md 의 검증 케이스인지 명시

---

## 검증 (sprint-template prototype)

본 템플릿이 처음 사용된 회고 = **Sprint 28 회고** (2026-05-04 ~ 2026-05-N). 회고 작성 시:

- frontmatter 4 신규 필드 (sprint type / office-hours Y/N / dual metric / 신규 BL count) 모두 채움
- §6 dual metric 측정 결과 PASS/FAIL 명시
- §7 메타-방법론 self-check 모두 통과

Sprint 29+ 회고에서 동일 패턴 적용 시 영구 규칙 승격.
