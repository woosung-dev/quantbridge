# ADR-038: `docs/` 최상위를 질문별로 편다 — `reference/` 래퍼와 `decisions/` 를 해체한다

> **상태:** 확정 (Accepted — 2026-08-21, 사용자 판정 「B′로 가자」)
> **일자:** 2026-08-21
> **결정자:** woosung (기안: Claude)
> **관련:** [ADR-026](./026-documentation-ssot.md)(SSOT 7축 — §1 ④ 의 **위치**만 본 ADR 이 대체, 축은 유지) ·
> [ADR-029](./029-monorepo-standard-layout.md)(코드 쪽 표준 배치) · [ADR-037](./037-harness-zero-base.md)(검사기 없음 — 본 ADR 도 검사기를 더하지 않는다)
> **대체함:** ADR-026 §1 ④ 「함정 = `docs/reference/`」의 경로 · `docs/README.md` 의 「`reference/` 는 수명으로 먼저 분리한다」
> **복원 원본:** 재배치 직전 커밋 `c3b35e5f` — `git show c3b35e5f:docs/reference/<경로>` / `git show c3b35e5f:docs/decisions/<NNN>-*.md`

---

## Context — 타 LLM 의 추천안을 받아 대조했다

2026-08-21 에 다른 LLM 이 「Engineering lifecycle + Diátaxis Hybrid」 구조를 추천했다 —
`architecture / adr / domain / development / api / operations / specs` 7폴더. 실측으로 대조한 결과:

- **80% 는 이미 있었다.** [ADR-026](./026-documentation-ssot.md)(2026-08-06)이 같은 출처(Diátaxis)로
  같은 축을 세웠다. 다른 것은 이름(`decisions/`↔`adr/`, `interfaces/`↔`api/`)과 **`reference/` 래퍼 한 층**뿐.
- **실질 차이는 하나** — `reference/operations/` 18파일에 「개발하는 법」(local-setup·worktree·gates·CI·env)과
  「운영하는 법」(deploy·mainnet runbook·live-close·auth setup·soak 원장)이 섞여 있었다.
- **추천안의 전제 3개는 이 레포와 안 맞는다** — ⑴ 팀·멀티앱(CODEOWNERS, `admin/`·`mobile/`) ⑵ backlog 는
  GitHub Issues(우리는 원장 3분할 1.2MB 를 `ledger-vitals.sh` 가 집행) ⑶ YAML frontmatter 로 수명 관리
  (ADR-037 직후라 검사기가 없고, 검사기 없는 메타데이터는 낡을 장식이다).

옵션 4개를 점수로 비교했다 — A(정리만, 80) · B(`reference/` 안에서 development 분리, 70) ·
**B′(래퍼 해체 + 개명, `specs/` 제외, 84)** · C(추천안 그대로, 55). 사용자가 B′ 를 골랐다.

## Decision

### 1. `docs/` 최상위 = 질문별 정본 6축 + `adr/` + 상태·반증

```text
docs/
├── architecture/   시스템은 어떻게 조립·실행되는가      ← reference/architecture
├── domain/         용어·엔티티·상태·제품 요구는 무엇인가 ← reference/domain + reference/product
├── api/            API·외부 경계는 무엇인가             ← reference/interfaces
├── development/    어떻게 개발·검증하는가 (+workflows/) ← reference/operations 의 개발분
├── operations/     어떻게 배포·운영·진단하는가          ← reference/operations 의 운영분 (+security/, soak 원장)
├── design/         화면·상호작용의 정본(프로토타입)     ← reference/design
├── adr/            왜 이 선택을 했는가                  ← decisions
├── status.md · roadmap.md · backlog*.md · lessons.md   (상태 3종 + 반증 — 변경 없음)
└── dev-log/ · archive/                                 (색인 · lessons 넘침분 — 변경 없음)
```

**수명축은 래퍼가 아니라 `docs/README.md` 의 표가 맡는다.** ADR-026 의 7축(행위·용어·실행 계약·함정·근거·
반증·상태)은 그대로고, ④ 함정의 **자리**만 바뀌었다.

