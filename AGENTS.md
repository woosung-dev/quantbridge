# QuantBridge — TradingView Pine Script 전략 → 백테스트·데모·라이브 트레이딩 퀀트 플랫폼

> **새 AI 세션 첫 step — 3종만 읽는다.** `CONTEXT.md`(도메인 헌법 — 용어/관계 SSOT) + 본 파일 + `docs/status.md`.
> ★**`CONTEXT.md` 는 자동 로드가 아니다 — 읽어야 들어온다.** `CLAUDE.md` 가 import 하는 것은 본 파일 **하나뿐**이다.
> ★**`docs/status.md` 의 「다음 스프린트」 블록이 다음에 무엇을 할지의 유일한 진입점이다.** 별도 킥오프
> 파일을 만들지 않는다 (`docs/reference/operations/workflows/generator-evaluator-pipeline.md` §G8).
> `docs/roadmap.md`(다음 후보)와 `docs/backlog.md`(open BL)는 **필요할 때 grep 으로 연다** — 통째로 읽지 않는다.
> 본 파일은 **오리엔테이션 전용**이다([ADR-026](docs/decisions/026-documentation-ssot.md)). 규칙 본문은
> `backend/AGENTS.md`·`frontend/AGENTS.md`, 결정 근거는 `docs/decisions/`, 반증 기록은 `docs/lessons.md` 가 정본이다.

---

## Golden Rules (Immutable)

- NEVER — 환경 변수·API 키·시크릿을 코드에 하드코딩 (`SecretStr` 사용)
- NEVER — Repository layer 밖에서 DB 접근 (`backend/AGENTS.md` §3)
- NEVER — `.env.example` 에 없는 환경 변수를 코드에서 참조
- NEVER — 사용자 승인 없는 `git push` / 배포 (main 직접 push 영구 차단)
- NEVER — LLM 생성 규칙 파일을 검토 없이 그대로 사용

## 개발 원칙

- ALWAYS — 사고/계획/대화/문서/주석 = **한국어**, 코드 네이밍/커밋 메시지 = **영어**
- ALWAYS — 코드 작성 전 「어떤 설계 문서 + 어떤 방향」 짧게 브리핑, 코드 수정 시 관련 문서 **동일 세션** 갱신
- ALWAYS — 확인된 사실 / 추론(`[가정]`) / 확인 필요(`[확인 필요]`) 구분 표기
- ALWAYS — 커밋/푸쉬/배포는 단계별 사용자 승인 (묶음 요청만 한 번에)
- ALWAYS — 게이트(`scripts/final-gates.sh`)는 **마지막 커밋 뒤에** 돌리고 그 뒤로 문서를 더 쓰지 마라 —
  pre-commit 의 `prettier --write`·`ruff format` 이 **커밋 시점에** 트리를 바꾸므로 커밋 전 결과는 낡는다
- ALWAYS — `gh pr create` 전, `docs/status.md` 에 **살아 있는 「다음 행동 = …」이 둘 이상이면 안 된다**.
  끝난 것은 `~~옛 문장~~ → **날짜 + 새 사실**` 로 바꾼다 — 다음 세션은 남아 있는 것을 그대로 따른다.
  ★**2026-08-08 부터 `docs-audit.sh` 가 잡는다**([BL-643] — 종전의 「어느 게이트도 안 잡는다」는
  이제 거짓이다). 재는 것은 **구문** `다음 행동 =` 이고 **파일 전체**로 센다(사고 2건이 서로 다른
  섹션에 하나씩 있었다). ⓪ 표 행 **≥3** 도 같이 본다. 종결 절차 전문 = §G8
- 역할 = **Senior Tech Lead + System Architect**. 완전한 코드(`...` 생략 금지), 복잡한 설계는 Mermaid.js

## 문서 — 어느 질문은 어디가 답하나 (SSOT 7축, ADR-026)

- **지금 상태** — `docs/status.md`(활성 sprint) · `docs/roadmap.md`(다음 후보) · `docs/backlog.md`(BL 원장)
- **정본** — `docs/reference/`. 코드와 어긋나면 **코드가 맞다** — 단 「지금 무엇을 하는가」에 한해서다.
  「왜 그렇게 했나」(`docs/decisions/`)와 「무엇이 반증됐나」(`docs/lessons.md`)에 대해 **코드는 증인이 아니다**
- **결정 근거** — `docs/decisions/`. 규칙 변경 전 필독. 폐기는 삭제가 아니라 `Superseded` 표기
- **과거 원문** — git history. 삭제 시 tombstone(무엇을+어디로+SHA) 1줄 의무. 발견 색인 = `docs/dev-log/INDEX.md`
- **뭘 돌려야 통과인가** — `docs/reference/operations/gates-and-traps.md` · 전체 목차 = `docs/README.md`

- NEVER — BL 상태를 손으로 세지 마라. `scripts/bl-audit.sh` 가 정본이며 3면(섹션 `**상태:**` 줄 · 인덱스 표 ·
  roadmap 체크박스)을 대조한다. BL 추가/해결 시 `**상태:**` 줄 의무 (없으면 `UNKNOWN`)
- ★**판정어 5종** — `ACTIVE`(지금 단독 착수 가능) / `DEFERRED`(**트리거 미도래** — 상태줄 `⏳ **대기 (트리거
미도래)**`) / `PARTIAL` / `RESOLVED` / `UNKNOWN`. DEFERRED 는 active 로 안 세고 3면에서는 ACTIVE 와 같은
  「미완」 쪽이다([ADR-028](docs/decisions/028-backlog-deferred-verdict.md)). 도래 판정 = `scripts/bl-trigger-sweep.sh`
  (**`--selftest` 를 전량 스윕보다 먼저**). ⓪ 표는 `--list ACTIVE` 에서 파생 — 손으로 후보를 얹지 마라
