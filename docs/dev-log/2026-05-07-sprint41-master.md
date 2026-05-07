# Sprint 41 Master Retrospective — 외부 demo 첫인상 패키지 (B+E+H+B-2 통합 4 PR) + Day 7 = 8/10 PASS

**기간**: 2026-05-07 (single day, wall-clock ~3h 메인 세션 + ~50분 자율 병렬 cmux)
**브랜치**: main `feecf56` → **`6d6a836`** (PR #181 squash, +2615/-166/40 files)
**활성 sprint type**: 외부 demo 첫인상 패키지 (디자인 + UX + share). 자율 병렬 cmux 5번째 실측.
**self-assessment Day 7**: **8/10 (a) PASS** — Playwright 자동 검증 10/10 + codex P2 2건 즉시 fix + Day 7 4중 AND PASS
**다음 분기**: Sprint 42 = **지인 N=5 demo 오픈 + feedback loop** (Beta 본격 진입 BL-070~075 trigger 는 N=5 + 1-2주 사용 후 별도 결정)

---

## 1. Context — 왜 Sprint 41 가 필요했나

Sprint 40 = stage→main merge + BL-003 / BL-005 본격 trigger 였으나 사용자 방향 전환 (2026-05-07): **mainnet 보류 → demo trading 으로 지인 N=5 오픈 prereq** 가 다음 목표. mainnet 본격 (BL-003 / BL-005) 은 demo dogfood feedback 후 재평가.

Sprint 41 = 외부 사용자 첫 5분 가치 확보. 3 worker 자율 병렬 (Sprint 38 cmux 4 worker 패턴 검증) + 사용자 dogfood 중 발견된 갭 1건 후속 spawn (B-2):

| Wave | Worker | Track                                              | 결과         |
| ---- | ------ | -------------------------------------------------- | ------------ |
| 1    | B      | 디자인 시스템 일관 적용                            | PR #177 머지 |
| 1    | E      | 빈상태/Skeleton/422 inline 통일                    | PR #178 머지 |
| 1    | H      | 백테스트 share link (PDF P1 deferral)              | PR #179 머지 |
| 2    | B-2    | 프로토타입 기반 App Shell + 4 페이지 visual layout | PR #180 머지 |

**Wave 2 추가 정당화**: dogfood 시점에 사용자가 "기존이랑 달라진게 없는것 같다 + `docs/prototypes/` 12 HTML 활용" 보고 → 첫 prereq 답변 ("DESIGN.md 기반 polish") 시점에 prototypes 가 인지 안 됨이 root cause. B 산출 (token 정합 + radius 4px 미세 조정) 은 시각 변화 미미 → B-2 가 진짜 visual 변화 추가.

---

## 2. 산출물 (4 PR / +2615 / -166 / 40 files)

### Wave 1 (B/E/H, 22분 자율)

#### PR #177 (B) — 디자인 시스템 일관 적용

- 신규: `frontend/src/lib/design-tokens.ts` (DESIGN.md 토큰 TS export)
- 보강: `frontend/src/styles/globals.css` `@theme inline` 매핑 7건 + dash sidebar 토큰 5건
- shadcn ui 4개 radius 표준화 (button 14→10px / input 14→6px / card 18→14px / badge → full pill)
- typography hierarchy (strategy-list / backtest-list `<h1>` / `<p>` 정합)
- codex review = 1 P2 즉시 fix (commit `6024fa0`, secondary 컬러 정합)

#### PR #178 (E) — 빈상태 / Skeleton / 422 inline 통일

- 신규: `frontend/src/components/{empty-state,skeleton,form-error-inline}.tsx` 3건
- /backtests 0건 시 EmptyState 카드 + CTA, /backtests/new FormSkeleton, /trading TableSkeleton
- backtest-form 의 friendly_message + unsupported_builtins 패턴을 FormErrorInline 으로 추출
- 신규 unit tests +10건 (empty-state 3 / skeleton 3 / form-error-inline 4)
- codex review 1-pass PASS

#### PR #179 (H) — 백테스트 share link (PDF P1 deferral)

- alembic migration `20260507_0001_add_backtest_share_token.py` (share_token / share_revoked_at)
- BE: `backtest/{models,exceptions,schemas,repository,service,router}.py` 갱신
- 신규 endpoint 3 — POST `/backtests/{id}/share` (idempotent) / DELETE `/backtests/{id}/share` (revoke) / GET `/backtests/share/{token}` (public, no auth)
- FE: `/share/backtests/[token]/page.tsx` (public read-only) + `opengraph-image.tsx` (Next.js 16 ImageResponse 1200×630) + `share-button.tsx` (clipboard + revoke)
- `proxy.ts` (Next.js 16 middleware) — `/share/backtests/(.*)` publicRoute + geoExempt
- 신규 tests +11건 (BE 6 / FE 5)
- 보안: `secrets.token_urlsafe(32)` 256-bit / 응답 error strip / 410 / 404 / 401 분기 정확
- codex review = 1 P2 즉시 fix (commit `708fd1c`, **share create race condition** SELECT FOR UPDATE row lock + 동시성 unit test +1)

### Wave 2 (B-2, 12분 자율 + 3분 fix)

#### PR #180 (B-2) — 프로토타입 기반 App Shell + 4 페이지 visual layout

- `frontend/src/components/layout/dashboard-shell.tsx` 재구성 — sidebar 220px (fixed left) + header 60-64px (sticky top) + page title slot + footer dock + `data-theme="dash"` 자동 토글 (`pathname.startsWith("/trading")` 파생값, effect 없음)
- `/backtests` KPI 4 카드 strip (총/완료/실행중/실패) + status 필터 chip (전체·완료·실행중·대기·실패·취소) + URL `?status=` 동기화 + 테이블 polish
- `/trading` Full Dark App Shell + 신규 `trading-dash-hero.tsx` KPI 4 카드
- /strategies / /backtests/[id] = 변경 X (기존 layout 이 이미 정합)
- 신규 tests +6건 (dashboard-shell 5 / backtest-list-filter 1)
- BE schema 우선 — 프로토타입과 다른 필드 (`BacktestSummary` metrics 미포함 등) 는 BE 따라감
- codex review = 1 P2 즉시 fix (commit `601b7d4e`, **client-side status filter chip 비활성+안내** when hasMore — 20+ backtest 사용자 잘못된 빈 결과 차단)

---

## 3. 회귀 / 검증

| 항목                          | baseline (main feecf56)             | stage (a1dfc82)                                                         | 변동                                                  |
| ----------------------------- | ----------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------- |
| BE pytest                     | 1679 PASS / 42 skip / 0 fail / 197s | **1686 PASS** / 42 skip / 0 fail / 264s                                 | +7 신규                                               |
| FE vitest                     | 431 PASS / 69 files / 8.8s          | **457 PASS** / 74 files / 10.2s                                         | +26 신규 (E +10 / H +11 / B-2 +6 / 회귀 -1 모듈 분할) |
| ruff / mypy / pnpm lint / tsc | 0 errors                            | 0 errors                                                                | 무변경                                                |
| idle CPU (LESSON-046)         | < 10%                               | beat 0% / ws-stream 0.2~0.3% / worker 0.3% / redis 0.8~2.6% / db 0~2.4% | 모든 컨테이너 < 3% (12+ 시간 stable)                  |

### Playwright 자동 검증 (10/10 PASS)

| #   | 항목                                                                                                                | 결과                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| 1   | App Shell sidebar 220px / header 64px / next/font 3 / 네비 4                                                        | ✅                                                     |
| 2   | /strategies h1 "내 전략" light theme                                                                                | ✅                                                     |
| 3   | /backtests h1 "백테스트" + KPI 4 (3/3/0/0) + 필터 chip 6 + 테이블 3 row                                             | ✅                                                     |
| 4   | /backtests/{id} 공유/재실행 + 탭 5 + 가정박스 + equity curve                                                        | ✅                                                     |
| 5   | /trading dash wrapper #0B1120 viewport cover (sidebar+body+foreground 모두 dark)                                    | ✅                                                     |
| 6   | /share/INVALID 404 안내 + CTA                                                                                       | ✅                                                     |
| 7   | /share/INVALID/opengraph-image 200 image/png 49.7KB                                                                 | ✅                                                     |
| 8   | BE GET share/INVALID 404 backtest_not_found / POST share noauth 401 auth_invalid_token                              | ✅                                                     |
| 9   | **Share full flow** POST 200 → GET 200 metrics → POST 멱등 same token → DELETE 204 → GET 410 backtest_share_revoked | ✅ Worker H race fix 효과                              |
| 10  | Worker B-2 trading dash scope (sidebar + body + foreground)                                                         | ✅ (P1 false alarm 정정 — wrapper rect viewport cover) |

### 사용자 manual dogfood (사용자 OK 회신)

clipboard 자동 복사 + toast / og:image 시각 / 모바일 viewport sidebar 토글 / FormSkeleton / TableSkeleton / form 422 inline error card — 사용자 진행 + "응 진행해도 될것 같아" 회신.

---

## 4. Day 7 4중 AND gate 결과 (영구 기준)

| Gate                                               | 결과          | 근거                                                                                                                          |
| -------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **(a)** self-assess ≥ 7/10 + 근거 ≥ 3              | **8/10 PASS** | 자율 병렬 cmux 5번째 실측 wall-clock ≈ 50분 / 회귀 0 / codex P2 2건 즉시 fix / Playwright 10/10 PASS / 4 트랙 fully delivered |
| **(b)** BL-178 BH curve                            | PASS          | main 변경 X (Sprint 41 시작 시점 baseline `feecf56` 그대로, BL-178 production curve 무수정)                                   |
| **(c)** BL-180 hand oracle 8                       | PASS          | main 변경 X (`tests/strategy/pine_v2/test_hand_oracle.py` 무수정)                                                             |
| **(d)** new P0=0 AND unresolved Sprint-caused P1=0 | PASS          | new P0 0 / Sprint-caused P1 0 (codex P2 2건 모두 즉시 fix 머지)                                                               |

**근거 3줄 (a)**:

1. **자율 병렬 cmux 5번째 실측**: 4 worker (B/E/H + B-2) → 4 PR pr_ready / 4 PR squash 머지. 사용자 interaction 4회 ("ok" 1 + race fix 결정 1 + filter fix 결정 1 + main merge 승인 1) — Sprint 38 4 worker 패턴 (3회) 보다 1회 증가하나 race + filter 2건 즉시 fix 의 결과.
2. **codex G.4 P1 review 4 PR 모두 PASS** — P0/P1 0건. P2 2건 (Worker H share race / B-2 client filter) **모두 워커 자체 또는 메인 세션 cmux send 로 5-15분 내 fix + stage 머지** → close-out 시점 Sprint-caused P1/P2 unresolved 0건.
3. **Playwright 자동 검증 10/10 PASS** — App Shell sidebar 220px / Full Dark wrapper viewport cover / share full flow (POST → GET 200 → POST 멱등 same token → DELETE 204 → GET 410) / og:image 200 image/png 49.7KB / 404·401 분기 정확. 사용자 manual dogfood 도 OK 회신.

---

## 5. 신규 BL 등록 (3건)

| BL                                       | 우선순위          | trigger                                | 비고                                                                                                                                                                  |
| ---------------------------------------- | ----------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **BL-190** PDF export                    | P1 deferrable     | 외부 사용자 요청 OR 인쇄 use case 발견 | jsPDF + html2canvas client-side 또는 Playwright server-side. share link 충분 결정 (사용자 prereq) → Sprint 41 미구현                                                  |
| **BL-191** share view rate-limit         | P1 (Beta 진입 시) | Beta 본격 오픈 (BL-070~075)            | abuse 방지. 익명 endpoint `/api/v1/backtests/share/{token}` 가 token 추정 brute-force 가능 (256-bit 엔트로피라 실질 risk 낮으나 IP 단위 throttle 권장)                |
| **BL-192** backtest status server filter | P2                | Beta 진입 시 (BL-070~075)              | B-2 의 client-side filter 제약 (20+ backtest 사용자) 해소. BE API status param 추가 + FE chip → server query 변경. 현재 hasMore 시 chip 비활성+안내 차단 패턴 적용 중 |

---

## 6. LESSON 신규 후보 (3건, `.ai/project/lessons.md` gitignored)

- **LESSON-048 후보 1/3**: **Playwright MCP + 인증 cookie 활용 자동 dogfood** — 메인 세션 browser 가 사용자 Clerk cookie 보유 시 인증 필요 페이지 자동 검증 가능. 본 sprint 에서 10/10 자동 검증 (App Shell / Full Dark / share full flow / og:image) → manual dogfood 시간 1/3 단축 + 회귀 결정성 확보. 일관 적용 시 LESSON 승격.
- **LESSON-049 후보 1/3**: **codex G.4 P1 P2 즉시 fix 패턴** — worker pr_ready 후 codex review P2 발견 시 (a) cmux send 로 worker 자체 iter +1 또는 (b) 메인 세션이 worktree 에서 직접 push (worker session stuck 시) 모두 LESSON-035 worker isolation 의 "branch swap 금지" 와 양립 가능. 본 sprint H race condition / B-2 status filter 2건 모두 5-15분 내 fix + stage 머지 검증.
- **LESSON-050 후보 1/3**: **Sprint kickoff 시 사용자 prereq 답변에 design source 명시 의무** — Sprint 41 의 첫 prereq 답변 ("DESIGN.md 기반 polish") 시점에 `docs/prototypes/` 12 HTML 가 인지 안 됨 → Worker B 가 token 정합 미세 조정만 → 사용자 dogfood 인지 X → Wave 2 (B-2) 추가 spawn 발생. 다음 sprint 부터 디자인 트랙 prereq 질문에 "디자인 source = \_\_\_ (DESIGN.md / 프로토타입 디렉토리 / Figma / .pen / 없음)" 4지선다 명시.

---

## 7. Sprint 42 분기 결정

**활성 sprint type**: 지인 N=5 demo 오픈 + feedback loop (Beta 본격 진입 trigger 는 별도)

**Sprint 42 mandatory**:

- 지인 N=5 demo 오픈 (사용자 본인 + 1차 N=5 ≈ 5명)
- feedback 수집 채널 setup (간단한 폼 또는 직접 인터뷰)
- 1-2주 dogfood 결과 → Beta 본격 진입 (BL-070~075) trigger 결정

**Sprint 42 prompt**: `<repo>/.claude/plans/sprint42-demo-friend-open-prompt.md` (별도 파일 — close-out 단계에서 작성)

**Beta 본격 진입 trigger**:

- ≥ N=5 사용자 1-2주 dogfood 통과 + critical bug 0건 + 사용자 NPS ≥ 7
- BL-003 / BL-005 mainnet 은 demo dogfood 후 별도 trigger (사용자 결정 = mainnet 본격 진입은 demo 통과 후)
