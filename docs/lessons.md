# Lessons Learned

> AI가 실수를 교정받을 때마다 이 파일이 업데이트됩니다.
> 반복 패턴(3회)은 `.claude/rules/` 스택 규칙 또는 해당 정본 축(ADR-026 7축)으로 승격, 본 파일에는 1-line reference 만 보존합니다.
> 승격 경로(구 global.md §6): dev-log 반증 카드 → 본 파일 (3회 반복) → `.claude/rules/` 또는 정본 문서 → 삭제(모델 개선으로 불필요 시).

---

## 작성 규칙

- 새 교훈은 `## LESSON-{NNN} — {제목}` 포맷으로 추가
- 반복 패턴이 동일하면 새 항목 만들지 말고 기존 항목의 **반복 횟수** 증가
- 반복 3 이상이면 승격 대상 (target rule file 명시)
- 승격 완료 시 본문 삭제 + §영구 승격 table 1-line 추가
- 본 파일 한계 **400 lines** — 초과 시 stale 항목 archive 정리 의무

---

## 영구 승격 완료 (rule file로 이전된 항목)

> 본문은 해당 rule file에 있음. 본 파일은 reference table 만 유지.

| ID         | 승격 위치                              | 한 줄 요약                                                                                                          |
| ---------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| LESSON-004 | `.claude/rules/frontend.md` §3 H-1 | `useEffect` dep 에 React Query data / Zustand selector / RHF watch / Zod parse 결과 사용 금지 (CPU 100% loop)       |
| LESSON-005 | `.claude/rules/frontend.md` §3 H-2 | `queryKey` 는 `userId` identity 사용 — Clerk `getToken` 직접 포함 금지                                              |
| LESSON-006 | `.claude/rules/frontend.md` §3 H-3 | React Compiler 호환 — render body 에서 `ref.current = value` 금지, deps-less `useEffect` 로 이동                    |
| LESSON-019 | `.claude/rules/backend.md` §3     | Service mutation 메서드는 `tests/<domain>/test_*_commits.py` 의 AsyncMock spy 회귀 의무 (broken-bug 3 회 재발 차단) |
| LESSON-020 | `.claude/rules/backend.md` §9.2   | Module-level `asyncio.<Semaphore/Lock/Event/Queue>` 추가 시 AST audit + allowlist 의무                              |
| LESSON-037 | `generator-evaluator-pipeline.md` §8.1             | Sprint kickoff 첫 step = baseline 재측정 preflight 의무 (Type A 의무 / B 권장 / C/D 면제)                           |
| LESSON-038 | `generator-evaluator-pipeline.md` §8.2             | Docker worker auto-rebuild on PR merge 의무 + sentinel function startup health check                                |
| LESSON-039 | `generator-evaluator-pipeline.md` §8.3             | Surface Trust 차단 (UI false positive) ≠ 기능 작동 (BE 정확 계산). 두 mechanism 분리 의무                           |
| LESSON-040 | `generator-evaluator-pipeline.md` §8.4             | codex G.0 직후 + Sprint 진입 전 = rapid prereq verification spike (10-30분) 의무                                    |
| LESSON-063 | `generator-evaluator-pipeline.md` §8.5             | 신규 도메인 / 5+ 파일 모듈 신설 직후 = `/deepen-modules` 1 호출 (Iron Law: 1 모듈만) 권장                           |
| LESSON-066 | `.claude/rules/backend.md` §7     | alembic enum = 처음부터 uppercase + downgrade enum swap 의무 (SAEnum/StrEnum 정합, 7차 영구 검증 — dev-log 삭제 전 등재 보충) |

---

## Active Candidates (3 회 검증 미달, 또는 sprint-specific)

### LESSON-001 — Pine Script → Python 변환 시 `exec()` 인젝션 위험

