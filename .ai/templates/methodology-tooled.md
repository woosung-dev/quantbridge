# AI 기반 1인 풀스택 개발 방법론 (Gstack + Superpowers)

> 이 문서는 `CLAUDE.md`/`AGENTS.md`에서 링크해 빠르게 읽는 **핵심 운영 요약본**이다.
> 도구 없이 운영하려면 `methodology.md`를, Claude 모드 운용은 `claude-code-workflow.md`를 참조한다.

---

## 전체 흐름

```text
[Stage 1] 기획 + 아키텍처 → [Stage 2] 디자인
  ↓
[Stage 3] Sprint 계획 → [Stage 4] 구현 ⇄ [Stage 5] 검증 + 배포 → [Stage 6] 학습
  ↓                        ↑ 실패 시 복귀                          ↓
  └──────────────── Stage 3로 돌아감 (다음 Sprint) ←────────────────┘
```

- Stage 1~2는 프로젝트 초반 1회에 가깝다.
- Stage 3~6은 Sprint 단위로 반복한다.
- 핵심은 **설계는 먼저, 구현은 Sprint 단위로 좁혀서 반복**하는 것이다.

---

## Stage 1. 기획 + 아키텍처

- `/office-hours` 또는 `/autoplan`으로 문제, 수요 증거, 타겟 유저, 성공 기준을 먼저 고정한다.
- `/plan-eng-review`를 거쳐 기술 스택 ADR, ERD, API 명세를 만든다.
- 아키텍처는 이번 Sprint만이 아니라 **전체 Phase**를 기준으로 설계한다.
- 통과 조건은 다음 3가지다: 성공 기준 3개 이상, 기술 스택 ADR 완료, ERD와 API 명세 완료.

## Stage 2. 디자인

- `/design-consultation`으로 `DESIGN.md`를 만들고 색상, 타이포, 간격, 모션 기준을 잡는다.
- 빠른 검증은 코드 기반 디자인, 시각 탐색이 크면 디자인 파일 기반 경로를 선택한다.
- 어떤 경로를 택하든 결과물은 `DESIGN.md`, 핵심 화면, 디자인 토큰이다.
- 통과 조건은 `DESIGN.md` 확정과 핵심 화면 3개 이상 정리다.

## Stage 3. Sprint 계획

- Stage 1 산출물을 먼저 읽고 정합성을 확인한다.
- 이번 Sprint는 **Vertical Slice** 기준으로 자른다. 즉, FE와 BE를 관통하는 핵심 흐름 하나를 끝까지 닫는다.
- `brainstorming`으로 설계를 탐색하고 `writing-plans`로 파일, 순서, 의존성, 검증 기준을 고정한다.
- 계획 단계에서도 **Generator-Evaluator 루프**를 돌린다. Generator가 초안을 만들고, Evaluator가 빈 컨텍스트에서 결함과 누락을 찾는다.
- Evaluator는 구현자가 아닌 별도 세션에서 수행한다. 중간 규모 이상이거나 API, 인증, DB 경계가 걸리면 **Codex를 evaluator로 호출해 교차 검증**한다.
- Evaluator가 찾는 항목은 범위 누락, 순서 오류, 파일 경계 충돌, 검증 기준 부재, 롤백/마이그레이션 위험이다.
- 치명적 이슈가 있으면 plan을 다시 쓰고, 재검증한다. 구현은 evaluator가 막은 이슈가 정리된 뒤 시작한다.
- 병렬화는 파일 경계가 겹치지 않는 작업만 허용한다. 충돌 가능성이 있으면 분리하지 않는다.
- 통과 조건은 모든 task에 파일 경로와 검증 기준이 있고, 병렬 작업과 순차 작업이 분리되어 있는 상태다.

### 계획 단계 검증 루프

`brainstorming`/`writing-plans`로 초안을 만든 뒤 아래 순서를 반복한다.

1. Generator가 Sprint plan 초안을 작성한다.
2. Evaluator가 빈 컨텍스트에서 spec, ADR, 계획 문서만 보고 결함을 찾는다.
3. 일반 변경은 같은 모델의 독립 세션 또는 `/plan-eng-review`로 검증한다.
4. 중위험 이상 변경은 **Codex evaluator**를 추가해 교차 검증한다.
5. 이슈가 남아 있으면 plan을 수정하고 다시 evaluator에 건다.

구현 진입 조건:
- task별 파일 경로가 겹치지 않는다.
- 검증 기준이 task마다 있다.
- API, 상태, 데이터 경계가 문서에 명시되어 있다.
- Codex evaluator가 막은 치명적 이슈가 없다.

---

## Stage 4. 구현

- 기본 루프는 `writing-plans → subagent-driven-development → test-driven-development → /simplify → /browse`다.
- 구현은 태스크 단위로 반복한다. 각 태스크는 테스트 먼저, Red → Green → Refactor 순서로 닫는다.
- 테스트가 실패하면 `systematic-debugging`으로 원인을 재현하고 추적한 뒤 구현으로 복귀한다.
- FE 변경은 `/browse`로 실제 브라우저에서 확인한다. 스택 규칙은 `.ai/rules/frontend.md`, `.ai/rules/backend.md`, `.ai/rules/fullstack.md` 중 해당 문서를 따른다.
- 병렬화 기본 원칙은 단순하다. **파일 경계가 안 겹치면 분리하고, 겹치면 한 흐름으로 처리한다.**
- 막히는 세션은 오래 끌지 않는다. 같은 오류가 반복되거나 컨텍스트가 오염되면 새 세션으로 옮기고, 필요하면 Stage 3으로 돌아가 plan을 다시 쓴다.

