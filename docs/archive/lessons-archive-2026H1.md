# Lessons Archive — 2026H1

> `docs/lessons.md`의 stale LESSON 본문 보관소입니다.
> 원본 = `docs/lessons.md`, 이동 시점 커밋 `fc1854d5`.
> 현재 후보·승격 상태는 [원본 lessons](../lessons.md)에서 확인합니다.
> 이 파일은 이동 당시 본문을 원문 그대로 보존합니다.

## LESSON-001 — Pine Script → Python 변환 시 `exec()` 인젝션 위험

- **상황 / 원인:** Pine → Python 동적 코드 실행 시 사용자 입력 그대로 → 코드 인젝션.
- **해결:** 인터프리터 패턴 (`pine_v2` AST 평가) 또는 RestrictedPython sandbox. `eval/exec` 절대 금지.
- **반복 / 승격:** 1 / ADR-003 + AGENTS.md QuantBridge 고유 규칙 반영 완료.

## LESSON-002 — Celery zombie task recovery (OOM/crash 후 status=running 영구 잔류)

- **해결:** 3-layer — `on_failure` 핸들러 / Celery Beat periodic cleanup (30분+ running → failed) / 수동 cancel 엔드포인트.
- **출처:** ADR-003 §3.

## LESSON-003 — Pine 파싱 "80%+" 가정 과대평가

- **해결:** TV 상위 50 전략 분류 테스트 선행 → "검증된 40% 패턴 지원 + 나머지 투명한 Unsupported" 정책. ADR-003 §2/§4.

## LESSON-007 — worktree 안 `git rev-parse --show-toplevel` 은 main repo 아닌 worktree 경로 반환

- **해결:** main repo 경로 필요 시 `--git-common-dir` 또는 명시 인자 전달. `kickoff-worker.sh` patch 후 본 항목 삭제 예정.

## LESSON-008 — Signal/IPC 식별자는 full id (prefix 포함) 고정

- **상황:** Bundle 2 자율 병렬에서 Planner 가 `{x}` 축약형, Monitor 가 full id (`fe-d.status`) 기대 → silent 멈춤.
- **해결:** Planner 프롬프트에 `SIG_ID = full sprint id (e.g., fe-d)` 명시 + Phase 1 kickoff 직후 Monitor 가 실제 signal 파일명 1회 검증.

## LESSON-009 — Worker 는 worktree 외부 (main repo) 에 파일 생성 금지

- **해결:** Worker prompt "생성하는 모든 파일은 worktree 내부 경로 제한" + squash merge 직전 main untracked 파일 `git status` 검증.

## LESSON-010 — stage worktree 생성 시 3 symlink 필수

- **3 symlink:** `backend/.venv` + root `node_modules` + `frontend/node_modules`. worktree 생성 직후 일괄.

## LESSON-011 — Redis 분산 락 wrapping `async with RedisLock(): pass` 는 mutex 아님

- **해결:** `pass` block 의 lock hold 시간 ≈ 1 RTT. Wrap 은 contention-detect signal + metrics 만. Correctness 는 이어지는 PG advisory + UNIQUE 가 보장.

## LESSON-012 — slowapi 0.1.9 `swallow_errors=True + headers_enabled=True` 동시 사용 시 `request.state.view_rate_limit` 미초기화 AttributeError

- **해결:** `_RateLimitStateInitMiddleware` 로 `request.state.view_rate_limit = None` 선초기화. slowapi upgrade 후 검증·제거 follow-up.

## LESSON-013 — worktree 심링크는 `../../..` prefix (3 단계)

- **원인:** symlink relative path 는 symlink 파일이 위치한 디렉토리 기준. `.worktrees/NAME/backend/.venv` 에서 원본까지 3 단계 필요.
- **해결:** 3 symlink 모두 `../../../*` (루트 `node_modules` 는 `../..` 2 단계). worktree 생성 후 `ls -L <symlink>` 로 resolve 확인.

## LESSON-014 — `conftest.py` 에 모든 필수 env 기본값 주입

