# QuantBridge 문서 목차

> TradingView Pine Script → 백테스트 → 데모/라이브 트레이딩 플랫폼
> **찾는 게 없으면 여기부터.** 이 파일이 `docs/` 의 유일한 지도다.

---

## 어디를 읽어야 하나

| 질문                          | 위치                                                                                    |
| ----------------------------- | --------------------------------------------------------------------------------------- |
| **지금 뭘 하고 있나**         | [`status.md`](./status.md) — 활성 sprint                                                |
| **다음에 뭘 하나**            | [`roadmap.md`](./roadmap.md) — 남은 작업 로드맵                                         |
| **미해결 부채가 뭔가**        | [`backlog.md`](./backlog.md) — BL 원장                                                  |
| **이 시스템은 어떻게 생겼나** | [`reference/`](./reference/) — 도메인·아키텍처·API·환경                                 |
| **왜 그렇게 정했나**          | [`decisions/`](./decisions/) — ADR                                                      |
| **언제 무슨 일이 있었나**     | [`dev-log/INDEX.md`](./dev-log/INDEX.md) — sprint 회고                                  |
| **뭘 돌려야 통과인가**        | [`reference/gates-and-traps.md`](./reference/gates-and-traps.md) — 게이트 커맨드 + 함정 |
| **끝난 작업의 기록**          | [`archive/`](./archive/) — 읽기 전용                                                    |

새 AI 세션은 `CONTEXT.md` + `AGENTS.md` + `status.md` **3종만** 읽는다. 나머지는 필요할 때 연다.

---

## 디렉토리

| 위치                                               | 내용                                                                                           | 갱신 규칙                                                                                            |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [`reference/`](./reference/)                       | 도메인 모델·엔티티·상태머신·ERD·시스템 아키텍처·API·환경 설정·CI/CD                            | 코드와 어긋나면 **코드가 맞다**, 문서를 고친다                                                       |
| [`reference/prototypes/`](./reference/prototypes/) | 화면 프로토타입 — **FE 디자인 캐논 정본**. `design-canon-*.test.ts` 가 실제로 로드한다         | 캐논 변경 시에만                                                                                     |
| [`reference/infra/`](./reference/infra/)           | 배포·Observability·Runbook                                                                     | draft                                                                                                |
| [`reference/project/`](./reference/project/)       | 비전·포지셔닝·경쟁 지형                                                                        | 드묾                                                                                                 |
| [`decisions/`](./decisions/)                       | ADR 20건 (`001-`~`021-`)                                                                       | 폐기는 삭제가 아니라 **`Superseded` 표기**                                                           |
| [`dev-log/`](./dev-log/)                           | sprint 회고 + dogfood 기록 (append-only)                                                       | 새 항목 추가 시 `INDEX.md` 동시 갱신 (husky 훅이 확인)                                               |
| [`guides/`](./guides/)                             | 개발 방법론·sprint 템플릿·BL audit 체크리스트                                                  | 규칙 변경 시                                                                                         |
| [`reports/`](./reports/)                           | dogfood/retro 리포트 **출력 디렉토리** — 코드가 쓴다 (`config.py` `dogfood_report_output_dir`) | 자동 생성                                                                                            |
| [`archive/`](./archive/)                           | 완결 sprint 17종 + QA·감사·마케팅·superpowers 산출물                                           | **기존 항목 수정 금지.** 새 완결분 추가는 허용                                                       |
| `<테마>/` (예: `live-entry-wiring/`)               | **활성 스프린트 작업 디렉토리.** 스프린트당 최대 1개, 임시                                     | 종료 시 [§9](./guides/sprint-template.md) 로 **반드시 비운다**. 남아 있으면 그 스프린트는 안 닫힌 것 |

