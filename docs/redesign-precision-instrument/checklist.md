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

## W1 — 토큰 파운데이션 + ui/ (직렬 크리티컬 패스)

- [ ] PR-1 (토큰): globals.css 팔레트/radius/shadow 전면 교체 + `--card-raised` 신설 + `--dash-*` 삭제 + 차트 토큰 `.dark` 승격 + `src/lib/brand-palette.ts` 신설 + chart-tokens.ts 폴백 동기(동일 커밋)
- [ ] PR-1 게이트: lint/tsc/vitest/build + 대비 계산표(4.5:1 전수) + live-smoke
- [ ] PR-1b (폰트): pretendard 설치 + `src/lib/fonts.ts`(Archivo wdth + IBM Plex Mono) + layout.tsx + globals.css 폰트 매핑 + `.qb-display-wide/-expanded` 유틸(h1-h6 블랭킷 font-stretch 금지)
- [ ] PR-1c (테마): defaultTheme="dark" + Clerk 3곳(bridge+sign-in/up 하드코딩 제거) + viewport themeColor + skip link 대비 수정
- [ ] PR-2 (ui/셸/모티프): ui/ 15개 리스타일 + layout 셸 5(tick ruler) + tape 승격(components/tape/) + skeleton variant:"tape" + 공용 7 + **DESIGN.md 신 헌법 초판**
- [ ] W1 종료 게이트: authed E2E 8 spec 전부 + 대표 6라우트 시각 스팟(dark/light × 375/768/1440)
- [ ] 태그 `redesign-w1-done`

## W2 — 코크핏/트레이딩 (로직 diff 0)

- [ ] PR-3: dashboard-cockpit + pnl-tape 소비처 + trading 5종 + orders-blotter
- [ ] 게이트: trading-ui / live-session-flow / sprint32-dogfood-gate / backtest-live-mirror
- [ ] 태그 `redesign-w2-done`

## W3 — backtests 트리 (worktree 병렬 3워커 + 통합 리뷰 1패스)

- [ ] PR-4: report 20 + charts 15
- [ ] PR-5: forms 8 + list 13 + trades 5
- [ ] PR-6: share 5 + OG(brand-palette import)
- [ ] report testid 20종 1:1 보존 체크
- [ ] 게이트: dogfood-flow / sprint46-tier1·2 + 통합 리뷰(해석 발산 방지)
- [ ] 태그 `redesign-w3-done`

## W4 — strategies/optimizer/onboarding

- [ ] PR-7: strategies 30 + Monaco pine-dark/light 재작성(brand-palette 참조) + fontFamily
- [ ] PR-8: optimizer 17
- [ ] PR-9: onboarding 10(illustration hex→토큰) + admin 2
- [ ] 게이트: sprint55-optimizer / sprint46-tier3 + Monaco 양테마 수동
- [ ] 태그 `redesign-w4-done`

## W5 — 랜딩/마케팅/auth (카피 동결)

- [ ] PR-10: 랜딩 10섹션 (SVG 재제작 캡 3: landing-hero / dashboard-showcase / brand-panel)
- [ ] PR-11: waitlist / pricing / legal 3종 / maintenance / not-available
- [ ] PR-12: auth split-screen + Clerk appearance 최종 정합
- [ ] 게이트: smoke + live-smoke + 랜딩 풀 시각 매트릭스 + Clerk 양테마
- [ ] 태그 `redesign-w5-done`

## W6 — 전역 QA/문서 마감

- [ ] PR-13: error/404 + hex grep 스윕(예외: brand-palette.ts + 명시 SVG)
- [ ] e2e:all + 25라우트 시각 매트릭스(~150샷)
- [ ] 접근성 감사: focus-visible 순회 / reduced-motion / 대비 재검 / tick ruler 페인트 비용
- [ ] chart 캐시 themeKey 초기 mismatch 검증
- [ ] DESIGN.md 최종 정합
- [ ] stage→main PR 생성(before/after 스크린샷) → **사용자 수동 머지**