- **상황:** `@limiter.limit` endpoint 추가 시 `REDIS_LOCK_URL` 누락 → ConnectionError.
- **해결:** rate-limit endpoint 추가 시 conftest env 기본값 검토 체크리스트. pre-push hook 으로 재현.

## LESSON-015 — Redis 논리 DB 0~2 점유 중 — 분산 락 / rate-limit 은 DB 3+

- **원인:** DB 0=cache / DB 1=Celery broker / DB 2=Celery result backend. lock 은 DB 3+ 격리 (broker burst/eviction 으로 lock 유실 방지).

## LESSON-016 — Next.js 16 은 `proxy.ts` (not `middleware.ts`)

- **해결:** edge middleware 파일명 변경. 새 FE plan 작성 시 `proxy.ts` 로 명시. `grep -r "clerkMiddleware" frontend/src/` 로 실제 파일 확인.

## LESSON-017 — codex Generator-Evaluator 루프는 plan 자체부터 시작 (G0 게이트)

- **해결:** master plan 작성 직후 codex consult 1 회. 발견 critical 을 plan 안 surgery 반영 후 ExitPlanMode.
- **검증:** Sprint 12 G0 7 critical 사전 차단 (savepoint rollback / Bybit auth window 등). 이전 모든 plan 에 누락. Sprint 12 부터 영구 적용.

## LESSON-018 — Heavy codex G-E 루프 시 Sprint scope 실측 +30~50%

- **해결:** Sprint 시작 시 **scope tier** (dogfood / production / multi-tenant) 명시 + codex prompt 포함. G4 BLOCK 시 max 2 iter 한도, 그 후 사용자 결정.

## LESSON-026 — `import a.b.c as d` 가 `__init__.py` re-export 와 충돌 시 변수로 평가됨

- **해결:** `sys.modules["src.tasks.celery_app"]` 우회. test 안 module reference 시 적용.

## LESSON-027 — Sprint 18 `_WORKER_LOOP` task 의 inner 함수는 `_async_xxx` 직접 await 가 pytest-asyncio 호환

- **해결:** `run_in_worker_loop` 우회 (이미 loop 안에서 실행 시 RuntimeError). Inner async 함수 직접 await + `create_worker_engine_and_sm` monkeypatch.

## LESSON-028 — PostgreSQL JSONB strict — NaN/Infinity 명시 sanitize 의무

- **해결:** Recursive `_sanitize_for_jsonb(value)` helper. `math.isnan/isinf` → `None`. dict/list/tuple recurse. JSONB INSERT 전 의무.

## LESSON-029 — SQLAlchemy enum auto cast vs Alembic String 컬럼 mismatch

- **해결:** 모델 field 에 명시적 `Column(String(N))` 선언. Alembic migration 도 String(N) (PG enum DDL 회피). 사용처 `.value` 호출 + `str(...)`.

## LESSON-030 — Bybit v5 `set_leverage / set_margin_mode` 는 idempotent — "not modified" silently ignore

- **해결:** ccxt `BadRequest` catch + `"not modified"` 포함 시 silently ignore. Bybit Provider 한정.

## LESSON-031 — Bybit Linear contract symbol normalize (ccxt unified)

- **해결:** `_to_bybit_linear_symbol(symbol)` helper — `BTC/USDT` → `BTC/USDT:USDT`. UI/Strategy spot format 유지.

## LESSON-032 — base-ui `Select.Value` 가 raw value 표시 — render prop 으로 name mapping

- **해결:** `<SelectValue>{(value) => lookup(value)?.name ?? "..."}</SelectValue>`. ID-based combobox 의무.

## LESSON-033 — Era 3 Sprint type 분류 (kickoff 의무, Sprint 28 도입)

- **type:** A 신규기능 (의무) / B BL fix risk-critical (권장) / C dogfood hotfix (압축) / D docs only (면제).
- **검증:** Sprint 28 5 Slice 차등 적용 + Sprint 30+ 부터 영구 적용 권고.

## LESSON-034 — office-hours 재진행 (3개월+ 경과 시 의무, Sprint 28 도입)

- **해결:** sprint kickoff frontmatter `office-hours 진행 여부` 필드 + 3개월+ 경과 + dogfood evidence 누적 시 Q4/Q5 + Q1-indie 변형 재진행. 결과는 ADR Addendum 으로 보존.