- **상황 / 원인:** Pine → Python 동적 코드 실행 시 사용자 입력 그대로 → 코드 인젝션.
- **해결:** 인터프리터 패턴 (`pine_v2` AST 평가) 또는 RestrictedPython sandbox. `eval/exec` 절대 금지.
- **반복 / 승격:** 1 / ADR-003 + AGENTS.md QuantBridge 고유 규칙 반영 완료.

### LESSON-002 — Celery zombie task recovery (OOM/crash 후 status=running 영구 잔류)

- **해결:** 3-layer — `on_failure` 핸들러 / Celery Beat periodic cleanup (30분+ running → failed) / 수동 cancel 엔드포인트.
- **출처:** ADR-003 §3.

### LESSON-003 — Pine 파싱 "80%+" 가정 과대평가

- **해결:** TV 상위 50 전략 분류 테스트 선행 → "검증된 40% 패턴 지원 + 나머지 투명한 Unsupported" 정책. ADR-003 §2/§4.

### LESSON-007 — worktree 안 `git rev-parse --show-toplevel` 은 main repo 아닌 worktree 경로 반환

- **해결:** main repo 경로 필요 시 `--git-common-dir` 또는 명시 인자 전달. `kickoff-worker.sh` patch 후 본 항목 삭제 예정.

### LESSON-008 — Signal/IPC 식별자는 full id (prefix 포함) 고정

- **상황:** Bundle 2 자율 병렬에서 Planner 가 `{x}` 축약형, Monitor 가 full id (`fe-d.status`) 기대 → silent 멈춤.
- **해결:** Planner 프롬프트에 `SIG_ID = full sprint id (e.g., fe-d)` 명시 + Phase 1 kickoff 직후 Monitor 가 실제 signal 파일명 1회 검증.

### LESSON-009 — Worker 는 worktree 외부 (main repo) 에 파일 생성 금지

- **해결:** Worker prompt "생성하는 모든 파일은 worktree 내부 경로 제한" + squash merge 직전 main untracked 파일 `git status` 검증.

### LESSON-010 — stage worktree 생성 시 3 symlink 필수

- **3 symlink:** `backend/.venv` + root `node_modules` + `frontend/node_modules`. worktree 생성 직후 일괄.

### LESSON-011 — Redis 분산 락 wrapping `async with RedisLock(): pass` 는 mutex 아님

- **해결:** `pass` block 의 lock hold 시간 ≈ 1 RTT. Wrap 은 contention-detect signal + metrics 만. Correctness 는 이어지는 PG advisory + UNIQUE 가 보장.

### LESSON-012 — slowapi 0.1.9 `swallow_errors=True + headers_enabled=True` 동시 사용 시 `request.state.view_rate_limit` 미초기화 AttributeError

- **해결:** `_RateLimitStateInitMiddleware` 로 `request.state.view_rate_limit = None` 선초기화. slowapi upgrade 후 검증·제거 follow-up.

### LESSON-013 — worktree 심링크는 `../../..` prefix (3 단계)

- **원인:** symlink relative path 는 symlink 파일이 위치한 디렉토리 기준. `.worktrees/NAME/backend/.venv` 에서 원본까지 3 단계 필요.
- **해결:** 3 symlink 모두 `../../../*` (루트 `node_modules` 는 `../..` 2 단계). worktree 생성 후 `ls -L <symlink>` 로 resolve 확인.

### LESSON-014 — `conftest.py` 에 모든 필수 env 기본값 주입

- **상황:** `@limiter.limit` endpoint 추가 시 `REDIS_LOCK_URL` 누락 → ConnectionError.
- **해결:** rate-limit endpoint 추가 시 conftest env 기본값 검토 체크리스트. pre-push hook 으로 재현.

### LESSON-015 — Redis 논리 DB 0~2 점유 중 — 분산 락 / rate-limit 은 DB 3+

- **원인:** DB 0=cache / DB 1=Celery broker / DB 2=Celery result backend. lock 은 DB 3+ 격리 (broker burst/eviction 으로 lock 유실 방지).

