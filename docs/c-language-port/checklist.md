<!-- C 디자인 언어 프로토타입 17벌을 React 로 이식하는 작업의 진행 체크리스트 -->

# C 언어 React 이식 — Checklist

> 계획 원본 `~/.claude/plans/quantbridge-c-kind-cray.md` · 결정 근거 [`context-notes.md`](./context-notes.md)
> 브랜치 `stage/c-language-port` (main `050ac64` 위) · 슬라이스 1개 = PR 1개, base 는 `stage/c-language-port`

---

## Phase 0 — 계획 (2026-07-20, 완료)

- [x] 핸드오프 + 프로젝트 규칙 4종 + `_KIT.md` + `terminology-ssot.md` 읽기
- [x] 베이스라인 실측 3종 병렬 (토큰/셸/반경 · P1 4화면 구조 · 테스트/CI)
- [x] 핸드오프 전제 독립 검증 — 색 불일치가 1건이 아니라 **5건**임을 실측으로 확인
- [x] 사용자 인터뷰 4Q → 스타일 아키텍처 / 라이트 테마 / nav-count / disabled nav 확정
- [x] 미해결 6건 처리 — 사용자 확정 2 + 계획 판단 4
- [x] 이식 계획 + 검증 게이트 배치 + React 검사 장치 설계
- [x] `checklist.md` + `context-notes.md` 생성 (본 문서)

---

## Phase 0.5 — 라이트 팔레트 확정 (2026-07-20, 완료)

> 핸드오프의 유일한 blocker 였다. 근거 전문 [`light-palette-trilemma.md`](./light-palette-trilemma.md)

- [x] 핸드오프 전제 재검증 — 감사표가 `--copper` 6.26(실측 7.53) · `--bull` 6.33(실측 9.99)로 과소 기재
- [x] ★A 안이 ② 를 만족하지 않음을 발견 — 채움 3색이 완전 등광도(상호 1.00)라 차트 범례가 구분 불가
- [x] A′ 안 도출 후 4안(A/A′/B1/B2) 프로토타입 생성 + 뷰어 등재
- [x] ★렌더 픽셀 실측 — 4안 최대 차이가 **0.61%**, 코크핏 A vs A′ 는 **픽셀 0개**
- [x] `design-taste-frontend` 적용 조항 채점 — B2 85점, §4.2 mandatory 가 A/A′ 를 실격
- [x] **B2 확정** — 채움 토큰 3개 제거 + 소비처 8곳 텍스트 토큰 환원
- [x] `td.num` 명시도 교정 (라이트 2벌) — 표의 손익 색 복구
- [x] 감사 블록 수치 전면 재계산 (치환 26건 단언 통과) · 기각안 6벌 삭제

**검증 게이트**

- [x] `runtime-check.mjs` 라이트 2/2 PASS · 다크 17/17 PASS (회귀 없음)
- [x] 브라우저 실측 — 채움 토큰 0개, 소비처 전부 텍스트 토큰, `td.num.pos/.neg` 색 복구, 콘솔 0
- [x] 대비 계산기를 공표 WCAG 기준값 6종으로 검증

---

## S0 — 검사 장치 + 캘리브레이션 (완료 2026-07-20)

> 안전망이 먼저다. 토큰 리네임을 안전망 없이 하면 `chart-tokens.ts` 가 **런타임 에러 없이 색만 틀리게** 조용히 깨진다.

**확정된 seam 5개** (2026-07-20 사용자 승인). 승인 안 된 seam 에는 테스트를 쓰지 않는다.

| #   | seam                                  | 상태                                                  |
| --- | ------------------------------------- | ----------------------------------------------------- |
| 1   | URL 의 렌더된 DOM (4폭)               | **완료** — `authed-canon-p1.spec.ts`                  |
| 2   | `resolveChartTokens()` 계약           | **완료**                                              |
| 3   | 커밋된 소스 텍스트 (반경·hex·em-dash) | **완료** — `design-canon-source.test`                 |
| 4   | 검사기가 스캔한 인벤토리 (위생 메타)  | 완료 (가드 3종에 동봉)                                |
| 5   | allowlist 래칫                        | 완료 (캐논 5 + 반경 21 + hex 6 + em 100 + P1 4라우트) |

