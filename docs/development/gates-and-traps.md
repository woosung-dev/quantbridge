# 게이트와 함정 — 모든 세션이 여는 문서

> 무엇을 돌려야 "통과" 인지와, 통과한 줄 알았는데 아닌 경우들.
> 2026-07-26 신설. 이 내용은 그전까지 스프린트 문서 7개에 복붙되고 있었고,
> 당시 `reference/` 에 있던 유일한 진술은 **틀려 있었다** ([`traps-gates-measurement.md`](./traps-gates-measurement.md) 의 `pnpm test` 항목).

> ★**[ADR-037](../adr/037-harness-zero-base.md) 제로베이스 (2026-08-19).** 이 문서에서
> `final-gates`·`bl-audit`·`docs-audit`·`bl-trigger-sweep`·`header-audit`·`skip-ratchet`·
> `signal-check`·`context-budget`·`tool-pin-audit`·`gate-harnesses`·`*-test.sh` 를 언급하는 절차는
> **전부 역사 기록이다** — 그 검사기들은 철거됐다(원문 = `git show harness-v1:<경로>`).
> 지금 유효한 것: §1 의 표준 러너(ruff/mypy/pytest/tsc/vitest/lint/build)와 CI 단일 게이트,
> §3 → [`traps-environment-shell.md`](./traps-environment-shell.md) §환경(`.env.local` 소싱·DATABASE_URL 단독 주입 금지 등 — 여전히 전부 참),
> §4 pre-push 는 ref 가드만 남음, 원장 사활 = `tools/scripts/ledger-vitals.sh` 3축.
> 리뷰 = `/review-code` · codex 훅 = `.codex/hooks.json` · 하네스 Eval = `evals/harness/`.
> 재입힘 규칙: 문서화된 사고 1건 = 슬림 복귀 1건 (ADR-037 §④).

---

## 1. 통과 가능한 게이트

```bash
QB=/Users/woosung/project/agy-project/quant-bridge

# 인프라 (격리 포트)
cd $QB && mise run up-isolated && mise run migrate-isolated

# BE — ruff / mypy / pytest
cd $QB/apps/api && uv run ruff check .
cd $QB/apps/api && uv run mypy src/
cd $QB/apps/api && set -a; source .env.local; set +a; uv run pytest -q

# OpenAPI 계약 drift (2026-08-16 배선 — ADR-031)
cd $QB && mise run openapi-check          # 커밋된 contracts/openapi/openapi.json 이 코드와 같은가

# FE — typecheck / vitest / eslint
cd $QB/apps/web && pnpm typecheck
cd $QB/apps/web && pnpm test
cd $QB/apps/web && pnpm lint
cd $QB/apps/web && pnpm build          # apps/web/.env.local 의 BETTER_AUTH_* 필요 (ADR-034)

# 디자인 캐논 런타임 (dev 서버 자동 기동, 인증 불요)
cd $QB/apps/web && pnpm e2e:design-canon

# e2e authed (apps/web/.env.local 에 E2E_AUTH_EMAIL·E2E_AUTH_PASSWORD 필요, 로컬 전용 — CI 에 없다)
cd $QB/apps/web && pnpm e2e:authed
```

`mise run lint` / `mise run typecheck` / `mise run test` 는 위를 FE+BE 로 묶은 것이다. 단 **env 를 source 하지 않으므로** BE pytest 는 셸에 3-env 가 이미 있어야 한다.

~~문서 구조·활성 Markdown 링크·폐기 경로는 루트에서 `mise run docs-audit`으로 검사한다.~~
→ **2026-08-19 [ADR-037] 철거** — `docs-audit` 은 없다(원문 = `git show harness-v1:tools/scripts/docs-audit.sh`).

### ~~게이트 3종 신규 · 게이트 2단(`--pre-pr`/`--deferred-only`) · 신호 4종(`.claude/gates/`)~~

→ **2026-08-19 [ADR-037] 철거.** 세 절(150줄)이 기술하던 기계가 전부 사라졌다 —
`tools/scripts/final-gates.sh` · `signal-check.sh` · `skip-ratchet.sh` · `docs-audit.sh` ·
`mise run gate-harnesses`(자기시험 14종) · 증거 마커 디렉터리 `.claude/gates/<run>/`.
**원문 = `git show harness-v1:docs/reference/operations/gates-and-traps.md`** (이 파일 53~202줄).