### LESSON-016 — Next.js 16 은 `proxy.ts` (not `middleware.ts`)

- **해결:** edge middleware 파일명 변경. 새 FE plan 작성 시 `proxy.ts` 로 명시. `grep -r "clerkMiddleware" frontend/src/` 로 실제 파일 확인.

### LESSON-017 — codex Generator-Evaluator 루프는 plan 자체부터 시작 (G0 게이트)

- **해결:** master plan 작성 직후 codex consult 1 회. 발견 critical 을 plan 안 surgery 반영 후 ExitPlanMode.
- **검증:** Sprint 12 G0 7 critical 사전 차단 (savepoint rollback / Bybit auth window 등). 이전 모든 plan 에 누락. Sprint 12 부터 영구 적용.

### LESSON-018 — Heavy codex G-E 루프 시 Sprint scope 실측 +30~50%

- **해결:** Sprint 시작 시 **scope tier** (dogfood / production / multi-tenant) 명시 + codex prompt 포함. G4 BLOCK 시 max 2 iter 한도, 그 후 사용자 결정.

### LESSON-026 — `import a.b.c as d` 가 `__init__.py` re-export 와 충돌 시 변수로 평가됨

- **해결:** `sys.modules["src.tasks.celery_app"]` 우회. test 안 module reference 시 적용.

### LESSON-027 — Sprint 18 `_WORKER_LOOP` task 의 inner 함수는 `_async_xxx` 직접 await 가 pytest-asyncio 호환

- **해결:** `run_in_worker_loop` 우회 (이미 loop 안에서 실행 시 RuntimeError). Inner async 함수 직접 await + `create_worker_engine_and_sm` monkeypatch.

### LESSON-028 — PostgreSQL JSONB strict — NaN/Infinity 명시 sanitize 의무

- **해결:** Recursive `_sanitize_for_jsonb(value)` helper. `math.isnan/isinf` → `None`. dict/list/tuple recurse. JSONB INSERT 전 의무.

### LESSON-029 — SQLAlchemy enum auto cast vs Alembic String 컬럼 mismatch

- **해결:** 모델 field 에 명시적 `Column(String(N))` 선언. Alembic migration 도 String(N) (PG enum DDL 회피). 사용처 `.value` 호출 + `str(...)`.

### LESSON-030 — Bybit v5 `set_leverage / set_margin_mode` 는 idempotent — "not modified" silently ignore

- **해결:** ccxt `BadRequest` catch + `"not modified"` 포함 시 silently ignore. Bybit Provider 한정.

### LESSON-031 — Bybit Linear contract symbol normalize (ccxt unified)

- **해결:** `_to_bybit_linear_symbol(symbol)` helper — `BTC/USDT` → `BTC/USDT:USDT`. UI/Strategy spot format 유지.

### LESSON-032 — base-ui `Select.Value` 가 raw value 표시 — render prop 으로 name mapping

- **해결:** `<SelectValue>{(value) => lookup(value)?.name ?? "..."}</SelectValue>`. ID-based combobox 의무.

### LESSON-033 — Era 3 Sprint type 분류 (kickoff 의무, Sprint 28 도입)

- **type:** A 신규기능 (의무) / B BL fix risk-critical (권장) / C dogfood hotfix (압축) / D docs only (면제).
- **검증:** Sprint 28 5 Slice 차등 적용 + Sprint 30+ 부터 영구 적용 권고.

### LESSON-034 — office-hours 재진행 (3개월+ 경과 시 의무, Sprint 28 도입)

- **해결:** sprint kickoff frontmatter `office-hours 진행 여부` 필드 + 3개월+ 경과 + dogfood evidence 누적 시 Q4/Q5 + Q1-indie 변형 재진행. 결과는 ADR Addendum 으로 보존.

### LESSON-035 — dual metric (sprint 종료 의무, Sprint 28 도입)