**red→green 대체 절차.** S0 은 기존 동작의 안전망이라 테스트가 처음부터 GREEN 이다.
"red first" 에 해당하는 것은 **반증**이다 — 가드가 잡겠다는 결함을 주입해 FAIL 을 확인하고 되돌린다.
이 단계 없이는 아무것도 스캔하지 않는 가드가 통과하고 멀쩡해 보인다.

- [x] `src/__tests__/design-canon-tokens.test.ts` — 캐논 22종 대조 + 래칫 (반증 3/3)
- [x] `src/__tests__/chart-tokens-contract.test.ts` — read() 이름 ↔ 계약 ↔ globals.css (반증 2/2)
- [x] `e2e/design-canon-runtime.spec.ts` — 런타임 해석 검증 (반증 2/2)
- [x] playwright project `chromium-design-canon` + `pnpm e2e:design-canon`
- [x] 위생 메타테스트 — 블록 미검출 시 `Tests no tests` 로 시끄럽게 실패함을 반증으로 확인
- [x] `e2e/design-canon-audit.ts` — `runtime-check.mjs` 의 `AUDIT`/`MOTION_AUDIT`/포커스링/4폭 이식 (공유 모듈). `design-canon.spec.ts` 대신 모듈+캘리브레이션+앱 spec 3분할 (하이픈 없는 `.spec.ts` 는 testMatch 미매치라 이 이름이 필수)
- [x] 정적 검사 확장 — `design-canon-source.test.ts` (반경 21 · hex 6 · 노출 em-dash 100, 반증 4/4). 주석 인지 스캐너로 grep 거짓양성 차단
- [x] 공개 라우트 감사 — `design-canon-public.spec.ts` (CI). `/` 2(랜딩 대비 결함, S1a 해소) · `/waitlist` 0. code-review 후 추가
- [x] 고아 spec `sprint55-optimizer-bayesian.spec.ts` 배선→실행→**폼 UX stale 확인**→사용자 결정 `test.skip + TODO` (배선 되돌림, /optimizer 는 P1 밖)
- [x] **CI 배선** — `pnpm e2e:design-canon` 을 `ci.yml` e2e 잡에 (병행안). 캘리브레이션+런타임+public 27 passed

**검증 게이트**

- [x] ★캘리브레이션 — 프로토타입 17벌 + 라이트 2벌 = **22 passed**, canon 카운트 전부 기준선 일치 (재현 확인). 출력 기록 → [`s0-baseline.md`](./s0-baseline.md)
- [x] React 4라우트 baseline 측정 → allowlist 확정: dashboard 0 · backtests 1(375px overflow) · trades 3(포커스링) · trading 1(포커스가능 div)
- [x] `pnpm test` 그린 — 158파일 856테스트
- [x] `code-review` — Standards(하드 위반 0) + Spec 2축 병렬. Spec 지적 3건 반영: 공개라우트 CI 추가 · 출력 기록 · stale 참조 수정
- [~] `vercel-react-best-practices` — S0 은 React 런타임 코드 0(테스트/CI 만)이라 N/A. S1a(globals.css/컴포넌트)에서 적용

**S0 커밋** — `97941e6` 캘리브레이션 · `24fde4c` 정적 래칫 · `45d21d9` 고아 skip · `bcad78c` CI · `e8fc657` P1 baseline · `fefde1a` 공개라우트+리뷰대응 · `6ba6697` docs. main(`050ac64`) 대비 13 앞.

---

## S1a — 토큰 정합

- [x] `.dark` 색 5건 교정 — `globals.css:360` `:363` `:364` `:371` `:380`
- [x] `brand-palette.ts:45` `textMuted` 미러 갱신
- [x] 토큰 이름 13건 리네임
- [x] ★`chart-tokens.ts:60-69` 동반 수정 (누락 시 조용히 깨짐)
- [x] `--r: 12px` 도입
- [x] 하드코딩 hex — `app/layout.tsx:23,24` → `BRAND_PALETTE`, `app/icon.svg` `#2563eb` → 코퍼
- [x] 죽은 토큰 제거 — `--radius`(소비자 0) · `--radius-pill`(소비자 0) · `@theme inline` 중복 키 2건