## LESSON-035 — dual metric (sprint 종료 의무, Sprint 28 도입)

- **3 metric:** Self-assess ≥7/10 (근거 ≥3줄) + 신규 BL count (P0=0, P1≤2) + 기존 P0 잔여 ≥1 감소. 셋 다 PASS 시만 sprint 완료 판정.

## LESSON-036 — Slice cascade PR pattern (Option C staging)

- **해결:** sprint kickoff 시 `stage/h2-sprint{N}-{theme}` 생성. 각 Slice sub-branch 가 stage base PR. cleanup PR 도 stage cascade. 사용자 manual stage→main merge (sprint 종료 + dual metric PASS 후).

## LESSON-041 — Pine partial declaration → 422 reject (Sprint 38 BL-188 v3 A1)

- **상황:** `default_qty_type` 만 명시 + `default_qty_value` 생략 = ambiguous semantics.
- **해결:** `PinePartialDeclaration(BacktestError)` 422 status + AST corpus audit 정기 검증. Pine `strategy()` paired 인자 strict invariant.

## LESSON-042 — Sizing source 단일 입력 강제 (Sprint 38 BL-188 v3 A1)

- **해결:** `position_size_pct` (Live mirror) 와 `default_qty_*` (manual) 동시 명시 시 `SizingSourceConflict` 422. BE Pydantic `@model_validator` + FE Zod `.refine()` parity.

## LESSON-043 — Live mirror leverage parity (Nx reject, BL-186 후 unlock)

- **해결:** engine 1x equity-basis only / live `leverage != 1` 시 `MirrorNotAllowed` 422. FE 4-state badge `live_blocked_leverage` 명시. Manual sizing override path 제공.

## LESSON-044 — 메인 세션 = 표준 prefix / worktree 워커 = `worker-*` prefix

- **해결:** stage push 시 `QB_PRE_PUSH_BYPASS=1` env override + branch swap (메인 worktree 가 stage). `--no-verify` 금지. pre-push hook 화이트리스트 = `feat/fix/chore/docs/test/refactor/hotfix`.

## LESSON-045 — env override 의무 (다른 프로젝트 host port 충돌)

- **해결:** isolated mode (5433/6380) 가 default. baseline preflight 시 `TEST_DATABASE_URL / REDIS_URL / REDIS_LOCK_URL / CELERY_BROKER_URL` inline env override 의무. `.env.local` 변경 회피 (다른 도구 영향).

## LESSON-046 — 통합 dogfood = Generator-Evaluator 못 잡는 회귀 detection layer

- **해결:** Day 7.5 mid-dogfood 시 (a) FE idle CPU 측정 + (b) main 베이스 delta + (c) navigate 시 CPU 변화 = falsification signal 3 종. 통합 회귀 발견 시 즉시 gate FAIL + 다음 sprint = polish iter.

## LESSON-047 — Turbopack `turbopack.root` 명시 시 wrong path = file watcher storm (400% sustained)

- **해결:** monorepo lockfile 위치 확인 의무. multi-lockfile warning 은 false alarm — 자동 inferred root 사용. fix 적용 시 fresh restart + idle CPU 6 samples × 5s 측정 의무. (자동 inferred = pnpm-lock.yaml 있는 root)

## LESSON-048 (2/3) — Playwright MCP + 인증 cookie 자동 dogfood

- **해결:** dogfood 시 Playwright MCP `browser_navigate` 자체 1 회 시도. 메인 세션 stack 의 Chromium = 사용자 chrome cookie 공유 가능 (인증 페이지 자동 검증). manual 시간 1/3+ 단축. clipboard / 모바일 viewport 등 자동화 어려운 항목 사용자에게 명시 위임.

## LESSON-049 — codex G.4 P1/P2 즉시 fix 패턴 (cmux 자율 병렬)

- **해결:** P2 발견 시 (a) cmux send + sig running reset 우선 / (b) session stuck 시 메인 세션 worktree 직접 push (LESSON-035 isolation 양립). defer 옵션은 demo/Beta 영향 없을 때만.

