# BL-773 레인 A 원장 초안

**상태:** PARTIAL — Generator 구현·관련 회귀 검증 완료, Evaluator 수용 판정 대기.

- `StrategyVersion` 불변 스냅샷, Strategy 최신 포인터, Backtest `strategy_version_id`·`engine_version`,
  기존 행 백필 마이그레이션을 추가했다.
- Backtest worker·coverage 및 Optimizer worker는 부모 Backtest의 스냅샷 source를 사용한다.
- 검증: 관련 pytest 45 passed, Ruff check/format 및 `git diff --check` 통과.
- 마이그레이션: 기존 행을 부모 리비전에 심는 backfill test와 `head → -1 → head`는 통과했다.
- AC-5: CONTROL 판정 — `funding_rates.exchange` drift는 선재 BL-782 범위이고, BL-773은 왕복 rc=0·신규 drift 0으로 충족한다.