**검증 게이트**

- [x] `chart-tokens.ts` 전용 회귀 테스트 — 10개 변수가 실제 해석되고 fallback 과 다른 값
- [x] `pnpm test` · `pnpm tsc --noEmit` · `pnpm build` 그린
- [x] `live-smoke` 그린 (이 워크플로는 `globals.css` 변경을 명시적 대상으로 삼는다)
- [x] allowlist 에서 `--text-muted` 대비 위반 제거 확인
- [x] `vercel-react-best-practices` + `code-review`

---

## S1b — Track A 슬롭 9종

- [x] ① `landing-faq.tsx:11` "100개 이상의 글로벌 거래소" → Bybit 단일
- [x] ② `step-4-result.tsx:67` `isError` 분기 신설
- [x] ③ 평가 상한 카피 `≤ 50회` → `최대 100회` (`optimizer-page-view.tsx:88-90`) + `genetic.py:19` docstring
- [x] ④ 노출 카피 em-dash (주석 치환 후 노출 마크업만. `"—"` 플레이스홀더 113건 일괄 치환 금지)
- [x] ⑤ "벡터화" 4곳 + 테스트 1곳
- [x] ⑥ 가짜 라이브 — `app/error.tsx:105-118` · `maintenance/page.tsx:29-37`
- [x] ⑦ 가짜 소셜프루프 — 이미 해결 (BL-270/271)
- [x] ⑧ `optimizer-run-list.tsx:89-98` genetic 분기 누락 (Best 열이 항상 `—`)
- [x] ⑨ `orders-panel.tsx:97-106` 헤더 한글화

**검증 게이트**

- [x] `pnpm test` 그린 (카피 assert 테스트 동반 수정)
- [x] 정적 가드 C1/C6 allowlist 가 0
- [x] `code-review`

---

## S2 — 공용 CSS 이식

- [x] `_kit.html` 24~997행 사이 **972줄**을 `globals.css` `@layer components` 로
- [x] 바이트 무결성 테스트 활성화

**검증 게이트**

- [x] 바이트 무결성 테스트 PASS
- [x] `pnpm build` 그린 · **시각 변화 0** (이 시점 소비자 0)
- [x] `live-smoke` 그린
- [x] `code-review`

---

## S3 — 셸 + 1024px 아이콘 레일

- [x] `ui-store.ts` 의 `sidebarOpen`/`toggleSidebar`/`setSidebarOpen` 삭제 (런타임 상수 `true`, 호출자 0)
- [x] `dashboard-header.tsx:14,15,19,28,29` 죽은 prop 2개 삭제
- [x] 1024px 레일을 **CSS 미디어쿼리로** (프로토타입도 JS 없이 CSS 로 한다)
- [x] nav 6개 정렬 + disabled 2개 제거
- [x] nav-count 3개 — 기존 `total` 재사용, 주문은 미체결 수임을 화면이 밝힌다
- [x] `dashboard-shell.tsx:13,44` 전체 스토어 구조분해 → 셀렉터

**검증 게이트**

- [x] design-canon 1024px — 모든 nav-item 접근 가능한 이름 + 가로 스크롤 0
- [x] 4폭(1440/1024/768/375) 전부 PASS
- [x] `components/layout/__tests__/` 갱신 후 그린
- [x] `design-taste-frontend` §9/§14 → `ui-ux-pro-max` → `vercel-react-best-practices` → `code-review`

---

## S4 — 용어 SSOT 모듈

- [x] `src/lib/labels.ts`
- [x] `src/features/backtest/labels.ts` · `src/features/trading/labels.ts`
- [x] 복제 Record 제거 — `status-badge.tsx:9-16` ↔ `backtest-list.tsx:30-37` (`queued` 가 `대기 중`/`대기` 로 갈림), `orders-blotter.tsx:33-42` `STATE_META` 이관

**검증 게이트**