### 구현 단계 최소 품질 게이트

- `unit + lint + type check`는 최소 게이트일 뿐, 완료 기준이 아니다.
- `verification-before-completion` 원칙을 따른다. 즉, 완료를 주장하기 전에 실제 실행 결과를 확인한다.
- unit test가 잡지 못하는 회귀가 있다. 런타임 환경, 통합 경계, 브라우저, 동시성, 리소스 누수는 실환경 스모크로 닫는다.
- 빌드와 실제 런타임 검증 없이 "통과했다"고 말하지 않는다.

상세 운영은 아래 문서를 본다.
- Claude 모드/승인 전략: `.ai/templates/claude-code-workflow.md`
- cmux 병렬 세션: `.ai/templates/cmux-skill.md`
- 장기 반복 자동화: `.ai/templates/ralph-loop.md`

---

## Stage 5. 검증 + 배포

Stage 5의 핵심은 **완료 주장보다 검증 증거가 먼저**라는 원칙이다. 순서는 `Verify → Review → QA → Ship → Monitor`이며, 증거가 부족하면 완료로 보지 않는다.

### 5a. Verify

- `verification-before-completion`을 적용한다. 테스트, lint/typecheck, build, 실제 실행 결과 중 무엇을 검증했는지 남긴다.
- FE 변경은 `/browse` 또는 Playwright smoke로 핵심 사용자 흐름을 실제 브라우저에서 확인한다. BE/DB는 integration test와 migration/rollback 가능 여부를 확인한다.
- 검증 중 버그가 나오면 `systematic-debugging`으로 재현→가설→추적→수정 순서로 닫는다.

### 5b. Review + QA

- `/review`로 Staff Engineer 수준 리뷰를 수행한다. SQL 안전성, 레이스 컨디션, N+1, 권한 경계, 타입 구멍을 우선 본다.
- 중위험 이상 변경은 빈 컨텍스트 evaluator 또는 Codex evaluator에 spec, ADR, plan, diff만 전달해 교차 검증한다.
- 리뷰에서 구조 문제가 나오면 Stage 4로, 설계 수정이 필요하면 Stage 3으로 되돌아간다.
- `/qa`로 통합 QA를 수행한다. 목표는 Health score 8+/10 또는 프로젝트 자체 기준 통과다.
- QA는 happy path만 보지 않는다. 빈 응답, 권한 오류, 네트워크 실패, 모바일 뷰포트, 느린 응답을 포함한다.

### 5c. Ship + Monitor

- `/ship` 전 테스트 결과, 리뷰 결과, 보안 감사, VERSION/CHANGELOG, PR 본문을 정리한다.
- 배포 전 migration 순서, rollback 절차, `.env.example` 동기화, production 스냅샷을 확인한다.
- 배포 후 `/canary` 또는 수동 체크로 핵심 사용자 흐름, 콘솔 에러, 5xx, p95, Web Vitals, 신규 critical 이슈를 확인한다.
- 1차 모니터링은 30분 이내, 2차 모니터링은 24시간 이내에 수행한다. 1차 실패는 rollback을 기본값으로 둔다.
- Git Safety Protocol은 그대로 유지한다. 커밋, 푸쉬, 배포는 사용자 승인 없이 진행하지 않는다.

통과 조건:
- 검증 증거가 남아 있음
- QA Health score 8+ 또는 자체 기준 통과
- CRITICAL 이슈 0개
- PR/배포/헬스체크 완료

## Stage 6. 학습

- 작업 중 나온 실수와 교훈은 즉시 `.ai/project/lessons.md`에 적는다.
- Sprint 말에는 `/retro`로 반복 패턴을 정리한다.
- 같은 패턴이 3회 반복되면 프로젝트 규칙 또는 공통 규칙으로 승격한다.
- 더 이상 필요 없는 규칙은 정기적으로 삭제한다.

---

## 핵심 원칙

1. 아키텍처는 전체를 보고, 실행은 Sprint 단위로 좁힌다.
2. Stage 3 없이 Stage 4로 뛰어들지 않는다.
3. Vertical Slice를 우선하고, FE/BE를 따로 완성하려 하지 않는다.
4. 계획도 구현처럼 `Generator → Evaluator → 수정` 루프로 검증한다. 중위험 이상은 Codex 교차 검증을 붙인다.
5. `TDD → verify → simplify → browse → review → qa → ship` 순서를 생략하지 않는다.
6. unit pass만으로 완료를 주장하지 않는다. 항상 실행 증거로 닫는다.
7. lessons.md를 남겨 반복 실수를 규칙으로 바꾼다.
8. 도구는 필요한 만큼만 쓴다. 과적재보다 명확한 기본 루프가 우선이다.