## LESSON-050 — Sprint kickoff design source 명시 의무

- **해결:** 디자인 트랙 sprint kickoff prereq 첫 step = `docs/design/prototypes/` + `DESIGN.md` + `*.pen` + Figma URL 모두 grep + 5지선다 prereq 옵션 (없음 + 4 source 종류). design source 누락 발견 시 즉시 Wave 2 추가 spawn.

## LESSON-051 — Agent isolation worktree 4 spawn 시 baseline 정리 의무

- **해결:** Sprint kickoff prereq 에 baseline 정리 명시 — dev server 중단 / docker idle stop / `pnpm install` 1 회 사전 / worktree prune.

## LESSON-052 — Worker prompt 첫 step `pwd` + cwd 검증 의무

- **해결:** Worker prompt 첫 step = `pwd` 출력 + cwd 가 worktree 인지 확인 → 메인 cwd 면 즉시 STOP. 절대경로 작성 금지 (cwd-relative). node_modules `pnpm install` 금지 (symlink 활용). 보고 양식에 isolation 위반 / CPU 자가 관찰 / node_modules 처리 3 항목 추가.

## LESSON-053 — Agent tool isolation 한계 — N=4+ 시 cmux 우선

- **해결:** N=4+ 동시 spawn 은 cmux + 사용자 통제 baseline. Agent tool isolation 은 N=1-2 또는 즉시 진행 요청 시 fallback. Sprint kickoff prereq 에 spawn 방식 (cmux vs Agent) 명시.

## LESSON-054 — Mental model 일관성 > fintech 다크 권장 (single-page 다크 회피)

- **해결:** 단일 페이지만 다른 theme 적용 (예: /trading 만 다크) 은 mental model 손상. light/dark 혼용은 manual toggle 또는 시스템 `prefers-color-scheme` 통한 일관 적용. prototype 정합성보다 mental model 일관성 우선.

## LESSON-055 — Worker prompt 첫 step `cd <absolute worktree path>` 사전 명시 의무

- **4 조건 (Sprint 43 검증 — 12 worker × 3 wave, 위반 0):**
  1. 메인 세션이 사전 worktree + branch + node_modules symlink 일괄 생성
  2. Worker prompt 첫 step에 `cd <absolute worktree path>` (relative 금지)
  3. `pwd` 검증 후 메인 cwd 면 STOP
  4. `git checkout -b` step **제거** (worktree 가 이미 branch attached)

## LESSON-062 — ADR 결정이 SSOT (AGENTS.md 표현) 변경 시 동기화 의무

- **상황:** vectorbt → pine_v2 SSOT 변경 (ADR-011 §6/§8, Sprint 8a) 후 AGENTS.md `핵심 도메인` 표현 3 주 stale. 다음 세션 LLM 이 stale SSOT 신뢰 → 잘못된 인사이트.
- **해결:** ADR 결정이 백테스트 엔진 / 핵심 도메인 정의 / 기술 스택 표현 변경 시 같은 PR 또는 다음 sprint close-out 안에 AGENTS.md 동기화 의무.

## LESSON-064 (3/3 — 정식 승격 후보) — `/deepen-modules` audit silent failure 판단 = 직접 read + 전체 dispatch 경로 추적

