# Precision Instrument 리디자인 — 체크리스트

> 마스터 플랜: `~/.claude/plans/golden-enchanting-teacup.md` (승인 2026-07-06).
> 브랜치 전략: `stage/precision-instrument`에 웨이브 PR 누적, stage→main은 사용자 수동(Option C).

## 킥오프

- [x] codex G0 플랜 검증 (388k tokens, frame change 5건 수용 / 오독 2건 기각)
- [x] prereq spike: Pretendard dynamic-subset import → `pnpm build` PASS (woff2 109개 번들)
- [x] checklist.md + context-notes.md 생성

## W0 — 준비

- [x] ci.yml `pull_request.branches`에 `stage/**` 추가 (PR #398, main 직행)
- [x] live-smoke.yml 동일 + paths에 `frontend/src/**/*.css` 추가 (codex G0 수용)
- [x] testid 베이스라인 고정 (`testid-baseline.txt`, 156 unique)
- [x] `stage/precision-instrument` 생성 (W0 커밋 기반 — merge ref에 신 워크플로우 포함)
- [ ] PR #398 사용자 머지 → main→stage 동기화
- [ ] stage 대상 더미/실PR로 CI 발화 확인 (W1 PR-1이 겸함)

## W1 — 토큰 파운데이션 + ui/ (직렬 크리티컬 패스) ✅

- [x] PR-1 (토큰): #399 — globals.css 전면 + `--card-raised` + `--dash-*` 삭제 + 차트 `.dark` 승격 + brand-palette.ts + chart-tokens 폴백 동기
- [x] PR-1 게이트: lint/tsc/vitest 812/build + 대비 계산표 22페어 ALL_PASS + live-smoke
- [x] PR-1b (폰트): #400 — pretendard dynamic-subset + fonts.ts + layout.tsx + `.qb-display-wide/-expanded` (+smoke 렌더스톰 카운트 woff2 제외)
- [x] PR-1c (테마): #401 — defaultTheme dark + Clerk 3곳 + viewport themeColor + skip link 대비
- [x] PR-2 (ui/셸/모티프): #402 — ui/ 리스타일 + tick ruler/노치 + tape 승격 + skeleton tape + DESIGN.md v3 초판
- [x] W1 종료 게이트: authed E2E **신규 회귀 0**(8건 실패는 main 동일 = stale baseline 실측) + 시각 스팟 16샷 PASS
- [x] 태그 `redesign-w1-done`

## W2 — 코크핏/트레이딩 (로직 diff 0) ✅

- [x] PR-3(#403): 팔레트 위반 4건 토큰화 + WidgetSection 눈금 + data-tone 테스트 전환
- [x] 게이트: trading-ui 7/7 (나머지 3 spec은 stale baseline — main 동일 실패 실측)
- [x] 태그 `redesign-w2-done`

## W3 — backtests 트리 (worktree 병렬 3워커) ✅

- [x] PR-4(#406): chart-legend/marker/axis hex → 토큰, key-stats-strip TickRuler, recharts 감사 위반 0
- [x] PR-5(#407): TapeProgress 3사이트 + violet→warning + 선재 버그(--bg-soft/--border-light 미정의) 수정
- [x] PR-6(#405): OG hex 13건 → BRAND_PALETTE.dark, 공유 페이지 정합
- [x] testid 보존(테스트 수정 0) + 통합 리뷰(칩 라운딩 6px 수렴 확인)
- [x] 태그 `redesign-w3-done`

## W4 — strategies/optimizer/onboarding ✅

- [x] PR-7(#408): Monaco pine-dark/light BRAND_PALETTE 재작성 + ibmPlexMono fontFamily + session-chips 이모지→lucide + pill 5곳 태그화
- [x] PR-8(#409): 히트맵 bullish/bearish 정본화 + data-tone 배지 + OOS TapeProgress
- [x] PR-9(#410): illustration 62 hex→CSS var + --text-tertiary 미정의 버그 수정 + admin 플랫화
- [x] 게이트: 전체 authed 재실행 — 실패 집합이 baseline 8건과 동일(신규 회귀 0) + 시각 스팟
- [x] 태그 `redesign-w4-done`

## W5 — 랜딩/마케팅/auth (카피 동결) ✅

- [x] PR-10(#412): 랜딩 hex 105→0, 목업 3종 dark 스코프 신브랜드 프리뷰, tape/눈금/노치 배선 (재제작 없이 치환으로 성립 — 캡 미소진)
- [x] PR-11(#404): waitlist ✓ 글리프 → lucide (나머지는 토큰 캐스케이드로 기정합)
- [x] PR-12(#411): brand-panel hex 10→0, forced-dark 카본 패널, Clerk radius 토큰화
- [x] 게이트: smoke 4/4(워커 격리 실행) + CI 그린 + 랜딩/auth 시각 검수
- [x] 태그 `redesign-w5-done`

## W6 — 전역 QA/문서 마감

- [x] hex grep 스윕: 잔존 4파일 중 2개 수정(activity-timeline-chart 6건, cockpit 수동 코퍼 1건) — 공인 예외만 남음(pine-language 에디터 웰 4 + layout viewport 2, 주석 명시)
- [x] 고아 keyframe chipPop 삭제 + onboarding SVG 구 폰트 문자열 → var(--font-mono/display)
- [x] 42 라우트×테마 콘솔 스윕 — **앱 레벨 에러 0** (전 에러 = 로컬 CORS 환경 이슈) + 스크린샷 매트릭스(~63샷, scratchpad/w6-matrix)
- [x] DESIGN.md v3 정합(§7/§10.4 v2 스냅샷 supersede 노트)
- [x] 게이트: lint/tsc/vitest 812/build PASS
- [ ] stage→main PR 생성(before/after) → **사용자 수동 머지**
- [ ] 잔여(후속 후보): 심층 키보드 순회 감사, chart 캐시 themeKey 초기 mismatch 코드 검토, aria-label 색 이름 카피(카피 사이클), 로컬 백엔드 CORS(3100 origin) 정리
