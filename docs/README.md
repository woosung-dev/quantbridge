# QuantBridge 문서 지도

> **문서의 위치가 필요할 때만 이 파일을 연다.** 새 AI 세션의 기본 입력은
> `CONTEXT.md` + `AGENTS.md` + [`status.md`](./status.md) 3종이다.
> 배치 근거 = [ADR-026](./adr/026-documentation-ssot.md)(질문 유형별 정본 분할) +
> [ADR-038](./adr/038-docs-top-level-by-question.md)(2026-08-21 — `reference/` 래퍼·`decisions/` 해체, 최상위를 질문별로).

## 지금 필요한 문서

| 질문                          | 정본                                                                 | 역할                                                                                                     |
| ----------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 지금 무엇을 하는가            | [`status.md`](./status.md)                                           | 활성 또는 다음 스프린트의 실행 계약 — 「다음 스프린트」 블록이 **유일한 진입점**                         |
| 다음에는 무엇을 하는가        | [`roadmap.md`](./roadmap.md)                                         | 다음 1~2개 스프린트 후보와 먼 제품 방향                                                                  |
| 아직 풀지 못한 일은 무엇인가  | [`backlog.md`](./backlog.md)                                         | 열린 `BL-`의 상태·영향·재개 조건·검증 링크 (ACTIVE ∪ PARTIAL + 인덱스 표 전량)                           |
| 트리거 대기 `BL-`의 본문은    | [`backlog-deferred.md`](./backlog-deferred.md)                       | DEFERRED 본문 (2026-08-18 3분할 — 인덱스 표 행은 `backlog.md` 에 남는다)                                 |
| 닫힌 `BL-`의 본문은 어디 있나 | [`backlog-resolved.md`](./backlog-resolved.md)                       | RESOLVED 본문. 인덱스 표 행은 `backlog.md` 에 남는다 — 원장 사활 검사 = `tools/scripts/ledger-vitals.sh` |
| 무엇을 실행해 검증하는가      | [`development/gates-and-traps.md`](./development/gates-and-traps.md) | 게이트 명령과 조용히 통과하는 함정                                                                       |
| FE 를 어떻게 배포하는가       | [`operations/frontend-deploy.md`](./operations/frontend-deploy.md)   | 오라클 A1 배포 절차·구조 근거·실측 함정                                                                  |

## 어느 질문은 어느 폴더가 답하나

최상위 폴더 이름이 곧 질문이다. 같은 층에 **지금도 참인 정본 6축**과 **근거·반증·상태**가 나란히 있고,
수명은 이 표가 가른다 — 폴더 래퍼로 가르지 않는다(ADR-038).

| 위치                                     | 읽는 사람의 질문                                   | 갱신 원칙                                                                                   |
| ---------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| [`architecture/`](./architecture/)       | 시스템·실행·데이터 흐름은 어떻게 조립되는가        | 코드와 어긋나면 코드에 맞춰 고친다 — system, data flow, Pine/Trust Layer                    |
| [`domain/`](./domain/)                   | 용어·엔티티·상태·제품 요구는 무엇인가              | 같음 — overview, ERD, entities, state machines, vision, requirements                        |
| [`api/`](./api/)                         | API·외부 경계는 무엇인가                           | 같음 — endpoints. 계약 원본은 OpenAPI export([ADR-031](./adr/031-api-contract-axis-poc.md)) |
| [`development/`](./development/)         | 어떻게 설치·검증·병렬 작업·반복 workflow 를 도는가 | 같음 — local setup, gates, CI, worktree, env, `workflows/`                                  |
| [`operations/`](./operations/)           | 어떻게 배포·운영·진단하는가                        | 같음 — BE/FE deploy, mainnet runbook, live-close, auth setup, `security/`, soak 원장        |
| [`design/`](./design/)                   | 화면·상호작용의 정본(프로토타입)은 무엇인가        | 프로토타입은 **테스트 픽스처**다 — `design-canon-*` 가 바이트 대조한다                      |
| [`adr/`](./adr/README.md)                | 왜 이 선택을 했는가                                | 폐기해도 삭제하지 않고 `Superseded`로 남긴다. 색인 = `adr/README.md`                        |
| [`lessons.md`](./lessons.md)             | 무엇이 반증됐는가 (LESSON 카드)                    | **400줄** 상한(관례 — 자동 집행은 ADR-037 로 철거). 넘으면 `archive/`로 내린다              |
| [`archive/`](./archive/)                 | `lessons.md`에서 내려온 stale LESSON 본문          | 지금은 이 용도**만** 남았다. 구 375파일은 삭제됐고 아래 git history 항목이 답한다           |
| [`dev-log/INDEX.md`](./dev-log/INDEX.md) | 완료된 스프린트에서 무엇을 측정·결정했는가         | 요약 색인만 유지. 회고는 `lessons.md` 카드 + 한 줄로 끝낸다 (원문 파일 없음)                |
| git history                              | 삭제된 과거 원문은 어디 있는가                     | 아래 tombstone 표가 좌표다                                                                  |