- **3 metric:** Self-assess ≥7/10 (근거 ≥3줄) + 신규 BL count (P0=0, P1≤2) + 기존 P0 잔여 ≥1 감소. 셋 다 PASS 시만 sprint 완료 판정.

### LESSON-036 — Slice cascade PR pattern (Option C staging)

- **해결:** sprint kickoff 시 `stage/h2-sprint{N}-{theme}` 생성. 각 Slice sub-branch 가 stage base PR. cleanup PR 도 stage cascade. 사용자 manual stage→main merge (sprint 종료 + dual metric PASS 후).

### LESSON-041 — Pine partial declaration → 422 reject (Sprint 38 BL-188 v3 A1)

- **상황:** `default_qty_type` 만 명시 + `default_qty_value` 생략 = ambiguous semantics.
- **해결:** `PinePartialDeclaration(BacktestError)` 422 status + AST corpus audit 정기 검증. Pine `strategy()` paired 인자 strict invariant.

### LESSON-042 — Sizing source 단일 입력 강제 (Sprint 38 BL-188 v3 A1)

- **해결:** `position_size_pct` (Live mirror) 와 `default_qty_*` (manual) 동시 명시 시 `SizingSourceConflict` 422. BE Pydantic `@model_validator` + FE Zod `.refine()` parity.

### LESSON-043 — Live mirror leverage parity (Nx reject, BL-186 후 unlock)

- **해결:** engine 1x equity-basis only / live `leverage != 1` 시 `MirrorNotAllowed` 422. FE 4-state badge `live_blocked_leverage` 명시. Manual sizing override path 제공.

### LESSON-044 — 메인 세션 = 표준 prefix / worktree 워커 = `worker-*` prefix

- **해결:** stage push 시 `QB_PRE_PUSH_BYPASS=1` env override + branch swap (메인 worktree 가 stage). `--no-verify` 금지. pre-push hook 화이트리스트 = `feat/fix/chore/docs/test/refactor/hotfix`.

### LESSON-045 — env override 의무 (다른 프로젝트 host port 충돌)

- **해결:** isolated mode (5433/6380) 가 default. baseline preflight 시 `TEST_DATABASE_URL / REDIS_URL / REDIS_LOCK_URL / CELERY_BROKER_URL` inline env override 의무. `.env.local` 변경 회피 (다른 도구 영향).

### LESSON-046 — 통합 dogfood = Generator-Evaluator 못 잡는 회귀 detection layer

- **해결:** Day 7.5 mid-dogfood 시 (a) FE idle CPU 측정 + (b) main 베이스 delta + (c) navigate 시 CPU 변화 = falsification signal 3 종. 통합 회귀 발견 시 즉시 gate FAIL + 다음 sprint = polish iter.

### LESSON-047 — Turbopack `turbopack.root` 명시 시 wrong path = file watcher storm (400% sustained)

- **해결:** monorepo lockfile 위치 확인 의무. multi-lockfile warning 은 false alarm — 자동 inferred root 사용. fix 적용 시 fresh restart + idle CPU 6 samples × 5s 측정 의무. (자동 inferred = pnpm-lock.yaml 있는 root)

### LESSON-048 (2/3) — Playwright MCP + 인증 cookie 자동 dogfood

- **해결:** dogfood 시 Playwright MCP `browser_navigate` 자체 1 회 시도. 메인 세션 stack 의 Chromium = 사용자 chrome cookie 공유 가능 (인증 페이지 자동 검증). manual 시간 1/3+ 단축. clipboard / 모바일 viewport 등 자동화 어려운 항목 사용자에게 명시 위임.

### LESSON-049 — codex G.4 P1/P2 즉시 fix 패턴 (cmux 자율 병렬)

- **해결:** P2 발견 시 (a) cmux send + sig running reset 우선 / (b) session stuck 시 메인 세션 worktree 직접 push (LESSON-035 isolation 양립). defer 옵션은 demo/Beta 영향 없을 때만.