- [x] `pnpm tsc --noEmit` 그린 (enum 추가 시 `Record` 누락이 타입 에러가 되는 배치인지 확인)
- [x] 원시 enum 노출 가드 테스트 신설
- [x] `code-review`

---

## S5 — `/backtests` (528줄)

> 가장 작고 self-contained. 유일한 서버 prefetch + HydrationBoundary 패턴을 여기서 확정한다.

- [x] 시맨틱 CSS 클래스 사용 패턴 확립 (이후 화면이 따른다)
- [x] prefetch 패턴 보존
- [x] `error.tsx` 신설
- [x] 상태 4종 실제 렌더

**검증 게이트** — design-canon 4폭 · 상태 4종 컴포넌트 테스트 · `pnpm e2e:authed` · allowlist 감소 · `design-taste-frontend` → `vercel-react-best-practices` → `code-review`

---

## S6 — `/backtests/[id]/trades` (1,107줄)

> 차트 없는 순수 표. 표·페이저·필터 프리미티브를 여기서 확립한다.

- [x] 표/페이저/필터 프리미티브 — `table.trades`/`.pager`·`.pg`(번호창+gap)/`.toolbar`·`.input`·`.select` 소비. 이후 표 화면이 따른다.
- [x] 중복 로딩 마크업 통합 — `page.tsx` Suspense fallback 과 shell isLoading 이 공유 `TradeDetailSkeleton`(`.sk`) 렌더
- [x] `error.tsx` — **신설 제외** (부모 `[id]/error.tsx` 82줄이 이미 덮는다)
- [x] 상태 4종 실제 렌더 — 스켈레톤/에러(`state-box.failed`)/빈(`state-box`)/데이터 + 컴포넌트 테스트 8종
- [x] S4 인계 — `{t.direction}` 원시 enum → `TRADE_DIRECTION_LABEL` 소비(표 셀·필터 옵션·펼침 상세)
- [x] 래칫 하강 — authed-canon-p1 `/backtests/:id/trades` allowlist 3 → 0 (검색·기간 입력이 공용 `.input` :focus-visible 링 소비). 실측 focus=0
- [x] 전 거래 로드 — `useAllBacktestTrades`(200-cap 해소)로 헤더 건수와 표 행 일치(정직성)

**검증 게이트** — S5 와 동일. 실측: vitest 877(+2)/tsc/lint/build 그린, design-canon 29, authed-canon-p1 5/5(trades 3→0), 4폭 overflow 0·console 0

---

## S7 — `/dashboard` (409줄, 4 feature slice 횡단)

- [x] 차트 경로 확립 (lightweight-charts)
- [x] 전략 카드 — 수명주기 상태 칩 **미렌더** (schemas.ts 에 대응 필드 0건)
- [x] `dashboard-cockpit.tsx:36` 크로스라우트 import 거취 판단
- [x] `error.tsx` 신설
- [x] 상태 4종 실제 렌더

**검증 게이트** — S5 공통 + 차트 축 설정 단위 테스트(`priceScale.mode` 비로그/비퍼센트, 포매터 배율 없음)

---

## S8 — `/trading` (4,269줄)

> 핸드오프의 2,494 는 `features/live-sessions` 1,543줄을 뺀 수다.

- [x] `features/trading` + `features/live-sessions` 양쪽 포함 — 코크핏이 두 도메인 훅·패널을 §01~§06 로 구성
- [x] 죽은 `kill-switch-modal.tsx` 177줄 + 그 테스트 삭제 — grep 0 소비자 재확인, em-dash 래칫 3건 감축
- [x] `error.tsx` 신설 — frontend.md §6 (use client + reset + state-box)
- [x] 상태 4종 실제 렌더 (에러 엔드포인트 = `GET /trading/sessions/{id}/positions · 503`) — SessionDiagnostics 4상태 프리미티브 + 패널 로딩/에러/빈/채움
- [x] ★S7 인계: KS 배너 재도입(코크핏 최상단) + LiveSessionTable → `features/live-sessions/components/` 이동(응집도)
- [x] ★S4 인계: `orders-panel.tsx` `{o.side}`·`{o.state}` → SSOT(`ORDER_SIDE_LABEL`/`statusLabelOf(ORDER_STATE_LABEL)`)
- [x] ★래칫: authed-canon-p1 `/trading` allowlist 1→0 (탭 제거로 outline-none 포커스가능 div 소멸, 실측 focus=0)
- [x] no-raw-enum 가드 스코프 유지(비확장) 그린

