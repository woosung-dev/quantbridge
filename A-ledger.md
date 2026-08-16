# BL-773 레인 A 원장 초안

**상태:** PARTIAL — Generator 구현·관련 회귀 검증 완료, Evaluator 수용 판정 대기.

- `StrategyVersion` 불변 스냅샷, Strategy 최신 포인터, Backtest `strategy_version_id`·`engine_version`,
  기존 행 백필 마이그레이션을 추가했다.
- Backtest worker·coverage 및 Optimizer worker는 부모 Backtest의 스냅샷 source를 사용한다.
- 검증: 관련 pytest 45 passed, Ruff check/format 및 `git diff --check` 통과.
- 마이그레이션: 기존 행을 부모 리비전에 심는 backfill test와 `head → -1 → head`는 통과했다.
- AC-5: CONTROL 판정 — `funding_rates.exchange` drift는 선재 BL-782 범위이고, BL-773은 왕복 rc=0·신규 drift 0으로 충족한다.
- [잔여] `apps/web/e2e/sprint46-tier3-nth.spec.ts:559`와 `apps/web/e2e/dogfood-flow.spec.ts:152`에는 `force: true` 클릭이 남아 있다; 이번 gate flake와의 인과는 확정하지 않았고 BL-773 범위 밖이라 수정하지 않는다.
- ★**CONTROL 판정 (2026-08-17) — `sprint46-tier1-critical.spec.ts` 의 제출 동기화 보강을 되돌렸다.**
  나쁜 변경이어서가 아니다. ⑴ **범위 밖**이다 — 무관한 게이트 실패를 고치려다 들어왔는데 그 실패와
  인과가 없음이 측정으로 밝혀졌다(가설 2건 반증). ⑵ **원장과 충돌**한다 — [BL-784] 가 잔존 `force` 2곳에
  「기전 확정 전에 손대지 마라」를 적었고, 같은 이유가 이 1곳에도 적용된다. 한 파일만 예외로 두면
  규칙이 아니라 편의가 된다. ⑶ **증명 없이 게이트 표면만 늘린다** — `apps/web` 을 건드리면 `has_fe=1` 이
  되어 P1 BE PR 에 `/vercel-react-best-practices`(React 컴포넌트 성능 리뷰)가 요구되는데, 대상은
  Playwright 스펙 6줄이라 그 리뷰에는 볼 것이 없다. 되돌린 뒤 `git diff --stat -- apps/web` = **0** 확인.
  개선안 자체는 [BL-784] 의 권장 접근 ⑵ 가 보유한다.
- ★**부수 관측 (BL 미등재)** — `has_fe` 는 `apps/web/e2e/**` 와 `apps/web/src/**` 를 구분하지 않는다.
  테스트만 고쳐도 React 성능 리뷰 신호가 필수가 되는 **과잉 발화**다. [BL-784] 와 다른 축이라 여기 적어만 둔다.
