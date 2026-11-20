# QuantBridge — Pine Script 전략 → 백테스트 · 데모 트레이딩 퀀트 플랫폼

> 새 세션은 `GLOSSARY.md`(용어 정본) → 이 파일 → `docs/status.md` 순으로 읽는다.
> `GLOSSARY.md` 는 자동 로드되지 않는다 — `CLAUDE.md` 가 import 하는 것은 이 파일 하나다.
> 다음에 할 일은 `docs/status.md` 의 살아 있는 `다음 행동 =` 한 줄이다. 별도 킥오프 파일을 만들지 않는다.
>
> 이 파일은 **코드가 말하지 못하는 것**만 갖는다([ADR-047](./docs/adr/047-agent-rules-as-enforcer-table.md)).
> 스택·폴더 구조·명령·CI 단계는 코드가 정본이다. 절 번호는 옮기지 않는다 — 코드와 문서가 인용한다.

## 1. 프로젝트

TradingView Pine Script 전략을 가져와 **같은 코드로** 백테스트 → 스트레스 테스트 → 데모 트레이딩까지
연결하는 웹 퀀트 플랫폼. 핵심은 기능 수가 아니라 **결과와 가정이 얼마나 정직하게 보이는가**다.

핵심 도메인은 Strategy(`pine_v2` 인터프리터) · Backtest · Stress Test · Optimizer · Trading(CCXT 주문) ·
Market Data(TimescaleDB) 여섯이다.

**제품 결정 3건**(2026-08-23 사용자) — 실자금(mainnet)에 가지 않는다(계정은 Bybit demo 만) ·
Beta 를 외부에 열지 않는다 · 거래소는 Bybit 하나다.
범위 전문 = [`docs/PRD.md`](./docs/PRD.md) · 용어 = [`GLOSSARY.md`](./GLOSSARY.md) · 도메인 관계 = [`도메인 개요`](./docs/domain/domain-overview.md).

## 2. 기술 스택

정본은 코드다 — `mise.toml`(도구 버전) · `apps/api/pyproject.toml` · `apps/web/package.json` · `docker-compose.yml`.
코드만 봐서는 놓치기 쉬운 것:

- 백엔드는 JWT 를 **JWKS 공개 키로 검증만** 한다. 백엔드가 쥐는 인증 시크릿은 없다([ADR-034](./docs/adr/034-auth-self-host-better-auth.md)).
- LLM provider 순서는 코드가 아니라 설정 `LLM_PROVIDER_ORDER` 가 정한다. 호출부는 `strategy/narrative/providers.py` 한 곳이다.
- lint 는 BE `ruff`, FE `biome` 단독이다([ADR-039](./docs/adr/039-frontend-biome.md)).
- 도구 버전 숫자는 `mise.toml` 에만 적는다([ADR-036](./docs/adr/036-tool-version-ssot-mise.md)). 예외는 Dockerfile 이다.

## 3. Golden Rules

| 하지 않는 것 | 이유 | 집행 |
| --- | --- | --- |
| 환경 변수·API 키·시크릿을 코드에 하드코딩 | 히스토리에 실제 키가 들어간 적이 2회 있다. `SecretStr` 을 쓴다 | `ruff` `S` 가 일부 문자열 패턴만 본다. 전용 스캐너 없음 |
| Repository layer 밖에서 DB 접근 | service 가 세션을 쥐면 DB 없이 단위 테스트를 못 한다 | `tests/common/test_repository_boundary_guard.py` · `tests/trading/test_router_layer_boundary.py` |
| `.env.example` 에 없는 환경 변수를 코드에서 참조 | 배포 호스트가 그 값을 안 넣어 조용히 다르게 동작한다 | `tests/common/test_env_example_contract.py` |
| AI 세션이 main/master 에 직접 push | main 에 들어간 커밋은 PR CI 없이 `release.yml` 이 곧바로 운영에 배포한다 | `.husky/pre-push` — 터미널이 없으면 거부한다 |
| LLM 이 생성한 규칙 파일을 검토 없이 사용 | — | 없음 |
| 워크트리에서 `mise run up`/`down`/`migrate`/`seed` | 컨테이너와 앱 DB 는 1벌 공유라 함께 깨진다 | `tools/scripts/assert-main-checkout.sh`(해당 mise task 가 부른다) |
| 워크트리에서 celery 경유 검증(백테스트·라이브신호·옵티마이저) | worker 가 메인의 `src` 를 mount 하므로 **내 코드가 아니라 메인 코드가 돈다**(침묵 실패) | 없음. 정본 = [`worktree-parallel.md`](./docs/development/worktree-parallel.md) |
| `DATABASE_URL` 만 단독 주입(서브에이전트 포함) | 세션 픽스처의 `drop_all` 이 개발 DB 를 겨냥한다 | `tests/conftest.py` 가 세션을 끝낸다 · `tests/test_destructive_db_guard.py` |

