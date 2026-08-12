# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 `_archived.md`, trigger 미도래 의도적 부활 가능 항목은 `_deferred.md`. 문서 경로 정합성은 `scripts/docs-audit.sh`로 검증한다.
> ★**tombstone (ADR-026 §5).** 본문이 가리키는 `_archived.md`(Resolved + stale 137건)·`_deferred.md`(부활 가능 8건)는
> 2026-08-06 문서 대개편에서 삭제됐다 — 원문 = `git show 0f0f0b06:docs/archive/refactoring-backlog/_archived.md`
> (`_deferred.md` 동일 경로). `_deferred.md` 내용은 본 문서 말미 「Deferred」 섹션으로 승격돼 있다.
> 그 뒤 강등분(2026-08-06 entry-set-divergence)의 본문 = `git show 23a9fcd4:docs/backlog.md`.
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정. `_deferred.md` 도 6-8주마다 재평가.

**작성일:** 2026-04-30
**최종 갱신:** 2026-07-26 (**dogfood-restore 스프린트** — 로컬 실사용 복원 + 3스프린트 누적 신뢰 작업 실화면 검증. **BL-465/467 Resolved** +
신규 **BL-466/468~472/474** + **BL-473 Resolved**(WS auth `expires` 창 — 라이브 체결 스트리밍이 통째로 죽어 있었다). ★**dogfood 가
P1 을 잡았다** — `_periodic_returns` 가 음수 자본을 안 걸러 파산한 실행에 **양수 샤프**가 붙었고(실측 -2179.68% 에 +0.029), **committed
Trust Layer baseline 이 그걸 담고 있었다**(s1_pbr 샤프 +0.600 · 소르티노 +2.349 on -536%). 코퍼스 5종 중 4종이 음수 자본이고 골든이 깨진 것도
정확히 그 4종. baseline 재생성 diff = 12 메트릭 키 중 2개 한정. ★**옵티마이저는 이 스택에서 구조적으로 죽어 있었다** — `optimizer_heavy` 유일 소비자에
OHLCV env 3종 부재. ★**`make seed` 신설** — 백테스트 1회가 곧 OHLCV 시딩(TimescaleProvider cache-first). 마이그레이션 0.) // 이전:
2026-07-26 (**money-path-finish 스프린트** — BL-457/454 Resolved + BL-458 부분 Resolved + **신규 BL-464**. 머니-패스 정확도
마감 팩. ★**실측이 BL-457 의 '권장 접근' 을 반박** — `attribution_facts` 재사용은 진짜 우리 청산을 external 로 뒤집는다(백로그 본문에서 제자리 정정).
★**백로그에 없던 결함 발견(BL-464)** — `attribute_exit` 이 거래소 원문↔canonical 심볼을 비교해 `inferred` 귀속이 구조적으로 죽어 있었고, **픽스처
기본값이 그걸 한 스프린트 동안 가렸다**. ★`format:check` 는 이 레포의 통과 가능 게이트가 아님을 실측 확인(선재 356 red). 마이그레이션 0.) // 이전:
2026-07-25 (**exit-money-path 스프린트** — BL-444/445 Resolved + BL-453 부분 Resolved + 신규 BL-454~458. 세션 스코프 머니-패스
정정(Site 3·4). ★§0.5 실측이 BL-438 ② 를 "미룸" 이 아니라 **"현재 데이터로는 정직하게 구현 불가"** 로 재분류 — bracket/trailing 0행 ·
matched/attributed 0행. ★대조군 판별력을 프로덕션 stash 로 실제 증명. ★active BL 카운트 산식을 헤더에 박아 stale 재발 차단.) // 이전: 2026-07-25
(**exit-attribution 스프린트 + 범위 축소 + dogfood 완주** — BL-438 부분 Resolved(관측 원장, **최근 7일**) + BL-442 Resolved + 신규
BL-443~453. 거래소 청산 원장 신설 + 스윕 계정 독립 열거. ★과거 90일 catch-up 기계장치는 머지 전 축소로 걷어냄 → BL-452. ★로컬 개발 DB 전소 사고 → BL-451
가드. ★dogfood 실측이 알림 크래시 진짜 P1 을 적발·수정 → BL-453 예방 등재.) // 이전: 2026-07-25 (**close-completeness 스프린트** —
BL-435/436 Resolved + BL-434 부분 Resolved(display) + 신규 BL-437(스윕 이연). 청산 즉시 flat + margin 503 회피 + 완전 TP/SL
보고.) // 이전: trading-surface-pack — BL-431/416/425/432/433 Resolved + BL-434~436.
**직전 갱신:** 2026-07-24 (**trading-surface-pack 스프린트** — BL-431/416/425/432/433 Resolved + 신규 BL-434~436. 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 완성.)
**현재 상태:** **집계 수치를 여기 박지 않는다** — 정본은 `bash scripts/bl-audit.sh` 이고, 그 스크립트는 `scripts/final-gates.sh` 게이트 체인 안에 있다(라벨 `BL 감사`, BL-564). 숫자가 필요하면 **그 자리에서 재라.** 문서에 박은 수치는 BL 하나만 추가돼도 즉시 stale 이고, 이 줄은 실제로 여러 스프린트 동안 stale 이었다. **BL-070~075 milestone active 승격** (deferred → P0 prep).

> ★이 수치는 손으로 세지 말고 기계적으로 재라 — 직전까지 "49 active" 로 여러 스프린트 동안 stale 했고, 그 다음 표기 "86 active / 전체 135" 도 실측(217 섹션)과 어긋나 있었다. **산식은 이제 문서 주석이 아니라 스크립트다:**
>
> ```bash
> scripts/bl-audit.sh                   # 판정 + P별 내역 + 3면 불일치 + UNKNOWN 목록
> #                                       UNKNOWN · 3면 불일치 · 중복 상태줄 · 중복 섹션 헤더 · 미닫힌 펜스/<details> → exit 1
> scripts/bl-audit.sh --list ACTIVE     # 트리거가 **도래한** 것 전량 (★목록 전용 — 항상 exit 0, 게이트에 쓰지 마라)
> scripts/bl-audit.sh --list DEFERRED   # 트리거 **미도래**로 대기 중인 것
> scripts/bl-trigger-sweep.sh --selftest  # ★도래 판정기의 판별력. 전량 스윕보다 **먼저** 돌려라
> ```
>
> ★**2026-08-10 부터 판정어가 다섯이다** — `ACTIVE / DEFERRED / PARTIAL / RESOLVED / UNKNOWN`([ADR-028](decisions/028-backlog-deferred-verdict.md)). `DEFERRED`(상태줄 `⏳ **대기 (트리거 미도래)**`)는 🟡 와 마찬가지로 **active 로 세지 않는다.** 종전에는 「조건이 아직 안 왔다」를 적을 낱말이 없어 열린 항목이 **전부 ACTIVE** 로 떨어졌고, 그래서 ACTIVE 159 는 작업량이 아니라 **셈하는 규칙이 만든 수**였다(전량 판정 후 **9**). 미도래의 경계는 **외생 조건**(사용자 승인·cutover·Beta·소크·외부 관측·미해결 선행 BL)**과 동승 조건**(「그 파일을 다음에 열 때」류 — 단독 착수 시 값이 0이라고 트리거 자신이 선언한 것) **둘 다**를 포함한다. 3면에서 DEFERRED 는 **ACTIVE 와 같은 「미완」 쪽**이다. 각 섹션의 `**트리거 판정:**` 줄이 **무엇이 막는지**를 적는다.
>
> ★**낡은 산식(인라인 awk)은 폐기했다.** 그것은 "섹션 본문 어딘가에 `Resolved` 문자열이 있으면 RESOLVED" 였고, 그래서 **cross-ref 한 줄이 항목을 지웠다** — `BL-003`(P0, 열려 있음)이 자기 섹션의 `BL-004 ✅ Resolved` 두 줄 때문에 RESOLVED 로 집계돼 **공식 산식이 P0 active 를 0 으로 보고하고 있었다**(BL-499·BL-535 도 같은 뿌리). 새 산식의 SSOT 는 각 섹션의 `**상태:**` / `**Status:**` **줄 하나**이고, 근거가 없으면 추측하지 않고 **UNKNOWN 으로 남긴다**. 🟡 부분 Resolved 는 종전대로 active 로 세지 않는다.

**최근 sprint BL 변경 (Sprint 55~Sprint 62 Beta 진입):**

- **2026-07-25 close-completeness 스프린트 (codex G0 REJECT→개정 + 2-generator ∥ + Claude 적대평가 per-worker + codex 최종
  diff + Opus dogfood 3계통)**: trading-surface-pack(#473) 후속. 청산/TP-SL 완성도 3건. **BL-435 Resolved**(즉시 flat =
  post-fill Celery 캐시 DEL, accept-time DEL 은 async close 라 무효) + **BL-436 Resolved**(청산 create_order 가
  reduce_only 시 set_margin_mode/set_leverage skip = margin 503 회피, ccxt marginMode 신뢰불가 우회) + **BL-434 부분
  Resolved**(완전 TP/SL 보고 display = fetch_open_conditional_orders 2콜 union+orderId dedupe+stopOrderType 엄격분류 →
  §03 병합 리스트 + has_trailing_stop 각주; **스윕은 BL-437 이연**) + hedge positionIdx 409 가드. 마이그레이션 0. 게이트: BE
  **2611**(+10) / FE **1084**(+1) / canon **32 불변** / ruff·mypy·tsc·lint 0 / alembic 무변경. **검증 체인**: codex G0
  = **REJECT**(전건 코드 대조 §7.3 후 개정 — B2 skip 전환·B1 post-fill DEL·B3 union dedupe·trail=position 필드·hedge 가드) →
  사용자 재인터뷰(스윕 이연·트레일링 각주) → codex 2워커 생성 ↔ Claude 적대평가(W1 ruff B023×3+mypy → codex resume hoist) → codex 최종
  diff([P1] has_trailing_stop 조건부 trail 해소+테스트) → **dogfood 3계통**(독립 오라클 raw ↔ 앱 provider
  fetch_open_conditional_orders(66000/62000 정확 분류·count=2 dedupe) ↔ get_reconciliation 병합 + **authed
  브라우저**(§03 병합·청산 flat·콘솔 0) + B1 redis 키 부재 + B2 no-503 + Bybit Partial 자동취소 실증). **★docker 포트 오버레이
  함정**(plain `docker compose up <svc>` 이 db/redis 를 base 5432/6379 로 되돌림 → `--no-deps` 필수). 신규 **BL-437**.
- **2026-07-24 trading-surface-pack 스프린트 (codex 2-generator ∥ + Claude 적대평가 per-worker + Opus dogfood)**:
  position-cockpit(#472) 후속. 코크핏 §03 포지션 표에 TP/SL 열 + reduce-only 시장가 청산 완성 + 부채 4종. **BL-431 Resolved**(BE:
  포지션-보고 TP/SL read-time 0→null 정규화 + `POST /live-sessions/{id}/positions/close` reduce-only 청산 = 신규
  `close_service.py` + `OrderService.execute(flatten=True)` 진입-위험 가드 ②~⑧ bypass·ownership 유지·reduce_only
  불변식·**청산 leverage=포지션값**으로 set_leverage no-op·cap-bypass 방지 / FE: 익절·손절 2열 + 청산 액션·확인 모달(정직 고지)·colSpan 14) +
  **BL-416 Resolved**(주문취소 행별 disabled `cancelOrder.variables` + 비-409 broad toast + 실 ACTIVE_ORDER_STATES
  import) + **BL-425 Resolved**(alert-rule 중복 유형 사전검사 = 마운트 목록 재사용, 409 요청·콘솔 노이즈 회피) + **BL-432
  Resolved**(positions select→combine 인덱스 zip + 고아 삭제) + **BL-433
  Resolved**(`qb_ws_subscribe_rejected_total{account_id}` counter). 마이그레이션 0. 게이트: BE **2601**(+18) / FE
  **1083**(+8) / canon **32** / authed **66**(+2 코크핏 §03 구조) / build ✓ / alembic 무변경. **검증 체인**: codex G0
  14건(코드 대조 후 반영, BLOCKING 3=leverage 라우팅·flatten 불변식·hedge 거부) → codex 2워커 병렬(backend/frontend 교집합 0) ↔
  Claude 적대평가 per-worker(게이트 직접 실행, W1 RUF059 1건 codex resume) → 최종 codex 누적 diff(MAJOR 1=청산 leverage
  cap-bypass → 포지션값 사용 fix) → **Opus dogfood 2계통**(독립 Bybit HMAC 오라클 ↔ 코크핏 §03: TP/SL 값 66000/62000 정확 일치·빈값→—
  정직 / 청산 종단 flat+Order row / **kill-switch 활성 청산 성공 = 가드 bypass 실증, KS 미소비** / 콘솔 error 0). 신규
  **BL-434~436**.
- **2026-07-23 functional-parity 스프린트 (codex 4-generator ∥ + Claude 적대평가 + Opus dogfood)**: C 디자인 이식 후 기능 격차
  마감. **BL-401 Resolved**(3폼 `formState.errors` → `.field-error` 프리미티브, superRefine 평탄 경로 row 매핑, 메시지 한국어화 —
  grid min>max 만 거부로 BE 계약 정합) + **BL-411 Resolved**(지원 kind 목록 `OptimizationKind` enum 파생 + Sprint 넘버 문구 중립화) +
  **BL-402 Resolved (구조 소멸)** — C 이식이 4사이트 전부 네이티브 `<select>` 로 재작성해 uncontrolled/raw-UUID 결함 자체가 소멸(실측 재확인,
  코드 변경 0). 신규 A2(주문취소 액션 열 — "API 없음" 미렌더 전제가 거짓이었음, CF4 완비)·B2(orders state 반복 Query + 미체결 nav-count 캐논 §4.6
  복원)·B1(strategy.backtest_count read-time GROUP BY, COMPLETED 기준)·A7-lite(스트레스 최신 결과 리로드 복원)·A1(대시보드 전략 링크
  404→edit). 게이트: vitest 965→980 / BE 2416+18 / canon 32 불변 / authed 56→62. 신규 **BL-413~416**. **Opus MCP
  dogfood(10항목)가 잠복 P1 2건 추가 발굴·동일 스프린트 해소**: (a) stress_test enum 혼합 케이싱 — 최초 migration 소문자 라벨 vs SAEnum 대문자
  저장으로 실 DB 에서 MC/WF 생성 전부 500 → RENAME VALUE migration `20260723_0001` + alembic-경로 enum 라벨 sentinel 테스트(즉시
  status enum 드리프트도 추가 검출). (b) provider cancel_order 전 구현이 ccxt 에 symbol 미전달 — 실거래소 취소가 전부
  ArgumentsRequired(CF4 fail-closed 로 submitted 영구 잔존, BL-404 동형) → Protocol+5 provider symbol 관통 + futures
  linear 정규화. dogfood 최종 V1~V10 전 항목 PASS (취소 200/202 실클릭 + DB 오라클 3점 + A7-lite 리로드 복원 실측).

- **2026-06-30 stress_test-deepen (deepen-modules)**: stress_test 도메인 1차 deepen (`/deepen-modules`, 코드 변경 0). C1 = **BL-363 sharpen**(money-path framing + git 실증 `6c7adfba`→`ffb2299b` + `_load_run_context`/`_execute_grid_sweep` 구체 인터페이스) / C2 = 신규 **BL-392**(CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합, untyped JSONB seam). 거부 = C3(`StressTestKind` dispatch registry — blast radius 최대 + 4타입 over-eng, 5번째 타입 등장 시 재평가) / C4(invariant SSOT — C2 graft 권장). engine 은 이미 `run_grid_sweep` 공유 = Deep 유지(건드리지 않음). dev-log `2026-06-30-stress_test-deepen.md`.
- **2026-06-30 backtest-deepen (verification loop)**: backtest 도메인 1차 deepen (improve-codebase-architecture + codex challenge, 코드 변경 0). 신규 **BL-387~391** (5건) — BL-387 sizing-canonical typed seam(P2 money-path) / BL-388 BacktestMetrics 4-site multi-SSOT(P2) / BL-389 finance-math `engine/metrics.py` 추출(P3) / BL-390 exit `fill_type` 중복 위임(P3) / BL-391 equity↔PnL reconciliation oracle(P3 test-first). codex KILL C3(idempotency dual-lock 통합 = 의도적 layered + 잘 테스트됨) → [ADR-021](decisions/021-backtest-idempotency-dual-lock.md). **codex C1 DOWNGRADE 는 phantom `metrics.py` 오인 → 직접 검증 후 KEEP 정정**(§7.3 circular-trust 차단). dev-log `2026-06-30-backtest-deepen.md`.
- **2026-06-30 BL-378 Resolved (`fix/pine-378-atr-wilder`)**: pine_v2 `ta.atr` 가 Wilder RMA (TV `ta.atr = ta.rma(ta.tr, len)`) 아닌 rolling SMA 사용 → 비-상수 TR(=모든 실데이터)에서 TradingView 와 silent divergence (헤드라인 harm-class). 실세계 8 전략 티어드 백테스트 QA (`docs/archive/qa/2026-06-30-pine-tiered-backtest/report.md`) 의 大-tier anti-circular hand-oracle 에서 발견 (5중 교차검증: codex G1 + 직접 oracle 9/9 bar + generator panel discriminator + panel 실행 15.0 vs 14.818 + codex G2). 수정 = `ta_atr` 가 기존 Wilder `ta_rma` 재사용 (~2줄, seed 동일·이후 TV 정합). G1-G4 (codex G1 plan eval + Workflow 12-agent generator panel + codex G2 challenge[B1 CONFIRMED] + codex diff-challenge[no P1] + G3 fresh review + mutation 2/2 CAUGHT) + full **2301 pass** (+6 pre-existing env, stash 대조 확인) + ruff/mypy clean + trust-layer golden 재생성(s2_utbot/i1_utbot num_trades 461→433, ATR→trailing 신호 변화). migration 0. 신규 **BL-379~386** (QA 부수 발견 9건: fn-local subscript / Track A alert warning / valuewhen na 등).
- **2026-06-30 BL-376 Resolved (`fix/pine-376-na-inf`)**: pine*v2 na/inf *소비\_ 사이트 robustness (BL-374 후속). 3 사이트 — (1) na/inf/<1 → ta.\* length: `_coerce_length` 헬퍼를 14 ta 함수 + dispatcher(change/stdev/variance int() 제거) + pivothigh/pivotlow 양 window + valuewhen occurrence(별도 non-finite 가드, occ=0 보존) 에 적용 → na 반환. (2) na/inf qty → `StrategyState.entry` skip + warning (라이브 reject 미러, 유한 0.0 보존). (3) inf → `math.floor/ceil/round`(per-branch, 공유 가드 미변경 — abs/sign/max 통과 유지) / subscript offset isfinite / timestamp +OverflowError. G1-G4(codex plan eval GO_WITH_FIXES + 4-candidate generator panel byte-수렴 + codex challenge[P1 valuewhen Decimal NaN 갭 → `(float, Decimal)` 가드] + fresh review SHIP + mutation 6/6 CAUGHT) + full suite 2305 pass(cov ≥90) + Playwright E2E(na/inf 백테스트 FAILED→COMPLETED, console.error 0). migration 0. 신규 [BL-377] (deferred: non-finite 주문/청산 가격 + 초대형 유한 length OverflowError).
- **2026-06-29 BL-374 Resolved (`fix/pine-374-na-semantics`)**: pine_v2 인터프리터 산술/math 도메인 오류 → Pine `na` 정규화 (`_na_safe`, 숫자 산술 한정, `math.pow` `**`→`math.pow()`). G1-G4 게이트(codex plan eval + 3-candidate generator panel + codex challenge[F1 dead stdlib-clamp 제거 + F2 문자열 `%` fail-closed] + fresh review GO + mutation 5/5) + full suite 2226 pass(cov 95.6%) + Playwright E2E(div-by-zero 백테스트 FAILED→COMPLETED, console.error 0). 신규 [BL-376] (deferred: na→length/qty, inf→floor·ceil·round).
- **2026-05-17 Sprint 62 PR #290 merge (Beta 본격 진입 결정 ★★★★★)**: 6 BL fix-first (BL-350+354 ★★★ Optimizer Zod resilience + BL-353 step 01 라벨 + BL-356/357/358/359 모바일 터치 ≥44pt 묶음). 실측 ~2-3h vs plan 6-8h (LESSON-067 6차 검증). main `36bb4e0`. **BL-070~072 milestone active 승격**. **재측정 skip + 본인 의지 (d) 통과**.
- **2026-05-17 Multi-Agent QA 재측정 (post-Sprint 61)**: Composite 6.08 → **7.5/10** (+1.42 목표 도달). 신규 BL-347~360 (14건, Critical 0 / P0 2 ★★★ 공통 BL-350+354 / P1 4 / P2 5 / P3 3). Sprint 61 11 BL Resolved 마킹 (PASS 8 + PARTIAL 2 + manual 1). 상세 = `integrated-report.html`.
- **2026-05-17 Sprint 61 PR #288 merge**: 11 BL fix (BL-310/311/312/319/322/323/327/328/339/340) source 적용 + hotfix PR #289 (BL-348/349). docs/archive/qa/2026-05-17/ baseline 별도.
- **2026-05-17 Multi-Agent QA 1차**: 신규 BL-310~346 (37건). 상세 = `integrated-report.html` + `sprint-61-plan.md`. 17 → 54 net.
- **Sprint 58** (2026-05-11~12): ✅ BL-241/242/243 Resolved (Pine TA 확장). 92 → 89 net.
- **Sprint 57** (2026-05-11): ✅ BL-234/237 Resolved (Optimizer Polish + heavy queue). 신규 BL-241~243. 91 → 92 net.
- **Sprint 56** (2026-05-11): ✅ BL-233 Resolved (Genetic). 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11): ✅ BL-232 Resolved (Bayesian). 신규 BL-233~237. 88 → 92 net.

**Sprint 59 트리아주 결과 (PR-D, 2026-05-13):** 158 BL → **13 Active** (본 문서 본문) + **8 Deferred** (`_deferred.md` — Beta 6 + BL-005 + BL-145) + **137 Archived** (`_archived.md` — Resolved + Sprint 16~30 stale).

**P0 / P1 active short list (Beta 본격 진입 prep):**

- **🚀 Beta 진입 milestone (BL-070~072) — active P0** (`_deferred.md` 에서 승격):
  - **BL-070** 도메인 + DNS + Cloudflare (사용자 manual 1-2h + DNS 전파 24h)
  - **BL-071** Backend 프로덕션 배포 (Cloud Run/Railway/Render + Postgres prod + Redis prod + Clerk production + 보안 헤더 gunicorn) — 2-4h. **BL-347 server strip 동시 처리** (gunicorn `--server_header False`).
  - **BL-072** Resend 이메일 + Waitlist 활성화 — 1-2h + 24h verify
  - BL-073/074/075 = 위 완료 후 자연 trigger (Twitter/X 캠페인 + Beta 인터뷰 + H2 진입 gate)
- **Sprint 62 Resolved (6 BL)** ✅:
  - BL-350+354 ★★★ Optimizer Zod resilience / BL-353 step 01 라벨 / BL-356/357/358/359 모바일 터치 ≥44pt 묶음
- **Sprint 61 Resolved (11 BL)** ✅ (요약): BL-310/311/312/319/322/323/327/328/339/340/348/349 (PASS 9 + PARTIAL 2 + manual 1)
- **Production deploy 시점 자동 해소 묶음** (BL-070/071 시점):
  - BL-320 Development mode 배지 / BL-321/352 Clerk application name / BL-347 server header / BL-261 Clerk custom domain
- **기존 P0**: BL-003 (Bybit mainnet runbook, H1 종료 gate — BL-073 캠페인 후 trigger)
- **잔존 P1/P2/P3** (Beta 본격 진입 후 polish 또는 dogfood 발견 시 trigger):
  - P1: BL-014/015/022/023/024/025/026 (**BL-308 은 2026-06-29 W3 Resolved — 이 목록에서 제거**)
  - P2: BL-186/190/195/235/236/309/313/314/315/316/329/330/332/344/345/351
  - P3: BL-306/307/317/318/324/325/326/331/333/334/335/336/337/338/346/355/360

> **신규 BL-347~360 상세**: `docs/archive/qa/2026-05-17-post-sprint61/integrated-report.html` §3 + 페르소나별 원본 보고서 4종.
> **Beta 진입 milestone 상세**: `_deferred.md` BL-070~075 섹션.

---

## 분류 차원

### Priority

| 라벨   | 의미                                               | 예시                                                      |
| ------ | -------------------------------------------------- | --------------------------------------------------------- |
| **P0** | dogfood-blocker / H1 종료 gate                     | submitted watchdog, mainnet runbook, 본인 1~2주 dogfood   |
| **P1** | risk-mitigation / 알려진 broken bug 패턴 재발 위험 | commit-spy 도메인 확장, Redis lease, Auth circuit breaker |
| **P2** | hardening / nice-to-have 가 아닌 "건강도" 작업     | cardinality allowlist, dogfood 통합 dashboard             |
| **P3** | nice-to-have / 컨벤션 정합 / 미래 path             | zod import 정정, Path γ/δ                                 |

### Trigger 유형

- **time-based** — Sprint N+ / Q2 / H2 말 등 시점 명시
- **event-based** — "after dogfood week 1", "Beta 5명 onboarding 후" 등 외부 사건
- **dependency-based** — 다른 BL 또는 외부 자원 (예: Bybit mainnet API key) 후
- **on-demand** — 특정 PR / sprint 안에서 발견 시 즉시

---

## P0 — Dogfood / H1 종료 blocker

| ID                | 제목                                                                                                                                                                                                                                                                                                     | Trigger              | Est      | 출처                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------- | -------------------- |
| [BL-003](#bl-003) | 🟡 부분 해결 — Bybit mainnet 진입 runbook + smoke 스크립트. **2026-08-09 산출물 축 닫힘**(runbook·`bybit-smoke.sh`·시크릿 절차) · **Trigger 축 열림**(`soak-gate.sh` C1 26.54h/168h). ★본문 「소액 $10~50」·「base URL 매핑 필요」·「smoke 신규」·「별도 secret manager」 **4건이 코드 대조로 반증**됐다 | H1 Stealth 종료 직전 | M (4-5h) | 2026-04-30 TODO 이력 |

> 추가 P0 — BL-005 본인 dogfood + BL-145 EffectiveLeverageEvaluator (deferred). Resolved P0 = BL-001/002/004 (`_archived.md`).

### BL-003

**Title:** Bybit mainnet 진입 runbook + smoke 스크립트
**Category:** Tooling / Infra
**Priority:** P0 (H1 Stealth 종료 직전)
**Trigger:** Bybit Demo 1주 안정 운영 후 + BL-004 완료 후 (BL-004 = 완료, Sprint 28). ★**「1주 안정 운영」은 2026-08-05 부터 기계가 판정한다** — `scripts/soak-gate.sh` 가 PASS/FAIL/UNKNOWN 을 내고 **PASS 만 exit 0** 이다. 술어·창·리셋 규칙 = [ADR-024](decisions/024-soak-stability-gate.md).
**Est:** M (4-5h)
**출처:** [2026-04-30 당시 `docs/TODO.md`의 mainnet 준비 항목](https://github.com/woosung-dev/quantbridge/blob/b2c1541054326b06acf5e64f25094b6d5a37ea10/docs/TODO.md#L650-L653)

**원인 / 영향:** dogfood 가 Bybit Demo 만으로는 H1 종료 gate 충족 안 됨. mainnet 전환 시 수동 step 누락 위험 (IP whitelist / 출금 권한 차단 / 레버리지 1:1 / 소액 시작).

**권장 접근:** ★★★**2026-08-09 에 이 3줄 중 4건이 코드 대조로 반증됐다** — 아래 「반증」 표를 먼저 읽어라.

1. ~~Trigger 충족 시 당시 Bybit 정책·계정 모드에 맞춘 mainnet runbook 신규 작성~~ → **2026-08-09 작성 완료**
   = [`bybit-mainnet-runbook.md`](reference/operations/bybit-mainnet-runbook.md). ★**Trigger 를 기다리지 않았다** —
   Trigger 가 막는 것은 산출물의 **실행**이지 **작성**이 아니다.
2. ~~`scripts/bybit-smoke.sh` 신규~~ → **2026-08-09 신규 + 기존 파이썬 재사용**(`bybit_demo_smoke.py` → `bybit_smoke.py`).
3. ~~`.env.production` 별도 secret manager + rotation 절차~~ → **2026-08-09 절차 확정**(runbook §3).
   보관처는 **오라클 서버 파일 단독**(사용자 결정) — `.env.prod.example` 이 전제하던 GCP Secret Manager 는 **현실과 어긋나 있었다**.

**의존성:** BL-004(완료, Sprint 28 PR #108).

**Status:** 🟡 **부분 해결 — 산출물 축은 닫혔고 Trigger 축은 열려 있다** (2026-08-09 bl003-mainnet-runbook).
★상태줄 어휘는 `bl-audit.sh:75-79` 의 `verdict_of` 가 읽는다 — `lead()` 가 `—` 앞까지만 자르므로
**「부분 해결」을 그 앞에 둬야** PARTIAL 로 판정된다(「부분 —」 로 쓰면 UNKNOWN 이 된다, 2026-08-09 실측).
★**「P0 가 전진했다」로 읽지 마라.** 이 항목의 완료는 두 축이고 이번에 닫힌 것은 ⑴뿐이다 —
⑴ **산출물**(runbook + smoke + 시크릿 절차) = **닫힘** · ⑵ **Trigger**(`soak-gate.sh` PASS) = **열림**
(2026-08-09 실측 C1 **26.54h/168h = 15.8%** · C2 15.30h/24h · 실격 0 · 24h 도달 **0/39**).
쓸 수 있는 문장은 **「게이트가 열릴 때 4~5h 를 더 기다리지 않아도 되게 만들었다」**다.
(위 두 줄의 BL-004 는 **참조**다 — 이 항목의 상태가 아니다. 이 구분이 없어서 낡은 산식이 BL-003 을 RESOLVED 로 세고 **P0 active 를 0 으로 보고했다.**)
**트리거 판정:** 미도래 — 소크 축. 2026-08-11 게이트 실측 `rc=2 UNKNOWN` · C1 **68.2197h**/168h · 24h 이상 창 **1/3**(15.30h · 0.01h · 52.91h). PASS 만 도래다([ADR-024]). ★사용자가 문턱을 「누적 24h × 3회」로 교체했지만 그 새 문턱으로도 1/3 이라 결론이 같다 (2026-08-11 bl-703-partial-verdicts)

**산출물 (2026-08-09):**

| 파일                                                                                                  | 무엇                                                                                           |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [`docs/reference/operations/bybit-mainnet-runbook.md`](reference/operations/bybit-mainnet-runbook.md) | 전제조건 · cutover 2곳 · 시크릿 · Kill Switch 표 · 2단계 진입 · **rollback** · [확인 필요] 5건 |
| `scripts/bybit-smoke.sh`                                                                              | 정문. `--dry-run` 기본 · **그 경로 네트워크 호출 0건**(정적+동적 대조) · fail-closed 검사 6종  |
| `backend/scripts/bybit_smoke.py`                                                                      | `bybit_demo_smoke.py` rename. `--mode live` · `--market spot` · credentials **env 전용**       |
| `backend/.env.prod.example` · `.env.example`                                                          | `KILL_SWITCH_*` mainnet 값 · `BYBIT_SMOKE_*` · 보관처 문구 교체                                |

**★★★반증 (2026-08-09 — 이 회차의 최대 산출):**

| 본문/코드 주석이 말한 것                                                           | 실측                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 「BybitDemo/Futures **base URL mainnet 매핑**」이 할 일 (`providers.py:2256-2257`) | **이미 있다.** `_apply_bybit_env`(`providers.py:2202-2210`)가 demo → `enable_demo_trading(True)` · **live → no-op(`api.bybit.com`)** 로 이미 가른다. 축은 `Credentials.environment`(`:108-109`) ⇒ **provider 본문을 새로 쓸 일이 없다**(단 「cutover 는 2줄」은 **아래에서 다시 반증됐다 — 6곳이다**) |
| 소액 **$10~50** 시작                                                               | **그 자본으로는 세션이 주문을 0건 낸다.** 사이징은 자본 비례(`strategy_state.py:503-506`)이고 서버 실측 자본 190,034 USDT → 주문 0.058 BTC ⇒ `X_min = 190,034 × (0.001/0.058) ≈ **$3,276**`. ★BTC 가격도 pct 도 **소거된다**(비율만 쓴다)                                                             |
| `scripts/bybit-smoke.sh` **신규**                                                  | 뼈대가 **이미 있었다** — `backend/scripts/bybit_demo_smoke.py` 221줄·6단계. 신규는 셸 래퍼뿐이다                                                                                                                                                                                                      |
| `.env.production` **별도 secret manager**                                          | `backend/.env.prod.example` 이 **이미 존재**했고 GCP Secret Manager 를 전제로 쓰여 있었다 — 그런데 **실제 배포는 오라클 docker compose** 다. 신규 작성이 아니라 **현실과 맞추는 개정**이 답이었다                                                                                                     |
| smoke = **「1 USDT limit-order」**                                                 | **불가능하다.** 2026-08-09 `load_markets` 실측 — spot `BTC/USDT` 의 **`min_cost = $5.0`** 이 진짜 하한이다(`min_amount` 1e-06 은 무의미). 본문은 그 제약을 모르고 쓰였다                                                                                                                              |

**★min_qty 실측으로 §8 [확인 필요] 1·2 를 닫았다 (2026-08-09, 공개 `load_markets` · 인증 없음 · 주문 없음):**

| 심볼            | type | `min_amount`  | `min_cost` | 최소 명목(BTC $64,957) |
| --------------- | ---- | ------------- | ---------- | ---------------------- |
| `BTC/USDT`      | spot | 1e-06         | **$5.0**   | **$5**                 |
| `BTC/USDT:USDT` | swap | **0.001 BTC** | (없음)     | **$64.96**             |

★★★**가정을 확인하러 간 조회가 확인 밖의 것을 고쳤다** — `min_qty = 0.001` **[가정]은 맞았지만**,
같은 조회가 ⑴ 내가 쓴 「perp 명목 ~$100」을 **$65** 로 정정하고(BTC 를 $100k 로 어림했다)
⑵ 본문의 「1 USDT limit-order」를 반증하고 ⑶ 셸 spot 기본 수량 0.0001(=**$6.5**, 하한 $5 에 너무
가깝다)을 **0.0002**(=$13)로 올리게 했다. **맞은 가정을 확인하는 것도 값을 낸다.**

★★**$3,276 이 독립 검증됐다** — 원래 식은 비율만 써서 가격을 **안 쓴다**. 그런데 가격을 넣어
명목 비율로 다시 세면 같은 답이 나온다: 데모 `0.058 × 64,957 / 190,034 = **1.98%**` ·
mainnet `0.001 × 64,957 / 3,276 = **2.0%**`. 산수 실수가 있었다면 여기서 어긋났을 것이다.

**★부수 발견 (수리했다):**

- `bybit_demo_smoke.py` 가 **`mode` 인자를 받고도 쓰지 않고** `enable_demo_trading(True)` 를 하드코딩했다.
  choices 가 `demo` 뿐이라 무해했지만, live 를 여는 순간 **「live 를 지정했는데 demo 로 간다」**가 된다.
- credentials 를 **argv 로** 넘기고 있었다(`--api-key`) — 같은 호스트의 아무 프로세스나 `ps` 로 읽는다.
  demo 키에선 무해, mainnet 실키에선 아니다 ⇒ **env 우선 + argv fallback** 으로 교체.
- ★**runbook 초안의 rollback 명령이 틀렸다** — `stop`/`flatten` 은 `session_id` 가 **positional** 이고
  `--confirm` 이 **required** 다(`live_session_admin.py:409-415`). `--session-id` 로 적었다면 **실자금
  rollback 이 그대로 실패**했을 것이다. 인용 17건 전수 대조로 잡았다.
- ★**내 셸 검사 하나가 죽은 코드였다** — `case *[![:print:]]*` 는 이 맥의 UTF-8 로케일에서 한글을
  **print 로 보고 통과**시켰다. 실제로 잡은 것은 `LC_ALL=C grep` 쪽이다(음성 대조 6/6 으로 확인).
- ★**내 테스트 도구가 한 번 거짓말했다** — zsh `MULTIOS` 가 `2>&1 >/dev/null` 를 **양쪽으로** 보내
  stdout 이 stderr 인 것처럼 보였다. stderr 를 파일로 받아 재측정.

**★★★codex 적대 리뷰가 내 runbook 의 핵심 주장을 반박했다 (7건 제기 · 7건 전부 코드 재현):**

지난 2회차에서 codex 는 **산출물 0**(파일만 읽고 exit 0)이었다. 이번엔 스펙에 **출력 형식을 강제**하고
「주장 6개를 하나씩 반증해라」로 표적을 좁혔더니 4,518B 를 냈다. **계약을 바꾸니 결과가 바뀌었다.**

| #   | 급  | 무엇                                                                                                                                                                 |
| --- | --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | P0  | **`close_service.py:92` 가 live 를 `422 live_mode_stub` 으로 거부** ⇒ runbook §7 **rollback 이 실자금에서 실패**한다. **나갈 문이 없는 채로 들어갈 뻔했다**          |
| 2   | P0  | `close_service.py:100-104` 는 **포지션만** 보고 조건부 주문을 안 본다 + CLI 가 그 409 를 **성공으로 출력**(`live_session_admin.py:383-387`) ⇒ 신규 [BL-661](#bl-661) |
| 3   | P1  | `live_signal.py:3383` 이 live 계정을 **평가에서 skip** ⇒ 세션을 열어도 **신호·주문 0건**                                                                             |
| 4   | P1  | 파이썬이 `--api-key` argv 를 여전히 수용 ⇒ 셸에서 **live 일 때 거부**로 막았다                                                                                       |
| 5   | P2  | 값 없는 `--mode` 가 **무한 루프**(`shift 2` 실패를 `set -e` 없이 삼킨다) — 실측 rc **124**                                                                           |
| 6   | P2  | `REPLACE_ME` 가 플레이스홀더 검사를 **통과**(rc 0) ⇒ 패턴 추가 + **영숫자 16자** 구조 술어 병행                                                                      |
| 7   | P2  | 「dry-run 외부 호출 0건」이 **부정확한 술어** — `stat`·`sed`·`grep` 은 돈다 ⇒ **「네트워크 호출 0건」**으로 교체                                                     |

★★★**그 결과 「cutover 는 2곳」이 반증됐다 — 실제로는 6곳이다.**
`grep -rn "ExchangeMode.demo" backend/src/` 전수: `live_session_service.py:115` ·
`live_signal.py:3383` · `close_service.py:92` · `position_service.py:332` · `:427` (+`registry.py:43-44`).
★**진입 자물쇠(⑵⑶)와 출구 자물쇠(⑷)가 다르다** ⇒ runbook 에 **「⑷ 를 먼저 풀어라」** 순서 규약을 넣었다.

★**부수로 하나 더 반증됐다** — 「registry stub 이 안전장치다」도 **거짓**이다.
`BybitFuturesProvider()` 를 **직접 생성**해 registry 를 우회하는 자리가 **13곳**이고
(`grep -rn "Bybit\(Futures\|Demo\|Live\)Provider()" backend/src/` → 14줄 중 1줄은 주석),
호스트를 정하는 것은 클래스가 아니라 `Credentials.environment` = **`account.mode`**
(`account_service.py:92`)다. stub 이 지금 무해한 이유는 「stub 이 막아서」가 아니라
**「세션·평가 게이트가 live 계정을 통과시키지 않아서」**다.

**남은 것 (cutover 회차의 일):**

1. **Trigger** — `soak-gate.sh` PASS. 이 축은 시간이 답한다.
2. runbook §8 의 **[확인 필요] 5건** — 특히 `min_qty = 0.001 BTC`([가정]). §6 의 $3,276 이 여기 걸려 있다.
3. cutover 코드 2곳 + 그때 red 가 될 테스트 2건(`test_live_session_commits.py:270,306` ·
   `test_demo_stability_gate.py:100-108`). **「고쳐야 할 red」이지 회귀가 아니다.**
4. `app_env=production` ↔ `soak-gate.sh` 무인증 조회 충돌(2026-08-07 실측) — 같은 API 인스턴스에서
   둘을 돌릴 계획이면 선행 과제다.

**게이트 현황 (2026-08-05 conditional-stop-ownership 재측정):** `scripts/soak-gate.sh` = **FAIL** (exit 1) — 누적 **0h / 168h**. ★**차단자 [BL-595] 를 이 회차에 수리했다**([ADR-025]) — 라이브 조건부 진입 체결의 권한을 주문 원장으로 옮겼고, 사망 **5건 전량을 얼려 재현**(영속 보고서와 비트 단위 일치)한 뒤 수리 전 5/5 `direction` 발산 → 수리 후 5/5 일치를 보였다. ★**착수 중에 소크 세션 `a16aa640` 이 죽었다**(08-05T09:12:53Z, 생존 8.642h) — 5번째 사망이자 워커 로그가 남은 유일한 건이라 오라클을 거래소 실측으로 교차검증하는 데 썼다(3/3 일치). 기저율 재측정: [BL-590] 이후 노출 **18.831h 에 자동 사망 3건 = 0.159/h(MTBF 6.3h)** · `phantom` 6건 = 0.319/h. ★★codex 가 **「가장 오래 산 세션에서 보호가 먼저 꺼지는」** 경로를 잡았다 — 원장 조회가 세션 스코프 + 상한 200 이라 체결 2.55건/h 로 **약 78시간**이면 영구 판정 불가가 된다(이 항목의 168h 누적 경로에서 정확히 밟는다). 재생 창 스코프로 바꿔 닫았다.

**이전 게이트 현황 (2026-08-05 divergence-rejudgement):** C3 **3건**(`cc19abd2` phantom 2 + auto_death 1), 소크 세션 `a16aa640` · 커밋 `f5f06886`. ★★★**실제 차단자는 달력 시간이 아니라 「엔진과 거래소가 서로 다른 stop 주문을 든다」는 것 — 신규 [BL-595]**. 사망 4건 부검에서 **엔진이 앞선 3건 · 거래소가 앞선 1건**으로 방향이 갈렸고, 킬 정책 교체([BL-591] 슬라이스 B)로 살아났을 세션은 **0개**다. ★★**판별식 교체 — 봉경계식 → 재무장 도장식**([ADR-024] §판별식 교체): 19건 전량 재적용 시 phantom **11→7**, 사망 상관 **4/4 보존**, **판정은 여전히 FAIL**(교체가 통과를 사지 않는다). ★아카이브에 판(版)을 실었다 — 안 그러면 취소된 라벨이 영원히 남는다. ★★★**과거 56.44h 는 소급 인정하지 않는다**(귀속 가능 0.46%) · **역대 2위 8.65h 는 마지막 46.7분 평가 정지** ⇒ 「역대 최장 15.3h = 9%」는 두 겹 낙관이었다.

---

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Trigger                                                                      | Est      | 출처                             |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------- | -------------------------------- |
| [BL-014](#bl-014) | 🟡 부분 Resolved — Partial fill `cumExecQty` tracking (잔여 = BL-439/440/441)                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 🟡 2026-07-25 `stage/money-path-accuracy`                                    | M (4-5h) | TODO.md L709                     |
| [BL-015](#bl-015) | OKX Private WS                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Bybit Demo 안정화 후                                                         | M (6-8h) | TODO.md L710                     |
| [BL-022](#bl-022) | ✅ golden expectations 재생성 — **Resolved** (2026-08-07 backtest-fidelity). `backend/scripts/regen_golden.py` 신설(`--confirm`/`--case`/`--check`). ★이 스크립트가 없었던 것이 [BL-621] stale 의 직접 원인이다                                                                                                                                                                                                                                                                                                                        | pine_v2 `strategy.exit` 도입 후                                              | M (3-4h) | TODO.md L17 (skip #1)            |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Trust Layer v2 검토 시                                                       | M (5-6h) | TODO.md L23 (skip #16)           |
| [BL-024](#bl-024) | real_broker E2E 본 구현 (nightly cron)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Bybit Demo credentials + seed data 준비 시                                   | L (8h+)  | CLAUDE.md Sprint 10 Phase C      |
| [BL-025](#bl-025) | ✅ autonomous-parallel-sprints 스킬 patch                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | on-demand (BUG-1/2/3 재발 시)                                                | S (2h)   | TODO.md L653                     |
| [BL-026](#bl-026) | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Stage 2c 2차 fixture 활성화 후                                               | S (1-2h) | TODO.md L20-22                   |
| [BL-619](#bl-619) | 🟡 부분 — ★**라이브 파이프라인이 한 세션에 ~17분 멈췄고 뿌리를 모른다.** 관측 장치는 2026-08-08 에 서버로 올렸다(systemd user unit `soak-logs-follow`, 실측 active·871KB·세션 `a4f1cbfb` 로그 유입). ★그것은 Trigger 를 **충족 가능하게** 만든 것이지 뿌리를 안 것이 아니다 — 닫는 조건은 재관측 부검 그대로다                                                                                                                                                                                                                         | 다음 서버 소크 창에서 같은 정지가 관측되면 (로그가 남아 있는 동안 즉시 부검) | M        | 2026-08-08 bl003-unblock         |
| [BL-633](#bl-633) | ✅ **이중 호스트 오염 — 근인 확정** — 같은 Bybit demo 계정의 맥 로컬 체결이 서버 세션 `39484a2c` 를 죽였다. G-A4‴ 소유권 7/27(귀속 불가 0)·G-A6′ 정본 항등식 4/4(반사실은 정의 4가지 어디서도 4/4 불가, 최대 1/4)·G-A7 계정 결합 27/27 이 뒷받침한다. ★원안 G-A4′ 6/6·G-A6 3/3 은 회차 도중 반증돼 교체됐다. `phantom` 은 증상이며, 오염 창은 ADR-025 의 반례로 셀 수 없다                                                                                                                                                             | — (부검 완료 · 후속은 BL-634 · BL-641 로 이관)                               | M        | 2026-08-08 bl003-unblock         |
| [BL-634](#bl-634) | ✅ **`register()` 전제조건 가드** — 같은 Bybit demo 계정에 두 호스트가 동시에 붙는 계정 배타성 가드 부재 — 두 DB 의 `live_signal_sessions` unique index 는 다른 호스트를 막지 못하며, 이번 `position_divergence` 사망의 직접 원인이다                                                                                                                                                                                                                                                                                                  | 실자금 전환 전 필수 / 두 번째 호스트를 다시 띄우기 전                        | M        | 2026-08-08 bl003-unblock         |
| [BL-635](#bl-635) | ✅ **게이트 아카이브 오염이 라이브 기전이다** — 판독 불가 로그를 시간 credit 하지 않고 `UNKNOWN 측정불가`로 내리도록 `32ea2a5d` 에서 수리했다. 서버 systemd 만 대상이며 맥 launchd 타이머는 잔여다                                                                                                                                                                                                                                                                                                                                     | — (해결됨. 맥 launchd 잔여는 별도 후속)                                      | S        | 2026-08-08 bl003-unblock         |
| [BL-661](#bl-661) | 🟡 **`flatten` 이 「이미 flat」으로 exit 0 하는데 조건부 주문은 남는다** — 2026-08-10 거짓 성공 제거(보고 + exit 3), 취소는 [BL-669](#bl-669) 로 분리. `close_service.py:100-104` 가 포지션만 보고 미체결 조건부 진입을 안 본다. 운영 CLI(`live_session_admin.py:383-387`)가 그 409 를 **성공으로 출력하고 return** 한다 ⇒ 고아 조건부가 나중에 트리거된다. [BL-003] rollback 이 이걸 **문서로만** 방어한다                                                                                                                            | 실자금 전환 전 필수 / 조건부 진입 세션을 내릴 때                             | S        | 2026-08-09 bl003-mainnet-runbook |
| [BL-641](#bl-641) | 🟡 부분 — BL-003 의 실질 선행조건은 문턱이 아니라 **MTBF** 다. 층화 + 95% CI 를 [ADR-024] 에 등재하고 재측정 도구(`mtbf_stratified.py`)를 만들었다. ★★★**점추정을 인용하지 마라 — CI 가 2026-08-12 에도 전 쌍 겹친다**(MTBF 13.39h→24.17h 로 1.8배 올랐는데도 「올랐다」를 못 말한다). 결론이 서는 근거는 셈이다: **24h 도달 1건/40세션 · 최장 65.28h**(2026-08-12 재측정, 노출 +86h 에 자동 사망 0건). ★**「이 표가 `user_stopped` 를 사망과 함께 센다」는 거짓이었다** — `soak_gate_predicate.py:39` 가 정본이고 처음부터 절단이었다 | BL-003 재계획 시 즉시 / 소크 재기동 회차마다 재측정                          | M        | 2026-08-08 bl003-unblock         |

> Resolved P1 = BL-001/002/010/011/012/013/016/017~021/080/091~099/101~103/110a 등 18+ 건 (`_archived.md`). + BL-622 (2026-08-07 gap-resync-autopsy). + BL-604 (2026-08-06 entry-set-divergence).

### BL-014

**Title:** Partial fill `cumExecQty` tracking
**Category:** 트랜잭션 / Order
**Priority:** P1
**Trigger:** partial fill 1 건 dogfood 발견 시 또는 Sprint 16~17 정기
**Est:** M (4-5h)
**출처:** TODO.md L709

**원인 / 영향:** 현재 terminal status 만 transition (closed + cumExecQty == quantity → filled). partial fill 진행 상황 추적 불가 → Kill Switch 노출 정확도 저하.

**권장 접근:** `order_executions` append-only table 신설 (order_id / executed_at / qty / price / fee). WS event 마다 row insert + Order.filled_quantity 누적 갱신.

**상태:** 🟡 **부분 Resolved (2026-07-25, `stage/money-path-accuracy`).** 재프레임 후 원안(ledger 테이블)이 아닌 **거래소 확정 손익 도입**으로 해결했다 — 진짜 리스크는 부분체결 추적이 아니라 `Order.realized_pnl` 이 close 주문 _생성 시점_ pine_v2 시뮬레이션 값(수수료 0·바 종가·전량청산 가정)이고 체결 후 한 번도 보정되지 않는다는 점이었다(머니-패스 5곳이 이 값을 SUM). Bybit `/v5/position/closed-pnl` 의 `closedPnl`(net) 로 reduce-only 체결분을 overwrite + `realized_pnl_synced_at` 출처 마커 + 4 winner 공용 backfill task + beat 스윕. `filled_quantity` 는 4 체결 경로 전부 write + `qb_partial_fill_total` + API/블로터 노출로 dead 컬럼 해소. **잔여** = per-execution ledger([BL-440](#bl-440)) / cancelled 종료 부분체결([BL-439](#bl-439)) / entry 부분체결 발산([BL-441](#bl-441)). 검증 = 실 Bybit demo 3건 오라클 대조 일치 + 스윕 멱등 + 라이브 worker 회수 + Kill Switch SUM 이동 실증.
**트리거 판정:** 미도래 — 이 섹션 자신의 잔여가 0 이다. 잔여 3갈래가 [BL-439]·[BL-440]·[BL-441] 로 분리됐고 셋 다 **DEFERRED**(2026-08-11 `bl-audit` 실측). Trigger 가 와도 여기서 착수할 것이 없다 (2026-08-11 bl-703-partial-verdicts)

---

### BL-015

**Title:** OKX Private WS
**Category:** WebSocket / Exchange
**Priority:** P1
**Trigger:** Bybit Demo 안정화 후 (BL-001 watchdog 완료 + 1주 운영)
**Est:** M (6-8h)
**상태:** ⏳ 대기 (트리거 미도래) — OKX 는 여전히 REST 전용 — private WS 스트림 파일이 없고 websocket_task.py:277 이 미구현을 주석으로 명시한다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 소크 창 미완(soak-gate rc=2 · C1 46.24h/168h). PASS 만 도래다([ADR-024]) (2026-08-10 bl-trigger-triage)
**출처:** TODO.md L710

**원인 / 영향:** Sprint 7d OKX 어댑터는 REST 만 보유. WS event 부재로 BL-001 의 fetch_order polling 부담 가중.

**권장 접근:** OKX private WS signing 방식 구현 (Bybit 와 다름). clOrdId 매핑은 Sprint 12 C-pre 에서 이미 완료.

---

### BL-022

**Title:** Golden expectations 재생성 (skip #1 해소)
**Category:** Test infra / Pine
**Priority:** P1
**Trigger:** pine_v2 `strategy.exit` 본격 지원 후
**Est:** M (3-4h)
**상태:** ✅ **Resolved** (2026-08-07 backtest-fidelity)
**출처:** TODO.md L17 / `tests/backtest/engine/test_golden_backtest.py:19`

**권장 접근:** legacy golden expectations 재생성 (pine_v2 strategy.exit 가 도입되면 expected 재계산). dette 카테고리 #1 해소.

**수리 (2026-08-07).** `backend/scripts/regen_golden.py` 신설 —
`--confirm` 없으면 exit 1 + 파일 0개 기록 · `--case <id>` 부분 실행 · `--check` 는 재생성본과 커밋본을
**의미 비교**(키 순서 무관)하고 차이가 있으면 exit 1, 파일은 안 쓴다.
케이스 발견은 `test_golden_backtest.py:_discover_cases()` 를 **재사용**한다(규칙이 갈리지 않게).
★**이 스크립트가 없었던 것이 [BL-621] stale 의 직접 원인**이다 — 같은 회차 `cda575f2` 가 trust-layer
baseline 은 regen 스크립트가 있어 갱신했는데 이 골든은 손으로 만들어야 해서 빠졌다.

---

### BL-023

**Title:** KIND-B/C mutation 분류 정밀도 (xfail strict 해소)
**Category:** Trust Layer / Mutation
**Priority:** P1
**Trigger:** Trust Layer v2 검토 시
**Est:** M (5-6h)
**상태:** ⏳ 대기 (트리거 미도래) — M4 의 xfail(strict=False) 가 그대로 남아 있고 KIND-B/C·NaN-tolerance 재설계 흔적은 docs 외 코드에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** TODO.md L23 / `tests/strategy/pine_v2/test_mutation_oracle.py:213`

**권장 접근:** KIND-B/C 가 NaN-tolerance 한계로 mutation 구분 못 함 (현재 `xfail(strict=False)`). NaN-tolerance 알고리즘 정밀화 또는 KIND 분류 재설계.

---

### BL-024

**Title:** real_broker E2E 본 구현 (nightly cron)
**Category:** Test infra
**Priority:** P1
**Trigger:** Bybit Demo credentials + seed data 첫 준비 시
**Est:** L (8h+)
**출처:** CLAUDE.md Sprint 10 Phase C — "실제 E2E 로직은 nightly 첫 실행 시 credentials + seed data 하에 작성 예정"

**상태:** 🟡 **열려 있다 (2026-08-04, `wt/e2e` — 워크플로·하네스만 수리, 실주문 leg 미착수).** ★★★**「skeleton 을 채운다」는 전제가 실측으로 뒤집혔다** — nightly 는 07-25~08-03 **10/10 실패**했고 지점은 pytest 가 아니라 `alembic upgrade head` 였다(`secrets.TRADING_ENCRYPTION_KEYS_TEST` 부재 → 빈 문자열 → `Settings` import 시점 ValidationError). ⇒ **pytest 는 한 번도 실행된 적이 없고, `flaky-real-broker` 이슈 89건(전부 OPEN)은 broker flakiness 의 증거가 아니다.** ★이 고장은 **alembic 스텝에만** 해당한다 — `tests/conftest.py:25-28` 이 pytest 에서는 빈 키를 즉석 Fernet 로 채운다. 이번 회차가 한 것: 워크플로 수리 9건(리터럴 키 · preflight `has_creds` 게이팅 · **이슈 생산기 스위치** · `_test` DSN · 아티팩트) + 계약 감사 `tests/test_nightly_workflow_contract.py`(marker 없음, 매 PR) + 자기정리 2층 하네스(`tests/real_broker/_harness.py`) + `_test` DSN 하드가드 + provider 경유 demo 엔드포인트 교정. ★**실거래소는 1바이트도 검증되지 않았다** — 잔여 = 실주문 leg(S2~S13), ★**차단 사유는 2026-08-04 에 바뀌었다** — 키 2종은 배치 완료이고 진짜 차단은 **지리 차단**이었다. 실행 경로를 로컬 스케줄로 옮겨 이미 첫 통과를 봤다(아래 §실행 경로).
**트리거 판정:** ~~도래 — … 잔여 차단(지리 403)은 트리거가 아니라 실행 경로 문제이고 로컬 스케줄로 첫 통과를 봤다 (2026-08-10 bl-trigger-triage)~~
→ ★★★**2026-08-11 ledger-truth 재정의 — 「지리 403」은 더 이상 차단자가 아니고, 진짜 차단자는
「소크와 계정 배타」다. 이 BL 은 소크와 상호배타이며 계정 분리 없이는 영구 SKIP 이다.**

**근거는 우리 코드가 직접 적고 있다** — `scripts/nightly-real-broker-local.sh:135`:

```
_verdict SKIP "소크가 돌고 있다 (활성 세션 ${ACTIVE}개) — 같은 Bybit 계정이라 포지션을 공유한다" 0
```

**로컬 nightly 8회 실측** (`~/Library/Logs/quantbridge/run-*.log`, 2026-08-04~08-10):
**SKIP 4** (전부 위 사유 · 활성 세션 1개) · **BLOCKED 2** (`quantbridge-db` 무응답) ·
**PASS 2**. ⇒ **8회 중 6회가 실거래소를 1바이트도 재지 못했다.**

★★**그 「PASS 2」도 실거래소 검증이 아니다** — 두 런의 pytest 요약이 **둘 다**
`1 passed, 1 skipped` 다(08-10 03:00 KST · 08-04 23:34). 본 섹션이 「로컬 스케줄로 이미 첫
통과를 봤다」고 적은 것은 **하네스 통과**이고, 같은 섹션의 「실거래소는 1바이트도 검증되지
않았다」가 여전히 참이다. ⇒ `_verdict` 가 rc 만 보고 PASS 를 찍는 것 자체가 별건 결함이다
(SKIP 도 **종료 코드 0** 이다 — `:135` 마지막 인자).

★**이것은 시간이 풀 수 없다.** [BL-003] 이 긴 소크 창을 노리는 한 활성 세션은 계속 1개 이상이고
`:135` 는 매번 발화한다. **2026-08-11 사용자 결정: 2번째 Bybit demo 계정을 발급하지 않는다**
⇒ 이 BL 은 「계정 분리」가 선행 조건인 **DEFERRED** 성격이다. 판정어 변경은 3면 정합을 함께
움직여야 하므로 별건으로 남긴다 — 지금 고치는 것은 **차단 사유의 거짓**이다.

**권장 접근:** 자격증명 2종 발급 후 실주문 leg 구현. ★체결 확인을 polling 으로 짜지 마라 — Bybit demo 시장가는 `create_order` 응답에서 `submitted` 로 오고(`providers.py:_map_ccxt_status`) 체결 확정은 WS 가 한다. `_async_fetch_order_status`(`tasks/trading.py:685-707`)를 명시적으로 태우는 설계여야 한다.

### ★2026-08-04 — 자격증명을 넣자 **진짜 차단이 드러났다** (실행 경로 = 로컬 스케줄)

**키 2종은 배치 완료다** — `backend/.env.local` + GitHub repo secret 동명 2종. 출처는
`trading.exchange_accounts` `19a8166a`(label `bybit demo`, `exchange_uid` **558689281**)의 거래 가능 키
(같은 uid 를 두 계정 행이 공유한다 — [BL-517](#bl-517)). ⇒ 「키 미발급」은 더는 차단 사유가 아니다.

**그러자 이 워크플로 역사상 pytest 가 처음 실행됐고**(직전 102회는 전부 `alembic` 에서 사망)
이렇게 실패했다 — nightly run `30917972735`:
`403 Forbidden — The Amazon CloudFront distribution is configured to block access from your country`
(`api-demo.bybit.com/v5/market/instruments-info`).

**대조 실측(같은 키, 같은 시각)** — GitHub Actions 러너 `fetch_balance` **403 Forbidden** /
로컬(한국) ✅ USDT 190,352.88 · `load_markets` ✅ 3,091 마켓. ⇒ **키 문제가 아니고 코드로 못 고친다.**
판정은 이슈 #540.

★**사용자 판정(2026-08-04) = B 안, 로컬 스케줄.** GitHub `schedule:` 은 껐고
`scripts/nightly-real-broker-local.sh` 가 launchd 로 매일 03:00(로컬)에 돈다
(`--install` / `--status` / `--uninstall`). 로그 = `~/Library/Logs/quantbridge/`.
★A 안(self-hosted 러너)은 **폐기가 아니라 보류** — CI 통합이 필요해지면 그때 재판단한다.

★**판정 낱말 4종** — `PASS` / `SKIP`(의도된 건너뜀, exit 0) / `FAIL`(exit 1) / `BLOCKED`(전제
미충족 = **측정 못 함**, exit 2). **exit 0 이 「검증됐다」를 뜻하지 않는다** — SKIP 도 0 이다.

★**가드 5종은 주입으로 판별력 5/5 를 증명했다** — 메인 체크아웃 아님 · 자격증명 빔 · DB 무응답
(「판정 불가」를 「이상 없음」으로 접지 않는다) · **소크 충돌**(같은 uid 라 포지션 공유 ⇒ SKIP) ·
지리 차단(CloudFront 403 ⇒ BLOCKED) · pytest 실패(⇒ FAIL).

★**첫 실행 실측(2026-08-04 23:34 KST) = `1 passed, 1 skipped`** — `fetch_balance` 가 실제 Bybit demo
에서 통과했다. 이 레포에서 스케줄 실행으로 실거래소 단언이 통과한 **첫 사례**다. ⇒ 위 상태 줄의
「실거래소는 1바이트도 검증되지 않았다」는 이 시점부터 **더는 참이 아니다.** 나머지 1건은 skeleton
skip 이고 그게 실주문 leg 의 본 작업이다.

**착수 순서 (고정):**

1. ★**충돌 가드 먼저.** nightly 는 03:00 에 도는데 그 시각 소크가 돌면 **같은 계정의 포지션을 서로
   본다**. 진입 **전에** 활성 라이브 세션을 확인하고, 있으면 「소크가 돌고 있다」로 **명시적 skip**.
   없으면 nightly 가 소크 포지션 때문에 오탐으로 빨개진다. 진짜 격리(별도 서브계정)는 소크 재개
   시점의 별도 판단이다.
2. **적대 검증 3건을 먼저 닫아라** — 실주문이 이 코드를 처음 실행시키는 순간 드러난다.
   **F3** `tests/real_broker/_harness.py` 함수 본문 **93% 미실행**(사용 테스트 0개 — 깨진 게 아니라
   **미검증**) · **F12** `flatten_one` 이 `submitted`→`filled` **대기 없이** `fetch_open_positions` 를
   불러 **거짓 residual** 가능(위 §권장 접근의 `_async_fetch_order_status` 설계가 이것이다) ·
   **F6** 계약 감사가 스텝 **순서**·`Upload pytest output` 존재·`timeout-minutes` 를 안 본다.
3. 시나리오 **S2~S13** 구현. 최소 수량으로 — 비용이 아니라 **신호**가 목적이다.
4. ★**멱등·자기정리.** 실패해도 거래소에 포지션·대기 주문을 남기지 마라. `stop` → `flatten` 순서
   계약. **세션 비활성화는 아무것도 flat 하지 않는다** — 이 레포가 3회 덴 함정이다.

---

### BL-025

**Title:** autonomous-parallel-sprints 스킬 patch (BUG-1/2/3 → LESSON-007/008/009)
**Category:** Tooling
**Priority:** P1 (다음 자율 병렬 sprint 시 재발 방지)
**Trigger:** on-demand (다음 자율 병렬 sprint 시도 직전)
**Est:** S (2h)
**상태:** ✅ Resolved — BUG-1(--git-common-dir)·BUG-2(full SIG_ID)·BUG-3(plan worktree-only) 세 패치가 스킬 repo 에 모두 반영돼 있다 (2026-08-09 status-triage-mass 코드 대조)
**출처:** TODO.md L653-657

**권장 접근:**

- BUG-1: kickoff-worker.sh symlink → `--git-common-dir` 기반 교체
- BUG-2: Planner SIG_ID full-id 강제
- BUG-3: Worker plan 저장 경로 worktree-only 강제
- 스킬 repo: `~/.claude/skills/autonomous-parallel-sprints/`

---

### BL-026

**상태:** 🟡 **열려 있다 — 단 범위를 특정할 수 없다 (2026-08-11 ledger-truth 재판정).** 본 섹션 `**Trigger:**` 줄의 ✅ 는 _Stage 2c 2차 fixture 활성화_(2026-04-23 완료)를 가리키고, 이 BL 자신은 같은 줄이 명시하듯 **"회귀 PR 생성 필요"** 상태다. 근거: 본 섹션 Trigger/권장 접근 줄 · `docs/roadmap.md:168` `- [ ] **BL-026**`.
★★★**2026-08-11 실측 — 제목·Est·권장 접근이 셋 다 반증됐다.**

- **제목의 「skip #4-7, #9-15」(=12건)은 출처가 사라졌다.** `**출처:** TODO.md L20-22` 인데
  `docs/TODO.md` 는 `fcc36bf7`(#485, docs 구조 재편 42→12)에서 **삭제**됐다. 그 번호가 어느
  테스트를 가리켰는지 **레포 어디에도 없다** ⇒ 「12 skip 일괄 활성화」는 대상 집합이 없다.
- **실측 무조건 skip 은 6건이고 그중 mutation 관련은 1건뿐이다** —
  `tests/strategy/pine_v2/test_trust_layer_parity.py:418`. 나머지 5건은
  `test_metrics_auth.py`(3) · `test_runs_error_response.py`(2) 로 **fixture env 부채**이고
  mutation 과 무관하다. `skipif` 는 21건인데 **mutation 게이팅에 쓰이지 않는다.**
- **진짜 게이트는 skip 데코레이터가 아니라 `tests/conftest.py:138-148` 의 마커**
  (`skip_mutation`)다 ⇒ `:418` 데코레이터는 그 위에 겹친 **죽은 껍데기**이고,
  「활성화」의 대상은 fixture 가 아니라 **그 껍데기 제거**다.
- ⇒ **Est 「S (1-2h)」는 근거가 없다.** 12건이 아니라 1건이고, 작업은 「활성화」가 아니라
  「껍데기 제거 후 `--run-mutations` 로 실제로 도는지 확인」이다.

**트리거 판정:** 도래 — 트리거 줄 자신이 「✅ 2026-04-23 완료, 회귀 PR 생성 필요」로 도래를 적었다 (2026-08-10 bl-trigger-triage). ★2026-08-11 유지 — 도래는 맞지만 **범위 재정의가 선행**이다.

**Title:** Mutation fixture 활성화 회귀 검토 (skip #4-7, #9-15)
**Category:** Trust Layer / Test infra
**Priority:** P1
**Trigger:** Stage 2c 2차 fixture 활성화 후 (✅ 2026-04-23 완료, 회귀 PR 생성 필요)
**Est:** S (1-2h)
**출처:** TODO.md L20-22

**권장 접근:** Path β Stage 2c 2차 mutation 8/8 도달 후 12 skip 가 활성화 가능 상태. 회귀 PR 1건으로 일괄 활성화 + 1주 nightly green 후 안정화.

---

### BL-492

**Title:** 이미 돌파된 stop 의 시뮬↔거래소 시맨틱
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 실자금 cutover 전, 또는 110093 거부가 잦아질 때
**Est:** S-M
**상태:** 🟡 부분 해결 — 권장안 (a) 시장가 근사가 110092/110093 복구 태스크로 배선·테스트까지 구현됨. 남은 것은 백테스트↔라이브 체결가 차이 문서화/결정뿐. (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 외생 조건 2겹. 본문 권장 접근이 「**라이브 매매 의미를 바꾸므로 사용자 결정이 선행**한다」를 적었고, 실자금 cutover 는 [BL-003] 이 막고 있다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-27 live-conditional-entry dogfood 실측

**원인 / 영향:** pine_v2 는 `low <= stop`(숏) / `high >= stop`(롱)을 즉시 체결로 보는데, 거래소는 이미 돌파된 트리거를 `retCode 110093` 으로 거부한다. 가격이 피벗을 지나가면 시뮬은 진입했다고 믿고 거래소엔 포지션이 없다. 104분 dogfood 에서 10건 관측. 참조가(마지막 종료 bar 종가) 사전 차단을 넣어 재시도 루프는 없앴지만 **시맨틱 차이 자체는 남는다**.

**권장 접근:** (a) 이미 돌파된 stop 을 시장가로 근사 — 시뮬과 맞지만 체결가가 달라 백테스트↔라이브 일치를 미묘하게 깬다. (b) 엔진 쪽에서 그 케이스를 진입 skip 으로 처리 — 라이브가 기준이 되어 백테스트 결과가 바뀐다. **라이브 매매 의미를 바꾸므로 사용자 결정이 선행**한다.

**영향 파일:** `strategy/pine_v2/strategy_state.py`, `trading/services/conditional_entry_planner.py`.

**Risk:** 🟡 (fail-closed 이고 원장에 사유가 남는다).

---

### BL-493

**Title:** 조건부 진입 첫 bar 커버리지 공백
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 진입 누락이 실측될 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 첫 bar 커버리지 공백을 다루는 코드·테스트가 없다 — 평가 tick 지연 보정도, 재발행 보장도 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry

**원인 / 영향:** 평가 tick 은 bar 종료 **56초 뒤**에 돈다(실측 16:17:56 tick 이 16:16 bar 를 읽음). 시뮬은 stop 을 다음 bar 전체에서 체결 가능하다고 보지만 거래소 주문은 그 bar 의 93% 가 지난 뒤 올라간다. PbR 처럼 매 bar 재발행하는 전략은 최초 1바만 해당하나, 한 번만 발행하는 전략은 그 bar 를 통째로 놓친다.

**Risk:** 🟢

---

### BL-494

**Title:** `min_qty != qty_step` 심볼에서 최소수량 미보장
**Category:** Backend / trading
**Priority:** P3
**Trigger:** BTCUSDT 외 심볼 지원 시
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 계획기는 여전히 qty_step 절삭만 하고 limits.amount.min 조회는 레포 어디에도 없다(있는 건 limits.cost.min 가드뿐). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry

**원인 / 영향:** 조건부 진입 계획기는 `qty_step` 절삭만 한다. BTCUSDT 는 `limits.amount.min == qtyStep == 0.001` 이라 절삭이 최소수량을 겸하지만 일반 보장은 아니다. 둘이 다른 심볼에서는 스텝은 통과하고 최소수량은 미달인 주문이 매 tick 거부될 수 있다.

**Risk:** 🟢

---

### BL-496

**Title:** 조건부 진입 발주 순서가 엔진 체결 우선순위와 다르다
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 같은 바에 조건부 진입이 2건 이상 열리고 둘 다 트리거될 수 있을 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 계획기는 여전히 trade_id 순 정렬(620-621)이고 엔진은 open 거리순(strategy_state.py:1057) — 정렬 통일도 독스트링 명시도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry 작업 노트 (E1 적대 검증 §9(f), 종결 시 등재)

**원인 / 영향:** 계획기는 `to_cancel`/`to_place` 를 **`trade_id` 순**으로 정렬한다(`conditional_entry_planner.py:179,297-298`). 반면 엔진의 같은 바 pending fill 후보는 **open 가격과의 거리순**으로 정렬한다(`strategy_state.py:765` `candidates.sort(key=lambda c: abs(c[2] - open_))`). 즉 두 조건부 진입이 같은 바에 둘 다 트리거되면 시뮬이 먼저 체결로 보는 쪽과 거래소에 먼저 올라가는 쪽이 다를 수 있다.

실해는 낮다 — 등재는 트리거 **이전**에 끝나고 거래소가 트리거 순서를 가격으로 결정하므로, 발주 순서가 체결 순서를 바꾸지는 않는다. 다만 **부분 등재로 끊긴 경우**(게이트 거부·네트워크 실패로 일부만 올라간 tick)에는 남는 주문이 시뮬 우선순위와 어긋난다.

**권장 접근:** 계획기 정렬 키를 `abs(stop_price - 참조가)` 로 맞추거나, 최소한 두 정렬 규약이 다르다는 사실을 계획기 독스트링에 고정한다. **정렬을 바꾸면 결정론 테스트가 함께 바뀐다**(현재 `trade_id` 순 결정론이 테스트로 고정돼 있다).

**영향 파일:** `trading/services/conditional_entry_planner.py`, `strategy/pine_v2/strategy_state.py`.

**Risk:** 🟢

---

### BL-497

**Title:** cancel → place 사이에 stop 이 부재하는 창
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 재등재 churn 이 잦아지거나(BL-486), 그 창에서 놓친 돌파가 실측될 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — cancel 루프(2456) 전량 후 place 루프(2501) 구조가 그대로고, amend/edit_order 는 레포 전체에 백로그 문장 외 구현이 0건이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-27 live-conditional-entry 작업 노트 (종결 시 등재)

**원인 / 영향:** reconcile 은 취소 루프를 **전부 끝낸 뒤** 등재 루프를 돈다(`tasks/live_signal.py:406-416` → `:462-492`). 의도한 순서지만(이중 등재 방지), 그 사이 수 초 동안 거래소에 그 stop 이 **없다**. 그 창에서 가격이 트리거를 지나가면 진입을 통째로 놓치고 시뮬만 진입했다고 믿는다 — BL-492 와 같은 발산의 다른 경로다. BL-486 창 드리프트로 재등재가 104분에 8건 나므로 창이 반복 열린다.

**권장 접근:** ccxt `edit_order`(amend) 로 취소·재등재를 한 번의 왕복으로 바꾼다. Bybit v5 는 `/v5/order/amend` 로 `triggerPrice`·`qty` 수정을 지원하므로 **계약 실측이 선행**한다(미트리거 조건부에 amend 가 되는지). 대안은 place-then-cancel 순서 뒤집기인데 그 사이 **이중 등재**가 열리므로 귀속 불변식만으로는 부족하다.

**영향 파일:** `tasks/live_signal.py`, `trading/providers.py`.

**Risk:** 🟢 (fail-closed 는 아니지만 무음 미진입이라 관측 가능성이 낮다).

---

### BL-499

**상태:** ⏳ **대기 (트리거 미도래) — 단 trigger 는 이제 발화 가능하다.** ★★2026-07-28 `feat/live-observability` 정정: 이 항목의 **Trigger("취소 실패 metric 이 관측되면")가 BL-506 이전에는 구조적으로 충족 불가**였다. 그 카운터는 worker 전용이라 어떤 스크레이프 경로에도 노출되지 않았기 때문이다(BL-506 이 그 모순을 지적했다). **BL-506 Resolved 로 관측 가능성 자체는 확보됐다** — 배선 후 `qb_live_conditional_reconcile_errors_total` 의 다른 라벨(`deferred_market_inflight` 8 · `positions` 3)이 실제로 관측된다.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
★그럼에도 **1시간 40분 soak 에서 `cancel`/`cancel_raced`/`cancel_stalled` 는 시리즈조차 나타나지 않았다.** 여전히 **"관측 안 됨" 이지 "일어나지 않음이 증명됨" 이 아니다.** 근본 경합은 열려 있다.
★**부수 발견** — 라벨 있는 Counter 는 자식이 처음 생길 때 노출되므로, 이 항목들은 `/metrics` 에 **0 으로도 나오지 않는다. 시리즈가 아예 없다.** 대시보드에서 "아직 안 일어남" 과 "그런 metric 이 없음" 이 구분되지 않는다.

**이전 상태(2026-07-28 live-ops-hygiene):** ★**신설 metric 실관측을 확인만 했다 — 결과는 0건이다.** janitor·sweeper beat 은 5분 주기로 정상 발화하지만(30분에 각 6회) `cancel_stalled`/`cancel_raced` 는 한 번도 오르지 않았다. 고착 행이 DB 에 0건이라 그 경로가 **주행되지 않았기 때문**이고, "관측되지 않음" 이지 "일어나지 않음이 증명됨" 이 아니다. 근본 경합은 그대로 열려 있다. ★단 BL-503 janitor 가 생기면서 `cancel_stalled` 의 **근거 문장이 낡았다** — "아무도 안 치운다" 는 이제 거짓이고 30분 뒤 janitor 가 처리한다(그 문구는 BL-503 에서 정정).

**이전 상태:** 🟡 부분 완화 (2026-07-27, `feat/live-conditional-hardening`). 근본 경합(취소 의도 영속 또는 dispatch 시점 재검사)은 사용자 결정으로 **마이그레이션 0** 을 택해 그대로 남는다. 이번에 한 것은 **패배와 진짜 실패를 구분해 관측 가능하게 만든 것**이다 — `transition_pending_to_cancelled` 가 rowcount 0 이면 `get_state_and_exchange_id_fresh`(식별맵 우회 컬럼 select)로 재조회해, 비-`pending` 이면 `RuntimeError` 대신 metric + 로그를 남긴다. ★**경합과 제출 중단을 라벨로 가른다** — `submitted` 인데 `exchange_order_id` 가 없으면 경합이 아니라 dispatch 가 상태만 커밋하고 거래소 왕복에서 죽은 **영구 고착**이고(`orphan_scanner` 가 조건부 진입을 면제해 아무도 안 치운다) 그 행은 매 tick 이 분기를 타 세션 등재를 영구 정지시킨다. `stage="cancel_stalled"` + `logger.error` 로 분리한다(적대 검증 지적 — 안 가르면 영구 장애가 1회성 경합 카운터에 섞여 사라진다). ★**패배해도 그 tick 의 `to_place` 는 건너뛴다(fail-closed 유지)** — `current_position` 은 취소 루프보다 **먼저** 찍은 스냅샷이라, 패배한 주문이 그 사이 체결되면 낡은 포지션 위에서 사이징한 주문이 나간다(G0.5 codex 지적, 재현 판정 후 플랜 개정).

★★**preflight 결론을 정정한다.** "취소된 16건이 전부 `exchange_order_id` 를 보유하므로 이 경로는 미주행" 은 **성립하지 않는다.** 패배한 호출은 rowcount 0 이라 행에 아무것도 안 쓰고, 이후 dispatch 가 `exchange_order_id` 를 붙이면 최종 행은 정확히 그 16건과 같은 모습이 된다. 증명된 것은 **"DB-only 취소 _성공_ 0건"** 뿐이다. 신설 metric 이 앞으로 호출·패배 횟수를 따로 센다.

**Title:** 조건부 진입 취소와 비동기 dispatch 의 경합 — 취소하려던 주문이 거래소에 올라간다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 취소 실패 metric(`stage="cancel"`)이 관측되거나 실자금 cutover 전
**Est:** M
**출처:** 2026-07-27 live-conditional-entry 최종 codex 리뷰 (재현 판정 후 등재)

**원인 / 영향:** `exchange_order_id` 가 없는 `pending` 주문은 `transition_pending_to_cancelled` 로 **DB 에서만** 취소한다(`live_signal.py:406-421`). 그 조건부 UPDATE 는 `state == pending` 을 요구하므로, 실행 워커가 `pending → submitted` 를 먼저 커밋하면 rowcount 0 → `RuntimeError` → `cancel_failed` → reconcile 중단이다. reconcile 을 중단해도 **이미 클레임한 dispatch 는 막지 못한다** — 취소하려던 조건부 진입이 거래소에 등재된다.

★**액면 수용하지 않고 재현 판정한 결과 자가 치유는 확인됐다.** 세션이 비활성이면 beat sweeper(`list_orphan_conditional_entries`)가 `state=submitted` + `trigger_price` + `reduce_only=false` + 비활성 세션으로 그 주문을 찾아 거래소에서 취소한다. 세션이 활성이면 다음 tick 의 `actual` 에 `exchange_order_id` 와 함께 들어와 정상 취소된다. **따라서 노출은 최대 1 tick(약 60초)이고 영구화하지 않는다.** 그 창에서 트리거가 돌파되면 원치 않은 진입이 체결될 수 있다는 것이 잔여 위험이다.

**권장 접근:** 취소 의도를 주문 행에 먼저 남기고(예: `cancel_requested_at`) dispatch 직전에 재검사하거나, dispatch 태스크가 라이브 세션·desired 유효성을 실행 시점에 재확인한다. 어느 쪽이든 마이그레이션 또는 dispatch 계약 변경이 필요하다.

**영향 파일:** `tasks/live_signal.py`, `trading/repositories/order_repository.py`, `tasks/trading.py`.

**Risk:** 🟡 (최대 1 tick 노출, sweeper·다음 tick 이 닫는다).

---

## P2 — Hardening / 건강도 작업

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Trigger                                                                                                         | Est          | 출처                                                         |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------ |
| [BL-522](#bl-522) | ★엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다 (유실 채널 5종)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 실자금 cutover 전 필수                                                                                          | M-L          | 2026-07-28 live-entry-parity                                 |
| [BL-186](#bl-186) | 🟡 부분 Resolved (186a) — Full leverage + funding + mm + liquidation 풀 모델 (잔여 = BL-186b)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Sprint 38+ (BL-185 foundation 위)                                                                               | M-L (16-24h) | Sprint 37 BL-185 후속                                        |
| [BL-190](#bl-190) | PDF export (jsPDF / Playwright)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 외부 사용자 요청 시                                                                                             | M (3-5h)     | Sprint 41 Worker H 결정                                      |
| [BL-195](#bl-195) | ✅ qb-form-slide-down animation 영구 truncation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Sprint 45 codex G.4                                                                                             | XS (30m)     | Sprint 45 codex G.4 발견                                     |
| [BL-235](#bl-235) | N-dim acquisition surface viz (Bayesian 전용)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Sprint 57+                                                                                                      | M (8-12h)    | ADR-013 §6 #8 deferred                                       |
| [BL-236](#bl-236) | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Sprint 56+                                                                                                      | S (3-5h)     | Sprint 55 deferred                                           |
| [BL-363](#bl-363) | ✅ stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | deepening sprint 또는 5번째 engine 추가 시                                                                      | S (2-3h)     | 2026-05-30 full-inspection §appendix P1-9                    |
| [BL-364](#bl-364) | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | string 카테고리 sweep 요청 시                                                                                   | M (4-6h)     | 2026-05-30 full-inspection §appendix P1-9 (S4 후속)          |
| [BL-366](#bl-366) | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | trading deepening sprint                                                                                        | S-M (3-5h)   | 2026-06-26 trading-deepen-2                                  |
| [BL-368](#bl-368) | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | trading deepening / 4번째 provider                                                                              | S-M (3-5h)   | 2026-06-26 trading-deepen-2                                  |
| [BL-369](#bl-369) | 3 provider `create_order` try/except/finally ~40 LOC 복붙                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | trading deepening sprint                                                                                        | S (2-4h)     | 2026-06-26 trading-deepen-2                                  |
| [BL-372](#bl-372) | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Wave 3 실자금 cutover 전                                                                                        | M (6-10h)    | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)           |
| [BL-373](#bl-373) | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | BL-365 standalone-trigger 발주 시                                                                               | S-M (3-5h)   | 2026-06-28 grilling (트레일링 후속 scope)                    |
| [BL-375](#bl-375) | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Wave 3 실자금 cutover 전                                                                                        | S-M (3-5h)   | 2026-06-29 BL-372 same-side stale G1 codex                   |
| [BL-379](#bl-379) | pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐, latent harm-class)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | pine_v2 robustness 후속                                                                                         | M (4-6h)     | 2026-06-30 QA codex G2 + 직접 재현                           |
| [BL-380](#bl-380) | Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반) + VirtualRunResult.warnings 미전파                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Track A 신뢰 표면 sprint                                                                                        | S-M (3-5h)   | 2026-06-30 QA LuxAlgo 0-trade                                |
| [BL-381](#bl-381) | Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허 (i2_luxalgo 검증 vacuous)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Trust Layer CI 강화                                                                                             | S (2-4h)     | 2026-06-30 QA codex G2/diff                                  |
| [BL-382](#bl-382) | qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성, mdd_exceeds_capital 은 표시됨)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | sizing 투명성 sprint                                                                                            | S (2-4h)     | 2026-06-30 QA F1 (codex G2)                                  |
| [BL-387](#bl-387) | backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 횡단 (key drift 시 silent 잘못된 sizing, money-path)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | backtest deepening 또는 sizing 로직 변경 시                                                                     | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 최강 후보)                 |
| [BL-392](#bl-392) | ✅ stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass↔serializer↔OutSchema, untyped JSONB seam)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | stress_test deepening 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시                                  | M (4-6h)     | 2026-06-30 stress_test-deepen (deepen-modules 1차)           |
| [BL-523](#bl-523) | 조건부·전환 진입에 TP/SL 브래킷이 붙지 않는다 (현재 코퍼스 미발현 — `stop=`+`strategy.exit` 동시 사용 시 발현)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 실자금 cutover 전                                                                                               | M            | 2026-07-28 live-entry-parity                                 |
| [BL-524](#bl-524) | `strategy.entry(limit=...)` 이 조용히 버려지고 시장가 진입으로 대체된다 (TV 충실도)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | limit 진입 전략 지원 시                                                                                         | M            | 2026-07-28 live-entry-parity                                 |
| [BL-527](#bl-527) | ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 기대치 정확도가 판정에 쓰이기 전                                                                                | S            | 2026-07-28 live-outcome-parity                               |
| [BL-528](#bl-528) | 세션 창 밖 늦은 체결이 어느 표면에도 안 잡힌다 (실측 확정 청산 4건 · net −0.5463)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 세션 손익 완결성이 필요할 때                                                                                    | M            | 2026-07-28 live-outcome-parity                               |
| [BL-529](#bl-529) | 🟡 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 전략 누적 지표를 신뢰해야 할 때                                                                                 | S            | 2026-07-28 live-outcome-parity                               |
| [BL-531](#bl-531) | parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery (지표 1개 추가 = 5파일 편집)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | parity 지표를 더 붙일 때                                                                                        | S            | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-532](#bl-532) | `_sum_decimals` 사본이 `PARITY_DECIMAL_CONTEXT` 밖에서 돈다 (본 레포가 방금 세운 규칙과 불일치)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 다음 parity 손질 시                                                                                             | XS           | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-533](#bl-533) | ✅ **Resolved (2026-08-09, W3)** — 종료 세션 목록이 같은 엔드포인트를 두 쿼리 키로 조회해 미러 state 를 낳는다. ★**키 통일은 [BL-423] 때 이미 끝나 있었다** — 남은 일은 미러 `selectedInactiveSession` 제거뿐(참조 4→0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 코크핏 손질 시                                                                                                  | XS           | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-534](#bl-534) | 외부 오라클 테스트가 27 leg Decimal 합산을 실제로 실행하지 않는다 (총계를 관측 1건에 몰아넣음)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | parity 산술을 손댈 때                                                                                           | XS           | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-538](#bl-538) | 발산 알림 본문이 모든 카테고리에 "전략 수정 후 재활성화" 라고 처방한다 (포지션 불일치엔 틀린 처방)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 운영 알림을 사람이 신뢰해야 할 때                                                                               | S            | 2026-07-29 PR #497 사후 리뷰                                 |
| [BL-541](#bl-541) | 세션 행이 아예 없는 포지션(웹훅 경로·거래소 수동)은 여전히 앱에서 못 닫는다 — ★아직 실측된 적 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `no_owning_session` 이 실제로 관측될 때                                                                         | M            | 2026-07-29 live-orphan-close                                 |
| [BL-545](#bl-545) | ★gap-resync 게이트가 5% 수량 허용치를 물려받아 구 게이트가 막던 불일치를 통과시킨다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 조건부 진입을 실자금으로 가기 전                                                                                | S            | 2026-07-30 conditional-entry-alignment                       |
| [BL-546](#bl-546) | 원장→엔진 seed 경계에서 `Decimal` 이 `float` 로 강등 (Decimal-first 하드 규칙)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 엔진 수치 표현을 손댈 때 / 큰 notional                                                                          | M            | 2026-07-30 conditional-entry-alignment                       |
| [BL-547](#bl-547) | ★원장 seed 가 그 tick 한 번만 산다 — 조용한 고아 가능 (**아직 실측된 적 없음**)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `exchange_only` 이 실제로 오르는 것이 관측될 때                                                                 | M            | 2026-07-30 conditional-entry-alignment                       |
| [BL-553](#bl-553) | ★`outcome="applied"`(원장 seed 주입)가 실주행에서 한 번도 안 밟혔다 — 단위테스트로만 증명                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 다음 soak (기회주의적 확인)                                                                                     | XS           | 2026-07-30 conditional-entry-alignment                       |
| [BL-556](#bl-556) | ✅ **`final-gates.sh` §4 에 `e2e chromium` 추가** — ★이것만 영역 판정(`has_fe`)에 건다(BE·DB·인증·소크 무결합). 3분기 전부 같은 3행, 6조합 전수 검증. ★★**4건이 아니라 3건**(`--list` 실측, 문서 5곳 오기). ★`FE build` fail-open 도 같이 닫았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 다음 회차 게이트 실행 전                                                                                        | XS           | 2026-07-30 live-entry-completeness                           |
| [BL-558](#bl-558) | retCode 를 `error_message` 에 싣는 경로가 **동기 1곳뿐** — 비동기 확정 거절이 코드 미상이 된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 거절 코드로 채널을 가를 때                                                                                      | M            | 2026-07-30 live-entry-completeness                           |
| [BL-565](#bl-565) | `check_exit_fills` 의 close 도 BL-560 과 같은 성질 — 읽기만 하고 남겼다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | `strategy.exit` 을 쓰는 전략을 라이브로 돌리기 전                                                               | S            | 2026-07-31 reversal-ledger-sync                              |
| [BL-567](#bl-567) | `place_trailing_stop` enqueue 가 실패하면 그 주문의 트레일링은 **영구 유실** — 회수 경로가 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 트레일링 전략을 라이브로 상시 운용하기 전                                                                       | —            | 2026-07-31 reversal-ledger-sync                              |
| [BL-568](#bl-568) | BL-562 체결시점 반전 계측이 **11건 중 10건 무측정** — 분류된 건이 0 이다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 그 분포를 근거로 무언가를 판단하기 전                                                                           | S            | 2026-08-01 ledgerhygiene                                     |
| [BL-574](#bl-574) | ★`LIMIT 100` 이 세션 필터보다 앞서 걸려 현 세션 resting 을 놓치고 `awaiting_trigger` 를 `unexplained` 로 오분류 (측정 완료 · 수리 보류 — 동시 최대 2 / 100)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 동시 resting 이 20건을 넘긴 날이 관측될 때                                                                      | S            | 2026-08-01 soak codex                                        |
| [BL-575](#bl-575) | SELECT 실패 후 같은 AsyncSession 을 rollback 없이 재사용 — fail-open 계약이 깨진다 (★선재 패턴, 회귀 아님)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | fail-open 을 근거로 쓰기 전                                                                                     | S            | 2026-08-01 soak codex                                        |
| [BL-580](#bl-580) | 계측 가드 잔여 **96곳** (누적 63곳 수리). ★산문 근거 29곳이 주입에서 **29곳 전건 유해** — 「가드 없이 유지」 누적 0곳. ★2026-08-03 신규 **H8** = 계측 실패가 fail-open `except` 에 삼켜져 **거절을 집행으로 뒤집는다**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | `qb_metrics_mutation_failed_total` 창 차분이 0 을 벗어날 때 (★프록시다 — 가드 밖은 이 counter 를 올리지 않는다) | M            | 2026-08-02 metric-guard-parity                               |
| [BL-591](#bl-591) | ★**뿌리** — 엔진 포지션의 SSOT 가 없다. `run_live` 시뮬이 매 tick 봉을 재생해 포지션을 **도출**하고 정상 운행 중엔 현실로 **보정되지 않는다**. 슬라이스 1(계측) = **PR #539 OPEN**(통합 브랜치 `stage/engine-position-ssot`, 미머지). ★★★**슬라이스 2 미착수 확정** — 사전등록 V1 발동(④ = 0: 사망 2건의 상류에 `exchange_only` 0건 · 최악 상계 ≤1/21). ★★★**유도 함수 재설계 필요** — `trade_id` 는 trade 가 아니라 Pine 진입 규칙 이름이고(`PivRevSE` 56체결/19세션) 반전은 `:close:` 키를 안 만든다 ⇒ 판정 불가 **27.6%**(전량 `duplicate_open`) · **net 은 맞고 legs 는 틀리다**(오라클 11건: 오답 0 · 적중 4 중 3건이 `legs=2` 인데 거래소는 단일 포지션 — 나머지 1건은 반전 없는 먼지 세션이라 정확) ★**2026-08-05 P1→P2 강등**(잔여 = D1/D2 · 근거는 §상태 줄)                            | 발산 증상 BL 을 또 하나 열기 전에 · 소크가 또 죽었을 때                                                         | L            | 2026-08-03 breach-rejection-recovery                         |
| [BL-592](#bl-592) | 같은 Bybit 데모 계정이 `trading.exchange_accounts` 에 **2행**이라 청산 1건이 **2행으로 적재**되고, 주문을 안 가진 계정 쪽에서는 `ours` 가 **`unknown` 으로 오라벨**된다(실측 91/91 대칭). 원장 구멍 계측을 **3.7배 부풀린다** — [BL-591] 슬라이스 1 관측 전에 인지 필요                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | `exchange_exits` 로 원장 구멍·귀속을 판정하기 전에                                                              | S            | 2026-08-04 engine-position-ssot                              |
| [BL-593](#bl-593) | 운영자 도구(`backend/scripts/verify_*.py` 등)가 `ClosePositionService` 를 못 써서 provider 를 **직접 호출** → 그 청산에 대응하는 `trading.orders` 행이 **없다**. 실측 `external_manual` **12건 / 103건(11.7%)**. [BL-591] C 안이 원장을 진실로 쓰므로 이 구멍이 곧 오주입 위험                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 소크를 끄거나 거래소를 손으로 flat 으로 만들기 전에                                                             | S            | 2026-08-04 engine-position-ssot                              |
| [BL-598](#bl-598) | ★**코퍼스 스크립트를 처음 파싱하는 테스트가 비용을 전부 문다** — `test_ast_classifier[i3_drfx]` 단독 **42.66s** vs 전체 스위트 안 **4.58s**. 프로세스 전역 비용이라 **쪼개면 샤드마다 중복**된다(CI 3샤드 합 1796s vs 단일 1278s, +519s 전부가 이 중복). 샤딩 저항의 뿌리이고 CI 14분 벽의 원인. ★**2026-08-08 정체 확정** — ANTLR ALL(\*) DFA 캐시가 **파싱에 의해** 지연 구축되는 것(import 아님·크기 법칙 아님). 같은 프로세스·같은 입력에서 DFA 만 비우면 3.63s→**49.61s** 로 되돌아온다(인과 대조). ⇒ ② 는 **테스트 디스크 캐시로 닫힌다 — `backend/src` 0줄**. 도구 = `backend/scripts/profile_corpus_parse.py`. ★**규모 대조는 미대조** — ① 은 로컬 9프로세스(+52.89s)이고 CI 3샤드(+519s)와 **직접 대조되지 않았다**(약 10배 차) ⇒ 「+519s 전부가 이 중복」은 여전히 **미검증 가정**이다 | CI backend 를 14분 아래로 내리려 할 때 · pine_v2 코퍼스 테스트를 늘리기 전에                                    | M            | 2026-08-06 ci-diet                                           |
| [BL-603](#bl-603) | ✅ 백테스트 비용 가정이 라이브 실효의 **2.7배** — 가정 왕복 0.30%(fees 0.1+slip 0.05/leg) vs 원장 실측 왕복 **0.1101%**(taker 0.055%/leg 단일 성분, 84 event 중 77 이 8자리 일치·비-taker 잔차 0.03%). 매칭쌍 진입가 잔차 중앙 0.014% vs slippage 가정 0.05%. **2026-08-07 Resolved** — 0.00055/0.00014(두 SSOT+FE 미러 4곳), 왕복 0.138%. 코퍼스 `num_trades` 불변·`s3_rsid` 부호 반전                                                                                                                                                                                                                                                                                                                                                                                                          | 백테스트 손익을 라이브 예측치로 읽기 전 (비용 축이 3배 비관)                                                    | S            | 2026-08-06 backtest-reality-gap                              |
| [BL-605](#bl-605) | ✅ **스윕 계정 루프 `exchange_uid` dedup** — `exchange_exits` 가 같은 청산 event 를 **정확히 2행**으로 적재하던 뿌리는 같은 실제 계정을 가리키는 계정 **행**이 2개라 같은 창을 두 번 조회한 것이었다. 2026-08-09 수리 · 수리 전 red 실증 · 하네스의 UNIQUE 축(`(exchange_account_id, row_hash)`) 도 함께 정정                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | exchange_exits 를 집계로 소비하는 코드를 추가하기 전                                                            | S            | 2026-08-06 backtest-reality-gap (eval2 실측)                 |
| [BL-610](#bl-610) | ✅ 코드·테스트·설정 **10곳**이 삭제된 문서 경로를 가리킨다. 2026-08-08 수리 — 사용자 표면 2곳은 **참조 제거**(`git:<sha>` 좌표는 사용자에게 쓸모없다), 개발자 8곳은 **tombstone**. ★삭제 커밋이 **둘**이라 sha 도 둘(heikinashi ADR 4곳 = `590eeec9` · 나머지 `0ddf2b53`) · 종전 재검출 명령은 `-n` 누락으로 **전건 오탐**했다                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | BL-003 소크 창 종료 후 첫 backend/src 정리 회차                                                                 | XS           | 2026-08-06 docs-overhaul (fix-doc)                           |
| [BL-611](#bl-611) | ✅ ★**메타-방법론 영구 규칙이 자동 로드에서 빠졌다** — 구 `.ai/common/global.md` §7 은 `paths` 없는 `.claude/rules/global.md` 로 **매 세션 무조건** 들어왔다(2026-08-07 실측 재현). ADR-026 이 이를 `generator-evaluator-pipeline.md` §8 로 옮기면서 **열어야만 읽히는** 문서가 됐다 — kickoff preflight(§8.1)·codex finding 코드 대조(§8.3)가 조용히 누락될 수 있다. **Resolved** — `AGENTS.md` 에 §8.1/§8.3 두 줄 인라인                                                                                                                                                                                                                                                                                                                                                                       | 다음 Sprint kickoff (Type A/B) 전                                                                               | S            | 2026-08-07 docs-overhaul 리뷰                                |
| [BL-625](#bl-625) | ★**플레이스홀더 시크릿이 development 에서는 아무 게이트에도 안 걸린다** — 서버 `backend/.env.local` 이 `CLERK_SECRET_KEY=sk_test_...`(문자 그대로)인데 API 는 정상 기동하고 `/health` 200 을 냈다. 호스트 uvicorn 이 인증 경로를 한 번도 안 밟아서 드러나지 않았고, 브라우저 첫 로그인 요청이 **전건 401** 로 터지고서야 보였다. `_enforce_production_safety` 가 이 계열을 알지만 **`app_env == production` 일 때만** 검사한다. ★2차: 루트 `.env` 인라인 주석(`# [필수 …]`)을 안 떼고 값을 옮기면 한글이 섞여 401 이 아니라 **500**(clerk SDK 헤더 ascii 인코딩)                                                                                                                                                                                                                                 | 새 호스트에 API 를 세울 때 · [BL-071] 발동 시                                                                   | S            | 2026-08-07 fe-oracle-deploy                                  |
| [BL-632](#bl-632) | 골든을 오라클로 승격했지만 그 기대값은 **엔진 자신의 출력**이다(회귀 감지기이지 정확성 오라클이 아니다). ★반순환 근거가 이 축을 안 덮는다 — 손계산 오라클 `test_golden_oracle_ema_sltp.py` 는 4봉·고정 stop/limit 이라 **`ta.atr` 를 한 번도 안 탄다**. ⇒ [BL-621] 의 낡음을 만든 바로 그 축이 **구조적으로 오라클 밖**이다. BL-621 본문의 「틀린 값을 정본으로 고정하게 된다」 경고에 아직 답하지 않았다                                                                                                                                                                                                                                                                                                                                                                                        | 골든 값이 또 어긋났을 때 · 백테스트 정확성을 대외 주장해야 할 때                                                | M            | 2026-08-07 backtest-fidelity                                 |
| [BL-631](#bl-631) | ✅ **소유자 없던 검사기 2종에 `docs-audit.sh` 를 붙였다** — ★★그전까지 **`runtime-check.mjs` 는 어느 게이트에도 안 붙어 죽은 채로 방치됐다** — `docs/` 재편 커밋 `fcc36bf7` 이후 playwright import 상대깊이가 안 따라와 `ERR_MODULE_NOT_FOUND` 로 즉사했고, 그래서 핸드오프 §8.5 의 **「다크 17벌 17/17 PASS」는 그 커밋 이후 한 번도 재현된 적 없는 숫자**였다(이번 회차가 고쳐 재현). 뿌리는 경로가 아니라 **소유자 부재** — `pnpm test`·CI·`docs-audit` 어디도 안 부른다                                                                                                                                                                                                                                                                                                                      | 다음에 `docs/` 를 재편하거나 프로토타입을 손대기 **전에**                                                       | S            | 2026-08-07 backtest-fidelity                                 |
| [BL-624](#bl-624) | ★**게이트의 HTTP 갈래는 `PROMETHEUS_BEARER_TOKEN` 과 양립 불가** — `soak-gate.sh` 의 `curl -sf` 가 인증 헤더를 안 보내서 401 → `DARKNESS=null` → **C5⑷ 영구 ✗**. `APP_ENV=production` 과 무관하다(토큰이 있으면 development 에서도 강제). 2026-08-07 FE 배포 회차가 실측으로 물렸다 — 서버 체크아웃이 [BL-620] 이전이라 기본이 HTTP 였고 베어러를 켜자 즉시 C5 가 죽었다. ★판별자는 API 로그의 `GET /metrics` 유무다 — 게이트 출력의 `darkness_computed=✓` 는 **어느 경로로 성공했는지 말해주지 않는다**. 지금은 기본이 직독이라 미발동                                                                                                                                                                                                                                                          | `QB_METRICS_URL`(원격 데몬 + ssh 터널 운영안)을 실제로 쓰려 할 때                                               | S            | 2026-08-07 fe-oracle-deploy                                  |
| [BL-620](#bl-620) | ✅ **소크 스택에 `/metrics` 를 내주는 것이 없어 게이트 C5 가 영구 ✗ 였다** — `soak-stack.sh up` 은 API 컨테이너를 안 띄우고 `:8100` 리스너가 0개라 **C1/C2 를 다 채워도 PASS 불가**였다. **Resolved** — 기본 취득을 HTTP → `backend/.metrics` **직독**으로 교체(워커가 같은 counter 를 거기 쓴다). ★PR #556 리뷰 후속: curl 갈래에도 `[ -n ]` 를 걸어 **`200 + 빈 본문` fail-open** 을 닫았고(초판은 직독 갈래에만 있었다), `QB_METRICS_DIR` 을 `.env.example` 에 등재했다(Golden Rule). 판정 `측정불가`→`진행중`, C5 전건 ✓. fail-closed 음성 대조 **3/3**. `QB_METRICS_URL` 명시 시 종전 HTTP 유지                                                                                                                                                                                             | —                                                                                                               | S            | 2026-08-07 gap-resync-autopsy                                |
| [BL-636](#bl-636) | backlog 인덱스 표 파손 + `bl-audit.sh` 가 표 파손을 감지하지 못 한다 — 수리 전 P1 조각 1행과 P2 조각 13행은 GFM 표로 렌더되지 않았고, 이번 회차에 빈 줄 제거·재결합으로 104행을 보존했지만 검사 축은 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 다음 백로그 인덱스를 편집할 때                                                                                  | S            | 2026-08-08 bl003-unblock                                     |
| [BL-637](#bl-637) | ✅ **`bl-audit.sh` 에 우선순위 배치 검사 축을 세웠다** — 수리 전 불일치 40건(뿌리는 P3 H2 아래에 인덱스 표가 아예 없어 새 P3 항목이 P2 표 꼬리에 붙은 것)을 제자리로 옮기고, 인덱스 행이 섹션 `**Priority:**` 와 같은 H2 표에 있는지를 4번째 축으로 검사한다. 주입 시험 2/2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 다음 백로그 인덱스를 편집할 때                                                                                  | S            | 2026-08-08 bl003-unblock                                     |
| [BL-639](#bl-639) | 🟡 미조인 `exchange_exits` 상시 기저율 — 배타성 판단은 과거 이력이 아니라 미체결 조건부 주문을 대상으로 해야 한다. **2026-08-08 판정식·판별력 확정**: `EXCLUSIVE ⟺ ∀ resting conditional(`reduce_only=None`) : `order_link_id ∈ {Order.id}`(`live_session_admin.py:206-256`에 이미 있다), 정상 상황 실측`FOREIGN_RESTING=0`·**오탐 0**. ★「판별력 0·34행 전량」은 계정 스코프 없이 센 값이라 **틀렸다**(좁히면 287 중 25 = 8.7%) — 결론은 유지, 근거 교체. 남은 것 = 소유권 집합의 계정 축(BL-634 소관)                                                                                                                                                                                                                                                                                          | BL-634 를 구현하기 전                                                                                           | S            | 2026-08-08 bl003-unblock → 2026-08-08 soak-attribution-close |
| [BL-642](#bl-642) | ✅ `soak-observe.sh` 가 게이트와 **같은 취득 경로**를 쓴다 — 기본 `.metrics` 직독, `QB_METRICS_URL` 명시 시 HTTP(`0f7f9342`). 5경로 격리 검증 5/5, 음성 대조 rc=7. 취득과 series 필터를 분리해 「매치 0건」이 「스크레이프 실패」로 읽히던 인접 fail-open 도 닫았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | — (해결됨. 서버 실행 검증은 다음 재기동 ⑺)                                                                      | XS           | 2026-08-08 bl003-unblock                                     |
| [BL-643](#bl-643) | ✅ `docs/status.md` 진입점의 최신성을 `docs-audit.sh` 가 집행한다 — 술어 2개(⓪ 표 행수 **≥3** · 살아 있는 **`다음 행동 =`** ≤1). ★★낱말이 아니라 **구문**을 재서 오탐 0(설명 문장은 `=` 가 없다) ★★★**파일 전체로 센다** — 실제 사고 2건은 서로 다른 섹션에 하나씩이라 「블록당 1개」로는 통과했다. 변이 **6/6**, 음성 대조 `ce583eef^` 2건 검출. 한계 = 모순 탐지기이지 낡음 탐지기가 아니다                                                                                                                                                                                                                                                                                                                                                                                                    | — (해결됨. 게이트가 매 실행 집행)                                                                               | S            | 2026-08-08 bl003-unblock                                     |
| [BL-650](#bl-650) | ★**Turbopack 영속 캐시(`.next/dev`)가 무한 성장하고 낡은 산출물을 계속 준다** — 1.99GB 까지 자란 상태에서 `next dev` 가 **요청 0건·클라이언트 0개**로 **417% CPU / 1000MB** 를 상시 소모했고(치우면 **0.1%** / 374MB) fork 고갈로 셸·playwright·머신을 함께 죽였다. 또 변이한 CSS 가 **서버 완전 재기동을 넘어** 낡은 채로 서빙돼 음성 대조를 거짓 통과시켰다 — `rm -rf .next` 로만 풀린다. 🟡 2026-08-08: 낡은 디렉터리 **5벌 8.5GB** 삭제(26G→18G) + `make fe` 1GB 경고. ★★**재현 실패가 결과다**(593MB 에서 idle **0.1%**) · **`turbopackMemoryLimit` 은 존재하지 않는다** ⇒ 원안 ① 폐기                                                                                                                                                                                                      | dev 서버가 느려지거나 CSS 변경이 안 먹을 때 · 캐시 상한/청소 정책을 정할 때                                     | S            | 2026-08-08 fe-canon-and-responsive                           |
| [BL-651](#bl-651) | ✅ **거래소 조회 루프 `exchange_uid` dedup** — 중복 계정 행이 배타성 판정식의 **개수**를 2배로 부풀린다 — 실측 `RESTING_CONDITIONAL=2` 인데 실제 조건부 주문은 **1건**(같은 `link=dd58ef44` 가 두 계정으로 계상), 포지션도 2행. `EXCLUSIVE`(존재 판정)는 배수에 불변이라 지금 깨지는 것은 없고, **개수를 문턱으로 쓰는 순간** 틀린다. BL-605 처방(스윕 루프)은 **이 자리를 안 고친다** — 여기는 거래소 조회 루프다                                                                                                                                                                                                                                                                                                                                                                               | BL-634 가드가 resting 개수를 문턱으로 쓰기 전                                                                   | S            | 2026-08-08 soak-attribution-close                            |
| [BL-653](#bl-653) | ✅ **게이트가 자기 해상도를 자백한다 (처방 ⑶ — 판정 불변)**. ①(표본 기반) 정체에 `lag N분 (표본 간격 중앙 …/최대 … · 크기 N배[, 구분 불가])` 병기 · 실격 0건 실행도 `표본 해상도:` 한 줄 ⇒ **「C3 실격 0」을 「정지 없음」으로 못 읽는다**. ★「구분 불가」 = 크기 < 표본 최대 간격 × 2(정체를 가로지르는 표본이 둘도 안 되면 크기는 하한일 뿐). ★★**②(종단 lag)에는 붙이지 않는다** — `deactivated_at`×`last_evaluated_bar_time` 둘 다 DB 값이라 표본에 의존하지 않는다. 아무 데나 붙이면 정확한 값을 깎아 표시가 무의미해진다. 변이 3/3 red(문턱 0.0/1e9/주석 no-op) · 실측 재현(간격 31.0분 → 크기 1.1배 구분 불가) · N 판정 비트 diff 공집합                                                                                                                                                  | BL-619 재관측 시 / 게이트 실격 판정을 신뢰해야 할 때                                                            | S            | 2026-08-08 soak-mortality-repair                             |
| [BL-654](#bl-654) | 증거금 게이트가 **진입 비용을 안 본다** — `_can_afford_entry` 와 `_open_trade` 최종 검증 둘 다 초기 증거금만 비교하고 **바로 아래에서 차감하는 진입 leg 비용**을 빼지 않는다. 고레버리지에서 갈린다: 자본 $1,000 · 125x · 비용률 0.069% · 명목 $118,750 은 증거금 $950 으로 **통과**하는데 진입 수수료 $81.94 후 `gate_equity` 가 **$918.06 < 950** 이라 유지 증거금을 못 댄다. [BL-460] 이 고친 것은 gross/net 축이고 **이 축은 선재**다                                                                                                                                                                                                                                                                                                                                                        | 고레버리지 백테스트를 신뢰해야 할 때 / [BL-466] 후속                                                            | S            | 2026-08-08 soak-mortality-repair (codex challenge P1)        |
| [BL-655](#bl-655) | `dedupe_accounts_by_exchange_uid` 는 **쓰기 가능한 형제 행이 둘이면** 주문을 누락한다 — 스윕이 대표 `account.id` 로만 매칭·backfill 하므로(`trading.py:1949`·`:1987`·`:2027`) 버려진 형제에 달린 주문의 청산이 `unknown` 이 되고 `realized_pnl` 이 미동기화된다. ★**현재 데이터에선 발화하지 않는다** — 실측 형제 2행 중 하나가 `read_only=t` 라 대표 선택 규칙 ⑵ 가 쓰기 가능한 행을 고른다. 막는 **DB 제약이 없다**는 것이 위험의 실체다                                                                                                                                                                                                                                                                                                                                                       | 같은 `exchange_uid` 에 쓰기 가능한 행이 2개 생기면 / 실자금 전환 전                                             | S            | 2026-08-08 soak-mortality-repair (codex challenge P2)        |
| [BL-656](#bl-656) | ✅ **⓿ 가 `soak-stack.sh ps`(신설, DB 무접촉)로 갈래를 고른다** — 완전 down 이면 **조회보다 먼저** `pin → up` + ⑷·덤프 건너뛰기. red→green: 같은 가짜 트리에서 `rc=2`·스택 호출 **0건** → `rc=0`·**`ps pin up`**. ★★★⓿ 를 ⑴ 앞에 뒀다가 red 에 잡혔다 — 거기선 원장 조회가 먼저 죽어 손으로 `--strategy-id` 를 줘야 한다(= 없애려던 손 절차). ★★★**결함 ①은 회귀해 있었다** — 「정적 카운트 0건으로 동결」이라 적었지만 **그 카운트를 도는 게이트가 없었다.** 신설 `soak-restart-test.sh`(14 단언 · 오라클 = 호출 순서)를 `final-gates.sh` 에 붙였다. 변이 4/4                                                                                                                                                                                                                                   | 다음 소크 재기동 시                                                                                             | S            | 2026-08-08 soak-mortality-repair (P7)                        |
| [BL-657](#bl-657) | ✅ **게이트가 어느 DB 를 봤는지 헤더 한 줄로 찍는다** — `대상: <컨테이너> <host:port>/<dbname> · docker <endpoint> · 실행 <hostname> · 분류기 <host:port/db>`. ★★**BL 본문의 「`DATABASE_URL` 을 따라간다」는 C1~C5 에 대해 거짓** — `_q()` 는 `docker exec ${DB_CONTAINER} psql` 이라 갈리는 축은 **docker 데몬+컨테이너**다. `DATABASE_URL` 은 분류기 전용이지만 `unverified_hours` 로 C1 을 깎으므로 함께 찍는다(한쪽만 찍으면 새 fail-open — 실측으로 이 워크트리는 둘이 어긋난다). 변이 2/2 헤더 추종 · 음성 대조 판정 비트 전건 불변(벽시계만 차이) · 비밀번호 누출 0                                                                                                                                                                                                                      | 다음 게이트 실행 시 / 게이트 숫자를 인용하기 전                                                                 | S            | 2026-08-08 session-handoff                                   |
| [BL-707](#bl-707) | ★**authed e2e 실패 메시지가 「API 도달 불가」를 「데이터 없음」으로 오지목한다** — 12건이 `make seed`·「시딩 필요」를 지시했지만 실제 원인은 BE 가 `:8100` 에 없었던 것이고, `make seed` 는 전건 「이미 존재」였다. **「데이터가 없다」와 「데이터를 못 가져온다」는 화면에서 똑같이 비어 보인다.** 처방 = 그 단정들 앞에 **API 도달성 프로브**(1회 fetch + 콘솔 `ERR_CONNECTION_REFUSED` 카운트)를 두고, 도달 불가면 시딩이 아니라 **그 사실**을 말하게 한다                                                                                                                                                                                                                                                                                                                                    | authed e2e 를 다시 손댈 때 / 같은 오진이 재발할 때                                                              | S            | 2026-08-12 surface-demo-pack                                 |
| [BL-708](#bl-708) | ★**`design-canon-calibration` 의 대비 측정이 회차마다 다른 파일에서 실패한다** — 3회 실행의 실패 집합이 `{screen-10}` → `{screen-08, screen-15}` → `{}` 로 **서로 겹치지 않는다**(실측값 `5.41:1` vs `5.82 필요`, 계산 폰트 10.08px). 「하드 실패 0」 계약이 **무증거로 새는 창**이 있다는 뜻이다. 처방 = 대비 계산의 비결정 원천(안티에일리어싱·소수 폰트 크기 반올림)을 고정하거나, 문턱 근처 값을 **WARN** 으로 내리고 하드 실패는 명확한 위반만 잡게 한다                                                                                                                                                                                                                                                                                                                                    | 캐논 감사 코어를 손댈 때 / 이 플레이크로 게이트가 막힐 때                                                       | S            | 2026-08-12 surface-demo-pack                                 |
| [BL-714](#bl-714) | ★**마감 게이트가 전제하는 브랜치 상태가 문서에 없다** — `signal-check.sh` 의 앵커 A1 이 `merge-base == HEAD` 를 **먼저** 보고 `no-branch-commits` rc=1 을 내므로, 회차를 증분 머지해 main 이 깨끗해진 뒤에는 신호 4종이 **구조적으로 초록이 될 수 없다**(sha 가 HEAD 와 같아도 A2 에 닿지 못한다). A1 자체는 옳다 — 그것이 없으면 main 에서 아무 신호나 통과한다. 갭은 **문서**다: §G8 과 ⓸ ④ 는 「마지막 커밋 뒤 게이트」라고만 하고 **「그 커밋이 아직 머지되지 않은 브랜치에 있어야 한다」를 말하지 않는다**. 2026-08-12 회차가 CI 확인 후 즉시 머지(사용자 결정)했다가 정확히 그 상태에 빠졌다                                                                                                                                                                                               | 마감 절차를 다시 쓸 때 / 같은 상태에 또 빠질 때                                                                 | XS-S         | 2026-08-12 surface-demo-pack                                 |

> Resolved P2 = BL-027/137/140/140b/141/144/150/152/176/178/180/181/183/184/185/187/187a/188/188a/189/200~206/219~234/237 + 30+ Sprint 16~30 stale (`_archived.md`). + BL-603 (2026-08-07 gap-resync-autopsy). + BL-597 (2026-08-06 entry-set-divergence).

### BL-186

**상태:** 🟡 **부분 Resolved (BL-186a, 2026-07-26 backtest-trust)** — 격리 단일 tier 레버리지 모델은 착지, **잔여 = BL-186b**(cross 마진 · tier 계단 MMR · 파산수수료 · 멀티거래소 · 펀딩-청산 상호작용). 근거: 본 섹션 `**🔸 부분 Resolved (BL-186a):**` 줄 · `docs/roadmap.md:114` `[x] BL-186a` / `docs/roadmap.md:115` `[ ] BL-186b`.
**트리거 판정:** 미도래 — 외생 조건. Trigger 줄의 「Sprint 38+」는 만료된 좌표지만 **본문이 진짜 게이트를 적었다** — 원인/영향의 「실제 dogfood / Beta 사용자가 high-leverage strategy 운영 시」. Beta 미도달이고 선행 BL-185 는 섹션이 없어 기계가 못 읽는다 (2026-08-11 bl-703-partial-verdicts)

**Title:** Full leverage + funding rate + maintenance margin + cross/isolated margin + liquidation 풀 모델
**Category:** 트랜잭션 / Risk / Pine v2
**Priority:** P2
**🔸 부분 Resolved (BL-186a):** 2026-07-26 backtest-trust 스프린트. **격리(isolated) 단일 tier 모델을 TV/MT5 컨벤션으로 구현.** ★**레버리지는 주문 수량을 바꾸지 않는다** — 1차 출처 조사(TV `margin_long/short` % · MT5 계좌 레버리지→필요증거금 · QC `SetLeverage`=매수여력 상한. 거래소 UI 조차 곱하는 대상은 _증거금_ 입력)로 확인해 핸드오프의 "사이징 × leverage" 안을 폐기했다. 따라서 **`compute_qty` 무변경 → 레버리지>1 에서도 TV parity 유지**.
구현: `pine_v2/leverage_model.py`(순수 수식, 라이브 `trading/liquidation.py` 와의 일치를 **216 케이스 parity 테스트**로 강제) + **단일 chokepoint `_open_trade()`**(마진 게이트 + 청산가. ★`Trade` 생성 site 가 `entry()` 와 `check_pending_fills()` **2곳**이라 `entry()` 에만 걸면 stop 진입이 뚫린다 — codex G0 적발) + `check_liquidations()`(양 루프, `check_exit_fills` **앞** = 비관적) + `RawTrade.liquidated` → metrics 4-site → DB `exit_kind='liquidation'`(★`ExitOrderKind` **enum 미확장** — `exit_order_mapping.py:48` else fall-through 가 BL-365 배선 시 새 값을 trigger-market 으로 빌드) + FE 레버리지 입력 재도입(Sprint 37 BL-187 제거분) + 고지 5종.
실측: **L=1 byte-identity 5 corpus** · 청산 1x=0 / 25x=8 / 100x=267(metrics·RawTrade·comment 3중 일치) · 마진 게이트가 corpus 내재 **4.2x** 를 정확 판정(3x 거부 / 10x 통과). 마이그레이션 **0**.
**잔여 = BL-186b** — cross 마진 / tier 계단 MMR / 파산수수료 / 멀티거래소 / 펀딩-청산 상호작용. 추가로 **마진 게이트가 gross 자본 판정**(신규 BL).
**Trigger:** Sprint 38+ deferred (BL-185 spot-equivalent foundation 위)
**Est:** M-L (16-24h)
**출처:** Sprint 37 BL-185 spot-equivalent 채택 후 풀 모델 후속

**원인 / 영향:** Sprint 37 BL-185 는 spot-equivalent (1x, 롱/숏) 만 보장. 실제 dogfood / Beta 사용자가 high-leverage strategy 운영 시 funding rate / maintenance margin / liquidation 정확 시뮬레이션 불가.

**권장 접근:** funding/mm/liquidation 정확 시뮬. exchange-specific (Bybit linear funding interval / Binance / OKX) parameter 화. Pine `strategy.entry(leverage=N)` 와 정합.

---

### BL-190

**Title:** PDF export (jsPDF + html2canvas client-side 또는 Playwright server-side) — backtest 결과 인쇄/오프라인 공유
**Category:** Frontend UX
**Priority:** P2 (deferrable)
**Trigger:** 외부 사용자 요청 또는 인쇄 use case 발견 시
**Est:** M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — 사용자 결정 대기: PDF 관련 코드·의존성 0건이고, Trigger 자체가 외부 사용자 요청 + client/server 방식 선택이라 사용자 결정이 선행이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** Sprint 41 Worker H 결정 — share link 충분 P1 deferrable, demo 첫인상 단계 미구현

**권장 접근:** share link 가 충분히 우선이라 demo 단계 미구현. 사용자 요청 시 jsPDF + html2canvas (client) 또는 Playwright (server-side) 둘 중 선택.

---

### BL-195

**Title:** qb-form-slide-down animation 영구 truncation (max-height 600px + overflow-hidden, 600px 초과 시 hint list 잘림)
**Category:** Frontend UX
**Priority:** P2
**Trigger:** Sprint 45 codex G.4 review 발견
**Est:** XS (30m)
**상태:** ✅ Resolved — truncation 원인이던 to{max-height:600px} 가 커밋 188273c9 에서 제거돼 현재 keyframe 에 캡이 없다. (2026-08-09 status-triage-mass 코드 대조)
**출처:** Sprint 45 codex G.4

**원인 / 영향:** `frontend/src/styles/globals.css:582` `qb-form-slide-down` `both` fill mode + `FormErrorInline` `overflow-hidden` 조합 = Pine Script 다수 미지원 함수 시 unsupported-builtins hint list 영구 truncation.

**권장 접근:** fill-mode `forwards` 제거 또는 max-height 풀림 패턴 적용.

---

### BL-235

**Title:** N-dim acquisition surface viz (3D+ surface 또는 parallel-coord, Bayesian 전용)
**Category:** Frontend UX / Optimizer
**Priority:** P2
**Trigger:** Sprint 57+
**Est:** M (8-12h, estimate)
**상태:** ⏳ 대기 (트리거 미도래) — Bayesian 시각화는 여전히 1D best_so_far inline SVG 뿐 — N차원 surface/parallel-coord 컴포넌트가 optimizer 디렉터리에 없다(2D heatmap 은 grid_search 전용). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** ADR-013 §6 #8 deferred (실체 = `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` `:202` — [BL-504]). Sprint 55 = inline SVG iteration-chart (1D best_so_far) 만 구현.

**권장 접근:** recharts 또는 plotly.js 의존성 추가 검토 + cross-page consistency 의무. Bayesian / Genetic 공용.

---

### BL-236

**Title:** `objective_metric` whitelist 자유화 (BacktestMetrics 24+ 지표 노출)
**Category:** Optimizer
**Priority:** P2
**Trigger:** Sprint 56+
**Est:** S (3-5h, estimate)
**상태:** ⏳ 대기 (트리거 미도래) — 3엔진 화이트리스트와 \_common.metric_value_for_objective switch 모두 sharpe/total_return/max_drawdown 3종 그대로 — 확장 미착수 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** Sprint 55 = `_SUPPORTED_OBJECTIVE_METRICS = {sharpe_ratio, total_return, max_drawdown}` 3종만 노출

**권장 접근:** BacktestMetrics 24 metric (sortino_ratio / calmar_ratio / win_rate / profit_factor 등) 노출 검토. `_objective_from_metrics` switch + FE select option 확장.

---

### BL-363

**Title:** stress*test `StressTestService.\_execute*\*`4-method boilerplate 추출
**Category:** Stress / Architecture (deep module)
**Priority:** P2
**Trigger:** deepening sprint 또는 5번째 stress engine 추가 시
**Est:** S (2-3h)
**상태:** ✅ Resolved — `\_RunContext`+`\_load_run_context`로 config 단일화, CA/PS 는`\_execute_grid_sweep` 위임 — 권장 처방 전부 구현됨 (2026-08-09 status-triage-mass 코드 대조)
**출처:**`2026-05-30-full-inspection.md`appendix P1-9 +`2026-06-30-stress_test-deepen.md` (deepen-modules stress_test 1차 audit — money-path 증거 + git 실증 sharpen)

**원인 / 영향:** `_execute_walk_forward`(`service.py:305-319`)/`_execute_cost_assumption_sensitivity`(`:366-384`)/`_execute_param_stability`(`:393-411`) 가 `strategy.find_by_id_and_owner → None가드 → provider.get_ohlcv → build_engine_config_from_db(bt)` prefix 를 복붙. **CA↔PS 본문은 19-LOC 중 3토큰만 차이**(에러문자열 + `run_*` engine fn + `*_to_jsonb` serializer fn). 이 분산된 boilerplate 가 실제 money-path silent corruption 으로 **한 번 물었음** — git `6c7adfba`(Sprint 52 BL-222: `build_engine_config_from_db` 를 CA/PS 에만 추가, **WF 누락**) → `ffb2299b`(WF 별도 패치). docstring `service.py:298-304` 가 증언: WF 의 IS/OOS 백테스트가 parent 의 fees/slippage/init_cash/leverage/sizing 대신 엔진 기본값으로 실행. config-build 변경 시 3곳(`:319/:377/:404`) 수동 동기화 의무 → 1곳 누락 = Celery run 성공·결과 silent 오염. 5번째 engine 도 동일 누락 위험.

**권장 접근:** `_load_run_context(st, bt) -> RunContext(strategy, ohlcv, backtest_config)` helper 추출(MC 는 equity_curve 기반이라 비대상) → `build_engine_config_from_db(bt)` single-site 화 = **BL-222 drift class 구조적 제거**. CA/PS 는 `_execute_grid_sweep(st, bt, *, engine_fn, to_jsonb)` 1메서드로 통합(engine 의미는 인자로 주입, 분리 유지). behavior-preserving 순수추출 — 기존 per-engine propagation 테스트(WF+CA+PS 각 1건) + state-isolation 가드가 안전망. **C2(BL-392) 와 묶으면 자연스러움**(grid-sweep DTO 통합과 동일 CA/PS 응집부).

---

### BL-364

**Title:** Optimizer 진짜 string-label CategoricalField sweep (Genetic + Bayesian)
**Category:** Optimizer / Feature
**Priority:** P2
**Trigger:** 사용자 string 카테고리 sweep 요청 시 (예: maType ∈ {ema,sma,wma})
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — GA·Bayesian 둘 다 비숫자 라벨을 여전히 명시 거부하고(BL-364 주석 포함), 테스트가 그 거부를 고정하고 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-05-30-full-inspection.md` appendix P1-9 (S4 Option A 후속)

**원인 / 영향:** S4(Option A)는 비숫자 CategoricalField 를 명확히 거부(InvalidOperation 크래시 차단)했으나, 스키마 docstring 의 본래 의도(`pine input.string / 사용자 정의 선택지` = `['ema','sma']`)는 미지원 상태. GA/Bayesian 이 individual 을 Decimal(ordinal)로 표현하기 때문.

**권장 접근:** ordinal 인코딩 — GA/Bayesian 이 categorical 차원을 index(Decimal 0..N-1)로 sample/mutate, backtest 호출 시 `field.values[int(idx)]` 로 string 디코드하여 input override 전달, best-params 에서 라벨 복원. Genetic `_sample_individual`/`_gaussian_mutation`/run-loop + Bayesian `_coerce_skopt_to_decimal`/skopt `Categorical(transform="label")` 양쪽 일관 처리. (S4 에서 사용자 결정 = Option A 우선, 본 feature 는 후속.)

---

### BL-366

**Title:** live-signal dispatch 의 OrderService DI 인라인 조립 중복 (HTTP `get_order_service` 와 drift)
**Category:** Trading / Architecture (locality / DI-dup)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 OrderService 의존성 추가 시
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — 공유 factory(create_order_service_for_dispatch)는 레포에 없고, OrderService+킬스위치 인라인 조립이 dispatch 2곳·recovery 1곳·HTTP DI 로 4중 중복이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**원인 / 영향:** `tasks/live_signal.py:650-682` 가 OrderService + 9 deps(order/account/kse repo, crypto, `BybitFuturesProvider()`, exchange_svc, 2 evaluator, ks_svc) 를 **인라인 조립** — `dependencies.py get_order_service`(HTTP 경로) 와 별도. 신규 인스턴스 vs singleton provider, threshold 값 등 **config drift** + 한쪽만 테스트되는 blind spot. money-path 조립이라 drift 시 dispatch 와 HTTP 가 다른 동작.

**권장 접근:** 공유 factory `create_order_service_for_dispatch(session, crypto=None)` 추출 → HTTP `get_order_service` 와 Celery dispatch 양쪽이 호출. (트레일링 안정화 후 — money-path churn 회피.)

**영향 파일:** `tasks/live_signal.py` + `trading/dependencies.py` + (선택) 신규 factory module.

**Risk:** 🟡 (money-path 조립 — CCXT 호출 전 조립 경로라 신중).

---

### BL-368

**Title:** `_merge_exit_params` 가 ccxt 키명 문자열을 3 call site 로 누설 (shallow interface)
**Category:** Trading / Architecture (shallow interface / information hiding)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 4번째 provider / exchange 추가 시
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — `_merge_exit_params` 가 여전히 키명 인자를 받고 3 call site 가 "orderLinkId"/"triggerBy"/"clOrdId" 문자열을 그대로 넘긴다. `build_ccxt_params_for_order` 는 레포에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**원인 / 영향:** `providers.py:135-207` 의 `_merge_exit_params` 가 `client_order_id_key`/`trigger_by_key`/`trigger_direction_key`/`trailing_stop_key` 등 **ccxt 필드명을 caller 가 알아야 하는 param** 으로 받음 → 3 call site(`:299/:480/:752`)가 `"orderLinkId"`/`"triggerBy"` 등 문자열을 분산 보유. exchange-specific 지식이 함수 안에 은닉되지 못함 → 새 exchange 추가 시 call site 마다 키 지식 복제.

**권장 접근:** `build_ccxt_params_for_order(exchange_name: ExchangeName, order: OrderSubmit) -> dict` 로 exchange→키명 dispatch 를 함수 내부로 은닉 (call site 는 ExchangeName 만 전달). lateral move + money-path 라 ccxt 전수 검증 필요.

**영향 파일:** `providers.py` (`_merge_exit_params` + 3 call site).

**Risk:** 🟡 (money-path ccxt 전수 검증).

---

### BL-369

**Title:** 3 provider `create_order` 의 try/except/finally + receipt 정규화 ~40 LOC 복붙
**Category:** Trading / Architecture (DRY / locality)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 provider 예외 처리 변경 시
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — 권장 helper(\_execute_create_order_with_ccxt) 가 레포에 없고 3 provider 의 try/except/finally+receipt 블록이 그대로 중복돼 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**원인 / 영향:** `providers.py:279-349`(BybitDemo) / `:431-529`(BybitFutures) / `:728-795`(OkxDemo) 의 `create_order` 가 동일한 `try / except ProviderError / except ccxt BaseError / except Exception / finally close` + receipt 정규화 ~40 LOC 를 character-identical 복붙. 예외 처리 1곳 변경 시 3곳 동기화 누락 위험.

**권장 접근:** `_execute_create_order_with_ccxt(exchange, symbol, type, side, amount, price, params, timer_label) -> OrderReceipt` helper 추출 → 각 provider 는 client 구성 + helper 호출. money-path 라 거래소별 미세 차이 보존 검증 필요.

**영향 파일:** `providers.py` (3 provider create_order).

**Risk:** 🟡 (money-path — 거래소별 분기 보존 검증).

---

### BL-372

**Title:** STEP B 트레일링 live-placement — 3-리뷰어 검증 follow-up 번들 (9 항목)
**Category:** Trading / money-path / Architecture / Security / Tests
**Priority:** P2 (bundle — 개별 항목 P2/P3 혼재)
**Trigger:** Wave 3 실자금 cutover 전 (데모 기간엔 고정 bracket SL floor 가 모든 손실 경로 보호)
**Est:** M (6-10h, 항목별 분리 가능)
**상태:** ⏳ 대기 (트리거 미도래) — 9항목 중 tick정규화·ccxt assert·docstring·hedge가드·alert정제·회귀테스트·dead param은 구현됨, 하드코딩 BybitFuturesProvider() registry 우회(trading.py:1369-1371)만 잔존 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-26 트레일링 PR 3-리뷰어 검증 (codex CLI + Opus 6-lens 워크플로 + adversarial verify). P1 blocker 0.

**원인 / 영향:** STEP B 머지 전 Tier-1(false-flat 재시도 + 3 P2 테스트)은 본 PR 에서 해소. 아래는 adversarial 검증 통과한 잔여 follow-up. 전부 degraded-protection / 방어심화 / 문서 수준 (현재 무버그 또는 narrow). 라이브 실자금 진입 전 처리 권장.

- **(P2, money-path) same-side stale 오부착** — 🟡 **Mitigated — common path (2026-06-29, `fix/trailing-372-same-side-stale`).** `_do_place_trailing_stop` 가드가 flat/flip 만 차단하던 것에 **createdTime ↔ filled_at 불변식** 추가: `PositionInfo.created_at`(Bybit raw `info.createdTime`/`createdAt`, ADD 시 불변 — ccxt normalized `timestamp` 가 아닌 raw 사용으로 ADD 오탐 회피[G1]) > `order.filled_at` + 2s tol → reopened 판정 → benign skip(`skipped_position_reopened` metric). 타임스탬프 결측 시 side-only degrade. placement 창의 **common(>2s) 구간을 닫음**(원 버그의 ~30s 창 대부분). 검증 = G1 codex(GO_WITH_FIXES) → TDD(매핑 4 + 가드 7 + session 전달 1 + helper 단위 1) → G2 codex(NO_GO=완전성 기준, 잔여 지적) + G3 fresh(SOUND, **mutation 4/4 catch**). **잔여(narrow, 전부 [BL-375](#bl-375)): (a) sub-2s reopen (b) fetch↔set TOCTOU (c) reconcile-lag late filled_at (d) worker clock-skew>2s false-skip.** 데모 기간 = 고정 bracket SL floor 가 손실 경로 보호. (이력) codex Evaluator(2026-06-28) [P1] = 실자금 cutover 전 필수 → common path 해소, 완전 닫기는 BL-375(거래소 fill-time).
- **(P2) tick-normalization** — `set_trading_stop` 가 `trailingStop` distance 를 price precision 정규화 없이 raw `str(Decimal)` 전송 → coarse-tick 심볼 Bybit 거부 가능(fail-safe: 거부→retry→critical alert). `providers.py:586-591`.
- **(P3, architect) 하드코딩 provider** — `_place_trailing_stop_with_session` 가 `BybitFuturesProvider()` 직접 생성, dispatch registry 우회(LESSON-063). Protocol 미노출 강제 + live=BL-003 stub 라 현재 무버그. 2nd native-trailing 거래소 추가 시 SSOT 라우팅. `tasks/trading.py:954-958`.
- **(P3, architect) hedge-mode 가정** — `fetch_position` first-size>0 = one-way mode 암묵 가정. hedge-mode 면 wrong-leg 가능(expected_side 가드가 benign skip 으로 중화). 문서화 또는 side/positionIdx 필터. `providers.py:637-644`.
- **(P3, money-path) docstring 모순** — `set_trading_stop` docstring 이 "독립 fetch_position 사후검증" 주장하나 미구현(ccxt retCode raise 로 실거부는 잡힘). 주석 정정 또는 재조회 구현. `providers.py:598`.
- **(P3, security) kill-switch bypass 2nd-line 부재** — trailing placement 가 kill-switch 우회(엔드포인트가 포지션 증가 불가 전제). `reduceOnly`/`positionIdx`/ccxt-version-assert 등 belt-and-suspenders 없음. one-way 모드선 exit-side market 이 포지션 close 라 framing 다소 과장. `providers.py:600` / `tasks/trading.py`.
- **(P3, security) alert 정보 노출** — catch-all `str(exc)` 가 미정제로 Slack 전송(사설 채널, api_secret 부재이나 sign-error 시 public apiKey/params 가능). classified reason 만 전송 + raw 는 `logger.exception`(team 기존 stance `providers.py:357` 정합). `tasks/trading.py:980-990,1007-1015`.
- **(P3, qa) 회귀 가드 2건** — `leverage is None` spot-skip 분기 + `expire_on_commit=False` 불변식 (4 enqueue 사이트 post-commit attr read load-bearing) 전용 테스트 신설.
- **(P3, ponytail) dead param cut** — `set_trading_stop` 의 `trigger_price`/`trailingTriggerPrice`(activePrice) 라이브 caller 0 + 그 테스트(~17L) 제거 (activation-price 스토리 실현 시 재추가).

**Risk:** 🟢 (전부 degraded-protection / 방어심화 / 문서 — 데모 기간 bracket SL floor 보호).

---

### BL-373

**Title:** OCO 형제취소 (sibling-cancel) — standalone exit order 시점에 구현
**Category:** Trading / money-path
**Priority:** P2 (defer)
**Trigger:** BL-365 standalone-trigger 발주 도입 시 (= app-side OCO 가 실제 필요해지는 시점)
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — oco_group_id 컬럼·전달만 존재하고 코드 주석이 여전히 'Wave 2 deferred' — sibling-cancel 오케스트레이션 코드는 레포에 없고 Trigger(BL-365 standalone 발주)도 미도래 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-28 grilling (트레일링 후속 scope 결정)

**원인 / 영향:** `oco_group_id` DB 컬럼 + OrderSubmit 전달은 이미 존재하나 sibling-cancel 오케스트레이션은 미구현. 현재는 entry-attached bracket 이라 거래소가 네이티브 OCO(한 다리 체결 시 형제 자동취소)를 처리 → app-side sibling-cancel 은 YAGNI. standalone exit order(BL-365) 발주 시점에 두 다리가 독립 주문이 되면 그때 app-side 형제취소가 필요.

**Risk:** 🟢 (현재 네이티브 OCO 로 커버 — defer 안전).

---

### BL-379

**Title:** pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐)
**Category:** Strategy / pine_v2 (interpreter)
**Priority:** P2 (latent harm-class — 코퍼스 8종 미트리거, 흔한 패턴)
**Trigger:** pine_v2 robustness 후속
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — \_eval_subscript 가 여전히 \_var_series 만 보고 \_scope_stack 을 안 봄 — 추적도 unsupported reject 도 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA codex G2 challenge + 직접 재현

**원인 / 영향:** `_eval_subscript`(interpreter.py:653)가 `x[1]`을 `_var_series`에서만 조회하는데, user function(`f(s) => ...`) 지역변수는 `_var_series`에 append 되지 않음. 재현: `f(s) => prev = s[1]` → `[nan]*N`(항상 na) vs top-level `close[1]` 정상. 코퍼스 8종은 미트리거(전부 인라인/builtin) 이나 `f(x)=>...x[1]...` (지표 함수 내 history 참조) 는 흔한 패턴 → 해당 전략 silent divergence. **권장:** user-function 스코프 변수 history 추적 또는 명시적 unsupported reject.

---

### BL-380

**Title:** Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반)
**Category:** Strategy / pine_v2 (Trust Layer / Track A)
**Priority:** P2 (신뢰 표면)
**Trigger:** Track A 신뢰 표면 sprint
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — INFORMATION/UNKNOWN 이 여전히 무경고 continue 이고, v2_adapter 는 state.warnings 만 전파해 VirtualRunResult.warnings 유실 그대로. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA LuxAlgo 0-trade 추적 + codex G2

**원인 / 영향:** `virtual_strategy.py:128-130` 가 INFORMATION/UNKNOWN alert 를 경고 없이 `continue` (docstring `:12` 은 "무시 + warning" 약속 — 계약 위반). LuxAlgo `alertcondition(.., 'Price broke the down-trendline upward')` → strict 기본 INFORMATION 키워드 `\btrendline\b` → 무경고 무시 → **0 trades, status=ok** (지표 수치는 정확). loose 모드(opt-in)면 directional. **추가:** 경고를 추가해도 `run_backtest_v2`(v2_adapter.py:181)가 `state.warnings`만 내보내 `VirtualRunResult.warnings` 유실. **권장:** (a) ignored actionable alert 시 wrapper.warnings 기록 + (b) VirtualRunResult.warnings → backtest parse warnings 전파. (strict 기본 정책 자체는 유지.)

---

### BL-381

**Title:** Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허
**Category:** Strategy / pine_v2 (Trust Layer CI)
**Priority:** P2 (meta / 검증 인프라)
**Trigger:** Trust Layer CI 강화
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — VirtualRunResult 에 warnings 만 있고 var_series 필드·반환이 여전히 없어 추출기 getattr 이 빈 dict 를 digest 한다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA codex G2 + diff-challenge

**원인 / 영향:** `VirtualRunResult`(virtual_strategy.py:61) 에 var_series 필드 부재 + 미반환. `test_trust_layer_parity.py:239` 의 golden 추출기가 `getattr(.., 'var_series', {})` → 빈 dict digest. 결과: Track A 전략(i2_luxalgo 등)의 지표 변화(예: ta.atr→slope)가 var_series_digest 에 반영 안 됨 → documented P-3 parity 검증이 부분 공허(BL-378 fix 시 i2_luxalgo baseline 불변이 이를 노출). **권장:** VirtualRunResult 에 var_series/warnings 노출 + 추출기 배선.

---

### BL-382

**Title:** qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성)
**Category:** Backtest / 투명성
**Priority:** P2 (투명성)
**Trigger:** sizing 투명성 sprint
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — BE 는 sizing_source 를 config JSONB 에 저장하지만 BacktestConfigOut 에 없고, FE schemas.ts·AssumptionsCard 어디에도 sizing 표면화가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA F1 (codex G2 = harm-class 아닌 transparency)

**원인 / 영향:** `default_qty_type` 미지정 전략(PbR/UtBot)은 qty=1.0 (1 BTC/trade ≈ $42k notional vs $10k capital) → mdd=-16.95/-41.47, fees $156k. 엔진은 `mdd_exceeds_capital=True` 정직 flag + FE KPI 가 자본초과 손실 표시. **그러나** sizing_source 가 FE 결과 schema 부재(schemas.ts:254), AssumptionsCard 가 "1 BTC 고정수량 fallback" 미표면화(assumptions-card.tsx:88). **권장:** config 응답에 sizing_source/default_qty 포함 + fallback 시 경고 표시.

---

### BL-383

**Title:** v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)
**Category:** Backtest / engine (관측성)
**Priority:** P3
**Trigger:** pine_v2 관측성 후속
**Est:** S (2-3h)
**상태:** 🟡 부분 해결 — 실행단계 PineRuntimeError·ValueError 는 이미 status=error 로 분기됐고, 잔여는 144줄 catch-all(+이를 고정한 테스트 1건)뿐. (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 동승 조건(pine_v2 관측성 후속). 잔여는 `v2_adapter` 144줄 catch-all 하나뿐이라 단독 착수 시 값이 0이다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-06-30 QA codex G2 (G1 에서도 지적)

**원인 / 영향:** `v2_adapter.py:126-133` generic `except Exception` → `status="parse_failed"`. parse 성공 후 실행 중 예외(TypeError 등)도 "parse failed"로 표시 → 사용자 원인 분류 오도. BL-376 이 na/inf escape 는 닫았으나 catch-all 잔존. **권장:** 실행-단계 예외를 `status="error"` 로 분기(parse 단계와 구분).

---

### BL-384

**Title:** ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3 (좁은 edge)
**Trigger:** pine_v2 parity 후속
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — stdlib.py:308 이 여전히 `source is not None and not _is_na(source)` 로 na occurrence 를 skip 하고, na 기록을 강제하는 테스트도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA codex G2 + 직접 재현

**원인 / 영향:** `stdlib.py:305-307` 가 `cond_bool and source not na` 일 때만 occurrence 기록. cond=true + source=na 인 occurrence 를 TV 는 기록(na 반환), QB 는 skip → 이전 non-na 반환. 재현: src=[10,na] → `valuewhen(cond,src,0)` QB=10, TV=na. RsiD `valuewhen(plFound, osc[lbR], 1)` (osc warmup 시 na) 후보. 좁은 edge. **권장:** cond=true occurrence 는 source 가 na 여도 기록.

---

### BL-385

**Title:** PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse
**Category:** Strategy / pine_v2 (coverage / 메타데이터)
**Priority:** P3 (경미)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — PineVersion enum은 여전히 v4/v5뿐이고 \_detect_version이 v6를 v5로 반환하며, DB enum에도 v6 값이 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA F3

**원인 / 영향:** `PineVersion` enum(strategy/models.py)이 v4/v5 뿐 → `_detect_version`(strategy/service.py)이 `//@version=6`(PbR, bs)를 v5 로 보고. 메타데이터 부정확(실행엔 무영향). **권장:** v6 enum 값 추가(alembic enum-add 패턴, LESSON-066).

---

### BL-386

**Title:** v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject)
**Category:** Strategy / pine_v2 (coverage)
**Priority:** P3 (경미, 안전 측 — silent 아님)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — interpreter/coverage 양쪽 \_V4_ALIASES 에 abs/max/min 만 있고 floor·ceil·round·sqrt bare 별칭이 여전히 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 QA F4

**원인 / 영향:** `SUPPORTED_FUNCTIONS` 의 `_V4_ALIASES` 가 abs/max/min 만 포함, `floor`/`ceil`/`round`/`sqrt`(유효 Pine builtin) 부재 → v4 스크립트의 `floor()` 가 unsupported flag(preflight 차단). over-strict 이나 silent 아님(안전). **권장:** v4 bare math builtin 을 `math.*` 로 재라우팅하는 alias 추가.

---

### BL-387

**Title:** backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 으로 영속 경계 횡단 (key drift 시 silent 잘못된 sizing)
**Category:** Backtest / Architecture (shallow seam / money-path)
**Priority:** P2
**Trigger:** backtest deepening sprint 또는 sizing 로직 변경 시
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — SizingCanonical 타입 VO 미도입 — dict[str,Any] seam 그대로. 단 config 조립은 .get 이 아니라 직접 인덱싱이라 drift 는 KeyError(무음 아님). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-30-backtest-deepen.md` (codex challenge 최강 후보)

**원인 / 영향:** `service.py:754-876` `_resolve_sizing_canonical` 이 6-key `dict[str, Any]` 를 반환하고 `service.py:188-212` 가 `.get('leverage', default)` 식으로 config_payload 를 손-조립한다. 두 dict 의 key 일치가 타입으로 보장되지 않아, resolve 쪽 key 가 rename 되면 조용히 default 로 떨어져 `sizing_source`/`leverage_basis` 가 잘못 영속될 수 있다(money-affecting). `dict[str, Any]` = Interface 가 거의 없는 shallow seam 이 백테스트 입력의 진실을 DB 경계로 흘려보낸다.

**권장 접근:** sizing 결정을 typed value object(`SizingCanonical`)로 만들어 `_resolve` 출력과 config 영속 사이 Seam 에 타입 부여 → key 불일치가 검증/타입 시점에 잡히게. `test_resolve_sizing_canonical` 8-case 존재하나 resolve 출력↔config_payload key-match 단언 부재 = 부분 gap.

**영향 파일:** `backtest/service.py` (`_resolve_sizing_canonical` + config_payload 조립), `config_mapper.py`.

**Risk:** 🟡 (money-path sizing — 영속 값 parity 검증 필요).

---

### BL-392

**Title:** stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass + serializer + OutSchema)
**Category:** Stress / Architecture (parallel definition / leaky JSONB seam)
**Priority:** P2
**Trigger:** stress_test deepening sprint, 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시
**Est:** M (4-6h)
**상태:** ✅ Resolved — 공유 grid_result.py(GridSweepMetricsCell/Result)+serializer 1쌍+schema 1클래스+C4 상수 SSOT+golden 라운드트립 테스트까지 전부 구현됨. (2026-08-09 status-triage-mass 코드 대조)
**출처:** `2026-06-30-stress_test-deepen.md` (deepen-modules stress_test 1차 audit)

**원인 / 영향:** 7-field cell shape(`param1_value·param2_value·sharpe·total_return·max_drawdown·num_trades·is_degenerate`)가 **8 site 평행 정의** — engine dataclass×2(`CostAssumptionCell`≡`ParamStabilityCell` `engine/cost_assumption_sensitivity.py:42-52` / `engine/param_stability.py:51-61`, docstring 단어만 차이) + serializer to/from×4(`serializers.py:158-251`, ~70 LOC char-identical) + OutSchema×2(`CostAssumptionCellOut`≡`ParamStabilityCellOut` / `*ResultOut` `schemas.py:218-298`). `result` 는 untyped JSONB(`models.py:94`) → writer(`*_to_jsonb`)↔reader(`*_from_jsonb`) 계약 무검증 → 1곳 drift 시 비싼 Celery run 성공 **후** GET-detail 때 KeyError. 엔진 계산은 이미 `run_grid_sweep` 공유 + 필드명이 generic(`param1_value`, `fees` 아님) → author 가 한 개념임을 알면서 **절반만 deepen**(loop lift-up O / DTO 통합 X). `models.py:90-93` `result` docstring 이 CA/PS 누락 = SSOT 미유지 증거.

**권장 접근:** engine 공유 `GridSweepCell`/`GridSweepResult` dataclass 1개(param-name-generic) → CA/PS `run_*` 가 동일 타입 반환. serializer `grid_result_to_jsonb`/`from_jsonb` 1쌍. schema `GridSweepCellOut`/`GridSweepResultOut` 1클래스. **API 비파괴**: `StressTestDetail.cost_assumption_result`/`param_stability_result` 필드명 유지 + 둘 다 `GridSweepResultOut` 타입(JSON shape 동일 → FE 무영향). **over-abstraction 가드(필수)**: 엔진 _의미_(CA=fees×slippage cost 가정 / PS=pine input override) 진짜 다름 → DTO/serializer 만 통합, `run_cost_assumption_sensitivity`/`run_param_stability` fn·`_SUPPORTED_PARAM_KEYS`/`_SUPPORTED_INPUT_TYPES`·pre_validate 분리 유지(trading BL-370 over-abstraction 교훈). golden round-trip test(저장→로드 동일) + 구버전 JSONB row 하위호환 의무. **C4(cross-layer invariant: 9-cell cap·2-key·`{fees,slippage}` allowed-keys 상수 SSOT) 를 본 작업 시 자연 graft 권장**(deepen-modules 거부 항목, dev-log 보존).

**영향 파일:** `engine/cost_assumption_sensitivity.py` + `engine/param_stability.py`(dataclass → 공유 import), 신규 `engine/_grid_result.py`(또는 `engine/_common.py` 확장), `serializers.py`(4 fn → 2), `schemas.py`(CellOut/ResultOut ×2 → 1).

**예상 LOC delta:** +30 / -90 (net ~-60).

**Risk:** 🟡 (직렬화 round-trip + 응답 schema — golden test 필수, 구버전 row 하위호환). **C1(BL-363) 와 묶으면 CA/PS 응집부 단일 sprint.**

---

### BL-377

**Title:** pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P3
**Trigger:** pine_v2 robustness 후속 또는 실자금 cutover 전 (BL-376 후속)
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — entry stop/\_num 은 여전히 \_is_na 만 보고 isfinite 가드가 없고, \_coerce_length 에도 maxsize 상한이 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-30 BL-376 G2 codex challenge [P1#3/#4] + G3 fresh review [LOW]

**원인 / 영향:** BL-376 이 na/inf 의 raw-예외-escape harm class 를 닫았으나, 다음 2종 잔여는 escape 가 아니거나(deterministic 오값) 별도 trigger 라 BL-376 scope 밖으로 이연:

- **non-finite 주문/청산 가격:** `strategy.entry(stop=inf)` / `strategy.exit(stop|limit|profit|loss|trail=inf)` 는 실측상 raw 예외 escape 가 **아니라** status='ok' + 무-NaN 의 deterministic false-fill(예: inf short-stop 이 다음 bar 체결). 라이브는 이미 `_to_decimal`(isfinite) 로 drop. 백테스트 path 에 동일 isfinite drop 미러 필요(entry `stop` = `interpreter.py:1265`, exit `_num` = `interpreter.py:1325-1340`).
- **초대형 유한 length OverflowError:** `_coerce_length` 는 na/inf/<1 만 차단 → `ta.sma(close, close*1e17)`(유한 ~1e19 > `sys.maxsize`) 는 통과 후 `deque(maxlen=int(huge))` 가 `OverflowError` escape(G3 실측). harm class 이나 trigger 가 비현실적이고 완전 수정은 sane max-length cap(제품 결정) 필요.
- (참고, 별도 boundary) `input.int` override `int()`(`interpreter.py:982`)에 `Decimal('NaN')` override 시 ValueError — optimizer 가 NaN override 미발행이라 도달 불가. config boundary(`BacktestConfig`) finite 검증이 더 적절.

**권장 접근:** (a) 백테스트 entry stop + `_num` exit level 에 `math.isfinite` drop 가드(라이브 `_to_decimal` 미러). (b) `_coerce_length` 에 sane upper-cap 추가(또는 `value > sys.maxsize` → None). 골든 테스트 동반.

**Risk:** 🟢 (전부 현재 deterministic 또는 비현실적 trigger — escape 아니거나 라이브 이미 안전. 실자금 cutover 전 처리 권장).

---

### BL-375

**Title:** trailing same-side stale — 완전 닫기 (거래소 fill-time 소싱 + TOCTOU/sub-tol 잔여)
**Category:** Trading / money-path
**Priority:** P2
**Trigger:** Wave 3 실자금 cutover 전 (데모 기간엔 고정 bracket SL floor 가 손실 경로 보호)
**Est:** M (4-8h)
**상태:** ⏳ 대기 (트리거 미도래) — 거래소 fill-time 소싱 컬럼·경로가 없고 코드 주석 자체가 잔여 4건을 미해결로 기록 중이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-06-29 BL-372 same-side stale fix 의 G1/G2 codex Evaluator (BL-372 가 common path 만 닫음)

**원인 / 영향:** BL-372 가드(`position.createdTime > order.filled_at + 2s`)는 placement 창의 common(>2s) 구간만 닫는다. 4 narrow 잔여:

- **(a) sub-tolerance reopen** — fill 후 2s 내 close+reopen 은 미탐(2s 는 clock-skew 흡수용 tolerance). codex G2 [P1].
- **(b) fetch↔set TOCTOU** — `_do_place_trailing_stop` 가 createdTime 을 read 한 뒤 `set_trading_stop` 보내는 ms 윈도에 reopen 되면 거래소가 현재 포지션에 부착(check-then-act inherent race). codex G2 [P1].
- **(c) reconcile-lag late filled_at** — `filled_at` 은 fill _처리_ 시각(`datetime.now(UTC)`)이지 거래소 체결 시각이 아님. reconcile 경로(watchdog/reconciler)에선 실제 체결보다 늦게 기록 → reopened `createdTime < filled_at` 이면 가드 통과. codex G1 [P1-3].
- **(d) worker clock-skew** — worker clock 이 거래소보다 >2s 느리면 정상 open 도 `createdTime > filled_at + 2s` 로 false-skip(저위험: trailing 미부착, bracket SL floor 유효). codex G2 [P2].

**권장 접근:** 근본 = **거래소 보고 체결 시각 소싱**. 4 fill-recording 경로(sync receipt / WS event / watchdog / reconciler)에서 exchange order/exec timestamp 추출 → 비교 기준으로 사용(전용 컬럼 또는 전달) → (c)(d) 해소. (a)(b) inherent race 는 거래소-side conditional(예 createdTime 조건부 trading-stop) 또는 placement 전 재확인(refetch-after-set verify)으로 좁힘. clock-skew 는 NTP 전제 문서화.

**Risk:** 🟡 (전부 narrow residual — common WS/sync path 는 BL-372 로 차단, 데모 bracket SL floor 보호. 실자금 cutover 전 처리 권장).

---

### BL-393

**Title:** pine_v2 `strategy.exit` trail_points/trail_offset 틱 단위 시맨틱스 (TV=틱\*mintick, QB=price-distance) + `syminfo.mintick` 0.01 하드코딩
**Category:** Strategy / pine_v2 (TV parity)
**Priority:** P2
**Trigger:** pine_v2 parity 후속 또는 틱 기반 exit 전략 사용자 등장 시
**Est:** M (4-6h — 실 심볼 mintick 소싱 결정 포함)
**상태:** ⏳ 대기 (트리거 미도래) — 처방 (a) 문서화만 완료; mintick 은 여전히 0.01 하드코딩이고 CCXT precision 소싱·틱 해석 opt-in config 는 코드에 전무. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint — 사용자 전략(HMA+ATR+Curvature) 커버리지 판정

**원인 / 영향:** TV 의 `trail_points`/`profit`/`loss` 는 **틱 단위**(값 × syminfo.mintick = 가격 오프셋). QB 인터프리터는 price-distance 로 해석(`interpreter.py` `_num` 근사, mintick=0.01 고정 — `interpreter.py:1131`). ATR 값을 trail_points 에 넣는 전략(사용자 전략 포함)은 TV 에선 초미세 트레일링(예: ATR 500 → $5)이 되어 승률 98%+ 의 **가짜 성적**이 나오고, QB 는 저자 의도(가격 거리)에 가깝게 동작 — 즉 발산의 원인이 TV 쪽 함정. 그러나 틱 단위를 의도한 전략은 QB 에서 발산.

**권장 접근:** (a) 발산 방향/원인을 supported-indicators 문서에 명시(완료: 2026-07-05 노트) (b) 실 심볼 mintick 소싱(CCXT market precision) + 틱 해석 opt-in config. TV 정합 모드(fill_timing 과 묶음) 시 함께 검토.

**Risk:** 🟢 (현 동작이 보수적/의도-근접. 문서화 우선).

---

### BL-460

**Title:** 백테스트 마진 게이트가 **gross 자본**으로 판정 — 수수료·슬리피지 차감 전 `running_equity` 사용
**Category:** Backtest / Risk (레버리지 모델 정확도)
**Priority:** P2
**Trigger:** 실자금 레버리지 백테스트 신뢰 필요 시 / BL-186b 진행 시
**Est:** M (설계 선행 필요)
**상태:** ✅ **Resolved** (2026-08-09 btfix) — 접근 **(a)**. 게이트 전용 net 누적치 `StrategyState.gate_equity` 신설, `_can_afford_entry`·`_open_trade` 만 본다. `running_equity` 는 **gross 유지** → `compute_qty`·Pine `strategy.equity` 불변 → L=1 byte-identity(golden **무변경** 실측). 비용률 = `fees + slippage` 를 `taker_cost_rate` 로 배선(기본 0.0 = 회귀 0, leverage≤1 은 no-op). 오라클 `test_margin_gate_net_equity.py`·`test_margin_gate_cost_wiring.py` — 되돌려 **red 8/8**, 옛 코드는 qty=17 을 **허용**하고 신규는 거절(qty=15 는 양쪽 허용). ★FE 배너 "차감 전 자본으로 판정" 이 거짓이 돼 정정. **잔여** ① 사이징(`percent_of_equity`)은 여전히 gross(BL 이 배제한 축) ② ★게이트가 TP 청산도 taker 로 쳐 **과대**계상(리포트는 BL-104 이후 maker) — 막는 방향이라 fail-closed. 초판 주석의 "모든 체결 taker" 는 **낡은 grounding** 이라 정정(`d570b2ea`).
**출처:** 2026-07-26 backtest-trust 스프린트 실측 (BL-186a 구현 중 발견)

**원인 / 영향:** `StrategyState.close()`(strategy_state.py:551)가 **gross pnl 만 누적**한다(docstring 의 "fees=0 Sprint 37 가정"). BL-186a 의 마진 게이트가 이 `running_equity` 에서 가용 증거금을 파생하므로, 거래가 쌓일수록 실제 순자산보다 낙관적으로 평가한다. 실측(`s1_pbr`, 초기 10,000): 종료 gross **+38,678.96** vs net(`total_return`) **−53,670** — 차이 약 **92,000**(465거래 × $42k notional × 0.15% × 2레그 ≈ $58,590 비용 미반영 + 복리). 즉 순자산이 깊은 마이너스일 때도 "증거금 충분" 으로 판정한다. **단 초기 판정은 정확**하다(초기 자본은 gross = net) — 실제로 corpus 의 내재 4.2x 를 3x 에서 정확히 거부했다.

**권장 접근:** `running_equity` 자체를 net 으로 바꾸면 그 값이 `compute_qty`(percent_of_equity) 입력이자 Pine `strategy.equity`(interpreter.py:1322)라 **leverage=1 byte-identity 가 즉시 깨진다**. 후보: (a) 게이트 전용 net 추정치를 별도 누적(체결 시점에 `fees`/`slippage` config 로 추정 차감) (b) `leverage > 1` 에서만 net 전환(같은 스크립트가 설정에 따라 다른 `strategy.equity` 를 보는 부작용 검증 필요). 어느 쪽이든 golden/Trust Layer 영향 분석 선행.

**영향 파일:** `strategy/pine_v2/strategy_state.py`(close/\_open_trade), `strategy/pine_v2/leverage_model.py`.

**Risk:** 🟡 (현재는 FE 배너로 정직 고지 중 — "증거금 충분 여부는 수수료·슬리피지 차감 전 자본으로 판정합니다").

---

### BL-489

**Title:** 사이징 자본이 D2 구간(진입 창 밖 / 청산 창 안)에서 일시 함몰한다
**Category:** Backend / trading (라이브 사이징)
**Priority:** P2
**Trigger:** BL-488 해소 후 (진입 이벤트 신뢰가 선행 조건)
**Est:** M (설계 선행 필요)
**상태:** ⏳ 대기 (트리거 미도래) — carry 는 여전히 bar_time < window_start 단일 절단(3445)이고 2-pass 재실행 흔적이 없다 — epoch 재계산(3562)은 다른 사고다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 live-engine-parity. 적대적 검증 지적 → 프로덕션 실증.

**원인 / 영향:** `run_live` 는 warmup 창을 flat 에서 재실행하므로 창 시작 이전에 진입한 포지션은 열려 있지 않다. `close()` 가 `None` 을 반환해 그 거래의 청산이 재현되지 않는데, 그 청산의 `bar_time` 은 아직 `>= window_start` 라 carry(`bar_time < window_start`)에도 잡히지 않는다. 진입이 창을 벗어난 순간부터 청산이 창을 벗어날 때까지(보유 기간 + 지표 warmup) 그 손익이 **0 회 계상**된다.

프로덕션 실증 (창은 정확히 300 바 = 11:50~16:49):

```
16:12Z  화면 3 건 · 5.16879987
16:49Z  화면 2 건 · 4.07002377     <- 12:34 청산(+1.09877350)이 사라졌다
        원장은 불변 3 건 · 5.16882074
```

★ 창을 벗어나서가 아니다. 그 거래의 **진입(11:50)이 창의 bar 0** 이 되어 EMA 가 재현 불가해진 것이다.

**화면 총계는 이번 스프린트에서 해결됐다** (`sum_realized_pnl_all` 원장 SSOT — 17:10Z 실측으로 화면 == 원장 확인, 이후 1.5시간 유지). **남은 것은 `initial_capital` 뿐**이며, 미수정 시절의 영구 누락이 "일시 함몰 후 복귀" 로 완화된 상태다. `test_run_live_sizing.py` 의 KNOWN_LIMITATION 테스트가 이 한계를 못 박고 있다.

**권장 접근:** (a) 2-pass — 잠정 자본으로 1회 실행해 엔진이 재현한 청산 집합을 얻고 `전체 원장 − 재현분` 을 정확한 carry 로 삼아 재실행한다. 레버리지 게이트 활성 시 진동 가능성 검증 필요. (b) entry↔close 페어링으로 진입 `bar_time` 기준 절단 — 단 **BL-488 이 진입 이벤트를 떨어뜨리므로 신뢰 불가**. (a) 우선.

**영향 파일:** `tasks/live_signal.py`, `strategy/pine_v2/event_loop.py`.

**Risk:** 🟡 (수량이 일시적으로 작아진다. 과대가 아니라 과소 방향).

---

### BL-490

**Title:** `margin_mode` 가 엔진에 전달되지 않고 청산 모델이 isolated 전용이다
**Category:** Backend / trading (레버리지 모델 정확도)
**Priority:** P2
**Trigger:** cross 계정 라이브 사용 시 / BL-186 풀 모델 진행 시
**Est:** M-L (구조 변경)
**상태:** ⏳ 대기 (트리거 미도래) — 엔진 kwargs 에 margin_mode 가 여전히 없고(주석으로 명시) leverage_model 은 MMR 0.5% isolated 단일 모델 그대로다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-186=PARTIAL (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 live-engine-parity 적대적 검증 (BL-483 구현 중).

**원인 / 영향:** `StrategySettings.margin_mode`(`cross`/`isolated`)가 엔진에 전달되지 않고 `strategy/pine_v2/leverage_model.py` 는 **isolated 전용**이다(MMR 0.5% 고정, `liquidation_price = entry x (1 - 1/lev + mmr)`). BL-483 이 `leverage` 를 배선하면서 `check_liquidations` 가 라이브에서 처음 활성화됐는데, **cross 계정은 실제보다 훨씬 이르게 강제 청산으로 판정**된다. 강제 청산은 실제 reduce-only 주문을 낸다.

레버리지별 롱 청산 임계 실측:

```
lev   2x -> 진입가 x 0.50500  (하락 49.50%)
lev  10x -> 진입가 x 0.90500  (하락  9.50%)
lev  25x -> 진입가 x 0.96500  (하락  3.50%)
lev 125x -> 진입가 x 0.99700  (하락  0.30%)
```

현재 등록된 라이브 전략은 전부 `isolated` / 레버리지 2 라 즉각 영향은 없다. 이번 스프린트는 **화면 고지**로 정직 처리했다(강제 청산 행 + "격리 증거금 기준이며 거래소의 실제 청산과 다를 수 있습니다" 문구).

**권장 접근:** cross 계정 통합 증거금 모델 신설. 계정 전체 자산 대비 유지증거금 합으로 판정해야 하는데 현재 엔진은 포지션 단위라 구조 변경이 크다. BL-186 과 묶어 설계.

**영향 파일:** `strategy/pine_v2/leverage_model.py`, `strategy/pine_v2/strategy_state.py`, `tasks/live_signal.py`.

**Risk:** 🟡 (cross 사용자 조기 강제 청산 — 화면 고지로 완화 중).

---

### BL-508

**Title:** `qb_active_orders` 의 inc/dec 계약이 multiprocess 에서 절대값을 보장하지 못한다 — 재기동마다 영구 편향
**Category:** Backend / observability (trading)
**Priority:** P2
**Trigger:** gauge 를 근거로 운영 판단·경보를 붙이려 할 때, 또는 실자금 cutover 전
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — gauge 는 여전히 multiprocess_mode="sum" + inc 1곳/dec 13곳 구조이고, DB 개수를 .set() 하는 스냅샷 경로가 코드·테스트 어디에도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability — G1 codex 적대 검증이 예측하고 **soak 이 산술까지 맞춰 확증**

**원인 / 영향:** `inc` 는 1곳(`order_service.py:431`, API+worker), `dec` 는 13곳(worker 11 · ws_stream 2 · API 1)에 흩어져 있다. multiprocess 모드에서 `sum` 은 **프로세스별 델타 파일의 합**이므로, 콜드 스타트로 파일이 비면 그 순간 in-flight 였던 주문의 `inc` 가 유실되고 `dec` 만 나중에 찍혀 **영구 −N 편향**이 남는다.

★**실측으로 확증했다.** soak 중 metric `qb_active_orders = 0.0` 인데 DB 실제 in-flight = **1**. 산술이 전부 설명된다 — 재기동 이후 생성 **+7** / 종료 **−6** / **재기동 이전 생성 → 이후 종료 1건의 고아 dec −1** = **0**. 그 1건은 `03:13:52` 생성 → `03:34:10` 취소로 원장에서 특정된다.

★**BL-506 이 만든 결함이 아니다.** 배선 전에는 API 프로세스의 `inc` 만 수집돼 **단조 증가**였으니 더 나빴다. BL-506 이 한 일은 **편향을 보이게 만든 것**이다.

**권장 접근:** inc/dec 계약을 버리고, 한 프로세스가 DB 의 `pending + submitted` 개수를 주기적으로 `.set()` 하는 **스냅샷 gauge** 로 교체한다. ★**주의** — `mark_process_dead` 는 `live*` 파일만 지우므로 지금은 **죽은 자식의 델타 파일이 남아 있어야 산술이 맞는다**(BL-509 와 결합). 파일 회수를 먼저 하면 이 gauge 가 즉시 깨진다.

**영향 파일:** `common/metrics.py`, `trading/services/order_service.py`, `tasks/trading.py`, `tasks/live_signal.py`, `tasks/conditional_entry_janitor.py`, `trading/websocket/*`.
**Risk:** 🟡 (동작 무영향 · 그러나 이 gauge 를 근거로 한 판단이 공허하다)

---

### BL-510

**Title:** 라이브 세션 생성이 `read_only` 계정을 막지 않는다 — 화면은 그 계정을 기본 선택으로 놓는다
**Category:** Backend / trading (세션 등록) + Frontend
**Priority:** P2
**Trigger:** 사용자가 계정을 여러 개 등록한 상태에서 세션을 시작할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — register() 계정 게이트는 여전히 exchange/mode 만 검사하고 read_only 는 청산·표시 경로에만 있다; 세션 폼도 읽기 전용 배지/비활성화 없음. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability — soak 세션 생성 중 화면 관측 + 코드 대조

**원인 / 영향:** `LiveSignalSessionService.register()` 의 계정 게이트는 `account.exchange != bybit or account.mode != demo` **뿐**(`live_session_service.py:108-112`). `read_only` 는 검사하지 않는다. `read_only` 강제는 **청산**(`close_service.py:59-60` → 422)과 **표시**(`position_service.py:301-302`)에만 있다.

즉 **읽기 전용 키로 라이브 자동매매 세션을 시작할 수 있다.** 세션은 평가·신호 생성까지 정상 진행하고 **주문 단계에서야** 실패한다(과거 원장에 `retCode 10005 Permission denied` 2건 실재).

★**화면이 악화시킨다** — 계정 선택 콤보박스가 `bybit demo- aaa`(`read_only=true`)를 **기본 활성 옵션**으로 놓고, 라벨만으로 두 계정을 구분할 수 없다. 쓰기 계정은 `bybit demo` 다.

**권장 접근:** `register()` 에서 `read_only` fail-closed(422) + 콤보박스에 읽기 전용 배지·비활성화.
**Risk:** 🟡

---

### BL-516

> ### 🟡 **권장안 2종 기각 · 「계측 우선」으로 착수 (2026-07-30 close-mismatch-soak)**
>
> 본문의 **권장 접근(leg 분리 / 발주 직전 재확인)은 둘 다 채택하지 않았다.** 근거:
>
> - ★**leg 분리 = 기각.** `Order.reduce_only.is_(False)` 술어가 **4곳**
>   (`order_repository.py:275` reconciler · `:315` sweep · `:347` janitor · `:513` 진입원장)이라
>   청산 leg 가 **모든 lifecycle 쿼리에서 배제**된다 → 세션 종료 후에도 안 걷히는 **고아 reduce-only
>   조건부 주문**. 계획기 주석이 스스로 _"사용자 손절을 지우는 것이 최악의 결함"_ 이라 적은 것의 거울상이다.
>   게다가 같은 trigger 가의 조건부 2건은 **체결 순서가 보장되지 않아** 진입 leg 가 먼저 체결되면
>   뒤이은 청산 leg 가 `110017 same side` 가 된다 — **BL-560 이 지금 재고 있는 바로 그 신호를 늘린다.**
> - ★**발주 직전 재확인 = 무효.** 갭은 **「등재 → 트리거」 사이**인데 거기에 우리 코드가 없다.
>   게다가 `fetch_open_positions`(`live_signal.py:929`) + 3중 fail-closed 로 **이미 구현돼 있다.**
>
> **채택 = 계측 + 좁은 가드.** 발주 형태 불변(1건, `reduce_only=False`, 수량 산식 그대로).
> `crosses_zero` / `overshoot_ratio` 파생값 + `qb_live_conditional_reversal_total{bucket}` +
> `max_reversal_overshoot_ratio` 캡(**기본 `None` = 비활성**). 깨진 기존 테스트 **0건** —
> `test_reversal_uses_full_target_delta` 가 살아남아 "수량 불변" 계약의 수호자가 된다.
>
> ★**soak 이 이 선택을 사후 정당화했다.** BL-560 실측 6/6 이 **반전 체결 직후 방향 불일치**를
> 보여줬다 — 반전 주문이 그 기계다. leg 분리를 했다면 reduce-only 를 **더 만들어** 거절을 늘렸을 것이다.
>
> **미검증:** `qb_live_conditional_reversal_total` 은 검증 창(3분)에 반전이 없어 **실주행 미발화**다.
> 다음 회차에서 확인할 것.

**Title:** 조건부 진입이 `reduce_only=False` 로 하드코딩돼 반전 주문이 기존 포지션을 보호 없이 가로지른다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 실자금 cutover 전
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 「계측 우선」으로 착수**(2026-07-30 close-mismatch-soak). 권장안 2종(leg 분리 / 발주 직전 재확인) 기각. 발주 형태 불변 + overshoot 계측 + 기본 비활성 캡.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability soak 실관측 + 코드 대조

**원인 / 영향:** `live_signal.py:628` 이 조건부 진입 `OrderRequest` 를 **무조건 `reduce_only=False`** 로 만든다. `_action_is_reduce_only`(`:182-188`)는 **시장가 close 에만** 적용된다.

★**soak 실관측** — 03:13:52 에 `qty 0.06` 매도 조건부 주문이 나갔다. 이는 기존 롱 0.03 청산 + 신규 숏 0.03 진입(stop-and-reverse)인데, **청산 부분에 reduce-only 보호가 없다.** 포지션이 그 사이에 이미 줄어 있으면 초과분이 반대 포지션을 연다.

**권장 접근:** 반전 주문을 청산 leg(`reduce_only=True`)와 진입 leg 로 분리하거나, 거래소의 reduce-only 시맨틱을 쓸 수 없다면 발주 직전 포지션 재확인을 강제한다.
**Risk:** 🟡

---

### BL-517

**Title:** stand-down 축이 거래소 uid 가 아니라 DB 계정 행 id 다 — 같은 계정을 두 번 등록하면 우회된다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 사용자가 같은 거래소 계정을 키 두 개로 등록한 상태에서 세션 두 개를 돌릴 때
**Est:** S
**상태:** ✅ Resolved — 2026-08-10 close-ownership-axis. `account_exclusivity._ownership_scope` 를 모듈 함수 `ownership_scope_ids` 로 추출해 stand-down 이 **재사용**한다(새 가드를 만들지 않았다 — 아래 반박 1 이 지목한 착수 지점 그대로). `_resolve_current_position` 이 `account_repo` 를 받아 uid 형제 행 전량의 활성 세션을 본다. `list_active_by_account` 자체는 **안 건드렸다**(소비자 3곳 중 stand-down 만 넓은 축이 필요하다) — 호출부에서 넓혔다. AST def-use 오라클이 요구하는 `stand_down_reason` 단일 `Assign` + `IfExp` 구조는 그대로다. 시험은 `exchange_uid` **한 필드만** 다른 양성/음성 쌍이고 `_resolve_current_position` 을 통과하는 경로로 잰다 — 순수 함수를 직접 부르면 배선 변이가 green 으로 탈출한다(`backend/AGENTS.md` §10-2). 변이 4/4 red(배선 변이 포함, 도달 확인)
**출처:** 2026-07-28 live-observability 코드 대조 (실행 재현은 read_only 제약으로 불가)

**원인 / 영향:** stand-down 술어는 `live_signal.py:462-464` → `list_active_by_account(sess.exchange_account_id)`, 구현은 `WHERE exchange_account_id == account_id`(`live_signal_session_repository.py:69-76`). **DB 행 id 축이다.**

우리 DB 의 두 계정 행 `19a8166a`·`0277c150` 은 **같은 `exchange_uid = 558689281`**(실측). 세션 둘을 서로 다른 계정 행에 붙이면 `shares_account_symbol = False` → **stand-down 미발화**. 그런데 두 세션은 **같은 거래소 포지션**을 건드린다.

★코드 주석(`live_signal.py:444-456`)이 스스로 전제를 밝힌다 — _"계정 순포지션을 세션 target 에서 빼는 산술은 '이 계정·심볼의 포지션이 이 세션 것뿐' 이라는 전제 위에 선다"_. 중복 등록에서 그 전제가 **조용히** 깨진다.

★지금 폭발하지 않는 이유는 `0277c150` 이 `read_only=true` 라서다 — **가드가 아니라 우연**이다. 등록 시 `exchange_uid` 를 이미 조회해 저장한다(`account_service.py:69,79`) — **가진 정보를 안 쓰고 있다.**

★★**2026-08-10 guards-blind-spots G0 — 코드 대조 결과. 착수 전 이것부터 읽어라.**

**확인된 것** — 핵심 주장은 참이다. stand-down 술어는 `live_signal.py:1817-1820` 이고
`list_active_by_account(sess.exchange_account_id)` 를 쓴다. 구현은
`live_signal_session_repository.py:92-99` 의 `WHERE exchange_account_id == account_id`. **DB 행 id 축이 맞다.**
`exchange_uid` 컬럼은 `models.py:196` 에 있고 등록 시
`account_service.py:69,78` 이 채운다. **`exchange_uid` 에 UNIQUE 제약이 없어** 같은 uid 두 행은 구조적으로 합법이다.

★**줄번호가 낡았다** — 본문의 `live_signal.py:462-464` 는 지금 **`:1817-1820`**,
`live_signal_session_repository.py:69-76` 은 **`:92-99`** 다.

★★**반박 1 — 「가진 정보를 안 쓰고 있다」가 거짓이다.**
`exchange_uid` 는 **이미 다른 가드의 축**이다: `account_exclusivity.py:128-136` 의
`_ownership_scope` 가 `list_by_exchange_uid` 로 **형제 행 전량**을 잡고,
`live_session_service.py:155` 에서 fail-closed 로 돈다. 참인 진술은 훨씬 좁다 —
**stand-down 술어만** 그 축을 안 쓴다. ⇒ 처방은 「uid 를 쓰기 시작하라」가 아니라
**「이미 있는 `_ownership_scope` 를 여기서도 재사용하라」**다. 새로 만들지 마라.

★★**반박 2 — 「read_only 라서 안 터진다」는 맞지만 기전이 레포 밖이다.**
`read_only` 를 **강제하는 곳은 레포 전체에서 한 곳뿐**이다 — `close_service.py:96-97`(수동 청산).
`LiveSessionService.register` · `OrderService.execute` · `live_signal.py` 에 검사가 **없다** ⇒
우리 코드는 read_only 행으로 **라이브 세션을 시작할 수 있다.** 「가드가 아니라 우연」은 참이고,
그 우연을 만드는 것은 **Bybit** 이지 우리 코드가 아니다. 레포 안에는 안전장치가 없다.

**착수 시 제약 2건**

- `test_conditional_divergence_reachability.py:197,239-240` 이 AST def-use 오라클로
  `stand_down_reason` **대입과 `is not None` 검사가 한 함수 안에** 있을 것을 강제한다.
  그 블록을 쪼개면 red 다.
- `exchange_uid IS NULL` 이면 **자기 행만** 봐야 한다(`_ownership_scope` 와 같은 폴백).

**커버리지 구멍(실측)** — `grep -c exchange_uid` 가 stand-down 테스트 두 파일
(`test_live_signal_conditional_reconcile.py` · `test_live_conditional_divergence_labels.py`)에서
**0** 이다. 기존 stand-down 테스트는 전부 `exchange_account_id=session.exchange_account_id`,
즉 **같은 행** 경우만 잰다. **같은 uid 두 행** 위상을 가드 입력으로 태우는 테스트는
`test_account_exclusivity_guard.py:226` 하나뿐이고 그건 다른 가드다.

**권장 접근:** stand-down 축을 `exchange_uid + symbol` 로 올린다. **BL-505**(청산 lock 축이 포지션 정체성이 아니다)와 **같은 계열의 축 문제**다.
**Risk:** 🟡

---

### BL-519

**Title:** 컨테이너로 API 를 띄우는 배포에는 multiprocess 배선이 없다 — 조용히 폴백해 worker 지표를 영영 못 본다
**Category:** Infra / observability
**Priority:** P2
**Trigger:** 프로덕션 배포 시
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — API 컨테이너 서비스도, production 미설정 경고 로그도 아직 없다 — 폴백은 여전히 무증상이다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증

**원인 / 영향:** `docker-compose.yml` 에 API 서비스가 **없다**(호스트 uvicorn). `PROMETHEUS_MULTIPROC_DIR` 을 주입하는 곳은 compose 의 worker 4곳 + Makefile 2곳뿐이다. `Dockerfile` 이 `/metrics` 디렉토리를 만들어 두지만 **그 값을 주입하는 곳이 레포 전체에 없다.**

컨테이너 API 배포에서는 env 미설정 → 단일 프로세스 폴백 → **worker 지표가 안 보인다.** 그리고 그 상태가 200 을 반환하므로 **무증상**이다.

★이번 세션에서는 `.env.example` 과 `docker-entrypoint.sh` 주석으로 **경고만** 남겼다. 배포 매니페스트가 이 레포에 없어 코드로 강제할 수 없다.

**권장 접근:** 배포 매니페스트에 env + 공유 볼륨을 넣고, API 기동 시 `PROMETHEUS_MULTIPROC_DIR` 미설정을 **production 에서 경고 로그**로 남긴다.
**Risk:** 🟡

---

### BL-520

**Title:** 머니-패스의 metric mutation 전면 sweep — 관측 코드가 주문 경로를 막을 수 없어야 한다
**Category:** Backend / trading (money-path)
**Priority:** P2
**Trigger:** 실자금 cutover 전
**Est:** S
**상태:** 🟡 부분 해결 — qb_active_orders inc/dec 는 감싸졌으나 live_signal.py:4180 sweep_filled inc 가 래퍼 밖 — metric 실패가 filled 를 sweep_cancel_failed 로 뒤집는다. AGENTS.md … (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). [BL-003] 이 막고 있다. ★잔여 (`live_signal.py:4180` sweep_filled inc 가 래퍼 밖)는 **지금도 데모에서 발화 가능**하지만 Trigger 가 정한 창은 cutover 전이다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-28 live-observability G6 codex 최종 적대 리뷰 (P1 의 후속)

**원인 / 영향:** BL-506 이 metric mutation 을 in-memory 증가에서 **공유 mmap 파일 쓰기**로 바꿨다. 그래서 read-only 마운트·ENOSPC·I/O 오류에 예외를 던질 수 있다.

이번 세션은 **주문을 영구 좌초시키는 유일한 지점** 하나만 고쳤다 — `order_service.py` 의 commit 직후·dispatch 직전 `qb_active_orders.inc()`(예외 시 주문 행은 commit 됐는데 dispatch 가 안 되고, 멱등 재시도는 캐시 조기 반환에 걸려 **영구 미발주**).

남은 것: `dec()` **13곳**과 `tasks/trading.py`·`tasks/live_signal.py`의 다른 metric 호출. 이들은 terminal 전이 이후라 예외 시 Celery 재시도로 회복되므로 좌초시키지는 않지만, **불변식으로 못박는 것이 옳다.**

**권장 접근:** 머니-패스의 모든 metric mutation 을 `record_metric_safely` 로 감싸고, 그 규칙을 `backend/AGENTS.md` 에 등재한다.
**Risk:** 🟡

### BL-662

**Title:** `/dashboard` 가 로컬 배럴로 렌더하지도 않는 컴포넌트 9종을 끌어온다
**Category:** Frontend / 번들
**Priority:** P2
**Trigger:** 대시보드 첫 로드 JS 를 줄이려 할 때 · 번들 분석을 돌릴 때
**Est:** XS
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — 직접 경로 3줄로 `/dashboard` 클라이언트 JS **1,140,321 B → 954,447 B (−185,874 B · −181.5 kB · −16.3%)**, 청크 17→13, 9종 문자열 지문 **8/9 → 0/9**, `react-hook-form` 전이 의존 **제거**. 양성 대조 `/trading` 은 8/9·바이트 불변
**출처:** 2026-08-09 status-triage-mass — `/vercel-react-best-practices` 교차검증

**원인 / 영향:** `dashboard-cockpit.tsx:28` 이 `@/features/live-sessions` 에서 훅 3개(`useLiveSessions`·`useLiveSessionsAggregate`·`useUnrealizedPnlEstimate`)를, `:34` 가 `@/features/trading` 에서 `useExchangeAccounts` 를 받는다. 두 배럴은 컴포넌트 9종을 함께 re-export 한다(`features/live-sessions/index.ts:38-41` · `features/trading/index.ts:3-7`). grep 실측으로 dashboard-cockpit 은 그 9종을 하나도 렌더하지 않는다. `frontend/package.json` 에 `"sideEffects"` 필드가 **없어** 번들러가 모듈 평가를 버릴 근거도 없다.

도달 범위 = `test-order-dialog`(605줄) · `outcome-parity-panel`(543) · `live-session-detail`(361) · `live-session-form`(234) · `activity-timeline-chart`(231) · `live-session-list`(227) · `orders-panel`(214) · `register-exchange-account-dialog`(198) · `exchange-accounts-panel`(135) · `live-session-table`(132) · `kill-switch-panel`(90) ≈ **3,000줄**과 전이 의존(`react-hook-form`·`sonner`·`ui/dialog`·`ui/select`). `kill-switch-banner.tsx:12` 도 같은 배럴을 쓴다.

★~~**바이트는 안 쟀다** — 착수 시 `@next/bundle-analyzer` 로 먼저 재라~~ → **2026-08-09 쟀고, 그 처방은 이 레포에서 안 돈다.** [BL-410] 은 **외부 패키지**(`radix-ui`) 배럴을 다루고 이 건은 **로컬 배럴 + 소비처**라 별개다 — 배럴 위반은 import 문이 아니라 **소비처**에 있다.

**해결 (2026-08-09 fe-perf-quartet):** `dashboard-cockpit.tsx` 2곳(`@/features/live-sessions/hooks` + `@/features/live-sessions/unrealized`, `@/features/trading/hooks`) · `kill-switch-banner.tsx:12` 1곳을 직접 경로로. `trading-cockpit.tsx` 는 9종을 실제로 렌더하므로 **안 건드렸다**.

★★★**이 건이 낸 반증 3개 — 셋 다 본문/처방이 틀렸다:**

1. **`@next/bundle-analyzer` 는 이 레포에서 아무것도 못 낸다.** Next 16 은 Turbopack 이 기본 빌더이고 빌드 로그가 직접 말한다: `The Next Bundle Analyzer is not compatible with Turbopack builds, no report will be generated.` 대안 = `next experimental-analyze`(Turbopack 전용) 또는 `--webpack`(다른 번들러를 재므로 실제 산출물을 안 설명한다).
2. **Next 16 Turbopack 은 `app-build-manifest.json` 을 안 만들고, 라우트 표에 `Size`/`First Load JS` 컬럼도 없다.** 실제 정본은 `.next/server/app/<route>/page_client-reference-manifest.js` 의 `__RSC_MANIFEST` 다.
3. **「9종 ≈ 3,000줄」이 과대다.** 최대 항목 `test-order-dialog`(605줄)는 **`/dashboard`·`/trading` 어느 쪽 청크에도 없다** — Turbopack 이 이미 떨어냈거나 다른 경로로 로드된다. 실측 도달은 **8종**이고 전부 `static/chunks/0j5~b2~airf-9.js`(84,344 B) 한 청크에 몰려 있었다.

★**측정기 자신이 한 번 반증됐다** — 1판은 `clientModules` 를 뒤졌는데 9종은 client boundary 진입점이 아니라 `"use client"` 컴포넌트 **안쪽**이라 거기 안 뜬다. **양성 대조 `/trading` 에서도 0/9** 가 나와서 판별력 0 임이 드러났고, 문자열 지문 검색으로 교체하자 `/trading` 8/9 가 나왔다. **양성 대조가 없었으면 「효과 0」을 그대로 보고했을 것이다.**

★`"sideEffects": false` 는 **선언하지 않았다** — import 경로만으로 −181.5 kB 가 나와 델타가 0이 아니었고, 이 레포 유일 bare import 인 `layout.tsx:8`(`globals.css`)를 드롭할 위험만 남기 때문이다. 필요하면 `["*.css"]` 형태로 별도 회차에.

**Risk:** 🟢

---

### BL-663

**Title:** 트레이딩 코크핏이 5초마다 §01~§08 전 서브트리를 재조정한다 (`useNowTick`)
**Category:** Frontend / 재렌더
**Priority:** P2
**Trigger:** 코크핏 반응성 불편 접수 시 · React Compiler 도입 검토 시
**Est:** S
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — KPI 카드를 `unrealized-pnl-kpi.tsx` leaf 로 내려 5초 틱 **과 WS ticker 구독을 함께** 가뒀다. 회귀 = 5초 3회 전진 뒤 §03 자식 렌더 수 불변(변이 M4 로 빨간 것 확인). ★본문의 인과는 **불완전했다**(아래)
**출처:** 2026-08-09 status-triage-mass — `/vercel-react-best-practices` 교차검증

**원인 / 영향:** `trading-cockpit.tsx:45-54` 의 `useNowTick(5_000)` 이 5초마다 `setNow(Date.now())` 를 부른다. 그 값의 소비처는 `:125-126` 의 `isTickerStale` **불리언 하나**다. 프론트엔드 전체에 `memo()` 가 **0건**이고(grep 실측) React Compiler 도 꺼져 있다(`next.config.ts` 에 `reactCompiler` 없음 — `eslint-plugin-react-compiler` 는 린트만 한다).

⇒ 코크핏을 **열어 두기만 해도** 5초마다 KPI 4장·잔고·포지션 표 2개·킬스위치·주문 원장·계정 패널·세션 표·폼·목록·세션 상세 차트 2개·진단이 통째로 재조정된다. 배지 하나 갱신하려고 내는 비용이다.

~~**권장 접근:** `rerender-derived-state` 처방대로 `isTickerStale` 만 파생 구독으로 뽑는다(연속값은 ref 로).~~ → **2026-08-09 이 처방은 거의 아무것도 안 산다는 것이 코드 대조로 드러났다.**

★★★**본문의 인과가 불완전했다 — 재조정 원천이 둘이다.** 같은 컴포넌트가 `useUnrealizedPnlEstimate` → `useRealtimeStore(useShallow(…))`(`unrealized.ts:122-130`)로 활성 세션 심볼의 WS ticker 를 구독한다. `applyTicker`(`realtime/store.ts:45-46`)가 매 틱 **새 `TickerEntry`** 를 넣으므로 shallow 비교가 깨져 **활성 세션 심볼이 틱할 때마다** 코크핏 전체가 재조정된다 — 5초보다 훨씬 잦다. 반대로 활성 세션이 0건이면 5초 틱만 남지만 그땐 `latestTs === null` 이라 `isTickerStale` 이 **항상 false** 다. ⇒ 「불리언만 뽑기」는 **활성 세션이 있을 때 효과 없고 없을 때 볼 것이 없다.** 해 = 두 원천을 **같은 leaf** 에 둔다.

★★**사거리 정정(codex 적대 리뷰 C4 REFUTED).** 이 분리가 지키는 것은 코크핏 본체와 **§01~§07** 이다. **§08 은 아니다** — `session-diagnostics.tsx:241-242` 가 `useRealtimeStore` 의 `status`·`lastEventTs` 를 **스스로** 구독하고 `realtime-bridge.tsx:62` 가 ticker 를 포함한 모든 envelope 에서 `recordEvent` 를 부른다. 초안 주석은 「§01~§08 이 재조정되지 않는다」고 적었고 그것은 **거짓**이었다.

★`reactCompiler: true` 검토는 **[BL-666]** 으로 분리했다(이 회차 범위 밖 — 켜지 않았다).
**Risk:** 🟡 코크핏은 라이브 세션 감시 화면이라 체감이 크다.

---

### BL-664

**Title:** 코크핏 새로고침 버튼이 앱 전체 쿼리 캐시를 무효화한다
**Category:** Frontend / 데이터 페칭
**Priority:** P2
**Trigger:** 새로고침 후 무관한 화면이 함께 재요청되는 것이 관측될 때
**Est:** XS
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — 이 화면이 소비하는 **네** 도메인 루트만 무효화한다(`trading`·`live-sessions`·`strategies`·`alert-rules`). 회귀 = 호출 4회·각 인자가 팩토리 출력·무인자 호출 0회(변이 M1·M5 로 빨간 것 확인)
**출처:** 2026-08-09 status-triage-mass — `/vercel-react-best-practices` 교차검증

**원인 / 영향:** `trading-cockpit.tsx:194` 의 `void queryClient.invalidateQueries()` 에 필터 인자가 없다. 「새로고침」 한 번에 앱 캐시의 **모든** 쿼리가 stale 이 되고, 마운트된 활성 쿼리가 전부 동시에 재요청된다 — ~~이 화면과 무관한 `useStrategies({limit:100})`~~ · 백테스트 목록 · 옵티마이저 실행까지 포함된다.

★**본문 반증(2026-08-09):** 「이 화면과 **무관한** `useStrategies({limit:100})`」는 **거짓**이다 — `trading-cockpit.tsx:76-80` 이 그 쿼리를 **직접 호출**한다(§07 폼·표의 전략명 매핑). 무관한 예로 든 셋 중 하나가 자기 쿼리였다. 남은 두 예(백테스트·옵티마이저)만 유효하다.

**해결 (2026-08-09 fe-perf-quartet):** 도메인 팩토리 루트 4개를 `queryKey` 필터로 돈다(키 하드코딩 금지 — `frontend/AGENTS.md` §3). `uid` 는 `useAuthCtx()`.

★★★**첫 판이 기능을 깼고 codex 가 잡았다(C3 REFUTED).** 셋만 무효화했더니 §08 `SessionDiagnostics` 의 `useAlertRules`(키 루트 `alert-rules`, `session-diagnostics.tsx:112`)가 **빠졌다**. 종전의 무필터 호출은 그것까지 갱신하고 있었으므로 **범위를 좁힌 것이 아니라 기능을 깬 것**이었다. ⇒ **무효화 범위를 좁힐 때는 그 화면의 자식이 부르는 훅을 전수로 세라.** 「이 화면이 쓰는 것」은 직접 호출만이 아니라 렌더 트리 전체다.

**Risk:** 🟢 정확성 문제는 없고 낭비만 있다.

---

### BL-707

**Title:** authed e2e 실패 메시지가 「API 도달 불가」를 「데이터 없음」으로 오지목한다
**Category:** 테스트 / 진단 품질
**Priority:** P2
**Trigger:** authed e2e 를 다시 손댈 때 / 같은 오진이 재발할 때
**Est:** S
**상태:** ⬜ Open — 처방 미착수. 2026-08-12 surface-demo-pack 에서 실측으로 등재했고, 이 회차가 그 오진에 실제로 걸렸다(원인 확정까지 `make seed` 실행 1회 + 브라우저 콘솔 판독 1회).
**트리거 판정:** 도래 — 조건절이 없다. 발견 회차가 곧 착수 가능 시점이고 대상 파일도 확정돼 있다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack (authed 12건 red 의 귀속을 정하다 발견)

**원인 / 영향:** `pnpm e2e:authed` 12건이 이렇게 실패했다:

```
Error: /trading 데이터 전제 미충족 — 등록된 거래소 계정이 없다. /trading 이 빈 상태만 그린다 (`make seed`)
Error: 완료된 백테스트 상세 링크를 찾지 못했다 — 캐논 감사가 볼 원장이 없다 (`make seed`)
Error: 완료 optimizer run 상세 링크를 찾지 못했다 — 완료 run 시딩 필요
Error: 완료 상태 백테스트를 목록에서 찾지 못했다 (백엔드 8000 에 완료 백테스트 시딩 필요)
```

지시대로 `make seed` 를 돌렸더니 **전건 「이미 존재」**(전략 스킵 3 · 실행 스킵 6)였다. DB 실측도
같았다 — 한 사용자가 전략 3 · **완료 백테스트 7** 을 소유하고 있었다.

진짜 원인은 **백엔드가 `:8100` 에 없었던 것**이다. `make fe-isolated`(`:3100`)는
`NEXT_PUBLIC_API_URL=:8100` 을 쓰는데 떠 있던 BE 는 `make be`(`:8000`)였다. 브라우저 콘솔에
`ERR_CONNECTION_REFUSED` **109건**이 찍혀 있었고, `make be-isolated` 로 `:8100` 을 띄운 뒤
**authed 84/84 green · 콘솔 error 109 → 0** 이 됐다.

★**「데이터가 없다」와 「데이터를 못 가져온다」는 화면에서 똑같이 비어 보인다.** 단정문이 빈
목록을 보고 원인을 **추측해서** 적으면, 그 추측이 다음 사람의 30분을 가져간다.

**권장 접근:** 그 단정들 앞에 **API 도달성 프로브**를 둔다 — `NEXT_PUBLIC_API_URL` 로 1회 fetch
하거나 콘솔의 `ERR_CONNECTION_REFUSED` 를 세고, 도달 불가면 **시딩이 아니라 그 사실**을 말한다
(`API 도달 불가: <url> — BE 가 떠 있는지 확인해라 (make be-isolated)`). 도달 가능한데 비어 있을
때만 시딩을 지목한다.

**Risk:** 🟡 프로덕션 무해. 다음 세션의 오진 비용이 위험이다.

---

### BL-708

**Title:** `design-canon-calibration` 의 대비 측정이 회차마다 다른 파일에서 실패한다 (「하드 실패 0」 계약이 새는 창)
**Category:** 테스트 / 게이트 판별력
**Priority:** P2
**Trigger:** 캐논 감사 코어를 손댈 때 / 이 플레이크로 게이트가 막힐 때
**Est:** S
**상태:** ⬜ Open — 처방 미착수. 2026-08-12 surface-demo-pack 이 3회 실행으로 비결정성을 확정했다.
**트리거 판정:** 도래 — 조건절이 없다. 재현 절차와 실측 3회가 이미 있다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack (E2E 회차의 red 귀속을 정하다 발견)

**원인 / 영향:** `frontend/e2e/design-canon-calibration.spec.ts:95` 의 「하드 실패 0」 단정이
회차마다 **다른 캐논 파일**에서 깨진다. 같은 코드·같은 커밋에서 3회 실행한 실패 집합:

| 회차 | 실패 파일                                                 |
| ---- | --------------------------------------------------------- |
| 1    | `screen-10-optimizer-detail.html`                         |
| 2    | `screen-08-strategy-editor.html` · `screen-15-login.html` |
| 3    | 없음 (22 passed)                                          |

**세 집합이 서로 겹치지 않는다** ⇒ 코드의 성질이 아니다.

★★**2026-08-12 CI 가 원인 축을 좁혔다** — 같은 커밋(`214dfeb1`)에서 **1회차 pass → 2회차
`screen-09`·`10`·`11`·`16` 4파일 fail → 3회차 pass** 였고, **2회차 안에서는 retry #1·#2 까지
같은 파일이 실패**했다. 즉 **한 회차 안에서는 결정적이고 회차 사이에서만 갈린다** ⇒ 원인은
테스트별 타이밍이 아니라 **런너/프로세스 단위 렌더 조건**(폰트 대체·`deviceScaleFactor`·
서브픽셀 반올림)이다. ⇒ 처방에서 「대기를 늘린다」는 **틀린 방향**이다. 실패 값은 문턱 바로 아래다 —
`canon 1440px 5.41:1 (5.82 필요) rgb(173, 50, 42) 10.08px "숏"`. 계산 폰트 크기가 **10.08px**
같은 소수라 대비 판정이 렌더 타이밍·안티에일리어싱에 흔들린다. 테스트 자신이 그 가능성을 적어
뒀다 — 「runtime-check.mjs 는 PASS 였으므로 이식된 감사 코어가 틀렸다」.

★**위험의 방향이 둘 다다.** 거짓 red 는 게이트를 막아 회차를 태우고, 거짓 green 은 **「하드 실패
0」을 무증거로 만든다.** 이 회차는 거짓 red 쪽을 밟았다.

**권장 접근:** ⑴ 대비 계산의 비결정 원천을 고정한다(소수 폰트 크기 반올림 규칙·`deviceScaleFactor`
고정·측정 전 `fonts.ready` 대기) 또는 ⑵ 문턱 ±0.5 이내는 **WARN** 으로 내리고 하드 실패는 명확한
위반만 잡게 한다. ★어느 쪽이든 **같은 커밋에서 N회 반복 실행이 같은 답을 내는지**를 수용 기준으로
둬라 — 이 BL 을 만든 것이 바로 그 반복이다.

**Risk:** 🟡 프로덕션 무해. 게이트 신뢰도가 위험이다.

---

### BL-709

**Title:** 전략 목록 RSC prefetch 가 URL 정렬을 안 읽어 정렬 링크마다 클라이언트 왕복이 하나 더 든다
**Category:** Frontend / 성능 (RSC ↔ React Query 정합)
**Priority:** P3
**Trigger:** 전략 목록을 다시 손댈 때 / 정렬 링크 공유가 실사용될 때
**Est:** S
**상태:** ⬜ Open — 처방 미착수. 2026-08-12 surface-demo-pack 의 G5(FE 성능 패스)가 **자기 회차가 만든 것**으로 찾아 등재했다.
**트리거 판정:** 도래 — 조건절이 없다. 원인·처방·파일이 확정돼 있다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G5 (`/vercel-react-best-practices` waterfall 축)

**원인 / 영향:** [BL-430] 이 정렬을 **URL 스칼라**(`order_by`/`order`)로 옮겼고 client hook 의
queryKey 가 그것을 포함한다. 그런데 `frontend/src/app/(dashboard)/strategies/page.tsx` 는
Server Component 인데 **`searchParams` 를 받지 않고** `order_by: "updated_at"` · `order: "desc"` 를
하드코딩해 `prefetchQuery` 한다.

⇒ `/strategies?order_by=sharpe_ratio&order=desc` 로 진입하면(정렬 후 새로고침 · 링크 공유 · 뒤로가기)
**서버가 한 번 조회한 결과가 버려지고** 클라이언트가 같은 목록을 다시 가져온다. 기능은 옳다 —
데이터는 refetch 로 맞는다. **비용만 든다**(서버 쿼리 1회 낭비 + 첫 콘텐츠까지 왕복 1회 추가).

★**이 회차가 만든 것이다.** 종전에는 정렬이 클라이언트 로컬이라 prefetch 가 **항상** 맞았다.
그리고 그 파일의 주석이 「client hook 과 **동일한 queryKey** 를 위해 같은 query」라고 단정하고
있었는데 그 문장이 정렬 URL 에서 거짓이 됐다 — 같은 회차에서 **주석만** 정정했다.

**권장 접근:** `searchParams`(Next 16 은 **`Promise<>`** — `await` 필수)를 받아 화이트리스트로
검증한 뒤 같은 query 로 prefetch 한다. ★**화이트리스트를 두 벌로 만들지 마라** — 지금
`SORT_OPTIONS` 는 client 파일(`strategy-list.tsx`) 안에 있고 export 되지 않는다. `features/strategy/`
로 올려 **1벌을 공유**해야 하고, 그러지 않으면 축을 추가할 때 서버·클라이언트가 갈린다.

**Risk:** 🟢 정확성 문제는 없고 낭비만 있다.

---

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived (BL-050/051/052/053/054/055/056/057/138/139/151/153). ~~**활성 P3 = 8**~~ ★**stale** — 2026-08-08 `bl-audit.sh` 실측 P3 ACTIVE **101**. 이 파일 헤더 규약대로 집계 수치는 여기 박지 말고 스크립트를 돌려라 (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2 + BL-389/390/391 2026-06-30 backtest-deepen). ★2026-08-06 entry-set-divergence 강등 = BL-606/607/608/609.

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Trigger                                                                                                           | Est       | 출처                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------ |
| [BL-377](#bl-377) | pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | pine_v2 robustness 후속 또는 실자금 cutover 전                                                                    | S (2-4h)  | 2026-06-30 BL-376 G2 codex challenge + G3 fresh review |
| [BL-383](#bl-383) | 🟡 v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | pine_v2 관측성 후속                                                                                               | S (2-3h)  | 2026-06-30 QA codex G2                                 |
| [BL-384](#bl-384) | ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | pine_v2 parity 후속                                                                                               | S (2-3h)  | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-385](#bl-385) | PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse (메타데이터 부정확)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | pine_v2 coverage 후속                                                                                             | XS (1-2h) | 2026-06-30 QA F3                                       |
| [BL-386](#bl-386) | v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject, over-strict)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | pine_v2 coverage 후속                                                                                             | XS (1-2h) | 2026-06-30 QA F4                                       |
| [BL-525](#bl-525) | 라이브가 Track A(indicator + alertcondition) 전략을 어떻게 다루는지 정의되지 않았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Track A 로 라이브 세션을 열 때                                                                                    | S         | 2026-07-28 live-entry-parity                           |
| [BL-539](#bl-539) | ✅ (P3) 방향 불일치 유예가 시간 경계가 없다 — 평가가 드문드문하면 오래된 strike 가 살아남는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 발산 가드를 다시 손댈 때                                                                                          | S         | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-540](#bl-540) | (P3) `live_signal.py` 반복 3종 — deactivate 의식 6회 · provider+creds 4회 · category 가 맨 `str`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 이 파일을 다시 크게 손댈 때                                                                                       | M         | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-548](#bl-548) | ✅ **Resolved (2026-08-09, W3)** — (P3) `OutcomeParityPanel` 이 375px 에서 본문 가로 스크롤을 만든다. ★**24px 재현 실패** — [BL-607] 반올림이 그 경로를 이미 닫았다. 남은 경로는 반올림 없는 `sub` 캡션 4곳 — 51자리 Decimal 이 오면 **191px**. 넘치는 것이 표가 아니라 텍스트라 처방은 `break-words`                                                                                                                                                                                                                                                                                                                                                                                 | 모바일 폭 점검 시                                                                                                 | XS        | 2026-07-30 conditional-entry-alignment                 |
| [BL-550](#bl-550) | (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 죽은 세션을 세션 단위로 대조해야 할 때                                                                            | S         | 2026-07-30 conditional-entry-alignment                 |
| [BL-551](#bl-551) | ✅ (P3) 라이브 세션 상세 진입이 URL 파라미터가 아니다 — 딥링크·새로고침 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 세션 상세를 링크로 공유해야 할 때                                                                                 | S         | 2026-07-30 conditional-entry-alignment                 |
| [BL-557](#bl-557) | (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 그 게이지로 무언가를 판단하기 전                                                                                  | S         | 2026-07-30 live-entry-completeness                     |
| [BL-559](#bl-559) | ✅ (P3) 진입 완결성 도구 잔여 3건 — 세션 목록 절단 감지 · 사문 라벨(**기각**) · janitor probe 전이                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 그 경로가 실측될 때                                                                                               | S         | 2026-07-30 live-entry-completeness                     |
| [BL-564](#bl-564) | ✅ **Resolved** (2026-08-09 backlog-sweep) — `bl-audit.sh` 가 코드펜스 · `<details>` 안의 옛 상태줄을 SSOT 로 오인할 수 있다. **처방 2건이 이미 구현돼 있었다**(`:114-120` 스킵 · `:268-288` 중복=exit 1)이고 Trigger 「게이트 체인 편입 전」도 도래(`final-gates.sh:151`). 코드 0줄                                                                                                                                                                                                                                                                                                                                                                                                  | 그 관용구가 상태줄을 품게 될 때                                                                                   | XS        | 2026-07-30 close-mismatch-soak                         |
| [BL-573](#bl-573) | (P3) `engine_only` tick 당 `list_resting_conditional_entries` 2회 — 감지가 reconcile 보다 앞서 돌아 공유 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | tick 비용을 손댈 때 / 두 경로를 합칠 때                                                                           | S         | 2026-08-01 soak codex                                  |
| [BL-581](#bl-581) | `/metrics` 영구 누적 **10277 파일 · 635MB · PID 1968** (counter 삭제 금지)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 20000 파일 초과 · 스크레이프 지연 · 여유 20G 미만                                                                 | M         | 2026-08-02 metric-guard-parity                         |
| [BL-582](#bl-582) | divergence counter 13 series 중 **5종** 도달 불가 (2026-08-03 재판정 — 7종에서 축소. 2종은 엔진 구동으로 **반증**), 프로덕션 확인 3/8                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 반증된 2종이 프로덕션에서 발화하거나 `other` def-use 오라클이 red 일 때                                           | S         | 2026-08-02 metric-guard-parity                         |
| [BL-584](#bl-584) | `BalanceUnverified` 가 라이브 dispatch 의 결정론적-거절 튜플 양쪽에 없다 — 소진 시 실제 사유가 `max_retries_exhausted` 로 덮인다. ★2026-08-03 **현재 코퍼스 도달 불가 확정**(계정 mode 는 생성 후 불변 · `mode=live` 계정 0건) ⇒ 수리 보류, Trigger 를 cutover 로 보강                                                                                                                                                                                                                                                                                                                                                                                                                | **`mode=live` 계정이 생성될 때**(Wave 3 cutover), 또는 `outcome="max_retries_exhausted"` 창 차분이 0 을 벗어날 때 | S         | 2026-08-03 metric-guard-residual-close                 |
| [BL-578](#bl-578) | 조건부 진입 `110092`/`110093` 거절 시 거래소가 준 정답(`current[...]`)을 버린다 — BL-536 재판정에서 유일하게 살아남은 채널의 잔여 (측정 완료 · 수리 보류)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | C1 거절이 하루 3건 이상으로 다시 오르거나 실자금 cutover 로 1건 비용이 달라질 때                                  | S         | 2026-08-01 entry-completeness-rejudgement              |
| [BL-586](#bl-586) | ✅ **Resolved** 2026-08-07 backtest-fidelity — 키 리스트를 `dataclasses.fields()` 자동 유도로 교체(스칼라 46 전량 + 리스트 3종 digest + 중첩 2종 평탄화 + `RawTrade` 22 전량). 원 증상: P-3 골든이 `BacktestMetrics` **51 중 13**, `RawTrade` **22 중 11** 만 고정해 38+11 이 회귀 감지 밖                                                                                                                                                                                                                                                                                                                                                                                            | TV parity 팩·비용 분해·청산 지표에서 회귀가 의심될 때                                                             | M         | 2026-08-03 backtest-metric-oracle                      |
| [BL-599](#bl-599) | Pine v1 shim(`src/strategy/pine/` 135L)은 타입 4종만 재export 하는 껍데기지만 `BacktestOutcome.parse` 가 코어 DTO 필드라 **단독 철거 불가**. 소비처는 「2곳」보다 넓다 — 프로덕션 import 2 + 생성 site 10+ + 테스트 3파일                                                                                                                                                                                                                                                                                                                                                                                                                                                             | `BacktestOutcome` 를 손볼 일이 생겼을 때 (단독으로 열지 마라)                                                     | M         | 2026-08-06 dead-code-sweep                             |
| [BL-600](#bl-600) | `strategy/trading_sessions.py:26` 의 `TradingSession` 이 CONTEXT 헌법의 _Avoid_ 이름과 **동음이의 충돌**(이쪽은 장중 시간대 필터). 값이 `Strategy.trading_sessions` **JSONB 에 영속**돼 단순 rename 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | `trading_sessions` JSONB 를 마이그레이션할 때 · 도메인 용어 정리 시                                               | M         | 2026-08-06 dead-code-sweep                             |
| [BL-601](#bl-601) | ✅ **호출 0건 잔재 3종 — 처리가 갈렸다.** 저장소 메서드 2건(`get_state_fresh` · `list_unsynced_reduce_only_since`)은 제거했고, `scripts/fleet-dispatch-test.sh` 는 **제거 대신 `final-gates.sh` 에 배선**했다. ★근거 반증 — 「나머지 둘은 final-gates 체인 안에 있다」가 절반 거짓이었다(체인 안은 `bl-audit-test.sh` 하나뿐). 그 하네스는 30/30 통과하고 원본 sed 추출이라 드리프트가 없다                                                                                                                                                                                                                                                                                           | `OrderRepository` 를 손볼 때 함께 · 다음 dead-code 스윕                                                           | S         | 2026-08-06 dead-code-sweep                             |
| [BL-602](#bl-602) | ★**루트 prettier 가 `frontend/` 안의 json/md/yml 을 포맷하지 못한다** — `frontend/.prettierrc` 가 `prettier-plugin-tailwindcss` 를 선언하는데 lint-staged 는 **루트**에서 prettier 를 돌리고 루트 `node_modules` 엔 그 플러그인이 없다. ⇒ `frontend/package.json` 을 스테이징하는 커밋은 **pre-commit 에서 죽는다**(실측 재현)                                                                                                                                                                                                                                                                                                                                                        | `frontend/` 안의 json/md/yml 을 커밋해야 할 때 (지금은 우회 가능하지만 다음엔 막힌다)                             | S         | 2026-08-06 e2e-consolidation                           |
| [BL-612](#bl-612) | ✅ **Resolved** (2026-08-09 backlog-sweep) — LESSON-095 압축 승격 → 버퍼 14,480B 삭제 → INDEX tombstone 전환. ★압축한 이유 = `lessons.md` **400줄 상한이 게이트 강제**(`docs-audit.sh:135`), 착수 시 380줄. ★**같은 위반 버퍼가 9건 더 있다**(최대 48,863B) — 본 항목 범위 밖. 원문: `docs/dev-log/2026-08-06-entry-set-divergence.md` 버퍼가 `docs/lessons.md` 로 승격되지 않았다 — ADR-026 §3 은 「세션 종결 시 승격 의무, 승격하면 버퍼를 비운다」인데 회차는 끝났고(PR #553 머지) 버퍼는 9천자로 남아 있다(반증 카드 상한 1~2천자 초과)                                                                                                                                           | 다음 문서 정리 회차                                                                                               | XS        | 2026-08-07 docs-overhaul 리뷰                          |
| [BL-613](#bl-613) | `live_signal.py` 핸들러 가시화가 남긴 **줄 수 부채** — `_evaluate_session_with_engine` **506줄**(Kind B 추출 E8~E14 미완) · `_place_planned_entry` 236 · `_reconcile_conditional_entries_inner` 203 · `_async_dispatch_event` 256(최대 `try` 본문 **225줄** — 이제 이게 최대). ★가시성 목표(최대 try 845→8)는 달성됐고 줄 수는 못 채웠다                                                                                                                                                                                                                                                                                                                                              | `live_signal.py` 를 다음에 크게 손댈 때 ([BL-580] 착수 회차와 겹친다)                                             | M         | 2026-08-04 handler-visibility (status 승계)            |
| [BL-614](#bl-614) | ✅ **Resolved** (2026-08-09 backlog-sweep) — **LESSON-096** 승격(`git show 0f0f0b06:…` 에서 원문 회수). ★3건 중 ③(검증 도구 적대 검증)은 **새 항목을 만들지 않았다** — **LESSON-092 재발**이고 그건 이미 `backend/AGENTS.md` §10 으로 승격돼 있다(작성 규칙 = 같은 패턴이면 반복 횟수 증가). 원문: 2026-08-04 handler-visibility 회차 방법론 **3건이 `docs/lessons.md` 미승격** — dev-log 본문은 문서 대개편에서 삭제됐고 INDEX 한 줄과 git history 에만 남았다(다중집합↔문장 순서 · 재적재 지문 = celery 배너 · 검증 도구를 먼저 적대 검증)                                                                                                                                          | 다음 문서 정리 회차 ([BL-612] 와 함께)                                                                            | XS        | 2026-08-04 handler-visibility (status 승계)            |
| [BL-615](#bl-615) | 스택 규칙 파일이 공식 권장 크기의 **2배** — `backend/AGENTS.md` **416줄** · `frontend/AGENTS.md` **316줄** (Claude Code 문서 권장 = 파일당 200줄 이하, 「Longer files consume more context and reduce adherence」). 그 디렉터리 파일을 열 때마다 전량 로드된다                                                                                                                                                                                                                                                                                                                                                                                                                        | 스택 규칙을 다음에 손댈 때 ([ADR-027] 정착 후)                                                                    | S         | 2026-08-07 ADR-027 (배치 이전 중 실측)                 |
| [BL-616](#bl-616) | 부트스트랩을 **우회해 만든** 워크트리는 husky 훅이 없다 — `pnpm install` 을 건너뛰면 `prepare: husky` 가 안 돌아 `.husky/_`(미트래킹)가 안 생기고, git 은 없는 `core.hooksPath` 를 **경고 없이 무시**한다. 실태: 워크트리 5개 중 **4개 정상**, 우회 생성된 1개만 결손(2026-08-07 정상화 완료). ★남은 축 = **감지 수단이 없다** — 훅이 안 도는 실패 모드는 출력이 0줄이라 「통과」와 구별되지 않는다                                                                                                                                                                                                                                                                                   | 워크트리에서 훅 미작동이 또 관측되면                                                                              | S         | 2026-08-07 ADR-027 회차 (자기 커밋에서 발견)           |
| [BL-618](#bl-618) | ✅ **문서를 코드에 맞췄다(①) + 경계 오라클 신설.** ★「1200px」는 **5곳이고 전부 콘텐츠 그리드 축**(셸 미개입) ⇒ 셸 경계는 1024/768 둘뿐. ★★**정본은 셋이 아니라 넷** — `@theme` 이 `sm:` 640→375 · `xl:` 1280→1200 으로 덮어 AGENTS.md 표가 **틀린 값**이었다. ★e2e `sidebar` grep 0건 → `design-canon-responsive.spec.ts` 신설. 잔여 [BL-644~647]                                                                                                                                                                                                                                                                                                                                    | 앱 셸 반응형(사이드바 축소·검색바 숨김·컨테이너 폭)을 다음에 손댈 때                                              | S         | 2026-08-07 prototype-canon-v2                          |
| [BL-617](#bl-617) | ★**「과거 기록」이 아닌 운영 절차 4종이 working tree 밖으로 나갔다** — Cloud Run 런북(39KB)·Grafana 셋업·Bybit mainnet 체크리스트(11KB)·법무 임시 런북. ADR-026 의 분류 기준이 **위치**(폴더 이름)였지 미래 유용성이 아니었던 결과다. 머지 후 `docs/` 전체에서 Cloud Run·Grafana·Prometheus·mainnet·법무 언급 **0건**인데 `alerts.yml`·`Dockerfile`·워크플로 4종은 레포에 살아 있다. ★지금 되살리지 않는다 — 트리거 시점에 갱신해 재등재                                                                                                                                                                                                                                              | [BL-071] 프로덕션 배포 발동 시 · Bybit mainnet 전환 시                                                            | S         | 2026-08-07 PR #554 리뷰                                |
| [BL-621](#bl-621) | ✅ **골든 `expected.json` 이 두 겹으로 낡아 있었다** — 손익 3지표가 2026-06-26(`80a2138e`) 이후 동결인데 그 뒤 ⑴ `cda575f2` 가 `ta.atr` 를 rolling SMA → Wilder RMA 로 바꾸고 ⑵ [BL-603] 이 비용 기본값을 내렸다. **Resolved** — 구 ATR + 구 비용을 **동시에** 되돌리자 4지표 전건 byte-identical 재현(⑴로 원인 특정). ★유일하게 보던 `num_trades` 는 네 조합 전부 14 라 **판별력 0** 이었다. `regen_golden.py` 신설 + `test_golden_backtest.py` 를 실제 오라클로 승격                                                                                                                                                                                                                | —                                                                                                                 | XS        | 2026-08-07 gap-resync-autopsy                          |
| [BL-627](#bl-627) | ✅ **`regen_golden.py` 에 출력 경로 리다이렉트가 없어 라운드트립 시험이 **실제 `expected.json` 을 두 번 덮어쓰고 finally 에서 바이트 복원**한다 — 정상 종료 시 오염 0이지만 강제 종료되면 워킹 트리가 더러워진다. `--out-dir` 추가가 수리. ★부수: `--check` 의 「차이 없음」 종료 코드가 계약에 미명시.** 2026-08-09 해결 — `--out-dir`(--confirm 전용) 신설, 시험은 tmp 로 쓰고 **정본 불변을 직접 단언**. ★제안된 변이(SIGKILL→dirty)는 재현 불가라 판별 가능한 변이 2종으로 교체했다                                                                                                                                                                                               | `regen_golden.py` 를 CI·병렬 실행에 넣을 때                                                                       | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-628](#bl-628) | ✅ **라이트 `--warning` `#875206`→`#824e05`** (subtle 6.03 / card 6.78 / bg 6.33 / bg-alt 5.99). ★자리는 마케팅 푸터가 **아니라** `legal-notice-banner.tsx:15`(전 라우트 상단). ★★**캐논 감사는 다크만 잰다** — 라이트를 재는 게이트가 0이었다 → `light-canon-contrast.test.ts` 신설. 잔여 [BL-648]                                                                                                                                                                                                                                                                                                                                                                                   | 라이트 공개 라우트 canon 을 다크 이하로 내리려 할 때                                                              | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-629](#bl-629) | ✅ **데드 `--chart-*` 7종 삭제**(axis·grid·bullish·bearish·line·area-top·area-bottom, 전부 참조 0건). `--chart-grid` 는 `brand-palette.ts`+sync 테스트도 동반. ★★**삭제를 지킬 것이 없었다** — 계약 테스트가 「정의된 것을 읽나」를 안 봤다 → **역방향 래칫**으로 정의 집합 동결                                                                                                                                                                                                                                                                                                                                                                                                      | 차트 축 색을 손대려 할 때 · 토큰 정리 스윕                                                                        | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-630](#bl-630) | ✅ **언레이어드 `table.trades tbody td.pos/.neg` 로 닫았다** — 명시도가 아니라 **캐스케이드 레이어**로 이긴다(KITPORT 무접촉). ★민짜 `.pos` 는 기각(표 밖 소비자까지 폭발). 오라클 = `design-canon-table-tone.spec.ts` 6조합×2테마, **역방향 2 포함**                                                                                                                                                                                                                                                                                                                                                                                                                                 | `<td>` 안에서 `.pos`/`.neg` 를 `.num` 없이 쓰게 될 때                                                             | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-626](#bl-626) | ✅ **`count` dedup + opt-in 회수 `--prune-archives`** — `unreadable_labels` 가 `(label, at, session_id)` **관측 단위**로 센다(키에 `archive` 를 넣지 않는 것이 요점). 회수는 개수가 아니라 **포함관계** 기준: 같은 `(log_from, predicate_version, classifier_ok)` 에서 `log_to` 최신본이 나머지의 상위집합. ★★★**후보 ⑴ 「최근 N개만」은 판정을 깎는다 — 실측 반증**: 228벌에서 최근 50만 남기면 커버리지 시작이 08-04→08-08(나흘 소실), 168h/30분이면 ~336벌 필요 ⇒ 어떤 상수 N 도 불가. 실측 228→66벌(회수 162 · `log_to='Error'` 파손 10벌은 무접촉 — 문자열 정렬로 재면 파손본이 대표로 뽑힌다), **판정 diff 공집합**(실격 15건 불변). ★동기는 미발화 — 228벌 = **0.10MB · 59ms** | `.soak/` 디스크 압박이 보일 때 · 게이트 1회 실행이 느려질 때                                                      | XS        | 2026-08-07 soak-unattended-watch                       |
| [BL-623](#bl-623) | 서버 클론이 `--single-branch` 라 feature 브랜치가 기본 fetch 로 안 온다 — `remote.origin.fetch` 가 main 한 줄뿐이라 `git checkout <branch>` 가 `pathspec did not match` 로 죽는다. 우회는 refspec 명시. 근본 수리(`git remote set-branches origin '*'`)는 소크가 도는 서버의 git 설정 변경이라 이연                                                                                                                                                                                                                                                                                                                                                                                   | 서버에서 feature 브랜치를 다시 받아야 할 때                                                                       | XS        | 2026-08-07 fe-oracle-deploy                            |
| [BL-638](#bl-638) | 🟡 `docs/archive/` 부재 — 2026-08-08 에 `lessons-archive-2026H1.md` 하나로 복원됐지만, `legacy_paths` 가 권장하는 하위 경로 4종은 여전히 없어 안내가 실행 불가다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 문서 보관 경로를 다시 안내하거나 정리할 때                                                                        | S         | 2026-08-08 bl003-unblock                               |
| [BL-640](#bl-640) | `.metrics` 가 컨테이너 세대를 넘어 누적된다 — `engine_only_suppressed` 합산 89 중 15가 이전 세대 값이라 창 안 차분에 창 밖 값이 섞인다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 게이트가 `.metrics` 값을 창 기준으로 해석할 때                                                                    | S         | 2026-08-08 bl003-unblock                               |
| [BL-644](#bl-644) | ✅ **Resolved — 767 → 768 한 줄.** 이 훅이 고르는 것은 Sheet vs Dialog 라 **셸의 모바일 판정과 같은 축**이고 셸은 `max-width:768px` 에서 넘어간다 ⇒ CSS 축에 붙였다. ★**세 축은 768 에서 전부 일치할 수 없다** — `min-width`·`max-width` 둘 다 경계값을 포함하므로 768 은 Tailwind `md:`(데스크탑)와 raw CSS(모바일)가 **동시에 참**인 유일한 점이다. 훅↔CSS 는 이제 일치, `md:`↔CSS 겹침은 이 BL 이전부터의 구조적 성질이라 그대로                                                                                                                                                                                                                                                   | 반응형 셸을 다시 손댈 때                                                                                          | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-645](#bl-645) | ✅ **Resolved (2026-08-09, W3)** — ★**처방 ③「주석만 달면 끝」이 틀렸다** — 정의 자리는 KITPORT 센티넬 안이고 가드가 **주석까지 대조**해 한 줄에 빨개진다(② 와 같은 allowlist 선행). ★**「어디에도 안 적혀 있다」도 틀렸다** — `DESIGN.md` §10.6 이 이미 근거까지 적고 있었다. 진짜 결함은 **줄 번호가 낡은 것**(`1159-1178`·`:1853` → 실측 `1146-1165`·`:1840`). 근거는 가드 밖 2곳에 두고 CSS 규칙은 안 건드렸다                                                                                                                                                                                                                                                                    | 백엔드 검색을 붙일 때 · CSS 정리 스윕                                                                             | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-646](#bl-646) | ✅ **Resolved — ① 등재**(`DESIGN.md` §4.3.1 신설, 콘텐츠 그리드 전용 6번째 경계). 흡수 2안 **실측 기각**. ★★**전제가 틀렸다 — 그리드가 받는 폭은 뷰포트가 아니라 `.page` 콘텐츠 박스이고 뷰포트에 단조가 아니다**(`--sidebar-w` 가 1024 에서 232→64 계단): 뷰포트 1023→**1025** 에서 콘텐츠가 911→**745** 로 **166px 줄어든다**. ⇒ 1024 흡수는 **가장 넓을 때 접는다**(모순 166px), 768 흡수는 뷰포트 769(콘텐츠 657)에서 `.trade-detail-metrics` 3열 219px 씩이 되며 `.metric` +6px **실제 파손**(「시각」이 「시/각」으로 꺾임), 900 유지가 모순 42px 로 최소. 근본 해는 컨테이너 쿼리 → [BL-647]. ★`frontend/AGENTS.md` §10 표는 [BL-602] 로 **미반영**                            | 반응형 정본을 다시 손댈 때                                                                                        | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-647](#bl-647) | `frontend/AGENTS.md` §10 은 mobile-first 필수인데 `globals.css` 의 `@media` **30곳이 전부 `max-width`**(min-width 0건) = 100% desktop-first. 2026-08-08 에 규칙의 **사거리를 좁혀** 봉합했고(신규 Tailwind 컴포넌트만 필수) 전면 전환은 미결                                                                                                                                                                                                                                                                                                                                                                                                                                          | CSS 규약을 집행 가능하게 만들 때                                                                                  | M         | 2026-08-08 fe-canon-and-responsive                     |
| [BL-648](#bl-648) | 🟡 **공개 라우트 라이트 런타임 커버리지 닫힘** — 처방 ②(`design-canon-public-light.spec.ts` 신설 + 감사 코어에 `theme` 옵션). ★**`colorScheme` 만으론 테마가 안 바뀐다**(`defaultTheme="dark"` ⇒ localStorage 선호값 필요) — `probeTheme()` 이 렌더 배경색을 읽어 도달 확인, 없으면 fail-open. ★★음성 대조: `--warning` 을 [BL-628] 회귀값으로 주입 ⇒ 새 spec **5/5 red**, **기존 다크 spec 은 5/5 초록**(AA 통과·캐논만 미달이라 하드 실패 게이트로 원리상 안 잡힌다). 복원 sha256 일치. 잔여 = **인증 셸 `.sidebar` 실폭**(소크 결합 [BL-597])                                                                                                                                      | 라이트 테마 회귀가 한 번 더 나올 때                                                                               | S         | 2026-08-08 fe-canon-and-responsive                     |
| [BL-649](#bl-649) | ✅ **Resolved — ① 삭제**(라이트·다크·`@theme inline` 3면 21줄). ②(`var(--warning)` 별칭 강등)를 버린 이유 = **별칭도 이름이고 소비자 0건이면 값을 못 한다** — 남기면 `@theme inline` 이 계속 유틸을 찍어 다음 사람이 또 고민한다. ★**「소비 0건」은 맞았지만 「참조 0건」은 아니었다** — [BL-629] 역방향 래칫 `CHART_VARS_FROZEN` 이 `--chart-1..5` 를 동결 목록에 잠그고 있었고(주석이 스스로 「처분은 [BL-649]」라 지목), 목록을 안 고쳤으면 집합 동등 단언이 red — **래칫이 설계대로 물었다**. 부수로 댕글링 주석 2줄 `warning` 정정                                                                                                                                               | 토큰 정리 스윕                                                                                                    | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-652](#bl-652) | ★**[BL-598] 의 결론은 전부 warm 프로세스 한정이다 — cold 축은 미측정**. 프로파일러 `section_import` 이 **첫 서브프로세스(17초, bytecode 컴파일+파일 캐시 워밍 포함)를 버리고** 이후 0.26s 로 가설 (a) 를 기각했는데, **CI 러너는 매 잡이 cold** 이고 샤드를 나누면 샤드마다 cold 다. 버린 17초가 샤드 수만큼 반복되는지는 아무도 안 쟀다(3샤드면 최악 51초). [BL-598] ② 의 파싱 디스크 캐시는 **파싱 비용만** 지우고 import·bytecode 는 캐시 히트여도 일어나므로 이 축은 남는다                                                                                                                                                                                                       | [BL-598] ② 착수 시 · CI 샤드 수를 늘리려 할 때                                                                    | S         | 2026-08-08 zero-touch-bundle                           |
| [BL-658](#bl-658) | `decisions/013-optimizer-strategy.md` 소급 작성 — ADR-013 은 결번인데 **실체는 삭제된 dev-log 로 git 에 살아 있다**(`94da86b1^`, 24,703B). [BL-504] 는 인용을 tombstone 경로로 돌려 닫았고, 남은 것은 **그 실체를 `decisions/` 로 승격**하는 일이다. 소급 작성은 결정을 새로 만드는 게 아니라 이미 실행된 결정을 기록하는 것이므로 **없는 근거를 지어내지 말고** `optimizer/executors/` 코드와 대조해야 한다                                                                                                                                                                                                                                                                          | Optimizer 설계를 실제로 바꿀 때 (알고리즘 교체 · scikit-optimize 이탈 · GA 파라미터 변경)                         | M         | 2026-08-09 backlog-sweep ([BL-504] 분리)               |
| [BL-660](#bl-660) | `regen_golden.py --confirm` 산출과 커밋본의 **포맷이 구조적으로 어긋난다** — pre-commit `prettier --write` 가 배열을 한 줄로 접고 스크립트는 `json.dumps(indent=2)` 로 원소당 한 줄을 쓴다. 그래서 정본 갱신 의도로 `--confirm` 을 돌리면 diff 에 **의미 없는 재포맷이 항상 섞인다**(실측 `+29/-2`). ★`--check` 는 **파싱된 값**을 비교하므로 이 어긋남을 구조적으로 못 본다                                                                                                                                                                                                                                                                                                          | 골든을 의도적으로 갱신할 때 / `regen_golden.py` 를 CI 에 넣을 때                                                  | XS        | 2026-08-09 backlog-sweep-4lane (W2, BL-627 부수)       |
| [BL-659](#bl-659) | `design-canon-calibration.spec.ts` 의 `screen-06-strategies-list.html` 케이스가 **간헐 실패**한다 — 2026-08-09 W3 에서 7회 중 2회. 같은 커밋에서 연속 3회는 42/42 green 이고 `git stash` 로 내 diff 를 걷어내도 통과/실패를 오갔다 ⇒ **코드 회귀가 아니다**. ★위험은 실패 자체가 아니라 **다음 회차가 이걸 자기 회귀로 오독하는 것**                                                                                                                                                                                                                                                                                                                                                  | 디자인 캐논 게이트가 빨개졌을 때 / 캐논 스윕 착수 시                                                              | XS        | 2026-08-09 backlog-sweep-4lane W3                      |
| [BL-709](#bl-709) | ★**전략 목록 RSC prefetch 가 URL 정렬을 안 읽어 정렬 링크마다 왕복이 하나 더 든다** — [BL-430] 이 정렬을 URL 스칼라로 옮겼는데 `strategies/page.tsx` 는 `searchParams` 를 읽지 않고 `order_by:"updated_at"` 을 하드코딩해 prefetch 한다. `/strategies?order_by=sharpe_ratio` 진입 시 **서버 prefetch 가 버려지고** 클라이언트가 refetch 한다(기능은 옳고 비용만 든다). 처방 = `searchParams`(Next 16 은 `Promise<>`) 를 await 해 화이트리스트 검증 후 같은 query 로 prefetch — 화이트리스트를 `features/strategy/` 로 올려 client 와 **1벌 공유**해야 한다                                                                                                                            | 전략 목록을 다시 손댈 때 / 정렬 링크 공유가 실사용될 때                                                           | S         | 2026-08-12 surface-demo-pack (G5)                      |
| [BL-710](#bl-710) | 전략 목록 성과 정렬·파생 필드의 **규모 비용 3종** — ⑴ `latest_completed` 서브쿼리가 owner/page 로 스코프되지 않아 전역 백테스트 규모만큼 든다 ⑵ `pine_source` 를 전량 로드해 행마다 정규식을 돈다 ⑶ `live_signal_sessions` 에 `strategy_id` **선행 인덱스가 없다**(기존 3개는 `user_id`/`is_active` 선행). 현 규모(전략 3 · 백테스트 7 · 활성 세션 0)에서는 무해하다                                                                                                                                                                                                                                                                                                                  | 전략 목록이 느려질 때 / 전략·백테스트가 수천 건이 될 때                                                           | S-M       | 2026-08-12 surface-demo-pack (codex G6 #1·#5·#6)       |
| [BL-711](#bl-711) | `metrics` JSONB **손상값**이 정렬 캐스팅에서 목록 전체를 500 으로 만든다 — `astext.cast(Numeric)` 는 `{"total_return":"corrupt"}` 에서 `invalid input syntax for type numeric` 이다. 같은 응답 경로의 `metrics_summary_from_jsonb` 는 손상값을 `None` 으로 격리하는데 **정렬 경로만 그 방어를 우회**한다. ★**선재다** — `backtest/repository.py:165-168` 이 같은 패턴을 4축에 먼저 갖고 있다                                                                                                                                                                                                                                                                                          | 손상 `metrics` 가 관측될 때 / 정렬 축을 늘릴 때                                                                   | S         | 2026-08-12 surface-demo-pack (codex G6 #2)             |
| [BL-712](#bl-712) | 전략 목록 **표시 정합 2건** — ⑴ `lifecycle` 이 `is_archived` 를 안 봐서 아카이브된 전략도 `validated`/`deployed` 로 응답한다(칩 4번째 값이 없다 = 사용자 결정) ⑵ 정렬 select 라벨이 **방향을 말하지 않는다** — `?order_by=total_return&order=asc` 로 진입하면 오름차순인데 라벨은 「수익률 높은 순」이다(UI 는 그 URL 을 만들지 않지만 공유·수동 편집으로 도달한다)                                                                                                                                                                                                                                                                                                                   | 전략 목록 표시를 다시 손댈 때 / 아카이브 화면을 낼 때                                                             | S         | 2026-08-12 surface-demo-pack (codex G6 #4·#12)         |
| [BL-713](#bl-713) | e2e 정체성 프로브가 `<title>` **부분일치**라 고유 식별자가 아니다 — 다른 앱의 title 이 `QuantBridge` 를 포함하기만 하면 통과한다. 지금은 판별에 성공하지만(`"Nexus Admin"` 실측 red) 우연에 의존한다. 처방 = 고유 마커(예: `<meta name="qb-app" content="quantbridge">`)를 심고 프로브가 **그것**을 본다                                                                                                                                                                                                                                                                                                                                                                              | 정체성 프로브가 거짓 통과하는 것이 관측될 때 / 같은 호스트에 앱이 늘 때                                           | XS        | 2026-08-12 surface-demo-pack (codex G6 #10)            |

### BL-491

**Title:** 백테스트 폼이 Live 레버리지를 미러하지 않는다 (차단 사유가 이미 사실이 아니다)
**Category:** Frontend / 정합
**Priority:** P3
**Trigger:** 백테스트↔라이브 폼 패리티 작업 시
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — live_blocked_leverage 분기와 liveLeverage===1 게이트가 그대로 있고 leverage 는 상수 1 로 초기화 — 미러 배선 미착수. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 live-engine-parity 적대적 검증.

**원인 / 영향:** `useBacktestForm.ts` 의 `liveLeverage != null && liveLeverage !== 1` 이 `live_blocked_leverage` 를 내고 `BacktestSizingFieldSet.tsx` 가 "Live 미러" 옵션을 `liveLeverage === 1` 로 막는다. 원래 문구는 "백테스트의 1배 자기자본 기준과 비대칭" 이라 설명했는데 **거짓**이다. 같은 폼에 백테스트 레버리지 입력이 있고 `v2_adapter` 가 `leverage=cfg.leverage` 를 같은 엔진 게이트로 넣는다. BL-483 배선 후엔 라이브도 레버리지를 반영하므로 차단 사유가 더 이상 없다.

이번 스프린트는 **문구만** 사실대로 고쳤다(술어 불변). 실제 미러링 배선은 미착수.

**권장 접근:** Live 설정(leverage / margin_mode / position_size_pct)을 백테스트 config 로 미러하는 경로를 열고 `live_blocked_leverage` 분기를 제거한다. 미러 시 백테스트↔라이브 패리티가 폼 수준에서도 성립한다.

**영향 파일:** `frontend/src/app/(dashboard)/backtests/_components/forms/useBacktestForm.ts`, `.../BacktestSizingFieldSet.tsx`, `.../live-settings-badge.tsx`.

**Risk:** 🟢 (UX / 정합. 금전 영향 없음).

---

### BL-389

**Title:** backtest finance math 10 함수 (~250 LOC) 가 v2*adapter god-file 에 혼재 — `engine/metrics.py` Deep Module 추출 (locality)
**Category:** Backtest / Architecture (shallow-by-size / locality)
**Priority:** P3
**Trigger:** backtest deepening sprint
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — metrics.py 는 실재하나 \_v2*\* finance 헬퍼 12개가 여전히 v2_adapter.py(1239줄) L935-1167 에 남아 있어 이동 미완. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-30-backtest-deepen.md` (codex DOWNGRADE → `metrics.py` 부재 직접 검증 후 KEEP 정정)

**원인 / 영향:** `v2_adapter.py` 의 본 책임은 V2RunResult → BacktestOutcome 변환(orchestration)인데, Sharpe/MaxDD/CAGR/win-rate/streak/monthly 등 도메인-비종속 finance math 함수가 같은 모듈에 혼재 = shallow-by-size, Locality 깨짐. stress_test 재사용은 speculative(현재 `result.metrics` 만 소비)라 추출 정당화는 locality 중심.

**★전제 정정 (2026-08-03 실측, backtest-metric-oracle):** 본 항목이 전제한 「`engine/metrics.py` 부재」는 **낡았다** — 그 파일은 2026-07-26 backtest-trust 스프린트 이후 실재하며 현재 343줄(`sharpe_ratio`/`sortino_ratio`/`calmar_ratio`/`compute_excursion_stats`/`compute_side_metrics` 등 12 함수)이다. 남은 이동 대상은 `v2_adapter.py` 의 `_v2_*` 헬퍼 블록이고 위치도 바뀌었다 — 등재 당시 인용 `L707-912 / 964L` 은 stale, 현재는 **1211줄 중 L907-1162**. 레포 전체 grep 결과 그 헬퍼 12개를 `src/` 안에서 import 하는 곳은 **0건**이라 순수 move 가 안전하다(테스트 2파일만 직접 import).

**권장 접근:** 남은 finance 계산을 기존 `engine/metrics.py` 로 이동 — '(equity_curve, trades, config) → 지표 묶음' 작은 Interface 뒤에 큰 behavior 은닉. v2_adapter 는 호출만 남김. 이동(move)이라 golden oracle parity 로 회귀 0 보장.

**영향 파일:** `engine/v2_adapter.py`(L907-1162 추출), 기존 `engine/metrics.py`.

**Risk:** 🟢 (move refactor — `test_golden_oracle_minimal` + `test_metrics_real_extract` parity 가드, 이동 전후 동일 oracle 재실행).

---

### BL-390

**Title:** backtest exit-leg maker/taker `fill_type` 라우팅이 v2_adapter 2곳 char-identical 복제 (주석은 SSOT 주장)
**Category:** Backtest / Architecture (DRY / locality, money-path)
**Priority:** P3
**Trigger:** backtest deepening 또는 `exit_kind` 의미 변경 시
**Est:** XS-S (1-3h)
**상태:** ⏳ 대기 (트리거 미도래) — 라우팅 삼항식이 v2_adapter :354/:838 에 여전히 char-identical 복제 — 헬퍼 위임 없음(줄번호만 265/568→354/838로 이동). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-30-backtest-deepen.md`

**원인 / 영향:** exit leg maker/taker 분기 `fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"` 가 `v2_adapter.py:265`(\_build_raw_trades)와 `:568`(\_compute_metrics)에 character-identical 복제. L549 주석은 'SSOT 위임으로 중복 제거' 라 주장하나 실제 SSOT 는 `_leg_cost` 뿐이고 routing 분기는 미위임 → `exit_kind` 의미 변경 시 2곳 동시 수정(money-path 수수료/슬리피지). 작지만 확정된 Locality 결함.

**권장 접근:** `fill_type` 라우팅을 단일 헬퍼(또는 RawTrade 메서드)로 위임 → 두 소비 사이트가 같은 한 곳을 호출. 주석의 SSOT 주장과 코드 일치.

**영향 파일:** `engine/v2_adapter.py` (:265, :568).

**Risk:** 🟢 (refactor-safe — `test_exit_leg_cost_split` C14 불변식이 발산 가드).

---

### BL-306

**Title:** `~/.claude/CLAUDE.md` §5 한국어 콜론 종결 lint mechanism 도입
**Category:** Docs / Lint
**Priority:** P3
**Trigger:** ~~누적 위반 181 line 검출 (2026-05-15 audit) — auto-fix 가능~~ → **2026-08-10 반증**: 「위반」이 아니었다
**Est:** ~~S (3-5h)~~ → 해당 없음 (고칠 대상 0건)
**상태:** ✅ Resolved (기각) — 2026-08-10 backtest-submit-fix. **전제가 실측으로 반증됐다.**
「181줄 위반 · false positive 0 · `:`→`.` 일괄 auto-fix」 셋 다 거짓이고, auto-fix 를 돌리면 문서 200줄이 손상된다.
**트리거 판정:** 해소 (기각) — 트리거가 센 「위반 181 line」이 위반이 아니었다 (2026-08-10 backtest-submit-fix)
**출처:** `2026-05-15-claudemd-align-audit.md` §6 Track C1, [LESSON-068](lessons.md)

**현 상태:** docs/dev-log 161 + dogfood 12 + guides 8 = 181 line 한국어 sentence + `:` end-of-line 위반. false positive 0. lint mechanism 0 = LLM 매 generation 자연 위반.

**권장 접근:**

1. markdownlint custom rule 또는 ruff custom plugin 으로 한국어 콜론 종결 검출 (regex `[가-힣]+\s*:\s*$` minus 코드 fence + URL + table cell + frontmatter)
2. auto-fix script — 검출 line `:` → `.` 일괄 sed (false positive 0 검증된 docs/\* scope 만)
3. pre-commit hook 추가 + CI gate
4. LESSON-068 2/3 누적 → 3차 시 문서 lint 영구 규칙 승격 (구 `global.md` §5 는 ADR-026 으로 소멸 — 승격처는 `scripts/docs-audit.sh` 확장)

**영향 파일:** ~~새 lint config 1 + auto-fix script 1 + pre-commit hook 1 + 검출 181 line edit (auto-fix 1회).~~
→ **없음.** 아래 기각 근거 참조.

**Risk:** ~~🟢 (lint + docs only, code 영향 0)~~ → 🔴 **였다.** auto-fix 를 그대로 돌렸으면 정상 문장 200줄이 손상된다.

---

#### ✅ 기각 (2026-08-10 backtest-submit-fix) — 검출 규칙이 성립하지 않는다

원장이 명시한 정규식(`[가-힣]\s*:\s*$` minus 코드펜스·URL·표 셀·frontmatter)을
`git ls-files '*.md'` **전량**에 적용한 실측:

| 항목                                         | 건수    |
| -------------------------------------------- | ------- |
| raw 매치                                     | **201** |
| ├ 코드블록·리스트·표를 **여는 도입부**(정당) | 168     |
| ├ 뒤 절을 여는 산문 콜론(정당)               | 33      |
| └ **진짜 dangling 콜론(고칠 것)**            | **0**   |

★**「false positive 0」이 정확히 뒤집혔다 — 실제 false positive 는 사실상 100% 다.**
매치의 전부가 무언가를 **여는** 콜론이다. 예: `프론트엔드 구현 시 Tailwind 토큰으로 매핑:` 뒤에
코드펜스, `새 Celery task 추가 시:` 뒤에 리스트, `레버리지별 롱 청산 임계 실측:` 뒤에 표.
이를 `.` 로 치환하면 도입부 의미가 깨진다 — **auto-fix 는 수리가 아니라 파손이다.**

원장 수치 「181 → 197줄로 늘었다」도 재현되지 않는다. 「197줄」의 근거였던 `docs/dev-log` 원문
161건은 2026-08-06 에 삭제됐고, 현재 어떤 계수법으로도 181/197 이 나오지 않는다(201 / 33 / 0).

**판정:** 한국어 콜론 종결은 이 레포에서 **검출 가능한 위반 클래스가 아니다.** 「문장 종결 콜론」과
「도입부 콜론」을 구문만으로 가르는 규칙이 없고, 후자가 전부다. `scripts/docs-audit.sh` 확장은
**잡을 것이 없는 규칙**을 추가하는 일이 되므로 하지 않는다. [BL-307] (§6 file header lint) 은 별개
축이라 이 기각의 영향을 받지 않는다 — 위 「의존성: BL-306 과 묶음 sprint 가능」은 이제 성립하지 않는다.

**LESSON-068 누적은 늘리지 않는다** — 이번 건은 「lint 부재가 위반을 누적시킨다」의 사례가 아니라
**그 전제 자체의 반증**이다. 상세 = [LESSON-099].

---

### BL-307

**Title:** `~/.claude/CLAUDE.md` §6 한국어 file header lint + 누락 70 file backfill
**Category:** Lint / Source
**Priority:** P3
**Trigger:** ~~누적 누락 70 file 검출 (BE 14 + FE 56, 2026-05-15 audit)~~ → **2026-08-10 재측정 48 file** (BE **13** + FE **35**). main.py / trading/registry.py / app/layout.tsx 는 누락 확인 · `core/config.py` 는 **exempt list 가 면제**(원장 내부 모순, 면제 유지로 확정)
**Est:** ~~M (8-12h)~~ → **실제 ≈4h** (검출기 1벌 + 백필 48건 생성자 4기 병렬)
**상태:** ✅ Resolved — 2026-08-10 bl-307-header-lint. `scripts/header-audit.sh` 신설(BE·FE 공용 1벌) + 위반 **48 → 0** + pre-commit·CI 배선. 하네스 14/14 · 변이 6종 전건 판별.
**트리거 판정:** 해소 — 누락 전건 백필 + 신규 파일 차단 기구 배선 완료 (2026-08-10 bl-307-header-lint)
**출처:** `2026-05-15-claudemd-align-audit.md` §6 Track C2, [LESSON-068](lessons.md)

**현 상태:** ~~BE 14/157 + FE 56/243 = 70 file 누락~~ → **2026-08-10 종결.** 착수 시 실측 = 스캔 750 ·
면제 242 · 검사 **508** · 위반 **48**(BE 13 + FE 35). 종료 시 **0**.

★**「근거였던 전역 §6 는 소멸」이 반증됐다.** 규칙은 죽은 것이 아니라 **이사했다** — 루트
[`AGENTS.md`](../AGENTS.md) §개발 원칙이 지금도 「사고/계획/대화/문서/주석 = **한국어**」를 명령한다.
그리고 **코드가 관행을 증언했다**: 착수 시점에 이미 508개 중 **460개(90.6%)가 한국어 헤더 보유**
(BE 175/188 = 93.1% · FE 285/320 = 89.1%). 죽은 규칙의 부활이 아니라 **미집행 9.4% 의 회수**였다.

★**48건 중 27건은 「추가」가 아니라 「영→한 번역」이었다** — 이미 영어 헤더가 있었다. 번역 시
Sprint/BL 참조와 기술 세부를 **버리지 않고 옮기는 것**이 실제 작업의 대부분이었다.

**권장 접근 → 실제로 한 것:**

1. ~~ESLint custom rule (`require-korean-file-header.js`)~~ → **`scripts/header-audit.sh` 1벌**(BE·FE 공용).
   ESLint 로 하면 BE 는 별도 기구가 필요해 **면제 목록이 두 곳에 살고**, 그것이 이 레포가 반복해 겪은 표류다.
2. ~~ruff custom plugin~~ → **불가능**. ruff 는 커스텀 룰 API 자체가 없다. ★**Biome 도 불가능** —
   커스텀 룰 수단인 GritQL 이 **주석을 trivia 로 취급해 쿼리에서 볼 수 없다**(공식 문서 확인). 이 룰은 전부가 주석 검사다.
3. ✅ 백필 **48건**(70 아님). 생성자 4기 병렬, 배치별 파일 집합이 서로 소.
4. ✅ `Makefile: header-audit` · `.husky/pre-commit`(대상 소스 스테이징 시 **차단**) ·
   `ci.yml` **`documentation` 잡**(경로 필터가 없어 **항상** 돈다 — 「신규 파일 차단」이 목적인
   게이트를 조건부 잡에 두면 목적이 사라진다).

★**검출기에 로케일 자기검사를 박았다.** 이 감사기의 전부는 `grep '[가-힣]'` 한 줄에 걸려 있고
그 동작은 로케일에 달렸다(CI = GNU grep, 개발기 = BSD grep). 깨진 환경에서는 **전건 위반**이나
**전건 통과** 중 하나가 조용히 나온다. ⇒ 매 실행마다 양성·음성 한 쌍으로 판별력을 확인하고
실패하면 **rc=3 으로 판정을 포기**한다. 판정할 수 없을 때 초록을 내지 않는다.

**영향 파일:** ESLint config 1 + ruff config 1 + pre-commit hook 1 + 70 file 첫 줄 주석 추가.

**Risk:** 🟡 (lint config 변경 + 70 file touch — risk 낮으나 large diff).

**의존성:** ~~BL-306 과 묶음 sprint 가능 (양쪽 모두 lint mechanism + 누적 누락 backfill).~~
→ **2026-08-10 소멸 — [BL-306] 이 기각되어 [BL-307] 은 단독 축이다.** 묶을 상대가 없어졌을 뿐
아니라, [BL-306] 에서 반증된 「auto-fix 로 일괄 수리」를 **이 항목에 옮겨 붙이면 안 된다**:
저기서 거짓이었던 것은 검출 규칙이 산문에서 위반을 가려낼 수 있다는 전제였고, 여기 「첫 3줄에
한국어 주석이 있는가」는 **구문만으로 판정된다** — 즉 검출은 성립하지만 70 file 의 주석 **내용**은
생성이지 fix 가 아니다. 근거 = [BL-306] §판정 · [LESSON-099].

---

### BL-367

**Title:** `_async_dispatch_event` 205 LOC + 8× `mark_failed+commit+metric` 반복 블록 추출
**Category:** Trading / Architecture (shallow-by-size)
**Priority:** P3
**Trigger:** trading deepening sprint (clean win, 단독 가치 낮음)
**Est:** XS-S (1-2h)
**상태:** ⏳ 대기 (트리거 미도래) — \_async_dispatch_event(:4217~4472, 약 255 LOC)이 그대로 있고 mark_failed+commit+metric 반복이 9회, 추출 헬퍼는 부재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**현 상태:** `tasks/live_signal.py` `_async_dispatch_event`(:572-776, 205 LOC, nesting 4-5) 안에 `await event_repo.mark_failed(...) + commit() + qb_live_signal_dispatch_total.labels(...).inc() + return/raise` 패턴이 8회 반복(session_inactive / strategy_missing / invalid_settings / settings_unset / rejected / kill_switched / NotionalExceeded계열 / idempotency_conflict).

**권장 접근:** `_mark_failed_and_return(event_id, error, action, outcome, repo) -> dict` + `_mark_failed_and_raise(...)` 추출 → 함수 길이/중첩 감소. 단일 파일, 저위험 clean win.

**영향 파일:** `tasks/live_signal.py`.

**Risk:** 🟢 (단일 파일, 동작 불변).

---

### BL-370

**Title:** exit-field multi-SSOT — 8 필드 × OrderSubmit/Order/OrderRequest 평행 재정의
**Category:** Trading / Architecture (locality / distributed schema)
**Priority:** P3
**Trigger:** exit-field 추가 시 3곳 동시 수정이 부담될 때 (현재는 견딜 만함)
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — OrderSubmit/Order/OrderRequest 3곳 exit-field 평행 정의가 그대로 살아 있고 ExitFields mixin 은 레포 전역 0건 — Trigger 도 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** `2026-06-26-trading-deepen-2.md`

**현 상태:** `reduce_only`/`trigger_price`/`trigger_by`/`take_profit`/`stop_loss`/`trigger_direction`/`oco_group_id`/`trailing_stop` 8 필드가 `OrderSubmit`(dataclass, providers.py:67-83) / `Order`(SQLModel, models.py:193-218) / `OrderRequest`(pydantic, schemas.py:60-71) 3 boundary type 에 동일 타입·주석으로 재정의 (+ LiveSignalEvent subset). 필드 추가 시 3곳 동시 수정.

**권장 접근:** `ExitFields` mixin/base 추출 검토 — **단 3 base(dataclass/SQLModel/pydantic)를 가로지르는 mixin 은 awkward → over-abstraction 함정 주의.** ROI 낮으면 보류. 등재 = 가시성 확보용.

**영향 파일:** `providers.py` / `models.py` / `schemas.py`.

**Risk:** 🟡 (3 base 가로지르는 추상화 — 잘못하면 복잡도 증가).

---

### BL-371

**Title:** ws-stream 고빈도 fill 스트레스 — orphan buffer cap 1000 + concurrent 순서 미검증
**Category:** Trading / Hardening (observability)
**Priority:** P3
**Trigger:** post-Beta 실거래 빈도 상승 시 (monitor)
**Est:** S (2-4h)
**상태:** 🟡 부분 해결 — 버퍼·cap·gauge 축은 BL-448 로 소멸하고 discarded 카운터·테스트가 대체됐다; 남은 건 out-of-order/고빈도 stress 테스트뿐(Trigger 미도래). (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 외생 조건(post-Beta 실거래 빈도 상승). Beta 미도달. 본문도 「현재 데모 빈도엔 충분 · 현재는 등재만」으로 스스로 적었다 (2026-08-11 bl-703-partial-verdicts)
**출처:** `2026-06-26-trading-deepen-2.md`

**현 상태:** ~~`state_handler.py` orphan buffer FIFO cap 1000(`_ORPHAN_MAX`)~~ → **2026-08-09 [BL-448](#bl-448) 로 버퍼·cap·gauge 가 통째로 사라졌다** (읽는 프로덕션 경로가 없었다). 남은 관심사는 out-of-order WS fill message / supervisor crash-restart cycle 의 고빈도(>100 fills/s) 스트레스 테스트 미검증뿐이다. 현재 데모 빈도엔 충분.

**권장 접근:** post-Beta 모니터링 — ~~`qb_ws_orphan_buffer_size` gauge alert >800~~ → **`qb_ws_orphan_discarded_total{reason="terminal_event_lost"}` 증가율**(버퍼 크기라는 축 자체가 없어졌다) + 필요 시 concurrent ordering 테스트 추가. 현재는 등재만.

**영향 파일:** `trading/websocket/state_handler.py` + 테스트.

**Risk:** 🟢 (현재 미발현, monitor).

---

### BL-394

**Title:** BE 거래 분포/수익구조 집계 엔드포인트 — `useAllBacktestTrades` 2000-cap 페이지 루프 대체
**Category:** Backtest / API + Frontend
**Priority:** P3
**Trigger:** 2000+ trades 백테스트가 흔해질 때
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — BE 집계 엔드포인트가 없어 FE 가 2000건 cap 으로 전량을 끌어온다 — 단 페이지 fetch 는 이미 병렬이라 남은 것은 cap 과 전송량뿐 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint F1/F3 (FE 파생 분포·waterfall 은 표본 근사 캡션으로 정직 고지 중)

**원인 / 영향:** 수익 분포 histogram/거래 분포 donut/수익 구조 waterfall 이 FE 에서 전체 trades(최대 2000, 페이지 루프 10회)로 파생. 초과 시 "표본 기준" 근사. BE 집계 1 endpoint 면 정확+경량. **참고:** BE `gross_profit_abs`/`gross_loss_abs`/`per_side.*` 는 net(비용 차감 후) 기준 승/패 분해 — waterfall 용 비용 전(gross) 분해와 다름(FE `computeProfitStructure` 항등식 참조). 집계 endpoint 설계 시 두 정의 모두 제공 권장.

---

### BL-395

**Title:** lightweight-charts v5 업그레이드 spike — 네이티브 멀티-pane + 시간축 동기화
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** 차트 pane 4개+ 필요 또는 줌/팬 동기화 요구 시
**Est:** M (6-8h, spike)
**상태:** ⏳ 대기 (트리거 미도래) — 여전히 lightweight-charts ^4.2.0 이고, 차트는 createChart 2회 호출로 독립 인스턴스를 쌓는다 — v5 네이티브 pane 미도입. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint F2 (v4.2 는 멀티-pane API 부재 → 독립 인스턴스 3개 스택, 시간축 미동기화)

---

### BL-396

**Title:** `/backtests/[id]/trades` 상세 서브페이지에 TV 신규 컬럼(런업/드로다운/누적/fee split/exit_kind) 정렬
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 원장(trade-ledger-table)과 서브페이지 컬럼 비정합 불편 접수 시
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — 원장 CSV 는 cumulative_pnl·runup_abs·drawdown_abs·fee_paid·slippage_paid 를 내는데 서브페이지 상세는 손익·수익률·수수료 3종뿐 — 비정합 존속 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint F4 (원장만 신규 컬럼 반영, 서브페이지는 무변경)

---

### BL-397

**Title:** ~~백테스트 리포트 섹션 **탭** URL 딥링크 (`?section=`)~~ → **재기술: 10개 섹션 중 9개에 앵커 `id` 가 없다**
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 리포트 특정 섹션 공유 요구 시
**Est:** ~~XS-S (1-3h)~~ → **XS** (프롭 하나를 9곳에 넘긴다)
**상태:** ✅ Resolved — 2026-08-10 fe-shareable-urls. 앵커 10개 + 상단바 보정 + 마운트 1회 해시 재조정. ★**재기술된 처방마저 반증됐다** (아래 종결 절).
**출처:** 2026-07-05 TV-parity sprint F2 (탭 상태 비제어 유지 결정) → **2026-08-09 그 탭이 더 이상 없다**

★★**원 전제 반증 (2026-08-09 실측).** 이 항목은 「탭 상태가 비제어라 URL 에 실을 수 없다」를 전제로 썼다.
그 탭이 **지금 존재하지 않는다** — `backtest-report-shell.tsx:8` 이 직접 적는다:
「**이전 shadcn Tabs 5탭 IA 를 위 번호 섹션 구조로 재편했다**」(2026-07-05 리포트 IA 전면 재편).
리포트 상세(`backtests/[id]/page.tsx` → `BacktestDetailView` → `BacktestReportShell`) 전체에
`role="tablist"` · `aria-selected` · `TabsTrigger` 가 **0건**이다. ⇒ **`?section=` 쿼리는 표적이 사라졌다.**

★**그런데 사용자 요구(「리포트 특정 섹션 공유」)는 아직 안 닫혔다.** 지금 구조는
`<section className="section" id={id}>`(`:55`)라 **네이티브 `#fragment` 로 딥링크가 가능한데**,
`id` 가 **옵셔널**(`id?: string`)이고 실제로 넘기는 호출부가 **1곳뿐**이다:

| 축               | 실측                                                                                               |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| `<Section>` 호출 | **10개** (`num="01"`~`"10"`, `:90`·`:102`·`:122`·`:137`·`:177`·`:197`·`:215`·`:230`·`:246`·`:267`) |
| `id` 를 받는 것  | **1개** — `:236` `id={STRESS_ANCHOR}`(`:35` `"stress-test"`, 소비처 `:274` `ReportNextSteps`)      |
| 결과             | 10개 중 **9개가 링크 불가**                                                                        |

**재기술된 처방:** `?section=` 쿼리 파라미터·라우터 상태를 **만들지 마라**. 나머지 9개 `<Section>` 에
안정적인 `id`(예: `key-stats` · `performance` · `trade-analytics` …)를 넘기면 끝이다. 이미 `STRESS_ANCHOR` 가
그 선례이고 소비처까지 있다. **수용기준** = `/backtests/<id>#<section-id>` 로 열었을 때 해당 섹션으로 스크롤되고,
음성 대조로 `#없는-id` 는 페이지 상단에 머문다.

**Risk:** 🟢 렌더 트리 무변경(속성 하나 추가) · 기존 `stress-test` 앵커 불변이 회귀 판별자.

### ✅ 2026-08-10 fe-shareable-urls — 종결. ★**「프롭 하나면 끝난다」가 실측으로 반증됐다**

위 재기술은 「나머지 9개 `<Section>` 에 안정적인 `id` 를 넘기면 끝이다」라고 적었다.
**그대로 해봤더니 화면이 움직이지 않았다.** `id` 9개 + `scroll-mt` 만 넣은 판에서 e2e 실측:

```
Error: expect(locator).toBeInViewport() failed
Locator:  locator('section#trades')
Expected: in viewport
Received: viewport ratio 0
  9 × locator resolved to <section id="trades" aria-label="거래 내역" class="section scroll-mt-[76px]">…</section>
```

엘리먼트는 DOM 에 **있는데** 브라우저가 스크롤하지 않았다. 같은 실행에서 음성 대조(`#nope`)는
green 을 유지했으므로 계측기 고장이 아니다. 뿌리 — `backtests/[id]/page.tsx` 는 서버 prefetch 도
`HydrationBoundary` 도 없이 클라이언트 `BacktestDetailView` 만 렌더하고, 리포트는 React Query 가
끝난 뒤에 삽입된다. **네이티브 fragment 위치결정은 문서 로드 시점에 한 번이고 다시 시도하지 않는다.**
⇒ 마운트 1회 해시 재조정(`useEffect(…, [])` · `setState` 없음 · DOM 만 만진다)을 함께 넣어야 한다.

★**두 번째 발견 — 지금 있던 `#stress-test` 딥링크도 제목이 가려지고 있었다.** `scroll-margin` 이
레포 전체 0건인데 `.topbar` 는 `sticky; top:0; height:60px; z-index:110` 이다. `scroll-mt-[76px]`
(60 + 여유 16)을 `<Section>` 에 준다. `globals.css` 의 `.section` 은 KITPORT 센티넬 안이라
건드리면 `design-canon-kit-port.test.ts` 가 빨개진다 — 그래서 컴포넌트 쪽 유틸로 넣었다.

**앵커 id** — `key-stats` · `benchmark` · `metrics` · `trades` · `distributions` ·
`profit-structure` · `runup-drawdown` · `stress-test`(불변) · `assumptions` · `next-steps`.
접두어 없이 기존 `stress-test` 선례와 한 벌로 간다.

**검증** — vitest `backtest-report-shell.test.tsx` 10건(신규 5) · e2e `report-section-anchors.spec.ts`
**3건**(2026-08-10 정정 — 원문 「2건」은 오기다) · 표적 변이 **6종 전건 판별**(음성 대조 = §02 desc 문구 변경, 아무것도 안 뒤집음) ·
sha256 복원 확인 · MCP playwright 실 DB 검증(상단바 bottom 60 / 섹션 top 76 / 제목 top **107** =
47px 여유 · `#nope` 는 `scrollY` 0 · 375px 가로 오버플로 0 · 콘솔 error 0).

★**백로그의 「0건」 주장 하나도 틀렸다** — 「리포트 트리 전체에 `role="tablist"`·`TabsGrid` 0건」은
**최상위 IA 만** 본 값이다. §07 `runup-drawdown-section.tsx` 가 shadcn `Tabs` 를, §02
`equity-chart-v2.tsx` 가 `role="tablist"`/`aria-selected` 를 쓴다. 다만 그것들은 섹션 **안의 하위 뷰
전환**이라 `?section=` 을 되살릴 근거는 아니다 — 처방은 그대로다.

---

### BL-399

**Title:** `ta.sar` TV hand-oracle 부재 — parity 스팟 검증 미완
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3
**Trigger:** SAR 사용 전략 등장 시
**Est:** S-M (3-5h — AF/EP/flip 규칙 손유도)
**상태:** ⏳ 대기 (트리거 미도래) — SAR 구현·단위테스트는 있으나 전부 성질 검사뿐 — TV 손유도 오라클 값 대조는 코드·문서 어디에도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 TV-parity sprint P1-4 (wma/bb/mom/obv/cross 는 스팟 판정 완료 — bb=population stdev=TV biased 기본 ✓, mom/obv/cross ✓. sar 만 오라클 미작성)

---

### BL-400

**Title:** optimizer 쿼리만 `enabled: userId != null` 가드 — 도메인 간 React Query enabled 정책 비일관 (통일 여부 결정 필요)
**Category:** Frontend / React Query 컨벤션
**Priority:** P3
**Trigger:** FE 훅 팩토리 후속 정비 시 (`use-auth-ctx` 소비 도메인 전수)
**Est:** S (2-3h — 정책 결정 + 일괄 적용)
**상태:** ⏳ 대기 (트리거 미도래) — 사용자 결정 대기: optimizer만 enabled: userId != null 유지, 타 도메인은 여전히 무가드 발사 — (a)통일 vs (b)제거는 사용자 정책 결정이 선행 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (훅 팩토리 SSOT 작업 중 발견, 2026-07-05 코드 재검증)

**원인 / 영향:** `features/optimizer/hooks.ts:59,70` 만 `enabled: userId != null` 로 로그아웃 시 쿼리를 미발사한다. 나머지 도메인(backtest/strategy/trading/live-sessions/waitlist) list 훅은 가드 없이 `useAuthCtx` 의 `uid="anon"` sentinel + null token 으로 발사(401 → retry 1). PR #394 훅 팩토리(`use-auth-ctx`/`use-invalidating-mutation`/`query-poll`)는 폴링 가드만 SSOT 화했고 enabled 가드는 미흡수. 실버그는 아니나 로그아웃 시 도메인별 동작이 달라 디버깅·테스트 기대가 갈린다.

**권장 접근:** 결정 사안 — (a) 전 도메인 `enabled: userId != null` 통일(무의미 401 제거, `use-auth-ctx` 에 헬퍼 추가) vs (b) optimizer 가드 제거로 "anon 발사" 일원화. Grilling 1문항으로 결정 후 일괄 적용.

**Risk:** 🟢 (정책 결정 사안 — 어느 쪽도 회귀 표면 작음).

---

### BL-403

**Title:** recharts↔lightweight-charts(+optimizer inline-SVG) 차트 3원화 해소 — 라이브러리 수렴 결정
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** **BL-395(lwc v5 spike) 완료 후** — 멀티-pane/커스텀 시리즈 확보가 수렴 가능성 판정의 전제
**Est:** L (8-16h — 대상 플롯별 이식 난도 상이, spike 선행)
**상태:** ⏳ 대기 (트리거 미도래) — 3원화 대상 3계열(파일·의존성)이 전부 그대로 있고 선행 BL-395(lwc v5) 도 미완이라 Trigger 자체가 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-395=ACTIVE (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (차트 지연로딩 정리 중 3원화 실측)

**원인 / 영향:** 시계열=lightweight-charts(`trading-chart.tsx` 싱글턴 dynamic import + backtest equity/drawdown pane + live-sessions), 통계 플롯=recharts 5종(`charts/recharts-plots.ts` 단일 seam, 414KB), optimizer 2종(`genetic-generation-chart.tsx`/`bayesian-iteration-chart.tsx`)=recharts 의존 회피 목적의 손수 inline SVG — 사실상 3원화. 번들 이중 부담 + 스타일 토큰(`lib/chart-tokens.ts` 로 완충 중) 3중 유지보수 + 신규 차트마다 라이브러리 선택 부채. Sprint 30-β 결정("recharts 보존, 신규만 lwc")이 3원화로 표류했다.

**권장 접근:** BL-395 spike 결과로 lwc v5 가 histogram/donut/waterfall 급 통계 플롯을 감당하는지 판정 → (a) lwc 수렴 + recharts 제거 (b) recharts 유지 + inline-SVG 2종만 recharts 편입 (c) 현상 유지 재확인 중 택1. BL-235(N-dim viz — cross-page consistency 의무)와 라이브러리 결정 공유.

**영향 파일:** `charts/recharts-plots.ts` 계열 5플롯, `components/charts/trading-chart.tsx`, optimizer inline-SVG 2종, `lib/chart-tokens.ts`.

**Risk:** 🟡 (표면 넓음 — spike 선행 + 페이지별 스냅샷 회귀 필요).

---

### BL-405 — ❌ CLOSED: not-a-bug (오라클 전제 오류, 2026-07-12 재분류)

**Title:** ~~pine_v2 bool 시리즈 na→False 실체화 — 워밍업 스퓨리어스 시그널~~ → **재분류: 엔진이 TV 정답, 버그 아님**
**Category:** Backend / pine_v2 na-semantics
**Priority:** ~~P2~~ → **CLOSED**
**상태:** ✅ Resolved — ❌ CLOSED: not-a-bug (2026-07-12 재분류). 2026-08-09 backlog-sweep 에서 **상태줄만** 추가했다. 코드 0줄.
**출처:** 2026-07-12 pine-batch QA 오라클 ② (`report.md` §4.2) → **2026-07-12 A+B+C Trust 번들에서 TV 공식문서로 반증**

★**왜 2026-08-09 까지 ACTIVE 로 세어졌나.** `scripts/bl-audit.sh` 의 판정 우선순위는
③ 「헤딩에 **✅**」 → RESOLVED 인데 이 헤딩은 **❌** 다. 상태줄이 없어 ⑤ 기본값 ACTIVE 로 떨어졌다.
즉 176 은 **열려 있는 수가 아니라 「닫혔다고 선언되지 않은 수」**였고, 이 항목이 그 실례다.
★**어휘 주의** — `verdict_of`(`bl-audit.sh:75-80`)가 아는 낱말은 ACTIVE/PARTIAL/RESOLVED 3계열뿐이고
**`CLOSED` 를 모른다.** `lead()`(`:66-74`)는 `:**`·`—`·`.` 중 가장 앞에서 자르므로,
상태줄을 `❌ CLOSED …` 로 시작하면 UNKNOWN 이 되어 **게이트가 exit 1** 이다. 그래서 `✅ Resolved` 로 시작한다.

**재분류 결론:** BL-405 의 전제("Pine 비교는 na 를 반환하고 bool 시리즈에 na 가 보존된다")는 **TradingView 공식 문서로 반증됨** (r.jina.ai 리더로 verbatim 확보):

- type-system: _"values of the 'bool' type are never na. Any 'bool' return type returns `false` instead of na if data is not available."_ → **bool 은 절대 na 아님**.
- type-system: _"The ==, != operators, and all other comparison operators always return `false` if at least one of the operands is … `na`."_ → 비교는 na 피연산자에 **concrete false** (na 전파 아님). `!=` 도 false (True 아님 — 오라클이 놓친 지점).
- type-system: bool history-ref on nonexistent bar → false. operators: _"If at least one operand is na, the result is also na."_ → **na 전파는 산술에만**.

→ **현재 pine_v2 동작(비교→False, bool never na, crossover→False, 산술→na)이 TV 정답이다.** 계획됐던 "비교/not/crossover 를 na 전파로 바꾸는 수정"은 TV 정합을 깨는 **회귀**였다 (미실행). 오라클 ②의 "TV=bar 15"는 bool na 전파를 잘못 가정한 계산 — 실제 TV 는 bool 을 na 로 만들지 않아 엔진처럼 bar 12 를 낸다(ta.ema 워밍업 동일 가정 하).

**조치 (엔진 동작 무변경):** TV-정합 동작을 잠그는 회귀 테스트 13건 추가 (`tests/strategy/pine_v2/test_na_bool_tv_parity.py`) + `_eval_compare`(interpreter.py) / `ta_crossover|crossunder|cross`(stdlib.py) 오해 유발 주석 정정 + `report.md` §4.2 erratum. **bs bar12↔bar15 실측 편차의 진짜 후보는 bool-na 가 아니라 ta.ema 워밍업 시딩 → BL-409 로 분리 추적.**

**Risk:** — (해소, 코드 동작 변경 없음).

---

### BL-406

**Title:** DrFXGOD 잔여 미지원 builtin 5종 — ta.alma / ta.dmi / time() 호출형 / ticker.new / request.security_lower_tf
**Category:** Backend / pine_v2 coverage
**Priority:** P3
**Trigger:** 사용자 DrFXGOD 류 대형 indicator 수요 재확인 시
**Est:** M (ta.alma/ta.dmi 각 2-3h + time() stub 1h) / ticker.new·security_lower_tf 는 별도 설계 필요
**상태:** ⏳ 대기 (트리거 미도래) — ta.alma/ta.dmi 는 TA_FUNCTIONS 에 없고 coverage 가 여전히 미지원 안내만 한다 — time 은 식별자만, 호출형 stub 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-12 pine-batch QA (`docs/archive/qa/2026-07-12-pine-batch-1h4h/report.md` §2)

**원인 / 영향:** G2(array 15종) 이후 DrFXGOD_indicator_hard(=i3_drfx) 의 잔여 차단 표면. (a) `ta.alma`(Arnaud Legoux MA)·`ta.dmi`(DMI/ADX) 는 순수 지표 — stdlib 추가로 feasible. (b) `time("")` 호출형은 timestamp stub 확장으로 feasible. (c) `ticker.new` + `request.security_lower_tf` 는 멀티심볼·하위 TF 데이터 패러다임 — 단일 TF 백테스트 전제 밖(거부 유지가 정직). (a)+(b) 만 구현해도 DrFXGOD 는 (c) 로 여전히 차단 — **전체 지원 목표가 아니라 (a)(b) 의 범용 가치로 판단할 것**.

**권장 접근:** ta.alma/ta.dmi 를 `_names.TA_FUNCTIONS` + stdlib `_call` 에 추가 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서 대조 + 수계산 오라클). time() 은 bar timestamp 반환 stub. (c) 는 workaround 텍스트 유지.

**Risk:** 🟢 (신규 함수 추가 — 기존 경로 무변경).

---

### BL-408

**Title:** 리포트/위저드 Precision Instrument 폴리시 잔여물 팩 (stale aria-label 색명 + radius/글래스/레이블 어휘 6건)
**Category:** Frontend / 디자인 시스템 정합
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-402 처리와 묶음 권장 — 파일 겹침)
**Est:** S (2-3h — 전부 표시 전용)
**상태:** ⏳ 대기 (트리거 미도래) — 6건 중 1~5 (색명·radius·글래스·레이블·mono)는 v3 재작성으로 소멸했으나 6번 --destructive-light 중복 alias(=subtle 동일값, 사용처 6곳)와 영문 aria-label 다수가 남았다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-12 pine-batch QA 디자인 감사 (`docs/archive/qa/2026-07-12-pine-batch-1h4h/report.md` §6.1)

**원인 / 영향:** W6 잔여물 + 리디자인 이후 미세 드리프트 묶음. (1) `charts/chart-legend.tsx:51`·`charts/equity-pane.tsx:78` aria-label "실선 녹색" — 실제 equity 색은 코퍼, 스크린리더에 틀린 색 전달 (P2급, 팩 내 최우선. E2E getByLabelText 2건 동반 수정). (2) `report/key-stats-strip.tsx:83`·`report/performance-chart.tsx:42` 히어로 카드 `rounded-xl`(14px) — DESIGN.md §5 카드 규격은 10px. (3) `charts/chart-legend.tsx:44` `bg-card/80 backdrop-blur` 글래스 잔존 — v3 플랫+1px 보더 원칙 위반 (스코프 내 유일). (4) `components/metric-tile.tsx:60` 레이블 sans 10px — §0.1 mono 11px tracking 0.14em 규격과 분열. (5) `report/trade-ledger-table.tsx` 금액 셀 mono/tabular 혼용. (6) `--destructive-light` alias 잔존 + 영문 aria-label("strategy select" 등). DESIGN.md §11 표의 "백테스트 결과 = Light" 는 v2 스냅샷 잔재 — 문서 정리 동반.

**권장 접근:** 항목별 1-line 수정 (전부 표시/문서 전용, 로직 무변경). BL-402 SelectWithDisplayName 교체 PR 에 동승 가능.

**Risk:** 🟢 (표시 전용 — 시각 스냅샷 확인만).

---

### BL-409

**Title:** pine_v2 워밍업 TV-parity 잔여 2건 — (a) ta.ema 시딩 정합 (bs bar12↔bar15 실측 편차 진짜 후보) (b) bool[n] 범위밖 과거참조 nan vs TV false
**Category:** Backend / pine_v2 warmup parity
**Priority:** P3
**Trigger:** 다음 pine_v2 TV-parity 사이클 (BL-405 재분류 후속) — 특히 (a)는 실제 TradingView 그라운드트루스 확보 시
**Est:** M ((a) ta.ema 시딩 조사 2-4h — 단 확정엔 실제 TV 실행 대조 필요 / (b) XS, 관측 무영향이라 저순위)
**상태:** ⏳ 대기 (트리거 미도래) — 사용자 결정 대기: (a) ta.ema 시딩은 여전히 SMA seed 그대로라 실제 TV 관측 없이는 대조 불가(순환검증), (b)는 nan 반환 그대로지만 관측 무영향. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-12 A+B+C Trust 번들 — BL-405 재분류 과정에서 TV 문서 검증 + 회귀 테스트(`test_na_bool_tv_parity.py`)로 표면화

**원인 / 영향:**

- **(a) ta.ema 워밍업 시딩** — 엔진 `ta_ema`(stdlib.py:81-97)는 첫 `length-1` bar 를 nan 으로 두고 bar `length-1` 에서 SMA 로 시드. 실제 TradingView 의 ta.ema 워밍업 시작 bar/값이 다르면 emaSlow 가 다른 bar 에서 살아나 `bull != bull[1]` 첫 전환이 다른 bar 로 이동한다. **bs 4h 2024 의 엔진 bar 12 vs 오라클 주장 bar 15 편차의 진짜 후보** (bool-na 와 무관). 확정하려면 실제 TradingView 에서 bs 4h 2024 의 첫 시그널 bar + ta.ema(5)/ta.ema(13) 초기 시리즈를 관측해 엔진과 대조해야 함 (순수 pandas 오라클이 엔진과 같은 시딩을 가정하면 순환검증 — §7.3).
- **(b) bool[n] 범위밖 과거참조** — `_eval_subscript`(interpreter.py:882-884)가 범위밖 history 를 타입 무관 nan 반환. bool 변수의 `b[1]` 이 bar 0 에서 nan (TV 는 false). 소비(비교/제어흐름)에서 `_truthy`/비교가 nan→false 로 소거 → **거래·시그널 영향 0** (test_na_bool_tv_parity.py 가 관측 등가 잠금). raw 저장 값만 편차.

**권장 접근:** (a) 실제 TV ta.ema 초기 시리즈 캡처 → 엔진 시딩 규칙 대조/조정 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서/실행 대조 + 수계산 오라클). (b) 관측 등가라 저순위 — 정적 bool 타입 추론 도입 시 함께 (pine_v2 동적 타입이라 난이도 있음).

**Risk:** 🟢 ((a) 조사 우선; (b) 관측 무영향).

---

### BL-462

**Title:** 백테스트 목록 Sharpe 정렬이 신·구 컨벤션을 섞어 센다
**Category:** Backtest / API (정렬 정합)
**Priority:** P3
**Trigger:** 구 백테스트가 목록에 남아 있는 동안
**Est:** M (equity_curve 로딩 필요)
**상태:** ✅ Resolved (2026-08-11 gate-freshness) — 정렬 결함 자체는 ledger-truth(`1d4d7e0b`)의 `_sharpe_sort_criteria` 등급 정렬(= 권장 접근의 「분리」안)이 이미 닫았고, 이 회차는 낡은 상태줄·FE 고지를 실측으로 정정하고 잔여 주장 2건(재계산·NULL화)을 코드로 기각했다.
**트리거 판정:** 도래 — 로컬 DB 실측: COMPLETED 백테스트에 `sharpe_convention` 마커 없는 구 컨벤션 1건이 남아 있고 신 컨벤션도 `tv_daily_rfr2`(2)/`tv_monthly_rfr2`(1) 로 섞여 있다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 backtest-trust 스프린트 (codex G0 P1 지적 → 수용)

**원인 / 영향 (2026-08-11 정정 — 종전 서술은 낡았다):** ~~`backtest/repository.py:71-77` sort whitelist 가 `metrics->>'sharpe_ratio'` 를 Numeric 캐스팅해 **서버 정렬**하는데 convention 을 보지 않는다~~ → ledger-truth(`1d4d7e0b`, PR #593)가 `repository.py` `_sharpe_sort_criteria()`(현행 `:64-101`) 로 **(등급 ASC, 정규화값)** 정렬을 구현했다 — 등급 0=비교 가능(연율화 계수로 정규화) / 1=구 컨벤션(척도 미상) / 2=degenerate(`unavailable*`) / 3=값 없음. dev DB 실측(2026-08-11): 구 컨벤션 행(sharpe 1.2249, **원값 1위**)이 등급 1 로 **4위에 분리**되고 degenerate 3건이 맨 뒤다.

★★**잔여 주장 2건 기각 (2026-08-11 코드 대조).**

1. **「equity_curve read-time recompute」 기각** — 재계산의 근거(의미가 다른 값이 한 순위로 섞임)가 등급 분리로 소멸했다. `list_by_user` 의 `defer(equity_curve)` 는 유지되고, FE 는 구행 tooltip(「구 기준(봉 수익률 · 무위험 0%) - 현재 기준과 비교 불가」)로 분리 **표시**도 이미 한다.
2. **「`engine/metrics.py` 의 `Decimal("0")` 을 NULL 로」 기각** — 다른 세션이 잔여로 지목했으나 코드가 명시적으로 반박한다: `sharpe_ratio()` 독스트링(`metrics.py:111-116`)이 비-옵셔널 반환을 의도로 못 박았다. None 반환 시 `optimizer/engine/grid_search.py:249` 의 `metrics.sharpe_ratio is None` dead branch 가 부활해 degenerate 셀이 급증하고 FE `key-stats-strip.tsx` 가 깨진다. degenerate 는 「값 0 + convention 마커」로 구분하는 것이 현 설계의 계약이다.

**남은 조치였던 FE 고지도 같은 회차에 사실로 갱신** — 종전 문구 「…정렬 순위를 그대로 신뢰할 수 없습니다」는 등급 정렬 이후 **거짓**이라 「구 기준 샤프는 현재 기준과 비교할 수 없어 정렬 시 비교 가능한 결과 뒤로 분리됩니다」로 교체(`backtest-list.tsx`, 커밋 `9e288935`, vitest red→green).

**Risk:** 🟢 (구 컨벤션 행은 과거 백테스트 재실행 시 자연 소멸 — 그때까지 등급 1 로 분리 정렬·표시된다).

---

### BL-463

**Title:** optimizer / stress_test 저장 sharpe 에 컨벤션 마커 없음
**Category:** Optimizer / Stress test (metrics 정합)
**Priority:** P3
**Trigger:** 구 optimizer·stress 결과 재해석 필요 시
**Est:** M (2 도메인 JSONB 스키마 확장)
**상태:** ⏳ 대기 (트리거 미도래) — sharpe_convention 마커는 backtest 계열에만 존재하고 optimizer/stress_test JSONB 는 여전히 순수 sharpe 값만 저장한다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 backtest-trust 스프린트 (codex G0 P2 지적 → 스코프 밖 수용)

**원인 / 영향:** `optimizer/serializers.py:104` 와 `stress_test/serializers.py:80,159` 가 각자 독립 JSONB 에 sharpe 를 저장한다. 본 스프린트는 **backtest metrics 만** 마킹했으므로 두 도메인의 과거 결과는 구·신 구분 없이 남는다. 신규 실행은 새 수식이지만 저장값에 그 사실이 기록되지 않는다.

**권장 접근:** 두 도메인 result JSONB 에도 컨벤션 마커 추가 + FE 표기. 3 도메인 동시 마킹은 스코프 폭발이라 분리했다.

**Risk:** 🟢 (신규 실행은 일관 · 구 결과 비교 시에만 오해 가능).

---

### BL-504

**Title:** ~~ADR-013 / ADR-019 가 존재하지 않는데 진입 문서 4곳이 가리킨다~~ → **ADR-013 인용이 죽은 경로를 가리킨다 (019 는 실재)**
**Category:** Docs / decisions (참조 정합)
**Priority:** P3
**Trigger:** Optimizer 설계 근거를 다시 물을 때 (알고리즘 교체 · scikit-optimize 이탈 · GA 파라미터 변경)
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — 인용 4곳을 **git tombstone 경로**로 교정. 소급 ADR 작성은 [BL-658] 로 분리. 코드 0줄.
**출처:** 2026-07-27 `/claude-md-improver` CLAUDE.md 감사 → **2026-08-09 전제 2건이 반증돼 근거 교체**

★★**G0 반증 2건 (2026-08-09 실측).**

1. **「013 과 019 가 결번」은 절반이 거짓이다.** `docs/decisions/` 실측 = 001~012 · **014~027**.
   결번은 **013 하나뿐**이고 **`019-worker-auto-rebuild.md` 는 실재한다**(ADR-019 = BL-181 Docker worker
   auto-rebuild, Sprint 38). 원 항목이 지목한 「ADR-019 오기」의 실체는 **`docs/dev-log/INDEX.md:141`**
   (`2026-05-05 · ADR-019 Surface Trust Pillar`) 한 줄뿐이고, 이건 **결번이 아니라 ID 중복 호칭**이다.
2. **`AGENTS.md:67` 인용은 이미 사라졌다.** 2026-08-06 문서 대개편([ADR-026])에서 `AGENTS.md` 가
   오리엔테이션 전용으로 재작성되며 그 줄이 없어졌다. 현재 `grep -rn 'ADR-013' AGENTS.md` = **0건**.

★★★**그리고 진짜 뿌리는 「ADR 이 작성되지 않았다」가 아니었다 — 작성됐고, 나중에 삭제됐다.**
실체 = `docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md`(**24,703바이트**), 도입 커밋
`9c93fa70`(PR #258), **삭제 커밋 `94da86b1`**(2026-08-06 「delete archive/ and dev-log bodies」).
인용된 절이 **전부 그 문서 안에 실재한다** — `## 6. Sprint 55+ kickoff 의무 checklist`(§6 #8 = BL-235 deferred,
`:202`) · `### 7.2 보완 결정 (Sprint 55 lock)` · `### 8.2 보완 결정 (Sprint 56 lock)`.
⇒ **인용은 유효했고 경로만 죽었다.** 「검증할 수 없는 근거」라는 원 진술은 **거짓**이다.

**살아 있는 인용처 (2026-08-09 재측정 — 원 항목의 4곳과 다르다):**

| 위치                                                                               | 조치                                             |
| ---------------------------------------------------------------------------------- | ------------------------------------------------ |
| `CONTEXT.md:47`                                                                    | tombstone 경로 병기                              |
| `docs/reference/domain/state-machines.md:174`                                      | ★**원 항목이 놓친 인용처** — tombstone 경로 병기 |
| `docs/backlog.md:488`(BL-235 표) · `:611`(BL-235 출처) · `:1893`(BL-412 권장 접근) | tombstone 경로 병기                              |
| ~~`AGENTS.md:67`~~                                                                 | **이미 소멸**(08-06 대개편)                      |
| `docs/archive/product/…-original-prd.md:8`                                         | archive 는 과거 원문이라 손대지 않는다           |

**조치(2026-08-09):** 위 인용처에 **`git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md`**
를 병기했다. [ADR-026] 「과거 원문 = git history · 삭제 시 tombstone 1줄 의무」에 정확히 부합하는 처리이고,
**없는 문서를 지어내지 않는다**. 소급 `decisions/013-optimizer-strategy.md` 작성은 별건(M 급) ⇒ **[BL-658]**.

**Risk:** 🟢 (동작 무영향 · Optimizer 설계 변경 시에만 근거 부재가 드러난다).

---

### BL-505

**Title:** 청산 공유 lock 의 축이 포지션 정체성이 아니라 `sessionId + symbol` 이다
**Category:** Frontend / trading (코크핏 §03)
**Priority:** P3
**Trigger:** 같은 계정·심볼에 세션이 여러 개 생긴 뒤 두 표에서 연달아 청산을 누를 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — mutationKey 가 여전히 ["close-position", sessionId, symbol] 이고 두 표 테스트도 같은 sessionId 를 주입한다 — 포지션 정체성 축 전환 흔적 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-ops-hygiene codex 최종 적대 리뷰 (재현 판정 후 등재)

**원인 / 영향:** BL-502 의 `mutationKey` 는 `["close-position", sessionId, symbol]` 이다. 그런데 두 표가 같은 포지션에 대해 **서로 다른 `sessionId` 를 잡을 수 있다** — 계정 표는 그 계정·심볼의 **최신** 귀속 세션(비활성 포함, `position_service.py:283`)을 쓰고, 세션 표는 **활성** 세션별로 렌더한다. 최신 세션이 비활성이고 더 오래된 세션이 활성이면 두 키가 갈리고 lock 이 분리된다 → 같은 순 포지션에 감소전용 주문 2개가 나갈 수 있다(BL-502 가 없애려던 바로 그 상태).

★**추가된 테스트도 이 경로를 판별하지 못한다** — `close-position-lock.test.tsx` 가 두 표에 **같은** `SESSION_ID` 를 주입한다. 정렬된 경우만 덮는다.

**권장 접근:** lock 축을 세션이 아니라 **포지션 정체성**(계정 또는 uid + 심볼 + 방향)으로 바꾼다. 다만 `close_position` API 가 세션 id 를 받으므로 키와 요청 인자가 갈라진다 — 그 분리를 감당할지 결정이 필요하다. 손실이 아니라 **원장 잡음**(두 번째 주문은 평탄해진 포지션에서 거부)이라 우선순위는 낮다.

**영향 파일:** `frontend/src/features/live-sessions/hooks.ts`, `.../account-positions-table.tsx`, `.../open-positions-table.tsx`.

**Risk:** 🟢

---

### BL-507

**Title:** 계정 표의 접기·청산 가능성 판정이 view 컴포넌트 안에 있다
**Category:** Frontend / trading (레이어)
**Priority:** P3
**Trigger:** 접기 규칙이 한 번 더 바뀔 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — features 분리 미실시. 단 :56 은 이미 모듈 레벨이라 분리는 성능을 안 바꾼다 — 실비용은 :248-301 조립·호출이 useMemo 밖인 것 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-ops-hygiene codex 최종 적대 리뷰

**원인 / 영향:** `collapseRows`(`account-positions-table.tsx`)가 권한(`readOnly`)·귀속 세션·차단 사유를 해석해 대표 행과 청산 가능성을 결정한다. `frontend/AGENTS.md` 의 view ↔ 비즈니스 로직 분리 원칙 위반이다.

★**이번 스프린트의 P1 이 정확히 이 경계에서 나왔다** — hedge 의 두 leg 를 한 행으로 지운 것이 이 함수였다. 규칙 위반이 실제 결함으로 이어진 사례이므로 nit 로만 두지 않는다.

**권장 접근:** 접기·대표 선택을 순수 함수로 분리해 단독 테스트 가능하게 하거나, 서버가 접힌 형태를 계산해 내려준다. 후자는 uid 가 계정 목록 계약에 이미 있으므로 가능하지만 **응답 계약 변경**이라 결정이 필요하다.

**Risk:** 🟢

---

### BL-509

**Title:** multiprocess mmap 파일이 무한히 쌓이고, 그 누수가 `qb_active_orders` 의 정확성을 떠받치고 있다
**Category:** Infra / observability
**Priority:** P3
**Trigger:** 스크레이프 지연이 눈에 띌 때, 또는 장기 무중단 가동 시
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — role별 dead-pid 접기 janitor(merge accumulate=False)가 코드·테스트 어디에도 없고, 있는 것은 콜드 스타트 wipe 뿐이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증(프로세스 경계 렌즈)

**원인 / 영향:** `mark_process_dead` 는 `gauge_live*` 파일만 지운다. `counter_`/`histogram_`/`gauge_sum_`/`gauge_mostrecent_` 는 **아무도 지우지 않는다**. `worker_max_tasks_per_child=250` 자식 교체마다 +4 파일, `uvicorn --reload`/watchfiles 재기동도 각각 새 식별자다. 수집기는 매 스크레이프마다 전 파일을 re-mmap + 키마다 `json.loads` 하므로 비용이 **O(F×K)** 다.

★**soak 실측 — 아직 문제로 관측되지는 않았다.** 약 1시간 창에서 파일 50 → 54(자식 1회 재활용), `scrape_seconds` 는 **24샘플 전부 0.01 고정**. 즉 이 태스크 부하에서는 열화가 나타나지 않았다. 원리상 실재하되 **긴급하지 않다.**

★★**함정: 순진하게 고치면 BL-508 이 즉시 깨진다.** 죽은 자식의 **음수 delta 파일이 남아 있어야** `sum` gauge 산술이 맞는다. 회수 janitor 를 만들 때 `multiprocess.merge(files, accumulate=False)` 로 role 별 집계 파일에 **접고** 삭제하는 형태여야 한다.

**권장 접근:** 콜드 스타트 wipe(현행) 유지 + role 별 dead-pid 접기 janitor. 런타임 중 counter 파일 pruning 은 **가짜 counter reset** 이므로 금지.
**Risk:** 🟢

---

### BL-513

**Title:** 성공은 안 보이고 실패만 보인다 — 완전체결 카운터 부재 · janitor 실적 미노출 · planner divergence 5종 무계측
**Category:** Backend / observability (trading)
**Priority:** P3
**Trigger:** 운영 대시보드를 만들 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 3종 처방 중 divergence 계측만 구현(BL-536), janitor 실적·완전체결 카운터는 여전히 부재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증(거래소 실상 렌즈)

**원인 / 영향:**

- **완전체결을 세는 카운터가 코드베이스에 없다.** `qb_partial_fill_total{source}` 는 **부분체결 전용**이다. 체결 시 일어나는 건 `qb_active_orders.dec()` 뿐이라 "몇 건 체결됐나" 를 물을 수 없다.
- **janitor 실적이 Prometheus 에 없다.** `conditional_entry_janitor.py:168` 이 `{repaired, rejected, terminal}` 를 **return 만** 한다. 오류 stage(`janitor_race`/`janitor_probe`)만 계측된다. soak 실측에서 janitor 는 5분마다 정상 발화하며 전부 0 을 반환했는데, **그 사실이 Celery 결과 로그에만 있다.**
- **planner divergence 5종 전량 무계측** — `conditional_entry_planner.py:172/195/216/240/255` → 소비처는 `live_signal.py:499-503` `logger.warning` 뿐. 특히 `below_exchange_minimum` 은 "전략이 영원히 한 주도 못 낸다" 는 뜻인데 무계측이다.

**권장 접근:** `qb_order_filled_total{source}`, `qb_conditional_janitor_actions_total{action}`, `qb_conditional_plan_divergence_total{reason}` 신설.
**Risk:** 🟢

---

### BL-514

**Title:** stand-down 이 발화한 것은 알 수 있어도 **왜** 발화했는지는 알 수 없다
**Category:** Backend / observability (trading)
**Priority:** P3
**Trigger:** stand-down 이 실제로 발화해 조치가 필요할 때
**Est:** XS
**상태:** ✅ Resolved — stand_down 사유가 qb_live_conditional_divergence_total{event,reason} 과 렌더되는 로그 extra 로 둘 다 노출된다(BL-561 포맷터). (2026-08-09 status-triage-mass 코드 대조)
**출처:** 2026-07-28 live-observability — **유도 실험 중 직접 관측**

**원인 / 영향:** stand-down 사유는 `hedge_mode` 와 `shared_account_symbol` 둘인데 조치가 완전히 다르다(계정 설정 문제 vs 운영 실수). 그런데 셋 다 사유를 안 준다.

- `qb_live_conditional_reconcile_errors_total{stage="positions"}` — **라벨에 사유 없음**(두 경우가 같은 시리즈).
- `logger.error("live_conditional_reconcile_divergence", extra={"reason": ...})` — ★**포맷터가 `extra` 를 렌더하지 않는다.** 실측: 발화 3건 전부 `live_conditional_reconcile_divergence` **한 줄로만** 출력됐다.
- `qb_live_conditional_cancelled_total{reason=...}` 만 사유를 담는데 **취소할 대상이 있을 때만** 오른다.
  → **취소 대상이 없는 stand-down 은 사유를 알 방법이 전혀 없다.**

**권장 접근:** `{stage="positions"}` 를 `{stage="positions", reason=...}` 로 분리하거나 `stage` 값을 `positions_hedge`/`positions_shared` 로 가른다. 로그는 `extra` 대신 메시지에 사유를 넣는다.
**Risk:** 🟢

---

### BL-515

**Title:** 정상 교체 사이클이 이상 판별을 삼킨다 + 경보 규칙이 2개뿐이라 카운터가 올라도 아무도 안 본다
**Category:** Infra / observability
**Priority:** P3
**Trigger:** metric 기반 운영 경보 도입 시
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — alerts.yml 은 여전히 alert 2개뿐이고 placed−cancelled recording rule 은 레포 어디에도 없다(record: 0건). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증

**원인 / 영향:** PbR 같은 전략은 매 bar 피벗이 움직여 `conditional_entry_planner.py:285-289` 가 항상 불일치 → **매 tick** `cancelled_total{reason="replaced"}` +1 · `placed_total` +1 이 정상이다. 병리(거절 루프)도 **같은 패턴**이라 두 카운터로는 구분할 수 없다. 유일한 신호는 `placed − cancelled` 의 발산인데 recording rule 이 없다.

그리고 `backend/prometheus/alerts.yml` 에 rule 이 **2개뿐**(`QbPendingAlertsHigh`, `QbRedisLockPoolUnhealthy`). 이번 세션이 관측 가능하게 만든 어떤 카운터도 경보에 연결돼 있지 않다.

★**단, BL-506 이전에는 이 논의 자체가 불가능했다** — 그 카운터들이 스크레이프되지 않았기 때문이다.

**권장 접근:** `placed − cancelled` recording rule + 이번 세션 판정표의 "관측됨" 계열에 대한 경보 규칙.
**Risk:** 🟢

---

### BL-518

**Title:** multiprocess 모드의 관측 계약 변화 — `_created` 전면 소실 · 프로덕션 경로 미테스트 · 값 범위 변화
**Category:** Infra / observability
**Priority:** P3
**Trigger:** `/metrics` 소비자(대시보드·경보)를 만들 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 4건 중 1건만 BL-448 로 소멸했고, 관측 계약 문서화도 multiproc /metrics HTTP 테스트도 레포에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability 적대 검증(관측 계약 렌즈) + 실측

**원인 / 영향:**

- ★**`_created` 시리즈 전면 소실.** 실측 — 미배선 API **30줄** → 배선 API **0줄**. `prometheus_client` 의 `_created` 는 `ValueClass` 를 거치지 않는 순수 float 이라 mmap 에 실리지 않는다. `rate()` 는 무영향이나 `_created` 기반 쿼리는 깨진다. **multiprocess 모드의 내재적 성질**이지 우리 버그가 아니다.
- **프로덕션 경로가 테스트되지 않는다.** 테스트 env 에 `PROMETHEUS_MULTIPROC_DIR` 이 없어 전 스위트가 폴백을 탄다. **`/metrics` HTTP 를 multiproc 모드로 때리는 테스트가 0건**이다(신규 테스트도 `render_metrics()` 단위까지).
- ~~**`qb_ws_orphan_buffer_size` 값 범위 변화.** docstring 은 "capped at 1000" 인데 `concurrency=3` + `livesum` 이라 0~3000. 기존 임계 재조정 필요.~~ → **2026-08-09 무효 — 그 gauge 는 [BL-448](#bl-448) 에서 삭제됐다**(버퍼째 제거). 이 항목이 재던 「livesum × concurrency 로 범위가 배수가 된다」는 성질 자체는 남은 `livesum` gauge(`qb_pending_alerts`)에 그대로 유효하다.
- **`qb_redis_lock_pool_healthy` 가 fail-open.** `mostrecent` 는 죽은 프로세스가 남긴 `1` 을 계속 서빙한다 — 건강한 프로세스가 없어도 healthy=1. `livemostrecent`/`min` 이 후보이나 각각 다른 실패 모드가 있다.

**권장 접근:** 위 4건을 `docs/reference/` 관측 계약 문서에 명시 + multiproc 모드 endpoint 테스트 추가.
**Risk:** 🟢

---

### BL-521

**Title:** `qb_live_signal_outbox_pending_gauge` 를 두 곳이 서로 다른 상한으로 덮어써 경보 신호가 잘린다
**Category:** Backend / observability
**Priority:** P3
**Trigger:** outbox 적체 경보를 붙일 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — limit=10_000 과 limit=50 두 .set() 이 그대로 공존하고 gauge 에 라벨도 없다 — 처방 미적용. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-observability G1 codex 적대 검증, 코드 재현 완료

**원인 / 영향:** `live_signal.py:813` 은 `list_pending(limit=10_000)` 결과를 `.set()` 하고, `:1475` 는 `list_pending(limit=50)` 결과를 같은 gauge 에 `.set()` 한다. **마지막 writer 가 이긴다.** 실제 pending 이 50 을 넘으면 recovery task 가 **50 으로 덮어써** 적체 신호가 조용히 잘린다.

★**단일 프로세스에서도 이미 그런 선재 결함**이다 — BL-506 이 만든 것이 아니다.

**권장 접근:** recovery task 의 `.set()` 을 제거하거나(문서상 계약은 "last eval cycle"), 두 소스를 라벨로 가른다.
**Risk:** 🟢

## Beta 오픈 번들 — 단일 milestone

> **deferred** — Beta 본격 진입 trigger (BL-005 self-assessment ≥ 7/10 + 본인 의지 second gate) 도래 시 main 으로 row 이동.
>
> 상세 sub-task (BL-070~075) + TODO.md L748~801 보존.

---

## Cross-reference

### ADR ↔ Backlog

| ADR                                                                                        | 미해소 BL                                           |
| ------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| [ADR-005](decisions/005-datetime-tz-aware.md) DateTime tz-aware                            | (Sprint 5 backfill 완료, 잔여 없음)                 |
| [ADR-011](decisions/011-pine-execution-strategy-v4.md) Pine Execution v4                   | (Path γ/δ archived — BL-040/041)                    |
| [ADR-020](decisions/020-trust-layer-ci-design.md) Trust Layer CI (구 ADR-013)              | BL-026 (skip 활성화 회귀), BL-023 (KIND-B/C 정밀도) |
| [ADR-016](decisions/016-sprint-y1-coverage-analyzer.md) Coverage Analyzer                  | (BL-037 archived)                                   |
| [ADR-018](decisions/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) WS Supervisor | BL-014 (partial fill), BL-015 (OKX WS)              |

### Lessons ↔ Backlog

| LESSON                                                     | 미해소 BL                                 |
| ---------------------------------------------------------- | ----------------------------------------- |
| LESSON-019 (commit-spy 회귀 의무화)                        | (BL-010 archived, 4 도메인 backfill 완료) |
| LESSON-007/008/009 (autonomous-parallel-sprints BUG-1/2/3) | BL-025 (스킬 patch)                       |

### Test Skip 추적표 ↔ Backlog

[2026-04-30 당시 `docs/TODO.md`의 Test Skip / xfail 추적표](https://github.com/woosung-dev/quantbridge/blob/b2c1541054326b06acf5e64f25094b6d5a37ea10/docs/TODO.md#L11-L31)의 dette 2 건이 백로그로 이관:

| Skip #                | 위치                                                 | BL ID                |
| --------------------- | ---------------------------------------------------- | -------------------- |
| #1                    | `tests/backtest/engine/test_golden_backtest.py:19`   | BL-022               |
| #16                   | `tests/strategy/pine_v2/test_mutation_oracle.py:213` | BL-023               |
| #4-7, #9-15 (12 skip) | `tests/strategy/pine_v2/test_*.py`                   | BL-026 (활성화 회귀) |

---

### BL-410

**Title:** FE vercel-react-best-practices 감사 low 잔여 팩 (확정 8건 — 배럴 2 + localStorage 스키마 2 + js 최적화 3 + fitContent 설계 1)
**Category:** Frontend / 성능·컨벤션
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-408 과 묶음 가능)
**Est:** S (2-4h — 전부 국소)
**상태:** ⏳ 대기 (트리거 미도래) — 8건 중 draft.ts version 스키마 1건만 구현, 배럴 2·webhook version·js 최적화 3·fitContent 설계 모두 코드에 그대로 남아 있다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-408=ACTIVE (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-13 vercel 70룰 멀티에이전트 감사 (파인더 6 + 반박형 검증, 원시 24 → 확정 18 중 high/medium 10건은 stage/fe-react-audit PR #433 에서 해소 — 본 팩은 low 8건)

**원인 / 영향:** (1) `components/ui/form.tsx:6` + `features/trading/index.ts:3` 배럴 import. (2) `features/strategy/webhook-secret-storage.ts:53` + `draft.ts:89` localStorage 버전 스키마 부재. (3) `features/backtest/utils.ts:218` 함수 결과 캐시 부재 + `equity-chart-v2.tsx:184` / `trade-stats-strip.tsx:113` filter/map 다중 순회. (4) `components/charts/trading-chart.tsx:300` data effect 의 `fitContent()` 가 매 sync 마다 실행되는 설계 — 근본 수정(최초 1회 제한)은 전 호출처 동작 변경이라 별도 검토 (PR #433 은 호출측 identity 안정화로 해소).

**권장 접근:** 항목별 1-line~소형 수정. (4)는 lightweight-charts v5 업그레이드 (BL-395) 와 함께 재검토.

**Risk:** 🟢.

---

### BL-412

**Title:** optimizer result read-side 판별 유니온 (C-full) — `OptimizationRunResponse.result: dict[str,Any]` 를 FE 동형 `OptimizationResultOut` 으로
**Category:** Optimizer / Arch (read-side 타입화)
**Priority:** P3
**Trigger:** optimizer 폼/리포트 다음 기능 사이클 (BL-235/236/364 중 아무거나 착수 시 동승 검토)
**Est:** M (+80~120 LOC, FE 동형 유지 의무)
**상태:** ⏳ 대기 (트리거 미도래) — read 응답은 여전히 result: dict[str,Any] 이고 \_to_response 가 raw jsonb 를 그대로 흘린다 — OptimizationResultOut 유니온 자체가 레포에 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 선행 BL-235=ACTIVE (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-13 optimizer deepen 감사 후보 C-full (C-min 은 동일 세션 해소 — get/list 손상 row 방어 대칭화, PR feat/optimizer-cmin-n2)

**원인 / 영향:** BE 는 typed 역직렬화 역량(`*_from_jsonb`)을 갖고도 read 응답을 untyped dict 로 흘려 FE zod 가 유일한 검증층. writer 변경 시 drift 를 BE 테스트가 못 잡음 (BL-388/392 harm-class).

**권장 접근:** ADR-013 §7.2/§8.2 result grammar (실체 = `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` — [BL-504]) 를 정확히 mirror 하는 `OptimizationResultOut` 판별 유니온 추가 — 반드시 C-min 의 저하 경로(retro-incorrect row 404) 위에서 soft-validate. FE `schemas.ts` 와 필드 1:1 대조 테스트 동반.

**Risk:** 🟡 (구 row 실패율 상승 가능 — C-min 선행 완료로 완화됨).

---

### BL-413

**Title:** 주문 상세 조회 배선 — BE `GET /orders/{id}` 기존재하나 프로토타입 screen-11 에 상세 affordance(행 확장/드로어) 부재로 defer
**Category:** Frontend / orders
**Priority:** P3
**Trigger:** 주문 상세 화면/드로어가 디자인 캐논(프로토타입)에 추가될 때
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — FE 에 getOrder 배선도 상세 드로어도 없고 프로토타입 screen-11 에도 상세 affordance 가 없어 Trigger 자체가 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-23 functional-parity 스프린트 defer 판정

**원인 / 영향:** 원장 행이 이미 전 필드(오류 메시지 전문 포함)를 인쇄해 실해는 낮음. 디자인 근거 없는 UI 신설은 캐논 위반이라 배선만 보류.

**권장 접근:** 프로토타입에 상세 affordance 가 생기면 `GET /orders/{id}` (broker 원문/체결 상세) 배선.

---

### BL-414

**Title:** 스트레스 테스트 이력 리스트 UI — `GET /stress-tests` 목록 API 기존재하나 프로토타입 17벌에 이력 화면 부재로 defer (A7-lite 로 최신 1건 복원만 해소)
**Category:** Frontend / backtest 리포트
**Priority:** P3
**Trigger:** 스트레스 이력 화면이 디자인 캐논에 추가될 때
**Est:** S-M (3-5h)
**상태:** ⏳ 대기 (트리거 미도래) — byBacktest 캐시는 여전히 useLatestStressTest 의 단일 Summary 이고 이력 리스트 화면·페이지 응답 재정의 모두 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-23 functional-parity 스프린트 defer 판정

**원인 / 영향:** 리로드 소실(기능 격차의 본질)은 A7-lite 가 해소. 과거 실행 브라우징만 미지원.

**권장 접근:** 이력 리스트 도입 시 `stressTestKeys.byBacktest` 캐시를 단일 Summary 에서 페이지 응답으로 재정의해야 함 (A7-lite 구현 노트).

---

### BL-415

**Title:** `.field-error` FieldError 컴포넌트 3사본 → 공용 컴포넌트 승격 + zod-v4-resolver 평탄 키의 per-field 재검증 stale 가능성
**Category:** Frontend / 폼 프리미티브
**Priority:** P3
**Trigger:** 다음 폼 터치 사이클 또는 4번째 사본 등장 시
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — 공용 FieldError 승격 미실시(optimizer 로컬 정의 + raw .field-error 사본 다수), resolver 는 여전히 path.join(".") 평탄 키이고 재검증 테스트도 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-23 BL-401 적대 평가 사소 지적 (waitlist/optimizer 2곳+@ 사본)

**원인 / 영향:** waitlist·optimizer 가 동일 FieldError 를 로컬 복제. 또 커스텀 resolver 가 평탄 키(`parameters.0.max`)로 에러를 만들면 RHF per-field 재검증(dotted-path unset)이 못 지워 제출 재시도까지 stale 에러가 남을 수 있음 (중첩 경로 폼 첫 소비 사례).

**권장 접근:** `components/` 공용 FieldError 승격 + resolver 평탄/중첩 키 정책 1개로 통일 + stale 재검증 재현 테스트.

---

### BL-420

**Title:** WS 인바운드 서버 하드닝 팩 — 비인증 소켓 글로벌 상한/rate-limit + auth→realtime 역참조 정리
**Category:** Backend / realtime 보안·아키텍처
**Priority:** P3
**Trigger:** Beta 공개 배포 전 또는 realtime 다음 터치 시
**Est:** S (2-4h)
**상태:** ⏳ 대기 (트리거 미도래) — pre-auth 글로벌 상한·rate-limit 코드가 전무하고 auth→realtime 역참조도 dependencies.py:13 에 그대로 남아 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 tc-realtime-be 적대 평가 잔여 리스크 2건

**원인 / 영향:** accept 후 5s auth 창을 쥔 미인증 소켓의 동시 수 상한이 없음(per-user 상한은 인증 후에만 작동, Origin 은 비브라우저가 위조 가능 — 인증 자체는 별도라 보안 붕괴는 아님). 또 `src/auth/dependencies.py` 가 feature 도메인 `src.realtime.auth` 를 import 하는 방향 역전.

**권장 접근:** pre-auth 소켓 글로벌 상한/접속 rate-limit + helper 를 `src/auth/` 로 이동하고 realtime 이 역참조. (부수: position 서비스의 spot 방어 분기 dead code — `market_type` 키는 실경로 저장 불가 — 함께 정리.)

---

### BL-424

**Title:** 대시보드 실현손익 카드 foot — 미실현(추정) 부기와 기존 문구가 시각적으로 밀착 (폭 부족)
**Category:** Frontend / dashboard 시각
**Priority:** P3
**Trigger:** 대시보드 polish 시
**Est:** XS (<1h)
**출처:** 2026-07-24 opspack-ws2 D8b dogfood 스크린샷 (docs/archive/sprints/opspack-ws2/context-notes.md #18)
**상태:** ✅ **Resolved (2026-08-09, W3)** — **재현됐다.** 단 원인은 「폭 부족」이 아니라
`.kpi-foot` 의 `display:flex` 였다. 아래 §재판정 참조.

**원인 / 영향:** foot 문장 줄바꿈 + 부기 병치로 간격이 타이트. 판독은 가능하나 밀도 과다.

**권장 접근:** 부기를 별도 행/뱃지로 분리하거나 foot 문구 축약.

**§재판정 (2026-08-09, W3)**

★**대상 파일이 BL 표기와 달랐다.** 「실현손익 카드」가 아니라
`dashboard/_components/dashboard-cockpit.tsx` 의 KPI foot 이다
(`workspace-equity-card.tsx` 에는 `미실현` 문자열이 없다).

★**재현 결과 — 밀착은 실재했고, 원인은 폭이 아니었다.** `globals.css:1381-1390` 의
`.kpi-foot` 이 `display: flex; align-items: center; gap: 6px` 다. 그 안에 여러 줄 산문을
**직접** 넣으면 텍스트 노드마다 **익명 flex item** 이 생겨 좌우로 흩어지고 `<br />` 이
줄바꿈으로 작동하지 않는다. 375px 실측 스크린샷에서 「건의 실현 손익 합입니다.」와
「미실현(추정) 0.00」이 본문 오른쪽에 세로로 뭉쳐 있었다 — BL 이 「밀착」이라 적은 그 모양이다.
줄 상자 top 간격 실측 = 수리 전 **[8, 2, 10]px**(줄 조각 4개, line-height 19.46px 에 한참 못
미친다) → 수리 후 **[2, 20]px**(진짜 줄바꿈 1회가 line-height 와 일치).

★**처방은 「부기 분리」가 아니라 「flex item 을 하나로」다.** 내용을 `<span>` 하나로 싸면
그 안은 보통의 인라인 흐름이라 `<br />` 이 되살아난다. `.kpi-foot` 규칙 자체는 **못 고친다** —
KITPORT 센티넬 안이라 무결성 가드가 막는다([BL-645] 에서 같은 벽을 실측했다).

변이 M = 그 `<span>` 을 지우면 구조 래칫이 빨개지고 줄 간격이 **[8, 2, 10] 으로 복귀**한다.
음성 대조 N = `dashboard-cockpit.test.tsx` 의 `미실현(추정) -3.20` 단언과 「KPI 라벨로
미실현을 노출하지 않는다」계약이 **둘 다 불변**. vitest 209파일 / **1302**테스트 green.

★**다른 `.kpi-foot` 소비자는 안 건드렸다** — 한 줄짜리 foot 은 flex 로도 정상이다.

---

### BL-426

**Title:** ws_stream 워커 용량 정책 — 멀티계정 시 public ticker starvation 가능 + 스트림 태스크 루프 직접 유닛 부재
**Category:** Backend / trading websocket 인프라
**Priority:** P3
**Trigger:** 거래소 계정 2개 이상 등록 시 (현 로컬 1계정 무해)
**Est:** S-M (2-6h)
**상태:** ⏳ 대기 (트리거 미도래) — public ticker 가 여전히 private 과 같은 ws_stream 큐(concurrency=3 고정) — 분리·계정수 산정·starvation 회귀 테스트 전무. lease 갱신 유닛만 존재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 opspack-ws2 codex G0 + WA 적대평가 P3 관찰

**원인 / 영향:** reconcile 이 활성 계정마다 장기 private stream 을 enqueue 하는데 계정 수 상한이 없어, 계정 N+1 > concurrency(3) 이면 public ticker 태스크가 큐에서 기아. 또한 60s refresh/lease-lost 루프는 코드 정독+프로브로만 검증(직접 단위 테스트 없음).

**권장 접근:** singleton public ticker 를 별도 큐·concurrency 1 워커로 분리하거나 계정 수 기반 concurrency 산정 + starvation 회귀 테스트. refresh 루프 유닛 동반.

---

### BL-427

**Title:** 전략 목록 파라미터 열 / 수명주기 칩(초안·검증·배포) 미렌더 — 백엔드 스키마 부재
**Category:** Frontend / backend schema
**Priority:** P3
**Trigger:** 전략 파라미터/수명주기 UI 요구 시
**Est:** M (4-8h, BE 스키마 + FE)
**상태:** ⏳ 대기 (트리거 미도래) — StrategyListItem 에 파라미터 요약·lifecycle 필드가 여전히 없고 FE 주석도 미렌더 사유를 그대로 유지 중이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 perf-surface (캐논 프로토타입엔 존재하나 StrategyListItem 스키마에 파라미터·lifecycle 필드 없음 → §4.9 미렌더 유지)

**원인 / 영향:** 캐논 screen 은 전략별 파라미터 요약 + 수명주기 칩을 그리나, `StrategyListItem` 에 해당 필드가 없어 perf-surface 는 성과 3칸만 노출하고 파라미터/칩은 의도적으로 미렌더. 데이터 모델 확장 전까지 표면 불가.

**권장 접근:** Strategy 파라미터 요약 + lifecycle 상태를 list 응답에 파생/영속 후 FE 칩 렌더. 스키마 우선.

---

### BL-428

**Title:** 트레이드 구간 미니차트 share 페이지 미지원
**Category:** Frontend
**Priority:** P3
**Trigger:** 공개 share 리포트에 구간 차트 요구 시
**Est:** M (owner-authed OHLCV 엔드포인트를 token 기반 공개 경로로 확장)
**상태:** ⏳ 대기 (트리거 미도래) — owner-authed /trades/{i}/ohlcv 그대로이고 token 공개 OHLCV 경로도, share 페이지 trade 표도 없다 — 처방 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 perf-surface A4 (TradeDetailTable 은 owner-authed `/trades/{i}/ohlcv` 사용 → share 페이지는 미렌더가 정직. 현재 share 는 trade 표 자체가 없음)

**원인 / 영향:** 미니차트 fetch 는 owner-authed 엔드포인트라 share(token) 컨텍스트에서 401. 현재 share 페이지는 Stat 카드+EquitySparkline 만 있고 trade 표가 없어 무해하나, 향후 share 에 trade 상세 도입 시 차트 공백.

**권장 접근:** token 기반 공개 OHLCV 조회 경로(민감도 낮음 — 과거 시세) 또는 share 렌더 시 차트 명시적 비활성 + 안내.

---

### BL-429

**Title:** 대시보드 §03 최적화 완료행 수익률/MDD 역산 미표시(`—` 고정)
**Category:** Frontend / backend
**Priority:** P3
**Trigger:** 대시보드에서 최적화 best 성과를 목록 단계에서 보고 싶을 때
**Est:** S-M (best_params 대응 backtest metric 역산 또는 denormalize)
**상태:** ⏳ 대기 (트리거 미도래) — §03 최적화 행의 수익률/MDD 칸이 여전히 EMPTY_CELL + "결과는 최적화 상세에서 확인" 고정이라 역산·objective 표기 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 perf-surface A3 (§03 병합에서 최적화 행은 수익률/MDD 를 `—`+"결과는 최적화 상세에서 확인" 으로 고정. best 지표 역산은 후속)

**원인 / 영향:** OptimizationRun 은 param_space/result(iterations) 만 보유, best 조합의 백테스트 metric 은 목록에 없어 §03 최적화 행 성과 칸이 빈칸. 정직하나 정보 밀도 낮음.

**권장 접근:** result 의 best_params → 대응 backtest metric 매핑을 denormalize 하거나 best objective_value 만이라도 표기.

---

### BL-430

**Title:** 전략 목록 성과 정렬(수익률/샤프) SORT_OPTIONS 미제공
**Category:** Frontend
**Priority:** P3
**Trigger:** 전략을 최근 성과 순으로 정렬하고 싶을 때
**Est:** S (2-3h; BE latest_backtest 정렬 축 + FE SORT_OPTIONS 확장)
**상태:** ⏳ 대기 (트리거 미도래) — SORT_OPTIONS 는 여전히 recent/name 둘뿐이고 정렬은 클라 로컬, BE strategy 목록에 성과 정렬 축(sort 파라미터) 자체가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-24 perf-surface A2 stretch 미실행 (SORT_OPTIONS 는 recent/name 만; 성과 3칸은 표기만, 정렬 축 부재)

**원인 / 영향:** 성과 열은 노출됐으나 전략 목록은 마지막수정/이름 정렬만 지원. latest_backtest 성과 기준 정렬 부재로 우열 비교가 목록 단계에서 제한적.

**권장 접근:** `latest_completed_by_strategy_ids` 결과를 정렬 축으로 노출(서버 정렬) + FE SORT_OPTIONS 에 수익률/샤프 추가. 클라 정렬은 페이지 한정이라 지양.

---

### BL-434

**상태:** 🟡 **부분 Resolved (2026-07-25 close-completeness)** — 완전 TP/SL **보고(display)** 는 착지, **청산 스윕은 [BL-437] 이연**(codex G0 2 BLOCKING). 근거: 본 섹션 `**⚠️ Partially Resolved …**` 리드인 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:23`, "BL-434 부분 Resolved(display) + 신규 BL-437(스윕 이연)").
**트리거 판정:** 미도래 — 선행 [BL-437] 이 **DEFERRED**(2026-08-11 실측)이고, 남은 청산 스윕이 그쪽 몫이다. Trigger 의 앞절(코크핏 §03 표시)은 display 축이 이미 착지해 소멸했다 (2026-08-11 bl-703-partial-verdicts)

**⚠️ Partially Resolved (2026-07-25 close-completeness)** — **완전 TP/SL 보고(display) 완료**: `fetch_open_conditional_orders`(2콜 union + orderId dedupe + stopOrderType 엄격분류) → position_service 조인(source-dedup·마크근접순) → §03 병합 표시(익절/손절 리스트) + has_trailing_stop 각주. dogfood 3계통(오라클 raw ↔ 앱 provider ↔ get_reconciliation 익절 66000/손절 62000). **청산 스윕은 BL-437 이연**(codex G0 2 BLOCKING: 타이밍 accept≠fill + account+symbol 공유 세션 오취소). dogfood 실측 = Partial 조건부 TP/SL 은 Bybit flat 시 자동취소(스윕 이연 안전).

**Title:** 완전 TP/SL 보고 — 포지션-부착 외 조건부(Partial-mode limit-TP) 주문 미표시 + 청산 시 미스윕
**Category:** Backend / Frontend / trading
**Priority:** P3
**Trigger:** 코크핏 §03 이 걸어둔 모든 TP/SL 을 보여줘야 하거나, 청산 후 잔여 조건부 주문 정리가 필요할 때
**Est:** M (fetch_open_orders 조인 + 스키마 확장 + 청산 스윕)
**출처:** 2026-07-24 trading-surface-pack (BL-431 은 포지션 필드만 read — Partial-mode limit-TP 는 별도 conditional order 라 미표시, 각주로 정직)

**원인 / 영향:** ccxt `fetch_positions` 의 position 필드는 Full-mode SL + set-trading-stop 트레일링만 담는다. QB 가 tpslMode=Partial 로 부착한 limit-TP 는 별도 조건부 주문이라 §03 에 안 나온다(각주로 고지). 또 reduce-only 청산은 포지션만 flatten 하고 잔여 조건부 주문은 스윕하지 않는다(포지션-부착 TP/SL 은 Bybit 이 flat 시 자동취소).

**권장 접근:** `fetch_open_orders`(conditional) 조인으로 완전 TP/SL 표시 + 청산 시 열린 reduce-only 조건부 주문 취소.

---

### BL-437

**Title:** 청산 스윕 — 청산 후 잔여 reduce-only 조건부 주문 자동취소 (post-fill + 세션 귀속)
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 수동 청산 후 잔여 조건부 주문(standalone SL/Trail 등 flat 시 자동취소되지 않는 것)이 dangling 으로 남아 재진입 시 오발화하는 실사례가 확인될 때
**Est:** M (post-fill flat 확인 mechanism + orderLinkId→세션 매핑)
**상태:** ⏳ 대기 (트리거 미도래) — 청산 후 잔여 조건부 주문 스윕 코드가 close_service 어디에도 없다; 계정 배타성만 갖춰졌고 post-fill flat 확인·세션 귀속 취소는 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 close-completeness (BL-434 분리 — codex G0 이 스윕에서 2 BLOCKING 발견해 이연)

**원인 / 영향:** BL-434 의 완전 보고(display)는 완료. 청산 스윕(잔여 reduce-only 조건부 주문 취소)은 codex G0 이 2 BLOCKING 을 드러내 이연: (1) **타이밍** — `execute()` 성공 = 주문 accept(async)이지 fill 이 아님. 발주 직후 스윕하면 시장가 청산 미체결 중 보호 주문부터 취소 = 머니-패스 위험. (2) **교차 세션** — 조회는 account+symbol 단위. 같은 계정·심볼 공유 타 세션의 보호 주문까지 방향만 맞으면 취소(스냅샷에 세션 귀속 식별자 없음). dogfood 실측 = 포지션-부착 Partial 조건부 TP/SL 은 Bybit 이 flat 시 자동취소하므로(close 후 orders count=0) 이연은 안전. 스윕은 truly-standalone dangling 주문에만 필요.

**권장 접근:** (a) post-fill flat 확인 후에만 스윕(재조회 후 flat 일 때만, 또는 fill 이벤트 훅) + (b) orderLinkId→Order→세션 매핑으로 이 세션이 건 조건부만 취소(account+symbol 단일-활성-세션 DB 제약이 없는 한). 그 매핑이 없으면 스윕 자체를 빼는 게 안전.

---

### BL-438

**Title:** 거래소 네이티브 TP/SL·트레일링 청산 손익이 머니-패스에 전혀 계상되지 않음
**Category:** Backend / trading (money path)
**Priority:** P1
**Trigger:** 즉시
**Est:** M (6-8h — 귀속 설계가 핵심)
**출처:** 2026-07-25 money-path-accuracy 계획 단계 실발견 (`context-notes.md` §3.1)

**원인 / 영향:** entry 에 부착한 브래킷 TP/SL 이나 `set_trading_stop` 트레일링이 체결되면 포지션이 닫히지만 **우리 DB 엔 아무 행도 생기지 않는다.** WS `order` 고아 이벤트는 5초 버퍼 후 폐기(`state_handler.py:97-102`, `logger.debug` 만 — 알림 없음), `execution` 토픽은 미구독(`websocket_task.py:330`), reconciler 는 local→exchange 단방향이라 INSERT 하지 않는다(`reconciliation.py:137-148`). Order INSERT 지점은 `OrderService.execute` 2곳뿐이다. 그 다음 바에서 pine_v2 warmup-replay 가 **같은 청산을 스스로 추측**해 이미 flat 인 포지션에 reduce-only close 를 발주하고 → `ProviderError` → `state=rejected` → 모든 손익 쿼리가 `state==filled` 로 걸러낸다. 결과적으로 **브래킷으로 익절/손절된 거래의 손익은 Kill Switch·loss-limit 알림·세션 에쿼티 커브 어디에도 잡히지 않는다.** money-path-accuracy(BL-014 부분)는 "우리가 발주한 청산 주문"만 고쳤으므로 이 구멍은 그대로다.

**★선행 주의(2026-07-25 자체 정정):** 현재 스윕의 `orphan_row` 카운터는 **구멍 크기를 측정하지 못한다.** 스윕 후보가 `list_unsynced_reduce_only_since()` = _우리 자신의_ 미동기화 주문이라, 백필이 정상 동작하는 steady state 에선 후보가 0 → 페이지를 아예 안 가져와 orphan 이 영영 0 으로 읽힌다(dogfood 에서 `groups=0` 실측). 규모를 실측하려면 **활성 계정·심볼을 독립적으로 열거**하는 별도 조회가 선행돼야 한다. 이 BL 의 첫 step = 그 측정 스파이크.

**권장 접근:** 스윕이 이미 `/v5/position/closed-pnl` 페이지를 읽고 있으므로 orphan 행을 (a) 합성 Order 행으로 INSERT(state=filled·reduce_only=true·exchange_order_id=Bybit orderId, 마이그레이션 0 가능하나 멱등성·세션 귀속 설계 필요) 하거나 (b) 별도 exchange-exit 원장을 신설한다. 어느 쪽이든 **세션 귀속**(어느 LiveSignalSession 의 포지션이었나)이 핵심 난점이다. 선행으로 `execution` 토픽 구독을 검토하면 실시간 귀속이 쉬워진다.

**Risk:** 🔴 (리스크 게이트가 실현 손실의 일부를 못 본다 — 한도 초과를 늦게 감지)

**상태:** 🟡 **부분 Resolved — 관측 원장(최근 7일) 까지 (2026-07-25, `stage/exit-attribution`).** 측정 스파이크가 전제를 뒤집었다 — 거래소 전용 행 4건(행 36.4% · |손익| 55.8%)은 **브래킷이 아니라 앱 밖 수동 청산**이었고, **브래킷 체결은 전 기간 0건**(조건부 주문 4건 전부 `Deactivated`, DB 17행 중 TP/SL 실은 주문 0)이라 이 구멍은 코드 경로상 실재하나 **프로덕션 관측 0 = 잠복**이다. 게다가 거래소 전용 4건 중 우리 포지션은 1건뿐이라 자동 계상은 오차단을 만든다. 사용자 확정 = **관측 원장까지**. 신규 `trading.exchange_exits`(행 단위 원본 + provenance) + 스윕을 계정 독립 열거·최근 7일 창·원장 집계 백필로 재작성 + 분류 7종/귀속 3등급(라벨 전용, `inferred` 는 머니-패스 미투입) + 신규 미귀속 행 1회성 알림.
**트리거 판정:** 도래 — Trigger 줄 자신이 「즉시」다. 조건절이 없고 외생·동승 어휘도 없다(`bl-trigger-sweep` 의 `지금` 축이 낭독으로 같은 판정을 낸다) (2026-08-11 bl-703-partial-verdicts)

**★범위 축소 (2026-07-25, 같은 브랜치).** 과거 90일까지 훑는 기계장치(`exchange_exit_sync_state` 워터마크 · 창 전진 · 잘림 처리)를 **머지 전에 걷어냈다.** 이유 = ① 그걸 만든 직접적 목적(20일 전 미동기화 4건 회수)이 로컬 개발 DB 전소로 소멸 ② 뒤집힌 측정을 스코프에 충분히 반영하지 못한 채 만들었다 ③ **실측 — 그 기계장치는 지속 기제가 아니라 ~13주기(약 65분) 후 영구 자기정지하는 일회성 catch-up 이었다**(워터마크는 주기당 7일 후퇴, horizon 은 매 주기 `now` 에서 재계산되어 전진 → `end_ms <= horizon_ms` 가 영구 latch, DB 영속이라 재시작으로도 안 풀림). 즉 정상 상태에서 축소 전후 동작은 동일하고, 실제로 없어진 것은 **일회성 90일 역사 수입** 하나다. 원장은 이제 **최근 7일만** 담는다 → [BL-452](#bl-452).

**★dogfood 완주 (2026-07-25, 사용자 계정 재등록 후).** 독립 오라클 실측(4행, 합계 −0.12392537) = 원장 적재 결과와 **완전 일치**. 분류·멱등·알림 1회성·§9.5 라이브 worker·authed 전부 실 계정으로 검증. **dogfood 가 진짜 P1 을 하나 더 잡았다** — 신규 미귀속 행 알림이 원장 재조회 시 `classification` 컬럼 타입 문제로 매 사이클 조용히 죽고 있었다(수정 완료, [BL-453](#bl-453)). 백필 종단 검증은 주문 이력 소실로 여전히 불가.

**잔여 = ② 거래소 exit 의 머니-패스 계상 + 과거 이력 적재·백필** — 다음 스프린트가 이 원장 데이터를 근거로 결정한다. 관련 신규 = [BL-444](#bl-444)(loss-limit 알림 스코프) · [BL-446](#bl-446)(cumulative_loss 시간축) · [BL-452](#bl-452)(원장 7일 한계) · [BL-453](#bl-453)(StrEnum 재조회 크래시 패턴).

**★② 재평가 (2026-07-25, exit-money-path §0.5) — "미룬 것" 이 아니라 "현재 데이터로는 정직하게 구현 불가" 다.** 실측이 결론을 강제했다.

```
bracket_tp / bracket_sl / trailing / liquidation = 0 행
matched_order_id IS NOT NULL = 0 · attributed_strategy_id IS NOT NULL = 0
JOIN trading.orders ON exchange_order_id → 0 행
```

원장 행을 머니-패스에 넣으려면 행마다 "어느 세션의 자본이 움직였나" 에 답해야 하는데, 쓸 수 있는 등급은 `exact`(존재 행 0)와 `inferred`(머니-패스 투입 금지)뿐이고 남는 것은 `none` = **귀속 불가**다. 오귀속은 곧 오차단이라 되돌릴 수 없다.

**정직하게 만들 수 있는 유일한 산출물은 귀속 없는 계정 단위 숫자**이고, 그건 Site 2(`DailyLossEvaluator`)의 스코프다. 즉 ② 는 "세션 귀속" 이 아니라 **"거래소 exit 를 포함한 계정 단위 실현손익"** 이라는 별개 설계(원장 직접 조회 + 새 집계 메서드 + Site 2 의 새 가산항)이며 스프린트 하나짜리다. exit-money-path 는 이 결론만 기록하고 착수하지 않았다.

부수 발견 = [BL-457](#bl-457)(`classify_exit` 의 format-only `ours`).

---

### BL-439

**Title:** 부분체결 후 `cancelled` 로 종료된 청산의 실체결 손익 누락
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** limit 청산 경로가 생기거나, 부분체결 상태에서 사용자 취소가 가능해질 때
**Est:** S (2-3h)
**상태:** ⏳ 대기 (트리거 미도래) — cancelled 승자 backfill 예약도, SUM 의 realized_pnl_synced_at 기준 확대도 미구현. limit 청산 매핑은 있으나 미배선이라 Trigger 미도래. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 money-path-accuracy (codex G0 BLOCKING 을 실측 반박한 뒤 남은 진짜 잔여)

**원인 / 영향:** closedPnl backfill 은 `state==filled` 인 reduce-only 주문만 대상으로 한다. 부분체결 뒤 `cancelled` 로 끝난 청산은 실제로 자금이 움직였는데도 `state==filled` 필터에 걸려 손익이 계상되지 않는다. **현재는 도달 불가** — 이 레포의 청산은 전부 `OrderType.market` 이고 Bybit 시장가 부분체결은 `PartiallyFilledCanceled` → ccxt `closed` → 우리 `filled` 로 매핑되기 때문이다. limit 청산이 도입되는 순간 활성화된다.

**권장 접근:** `transition_to_cancelled` 승자에서도 reduce-only 면 backfill 을 enqueue 하고, Kill Switch SUM 의 state 필터를 `realized_pnl_synced_at IS NOT NULL` 기준으로 넓힌다(단 생성 시점 엔진 추정값이 cancelled 행에 남아 있으면 오계상되므로 취소 시 null-out 이 선행돼야 한다).

---

### BL-440

**상태:** ⏳ **대기 (트리거 미도래)** — 본 섹션의 "Resolved" 문자열은 **BL-014 를 가리키는 cross-ref**(출처 줄)이고, 이 BL 자신(`order_executions` per-execution ledger)은 **YAGNI 로 미착수**다. 근거: 본 섹션 `**권장 접근:**` 줄("실제 분석 수요가 생기기 전에는 만들지 않는다") · `docs/roadmap.md:262` `- [ ] **BL-440**`.
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**Title:** per-execution ledger (`order_executions`) — BL-014 원안의 잔여
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 주문 1건의 체결 내역(체결가·수량·수수료 분포) 분석 요구가 생길 때
**Est:** M (4-5h, 마이그레이션 1)
**출처:** 2026-07-25 money-path-accuracy (BL-014 부분 Resolved 후 잔여)

**원인 / 영향:** BL-014 원안은 append-only `order_executions` 테이블(order_id / executed_at / qty / price / fee)을 권고했다. money-path-accuracy 는 거래소 확정 `closedPnl` 로 **주문 단위** 정확도를 확보했으므로 리스크 집계에는 충분하지만, 한 주문 안의 체결 분포는 여전히 표현되지 않는다. `Order.filled_quantity` 는 누적 체결 수량 1개 값만 보유한다.

**권장 접근:** 실제 분석 수요가 생기기 전에는 만들지 않는다(YAGNI). 필요해지면 `/v5/execution/list` 를 원천으로 append-only 적재.

---

### BL-441

**Title:** entry 부분체결 시 pine_v2 warmup-replay 의 사이즈 발산
**Category:** Backend / pine_v2 · trading (money path)
**Priority:** P2
**Trigger:** entry 부분체결이 1건이라도 실관측될 때
**Est:** M (4-6h)
**상태:** ⏳ 대기 (트리거 미도래) — 부분체결 계측(qb_partial_fill_total)만 있고 warmup-replay 수량 보정도 세션 fail-closed 비활성화도 없다 — 조건부 진입 tick 판정 불가 처리가 전부. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 money-path-accuracy

**원인 / 영향:** entry 주문이 부분체결되면 거래소 실포지션은 시뮬레이션이 가정한 수량보다 작다. `run_live` 는 매 평가마다 전체 히스토리를 재실행하며 **자기 시뮬 포지션**을 기준으로 청산 수량을 산출하므로, 이후 close 신호가 실제 보유량보다 큰 수량을 요청한다. reduce-only 라 over-fill 은 막히지만 시뮬과 실계좌의 사이즈가 계속 어긋난다.

**권장 접근:** `Order.filled_quantity`(이번 스프린트로 4 경로 전부 write 됨)를 warmup-replay 진입 수량 보정 입력으로 사용하거나, 부분체결 감지 시 세션을 fail-closed 비활성화한다. `qb_partial_fill_total` 이 실관측 빈도를 제공한다.

---

### BL-446

**Title:** `cumulative_loss` 가 전 기간 누적 손익을 현재 잔고로 나눈다 (시간축 불일치 + 외부 거래 분모 오염)
**Category:** Backend / trading (risk gate)
**Priority:** P2
**Trigger:** 실자금 전환 전 필수
**Est:** M (4h — 리스크 게이트 변경이라 회귀 범위 넓음)
**상태:** ⏳ 대기 (트리거 미도래) — 분자는 여전히 strategy_id+filled 전 기간 합(시간창 없음), 분모는 trigger 시점 실잔고 — 스냅샷/기간창 처방 흔적 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution Plan 압박검증 + 실측

**원인 / 영향:** `CumulativeLossEvaluator`(`kill_switch.py:97-136`)의 분자는 `strategy_id` + `state=filled` 전 기간 누적이고(시간창·`reduce_only`·`realized_pnl_synced_at` 필터 전무), 분모는 `balance_provider.fetch_balance_usdt` 로 조회한 **현재** 잔고다. ① 과거 데이터를 소급 삽입/보정하면 **오늘의 발주 게이트**가 즉시 반응한다 ② 앱 밖 외부 거래가 잔고를 줄이면 **분모가 이미 오염**되므로 그 손익을 분자에 넣으면 이중 반영, 안 넣어도 과대평가다. **실측 — 임계 10%, 분모 실잔고 190,679 USDT 기준 백필 후 loss% 는 0.00018%(여유 54,117배)라 현재 계정에선 발화하지 않는다.** 구조 결함이므로 실자금 전환 전에 닫아야 한다.

**권장 접근:** `capital_base` 를 전략 시작 시점 스냅샷으로 고정하거나, 분자에 세션/기간 창을 도입해 분자·분모의 시간축을 맞춘다.

---

### BL-447

**Title:** `exchange_order_id` write 2경로가 `""` / `"None"` 을 저장할 수 있어 unique index 도입을 막는다
**Category:** Backend / trading
**Priority:** P3
**Trigger:** `exchange_order_id` 에 unique index 를 걸어야 할 때 (합성 행 도입 등)
**Est:** S (2h)
**상태:** ⏳ 대기 (트리거 미도래) — sanitize 미적용 — WS 는 여전히 str(...,""), reconciler 는 str(exch.get("id",...)), transition_to_filled 는 str 무조건 write, 계정 스코프도 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution 적대 평가

**원인 / 영향:** `state_handler.py:235` 는 `str(payload.get("orderId", ""))` 이라 WS 페이로드에 키가 없으면 **빈 문자열**을 저장한다. `reconciliation.py:233` 은 `str(exch.get("id", ...))` 인데 ccxt `safe_order` 가 `id` 키를 **항상 포함**하므로 값이 `None` 이어도 default 가 발동하지 않아 문자열 `"None"` 이 된다. 두 경로 모두 `transition_to_filled` 의 무조건 write 로 들어간다. partial unique index 가 걸린 상태라면 이 UPDATE 가 `IntegrityError` 로 실패해 **체결이 DB 에 기록되지 않는다.** 또한 `state_handler.py:251-263` 의 `_get_by_exchange_order_id` 는 계정 스코프가 없어 계정 간 id 충돌 시 `MultipleResultsFound` 로 터진다(Binance `orderId` 는 심볼별 int64).

**권장 접근:** 두 write 경로를 sanitize(빈 문자열/`"None"`/공백 → `NULL`)하고 `transition_to_filled` 의 인자를 `str | None` 으로 바꿔 None 이면 기존값 보존. `_get_by_exchange_order_id` 에 `exchange_account_id` 조건 추가. 그 다음에야 `(exchange_account_id, exchange_order_id)` 복합 partial unique 가 안전하다.

---

### BL-448

**Title:** WS 고아 이벤트 `replay_orphan` 이 프로덕션 호출자 0 (dead code)
**Category:** Backend / trading (websocket)
**Priority:** P3
**Trigger:** WS 고아 이벤트 유실이 실제 문제로 관측될 때
**Est:** S (2h)
**출처:** 2026-07-25 exit-attribution grounding 실측

**원인 / 영향:** `state_handler.py:172-180` 의 `replay_orphan` 은 테스트에서만 호출된다. REST 응답 경로(`attach_exchange_order_id` / `transition_to_filled`)가 부르지 않아 5초 버퍼는 사실상 **무조건 폐기**로 동작한다. TTL 소거도 다음 `_buffer_orphan` 호출 시에만 도는 lazy 방식이라 백그라운드 타이머가 없고, **폐기 시점에는 로그·메트릭·알림이 전무**하다(버퍼 진입 카운터 `qb_ws_orphan_event_total` 만 있어 유실과 구분 불가).

**권장 접근:** REST 승자 경로에서 `replay_orphan(key, account_id)` 을 호출해 배선하거나, 배선하지 않을 거면 버퍼·함수를 통째로 제거하고 reconciler 단일 복구 경로임을 명시한다. 폐기 시 metric 은 어느 쪽이든 필요하다.

**상태:** ✅ **Resolved (2026-08-09, W2)** — 두 갈래 중 **제거 + 폐기 메트릭**(사용자 결정). 배선은
money-path 의미를 바꾸므로 하지 않았다.

**한 것:**

- `_orphan_buffer` · `replay_orphan` · `_buffer_orphan` · `_ORPHAN_TTL_S` · `_ORPHAN_MAX` 제거.
  reconciler 가 단일 복구 경로임을 모듈 docstring 에 근거와 함께 명시(회수되는 것 = 우리가 발주한
  주문의 놓친 종결 이벤트, 회수 안 되는 것 = 로컬 행이 끝내 안 생기는 이벤트 — reconciler 는
  local→exchange 단방향이라 INSERT 하지 않는다).
- 신규 `qb_ws_orphan_discarded_total{account_id, reason}` — **폐기 축**. `reason` 은
  `terminal_event_lost`(머니-패스 손실) / `non_terminal_ignored`(로컬 행이 있었어도 skip 했을 값).
  ★한 축으로 뭉치지 않은 이유 = 그러면 경보 문턱을 정할 수 없다. 도착 축
  `qb_ws_orphan_event_total` 은 대시보드 계약이라 **불변으로 뒀다**.
- 종결 이벤트 폐기는 `logger.warning` 으로 승격(종전 `logger.debug` 는 프로덕션 레벨에서 무음이었다).
- `qb_ws_orphan_buffer_size` Gauge 삭제 — 버퍼가 없으니 구조적으로 영원히 0 이다.

**★G0 정정 2건 (2026-08-09 실측).** ① BL 본문의 `state_handler.py:172-180` 은 드리프트 — 실제
정의는 `:175` 였다. ② 「테스트에서만 호출된다」는 `replay_orphan` 에 대해서만 참이고, 버퍼 자체는
`test_state_handler.py` 의 **두 케이스가 더** 잡고 있었다(`test_unknown_order_buffered_in_orphan_buffer` ·
`test_orphan_buffer_fifo_eviction_at_1000`). 즉 「`test_state_handler_gaps.py` 를 제외한 WS 테스트
전량 불변」은 **달성 불가능한 음성 대조**였다 — 앞의 것은 행위 단언(전이 없음 + 폐기 계상)으로
바꿨고 뒤의 것은 tombstone 주석과 함께 삭제했다.

---

### BL-449

**Title:** `Order.webhook_payload` 가 SQL NULL 이 아니라 JSONB `'null'` 로 저장됨
**Category:** Backend / trading
**Priority:** P3
**Trigger:** `webhook_payload IS NULL` 술어나 partial index 를 쓰려 할 때
**Est:** S (1h, 마이그레이션 1)
**상태:** ⏳ 대기 (트리거 미도래) — webhook_payload 는 아직 plain JSONB 이고 'null' 정규화 마이그레이션도 없다 — none_as_null 은 ExchangeExit.raw 에만 적용됐다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution 적대 평가 실측

**원인 / 영향:** `models.py:181-184` 가 `Column(JSONB, nullable=True)` 만 지정해 `none_as_null` 이 기본값 False 다. Python `None` 이 `'null'::jsonb` 로 직렬화되어 **DB 실측 17행 중 15행이 JSONB `'null'`** 이고 SQL NULL 은 레거시 시드 2행뿐이다. `webhook_payload IS NULL` 을 술어로 쓰면 레거시 2행만 잡는다.

**권장 접근:** `postgresql.JSONB(none_as_null=True)` 로 바꾸고 기존 `'null'` 행을 SQL NULL 로 정규화하는 데이터 마이그레이션을 함께 넣는다. exit-attribution 의 `ExchangeExit.raw` 는 처음부터 이 지정을 적용했다.

---

### BL-450

**Title:** 일일 dogfood 보고 `get_daily_summary` 에 테넌트 스코프가 없음
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 사용자가 둘 이상 되는 시점 (Beta)
**Est:** S (1h)
**상태:** ⏳ 대기 (트리거 미도래) — get_daily_summary(date) 는 여전히 date 인자 하나뿐이고 user/account 조인이 없어 전 테넌트 글로벌 합계다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution grounding 실측

**원인 / 영향:** `order_repository.py:286-319` 의 `get_daily_summary` 는 `state='filled' AND filled_at ∈ [UTC 자정, +1d)` 만 걸고 user/strategy/account 스코프가 전혀 없다 — **전 테넌트 글로벌 합계**다. `dogfood_report.py:84` 가 이 값을 HTML 리포트에 싣는다. 단일 사용자 환경에선 무해하나 Beta 진입 시 남의 손익이 섞인다.

**권장 접근:** `user_id` 파라미터를 받아 `exchange_accounts` 조인으로 스코프를 건다.

---

### BL-451

**Title:** 파괴적 마이그레이션 테스트가 env 폴백으로 개발 DB 를 드롭할 수 있는 구조
**Category:** DevOps / 안전
**Priority:** P2
**Trigger:** 즉시 (부분 완화 완료)
**Est:** S (2h)
**상태:** ✅ **Resolved** (2026-08-10, `stage/migration-guard`) — 잔여 3항목 전건 종결. ①판정 SSOT `tests/_db_guard.py` 신설 + 루트 `tests/conftest.py::pytest_configure` 로 **승격**하고 `DATABASE_URL` 폴백을 **금지**했다. ★종전 가드의 실체는 「conftest 에도 같은 폴백이 있다」가 아니라 **배선 부재**였다 — 착수 시 실측으로 `pytest tests/trading/` 이 개발 DB DSN 을 물고 rc=0 으로 1088건을 수집했다(그 경로의 세션 픽스처가 `drop_all` 을 돈다). ②`make db-snapshot`/`db-restore` 신설 — 덤프 2.15MB 생성 후 임시 DB 로 복원해 orders 823·strategies 3·**암호화 API 키 2/2** 왕복을 실증했다(개발 DB 무접촉). ③이미 됨 ④`alembic/env.py` 에 `downgrade` 전용 가드 + `-x allow_destructive=1` 탈출구 — `upgrade` 는 통과시켜 `make migrate`·entrypoint·CI 무영향(rc=0 실측). 배선 테스트 **14건** + 변이 **8/8** red(도달 8/8). ★`/code-review` 가 변이 5/5 를 통과한 구현에서 결함 4건을 잡았다 — `-x allow_destructive=0` 이 파괴를 **허용**(`bool("0")`), `TEST_DATABASE_URL` 이 `.env.example` 에 **없음**(Golden Rule), rc=3 이 가드 고유 신호가 아님(INTERNALERROR 와 구분 불가), `effective_dsn()` 2층 방어에 **도달 0**. 넷 다 고치고 회귀 변이 M6·M7·M8 로 박았다. 판정 사본 1곳 잔존 → [BL-697](#bl-697).
**트리거 판정:** 도래 — 트리거가 「즉시」다. 조건어가 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution **실사고**

**원인 / 영향:** `tests/test_migrations.py` 는 `command.downgrade(cfg, "base")` 로 전 테이블을 드롭한다. `_resolved_test_db_url()` 이 `TEST_DATABASE_URL` 없이 `DATABASE_URL` 로 폴백하므로, `DATABASE_URL` 만 export 된 셸에서 이 파일을 돌리면 **개발 DB 가 대상이 된다.** 실제로 이번 스프린트에서 적대 평가 서브에이전트가 그 셸 상태로 실행해 **로컬 개발 DB 가 전소했다** — 주문 17행 · 거래소 계정 1(암호화된 Bybit demo API 키) · 전략 6종 Pine 소스 · 세션 4 · 이벤트 10. `.env.local` 에 평문 키가 없어 API 키는 복구 불가였고 사용자가 재등록해야 했다.

**부분 완화 (2026-07-25, `stage/exit-attribution`):** `_assert_disposable_database` 가 DSN 의 DB 이름이 `_test` 로 끝나지 않으면 `RuntimeError` 를 던진다. 개발 DB DSN 으로 실행 시 파괴 대신 예외가 나는 것을 실증했다.

**잔여 / 권장 접근:** ① 같은 폴백 구조가 `tests/conftest.py` 에도 있다(`TEST_DATABASE_URL > DATABASE_URL > default`) — 파괴성은 낮지만 동일 가드가 필요한지 검토 ② 로컬 개발 DB 주기 백업(`pg_dump` cron 또는 `make db-snapshot`)이 없다. dogfood 데이터는 재현 비용이 크고 API 키는 복구 불가다 ③ 서브에이전트에 DB env 를 넘길 때의 표준 레시피를 `backend/AGENTS.md` 로 승격 ④ **`alembic/env.py:40` 이 `settings.database_url` 을 주입하므로 수동 `alembic downgrade` 는 가드 없이 개발 DB 를 향한다** — `_assert_disposable_database` 는 pytest 경로만 막는다. CLI 경로 가드 또는 `make` 래퍼 검토.

---

### BL-452

**Title:** 거래소 청산 원장이 최근 7일만 담는다 — 과거 이력 적재·백필 불가
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** 아래 중 하나가 실제로 관측될 때 — ① 워커가 7일 넘게 정지한 실사례 ② 7일보다 오래된 미동기화 reduce-only 주문 관측 ③ 한 계정의 7일 청산이 500행 초과(`closed_pnl_window_truncated` 경고 발화) ④ `list_unsynced_reduce_only` 목록이 영구 좀비로 포화
**Est:** M (4-6h — 일회성 catch-up 재도입)
**상태:** ⏳ 대기 (트리거 미도래) — 일회성 catch-up 경로가 레포에 없고, ASC 좀비 정렬(order_repository.py:769)과 meta 커서 tie(-1)도 그대로다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-attribution **범위 축소** 결정 (`context-notes.md` §9)

**원인 / 영향:** 스윕은 매 주기 `[now−7d, now]` **한 창만** 조회한다([BL-438](#bl-438) 축소). 여기서 파생되는 한계 4종을 **의도된 트레이드오프**로 수용했다.

1. 7일보다 오래된 거래소 청산은 원장에 들어오지 않는다.
2. 따라서 백필·재동기화도 **7일 안에서만** 동작한다(#475 의 24시간 한계를 7일로 넓힌 것). 7일 넘게 미동기화로 남은 주문은 자동으로 안 고쳐진다.
3. 워커가 7일 넘게 죽어 있으면 그 구간은 영영 조회되지 않는다.
4. 7일 500행(`_CLOSED_PNL_MAX_PAGES=5` × `limit=100`) 상한을 넘는 계정은 가장 오래된 행을 잃는다. **관측은 로그뿐** — `providers.py` 의 `closed_pnl_window_truncated` 경고(계정 식별자 포함). `qb_closed_pnl_backfill_total` 의 8-outcome 계약이 불변이라 메트릭 라벨은 추가하지 않았다.

**★부수 위험 — `list_unsynced_reduce_only` head-of-line.** `order_repository.py:162` 는 시간창 없이 `ORDER BY filled_at ASC LIMIT 500` 이다. 7일 밖 청산은 원장에 못 들어오므로 그 주문은 영구 미동기화(좀비)로 남고, **ASC 라서 좀비가 앞줄을 차지**한다. 한 계정에 좀비가 500건 쌓이면 쿼리가 좀비만 돌려주어 신규 주문이 영영 백필되지 않으며, 그 상태와 "할 일 없음"을 구분하는 메트릭이 없다. `list_synced_reduce_only` 는 이미 `.desc()` 라 비대칭이다. **사용자 확정 = 등재만, 코드 미변경** (축소 전에도 90일 catch-up 이 ~65분 후 latch-off 되어 동일 위험이었고, 1인 로컬 앱에서 좀비 500건은 멀다).

**★부수 항목 — `fetch_closed_order_meta` 의 커서 tie.** `providers.py:1410` 은 아직 `until = oldest_ms - 1` 이라 같은 `createdTime` 행이 페이지 상한을 넘으면 tie 행을 건너뛴다. `fetch_closed_pnl_window` 쪽은 머니-패스라 이번에 경계 포함으로 고쳤으나, 이쪽은 **분류 라벨 전용 + `setdefault` 멱등**이라 그대로 뒀다 — 누락의 결과는 일부 행이 `unknown` 으로 분류되는 것뿐이다. 분류를 게이트 입력으로 승격하려면 함께 고쳐야 한다.

**권장 접근:** 워터마크 테이블을 되살리는 대신 **일회성 catch-up** 으로 설계한다(축소 전 구현이 실질적으로 그랬다 — §9 실측). 예: 관리 커맨드/1회성 task 가 지정 구간을 창 단위로 훑어 원장을 채우고 끝난다. 상시 beat 경로는 최근 7일 그대로 둔다. ★되살릴 때 **진행 상태를 원장의 `min(exchange_created_at)` 에서 파생하지 말 것** — 청산이 없던 구간에서 삽입이 0 이라 min 이 안 움직여 같은 빈 창을 영원히 재조회한다(실측 반증: 07-24 행 4건 적재 후 정지, 07-05 행 7건 영구 미도달). 함께 `list_unsynced_reduce_only` 를 `.desc()` 로 뒤집거나 `filled_at >= cutoff` 로 조회 창을 적재 창에 맞춘다.

**Risk:** 🟡 (관측 범위 축소. 머니-패스 정확도 자체는 7일 안에서 온전하고, 정상 상태 동작은 축소 전과 동일)

---

### BL-453

**Title:** StrEnum + 평문 String 컬럼 필드 — 새 세션 재조회 시 `.value`/`.name` 접근이 크래시할 수 있음
**Category:** Backend / trading (defensive — 패턴 재발 방지)
**Priority:** P3
**Trigger:** 이 5개 필드 중 하나에 `.value`/`.name`/`isinstance(..., <EnumClass>)` 를 새 세션 재조회 결과에 쓰는 코드가 추가될 때
**Est:** S (1-2h — 감사 + lint 가드 또는 테스트 1건씩)
**출처:** 2026-07-25 exit-attribution dogfood 실측 (`context-notes.md` §9.9) — **실제로 프로덕션 코드에서 한 건 발생해 수정함**

**원인 / 영향:** `ExchangeExit.classification`(`ExitClassification` StrEnum)이 `sa_column=Column("classification", String(24), ...)` 로 선언돼 있다(Sprint 26 의 `UndefinedObjectError` 회피 워크어라운드, `models.py:438-440`). 메모리에서 갓 만든 객체는 `.classification` 이 진짜 enum 이라 `.value` 가 되지만, **다른 세션에서 새로 `SELECT` 한 행은 SQLAlchemy 가 plain `str` 을 그대로 준다**(재캐스팅 없음) — `.value` 접근이 `AttributeError` 를 던진다. dogfood 에서 `_alert_new_exchange_exits` 가 정확히 이 경로로 죽어 신규 미귀속 행 알림이 매 사이클 조용히 실패하고 있었다(§7.3 대로 실측으로만 드러남 — 유닛테스트는 fake repo 라 잡지 못했다). `str(row.classification)` 로 수정 완료(`StrEnum.__str__` 이 값 자체를 돌려주므로 reload/메모리 양쪽 안전) + 실 DB 회귀 테스트 부착.

**감사 결과** — 같은 패턴(StrEnum 타입 + 평문 String 컬럼)인 필드가 4개 더 있다: `LiveSignalSession.interval` · `LiveSignalEvent.status` · `AlertRule.rule_type` · `AlertRule.channel`. 전수 조사 결과 **현재는 이 4개 모두 `==`/`!=`/`str()` 만 쓰거나 호출부가 없어 안전**하다(`StrEnum` 이 `str` 서브클래스라 비교 연산은 reload 여부와 무관). 즉 지금 당장 고칠 버그는 없고, **미래에 이 필드들에 `.value`/`.name` 을 쓰는 코드가 추가되면 같은 함정을 반복**할 잠재 위험만 남아 있다.

**권장 접근:** (a) 최소 — 5개 필드 선언부에 "`.value`/`.name` 금지, `==`/`!=`/`str()` 만 사용" 주석을 통일해서 남긴다(현재 `interval` 필드에만 있음, 나머지 4개엔 없음) (b) 중간 — ruff 커스텀 규칙 또는 AST 기반 테스트(이 레포의 `test_no_module_level_loop_bound_state.py` 패턴 참고)로 이 5개 필드명에 대한 `.value`/`.name` 접근을 정적으로 금지 (c) 근본 — Sprint 26 워크어라운드가 아직 필요한지 재검토하고, 필요 없으면 `sa.Enum` 으로 되돌려 SQLAlchemy 가 재캐스팅을 대신하게 한다.

**Risk:** 🟢 (현재 실제 발생한 크래시는 이미 수정됨. 이 항목은 재발 방지용 예방적 등재)

**상태:** 🟡 **부분 Resolved — 권장안 (a) 까지 (2026-07-25, `stage/exit-money-path`).** `tasks/trading.py:1698` 의 마지막 `.value` 잔존(`qb_exchange_exit_rows_total` 라벨)을 `str(row.classification)` 로 바꿨다. 지금은 메모리 객체라 안전하지만, 소스가 재조회 경로로 바뀌는 리팩터 한 번이면 dogfood 때와 같은 크래시가 재현되는 자리였다(grep 결과 코드베이스에 남은 유일한 `.value`). 그리고 **감사 목록에서 빠져 있던 `ExchangeExit.attribution_confidence` 를 포함해 6개 필드 전부**에 "`.value`/`.name` 금지, `==`/`!=`/`str()` 만" 주석을 통일했다(`models.py:441 · 583 · 634 · 640 · 718 · 742`). 권장안 (b) 정적 가드와 (c) `sa.Enum` 복귀는 미착수.
**트리거 판정:** 미도래 — 동승 조건. 「이 5개 필드에 `.value` 를 새로 쓰는 코드가 추가될 때」라 그 코드를 쓰는 회차에 붙는다. 단독 착수 시 값이 0이다 (2026-08-11 bl-703-partial-verdicts)

---

### BL-455

**Title:** 수동 청산이 `LiveSignalEvent` 를 남기지 않아 FE 타임라인과 watchdog 팬아웃에서 빠진다
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 수동 청산을 이벤트 타임라인에서 보고 싶을 때 · watchdog 규칙을 수동 청산에도 걸고 싶을 때
**Est:** M (4-6h — 쓰기 경로 + 원자성 설계)
**상태:** ⏳ 대기 (트리거 미도래) — close_service 는 여전히 Order 만 만들고 이벤트를 안 남기며, 테스트가 'manual_close 는 세션 역인덱스에 안 잡힌다'를 그대로 고정하고 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-money-path — [BL-444](#bl-444) 안 (b) 기각분 분리 등재

**원인 / 영향:** `ClosePositionService.close_position`(`close_service.py:78-95`)은 Order 만 만들고 `LiveSignalEvent` 를 만들지 않는다. [BL-444](#bl-444) 의 손익 집계 결함은 읽기 스코프 교체로 닫혔으나, **이벤트 FK 에 의존하는 나머지 두 기능은 여전히 수동 청산을 못 본다** — ① FE §07 이벤트 타임라인 ② `LiveSignalSessionRepository.find_active_by_order_id` 기반 watchdog 규칙 팬아웃(`tasks/trading.py:549-585`). TradingView 웹훅 주문도 같다.

**★착수 전 반드시 읽을 것 — 순진한 구현은 중복 청산을 발주한다.** `dispatch_pending_live_signal_events_task`(`tasks/live_signal.py:756`)가 beat 5분 주기로 `list_pending(limit=50)` 을 **세션 필터 없이 무조건 재발행**한다. `status=pending` 이벤트를 넣으면 beat 이 집어 두 번째 reduce-only 시장가 청산을 낸다. 수동 청산은 `idempotency_key=None`(`close_service.py:93`)이라 idempotency 방어도 없다. 또 `OrderService.execute` 가 내부에서 commit 하므로 "주문 커밋 → 이벤트 커밋" 사이 프로세스가 죽으면 이벤트 없는 주문이 남는다 — OrderService 의 커밋 경계를 재설계하지 않는 한 이 구멍은 못 막는다.

**★UNIQUE 주의.** `uq_live_signal_events_idempotency(session_id, bar_time, sequence_no, action, trade_id)` 에 `on_conflict_do_nothing` 이 걸려 있다(`live_signal_event_repository.py:100`). `bar_time` 을 바 경계로 정렬하면 **진짜 Pine 시그널 INSERT 가 조용히 삼켜진다.** `trade_id = f"manual:{order_id}"` 처럼 그 필드 하나로 전역 유일성이 보장되는 형태여야 한다.

**권장 접근:** 이벤트 테이블의 계약("엔진이 낸 실행 지시")을 오염시키지 않는 별도 표현(예: 이벤트에 출처 컬럼 추가, 또는 타임라인을 Order 기준으로 합성)을 먼저 검토한다. 이벤트를 직접 넣기로 한다면 `status` 를 pending 이 아닌 terminal 로 넣어 beat 재발행 경로를 원천 차단할 것.

**Risk:** 🟡 (관측 결손. 잘못 구현하면 🔴 — 중복 청산 발주)

---

### BL-456

**Title:** 세션 창이 `filled_at` 반열림이라 늦은 체결이 다음 세션으로 오귀속되거나 영구 미귀속된다
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** 세션 종료 직후 체결이 실제로 관측될 때 — `filled_at − created_at` 간극이 세션 종료 지연보다 클 때
**Est:** M (3-4h — 대안마다 다른 결함이 있어 설계가 핵심)
**상태:** ⏳ 대기 (트리거 미도래) — 창은 여전히 filled_at 반열림 그대로이고(:225/:233/:238) 권장 선행조건인 filled_at−created_at 간극 실측 기록이 레포에 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-money-path [BL-445](#bl-445) 가 **수용한** 트레이드오프

**원인 / 영향:** `_session_scope_where`(`order_repository.py`)가 창을 `Order.filled_at` 에 `[created_at, deactivated_at)` 로 건다. 청산을 누르고(202, `state=pending`) 곧바로 세션을 끈 뒤 체결이 도착하면 그 주문은 자기를 만든 세션에서 빠진다. 인접 세션이 있으면 **그쪽으로 귀속**되고, 없으면 **어느 세션에도 안 잡힌다.** 후자의 경우 Site 3(loss-limit)·Site 4(커브·대시보드 KPI) 양쪽에서 사라진다.

덧붙여 `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**("terminal_at")이라, 창의 정밀도가 관측 지연만큼 흐리다(codex G0 지적).

**검토한 대안과 각각의 결함** — ① `created_at` 상한: 늦은 체결을 살리고 인접 세션 중복도 없지만, 인과("이 세션이 이 주문을 일으켰나")와 커브 x축(`filled_at`)의 기준이 갈린다 ② `filled_at + grace`: 임의 상수가 생기고 인접 세션과 창이 겹쳐 **같은 주문이 두 커브에 동시 등장**한다 ③ 현행 `filled_at` 반열림: 배타성은 완벽하나 늦은 체결을 흘린다.

**권장 접근:** 실측이 선행돼야 한다 — dogfood 에서 `filled_at − created_at` 실제 간극을 재고, 그 간극이 세션 종료 지연보다 유의하게 큰지 확인한 뒤에야 대안을 고른다. 간극이 수백 ms 수준이면 현행 유지가 옳다.

**Risk:** 🟡 (경계 케이스 손익 누락. 현행 계약은 테스트로 고정돼 있어 조용한 변경은 불가)

---

### BL-458

**Title:** 머니-패스 5곳이 `realized_pnl_synced_at` 을 구분하지 않아 pine 추정값과 거래소 확정값이 한 합계에 섞인다
**Category:** Backend / trading (money path)
**Priority:** P2
**Trigger:** 실자금 전환 전
**Est:** M (4h — 스키마 필드 추가 + FE)
**출처:** 2026-07-25 exit-money-path Explore 3-리더 grounding

**원인 / 영향:** money-path-accuracy 스프린트가 `Order.realized_pnl_synced_at`(`models.py:200`)을 출처 마커로 만들었다 — NULL = pine_v2 추정, 값 있음 = 거래소 확정 `closedPnl`. 그런데 **소비처 5곳 어디도 이 컬럼을 읽지 않는다.** Kill Switch 누적·일일, loss-limit 알림, 세션 커브·대시보드 KPI, 일일 리포트 전부 추정값과 확정값을 무차별로 더한다. FE 블로터는 주문 **행 단위로는** 이 구분을 렌더하고 있어(`orders-blotter.tsx`), 집계에서만 사라진다.

**★권장 접근 — 필터링은 틀린 해법이다.** `realized_pnl_synced_at IS NOT NULL` 로 합계를 좁히면 **체결 시점부터 스윕 도착까지의 손실이 통째로 안 보인다**(fail-open). 자본 보호 게이트에 대해 추정값은 0 보다 엄격하게 낫다 — pine 추정 오차는 수수료·슬리피지 수준이지만 배제는 오차 100% 다. 게다가 수동 청산은 삽입 시 `realized_pnl` 이 **애초에 NULL** 이라 이중으로 사라진다.

올바른 방향은 **라벨**이다. Site 4 응답의 커브 포인트(또는 주문)에 `confirmed: bool` 을 실어 FE 가 추정 구간을 다르게 렌더하게 한다. 가산적이고 게이트에 무영향이다. `LiveSignalStateResponse` 스키마 필드 추가 + FE 변경이 따른다.

**Risk:** 🟡 (숫자의 신뢰 등급이 화면에 안 드러난다. 게이트 자체는 fail-loud 쪽이라 안전)

**상태:** 🟡 **부분 Resolved (2026-07-26, `stage/money-path-finish`) — 사람이 읽는 2표면까지.** 사용자 결정 = "라벨 + 소계 · Site 3·4". **Site 3**(loss-limit 알림) = `sum_filled_realized_pnl_for_session` → `realized_pnl_split_for_session -> SessionRealizedPnl`(PG `FILTER` 한 문장 5 스칼라)로 개명·retype 해 "출처를 안 보고 합산" 을 표현 불가로 만들고, 본문에 `거래소 확정 X · 추정 Y` + 손익 미도착 체결 건수를 싣는다. **Site 4**(세션 커브·대시보드 §01 KPI) = 커브 포인트에 `source` + 평면 소계 4필드, FE 는 기존 SSOT(`ORDER_REALIZED_PNL_SOURCE_LABEL`)를 재사용해 새 어휘 0. **Site 1·2 게이트 수식과 Site 5 는 무변경** — 확정값만으로 좁히면 체결~스윕 도착 구간 손실이 사라지는 fail-open 이다. 대조군 seed 에 `synced_at` 을 심어 **가드레일이 그 fail-open 좁힘을 잡아내게** 강화했다.
**트리거 판정:** 미도래 — 외생 조건(실자금 전환). [BL-003] 이 막고 있다 (2026-08-11 bl-703-partial-verdicts)

**잔여** — ① Site 1·2 게이트는 여전히 추정·확정 혼재(의도) ② Site 5 일일 리포트 미표면화 ③ **포트폴리오 병합 커브는 포인트별 출처 표현 불가** — `mergeCumulativeCurves` 가 각 세션의 마지막 누적값을 carry-forward 해 더하므로 한 지점의 값은 대부분 과거 거래에서 실려온 값의 합이다. 집계 수준 라벨로 강등했고 구간별 표시는 세션 상세에서만 한다 ④ Site 4 는 `unrecorded_count` 를 세지 않는다(추가 왕복 0 을 택함 — 폴백은 `docs/archive/sprints/money-path-finish/operating-contract.md` §4).

---

### BL-459

**Title:** 세션 읽기와 주문 조회 사이에 비활성화가 커밋되면 그 한 번의 응답이 종료 후 체결을 포함한다 (TOCTOU)
**Category:** Backend / trading (money path — 관측 정확도)
**Priority:** P3
**Trigger:** 세션 종료와 체결이 같은 순간에 겹치는 것이 실제로 관측될 때
**Est:** M (3-4h — 세션↔주문 단일 조인으로 재구성)
**상태:** ⏳ 대기 (트리거 미도래) — 세션 행을 파이썬에서 읽어 SessionScope 를 만든 뒤 별도 SELECT 로 주문을 조회하는 구조가 두 소비처에 그대로다 — 단일 조인 없음. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-25 exit-money-path **최종 codex 누적 diff 리뷰** [P2]

**원인 / 영향:** 두 소비처 모두 **세션 행을 먼저 읽고 → 별도 SELECT 로 주문을 조회**한다.

- `alert_rules.py:60` — `list_active_loss_rules_with_sessions()` 가 `is_active=true` 세션만 돌려주므로 `SessionScope.ended_at` 은 항상 `None`(무상한)이다.
- `router.py:465` — `get_by_id(session_id)` 로 읽은 `sess` 의 `deactivated_at` 을 그대로 쓴다.

그 사이에 `LiveSignalSessionRepository.deactivate`(`:155`)가 커밋되면 — 호출 지점은 4곳(`tasks/live_signal.py:433/503/539` beat + `router.py:442` 사용자 DELETE) — 스코프는 여전히 무상한이라 **종료 후 체결이 그 한 번의 계산에 섞인다.** READ COMMITTED 라 두 번째 SELECT 는 새 스냅샷을 보지만 `ended_at` 값은 이미 파이썬 쪽에 잡혀 있다.

**★등급 판단 — 회귀가 아니다.** 이 변경 **전에는** Site 4 에 창이 아예 없었고(전 기간 무조건 포함) Site 3 도 창이 없었다. 즉 이 레이스는 새 코드가 **한 번의 계산 동안만** 옛 동작을 하게 만드는 것이고, 다음 평가/요청에서 자가 교정된다. 두 경로 모두 발주를 막지 않는 **읽기 전용 관측**이다. 그래서 exit-money-path 는 이걸 고치지 않고 등재만 했다 — 스프린트 막바지에 쿼리 구조를 바꾸면 회귀 표면이 넓어지고, codex 자신도 "새 테스트는 순차 실행뿐이라 이 경쟁 조건을 잡지 못한다" 고 적었다.

**권장 접근:** 세션 경계와 주문을 **한 쿼리**로 묶는다(`live_signal_sessions` 를 조인해 `s.created_at`/`s.deactivated_at` 을 SQL 안에서 읽게 한다 — `docs/archive/sprints/exit-money-path/operating-contract.md` §5 의 진단 SQL 이 이미 그 형태다). 그러면 단일 스냅샷 안에서 경계와 행이 함께 결정된다. 잠금은 불필요하다.

**Risk:** 🟢 (한 번의 응답/평가에 한정 · 자가 교정 · 변경 전보다 엄격)

### BL-466

**Title:** 레버리지 1 백테스트가 자본을 무제한 음수로 몰 수 있다 (마진 게이트 no-op + 청산 없음)
**Category:** Backend / backtest engine (모델 충실도)
**Priority:** P2
**Trigger:** 실자금 전 · 또는 사이징 모델 재검토 시
**Est:** M (설계 결정 선행)
**상태:** ✅ **Resolved** (2026-08-09 btfix) — 승인안 **(c) 리포트 고지**. ★**새 지표 필드를 만들지 않았다** — `mdd_exceeds_capital` 이 이미 정확히 그 술어다(peak ≥ init_cash > 0 이므로 `max_drawdown < -1` ⟺ `equity_min < 0`). 동치 boolean 을 더하면 정보 없이 golden·trust-layer baseline 만 움직인다(`metrics_snapshot` 이 `dataclasses.fields()` 유도 + 정확 dict 비교라 필드 1개에 71→72 keys). 실측 재현: L=1·사이징 미선언에서 자본 10,000 → **−49,044**(5.9배 손실)인데 플래그는 **이미 True** 였다. 한 것 = ① 실경로 오라클 신설 `tests/backtest/engine/test_capital_exceeded_disclosure.py` — 종전 오라클은 `RawTrade` 를 손조립해 어댑터 내부 함수를 불러 **이 경로를 한 번도 안 밟았다**. 고지 + **동작 불변**(강제 종료 없음·수량 1.0 그대로) + 음성 대조 + JSONB 왕복 4건 ② ★**FE 가 원인을 레버리지로 오귀속**하고 있었다 — 축 라벨 "leverage 시 -100% 초과 가능" 을 사실 진술로 바꾸고, 1x 캡션에 "강제청산이 없어 실제로는 불가능한 결과" 를 더했다. `backend/src` **0줄** 이라 golden baseline 은 구조적으로 무변경.
**출처:** 2026-07-26 dogfood-restore — [BL-465](#bl-465) 조사 중 파생

**원인 / 영향:** `_can_afford_entry` 는 `is_leverage_active(self.leverage)` 가 거짓이면 즉시 `True` 를 반환한다(`strategy_state.py:374`). L=1 에는 마진 개념이 없다는 #480 TV/MT5 컨벤션 결정의 귀결이고 그 자체로는 일관적이다. 문제는 **L=1 에서 청산도 없다**는 것과 겹칠 때다 — 사이징을 선언하지 않은 전략은 `compute_qty` 가 `1.0` 을 돌려주므로(`strategy_state.py:317`) 1 BTC ≈ $64,000 명목이 $10,000 자본 위에서 돌고, 손실이 무한정 누적된다. 실측 = 초기자본의 **21.8배 손실**. 현물 1x 에서는 물리적으로 불가능한 결과다.

`test_mdd_exceeds_capital_when_equity_goes_negative` 가 이미 존재하므로 음수 자본은 **알려진·테스트된 조건**이었다. 다만 그 위에서 지표가 무엇을 보고해야 하는지는 정해져 있지 않았다.

**권장 접근:** 선택지 3 — (a) L=1 에도 자본 소진 시 강제 종료(현물 파산 모델) (b) 무담보 명목을 자본으로 상한 (c) 현 동작 유지 + 리포트에 "이 실행은 자본을 초과해 손실했다" 명시 고지. (c) 가 가장 싸고 baseline 을 안 흔든다.

**Risk:** 🟡 (숫자가 물리적으로 불가능하지만 지표는 BL-465 로 이미 입을 닫았다)

---

### BL-468

**Title:** `OHLCV_FIXTURE_ROOT` 기본값이 CWD 상대라 host 실행에서 깨지고, `FixtureProvider` 는 canonical 심볼을 서빙할 수 없다
**Category:** Backend / market_data
**Priority:** P3
**Trigger:** fixture provider 를 실제로 쓸 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — config 기본값은 여전히 CWD 상대이고 fixture.py:30 이 심볼 슬래시를 그대로 경로에 넣는다 — 두 결함 모두 미수정. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**원인 / 영향:** ① 코드 기본값 `"backend/data/fixtures/ohlcv"` 가 프로세스 CWD 상대인데 `make be`/`make be-isolated` 는 `cd backend` 후 실행하므로 `backend/backend/…` 로 풀린다(존재하지 않음). 오늘 무해한 이유는 host uvicorn 이 `FixtureProvider.get_ohlcv()` 를 실제로 호출하지 않기 때문뿐이다. ② `FixtureProvider` 는 `root / f"{symbol}_{tf}.csv"` 를 만드는데(`fixture.py:30`) canonical `BTC/USDT` 의 슬래시가 **경로 구분자**가 되어 `<root>/BTC/USDT_1h.csv` 를 찾는다. 커밋된 픽스처는 평면 `BTCUSDT_1h.csv` 뿐 — 레포의 빈 `backend/data/fixtures/ohlcv/BTC/` 디렉터리가 과거에 누가 여기 부딪힌 흔적이다.

**권장 접근:** 기본값을 레포 루트 기준 절대경로로 해석하거나, `FixtureProvider` 가 심볼의 `/` 를 파일명 안에서 치환.

**Risk:** 🟡 (오늘은 timescale provider 만 쓰여서 잠복)

---

### BL-469

**Title:** `market_data.backfill_ohlcv` 태스크가 celery 에 등록돼 있지 않고, docstring 의 실행법도 존재하지 않는다
**Category:** Backend / tasks (dead code + 거짓 문서)
**Priority:** P3
**Trigger:** 백필을 태스크로 돌릴 필요가 생길 때
**Est:** S (10m)

**원인 / 영향:** `celery_app.py:29-42` `include=[…]` 10개에 `src.tasks.market_data_backfill` 이 없고 autodiscover 도 없다 → `.delay()`/`celery call` 은 `Received unregistered task` 로 끝난다. 게다가 docstring 이 안내하는 `python -m src.tasks.market_data_backfill BTC/USDT 1h 60` 은 **`__main__` 블록이 없어 무동작**이다. 직접 await 가능한 `_async_backfill` 은 동작하지만 `[now-N일, now]` 창만 표현한다.

오늘 이게 안 아픈 이유 = `TimescaleProvider` 가 cache-miss 시 스스로 fetch 하므로 별도 백필이 필요 없다. 그래서 **경로 자체가 불필요할 수 있다** — 등록하기 전에 존치 여부부터 결정할 것.

**Risk:** 🟢 (dead)

**상태:** ✅ **Resolved (2026-08-09, W2)** — **등록하지 않고 제거**했다. `src/tasks/market_data_backfill.py`(141줄) + `tests/tasks/test_market_data_backfill.py`(164줄) 삭제.

**존치 여부 판정 — 「등록 전에 결정하라」에 대한 코드 근거.** `TimescaleProvider.get_ohlcv` 는
cache-first 다 — `find_gaps` 로 빈 구간을 찾아 그 구간만 `ccxt.fetch_ohlcv` → `insert_bulk` →
`commit` 한다(`providers/timescale.py:62-81`). 그리고 그 함수를 **백테스트·옵티마이저·스트레스
테스트 셋이 이미 부른다**(`backtest/service.py:295` · `optimizer/service.py:243` ·
`stress_test/service.py:329`). 즉 시딩은 별도 작업이 아니라 **첫 조회의 부수효과**다 —
`instrument-symbol-boundary.md` 가 이미 같은 말을 적어 뒀다(「백테스트 1회가 곧 perp 시딩」).
따라서 백필 태스크를 살리는 것은 **죽은 경로를 되살리는 것**이지 능력을 되찾는 것이 아니다.

**두 실행법이 **둘 다** 거짓이었다는 실측 (2026-08-09):**

- `python -m src.tasks.market_data_backfill BTC/USDT 1h 60` → **출력 0줄·무동작**(`__main__` 블록 부재).
- 워커 부팅을 흉내내 `include` 12개를 전부 import 한 뒤 레지스트리를 세니 **28개**가 잡혔고
  `market_data.backfill_ohlcv` 는 **그 안에 없다**. `include` 에 `src.tasks.market_data_backfill`
  이 없으므로 `.delay()`/`celery call` 은 `Received unregistered task` 로 끝난다.

**★G0 경로 드리프트 정정.** BL 본문의 `celery_app.py:29-42` `include=[…]` **10개**는 낡았다 —
실제는 **`celery_app.py:57-70` 의 12개**다.

---

### BL-470

**Title:** 캐논 감사 9건이 빈 DB 에서 조용히 통과한다 (데이터 전제 부재)
**Category:** Frontend / e2e
**Priority:** P2
**Trigger:** 다음 캐논 baseline 재측정 시
**Est:** S
**상태:** ✅ Resolved — 2026-08-10 fe-close-surface. 4라우트 전부 `minExamined(res) > 0` 단정(감사 코어가 그 값을 이미 내주고 있었는데 spec 이 import 조차 안 했다) + `/backtests`·`/trading` 에 데이터 전제 단정 + `/backtests/:id/trades` 의 `test.skip` 을 `expect` 로 뒤집고 체결 행 ≥1 도 본다. 음성 대조 2건이 **skip 이 아니라 fail** 을 내는 것으로 확인. ★**종전 상태줄이 과소 진단이었다** — `test.skip` 은 `/trades` 1건뿐이고 나머지 셋은 skip 조차 없이 **초록**이었다(문제가 1건이 아니라 4건)

**원인 / 영향:** authed 캐논 감사는 **렌더된 것**의 하드 실패 수만 센다. 빈 DB 에서는 `StateBox` 하나만 렌더되므로 11열 표·최대 585 체결 원장이 통째로 사라진 걸 **빨간 신호 없이** 놓친다. `authed-canon-p1.spec.ts:16-18` 이 baseline 측정 조건을 명시해 뒀다(`/backtests` 6건 · `/trades` 최대 585 체결 · `/trading` 거래소 1) — 즉 조건이 문서화돼 있는데 단정되지 않는다.

**권장 접근:** 각 캐논 스펙에 데이터 전제 사전조건 단정 추가(없으면 skip 이 아니라 시끄럽게 실패). `make seed` 가 그 전제를 재현 가능하게 만들어 뒀다.

★**2026-08-10 수리 시 드러난 것 2건.** ⑴ 그 baseline 주석 자체가 **이미 거짓**이었다 —
「6건(완료 3·실패 3)」인데 실측은 **완료 7·실패 0**(체결 3,233)이다. 그래서 수리는 **개수를
동결하지 않는다**. 세는 것은 「있는가」이고, 개수를 박으면 시드가 바뀔 때마다 그 단정이 다시
거짓이 된다. ⑵ 고칠 도구가 **이미 코어에 있었다** — `design-canon-audit.ts:543` 의
`minExamined()` 가 「측정 못 했다 vs 깨끗하다」를 가르라고 만들어졌는데 p1 spec 의 import 가
그것만 빼놓았고, `formatCanonResult` 가 로그로 찍기만 했다. `authed-canon-remaining.spec.ts`
는 같은 함정을 이미 `expect` 로 막아 뒀다. **패턴이 레포 안에 있었고 이 파일만 안 따라갔다.**

**Risk:** 🟡 (감사 커버리지가 조용히 증발)

---

### BL-471

**Title:** `exchange_exits` 는 `row_hash` 멱등이라 분류 로직이 바뀌어도 기존 행이 재분류되지 않는다
**Category:** Backend / trading (원장)
**Priority:** P3
**Trigger:** 분류·귀속 로직 변경 시
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — on_conflict_do_nothing 멱등 적재가 그대로고, classification_version 컬럼도 재분류 마이그레이션도 레포에 전혀 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**원인 / 영향:** 원장 적재는 `row_hash` 로 멱등이라 이미 있는 행은 건너뛴다. 그래서 BL-457(#481)이 `classify_exit` 의미를 바꿨는데도 기존 행은 pre-fix 라벨로 고착돼 있다. 실측 — 현 개발 DB 4행 중 3행이 `ours` 인데 `matched_order_id` 는 전부 NULL 이고 `orders` 는 0행이다. 포스트-#481 로직이면 `unknown` 이 나와야 한다.

**권장 접근:** 재분류 마이그레이션 또는 `classification_version` 컬럼 + 버전 불일치 시 재계산.

**Risk:** 🟢 (라벨 전용 축이고 소비처가 0)

---

### BL-472

**Title:** 백테스트 목록이 정상 컨벤션(monthly/daily)에는 각주를 달지 않아 두 기준을 구분할 수 없다
**Category:** Frontend / backtest
**Priority:** P3
**Trigger:** BL-461(sub-daily fallback) 처리 시 함께
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 목록 title 이 여전히 legacy/unavailable 일 때만 붙고, monthly/daily 는 undefined 라 각주가 없다. (2026-08-09 status-triage-mass 확인) ★2026-08-10 fe-shareable-urls 가 **착수하지 않고 전제만 대조했다** — 아래 세 줄이 그 결과다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

★★**2026-08-10 실측 — 본문 한 문장이 틀렸고, 도메인 값 하나가 빠져 있고, 처방이 하나 더 필요하다.**

- **틀림:** 「리포트는 각주를 달지만 목록은 달지 않는다」 → 목록도 legacy·unavailable 에는 단다
  (`backtest-list.tsx` 의 `sharpe.isLegacy || sharpe.isUnavailable` 조건). 비대칭은 **monthly/daily 에서만** 이다.
  리포트는 `key-stats-strip.tsx` · `metric-groups-section.tsx` 둘 다 **컨벤션과 무관하게 항상** `sharpe.foot` 을 노출한다.
- **누락:** 컨벤션 도메인은 3종이 아니라 **4종**이다 — `tv_monthly_rfr2` · `tv_daily_rfr2` ·
  `unavailable` · **`unavailable_nonpositive_equity`**(`features/backtest/sharpe-convention.ts`).
  처방이 `describeSharpe` 를 그대로 쓰면 넷 다 덮인다.
- **미등재 구멍:** `hasMixedSharpeConventions` 는 `null`(legacy)과 non-null 이 섞일 때만 켜진다.
  **monthly + daily 혼재는 둘 다 non-null 이라 무경고로 통과**한다 — 이 BL 이 지적한 바로 그 상황이
  경고를 못 받는다. 정렬은 BE 가 `sharpe_ratio` 숫자만으로 하고 컨벤션은 보지 않는다(`backtest/repository.py`).

**원인 / 영향:** `backtest-list.tsx` 는 legacy·unavailable 계열에만 `title` 을 단다. `tv_monthly_rfr2` 와 `tv_daily_rfr2` 는 **분모 기간이 다른 별개 척도**인데 목록에서는 둘 다 그냥 숫자로 보여 나란히 정렬된다. 리포트는 각주를 달지만 목록은 달지 않는다.

**Risk:** 🟢

---

### BL-475

**Title:** 서버 권위 risk% 사이징이 구현된 적 없다 (UI 는 있다고 말하고 있었다)
**Category:** Backend / trading (사이징)
**Priority:** P3
**Trigger:** 사이징 자동화가 실제로 필요해질 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — compute_position_size 는 레포 전체에서 backlog 문서에만 존재하고 quantity 도 여전히 Field(gt=0) 필수 — 수량 산출 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 BL-474 작업 중 발견

**원인 / 영향:** 테스트 주문 다이얼로그의 "리스크 %" 모드 문구는 _"수량은 서버가 잔고·리스크 기준으로 계산합니다 (서버 권위 사이징)"_ 였다. 그런 코드는 없다. `OrderService._validate_position_size`(`order_service.py:92-134`)는 `max_qty` 를 구해 **client 수량이 초과하면 거부**할 뿐 수량을 만들어내지 않는다. 게다가 그 모드는 payload 에서 `quantity` 를 빼고 보냈고 `parse_tv_payload:122` 는 `payload["quantity"]` 를 필수로 읽으므로 **전송하면 401** 이었다 — 한 번도 작동한 적 없는 경로다.

**BL-474 에서 한 것(전체 아님):** 모드를 실제 동작에 맞춰 재정의했다 — 수량 필수 + risk% 는 **상한**, 손절가 필수(없으면 `risk_sizing_skip_no_stop` 으로 가드가 조용히 skip 되어 "통과처럼 보이는 미검증" 이 된다). `risk_percent` 를 webhook 파서·라우터에 배선해 상한 검증이 실제로 돌게 했다.

**남은 것:** 진짜 서버 사이징(잔고 × 리스크% ÷ 스탑거리로 **수량 산출**)은 미구현. 필요해지면 `_validate_position_size` 옆에 `compute_position_size` 를 두고 `OrderRequest.quantity` 를 optional 로 여는 설계 결정부터 해야 한다(현재 `Field(gt=0)` 필수).

**Risk:** 🟢 (거짓 문구는 제거됨)

---

### BL-476

**Title:** 공개 webhook 핸들러가 동기 CCXT 왕복 3회를 태운다 (실측 **+4.8초**)
**Category:** Backend / trading (지연)
**Priority:** P2
**Trigger:** TradingView 실연동 전 / webhook 타임아웃 관측 시
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — webhook 라우터가 여전히 동기로 OrderService.execute 를 호출하고 가드의 CCXT 3회(mark/min_notional/balance)가 그대로 인라인이다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-26 BL-474 dogfood 실측

**원인 / 영향:** BL-474 로 `leverage` 가 채워지면서 `order_service.py:218-266` 의 notional 가드가 webhook 경로에서 **처음으로 도달 가능**해졌다. 그 대가로 동기 HTTP 핸들러 안에 CCXT 왕복 3회가 들어왔다.

```
fetch_mark_price     1663 ms   -> 64532.7
fetch_min_notional   1549 ms   -> 5.0
fetch_balance_usdt   1600 ms   -> 190549.99
TOTAL                4812 ms
```

각 호출이 계정 재조회 + 자격증명 복호화 + ephemeral ccxt 클라이언트 생성(`timeout: 30000`)을 한다. 위는 정상 응답 기준이고, 거래소가 느리거나 죽으면 **최악 90초**까지 늘어난다 — TradingView 는 webhook 을 재시도하므로 중복 신호가 될 수 있다(멱등키가 있으나 client-generated 라 재시도마다 새 값이면 무력).

**★게이트가 못 잡는 종류다.** 테스트는 provider 를 stub 으로 갈아끼우므로 항상 0ms 다. 회귀는 프로덕션에서만 보인다.

**권장 접근:** 가드를 Celery 경계 뒤로 옮긴다 — `OrderService.execute` 는 행을 만들고 즉시 201 을 주고, `tasks/trading.py:_execute_with_session` 이 발주 직전에 가드를 평가해 실패 시 `rejected` 로 전이. 이미 그 경로에 `except ProviderError` graceful 전이가 있다. 다만 **거부 시점이 응답 뒤로 밀리는** 계약 변경이라 별도 결정이 필요하다.

**Risk:** 🟡 (지연 절벽, 데이터 오류는 아님)

---

### BL-477

**Title:** 같은 Bybit 서브계정을 가리키는 API 키 2개가 청산 원장에 같은 행을 2번 적재한다 (phantom `unknown`)
**Category:** Backend / trading (청산 원장 귀속)
**Priority:** P3
**Trigger:** 읽기 전용 계정 정리 시 또는 external-exit 알림이 시끄러워질 때
**Est:** S
**상태:** 🟡 부분 해결 — BL-605 dedupe 로 신규 이중 적재는 막혔으나 기존 574행이 남아 있다 — 잔여는 [BL-529] 와 같은 「이미 쌓인 거울 행 정리(사용자 승인)」 (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 외생 조건이 **사용자 결정으로 닫혔다.** 2026-08-11 결정 = `exchange_accounts` `0277c150` **행을 삭제하지 않는다**(FK `ondelete="RESTRICT"` ×3 + `exchange_exits` 103행 ⇒ 지금 DELETE 는 500). 잔여 574행 정리는 그 결정이 뒤집혀야 열린다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-26 BL-474 dogfood 실측

**원인 / 영향:** `exchange_accounts` 두 행(`19a8166a` "bybit demo" · `0277c150` "bybit demo- aaa")이 **같은 Bybit 데모 서브계정의 서로 다른 API 키**다. 스윕은 계정별로 `/v5/position/closed-pnl` 을 치므로 같은 청산이 두 번 적재되고, upsert 키에 `exchange_account_id` 가 들어가 중복으로 접히지 않는다.

```
exchange_order_id                     closed_pnl    classification  exchange_account_id
b0a1c42a-aeb9-404e-89ec-b22ac939e126  -0.05935440   ours            19a8166a  (우리 주문과 매칭)
b0a1c42a-aeb9-404e-89ec-b22ac939e126  -0.05935440   unknown         0277c150  (매칭 실패 → 외부로 분류)
```

07-24 행들도 같은 패턴이라 **선재 문제**이며 BL-474 와 무관하다.

**손익 이중 계상은 없다** — `aggregate_closed_pnl`(`exchange_exit_repository.py:43-59`)이 `WHERE exchange_account_id == account_id` 로 계정 스코프이고, 세션 손익은 `orders.realized_pnl` 을 세지 원장을 세지 않는다. 실측으로 확인: 세션 확정 손익 `-0.12772399` = 두 청산의 정확한 합.

**진짜 영향은 귀속/알림 표면**이다. 우리가 낸 청산이 두 번째 키 관점에서는 "앱 밖에서 일어난 청산" 으로 보여 `unknown` 이 되고, external-exit 알림이 유령 이벤트로 시끄러워진다.

**권장 접근:** ~~(a) 사용자가 읽기 전용 계정을 삭제하면 자연 소멸(가장 싸다)~~ · (b) 등록 시 동일 거래소 서브계정 중복을 감지해 경고 · (c) 귀속을 계정이 아니라 `(exchange, exchange_order_id)` 기준으로 재조회. 셋 중 무엇을 할지는 계정 2개 등록을 계속 지원할지에 달렸다.

★★★**2026-08-11 ledger-truth — (a) 는 「가장 싸다」가 아니라 「지금 누르면 500 이다」.**
DB·코드 대조 실측:

| 무엇                     | 실측                                                                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 두 계정의 `exchange_uid` | **둘 다 `558689281`** (`0277c150` · `19a8166a`) — 중복 확인                                                                                      |
| `0277c150` 의 의존 행    | `exchange_exits` **290** · `orders` **2** · `live_signal_sessions` **1**                                                                         |
| FK 제약                  | `ondelete="RESTRICT"` **×3** — `trading/models.py:244` · `:509` · `:785`                                                                         |
| DELETE 핸들러            | `trading/router.py:274-291` `delete_exchange_account` → `svc._repo.delete()` 직행. `IntegrityError` 핸들러가 **router·service 양쪽에 0건**(grep) |

⇒ DELETE 는 FK RESTRICT 에서 `IntegrityError` 를 내고, 잡는 곳이 없어 **500** 이 된다.
★**「읽기 전용 계정」이라는 전제도 틀렸다** — `0277c150` 에는 `live_signal_sessions` **1행**이
붙어 있다. 읽기 전용이 아니다.
★**상속받은 「`exchange_exits` 103행」도 틀렸다 — 실측 290 이다**(LESSON-099: 「N건」을 상속하지 마라).

**2026-08-11 사용자 결정: 삭제하지 않는다.** ⇒ 진짜 처방은 (b)+(c) 이고, 그 앞에
`router.py:288` 에 **409** 를 세우는 것이 선행이다(현재 500 은 「왜 안 되는지」를 안 알려 준다).
이 셋은 이 회차 범위 밖이고 다음 회차 항목이다.

**Risk:** 🟢 (알림 노이즈. 금액 정확도 영향 없음)

---

### BL-485

**Title:** `FormErrorInline` 이 `detail.detail` 로 폴백하지 않아 공통 컴포넌트를 쓸 수 없다
**Category:** Frontend (에러 표면)
**Priority:** P3
**Trigger:** 422 에러 표면을 공통화하고 싶을 때
**Est:** S
**출처:** 2026-07-26 live-entry-wiring
**상태:** ✅ **Resolved (2026-08-09, W3)** — `parseError` 422 general 분기에
`fm ?? innerDetail ?? fallback` 폴백 추가. red→green = `friendly_message` 없는 422 가
`"API 422 /api/v1/live-sessions"` → 서버 `detail` 문구를 렌더하고 `"API 422"` 미포함.
변이 M = 폴백을 `fm ?? fallback` 으로 되돌리면 그 테스트가 다시 빨개진다(실측).
음성 대조 N = `friendly_message` 가 있으면 `detail.detail` 이 함께 있어도 여전히
`friendly_message` 가 이긴다(전용 테스트로 고정). vitest 209파일 / 1300테스트 green.
★**라이브 세션 폼 교체는 하지 않았다** — 별건이고 이 회차 범위 밖이다.

**원인 / 영향:** `form-error-inline.tsx:93-97` 의 422 general 분기가 `friendly_message` 만 읽고, 없으면 `fallback = err.message` 로 떨어진다. 그 `err.message` 는 `"API 422 /api/v1/live-sessions"` 라 사람이 못 읽는다.

그리고 `friendly_message` 를 응답에 싣는 곳은 `main.py:17-54` 의 `isinstance` **하드코딩 화이트리스트**(`StrategyNotRunnable` / `StrategyDegraded`) 뿐이라, 새 예외는 그 필드를 못 갖는다.

결과: 라이브 세션 폼을 `FormErrorInline` 으로 교체하면 기존 422 **4종**(`StrategySettingsRequired` / `InvalidStrategySettings` / `AccountModeNotAllowed` / `LiveSessionQuotaExceeded`)이 전부 `"API 422 ..."` 로 **조용히 퇴행**한다. 그래서 이번 스프린트는 교체하지 않고 서버 `detail` 문자열 + `describeApiError` 경로를 유지했다.

**권장 접근:** `parseError` 에 `friendly_message ?? detail.detail` 폴백 3줄 추가. 그러면 공통 컴포넌트가 모든 도메인 예외에 안전해지고, 라이브 세션 폼 교체를 재검토할 수 있다. 회귀 = `friendly_message` 없는 422 가 `detail` 문구를 렌더하고 `"API 422"` 를 포함하지 않는지.

**Risk:** 🟢

---

## 운영 규약

### 신규 항목 추가

1. 적절한 priority 결정 (P0~P3 정의 표 참조)
2. 다음 BL ID 부여 (현재 사용 범위: BL-001~005, BL-010~487)
3. live ledger에는 다음 7필드를 쓴다: ID / 제목 / priority / **Status:** / 1줄 영향 / trigger 또는 재검토 시점 / 다음 검증 / 근거 링크. `Category`·`Est`는 실제 계획에 필요할 때만 추가한다.
4. 장문의 재현·반증·대안은 처음부터 해당 sprint `dev-log` 또는 `archive/backlog/`에 둔다. live ledger에 중복하지 않는다.
5. 출처 cross-link (파일:라인 또는 dev-log 파일명) 필수
6. 의존성 있으면 명시 (다른 BL ID 또는 외부 자원)
7. 출처 문서의 자연어 표현 옆에 `→ BL-XXX` cross-link를 추가한다.

### 항목 해소

1. 해당 BL 절에 `**Status:** ✅ Resolved (2026-XX-YY, PR #NN)` 추가
2. 원인·대안·실측이 1화면을 넘으면 먼저 해당 sprint `dev-log`를 상세 근거로 쓴다. 그 기록만으로 재검토할 수 없을 때만 묶음 단위 `archive/backlog/YYYY-MM-DD-<bundle>.md`를 만든다. 기존 `archive/refactoring-backlog/`은 이전 이력으로 유지한다.
3. 본 문서에는 ID / 제목 / priority / status / 1줄 결과 / archive·dev-log 근거 링크만 남긴다. 이 6줄 ledger를 삭제하지 않는다 — `scripts/bl-audit.sh`가 상태를 계속 대조한다.
4. 출처 문서의 cross-link 옆에 `(✅ Resolved BL-XXX)`를 표기한다.
5. "변경 이력"에는 묶음당 한 줄만 기록하고, 상세 서사는 dev-log 또는 archive 링크로 끝낸다.

### Trigger 도래 확인

신규 sprint 진입 시:

1. 본 문서 P0 섹션 전체 review — trigger 도래 항목이 있는가?
2. P1~P2 섹션의 trigger 도 함께 review (예: "Bybit Demo 안정화 후" → 현재 안정화 됐는가?)
3. `_deferred.md` 의 6-8주 재평가 (BL-005 본인 의지 second gate, BL-070~075 Beta milestone)
4. 도래 항목이 있으면 active TODO.md 의 "Next Actions" 로 승격 + 본 문서에서 `**Status:** 🟡 In progress (Sprint NN)` 마킹

---

## 변경 이력

> Sprint 별 BL 변경 1-line 요약. 상세는 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 또는 해당 sprint dev-log.

### functional-parity 스프린트 (2026-07-23)

- **C 디자인 이식 후 기능 격차 마감 (codex exec 4-generator 병렬 + Claude 적대 평가 교차 + Opus MCP dogfood)**: BL-401/BL-411 구현 Resolved + BL-402 구조 소멸 Resolved. 신규 배선 = 주문취소 액션 열(A2, "API unbacked" 미렌더 전제가 거짓 — CF4 완비 실측) / orders `state` 반복 Query + 미체결 nav-count(B2, 캐논 §4.6 복원) / `strategy.backtest_count` read-time GROUP BY(B1, COMPLETED 기준) / 스트레스 최신 결과 리로드 복원(A7-lite) / 대시보드 전략 링크 404 수정(A1) / dead code 정리(backtest-history-card·viewBacktestShare·StrategyWithPine stub). 적대 평가가 실버그 3건 사전 차단(RQ v5 undefined-resolve 영구 error / grid min==max 차단 회귀 / Sprint 54 문구 잔존). 신규 BL-413~416. 정본 = `functional-parity/`.

### optimizer deepen + FE vercel 70룰 감사 (2026-07-13)

- **optimizer deepen 1차 (improve-codebase-architecture, 감사→같은 세션 구현)**: STOP 실측(repository.py 40%) → S0 test-first (40%→100%, 실 DB 11건) + A(디스패치 SSOT — service inline match 제거, seam 3이름→1이름) + B(serializer 공통 helper + `optimizer_result_to_jsonb` 진입점, golden byte-compat 실증) + N1(`engine/dispatch.py`→`select.py` rename — dispatcher.py 이름충돌 해소) + C-min(get/list 손상 row 방어 대칭화, get 500→404) + N2(pick-best·objective 화이트리스트 `_common` SSOT). PR #431/#432/feat/optimizer-cmin-n2 (base stage/optimizer-deepen). 적대 리뷰 P1 0건 + 실 celery worker 3-cell grid 풀 스모크 COMPLETED 검증. KILL/보류: N3→BL-411, C-full→BL-412, N4/N5(이미 deep/의도된 분리 — 재제안 금지).
- **FE vercel 70룰 감사** (파인더 6+반박 검증 30 에이전트, 원시 24→확정 18): high/medium 10건 수정 — **BL-407 Resolved** (lwc v4 PercentageFormatter ×100 부재+precision 양자화 이중결함, 육안 검증 PASS) + live-sessions 차트 identity churn(폴링마다 줌 리셋, "React Compiler 자동 memoize" 주석 거짓 전제 확인) + O(E×N)→O(E+N) + all-trades 병렬 페치 + clerk 배럴 4.9MB→95KB. PR #433 (base stage/fe-react-audit), live smoke 그린(authed 실패 8건은 main 과 동일 집합 = 기지 stale 베이스라인 실측 대조). low 잔여 → **신규 BL-410**.
- **신규 3건**: BL-410(P3 FE low 팩) + BL-411(P3 optimizer stale 422 메시지) + BL-412(P3 result read-side 유니온 C-full).

### pine-batch QA + 엔진 개선 루프 (2026-07-12)

- **신규 4건**: BL-405(P2, pine_v2 bool na→False 실체화 — 워밍업 경계 스퓨리어스 시그널, 오라클 수계산으로 확정) + BL-406(P3, DrFXGOD 잔여 5종 — alma/dmi/time feasible, ticker.new/security_lower_tf 패러다임 밖) + BL-407(P3, 낙폭 차트 Y축 눈금 "-0.1%" 뭉개짐) + BL-408(P3, 디자인 폴리시 잔여물 팩 — stale aria-label 색명 등 6건).
- **기존 확장 1건**: BL-402 에 3사이트 추가 — `backtests/new` strategy picker(UUID 실측+원인 확정) + 원장/필터 Select 2파일 동일 클래스.
- **디자인 감사 총평**: strategies/new + 리포트 페이지 AI-slop 판정 **명백한 부정** — raw hex 0/팔레트 클래스 0/이모지 0, 다크·라이트 양 테마 변수 완비.
- **엔진 즉시 해소 5건 (BL 미경유)**: G1 루프 silent skip / G2 array 15종 / G3 bare security degraded / G4 table.new positional / G5 label.style\_ drift — PR #422, 스위트 778→815 그린.
- **데이터 정직성**: `BTCUSDT_1h.csv` 합성 데이터(OHLC 위반 77%)를 실 Bybit perp 로 교체 + 4h/최근1년 3세트 신설 — PR #421.

- **신규 1건 + 즉시 해소**: BL-404(P1, watchdog `fetch_order` Bybit 전면 실패 — ccxt acknowledged 게이트 + futures 심볼 미정규화 2중 결함) ✅ Resolved 동일 PR. 데모 라이브 세션 실주문 dogfood(코크핏/블로터 3면 검증 PASS)에서 실측 발견.
- **미등재 관찰(후보)**: 신규 세션 첫 evaluate 전 `/state` 404 FE 콘솔 노이즈 / host 기동 `/healthz` celery inspect ping 상시 timeout / ws_stream 큐의 삭제된 계정 태스크 잔재 / `fetch_mark_price` spot 티커 근사(BL-404 본문 기재).

### PR #394 후속 FE 부채 등재 (2026-07-05)

- **신규 4건**: BL-401(optimizer 3폼 field-level zod 에러 미렌더) / BL-402(백테스트 picker uncontrolled↔controlled + raw UUID, BL-164 SSOT 회귀) P2 + BL-400(`enabled: userId` 가드 도메인 비일관 — 통일 결정) / BL-403(recharts↔lwc↔inline-SVG 3원화 해소, BL-395 완료 후) P3.
- **검증 노트**: backtest 폼은 field-level 에러 정상 렌더 확인(zod resolver 미사용) → BL-401 스코프에서 제외. 4건 모두 활성/archived/deferred 중복 grep 0건.

### TV-parity sprint (2026-07-05, 백테스팅 완성도 + 리포트 전문화)

- **신규 7건**: BL-393(trail 틱 시맨틱스+mintick) / BL-398(Sharpe TV convention) P2 + BL-394(BE 분포 집계) / BL-395(lightweight-charts v5 spike) / BL-396(trades 서브페이지 컬럼) / BL-397(섹션 딥링크) / BL-399(ta.sar oracle) P3.
- **코드 반영 (BL 미등재 직접 수정)**: ta.hma sqrt floor→round TV 정합(BL-378 패턴) / BL-388 tripwire 3종+`_to_detail` spread(4→3 site) / sortino·calmar 실구현(TV convention) / BacktestMetrics TV 팩(flat 14+nested 2) / BacktestTrade 10컬럼(MFE/MAE·fee split·exit_kind·comment·누적) / FE 리포트 IA 전면 재편(TV Strategy Tester 구조, Terminal Tape 유지).

### `/deepen-modules trading` 2차 audit-only (2026-06-26, 트레일링 live-placement 직전)

- Wave 1/2/3(라이브 TP/SL) 누적 부채 7건 신규: P2 BL-365(trigger_direction dead+미배선) / BL-366(dispatch DI 중복) / BL-368(`_merge_exit_params` ccxt-key 누설) / BL-369(create_order 3×복붙), P3 BL-367(dispatch boilerplate) / BL-370(exit-field multi-SSOT) / BL-371(ws-stream fill 스트레스). 3 병렬 Explore + adversarial 검증(Agent 2건 과대평가 교정: trigger_direction=현재 버그 아님 latent / risk-sizing test 7건 존재→STOP 미발동). `2026-06-26-trading-deepen-2.md`. BL-202/205 와 무중복. money-path churn 회피로 **리팩터는 트레일링 안정화 후** — C1(BL-365)도 trading-stop 엔드포인트(position-inferred)라 트레일링 미소비, deferred 확정.

### Track B `/deepen-modules trading` audit-only (2026-05-15)

- BL-308 P1 (websocket test coverage 4% → ≥70%) + BL-309 P2 (registry/webhook/fees 0% test 추가) 신규. 15 → 17 active. `2026-05-15-trading-deepen.md`. **Architectural debt 적음** 결론 (Deep module + dispatch dict + 0 SSOT 중복). skill STOP condition (test coverage <70%) 매치 = test 우선 권고.

### CLAUDE.md align audit Track C (2026-05-15)

- BL-306 (§5 한국어 콜론 종결 lint) + BL-307 (§6 한국어 file header lint + 70 file backfill) 신규 P3. 13 → 15 active. `2026-05-15-claudemd-align-audit.md`. LESSON-068 1/3 등재.

### Sprint 59 — PR-D 트리아주 (2026-05-13)

- 158 BL → 13 Active + 8 Deferred + 137 Archived. `_archived.md` + `_deferred.md` 신설.

### 최근 sprint (Sprint 53~58)

- **Sprint 58** (2026-05-11) — BL-241/242/243 Pine TA 확장 Resolved (ta.wma/hma/bb/cross/mom/obv+fixnan + strategy.equity + UTC 라벨). 92 → 89. `sprint58-close`.
- **Sprint 57** (2026-05-11) — BL-234 Optimizer Polish (prior=normal+one_hot+roulette) + BL-237 optimizer_heavy queue Resolved. 신규 BL-241~243. 91 → 92. `sprint57-close`.
- **Sprint 56** (2026-05-11) — BL-233 Genetic executor 본격 Resolved + 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11) — BL-232 Bayesian executor 본격 Resolved + 신규 BL-233~237 (5건). 88 → 92. `sprint55-master`.
- **Sprint 54** (2026-05-12) — Phase 3 Optimizer 본격 진입 (Grid Search MVP). BL-226/227/228/229/230/231 Resolved. 93 → 88.
- **Sprint 53** (2026-05-11) — Optimizer prereq spike. BL-226 Resolved + BL-227~231 신규.

### 이전 sprint (Sprint 15~52, 1-line 요약)

- **Sprint 52** (2026-05-11) — Stress Test follow-up. BL-222~225 Resolved + BL-226 신규.
- **Sprint 51** (2026-05-11) — BL-220 Param Stability MVP Resolved + BL-222~225 신규.
- **Sprint 50** (2026-05-10) — Cost Assumption Sensitivity 본격. BL-219 Resolved.
- **Sprint 45** (2026-05-09) — Surgical Cleanup #4/#3. dashboard-shell 추출 + codex G.4. 신규 BL-195. 92 → 93.
- **Sprint 42** (2026-05-08) — Phase 1.1/1.2 demo onboarding. 신규 BL-193/194. 90 → 92.
- **Sprint 41** (2026-05-07) — 외부 demo 첫인상 패키지. 신규 BL-190/191/192. 87 → 90.
- **Sprint 39** (2026-05-07) — BL-189 Resolved. 88 → 87.
- **Sprint 38** (2026-05-07) — BL-181 Resolved + BL-189 신규 P0.
- **Sprint 37** (2026-05-06) — polish iter 5 (BL-183/184/185/187/187a/188a Resolved, 6건) + 신규 BL-186/188. 86 → 88.
- **Sprint 36** (2026-05-06) — polish iter 4. BL-150/176 Resolved + BL-183 신규.
- **Sprint 35** (2026-05-05) — polish iter 3 + Day 7 4중 AND gate. BL-178/180 Resolved + BL-181/182 신규.
- **Sprint 34** (2026-05-05) — BL-175 Resolved + BL-177 partial + BL-166 cancel + 신규 BL-177-A/B/C/178/179. 80 → 86.
- **Sprint 33** (2026-05-05) — BL-164 Resolved + 신규 BL-175/176/177. 80 net.
- **Sprint 32** (2026-05-05) — Surface Trust Recovery (7 Resolved). 87 → 80. `sprint32-master-retro`.
- **Sprint 27** (2026-05-04) — dogfood Day 1-7 launch. 신규 BL-137~141. 76 → 81.
- **Sprint 25 Hybrid** (2026-05-03) — Frontend E2E Playwright. 5 Resolved + 14 신규.
- **Sprint 21** (2026-05-02) — BL-093/095/097 Resolved + BL-096 partial + 신규 BL-098/099/100.
- **Sprint 18** (2026-05-02) — BL-080 Option C persistent worker loop Resolved.
- **Sprint 17** (2026-05-02) — prefork-safe Partial fix. 신규 BL-080.
- **Sprint 16** (2026-05-01) — BL-010 commit-spy 4 도메인 backfill + BL-027 Resolved.
- **Sprint 15** (2026-05-01) — BL-001 + BL-002 Resolved + 신규 BL-027/028/029.
- **2026-04-30** — 초기 작성 50 BL (P0 5 + P1 17 + P2 14 + P3 8 + Beta 6).

> 누락 sprint (19/20/22~24/26/28~31/40/43/44/46~49)은 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 본문 참조.

---

### BL-522

**Title:** ★**엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다** — 유실 채널 ~~5종~~ **실측 1종**
**Category:** Backend / trading (라이브 진입 완결성)
**상태:** ⏳ **대기 (트리거 미도래) — 「축소」 (2026-08-01 entry-completeness-rejudgement).** 유실 채널 5종 중 **(2)(3) 은 유실 채널이 아님이 확정**, **(4)(5) 는 판별력을 증명한 계측기로 0**, 남은 것은 **(1) 잔여 거절 하나뿐 1건/2일**이다. 층위1 확정 거절률 **16.67% → 2.44%** · 에피소드 유실률 **2.08%**. **P1 → P2 강등** — 잔여 설계는 [BL-578](#bl-578), 재측정 근거는 [BL-536](#bl-536) §2026-08-01(Resolved). 아래 §채널 5종 크기 확정 참조.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**Priority:** **P2** (~~P1~~ — 2026-08-01 축소 판정으로 강등. ★Trigger 는 유지한다)
**Trigger:** 실자금 cutover 전 필수
**Est:** M-L
**출처:** 2026-07-28 live-entry-parity — codex G1 검증 #1/#2/#3/#4/#5 가 하나의 근본원인으로 수렴, soak 실측으로 크기 확정

**원인 / 영향:** sim 이 pending stop 을 체결하면(`strategy_state.py:82-83`) 그 주문은 `desired` 에서 사라지고 포지션이 된다. 그런데 `action="fill"` 은 **dispatch 대상이 아니다** — `event_loop.py:422` 가 "broker 가 자체 fill 알림 처리" 를 전제하기 때문이다(BL-478 이 지적한 그 전제). 따라서 그 진입이 라이브에서 **어떤 이유로든** 완결되지 못하면 다시 시도할 주체가 없다.

**유실 채널 5종** — (1) 조회~발주 사이 가격이 다시 움직여 생기는 잔여 거절 (2) `market_orders_in_flight` 로 reconcile 전체가 deferred (3) 전환 주문의 부분체결 (4) 돌파+resting 조합에서 취소가 트리거를 이긴 경우 (5) notional/balance 사전 게이트 거부.

~~★**크기가 처음 측정됐다** — 62분 soak 에서 `qb_live_conditional_reconcile_errors_total{stage="deferred_market_inflight"}` = **14**. 채널 (2) 하나가 **시간당 14회**다.~~ 조건부 모델에서는 다음 bar 에 재등재되므로 무해했지만 **1-shot 시장가 전환에서는 유실**이다.

> ### ❌ **「시간당 14회」는 반증됐다 (2026-08-01 silent-surface-honesty, 소급 정정)**
>
> 근거였던 `deferred_market_inflight` 는 **유실 채널이 아니라 「청산 tick 수」**임이
> 2026-07-30 close-mismatch-visibility 에서 확정됐다 — `live_signal_events` 9건이 **전량
> `action='close'`** 이고 counter 9 와 **1:1 동치**이며, 게다가 이 counter 는 `desired` 를
> **읽기 전에** 오른다(`live_signal.py:706` vs `:742`) ⇒ **미룰 진입이 0건이어도 발화한다.**
> 그 판정은 [BL-536](#bl-536) 섹션에 기록됐는데 **본 섹션에는 전파되지 않아** 3개월 가까이
> 반증된 숫자가 P1 크기 근거로 남아 있었다.
>
> **처분:** 채널 (2) 의 크기는 **미측정**이다. 이 숫자를 인용하지 마라.
> 채널 5종 중 (2) 를 제외한 나머지의 크기도 재측정 대상이다.
> ★결함 실재 자체는 반증되지 않았다 — **크기만 근거를 잃었다.**

> ### 🟢 **채널 5종 크기 확정 (2026-08-01 entry-completeness-rejudgement)** — 위 「재측정 대상」의 답
>
> **[BL-536](#bl-536) 재판정이 5종 전건의 크기를 냈다. 판정 = 「축소」(사전등록 A3).**
>
> | 채널                                 | 크기 (창 P = 2026-07-30~31, 조건부 파이프라인 109건)                                                                            |
> | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
> | **(1) 잔여 거절**                    | **1건 / 2일** — 유일한 잔존 채널. 격차 0.0005~0.071%. → [BL-578](#bl-578)                                                       |
> | **(2) `market_orders_in_flight`**    | ★**유실 채널이 아니다.** 「청산 tick 수」로 확정(PR #511). **크기 질문 자체가 성립 안 함**                                      |
> | **(3) 전환 주문의 부분체결**         | ★**유실 채널이 아니다.** 조건부 진입 부분체결은 **원장 전 기간 0건**. 원표 `7` 은 **청산측 `qty_step` 절삭 아티팩트**(5축 확정) |
> | **(4) 취소가 트리거를 이김**         | **0 / 68** — 공개 Bybit kline 2호스트 교차(불일치 0) + 체결분 35/37 양성 대조로 판별력 증명                                     |
> | **(5) notional/balance 사전 게이트** | **0** — counter 3종 series 전부 부재 + `live_signal_events` 전 기간 failed 는 `close_position_flat` 뿐 (2축)                    |
>
> ★**따라서 본문의 「유실 채널 5종」은 실제로는 1종이다.** 「전환 의도를 영속화하는 새 상태
> 저장소」는 **짓지 마라** — 본문 자신이 경고한 「사라질 문제에 저장소를 만드는」 경우다.
> 상세 = [BL-536](#bl-536) §2026-08-01 재판정.

**권장 접근:** 전환 의도를 영속화해 다음 tick 에 재시도하거나, `action="fill"` 을 라이브에서 소비하는 경로를 만든다. ★**새 상태 저장소는 위험하므로 크기를 본 뒤 설계한다** — 이번 스프린트가 계측만 넣고 멈춘 이유다.
**Risk:** 🟡 (백테스트↔라이브 진입 발산. 실주문을 잘못 내지는 않는다)

---

### BL-523

> ### 🟡 **판정 「축소」 (2026-07-30 close-mismatch-soak) — ★붙일 값이 없다**
>
> **본문의 전제 2건이 코드 대조로 반증됐다.**
>
> 1. ★**`exit_levels_for` 는 조건부 진입에 대해 항상 `(None, None, None)` 이다.**
>    `place_exit` 가 `targets = [from_entry] if from_entry in self.open_trades else []`
>    (`strategy_state.py:963`) 로 **`open_trades` 만** 타깃하는데, stop 진입은
>    `pending_orders[...] = PendingOrder(...); return None`(`:714-726`) 이라 체결 전까지 거기 없다.
>    ⇒ `pending_exits` 에 레그가 **애초에 생기지 않는다.**
> 2. ★**시드 전략 `s1_pbr.pine` 은 `strategy.exit` 이 0건**이고, 코퍼스 8벌 중 stop 진입과 exit 을
>    **둘 다 쓰는 전략이 없다**(`s4_hma_curvature` 는 exit 만, 나머지는 stop 진입만).
>
> **부수 정정 — 본문의 패리티 근거도 틀렸다.** _"백테스트는 체결 직후 `check_exit_fills` 로
> 브래킷이 활성화되므로 라이브만 무방비"_ 라고 적었으나, bar 루프는
> `check_exit_fills`(`event_loop.py:169`) → `interp.execute`(`:197`) 순서라 레그는 그 bar **끝**에
> 등록되어 **다음 bar** 부터 검사된다. **백테스트도 체결 bar 안에서는 보호하지 않는다.**
>
> #### 실주행 확인 (2026-07-30, celery 경유 · 메인 체크아웃)
>
> ```
> qb_live_conditional_guard_total{outcome="bracket_unavailable"} 2.0
>                                (bracket_attached — 부재)
> ```
>
> 조건부 진입 2건 전량이 `bracket_unavailable`. **100% / 0%** 로 전제가 재현됐다.
>
> **이번 회차에 한 것:** 3단 seam 배관 + 게이트 A(trailing-only 거부)/B(tpSize 정합) +
> `conditional_request_invalid` 라벨 분리 + guard outcome 4종. **부착이 목적이 아니라
> "붙일 것이 있었는가" 를 재는 계측이 산출물이다.** 회귀 테스트
> `test_pending_order_snapshot_has_no_exit_levels_when_entry_not_open` 이 이 사실을 못박는다.
>
> **남은 것(이번 범위 밖):** `bracket_unavailable` 이 계속 100% 면 선택은 둘 —
> (a) `place_exit` 이 pending 진입도 타깃하도록 **엔진 계약 변경**(백테스트 결과가 바뀌므로 TV 패리티 게이트 필요),
> (b) 체결 후 부착(`set_trading_stop` 이 현재 trailing 전용 시그니처라 TP/SL 확장 필요).
> ★**지금 고르지 마라 — 아직 크기를 모른다.**

**Title:** 조건부·전환 진입에 TP/SL 브래킷이 붙지 않는다 — ~~전환은 즉시 체결이라 무방비 창이 실재한다~~ → **엔진이 pending 진입에 exit 레그를 만들지 않아 실을 값이 없다**
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 실자금 cutover 전
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래) — 범위 「축소」**(2026-07-30 close-mismatch-soak). 전제 반증: 엔진이 pending 진입에 exit 레그를 만들지 않아 실을 값이 없다. 배관+계측은 착지, 엔진 계약 변경은 크기 미확정으로 보류.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-entry-parity 적대 검증(백테스트 패리티 렌즈)

**원인 / 영향:** reconcile 의 `OrderRequest`(`tasks/live_signal.py` 발주 루프)에 `take_profit`/`stop_loss`/`trailing_stop` 이 없다. 일반 LiveSignal 경로는 지정한다. 백테스트는 체결 직후 `check_exit_fills`(`event_loop.py`)로 브래킷이 활성화되므로 **라이브만 무방비**다. 조건부일 때는 트리거 전까지 잠재적이었지만 **시장가 전환은 즉시 포지션을 연다.**

**권장 접근:** `PendingOrderSnapshot` 에 exit 레벨을 실어 진입 주문에 부착한다. 체결 후 부착 경로(`_enqueue_trailing_if_intended`)와 중복되지 않게 정리 필요.
**Risk:** 🟡

---

### BL-524

**Title:** `strategy.entry(limit=...)` 이 조용히 버려지고 시장가 진입으로 대체된다 — TV 충실도 결함
**Category:** Backend / pine_v2
**Priority:** P2
**Trigger:** limit 진입을 쓰는 전략을 지원할 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — entry 의 limit/trail/qty_percent 는 여전히 unsupported 로 버려지고, PendingOrder 에 limit_price 필드가 없다(있는 건 exit leg 뿐). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-entry-parity 스코프 조사

**원인 / 영향:** `interpreter.py:1521-1523` 이 `limit`·`trail_points`·`trail_offset`·`qty_percent` 를 **미지원 인자로 걸러 경고만 남기고** 버린다. `stop` 이 없으면 그 진입은 `MarketIntent` 로 큐돼 **시장가로 체결**된다. `PendingOrder`/`PendingOrderSnapshot` 에 `limit_price` 필드 자체가 없어 라이브 reconciler 까지 도달하지 못한다.

★백테스트와 라이브가 **똑같이** 그러므로 패리티 결함은 아니다. 그러나 TV 는 지정가 도달을 기다리므로 **TV 충실도**가 깨지고, 사용자는 경고를 라이브에서 보지 못한다(`live_signal.py` 에 `warnings` 참조 0건).
**Risk:** 🟡

---

### BL-525

**Title:** 라이브가 Track A(indicator + alertcondition) 전략을 어떻게 다루는지 정의되지 않았다
**Category:** Backend / trading (라이브 신호)
**Priority:** P3
**Trigger:** Track A 전략으로 라이브 세션을 열 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — run_live 는 아직 run_historical 만 호출하고, trading 라우터/서비스 어디에도 Track 판정·422 가드가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-entry-parity codex G1 검증 #7 (재현 확인)

**원인 / 영향:** `run_live`(`event_loop.py`)는 `run_historical` **만** 호출한다. Track A 를 처리하는 `run_virtual_strategy` 는 `TrackRunner._dispatch_table["A"]` 로만 도달한다. 즉 라이브 경로에 Track 분기가 없다. `fill_timing=next_bar_open` 이 Track A 에서 무시된다는 경고도 라이브에서는 발생하지 않는다(그 코드에 도달하지 않으므로).

★이번 스프린트가 "없는 경로에 계측을 붙이지 않기 위해" W3-3 을 폐기하면서 발견했다. **영원히 0인 카운터를 만들지 않은 대신, 그 경로가 무엇을 하는지는 여전히 미정의다.**

**권장 접근:** 라이브 세션 등록 시 Track 을 판정해 미지원이면 422 로 막거나(BL-478 (c) 선례), `run_live` 에 Track 분기를 넣는다.
**Risk:** 🟢

---

### BL-527

**Title:** ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다
**Category:** pine_v2 / 라이브 신호
**Priority:** P2 (잠재 — 실데이터 미재현)
**Trigger:** 기대치 정확도가 판정 입력으로 쓰이기 전
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — pnl_by_trade 는 여전히 t.id 단일 키 dict 이고 거짓 전제 주석도 그대로이며, catch-up 정상 경로도 유지된다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-outcome-parity 적대 검증

**원인 / 영향:** `event_loop.py` 의 `pnl_by_trade` 는 `strategy_state.closed_trades` 를 `t.id` 로 인덱싱하는데, 그 id 는 Pine 진입 이름(`"PivRevSE"` 등)이라 **거래마다 재사용**된다. 같은 dict 키에 여러 청산이 들어오면 **마지막 값만 남는다.**

그 코드의 주석은 스스로 "마지막 bar event 만 signal 로 나가므로 실무상 1:1" 을 근거로 든다. 그런데 `tasks/live_signal.py` 는 `last_evaluated_bar_time` 이 있으면 **거의 항상** `emit_from_bar_time` 을 세운다 — **catch-up 은 예외가 아니라 정상 경로**다. 즉 그 주석의 전제는 이미 거짓이다.

★**결함은 잠재, 근거는 확정.** 실데이터에서 같은 배치 안 다중 close 오염은 재현되지 않았다(중복 PnL 1쌍은 25분 떨어진 별개 bar). 오염되면 `live_signal_events.realized_pnl` 이 틀리고, 그것이 BL-526 표면의 **기대치 입력**이다.

**권장 접근:** `pnl_by_trade` 키를 `(trade_id, exit_bar_index)` 같은 유일 키로 바꾸거나, 청산을 dict 가 아닌 리스트로 들고 이벤트 생성 시점에 짝을 맞춘다. ★**주석의 거짓 전제를 먼저 지워라** — 그 문장이 남아 있으면 다음 사람이 같은 판단을 반복한다.
**Risk:** 🟡 (기대치 정확도)

---

### BL-528

**Title:** 세션 창 밖 늦은 체결이 어느 표면에도 안 잡힌다
**Category:** Trading / 세션 스코프
**Priority:** P2
**Trigger:** 세션 손익 완결성이 필요할 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — created 창은 BL-536 진입 원장에만 열렸고, /state·손실한도·parity 3소비처는 여전히 terminal 창 기본값 + grace 없음 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-28 live-outcome-parity 실측

**원인 / 영향:** `SessionScope` 의 창은 `filled_at` 기준 반열림 `[started_at, ended_at)` 이고, 그 docstring 이 **"세션 종료 뒤 체결된 주문은 인접 세션이 있으면 그쪽으로, 없으면 어디에도 안 잡힌다"** 를 수용된 트레이드오프로 명시한다.

★**이번에 그 크기를 처음 쟀다** — 확정 청산 **27건 중 4건**(net **−0.5463**)이 어느 세션 창에도 안 들어간다. 그 4건은 `/state` 커브에도, outcome-parity 표면에도 나타나지 않는다.

부수 효과 — 기대 축(이벤트, `session_id` FK)과 실제 축(주문, `filled_at` 창)의 스코프 정의가 다르므로, 늦은 청산은 세션 A 에서 `expected_only`, 인접 세션 B 에서 `actual_only` 가 된다. **두 세션 패널이 서로 다른 답을 내되 둘 다 정상 응답**이다.

**권장 접근:** 창 상한을 `deactivated_at + grace` 로 두거나, 세션 귀속을 `filled_at` 이 아니라 **주문 생성 시점**(세션이 발주했다는 사실)으로 바꾼다. 후자가 의미상 맞지만 기존 소비처 3곳(`/state` 커브 · 손실 한도 알림 · 이번 표면)에 동시 영향이라 별도 스프린트가 필요하다.
**Risk:** 🟡

---

### BL-529

**Title:** 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다
**Category:** Trading / 데이터 위생
**Priority:** P2
**Trigger:** 전략 누적 지표를 신뢰해야 할 때
**Est:** S
**상태:** 🟡 부분 해결 — 스윕 uid dedup(BL-605)과 화면 문구는 구현됐다 — 잔여는 등록 시 uid 중복 경고와 이미 쌓인 거울 행/중복 계정 행 정리(사용자 승인). (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 동승 조건(전략 누적 지표를 신뢰해야 할 때) + [BL-477] 과 같은 사용자 결정. 거울 행 정리 경로가 2026-08-11 에 닫혔다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-28 live-outcome-parity 실측

**원인 / 영향:** `exchange_exits` 실측 — 계정 행이 2개(`0277c150` / `19a8166a`)인데 **둘 다 같은 Bybit uid** 를 가리켜 같은 청산이 계정별로 2행 적재된다. 한쪽은 32행 전부 `matched_order_id IS NULL` 이다.

- 세션 단위 표면은 **무해**하다(한 세션 = 한 계정).
- 전략 누적과 계정 진단에서 **`unattributed_count` 가 부풀려진다**(실측 37 중 다수가 거울 행).
- `aggregate_closed_pnl` 은 계정 스코프라 안전하지만, 계정을 안 거는 새 집계를 만들면 즉시 2배가 된다.

**권장 접근:** 등록 시 거래소 uid 중복을 감지해 경고하거나, 스윕을 uid 단위로 dedupe 한다. 화면은 그때까지 "계정 행마다 중복 적재될 수 있음" 을 명시한다(이번 스프린트에서 문구 반영).
**Risk:** 🟢

**🔁 재확인 (2026-07-29, live-close-completeness 리뷰):** 거울 행이 **실재로 재확인**됐다 — `exchange_exits` 분류 집계에서 `ours` **30행**과 `unknown` **30행**이 건수뿐 아니라 **net 합계까지 −27.6870 으로 동일**했다. 같은 청산이 계정 행 2개에 각각 적재된다는 BL 본문의 진단과 일치한다.

★이 확인은 live-close-completeness 플랜(W4)이 "등재 내용 보강만" 으로 약속했으나 **그 PR 에서 누락**됐고, 사후 Spec 리뷰가 잡아 여기 반영한다. 스코프를 줄인 게 아니라 **적어놓고 안 한 것**이므로 같은 누락이 반복되지 않도록 기록해 둔다.

---

### BL-531

**Title:** parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery
**Category:** Refactor / Trading
**Priority:** P2
**Trigger:** parity 지표를 더 붙일 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — \_to_scope 36필드 수동 평탄화·private \_session_scope_where import·linked/confirmed 술어 중복이 모두 그대로 남아 있다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #496 코드리뷰 (Standards 축)

**원인 / 영향:** 순수 파생 `ParitySummary`(중첩 dataclass)를 응답 `OutcomeParityScope`(36 필드 평탄화)로 `_to_scope` 가 손으로 옮긴다. 지표 1개를 추가하면 **5파일**(순수 모듈 · 서비스 매핑 · 스키마 · zod · 패널)을 편집해야 한다.

부수로 같은 리뷰가 지적한 것 — `linked_order_scope` / `confirmed_close_scope` 가 5개 술어 완전 동일한데 이름만 둘(`parity_repository.py:337-355`), `_derive_ledger_values` 가 `len != 1` 을 걸러낸 뒤 1원소 합산 루프를 돈다, `load_account_ledger_diagnostics` CTE 가 안 쓰는 3열을 select 한다, `parity_repository.py:31` 이 `order_repository` 의 private `_session_scope_where` 를 import 한다.

**권장 접근:** 평탄화를 유지할지(직렬화 단순) 중첩을 노출할지 먼저 정한다. 유지한다면 매핑을 필드 목록 하나에서 파생시켜 손 편집 지점을 1곳으로 줄인다. `_session_scope_where` 는 공개 이름으로 승격하거나 `SessionScope` 에 메서드로 얹는다.
**Risk:** 🟢 (읽기 전용 파생)

---

### BL-532

**Title:** `_sum_decimals` 사본이 `PARITY_DECIMAL_CONTEXT` 밖에서 돈다
**Category:** Refactor / 금융 정확도
**Priority:** P2
**Trigger:** 다음 parity 손질 시
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — \_sum_decimals 사본이 여전히 2벌이고 리포지토리 호출부 4곳(92·159·169·174)은 localcontext(PARITY_DECIMAL_CONTEXT) 밖 그대로다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #496 코드리뷰 (Standards 축, 평가자 재현 확인)

**원인 / 영향:** `_sum_decimals` 가 `outcome_parity.py:130` 과 `parity_repository.py:59` 에 **2벌** 있고, 후자의 호출부(`:92, 159, 169, 174`)는 `localcontext(PARITY_DECIMAL_CONTEXT)` **밖**이다. 전자는 모든 산술을 `prec=50` 으로 감싼다.

★**PR #496 이 `gates-and-traps.md` 에 직접 추가한 규칙**("금융 파생 모듈은 `localcontext(Context(prec=50))` 로 감싸라")과 그 PR 자신이 어긋난다. `Numeric(18,8)` 값의 단순 합산이라 실무 위험은 낮지만, 규칙을 세운 PR 이 그 규칙을 안 지키면 다음 사람이 규칙을 안 믿는다.

**권장 접근:** 사본을 지우고 `outcome_parity._sum_decimals` 를 import 하거나, 리포지토리 호출부를 같은 컨텍스트로 감싼다.
**Risk:** 🟢

---

### BL-533

**Title:** 종료 세션 목록이 같은 엔드포인트를 두 쿼리 키로 조회해 미러 state 를 낳는다
**Category:** Frontend UX / 상태관리
**Priority:** P2
**Trigger:** 코크핏 손질 시
**Est:** XS
**출처:** 2026-07-29 PR #496 코드리뷰 (Standards 축)
**상태:** ✅ **Resolved (2026-08-09, W3)** — 단 **쿼리 키 통일은 이미 끝나 있었다.**
`trading-cockpit.tsx:73` 은 [BL-423] 회차부터 `useLiveSessions(true)` 였고
`live-sessions-list-query-dedupe.test.tsx` 가 그것을 래칫으로 잡고 있었다. 즉 이번에 남은
일은 **미러 state 제거 하나**다 — 통일이 끝났는데도 `selectedInactiveSession` 이 남아
같은 사실을 두 곳에 두고 있었다. red→green = 미러 참조 **4곳 → 0곳**(`useState` 1 ·
`selected` 폴백 1 · `handleSessionSelect` 1 · `LiveSessionForm.onSuccess` 1).

★**미러를 지우자 기존 테스트가 빨개졌고, 그게 진짜 결함을 드러냈다.** mock 이
`{ id: "session-1", is_active: true }` **활성 1건만** 돌려줘서 `include_inactive=false` 를
흉내내고 있었다 — 「최근 종료 세션 선택」테스트는 **미러 덕분에만** 통과하고 있었다.
mock 을 실제 쿼리대로 고치고(비활성 1건 추가), 그 위에 **음성 대조**를 새로 넣었다:
쿼리가 활성만 실어 오면 같은 클릭이 상세가 아니라 중단 안내로 떨어진다. 이 대조가
변이 M 의 상설판이다 — 없으면 그 테스트는 「종료 세션이 목록에 있든 없든 통과」로 읽힌다.

★**부수 — 소스 래칫의 오탐면을 고쳤다.** 그 래칫은 파일 원문을 훑어서 **주석에
`useLiveSessions()` 를 인용하기만 해도** 빨개졌다(이번에 실제로 물렸다). 문장을 비틀지
않고 술어를 고쳤다 — 주석을 걷어낸 뒤 매칭한다. 판별력 실측: 산문 인용 5/5 green ·
코드를 실제로 되돌리면 red.

검증 = vitest **209파일 / 1301테스트** green. `chromium-authed` 는 10건 실패지만
**stash 대조로 전건 기존 실패**임을 확인했다(이 워크트리에 BE `:8111` 이 없다).

**원인 / 영향:** 코크핏은 `useLiveSessions()`, 세션 리스트는 `useLiveSessions(true)` 를 쓴다. 같은 엔드포인트를 **서로 다른 쿼리 키로 2회** 조회하고, 그 때문에 `selectedInactiveSession` 미러 state 가 필요해졌다. 코크핏도 `true` 를 쓰면 미러가 사라진다.

같은 리뷰가 지적한 FE 위생 — 패널이 isLoading / isError / !data **3단 early-return 캐스케이드**(`outcome-parity-panel.tsx:309-338`, `frontend.md` §3 은 Suspense+ErrorBoundary 권장), `parsedNumber(value)` 는 값처럼 읽히는 이름(`toFiniteNumber` 등이 낫다).

**권장 접근:** 코크핏도 `include_inactive=true` 로 통일하고 미러 state 제거.
**Risk:** 🟢

---

### BL-534

**Title:** 외부 오라클 테스트가 27 leg Decimal 합산을 실제로 실행하지 않는다
**Category:** Test infra / Trading
**Priority:** P2
**Trigger:** parity 산술을 손댈 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 오라클 총계를 관측 1건에 몰고 26건을 0으로 채우는 구조·테스트 이름 모두 그대로다(:47, :54-66). (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #496 코드리뷰 (Spec 축)

**원인 / 영향:** `test_outcome_parity.py:55-78` 이 SQL 오라클 **총계를 관측 1건에 통째로 넣고** 나머지 26건을 0 으로 채운다. 총계와 실효 비용률(0.05526%)은 맞지만 **27건 Decimal 합산 자체는 이 오라클이 검증하지 않는다.**

★조인·스코프 정확성은 `test_parity_repository.py` 와 실 DB 대조가 담당하므로 커버는 있다. 다만 이 테스트의 이름(`test_reproduces_sql_oracle_totals...`)이 실제보다 넓은 것을 주장한다.

부수 — 리뷰가 함께 지적한 스코프 이탈 2건은 **의도된 것으로 판단해 기각**한다: (a) 종료 세션 도달 경로(W5)는 화면 검증이 "기능에 도달 불가" 를 잡아 추가한 것으로 dev-log 에 근거가 있다, (b) `/state` 폴링 계약 변경은 신규 표면이 폴링하지 않도록 한 결과이고 핸들러는 무변경이다. 다만 **둘 다 G1 동결 스펙 밖이었다** — 스코프 확장 시 동결 문서를 갱신하는 절차가 없었던 것이 진짜 문제다.

**권장 접근:** 27개 관측에 실제 leg 값을 넣어 합산을 재현하거나, 테스트 이름을 실제 검증 범위에 맞게 좁힌다.
**Risk:** 🟢

---

### BL-541

**Title:** 세션 행이 아예 없는 포지션은 여전히 앱에서 못 닫는다 (웹훅 경로 · 거래소 수동 거래)
**Category:** Backend / trading
**Priority:** P2
**Trigger:** 웹훅으로 포지션을 열기 시작할 때, 또는 `no_owning_session` 이 실제로 관측될 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 차단 사유만 있고 원장 귀속 폴백은 미구현(position_service 는 세션 없으면 즉시 no_owning_session), Trigger 관측도 아직 없다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 live-orphan-close (BL-537 재현이 남긴 잔여)

**원인 / 영향:** `Order.strategy_id` 가 `nullable=False` + FK RESTRICT(`models.py:172-178`)라 청산 원장 행에 전략이 반드시 필요하다. 세션에서 그걸 얻으므로 세션 행이 없으면 `no_owning_session` 으로 막힌다(`position_service.py:303`). 해당 클래스는 **웹훅 경로**(`router.py:99-183` 은 `LiveSignalSession` 없이 주문을 낸다)와 거래소에서 직접 연 포지션이다.

★**아직 실측된 적이 없다.** 2026-07-29 재현에서 `no_owning_session` 은 **한 번도 안 났다** — 세션 행은 비활성이어도 영구히 남기 때문이다. 그래서 이번 스프린트에서 **의도적으로 짓지 않았다**(BL-536 이 경고하는 "측정되지 않은 필요 위에 설계" 회피).

**권장 접근:** 실제로 관측되면 착수한다. 그때도 `Order.strategy_id` nullable 화는 금지 — `CumulativeLossEvaluator`(`kill_switch.py:96-105`)가 전략별로 합산하므로 NULL 행은 kill-switch 에 **영구 불가시**가 되고, `order_service.py:161-175` 소유 게이트에 `None` 분기를 뚫어야 한다. 대신 **원장 귀속**(해당 계정·심볼의 `filled` 진입 주문의 distinct `strategy_id` 가 정확히 1개일 때만 채택 — `exit_attribution.py:129-130` 의 보수 규칙)이 마이그레이션 0 이다.
**Risk:** 🟡

---

### BL-538

**Title:** 발산 알림 본문이 **모든 카테고리에 "전략 수정 후 재활성화 필요"** 라고 처방한다 (포지션 불일치엔 틀린 처방)
**Category:** Backend / trading (운영 알림)
**Priority:** P2
**Trigger:** 운영 알림을 사람이 신뢰해야 할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 메시지가 여전히 stage 분기 없는 단일 f-string 이고 '전략 수정 후 재활성화 필요' 하드코딩, remedy 원소 부재. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #497 사후 리뷰 (Spec 축)

**원인 / 영향:** `_alert_live_divergence`(`tasks/live_signal.py`)의 메시지가 단일 f-string 이고 **stage 분기가 없다**:

```
f"{reason}({stage}/{category}) 감지 — 세션을 비활성화했습니다(...). 전략 수정 후 재활성화 필요."
```

`reason` 은 카테고리별로 갈리지만 **처방 문장은 하드코딩**이라, 포지션 계열(`gap_resync_position_mismatch`, `position_direction_mismatch`)에도 "전략을 고쳐라" 가 나간다. 실제 필요한 조치는 **거래소 포지션과 엔진 상태 대조 후 재활성화**다.

★**선재 결함이다** — `gap_resync_position_mismatch` 가 이미 같은 문장을 받고 있었고, PR #497 이 카테고리를 하나 더 추가하면서 노출면이 넓어졌다. #497 은 사유·제목만 정정했다(메타데이터 등재).

**권장 접근:** `_PREFLIGHT_CATEGORY_METADATA` 에 처방(remedy) 원소를 추가하거나 `_alert_live_divergence` 에 kwarg 로 주입한다.
**Risk:** 🟡 (사람이 잘못된 조치를 하게 만든다. 자동 경로 무영향)

---

### BL-539

**Title:** 방향 불일치 유예가 **시간 경계가 없다** — 평가가 드문드문하면 오래된 strike 가 살아남는다
**Category:** Backend / trading (라이브 발산 감지)
**Priority:** P3
**Trigger:** 발산 가드를 다시 손댈 때
**Est:** S
**상태:** ✅ Resolved — strike 에 봉 시각(\_DIRECTION_STRIKE_BAR_KEY)을 실어 TTL·평가공백 판정까지 구현됐고 전용 테스트가 집행한다 (2026-08-09 status-triage-mass 코드 대조)
**출처:** 2026-07-29 PR #497 사후 리뷰 (Spec 축)

**원인 / 영향:** `_DIRECTION_MISMATCH_KEY` 플래그는 `upsert_state` 에 도달한 tick 에서만 갱신된다. `no_new_bar` / `claim_lost` 로 조기 반환하는 tick 은 갱신하지 않으므로, 오래 전 `True` 가 그대로 남는다. 그 뒤 **진짜로 한 bar 만에 풀릴 skew** 가 와도 첫 관측에 차단될 수 있다.

★계약이 "판정된 **평가** 2회" 이지 "연속 2회 **bar**" 가 아니다. 1m 세션에서는 둘이 사실상 같지만 5m/15m/1h 나 재기동 후에는 갈린다.

★**반대 방향 위험도 같이 있다** — 판정 불가(거래소 자격증명 파손 · `position_size` 결측)가 오래 이어지면 strike 가 **ON 으로 고착**한다. 그 상태에서 처음 판정되는 `direction` 이 즉시 세션을 죽인다. 즉 시간 경계 부재는 **양방향**이다: 오래된 strike 가 살아남거나(과잉차단), 판정 불가가 길어지면 유예가 사실상 사라진다.

**권장 접근:** 플래그에 관측 bar_time 을 함께 실어 인접 bar 일 때만 strike 로 인정한다. 그러면 두 방향이 동시에 닫힌다.
**Risk:** 🟢 (과잉차단 방향 — 세션이 죽지 돈이 새지 않는다)

---

### BL-540

**Title:** `live_signal.py` 의 반복 3종 — deactivate 의식 6회 · provider+creds 조립 4회 · divergence category 가 맨 `str`
**Category:** Refactor / trading
**Priority:** P3
**Trigger:** 이 파일을 다시 크게 손댈 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — get_state 는 1회로 줄었으나 deactivate 의식 중복(헬퍼로 쪼갰지만 본문 동일·테스트가 7건 동결)·provider+creds 5곳·category 맨 str 이 그대로다 (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-29 PR #497 사후 리뷰 (Standards 축)

**원인 / 영향:**

- **deactivate 의식**(`deactivate` → `commit` → `rows == 1` → sweep → `publish_realtime` → counter → alert)이 한 함수 안에서 **6회** 반복된다. 한 갈래만 고치면 나머지가 조용히 갈린다.
- **provider + credentials 조립**(`BybitFuturesProvider` + `EncryptionService` + `ExchangeAccountService` + `get_credentials_for_order`)이 **4곳**(`:316` `:449` `:1437` `:2155`)에 거의 동일하게 반복된다.
- **divergence category 가 맨 `str | None`** — 합법 집합이 `common/metrics.py` 주석에만 있고 `== "direction"` 리터럴과 metric label 로 재인코딩된다. 이 저장소는 StrEnum-vs-plain-str 로 이미 물렸다(BL-453).
- 같은 tick 에 `sess_repo.get_state(sess.id)` **2회**(발산 판정 · equity curve).

★전부 **선재 패턴**이고 PR #497 이 각각 하나씩 보탰다. 지금 리팩터링하면 diff 가 커져 리뷰가 어려워지므로 분리한다.

**권장 접근:** deactivate 의식을 헬퍼로 접고, category 를 StrEnum 으로 승격하고, `get_state` 를 한 번만 읽어 두 소비처가 공유한다.
**Risk:** 🟢

---

### BL-545

**Title:** ★gap-resync 안전 게이트가 5% 수량 허용치를 물려받아, 구 게이트가 막던 불일치를 통과시킨다
**Category:** Backend / trading (가용성 ↔ 안전 트레이드오프)
**Priority:** P2
**Trigger:** 조건부 진입 세션이 실자금으로 가기 전 / 부분체결이 흔해질 때
**Est:** S
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (P1 제기 → 오케스트레이터가 코드 대조 후 P2 로 강등)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 guards-blind-spots 가 `tol = max(qty_step, larger*0.001)` 로 **구현했다가 되돌렸다**(변이 4/4 red 를 통과했는데도). codex 최종 리뷰가 **P1 2건을 냈고 둘 다 숫자로 재현됐다** — 아래 ★2026-08-10 절이 정본이다. **권장 접근 자체가 불완전하다**: 양자화 오차는 **leg 수**에 비례해 쌓이는데 판정은 순포지션 하나만 받는다. ★단 **「leg 수를 못 구한다」는 거짓이다** — 2026-08-10 review-and-merge 가 `_carried_position_size` 에서 반증했다(아래 절)
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**원인 / 영향:** BL-544 가 gap-resync 판정을 `exchange_positions == [] and carried_flat`(무관용)에서
`_classify_position_divergence(carried, exchange) is None`(엔진↔거래소 일치)로 일반화했다. 그런데 그 함수는
같은 방향 크기차가 `_POSITION_SIZE_REL_TOL = 0.05` 이하면 `None` 을 준다(`live_signal.py:227`, `:303`).
따라서 엔진 `0.028` / 거래소 `0.029` 처럼 **실제로 0.001 어긋난 상태가 "일치" 로 통과**한다.
구 게이트는 거래소가 non-empty 이기만 하면 죽였으므로, 이 부류는 **새로 통과하게 된 것**이다.
그리고 이후 정상 tick 의 발산 감지도 `size` 를 **counter 만 올리고 차단하지 않는다**(`:1765-1772`).

★**그 5% 를 그냥 좁히면 안 된다.** 값에 실측 근거가 있다 — 엔진 `position_size` 는 float 누적
(실측 `-0.029910810628287526`)이고 거래소는 step 양자화(실측 `0.029`, BTC linear step 0.001)라
**의도가 같아도 두 값은 절대 같아지지 않는다.** 측정된 양자화 폭 = 3.45%. 좁히면 seed 가 정렬되지
않아 BL-544 자체가 무효가 된다.

★★**2026-08-10 정정 두 건 — 위 문단의 숫자와 근거가 정확하지 않다.**

⑴ **「3.45%」는 관측값이 아니라 상한이다.** `live_signal.py:237` 주석도 같은 수를 적는데,
`:799` 의 식은 `larger = max(|engine|,|exchange|)` 로 나눈다. 실측 쌍
(`-0.029910810628287526` vs `-0.029`)의 **실제 비율은 3.045%** 다
(`0.000910810628287526 / 0.029910810628287526`, python 확인). 3.45% 는 `step / 거래소수량`
(`0.001/0.029`)으로 **코드가 계산하지 않는 양**이다. 둘 다 맞지만 답하는 질문이 다르고,
**좁히기를 제약하는 수는 상한인 0.0345** 다.

⑵ **「좁히면 BL-544 가 무효」는 테스트 근거로는 훨씬 약하다.** 하한을 구속하는 테스트는
**정확히 하나**(`test_live_signal_instrument_parity.py` 의 `test_quantization_is_not_a_divergence`)
이고, BL-544 의 gap-resync 테스트는 전부 engine/exchange 가 **정확히 같다**(`0.029`/`0.029`).
tick-oracle 픽스처 11종도 0~5% 밴드에 하나도 없다 ⇒ `[0.0345, 0.05)` 로 좁히면 **red 0건**이다.
주장은 프로덕션 거동에 대해서는 참이고 「테스트의 벽」으로는 거짓이다.

★★★**⑶ 「size 비례 → step 파생」이라는 권장 접근 자체가 불완전하다. 구현했다가 되돌렸다.**

`tol = max(qty_step, larger * 0.001)` 로 구현했고 표적 변이 **4/4 가 red**(배선 변이 포함)였다.
그런데 codex 최종 적대 리뷰가 **P1 2건**을 냈고 **둘 다 python 으로 재현**됐다:

| 입력                                                      | 종전 축 (5%)             | step 축                   | 무엇이 문제인가          |
| --------------------------------------------------------- | ------------------------ | ------------------------- | ------------------------ |
| pyramiding 10 leg · 엔진 net `5.999108…` / 거래소 `5.990` | tol 0.29996 → **None**   | tol 0.005999 → **`size`** | **정상 세션을 죽인다**   |
| 최소 수량 · 엔진 `0.001` / 거래소 `0.002`(1 lot 차이)     | tol 0.00005 → **`size`** | tol 0.001 → **None**      | **진짜 불일치를 삼킨다** |

⇒ 내 변경은 **아파야 할 곳에서 더 관대해지고, 관대해야 할 곳에서 더 엄격해졌다.**
뿌리는 하나다 — **절삭 오차는 `leg 수 × step` 으로 쌓이는데 `_classify_position_divergence` 가
받는 것은 순포지션 하나뿐이다.** 엔진은 leg 를 절삭하지 않고 거래소는 leg 마다 절삭하므로
(`providers.py:404` `amount_to_precision`), 누적 드리프트는 포지션 크기가 아니라
**체결 횟수**를 따라간다. 순포지션 하나만 보는 어떤 문턱도 두 실패 모드를 동시에 못 막는다.

★★★**2026-08-10 review-and-merge 정정 — 「순포지션이 leg 수를 안 들고 있다」는 판정부에서 거짓이다.**
2축 리뷰 Spec 축이 제기했고 코드로 재현했다. 판정이 쓰는 순포지션을 만드는 것은
`_carried_position_size`(`backend/src/tasks/live_signal.py:712-746`)인데, 그 함수는
`open_trades` **리스트를 leg 단위로 순회**하며 leg 마다 `qty` 를 읽어 net 을 누적한다.
⇒ **leg 수도 leg 별 수량도 이미 그 자리에 있다.** 필요한 것은 새 데이터 원천이 아니라
**반환값을 `net` 하나에서 `(net, legs)` 로 넓히는 것**이다 — 「입력 자료의 문제」라는 진단은
맞지만 정확히는 **「자료가 없다」가 아니라 「있는 자료를 버리고 있다」**이다. 비용이 다르다.
★단 **tick 관측부에는 진짜로 없다** — `live_signal.py:925-938` 이 다루는 `position_size` 는
스칼라다. **두 자리를 섞지 마라.**
★**되돌림 커밋(`e17a082c`)의 인용 2건이 모두 빗나갔다** — `strategy_state.py:861` 은 [BL-104]
pyramiding cap 주석이고, `providers.py:403` 은 `load_markets()` 다(절삭은 `:404`).
엔진 무절삭의 근거는 특정 줄이 아니라 **파일 1,321행 전체에 `amount_to_precision`·`quantize`
호출이 0건**이라는 사실이다(2026-08-10 실측). **근거를 줄 번호로 적을 때 그 줄을 열어 봐라.**

★**되돌린 이유** — 첫 행은 `gap_resync_position_mismatch` 사망 경로이고, 그것은 역대 실격
11건 중 **2건**의 라벨이다. 소크가 도는 중에 사망률을 올릴 수 있는 변경을 넣지 않는다.

**다음 착수자에게** — 후보는 「leg 별 거래소 정밀도로 정규화한 기대 순포지션과 비교」다
(codex 처방). 그러려면 판정이 순포지션이 아니라 **leg 목록**을 받아야 하므로
`_classify_position_divergence` 의 시그니처 문제가 아니라 **입력 자료의 문제**다.
★**그리고 그 자료는 이미 있다**(위 2026-08-10 정정) — 착수 지점은
`_carried_position_size` 의 반환을 `(net, legs)` 로 넓히는 것이고, 그 함수는 이미 leg 를 돈다.
**「원리상 불가능」으로 읽고 포기하지 마라.**
되돌린 구현·테스트·변이 하네스는 git history 에 있다(`3cc33b75`·`dca6b11a` 와 그 revert).

**권장 접근:** 상대 허용치를 **거래소 수량 step 에서 파생**시켜라 —
`tol = max(qty_step, size * rel_tol_small)` 같은 형태. step 은 `_reconcile_conditional_entries` 가
이미 `market["precision"]["amount"]` 로 가져온다(`live_signal.py:638`). 그러면 "양자화 1틱" 은
통과하고 "부분체결 잔량" 은 통과하지 못한다. 대안: gap-resync 에만 더 좁은 별도 문턱을 두고
정상 tick 의 관측용 문턱과 분리한다.

**2026-08-08 실측.** `size` 발산은 `14:17:49.558` ~ `15:08:49.945` 동안 **51분 연속 52건**
발화했지만 게이트 C3 실격 목록에는 **0건**이었다 — `size` 는 실격 라벨이 아니다.

그 52건의 `exchange_position` 은 엔진 값의 정수배였다 — `0.087 = 0.029 × 3` ·
`-0.145 = -0.029 × 5`. 이 계열은 「양자화 1틱」도 「부분체결 잔량」도 아니고, 다른 호스트의
포지션이 같은 계정에 얹힌 것이다. 근인은 BL-634 로 등재했다.

따라서 이 BL 의 문턱 설계는 그대로 유효하다. 다만 `size` 를 관측 전용으로 두는 정책 자체가
별도 질문이며, 이번 회차는 그 수리를 하지 않았다.

**Risk:** 🟡 (통과한 불일치는 다음 주문이 그 위에 얹히지만, 5% 이내라 규모는 제한적)

---

### BL-546

**Title:** 원장→엔진 seed 경계에서 `Decimal` 수량·가격이 `float` 로 강등된다 (Decimal-first 하드 규칙 위반)
**Category:** Backend / pine_v2 · trading 경계
**Priority:** P2
**Trigger:** 엔진 내부 수치 표현을 손댈 때 / 큰 notional 을 다룰 때
**Est:** M (엔진 전반이 float 기반이라 국소 수정으로 안 끝난다)
**상태:** ⏳ 대기 (트리거 미도래) — seed 경로가 여전히 float(fill.filled_quantity/price) 로 강등하고, Trade.qty 도 float이며 dust 상한을 고정하는 테스트가 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (확정)

**원인 / 영향:** DB `Numeric(18,8)` 인 `filled_quantity`/`filled_price` 가 seed 경로에서 `float` 로
변환된다(`live_signal.py` seed leg 조립 · `strategy_state.py` `Trade.qty: float`). 예:
`9999999999.99999999` 는 float 왕복 뒤 `10000000000.0`. seed 포지션의 수량·진입가·증거금 계산에
반올림값이 들어간다. `AGENTS.md` 와 `backend/AGENTS.md` §2 의 "금융 숫자는 Decimal,
float 금지" 를 형식상 위반한다.

★**이 변경이 새로 만든 문제는 아니다** — `StrategyState` 는 원래 float 기반이고(`Trade.qty: float`),
`run_live` 의 모든 수치 입력이 이미 float 다. seed 는 **새 변환 지점을 하나 더 만들었을 뿐**이다.
그래서 국소 수정이 아니라 엔진 수치 표현 결정 사안이다.

**권장 접근:** (a) 엔진 경계에 변환 지점을 한 곳으로 모으고 그 자리에 정밀도 손실 상한을 단언한다,
또는 (b) `StrategyState` 의 금액·수량을 `Decimal` 로 올린다(대공사 — 별도 스파이크로 크기부터 재라).
현실적 1차: **BTC 급 수량·가격 범위에서 float 왕복 오차가 `_POSITION_DUST`(1e-8) 아래임을 테스트로
고정**하고, 그 가정이 깨지는 심볼(고가·고정밀)에서 경고하게 한다.
**Risk:** 🟢 (현재 취급 범위에서는 오차가 dust 아래일 가능성이 높다 — 단 측정된 적 없다)

---

### BL-548

**Title:** (P3) `OutcomeParityPanel` 이 375px 에서 페이지 본문 가로 스크롤 24px 을 만든다
**Category:** Frontend / 반응형
**Priority:** P3
**Trigger:** 모바일 폭 점검 시
**Est:** XS
**출처:** 2026-07-30 conditional-entry-alignment 게이트 4 (MCP playwright 실브라우저)
**상태:** ✅ **Resolved (2026-08-09, W3)** — 단 **적힌 24px 은 재현되지 않았고 결론만 살아남았다.**
2026-08-09 실측(슬롯 11 dev + `chromium-authed`, 375×812): 실측 픽스처
`MOCK_OUTCOME_PARITY` 위에서는 **수리 전에도 0px** 이다. 아래 §재판정 참조.

**원인 / 영향:** `/trading` 에서 세션 상세를 열면 body 가 24px 가로 스크롤된다(375px 기준).
인과 분리 실측 — 상세 닫힘 **0px** / 상세 열림 **24px** / 상세 열림 + `outcome-parity-panel`
`display:none` **0px**. 대조군 `/dashboard` 는 **0px**.

★**이번 회차 회귀가 아니다.** `outcome-parity-panel.tsx` 는 BL-526(PR #496, 2026-07-29)의
컴포넌트이고 이번 diff 가 만지지 않았으며, 그 경로는 이번 변경 **이전에도 도달 가능**했다.

**권장 접근:** 패널 안 넓은 콘텐츠를 자기 `overflow-x:auto` 컨테이너로 감싼다 — 같은 화면의 세 표는
이미 `div.table-wrap{overflow-x:auto}` 로 그렇게 하고 있다. 그 패턴을 패널에도 적용.
**Risk:** 🟢

**§재판정 (2026-08-09, W3)**

★**24px 은 이미 남이 고쳤다.** 2026-07-30 관측 당시 값 타일은 원장 Decimal 원문을 그대로
그렸고, [BL-607](#bl-607)(2026-08-06)이 `DecimalValue` 반올림을 넣으며 그 경로를 닫았다.
그래서 오늘 실측 픽스처 위에서는 **수리 전에도 0px** 이다 — 이 BL 을 「그대로 재현 → 수리」로
잡았으면 **판별력 0 인 테스트**를 초록으로 만들고 닫았을 것이다.

★**남은 경로는 `sub` 캡션이다.** `DecimalValue` 는 값 타일에만 걸려 있고,
`undecomposed_net` · `expected_only_gross` · `actual_only_net` · `ledger_only_net` 네 필드는
`sub` 로 **원문 그대로** 보간된다. 51자리 Decimal 은 끊을 수 없는 한 낱말이라 자기 블록을
넘긴다. 인과 분리 실측 — 상세 닫힘 **0** / 열림 **191** / 열림 + 패널 `display:none` **0**.

★**처방을 `overflow-x:auto` 에서 `break-words` 로 바꿨다.** 넘치는 것이 표가 아니라 **텍스트**라서다.
`frontend/AGENTS.md` §10 완료 체크리스트도 둘을 갈라 놓았다 — 표는 `overflow-x-auto` 래퍼,
텍스트는 `truncate` 또는 `break-words`. 스크롤 컨테이너를 씌우면 캡션을 읽으려고 가로 스크롤을
해야 한다. 변이 M — `break-words` 4곳을 지우면 **191px 로 복귀**(실측).

회귀 픽스처는 `MOCK_OUTCOME_PARITY_LONG_LEDGER_SUB` 로 **따로 두었다** — 실측 픽스처는 이 네 자리가
마침 `"0"`·`"20"` 이라 결함을 못 본다.

---

### BL-550

**Title:** (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다 (계정 스코프 표로만 보인다)
**Category:** Frontend / live-sessions
**Priority:** P3
**Trigger:** 죽은 세션의 포지션을 세션 단위로 대조해야 할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — OpenPositionsTable 은 여전히 is_active 필터된 activeSessions 만 받는다 — 비활성 세션 per-session 대조 UI 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 conditional-entry-alignment (BL-423 잔여 중 의도적 defer)

**원인 / 영향:** `OpenPositionsTable`(`trading-cockpit.tsx:342`)은 `activeSessions` 만 받는다.
BE `GET /live-sessions/{id}/positions` 는 비활성 세션에도 200 을 주지만 FE 가 부르지 않는다.

★**의도적으로 미루었다** — 계정 스코프 표(`AccountPositionsTable`)가 이미 고아 포지션을 보여주고
청산까지 되며(2026-07-29 BL-537 실측), 비활성 세션마다 per-row 쿼리를 붙이면 폴링 비용이 붙는다.
**Risk:** 🟢

---

### BL-551

**Title:** (P3) 라이브 세션 상세 진입이 URL 파라미터가 아니라 클라이언트 state — 딥링크·새로고침 불가
**Category:** Frontend / live-sessions UX
**Priority:** P3
**Trigger:** 세션 상세를 링크로 공유하거나 새로고침 보존이 필요할 때
**Est:** S
**상태:** ✅ Resolved — 2026-08-10 fe-shareable-urls. 선택이 `?session=<id>` 로 옮겨갔고 딥링크·새로고침 보존이 실 DB 로 실증됐다. `backend/src` 0줄.
**출처:** 2026-07-30 conditional-entry-alignment (BL-423 잔여 중 defer)

**원인 / 영향:** `trading-cockpit.tsx` 의 `useState` 가 선택 상태를 쥔다. `useSearchParams`
사용처 0. 새로고침하면 선택이 사라지고 특정 세션 상세로 링크할 수 없다.
부수: e2e 가 쓰는 `/trading?tab=live-sessions` 의 `tab` 파라미터는 **읽는 코드가 없는 유물**이다.
★본문의 줄 인용 `:76-77`(인덱스 표는 `:82`)은 **2026-08-10 실측에서 둘 다 틀렸다** — 실제는 `:67` 이었다.
**Risk:** 🟢

### ✅ 2026-08-10 fe-shareable-urls — 종결

`selectedId` 를 `searchParams.get("session")` 로 파생시키고, 선택 시
`router.replace(url, { scroll: false })` 로 URL 에 싣는다(선례 = `backtest-list.tsx` 의
`pushStatus`/`pushSort`). 쓰기 지점은 목록 클릭과 `LiveSessionForm.onSuccess` 둘 다이며 같은
함수를 쓴다. **`useState` 미러를 두지 않는다** — [BL-533] 이 같은 이유로 미러를 지운 자리다.

★**`{ scroll: false }` 는 장식이 아니다.** Next 16 의 `replace` 는 기본으로 페이지 최상단으로
스크롤한다(설치된 문서 `use-router.md` §"Disabling scroll to top"). 세션 목록은 화면 §07 이라
인자 하나짜리 호출이면 클릭마다 꼭대기로 튄다. **실측** — 클릭 직전 `scrollY` **7866**,
클릭 직후에도 **7866 불변**(`?session=` 은 붙고 상세는 열림).

★**목록을 못 읽은 상태를 「밀려났다」로 오진하지 않는다.** `isPending` 중에는 딥링크 진입 시
「밀려났습니다」가 한 프레임 번쩍이고, `isError` 이면 **네트워크 실패를 종료 이력 20건 제한으로
잘못 설명**한다. 둘 다 별도 분기로 갈랐다(codex G1 발견 2).

★**목록 밖 id 는 원리상 열 수 없다** — `GET /live-sessions/{id}` 가 없고 목록은 활성 전체 +
최근 종료 20건뿐이다. 그래서 기존 `live-session-stopped-notice` 로 떨어지는 것이 정답이고,
그것이 이 회차의 음성 대조다. **backend 0줄이 성립하는 이유가 이것이다.**

**검증** — vitest `trading-cockpit.test.tsx` 18건(**신규 7** — 2026-08-10 정정, 11→18 이다) ·
e2e `live-session-deeplink.spec.ts` 3건 ·
표적 변이 **7종 전건 판별**(음성 대조 = 안내 문구 변경, 아무것도 안 뒤집음) · sha256 복원 확인 ·
MCP playwright 실 DB 검증(위 7866 실측 · 목록 밖 id 음성 대조 · 375px 가로 오버플로 0 · 콘솔 error 0).

★**내 테스트가 잘못된 계약을 고정하고 있었다** — 처음 쓴 `toHaveBeenCalledWith("/trading?session=…")`
는 인자 하나짜리 `replace` 를 기대했고, 그 형태가 바로 위 결함이다. codex 설계 검증을 **코드 쓰기
전에** 건 것이 이것을 잡았다. 구현이 옳게 고쳤다면 내 시험이 그것을 red 로 만들었을 것이다.

---

### BL-547

**Title:** ★원장 seed 는 **그 tick 한 번만** 산다 — 다음 tick 에 조용한 고아가 될 수 있다 (아직 실측된 적 없음)
**Category:** Backend / trading (BL-544 잔여)
**Priority:** P2
**Trigger:** ★`qb_live_position_divergence_total{category="exchange_only"}` 이 **실제로 오르는 것이 관측될 때**
**Est:** M
**상태:** ⬜ Open — seed 는 여전히 gap tick 1회에만 계산되고 `_qb_ledger_seed_since` watermark 는 레포에 0건 — 처방 미착수. ★**2026-08-11 ledger-truth: 트리거가 도래했다** (아래 판정 줄).
**트리거 판정:** ~~미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)~~
→ ★★★**2026-08-11 ledger-truth — 도래. `/metrics` 실측이 「미도래」와 본문 서술을 함께 반증했다.**

서버 `backend/.metrics` **1회** 스냅샷(2026-08-11 · prometheus multiproc 직독):

```
qb_live_position_divergence_total{category="exchange_only"} 3.0
qb_live_position_divergence_total{category="size"} 52.0
qb_live_position_divergence_total{category="direction_transient"} 5.0
qb_live_position_divergence_total{category="engine_only_awaiting_trigger"} 1.0
```

트리거는 「`…{category="exchange_only"}` 이 **실제로 오르는 것이 관측될 때**」다. **3.0 이다** ⇒ 도래.

★★**본문의 「그 counter 는 역사적으로도 한 번도 오른 적이 없다」도 같이 반증됐다.** 그 문장이
「미도래」 판정의 근거였으므로 **판정과 근거가 함께 무너진다.** 「외생 조건이라 우리 의지로
만들 수 없다」는 참이지만, **외생 조건은 이미 발생했다** — 만들 필요가 없었다.

★**동시에 상속받은 진단 하나를 기각한다.** 2026-08-11 착수 계획은 이 자기모순의 근거로
「같은 파일이 그 카테고리 **21건**을 기록한다」를 들었다(현 `backlog.md` §divergence 분류 표).
**그 표는 이 counter 가 아니다** — 표는 특정 분석 창의 이벤트 행 집계이고 라이브 counter 는
**3.0** 이다. 결론(도래)은 같지만 **근거가 달랐다** ⇒ 「남이 준 실측도 실측이 아니다」.

★**음성 대조 — 모든 판정이 뒤집힌 것은 아니다.** 같은 스냅샷에서 [BL-499] 의
`cancel`/`cancel_raced`/`cancel_stalled` 는 **여전히 부재**다(`qb_live_conditional_cancelled_total`
은 `reason="replaced"` 150.0 **하나뿐**). ⇒ [BL-499] 의 「미도래」는 **유지**다. 스냅샷이
전건을 도래로 밀어 올리지 않았다는 것이 이 판독에 판별력이 있다는 증거다.
**출처:** 2026-07-30 conditional-entry-alignment — 워커 `bl544` 가 자기 구현의 한계로 스스로 올린 것(codex G1 F6), 오케스트레이터가 코드 대조로 확인

**원인 / 영향:** `ledger_seed` 는 `if requires_gap_resync:` **안에서만** 계산된다(`live_signal.py:1678` 초기화 · `:1720` 계산). 다음 tick 은 공백이 아니므로 원장을 읽지 않는다. 재생이 그 진입을 스스로 다시 만들지 못하면 엔진은 **다시 flat** 이 되고, 그때 발산은 `exchange_only` 로 분류돼 **counter 만 올리고 세션을 죽이지 않는다**(`live_signal.py:1765-1772`). 즉 이론상 **시끄러운 사망이 한 tick 뒤 조용한 고아로 바뀔 수 있다.**

★**다만 2026-07-30 soak 3 leg 에서 발현하지 않았다.** 세 leg 모두 재생이 포지션을 스스로 재현했고 `exchange_only` 는 **부재(0) 를 유지**했다(그 counter 는 역사적으로도 한 번도 오른 적이 없다 — 세션이 gap 판정에서 먼저 죽어 발산 감지까지 도달한 적이 없었기 때문). 완화 요인 하나 — seed 를 **마지막 bar 직전**에 심으므로 그 tick 의 Pine 이 포지션을 보고 청산을 낼 수 있다. 전략이 닫으면 그 자리에서 해소된다.

★[BL-541](#bl-541) 과 같은 프레임으로 둔다 — **측정되지 않은 필요 위에 상태 저장소를 짓지 않는다.**

**권장 접근 (관측되면):** seed 창 watermark 를 `last_strategy_state_report` JSONB 에 `_qb_ledger_seed_since` 로 남기고(`_qb_position_epoch`(`:237`) / `_qb_direction_mismatch_seen`(`:233`) 과 같은 자리·같은 방식, 마이그레이션 0), 매 tick 그 창의 원장에서 seed 를 **재도출**한다. 창의 순포지션이 0 이 되면 marker 를 지워 자기 종결시킨다. **남는 구멍:** 부분 청산은 창이 inadmissible 이 되어 seed 가 끊긴다.
**Risk:** 🟡 (관측되면 🔴 — 조용한 고아는 관리 주체가 없다)

---

### BL-553

> ### ⏳ **유지 (2026-07-30 close-mismatch-soak) — ★사전조건이 불완전했음이 밝혀졌다**
>
> **공백 33분 03초**(`18:35:03Z` → `19:08:06Z`)를 **장전된 상태에서** 열었다
> (armed=1, `buy 0.087 @ 64795.6`). 즉 직전 회차가 지정한 사전조건을 **충족했다.**
> 그런데 `applied` 는 **또 미발화**했고 `already_open` 이 +1(1.0 → 2.0) 됐다.
> 누적 **62분57초 + 33분03초 = 96분에서 0회.**
>
> ★★**"장전" 만으로는 부족하다.** `already_open` 은 **엔진 원장에 이미 열린 트레이드가 있어
> seed 가 불필요했다**는 뜻이다. `applied` 에 도달하려면 **장전 + 엔진 flat** 이어야 한다 —
> 공백 중 트리거가 체결돼 **엔진이 모르는 포지션이 생겨야** seed 가 의미를 갖는다.
>
> ★**그리고 그것이 PbR 로는 구조적으로 어렵다.** `s1_pbr` 은 stop-and-reverse 라 거의 항상
> 포지션을 들고 있다(flat 구간이 사실상 없다). **5회 연속 미발화의 이유가 이것으로 설명된다.**
>
> **다음 회차 설계:** 전략을 바꿔라. `strategy.close` 로 **flat 으로 돌아가는 구간이 있는 전략**
> (예: `s4_hma_curvature`)에서, flat + 장전 상태를 확인한 뒤 공백을 연다.
> ★**PbR 로 재시도하지 마라 — 같은 0 을 6번째로 얻는다.**

<details><summary>이전 판정 (2026-07-30 live-entry-completeness)</summary>

> ### ⏳ **유지 — 단 이유가 정확해졌다**
>
> 이번 soak 공백 2회(16분35초 + 18분22초, 누적 34분57초)에서도 `applied` **미발화**.
> 직전 28분 + 이번 34분57초 = **누적 62분57초에서 0회**.
>
> ★★**그런데 "시장이 안 움직였다" 가 아니다.** 대기 stop 이 **실제로 트리거됐고, 하필 공백 밖
> (leg 3)에서** 일어났다 — 화면의 진입가 **64609.1** = 공백 2 의 `trig=64610`.
> 공백 중 거래소를 외부 raw HMAC 오라클로 **5회** 찍어 내내 `Untriggered` 임을 실측했다.
>
> → **다음 회차 설계:** 공백을 **30분+** 로 가져가면 트리거가 공백 안에 들어올 확률이 오른다.
> 확인 신호에서 **구조화 로그의 `trade_ids` 는 빼라** — 포매터가 `extra` 를 렌더하지 않아
> 관측 불가다(정본이 이미 경고). metric `{outcome="applied"}` + 엔진 `open_trades` 변화로 본다.

</details>

**Title:** ★`outcome="applied"`(원장 seed **주입**)가 실주행에서 한 번도 밟히지 않았다 — 단위테스트로만 증명됨
**Category:** Backend / trading 검증 공백
**Priority:** P2
**Trigger:** 다음 soak / 조건부 진입 전략을 오래 굴릴 때 (기회주의적 확인)
**Est:** XS (검증만 — 코드 변경 없음)
**상태:** ⏳ 대기 (트리거 미도래) — 코드 변경 없는 실주행 관측 항목 — 계측은 그대로 있고 관측된 outcome 은 no_basis 뿐, applied>0 근거 0건. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 소크 창 미완(soak-gate rc=2 · C1 46.24h/168h). PASS 만 도래다([ADR-024]) (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 conditional-entry-alignment soak 3 leg

**원인 / 영향:** BL-544 의 핵심 기전은 둘이다 — (1) **판정 완화**(엔진↔거래소 순포지션 일치) (2) **원장 seed 주입**. soak 3 leg 이 3/3 생존했지만 **세 번 다 (1) 로 살았다** — 재생이 포지션을 스스로 재현해 seed 가 생략됐다(`already_open` / `no_basis` / `inadmissible`). `applied` 를 밟으려면 **대기 조건부 주문이 공백 중에 트리거**돼야 하는데 누적 공백 ~28분 동안 일어나지 않았다(시장 변동 의존이라 강제할 수 없다).

★따라서 현재 증거 수준은 **비대칭**이다 — 판정 완화 = 실주행 실증 / seed 주입 = 단위테스트 + 표적 변이(멱등·마지막 bar Pine 가시성·기본값 report dict 불변)까지. 원래 BL-544 실패(2026-07-29)가 정확히 seed 주입이 필요한 케이스였으므로 이 공백은 실질적이다.

**권장 접근:** 코드 변경 없음. 다음 soak 에서 (a) 공백을 **더 길게**(15분+) 가져가 대기 stop 이 트리거될 확률을 올리거나, (b) 변동성이 큰 구간을 골라 재현한다. 확인 신호는 `qb_live_gap_ledger_seed_total{outcome="applied"} > 0` + 구조화 로그 `live_signal_gap_ledger_seed` 의 `trade_ids` 비어 있지 않음. **관측되면 이 BL 을 닫고 BL-544 의 검증을 완성으로 표기한다.**
**Risk:** 🟡 (기전이 틀렸다는 증거는 없다 — 다만 실주행 증거가 없다)

---

### BL-556

**Title:** `final-gates.sh` 가 `pnpm e2e`(chromium 4건)를 집행하지 않는다 — CI e2e 잡에는 있다
**Category:** DX / 게이트 집행
**Priority:** P2
**Trigger:** 다음 회차 게이트 실행 전
**Est:** XS
**출처:** 2026-07-30 live-entry-completeness
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — `final-gates.sh` §4 에
라벨 **`e2e chromium`** 으로 추가했다. 순서는 `chromium → design-canon → authed`(싼 것 먼저).
★**이것만 영역 판정(`has_fe`)에 건다** — `chromium` 은 BE·DB·인증·소크 무결합이라
`frontend/` diff 0 이면 잴 것이 없다. 나머지 둘은 종전대로 무조건 돈다(`authed` 는 backend
변경도 문다). 영역과 서버(정체성 프로브)는 직교하므로 중첩 if 2단이고, **세 분기
(`--skip-e2e` / 프로브 OK / 프로브 실패) 전부에서 같은 3행이 같은 순서로** 나온다.
검증 = §4 블록을 `awk` 로 원본에서 추출해 `record`/`skip_gate`/`run_gate`/`curl` 을 스텁으로
바꿔 6조합 전수 실행(손으로 베끼면 원본이 아니라 사본을 시험하게 된다).
★★**4건이 아니라 3건이다** — `playwright test --project=chromium --list` 실측
`Total: 3 tests in 1 file`. 「4건」은 아래 **권장 접근**의 「4 passed」에서 나와 문서 5곳
(`status.md` · 이 파일 3곳 · `generator-evaluator-pipeline.md`)에 복제된 오기였다.
★같은 회차에 `FE build`(`:177`)의 fail-open 도 닫았다 — 다른 네 FE 게이트가 다 갖고 있는
`|| [ -z "$BASE" ]` 가 거기만 없어 `merge-base` 실패 시 **조용히 skip** 됐다.

**원인 / 영향:** `.github/workflows/ci.yml` 의 e2e 잡은 `pnpm e2e`(project=chromium, ~~4건~~ **3건**) ·
`pnpm e2e:design-canon` 을 돌린다. 그런데 `scripts/final-gates.sh` 는 `e2e:design-canon` 과
`e2e:authed` 만 돌리고 **`pnpm e2e` 는 어느 게이트에도 없다.**
`generator-evaluator-pipeline.md` §G7 표가 그것을 "로컬 상시 게이트에 없는 CI 전용 스텝" 으로
명시하는데도 집행되지 않는다. CI 는 러너 미할당이라 판단 근거가 로컬뿐인데 그 로컬에 구멍이 있다.

**권장 접근:** 게이트 체인에 추가한다(`PLAYWRIGHT_BASE_URL` 필수, 정체성 프로브 뒤에).
이번 회차는 CONTROL 이 수동으로 메웠다 — **4 passed**.
**Risk:** 🟡

---

### BL-557

**Title:** (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳
**Category:** Backend / 계측
**Priority:** P3
**Trigger:** 그 게이지로 무언가를 판단하기 전
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — Gauge 그대로이고 inc 1곳(order_service:457) vs dec 17곳 비대칭 유지 — created/terminal Counter도 terminal 단일 훅도 없다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 live-entry-completeness (기존 BL 의 새 증거)

**원인 / 영향:** 이미 등재된 "inc/dec 계약이 multiprocess 에서 절대값을 보장하지 못한다" 의
**새 증거 2건**이다. (a) 직전 회차는 "0 인데 실제 1"(양의 편향)이었는데 이번엔 **음수 -2.0** —
편향이 양방향이다. (b) ★**구조적 비대칭** — `inc` 지점은 **1 곳**(`order_service.py:432`),
`dec` 지점은 **약 18 곳**(`tasks/trading.py` 8 · `tasks/live_signal.py` 3 ·
`conditional_entry_janitor.py` 3 · `websocket/{reconciliation,state_handler}.py` 2 · `router.py` 1 …).
1:18 이면 어느 dec 하나가 중복 발화해도 음수로 샌다.

**권장 접근:** dec 를 단일 지점(terminal 전이 훅)으로 모으거나, Gauge 를 버리고
`created - terminal` 두 Counter 의 차분으로 렌더한다. **음수는 그 자체로 계약 위반 신호다.**
**Risk:** 🟢 (관측 왜곡. 머니-패스 영향은 없다)

---

### BL-558

**Title:** retCode 를 `error_message` 에 싣는 경로가 **동기 1곳뿐** — 비동기 확정 거절이 코드 미상이 된다
**Category:** Backend / trading (계측 타당성)
**Priority:** P2
**Trigger:** 거절 코드로 채널을 가를 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 구조화 코드 컬럼이 없고(models.py 에 error_message 문자열뿐), WS·submission 경로는 여전히 평문이라 retCode 정규식 파싱에 의존한다. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-30 live-entry-completeness (적대 검증 렌즈1)

**원인 / 영향:** retCode JSON 을 원문에 싣는 것은 동기 `provider_failure: {ccxt}`
(`tasks/trading.py:432`) **하나뿐**이다. WS(`state_handler.py:241` `ws_rejected: <rejectReason>`) ·
reconciler(`reconciliation.py:240`) · janitor(`conditional_entry_janitor.py`) ·
sweep(`live_signal.py:2480`) · `exchange_rejected_at_submission`(`trading.py:549`) 는 전부 **평문**이라
`110092`/`110093` 같은 코드가 **복원 불가**다. 즉 비동기로 확정된 거절은 진입 완결성 도구에서
**"코드 미상"** 으로 떨어진다.

★**이번 측정의 알려진 한계**이고 도구 출력에 그렇게 명시돼 있다
(_"`unparsed` 는 '거절 아님' 이 아니다"_).

**권장 접근:** 거절 확정 경로 전부가 **구조화된 코드 필드**를 남기게 한다.
`error_message` 문자열 파싱에 의존하는 설계 자체가 취약하다 — 별 컬럼이면 마이그레이션 1이다.
**Risk:** 🟡 (채널 분해의 분자를 과소·오분류한다)

---

### BL-559

**Title:** (P3) 진입 완결성 도구 잔여 3건 — 세션 목록 절단 감지 · 사문 라벨 · janitor probe 전이
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 그 경로가 실측될 때
**Est:** S
**상태:** ✅ **Resolved (2026-08-11 gate-surface)** — ①③ 은 구현 완료였고 ②는 **기각**한다. 「사문 라벨을 제거하라」는 처방이 코드 대조로 반증됐다 — 그 라벨이 사문인 것은 **결함이 아니라 설계 의도의 결과**이고, 지우면 마지막 방어선이 발화하는 날의 유일한 증거가 사라진다 (근거는 아래 §2026-08-11)
**트리거 판정:** 도래 — 잔여 ②에는 조건이 없다. Trigger 「그 경로가 실측될 때」는 **③ janitor probe** 를 가리키는데 상태줄이 ①③ 구현 완료를 적었고, 권장 접근은 ②를 「라벨 제거」로만 적었다(조건 없음). 코드 실측 — 사문 라벨 `reduce_only_entry_ignored` 가 `live_signal.py:1098` · `conditional_entry_planner.py:408` · `metrics.py:561` 3곳에 잔존 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-07-30 live-entry-completeness (적대 검증 잔여)

**원인 / 영향:** 세 건 모두 확인됐으나 이번 스코프 밖으로 남겼다.

1. `live_signal_session_repository.list_overlapping_window` 가 200 제한인데 `limit+1` **절단 감지가 없다**
   — 주문 쪽은 그 규율을 지키는데 세션 쪽만 빠졌다(같은 PR 안의 불일치).
2. `plan_drop{reduce_only_entry_ignored}` 라벨이 **구조적 사문** — 우리 조건부 진입은
   `reduce_only=False` 로만 발주되므로 발화 경로가 없다.
3. janitor 의 probe 부재 → `rejected` 전이가 **체결을 유실로 뒤집을 수 있다**
   (`fetch_order_by_client_id(trigger=True)` 가 history 를 포함하는지 **[확인 필요]**).

**권장 접근:** 1 은 즉시 고칠 수 있다(주문 쪽 패턴 복사). 2 는 라벨 제거. 3 은 **실측되면** 착수.
**Risk:** 🟢

**2026-08-11 gate-surface — ②를 기각한다 (코드 0줄).**

전제는 맞다. 라벨은 프로덕션에서 **발화할 수 없다.** 단 그 이유가 결함이 아니다 —
**상위 필터가 두 겹**이라서다:

| 층                                              | 무엇을 하나                                                   |
| ----------------------------------------------- | ------------------------------------------------------------- |
| `order_repository.py:294`                       | SQL `WHERE Order.reduce_only IS FALSE` (로컬 행 경로)         |
| `live_signal.py:1653`                           | 거래소 응답 경로에서 `linked_order.reduce_only` 면 `continue` |
| `conditional_entry_planner.py:404` (**남긴다**) | 위 둘이 깨져도 취소 대상으로 안 삼는다 — **마지막 방어선**    |

★**그 분기는 죽은 코드가 아니라 의도된 안전망이다.** 코드 주석이 직접 적었다 — 「상위 계층이
필터를 잘못 넘겨 섞여 들어와도 … **사용자 손절을 지우는 것이 이 스프린트가 낼 수 있는 최악의
결함**이라 마지막 방어선을 여기 둔다」. 전용 회귀 테스트도 있다:
`tests/trading/test_conditional_entry_planner.py:194`
`test_reduce_only_resting_orders_are_never_cancelled` — 라벨을 지우려면 **이 테스트를 죽여야 한다.**

★**손익 계산이 명확히 한쪽이다.** 아끼는 것은 Prometheus series **1개**(8개 중 1)이고,
잃는 것은 상위 필터 회귀가 실제로 일어난 날 그것을 알아볼 **유일한 사유 문자열**이다
(allowlist 정규화 때문에 라벨을 빼면 `other` 로 수렴해 다른 드롭들과 구분이 사라진다).

⇒ **「사문이니 제거」는 사문인 이유를 안 본 처방이었다.** 원장이 「제거하라」고 말할 때도
코드에게 되물어라 — [BL-307]·[BL-703]·[BL-672]·[BL-704] 에 이은 **다섯 번째** 실증이고,
앞의 넷과 달리 이번엔 **처방 자체가 틀렸다**(전제는 맞았다).

---

### BL-564

**우선순위:** P3
**카테고리:** Tooling / docs (BL 감사 스크립트)
**Trigger:** `scripts/bl-audit.sh` 를 게이트 체인에 넣기 전
**Est:** XS
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — 처방 2건이 **이미 구현돼 있었고** Trigger 도 이미 도래했다. 코드 0줄.

★**2026-08-09 실측 — 이 항목은 「고쳐야 할 것」이 아니라 「닫혔다고 선언되지 않은 것」이었다.**
처방 3축을 코드로 대조했다:

| 처방                                 | 구현 위치                                    | 변이로 실증한 판별력                                                                |
| ------------------------------------ | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| 펜스·`<details>` 구간 건너뛰기       | `scripts/bl-audit.sh:114-120`                | 스킵 2줄을 제거하니 펜스 안 가짜 상태줄로 BL-627 이 **ACTIVE→RESOLVED 로 뒤집혔다** |
| 중복 상태줄을 경고가 아니라 **실패** | `:268-272` 보고 + `:288` `exit 1`            | 중복 1줄 주입 시 `중복 상태줄 1 건` + **exit 1**(주입 없으면 exit 0)                |
| Trigger 「게이트 체인 편입 전」      | `scripts/final-gates.sh:151`(+`:156` 하네스) | 이미 편입돼 있다 — Trigger 가 도래했고 조건도 갖춰졌다                              |

★**덤으로 원안보다 넓어져 있었다** — 파서는 태그를 **줄 머리에서만** 인정하고(산문 오탐 차단),
닫히지 않은 펜스·`<details>` 를 **서식 오류로 실패**시키며(`:283-284`), 중복 **섹션 헤더**까지 본다([BL-569]).
★본문의 「현재 `UNKNOWN 17` 정리와 함께」는 낡았다 — 2026-08-09 실측 **UNKNOWN 0**.

★**`bl-audit.sh` 가 코드펜스·`<details>` 안의 옛 상태줄을 SSOT 로 오인할 수 있다.**(← 아래는 등재 당시 원문)

**원인/영향.** 파서가 섹션 본문에서 첫 `**상태:**` / `**Status:**` 를 SSOT 로 잡는데,
코드펜스 안이나 `<details>`(폐기된 옛 판정을 접어두는 관용구) 안의 줄도 후보가 된다.
첫 줄이 이기고 **중복은 실패 조건에 포함되지 않는다**(경고만 출력).

★**실제로 이 회차에 `<details>` 를 처음 도입했다**(BL-553 의 이전 판정 보존). 지금은 그 안에
`**상태:**` 형식이 없어 오탐이 나지 않지만, 관용구가 퍼지면 조용히 뒤집힌다.

**권장 접근:** 파서가 ` ``` ` 펜스와 `<details>…</details>` 구간을 **건너뛰게** 한다.
중복 상태줄은 경고가 아니라 **실패**로 올린다(SSOT 는 하나여야 한다).
★현재 `UNKNOWN 17` 정리와 함께 처리하면 게이트 체인 편입 조건이 갖춰진다.

**Risk:** 🟢

---

### BL-565

**우선순위:** P2
**카테고리:** Backend / trading (라이브 청산 정합성)
**Trigger:** `strategy.exit` 을 쓰는 전략을 라이브로 돌리기 **전**
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-07-31 reversal-ledger-sync 에서 BL-560 을 고치며 **읽기만** 하고
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
범위 밖으로 남긴 항목. 코드 수정 0.
**출처:** 2026-07-31 reversal-ledger-sync (BL-560 4단계 판단)

★**거래소 bracket 이 이미 체결한 청산을 엔진이 또 보낸다 — BL-560 과 같은 모양이다.**

**원인/영향.** BL-560 은 `check_pending_fills` 의 close leg 가 broker 소유임을 확정하고 고쳤다.
`check_exit_fills` 는 **같은 성질인데 손대지 않았다**:

- `strategy_state.py:1068` — TP/SL/트레일링 leg 가 체결되면 `self.close(entry_id, ...)` 를
  **표시 없이** 부른다 → `action="close"` 이벤트 → `event_loop.py:513` 필터를 그대로 통과 →
  `live_signal.dispatch_event` 가 `reduce_only=True` 시장가 청산을 발주한다.
- 그런데 그 TP/SL 은 **거래소에 이미 걸려 있다.** 진입 주문이 `take_profit`/`stop_loss` 를
  실어 보내 Bybit 포지션 bracket(거래소-네이티브 OCO)이 되고(`tasks/live_signal.py:2865-2866`,
  부착 여부는 `:1389` `bracket_attached` 로 계측), 트레일링은 체결 후
  `set_trading_stop` 으로 따로 등재된다(`:2867-2871`).
- ⇒ 거래소가 먼저 청산해 **flat** 이 된 뒤 엔진이 다음 봉에서 그 체결을 재도출하고 청산 주문을
  또 낸다. 결과는 `110017 current position is zero` — BL-560 이 셌던 표의 **"무해" 30건 갈래**다.

**★단 무해가 보장되지는 않는다.** 같은 봉에서 전략이 재진입하면 그 사이 포지션이 반대편으로
차 있어 `same side` 가 된다 — BL-560 과 같은 위험 갈래로 넘어간다.

**★아직 실측되지 않았다 — 크기를 모른다.** 2026-07-30 soak 창의 전략(PbR)은 `strategy.exit` 을
쓰지 않아 `pending_exits` 가 비어 있고, `check_exit_fills` 는 그때 **즉시 return** 했다
(`strategy_state.py:1042`). 즉 그 창의 `position_zero` 0건은 **이 경로의 반증이 아니다.**
BL-563 이 같은 조건을 다른 각도에서 이미 경고하고 있다("`strategy.exit` 을 쓰는 전략이
등장하는 순간 이 숫자는 못 믿는다").

**권장 접근:** BL-560 과 같은 자리·같은 수단이다 — `check_exit_fills` 의 `close` 를
`broker_filled=True` 로 표시하면 dispatch 에서 빠진다(필드와 필터는 이미 있다).
★**단 먼저 재라.** BL-560 에서 배운 대로 bracket 부착이 **실제로** 되고 있는지가 전제인데
(`bracket_attached` 비율), 지금 그 counter 는 BL-563 의 귀속 오류를 안고 있다.
**BL-563 → 실측 → 이 항목** 순서를 지켜라. `strategy.exit` 전략 없이 고치면 검증 불가능한
수정이 된다.

★**`check_liquidations`(`strategy_state.py:901-`)는 다르다.** 그쪽 close 는 계속 dispatch 돼야
한다 — 엔진의 격리 청산가 모델은 **근사**이고 거래소가 실제로 청산했다는 보장이 없다.
`test_run_live.py:610` 이 그 계약을 이미 고정하고 있다. 같이 묶지 마라.

**Risk:** 🟡 (현재 관측 갈래는 무해하나 재진입이 겹치면 BL-560 과 동급)

---

### BL-567

**우선순위:** P2
**카테고리:** Backend / trading (체결 후속 훅 회수)
**Trigger:** 트레일링을 쓰는 전략을 라이브로 상시 운용하기 **전**, 또는
`terminal_hook_trailing_failed` counter 가 1건이라도 발화할 때
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-07-31 reversal-ledger-sync 에서 **한계로 명시하고 남긴 것**.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-07-31 reversal-ledger-sync (codex 3차 리뷰 [3] 후속)

★**`place_trailing_stop` enqueue 가 실패하면 그 주문의 트레일링은 영구 유실이다.**

**원인/영향.** BL-560 write-back 은 후속 훅 실패를 전이 성공과 분리해 삼킨다
(`tasks/live_signal.py:790-816`). **세 훅의 회수 범위가 갈린다**:

| 훅                                      | enqueue 실패 시 회수                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `_enqueue_closed_pnl_refresh`           | ✅ `trading.sweep_closed_pnl` 비트(`celery_app.py:141`)가 backfill                               |
| `_enqueue_conditional_reversal_measure` | 🟡 불필요 — 크기 분포 프로브라 1건 유실이 판정을 안 뒤집는다 (BL-562 가 이미 at-least-once 수용) |
| `_enqueue_trailing_if_intended`         | ❌ **없다**                                                                                      |

`place_trailing_stop_task` 는 `_enqueue_trailing_if_intended`(`tasks/trading.py:1141-1152`)
**한 곳에서만** 예약되고, 그 시점엔 행이 이미 `filled` 이라 다른 terminal 경로도 다시
오지 않는다. 결과 = **의도한 트레일링이 없는 채로 포지션이 열려 있다**(무방비).

★**삼키는 선택 자체는 옳다.** 삼키지 않아도 트레일링은 똑같이 유실되고, 거기에 더해
호출자의 전역 catch 가 그 tick 의 취소 루프까지 날린다. 삼키는 쪽이 순수하게 낫다.
문제는 **회수 경로가 없다**는 것이지 삼킨 것이 아니다.

★**이 한계는 write-back 이 만든 것이 아니다** — 같은 훅을 쓰는 기존 3 사이트
(`tasks/trading.py:526,867` · `conditional_entry_janitor.py:154`)도 동일하다. write-back 이
그 사실을 counter 로 **보이게** 만들었을 뿐이다.

**권장 접근:** `sweep_closed_pnl` 과 같은 모양의 비트 스윕 — `filled` + `trailing_stop IS NOT NULL`

- 포지션이 아직 열려 있는데 거래소에 트레일링이 없는 주문을 찾아 재예약한다.
  ★**먼저 재라.** `terminal_hook_trailing_failed` 가 실제로 발화하는지 모른다(구조적 가능성만
  확인했다). 발화 0 이면 이 항목은 비용 대비 가치가 없다 — BL-560 이 두 번 밟은 함정이다.

**Risk:** 🟡 (트레일링 미부착 = 무방비 포지션. 단 발생률 미측정)

---

### BL-568

**우선순위:** P2
**카테고리:** Backend / trading (조건부 진입 반전 계측)
**Trigger:** BL-562 의 **체결시점** 반전 분포를 근거로 무언가를 판단하기 전
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-01 ledgerhygiene 에서 실측. 아직 원인 미측정.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 ledgerhygiene (BL-562 착지 후 첫 실측)

★**BL-562 의 체결시점 반전 계측이 11건 중 10건을 못 쟀다 — 분류된 건이 0 이다.**

**원인/영향.** 메인 스택 worker 의 prometheus multiproc 레지스트리를 그대로 읽었다:

```
qb_live_conditional_reversal_filled_total{bucket="unmeasured_position_predates_order"}  10
qb_live_conditional_reversal_filled_total{bucket="not_reversal"}                         1
(그 외 버킷 = 없음)                                                                       0
```

같은 창의 **등재 시점** 축은 `qb_live_conditional_reversal_total{bucket="1x"} = 27` 로 살아 있다.
즉 축 자체는 돌지만 **체결시점 축만 91%(10/11)가 `unmeasured` 로 떨어진다.**
BL-562 는 "증명하지 못하면 버킷에 넣지 않는다" 를 원칙으로 삼았고 그 원칙은 옳다 —
문제는 **그 결과 남는 신호가 사실상 없다**는 것이다. 지금 이 counter 로는 반전이
일어나는지 아닌지를 말할 수 없다.

`unmeasured_position_predates_order` 는 `_reversal_bucket_at_fill`
(`backend/src/tasks/trading.py:1595`) 의 마지막 분기다 — 같은 방향 + `size < filled_quantity`
까지 온 뒤 `created_at < submitted_at - 2s` 면 여기로 떨어진다.

**[가정] anchor 가 구조적으로 뒤진다는 후보 1.** `position.created_at` 은
`_parse_position_created_at`(`backend/src/trading/providers.py:271-278`)이 Bybit raw
`info.createdTime` 에서 채우고, 그 주석이 **「최초 포지션 생성 시각 (ADD 시 불변)」** 이라고
못박는다. 포지션이 flat 을 거치지 않고 살아 있는 한 `created_at` 은 계속 최초 개시 시각이므로,
**나중에 등재된 조건부 주문의 `submitted_at` 보다 항상 앞선다.** 조건부 주문은 등재 후
트리거까지 대기하므로 이 시차는 분 단위로 벌어진다. ★단 이건 코드 대조로 세운 가설이고
**실측되지 않았다.**

★**먼저 재라 — 왜 anchor 가 항상 뒤지는가.** 10건 각각에 대해 `submitted_at` ·
`position.created_at` · `filled_quantity` · `position.size` 를 함께 남기고 차이를 봐라.
가설이 맞다면 `created_at` 이 **모든 건에서 동일한 한 시각**(그 포지션의 최초 개시)으로
수렴한다 — 그게 판별식이다. ★★**코드 대조로 뿌리를 정하지 마라** — BL-560 이 정확히 그렇게
두 번 틀렸다(2026-07-31 실주행이 코드 대조 가설을 반증).

**권장 접근:** 원인이 측정된 뒤에 고른다. anchor 후보는 최소 3개이고 셋 다 대가가 다르다 —
(a) 거래소 체결 시각 소싱(BL-375 와 같은 뿌리, 가장 비싸고 가장 정확),
(b) 주문 등재 시점의 포지션 스냅샷을 함께 저장해 delta 로 판정(계측 전용 경로에 쓰기가 생긴다),
(c) `created_at` 대신 포지션 `updatedTime` 을 보조 축으로(★BL-372 가 정확히 그 이유로
`timestamp` 를 버렸다 — same-side ADD 를 reopen 으로 오탐한다. **같은 함정을 반대편에서
다시 밟는 선택지다**).

★**계측 전용이라는 성질은 지켜라.** 이 경로는 주문을 내지 않고 행을 쓰지 않는다
(`trading.py:1610-1613`). 원인을 고치려고 여기에 쓰기를 넣으면 계측기가 머니-패스가 된다.

**Risk:** 🟢 (계측 전용 — 잘못된 값이 주문으로 이어지지 않는다. 단 BL-562 의 판정 근거가 비어 있다)

---

### BL-573

**우선순위:** P3
**카테고리:** Backend / trading (라이브 tick 중복 조회)
**Trigger:** `live_signal` tick 비용을 손댈 때, 또는 발산 감지와 reconcile 을 한 자리로 합칠 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-01 codex 적대 리뷰 #1 (CONTROL 코드 대조로 확인).
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 soak 후속 codex 리뷰

★**`engine_only` tick 마다 `list_resting_conditional_entries` 가 두 번 돈다 — 결과 공유가 구조적으로 불가능하다.**

**원인/영향.** 두 호출부가 `backend/src/tasks/live_signal.py:639`(발산 감지)와 `:946`(reconcile)에 있다.
**발산 감지가 reconcile 보다 앞서 돈다.** 그래서 뒤쪽이 앞쪽 결과를 물려받을 수 없고,
앞쪽이 뒤쪽을 위해 캐시하려면 tick 수명 동안 값을 들고 다녀야 한다 — 지금 구조로는 그 자리가 없다.

비용은 **인덱스 SELECT 1회/틱**이다(같은 `strategy_id` + `exchange_account_id` 조건,
`order_repository.py:267-281`). 작다. **P3 인 이유가 그것이다** — 정합성 문제가 아니라 중복이다.

★**좌표 주의.** 위 줄번호는 **메인/스테이지 기준**이다. `wt/ledgerhygiene` 워크트리에는
이 두 호출부가 아직 없다(`list_resting_conditional_entries` 가 `live_signal.py:880` 한 곳뿐).
발산 감지 경로는 W1 `divsplit` 작업이 들여온 것이다 — 브랜치를 확인하고 grep 해라.

**권장 접근:** 합치려면 **호출 순서를 먼저 정하라.** 발산 감지를 reconcile 뒤로 옮기면 공유가
가능해지지만, 그러면 감지가 reconcile 이 만든 상태를 보게 되어 **무엇을 재는지가 바뀐다.**
★**비용이 SELECT 1회이므로, 순서를 바꿔서까지 합칠 값어치가 있는지부터 판단해라.**
[BL-576](#bl-576) 과 같은 자리를 건드리므로 함께 보는 편이 싸다.

**Risk:** 🟢 (중복 읽기. 정합성 영향 없음)

---

### BL-574

**우선순위:** P2
**카테고리:** Backend / trading (조회 절단이 분류를 뒤집는다)
**Trigger:** 한 (strategy, account) 의 **동시 resting 이 20건을 넘긴 날**이 관측될 때 (아래 쿼리). 또는 `awaiting_trigger` / `unexplained` 분해를 근거로 쓰기 **전**
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 크기 측정 완료, 수리는 의도적으로 보류.** 2026-08-02 divergence-label-split.
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 soak 후속 codex 리뷰

★**`LIMIT 100` 이 세션 필터보다 앞서 걸려, 현 세션의 resting 주문을 놓치고 `awaiting_trigger` 를 `unexplained` 로 오분류한다.**

**원인/영향.** `order_repository.py:267-281` 의 조회는 **세션으로 필터하지 않는다** —
`state IN (pending, submitted)` + `trigger_price IS NOT NULL` + `reduce_only = false` +
`strategy_id` + `exchange_account_id` 로만 좁히고, `submitted_at ASC` 정렬에
**`.limit(100)`(`:279`)** 을 건다. 세션 스코프는 **호출부에서 사후에** 적용된다.

⇒ 같은 전략·계정에 **다른 세션의 미종결 조건부 주문 100건이 더 오래된 `submitted_at` 으로
앞서 있으면**, 현 세션의 resting 주문이 SQL 단계에서 잘려 나간다. 호출부는 "이 세션에 대기 중인
조건부 진입이 없다" 고 읽고, 그 tick 의 `engine_only` 를 **`awaiting_trigger` 가 아니라
`unexplained` 로 분류**한다.

★**이것이 [BL-566](#bl-566) 재판정의 20/9 분해를 직접 건드린다.** 편향 방향은 다행히
**보수적**이다 — 놓치면 `unexplained` 쪽으로 떨어지므로 "설명된 비율" 을 **과소** 평가한다.
즉 재판정의 69%는 하한이다. 그래도 **분류 근거가 조회 절단에 의존한다는 사실 자체가 결함**이고,
세션이 쌓이면 임계를 넘는 날이 온다.

### ★크기 측정 완료 (2026-08-02, divergence-label-split) — **수리는 값어치 근거로 보류**

~~★**아직 실측되지 않았다**~~ → **쟀다. 그리고 재는 축이 틀려 있었다.**

★★**`LIMIT 100` 은 달력일이 아니라 「동시각 resting」에 걸린다.** 그전에 인용되던
「(strategy, day) 당 최대 75건」은 **일별 생성 수**라 이 술어의 축이 아니다.

| 축                             | 값                                                                       |
| ------------------------------ | ------------------------------------------------------------------------ |
| 조건부 파이프라인 총량         | **264** = `cond` **255** + `condmkt` **9** — 전건 terminal               |
| 일별 생성                      | 07-28 **81** · 07-30 **59** · 07-31 **50** · 07-29 **43** · 07-27 **31** |
| ★**동시 미종결(resting) 최대** | **2** (per strategy+account) — 독립 4방법 일치                           |
| 날짜를 넘긴 미종결             | UTC **0** / **KST 2** ★타임존 의존                                       |

★**총량 술어 주의** — `trigger_price IS NOT NULL` 로 세면 **`condmkt` 9건이 통째로 빠진다**
(시장가 전환 주문은 정의상 `trigger_price` 가 NULL). 정본은 `idempotency_key` 의 kind 세그먼트다
(`entry_completeness.py` 의 `label="조건부 진입 (우리 cond/condmkt key 만)"`).
**이 함정은 2회차 연속 밟혔다.**

⇒ **`LIMIT 100` 이 절단한 적은 없다.** 단 여유는 「75 대 100」이 아니라 **「2 대 100」**이고,
★**그 2 는 부하 여유가 아니라 이 전략의 진입 신호 수(2종)가 만든 상한**이라 다른 전략으로 외삽할 근거가 없다.

**판단: 선제 경화를 지금 하지 않는다.** 실측 상한이 한계의 **2%** 라 `limit + 1` 절단 감지의
기대 이득이 없다. **되살릴 조건 = 아래 Trigger** — 한 (strategy, account) 의 동시 resting 이
**20건(한계의 20%)을 넘기면**(= 21 이상) 그때 경화한다.

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -At -F'|' -c "
WITH scoped AS (
  SELECT strategy_id, exchange_account_id, created_at,
         COALESCE(filled_at, now()) AS closed_at
    FROM trading.orders
   WHERE trigger_price IS NOT NULL AND reduce_only = false
     AND COALESCE(filled_at, now()) >= now() - interval '7 days'
), ev AS (
  SELECT strategy_id, exchange_account_id, created_at AS ts,  1 AS d FROM scoped
  UNION ALL
  SELECT strategy_id, exchange_account_id, closed_at  AS ts, -1 AS d FROM scoped
), r AS (
  SELECT strategy_id, exchange_account_id,
         sum(d) OVER (PARTITION BY strategy_id, exchange_account_id ORDER BY ts, d DESC
                      ROWS UNBOUNDED PRECEDING) AS run
    FROM ev)
SELECT strategy_id, exchange_account_id, max(run) FROM r GROUP BY 1,2 HAVING max(run) > 20"
```

★★**창 필터를 `created_at` 이 아니라 `closed_at` 에 건다** (2026-08-02 codex MAJOR#2 정정).
`created_at >= now()-7d` 로 거르면 **창 시작 전에 열려 창 안에도 살아 있던 주문(carry-in)이 통째로
빠져** 재고가 0 에서 시작한다. 술어의 실제 대상은 `pending`/`submitted` 상태의 지속이지 생성 시각이 아니다.
★**`>= 20` 이 아니라 `> 20`** — 문장이 「넘긴」이므로 20 은 발화하지 않는다(codex MINOR#3).

**2026-08-02 실행 결과 = 0행 (보류 유지).** ★판별력 확인 = 같은 쿼리의 `HAVING max(run) > 1` 이
`(전략 07a22564, 계정 19a8166a, max 2)` 를 돌려준다 — **창이 비어서 0행인 게 아니다.**

★**여기서는 `trigger_price IS NOT NULL` 이 옳다** — 이 술어가 재는 것은 `list_resting_conditional_entries`
가 실제로 거는 조건이고, 그 조회 자체가 같은 필터를 쓴다(`order_repository.py:275`). **총량을 셀 때와
절단 위험을 잴 때의 정본 술어가 다르다** — 이 구분이 위 함정의 반대편이다.

**권장 접근(되살릴 때):** 세션 술어를 **SQL 안으로** 내린다(`SessionScope` 관용구가 이미 있다).
그게 어려우면 최소한 **절단을 감지**해라 — `limit + 1` 로 가져와 `len(rows) > limit` 이면
분류를 `unexplained` 가 아니라 **`unmeasured_truncated`** 로 떨어뜨린다. ★후자가 이 레포의 기존
관용구다(`list_fills_since` 가 정확히 그렇게 한다, `order_repository.py:400-418`).
**모르는 것을 아는 것처럼 분류하지 마라** — BL-562 가 세운 규칙과 같다.

**Risk:** 🟢 (실측 상한이 한계의 2%. 단 그 분류가 [BL-566](#bl-566) 판정의 근거였으므로 Trigger 는 유지)

---

### BL-575

**우선순위:** P2
**카테고리:** Backend / trading (실패 후 세션 재사용 — fail-open 계약)
**Trigger:** 「발산 감지는 세션을 죽이지 않는다」를 근거로 쓰기 전, 또는 그 tick 의 DB 실패를 조사할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-01 codex 적대 리뷰 #5. ★**선재 패턴이고 회귀가 아니다.**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 soak 후속 codex 리뷰

★**SELECT 가 실패하면 같은 `AsyncSession` 을 rollback/savepoint 없이 계속 쓴다 — aborted transaction 이면 「fail-open · 세션을 죽이지 않는다」 계약이 깨진다.**

**원인/영향.** 발산 감지의 `except Exception` 은 예외를 삼키고 경고만 남긴다
(`live_signal.py:637-645` 근방). 하지만 `session` 을 rollback 하지 않는다. 실패가 asyncpg
트랜잭션을 **abort 시키는 종류**라면 그 tick 의 이후 DB 작업이 **줄줄이 실패**한다.
즉 이 `except` 가 막는 것은 **이 함수가 예외를 위로 던지는 것**뿐이고, 계약이 약속한
"세션이 안 죽는다" 는 여기서 보장되지 않는다.

★**코드가 이미 이 한계를 스스로 적어 놓았다** — `live_signal.py:630-634` 의 docstring 이
_"`session` 을 rollback 하지 않으므로 … 같은 tick 의 이후 DB 작업이 이어서 실패한다.
즉 '세션이 안 죽는다' 를 여기서 보장하지는 못한다"_ 라고 명시한다. **결함을 숨긴 코드가 아니라
정직하게 적어 두고 남긴 것**이다. 이 항목은 그 한계를 원장으로 끌어올린 것이다.

★★**선재 패턴 — 회귀가 아니다.** 같은 관용구가 `live_signal.py:2168` 의 `list_fills_since`
호출부에도 있다(docstring 이 그 자리를 직접 지목한다). **한 자리만 고치면 다른 자리가 남으므로
두 자리를 함께 봐야 한다.** 새 코드가 만든 문제로 오해하고 W1 변경을 되돌리지 마라 —
되돌려도 `:2168` 은 그대로다.

★**아직 실측되지 않았다** — aborted transaction 으로 tick 이 연쇄 실패한 관측은 없다.
이 SELECT 가 실패한 적 자체가 없다.

**권장 접근:** 두 자리에 같은 처리를 준다 — `begin_nested()` savepoint 로 감싸거나,
`except` 안에서 `await session.rollback()` 한다. ★**어느 쪽이든 「그 tick 을 계속 진행해도
되는가」를 먼저 정해라.** rollback 은 같은 tick 의 **앞선 미커밋 작업까지** 되돌리므로,
savepoint 없이 넣으면 조용히 다른 것을 잃는다.

**Risk:** 🟡 (fail-open 계약이 문서와 어긋난다. 단 발생 실측 0)

---

### BL-578

**우선순위:** P3
**카테고리:** Backend / trading (조건부 진입 발주 레이스 — 잔여)
**Trigger:** C1 잔여 거절이 **UTC 달력일 기준 3건 이상**인 날이 나오거나, 실자금 cutover 로 1건의 비용이 달라질 때.

★**집행 방법 — 문장이 아니라 쿼리다** (2026-08-01 codex MINOR: 「누가 무엇을 보고 판단하나」).
스프린트 kickoff 의 baseline 재측정 step 에서 **아래 한 줄을 함께 돌린다.** 별도 alert 는 만들지 않는다
(현재 크기 1건/2일에 상시 감시를 붙이는 것이 과하다 — 그 판단 자체가 이 BL 의 내용이다).

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -At -F'|' -c "
SELECT date_trunc('day', created_at AT TIME ZONE 'UTC')::date, count(*)
FROM trading.orders
WHERE reduce_only = false AND state = 'rejected'
  AND (error_message LIKE '%110092%' OR error_message LIKE '%110093%')
  AND created_at >= now() - interval '14 days'
  AND created_at >= timestamptz '2026-07-29 00:00+00'
GROUP BY 1 HAVING count(*) >= 3 ORDER BY 1"
```

**행이 하나라도 나오면 이 BL 을 되살린다.** 나오지 않으면 보류 유지.
기준선(2026-08-01 실측) = 07-27 **10** · 07-28 **20** · 07-29 **2** · 07-30 **0** · 07-31 **1**
— PR #493 이후 문턱을 넘은 날이 없다.

> ★★**2026-08-02 정정 — 이 Trigger 는 자기 기준선에 발화하고 있었다.** 마지막 줄
> (`created_at >= '2026-07-29'`)이 그 수정이다. 그전 형태는 14일 롤링 창이 기준선 07-27(**10**)·
> 07-28(**20**) 을 그대로 담아 **2행을 돌려줬고**, 위 결정 규칙이 「행이 하나라도 나오면 되살린다」라
> **2026-08-11 04:26 UTC 까지 매번 되살림을 지시하는 항상-참 판정식**이었다(verbatim 실행 확인).
> 원장에 **2026-07-31 18:39 UTC 이후 주문이 0건**이므로 새 증거 없이 발화한다.
> 정본 규율 = [`reference/operations/workflows/generator-evaluator-pipeline.md`](reference/operations/workflows/generator-evaluator-pipeline.md) §G1.1 규율 6.
> 수정 후 실행 = **0행**(= 보류 유지). 판별력 확인 = 같은 쿼리의 `HAVING count(*) >= 1` 이 07-29(**2**)·07-31(**1**)을 돌려준다(창이 빈 게 아니다).

**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 크기 측정 완료, 수리는 의도적으로 보류.** 2026-08-01 entry-completeness-rejudgement.
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-01 [BL-536](#bl-536) 재판정에서 유일하게 살아남은 채널(C1)의 잔여

★**조건부 진입이 `110092`/`110093` 으로 거절될 때 거래소는 정답(`current[...]`)을 함께 주는데 우리는 그 값을 버린다.**

**원인/영향.** `conditional_entry_planner.plan_reconcile` 은 plan 시점의 `reference_price` 로
돌파 여부를 판정한다(`conditional_entry_planner.py:404-416`). 판정과 발주 사이의 REST 왕복 동안
가격이 트리거를 넘어서면 거래소가 거절한다 — long stop 은 `110092`("expect Rising"),
short stop 은 `110093`("expect Falling"). 거절 메시지는
`trigger_price[627343000] <= current[627366000]` 처럼 **거래소 기준 현재가를 그대로 담고 있다.**

**측정된 크기 (2026-08-01, 원장 전 기간 5일치).**

| 축                        | 값                                                                    |
| ------------------------- | --------------------------------------------------------------------- |
| 거절 총량 (일자별)        | 07-27 **10** · 07-28 **20** · 07-29 **2** · 07-30 **0** · 07-31 **1** |
| `trigger↔current` 격차    | 최소 **0.0005%** · 중앙 **0.0236%** · 최대 **0.0710%** (33건 전건)    |
| 고유 의도 수              | **6** (= 33 거절은 재시도 폭주. 07-28 한 의도가 **18건**)             |
| 같은 의도가 나중에 체결됨 | **22 / 33 (66.7%)**, 지연 **3~54분**                                  |
| 현행 코드 구간(07-30~31)  | **1건 / 2일** · 조건부 파이프라인 109건 대비                          |

★**PR #493(2026-07-28 live-entry-parity)이 이미 20배 줄였다** — 실시간 perp last 기준가 +
돌파 시 시장가 전환. 재시도 폭주도 그 이후 사라졌다. **이 항목은 그 수리의 잔여다.**

**왜 이번에 고치지 않았나 (그 자리에서 판단했다).** 남은 수리 수단이 **시장가 전환**뿐인데
그건 머니-패스 변경이다. 측정된 이득은 **1건/2일**이고 그마저 **66.7%가 다음 bar 에 자연 회복**한다.
게다가 창 P 의 그 1건은 거절 **44초 뒤 세션이 `user_stopped`** 로 꺼져 회복 tick 자체가 없었다 —
「회복 안 됨」이 아니라 「회복할 기회가 없었다」다. 레포 규칙(「새 상태 저장소는 위험하므로
**크기를 본 뒤** 설계한다」, [BL-522](#bl-522))을 따라 **크기를 근거로 보류**한다.

**권장 접근(되살릴 때).** 새 상태 저장소를 만들지 마라. 거절 응답의 `current[...]` 를 파싱해
**그 tick 의 돌파 판정에 되먹인다** — 기존 `max_trigger_breach_pct` cap 을 그대로 통과시켜
시장가 전환 여부를 재평가한다. ★**전환 폭주 방지 가드를 함께 설계해라** — 07-28 에 한 의도가
18번 재시도한 이력이 있다.

**Risk:** 🟢 (현행 크기 1건/2일 · 자연 회복 66.7%. 단 되살릴 때의 수리는 머니-패스라 🟡)

---

### BL-580

**우선순위:** P2
**카테고리:** Backend / 관측 (계측 가드 잔여)
**Trigger:** ★`qb_metrics_mutation_failed_total` 의 **창 차분이 0 을 벗어나는 순간** 즉시 승격. 절대값 아님 — `CounterBasis.delta` 로만 읽는다. 또는 잔여 96곳 중 어느 자리가 머니-패스·알림·내구 쓰기 경계에 새로 닿게 될 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래) — 84곳.** 2026-08-04 direction-channel-decomposition 연장이 `_reconcile_conditional_entries` **12곳을 전건 수리**(96→84). 그 앞 회차가 발주 outbox 12곳 판정(수리 8 · 보류 4, 104→96). 그 앞이 25곳(129→104), 그 앞이 12곳(141→129). 2026-08-02 metric-guard-parity 에서 [BL-579](#bl-579) 분리.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-02 metric-guard-parity (18곳 수리 후 잔여)

가드 밖 mutation **84곳**(규칙 R1, `test_metric_guard_census.py` 가 정본이고 천장으로 고정).

★★★**2026-08-04 교훈 — 함수 하나를 통째로 한 형태로 취급하지 마라.** `_reconcile_conditional_entries`
12곳을 「전부 바깥 fail-open `except` 안」으로 판정했는데 **기존 회귀 테스트가 반증했다**:
`unrepresentable_key`(`:1817`)는 **안쪽 발주 `try`** 안이라 예외가 `stage="conditional_place"`
(= 발주 실패)로 **오기록**되고 있었다 — 발주를 시도한 적도 없는데. 해악은 두 갈래로 갈라 적어라:
**(a) 안쪽 `except` → 오기록** / **(b) 바깥 fail-open → 조용한 중단 + 호출자는 `outcome="success"`**.
★직전 회차도 「전부 commit 뒤라 같은 형태」가 8곳 중 1곳에서 틀렸다. **두 회차 연속 같은 병이다.**
★**H8 은 아니다** — 어느 갈래든 예외는 `continue` 와 `execute` 를 함께 건너뛴다.

★**주입 판정이 안 되면 「판정 보류」로 적고 하네스를 짓지 마라.** 이 회차에 시도한 주입 2건은
**판별력 0**(하나는 기존 A3 와 같은 갈래로 샘 · 하나는 `precision_error` 가 자체 `except` 에
잡혀 바깥까지 안 감)이라 **커밋하지 않고 지웠다.** 구조적 방어는 주입이 아니라 **census AST 동결**이다.

### ★2026-08-03 — 「뺀 이유」 4곳이 **전건 반증**됐다

아래 표의 첫 줄(명시 4곳)은 **코드 독해**였다. 고장 주입으로 재니 **4곳 전부 H1**(성공한 외부
작용이 실패로 보고)이었다. 같은 회차 스윕이 5곳을 더 찾았고 수리 중에 2곳이 더 나왔다 ⇒ **12곳**.
근거는 이제 산문이 아니라 테스트다 — `tests/trading/test_router_cancel_metric_failure.py` ·
`tests/trading/test_trading_task_metric_failure.py` · `tests/tasks/test_live_signal_metric_failure.py`.

★**S1(「가드 옆 raw」) 스윕은 앞만 본다** — `_count_safely` **뒤**에 오는 raw 는 구조적으로 못 잡는다.
실제로 2곳을 놓쳤고 수리 중 테스트 red 로 발견했다. **이 규칙은 완전성을 주장하지 않는다.**

★**`metrics_multiproc.py:35` 는 영구 제외** — `record_metric_safely` 자신의 실패 fallback 이라
감싸면 **재귀**한다. 이미 자체 `try/except` 안이고 DB write·후속 훅·HTTP 표면이 없다.

★**Trigger 의 한계** — `qb_metrics_mutation_failed_total` 은 `record_metric_safely` **안에서만**
오른다(`metrics_multiproc.py` 유일 증가 지점). 가드 **밖** 96곳이 던지면 이 counter 는 오르지
않고 호출자가 죽는다. 즉 이 Trigger 는 **직접 관측이 아니라 프록시**다 — 「같은 환경이면 가드된
자리도 함께 실패한다」를 전제로만 성립한다.

### ★2026-08-03 — 위 표의 **산문 2줄이 25곳을 잘못 뺐다** (metric-guard-residual-close)

종전 이 자리에는 「`order_service.py` 10곳 = 발주 전 검증 거절 직후 `raise`, blast radius 0」과
「`trading.py` closed_pnl 7곳 = `already_synced` 로 수렴, 귀결은 거짓 알림 1건」이 적혀 있었다.
**둘 다 고장 주입으로 반증됐다. 판정 25곳 전건 「수리함」, 「가드 없이 유지」 0곳.**

- **`order_service.py` 10/10** — 계측이 던지면 도메인 예외가 **아예 발생하지 않고** `OSError` 가
  탈출한다. 9종 전부 `AppException`(4xx) 이라 HTTP **500** 이 되고, 그중 6종은 호출자가 예외
  **타입으로 분기**하므로(`tasks/live_signal.py:3232`/`:3239`/`:3249`/`:2793`) `mark_failed` +
  `commit` 이 통째로 빠지고 결정론적 거절이 **3회 재시도**된다. ★`idempotency_conflict` 자리는
  「발주 전」이 아니라 `begin_nested()` + advisory lock **안**이었다.
- **closed_pnl** — 수렴을 만드는 `realized_pnl_synced_at IS NULL` 조건은
  `backfill_exchange_realized_pnl` 을 **호출하는 자리에만** 적용된다. 7곳 중 **5곳은 그 함수를
  한 번도 안 부르는 종결 skip** 이고, `already_synced` 자신은 수렴이 아니라 **고정점 실패**다.
  논거가 성립하는 것은 `applied` 1곳뿐이고 그 자리도 commit **뒤**다.
- **★「거짓 알림 1건」은 반대였다** — `:1744`/`:1756` 은 포기 알림 **바로 앞**이라 지속 실패 시
  알림이 **0건**이 되고 task 가 죽는다.
- **★백로그가 이름을 대지 않았던 8곳 중 6곳이 더 나빴다** — `(tasks/trading.py, qb_closed_pnl_backfill_total)`
  census 는 **15곳**이고 「7곳」은 한 함수의 부분집합이었다. 나머지 중 `:2144` 는 **계정 격리를
  지키는 `except` 의 첫 줄**이라 계측 지속 실패 시 **계정 루프 전체가 중단**된다.
- ★★**단 `:1879`/`:1884` 2곳은 「판정 보류」다 — 프로덕션에서 구조적으로 도달 불가**
  (`list_by_exchange(bybit)` 가 SQL 로 걸러 오고, `BybitFuturesProvider` 에는 `__init__` 이 없다).
  **내 하네스가 계약을 깨서 만든 분기였고 codex G6 가 잡았다.** [BL-582] 함정의 거울상이다 —
  손조립한 상태는 「도달 불가」로도 「유해」로도 거짓말한다. 래핑은 유지, 인용은 금지.
  ⇒ 판정 25곳 = **수리함 23 + 판정 보류 2**, 「가드 없이 유지」 0.

정본은 산문이 아니라 테스트다 — `tests/trading/test_order_rejected_metric.py` ·
`tests/tasks/test_closed_pnl_refresh_metric_failure.py` ·
`tests/tasks/test_closed_pnl_sweep_metric_failure.py` · `tests/tasks/test_refresh_closed_pnl.py` ·
`tests/tasks/test_live_signal_metric_failure.py`(호출자 오라클) ·
`tests/common/test_metrics_multiproc.py`(가드 폭).

★**가드 폭도 별도로 지킨다** — `.labels` 만 감싸고 `.inc()` 를 밖에 두는 **반쪽 수리는 사이트
주입 29건을 전부 통과한다**(변이 M5 실측). `_count_safely` 전용 단위 테스트 2건이 그것을 막는다.

**남은 84곳 — 파일별 분포 (개별 사유는 아직 없다. 「미판정」이지 「안전」이 아니다)**

| 건수 | 파일                                                                                                                                                                                                                                                                                                     |
| ---: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   34 | `backend/src/tasks/live_signal.py` (`_evaluate_session_inner` 21 · `_async_sweep_conditional_entries` 4 · `_async_evaluate_all` 2 · `_async_evaluate_session` 2 · `_async_dispatch_pending` 1 · **`_async_dispatch_event` 4 = 판정 보류**) — `_reconcile_conditional_entries` 12 는 2026-08-04 전건 수리 |
|   14 | `backend/src/tasks/trading.py`                                                                                                                                                                                                                                                                           |
|    5 | `backend/src/tasks/conditional_entry_janitor.py`                                                                                                                                                                                                                                                         |
|    4 | `backend/src/tasks/_ws_circuit_breaker.py`                                                                                                                                                                                                                                                               |
|    3 | `backend/src/common/redlock.py` · `backend/src/tasks/websocket_task.py` · `backend/src/trading/websocket/state_handler.py` (각 3)                                                                                                                                                                        |
|    2 | `common/alert.py` · `common/metrics.py` · `trading/realtime_publisher.py` · `trading/webhook.py` · `trading/websocket/bybit_private_stream.py` (각 2)                                                                                                                                                    |
|    1 | 나머지 8개 파일 (각 1)                                                                                                                                                                                                                                                                                   |

★**누적 판정 42곳 중 「가드 없이 유지」 0곳이다**(9 + 25 + 이번 8). 잔여 84곳도
산문으로 분류하지 말고 **주입으로 시작해라.**

**착수 순서 — `live_signal.py` 34곳부터, 한 회차에 한 헬퍼 계열로 끊어라.**
★**선행 조건은 이미 서 있다**(2026-08-04 handler-visibility): 그 34곳은 **이름 붙은 헬퍼 안**에
있고, 운반자 함수(`_reconcile_conditional_entries_inner`·`_evaluate_session_with_engine`)에는
**`try` 가 하나도 없으며** 감싸는 핸들러는 각 헬퍼가 소유하고 **docstring 에 적혀 있다**.
⇒ 4차·3차가 두 번 연속 밟은 **「함수 하나 = 한 형태」 오판의 물리적 조건이 사라졌다.**
★**그래도 산문으로 분류하지 마라** — 누적 42곳에서 「가드 없이 유지」가 0곳이다. 주입으로 시작해라.

**방법 4단계 (이전 4회차가 확립한 것 — 바꾸지 마라):**

1. 자리마다 **감싸는 핸들러를 코드로 확인**하고, 해악을 (a) 오기록 / (b) 조용한 중단 으로 갈라 적는다
2. **고장 주입으로 판정**한다 — 산문으로 「~라서 안전하다」 쓰지 마라(누적 42곳에서 그 산문 **전건 반증**)
3. 주입 판정이 안 되면 **「판정 보류」로 적고 하네스를 짓지 마라**(4회 연속 판별력 0 을 밟았다)
4. 구조적 방어는 `tests/common/test_metric_guard_census.py` 의 AST 동결(**현재 40키 / 84곳**)

★**census 숫자가 줄면 그만큼 `_FROZEN_CENSUS` 를 낮춰라** — 안 낮추면 다음 회차가 그 자리를 다시 판정한다.

### ★2026-08-03 — 「commit 뒤」는 형태가 아니다 (신규 라벨 **H8**)

발주 outbox 12곳은 **전부 `mark_failed`/`mark_dispatched` + `commit()` 뒤**였고 나는 그것을
하나의 형태로 요약했다. **8곳 중 1곳에서 그 요약이 틀렸다.** `:3133`(`close_position_flat`)만
**fail-open `try` 안**이라, 계측 예외를 `except Exception` 이 「포지션 조회 실패」로 오인해
삼키고 `return` 을 건너뛴 채 **그대로 발주한다**(주입 실측: 반환값이 `{"dispatched": …}`).
⇒ 귀결이 오기록이 아니라 **원장 분기**다 — `failed` 로 커밋된 이벤트에 실주문이 나간다.
**H8 = 거절이 집행으로 뒤집힌다.** 다음 스윕은 사이트마다 **바깥 `except` 가 무엇을 하는지**부터 적어라.

★**보류 4곳은 「안전」이 아니라 「도달 경로를 못 적었다」다** — 하네스를 만들면 프로덕션이
못 만드는 상태를 손조립하게 된다([BL-582] 함정의 거울상). 사유는 census 정본의 키 위 주석에 있다.
그중 `:3253`(`idempotency_conflict`)은 **사문**이다 — 유일 raise 지점이 `body_hash is not None`
안인데 이 호출자는 `body_hash=None` 을 넘긴다.

★**census 규칙이 못 잡는 것** — 별칭(`c = qb_x; c.inc()`) · `getattr` 동적 접근 · 모듈 alias ·
**eager `.labels()`**(`record_metric_safely(qb_x.labels(a="b").inc)` 는 `.labels()` 가 헬퍼 호출
**전에** 실행돼 예외가 탈출하는데 census 는 guarded 로 센다. 현 트리에 **0곳**, 2026-08-02 codex G6 MINOR).
★**디스크 full 의 mmap write 는 `SIGBUS`** 라 `record_metric_safely` 도 못 잡는다. 가드는 만능이 아니다.

**Risk:** 🟡

---

### BL-581

**우선순위:** P3
**카테고리:** Backend / 운영 위생 (`/metrics` 영구 누적)
**Trigger:** 파일 수가 20000 을 넘거나, `/metrics` 스크레이프 지연이 관측되거나, 디스크 여유가 20G 아래로 떨어질 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래) — 측정 완료, 수리 보류.** 2026-08-02 metric-guard-parity (사용자 확정: 측정만).
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-02 [BL-579](#bl-579) 측정 중 별개 축으로 분리

| 축           | 실측 (2026-08-02)                        | 실측 (2026-08-04 03:1x Z)              |
| ------------ | ---------------------------------------- | -------------------------------------- |
| 파일 수      | **10277** (전날 9423 → 회차 중에도 증가) | **14905** — Trigger 20000 의 **74.5%** |
| 용량         | **635MB** (여유 125G)                    | **924MB** (여유 124G — 아직 여유)      |
| distinct PID | **1968**                                 | 미측정                                 |
| 최초 파일    | **2026-07-28**                           | 2026-07-28 12:19 (= counter 출생일)    |
| 스크레이프   | 미측정                                   | **2.67초**                             |

~~★**증가율 실측 = +175 파일/h**(08-03 15:11 의 12836 → 08-04 03:1x 의 14905). 이 속도면
**약 29시간 뒤 Trigger(20000) 에 닿는다.** 즉 이제 이 항목은 소크 창의 **상한**이다.~~

★★**2026-08-04 후속 회차 정정 — 이 항목은 소크 창의 상한이 아니다.** 위 「+175/h ⇒ 29시간」은
**개발 세션 중** 창을 재서 나온 값이고, 그 시간대에는 `backend/src` 편집마다 워커가 재기동한다.

증가 드라이버는 **PID churn** 이 맞는데, 그 PID churn 을 만드는 것이 무엇인지가 빠져 있었다 —
워커 커맨드가 **`uv run watchfiles --filter python celery … /app/src`**(`docker inspect` 실측)라
**`backend/src` 를 편집할 때마다** 전체 재기동하고, 재기동마다 새 PID 가 role 당 5파일
(`counter`/`gauge_livesum`/`gauge_mostrecent`/`gauge_sum`/`histogram`)을 만든다.

| 시간대                        | 실측 증가율     | 근거                                                                           |
| ----------------------------- | --------------- | ------------------------------------------------------------------------------ |
| **편집 세션**                 | **~600 파일/h** | 08-03 08시 584 · 08-03 17시 829 · 08-04 01시 595 (birth 시각 히스토그램)       |
| **조용한 소크**(`src` 편집 0) | **~4–5 파일/h** | 08-04 00시 **4개** · 08-04 02:55~04:27 의 90분에 **5개**(워커 자식 1회 재활용) |

⇒ 잔여 5,091 파일을 조용한 소크 속도로 나누면 **약 42일**이다. **소크를 며칠 돌리는 데 구조적
상한이 없다.** 이 항목이 제약하는 것은 소크 시간이 아니라 **개발 재기동 예산**(약 8시간치 편집
세션)이다. ⇒ 우선순위 **P3 유지**, [BL-591]/[ADR-023] 보다 앞설 이유 없음.

★**「최근 57분간 신규 0개」로 먼저 적었던 것은 과장이었다** — 같은 회차 안에서 90분 창으로 다시
재니 5개였다. **n=1 창으로 「0」을 주장하지 마라**(이 레포의 「작은 창의 0 은 0 이 아니다」).

★★**counter/histogram 파일을 지우지 마라** — `entry_completeness.py` 가 **재기동 생존을 전제로**
창 차분을 잰다. 지우면 이 레포의 측정 체계가 깨진다. `mark_process_dead` 는 gauge 만 지운다.
★**writer id 를 PID → worker index 로 바꾸는 것도 금지** — `MmapedDict` 는 단일 writer 전제이고
prefork 부모+자식 동시 생존 · reload drain 겹침 구간이 실재한다. **손상 확률을 올린다.**
★**착수 시 내가 「로컬 API 는 단일 프로세스 모드」라고 적었는데 거짓이다** — `Makefile:163-166` 이
`PROMETHEUS_MULTIPROC_DIR` 와 `QB_METRICS_ROLE=api` 를 직접 주입한다.

**Risk:** 🟢

---

### BL-582

**우선순위:** P3
**카테고리:** Backend / 관측 (도달 불가 series)
**Trigger:** `PendingOrderSnapshot` 이 exit level 을 갖게 되거나(엔진 계약 변경), `degraded_input` 이 자연 발화로 관측될 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 2026-08-03 metric-guard-residual 이 「7종」을 「5종」으로 축소 재판정.**
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
2종은 **엔진 실행으로 반증**됐고 남은 5종은 실행 가능한 구조 전제 게이트로 고정했다.
**출처:** 2026-08-02 [BL-576](#bl-576) 잔여 검증 중 확정

`qb_live_conditional_divergence_total` 의 13 series 중 **5종**이 구조적으로 도달 불가다(종전 7종).

### ★2026-08-03 반증 — 근거 문장이 거짓이었다

종전 근거는 「`PendingOrderSnapshot.take_profit/stop_loss/trailing_stop` 이 **항상 `None`**」이었다.
`run_live` 를 직접 돌려 반증했다 — **반대 방향 same-id 재발행 + `strategy.exit`** 이면 엔진이
`take_profit=192`·`stop_loss=64`(또는 `trailing_stop=100`)를 **실제로 싣는다.**

★**올바른 서술은 [BL-523](#bl-523) 쪽이었다** — 「현재 코퍼스 미발현」. 발현 조건 3개:
(a) 같은 `trade_id` 가 이미 열려 있고 (b) 그 id 에 `strategy.exit` 브래킷이 붙고
(c) 재발행이 **반대 방향**(같은 방향이면 계획기가 `quantity==0` 에서 `continue` 해 게이트 미도달).

★**왜 종전 판정이 그렇게 나왔나** — 기존 게이트 테스트는 스냅샷을 **손조립**해 게이트 라인만
구동했다. 「게이트는 동작한다」는 증명하지만 「엔진이 그 입력을 만들 수 있는가」는 검증하지
않았다. 그 미검증 구간이 「도달 불가」로 기록됐다. 정본 =
`tests/tasks/test_conditional_divergence_reachability.py`(엔진 산출물을 reconcile 루프에 직접 흘린다).

| series                                                            | 판정                                                                                                            |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `guard_drop`/`bracket_trailing_only` · `bracket_tp_size_mismatch` | ★**도달 가능** (2026-08-03 엔진 구동 확인). 프로덕션 발화는 여전히 미관측                                       |
| `other` 5종                                                       | 도달 불가 — 전 호출부 reason 가능값이 allowlist 부분집합임을 **bounded def-use 오라클**로 고정(해소 실패 = red) |

★**도달 가능 8종**(2026-08-03 재판정, 종전 6종) **중 프로덕션 확인 = 3**
(`stand_down/shared_account_symbol` · `market_converted` ·
**`exchange_divergence`**(2026-08-02 유도로 신규 확인)). 남은 **5종**:
`stand_down/hedge_mode`(계정 position mode 전환 필요) · `guard_drop/breach_exceeds_cap`(확률적) ·
★`degraded_input/reference_price_unavailable` — **유도하려면 제3자 공개 API 에 레이트리밋 유발
트래픽을 쏘거나 MITM 프록시가 필요하다. 전자는 하지 않는다(영구 제외)** ·
`guard_drop/bracket_trailing_only` · `guard_drop/bracket_tp_size_mismatch`(2026-08-03 신규 —
결정론 fixture 로만 검증, 코퍼스에 발현 전략이 없어 프로덕션 유도는 전략 등록이 선행돼야 한다).

★**2026-08-03 회차는 soak 를 하지 않았다**(사용자 결정) — 위 5종은 **「프로덕션 미확인」으로
명시 유지**한다. 미확인을 적어 두는 것 자체가 산출물이다.

★**「13 series 존재」를 기능 증거로 인용하지 마라 — 증거는 오직 차분이다.**

**Risk:** 🟢

---

### BL-584

**우선순위:** P3
**카테고리:** Backend / 관측 (라이브 발주 실패 사유 유실)
**Trigger:** ★**`mode=live` 인 `ExchangeAccount` 가 처음 생성될 때**(Wave 3 cutover — 그 순간 도달 가능해진다). 또는 `qb_live_signal_dispatch_total{outcome="max_retries_exhausted"}` 의 창 차분이 0 을 벗어날 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래) — 2026-08-03 metric-guard-residual-sweep 가 「현재 코퍼스 도달 불가」로 확정.**
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
수리하지 않는다. 등재는 유지하되 Trigger 를 cutover 로 바꿨다.
**출처:** 2026-08-03 metric-guard-residual-close (BL-580 A6/A7 판정 중)

`BalanceUnverified`(fail-closed 잔고 미검증 거절, 422)가 `tasks/live_signal.py` 의 **결정론적-거절
튜플 양쪽에 없다** — `_async_dispatch_event` 의 `except (NotionalExceeded, LeverageCapExceeded,
MinNotionalNotMet, TradingSessionClosed)` 에도, `dispatch_live_signal_event_task` 의 무재시도
튜플에도 없다. 같은 계열의 다른 거절 5종은 둘 다에 있다.

**귀결.** 이 거절은 `except Exception` 으로 떨어져 **재시도 대상**이 되고, 소진하면
`mark_failed(error="max_retries_exhausted")` + `outcome="max_retries_exhausted"` 로 기록된다.
**실제 사유(잔고 미검증)가 기록에서 사라진다.**

★**재시도 자체는 타당할 수 있다** — 잔고·mark price 조회 실패는 일시적일 수 있다. 그래서 P3 이고,
수리 방향은 「튜플에 넣기」가 아니라 **소진 시 원래 예외 사유를 error 에 보존하기**일 가능성이 높다.
결정 전에 `BalanceUnverified` 가 라이브에서 실제로 발생하는지부터 봐야 한다 — 현재 플랫폼은
Bybit **demo** 만 허용하고 이 거절은 `mode == live` 분기에서만 난다(`order_service.py`), 즉
**현재 코퍼스에서 도달 불가일 수 있다**. 그것부터 확인하는 것이 첫 step 이다.

### ★2026-08-03 도달성 확인 — **현재 코퍼스 도달 불가 확정** (수리 없음)

- `raise BalanceUnverified` 2곳(`order_service.py:295`·`:309`)은 모두
  `dispatch_snapshot["mode"] == ExchangeMode.live` 게이트 안이다.
- `dispatch_snapshot["mode"]` 는 발주 시점 계정 **fresh read**(`order_service.py:199`) —
  세션 등재 시점 스냅샷이 아니다.
- 라이브 세션 등재는 `account.exchange == bybit and account.mode == demo` 를 강제하고
  아니면 `AccountModeNotAllowed`(`live_session_service.py:109`).
- ★**계정 mode 는 생성 후 불변이다** — `ExchangeAccountRepository` 에 갱신 메서드가 없고
  (`save`/`get_by_id`/`list_*`/`delete` 뿐), 라우터도 POST(등재)·GET·DELETE 뿐이다.
- 코퍼스 실측(2026-08-03): `mode=live` 계정 **0건**.

⇒ 라이브 신호 dispatch 경로에서 이 거절은 **날 수 없다.** 그래서 고치지 않고, Trigger 를
「그 전제가 깨지는 순간」(= `mode=live` 계정 생성)으로 바꿔 등재만 유지한다.

**Risk:** 🟢

---

### BL-586

**우선순위:** P3
**카테고리:** Backtest / Trust Layer (골든 커버리지 구멍)
**Trigger:** TV parity 팩·비용 분해·청산 지표에서 회귀가 의심될 때
**Est:** M (baseline 크기 증가 + 리스트형 필드 직렬화 설계 선행)
**상태:** ✅ **Resolved** (2026-08-07 backtest-fidelity)
**출처:** 2026-08-03 backtest-metric-oracle

**수리 (2026-08-07).** `regen_trust_layer_baseline.py` 의 `metrics_dict` 와 `_trade_to_dict` 를
**하드코딩 키 리스트에서 `dataclasses.fields()` 자동 유도로 교체**했다 — 이것이 수리의 핵심이다.
키를 손으로 적으면 다음에 `types.py` 에 필드가 늘어도 여기가 안 늘어난다.

- `BacktestMetrics` 51 = 스칼라 **46 전량** + 리스트 3종(`monthly_returns`·`drawdown_curve`·
  `buy_and_hold_curve`)은 `metrics_list_digests` 로 접고 + 중첩 2종(`per_side`·`excursion_stats`)은
  평탄화(`per_side.long.*` / `excursion_stats.*`).
- `RawTrade` **22 전량**(digest 11 → 22). ★실측으로 확인: `RawTrade` 는 **리스트/dict 형 필드가 0개**라
  digest 설계가 필요 없었다 — BL 본문이 예상한 「리스트 직렬화 설계 선행」은 metrics 쪽에만 해당했다.
- `types.py:289` 의 "trust-layer trades digest(명시적 11-필드) 불변" 주석을 갱신했다.
- 같은 digest 규칙을 `regen_golden.py`([BL-621]/[BL-022])와 공유한다.
- 신규 가드 `tests/strategy/pine_v2/test_baseline_field_coverage.py`(evaluator 가 구현 전에 작성).

★**아래는 2026-08-07 수리 전의 상태 기술이다**(현재는 위 Resolved 블록이 정본).
수리 전 P-3 골든이 고정한 것은 `BacktestMetrics` **51 필드 중 13개**뿐이었다.
**38개가 회귀 감지 대상 밖**이었다 — TV parity 팩(`avg_holding_hours` · `consecutive_*_max` ·
`monthly_returns` · `drawdown_curve` · `annual_return_pct` · `avg/best/worst_trade_pct`),
비용 분해(`total_fees` · `total_slippage` · `total_funding`), `per_side`, `excursion_stats`,
청산(`liquidation_occurred` · `liquidation_count`) 이 전부 여기 속한다.

`RawTrade` 도 22 필드 중 digest 에 들어가는 것은 **11개**였다(당시 `types.py` 주석이 "trust-layer
trades digest(명시적 11-필드) 불변" 으로 그 결정을 명문화했다 — ★그 주석은 2026-08-07 에 `:289-293`
으로 옮겨 **내용이 뒤집혔다**). `exit_kind` · `fee_paid` · `slippage_paid` ·
`liquidated` 등이 빠져 있다.

**권장 접근:** 전량 고정은 baseline 을 크게 만들고 리스트형 필드(`monthly_returns` ·
`drawdown_curve` · `buy_and_hold_curve`)는 그대로 넣기 어렵다 — **digest 로 접는 쪽**이 현실적이다.
스칼라 필드부터 늘리고 리스트는 필드별 digest 를 추가하는 2단계 권장.

**영향 파일:** `scripts/regen_trust_layer_baseline.py`, `tests/strategy/pine_v2/test_trust_layer_parity.py`, `tests/fixtures/pine_corpus_v2/baseline_metrics.json`.

**Risk:** 🟢

---

### BL-591

**우선순위:** P2 (2026-08-05 강등 — 「P0 [BL-003] 의 실질 게이트」가 [ADR-025] 상류 폐쇄로 무너졌다. **본 BL 범위의 잔여 = D1/D2 뿐**이고, 되먹임이 없는 나머지 갈래(브래킷 TP/SL · 거래소발 청산 · 시장가 진입)는 [ADR-023] 소관으로 남는다 — 이 강등은 그 축까지 내리지 않는다)
**카테고리:** Trading / 라이브 신호 (엔진 포지션 SSOT)
**Trigger:** ★**이미 발화했다.** 자동 종료 **15회**(NULL 12 + `gap_resync_position_mismatch` 1 +
`position_divergence` 2). `direction` 발산 가드 머지(#497, `2026-07-28T23:09Z`) **이후의 자동 종료는
6회**이고 그 **6/6 이 2시간 안에 죽었다**(104.9 · 91.4 · 84.3 · 65.0 · 21.5 · 18.0분).
**Est:** L — **설계 결정 선행**(사용자). 구현 착수 전 이 절의 §설계 축을 확정해야 한다.
★★**2026-08-11 ledger-truth — 이 Est 는 같은 섹션의 우선순위 줄과 모순이다.** 그 줄은 「본 BL
범위의 잔여 = **D1/D2 뿐**」이라 적는데 Est 는 여전히 **L**(설계 결정 선행)이다. 설계 5축은
2026-08-04 에 축소·이관으로 정리됐고 남은 것은 두 갈래뿐이다 ⇒ **Est 는 재산정 대상**이고
「L + 사용자 선행」을 근거로 미루면 이미 끝난 결정을 다시 기다린다.
**상태:** 🟢 **Open — 슬라이스 1(계측)은 PR #539 로 머지됐다(`gh pr view 539` 로 재확인). 슬라이스 2 는 사전등록 V1 발동으로 미착수 확정. ★2026-08-04 에 C 안이 「예방 전용·사망 경로 구조적 미도달」로 축소되고 사망 경로의 수리 축은 [ADR-023](decisions/023-engine-state-ssot.md)(Proposed)으로 이관됐다. ★★★2026-08-05 divergence-rejudgement — **슬라이스 B(킬 정책 교체)는 판별력 0 으로 판정되어 보류**(폐기 아님): 사망 4건 **전부**가 새 판별식으로도 `phantom` 이라 「즉시 킬」로도 그대로 죽고, 무해 12건 중 사망은 **0건**이라 「절대 안 킬」로 구제될 세션도 없다 ⇒ **이 정책으로 살아났을 세션이 0개다.** D1(strike TTL 부재)·D2 는 도달 가능하므로 폐기하지 않는다. ★★**「무해 7 : 치명 4」의 방향 서술도 반증됐다** — 사망 4건 부검에서 **거래소가 앞선 사망 1건**(`39731d57`)이 나왔다. **레버는 킬 정책이 아니라 [BL-595]**(엔진·거래소가 서로 다른 stop 주문을 든다)다. ★슬라이스 A 는 재개 조건이 발화했으나 **킬 결과를 바꾸지 않는다** — 관측 가치만 남는다. 판별식·테스트·오라클은 레포에 있다(2026-08-05 기준 41 테스트)** ★★★**2026-08-05 재판정 — P1→P2 강등**: P1 근거 「[BL-003] 의 실질 게이트」가 무너졌다 — 사망 5/5 는 [BL-595] 로 재귀속돼 [ADR-025](decisions/025-conditional-fill-ownership.md) 가 **상류에서** 닫았고, 자신의 레버 A·B·슬라이스 2 도 각자 죽었다. **본 BL 범위의 잔여 = D1/D2 뿐 · 프로덕션 미관측**([ADR-025] §남는 것 = 「관측만 한다」). 재개 조건 불변.
**트리거 판정:** 도래 — 트리거가 「★이미 발화했다」로 선언(자동 종료 15회) (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-03 breach-rejection-recovery (증상 반복의 뿌리 재판정)

★★★**2026-08-11 ledger-truth — 상태줄이 6일간 거짓이었다.** 종전 문장은 「슬라이스 1(계측)은
PR #539 ~~OPEN(미머지, 통합 브랜치)~~」였다. 실제는 `MERGED 2026-08-05T00:33:22Z`
(`gh pr view 539`). 원장을 읽은 회차마다 **「미머지라서 못 이어받는다」**로 읽혔고, 그 사이
이 BL 은 ⓪ 표에서 「설계 결정이 사용자 선행」이라는 딸린 사유까지 함께 달고 내려가 있었다.
⇒ **문서가 PR 상태를 적으면 반드시 낡는다.** 상태가 아니라 **조회 명령**(`gh pr view 539`)을 적어라.

★★★**착수 전제 5건이 2026-08-04 실측으로 반증됐다. 아래 원문 숫자를 그대로 믿지 마라** —
정정본은 §실측 정정에 있다. 특히 「30건 Resolved」(실제 **16건**)와 「발화 조건만 넓히면 된다」
(실제로는 **유도 로직 신설**)가 작업량과 기대효과를 크게 왜곡한다.

**증상을 16건 고쳤는데 병이 그대로다.**

엔진↔거래소 정렬 축에 걸린 BL 은 **30건**이고 그중 **16건이 Resolved** 다(BL-361/362/374/378/
442/480/484/498/500/511/530/543/566/576/589/590). **12건이 아직 ACTIVE**(BL-390/393/441/497/515/
522/538/539/540/545/547/553) · **2건 PARTIAL**(BL-014/535). 그런데도 소크는 스스로 죽을 때 늘
2시간 안에 죽는다. **기전은 매번 달랐고 뿌리는 하나다.**

**뿌리 — 엔진 포지션은 「도출값」이고, 그것을 고칠 수 있는 자리가 없다.**

`run_live(strategy.pine_source, df, ...)` 는 **매 tick 봉을 처음부터 재생**한다
(`live_signal.py:2360`). `last_strategy_state_report` 는 발산 스트라이크 플래그와 보고용일 뿐
엔진 상태를 이어받지 않는다. ⇒ **엔진 포지션에 「쓸」 수 있는 곳이 없다.** 거래소에서 무슨 일이
일어나도 엔진은 자기 재생 결과만 믿는다.

**만성 불일치는 이미 계측돼 있다** (프로덕션 누적):

| category                  | 건수    | 처리                 |
| ------------------------- | ------- | -------------------- |
| `engine_only`             | **314** | 관측 전용            |
| `size`                    | 28      | 관측 전용            |
| `direction_transient`     | 23      | 1회차 유예           |
| `exchange_only`           | 21      | 관측 전용            |
| `direction`               | **3**   | **fail-closed 종료** |
| `engine_only_unexplained` | 1       | 관측 전용            |

즉 **어긋남은 상시**이고, 그중 **방향이 뒤집힌 경우만** 죽인다. 나머지는 「보고 넘긴다」.

★**위 표에서 원장 주입이 닿을 수 있는 것은 `exchange_only` 21건뿐이다** — 나머지 366건은
엔진에 이미 포지션이 있어 주입 함수가 첫 줄에서 나간다(§실측 정정 ④).

**보정 경로는 하나뿐이고, 프로덕션에서 한 번도 성공한 적이 없다.**

`_ledger_gap_seed`(BL-544, PR #506)가 유일한 원장→엔진 주입이다. 그런데 ① `if requires_gap_resync:`
안에서만 돌고(= 워커가 오래 멈춰 봉을 건너뛴 경우) ② 실측 결과 **성공 seed 0건**이다 —
`already_open` 2 · `inadmissible` 2 · `no_basis` 4, `seedable` **0**.

**주입점 자체는 이미 옳은 자리에 있다.** `event_loop.py:192` 가
`if ledger_seed_legs and bar.bar_index == last_bar_index:` 로 **마지막 bar 의 Pine 실행 직전**에
넣는다. **주입 배관은 그대로 쓸 수 있다.**

★단 **「발화 조건만 넓히면 된다」는 틀렸다** — `_ledger_gap_seed` 자체는 상시 주입에 **재사용할 수
없다**(§실측 정정 ⑤). 넓히면 legs 가 항상 비어 아무것도 주입되지 않는다.

---

#### ★설계 축 — 사용자 결정 사항 (구현 착수 전 확정)

**제약(코드에 이미 적혀 있다, `live_signal.py:2248`):**

> ★조회는 여기, 판정은 아래. seed 를 **거래소에서** 가져오면 아래 대조가 **동어반복**이 되어
> 가드가 통째로 사라진다.

⇒ **「거래소를 그대로 엔진에 복사한다」는 선택지는 이미 기각돼 있다.** 그렇게 하면 발산 가드가
자기 자신을 비교하게 되어 안전망이 사라진다.

| 안                    | 내용                                                                        | 대가                                                                                                            |
| --------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **A. 현행 유지**      | 엔진 SSOT · 어긋나면 fail-closed                                            | 고칠 방법이 없어 **증상별 수리가 무한**하다. 지금까지 30건.                                                     |
| **B. 거래소 SSOT**    | 매 tick 거래소 포지션을 주입                                                | **가드 소멸**(위 제약). 게다가 포지션 크기만으로는 진입가·trade_id·pending order 를 복원 못 한다. **기각 권고** |
| **C. 원장 SSOT** ★    | `ledger_seed_legs` 를 **상시** 주입 — 엔진은 「우리 체결 원장」을 믿고 재생 | 원장이 거래소를 못 따라잡는 구간(**BL-560 실측 13분 38초**) · **원장 밖 청산**은 안 보인다(오늘 2건 발생)       |
| **D. 조정 연산 정의** | 발산 감지 시 죽이는 대신 되돌린다                                           | 엔진에 쓸 자리가 없으므로 결국 C 의 주입점을 쓰게 된다. **C 의 부분집합**                                       |

★**C 를 채택했다.** 근거 둘: ① 원장 ≠ 거래소이므로 **가드가 동어반복이 되지 않는다**(원장↔거래소
대조는 여전히 독립) ② 주입 배관(`ledger_seed_legs`, `event_loop.py:192`)이 **이미 옳은 자리에 있다.**
★위 표의 「원장 밖 청산 오늘 2건」과 아래 ①의 근거 두 줄은 **실측으로 정정됐다** — §실측 정정 참조.

#### ✅ 확정 답 (2026-08-04, 사용자 결정)

**설계 한 줄 — 엔진 포지션 SSOT = 원장. 거래소는 거부권자. 확장은 계측이 정한다.**

```
매 tick:
  ① 원장에서 포지션 유도            (값의 유일한 출처)
  ② 거래소 스냅샷 조회              (이미 매 tick 한다 — 게이트 비용 0)
  ③ ①≠② → veto                     (거래소는 "넣지 마"만 말한다)
       veto 아님 → 엔진이 flat 이면 주입
       veto      → 주입 ✖ + 발주 ✖ (관망) + 버팀 카운터 +1
                   상한 초과 시 오늘처럼 fail-closed 종료
  ④ 주입/veto/버팀 내역을 tick 상태(jsonb)에 영속
  ⑤ 주입 후 남는 발산은 현행대로 `direction` 만 킬
```

**Q2 — 원장 밖 청산 → 「거래소에 거부권만(veto)」.**
값은 끝까지 원장에서만 가져오고, 주입 직전 거래소 스냅샷과 어긋나면 주입을 포기해 오늘의
fail-closed 로 떨어진다. 거래소는 **막을 수만 있고 값을 주지 못하므로** `live_signal.py:2248`
제약에 걸리지 않는다.
_기각_ — **구멍부터 메우는 선행 슬라이스**(합성 `Order` 행이 머니-패스 원장을 오염시키고, 수집이
300초 주기라 최대 5 tick 구멍이 어차피 남는다) · **게이트 없이 수용**(오주입 → 반대 주문 발주 →
**그 뒤에야** 가드 발화. 돈이 먼저 나간다 = 이 BL 이 경고한 「C 가 지금보다 나쁘다」가 바로 이것).

**Q1 — 리컨사일러 지연 → 「관망(hold)」.**
veto tick 에서는 주입도 **발주도** 하지 않고 버팀 카운터만 올린다. 원장이 따라잡으면 정상 복귀,
상한 초과 시 fail-closed 종료. ⇒ **어느 쪽도 믿지 않는다. 확실해질 때까지 아무것도 하지 않는다.**
_기각_ — **주입만 건너뛴다**(C 의 효과가 82% tick 에만 미치고 지연 긴 15.6% 는 오늘과 똑같이 죽는다) ·
**veto 면 즉시 킬**(체결 직후 tick 의 17.8% 에서 즉사 → P0 달력 시계를 오히려 말린다).

**Q1-b — 상한은 `interval` 비례, 계수는 계측 후 확정.**
`list_active_due` 가 `last_evaluated_bar_time + interval <= now` 로 due 를 정하므로 **tick 주기 =
interval** 이다(1m/5m/15m/1h → 60/300/900/3600초). ⇒ ★**「2 tick 유예」는 1분봉이면 2분,
1시간봉이면 2시간**이고, **현행 `direction_transient` 1회 유예도 이미 interval 비례**다(미문서화였다).
단 **순수 비례는 물리와 안 맞는다** — 지연의 원인은 절대 시간(WebSocket 왕복 · 폴링 300초)이고
관망의 비용은 봉 개수(interval 비례)다. ⇒ `max(절대 하한, interval × N)` 류 **혼합형**이 후보이나
**계수는 슬라이스 1 실측으로 정한다**(추정으로 찍지 않는다).
_기각_ — **보수적 초기값으로 바로 켠다**(계수 근거가 청산 90건 추정이라 틀리면 소크 사망으로만
알게 된다) · **계측+공식을 한 슬라이스에**(꺼져 있는 관망 경로가 머니-패스에 먼저 들어간다 =
BL-582 로 데인 함정과 같은 형태).

**Q3 — 백테스트 재현성 → 안 깨진다. 단 라이브 재현성은 바뀌므로 tick 상태에 남긴다.**
백테스트(`compat.parse_and_run_v2` → `run_historical`)와 라이브(`run_live` → `run_historical`)는
**같은 엔진**이지만 `ledger_seed_legs` 를 채우는 곳은 `live_signal.py:2358` **하나뿐**이라 백테스트
골든은 안 깨진다. ⚠️ 그 격리가 **관례로만** 유지되므로(인자가 공개다) **회귀 테스트를 신설**한다.
바뀌는 것은 **라이브 자신의 재현성** — 주입 후엔 「전략+OHLCV」만으로 재현이 안 되고 그 시점
원장이 필요하다. ⇒ `live_signal_states.last_strategy_state_report`(기존 jsonb, **마이그레이션 0**)에
`ledger_seed{applied, vetoed, hold_ticks}` 를 얹는다.
_기각_ — **로그만**(보존 기간에 묶이고 SQL 집계 불가) · **카운터만**(개별 tick 증거가 없어 사후분석 불가).

**Q4 — 주입 범위와 fail-closed → 둘 다 현행 유지, 확장은 계측이 판정.**
주입은 「엔진이 완전히 비었을 때만」(= `exchange_only` 겨냥)을 그대로 두고 킬도 `direction` 만.
_기각_ — **원장으로 전면 덮어쓰기**(멱등성이 깨져 재생 포지션과 원장이 섞이고, 원장 구멍 11.7% 에
훨씬 크게 노출) · **킬을 `engine_only`·`size` 로 확대**(314+28 규모로 사망해 소크가 못 돈다.
분류기 주석이 이미 「양쪽을 죽이면 세션이 상시 사망」이라 경고한다).

**Risk:** 🔴 머니-패스 핵심. 잘못 주입하면 엔진이 없는 포지션을 믿고 반대 주문을 낸다.

#### ★실측 정정 — 착수 전제 5건 반증 (2026-08-04)

**① 「가드 머지 후 12/12 전부 2시간 미만」 → 머지 후 자동 종료는 6건이고, 반례가 있다.**
세션 전수(28행) 실측. 나열됐던 12개 값 중 **5개가 머지 전 세션**이다(99.5 · 61.3 · 57.4 · 15.5 · 2.6).

| 구간                         |   n   | 최대        | 2h 초과 |
| ---------------------------- | :---: | ----------- | :-----: |
| 머지 **전** · 자동 종료      |   9   | **916.7분** |    3    |
| 머지 **후** · 자동 종료      | **6** | **104.9분** |  **0**  |
| 머지 **후** · `user_stopped` |  13   | **197.8분** |  **3**  |

★★★**결정적 반례** — `a815df92` 는 머지 후 **197.8분(3.3시간) · 주문 39건**을 돌고 **죽지 않았다**
(`user_stopped`). `position_divergence` 킬은 그때 이미 라이브였다(`fa603ca4` 가 `07-30T04:40Z` main
진입, 세션 시작 `07-30T15:54Z`). `fa114ce9` 153.4분 · `98d86785` 148.4분도 같다. 게다가 이 문장을
쓰는 시점의 소크(`4bf679af`)가 **2.4시간째 생존 중**이었다.
⇒ 참인 명제는 **「2시간을 못 넘긴다」가 아니라 「스스로 죽을 때는 항상 2시간 안에 죽는다」**이다.

**② 「30건 Resolved」 → 16건.** `scripts/bl-audit.sh`(정본) 대조 결과
**RESOLVED 16 / ACTIVE 12 / PARTIAL 2**(목록은 위 본문). ★섹션 상태줄을 `awk` 로 직접 읽으면
**틀린다** — BL-393/441 등은 자기 섹션에 상태줄이 아예 없어 다음 섹션 것을 집어온다.
**`bl-audit.sh` 가 정본이라는 규칙이 여기서 실제로 필요했다.**

**③ 「원장 밖 청산 오늘 2건 · `ClosePositionService` 가 provider 직접 호출」 → 12건, 단 10/12 가
세션 밖이고 앱에는 우회 경로가 없다.**
`trading.exchange_exits`(이미 돌고 있는 계측기)로 실측 — 실제 청산 **103건** 중 `external_manual`
**12건**(07-24/27/28/31, 08-01/03 **6일에 걸쳐** = 상시). ★★그러나 **12건 중 10건이 「활성 세션
없음」 구간**이고, 세션 안은 2건(같은 세션, 데스크 개입일)뿐이다.
★★★**그리고 `close_service.py` 는 `OrderService.execute` 를 타므로 `Order` 행을 남긴다** —
`src/` 에서 주문을 내는 provider 호출은 `tasks/trading.py:431`(원장 경로) 하나뿐이다. 범인은
**`backend/scripts/verify_*.py` 등 운영자 도구**다(서비스가 HTTP 에만 조립돼 스크립트가 못 쓴다).
⇒ **구멍은 앱의 결함이 아니라 도구의 결함이다.** → [BL-593]
★함정: `unknown` 91건은 구멍이 아니라 **중복 계정 아티팩트**다 → [BL-592].

**④ 「`engine_only` 314건을 원장 주입이 정면으로 겨냥」 → 겨냥 대상은 `exchange_only` 21건이다.**
`strategy_state.py:357` 주입 함수 첫 줄이 `if not legs or self.open_trades: return ()` —
**엔진이 완전히 비었을 때만** 주입한다(주석: 「채택은 "엔진이 완전히 비어 있을 때 원장을 믿는다"
하나뿐이다」). 분류기와 대조하면 주입 가능한 것은 **엔진 flat 인 `exchange_only` 21건뿐**이고
나머지 366건(`engine_only` 314 · `size` 28 · `direction` 3 · `transient` 23)은 `open_trades` 가
차 있어 **주입 자체가 일어나지 않는다.**
★★★**그리고 주입과 `direction` 킬은 같은 tick 에 공존할 수 없다** — `direction` 은 양쪽 non-flat,
주입은 엔진 flat 이 조건이다. ⇒ **C 는 소크를 죽이는 그 발산을 「교정」하지 못한다. 「예방」할
뿐이다**(진입을 놓친 상태를 미리 메워 나중에 `direction` 으로 발전하는 것을 막는다).
**이 구분을 지우면 다음 사람이 「314건짜리 수리」로 읽고 효과를 과대평가한다.**

**⑤ 「순수 함수가 이미 있다 · 발화 조건만 넓히면 된다」 → `_ledger_gap_seed` 는 재사용 불가.**
그 함수의 채택 조건이 **「창 안 체결이 전부 같은 방향 + reduce-only 하나도 없음」**이다
(`live_signal.py:405-407`). 상시 주입에서는 `since` 를 어떻게 잡아도 깨진다 — 세션 시작으로
잡으면 진입+청산이 **반드시 섞여** `inadmissible`, 직전 tick 으로 잡으면 체결이 거의 없어
`no_basis`. 둘 다 **legs 가 빈다.**
⇒ **C 는 「발화 조건 확대」가 아니라 「원장 → 현재 열린 포지션」 유도 로직의 신설**이다
(Pine `trade_id` 단위로 진입/청산 상쇄). 순수 함수라 단위 테스트로 전량 검증 가능하지만
**작업량은 이 BL 이 시사한 것보다 크다.**

#### 슬라이스 계획

**슬라이스 1 — 계측만 (판정·발주 경로 무변경).** 반증 ⑤ 때문에 **1a 유도 함수 신설**이 최대 작업이다.
★**「동작 변경 0」은 정확하지 않다** — 거래소 조회가 tick 당 1회 늘어 **2회**가 된다.
`_detect_position_divergence` 는 `engine_position`(= `run_live` 결과)이 필요해 뒤로 갈 수밖에 없고
veto 는 주입 **직전**에 판정해야 하므로 두 조회는 **구조적으로 합칠 수 없다.**
`run_live` **직전**(= 슬라이스 2 의 주입 판정 지점과 **같은 자리**)에서 원장 포지션 유도 + 거래소
스냅샷 + 비교 판정을 **계산만** 하고 카운터·jsonb 에 기록한다. `_detect_position_divergence` 는
**무수정**(동작 변경 0 보장). ★계측 지점이 슬라이스 2 의 판정 지점과 다르면 **여기서 잰 계수가
무의미**해진다.
_재는 것_ ① 주입 가능 tick 수 ② veto 발동률 ③ **veto 해소까지 tick 분포**(상한 계수의 직접 근거)
④ ★**`exchange_only` → `direction` 발전율**(= C 의 예방 효과 그 자체) ⑤ 유도 함수 `None` 비율.
_사전등록_ **④가 0 이면 C 의 근거가 무너지므로 슬라이스 2 를 착수하지 않는다.**
「몇 시간 무사고」를 증거로 쓰지 않는다.

**슬라이스 2 — 주입 + veto + 관망.** 상한 계수는 슬라이스 1 의 ③ 분포로 확정한다.

**부수** — 운영자 청산 도구 원장 기록([BL-593], 슬라이스 1 과 독립) · 백테스트 격리 회귀 테스트.

**비목표:** 증상별 발산 채널을 또 닫는 것. **이 BL 이 열려 있는 동안 새 증상 BL 은 여기에 링크**해라.

#### ★슬라이스 1 실측 — 사전등록 V1 발동, 슬라이스 2 **미착수 확정** (2026-08-04)

**④ = 0.** 근거 3층(전문은 [ADR-022](decisions/022-engine-position-ssot.md) §슬라이스 1 실측):

1. **연역 상계** — 주입은 엔진이 완전히 비었을 때만 일어나고(`strategy_state.py:357`) `agree` 면
   거래소도 non-flat 이므로, **주입이 값을 넣는 tick 은 `exchange_only` tick 의 부분집합**이다.
2. **모집단**(`.soak/snap-*.txt` 차분 17.06h) — `exchange_only` **+1** vs 하드 `direction` 킬 **+2**.
   ★결과 사건이 발화했으므로 **「무사고라 못 쟀다」가 아니다.**
3. **부검 2/2** — 사망 세션 2건의 상류에 `exchange_only` **0건**. 유일한 1건은 세션 첫 tick 의
   먼지 잔여(`engine 0.0 / exchange -0.001`)라 원장이 비어 **주입 대상이 아니다.** 최악 상계 ≤ **1/21**.

⇒ 사망 경로는 **반전**이고 반전은 tick 경계에서 flat 을 거치지 않는다. **C 의 전제가 사망 경로에서
구조적으로 밟히지 않는다.**

**⑤ = 27.6%(세션) / 63.6%(발산 사건).** 과거 **29세션 전량**에 `derive_open_position` 을 그대로
재생한 결과 판정 불가 **8/29** 이고 그중 **7건이 `duplicate_open`** 이다(나머지 1건 `foreign_fill`).

★★★**뿌리 — `trade_id` 는 trade 인스턴스가 아니라 Pine 진입 규칙 이름이다.** 실측: `PivRevSE`
**56 체결 / 19세션**, `PivRevLE` 39/16. 게다가 **반전은 `:close:` 키를 만들지 않는다** — 배(倍)
수량 진입 주문 하나로 나간다(실측 `0.03` 숏 보유 중 `0.06` 롱 진입). ⇒ 유도 함수의 전제
「어느 진입을 어느 청산이 닫았는지 키만으로 이어붙일 수 있다」가 **반전 전략에서 성립하지 않는다.**

★★★**net 은 맞고 legs 는 틀리다 — 계측이 재는 것과 슬라이스 2 가 쓰는 것이 다르다.**
구현과 독립된 오라클(워커 로그가 그 시각 거래소에서 직접 읽은 값) 11건 대조:
**빗나감 0 · 적중 4 · 판정불가 7**. ★적중 4건 중 **3건이 `legs=2`** 인데 거래소는 단일 포지션이다
(예: 숏 0.03 + 롱 0.06 = net +0.03 ✓, 실제는 롱 0.03 하나). 슬라이스 1 은 **net** 으로 `agree` 를
판정하고 슬라이스 2 는 **legs** 를 주입하므로, **계측이 초록이어도 주입될 값은 틀렸다.**
⇒ ④가 0 이 아니었더라도 현행 유도 함수로는 슬라이스 2 를 켤 수 없다.

**칭찬할 것 하나** — 유도 함수는 **틀린 답을 낸 적이 없다**(오답 0/11). 「모른다」와 「비었다」를
접지 않은 fail-closed 설계가 실제로 작동했다. 문제는 **모른다고 답하는 비율**과 **legs 분해**다.

#### 부수 관측 (수리하지 않음 — 기록만)

- **원장 스캔 상한 200건**(`LEDGER_FILL_SCAN_LIMIT`)이 장기 소크에서 `overflow`(판정 불가)로
  떨어진다. 실측 체결률 최대 **0.09건/분** ⇒ 약 **37시간**이면 200 도달. P0([BL-003])의
  「데모 1주 안정 운영」과 양립하지 않는다.
- **`_qb_ledger_shadow` 는 최신 tick 만 덮어쓴다** — ③(veto 해소 tick 분포)를 사후에 못 캔다.
  근거가 counter bucket 에만 남으므로 n 이 잘 안 쌓인다.

#### 후속 실측 (2026-08-04 engine-state-ssot) — **판정 불가는 비율이 아니라 흡수 상태다**

**사전등록 예측 적중.** 「다음 `PivRevSE` 진입 체결에서 `duplicate_open` 으로 넘어간다」가 그대로
맞았다(`03:48:16`, 2번째 `PivRevSE` 체결). ★첫 읽기가 0 이었던 것은 **호스트 `/metrics` 지연**이다.

**흡수 상태.** `_capture_ledger_shadow` 가 `since = sess.created_at`(`live_signal.py:471`)으로
**세션 전체**를 읽으므로, `trade_id` 가 한 번 반복되면 그 뒤 **모든 tick 이 영구히 `legs=None`**
이다. 프로덕션 실증 — `derive_total{open}` 이 **44.0 에서 완전 정지**하고 `{duplicate_open}` 만
**36 연속**으로 올랐다.

| 축                                                             | 실측                                                                                                                                                   |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 라이브 시간 중 어두운 비율                                     | **19.0%** (601 / 3165 세션·분, n=29)                                                                                                                   |
| 실명까지                                                       | median **26.6분** (min 17.3 / max 60.5, n=8)                                                                                                           |
| ★**`position_divergence` 사망 2건이 모두 이미 어두운 뒤 사망** | `a201a47b` T0+17.3 → T0+104.9 · `04097fdc` T0+26.1 → T0+65.0                                                                                           |
| 깨지는 조건                                                    | **반전(`:close:` 키 없음)** — close 키 0 + 체결 ≥2 세션 **6/6 전건** dark. 916분 무실명 세션 `e1f6d84c` 는 `Long` 12 open/12 close **짝 맞는 롱 전용** |

★재생 산식이 위 ⑤ 의 **27.6%(8/29)를 그대로 재현**해 계측기 자체가 교차검증됐다.

**판정 — veto 절반까지 꺼진다.** ④=0 이 **주입**을 막았고, 이번 실측이 **veto/관망**까지 막는다:
⑴ 사망 시점에 유도가 판정 불가라 입력이 없다 ⑵ 설령 계산돼도 veto 는 「원장 vs 거래소」 대조인데
사망 경로는 **원장==거래소·엔진만 거짓말**이라 `agree` 로 통과한다 ⑶ 방향이 반대다
(`engine_only` **314** vs `exchange_only` **21**).
⇒ **C 는 예방 전용이며 사망 경로에 구조적으로 닿지 않는다.** 사망 경로의 수리는
[ADR-023](decisions/023-engine-state-ssot.md) 으로 이관.

**유도 함수 재설계의 알고리즘이 선행연구에 있다** — NautilusTrader 는 `trade_id` 짝짓기를 하지
않고 **부호 있는 순수량의 zero-crossing 으로 생애주기를 자른다**(+ 불완전한 첫 생애주기에 합성
개시 체결을 더한다). `trade_id` 재사용·배수량 반전에 **구조적으로 면역**이다. 상세는 ADR-023.

#### 후속 실측 (2026-08-04 direction-channel-decomposition) — **`direction` 은 두 현상이다**

워커 로그 41시간의 `direction` 관측 **11건 전량**을 원장 체결과 대조했다. **부호가 반대인 두
현상**이 한 라벨에 묻혀 있었고, 「마지막 체결로부터의 경과 시간」으로 **겹침 없이** 갈린다.

| 갈래               | n     | 마지막 체결로부터  | 누가 앞서나                            | 자가치유 | 사망    |
| ------------------ | ----- | ------------------ | -------------------------------------- | -------- | ------- |
| **A** `replay_lag` | **7** | 0.59 – **24.7초**  | **거래소가 앞섬** — 엔진이 못 따라온다 | **7/7**  | 0       |
| **B** `phantom`    | **4** | **909초** – 2336초 | **엔진이 앞섬** — 주문이 거래소에 없다 | **0/4**  | **2/2** |

경계가 **37배** 벌어져 있고 겹치는 관측이 없다. 산술도 닫힌다 — 11 = `direction_transient` **+9**

- 하드 킬 **2**(9 = A 7건 + B 각 쌍의 **첫** 관측 2건).

★**A 는 결함이 아니라 구조다** — 조건부 주문은 봉 중간에 거래소에서 체결되고 엔진은 닫힌 봉만
재생한다(`ccxt.py:145`). `live_signal.py:2705-2714` 가 이미 적어 두었고 `direction_transient` 는
**바로 이걸 흡수하려고** 있다. 실측 **반전 28건 중 7건(25%)**.
★**B 가 사망의 전부다** — [BL-589] 「계획기가 드롭」·[BL-590] 「거절 뒤 복구 없음」이 각각 한 쌍.

**치명 갈래만 노출 시간으로 재면:** 수리 전 **4건/2.85h = 1.40/h** → 수리 후 **0건/6.12h**
(기대 8.6건). ★**「닫혔다」고 쓰지 마라** — 95% 상계 **0.49/h** 다. 상계를 0.25/h 로 낮추려면
**6.1 라이브시간이 더** 필요하다.
★**[ADR-023] 의 「≈0.5/h」는 벽시계 rate 였다**(9건/18.5시간). 노출 기준으로는 **1.27/h** 이고
그 대다수가 A 다. 같은 문서가 `engine_only` 는 노출로 재라고 요구하면서 `direction` 만 벽시계로 쟀다.

**오라클** — `backend/scripts/classify_direction_divergence.py`(프로덕션 코드 미import).
사망 상관 **2/2** · `replay_lag` 생존 **7/7** · 봉경계식 vs 시간문턱식 불일치 **0건**.
★**적합은 검증이 아니다** — 판별식을 이 11건에서 유도했으므로 독립적인 것은 **사망 상관**
하나뿐이다. 나머지는 **전향 예측**으로 갚는다(`docs/status.md` 사전등록).
★관측 11건은 전이력 27건(`transient` 24 + 킬 3) 중 **41%** 다 — 나머지는 워커 로그 보존창 밖이다.

#### 슬라이스 설계 (사용자 판정 2026-08-04)

**슬라이스 A — 라벨 분해 (관측 전용, 킬 정책 불변).** `_subclassify_direction_divergence` 를
`_subclassify_engine_only_divergence`(`live_signal.py:773-814`)와 **대칭**으로 짠다 — 같은 `except`
관용구, 같은 「조회 불가는 기존 라벨 보존」, 같은 idempotency-key 귀속. 필요한 `order_repo` 는
**이미 탐지기에 넘어가 있고**(`live_signal.py:2726-2731`) `last_bar_time` 은 **같은 함수 스코프의
지역변수**(`:2299`)라 새 조회가 0이다. `qb_live_position_divergence_total` 에 3라벨 추가
(`metrics.py:773-782` 계약 갱신). ★`direction` 은 지금 **한 번도 세분화된 적이 없는 유일한 category** 다.

**판별식** — `horizon = last_bar_time + interval = floor(평가시각, interval)` 에 대해
`t_fill >= horizon` → `replay_lag` / `t_fill < horizon` → `phantom` / 체결 없음 → `unattributed`.
★**한쪽으로만 틀린다** — `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**이라
(`order_repository.py:53,107,129,212`) **`phantom` 을 과소계상하고 `replay_lag` 을 과대계상하지
않는다.** ⇒ **`phantom` 라벨은 신뢰할 수 있다.** 실측 최소 여유 **0.652초**.
★귀속은 `idempotency_key` 로만 — 계정으로 하면 [BL-592] 중복에 걸려 3.7배 부풀려진다.

**★판별식은 경계까지 못박혀 있다 (2026-08-04 연장).**
`backend/tests/scripts/test_classify_direction_divergence.py` **20 테스트** — 경계
`t_fill == horizon` → **`replay_lag`**(부등호를 `>` 로 바꾸면 무해가 유령이 되어 **거짓 사망**.
실측 최소 여유 **0.652초**라 경계는 실제로 붙는다) · 1µs 아래 → `phantom` · 관측 뒤 체결 무시 ·
다른 세션/다른 심볼 **오귀속 금지** · `idempotency_key` 없는 운영자 청산 → `unattributed` ·
interval 일반화(5m 에서 지평이 달라진다) · 사망 상관 **음성 대조**(무해가 사망과 겹치면 False).
★**두 술어가 동치가 아님을 테스트가 명시한다** — 경과 46초(<60)라도 봉 경계 아래면 봉경계식은
`phantom`, 시간문턱식은 `replay_lag`. **실측 11건에서 일치한 것은 우연이다.**
⇒ **슬라이스 A 는 설계가 아니라 전사(轉寫)다.**

★**그 테스트가 실제 결함을 잡았다** — `adjudicate` 가 최신 체결을 `candidates[-1]` 로 집어
**입력 정렬에 의존**했다(SQL 이 `ORDER BY filled_at` 로 주기 때문에만 맞는 코드). 순서가
흐트러지면 오래된 체결을 집어 **무해가 유령으로 조용히 뒤집힌다.** `max(key=filled_at)` 로 교체.
프로덕션 11건 재판정은 완전히 동일 — **실데이터로는 안 드러나는 결함**이었다.
⇒ **슬라이스 A 가 `order_repo` 결과를 쓸 때 정렬을 가정하지 마라.**

**슬라이스 B — 킬 규칙을 인과 판정으로 교체 (사전등록, 분해 데이터 확인 후).**
`phantom` **즉시 킬** / `replay_lag` **절대 안 킬**. 근거 = 위 「한쪽으로만 틀린다」 — 이 방향의
오차는 거짓 사망을 만들지 않는다. 아래 D1·D2 가 동시에 사라진다.
★**대가** — 오늘의 2-strike 유예가 없어지므로 판별기가 틀리면 즉시 사망이다.

#### 함께 등재 — 현행 가드의 잠재 결함 2건 (새 BL 아님)

- **D1 — strike 에 TTL 이 없다.** `live_signal.py:2734`. 설계 주석(`:2711-2714`)이 명시한다:
  판정 못 한 tick 은 **세지도 지우지도 않으므로** 두 관측이 시간상 임의로 멀 수 있다(BL-539).
  ⇒ 무해한 `replay_lag` 2건이 probe 실패를 사이에 두고 이어지면 **건강한 세션을 죽인다.**
  미관측(`probe_failed` 전이력 **2건**)이지만 **도달 가능**하다.
- **D2 — 시장가 반전은 주문 발주 _전에_ strike 를 연다.** probe `:2726` vs dispatch `:2917`.
  ⇒ 시장가 반전은 Celery **3홉**을 다음 판정 평가 전에 끝내야 하고, 못 끝내면 죽는다.
  ★이 소크의 반전 **28건 전부 조건부**(`:cond`)라 이 경로는 **프로덕션 미실행**이다.
  ★★그런데 **[BL-590] 의 복구가 시장가 주문을 낸다** ⇒ 그 복구는 이 가드에게 **60초**를 받는다.
  `recovery_placed`=1 은 **유도된 것**(`InducedBreach`, 세션 `aa0c76b3`)이라 **자연 발화는 0회**다.

★**부수 관측(수리 안 함)** — 킬 counter `qb_live_signal_divergence_total{category="direction"}` 이
**3** 인데 DB 의 `position_divergence` 사망은 **2행**이다. 삭제된 세션이 유력하나 **확인 안 했다.**

---

### BL-592

**우선순위:** P2
**카테고리:** Trading / 거래소 계정 (계측 정합성)
**Trigger:** `exchange_exits` 로 원장 구멍·귀속을 판정하기 전에
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-04 engine-position-ssot ([BL-591] Q2 실측 중 발견)

**같은 Bybit 데모 계정이 두 번 등록돼 있어 청산 원장이 이중 적재된다.**

`trading.exchange_accounts` 에 `bybit demo`(`19a8166a`, 2026-07-25 생성) 와
`bybit demo- aaa`(`0277c150`, 2026-07-26 생성) 두 행이 있고 **같은 거래소 계정을 가리킨다.**
`exchange_exits` 의 유니크 키가 `(exchange_account_id, row_hash)` 라 **같은 청산이 계정마다 한 행씩**
들어간다.

**오라벨이 따라온다.** `classify_exit` 의 `known_order_ids` 는 **계정 스코프**다. 주문을 실제로
가진 계정(`19a8166a`)에서는 `ours` 로 맞게 분류되는 **바로 그 청산**이, 주문이 없는 계정
(`0277c150`)에서는 `unknown` 이 된다.

실측(2026-08-04):

| 계정                   | ours   | unknown | external_manual |
| ---------------------- | ------ | ------- | --------------- |
| `19a8166a` (주문 보유) | **91** | 0       | 12              |
| `0277c150` (주문 없음) | 0      | **91**  | 12              |

★**대칭이 단서였다** — `CreateByUser` 65/65 · `CreateByStopOrder` 26/26 으로 정확히 갈렸다.

**영향 — 계측을 3.7배 부풀린다.** 중복 제거 전 전체 206행 중 미매칭이 119건으로 보이지만 실제
청산은 **103건**이고 원장 밖은 **12건(11.7%)** 이다. [BL-591] 슬라이스 1 이 이 테이블을 관측축으로
쓰므로 **인지하지 않으면 판정이 오염된다.**

**처리 방향 (택일 — 미확정):** ① 미사용 계정 행 정리(참조 무결성 확인 선행 — `orders` ·
`live_signal_sessions` 가 `RESTRICT` 다) ② 거래소 UID 기준 중복 등록 차단
(`backfill_exchange_account_identities` 가 이미 UID 를 채운다) ③ 계측 질의에서만 중복 제거.
★**최소한 ②는 필요하다** — 지금은 같은 계정을 몇 번이든 등록할 수 있다.

**Risk:** 🟡 계측 정합성. 머니-패스는 아니다(각 계정의 주문 스코프는 정확히 분리돼 있다).

**연결:** [BL-591] (이 테이블을 관측축으로 쓴다)

---

### BL-593

**우선순위:** P2
**카테고리:** Trading / 운영자 도구 (원장 완결성)
**Trigger:** 소크를 끄거나 거래소를 손으로 flat 으로 만들기 전에
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 소크 창 미완(soak-gate rc=2 · C1 46.24h/168h). PASS 만 도래다([ADR-024]) (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-04 engine-position-ssot ([BL-591] Q2 실측 중 확정)

**운영자 도구가 청산할 때 원장에 아무것도 안 남는다.**

★**앱 코드에는 원장을 건너뛰는 청산 경로가 없다.** `ClosePositionService.close_position` 은
`OrderService.execute(...)` 를 타므로 **`Order` 행을 남긴다**. `src/` 전체에서 주문을 내는 provider
호출은 `tasks/trading.py:431`(= 원장 경로) 하나뿐이다.

문제는 **그 서비스가 `dependencies.py` 를 통해 HTTP 에만 조립돼 있다**는 것이다. 그래서
`backend/scripts/verify_*.py` · `bybit_demo_smoke.py` 및 임시 정리 스크립트는 그걸 못 쓰고
**provider 를 직접 호출**한다 → 대응 `trading.orders` 행이 없다.

**실측 (2026-08-04, `trading.exchange_exits` 계정 `19a8166a`):** 청산 **103건** 중
`external_manual`(원장 밖) **12건 = 11.7%**. 날짜별 07-24(1) · 07-27(1) · 07-28(2) · 07-31(3) ·
08-01(2) · 08-03(3) — **6일에 걸쳐 상시**다. 단 **12건 중 10건이 「활성 세션 없음」 구간**이고
세션 안은 2건(`dc1e08f1`, 07-31)뿐이다.

**왜 지금 중요한가.** [BL-591] 이 채택한 C 안은 **원장을 진실로 써서 엔진에 주입**한다. 원장에
없는 청산이 있으면 **틀린 포지션을 주입**하게 된다. veto 게이트가 그 순간을 막도록 설계됐지만,
애초에 구멍을 안 만드는 쪽이 근본이다.

**처리 방향:** `ClosePositionService` 를 **HTTP 밖에서 조립하는 진입점**을 만들어 스크립트가
그것을 쓰게 한다. 선례 = `backend/scripts/seed_dogfood.py:11-19`(서비스 계층 직접 호출).
★**검증은 실사용으로 한다** — 정리 후 `exchange_exits` 에 `external_manual` 이 **안 늘고**
`ours` 가 느는지로 판정한다.

**Risk:** 🟡 도구 결함. 다만 [BL-591] C 안의 전제를 직접 갉는다.

**연결:** [BL-591] (원장을 SSOT 로 쓰는 전제)

---

### BL-602

**Priority:** P3
**카테고리:** DX / 커밋 훅 (prettier 플러그인 해석)
**Trigger:** `frontend/` 안의 `*.json` / `*.md` / `*.yml` 을 커밋해야 할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — ★2026-08-07 [ADR-027] 로 **표면이 넓어졌다**: 스택 규칙을 `frontend/AGENTS.md`·`frontend/CLAUDE.md` 로 옮기면서 이 함정에 걸리는 파일이 2개 늘었고, 당장은 `.prettierignore` **회피**로 막아 뒀다(근본 수리 아님). 회피 두 줄은 본 BL 해소 시 함께 지운다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**루트 prettier 가 `frontend/` 안의 json/md/yml 을 포맷하지 못한다.**

**실측 재현 (2026-08-06):**

```
$ ./node_modules/.bin/prettier --check frontend/package.json
[error] Cannot find package 'prettier-plugin-tailwindcss' imported from .../quant-bridge/noop.js

$ ./node_modules/.bin/prettier --check docs/reference/operations/gates-and-traps.md
All matched files use Prettier code style!     ← 루트 밖 파일은 정상
```

**뿌리.** `frontend/.prettierrc` 가 `"plugins": ["prettier-plugin-tailwindcss"]` 를 선언한다.
루트 `package.json` 의 lint-staged 는 `*.{json,md,yml,yaml}` 을 **레포 전역**으로 잡아 **루트**
prettier 로 돌리는데, 루트 `node_modules` 는 husky/lint-staged/prettier **3개뿐**이라(설계상
루트는 도구 전용) 그 플러그인을 해석하지 못한다. prettier 3.x 가 플러그인을 **CWD 기준**으로
찾기 때문에 `frontend/node_modules` 에 있어도 못 본다.

**증상.** `frontend/package.json` 을 포함해 커밋하면 pre-commit 이 `prettier --write` 에서
죽고, 같은 실행에서 eslint 가 `KILLED` 로 함께 넘어져 원인이 가려진다. 이번 회차에는
`package.json` 에 `e2e:ci` 스크립트를 넣으려다 막혀 **ci.yml 인라인으로 우회**했다.

★**과거에 통과한 이력이 있다**(`frontend/package.json` 을 담은 커밋 4건). 그래서 「원래 안 되던
것」이 아니라 **어느 시점에 깨진 것**이다 — prettier/pnpm 버전이나 hoisting 변화가 후보다.
고치기 전에 **언제부터 깨졌는지 먼저 확인해라**(그 4 커밋 시점의 prettier 버전 대조).

**처리 방향(택1, 조사 후 결정):** ① 루트 devDependencies 에 `prettier-plugin-tailwindcss` 추가
② lint-staged 의 `*.{json,md,yml,yaml}` 글로브에서 `frontend/**` 를 빼고 frontend 전용 항목을 신설
③ `frontend/.prettierrc` 의 plugins 를 해석 가능한 절대/상대 경로로.
★**`--no-verify` 는 답이 아니다**(레포 규약 금지).

**Risk:** 🟢 DX 문제이고 프로덕션 무관. 다만 **막히면 커밋 자체가 안 된다.**

**★이연 부채 목록 — 본 BL 이 닫히면 함께 고친다.**

1. (2026-08-06 docs-overhaul) `frontend/README.md:39` 의 구 `.ai/rules/frontend.md` 참조 →
   `frontend/AGENTS.md` 로 갱신.
2. (2026-08-08 zero-touch-bundle) `frontend/AGENTS.md:271` 의 「미등재 경계
   `@media (max-width: 900px)` 5곳은 [BL-646]」이 **이제 거짓이다** — [BL-646] 은 Resolved 이고
   `DESIGN.md §4.3.1` 이 900 을 **콘텐츠 그리드 전용 6번째 경계로 등재**했다. 같은 §10 사다리
   표에 900 행도 필요하다([BL-646] 본문이 이미 지목).
   ★**[확인 필요] 이 항목은 지금도 고칠 수 있을지 모른다** — `.prettierignore:12` 에
   `frontend/AGENTS.md` 가 들어 있어 루트 prettier 가 건너뛴다(2026-08-08 실측:
   `prettier --check frontend/AGENTS.md` **exit 0**, 대조군 `frontend/package.json` exit 1).
   즉 이 파일에 한해 pre-commit 사망 조건이 성립하지 않는다. 이연한 이유는 트랩이 아니라
   **회차 제약**(zero-touch-bundle 은 `frontend/` md 무접촉으로 착수했다)이다. 다음 회차가
   이 두 줄 중 어느 쪽이 맞는지 커밋 한 번으로 확정해라.

**출처:** 2026-08-06 e2e-consolidation (커밋 시도 중 실측 재현)

---

### BL-598

**Priority:** P2
**카테고리:** Backend / 테스트 인프라 (코퍼스 첫-접촉 파싱 비용)
**Trigger:** CI backend 를 **14분 아래**로 내리려 할 때 · pine_v2 코퍼스 테스트를 늘리기 전에
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**코퍼스 스크립트를 「처음」 파싱하는 테스트가 비용을 전부 물고, 이후는 거의 공짜다.**

**실측 (2026-08-06 ci-diet):**

| 대상                              | 단독 실행  | 전체 스위트 안 |
| --------------------------------- | ---------- | -------------- |
| `test_ast_classifier[i3_drfx]`    | **42.66s** | **4.58s**      |
| `test_ast_classifier[i1_utbot]`   | 12.06s     | 0.02s          |
| `test_ast_classifier[i2_luxalgo]` | 6.45s      | 0.04s          |

★샤딩 전에는 알파벳상 앞선 `test_alert_hook` 이 그 값을 치르고 나머지가 무임승차했다. 그래서
이 테스트는 단일 실행 `--durations=10` 에 **아예 안 나타났고**, 샤드 경계를 그 목록으로 잡은
착수 추정이 **2.2배 빗나갔다**(샤드 a 추정 385s → 실측 847s).

**왜 중요한가.** 이 비용은 **프로세스 전역**이라 스위트를 쪼개는 순간 샤드마다 중복된다.
CI 3 샤드 합 **1796s** vs 단일 **1278s** 의 **+519s 전부**가 이 중복이다(고정 오버헤드가 아니다 —
샤드 b 는 70 테스트에 615.42s 인데 top-10 만 596s 를 차지한다). ⇒ **스위트가 샤딩에 저항한다.**
현행 3-way 는 wall 14.8분이 한계고, 재분배로는 못 내려간다(샤드 a 에 `i3_drfx` 소비 파일이 9개 더
있어 `ast_classifier` 를 빼도 다음 테스트가 그 240s 를 문다).

**① 정체 규명 — 확정 (2026-08-08).** 재현 도구 = `backend/scripts/profile_corpus_parse.py`
(인자 없이 돌리면 요약표. `--ramp` / `--solo` / `--cprofile` / `--all`). 정체는 **`pynescript` 가
쓰는 ANTLR4 ALL(\*) 어댑티브 예측의 DFA 캐시가 「파싱에 의해」 지연 구축되는 것**이다 —
import 워밍업도 아니고 입력 크기 법칙도 아니다.

| 축               | 실측                                                                                           | 판정                                             |
| ---------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| import 비용      | `classify_script` import **0.26s**(warm), import 직후 DFA 상태 **0**                           | **(a) 기각** — cold 합계의 0.4% (**warm 한정**)  |
| 코퍼스 cold/warm | 9벌 cold 합계 **71.25s** vs 같은 프로세스 warm **5.77s**                                       | 첫-접촉 프리미엄 **91.9%**                       |
| `i3_drfx` 단독   | cold **42.19s** / warm **3.80s**                                                               | warm 이 전체 스위트 안 4.58s 와 일치             |
| **인과 대조**    | 같은 프로세스·같은 입력에서 캐시**만** 비우니 3.68s → **51.37s**, 다시 3.69s                   | 원인이 캐시 상태임을 **인과로 확정** (14.0배)    |
| **성분 분리**    | `parser_dfa` 만 비움 **55.16s(15.0배)** · `shared_ctx` 3.82s(1.0배) · `lexer_dfa` 3.93s(1.1배) | 비용을 지는 것은 **파서 DFA 하나**뿐             |
| cold 램프        | **조각마다 새 프로세스**. 크기 8.6배 → cold 8.39s→**50.80s**(6.1배), log-log 기울기 **0.78**   | **(b) 기각** — 초선형이 아니라 **sublinear**     |
| warm 램프        | log-log 기울기 1.25 이나 꼬리 절반은 크기 1.6배 → 시간 1.1배(sublinear)                        | **(b) 기각** — warm 5.77s 로 42.66s 를 못 만든다 |
| 샤딩 중복        | 프로세스 9개로 쪼개면 합계 **122.82s** vs 단일 프로세스 **69.93s**                             | 중복분 **+52.89s** 를 실측으로 확인              |

★**램프는 두 축을 분리하지 못한다** — 한 파일의 prefix 는 「글자 수」와 「처음 보는 문법
결정 수」가 **함께** 자란다(기울기 0.78 vs 0.84 로 사실상 구분 불가). 램프가 답하는 것은
「초선형인가」뿐이고 답은 **아니다**. 축을 가르는 것은 아래 성분 대조다.

기전: `PinescriptParser.decisionsToDFA` 가 generated 파서의 **클래스 속성**(`PinescriptParser.py:346`)
이라 프로세스 전역이고, 파서 인스턴스는 생성 시점에 그것을 읽는다
(`ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)`).
cProfile 누적시간 99% 가 `adaptivePredict` → `execATN` → `closure_`(2,396만 호출)다.
⇒ 「프로세스 전역이라 샤딩하면 중복된다」는 위 진단은 **맞았다**. 틀린 것은 원인 후보
2개(import·크기)뿐이다.

★**성분 분리가 없으면 「ANTLR 캐시가 원인」까지밖에 못 간다.** 초판은 파서 DFA·
`sharedContextCache`·렉서 DFA 를 한꺼번에 비워 놓고 결론을 「DFA 가 원인」이라고 적었다 —
셋을 묶어 비운 실험은 그 문장을 지지하지 못한다. 하나씩 비우자 **파서 DFA 만 15.0배이고
나머지 둘은 1.0/1.1배**로, 결론이 좁혀지는 동시에 강해졌다.

★★**2026-08-08 결론 문구 정정 — 「parser DFA **단독**이 원인」은 과대 진술이었다.**
성분 루프가 회차마다 `→ warm` 으로 **다시 데우므로**, `shared_ctx` 를 비울 때 parser DFA 는
**이미 워밍돼 있었다.** 그 배치에서 나온 1.0배가 지지하는 문장은

> **parser DFA 가 워밍된 상태에서는 나머지 둘이 추가 비용을 지지 않는다**

까지다. 「shared_ctx 는 무관하다」가 아니다. **처방(파싱 결과 디스크 캐시)은 그대로 지지된다** —
파싱을 아예 안 하면 셋 다 안 쌓이므로 성분 배분과 무관하다. 근거 진술만 좁힌다.

★**independent control 을 실제로 재서 순서 의존을 배제했다**(`--components`, 2026-08-08).
성분마다 **새 프로세스**를 띄워 리셋 직전 상태를 「cold 1회 + warm 1회」로 셋 다 동일하게 맞췄다:

| scope        | cold_s | warm_s | after_reset_s | 배수       |
| ------------ | ------ | ------ | ------------- | ---------- |
| `parser_dfa` | 51.28  | 3.80   | **52.70**     | **13.9배** |
| `shared_ctx` | 51.15  | 3.74   | 3.85          | 1.0배      |
| `lexer_dfa`  | 51.30  | 3.82   | 3.93          | 1.0배      |

순서 의존이 사라져도 결과가 같다 ⇒ [8] 의 15.0/1.0/1.1 은 **측정 순서의 산물이 아니다.**
다만 이것도 **조건부 문장을 확증할 뿐 단독 기여를 재지 않는다** — 리셋 시점에 parser DFA 는
여전히 데워져 있다.

★**[확인 필요] clean first-touch 성분 분해는 미측정이다.** 「셋 다 비어 있는 상태에서 각
성분이 첫 파싱의 몇 초씩을 가져가는가」는 이 도구가 답하지 않는다 — 캐시를 **끈 채로** 파싱할
수단이 없어서(비우면 즉시 다시 쌓인다) 실험 설계 자체가 없다. ② 가 디스크 캐시로 닫히면
이 분해는 필요 없어지므로 **하지 않기로 했고, 여기 적어 둔다.**

**② 처리 방향 — 테스트 쪽에서 닫힌다 (`backend/src` 0줄).** 파싱 시간이 크기에 초선형이
아니므로 **파서에는 고칠 표적이 없다**. 표적은 「테스트가 파싱을 한다」는 사실 자체다.

★**단, `classify_script()` 만 캐시하면 안 닫힌다.** 코퍼스를 읽는 테스트가 **30 파일**이고
그중 `i3_drfx` 를 건드리는 것이 **10 파일**이다. 진입점도 `classify_script`·`extract_content`·
`analyze_coverage`·`classify_message`(alert hook)·`parse_and_run_v2` 로 갈린다.
`test_ast_classifier` 만 캐시하면 **그 샤드의 다음 테스트가 같은 워밍업을 그대로 문다.**

닫는 자리는 **하나**다 — `src/strategy/pine_v2/` 의 7 모듈이 전부 `from pynescript import ast
as pyne_ast` 뒤 `pyne_ast.parse(...)` 를 부르므로 **호출 시점에 같은 모듈 객체의 속성**을 본다.
⇒ `conftest.py` 에서 `pynescript.ast.parse` 를 **소스 해시 키 디스크 캐시로 감싸면** 7 진입점이
한꺼번에 덮인다. `tests/` 안에서 끝나므로 `backend/src` 0줄이다(baseline 재생성 경로는 캐시
우회 플래그로 남긴다).

캐시 매체는 **pickle 로 확인됐다** — AST 노드가 module-level `@dataclass` 라 그대로 직렬화된다.
`s1_pbr` 실측: cold 파싱 **5.316s** vs unpickle **0.0002s**(6,542 B, 타입·`body` 길이 보존).
파싱을 **약 3만 배** 싼 역직렬화로 바꾸는 것이라 ② 의 이득은 구조적으로 확보된다.
[확인 필요] 캐시가 켜진 상태에서 **코퍼스 소비 테스트 전량이 여전히 green 인지**는 ② 착수 시
확인한다(위 실측은 타입·`body` 길이까지만 대조했다).

③ ②가 되면 샤드마다 중복되던 비용이 사라져 샤드 재분배로 추가 이득이 열린다.

★★**사거리 — 위 결론은 전부 `warm` 프로세스 한정이다. cold 축은 미측정이다**(2026-08-08 정정).
프로파일러 `section_import` 는 **첫 서브프로세스를 버린다** — 그 첫 회가 **17초**였고 그 안에
bytecode(`.pyc`) 컴파일 + OS 파일 캐시 워밍이 섞여 있다. 버린 뒤 3회를 재서 나온 것이
0.26s 다. 그런데 **CI 러너는 cold 다** — `.pyc` 도 파일 캐시도 없이 시작한다.
⇒ 「import 는 cold 합계의 0.4% 라 무시 가능」은 **[BL-598] 이 정의하는 현상**(같은 머신,
warm 프로세스에서 단독 42.66s vs 스위트 안 4.58s)에 대해서만 참이고, **cold CI 를 배제하지
않는다.** 그 축은 신규 **[BL-652](#bl-652)**.

★★**규모 대조는 하지 않았다 — 「+519s 전부가 이 중복」은 여전히 미검증 가정이다**
(2026-08-08 zero-touch-bundle `/code-review` 지적). 착수 spec 이 든 숫자와 ①의 실측은 **잰 양이 다르다**:

| 출처                | 단위                                         | 값                              |
| ------------------- | -------------------------------------------- | ------------------------------- |
| 착수 spec (CI 실측) | pytest **3샤드** wall 합 vs 단일             | 1796s vs 1278s ⇒ **+519s**      |
| ① 실측 (로컬)       | 코퍼스 파싱만, **9프로세스** 합 vs 1프로세스 | 122.82s vs 69.93s ⇒ **+52.89s** |

두 값은 **약 10배** 차이인데, 그 차이가 규모 때문인지 다른 성분 때문인지 **아무도 대조하지 않았다.**
셈만 해 보면 대조가 필요한 이유가 보인다 — 「샤드마다 코퍼스 첫-접촉을 한 번씩 다시 문다」 모형에서
샤드 3개의 중복은 `(3-1) × 프리미엄` 이고, 이 맥의 프리미엄은 **65.48s**(cold 합 71.25 − warm 합 5.77)라
**약 131s** 다. 519s 의 **25%** 다. 나머지를 이 모형으로 덮으려면 CI 러너의 cold 파싱이 이 맥보다
**약 4배** 느려야 하는데, 그건 방향으로는 그럴듯해도(러너 2 vCPU) **잰 적이 없다.**
★그리고 ①의 `+52.89s` 를 샤드 프리미엄으로 읽으면 안 된다 — 그 실험은 코퍼스 9벌을 **9프로세스로
쪼갠** 것이라 프로세스마다 **자기 조각 하나만** 파싱한다. 샤드가 코퍼스 전체를 다시 무는 CI 상황과
**모집단이 다르다.** ⇒ 이 축을 닫으려면 **CI 에서** 샤드 수를 바꿔 가며 재야 한다. 여기서는
**미대조**로 적어 둔다(추정치를 지어내지 않는다). [BL-652] 의 cold import 축도 같은 자리에서 열린다.

★**「캐시가 있을 것이다」로 시작하지 마라** — 찾아봤고 없었다. 관측부터 해라.

★**절대초를 인용하지 마라 — 배수를 인용해라.** 같은 cold 파싱이 머신 부하에 따라 41~68s 로
흔들렸다. 재현 가능한 것은 순위와 배수(cold/warm ≈ 14배)이지 절대시간이 아니다.

**[확인 필요]** ANTLR `PredictionMode.SLL` 로 낮추면 예측 비용이 급감하지만 모호 문법에서
오파싱 위험이 있고, 그 설정 지점이 `pynescript` 의 `parse()` 경로 **안**이라 이번 축에서는
건드리지 않았다. ② 가 디스크 캐시로 닫히면 이 선택지는 열 필요가 없다.

**Risk:** 🟢 CI 시간·비용 문제이고 프로덕션 정확성과 무관. 단 **테스트 시간 추정을 반복해서
빗나가게 만드는** 원인이라 계측 신뢰도에 영향.

**연결:** [BL-583] (수집 집합이 결과를 바꾼 선례 — 같은 「무엇이 함께 도는가」 축)

**출처:** 2026-08-06 ci-diet (CI run 31071389290 잡별 실측 부검)

### BL-599

**Priority:** P3
**카테고리:** Backend / 죽은 코드 (Pine v1 shim)
**Trigger:** `BacktestOutcome` 를 손볼 일이 생겼을 때 (단독으로 열지 마라 — 이득 대비 파급이 크다)
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**Pine v1 shim(`src/strategy/pine/`, 135L)은 타입 4종만 재export 하는 껍데기다.**
lexer/parser/interpreter/stdlib/v4_to_v5/ast_nodes 6 모듈(2146L)은 이미 제거됐고, 남은 것은
`ParseOutcome / SignalResult / SourceSpan / PineError` 뿐이다.

**왜 아직 못 지우나.** `BacktestOutcome.parse: ParseOutcome` 이 코어 DTO 필드라서다. 소비처는
**「2곳」보다 넓다**(2026-08-06 실측): 프로덕션 import 2곳(`backtest/engine/types.py:13` ·
`v2_adapter.py:39`) + `BacktestOutcome(...)` 생성 site **10곳 이상**(v2_adapter) + 테스트 3파일
(`tests/backtest/engine/test_types.py` · `tests/strategy/pine/test_types.py` · `test_errors.py`).
`walk_forward.py` 도 `BacktestOutcome` 을 타입으로 받는다.

**처리 방향:** shim 제거는 `BacktestOutcome.parse` 철거와 **동시에만** 의미가 있다.
① 그 필드가 실제로 소비되는지(API 응답까지 나가는지) 먼저 추적 ② 안 나가면 필드 제거 +
생성 site 정리 ③ 그 뒤 `src/strategy/pine/` 삭제. ★①을 건너뛰고 shim 만 옮기면 순환만 늘어난다.

**Risk:** 🟢 순수 정리. 다만 코어 DTO 를 건드리므로 백테스트·최적화·스트레스 3 소비자에 동시 파급.

**출처:** 2026-08-06 dead-code-sweep

---

### BL-600

**Priority:** P3
**카테고리:** Backend / 명명 (CONTEXT 헌법 충돌)
**Trigger:** `trading_sessions` JSONB 키를 마이그레이션할 일이 생겼을 때 · 신규 도메인 용어 정리 시
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`strategy/trading_sessions.py:26` 의 `TradingSession` 이 CONTEXT.md 의 _Avoid_ 이름과 충돌한다.**
헌법은 **TradingSession** 을 「미구현 phantom — 실제 lifecycle 은 LiveSignalSession + Order +
LiveSignalEvent」로 못박아 두었는데, 이 파일은 같은 이름을 **장중 시간대 필터**(asia/london/ny)로
쓴다. 의미가 다른 동음이의어라 헌법을 읽고 온 사람이 정확히 반대로 이해한다.

★**단순 rename 이 아니다.** 이 값은 `Strategy.trading_sessions` **JSONB 에 문자열로 영속**되고
(`SESSION_VALUES` frozenset), 백테스트 엔진과 라이브 executor 양쪽이 읽는다. 게다가 trading 도메인에
`TradingSessionClosed` 예외와 `TradingSessionTzNaiveReject` 가 따로 있어 grep 만으로는 안 갈린다.

**처리 방향:** ① JSONB 에 실제로 들어 있는 키/값 분포를 먼저 조사 ② 코드 심볼만 개명
(`MarketSession` 등) 하고 **영속 값은 건드리지 않는** 안이 최소 ③ 예외 이름 2종도 같이 볼지 판단.

**Risk:** 🟡 영속 데이터가 걸려 있어 rename 을 코드에만 적용해야 한다.

**출처:** 2026-08-06 dead-code-sweep

---

### BL-601

**Priority:** P3
**카테고리:** Backend / 죽은 코드 (호출 0건)
**Trigger:** `OrderRepository` 를 손볼 때 함께 · 다음 dead-code 스윕
**Est:** S
**상태:** ✅ **Resolved (2026-08-09, W2)** — 저장소 메서드 2건은 제거, 하네스 1건은 **제거 대신 게이트 배선**.

**★처리가 3종 동일하지 않다 — 근거가 하나 반증됐다 (2026-08-09).** 아래 「앞의 둘은
`final-gates.sh` 체인 안에 있다」는 **절반이 거짓**이었다. 실측 — `final-gates.sh` 가 실제로
부르는 것은 `bl-audit-test.sh` **하나뿐**(`:156`)이고, `pre-push-guard-test.sh` 는 산문 참조
3곳(`.husky/pre-push:23` · `soak-gate.sh:250` · `lib/pre-push-ref-guard.sh:6`)만 있다. 즉
`fleet-dispatch-test.sh` 를 지우고 `pre-push-guard-test.sh` 를 살리는 판별 기준이 성립하지 않는다.
게다가 그 하네스는 **지금 30/30 통과**하고 원본에서 `sed` 로 술어를 떼어내므로 사본 드리프트가 없다
(이름이 바뀌면 추출 실패로 죽는다 — 실측: `qb_injectable` 을 개명하니 exit 0 → **exit 1**).
⇒ 「호출자 0」이라는 불만은 **삭제가 아니라 배선**으로 해소했다(`final-gates.sh` 신규 1줄).

**처리 결과:**

| 대상                                                          | 처리                                                          |
| ------------------------------------------------------------- | ------------------------------------------------------------- |
| `OrderRepository.get_state_fresh` (`order_repository.py:280`) | **제거** — BL-499 도입, 호출자 소멸                           |
| `OrderRepository.list_unsynced_reduce_only_since` (`:733`)    | **제거** — 복구 경로가 재구현돼 있다(아래)                    |
| `scripts/fleet-dispatch-test.sh`                              | **존치 + `final-gates.sh` 배선** — 살아 있는 코드의 단언 30건 |

**★`list_unsynced_reduce_only_since` 가 왜 죽었나 (코드 대조).** `6b200e59` 에서 도입됐고
`0a8e229b`(exit-attribution)이 스윕을 **계정 독립 열거**로 재작성하면서 호출자가 사라졌다. 복구
경로 자체는 살아 있다 — 대체물은 같은 파일의 `list_unsynced_reduce_only`(계정 스코프 · 시간창
없음)이고 `src/tasks/trading.py:2118` 이 매 스윕마다 부른다. 즉 **기능이 아니라 시간창 술어만
버려진 것**이라 제거가 안전하다.

**원 관측 — 호출자가 0인 채 남아 있는 것 3종** (2026-08-06 실측 — 정의 줄 외 참조 0):

| 대상                                                          | 비고                                                       |
| ------------------------------------------------------------- | ---------------------------------------------------------- |
| `OrderRepository.get_state_fresh` (`order_repository.py:280`) | 테스트도 없다                                              |
| `OrderRepository.list_unsynced_reduce_only_since` (`:733`)    | 테스트도 없다                                              |
| `scripts/fleet-dispatch-test.sh`                              | 자기 docstring 외 참조 0. `fleet-dispatch.sh` 는 살아 있다 |

★**원안의 「고아 하니스 3종」은 1종으로 정정한다** — `bl-audit-test.sh` ·
`pre-push-guard-test.sh` · `sentinel_bl181_worker_reload.sh` 는 **고아가 아니다**(각각 backlog ·
soak-gate 주석 · dev-log 가 참조한다). ~~앞의 둘은 `final-gates.sh` 체인 안에 있다~~ →
**2026-08-09 반증 — 체인 안에 있는 것은 `bl-audit-test.sh` 하나뿐이다**(위 상태 블록 참조).

**처리 방향:** 지우기 전에 **왜 만들어졌는지** 한 번 본다 — `list_unsynced_reduce_only_since` 는
reduce-only 동기화 복구용으로 보이므로, 그 복구 경로가 다른 방식으로 구현됐는지 확인 후 제거.

**Risk:** 🟢 순수 정리.

**출처:** 2026-08-06 dead-code-sweep

---

### BL-603

**Priority:** P2
**카테고리:** Backend / backtest 비용 모델
**Trigger:** 백테스트 손익을 라이브 예측치로 읽기 전
**Est:** S
**상태:** ✅ **Resolved (2026-08-07 gap-resync-autopsy 회차)** — 기본값을 실측으로 교체했다.
`fees` 0.001→**0.00055** · `slippage` 0.0005→**0.00014** · `maker_fee` **불변**(Bybit maker
0.02% 와 이미 일치). 왕복 **0.300%→0.138%**.
★**두 SSOT 를 같이 옮겼다** — `engine/types.py:34-38` 만 고치면 `backtest/schemas.py` 의
Pydantic 기본값이 항상 채워져 **사용자 제출 경로는 안 바뀐다**(실측 확인). FE 미러 4곳
(`assumptions-card.tsx`·`useBacktestForm.ts`·`rerun-button.tsx`·`BacktestCostFieldSet.tsx`
안내문)과 e2e `house_default` 픽스처도 함께. `_house_default_assumption()` 은 `BacktestConfig()`
를 런타임에 읽어 **자동으로 따라온다**([BL-526] 표면).
★**프리셋 안은 기각** — 백테스트 요청 스키마에 exchange/mode 필드가 **없어서**(`schemas.py:30-61`
실측) 키로 삼을 축이 없다. 프리셋을 두려면 도메인 입력부터 신설해야 해서 범위 밖이다.
★**손계산 오라클을 다시 손으로 계산했다**(`test_golden_oracle_ema_sltp.py`, LESSON-039
anti-circular): entry taker 100×0.00055=0.055 + exit maker 110×0.0002=0.022 ⇒ fees 0.077 ·
slippage 100×0.00014=0.014 · net 9.909. 엔진 출력과 **첫 시도에 일치**.
★코퍼스 baseline 재생성(`regen_trust_layer_baseline.py --confirm`) — 변경 5% 초과라 근거를
남긴다. **`num_trades` 는 7 코퍼스 전건 불변**(비용은 체결 집합을 안 바꾼다)이고 손익만 움직였다.
`s3_rsid` 는 total_return **−1.083 → +0.184**, profit_factor **0.881 → 1.022** 로 **부호가
뒤집혔다** — 이 BL 이 말한 「비용 민감 전략의 부당 탈락」의 실물이다.

**백테스트 비용 가정이 라이브 실효 비용의 2.7배다.**

**실측 (2026-08-06 backtest-reality-gap, 원장 dedup 84 event · 31.4h · 엔진 무경유 산술):**

- 라이브 실효 비용 = **taker 0.055%/leg 단일 성분** — 잔차(`closed_pnl − gross`)가 84 event
  전건 음수이고 77건이 소수 8자리까지 −0.055% 와 일치, 비-taker 잔차 합 +0.055 USDT(총비용의
  0.03%). 펀딩 가설은 2×2 표로 반증(필요조건도 충분조건도 아님). 왕복 **0.1101%**.
- 백테스트 기본 가정 = fees 0.1% + slippage 0.05% /leg = 왕복 **0.30%** (`engine/types.py:34-38`).
- 매칭쌍(34) 진입가 잔차 중앙 **0.014%** — slippage 가정 0.05% 의 1/3 자릿수.
- 크기 감각: 이 창의 라이브 Σgross +28.27 vs Σ비용 −172.83 — 비용이 전략 손익의 6.1배라
  비용 가정의 2.7배 오차는 결과 부호를 좌우한다.

**처방 후보(수리는 미착수):** 기본 fees/slippage 를 실측 기반으로 좁히거나, 거래소·모드별
프리셋(Bybit demo taker 0.055%)을 둔다. BL-526 표면의 `house_default` 가정 표기도 함께.

**Risk:** 🟡 판단 근거의 보수성 방향이 일관되게 비관(비용 과대)이라 안전하지만, 전략 선별을
왜곡한다(비용 민감 전략을 부당하게 탈락).

---

### BL-605

**Priority:** P2
**카테고리:** Backend / trading (exchange_exits 적재)
**Trigger:** exchange_exits 를 집계로 소비하는 코드를 추가하기 전
**Est:** S
**상태:** ✅ **Resolved** (2026-08-09 excl) — 스윕 계정 루프가 `exchange_uid` 로 접힌다(`src/trading/account_identity.py:dedupe_accounts_by_exchange_uid`). 회귀 = `test_sweep_visits_one_row_per_real_exchange_account` — **수리 전 red 를 되돌려 실증**했다(`accounts=2`·조회 2회·원장 2행 → 수리 후 1/1/1). ★같은 회차에서 **테스트 하네스도 고쳤다**: 페이크 `upsert_rows` 가 `row_hash` 단독으로 접고 있어 실제 UNIQUE 축 `(exchange_account_id, row_hash)` 를 흉내내지 못했고, 그래서 **2배 적재를 하네스가 가리고 있었다**. 기존 574행은 그대로 둔다(계정 필터가 소비를 가른다)

**`exchange_exits` 가 같은 청산 event 를 정확히 2행으로 적재한다.**

**실측 (2026-08-06, eval2):** 08-05 이후 172행 = **86 event × 정확히 2행**. 각 쌍은
`closed_pnl`·`closed_size`·`avg_entry/exit_price`·`exchange_created_at` 이 한 필드도 다르지
않고, 다른 것은 `id`·`matched_order_id`(ours 만 보유)·`classification`(`ours`/`unknown`)·
`attribution_confidence` 뿐. ⇒ `SUM(closed_pnl)` 형 소비는 손익을 **정확히 2배** 계상한다
(실측 −289.13 vs 진값 −144.57). `row_hash` 컬럼이 있는데도 중복이 들어온다.

### ★2026-08-08 — 뿌리 확정. **코드가 아니라 데이터였다** (soak-attribution-close)

~~적재 경로가 분류 pass 별로 행을 새로 쓰는 것으로 보인다(뿌리 미확정)~~ → **틀렸다.** 분류
pass 는 하나뿐이다. 뿌리는 **스윕 루프의 계정 행 중복 열거**다.

`_sweep_closed_pnl_with_session`(`backend/src/tasks/trading.py:1904-1906`)이
`ExchangeAccountRepository.list_by_exchange`(`exchange_account_repository.py:40-47`)로 계정
**행**을 열거하는데 `exchange_uid` dedup 이 없다. DB 에는 같은 `exchange_uid` **558689281** 을
공유하는 계정 행이 **2개**다(`19a8166a` `bybit demo` · `0277c150` `bybit demo- aaa`
`read_only=t` — [BL-517](#bl-517)). 두 행이 **같은 실제 Bybit 계정의 같은 closed-pnl 창**을 각자
조회한다.

`compute_row_hash`(`models.py:857-898`)의 해시 입력 8개는 **전부 거래소 원본 값**이고
`exchange_account_id` 가 **안 들어간다** ⇒ 두 행의 `row_hash` 는 **동일**하다. 그런데 UNIQUE 축은
`(exchange_account_id, row_hash)`(`models.py:775`)라 **충돌하지 않고 둘 다 들어간다.**
⇒ **배수 = 같은 uid 를 공유하는 계정 행 수 = 2.**

`ours`/`unknown` 쌍이 나오는 이유도 같은 코드다 — 매칭이 계정 스코프이기 때문이다
(`order_repository.py:753-765`, `WHERE exchange_account_id == account_id AND state == filled`).
주문이 달린 행에서만 `matched_order_id` 가 잡혀 `ours`/`exact` 가 되고, 형제 행은 구조적으로
`unknown`/`none`/`matched_order_id IS NULL` 이 된다.

**서버 DB 실측 (2026-08-08):** `trading.exchange_exits` **574행 = 287 × 2**. 287개 `row_hash`
**전량**이 두 계정에 걸쳐 있다(`having count(distinct exchange_account_id)=2` 가 287/287).
계정별 분포 = `19a8166a`: `ours/exact` 262(미조인 0) + 나머지 25 / `0277c150`: 287 전량 미조인.

**처방 (확정):** 스윕 계정 루프에서 같은 `exchange_uid` 는 **대표 1행만** 스윕한다. 선례가 이미
레포에 3곳 있다 — `tasks/trading.py:507-512` · `:851` · `websocket/position_fanout.py:69-80`
(`list_by_exchange_uid` 로 형제를 펴는 관용구). 기존 574행은 그대로 두어도 계정 필터가 소비를
가르므로 과거 데이터 해석이 안 바뀐다.

~~**처방 후보:** 적재 시 `order_link_id` 단위 upsert 로 분류만 갱신, 또는 소비 계약에
「`classification='ours'` 필터/`DISTINCT order_link_id` 의무」를 정본화.~~ → **폐기.** 둘 다
표적을 빗나간다. `order_link_id` upsert 는 두 행의 `exchange_account_id` 축이 달라 unique 로
흡수되지 않고(형제 행은 `meta_by_order_id` 경로를 타야만 `order_link_id` 가 채워진다),
소비 계약 dedup 은 증상을 소비처마다 반복해 막을 뿐 적재를 안 고친다.

**이 처방이 안 고치는 것:** 포지션·미체결 조건부의 **2중 계상**. 배타성 판정식이 같은 병을 앓는다
— [BL-651](#bl-651) 로 분리했다.

**소비처 전수 (2026-08-06 entry-set-divergence, eval/codex 정적 전수 + CONTROL 코드·데이터
대조):** 런타임 소비처 7곳 분류 완료 — eval 의 「확정 머니-패스 2배」 판정은 **CONTROL
실측으로 조건부로 강등**됐다: `aggregate_closed_pnl()`(`exchange_exit_repository.py:43-58`,
dedup 없는 `SUM`)이 `Order.realized_pnl` 로 흘러가는 경로(`tasks/trading.py:2110-2163`,
backfill/resync)는 코드상 무방비가 맞지만, **실데이터에서 `ours`/`unknown` 2행은 서로 다른
`exchange_account_id` 로 적재**돼 단일 계정 필터가 사실상의 dedup 역할을 한다(실기록
reduce-only 3건 전부 1배 정확 — DB 실측). ⇒ 이 BL 의 실체는 「지금 2배가 흐른다」가 아니라
**「dedup 이 명시적 설계가 아니라 계정 분리의 부수효과이고, 그 invariant 를 강제하는
코드·테스트가 없다」**. 같은 계정 안에 같은 `exchange_order_id` 중복이 적재되는 형상이
생기면 즉시 2배가 된다. 그 외: `parity_repository.py:430-478` `ledger_only_net` 은 분류
필터로 조건부 · `tasks/trading.py:1852-1880`(알림)·`_derive_ledger_values`(2행 fail-closed)·
count 류·`btgap_compare.py`(자체 dedup)는 무해. **테스트 사각 6곳** — `ours`/`unknown` 동일
payload 쌍의 2배 방지를 검증하는 테스트가 0건(eval 전수 표 = PR 의
`.claude/fleet/entryset/reports/eval-report.md` Phase 1).

**Risk:** 🟡 현재 형상에서는 1배가 실측 사실. 수리 범위 = invariant 명문화(적재 경로) +
음성 대조 테스트 — 이번 회차 범위 밖.

---

### BL-610

**Priority:** P2 (~~P3~~ — 2026-08-07 전수 재검출로 상향. 인덱스 행은 처음부터 P2 표에 있었고,
사용자 표면 2곳이 확인돼 섹션 선언을 표에 맞춘다)
**카테고리:** Backend / trading (문자열·메타데이터) + Frontend 주석
**Trigger:** BL-003 소크 창 종료 후 첫 `backend/src` 정리 회차
**Est:** XS → **S** (1곳 → 10곳)
**상태:** ✅ **Resolved** (2026-08-08 soak-mortality-repair — 10/10 수리, 재검출 `DANGLING` 0건)

**코드·테스트·설정 10곳이 삭제된 문서 경로를 가리킨다.** 문서 대개편(ADR-026, fix-doc)이
`docs/archive/`·dev-log 원문을 지웠다. 소크 활성 중 `backend/src` 무접촉 원칙 때문에 이번 회차에서
고치지 않고 이연한다. **2026-08-07 PR #554 리뷰에서 전수 재검출** — 최초 등재 시엔 1곳만 잡았다.

★**2026-08-08 수리 — 두 갈래로 갈랐다.** 사용자 표면 2곳과 개발자 참조 8곳은 같은 처방을 못 쓴다:

- **사용자 표면 2곳 = 참조 자체를 제거**했다. tombstone 은 `git:<sha>` 좌표라 API 응답·UI 문자열에
  넣으면 사용자에게 쓸모가 없다. 남은 문장이 이미 필요한 정보를 다 준다(무엇이 왜 degraded 인지).
  추적용 tombstone 은 **바로 위 코드 주석**으로 옮겼다.
- **개발자 참조 8곳 = tombstone 접두사**. 경로는 **보존한다** — 원문을 꺼내려면 경로가 필요하다.

★**삭제 커밋이 하나가 아니었다.** heikinashi ADR(4곳이 가리킨다)은 문서 대개편이 아니라
**2026-05-15 `b9a51b6a`** 에서 이미 사라졌다 ⇒ 직전 `git:590eeec9`. 나머지 5경로는 대개편
`94da86b1` 이므로 직전 `git:0ddf2b53`. **한 sha 로 전부 찍었으면 4곳이 빈 좌표를 가리켰다.**

★**아래 재검출 명령을 갱신했다** — 종전 명령은 tombstone 을 인식하지 못한다. 경로 문자열을 그대로
두는 것이 tombstone 의 목적이므로, 수리 후에도 종전 정규식은 10곳을 전부 `DANGLING` 으로 낸다.

★**그중 2곳은 사용자에게 그대로 보인다** (주석이 아니다):

- `backend/src/backtest/service.py:191` — `StrategyDegraded.detail` 에 `"See docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md."` 가 들어가 **API 응답으로 나간다**
- `backend/src/strategy/pine_v2/coverage.py:697` — heikinashi 경고 문자열의 `"참고: …"` 가 **UI 로 표면화된다**

나머지 8곳 (동작 무해):

- `backend/src/trading/entry_completeness.py:158` — `source=` 메타데이터 (최초 등재분)
- `backend/prometheus/alerts.yml:14` · `backend/tests/strategy/pine_v2/{test_coverage_sprint21.py:197,test_dogfood_pine_corpus_e2e.py:56,test_trust_layer_parity.py:10}`
- `frontend/src/__tests__/design-canon-tokens.test.ts:62` · `frontend/src/app/(dashboard)/backtests/_components/charts/equity-chart-v2.tsx:9` · `frontend/src/components/charts/trading-chart.tsx:4`

수리 = tombstone 형식(`git:<삭제직전sha> <경로>`) · 현존 정본 경로 · 사용자 표면이면 제거.
재검출 명령 (게이트가 아니라 손으로 돌린다. ★`-n` 과 tombstone 제외가 둘 다 필요하다 —
`-n` 이 없으면 `read` 의 필드가 밀려 `[ -e "$p" ]` 가 **빈 문자열을 검사해 전건 오탐**한다):

```bash
git grep -noE '(git:[0-9a-f]{7,8} )?docs/(archive|dev-log)/[A-Za-z0-9_./-]+\.(md|html)' \
  -- backend frontend \
  | while IFS=: read -r f l p; do
      case "$p" in git:*) continue;; esac
      [ -e "$p" ] || echo "DANGLING $f:$l -> $p"
    done
```

★`scripts/docs-audit.sh:81~83,128` 의 4건은 **안내 메시지 문자열**이라 별개다 — 검사 로직은
legacy 문자열의 존재 여부만 보므로 동작 영향이 없다. 같이 고쳐도 되고 두어도 된다.

**Risk:** 🟡 8곳은 주석 수준이지만 **2곳은 사용자 표면**이다 — 지금도 없는 파일을 안내하고 있다.

---

---

### BL-611

**Priority:** P2
**카테고리:** DX / 문서 로딩 (ADR-026 후속)
**Trigger:** 다음 Sprint kickoff (Type A/B) 전
**Est:** S
**상태:** ✅ **Resolved (2026-08-07, PR #554 리뷰 회차)** — 후보 ⑴ 채택. `AGENTS.md` 에
`## 메타-방법론 (영구)` 블록 신설, §8.1(kickoff baseline preflight)·§8.3(codex finding 코드 대조)
두 줄만 본문으로 승격하고 §8 전문은 링크로 남겼다. **§8.2/§8.4/§8.5 는 의도적으로 인라인하지
않는다** — 그 셋은 트리거가 외부 사건(PR 머지 / codex G.0 산출물 / 신규 모듈 신설)이라 그 시점에
문서를 여는 흐름이 이미 있다. §8.1·§8.3 만이 **아무 신호 없이 건너뛰어진다**.
★**판정 방법은 하나뿐** — 새 세션을 띄워 그 블록이 컨텍스트에 들어오는지 육안 확인한다
(루트 `AGENTS.md` 는 `CLAUDE.md` 가 import 하므로 무조건 로드된다).

**메타-방법론 영구 규칙이 「매 세션 자동 로드」에서 「열어야 읽힘」으로 강등됐다.**
구 `.ai/common/global.md` 는 `paths` frontmatter 가 없어 `.claude/rules/global.md`(심볼릭) 경유로
**무조건** 로드됐다 — 2026-08-07 실측 재현: 그 세션 컨텍스트에 `global.md` 가 들어와 있었고
`paths` 가 있는 backend/frontend/nextjs-shared/typescript 는 로드되지 **않았다**.
ADR-026 은 §7(메타-방법론 영구 규칙)을 `generator-evaluator-pipeline.md` §8 로 병합했는데,
이 문서는 22,511 tok 이고 AGENTS.md 에 **링크로만** 걸린다. ADR 의 Consequences 는 「스택 규칙」
누락만 적고 이 축은 짚지 않았다.
후보 = ⑴ §8.1/§8.3 의 **강제 조항만** AGENTS.md 본문으로 승격(고정비 +200자 내외) ·
⑵ `docs/AGENTS.md` 신설([ADR-027] 배치에서는 `docs/` 파일을 여는 순간 로드된다 — 단 **kickoff 시점과 트리거가 어긋난다**: 규율이 필요한 때는 문서를 열기 **전**이다) ·
⑶ Sprint kickoff 체크리스트를 `status.md` 「다음 스프린트」 블록 템플릿에 못 박기.

**Risk:** 🟡 규율 누락은 조용하다 — 위반해도 게이트가 red 로 안 변한다. 검출은 sprint close-out
audit 뿐이라 발견이 회차 끝으로 밀린다.

---

### BL-612

**Priority:** P3
**카테고리:** Docs / dev-log 버퍼 (ADR-026 §3)
**Trigger:** 다음 문서 정리 회차
**Est:** XS
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — LESSON-095 승격 → 버퍼 삭제 → INDEX tombstone 전환. 코드 0줄.

★**집행 기록 (2026-08-09).** ⑴ 회차 고유 교훈 3건(키 규약 = 체결봉 vs 장전봉 · 저장 digest 비교의 변조
무방비 · 적중률은 판별 표면이 아니다)을 **LESSON-095** 한 항목으로 압축 승격 ⑵ 버퍼 14,480B 삭제
⑶ `dev-log/INDEX.md:27` 을 `— dev-log (git show 4d072991:…)` tombstone 형식으로 전환.
★**압축한 이유** — `docs/lessons.md` 는 **400줄 상한이 게이트로 강제**된다(`docs-audit.sh:135`,
[BL-631] 계열). 착수 시점 380줄이라 여유가 20줄뿐이었다. 상한을 올려 통과시키지 않았다
(그 파일이 「상한을 올려 통과시키지 마라 — 넘쳤다는 것은 승격 대상이 밀렸다는 신호다」라고 적는다).
★**INDEX 줄도 300자 상한에 걸려 한 번 줄였다**(313자 → 통과). 게이트가 잡았다.

★★**범위 밖으로 남긴 것 — 같은 위반이 이 항목 하나가 아니다.** 2026-08-09 실측: ADR-026 §3 의
반증 카드 상한(1~2천자)을 넘는 dev-log 버퍼가 **9건**이고 최대는 `2026-08-08-bl003-unblock.md`
**48,863B**(이 항목의 3.4배)다. 본 항목은 entry-set-divergence **1건**만 다룬다 —
나머지 8건은 이 회차 비목표(신규 BL 사냥 금지)라 등재도 하지 않았다. **다음 문서 정리 회차의 표적이다.**

**entry-set-divergence 회차의 dev-log 버퍼가 승격되지 않은 채 남아 있다.**(← 아래는 등재 당시 원문)
ADR-026 §3 은 dev-log 를 이력이 아니라 **입력 버퍼**로 규정하고 「세션 종결 시 `docs/lessons.md`
승격이 의무, 승격하면 버퍼를 비운다」고 못 박는다. 그 회차는 PR #553 으로 종결됐는데
`docs/dev-log/2026-08-06-entry-set-divergence.md` 는 14,480바이트(약 9천자)로 남아 있다 —
§3 이 정한 반증 카드 상한(1~2천자)의 4~9배다. LESSON-072(사전등록 기각영역)는 이미 승격됐으나
회차 고유 교훈(키 규약 관측 = 체결봉 vs 장전봉 · 저장 digest 비교의 변조 무방비 ·
적중률은 판별 표면이 아니다)은 미승격이다.
수리 = 미승격 교훈을 `docs/lessons.md` 에 등재 → 버퍼 삭제 → INDEX 줄을 `— dev-log` 형식으로 전환.

**Risk:** 🟢 정보 유실은 없다(git + INDEX 한 줄). 다만 버퍼가 쌓이면 §3 의 3층 구조가 무너져
INDEX·lessons·git 의 역할 분담이 다시 흐려진다.

---

### BL-613

**Priority:** P3
**카테고리:** Backend / 구조 (핸들러 가시화 잔여)
**Trigger:** `live_signal.py` 를 다음에 크게 손댈 때 ([BL-580](#bl-580) 착수 회차와 겹친다)
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 선행 BL-580=ACTIVE (2026-08-10 bl-trigger-triage)

**2026-08-04 handler-visibility 회차가 「안 한 것」 — 줄 수 부채는 남았다.**
그 회차의 목표는 줄 수가 아니라 **핸들러 가시성**이었고 그건 달성됐다(최대 `try` 본문 **845 → 8**).
남은 것:

- `_evaluate_session_with_engine` **506줄** — Kind B 추출(E8~E14) 미완. 프롬프트의 「200줄 이하」를
  운반자 기준으로는 못 채웠다.
- `_place_planned_entry` **236줄** · `_reconcile_conditional_entries_inner` **203줄** — 경계선.
- `_async_dispatch_event` **256줄** · 최대 `try` 본문 **225줄** — 그 회차 **범위 밖**이었다.
  ★**이제 이게 트리 최대다.**

★[BL-580](#bl-580) 과 같은 파일을 건드리므로 **한 회차에 묶어라** — 따로 하면 같은 코드를 두 번 읽는다.
★`_async_dispatch_event` 는 [BL-580] 쪽에서 **4곳이 판정 보류**로 잠겨 있다. 줄 수를 줄이겠다고
그 4곳의 감싸는 핸들러를 바꾸면 보류 판정의 전제가 깨진다 — 손대려면 census 부터 다시 판정해라.

**Risk:** 🟢 가시성은 이미 확보됐으므로 급하지 않다. 단 `_async_dispatch_event` 225줄 `try` 는
다음 사고 때 「어느 핸들러가 삼켰나」를 다시 어렵게 만든다.

---

### BL-614

**Priority:** P3
**카테고리:** Docs / 교훈 승격 (ADR-026 §3)
**Trigger:** 다음 문서 정리 회차 ([BL-612](#bl-612) 와 함께)
**Est:** XS
**상태:** ✅ Resolved (2026-08-09 backlog-sweep) — LESSON-096 승격. 3건 중 1건은 **기존 항목 재발**로 기록. 코드 0줄.

★**집행 기록 (2026-08-09).** 원문을 `git show 0f0f0b06:docs/dev-log/2026-08-04-handler-visibility.md`
로 꺼내(sha 유효 확인) **LESSON-096** 으로 승격했다. 3건의 처리가 서로 다르다:

| 미승격 3건                            | 처리                                                                                                                                                                                                                                                                  |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ① 다중집합은 문장 순서를 못 본다      | **LESSON-096 본문** — 「정규 동치 0」을 「행위 변경 0」으로 갈음하지 마라                                                                                                                                                                                             |
| ② 재적재 지문 = celery 기동 배너      | **LESSON-096 본문** — md5 일치는 파일의 증거이지 프로세스의 증거가 아니다                                                                                                                                                                                             |
| ③ 검증 도구를 먼저 적대 검증에 걸어라 | ★**새 항목을 만들지 않았다** — **LESSON-092**(검사기 표면 < 실패 표면, `backend/AGENTS.md` §10 승격)의 **재발**이다. `lessons.md` 작성 규칙이 「반복 패턴이 동일하면 새 항목 만들지 말고 기존 항목의 반복 횟수 증가」라고 적는다 ⇒ LESSON-096 안에 재발 기록만 남겼다 |

★**③ 을 새 항목으로 세지 않은 것이 이 항목의 실질 판단이다.** 42건 주입 중 16건 거짓 음성
(가장 큰 것 = `except`/`else`/`finally` 구역 site 24개가 감싸는 `try` 를 통째로 잃음)은 **현상이 다르고
뿌리가 같다.** 뿌리로 세면 LESSON-092 는 이미 승격돼 규칙 파일에 있으므로 **행동 지침은 이미 존재한다.**

**2026-08-04 handler-visibility 회차의 방법론 3건이 `docs/lessons.md` 에 없다.**(← 아래는 등재 당시 원문)
그 회차 dev-log 본문은 문서 대개편(ADR-026)에서 삭제됐고, 지금은 `dev-log/INDEX.md` 한 줄과
git history(`git show 0f0f0b06:docs/dev-log/2026-08-04-handler-visibility.md`)에만 있다.
[BL-612](#bl-612) 와 축은 같지만 **대응이 다르다** — 저기는 버퍼가 남아 있고, 여기는 버퍼가
이미 삭제돼서 승격할 원본을 git 에서 꺼내야 한다.

미승격 3건:

1. **다중집합 비교는 문장 순서를 구조적으로 못 본다.** codex 가 그 축에서 MAJOR 를 냈다 —
   lazy import 를 헬퍼로 옮기자 **실패가 커밋 뒤로** 밀렸는데 다중집합 대조는 통과했다.
   ⇒ 「정규 동치 0」을 「행위 변경 0」으로 갈음하지 마라.
2. **재적재의 지문은 `watchfiles` 로그가 아니라 celery 기동 배너**(`Connected to redis`→`mingle`
   →`ready.`)다. `watchfiles` 는 조용하다. **md5 일치는 파일의 증거이지 프로세스의 증거가 아니다.**
3. **검증 도구를 먼저 적대 검증에 걸어라.** CONTROL 도구가 42건 주입 중 **16건 거짓 음성**이었다
   (가장 큰 것: `except`/`else`/`finally` 구역 site 24개가 감싸는 `try` 를 통째로 잃음).

**Risk:** 🟢 정보 유실은 없다(git + INDEX 한 줄). 다만 3건 다 **재발형 실수**라 승격 전까지는
같은 함정을 다시 밟아도 막을 근거가 문서에 없다.

---

### BL-615

**Priority:** P3
**카테고리:** Docs / 스택 규칙 크기 (ADR-027 후속)
**Trigger:** 스택 규칙을 다음에 손댈 때 ([ADR-027](decisions/027-nested-agents-md.md) 정착 후)
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**스택 규칙이 공식 권장 크기의 2배다** — `backend/AGENTS.md` **416줄** · `frontend/AGENTS.md` **316줄**.
Claude Code 메모리 문서는 파일당 **200줄 이하**를 권장하며 이유를 명시한다 — 「Longer files consume more
context and reduce adherence」. [ADR-027] 배치에서는 그 디렉터리 파일을 여는 순간 **전량** 로드되므로,
백엔드 작업 세션의 실질 고정비다(416줄 ≈ 11k tok).

**덜어낼 1순위 = §1 Tech Stack 표** — 두 파일 모두 첫 절이 스택 나열인데, 이건 `pyproject.toml` ·
`package.json` 에서 **추론 가능한 정보**다(구 `.ai/common/global.md` §5 가 「추론 가능한 정보 제외」를
규정했던 바로 그 축이고, 그 규정은 ADR-026 으로 소멸했다). 2순위 = 코드 예시 블록 — 규칙 진술과
예시가 1:1 로 붙어 있어 길이의 상당분을 차지한다.

★**줄이면서 규칙을 지우지 마라.** 이 두 파일에는 `LESSON-004/005/006/019/020/066` 이 승격돼 있고
`docs/lessons.md` 가 **§ 번호로** 그것을 가리킨다. 절을 재배치하면 그 표의 § 참조도 함께 갱신해야 한다
(ADR-027 이 `nextjs-shared.md §3` → `frontend/AGENTS.md §9` 로 갱신한 것과 같은 작업).

**Risk:** 🟢 동작에 영향 없다. 다만 「reduce adherence」가 사실이라면 **규칙이 안 지켜지는 쪽**으로
조용히 샌다 — 게이트로는 안 잡힌다.

---

### BL-616

**Priority:** P3
**카테고리:** DX / 워크트리 부트스트랩 (훅 결손 감지)
**Trigger:** 워크트리에서 훅 미작동이 또 관측되면
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 관측된 결함(워크트리 1개의 훅 결손)은 2026-08-07 에 정상화했다. **감지 수단 부재**만 열려 있다.
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**부트스트랩을 우회해 만든 워크트리는 husky 훅이 없다.**

**사슬** — `herdr-fleet.sh:234` 가 워크트리 생성 후 `worktree-bootstrap.sh --adopt-env` 를 부르고,
그것이 `pnpm install --frozen-lockfile`(:356)을 돌리면 `package.json` 의 `"prepare": "husky"` 가
실행돼 `.husky/_` 가 생긴다. 이 경로를 건너뛰면 `.husky/_` 가 없고, git 은 존재하지 않는
`core.hooksPath` 를 **경고도 exit code 도 없이 무시**한다.

**실태 (2026-08-07 전수 확인)** — 워크트리 5개 중 **4개는 정상**이었다(`node_modules` 가 실디렉터리 =
`pnpm install` 을 거쳤다는 지문). 결손은 `node_modules` 를 **심볼릭으로 때운** 1개뿐이었고,
`pnpm exec husky` 로 정상화해 메인과 파일 목록이 일치함을 확인했다.

★★**이 항목은 처음에 「워크트리 전반의 구조적 결함, `core.hooksPath` 가 상대 경로라서」로 등재됐다가
같은 회차에 반증됐다.** 표본 1개(결손 워크트리)만 보고 원인을 귀속했고 **정상 사례 4개를 확인하지
않았다.** 이 레포가 반복해서 적어 온 「기저율 먼저」를 그대로 어겼다. 상대 경로는 문제가 아니다 —
`.husky/pre-commit`·`pre-push` 는 트래킹되고, 없던 것은 husky 가 만드는 `_` wrapper 뿐이다.

**증상(그 워크트리에서 실제로 일어난 일)** — `pre-push` 의 main 직접 push 차단·브랜치 화이트리스트·
FE 회귀 방어와 `pre-commit` 의 lint-staged 가 전부 무력이었고, 그 결과 prettier 위반 14파일이
푸시됐다(같은 회차에 발견·수리). eslint·ruff 는 CI 가 받치지만 **prettier 검사 스텝은 CI 에 없다.**

**남은 축 = 감지 수단이 없다.** 훅이 안 도는 실패 모드는 **출력이 0줄**이라 「통과했다」와 구별되지
않는다. `worktree-bootstrap.sh` 는 env 파일 실재는 검증하지만 훅 작동은 검증하지 않으며, 애초에
그 스크립트를 안 돌린 워크트리에는 그 검증도 닿지 않는다.
★**판별법(수리 없이도 쓸 수 있다)** — 워크트리에서 `git push --dry-run <remote> <branch>` 를 돌려
`→ pre-push:` 로 시작하는 줄이 하나도 없으면 훅이 없는 것이다.
수리를 넣는다면 후보는 ⑴ 부트스트랩 검증에 `core.hooksPath` 실재 확인 한 줄 · ⑵ CI 에 prettier
검사 추가(로컬 훅과 독립한 이중 안전망). **2026-08-07 사용자 판정: 둘 다 하지 않는다** — 도구 체인은
이미 옳고 이번 사고는 「도구가 없어서」가 아니라 「도구를 안 거쳐서」 났다.

**Risk:** 🟡 재발 시 조용하다. 단 정상 경로(herdr / `worktree-bootstrap.sh`)로 만든 워크트리는 영향 없다.

---

### BL-617

**Priority:** P3
**카테고리:** Docs / 운영 절차 회수 (ADR-026 후속)
**Trigger:** [BL-071](#deferred--trigger-미도래--의도적-부활-가능-구-_deferredmd-승격-2026-08-06) 발동 시 (프로덕션 배포) · Bybit mainnet 전환 시
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**「과거 기록」이 아닌 운영 절차 4종이 문서 대개편에서 working tree 밖으로 나갔다.**
ADR-026 은 `docs/archive/` 를 통째로 삭제했는데, 그 분류 기준은 **위치**(폴더 이름)였지
**미래 유용성**이 아니었다. 그 결과 아직 **실행하지 않은 절차**가 「과거 원문」으로 함께 나갔다:

| 문서 (`git show 0f0f0b06:<경로>`)                                       | 크기 | 언제 필요한가          |
| ----------------------------------------------------------------------- | ---- | ---------------------- |
| `docs/archive/operations/deployment/2026-05-05-cloud-run-runbook.md`    | 39KB | [BL-071] 프로덕션 배포 |
| `docs/archive/operations/observability/grafana-cloud-setup.md`          | —    | 운영 관측성 켤 때      |
| `docs/archive/operations/trading/2026-04-21-bybit-mainnet-checklist.md` | 11KB | demo → mainnet 전환    |
| `docs/archive/operations/legal/2026-04-25-legal-temporary-runbook.md`   | —    | 외부 사용자 받기 전    |

**측정 (2026-08-07)** — 머지 후 `docs/` 전체에서 **Cloud Run · Grafana · Prometheus · mainnet ·
법무 언급이 0건**이 된다. 그런데 `backend/prometheus/alerts.yml` · `backend/Dockerfile` ·
워크플로 4종은 **레포에 살아 있다** — 설정은 있고 「왜/어떻게」만 이력으로 빠지는 비대칭이다.

★**지금 되살리지 않는 것이 맞다** — 넷 다 3개월 이상 낡았고, 실제 배포·전환 시점에 어차피 다시 쓴다.
지금 `reference/` 로 옮기면 안 쓰는 채로 다시 썩는다. 필요한 것은 **꺼낼 수 있다는 사실의 보존**이고,
그 경로는 [`docs/README.md`](./README.md) §문서의 수명과 위치에 명시했다.

**수리** = 트리거 발동 시 위 경로에서 꺼내 **갱신한 뒤** `docs/reference/operations/` 로 재등재.
그대로 복사하지 않는다 (낡은 절차를 정본으로 만드는 것이 더 나쁘다).

**Risk:** 🟢 지금은 영향 없다. 단 트리거가 왔을 때 **이 항목이 없으면 그 문서들의 존재 자체를
아무도 모른다** — `docs/archive/` 375파일에는 파일 목록 색인이 남아 있지 않기 때문이다.

---

### BL-622

**Priority:** P1
**카테고리:** Backend / 라이브 신호 (공백 재동기)
**Trigger:** — (해결됨. 재발 시 = 유예 상한 재검토)
**Est:** S
**상태:** ✅ **Resolved (2026-08-07 gap-resync-autopsy 회차)**

**공백 재동기 판정이 원장보다 먼저 뛰어 정상 세션을 죽였다 (19.42h 소크 창 폐기).**

**부검 실측 (세션 `c160a1a9`, 2026-08-06).** 사전등록한 판정 규칙에 대입한 결과 **H3(관측 지연)**:

| 관측량                                       | 값                                             | 출처                                 |
| -------------------------------------------- | ---------------------------------------------- | ------------------------------------ |
| `T_death`                                    | **20:31:48.126**                               | `live_signal_sessions`               |
| 주문 `7e406c4e` **거래소** 체결시각          | **20:17:19.519**                               | `exchange_exits.exchange_updated_at` |
| 우리 `filled_at`(= **관측**시각)             | **20:31:51.622** — 거래소보다 **872.1초** 늦음 | `trading.orders`                     |
| 엔진 carried (마지막 성공 평가 20:14:33.924) | **long 0.029535828** (`PivRevLE` @64420.1)     | `live_signal_states`                 |
| 거래소 실 순포지션 @ `T_death`               | **short 0.029**                                | 위 + `exchange_exits.closed_size`    |
| 공백                                         | 20:14:33 → claim 한 bar 20:30:00 = **16분**    | 세션 행                              |

★**계통 오차가 아니다.** 같은 세션의 다른 3건은 거래소 시각과 우리 `filled_at` 이 **50밀리초**
차다(`f068c5a1` 0.050s · `30c68f4e` 0.053s · `1311b5b4` 0.050s). 이 한 건만 872초였다.

**인과.** 파이프라인이 ~17분 멈춘 사이([BL-619]) 거래소가 대기 조건부를 체결해 롱 0.029 →
숏 0.029 로 반전했고(sell 0.058 = 청산+신규), 복구 tick 에서 `_probe_gap_resync_state` 는
거래소의 숏을 읽었지만 `list_fills_since` 는 **아직 `submitted` 인 그 주문을 못 봐** seed 가
비었다 ⇒ 엔진은 반전 전 롱을 든 채 대조돼 `_positions_are_aligned` False → fail-closed 사망.
**3.5초 뒤** 원장이 따라잡았다.

**수리.** `live_signal.py` 의 `requires_gap_resync` 블록 **앞**(claim 전)에서, 이 세션 소유의
미확정 조건부 진입이 있으면 **판정을 미룬다**(`_gap_resync_defer_reason`).
판별자는 기존 `OrderRepository.list_resting_conditional_entries` 재사용 —
`state IN (pending, submitted) AND trigger_price IS NOT NULL AND reduce_only = false` 이고
`7e406c4e` 는 판정 시점에 정확히 그 상태였다. **새 쿼리도 새 저장소도 없다.**

★★★**claim 앞이어야 한다.** `try_claim_bar` 는 성공 시 `last_evaluated_bar_time` 을 **무조건**
전진시키므로, claim 뒤에서 미루고 `return` 하면 다음 tick 의 공백이 5분 안으로 줄어
**`requires_gap_resync` 가 다시는 True 가 안 된다** — 세션이 낡은 엔진 포지션을 들고 조용히
계속 돈다(죽는 것보다 나쁘다). 이 함정을 잡는 단언이 재현 테스트의
`try_claim_bar.assert_not_awaited()` 다.

★**fail-closed 를 약화시키지 않는다.** 미는 조건은 「**알려진 미확정**이 있다」이지 「모른다」가
아니다. 미확정이 0건이면 종전과 100% 같은 경로다.
★**상한은 「미룬 횟수」다 — 주문 나이가 아니다**(`_MAX_GAP_RESYNC_DEFERS = 3`, 카운터는
`last_strategy_state_report._qb_gap_resync_defers`, 마이그레이션 0).

★★★**초판은 janitor 문턱(30분)에 얹었고 그건 틀렸다 — PR #556 리뷰가 실측으로 반증했다.**
조건부 진입은 트리거를 기다리며 **정상적으로** 오래 쉰다: 사망 세션 `c160a1a9` 의 조건부 진입
**118건 · 평균 resting 563초 · 최대 2337초**, 그 resting 이 **벽시계의 95.1%** 를 덮는다.
⇒ 나이로 끊으면 「거의 항상 미룰 수 있음」이 되어 「미확정 0건이면 종전과 동일」이 **4.9% 에만
참**이고, 진짜 발산도 최대 30분 판정이 미뤄진다. 그리고 초판이 30분을 정당화한 근거는
「부검 대상 주문의 나이 16분 58초가 문턱 안」이었는데, 그건 **문턱을 그 문턱이 덮어야 할
데이터에서 유도한 것**이다 — 적합은 검증이 아니다. 부검 사례는 원장이 **3.5초** 뒤 따라잡았으니
다음 1 tick 이면 충분했고, 3 tick 은 그 여유의 3배다.

★**fail-open 이 아니다** — 카운터 쓰기가 실패하면 다음 tick 이 또 미루지만(상한 무력화) 평가는
안 죽는다. 그 경우 `live_signal_gap_resync_defer_persist_failed` 로 반드시 남는다.

**검증.** 결정론 테스트 5건(재현 / 회복 / 다른 세션 음성 대조 / **상한 소진** 음성 대조 /
리포트 이어받기) + **변이 4/4 전건 적발**(유예 제거 · 상한 제거 → 항상 미룸 · 리포트 이어받기
제거 · 세션 필터 제거 — 각각 의도한 테스트만 red). 유예를 claim 뒤로 옮기는 변이는 재현
테스트의 `try_claim_bar.assert_not_awaited()` 가 잡는다.
계측은 `qb_live_signal_skipped_total{reason="gap_resync_pending_ledger"}` 이며
**[BL-580] 미가드 site 를 새로 만들지 않도록** `_count_safely` 로 감쌌다(census 84 불변).

**Risk:** 🟢 미확정 0건이면 무동작. 최대 노출은 **3 tick**(1분봉 기준 약 2분)이고, 그 뒤에는
미확정이 남아 있어도 종전 fail-closed 가 집행된다.

---

### BL-619

**Priority:** P1
**카테고리:** Backend / 라이브 신호 (가용성)
**Trigger:** 다음 소크 창에서 같은 정지가 관측되면 (로그가 남아 있는 동안 즉시 부검)
**Est:** M
**상태:** 🟡 **부분 해결 — 관측 장치는 배치됐다. 뿌리는 여전히 모른다** (2026-08-08
soak-exclusivity-and-observability 회차). 서버에 `dev.quantbridge.soak-logs-follow.service` 를
설치했다(`--install` · linger 는 이미 `yes` 라 sudo 불필요). 실측: 서비스 `active` ·
`~/quantbridge/.soak/logs/worker-follow.log` **871KB** · 활성 세션 `a4f1cbfb` 의
`live_signal.evaluate_all` 이 실제로 찍힌다. ★**「설치 완료」 출력은 검증이 아니다** — 75초
재측정으로 **+10,422 바이트**, 커서 `06:05:04Z → 06:15:03Z` 전진을 확인했다(멈춘 follow 와
살아 있는 follow 는 파일 존재만으로는 구분되지 않는다). 회전 상한 32MB × 4벌.
★**이것은 이 BL 을 닫지 않는다** — Trigger 가
비로소 **충족 가능해진 것**이지 정지의 뿌리를 안 것이 아니다. 닫는 조건은 불변이다:
같은 정지를 로그가 남아 있는 동안 재관측하고 부검한다.
**트리거 판정:** 미도래 — 외생 조건(재관측). 2026-08-11 게이트 실측 = **실격 0건 · C4 표본 공백 0건**이고, 본문의 첫 재관측(15.30h 창 · `evaluate_all` 919건 · 간격 최소=중앙=최대 60.0초)도 「재발 없음」이었다. **이벤트 부재는 정지의 증거가 아니지만, 관측되지 않은 것을 부검할 수도 없다** (2026-08-11 bl-703-partial-verdicts)

★★**2026-08-08 — 재관측이 처음 성립했고 결과는 「재발 없음」이다**(soak-mortality-repair).
로그가 남은 첫 창(세션 `a4f1cbfb` · `2026-08-08T02:32:42Z`~`17:50:42Z` · **15.30h**)에서
`live_signal.evaluate_all` 디스패치 **919건**을 재니 간격이 **최소=중앙=최대 60.0초** ·
**2분 이상 공백 0건**이다. ⇒ **태스크 디스패치 축의 정지는 0건**이다.
★**판별력은 있다** — 원 사건은 ~17분이고 이 도구는 60초 해상도로 2분 공백을 잡는다.
17분 정지가 있었다면 확실히 잡혔다. **유효한 음성 대조다.**
★**그래도 닫지 않는다** — 재발 0건은 뿌리를 밝히지 않는다. 원 사건은 1회성이고 창은 15.30h 다.

★★★**다른 축은 조용하지 않았다 — 그리고 그 축을 잴 도구가 없다.** 같은 창에서
`last_evaluated_bar_time` 은 **10분 이상 정체가 35구간**(최대 31.0분) 관측됐다. 디스패치는
60초마다 살아 있는데 **상태가 전진하지 않은** 것이고, 이는 원 사건이 보인 축
(`live_signal_states` 마지막 쓰기 `20:14:33` → 다음 claim `20:30:00` bar)과 **같은 축**이다.
★**그 35건의 크기는 못 믿는다** — 게이트 표본 간격이 **중앙 13.9분 · 최대 31.0분**이라
관측된 「정체 31.0분」이 표본 최대 간격과 **정확히 같다**. 정지의 크기인지 관측 공백의 크기인지
이 표본으로는 구분되지 않는다 ⇒ 신규 [BL-653](#bl-653). DB 축(`live_signal_states` 쓰기 시각)이
이를 가를 유일한 수단인데 이 회차는 스택을 내린 채 작업해 **조회하지 않았다**. 다음 창에서 물어라.

**라이브 파이프라인이 한 세션에 대해 ~17분 멈췄고 뿌리를 모른다.**

[BL-622] 부검의 **상류**다. 2026-08-06 20:14:33 ~ 20:31:48 사이에 세션 `c160a1a9` 는
**평가도 멈췄고**(`live_signal_states` 마지막 쓰기 20:14:33.924, 다음 claim 이 20:30:00 bar)
**체결 관측도 멈췄다**(같은 창에서 872초 지연). 둘이 같은 창이고 **같이 풀렸다** — 한 번의 정지가
두 증상을 냈다는 뜻이다. 그 정지가 `requires_gap_resync` 를 열었고, 그것이 사망의 전제였다.

★**판정 불가 — 「이상 없음」이 아니다.** 워커 컨테이너가 2026-08-07 03:35Z 경 재생성돼 사망
시점 로그가 없다(`docker logs quantbridge-worker` 최초 줄이 재생성 시점). 라이브 OHLCV 는
`ts.ohlcv` 가 아니라 CCXT REST(`live_signal.py:2885`, `fetch_ohlcv` 300봉)라 DB 로도 역추적이
안 된다. ⇒ **다음 창에서 로그를 남긴 채 재관측한다.**

★**정정(2026-08-08 실측).** 서버에는 `.soak/logs` 자체가 존재하지 않는다.
`.soak/logs/follow.sh` 는 로컬 전용 비추적 스크립트였고 서버로 배포된 적이 없다. 따라서 이 BL 의
「다음 소크 창에서 로그를 남긴 채 재관측」 조건은 서버 소크에 대해 한 번도 성립하지 않았다.

이번 회차는 추적되는 `scripts/soak-logs-follow.sh` 를 만들었다 — **466줄 신규**, 이번 브랜치 커밋
`32ea2a5d` 이며 systemd unit 승격 경로를 가진다. 서버 활성 세션은 현재 **0**이다. 이 장치를
서버 소크에 올린 뒤에야 같은 정지를 로그가 남아 있는 동안 재관측할 수 있다.

**Risk:** 🟡 [BL-622] 수리가 이 정지의 **사망 전이**는 막지만 **정지 자체**는 안 막는다.
17분 무평가 = 그 창의 신호를 안 낸다.

---

### BL-620

**Priority:** P2
**카테고리:** 운영 / BL-003 게이트
**Trigger:** —
**Est:** S
**상태:** ✅ **Resolved (2026-08-07 gap-resync-autopsy 회차)** — 게이트의 기본 취득 경로를
**HTTP → 멀티프로세스 디렉터리 직독**으로 바꿨다(`soak-gate.sh`). 워커가 `backend/.metrics`
에 같은 counter 를 계속 쓰므로 API 프로세스가 필요 없다. 판정이 `UNKNOWN 측정불가` →
**`UNKNOWN 진행중`** 으로 바뀌었고 C5 6개 서브조건 **전건 ✓** 다(어둠 88.0% — 보고 전용).
★**fail-closed 는 그대로다 — 음성 대조 3/3:** 없는 dir → `측정불가` · 죽은 포트 URL 명시 →
`측정불가` · 기본(직독) → ✓. 「취득 실패=null」과 「counter 부재=0/0」의 구분도 유지된다.
★`QB_METRICS_URL` 을 **명시하면 종전대로 HTTP** 를 쓴다 — 원격 데몬 + ssh 터널 운영안
(`docs/reports/2026-08-07-cloud-deploy-design.html`)이 그 override 를 전제하므로 보존했다.
★판정 모듈(`soak_gate_predicate.py`)과 그 309 테스트는 **무변경** — 바뀐 것은 취득뿐이다.
★**잔여(수리 안 함):** 어둠 비율이 **누적 절대값**이라 죽은 세션의 표본이 섞여 있다
(mmap 이 살아남는다 — 이 레포의 「counter 출생일」 함정). 보고 전용이라 판정에 영향은 없지만,
이 값을 **이번 창의 어둠**으로 읽으면 틀린다. 창 기준 차분이 필요하면 별도 BL 로 연다.

**소크 스택에 `/metrics` 를 내주는 것이 없어 게이트 C5 가 영구히 ✗ 다.**

**원인 확정 (2026-08-07, 재기동 직후 실측).** 게이트 결함이 **아니다** —
`soak-gate.sh:286` 이 `METRICS_URL`(기본 `http://localhost:8100/metrics`)을 `curl` 해서
`qb_live_ledger_derive_total{outcome}` 로 어둠 비율을 계산하는데, **`:8100` 에 리스너가
없다**(`lsof -nP -iTCP:8100 -sTCP:LISTEN` 0행). `soak-stack.sh up` 이 띄우는 것은
worker · beat · ws-stream · db · redis **5종뿐이고 API 컨테이너가 없다** — `/metrics` 는
호스트 uvicorn(`make be-isolated`, port 8100)이 `backend/.metrics` 멀티프로세스 디렉터리를
읽어 내주는 구조인데 그게 안 떠 있다. `soak-observe.sh` §4 도 같은 이유로 UNKNOWN 이다.
★게이트는 **스크레이프 실패(null=측정불가)와 counter 부재(0/0=표본 없음)를 의도적으로
구분**한다(`soak-gate.sh:282-284` 주석) — 즉 이 ✗ 는 fail-closed 가 **설계대로** 동작한 것이다.

★**초판 서술 정정.** 이 항목을 처음 적을 때 「활성 세션 0·귀속 창 0개 때문으로 보인다」로
`[확인 필요]` 를 달았는데 **틀렸다**. 세션을 띄운 뒤에도 ✗ 이고, 원인은 세션이 아니라
엔드포인트 부재였다.

**수리 후보:** ⑴ 소크 운영 절차에 「호스트 API 기동」을 넣는다(단 `make be-isolated` 는
`migrate-isolated` 를 선행하므로 마이그레이션 승인이 필요하다) ⑵ 소크 스택에 metrics 전용
경량 서비스를 넣는다 ⑶ 게이트가 `backend/.metrics` 를 **직접** 읽는다(HTTP 를 안 탄다).
★어느 쪽이든 **C5 를 느슨하게 만드는 방향은 금지** — 측정불가를 0% 로 접으면 이 레포가
이미 덴 「fail-open 게이트」다.

**Risk:** 🔴 **C1/C2 를 아무리 채워도 PASS 가 안 난다.** [BL-003] 의 종료 조건이 구조적으로
도달 불가라는 뜻이므로, 시간을 쌓기 **전에** 이것부터 정해야 한다.

---

### BL-621

**Priority:** P3
**카테고리:** Backend / 테스트 픽스처
**Trigger:** 골든 케이스로 비용·손익 회귀를 판정하려 할 때
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-07 backtest-fidelity)

**★부검 결론 ⑴ 원인 특정 — 두 겹이었다.** 두 축을 **동시에** 되돌려야 기록값이 재현된다.

| 조합                 | total_return                  | max_drawdown               | win_rate                           |
| -------------------- | ----------------------------- | -------------------------- | ---------------------------------- |
| 현행 ATR + 현행 비용 | -0.00075225935038332512252    | -0.0019096436091021742     | 0.2857142857…                      |
| 현행 ATR + 구 비용   | -0.000979728462339637565      | -0.0020657351891689804     | 0.2142857142…                      |
| 구 ATR + 현행 비용   | -0.00014915585433282336549    | -0.001306871746680595      | 0.2857142857…                      |
| **구 ATR + 구 비용** | **-0.0003771138174282226845** | **-0.0014634176774924912** | **0.2142857142…** ★4지표 전건 일치 |

원인 ⑴ `cda575f2`(2026-06-30, [BL-378] `ta.atr` rolling SMA → Wilder RMA) — 그 커밋은
`stdlib.py`·trust-layer `baseline_metrics.json`·`test_stdlib.py` 를 건드렸고 **이 골든은 안 건드렸다.**
이 케이스는 ATR 기반 SL/TP 전략이라 정면으로 영향을 받는다.
원인 ⑵ [BL-603] — 2026-08-07 비용 기본값 인하 — 역시 이 골든을 재생성하지 않았다.

★**왜 아무도 못 봤나** — `test_golden_backtest.py` 가 보던 유일한 값 `num_trades` 는 **네 조합 전부 14**
라 **판별력 0** 이었다. 그리고 재생성 스크립트가 없었다([BL-022]).
★값이 마지막으로 갱신된 커밋 = `80a2138e`(2026-06-26). 그 뒤 유일한 수정 `b97ac578`(2026-07-26)은
**`sharpe_ratio`·`description` 만** 바꿨다.

**수리** — `backend/scripts/regen_golden.py` 신설(`--confirm`/`--case`/`--check`) · `expected.json` 재생성
(스칼라 전량 + 리스트 3종 digest) · `test_golden_backtest.py` 를 smoke 에서 **실제 오라클로 승격**
(전 스칼라·digest·`entries_indices`/`exits_indices` 비교).

**★교훈** — 「원인이 하나」를 가정하고 축을 하나씩 되돌리면 원인이 둘일 때 **전건 미확정**으로 떨어진다.
직교 축의 **곱집합**을 재야 닫힌다.

**골든 `expected.json` 의 metric 블록이 낡았는데 아무도 대조하지 않는다.**

`tests/backtest/engine/golden/ema_cross_atr_sltp_v5/expected.json` 의
`total_return` 은 `-0.0003771138174282226845` 인데, **BL-603 교체 전 기본값으로 돌려도**
`-0.000979728462339637565` 가 나온다 — 즉 **이번 회차 이전부터 낡아 있었다**(2026-08-07 실측).
`test_golden_backtest.py` 가 `status` 와 `num_trades >= 0` 만 보고 「구체 metric 비교는 유보」라
red 가 안 난다. `run_backtest` 는 `run_backtest_v2` 의 별칭이라(`engine/__init__.py:18`)
호출 경로 차이도 아니다.

**Risk:** 🟢 지금은 무해(미대조). 단 나중에 이 파일을 오라클로 승격하면 **틀린 값을 정본으로
고정**하게 된다. 재생성 스크립트가 없어 손으로 만들어야 한다.

---

### BL-625

**Priority:** P2
**카테고리:** 운영 / 배포 검증
**Trigger:** 새 호스트에 API 를 세울 때 · [BL-071] 프로덕션 배포 발동 시
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 외생 조건(Beta·프로덕션 배포). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**플레이스홀더 시크릿이 development 에서는 아무 게이트에도 안 걸린다.**

2026-08-07 FE 배포 실측: 서버 `backend/.env.local` 이 `CLERK_SECRET_KEY=sk_test_...`(문자 그대로
플레이스홀더)였는데 **API 는 정상 기동하고 `/health` 는 200 을 냈다.** 진짜 키는 루트 `.env` 에만
있었고(compose 워커만 그걸 읽는다) 호스트 uvicorn 은 인증 경로를 **한 번도 밟은 적이 없어서**
드러나지 않았다. 브라우저에서 로그인한 첫 요청이 **전건 401** 로 터지고 나서야 보였다.

`_enforce_production_safety`(`config.py`)는 이 계열을 이미 안다 — `SECRET_KEY`·`CLERK_SECRET_KEY`·
`WAITLIST_TOKEN_SECRET` 의 placeholder 를 기동 시점에 raise 한다. **단 `app_env == production`
일 때만이다.** development/staging 은 통과시킨다.

★같은 회차에 **2차 결함**도 물렸다 — 루트 `.env` 는 이 레포 관례상 `KEY=value  # [필수 …]` 로
인라인 주석을 단다. 값을 `cut -d= -f2` 로 옮기면 주석의 한글이 값에 섞이고, 그러면 401 이 아니라
**500** 이 난다(`clerk_backend_api` 가 헤더를 ascii 인코딩 → `UnicodeEncodeError`).
두 실패의 **증상이 다르다**는 것이 오히려 진단을 도왔다.

**수리 후보(택1, 미결정):** ⑴ placeholder 검사를 env 무관하게 **warning 으로** 항상 돌린다
⑵ `/healthz` 에 「Clerk 키가 placeholder 아님」 서브체크를 넣는다 ⑶ 배포 런북의 검증을
「로그인 후 데이터 화면」까지로 못박는다(이미 반영 — `frontend-deploy.md` §5).

**Risk:** 🟡 조용하다. 새 호스트마다 재발하고, 발견 시점이 **사용자가 처음 화면을 열 때**다.

---

### BL-623

**Priority:** P3
**카테고리:** 운영 / 클라우드 서버 체크아웃
**Trigger:** 서버에서 feature 브랜치를 다시 받아야 할 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**서버 클론이 `--single-branch` 라 feature 브랜치가 기본 fetch 로 오지 않는다.**

`remote.origin.fetch` 가 `+refs/heads/main:refs/remotes/origin/main` **한 줄뿐**이라
`git fetch origin && git checkout <branch>` 가 `pathspec did not match` 로 죽는다(2026-08-07 실측).
우회는 refspec 명시 — `git fetch origin <branch>:refs/remotes/origin/<branch>`.

**Risk:** 🟢 무해하지만 배포 때마다 한 번씩 걸린다. 근본 수리는
`git remote set-branches origin '*'` 한 줄인데, **소크가 도는 서버의 git 설정을 바꾸는 것**이라
창을 내릴 필요가 없다는 확인을 먼저 하고 싶어 이연했다.

---

### BL-624

**Priority:** P2
**카테고리:** 운영 / BL-003 게이트
**Trigger:** `QB_METRICS_URL`(원격 데몬 + ssh 터널 운영안)을 실제로 쓰려 할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**게이트의 HTTP 갈래는 `PROMETHEUS_BEARER_TOKEN` 과 양립하지 않는다.**

`soak-gate.sh` 의 `curl -sf --max-time 20 "${METRICS_URL}"` 는 **인증 헤더를 안 보낸다.**
`PROMETHEUS_BEARER_TOKEN` 이 설정돼 있으면 `/metrics` 가 401 을 내므로 `METRICS_RC != 0` →
`DARKNESS=null` → **C5⑷ 가 영구 ✗** 다. `APP_ENV=production` 과 무관하다 — 토큰이 있으면
development 에서도 강제된다(`main.py` 의 `_verify_prometheus_bearer`).

**2026-08-07 실측으로 물렸다.** 서버 체크아웃이 [BL-620] **이전** 커밋이라 기본값이 HTTP 였고,
FE 배포 회차가 공개 `/metrics` 를 막으려고 베어러 토큰을 켜자 그 즉시 C5 가 죽었다. 체크아웃을
올려 직독으로 바꾸자 복구됐다(판별자 = API 로그의 `GET /metrics` 유무 — 게이트 출력의
`darkness_computed=✓` 는 **어느 경로로 성공했는지 말해주지 않는다**).

**지금은 발동하지 않는다** — 기본 경로가 직독이라 `QB_METRICS_URL` 을 명시할 때만 문제다.
수리하면 `QB_METRICS_BEARER` 를 읽어 `-H "Authorization: Bearer …"` 를 붙이는 한 줄이다.

**Risk:** 🟡 그 override 를 쓰는 순간 **C1/C2 를 다 채워도 PASS 불가**가 된다 —
[BL-620] 이 닫은 실패 계열이 override 갈래에 그대로 남아 있다.

---

### BL-626

**Priority:** P3
**카테고리:** 운영 / BL-003 게이트
**Trigger:** `.soak/` 디스크 압박이 보일 때 · 게이트 1회 실행이 눈에 띄게 느려질 때
**Est:** XS
**상태:** ✅ Resolved (2026-08-09, W1)

**`.soak/phantom-*.json` 이 상한 없이 쌓이고, 판정기가 매번 그 전부를 읽는다.**

`soak-gate.sh:294-360` 은 **수집 실행마다** phantom 아카이브를 새로 쓴다. 판정기는
`soak_gate_predicate.py:462-484` 에서 **모든** 아카이브를 읽어 verdict 를 합집합한다. 회수·상한이
없다. 2026-08-07 실측: 09:10~13:11 **4시간에 29개**(타이머 8회 + 수동 실행). 30분 타이머만으로도
하루 48개, 한 달 1,400개다.

판정은 안전하다 — 실격은 `(at, kind, detail)` 로 dedup 된다. 새는 것은 **둘**이다:
⑴ 파싱 시간과 디스크가 선형으로 는다 ⑵ `unreadable_labels()[label]["count"]` 는 dedup 되지
**않아** 같은 관측이 아카이브 수만큼 곱해진다 — `측정불가` 요약의 `총 N건` 이 부풀려진다.

★파일명 `STAMP` 이 `date -u '+%Y%m%dT%H%M%SZ'` 로 **1초 해상도**라, 같은 초에 두 번 돌면
파일이 충돌한다. 게이트에 flock 이 없으므로 타이머 두 개를 같이 돌리면 실제로 가능하다
(그래서 `soak-watch.sh --install` 이 게이트 타이머를 끈다).

**수리 후보(택1, 미결정):** ⑴ 커버리지에 실제로 기여하는 최근 N개만 남기고 회수
⑵ `.soak/superseded-<판>/` 로 옮기는 기존 관례를 나이 기준으로 자동화 ⑶ 아카이브를 하나로
append 하고 `log_to` 로 클립.

**Risk:** 🟢 조용하고 느리다. 판정은 안 틀리지만 `총 N건` 수치를 인용하면 과대 계상된다.

---

**해결 (2026-08-09, W1):** 두 축을 따로 닫았다. ★**읽는 지점 재탐색 결과 위 본문의 인용이 틀렸다** —
`soak_gate_predicate.py:462-484` 에는 glob 이 **없다**. 실제 읽는 곳은 `scripts/soak-gate.sh:529`
(커버리지·verdicts)와 **`:562`(현행 판 탐색, 두 번째 glob)** 다. 판정기 쪽에 있는 것은 `count` 뿐이다.

**축 ⑵ — `count` dedup (BL 이 「진짜 결함」이라 부른 것):** `unreadable_labels` 가 `count` 를
`(label, at, session_id)` **관측 단위**로 접는다. 키에 `archive` 를 넣지 않는 것이 요점이다 —
그게 부풀리는 축이다. 표본 예산(`MAX_UNREADABLE_LABEL_SAMPLES`)도 같은 관측을 여러 번
쓰지 않게 되어 **서로 다른 관측**을 보여준다.

- **red → green:** 같은 관측을 담은 아카이브 3벌 → `총 3건` → `count == 1` · 표본 1건.
- **음성 대조:** `at` 이 서로 다른 7건은 여전히 `총 7건`
  (기존 `test_the_report_names_where_an_unreadable_label_came_from` 이 그 대조군이다 —
  dedup 이 1 로 뭉개면 그 시험이 red 다).
- **변이 2/2:** dedup skip 무효화(`and False`) → 신규 시험만 red · 키에 `archive` 재삽입 → 신규 시험만 red.
- ★실데이터로는 이 결함을 **실증할 수 없다** — 현재 코퍼스의 미지 라벨은 **0건**이다(228벌 전량 스캔).
  그래서 M 은 합성 아카이브 3벌이어야 한다. 「지금 안 보인다」와 「없다」는 다르다.

**축 ⑴ — 회수: `soak-gate.sh --prune-archives [--confirm]` (기본 dry-run, 지우지 않고 옮긴다).**

★★★**처방 후보 ⑴ 의 「최근 N개만 남긴다」는 판정을 깎는다 — 실측으로 반증했다.** 아카이브는
커버리지 구간을 들고 있고 C1 은 **커버리지가 덮은 시간만** 센다. 메인 체크아웃 228벌에서
「최근 50개만」이면 커버리지 시작이 `2026-08-04T15:51` → `2026-08-08T18:21` 로 **나흘치가 사라진다.**
168h 를 30분 주기로 채우려면 ~336벌이 필요하므로 **어떤 상수 N 도 안전하지 않다.**
⇒ 기준을 개수가 아니라 **포함관계**로 바꿨다: 매 실행이 로그 전량을 재분류하므로 같은
`(log_from, predicate_version, classifier_ok)` 안에서 `log_to` 가 가장 늦은 것이 나머지의
**상위집합**(같은 시작·더 늦은 끝·같은 판별식)이다. 그것만 남긴다.

- `predicate_version` 을 키에 넣는다 — 새 판이 취소한 옛 라벨을 조용히 버리면 합집합 규율
  ([ADR-024] §아카이브 판)이 깨진다. `classifier_ok` 도 넣는다 — 껍데기 아카이브는 커버리지가 아니다.
- **`log_to` 가 ISO 가 아닌 것은 절대 회수하지 않는다.** 실측 **10벌**이 타임스탬프 자리에 문자
  `Error` 를 들고 있고(launchd 파손, [BL-641] 계열) 그것들은 `unreadable_log_coverage` 로 C5 에
  참여한다. ★문자열 정렬로 재면 `'Error' > '2026-…'` 이라 **파손본이 대표로 뽑혀 성한 것을 버린다.**
- **실측 (메인 228벌을 이 워크트리로 복사해 재고 전량 치웠다):** 228벌 → 그룹 11개 · 보존 11 ·
  회수 162 · 손대지 않음 55(= 무기여 45 + `Error` 10) ⇒ **228 → 66벌.**
- **음성 대조 N — 판정 diff 공집합.** prune 전/후 게이트 출력이 벽시계 말고 **한 글자도 안 다르다**:
  C1~C5 · C3 실격 0 · **전 이력 실격 15건** · 귀속(코드 결함 7 · 운영 0 · 미판정 8) · 귀속 불가 110.11h.
  (아카이브를 얹으면 실격이 9 → 15 로 는다 — 그 **더 풍부한 코퍼스에서** 불변을 쟀다.)
- **기본 읽기 경로는 한 줄도 안 바뀌었다** — prune 은 opt-in 이라 N 이 구조적으로 성립한다.

★**동기 자체는 아직 발화하지 않았다(정직하게 적는다):** 228벌 = **0.10MB · 파싱 59ms**.
`du -sh .soak` 의 7.1M 은 `.soak/src`·logs·evidence 를 합친 값이고 아카이브 몫은 100KB 다.
Trigger(「디스크 압박」·「눈에 띄게 느려짐」)는 둘 다 안 왔다 — 그래서 회수를 **기본 동작으로
켜지 않았다.**

★**남은 것(등재만, 이 회차 착수 안 함):** ⑴ 무기여 45벌(커버리지·verdicts 둘 다 없음)도 원리상
회수 가능하지만 상위집합 규칙으로는 증명이 안 돼 손대지 않았다 ⑵ `log_to == 'Error'` **10벌**은
게이트를 영구 `측정불가` 쪽으로 미는 파손 원자료다 — 판독·폐기 판단이 필요하다
⑶ `STAMP` 1초 해상도 + flock 부재는 그대로다(위 ★ 문단이 정본).

---

### BL-627

**Priority:** P3
**카테고리:** Test infra / 골든 재생성
**Trigger:** `regen_golden.py` 를 CI 나 병렬 실행에 넣을 때
**Est:** XS
**상태:** ✅ **Resolved (2026-08-09, W2)** — `--out-dir <path>` 신설(`--confirm` 전용). 라운드트립
시험은 이제 `tmp_path` 두 곳에 산출을 쓰고, **정본이 내용·mtime 모두 불변인지를 직접 단언**한다.
백업/`finally` 복원은 삭제했다 — 그 복원 코드는 프로세스와 함께 죽으므로 애초에 강제 종료를
막지 못했다. 부수 항목(`--check` 의 「차이 없음 = exit 0」)도 시험으로 고정했다.

**red→green 실측:** 수리 전 코드로 이 시험을 돌리니 정본 mtime 이 `13:43:21 → 13:53:55` 로
움직였다(= 두 번 덮어썼다). 수리 후에는 `13:43:21` 그대로다.

**★변이 M — 「dirty 창」을 셈으로 실측했다. 위험은 truncate 경쟁이 아니라 포맷 차이다.**

처음에 나는 이 변이가 재현 불가라고 판단했다가 **스스로 반증했다.** 오판의 뿌리 —
`--check` 가 통과하니 재생성 산출이 커밋본과 바이트 동일할 거라 넘겨짚었다. **아니다.**
`_differences()` 는 **파싱된 값**을 비교하므로 포맷에 무관하고, 커밋본은 pre-commit 의
`prettier --write` 가 배열을 한 줄로 접어 둔 반면 `regen_golden.py` 는
`json.dumps(indent=2)` 로 **원소당 한 줄**을 쓴다. 그래서 `--confirm` **1회만으로 트리가
dirty** 해진다(실측 — `+29/-2`). SIGKILL 이 truncate 창에 떨어질 필요가 전혀 없었다.

정본 sha 를 시험이 도는 내내 고빈도 표집해 창의 크기를 쟀다:

|         | 표본 | 정본이 HEAD 와 다른 표본 |
| ------- | ---- | ------------------------ |
| 수리 전 | 906  | **288 (31.8%)**          |
| 수리 후 | 912  | **0**                    |

즉 **시험 실행 시간의 3분의 1 동안 정본이 더러웠고**, 그 사이 어디서 죽어도 `finally` 는
프로세스와 함께 죽어 복원이 안 된다. 수리 후에는 그 창이 **0** 이다.

보강 변이 2종(둘 다 정확히 한 시험만 red) — ① `--out-dir` 리다이렉트 무력화(항상 정본에 쓴다)
→ `test_regen_roundtrip_is_stable`. ② `--check` 의 차이 없음 반환 `0→3`
→ `test_regen_check_exits_zero_when_there_is_no_difference`.

★**부수 발견(등재만, 착수 안 함):** `--confirm` 산출과 커밋본은 **포맷이 구조적으로 어긋난다** —
`prettier` 가 커밋 시점에 접고 스크립트는 펴서 쓴다. 그래서 정본을 갱신할 의도로 `--confirm` 을
돌리면 diff 에 **의미 없는 재포맷이 항상 섞인다**. `--check` 는 값 비교라 이걸 못 본다 → [BL-658](#bl-658).

**`regen_golden.py` 에 출력 경로 리다이렉트가 없다.**

그래서 라운드트립 안정성을 재는 `test_golden_regen.py::test_regen_roundtrip_is_stable` 이
**실제 `golden/<case>/expected.json` 을 두 번 덮어쓰고 `finally` 에서 바이트로 복원**한다.
정상 종료 시 오염 0이지만 **프로세스가 강제 종료되면 워킹 트리가 더러워진다**
(복구 = `git checkout -- backend/tests/backtest/engine/golden`).

**수리 방향:** `--out-dir <path>` 를 받아 재생성 산출을 다른 곳에 쓸 수 있게 한다. 그러면 테스트가
정본 파일을 건드리지 않고, `--check` 도 같은 경로를 재사용할 수 있다.

★부수: `--check` 의 **「차이 없음」 종료 코드가 계약에 명시돼 있지 않다**(차이 있으면 1 만 명시).
현재 구현은 0 을 내지만 시험이 그것을 단언하지 않으므로 계약에 적어 고정해야 한다.

**Risk:** 🟢 지금은 무해(정상 종료 경로에서 오염 0).

---

### BL-628

**Priority:** P3
**카테고리:** Frontend / 디자인 토큰 (라이트 캐논)
**Trigger:** 라이트 공개 라우트의 캐논 등급을 다크 이하로 내리려 할 때
**Est:** XS
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 라이트 `--warning` 을
`#875206` → **`#824e05`** 로 옮겼다(`--accent-amber` 동반, `brand-palette.ts` 동기).
`--warning-subtle` 위 **6.03** · `--card` 6.78 · `--bg` 6.33 · `--bg-alt` 5.99 로 네 표면
전부 캐논 통과, 흰 글자 6.48 → 6.91. **표면을 바꾸는 후보(아래 ★)는 채택하지 않았다** —
같은 fg/bg 쌍을 `[data-tone=warning]`·`.chip.warn`·`.ks-banner-warn`·`.notice-inline` 등
10여 곳이 함께 쓰므로 토큰을 옮겨야 전부 낫는다.
★★**「마케팅 푸터」는 틀렸다** — 실제 자리는 `components/legal-notice-banner.tsx:15`,
`app/layout.tsx:50` 이 `AppProviders` **앞에** 마운트하는 **전 라우트 상단 고정 배너**다
(`/` 한정으로 `geo-block-banner.tsx:8` 도 같은 쌍). 마케팅 푸터 3종(`landing-footer` ·
`.site-foot` · `.foot`)은 전부 `--ink-3` on `--bg-alt` 라 warn 을 **한 번도 안 쓴다**.
한 토큰 쌍이 68건을 만든 이유가 그것이다.
★★★**그리고 이 BL 은 어떤 게이트도 물지 않고 있었다** — `design-canon-audit.ts:300` 의
`newContext` 가 테마를 강제하지 않고 `app-providers.tsx:21` 이 `defaultTheme="dark"` 라
캐논 감사 4폭이 **전부 다크에서** 돈다. 라이트를 재는 것이 하나도 없었다.
신설 `src/__tests__/light-canon-contrast.test.ts` 가 `:root` 조합 25건의 대비를 브라우저
없이 계산해 5.82 로 래칫한다(음성 대조: 구값 복원 시 `--warning-subtle`·`--bg-alt` **2건만**
red, sha256 복원 일치). 런타임 라이트 커버리지 부재 자체는 신규 **[BL-648]**.

~~**마케팅 푸터 법적 고지 한 곳이 공개 라우트 라이트 캐논 미충족의 단일 원인이다.**~~

2026-08-07 backtest-fidelity 회차가 B2 팔레트 적용 후 앱을 실제로 재서 발견했다.

| 집합          | 라이트 canon | 다크 canon | 판정       |
| ------------- | ------------ | ---------- | ---------- |
| 인증 12라우트 | 171          | 255        | 충족       |
| 공개 4라우트  | **68**       | 24         | **미충족** |
| 전체 16라우트 | 239          | 279        | 충족       |

원인 = `--warning` 을 `--warning-subtle` **위에** 얹는 조합으로 **5.66:1** (캐논 5.82 미달, WCAG AA 는 통과).
캐논 임계는 「카드 위」 기준이라 중첩 표면에서 내려가는 것 자체는 다크 정본도 같다
(`--card-2` 5.44 · `--card-3` 5.15).

★**B2 가 만든 것이 아니다.** 같은 자리가 구팔레트에서는 **4.30:1 = AA 하드 실패**였다. B2 는 그것을
5.66 으로 **올렸고**, 남은 것은 캐논 문턱까지의 0.16 이다. 색을 더 손대는 대신 **그 자리의 표면을
바꾸는 것**(`--warning-subtle` 대신 `--card`)이 후보다.

**Risk:** 🟢 AA 통과 상태. 캐논은 하드 실패가 아니라 지표다.

---

### BL-629

**Priority:** P3
**카테고리:** Frontend / 디자인 토큰 (데드 토큰)
**Trigger:** 차트 축 색을 손대려 할 때 · 토큰 정리 스윕 때
**Est:** XS
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 수리 방향 **①(삭제)** 을
택했다. `chart-tokens.ts` 가 축=`--text-muted` · 그리드=`--border` · 상승/하락=
`--bullish`/`--bearish` 를 **의도적으로** 읽으므로, ②(배선)는 동기 지점을 하나 더 만든다.
★★**범위가 1종이 아니라 7종이었다** — 실측하니 참조 0건인 `--chart-*` 가
`axis` · `grid` · `bullish` · `bearish` · `line` · `area-top` · `area-bottom` **7개**였다.
전부 라이트/다크 양쪽에서 삭제(토큰 수 `:root` 114→107 · `.dark` 74→67).
`--chart-grid` 는 `brand-palette.ts:33/58` 과 `brand-palette-css-sync.test.ts:53` 에도
있어 함께 지웠다. shadcn `--chart-1..5` 는 존속(유틸 소비 0건 — 처분은 [BL-649]).
★★★**삭제를 지킬 것이 없었다** — `chart-tokens-contract.test.ts` 는 「읽는 것이 정의됐나」만
보고 「정의된 것을 읽나」는 아무도 안 봤다. 그래서 다크 `--chart-axis` 가 팔레트 개정
한 바퀴를 통째로 썩은 채 통과했다. **역방향 래칫**을 추가해 `--chart-*` **정의 집합
전체를 두 테마에서 동결**했다(음성 대조: `--chart-axis` 를 `:root` 에 되살리면 red,
sha256 복원 일치).
★**아래 줄 번호는 낡았다** — `:66`/`:458` 이 아니라 삭제 직전 기준 `:70`/`:462` 였다.

~~**`--chart-axis` 는 정의만 있고 아무도 안 읽는 데드 토큰이다.**~~

`globals.css:66`(라이트) · `:458`(다크)에 정의돼 있는데 `chart-tokens.ts:65` 는
`read("--text-muted", …)` 로 **`--text-muted` 를 축 색으로 읽는다.** `--chart-axis` 를 읽는 코드는
`frontend/src` 전체에 **0건**(2026-08-07 실측).

★증거가 하나 더 있다 — 다크 `--text-muted` 는 캐논 교정으로 `#8b939c` 가 됐는데 다크 `--chart-axis` 는
**구값 `#7a828c` 에 남아 있다.** 아무도 안 읽으니 아무도 안 고쳤다.

**수리 방향(택1):** ① 토큰을 지운다 ② `chart-tokens.ts` 가 `--chart-axis` 를 읽게 하고 값을
`--text-muted` 와 동기화한다. ①이 단순하지만 ②는 「축 색을 본문 muted 와 독립으로 조정」 가능성을 남긴다.

**Risk:** 🟢 무해. 단 다음 사람이 `--chart-axis` 를 고치고 화면이 안 바뀌어 시간을 태운다.

---

### BL-630

**Priority:** P3
**카테고리:** Frontend / CSS 명시도
**Trigger:** `<td>` 안에서 `.pos`/`.neg` 를 `.num` 없이 쓰게 될 때
**Est:** XS
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 수리 방향 중 **전자**를
택했다. 언레이어드 블록(기존 `td.num.pos` 중복이 이미 있던 그 자리)에
`table.trades tbody td.pos` / `td.neg` 를 추가했다. **명시도가 아니라 캐스케이드 레이어로
이긴다** — 언레이어드는 `@layer components` 를 명시도 무관하게 이기므로 KITPORT 센티넬을
건드릴 필요가 없다(`globals.css:175-183` 의 `--sidebar-w` 레일이 같은 기법).
★**민짜 `.pos { color }` 로 올리지 않았다** — `.kpi-value mono pos`(optimizer-run-detail) ·
`.mock-v pos`(landing-hero) 같은 표 **밖** 소비자까지 레이어드 규칙을 이기게 되어
폭발반경이 앱 전체가 된다. 스코프를 `table.trades tbody td` 로 묶었다.
오라클 = 신설 `e2e/design-canon-table-tone.spec.ts` — **문자열이 아니라 캐스케이드 승패**를
잰다(6조합 × 2테마, 그중 **역방향 2**: `td.num`→`--ink`, 민짜 `td`→`--ink-2` 가 유지되는지).
음성 대조: 규칙 2줄 제거 시 `pos`/`neg` 가 양 테마에서 red 이고 실제로 `--ink-2` 로 떨어진다
(다크 `rgb(166,173,181)` · 라이트 `rgb(75,83,92)`), sha256 복원 일치.
★★★**그 음성 대조가 1차 시도에서 거짓 통과했다** — CSS 를 고치고 1초 뒤 e2e 를 돌리면
Turbopack 이 **직전 스타일시트**를 준다. 더 나쁜 건 그 낡은 산출물이 **dev 서버 완전
재기동을 넘어 살아남았고** `rm -rf .next` 로만 지워졌다는 것이다. 음성 대조 전에 **서빙
CSS 자산을 폴링해 변이 도달을 확인**해라(~3초).
★부수 지적(주석의 「같은 명시도」 서술 부정확)은 그대로 유효하다 — 고치지 않았다.

~~**`.pos`/`.neg` **단독**은 여전히 `td` 색에 진다.**~~

핸드오프 §8.5 가 등재한 「표의 손익 색이 두 테마 모두 죽어 있다」는 **이미 수리돼 있다** —
`globals.css:1653-1654`(레이어드 `table.trades tbody td.num.pos`, 명시도 `0,3,3`)와
`:2700-2701`(언레이어드 중복)이 `td.num`(`:1645`, `0,2,3`)을 이긴다(2026-08-07 실측).

**남은 구멍은 다른 것이다.** `:990-991` 의 `.pos`/`.neg`(명시도 `0,1,0`)는 `td`(`:1632`, `0,2,3`)와
`td.num`(`:1645`)에 **진다.** 즉 `<td class="pos">` 처럼 `.num` **없이** 쓰면 색이 죽는다.
지금 마크업은 항상 `.num` 과 함께 붙여 쓰므로 발현되지 않는다 — **관례가 지키고 있을 뿐 규칙이 아니다.**

★부수: `:1651-1652` 주석이 "같은 명시도로 올려 되살린다" 라고 적었는데 실제 `td.num.pos` 는 클래스가
하나 더 붙어 **한 단계 높은** 명시도다. 결과는 맞고 서술만 부정확하다.

**수리 방향:** `table.trades tbody td.pos` / `td.neg` 규칙을 추가하거나, `td.num` 의 `color` 선언을
걷어낸다. 후자가 근본이지만 KITPORT 센티넬 구역(987–1889)이라 `_kit.html` 과 함께 움직여야 한다.

**Risk:** 🟢 현재 미발현.

---

### BL-631

**Priority:** P2
**카테고리:** DX / 디자인 게이트 (검사기가 죽은 채 방치됐다)
**Trigger:** 다음에 `docs/` 를 재편하거나 프로토타입을 손댈 때 (그전에 붙이는 게 싸다)
**Est:** S
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — 수리 방향 ⑵ 를 택했다. `scripts/docs-audit.sh` 가 `runtime-check.mjs` 와 `regen_golden.py --check` **둘 다**의 존재+기동을 확인한다(이 BL 이 정의한 「두 도구를 함께」). 출력 축에 `orphan tool startup` 이 추가됐다. ★[BL-602] 를 피해 `frontend/package.json` 은 건드리지 않았다. ★회차 말 실측: `node runtime-check.mjs` **17/17 통과 · exit 0** — 이 회차의 `docs/` 재편(archive 신설)이 이 도구를 다시 죽이지 않았다.

**`runtime-check.mjs` 가 어느 게이트에도 안 붙어 있어 죽은 채로 방치됐다.**

2026-08-07 backtest-fidelity 회차 실측: 이 검사기는 **기동조차 못 하고 있었다.**
`docs/` 재편 커밋 `fcc36bf7` 이 파일을 두 단계 깊은 곳으로 옮겼는데 playwright import 의 상대
깊이(`../../../frontend/…`)가 안 따라와 **`ERR_MODULE_NOT_FOUND` 로 즉사**했다.

★★**그래서 `HANDOFF-react-port.md` §8.5 의 「다크 17벌 17/17 PASS」는 그 커밋 이후 한 번도 재현된
적이 없는 숫자였다.** 이번 회차가 깊이를 고쳐 17/17 을 실제로 재현했고, 그 값이 회귀 기준선이다.

**뿌리는 경로가 아니라 소유자 부재다.** `pnpm test`·CI·`docs-audit.sh` 어디도 이 도구를 부르지 않는다.
부르는 사람이 없으면 다음 이동에서 또 죽고, 또 아무도 모른다.

**수리 방향:** ⑴ `frontend/package.json` 에 스크립트로 등재(★[BL-602] 때문에 그 파일 스테이징이
지금 막혀 있다 — 선행 의존) 또는 ⑵ `scripts/` 에 얇은 래퍼를 두고 `docs-audit.sh` 가 **존재+기동만**
확인(전 화면 실행은 느리다). ⑵가 싸고 「죽은 채 방치」를 정확히 막는다.

★★**같은 계열이 하나 더 있다 — `regen_golden.py --check`.** 2026-08-07 에 신설했는데 **어느 게이트도
안 부른다.** 골든이 엔진과 어긋나도 `--check` 를 손으로 돌리기 전에는 아무도 모른다 — [BL-621] 을
만든 것과 **정확히 같은 구조**다(그때는 스크립트조차 없었고, 지금은 있는데 안 부른다).
이 BL 의 수리는 **두 도구를 함께** 붙이는 것으로 정의한다.

**Risk:** 🟡 조용하다. 디자인 캐논 게이트 전체가 **없는 것과 같은 상태**로 임의 기간 지속될 수 있다.

---

### BL-633

**Priority:** P1
**카테고리:** Trading / 라이브 신호 (이중 호스트 오염 — 근인 확정)
**Trigger:** — (부검 완료 · 후속은 BL-634 · BL-641 로 이관)
**Est:** M
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — G-A4‴ 소유권 7/27 · G-A6′ 정본 항등식 4/4(반사실은 정의 4가지 어디서도 4/4 불가 · 최대 1/4) · G-A7 계정 결합 27/27 로 이중 호스트 오염을 근인으로 확정했다. ★원안 G-A4′·G-A6 은 회차 도중 반증돼 교체됐다.

**이중 호스트 오염이 서버 소크 세션 `39484a2c` 를 죽인 근인이다.**

세션 `39484a2c` 는 2026-08-07 09:39:38 에 생성돼 15:10:49.561534 에 `position_divergence` 로
자동 사망했고, 수명은 **5.52h** 였다. 죽인 것은 같은 Bybit demo 계정에 붙은 두 번째 호스트인 맥
로컬이었다.

★★★**판정식이 회차 도중 한 번 교체됐다.** 아래 원안 둘은 적대 검증이 반증했고 CONTROL 이
동결 원자료로 전건 재확인했다. **결론(이중 호스트 오염)은 유지되지만 근거는 대체됐다.**
교체판 정본 = `.claude/fleet/bl003/artifacts/verdict-corrected.md`.

~~**G-A4′ 소유권 = 6/6**~~ — **반증.** `matched_order_id IS NULL` 은 서버 `exchange_exits`
**34행 / 유니크 27 = 전량**을 고른다. BL-605 의 2배 중복 때문에 모든 청산이 최소 1벌은 미조인이라
이 필터는 **판별력이 0** 이다. 「6」은 판정식에 적지 않은 시간 필터의 산물이었다.
★★그리고 그 6건 중 `2cab1a3f`(15:38:36) · `f8ba3233`(16:13:15) · `ebf189cb`(16:23:43) **3건은
사망(15:10:49.561534) 27~73분 뒤 체결**이다 — 사망 뒤 사건은 그 사망의 원인 증거가 될 수 없다.

~~**G-A6 산술 닫힘 = 3/3**~~ — **반증.** 「로컬 순포지션」이라 부른 값이 실은 잔차
`R = exchange − engine` 그 자체라 **항진명제**였고 반증이 불가능했다. 로컬 원장에서 독립 계산하면
**1/3** 이다(`14:17:49` 만 일치 · `14:49:49` 로컬누적 −0.058 vs 잔차 −0.116 · `15:09:49` 로컬누적
+0.116 vs 잔차 +0.058). LESSON-072 계열 재발이다.

~~「서버 엔진은 세션당 고정 sizing 이라 0.087·0.145 를 발주할 수 없다」~~ — **거짓.** 서버 발주
실측 `0.029×9 · 0.058×45 · 0.116×2 · 0.174×3`(체결분만도 `0.029×4 · 0.058×19 · 0.116×1`).
**수량은 호스트 판별자가 못 된다.**

**교체판 ⑴ — G-A4‴ 소유권.** 분모 = 서버 `exchange_exits` 의 고유 `order_link_id` **27**.
분자 = **로컬 원장에만** 있는 것. 실측 **7** — 서버 원장에만 18 · 양쪽 2 · **어느 쪽에도 없는 것 0**.
귀속 불가가 0이라 그 7이 진짜다. ★이것이 증명하는 것은 **「계정이 공유됐다」**이지 「이 7건이
사망을 일으켰다」가 아니다. 사망 인과는 아래 항등식과 발산 관측이 맡는다 — 두 주장을 섞지 마라.

**교체판 ⑵ — G-A6′ 정본 항등식.** `exchange(t) = P0 + Σ(양쪽 호스트 체결)`, `P0 = -0.029` 에서
검사점 4개 **전건 일치(4/4)** 다. ★**반사실이 실제로 떨어진다** — 한쪽 호스트 체결만 쓰면 정의 4가지(서버/로컬 × 공유주문 포함/제외)
어디서도 4/4 가 안 나온다(서버전량 **0/4** · 서버만 **1/4** · 로컬전량 **1/4** · 로컬만 **0/4**, 최대 1/4).
★공유 주문은 `state='filled'` 기준 **3건**이고 한 번만 센다 — 초판의 「2건」은 다른 모집단의 값이었다. 파라미터 1개 대 방정식 4개로 과결정이고, `P0` 조차 독립 결정된다: 로컬 `a7729ddd` 가
`07:42:45.717962` 에 `reduce_only=t buy 0.029` 로 체결했는데 reduce-only 매수는 숏을 닫는 것이므로
그 직전 포지션이 −0.029 다. ★양쪽 원장에 다 있는 공유 주문 2건은 **한 번만** 센다.

**G-A5 size 재현 = 51 정확 일치.** `category=size` 52건은 `14:17:49.558` ~ `15:08:49.945` 에
발화했고 분 유니크는 51이다. **G-A7 계정 결합** — 두 원장의 고유 `exchange_order_id` 가 **27/27**
일치한다. 두 독립 데이터베이스가 같은 27건의 거래소 체결로 수렴했다는 뜻이고, 어느 한쪽 코드의
버그로는 설명되지 않는다.

직전 회차는 서버 HEAD `0c75aaa3` · 고정 커밋 `0c9ccc68` 불변, 배포 0건, 독립 클론을 근거로
「이 회차와 무관」으로 판정했다. 이는 코드 결합만 확인하고 계정 결합을 묻지 않아 틀렸다.

**ADR-025 반례가 아니다.** `phantom` 은 증상이지 원인이 아니었다. 이 창은 이중 호스트로 오염돼
ADR-025 를 시험한 창이 아니므로 **반례로 셀 수 없다**. 이것은 반증 실패가 아니라 시험 표본의
오염 판정이다.

남는 후속은 계정 배타성 가드인 BL-634 와 MTBF 병목인 BL-641 로 이관한다.

**Risk:** 🔴 이 사망은 BL-003 의 차단자가 아니라 오염된 표본이었다. 진짜 차단자는 MTBF 다.

---

### BL-632

**Priority:** P2
**카테고리:** Backtest / Trust Layer (외부 오라클 부재)
**Trigger:** 골든 값이 또 어긋났을 때 · 백테스트 정확성을 대외적으로 주장해야 할 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**골든을 오라클로 승격했지만 그 골든은 여전히 엔진 자신의 출력이다 — 그리고 반순환 근거가 ATR 축을 안 덮는다.**

2026-08-07 backtest-fidelity 가 [BL-621]/[BL-022] 를 닫으면서 `test_golden_backtest.py` 를 smoke 에서
**71 스칼라 + 3 digest + 봉 위치를 전건 비교**하는 오라클로 승격했다. 그런데 그 기대값은
`regen_golden.py` 가 `run_backtest` 를 돌려 받아 적은 **엔진 자신의 출력**이다 ⇒ **회귀 감지기이지
정확성 오라클이 아니다.**

★**반순환 근거가 이 축을 안 덮는다** — 레포의 손계산 오라클 `test_golden_oracle_ema_sltp.py` 는
**4봉 · 고정 stop 95 / limit 110** 시나리오라 **`ta.atr` 를 한 번도 안 탄다**.
`test_golden_oracle_tv_pack.py` 는 합성 계열로 metric **함수**를 검증할 뿐 이 케이스의 진입/청산
집합을 검증하지 않는다. ⇒ **이번에 낡음을 만든 바로 그 축(ATR)이 구조적으로 오라클 밖이다.**

★★[BL-621] 본문이 이미 경고해 뒀다 — _"나중에 이 파일을 오라클로 승격하면 **틀린 값을 정본으로
고정**하게 된다."_ 그 승격을 했고, 답한 것은 「부검으로 값의 출처를 설명할 수 있게 됐다」이지
**「외부 오라클을 얻었다」가 아니다.** 이 구분을 문서 밖으로 흘리지 않기 위해 등재한다.

**수리 방향(택1):**
① ATR 기반 SL/TP 케이스에 **손계산 오라클**을 하나 더 만든다(작은 봉 수 + 손으로 계산 가능한 ATR).
② TradingView 에서 같은 전략·같은 봉을 돌린 결과를 **동결 픽스처**로 들여온다([ADR-020] 이 이연한 P-4).
③ 승격을 되돌리지 않고 **문서로만** 한계를 명시한다(현재 상태 — `dev-log/2026-08-07-backtest-fidelity.md` §2.4).

**Risk:** 🟡 지금은 무해하다(값의 출처가 설명 가능하므로). 단 다음 사람이 이 골든을
「정확성이 검증된 값」으로 읽으면 **틀린 값을 근거로 쓴다.**

---

### BL-618

**Priority:** P3
**카테고리:** Docs / 디자인 토큰 SSOT (반응형 브레이크포인트)
**Trigger:** 앱 셸 반응형(사이드바 축소·검색바 숨김·컨테이너 폭)을 다음에 손댈 때
**Est:** S
**상태:** ✅ **Resolved (2026-08-08 fe-canon-and-responsive)** — 수리 방향 **①(문서 정렬)**.
`DESIGN.md` §10.1·§10.2·§10.6·§4.2·§4.3 과 `frontend/AGENTS.md` §10 을 코드 실측
(232 / 64 / 0 · 1024 / 768 · `.page` 1240 · `.lp-page .page` 1120)으로 교체했다. 화면은
1픽셀도 안 바뀐다 — 문서만 코드에 맞췄다(위 ★ 우려에 대한 답).
★★**미해결로 남겨둔 「1200px」 규명이 끝났다 — 4곳이 아니라 5곳이고, 셸 축이 전혀 아니다.**
`globals.css:1836 · 2442 · 2531 · 2991 · 3503`(랜딩 `:3503` 이 종전 셈에서 빠져 있었다)이고
다섯 블록 전부 **콘텐츠 그리드 열 수 축소**(`.kpi-row`·`.metric-groups`·`.diag-row`·`.cta-row` /
`.create-grid` / `.strip-3` / `.setup-grid` / `.lp-hero`·`.lp-feat-grid`·`.lp-steps`)다.
사이드바·토프바·`.page` 폭에 **개입하는 블록이 하나도 없다** ⇒ §10.2 의 「1200px↓ 사이드바
축소」는 코드 근거 0건이었고, 셸 경계는 **1024 / 768 둘뿐**이다.
★★★**정본이 셋이 아니라 넷이었다** — `globals.css:204-211` 의 `@theme` 가 Tailwind 스케일을
덮어써 `sm:` 은 640 이 아니라 **375**, `xl:` 은 1280 이 아니라 **1200**, `2xl:` 은 **1440** 이다.
`frontend/AGENTS.md` 표가 이것을 「Tailwind v4 기본값」이라 적고 있었으므로 **미비가 아니라
틀린 값**이었고, `sm:` 은 실사용 36건이라 화면에 실제로 영향을 준다.
★**오라클을 신설했다** — 그전까지 e2e 전체에서 `sidebar` grep 이 **0건**이라 이 표가 틀려도
게이트가 조용했다. `e2e/design-canon-responsive.spec.ts` 가 경계 4점(1025/1024/769/768)의
`--sidebar-w` · 주입 `.sidebar` 실폭+`display` · 실물 `.page` max-width 를 3층으로 잰다.
★부수 관측 3건은 **등재만** 했다 — 767 vs 768 1픽셀 어긋남 [BL-644] · 렌더 0건인 `.searchbox`
데드 CSS [BL-645] · 어느 정본에도 없는 `@media (max-width:900px)` 5곳 [BL-646] ·
CSS 30곳 전부 desktop-first 라 mobile-first 규약과 정면 충돌 [BL-647].

~~**`DESIGN.md` 의 반응형 규정이 자기 자신과 어긋나고, 2세대 프로토타입 실측과도 어긋난다.**~~

2026-08-07 prototype-canon-v2 회차에서 `INTERACTION_SPEC.md` 폐기 판정을 위해 브레이크포인트를
대조하다 발견했다. 1세대와 무관한 **별개 축**이라 그 PR 에서 고치지 않고 등재만 한다.

| 항목               | `DESIGN.md`                                                                         | `shotgun-2026-07/_kit.html` (실측) |
| ------------------ | ----------------------------------------------------------------------------------- | ---------------------------------- |
| 사이드바 축소      | **§10.2(`:502`) 1200px↓** vs **§10.6(`:600-608`) 1024px~** — 같은 문서 안에서 두 값 | `:966` **1024px**                  |
| 사이드바 폭        | `:499` 확장 **220px** / 축소 **60px**                                               | `:70` **232px** / `:966` **64px**  |
| 컨테이너 max-width | `:161` `.container` **1200px**                                                      | `:335` `.page` **1240px**          |
| 검색바 숨김        | §10.6 1024px~ (§10.2 는 미기재)                                                     | `:972` 1024px (일치)               |

★**세 번째 값 세트가 하나 더 있다** — `frontend/AGENTS.md:245-253` 은 Tailwind v4 기본값
(`sm` 640 / `md` 768 / `lg` 1024 / `xl` 1280)만 규정하고 **셸 고유 브레이크포인트(사이드바 폭·검색바)는
0건**이다. 즉 FE 구현자가 볼 수 있는 정본이 세 곳인데 서로 다르다.

~~★`HANDOFF-react-port.md:58,166` 이 「1024px 아이콘 레일」을 🔴 **미구현**으로 등재해 뒀다
(`sidebarOpen` 이 뷰포트를 안 보고 Zustand 수동 토글). ⇒ **어느 값이 정본인지부터 정해야** 그 구현을
시작할 수 있다.~~

★★★**2026-08-08 반증 — 아이콘 레일은 이미 구현돼 있다. HANDOFF 의 🔴 등재가 낡았다.**
`frontend/src/styles/globals.css:185-190` 이 언레이어드 `:root` 에서
`@media (max-width:1024px) → --sidebar-w: 64px` · `@media (max-width:768px) → 0px` 를 오버라이드하고,
`dashboard-sidebar.tsx:3` 이 「1024px 아이콘 레일은 순수 CSS 로 접힌다 — `sidebarOpen` 프롭 삭제」를
명시한다. 기본값은 `:169` **232px**, `.page` max-width 는 `:1218` **1240px** — **전부 `_kit.html`
실측값**이다(코드 주석도 「값·브레이크포인트는 `_kit.html` 과 동일」이라 적었다).
⇒ **수리 방향은 ①로 사실상 확정된다** — 코드가 이미 ①이므로 ②를 고르면 화면을 바꿔야 하고, 그건
본 BL 이 스스로 「17벌 재검증이라 비용이 크다」고 적은 갈래다. **남은 일은 구현이 아니라 문서 정렬이다.**
★★**단 미해결이 하나 남는다** — 코드에 `@media (max-width: 1200px)` 가 **4곳**(`:1844` `:2450`
`:2539` `:2987`) 살아 있다. `DESIGN.md` §10.2 의 「1200px↓」와 같은 것인지 다른 축인지 **정렬 전에
규명해라.** 이 항목이 「1024 vs 1200」 혼선의 잔여일 수 있다.
★이 반증은 이 레포가 반복해 덴 계열이다 — [BL-630] 도 「핸드오프가 등재한 `td.num` 문제는 이미
수리돼 있었다」였다. **핸드오프의 🔴 는 그 시점 관측이지 현재 상태가 아니다.**

**수리 방향(택1, 결정 필요):** ① `_kit.html` 실측값(232/64/1240/1024)을 정본으로 삼고 `DESIGN.md`
§10.2·§10.6·§4.2 를 정렬 ② `DESIGN.md` 를 정본으로 삼고 2세대 셸을 고친다(★`preflight.py` 가
`_kit.html` 바이트 비교로 잡으므로 17벌 전부 재검증 필요 — 비용이 크다).
★①을 고르더라도 **시각 회귀 위험**이 있다 — FE 는 이미 `_kit.html` 계열 값으로 이식됐으므로
`DESIGN.md` 쪽만 고치면 문서가 코드에 맞춰지는 것이지 화면이 바뀌지 않는지 먼저 확인해라.

**Risk:** 🟢 프로덕션 무관. 현재 화면은 이식된 값으로 동작하고 있고, 위험은 **다음 사람이 세 정본 중
틀린 것을 골라 구현하는 것**이다.

**출처:** 2026-08-07 prototype-canon-v2 (`INTERACTION_SPEC.md` 폐기 대조 중 실측)

---

### BL-634

**Priority:** P1
**카테고리:** Trading / 계정 배타성
**Trigger:** 실자금 전환 전 필수 / 두 번째 호스트를 다시 띄우기 전
**Est:** M
**상태:** ✅ **Resolved** (2026-08-09 excl) — 가드가 `LiveSignalSessionService.register()` 의 **전제조건**으로 들어갔다(`src/trading/services/account_exclusivity.py`, 잔고 스냅샷 뒤 · quota lock 앞). HTTP(`router.py:458`)와 스크립트(`live_session_admin.py:_cmd_start`)가 공유하는 유일한 병목이라 두 경로가 함께 덮인다 — 종전의 유일한 강제였던 `scripts/soak-restart.sh` 는 소크 재시작 경로에만 걸렸다. 판정식은 [BL-639] 가 확정한 그대로(resting conditional · `reduce_only=None` · `order_link_id` 소유권)다. ★**소유권 집합의 계정 축 = `exchange_uid` 형제 행 전량**(BL-639 실패 모드 3 종결) — 스코프 없음은 거부율이 원장 크기를 따라가고, 행 하나로 좁히면 [BL-605] 의 2행 때문에 **우리 주문을 FOREIGN 으로** 판정해 정상 재기동을 영구히 막는다. ★fail-closed — 거래소를 못 읽으면 `ProviderError` 가 올라가 세션이 안 열린다. ★`exclusivity_service` 는 **필수 인자**다(기본값 `None` 은 새 조립부를 조용히 무방비로 만든다). 회귀 = `tests/trading/test_account_exclusivity_guard.py` 6건, **변이 2종으로 판별력 실증**(가드 호출 제거 → 5/6 red · 계정 축을 자기 행으로 좁힘 → 형제 테스트 red)

**계정 배타성 가드가 없어 같은 Bybit demo 계정에 두 호스트가 동시에 붙을 수 있다.**

두 호스트는 두 DB 를 쓰므로 `live_signal_sessions` 의 unique index 는 원리상 다른 호스트를 막지
못 한다. 각 DB 는 자기 세션만 안다. 그래서 서버 소크와 로컬 `make up` 이 같은 Bybit demo 계정에
동시에 붙었고, 서버 세션 `39484a2c` 가 `position_divergence` 로 죽었다. 수명은 **5.52h** 였다.

가드는 거래소 쪽 상태를 봐야 하며, 이번 사망의 직접 원인이다. 미조인 체결 이력으로 가드를 만들면
상시 거부가 되므로 설계 제약은 BL-639 를 함께 읽어야 한다.

**Risk:** 🔴 두 번째 호스트가 같은 계정에 붙으면 독립 DB 의 제약은 작동하지 않고, 기존 소크를 다시
오염시킬 수 있다.

---

### BL-635

**Priority:** P1
**카테고리:** 운영 / 소크 게이트 아카이브
**Trigger:** — (해결됨. 맥 launchd 잔여는 별도 후속)
**Est:** S
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — 서버 게이트 아카이브의 판독 불가를 fail-closed 로 처리했다.

**게이트 아카이브 오염이 라이브 기전이다.**

맥의 launchd `dev.quantbridge.soak-gate` 는 `StartInterval 1800` 으로 **30분마다** 돈다. 워커
컨테이너가 없으면 `docker logs` 가 실패하고 `2>&1` 이 오류 첫 토큰 `Error` 를 타임스탬프 자리에
넣는다. 판정기는 `ValueError: Invalid isoformat string: 'Error'` 로 죽고, 그 크래시의 exit 1 은
FAIL 과 구분되지 않는다. 로컬 실측은 09:44~13:30 오염 **8벌** / 14:00~17:01 정상 **9벌**
— 워커 생존 — / 17:31 다시 오염 **1벌**이다. 서버는 아직 오염 **0벌**이지만 `soak-watch.timer` 가
같은 30분 주기로 돌고 `soak-restart.sh` 가 부르는 `down` 창이 정확히 같은 조건을 만든다.

**Resolved 근거 — 이번 브랜치 커밋 `32ea2a5d`.** `scripts/soak-gate.sh` 가 `docker logs` 반환 코드와
ISO 8601 형식을 모두 검사해, 실패하면 커버리지를 비우고 `log_note` 를 싣는다.
`backend/scripts/soak_gate_predicate.py` 에 `parse_log_coverage` 와
`summarize_unreadable_log_coverage` 를 추가해 판독 불가 항목의 시간을 credit 하지 않고
`UNKNOWN 측정불가` 로 낸다. C3 실격 **뒤**에 두어 진짜 실격을 UNKNOWN 이 덮지 못하게 했다.
같은 커밋은 systemd unit 에 `SuccessExitStatus=1 2` 를 넣어 UNKNOWN=2 가 매 실행 `failed` 로
남던 것도 고쳤다.

★**스케줄러 범위 — 오해하지 마라.** 오염을 만드는 자리는 `scripts/soak-gate.sh` **본문**이고 그
파일은 맥 launchd 와 서버 systemd 가 **같은 것을 부른다**(`:30` 의 `LABEL` 하나로 양쪽을 설치한다).
따라서 `docker logs` rc·ISO 검사는 **두 스케줄러 모두**에 적용된다. systemd 전용은
`SuccessExitStatus=1 2` 한 줄뿐이고, launchd plist 에는 대응 항목이 없다.

★**남은 것 2가지.** ⑴ **이미 설치된** 유닛·plist 는 `--install` 을 다시 돌리기 전까지 낡은 정의를
쓴다 — 코드가 아니라 운영이다. ⑵ 이미 찍힌 로컬 오염 **9벌**은 `.soak/` 에 그대로 남아 있고, 게이트는
`state.glob("phantom-*.json")` 로 **창 없이 전부** 읽는다 ⇒ 수리 후 그 아카이브들은 크래시 대신
`UNKNOWN 측정불가` 를 만든다. **[확인 필요]** 이 ⑵는 코드 대조로만 확인했고 실행으로 재현하지 않았다.

**Risk:** 🟡 fail-open 은 닫혔지만, 낡은 오염 아카이브가 남아 있는 동안 로컬 게이트 판정은
`UNKNOWN` 으로 고정될 수 있다.

---

### BL-636

**Priority:** P2
**카테고리:** Docs / 백로그 인덱스 검사
**Trigger:** 다음 백로그 인덱스를 편집할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**backlog 인덱스 표가 파손돼도 `bl-audit.sh` 는 이를 감지하지 못 한다.**

실측에서 P1 표는 `BL-522` 다음의 빈 줄 하나 때문에 `BL-619` **1행**이 헤더 없는 조각이 됐고,
P2 표는 `BL-617` 다음의 빈 줄 하나 때문에 BL-625/621/627/628/629/630/633/632/631/624/626/623/620
**13행**이 헤더와 구분선 없는 조각이 됐다. GFM 에서 구분선 없는 파이프 줄은 표로 렌더되지 않아
그 14행은 문서상 보이지 않았다.

`scripts/bl-audit.sh` 는 줄 형태 정규식 `^\|[ ]*\[BL-[0-9]+\]\(#bl-[0-9]+\)` 만 보고 H2 섹션이나
표 경계를 추적하지 않는다. 따라서 조각 속 행도 정상 행처럼 읽혀 3면 대조가 통과했다.

이번 회차는 빈 줄을 제거하고 조각을 재결합해 행 손실 없이 총 **104행**을 보존했다. 검사 축 추가는
하지 않았으므로 재발 방지는 없다.

**Risk:** 🟡 다음 편집자가 같은 자리에 빈 줄을 넣으면 인덱스 행이 다시 문서에서 보이지 않을 수 있다.

---

### BL-637

**Priority:** P2
**카테고리:** Docs / 백로그 우선순위 검사
**Trigger:** 다음 백로그 인덱스를 편집할 때
**Est:** S
**상태:** ✅ **Resolved (2026-08-08 bl003-unblock 회차)** — `scripts/bl-audit.sh` 에 우선순위 배치가 **4번째 검사 축**으로 들어갔다. 출력은 「✓ 4면 정합 — 3면(섹션 · 인덱스 표 · 로드맵) + 우선순위 배치」다. ★판별력 주입 시험 **2/2** — BL-626 섹션의 `**Priority:**` 만 P3→P1 로 바꾸자 exit 1(「우선순위 배치 1 건」), 문자열 치환으로 되돌리고 sha256 일치로 원상복구를 증명한 뒤 exit 0.

**`bl-audit.sh` 는 인덱스 행의 우선순위 배치를 검사하지 않는다.**

이 스크립트는 섹션 상태·인덱스 표 마커·로드맵 체크박스 3면을 대조하지만, 인덱스 행이 해당 BL 의
`**Priority:**` 와 같은 H2 표 아래에 있는지는 보지 않는다. 2026-08-08 수리 전 실측 불일치는
**40건** — BL-522 1건, P3 섹션인데 P2 표에 있던 **38건**, BL-633 1건 — 이었다. P3 H2 아래에는
인덱스 표가 아예 없어 새 P3 항목이 모두 P2 표 꼬리에 붙었다.

이번 회차는 P3 인덱스 표를 신설하고 40건을 제자리로 옮겼다 — P0 1 / P1 9 / P2 56 / P3 38, 합 104.
검사 축은 추가하지 않았으므로 열어 둔다.

**Risk:** 🟡 상태 대조가 통과해도 우선순위 표가 잘못된 H2 아래에 놓일 수 있다.

---

### BL-638

**Priority:** P3
**카테고리:** Docs / 보관 경로
**Trigger:** 문서 보관 경로를 다시 안내하거나 정리할 때
**Est:** S
**상태:** 🟡 **Partial (2026-08-08 bl003-unblock 회차)** — `docs/archive/` 디렉터리가 실재하게 됐고 `lessons-archive-2026H1.md` 가 들어갔다(lessons 442→341). ★**남은 것** — `docs-audit.sh` 의 `legacy_paths` 가 권장 대체 경로로 가리키는 `docs/archive/{operations,product,architecture,domain}/` 4종은 **여전히 없다**. 경로 존재 검사가 없어 게이트가 이를 안 잡는다.
**트리거 판정:** 미도래 — 동승 조건(문서 보관 경로를 다시 안내하거나 정리할 때). 잔여는 `legacy_paths` 가 가리키는 `docs/archive/{operations,product,architecture,domain}/` 4종 부재이고, 그 안내를 고치는 회차에 붙는다 (2026-08-11 bl-703-partial-verdicts)

**`docs/archive/` 부재로 권장 경로가 실행 불가였다.**

`scripts/docs-audit.sh` 는 `docs/archive` 를 `frozen` 3종 중 하나로 선언하고
`docs/dev-log`·`docs/reports` 와 함께 관리한다. 또한 `legacy_paths` 의 권장 대체 경로는
`docs/archive/operations/` · `docs/archive/product/` · `docs/archive/architecture/…` ·
`docs/archive/domain/…` 이다. 그러나 2026-08-06 문서 대개편이 `docs/archive/` 를 통째로 지워
권장 경로가 없는 디렉터리를 가리켰다.

2026-08-08 실측으로 `docs/archive/` 는 다시 생겼고 다른 에이전트가 `lessons-archive-2026H1.md`
1개를 넣었다. 다만 `legacy_paths` 가 가리키는 하위 경로 4종은 여전히 없다. `docs-audit` 는 권장
문자열일 뿐인 이 불일치를 검사하지 않으므로 조용히 통과한다.

**Risk:** 🟡 안내를 따라가도 대상 경로가 없어 과거 자료를 꺼낼 수 없다.

---

### BL-639

**Priority:** P2
**카테고리:** Trading / 계정 배타성 판정 제약
**Trigger:** BL-634 를 구현하기 전
**Est:** S
**상태:** 🟡 **부분 해결** (2026-08-08) — 판정식(`EXCLUSIVE`)과 **판별력 실측치**가 확정됐다. 남은 것은 실패 모드 3(소유권 집합의 계정 축)이고 그 결정은 [BL-634](#bl-634) 구현에 속한다
**트리거 판정:** 도래 — 선행 [BL-634] 가 **2026-08-09 에 ✅ Resolved** 됐다(`account_exclusivity.py` 가드가 `register()` 전제조건으로 들어감). 즉 「구현하기 전」이라는 창은 **이미 지났고**, 남은 실패 모드 3(소유권 집합의 계정 축)은 그 결정 없이 머지됐다. ★기계는 「기 전」이 동승 어휘라 「판단 필요」를 냈다 — 사람이 본문 대조로 뒤집은 건이다 (2026-08-11 bl-703-partial-verdicts)

**미조인 `exchange_exits` 는 상시 기저율이어서 배타성 판정의 근거가 될 수 없다.**

BL-634 의 가드를 「원장에 없는 체결 이력이 있으면 남의 호스트다」로 만들면 상시 거부가 된다.
실측: `matched_order_id IS NULL` 은 서버 `exchange_exits` **34행 / 유니크 27 = 전량**을 고른다 — BL-605 의 2배 중복 때문에 모든 청산이 최소 1벌은 미조인이라 **이 필터의 판별력은 0** 이다. ★부검 초판이 인용한 「6건」은 판정식에 적지 않은 시간 필터의 산물이었고 회차 도중 반증됐다.
BL-605 의 중복 채널이 살아 있는 한 미조인 행은 항상 존재한다. 과거 회차의 계정별 `ours/unknown`
분리도 부수효과 dedup 의 산물이지 소유권 판정이 아니었다.

따라서 배타성 판정 대상은 체결 이력이 아니라 미체결 resting 조건부 주문이어야 한다. 이는 지금 이
계정을 누가 잡고 있는지를 재고하므로 과거 이력의 기저율에 오염되지 않는다.

### ★2026-08-08 — 판정식은 이미 존재한다. 판별력을 **실측했다** (soak-attribution-close)

**결론은 유지되고 근거가 교체된다.** 「판별력 0 · 34행 전량」은 **계정 스코프 없이 센 값**이었다.
계정을 좁히면 그 값이 틀린다 — 아래 표가 그것을 대체한다.

**판정식 (신설 아님 — `backend/scripts/live_session_admin.py:206-256` 이 이미 구현했고 근거 주석까지 있다):**

```
EXCLUSIVE ⟺ ∀ resting conditional order o (reduce_only=None 전량) : o.order_link_id ∈ {Order.id}
```

`fetch_open_conditional_orders(creds, symbol, reduce_only=None)`(`providers.py:1233-1320`)이
필수 계약이다 — 기본값 `True` 는 TP/SL 만 주고, **오염을 만드는 것은 조건부 진입**(reduce-only 가
아니다)이다. 소유권 축은 `order_link_id ∈ {Order.id}` 이고, 이는 `classify_exit` 2차 판별자
(`exit_attribution.py:53-55`)와 같은 술어다 — `matched_order_id` 는 그 술어의 **계정 스코프 한정
근사**일 뿐이고, 판별력이 0인 것은 후자다.

**실측 판별력 (2026-08-08 · 서버 소크 진행 중 세션 `a4f1cbfb` · `--symbol BTC/USDT`):**

| 축                  | 값                                                                                                                                                                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **정상 상황 거부**  | `FOREIGN_RESTING=0` · `EXCLUSIVE=YES` ⇒ **오탐 0**                                                                                                                                                           |
| resting 계상        | `RESTING_CONDITIONAL=2` ★**실제 조건부 주문은 1건**이다 — 같은 `link=dd58ef44`·같은 trigger·같은 qty 가 두 계정으로 중복 계상됐다([BL-651](#bl-651))                                                         |
| 체결 이력 축 (참고) | `matched_order_id IS NULL` = 574 중 312. **계정을 `19a8166a` 로 좁히면 287 중 25(8.7%)** — 「전량」이 아니다. 그중 `classification='unknown'` **8건은 전부 2026-08-07**(BL-633 오염 창)이고 그 외 날짜엔 0건 |

★**체결 이력 축이 판별력 0 이라는 진술은 계정 스코프를 붙이면 성립하지 않는다.** 다만 결론은
그대로다 — 남은 25건 중 12건이 `external_manual`(사용자 수동 청산)이라 **정상 상황에서도 발생**하고,
`unknown` 8건의 적중은 **오염 창 1건에서 유도한 것이라 적합이지 검증이 아니다**(표본 1). resting 축은
그런 유도 없이 지금 이 순간의 점유를 직접 잰다.

**실패 모드 (판정식이 놓치는 것 / 오탐하는 것):**

1. **미탐** — 남의 호스트가 조건부 주문을 안 쓰고 시장가만 내면 resting 이 0이라 `EXCLUSIVE=YES` 가 된다.
2. **미탐** — 심볼 인자가 1개(`_cmd_status(symbol)`)라 다심볼 계정에서는 **부분 판정**이다.
3. **오탐 위험** — 소유권 집합이 `SELECT id FROM trading.orders`, 즉 **전 계정·전 시간 무필터**다.
   계정 스코프를 붙이면 형제 계정 주문을 남의 것으로 세고, 안 붙이면 진짜 남의 계정 주문 id 를 우리
   것으로 셀 수 있다. [BL-634](#bl-634) 구현 시 이 축을 결정해야 한다.
4. **개수 오염** — 계정 중복으로 `RESTING_CONDITIONAL`·`FOREIGN_RESTING` 이 2배가 된다. 판정(≠0)은
   안 깨지지만 **개수를 문턱으로 쓰면 깨진다**.

**Risk:** 🔴 체결 이력을 가드로 쓰면 정상 운영도 상시 거부할 수 있다. ★resting 축은 실측 오탐 0 이지만
**미탐 2종**(시장가 전용 호스트 · 다심볼)이 남아 있으므로 「가드가 통과했다 = 배타적이다」로 읽지 마라.

---

### BL-640

**Priority:** P3
**카테고리:** 운영 / 지표 세대 경계
**Trigger:** 게이트가 `.metrics` 값을 창 기준으로 해석할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`.metrics` 합산은 죽은 컨테이너 세대의 값을 함께 센다.**

`backend/.metrics` 는 역할과 컨테이너 id 로 파일이 갈린다. 파일을 전부 합산하면 죽은 이전 세대의
값까지 들어온다. 2026-08-08 실측에서 `engine_only_suppressed` 합산 **89** 중 **15가 이전 컨테이너**
세대의 값이었다. 창 안의 차분을 보려 해도 창 밖 값이 섞인다.

BL-620 이 게이트 취득 경로를 HTTP 에서 `.metrics` 직독으로 바꿨으므로 이 함정은 게이트 경로 위에
있다. 당장은 현 컨테이너 id 만 거르는 세대 필터 또는 창 시작 스냅샷과의 차분으로 읽어야 한다.

**Risk:** 🟡 이전 세대 누적을 이번 창의 관측값으로 오독할 수 있다.

---

### BL-643

**Priority:** P2
**카테고리:** DX / 종결 게이트 (산문 처방이 세 번째로 실패하지 않게)
**Trigger:** — (해결됨. 게이트가 매 실행 집행한다)
**Est:** S
**상태:** ✅ **Resolved (2026-08-08 soak-exclusivity-and-observability 회차)** — 술어 2개가
`scripts/docs-audit.sh` 에 착지했다(`final-gates.sh:162` 와 CI 가 이미 부른다 = 소유자 있음).
★★**초안의 낱말 술어를 구문 술어로 바꿔 오탐을 없앴다** — 실행 지시는 언제나 `다음 행동 = …`
형태이므로 `=` 를 요구하면 규칙을 _설명하는_ 문장 2건이 자동으로 빠진다. 그래서 본문이 지시하던
「⓪ 표 안쪽 제외」는 **불필요해졌다**(낱말 술어를 전제한 처방이었다).
★★★**그리고 본문의 「블록 내」가 틀렸다 — 파일 전체로 센다.** 실제 사고의 2건은 서로 **다른
섹션**에 하나씩 있었고(`ce583eef^` 실측: 66줄·171줄), 블록별로 세면 각 1건이라 **그 사고가
그대로 통과한다**. 계약 문구는 사람이 읽는 규범으로 두고 집행만 넓혔다.
★★★**착지 직후 그 게이트가 이 회차 기록을 물었다** — 규칙을 _설명하면서_ 규칙 자신을 인라인
코드로 인용한 3줄이다(코드펜스는 제외했는데 인라인 코드는 안 했다). **문장을 비틀지 않고 술어를
고쳤다** — 규칙을 문서화할 수 없는 게이트는 틀린 게이트다.
★판별력 = 변이 **8/8** — 대조군 통과 · 수리 전 실물(`ce583eef^`) FAIL(두 술어 모두 발화) ·
⓪ 표 2행 축소 FAIL · 살아 있는 지시 2건 FAIL · **설명 문장 3줄 추가 PASS(오탐 0)** ·
**코드펜스 안 지시 2건 PASS** · **인라인 코드 인용 3건 PASS** · ★**같은 문장에서 백틱만 제거 FAIL**
(인용과 지시를 백틱 유무로 정확히 가른다). 음성 대조: 현행 트리 0건 vs 수리 전 2건.
★**한계는 본문 그대로 남는다** — 모순 탐지기이지 낡음 탐지기가 아니다(단독 1건 · 어구 변형은 사거리 밖).

**`docs/status.md` 「다음 스프린트」 블록의 최신성을 어떤 게이트도 보지 않는다.**

2026-08-08 실측 — 그 블록에 이미 끝난 일을 지시하는 「다음 행동」이 **2곳** 살아 있는 동안
`bash scripts/bl-audit.sh` 와 `bash scripts/docs-audit.sh` 가 **둘 다 exit 0** 이었다.
그 블록은 [ADR-026]·§G8 상 **다음 세션의 유일한 진입점**인데, 내용을 읽는 기계가 없다.

★★**산문 처방은 이미 두 번 실패했다.** §G8 이 2026-07-27 에 「종결 체크리스트에 **「요약(INDEX·roadmap·status)을
본문과 대조」를 고정 항목으로 넣는다**」고 적었는데 **실행처를 만들지 않았다** —
`grep -c "본문과 대조" docs/reference/operations/workflows/sprint-template.md` = **0**.
2026-08-08 PR #562 가 세 번째로 산문을 추가했고, 그 PR 자신이 「이 항만은 어느 게이트도 안 잡는다」를
자백하는 형태로 닫았다. **LESSON-078 의 한 층 위 판본 — 아무도 만들지 않은 체크리스트다.**

★**단순 문자열 술어는 못 쓴다 (실측).** 「취소선 없는 `다음 행동` 개수 ≥ 2」를 두 브랜치에 돌렸다:

```
origin/main (수리 전)          살아있는 「다음 행동」 2건   ← 진성 검출
stage/bl003-unblock (수리 후)  살아있는 「다음 행동」 1건   ← ★오탐
```

그 1건은 새 스프린트 블록의 **「본 블록의 낡은 「다음 행동」 잔여도 정리」**, 즉 **규칙을 설명하는 문장 자신**이다.
★부수 미탐 2종도 확인됐다 — ⑴ 어구를 「다음 스텝」·「이제 할 것」으로 바꾸면 눈이 먼다
⑵ 낡은 것이 1개뿐이면 개수 술어가 통과한다(이 술어는 「낡음」이 아니라 **「모순(다중성)」**을 잰다).

**수리 방향 — 의미론을 구문론으로 바꾸는 선행이 필요하다.**
「다음 행동」은 §G8 의 **6필드 실행 계약에 없는 임시 어구**라 셀 수가 없었다. 그것을 필드로 승격해야
`scripts/docs-audit.sh` 에 `docs/status.md` 대상 검사를 붙일 수 있다. ★부르는 자리는 **새로 만들 필요가
없다** — `scripts/final-gates.sh:162` 와 CI 가 `docs-audit.sh` 를 이미 부른다(LESSON-078 조건 충족).
★★그때도 정직하게 적어라 — 그것은 **모순 탐지기이지 낡음 탐지기가 아니다**(단독으로 낡은 1건은 여전히 통과).

★**2026-08-08 PR #562 로 선행 절반이 착지했다.** §G8 계약이 **7필드**가 됐다 — 신설 **⓪ 다음 후보**
(추천도·난이도·소요·`backend/src` 접촉·리스크 5열 표)가 「고르는 자리」를 갖고, 「다음 행동」은 그
**선택의 결과**로 정의됐다. ★계약이 「정확히 1개」가 아니라 **≤1** 인 것에 주의해라 — 아직 안 고른
상태(0개)가 정상이기 때문이다. 초안의 「정확히 1」은 **작성 당시 main 에서 이미 거짓**이었다
(블록 안 살아 있는 「다음 행동」 0건 · 존재하는 3건은 전부 취소선 + 전부 블록 밖).

**남은 것 = 술어 2개뿐이다.** ⑴ `⓪` 표의 행 수 **≥3** ⑵ 블록 안 비취소선 `다음 행동` **≤1**.
⑵ 는 위에 기록된 오탐(규칙을 _설명하는_ 문장)을 여전히 문다 — **⓪ 표 안쪽과 코드펜스를 제외**하고
세야 한다. 미탐 2종(어구 변형 · 단독 낡음)은 이 술어의 사거리 밖으로 남는다.

**Risk:** 🟡 조용하다. 그리고 이 항목이 실패하는 방식은 **다음 세션이 끝난 일을 다시 하는 것**이라
비용이 회차 단위로 붙는다.

---

### BL-642

**Priority:** P2
**카테고리:** 운영 / 소크 재기동 (BL-620 과 같은 실패 계열, 다른 도구)
**Trigger:** — (해결됨. 서버 실행 검증은 다음 재기동의 ⑺ 이 그대로 오라클이다)
**Est:** XS
**상태:** ✅ **Resolved (2026-08-08 soak-exclusivity-and-observability 회차)** — `soak-gate.sh` 의
취득 블록을 이식했다(`0f7f9342`). 기본이 `.metrics` 직독이고 `QB_METRICS_URL` 명시 시 HTTP.
함수를 추출해 5경로로 검증했다 — 직독 성공(244 series) · dir 부재 실패 · HTTP 본문 성공 ·
**HTTP 200+빈 본문 실패** · 죽은 포트 실패(직독 fallback 안 함), 5/5.
★음성 대조로 판별력을 확인했다 — 같은 호스트에서 수리 전 명령은 `rc=7` 이다.
★수리하며 **인접 fail-open 하나를 같이 닫았다**: 취득과 series 필터가 한 파이프에 있어
「매치 0건」(counter 미발화)이 파이프 rc 로 「스크레이프 실패」와 구분되지 않았다. 이제 분리한다.

**`soak-observe.sh` 가 아직 `http://localhost:8100/metrics` 를 긁어 재기동 ⑺ 을 실패시킨다.**

2026-08-08 bl003-unblock 재기동 실측 — `soak-restart.sh --confirm` 이 ⑴~⑹ 을 전부 통과하고
`.soak/session` 도 올바른 `SESSION_ID=` 형식으로 쓴 뒤 ⑺ 에서 죽었다:

```
── 4. counter 차분 (★절대값 비교 금지 — 이전 스냅샷 대비 변화만)
  UNKNOWN — http://localhost:8100/metrics 스크레이프 실패
✗ 일부 조회가 실패했다 — 위 UNKNOWN 을 「이상 없음」으로 읽지 마라.
✗ baseline 앵커 실패
```

★**[BL-620] 이 정확히 이 실패를 게이트에 대해 닫았다** — `soak-stack.sh up` 은 API 컨테이너를
띄우지 않으므로 `:8100` 에 리스너가 없고, 그래서 `soak-gate.sh` 의 취득 경로를
**`backend/.metrics` 직독**으로 바꿨다. `soak-observe.sh` 는 **그 교체를 안 받았다.**
같은 실패 계열이 도구별로 남아 있는 형상이다.

★**피해는 한정적이다** — 세션 등재·`.soak/session` 기록은 ⑺ **전에** 끝나므로 재기동 자체는
성공한다. 잃는 것은 baseline 스냅샷의 counter 차분 절이고, 게이트 판정에는 영향이 없다
(2026-08-08 실측: 재기동 직후 게이트가 `UNKNOWN 진행중` · C5 전건 ✓).
단 **⑺ 이 실패하면 `soak-restart.sh` 가 ⑻(게이트 확인)까지 못 간다** — 운영자가 손으로 게이트를
다시 돌려야 한다.

**수리:** `soak-gate.sh` 의 취득 함수를 그대로 재사용해라 — `QB_METRICS_URL` 이 있으면 HTTP,
없으면 `PROMETHEUS_MULTIPROC_DIR` 직독. 두 도구가 같은 경로를 쓰게 만드는 것이 요지다.
★그리고 **취득 실패를 「이상 없음」이 아니라 `측정불가`로 내는 현재 동작은 옳다** — 그것까지 바꾸지 마라.

**Risk:** 🟡 조용하지 않다(재기동마다 빨간 줄이 뜬다). 다만 그 빨간 줄이 **진짜 실패처럼 보여**
운영자가 재기동이 실패했다고 오독할 수 있는 것이 실질 위험이다.

---

### BL-641

**Priority:** P1
**카테고리:** 운영 / BL-003 게이트 해석
**Trigger:** BL-003 재계획 시 즉시 / 소크 재기동 회차마다 재측정
**Est:** M
**상태:** 🟡 **부분 해결 — 2026-08-12 재측정 완료. 셈은 움직였지만 CI 는 아직 못 가른다**
(2026-08-08 soak-exclusivity-and-observability 착지 · 2026-08-12 surface-demo-pack 재측정).
⑴ 층화 + **95% 신뢰구간**을 [ADR-024] 에 등재했고
⑵ 재측정 도구 `backend/scripts/mtbf_stratified.py` 를 만들어 「회차마다 재측정」 Trigger 를
집행 가능하게 했다(self-check 가 앞 38행으로 이 회차 값을 재현한다, 2/2).
⑶ **2026-08-12 에 그 Trigger 뒷절을 실제로 집행했다** — 아래 표가 새 값이다. 4일 만에 노출이
107.12h → 193.37h(**+86.25h**)로 늘었는데 자동 사망은 **8건 그대로**다. **닫는 조건은 불변** —
사망률이 실제로 내려가야 하고, 그 판정은 며칠 단위 관측이라 이 회차 밖이다.
★★★**그 과정에서 이 BL 자신의 인용값이 반증됐다** — 아래 층화 표는 **점추정끼리 비교할 수
없다**. 네 층의 CI 가 **6쌍 전부 겹친다**(상세 = [ADR-024] §층화). ⇒ 「수리로 MTBF 가 올랐다」도
「내렸다」도 이 데이터로는 말할 수 없다. **닫는 조건은 불변** — 사망률이 실제로 내려가야 한다.
**트리거 판정:** 도래 — Trigger 앞절이 발화했다. 「[BL-003] 재계획 시 즉시」인데 **2026-08-11 사용자 결정으로 C1 문턱이 「168h」에서 「누적 24h × 3회」로 교체**됐고(그 미반영이 [BL-701] 로 등재됐다), 뒷절 「소크 재기동 회차마다 재측정」도 2026-08-08 재기동으로 충족된다. ★기계는 트리거에 「소크」가 들어 있어 소크 축으로 버킷하고 미도래를 냈다 — **절의 접속을 반쪽만 읽은 것**이다 (2026-08-11 bl-703-partial-verdicts)

**BL-003 의 실질 선행조건은 문턱이 아니라 MTBF 다.**

ADR-024 리셋 표에 의해 실격은 C1 을 0 으로 되돌린다. 그러므로 「누적 clean 168h」는 사실상
「168시간 연속 무실격」이고, 그 확률이 P(168h 생존)이다.

**2026-08-12 재측정** (surface-demo-pack · 서버 원장 40행 · self-check 2/2 ✓). 괄호는 2026-08-08 값:

| 표본            |   n | 누적                    | 최장                  | 자동 사망 | MTBF                  | 95% CI         | P(168h)                    |
| --------------- | --: | ----------------------- | --------------------- | --------: | --------------------- | -------------- | -------------------------- |
| 전 이력         |  40 | **193.37h** (구 107.12) | **65.28h** (구 19.42) |         8 | **24.17h** (구 13.39) | [12.27, 55.99] | **9.584e-04** (구 3.6e-06) |
| 2026-08-03 이후 |  16 | **147.16h** (구 60.91)  | **65.28h**            |         7 | **21.02h** (구 8.70)  | [10.20, 52.29] | **3.383e-04** (구 4.1e-09) |

**24h 도달 1건 / 40세션** — 전 이력 최초다(구 0/38). 사인 전량(서버 DB GROUP BY):
`user_stopped` **19** · 사인 없음 **13**(1건은 진행 중) · `position_divergence` **6** ·
`gap_resync_position_mismatch` **2**. ★**자동 사망은 뒤의 둘, 합 8건뿐이다.**

★★★**2026-08-12 반증 — 「이 표가 `user_stopped` 를 자동 사망과 함께 센다」는 거짓이었다.**
`user_stopped` 는 `AUTOMATIC_DEATH_REASONS`(8종)에 **없고**, `auto_death` 는 그 집합 소속 여부
단독으로 정해진다(`backend/scripts/mtbf_stratified.py` `parse_rows`). 정본이 코드 옆에 이미 적혀
있었다 — `soak_gate_predicate.py:39` 「`SessionDeactivationReason` 에서 `user_stopped` 를 뺀 것 =
**자동 사망**」. ⇒ 운영자 재기동은 **처음부터 우측 절단**이었고 P(24h)·MTBF 는 오염되지 않았다.
독립 대조: `soak-gate.sh` 실격 목록의 `auto_death` 도 **8건**이고 그 목록에 `user_stopped` 는 0건이다.
★그 대신 **표시 결함이 실재했다** — `절단` 열이 `alive + operational_dropped` 만 세서 40행이
`사망 8 + 절단 1` 로 인쇄됐다(비-자동사망 종료 31건이 어느 열에도 없었다). 산술은 처음부터
맞았고 표시만 틀렸다. 같은 회차에서 `n - deaths` 로 고쳤다.

★**168h 문턱은 이미 폐기됐다** — 2026-08-11 사용자 결정으로 C1 은 「누적 24h × 3회」다([BL-701] 반영).
그러므로 위 P(168h) 열은 **역사적 대조용**이고 판정에 쓰이지 않는다. 지금 진척은 `soak-gate.sh` 의
`C1 24h 창 N / 3회` 줄로만 읽는다(2026-08-12 실측 **1/3**). 사망률을 낮추는 것이 유일한 경로라는
결론은 불변이고, 표적도 그대로다 — BL-634 계정 배타성 이후 `position_divergence` 계열 전체.
이 BL 은 BL-003 의 하위 작업이 아니라 게이트 해석이므로, BL-003 의 Est 를 다시 잡기 전에 읽어야 한다.

**Risk:** 🔴 MTBF 를 개선하지 않으면 168h 연속 무실격 조건은 사실상 도달 불가다.

### BL-710

**Title:** 전략 목록 성과 정렬·파생 필드의 규모 비용 3종 (현 규모에서는 무해)
**Category:** Backend / 성능
**Priority:** P3
**Trigger:** 전략 목록이 느려질 때 / 전략·백테스트가 수천 건이 될 때
**Est:** S-M
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #1·#5·#6 을 평가자가 코드 대조로 채택했으나 발화 조건이 **규모**다.
**트리거 판정:** 미도래 — **규모 조건**이다. 현 실측(전략 3 · 완료 백테스트 7 · 활성 세션 0)에서는 발화하지 않는다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:** 셋 다 [BL-430]/[BL-427] 구현이 만든 것이고 **현 규모에서는 측정 가능한 피해가 없다.**

⑴ `backend/src/strategy/repository.py` 의 `latest_completed` 서브쿼리는 `status == COMPLETED` 만
걸고 **owner 나 현재 페이지의 `strategy_id` 로 좁히지 않는다.** `DISTINCT ON` 이 1:1 을 보장하므로
`total` 은 틀어지지 않지만, 비용이 **페이지 크기와 무관하게 전역 백테스트 수**에 비례한다.
★처방은 1줄이다 — 서브쿼리에 `Backtest.user_id == owner_id` 를 더한다(조인이 이미 그 사용자의
전략에만 붙으므로 **의미 보존**이다).

⑵ `backend/src/strategy/service.py` 의 `param_count` 는 행마다 `_strip_comments` +
`_strip_string_literals` + 정규식을 돈다. 그리고 `list_by_owner` 는 `defer` 가 없어 `pine_source` 를
**전량 로드**한다. 10MB 소스 100건이면 요청당 약 1GB 문자열이다(`pine_source` 크기 상한도 없다).
처방 = `param_count` 를 컬럼으로 영속(**alembic 필요**) 또는 목록 조회에서 `load_only`.

⑶ `backend/src/trading/models.py:471-484` 의 인덱스 3개는 `(user_id, is_active)` ·
`(is_active, last_evaluated_bar_time)` partial · `(user_id, strategy_id, exchange_account_id, symbol)`
partial-unique 다 — **`strategy_id` 선행이 없다.** `list_active_strategy_ids` 의
`strategy_id IN (...) AND is_active` 는 활성 세션 전량을 훑을 수 있다. 처방 = alembic 인덱스.

**Risk:** 🟢 정확성 문제는 없다. 규모가 커지면 지연으로 나타난다.

---

### BL-711

**Title:** `metrics` JSONB 손상값이 정렬 캐스팅에서 목록 전체를 500 으로 만든다 (선재 · 백테스트·전략 양쪽)
**Category:** Backend / 견고성
**Priority:** P3
**Trigger:** 손상 `metrics` 가 관측될 때 / 정렬 축을 늘릴 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #2 채택 + **선재임을 함께 확인**했다(손상 행 관측 0).
**트리거 판정:** 미도래 — 손상 `metrics` 행이 관측된 적이 없다. 발화 조건이 외생이다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:** 정렬 축은 `metrics["<key>"].astext.cast(Numeric)` 이다. 값이 숫자가 아니면
PostgreSQL 이 `invalid input syntax for type numeric` 을 던져 **목록 요청 전체가 500** 이 된다.
같은 응답 경로의 `metrics_summary_from_jsonb` 는 손상값을 `None` 으로 격리하는데 **정렬 경로만**
그 방어를 우회한다.

★**이 회차가 만든 것이 아니다** — `backend/src/backtest/repository.py:165-168` 이 동일한 패턴을
4축(`total_return`·`max_drawdown`·`sharpe_ratio`·`num_trades`)에 **먼저** 갖고 있다. 전략 목록
(`backend/src/strategy/repository.py`)이 그 노출을 물려받았을 뿐이다. **그래서 처방도 한 곳이 아니라
두 도메인에 같이 가야 한다.**

**권장 접근:** 캐스팅 앞에 숫자 판별을 두거나(정규식 `~ '^-?[0-9.]+$'` 후 캐스팅) 안전 캐스팅
함수를 쓴다. ★**한 도메인만 고치면 다른 쪽이 남는다** — 두 파일을 같은 PR 에서 다뤄라.

**Risk:** 🟡 발화하면 목록 화면이 통째로 죽는다. 다만 손상 행이 실제로 관측된 적은 없다.

---

### BL-712

**Title:** 전략 목록 표시 정합 2건 — lifecycle 이 archived 를 안 보고, 정렬 라벨이 방향을 안 말한다
**Category:** Frontend / backend (표시 계약)
**Priority:** P3
**Trigger:** 전략 목록 표시를 다시 손댈 때 / 아카이브 화면을 낼 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #4·#12 채택. ⑴은 **사용자 결정 선행**이다.
**트리거 판정:** 미도래 — ⑴은 **사용자 결정 선행**(칩 4번째 값을 만들 것인가)이고 ⑵는 UI 가 만들지 않는 URL 에서만 보인다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:**

⑴ `lifecycle` 파생은 `deployed → validated → draft` 3분기이고 **`is_archived` 를 보지 않는다.**
아카이브된 전략을 `?is_archived=true` 로 조회하면 `validated`/`deployed` 칩이 그대로 나온다.
`StrategyLifecycle` 에 `archived` 값이 없다. ★**캐논에도 칩이 3종뿐**이라(screen-06) 4번째를 만드는
것은 디자인 결정이다 — 그래서 미도래로 둔다.

⑵ 정렬 select 는 `order_by` 만 반영하고 라벨은 고정 문구(「수익률 높은 순」)다. UI 의 `pushSort` 는
축마다 방향을 고정해 넣으므로 정상 경로에서는 어긋나지 않지만, `?order_by=total_return&order=asc`
같은 URL(공유·수동 편집·뒤로가기)에서는 **오름차순 결과에 「높은 순」 라벨**이 붙는다.

**권장 접근:** ⑴ 사용자와 칩 4번째 값을 정한 뒤 파생에 `is_archived` 를 더한다. ⑵ 라벨을
`order` 에서 파생하거나, 화이트리스트 밖 조합을 기본값으로 정규화한다(후자가 [BL-709] 처방과 같은
자리에서 처리된다).

**Risk:** 🟢 데이터는 정확하고 라벨만 어긋난다.

---

### BL-713

**Title:** e2e 정체성 프로브가 `<title>` 부분일치라 고유 식별자가 아니다
**Category:** 테스트 / 게이트 판별력
**Priority:** P3
**Trigger:** 정체성 프로브가 거짓 통과하는 것이 관측될 때 / 같은 호스트에 앱이 늘 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)** — 처방 미착수. 2026-08-12 codex G6 #10 채택. 현행 판별은 **실측으로 성공**하지만 우연에 의존한다.
**트리거 판정:** 미도래 — 실측으로 지금은 판별한다(`"Nexus Admin"` red). 거짓 통과가 관측되면 도래다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack G6

**원인 / 영향:** `frontend/e2e/identity.setup.ts` 와 `global.setup.ts` 의 프로브는
`title.includes("QuantBridge")` 다. 다른 앱의 title 이 그 문자열을 **포함하기만** 하면 통과한다
(예: `QuantBridge migration docs`). 2026-08-12 실측에서는 `:3003` 의 title 이 `"Nexus Admin"` 이라
정확히 red 가 났지만, 그것은 **이름이 겹치지 않았기 때문**이다.

★같은 회차에 이 프로브가 **status 200 을 통과한 남의 앱**을 잡았다는 것을 기억해라 — status 만으로는
못 잡았고 title 이 잡았다. 그 마지막 판별자가 부분일치라는 것이 이 BL 이다.

**권장 접근:** 앱이 고유 마커를 내보내고 프로브가 그것을 본다 — 예: `<meta name="qb-app"
content="quantbridge">` 또는 루트 요소의 `data-app` 속성. title 검사는 보조로 남겨도 된다.

**Risk:** 🟢 지금은 판별한다. 우연이 깨지는 날 거짓 그린이 된다.

---

### BL-714

**Title:** 마감 게이트가 전제하는 브랜치 상태가 문서에 없다 — 증분 머지 후에는 신호가 구조적으로 초록이 될 수 없다
**Category:** Ops / 게이트 (문서 계약)
**Priority:** P2
**Trigger:** 마감 절차를 다시 쓸 때 / 같은 상태에 또 빠질 때
**Est:** XS-S
**상태:** ⬜ Open — 처방 미착수. 2026-08-12 surface-demo-pack 이 실제로 그 상태에 빠져 신호 4종을 초록으로 만들 수 없었다(빈 커밋으로 브랜치를 만들지 **않았다**).
**트리거 판정:** 도래 — 조건절이 없고 처방이 우리 손 안에 있다. 재현 절차와 실측 출력이 이미 있다 (2026-08-12 surface-demo-pack)
**출처:** 2026-08-12 surface-demo-pack (마감에서 실측)

**원인 / 영향:** `scripts/signal-check.sh` 의 `judge_freshness()` 는 **앵커 A1** 을 가장 먼저 본다:

```sh
if [ -n "$MERGE_BASE" ] && [ "$MERGE_BASE" = "$HEAD_SHA" ]; then           # ← 앵커 A1
  CODE="no-branch-commits"; WHY="브랜치 커밋이 0개다 (merge-base == HEAD)"; return 1
fi
if [ "$sha" = "$HEAD_SHA" ]; then                                          # ← 앵커 A2
  CODE="head"; WHY="HEAD 와 동일"; return 0
fi
```

A1 이 A2 **앞**이므로, 전건 머지돼 `merge-base(origin/main, HEAD) == HEAD` 가 된 main 에서는
신호의 sha 가 HEAD 와 **정확히 같아도** 판정이 `stale[no-branch-commits]` rc=1 이다. 실측:

```
screen.ok rc=1 stale: screen.ok @ 93655ee3 [no-branch-commits] — 브랜치 커밋이 0개다 (merge-base == HEAD)
codex.ok  rc=1 stale: codex.ok  @ 93655ee3 [no-branch-commits] — 동일
g9.ok     rc=1 stale: g9.ok     @ 93655ee3 [no-branch-commits] — 동일
vercel.ok rc=1 stale: vercel.ok @ 93655ee3 [no-branch-commits] — 동일
```

★**A1 을 없애면 안 된다** — 그것이 없으면 main 에 서서 `commit: $(git rev-parse HEAD)` 한 줄만 적어도
4종이 전부 통과한다. [BL-706] 이 막으려던 것이 정확히 그것이다.

★**갭은 게이트가 아니라 문서다.** `§G8` 과 `docs/status.md` ⓸ ④ 는 「마지막 커밋 뒤, 클린 트리에서
게이트를 돌려라」라고만 말하고 **「그 커밋이 아직 머지되지 않은 브랜치에 있어야 한다」를 말하지
않는다.** 그리고 §G8 의 순서(「PR 생성까지, squash 는 사용자」)는 그 전제를 **암시만** 한다.
2026-08-12 회차는 사용자 결정으로 「CI 확인 → 즉시 머지」를 반복했고, 마감 시점에 브랜치가 남지
않아 그 상태에 빠졌다. ⇒ **문서를 그대로 따르면서도 게이트가 성립하지 않는 경로가 있다.**

★★그리고 **빈 커밋으로 브랜치를 만들어 초록을 사지 않았다.** 그것이 이 레포가 반복해 밟은 거짓
그린이고, [BL-706] 회차의 「비어 있지 않은 파일 하나로 초록을 만들 수 있었지만 그러지 않았다」와
같은 자리다.

**권장 접근 (셋 중 하나 이상):**

1. **문서에 전제를 명시한다** — 「마감 게이트는 **그 회차의 마지막 PR 브랜치에서**, 머지 **전에**
   돌린다」를 §G8 과 ⓸ ④ 에 박는다. 가장 싸고 이 회차의 사고를 그대로 막는다.
2. **머지된 회차용 탈출구** — `signal-check.sh` 에 `--range <base>..<head>` 를 주면 A1 대신 그 범위로
   판정한다. 단 **범위를 사람이 고를 수 있으면 판별력이 준다** — 기본값 없이 명시 인자만 허용하고,
   범위가 비면 rc=3 으로 판정을 포기해야 한다.
3. **신호에 범위를 적게 한다** — 첫 줄을 `commit: <sha>` 에서 `range: <base>..<head>` 로 확장하고,
   게이트는 그 범위가 **원장(reflog·머지 커밋)에 실재**하는지만 본다.

★**어느 쪽이든 수용 기준에 「A1 을 무력화하지 않았음」을 넣어라** — 변이로 A1 을 지웠을 때 main 에서
빈 신호가 통과하는 것이 다시 red 로 잡혀야 한다.

**Risk:** 🟡 게이트가 안 도는 것이 아니라 **마감 증거를 남길 수 없다.** 이 회차는 구성 게이트를
전부 개별 실행해 증거를 남겼지만, 그것은 `final-gates` 한 줄이 주는 보증과 다르다.

---

## Deferred — trigger 미도래 · 의도적 부활 가능 (구 `_deferred.md` 승격, 2026-08-06)

> archive 삭제(docs 대개편)와 함께 Sprint 59 트리아주의 deferred 원장을 본 문서로 승격했다.
> 부활 = 행을 위 P 섹션으로 옮기고 `### BL-NNN` 섹션 + `**상태:**` 줄을 단다. 6-8주마다 재평가.
> ★이 표의 BL 은 섹션이 없으므로 `bl-audit.sh` 집계 대상이 아니다(의도). BL-070~075 는 2026-05-17 헤더 shortlist 에 「milestone active 승격」 표기가 함께 있다 — 실행은 여전히 trigger 대기.

| ID     | 제목                                                                                                     | Trigger                                                                                          | Est                       |
| ------ | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------- |
| BL-070 | A. 도메인 + DNS + (옵션) Cloudflare                                                                      | BL-005 self-assessment ≥7/10 + 본인 의지 second gate. A·B·C 번들 필수(개별 진행 시 재작업 2~3배) | 1-2h + 24h DNS            |
| BL-071 | B. Backend 프로덕션 배포 (Cloud Run/Railway/Render + prod Postgres/Redis + Clerk production + 보안 헤더) | 위 번들                                                                                          | 2-4h                      |
| BL-072 | C. Resend 이메일 + Waitlist 활성화                                                                       | 위 번들                                                                                          | 1-2h + 24h verify         |
| BL-073 | Twitter/X #buildinpublic 캠페인 시작                                                                     | BL-070~072 완료 후                                                                               | S (사용자 수동)           |
| BL-074 | Beta 인터뷰 3명 × 3회 (narrowest wedge 60% 검증)                                                         | BL-073 후 + 5~10명 onboarding 후                                                                 | L (사용자 수동, 9 slots)  |
| BL-075 | H2 진입 게이트 설계 (MC / Walk-Forward 우선순위)                                                         | BL-005 self-assessment ≥7/10 직후                                                                | M (3-5h)                  |
| BL-005 | 본인 실자본 1~2주 dogfood 운영                                                                           | BL-001~004 완료 + self-assessment ≥7/10 + 본인 의지 second gate                                  | L (≥14 days, 사용자 수동) |
| BL-145 | EffectiveLeverageEvaluator (Cross Margin position aggregation)                                           | Sprint 30+ Phase 2 prereq (BL-004 sibling)                                                       | M (3-4h)                  |

★★★**2026-08-08 정정 — 이 BL 이 인용한 「MTBF 8.70h · P(168h)=4.115e-09」은 혼합 추정치다.**
원인별로 층화하면 이미 고친 원인들이 섞여 있다는 것이 드러난다:

**아래는 2026-08-12 재측정본**이고 괄호가 2026-08-08 값이다(층 경계는 날짜가 아니라 **수리**라서 불변):

| 창                  | n          | 노출                | 자동사망 | MTBF                 | 95% CI          | 그 사망의 정체                           |
| ------------------- | ---------- | ------------------- | -------- | -------------------- | --------------- | ---------------------------------------- |
| 전 이력             | 40 (구 38) | 193.37h (구 107.12) | 8        | 24.17h (구 13.39)    | [12.27, 55.99]  | 혼합                                     |
| 2026-08-03 이후     | 16 (구 14) | 147.16h (구 60.91)  | 7        | 21.02h (구 **8.70**) | [10.20, 52.29]  | **혼합 — 이 BL 이 인용해 온 값**         |
| [ADR-025] 수리 이후 | 7 (구 5)   | 124.72h (구 38.47)  | 2        | 62.36h (구 19.24)    | [17.26, 514.93] | gap-resync 1 — [BL-622] 가 수리 · 오염 1 |
| [BL-622] 수리 이후  | 4 (구 2)   | 91.84h (구 5.59)    | 1        | 91.84h (구 —)        | [16.48, 3627.6] | **오염 1건뿐** — [BL-634] 미시행         |

★**각 수리 이후의 사망은 전부 「그 다음 원인」이었다.** 알려진 원인이 모두 닫힌 뒤의 **미설명 사망은
0건**이다. ★2026-08-12 정정 — 종전의 「노출이 5.59h 뿐이라 **아래에서 못 잰다**」는 낡았다:
[BL-622] 이후 노출이 **91.84h(16.4배)** 로 자랐고 그 안의 사망은 1건이다. 그래도 **CI 상한이
3627h** 라 여전히 아래에서 못 가른다 — 자란 것은 표본이지 **판별력이 아니다**.

★★**그러므로 이 BL 의 결론을 「MTBF 가 병목이다」로 단정하지 마라.** 정확한 문장은
**「현행 사망률을 아래에서 잴 표본이 아직 없다 — 층화 전 값(21.02h)은 고친 원인을 섞은 상한이다」**이다.
판정에 필요한 것은 **[BL-634] 착지 이후의 노출**이고, 그때까지 이 BL 은 **측정 대기**다.
★★★**네 층의 CI 가 2026-08-12 에도 6쌍 전부 겹친다**(운영 사고 제외 층을 넣으면 10쌍 전부).
MTBF 점추정이 13.39h → 24.17h 로 **1.8배** 올랐는데도 「올랐다」고 말할 수 없다 — 이것이 이 BL 이
CI 를 표와 같은 실행에서 내게 만든 이유다.

★부수 — **오염은 자동사망 8건 중 1건뿐**이었다(나머지 7건은 맥→오라클 이관 전이라 호스트가 하나였다).
「배타성을 고치면 MTBF 가 오른다」는 성립하지 않는다. [BL-634] 가 사는 것은 **재발 방지**다.

---

### BL-644

**Priority:** P3
**카테고리:** Frontend / 반응형 일관성
**Trigger:** 반응형 셸을 다시 손댈 때
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-08, `stage/ztb-w3-responsive`)

**JS 미디어쿼리 하나만 767px 이고 CSS 30곳은 768px 이다.**

`frontend/src/app/(dashboard)/strategies/[id]/edit/_components/delete-dialog.tsx:135` 이
`useMediaQuery("(max-width: 767px)")` 를 쓴다. 레포에서 **유일한 JS 미디어쿼리**이고, CSS 쪽
`@media (max-width: 768px)` 는 14곳 전부 768 이다.

⇒ 뷰포트가 정확히 768px 일 때 **CSS 는 모바일**(`--sidebar-w: 0`, 햄버거 노출)인데 이 훅은
`isMobile === false` 를 준다. 다이얼로그 하나의 표현 분기라 현재 피해는 작지만, 경계값이
갈린 채로 남으면 다음 사람이 어느 쪽을 믿을지 못 고른다.

**수리 방향:** 767 → 768 한 줄. `.tsx` 라 [BL-602] 무관.
**Risk:** 🟢 1픽셀. 다만 고칠 때 `md:` 유틸(=768, min-width)과 CSS(=768, max-width)가
**같은 숫자를 반대 방향으로** 쓴다는 것을 함께 확인해라.

**해결(2026-08-08).** `delete-dialog.tsx:135` 767 → 768. 이 훅이 고르는 것은 Sheet(모바일)
vs Dialog(데스크탑)이라 **셸의 모바일 판정과 같은 축**이고, 셸은 `@media (max-width: 768px)`
에서 `--sidebar-w: 0` + 햄버거로 넘어간다 ⇒ CSS 축에 맞추는 것이 옳다.

★**세 축은 768 에서 전부 일치할 수 없다.** 뷰포트 정확히 768px 에서:

| 축                            | 방향        | 768px 에서         |
| ----------------------------- | ----------- | ------------------ |
| Tailwind `md:` 유틸           | `min-width` | **적용(데스크탑)** |
| raw CSS `@media (max-width:)` | `max-width` | **적용(모바일)**   |
| `useMediaQuery` (수정 후)     | `max-width` | **모바일**         |

`min-width`·`max-width` 둘 다 경계값을 **포함**하므로 768 은 두 방향이 동시에 참인 유일한
점이다. 이번 수정은 훅을 **CSS 축**에 붙였고, 남은 `md:` ↔ CSS 겹침은 이 BL 이전부터 있던
구조적 성질이라 그대로다(정본 기술 = `frontend/AGENTS.md` §10 · `DESIGN.md` §4.3).

---

### BL-645

**Priority:** P3
**카테고리:** Frontend / 데드 CSS
**Trigger:** 백엔드 검색을 붙일 때 · CSS 정리 스윕
**Est:** XS
**상태:** ✅ **Resolved (2026-08-09, W3)** — 단 **처방 ③ 은 「가장 싸다」가 아니었다.**
CSS 정의 자리에 주석을 달면 KITPORT 무결성 가드가 빨개진다(실측) — ② 와 **똑같이**
allowlist 등재가 선행이다. 그래서 근거를 가드 밖 두 자리에 남기고 `globals.css` 규칙은
건드리지 않았다. 아래 §재판정 참조.

**`.searchbox` 는 CSS 만 있고 렌더하는 컴포넌트가 없다.**

정의 `globals.css:1159-1178`, 1024px 숨김 규칙 `:1853`. 그런데 `.searchbox` 를 렌더하는 TSX 가
`frontend/src` 전체에 **0건**이다 — `components/layout/dashboard-header.tsx:5` 가
「검색창은 백엔드 검색 기능이 없어 이식하지 않는다(가짜 UI 방지)」라고 명시한다.

★이것이 `DESIGN.md` §10.6 의 「1024px~ 검색 숨김」을 **검증 불가**로 만든 원인이다. 규칙은
KITPORT 센티넬 안에 있어 `_kit.html` 과 묶여 있으므로 지우려면 allowlist 등재가 필요하다.

**수리 방향(택1):** ① 검색 기능과 함께 살린다 ② KITPORT allowlist 에 올리고 삭제
③ 「의도적 미이식」 주석만 단다(가장 싸다).
**Risk:** 🟢 무해. 비용은 사람의 오독뿐이다.

**§재판정 (2026-08-09, W3)**

★**「어디에도 안 적혀 있다」가 틀렸다.** `DESIGN.md` §10.6 은 **이미** 「검증 불가 — 검색창이
렌더되지 않는다」를 근거(`dashboard-header.tsx:5`)와 함께 적고 있었고 이 BL 번호까지 달고
있었다. 그래서 이번에 산 것은 「없던 설명을 새로 쓴 것」이 아니다.

★**진짜 결함은 줄 번호가 낡았다는 것이었다.** 이 BL 과 `DESIGN.md` 가 함께 인용하던
`globals.css:1159-1178`·`:1853` 은 지금 파일에서 각각 `.searchbox:hover` 중간과
`@media (max-width: 1024px)` **바깥**을 가리킨다. 실측 정정 = 정의 **1146-1165** ·
1024px 숨김 **1840**. 렌더 TSX 는 재확인해도 **0건**이다(유일한 `searchbox` 히트는
`app/__tests__/not-found.test.tsx` 의 **ARIA role** 이라 이 CSS 클래스가 아니다).

★**처방 ③ 이 무료가 아님을 실측으로 확정했다.** `design-canon-kit-port.test.ts` 의
`normalize` 는 공백만 접고 **주석을 보존**한다. 정의 바로 위에 주석 한 줄을 넣자
「이식 블록은 allowlist 를 제외하면 \_kit.html 공용 블록과 정규화 동일하다」가 빨개졌다.
⇒ 다음 회차는 ③ 을 「XS 무비용」으로 잡지 마라 — ② 와 같은 선행 작업을 요구한다.

**둔 자리 2곳 (둘 다 가드 밖):** `DESIGN.md` §10.6 · `globals.css` 의 `KITPORT-START`
센티넬 머리 주석(가드가 이 주석의 `*/` **뒤**부터 대조하므로 안전 — 넣고 5/5 green 실측).
검증 = kit-port 가드 5/5 · `e2e:design-canon` 42/42 · CSS 변경은 주석 블록 1개뿐.

---

### BL-646

**Priority:** P3
**카테고리:** Frontend / 반응형 정본
**Trigger:** 반응형 정본을 다시 손댈 때
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-08, `stage/ztb-w3-responsive`)

**어느 정본에도 없는 900px 경계가 5곳 살아 있다.**

`globals.css` 의 `@media (max-width: 900px)` — `.perf-row` · `.trade-detail-metrics` ·
`.session-manage` · `.report-analysis-grid` · `.ob-panel`/`.ob-illus`. 전부 화면 전용
그리드 축소다.

`DESIGN.md` §4.3 사다리(375/768/1024/1200/1440)에도, `frontend/AGENTS.md` §10 에도,
`_kit.html` 에도 900 은 **0건**이다. 2026-08-08 문서 정렬에서 이 다섯 곳만 흡수하지 못해
「미등재 경계」로 명시하고 넘겼다.

**수리 방향(택1):** ① 정본 사다리에 900 을 추가한다 ② 다섯 곳을 1024 나 768 로 흡수한다
(시각 회귀 확인 필요).
**Risk:** 🟢 현재 동작 정상. 문제는 사다리가 사다리가 아니라는 것.

**해결(2026-08-08) = ① 등재.** 흡수 2안은 **실측으로 기각**했다(`DESIGN.md` §4.3.1 신설).

★★**전제가 틀렸다 — 이 그리드들이 받는 폭은 뷰포트가 아니라 `.page` 콘텐츠 박스이고, 그 값은
뷰포트에 대해 단조가 아니다.** `--sidebar-w` 가 1024 에서 `232 → 64` 로 계단을 밟기 때문이다.
dev 서버(3111) + Playwright 하네스 실측:

| 뷰포트         | 769 | 899 | 901 | 1023    | **1025** | 1200 |
| -------------- | --- | --- | --- | ------- | -------- | ---- |
| 콘텐츠 박스 px | 657 | 787 | 789 | **911** | **745**  | 920  |

⇒ 뷰포트가 **늘었는데**(1023 → 1025) 콘텐츠는 **166px 줄어든다**. 그래서 어떤 뷰포트 문턱을
골라도 「같은 콘텐츠 폭이 접힘·펼침 양쪽에 나타나는」 모순 구간이 남는다. 셋을 그 폭으로 비교:

| 안              | 모순 구간           | 판정                                                                                                          |
| --------------- | ------------------- | ------------------------------------------------------------------------------------------------------------- |
| ② 1024 로 흡수  | **166px** (745~911) | ❌ 콘텐츠 911 에서 1열로 접고 745 에서는 2·3열 유지 — **가장 넓을 때 접는다**                                 |
| ② 768 로 흡수   | 83px (657~740)      | ❌ **실제 파손** — 뷰포트 769(콘텐츠 657)에서 `.trade-detail-metrics` 3열이 219px 씩, `.metric` 2건 +6px 넘침 |
| ① 900 유지·등재 | **42px** (745~787)  | ✅ 셋 중 최소                                                                                                 |

768 흡수의 파손은 숫자만이 아니라 눈으로도 갈린다 — 219px 열에서 라벨 「시각」이 「시/각」으로
꺾인다(스크린샷 대조 5셀렉터 × 3변형 × 5폭 = 75장). 나머지 4셀렉터는 어느 안에서도 넘침 0건이라
**흡수 기각의 근거는 `.trade-detail-metrics` 단독**이다 — 부분 흡수도 가능하지만, 다섯 곳이
같은 이유(콘텐츠 그리드 축소)로 존재하므로 경계를 쪼개지 않고 하나로 뒀다.

★**900 은 옳은 축이 아니라 최선의 근사다.** 근본 해는 컨테이너 쿼리(그리드가 뷰포트가 아니라
자기 컨테이너를 본다)이고, 그러면 모순 구간이 0 이 된다 → [BL-647] 과 함께 다룬다.
★`frontend/AGENTS.md` §10 의 사다리 표에도 900 줄이 필요하지만 [BL-602] 로 `frontend/` 안 md 를
스테이징할 수 없어 **미반영**이다 — 별도 처리 필요.

---

### BL-647

**Priority:** P3
**카테고리:** Frontend / CSS 규약 집행
**Trigger:** CSS 규약을 집행 가능하게 만들 때
**Est:** M
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**mobile-first 규약과 코드가 정반대다.**

`frontend/AGENTS.md` §10 은 「데스크탑 기준으로 먼저 작성하는 방식 **금지**」라고 적어 왔는데,
`globals.css` 의 `@media` **30곳이 전부 `max-width`** 이고 `min-width` 는 **0건**이다.
C 이식 CSS 가 `_kit.html`(desktop-first)의 바이트 정본이라 구조적으로 그렇다.

2026-08-08 에 **규칙의 사거리를 좁혀** 봉합했다 — 신규 Tailwind 컴포넌트는 mobile-first 필수,
KITPORT·화면 전용 CSS 는 그 파일의 desktop-first 관례를 따른다. **전면 전환은 미결이다.**

★전환하려면 `_kit.html` 17벌 재검증이 따라온다(`design-canon-kit-port.test.ts` 가 바이트
대조). 비용이 크므로 「하지 않는다」도 정당한 결론이다 — 다만 **결론을 적어야** 다음 사람이
같은 모순을 다시 발견하지 않는다.
**Risk:** 🟢 동작 무관. 규약 신뢰도 문제.

---

### BL-648

**Priority:** P3
**카테고리:** Frontend / 테스트 커버리지 (캐논)
**Trigger:** 라이트 테마 회귀가 한 번 더 나올 때
**Est:** S
**상태:** 🟡 **부분 해결 — 공개 라우트 라이트 런타임 커버리지는 닫혔다. 잔여 = 인증 셸 `.sidebar` 실폭**
(2026-08-08 ztb-w2-light-canon). 처방 **②**(공개 라우트 라이트 전용 spec) 채택.
`e2e/design-canon-public-light.spec.ts` 신설 + `design-canon-audit.ts` 에 `theme` 옵션 추가.
★①(감사 컨텍스트를 테마별 2벌)은 **기각** — `design-canon-calibration.spec.ts` 는 next-themes 가
없는 **정적 프로토타입 HTML** 을 감사하고 다크 canon 카운트 17벌을 정확히 일치로 동결한다(라이트를
얹을 대상이 없다). `authed-canon-*` 는 `chromium-authed` 몫이라 소크 결합([BL-597]). ②의 위험이던
「감사 로직이 갈린다」는 코어를 복제하지 않고 옵션 하나로 매개변수화해 없앴다.
★★**`colorScheme` 만으로는 테마가 안 바뀐다**(실측) — `defaultTheme="dark"` 라 저장된 선호값이
없으면 next-themes 가 다크로 고정한다. `colorScheme:"light"` 단독 컨텍스트도 `<html class="… dark">`
· body 배경 `rgb(11, 13, 15)` 였다. localStorage `theme=light` 를 `addInitScript` 로 심어야
`class="… light"` · `rgb(244, 245, 246)` 이 된다. 그래서 `probeTheme()` 이 **매 컨텍스트마다 렌더
결과를 읽어** 도달을 확인하고 어긋나면 던진다 — 없으면 라이트 감사가 조용히 다크를 한 번 더 재고도
초록이 되는 **fail-open** 이다.
★★★**음성 대조 — 판별력 확인.** 라이트 `--warning` 을 [BL-628] 회귀값 `#824e05`→`#875206` 으로
주입(치환 문자열 `^  --warning: #824e05;$` 는 파일 내 **유일**. 같은 hex 가 `--accent-amber` ·
`brand-palette.ts` 에도 있어 앵커 없이 치환하면 3곳이 함께 바뀐다). 주입이 dev 서버에 **도달했는지**
먼저 확인(배너 `rgb(130,78,5)`→`rgb(135,82,6)`, 배경 `rgb(247,239,220)` 불변) 후 실행 ⇒ 새 spec
**5/5 red**(canon 2→18 · 6→16 · 14→24 · 4→16 · 2→12). ★**같은 실행에서 기존 다크 spec 은 5/5 초록**
— 이 회귀는 AA(4.5)를 통과하고 캐논(5.82)만 미달이라 하드 실패 게이트로는 **원리상 안 잡힌다**.
구멍이 실재했다는 대조군이다. 복원은 직접 역치환 후 sha256 일치 확인
(`ec7f1a10…9fa7c5`). 게이트: `pnpm test` 1292/1292 · `e2e:design-canon` 36→**42 passed**(34.1→50.8s).
★★**범위가 spec 을 넘었다 — 왜, 그리고 기존 4 spec 에 무엇이 닿았나**(2026-08-08 zero-touch-bundle
`/code-review` 기록). spec 은 「테마별 2벌 또는 라이트 전용 spec」이었는데, 실제 착지물에는
`NavProbe(status/examined)` · `auditStatuses()` · `minExamined()` · `worstCanonRatio()` 가 **감사 코어**에
함께 들어갔다. 근거는 codex 평가가 잡은 **fail-open** — `auditUrl` 이 `page.goto()` **반환값을 버려서**
404·빈 DOM 도 `hardFail=0 · canon=0` 으로 초록이었다(라이트 spec 만 세우면 그 spec 자신이 그 구멍 위에
서게 된다). 그래서 spec 밖이지만 정당하다. **영향 범위:** 코어를 쓰는 기존 4 spec(calibration · public ·
authed-canon-p1 · authed-canon-remaining)은 `hardFailCount()` 와 `formatCanonResult()` **둘만** 쓰고 결과
객체를 구조 비교하지 않는다 ⇒ 바뀐 것은 **로그에 `reached:` 한 줄이 붙은 것**뿐이고 판정은 불변이다
(`theme` 을 안 주면 `newAuditContext` 는 종전과 동일 경로). **무손상 실증**: `e2e:design-canon` 이 calibration ·
public 을 매 회 다시 돌려 초록을 확인한다. `authed-canon-*` 2벌은 `chromium-authed` 라 소크 결합([BL-597])
이어서 이번 게이트 범위 밖이다 — 그쪽은 **구조 논거로만** 무손상이고 실행으로는 미확인이다.
★라이트 canon 잔량(2/6/14/4/2)은 전부 `--text-muted`(#585f68)가 `--card`/`--bg` **아닌** 표면에서
5.60~5.64 인 것이다. 이 조합은 `light-canon-contrast.test.ts` 의 PAIRS 에 **없어 계산으로는 안 보인다**
— 실화면 합성이 무엇을 더 잡는지의 실례. 토큰 이동은 별건이라 래칫으로 동결만 했다.
**트리거 판정:** 미도래 — 외생 조건(라이트 테마 회귀 재발). 잔여인 인증 셸 `.sidebar` 실폭은 `chromium-authed` 몫이라 [BL-597] 소크 결합에도 걸리고, 2026-08-11 현재 `E2E_CLERK_*` 가 비어 authed 경로 자체가 안 돈다 (2026-08-11 bl-703-partial-verdicts)

**런타임 캐논 감사가 다크 테마만 잰다.**

`e2e/design-canon-audit.ts:300` 의 `browser.newContext` 는 `colorScheme` 을 강제하지 않고,
`components/providers/app-providers.tsx:21` 이 `defaultTheme="dark"` 다. 그래서
`CANON_WIDTHS` 4폭 감사가 **전부 다크에서** 돈다.

⇒ 라이트 라우트의 대비/캐논을 재는 e2e 가 **하나도 없다.** [BL-628] 이 등재만 되고 어떤
게이트도 물지 않은 채 배포돼 있던 이유이고, 그 앞에는 라이트 AA 하드 실패 **116건**이
같은 구멍으로 나갔다.

2026-08-08 에 `src/__tests__/light-canon-contrast.test.ts` 를 세워 **커밋된 토큰값의 대비**는
막았다. 남은 것은 **실화면 합성**이다 — 알파 표면(`rgba` subtle)·중첩 레이어·Clerk 위젯 같은
것은 계산으로 못 잰다.

★두 번째 구멍: **인증 셸에서 실제로 렌더된 `.sidebar` 폭**도 아무도 안 잰다.
`e2e/design-canon-responsive.spec.ts` 는 공개 라우트에 `.sidebar` 가 없어 **주입 프로브**로
대신했다. 진짜 셸 측정은 `chromium-authed` 몫이고 그쪽은 소크 상태에 결합된다([BL-597]).

~~**수리 방향:** 감사 컨텍스트를 테마별 2벌로 돌리거나(`emulateMedia` + `.dark` 클래스 제거),
공개 라우트 라이트 전용 spec 을 하나 더 세운다.~~ → **2026-08-08 ② 로 닫았다**(위 상태 줄).
**잔여 수리 방향:** 인증 셸 `.sidebar` 실폭 측정만 남았다 — `chromium-authed` 몫이라 소크 결합.
**Risk:** 🟡 라이트는 보조 테마지만 마케팅·법무 라우트가 전부 거기다.

---

### BL-649

**Priority:** P3
**카테고리:** Frontend / 데드 토큰
**Trigger:** 토큰 정리 스윕
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-08, `stage/ztb-w3-responsive`)

**소비자가 없는 토큰이 두 묶음 남았다.**

- `--accent-amber` / `--accent-amber-light` — `@theme inline` 이 유틸로 노출하지만 TSX
  소비 **0건**. 라이트에서는 `--warning` / `--warning-subtle` 과 값이 같고(2026-08-08
  [BL-628] 때 함께 옮겼다), 다크에서는 `-light` 가 0.12 인데 `--warning-subtle` 은 0.10 으로
  **이미 갈렸다** — 같은 값을 두 이름으로 들고 있으면 반드시 갈린다는 실례.
- `--chart-1..5` — shadcn 카테고리 슬롯. `--color-chart-N` 유틸 사용 **0건**. 그리고
  `--chart-4` 는 구 `--warning`(`#875206`) 사본이라 [BL-628] 이후 **드리프트한 복사본**이다.

[BL-629] 가 `--chart-*` 데드 7종을 지울 때 이 둘은 **별개 묶음**이라 범위 밖으로 뒀다.

**수리 방향(택1):** ① 삭제 ② `--accent-amber` 를 `var(--warning)` 별칭으로 강등해 드리프트
불가하게 만든다. ②가 이름을 살리면서 갈라짐을 막는다.
**Risk:** 🟢 소비자 0건.

**해결(2026-08-08) = ① 삭제**(12줄, 라이트/다크/`@theme inline` 3면 전부).

②(별칭 강등)를 고르지 않은 이유 — **별칭도 이름이고, 이름은 소비자가 있을 때만 값을 한다.**
소비 0건에서 `--accent-amber: var(--warning)` 을 남기면 드리프트는 막히지만 `@theme inline` 이
계속 유틸(`bg-accent-amber` 등)을 찍어내 **다음 사람이 둘 중 무엇을 쓸지 다시 고민한다.**
앰버가 필요하면 `--warning`/`--warning-subtle` 하나뿐이어야 한다.

**착수 전 재확인한 소비 실측**(백로그 숫자를 그대로 믿지 않고 현재 파일 기준으로 다시 셌다):

| 심볼                        | 선언                                                 | TSX/e2e 소비 |
| --------------------------- | ---------------------------------------------------- | ------------ |
| `--accent-amber` / `-light` | `:root` 2 · `.dark` 2 · `@theme inline` 2 = **6줄**  | **0건**      |
| `--chart-1..5`              | `:root` 5 · `.dark` 5 · `@theme inline` 5 = **15줄** | **0건**      |

★백로그 기술과 **다른 점 1건** — `--chart-1..5` 는 「소비 0건」이지만 **참조는 0건이 아니었다.**
`__tests__/chart-tokens-contract.test.ts` 의 [BL-629] 역방향 래칫 `CHART_VARS_FROZEN` 이 다섯을
**동결 목록에 넣어 잠그고** 있었다(그 주석이 「처분은 [BL-649]」라고 스스로 지목). 삭제하려면
그 목록부터 고쳐야 했고, 안 고쳤으면 집합 동등 단언이 red 가 된다 — 래칫이 **설계대로 물었다**.

부수: `disclaimer/page.tsx:1` · `_components/legal-callout.tsx:1` 의 주석이 `accent-amber` 를
이름으로 부르고 있었다(실제 구현은 이미 `border-warning bg-warning-subtle text-warning`). 삭제로
**댕글링이 되므로** 두 줄만 `warning` 으로 고쳤다.

**검증:** `pnpm test` 209 files / 1292 tests green · `e2e:design-canon` 36 passed
(`design-canon-tailwind-utilities` · `design-canon-runtime` 포함 — `@theme inline` 경로가
살아 있음을 런타임에서 확인). 삭제 후 `--color-chart-` · `accent-amber` grep = 툼스톤 주석 외 0건.

---

### BL-650

**Priority:** P2
**카테고리:** DX / 빌드 캐시
**Trigger:** dev 서버가 느려지거나 CSS 변경이 안 먹을 때 · 캐시 정책을 정할 때
**Est:** S
**상태:** 🟡 **부분 해결 — 부수(디스크 8.5GB)는 닫혔고 관측 장치를 걸었다. 정책은 미정이다**
(2026-08-08 soak-window-and-gate-attribution). ⑴ 낡은 빌드 디렉터리를 지웠다 — **4벌이 아니라
5벌**이고 합계 **8.5GB** 였다(`.next.stale-fp-20260723` **5.8G** · `.next.bak-turbocache` **2.0G** ·
나머지 3벌 117M). 레포 26G → **18G**. ⑵ `make fe` 가 `.next` 크기를 재서 1GB 초과 시 경고한다
(양성/음성 대조 2/2). **닫는 조건은 불변** — 「몇 GB에서 태우기 시작하나」를 재야 정책이 선다.
**트리거 판정:** 미도래 — 앞절은 이 회차에 관측되지 않았고(dev 서버 미기동) 뒷절 「캐시 정책을 정할 때」는 동승이다. ★단 `frontend/.next` 는 2026-08-11 실측 **1.2GB** 로 `make fe` 경고선 1GB 를 이미 넘겼다 — 닫는 조건인 「몇 GB에서 태우기 시작하나」는 여전히 두 점(1.99GB 사망 · 593MB 무해)뿐이다 (2026-08-11 bl-703-partial-verdicts)

★★★**재현에 실패했고 그것이 이 회차의 결과다.** 593MB 캐시에 요청 1건을 먹인 뒤 재니
**idle CPU 0.1% · `/` 0.61초 · RSS 945MB** 였다 — 아래 표의 `rm -rf` 후 값과 같다. 즉 증상은
**크기 단조가 아니다**(RSS 는 이미 945MB 인데 CPU 는 0.1%). 1.99GB 를 만들려면 며칠의 개발이
필요하므로 **문턱은 이 회차에서 아래로부터 잴 수 없었다.** `make fe` 경고선 1GB 는 그래서
**정책이 아니라 관측 장치**이고, 근거는 두 점(1.99GB 사망 · 593MB 무해)뿐이다 — 인용 금지.

★★**수리 방향 ①은 실행 불가다 — `turbopackMemoryLimit` 은 존재하지 않는다.** Next 가
`experimental.turbo.memoryLimit` 과 `experimental.turbopackMemoryLimit` 을 **둘 다 제거**했고
대체 옵션이 없다(codemod `next-experimental-turbo-to-turbopack` 이 「no longer supported,
removed entirely」라고 명시). 실재하는 손잡이는 **둘뿐**이다:
`experimental.turbopackFileSystemCacheForDev`(dev 기본 **켜짐** — 끄면 재기동이 느려진다,
그게 이 캐시의 존재 이유다) · `turbopackMemoryEviction: false | 'full' | 'auto'`(기본 `'auto'`,
스냅샷 뒤 메모리 회수). ⇒ **①을 「상한을 건다」로 적은 원안은 폐기하고 위 둘로 교체한다.**

★**왜 8.5GB 가 아무 눈에도 안 띄었나 — `frontend/.gitignore:3` 이 `.next*/` 를 무시한다.**
git status 에 영원히 안 나오고, 백로그의 「4벌」도 개수만 적고 크기를 안 쟀다.

★**측정 도구가 또 틀렸다** — `pgrep -f "next dev"` 는 **부모 래퍼**를 준다(RSS 71MB · CPU 0.18s).
실제 서버는 그 자식이고 판별자는 **`lsof -nP -iTCP:<port> -sTCP:LISTEN -t`** 다. 부모로 재면
「CPU 0%」가 나오는데 그건 서버가 조용한 게 아니라 **엉뚱한 프로세스를 본 것**이다.

**Turbopack 영속 캐시가 무한히 자라고, 자란 뒤에는 CPU 를 상시로 태우며 낡은 산출물을 준다.**

2026-08-08 fe-canon-and-responsive 회차에서 실측했다. 증상은 셋인데 원인은 하나다.

| 관측                                                | 캐시 1.99GB   | `rm -rf .next` 후 |
| --------------------------------------------------- | ------------- | ----------------- |
| `next dev` idle CPU (**요청 0건 · 클라이언트 0개**) | **416.9%**    | **0.1%**          |
| RSS                                                 | 1000MB        | 374MB             |
| `/` 첫 응답                                         | 120s 타임아웃 | 2.9s              |
| `/maintenance`                                      | 120s 타임아웃 | 0.42s             |

★★그 상태가 **fork 고갈**(`resource temporarily unavailable`)로 번져 Bash·playwright·
dev 서버가 함께 죽었고, 머신이 두 번 다운됐다. 처음에는 **React 렌더 루프**로 의심했으나
클라이언트가 0개라 성립하지 않았고, 랜딩 트리의 `useEffect`/rAF/interval 도 **0건**이었다.

★★★**두 번째 증상이 더 위험하다** — 변이한 CSS 가 **dev 서버 완전 재기동을 넘어** 낡은 채로
서빙됐다. `globals.css` 의 `.pos`/`.neg` 규칙을 지우고 e2e 를 돌렸는데 **통과**했고, 그것이
「오라클에 판별력이 없다」로 오독될 뻔했다. `rm -rf .next` 로만 풀렸다. 이 파일의 `r<n>`
캐시 무효화 주석이 경고하던 함정의 **더 강한 형태**다.

★측정 도구 주의 — macOS `ps -o pcpu` 는 **수명 평균**이라 「지금 도는가」를 못 가른다.
`ps -o time` 을 두 번 떠 벽시계로 나눠라(실측 433.6% vs 수명평균 435.5%).

~~★부수 — `frontend/` 에 낡은 빌드 디렉터리가 **4벌** 방치돼 있다.~~ ★**2026-08-08 정정 —
5벌이었고 합계 8.5GB 였다. 지웠다**(위 상태 줄).

**수리 방향(택1, 조사 필요) — 2026-08-08 개정:** ~~① 캐시 상한(`turbopackMemoryLimit`)~~
**①′ 정기 청소를 정책으로**(상한 옵션은 Next 에 **없다**, 위 참조) ② `next.config.ts` 에서
`experimental.turbopackFileSystemCacheForDev: false` — 증상은 구조적으로 사라지지만 **재기동이
느려진다** ②′ `turbopackMemoryEviction: 'full'` — RSS 945MB 실측에 겨눈다, 단 **CPU 증상에
듣는지는 미검증** ③ Next 업스트림 이슈인지 확인한다 — 2GB 까지 자라는 것 자체가 정상인지
판정이 없다.
★**정책을 정하기 전엔 「dev 가 이상하면 `rm -rf .next` 부터」가 유일한 처방이다.**
★★**어느 것도 근거 없이 켜지 않는다** — 문턱을 모르는 상태에서 손잡이를 돌리면 「고쳤다」와
「원래 안 났다」를 구분할 수 없다(593MB 재측정이 정확히 그 상태다).
**Risk:** 🟠 개발을 실제로 멈춰 세웠다. 프로덕션 무관(빌드 산출물).

---

### BL-651

**Priority:** P2
**카테고리:** Trading / 계정 배타성 판정 (계상 오염)
**Trigger:** BL-634 가드가 `RESTING_CONDITIONAL`·`FOREIGN_RESTING` 을 **개수**로 쓰기 전
**Est:** S
**상태:** ✅ **Resolved** (2026-08-09 excl) — `live_session_admin._cmd_status` 의 거래소 조회 루프가 `exchange_uid` 로 접힌다([BL-605](#bl-605) 와 **같은 헬퍼**, 다른 루프). raw SQL 을 걷어내고 `ExchangeAccountRepository.list_by_exchange(bybit)` 로 바꿔 `exchange_uid`·`read_only` 를 얻는다 (Repository 밖 DB 접근 금지 규칙에도 맞다). 회귀 = `tests/trading/test_live_session_admin_status.py` 3건 — **수리 전 red 를 되돌려 실증**했고 그 출력이 CONTROL 실측을 그대로 재현했다(`RESTING_CONDITIONAL=2`, `FOREIGN` 줄 2개 → 수리 후 1/1). ★음성 대조 포함 — 원장이 소유를 주장 못 하는 resting 은 dedup 후에도 `EXCLUSIVE=NO` 로 잡힌다(판별력 불변)

**중복 계정 행이 배타성 판정식의 개수를 2배로 부풀린다.**

**실측 (2026-08-08, 서버 소크 진행 중 · `live_session_admin.py status --symbol BTC/USDT`):**

```
거래소 포지션 (BTC/USDT):
  bybit demo: long 0.029
  bybit demo- aaa: long 0.029          ← 같은 실제 계정을 두 번 봤다
미체결 조건부 주문 (BTC/USDT):
  bybit demo:      sell other qty=0.058 trigger=64879.9 link=dd58ef44… [ours]
  bybit demo- aaa: sell other qty=0.058 trigger=64879.9 link=dd58ef44… [ours]
RESTING_CONDITIONAL=2      ← 실제 조건부 주문은 1건이다
FOREIGN_RESTING=0
EXCLUSIVE=YES
```

`_cmd_status`(`backend/scripts/live_session_admin.py:206-234`)가 계정 **행**마다
`fetch_open_conditional_orders` 를 부르는데, `exchange_uid` **558689281** 을 공유하는 계정 행이
2개라 같은 주문이 두 번 계상된다([BL-517](#bl-517) · [BL-605](#bl-605) 와 **같은 축 오류**).
포지션 출력도 같은 이유로 2행이다.

**지금 당장 깨지는 것은 없다** — `EXCLUSIVE` 는 `FOREIGN_RESTING != 0` 이라는 **존재 판정**이라
배수에 불변이고, `QUIET` 도 `resting_total` 의 0/비0만 본다. 깨지는 것은 **개수를 문턱으로 쓰는
순간**이다(예: 「resting 이 N건 넘으면 거부」, 「포지션 수량 합계」).

★[BL-605] 의 처방(스윕 루프 `exchange_uid` dedup)은 **이 자리를 안 고친다** — 축이 다르다.
여기는 **거래소 조회 루프**다. 두 자리를 같은 관용구(`list_by_exchange_uid` 로 대표 1행 선택)로
고치되 커밋을 나눠야 회귀 시 어느 축인지 갈린다.

**수리 방향:** ① 조회 루프에서 `exchange_uid` 대표 1행만 조회 ② 근본은 중복 계정 행 정리
([BL-517]) — `0277c150` 은 `read_only=t` 이고 세션 1건·주문 2건이 달려 있어 FK RESTRICT 라
soft-delete 또는 재귀속이 선행이다.

**Risk:** 🟡 판정(존재)은 지금 정확하다. 개수를 신뢰하면 그 순간 틀린다.

---

### BL-652

**Priority:** P3
**카테고리:** Backend / 테스트 인프라 (cold CI import·bytecode 비용)
**Trigger:** [BL-598] ② (파싱 디스크 캐시)를 착수할 때 · CI 샤드 수를 늘리려 할 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 선행 BL-598=ACTIVE (2026-08-10 bl-trigger-triage)

**[BL-598] 이 재고 결론 낸 것은 전부 `warm` 프로세스다. cold 축은 아직 아무도 안 쟀다.**

`backend/scripts/profile_corpus_parse.py` 의 `section_import` 은 **첫 서브프로세스를 의도적으로
버린다** — 그 첫 회가 **17초**이고 안에 bytecode(`.pyc`) 컴파일 + OS 파일 캐시 워밍이 섞여
있어서다. 버린 뒤 3회를 재서 나온 값이 **0.26s** 이고, [BL-598] 은 그것으로 가설 (a)(import
워밍업)를 기각했다. 그 기각은 **[BL-598] 이 정의한 현상**(같은 머신·warm 프로세스에서
`test_ast_classifier[i3_drfx]` 단독 42.66s vs 스위트 안 4.58s)에 대해서는 옳다.

**옳지 않은 것은 일반화다.** CI 러너는 매 잡이 **cold** 다 — `.pyc` 도, OS 파일 캐시도, 그리고
샤드를 나누면 **샤드마다** 없다. 버려진 17초가 CI 에서 샤드 수만큼 반복되는지는
**측정된 적이 없다.** 3샤드면 그것만으로 최악 51초이고, 샤드를 더 쪼갤수록 커진다.
[BL-598] 의 처방(파싱 결과 디스크 캐시)은 **파싱 비용만** 지우고 이 축은 그대로 남긴다 —
import 와 bytecode 컴파일은 캐시 히트여도 일어난다.

**재는 법:** ⑴ `__pycache__` 를 지우고 `_IMPORT_CHILD` 를 **첫 회부터** 기록하는 모드를
프로파일러에 추가(현재는 버린다) ⑵ CI 에서 잡별 `python -X importtime` 상위 항목 수집
⑶ `uv` 캐시·`__pycache__` 를 actions/cache 로 나르는 것이 이 17초를 지우는지 대조.

★**착수 전 확인할 것** — GitHub Actions 러너가 `.pyc` 를 잡 사이에 나르는지는 캐시 설정에
달렸다. 「cold 다」를 가정하지 말고 **런 로그로 확인부터** 해라([BL-598] 이 정확히 반대 방향의
가정으로 물린 자리다).

**Risk:** 🟢 CI 시간 문제이고 프로덕션과 무관. 단 [BL-598] ② 를 끝내고도 CI 가 기대만큼 안
줄면 **원인 후보가 여기밖에 안 남는다** — 그때 이 항목이 없으면 처음부터 다시 잰다.

**연결:** [BL-598](#bl-598) (모집단은 같고 온도가 다르다)

**출처:** 2026-08-08 zero-touch-bundle (codex challenge F3 — cold 표본을 버린 것이 결론의 사거리를 좁힌다)

---

### BL-653

**Priority:** P2
**카테고리:** 운영 / BL-003 게이트 (판정 해상도)
**Trigger:** [BL-619] 재관측 시 / 게이트 실격 판정을 신뢰해야 할 때
**Est:** S
**상태:** ✅ Resolved (2026-08-09, W1)

**게이트의 `tick_stall` 판정이 재려는 신호보다 거친 표본 위에서 돈다 — 방향은 fail-open 이다.**

`backend/scripts/soak_gate_predicate.py:288-350` 의 `_tick_stalls` 는 입력 둘을 쓴다:
① `.soak/gate-samples.jsonl` 의 `last_evaluated_bar_time` 동결 ② 세션 종단 lag.
2026-08-08 실측(서버 표본 125건, `2026-08-07T09:10Z`~`2026-08-08T17:50Z`) ①의 **표본 간격이
중앙 13.9분 · 최대 31.0분**이다. 그런데 [BL-619] 가 쫓는 정지는 **~17분**이다 — **판정 대상과
표본 해상도가 같은 자릿수**다.

★**그래서 크기를 못 잰다.** 같은 창에서 「`last_evaluated_bar_time` 10분 이상 정체」가 35구간
관측됐는데 그중 다수의 값이 **31.0분 = 표본 최대 간격과 정확히 일치**한다. 정지의 크기인지
관측 공백의 크기인지 이 표본으로는 **구분되지 않는다**. 적합은 검증이 아니다.

★**대조군이 판별력의 존재를 보여준다.** 같은 창을 워커 로그(`.soak/logs/worker-follow.log`,
60초 해상도)로 재면 `live_signal.evaluate_all` 디스패치 **919건 · 간격 최소=중앙=최대 60.0초 ·
2분 이상 공백 0건**으로 **깨끗하게 갈린다**. 즉 문제는 현상이 아니라 **표본**이다.

★**fail-open 인 이유** — 표본이 성기면 정체를 못 보고, 못 보면 실격을 **안 낸다**. 게이트가
관대해지는 쪽이다. 이 레포는 「게이트를 관대하게 만드는 경로」로 여러 번 물렸다.

**처방 후보 (고르는 것은 사용자다):**

- ⑴ 표본 주기를 신호보다 촘촘하게(최소 2배 오버샘플). 가장 싸지만 파일이 커진다.
- ⑵ 판정 축을 로그/DB(`live_signal_states` 쓰기 시각)로 옮긴다. 정확하지만 게이트가 로그에 결합된다.
- ⑶ 표본 간격을 판정 결과에 **함께 기록**해 「구분 불가」를 표현 가능하게 만든다 —
  판정을 바꾸지 않고 **거짓 확신만 제거**한다.

**Risk:** 🟡 실격 미계상(fail-open). C3 「실격 0」이 「정지가 없었다」를 뜻하지 않을 수 있다.

**연결:** [BL-619](#bl-619) (이 해상도 문제 때문에 그 BL 의 두 번째 축을 못 닫았다)

**출처:** 2026-08-08 soak-mortality-repair (BL-619 재관측 중 측정 도구 자신이 반증됐다)

---

**해결 (2026-08-09, W1 — 처방 ⑶. 판정을 바꾸지 않고 거짓 확신만 뺐다):**

- **red:** 판정 출력에 표본 간격 언급 **0건**. `_tick_stalls` ①이 내던 문장은
  `39731d57 bar time 정지 11:00:00~11:31:00` — **크기도 없고 무엇으로 쟀는지도 없다**.
- **green:** 같은 입력(BL 실측 재현 — 표본 간격 31.0분, 동결 lag 35.0분)에
  `… 11:00:00~11:31:00 lag 35.0분 (표본 간격 중앙 31.0분/최대 31.0분 · 크기 1.1배, 구분 불가)`.
  실격이 0건인 실행도 C4 아래에 `표본 해상도: N건 · 간격 중앙 …/최대 … (이보다 짧은 tick 정체는 판별 불가)`
  를 낸다 — ★**「C3 실격 0」을 「정지가 없었다」로 못 읽게 하는 것이 이 축의 요점이다.**
- **「구분 불가」 정의:** 크기 < 표본 최대 간격 × **2**. 정체를 가로지르는 표본이 두 개도 안 되면
  보고된 크기는 하한이고 **관측 격자의 크기**일 뿐이다(BL 본문 실측 「31.0분 = 표본 최대 간격」이 그 경우다).
- ★★★**②(종단 lag)에는 붙이지 않았다 — 이게 이 수리의 핵심 판단이다.** ②는
  `deactivated_at` × `last_evaluated_bar_time` 로 **둘 다 DB 값**이라 표본 해상도와 무관하다.
  전건에 붙이면 정확한 값까지 「구분 불가」로 깎여 표시 자체가 무의미해진다(= 새로운 fail-open 의 거울상).
  BL 본문이 「입력 둘」이라 적었지만 해상도 문제는 **①에만** 있다.
- **변이 M — 4/4 판별력.**
  ⑴ 성긴 픽스처(간격 31.0분, 크기 35.0분) → 「구분 불가」 **뜬다**
  ⑵ 촘촘한 픽스처(간격 60초, 같은 크기 35.0분 = 35.0배) → **안 뜬다**
  (⑴만 두면 항진명제다 — ①의 span 은 정의상 항상 한 표본 간격이라 아무 표시나 붙는다)
  ⑶ 문턱을 `ratio < 0.0`(절대 안 붙임) 으로 변이 → ⑴이 red
  ⑷ 문턱을 `ratio < 1e9`(전건 붙임) 으로 변이 → ⑵가 red · 주석 자체를 no-op 으로 변이 → ⑴⑵ 둘 다 red
  (★변이가 **도달했는지 grep 으로 따로 확인**했다 — `backend/AGENTS.md` §10 판별 절차)
- **음성 대조 N — 판정 불변.** 실제 게이트 출력 red vs green 을 신규 줄만 빼고 `diff` → **공집합**.
  C1~C5 6비트 · C3 실격 **0건** · 전 이력 실격 **9건** · 귀속(코드 결함 7 · 운영 0 · 미판정 2) 전부 동일.
  귀속 매칭 키가 `(at, kind)` 라 `detail` 문자열을 늘려도 분류가 흔들리지 않는다(`:496` 주석이 근거).
- **테스트 5건 추가** (`tests/scripts/test_soak_gate_predicate.py`) — 위 ⑴⑵ + ② 음성 대조 +
  실격 0건 실행의 해상도 보고 + 표본 0건이면 키를 안 넣는다(바이트 동일 규율). 전체 스위트 **4512 passed**.
- ★**이 워크트리 로컬 표본은 0건**이라 셸 출력 경로는 `.soak/gate-samples.jsonl` 을 2행(간격 31.0분)으로
  **임시 주입해 실증**하고 제거했다 — 순수 함수만 재면 「그것을 쓰는 경로」가 미검증으로 남는다(§10 규약 2).

---

### BL-654

**Priority:** P2
**카테고리:** Backend / backtest engine (모델 충실도)
**Trigger:** 고레버리지 백테스트를 신뢰해야 할 때 / [BL-466] 후속
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**증거금 게이트가 진입 비용을 판정에 넣지 않는다.** `backend/src/strategy/pine_v2/strategy_state.py`
의 `_open_trade` 최종 검증(`available = gate_equity - Σ margin_used`)과 `_can_afford_entry` 가
**둘 다 초기 증거금만** 비교하고, **바로 아래에서 차감하는 진입 leg 비용**을 가용 자본에서 빼지 않는다.

**갈리는 수치 (codex challenge 제시 · 코드 대조 완료):** 자본 $1,000 · 125x · 비용률 0.069% ·
명목 $118,750 ⇒ 증거금 $950 으로 **통과**한다(버퍼 95% 한도에 정확히 닿는다). 그런데 진입 수수료
$81.94 를 차감하면 `gate_equity` 가 **$918.06** 이 되어 **유지 중인 증거금 $950 보다 작다** —
실제 잔고로는 낼 수 없는 주문이 백테스트에서 허용된다.

★**[BL-460] 이 고친 것과 다른 축이다.** BL-460 은 **gross(`running_equity`) → net(`gate_equity`)**
축이었고 이 회차에 닫혔다. 여기는 **「증거금」 대 「증거금 + 진입 비용」** 축이고 **선재**다 —
이 회차가 만든 회귀가 아니다.

★**착수 시 확인할 것:** 이 수리는 **진입 거절을 늘린다** ⇒ golden baseline 이 움직일 수 있다.
[BL-466] (c)안이 산 「baseline 무변경」과 충돌하는지 먼저 재고, 움직인다면 그것이 **의도된 정정**임을
golden 갱신 커밋에 적어라.

**Risk:** 🟡 저레버리지에서는 버퍼가 흡수한다 — 갈리는 것은 버퍼 한도에 닿는 고레버리지뿐이다.

**연결:** [BL-460](#bl-460) (같은 함수, 다른 축) · [BL-466](#bl-466) (golden 무변경 계약)

**출처:** 2026-08-08 soak-mortality-repair (codex challenge P1 — 코드 대조로 수치 재현 확인)

---

### BL-655

**Priority:** P2
**카테고리:** Backend / trading (계정 축)
**Trigger:** 같은 `exchange_uid` 에 **쓰기 가능한** 행이 2개 생기면 / 실자금 전환 전
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 외생 조건(실자금 cutover). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)

**계정 dedup 이 쓰기 가능한 형제 행 둘을 만나면 주문을 누락한다.**
[BL-605] 수리는 `dedupe_accounts_by_exchange_uid`(`backend/src/trading/account_identity.py`)로
`exchange_uid` 당 **대표 1행**만 스윕한다. 그런데 스윕은 그 뒤로 대표 `account.id` **하나로만**
매칭·backfill 한다(`backend/src/tasks/trading.py:1949` · `:1987` · `:2027`). 버려진 형제 행에 달린
주문의 청산은 대표 계정에서 `unknown` 으로 기록되고 그 `Order.realized_pnl` 은 동기화되지 않는다.

★**현재 데이터에서는 발화하지 않는다 — 그래서 P2 다.** 실측(2026-08-08) `exchange_uid`
**558689281** 형제 2행 중 `0277c150` 이 **`read_only=t`** 이고, 대표 선택 규칙 ⑵ 가 `read_only` 행을
대표로 뽑지 않으므로 쓰기 가능한 `19a8166a` 가 대표가 된다. 주문은 쓰기 가능한 행에만 달리므로
누락이 없다. ★**위험의 실체는 「그 배치를 막는 DB 제약이 없다」** 는 것이다.

**처방 후보:** ⑴ 거래소 **조회**만 uid 당 1회로 접고 **매칭·backfill 은 형제 계정 ID 전량**에
적용한다(가장 곧다 — [BL-634] 소유권 집합이 이미 「형제 행 전량」을 쓰므로 **두 축이 일관돼진다**)
⑵ 주문을 canonical 계정으로 통일한다(이관 필요) ⑶ 쓰기 가능한 형제 2행을 **DB 제약으로 금지**한다.

**Risk:** 🟡 잠복. 발화하면 손익이 조용히 미동기화된다(원장 구멍 계측을 다시 흔든다).

**연결:** [BL-605](#bl-605) (이 dedup 을 도입한 수리) · [BL-634](#bl-634) (계정 축을 형제 전량으로
정한 결정 — 스윕이 그것과 어긋나 있다) · [BL-592](#bl-592) (형제 행 오라벨의 원 관측)

**출처:** 2026-08-08 soak-mortality-repair (codex challenge P2 — 전제는 현재 미성립, 코드 경로는 실재)

---

### BL-656

**Priority:** P2
**카테고리:** 운영 / 소크 재기동 도구
**Trigger:** 다음 소크 재기동 시
**Est:** S
**상태:** ✅ Resolved (2026-08-09, W1)

**`scripts/soak-restart.sh` 가 「완전 down 에서 올리기」를 못 다룬다 — 그리고 dry-run 이 자기 문장을 실행했다.**

2026-08-08 soak-mortality-repair 의 P7 에서 둘 다 실측했다.

★**결함 ① — dry-run 이 명령 치환을 했다(수리 완료).** `cat << EOF` 가 **unquoted heredoc** 이라
설명문 안의 백틱이 명령으로 실행됐다: `soak-restart.sh: line 214: countable: command not found`.
⑻ 설명이 그 자리만큼 **잘린 채** 출력됐다 — 읽는 사람은 문장이 깨진 줄 모른다. 같은 heredoc 이
`${ROOT}`·`${SYMBOL}` 확장을 쓰므로 `<< 'EOF'` 로 못 바꾼다 ⇒ 백틱을 제거했다. 회귀 방지로
「unquoted heredoc 안에 백틱·`$(` 가 없다」를 정적으로 셌다(현재 **0건**).

★**결함 ② — 순서 전제가 뒤집혀 있다(미수리).** 이 스크립트는 ⑴ 에서 `status` 로 FLAT 을 보는데
그것이 **DB 를 읽는다.** 스택이 내려가 있으면 DB 컨테이너도 없어 `ConnectionRefusedError` 로 끝난다.
그런데 ⑷ 는 `down → pin → up` 이라 **이미 돌고 있는 스택**을 전제한다. ⇒ 「완전 down 에서 올리기」는
이 스크립트로 **불가능**하다. P7 에서 손으로 밟은 순서가 정본이다:

```
soak-stack.sh pin → soak-stack.sh up → live_session_admin.py status(FLAT 확인)
  → (FLAT=NO 면) stop → flatten → start → soak-observe.sh --baseline → soak-gate.sh
```

★**stop 이 flatten 보다 먼저인 것이 실측으로 갈렸다.** P0 에서는 세션이 살아 있는 채 flatten 만
했더니 **엔진이 다음 tick 에 재무장**해 `EXCLUSIVE=NO` · `FOREIGN_RESTING=2` 가 됐다. P7 에서
`stop → flatten` 순으로 하니 `FLAT=YES · RESTING_CONDITIONAL=0 · QUIET=YES` 로 깨끗했다.
스크립트 ⑵ 의 「순서가 중요하다」는 경고가 **옳았고, 그것을 어긴 것은 사람이었다.**

**처방 후보:** ⑴ `soak-stack.sh ps` 류로 스택 생존을 먼저 보고, down 이면 `pin → up` 을 **스스로**
선행한다(가장 곧다) ⑵ `--from-down` 플래그로 순서를 갈라 준다 ⑶ 문서만 고치고 사람에게 맡긴다
(이번 회차는 ⑶ 을 했다 — dry-run 머리에 전제와 손 순서를 박았다).

**Risk:** 🟡 재기동은 드물지만 **틀리면 소크 창이 걸린다.** ②는 사람이 순서를 알면 우회 가능하다.

**연결:** [BL-634](#bl-634) (배타성 가드가 재기동 경로의 전제) · [ADR-024](decisions/024-soak-stability-gate.md) (C1/C2 리셋 규칙)

**출처:** 2026-08-08 soak-mortality-repair P7 (재기동을 실제로 밟다가 둘 다 물렸다)

---

**해결 (2026-08-09, W1 — 처방 ⑴):** ⓿ 단계가 `soak-stack.sh ps` 로 갈래를 고른다.

- 신설 `soak-stack.sh ps` — **DB 를 안 건드리는** 생존 확인. exit 0 = 하나라도 running /
  1 = 완전 down / **2 = 못 쟀다**. `status` 를 못 쓰는 이유는 그쪽이 `psql` 을 쏘기 때문이다(down 이면 그 자체가 못 돈다).
- 살아 있으면 종전 경로 그대로(⑷ `down → pin → up`). 완전 down 이면 ⓿-b 가 `pin → up` 을
  선행하고 ⑷ 와 증거 덤프를 건너뛴다(`_dump_evidence` 는 fail-closed 라 컨테이너가 없으면 죽는다).

★★★**통합 리뷰가 이 수리 자신에서 fail-open 을 1건 잡았다 (2026-08-09 CONTROL, 실측).**
초판 `_ps` 는 「데몬에 못 닿는다」와 「그런 컨테이너가 없다」를 구분하지 않았고 `soak-restart.sh`
`:110` 이 `|| STACK_UP=0` 으로 **rc 1 과 2 를 한데 접었다.** 뿌리는 도구 쪽이다 —
`docker inspect` 는 두 경우를 **둘 다 exit 1** 로 낸다(실측: 도달 불가 1 · 없는 컨테이너 1).

★**이 결함이 무서운 이유는 「탐지기와 보호가 같은 실패 모드를 공유한다」는 것이다.**
`DOCKER_HOST`·docker context 가 어긋나면 **살아 있는 스택이 「완전 down」으로 보이고**, 그러면
새 ⓿-b 갈래가 `down` 을 건너뛰고 곧장 `pin` 을 부른다. 그런데 `_pin` 의 보호
(`soak-stack.sh:182` 「돌고 있는 고정본 위엔 pin 금지」)는 `_stack_is_pinned`·`_celery_main_pid`
로 판정하고 **그 둘도 같은 docker 로 간다** ⇒ 탐지가 틀린 바로 그 조건에서 가드도 함께 눈이 먼다.
결과는 살아 있는 컨테이너의 mount 원본 `.soak/src` 를 **제자리에서 덮어쓰는 것**이고, 그건
`soak-stack.sh:177-187` 이 P1 로 적어 둔 사고다(창은 B 로 기록되는데 실제로는 A 가 돈다).
★**가정이 아니다** — 이 레포는 클라우드 이관에서 원격 `DOCKER_HOST` 때문에 `stack_pinned` 가
영구 false 인 조건을 이미 밟았다. ★**종전 경로엔 이 구멍이 없었다** — 항상 `down` 이 먼저였고
docker 가 죽어 있으면 그 `down` 이 실패해 die 했다(fail-closed). **구멍은 이 수리와 함께 생겼다.**

- **수리:** `_ps` 가 `docker version --format '{{.Server.Version}}'` 으로 **데몬 도달성만** 먼저
  재고(실측: 도달 불가 exit 1 · 정상 0), 못 닿으면 **rc=2** 로 돌려준다. `soak-restart.sh` 는
  `case` 로 3값을 3값으로 받아 **2 면 die** 한다. **측정 실패를 상태로 바꾸지 않는다.**
- **red→green:** `DOCKER_HOST=tcp://127.0.0.1:1 scripts/soak-stack.sh ps` 가 **1 → 2**,
  같은 조건의 `soak-restart.sh` 가 **「완전 down 갈래 진입」 → rc=2 로 정지**.
- **변이 M — 3/3 판별.** `1|2) STACK_UP=0` 으로 초판을 복원하면 신규 3건이 정확히 red 가 된다
  (`rc=0 로 끝났다` · **`pin 을 불렀다`** · `스택을 만졌다`). 하네스 **14 → 17건**.
- **음성 대조 N:** 정상 docker 에서 `ps` 는 여전히 **0**(살아 있음)·**1**(컨테이너 없음)을 내고,
  기존 14건이 전부 초록 유지 — 두 정상 갈래의 호출 순서(`ps down pin up` / `ps pin up`)가 불변이다.

★★★**구현 중 순서 결함 1건을 red 시험이 잡았다 — 내가 ⓿ 를 잘못된 자리에 뒀다.** 처음엔 ⑴
바로 앞에 뒀는데, 완전 down 이면 그보다 **먼저** 도는 파라미터 조회(`_q` 원장 최근 세션)가 빈 값을
내고 `--confirm` 이 「원장에 세션이 하나도 없다」로 **exit 2 · 스택 호출 0건**으로 죽었다. 그러면
`--strategy-id/--account-id` 를 손으로 줘야 하고 **그게 이 BL 이 없애려던 손 절차 자체**다.
⇒ ⓿-b 를 파라미터 조회 **앞으로** 옮겼다.

- **red → green (같은 가짜 트리, 완전 down, `--confirm`):**
  수리 전 = `rc=2` · 「원장에 세션이 하나도 없다」 · **스택 호출 0건**(시도조차 못 했다).
  수리 후 = `rc=0` · 호출 순서 **`ps pin up observe gate`** · 세션 등재까지 끝났다.
- **변이 M — 4/4 red, 방향 양쪽.** ⑴ ⓿ 분기 제거(`STACK_UP` 항상 1) → down 케이스 **4건 red**
  ⑵ 항상 down 갈래(`STACK_UP` 항상 0) → up 케이스 **4건 red**(이 짝이 없으면 「늘 pin→up」 구현이 통과한다)
  ⑶ heredoc 에 백틱 재삽입 → 정적 카운트 + 실행 단언 **2건 red**
  ⑷ 안내문의 stop/flatten 순서 뒤집기 → **1건 red**. 변이가 도달했는지 매번 grep 으로 따로 확인했다.
- **음성 대조 N:** ① up 갈래 호출 순서가 **`ps down pin up`** 으로 종전과 동일하고 덤프도 여전히
  `down` 앞이다(하네스가 단언). ② `git diff` 상 ⑷ 본문은 `if/else` 로 감싼 것 외에 **한 줄도 안 바뀌었다.**
  ③ dry-run 실행 출력에 `command not found` **0건**.
- ★★★**결함 ① 은 「수리 완료」가 아니었다 — 회귀해 있었다.** 위 본문이 「정적 카운트 0건으로
  동결」이라 적었지만 **그 카운트를 도는 게이트가 없었다.** 2026-08-09 실측: dry-run 이
  `line 214: ConnectionRefusedError: command not found` 를 내고 그 낱말이 출력에서 사라져 있었다
  (백틱을 되돌려 놓은 것은 **BL-656 이 ⑶ 로 박아 넣은 그 전제 문단 자신**이다).
  ⇒ 백틱을 「」로 바꾸고 **`final-gates.sh` 에 「소크 재기동 하네스」를 붙였다** — 동결은 기록이
  아니라 실행이다.
- **신설 하네스** `scripts/soak-restart-test.sh` (14 단언, 전건 통과 = exit 0). mktemp 트리에
  사본 + 가짜 `soak-stack.sh`·`assert-main-checkout.sh`·`soak-observe.sh`·`soak-gate.sh` +
  PATH 앞단 가짜 `docker`·`uv`. **오라클은 호출 순서 로그**다(출력 문구로 재면 문구를 바꾸는
  순간 판별력이 사라진다). 실제 소크·docker·거래소를 한 번도 건드리지 않는다.
- ★하네스 자체의 결함 1건도 실행이 잡았다 — 가짜 `docker` 가 인자를 로그에 적었더니 **여러 줄
  SQL 이 로그를 찢어** 인접 패턴(`ps pin up`)이 깨졌다. 인자를 안 적고 `grep -vx docker` 로 건다.

---

### BL-657

**Priority:** P2
**카테고리:** 운영 / BL-003 게이트 (판정 신뢰성)
**Trigger:** 다음 게이트 실행 시 / 게이트 숫자를 인용하기 전
**Est:** S
**상태:** ✅ Resolved (2026-08-09, W1)

**게이트가 자기가 어느 DB 를 보는지 출력하지 않는다 — 그래서 로컬 실행이 그럴듯한 거짓 창을 낸다.**

`scripts/soak-gate.sh` 는 `.env.local` 의 `DATABASE_URL` 을 따라간다. 소크는 서버에 있으므로
**로컬에서 돌리면 로컬 DB 를 잰다.** 2026-08-08 실측 대조(같은 스크립트, 같은 커밋):

|                | 로컬                  | 서버                  |
| -------------- | --------------------- | --------------------- |
| 판정           | `UNKNOWN 측정불가`    | `UNKNOWN 진행중`      |
| C1             | **1.5574h**           | **15.5680h**          |
| 창 시작        | `2026-08-06T20:31:48` | `2026-08-07T15:10:49` |
| `stack_pinned` | ✗                     | ✓                     |
| 실격 이력      | 14건                  | 11건                  |
| 귀속 세션      | `98ff6ecc`·`fcf1dcbe` | `a4f1cbfb`·`de3db35a` |

★**위험의 실체는 「틀린다」가 아니라 「틀린 티가 안 난다」다.** `C1 1.5574h` 는 오류 메시지가
아니라 **정상 서식의 숫자**다. 판정도 `UNKNOWN` 이라 평소와 같다. 지금 이것을 가르는 것은
사람이 네 신호(`stack_pinned=✗` · 창 시작 날짜 · 실격 건수 · `⚠ 원장에만 있고 …` 경고)를
**알고 있을 때뿐**이다.

**처방 후보:** ⑴ 헤더에 **DB 호스트/포트/이름과 실행 호스트명**을 한 줄 찍는다(가장 싸고, 인용된
출력만 봐도 갈린다) ⑵ `.soak/` pin 파일과 DB 를 대조해 불일치면 `측정불가` 가 아니라 **명시적
거부**로 끝낸다 ⑶ 서버 전용 가드(`assert-soak-host.sh` 류).

★**부수 발견 — 클라우드 이관이 phantom 을 다 안 옮겼다.** 로컬 14건 중 `phantom` 3건
(08-04 `39731d57` · `cc19abd2` · 08-05 `a16aa640`)이 서버에 없다. 그래서 같은 원장
(`docs/reference/operations/soak-disqualifications.jsonl`)을 대조해도 귀속이 갈린다 —
서버 「코드 결함 7 · 운영 사고 3 · 미판정 1」 vs 로컬 「7 · 0 · 7」. **원장은 서버 DB 를 전제로
쓰였다**는 사실이 어디에도 안 적혀 있다.

**Risk:** 🟡 게이트 숫자는 [BL-003] 판정의 유일한 근거다. 거짓 창을 인용하면 회차 계획이 통째로
어긋난다(이 회차는 실제로 사용자가 로컬에서 돌려 「C1 1.5574h」를 봤다).

**연결:** [BL-641](#bl-641) (게이트 해석) · [BL-653](#bl-653) (같은 게이트의 표본 해상도)

**출처:** 2026-08-08 session-handoff (사용자가 로컬에서 게이트를 돌리다 발견)

---

**해결 (2026-08-09, W1 — 처방 ⑴):** `scripts/soak-gate.sh` 판정 헤더 바로 위에 한 줄이 뜬다.

```
══ [BL-003] 소크 안정 게이트 ══
대상: quantbridge-db 127.0.0.1:5433/quantbridge · docker ctx:desktop-linux · 실행 MacBook-Pro-2.local · 분류기 localhost:5433/quantbridge
판정: UNKNOWN 측정불가
```

★★★**위 본문의 「게이트는 `.env.local` 의 `DATABASE_URL` 을 따라간다」는 C1~C5 에 대해 거짓이다.**
판정의 입력은 `soak-gate.sh:208-212` 의 `_q()` = `docker exec ${DB_CONTAINER} psql -U quantbridge -d quantbridge`
이므로 로컬/서버를 가르는 축은 **어느 docker 데몬의 어느 컨테이너인가**다. `DATABASE_URL` 은 phantom
분류기(`:339` 의 서브셸 소싱)만 쓴다 — 다만 그 결과가 `unverified_hours` 로 C1 을 깎으므로 무관하지도 않다.
실측이 이 구분을 강제했다: 이 워크트리의 `DATABASE_URL` 은 `localhost:5433` 인데 `_q` 는 컨테이너
`quantbridge-db` 로 간다. **`DATABASE_URL` 만 찍으면 BL-657 과 같은 계열의 새 fail-open** 이므로 양쪽을 다 찍는다.

- **red:** 수리 전 게이트 출력에 DB 호스트·포트·DB명·실행 호스트 언급 **0건**(`grep -cEi "호스트|:5432|:5433|quantbridge-db|docker"` = 0).
- **green:** 헤더 1줄. 필드 6개 모두 실측값이고 하드코딩 0.
- **변이 M — 2/2 추종.** ⑴ `QB_DB_CONTAINER=quantbridge-redis` → `대상: quantbridge-redis (포트 미공개)/? …`
  ⑵ `.env.local` 에 `DATABASE_URL=…@mutant.example:65432/mutantdb` 추가 → `분류기 mutant.example:65432/mutantdb`
  (복원 후 sha256 동일). 리터럴 `@` 가 든 비밀번호(`u:p@ss@mutant2.example:1/db2`)도 `mutant2.example:1/db2` 로만 남았다.
- **음성 대조 N — 판정 비트 전건 불변.** 수리 전/후를 `--no-collect` 로 떠서 `대상:` 줄만 빼고 `diff`:
  차이는 `현재:` 벽시계 1줄뿐. 벽시계를 정규화하면 **diff 완전 공집합** — C1~C5 6비트 · 실격 9건 ·
  귀속 창 0개 · 귀속 불가 110.11h 전부 동일.
- **비밀번호 누출 0.** 마지막 `@` 앞을 통째로 버리므로 비밀번호에 `@` 가 있어도 안전. 실측 grep 0건.
- **부수 처리:** 「원장은 서버 DB 를 전제로 쓰였다」를
  `docs/reference/operations/soak-disqualifications.jsonl` 의 `_comment` 행에 적었다
  (서버 11건 vs 로컬 14건 vs 이 워크트리 9건 — 같은 스크립트가 세 값을 낸다).
- ★**자기 결함 1건을 변이가 잡았다.** `docker exec` 는 OCI 런타임 오류를 **stdout 으로** 내므로
  초판 M1 에서 `exec: "psql": executable file not found` 가 dbname 자리에 그대로 실렸다 →
  식별자 서식(`^[A-Za-z0-9_]+$`)이 아니면 `?` 로 버린다.

---

### BL-658

**Priority:** P3
**카테고리:** Docs / decisions (소급 ADR)
**Trigger:** Optimizer 설계를 실제로 바꿀 때 (알고리즘 교체 · scikit-optimize 이탈 · GA 파라미터 변경)
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-09 등재. **착수 금지**(이 회차 비목표 = M/L 급).
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`decisions/013-optimizer-strategy.md` 를 소급 작성해 ADR-013 결번을 닫는다.**

[BL-504](#bl-504) 가 2026-08-09 에 인용 축을 닫았다 — 살아 있는 인용 4곳에 git tombstone 경로를 병기했다.
남은 것은 **실체를 `decisions/` 로 승격**하는 일이고, 그것은 별개 작업이다.

**실체(확인됨):** `docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` — **24,703바이트**,
도입 `9c93fa70`(PR #258), 삭제 `94da86b1`(2026-08-06 문서 대개편).
읽는 법 = `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md`.
인용되는 절이 전부 그 안에 있다 — `## 6.`(§6 #8 = BL-235 deferred, `:202`) · `### 7.2` · `### 8.2` ·
`## 5. References` · `## 7~9` Sprint 55/56/57 amendment 3종.

★**소급 작성은 결정을 새로 만드는 게 아니라 이미 실행된 결정을 기록하는 것이다.**
없는 근거를 지어내지 말고 실제 코드(`backend/src/optimizer/executors/`)와 **대조**해라 —
dev-log 가 적은 결정과 코드가 어긋나면 **코드가 맞다**([ADR-026] 「지금 무엇을 하는가」 축).

★**같이 볼 것 — ADR-019 는 결번이 아니다.** `decisions/019-worker-auto-rebuild.md` 가 실재한다(Sprint 38).
`docs/dev-log/INDEX.md:141` 의 `2026-05-05 · ADR-019 Surface Trust Pillar` 는 **ID 중복 호칭**이므로
그 줄을 고칠지도 이 작업에서 함께 정한다(고칠 거면 `020-trust-layer-ci-design.md:3` 의 renumber 서술과 정합시켜라).

**Risk:** 🟢 동작 무영향. 비용은 24,703바이트를 읽고 코드와 대조하는 시간이다.

**연결:** [BL-504](#bl-504) (인용 축 — 닫힘) · [ADR-026](decisions/026-documentation-ssot.md) (tombstone 규약)

**출처:** 2026-08-09 backlog-sweep ([BL-504] G0 에서 실체가 git 에 살아 있음을 확인하고 분리)

---

### BL-659

**Priority:** P3
**카테고리:** Test infra / 디자인 캐논 게이트
**Trigger:** 디자인 캐논 게이트가 빨개졌을 때 / 캐논 스윕 착수 시
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`design-canon-calibration.spec.ts` 의 `screen-06-strategies-list.html` 케이스가 간헐 실패한다.**

2026-08-09 backlog-sweep-4lane W3 관측 — `pnpm e2e:design-canon` **7회 중 2회** 이 케이스
하나만 빨개졌다(나머지 실행은 42/42). 같은 커밋에서 **연속 3회 42/42** 이고, `git stash` 로
내 diff 를 걷어낸 뒤에도 같은 케이스가 통과/실패를 오갔다 — 즉 **코드 회귀가 아니다.**

★**위험은 실패 자체가 아니라 오독이다.** 이 게이트는 W3 회차에서 [BL-548](#bl-548) ·
[BL-645](#bl-645) 의 음성 대조로 쓰였다. 간헐 실패를 자기 변경의 회귀로 읽으면 멀쩡한
수리를 되돌리게 된다. 이번 회차도 처음 빨개졌을 때 stash 대조를 하고서야 무관함을 확정했다.

★**원인은 조사하지 않았다.** 대상이 정적 HTML 이라 서버 상태와 무관해 보이는데도 흔들린다는
점이 단서다 — 폰트 로딩 타이밍 또는 대비 계산 경계값을 의심한다. **[가정]** 이며 미확인이다.

**권장 접근:** 실패 실행의 하드 실패 목록을 성공 실행과 diff 해 흔들리는 항목을 특정한다.
그 항목이 대비 경계값이면 임계 근처 표본을 고정하거나 폰트 로딩 완료를 기다린다.

**Risk:** 🟢 게이트 신뢰성만 해당. 프로덕션 코드 영향 없음.

**출처:** 2026-08-09 backlog-sweep-4lane W3 (BL-548·BL-645 음성 대조 중 관측)

---

### BL-660

**Priority:** P3
**카테고리:** Test infra / 골든 재생성 (도구 산출 ↔ 포매터 충돌)
**Trigger:** 골든을 의도적으로 갱신할 때 / `regen_golden.py` 를 CI 에 넣을 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)**
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)

**`--confirm` 이 쓰는 포맷과 커밋본의 포맷이 구조적으로 다르다.**

pre-commit 의 `prettier --write` 가 `*.json` 을 대상으로 하므로 커밋된
`golden/<case>/expected.json` 은 배열이 **한 줄로 접혀** 있다. 반면 `regen_golden.py` 는
`json.dumps(generated, indent=2)` 로 쓰므로 **원소당 한 줄**이다. 그래서 `--confirm` 을 한 번만
돌려도 트리가 dirty 해진다 — 2026-08-09 실측 `+29/-2` (값은 하나도 안 바뀌고 전부 재포맷).

★**`--check` 는 이 어긋남을 구조적으로 못 본다.** `_differences()` 가 비교하는 것은
`json.loads` 한 **값**이라 포맷에 무관하기 때문이다. 즉 `--check` 는 green 인데 `--confirm` 은
트리를 더럽히는 상태가 정상으로 유지된다.

**왜 지금 아픈가 (실사례):** [BL-627](#bl-627) 을 고치면서 「`--check` 가 통과하니 산출이 커밋본과
바이트 동일하겠지」라고 넘겨짚었다가 **자기 반증**했다. 이 어긋남이 바로 그때 `test_regen_roundtrip_is_stable`
이 정본을 **시험 시간의 31.8%** 동안 dirty 로 만들던 실체다(표본 906 중 288).

**처방 후보:** ⑴ 스크립트가 `prettier` 와 같은 서식으로 쓴다 ⑵ `.prettierignore` 에 golden 을 넣어
`json.dumps` 서식을 정본으로 삼는다 ⑶ 쓰기 직후 `prettier --write` 를 부른다. ★어느 쪽이든 **한쪽을
정본으로 정하는 것**이 요점이고, 정한 뒤에는 `--check` 가 서식까지 보게 할지 따로 정해야 한다.

**Risk:** 🟢 값 정확성에는 영향이 없다. 다만 골든 갱신 diff 의 신호 대 잡음비를 망가뜨린다.

**출처:** 2026-08-09 backlog-sweep-4lane (W2 — BL-627 수리 중 부수 발견)

---

### BL-661

**Priority:** P1
**카테고리:** Backend / trading (청산) · 운영 CLI
**Trigger:** 실자금 전환 전 필수 / 조건부 진입을 쓰는 세션을 내릴 때
**Est:** S
**상태:** 🟡 부분 해결 — 2026-08-10 guards-blind-spots 에서 **거짓 성공을 없앴다**(보고 + exit 3). 포지션 0 인데 미체결 조건부 진입이 있으면 `409 detail={"code":"resting_conditional_entries",…}` 이고 CLI 가 잔량을 찍고 **exit 3** 으로 끝난다. **취소는 미구현**이라 부분이다 — 권장 접근의 「그것을 취소하도록」은 [BL-669](#bl-669) 로 분리했다. 변이 6/6 red · 음성 대조 green
**트리거 판정:** 미도래 — 외생 조건(실자금 전환) + 동승(조건부 진입 세션을 내릴 때). 잔여인 「취소하도록」은 [BL-669] 로 분리됐고 그쪽은 **DEFERRED**(뒷절이 거래소 접촉 승인이다) (2026-08-11 bl-703-partial-verdicts)

**`flatten` 이 「이미 flat」을 내고 exit 0 하는데 조건부 주문은 남아 있다.**

`close_service.py:100-104` 는 `fetch_open_positions` 결과만 보고 비면 `409 no_open_position`
을 낸다. **미체결 조건부 진입 주문은 보지 않는다.** 그런데 운영 CLI
(`live_session_admin.py:383-387`)가 그 예외를 잡아 **`✓ 이미 flat 이다 (no_open_position).
주문을 내지 않았다.` 를 출력하고 `return`** 한다 — 종료 코드 **0**.

⇒ **조건부 주문이 살아 있는 채로 「정리 완료」로 읽힌다.** 그 주문은 나중에 트리거되어
아무도 보고 있지 않은 시점에 포지션을 연다.

★**이 레포는 같은 계열을 이미 겪었다** — 2026-08-08 `down` 이후 `FLAT=YES` 인데 엔진이 재무장해
`d655f560`(FOREIGN sell) + `8d4272fe`(ours buy)가 거래소에 남았고 `EXCLUSIVE=NO` 가 됐다.
그때는 `soak-restart.sh:288-304` 가 die 해서 드러났지만, **`flatten` 자신은 조용했다.**

**왜 지금 아픈가:** [BL-003] runbook §7 rollback 이 `flatten` → `status` 순서인데, `flatten` 이
거짓 성공을 내면 **실자금에서 조건부 주문을 남긴 채 「내렸다」고 판단**하게 된다. runbook 은
「`status` 의 `RESTING_CONDITIONAL` 을 반드시 눈으로 확인하라」로 **문서 방어만** 해 뒀다 —
코드 방어가 아니다.

**권장 접근:** `close_position` 이 포지션과 **조건부 주문을 함께** 보고, 포지션이 없어도
미체결 조건부가 있으면 그것을 취소하도록. 조회 계약은 이미 있다 —
`fetch_open_conditional_orders(creds, symbol, reduce_only=None)`
(`live_session_admin.py:242-244` 가 쓴다. ★`reduce_only=None` 은 협상 불가 계약이다).
CLI 쪽은 `no_open_position` 을 **성공으로 출력하지 마라** — 최소한 조건부 잔량을 함께 찍어라.

**Risk:** 🔴 실자금에서 고아 조건부 주문. 데모에서도 참이지만 손실이 가상이라 안 아팠다.

**출처:** 2026-08-09 bl003-mainnet-runbook (codex 적대 리뷰 발견 2 — 코드 대조로 확정)

---

### BL-669

**Title:** `flatten` 이 미체결 조건부 진입을 **보고만** 하고 취소하지 않는다
**Category:** Backend / trading (청산) · 운영 CLI
**Priority:** P2
**Trigger:** [BL-517] 종결 + 거래소 접촉 검증이 가능한 회차
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — [BL-661] 이 거짓 성공만 없앴다(보고 + exit 3). 취소는 미착수
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 guards-blind-spots (사용자 결정으로 범위 분리)

**원인 / 영향:** [BL-661] 의 권장 접근은 「포지션이 없어도 미체결 조건부가 있으면 그것을
취소하도록」이었는데, 2026-08-10 회차는 **보고까지만** 했다. 고아 조건부는 여전히
운영자가 손으로 취소해야 한다.

**왜 이번에 안 했나 (사용자 판정 5)** — ⑴ [BL-661] 의 P1 은 **거짓 성공**이지 취소 부재가 아니다
⑵ 취소는 비가역이고 미룸은 가역이다(같은 선택을 `live_signal.py:1467-1512`
`_cancel_planned_entry` 가 이미 한다 — 취소 대신 `"deferred"` 를 돌려 janitor 로 넘긴다)
⑶ `soak-restart.sh:347-363` 의 `EXCLUSIVE` 가드가 하류에서 fail-closed 다
⑷ 「ours 만 취소」는 `_ownership_scope` 위에 서는데 [BL-517] 이 그 축을 다루는 중이다
⑸ 그 회차는 거래소 접촉 금지라 취소 경로를 **검증할 수 없었다**.

**권장 접근:** `order_link_id` 소유권으로 ours 만 취소하고 foreign 은 보고한다
(`live_session_admin.py:246-255` 의 status 표기와 같은 판별자). `close_service` 에는
소유권 스코프가 없으므로 `OrderRepository` 주입이 선행이다.
**Risk:** 🔴 비가역 · 실자금

---

### BL-670

**Title:** `docs/status.md` 가 **존재하지 않는 절**을 근거로 인용한다 (`[ADR-025] §⑧`)
**Category:** Docs / SSOT
**Priority:** P3
**Trigger:** 문서 감사 시 / 그 문장을 근거로 쓸 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 guards-blind-spots (사용자가 제기 → grep 으로 확정)

**원인 / 영향:** `docs/status.md:396` 이 「원장 못 읽은 tick 은 리컨사일을 1 tick 미룬다
(취소는 비가역, 미룸은 가역)」를 **[ADR-025] §⑧** 으로 돌린다. 그런데
`025-conditional-fill-ownership.md` 에는 **번호 절이 없고**(전부 이름 헤딩),
`비가역` 은 `docs/decisions/` **전체에 0건**이다(grep 실측). **죽은 앵커다.**

★원칙 자체는 유효하다 — 정본은 **구현**이다: `live_signal.py:1467-1512` 가 취소 대신
`"deferred"` 를 돌려 janitor 로 넘기고(`:1499`), gap-resync 는 `_GAP_RESYNC_DEFER_KEY`(`:273`)로
같은 선택을 한다.

**권장 접근:** `status.md` 의 인용을 ADR 앵커에서 **구현 경로**로 교체한다.
★2026-08-10 회차는 `status.md` 를 안 건드렸다(레인 충돌 회피) — 등재만 했다.
**Risk:** 🟢

---

### BL-671

**Title:** [BL-661] 의 새 409 계약이 웹 UI 와 OpenAPI 에 **도달하지 않는다**
**Category:** Frontend / trading · API 계약
**Priority:** P2
**Trigger:** 코크핏 청산 버튼으로 조건부 잔량을 봐야 할 때
**Est:** S
**상태:** 🟡 부분 해결 — 2026-08-10 close-ownership-axis 가 409 body 의 키를 레포 계약에 맞췄고(`message` → `detail`), 2026-08-10 fe-close-surface 가 **FE 축을 닫았다**: `RestingEntriesConflictSchema` 로 `orders` 를 펴고 `CloseOutcomePanel` 이 목록으로 그린다. 함께 `api-client.ts` 의 `code` 해석이 FastAPI 의 `{detail:{code}}` 한 겹을 파도록 고쳤다(종전에는 도메인 코드가 **언제나** `unknown_error` 였다). ★**본문의 「화면에 generic `API 409` 만 뜬다」는 두 표 중 하나에만 참이었다** — `account-positions-table` 은 이미 `describeApiError` 를 썼고 `open-positions-table` 만 `error.message` 였다. 그 비대칭도 함께 없앴다. **잔여 1건 = `router.py` 의 409 `responses` 선언(OpenAPI)**. 넣지 않은 이유는 아래 §OpenAPI 판단
**트리거 판정:** 미도래 — 동승 조건(코크핏 청산 버튼으로 조건부 잔량을 봐야 할 때). 잔여 1건 = `router.py` 의 409 `responses` OpenAPI 선언이고, 본문 §OpenAPI 판단이 넣지 않은 이유를 적어 뒀다 (2026-08-11 bl-703-partial-verdicts)
**출처:** 2026-08-10 guards-blind-spots codex 최종 적대 리뷰 (P2 — 코드 대조로 확정)

**원인 / 영향:** 서버는 `409 {"detail": {"code": "resting_conditional_entries", "message": …,
"orders": […]}}` 를 낸다. 그런데 `frontend/src/lib/api-client.ts:53,97` 은 **최상위 `code`** 와
**`detail.detail` 문자열**만 처리한다 ⇒ 주문 목록과 메시지가 사라지고 화면에는
generic `API 409 …` 만 뜬다. `router.py:610` 에 409 `responses` 선언이 없어 **OpenAPI 에도
이 구조가 없다**(생성 응답은 202·422 뿐).

★백엔드는 완화를 이미 넣었다 — `message` 필드에 사람이 읽을 한국어 한 문장을 싣는다.
그러나 클라이언트가 중첩 `detail` 을 안 펴므로 그것조차 화면에 안 나온다.
★2026-08-10 회차는 `frontend/` **0줄** 제약이라 손대지 않았다.

**권장 접근:** 라우터에 409 error schema 를 선언하고, `api-client.ts` 가 중첩
`detail.code`/`message`/`orders` 를 펴서 렌더하도록 맞춘다.

**§OpenAPI 판단 (2026-08-10 fe-close-surface).** 409 `responses` 선언을 **넣지 않았다**.
근거 셋이 전부 실측이다 — ⑴ `frontend/` 에 OpenAPI 코드젠이 **없다**(생성 타입 파일 0 ·
codegen 스크립트 0). 화면은 수기 Zod 로만 계약을 아니까 선언이 화면에 도달하는 경로 자체가
없다. ⑵ `responses=` 를 쓰는 라우트가 `backend/src` 전체에 **0건**이다 — 넣으면 FE 회차가
선례 없는 관례를 연다. ⑶ `test_main_openapi_gating.py` 는 docs **노출** 게이팅만 재고, 에러
응답 문서화를 요구하는 게이트는 없다. ⇒ 값이 0 인데 `backend/src` 를 건드리게 된다.
**넣을 값이 생기는 시점은 FE 가 OpenAPI 에서 타입을 생성하기 시작할 때**다.

**Risk:** 🟡 ~~운영자가 화면만 보면 조건부 잔량을 못 본다~~ → 🟢 화면 축은 닫혔다. 남은 것은 문서 축

---

### BL-672

**Title:** [BL-661] service→CLI `detail` 계약을 **잇는 테스트가 없다** + runbook §7 이 낡았다
**Category:** Backend / trading · 테스트 계약 · 문서
**Priority:** P3
**Trigger:** `flatten` 출력 형식을 바꿀 때
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-11 bl-672-close) — 잔여 2건이 **둘 다 이미 이행돼 있었다.** ⑴ 계약 테스트 = `test_live_session_admin_flatten.py:130` `test_flatten_cli_formats_actual_flat_resting_entry_detail` (2026-08-10 close-ownership-axis 가 넣었다). ⑵ 「runbook §7 갱신 미이행」은 **반증됐다** — `bybit-mainnet-runbook.md:363-372` 이 2026-08-10 정정으로 `no_open_position` 의 새 의미와 **rc 0/1/3/4 분기**를 이미 적고 있다. ★**이 항목은 한 줄도 새로 짜지 않고 닫혔다** — 닫은 것은 코드가 아니라 **원장의 거짓 문장**이다. 「미이행」이라 적힌 것을 문서에게 되물었더니 이행돼 있었다([BL-307]·[BL-703] 에 이은 **네 번째** 실증)
**트리거 판정:** ~~도래 — 잔여가 이미 0 이라 종결 판정만 남았다. ★상태줄의 「⑵ runbook §7 갱신은 **미이행**」이 **반증됐다** — `bybit-mainnet-runbook.md:363-372` 이 2026-08-10 정정으로 `no_open_position` 의 새 의미와 **rc 0/1/3/4 분기**를 이미 적고 있다([BL-661]+[BL-684] 인용). 원장이 「미이행」이라 말할 때 **문서에게 되물어라** (2026-08-11 bl-703-partial-verdicts)~~
**출처:** 2026-08-10 guards-blind-spots codex 최종 적대 리뷰 (P3 2건 — 코드 대조로 확정)

**원인 / 영향 ⑴ 계약 단절.** `test_close_service.py` 는 실제 detail 에서 `order_id` 만 보고,
`test_live_session_admin_flatten.py` 는 **키가 전부 있는 수제 dict** 를 주입한다. 둘을 잇는
테스트가 없어서, `side` 없는 detail 을 CLI 에 주면 `live_session_admin.py:395` 가
**`KeyError` → rc 1** 이 된다(재현됨). 지금은 service 가 항상 전 키를 채우므로 무증상이다.

**원인 / 영향 ⑵ runbook 이 거짓을 안내한다.**
`bybit-mainnet-runbook.md:361` 이 「`close_service.py:102-104` 가 조건부를 안 보므로
`no_open_position` 이 나올 수 있다」고 단언하는데, [BL-661] 이후 **코드가 조건부를 검사하고
exit 3 으로 분기한다.** `no_open_position` 의 의미가 「진짜 flat」으로 좁아졌다.

**권장 접근:** ⑴ 실제 service detail 을 CLI formatter 에 넘기는 통합 테스트 1건, 또는 공유
Pydantic 스키마. ⑵ runbook §7 에서 `no_open_position` 의 새 의미와 exit 3 분기를 갱신한다.
**Risk:** 🟢

---

### BL-665

**Title:** 거래 상세 검색이 키 입력마다 2000건을 다시 정렬한다 (디바운스 없음 + comparator 안 날짜 파싱)
**Category:** Frontend / JS 성능
**Priority:** P3
**Trigger:** 거래 상세·리포트 원장에서 검색·필터 반응이 굼뜰 때
**Est:** XS
**상태:** ✅ Resolved (2026-08-09 fe-perf-quartet) — decorate·sort·undecorate 로 키를 N회만 파고, 검색은 기존 `useDebouncedValue`(200ms)를 물렸으며 memo dep 을 객체에서 스칼라 8개로 바꿨다. 회귀 3건(동점 안정성 · 디바운스 · 배지↔표↔CSV 스냅샷 일치)은 변이 M2·M3·M6 으로 빨간 것을 확인했다
**출처:** 2026-08-09 status-triage-mass — `/vercel-react-best-practices` 교차검증

**원인 / 영향:** `features/backtest/utils.ts:230-243` 의 comparator 가 `new Date(t.entry_time).getTime()` 을 **비교할 때마다** 판다. `trade-filter-row.tsx:104` 의 검색 입력은 `onChange` 로 곧장 `filters` 를 갱신하고, `filters` 는 정렬 `useMemo` 의 dep 다(`trade-detail-table.tsx:70-113`).

데이터원은 `useAllBacktestTrades`(상한 **2000**, `hooks.ts:116`). 2000건을 `entry_time` 으로 정렬하면 ≈2000·log₂2000 ≈ 22,000 비교 × 2회 = **약 44,000회 날짜 문자열 파싱**이고, 그것이 **검색창 키 입력 한 글자마다** 다시 돈다. `trade-ledger-table.tsx:43-53` 은 같은 comparator 로 2000건을 전량 정렬한 뒤 `.slice(0, 25)` 한다.

★레포에 `useDebouncedValue`(`features/strategy/utils.ts:28`)가 **이미 있는데** 여기선 안 쓴다.

**해결 (2026-08-09 fe-perf-quartet):** ⑴ `trade-detail-table.tsx` 가 `useDebouncedValue(filters.search, 200)` 를 쓴다 — **입력창은 계속 즉시값을 그린다**(굼뜨면 안 된다). ⑵ `applyTradeFilterSort` 를 decorate·sort·undecorate 로. ⑶ memo dep 을 객체 `filters` → 스칼라 필드 7개 + `debouncedSearch` 로(H-1 「scalar dep 선호」. 객체를 쓰면 키 한 글자마다 identity 가 갈려 그 memo 가 **사실상 없는 것과 같다**).

★**⑶ 은 백로그가 안 적은 부분이고, 사실 ⑴·⑵ 보다 이것이 근본이다** — 디바운스를 물려도 dep 이 객체면 다른 필터 조작마다 여전히 전량 재계산된다.

★**미리보기 25건 부분 선택은 하지 않았다** — ⑵ 로 파싱이 사라지면 남는 것은 숫자 비교뿐이라 복잡도만 산다(`trade-ledger-table.tsx:43-53` 그대로).

★★**codex 적대 리뷰가 내가 만든 결함을 잡았다(C7 REFUTED · P1).** 배지 `countActiveFilters(filters)` 는 **즉시값**을 세는데 표·CSV(`handleExport` 는 `filtered` 를 쓴다)는 **200ms 늦은** 값을 쓴다 ⇒ 검색어를 치고 200ms 안에 CSV 를 누르면 배지는 「필터 1개」인데 CSV 는 **안 걸린 전량**이 나간다. 수리 = 배지도 같은 스냅샷(`{...filters, search: debouncedSearch}`)을 세게 했다. **즉시성이 필요한 것은 입력창 하나뿐이다.**

★**주석의 셈도 반증됐다(codex P2).** 「2000건이면 비교 ~22,000회」는 **입력 의존값**이다 — V8 TimSort 는 이미 정렬된 입력에서 ~1,999회다. 사전계산은 입력과 무관하게 N회라는 것이 정확한 진술이다.

★**착수 시점에 검색은 단위·e2e 어느 쪽에도 커버가 0건이었다** — 디바운스를 넣기 전엔 「검색이 여전히 거른다」조차 못 재고 있었다. 시험 2건을 신설했다.
**Risk:** 🟢

---

### BL-666

**Title:** `reactCompiler: true` 검토 — FE 전체 `memo()` 0건인 채로 수동 처방을 반복하고 있다
**Category:** Frontend / 빌드
**Priority:** P3
**Trigger:** `rerender-*` 계열 결함이 또 등재될 때 · Next 16 업그레이드 회차
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — [BL-663] 에서 분리했다. 켜지 않았고 측정도 안 했다 (2026-08-09 fe-perf-quartet)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-09 fe-perf-quartet ([BL-663] 범위 분리)

**원인 / 영향:** `next.config.ts` 에 `reactCompiler` 가 없다. `eslint-plugin-react-compiler`(19.1.0-rc.2)는 devDependency 로 있지만 **린트만 한다.** 그래서 FE 전체에 `memo()`/`React.memo` 가 **0건**인 채로 재렌더 범위를 컴포넌트 분리로 하나씩 손봐 왔다([BL-663] 이 그 4번째다).

**권장 접근:** ⑴ `reactCompiler: true` 를 켜고 빌드·번들·테스트 델타를 잰다 ⑵ H-3(render body 에서 `ref.current` 대입 금지, `frontend/AGENTS.md`)이 이미 컴파일러 호환을 전제하므로 위반 잔여를 먼저 센다 ⑶ 켠 뒤에도 [BL-663] 같은 **구독 위치** 문제는 안 사라진다는 것을 명시해라 — 컴파일러는 메모이제이션을 자동화하지 나쁜 구독 경계를 옮겨 주지 않는다.
**Risk:** 🟡 빌드 전역 스위치라 회귀 표면이 넓다. 단독 회차로 잡아라.

---

### BL-667

**Title:** `frontend/**` 의 json·md 를 스테이징하면 pre-commit 이 죽는다 (루트에 prettier 플러그인 부재)
**Category:** DX / 게이트
**Priority:** P3
**Trigger:** `frontend/` 안의 json·md·yml 을 커밋할 때
**상태:** 🟡 부분 해결 (2026-08-09 fe-perf-quartet) — 루트 devDependency 를 추가해 즉시 증상은 없앴다. 구조(두 곳이 같은 설정을 서로 다른 해석 뿌리로 읽는다)는 그대로다
**트리거 판정:** 미도래 — 동승 조건(`frontend/` 안의 json·md·yml 을 커밋할 때). 즉시 증상은 루트 devDependency 로 닫혔고 잔여는 구조(두 곳이 같은 설정을 서로 다른 해석 뿌리로 읽는다)뿐이라 그 파일들을 건드리는 회차에 붙는다 (2026-08-11 bl-703-partial-verdicts)
**Est:** XS
**출처:** 2026-08-09 fe-perf-quartet (커밋이 실제로 막혀서 발견)

**원인 / 영향:** `frontend/.prettierrc` 가 `"plugins": ["prettier-plugin-tailwindcss"]` 를 선언하는데 그 패키지는 **`frontend/node_modules` 에만** 있었다. 루트 `package.json` 의 lint-staged 는 `*.{json,md,yml,yaml}` 을 **레포 전역**으로 잡아(패턴에 슬래시가 없어 basename 매칭) `frontend/package.json` 같은 파일에도 루트 prettier 를 돌린다. 그러면 prettier 가 `frontend/.prettierrc` 를 찾아 읽고 플러그인을 **루트에서** 해석하려다 실패한다:

```
[error] Cannot find package 'prettier-plugin-tailwindcss' imported from <repo>/noop.js
```

★**기존 결함이다** — 손대지 않은 파일로 재현된다: `npx prettier --check frontend/tsconfig.json`. 오랫동안 `frontend/` 의 json 을 커밋한 회차가 없어 잠복해 있었다(직전 사례는 PR #463).

★**증상이 원인을 숨긴다** — lint-staged 가 `prettier --write [FAILED]` 와 함께 eslint 태스크를 `[KILLED]` 로 찍어서 **eslint 가 실패한 것처럼 보인다.** 실제 실패는 prettier 하나뿐이다.

**권장 접근:** 근본 해는 둘 중 하나다 — ⑴ 루트 lint-staged 의 json/md 글롭에서 `frontend/**` 를 제외하고 frontend 자신의 prettier 에 맡긴다 ⑵ 두 `.prettierrc` 를 하나로 합친다. 지금은 ⑶ **루트에 플러그인 추가**로 막아 뒀는데, 버전이 두 곳에서 각자 흘러가면 같은 파일을 두 도구가 다르게 포맷할 수 있다.
**Risk:** 🟢 포맷만 건드린다.

---

### BL-668

**Title:** `e2e:authed` backtest form 2건이 로컬에서만 빨갛다 (CI 는 초록)
**Category:** DX / 테스트 환경
**Priority:** P3
**Trigger:** 로컬에서 `pnpm e2e:authed` 를 돌릴 때 · 격리 스택을 새로 만들 때
**상태:** ⏳ 대기 (트리거 미도래) — 원인 미규명. 코드가 아니라 환경이라는 것까지만 좁혔다 (2026-08-09 fe-perf-quartet)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-09 fe-perf-quartet (final-gates 에서 발견 · 음성 대조 2회)

**원인 / 영향:** `e2e/sprint46-tier1-critical.spec.ts:69`(#1 backtest form 422 unsupported_builtins)와 `e2e/sprint46-tier3-nth.spec.ts:489`(#20 friendly_message 카드)이 로컬 격리 스택(`:3100`/`:8100`)에서 일관 실패한다. 증상은 **하나**다 — `POST /api/v1/backtests` 가 아예 안 나가서 `waitForRequest` 가 15초 타임아웃한다. 폼 제출 **이전** 단계에서 막힌다는 뜻이다.

★★**음성 대조 2회로 코드 축을 배제했다:**

1. `git checkout 85970b83 -- frontend/src` 로 **main 코드**를 씌우고 같은 두 건을 태웠다 → **동일하게 2 failed / 1 passed.** 브랜치 회귀가 아니다.
2. **CI 는 초록이다** — PR **#574 에서 `e2e` SUCCESS**, 그 뒤 #575·#576·#577 은 전부 문서 전용이라 `e2e` 가 SKIPPED. ⇒ CI 가 통과시킨 FE 코드가 지금 main 과 같다.

⇒ 남은 축은 **로컬 격리 스택의 데이터/시드 상태**다. 폼이 제출까지 못 가는 것이므로 전략 목록·`parse_status`·coverage 전제가 CI 시드와 다를 가능성이 높다.

★**이것이 게이트를 오염시킨다** — `final-gates.sh` 의 `e2e authed` 가 항상 FAIL 이면 그 게이트는 **신호를 잃는다**(진짜 회귀도 같은 빨강으로 보인다).

★★**같은 회차에 별개의 flake 1건도 드러났다 — `e2e/trading-ui.spec.ts:108`(kill switch API 오류 → 황색 배너).** 전체 스위트 2회 중 **1회만** 실패했고(`ks-error-banner` 미발견 + 30초 테스트 타임아웃), **격리 실행 3/3 통과**했다. ★이 파일은 이 회차가 실제로 만진 `kill-switch-banner.tsx` 의 시험이라 회귀를 의심해 일부러 3회 태웠다 — **회귀가 아니라 flake 다.** 위 2건(항상 실패)과 **다른 현상**이므로 같이 묶어 고치지 마라.

**권장 접근:** ⑴ `test-results/.../error-context.md` 와 trace 를 열어 어느 검증에서 멈추는지 본다 ⑵ CI 의 e2e 시드 절차와 로컬 격리 스택 시드를 대조한다 ⑶ 차이가 시드면 로컬 시드 타깃에 반영하고, 아니면 이 BL 의 전제를 다시 세운다.
**Risk:** 🟢 프로덕션 코드 무관. 단 게이트 신뢰도를 깎는다.

---

### BL-680

**Title:** 공개 공유 URL `/share/backtests/[token]` 에는 리포트 섹션 앵커가 아예 없다
**Category:** Frontend / backtest (공유)
**Priority:** P3
**Trigger:** 공유 링크로 특정 섹션을 가리키고 싶다는 요구가 나올 때
**Est:** M (같은 데이터를 토큰 경로에서 다시 조립해야 한다)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-shareable-urls 에서 코드 대조로 확인. 사거리 밖이라 열어 둔다.
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-shareable-urls, codex G1 설계 검증 발견 2

**원인 / 영향:** [BL-397] 이 준 앵커 10개는 `/backtests/[id]` 의 `BacktestReportShell` 에만 있다.
그런데 화면의 「공유」 버튼은 API 가 준 `share_url_path` 를 그대로 복사하고
(`share-button.tsx:29-39`), 그 공개 URL 은 `/share/backtests/[token]` 이다.
그 페이지는 `BacktestReportShell` 을 **참조조차 하지 않는다**(`page.tsx` 에 해당 import 0건,
고정 `id=` 0건). 즉 **사용자가 실제로 공유하는 링크에는 `#trades` 가 붙을 대상이 없다.**

★따라서 [BL-397] 이 닫은 것은 「로그인한 사용자끼리 주소창을 복사해 나누는 경로」다.
공개 공유 경로는 별개이고, 두 화면이 같은 리포트를 서로 다른 컴포넌트로 그린다는 사실 자체가
이 항목의 비용을 정한다.

**Risk:** 🟢 (지금 깨진 것은 없다. 없는 기능이다)

---

### BL-681

**Title:** 백테스트 상세 라우트가 Suspense 없이 클라이언트 `isLoading` 분기를 쓴다 — 앵커 재조정이 필요해진 뿌리
**Category:** Frontend / backtest (렌더 경로)
**Priority:** P3
**Trigger:** 상세 라우트를 스트리밍으로 바꿀 때 / [BL-397] 의 해시 효과를 걷어내고 싶을 때
**Est:** M
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-shareable-urls 에서 실측. 이 회차 사거리 밖.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-shareable-urls, G5 `/vercel-react-best-practices` (`async-suspense-boundaries`)

**원인 / 영향:** `backtests/[id]/page.tsx` 는 서버 prefetch 도 `HydrationBoundary` 도 없이
클라이언트 `BacktestDetailView` 만 렌더하고, 그 컴포넌트는 `isLoading`/`isError` 를 손으로
분기한다. `frontend/AGENTS.md` §3 이 명시적으로 금지하는 패턴이다
(「`if (isLoading)` / `if (error)` 남발 금지 → `Suspense` + `ErrorBoundary` 로 위임」).

★**이것이 [BL-397] 에서 마운트 1회 해시 재조정 `useEffect` 를 넣어야 했던 이유다.** 리포트가
문서 로드 시점에 DOM 에 없으니 네이티브 fragment 위치결정이 빈손으로 끝난다.
비교 대상 — 목록 라우트(`backtests/page.tsx`)는 이미 `auth()` + `prefetchQuery` +
`HydrationBoundary` 를 쓴다. **같은 도메인 안에서 두 라우트가 다른 규약을 따르고 있다.**

★★**단, 「Suspense 로 바꾸면 해결된다」는 틀렸다** — 이 항목의 첫 판이 그렇게 적었고
codex G6 적대 리뷰가 반증했다. **클라이언트** Suspense fallback 뒤에 리포트를 꽂는 구조는
여전히 fragment 위치결정 **이후**다. 효과를 없앨 수 있는 조건은 하나뿐이다 —
**대상 엘리먼트가 최초 HTML 에 들어 있을 것**(서버 렌더 또는 prefetch + 하이드레이션).

**권장 접근:** 상세 라우트를 목록 라우트와 같은 형태(서버 prefetch + `HydrationBoundary`)로
맞춘 뒤, `backtest-report-shell.tsx` 의 해시 효과가 **없어도** e2e
`report-section-anchors.spec.ts` 가 green 인지로 판정한다. 그 시험이 이미 판별자다.

**Risk:** 🟡 (상세 화면 전체의 로딩 계약을 바꾼다 — 회귀 표면이 넓다)

---

### BL-682

**Title:** 세션 생성 직후 잠깐 「목록에서 밀려났습니다」로 오진한다 (background refetch 창)
**Category:** Frontend / live-sessions UX
**Priority:** P3
**Trigger:** 세션 생성 흐름을 손볼 때 / 사용자가 이 깜빡임을 보고할 때
**Est:** S
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-shareable-urls 의 codex G6 적대 리뷰가 제기. ★**이 diff 가 만든 것이 아니라 종전 `useState` 판에도 있던 동작**임을 코드 대조로 확인했다.
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-shareable-urls, codex G6 발견 1

**원인 / 영향:** `LiveSessionForm` 은 생성 성공 즉시 `onSuccess(session)` 을 부르고, 무효화 래퍼는
목록 refetch 를 `await` 하지 않는다(`use-invalidating-mutation.ts`). **기존 목록 캐시가 있으면
background refetch 중에도 `isPending` 은 false** 이므로, 코크핏은 「선택 id 는 있는데 목록에 없다」
= `live-session-stopped-notice` 로 떨어진다. 새 응답이 오면 상세로 바뀐다.

★**종전 판도 같았다** — `onSuccess` 가 `setSelectedId(session.id)` 를 했고 같은 3분기를 탔다.
[BL-551] 이 그 id 를 URL 로 옮겼을 뿐 이 창은 그대로다. 즉 **회귀가 아니라 기존 결함의 재발견**이다.

★현행 시험이 이것을 못 잡는 이유도 기록해 둔다 — vitest 는 `replace` 인자만 보고 다음 렌더를
하지 않으며, e2e 는 폼 제출을 하지 않는다. **닫을 때 이 두 구멍을 함께 메워야 한다.**

**권장 접근:** ⑴ 생성 응답으로 목록 캐시를 낙관적으로 채우거나 ⑵ `isFetching` 중에는 중단 안내
대신 로딩 안내를 쓴다. ⑵ 는 [BL-551] 이 이미 만든 `isPending` 분기 옆이라 값싸다.
**Risk:** 🟢 (자기 해소되는 깜빡임 · 데이터 오류 아님)

---

### BL-683

**Title:** `useSearchParams` 가 Suspense 경계 없이 들어와 `/trading` 을 prerender 밖으로 밀어냈다
**Category:** Frontend / trading (성능)
**Priority:** P2
**Trigger:** FE 성능 회차 · 또는 `/trading` 초기 페인트가 느리다는 보고
**Est:** S (page.tsx 에 Suspense 한 겹 = 5분. 복원폭 측정이 그보다 오래 걸린다)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 review-and-merge 2축 리뷰 Standards 축이 제기, **실측으로 확정**. 사용자 판정으로 머지를 막지 않고 등재했다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 review-and-merge (PR #580 Standards 축)

**원인 / 영향:** `trading-cockpit.tsx:54` 가 `useSearchParams()` 를 부르는데
`(dashboard)/trading/page.tsx` 는 `<TradingCockpit />` 하나만 렌더하고 `<Suspense>` 경계가 없다.
Next 16 은 static 세그먼트에서 이 훅을 만나면 **라우트 전체를 CSR 로 bail out** 한다.
기존 `useSearchParams` 선례 둘(`backtests/`·`strategies/`)은 서버 `auth()` 로 이미 dynamic 이라
이 문제가 없었다 — `/trading` 이 **첫 static 사례**다.

**실측** (빌드 산출물 대조 — main `d277a54a` 빌드 vs 브랜치 `e9f01576` 빌드):

| 축                              | main        | 브랜치      | 델타                     |
| ------------------------------- | ----------- | ----------- | ------------------------ |
| `.next/server/app/trading.html` | 65,097 B    | 41,439 B    | **−23,658 B**            |
| `aria-label="트레이딩 개요"`    | 1건         | **0건**     | 코크핏이 통째로 사라졌다 |
| `static/chunks` 총량            | 2,941,841 B | 2,955,844 B | +14,003 B (**+0.48%**)   |
| 청크 파일 수                    | 57          | 57          | 0                        |

★**음성 대조** — prerender 된 **16개 라우트 중 15개가 바이트 동일(+0)** 이고 `trading.html` 만
줄었다. 빌드 조건 차이가 아니라 **이 변경이 원인**이다.
★**잃은 것은 prerender HTML 뿐이고 클라이언트 JS 는 +0.48% 다.** 두 축을 섞어 말하지 마라 —
[BL-662]~[BL-665] 가 판 것은 JS 축이고 이것은 HTML 축이다.

**되찾을 수 있는 것의 크기 — fallback 수준이다.** `useSearchParams` 가 코크핏 **최상단**(`:54`)
이라 `page.tsx` 를 `<Suspense>` 로 감싸면 경계가 **페이지 전체**를 삼킨다 ⇒ prerender 되는 것은
fallback 껍데기뿐이고, **그 껍데기는 `trading/loading.tsx` 가 이미 준다.**
65kB 를 통째로 되찾으려면 URL 을 읽는 부분만 작은 자식으로 격리해야 한다 — 그건 S 가 아니다.
★`/trading` 은 `(dashboard)` **인증 라우트**라 공개 라우트보다 prerender 의 값이 낮다.

**권장 접근:** `page.tsx` 에 `<Suspense>` 한 겹. 선례는 `backtests/[id]/trades/page.tsx:32`.
그 뒤 **같은 방법으로 복원폭을 재라** — `.next/server/app/*.html` 전 라우트 크기 대조 +
`aria-label` 존재 여부. 음성 대조(다른 15개 라우트 불변)를 반드시 함께 재라.

**Risk:** 🟡 초기 페인트가 CSR 로 늦다. 기능 결함은 아니다.

---

### BL-684

**Title:** `close_position` 이 포지션이 **있을 때는** 미체결 조건부 진입을 보고조차 하지 않는다
**Category:** Backend / trading (청산) · 운영 CLI
**Priority:** P1
**Trigger:** [BL-003] runbook §7 rollback · 실자금 전환 전 필수
**Est:** S
**상태:** ✅ Resolved — 2026-08-10 close-ownership-axis. 포지션이 있는 경로에서도 미체결 진입 주문을 청산 주문 **앞에** 조회해 `ClosePositionResponse.resting_entries` 로 싣는다. 조회 실패는 청산을 막지 않고 `resting_entries_unknown` 으로 구분한다 — flat 경로의 fail-closed 와 **의도적 비대칭**이다(위험이 반대: flat 에서 fail-open 은 거짓 flat 보고, 포지션 경로에서 fail-closed 는 열린 포지션 봉쇄). CLI 는 rc **4** 신설(0=flat/잔량 없음 · 1=실패 · 3=잔량 있고 주문 미발행 · 4=주문 접수+잔량). 표적 변이 7/7 red(도달 확인 포함). 「조건부 진입」 문구는 **「미체결 진입 주문」**으로 고쳤다 — 필터가 일반 지정가도 잡으므로
**출처:** 2026-08-10 review-and-merge (PR #579 Spec 축)

**원인 / 영향:** [BL-661] 이 넣은 조건부 조회는 `close_service.py:103` 의 `if not positions:`
**블록 안에만** 있다. 포지션이 있으면 `fetch_open_conditional_orders` 를 **한 번도 부르지 않고**
`ClosePositionResponse` 를 돌려주고, CLI(`live_session_admin.py:402`)는
`✓ 청산 주문 접수: order_id=… state=…` + **exit 0** 을 찍는다 — 조건부 잔량은 한 글자도 안 나온다.

⇒ 포지션과 미체결 조건부 진입이 **함께** 있는 상태(runbook §7 rollback 의 정상 상황)에서
[BL-661] 이 지목한 거짓 성공이 **더 흔한 경로에 그대로 남아 있다.** 포지션은 닫히고 조건부는
산 채로 남는데 운영자는 「내렸다」고 읽는다.

★[BL-661] 의 권장 접근 원문은 「`close_position` 이 포지션과 **조건부 주문을 함께** 보고」였다 —
「포지션이 없을 때만」이 아니다. **부분 해결의 경계가 백로그 본문과 다르다.**

**부수 — 이름이 동작보다 좁다.** `close_service.py:109` 의 `order.reduce_only is False` 는
`providers.py:1253-1263` 이 `fetch_open_orders`(비-trigger)와 trigger 주문을 **합쳐서** 주므로
**일반 미체결 지정가 진입도 통과시킨다**. 잡는 쪽으로는 안전하지만 메시지는 「조건부 진입」이라
부른다 — 운영자가 화면에서 못 찾을 수 있다.

**Risk:** 🔴 실자금에서 고아 조건부 주문 — [BL-661] 과 같은 위험이고 경로가 더 흔하다.

---

### BL-685

**Title:** 마운트 1회 해시 재조정이 데이터 도착 뒤 성장에 밀리는지 **측정되지 않았다**
**Category:** Frontend / backtest (리포트 앵커)
**Priority:** P2
**Trigger:** [BL-397] 앵커 불만 보고 · 또는 FE e2e 를 손보는 회차
**Est:** S (픽스처 하나 + 시험 하나)
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 review-and-merge Spec 축이 제기. ★**「결함」이 아니라 「미측정」이다** — 제기한 리뷰어 본인이 「브라우저 scroll-anchoring 이 막을 수 있다, 측정하지 않았다」고 자인했다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 review-and-merge (PR #580 Spec 축)

**원인 / 영향 (제기된 기전 — 미확정):** `backtest-report-shell.tsx:89-93` 의 해시 재조정은
`useEffect(…, [])` 라 마운트 1회만 돈다. 그 시점에 `:74` 의 `trades.data?.items` 는 `undefined`
이고, §02(`#benchmark` — `#trades` **위**)의 `performance-chart.tsx:88-92` 는 trades 가 있을 때만
caption + 120px pane 을 그린다 ⇒ §02 가 **스크롤이 끝난 뒤** 자라 `#trades` 를 아래로 민다.

★**현 시험이 못 잡는 이유:** `report-section-anchors.spec.ts:37` 이 쓰는
`fixtures/backtest-report.ts:82` 의 `trades` 기본값이 **`[]`** 라 `hasTrades` 가 false 다 ⇒
**성장 경로를 아예 안 탄다.** 게다가 두 단언이 한쪽 방향이다(`toBeInViewport()` 에 ratio 없음 ·
`box.y >= TOPBAR_H`) — 아래로 밀리는 드리프트는 red 를 못 만든다.

**재는 법 (다음 회차가 0에서 시작하지 않도록):**

1. `trades` 가 **있는** 픽스처를 만든다 — 현 기본값 `[]` 를 덮어야 한다.
2. `/backtests/<id>#trades` 로 진입한다.
3. §02 성장 **후** `#trades` 의 `box.y` 가 유지되는지 관측한다 — ratio 를 준
   `toBeInViewport({ ratio })` 로. 한쪽 방향 단언으로는 이 현상을 못 잡는다.
4. ★**로컬 e2e 는 [BL-668] 로 2건이 상시 red 다**(`sprint46-tier1-critical.spec.ts:69` ·
   `sprint46-tier3-nth.spec.ts:489`). **새 red 를 그 둘과 분리해서 읽어라.**
5. green 이면 원인은 브라우저 scroll-anchoring 이다 — **그 사실을 여기 적고 닫아라.**
   「측정했더니 문제가 없었다」도 산출이다.

**Risk:** 🟢 (미측정. 참으로 밝혀지면 🟡)

---

### BL-686

**Title:** `scroll-mt-[76px]` 이 `--topbar-h` 토큰을 우회하고 같은 수를 네 곳에 다시 쓴다
**Category:** Frontend / backtest (리포트 앵커) · 디자인 토큰
**Priority:** P3
**Trigger:** 탑바 높이를 바꿀 때 — 그때 네 곳이 따로 논다
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 review-and-merge Standards 축이 제기, 코드 대조로 확인
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 review-and-merge (PR #580 Standards 축)

**원인 / 영향:** `backtest-report-shell.tsx:56` 이 `className="section scroll-mt-[76px]"` 다.
`globals.css:170` 이 `--topbar-h: 60px` 를 선언하고 7곳 이상이 `var(--topbar-h)` 로 소비하는데,
이 60(+16 여백)은 **컴포넌트 클래스 · 그 주석 · 단위 시험의 정확-문자열 단언 · e2e `TOPBAR_H = 60`**
**네 곳**에 다시 쓰여 있다.

★**부수 — [BL-397] 이 스스로 정한 회귀 판별자를 움직였다.** 그 명세는 「**Risk:** 🟢 렌더 트리
무변경(속성 하나 추가) · 기존 `stress-test` 앵커 불변이 회귀 판별자」라고 썼는데, `:56` 의 클래스가
`id={STRESS_ANCHOR}`(`:262`) 를 포함한 **모든** 섹션에 붙어 그 앵커도 76px 이동했다.
**판별자로 쓰려면 움직였다는 사실을 알고 써야 한다.**

**권장 접근:** `scroll-mt-[calc(var(--topbar-h)+16px)]` 한 줄로 접는다.

**Risk:** 🟢

---

### BL-687

**Title:** pre-commit 의 backend 훅이 스테이징된 py 파일 중 **첫 하나만** 검사한다
**Category:** Infra / 개발 도구 (pre-commit)
**Priority:** P2
**Trigger:** 파이썬 파일을 2개 이상 한 커밋에 스테이징할 때 — 즉 거의 매 커밋
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-10, `stage/precommit-scope`) — 훅 3개를 `"${0#backend/}" "${@#backend/}"` 로 바꿔 스테이징된 py 전량을 넘긴다.
**트리거 판정:** 도래 — 상태줄이 「2026-08-10 close-ownership-axis 가 실측으로 재현」이고 트리거가 「즉 거의 매 커밋」이다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 close-ownership-axis (커밋 중 관측 → `bash -c` 시맨틱으로 재현)

**원인 / 영향:** 루트 `package.json` 의 lint-staged 가 backend 훅 3개를 이렇게 쓴다.

```json
"backend/**/*.py": [
  "bash -c 'cd backend && .venv/bin/ruff check --fix --exit-non-zero-on-fix ${0#backend/}'",
  "bash -c 'cd backend && .venv/bin/ruff check ${0#backend/}'",
  "bash -c 'cd backend && .venv/bin/ruff format ${0#backend/}'"
]
```

lint-staged 는 명령 뒤에 **파일 목록 전체**를 붙이는데, `bash -c 'cmd' f1 f2 f3` 에서 `$0` 는
**`f1` 하나**이고 나머지는 `$@` 에 들어간다. 명령이 `${0#backend/}` 만 참조하므로 **두 번째
이후 파일은 어떤 훅도 통과하지 않는다.**

**재현 (실측):**

```
$ bash -c 'echo "받은 것: [$0] · 나머지: [$@]"' a.py b.py c.py
받은 것: [a.py] · 나머지: [b.py c.py]
```

★**발각 경위** — py 5개를 한 커밋에 올렸는데 `ruff format` 이 [COMPLETED] 로 찍히고도
`src/trading/schemas.py` 의 포맷 불일치가 **그대로 남았다**. 같은 ruff 버전(0.15.10)으로
직접 돌리면 재포맷된다 ⇒ 훅이 그 파일에 **도달하지 않았다**.

★**진짜 피해는 format 이 아니라 `ruff check --fix --exit-non-zero-on-fix` 다** — 두 번째
이후 파일의 lint 오류가 **커밋을 못 막는다**. `final-gates` 가 전체를 보므로 최종 방어선은
살아 있지만, pre-commit 이 「검사했다」고 말하는 범위가 실제보다 좁다.

**권장 접근:** `${0#backend/}` → `"$@"` 형태로 바꾸고 `bash -c '…' _ "$@"` 처럼 `$0` 자리를
더미로 채운다. 또는 lint-staged 함수형 설정으로 파일 목록을 직접 조립한다.

**Risk:** 🟡 검사기가 「내가 본 것 중에는 없었다」만 말하는 전형(LESSON-092)

**수리 (2026-08-10).** 루트 `package.json` 의 backend 훅 3개에서 `${0#backend/}` →
`"${0#backend/}" "${@#backend/}"`. bash 의 `${@#prefix}` 는 **각 위치인자에** 접두사 제거를
적용하므로 `$0` 하나와 나머지 전부를 함께 넘긴다.

**실측 (재현 → 수리 → 음성 대조 → 종단)**

| 무엇                                   | 현행                            | 수정본                                               |
| -------------------------------------- | ------------------------------- | ---------------------------------------------------- |
| `ruff format` 에 3파일                 | `1 file reformatted` (b·c 무시) | `3 files reformatted`                                |
| **음성 대조 — 1파일**                  | —                               | `1 file reformatted` (빈 `$@` 가 전체를 잡지 않는다) |
| **종단 `pnpm exec lint-staged`** 2파일 | —                               | 두 파일 다 포맷된 채 인덱스에 반영                   |

★**음성 대조가 필요한 이유** — 파일이 1개면 `$@` 가 비는데, 인용을 빠뜨려 `${@#backend/}` 로
쓰면 **빈 인자**가 들어가 ruff 가 CWD 전체를 잡는다. 큰따옴표가 그걸 막는다(0단어 확장).

★**프론트 축은 같은 뿌리의 다른 실패 모드다** — `frontend/**` eslint 줄은 파일을 **아예 참조하지
않아** 매 커밋 **전량 린트**한다(실측 **14.7s**). 과소가 아니라 과대라 이 BL 로 묶지 않는다 ⇒ [BL-696]

---

### BL-688

**Title:** FE `ClosePositionResponseSchema` 가 [BL-684] 의 새 필드를 Zod 에서 버린다
**Category:** Frontend / trading (청산) · API 계약
**Priority:** P2
**Trigger:** 코크핏 청산 버튼으로 조건부 잔량을 봐야 할 때 — [BL-671] 잔여와 같은 화면
**Est:** S
**상태:** ✅ Resolved — 2026-08-10 fe-close-surface. `RestingEntryOrderSchema` 신설 + 두 필드를 `.default()` 로 선언(서버 모델 기본값과 같게)했고, `close-outcome.ts` 가 응답/에러를 다섯 상태로 갈라 `CloseOutcomePanel` 이 그린다. 잔량 있음과 **확인 실패**가 서로 다른 `data-testid` 를 갖고 서로를 배제한다. 변이 6/6 red(도달 확인 포함) · e2e 5건이 실브라우저에서 판정 · Zod strip 을 되돌리면 e2e 3/5 가 빨개진다
**출처:** 2026-08-10 close-ownership-axis (PR Spec 축)

**원인 / 영향:** [BL-684] 가 `ClosePositionResponse` 에 `resting_entries` 와
`resting_entries_unknown` 을 실었는데, `frontend/src/features/live-sessions/schemas.ts:185-189`
의 `ClosePositionResponseSchema` 는 `order_id`/`state`/`detail` **셋만** 선언한다.
`z.object` 는 기본이 strip 이라 파싱은 성공하고 **새 필드는 조용히 사라진다.**

⇒ CLI 는 rc 4 로 잔량을 알리는데 **웹 코크핏은 여전히 「청산 접수」만 보여준다.**
[BL-684] 본문이 지목한 거짓 성공이 **화면 축에는 그대로 남아 있다.**

★[BL-671] 의 잔여(FE 가 409 `orders` 를 렌더하지 않는다)와 **같은 화면·다른 경로**다 —
저것은 409(진입만 남음), 이것은 200(청산 접수 + 잔량). 함께 고치는 것이 싸다.
★2026-08-10 회차는 `frontend/` **0줄** 제약이라 손대지 않았다.

**권장 접근:** Zod 스키마에 두 필드를 더하고, 코크핏이 `resting_entries` 를 목록으로,
`resting_entries_unknown` 을 「확인 실패」 경고로 렌더한다. [BL-671] 과 한 회차로 묶어라.

**Risk:** 🟡 운영자가 화면만 보면 고아 진입 주문을 못 본다

---

### BL-689

**Title:** stand-down 이 uid 형제 행마다 세션 조회를 따로 돈다 (N+1)
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 같은 `exchange_uid` 행이 3개 이상으로 늘 때 — 지금은 실측 2행이라 무증상
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 close-ownership-axis 가 [BL-517] 을 닫으며 **의도적으로 남겼다**(스코프)
**트리거 판정:** 미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 close-ownership-axis (Standards 축 · Spec 축 **양쪽이 독립 검출**)

**원인 / 영향:** `live_signal.py` 의 `_resolve_current_position` 이 이렇게 돈다.

```python
for account_id in scope_ids:
    others.extend(await session_repo.list_active_by_account(account_id))
```

`list_active_by_account` 는 단일 id 만 받으므로 **형제 행 수만큼 쿼리가 는다.**
`backend/AGENTS.md` §2 의 「N+1 방지」와 결이 다르다.

★**이 회차가 안 고친 이유** — `list_active_by_account` 는 소비자가 3곳이고
([BL-517] 이 넓힌 stand-down · `tasks/trading.py:501` · `websocket/position_fanout.py:69`)
그중 stand-down 만 넓은 축이 필요하다. 시그니처를 바꾸면 나머지 둘의 의미도 함께 바뀐다.
⇒ 복수형 메서드를 **새로** 추가하는 것이 옳고, 그건 이 회차 스코프 밖이었다.

★**지금 무증상인 이유는 형제가 2행이라서다 — 가드가 아니라 데이터다.** [BL-605] 가
신규 이중 적재를 막았지만 기존 574행은 그대로 두므로, 행 수는 줄지 않는다.

**권장 접근:** `list_active_by_accounts(account_ids, *, symbol=None)` 를 리포지토리에 추가해
한 쿼리로 접는다. 판정이 `any()` 라 심볼 필터를 repo 로 내리면 조기 종료도 산다.

**Risk:** 🟢 (성능 축. 결과는 지금도 옳다)

---

### BL-690

**Title:** `soak-stack.sh` 의 「연속 창은 끊긴다」가 「벌어 둔 C2 를 잃는다」로 읽힌다
**Category:** Infra / 소크 운영 도구 (문구)
**Priority:** P3
**Trigger:** 다음에 `pin` 을 집행할 때 — 또는 사망 축 수정을 미룰지 판단할 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 soak-pin-cost-correction 이 오해를 코드로 반증하고 문서 2곳을 고쳤다. **도구 문구는 아직 그대로**다
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 close-ownership-axis (세션 프롬프트의 절대 규칙이 코드에 반증되며 발각)

**원인 / 영향:** `scripts/soak-stack.sh:185` 가 `down` 을 요구하며 이렇게 말한다.

```
→ 'scripts/soak-stack.sh down' 으로 내린 뒤 pin 해라 (연속 창은 끊긴다).
```

문장 자체는 참이다 — **진행 중인 창**은 거기서 끊긴다. 그런데 **「이미 벌어 둔 최장 창(C2)을
잃는다」**로 읽혔고, 그 오독이 `docs/status.md` 의 「재기동 시 … C2 는 0 부터」를 낳았으며,
거기서 다시 세션 프롬프트의 **절대 규칙**(「`pin` 금지 — C2 를 0 으로 리셋한다」)으로 승격됐다.

**무엇이 사실인가** — `soak_gate_predicate.py` 에서 `window_start = disq[-1].at`(`:614`)이라
창을 리셋하는 것은 **실격뿐**이고, `C1 = sum(merged)`(`:690`) · `C2 = max(merged)`(`:691`) 다.
게이트 자체 출력이 고정 sha **두 종류**의 귀속 창을 나란히 보여주며 합이 맞는다
(`15.3007 + 0.0133 + 26.6558 = 41.97h`). ⇒ pin 은 attribution 을 쪼갤 뿐 과거를 배제하지 않는다.

★**피해는 문구가 아니라 그것이 만든 미룸이다** — 「사망 축 수정은 C1 완주 후」라는 계획이
**검증되지 않은 전제 위에** 서 있었다. 코드 결함 7건이 실격 원장의 다수인데도 그렇다.

**권장 접근:** 두 문장으로 가른다 — ⑴ 「진행 중 창은 끊긴다(C1 은 거기까지 계상된다)」
⑵ 「이미 24h 를 넘긴 창은 C2 가 `max` 라 그대로 남는다」 ⑶ 「진짜 위험은 `down` 동안의 tick
공백이 실격을 만드는 것이다 — 그것만이 창을 리셋한다」.

**Risk:** 🟢 (문구. 단 이 문구가 만든 판단 오류는 🟡였다)

---

### BL-691

**Title:** `RestingEntryOrder` docstring 이 409 직렬화를 `str()` 이라고 말하는데 코드는 `model_dump(mode="json")` 이다
**Category:** Backend / trading (청산) · 문서(주석)
**Priority:** P3
**Trigger:** 409 경로의 필드 타입을 바꿀 때 — 또는 그 docstring 을 근거로 삼을 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-close-surface 가 FE 쪽 계약을 읽다 발견. 스코프 밖이라 등재만
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-close-surface (계약 조사 중 코드 대조)

**원인 / 영향:** `backend/src/trading/schemas.py:132-139` 의 docstring 이 「문자열이 필요한
것은 `HTTPException(detail=<raw dict>)` 로 나가는 409 경로뿐이고, **거기서만 `str()` 로
담는다**(`close_service.py`)」고 적었다. 그런데 실제 코드는
`close_service.py:143` 에서 `RestingEntryOrder.from_snapshot(order).model_dump(mode="json")`
을 쓴다. `str()` 을 직접 부르는 자리는 없다.

**재현:** `grep -n 'str(' backend/src/trading/services/close_service.py` → 해당 호출 0건.
`grep -n 'model_dump' 같은 파일` → `:143` 1건.

★**결과는 같지만 기술이 낡았다.** 이 문장은 2026-08-10 close-ownership-axis 가 `str()` 방식을
`model_dump(mode="json")` 로 바꾸면서 남은 잔재다(그 커밋이 「두 경로가 갈라지지 않게 하는
유일한 장치」라고 쓴 것이 바로 이 교체다). 다음 사람이 docstring 을 믿고 `str()` 을 찾으면
없는 것을 찾게 된다.

**권장 접근:** 그 문단을 `model_dump(mode="json")` 으로 고친다. 한 문장이다.
**Risk:** 🟢 (주석. 동작 무관)

---

### BL-692

**Title:** `RestingEntryOrder.from_snapshot(order: object)` 이 정적 검증을 통째로 포기한다
**Category:** Backend / trading (청산) · 타입
**Priority:** P3
**Trigger:** `ConditionalOrderSnapshot` 의 필드명을 바꿀 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-close-surface 가 FE 쪽 계약을 읽다 발견. 스코프 밖이라 등재만
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-close-surface (계약 조사 중 코드 대조)

**원인 / 영향:** `backend/src/trading/schemas.py:146-156` 의 시그니처가 `order: object` 라
다섯 필드 접근이 전부 `# type: ignore[attr-defined]` 다. `ConditionalOrderSnapshot`
(`providers.py:221-232`)에서 `trigger_price` 나 `order_link_id` 를 개명하면 **mypy 가 아무 말도
안 하고** 런타임에 `AttributeError` 로 터진다. 그 자리는 청산 경로 한복판이다.

★**409 경로는 더 나쁘다** — 거기서 터지면 「포지션 0 + 진입 잔량」이라는 이미 나쁜 상황에서
500 이 된다.

**재현:** `providers.py` 의 `ConditionalOrderSnapshot.trigger_price` 를 개명하고
`uv run mypy backend/src/trading/schemas.py` → 0 errors. 그 뒤 `test_close_service.py` 만 빨개진다.

**권장 접근:** `order: ConditionalOrderSnapshot` 으로 좁히고 `type: ignore` 5개를 지운다.
순환 import 가 걸리면 `TYPE_CHECKING` 블록 + 문자열 어노테이션으로 충분하다.
**Risk:** 🟢 (지금 동작은 옳다. 개명 안전망이 없을 뿐)

---

### BL-693

**Title:** `alert-rule-form` 의 수동 2단계 `code` 폴백이 `api-client` 수리로 잉여가 됐다
**Category:** Frontend / alert-rules · 정리
**Priority:** P3
**Trigger:** 그 파일을 다음에 열 때
**Est:** XS
**상태:** ⏳ 대기 (트리거 미도래) — 2026-08-10 fe-close-surface 가 만든 잉여. 남의 코드라 지우지 않고 등재만 (`CLAUDE.md` §3)
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 fe-close-surface

**원인 / 영향:** `frontend/src/features/alert-rules/components/alert-rule-form.tsx:31-44` 의
`isDuplicateActiveRule` 은 `error.code` 를 먼저 보고 실패하면 `detail.detail.code` 로 한 겹 더
판다. 그 두 번째 갈래는 `api-client.ts` 가 최상위 `code` 만 보던 시절의 우회다.

2026-08-10 fe-close-surface 가 `resolveErrorCode` 로 그 한 겹을 클라이언트에서 파도록 고쳤으므로
이제 **첫 줄에서 이미 참**이고 아래 9줄은 판정을 가르지 않는다.

★**죽은 코드가 아니다** — 여전히 옳고, 지금도 같은 답을 낸다. 그래서 이 회차가 지우지 않았다.
지울지 남길지는 그 파일을 소유한 회차가 정하는 것이 맞다.

**재현:** `alert-rule-form.tsx:34-43` 을 지우고 alert-rules 테스트를 돌린다 → 전건 통과.

**권장 접근:** 그 파일을 다음에 만질 때 `error.code === "alert_rule_already_active"` 한 줄로 접는다.
**Risk:** 🟢 (동작 무관. 읽는 비용만)

---

### BL-694

**Title:** `## Deferred` H2 표와 판정어 `DEFERRED` 가 같은 것을 두 방식으로 말한다
**Category:** Docs / 원장 정합
**Priority:** P3
**Trigger:** Deferred 표를 편집할 때 · 또는 6-8주 부활 재평가를 돌릴 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 bl-trigger-triage 가 등재만 하고 통합하지 않았다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 bl-trigger-triage ([ADR-028](decisions/028-backlog-deferred-verdict.md) Consequences)

**원인 / 영향:** `## Deferred — trigger 미도래 · 의도적 부활 가능` 표(BL-070~075 · BL-005 · BL-145,
8건)는 **섹션이 없어서** `bl-audit` 집계 밖이다(의도). 그런데 [ADR-028] 이 같은 의미의 판정어
`DEFERRED` 를 신설했으므로, 지금 원장은 「트리거 미도래」를 **두 방식으로** 말한다 — 섹션 있는
151건은 판정어로, 표의 8건은 표 소속으로. 읽는 사람이 어느 쪽이 전부인지 못 고른다.

**권장 접근:** 셋 중 하나. ⑴ 표의 8건에 섹션 + `⏳` 상태줄을 달아 판정어로 흡수(집계가 244→252,
DEFERRED 159) ⑵ 표를 남기되 머리글에 「이 8건은 판정어 축 밖이다」를 명시 ⑶ 표를 `_deferred`
tombstone 으로 되돌린다. **⑵ 가 가장 싸고 ⑴ 이 가장 정합적이다.**
**Risk:** 🟢 문서 전용. 단 ⑴ 은 `bl-audit` 총계를 움직이므로 같은 커밋에서 수치 인용을 함께 고쳐라.

---

### BL-695

**Title:** `**트리거 판정:**` 줄에 소유자가 없다 — 다음 BL 은 이 줄 없이 등재된다
**Category:** Docs / 게이트
**Priority:** P3
**Trigger:** 즉시 — 규율이 기록만 돼 있고 어느 게이트도 안 잰다
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-10, `stage/precommit-scope`) — `docs-audit.sh` 가 ACTIVE/DEFERRED 섹션마다 `**트리거 판정:**` 줄을 **정확히 1개** 요구한다.
**트리거 판정:** 도래 — 규율이 기록만 된 상태이고, 이 레포는 「기록된 규율은 안 지켜진다」를 반복 실측했다([BL-631]·LESSON-078 과 같은 뿌리) (2026-08-10 bl-trigger-triage)
**출처:** 2026-08-10 bl-trigger-triage (자기 산출물의 소유자 부재)

**원인 / 영향:** 이 회차가 ACTIVE/DEFERRED 159건 전량에 `**트리거 판정:**` 줄을 달았고
[ADR-028] §4 가 그것을 규약으로 적었다. **그런데 `bl-audit`·`docs-audit` 어느 쪽도 그 줄의
존재를 재지 않는다.** ⇒ 다음 회차가 새 BL 을 등재하면 그 줄 없이 들어가고, 몇 회차 뒤
「159/159」는 조용히 낡는다. `bl-trigger-sweep.sh` 는 **커버리지(트리거 줄)** 를 재지
**판정 줄**을 재지 않는다 — 다른 양이다.

**권장 접근:** `docs-audit.sh` 에 검사 1건 — ACTIVE·DEFERRED 판정을 받은 섹션에
`**트리거 판정:**` 줄이 **정확히 1개** 있는가. 없으면 exit 1. 산식은 `bl-audit --list` 를
되읽으면 되고 파서를 새로 쓰지 마라. ★같이 볼 것: 그 줄이 **2개**인 경우(중복 상태줄과 같은 사고).
**Risk:** 🟢 게이트 추가. 지금 원장은 159/159 라 도입 즉시 초록이다 — **비용 0에 회귀만 막는다.**

**수리 (2026-08-10).** `scripts/docs-audit.sh` 에 축 하나 추가 — `trigger_verdicts`.
판정은 **`bl-audit.sh --list` 를 되읽어** 얻는다(상태줄 파서를 두 벌로 만들지 않는다 —
두 벌이 갈리면 어느 쪽이 맞는지 아무도 모른다). **0개도 2개도 실패**다: 0 은 규율 누락,
2 이상은 중복 상태줄과 같은 사고다.

**판별력 (양성 2 + 음성 1)**

| 대조                    | 기대 | 실측                                        |
| ----------------------- | ---- | ------------------------------------------- |
| 현행 원장(160/160 정합) | 초록 | RC=0                                        |
| BL-015 판정 줄 **삭제** | red  | RC=1 · `줄이 0개다 … 무엇이 막는지 적어라`  |
| BL-015 판정 줄 **중복** | red  | RC=1 · `줄이 2개다 … SSOT 는 하나여야 한다` |

sha256 복원 대조 완료. ★**도입 즉시 초록이라 비용이 0이다** — 지금 원장이 전량 정합이고,
막는 것은 오직 회귀다.

---

### BL-696

**Title:** `frontend/**` eslint 훅이 스테이징 파일을 안 받아 **매 커밋 전량 린트**한다
**Category:** DX / 게이트 (pre-commit)
**Priority:** P3
**Trigger:** FE 커밋 대기가 거슬릴 때 · 또는 pre-commit 설정을 다음에 손댈 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 실측 등재. 결과는 맞고 **비용만** 틀리다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 precommit-scope)
**출처:** 2026-08-10 precommit-scope ([BL-687] 수리 중 인접 관측)

**원인 / 영향:** 루트 `package.json` 의
`"bash -c 'cd frontend && pnpm exec eslint --fix --no-warn-ignored --'"` 는 lint-staged 가 뒤에
붙이는 파일 목록을 **한 번도 참조하지 않는다**(`$0`·`$@` 어느 쪽도 안 쓴다). ⇒ eslint 가 인자 없이
돌아 flat config 기본 패턴으로 **레포 전량**을 린트한다. 실측 **14.7s / 203% CPU**.

★**[BL-687] 과 같은 뿌리(`bash -c` 위치인자)지만 실패 모드가 반대다** — backend 는 **과소**(첫
하나만), frontend 는 **과대**(전량). 그래서 [BL-687] 로 묶지 않았다. **결과가 맞아서 아무도 못
알아챘다** — 전량 린트는 스테이징분을 포함하므로 검사 자체는 통과한다.

**권장 접근:** [BL-687] 과 같은 꼴로 `"$0" "$@"` 를 넘긴다. 단 eslint 는 `cd frontend` 뒤
**상대경로**를 받으므로 `"${0#frontend/}" "${@#frontend/}"` 여야 한다.
★**고치면 반드시 음성 대조를 해라** — 인용을 빠뜨리면 빈 인자가 들어가 지금과 같은 전량 린트로
조용히 되돌아간다([BL-687] 수리에서 실제로 잰 축이다).
**Risk:** 🟢 훅 설정 1줄. 단 FE 커밋 경로 전체가 걸리므로 종단(`pnpm exec lint-staged`)까지 재라.

---

### BL-697

**Title:** 테스트 DSN 판정 사본이 `test_prefork_smoke_integration.py` 에 1곳 남았다
**Category:** Testing / 안전 (판정 SSOT)
**Priority:** P3
**Trigger:** prefork integration 테스트를 다음에 손댈 때 · 또는 테스트 DSN 판정 규칙을 또 바꿀 때
**Est:** XS
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 [BL-451] 수리 중 인접 관측. 위험은 낮고 **일관성**만 문제다.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이라 인접 작업 회차에 붙인다 (2026-08-10 migration-guard)
**출처:** 2026-08-10 migration-guard ([BL-451] ① 수리 중 전수 grep)

**원인 / 영향:** [BL-451] 이 테스트 DSN 판정을 `tests/_db_guard.py` 한 곳으로 모으면서
`tests/test_migrations.py` · `tests/real_broker/conftest.py` · `tests/real_broker/_harness.py`
세 사본을 위임으로 바꿨다. **`tests/tasks/test_prefork_smoke_integration.py:42` 만 남았다** —
`TEST_DATABASE_URL or DATABASE_URL` 폴백과 `make_url().database` + `_test` 검사를 자기 안에 갖고 있다.

★**지금 위험하지 않은 이유 셋.** ⑴ 이 파일은 `@pytest.mark.integration` 이라 `--run-integration`
없이는 수집돼도 **skip** 된다 ⑵ 파괴적 경로가 아니다(`drop_all`·`downgrade` 를 호출하지 않는다)
⑶ 무엇보다 루트 `tests/conftest.py::pytest_configure` 가 **세션 최상단에서 먼저 판정**하므로
그 폴백이 개발 DB 를 돌려주는 상태에는 애초에 도달할 수 없다.

★**그럼에도 등재하는 이유.** 판정이 두 벌이면 한 벌만 고쳐지는 날이 온다 — 그것이 [BL-451] 의
실사고 구조 그 자체였다. 그리고 이 사본은 폴백을 **허용**하므로, 루트 가드가 미래에 약해지면
둘의 판정이 **어긋난 채로** 조용히 통과한다.

**권장 접근:** `_verify_test_db_dsn()` 을 `_db_guard.refusal_reason()` 위임으로 바꾼다. 단
이 파일의 계약은 「미명시면 **명시적 fail**」(silent skip 금지, codex G.0 P1 #2)이고 `_db_guard`
의 기본값은 `DEFAULT_TEST_DSN` 폴백이라 **의미가 다르다** — 위임 시 그 차이를 어느 쪽으로
맞출지 먼저 정해라. 그냥 갈아끼우면 codex P2 권고가 조용히 뒤집힌다.
**Risk:** 🟢 (테스트 파일 1개. 단 위 의미 차이를 안 보면 계약이 뒤집힌다)

---

### BL-698

**Title:** `e2e authed` 백테스트 폼 422 케이스 2건이 **main 에서 이미 red** 다
**Category:** Testing / 게이트 (e2e)
**Priority:** P2
**Trigger:** 즉시 — `scripts/final-gates.sh` 가 **모든 회차에서** rc=1 을 낸다
**Est:** M (재현 + 원인 규명)
**상태:** ✅ Resolved — 2026-08-10 backtest-submit-fix. **테스트 결함이 아니라 프로덕션 결함이었다.**
백테스트 폼 제출이 `753f4bf6`(2026-08-07, BL-603) 이후 **main 에서 212 커밋 동안 죽어 있었다**.
**트리거 판정:** 해소 — 원인 수정 후 red 3건 전건 green (2026-08-10 backtest-submit-fix)
**출처:** 2026-08-10 migration-guard (`final-gates.sh --run migration-guard`) · 종결 = 2026-08-10 backtest-submit-fix

**원인 / 영향:** 두 케이스가 red 다.

- `e2e/sprint46-tier1-critical.spec.ts:69` — `#1 Backtest form — 422 unsupported_builtins UL hint → fix → submit success`
- `e2e/sprint46-tier3-nth.spec.ts:489` — `#20 Backtest form — 422 friendly_message 카드 (BL-163)`

★**내 회차 탓이 아님을 실측으로 갈랐다.** migration-guard 브랜치는 `frontend/` **0줄** ·
`backend/src` **0줄**인데 `e2e authed` 가 FAIL 했다. `git checkout main` 후 같은 두 케이스만
`--grep` 으로 돌렸더니 **main 에서도 정확히 그 2건이 red**(1 passed)였다. ⇒ 선재.

★**게이트 구조상 이것이 지금 모든 회차를 막는다.** `final-gates.sh:220` 은 `e2e authed` 를
**`has_fe` 와 무관하게 항상** 돌린다(`e2e chromium` 만 `frontend diff 0` 이면 skip). 따라서
FE 를 한 줄도 안 건드린 회차도 rc=1 을 받고 「PR 을 만들지 마라」를 본다.
그 상태가 계속되면 **게이트를 무시하는 습관**이 생기고, 그때 진짜 red 가 섞여 들어온다.

**권장 접근:** 먼저 두 케이스가 무엇을 기대하는지 확인해라 — 실패 지점은
`sprint46-tier3-nth.spec.ts:553-554` 의 `expect(friendly).toContainText(/Trust Layer 위반|ADR-003/)`
이다. 즉 **422 응답 본문의 문구**를 재는 케이스이므로, 원인 후보는 ⑴ 백엔드 422 메시지가 바뀌었다
⑵ FE 카드 렌더가 바뀌었다 ⑶ 픽스처 전략의 Pine 소스가 더 이상 그 422 를 안 낸다 셋이다.
`test-results/.../error-context.md` 와 trace(zip)가 남아 있으니 **먼저 그것을 열어라** —
재현부터 다시 만들지 마라.
★**고치기 전에 언제부터 red 인지 이분해라.** 그래야 「무엇이 바꿨나」가 나온다.

★**부수 관측 — `e2e design-canon` 은 불안정하다.** 같은 브랜치·같은 커밋에서 `final-gates.sh` 를
두 번 돌렸는데 **1회차 PASS · 2회차 FAIL** 이었고, 곧바로 `pnpm e2e:design-canon` 을 단독으로
돌리자 **42 passed** 였다. `frontend/` 0줄인 브랜치이므로 코드 원인이 아니다. 위 422 두 건과 달리
**재현되지 않는다** — 두 축을 같은 항목으로 묶어 보지 마라. 후보: authed 스위트와의 간섭 ·
dev server(:3100) 상태 · 브랜치 스위칭 후 `.next` 캐시([BL-650] 과 같은 계열).
★**이 축을 먼저 쫓지 마라** — 재현이 안 되는 쪽보다 **항상 red 인 422 두 건**이 값이 크다.

**Risk:** 🟡 (게이트가 상시 붉으면 게이트가 아니다. 단 프로덕션 경로 결함인지 테스트 결함인지 아직 모른다)

---

#### ✅ 종결 (2026-08-10 backtest-submit-fix) — **프로덕션 결함이었다**

**근본 원인.** `<form id="backtest-setup-form">` 에 `noValidate` 가 없어 native constraint validation 이
살아 있는데, 비용 필드 두 개의 기본값이 자기 `step` 격자를 어긴다:

| 필드           | 기본값    | `step`     | `validity.stepMismatch` |
| -------------- | --------- | ---------- | ----------------------- |
| `fees_pct`     | `0.00055` | `"0.0001"` | **true**                |
| `slippage_pct` | `0.00014` | `"0.0001"` | **true**                |

폼이 constraint-invalid 이면 브라우저는 **submit 이벤트를 발화조차 하지 않는다.** 제출 버튼이
`<form>` **밖**(요약 aside)에 `form={id}` 로 붙어 있어 native 경고 UI 조차 안 뜬다. ⇒ `handleSubmit`
도, `onSubmit` 도, `create.mutate` 도, 토큰 획득도 **전부 안 돈다.** 그래서 증상이 「422 가 아니라
요청이 아예 안 나감」이었다.

**회귀 시점 = `753f4bf6`** (2026-08-07, [BL-603] "narrow default cost assumptions").
`fees 0.001→0.00055` · `slippage 0.0005→0.00014` 로 좁히면서 Sprint 31 이래의 `step="0.0001"` 은
그대로 뒀다. 종전 기본값 `0.0005` 는 격자에 맞아 통과했다. **`0.00055` 로 좁히는 순간 죽었다.**

**수정 (프로덕션 3줄, `frontend/**`만 ·`backend/src`0줄):**`<form>`에`noValidate`+`fees_pct`·`slippage_pct`를`step="any"`. 범위 검증은 RHF `validate`(0~0.01)가 이미 이중화하고 있다.

★**원장이 적어 둔 「권장 접근」은 틀렸다.** 실패 지점을 `sprint46-tier3-nth.spec.ts:553-554` 의
**문구 assertion** 이라 적었으나, 실제 실패는 그보다 앞선 `tier1:124` 의
`page.waitForRequest(POST /api/v1/backtests)` **15초 타임아웃**이다. 문구는 애초에 도달하지 않는다.
⇒ 「응답 본문이 바뀌었나」 3후보(BE 422 메시지 / FE 카드 렌더 / 픽스처 Pine)는 **전부 무관**했다.

★**기존 단위 테스트 17건이 왜 못 잡았나.** 전부 `fireEvent.submit(form)` 으로 submit 이벤트를 **직접
디스패치**한다 — native validation 을 통째로 우회하는 경로다. 사용자가 밟는 `click` 경로를 재는
케이스가 **하나도 없었다**. 신설 3건은 `fireEvent.click(getByTestId("backtest-submit"))` 을 쓴다.

**변이 3종 전건 판별력 확인** — M1(step 되돌림) → T2 red · M2(`noValidate` 제거) → T3 red ·
M3(둘 다) → T1·T2·T3 red. 두 수정은 제출 경로에 대해 **의도적 중복 방어**라 단일 변이는 한쪽만 죽인다.

**검증:** vitest 1346/1346 · `tsc --noEmit` · `eslint` · `e2e:authed` red 3건 → **전건 green**(1회 소모).
신설 테스트 **결정론 20/20**.

**남긴 것:** 같은 클래스의 잠복 결함 → [BL-699]. 반증 카드 → [LESSON-097]·[LESSON-098].

---

### BL-699

**Title:** RHF 폼 6개에 `noValidate` 가 없다 — [BL-698] 과 같은 클래스의 **잠복** 결함
**Category:** Frontend / 폼 검증
**Priority:** P3
**Trigger:** 그 6개 폼 중 하나의 **기본값이 native 제약(step/min/max)을 어기는 순간** — 그때 제출이 조용히 죽는다
**Est:** S (1-2h · 폼당 `noValidate` 1줄 + 클릭 경로 테스트)
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 backtest-submit-fix 에서 전수 스캔. **현재 활성 결함 0건.**
**트리거 판정:** 미도래 — 6개 전건의 현재 기본값이 자기 제약 격자 안에 있음을 실측 확인 (2026-08-10 backtest-submit-fix)
**출처:** 2026-08-10 backtest-submit-fix ([BL-698] 수리 중 부수 발견)

**원인 / 영향:** [BL-698] 은 「기본값이 `step` 격자를 벗어나면 브라우저가 submit 이벤트를 발화조차
하지 않는다」는 결함이었다. 그 조건의 **전건**은 `<form>` 에 `noValidate` 가 없는 것이다.
실측 — 이 레포 RHF 폼 **9개 중 `noValidate` 는 3개뿐**이다:

| `noValidate`                                     | 폼                                                                                                                                                                     |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 있음 (3, + BL-698 로 추가된 `backtest-form` = 4) | `waitlist-form-card` · `test-order-dialog` · `alert-rule-form`                                                                                                         |
| **없음 (6)**                                     | `optimizer/{genetic,grid,bayesian}-search-form` · `strategies/[id]/edit/tab-metadata` · `live-sessions/live-session-form` · `trading/register-exchange-account-dialog` |

★**지금 붉지 않다.** 6개의 native 제약을 전수 확인한 결과 전부 `step="any"` 이거나 정수 step +
정수 경계라 기본값이 격자 안이다. 즉 **잠복**이지 발현이 아니다 — 그래서 ACTIVE 가 아니라 DEFERRED
([ADR-028](decisions/028-backlog-deferred-verdict.md)).

★**위험은 「지금 틀렸다」가 아니라 「조용히 틀려진다」다.** [BL-698] 은 폼 코드를 한 줄도 안 건드린
커밋(`753f4bf6` — 기본값 상수만 좁혔다)이 만들었고, **212 커밋 동안 아무 게이트도 못 잡았다.**
같은 일이 이 6개에서 일어나면 증상은 또 「버튼을 눌러도 아무 일이 없다」이고, 로그도 에러도 없다.

**권장 접근:** 폼당 `noValidate` 1줄. 단 **넣기 전에** 그 폼의 native `min`/`max`/`required` 가
RHF rule 로 이중화돼 있는지 확인해라 — 이중화가 없으면 `noValidate` 는 검증을 **없애는** 것이 된다
([BL-698] 은 전건 이중화돼 있어 잃는 것이 0 이었다). 함께 각 폼에 **클릭 경로**(`fireEvent.submit`
아님) 테스트 1건씩.

**영향 파일:** 위 표의 6개 + 각 테스트.

**Risk:** 🟢 (선제 조치. 단 RHF 이중화 확인을 건너뛰면 검증을 지우는 변경이 된다)

---

### BL-700

**Title:** FE 헤더 주석과 `"use client"` 의 순서 관례가 두 갈래로 갈려 있다
**Category:** Frontend / 컨벤션
**Priority:** P3
**Trigger:** `frontend/AGENTS.md` 를 손댈 회차 — 관례를 문서로 고정할 때 함께 처리한다
**Est:** XS (문서 1줄 + 필요 시 정렬)
**상태:** ⏳ **대기 (트리거 미도래)** — 2026-08-10 bl-307-header-lint 에서 발견. **둘 다 합법이고 게이트는 양쪽 다 통과한다** — 지금 고장난 것은 없다.
**트리거 판정:** 미도래 — 동승 트리거(`frontend/AGENTS.md` 를 여는 회차). 단독 착수 시 값이 0이다 (2026-08-10 bl-307-header-lint)
**출처:** 2026-08-10 bl-307-header-lint (`/code-review` Spec 축 (b)2)

**원인 / 영향:** [BL-307] 이 헤더를 첫 3줄에 넣으면서 `"use client"` 와의 상대 순서를 정해야 했다.
실측 — 레포에 **두 관례가 이미 공존**한다:

| 관례                          | 표본                                                  |
| ----------------------------- | ----------------------------------------------------- |
| 주석 → `"use client"`         | `waitlist-filter-bar` · `waitlist-stats-strip` (다수) |
| `"use client"` → 빈 줄 → 주석 | `waitlist-admin-view` · `components/ui/*` 6건         |

[BL-307] 은 **다수 쪽(주석 먼저)**으로 통일했다. Next.js 는 지시문 앞에 주석만 있으면 합법이라
둘 다 동작하고, `header-audit` 은 3줄 창 안이기만 하면 양쪽을 통과시킨다.

**권장 접근:** `frontend/AGENTS.md` 에 한 줄로 고정하고(권장 = 주석 먼저), 어긋난 파일은
**그 파일을 다음에 열 때** 맞춘다. 일괄 정렬은 값에 비해 diff 가 크다.

**영향 파일:** `frontend/AGENTS.md` 1 + (동승) 해당 컴포넌트.

**Risk:** 🟢 (순수 컨벤션. 동작 영향 0)

---

### BL-701

**Title:** soak-gate C1 판정식이 [ADR-024] 의 새 문턱(24h 창 3회)을 반영하지 않는다
**Category:** Ops / soak gate (판정식)
**Priority:** P1
**Trigger:** 즉시
**Est:** M (판정식 + 하네스 + 음성 대조)
**상태:** ✅ **Resolved** (2026-08-11 bl-701-c1-window-count) — `soak_gate_predicate.py` 가 `DEFAULT_REQUIRE_WINDOWS = 3` 과 **자격 창 셈**을 갖고, 판정 문구·`soak-gate.sh` 출력이 **문턱을 하나만** 말한다(`C1 24h 창 1 / 3회 (참고: 누적 69.14h)`). [ADR-024] §판정 술어 표와 §C1 의 🔴 도 함께 닫았다. 변이 **8/8 red** · 음성 대조 = **23.9h 창 3개(합 71.7h) → 0/3**. 테스트 58 → **68** · soak-watch 하네스 14 → **17**. ★★**codex 적대 리뷰가 P1 을 잡았다** — 초판이 커버리지 조각을 그대로 세어 **단일 74h 실행이 3회로 위조**됐다(측정이 나쁠수록 점수가 오르는 fail-open). 자격 창을 **귀속 구간당 최대 1개**로 고쳤다. ★**부수 발견 — 이 수리가 무인 감시를 죽일 뻔했다**: `soak-watch.sh:246` 이 크래시 판별 앵커를 `C1 누적` **문자열**에 걸어 놨고, 그 하네스 픽스처는 옛 서식의 얼린 캡처라 **초록인 채로** 매 실행이 「게이트 크래시」가 됐을 것이다 ⇒ 앵커를 라벨(`C1`)만 잡게 고치고 신 서식 픽스처 + 케이스 ⑪ 추가
**트리거 판정:** ~~도래 — 선행([ADR-024] 문턱 교체 결정)이 2026-08-11 에 닫혔고 코드는 안 따라왔다 (2026-08-11 ledger-truth)~~
**출처:** 2026-08-11 ledger-truth (Q1 사용자 결정의 코드 잔여)

**원인 / 영향:** 2026-08-11 사용자 결정으로 C1 문턱이 **「누적 168h」 → 「≥24h 연속 무실격
창 3회」**로 교체됐다([ADR-024] §C1 의 `Superseded` 블록). 그런데 판정식은 안 바뀌었다 —
`backend/scripts/soak_gate_predicate.py` 와 [ADR-024] §판정 술어 표가 여전히 `C1 ≥ 168h` 다.
⇒ `scripts/soak-gate.sh` 는 지금 **`C1 누적 56.4197h / 168h (33.6%)`** 를 찍는데, 새 문턱으로
읽으면 **C2 41.1057h 로 1/3 달성**이다. **같은 게이트가 두 문턱을 동시에 말한다.**

★**이게 왜 P1 인가** — P0 [BL-003] 의 종료 조건이 여기 걸려 있다. 문서만 고친 상태로 두면
다음 회차는 게이트 출력(`/168h`)을 그대로 읽고 **「아직 33.6% 다」**로 판단한다. 이 회차가
고치려던 병(원장이 다음 회차를 잘못 이끈다)이 **판정식 층에서 재발한 것**이다.

**권장 접근:** ⑴ `soak_gate_predicate.py` 에 「≥24h 창 달성 횟수」를 산출하는 술어를 추가한다
— 기존 귀속 창 목록(`attribution`)에서 길이 ≥24h 인 창을 세면 되고 새 저장소가 필요 없다.
⑵ 판정 출력에 **두 문턱을 함께 찍지 마라** — 어느 쪽이 정본인지 모르게 된다. 새 문턱만 찍고
옛 값은 `(참고)` 로 내린다. ⑶ **음성 대조 필수** — 창 3개가 각각 23.9h 이면 **0/3** 이어야
한다(합이 71.7h 라서 「누적 168h」식 셈으로는 그럴듯해 보인다). ⑷ N=3 은 `[가정]`이므로
상수로 빼고 ADR 을 가리키는 주석을 달아라.

**영향 파일:** `backend/scripts/soak_gate_predicate.py` · `scripts/soak-gate.sh`(출력) ·
[ADR-024] §판정 술어 표 · `generator-evaluator-pipeline.md` §G1.1(판정식 정본).

**Risk:** 🟡 (P0 의 종료 조건을 바꾼다 — 반쪽이면 게이트가 두 문턱을 말한다)

---

### BL-704

**Title:** `/metrics` fail-closed 를 지켜 주는 것이 실배포 호스트에는 없다 — 부팅 가드가 `app_env=production` 만 본다
**Category:** Backend / observability (설정 가드)
**Priority:** P2
**Trigger:** 즉시
**Est:** S
**상태:** ✅ **Resolved (2026-08-11 metrics-boot-log)** — 권장 접근 ⑴⑵ 이행. `lifespan()` 이 `metrics_auth=enabled|DISABLED app_env=…` 1줄을 **모든 환경에서** 찍는다(부팅은 안 막는다). 판정은 `_metrics_auth_token()` 하나를 엔드포인트 가드와 공유해 로그와 실제 동작이 갈라질 수 없다. ⑶(노출 판정을 바인딩·프록시로 이관)은 잔여 — 아래 참조
**트리거 판정:** 도래 — fail-closed 전환이 머지되는 순간부터 이 공백이 실재한다 (2026-08-11 ledger-truth)
**출처:** 2026-08-11 ledger-truth (Opus 콜드 평가자 ① 정확성 렌즈 P1)

**원인 / 영향:** `_verify_prometheus_bearer` 가 이제 토큰 미설정 시 **401** 이다. 이 전환을
「안전하다」고 판단한 근거는 `core/config.py:396-405` 의 production validator 였는데, 그 가드는
`:369` 의 **문자열 비교**(`app_env != "production"` 이면 early-return)에 걸려 있고 `:367` 이
staging 을 명시 면제한다. **이 레포의 실배포 호스트는 `APP_ENV` 를 아예 설정하지 않아 기본값
`development`(`config.py:33`)로 돈다**(`frontend-deploy.md:13`) ⇒ 부팅 가드의 보호를 **안 받는다.**

**2026-08-11 실측 (서버 `.env.local`):** `APP_ENV=` **없음** · `PROMETHEUS_BEARER_TOKEN`
**설정됨(비어 있지 않음)**. ⇒ **오늘 스크레이프는 깨지지 않는다.** 그러나 그것을 보장하는 것은
**운영자의 손**이고 부팅 시점에 검사하는 것이 없다 — 재프로비저닝에서 그 줄을 빠뜨리면
`/metrics` 는 **조용히 401** 이 되고 부팅은 성공한다.

★**이 항목의 값은 「고치는 것」보다 「거짓 안심을 지운 것」에 있다.** 종전 코드 주석과 설정
description 이 「production 에서는 토큰이 항상 있으므로 이 분기는 발화하지 않는다」를 단언하고
있었고, 그 문장이 **오케스트레이터가 워커에게 준 전제**였다. 문구는 2026-08-11 에 정정했다
(`main.py` docstring · `config.py` Field description).

**권장 접근:** ⑴ startup 로그에 「`/metrics` 인증: 활성/**비활성**」 1줄을 찍어 배포 직후 눈으로
확인 가능하게 한다(부팅을 막지 않으므로 dev 를 안 깬다). ⑵ 음성 대조 — 토큰을 지우고 부팅해
그 줄이 「비활성」으로 바뀌는지 본다. ⑶ 더 나아가려면 노출 판정을 `app_env` 문자열이 아니라
바인딩·프록시 설정으로 옮긴다.

**2026-08-11 종결 근거:**

- **로그는 `app_env` 로 감싸지 않는다.** 감싸는 것이 이 항목의 병이다 — 실배포 호스트가
  `APP_ENV` 미설정이라 **보호를 가장 못 받는 환경이 경고도 못 받는다.** `app_env` 는
  조건이 아니라 **찍는 값**이다. 회귀 핀 = `test_boot_warns_regardless_of_app_env`
  (development / staging / production 3종 파라미터라이즈).
- **테스트는 lifespan 을 실제로 태운다** — 로그 문장을 만드는 헬퍼를 직접 부르면
  「그 함수」만 재고 배선을 못 잰다([LESSON-092] §2). 수집은 **`yield` 안**에서 한다:
  컨텍스트를 나온 뒤에 세면 그 줄을 **shutdown 으로 미루는 변경이 초록**으로 샌다(실측).
- **부수 발견 — `frontend-deploy.md` §4 의 검증 절차가 이 결함을 못 갈랐다.**
  `curl … /metrics # 401` 은 fail-closed 전환 이후 「보호 중」과 「토큰 누락 = 관측 상실」을
  **동시에** 뜻한다. 판별자가 없었다 ⇒ 부팅 로그 확인 1줄을 §4 에 넣고 §5 에 이유를 적었다.

**변이 4종 (스냅샷 되쓰기 + sha256 · 지목 케이스로 판정):**

| 변이                                                  | 죽은 케이스                                                                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 로그를 `if not settings.is_production:` 로 감쌈       | `regardless_of_app_env[development]`·`[staging]` red · **`[production]` 은 초록** ← 축이 정확히 `app_env` 임을 증명 |
| 로그가 `token is not None` 이라는 **2벌째 술어**를 씀 | `treats_empty_token_as_disabled` **1건만**                                                                          |
| 엔드포인트를 fail-open 으로 되돌림                    | `metrics_401_when_token_unset` · `metrics_401_when_token_empty_string`                                              |
| 로그를 `yield` 뒤(shutdown)로 미룸                    | 부팅 로그 6/7 (부팅 성공만 재는 1건은 생존 — 옳다)                                                                  |

★**등가 변이 1건을 기록한다** — `_metrics_auth_token()` 의 `or None` 을 지워도 **아무것도
안 죽는다.** `""` 는 어차피 falsy 라 두 호출부가 같게 동작하기 때문이고, 이것은 커버리지
구멍이 아니라 **의미상 같은 변이**다. 「red 가 안 났다」를 무조건 구멍으로 읽지 마라.

**잔여:** 권장 접근 ⑶ — 노출 판정을 `app_env` 문자열이 아니라 **바인딩·프록시 설정**으로
옮기는 것. 이번 S 범위 밖이고, 그것을 하려면 배포 토폴로지(Cloudflare Access·컨테이너 포트
공개 범위) 결정이 선행한다.

**Risk:** 🟡 (조용한 관측 상실. 지금은 토큰이 있어 미발동)

---

### BL-705

**Title:** skip 래칫의 스코프 하한이 합계라 한쪽 스코프가 통째로 빠져도 초록이다 + 스캔층 자기검사 부재
**Category:** Ops / 게이트 (판별력)
**Priority:** P2
**Trigger:** 즉시
**Est:** S
**상태:** ✅ **Resolved (2026-08-11 skip-ratchet-scope)** — 권장 접근 ⑴~⑷ 전건 이행 + 신설 하네스 11/11. 하한을 스코프별(`backend/tests` 350 / `backend/src` 150 = 실측 505·217 의 70% 선)로 바꾸고 스코프 경로 부재를 따로 판정한다. 스캔을 `scan(root)` 으로 분리하고 `scripts/skip-ratchet-test.sh` 가 임시 트리로 그 층을 태운다
**트리거 판정:** 도래 — 게이트가 이미 `final-gates.sh` 에 배선돼 돌고 있다 (2026-08-11 ledger-truth)
**출처:** 2026-08-11 ledger-truth (Opus 콜드 평가자 ③ 빈입력초록 렌즈 P1 ×2)

**원인 / 영향:** `scripts/skip-ratchet.sh` 의 하한 판정이 **두 스코프 합계**(`files < MIN_FILES`)다.
`os.walk` 는 없는 디렉터리에서 조용히 0 을 내므로, 위반이 사는 `backend/tests`(505 파일)가
**통째로 안 스캔돼도** `backend/src`(217)가 200 을 넘겨 「위반 0건 ✓ rc=0」이 된다(평가자 실측).
`TARGETS` 두 항목 중 **하나만** 오타 나면 발화한다.

★**자기검사가 스캔층을 전혀 덮지 않는다** — 입력이 「한 줄 문자열과 정수 둘」이라
`TARGETS`·확장자 필터·hit 수집이 **무검증**이다. 실측 — 자기검사를 `if False:` 로 막고 정규식까지
무력화하면 **rc=0**. 신설 시 「하네스를 따로 두면 또 하나의 고아 스크립트가 된다」는 이유로 별도
`-test.sh` 를 뺐는데, **스캔층은 파일 트리 fixture 없이는 검사할 수 없다** — 그게
`bl-audit-test.sh`·`header-audit-test.sh` 가 임시 트리를 쓰는 이유다. 그 판단이 반증됐다.

**권장 접근:** ⑴ `MIN_FILES` 를 **스코프별 하한**으로(실측 tests 505 / src 217 의 70% 선).
⑵ 스캔을 함수로 빼고 `scripts/skip-ratchet-test.sh` 에서 임시 트리로 돌린다 — 한쪽 스코프만
삭제 → rc=3 · 위반 1건 → rc=1 · 무변화 → rc=0 · **양성 대조**(일치 시 침묵). ⑶ `MIN_FILES=200` 은
실측 722 의 27.7% 라 파일 72% 손실까지 초록이다 — 함께 올린다. ⑷ `QB_SKIP_RATCHET_ROOT` 가
설정돼 있으면 출력에 찍어라(셸 잔여 export 하나가 판정 대상 트리를 조용히 갈아치운다).

**이미 닫은 것 (같은 회차, 변이로 rc=1 확인):** 주석 꼬리 bare `@pytest.mark.skip` ·
`pytestmark = pytest.mark.skip(...)` 모듈 레벨 — 둘 다 **오늘 당장 쓸 수 있는 우회**였다.
★남은 형태 하나 — 함수 몸통 안 `pytest.skip("…")` 인라인(`tests/real_broker/test_webhook_to_filled_e2e.py:97`).
래칫은 「무조건 skip」을 **선언 형태**로 정의하므로 규정 위반은 아니지만, 「부채 0」이라고
말할 수 있는 범위는 그보다 좁다.

**2026-08-11 종결 근거 (재현 → 수리 순서로 실측):**

- **재현** — 하네스를 수리보다 **먼저** 써서 수리 전 스크립트에 대고 돌렸다(G1 동결). 케이스
  ④가 `스캔 200건 (backend/tests 0 / backend/src 200) … ✓ 무조건 skip 0건 rc=0` 을 냈다.
  **원장이 적은 그 거짓 초록이 출력 그대로 재현됐다.** ⑤(반대 축)·⑥(경계)·⑨도 red.
- **변이 5종** — ①스코프별→합계 되돌림 ②스캔층이 없는 스코프를 하한으로 메움 ③확장자 필터
  제거 ④데코레이터 정규식 제거 ⑤자기검사 2종 무력화. 복원은 **스냅샷 되쓰기 + sha256 대조**.
- ★**변이 ①④는 자기검사가 먼저 물어 8/11 이 죽었다 — 「아무튼 실패」라 판별력 측정이 아니다.**
  그래서 스캔층만 겨냥한 변이 ②를 따로 심었고 **정확히 ④⑤만** red 가 됐다. 변이 ③은 ①⑥⑦⑧,
  변이 ⑤는 ⑩⑪ 만. **지목한 케이스가 죽는지**로 재야 판별력이 나온다.
- ★★**변이 ⑤가 새 사각을 드러냈다** — 자기검사 2종을 통째로 무력화해도 **게이트 rc=0 · 하네스
  9/9 초록**이었다. 자기검사는 정상 상태에서 절대 발화하지 않으므로 **그것을 지우는 변경은
  아무도 못 잡는다.** ⇒ 케이스 ⑩⑪(래칫 **사본**에 변이를 심어 「자기검사가 실제로 우는가」를
  behavioral 로 잰다)을 추가해 닫았다. 재실행 시 변이 ⑤는 **⑩⑪ 만** red 다.
- **미끼가 없으면 무증거다** — 「확장자 필터 제거」 변이는 fixture 에 `*.py` 아닌 파일이
  없으면 아무 케이스도 안 죽인다. 그래서 위반 문자열을 **줄 맨 앞**에 품은 `notes.md` 를
  fixture 에 심었다.

**잔여 (이 항목 밖):** ⑴ 함수 몸통 안 `pytest.skip(...)` 인라인은 여전히 정의 밖이다.
⑵ 기본 ROOT 파생(`dirname $0/..`) 갈래는 하네스가 env 로 트리를 주입하므로 안 덮는다 —
`final-gates.sh` 의 실물 게이트 실행(인자·env 없음)이 매번 덮는다.

**Risk:** 🟡 (새 게이트가 조용히 눈이 멀 수 있다)

### BL-706

**Title:** `final-gates` 신호 4종이 신선도를 안 봐 **남의 회차 파일로 초록**이 난다 — 게다가 문서가 시키는 명령이 그걸 만든다
**Category:** Ops / 게이트 (판별력)
**Priority:** P1
**Trigger:** 즉시
**Est:** S
**상태:** ✅ Resolved (2026-08-11 gate-freshness) — 처방 ⑴+⑵+⑷ 구현: `scripts/signal-check.sh`(첫 줄 `commit: <sha>` 를 merge-base(origin/main,HEAD)..HEAD 범위와 대조, merge-base 실패는 rc=3 abort) + `final-gates.sh` 의 `--run eod` 인자 거부(문서 규율이 아니라 스크립트가 막는다) + 하네스 25케이스·변이 13종. ⑶(재사용 경고)은 ⑴ 이 있으면 잉여라 기각. 실물 대조 — eod 낡은 신호 4종이 이제 `missing[commit-line]` FAIL 이고, origin/main sha 는 `stale[origin-main]`, HEAD/브랜치 커밋은 `signal[head]`/`signal[branch]` 다.
**트리거 판정:** 도래 — 게이트가 매 회차 마감에서 이미 돌고 있고, 실측으로 4종 전부가 남의 회차 파일로 통과했다 (2026-08-11 gate-surface)
**출처:** 2026-08-11 gate-surface (`final-gates.sh --run eod` 결과를 대조하다 발견)

**원인 / 영향:** `check_signal()`(`scripts/final-gates.sh:307-317`)의 판정은 **`[ -s "$f" ]`
하나**다 — 파일이 존재하고 비어 있지 않으면 PASS. **누가·언제·무엇에 대해** 썼는지를 보지 않는다.

그리고 그 파일이 사는 곳은 `GATEDIR="$ROOT/.claude/gates/$RUN"`(`:60`)인데, **`docs/status.md:112`
가 회차 마감 명령으로 `scripts/final-gates.sh --run eod` 를 못 박고 있다.** 즉 문서를 그대로
따르는 모든 회차가 **같은 디렉터리**에 착지하고, 앞 회차가 남긴 신호를 그대로 물려받는다.
★**사용자 실수가 아니라 문서가 만드는 구조적 사고다.**

**2026-08-11 실측** (`.claude/gates/eod/` mtime):

| 신호        | mtime       | 쓴 회차      |
| ----------- | ----------- | ------------ |
| `vercel.ok` | 08-11 02:53 | ledger-truth |
| `codex.ok`  | 08-11 03:05 | ledger-truth |
| `screen.ok` | 08-11 11:27 | 다른 회차    |
| `g9.ok`     | 08-11 11:39 | 다른 회차    |

gate-surface 회차는 **이 넷 중 무엇도 수행하지 않았는데** 결과표에 `PASS … signal: codex.ok`
4줄이 찍혔다. 특히 `screen.ok` 는 프롬프트가 「3회차 연속 미취득이니 **비어 있지 않은 파일
하나로 초록을 만들지 마라**」고 경고한 바로 그 신호인데, **이미 있는 파일이 정확히 그 일을
하고 있었다.**

★**증거는 파일 안에 있었다.** `eod/g9.ok` 의 첫 줄은 `# G9 — 계획 vs 실제 구현 (2026-08-11
ledger-truth)` 다 — 파일 **자신이** 어느 회차 것인지 적고 있는데 검사기가 크기만 봤다.
「검사기가 보는 표면 < 실제 실패 표면」의 또 한 사례다(같은 회차의 [BL-705]·[BL-704] 와 동류).

★`.claude/*` 는 `.gitignore:16` 이라 **git 이 증인이 아니다** — 신선도를 git 이력으로 되물을 수 없다.

**무엇이 위험한가:** 이 넷은 자동화가 아니라 **사람·에이전트의 판단**을 요구하는 게이트다
(적대 리뷰 · 실제 화면 · 계획 대비 구현). 자동 게이트는 회귀하면 red 가 나지만, 이 넷은
**수행하지 않아도 red 가 안 난다.** 회차가 「전건 초록」을 보고하는 근거의 4/4 가 남의 것일 수 있다.

**권장 접근:**

1. **신호에 대상 커밋을 요구하고 대조한다** — 파일 첫 줄에 `commit: <sha>` 를 의무화하고
   `check_signal()` 이 현재 `HEAD`(또는 `merge-base origin/main HEAD` 이후)와 대조한다.
   신호는 「무엇을 검증했는지」를 말해야 한다. 크기 검사보다 강하고, 재실행 시 자동 무효화된다.
2. **`--run eod` 관용구를 회차 슬러그로 바꾼다**(`docs/status.md:112` · `gates-and-traps.md`).
   이름이 겹치지 않으면 물려받을 파일도 없다. **⑴ 없이 ⑵만 하면 규율에 의존하는 처방**이라
   이 레포가 반복 실패한 형태다(LESSON-078) — ⑵는 보조다.
3. **이미 신호가 있는 run 디렉터리를 재사용하면 최소 경고**, 대조 실패 시 FAIL.
4. **하네스로 판별력을 증명한다** — `docs-audit-test`·`skip-ratchet-test` 와 같은 임시 트리:
   신선한 신호 → PASS · **낡은 신호(다른 sha) → FAIL** · 없는 신호 → FAIL(현행 유지).
   ★**낡은 신호가 FAIL 이 되는 케이스가 이 BL 의 본체다** — 그것이 없으면 수리가 무증거다.

**Risk:** 🟠 (회차 종료 판정 4축이 조용히 거짓 초록. 프로덕션 코드는 아니지만 **모든 회차의
「끝났다」 판정**이 여기 걸린다)

★★**종결 기록 (2026-08-11 gate-freshness).** 하네스를 수리보다 먼저 동결하고(케이스 25 · red
기대 16), 행위 불변 추출본에 돌려 `red = [③④⑦⑨⑩⑪⑫⑬⑭⑮⑲⑳㉒㉓㉔㉕]` 16/25 를 **글자
그대로** 재현한 뒤 수리해 25/25 green + 변이 13종 기대 집합 정확 일치(M9=⑨㉕). 처방 ⑴ 은
G1 codex 플랜 검증의 [치명적] finding 으로 한 번 강화됐다 — merge-base 의 **모든** 실패를
축약 판정으로 뭉개면 깨진 origin/main 에서 `sha==HEAD` 초록이 새므로, ref 부재(축약 판정 +
stderr 경고)와 merge-base 실패(rc=3 abort)를 가른다. 부수 실측 2건 — ⑴ /bin/bash 3.2 는
**명령 치환 안 quoted heredoc** 에서 달러+작은따옴표 인접의 달러를 삼킨다(하네스 앵커 검사가
이것 때문에 x0 이 됐고, 생성자가 훼손 앵커에 맞춘 미끼 주석으로 통과시키는 사고까지 겹쳤다 —
처방: heredoc 을 $( ) 밖 평명령+리다이렉트로) ⑵ `docs/status.md` ⓸ ④ 의 `--run eod` 관용구가
사고의 뿌리라 `--run <회차슬러그>` + 신호 첫 줄 규약으로 교체. `gates-and-traps.md` 에는 eod
관용구가 **없었다** — 본문 처방 ⑵ 의 그 지목은 과대였다.

### BL-702

**Title:** ⓪ 표 정체성 계약에 소유자가 없다 — 살아 있는 행이 원장과 갈려도 게이트가 침묵한다
**Category:** Docs / 게이트 (진입점 정합)
**Priority:** P1
**Trigger:** 즉시
**Est:** S
**상태:** ✅ **Resolved (2026-08-11 ledger-truth)** — `docs-audit.sh` 에 `zero_table_identity` 축 신설 + `scripts/docs-audit-test.sh` 하네스 4/4 + `final-gates.sh` 배선.
**트리거 판정:** 도래 — ⓪ 표 자신이 「이 계약에는 아직 소유자가 없다」를 적어 도래를 선언했다 (2026-08-11 ledger-truth)
**출처:** 2026-08-10 status-table-resync (⓪ 표 서문이 직접 후속을 지목)

**원인 / 영향:** 종전 `docs-audit` 의 ⓪ 표 축은 **행 수 ≥3** 하나뿐이었다. 그래서 종결된
[BL-698]·기각된 [BL-306] 이 **살아 있는 행**으로 남아, 표를 그대로 읽으면 **닫힌 결함이
★★★ 최상위 추천**으로 보이는데도 게이트는 초록이었다. ⓪ 표 서문이 그 사고를 기록하며
「다음 회차가 BL 로 등록해 `docs-audit` 축으로 박아라」를 남겼다 — 이 BL 이 그것이다.

**처방 (구현됨):** 살아 있는 행의 BL id 집합 == `bl-audit --list ACTIVE` ∪ (PARTIAL ∧ 도래).

- **판정 SSOT 재사용** — `bl-audit.sh --list` 를 `subprocess` 로 되읽는다. 상태줄 파서를
  2벌로 만들지 않는다([BL-695] 가 세운 규약).
- **취소선은 후보 셀만 본다.** 행 전체로 재면 「왜 지금」 셀의 `~~정정 이력~~` 이 살아 있는
  후보를 죽은 것으로 읽는다 — 2026-08-11 의 행 **G** 가 정확히 그 형태였다.
- **양쪽이 비면 `rc=3` ABORT.** 빈 입력이 「일치」로 새는 것이 이 레포가 2026-08-10 에 **두 번**
  밟은 함정이다([LESSON-101]). 정상 레포에서는 이 경로가 절대 발화하지 않으므로
  **하네스만이 밟을 수 있다** ⇒ `docs-audit-test.sh` 가 실제로 발화시킨다.

★★**첫 실행에서 곧바로 실결함 1건을 잡았다** — 같은 회차가 [BL-701] 을 등재하고 ⓪ 표에
행을 안 넣었는데, 그걸 사람도 다른 게이트도 못 봤고 이 축이 잡았다.

★**하네스 4케이스** — ⑴ 양쪽 공집합 → rc=3 ⑵ 원장에만 있음 → 불일치 ⑶ 표에만 있음 → 불일치
⑷ **양성 대조**(일치 시 축이 **침묵**). ⑷ 가 없으면 상시 빨강인 검사기를 판별력 있다고 착각한다.

★**남는 한계 (정직하게)** — 취소선 판정은 후보 셀에 `~~` 가 **하나라도** 있으면 「죽었다」로 읽는다.
그래서 `~~` 를 **짝이 안 맞게** 쓴 행은 살아 있어도 조용히 빠진다. 실측으로 밟았다 — 이 축의
변이 시험 1차가 여는 `~~` 만 지웠는데 닫는 `~~` 가 남아 **게이트가 초록이었고, 그때 나는 게이트를
의심했다. 틀린 것은 변이였다.** 짝수 개 판정으로 좁힐 수 있지만, 짝이 안 맞는 `~~` 는 마크다운에서
리터럴로 **보이므로** 사람이 먼저 본다 ⇒ 지금은 이 한계를 문서로 둔다.

**Risk:** 🟢 (문서 게이트. 반쪽 머지는 CI red 를 부르므로 그날 마지막 PR 로 낸다)

---

### BL-703

**Title:** PARTIAL 24건이 `**트리거 판정:**` 줄을 갖지 않아 「PARTIAL ∧ 도래」가 구조적 공집합이다
**Category:** Docs / 원장 (판정 커버리지)
**Priority:** P1
**Trigger:** 즉시
**Est:** M (24건 판정 — 근거와 함께)
**상태:** ✅ **Resolved** (2026-08-11 bl-703-partial-verdicts) — PARTIAL **24/24** 에 근거를 붙인 `**트리거 판정:**` 줄을 넣었고(도래 5 · 미도래 19), `docs-audit.sh` 의 `trigger_verdicts` 축과 `bl-trigger-sweep.sh` 의 대상 집합이 **둘 다 PARTIAL 을 포함**한다. 하네스 `docs-audit-test.sh` 7/7(신규 3 = PARTIAL 도래/미도래/판정줄 누락). ⓪ 표에 **O~S 5행**이 올라왔다. ★착수 근거였던 「P0 1 + P1 4 가 올라온다」는 **반증됐다** — [BL-003]·[BL-619]·[BL-661] 은 실측으로 미도래이고, 대신 원장이 몰랐던 [BL-639]·[BL-672] 가 올라왔다
**트리거 판정:** ~~도래 — [BL-702] 가 술어를 넣었고 그 술어의 한쪽 입력이 비어 있음이 실측됐다 (2026-08-11 ledger-truth)~~
**출처:** 2026-08-11 ledger-truth ([BL-702] 구현 중 실측)

**원인 / 영향:** `**트리거 판정:**` 줄을 요구하는 두 자리가 **둘 다 PARTIAL 을 뺀다** —
`bl-trigger-sweep.sh:229` 는 `대상=ACTIVE` 이고 `docs-audit.sh` 의 `trigger_verdicts` 축은
`("ACTIVE", "DEFERRED")` 만 돈다. 그 결과 **PARTIAL 24건 중 그 줄을 가진 것이 0건**이다.

**실측 (2026-08-11 · 양성 대조 포함):**

| 판정어   | 건수 | `**트리거 판정:**` 줄 |
| -------- | ---- | --------------------- |
| ACTIVE   | 6    | **6**                 |
| DEFERRED | 155  | **155**               |
| PARTIAL  | 24   | **0**                 |

★**양성 대조가 이 0 을 사실로 만든다** — 같은 파서가 ACTIVE 6/6 · DEFERRED 155/155 를 찾았고
251 섹션 전량이 파싱됐다(미파싱 0). ⇒ 파서 결함이 아니라 **데이터 공백**이다.

★**무엇이 안 보이는가** — PARTIAL 안에 **P0 1건 + P1 4건**이 있다:
[BL-003] · [BL-438] (트리거가 `즉시` 다) · [BL-619] · [BL-641] · [BL-661].
[BL-702] 의 술어는 이들을 ⓪ 표에 올릴 준비가 돼 있지만, 판정 줄이 없어 **한 건도 안 올라온다.**

**권장 접근:** ⑴ `bl-trigger-sweep.sh` 의 `targets` 를 `ACTIVE ∪ PARTIAL` 로 넓힌다.
⑵ **기계 판정을 그대로 채택하지 마라** — 2026-08-10 에 그 판정기 초판이 5건을 근거 없이
「도래」로 올렸고 잡은 것은 전량 스윕이 아니라 **`--selftest` 음성 대조**였다. 기본값은
**「판단 필요」**다. ⑶ 24건을 근거와 함께 판정한 뒤 `docs-audit` 의 `trigger_verdicts` 축
대상에 `PARTIAL` 을 더한다(그 순서를 바꾸면 24건이 즉시 red 다).

**Risk:** 🟡 (P0·P1 5건이 진입점에서 안 보이는 상태가 유지된다)

---
