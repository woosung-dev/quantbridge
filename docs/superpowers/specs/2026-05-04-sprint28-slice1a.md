# Sprint 28 Slice 1a — Phase C workflow enforcement (Type D, brainstorming 면제)

> **Type:** D (docs only — brainstorming 면제, codex G0 면제)
> **시간:** 2-3h 구현 (writing-plans 직접)
> **Branch:** sub-branch from `stage/h2-sprint28-comprehensive` → PR base = stage
> **Plan source:** [`~/.claude/plans/dreamy-dancing-pizza.md`](file:///Users/woosung/.claude/plans/dreamy-dancing-pizza.md) §3 Phase C (Task C.1~C.6)

## Goal

methodology Stage 1~6 적용 격차를 자동/반자동으로 봉합. 향후 sprint 가 자연스럽게 codex G0/G2/G4 기록 + dual metric 측정을 남기도록 hook + template 정비.

## Tasks (6 task, 약 2h 15min)

### T1 — sprint-template.md 신규 (30분)

**File:** `docs/guides/sprint-template.md` (신규)

**내용:**

- Frontmatter (sprint 번호 / 시작일 / 종료일 / branch / PR 링크 / **sprint type (A/B/C/D)** / **office-hours 진행 여부 (Y/N)** / self-assessment 점수 / 신규 BL count P0/P1)
- 본문 섹션 (목표 / 결과물 / **codex G.0~G.4 결과 슬롯** / dev-log 링크 / BL 신규 등록 / lessons 신규 등록 / **dual metric 측정 결과**)
- Trailer (다음 sprint 후보 / TODO.md 갱신 / INDEX.md 갱신 reminder)
- **prototype 검증:** 본 sprint (Sprint 28) 회고 작성 시 첫 사용 사례

**검증:** `wc -l docs/guides/sprint-template.md` ≥ 80 + frontmatter 4 신규 필드 (sprint type / office-hours Y/N / dual metric / 신규 BL count) 모두 존재

### T2 — bl-audit-checklist.md 신규 (20분)

**File:** `docs/guides/bl-audit-checklist.md` (신규)

**내용:**

- sprint 시작 시 review 의무 항목 (P0 BL trigger 도래 / P1 BL trigger 도래 / Beta BL 진행 상황)
- 자동화 가능 부분 — `grep -E "BL-[0-9]+" docs/REFACTORING-BACKLOG.md` 로 active BL 추출 + status grep
- 영구 규칙: 각 sprint kickoff 시 bl-audit-checklist 1회 실행 + 결과 sprint-template.md frontmatter 안 명시

**검증:** Sprint 28 종료 시 본 checklist 사용 1건 검증 (Step 5 학습 단계)

### T3 — PR template 강화 (15분)

**File:** `.github/pull_request_template.md` (수정 — 현재 53줄)

**변경:**

- "검증 (필수)" 섹션 다음에 "**Codex Gates (sprint 단위)**" 섹션 추가:
  ```
  ## Codex Gates (sprint 단위)
  - [ ] G.0 Plan eval (link)
  - [ ] G.2 Implementation review (link)
  - [ ] G.4 P2 issue 처리 (link)
  - [ ] self-assessment 점수 N/10 + 근거 (≥3 줄)
  ```
- "관련 이슈 / 문서" 섹션에 BL ID + lessons ID 명시 의무화

**검증:** Sprint 28 의 다음 PR (Slice 1b 또는 Slice 2) description 에 codex Gates 섹션 채워짐

### T4 — .claude/settings.json hooks 신규 (30분)

**File:** `.claude/settings.json` (수정 — 현재 64줄, hooks 키 부재)

**변경:**

- `hooks` 키 신규 추가:
  - **Stop hook** — sprint 종료 시 INDEX.md 갱신 reminder script
  - **SessionStart hook** — BL audit checklist 자동 표시 (echo or cat)
- 각 hook 의 `command` 정의 — `cat docs/guides/bl-audit-checklist.md` 또는 echo simple message
- test run 1회 — Stop hook 동작 검증

**검증:** `jq '.hooks' .claude/settings.json` non-empty + 1회 fire 검증

### T5 — .husky/pre-commit reminder 강화 (선택, 30분)

**File:** `.husky/pre-commit` (수정)

**변경:**

- 신규 dev-log 파일 추가 시 INDEX.md 갱신 검증 script:
  ```bash
  if git diff --cached --name-only | grep -q "dev-log/.*\.md"; then
    if ! git diff --cached --name-only | grep -q "dev-log/INDEX.md"; then
      echo "[reminder] dev-log 신규 추가 — INDEX.md 갱신 권장"
    fi
  fi
  ```
- 검증 실패 시 reminder 출력 (저장은 막지 않음 — reminder only)

**정책 결정:** `[권고]` reminder only (속도 저하 회피, dogfood 흐름 유지)

**검증:** test commit 으로 hook fire 1회 검증

### T6 — TODO.md 메타 헤더 표준화 (10분)

**File:** `docs/TODO.md` (수정 — 현재 882줄)

**변경:**

- L1-L10 에 메타 헤더 추가:
  ```markdown
  > **Last Updated:** 2026-05-04
  > **Active Sprint:** Sprint 28 — Beta prereq 종합 (Slice 1a/1b/2/3/4)
  > **Recent BLs:** BL-141 / BL-140b / BL-004 (Slice 2/3/4 active)
  > **Next Trigger:** dogfood Day 7 종료 + dual metric 통과 → Beta path A1 결정
  ```
- 매 sprint 종료 시 갱신 의무 명시 (sprint-template.md trailer 와 연결)

**검증:** TODO.md L1-L10 4 필드 모두 채워짐

## File summary

**신규 (3 파일):**

- `docs/guides/sprint-template.md`
- `docs/guides/bl-audit-checklist.md`

**수정 (4 파일):**

- `.github/pull_request_template.md`
- `.claude/settings.json`
- `.husky/pre-commit`
- `docs/TODO.md`

## Risks & Mitigations

| 리스크                                                                       | 영향                             | 완화                                                          |
| ---------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------- |
| .claude/settings.json hook 추가 시 다른 sprint 영향                          | 다른 작업 시 hook fire           | hook 명령 idempotent 보장 (echo / cat 만 사용, mutation 0)    |
| .husky/pre-commit 강화 시 commit 속도 저하                                   | 매 commit 시 grep 실행 (수십 ms) | reminder only, 차단 X. 속도 영향 최소                         |
| sprint-template.md frontmatter 4 신규 필드가 다른 sprint 회고 적용 시 미준수 | 메타-방법론 정책 미정착          | Sprint 28 회고가 첫 검증 케이스 — Stage 6 Step 5 시 자체 검증 |

## Acceptance Criteria

- [ ] T1 sprint-template.md frontmatter 4 신규 필드 (sprint type / office-hours Y/N / dual metric / 신규 BL count) 존재
- [ ] T2 bl-audit-checklist.md 의 grep script 동작 확인 (active BL 추출)
- [ ] T3 PR template Codex Gates 섹션 = 4 체크박스 + self-assess 슬롯
- [ ] T4 `.claude/settings.json` hooks 키 ≥1 hook 정의 + 1회 fire 검증
- [ ] T5 (선택) `.husky/pre-commit` reminder 동작 검증
- [ ] T6 `docs/TODO.md` L1-L10 4 필드 채움

## PR Strategy

**1 PR**: `chore/sprint28-slice1a-workflow-enforcement` → base `stage/h2-sprint28-comprehensive`

- T1-T6 모두 1 PR
- commit 분리 가능 (T1 / T2 / T3 / T4 / T5 / T6 각 atomic) 또는 단일 commit

## Self-Review (G0 evaluator pattern)

- [P2-1] T4 hook 의 `cat docs/guides/bl-audit-checklist.md` 가 매 SessionStart 마다 fire 시 노이즈 가능 — alternative: `head -20` 또는 `grep "active"` 만
- [P2-2] T5 husky reminder 의 grep 가 macOS / Linux 모두 동작? — 표준 grep 사용 시 OK
- [P2-3] T6 TODO.md 메타 헤더 4 필드 가 매 sprint 종료 시 갱신 의무 — sprint-template trailer 에 명시 필요 (T1 의 trailer 섹션 안)

P1 0건 / P2 3건 — Slice 1a 진행 OK.