- **상황:** BL-205 `OrderReceipt` 3-state 가 단일 grep 으로 silent failure 등재됐으나 codex G.0 2차 재검증 결과 = 의도된 _create flow_ simplification, _fetch flow_ 는 별도 `OrderStatusFetch` 4-state. 코드 변경 0, ADR 문서화로 Resolved.
- **해결:** (a) 단일 파일 grep 미확정 / (b) `_map_*` reverse 매핑 + consumer 전수 추적 / (c) BL 등재 전 codex G.0 cross-check. post-merge audit (Sprint 48 Worker E reverse-mapping audit) = positive validation safety net.
- **3차 검증 (2026-06-30 stress_test-deepen):** BL-363 boilerplate 의 money-path 위험을 단일 grep 이 아니라 **직접 read(`service.py:298-411`) + git co-change 추적(`6c7adfba` WF 누락 → `ffb2299b` 별도 패치)** 으로 확정 — config-drift 가 실제 silent corruption 으로 한 번 물었음을 증명. `StressTestKind` dispatch 도 5 site/3 파일 전수 추적으로 over-eng(C3 거부) 판단. 단일 grep 이었으면 "boilerplate 추출" 표면 가치만 봤을 것 → 직접 read 가 money-path framing + git 실증을 끌어냄. **3/3 누적 → `generator-evaluator-pipeline.md` §8.5 의 deepen-modules 절차에 "단일 grep 금지, 직접 read + dispatch/co-change 전수 추적 의무" 영구 승격 후보(사용자 검토).**
- **[LESSON-063 §7.5 4차 재현 corroboration]** multi-SSOT/평행정의 패턴: pine_v2 STDLIB(1) → backtest BacktestMetrics 24-field 4-site(2) → trading exit-field(3) → **stress_test cell 8-site + add-a-type 7파일 lockstep(4, git verbatim 2회)**. AI 누적 코드는 신규 도메인 타입 추가 시 N 타입 × M 레이어 평행 확장을 디폴트로 누적 → §7.5 `/deepen-modules` 신규 도메인 직후 의무 재확인.

## LESSON-065 — subagent review 2-stage 가 monkeypatch indirect dependency 못 잡음

- **상황:** Sprint 48 PR #246 BL-203 service.py 5-service 분할 → 5 test FAIL (`logger`/`datetime`/`settings` AttributeError). spec/code reviewer 2-stage PASS 통과 후 GitHub Actions 에서 detection.
- **원인:** Python namespace 분리 — shim re-export 는 module-level attribute (logger/datetime/settings/typing import) 까지 보존 안 함. `monkeypatch.setattr(service_mod, ...)` 가 shim attribute 만 변경 → services/\* 안 자체 attribute 영향 0.
- **해결:** module rename/split 동반 PR review 의무 — (1) `monkeypatch.setattr(<module>, ...)` 패턴 + module split 영역 발견 시 attribute resolution 직접 검증 / (2) shim 의 namespace 한계 인지 / (3) Preflight grep audit 시 alias (`as service_mod`) 패턴 검색 의무.

## LESSON-067 — codex evaluator 는 분산형(G.0 + slice spot + G.4)이 정본 패턴, 비용은 스코프의 함수 (6/6)

- **상황:** Sprint 39/51~57/59/60 에 걸쳐 codex evaluator 호출 패턴을 6회 실측 — 단일 G.0
  일괄(518k) vs 분산형(G.0 + slice spot + G.4). 분산형 비용은 스코프에 따라 216k~1.8M tokens
  로 가변(revision 양 + 트랙 수의 함수)이며, spot 축소(Sprint 52 형)로 1/5 까지 줄었다.
  「단일 worker single-day scope 자율 진행 가능」 판정도 같은 실측 계열에서 6/6 누적.
- **해결:** evaluator 는 분산형을 기본으로 하되 slice spot 은 스코프가 좁으면 생략한다.
  budget 은 고정값이 아니라 스코프 함수로 계획한다.
- **6차 검증 (dev-log 삭제 전 등재 보충 — 원문은 git history `docs/dev-log/2026-05-1*-sprint5*-close.md`).**

## LESSON-068 — Korean docs lint mechanism 부재 → §5/§6 위반 누적 자연 발생 (1/3)

- **상황:** 2026-05-15 CLAUDE.md align audit Track C 검증 결과 — `~/.claude/CLAUDE.md` §5 (한국어 콜론 종결 금지) **181 line 위반** (docs/dev-log 161 + dogfood 12 + guides 8) + §6 (신규 source file 1줄 한국어 주석 의무) **70 file 누락** (BE 14/157 = 8.9% + FE 56/243 = 23%). main.py / core/config.py / trading/registry.py / app/layout.tsx 등 핵심 file 도 누락.
- **원인:** lint mechanism 0 — markdownlint custom rule (한국어 sentence + `:` end-of-line) 부재 + ESLint custom rule (한국어 주석 첫 3줄 의무) 부재 + ruff custom rule 부재. LLM 매 generation 자연 위반 + reviewer 0 → 누적.
- **해결 path:** (a) ruff custom plugin 또는 markdownlint custom rule 으로 §5 자동 검출 + auto-fix script (`:` → `.` 한국어 sentence ender 한정) (b) ESLint custom rule + ruff custom rule 으로 §6 누락 file 검출 + pre-commit hook (c) 누락 70 file 일괄 한국어 헤더 추가 sprint = BL-307. 1차 누적 (Sprint 60 Track C) — 3차 시 영구 규칙(문서 lint 축) 승격 path — 구 global.md §5/§6 은 ADR-026 으로 소멸, 승격처는 `docs-audit.sh` 확장.



