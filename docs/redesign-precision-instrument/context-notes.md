# Precision Instrument 리디자인 — 컨텍스트 노트

> 결정과 근거를 세션 간 이어받기 위한 기록. 갱신은 append 위주.

## 2026-07-06 킥오프

### 브랜드 결정 (사용자 확정)

- **방향 A "Precision Instrument"** — 콜드스틸/카본 뉴트럴 + 시그널 코퍼 유지. 근거: 현행 Terminal Tape의 웜크림(#fafaf7)+코퍼가 AI 생성 디자인 기본값 클러스터 #1(웜크림+테라코타)과 인접 → "AI 티"의 근원. 뉴트럴 교체가 처방, 코퍼는 브랜드 연속성 자산이라 유지.
- **다크 디폴트** (enableSystem 유지 — 기존 localStorage 명시 선택은 next-themes가 우선 존중, 신규 방문자만 다크).
- **전 범위** — 랜딩/마케팅 포함, 웨이브 시리즈.
- 타이포: Archivo(display) / Pretendard Variable(body, 한국어 품질 핵심) / IBM Plex Mono(mono). 숫자 = mono tabular 주인공.
- 시그니처 2종에만 볼드함 집중: tick ruler + P&L Tape 모티프 확장. 나머지 절제(플랫+1px 보더).

### codex G0 (388k tokens, 1 iter)

**수용 (frame change 5):**

1. DESIGN.md 신 헌법 초판을 W6→W1로 앞당김 — 헌법 없이 웨이브 진행은 순서 오류.
2. live-smoke `paths`에 `.css` 부재 — globals.css-only PR 무검증 갭 → W0에서 추가.
3. h1-h6 블랭킷 `font-stretch` 금지 — 한글 제목은 Pretendard 폴백이라 라틴만 늘어나는 혼합 폭. 라틴 전용 `.qb-display-wide/-expanded` 유틸로 한정.
4. W1 PR-1 3분할(토큰/폰트/테마) — 실패 양상이 달라 원인 분리 + revert 입도.
5. `src/lib/brand-palette.ts` 신설 — CSS 변수 못 읽는 3 소비자(chart 폴백/Monaco hex/OG)의 3중 desync를 단일 상수 모듈로 해소.

**기각 (코드 근거):**

- "Monaco에 리터럴 `"IBM Plex Mono"` 주면 fonts.ts 불필요" — next/font는 해시된 family명만 @font-face 등록. `ibmPlexMono.style.fontFamily` 필요. fonts.ts 유지.
- "차트 폴백 다크화 = enableSystem 모순" — 폴백은 SSR/사전 hydration 전용, 어느 값이든 한쪽은 플래시. 다크 디폴트 정책상 다크 편향이 정합(기존 코드도 반대 방향 동일 트레이드오프).

**메모(구현 시 확인):** chart-tokens paletteCache themeKey 초기 mismatch 가능성(W6 검증 항목), `--card-raised`는 @theme inline 매핑+`--popover` 배선까지, theme-color는 Next 16 `viewport` export로.

### prereq spike

- **Pretendard dynamic-subset PASS**: `pnpm add pretendard` + globals.css `@import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"` → `pnpm build` 성공, woff2 109개 `.next/static/media` 번들, CSS에 "Pretendard Variable" @font-face 확인. next/font/local 폴백 플랜 불필요.
- 스파이크는 리셋함(실제 적용은 W1 PR-1b).

### 운영 결정

- **stage 브랜치는 W0 커밋(0a059d3) 기반으로 생성** — PR merge ref에 신 워크플로우가 포함되어 PR #398의 main 머지를 기다리지 않고 웨이브 PR CI 발화 가능. #398 머지 후 main→stage 동기화 시 동일 변경이라 무충돌.
- **branch protection 없음** (private repo, free plan — API 403). required checks 강제 불가 → 머지 규율은 사용자 수동으로 커버. codex의 required-checks 지적은 이 레포에선 해당 없음.
- **pre-push 훅**: stage/\*\* push는 `QB_PRE_PUSH_BYPASS=1` 필요 (기존 관례).
- **승인 게이트**: 브랜치/커밋/push/PR 생성은 플랜 승인으로 위임받음. main 머지(stage→main 포함)와 배포는 전부 사용자 수동.
- **카피 동결**: 리디자인은 visual-only. E2E getByText 65건 + smoke.spec 카피 셀렉터 의존. 카피 개선은 별도 사이클.
- 하이브리드 상태 허용: 토큰 선교체로 미개편 페이지가 새 팔레트로 뜨는 중간 상태는 버그 아님(각 PR 설명에 명기).
