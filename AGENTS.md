# QuantBridge — Pine Script 전략 → 백테스트 · 데모 트레이딩 퀀트 플랫폼

> **새 AI 세션 첫 step — 3종만 읽는다.** `CONTEXT.md`(용어/관계 SSOT) + 본 파일 + `docs/status.md`.
> ★**`CONTEXT.md` 는 자동 로드가 아니다 — 읽어야 들어온다.** `CLAUDE.md` 가 import 하는 것은 본 파일 **하나뿐**이다.
> ★**`docs/status.md` 의 살아 있는 `다음 행동 =` **하나**가 다음에 무엇을 할지의 유일한 진입점이다.**
> 별도 킥오프 파일을 만들지 않는다.
> 본 파일은 **오리엔테이션 전용**이다([ADR-026](./docs/adr/026-documentation-ssot.md)) — 규칙 본문은 §8 의 하위 `AGENTS.md` 가 갖는다.

| 무엇을 찾나 | 어디 |
| --- | --- |
| 이 제품이 뭔가 · 무엇을 안 하나 | §1 · 전문 = [`docs/PRD.md`](./docs/PRD.md) |
| 뭘로 만들어졌나 | §2 |
| 어기면 안 되는 것 | §3 Golden Rules |
| 어떻게 일하나 (승인·green·리뷰) | §4 |
| 어떤 명령을 치나 | §5 |
| 어느 문서가 무슨 질문에 답하나 | §6 |
| 무엇이 기계로 집행되나 (훅·CI) | §7 |
| BE/FE 코드 규칙 | §8 → `apps/api/AGENTS.md` · `apps/web/AGENTS.md` |
| 어느 디렉터리가 뭘 하나 | §9 |

---

## 1. 프로젝트

TradingView Pine Script 전략을 가져와 **같은 코드로** 백테스트 → 스트레스 테스트 → 데모 트레이딩까지
연결하는 웹 퀀트 플랫폼. 핵심은 기능 수가 아니라 **결과와 가정이 얼마나 정직하게 보이는가**다.

**핵심 도메인 6종** — Strategy(`pine_v2` 인터프리터) / Backtest / Stress Test / Optimizer /
Trading(CCXT 주문) / Market Data(TimescaleDB).

★**현재 제품 결정 3건**(2026-08-23 사용자) — **실자금(mainnet) 안 간다**(계정 모드 = **Bybit demo 만**) ·
**Beta 외부 공개 안 연다**(실사용자 0명) · **멀티 거래소 안 한다**(Bybit 하나).
범위·비범위 전문 = [`docs/PRD.md`](./docs/PRD.md) · 용어·관계 SSOT = [`CONTEXT.md`](./CONTEXT.md).

## 2. 기술 스택

- **BE** — FastAPI(100% async) · SQLModel + SQLAlchemy 2.0(`asyncpg`) · Pydantic V2 · `uv`
- **DB** — PostgreSQL + **TimescaleDB hypertable**(OHLCV) · Redis(Celery broker + 락)
- **Worker** — Celery prefork(`_WORKER_LOOP` 통일 — `apps/api/AGENTS.md` §9)
- **FE** — Next.js 16(App Router) · TypeScript strict · Tailwind · shadcn v4 · Zod v4 · Zustand · `pnpm`
- **인증** — self-host Better Auth. 백엔드는 JWT 를 **JWKS 공개 키로 검증만** 한다([ADR-034](./docs/adr/034-auth-self-host-better-auth.md)) — 백엔드가 쥐는 인증 시크릿이 **없다**
- **거래소** — CCXT(Bybit demo) · **LLM** — provider **순서는 코드가 아니라 설정**이 정한다
  (`LLM_PROVIDER_ORDER` = `anthropic`·`openai`·`gemini` 중 쉼표 목록). 브리핑 해설·전략 생성의 호출부는
  `strategy/narrative/providers.py` **한 곳**이고 세 provider 모두 **스키마를 강제**한다.
  `strategy/convert/service.py`도 같은 층의 `complete_json` 계약을 쓰며, `converted_code` JSON schema와
  실제 provider·token usage를 소비한다.
- **테스트** — BE `pytest` · FE `vitest` + Playwright e2e · **lint 는 BE `ruff` / FE `biome` 단독**([ADR-039](./docs/adr/039-frontend-biome.md))
- **도구 버전 SSOT = 루트 `mise.toml` 하나**([ADR-036](./docs/adr/036-tool-version-ssot-mise.md)) — 숫자를 다른 곳에 적지 마라(예외는 Dockerfile 2곳)