**검증 게이트** — S5 공통 + `ui-ux-pro-max` 2회차 ✅ (vitest 906·tsc·lint·build·design-canon 29·authed-canon-p1 5·4폭 실측·스킬 4종)

---

## S9 — 교차 정합 감사 + 잔여 정리 (완료 2026-07-21)

> 함정 #5. 프로토타입 17벌이 개별 통과 후 교차 감사에서 49건(BLOCKER 3)이 나왔다. React 에서는 **컴포넌트 경계**에서 같은 일이 일어난다.

- [x] 캐논 §4.1 원장 지정을 React 화면에 매핑해 교차 감사 — **사실 모순 0건**. 파생 `/dashboard` §03 은 원장 `/backtests` 와 같은 API `.total` 을 읽고 상태 라벨은 4화면 모두 S4 SSOT(BACKTEST/TRADE/ORDER)를 경유한다. nav-count 주문은 원장 전체(툴팁으로 미체결 아님을 명시)로 /trading §03 과 정합. 세션 수(활성/총)도 동일 소스. 유일한 잔여 = live-session-detail/list 의 `toLocaleString` 날짜 포맷(형식 불일치, §05 미이식 층 3e 이연).
- [x] 무력 `min()` 클램프 제거 — `button.tsx`(xs/sm/icon-xs/icon-sm) · `select.tsx`(sm) → `rounded-md`(=--radius-md 6px, 클램프가 항상 var 값). `badge.tsx` `rounded-[4px]`→`rounded-sm`.
- [x] 잔여 반경 재실측 후 정리 — 공용 층(badge)만 정리. **P1 4라우트+셸 마크업엔 반경 리터럴 0건**(전부 시맨틱 CSS 소비). 나머지 반경/stale var() 폴백은 전부 P1 밖(waitlist·share·error·maintenance·onboarding·strategies) = 공유 프리미티브 규칙상 이연(remaining 참조). tape `rounded-[1px]` 3건은 의도(불가침 pnl-tape 정합).
- [x] 503 orphan 삭제(3d) · 크로스페이지 프리미티브 StateBox/InfoIcon 추출(3a) · raw-enum 가드 확장 + live-session-detail `{ev.status}` SSOT 이관(3b) · live-session-form em-dash 2건 교정(3c).
- [x] allowlist 확인 — authed-canon-p1 4라우트 HARDFAIL 0 유지 · design-canon-tokens KNOWN_MISMATCHES 0 · design-canon-source 래칫 3종 감축(radius badge 제거·error-recovery 4→2 · em-dash live-session-form 제거).

**검증 게이트 (2026-07-21 실측)**

- [x] `pnpm test --run` — 164 files / **905 tests** (baseline 906 − 삭제된 503 variant 테스트 1)
- [x] `pnpm tsc --noEmit` 클린 · `pnpm lint` 클린 · `pnpm build`(임시 distDir → 원복) 성공
- [x] `chromium-design-canon` **29 passed** · `chromium-authed authed-canon-p1` **5 passed** (4 P1 라우트 하드 실패 0)

---

## 잔여 완주 세션 (2026-07-21 착수) — 브랜치 `stage/c-port-remaining`

> 계획 `~/.claude/plans/c-react-greedy-stardust.md` · 운영 계약 [`operating-contract.md`](./operating-contract.md)
> 게이트 3분류 ⓐⓑⓒ + 스킬 게이트 + 오케스트레이터 직렬 재현. baseline: vitest 164/904 · canon 29 · authed 5.

