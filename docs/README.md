# QuantBridge 문서 지도

> **문서의 위치가 필요할 때만 이 파일을 연다.** 새 AI 세션의 기본 입력은
> `CONTEXT.md` + `AGENTS.md` + [`status.md`](./status.md) 3종이다.

## 지금 필요한 문서

| 질문 | 정본 | 역할 |
| --- | --- | --- |
| 지금 무엇을 하는가 | [`status.md`](./status.md) | 활성 또는 다음 스프린트의 실행 계약 |
| 다음에는 무엇을 하는가 | [`roadmap.md`](./roadmap.md) | 다음 1~2개 스프린트 후보와 먼 제품 방향 |
| 아직 풀지 못한 일은 무엇인가 | [`backlog.md`](./backlog.md) | 열린 `BL-`의 상태·영향·재개 조건·검증 링크 |
| 무엇을 실행해 검증하는가 | [`reference/operations/gates-and-traps.md`](./reference/operations/gates-and-traps.md) | 게이트 명령과 조용히 통과하는 함정 |

## 문서의 수명과 위치

| 위치 | 읽는 사람의 질문 | 갱신 원칙 |
| --- | --- | --- |
| [`reference/`](./reference/README.md) | 지금도 참인 도메인·아키텍처·운영·제품·API·설계 계약은 무엇인가 | 코드와 어긋나면 코드에 맞춰 고친다 |
| [`decisions/`](./decisions/) | 왜 이 선택을 했는가 | 폐기해도 삭제하지 않고 `Superseded`로 남긴다 |
| [`dev-log/INDEX.md`](./dev-log/INDEX.md) | 완료된 스프린트에서 무엇을 측정·결정했는가 | 결과와 근거를 append-only로 남긴다 |
| [`archive/`](./archive/) | 더는 현재 규칙이 아닌 상세 기록은 무엇인가 | 읽기 전용이다 |
| [`reports/`](./reports/) | 생성된 dogfood·retro 출력은 어디 있는가 | 코드 생성물이다. 수동 정본을 만들지 않는다 |

루트의 사람용 정본은 [`README.md`](../README.md), [`AGENTS.md`](../AGENTS.md),
[`CONTEXT.md`](../CONTEXT.md), [`DESIGN.md`](../DESIGN.md)다. [`CLAUDE.md`](../CLAUDE.md)는
`AGENTS.md`를 불러오는 Claude Code 호환 진입점이다.

## 오래 참는 계약 찾기

`reference/`는 수명으로 먼저 분리한 뒤, 안에서 질문별로만 얕게 나눈다.

| 질문 | 위치 | 대표 문서 |
| --- | --- | --- |
| 시스템은 어떻게 조립·실행되는가 | [`reference/architecture/`](./reference/architecture/) | system, data flow, Pine/Trust Layer architecture |
| 도메인 용어·엔티티·상태는 무엇인가 | [`reference/domain/`](./reference/domain/) | domain overview, ERD, entities, state machines |
| 어떻게 설치·검증·운영하는가 | [`reference/operations/`](./reference/operations/) | local setup, gates, CI, worktree, security, 반복 workflow |
| API·외부 경계는 무엇인가 | [`reference/interfaces/`](./reference/interfaces/) | endpoints |
| 제품 요구·전략·SLO는 무엇인가 | [`reference/product/`](./reference/product/) | vision, 현재 제품 범위 |
| 화면·상호작용 근거는 무엇인가 | [`reference/design/`](./reference/design/) | prototypes, interaction specification |

## 새 문서를 만들기 전

1. 지금 실행할 일인가 → `status.md`, 아직 해결하지 못한 일인가 → `backlog.md`, 다음 후보인가 → `roadmap.md`에 먼저 둔다.
2. 스프린트가 끝나도 계속 참인가 → `reference/`, 결정 이유인가 → `decisions/`, 결과 기록인가 → `dev-log/` 또는 `archive/`에 둔다.
3. 어느 경우에도 맞지 않으면 새 파일을 만들기 전에 독자와 수명을 먼저 정한다.

스프린트 종료 시 작업 문서는 반드시 승격·강등·삭제 중 하나로 종결한다.
자세한 절차는 [`reference/operations/workflows/sprint-template.md`](./reference/operations/workflows/sprint-template.md) §9를 따른다.