### LESSON-050 — Sprint kickoff design source 명시 의무

- **해결:** 디자인 트랙 sprint kickoff prereq 첫 step = `docs/reference/design/prototypes/` + `DESIGN.md` + `*.pen` + Figma URL 모두 grep + 5지선다 prereq 옵션 (없음 + 4 source 종류). design source 누락 발견 시 즉시 Wave 2 추가 spawn.

### LESSON-051 — Agent isolation worktree 4 spawn 시 baseline 정리 의무

- **해결:** Sprint kickoff prereq 에 baseline 정리 명시 — dev server 중단 / docker idle stop / `pnpm install` 1 회 사전 / worktree prune.

### LESSON-052 — Worker prompt 첫 step `pwd` + cwd 검증 의무

- **해결:** Worker prompt 첫 step = `pwd` 출력 + cwd 가 worktree 인지 확인 → 메인 cwd 면 즉시 STOP. 절대경로 작성 금지 (cwd-relative). node_modules `pnpm install` 금지 (symlink 활용). 보고 양식에 isolation 위반 / CPU 자가 관찰 / node_modules 처리 3 항목 추가.

### LESSON-053 — Agent tool isolation 한계 — N=4+ 시 cmux 우선

- **해결:** N=4+ 동시 spawn 은 cmux + 사용자 통제 baseline. Agent tool isolation 은 N=1-2 또는 즉시 진행 요청 시 fallback. Sprint kickoff prereq 에 spawn 방식 (cmux vs Agent) 명시.

### LESSON-054 — Mental model 일관성 > fintech 다크 권장 (single-page 다크 회피)

- **해결:** 단일 페이지만 다른 theme 적용 (예: /trading 만 다크) 은 mental model 손상. light/dark 혼용은 manual toggle 또는 시스템 `prefers-color-scheme` 통한 일관 적용. prototype 정합성보다 mental model 일관성 우선.

### LESSON-055 — Worker prompt 첫 step `cd <absolute worktree path>` 사전 명시 의무

- **4 조건 (Sprint 43 검증 — 12 worker × 3 wave, 위반 0):**
  1. 메인 세션이 사전 worktree + branch + node_modules symlink 일괄 생성
  2. Worker prompt 첫 step에 `cd <absolute worktree path>` (relative 금지)
  3. `pwd` 검증 후 메인 cwd 면 STOP
  4. `git checkout -b` step **제거** (worktree 가 이미 branch attached)

### LESSON-062 — ADR 결정이 SSOT (AGENTS.md 표현) 변경 시 동기화 의무

- **상황:** vectorbt → pine_v2 SSOT 변경 (ADR-011 §6/§8, Sprint 8a) 후 AGENTS.md `핵심 도메인` 표현 3 주 stale. 다음 세션 LLM 이 stale SSOT 신뢰 → 잘못된 인사이트.
- **해결:** ADR 결정이 백테스트 엔진 / 핵심 도메인 정의 / 기술 스택 표현 변경 시 같은 PR 또는 다음 sprint close-out 안에 AGENTS.md 동기화 의무.

### LESSON-064 (3/3 — 정식 승격 후보) — `/deepen-modules` audit silent failure 판단 = 직접 read + 전체 dispatch 경로 추적

