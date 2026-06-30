<!-- UI/UX 풀 개편 진행 체크리스트 (P0~P7) -->

# UI/UX 개편 — Checklist

## P0 — 방향·시그니처 (design-shotgun)

- [x] 4종 변형 생성·비교 보드
- [x] 방향 확정 = A "Terminal Tape" (시그니처 = P&L Tape, 단일 코퍼 액센트)
- [x] 라이트+다크 hex 페어 전체 토큰 확정 (context-notes.md, WCAG AA 검증)
- [x] DESIGN.md 방향 supersede 노트

## P1 — 디자인 언어 잠금 + 다크 인프라 (직렬) ✅ 핵심 완료

- [x] `globals.css` 토큰 레이어 재작성 (전체 `.dark`, 금융 토큰, `@theme inline` 이동, dead dash 삭제) — `dc247cd`
- [x] `qb-*` keyframe → `color-mix(token)` 전환 — `dc247cd`
- [x] `DESIGN.md §0` 듀얼 테마 방향 supersede (§1/§2/§11 구버전은 §0가 상위) — `f7b94f7`
- [x] `next-themes` + `@clerk/themes` 설치 — `dc247cd`
- [x] `app-providers.tsx` ThemeProvider + ClerkThemeBridge — `dc247cd`
- [x] `components/ui/theme-toggle.tsx` (CSS dark: 기반, set-state-in-effect 회피) — `dc247cd`
- [x] 헤더 토글 배치 (dashboard-header) — `dc247cd` / public 헤더 → P6
- [x] 프리미티브 — card/button/badge/chips/nav가 시맨틱 토큰으로 **자동 flip 검증**(별도 격상 불필요, 스크린샷 확인)
- [x] 차트 테마 배선 (trading-chart resolved hex + themeKey) — `8119835`. recharts `var()` 자동 flip. **Monaco pine-light → P4 이관**
- [x] optimizer SVG `hsl()` 렌더버그 수정 — `8119835`
- [x] **DoD 검증: 토글 전 앱 flip(실 인증화면 양 테마 스크린샷) / tsc·lint·754 test·build green**
- [→ 이관] 신규 `components/ui/data-table.tsx` → **P2**(첫 소비처 optimizer). 아이콘 글리프→Lucide 스윕 → **P2/P6** 각 표면.

## P2~P6 — 화면별 롤아웃 (P1 머지 후, worktree 병렬)

- [ ] P2 optimizer (14파일) — 글리프/테이블/raw error/API 용어
- [ ] P3 백테스트 리포트 (43파일) — recharts 테마 / trade-table 패리티 / BL-360
- [ ] P4 strategies (29파일) — 어휘 / Monaco light / strategy-card 보존
- [ ] P5 trading (6파일) — 양 테마 / 거래소 삭제 onError / BL-355
- [ ] P6 public·shell — 레이아웃 / 공유 뷰어 차트 / 글로벌 모바일 터치 룰

## P7 — 접근성·정리 스윕 (직렬)

- [ ] 전 화면 양 테마 axe 재실행
- [ ] 최종 글리프/`dark:`-leak grep 감사
