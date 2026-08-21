# ADR — 왜 이 선택을 했는가

> **역할:** 변경하기 어렵거나 시스템에 큰 영향을 주는 결정의 **이유와 버린 대안**. 한 ADR = 한 결정.
> **불변:** Accepted 된 본문은 고치지 않는다. 결정이 바뀌면 **새 번호**를 쓰고 옛 것에 `Superseded` 한 줄을 단다.
> **번호:** 다음 번호 = 이 폴더의 최대 + 1. 결번(013)은 채우지 않는다 — 소급 작성은 [BL-658] 의 판정을 따른다.
> **아닌 것:** 스프린트 회고·완주 보고는 결정이 아니다. 초기 회차(012·014~018)가 이 폴더에 남아 있는 것은
> **역사**이고, 새로 넣지 않는다 — 회고는 반증 카드 → `../lessons.md`, 색인은 `../dev-log/INDEX.md`(ADR-026 §3).

## 색인

| ADR                                                              | 결정                                           | 종류           | 비고                                 |
| ---------------------------------------------------------------- | ---------------------------------------------- | -------------- | ------------------------------------ |
| [001](./001-tech-stack.md)                                       | 기술 스택                                      | 결정           |                                      |
| [002](./002-parallel-scaffold-strategy.md)                       | 병렬 스캐폴딩 전략                             | 결정           |                                      |
| [003](./003-pine-runtime-safety-and-parser-scope.md)             | Pine 런타임 안전성 + 파서 범위                 | 결정           |                                      |
| [004](./004-pine-parser-approach-selection.md)                   | Pine 파서 접근법                               | 결정           |                                      |
| [005](./005-datetime-tz-aware.md)                                | DateTime tz-aware + `AwareDateTime`            | 결정           |                                      |
| [006](./006-sprint6-design-review-summary.md)                    | Sprint 6 Trading 데모 설계 리뷰 + 3 결정       | 결정           | 리뷰 결과를 겸한다                   |
| [007](./007-sprint7a-futures-decisions.md)                       | Bybit Futures + Cross Margin 사전 결정         | 결정           |                                      |
| [008](./008-sprint7c-scope-decision.md)                          | Sprint 7c FE 따라잡기 스코프                   | 결정           |                                      |
| [009](./009-shadcn-v4-form-radix-exception.md)                   | shadcn/ui v4 규칙 예외(`form.tsx`)             | 결정           |                                      |
| [010a](./010a-dev-cpu-budget.md)                                 | Dev CPU Budget + Next.js 안티패턴              | 결정           |                                      |
| [010b](./010b-product-roadmap.md)                                | Product Roadmap 프레임                         | 결정           |                                      |
| [011](./011-pine-execution-strategy-v4.md)                       | Pine 실행 전략 v4 — 3-Track                    | 결정           |                                      |
| [012](./012-sprint-8a-tier0-final-report.md)                     | Sprint 8a Tier-0 Final Report                  | **보고(역사)** | 결정 아님                            |
| 013                                                              | —                                              | **결번**       | 실체는 git 에만([BL-658])            |
| [014](./014-sprint-8b-8c-pine-v2-expansion.md)                   | Sprint 8b+8c pine_v2 Tier-1                    | **회고(역사)** |                                      |
| [015](./015-sprint-7d-okx-sessions.md)                           | Sprint 7d OKX Adapter + Sessions               | **회고(역사)** |                                      |
| [016](./016-sprint-y1-coverage-analyzer.md)                      | Sprint Y1 Pine Coverage Analyzer               | **회고(역사)** |                                      |
| [017](./017-fe-polish-bundle-1-2-retro.md)                       | FE Polish Bundle 1/2                           | **회고(역사)** |                                      |
| [018](./018-sprint12-ws-supervisor-and-exchange-stub-removal.md) | WS Supervisor + Exchange stub 제거             | **회고(역사)** |                                      |
| [019](./019-worker-auto-rebuild.md)                              | Docker worker auto-rebuild                     | 결정           |                                      |
| [020](./020-trust-layer-ci-design.md)                            | Trust Layer CI 3-Layer Parity                  | 결정           |                                      |
| [021](./021-backtest-idempotency-dual-lock.md)                   | backtest 멱등성 dual-lock 유지                 | 결정           |                                      |
| [022](./022-engine-position-ssot.md)                             | 엔진 포지션 SSOT — 원장이 진실                 | 결정           |                                      |
| [023](./023-engine-state-ssot.md)                                | 엔진 상태 SSOT — 영속 상태                     | **Proposed**   | 사용자 판정 대기                     |
| [024](./024-soak-stability-gate.md)                              | 「데모 1주 안정」의 조작적 정의                | 결정           |                                      |
| [025](./025-conditional-fill-ownership.md)                       | 조건부 진입 체결의 소유권                      | 결정           |                                      |
| [026](./026-documentation-ssot.md)                               | 문서 SSOT 7축 + 로드 계층화                    | 결정           | §2 → 027 · §1④ 위치 → 038 Superseded |
| [027](./027-nested-agents-md.md)                                 | 스택 규칙 = 디렉터리별 `AGENTS.md`             | 결정           |                                      |
| [028](./028-backlog-deferred-verdict.md)                         | 원장 판정어 `DEFERRED`                         | 결정           |                                      |
| [029](./029-monorepo-standard-layout.md)                         | 모노레포 표준 배치 apps/·tools/·infra/         | 결정           |                                      |
| [030](./030-harness-pilot-verdict.md)                            | 러너 파일럿 종결 — 조종 장치 철거              | 결정           |                                      |
| [031](./031-api-contract-axis-poc.md)                            | API 계약축 PoC — OpenAPI export                | 결정           | PoC 범위                             |
| [032](./032-position-mode-verdict.md)                            | 포지션 모드 one-way 유지                       | 결정           |                                      |
| [033](./033-db-hosting-self-host-timescaledb.md)                 | DB 호스팅 self-host TimescaleDB                | 결정           |                                      |
| [034](./034-auth-self-host-better-auth.md)                       | 인증 Clerk → self-host Better Auth             | 결정           |                                      |
| [035](./035-fe-component-ownership.md)                           | FE 컴포넌트 소유권 = feature                   | 결정           |                                      |
| [036](./036-tool-version-ssot-mise.md)                           | 도구 버전 SSOT = `mise.toml`                   | 결정           |                                      |
| [037](./037-harness-zero-base.md)                                | 하네스 제로베이스 — 검사기 전량 철거           | 결정           | 복원 = 태그 `harness-v1`             |
| [038](./038-docs-top-level-by-question.md)                       | `docs/` 최상위 질문별 분할 — `reference/` 해체 | 결정           | 복원 = `c3b35e5f`                    |

## 새 ADR 을 쓸 때

1. 대상인가 — 되돌리기 어렵거나 여러 앱·층에 걸치는 선택. 변수 이름·작은 라이브러리 교체·스프린트 계획은 아니다.
2. 헤더 = `상태 / 일자 / 결정자 / 관련 / 대체함 / 복원 원본`(있으면). 본문 = Context → Decision → Consequences → 재평가 트리거.
3. **버린 대안을 적는다.** 같은 추천을 다시 받았을 때 다시 논하지 않기 위해서다.
4. 이 표에 한 줄을 더한다.
