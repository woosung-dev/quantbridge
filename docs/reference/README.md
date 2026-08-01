# QuantBridge — Reference 계약 지도

> **역할:** 코드와 함께 오래 참이어야 하는 계약의 정본. 현재 작업은 `../status.md`, 결정 이유는 `../decisions/`, 완료된 측정·판정은 `../dev-log/`, 더 이상 기본 경로가 아닌 증거는 `../archive/`에서 찾는다.

## 분류 원칙

먼저 문서의 **수명**으로 `docs/`의 위치를 정한다. `reference/`에 둘 문서만, 독자가 던지는 질문에 따라 아래 여섯 영역으로 분류한다. 폴더의 수명이나 상태를 다시 설명하지 않는다.

| 영역 | 답하는 질문 | 포함하지 않는 것 |
| --- | --- | --- |
| [`architecture/`](./architecture/) | 시스템·실행·데이터 흐름은 어떻게 구성되는가 | 제품 우선순위·스프린트 결과 |
| [`domain/`](./domain/) | Pine·전략·거래·데이터의 의미, 엔티티, 상태는 무엇인가 | 설치·배포 절차 |
| [`operations/`](./operations/) | 어떻게 개발·검증·배포·진단·반복 workflow를 실행하는가 | 코드 모델의 상세 정의 |
| [`interfaces/`](./interfaces/) | API와 외부 시스템의 경계는 무엇인가 | 내부 구현 서술 |
| [`product/`](./product/) | 제품 요구, 지원 범위, SLO, 전략은 무엇인가 | 현재 sprint의 실행 지시 |
| [`design/`](./design/) | 화면·상호작용의 현재 계약과 프로토타입은 무엇인가 | 구현 완료 회고 |

## 대표 진입점

- 아키텍처: [`system-architecture.md`](./architecture/system-architecture.md), [`data-flow.md`](./architecture/data-flow.md)
- 도메인: [`domain-overview.md`](./domain/domain-overview.md), [`entities.md`](./domain/entities.md), [`erd.md`](./domain/erd.md)
- 운영: [`local-setup.md`](./operations/local-setup.md), [`gates-and-traps.md`](./operations/gates-and-traps.md), [`worktree-parallel.md`](./operations/worktree-parallel.md), [`security/geo-block-setup.md`](./operations/security/geo-block-setup.md), [`workflows/sprint-template.md`](./operations/workflows/sprint-template.md)
- 인터페이스: [`endpoints.md`](./interfaces/endpoints.md)
- 제품: [`requirements-overview.md`](./product/requirements-overview.md), [`vision.md`](./product/vision.md)
- 설계: [`prototypes/README.md`](./design/prototypes/README.md)

## 새 문서의 자리

1. 이번 sprint만의 실행 계약이면 `../status.md`, 열린 항목이면 `../backlog.md`에 둔다.
2. 완료한 판단·측정 결과면 `../dev-log/`로, 더 이상 기본 경로가 아닌 상세 증거면 `../archive/`로 보낸다.
3. 위 둘이 아니고 코드와 함께 갱신될 계약이라면 이 폴더의 여섯 질문 중 하나를 택한다. 어느 곳에도 맞지 않으면 새 카테고리를 만들지 말고 먼저 `docs/README.md`의 지도와 수명을 재검토한다.
