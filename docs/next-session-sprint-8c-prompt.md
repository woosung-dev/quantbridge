# 다음 세션 시작 프롬프트 — Sprint 8c (user function + 3-Track 라우터 묶음)

> **사용법:** 새 세션에서 아래 코드블록 전체를 복사·붙여넣기.
> Sprint 8b 완료 직후 (2026-04-18, 브랜치 `feat/sprint8b-tier1-rendering`) 시점 기준.

---

```
Sprint 8b 완료 상태 (브랜치 `feat/sprint8b-tier1-rendering`, 15 commits, push/PR 아직).
  이번 세션은 **Sprint 8c — user-defined function(`=>`) + 3-Track 라우터(S/A/M) 묶음**.

  ## 이 세션의 위치
  - Sprint 8b 종료 시점: pine_v2 foundation + Tier-1 가상 strategy + Tier-0 렌더링
  scope A + 6/6 corpus 완주 달성. Opus+Sonnet 독립 리뷰 교차 hardening 포함.
  - **224 pine_v2 tests / 750 backend / ruff·mypy clean.**
  - s3_rsid / i3_drfx는 `strict=False` 경로로 완주만 검증 — user-defined function
  (`foo(x) =>`)과 `valuewhen`/`barssince`/`request.security` 미지원이 원인.
  - 이번 세션 목표: user function 지원으로 s3/i3 **실제 매매 검증 재활성화** +
  3-Track 라우터(S/A/M 분류기) 구축.

  ## 이미 지원 완료 (Sprint 8a/8b, 재구현 금지)
  - **stdlib ta.***: sma / ema / atr / rsi / highest / lowest / change / crossover /
  crossunder / pivothigh / pivotlow / stdev / variance + na / nz(2-arg)
  - **v4 legacy alias**: atr/ema/sma/rsi/crossover/crossunder/highest/lowest/change/
  pivothigh/pivotlow/max/min/abs → ta.*/math.*
  - **math.***: abs/max/min/floor/ceil/round/sqrt/log/pow (na 전파)
  - **strategy.***: entry(long/short, 시장가, stop= OCO, when= kwarg,
  v4 boolean direction + v5 strategy.long/short 양쪽 parity), close, close_all,
  position_size, position_avg_price
  - **built-in**: open/high/low/close/volume/bar_index/na/time +
  syminfo.mintick/tickerid + timestamp(y,mo,d,h,mi) (month/day/hour/min 반영)
  - **Pine 구문**: var / varip / user 변수 series subscript (`myvar[n]`) /
  if-else / ternary / BoolOp 단축평가 / chained Compare / **switch (Switch/Case AST)** /
  iff(cond, then, else)
  - **Alert Hook v1**: collect_alerts() + classify_message() + condition-trace +
  discrepancy 자동 감지 + **condition_ast 보존** (Tier-1 재평가용)
  - **Tier-1 가상 strategy 래퍼**: VirtualStrategyWrapper + run_virtual_strategy —
  edge-trigger(False→True) SignalKind → strategy.entry/close 자동 매핑,
  discrepancy=True 경고 후 condition_signal 우선
  - **Tier-0 렌더링 scope A**: LineObject/BoxObject/LabelObject/TableObject +
  RenderingRegistry (좌표 저장 + getter). line.get_price 선형보간.
  deleted 상태면 get_price=nan, set_xy=no-op (Sprint 8b hardening)
  - **_ATTR_CONSTANTS 40+**: line.style_*/extend.*/shape.*/location.*/size.*/
  position.* + alert.freq_*/display.*/xloc.*/yloc.*/text.*/font.* prefix stub
  - **에러 경로**: pynescript.ast.error.SyntaxError (Python 내장 미상속, except 분기 주의)
  - **strict=False 완주 경로**: PineRuntimeError를 errors 리스트로 수집 후 다음 bar 진행.
  단, 다른 예외(ZeroDivisionError/TypeError)는 포착 안됨

  ## 이번 세션 목표 2가지 (묶어 진행, H1 scope 내)

  ### 🎯 1. user-defined function 지원 (ADR-011 Tier-0 확장)
  pynescript AST에서 `FunctionDef` 노드를 top-level Assign 유사 개념으로 수집해
  interpreter의 symbol table에 저장. Call 해석 시 해당 이름이 user function이면
  body를 evaluate 컨텍스트에서 실행하고 반환값(마지막 Expr 값) 반환.

  **최소 구현 범위 (H1 scope):**
  - `foo(x, y) => x + y` 같은 단일 표현식 반환
  - 다중 statement body 반환 (마지막 expr가 결과값, Pine 관례)
  - **multi-return tuple** (`[a, b] = foo(...)` — i3_drfx supertrend 패턴)
  - H2+ 이연: 중첩 closure / 고차 함수 / 타입 추론

  **성공 기준:**
  - s3_rsid.pine이 `strict=True`로 완주 + `_inRange` 기반 매매 시퀀스 생성
  - i3_drfx.pine의 `supertrend(...)` 호출이 성공적으로 `[superTrend, direction]`
    반환하고 인덱스 분해 동작
  - 기존 hardening 테스트 `test_switch_default_in_middle_rejected_by_parser` 포함
    224 tests 전부 유지 (regression zero)

  ### 🏗 2. 3-Track 라우터 (S / A / M 분류기)
  ADR-011 §2.1.1 3-Track 아키텍처. 파싱 후 스크립트를 3종으로 분류:
  - **Track S**: `strategy()` 선언 + `strategy.entry/exit/close` 사용 → 네이티브 실행
  - **Track A**: `indicator()` + `alertcondition()`/`alert()` 존재 → Alert Hook Parser
    + 가상 strategy 래퍼 (Sprint 8b에서 이미 구현)
  - **Track M**: `indicator()` only, alert 없음 → Variable Explorer (H2+ 이연,
    이 세션은 "분류 + warning" 까지만)

  **공개 API (제안):**
  ```python
  from src.strategy.pine_v2 import classify_script, ScriptTrack

  track = classify_script(source)  # ScriptTrack.STRATEGY / ALERT / MANUAL
  ```

  **성공 기준:**
  - 6 corpus 각각 올바른 Track 반환 (s1/s2/s3 → STRATEGY, i1/i2/i3 → ALERT)
  - Track M 스크립트 샘플 1개 작성해서 classifier 검증
  - `parse_and_run_v2(source, ohlcv)` wrapper가 Track에 따라 `run_historical` vs
    `run_virtual_strategy` 자동 dispatch

  ## 진행 순서 (권장)
  1. **user function 먼저** → s3/i3 실제 매매 검증 재활성화 (Sprint 8b strict=False
     테스트를 strict=True + trade assertion으로 상향). 독립 완결.
  2. **3-Track 라우터** → classify_script() + parse_and_run_v2 dispatcher.
     6 corpus parametrized 검증.
  3. 양쪽 완료 후 s3/i3 테스트에 "strict=True + trade count > 0" assertion 추가.

  ## 엄수 제약
  - **pine_v2/ 모듈만.** 기존 pine/ 모듈은 touch 0 (dogfood 복구 경로 보호)
  - **H1 MVP scope 준수** — user function은 core만 (closure / 고차 H2+).
    strategy.exit trail_points / qty_percent / pyramiding 여전히 H2+ 이연
  - **pynescript LGPL 격리** — import 6 파일 경계 유지 (parser_adapter /
    ast_metrics / ast_classifier / alert_hook / ast_extractor / interpreter)
  - **ruff/mypy clean** + 기존 224 regression green 유지

  ## 방법론 — superpowers
  1. **writing-plans 스킬로 plan 먼저 작성**
     (`docs/superpowers/plans/YYYY-MM-DD-sprint-8c-user-function-3track.md`)
     - user function AST 수집 + call dispatch 설계
     - 3-Track classifier 기준 명시
     - 병렬 가능 항목 표시
  2. **ExitPlanMode로 사용자 승인** 받기
  3. **executing-plans 스킬로 task-by-task 진행** — TDD (test 먼저 → 구현 → verification)
  4. 각 task 완료마다 commit (체크포인트)
  5. Sprint 8b 관례대로 **외부 독립 리뷰 (Opus/Sonnet) 교차 hardening** 단계 포함
     — 완주 직후 공통 gap 추출 후 보강

  ## 브랜치 전략
  - **새 브랜치 권장:** `feat/sprint8c-user-function-3track` (main에서 분기)
  - 이유: Sprint 8b(15 commits)는 이미 자연스러운 완결 단위. 새 작업을 별도 PR로
    분리하면 리뷰 부하 감소 + 롤백 범위 명확.
  - Sprint 8b PR은 차기 세션에서 별도로 생성 또는 그대로 보존.

  ## 선택지 제시 시 **별점 추천도 필수** (메모리 규칙 참조)
  `| 추천도 | 옵션 | 이유 |` 형식 테이블.

  ## 참조
  - 메모리: [Sprint 8b 완료](project_sprint8b_complete.md) — 구현 + hardening 상세
  - 메모리: [스프린트를 너무 짧게 끊지 말 것](feedback_sprint_cadence.md) — 묶어 진행 선호
  - Sprint 8b plan: `docs/superpowers/plans/2026-04-18-sprint-8b-tier1-rendering.md`
  - 아키텍처: `docs/04_architecture/pine-execution-architecture.md` (3-Track §336-363)
  - ADR-011: `docs/dev-log/011-pine-execution-strategy-v4.md`
    - §2.0 Tier-0 (user function, runtime 범위 A)
    - §2.1 Tier-1 (Alert Hook + 가상 strategy)
    - §13 Phase -1 amendment (H1 MVP scope)

  ## 시작 액션
  1. `git checkout main && git pull origin main` + `git log --oneline -5` 확인
  2. `git checkout -b feat/sprint8c-user-function-3track`
  3. writing-plans 스킬 invoke → plan file 작성
  4. 사용자에게 plan 승인 요청 (ExitPlanMode)
  5. 승인 후 executing-plans로 진입
```

---

## 세션 준비 체크리스트 (선택 사항)

새 세션 시작 전에 수동으로 확인:

- [ ] `git status` — working tree clean
- [ ] `git log --oneline feat/sprint8b-tier1-rendering ^main | wc -l` = 15
- [ ] `cd backend && source .venv/bin/activate && pytest tests/strategy/pine_v2 -q`
  로 224 tests green 재확인 (선택)
- [ ] Sprint 8b PR 생성 여부 결정 (이 세션 진입 전 별도 처리 가능)

새 세션에서 첫 메시지로 위 코드블록을 붙여넣고, `feat/sprint8c-user-function-3track`
브랜치 분기부터 시작하면 됩니다.