사람은 main 에 직접 push 할 수 있다(개인 레포 — 2026-10-02 사용자 결정). `pre-push` 가 터미널로 `[y/N]` 을 묻는다.
작업 브랜치 push 와 `gh pr create` 는 승인 없이 한다.

## 4. 개발 원칙

- 사고·계획·대화·문서·주석은 한국어, 코드 네이밍과 커밋 메시지는 영어로 쓴다.
- 코드를 쓰기 전에 어떤 설계 문서를 따라 어떤 방향으로 갈지 짧게 알린다. 코드를 고치면 관련 문서를 같은 세션에 고친다.
- 확인된 사실, 추론(`[가정]`), 확인 필요(`[확인 필요]`)를 구분해 적는다.
- 승인이 필요한 것은 **배포 · 실주문 · 남의 데이터 삭제** 셋뿐이다. 커밋·작업 브랜치 push·PR 생성은 승인 없이 PR 까지 간다.
- green 은 CI 가 판정한다([ADR-037](./docs/adr/037-harness-zero-base.md)). 단계의 정본은 `.github/workflows/ci.yml` 이다. 미리 보려면 §5 의 명령을 직접 돌린다.
- 착수 전에 baseline 을 다시 잰다. 인상, plan 의 가정, 프롬프트의 가정은 실측 전에는 믿지 않는다.
- codex 가 낸 finding 은 코드와 대조한 뒤에만 채택한다.
- 리뷰 도구는 `/qb-review`(체크리스트 1패스)와 `/review-code`(차원별 병렬 + 회의론자 다수결) 둘이다.
- 규칙은 가장 높은 단에서 고친다 — 구조 → 타입·lint → 테스트 → 문장([ADR-047]). 같은 교정을 두 번 하게 되면
  문장을 굵게 하지 말고 집행기를 만든다. 검사기는 문서화된 사고가 있을 때만 더한다([ADR-037]).
- 복잡한 설계는 Mermaid.js 로 그린다.
- 메타-방법론 전문 = [`generator-evaluator-pipeline.md`](./docs/development/workflows/generator-evaluator-pipeline.md) §8