## 3. Golden Rules (Immutable)

- **NEVER** — 환경 변수·API 키·시크릿을 코드에 하드코딩. **이유:** 히스토리에 실제 키가 들어간 적이 2회 있다. `SecretStr` 을 써라
- **NEVER** — Repository layer 밖에서 DB 접근. **이유:** service 가 세션을 쥐면 DB 없이 단위 테스트가 불가능해진다(`apps/api/AGENTS.md` §3)
- **NEVER** — `.env.example` 에 없는 환경 변수를 코드에서 참조. **이유:** 배포 호스트가 그 값을 안 넣어 조용히 다르게 동작한다(2026-08-15 `/docs` 인터넷 노출 실사고)
- **NEVER** — **main/master 직접 push**(영구 차단 · bypass 불가 · PR 경유 의무).
  ★**작업 브랜치 push 와 `gh pr create` 는 승인 없이 해도 된다**(2026-08-22 사용자 결정) —
  기계 집행 `.husky/pre-push` 도 처음부터 그랬다(main/master 만 거부). 막고 있던 것은 이 문서였다
- **NEVER** — LLM 생성 규칙 파일을 검토 없이 그대로 사용
- **NEVER** — 워크트리에서 `mise run up`/`down`/`migrate`/`seed`. **이유:** 컨테이너·앱 DB 는 1벌 공유라 함께 깨진다
- **NEVER** — 워크트리에서 celery 경유 검증(백테스트·라이브신호·옵티마이저). **이유:** worker 가 메인의 `src` 를 mount 하므로 **내 코드가 아니라 메인 코드가 돈다**(침묵 실패). 정본 = [`worktree-parallel.md`](./docs/development/worktree-parallel.md)
- **NEVER** — `DATABASE_URL` 만 단독 주입(서브에이전트 포함). **이유:** 세션 픽스처 `drop_all` 이 **개발 DB 를 겨냥**한다. §5 의 통째 소싱을 써라

## 4. 개발 원칙

- **ALWAYS** — 사고/계획/대화/문서/주석 = **한국어**, 코드 네이밍/커밋 메시지 = **영어**
- **ALWAYS** — 코드 작성 전 「어떤 설계 문서 + 어떤 방향」 짧게 브리핑. 코드 수정 시 관련 문서 **같은 세션** 갱신
- **ALWAYS** — 확인된 사실 / 추론(`[가정]`) / 확인 필요(`[확인 필요]`) 구분 표기
- **ALWAYS** — 승인이 필요한 것은 **배포 · 실주문 · 남의 데이터 삭제** 셋뿐. 커밋·작업 브랜치 push·PR 생성은 **승인 불요** — 거기서 멈추지 말고 **PR 까지 올려라**
- **ALWAYS** — **green = CI 단일 게이트**([ADR-037](./docs/adr/037-harness-zero-base.md)). 로컬 pre-flight 의식 없음 — PR 을 올리면 CI(be: `ruff`+`pytest` / fe: `biome`+`tsc`+`vitest`+`build`)가 판정한다. 미리 보려면 §5 의 러너를 직접 돌려라
- **ALWAYS** — `gh pr create` 전 `docs/status.md` 에 **살아 있는 `다음 행동 =` 이 둘 이상이면 안 된다**. 끝난 것은 `~~옛 문장~~ → **날짜 + 새 사실**` 로 바꾼다. 기계 집행 = pre-commit 의 `ledger-vitals.sh` 3축
- **ALWAYS** — Sprint kickoff 첫 step = **baseline 재측정 preflight**. 본인 인상·plan 가정·사용자 prompt 가정 **모두 실측 전 신뢰 금지**
- **ALWAYS** — codex finding 은 **코드 대조 후에만** 채택 (phantom finding 차단)
- 리뷰 도구는 **둘** — `/qb-review`(체크리스트 1패스, 가벼운 변경) · `/review-code`(3차원 병렬 + finding 당 skeptic 3명 2/3 다수결, 무거운 변경)
- ★**[ADR-037] 재입힘 규칙** — 하네스는 추측으로 자라지 못한다. **문서화된 사고 1건 = 슬림 복귀 1건**만 허용하고 복귀는 최소판으로. 철거 전 원문 = git 태그 `harness-v1`
- 역할 = **Senior Tech Lead + System Architect**. 완전한 코드(`...` 생략 금지), 복잡한 설계는 Mermaid.js
- 나머지 메타-방법론 전문 = [`generator-evaluator-pipeline.md`](./docs/development/workflows/generator-evaluator-pipeline.md) §8

