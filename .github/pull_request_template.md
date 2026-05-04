## 요약

<!-- 변경 목적을 1-3줄로. "왜 필요한가 / 무엇이 바뀌는가". -->

## 변경 파일 / 스코프

- [ ] frontend
- [ ] backend
- [ ] infra / CI / hooks
- [ ] docs / rules

## 검증 (필수)

### 공통

- [ ] 로컬 `pnpm lint` / `pnpm typecheck` 통과
- [ ] 로컬 `pnpm test` 통과
- [ ] CI green (이 PR)

### Frontend hooks 변경 시 필수 (LESSON-004 방어)

<!-- useEffect / useState / useMemo / useCallback / useRef / 커스텀 훅 / React Query / Zustand / RHF 이 diff 에 있다면 반드시 체크 -->

- [ ] `dev server 5분 이상` 실제 사용 + Activity Monitor/top으로 **CPU 100% 폭주 없음 확인**
- [ ] React DevTools Profiler로 **불필요 재렌더 없음 확인** (또는 "Highlight updates" on)
- [ ] `useEffect` dep 배열에 **object/array prop 없음** (scalar 우선 — `[obj.id]`, `[list.length]`)
- [ ] `react-hooks/set-state-in-effect` / `exhaustive-deps` ESLint 규칙 disable **하지 않음**
- [ ] React Query `.data`, Zustand full store, RHF `watch()`, Zod `.parse()` 결과를 useEffect dep **로 쓰지 않음**
- [ ] unit test 35+개 외에, **Playwright/수동 E2E walkthrough 완료** (Clerk 로그인부터 핵심 흐름까지)

### Backend 변경 시

- [ ] `uv run ruff check .` 통과
- [ ] `uv run mypy src/` 통과
- [ ] 관련 pytest 추가 / 기존 녹색

### UI/UX 변경 시

- [ ] 모바일 (375px) / 데스크톱 (1280px) 렌더 확인
- [ ] dark / light 테마 양쪽 확인 (해당 시)
- [ ] 접근성 — keyboard 탐색, aria-label, touch target ≥ 44px

## Codex Gates (Sprint 28+ 의무, sprint type 별 차등)

> **Sprint type:** A (신규 기능 의무) / B (risk-critical 권고) / C (dogfood hotfix 압축) / D (docs 면제)
> **codex hang 발생 시:** Claude self-review (G0 evaluator pattern adapted) 가 fallback — 기록에 명시.

- [ ] **G.0 Plan eval** (sprint 시작 시 plan review) — link: <!-- artifact / commit / dev-log -->
- [ ] **G.2 Implementation review** (각 PR adversarial review) — link: <!-- PR comment 또는 dev-log -->
- [ ] **G.4 P2 issue 처리** (G.2 통과 후 P2 정리) — link: <!-- BL 등록 vs 즉시 fix -->
- [ ] **Self-assessment 점수** N/10 + 근거 (≥3 줄):
<!-- 정성 + 정량 dual metric. Sprint 27 의 8.0 + 4 P0 BL divergence case 회피. -->

## 관련 이슈 / 문서

<!-- docs/dev-log/ 번호 / GitHub issue / Lesson 번호 (.ai/project/lessons.md) -->
<!-- BL ID 명시 의무: 해결 시 Resolved 표시 + 신규 등록 시 P0/P1/P2/P3 분류 -->

## 스크린샷 / 터미널 로그

<!-- UI/UX 변경 시 before/after. perf 이슈 시 Profiler 캡처. -->

## 롤백 전략

<!-- 머지 후 문제 시 어떻게 되돌리는가. feature flag / revert / config toggle. -->