지금의 판정은 **표준 러너 + CI 단일 게이트** 하나다(위 §1 명령 + `.github/workflows/ci.yml`).
로컬에서 미리 보려면 그 러너를 직접 돌려라 — 유예 원장도, 신호 파일도, 브랜치 전제도 없다.
복귀는 [ADR-037] 재입힘 규칙(문서화된 사고 1건 = 슬림 복귀 1건, 최소판) 경유다.

### ~~소크 (P0 [BL-003] 의 달력 시간 게이트)~~ · ~~소크 무인 감시 + 원터치 재기동~~

> **tombstone (2026-09-10 [ADR-043]).** 두 절 200줄(pin/up/commit · 게이트 CLI · `QB_SOAK_OVERRIDE` · 무인 감시 · 재기동 8단계 ·
> `soak-stack.sh migrate`)은 스크립트 6종과 함께 삭제됐다. 원문 = `git show c488b545:docs/development/gates-and-traps.md`.
> 지금 서버의 「통과」는 `deploy.sh` 의 rc 하나다 — 0 = 배포됨 · 2 = 멈춤(24h 실격 또는 DDL 필요) · 1 = 실패.

## 2. 통과 가능한 게이트가 **아닌** 것

- **`ruff format`** — 이 레포는 포매터를 게이트로 쓰지 않는다.
- **`prettier` / `format:check`** — main 에 선재 red 356 건. 고치라는 신호가 아니다.
- **Pyright / IDE 인라인 진단** — IDE 가 uv 가상환경을 못 잡아 `pandas`·`pydantic`·`celery` 를 "unresolved" 로 표시한다. 권위는 `mypy src/` 다.

## 3. 함정

> **2026-08-21 — 94.6KB 였던 이 절을 주제별 4파일로 나눴다**([ADR-038](../adr/038-docs-top-level-by-question.md) 후속).
> 본문은 전부 옮겼고 여기는 색인만 남는다. 원문 위치 = `git show 9e91809c:docs/development/gates-and-traps.md` L271-1065.
> 새 함정은 **주제가 맞는 파일에** 적는다 — 이 절에 본문을 다시 쌓지 마라.

| 파일                                                         | 다루는 것                                                                                                         | 절                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`traps-environment-shell.md`](./traps-environment-shell.md) | 로컬 환경·셸·캐시·린트가 게이트를 거짓 red/green 으로 만드는 조건                                                 | 환경 · 셸·게이트가 거짓 red 를 내는 경로 (2026-07-28) · 린트가 잡는 문자 · 언어·타입 · 게이트가 **거짓 red** 를 내는 경로 (2026-07-27 live-conditional-hardening) · 캐시·주기 (2026-07-27 live-conditional-hardening)                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| [`traps-ci-e2e.md`](./traps-ci-e2e.md)                       | CI 와 로컬의 차이, 샤딩, e2e 통합·재현, authed 증거, FE 스키마 대조                                               | ★★CI 와 로컬은 같은 명령이어도 **같은 env 가 아니다** (2026-08-01, 실측 5건) · CI pytest 샤딩 (2026-08-06 ci-diet) · e2e spec 을 통합할 때 (2026-08-06 e2e-consolidation) · e2e 가 게이트에서만 red 일 때 — 증거를 남기고 조건을 재현하는 법 ([BL-784], 2026-08-17) · CI 초록은 **authed 통과의 증거가 아니다** ([BL-789], 2026-08-17) · 신규 BE 필드는 FE `.strict()` 스키마와 **항상** 대조해라 (2026-07-30, codex 적대 리뷰 MAJOR)                                                                                                                                                                                                                                                        |
| [`traps-gates-measurement.md`](./traps-gates-measurement.md) | 조용히 통과하는 명령, 측정 도구가 먼저 틀리는 경우, 게이트가 「돌렸다」만 보증하는 경우, 변이·추론·git 으로 셀 때 | 조용히 통과한 것처럼 보이는 것 · 검증이 무언가를 증명하지 못하는 세 가지 방식 (2026-07-28 live-outcome-parity, 한 스프린트에서 3회) · 수정이 새 표면을 만든다 (2026-07-28) · 통계 게이트 (2026-07-28) · 측정 도구가 먼저 틀린다 (2026-07-30 — 한 회차에 **6번**) · 측정 도구가 먼저 틀린다 (2026-07-30 close-mismatch-soak — 또 **2번**) · 게이트가 "돌렸다" 만 보증한다 (2026-07-30) · ★★스위트 결과가 **수집 집합**에 달려 있었다 (2026-08-03 gate-trustworthiness, BL-583) · 죽은 의존성을 걷어낼 때 (2026-08-06 dead-code-sweep) · 측정 도구가 먼저 틀린다 (2026-07-28) · git 으로 세거나 「안전하다」고 말할 때 (2026-08-12 branch-debris) · 변이 검증 (2026-07-27) · 추론 (2026-07-27) |
| [`traps-live-trading.md`](./traps-live-trading.md)           | 라이브 신호 도메인, 거래소 실상, 원장을 읽을 때, 함대·계측, 계기                                                  | 라이브 신호 도메인 · 거래소 실상 (2026-07-28 live-entry-parity, 실거래소 실측) · 원장을 읽을 때 (2026-07-30 close-mismatch-visibility) · 함대·계측 함정 (2026-07-31 reversal-ledger-sync) · 계기(instrument) — 어떤 상품의 가격을 보고 있는가 (2026-07-28)                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## 3.5 컨텍스트 예산 — 세션이 새는 두 채널

