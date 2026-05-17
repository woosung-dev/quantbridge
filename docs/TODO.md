# QuantBridge — TODO

> **Last Updated:** 2026-05-17 (Sprint 60→61→62 누적 3-sprint cycle 완료 + **Beta 본격 진입 결정 ★★★★★** — BL-070~075 트랙 활성화)
> **Active Sprint:** **Sprint 63 = Beta 본격 진입 prep (BL-070~072 외부 의존 작업)** — 사용자 manual 영역 진입
> **Active Branch:** main (PR #288 + #289 + #290 모두 머지 완료)
> **Sprint type:** D (external-dependency setup — domain + DNS + Backend prod + Resend)
> **office-hours 진행:** N
> **Next Trigger:** BL-070 (도메인 + DNS) + BL-071 (Backend prod 배포) + BL-072 (Resend + Waitlist 활성화) = 사용자 manual 4-8h + DNS 24h. BL-073/074/075 = 위 완료 후 자연 trigger.

---

## 🚀 Beta 본격 진입 결정 (2026-05-17)

**근거**:

- Composite Health 4.18 (2026-05-13) → 6.08 (Sprint 60 후) → 7.5 (Sprint 61 후) → **추정 8.5+** (Sprint 62 후, 재측정 skip 결정).
- 4-AND gate: (a) Composite ≥ 7 ✅ / (b) Critical = 0 ✅ (BL-340 회복 + BL-339 페이지 내부 BL-356~359 fix) / (c) High ≤ 3 ✅ (P0 BL-350+354 fix + P1 BL-353/356 fix) / **(d) 본인 의지 ✅**.
- Sprint 60→62 누적 3-sprint cycle = 17 + 11 + 6 = **34 BL Resolved**. LESSON-067 6차 검증 (단일 worker 단축 패턴 누적).
- Multi-Agent QA 1차 → Sprint 60 fix → 2차 → Sprint 61 fix → 3차 → Sprint 62 fix = LESSON-068 보강 **3/3 누적** (정식 승격 후보).

**Beta 본격 진입 prep (BL-070~072) 필수 manual**:

- **BL-070** 도메인 구매 (e.g. quantbridge.io) + DNS + Cloudflare (선택) — 1-2h + DNS 전파 24h
- **BL-071** Backend 프로덕션 배포 — Cloud Run / Railway / Render 선택 + Postgres prod + Redis prod + Clerk production key + 보안 헤더 production gunicorn (BL-347 server strip 동시 처리) — 2-4h
- **BL-072** Resend 계정 + 이메일 도메인 verify + Waitlist 활성화 — 1-2h + 24h verify

**Beta 본격 진입 자연 trigger (BL-070~072 완료 후)**:

- **BL-073** Twitter/X #buildinpublic 캠페인 시작 (사용자 수동)
- **BL-074** Beta 인터뷰 3명 × 3회 (5-10명 onboarding 후, narrowest wedge 60% 검증)
- **BL-075** H2 진입 게이트 설계 (BL-005 self-assess ≥ 7/10 직후, 3-5h)

**Sprint 62 production deploy 시점 묶음 자동 해소 BL**:

- BL-320 Development mode 배지 → production key 사용 시 자동 해소
- BL-321/352 Clerk application name → dashboard 1분 변경 (BL-070 시점)
- BL-347 server header leak → gunicorn `--server_header False` (BL-071 시점)
- BL-261 Clerk custom domain → DNS CNAME (BL-070 시점)

---

## Recently Completed — Sprint 62 fix-first (PR #290 main merge, 2026-05-17)

- [x] **T-1 BL-350+354** ★★★ Optimizer Zod resilience — FE row-level safeParse + skipped_count + 컴포넌트 graceful + BE row-level try/except (PR #290)
- [x] **T-2 BL-356/357/358/359** 모바일 페이지 내부 터치 ≥44pt 묶음 — TabsList + date-preset-pills + KPI ? + 편집 링크 + UserButton + 계정 삭제 모두 mobile h-11/size-11 + md: 분기
- [x] **T-3 BL-353** landing step 01 라벨 hero 정합 ("전략 업로드" → "전략 코드 붙여넣기")
- [x] **PR #289 + #290 머지 완료** — main `36bb4e0`
- [x] **검증**: BE optimizer 145 PASS + 2 skipped / FE 716 PASS / tsc + lint + ruff + mypy clean
- [x] **신규 11 test**: BE row-level resilience 3 + FE component graceful 3 + 회귀 갱신

**실측 시간**: ~2-3h vs plan 6-8h (Sprint 60/61 패턴 재현, LESSON-067 6차 검증).

### Sprint 62 BL Resolved 마킹 (6 BL)

- ✅ BL-350+354 ★★★ Optimizer Zod error 도배 차단 / BL-353 landing step 01 라벨 / BL-356 모바일 페이지 내부 / BL-357 strategies 편집 링크 / BL-358 UserButton width 28 / BL-359 trading 계정 삭제

---

## Recently Completed — Sprint 61 fix-first + Multi-Agent QA 재측정 (2026-05-17)

### Sprint 61 fix-first (PR #288 main @`26b7486` merge + hotfix `9103134` PR #289)

- [x] **PR #288 merge** — 8 BL fix (T-4 BL-312 OpenAPI gate / T-5 BL-311 보안 헤더 / T-6 BL-310 healthz /livez / T-1 BL-340 overflow / T-2 BL-339 터치 / T-3 BL-319+321+328 Clerk dev surface / T-7 BL-327 KPI tooltip / T-8 BL-322+323 Hero copy + Optimizer 메뉴)
- [x] **Hotfix PR #289** — BL-348 protected route accounts.dev redirect (clerkMiddleware second arg signInUrl/signUpUrl 명시) + BL-349 healthz timeout 8→12s

### Multi-Agent QA 재측정 (Standard depth, `docs/qa/2026-05-17-post-sprint61/`)

- [x] **QA Sentinel 재측정** — 7.45 → 7.8 (+0.35), Sprint 61 fix 11 BL 직접 검증 8 PASS / 2 PARTIAL / 1 manual pending
- [x] **Curious 재측정** — 6.5 → 8.0 (+1.5), Maybe → **Yes (가벼운 조건부)**, 친구 추천도 ★★★ → ★★★★
- [x] **Casual 재측정** — 5.2 → 7.4 (+2.2), 용어 해독률 22% → **89%**, 막힘 9 → 3, 포기 abandon 안 함
- [x] **Mobile 재측정** — 3.8 → 6.5 (+2.7), Critical 2 → 1 (BL-340 회복 ✅, BL-339 페이지 내부 ~15 잔존)
- [x] **통합 HTML** `docs/qa/2026-05-17-post-sprint61/integrated-report.html` — **Composite 7.5/10** (목표 정확 도달, Pre 6.08 → △ +1.42)

### Sprint 61 BL Resolved 마킹 (11 BL)

- ✅ BL-310 (PARTIAL — /livez 분리 PASS / healthz timeout 12s 완화) / BL-311 (4/5 헤더 PASS, server strip FAIL → BL-347 follow-up) / BL-312 / BL-319 (hotfix BL-348 와 묶음) / BL-322 / BL-323 / BL-327 / BL-328 / BL-339 (PARTIAL — navigation chrome ✅, 페이지 내부 ~15 잔존 → BL-356~359 follow-up) / BL-340 / BL-348 / BL-349
- ⏭️ BL-320 (defer Sprint 62 production deploy) / BL-321 (사용자 manual pending)

### 신규 BL (Multi-Agent QA 재측정, BL-347 ~ BL-360, 11건)

- **P0 ★★★ 공통**: BL-350 (Curious) + BL-354 (Casual) = `/optimizer` Zod error 도배 (Sprint 50-52 retro row + 53-55 schema tightening 합집합, Sprint 61 BL-323 사이드바 노출의 side-effect)
- **P1**: BL-353 (step 01 라벨 통일) / BL-356 (모바일 페이지 내부 터치 11 violations)
- **P2**: BL-347 (server header leak — uvicorn flag) / BL-351 (Apple/Google SSO aria-label 영어) / BL-357 (strategies 텍스트 링크 38x16) / BL-358 (UserButton width 28 + ghost DOM) / BL-359 (trading "계정 삭제" 16x16)
- **P3**: BL-352 (Clerk dashboard application name manual) / BL-355 ("Demo" → "데모") / BL-360 (backtests 375x667 +9px overflow noise)

---

## Sprint 62 분기 후보 (사용자 결정 대기)

| 옵션                               | 권고                                                          | scope                               | 기대 효과                             |
| ---------------------------------- | ------------------------------------------------------------- | ----------------------------------- | ------------------------------------- |
| **A. fix-first Sprint 62 (★★★★★)** | BL-350/354 (4-5h) + BL-356~359 묶음 (2-3h) + BL-353 (5분)     | ~6-8h 1 day single worker           | Composite 7.5 → 8.5+ → Beta 본격 진입 |
| B. Beta 본격 진입 즉시 (★★★)       | gate (a) PASS, BL-350/354 = Optimizer 메뉴 일시 hide          | dogfood 5명 onboarding 중 추가 처리 | BL-070~075 트랙                       |
| C. Sprint 47 Deepening 2차 (★★)    | BL-201/203/204 architectural                                  | —                                   | Mobile/UX 갭 우선순위 낮음            |
| D. mainnet 진입 (★)                | BL-003 Bybit runbook + BL-347 server strip + Clerk production | —                                   | H1 종료 gate                          |

---

## Recently Completed — Multi-Agent QA 2026-05-17 1차 (Sprint 60 → 61 baseline)

- [x] **사전 환경 검증** — FE :3100 + BE :8100 + worker 3종 (default/ws_stream/optimizer_heavy) 부팅 + environment fingerprint 기록
- [x] **QA Sentinel** Exhaustive — 7.45/10, BL-310~316 (7건, Critical 0 / High 4 / Med 2 / Low 1), Sprint 60 P0 fix source-level PASS 10/0
- [x] **Curious** Exhaustive — 6.5/10 Maybe, BL-317~326 (10건, Critical 0 / High 2 / Med 5 / Low 3)
- [x] **Casual** Exhaustive — 5.2/10, BL-327~337 (11건, Critical 0 / High 2 / Med 4 / Low 5), 막힘 9건 + 용어 해독률 40% + axe-core 92 serious
- [x] **Mobile** Exhaustive — 3.8/10, BL-338~346 (9건, **Critical 2** / High 3 / Med 2 / Low 1) — Casual PASS 보고 중 2건 false positive 검출
- [x] **통합 HTML** `docs/qa/2026-05-17/integrated-report.html` — Composite 6.08/10 (베이스라인 4.18 → △ +1.90)
- [x] **Sprint 61 plan** `docs/sprint-61-plan.md` — 8 BL fix-first, ≈ 23h scope

**Composite 6.08 / 10** — Beta 4-AND gate (a) FAIL 6.08<7 / (b) FAIL Crit 2 / (c) FAIL High 11 / (d) Day 7 NPS 결과 보류.
**분기 결론**: Sprint 61 fix-first 진입 → Sprint 62 Beta gate 재측정.

### 신규 BL (Sprint 61 fix-first 진입)

- **P0 (3)**: BL-339 터치 타겟 / BL-340 Trading overflow / BL-319+320+328+321 Clerk production (★★★ 3 페르소나 공통)
- **P1 (5)**: BL-310 healthz /livez / BL-311 BE 보안 헤더 / BL-312 OpenAPI gate / BL-327 KPI tooltip / BL-322+323 Hero copy + Optimizer 메뉴

### 신규 BL (Sprint 62+ 이연)

- **P2 (8)**: BL-313/314/315/316/329/330/332/344/345
- **P3 (13)**: BL-317/318/324/325/326/331/333/334/335/336/337/338/346

---

## Recently Completed — Sprint 60 (2026-05-14, ~8h actual / plan 25h)

- [x] **S0 Preflight** — slowapi inventory 강화 (false-positive 해소) + codex G.0 (master plan 31 finding 반영)
- [x] **S1 BL-244** — Optimizer 3 endpoint slowapi headers_enabled Response param fix (commit 026f7c9, codex G.1 PASS 0 findings)
- [x] **S2 UI 정직** — 가짜 marketing/testimonial/Disclaimer/내부 ID 일괄 제거 (3 commit / 27 files / vitest 27 PASS / codex G.2 2회 FAIL → 사용자 gate 명시 승인)
- [x] **S3 Auth/Routing** — Hero CTA /sign-up + middleware redirect + webhook env + /pricing (commit 14fda48)
- [x] **S4 Mobile + Clerk** — Sheet drawer + UserButton wrapper + SheetClose 44×44 + appearance.elements size-9 (2 commit / codex G.3 PASS 재진입)
- [x] **S5 안전헤더** — next.config.ts 5 헤더 + /metrics auth test (commit 2d352c2)
- [x] **S6 Close-out** — dev-log + REFACTORING-BACKLOG + TODO.md 갱신 (this)
- [x] **17 BL Resolved**: BL-244/260/262/265/268/269/270/271/273/275/280/285/300/303/305 + BL-245/246/274

**Composite Health 추정**: 4.18 → ~7.8-8.5 (manual smoke 후 보정 의무, 목표 8.0 달성).

### Sprint 60 Deferred (사용자 manual)

- [ ] Playwright e2e Mobile-Safari spot-check (viewport 4종 + a11y axe-core) — BL-285/300/305 evidence
- [ ] Critical 11 → 0 BL별 evidence 표 (screenshot/curl trace, dev-log 첨부)
- [ ] Celery worker 1+ 환경 manual smoke (backtest/optimizer 영구 pending 회피)
- [ ] PR 분리 — 1a1dbda LLM convert + Sprint 60 8 commit squash merge 결정
- [ ] codex G.4 GATE 호출 (close-out 마지막 단계, 700k tokens)

### Sprint 61 후보 (Day 7 + manual smoke 결과 합산 분기)

- **(a) Composite ≥8.0 + 본인 의지 O** → Beta 본격 진입 (BL-070~075 + BL-261 Clerk custom domain)
- **(b) Composite 6.5~7.9 + polish iter** → P1 Cleanup: BL-245/274 보안 헤더 polish (CSP strict) / BL-247 에러 schema / BL-250 ADR-003 request.security / BL-264 TTFV WS / BL-301 모바일 가로 / Casual UX BL-281~286
- **(c) Composite <6.5** → 추가 trust 회복 + Sprint 60 회고

### 신규 BL (Sprint 61 follow-up)

- [ ] BL-신규 Clerk JWT 60s expired E2E case (plan v2 P1-2 Playwright auth-flow.spec)
- [ ] BL-신규 MobileNav unit test (G.3 P2-3 append, drawer open/close/route/Escape/UserButton hit target)
- [ ] BL-신규 Backend test fixture DB password 환경 (S1/S5 integration test 3 ERROR 공통)

> 사람과 AI 가 공동 관리하는 활성 작업 추적 파일.
> 차단 항목은 `[blocked]` 표시 / 질문은 §Questions / 활성 BL 상세는 [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md) / sprint 회고는 [`dev-log/INDEX.md`](./dev-log/INDEX.md).

---

## 활성 sprint 상태

### Sprint 59 (완료, 2026-05-13)

- **PR 묶음 (5 PR squash merge):** #273 (`_worker_engine` SSOT, -163L) + #274 (Pine v1 demolition, -4838L) + #275 (BACKLOG 압축 1028→587L) + #276 (158 BL → 13 Active 트리아주) + #277 (backtest-form 5-split, 866→232L)
- **검증:** BE 회귀 0 (pine_v2 537 PASS / tasks 146 PASS / engine 138 PASS) + FE 회귀 0 (vitest 680 PASS) + ruff/mypy/tsc/lint clean
- **신규 BL:** 0 / Resolved (PR-D 5-rule triage): 158 BL → **13 Active + 8 Deferred + 137 Archived**
- **누적 net deletion:** ~6,000+ lines (메타 노이즈 + dead code + locality 정리)
- **상세:** [`docs/dev-log/2026-05-13-sprint59-close.md`](./dev-log/2026-05-13-sprint59-close.md)
- **13 active BL** (상세 = [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md) + [`refactoring-backlog/_archived.md`](./refactoring-backlog/_archived.md) + [`refactoring-backlog/_deferred.md`](./refactoring-backlog/_deferred.md))

### 직전 sprint: Sprint 58 (BL-241/242/243 Pine TA 확장)

- 상세: [`docs/dev-log/2026-05-11-sprint58-close.md`](./dev-log/2026-05-11-sprint58-close.md)

---

## 다음 분기 (Sprint 60)

dogfood Day 7 인터뷰 (2026-05-16, 사용자 manual) 결과 + 본인 의지 second gate 에 따라 4-way 분기:

- **(a)** NPS ≥7 + critical bug 0 + self-assess ≥7 + 본인 의지 → Sprint 60 = **Beta 본격 진입** (BL-070~075 도메인+DNS / BE 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)
- **(b)** dogfood mixed / no urgent bug → Sprint 60 = 잔여 active BL (BL-003 mainnet runbook / BL-014 partial fill / BL-022 golden / BL-235 N-dim viz / BL-236 objective whitelist)
- **(c)** mainnet trigger 도래 → Sprint 60 = BL-003 / BL-005 mainnet 본격
- **(d)** trust-breaking bug 노출 → Sprint 60 = 그 fix 1 sprint 우선, 후속은 Sprint 61+ 이연

### Sprint 60 첫 step 의무

- Day 7 카톡 인터뷰 결과 정리 (`sprint42-feedback.md` Day 7 row) + Sprint 59 evidence 검토 ([`dev-log/2026-05-13-sprint59-close.md`](./dev-log/2026-05-13-sprint59-close.md))
- 4-AND gate 검증: (a) self-assess ≥7 / (b) BL-178 production BH 정상 / (c) BL-180 hand oracle 8 test GREEN / (d) new P0=0 AND unresolved Sprint-59-caused P1=0
- **Sprint 50/51/52 `result_jsonb` retro-incorrect 안내 유지** — BL-222 fix 이전 CA / PS 결과는 사용자 manual 재실행 권고
- PR-E (5-split) 의 **5분 dev smoke** (LESSON-004 PR 규약, 사용자 manual) — 누락 시 회귀 의무 검증

---

## 상시 활성 컨텍스트 (영구 기록 외 발견 패턴)

- `dogfood Day N` 노트는 sprint 묶음과 별개로 `dev-log/` 에 단독 파일로 보관
- BL-005 (본인 1-2 주 dogfood) trigger 도래 후 H1→H2 gate (self-assessment ≥7) 가 재평가 기준
- `make up-isolated` (3100 / 8100 / 5433 / 6380) 가 다른 웹앱 병렬 시 디폴트
- **Pine SSOT 4 invariant audit** (`tests/strategy/pine_v2/test_ssot_invariants.py`) — supported list 추가 시 4 collection 동시 갱신 의무 자동 검증
- **Surface Trust sub-pillar (Sprint 30 ADR-019)** — Backend Reliability + Risk Management + Security + Surface Trust (가정박스 / 차트 / 24 metric / 거래목록). 측정: PRD 24 metric BE+FE 100% / config 5 가정 FE 100% / lightweight-charts 정합 / dogfood self-assess Day 3 ≥7
- **자율 병렬 sprint Agent worktree 패턴** — 충돌 회피 신규 파일 only / 통합 작업은 메인 세션 후처리 / gh CLI auto-merge --squash / `--no-verify` 1 회 우회 사용자 명시 승인 패턴

---

## 활성 BL 요약 (상세는 [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md))

> 본 sprint kickoff 시 백로그 review 의무. 자연어 표현은 컨텍스트 복원성 위해 sprint 회고 안에 유지하되, 새 항목 추가 시 BL ID 부여 후 등록.

핵심 cross-link (Sprint 59 PR-D 트리아주 후):

- **P0 active**: [BL-003](./REFACTORING-BACKLOG.md#bl-003) Bybit mainnet runbook
- **P1 active**: [BL-014](./REFACTORING-BACKLOG.md#bl-014) partial fill / [BL-015](./REFACTORING-BACKLOG.md#bl-015) OKX WS / [BL-022](./REFACTORING-BACKLOG.md#bl-022) golden 재생성 / [BL-023](./REFACTORING-BACKLOG.md#bl-023) KIND-B/C / [BL-024](./REFACTORING-BACKLOG.md#bl-024) real_broker E2E / [BL-025](./REFACTORING-BACKLOG.md#bl-025) autonomous-parallel patch / [BL-026](./REFACTORING-BACKLOG.md#bl-026) mutation fixture
- **P2 active**: [BL-186](./REFACTORING-BACKLOG.md#bl-186) full leverage model / [BL-190](./REFACTORING-BACKLOG.md#bl-190) PDF export / [BL-195](./REFACTORING-BACKLOG.md#bl-195) form animation / [BL-235](./REFACTORING-BACKLOG.md#bl-235) N-dim viz / [BL-236](./REFACTORING-BACKLOG.md#bl-236) objective whitelist
- **Deferred milestone** ([`_deferred.md`](./refactoring-backlog/_deferred.md)): BL-005 본인 dogfood / BL-070~075 Beta 본격 진입 / BL-145 EffectiveLeverageEvaluator
- **Archived 138건** ([`_archived.md`](./refactoring-backlog/_archived.md)): 모든 ✅ Resolved + Sprint 16~30 stale follow-up + P3 전부
- **정합성 audit:** [`04_architecture/architecture-conformance.md`](./04_architecture/architecture-conformance.md) — 15 항목 영구 체크리스트

---

## Test Skip / xfail 추적표 (Sprint 15-C 신설, 2026-04-28)

> 18 skip + 0 fail (Sprint 14 기준). "이 skip 이 왜 존재 + 언제 해소" 명시. 신규 skip 추가 시 본 표 업데이트 의무.

| #    | 위치                                                                                   | 종류                     | 사유                                                                                 | 해소 트리거                                                                  |
| ---- | -------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 1    | `tests/backtest/engine/test_golden_backtest.py:19`                                     | `pytestmark.skip`        | legacy golden expectations — pine_v2 `strategy.exit` 지원 + expected 재생성 필요     | pine_v2 strategy.exit 도입 후 golden 재생성                                  |
| 2    | `tests/real_broker/test_webhook_to_filled_e2e.py:31`                                   | `pytestmark.real_broker` | nightly E2E (Bybit Demo 실 호출). `--run-real-broker` flag + `BYBIT_DEMO_*` env 필요 | 매일 nightly cron (`.github/workflows/nightly-real-broker.yml`)              |
| 3    | `tests/real_broker/conftest.py:43`                                                     | `skip_marker`            | 위 #2 의 conftest fallback (env 미주입 시 collection-time skip)                      | 동일                                                                         |
| 4-7  | `tests/strategy/pine_v2/test_trust_layer_parity.py:251/334/357/421`                    | `skipif`                 | Trust Layer fixture (`regen_trust_layer_baseline.py` / 8 mutation set) 미생성        | Path β Stage 2c 2 차 mutation 8/8 도달 (2026-04-23 완료, 회귀로 활성화 검토) |
| 8    | `tests/strategy/pine_v2/test_trust_layer_parity.py:405`                                | `pytest.mark.skip`       | Mutation oracle 은 nightly workflow 또는 `--run-mutations` 수동 (CI default 차단)    | nightly mutation workflow 또는 manual gate                                   |
| 9-15 | `tests/strategy/pine_v2/test_mutation_oracle.py:147/179/212/253/296/328/376/414` (8건) | `skipif`                 | mutation fixture 미생성 시 collection skip                                           | Stage 2c 2 차 fixture 활성화 후 사용 가능 (현재 안전 fallback)               |
| 16   | `tests/strategy/pine_v2/test_mutation_oracle.py:213`                                   | `xfail(strict=False)`    | KIND=B/C 가 NaN-tolerance 한계로 mutation 구분 못 함. strict=False 로 명시           | KIND-B/C 분류 정밀도 향상 (Trust Layer v2 검토)                              |
| 17   | `tests/conftest.py:93`                                                                 | `skip_mutation` autouse  | 모든 `@pytest.mark.mutation` 자동 skip (CI default), `--run-mutations` 시 활성화     | pytest collection-time guard (영구)                                          |
| 18   | (집계 차이)                                                                            | xfail/skip 누적          | pytest collection-time 자동 분기 (real_broker / mutation 기본 차단)                  | 표 업데이트 의무                                                             |

**카테고리:**

- 영구 (정상): #2, #3, #8, #17 — opt-in flag 가 정확한 안전장치
- fixture 활성화 후 자동 해소: #4-7, #9-15 — Path β Stage 2c 2 차 후 회귀 검토 → [BL-026](./REFACTORING-BACKLOG.md#bl-026)
- dette: #1 (golden 재생성) → [BL-022](./REFACTORING-BACKLOG.md#bl-022) / #16 (KIND-B/C 정밀도) → [BL-023](./REFACTORING-BACKLOG.md#bl-023)

**관리 규약:** 신규 skip 추가 시 본 표 동일 PR 업데이트 / 매 sprint 끝 fixture 카테고리 재검토.

---

## Blocked

(현재 없음 — Sprint 58 종료)

---

## Questions

(없음 — 활성 질문 시 추가)

---

## Next Actions

- Sprint 59 진입 = Day 7 인터뷰 2026-05-16 결과 분석 후 결정
- Tier 1 refactor audit (현재 진행 중) → 사용자 승인 후 commit + PR