- **상황:** BL-205 `OrderReceipt` 3-state 가 단일 grep 으로 silent failure 등재됐으나 codex G.0 2차 재검증 결과 = 의도된 _create flow_ simplification, _fetch flow_ 는 별도 `OrderStatusFetch` 4-state. 코드 변경 0, ADR 문서화로 Resolved.
- **해결:** (a) 단일 파일 grep 미확정 / (b) `_map_*` reverse 매핑 + consumer 전수 추적 / (c) BL 등재 전 codex G.0 cross-check. post-merge audit (Sprint 48 Worker E reverse-mapping audit) = positive validation safety net.
- **3차 검증 (2026-06-30 stress_test-deepen):** BL-363 boilerplate 의 money-path 위험을 단일 grep 이 아니라 **직접 read(`service.py:298-411`) + git co-change 추적(`6c7adfba` WF 누락 → `ffb2299b` 별도 패치)** 으로 확정 — config-drift 가 실제 silent corruption 으로 한 번 물었음을 증명. `StressTestKind` dispatch 도 5 site/3 파일 전수 추적으로 over-eng(C3 거부) 판단. 단일 grep 이었으면 "boilerplate 추출" 표면 가치만 봤을 것 → 직접 read 가 money-path framing + git 실증을 끌어냄. **3/3 누적 → `generator-evaluator-pipeline.md` §8.5  의 deepen-modules 절차에 "단일 grep 금지, 직접 read + dispatch/co-change 전수 추적 의무" 영구 승격 후보(사용자 검토).**
- **[LESSON-063 §7.5 4차 재현 corroboration]** multi-SSOT/평행정의 패턴: pine_v2 STDLIB(1) → backtest BacktestMetrics 24-field 4-site(2) → trading exit-field(3) → **stress_test cell 8-site + add-a-type 7파일 lockstep(4, git verbatim 2회)**. AI 누적 코드는 신규 도메인 타입 추가 시 N 타입 × M 레이어 평행 확장을 디폴트로 누적 → §7.5 `/deepen-modules` 신규 도메인 직후 의무 재확인.

### LESSON-065 — subagent review 2-stage 가 monkeypatch indirect dependency 못 잡음

- **상황:** Sprint 48 PR #246 BL-203 service.py 5-service 분할 → 5 test FAIL (`logger`/`datetime`/`settings` AttributeError). spec/code reviewer 2-stage PASS 통과 후 GitHub Actions 에서 detection.
- **원인:** Python namespace 분리 — shim re-export 는 module-level attribute (logger/datetime/settings/typing import) 까지 보존 안 함. `monkeypatch.setattr(service_mod, ...)` 가 shim attribute 만 변경 → services/\* 안 자체 attribute 영향 0.
- **해결:** module rename/split 동반 PR review 의무 — (1) `monkeypatch.setattr(<module>, ...)` 패턴 + module split 영역 발견 시 attribute resolution 직접 검증 / (2) shim 의 namespace 한계 인지 / (3) Preflight grep audit 시 alias (`as service_mod`) 패턴 검색 의무.

### LESSON-068 — Korean docs lint mechanism 부재 → §5/§6 위반 누적 자연 발생 (1/3)

- **상황:** 2026-05-15 CLAUDE.md align audit Track C 검증 결과 — `~/.claude/CLAUDE.md` §5 (한국어 콜론 종결 금지) **181 line 위반** (docs/dev-log 161 + dogfood 12 + guides 8) + §6 (신규 source file 1줄 한국어 주석 의무) **70 file 누락** (BE 14/157 = 8.9% + FE 56/243 = 23%). main.py / core/config.py / trading/registry.py / app/layout.tsx 등 핵심 file 도 누락.
- **원인:** lint mechanism 0 — markdownlint custom rule (한국어 sentence + `:` end-of-line) 부재 + ESLint custom rule (한국어 주석 첫 3줄 의무) 부재 + ruff custom rule 부재. LLM 매 generation 자연 위반 + reviewer 0 → 누적.
- **해결 path:** (a) ruff custom plugin 또는 markdownlint custom rule 으로 §5 자동 검출 + auto-fix script (`:` → `.` 한국어 sentence ender 한정) (b) ESLint custom rule + ruff custom rule 으로 §6 누락 file 검출 + pre-commit hook (c) 누락 70 file 일괄 한국어 헤더 추가 sprint = BL-307. 1차 누적 (Sprint 60 Track C) — 3차 시 영구 규칙(문서 lint 축) 승격 path — 구 global.md §5/§6 은 ADR-026 으로 소멸, 승격처는 `docs-audit.sh` 확장.