외부 engineering 스킬을 쓸 때는 [`CLAUDE.md` 의 Agent skills](./CLAUDE.md#agent-skills)를 먼저 읽는다.

## 5. 명령어

전체 목록은 `mise tasks` 다. 코드만 봐서는 틀리기 쉬운 것:

```bash
# BE pytest 는 .env.local 을 통째로 소싱한다 (DATABASE_URL 단독 주입은 §3)
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest

cd apps/api && uv run mypy src
cd apps/api && uv run python scripts/export_openapi.py --check   # OpenAPI drift
cd apps/web && pnpm exec biome check .
./tools/scripts/ledger-vitals.sh
```

- **판정 명령에 파이프를 붙이지 않는다.** `pytest ... | tail` 은 pytest 가 아니라 `tail` 의 rc 를 읽는다.
  rc 를 먼저 잡고 출력은 나중에 자른다.
- 워크트리 병렬은 슬롯으로 한다. `./tools/scripts/worktree-bootstrap.sh --adopt-env` 가 포트·테스트 DB·env 를 붙인다.
- CI 는 `ruff format` 을 재지 않는다. format 드리프트는 red 가 아니다.

## 6. 문서 — 어느 질문은 어디가 답하나 ([ADR-026](./docs/adr/026-documentation-ssot.md))

| 질문 | 정본 |
| --- | --- |
| 지금 실행할 일 | `docs/status.md` — 살아 있는 `다음 행동 =` 1개 |
| 제품이 뭐고 무엇을 안 하나 | `docs/PRD.md` |
| 열린 결함 | `docs/backlog.md`(ACTIVE ∪ PARTIAL) · `docs/backlog-deferred.md`(DEFERRED) |
| **왜** 그렇게 정했나 | `docs/adr/` — 결정 / 이유 / 트레이드오프. 회차 발견을 여기 쌓지 않는다 |
| 무엇이 **반증**됐나 | `docs/lessons.md` |
| 구현 계약 | `docs/{architecture,domain,api,development,operations,design}/` ([ADR-038](./docs/adr/038-docs-top-level-by-question.md)) |
| 과거 원문 | git — 삭제할 때 tombstone(무엇을 + 어디로 + SHA) 1줄을 남긴다 |

- 코드와 문서가 어긋나면 **코드가 맞다** — 「지금 무엇을 하는가」에 한해서다.
  「왜 그렇게 했나」(`adr/`)와 「무엇이 반증됐나」(`lessons.md`)에 대해 코드는 증인이 아니다.
- 판정어는 `ACTIVE`(단독 착수 가능) / `DEFERRED`(트리거 미도래) / `PARTIAL` / `RESOLVED` / `UNKNOWN` 다섯이다.
  DEFERRED 는 active 로 세지 않지만 「미완」 쪽이다([ADR-028](./docs/adr/028-backlog-deferred-verdict.md)).
  RESOLVED 는 파일로 옮기지 않고 지운다 — 끝난 것은 git 이 갖는다.
- 끝난 회차 기록은 어느 문서에도 쌓지 않는다. 커밋 메시지와 git log 가 정본이다.
- 요약 줄은 `dev-log/INDEX.md` 300자, `backlog*.md` 1,000자를 넘기지 않는다(집행 없음).
- 스프린트가 끝나면 작업 문서는 승격·강등·삭제 중 하나로 닫는다. 회고는 반증 카드 → `lessons.md` → INDEX 한 줄이다.
- ID 는 `SCR-` 화면 / `API-` API / `ENT-` 엔티티 / `REQ-` 기능 / `BL-` 백로그다. 재사용하지 않는다.

## 7. 자동화 — 무엇이 기계로 집행되나

| 무엇 | 집행 |
| --- | --- |
| main/master push 확인 · 메인 체크아웃의 브랜치 접두사(`stage\|feat\|fix\|chore\|docs\|test\|refactor\|hotfix/*`) | `.husky/pre-push`. 워크트리에서는 판정하지 않는다 |
| `docs/status.md` 진입점 — 살아 있는 `다음 행동 =` 이 정확히 1개이고 `PRD.md` §5 를 겨냥 · ⓪ 표에 행이 있음 · `backlog.md` 에 RESOLVED 없음 | pre-commit `tools/scripts/ledger-vitals.sh` |
| 스테이지된 파일의 lint·format | pre-commit lint-staged |
| 품질 게이트(lint · OpenAPI drift · 타입 · 테스트 · 빌드) | CI `.github/workflows/ci.yml` |
| codex 의 위험 명령 | `tools/scripts/hooks/` |
| 지침을 읽은 모델이 규칙을 실제로 적용하는가 | `evals/harness`(수동 실행 · API 키 필요) |

스택별 「규칙 ↔ 집행」 표는 §8 의 하위 파일 끝에 있다.

## 8. 스택 규칙 — 하위 `AGENTS.md` 2종

`apps/api/` 와 `apps/web/` 에 각각 `AGENTS.md`(규칙)와 `CLAUDE.md`(`@AGENTS.md` 한 줄)를 둔다.
Claude Code 는 그 디렉터리의 파일을 읽는 순간 하위 `CLAUDE.md` 를 로드하고, codex 는 가까운 `AGENTS.md` 를
직접 읽는다([ADR-027](./docs/adr/027-nested-agents-md.md)). 파일을 열지 않고 설계만 논하는 세션에서는 직접 연다.

하위 파일은 루트를 덮어쓰지 않고 보강만 한다. Claude 는 루트와 하위를 이어붙이고 codex 는 가까운 것만 봐서,
충돌하는 문장을 쓰면 두 도구가 다르게 행동한다.

| 파일 | 무엇을 갖나 |
| --- | --- |
| [`apps/api/AGENTS.md`](apps/api/AGENTS.md) | 3-Layer 7파일 표준과 예외 표 · Decimal-first · JWT/JWKS 검증 · Alembic · Celery prefork-safe · 검사기 판별 절차 |
| [`apps/web/AGENTS.md`](apps/web/AGENTS.md) | 인증 seam · React Hooks 안전 H-1~H-3 · 레이어 경계 · Next.js 16 · Zod v4 · shadcn v4 · 반응형 · TS 컨벤션 |

지침 파일에는 코드로 읽히지 않는 구조·경계·금지와 「규칙 ↔ 집행」 표를 둔다. 예제와 절차는 `docs/` 에, 이력은 git 에 둔다.

## 9. 경로 → 용도

| 경로 | 무엇 |
| --- | --- |
| `apps/api/src/<도메인>/` | router · service · repository · schemas · models · dependencies · exceptions (7파일 표준) |
| `apps/api/src/strategy/pine_v2/` | Pine 인터프리터 정본 |
| `apps/web/src/` | Next.js FSD Lite. 화면 컴포넌트의 기본 자리는 `features/<domain>/components/` 다([ADR-035](./docs/adr/035-fe-component-ownership.md)) |
| `tools/scripts/` | 운영 런타임(`deploy`·`host-bootstrap`·`docker-reclaim`·`db-backup`·`disk-guard`) · 가드 · `ledger-vitals` · `hooks/` |
| `docs/` | `status`·`PRD`·`backlog*` + 정본 6축 + `adr/` + `lessons.md` (지도 = [`docs/README.md`](./docs/README.md)) |
| `.claude/` · `evals/harness/` | 리뷰 커맨드와 `workflows/review-code.js` · 지침 Eval |
