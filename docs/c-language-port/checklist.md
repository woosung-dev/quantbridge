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

## S0 — 검사 장치 + 캘리브레이션

> 안전망이 먼저다. 토큰 리네임을 안전망 없이 하면 `chart-tokens.ts` 가 **런타임 에러 없이 색만 틀리게** 조용히 깨진다.

- [ ] `frontend/e2e/design-canon.spec.ts` — `runtime-check.mjs` 의 `AUDIT`/`MOTION_AUDIT` 를 그대로 이식
- [ ] `frontend/src/__tests__/design-canon.test.ts` — `no-internal-ids.test.ts` 템플릿으로 정적 검사
- [ ] 위생 메타테스트 2종 (인벤토리 파일 수 범위 + P1 4라우트 명시 포함)
- [ ] allowlist ratchet 구조 (알려진 위반 고정, 슬라이스마다 축소)
- [ ] 고아 spec `e2e/sprint55-optimizer-bayesian.spec.ts` 처리 (어느 `testMatch` 에도 안 걸려 한 번도 실행된 적 없음)

**검증 게이트**

- [ ] ★캘리브레이션 — 새 spec 을 **프로토타입 17벌에 먼저** 돌려 17/17 PASS 재현. 출력 그대로 기록
- [ ] React 4라우트 baseline 측정 → allowlist 초기값 확정
- [ ] `pnpm test` 그린
- [ ] `vercel-react-best-practices` + `code-review`

---

## S1a — 토큰 정합

- [ ] `.dark` 색 5건 교정 — `globals.css:360` `:363` `:364` `:371` `:380`
- [ ] `brand-palette.ts:45` `textMuted` 미러 갱신
- [ ] 토큰 이름 13건 리네임
- [ ] ★`chart-tokens.ts:60-69` 동반 수정 (누락 시 조용히 깨짐)
- [ ] `--r: 12px` 도입
- [ ] 하드코딩 hex — `app/layout.tsx:23,24` → `BRAND_PALETTE`, `app/icon.svg` `#2563eb` → 코퍼
- [ ] 죽은 토큰 제거 — `--radius`(소비자 0) · `--radius-pill`(소비자 0) · `@theme inline` 중복 키 2건

**검증 게이트**

- [ ] `chart-tokens.ts` 전용 회귀 테스트 — 10개 변수가 실제 해석되고 fallback 과 다른 값
- [ ] `pnpm test` · `pnpm tsc --noEmit` · `pnpm build` 그린
- [ ] `live-smoke` 그린 (이 워크플로는 `globals.css` 변경을 명시적 대상으로 삼는다)
- [ ] allowlist 에서 `--text-muted` 대비 위반 제거 확인
- [ ] `vercel-react-best-practices` + `code-review`

---

## S1b — Track A 슬롭 9종

- [ ] ① `landing-faq.tsx:11` "100개 이상의 글로벌 거래소" → Bybit 단일
- [ ] ② `step-4-result.tsx:67` `isError` 분기 신설
- [ ] ③ 평가 상한 카피 `≤ 50회` → `최대 100회` (`optimizer-page-view.tsx:88-90`) + `genetic.py:19` docstring
- [ ] ④ 노출 카피 em-dash (주석 치환 후 노출 마크업만. `"—"` 플레이스홀더 113건 일괄 치환 금지)
- [ ] ⑤ "벡터화" 4곳 + 테스트 1곳
- [ ] ⑥ 가짜 라이브 — `app/error.tsx:105-118` · `maintenance/page.tsx:29-37`
- [x] ⑦ 가짜 소셜프루프 — 이미 해결 (BL-270/271)
- [ ] ⑧ `optimizer-run-list.tsx:89-98` genetic 분기 누락 (Best 열이 항상 `—`)
- [ ] ⑨ `orders-panel.tsx:97-106` 헤더 한글화

**검증 게이트**

- [ ] `pnpm test` 그린 (카피 assert 테스트 동반 수정)
- [ ] 정적 가드 C1/C6 allowlist 가 0
- [ ] `code-review`

---

## S2 — 공용 CSS 이식

- [ ] `_kit.html` 24~997행 사이 **972줄**을 `globals.css` `@layer components` 로
- [ ] 바이트 무결성 테스트 활성화

**검증 게이트**

- [ ] 바이트 무결성 테스트 PASS
- [ ] `pnpm build` 그린 · **시각 변화 0** (이 시점 소비자 0)
- [ ] `live-smoke` 그린
- [ ] `code-review`

---

## S3 — 셸 + 1024px 아이콘 레일

- [ ] `ui-store.ts` 의 `sidebarOpen`/`toggleSidebar`/`setSidebarOpen` 삭제 (런타임 상수 `true`, 호출자 0)
- [ ] `dashboard-header.tsx:14,15,19,28,29` 죽은 prop 2개 삭제
- [ ] 1024px 레일을 **CSS 미디어쿼리로** (프로토타입도 JS 없이 CSS 로 한다)
- [ ] nav 6개 정렬 + disabled 2개 제거
- [ ] nav-count 3개 — 기존 `total` 재사용, 주문은 미체결 수임을 화면이 밝힌다
- [ ] `dashboard-shell.tsx:13,44` 전체 스토어 구조분해 → 셀렉터