<!-- 2026-08-17 sprint-parallel-lanes 강등 — lessons.md 400줄 상한 -->

### LESSON-088 — 「뿌리 미확정」이 적힌 항목의 **처방 후보를 상속하지 마라**. 뿌리를 모르는 처방은 증상의 모양만 베낀다 (1/3)

- **상황:** [BL-605] — `exchange_exits` 가 같은 청산을 정확히 2행으로 적재 — 는 뿌리를 「적재 경로가
  분류 pass 별로 행을 새로 쓰는 것으로 보인다(**뿌리 미확정**)」로 적고, 그 위에 처방 후보 둘을
  올려 두었다 — ⑴ `order_link_id` 단위 upsert ⑵ 소비 계약에 dedup 의무 정본화. 이번 회차는 그
  둘 중 하나를 고르라는 지시로 시작했다.
- **반증:** 뿌리는 **코드가 아니라 데이터**였다. 스윕이 계정 **행**을 열거하는데
  (`tasks/trading.py:1904-1906` → `exchange_account_repository.py:40-47`) DB 에 같은
  `exchange_uid`(558689281)를 공유하는 계정 행이 **2개** 있었다. `compute_row_hash` 는 거래소 값만
  해싱해 두 행의 `row_hash` 가 **같은데**, UNIQUE 축은 `(exchange_account_id, row_hash)` 라
  **충돌하지 않는다**. ⇒ 배수 = 같은 uid 를 공유하는 계정 행 수. 실측 574행 = 287×2 이고
  287개 해시 **전량**이 두 계정에 걸쳐 있어 셈이 정확히 닫혔다.
- **두 후보가 왜 빗나갔나:** 둘 다 **「적재 코드가 잘못 쓴다」를 전제**로 삼았다. ⑴ 은 축이 다른
  두 행을 unique 로 흡수하지 못하고, ⑵ 는 증상을 소비처마다 반복해 막을 뿐 적재를 안 고친다.
  전제가 틀렸으므로 두 처방 모두 **표적 자체가 없었다**.
- **해결:** ⑴ 「뿌리 미확정」이 본문에 있으면 처방 후보는 **가설이지 선택지가 아니다** — 고르기
  전에 뿌리를 확정해라 ⑵ 뿌리 확정의 가장 싼 도구는 **셈이 닫히는지**다(574 = 287×2 이고 287/287
  이 두 계정에 걸림 ⇒ 배수의 정체가 계정 수임이 즉시 나온다) ⑶ 같은 회차에서 **선례를 먼저 찾아라**
  — 이 레포는 `exchange_uid` 형제를 펴는 관용구를 이미 3곳에 갖고 있었다.
- **1차 누적.** ★**축 판정 (2026-08-14 재계수)** — 「착수 전제·상속 사실이 반증됐다」는 `dev-log/INDEX.md` 2026-08-07~08-12 **22줄 중 12줄**이다. 다만 이 축은 이미 [generator-evaluator-pipeline.md](../development/workflows/generator-evaluator-pipeline.md) **§8.1**(=[LESSON-037])로 승격돼 있으므로 **다시 승격하지 않는다** — 이 카드는 그 축의 개별 사례로 남는다(`lessons.md:12` 규약).

---

### LESSON-089 — **판별력 수치는 스코프를 안 적으면 틀린다.** 결론이 맞아도 근거는 갈아 끼워야 한다 (1/3)