## 5. 명령어

```bash
mise run up            # 컨테이너 기동 → 3000/8000/5432/6379
mise run be            # 백엔드만    ·  mise run fe   # 프런트만
mise run up-isolated   # 격리 슬롯   → 3100/8100/5433/6380
mise tasks             # 전체 목록   ·  mise run help ·  mise ls  # 도구 버전 + 출처

# ★ALWAYS — BE pytest 는 .env.local 을 **통째로** 소싱한다 (DATABASE_URL 단독 주입 금지 — §3)
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest

cd apps/api && uv run mypy src                # BE 타입 (차단 게이트)
cd apps/api && uv run python scripts/export_openapi.py --check   # OpenAPI drift (차단 게이트)

cd apps/web && pnpm exec biome check .        # FE lint (단독 게이트)
./tools/scripts/ledger-vitals.sh              # 원장 3축
```

★**판정 명령에 파이프를 붙이지 마라** — `pytest ... | tail` 은 pytest 가 아니라 **tail 의 rc** 를 읽는다.
이 레포에서 10회 이상 재발했다. rc 를 먼저 잡고 텍스트는 나중에 잘라라.

★**워크트리 병렬 = 슬롯**(FE `3100+N` / BE `8100+N` / pytest DB `quantbridge_w{N}_test`).
`./tools/scripts/worktree-bootstrap.sh --adopt-env` 가 슬롯·테스트DB·env 를 붙인다.
herdr 함대 래퍼는 2026-08-13 제거됐다([ADR-030](./docs/adr/030-harness-pilot-verdict.md)).

## 6. 문서 — 어느 질문은 어디가 답하나 ([ADR-026](./docs/adr/026-documentation-ssot.md))

| 질문 | 정본 |
| --- | --- |
| 지금 실행할 일 | `docs/status.md` — 살아 있는 `다음 행동 =` **1개** |
| 제품이 뭐고 무엇을 안 하나 | `docs/PRD.md` |
| 열린 결함 | `docs/backlog.md`(ACTIVE ∪ PARTIAL) · `docs/backlog-deferred.md`(DEFERRED) |
| **왜** 그렇게 정했나 | `docs/adr/` — **결정 / 이유 / 트레이드오프**. 회차 발견을 여기 쌓지 마라 |
| 무엇이 **반증**됐나 | `docs/lessons.md` |
| 구현 계약 | `docs/{architecture,domain,api,development,operations,design}/` ([ADR-038](./docs/adr/038-docs-top-level-by-question.md)) |
| 과거 원문 | **git** — 삭제 시 tombstone(무엇을+어디로+SHA) 1줄 의무 |

- 코드와 문서가 어긋나면 **코드가 맞다** — 단 「지금 무엇을 하는가」에 한해서다.
  「왜 그렇게 했나」(`adr/`)와 「무엇이 반증됐나」(`lessons.md`)에 대해 **코드는 증인이 아니다**
- ★**판정어 5종** — `ACTIVE`(단독 착수 가능) / `DEFERRED`(트리거 미도래) / `PARTIAL` / `RESOLVED` / `UNKNOWN`.
  DEFERRED 는 active 로 안 세지만 「미완」 쪽이다([ADR-028](./docs/adr/028-backlog-deferred-verdict.md)).
  ★**RESOLVED 는 파일이 아니라 삭제다**(2026-08-23) — 끝난 것은 git 이 갖는다
- ★**끝난 회차 기록은 어느 문서에도 쌓지 않는다** — 커밋 메시지와 git log 가 정본이다.
  이 규칙이 없어서 `status.md` 가 124KB, `roadmap.md` 가 550줄, ADR 하나가 72KB 가 됐다(2026-08-23 실측)
