<!-- UI/UX 풀 개편 진행 체크리스트 (P0~P7) -->

# UI/UX 개편 — Checklist

## P0 — 방향·시그니처 (design-shotgun)

- [x] 4종 변형 생성·비교 보드
- [x] 방향 확정 = A "Terminal Tape" (시그니처 = P&L Tape, 단일 코퍼 액센트)
- [x] 라이트+다크 hex 페어 전체 토큰 확정 (context-notes.md, WCAG AA 검증)
- [x] DESIGN.md 방향 supersede 노트

## P1 — 디자인 언어 잠금 + 다크 인프라 + 프리미티브 (직렬)

- [ ] `globals.css` 토큰 레이어 재작성 (전체 `.dark`, 금융 토큰, `@theme inline` 이동, dead dash 삭제)
- [ ] `qb-*` keyframe → `color-mix(currentColor)` 전환
- [ ] `DESIGN.md` §1/§2/§11 듀얼 테마 SSOT 갱신
- [ ] `next-themes` + `@clerk/themes` 설치
- [ ] `app-providers.tsx` ThemeProvider + ClerkThemeBridge
- [ ] `components/ui/theme-toggle.tsx` (mounted 가드)
- [ ] 헤더 토글 배치 (dashboard-header + public)
- [ ] 프리미티브 격상 (card/button/badge/input/textarea/select/tabs)
- [ ] 신규 `components/ui/data-table.tsx`
- [ ] 아이콘 규약 (글리프 → Lucide 매핑)
- [ ] 차트 테마 배선 (trading-chart resolved hex / recharts / Monaco pine-light)
- [ ] optimizer SVG `hsl()` 버그 수정
- [ ] DoD: 토글 전 앱 flip / tsc·lint·test·build green / 양 테마 axe / 폴리시드 라이트 픽셀 동일

## P2~P6 — 화면별 롤아웃 (P1 머지 후, worktree 병렬)

- [ ] P2 optimizer (14파일) — 글리프/테이블/raw error/API 용어
- [ ] P3 백테스트 리포트 (43파일) — recharts 테마 / trade-table 패리티 / BL-360
- [ ] P4 strategies (29파일) — 어휘 / Monaco light / strategy-card 보존
- [ ] P5 trading (6파일) — 양 테마 / 거래소 삭제 onError / BL-355
- [ ] P6 public·shell — 레이아웃 / 공유 뷰어 차트 / 글로벌 모바일 터치 룰

## P7 — 접근성·정리 스윕 (직렬)

- [ ] 전 화면 양 테마 axe 재실행
- [ ] 최종 글리프/`dark:`-leak grep 감사