**검증 게이트**

- [ ] design-canon 1024px — 모든 nav-item 접근 가능한 이름 + 가로 스크롤 0
- [ ] 4폭(1440/1024/768/375) 전부 PASS
- [ ] `components/layout/__tests__/` 갱신 후 그린
- [ ] `design-taste-frontend` §9/§14 → `ui-ux-pro-max` → `vercel-react-best-practices` → `code-review`

---

## S4 — 용어 SSOT 모듈

- [ ] `src/lib/labels.ts`
- [ ] `src/features/backtest/labels.ts` · `src/features/trading/labels.ts`
- [ ] 복제 Record 제거 — `status-badge.tsx:9-16` ↔ `backtest-list.tsx:30-37` (`queued` 가 `대기 중`/`대기` 로 갈림), `orders-blotter.tsx:33-42` `STATE_META` 이관

**검증 게이트**

- [ ] `pnpm tsc --noEmit` 그린 (enum 추가 시 `Record` 누락이 타입 에러가 되는 배치인지 확인)
- [ ] 원시 enum 노출 가드 테스트 신설
- [ ] `code-review`

---

## S5 — `/backtests` (528줄)

> 가장 작고 self-contained. 유일한 서버 prefetch + HydrationBoundary 패턴을 여기서 확정한다.

- [ ] 시맨틱 CSS 클래스 사용 패턴 확립 (이후 화면이 따른다)
- [ ] prefetch 패턴 보존
- [ ] `error.tsx` 신설
- [ ] 상태 4종 실제 렌더

**검증 게이트** — design-canon 4폭 · 상태 4종 컴포넌트 테스트 · `pnpm e2e:authed` · allowlist 감소 · `design-taste-frontend` → `vercel-react-best-practices` → `code-review`

---

## S6 — `/backtests/[id]/trades` (1,107줄)

> 차트 없는 순수 표. 표·페이저·필터 프리미티브를 여기서 확립한다.

- [ ] 표/페이저/필터 프리미티브
- [ ] 중복 로딩 마크업 통합 — `page.tsx:28-34` 와 `trade-detail-shell.tsx:31-35` 가 같은 `<p>불러오는 중…</p>`
- [ ] `error.tsx` — **신설 제외** (부모 `[id]/error.tsx` 82줄이 이미 덮는다)
- [ ] 상태 4종 실제 렌더

**검증 게이트** — S5 와 동일

---

## S7 — `/dashboard` (409줄, 4 feature slice 횡단)

- [ ] 차트 경로 확립 (lightweight-charts)
- [ ] 전략 카드 — 수명주기 상태 칩 **미렌더** (schemas.ts 에 대응 필드 0건)
- [ ] `dashboard-cockpit.tsx:36` 크로스라우트 import 거취 판단
- [ ] `error.tsx` 신설
- [ ] 상태 4종 실제 렌더

**검증 게이트** — S5 공통 + 차트 축 설정 단위 테스트(`priceScale.mode` 비로그/비퍼센트, 포매터 배율 없음)

---

## S8 — `/trading` (4,269줄)

> 핸드오프의 2,494 는 `features/live-sessions` 1,543줄을 뺀 수다.

- [ ] `features/trading` + `features/live-sessions` 양쪽 포함
- [ ] 죽은 `kill-switch-modal.tsx` 177줄 + 그 테스트 삭제
- [ ] `error.tsx` 신설
- [ ] 상태 4종 실제 렌더 (에러 엔드포인트 = `GET /trading/sessions/{id}/positions · 503`)

**검증 게이트** — S5 공통 + `ui-ux-pro-max` 2회차

---

## S9 — 교차 정합 감사 + 잔여 정리

> 함정 #5. 프로토타입 17벌이 개별 통과 후 교차 감사에서 49건(BLOCKER 3)이 나왔다. React 에서는 **컴포넌트 경계**에서 같은 일이 일어난다.

- [ ] 캐논 §4.1 원장 지정을 React 화면에 매핑해 교차 감사 (파생 `/dashboard` 가 원장 `/backtests` 와 어긋나면 파생이 고칠 쪽)
- [ ] 잔여 반경 — `rounded-2xl`/`3xl` 6건 · 리터럴 px arbitrary 16건 · stale `var()` 폴백 5건
- [ ] `button.tsx:31,32,36,38` · `select.tsx:46` 무력 `min()` 클램프 제거
- [ ] allowlist 0 도달 확인

---

## Blocked

(현재 없음)

## Questions

- `strategy.backtest_count` 정의 (완료 기준 대 전체 실행 기준) — 원장이 `screen-06` 이라 P1 밖. 전략 목록 이식 시 결정
- OKX 를 `frontend/src/features/trading/schemas.ts:71` enum 에서 뺄지 — "OKX 데모로 실제 주문이 오갔는가" 실측 후 판단