- **ALWAYS** — 요약 줄 길이 상한: `dev-log/INDEX.md` **300자** · `backlog*.md` **1,000자**(기계 강제 없음 — 스스로 지켜라)
- **ALWAYS** — 스프린트 종료 시 작업 문서는 승격·강등·삭제 중 하나로 종결. 회고는 **반증 카드 → `lessons.md` → INDEX 한 줄**
- ID 체계: `SCR-` 화면 / `API-` API / `ENT-` 엔티티 / `REQ-` 기능 / `BL-` 백로그. **ID 재사용 금지**

## 7. 자동화 — 무엇이 기계로 집행되나

| 훅/게이트 | 무엇을 막나 |
| --- | --- |
| `.husky/pre-push` | main/master 직접 push (`stage\|feat\|fix\|chore\|docs\|test\|refactor\|hotfix/*` 는 통과) |
| pre-commit `ledger-vitals.sh` | `다음 행동` ≤1 · ⓪ 표 ≥1행 · RESOLVED 역류 0 |
| pre-commit lint-staged | 스테이지된 `.py` 에 `ruff check --fix` + `ruff format` |
| CI (`.github/workflows/ci.yml`) | **유일한 품질 게이트** — be: `ruff check .` → `scripts/export_openapi.py --check`(OpenAPI drift) → `mypy src` → `pytest` 전량 / fe: `biome`+`tsc`+`vitest`+`build` |
| `tools/scripts/hooks/` | codex 레이어 가드 (위험 명령 차단) |

★**CI 는 `ruff format` 을 안 잰다** — 레포에 format 드리프트가 상시 있고 그것은 red 가 아니다.

## 8. 스택 규칙 — 하위 `AGENTS.md` 2종

★`apps/api/` · `apps/web/` 에 각각 `AGENTS.md`(규칙 본문) + `CLAUDE.md`(`@AGENTS.md` 한 줄)를 둔다.
Claude Code 는 **그 디렉터리의 파일을 읽는 순간** 하위 `CLAUDE.md` 를 로드하고 import 를 따라
`AGENTS.md` 까지 편다(2026-08-07 실측). codex 는 `AGENTS.md` 를 직접 읽는다([ADR-027](./docs/adr/027-nested-agents-md.md)).
**파일을 안 열고 설계만 논하는 세션에서는 직접 열어라.**

★**하위는 루트를 덮어쓰지 말고 보강만 해라** — Claude 는 루트와 하위를 **이어붙이고** codex 는
**가까운 것만** 본다. 충돌하는 문장을 쓰면 두 도구가 다르게 행동한다.

| 파일 | 무엇을 갖나 |
| --- | --- |
| [`apps/api/AGENTS.md`](apps/api/AGENTS.md) | 3-Layer 7파일 표준 + **예외 표** · Decimal-first · JWT/JWKS 검증 · Alembic · Celery prefork-safe · 검사기 판별 절차 |
| [`apps/web/AGENTS.md`](apps/web/AGENTS.md) | React Hooks 안전 H-1~H-3 · `error.tsx` 의무 · Next.js 16 · Zod v4 · shadcn v4 · 반응형 · TS 컨벤션 |

★**분리 기준**(2026-08-23 확립) — **「구조·경계·금지」는 이 자동 로드 층, 「예제·절차」는 `docs/` 정본 층.**
구조를 모르면 새 코드를 못 쓰지만 예제는 필요할 때 열면 된다.

## 9. 경로 → 용도

| 경로 | 무엇 |
| --- | --- |
| `apps/api/src/<도메인>/` | router · service · repository · schemas · models · dependencies · exceptions (7파일 표준) |
| `apps/api/src/strategy/pine_v2/` | Pine 인터프리터 **SSOT** |
| `apps/web/src/` | Next.js FSD Lite. ★화면 컴포넌트의 기본 자리는 `features/<domain>/components/` — `app/**/_components/` 가 **아니다**([ADR-035](./docs/adr/035-fe-component-ownership.md)) |
| `tools/scripts/` | 운영 런타임(`soak-*`·`db-backup`·`disk-guard`) · 가드 · `ledger-vitals` · `hooks/` · 스모크·재현 유틸 |
| `phases/<회차>/` | 하네스 러너의 회차 정의. ★산출물은 `runs/`(gitignore)에만. ★**끝난 회차는 지운다** |
| `docs/` | `status`·`PRD`·`backlog*` + 정본 6축 + `adr/` + `lessons.md` (지도 = [`docs/README.md`](./docs/README.md)) |
| `.claude/workflows/` | `review-code.js` · 하네스 Eval = `evals/harness/` |
