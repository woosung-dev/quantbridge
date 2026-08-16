# QuantBridge 문서 지도

> **문서의 위치가 필요할 때만 이 파일을 연다.** 새 AI 세션의 기본 입력은
> `CONTEXT.md` + `AGENTS.md` + [`status.md`](./status.md) 3종이다.

## 지금 필요한 문서

| 질문                          | 정본                                                                                   | 역할                                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 지금 무엇을 하는가            | [`status.md`](./status.md)                                                             | 활성 또는 다음 스프린트의 실행 계약                                                           |
| 다음에는 무엇을 하는가        | [`roadmap.md`](./roadmap.md)                                                           | 다음 1~2개 스프린트 후보와 먼 제품 방향                                                       |
| 아직 풀지 못한 일은 무엇인가  | [`backlog.md`](./backlog.md)                                                           | 열린 `BL-`의 상태·영향·재개 조건·검증 링크                                                    |
| 닫힌 `BL-`의 본문은 어디 있나 | [`backlog-resolved.md`](./backlog-resolved.md)                                         | RESOLVED 본문. 인덱스 표 행은 `backlog.md` 에 남아 있고 `bl-audit` 이 둘을 **한 벌로** 읽는다 |
| 무엇을 실행해 검증하는가      | [`reference/operations/gates-and-traps.md`](./reference/operations/gates-and-traps.md) | 게이트 명령과 조용히 통과하는 함정                                                            |
| FE 를 어떻게 배포하는가       | [`reference/operations/frontend-deploy.md`](./reference/operations/frontend-deploy.md) | 오라클 A1 배포 절차·구조 근거·실측 함정                                                       |

## 문서의 수명과 위치

| 위치                                     | 읽는 사람의 질문                                               | 갱신 원칙                                                                         |
| ---------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [`reference/`](./reference/README.md)    | 지금도 참인 도메인·아키텍처·운영·제품·API·설계 계약은 무엇인가 | 코드와 어긋나면 코드에 맞춰 고친다                                                |
| [`decisions/`](./decisions/)             | 왜 이 선택을 했는가                                            | 폐기해도 삭제하지 않고 `Superseded`로 남긴다                                      |
| [`lessons.md`](./lessons.md)             | 무엇이 반증됐는가 (LESSON 카드)                                | `docs-audit`이 **400줄** 상한을 건다. 넘으면 `archive/`로 내린다                  |
| [`archive/`](./archive/)                 | `lessons.md`에서 내려온 stale LESSON 본문                      | 지금은 이 용도**만** 남았다. 구 375파일은 삭제됐고 아래 git history 항목이 답한다 |
| [`dev-log/INDEX.md`](./dev-log/INDEX.md) | 완료된 스프린트에서 무엇을 측정·결정했는가                     | 요약 색인만 유지. 회고는 `lessons.md` 카드 + 한 줄로 끝낸다 (원문 파일 없음)      |
| git history                              | 삭제된 과거 원문(구 `archive/`·`dev-log/*.md`)은 어디 있는가   | **2026-08-06 이전 원문만** 여기 있다 — `git show 0f0f0b06:docs/archive/<경로>`    |
| [`reports/`](./reports/)                 | 생성된 dogfood·retro 출력은 어디 있는가                        | 코드 생성물이다. 수동 정본을 만들지 않는다                                        |

★**삭제된 원문의 「목록」은 파일로 남아 있지 않다 — 명령으로 뽑는다.** `dev-log/INDEX.md`가 색인하는
것은 회고뿐이고, 구 `archive/` 375파일에는 색인이 없다. 파일명을 모르면 위 `git show`를 칠 수 없다.

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
여기서 꺼내 `reference/operations/`로 갱신 재등재한다 ([BL-617](./backlog.md#bl-617)).

루트의 사람용 정본은 [`README.md`](../README.md), [`AGENTS.md`](../AGENTS.md),
[`CONTEXT.md`](../CONTEXT.md), [`DESIGN.md`](../DESIGN.md)다. [`CLAUDE.md`](../CLAUDE.md)는
`AGENTS.md`를 불러오는 Claude Code 호환 진입점이다.

## 오래 참는 계약 찾기

`reference/`는 수명으로 먼저 분리한 뒤, 안에서 질문별로만 얕게 나눈다.

| 질문                               | 위치                                                   | 대표 문서                                                 |
| ---------------------------------- | ------------------------------------------------------ | --------------------------------------------------------- |
| 시스템은 어떻게 조립·실행되는가    | [`reference/architecture/`](./reference/architecture/) | system, data flow, Pine/Trust Layer architecture          |
| 도메인 용어·엔티티·상태는 무엇인가 | [`reference/domain/`](./reference/domain/)             | domain overview, ERD, entities, state machines            |
| 어떻게 설치·검증·운영하는가        | [`reference/operations/`](./reference/operations/)     | local setup, gates, CI, worktree, security, 반복 workflow |
| API·외부 경계는 무엇인가           | [`reference/interfaces/`](./reference/interfaces/)     | endpoints                                                 |
| 제품 요구·전략·SLO는 무엇인가      | [`reference/product/`](./reference/product/)           | vision, 현재 제품 범위                                    |
| 화면·상호작용 근거는 무엇인가      | [`reference/design/`](./reference/design/)             | prototypes, interaction specification                     |

## 새 문서를 만들기 전

1. 지금 실행할 일인가 → `status.md`, 아직 해결하지 못한 일인가 → `backlog.md`, 다음 후보인가 → `roadmap.md`에 먼저 둔다.
2. 스프린트가 끝나도 계속 참인가 → `reference/`, 결정 이유인가 → `decisions/`, 결과 기록인가 → `dev-log/INDEX.md` 요약 한 줄(원문은 커밋·git history)로 남긴다.
3. 어느 경우에도 맞지 않으면 새 파일을 만들기 전에 독자와 수명을 먼저 정한다.

스프린트 종료 시 작업 문서는 반드시 승격·강등·삭제 중 하나로 종결한다.
자세한 절차는 [`reference/operations/workflows/sprint-template.md`](./reference/operations/workflows/sprint-template.md) §9를 따른다.