- **상황:** [BL-639]는 「미조인 `exchange_exits` 로 배타성을 판정하면 상시 거부가 된다」를 적으면서
  근거로 **「`matched_order_id IS NULL` 이 34행 / 유니크 27 = 전량을 고른다 ⇒ 판별력 0」**을 박아
  두었다. 이 값은 `docs/backlog.md` 와 `live_session_admin.py` 주석 양쪽에 인용돼 있었다.
- **반증:** 그 값은 **계정 스코프 없이 센 것**이다. 계정을 하나(`19a8166a`)로 좁히면 287행 중
  **25행(8.7%)** 만 고른다 — `ours/exact` 262행은 **미조인 0** 이다. 「전량」도 「판별력 0」도
  지금 데이터에서 성립하지 않는다. 게다가 남은 25행 중 `classification='unknown'` **8건은 전부
  2026-08-07** 하루, 즉 이중 호스트 오염 창에만 몰려 있어 **판별력이 오히려 있다**.
- **그런데 결론은 유지된다:** 남은 25건 중 12건이 `external_manual`(사용자 수동 청산)이라 정상
  상황에서도 발생하고, `unknown` 8건의 적중은 **오염 창 1건에서 유도한 것이라 적합이지 검증이
  아니다**(표본 1). resting 조건부 축은 그런 유도 없이 지금 이 순간의 점유를 직접 잰다.
- **해결:** ⑴ 판별력 수치를 문서에 박을 때는 **모집단의 스코프**(계정·기간·상태 술어)를 같은
  문장에 적어라 — 스코프 없는 「전량」은 재현 불가다 ⑵ **결론이 맞다는 것이 근거가 맞다는 뜻이
  아니다.** 근거가 틀린 채 남으면 다음 사람이 그 수치로 다른 결정을 한다 ⑶ 인용된 수치는
  **인용처까지 같이 고쳐라**(여기서는 백로그 본문·인덱스 표·코드 주석 3곳).

---

### LESSON-090 — **음성 대조가 「도달」을 안 보면 fail-open 이다.** 「제대로 온 경우」만 다룬 대조는 대조가 아니다 (1/3)

- **상황:** 2026-08-08 zero-touch-bundle, [BL-648]. 라이트 캐논 spec 은 착지 시점에 이미
  음성 대조를 갖고 있었다 — 회귀 색(`--warning` 을 [BL-628] 이전 값으로)을 주입하니 **5/5 red**,
  같은 실행에서 다크 짝은 5/5 초록. 「판별력을 확인했다」로 적혀 있었고 그 문장은 참이었다.
- **반증:** codex 평가가 **다른 축**을 물었다. `auditUrl` 이 `page.goto()` 의 **반환값을 버려서**,
  5라우트를 **없는 경로**로 바꿔도 · 감사 직전 **body 를 비워도** 결과가 `hardFail=0 · canon=0`
  이라 **둘 다 5/5 초록**이었다. 화면이 좋아서가 아니라 **잴 것이 없어서** 0 이었다.
  수리 후: 없는 경로 **4 red**(404 프로브는 404 가 정답이라 초록 유지) · 빈 DOM **5/5 red**.
- **왜 놓쳤나:** 기존 대조는 전부 **「페이지가 제대로 왔다」를 배경으로** 값을 나쁘게 만드는
  주입이었다. 배경 자체가 무너지는 실패 모드는 그 축에 없었고, **그 축이 없다는 것은 그 축의
  대조를 안 짜 봐야 안 보인다.**
- **해결:** ⑴ 게이트의 음성 대조는 **두 계열**을 짜라 — 「값이 나빠졌다」와 **「측정이 없었다」**
  (404·5xx·빈 DOM·타임아웃·대상 소멸) ⑵ 그러려면 **관측량**을 결과에 실어야 한다. 소견 배열은
  나쁜 것만 담으므로 **빈 화면과 완벽한 화면이 똑같이 0** 이다 — 둘을 가르는 것은 `examined`
  같은 원시 셈이다 ⑶ 도달 판정은 **코어가 아니라 호출부**에 둬라. 정상 대상 중에 2xx 가 아닌
  것이 이미 있으면(404 프로브·점검 화면) 코어에 박은 「2xx 여야 한다」가 **거짓 red** 를 만든다.

---
