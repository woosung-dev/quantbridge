# A+B+C Trust 번들 — Context Notes (append-only 결정 기록)

> 2026-07-12 pine-batch QA 후속. 결정·[가정]·불일치를 발생 순서대로 기록.

## Phase 0 — Preflight (§7.1)

- PR #425 (stage/pine-batch-qa → main) **MERGED @9398a36**. 로컬 main = origin/main 동기. → 분기 기준 = **main**.
- `docs/archive/qa/2026-07-12-pine-batch-1h4h/results.json` 존재 확인.
- baseline 실측: `uv run pytest tests/strategy/pine_v2 -q` → **815 passed, 16 skipped** (skipped = nightly mutation oracle). 기억 아닌 실측 일치.
- 브랜치: `stage/trust-bundle`(main 분기, origin push) → `feat/pine-405-na-propagation` 분기.
- Task B 엔진-diff-0 사전확정: `BacktestConfig.default_qty_type/value`(types.py:40-41) + `run_backtest_v2` form-tier 전달(v2_adapter.py:100-101). `--normalized` 는 config-only.

## Phase A — BL-405 ★FRAME CHANGE (전제 반증)

- **결정적 발견:** TV 공식문서 리서치(Workflow, r.jina.ai 리더 인용)로 BL-405 전제가 **반증됨**.
  - TV type-system: "bool 은 절대 na 아님", "비교 연산은 na 피연산자에 concrete `false` 반환"(`!=` 포함), "bool history on nonexistent bar → false".
  - TV operators: "na 전파는 산술에만".
- **결론:** 현재 pine_v2 동작(비교→False, bool never na, crossover→False)이 **TV 정답**. 계획됐던 na-전파 수정은 **회귀**였음.
- **오라클 ②의 "TV=bar 15" 는 잘못된 전제** (bool na 전파 가정). 실제 TV 는 엔진처럼 bar 12. → §7.3 순환/wrong-premise 함정의 교과서 사례. **TV 문서 인용 게이트가 코드 작성 전에 오진을 차단함.**
- 영향 조사(Workflow) 교차 확인: 골든 5종은 (계획대로 na 전파했다면) 트레이드/메트릭 불변, s2/s3 는 var_series digest 만 변동 → 관측 거래 결과에 버그 없음 방증.
- **사용자 결정 (AskUserQuestion):** "BL-405 폐기 + TV정합 회귀테스트" (옵션 1). → PR-1 = **엔진 동작 무변경** + 회귀 테스트 + 백로그 재분류 + 주석/리포트 정정 + ta.ema 워밍업 신규 BL.

### 조치 산출물

- 신규 회귀 테스트 `tests/strategy/pine_v2/test_na_bool_tv_parity.py` (13건) — 비교/bool/crossover/산술 대비/제어흐름 TV 정합 잠금. 인용 docstring 포함. **13 passed.**
- [실측 발견] 회귀 테스트 작성 중 **부수 edge 1건** 발견: `bool[n]` 범위밖 과거참조(bar 0)가 nan 반환(TV 는 false). in-range 는 concrete bool 정상. 소비(비교/제어흐름)에서 nan→false 소거로 **거래·시그널 영향 0**. 관측 등가를 테스트로 잠그고 raw 저장 편차는 **BL-409(b)** 로 등재.
- 주석 정정: `interpreter.py` `_eval_compare` na-guard(오해 유발 "na 전파" 문구 → TV 인용), `stdlib.py` crossover/crossunder/cross na-guard 3곳.
- 백로그: **BL-405 → CLOSED not-a-bug 재분류**, **BL-409 신규 등재**(ta.ema 시딩 (a) + bool[n] 범위밖 (b)).
- `report.md` §4.2 에 **erratum** 추가.

### [가정] / [확인 필요]

- [확인 필요] bs 4h 2024 의 실제 TradingView 첫 시그널 bar — 실제 TV 실행 그라운드트루스 필요(내 환경 불가). ta.ema 시딩 정합(BL-409a)의 최종 판정 조건.
- [가정] ta.ema 워밍업이 엔진과 TV 가 동일하다면 bs 첫 시그널 = bar 12(엔진=TV). 다르면 bar 이동은 bool-na 가 아닌 ta.ema 시딩 탓.