### LESSON-069 — 저-카디널리티 라벨이 **위험도가 다른 갈래**를 합치면 큰 갈래가 작은 갈래를 묻는다 (1/3)

- **상황:** 2026-07-30 close-mismatch-visibility. `metrics.py` 가 Bybit `110017` 을 단일
  `reduce_only_violation` 으로 접었다. 실측 39건 = `reduce-only ... same side`(★엔진↔거래소
  **반대 방향**, 머니-패스 위험) **9건** + `current position is zero`(무해) **30건**.
  무해가 3배라 counter 를 보면 "유령 포지션 문제" 로만 보이고 **방향 반전은 보이지 않았다.**
  위험 갈래는 **5개 세션에 걸쳐 반복 발생** 중이었다.
- **원인:** 카디널리티 보호를 위해 retCode 로만 매핑했다. 그런데 `gates-and-traps.md:104` 와
  `live-close-diagnostics.md` §2 가 **이미 "코드로만 묶지 마라, retMsg 까지 갈라라" 고 적어 뒀는데**
  코드가 그 경고를 지키지 않았다. 문서가 경고를 적는 것과 코드가 지키는 것은 다른 사건이다.
- **해결:** 코드 확정 **뒤** 그 안에서만 retMsg 로 갈래를 가른다(코드 판정에는 retMsg 를 쓰지 않는
  BL-512 원 제약은 유효). 잔여 버킷을 남겨 미지 문구가 조용히 사라지지 않게 한다.
- **일반 규칙 후보:** **저-카디널리티 라벨을 만들 때 "이 버킷 안의 두 값이 서로 다른 조치를
  요구하는가" 를 물어라.** 요구한다면 그 코드는 라벨이 될 수 없다. 그리고 **큰 갈래가 작은 갈래를
  묻는 방향**(무해가 다수, 위험이 소수)이면 평균이 안전을 말하게 된다.
- **1차 누적.** 3회 시 영구 규칙 승격 후보 (`generator-evaluator-pipeline.md` §8).

### LESSON-070 — 비중(%)을 인용하기 전에 **분모가 무엇을 세는지** 코드로 확인해라 (1/3)

- **상황:** 같은 회차. 직전 스프린트가 `deferred_market_inflight` 를 "유실 채널 합의 **75%**" 로
  적었고 그 위에 다음 스프린트를 설계했다. 실측 — 그 counter 는 `bool(new_events)` 로 오르는데
  `new_events` 는 `entry`/`close` **시장가 이벤트만** 담고 **조건부 진입은 그 테이블을 거치지 않는다.**
  즉 stop-entry 전략에서 그 값은 **「청산 tick 수」** 이고, 세션 실측에서 events 9건(전량 `close`)과
  counter 9 가 **1:1** 이었다. 게다가 증가 지점이 `desired` 를 **읽기 전**이라 미룰 진입이
  0건이어도 발화한다.
- **해결:** 비중을 쓰기 전에 (a) 분자·분모가 **같은 사건 단위**인가 (b) 그 counter 가 증가하는
  **코드 위치가 무엇을 이미 알고 있는가** 를 확인한다. 후자가 이번의 결정타였다 — 증가가
  판정 대상보다 **앞**에 있으면 그 counter 는 판정에 대해 아무것도 모른다.
- **1차 누적.**

### LESSON-071 — 합계가 닫힌다는 것은 귀속이 옳다는 증거가 아니다 (1/3)

- **상황:** 2026-08-06 backtest-reality-gap. 원장 event 를 라이브 진입에 귀속하는 두 방식
  (시간순 FIFO vs 직결 링크)이 86건 중 59건에서 서로 다른 주문을 골랐는데, **양쪽 모두**
  버킷 합이 dedup Σ(−149.85)와 소수 8자리까지 닫혔다. 닫힘은 「한 번씩 세었다」의 성질이지
  「맞는 곳에 붙였다」의 성질이 아니다. 틀린 귀속 위의 「가격 격차 +19.36」은 옳은 귀속에서
  **부호까지 바뀌었다**(+28.35 — 중간 반사실은 −0.36).