- [ ] W0 — 브랜치 + 운영 계약 커밋 + 환경 복구(stale CSS 재컴파일) + fixture 시딩(optimizer 완료 run) + codex 플랜 검증
- [x] W1 — 용어 SSOT 확장 완료 (`af9eb2d`~`67e2893`). labels 2모듈(§4-3/§4-5 전문) + §5-3/5-4/5-5 이관 + 가드 5필드·템플릿보간·6스코프 확장. ★반증이 가드 위양성(`=>` 를 태그닫힘 오인) 발견→교정, 스코프 확장이 §5 미기재 원시 렌더 6곳 표면화(차트·리더보드 5벌 + live-session-detail 방향)→이관, `LIVE_SIGNAL_DIRECTION_LABEL` 신설(backend models.py long|short 실측 근거). 오케스트레이터 재현: vitest 164/**907**·tsc 0·lint 0·가드+래칫 16/16
- [x] W2 — variant-c → `/backtests/[id]` 완료 (`67d56e3`·`d112b26`). 번호 섹션 01~10 IA, recharts/lwc 불변, authed-canon-remaining 신설(완료행 선택+expect FAIL+렌더 대기), 공선성 검사는 반증(ResponsiveContainer+jsdom 폭0 = 비결정)으로 기각→축 설정 단위 테스트 갈음. KPI 미터 미렌더(§4.9 — 상한이 프로토 임의값). 재현: authed `/backtests/:id` 하드 0 (첫 실측 contrast=4 는 stale CSS — r 주석 무효화 루틴으로 해소)
- [x] W3-A — screen-05 → `/backtests/new` 완료 (`2bcd0e1` cherry-pick). 가짜 라이브 배지·ETA/수수료 휴리스틱 제거(unbacked ETA 검증 테스트 2건 삭제 명시), em-dash 래칫 -3항목
- [x] W3-B — 전략 3벌 완료 (`17a727d`~`caf7472` cherry-pick, 구 위저드/필터바 18파일 삭제 — **테스트 순감 918→884, 삭제 목록 PR 본문 명시 의무**). backtest_count·수명주기·성과 3칸 미렌더(§4.9). ★globals 주석 `.trust-*/` 조기 종결 → CSS 파스 전면 500 — 통합 게이트가 검출·픽스. 재현: /strategies·/new·/:id/edit 하드 0
- [x] W3-C — 옵티마이저 2벌 완료 (`e02ec72`~`3fa9662` cherry-pick). §4.5 상한 칩·무데이터 문구·backed-only(조인 부제·가짜 cap 미터 미렌더), OOS 실API 재스킨 유지. 재현: /optimizer·/optimizer/:id 하드 0. ★sprint55 spec 은 라이브에서 mock 라우트 미매치로 FAIL → FIX-4
- [x] W3-D — `/orders` 완료 (`e112052`→`f21335f`). §4.6 규약 전이식 + tablist→role=group + 정직 미렌더 5건(브로커/모의 배지·취소 열 — 스키마/API unbacked)
- [x] W3-E — `/onboarding` 완료 (`c1b0a24`→`4698e50`). radius 래칫 -1(option-card-radio)
- [x] W3-F — live-sessions 부채 완료 (`653699a`~`fc7e6fe`). §05 재스킨 + 결정적 날짜 + kpi-pnl isError(StatValue) + ★OKX FE 제거(테스트 교체 포함, codex#6) + orders-panel 청산가 열 제거
- [x] W3-G — 마케팅 4벌 완료 (net-diff squash `64634d4` — 중간 prettier 재포맷 사고 커밋 배제). `/pricing` 신설+public/live-smoke 편입, Beta 배너 한국어 재스킨(em-dash 해소), 래칫 radius -3·em-dash -4. sign-in 은 Clerk 외부 로드 사유로 public 감사 제외(주석 문서화, 시각 게이트는 오케스트레이터 육안)
- [x] W3-H — 에러 3종 완료 (`25f4889`~`a11854d` cherry-pick). 구 error-\* 컴포넌트 삭제(소비자 0 전수 확인), radius 래칫 -5, /maintenance+404 공개 캐논 편입. 재현: canon 29→31

**FIX 목록 (게이트 통과분의 프로토타입 충실도 갭 — 별도 픽스 슬라이스)**

1. screen-06 필터 행(검색·심볼·정렬 — 전부 backed, 클라이언트 필터 가능) + CSV 내보내기 미렌더 → 재도입
2. screen-07 04 진단 섹션(지원 함수 사전 카드·저장된 초안 카드 — backed) + 파일 열기/예제 버튼 → 재도입 검토
3. screen-10 파라미터 안정성 섹션(cells 파생 가능 — unbacked 아님) 미이식 → 이식
4. sprint55-optimizer-bayesian spec 라이브 그린화 — mock 라우트가 실제 크로스오리진(8000) 요청과 미매치 → 실백엔드 거부 alert. 제품 결함 아님
5. (교차 감사 사용자 노출) W2 KPI 미터 미렌더 결정 · 상단 Beta 배너(영문+em-dash) 처리 · 히트맵 기본 접힘

- [x] W-final — 완료. 부채 마감(`e04bf57`~`665f4b3`: StateBox 9파일 13곳 전량 이관·이중 링 sweep 7파일·반경 판정) + 감사기 픽스 2종(`225f83e` WCAG 1.4.3 비활성 예외 hard 축만 · `3b02f03` 대비 샘플링 reduced-motion 정지 상태 — .rise 스태거 knife-edge 제거, 캘리브레이션 22 동등 유지) + 교차 감사 8건 처분(7픽스 `eb65ed2`~`07a6613` + nav-count 기결) + codex 최종 8건 처분(7픽스 `f3b52cc`~`af9e284` + labels 미소비 export 기각=문서 전문 정책) + 레거시 authed 스펙 수리(`81fa8e4`~`b449338` — 8스펙 재작성, KS resolve un-skip, 앱 결함 0)

**최종 게이트 실측 (2026-07-21, 오케스트레이터 직렬 재현)**

- vitest **169파일/963** · tsc 0 · lint 0 · **build 0**(임시 distDir→원복) · design-canon **32**(캘리브레이션 22 동등) · **e2e:authed 전체 56 passed / 0 failed / 0 skipped**(캐논 17 + 레거시 수리분 포함) · live-smoke(+pricing) 그린 · kit-port 무결성 유지
- 잔여 관측: hand-rolled state-box 3건(trade-ledger-table·parse-result-panel·new-strategy-wizard — 시각 동일, 일관성 부채) · backtest-history-card = dead(삭제는 후속 판단) · KPI 미터 미렌더 결정(사용자 노출 대상)

**Coverage 매트릭스 (codex#3 — 슬라이스마다 이 표로 단조 증가 추적)**

| 라우트                          | spec                                                                                        | 소유 | 축   |
| ------------------------------- | ------------------------------------------------------------------------------------------- | ---- | ---- |
| /backtests/[id] 완료 리포트     | `authed-canon-remaining.spec.ts` **신설**(+testMatch, 완료행 선택·fixture expect·렌더 대기) | W2   | 로컬 |
| /backtests/new                  | authed-canon-remaining                                                                      | W3-A | 로컬 |
| /strategies · /new · /[id]/edit | authed-canon-remaining (+3)                                                                 | W3-B | 로컬 |
| /optimizer · /[id](완료)        | authed-canon-remaining (+2)                                                                 | W3-C | 로컬 |
| /orders                         | authed-canon-remaining                                                                      | W3-D | 로컬 |
| /onboarding                     | authed-canon-remaining                                                                      | W3-E | 로컬 |
| /pricing                        | design-canon-public + live-smoke                                                            | W3-G | CI   |
| /sign-in                        | design-canon-public (Clerk 불안정 시 remaining 이관+사유)                                   | W3-G | CI   |
| /maintenance · 404              | design-canon-public (+2)                                                                    | W3-H | CI   |

기대 passed: canon **29→33** · authed **5→14**. 조 소유권 교정(codex#1): G = landing-_ + page.tsx + waitlist + pricing + (auth) / H = 루트 에러 3종 + `app/\_components/error-_` + 그 테스트.

## Blocked

(현재 없음)

## Questions

(2026-07-21 해소) `strategy.backtest_count` = **열 미렌더** 확정 · OKX = **FE 등록 폼에서 제거** 확정 (계정 0·주문 0 실측). 근거는 context-notes 잔여 세션 절.