### Tombstone — 삭제된 것과 좌표

| 무엇을                                                      | 언제·왜                                            | 원문                                                |
| ----------------------------------------------------------- | -------------------------------------------------- | --------------------------------------------------- |
| `docs/reference/` 래퍼 전체 · `docs/decisions/`             | 2026-08-21 ADR-038 — 최상위로 이동(삭제 아님)      | `git show c3b35e5f:docs/reference/<경로>`           |
| `docs/reference/README.md`                                  | 2026-08-21 — 이 파일의 표로 합쳐졌다               | `git show c3b35e5f:docs/reference/README.md`        |
| `docs/reports/` (README·템플릿·auto-dogfood 2026-05-03)     | 2026-08-21 — gitignore 산출 자리. 산출물은 `runs/` | `git show c3b35e5f:docs/reports/README.md`          |
| `docs/evidence/` (png 4) · `sprint60-interview-template.md` | 2026-08-21 — 참조 0건                              | `git show c3b35e5f:docs/evidence/` · `…/workflows/` |
| 구 `archive/` 375파일 · `dev-log/*.md` 135파일              | 2026-08-06 문서 대개편                             | 아래 `0f0f0b06` 명령                                |

★**2026-08-06 이전 원문의 「목록」은 파일로 남아 있지 않다 — 명령으로 뽑는다.** `dev-log/INDEX.md`가 색인하는
것은 회고뿐이고, 구 `archive/` 375파일에는 색인이 없다. 파일명을 모르면 `git show`를 칠 수 없다.

```bash
git ls-tree -r --name-only 0f0f0b06 -- docs/archive   # 삭제된 archive 375파일 목록
git ls-tree -r --name-only 0f0f0b06 -- docs/dev-log   # 삭제된 회고 원문 135파일 목록
git show 0f0f0b06:<위 목록의 경로>                     # 원문 조회
```

★**`0f0f0b06` 은 태그 `docs-pre-overhaul` 이 고정한다 — 그 태그를 지우지 마라.** 이 커밋은 대개편
브랜치에서만 도달 가능해서, 태그가 없으면 squash·rebase 머지 시 fresh clone 에서 위 세 명령이 전부
`not a valid object name` 으로 깨진다.

★**그 목록 안에 「과거 기록」이 아닌 것이 4건 있다** — Cloud Run 런북 · Grafana 셋업 ·
Bybit mainnet 체크리스트 · 법무 임시 런북. 아직 실행하지 않은 절차라 배포·메인넷 착수 시
여기서 꺼내 `operations/`로 갱신 재등재한다 ([BL-617](./backlog.md#bl-617)).

루트의 사람용 정본은 [`README.md`](../README.md), [`AGENTS.md`](../AGENTS.md),
[`CONTEXT.md`](../CONTEXT.md), [`DESIGN.md`](../DESIGN.md)다. [`CLAUDE.md`](../CLAUDE.md)는
`AGENTS.md`를 불러오는 Claude Code 호환 진입점이다. 스택별 규칙은 `apps/api/AGENTS.md`·`apps/web/AGENTS.md`.

## 새 문서를 만들기 전

1. 지금 실행할 일인가 → `status.md`, 아직 해결하지 못한 일인가 → `backlog.md`, 다음 후보인가 → `roadmap.md`에 먼저 둔다.
2. 스프린트가 끝나도 계속 참인가 → 위 표의 정본 6축 중 **질문이 맞는 폴더**, 결정 이유인가 → `adr/`,
   결과 기록인가 → `dev-log/INDEX.md` 요약 한 줄(원문은 커밋·git history)로 남긴다.
3. 어느 경우에도 맞지 않으면 새 폴더를 만들지 말고 독자와 수명을 먼저 정한다. 하위 폴더(`runbooks/`·`diagrams/`)는
   파일이 여럿 생겼을 때 연다 — 빈 폴더를 미리 만들지 않는다.
4. `docs/` 에 넣지 않는 것 — 회차 산출물·HTML 리포트(→ `runs/`), 생성 client·OpenAPI 원본(→ 코드 쪽), 앱 실행 명령(→ `mise.toml`·앱 README).

스프린트 종료 시 작업 문서는 반드시 승격·강등·삭제 중 하나로 종결한다.
자세한 절차는 [`development/workflows/sprint-template.md`](./development/workflows/sprint-template.md) §9를 따른다.