- **해결:** 귀속 있는 집계는 3층으로 검증한다 — ⑴ 합계 닫힘 ⑵ 귀속 근거 분포(linked/inferred)
  ⑶ **행별 독립 판별자**(이번엔 event 의 진입가 ↔ 귀속된 주문의 체결가 대조, 80/81 exact).
  합은 telescoping 이라 계열 전체가 한 칸 밀려도 못 본다 — 행별 대조만이 가른다.
- **1차 누적.**

### LESSON-072 — 사전등록 지표는 등록 전에 「기각 영역이 도달 가능한가」를 그려라 (1/3)

- **상황:** 같은 회차. 사전등록 ③(비용 설명 비율 ≥40%, Σ 후 절대값)이 실데이터에서 **거의
  항진명제**였다 — FAIL 영역이 Σdiv > +253 / < −590 뿐(라이브 총손익의 9배 규모)이고 상한이
  없어 134%·3095% 도 「PASS」로 읽힌다. 부호 상쇄 때문에 같은 총발산에서 밖-abs 정의는
  49%~3095%(63배) 흔들린다(행별-abs 는 2.7배). 판정은 「미판정 + 정의 결함 병기」로 강등했다.
- **해결:** 비율 지표는 ⑴ 분자·분모의 상쇄 구조(Σ 후 abs vs 행별 abs)를 등록 전에 정하고
  ⑵ 상·하한을 구간으로 걸고 ⑶ 등록 직후 적대 검증자에게 **기각되는 관측 공간**을 그리게
  한다 — 기각 영역이 물리적으로 원격이면 그 지표는 적중해도 증거가 못 된다.
- **1차 누적.**

### LESSON-067 — codex evaluator 는 분산형(G.0 + slice spot + G.4)이 정본 패턴, 비용은 스코프의 함수 (6/6)

- **상황:** Sprint 39/51~57/59/60 에 걸쳐 codex evaluator 호출 패턴을 6회 실측 — 단일 G.0
  일괄(518k) vs 분산형(G.0 + slice spot + G.4). 분산형 비용은 스코프에 따라 216k~1.8M tokens
  로 가변(revision 양 + 트랙 수의 함수)이며, spot 축소(Sprint 52 형)로 1/5 까지 줄었다.
  「단일 worker single-day scope 자율 진행 가능」 판정도 같은 실측 계열에서 6/6 누적.
- **해결:** evaluator 는 분산형을 기본으로 하되 slice spot 은 스코프가 좁으면 생략한다.
  budget 은 고정값이 아니라 스코프 함수로 계획한다.
- **6차 검증 (dev-log 삭제 전 등재 보충 — 원문은 git history `docs/dev-log/2026-05-1*-sprint5*-close.md`).**

---

## 확장 시점 판단 기준 (변경 없음)

> 아래 조건이 충족되면 해당 패턴 도입을 검토한다. 그 전까지는 도입하지 않는다.

| 패턴                               | 도입 트리거                                                   | 현재 상태 |
| ---------------------------------- | ------------------------------------------------------------- | --------- |
| 코드 내 중첩 AGENTS.md             | 도메인 3 개 이상 + 각각 반직관적 비즈니스 규칙 3 개 이상 누적 | 미해당    |
| Action-Based Routing (Context Map) | (구 `.ai/rules/domain.md` 구상 — 부재) 도메인 규칙 파일이 200 줄 초과 + 섹션 분리로도 부족     | 미해당    |
| 모노레포 규칙 분기                 | `apps/` 하위에 독립 `package.json` 이 2 개 이상 존재          | 미해당    |