### 2. `specs/` 는 만들지 않는다

`status.md` 「다음 스프린트」 블록이 **유일한 진입점**이고(`AGENTS.md` · §G8), 회차 정의는 `phases/<회차>/`,
산출물은 `runs/` 다. `specs/active|archive` 를 더하면 진입점이 둘이 되고, 이 레포는 진입점이 둘일 때
낡은 쪽을 따르는 사고를 반복해 왔다([LESSON-101] 계열).

### 3. 기각한 것 (같은 추천을 다시 받았을 때 다시 논하지 않기 위해 적는다)

- YAML frontmatter(`status`·`last-reviewed`) — 검사기 없이는 드리프트 원천. ADR-037 재입힘 규칙 경유가 아니면 금지
- CODEOWNERS · review owner 표 — 1인 + 에이전트 레포
- backlog → GitHub Issues — [BL-779] 원장 3분할이 3일 전, 기계 집행 중
- `api/` 정책 7파일(conventions·error-model·pagination…) — 추측 생성. 규칙은 `apps/api/AGENTS.md`, 계약은 OpenAPI export([ADR-031])
- `architecture/diagrams/` · `operations/runbooks/` 하위 폴더 — 파일이 여럿 생길 때 만든다(추천안 자신의 규칙 6)

### 4. 같이 걷어낸 것 (tombstone — 원문 = `git show c3b35e5f:<경로>`)

| 무엇을                                                               | 근거                                                                                                                     |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `docs/reference/README.md`                                           | 내용이 `docs/README.md` 표로 합쳐졌다                                                                                    |
| `docs/reference/operations/workflows/sprint60-interview-template.md` | 참조 0건 · 스프린트 고유                                                                                                 |
| `docs/evidence/` (png 4)                                             | 참조 0건 · 대상 [BL-414]·[BL-429] 는 RESOLVED                                                                            |
| `docs/reports/` (README · 템플릿 · auto-dogfood 2026-05-03)          | gitignore 산출 자리 — 「아무도 안 읽는다」(2026-08-15 사용자 지시). `run_auto_dogfood.py` 출력은 `runs/auto-dogfood/` 로 |

`sprint-kickoff-template.md` 는 `ci-cd.md`·`pre-commit.md` 가 §B 를 인용 중이라 **이번엔 이동만** 했다 — 삭제는 별도 판정. → **같은 날 후속 PR 에서 삭제**(규칙은 두 파일에 인라인, 원문 `git show 9e91809c:docs/development/workflows/sprint-kickoff-template.md`).

## Consequences

- **이동 104 · 삭제 10 · 재작성 120파일.** 상대 링크는 파일의 구·신 위치 기준으로 resolve → 재상대화했고
  git SHA 좌표(`<sha>:docs/...`, `prototypes-gen1:`)가 있는 줄은 건드리지 않았다.
- **경로를 하드코딩한 테스트·스크립트 5곳이 안전망이었다** — `design-canon-*` 3곳(프로토타입 바이트 대조) ·
  `soak-gate.sh` · `mtbf_stratified.py`(soak 원장). 치환이 빠지면 CI 가 red 다.
- 검사기를 더하지 않았다 — 링크 검사는 회차 안에서 일회용 python 으로 돌리고 버렸다(ADR-037).
- `docs/reference/` 를 기억하는 세션·메모리·외부 노트는 낡는다. `git show c3b35e5f:` 가 답한다.

## 비고 — 재평가 트리거

⑴ 한 폴더가 20파일을 넘으면 하위 분할(`runbooks/`·`diagrams/`)을 그때 연다 · ⑵ `design/prototypes/` 는 문서가
아니라 **테스트 픽스처**다 — `apps/web/` 밖 공용 자리가 필요해지면 이전을 별도 결정한다 · ⑶ 협업자·타 에이전트가
늘어 문서 메타데이터가 필요해지면 frontmatter 는 **검사기와 한 쌍으로만** 들인다.
