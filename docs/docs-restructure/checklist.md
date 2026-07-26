# docs-restructure 체크리스트

> 목표 = `docs/` 최상위 34개 → 9개 · 고장 2건 수리 · 증식 차단 규칙 신설
> 근거 = 90개 레포 실측 조사 (`~/Downloads/조사/`) · 상세 판단은 [`context-notes.md`](./context-notes.md)

---

## S0. 준비

- [x] 브랜치 `docs/restructure` 생성
- [x] 인바운드 참조 실측 — 코드 참조 12파일 · 테스트 파일 로드 2건 확인
- [x] 위험 기반 스코프 조정 — `dev-log/` `reports/` 는 제자리 유지 결정
- [x] checklist + context-notes 선작성 (CLAUDE.md §7)

## S1. 고장 수리 (측정으로 확정된 실제 결함 2건)

- [ ] 루트 `CLAUDE.md → AGENTS.md` 심볼릭 생성 + 커밋
      → 검증: `git ls-files CLAUDE.md` 가 심볼릭으로 추적됨
- [ ] `.gitignore` 에서 `.ai/` 무시 해제 + 24파일 커밋
      → 검증: `AGENTS.md` 가 참조하는 미추적 경로 11 → 0

## S2. 증식 차단 (이걸 안 하면 나머지가 3주짜리)

- [ ] 스프린트 종료 체크리스트에 **승격/강등 택1** 단계 추가
      → 검증: 템플릿에 항목 존재 + 본 스프린트가 스스로 그 규칙을 적용

## S3. 구조 재편

- [ ] `docs/archive/` 신설 — 완결 스프린트 15 + qa + superpowers + audit + 기타 이관
- [ ] `docs/reference/` 신설 — `00_`~`07_` 8개 + `prototypes/` 통합
- [ ] `docs/decisions/` 신설 — `dev-log/` ADR 18건 분리
- [ ] `TODO.md` → `status.md` (활성분만, 84KB → 목표 8KB 이하)
- [ ] `product-roadmap.md` → `roadmap.md` · `REFACTORING-BACKLOG.md` → `backlog.md`
      → 검증: `docs/` 최상위 엔트리 9개

## S4. 참조 무결성

- [ ] 코드 내 docs 경로 문자열 갱신 (에러 메시지 7 · 도크스트링 3 · 테스트 상수 4)
- [ ] `docs/` 내부 상호 링크 876건 중 이동 대상 갱신
      → 검증: 깨진 상대 링크 0

## S5. 에이전트 자산 공유

- [ ] `.gitignore` 에 `!.claude/skills/` 추가 + 팀 자산 스킬 선별 커밋
- [ ] `docs/guides/` 절차 문서 → `.claude/skills/` 이관 검토
- [ ] `.claude/{plans,worktrees}` 명시적 무시

## S6. 진입 문서

- [ ] `AGENTS.md` §문서화 구조 표(14줄) → 5줄 교체
- [ ] 첫-step 5종 → 3종 축소
- [ ] `docs/README.md` 목차 재작성 (**반드시 마지막**)

## S7. 게이트

- [ ] BE pytest 전량 (3-env 필수)
- [ ] FE vitest 전량 (canon 32 포함)
- [ ] `git ls-files` 기준 최종 구조 확인
- [ ] 본 스프린트 문서를 새 규칙대로 강등 (`docs/archive/sprints/docs-restructure/`)

## S8. 착지

- [ ] 시맨틱 커밋 분할
- [ ] PR 생성