> 2026-07-28 승격. 직전 회차가 이 규칙을 **참조는 했으나 이 파일에 없었다** — 핸드오프가 "여기 있다" 고 적었지만 실제로는 없었고, 이번에 실제로 넣는다.

- ★**서브에이전트는 파일이 아니라 상한으로 답한다.** 이 저장소의 읽기 전용 서브에이전트(`Explore`)는 **Write 도구가 없다.** "리포트를 파일에 써라" 는 지시는 실패하고 전문이 반환값으로 돌아온다(단일 최대 소모원). **반환값 줄 수 상한을 명시해라** — "30줄 이내 / 발견마다 3줄 / 코드 덤프 금지" 가 실제로 먹는다.
- ★**Monitor 는 변화 감지가 아니라 위험 신호 + 하트비트다.** 즉시 발화는 **작업을 죽이는 사건만**(세션 비활성화 · kill switch · DNS 실패). 진행 상황은 **10~15분 하트비트 1줄**. 판단 기준 = _"이 발화를 보고 내가 뭘 할 것인가?"_
- worker 로그 전문 금지 — `grep -c` / `sort | uniq -c` 집계만.
- 문서 파일은 `head`/`sed -n` 에 **`cut -c1-200`** 을 붙여라. 이 저장소 dev-log·backlog 는 행 하나가 3,000자다.
- ★**codex 산출물(`*-codex.txt`)은 tool-trace 가 수십만 줄이다.** 최종 답변만 뽑아라 — `awk '/^\[P[123]\]/{f=1} f'` 같은 패턴으로 자른다. 통째로 읽지 마라.

## 4. pre-push 훅

`.husky/pre-push` 는 **ref 가드 하나만** 한다 ([ADR-037] 2026-08-19 — 품질 검사부는 철거,
원문 = `git show harness-v1:.husky/pre-push`). CI 가 품질을 단독 판정한다.

- `main` / `master` push **영구 차단** (bypass 불가)
- `stage/*` `feat/*` `fix/*` `chore/*` `docs/*` `test/*` `refactor/*` `hotfix/*` 만 허용.
  그 외 임의 브랜치는 차단 + bypass 안내 (판정 순수 함수 = `tools/scripts/lib/pre-push-ref-guard.sh`)
- 판정 대상은 현재 브랜치가 아니라 **실제로 미는 ref** 다 ([BL-554]·[BL-555])
- ~~`apps/web/` 변경 시 `pnpm typecheck && pnpm test`~~ ~~`apps/api/` 변경 시 `ruff`·`mypy`~~
  ~~`.env.local` 의 `TEST_` 접두 자동 export~~ → **전부 철거됐다. push 는 품질을 안 본다.**

## 5. 격리 스택

| 항목     | 기본 | 격리 (`mise run up-isolated`) |
| -------- | ---- | ----------------------------- |
| FE       | 3000 | **3100**                      |
| BE       | 8000 | **8100**                      |
| Postgres | 5432 | **5433**                      |
| Redis    | 6379 | **6380**                      |

다른 웹앱과 병렬로 돌릴 때 격리가 디폴트다. 옛 스프린트 문서의 `5436` 표기는 stale — 2026-07-25 포트 정렬 이후 **5433** 이 정답이다.

---

**관리 규약** — 새 스프린트에서 게이트 함정을 발견하면 자기 체크리스트에 적지 말고 **여기에 추가**해라. 그게 이 파일이 존재하는 이유다.