루트 문서 — [`../CONTEXT.md`](../CONTEXT.md) 도메인 헌법 · [`../AGENTS.md`](../AGENTS.md) 에이전트 진입점 · [`../DESIGN.md`](../DESIGN.md) 디자인 시스템 · [`../QUANTBRIDGE_PRD.md`](../QUANTBRIDGE_PRD.md) PRD · [`../.ai/rules/`](../.ai/rules/) 스택 규칙.

---

## 자주 여는 문서

| 문서                                                                                                               | 설명                                               |
| ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| [`reference/local-setup.md`](./reference/local-setup.md)                                                           | 로컬 개발 환경 5분 셋업                            |
| [`reference/env-vars.md`](./reference/env-vars.md)                                                                 | 환경 변수 의미·획득법                              |
| [`reference/domain-overview.md`](./reference/domain-overview.md)                                                   | 8 도메인 경계 + 책임 매트릭스                      |
| [`reference/entities.md`](./reference/entities.md)                                                                 | `ENT-###` 엔티티 카탈로그                          |
| [`reference/erd.md`](./reference/erd.md)                                                                           | 컬럼 정의 SSOT                                     |
| [`reference/system-architecture.md`](./reference/system-architecture.md)                                           | C4 다이어그램 + 인증/에러 경계                     |
| [`reference/supported-indicators.md`](./reference/supported-indicators.md)                                         | 지원 지표 목록 (엔진 에러 메시지가 인용)           |
| [`reference/endpoints.md`](./reference/endpoints.md)                                                               | API 엔드포인트 스펙                                |
| [`guides/sprint-template.md`](./guides/sprint-template.md)                                                         | sprint 종료 sweep — **§9 문서 생명주기 종결 포함** |
| [`guides/generator-evaluator-pipeline.md`](./guides/generator-evaluator-pipeline.md)                               | 구현=codex / 판정=Claude 분리 파이프라인 (G0~G8)   |
| [`decisions/003-pine-runtime-safety-and-parser-scope.md`](./decisions/003-pine-runtime-safety-and-parser-scope.md) | ADR-003: Pine 런타임 안전성 + 파서 범위            |

---

## 기술 스택

| 영역            | 기술                                                                        |
| --------------- | --------------------------------------------------------------------------- |
| Frontend        | Next.js 16, TypeScript, Tailwind CSS v4, shadcn/ui v4, React Query, Zustand |
| Backend         | FastAPI, Python 3.11+, SQLModel, Pydantic V2, Celery                        |
| Auth            | Clerk (Frontend + Backend JWT 검증)                                         |
| Database        | PostgreSQL + TimescaleDB + Redis                                            |
| Backtest Engine | `pine_v2` 자체 인터프리터 (SSOT) · vectorbt 는 지표 계산 전용               |
| Exchange        | CCXT (Bybit, Binance, OKX)                                                  |
| Infra           | Docker Compose (dev)                                                        |

```bash
docker compose up -d                                  # 인프라
cd frontend && pnpm install && pnpm dev               # FE
cd backend && uv sync && uvicorn src.main:app --reload # BE
```

---

## 문서를 늘리기 전에

이 `docs/` 는 2026-07-26 기준 최상위 **34개**까지 불어났었다. 고스타 오픈소스 90개를 실측했을 때
`docs/` 최상위 디렉토리 중앙값은 **1개**, 최대가 30개였다 — **우리가 표본 전체보다 많았다.**

원인은 분류 실패가 아니라 **완결된 것을 내리는 규칙이 없었던 것**이다. 그래서 규칙을 만들었다.

> **스프린트가 끝나면 그 문서를 승격(`reference/`) 하거나 강등(`archive/`) 한다. 그대로 두는 선택지는 없다.**
> — [`guides/sprint-template.md`](./guides/sprint-template.md) §9

새 디렉토리를 만들기 전에 자문한다. **누가 이 파일을 읽는가?** 사람이 다시 읽을 일이 없고
테스트도 로드하지 않는다면 그건 `archive/` 행이거나 애초에 쓰지 않아도 되는 문서다.