- ALWAYS — 요약 줄 길이 상한 준수: `dev-log/INDEX.md` **300자** · `backlog.md`·`roadmap.md` **1,000자**
  (`scripts/docs-audit.sh` 강제). 읽는 비용은 `scripts/context-budget.sh` 로 잰다 (바이트 아닌 **문자**)
- ALWAYS — 스프린트 종료 시 작업 문서는 승격(`reference/`)·강등·삭제 중 하나로 종결. 회고는 **반증 카드
  1~2천자 → `docs/lessons.md` 승격 → INDEX 한 줄** (ADR-026 §3)
- ID 체계: `SCR-` 화면 / `API-` API / `ENT-` 엔티티 / `REQ-` 기능 / `BL-` 백로그. ID 재사용 금지

## 현재 컨텍스트

핵심 도메인 6종 — Strategy(`pine_v2` 인터프리터) / Backtest / Stress Test / Optimizer /
Trading(CCXT 주문 — 계정 모드는 **Bybit demo 만**) / Market Data(TimescaleDB).
★**용어·관계·도메인 경계의 SSOT 는 [`CONTEXT.md`](CONTEXT.md)** — 도메인을 다루기 전에 읽어라.

## Operational Commands

- 기본: `make up` / `make be` / `make fe` → 3000/8000/5432/6379 · 격리: `make up-isolated` 계열 →
  3100/8100/5433/6380. 자세한 타깃은 `make help`
- 워크트리 병렬 = **슬롯**(FE `3100+N` / BE `8100+N` / pytest DB `quantbridge_w{N}_test`).
  `scripts/herdr-fleet.sh`(★메인 체크아웃 전용) · 워크트리 단독은 `./scripts/worktree-bootstrap.sh --adopt-env`
- NEVER — 워크트리에서 `make up`/`down`/`migrate`/`seed` — 컨테이너·앱 DB 는 1벌 공유라 함께 깨진다
- NEVER — 워크트리에서 celery 경유 검증(백테스트·라이브신호·옵티마이저) — worker 는 메인의 `src` 를
  mount 하므로 **내 코드가 아니라 메인 코드가 돈다**(침묵 실패).
  정본: [`docs/reference/operations/worktree-parallel.md`](docs/reference/operations/worktree-parallel.md)
- ALWAYS — BE pytest 전 `.env.local` **통째** 소싱: `cd backend && set -a; . ./.env.local; set +a; uv run pytest`
- NEVER — `DATABASE_URL` 만 단독 주입(서브에이전트 포함) — 세션 픽스처 `drop_all` 이 **개발 DB 를 겨냥**한다.
  상세·함정 전체: `gates-and-traps.md` §환경

## 스택 규칙 (그 디렉터리 파일을 열면 자동 로드)

★`backend/` · `frontend/` 에 각각 `AGENTS.md`(규칙 본문) + `CLAUDE.md`(`@AGENTS.md` 한 줄)를 둔다.
Claude Code 는 **그 디렉터리의 파일을 읽는 순간** 하위 `CLAUDE.md` 를 로드하고 import 를 따라
`AGENTS.md` 까지 편다(2026-08-07 실측). codex 등 다른 에이전트는 `AGENTS.md` 를 직접 읽는다
([ADR-027](docs/decisions/027-nested-agents-md.md)). 파일을 안 열고 설계만 논하는 세션에서는 직접 열어라.
★**하위 `AGENTS.md` 는 루트를 덮어쓰지 말고 보강만 해라** — Claude 는 루트와 하위를 **이어붙이고**
codex 는 **가까운 것만** 본다. 충돌하는 문장을 쓰면 두 도구가 다르게 행동한다.

- [`backend/AGENTS.md`](backend/AGENTS.md) — FastAPI 3-Layer · Decimal-first · 도메인 규칙 표 · Celery prefork-safe (§2/§4/§9)
- [`frontend/AGENTS.md`](frontend/AGENTS.md) — React Hooks 안전 H-1~H-3 · `error.tsx` 의무(§3/§6) ·
  Next.js 16 · Zod v4 · shadcn v4 · 반응형 · TS 컨벤션(**§7~§11**, 구 `nextjs-shared.md`)

## 메타-방법론 (영구) — 아무 신호 없이 건너뛰어지는 둘만 여기 둔다

- ALWAYS — Sprint kickoff(Type A/B) 첫 step = **baseline 재측정 preflight**. 본인 인상·plan 가정·
  사용자 prompt 가정 모두 실측 전 신뢰 금지
- ALWAYS — codex finding 은 **코드 대조 후에만** 채택 (phantom finding 차단)
- 나머지(§8.2/§8.4/§8.5)와 전문 =
  [`generator-evaluator-pipeline.md`](docs/reference/operations/workflows/generator-evaluator-pipeline.md) §8

## 경로 → 용도 (Quick Reference)

- `backend/src/<도메인>/` — router/service/repository/schemas/models · `backend/src/strategy/pine_v2/` — 인터프리터 SSOT
- `frontend/src/` — Next.js 16 FSD Lite (`app`/`components`/`features`/`hooks`/`lib`/`store`)
- `scripts/` — 게이트·감사·함대 셸 (`bl-audit` · `docs-audit` · `context-budget` · `soak-gate` · `herdr-fleet`)
- `docs/` — 상태 3종 + `reference/` + `decisions/` + `lessons.md` (지도: `docs/README.md`)
- `backend/AGENTS.md` · `frontend/AGENTS.md` — 스택 규칙 (같은 자리 `CLAUDE.md` = `@AGENTS.md` 한 줄)
