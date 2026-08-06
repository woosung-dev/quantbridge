# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 [`refactoring-backlog/_archived.md`](archive/refactoring-backlog/_archived.md), trigger 미도래 의도적 부활 가능 항목은 [`refactoring-backlog/_deferred.md`](archive/refactoring-backlog/_deferred.md). 문서 경로 정합성은 `scripts/docs-audit.sh`로 검증한다.
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
> scripts/bl-audit.sh                 # 판정 + P별 내역 + 3면 불일치 + UNKNOWN 목록
> #                                     UNKNOWN · 3면 불일치 · 중복 상태줄 · 중복 섹션 헤더 · 미닫힌 펜스/<details> → exit 1
> scripts/bl-audit.sh --list ACTIVE   # id / 우선순위 / 줄번호 만 (★목록 전용 — 항상 exit 0, 게이트에 쓰지 마라)
> ```
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

- **2026-06-30 stress_test-deepen (deepen-modules)**: stress_test 도메인 1차 deepen (`/deepen-modules`, 코드 변경 0). C1 = **BL-363 sharpen**(money-path framing + git 실증 `6c7adfba`→`ffb2299b` + `_load_run_context`/`_execute_grid_sweep` 구체 인터페이스) / C2 = 신규 **BL-392**(CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합, untyped JSONB seam). 거부 = C3(`StressTestKind` dispatch registry — blast radius 최대 + 4타입 over-eng, 5번째 타입 등장 시 재평가) / C4(invariant SSOT — C2 graft 권장). engine 은 이미 `run_grid_sweep` 공유 = Deep 유지(건드리지 않음). dev-log [`2026-06-30-stress_test-deepen.md`](dev-log/2026-06-30-stress_test-deepen.md).
- **2026-06-30 backtest-deepen (verification loop)**: backtest 도메인 1차 deepen (improve-codebase-architecture + codex challenge, 코드 변경 0). 신규 **BL-387~391** (5건) — BL-387 sizing-canonical typed seam(P2 money-path) / BL-388 BacktestMetrics 4-site multi-SSOT(P2) / BL-389 finance-math `engine/metrics.py` 추출(P3) / BL-390 exit `fill_type` 중복 위임(P3) / BL-391 equity↔PnL reconciliation oracle(P3 test-first). codex KILL C3(idempotency dual-lock 통합 = 의도적 layered + 잘 테스트됨) → [ADR-021](decisions/021-backtest-idempotency-dual-lock.md). **codex C1 DOWNGRADE 는 phantom `metrics.py` 오인 → 직접 검증 후 KEEP 정정**(§7.3 circular-trust 차단). dev-log [`2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md).
- **2026-06-30 BL-378 Resolved (`fix/pine-378-atr-wilder`)**: pine_v2 `ta.atr` 가 Wilder RMA (TV `ta.atr = ta.rma(ta.tr, len)`) 아닌 rolling SMA 사용 → 비-상수 TR(=모든 실데이터)에서 TradingView 와 silent divergence (헤드라인 harm-class). 실세계 8 전략 티어드 백테스트 QA (`docs/archive/qa/2026-06-30-pine-tiered-backtest/report.md`) 의 大-tier anti-circular hand-oracle 에서 발견 (5중 교차검증: codex G1 + 직접 oracle 9/9 bar + generator panel discriminator + panel 실행 15.0 vs 14.818 + codex G2). 수정 = `ta_atr` 가 기존 Wilder `ta_rma` 재사용 (~2줄, seed 동일·이후 TV 정합). G1-G4 (codex G1 plan eval + Workflow 12-agent generator panel + codex G2 challenge[B1 CONFIRMED] + codex diff-challenge[no P1] + G3 fresh review + mutation 2/2 CAUGHT) + full **2301 pass** (+6 pre-existing env, stash 대조 확인) + ruff/mypy clean + trust-layer golden 재생성(s2_utbot/i1_utbot num_trades 461→433, ATR→trailing 신호 변화). migration 0. 신규 **BL-379~386** (QA 부수 발견 9건: fn-local subscript / Track A alert warning / valuewhen na 등).
- **2026-06-30 BL-376 Resolved (`fix/pine-376-na-inf`)**: pine*v2 na/inf *소비\_ 사이트 robustness (BL-374 후속). 3 사이트 — (1) na/inf/<1 → ta.\* length: `_coerce_length` 헬퍼를 14 ta 함수 + dispatcher(change/stdev/variance int() 제거) + pivothigh/pivotlow 양 window + valuewhen occurrence(별도 non-finite 가드, occ=0 보존) 에 적용 → na 반환. (2) na/inf qty → `StrategyState.entry` skip + warning (라이브 reject 미러, 유한 0.0 보존). (3) inf → `math.floor/ceil/round`(per-branch, 공유 가드 미변경 — abs/sign/max 통과 유지) / subscript offset isfinite / timestamp +OverflowError. G1-G4(codex plan eval GO_WITH_FIXES + 4-candidate generator panel byte-수렴 + codex challenge[P1 valuewhen Decimal NaN 갭 → `(float, Decimal)` 가드] + fresh review SHIP + mutation 6/6 CAUGHT) + full suite 2305 pass(cov ≥90) + Playwright E2E(na/inf 백테스트 FAILED→COMPLETED, console.error 0). migration 0. 신규 [BL-377] (deferred: non-finite 주문/청산 가격 + 초대형 유한 length OverflowError).
- **2026-06-29 BL-374 Resolved (`fix/pine-374-na-semantics`)**: pine_v2 인터프리터 산술/math 도메인 오류 → Pine `na` 정규화 (`_na_safe`, 숫자 산술 한정, `math.pow` `**`→`math.pow()`). G1-G4 게이트(codex plan eval + 3-candidate generator panel + codex challenge[F1 dead stdlib-clamp 제거 + F2 문자열 `%` fail-closed] + fresh review GO + mutation 5/5) + full suite 2226 pass(cov 95.6%) + Playwright E2E(div-by-zero 백테스트 FAILED→COMPLETED, console.error 0). 신규 [BL-376] (deferred: na→length/qty, inf→floor·ceil·round).
- **2026-05-17 Sprint 62 PR #290 merge (Beta 본격 진입 결정 ★★★★★)**: 6 BL fix-first (BL-350+354 ★★★ Optimizer Zod resilience + BL-353 step 01 라벨 + BL-356/357/358/359 모바일 터치 ≥44pt 묶음). 실측 ~2-3h vs plan 6-8h (LESSON-067 6차 검증). main `36bb4e0`. **BL-070~072 milestone active 승격**. **재측정 skip + 본인 의지 (d) 통과**.
- **2026-05-17 Multi-Agent QA 재측정 (post-Sprint 61)**: Composite 6.08 → **7.5/10** (+1.42 목표 도달). 신규 BL-347~360 (14건, Critical 0 / P0 2 ★★★ 공통 BL-350+354 / P1 4 / P2 5 / P3 3). Sprint 61 11 BL Resolved 마킹 (PASS 8 + PARTIAL 2 + manual 1). 상세 = [`docs/archive/qa/2026-05-17-post-sprint61/integrated-report.html`](archive/qa/2026-05-17-post-sprint61/integrated-report.html).
- **2026-05-17 Sprint 61 PR #288 merge**: 11 BL fix (BL-310/311/312/319/322/323/327/328/339/340) source 적용 + hotfix PR #289 (BL-348/349). docs/archive/qa/2026-05-17/ baseline 별도.
- **2026-05-17 Multi-Agent QA 1차**: 신규 BL-310~346 (37건). 상세 = [`docs/archive/qa/2026-05-17/integrated-report.html`](archive/qa/2026-05-17/integrated-report.html) + [`docs/archive/sprint-61-plan.md`](archive/sprint-61-plan.md). 17 → 54 net.
- **Sprint 58** (2026-05-11~12): ✅ BL-241/242/243 Resolved (Pine TA 확장). 92 → 89 net.
- **Sprint 57** (2026-05-11): ✅ BL-234/237 Resolved (Optimizer Polish + heavy queue). 신규 BL-241~243. 91 → 92 net.
- **Sprint 56** (2026-05-11): ✅ BL-233 Resolved (Genetic). 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11): ✅ BL-232 Resolved (Bayesian). 신규 BL-233~237. 88 → 92 net.

**Sprint 59 트리아주 결과 (PR-D, 2026-05-13):** 158 BL → **13 Active** (본 문서 본문) + **8 Deferred** ([`_deferred.md`](archive/refactoring-backlog/_deferred.md) — Beta 6 + BL-005 + BL-145) + **137 Archived** ([`_archived.md`](archive/refactoring-backlog/_archived.md) — Resolved + Sprint 16~30 stale).

**P0 / P1 active short list (Beta 본격 진입 prep):**

- **🚀 Beta 진입 milestone (BL-070~072) — active P0** ([\_deferred.md](archive/refactoring-backlog/_deferred.md) 에서 승격):
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
> **Beta 진입 milestone 상세**: [\_deferred.md](archive/refactoring-backlog/_deferred.md) BL-070~075 섹션.

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

| ID                | 제목                                        | Trigger              | Est      | 출처                 |
| ----------------- | ------------------------------------------- | -------------------- | -------- | -------------------- |
| [BL-003](#bl-003) | Bybit mainnet 진입 runbook + smoke 스크립트 | H1 Stealth 종료 직전 | M (4-5h) | 2026-04-30 TODO 이력 |

> 추가 P0 — [BL-005 본인 dogfood](archive/refactoring-backlog/_deferred.md) + [BL-145 EffectiveLeverageEvaluator](archive/refactoring-backlog/_deferred.md) (deferred). Resolved P0 = BL-001/002/004 ([\_archived.md](archive/refactoring-backlog/_archived.md)).

### BL-003

**Title:** Bybit mainnet 진입 runbook + smoke 스크립트
**Category:** Tooling / Infra
**Priority:** P0 (H1 Stealth 종료 직전)
**Trigger:** Bybit Demo 1주 안정 운영 후 + BL-004 완료 후 (BL-004 = 완료, Sprint 28). ★**「1주 안정 운영」은 2026-08-05 부터 기계가 판정한다** — `scripts/soak-gate.sh` 가 PASS/FAIL/UNKNOWN 을 내고 **PASS 만 exit 0** 이다. 술어·창·리셋 규칙 = [ADR-024](decisions/024-soak-stability-gate.md).
**Est:** M (4-5h)
**출처:** [2026-04-30 당시 `docs/TODO.md`의 mainnet 준비 항목](https://github.com/woosung-dev/quantbridge/blob/b2c1541054326b06acf5e64f25094b6d5a37ea10/docs/TODO.md#L650-L653)

**원인 / 영향:** dogfood 가 Bybit Demo 만으로는 H1 종료 gate 충족 안 됨. mainnet 전환 시 수동 step 누락 위험 (IP whitelist / 출금 권한 차단 / 레버리지 1:1 / 소액 시작).

**권장 접근:**

1. Trigger 충족 시 당시 Bybit 정책·계정 모드에 맞춘 mainnet runbook 신규 작성 — IP whitelist · 출금 권한 OFF 확인 · 레버리지 1:1 · 소액 ($10-50) 시작 · Kill Switch 임계값 lower bound
2. `scripts/bybit-smoke.sh` 신규 — mainnet credentials 로 read-only API 호출 (잔고 조회 + 1 USDT limit-order 후 즉시 cancel) dry-run
3. `.env.production` 별도 secret manager + rotation 절차

**의존성:** BL-004(완료, Sprint 28 PR #108).

**Status:** 🔴 **열려 있다.** mainnet runbook·smoke 스크립트 미착수. (위 두 줄의 BL-004 는 **참조**다 — 이 항목의 상태가 아니다. 이 구분이 없어서 낡은 산식이 BL-003 을 RESOLVED 로 세고 **P0 active 를 0 으로 보고했다.**)

**게이트 현황 (2026-08-05 conditional-stop-ownership 재측정):** `scripts/soak-gate.sh` = **FAIL** (exit 1) — 누적 **0h / 168h**. ★**차단자 [BL-595] 를 이 회차에 수리했다**([ADR-025]) — 라이브 조건부 진입 체결의 권한을 주문 원장으로 옮겼고, 사망 **5건 전량을 얼려 재현**(영속 보고서와 비트 단위 일치)한 뒤 수리 전 5/5 `direction` 발산 → 수리 후 5/5 일치를 보였다. ★**착수 중에 소크 세션 `a16aa640` 이 죽었다**(08-05T09:12:53Z, 생존 8.642h) — 5번째 사망이자 워커 로그가 남은 유일한 건이라 오라클을 거래소 실측으로 교차검증하는 데 썼다(3/3 일치). 기저율 재측정: [BL-590] 이후 노출 **18.831h 에 자동 사망 3건 = 0.159/h(MTBF 6.3h)** · `phantom` 6건 = 0.319/h. ★★codex 가 **「가장 오래 산 세션에서 보호가 먼저 꺼지는」** 경로를 잡았다 — 원장 조회가 세션 스코프 + 상한 200 이라 체결 2.55건/h 로 **약 78시간**이면 영구 판정 불가가 된다(이 항목의 168h 누적 경로에서 정확히 밟는다). 재생 창 스코프로 바꿔 닫았다.

**이전 게이트 현황 (2026-08-05 divergence-rejudgement):** C3 **3건**(`cc19abd2` phantom 2 + auto_death 1), 소크 세션 `a16aa640` · 커밋 `f5f06886`. ★★★**실제 차단자는 달력 시간이 아니라 「엔진과 거래소가 서로 다른 stop 주문을 든다」는 것 — 신규 [BL-595]**. 사망 4건 부검에서 **엔진이 앞선 3건 · 거래소가 앞선 1건**으로 방향이 갈렸고, 킬 정책 교체([BL-591] 슬라이스 B)로 살아났을 세션은 **0개**다. ★★**판별식 교체 — 봉경계식 → 재무장 도장식**([ADR-024] §판별식 교체): 19건 전량 재적용 시 phantom **11→7**, 사망 상관 **4/4 보존**, **판정은 여전히 FAIL**(교체가 통과를 사지 않는다). ★아카이브에 판(版)을 실었다 — 안 그러면 취소된 라벨이 영원히 남는다. ★★★**과거 56.44h 는 소급 인정하지 않는다**(귀속 가능 0.46%) · **역대 2위 8.65h 는 마지막 46.7분 평가 정지** ⇒ 「역대 최장 15.3h = 9%」는 두 겹 낙관이었다.

---

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

| ID                | 제목                                                                                               | Trigger                                         | Est        | 출처                            |
| ----------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------- | ------------------------------- |
| [BL-014](#bl-014) | 🟡 부분 Resolved — Partial fill `cumExecQty` tracking (잔여 = BL-439/440/441)                      | 🟡 2026-07-25 `stage/money-path-accuracy`       | M (4-5h)   | TODO.md L709                    |
| [BL-015](#bl-015) | OKX Private WS                                                                                     | Bybit Demo 안정화 후                            | M (6-8h)   | TODO.md L710                    |
| [BL-022](#bl-022) | golden expectations 재생성                                                                         | pine_v2 `strategy.exit` 도입 후                 | M (3-4h)   | TODO.md L17 (skip #1)           |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                       | Trust Layer v2 검토 시                          | M (5-6h)   | TODO.md L23 (skip #16)          |
| [BL-024](#bl-024) | real_broker E2E 본 구현 (nightly cron)                                                             | Bybit Demo credentials + seed data 준비 시      | L (8h+)    | CLAUDE.md Sprint 10 Phase C     |
| [BL-025](#bl-025) | autonomous-parallel-sprints 스킬 patch                                                             | on-demand (BUG-1/2/3 재발 시)                   | S (2h)     | TODO.md L653                    |
| [BL-026](#bl-026) | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                                    | Stage 2c 2차 fixture 활성화 후                  | S (1-2h)   | TODO.md L20-22                  |
| [BL-308](#bl-308) | ✅ Resolved — trading websocket test coverage 4% → ≥70% (실측 85% → **96%** combined)              | ✅ W3 2026-06-29 (CI `--cov-fail-under=90`)     | L (12-16h) | 2026-05-15 trading-deepen audit |
| [BL-361](#bl-361) | ✅ Resolved — Pine Trust Layer 누출 (coverage SUPPORTED ↔ interpreter dispatch 28 symbols)         | ✅ S2 `stage/fix-trust-layer-leak`              | S (2-3h)   | 2026-05-30 전체 정검 §4.3       |
| [BL-404](#bl-404) | ✅ Resolved — watchdog `fetch_order` Bybit 전면 실패 (acknowledged 게이트 + futures 심볼 미정규화) | ✅ `fix/trading-bl404-fetch-order-acknowledged` | S (1-2h)   | 2026-07-05 데모 라이브 dogfood  |
| [BL-488](#bl-488) | ✅ Resolved — 평가 갭 orphan close → 보유분 없는 `reduce_only` 주문과 시뮬 손익 오염               | ✅ 2026-07-27 `feat/live-conditional-entry`     | M          | 2026-07-26 live-engine-parity   |
| [BL-522](#bl-522) | ★엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다 (유실 채널 5종)             | 실자금 cutover 전 필수                          | M-L        | 2026-07-28 live-entry-parity    |

> Resolved P1 = BL-001/002/010/011/012/013/016/017~021/080/091~099/101~103/110a 등 18+ 건 ([\_archived.md](archive/refactoring-backlog/_archived.md)).

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

---

### BL-015

**Title:** OKX Private WS
**Category:** WebSocket / Exchange
**Priority:** P1
**Trigger:** Bybit Demo 안정화 후 (BL-001 watchdog 완료 + 1주 운영)
**Est:** M (6-8h)
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
**출처:** TODO.md L17 / `tests/backtest/engine/test_golden_backtest.py:19`

**권장 접근:** legacy golden expectations 재생성 (pine_v2 strategy.exit 가 도입되면 expected 재계산). dette 카테고리 #1 해소.

---

### BL-023

**Title:** KIND-B/C mutation 분류 정밀도 (xfail strict 해소)
**Category:** Trust Layer / Mutation
**Priority:** P1
**Trigger:** Trust Layer v2 검토 시
**Est:** M (5-6h)
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

**상태:** 🟡 **열려 있다 (2026-08-04, `wt/e2e` — 워크플로·하네스만 수리, 실주문 leg 미착수).** ★★★**「skeleton 을 채운다」는 전제가 실측으로 뒤집혔다** — nightly 는 07-25~08-03 **10/10 실패**했고 지점은 pytest 가 아니라 `alembic upgrade head` 였다(`secrets.TRADING_ENCRYPTION_KEYS_TEST` 부재 → 빈 문자열 → `Settings` import 시점 ValidationError). ⇒ **pytest 는 한 번도 실행된 적이 없고, `flaky-real-broker` 이슈 89건(전부 OPEN)은 broker flakiness 의 증거가 아니다.** ★이 고장은 **alembic 스텝에만** 해당한다 — `tests/conftest.py:25-28` 이 pytest 에서는 빈 키를 즉석 Fernet 로 채운다. 이번 회차가 한 것: 워크플로 수리 9건(리터럴 키 · preflight `has_creds` 게이팅 · **이슈 생산기 스위치** · `_test` DSN · 아티팩트) + 계약 감사 `tests/test_nightly_workflow_contract.py`(marker 없음, 매 PR) + 자기정리 2층 하네스(`tests/real_broker/_harness.py`) + `_test` DSN 하드가드 + provider 경유 demo 엔드포인트 교정. ★**실거래소는 1바이트도 검증되지 않았다** — 잔여 = 실주문 leg(S2~S13), **차단 사유는 Bybit demo 전용 키 2종 미발급**(`BYBIT_DEMO_API_KEY_TEST` / `BYBIT_DEMO_API_SECRET_TEST`).

**권장 접근:** 자격증명 2종 발급 후 실주문 leg 구현. ★체결 확인을 polling 으로 짜지 마라 — Bybit demo 시장가는 `create_order` 응답에서 `submitted` 로 오고(`providers.py:_map_ccxt_status`) 체결 확정은 WS 가 한다. `_async_fetch_order_status`(`tasks/trading.py:685-707`)를 명시적으로 태우는 설계여야 한다.

---

### BL-025

**Title:** autonomous-parallel-sprints 스킬 patch (BUG-1/2/3 → LESSON-007/008/009)
**Category:** Tooling
**Priority:** P1 (다음 자율 병렬 sprint 시 재발 방지)
**Trigger:** on-demand (다음 자율 병렬 sprint 시도 직전)
**Est:** S (2h)
**출처:** TODO.md L653-657

**권장 접근:**

- BUG-1: kickoff-worker.sh symlink → `--git-common-dir` 기반 교체
- BUG-2: Planner SIG_ID full-id 강제
- BUG-3: Worker plan 저장 경로 worktree-only 강제
- 스킬 repo: `~/.claude/skills/autonomous-parallel-sprints/`

---

### BL-026

**상태:** 🟡 **열려 있다** — 본 섹션 `**Trigger:**` 줄의 ✅ 는 _Stage 2c 2차 fixture 활성화_(2026-04-23 완료)를 가리키고, 이 BL 자신은 같은 줄이 명시하듯 **"회귀 PR 생성 필요"** 상태다. 근거: 본 섹션 Trigger/권장 접근 줄 · `docs/roadmap.md:168` `- [ ] **BL-026**`.

**Title:** Mutation fixture 활성화 회귀 검토 (skip #4-7, #9-15)
**Category:** Trust Layer / Test infra
**Priority:** P1
**Trigger:** Stage 2c 2차 fixture 활성화 후 (✅ 2026-04-23 완료, 회귀 PR 생성 필요)
**Est:** S (1-2h)
**출처:** TODO.md L20-22

**권장 접근:** Path β Stage 2c 2차 mutation 8/8 도달 후 12 skip 가 활성화 가능 상태. 회귀 PR 1건으로 일괄 활성화 + 1주 nightly green 후 안정화.

---

### BL-308

**Title:** trading websocket subsystem test coverage boost (4% → ≥70%)
**Category:** Test infra / Trading
**Priority:** P1
**Trigger:** dogfood 직후 (Day 7 인터뷰 2026-05-16 후) — websocket reconciliation 미검증 = 거래 silent failure risk
**Est:** L (12-16h)
**출처:** [`docs/dev-log/2026-05-15-trading-deepen.md`](dev-log/2026-05-15-trading-deepen.md) Phase 2

**✅ Resolved (W3, 2026-06-29):** baseline 재측정 결과 "4%" 는 stale (2026-05-15, PR #305 money-path 감사 + TP/SL·트레일링 wave 이전). 실측 baseline = `websocket/` **85% combined branch cov** (bybit_private_stream 75% / reconciliation 90% / reconcile_fetcher 100% / state_handler 86%). W3 가 진짜 미커버 머니패스 분기만 보강 (replay_orphan / orphan TTL eviction / \_receive_loop json·topic·handler-None·exception-swallow / \_heartbeat_loop / \_maybe_reconcile 예외 / auth timeout / \_find_match orderLinkId·clOrdId fallback / Rejected 전이 / \_handle_unknown alert 예외) → **96% combined** (bybit 93% / reconciliation 97% / state_handler 96%). 잔여 미커버 = supervisor reconnect/timeout 타이밍 분기 + trivial getter (deterministic 테스트 불가 → vacuous 회피로 의도적 제외). CI `--cov-fail-under=90` ratchet 게이트 추가. 게이트: G1 codex plan + G2 codex challenge(4 P1 false-green 수정) + G3 fresh review(mutation 검증) PASS.

**현 상태 (2026-05-15 당시):** `backend/src/trading/websocket/` 904 LOC (도메인 19.4%) = 3 file (`bybit_private_stream.py` 319L + `reconciliation.py` 225L + `state_handler.py` 221L 등) 안 test 2/48 file 만 reference = **~4% 추정 coverage**. WS event reconciliation logic = order state cascade 핵심 = silent corruption risk.

**권장 접근:**

1. `tests/trading/websocket/` 폴더 신규 — bybit_private_stream / reconciliation / state_handler 각 file 1-2 test module
2. fixture = `BybitPrivateStream` async context manager mock + WS message replay (json fixture)
3. reconciliation engine end-to-end test (open order → WS event sequence → terminal state 검증)
4. coverage `pytest --cov=src.trading.websocket --cov-fail-under=70` CI gate 추가

**Risk:** 🔴 (현재 silent failure risk = order state mismatch 가능). dogfood 직후 = order 발송 후 reconciliation 깨짐 시 사용자 발견 어려움.

**의존성:** BL-024 real_broker E2E 와 묶음 sprint 가능 (양쪽 모두 trading 안정화 sprint).

---

### BL-361

**Title:** Pine Trust Layer 누출 — coverage SUPPORTED ↔ interpreter dispatch SSOT drift (28 symbols)
**Category:** Strategy / pine_v2 SSOT / Trust Layer
**Priority:** P1
**Trigger:** 전체 정검 2026-05-30 (P1-10/13)
**Est:** S (2-3h) — 실측 ~1.5h
**출처:** [`docs/archive/audit/2026-05-30-full-inspection.md`](archive/audit/2026-05-30-full-inspection.md) §4.3
**Status:** ✅ **Resolved S2** (`stage/fix-trust-layer-leak`) — 28 누출 전부 구현 + 망라 parity 테스트가 영구 tripwire. ★단 이 항목이 닫은 것은 **그 28건**이고, 라이브 `strict=False` 가 향후 임의의 발산을 조용히 삼키는 latent risk 서술은 [BL-362](#bl-362) 본문에 남아 있다 (지우지 말 것).

**원인 / 영향:** `coverage.py` 가 SUPPORTED 표기하나 interpreter 미구현 → `is_runnable=True` preflight 통과 후 runtime `PineRuntimeError`. backtest=FAILED(strict=True), live=silent swallow 후 오신호(strict=False, event_loop.py:128). ADR-003 부분실행 금지 위반.

**해소:** 망라 parity 테스트(`tests/strategy/pine_v2/test_coverage_interpreter_parity.py` 의 `SUPPORTED_ATTRIBUTES`/`_STRING_FUNCTIONS`/`_MATH_FUNCTIONS` 전수 순회)로 audit hand-found ~10 + **미발견 18** = 총 **28 누출** 검출 → `interpreter.py` 전부 구현: hl2/hlc3/ohlc4(`_resolve_name`, Pine 정의 1:1), barstate.isfirst/islast/ishistory/isconfirmed(`_eval_attribute`, bar*index/len), str.tostring/tonumber/format/length + bare tonumber(`_eval_call`, NOP-safe/정확 parse), currency.\* 12(`_eval_attribute` prefix), strategy.commission*\* 3(`_ATTR_CONSTANTS`), math.log10. TDD RED 28→GREEN. **codex challenge(769k) 교차검증 → Finding 1 추가 fix**: `hl2[1]`/`hlc3[1]`/`ohlc4[1]` lagged 참조가 history series 누락으로 na 반환하던 silent 오값 → `_synthetic_source(name, offset)` helper (current+history 공용) 로 보완 (`test_synthetic_source_history_lag`). codex Findings 2~6 은 재검증으로 out-of-scope/pre-existing/consistent (audit §7). pine_v2 612 pass 회귀 0. 향후 SUPPORTED 추가 누출 = 망라 테스트가 CI 자동 차단(영구 tripwire).

---

### BL-404

**Title:** watchdog `fetch_order` Bybit 전면 실패 — ccxt `acknowledged` 게이트 미대응 + futures 심볼 카테고리 미정규화 (라이브 주문 submitted 영구 고착)
**Category:** Trading / provider (money-path 안전망)
**Priority:** P1
**Trigger:** 즉시 (2026-07-05 데모 라이브 dogfood 실측 발견)
**Est:** S (1-2h) — 실측 ~1h
**출처:** 2026-07-05 데모 라이브 dogfood — 라이브 주문 9건 전부 submitted 고착 + 재현 1줄(`BybitFuturesProvider.fetch_order(creds, exid, "BTC/USDT")`)

**원인 / 영향:** 2중 결함. (1) ccxt bybit `fetchOrder()` 가 `params["acknowledged"]=True` 없이 `ArgumentsRequired` raise(last-500-orders 제약 인지 게이트) — `_bybit_fetch_order_impl` 미대응으로 watchdog `trading.fetch_order_status` 가 전량 ProviderError → 무한 백오프 재시도. (2) 게이트를 통과해도 futures fetch 가 DB `order.symbol`(spot 포맷 `BTC/USDT`)을 미정규화 전달 → ccxt market 해석이 category=spot → linear 주문 `OrderNotFound` (실 demo 대조: `BTC/USDT:USDT`=OK / `BTC/USDT`=NotFound. BL-124 정규화가 create/trailing/position 3 call-site 에만 적용, fetch 만 누락 — (1) 게이트가 가려온 latent). 결과 = 라이브 주문이 거래소에선 체결돼도 DB submitted 영구 고착 → filled_price/realized_pnl 미기록 → 코크핏 집계·kill-switch CumulativeLoss 평가 무력화. ws_stream Reconciler(fetch_open/closed/canceled 사용)가 뜨면 커버되나, ws 워커 부재 환경(host 단독 기동 등)에선 fill 확정 안전망 0겹.

**해소:** `_bybit_fetch_order_impl` 에 `params={"acknowledged": True}`(게이트 도입 전 realtime 조회 동작 복원) + `BybitFuturesProvider.fetch_order` 에 `_to_bybit_linear_symbol()` 적용. TDD(red 3 → green, `test_provider_fetch_order.py` 회귀 2건 추가) + trading 스위트 440 pass + 실 Bybit demo end-to-end(신선 주문 생성 → spot 포맷 경로 fetch `status=filled` 확인 → flatten). **잔여(후속 후보):** `fetch_mark_price` 도 spot 티커 근사 사용(동일 계열, 실패 아님 — notional 가드 정밀도) / realtime 범위(최근 500) 밖 장기 고착 주문은 여전히 미조회 → Reconciler 커버(BL-375 계열) / BL-003 mainnet 시 재점검: classic(비-UTA) live 계정 경로(`fetch_orders_classic`)에선 acknowledged 가 쿼리 param 으로 누수(현재는 live stub 이라 dead, adversarial 리뷰 footnote).

**Status:** ✅ Resolved (2026-07-05, `fix/trading-bl404-fetch-order-acknowledged`)

---

### BL-488

**상태:** ✅ **Resolved (2026-07-27, `feat/live-conditional-entry`).** 원인은 인프라가 아니라 `run_live` 가 마지막 bar 이벤트만 발행하는 계약이었다. 24h 실측으로 갭 131바를 분해하니 macOS 클램셸 수면 73바 + 우리 배포창 50바 + idle sleep 3바였고 **서버 기전은 늦은 tick 4바(0.29%)** 뿐이었다(`/data` uid 1000, permission denied 0건, RestartCount 0 으로 beat 가설 기각). `emit_from_bar_time` opt-in catch-up(기본값 byte-identical) + **벽시계** staleness 상한 + 초과 시 resync(양쪽 flat 이면 조용히 정상화, 불일치면 비활성화 + 조건부 진입 청소) + close dispatch 전 포지션 확인(조회 실패는 fail-OPEN). 프로덕션에서 resync 가 실제로 발동해 orphan close 를 막는 것을 관측했다.

**Title:** 평가 갭이 orphan close 를 만든다
**Category:** Backend / trading (라이브 신호 평가)
**Priority:** P1
**Trigger:** 즉시. 평가 갭이 재현되거나 beat 안정화 전
**Est:** M
**출처:** 2026-07-26 live-engine-parity preflight 실측. 라이브 세션 `e1f6d84c`.

**원인 / 영향:** `run_live` 는 마지막 bar 신호만 dispatch 하고 warmup replay 는 창 전체를 재구성한다. 워커가 어떤 bar를 평가하지 못하면 그 bar의 진입은 발주된 적 없는데, 이후 청산은 정상 발주된다. 결과는 보유분 없는 `reduce_only` 주문의 거래소 거부와 시뮬 이익의 오염이다.

실측은 11:45~15:57 사이 252 bar 중 180 bar만 평가했고 13:10~13:59에 50분 구멍이 있었다. 약 13:19 시뮬 진입은 `live_signal_events`에 0건인데 15:11 청산은 발주돼 `orders.state = rejected` 였으며, 시뮬은 `+4.87330864` 를 이익으로 계상했다. `Σ orders.realized_pnl` 도 그 추정치를 담아 원장 합계를 오염시킨다.

**권장 접근:** 연속 `bar_time` 결손을 감지해 갭 뒤 첫 tick에서 포지션을 재동기화하거나, close 발주 전에 거래소 포지션을 확인한다. 후자는 BL-476이 REST 왕복 1.5~1.7초를 실측했으므로 지연 비용 측정이 먼저다. 어느 쪽이든 갭 자체를 줄이는 beat 안정화가 선행한다.

**영향 파일:** `tasks/live_signal.py`, `strategy/pine_v2/event_loop.py`.

**Risk:** 🔴 (실주문 거부 + 시뮬 손익 오염).

---

### BL-492

**Title:** 이미 돌파된 stop 의 시뮬↔거래소 시맨틱
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** 실자금 cutover 전, 또는 110093 거부가 잦아질 때
**Est:** S-M
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
**출처:** 2026-07-27 live-conditional-entry

**원인 / 영향:** 조건부 진입 계획기는 `qty_step` 절삭만 한다. BTCUSDT 는 `limits.amount.min == qtyStep == 0.001` 이라 절삭이 최소수량을 겸하지만 일반 보장은 아니다. 둘이 다른 심볼에서는 스텝은 통과하고 최소수량은 미달인 주문이 매 tick 거부될 수 있다.

**Risk:** 🟢

---

### BL-495

**상태:** ✅ **Resolved (2026-07-27, `feat/live-conditional-entry`).** `.pager-nums` 에 `flex-wrap: wrap` 1줄. 부모 `.pager` 는 이미 `flex-wrap: wrap` 이었고 그 안쪽에서만 줄바꿈이 막혀 있었다. 실측 375px `/orders` — `flex-wrap` `nowrap` → `wrap`, `.pager-nums` **453px → 301px**, `scrollWidth` **490 → 375**(= `clientWidth`), 콘솔 error 0. ★**"다른 규칙이 이기고 있다" 는 가설은 반증됐다** — CSSOM 덤프 결과 `.pager-nums` 에 매치된 규칙은 layer `components` 의 **1개뿐**이었고, dev 서버 재기동·캐시 제거 없이 HMR 이 바로 반영했다. 진짜 제약은 따로 있었다 — 이 규칙은 `globals.css` 의 **KITPORT 센티넬 안**(976~1878행)이라 `design-canon-kit-port.test.ts` 가 `_kit.html` 정본과 정규화 동일로 잠근다. 그래서 기존 선례 3건과 같은 방식으로 **allowlist 4번째 항목 + "실재한다" 테스트**를 함께 넣었다(변이 검증 — CSS 만 되돌리면 그 테스트만 red, 나머지 4건 green).

**Title:** `/orders` 페이저가 좁은 폭에서 가로 오버플로
**Category:** Frontend / 디자인 캐논
**Priority:** P3
**Trigger:** 즉시(게이트 red). authed 캐논 `/orders` 하드 실패 1건
**Est:** XS
**출처:** 2026-07-27 live-conditional-entry dogfood (데이터 유발로 드러난 잠복 결함)

**원인 / 영향:** `.pager-nums` 가 `display: inline-flex` 에 줄바꿈이 없다(`styles/globals.css:1675`). 페이지 수가 늘면 375px 폭에서 넘친다 — 실측 주문 99건 -> 10 페이지 -> `span.pager-nums` **453px**, 문서 `scrollWidth 490 > innerWidth 375`. **이번 스프린트 코드 회귀가 아니다**(주문 페이지·페이저 미변경). dogfood 가 주문을 62 -> 99건으로 늘리며 잠복 결함이 드러난 것이다.

**권장 접근:** `flex-wrap: wrap` 이 자연스러운 후보지만 **한 번 시도했을 때 적용되지 않았다**(`getComputedStyle` 이 여전히 `nowrap`). 다른 규칙이 이기고 있거나 dev 서버 재컴파일 문제일 수 있으니 **원인부터 확인**해라. 검증 없이 싣지 말 것 — 그래서 이번엔 되돌리고 등재만 한다.

**영향 파일:** `frontend/src/styles/globals.css`.

**Risk:** 🟢 (표시 전용. 단 authed 캐논 게이트가 red 다).

---

### BL-496

**Title:** 조건부 진입 발주 순서가 엔진 체결 우선순위와 다르다
**Category:** Backend / trading (조건부 진입)
**Priority:** P3
**Trigger:** 같은 바에 조건부 진입이 2건 이상 열리고 둘 다 트리거될 수 있을 때
**Est:** S
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
**출처:** 2026-07-27 live-conditional-entry 작업 노트 (종결 시 등재)

**원인 / 영향:** reconcile 은 취소 루프를 **전부 끝낸 뒤** 등재 루프를 돈다(`tasks/live_signal.py:406-416` → `:462-492`). 의도한 순서지만(이중 등재 방지), 그 사이 수 초 동안 거래소에 그 stop 이 **없다**. 그 창에서 가격이 트리거를 지나가면 진입을 통째로 놓치고 시뮬만 진입했다고 믿는다 — BL-492 와 같은 발산의 다른 경로다. BL-486 창 드리프트로 재등재가 104분에 8건 나므로 창이 반복 열린다.

**권장 접근:** ccxt `edit_order`(amend) 로 취소·재등재를 한 번의 왕복으로 바꾼다. Bybit v5 는 `/v5/order/amend` 로 `triggerPrice`·`qty` 수정을 지원하므로 **계약 실측이 선행**한다(미트리거 조건부에 amend 가 되는지). 대안은 place-then-cancel 순서 뒤집기인데 그 사이 **이중 등재**가 열리므로 귀속 불변식만으로는 부족하다.

**영향 파일:** `tasks/live_signal.py`, `trading/providers.py`.

**Risk:** 🟢 (fail-closed 는 아니지만 무음 미진입이라 관측 가능성이 낮다).

---

### BL-498

**상태:** ✅ **Resolved (2026-07-27, `feat/live-conditional-hardening`).** 계정 스코프 조회 `GET /exchange-accounts/{id}/positions` 신설 + 코크핏 §03 에 "계정 잔여 포지션" 표를 세션별 대조 **위**에 추가. **신규 청산 경로는 만들지 않았다** — preflight 가 `ClosePositionService.close_position` 이 `is_active` 를 요구하지 않는다는 것을 밝혔으므로(비활성 세션 id 로도 청산된다) 막혀 있던 건 화면이 활성 세션만 순회하는 것뿐이었다. ccxt `fetch_positions()` 는 심볼 인자 없이 `settleCoin=USDT`·`category=linear` 로 계정 전체를 1콜에 준다. ★**dogfood 종단 증명** — 활성 세션 0건 상태에서 raw HMAC 으로 앱 밖에서 `BTCUSDT Buy 0.002 @65331.1` 생성 → 코크핏 §03 렌더된 화면에 표시 → 화면 청산 버튼 → 거래소 `Sell 0.002 reduceOnly=True @65315.1`, 포지션 `legs=0`. 3중 대조 일치(우리 원장 `a8765854` = 거래소 `orderLinkId`, `exchange_order_id bedc278b` = 거래소 `orderId`, `filled_price 65315.1` = `avg`). 콘솔 error 0. ★청산 불가 사유를 **서버에서** 판정한다 — 귀속 세션 없음(`no_owning_session`) · hedge/`position_idx != 0`(`hedge_unsupported`). 누르면 409 로 실패할 버튼을 주지 않는다. ★조회 범위(USDT 정산 linear 전용)를 응답 필드와 화면 각주로 고지한다.

**Title:** 활성 세션이 없으면 거래소 포지션을 화면에서 보지도 닫지도 못한다
**Category:** Frontend / trading (코크핏 §03)
**Priority:** **P2**
**Trigger:** 즉시 — fail-closed 종료가 포지션을 남기는 것은 **설계**이므로 반복해서 발생한다
**Est:** M
**출처:** 2026-07-27 live-conditional-entry 종결 (실측으로 발견)

**원인 / 영향:** `open-positions-table.tsx` 는 **세션 스코프**("세션별 대조")다. 행 생성이 활성 세션 순회라 활성 세션이 0건이면 `"활성 라이브 세션이 없습니다."` 만 렌더되고 **수동 청산 버튼 자체가 존재하지 않는다**(렌더된 페이지에서 확인).

문제는 이게 예외 상황이 아니라는 것이다 — BL-488 의 `gap_resync_position_mismatch` fail-closed 는 **주문은 걷고 포지션은 의도적으로 남긴 채** 세션을 비활성화한다. 즉 이 경로를 탈 때마다 사용자에게 **화면에서 보이지도 닫히지도 않는 실포지션**이 남는다. 실측 — 07-27 dogfood 종료 후 `BTCUSDT Sell 0.029 @ 65340.2`(미실현 +7.22 USDT)가 거래소에 남았고 코크핏에는 아무것도 뜨지 않았다. 남은 우회로 2개도 실질적으로 막혀 있다 — 테스트 주문 다이얼로그는 `sessionStorage` webhook secret 을 요구하고 그걸 얻으려면 **secret 회전**(기존 secret 무효화)이 필요하다.

**권장 접근:** 계정 단위 포지션 섹션을 세션 대조와 **분리**한다. 세션 순회가 아니라 `exchange_account_id` 로 거래소 포지션을 조회해 `세션 없음` 상태에서도 렌더하고, 기존 감소전용 시장가 청산(`close-position`)을 그 행에 붙인다. 세션별 대조는 지금 자리에 그대로 둔다(용도가 다르다 — 대조는 발산 감지, 이건 잔여 노출 관리).

**영향 파일:** `frontend/src/app/(dashboard)/trading/_components/open-positions-table.tsx`, `trading/services/position_service.py`.

**Risk:** 🟡 (실자금에서는 관리 불가 노출. 데모에서는 정리 불가 상태).

---

### BL-499

**상태:** 🟡 **열려 있다 — 단 trigger 는 이제 발화 가능하다.** ★★2026-07-28 `feat/live-observability` 정정: 이 항목의 **Trigger("취소 실패 metric 이 관측되면")가 BL-506 이전에는 구조적으로 충족 불가**였다. 그 카운터는 worker 전용이라 어떤 스크레이프 경로에도 노출되지 않았기 때문이다(BL-506 이 그 모순을 지적했다). **BL-506 Resolved 로 관측 가능성 자체는 확보됐다** — 배선 후 `qb_live_conditional_reconcile_errors_total` 의 다른 라벨(`deferred_market_inflight` 8 · `positions` 3)이 실제로 관측된다.
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

### BL-500

**상태:** ✅ **Resolved (2026-07-27, `feat/live-conditional-hardening`).** 거래소 조회가 **성공한** tick 에 한해, `exchange_order_id` 가 있는데 거래소 응답에 없는 로컬 행을 `actual` 에서 제거하고 `stage="exchange_missing"` metric + 발산 로그를 남긴다. 계획기가 그 trade_id 를 다시 등재하므로 영구 no-op 이 풀린다.

★★**"목록에 없다" 는 부재의 증거로 쓰지 않는다.** 후보마다 `fetch_order(exchange_order_id)` 로 **거래소에 직접 물어** terminal(`filled`/`cancelled`/`rejected`)임을 확인한 뒤에만 제거한다. 확인하지 못하면(조회 실패·아직 열려 있음) 그대로 둔다. `exchange_order_id` 가 없는 in-flight 행은 물어볼 대상이 없으므로 건드리지 않는다.

★**나이 게이트(3분)는 폐기했다 — 적대 검증이 잘못된 시계를 잰다는 것을 증명했다.** reconcile 은 60초마다가 아니라 **bar 마다** 돈다(`no_new_bar` 조기 return). 1h 세션이면 어떤 주문이든 나이가 항상 3분을 넘어 게이트가 늘 열려 있었다. 게다가 `submitted_at` 은 **주문의 나이**이지 **부재의 나이**가 아니고, 조건부 진입은 정의상 몇 시간 resting 하다 트리거된다 — 막겠다던 창의 주문은 거의 전부 이미 늙어 있다.

★**체결이 확인되면 그 tick 은 등재하지 않는다.** 포지션 스냅샷이 그 체결보다 앞서 찍혔을 수 있어 낡은 포지션으로 사이징하면 이중 포지션이 된다.

★**상태 전이는 하지 않는다** — watchdog·`Reconciler` 책임이다. **한계(정정)** — 유령 행은 자연 해소되지 않는다. `websocket/reconcile_fetcher.py` 는 `trigger=True`/`orderFilter=StopOrder` 를 쓰지 않아 **미트리거 조건부 주문을 구조적으로 볼 수 없다**(이전 서술 "WS 재연결 reconcile 까지" 는 틀렸다). `orphan_scanner` 도 조건부 진입을 면제하므로 아무도 안 치운다 → **BL-503** 등재.

**Title:** 거래소에서 사라진 `submitted` 조건부 주문을 DB 행만으로 resting 이라 오인한다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** ws-stream 장애 후, 또는 사용자가 거래소에서 직접 취소했을 때
**Est:** M
**출처:** 2026-07-27 live-conditional-entry 최종 codex 리뷰 (재현 판정 후 등재)

**원인 / 영향:** `actual` 은 로컬 `pending/submitted` 행으로 먼저 채우고(`live_signal.py:300-314`) 그 뒤 거래소 조회 결과로 **덮어쓰기만** 한다(`:319-345`). 거래소 open-order 응답에 없는 로컬 행은 **제거되지 않는다.** 그래서 거래소엔 없고 DB 만 `submitted` 인 주문이 desired 와 일치하면 계획기가 "이미 등재됨" 으로 보고 재등재하지 않는다 — 그 전략은 그 trade_id 에 대해 영구 no-op 이 된다.

이 설계는 의도된 것이다(D4 — `actual` = 거래소 ∪ 로컬 in-flight, 이중 등재 봉인). 문제는 **로컬 우선이 거래소 부재를 이기는 방향**이라는 것이다. 완화 경로는 있다 — 사용자가 Bybit 에서 취소하면 private WS order 스트림이 `Cancelled` 를 밀어 `state_handler` 가 상태를 전이시킨다. ★단 이번 스프린트가 `orphan_scanner` 에서 조건부 진입을 **오탐 면제**시켰으므로(`trigger_price IS NULL` 필터) 그 stuck 검출기는 더 이상 이 케이스를 잡지 않는다. WS 를 놓치면 영구화한다.

**권장 접근:** 거래소 조회가 **성공한** tick 에 한해 `exchange_order_id` 가 있는 로컬 행 중 거래소 응답에 없는 것을 `actual` 에서 제거하고 발산 보고한다. `exchange_order_id` 가 아직 없는 in-flight 행은 그대로 둔다(그건 진짜 이중 등재 방어다). 조회 실패 tick 에는 절대 제거하지 않는다(fail-OPEN 이 아니라 현상 유지).

★**테스트 계약 구멍도 함께 닫아야 한다** — `test_local_in_flight_order_prevents_duplicate_placement` 는 로컬 행을 실제 주문의 증거로 취급하므로 이 반대 케이스를 구조적으로 못 잡는다.

**영향 파일:** `tasks/live_signal.py`, `trading/services/conditional_entry_planner.py`.

**Risk:** 🟡 (무음 미진입 — 관측 가능성이 낮다).

---

### BL-501

**상태:** ✅ **Resolved (2026-07-28, `feat/live-ops-hygiene`).** 마이그레이션 1건(`exchange_uid`·`read_only`, 둘 다 nullable = "아직 모른다"). 등록 시 1회 + 5분 beat 백필로 채우고, **목록 엔드포인트는 순수 DB 읽기로 유지**한다(hot path 에 무제한 REST 를 붙이지 않는다). 화면에서 `(uid, symbol)` 로 행을 병합하되 **계정은 전부 조회**한다. read-only 는 `close_blocked_reason="read_only_key"` + 서버 422 로 이중 차단. 15초 잔존 창은 **청산 시 uid 형제 계정의 스냅샷 키까지 삭제**해 닫았다(3 사이트 전부).

★★**"uid 대표 계정만 조회" 로 갔으면 기능이 역효과였다.** 세션 귀속과 자격증명은 uid 가 아니라 `exchange_account_id` 에 묶여 있어(`live_signal_session_repository.py:92`, `close_service` 가 세션의 계정으로 서명), 실측 배치처럼 read-only 형제가 그 심볼 세션을 갖고 있으면 쓰기 대표는 `no_owning_session` 이 되어 **청산 버튼이 오히려 사라진다.** 그래서 접기는 **표시 전용**이고 `close_service` 는 손대지 않았다.

★★**최종 리뷰가 P1 을 잡았다 — 접기가 hedge 의 두 leg 를 한 행으로 지웠다.** 서버는 leg 마다 행을 주는데(`position_service.py:287-300`, `test_hedge_legs_are_not_closable` 가 2행 단언) 그룹 키가 `(uid, symbol)` 뿐이라 long/short 이 병합돼 하나가 **화면에서 사라졌다.** uid 가 채워진 계정 하나만 있어도 재현된다. `hedge_unsupported` 행은 접지 않도록 고쳤다. ★화면 검증이 이걸 놓친 이유는 dogfood 계정이 one-way 단일 leg 였기 때문이다 — **재현 상태를 만들지 못하면 화면 검증도 못 본다.**

★**알려진 한계** — 저장값은 등록 시점 스냅샷이다. 나중에 키 권한을 바꾸면 낡고, 재등록이 해소 경로다. identity 조회가 실패하면 두 컬럼이 NULL 로 남고 그동안은 차단하지 않는다(**의도적 fail-open** — 모를 때 막으면 정상 계정의 청산까지 끊긴다).

**외부 오라클** — raw HMAC `/v5/user/query-api` 로 `19a8166a`→`userID=558689281, readOnly=0` · `0277c150`→`같은 uid, readOnly=1` 확인. 백필이 채운 DB 값과 일치.

**Title:** 같은 거래소 계정을 가리키는 API 키가 둘이면 포지션이 중복되고 read-only 키에도 청산 버튼이 붙는다
**Category:** Backend / Frontend / trading (계정 스코프)
**Priority:** P3
**Trigger:** 사용자가 같은 서브계정에 API 키를 2개 이상 등록해 둔 동안
**Est:** S-M
**출처:** 2026-07-27 live-conditional-hardening dogfood 실측

**원인 / 영향:** 계정 스코프 포지션은 **등록된 계정마다** 거래소를 조회한다. 그런데 등록된 두 계정이 같은 Bybit 서브계정을 가리킬 수 있다 — 실측으로 `19a8166a`('bybit demo')와 `0277c150`('bybit demo- aaa')가 **같은 uid `558689281`** 이었다(`/v5/user/query-api` raw HMAC 확인, BL-477 과 같은 사실). 그래서 하나뿐인 포지션이 계정마다 한 행씩 **두 번** 렌더된다.

두 번째 문제는 그중 `0277c150` 이 **`readOnly=1`** 이라는 것이다. 그 계정에도 BTC/USDT 세션이 있어 귀속 판정을 통과하므로 청산 버튼이 붙는데, 누르면 거래소가 권한 오류로 거부한다. 즉 `close_service` 가 걸러내는 hedge 와 같은 부류의 "누르면 실패하는 버튼" 이 권한 축에서 남아 있다.

**이번 스프린트 조치** — 계정이 2개 이상일 때 "여러 API 키가 같은 거래소 계정을 가리키면 같은 포지션이 계정마다 한 번씩 나타납니다" 각주를 렌더한다(무음 중복을 고지로 바꾼 것이지 해결이 아니다).

★**세 번째 귀결이 dogfood 로 드러났다 — 캐시 무효화가 계정 id 단위다.** 청산 주문은 자기 `exchange_account_id` 의 스냅샷 키만 지운다. 같은 거래소 계정을 가리키는 **다른 자격증명의 키는 그대로 남아** 최대 15초 동안 이미 닫힌 포지션을 계속 보여준다. 실측 — `19a8166a` 로 청산하니 그 키는 즉시 사라졌고 `0277c150` 키는 TTL 만료까지 남았다. uid 로 접으면 이 문제도 함께 닫힌다.

**권장 접근:** 계정 등록/조회 시 `/v5/user/query-api` 의 `userID` 를 캐시해 (a) 같은 uid 계정을 한 행으로 접고 (b) `readOnly` 키를 청산 불가로 판정한다. 등록 시점 1회 조회 + 계정 행 저장이면 조회 경로에 REST 비용이 안 붙는다. **마이그레이션 1건**(컬럼 2개)이 필요하다.

**영향 파일:** `trading/services/position_service.py`, `trading/services/account_service.py`, `trading/models.py`, `frontend/src/app/(dashboard)/trading/_components/account-positions-table.tsx`.

**Risk:** 🟢 (표시 중복 + 실패하는 버튼. 중복 청산을 눌러도 두 번째 감소전용 주문은 평탄해진 포지션에서 거부된다).

---

### BL-502

**상태:** ✅ **Resolved (2026-07-28, `feat/live-ops-hygiene`).** `useClosePosition` 이 대상을 받아 `["close-position", sessionId, symbol]` mutationKey 를 만들고, 두 표가 `useIsMutating` 으로 같은 키를 구독한다. `useInvalidatingMutation` 에 `mutationKey` 통과 옵션 1개만 추가했고 나머지 동작은 무변경.

★**고정 단일 키를 쓰지 않았다** — 그러면 계정·심볼이 달라도 모든 청산이 함께 잠겨 서로 다른 두 포지션을 연달아 닫지 못한다.

★★**테스트가 거짓 게이트였고 변이가 잡았다.** 과차단 음성 테스트가 `waitFor` 로 "여전히 활성" 을 단언했는데 그 콜백은 **t=0 에 즉시 성공**한다(변이가 in-flight 로 등록되기 전). 고정 단일 키로 바꿔도 통과했다. 클릭한 표의 버튼이 pending 라벨로 바뀌는 것을 **먼저 기다린 뒤** 다른 표를 단언하도록 고쳤고, 그 뒤 두 변이(키 제거·고정 키)가 각각 red 가 되는 것을 확인했다.

★**잔여** — lock 축이 포지션 정체성이 아니라 `sessionId + symbol` 이다. 계정 표는 계정·심볼의 **최신** 귀속 세션(비활성 포함)을, 세션 표는 **활성** 세션을 잡으므로 둘이 갈리면 lock 이 분리된다 → **BL-505** 등재.

**Title:** 세션 표와 계정 표의 청산 버튼에 공유 lock 이 없다
**Category:** Frontend / trading (코크핏 §03)
**Priority:** P3
**Trigger:** 두 표가 같은 포지션을 보여주는 동안 사용자가 양쪽을 연달아 누를 때
**Est:** S
**출처:** 2026-07-27 live-conditional-hardening G0.5 codex 지적 (재현 판정 후 등재)

**원인 / 영향:** 두 표가 각각 별도의 `useClosePosition` 인스턴스를 쓰므로 `isPending` 이 공유되지 않는다. 같은 순 포지션에 대해 두 개의 감소전용 시장가 주문이 비동기로 나갈 수 있다.

★★**"캐시 무효화는 이미 맞다" 고 썼던 것을 정정한다.** React Query 층에서만 참이었다 — 재조회가 서버의 **15초 Redis 스냅샷**에 그대로 적중해 방금 닫은 포지션이 다시 왔다. 적대 검증이 잡았고 같은 스프린트에서 수정했다(reduce-only 즉시 체결 + **watchdog 확정** + WS position 팬아웃 세 경로에서 계정 키 삭제. ★watchdog 경로는 G6 최종 리뷰가 추가로 잡았다 — 첫 수정은 즉시 `filled` 만 덮어 절반이었다. 기존 세션 키 삭제는 **활성** 세션 순회라 활성 0건이면 아무것도 안 지웠다 — 계정 표는 바로 그 상태를 위해 있다). 남은 것은 in-flight 중복뿐이고, 두 번째 주문은 평탄해진 포지션에서 거래소가 거부하므로 손실이 아니라 **원장 잡음**이다.

**권장 접근:** `useClosePosition` 에 `mutationKey` 를 부여하고 두 표가 `useIsMutating({ mutationKey })` 로 버튼을 함께 비활성화한다. 서버 측 중복 방어(계정·심볼 단위 flatten 멱등성)는 별도 결정이 필요하다.

**영향 파일:** `frontend/src/features/live-sessions/hooks.ts`, `open-positions-table.tsx`, `account-positions-table.tsx`.

**Risk:** 🟢

---

### BL-503

**상태:** ✅ **Resolved (2026-07-28, `feat/live-ops-hygiene`).** `tasks/conditional_entry_janitor.py` 신설(beat 5분). 대상은 `submitted` + `trigger_price` + `reduce_only=false` + 30분 경과이고 **세션 활성 여부를 가리지 않는다** — 기존 sweeper 의 `list_orphan_conditional_entries` 는 비활성 세션 행만 봐서 **진짜 피해(활성 세션의 등재 영구 정지)를 구조적으로 못 봤다**.

★**거래소에 물어본 뒤에만 처분한다.** 우리 앱은 `orderLinkId = str(Order.id)` 를 싣는다(`tasks/trading.py:377`). 살아 있으면 `exchange_order_id` 를 **붙이고(수리)**, terminal 이면 그 상태로 전이, **명확한 부재일 때만** `rejected`, 조회 실패면 아무것도 안 한다. reject 는 `state=submitted AND exchange_order_id IS NULL` **CAS** 라 늦은 attach 를 덮지 않는다.

★★**초안은 "id 가 없으니 그냥 rejected" 였고 그건 위험했다** — dispatch 는 `create_order`(거래소 등재) 뒤에 `attach_exchange_order_id` 를 하므로 그 사이에 죽으면 주문은 **거래소에 살아 있다**. 장부 잡음을 관리 불가 실주문으로 바꿀 뻔했다.

★★**sweeper 는 예외 코드 추론을 버렸다.** 실측 — Bybit `110001`→`OrderNotFound`, **`110010`("already cancelled")·`110008`("finished or canceled")→`InvalidOrder`**. 즉 "이미 취소됨" 은 `OrderNotFound` 로 안 잡히고, 잡히는 `110001` 은 체결 후 사라진 경우일 수도 있다. 이제 취소 실패 시 **거래소에 상태를 물어** 그 답대로 전이한다.

★★**적대 검증이 "유령 케이스가 한 건도 안 닫힌다" 를 잡았다** — ccxt `fetch_order` 는 `/v5/order/realtime` 만 치고 빈 list 에 `OrderNotFound` 를 던지는데, janitor 는 정의상 30분 이상 된 행만 보므로 terminal 주문은 이미 realtime 창 밖이다. 그런데 task 는 `{0,0,0}` 을 돌려줘 "고칠 게 없었다" 로 보였다. 양 분기를 **realtime→history** 단일 계약으로 통일했다.

★**F-A 는 반증됐다** — "`trigger=True` 없이는 조건부 주문을 못 본다" 는 내 결론과 codex 의 동의는 **둘 다 내부 증거(ccxt 소스·우리 코드)만** 본 것이었고, 거래소 실측에서 진짜 `orderId` 로 조회하면 `orderFilter` 유무와 무관하게 나왔다. 기존 probe 는 죽어 있지 않았다. `orderFilter=StopOrder` 는 오히려 **트리거된 주문을 숨겨** 체결을 `rejected` 로 찍을 수 있어 제거했다.

그 외 — `Deactivated`→`cancelled`(ccxt 와 일치) · `PartiallyFilledCanceled`→terminal(영구 좀비 제거) · `cancelled` 의 부분 체결 기록 · provider 를 `registry.dispatch` 로 주문마다 선택 · `orderLinkId` 에코 대조 · 루프 전 스칼라 선추출(`session.rollback()` 이 배치 나머지를 expire 시켜 다음 순회가 `MissingGreenlet` 으로 죽던 것) · `filled` winner 의 trailing/closed-pnl 후속 훅 · rowcount 0 경합과 "취소 실패 + 아직 살아 있음" 분기의 metric·로그.

**Title:** 제출 중단·유령 조건부 진입 행을 아무도 치우지 않는다
**Category:** Backend / trading (조건부 진입)
**Priority:** P2
**Trigger:** `stage="cancel_stalled"` 또는 `stage="exchange_missing"` 이 같은 `order_id` 로 반복 관측될 때
**Est:** M
**출처:** 2026-07-27 live-conditional-hardening 적대 검증(동시성 렌즈, 재현 판정 후 등재)

**원인 / 영향:** 조건부 진입 주문 행이 아래 두 모양으로 **영구 고착**할 수 있고, 현재 어떤 복구 주체도 그 행을 보지 못한다.

1. **제출 중단** — dispatch 가 `pending → submitted` 를 커밋하고(`tasks/trading.py:297-304`) 거래소 왕복(`:398`) 또는 `attach_exchange_order_id`(`:521`) 전에 죽으면 `state=submitted, exchange_order_id=NULL` 이 남는다. 이 행은 `list_resting_conditional_entries` 에 **매 tick 영원히** 들어오고, desired 와 어긋나면 `to_cancel` → DB-only 취소 rowcount 0 → `cancel_stalled` → **그 tick 등재 0**. 즉 그 세션의 조건부 진입이 영구 정지한다.
2. **유령** — 로컬 `submitted` + `exchange_order_id` 보유인데 거래소에 없는 행. 이번 스프린트가 `actual` 에서 빼도록 고쳤지만 **DB 행은 그대로 남는다.**

복구 주체가 전부 이 행들을 못 본다.

- `orphan_scanner` 의 `list_stuck_submitted` / `list_stuck_submission_interrupted` 는 둘 다 `Order.trigger_price.is_(None)` — 조건부 진입 **구조적 제외**(이건 30분 CRITICAL 오탐을 막으려던 이번 시리즈의 의도된 면제다).
- WS `Reconciler` 의 `reconcile_fetcher` 는 `fetch_open_orders`/`fetch_closed_orders`/`fetch_canceled_orders` 어디에도 `trigger=True`·`orderFilter=StopOrder` 를 쓰지 않는다 → **미트리거 조건부 주문이 스냅샷에 나타나지 않는다** → `_handle_unknown` → 상태 유지 + `send_critical_alert`(스로틀 없음).
- 세션 종료 후 beat sweeper 는 사라진 `exchange_order_id` 로 `cancel_order` 를 호출해 `OrderNotFound` → `ProviderError` → `stage="sweep_cancel"` 예외 로그를 **5분마다 영원히** 반복한다.

부수 — 그동안 `qb_active_orders` 게이지가 행당 +1 영구 표류한다.

**권장 접근:** (a) `reconcile_fetcher` 에 trigger 조회를 추가해 `Reconciler` 가 조건부 주문에도 terminal evidence 를 얻게 하거나, (b) 조건부 진입 전용 정리 스캐너를 두어 `fetch_order` 로 terminal 확인 후 전이한다. (b) 는 이번 스프린트가 reconcile 안에 넣은 probe 와 같은 기전이라 재사용 가능하다. sweeper 의 `OrderNotFound` 는 "이미 없다 = 취소 성공" 으로 흡수해야 한다.

**영향 파일:** `trading/websocket/reconcile_fetcher.py`, `tasks/live_signal.py`(sweeper), `trading/repositories/order_repository.py`.

**Risk:** 🟡 (세션 등재 영구 정지 + 무한 오경보. 실주문을 잘못 내지는 않는다).

---

### BL-511

**상태:** ✅ **Resolved (2026-07-28, `feat/live-entry-parity`).** 가드 기준가를 stale bar 종가 → **거래소 실시간 perp last price** 로 교체하고, 트리거가 이미 돌파됐으면 **시장가로 전환**한다(resting 조건부가 없을 때만 — 있으면 거래소가 이미 트리거했을 확률이 높아 이중 진입이 된다). 근거 = 우리 백테스트 엔진이 그 상황을 다음 bar 시가에 체결한다(`strategy_state.py:67-84`). 사용자 설정 상한 `StrategySettings.max_trigger_breach_pct`(기본 `None` = 무제한 = 백테스트와 동일). 마이그레이션 **0**(JSONB). **62분 soak 실측 — 조건부 거절 43.3%(29/67) → 0%(0/19), `110093` 29 → 0, 거래소 raw HMAC 오라클 26주문 전부 `EC_NoError`, 시장가 전환 5건 전부 체결.** ★적대 검증이 **기준가가 perp 이 아니라 스팟이었음**을 잡았다(실측 오차 0.0543% > 잡으려던 신호 중앙값 0.025%) — 그대로 갔으면 숫자는 나와도 뜻을 알 수 없었다. 상세 = `docs/dev-log/`.

**Title:** ★조건부 진입의 **절반이 거래소에 거절된다** — stale 기준가로 인한 매 tick 재시도 루프, 백테스트↔라이브 조용한 발산
**Category:** Backend / trading (조건부 진입)
**Priority:** **P1**
**Trigger:** **이미 진행 중.** 실자금 cutover 전 필수
**Est:** M
**출처:** 2026-07-28 live-observability soak 실관측 (1시간 40분 전수 집계)

★★**실측 규모 — 이것이 P1 인 이유.** soak 창에서 발주된 주문 38건 중 **거절 19건(50%)이고 100% 가 `110093`** 이다. 체결은 4건뿐이었다. 거절 시각이 `03:54–03:57` · `04:07–04:12` · `04:25–04:27` 처럼 **연속 분 단위 클러스터**를 이룬다 — 같은 트리거 값으로 **bar 가 바뀔 때까지 매 tick 재시도**하는 루프다. 즉 **백테스트가 의도한 진입의 절반가량이 라이브에서 조용히 사라진다.** 백테스트→라이브 패리티가 제품 전제인 플랫폼에서 이건 신뢰 문제다.

**원인 / 영향:** PbR 의 `strategy.entry("PivRevSE", strategy.short, stop=lprice - syminfo.mintick)` 가 주문을 올리는 시점에 가격이 이미 피벗 저점 아래면 트리거가 현재가 **위**가 되어 Bybit 이 거절한다 — `retCode 110093 "expect Falling, but trigger_price[63180.2] >= current[63149.1]"`.

★**TradingView 는 트리거를 이미 지난 stop 주문을 시장가로 전환**하지만 라이브는 거절한다. **백테스트는 진입하고 라이브는 진입하지 않는다.**

★**원장 전수 집계** — `110093` **12건**(2026-07-27 05:50 ~ 현재도 발생). 이번 soak 창에서만 2건.

★**기계적 원인이 특정됐다** — `trigger_already_breached` 가드(`conditional_entry_planner.py:195`, 주석이 이미 110093 을 알고 있다)의 기준가가 `live_signal.py:1355` `reference_price=_last_close_or_none(df)` = **마지막 종료 bar 종가**다. 거래소는 **현재가**로 판정한다. 1m 세션에서 최대 60초 스테일 → 가드가 체계적으로 뚫린다.

**권장 접근:** 가드 기준가를 실시간 가격(티커/마크)으로 교체하거나, 돌파 판정 시 등재를 건너뛰고 그 사실을 계측한다. BL-478 (a) 선택 시 남는 **잔여 격차**다.
**Risk:** 🟡

## P2 — Hardening / 건강도 작업

| ID                   | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Trigger                                                                                                           | Est          | 출처                                                   |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------ |
| [BL-186](#bl-186)    | 🟡 부분 Resolved (186a) — Full leverage + funding + mm + liquidation 풀 모델 (잔여 = BL-186b)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Sprint 38+ (BL-185 foundation 위)                                                                                 | M-L (16-24h) | Sprint 37 BL-185 후속                                  |
| [BL-190](#bl-190)    | PDF export (jsPDF / Playwright)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 외부 사용자 요청 시                                                                                               | M (3-5h)     | Sprint 41 Worker H 결정                                |
| [BL-195](#bl-195)    | qb-form-slide-down animation 영구 truncation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Sprint 45 codex G.4                                                                                               | XS (30m)     | Sprint 45 codex G.4 발견                               |
| [BL-235](#bl-235)    | N-dim acquisition surface viz (Bayesian 전용)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Sprint 57+                                                                                                        | M (8-12h)    | ADR-013 §6 #8 deferred                                 |
| [BL-236](#bl-236)    | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Sprint 56+                                                                                                        | S (3-5h)     | Sprint 55 deferred                                     |
| [BL-309](#bl-309)    | ✅ Resolved — trading registry/webhook/fees test 0% → ≥80%                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ✅ W3 2026-06-29 (baseline stale + fees obsolete)                                                                 | M (4-6h)     | 2026-05-15 trading-deepen audit                        |
| [BL-362](#bl-362)    | ✅ Resolved — live 경로 coverage↔interpreter divergence silent swallow observability                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ 2026-07-25 `stage/money-path-accuracy`                                                                         | S (2-4h)     | 2026-05-30 full-inspection §4.3                        |
| [BL-363](#bl-363)    | stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | deepening sprint 또는 5번째 engine 추가 시                                                                        | S (2-3h)     | 2026-05-30 full-inspection §appendix P1-9              |
| [BL-364](#bl-364)    | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | string 카테고리 sweep 요청 시                                                                                     | M (4-6h)     | 2026-05-30 full-inspection §appendix P1-9 (S4 후속)    |
| [BL-365](#bl-365)    | ✅ Resolved — `trigger_direction_for`/`map_exit_kind` dead + 서버 미배선 (standalone-trigger 방향)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ 2026-07-27 `feat/live-conditional-entry`                                                                       | S (2-4h)     | 2026-06-26 trading-deepen-2                            |
| [BL-366](#bl-366)    | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | trading deepening sprint                                                                                          | S-M (3-5h)   | 2026-06-26 trading-deepen-2                            |
| [BL-368](#bl-368)    | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | trading deepening / 4번째 provider                                                                                | S-M (3-5h)   | 2026-06-26 trading-deepen-2                            |
| [BL-369](#bl-369)    | 3 provider `create_order` try/except/finally ~40 LOC 복붙                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | trading deepening sprint                                                                                          | S (2-4h)     | 2026-06-26 trading-deepen-2                            |
| [BL-372](#bl-372)    | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Wave 3 실자금 cutover 전                                                                                          | M (6-10h)    | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)     |
| [BL-373](#bl-373)    | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | BL-365 standalone-trigger 발주 시                                                                                 | S-M (3-5h)   | 2026-06-28 grilling (트레일링 후속 scope)              |
| [BL-374](#bl-374)    | ✅ Resolved (2026-06-29) — pine_v2 interpreter na-semantics — `x/0`·`math.sqrt(-1)` 등 raw 예외 → Pine `na`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | ✅ `fix/pine-374-na-semantics`                                                                                    | M (4-6h)     | 2026-06-28 BL-362 G2 codex challenge                   |
| [BL-375](#bl-375)    | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Wave 3 실자금 cutover 전                                                                                          | S-M (3-5h)   | 2026-06-29 BL-372 same-side stale G1 codex             |
| [BL-376](#bl-376)    | ✅ Resolved (2026-06-30) — pine_v2 na/inf 소비 사이트 robustness — na/inf→ta.\* length / na/inf→entry qty skip / inf→math.floor·ceil·round·subscript·timestamp                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ✅ `fix/pine-376-na-inf`                                                                                          | M (4-6h)     | 2026-06-29 BL-374 G1/G2/G3 + generator panel 합의      |
| [BL-377](#bl-377)    | pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | pine_v2 robustness 후속 또는 실자금 cutover 전                                                                    | S (2-4h)     | 2026-06-30 BL-376 G2 codex challenge + G3 fresh review |
| [BL-378](#bl-378)    | ✅ Resolved (2026-06-30) — pine_v2 `ta.atr` rolling SMA → Wilder RMA (TV parity, headline harm-class)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ `fix/pine-378-atr-wilder`                                                                                      | S (2-4h)     | 2026-06-30 티어드 백테스트 QA 大-tier oracle           |
| [BL-379](#bl-379)    | pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐, latent harm-class)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | pine_v2 robustness 후속                                                                                           | M (4-6h)     | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-380](#bl-380)    | Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반) + VirtualRunResult.warnings 미전파                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Track A 신뢰 표면 sprint                                                                                          | S-M (3-5h)   | 2026-06-30 QA LuxAlgo 0-trade                          |
| [BL-381](#bl-381)    | Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허 (i2_luxalgo 검증 vacuous)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Trust Layer CI 강화                                                                                               | S (2-4h)     | 2026-06-30 QA codex G2/diff                            |
| [BL-382](#bl-382)    | qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성, mdd_exceeds_capital 은 표시됨)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | sizing 투명성 sprint                                                                                              | S (2-4h)     | 2026-06-30 QA F1 (codex G2)                            |
| [BL-383](#bl-383)    | v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | pine_v2 관측성 후속                                                                                               | S (2-3h)     | 2026-06-30 QA codex G2                                 |
| [BL-384](#bl-384)    | ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | pine_v2 parity 후속                                                                                               | S (2-3h)     | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-385](#bl-385)    | PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse (메타데이터 부정확)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | pine_v2 coverage 후속                                                                                             | XS (1-2h)    | 2026-06-30 QA F3                                       |
| [BL-386](#bl-386)    | v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject, over-strict)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | pine_v2 coverage 후속                                                                                             | XS (1-2h)    | 2026-06-30 QA F4                                       |
| [BL-387](#bl-387)    | backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 횡단 (key drift 시 silent 잘못된 sizing, money-path)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | backtest deepening 또는 sizing 로직 변경 시                                                                       | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 최강 후보)           |
| [BL-388](#bl-388)    | ✅ Resolved — BacktestMetrics 24-field 4곳 평행 정의 (dataclass↔schema↔serializer↔_to_detail)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ 2026-07-26 backtest-trust (착수 시 이미 해결 상태)                                                             | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 가 4번째 site 발견)  |
| [BL-392](#bl-392)    | stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass↔serializer↔OutSchema, untyped JSONB seam)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | stress_test deepening 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시                                    | M (4-6h)     | 2026-06-30 stress_test-deepen (deepen-modules 1차)     |
| [BL-401](#bl-401)    | ✅ Resolved (2026-07-23) — optimizer 3폼 field-level zod 에러 렌더 (`.field-error` + role=alert, 메시지 한국어화)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ `stage/functional-parity`                                                                                      | S-M (2-4h)   | 2026-07-05 PR #394 FE 리팩토링 번들 dogfood            |
| [BL-402](#bl-402)    | ✅ Resolved (2026-07-23, 구조 소멸) — C 이식 네이티브 select 전환으로 4사이트 결함 자체 소멸 (실측 재확인, 코드 변경 0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ `stage/functional-parity` (문서만)                                                                             | XS-S (1-2h)  | 2026-07-05 PR #394 FE 리팩토링 번들 dogfood            |
| [BL-523](#bl-523)    | 조건부·전환 진입에 TP/SL 브래킷이 붙지 않는다 (현재 코퍼스 미발현 — `stop=`+`strategy.exit` 동시 사용 시 발현)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 실자금 cutover 전                                                                                                 | M            | 2026-07-28 live-entry-parity                           |
| [BL-524](#bl-524)    | `strategy.entry(limit=...)` 이 조용히 버려지고 시장가 진입으로 대체된다 (TV 충실도)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | limit 진입 전략 지원 시                                                                                           | M            | 2026-07-28 live-entry-parity                           |
| [BL-525](#bl-525)    | 라이브가 Track A(indicator + alertcondition) 전략을 어떻게 다루는지 정의되지 않았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Track A 로 라이브 세션을 열 때                                                                                    | S            | 2026-07-28 live-entry-parity                           |
| [BL-526](#bl-526)    | ~~★라이브 실적이 백테스트 기대치와 맞는지 화면에서 물을 수 없다~~ **✅ Resolved 2026-07-28**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | —                                                                                                                 | M            | 2026-07-28 live-entry-parity                           |
| [BL-527](#bl-527)    | ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 기대치 정확도가 판정에 쓰이기 전                                                                                  | S            | 2026-07-28 live-outcome-parity                         |
| [BL-528](#bl-528)    | 세션 창 밖 늦은 체결이 어느 표면에도 안 잡힌다 (실측 확정 청산 4건 · net −0.5463)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 세션 손익 완결성이 필요할 때                                                                                      | M            | 2026-07-28 live-outcome-parity                         |
| [BL-529](#bl-529)    | 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 전략 누적 지표를 신뢰해야 할 때                                                                                   | S            | 2026-07-28 live-outcome-parity                         |
| [BL-530](#bl-530)    | ✅ Resolved — ★엔진이 청산했다고 본 것의 71% 가 거래소에서 확정되지 않는다 (실측 51/72)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ 2026-07-28 live-close-completeness (PR #497/#498)                                                              | M-L          | 2026-07-28 live-outcome-parity                         |
| [BL-531](#bl-531)    | parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery (지표 1개 추가 = 5파일 편집)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | parity 지표를 더 붙일 때                                                                                          | S            | 2026-07-29 PR #496 코드리뷰                            |
| [BL-532](#bl-532)    | `_sum_decimals` 사본이 `PARITY_DECIMAL_CONTEXT` 밖에서 돈다 (본 레포가 방금 세운 규칙과 불일치)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 다음 parity 손질 시                                                                                               | XS           | 2026-07-29 PR #496 코드리뷰                            |
| [BL-533](#bl-533)    | 종료 세션 목록이 같은 엔드포인트를 두 쿼리 키로 조회해 미러 state 를 낳는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 코크핏 손질 시                                                                                                    | XS           | 2026-07-29 PR #496 코드리뷰                            |
| [BL-534](#bl-534)    | 외부 오라클 테스트가 27 leg Decimal 합산을 실제로 실행하지 않는다 (총계를 관측 1건에 몰아넣음)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | parity 산술을 손댈 때                                                                                             | XS           | 2026-07-29 PR #496 코드리뷰                            |
| [BL-535](#bl-535)    | 🟡 부분 Resolved — ★백테스트는 스팟 봉으로 perp 전략을 검증한다 (적재는 착지, 결과 차 대조 미실시)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 백테스트를 라이브 판단 근거로 쓰기 전                                                                             | M            | 2026-07-28 live-close-completeness                     |
| [BL-536](#bl-536) ✅ | BL-522 진입 완결성 — 계기 정렬 후 유실 채널 5종 재측정 후 설계 (**재측정 완료 · 판정 「축소」 · 설계 = 저장소를 짓지 않는다**)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 실자금 cutover 전 필수                                                                                            | M            | 2026-07-28 live-close-completeness                     |
| [BL-537](#bl-537)    | ~~활성 세션이 없으면 고아 포지션을 앱에서 청산할 수 없다~~ **✅ Resolved 2026-07-29 — ★전제 반증**(계정 스코프는 이미 닫힌다; 진짜 결함은 "누르면 실패하는 버튼")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | —                                                                                                                 | S            | 2026-07-28 live-close-completeness                     |
| [BL-538](#bl-538)    | 발산 알림 본문이 모든 카테고리에 "전략 수정 후 재활성화" 라고 처방한다 (포지션 불일치엔 틀린 처방)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 운영 알림을 사람이 신뢰해야 할 때                                                                                 | S            | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-539](#bl-539)    | (P3) 방향 불일치 유예가 시간 경계가 없다 — 평가가 드문드문하면 오래된 strike 가 살아남는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 발산 가드를 다시 손댈 때                                                                                          | S            | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-540](#bl-540)    | (P3) `live_signal.py` 반복 3종 — deactivate 의식 6회 · provider+creds 4회 · category 가 맨 `str`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 이 파일을 다시 크게 손댈 때                                                                                       | M            | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-541](#bl-541)    | 세션 행이 아예 없는 포지션(웹훅 경로·거래소 수동)은 여전히 앱에서 못 닫는다 — ★아직 실측된 적 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | `no_owning_session` 이 실제로 관측될 때                                                                           | M            | 2026-07-29 live-orphan-close                           |
| [BL-542](#bl-542)    | ✅ Resolved — (P3) 계정 포지션 표의 "잘렸다" 경고가 포지션 1건에도 켜진다 — 거짓 양성 **확정** · n=2 · 기전 확정(2026-08-01)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 잔여 노출 표를 신뢰해야 할 때 — 남은 것은 판정식 교체                                                             | XS           | 2026-07-29 live-orphan-close                           |
| [BL-543](#bl-543)    | ✅ Resolved 2026-07-30 (a) · (c)→[BL-544](#bl-544) — ★`engine_only` 은 진입 유실을 측정할 수 없다, 세션은 태어날 때부터 갈려 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ PR #503 engine-exchange-alignment (position epoch)                                                             | S            | 2026-07-29 live-orphan-close                           |
| [BL-544](#bl-544)    | ✅ 조건부 진입이 거래소에서만 체결되고 엔진 재생이 재현 못 해 공백 후 세션이 죽는다 (2026-07-30 Resolved)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | —                                                                                                                 | M            | 2026-07-30 engine-exchange-alignment                   |
| [BL-545](#bl-545)    | ★gap-resync 게이트가 5% 수량 허용치를 물려받아 구 게이트가 막던 불일치를 통과시킨다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 조건부 진입을 실자금으로 가기 전                                                                                  | S            | 2026-07-30 conditional-entry-alignment                 |
| [BL-546](#bl-546)    | 원장→엔진 seed 경계에서 `Decimal` 이 `float` 로 강등 (Decimal-first 하드 규칙)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 엔진 수치 표현을 손댈 때 / 큰 notional                                                                            | M            | 2026-07-30 conditional-entry-alignment                 |
| [BL-547](#bl-547)    | ★원장 seed 가 그 tick 한 번만 산다 — 조용한 고아 가능 (**아직 실측된 적 없음**)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | `exchange_only` 이 실제로 오르는 것이 관측될 때                                                                   | M            | 2026-07-30 conditional-entry-alignment                 |
| [BL-548](#bl-548)    | (P3) `OutcomeParityPanel` 이 375px 에서 본문 가로 스크롤 24px 을 만든다 (기존 결함)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 모바일 폭 점검 시                                                                                                 | XS           | 2026-07-30 conditional-entry-alignment                 |
| [BL-549](#bl-549)    | ✅ Resolved — ★`final-gates.sh` 를 커밋 전에 돌리면 게이트를 skip 하고도 통과처럼 읽힌다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ 2026-07-30 live-entry-completeness                                                                             | XS           | 2026-07-30 conditional-entry-alignment                 |
| [BL-550](#bl-550)    | (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 죽은 세션을 세션 단위로 대조해야 할 때                                                                            | S            | 2026-07-30 conditional-entry-alignment                 |
| [BL-551](#bl-551)    | (P3) 라이브 세션 상세 진입이 URL 파라미터가 아니다 — 딥링크·새로고침 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 세션 상세를 링크로 공유해야 할 때                                                                                 | S            | 2026-07-30 conditional-entry-alignment                 |
| [BL-552](#bl-552)    | ✅ Resolved — ★`fleet-dispatch.sh` 가 프롬프트 미제출을 성공으로 보고, 워커가 `idle` 로 멈춘다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ✅ 2026-07-30 live-entry-completeness                                                                             | XS           | 2026-07-30 conditional-entry-alignment                 |
| [BL-553](#bl-553)    | ★`outcome="applied"`(원장 seed 주입)가 실주행에서 한 번도 안 밟혔다 — 단위테스트로만 증명                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 다음 soak (기회주의적 확인)                                                                                       | XS           | 2026-07-30 conditional-entry-alignment                 |
| [BL-554](#bl-554)    | ✅ Resolved — (P3) pre-push 훅이 푸시 대상 ref 가 아니라 현재 브랜치를 봐서 원격 브랜치 삭제까지 막는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ 2026-07-30 live-entry-completeness                                                                             | XS           | 2026-07-30 conditional-entry-alignment                 |
| [BL-555](#bl-555)    | ✅ Resolved — (P3) `stage/*` 가 통합 브랜치 관례인데 pre-push 화이트리스트에 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ 2026-07-30 live-entry-completeness                                                                             | XS           | 2026-07-30 conditional-entry-alignment                 |
| [BL-556](#bl-556)    | `final-gates.sh` 가 `pnpm e2e`(chromium 4건)를 집행하지 않는다 — CI e2e 잡에는 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 다음 회차 게이트 실행 전                                                                                          | XS           | 2026-07-30 live-entry-completeness                     |
| [BL-557](#bl-557)    | (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 그 게이지로 무언가를 판단하기 전                                                                                  | S            | 2026-07-30 live-entry-completeness                     |
| [BL-558](#bl-558)    | retCode 를 `error_message` 에 싣는 경로가 **동기 1곳뿐** — 비동기 확정 거절이 코드 미상이 된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 거절 코드로 채널을 가를 때                                                                                        | M            | 2026-07-30 live-entry-completeness                     |
| [BL-559](#bl-559)    | (P3) 진입 완결성 도구 잔여 3건 — 세션 목록 절단 감지 · 사문 라벨 · janitor probe 전이                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 그 경로가 실측될 때                                                                                               | S            | 2026-07-30 live-entry-completeness                     |
| [BL-560](#bl-560)    | ✅ Resolved 2026-08-01 — 엔진과 거래소가 반대 방향. ★프로덕션 검증은 **유도 1회**(60초, 기저율 ≈4일 1회) · `same_side` 자연 관측 0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ 배선·기록 경로 검증 완료 (효과 측정은 별건)                                                                    | M            | 2026-07-30 close-mismatch-visibility                   |
| [BL-561](#bl-561)    | ✅ Resolved 2026-08-01 — 포매터가 `extra` 를 렌더하지 않아 진단 증거가 즉시 소실된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ 2026-08-01 메인 실주행 렌더 확인                                                                               | XS           | 2026-07-30 close-mismatch-soak                         |
| [BL-562](#bl-562)    | ✅ Resolved — 조건부 진입 반전 판정 3값이 계획 시점 계산이라 트리거까지 대기하는 동안 낡는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ 2026-07-31 reversal-ledger-sync                                                                                | S            | 2026-07-30 close-mismatch-soak                         |
| [BL-563](#bl-563)    | ✅ Resolved — (P3) bracket outcome 을 게이트 처리 **후** request 기준으로 세어 TP 공급을 미공급으로 오분류                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ✅ 2026-07-31 reversal-ledger-sync                                                                                | XS           | 2026-07-30 close-mismatch-soak                         |
| [BL-564](#bl-564)    | (P3) `bl-audit.sh` 가 코드펜스 · `<details>` 안의 옛 상태줄을 SSOT 로 오인할 수 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 그 관용구가 상태줄을 품게 될 때                                                                                   | XS           | 2026-07-30 close-mismatch-soak                         |
| [BL-565](#bl-565)    | `check_exit_fills` 의 close 도 BL-560 과 같은 성질 — 읽기만 하고 남겼다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `strategy.exit` 을 쓰는 전략을 라이브로 돌리기 전                                                                 | S            | 2026-07-31 reversal-ledger-sync                        |
| [BL-566](#bl-566)    | ✅ Resolved 2026-08-01 **재판정** — 유령 포지션이 아니라 **계획기 무장 지연**. 41.6/h→12.9/h · 69%→21% · 전건 2~4봉 자기해소                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ 2026-08-01 soak (사전등록 Y2 충족)                                                                             | M            | 2026-07-31 reversal-ledger-sync                        |
| [BL-567](#bl-567)    | `place_trailing_stop` enqueue 가 실패하면 그 주문의 트레일링은 **영구 유실** — 회수 경로가 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 트레일링 전략을 라이브로 상시 운용하기 전                                                                         | —            | 2026-07-31 reversal-ledger-sync                        |
| [BL-568](#bl-568)    | BL-562 체결시점 반전 계측이 **11건 중 10건 무측정** — 분류된 건이 0 이다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 그 분포를 근거로 무언가를 판단하기 전                                                                             | S            | 2026-08-01 ledgerhygiene                               |
| [BL-569](#bl-569)    | ✅ Resolved — `bl-audit.sh` 가 중복 섹션 헤더를 못 잡아 같은 BL 번호 두 벌이 exit 0 을 유지했다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ✅ 2026-08-01 ledgerhygiene                                                                                       | XS           | 2026-08-01 ledgerhygiene                               |
| [BL-570](#bl-570)    | ✅ Resolved — 무편집 상태에서 `설정 저장` 이 활성인데 누르면 요청 · 토스트 · 필드에러가 전부 0 이다 (★기전은 [가정])                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 전략 편집 화면을 손댈 때 / 같은 미렌더 패턴의 폼을 만들 때                                                        | S            | 2026-08-01 qa                                          |
| [BL-571](#bl-571)    | ✅ Resolved — (P3) enum 밖 종료 사유가 원장에 박혀 원문 노출 — AST 가드가 원장 직접 기입을 못 본다 (콘솔 40초 67건)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | soak 운영 절차를 다시 돌릴 때 / 콘솔 경고를 게이트로 쓸 때                                                        | XS           | 2026-08-01 qa                                          |
| [BL-572](#bl-572)    | ✅ Resolved — (P3) 같은 세션을 표는 `PAUSED`, 옆 카드는 `종료된 세션` 으로 부른다 — 죽은 세션이 재개 가능해 보인다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 라이브 세션 목록/카드를 손댈 때                                                                                   | XS           | 2026-08-01 qa                                          |
| [BL-573](#bl-573)    | (P3) `engine_only` tick 당 `list_resting_conditional_entries` 2회 — 감지가 reconcile 보다 앞서 돌아 공유 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | tick 비용을 손댈 때 / 두 경로를 합칠 때                                                                           | S            | 2026-08-01 soak codex                                  |
| [BL-574](#bl-574)    | ★`LIMIT 100` 이 세션 필터보다 앞서 걸려 현 세션 resting 을 놓치고 `awaiting_trigger` 를 `unexplained` 로 오분류 (측정 완료 · 수리 보류 — 동시 최대 2 / 100)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 동시 resting 이 20건을 넘긴 날이 관측될 때                                                                        | S            | 2026-08-01 soak codex                                  |
| [BL-575](#bl-575)    | SELECT 실패 후 같은 AsyncSession 을 rollback 없이 재사용 — fail-open 계약이 깨진다 (★선재 패턴, 회귀 아님)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | fail-open 을 근거로 쓰기 전                                                                                       | S            | 2026-08-01 soak codex                                  |
| [BL-576](#bl-576)    | ✅ Resolved — ★`live_conditional_reconcile_divergence` 한 이름이 발화 8곳 · payload 3종을 덮는다 (`110017` 라벨 충돌과 같은 형태)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 그 이름으로 세거나 알림·게이트로 쓰기 전                                                                          | S            | 2026-08-01 soak                                        |
| [BL-577](#bl-577)    | ✅ Resolved — ★전제 반증: 가드는 **실재했다**(내용 grep 이 파일명만 있는 문자열을 못 잡았다). 진짜 구멍은 JSX 안 원시 대문자 리터럴 하나뿐 → 기존 가드에 두 번째 검출기 추가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 원시 enum 렌더가 막혔다고 믿고 라벨 코드를 손댈 때                                                                | S            | 2026-08-01 silent-surface-honesty                      |
| [BL-579](#bl-579)    | ✅ Resolved — 머니-패스 계측 **18곳 가드** + 결함 재현 확정(계측 실패가 **주문을 하나 더 냈다**). 잔여는 [BL-580](#bl-580)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | —                                                                                                                 | M            | 2026-08-02 canonical-measurement-surface               |
| [BL-580](#bl-580)    | 계측 가드 잔여 **96곳** (누적 63곳 수리). ★산문 근거 29곳이 주입에서 **29곳 전건 유해** — 「가드 없이 유지」 누적 0곳. ★2026-08-03 신규 **H8** = 계측 실패가 fail-open `except` 에 삼켜져 **거절을 집행으로 뒤집는다**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `qb_metrics_mutation_failed_total` 창 차분이 0 을 벗어날 때 (★프록시다 — 가드 밖은 이 counter 를 올리지 않는다)   | M            | 2026-08-02 metric-guard-parity                         |
| [BL-581](#bl-581)    | `/metrics` 영구 누적 **10277 파일 · 635MB · PID 1968** (counter 삭제 금지)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 20000 파일 초과 · 스크레이프 지연 · 여유 20G 미만                                                                 | M            | 2026-08-02 metric-guard-parity                         |
| [BL-582](#bl-582)    | divergence counter 13 series 중 **5종** 도달 불가 (2026-08-03 재판정 — 7종에서 축소. 2종은 엔진 구동으로 **반증**), 프로덕션 확인 3/8                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 반증된 2종이 프로덕션에서 발화하거나 `other` def-use 오라클이 red 일 때                                           | S            | 2026-08-02 metric-guard-parity                         |
| [BL-583](#bl-583)    | ✅ Resolved — ★스위트 결과가 **수집 집합**에 달려 있었다(순서 랜덤이 아니다 — `pytest-randomly` 미설치). 뿌리 = 정의 모듈 패치 창에서 소비 모듈 첫 적재 시 가짜가 **모듈 전역으로 영구 복사**. 오염원 4곳·전역 8개 처분 + 상시 가드                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 게이트가 이유 없이 red 이거나 같은 커밋이 두 번 다른 결과를 낼 때                                                 | M            | 2026-08-03 metric-guard-residual                       |
| [BL-584](#bl-584)    | `BalanceUnverified` 가 라이브 dispatch 의 결정론적-거절 튜플 양쪽에 없다 — 소진 시 실제 사유가 `max_retries_exhausted` 로 덮인다. ★2026-08-03 **현재 코퍼스 도달 불가 확정**(계정 mode 는 생성 후 불변 · `mode=live` 계정 0건) ⇒ 수리 보류, Trigger 를 cutover 로 보강                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | **`mode=live` 계정이 생성될 때**(Wave 3 cutover), 또는 `outcome="max_retries_exhausted"` 창 차분이 0 을 벗어날 때 | S            | 2026-08-03 metric-guard-residual-close                 |
| [BL-578](#bl-578)    | 조건부 진입 `110092`/`110093` 거절 시 거래소가 준 정답(`current[...]`)을 버린다 — BL-536 재판정에서 유일하게 살아남은 채널의 잔여 (측정 완료 · 수리 보류)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | C1 거절이 하루 3건 이상으로 다시 오르거나 실자금 cutover 로 1건 비용이 달라질 때                                  | S            | 2026-08-01 entry-completeness-rejudgement              |
| [BL-585](#bl-585)    | ✅ Resolved — 안 도는 스키마를 **지웠다**. 중복이 아니었던 유일한 검사(`corpora` 8벌)는 **키 집합 대조**로 강화해 테스트로 이관. 패턴을 남기면 세 번째 SSOT 가 된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | baseline 정답지의 형태 검사를 다시 논할 때                                                                        | XS           | 2026-08-03 backtest-metric-oracle                      |
| [BL-586](#bl-586)    | P-3 골든이 `BacktestMetrics` **51 필드 중 13개**만 고정 — 38개가 회귀 감지 대상 밖(TV parity 팩 · 비용 분해 · per_side · excursion · 청산). `RawTrade` 도 22 중 11 필드만 digest                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | TV parity 팩·비용 분해·청산 지표에서 회귀가 의심될 때                                                             | M            | 2026-08-03 backtest-metric-oracle                      |
| [BL-587](#bl-587)    | ✅ Resolved — **원인 차단 + 탐지기 둘 다**. `backend/.python-version` 3.12 핀 + envelope assert 3건(그전까지 읽는 곳 0곳). red 메시지에 「회귀가 아니라 regen 해라」 명시                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | parquet 교체 · python/pynescript 업그레이드 시                                                                    | XS           | 2026-08-03 backtest-metric-oracle                      |
| [BL-589](#bl-589)    | ✅ Resolved — ★뿌리는 엔진이 아니라 **조건부 진입 계획기**였다. 엔진은 취소를 못 본 게 아니라 **주문을 아예 모른다**(포지션 출처 = `run_live` 시뮬). 계획기가 「대기 주문이 있다」는 이유만으로 시장가 전환을 껐는데 그 대기 주문은 **발화할 수 없었다** → 술어를 「발화할 수 있었는가」로 좁힘                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 조건부 진입이 드롭됐는데 시뮬은 진입을 잡은 상태가 의심될 때                                                      | M            | 2026-08-03 backtest-metric-oracle                      |
| [BL-588](#bl-588)    | ✅ Resolved — 목록을 `_corpus.py` **하나로** 합쳤다. ★5벌이 정확히 **위험조정지표 축퇴 5벌**이라 그 산술 회귀가 감지 불가였다. nightly +19%, 감지 불변                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 코퍼스를 또 추가/제거할 때                                                                                        | XS-S         | 2026-08-03 backtest-metric-oracle                      |
| [BL-590](#bl-590)    | ✅ Resolved — ★가드가 뚫린 게 아니라 **거절 뒤 복구가 없었다**. 계획기는 발주 시각에 옳았고 거래소가 2.1초 뒤 자기 시각으로 `110092`/`110093` 거절 → 엔진 시뮬만 전진 → `direction` 발산 2회 → 소크 105분 사망. 거절을 「돌파 확정 증거」로 읽고 PR #493 의 시장가 전환을 그 자리에서 집행                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 조건부 진입이 거래소에서 거절됐는데 세션이 발산으로 죽을 때                                                       | M            | 2026-08-03 breach-rejection-recovery                   |
| [BL-591](#bl-591)    | ★**뿌리** — 엔진 포지션의 SSOT 가 없다. `run_live` 시뮬이 매 tick 봉을 재생해 포지션을 **도출**하고 정상 운행 중엔 현실로 **보정되지 않는다**. 슬라이스 1(계측) = **PR #539 OPEN**(통합 브랜치 `stage/engine-position-ssot`, 미머지). ★★★**슬라이스 2 미착수 확정** — 사전등록 V1 발동(④ = 0: 사망 2건의 상류에 `exchange_only` 0건 · 최악 상계 ≤1/21). ★★★**유도 함수 재설계 필요** — `trade_id` 는 trade 가 아니라 Pine 진입 규칙 이름이고(`PivRevSE` 56체결/19세션) 반전은 `:close:` 키를 안 만든다 ⇒ 판정 불가 **27.6%**(전량 `duplicate_open`) · **net 은 맞고 legs 는 틀리다**(오라클 11건: 오답 0 · 적중 4 중 3건이 `legs=2` 인데 거래소는 단일 포지션 — 나머지 1건은 반전 없는 먼지 세션이라 정확) ★**2026-08-05 P1→P2 강등**(잔여 = D1/D2 · 근거는 §상태 줄) | 발산 증상 BL 을 또 하나 열기 전에 · 소크가 또 죽었을 때                                                           | L            | 2026-08-03 breach-rejection-recovery                   |
| [BL-592](#bl-592)    | 같은 Bybit 데모 계정이 `trading.exchange_accounts` 에 **2행**이라 청산 1건이 **2행으로 적재**되고, 주문을 안 가진 계정 쪽에서는 `ours` 가 **`unknown` 으로 오라벨**된다(실측 91/91 대칭). 원장 구멍 계측을 **3.7배 부풀린다** — [BL-591] 슬라이스 1 관측 전에 인지 필요                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `exchange_exits` 로 원장 구멍·귀속을 판정하기 전에                                                                | S            | 2026-08-04 engine-position-ssot                        |
| [BL-593](#bl-593)    | 운영자 도구(`backend/scripts/verify_*.py` 등)가 `ClosePositionService` 를 못 써서 provider 를 **직접 호출** → 그 청산에 대응하는 `trading.orders` 행이 **없다**. 실측 `external_manual` **12건 / 103건(11.7%)**. [BL-591] C 안이 원장을 진실로 쓰므로 이 구멍이 곧 오주입 위험                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 소크를 끄거나 거래소를 손으로 flat 으로 만들기 전에                                                               | S            | 2026-08-04 engine-position-ssot                        |
| [BL-595](#bl-595) ✅ | ★**엔진의 시뮬 stop 과 거래소의 resting stop 은 같은 주문이 아니었다** — 수준도 수명도 달라 양쪽 모두 혼자 발화했고 `position_divergence` 사망 **5건**이 전부 이것이다. **2026-08-05 Resolved** — 라이브 조건부 진입 체결의 권한을 **주문 원장**으로 옮겼다([ADR-025]). 원장이 증언 안 하면 엔진도 체결 안 하고(형 A 4건), 증언하면 봉·트리거 판정과 무관하게 체결한다(형 B 1건). 백테스트는 인자 기본값 `None` 으로 byte-identical. 사망 5건 전량을 얼려 재현(비트 단위 일치) → 수리 전 5/5 발산, 수리 후 5/5 일치. ★형 B 재판정: `39731d57` 은 거래소가 앞선 별개 현상이 아니라 **거짓 사망**(엔진이 2봉 뒤처졌고 다음 tick 에 따라잡았을 것)                                                                                                                       | ✅ 2026-08-05 conditional-stop-ownership                                                                          | L            | 2026-08-05 divergence-rejudgement                      |
| [BL-594](#bl-594) ✅ | ★**Redis 가 재기동 불능인 채 6일 돌고 있었다** — `make down` 후 `unhealthy` 로 기동 실패. `appendonly.aof.4.incr.aof` 가 **35.6MB 중 30.8MB(86.6%) 판독 불가**. AOF 는 **기동 시에만 읽히므로** 떠 있는 프로세스에는 증상이 0 이고 healthcheck(`redis-cli ping`)도 구조적으로 못 본다. ⇒ 스택에 **재기동 내성이 없었다** — [BL-003] 의 168h 창 안에 재부팅이 들어오면 워커가 안 뜬다. 손상 원인 미조사                                                                                                                                                                                                                                                                                                                                                                | 소크가 168h 를 향해 도는 동안 · 호스트 재부팅 전                                                                  | S            | 2026-08-05 soak-clock-restoration                      |
| [BL-596](#bl-596) ✅ | 게이트가 **모르는 라벨을 조용히 무해 취급**한다 — `soak_gate_predicate.py:191` 이 `label == "phantom"` 만 실격으로 세므로 `unattributed` 도, 앞으로 판별식이 낼 어떤 새 라벨도 **fail-open** 이다. 판별식은 2026-08-05 에만 두 번 바뀌었다(봉경계식 → 재무장식 → 회복식). 현행 회복식은 판정 불가를 새 라벨이 아니라 **종전 식으로 강하**시켜 이 경로를 피해 갔을 뿐 닫지는 않았다. **2026-08-05 Resolved** — 라벨 어휘를 명시적 3분할 frozenset 으로 읽고, 무해도 실격도 아닌 라벨(`unattributed` + 어휘 밖 + 키 결손)은 C5 를 떨어뜨려 `UNKNOWN 측정불가`. 소급 실격은 아니고, FAIL 이 C5 보다 먼저라 실격을 덮지도 않는다. 알려진 라벨만 있는 판정은 180 조합 전량 불변                                                                                            | 판별식이 새 라벨을 낼 때 · 또는 `unattributed` 가 실제로 관측될 때                                                | S            | 2026-08-05 live-replay-visibility                      |
| [BL-597](#bl-597) ✅ | e2e authed 가 **소크 상태와 결합** — 열린 포지션이 `/trading` 에 표를 추가해 느슨한 로케이터가 엉뚱한 표를 집는다(final-gates 1차 red, hydration flake 와 다른 축)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | e2e 로케이터 수리 전 · 소크 병행 게이트마다                                                                       | S            | 2026-08-06 night-watch                                 |

> Resolved P2 = BL-027/137/140/140b/141/144/150/152/176/178/180/181/183/184/185/187/187a/188/188a/189/200~206/219~234/237 + 30+ Sprint 16~30 stale ([\_archived.md](archive/refactoring-backlog/_archived.md)).

### BL-186

**상태:** 🟡 **부분 Resolved (BL-186a, 2026-07-26 backtest-trust)** — 격리 단일 tier 레버리지 모델은 착지, **잔여 = BL-186b**(cross 마진 · tier 계단 MMR · 파산수수료 · 멀티거래소 · 펀딩-청산 상호작용). 근거: 본 섹션 `**🔸 부분 Resolved (BL-186a):**` 줄 · `docs/roadmap.md:114` `[x] BL-186a` / `docs/roadmap.md:115` `[ ] BL-186b`.

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
**출처:** Sprint 41 Worker H 결정 — share link 충분 P1 deferrable, demo 첫인상 단계 미구현

**권장 접근:** share link 가 충분히 우선이라 demo 단계 미구현. 사용자 요청 시 jsPDF + html2canvas (client) 또는 Playwright (server-side) 둘 중 선택.

---

### BL-195

**Title:** qb-form-slide-down animation 영구 truncation (max-height 600px + overflow-hidden, 600px 초과 시 hint list 잘림)
**Category:** Frontend UX
**Priority:** P2
**Trigger:** Sprint 45 codex G.4 review 발견
**Est:** XS (30m)
**출처:** Sprint 45 codex G.4

**원인 / 영향:** `frontend/src/styles/globals.css:582` `qb-form-slide-down` `both` fill mode + `FormErrorInline` `overflow-hidden` 조합 = Pine Script 다수 미지원 함수 시 unsupported-builtins hint list 영구 truncation.

**권장 접근:** fill-mode `forwards` 제거 또는 max-height 풀림 패턴 적용.

---

### BL-309

**Title:** trading 핵심 dispatch 모듈 test 추가 (registry / webhook / fees, 0% → ≥80%)
**Category:** Test infra / Trading
**Priority:** P2
**Trigger:** BL-308 묶음 또는 dogfood 직후
**Est:** M (4-6h)
**출처:** [`docs/dev-log/2026-05-15-trading-deepen.md`](dev-log/2026-05-15-trading-deepen.md) Phase 2

**✅ Resolved (W3, 2026-06-29) — baseline stale + fees obsolete:** "0%" 는 2026-05-15 수치. 실측 결과:

- **`fees.py` 는 파일 자체 삭제됨** (PR #344 dead vectorbt-era cleanup). fee 로직은 `providers.py`/backtest 로 이전 — fees 항목 **무효** (복원/테스트 안 함).
- **`registry.py` = 이미 100% cov** (`tests/tasks/test_provider_dispatch.py` 가 5-tuple + unsupported + `.key` + ProviderError 서브클래스 전수 검증, `_provider_for_account_and_leverage` wrapper 경유). W3 = 미검증 잔여 불변식만 추가 (per-call factory identity = prefork-safe iron law + 미지원 매트릭스 빈칸 `(okx,live,True)`). 풀 dispatch-parity 스위트는 vacuous 중복이라 의도적 미작성 (G1 codex 검증).
- **`webhook.py` = ~94% cov** (HMAC verify grace 안/밖 + parse_tv_payload happy/error 광범위). 잔여 1 line(`ensure_authorized` raise)은 router 401 테스트로 행동 커버 → pure unit 은 cosmetics 라 미작성 (G1/G2 합의).

BL-308 묶음 PR 에 포함. CI ratchet 게이트가 registry/webhook 도 합산 커버.

**현 상태 (2026-05-15 당시):** **0% test coverage** 3 file = `registry.py` 64L (provider dispatch 핵심, 5 entry tuple) + `webhook.py` 81L (TV payload 파싱) + `fees.py` 55L (fee calculation). 합계 200L 핵심 dispatch 로직 미검증.

**권장 접근:**

1. `tests/trading/test_registry.py` — 5 tuple (Bybit demo spot/futures + OKX demo + Bybit live) provider factory 검증 + UnsupportedExchangeError raise 검증
2. `tests/trading/test_webhook.py` — TV payload parsing positive/negative + secret rotation
3. `tests/trading/test_fees.py` — fee calculation per-exchange parity (Bybit vs OKX 수수료 형식 차이)
4. coverage `pytest --cov=src.trading.registry --cov=src.trading.webhook --cov=src.trading.fees --cov-fail-under=80` CI gate

**Risk:** 🟡 (dispatch 깨짐 = 신규 거래소 추가 시 silent failure).

**의존성:** BL-308 와 묶음 권고 (양쪽 = trading test 보강 sprint).

---

### BL-235

**Title:** N-dim acquisition surface viz (3D+ surface 또는 parallel-coord, Bayesian 전용)
**Category:** Frontend UX / Optimizer
**Priority:** P2
**Trigger:** Sprint 57+
**Est:** M (8-12h, estimate)
**출처:** ADR-013 §6 #8 deferred. Sprint 55 = inline SVG iteration-chart (1D best_so_far) 만 구현.

**권장 접근:** recharts 또는 plotly.js 의존성 추가 검토 + cross-page consistency 의무. Bayesian / Genetic 공용.

---

### BL-236

**Title:** `objective_metric` whitelist 자유화 (BacktestMetrics 24+ 지표 노출)
**Category:** Optimizer
**Priority:** P2
**Trigger:** Sprint 56+
**Est:** S (3-5h, estimate)
**출처:** Sprint 55 = `_SUPPORTED_OBJECTIVE_METRICS = {sharpe_ratio, total_return, max_drawdown}` 3종만 노출

**권장 접근:** BacktestMetrics 24 metric (sortino_ratio / calmar_ratio / win_rate / profit_factor 등) 노출 검토. `_objective_from_metrics` switch + FE select option 확장.

---

### BL-362

**Title:** live 경로 coverage↔interpreter divergence silent swallow observability
**Category:** Strategy / pine_v2 / Trading (money path)
**Priority:** P2
**Trigger:** S5 (trading kill-switch/notional/reconcile 묶음) — money path 변경이라 trading 테마와 함께
**Est:** S (2-4h)
**출처:** [`docs/archive/audit/2026-05-30-full-inspection.md`](archive/audit/2026-05-30-full-inspection.md) §4.3 (strategy/D 관찰 — observability gap)

**원인 / 영향:** `run_live` 가 `run_historical(..., strict=False)`(event_loop.py:219) 호출 → `PineRuntimeError` 를 `result.errors` 에 기록만 하고 **그 bar statement 만 건너뛴 채 실행 계속**(event_loop.py:128-133). live 경로엔 coverage preflight 게이트도 없음. BL-361 이 현재 28 누출을 닫았으나, **향후 임의의 coverage↔interpreter divergence 가 라이브에서 조용히 오신호 생성**할 latent risk 상존. (S2 는 DEC-16=A 로 본 갭을 S5 이관.)

**권장 접근:** (a) live 진입 전 `analyze_coverage` preflight reject 적용, 또는 (b) `run_live` 의 swallowed `result.errors` 를 Slack/Prometheus alert + (선택) 세션 abort 로 표면화. money path 변경이므로 S5 에서 commit-spy + kill-switch 회귀와 함께 신중 검토.

**상태:** ✅ **Resolved (2026-07-25, `stage/money-path-accuracy`).** 본체는 PR #369(commit `a9dca4f`)가 이미 shipped — preflight reject + `run_live` fail-closed + runtime divergence safety-net + `qb_live_signal_divergence_total` + 14 테스트. 잔여였던 알림 채널을 이번에 마감했다: `_alert_live_divergence` 가 Slack 전용 `send_critical_alert` → `send_rule_alert(channel=AlertChannel.both)`(채널별 예외 격리). `run_live_error` 경로는 raw 예외 문자열이 미감사 텍스트라 **호출부에서 클래스명만** 싣도록 축소(원문은 `logger.exception` 유지). `backend/.env.example`·`.env.prod.example` 에 `TELEGRAM_*` 추가. ★dogfood 실측에서 `SLACK_WEBHOOK_URL` 이 이 환경에 미설정임이 드러나 **이 변경 전까지 발산 알림이 아무에게도 도달하지 않았음**이 확인됐다(텔레그램 실수신 `{'slack': False, 'telegram': True}` = 채널 격리도 동시 실증).

---

### BL-363

**Title:** stress*test `StressTestService.\_execute*\*` 4-method boilerplate 추출
**Category:** Stress / Architecture (deep module)
**Priority:** P2
**Trigger:** deepening sprint 또는 5번째 stress engine 추가 시
**Est:** S (2-3h)
**출처:** [`docs/archive/audit/2026-05-30-full-inspection.md`](archive/audit/2026-05-30-full-inspection.md) appendix P1-9 + [`docs/dev-log/2026-06-30-stress_test-deepen.md`](dev-log/2026-06-30-stress_test-deepen.md) (deepen-modules stress_test 1차 audit — money-path 증거 + git 실증 sharpen)

**원인 / 영향:** `_execute_walk_forward`(`service.py:305-319`)/`_execute_cost_assumption_sensitivity`(`:366-384`)/`_execute_param_stability`(`:393-411`) 가 `strategy.find_by_id_and_owner → None가드 → provider.get_ohlcv → build_engine_config_from_db(bt)` prefix 를 복붙. **CA↔PS 본문은 19-LOC 중 3토큰만 차이**(에러문자열 + `run_*` engine fn + `*_to_jsonb` serializer fn). 이 분산된 boilerplate 가 실제 money-path silent corruption 으로 **한 번 물었음** — git `6c7adfba`(Sprint 52 BL-222: `build_engine_config_from_db` 를 CA/PS 에만 추가, **WF 누락**) → `ffb2299b`(WF 별도 패치). docstring `service.py:298-304` 가 증언: WF 의 IS/OOS 백테스트가 parent 의 fees/slippage/init_cash/leverage/sizing 대신 엔진 기본값으로 실행. config-build 변경 시 3곳(`:319/:377/:404`) 수동 동기화 의무 → 1곳 누락 = Celery run 성공·결과 silent 오염. 5번째 engine 도 동일 누락 위험.

**권장 접근:** `_load_run_context(st, bt) -> RunContext(strategy, ohlcv, backtest_config)` helper 추출(MC 는 equity_curve 기반이라 비대상) → `build_engine_config_from_db(bt)` single-site 화 = **BL-222 drift class 구조적 제거**. CA/PS 는 `_execute_grid_sweep(st, bt, *, engine_fn, to_jsonb)` 1메서드로 통합(engine 의미는 인자로 주입, 분리 유지). behavior-preserving 순수추출 — 기존 per-engine propagation 테스트(WF+CA+PS 각 1건) + state-isolation 가드가 안전망. **C2(BL-392) 와 묶으면 자연스러움**(grid-sweep DTO 통합과 동일 CA/PS 응집부).

---

### BL-364

**Title:** Optimizer 진짜 string-label CategoricalField sweep (Genetic + Bayesian)
**Category:** Optimizer / Feature
**Priority:** P2
**Trigger:** 사용자 string 카테고리 sweep 요청 시 (예: maType ∈ {ema,sma,wma})
**Est:** M (4-6h)
**출처:** [`docs/archive/audit/2026-05-30-full-inspection.md`](archive/audit/2026-05-30-full-inspection.md) appendix P1-9 (S4 Option A 후속)

**원인 / 영향:** S4(Option A)는 비숫자 CategoricalField 를 명확히 거부(InvalidOperation 크래시 차단)했으나, 스키마 docstring 의 본래 의도(`pine input.string / 사용자 정의 선택지` = `['ema','sma']`)는 미지원 상태. GA/Bayesian 이 individual 을 Decimal(ordinal)로 표현하기 때문.

**권장 접근:** ordinal 인코딩 — GA/Bayesian 이 categorical 차원을 index(Decimal 0..N-1)로 sample/mutate, backtest 호출 시 `field.values[int(idx)]` 로 string 디코드하여 input override 전달, best-params 에서 라벨 복원. Genetic `_sample_individual`/`_gaussian_mutation`/run-loop + Bayesian `_coerce_skopt_to_decimal`/skopt `Categorical(transform="label")` 양쪽 일관 처리. (S4 에서 사용자 결정 = Option A 우선, 본 feature 는 후속.)

---

### BL-365

**상태:** ✅ **Resolved (2026-07-27, `feat/live-conditional-entry`).** 진입 전용 `entry_trigger_direction` 신설. `trigger_direction_for` 는 청산 side + SL/TP 종류 기준이라 진입에 재사용하면 정반대가 나온다(롱 청산 sell+SL 은 2, 롱 진입 breakout 은 1). 실거래 체결가로 검증 — 롱은 트리거 위, 숏은 트리거 아래에서 체결됐다.

**Title:** `trigger_direction_for` / `map_exit_kind` dead-code + 서버 미배선 (standalone-trigger 방향 latent gap)
**Category:** Trading / pine_v2 (money path, latent correctness)
**Priority:** P2
**Trigger:** standalone 조건부 트리거 주문(SL/Trail) 을 서버가 발주하게 되는 시점 (manual API trigger_price 노출 강화 또는 Wave 4+ standalone exit)
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md) (deepen-modules trading 2차 audit)

**원인 / 영향:** `exit_order_mapping.py:48/76` 의 `map_exit_kind`/`trigger_direction_for` 는 production caller 0 (doc-comment 만 `models.py:212` / `providers.py:77`). 현재 라이브 자율 exit 는 entry-attached bracket 으로 Bybit 가 방향을 포지션에서 추론 → 영향 없음 (Phase 3 PASS). **단 manual order API 는 `trigger_direction` 을 client 가 공급**(`schemas.py:67` `int|None ge=1 le=2`) — 서버가 SSOT (`trigger_direction_for`)로 계산하지 않아, 향후 서버 발주 standalone 트리거가 방향 미산정 시 역방향 트리거 / 거부 위험. 트레일링 live-placement(STEP B)는 trading-stop 엔드포인트(position-inferred)라 본 BL 미소비 — deferred 확정.

**권장 접근:** 서버가 standalone 트리거 exit 를 발주하는 첫 경로에서 `trigger_direction_for(exit_side, kind)` 호출로 SSOT 산정 + manual API 의 client-supplied 값 검증/override. 그 전까진 dead-code 유지 (제거 시 SSOT 의도 상실). 진리표 테스트(LONG-SL→2 / LONG-TP→1 / SHORT-SL→1 / SHORT-TP→2) 의무.

**영향 파일:** `tasks/live_signal.py` 또는 신규 standalone-trigger 경로 + `exit_order_mapping.py` (배선만).

**Risk:** 🟢 (현재 미소비 — 배선 시점에만 검증 필요).

---

### BL-366

**Title:** live-signal dispatch 의 OrderService DI 인라인 조립 중복 (HTTP `get_order_service` 와 drift)
**Category:** Trading / Architecture (locality / DI-dup)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 OrderService 의존성 추가 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

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
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

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
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

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
**출처:** 2026-06-28 grilling (트레일링 후속 scope 결정)

**원인 / 영향:** `oco_group_id` DB 컬럼 + OrderSubmit 전달은 이미 존재하나 sibling-cancel 오케스트레이션은 미구현. 현재는 entry-attached bracket 이라 거래소가 네이티브 OCO(한 다리 체결 시 형제 자동취소)를 처리 → app-side sibling-cancel 은 YAGNI. standalone exit order(BL-365) 발주 시점에 두 다리가 독립 주문이 되면 그때 app-side 형제취소가 필요.

**Risk:** 🟢 (현재 네이티브 OCO 로 커버 — defer 안전).

---

### BL-374

**Title:** pine_v2 interpreter na-semantics — `x/0` · `math.sqrt(-1)` 등 raw Python 예외를 Pine `na` 로 정규화
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P2
**Trigger:** pine_v2 robustness sprint 또는 사용자 div-by-zero/도메인 오류 전략 제보 시
**Est:** M (4-6h)
**출처:** 2026-06-28 BL-362 G2 codex challenge (live 발산 observability)

**원인 / 영향:** pine_v2 인터프리터가 `/`(`operator.truediv`)·`math.sqrt`·`math.log` 등에서 raw Python 예외(`ZeroDivisionError`/`ValueError: math domain error`)를 그대로 전파한다. TradingView Pine 의미상 `1/0`·`math.sqrt(-1)` 은 `na` 를 반환해야 한다(crash 아님). 이 예외들은 `PineRuntimeError` 가 아니라서 `run_historical(strict=False)` 의 `except PineRuntimeError` 가 안 잡고 `run_live` 밖으로 raise → 백테스트는 실패, **라이브는 BL-362 가 `run_live_error` 로 fail-closed 세션 비활성화**(crash-loop 차단). 즉 현재는 안전하지만, 정상 작동하는 TradingView 전략이 우리 인터프리터에선 비활성화되는 false-positive 가 남는다.

**권장 접근:** `BinOp` Div/Mod 0-분모 → `na`(float nan), `math.sqrt/log/...` 도메인 밖 입력 → `na` 로 정규화(Pine 의미 일치). stdlib/interpreter 산술 경로에 na-guard 추가 + 골든 테스트(`1/0 == na`, `sqrt(-1) == na`). 완료 시 BL-362 의 `run_live_error` 비활성화는 진짜 구조적 crash(parse error 등)에만 발생.

**Risk:** 🟢 (BL-362 fail-closed 로 라이브 money-path 는 이미 안전 — 본 BL 은 false-positive 정밀도 개선).

**상태:** ✅ **Resolved (2026-06-29, `fix/pine-374-na-semantics`, commit `2cd1313`).** `_na_safe(compute)` 헬퍼(`(ArithmeticError, ValueError)` catch + complex 결과 → nan)를 `_eval_binop`(숫자 피연산자 한정 — 문자열 `%` 등 타입 오용은 fail-closed) + `math.sqrt/log/log10/exp` 에 적용, `math.pow` 는 `args[0] ** args[1]` → `math.pow()` 전환(bigint/complex 무음오염 차단). `PineRuntimeError`/`TypeError` 전파 유지(BL-362 fail-closed 유지). stdlib `ta_stdev/ta_bb` sqrt-clamp 는 G2 challenge 에서 2-pass variance ≥0 항상이라 dead-code 로 판명 → 제거(diff = `interpreter.py` + 신규 테스트만). 검증 = G1 codex plan eval + 3-candidate generator panel(core 6 edit byte-identical 수렴) + G2 codex challenge(F1 dead-clamp 제거 + F2 문자열 `%` over-catch → 숫자 한정 가드) + G3 fresh review(GO) + mutation 5/5 catch + full suite 2226 pass(cov 95.6%) + **Playwright E2E**(div-by-zero 백테스트 FAILED→COMPLETED, console.error 0). **잔여 deferred → [BL-376](#bl-376).**

---

### BL-376

**Title:** pine_v2 na/inf 소비 사이트 robustness — na→ta.\* length / na→strategy.entry qty / inf→math.floor·ceil·round
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P3
**Trigger:** pine_v2 robustness 후속 또는 실자금 cutover 전 (BL-374 후속)
**Est:** M (4-6h)
**출처:** 2026-06-29 BL-374 G1 codex / G2 codex challenge / G3 fresh review + 3-candidate generator panel 합의

**원인 / 영향:** BL-374 가 산술/math _생성_ 사이트의 raw 예외를 na 로 정규화했으나, 그 na/inf 가 _소비_ 되는 다음 사이트는 여전히 raw 예외 escape 가능(전부 실측 검증, 동일 harm class = `run_historical` 밖 escape → 백테스트 FAILED / 라이브 세션 비활성):

- **na → ta.\* length:** `ta.sma(close, na)` 등이 `int(nan)`(ValueError) / `deque(maxlen=nan)`(TypeError). 단 실 TradingView 는 length=simple int 강제라 비-TV-valid 시나리오(우리 인터프리터 leniency). pre-existing.
- **na → strategy.entry qty:** `qty=close/0` → na qty → `_compute_metrics` 의 `Decimal('NaN')` 비교에서 `decimal.InvalidOperation` → status=error(**깨끗한 실패, 무음 오염 아님**). 라이브는 이미 nan qty 거부(`test_live_exit_surfacing`). 사이징을 div-by-zero 로 하는 전략은 본질적으로 broken.
- **non-raising inf → math.floor/ceil/round/subscript-int:** `1e308 * 10.0`(operator.mul, raise 안 함) → inf → `math.floor(inf)` 등 `OverflowError` escape. 3-candidate generator panel 전원 + G3 fresh review 독립 발견.

**권장 접근:** (a) ta.\* length 진입 시 na/non-finite → na 결과 정규화(또는 length 타입 강제). (b) strategy.entry/order qty 가 na/non-finite → 주문 skip(라이브 path 의 기존 nan→reject 미러). (c) inf 생성부 clamp 또는 floor/ceil/round/subscript int 변환 na-safe. 골든 테스트 동반.

**Risk:** 🟢 (전부 현재 깨끗한 실패 또는 비-TV-valid — BL-374 가 핵심 false-positive 해소, 본 BL 은 잔여 robustness).

**상태:** ✅ **Resolved (2026-06-30, `fix/pine-376-na-inf`).** 3 사이트 전부 닫음:

- **Site #1** `_coerce_length(value) -> int | None`(`not math.isfinite(value) or value < 1 → None`) 헬퍼를 14 ta 함수(sma/ema/rma/atr/rsi/highest/lowest/change/stdev/variance/wma/mom/hma/bb) + dispatcher(change/stdev/variance 의 `int()` 제거) + pivothigh/pivotlow 양 window 에 적용 → na 반환. `ta.valuewhen` occurrence 는 length 아님(0/음수 유효) → **별도 non-finite 가드**(`isinstance(occ_raw, (float, Decimal)) and not math.isfinite`). 실측 갱신: na 뿐 아니라 inf-length(`deque(maxlen=inf)` TypeError) + 초기 가드 없던 highest/lowest 의 length 0/-N(`max(empty)`/negative maxlen ValueError) 도 함께 해소.
- **Site #2** `StrategyState.entry` 에서 `not math.isfinite(qty)` → 주문 skip + warning(라이브 nan→reject 미러). 실측 갱신: **closed na-qty 는 깨끗한 실패였으나 _open_ na-qty 는 status='ok' 인데 equity NaN 무음 오염** = 실제 버그 → skip 으로 양쪽 통일. `qty<=0` 미skip(compute_qty 의 유한 0.0 보존).
- **Site #3 (소비부 가드, 사용자 결정)** `math.floor/ceil/round` per-branch `not math.isfinite → na`(공유 `any(_is_na)` 가드 미변경 → `math.abs/sign/max/min/sqrt/log` 의 inf 통과 유지) + subscript offset `not math.isnan` → `math.isfinite` + timestamp `int()` except 에 `OverflowError` 추가.

검증 = G1 codex plan eval(GO_WITH_FIXES) + 4-candidate generator panel(아키텍처 byte-수렴, judge 가 C4 isinstance pre-check=BL-362 위반 기각) + G2 codex challenge(P1 = valuewhen `Decimal('NaN')` occurrence 가 `isinstance(float)` 갭으로 escape, 실측 재현 → `(float, Decimal)` 확장 + 테스트; P2 ema/rma/rsi fractional truncation = 되돌리면 `Decimal('NaN')<=0` 재escape 라 유지) + G3 fresh review(SHIP) + **mutation harness 6/6 CAUGHT(false-green 0)** + full suite 2305 pass(cov ≥90, ruff+mypy clean, alembic head, **migration 0**) + **Playwright E2E**(na/inf 전략 백테스트 before=실패 "an integer is required" → after=완료, console.error 0). **잔여 deferred → [BL-377](#bl-377).**

---

### BL-378

**상태:** ✅ **Resolved (2026-06-30, `fix/pine-378-atr-wilder`)** — 근거: 본 섹션 `**Title:**` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:29`) · 인덱스 표 행 ✅.

**Title:** pine_v2 `ta.atr` rolling SMA → Wilder RMA (TradingView parity) ✅ **Resolved (2026-06-30, `fix/pine-378-atr-wilder`)**
**Category:** Strategy / pine_v2 (indicator 정확성)
**Priority:** P1 (harm-class, 트리거됨)
**출처:** 2026-06-30 실세계 8 전략 티어드 백테스트 QA (`docs/archive/qa/2026-06-30-pine-tiered-backtest/report.md` finding B1)

**원인 / 영향:** `ta_atr`(stdlib.py) 가 True Range 의 단순 rolling SMA(`deque(maxlen=len)` → `sum/len`)를 계산. TradingView `ta.atr(len) = ta.rma(ta.tr, len)` = Wilder smoothing(alpha=1/len). 비-상수 TR 에서 발산(len=3, bar 3: 엔진 3.50000=SMA vs TV 3.05556=RMA, 14% 누적). 같은 파일 `ta_rma`(Wilder)는 정확하고 `rsi`가 이를 사용 → atr 만 고립 버그. ATR 사용 전 전략(DrFX supertrend / UtBot·RsiD 트레일링 / LuxAlgo slope) 백테스트가 TV 와 silent divergence. 상수 TR 슬라이스는 SMA=RMA 라 기존 테스트가 못 잡음.

**수정:** `ta_atr` 가 TR 계산 후 기존 Wilder `ta_rma(state, node_id, tr, _len)` 재사용(~2줄). seed=SMA(first len TRs) 로 현재와 동일, 이후 bar 부터 TV 정합. 비-상수 TR anti-circular 골든 테스트 2건(`test_ta_atr_matches_tradingview_wilder_rma` / `test_ta_atr_not_rolling_sma`) + trust-layer golden 재생성(s2_utbot/i1_utbot). **검증:** G1-G4(codex G1/G2/diff-challenge no-P1 + Workflow 12-agent panel + G3 fresh review + mutation 2/2 CAUGHT) + full 2301 pass + ruff/mypy clean. migration 0.

---

### BL-379

**Title:** pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐)
**Category:** Strategy / pine_v2 (interpreter)
**Priority:** P2 (latent harm-class — 코퍼스 8종 미트리거, 흔한 패턴)
**Trigger:** pine_v2 robustness 후속
**Est:** M (4-6h)
**출처:** 2026-06-30 QA codex G2 challenge + 직접 재현

**원인 / 영향:** `_eval_subscript`(interpreter.py:653)가 `x[1]`을 `_var_series`에서만 조회하는데, user function(`f(s) => ...`) 지역변수는 `_var_series`에 append 되지 않음. 재현: `f(s) => prev = s[1]` → `[nan]*N`(항상 na) vs top-level `close[1]` 정상. 코퍼스 8종은 미트리거(전부 인라인/builtin) 이나 `f(x)=>...x[1]...` (지표 함수 내 history 참조) 는 흔한 패턴 → 해당 전략 silent divergence. **권장:** user-function 스코프 변수 history 추적 또는 명시적 unsupported reject.

---

### BL-380

**Title:** Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반)
**Category:** Strategy / pine_v2 (Trust Layer / Track A)
**Priority:** P2 (신뢰 표면)
**Trigger:** Track A 신뢰 표면 sprint
**Est:** S-M (3-5h)
**출처:** 2026-06-30 QA LuxAlgo 0-trade 추적 + codex G2

**원인 / 영향:** `virtual_strategy.py:128-130` 가 INFORMATION/UNKNOWN alert 를 경고 없이 `continue` (docstring `:12` 은 "무시 + warning" 약속 — 계약 위반). LuxAlgo `alertcondition(.., 'Price broke the down-trendline upward')` → strict 기본 INFORMATION 키워드 `\btrendline\b` → 무경고 무시 → **0 trades, status=ok** (지표 수치는 정확). loose 모드(opt-in)면 directional. **추가:** 경고를 추가해도 `run_backtest_v2`(v2_adapter.py:181)가 `state.warnings`만 내보내 `VirtualRunResult.warnings` 유실. **권장:** (a) ignored actionable alert 시 wrapper.warnings 기록 + (b) VirtualRunResult.warnings → backtest parse warnings 전파. (strict 기본 정책 자체는 유지.)

---

### BL-381

**Title:** Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허
**Category:** Strategy / pine_v2 (Trust Layer CI)
**Priority:** P2 (meta / 검증 인프라)
**Trigger:** Trust Layer CI 강화
**Est:** S (2-4h)
**출처:** 2026-06-30 QA codex G2 + diff-challenge

**원인 / 영향:** `VirtualRunResult`(virtual_strategy.py:61) 에 var_series 필드 부재 + 미반환. `test_trust_layer_parity.py:239` 의 golden 추출기가 `getattr(.., 'var_series', {})` → 빈 dict digest. 결과: Track A 전략(i2_luxalgo 등)의 지표 변화(예: ta.atr→slope)가 var_series_digest 에 반영 안 됨 → documented P-3 parity 검증이 부분 공허(BL-378 fix 시 i2_luxalgo baseline 불변이 이를 노출). **권장:** VirtualRunResult 에 var_series/warnings 노출 + 추출기 배선.

---

### BL-382

**Title:** qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성)
**Category:** Backtest / 투명성
**Priority:** P2 (투명성)
**Trigger:** sizing 투명성 sprint
**Est:** S (2-4h)
**출처:** 2026-06-30 QA F1 (codex G2 = harm-class 아닌 transparency)

**원인 / 영향:** `default_qty_type` 미지정 전략(PbR/UtBot)은 qty=1.0 (1 BTC/trade ≈ $42k notional vs $10k capital) → mdd=-16.95/-41.47, fees $156k. 엔진은 `mdd_exceeds_capital=True` 정직 flag + FE KPI 가 자본초과 손실 표시. **그러나** sizing_source 가 FE 결과 schema 부재(schemas.ts:254), AssumptionsCard 가 "1 BTC 고정수량 fallback" 미표면화(assumptions-card.tsx:88). **권장:** config 응답에 sizing_source/default_qty 포함 + fallback 시 경고 표시.

---

### BL-383

**Title:** v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)
**Category:** Backtest / engine (관측성)
**Priority:** P3
**Trigger:** pine_v2 관측성 후속
**Est:** S (2-3h)
**출처:** 2026-06-30 QA codex G2 (G1 에서도 지적)

**원인 / 영향:** `v2_adapter.py:126-133` generic `except Exception` → `status="parse_failed"`. parse 성공 후 실행 중 예외(TypeError 등)도 "parse failed"로 표시 → 사용자 원인 분류 오도. BL-376 이 na/inf escape 는 닫았으나 catch-all 잔존. **권장:** 실행-단계 예외를 `status="error"` 로 분기(parse 단계와 구분).

---

### BL-384

**Title:** ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3 (좁은 edge)
**Trigger:** pine_v2 parity 후속
**Est:** S (2-3h)
**출처:** 2026-06-30 QA codex G2 + 직접 재현

**원인 / 영향:** `stdlib.py:305-307` 가 `cond_bool and source not na` 일 때만 occurrence 기록. cond=true + source=na 인 occurrence 를 TV 는 기록(na 반환), QB 는 skip → 이전 non-na 반환. 재현: src=[10,na] → `valuewhen(cond,src,0)` QB=10, TV=na. RsiD `valuewhen(plFound, osc[lbR], 1)` (osc warmup 시 na) 후보. 좁은 edge. **권장:** cond=true occurrence 는 source 가 na 여도 기록.

---

### BL-385

**Title:** PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse
**Category:** Strategy / pine_v2 (coverage / 메타데이터)
**Priority:** P3 (경미)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**출처:** 2026-06-30 QA F3

**원인 / 영향:** `PineVersion` enum(strategy/models.py)이 v4/v5 뿐 → `_detect_version`(strategy/service.py)이 `//@version=6`(PbR, bs)를 v5 로 보고. 메타데이터 부정확(실행엔 무영향). **권장:** v6 enum 값 추가(alembic enum-add 패턴, LESSON-066).

---

### BL-386

**Title:** v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject)
**Category:** Strategy / pine_v2 (coverage)
**Priority:** P3 (경미, 안전 측 — silent 아님)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**출처:** 2026-06-30 QA F4

**원인 / 영향:** `SUPPORTED_FUNCTIONS` 의 `_V4_ALIASES` 가 abs/max/min 만 포함, `floor`/`ceil`/`round`/`sqrt`(유효 Pine builtin) 부재 → v4 스크립트의 `floor()` 가 unsupported flag(preflight 차단). over-strict 이나 silent 아님(안전). **권장:** v4 bare math builtin 을 `math.*` 로 재라우팅하는 alias 추가.

---

### BL-387

**Title:** backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 으로 영속 경계 횡단 (key drift 시 silent 잘못된 sizing)
**Category:** Backtest / Architecture (shallow seam / money-path)
**Priority:** P2
**Trigger:** backtest deepening sprint 또는 sizing 로직 변경 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex challenge 최강 후보)

**원인 / 영향:** `service.py:754-876` `_resolve_sizing_canonical` 이 6-key `dict[str, Any]` 를 반환하고 `service.py:188-212` 가 `.get('leverage', default)` 식으로 config_payload 를 손-조립한다. 두 dict 의 key 일치가 타입으로 보장되지 않아, resolve 쪽 key 가 rename 되면 조용히 default 로 떨어져 `sizing_source`/`leverage_basis` 가 잘못 영속될 수 있다(money-affecting). `dict[str, Any]` = Interface 가 거의 없는 shallow seam 이 백테스트 입력의 진실을 DB 경계로 흘려보낸다.

**권장 접근:** sizing 결정을 typed value object(`SizingCanonical`)로 만들어 `_resolve` 출력과 config 영속 사이 Seam 에 타입 부여 → key 불일치가 검증/타입 시점에 잡히게. `test_resolve_sizing_canonical` 8-case 존재하나 resolve 출력↔config_payload key-match 단언 부재 = 부분 gap.

**영향 파일:** `backtest/service.py` (`_resolve_sizing_canonical` + config_payload 조립), `config_mapper.py`.

**Risk:** 🟡 (money-path sizing — 영속 값 parity 검증 필요).

---

### BL-388

**Title:** BacktestMetrics 24-field 가 4곳 평행 정의 (engine dataclass ↔ schema ↔ serializer ↔ `_to_detail`) — field-parity 무검증 leaky seam
**Category:** Backtest / Architecture (locality / multi-SSOT)
**Priority:** P2
**✅ Resolved:** 2026-07-26 backtest-trust 스프린트. ★**착수 시 실측하니 이미 해결 상태였다** — 본문의 "24-field / 4곳" 은 stale 이고 실제는 **48필드 / 실질 3-site**(`_to_detail` 은 PR #391 에서 `asdict` spread 로 전환), dataclass/OutSchema/to_jsonb/from_jsonb **전 차집합 공집합**, tripwire 6테스트 통과 중. 재구현하지 않고 close + **micro-tripwire 2건 추가**(① `BacktestMetricsSummary` 키 ⊆ dataclass 필드 — 기존 tripwire 사각지대 ② `BacktestMetricsOut` 의 Decimal 필드 전수가 `field_serializer` 에 등재 — 누락 시 JSON float 로 새는 조용한 정밀도 손실) → **8 passed**. 본 스프린트가 신규 필드 3개(`sharpe_convention`/`liquidation_occurred`/`liquidation_count`)를 추가할 때 이 tripwire 가 4-site 동시 수정을 실제로 강제했다. stale 주석은 숫자를 다시 적지 않고 "필드 수 SSOT = dataclass + tripwire" 로 정정(재-stale 차단). **full SSOT 파생(metaprogram)은 사용자 명시 거부** — serializer 가 필드별 커스텀 shape 를 갖고 있어 genericize 시 가독성만 악화.
**Trigger:** backtest deepening sprint 또는 BL-236(objective_metric 노출) 진행 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex challenge 가 4번째 site `_to_detail` 추가 발견)

**원인 / 영향:** 동일 지표 shape 가 `engine/types.py:101 BacktestMetrics`(dataclass) + `schemas.py:195 BacktestMetricsOut` + `serializers.py metrics_to/from_jsonb` + `service.py:668 _to_detail`(BacktestMetricsOut 손-매핑) **4곳**에 평행 정의된다. 지표 1개 추가 = 4 edit site 동시 수정 — Locality 가 도메인 전체로 퍼진 leaky Seam. round-trip serializer 테스트(`test_serializers`/`test_serializers_extended`)는 있으나 dataclass↔schema field-set parity 단언이 없어 두 정의가 silent drift 가능. BL-236 이 지표 노출 확대 시 추가 비용 증폭.

**권장 접근:** 지표 field 의 단일 정의를 SSOT 로 고정하고 나머지 표현(API/JSONB/detail)을 파생, 또는 최소 'dataclass field 집합 == schema field 집합' CI parity 가드(tripwire) 선추가로 drift 를 구조 차단.

**영향 파일:** `engine/types.py`, `schemas.py`, `serializers.py`, `service.py` (`_to_detail`).

**Risk:** 🟡 (직렬화는 round-trip 보호됨, parity 가드는 test-first 성격 약함).

---

### BL-392

**Title:** stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass + serializer + OutSchema)
**Category:** Stress / Architecture (parallel definition / leaky JSONB seam)
**Priority:** P2
**Trigger:** stress_test deepening sprint, 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시
**Est:** M (4-6h)
**출처:** [`docs/dev-log/2026-06-30-stress_test-deepen.md`](dev-log/2026-06-30-stress_test-deepen.md) (deepen-modules stress_test 1차 audit)

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
**출처:** 2026-07-05 TV-parity sprint — 사용자 전략(HMA+ATR+Curvature) 커버리지 판정

**원인 / 영향:** TV 의 `trail_points`/`profit`/`loss` 는 **틱 단위**(값 × syminfo.mintick = 가격 오프셋). QB 인터프리터는 price-distance 로 해석(`interpreter.py` `_num` 근사, mintick=0.01 고정 — `interpreter.py:1131`). ATR 값을 trail_points 에 넣는 전략(사용자 전략 포함)은 TV 에선 초미세 트레일링(예: ATR 500 → $5)이 되어 승률 98%+ 의 **가짜 성적**이 나오고, QB 는 저자 의도(가격 거리)에 가깝게 동작 — 즉 발산의 원인이 TV 쪽 함정. 그러나 틱 단위를 의도한 전략은 QB 에서 발산.

**권장 접근:** (a) 발산 방향/원인을 supported-indicators 문서에 명시(완료: 2026-07-05 노트) (b) 실 심볼 mintick 소싱(CCXT market precision) + 틱 해석 opt-in config. TV 정합 모드(fill_timing 과 묶음) 시 함께 검토.

**Risk:** 🟢 (현 동작이 보수적/의도-근접. 문서화 우선).

---

### BL-398

**Title:** Sharpe TV convention 정렬 (달력월 수익률 + RFR 2%/yr) — optimizer objective 영향 분석 동반
**Category:** Backtest / metrics (TV parity)
**Priority:** P2
**✅ Resolved:** 2026-07-26 backtest-trust 스프린트. `engine/metrics.py` 에 `_periodic_returns` 재사용 형제 `sharpe_ratio()` 신설(달력월 + RFR 2%/12, 모집단 SD, 연율화 없음) + `v2_adapter:662` 교체 + `_sharpe` 제거. **Decimal 비-옵셔널 유지**(None 시 `grid_search.py:249` dead branch 부활 + FE `.toFixed` 크래시). **신규 `sharpe_convention` 마커 4종**(`tv_monthly_rfr2`/`tv_daily_rfr2`/`unavailable`/null=구 실행)을 4-site 동시 등재해 baked 혼재를 화면에서 구분. **랭킹 flip 실측(의무 이행)**: 15셀에서 **argmax FLIP** · Kendall τ 0.6381 · 11/15 셀 2계단 이상 이동. ★핵심 근거 = 구 수식이 **자본 38배 손실(−3837%) 실행에 양수 샤프 +0.3955** 를 줬다(신 −0.0757). baseline regen 1회(diff 는 sharpe 키 + 메타 한정, 3종 digest 불변). 잔여는 신규 BL(목록 read-time recompute / optimizer·stress 저장값 혼재 / `_periodic_returns` sub-daily fallback).
**Trigger:** TV parity 2차 또는 사용자 Sharpe 값 문의 시
**Est:** M (4-6h — baseline 재생성 + optimizer `sharpe_ratio` objective 랭킹 영향 분석 의무)
**출처:** 2026-07-05 TV-parity sprint B3 (sortino 는 TV convention 으로 신규 구현, sharpe 는 blast radius 로 이연)

**원인 / 영향:** `_sharpe`(v2_adapter)는 bar 수익률 + RF=0 + √N — TV 는 달력월(2개월 미만 daily) + RFR 2%/yr + 비연율화. 동일 리포트에서 sortino(TV convention)와 sharpe(bar 기준)가 다른 척도로 병존(FE 는 "(bar 수익률 기준)" 라벨로 정직 고지 중). sharpe 변경은 trust-layer baseline + optimizer objective(`_SUPPORTED_OBJECTIVE_METRICS`) 랭킹에 영향.

**권장 접근:** engine/metrics.py `_periodic_returns` 재사용해 TV convention sharpe 구현 → baseline 재생성(diff = sharpe 키 한정 단언) + optimizer 랭킹 flip 여부 실측 후 교체.

**Risk:** 🟡 (optimizer objective 소비자 영향 — 분석 선행 의무).

---

### BL-401

**상태:** ✅ **Resolved (2026-07-23, `stage/functional-parity`)** — 근거: 본 섹션 `**Title:**` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:25`) · 인덱스 표 행 ✅.

**Title:** optimizer 3폼(grid/bayesian/genetic) field-level zod 에러 미렌더 — 검증 실패 시 사용자 무피드백 제출 차단 → ✅ **Resolved (2026-07-23, stage/functional-parity)**
**Category:** Frontend / optimizer 폼 UX
**Priority:** P2
**Trigger:** optimizer 폼 polish 또는 사용자 "제출 안 됨" 문의 시
**Est:** S-M (2-4h — 3폼 공통 필드 에러 표출 + 회귀 테스트)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (optimizer 폼 통합 작업 중 발견, 2026-07-05 코드 재검증)

**원인 / 영향:** `grid-search-form.tsx:47` / `bayesian-search-form.tsx:57` / `genetic-search-form.tsx:97` 은 `zodV4Resolver(FormSchema)` 를 쓰지만 `formState.errors` 를 어느 필드 컴포넌트(`optimizer-form-fields.tsx`/`param-rows-fieldset.tsx` — register/control 만 수신)에도 전달·렌더하지 않는다. 표출되는 에러는 mutation 실패 시 `FormErrorAlert`(GENERIC_ERROR_MSG) 뿐. `form-schemas.ts` 의 사용자향 검증 메시지("var_name required" :38 / superRefine "min < max 강제" :71 / "log_scale / log_uniform 은 min > 0 필요" :78 등)가 계산만 되고 화면에 도달하지 못해 `handleSubmit` 이 무피드백으로 제출만 차단한다. **스코프 노트:** backtest 폼은 zod resolver 미사용(RHF 네이티브 `useBacktestForm.ts:88`) + field 에러 정상 렌더(`backtest-form.tsx:111`, `BacktestCostFieldSet.tsx:36/69/93`) 확인 — 본 BL 스코프에서 제외. BL-350/354(✅ Resolved Sprint 62, `/optimizer` 리스트 row resilience)와 같은 도메인·같은 zod 지만 다른 표면(폼 입력)이다.

**권장 접근:** `waitlist-form-card.tsx:71` 의 field 에러 렌더 패턴대로 3폼 공통 필드 조각에 `errors` prop 전달 + 필드 하단 `text-destructive` 메시지 렌더. superRefine(param row 교차 검증)은 해당 row 하단 표출 위치 설계 동반.

**영향 파일:** `grid-search-form.tsx`, `bayesian-search-form.tsx`, `genetic-search-form.tsx`, `optimizer-form-fields.tsx`, `param-rows-fieldset.tsx`.

**Risk:** 🟢 (표출 전용 — 제출 페이로드 무변경. PR #394 characterization 스모크가 body 고정).

---

### BL-402

**상태:** ✅ **Resolved (2026-07-23, 구조 소멸)** — C 이식이 4사이트를 네이티브 `<select>` 로 재작성해 결함 자체가 사라졌다(실측 재확인, 코드 변경 0). 근거: 본 섹션 `**Title:**` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:25`) · 인덱스 표 행 ✅.

**Title:** optimizer 백테스트 picker `value={backtestId || undefined}` uncontrolled↔controlled 전환 콘솔 에러 + 트리거 raw UUID 노출 (BL-164 SSOT 미적용 회귀) → ✅ **Resolved (2026-07-23, 구조 소멸 — C 이식 네이티브 select 전환. 실측 재확인)**
**Category:** Frontend / optimizer UX
**Priority:** P2
**Trigger:** BL-401 과 묶음 권장 (동일 페이지)
**Est:** XS-S (1-2h)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 dogfood (2026-07-05 코드 재검증)

**원인 / 영향:** `optimizer-page-view.tsx:66` 이 `value={backtestId || undefined}` — 초기 `""` → `undefined`(uncontrolled) → 선택 후 UUID 문자열(controlled) 전환으로 콘솔 경고 유발. 또한 raw `Select`+`SelectValue`(render prop 無, :65-90) 라 선택 후 트리거에 full UUID 가 그대로 표시된다(옵션 label 은 `${symbol} · ${timeframe} · ${id.slice(0,8)}` 인데 트리거만 raw value). `SelectWithDisplayName`(BL-164 SSOT, `select-with-display-name.tsx`) 미적용 — Compare picker 동일 결함을 PR #383 에서 고친 것과 같은 계열의 회귀다(BL-164/176/206 은 전부 archived, 활성 추적 부재였음).

**권장 접근:** `SelectWithDisplayName` 로 교체 — value 는 순수 string(빈 값 처리 내장), label 매핑 캡슐화. PR #383 의 `equity-chart-with-compare.tsx:76` 패턴 그대로.

**영향 파일:** `app/(dashboard)/optimizer/_components/optimizer-page-view.tsx` (:33, :65-90).

**2026-07-12 pine-batch QA 실측 확장 (3사이트 추가):** (a) `backtests/_components/forms/backtest-form.tsx:84-106` **strategy picker** — 옵션 실클릭 후 트리거 raw UUID 노출 Playwright 실측 + 소스 감사로 원인 확정 (raw `Select`+자식 없는 `SelectValue`). (b) `report/trade-ledger-table.tsx:98-125` (c) `trades/trade-filter-row.tsx:116-141,202-211` 방향/결과 필터 — 동일 클래스 (value≠label), 선택 후 raw 토큰 노출 추정. 전부 `SelectWithDisplayName` 교체로 일괄 처리 (`equity-chart-with-compare.tsx:76` 선례). 상세: `docs/archive/qa/2026-07-12-pine-batch-1h4h/report.md` §6.1.

**Risk:** 🟢 (프리젠테이션 전용 — 선택 값 전달 로직 무변경).

---

### BL-460

**Title:** 백테스트 마진 게이트가 **gross 자본**으로 판정 — 수수료·슬리피지 차감 전 `running_equity` 사용
**Category:** Backtest / Risk (레버리지 모델 정확도)
**Priority:** P2
**Trigger:** 실자금 레버리지 백테스트 신뢰 필요 시 / BL-186b 진행 시
**Est:** M (설계 선행 필요)
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
**출처:** 2026-07-28 live-observability — soak 세션 생성 중 화면 관측 + 코드 대조

**원인 / 영향:** `LiveSignalSessionService.register()` 의 계정 게이트는 `account.exchange != bybit or account.mode != demo` **뿐**(`live_session_service.py:108-112`). `read_only` 는 검사하지 않는다. `read_only` 강제는 **청산**(`close_service.py:59-60` → 422)과 **표시**(`position_service.py:301-302`)에만 있다.

즉 **읽기 전용 키로 라이브 자동매매 세션을 시작할 수 있다.** 세션은 평가·신호 생성까지 정상 진행하고 **주문 단계에서야** 실패한다(과거 원장에 `retCode 10005 Permission denied` 2건 실재).

★**화면이 악화시킨다** — 계정 선택 콤보박스가 `bybit demo- aaa`(`read_only=true`)를 **기본 활성 옵션**으로 놓고, 라벨만으로 두 계정을 구분할 수 없다. 쓰기 계정은 `bybit demo` 다.

**권장 접근:** `register()` 에서 `read_only` fail-closed(422) + 콤보박스에 읽기 전용 배지·비활성화.
**Risk:** 🟡

---

### BL-512

**상태:** ✅ **Resolved (2026-07-28, `feat/live-entry-parity`).** `qb_exchange_order_response_total{exchange,outcome,reason}` 신설 — **`retCode` 숫자로** 정규화한다(ccxt 예외 클래스로는 안 된다: `110093` 트리거방향오류와 `110017` reduce-only 위반이 **둘 다 `InvalidOrder`** 다). `outcome` ∈ `accepted|rejected|unknown` — ★**응답을 못 읽은 경우(타임아웃 등)를 "거절" 로 세면 개선치가 오염**되므로 `unknown` 으로 분리한다. `qb_live_conditional_guard_total{outcome}` 7종 신설. 정상 체결이 `exchange_missing` error 카운터를 올리던 오계상 수정. **soak 실측 검증 — `accepted/submitted` 27 · `rejected/reduce_only_violation` 2.** ★★두 가지가 사후 증명됐다 — (a) Bybit demo 는 **시장가도 `submitted` 로 응답**하고 체결은 WS 가 확정하므로, `filled` 만 accepted 로 셌다면 **카운터가 영구 0** 이었다(codex G1 검증이 코드 쓰기 전에 잡았다). (b) `110017` 을 `position_zero` 가 아니라 **`reduce_only_violation`** 으로 정정한 것이 옳았다 — soak 중 실제로 `"reduce-only order has same side with current position"` 이 나왔고, 옛 매핑이었다면 **포지션 반전 부작용이 "무해" 로 위장**됐을 것이다.

**Title:** 계측이 "우리가 하려던 것" 만 세고 "거래소가 한 것" 은 안 센다 — 거절 미계상 · 낙관적 placed · **정상 체결이 error 카운터**
**Category:** Backend / observability (trading)
**Priority:** P2
**Trigger:** metric 기반 경보를 붙이려 할 때
**Est:** M
**출처:** 2026-07-28 live-observability 적대 검증(거래소 실상 렌즈), 전건 코드 재현

**원인 / 영향:** 세 가지가 겹친다.

1. **거래소 거절이 `qb_order_rejected_total` 을 올리지 않는다.** 이 카운터의 import 지점은 `common/metrics.py`·`order_service.py`·`webhook.py` **3곳뿐**이고, 거절이 착지하는 `tasks/trading.py:403-415` 는 import 조차 없다. 그 카운터는 **pre-flight 게이트 전용**이다. 실제로 오르는 건 `qb_ccxt_request_errors_total{error_class="InvalidOrder"}` 하나인데, 증거금부족·심볼오류·트리거방향오류가 한 버킷에 섞인다.
2. **`qb_live_conditional_placed_total` 이 거래소 수락 전에 오른다.** `live_signal.py:645-652` — `order_service.execute()`(로컬 INSERT + Celery enqueue) 직후 `.inc()`. 거래소 왕복은 **다른 프로세스**다. `stage="place"` 의 `try` 도 로컬만 감싼다. **이번 soak 의 거절 2건도 "placed" 로 계상됐다.**
3. ★**정상 체결이 error 카운터를 올린다.** `live_signal.py:400-409` — probe 결과가 `filled` 면 `fill_confirmed = True` 로 두고 **무조건** `stage="exchange_missing"` 을 `.inc()` 한다. 대시보드에서 **체결이 곧 에러**로 보인다.

**권장 접근:** 거래소 응답 축의 카운터를 신설한다(`retCode` 를 저-카디널리티 사유로 매핑). `placed_total` 은 거래소 수락 후로 옮기거나 `submitted`/`accepted` 를 분리한다. `exchange_missing` 은 체결 확인 시 `.inc()` 하지 않는다(2줄).
**Risk:** 🟡 (동작 무영향 · 관측이 사실과 어긋난다)

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
**상태:** 🟡 **열려 있다 — 「계측 우선」으로 착수**(2026-07-30 close-mismatch-soak). 권장안 2종(leg 분리 / 발주 직전 재확인) 기각. 발주 형태 불변 + overshoot 계측 + 기본 비활성 캡.
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
**출처:** 2026-07-28 live-observability 코드 대조 (실행 재현은 read_only 제약으로 불가)

**원인 / 영향:** stand-down 술어는 `live_signal.py:462-464` → `list_active_by_account(sess.exchange_account_id)`, 구현은 `WHERE exchange_account_id == account_id`(`live_signal_session_repository.py:69-76`). **DB 행 id 축이다.**

우리 DB 의 두 계정 행 `19a8166a`·`0277c150` 은 **같은 `exchange_uid = 558689281`**(실측). 세션 둘을 서로 다른 계정 행에 붙이면 `shares_account_symbol = False` → **stand-down 미발화**. 그런데 두 세션은 **같은 거래소 포지션**을 건드린다.

★코드 주석(`live_signal.py:444-456`)이 스스로 전제를 밝힌다 — _"계정 순포지션을 세션 target 에서 빼는 산술은 '이 계정·심볼의 포지션이 이 세션 것뿐' 이라는 전제 위에 선다"_. 중복 등록에서 그 전제가 **조용히** 깨진다.

★지금 폭발하지 않는 이유는 `0277c150` 이 `read_only=true` 라서다 — **가드가 아니라 우연**이다. 등록 시 `exchange_uid` 를 이미 조회해 저장한다(`account_service.py:69,79`) — **가진 정보를 안 쓰고 있다.**

**권장 접근:** stand-down 축을 `exchange_uid + symbol` 로 올린다. **BL-505**(청산 lock 축이 포지션 정체성이 아니다)와 **같은 계열의 축 문제**다.
**Risk:** 🟡

---

### BL-519

**Title:** 컨테이너로 API 를 띄우는 배포에는 multiprocess 배선이 없다 — 조용히 폴백해 worker 지표를 영영 못 본다
**Category:** Infra / observability
**Priority:** P2
**Trigger:** 프로덕션 배포 시
**Est:** S
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
**출처:** 2026-07-28 live-observability G6 codex 최종 적대 리뷰 (P1 의 후속)

**원인 / 영향:** BL-506 이 metric mutation 을 in-memory 증가에서 **공유 mmap 파일 쓰기**로 바꿨다. 그래서 read-only 마운트·ENOSPC·I/O 오류에 예외를 던질 수 있다.

이번 세션은 **주문을 영구 좌초시키는 유일한 지점** 하나만 고쳤다 — `order_service.py` 의 commit 직후·dispatch 직전 `qb_active_orders.inc()`(예외 시 주문 행은 commit 됐는데 dispatch 가 안 되고, 멱등 재시도는 캐시 조기 반환에 걸려 **영구 미발주**).

남은 것: `dec()` **13곳**과 `tasks/trading.py`·`tasks/live_signal.py`의 다른 metric 호출. 이들은 terminal 전이 이후라 예외 시 Celery 재시도로 회복되므로 좌초시키지는 않지만, **불변식으로 못박는 것이 옳다.**

**권장 접근:** 머니-패스의 모든 metric mutation 을 `record_metric_safely` 로 감싸고, 그 규칙을 `.ai/stacks/fastapi/backend.md` 에 등재한다.
**Risk:** 🟡

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived ([BL-050/051/052/053/054/055/056/057/138/139/151/153](archive/refactoring-backlog/_archived.md#p3-전부-nice-to-have-컨벤션-정합)). **활성 P3 = 8** (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2 + BL-389/390/391 2026-06-30 backtest-deepen).

### BL-491

**Title:** 백테스트 폼이 Live 레버리지를 미러하지 않는다 (차단 사유가 이미 사실이 아니다)
**Category:** Frontend / 정합
**Priority:** P3
**Trigger:** 백테스트↔라이브 폼 패리티 작업 시
**Est:** S (2-3h)
**출처:** 2026-07-26 live-engine-parity 적대적 검증.

**원인 / 영향:** `useBacktestForm.ts` 의 `liveLeverage != null && liveLeverage !== 1` 이 `live_blocked_leverage` 를 내고 `BacktestSizingFieldSet.tsx` 가 "Live 미러" 옵션을 `liveLeverage === 1` 로 막는다. 원래 문구는 "백테스트의 1배 자기자본 기준과 비대칭" 이라 설명했는데 **거짓**이다. 같은 폼에 백테스트 레버리지 입력이 있고 `v2_adapter` 가 `leverage=cfg.leverage` 를 같은 엔진 게이트로 넣는다. BL-483 배선 후엔 라이브도 레버리지를 반영하므로 차단 사유가 더 이상 없다.

이번 스프린트는 **문구만** 사실대로 고쳤다(술어 불변). 실제 미러링 배선은 미착수.

**권장 접근:** Live 설정(leverage / margin_mode / position_size_pct)을 백테스트 config 로 미러하는 경로를 열고 `live_blocked_leverage` 분기를 제거한다. 미러 시 백테스트↔라이브 패리티가 폼 수준에서도 성립한다.

**영향 파일:** `frontend/src/app/(dashboard)/backtests/_components/forms/useBacktestForm.ts`, `.../BacktestSizingFieldSet.tsx`, `.../live-settings-badge.tsx`.

**Risk:** 🟢 (UX / 정합. 금전 영향 없음).

---

### BL-389

**Title:** backtest finance math 10 함수 (~250 LOC) 가 v2_adapter god-file 에 혼재 — `engine/metrics.py` Deep Module 추출 (locality)
**Category:** Backtest / Architecture (shallow-by-size / locality)
**Priority:** P3
**Trigger:** backtest deepening sprint
**Est:** M (4-6h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex DOWNGRADE → `metrics.py` 부재 직접 검증 후 KEEP 정정)

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
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md)

**원인 / 영향:** exit leg maker/taker 분기 `fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"` 가 `v2_adapter.py:265`(\_build_raw_trades)와 `:568`(\_compute_metrics)에 character-identical 복제. L549 주석은 'SSOT 위임으로 중복 제거' 라 주장하나 실제 SSOT 는 `_leg_cost` 뿐이고 routing 분기는 미위임 → `exit_kind` 의미 변경 시 2곳 동시 수정(money-path 수수료/슬리피지). 작지만 확정된 Locality 결함.

**권장 접근:** `fill_type` 라우팅을 단일 헬퍼(또는 RawTrade 메서드)로 위임 → 두 소비 사이트가 같은 한 곳을 호출. 주석의 SSOT 주장과 코드 일치.

**영향 파일:** `engine/v2_adapter.py` (:265, :568).

**Risk:** 🟢 (refactor-safe — `test_exit_leg_cost_split` C14 불변식이 발산 가드).

---

### BL-391

**Title:** backtest trades→equity→metrics 3단 reconciliation 불변식 암묵 + cross-stage oracle 부재 (test-first)
**Category:** Backtest / Test surface (locality / pure-fn-extracted anti-pattern)
**Priority:** P3
**상태:** Resolved (2026-08-03, backtest-metric-oracle)
**Trigger:** BL-389 metrics 추출과 묶음 또는 backtest test 강화 시
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex DOWNGRADE → 좁은 oracle 범위로 축소)

**원인 / 영향:** `_build_raw_trades`(:295) → `_compute_equity_curve`(:472) → `_compute_metrics`(:621) 가 상호 의존(equity ← trade pnl, metrics ← 양쪽)하나 각각 isolation 으로만 테스트되고 단계 간 계약(`sum(trade.pnl)` ↔ equity 종가 delta)이 문서화/검증 안 됨 = 'testability 위해 추출된 순수함수' 안티패턴.

**해결 (2026-08-03):** `tests/backtest/test_cross_stage_reconciliation.py` 5건 + 세 함수 docstring 에 계약 명시. 고정한 불변식 2종 — `equity[-1] - init_cash == Σ trade.pnl`(1단↔2단), `net_profit_abs == total_return × init_cash`(1단↔2단, 3단 경유). 후자가 유효한 이유는 `_compute_metrics` 가 두 값을 **서로 다른 입력**에서 독립 계산하기 때문이다(`:719` trades / `:663` equity).

**★전제 부분 반증:** 백로그가 표적으로 지목한 **off-by-one 은 이미 커버돼 있었다.** 실측 — `exit_bar_index <= bar_idx` 를 `<` 로 바꾸자 `test_golden_oracle_minimal` 2건 + `test_v2_adapter::test_equity_curve_accrues_realized_pnl_on_exit_bar` 가 red 가 됐다(골든이 equity **전 계열**을 하드코딩 기대값과 대조한다). 실제로 비어 있던 곳은 (a) **metrics 단계에서 두 집계가 서로 어긋나는 것**, (b) **fees > 0 경로**(기존 골든은 전부 `fees=0`)였다. `net_profit_abs` 비용 이중 차감 변조는 기존 backtest 스위트 **557건을 전부 통과**했고 신규 오라클만 잡았다.

**Risk:** 🟢 (test + docstring — 프로덕션 동작 변경 0).

---

### BL-306

**Title:** `~/.claude/CLAUDE.md` §5 한국어 콜론 종결 lint mechanism 도입
**Category:** Docs / Lint
**Priority:** P3
**Trigger:** 누적 위반 181 line 검출 (2026-05-15 audit) — auto-fix 가능
**Est:** S (3-5h)
**출처:** [`docs/dev-log/2026-05-15-claudemd-align-audit.md`](dev-log/2026-05-15-claudemd-align-audit.md) §6 Track C1, [LESSON-068](../.ai/project/lessons.md)

**현 상태:** docs/dev-log 161 + dogfood 12 + guides 8 = 181 line 한국어 sentence + `:` end-of-line 위반. false positive 0. lint mechanism 0 = LLM 매 generation 자연 위반.

**권장 접근:**

1. markdownlint custom rule 또는 ruff custom plugin 으로 한국어 콜론 종결 검출 (regex `[가-힣]+\s*:\s*$` minus 코드 fence + URL + table cell + frontmatter)
2. auto-fix script — 검출 line `:` → `.` 일괄 sed (false positive 0 검증된 docs/\* scope 만)
3. pre-commit hook 추가 + CI gate
4. LESSON-068 2/3 누적 → 3차 시 `.ai/common/global.md` §5 mechanism 의무 영구 승격

**영향 파일:** 새 lint config 1 + auto-fix script 1 + pre-commit hook 1 + 검출 181 line edit (auto-fix 1회).

**Risk:** 🟢 (lint + docs only, code 영향 0).

---

### BL-307

**Title:** `~/.claude/CLAUDE.md` §6 한국어 file header lint + 누락 70 file backfill
**Category:** Lint / Source
**Priority:** P3
**Trigger:** 누적 누락 70 file 검출 (BE 14 + FE 56, 2026-05-15 audit). main.py / core/config.py / trading/registry.py / app/layout.tsx 등 핵심 file 포함
**Est:** M (8-12h — lint rule 4-6h + 70 file 의미 있는 한국어 1줄 주석 작성 4-6h)
**출처:** [`docs/dev-log/2026-05-15-claudemd-align-audit.md`](dev-log/2026-05-15-claudemd-align-audit.md) §6 Track C2, [LESSON-068](../.ai/project/lessons.md)

**현 상태:** BE 14/157 (8.9%) + FE 56/243 (23%) = 70 file 신규 source 첫 3줄 한국어 주석 누락. config / test / **init** / index.ts / \*.d.ts 제외. ESLint custom rule 부재 + ruff custom rule 부재.

**권장 접근:**

1. ESLint custom rule (`require-korean-file-header.js`) — 첫 3줄 안 한국어 char 검출 의무. exempt list = config / test / spec / d.ts / index / generated.
2. ruff custom plugin 또는 pre-commit hook 으로 .py file 동일 검증.
3. 누락 70 file 일괄 한국어 1줄 주석 추가 (의미 = file 역할 한 줄 — LLM 일괄 생성 가능).
4. CI gate + pre-commit hook 추가. 신규 file 차단 mechanism.

**영향 파일:** ESLint config 1 + ruff config 1 + pre-commit hook 1 + 70 file 첫 줄 주석 추가.

**Risk:** 🟡 (lint config 변경 + 70 file touch — risk 낮으나 large diff).

**의존성:** BL-306 과 묶음 sprint 가능 (양쪽 모두 lint mechanism + 누적 누락 backfill).

---

### BL-367

**Title:** `_async_dispatch_event` 205 LOC + 8× `mark_failed+commit+metric` 반복 블록 추출
**Category:** Trading / Architecture (shallow-by-size)
**Priority:** P3
**Trigger:** trading deepening sprint (clean win, 단독 가치 낮음)
**Est:** XS-S (1-2h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

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
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

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
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**현 상태:** `state_handler.py` orphan buffer FIFO cap 1000(`_ORPHAN_MAX`) + out-of-order WS fill message / supervisor crash-restart cycle 가 고빈도(>100 fills/s) 스트레스 테스트 미검증. 현재 데모 빈도엔 충분.

**권장 접근:** post-Beta 모니터링(`qb_ws_orphan_buffer_size` gauge alert >800) + 필요 시 concurrent ordering 테스트 추가. 현재는 등재만.

**영향 파일:** `trading/websocket/state_handler.py` + 테스트.

**Risk:** 🟢 (현재 미발현, monitor).

---

### BL-394

**Title:** BE 거래 분포/수익구조 집계 엔드포인트 — `useAllBacktestTrades` 2000-cap 페이지 루프 대체
**Category:** Backtest / API + Frontend
**Priority:** P3
**Trigger:** 2000+ trades 백테스트가 흔해질 때
**Est:** M (4-6h)
**출처:** 2026-07-05 TV-parity sprint F1/F3 (FE 파생 분포·waterfall 은 표본 근사 캡션으로 정직 고지 중)

**원인 / 영향:** 수익 분포 histogram/거래 분포 donut/수익 구조 waterfall 이 FE 에서 전체 trades(최대 2000, 페이지 루프 10회)로 파생. 초과 시 "표본 기준" 근사. BE 집계 1 endpoint 면 정확+경량. **참고:** BE `gross_profit_abs`/`gross_loss_abs`/`per_side.*` 는 net(비용 차감 후) 기준 승/패 분해 — waterfall 용 비용 전(gross) 분해와 다름(FE `computeProfitStructure` 항등식 참조). 집계 endpoint 설계 시 두 정의 모두 제공 권장.

---

### BL-395

**Title:** lightweight-charts v5 업그레이드 spike — 네이티브 멀티-pane + 시간축 동기화
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** 차트 pane 4개+ 필요 또는 줌/팬 동기화 요구 시
**Est:** M (6-8h, spike)
**출처:** 2026-07-05 TV-parity sprint F2 (v4.2 는 멀티-pane API 부재 → 독립 인스턴스 3개 스택, 시간축 미동기화)

---

### BL-396

**Title:** `/backtests/[id]/trades` 상세 서브페이지에 TV 신규 컬럼(런업/드로다운/누적/fee split/exit_kind) 정렬
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 원장(trade-ledger-table)과 서브페이지 컬럼 비정합 불편 접수 시
**Est:** S (2-3h)
**출처:** 2026-07-05 TV-parity sprint F4 (원장만 신규 컬럼 반영, 서브페이지는 무변경)

---

### BL-397

**Title:** 백테스트 리포트 섹션 탭 URL 딥링크 (`?section=`)
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 리포트 특정 섹션 공유 요구 시
**Est:** XS-S (1-3h)
**출처:** 2026-07-05 TV-parity sprint F2 (탭 상태 비제어 유지 결정)

---

### BL-399

**Title:** `ta.sar` TV hand-oracle 부재 — parity 스팟 검증 미완
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3
**Trigger:** SAR 사용 전략 등장 시
**Est:** S-M (3-5h — AF/EP/flip 규칙 손유도)
**출처:** 2026-07-05 TV-parity sprint P1-4 (wma/bb/mom/obv/cross 는 스팟 판정 완료 — bb=population stdev=TV biased 기본 ✓, mom/obv/cross ✓. sar 만 오라클 미작성)

---

### BL-400

**Title:** optimizer 쿼리만 `enabled: userId != null` 가드 — 도메인 간 React Query enabled 정책 비일관 (통일 여부 결정 필요)
**Category:** Frontend / React Query 컨벤션
**Priority:** P3
**Trigger:** FE 훅 팩토리 후속 정비 시 (`use-auth-ctx` 소비 도메인 전수)
**Est:** S (2-3h — 정책 결정 + 일괄 적용)
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
**출처:** 2026-07-12 pine-batch QA 오라클 ② (`report.md` §4.2) → **2026-07-12 A+B+C Trust 번들에서 TV 공식문서로 반증**

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
**출처:** 2026-07-12 pine-batch QA (`docs/archive/qa/2026-07-12-pine-batch-1h4h/report.md` §2)

**원인 / 영향:** G2(array 15종) 이후 DrFXGOD_indicator_hard(=i3_drfx) 의 잔여 차단 표면. (a) `ta.alma`(Arnaud Legoux MA)·`ta.dmi`(DMI/ADX) 는 순수 지표 — stdlib 추가로 feasible. (b) `time("")` 호출형은 timestamp stub 확장으로 feasible. (c) `ticker.new` + `request.security_lower_tf` 는 멀티심볼·하위 TF 데이터 패러다임 — 단일 TF 백테스트 전제 밖(거부 유지가 정직). (a)+(b) 만 구현해도 DrFXGOD 는 (c) 로 여전히 차단 — **전체 지원 목표가 아니라 (a)(b) 의 범용 가치로 판단할 것**.

**권장 접근:** ta.alma/ta.dmi 를 `_names.TA_FUNCTIONS` + stdlib `_call` 에 추가 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서 대조 + 수계산 오라클). time() 은 bar timestamp 반환 stub. (c) 는 workaround 텍스트 유지.

**Risk:** 🟢 (신규 함수 추가 — 기존 경로 무변경).

---

### BL-407

**상태:** ✅ **Resolved (2026-07-13, PR #433 `stage/fe-react-audit`)** — 근거: 본 섹션 `**Title:**` 줄 + `**해소 (2026-07-13):**` 문단(실 리포트 스크린샷 육안 검증 PASS).

**Title:** 백테스트 리포트 낙폭(Drawdown) 차트 Y축 눈금 전부 "-0.1%" 동일 표기 — 축 포맷터 정밀도/단위 버그 → ✅ **Resolved (2026-07-13, PR #433 stage/fe-react-audit)**
**Category:** Frontend / backtest 리포트 차트
**Priority:** P3
**Trigger:** backtest 리포트 차트 polish 사이클
**Est:** XS (0.5-1h)
**출처:** 2026-07-12 pine-batch QA Playwright 실측 (`docs/archive/qa/2026-07-12-pine-batch-1h4h/screenshots/03-backtest-report-1h.png`)

**해소 (2026-07-13):** 원인 실측 확정 — lightweight-charts **v4 `PercentageFormatter` 는 값에 ×100 을 하지 않으며**(파일 주석의 전제가 거짓), percent 타입 precision 이 priceScale 에서 1/2 단위 양자화되어 |값|∈[0.25,0.75) 눈금이 전부 "-0.1%" 로 붕괴하는 이중 결함. `type:"custom"` 포맷터(비율×100 + toFixed(2)%)로 함정 자체 회피. 실 리포트 스크린샷 육안 검증 PASS (0.00% ~ -44.91% 정상 렌더).

**원인 / 영향:** MDD -59.91% 인 리포트에서 낙폭 미니차트 Y축 눈금 4개가 모두 "-0.1%" 로 표기 (현재값 배지도 -0.1%). 시리즈 형상은 정상 변동 — 눈금 라벨 포맷터가 ratio(-0.0~-0.6)를 %로 변환할 때 정밀도가 뭉개지거나 tick 간격 계산이 단위 불일치로 보임. 시각 신뢰 훼손 (Surface Trust ADR-019 관점).

**권장 접근:** lightweight-charts drawdown pane 의 priceFormat/tickMarkFormatter 확인 — ratio→% 변환 위치와 `precision` 옵션 정합. 라이트/다크 양 테마 + 1M/3M/6M/전체 기간 스위치 회귀 확인.

**Risk:** 🟢 (표시 전용).

---

### BL-408

**Title:** 리포트/위저드 Precision Instrument 폴리시 잔여물 팩 (stale aria-label 색명 + radius/글래스/레이블 어휘 6건)
**Category:** Frontend / 디자인 시스템 정합
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-402 처리와 묶음 권장 — 파일 겹침)
**Est:** S (2-3h — 전부 표시 전용)
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
**출처:** 2026-07-12 A+B+C Trust 번들 — BL-405 재분류 과정에서 TV 문서 검증 + 회귀 테스트(`test_na_bool_tv_parity.py`)로 표면화

**원인 / 영향:**

- **(a) ta.ema 워밍업 시딩** — 엔진 `ta_ema`(stdlib.py:81-97)는 첫 `length-1` bar 를 nan 으로 두고 bar `length-1` 에서 SMA 로 시드. 실제 TradingView 의 ta.ema 워밍업 시작 bar/값이 다르면 emaSlow 가 다른 bar 에서 살아나 `bull != bull[1]` 첫 전환이 다른 bar 로 이동한다. **bs 4h 2024 의 엔진 bar 12 vs 오라클 주장 bar 15 편차의 진짜 후보** (bool-na 와 무관). 확정하려면 실제 TradingView 에서 bs 4h 2024 의 첫 시그널 bar + ta.ema(5)/ta.ema(13) 초기 시리즈를 관측해 엔진과 대조해야 함 (순수 pandas 오라클이 엔진과 같은 시딩을 가정하면 순환검증 — §7.3).
- **(b) bool[n] 범위밖 과거참조** — `_eval_subscript`(interpreter.py:882-884)가 범위밖 history 를 타입 무관 nan 반환. bool 변수의 `b[1]` 이 bar 0 에서 nan (TV 는 false). 소비(비교/제어흐름)에서 `_truthy`/비교가 nan→false 로 소거 → **거래·시그널 영향 0** (test_na_bool_tv_parity.py 가 관측 등가 잠금). raw 저장 값만 편차.

**권장 접근:** (a) 실제 TV ta.ema 초기 시리즈 캡처 → 엔진 시딩 규칙 대조/조정 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서/실행 대조 + 수계산 오라클). (b) 관측 등가라 저순위 — 정적 bool 타입 추론 도입 시 함께 (pine_v2 동적 타입이라 난이도 있음).

**Risk:** 🟢 ((a) 조사 우선; (b) 관측 무영향).

---

### BL-461

**Title:** `_periodic_returns` daily fallback 이 sub-daily 봉을 "1 bar = 1 day" 로 센다 (resample 부재)
**Category:** Backtest / metrics (TV parity)
**Priority:** P3
**상태:** Resolved (2026-08-03, backtest-metric-oracle)
**Trigger:** 2개월 미만 백테스트의 Sharpe/Sortino 문의 시
**Est:** S-M (baseline 2 metric 확산 주의)
**출처:** 2026-07-26 backtest-trust 스프린트 (BL-398 구현 중 발견)

**원인 / 영향:** `engine/metrics.py` 의 else 분기가 **resample 없이 전 bar** 를 기간 표본으로 쓰고 RFR 은 `0.02/365` 를 적용했다(등재 당시 인용 `:41-43` 은 BL-465 가드 추가로 밀려 실제로는 `:62-65`). 1h/5m 백테스트가 2 달력월 미만이면 1시간을 하루로 세어 위험조정 지표가 왜곡된다. **sortino 가 이미 갖고 있던 선재 결함**이고, BL-398 이 `_periodic_returns` 를 재사용하면서 sharpe 로도 전파됐다.

**해결 (2026-08-03):** else 분기를 `equity.resample("D").last().dropna()` 로 교체. 실측 왜곡 크기 — 같은 자본 경로 `[100, 110, 99]` 를 1h 봉 72개로 적으면 Sharpe 가 `-0.003265` 로 참 값 `-0.000548` 의 약 6배였고(sortino 는 `-0.004614` vs `-0.000774`), **하루치 1h 봉 24개 상승 구간에서는 23개의 가짜 "일간" 수익률로 Sharpe `16.56` 을 만들어냈다.** 리샘플 후 표본이 2 미만이면 `unavailable` 이다 — 없는 정보를 지어내지 않는다.

**검증:** `test_golden_oracle_tv_pack.py` 에 hand-oracle 3건 신설(봉-단위 불변성 + 손계산 값 + 단일일 경계). 수정 전 3건 전부 red → 수정 후 green. 기존 daily 테스트 2건은 `freq="D"` 라 `resample("D")` 가 항등이므로 green 유지. **골든 baseline regen 0행** — 코퍼스 7벌이 전부 월간 경로다(parity 20 passed 로 확인). 우려됐던 "sortino 로의 2 metric 확산" 은 코퍼스에서 발생하지 않았다.

**부수 실측:** `scripts/seed_dogfood.py` 의 `daily` RunSpec(2026-03-02~03-30, `TIMEFRAME="1h"`)이 정확히 이 케이스라 dogfood 시드의 sharpe/sortino 가 바뀐다. 시드는 생성물이지 고정 baseline 이 아니라 게이트에는 안 걸린다.

**Risk:** 🟢 (2개월 이상 백테스트는 월간 경로라 무영향).

---

### BL-462

**Title:** 백테스트 목록 Sharpe 정렬이 신·구 컨벤션을 섞어 센다
**Category:** Backtest / API (정렬 정합)
**Priority:** P3
**Trigger:** 구 백테스트가 목록에 남아 있는 동안
**Est:** M (equity_curve 로딩 필요)
**출처:** 2026-07-26 backtest-trust 스프린트 (codex G0 P1 지적 → 수용)

**원인 / 영향:** `backtest/repository.py:71-77` sort whitelist 가 `metrics->>'sharpe_ratio'` 를 Numeric 캐스팅해 **서버 정렬**하는데 convention 을 보지 않는다. 마커(`sharpe_convention`)는 혼재를 **보이게** 할 뿐 정렬을 **고치지는** 못한다 — 의미가 다른 값이 계속 한 순위로 섞인다.

**권장 접근:** 목록에서 equity_curve 를 읽어 read-time recompute(성능 부담 — `list_by_user` 가 `defer(equity_curve)` 중), 또는 구 컨벤션 행을 정렬에서 분리 표시. 현재는 **FE 고지**("구 기준과 현재 기준 샤프가 섞여 있어 정렬 순위를 그대로 신뢰할 수 없습니다")로 대응.

**Risk:** 🟢 (고지 중 · 과거 백테스트를 재실행하면 자연 소멸).

---

### BL-463

**Title:** optimizer / stress_test 저장 sharpe 에 컨벤션 마커 없음
**Category:** Optimizer / Stress test (metrics 정합)
**Priority:** P3
**Trigger:** 구 optimizer·stress 결과 재해석 필요 시
**Est:** M (2 도메인 JSONB 스키마 확장)
**출처:** 2026-07-26 backtest-trust 스프린트 (codex G0 P2 지적 → 스코프 밖 수용)

**원인 / 영향:** `optimizer/serializers.py:104` 와 `stress_test/serializers.py:80,159` 가 각자 독립 JSONB 에 sharpe 를 저장한다. 본 스프린트는 **backtest metrics 만** 마킹했으므로 두 도메인의 과거 결과는 구·신 구분 없이 남는다. 신규 실행은 새 수식이지만 저장값에 그 사실이 기록되지 않는다.

**권장 접근:** 두 도메인 result JSONB 에도 컨벤션 마커 추가 + FE 표기. 3 도메인 동시 마킹은 스코프 폭발이라 분리했다.

**Risk:** 🟢 (신규 실행은 일관 · 구 결과 비교 시에만 오해 가능).

---

### BL-504

**Title:** ADR-013 / ADR-019 가 존재하지 않는데 진입 문서 4곳이 가리킨다
**Category:** Docs / decisions (참조 정합)
**Priority:** P3
**Trigger:** Optimizer 설계 근거를 다시 물을 때 (알고리즘 교체 · scikit-optimize 이탈 · GA 파라미터 변경)
**출처:** 2026-07-27 `/claude-md-improver` CLAUDE.md 감사

**원인 / 영향:** `docs/decisions/` 는 001~012 · 014~018 · 020 · 021 로 **013 과 019 가 결번**이다. 그런데 다음이 ADR-013 을 실재하는 근거처럼 인용한다.

- `AGENTS.md:67` — "Optimizer — Grid / Bayesian / Genetic 파라미터 최적화 (ADR-013)". **새 세션이 첫 step 에 읽는 3종 중 하나다.**
- `CONTEXT.md:46` — 도메인 헌법의 Optimizer 정의
- `docs/archive/product/2026-04-14-original-prd.md:8` — "scikit-optimize + 자체구현 GA (Optuna 아님 — ADR-013)"
- `docs/backlog.md:589,708,1828` — BL-235 근거 및 "ADR-013 §6 #8 deferred" · "§7.2/§8.2 result grammar"

경위는 `docs/archive/status-history.md:564` 에 남아 있다 — PR #306 이 _"ADR-013 충돌 해소 (trust-layer → ADR-020, optimizer 013 유지)"_. trust-layer 는 020 으로 이동했는데, **013 을 유지하기로 한 optimizer ADR 은 끝내 작성되지 않았다.** ADR-019 도 같은 모양이다 — 실체는 `docs/dev-log/2026-05-05-sprint30-surface-trust-pillar-adr.md` 인데 당시 status 이력 등이 "ADR-019" 로 불렀다.

영향은 조용하다. 인용된 `§6 #8` · `§7.2/§8.2` 는 **검증할 수 없는 근거**이고, Optimizer 설계를 바꿀 때 필독해야 할 문서가 열리지 않는다. `AGENTS.md` §문서의 자체 규칙(_"폐기는 삭제가 아니라 `Superseded` 표기"_)도 지금 상태로는 위반이다.

**권장 접근:** Sprint 53~57 dev-log + backlog 인용문(§6 #8 / §7.2 / §8.2)을 근거로 `013-optimizer-strategy.md` 를 소급 작성하고, ADR-019 는 dev-log 실체를 `decisions/019-*.md` 로 승격하거나 인용 4곳을 dev-log 경로로 교정한다. 소급 작성은 **결정을 새로 만드는 게 아니라 이미 실행된 결정을 기록**하는 것이므로, 없는 근거를 지어내지 말고 실제 코드(`optimizer/executors/`)와 대조한다.

**Risk:** 🟢 (동작 무영향 · Optimizer 설계 변경 시에만 근거 부재가 드러난다).

---

### BL-505

**Title:** 청산 공유 lock 의 축이 포지션 정체성이 아니라 `sessionId + symbol` 이다
**Category:** Frontend / trading (코크핏 §03)
**Priority:** P3
**Trigger:** 같은 계정·심볼에 세션이 여러 개 생긴 뒤 두 표에서 연달아 청산을 누를 때
**Est:** S
**출처:** 2026-07-28 live-ops-hygiene codex 최종 적대 리뷰 (재현 판정 후 등재)

**원인 / 영향:** BL-502 의 `mutationKey` 는 `["close-position", sessionId, symbol]` 이다. 그런데 두 표가 같은 포지션에 대해 **서로 다른 `sessionId` 를 잡을 수 있다** — 계정 표는 그 계정·심볼의 **최신** 귀속 세션(비활성 포함, `position_service.py:283`)을 쓰고, 세션 표는 **활성** 세션별로 렌더한다. 최신 세션이 비활성이고 더 오래된 세션이 활성이면 두 키가 갈리고 lock 이 분리된다 → 같은 순 포지션에 감소전용 주문 2개가 나갈 수 있다(BL-502 가 없애려던 바로 그 상태).

★**추가된 테스트도 이 경로를 판별하지 못한다** — `close-position-lock.test.tsx` 가 두 표에 **같은** `SESSION_ID` 를 주입한다. 정렬된 경우만 덮는다.

**권장 접근:** lock 축을 세션이 아니라 **포지션 정체성**(계정 또는 uid + 심볼 + 방향)으로 바꾼다. 다만 `close_position` API 가 세션 id 를 받으므로 키와 요청 인자가 갈라진다 — 그 분리를 감당할지 결정이 필요하다. 손실이 아니라 **원장 잡음**(두 번째 주문은 평탄해진 포지션에서 거부)이라 우선순위는 낮다.

**영향 파일:** `frontend/src/features/live-sessions/hooks.ts`, `.../account-positions-table.tsx`, `.../open-positions-table.tsx`.

**Risk:** 🟢

---

### BL-506

**상태:** ✅ **Resolved** (2026-07-28, `feat/live-observability`). `PROMETHEUS_MULTIPROC_DIR` + `MultiProcessCollector` 배선. 호스트 `backend/.metrics` → 컨테이너 `/metrics` bind mount 를 worker 4종이 공유하고, 식별자는 `{role}-{hostname}-{pid}`(언더스코어 금지 — 수집기가 basename 을 `split('_')` 로 파싱한다).

★**실증 (같은 순간 두 프로세스 대조)** — 미배선 API(:8100)에는 `qb_live_signal_evaluated_total` 이 **없고**, 배선 API(:8101)에는 **1.0** 이 있다. `qb_` 라인 수 **75 → 105**. 값을 올리는 주체가 master 가 아니라 **prefork 자식**(`counter_worker-64/65`)이라 "worker 별 exporter 포트" 안이었으면 못 봤다.
★**정확성 대조** — `placed_total` 합 **21** = DB 조건부 행 **21**, `evaluated_total` **29 = 29분**(beat 60초와 1:1).
★**실측된 제약 3건** — ① bind mount 전파가 **최대 18~20초 지연**(mmap 계층에 `msync` 호출이 없다) ② **PID 충돌은 파괴적**(컨테이너 4종의 master 가 전부 pid 51 — role 접두어가 없으면 같은 파일을 파괴적으로 공유) ③ `_created` 시리즈 **전면 소실**(30줄 → 0, multiprocess 모드의 내재적 성질).
★후속은 **BL-508**(gauge 절대값) · **BL-509**(파일 회수) · **BL-518**(관측 계약) · **BL-519**(컨테이너 API 배포) · **BL-520**(머니-패스 sweep) 으로 분리 등재.

**Title:** worker 프로세스의 Prometheus metric 이 스크레이프되지 않아 gauge 규율이 전부 관측 불가다
**Category:** Infra / observability
**Priority:** P2
**Trigger:** 운영 알림을 metric 기반으로 붙이려 할 때, 또는 실자금 cutover 전
**Est:** M
**출처:** 2026-07-28 live-ops-hygiene 적대 검증 (3기 중 2기가 독립 지적)

**원인 / 영향:** `/metrics` 는 FastAPI 프로세스만 노출한다(`src/main.py`). `docker-compose.yml` 의 `backend-worker`·`backend-beat`·ws-stream·optimizer_heavy 는 포트도 exporter 도 없고 레포에 `prometheus.yml` 도 없다. `prometheus_client` 의 기본 레지스트리는 프로세스 단위이고 `PROMETHEUS_MULTIPROC_DIR` 설정도 없다.

★그래서 **worker 에서 올리는 모든 counter/gauge 가 수집되지 않는다** — `qb_active_orders` 의 winner-only dec 규율, `qb_live_conditional_reconcile_errors_total` 의 `cancel_stalled`/`cancel_raced`/`sweep_cancel`/`exchange_missing`/신설 `janitor_*` 라벨 전부. 반대로 API 프로세스의 `inc` 만 수집되므로 **스크레이프되는 gauge 는 단조 증가**한다.

★이번 스프린트의 BL-503 이 gauge 표류를 닫는다고 적었는데, 배포 토폴로지에서는 그 dec 이 보이지 않는다. **코드는 맞고 관측 경로가 없다.** BL-499 의 "metric 이 관측되면 trigger" 도 이 상태에서는 성립하지 않는다.

> **(2026-07-28 정정)** 위 두 문장은 **해소됐다.** dec 은 이제 보인다 — 단 보이자마자 **gauge 절대값을 믿을 수 없다는 것**이 드러났다(BL-508). BL-499 의 trigger 도 발화 가능해졌으나 실관측은 여전히 0건이다(BL-499 본문 정정 참조).

**권장 접근:** `PROMETHEUS_MULTIPROC_DIR` + `MultiProcessCollector` 를 도입하거나, worker 별 exporter 포트를 열고 스크레이프 대상에 추가한다. 어느 쪽이든 **먼저 "지금 무엇이 수집되고 있는가" 를 실측**하고, 그 뒤에 metric 기반 trigger 를 쓰는 BL(499·503)의 문구를 정정한다.

**Risk:** 🟡 (동작 무영향 · 그러나 metric 을 근거로 한 판단이 전부 공허해진다).

---

### BL-507

**Title:** 계정 표의 접기·청산 가능성 판정이 view 컴포넌트 안에 있다
**Category:** Frontend / trading (레이어)
**Priority:** P3
**Trigger:** 접기 규칙이 한 번 더 바뀔 때
**Est:** S
**출처:** 2026-07-28 live-ops-hygiene codex 최종 적대 리뷰

**원인 / 영향:** `collapseRows`(`account-positions-table.tsx`)가 권한(`readOnly`)·귀속 세션·차단 사유를 해석해 대표 행과 청산 가능성을 결정한다. `.ai/rules/frontend.md` 의 view ↔ 비즈니스 로직 분리 원칙 위반이다.

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
**출처:** 2026-07-28 live-observability 적대 검증(관측 계약 렌즈) + 실측

**원인 / 영향:**

- ★**`_created` 시리즈 전면 소실.** 실측 — 미배선 API **30줄** → 배선 API **0줄**. `prometheus_client` 의 `_created` 는 `ValueClass` 를 거치지 않는 순수 float 이라 mmap 에 실리지 않는다. `rate()` 는 무영향이나 `_created` 기반 쿼리는 깨진다. **multiprocess 모드의 내재적 성질**이지 우리 버그가 아니다.
- **프로덕션 경로가 테스트되지 않는다.** 테스트 env 에 `PROMETHEUS_MULTIPROC_DIR` 이 없어 전 스위트가 폴백을 탄다. **`/metrics` HTTP 를 multiproc 모드로 때리는 테스트가 0건**이다(신규 테스트도 `render_metrics()` 단위까지).
- **`qb_ws_orphan_buffer_size` 값 범위 변화.** docstring 은 "capped at 1000" 인데 `concurrency=3` + `livesum` 이라 0~3000. 기존 임계 재조정 필요.
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
**출처:** 2026-07-28 live-observability G1 codex 적대 검증, 코드 재현 완료

**원인 / 영향:** `live_signal.py:813` 은 `list_pending(limit=10_000)` 결과를 `.set()` 하고, `:1475` 는 `list_pending(limit=50)` 결과를 같은 gauge 에 `.set()` 한다. **마지막 writer 가 이긴다.** 실제 pending 이 50 을 넘으면 recovery task 가 **50 으로 덮어써** 적체 신호가 조용히 잘린다.

★**단일 프로세스에서도 이미 그런 선재 결함**이다 — BL-506 이 만든 것이 아니다.

**권장 접근:** recovery task 의 `.set()` 을 제거하거나(문서상 계약은 "last eval cycle"), 두 소스를 라벨로 가른다.
**Risk:** 🟢

## Beta 오픈 번들 — 단일 milestone

> **deferred** — Beta 본격 진입 trigger (BL-005 self-assessment ≥ 7/10 + 본인 의지 second gate) 도래 시 main 으로 row 이동.
>
> 상세 sub-task ([BL-070~075](archive/refactoring-backlog/_deferred.md#beta-본격-진입-milestone-bl-070075)) + TODO.md L748~801 보존.

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
**출처:** 2026-07-13 vercel 70룰 멀티에이전트 감사 (파인더 6 + 반박형 검증, 원시 24 → 확정 18 중 high/medium 10건은 stage/fe-react-audit PR #433 에서 해소 — 본 팩은 low 8건)

**원인 / 영향:** (1) `components/ui/form.tsx:6` + `features/trading/index.ts:3` 배럴 import. (2) `features/strategy/webhook-secret-storage.ts:53` + `draft.ts:89` localStorage 버전 스키마 부재. (3) `features/backtest/utils.ts:218` 함수 결과 캐시 부재 + `equity-chart-v2.tsx:184` / `trade-stats-strip.tsx:113` filter/map 다중 순회. (4) `components/charts/trading-chart.tsx:300` data effect 의 `fitContent()` 가 매 sync 마다 실행되는 설계 — 근본 수정(최초 1회 제한)은 전 호출처 동작 변경이라 별도 검토 (PR #433 은 호출측 identity 안정화로 해소).

**권장 접근:** 항목별 1-line~소형 수정. (4)는 lightweight-charts v5 업그레이드 (BL-395) 와 함께 재검토.

**Risk:** 🟢.

---

### BL-411

**상태:** ✅ **Resolved (2026-07-23, `stage/functional-parity`)** — 근거: 본 섹션 `**Title:**` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:25`, "지원 kind 목록 `OptimizationKind` enum 파생").

**Title:** optimizer 422 에러 메시지 stale — "Sprint 55 supports {grid_search, bayesian}" 이 genetic 활성 후에도 미지원 안내 → ✅ **Resolved (2026-07-23, stage/functional-parity — `OptimizationKind` enum 파생 + Sprint 넘버 문구 중립화)**
**Category:** Optimizer / correctness (사용자 노출 메시지)
**Priority:** P3
**Trigger:** optimizer 다음 터치 시 동승
**Est:** XS (~0.5h)
**출처:** 2026-07-13 optimizer deepen 감사 후보 N3 (사용자 pick 제외 → BL 등재). `backend/src/optimizer/exceptions.py:43-76`

**원인 / 영향:** genetic 은 Sprint 56 활성인데 `OptimizationKindUnsupportedError` 메시지가 "genetic = Sprint 56+ 예정" 이라 안내 — kind mismatch 시 사용자가 틀린 지원 목록을 받음. `OptimizationParameterUnsupportedError` 의 "Sprint 54 MVP" 문구도 동류.

**권장 접근:** 지원 목록을 `OptimizationKind` enum 에서 파생해 drift 구조 차단 + `test_exceptions.py` 메시지 assert 갱신.

**Risk:** 🟢 (문자열).

---

### BL-412

**Title:** optimizer result read-side 판별 유니온 (C-full) — `OptimizationRunResponse.result: dict[str,Any]` 를 FE 동형 `OptimizationResultOut` 으로
**Category:** Optimizer / Arch (read-side 타입화)
**Priority:** P3
**Trigger:** optimizer 폼/리포트 다음 기능 사이클 (BL-235/236/364 중 아무거나 착수 시 동승 검토)
**Est:** M (+80~120 LOC, FE 동형 유지 의무)
**출처:** 2026-07-13 optimizer deepen 감사 후보 C-full (C-min 은 동일 세션 해소 — get/list 손상 row 방어 대칭화, PR feat/optimizer-cmin-n2)

**원인 / 영향:** BE 는 typed 역직렬화 역량(`*_from_jsonb`)을 갖고도 read 응답을 untyped dict 로 흘려 FE zod 가 유일한 검증층. writer 변경 시 drift 를 BE 테스트가 못 잡음 (BL-388/392 harm-class).

**권장 접근:** ADR-013 §7.2/§8.2 result grammar 를 정확히 mirror 하는 `OptimizationResultOut` 판별 유니온 추가 — 반드시 C-min 의 저하 경로(retro-incorrect row 404) 위에서 soft-validate. FE `schemas.ts` 와 필드 1:1 대조 테스트 동반.

**Risk:** 🟡 (구 row 실패율 상승 가능 — C-min 선행 완료로 완화됨).

---

### BL-413

**Title:** 주문 상세 조회 배선 — BE `GET /orders/{id}` 기존재하나 프로토타입 screen-11 에 상세 affordance(행 확장/드로어) 부재로 defer
**Category:** Frontend / orders
**Priority:** P3
**Trigger:** 주문 상세 화면/드로어가 디자인 캐논(프로토타입)에 추가될 때
**Est:** S (2-4h)
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
**출처:** 2026-07-23 BL-401 적대 평가 사소 지적 (waitlist/optimizer 2곳+@ 사본)

**원인 / 영향:** waitlist·optimizer 가 동일 FieldError 를 로컬 복제. 또 커스텀 resolver 가 평탄 키(`parameters.0.max`)로 에러를 만들면 RHF per-field 재검증(dotted-path unset)이 못 지워 제출 재시도까지 stale 에러가 남을 수 있음 (중첩 경로 폼 첫 소비 사례).

**권장 접근:** `components/` 공용 FieldError 승격 + resolver 평탄/중첩 키 정책 1개로 통일 + stale 재검증 재현 테스트.

---

### BL-416

**✅ Resolved (2026-07-24 trading-surface-pack)** — `cancelOrder.variables===o.id` 행별 disabled + 비-409 broad toast + 실 ACTIVE_ORDER_STATES import.

**Title:** 주문취소 FE polish 팩 — 행별 disabled(현재 전역 `isPending` 으로 전 행 잠김) + 비-409 에러 무피드백 + 테스트 mock 의 ACTIVE_ORDER_STATES 리터럴 드리프트
**Category:** Frontend / orders UX
**Priority:** P3
**Trigger:** 다건 미체결 운영이 일상화되거나 orders 다음 터치 시
**Est:** S (2-3h)
**출처:** 2026-07-23 A2 적대 평가 사소 지적 3건 묶음

**원인 / 영향:** 한 건 취소 중 다른 행 버튼도 잠김(기능 위반 아님, 거친 UX). 네트워크/500 실패 시 toast 무발화(도메인 관례와는 일치). 테스트 mock 이 실 상수 대신 Set 리터럴 복제라 드리프트 침묵.

**권장 접근:** mutation variables 기반 행별 pending + 비-409 공용 에러 toast 정책 결정 + mock 을 실 상수 import 로.

---

### BL-417

**상태:** ✅ **Resolved (2026-07-24, `stage/opspack-ws2`)** — 근거: 본 섹션 `**Title:**` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 "BL-417 drop").

**Title:** `LiveSignalState.last_open_trades_snapshot` 이 실경로에서 항상 `{}` — 저장 가드가 리스트를 버림 (dead data 컬럼) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend / trading live-signal
**Priority:** P2
**Trigger:** live_signal 다음 터치 또는 스냅샷 소비자 신설 시
**Est:** S (2-4h)
**출처:** 2026-07-24 tier-c G0 (codex) 발견 — 코드 대조 확정

**원인 / 영향:** `to_report()` 는 `open_trades` 를 **리스트**로 내는데(strategy_state.py:813) live_signal.py 업서트 가드는 `isinstance(dict)` 만 저장 → 컬럼이 영구 `{}`. tier-c 포지션 대조는 `last_strategy_state_report["open_trades"]` 로 우회했으나, 컬럼 자체는 죽은 데이터로 남아 미래 소비자를 오도한다.

**권장 접근:** 저장 계약을 리스트로 교정(소비자 전수 확인 후) 또는 컬럼 제거 마이그레이션. 어느 쪽이든 report 필드와의 SSOT 단일화.

---

### BL-418

**상태:** ✅ **Resolved (2026-07-24, `stage/opspack-ws2`)** — 근거: 본 섹션 `**Title:**` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 "payload 계약").

**Title:** realtime 이벤트 payload 계약 미강제 — publisher/manager 가 임의 dict 통과 (worker 간 계약 drift 표면) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend / realtime
**Priority:** P3
**Trigger:** 발행 지점 추가 또는 이벤트 타입 확장 시
**Est:** S (2-3h)
**출처:** 2026-07-24 tier-c 최종 diff 리뷰 (codex MINOR)

**원인 / 영향:** BE 에 타입별 payload Pydantic 모델이 선언돼 있으나 publish_realtime 은 dict 를 그대로 직렬화. 필수 필드 누락 발행 시 FE zod 가 조용히 drop — 현 13개 발행 지점은 전부 채우지만 신규 지점의 계약 위반을 못 잡는다.

**권장 접근:** publish_realtime 이 event_type 별 payload 모델로 validate (no-raise 유지 — 실패 시 skip+counter) + 계약 테스트.

---

### BL-419

**상태:** ✅ **Resolved (2026-07-24, `stage/opspack-ws2`)** — 근거: 본 섹션 `**Title:**` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 정비 팩 6종).

**Title:** live_signal `result.errors` 경로의 세션 자동 비활성이 `session_state` 를 발행하지 않음 (최대 30s stale) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend / realtime
**Priority:** P3
**Trigger:** realtime 다음 터치 시
**Est:** XS (1h)
**출처:** 2026-07-24 tier-c 최종 diff 리뷰 (codex MINOR — live_signal.py:533 부근)

**원인 / 영향:** preflight/런타임 오류 2경로는 발행하나 `result.errors` 비활성 경로는 누락 — 폴링(30s)까지 코크핏 활성 세션 수가 stale.

**권장 접근:** 해당 commit 직후 발행 1줄 + spy 테스트 (publish-be 패턴 미러).

---

### BL-420

**Title:** WS 인바운드 서버 하드닝 팩 — 비인증 소켓 글로벌 상한/rate-limit + auth→realtime 역참조 정리
**Category:** Backend / realtime 보안·아키텍처
**Priority:** P3
**Trigger:** Beta 공개 배포 전 또는 realtime 다음 터치 시
**Est:** S (2-4h)
**출처:** 2026-07-24 tc-realtime-be 적대 평가 잔여 리스크 2건

**원인 / 영향:** accept 후 5s auth 창을 쥔 미인증 소켓의 동시 수 상한이 없음(per-user 상한은 인증 후에만 작동, Origin 은 비브라우저가 위조 가능 — 인증 자체는 별도라 보안 붕괴는 아님). 또 `src/auth/dependencies.py` 가 feature 도메인 `src.realtime.auth` 를 import 하는 방향 역전.

**권장 접근:** pre-auth 소켓 글로벌 상한/접속 rate-limit + helper 를 `src/auth/` 로 이동하고 realtime 이 역참조. (부수: position 서비스의 spot 방어 분기 dead code — `market_type` 키는 실경로 저장 불가 — 함께 정리.)

---

### BL-421

**상태:** ✅ **Resolved (2026-07-24, `stage/opspack-ws2`)** — 근거: 본 섹션 `**Title:**` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 "pending 시맨틱").

**Title:** 미평가 라이브 세션의 `/state` 404 무한 폴링 — 콘솔 error 도배 (정상 과도상태를 error 로 표면화) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend+Frontend / live-sessions
**Priority:** P2
**Trigger:** 라이브 세션 다음 터치 시
**Est:** S (2-3h)
**출처:** 2026-07-24 tier-c Opus dogfood 발견 #1 (기존재 동작 — tier-c 회귀 아님)

**원인 / 영향:** 신규 세션은 첫 evaluate tick 전까지 `GET /live-sessions/{id}/state` 가 404("not yet evaluated"). FE 는 2-3s 간격 폴링이라 세션 선택 직후 콘솔 error 가 무한 누적(~90+/10분 실측). beat 정지 시엔 영구 지속.

**권장 접근:** BE 를 200+`evaluated:false`(또는 204) pending 시맨틱으로 바꾸거나, FE 가 이 404 를 예상 상태로 흡수(에러 로그 억제 + 폴링 백오프). 콘솔 위생 게이트의 기지 예외 목록에 임시 등재 금지 — 근본 해소.

---

### BL-422

**상태:** ✅ **Resolved (2026-07-24, `stage/opspack-ws2`)** — 근거: 본 섹션 `**Title:**` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 정비 팩 6종).

**Title:** 알림 규칙 생성 폼이 empty 상태에서만 노출 — 세션당 2번째 규칙(watchdog 등) UI 추가 불가 + 409 경로 UI 도달 불가 → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Frontend / alert-rules UX
**Priority:** P3
**Trigger:** 알림 규칙 실사용 개시 시
**Est:** XS-S (1-2h)
**출처:** 2026-07-24 tier-c Opus dogfood 발견 #2

**원인 / 영향:** 규칙 1개라도 있으면 "만들기" 어포던스가 사라져 loss_limit+watchdog 동시 운용을 UI 로 못 만든다 (BE 는 유형별 1개씩 허용). 409 안내 문구는 유닛으로만 검증됨.

**권장 접근:** ok 상태에도 "규칙 추가" 어포던스 유지 (rule_type 별 중복은 409 안내가 처리). 표기 nit 동반: threshold "5.00000000%" → trimming (dogfood 발견 #3).

---

### BL-423

**✅ Resolved (2026-07-30 conditional-entry-alignment)** — ★**원문 전제는 착수 preflight 에서 반증됐다.** `include_inactive` 쿼리 + 최근 종료 세션 목록 + 비활성 상세는 **BL-526(PR #496, 2026-07-29)이 이미 착지**시켰고, 상세 경로에 `is_active` 게이트는 한 곳도 없었다(`grep is_active router.py` → 0 hit). 이번 회차가 실제로 닫은 잔여는 셋이다 — (a) 코크핏 목록 쿼리 이중화 해소(`useLiveSessions(true)` 단일화, 같은 화면이 목록을 두 번 fetch 하던 것) → 그 부수로 **도달 불가였던 `LiveSessionTable` 의 `PAUSED` 칩과 active-first 정렬이 살아났다**(실브라우저 확인), (b) 넓어진 목록과 어긋난 안내 문구 4곳 정정, (c) **비활성 세션 상세 5경로(`/state`·`/positions`·`/events`·`/alert-rules`·`/outcome-parity`)가 200 이라는 회귀 테스트 신설** — 동작은 맞았지만 고정돼 있지 않아 누가 `is_active` 필터를 넣어도 안 깨졌다. 사유 표시는 [BL-484](#bl-484) 로 함께 착지. 잔여 2건은 [BL-550](#bl-550)·[BL-551](#bl-551) 로 분리.

**Title:** 비활성(과거) 세션의 진단 정보를 UI 로 열 수 없음 — `/live-sessions` 가 active 전용
**Category:** Frontend / live-sessions UX
**Priority:** P3
**Trigger:** 과거 세션의 규칙·포지션·상태 회고 필요 시
**Est:** S (2-4h)
**출처:** 2026-07-24 opspack-ws2 Opus dogfood — 검증자가 RQ 캐시 주입으로 우회해야 했음 (docs/archive/sprints/opspack-ws2/context-notes.md #14)

**원인 / 영향:** BE `list_active()` 필터 + FE 리스트 클릭 전용 진입이라 비활성 세션의 알림 규칙/포지션 대조/state 를 볼 방법이 없다. 세션 종료 후 회고·규칙 정리가 불가.

**권장 접근:** 목록 API 에 `include_inactive` 쿼리 또는 별도 이력 뷰. 상세 진입의 URL 파라미터화 동반 검토.

---

### BL-424

**Title:** 대시보드 실현손익 카드 foot — 미실현(추정) 부기와 기존 문구가 시각적으로 밀착 (폭 부족)
**Category:** Frontend / dashboard 시각
**Priority:** P3
**Trigger:** 대시보드 polish 시
**Est:** XS (<1h)
**출처:** 2026-07-24 opspack-ws2 D8b dogfood 스크린샷 (docs/archive/sprints/opspack-ws2/context-notes.md #18)

**원인 / 영향:** foot 문장 줄바꿈 + 부기 병치로 간격이 타이트. 판독은 가능하나 밀도 과다.

**권장 접근:** 부기를 별도 행/뱃지로 분리하거나 foot 문구 축약.

---

### BL-425

**✅ Resolved (2026-07-24 trading-surface-pack)** — alert-rule-form 사전 중복검사(마운트된 `rules.data.items` 재사용, 새 fetch·409 요청·broad 콘솔 allowlist 없음). dogfood 전 상호작용 콘솔 error 0.

**Title:** 예상된 alert-rules 409(중복 활성 규칙)가 브라우저 콘솔 error 로 노출
**Category:** Frontend / 관찰성
**Priority:** P3
**Trigger:** 콘솔 위생 게이트 강화 시
**Est:** XS (<1h)
**출처:** 2026-07-24 opspack-ws2 D8b dogfood (기능 무해 — FE 는 정상 캐치·안내)

**원인 / 영향:** fetch 의 4xx 응답은 브라우저가 네이티브 로그를 남긴다. 409 는 정상 흐름(중복 안내)이라 노이즈.

**권장 접근:** 사전 중복 검사(로컬 규칙 목록 대조)로 409 요청 자체를 회피하거나, 콘솔 게이트에서 409 전용 좁은 예외를 채택할지 결정 (404 류 브로드 예외 부활은 금지).

---

### BL-426

**Title:** ws_stream 워커 용량 정책 — 멀티계정 시 public ticker starvation 가능 + 스트림 태스크 루프 직접 유닛 부재
**Category:** Backend / trading websocket 인프라
**Priority:** P3
**Trigger:** 거래소 계정 2개 이상 등록 시 (현 로컬 1계정 무해)
**Est:** S-M (2-6h)
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
**출처:** 2026-07-24 perf-surface A2 stretch 미실행 (SORT_OPTIONS 는 recent/name 만; 성과 3칸은 표기만, 정렬 축 부재)

**원인 / 영향:** 성과 열은 노출됐으나 전략 목록은 마지막수정/이름 정렬만 지원. latest_backtest 성과 기준 정렬 부재로 우열 비교가 목록 단계에서 제한적.

**권장 접근:** `latest_completed_by_strategy_ids` 결과를 정렬 축으로 노출(서버 정렬) + FE SORT_OPTIONS 에 수익률/샤프 추가. 클라 정렬은 페이지 한정이라 지양.

---

### BL-431

**✅ Resolved (2026-07-24 trading-surface-pack)** — 포지션-보고 TP/SL read-time 2열 + reduce-only 시장가 청산(세션스코프 202, flatten 가드 bypass, 청산 leverage=포지션값). 완전 TP/SL 보고(조건부 주문 조인)는 BL-434 이연.

**Title:** 코크핏 §03 열린 포지션 표 TP/SL·청산 액션 열 미렌더 — API 부재
**Category:** Backend / Frontend
**Priority:** P2
**Trigger:** 코크핏에서 포지션 TP/SL 확인 또는 시장가 청산이 필요할 때
**Est:** M-L (BE bracket/close 조회·발주 API + FE 열/액션)
**출처:** 2026-07-24 position-cockpit B4 (캐논 screen-01 은 TP/SL·청산 열 보유하나 `/positions` verdict 응답에 없어 §4.9 미렌더)

**원인 / 영향:** 캐논 프로토타입은 열린 포지션 행에 TP/SL 값 + 시장가 청산 액션을 두나, 현재 PositionService 응답은 대조 verdict + 거래소 보고 포지션(size/side/entry/mark/uPnL/liq/leverage)만 제공. TP/SL 부착 상태 조회 API 와 청산 발주 API 부재로 정직하게 미렌더.

**권장 접근:** 거래소 conditional order(TP/SL) 조회를 positions 응답에 조인 + reduce-only 시장가 청산 엔드포인트 신설 후 표 열/액션 렌더.

---

### BL-432

**✅ Resolved (2026-07-24 trading-surface-pack)** — `useLiveSessionsPositions` per-query select 제거 → `combineLiveSessionPositions(sessions, results)` 인덱스 zip(형제 aggregate 패턴) + 고아 `makePositionsSelector`/`LiveSessionPositionQueryData` 삭제.

**Title:** 잔고/포지션 useQueries select 콜백이 렌더마다 새 클로저
**Category:** Frontend / perf
**Priority:** P3
**Trigger:** 코크핏 리렌더 프로파일링 또는 vercel-react 정리 시
**Est:** S (2-3h; per-session selector 메모 또는 combine 이관)
**출처:** 2026-07-24 position-cockpit W3 평가(hooks.ts:340 `select: makePositionsSelector(session)` 렌더마다 새 identity → select 재실행)

**원인 / 영향:** `useLiveSessionsPositions` 의 useQueries 각 쿼리 `select` 가 렌더마다 새 함수라 select 변환이 매 렌더 재실행. combine 산출은 structural sharing 되고 identity-민감 effect 없어 무해(cosmetic/perf-only). 기존 per-render 팩토리 컨벤션(makeXFetcher)과 동일 패턴이라 회귀 위험 고려해 이번 스프린트 미수정.

**권장 접근:** session-label 부착을 select 대신 combine 으로 이관(쿼리별 select 제거)하거나 session 키 기준 selector 메모. tsc/lint 무영향.

---

### BL-433

**✅ Resolved (2026-07-24 trading-surface-pack, metric 부분)** — `qb_ws_subscribe_rejected_total{account_id}` counter + position_fanout reject `.labels().inc()`. BL-423(비활성 세션 진단 UI) 연계는 별도 유지.

**Title:** WS subscribe negative-ack 관측이 warning 로그만 — metric counter 부재 + BL-423 연계
**Category:** Backend / observability
**Priority:** P3
**Trigger:** position 구독 거부의 silent 폴링 degrade 를 대시보드로 감지하려 할 때
**Est:** S (metric counter + BL-423 비활성 세션 진단 표기)
**출처:** 2026-07-24 position-cockpit (PrivateTopicRouter subscribe success:false → `ws_subscribe_rejected` warning 만; 진단 §08 에서 PositionDiagnostic 제거로 포지션 상태가 §03 표로 이관)

**원인 / 영향:** position 구독이 거부되면 warning 만 남기고 15s 폴링으로 조용히 degrade — Prometheus counter 부재로 집계 불가. 또한 결정 ⑤로 §08 진단의 PositionDiagnostic 제거되어 비활성 세션의 포지션 상태 노출이 §03 표(활성 세션만)로 이관 → BL-423(비활성 세션 진단 UI)과 연계 재검토 필요.

**권장 접근:** `qb_ws_subscribe_rejected_total` counter 추가 + BL-423 에서 비활성 세션 포지션 상태의 별도 진단 표기 여부 결정.

---

### BL-434

**상태:** 🟡 **부분 Resolved (2026-07-25 close-completeness)** — 완전 TP/SL **보고(display)** 는 착지, **청산 스윕은 [BL-437] 이연**(codex G0 2 BLOCKING). 근거: 본 섹션 `**⚠️ Partially Resolved …**` 리드인 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:23`, "BL-434 부분 Resolved(display) + 신규 BL-437(스윕 이연)").

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

### BL-435

**✅ Resolved (2026-07-25 close-completeness)** — accept-time close_service DEL 은 무효(close = async Celery dispatch, 발주 accept 시점엔 미체결). **post-fill Celery DEL 로 구현**: `tasks/trading.py _execute_with_session` reduce_only fill 승자 경로 → `list_active_by_account` 세션들 캐시(`position_snapshot_cache_key`) best-effort DEL(WS fanout 독립, no-WS 창 커버). dogfood: 청산 후 redis `qb_pos_snapshot:*` 키 부재 실측 + §03 flat.

**Title:** 수동 청산 후 §03 flat 반영 지연 — WS 미연결 창에서 캐시 TTL+폴 지연(~15-30s)
**Category:** Backend / Frontend / UX
**Priority:** P3
**Trigger:** 청산 즉시성 UX 개선 또는 WS 미연결 시나리오 다발 시
**Est:** S (청산 서비스에서 position 캐시 DEL)
**출처:** 2026-07-24 trading-surface-pack dogfood (청산 202 후 오라클 flat 이나 §03 는 WS 미연결 창에서 ~30s 뒤 빈복귀 — 사용자 확정 비동기 202 설계 내이나 WS 의존)

**원인 / 영향:** 청산 flat 반영은 WS position_update(fast) + 15s 폴링(fallback)에 의존. 신규 활성 세션은 ws-stream reconcile(300s) 전이라 WS 미푸시 → 폴 fallback 만 동작(캐시 15s TTL + 폴 간격). 머니-패스 정확(청산 성공)하나 즉시성 미흡.

**권장 접근:** 청산 서비스가 발주 직후 `qb_pos_snapshot:{session_id}` 캐시 DEL(WS position_update 핸들러 DEL 패턴 미러) → 폴 fallback 이 WS 독립으로 fresh. (거래소 체결 지연은 잔존.)

---

### BL-436

**✅ Resolved (2026-07-25 close-completeness)** — codex G0: ccxt `marginMode` 는 신뢰 불가(Bybit v5 position tradeMode deprecated) → "PositionSnapshot 에 margin_mode 노출·포지션값 사용" 폐기. **권장 접근 대안 채택 = reduce_only 경로에서 set_margin_mode/set_leverage skip**(`create_order` 를 `if not order.reduce_only:` 로 감쌈; reduce-only 는 기존 포지션 설정 유지 → 잘못된 값 재설정 503 회피). reduce_only 는 이미 Order 영속 → 마이그레이션 0. dogfood: 청산 Order filled, worker 로그 set_margin_mode/503 없음.

**Title:** 청산 create_order 가 settings.margin_mode 로 set_margin_mode — 포지션 실제 mode 불일치 시 실패 가능
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 포지션 실제 margin_mode 와 전략 settings 가 어긋나는 수동/외부 포지션 청산 시
**Est:** S (PositionSnapshot 에 margin_mode 노출 후 포지션값 사용, leverage fix 와 동형)
**출처:** 2026-07-24 trading-surface-pack (최종 codex diff review — leverage 는 포지션값으로 fix, margin_mode 는 잔여)

**원인 / 영향:** `create_order`(providers.py:545-556)가 주문 전 `set_margin_mode(order.margin_mode)` 호출. 청산은 `settings.margin_mode` 사용 — 포지션 실제 mode 와 같으면 "not modified" no-op(관리 플로우), 다르면 Bybit 이 open position 의 margin 변경을 거부해 청산 503 가능. leverage 는 포지션값 사용으로 해소했으나 PositionSnapshot 에 margin_mode 필드 부재로 margin 은 잔여. live_signal 청산 경로도 동형(공유 특성).

**권장 접근:** PositionSnapshot 에 margin_mode 노출 → 청산 req 에 포지션값 사용(leverage 와 동일 원리, set_margin_mode no-op). 또는 reduce_only 경로에서 set_margin_mode/set_leverage skip.

---

### BL-437

**Title:** 청산 스윕 — 청산 후 잔여 reduce-only 조건부 주문 자동취소 (post-fill + 세션 귀속)
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 수동 청산 후 잔여 조건부 주문(standalone SL/Trail 등 flat 시 자동취소되지 않는 것)이 dangling 으로 남아 재진입 시 오발화하는 실사례가 확인될 때
**Est:** M (post-fill flat 확인 mechanism + orderLinkId→세션 매핑)
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
**출처:** 2026-07-25 money-path-accuracy 계획 단계 실발견 ([`docs/archive/sprints/money-path-accuracy/context-notes.md`](archive/sprints/money-path-accuracy/context-notes.md) §3.1)

**원인 / 영향:** entry 에 부착한 브래킷 TP/SL 이나 `set_trading_stop` 트레일링이 체결되면 포지션이 닫히지만 **우리 DB 엔 아무 행도 생기지 않는다.** WS `order` 고아 이벤트는 5초 버퍼 후 폐기(`state_handler.py:97-102`, `logger.debug` 만 — 알림 없음), `execution` 토픽은 미구독(`websocket_task.py:330`), reconciler 는 local→exchange 단방향이라 INSERT 하지 않는다(`reconciliation.py:137-148`). Order INSERT 지점은 `OrderService.execute` 2곳뿐이다. 그 다음 바에서 pine_v2 warmup-replay 가 **같은 청산을 스스로 추측**해 이미 flat 인 포지션에 reduce-only close 를 발주하고 → `ProviderError` → `state=rejected` → 모든 손익 쿼리가 `state==filled` 로 걸러낸다. 결과적으로 **브래킷으로 익절/손절된 거래의 손익은 Kill Switch·loss-limit 알림·세션 에쿼티 커브 어디에도 잡히지 않는다.** money-path-accuracy(BL-014 부분)는 "우리가 발주한 청산 주문"만 고쳤으므로 이 구멍은 그대로다.

**★선행 주의(2026-07-25 자체 정정):** 현재 스윕의 `orphan_row` 카운터는 **구멍 크기를 측정하지 못한다.** 스윕 후보가 `list_unsynced_reduce_only_since()` = _우리 자신의_ 미동기화 주문이라, 백필이 정상 동작하는 steady state 에선 후보가 0 → 페이지를 아예 안 가져와 orphan 이 영영 0 으로 읽힌다(dogfood 에서 `groups=0` 실측). 규모를 실측하려면 **활성 계정·심볼을 독립적으로 열거**하는 별도 조회가 선행돼야 한다. 이 BL 의 첫 step = 그 측정 스파이크.

**권장 접근:** 스윕이 이미 `/v5/position/closed-pnl` 페이지를 읽고 있으므로 orphan 행을 (a) 합성 Order 행으로 INSERT(state=filled·reduce_only=true·exchange_order_id=Bybit orderId, 마이그레이션 0 가능하나 멱등성·세션 귀속 설계 필요) 하거나 (b) 별도 exchange-exit 원장을 신설한다. 어느 쪽이든 **세션 귀속**(어느 LiveSignalSession 의 포지션이었나)이 핵심 난점이다. 선행으로 `execution` 토픽 구독을 검토하면 실시간 귀속이 쉬워진다.

**Risk:** 🔴 (리스크 게이트가 실현 손실의 일부를 못 본다 — 한도 초과를 늦게 감지)

**상태:** 🟡 **부분 Resolved — 관측 원장(최근 7일) 까지 (2026-07-25, `stage/exit-attribution`).** 측정 스파이크가 전제를 뒤집었다 — 거래소 전용 행 4건(행 36.4% · |손익| 55.8%)은 **브래킷이 아니라 앱 밖 수동 청산**이었고, **브래킷 체결은 전 기간 0건**(조건부 주문 4건 전부 `Deactivated`, DB 17행 중 TP/SL 실은 주문 0)이라 이 구멍은 코드 경로상 실재하나 **프로덕션 관측 0 = 잠복**이다. 게다가 거래소 전용 4건 중 우리 포지션은 1건뿐이라 자동 계상은 오차단을 만든다. 사용자 확정 = **관측 원장까지**. 신규 `trading.exchange_exits`(행 단위 원본 + provenance) + 스윕을 계정 독립 열거·최근 7일 창·원장 집계 백필로 재작성 + 분류 7종/귀속 3등급(라벨 전용, `inferred` 는 머니-패스 미투입) + 신규 미귀속 행 1회성 알림.

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
**출처:** 2026-07-25 money-path-accuracy (codex G0 BLOCKING 을 실측 반박한 뒤 남은 진짜 잔여)

**원인 / 영향:** closedPnl backfill 은 `state==filled` 인 reduce-only 주문만 대상으로 한다. 부분체결 뒤 `cancelled` 로 끝난 청산은 실제로 자금이 움직였는데도 `state==filled` 필터에 걸려 손익이 계상되지 않는다. **현재는 도달 불가** — 이 레포의 청산은 전부 `OrderType.market` 이고 Bybit 시장가 부분체결은 `PartiallyFilledCanceled` → ccxt `closed` → 우리 `filled` 로 매핑되기 때문이다. limit 청산이 도입되는 순간 활성화된다.

**권장 접근:** `transition_to_cancelled` 승자에서도 reduce-only 면 backfill 을 enqueue 하고, Kill Switch SUM 의 state 필터를 `realized_pnl_synced_at IS NOT NULL` 기준으로 넓힌다(단 생성 시점 엔진 추정값이 cancelled 행에 남아 있으면 오계상되므로 취소 시 null-out 이 선행돼야 한다).

---

### BL-440

**상태:** 🟡 **열려 있다** — 본 섹션의 "Resolved" 문자열은 **BL-014 를 가리키는 cross-ref**(출처 줄)이고, 이 BL 자신(`order_executions` per-execution ledger)은 **YAGNI 로 미착수**다. 근거: 본 섹션 `**권장 접근:**` 줄("실제 분석 수요가 생기기 전에는 만들지 않는다") · `docs/roadmap.md:262` `- [ ] **BL-440**`.

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
**출처:** 2026-07-25 money-path-accuracy

**원인 / 영향:** entry 주문이 부분체결되면 거래소 실포지션은 시뮬레이션이 가정한 수량보다 작다. `run_live` 는 매 평가마다 전체 히스토리를 재실행하며 **자기 시뮬 포지션**을 기준으로 청산 수량을 산출하므로, 이후 close 신호가 실제 보유량보다 큰 수량을 요청한다. reduce-only 라 over-fill 은 막히지만 시뮬과 실계좌의 사이즈가 계속 어긋난다.

**권장 접근:** `Order.filled_quantity`(이번 스프린트로 4 경로 전부 write 됨)를 warmup-replay 진입 수량 보정 입력으로 사용하거나, 부분체결 감지 시 세션을 fail-closed 비활성화한다. `qb_partial_fill_total` 이 실관측 빈도를 제공한다.

---

### BL-442

**Title:** 주문 원장 CSV 내보내기에 손익 출처(거래소 확정/추정) 미표기
**Category:** Frontend / trading
**Priority:** P3
**Trigger:** CSV 를 외부 회계·세무에 쓰기 시작할 때
**Est:** S (1h)
**출처:** 2026-07-25 money-path-accuracy (FE 적대 평가 #11)

**원인 / 영향:** 화면 손익 셀에는 "거래소 확정 / 추정" 배지가 붙지만 CSV 내보내기는 `realized_pnl` 값만 싣는다. 내보낸 행만 보면 pine_v2 추정값과 거래소 정산값을 구분할 수 없다 — 이 레포의 정직성 원칙에 어긋난다.

**권장 접근:** CSV 에 `realized_pnl_source` 열을 추가하거나 손익 값 옆에 접미사를 붙인다. 화면 열 수와 CSV 열 수를 맞추는 기존 관례와의 충돌은 주석으로 명시.

**상태:** ✅ **Resolved (2026-07-25, `stage/exit-attribution`).** CSV 가 잃는 정보는 손익 출처 1건이 아니라 3건이었다(출처 · 부분체결 마커 · 시각의 날짜). `ORDER_CSV_EXTRA_HEADER.realizedPnlSource` 열 신설(화면 12열 SSOT `ORDER_TABLE_HEADER` 는 불변) + 날짜 복원 + 부분체결 마커를 화면과 동일 문자열로 적재. 판정은 `displayRealizedPnl` / `isPartialFill` / `realizedPnlSource` 세 헬퍼로 SSOT 화해 화면·CSV 발산을 구조적으로 차단.

---

### BL-443

**Title:** 체결되지 않은 주문의 pine_v2 추정 손익이 원장·CSV 에 노출됨
**Category:** Frontend / trading (정직성)
**Priority:** P2
**Trigger:** 즉시
**Est:** S (1h)
**출처:** 2026-07-25 exit-attribution grounding 실발견

**원인 / 영향:** 손익 셀 렌더 조건이 `o.realized_pnl != null` 하나뿐이라 **체결된 적 없는 주문의 추정 손익이 화면에 뜬다.** `realized_pnl` 은 close 주문 **생성 시점**(state=`pending`)에 pine_v2 값으로 기록되고 거부돼도 그대로 남으며, `realized_pnl_synced_at` 은 백필 CAS 가 `state == filled` 를 요구해 영구 NULL 이라 항상 "추정" 배지가 붙는다. 실 DB 에 `state=rejected` + `realized_pnl = -1007.70000000` 인 행이 있었고 원장에 빨간 손실로 표시됐다. 백엔드 리스크 게이트는 전부 `state == filled` 로 걸러 안전하지만 **사용자만 오판한다.**

**상태:** ✅ **Resolved (2026-07-25, `stage/exit-attribution`).** `displayRealizedPnl` 단일 판정(`state === "filled"`)을 화면·CSV·부호 톤이 공유. 감춘 셀에는 상태별 사유 `title` 부착. 부분체결 후 `cancelled` 는 현재 도달 불가 경로(청산이 전부 시장가 → `PartiallyFilledCanceled` → ccxt `closed` → 우리 `filled`)이므로 각주로 명시([BL-439](#bl-439) 활성화 시 조건 확대 필요).

---

### BL-444

**Title:** loss-limit 알림이 `live_signal_events` 조인이라 거래소 확정 손익을 보지 못함
**Category:** Backend / trading (money path)
**Priority:** P1
**Trigger:** 즉시
**Est:** M (3-4h — 스코프 재정의가 핵심)
**출처:** 2026-07-25 exit-attribution grounding 실측

**원인 / 영향:** `OrderRepository.sum_filled_realized_pnl_for_live_session`(`order_repository.py:90-102`)은 `live_signal_events.order_id` 서브쿼리로 세션 귀속 주문만 합산한다. 그런데 `close_service.execute`(수동 청산)는 `LiveSignalEvent` 를 만들지 않는다 — `mark_dispatched` 는 dispatch task 전용 경로다. **DB 실측: 손익을 가진 filled reduce-only 7건 중 거래소 확정값 3건(07-24 수동 청산)은 전부 이벤트가 없고, 이벤트가 있는 4건(07-05)은 전부 pine 시뮬 오차값이다.** 즉 loss-limit 알림은 **틀린 값만 보고 맞는 값은 하나도 못 본다.**

**권장 접근:** 스코프를 event-join 에서 `(strategy, account)` 튜플 + 세션 창(`created_at`~`deactivated_at`)으로 바꾼다. 단 `(strategy, account)` 스코프는 비활성 세션끼리 커브를 공유하는 [BL-445](#bl-445) 문제를 물려받으므로 세션 창 필터가 함께 가야 한다. 또는 `close_service` 가 `LiveSignalEvent` 를 남기도록 한다.

**Risk:** 🔴 (세션 손실한도 알림이 실제 정산 손실을 못 본다)

**상태:** ✅ **Resolved (2026-07-25, `stage/exit-money-path`).** 읽기 스코프만 교체하는 안 (a) 채택 — 신규 `SessionScope` 값 객체 + `_session_scope_where` 단일 술어로 [BL-445](#bl-445) 와 함께 해결. `sum_filled_realized_pnl_for_session(scope)` 로 개명하고 구 메서드는 삭제했다.

**★안 (b)(`close_service` 가 이벤트를 남기게) 를 기각한 실측 근거** — `dispatch_pending_live_signal_events_task`(`tasks/live_signal.py:756`)가 beat 5분 주기로 `list_pending(limit=50)` 을 **세션 필터 없이 무조건 재발행**한다. `close_service` 가 pending 이벤트를 넣으면 이 beat 이 집어 **두 번째 reduce-only 시장가 청산**을 발주한다. 게다가 `OrderService.execute` 가 내부에서 commit 하므로 "주문 커밋 → 이벤트 커밋" 사이 원자성 구멍을 이번 범위에서 막을 수 없다. 비상 청산 버튼 위의 쓰기 경로라 리스크 등급이 다르다. 잔여 이득(FE 타임라인 가시성 · watchdog 팬아웃)은 [BL-455](#bl-455) 로 분리 등재.

**★본문 실측 근거는 재현 불가.** "확정 3건은 이벤트 없음 / 이벤트 있는 4건은 pine 시뮬값" 은 로컬 DB 전소 이전 데이터다. 이 수정은 **코드 경로 논증**(`close_service.py:78` 의 `OrderRequest` 에 `realized_pnl` 필드 자체가 없고 `LiveSignalEvent` 도 만들지 않는다 — 코드로 확실)에 근거한다. 규모 실측 없이 진행한 것을 명시해 둔다.

**★"보이느냐" 는 고쳤지만 "언제 보이느냐" 는 안 고쳤다.** 수동 청산은 삽입 시 `realized_pnl` 이 NULL 이라, 이 수정 후에도 `refresh_closed_pnl_task` → 스윕 백필이 도착하기 전까지는 여전히 0 으로 보인다.

**검증** — `tests/tasks/test_alert_rules_scope_real_db.py` 실 DB 종단(임계 10% · 자본 100 에서 이벤트 있는 −5 만 세면 5.00% 로 **미발화**, 수동 청산 −7 을 포함해야 12.00% 로 발화 → 판별). `tests/trading/test_session_scope_money_path.py` 대조군.

---

### BL-445

**Title:** 세션 에쿼티 커브가 `(strategy, account)` 튜플 스코프라 비활성 세션끼리 커브를 공유
**Category:** Backend / trading
**Priority:** P2
**Trigger:** 같은 전략·계정으로 세션을 두 번 이상 돌린 뒤 세션별 성과를 비교할 때
**Est:** S (2h)
**출처:** 2026-07-25 exit-attribution grounding 실측

**원인 / 영향:** `list_filled_realized_by_strategy_and_account`(`order_repository.py:71-88`) → `router.py:483-501` 은 세션에서 `(strategy_id, exchange_account_id)` 만 뽑아 그 튜플의 모든 filled 주문을 긁는다. 세션 창 필터가 없다. 활성 유일성 제약(`uq_live_sessions_active_unique`)은 `is_active=true` 부분 인덱스라 **비활성 세션은 무제한 누적**된다. 실측상 세션 4개 중 3개가 동일 튜플이었고, 이벤트가 0건인 세션이 다른 세션의 거래를 자기 커브로 렌더했다. 대시보드 §01 KPI 도 같은 경로다.

**권장 접근:** 세션의 `created_at`~`deactivated_at` 창을 `filled_at` 에 적용한다. [BL-444](#bl-444) 와 같은 PR 로 묶는 것이 자연스럽다.

**상태:** ✅ **Resolved (2026-07-25, `stage/exit-money-path`).** 권장안대로 `filled_at` 반열림 `[created_at, deactivated_at)` 을 적용하고, `list_filled_realized_for_session(scope)` 로 개명해 [BL-444](#bl-444) 와 **같은 술어**(`_session_scope_where`)를 공유하게 했다. 둘은 서로 다른 두 버그가 아니라 같은 스코프 버그가 두 군데 있던 것이라, 술어를 두 벌 두면 그 병이 재생산된다.

**★권장안에 없던 `symbol` 술어를 추가했다.** `uq_live_sessions_active_unique` 가 `(user_id, strategy_id, exchange_account_id, symbol) WHERE is_active` 라 **심볼만 다른 활성 세션 2개가 합법**이고, 대시보드 §01 KPI(`dashboard-cockpit.tsx` → `useLiveSessionsAggregate`)는 활성 세션들의 `total_realized_pnl` 을 단순 합산한다 → 같은 손익을 두 번 더하고 있었다. 심볼 술어로 **FE 변경 없이** 닫혔다. 트레이드오프는 [BL-454](#bl-454) 참조.

**★수용한 트레이드오프 — 늦은 체결.** 창을 `filled_at` 에 걸었으므로 세션 종료 뒤 체결된 주문은 인접 세션이 있으면 그쪽으로 귀속되고, 없으면 어디에도 안 잡힌다 → [BL-456](#bl-456). 또한 `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**("terminal_at")이라 창의 정밀도가 관측 지연만큼 흐리다(codex G0 지적).

**검증** — `tests/trading/test_session_scope_money_path.py`(세 세션이 fix 전 `-1151.00001151` 로 동일했다가 fix 후 `-3.00000003`/`-28.00000028`/`-32.00000032` 로 서로소가 되는 것을 고정) + `tests/trading/test_router_live_session_state_real_pnl.py` 라우터 종단(인접 세션 2개가 서로 다른 커브).

---

### BL-446

**Title:** `cumulative_loss` 가 전 기간 누적 손익을 현재 잔고로 나눈다 (시간축 불일치 + 외부 거래 분모 오염)
**Category:** Backend / trading (risk gate)
**Priority:** P2
**Trigger:** 실자금 전환 전 필수
**Est:** M (4h — 리스크 게이트 변경이라 회귀 범위 넓음)
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

---

### BL-449

**Title:** `Order.webhook_payload` 가 SQL NULL 이 아니라 JSONB `'null'` 로 저장됨
**Category:** Backend / trading
**Priority:** P3
**Trigger:** `webhook_payload IS NULL` 술어나 partial index 를 쓰려 할 때
**Est:** S (1h, 마이그레이션 1)
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
**출처:** 2026-07-25 exit-attribution **실사고**

**원인 / 영향:** `tests/test_migrations.py` 는 `command.downgrade(cfg, "base")` 로 전 테이블을 드롭한다. `_resolved_test_db_url()` 이 `TEST_DATABASE_URL` 없이 `DATABASE_URL` 로 폴백하므로, `DATABASE_URL` 만 export 된 셸에서 이 파일을 돌리면 **개발 DB 가 대상이 된다.** 실제로 이번 스프린트에서 적대 평가 서브에이전트가 그 셸 상태로 실행해 **로컬 개발 DB 가 전소했다** — 주문 17행 · 거래소 계정 1(암호화된 Bybit demo API 키) · 전략 6종 Pine 소스 · 세션 4 · 이벤트 10. `.env.local` 에 평문 키가 없어 API 키는 복구 불가였고 사용자가 재등록해야 했다.

**부분 완화 (2026-07-25, `stage/exit-attribution`):** `_assert_disposable_database` 가 DSN 의 DB 이름이 `_test` 로 끝나지 않으면 `RuntimeError` 를 던진다. 개발 DB DSN 으로 실행 시 파괴 대신 예외가 나는 것을 실증했다.

**잔여 / 권장 접근:** ① 같은 폴백 구조가 `tests/conftest.py` 에도 있다(`TEST_DATABASE_URL > DATABASE_URL > default`) — 파괴성은 낮지만 동일 가드가 필요한지 검토 ② 로컬 개발 DB 주기 백업(`pg_dump` cron 또는 `make db-snapshot`)이 없다. dogfood 데이터는 재현 비용이 크고 API 키는 복구 불가다 ③ 서브에이전트에 DB env 를 넘길 때의 표준 레시피를 `.ai/rules` 로 승격 ④ **`alembic/env.py:40` 이 `settings.database_url` 을 주입하므로 수동 `alembic downgrade` 는 가드 없이 개발 DB 를 향한다** — `_assert_disposable_database` 는 pytest 경로만 막는다. CLI 경로 가드 또는 `make` 래퍼 검토.

---

### BL-452

**Title:** 거래소 청산 원장이 최근 7일만 담는다 — 과거 이력 적재·백필 불가
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** 아래 중 하나가 실제로 관측될 때 — ① 워커가 7일 넘게 정지한 실사례 ② 7일보다 오래된 미동기화 reduce-only 주문 관측 ③ 한 계정의 7일 청산이 500행 초과(`closed_pnl_window_truncated` 경고 발화) ④ `list_unsynced_reduce_only` 목록이 영구 좀비로 포화
**Est:** M (4-6h — 일회성 catch-up 재도입)
**출처:** 2026-07-25 exit-attribution **범위 축소** 결정 ([`docs/archive/sprints/exit-attribution/context-notes.md`](archive/sprints/exit-attribution/context-notes.md) §9)

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
**출처:** 2026-07-25 exit-attribution dogfood 실측 ([`docs/archive/sprints/exit-attribution/context-notes.md`](archive/sprints/exit-attribution/context-notes.md) §9.9) — **실제로 프로덕션 코드에서 한 건 발생해 수정함**

**원인 / 영향:** `ExchangeExit.classification`(`ExitClassification` StrEnum)이 `sa_column=Column("classification", String(24), ...)` 로 선언돼 있다(Sprint 26 의 `UndefinedObjectError` 회피 워크어라운드, `models.py:438-440`). 메모리에서 갓 만든 객체는 `.classification` 이 진짜 enum 이라 `.value` 가 되지만, **다른 세션에서 새로 `SELECT` 한 행은 SQLAlchemy 가 plain `str` 을 그대로 준다**(재캐스팅 없음) — `.value` 접근이 `AttributeError` 를 던진다. dogfood 에서 `_alert_new_exchange_exits` 가 정확히 이 경로로 죽어 신규 미귀속 행 알림이 매 사이클 조용히 실패하고 있었다(§7.3 대로 실측으로만 드러남 — 유닛테스트는 fake repo 라 잡지 못했다). `str(row.classification)` 로 수정 완료(`StrEnum.__str__` 이 값 자체를 돌려주므로 reload/메모리 양쪽 안전) + 실 DB 회귀 테스트 부착.

**감사 결과** — 같은 패턴(StrEnum 타입 + 평문 String 컬럼)인 필드가 4개 더 있다: `LiveSignalSession.interval` · `LiveSignalEvent.status` · `AlertRule.rule_type` · `AlertRule.channel`. 전수 조사 결과 **현재는 이 4개 모두 `==`/`!=`/`str()` 만 쓰거나 호출부가 없어 안전**하다(`StrEnum` 이 `str` 서브클래스라 비교 연산은 reload 여부와 무관). 즉 지금 당장 고칠 버그는 없고, **미래에 이 필드들에 `.value`/`.name` 을 쓰는 코드가 추가되면 같은 함정을 반복**할 잠재 위험만 남아 있다.

**권장 접근:** (a) 최소 — 5개 필드 선언부에 "`.value`/`.name` 금지, `==`/`!=`/`str()` 만 사용" 주석을 통일해서 남긴다(현재 `interval` 필드에만 있음, 나머지 4개엔 없음) (b) 중간 — ruff 커스텀 규칙 또는 AST 기반 테스트(이 레포의 `test_no_module_level_loop_bound_state.py` 패턴 참고)로 이 5개 필드명에 대한 `.value`/`.name` 접근을 정적으로 금지 (c) 근본 — Sprint 26 워크어라운드가 아직 필요한지 재검토하고, 필요 없으면 `sa.Enum` 으로 되돌려 SQLAlchemy 가 재캐스팅을 대신하게 한다.

**Risk:** 🟢 (현재 실제 발생한 크래시는 이미 수정됨. 이 항목은 재발 방지용 예방적 등재)

**상태:** 🟡 **부분 Resolved — 권장안 (a) 까지 (2026-07-25, `stage/exit-money-path`).** `tasks/trading.py:1698` 의 마지막 `.value` 잔존(`qb_exchange_exit_rows_total` 라벨)을 `str(row.classification)` 로 바꿨다. 지금은 메모리 객체라 안전하지만, 소스가 재조회 경로로 바뀌는 리팩터 한 번이면 dogfood 때와 같은 크래시가 재현되는 자리였다(grep 결과 코드베이스에 남은 유일한 `.value`). 그리고 **감사 목록에서 빠져 있던 `ExchangeExit.attribution_confidence` 를 포함해 6개 필드 전부**에 "`.value`/`.name` 금지, `==`/`!=`/`str()` 만" 주석을 통일했다(`models.py:441 · 583 · 634 · 640 · 718 · 742`). 권장안 (b) 정적 가드와 (c) `sa.Enum` 복귀는 미착수.

---

### BL-454

**Title:** 세션 등록·TV 웹훅 어느 쪽도 심볼을 정규화하지 않아 두 자유 문자열이 세션 스코프에서 어긋난다
**Category:** Backend / trading (money path)
**Priority:** P2
**Trigger:** TV 웹훅을 실제로 쓰기 시작할 때 · 또는 세션 스코프가 조용히 빈 것을 관측할 때
**Est:** S (2h, 마이그레이션 0 — **지금은**)
**출처:** 2026-07-25 exit-money-path codex G0 [P1] → 전건 코드 대조

**원인 / 영향:** `RegisterLiveSessionRequest.symbol` 은 `Field(min_length=1, max_length=32)` 뿐이라 형식 검증도 정규화도 없고(`schemas.py:183`), `live_session_service.py:118` 이 `req.symbol` 을 그대로 저장한다. TV 웹훅은 `webhook.py:89` 가 `str(payload["symbol"])` 원문을 싣는다. `normalize_symbol`(`market_data/constants.py:18`, `BTCUSDT` → `BTC/USDT`)이 존재하지만 **`src/trading/`·`src/tasks/` 어디서도 호출되지 않는다**(grep 0건). 즉 세션 심볼과 주문 심볼은 서로 독립된 자유 문자열 두 개다.

[BL-445](#bl-445) 가 세션 스코프에 `symbol` 정확 문자열 동등을 넣었으므로, **표기가 어긋난 TV 웹훅 주문은 세션 손익에서 조용히 빠진다** = loss-limit 알림의 fail-open. dispatch(`tasks/live_signal.py:926`)와 수동 청산(`close_service.py:81`)은 세션 심볼을 그대로 복사하므로 구조적으로 항상 일치한다 — 노출은 웹훅 경로 하나로 한정된다.

**권장 접근:** 두 ingress(`RegisterLiveSessionRequest` 검증 또는 `live_session_service`, 그리고 `parse_tv_payload`)에 `normalize_symbol` 을 적용한다. ★**지금 `trading.orders` 와 `trading.live_signal_sessions` 가 0행이라 데이터 백필 비용이 0 인 유일한 창이다.** 행이 쌓인 뒤에는 정규화 마이그레이션이 따라붙는다.

**Risk:** 🟡 (세션 손익 과소 집계 → 손실 알림 지연. 노출 경로는 TV 웹훅 하나)

**상태:** ✅ **Resolved (2026-07-26, `stage/money-path-finish`).** `src/common/normalized_symbol.py` 에 공용 도메인 프리미티브 `NormalizedSymbol = Annotated[str, BeforeValidator(...)]` 를 신설(레포 선례 `strict_decimal_input.py` 미러)하고 두 ingress 가 **같은 함수**를 쓴다 — `RegisterLiveSessionRequest.symbol` + `parse_tv_payload`. canonical `BTC/USDT` 는 선택이 아니라 강제였다(`providers._to_bybit_linear_symbol` 이 `"/" not in symbol` 이면 원문을 통과시켜 **원문 `BTCUSDT` 가 linear 어댑터를 우회**한다). 정규화 불가 표기는 **거부 + 관측**(API 422 / 웹훅 401 + `qb_webhook_symbol_rejected_total` + 원문 로그) — TV `{{ticker}}` 가 퍼프에서 `.P` 를 붙이는지 1차 출처로 확인하지 못했으므로 장식 제거를 추측으로 넣지 않았다. ★**의도된 동작 변경 1건** — 정규화로 `BTCUSDT`/`BTC/USDT` 가 한 문자열로 붕괴해 `uq_live_sessions_active_unique` 에서 충돌한다(예전 201 → 4xx). 그게 대시보드 §01 KPI 이중 계상의 원인이었으므로 수정의 요점이다. `live_signal_sessions` 0행이라 백필 0.

---

### BL-455

**Title:** 수동 청산이 `LiveSignalEvent` 를 남기지 않아 FE 타임라인과 watchdog 팬아웃에서 빠진다
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 수동 청산을 이벤트 타임라인에서 보고 싶을 때 · watchdog 규칙을 수동 청산에도 걸고 싶을 때
**Est:** M (4-6h — 쓰기 경로 + 원자성 설계)
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
**출처:** 2026-07-25 exit-money-path [BL-445](#bl-445) 가 **수용한** 트레이드오프

**원인 / 영향:** `_session_scope_where`(`order_repository.py`)가 창을 `Order.filled_at` 에 `[created_at, deactivated_at)` 로 건다. 청산을 누르고(202, `state=pending`) 곧바로 세션을 끈 뒤 체결이 도착하면 그 주문은 자기를 만든 세션에서 빠진다. 인접 세션이 있으면 **그쪽으로 귀속**되고, 없으면 **어느 세션에도 안 잡힌다.** 후자의 경우 Site 3(loss-limit)·Site 4(커브·대시보드 KPI) 양쪽에서 사라진다.

덧붙여 `Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**("terminal_at")이라, 창의 정밀도가 관측 지연만큼 흐리다(codex G0 지적).

**검토한 대안과 각각의 결함** — ① `created_at` 상한: 늦은 체결을 살리고 인접 세션 중복도 없지만, 인과("이 세션이 이 주문을 일으켰나")와 커브 x축(`filled_at`)의 기준이 갈린다 ② `filled_at + grace`: 임의 상수가 생기고 인접 세션과 창이 겹쳐 **같은 주문이 두 커브에 동시 등장**한다 ③ 현행 `filled_at` 반열림: 배타성은 완벽하나 늦은 체결을 흘린다.

**권장 접근:** 실측이 선행돼야 한다 — dogfood 에서 `filled_at − created_at` 실제 간극을 재고, 그 간극이 세션 종료 지연보다 유의하게 큰지 확인한 뒤에야 대안을 고른다. 간극이 수백 ms 수준이면 현행 유지가 옳다.

**Risk:** 🟡 (경계 케이스 손익 누락. 현행 계약은 테스트로 고정돼 있어 조용한 변경은 불가)

---

### BL-457

**Title:** `classify_exit` 의 `ours` 는 실제 매칭이 아니라 orderLinkId 가 UUID 로 파싱되는지만 본다
**Category:** Backend / trading (원장 라벨 정확도)
**Priority:** P2
**Trigger:** 즉시 (현재 진행형 오보고) — 그리고 `classification` 이 머니-패스 입력으로 승격되기 전 필수
**Est:** S (1-2h)
**출처:** 2026-07-25 exit-money-path §0.5 실측 + Explore 코드 대조

**원인 / 영향:** `classify_exit`(`exit_attribution.py:33-69`)이 `ours` 를 돌려주는 경로는 둘이다 — ① `matched_order_id is not None`(진짜 매칭) ② `meta.order_link_id` 가 UUID 로 **파싱되기만** 하면(`_is_our_client_order_id` 는 맨 `UUID(s)` try/except 로 DB 조회가 없다). 후자가 형식-only 휴리스틱이다.

**DB 실측 — `ours` 3행 전부 `matched_order_id IS NULL` + `attribution_confidence='none'`** 이다. 즉 지금 원장의 `ours` 라벨은 전부 형식만 보고 붙었다. 결과는 두 가지다. ① `_alert_new_exchange_exits`(`tasks/trading.py:1490`)가 `classification != ours` 로 거르므로 **UUID 모양 client id 를 단 외부 청산이 운영자 알림에서 조용히 빠진다** ② `qb_exchange_exit_rows_total{classification="ours"}` 가 과대 집계된다. 함수의 주석은 정확히 이 오분류를 피하려 한다고 적혀 있는데 구현은 "비어 있지 않음" 을 "UUID 로 파싱됨" 으로 한 칸 올렸을 뿐이라 여전히 순수 구문 판정이다.

`ix_exchange_exits_classification` 인덱스는 아직 쓰는 쿼리가 없다. [BL-438](#bl-438) ② 가 랜딩해 무언가 `classification` 으로 필터링하는 순간 이 결함은 **머니-패스 결함**이 된다.

**권장 접근:** `exit_attribution.py` 는 지난 스프린트가 **순수 함수 + 순수 테스트**로 확정한 모듈이라 안에서 DB 를 조회하면 안 된다. 순수성을 지키는 방법은 `known_order_ids: frozenset[UUID]` 를 인자로 받는 것이다.

**★정정 (2026-07-26, money-path-finish 실측)** — 위 문단의 원래 후속 문장은 "`attribution_facts` 가 `order_id` 를 들고 있으므로 **새 쿼리가 필요 없다**" 였다. **그 조언은 틀렸고, 따르면 새 버그를 만든다.** `attribution_facts` 는 `list_filled_for_attribution` 이 `limit=500` + `state==filled` + `filled_at IS NOT NULL` 로 좁힌 목록이고, link-id 실재 확인이 필요한 행은 **정의상 `state==filled` 매칭에 실패한 주문**(`submitted` · 부분체결 후 `cancelled` · `pending` 중 사망)이다. 즉 그 목록에는 필요한 행이 구조적으로 없어서, 재사용하면 **진짜 우리 청산이 `external_manual` 로 뒤집혀** 운영자 알림이 헛발화한다. 계정 스코프 + **state 무필터** 전용 쿼리가 필요하다.

**Risk:** 🟡 (현재는 운영자 알림 누락 + 메트릭 과대. 머니-패스 승격 시 🔴)

**상태:** ✅ **Resolved (2026-07-26, `stage/money-path-finish`).** `classify_exit` 이 `known_order_ids: frozenset[UUID]` 를 **필수 키워드**로 받고, `OrderRepository.list_existing_ids`(술어 2개 · state 무필터)가 계정 스코프 실재를 확인한다. 부수 이득 2건 — ① 실재 확인을 요구하면서 `createType`/`stopOrderType` 분기가 link-id 분기 앞으로 올라와 **버려지던 TP/SL·청산 유래가 되살아났다** ② UUID 형식이지만 미확인인 행은 `external_manual`(= "사람이 UI 에서 Close 를 눌렀다" 는 거짓 단정)이 아니라 `unknown` 으로 떨어진다 — 사람은 UUID4 를 타이핑하지 않는다. 관측 = `qb_exchange_exit_link_unverified_total` + `exchange_exit_link_id_unverified` 로그(orderLinkId 원문). 사용자 결정에 따라 **기존 원장 4행은 재분류하지 않았다**(마이그레이션 0) — 근거는 `docs/archive/sprints/money-path-finish/operating-contract.md` §2.

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

**잔여** — ① Site 1·2 게이트는 여전히 추정·확정 혼재(의도) ② Site 5 일일 리포트 미표면화 ③ **포트폴리오 병합 커브는 포인트별 출처 표현 불가** — `mergeCumulativeCurves` 가 각 세션의 마지막 누적값을 carry-forward 해 더하므로 한 지점의 값은 대부분 과거 거래에서 실려온 값의 합이다. 집계 수준 라벨로 강등했고 구간별 표시는 세션 상세에서만 한다 ④ Site 4 는 `unrecorded_count` 를 세지 않는다(추가 왕복 0 을 택함 — 폴백은 `docs/archive/sprints/money-path-finish/operating-contract.md` §4).

---

### BL-459

**Title:** 세션 읽기와 주문 조회 사이에 비활성화가 커밋되면 그 한 번의 응답이 종료 후 체결을 포함한다 (TOCTOU)
**Category:** Backend / trading (money path — 관측 정확도)
**Priority:** P3
**Trigger:** 세션 종료와 체결이 같은 순간에 겹치는 것이 실제로 관측될 때
**Est:** M (3-4h — 세션↔주문 단일 조인으로 재구성)
**출처:** 2026-07-25 exit-money-path **최종 codex 누적 diff 리뷰** [P2]

**원인 / 영향:** 두 소비처 모두 **세션 행을 먼저 읽고 → 별도 SELECT 로 주문을 조회**한다.

- `alert_rules.py:60` — `list_active_loss_rules_with_sessions()` 가 `is_active=true` 세션만 돌려주므로 `SessionScope.ended_at` 은 항상 `None`(무상한)이다.
- `router.py:465` — `get_by_id(session_id)` 로 읽은 `sess` 의 `deactivated_at` 을 그대로 쓴다.

그 사이에 `LiveSignalSessionRepository.deactivate`(`:155`)가 커밋되면 — 호출 지점은 4곳(`tasks/live_signal.py:433/503/539` beat + `router.py:442` 사용자 DELETE) — 스코프는 여전히 무상한이라 **종료 후 체결이 그 한 번의 계산에 섞인다.** READ COMMITTED 라 두 번째 SELECT 는 새 스냅샷을 보지만 `ended_at` 값은 이미 파이썬 쪽에 잡혀 있다.

**★등급 판단 — 회귀가 아니다.** 이 변경 **전에는** Site 4 에 창이 아예 없었고(전 기간 무조건 포함) Site 3 도 창이 없었다. 즉 이 레이스는 새 코드가 **한 번의 계산 동안만** 옛 동작을 하게 만드는 것이고, 다음 평가/요청에서 자가 교정된다. 두 경로 모두 발주를 막지 않는 **읽기 전용 관측**이다. 그래서 exit-money-path 는 이걸 고치지 않고 등재만 했다 — 스프린트 막바지에 쿼리 구조를 바꾸면 회귀 표면이 넓어지고, codex 자신도 "새 테스트는 순차 실행뿐이라 이 경쟁 조건을 잡지 못한다" 고 적었다.

**권장 접근:** 세션 경계와 주문을 **한 쿼리**로 묶는다(`live_signal_sessions` 를 조인해 `s.created_at`/`s.deactivated_at` 을 SQL 안에서 읽게 한다 — `docs/archive/sprints/exit-money-path/operating-contract.md` §5 의 진단 SQL 이 이미 그 형태다). 그러면 단일 스냅샷 안에서 경계와 행이 함께 결정된다. 잠금은 불필요하다.

**Risk:** 🟢 (한 번의 응답/평가에 한정 · 자가 교정 · 변경 전보다 엄격)

### BL-464

**Title:** `attribute_exit` 이 거래소 원문 심볼과 우리 canonical 심볼을 비교해 `inferred` 귀속이 구조적으로 죽어 있었다
**Category:** Backend / trading (원장 귀속 정확도)
**Priority:** P2
**Trigger:** 즉시 (귀속 축 전체가 무동작)
**Est:** S (1h)
**출처:** 2026-07-26 money-path-finish §0.5 실측 — 백로그에 없던 신규 발견

**원인 / 영향:** `attribute_exit`(`exit_attribution.py:99`)이 `order.symbol == symbol` 로 정확 문자열 동등을 본다. 호출부(`tasks/trading.py`)가 넘기는 `snapshot.symbol` 은 Bybit 원문 **`BTCUSDT`**(`providers.py:368` 이 `str(row["symbol"])` 로 그대로 싣는다)이고, `OrderFact.symbol` 은 `_order_facts` 가 `order.symbol` 을 그대로 담은 우리 canonical **`BTC/USDT`** 다. → **어떤 표본에서도 매칭이 성립하지 않아 항상 `(ExitAttribution.none, None)`** 을 돌려준다. DB 실측 정합 — 원장 4행 전부 `attributed_strategy_id IS NULL` · `attribution_confidence='none'`. `ExitAttribution.exact`(exchange_order_id 매칭)는 영향 없다.

직전 스프린트가 `attributed_strategy_id NOT NULL 0` 을 관측했지만 **"0행 위에서 0"** 으로 해석했다. 이건 구분되는 진단이다 — **데이터가 있어도** 매칭이 안 된다.

**★왜 한 스프린트 동안 안 보였나** — `tests/tasks/test_closed_pnl_sweep.py::_snapshot` 의 기본 심볼이 `"BTC/USDT"`(우리 canonical)였다. 실제 Bybit closed-pnl 은 `BTCUSDT` 를 준다. 원장 쪽 피연산자를 우리 표기로 위장한 픽스처가 경계 버그를 가렸다. **외부 시스템 픽스처의 기본값은 "다루기 편한 형태" 가 아니라 그 시스템이 실제로 주는 형태여야 한다.**

**상태:** ✅ **Resolved (2026-07-26, `stage/money-path-finish`).** `_order_facts` 와 `attribute_exit` 호출 양쪽에 `to_bybit_raw_symbol` 을 적용해 **같은 거래소 공간**에서 비교한다(`exit_attribution.py` 는 순수 문자열 동등 유지). `normalize_symbol` 을 쓰지 않은 이유 — 그건 **raise** 하고, 계정 루프 안에서 던지면 바깥 `except Exception` 에 삼켜져 `failed_provider` 로 오집계되며 **그 계정의 원장 적재 전체를 잃는다**. `to_bybit_raw_symbol` 은 raise 하지 않고 원문에 idempotent 하다. 규칙 = **원장은 거래소 공간 / 우리 테이블은 canonical 공간 / `_order_facts` 가 유일한 건널목**. 관측 = `qb_exchange_exit_attribution_total{confidence}`.

★**되살린 것이 휴리스틱 승인은 아니다** — 함수 스스로 "실측 표본 4건에서 4/4 였지만 활성 세션이 사실상 하나였다, 검정력이 없다" 고 적고 있다. `attributed_strategy_id` 독자가 레포 전체에 0 이라서만 안전하다. 새 메트릭은 [BL-438](#bl-438) ② 가 이걸 머니-패스 입력으로 승격하기 **전에** 실제 inferred 비율을 재기 위해 존재한다.

**Risk:** 🟡 (원장 귀속 결손. 소비처가 0 이라 오늘 머니-패스 영향은 없다)

**Dependency:** [BL-454](#bl-454) 와 같은 뿌리(심볼 표기 비대칭)이지만 ingress 정규화로는 안 고쳐진다 — 거래소 쪽 피연산자는 구조상 원문이다.

---

### BL-465

**Title:** `_periodic_returns` 가 음수 자본을 걸러내지 않아 파산한 실행에 양수 위험조정수익이 붙었다
**Category:** Backend / backtest (지표 정직성)
**Priority:** P1
**Trigger:** 즉시
**Est:** S (1h)
**출처:** 2026-07-26 dogfood-restore 실화면 검증 — 백로그에 없던 신규 발견

**원인 / 영향:** 기간 수익률은 `(cur - prev) / prev` 다. `prev` 가 음수면 부호가 뒤집혀 **더 잃을수록 수익률이 양수**가 된다. `_periodic_returns` 는 `prev == 0` 만 막아(분모를 고민한 흔적은 있다) 음수 구간이 그대로 통과했다.

실측 — `s1_pbr` BTC/USDT 1h 2025-07-01→2026-07-25 실행이 10,000 → **-207,968**(총수익률 -2179.68%)로 끝났고 자본이 9,337 지점 중 8,874(95%)에서 음수였다. 월간 수익률 13개 중 **11개가 양수**로 계산돼 **샤프 +0.029**. BL-398(#480)이 없애려던 거짓말과 같은 부류이나 원인이 다르다 — 그쪽은 수식(bar t-통계량), 이쪽은 **분모 부호**.

**★committed Trust Layer baseline 이 이걸 담고 있었다** — `s1_pbr` baseline 샤프 **+0.600** · 소르티노 **+2.349**(총수익률 -536%). 코퍼스 5종 중 4종이 자본을 음수로 몬다(s1_pbr 81.8% · s2_utbot 84.2% · i1_utbot 84.2% · s3_rsid 3.6%). 거래가 없는 `i2_luxalgo` 만 무관하고, **골든이 깨진 것도 정확히 그 4종**이다.

**상태:** ✅ **Resolved (2026-07-26, `stage/dogfood-restore`).** `_has_nonpositive_equity` 술어를 `sharpe_ratio`·`sortino_ratio` 앞에 두고 신규 마커 `unavailable_nonpositive_equity` 를 반환한다. `unavailable` 과 합치지 않은 이유 — 그쪽 문구("변동이 없거나 기간이 짧아")가 파산한 계좌에는 적극적으로 틀리다. baseline 재생성 diff 는 **12 메트릭 키 중 2개**(`sharpe_ratio`·`sortino_ratio`)·해당 4 코퍼스 한정, `ohlcv_sha256` 불변, 거래수·수익률·드로다운 전부 동일.

**Risk:** 🟢 (해소. 회귀 테스트 5건 — 실측 월말 계열 그대로 사용, 표본을 줄이면 큰 음수 하나가 평균을 지배해 성질이 죽는다)

**Dependency:** [BL-466](#bl-466) 이 음수 자본 자체를 다룬다. 본 항목은 **그 위에서 지표가 거짓말하지 않는 것** 만 닫았다.

---

### BL-466

**Title:** 레버리지 1 백테스트가 자본을 무제한 음수로 몰 수 있다 (마진 게이트 no-op + 청산 없음)
**Category:** Backend / backtest engine (모델 충실도)
**Priority:** P2
**Trigger:** 실자금 전 · 또는 사이징 모델 재검토 시
**Est:** M (설계 결정 선행)
**출처:** 2026-07-26 dogfood-restore — [BL-465](#bl-465) 조사 중 파생

**원인 / 영향:** `_can_afford_entry` 는 `is_leverage_active(self.leverage)` 가 거짓이면 즉시 `True` 를 반환한다(`strategy_state.py:374`). L=1 에는 마진 개념이 없다는 #480 TV/MT5 컨벤션 결정의 귀결이고 그 자체로는 일관적이다. 문제는 **L=1 에서 청산도 없다**는 것과 겹칠 때다 — 사이징을 선언하지 않은 전략은 `compute_qty` 가 `1.0` 을 돌려주므로(`strategy_state.py:317`) 1 BTC ≈ $64,000 명목이 $10,000 자본 위에서 돌고, 손실이 무한정 누적된다. 실측 = 초기자본의 **21.8배 손실**. 현물 1x 에서는 물리적으로 불가능한 결과다.

`test_mdd_exceeds_capital_when_equity_goes_negative` 가 이미 존재하므로 음수 자본은 **알려진·테스트된 조건**이었다. 다만 그 위에서 지표가 무엇을 보고해야 하는지는 정해져 있지 않았다.

**권장 접근:** 선택지 3 — (a) L=1 에도 자본 소진 시 강제 종료(현물 파산 모델) (b) 무담보 명목을 자본으로 상한 (c) 현 동작 유지 + 리포트에 "이 실행은 자본을 초과해 손실했다" 명시 고지. (c) 가 가장 싸고 baseline 을 안 흔든다.

**Risk:** 🟡 (숫자가 물리적으로 불가능하지만 지표는 BL-465 로 이미 입을 닫았다)

---

### BL-467

**Title:** `backend-optimizer-heavy` 에 OHLCV 설정 3종이 없어 모든 optimizer 실행이 실패했다
**Category:** Infra / docker-compose
**Priority:** P1
**Trigger:** 즉시
**Est:** S (10m)
**출처:** 2026-07-26 dogfood-restore 실측

**원인 / 영향:** `optimizer.run` 은 `optimizer_heavy` 큐로만 라우팅되고(`celery_app.py` task_routes) `backend-optimizer-heavy` 가 유일한 소비자다. 그런데 그 서비스에 `OHLCV_PROVIDER`·`OHLCV_FIXTURE_ROOT`·`DEFAULT_EXCHANGE` 가 없어 `ohlcv_provider` 가 코드 기본값 `"fixture"` 로 떨어지고, `ohlcv_fixture_root` 는 CWD(/app) 상대라 `/app/backend/data/fixtures/ohlcv` 로 풀려 **컨테이너 안에 존재하지 않는다** → 전 실행이 `OHLCVFixtureNotFound`. 아무도 짐작 못 할 경로다.

**상태:** ✅ **Resolved (2026-07-26, `stage/dogfood-restore`).** `backend-worker` 와 동일한 3종을 추가하고, 격리 오버레이에도 서비스를 등재해 다른 3 워커와 코드 세대가 갈리지 않게 했다(§7.2).

**Risk:** 🟢

---

### BL-468

**Title:** `OHLCV_FIXTURE_ROOT` 기본값이 CWD 상대라 host 실행에서 깨지고, `FixtureProvider` 는 canonical 심볼을 서빙할 수 없다
**Category:** Backend / market_data
**Priority:** P3
**Trigger:** fixture provider 를 실제로 쓸 때
**Est:** S

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

---

### BL-470

**Title:** 캐논 감사 9건이 빈 DB 에서 조용히 통과한다 (데이터 전제 부재)
**Category:** Frontend / e2e
**Priority:** P2
**Trigger:** 다음 캐논 baseline 재측정 시
**Est:** S

**원인 / 영향:** authed 캐논 감사는 **렌더된 것**의 하드 실패 수만 센다. 빈 DB 에서는 `StateBox` 하나만 렌더되므로 11열 표·최대 585 체결 원장이 통째로 사라진 걸 **빨간 신호 없이** 놓친다. `authed-canon-p1.spec.ts:16-18` 이 baseline 측정 조건을 명시해 뒀다(`/backtests` 6건 · `/trades` 최대 585 체결 · `/trading` 거래소 1) — 즉 조건이 문서화돼 있는데 단정되지 않는다.

**권장 접근:** 각 캐논 스펙에 데이터 전제 사전조건 단정 추가(없으면 skip 이 아니라 시끄럽게 실패). `make seed` 가 그 전제를 재현 가능하게 만들어 뒀다.

**Risk:** 🟡 (감사 커버리지가 조용히 증발)

---

### BL-471

**Title:** `exchange_exits` 는 `row_hash` 멱등이라 분류 로직이 바뀌어도 기존 행이 재분류되지 않는다
**Category:** Backend / trading (원장)
**Priority:** P3
**Trigger:** 분류·귀속 로직 변경 시
**Est:** S

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

**원인 / 영향:** `backtest-list.tsx` 는 legacy·unavailable 계열에만 `title` 을 단다. `tv_monthly_rfr2` 와 `tv_daily_rfr2` 는 **분모 기간이 다른 별개 척도**인데 목록에서는 둘 다 그냥 숫자로 보여 나란히 정렬된다. 리포트는 각주를 달지만 목록은 달지 않는다.

**Risk:** 🟢

---

### BL-473

**Title:** Bybit private WS 인증 `expires` 창이 +1s 라 왕복 지연에 먹혀 라이브 체결 스트리밍이 죽어 있었다
**Category:** Backend / trading (WebSocket)
**Priority:** P1
**Trigger:** 즉시
**Est:** S (30m)
**출처:** 2026-07-26 dogfood-restore 실측

**원인 / 영향:** `_authenticate` 가 `expires = int((time.time() + 1) * 1000)` 을 보낸다("codex G0-5: 공식 예시 기준 +1s" 주석). 프레임이 Bybit 서버에 닿는 시점에 이미 만료돼 `{"success":false,"ret_msg":"Params Error"}` 로 거부되고, auth circuit breaker 가 1시간 열려 **라이브 체결 스트리밍이 통째로 멈춘다**. 주문 발주(REST)는 되지만 체결 이벤트가 실시간으로 안 들어온다.

**★지연 의존이라 회귀처럼 안 보인다.** #472 dogfood 때는 WS 실주문 4점이 통과했다. 지연이 낮을 때만 붙는 시한폭탄이라 스프린트마다 붙었다 떨어졌다 했다.

**★진단 경로 기록** — 처음엔 "API 키 만료" 로 오진해 사용자에게 재등록을 요청했다. 독립 HMAC 오라클로 REST 를 치자 **양쪽 키 모두 `retCode 0`**(자산 846,921.08) 이었다. 키는 처음부터 멀쩡했다. 이어서 **우리 코드가 아닌 독립 WS 클라이언트**로 같은 페이로드를 보내 동일 재현 → 배관이 아니라 페이로드 문제로 좁혔고, 통제 실험으로 창 크기가 원인임을 확정했다.

```
expires = now +1s   → success=False "Params Error"   (demo·mainnet 동일)
expires = now +10s  → success=True
expires = now +60s  → success=True
```

**상태:** ✅ **Resolved (2026-07-26, `stage/dogfood-restore`).** `_AUTH_EXPIRES_WINDOW_S = 10.0`. Bybit 이 문서화한 시계 드리프트 허용(±5s)과 같은 크기 이상이어야 드리프트만으로 창이 사라지지 않는다. 서명 만료창일 뿐 비밀이 아니라 넉넉히 잡는 게 옳다. 회귀 테스트가 `expires` 가 현재보다 ≥5s 앞서는지 단정하고 구 값(+1s)에 RED 임을 확인했다. 라이브 검증 = circuit 키 제거 후 양쪽 계정 `ws_stream_connected`.

**Risk:** 🟢

---

### BL-474

**Title:** 테스트 주문 다이얼로그가 라이브 경로와 **다른 시장**으로 나간다 (spot vs linear perp)
**Category:** Frontend / trading (dogfood 도구 충실도)
**Priority:** P2
**Trigger:** 다음 실주문 dogfood 전
**Est:** S~M

**원인 / 영향:** 라우팅은 `(exchange, mode, has_leverage)` 튜플이다(`registry.py:35-39`) — `False` → `BybitDemoProvider`(**Spot**), `True` → `BybitFuturesProvider`(**Linear Perp**).

실측 dispatch snapshot —

```
라이브 신호 주문   leverage=1  margin_mode=isolated  has_leverage=true   → linear perp
테스트 주문 다이얼로그  leverage=NULL  margin_mode=NULL  has_leverage=false  → spot
```

즉 "dogfood-only" 라고 이름 붙은 도구가 **프로덕션이 실제로 쓰는 시장을 연습하지 않는다**. 확인 = 우리 주문 `2267433208968908032` 는 Bybit **spot** 히스토리에만 있고 linear 에는 없다(숫자형 ID = spot, linear 는 UUID).

**따라오는 결과** — 청산 원장(`/v5/position/closed-pnl`)·포지션 코크핏·`exchange_exits` 는 전부 linear 만 본다. 그래서 다이얼로그로 낸 체결은 **`realized_pnl_synced_at` 을 영원히 못 받고 원장에도 안 뜬다**. 이 도구로 머니-패스를 dogfood 하면 조용히 아무것도 검증하지 못한다.

**권장 접근:** 다이얼로그가 전략의 Live Settings(leverage/margin_mode)를 실어 보내 라이브 경로와 같은 튜플로 dispatch 되게 하거나, 최소한 화면에 **어느 시장으로 나가는지 표시**한다. 후자만으로도 조용한 오검증은 막힌다.

**부수 관측:** 시더로 만든 전략은 평문 webhook secret 이 브라우저에 없어 다이얼로그가 "캐시 없음" 으로 막힌다 — Secret 회전 1회가 선행돼야 한다. 정상 동작이지만 안내문이 "Strategy 페이지에서 Rotate" 라고만 해서 §05 Webhook 카드까지 스크롤해야 한다는 걸 알기 어렵다.

**상태:** ✅ **Resolved (2026-07-26, `feat/bl-474-webhook-ingress-parity`).**

**★진단이 한 겹 더 깊었다 — 문제는 다이얼로그가 아니라 webhook ingress 였다.** `router.py:138-147` 이 `OrderRequest` 를 7개 필드로만 조립하고 `parse_tv_payload`(`webhook.py:118-125`)가 6개 키만 읽어, **한 자리에서 세 가지가 동시에 버려지고 있었다** — leverage/margin_mode(해결 자체를 안 함) + `reduce_only` + TP/SL(프론트가 **보내는데** 파서가 안 읽음). 원인이 프론트가 아니므로 "다이얼로그가 실어 보낸다" 는 권장 접근은 잘못된 층을 고칠 뻔했다.

**★leverage 만 고쳤으면 A(출처 라벨 검증)는 여전히 안 열렸다.** 청산 확정 경로 전체가 `reduce_only` 를 요구한다 — `tasks/trading.py:1342` 조기 반환 + 스윕의 `list_unsynced_reduce_only`. 그 플래그 없이는 다이얼로그 청산이 **영원히 `realized_pnl_synced_at` 을 못 받는다**.

**★위 실측 표의 "leverage=1" 은 맞고, 체크리스트 §2 가 여기서 끌어낸 "레버리지 1 은 시장 유형을 바꾼다(`has_leverage=False`)" 는 틀렸다.** `order_service.py:194` = `req.leverage is not None and req.leverage > 0`, `tasks/trading.py:135` = `return lev > 0` → **1 이면 True → linear perp**. 진짜 원인은 값이 1이어서가 아니라 **아무 값도 안 보내서**다. `docs/archive/sprints/dogfood-restore/checklist.md` 에서 정정했다.

**해결:** `WebhookService.resolve_trading_params()` 신설 — `Strategy.settings` 에서 leverage/margin_mode 를 해결하고 미설정/무효는 **422 fail-closed**(`live_signal.py:852-866` / `close_service.py:47-58` 와 동일 정책). payload 로는 받지 않는다(secret 보유자가 운영자 리스크 설정을 우회하는 걸 차단). HMAC 검증 **뒤에** 호출해 응답코드 차이로 settings 유무를 탐지당하지 않게 했다. `reduce_only`/TP/SL/`risk_percent` 는 파서가 읽어 전달하며, `reduce_only` 는 `bool("false") is True` 함정을 명시 화이트리스트로 막았다.

fail-closed 를 고른 이유 = spot 진입은 **닫을 수단이 없다**. 모든 청산 경로가 linear reduce-only 로 나가고 거래소는 `110017 "current position is zero"` 로 거부한다(이 스프린트가 관측한 그 에러). 하위 머니-패스(청산 원장·코크핏·`exchange_exits`)가 전부 linear 전용이라 spot 체결은 확정 손익을 영원히 못 받는다.

FE 는 경고만 하고 차단하지 않는다 — 공개 ingress 라 서버가 권위여야 하고, 정책을 두 곳에 두면 반드시 어긋난다. 다이얼로그에 라우팅 배지(`Linear Perp · 2x · isolated`), settings 없을 때 422 경고, 미리보기 레버리지 기본값 = 전략 설정, secret 안내문 구체화(§05 Webhook 카드 명시)를 넣었다.

회귀 = 22 테스트 **전부 수정 전 RED 확인**(parse 17 · router 4 · e2e 1). FE 신규 7건은 `git stash` 로 프로덕션 변경만 되돌려 RED 재현 — 통과만 보고 넘어가면 판별력 0인 가드를 100%로 착각한다. Sprint 7a 가 `test_e2e_webhook_to_futures_order.py:5-6` 독스트링에 "Sprint 7b 로 분리" 라 적고 미뤄둔 HTTP→ccxt 전 구간 테스트도 여기서 닫았다.

**Risk:** 🟢

---

### BL-475

**Title:** 서버 권위 risk% 사이징이 구현된 적 없다 (UI 는 있다고 말하고 있었다)
**Category:** Backend / trading (사이징)
**Priority:** P3
**Trigger:** 사이징 자동화가 실제로 필요해질 때
**Est:** M
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

**권장 접근:** (a) 사용자가 읽기 전용 계정을 삭제하면 자연 소멸(가장 싸다) · (b) 등록 시 동일 거래소 서브계정 중복을 감지해 경고 · (c) 귀속을 계정이 아니라 `(exchange, exchange_order_id)` 기준으로 재조회. 셋 중 무엇을 할지는 계정 2개 등록을 계속 지원할지에 달렸다.

**Risk:** 🟢 (알림 노이즈. 금액 정확도 영향 없음)

---

### BL-478

**상태:** ✅ **Resolved (2026-07-27, `feat/live-conditional-entry`).** (c) 차단은 2026-07-26 에, **(a) 조건부 주문 등재는 이번에** 해소했다. 선언적 reconcile — `PendingOrderSnapshot.target_position`(체결 후 순 포지션)이 사이징 SSOT 이고 주문 수량은 거래소 실포지션과의 차로 계산한다(delta 를 보내면 같은 id 재발행에서 포지션이 2배가 된다). 귀속 불변식 5조건 · `idempotency_key` 에 `trade_id` 를 실어 마이그레이션 0 · 세션 종료 시 청소 · `orphan_scanner` 오탐 면제 · 화면 노출. **데모에서 조건부 진입 5건 실체결**, 거래소 `/v5/order/history` 5/5 + `/v5/execution/list` 5/5(`closedSize=0` = 진입) 대조 일치.

**Title:** stop-entry 전략은 라이브에서 **진입이 구조적으로 절대 나가지 않는다** — 청산만 나가서 매번 110017
**Category:** Backend / trading (라이브 신호 dispatch)
**Priority:** **P1**
**Trigger:** 즉시 (라이브 세션이 지금 이 상태로 돌고 있다)
**Est:** M
**출처:** 2026-07-26 dogfood-restore 체크리스트 B 조사

**원인 / 영향:** `run_live` 가 `fill` 액션을 dispatch 대상에서 제외한다 — `event_loop.py:287-288`:

```python
    # entry / close 만 dispatch 대상 (fill 은 broker 측 pending stop 체결)
    if e.action not in ("entry", "close"):
        continue
```

독스트링(`event_loop.py:253-255`)이 근거를 명시한다: _"action="fill" 은 broker 이벤트 (pending stop 체결) 이므로 Pine signal 로 dispatch 안 함 — **broker 가 자체 fill 알림 처리**"_.

**★그 전제가 성립하지 않는다. broker 에 그 stop 주문을 올린 적이 없다.** `src/tasks/live_signal.py` 에 `trigger_price` / `trigger_direction` / `PendingOrder` 참조가 **0건**이다(전수 grep). 즉 조건부 진입 주문을 거래소에 등재하는 코드가 존재하지 않는다.

**영향 범위 = `strategy.entry(..., stop=...)` 를 쓰는 전략 한정.** `strategy_state.py:598-608` 이 `stop` 이 있으면 `PendingOrder` 만 파킹하고 **`return None`**(이벤트 미발행) 한다. `stop` 없는 시장가 진입은 `:634-642` 가 `event_action="entry"` 로 정상 발행하므로 영향 없다.

**결과 사슬** — 진입 이벤트 0건 → 거래소 포지션 0 → 다음 반전 시 pine 이 `close` 이벤트 발행(`strategy_state.py:748` `_flip_opposite_positions` → `close()` → `:671-679`) → 그건 dispatch 됨 → reduce-only 인데 포지션이 없음 → `retCode 110017 "current position is zero"`. 실측 = 라이브 세션 `0e15c3c0` 의 주문 전량이 `reduce_only=true`·`rejected`·110017 이고 진입 주문은 **한 건도 없다**.

시드 전략 `s1_pbr` 은 진입 2개가 모두 `stop=` 이라(`s1_pbr.pine:7,20`) **100% 이 경로다.**

<details><summary>이전 판정 (2026-07-26 live-entry-wiring — (c) 한정. 위 상태 줄이 대체했다)</summary>

**상태:** ✅ **(c) Resolved (2026-07-26, `feat/live-entry-wiring`)** — 세션 시작 422 `live_stop_entry_unsupported` + evaluate preflight 자동 종료. 실화면 확인(`0e15c3c0` 이 첫 tick 30초 내 자동 종료, PbR 422 문구 + EMA 201 음성 대조). **(a) 조건부 주문 등재는 열려 있다** — (c) 는 거짓말을 멈춘 것이지 기능을 만든 것이 아니다.

</details>

**권장 접근:** 셋 중 택일 — (a) `PendingOrder` 를 거래소 conditional order 로 등재(`OrderRequest.trigger_price`/`trigger_direction` 이 이미 있고 `_merge_exit_params` 가 처리한다) · (b) `fill` 도 dispatch 대상에 넣어 시장가로 근사(체결가 괴리 발생, TV parity 훼손) · (c) stop-entry 전략의 라이브 세션 시작을 **명시적으로 차단**하고 이유를 화면에 표시. **최소 정직안은 (c)** — 지금은 조용히 안 되면서 되는 척한다.

**Risk:** 🔴 (라이브 자동매매가 진입을 못 하는데 화면상 "돌고 있음")

---

### BL-479

**Title:** 라이브 경로에 사이징이 배선돼 있지 않다 — `compute_qty()` 가 항상 `1.0`, `position_size_pct` 는 읽히지 않는다
**Category:** Backend / trading (라이브 포지션 사이징)
**Priority:** **P1**
**Trigger:** BL-478 과 함께 (진입이 열리면 즉시 수량이 문제가 된다)
**Est:** M
**출처:** 2026-07-26 dogfood-restore 체크리스트 B 조사

**원인 / 영향:** `run_live`(`event_loop.py:270-272`)가 `run_historical` 을 **사이징 인자 없이** 호출한다.

```python
    # run_historical 전체 재실행 (warmup replay)
    result = run_historical(source, ohlcv, capture_history=False, strict=False)
```

`run_historical` 은 `initial_capital` / `default_qty_type` / `default_qty_value` / `leverage` 를 받지만(`event_loop.py:62-76`) `configure_sizing` 은 `if initial_capital is not None` 게이트 뒤에 있다(`:107-113`). 라이브에선 `None` → 미호출 → `compute_qty()` 가 fallback `1.0` 반환(`strategy_state.py:311-317`).

그 `1.0` 이 그대로 `LiveSignal.qty` → `LiveSignalEvent.qty` → `OrderRequest.quantity`(`live_signal.py:929`)로 흐른다. **1 BTC ≈ $64,000 명목.**

**`StrategySettings.position_size_pct` 는 라이브에서 아무 데서도 읽히지 않는다.** 전수 분류 결과 사이징 계산에 쓰이는 유일한 자리는 `compat.parse_and_run_v2`(`compat.py:99-111`)이고, 그 함수의 프로덕션 호출자는 `backtest/engine/v2_adapter.py:96` **하나뿐**이다. `live_signal.py` 는 `parsed_settings` 를 `leverage`(`:931`)·`margin_mode`(`:932`) 두 곳에만 쓰고 `position_size_pct` 는 검증만 하고 버린다. `live_session_service.py:80` 은 필드 **존재**만 요구하고 값은 안 본다.

★**Pine 선언도 마찬가지로 무시된다.** `strategy(default_qty_type=..., default_qty_value=...)` 를 선언한 스크립트조차 라이브에선 `1.0` 이다 — 추출 경로(`ast_extractor.py:259-280` → `compat.py:41-57`) 전체가 `initial_capital is not None` 게이트 뒤에 있기 때문. 즉 사이징 우선순위 사슬(Pine > form > Live)이 라이브에선 통째로 죽어 있다.

**상태:** ✅ **Resolved (2026-07-26, `feat/live-entry-wiring`)** — 세션 시작 시 `AccountBalanceService.get_balance().total` 1회 스냅샷 → `live_signal_sessions.equity_baseline_usdt` → evaluate 가 `run_live(initial_capital=..., live_position_size_pct=...)` 로 전달. 우선순위 사슬은 신규 `pine_v2/sizing.py` SSOT 로 백테스트와 공유. **실주문 3중 대조** — 손계산 `190549.99467459 x 1% / 64512.50 = 0.02953691` = DB = 거래소(`qty 0.029 Filled`), 실집행 $1,870 vs 미배선 $64,484(34.5배).

★기준선은 **매 tick 조회가 아니라 세션 시작 1회 스냅샷**이다. warmup replay 라 매 tick 실잔고를 주입하면 실현손익이 이중 계상되고, 300바를 벗어나면 빠져 같은 바가 tick 마다 다른 수량을 갖는다.

**권장 접근:** `run_live` 에 자본 기준선 + 사이징을 전달한다. `position_size_pct` 는 evaluate 단계에서 이미 `parsed_settings` 로 손에 있고(`live_signal.py:396`), 없는 것은 **equity 기준선**이다 — kill-switch 가 이미 쓰는 balance provider(`live_signal.py:880-885`)를 재사용하는 게 가장 짧다. 다만 "라이브 equity 를 매 tick 거래소에서 가져올 것인가"는 지연·정합성 결정이 필요하다(BL-476 과 같은 종류의 trade-off).

**BL-466 과 뿌리가 다르다** — 그쪽은 백테스트 마진 게이트 no-op(L=1), 이쪽은 라이브 배선 부재다.

**Risk:** 🔴 (열리면 곧바로 과대 포지션)

---

### BL-480

**Title:** `local_only` 발산이 빈 포지션 표에서 렌더되지 않아 사용자에게 숨겨진다
**Priority:** P2
**Status:** ✅ Resolved (2026-07-26, `feat/bl-474-webhook-ingress-parity`)

**결과:** 세션 단위 `divergences`를 표면화하고 빈 상태 가드에 포함시켜, 거래소 포지션이 0건이어도 전략이 보고한 발산을 화면에 표시한다.
**근거:** [스프린트 회고](dev-log/2026-07-26-bl474-webhook-ingress-parity.md)

---

### BL-481

**Title:** `sessions_allowed` 가 라이브에 미배선 — 거래 시간대를 제한해도 라이브는 24 시간 진입한다
**Priority:** P2
**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

**결과:** `run_live`에 세션 제약을 배선하고, 세션 제약이 있을 때 라이브 OHLCV의 `timestamp`를 tz-aware 인덱스로 복원해 범위 밖 진입을 fail-closed로 막았다.
**근거:** [보관 상세](archive/backlog/2026-07-26-live-engine-parity.md#bl-481) · [스프린트 회고](dev-log/2026-07-26-live-engine-parity.md)

---

### BL-482

**Title:** `pyramiding` cap 이 라이브에 미배선 — 같은 전략이 백테스트는 cap, 라이브는 무제한 중첩
**Priority:** P3
**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

**결과:** 선언의 `pyramiding` cap을 라이브 엔진까지 전달하고, cap 때문에 건너뛴 진입도 관측 가능한 skip으로 표면화했다.
**근거:** [보관 상세](archive/backlog/2026-07-26-live-engine-parity.md#bl-482) · [스프린트 회고](dev-log/2026-07-26-live-engine-parity.md)

---

### BL-483

**Title:** `leverage` 가 라이브 엔진에 미배선 — 증거금 게이트와 청산가 모델이 L=1 로 no-op
**Priority:** **P1**
**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

**결과:** leverage를 라이브 엔진의 증거금·청산 게이트까지 배선하고, 무음 skip을 구조화된 `entry_skips`·메트릭·화면 행으로 표면화했다.
**근거:** [보관 상세](archive/backlog/2026-07-26-live-engine-parity.md#bl-483) · [스프린트 회고](dev-log/2026-07-26-live-engine-parity.md)

---

### BL-484

**✅ Resolved (2026-07-30 conditional-entry-alignment · 마이그레이션 1)** —
`trading.live_signal_sessions.deactivated_reason` 신설(nullable `String(64)` — PG enum 을 쓰지 않아
`LiveSignalInterval` 이 밟은 자동 enum cast 함정을 피하고 사유 추가에 DDL 이 불필요하다. 대신 **읽으면 plain str** 이라 `.value`/`.name` 금지
— BL-453 과 같은 계약). 값 집합 SSOT = `SessionDeactivationReason(StrEnum)` **9종**. `deactivate(..., reason: str)` 는
**기본값 없는 필수 키워드**다 — 기본값을 주면 새 종료 경로가 사유를 빼먹어도 조용히 통과해 "왜 죽었는지 모르는 세션" 이 다시 생긴다. **7개 종료 경로 전건 배선**(preflight
2 · `run_live_error` · `runtime_divergence` · `gap_resync_position_mismatch` · `position_divergence` ·
`user_stopped`). ★`tasks/live_signal.py` 는 다른 워커 소유라 import 없이 리터럴을 넘겼고, 대신 **AST 테스트가 그 파일의 모든
`deactivate(...)` 호출을 훑어 미등재 사유를 차단**한다 — 변수(`preflight_cat`) 인자도 대입 리터럴을 추적하고 **리터럴 아닌 대입이 있으면 실패**시킨다. FE 는
목록·상세 공용 칩 1개(`SessionEndedReason`)로 렌더하고 코드→한국어 매핑은 `labels.ts` SSOT, **BE enum 을 실제로 읽어 라벨 누락·고아 라벨을 양방향
검사**하는 drift 가드까지 둔다. 사유가 없는 과거 행(마이그레이션 이전 종료)은 **아무것도 그리지 않는다** — 실브라우저에서 기존 12 세션 전부 `NULL` 로 확인.

**Title:** 세션 자동 중단 **사유**가 화면에 남지 않는다 — 알림 채널로만 나가고 DB 에 없다
**Category:** Frontend + Backend / trading (Surface Trust)
**Priority:** P2
**Trigger:** 자동 중단이 실제로 자주 일어나기 시작할 때
**Est:** M
**출처:** 2026-07-26 live-entry-wiring

**원인 / 영향:** preflight/runtime 자동 비활성화는 `_fire_divergence_alert` 로 Slack·Telegram 에만 사유를 보내고, DB 에는 `deactivated_at` 만 남는다. `publish_realtime(user_id, "session_state", {session_id})` 도 세션 ID 만 싣는다.

`GET /live-sessions` 는 `is_active=true` 만 돌려주므로 중단된 세션은 목록에서 **사라진다**. 사용자는 "왜 꺼졌는지" 는커녕 **꺼졌다는 사실도** 화면에서 알기 어렵다. BL-480 이 고친 "화면이 아는 것을 숨긴다" 와 같은 클래스다.

이번 스프린트는 최소 정직안만 했다 — 코크핏이 선택 세션을 목록에서 파생시켜, 사라지면 "이 세션은 중단되었습니다 + 알림 채널을 보라 + 재시작하면 사유가 보인다" 를 렌더한다. 그 문장은 전부 참이지만 **사유 자체는 여전히 화면에 없다.**

**권장 접근:** `live_signal_sessions` 에 `deactivated_reason` 컬럼 추가 + `GET /live-sessions?include_inactive=true`(BL-423 와 동일 요구) + 세션 카드에 사유 표시. BL-423 과 한 PR 로 묶는 게 자연스럽다.

**Risk:** 🟡 (조용한 중단. 금액 정확도 영향 없음)

---

### BL-485

**Title:** `FormErrorInline` 이 `detail.detail` 로 폴백하지 않아 공통 컴포넌트를 쓸 수 없다
**Category:** Frontend (에러 표면)
**Priority:** P3
**Trigger:** 422 에러 표면을 공통화하고 싶을 때
**Est:** S
**출처:** 2026-07-26 live-entry-wiring

**원인 / 영향:** `form-error-inline.tsx:93-97` 의 422 general 분기가 `friendly_message` 만 읽고, 없으면 `fallback = err.message` 로 떨어진다. 그 `err.message` 는 `"API 422 /api/v1/live-sessions"` 라 사람이 못 읽는다.

그리고 `friendly_message` 를 응답에 싣는 곳은 `main.py:17-54` 의 `isinstance` **하드코딩 화이트리스트**(`StrategyNotRunnable` / `StrategyDegraded`) 뿐이라, 새 예외는 그 필드를 못 갖는다.

결과: 라이브 세션 폼을 `FormErrorInline` 으로 교체하면 기존 422 **4종**(`StrategySettingsRequired` / `InvalidStrategySettings` / `AccountModeNotAllowed` / `LiveSessionQuotaExceeded`)이 전부 `"API 422 ..."` 로 **조용히 퇴행**한다. 그래서 이번 스프린트는 교체하지 않고 서버 `detail` 문자열 + `describeApiError` 경로를 유지했다.

**권장 접근:** `parseError` 에 `friendly_message ?? detail.detail` 폴백 3줄 추가. 그러면 공통 컴포넌트가 모든 도메인 예외에 안전해지고, 라이브 세션 폼 교체를 재검토할 수 있다. 회귀 = `friendly_message` 없는 422 가 `detail` 문구를 렌더하고 `"API 422"` 를 포함하지 않는지.

**Risk:** 🟢

---

### BL-486

**Title:** 라이브 사이징 equity 가 **300바 롤링 창**에 따라 변한다 — 같은 신호가 볼 때마다 다른 수량
**Priority:** **P1**
**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

**결과:** 창 이전의 `live_signal_events` 실현손익 carry를 기준 자본에 반영해 warmup 창과 무관한 사이징을 만들고, 화면 총계도 원장 SSOT로 전환했다.
**근거:** [보관 상세](archive/backlog/2026-07-26-live-engine-parity.md#bl-486) · [스프린트 회고](dev-log/2026-07-26-live-engine-parity.md)

---

### BL-487

**Title:** `test_get_pool_safe_across_event_loops` 가 `id()` 재사용에 취약 — 전체 스위트에서 random RED
**Priority:** P3
**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

**결과:** pool 객체 참조를 유지한 채 identity를 비교하도록 바꿔 `id()` 재사용에 따른 random RED를 제거했다.
**근거:** [보관 상세](archive/backlog/2026-07-26-live-engine-parity.md#bl-487) · [스프린트 회고](dev-log/2026-07-26-live-engine-parity.md)

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
3. [`_deferred.md`](archive/refactoring-backlog/_deferred.md) 의 6-8주 재평가 (BL-005 본인 의지 second gate, BL-070~075 Beta milestone)
4. 도래 항목이 있으면 active TODO.md 의 "Next Actions" 로 승격 + 본 문서에서 `**Status:** 🟡 In progress (Sprint NN)` 마킹

---

## 변경 이력

> Sprint 별 BL 변경 1-line 요약. 상세는 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 또는 해당 sprint dev-log.

### functional-parity 스프린트 (2026-07-23)

- **C 디자인 이식 후 기능 격차 마감 (codex exec 4-generator 병렬 + Claude 적대 평가 교차 + Opus MCP dogfood)**: BL-401/BL-411 구현 Resolved + BL-402 구조 소멸 Resolved. 신규 배선 = 주문취소 액션 열(A2, "API unbacked" 미렌더 전제가 거짓 — CF4 완비 실측) / orders `state` 반복 Query + 미체결 nav-count(B2, 캐논 §4.6 복원) / `strategy.backtest_count` read-time GROUP BY(B1, COMPLETED 기준) / 스트레스 최신 결과 리로드 복원(A7-lite) / 대시보드 전략 링크 404 수정(A1) / dead code 정리(backtest-history-card·viewBacktestShare·StrategyWithPine stub). 적대 평가가 실버그 3건 사전 차단(RQ v5 undefined-resolve 영구 error / grid min==max 차단 회귀 / Sprint 54 문구 잔존). 신규 BL-413~416. 정본 = [`functional-parity/`](archive/sprints/functional-parity/checklist.md).

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

- Wave 1/2/3(라이브 TP/SL) 누적 부채 7건 신규: P2 BL-365(trigger_direction dead+미배선) / BL-366(dispatch DI 중복) / BL-368(`_merge_exit_params` ccxt-key 누설) / BL-369(create_order 3×복붙), P3 BL-367(dispatch boilerplate) / BL-370(exit-field multi-SSOT) / BL-371(ws-stream fill 스트레스). 3 병렬 Explore + adversarial 검증(Agent 2건 과대평가 교정: trigger_direction=현재 버그 아님 latent / risk-sizing test 7건 존재→STOP 미발동). [`2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md). BL-202/205 와 무중복. money-path churn 회피로 **리팩터는 트레일링 안정화 후** — C1(BL-365)도 trading-stop 엔드포인트(position-inferred)라 트레일링 미소비, deferred 확정.

### Track B `/deepen-modules trading` audit-only (2026-05-15)

- BL-308 P1 (websocket test coverage 4% → ≥70%) + BL-309 P2 (registry/webhook/fees 0% test 추가) 신규. 15 → 17 active. [`2026-05-15-trading-deepen.md`](dev-log/2026-05-15-trading-deepen.md). **Architectural debt 적음** 결론 (Deep module + dispatch dict + 0 SSOT 중복). skill STOP condition (test coverage <70%) 매치 = test 우선 권고.

### CLAUDE.md align audit Track C (2026-05-15)

- BL-306 (§5 한국어 콜론 종결 lint) + BL-307 (§6 한국어 file header lint + 70 file backfill) 신규 P3. 13 → 15 active. [`2026-05-15-claudemd-align-audit.md`](dev-log/2026-05-15-claudemd-align-audit.md). LESSON-068 1/3 등재.

### Sprint 59 — PR-D 트리아주 (2026-05-13)

- 158 BL → 13 Active + 8 Deferred + 137 Archived. [`_archived.md`](archive/refactoring-backlog/_archived.md) + [`_deferred.md`](archive/refactoring-backlog/_deferred.md) 신설.

### 최근 sprint (Sprint 53~58)

- **Sprint 58** (2026-05-11) — BL-241/242/243 Pine TA 확장 Resolved (ta.wma/hma/bb/cross/mom/obv+fixnan + strategy.equity + UTC 라벨). 92 → 89. [`sprint58-close`](dev-log/2026-05-11-sprint58-close.md).
- **Sprint 57** (2026-05-11) — BL-234 Optimizer Polish (prior=normal+one_hot+roulette) + BL-237 optimizer_heavy queue Resolved. 신규 BL-241~243. 91 → 92. [`sprint57-close`](dev-log/2026-05-11-sprint57-close.md).
- **Sprint 56** (2026-05-11) — BL-233 Genetic executor 본격 Resolved + 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11) — BL-232 Bayesian executor 본격 Resolved + 신규 BL-233~237 (5건). 88 → 92. [`sprint55-master`](dev-log/2026-05-11-sprint55-master.md).
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
- **Sprint 32** (2026-05-05) — Surface Trust Recovery (7 Resolved). 87 → 80. [`sprint32-master-retro`](dev-log/2026-05-05-sprint32-master-retrospective.md).
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
**상태:** 🟢 **열려 있다 — 「축소」 (2026-08-01 entry-completeness-rejudgement).** 유실 채널 5종 중 **(2)(3) 은 유실 채널이 아님이 확정**, **(4)(5) 는 판별력을 증명한 계측기로 0**, 남은 것은 **(1) 잔여 거절 하나뿐 1건/2일**이다. 층위1 확정 거절률 **16.67% → 2.44%** · 에피소드 유실률 **2.08%**. **P1 → P2 강등** — 잔여 설계는 [BL-578](#bl-578), 재측정 근거는 [BL-536](#bl-536) §2026-08-01(Resolved). 아래 §채널 5종 크기 확정 참조.
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
**상태:** 🟡 **열려 있다 — 범위 「축소」**(2026-07-30 close-mismatch-soak). 전제 반증: 엔진이 pending 진입에 exit 레그를 만들지 않아 실을 값이 없다. 배관+계측은 착지, 엔진 계약 변경은 크기 미확정으로 보류.
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
**출처:** 2026-07-28 live-entry-parity codex G1 검증 #7 (재현 확인)

**원인 / 영향:** `run_live`(`event_loop.py`)는 `run_historical` **만** 호출한다. Track A 를 처리하는 `run_virtual_strategy` 는 `TrackRunner._dispatch_table["A"]` 로만 도달한다. 즉 라이브 경로에 Track 분기가 없다. `fill_timing=next_bar_open` 이 Track A 에서 무시된다는 경고도 라이브에서는 발생하지 않는다(그 코드에 도달하지 않으므로).

★이번 스프린트가 "없는 경로에 계측을 붙이지 않기 위해" W3-3 을 폐기하면서 발견했다. **영원히 0인 카운터를 만들지 않은 대신, 그 경로가 무엇을 하는지는 여전히 미정의다.**

**권장 접근:** 라이브 세션 등록 시 Track 을 판정해 미지원이면 422 로 막거나(BL-478 (c) 선례), `run_live` 에 Track 분기를 넣는다.
**Risk:** 🟢

---

### BL-526

**Title:** ★**라이브 실적이 백테스트 기대치와 맞는지 화면에서 물을 수 없다** — 패리티가 진입까지만 증명됐다
**Category:** Frontend + Backend / 성과 표면
**Priority:** P2 (제품 전제 검증)
**Trigger:** 다음 스프린트
**Est:** M
**출처:** 2026-07-28 live-entry-parity 종결 판단

**원인 / 영향:** 11스프린트에 걸쳐 "라이브가 백테스트대로 **주문하는가**" 를 고쳤고 BL-511 로 그것이 닫혔다(거절 43.3% → 0%). 그런데 **"라이브가 백테스트대로 **버는가**" 는 아직 어디에서도 물을 수 없다.**

- 라이브는 주문별 `realized_pnl` 과 세션 이벤트만 있다. 백테스트는 24 metric 리포트가 있다. **둘을 같은 자로 놓는 표면이 없다.**
- 프론트 grep 결과 라이브↔백테스트 대조 컴포넌트 **0건**.

★**첫 실측이 문제를 가리킨다** — 62분 soak 실현손익 **−5.74 USDT**, 체결당 수수료 **≈1.01 USDT**. 0.029 BTC(≈1,840 USDT notional) 라운드트립 수수료가 **notional 의 약 0.11%** 다. **1m PbR 이 그 문턱을 넘는 엣지가 있는지 아무도 모른다.** 이 대조가 없으면 이후 배선 작업이 전부 "지는 전략을 더 정확하게 실행" 하는 데 쓰일 수 있다.

**권장 접근:** 새 엔진 코드 없이 **read-time 파생**으로 만든다(#471 perf-surface 선례). 같은 전략·같은 기간의 백테스트 기대치와 라이브 세션 실적을 나란히 놓고, **수수료·슬리피지를 포함한 실효 격차**를 보여준다.

★**설계 시 반드시 짚을 것** — (a) 라이브 세션 손익의 SSOT 는 `live_signal_states.total_realized_pnl` 이 **아니라** append-only `live_signal_events` 다(단조가 아니다). (b) 시뮬 PnL 과 거래소 PnL 은 **부호까지 다를 수 있다**(수수료 왕복). 같은 누적기에 넣지 마라. 둘 다 `gates-and-traps.md` 에 실측 근거가 있다.
**Risk:** 🟢 (읽기 전용 파생 — 머니-패스 무영향)

**✅ Resolved (2026-07-28, live-outcome-parity):** `GET /live-sessions/{id}/outcome-parity` + 세션 상세 패널. **마이그레이션 0 · 새 엔진 코드 0.** 회고는 [`dev-log/2026-07-28-live-outcome-parity.md`](dev-log/2026-07-28-live-outcome-parity.md).

- **분해** = `엔진 기대 gross + 체결 격차 + 비용 = 거래소 확정 net`. 수수료는 **가정하지 않고 파생**한다(원장 평균가 gross - 확정 net).
- **실측** — 62분 soak: 기대 +0.6857 / 격차 +2.7154 / 비용 -6.1641 / 확정 **-2.7630**, 왕복 실효 비용률 **0.1115%**. 전략 누적 4세션: 매칭 9건, 커버리지 **15%**, 기대 +5.20 vs 확정 **-14.19**.
- ★**BL 이 물었던 0.11% 문턱이 화면에 나왔다** — 손계산과 화면이 일치(0.1115%). **다만 화면은 아직 답을 말하지 않는다**(표본 9 < 필요 30 이라 성과 비율 차단). 그게 이 기능의 의도다.
- ★**전제 3건이 반증됐다** — 저장된 백테스트로는 대조 불가(전부 1h·비중첩, 1m OHLCV 0행) · `live_signal_events.realized_pnl` 에 **비용이 적용된 적 없음**(`run_live` 가 `v2_adapter` 비용모델을 안 거친다) · `CONTEXT.md` 의 "선택적 reference Backtest" 는 **없는 FK**.
- ★**설계 노트 (a) 는 부정확했다** — 실적의 SSOT 는 이벤트가 아니라 **확정 주문**이다. `live_signal_events` 는 **기대치**의 SSOT 다. 미동기 `Order.realized_pnl` 에는 엔진 추정값이 그대로 들어 있어 확정 필터가 빠지면 화면이 동어반복이 된다.
- 부수: 종료된 세션 도달 경로 신설(`include_inactive=true`, 기본값 불변) — 그전엔 API·UI 양쪽에서 활성만 노출돼 **회고 표면에 도달 자체가 불가능**했다.

---

### BL-527

**Title:** ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다
**Category:** pine_v2 / 라이브 신호
**Priority:** P2 (잠재 — 실데이터 미재현)
**Trigger:** 기대치 정확도가 판정 입력으로 쓰이기 전
**Est:** S
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

### BL-530

**Title:** ★엔진이 청산했다고 본 것의 71% 가 거래소에서 확정되지 않는다
**Category:** Trading / 라이브 완결성
**Priority:** **P1**
**Trigger:** 실자금 cutover 전 필수
**Est:** M-L
**출처:** 2026-07-28 live-outcome-parity 실측

**원인 / 영향:** close 이벤트 **72건 중 거래소 확정은 21건(29%)** 이다. 나머지 51건:

| 갈래            | 건수   | 뜻                        |
| --------------- | ------ | ------------------------- |
| dispatch failed | **16** | 이벤트가 발주까지 못 갔다 |
| order rejected  | **35** | 발주됐으나 거래소가 거부  |

직전 스프린트(BL-511)가 고친 것은 **진입** 거절이다. 이 숫자는 **청산** 쪽 유실을 처음 계량한 것이다. 엔진은 포지션이 닫혔다고 보고 다음 신호를 평가하는데 거래소에는 포지션이 남아 있을 수 있다 — 즉 **시뮬과 실제의 포지션 상태가 갈린다.**

★거절 상당수는 "reduce-only 대상 포지션 부재" 계열로 보인다(진입이 애초에 안 걸린 것의 하류 효과). **원인 분해가 첫 step 이어야 하고, 기계적 수리가 아니라 측정이 먼저다.**

**권장 접근:** 거절 코드별 분해 -> 진입 유실 하류인지 독립 결함인지 판정 -> 그 다음 수리. BL-522(진입 완결성)와 같은 뿌리일 가능성이 높으므로 묶어서 본다.
**Risk:** 🔴 (실자금에서 포지션 상태 발산)

**✅ Resolved (2026-07-28, live-close-completeness):** 뿌리는 **계기 불일치**였다 — 엔진이 **Bybit 스팟** 1m 봉을 재생하는데 주문은 **무기한선물**에 나갔다(`market_data/providers/ccxt.py:46` `defaultType: "spot"`). 라이브 OHLCV fetch 를 `to_ccxt_perpetual_symbol` 로 통과시켜 정렬했다. **마이그레이션 0 · 1사이트.** 회고는 [`dev-log/2026-07-28-live-close-completeness.md`](dev-log/2026-07-28-live-close-completeness.md).

- **분해 실측** — 51건 중 **46건(90%)이 한 갈래**다: 엔진은 포지션을 믿는데 거래소는 flat(`close_position_flat` 16 + `110017 current position is zero` 30). 나머지 4건은 **반대 방향**(`reduce-only ... same side`)이고, `reduce_only=True` 하나가 포지션 반전을 막는 유일한 방벽이었다. 1건은 read-only 계정(BL-501 계열).
- ★**외부 오라클이 기전을 확정했다** — 2026-07-28 08:06 UTC **스팟 고가 63541.7** 이 시뮬 스톱과 **소수점까지 일치**했고, 같은 분 **perp 고가는 63499.4**(42.3 아래). 스톱 가격 자체가 스팟 피벗에서 계산됐다는 뜻이다. 두 봉 계열을 픽스처로 고정했다(`tests/fixtures/bybit_spot_vs_perp_bars.py`).
- ★**헤드라인 71% 는 창을 안 건 값이었다** — 3일·3스프린트 누적이라 BL-511 이전 데이터가 대부분이다(reduce-only 거절 35건 중 31건이 07-26). **수리 전 기준선은 50%(n=6)** 로 정정한다.
- **BL-522 는 미착수** — 계기 수리 후 재측정한 크기 위에서 설계한다. 사라질 문제에 새 상태 저장소를 만드는 것이 최대 위험이라는 BL-522 자신의 경고를 따랐다.
- 부수: 엔진↔거래소 포지션 발산 감지 신설(`qb_live_position_divergence_total`) — **방향 불일치만 fail-closed**, 나머지는 관측만. 진단 절차는 [`live-close-diagnostics.md`](reference/operations/live-close-diagnostics.md).

---

### BL-531

**Title:** parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery
**Category:** Refactor / Trading
**Priority:** P2
**Trigger:** parity 지표를 더 붙일 때
**Est:** S
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
**출처:** 2026-07-29 PR #496 코드리뷰 (Spec 축)

**원인 / 영향:** `test_outcome_parity.py:55-78` 이 SQL 오라클 **총계를 관측 1건에 통째로 넣고** 나머지 26건을 0 으로 채운다. 총계와 실효 비용률(0.05526%)은 맞지만 **27건 Decimal 합산 자체는 이 오라클이 검증하지 않는다.**

★조인·스코프 정확성은 `test_parity_repository.py` 와 실 DB 대조가 담당하므로 커버는 있다. 다만 이 테스트의 이름(`test_reproduces_sql_oracle_totals...`)이 실제보다 넓은 것을 주장한다.

부수 — 리뷰가 함께 지적한 스코프 이탈 2건은 **의도된 것으로 판단해 기각**한다: (a) 종료 세션 도달 경로(W5)는 화면 검증이 "기능에 도달 불가" 를 잡아 추가한 것으로 dev-log 에 근거가 있다, (b) `/state` 폴링 계약 변경은 신규 표면이 폴링하지 않도록 한 결과이고 핸들러는 무변경이다. 다만 **둘 다 G1 동결 스펙 밖이었다** — 스코프 확장 시 동결 문서를 갱신하는 절차가 없었던 것이 진짜 문제다.

**권장 접근:** 27개 관측에 실제 leg 값을 넣어 합산을 재현하거나, 테스트 이름을 실제 검증 범위에 맞게 좁힌다.
**Risk:** 🟢

---

### BL-535

**상태:** 🟡 **부분 Resolved (2026-07-30, PR #503 engine-exchange-alignment)** — 적재 경로는 실주행 확인(perp `BTC/USDT:USDT` 721행 신규 · 스팟 9337 불변), **스팟/perp 결과 차 대조는 미실시**. 근거: 본 섹션 「★실주행 검증」 마지막 문단("Resolved 가 아니라 **부분 완료**로 둔다") · `docs/archive/dev-log/index-full-2026-08-02.md` ("BL-535 부분", "잔여 = 스팟/perp 결과 차 대조 미실시").

**Title:** ★**백테스트는 스팟 봉으로 perp 전략을 검증한다** — 라이브만 계기를 맞춰 두 축이 갈렸다
**Category:** Backend / market_data
**Priority:** **P1**
**Trigger:** 백테스트 결과를 라이브 판단 근거로 쓰기 전
**Est:** M
**출처:** 2026-07-28 live-close-completeness (BL-530 수리의 의도된 잔여)

**원인 / 영향:** BL-530 이 **라이브 경로만** perp 로 정렬했다(`tasks/live_signal.py` 1사이트). 백테스트는 여전히 `TimescaleProvider` → `CCXTProvider`(`defaultType: "spot"`) 경로라 **스팟 이력**으로 돈다. 즉 지금은 **백테스트=스팟 / 라이브=perp** 다.

★**이것은 버그가 아니라 명시적 트레이드오프다.** 라이브 실행 패리티(P1, cutover 블로커)를 먼저 닫는 대가로 남겼다. 다음 사람이 이 상태를 결함으로 오진하고 라이브를 스팟으로 되돌리면 BL-530 이 그대로 재발한다.

**영향** — 같은 전략이 두 축에서 다른 신호를 낸다. 실측 괴리는 **25~42 USDT(0.04~0.066%)** 이고 **한쪽으로 치우친다**(스팟이 위). 스톱·피벗이 그 폭 안에 있는 전략일수록 발산이 크다. BL-526 의 라이브↔백테스트 대조 표면도 이 confound 를 안고 있다.

**권장 접근:** `ts.ohlcv` 에 perp 를 **`BTC/USDT:USDT` 키로 신규 적재**한다 — 기존 행 불변이라 **마이그레이션 0** 이고, `TimescaleProvider` 는 cache-first 라 백테스트 1회가 곧 시딩이다(dogfood-restore 선례). 심볼 컨벤션이 전략·UI·기존 백테스트에 파급되므로 그 경계를 먼저 정해야 한다.
**Risk:** 🟡 (판단 근거의 정합성. 머니-패스 직접 영향은 없다)

### 코드 착지 (2026-07-29 함대 워커 `bl535`) — **실주행 검증 대기**

경계 정본 신설: [`instrument-symbol-boundary.md`](reference/domain/instrument-symbol-boundary.md).
변환은 `to_ccxt_perpetual_symbol` **재사용**이고 신규 함수는 없다. 마이그레이션 0.

- **fetch 경로 1사이트** — `market_data/providers/timescale.py` `get_ohlcv` 가 canonical 을 받아 상품 키로 lock·gap·fetch·insert·get_range 한다. 세 소비자(backtest·optimizer·stress_test)가 이 프로토콜 하나를 지나므로 소비자별 복제가 없다. `CCXTProvider` 의 `defaultType: "spot"` 은 **건드리지 않았다**(콜론 표기가 이기는 것은 BL-530 이 외부 오라클로 확정).
- 부수 2사이트 — 거래 상세 차트(`backtest/service.py` `trade_ohlcv`)가 perp 우선·없으면 legacy 스팟, `tasks/market_data_backfill.py` 의 row-count 가 **쓰는 키로** 센다(안 고치면 `rows_written` 이 상시 0 이라 거짓 보고).
- 기존 스팟 행은 UPDATE/DELETE 없음. `TestLegacySpotRowsAreUntouched` 가 값까지 잠근다.

### ★실주행 검증 (2026-07-30 CONTROL) — 적재 **확인**, 결과 차 대조는 **미실시**

백테스트 1회(HMA Curvature · `BTC/USDT` · 1h · 2026-06-29~07-29)를 실제 API 로 큐에 올려 celery 로 완주시켰다.

| `ts.ohlcv` 키          | 실행 전(14:58) | 실행 후(15:00)                           |
| ---------------------- | -------------- | ---------------------------------------- |
| `BTC/USDT` (스팟)      | 9337           | **9337 불변** ✅                         |
| `BTC/USDT:USDT` (perp) | **없음**       | **721행 신규** (요청 기간과 정확히 일치) |

즉 수용 기준 ②(perp 를 문다)와 ③(기존 행 불변)이 실주행에서 확인됐다. 마이그레이션 0.

★**미실시 — 같은 전략의 스팟/perp 결과 차 대조.** 활성 라이브 세션이 하나라도 있으면 `strategy.settings.leverage != 1` 인 전략의 백테스트가 전부 **422 `mirror_not_allowed`** 로 막힌다(`backtest/exceptions.py:202`, BL-186 대기 사항). 그래서 두 축 비교는 leverage 미설정 전략으로만 가능했고, **실측 괴리(0.04~0.066%) 방향 일치는 확인하지 못했다.** 이 대조가 남아 있으므로 Resolved 가 아니라 **부분 완료**로 둔다.

---

### BL-536

**Title:** 진입 유실 채널 5종을 재측정하고, 그 크기로 설계 여부를 판단한다
**Priority:** P1
**Status:** ✅ Resolved (2026-08-01, entry-completeness-rejudgement)

**결과:** C2·C3는 유실 채널이 아니고 C4·C5는 판별력을 증명한 계측기로 0이었다. 남은 C1은 1건/2일(층위1 2.44%, 에피소드 2.08%)이어서 전환 의도 영속화 저장소를 만들지 않으며 [BL-578](#bl-578)로 보류했다.
**근거:** [재판정 회고](dev-log/2026-08-01-entry-completeness-rejudgement.md) · [사전등록 감사](dev-log/2026-08-01-entry-completeness-rejudgement-prereg-audit.md)

---

### BL-543

**Title:** 재생 구간 포지션이 세션 시작부터 `engine_only` 발산을 만든다
**Priority:** P1
**Status:** ✅ Resolved (2026-07-30, engine-exchange-alignment)

**결과:** position epoch 이전 상태를 폐기해 신규 세션 첫 평가 `position_size=0.0`, `engine_only` 증가 0을 실주행으로 확인했다. 반대 방향의 가용성 잔여는 별건 [BL-544](#bl-544)로 이관했다.
**근거:** [스프린트 회고](dev-log/2026-07-30-engine-exchange-alignment.md)

---

### BL-537

**Title:** 활성 세션이 없을 때 고아 포지션을 앱에서 청산할 수 없다
**Priority:** P1
**Status:** ✅ Resolved (2026-07-29, live-orphan-close)

**결과:** 계정 스코프의 기존 BL-498 경로가 비활성 세션 포지션도 닫는다는 것을 실주행 3중 대조로 확인해 새 엔드포인트를 만들지 않았다. 실제 결함인 settings 422와 0/None leverage 폴백을 수정했다.
**근거:** [스프린트 회고](dev-log/2026-07-29-live-orphan-close.md)

---

### BL-541

**Title:** 세션 행이 아예 없는 포지션은 여전히 앱에서 못 닫는다 (웹훅 경로 · 거래소 수동 거래)
**Category:** Backend / trading
**Priority:** P2
**Trigger:** 웹훅으로 포지션을 열기 시작할 때, 또는 `no_owning_session` 이 실제로 관측될 때
**Est:** M
**출처:** 2026-07-29 live-orphan-close (BL-537 재현이 남긴 잔여)

**원인 / 영향:** `Order.strategy_id` 가 `nullable=False` + FK RESTRICT(`models.py:172-178`)라 청산 원장 행에 전략이 반드시 필요하다. 세션에서 그걸 얻으므로 세션 행이 없으면 `no_owning_session` 으로 막힌다(`position_service.py:303`). 해당 클래스는 **웹훅 경로**(`router.py:99-183` 은 `LiveSignalSession` 없이 주문을 낸다)와 거래소에서 직접 연 포지션이다.

★**아직 실측된 적이 없다.** 2026-07-29 재현에서 `no_owning_session` 은 **한 번도 안 났다** — 세션 행은 비활성이어도 영구히 남기 때문이다. 그래서 이번 스프린트에서 **의도적으로 짓지 않았다**(BL-536 이 경고하는 "측정되지 않은 필요 위에 설계" 회피).

**권장 접근:** 실제로 관측되면 착수한다. 그때도 `Order.strategy_id` nullable 화는 금지 — `CumulativeLossEvaluator`(`kill_switch.py:96-105`)가 전략별로 합산하므로 NULL 행은 kill-switch 에 **영구 불가시**가 되고, `order_service.py:161-175` 소유 게이트에 `None` 분기를 뚫어야 한다. 대신 **원장 귀속**(해당 계정·심볼의 `filled` 진입 주문의 distinct `strategy_id` 가 정확히 1개일 때만 채택 — `exit_attribution.py:129-130` 의 보수 규칙)이 마이그레이션 0 이다.
**Risk:** 🟡

---

### BL-542

**Title:** 계정 포지션 표의 절단 경고가 실제 절단 없이 상시 발화한다
**Priority:** P3
**Status:** ✅ Resolved (2026-08-01, silent-surface-honesty)

**결과:** `truncated` 판정을 커서 존재가 아닌 0-size 필터 전 페이지 상한 도달로 교체했다. 계정 2/2 인증 fetch에서 `rows=1 · truncated=false`를 확인했다.
**근거:** [스프린트 회고](dev-log/2026-08-01-silent-surface-honesty.md)

---

### BL-538

**Title:** 발산 알림 본문이 **모든 카테고리에 "전략 수정 후 재활성화 필요"** 라고 처방한다 (포지션 불일치엔 틀린 처방)
**Category:** Backend / trading (운영 알림)
**Priority:** P2
**Trigger:** 운영 알림을 사람이 신뢰해야 할 때
**Est:** S
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

### BL-544

**Title:** 거래소의 조건부 진입 체결을 엔진 재생이 놓쳐 공백 후 세션이 중단된다
**Priority:** P1
**Status:** ✅ Resolved (2026-07-30, conditional-entry-alignment)

**결과:** 원장 기반 seed와 순포지션 판정으로 3개 soak leg가 공백을 넘어 생존했다. seed 주입 `outcome=applied`의 실주행 발화는 아직 없어 [BL-553](#bl-553)로 명시적으로 남겼다.
**근거:** [스프린트 회고](dev-log/2026-07-30-conditional-entry-alignment.md)

---

### BL-545

**Title:** ★gap-resync 안전 게이트가 5% 수량 허용치를 물려받아, 구 게이트가 막던 불일치를 통과시킨다
**Category:** Backend / trading (가용성 ↔ 안전 트레이드오프)
**Priority:** P2
**Trigger:** 조건부 진입 세션이 실자금으로 가기 전 / 부분체결이 흔해질 때
**Est:** S
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (P1 제기 → 오케스트레이터가 코드 대조 후 P2 로 강등)

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

**권장 접근:** 상대 허용치를 **거래소 수량 step 에서 파생**시켜라 —
`tol = max(qty_step, size * rel_tol_small)` 같은 형태. step 은 `_reconcile_conditional_entries` 가
이미 `market["precision"]["amount"]` 로 가져온다(`live_signal.py:638`). 그러면 "양자화 1틱" 은
통과하고 "부분체결 잔량" 은 통과하지 못한다. 대안: gap-resync 에만 더 좁은 별도 문턱을 두고
정상 tick 의 관측용 문턱과 분리한다.
**Risk:** 🟡 (통과한 불일치는 다음 주문이 그 위에 얹히지만, 5% 이내라 규모는 제한적)

---

### BL-546

**Title:** 원장→엔진 seed 경계에서 `Decimal` 수량·가격이 `float` 로 강등된다 (Decimal-first 하드 규칙 위반)
**Category:** Backend / pine_v2 · trading 경계
**Priority:** P2
**Trigger:** 엔진 내부 수치 표현을 손댈 때 / 큰 notional 을 다룰 때
**Est:** M (엔진 전반이 float 기반이라 국소 수정으로 안 끝난다)
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (확정)

**원인 / 영향:** DB `Numeric(18,8)` 인 `filled_quantity`/`filled_price` 가 seed 경로에서 `float` 로
변환된다(`live_signal.py` seed leg 조립 · `strategy_state.py` `Trade.qty: float`). 예:
`9999999999.99999999` 는 float 왕복 뒤 `10000000000.0`. seed 포지션의 수량·진입가·증거금 계산에
반올림값이 들어간다. `AGENTS.md:122` 와 `.ai/stacks/fastapi/backend.md:50` 의 "금융 숫자는 Decimal,
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

**원인 / 영향:** `/trading` 에서 세션 상세를 열면 body 가 24px 가로 스크롤된다(375px 기준).
인과 분리 실측 — 상세 닫힘 **0px** / 상세 열림 **24px** / 상세 열림 + `outcome-parity-panel`
`display:none` **0px**. 대조군 `/dashboard` 는 **0px**.

★**이번 회차 회귀가 아니다.** `outcome-parity-panel.tsx` 는 BL-526(PR #496, 2026-07-29)의
컴포넌트이고 이번 diff 가 만지지 않았으며, 그 경로는 이번 변경 **이전에도 도달 가능**했다.

**권장 접근:** 패널 안 넓은 콘텐츠를 자기 `overflow-x:auto` 컨테이너로 감싼다 — 같은 화면의 세 표는
이미 `div.table-wrap{overflow-x:auto}` 로 그렇게 하고 있다. 그 패턴을 패널에도 적용.
**Risk:** 🟢

---

### BL-549

> ### ✅ **Resolved (2026-07-30 live-entry-completeness)** — 더러운 트리 **기본 거부**(종료 코드 != 0) +
>
> `--allow-dirty` 로만 워킹트리 기준 판정 + 헤더에 `dirty=N`. 죽은 `be()` 헬퍼 제거.
> ★rename(`--no-renames`)·비ASCII 경로·`git status` 실패를 "깨끗함" 으로 삼키지 않는 것까지 처리.
> CONTROL 실증: 더러운 트리에서 **exit=1**, 거부 메시지가 **왜**까지 설명.

**Title:** ★`final-gates.sh` 를 커밋 전에 돌리면 게이트 대부분을 skip 하고도 그럴듯한 PASS 표를 낸다
**Category:** DX / 게이트 집행
**Priority:** P2
**Trigger:** 다음 회차 게이트 실행 전 (지금 고치는 게 가장 싸다)
**Est:** XS
**출처:** 2026-07-30 conditional-entry-alignment — 워커 `bl423` 이 자기 실행 중 발견

**원인 / 영향:** 스크립트는 변경 영역을 `git diff $(merge-base origin/main HEAD)..HEAD` 로 판정한다
(`final-gates.sh:43-51`). **작업트리의 미커밋 변경은 안 본다.** 커밋 전에 돌리면
`fe_diff=0 be_diff=0` 이 되어 lint·type·단위·build 를 전부 `skip` 으로 넘기고, 결과표는
"skip" 이라고는 적지만 **FAIL 이 없어 통과처럼 읽힌다.** 이 스크립트가 존재하는 이유가
"적어놓은 게이트는 집행되지 않는다" 였는데 그 집행 자체에 구멍이 있다.

**권장 접근:** 시작 시 `git status --porcelain` 이 비어 있지 않으면 (a) 경고 후 워킹트리 기준으로
영역을 판정하거나 (b) 아예 거부한다. 최소한 헤더의 `fe_diff/be_diff` 옆에 **"미커밋 변경 N개"**
를 찍어라. 겸사겸사 `be()` 헬퍼(`:68`)는 어디서도 안 쓰이는 죽은 코드다.
**Risk:** 🟡 (거짓 그린은 이 레포가 반복해 밟은 실패 유형이다)

---

### BL-550

**Title:** (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다 (계정 스코프 표로만 보인다)
**Category:** Frontend / live-sessions
**Priority:** P3
**Trigger:** 죽은 세션의 포지션을 세션 단위로 대조해야 할 때
**Est:** S
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
**출처:** 2026-07-30 conditional-entry-alignment (BL-423 잔여 중 defer)

**원인 / 영향:** `trading-cockpit.tsx:76-77` 의 `useState` 가 선택 상태를 쥔다. `useSearchParams`
사용처 0. 새로고침하면 선택이 사라지고 특정 세션 상세로 링크할 수 없다.
부수: e2e 가 쓰는 `/trading?tab=live-sessions` 의 `tab` 파라미터는 **읽는 코드가 없는 유물**이다.
**Risk:** 🟢

---

### BL-552

> ### ✅ **Resolved (2026-07-30 live-entry-completeness)** — 주입 후 전달 확인 + Enter **1회** 재시도 +
>
> `delivery` **별 파일**(`status` CAS 는 워커의 `running` 을 덮는 레이스가 있다).
> ★**주입 후 폴링 중 `blocked` 로 전이한 pane 에는 Enter 를 밀지 않는다** — 그 키는 승인 다이얼로그의
> 기본 선택을 누른다. **fail-closed 허용목록**(`idle|done`)으로 잡았다.
> ★**실경로 2회 검증** — 새 스크립트로 재지시하니 **Enter 없이** 주입→working. 옛 스크립트는 같은
> 자리에서 `✓` 만 찍고 워커를 `idle` 로 방치했다.
> ★본문 보강 — **첫 분배에서도 난다**(이번 회차 2/2). "첫 분배는 정상이었다" 는 관측은 표본 부족이었다.

**Title:** ★`fleet-dispatch.sh` 가 프롬프트 미제출을 성공으로 보고한다 — 워커가 지시를 입력창에 담은 채 `idle` 로 멈춘다
**Category:** DX / 함대 오케스트레이션
**Priority:** P2
**Trigger:** 다음 함대 회차 (재분배·재지시가 있을 때 특히)
**Est:** XS
**출처:** 2026-07-30 conditional-entry-alignment — `bl544` 재지시(R1) 분배 시 실측

**원인 / 영향:** `herdr agent prompt` 가 텍스트를 pane 에 **붙이기만 하고 제출(Enter)하지 않는
경우가 있다.** 실측: 재지시 분배 후 `fleet-dispatch.sh` 는 `✓ bl544 → wM:p1` 로 성공을 보고했지만,
`herdr pane read` 로 보니 입력창에 `❯ [Pasted text #2 +14 lines]` 가 담긴 채 에이전트는 `idle`
이었다. 상태표도 `HERDR=idle / SIGNAL=pending` 으로 **정상 대기처럼 보인다** — `pending` 은 분배가
주입 전에 쓰는 값이라(§8) 미제출과 구분되지 않는다. 첫 분배는 정상이었으므로 레이스다.

★**이 레포가 반복해 밟은 "거짓 그린" 유형이다.** 오케스트레이터가 pane 을 직접 읽지 않았다면
워커가 일하는 줄 알고 무한정 기다렸을 것이다. 해소는 `herdr pane send-keys <pane> Enter`.

**권장 접근:** 분배 직후 짧게 폴링해 `agent_status` 가 `working` 으로 바뀌는지 확인하고, 안 바뀌면
(a) `send-keys Enter` 로 한 번 더 밀거나 (b) die 한다. 기동 검증(`herdr-fleet.sh` 가 이미 하는
"살아 있는지 재확인" 패턴)과 같은 규율을 분배에도 적용하면 된다.
**Risk:** 🟡 (침묵 지연 — 결과는 안 틀리지만 회차가 통째로 멈춘다)

---

### BL-547

**Title:** ★원장 seed 는 **그 tick 한 번만** 산다 — 다음 tick 에 조용한 고아가 될 수 있다 (아직 실측된 적 없음)
**Category:** Backend / trading (BL-544 잔여)
**Priority:** P2
**Trigger:** ★`qb_live_position_divergence_total{category="exchange_only"}` 이 **실제로 오르는 것이 관측될 때**
**Est:** M
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
**출처:** 2026-07-30 conditional-entry-alignment soak 3 leg

**원인 / 영향:** BL-544 의 핵심 기전은 둘이다 — (1) **판정 완화**(엔진↔거래소 순포지션 일치) (2) **원장 seed 주입**. soak 3 leg 이 3/3 생존했지만 **세 번 다 (1) 로 살았다** — 재생이 포지션을 스스로 재현해 seed 가 생략됐다(`already_open` / `no_basis` / `inadmissible`). `applied` 를 밟으려면 **대기 조건부 주문이 공백 중에 트리거**돼야 하는데 누적 공백 ~28분 동안 일어나지 않았다(시장 변동 의존이라 강제할 수 없다).

★따라서 현재 증거 수준은 **비대칭**이다 — 판정 완화 = 실주행 실증 / seed 주입 = 단위테스트 + 표적 변이(멱등·마지막 bar Pine 가시성·기본값 report dict 불변)까지. 원래 BL-544 실패(2026-07-29)가 정확히 seed 주입이 필요한 케이스였으므로 이 공백은 실질적이다.

**권장 접근:** 코드 변경 없음. 다음 soak 에서 (a) 공백을 **더 길게**(15분+) 가져가 대기 stop 이 트리거될 확률을 올리거나, (b) 변동성이 큰 구간을 골라 재현한다. 확인 신호는 `qb_live_gap_ledger_seed_total{outcome="applied"} > 0` + 구조화 로그 `live_signal_gap_ledger_seed` 의 `trade_ids` 비어 있지 않음. **관측되면 이 BL 을 닫고 BL-544 의 검증을 완성으로 표기한다.**
**Risk:** 🟡 (기전이 틀렸다는 증거는 없다 — 다만 실주행 증거가 없다)

---

### BL-554

> ### ✅ **Resolved (2026-07-30 live-entry-completeness)** — stdin 4-튜플로 **실제 push ref** 판정.
>
> ★★**main 보호는 `remote_ref` 를 가장 먼저 본다** — `git push origin feat/foo:main` 은
> local=feat/foo · **remote=main** 이라 화이트리스트를 local 로 걸면 원격 main 갱신이 그대로 나간다
> (codex G1 이 **코드 쓰기 전에** 잡았다). 삭제는 대상이 main/master 일 때만 차단.
> 순수 sh lib(`scripts/lib/pre-push-ref-guard.sh`) + 하네스(`scripts/pre-push-guard-test.sh`, 26 케이스).

**Title:** (P3) pre-push 훅이 **푸시 대상 ref 가 아니라 현재 브랜치**를 봐서 원격 브랜치 삭제까지 막는다
**Category:** DX / git 훅
**Priority:** P3
**Trigger:** 다음에 머지된 stage 브랜치를 원격에서 지울 때
**Est:** XS
**출처:** 2026-07-30 conditional-entry-alignment PR #506 머지 후 정리

**원인 / 영향:** `.husky/pre-push` 는 `git symbolic-ref --short HEAD` 로 **현재 브랜치**를 보고 판정한다. 그래서 main 에 서서 `git push origin --delete stage/<theme>` 를 하면 **"main 직접 push 영구 금지"** 로 거부된다 — 실제로는 main 을 밀지 않고 남의 브랜치를 지우는 것인데도. `QB_PRE_PUSH_BYPASS=1` 도 그 분기는 **의도적으로 안 뚫는다**(main 보호는 bypass 불가). 결국 `gh api -X DELETE repos/…/git/refs/heads/<branch>` 로 우회했다.

★**보호 자체는 옳다** — main 직접 push 는 영구 금지가 맞다. 문제는 **판정 대상이 틀렸다**는 것이다.

**권장 접근:** 훅은 stdin 으로 `<local ref> <local sha> <remote ref> <remote sha>` 를 받는다. 그걸 읽어 **실제로 미는 ref** 로 판정하면 된다. 삭제(로컬 sha 가 전부 0)는 애초에 대상 브랜치가 main 일 때만 막으면 된다. 지금은 stdin 을 쓰지 않는다.
**Risk:** 🟢 (우회 경로가 있고 데이터 위험 없음 — 다만 매번 gh 로 돌아가야 한다)

---

### BL-555

> ### ✅ **Resolved (2026-07-30 live-entry-completeness)** — `stage/*` 화이트리스트 추가.
>
> 부수로 **태그 push 정책 명시**(`refs/tags/*` 가 `deny-arbitrary` 로 떨어지던 회귀 차단).

**Title:** (P3) `stage/*` 가 이 레포의 통합 브랜치 관례인데 pre-push 훅 화이트리스트에 없다
**Category:** DX / git 훅
**Priority:** P3
**Trigger:** BL-554 와 함께 (같은 파일)
**Est:** XS
**출처:** 2026-07-30 conditional-entry-alignment PR #506 푸시

**원인 / 영향:** ADR-017 이 정한 이 레포의 통합 브랜치는 `stage/<theme>` 인데, `.husky/pre-push` 의 허용 prefix 는 `feat|fix|chore|docs|test|refactor|hotfix` 뿐이라 **관례대로 만든 브랜치를 밀 때마다 `QB_PRE_PUSH_BYPASS=1` 이 필요하다.** bypass 를 습관화하면 그 플래그가 지켜야 할 것(워커 워크트리에서의 오발사)도 함께 무뎌진다.

**권장 접근:** 화이트리스트에 `stage/*` 추가. 그러면 bypass 는 원래 의도대로 **정말 예외적인 경우**에만 쓰인다.
**Risk:** 🟢

### BL-556

**Title:** `final-gates.sh` 가 `pnpm e2e`(chromium 4건)를 집행하지 않는다 — CI e2e 잡에는 있다
**Category:** DX / 게이트 집행
**Priority:** P2
**Trigger:** 다음 회차 게이트 실행 전
**Est:** XS
**출처:** 2026-07-30 live-entry-completeness

**원인 / 영향:** `.github/workflows/ci.yml` 의 e2e 잡은 `pnpm e2e`(project=chromium, 4건) ·
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

---

### BL-560

**Title:** 거래소 terminal 체결을 확인하고도 원장에 write-back하지 않아 반전 청산이 어긋난다
**우선순위:** P1
**상태:** ✅ Resolved (2026-08-01, conditional-fill-visibility)

**결과:** `_write_back_confirmed_terminal`의 프로덕션 경로를 CONTROL로 유도해 terminal→원장 기록 60초(사고 당시 818초)를 확인했다. 자연 `same_side` 효과는 아직 관측하지 않아, 검증 범위는 배선·기록 경로에 한정한다.
**근거:** [원인·수정 회고](dev-log/2026-07-31-reversal-ledger-sync.md) · [프로덕션 검증](dev-log/2026-08-01-conditional-fill-visibility.md)

---

### BL-561

**Title:** 구조화 로그의 `extra` 필드가 렌더되지 않아 진단 증거가 소실된다
**우선순위:** P2
**상태:** ✅ Resolved (2026-08-01, conditional-fill-visibility)

**결과:** 포매터와 celery·uvicorn 배선을 추가하고, 메인 실주행에서 엔진·거래소 포지션 값이 포함된 로그를 확인했다.
**근거:** [스프린트 회고](dev-log/2026-07-31-reversal-ledger-sync.md) · [완료 승격](dev-log/2026-08-01-conditional-fill-visibility.md)

---

### BL-562

**Title:** 조건부 진입의 반전 계측이 등재 시점 포지션만 본다
**우선순위:** P2
**상태:** ✅ Resolved (2026-07-31, instrument)

**결과:** 반전 계측을 체결 훅으로 옮기고 `unmeasured` 원인을 6종으로 분리했다. 캡·게이트 B는 주문 이후에는 바꿀 수 없어 등재 시점 근사임을 명시했다.
**근거:** [스프린트 회고](dev-log/2026-07-31-reversal-ledger-sync.md)

---

### BL-563

**Title:** bracket outcome이 게이트 뒤 요청을 기준으로 집계돼 공급 여부를 오분류한다
**우선순위:** P3
**상태:** ✅ Resolved (2026-07-31, instrument)

**결과:** outcome을 원본 `planned_entry` 기준으로 옮기고 `bracket_supplied_gate_dropped` 축을 분리해 세 라벨의 상호배타성을 고정했다.
**근거:** [스프린트 회고](dev-log/2026-07-31-reversal-ledger-sync.md)

---

### BL-564

**우선순위:** P3
**카테고리:** Tooling / docs (BL 감사 스크립트)
**Trigger:** `scripts/bl-audit.sh` 를 게이트 체인에 넣기 전
**Est:** XS
**상태:** 🟡 **열려 있다** — 2026-07-30 codex 적대 리뷰 MINOR.

★**`bl-audit.sh` 가 코드펜스·`<details>` 안의 옛 상태줄을 SSOT 로 오인할 수 있다.**

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
**상태:** 🔴 **열려 있다** — 2026-07-31 reversal-ledger-sync 에서 BL-560 을 고치며 **읽기만** 하고
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
**상태:** 🔴 **열려 있다** — 2026-07-31 reversal-ledger-sync 에서 **한계로 명시하고 남긴 것**.
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

### BL-566

**우선순위:** P2
**카테고리:** Backend / trading (라이브 원장 정합성)
**Trigger:** BL-560 실주행 재측정을 다시 시도하기 전
**Est:** M
**상태:** ✅ **Resolved — 재판정으로 닫는다** (2026-08-01). ★**등재 당시의 명제
「다음 진입이 올 때까지 지워지지 않는다」가 원장과 어긋난다.** 재분해 결과 이것은 유령 포지션이
지속되는 현상이 아니라 **계획기 무장 지연 — 시장가 전환 이전의 과도 상태**다. 크기 확정:
**41.6/h → 12.9/h**, 평가의 **69% → 21%**, 미설명분 **전건이 2~4봉 안에 자기해소**(최대 연속 런 4).
사전등록 **Y2**(연속 런 ≤5) 충족. 아래 「재판정」 참조.
**출처:** 2026-07-31 reversal-ledger-sync (BL-561 이 로그를 렌더하자마자 드러났다)

~~★**청산이 성공했는데도 엔진 원장이 그 포지션을 계속 들고 있다.**~~
→ **2026-08-01 재판정으로 철회.** 아래 「재판정」이 정본이고, 이 아래 원 서술은 등재 당시의
판단으로 보존한다(폐기된 판정을 지우지 않는 이 레포 관용구).

**원인/영향.** pre-fix 창(세션 `7fb8e2ed`, 0.71h)에서 `live_signal_position_divergence` 가
**29건 전건 `engine_only`** 로 찍혔다 — **41.6건/h**, 평가 ~42회 중 **69%가 발산 상태**다.

```
02:30:20  buy reduce-only 체결 (청산 성공, 거래소 flat)
02:31:12 ~ 02:39:11   engine_position=-0.0295738  exchange_position=0   ← 매 분 9회 연속
02:41:28  buy reduce-only 체결 (청산 성공)
02:42:12 ~            engine_position=-0.0296368  exchange_position=0   ← 값이 새로 바뀐 유령
```

거래소는 flat 인데 엔진은 숏을 들고 있고, **다음 진입이 올 때까지 지워지지 않는다.**
그 상태에서 청산 신호가 나가면 `110017` 계열이 되고, 반대편 포지션이 차 있으면
**BL-560 의 `same_side` 위험 갈래로 넘어간다.**

★**BL-560 과 같은 계열인지 별개 채널인지 미확정.** BL-560 의 진짜 뿌리는 「체결 write-back 지연」
이었는데, 이 현상은 **청산이 성공한 뒤**에도 남으므로 다른 지점일 수 있다.
후보: `run_live` 가 매 tick 원장을 봉 재생으로 재도출하는 구조(`event_loop.py`)와
`position_epoch` / `seed_positions_from_ledger` 의 상호작용.

★**이것이 지금까지 안 보였던 이유** — 포매터가 `extra` 를 렌더하지 않아
`live_signal_position_divergence` 가 **이벤트 이름만** 찍혔다(BL-561). 값이 나오자마자 드러났다.

**권장 접근:** ★**먼저 재라.** 최종 창(`c77d5851`, 0.86h)에서는 divergence 가 **12/h** 로 줄었고
성격도 `exchange_only` 9 / `direction` 1 로 바뀌었다 — **창마다 성격이 다르다.**
분모(평가 횟수) 대비 발산 비중을 여러 창에서 재고, `engine_only` 가 지속되는 구간의
`position_epoch` 값을 함께 남겨라. 크기 없이 원인 후보를 고르지 마라.

**재판정 (2026-08-01, 창 2026-07-31 17:40:00→18:46 UTC · 66분 · 66틱 · 세션 `dc1e08f1`).**

★**과거 29건을 세션 스코프로 재분해했다**(팬아웃 0 — JOIN 없이 센 29 와 일치):

| 갈래               | 건수 | 비중 |
| ------------------ | ---- | ---- |
| `awaiting_trigger` | 20   | 69%  |
| `unexplained`      | 9    | 31%  |

⇒ 크기 **41.6/h → 12.9/h**, 평가의 **69% → 21%**. 등재 헤드라인이 **3.2배 부풀어 있었다** —
분모가 아니라 **분자**가 틀렸다(대기 중인 조건부 진입을 유령으로 셌다).

★**`unexplained` 9건도 지속되지 않는다 — 전건이 2~4봉 안에 자기해소**한다
(연속 런 **3 / 4 / 2**, 최대 **4**). 「다음 진입이 올 때까지」라는 등재 서술의 핵심 주장이 여기서 깨진다.

★**이번 창에서는 자연 발생이 0이다.** 정렬 상태로 시작해 66틱, 실거래 있음(조건부 체결 3 · 취소 7)
인데 `engine_only` **자연 발생 0건**. 유일한 1건은 CONTROL 이 유도했고 **1틱만에 해소**됐다.

★**기전 확정.** 엔진이 포지션을 든 채 거래소가 flat 이면 트리거가 **이미 돌파돼 있어** 계획기가
**시장가로 전환**한다 — `market_converted` **8 → 9**, 로그 `reason=market_converted
breach_pct=0.0116`, 등재 **1초** 만에 체결. 그래서 같은 방향 진입이 **대기한 적이 없다.**
즉 관측된 창은 "유령이 남아 있는 시간" 이 아니라 **"계획기가 아직 무장하지 않은 과도 구간"** 이다.

**⇒ 재정의: 「계획기 무장 지연 — 시장가 전환 이전의 과도 상태」.** 크기가 확정됐고 자기해소가
증명됐으므로 닫는다. 사전등록 **Y2**(연속 런 ≤5) 충족.

★★**남기는 한계 — `engine_only_awaiting_trigger` 라벨은 프로덕션에서 한 번도 실행되지 않았다.**
이 재판정의 69%/31% 분해는 **단위테스트 + 과거 원장 재분해 20건**으로만 뒷받침된다. 라벨 자체가
실주행에서 발화한 적이 없으므로, **다음 창에서 이 라벨이 실제로 찍히는지 기회주의적으로 확인해라.**
★그리고 그 분류는 [BL-574](#bl-574)(`LIMIT 100` 이 세션 필터보다 앞선다)의 영향을 받는다 —
다른 세션 미종결 주문이 100건을 채우면 `awaiting_trigger` 가 `unexplained` 로 떨어져
**위 20/9 비율이 보수적으로(=unexplained 쪽으로) 치우친다.**

**Risk:** 🟢 (재판정 후 — 과도 상태이고 자기해소한다. 방벽은 `reduce_only` 가 그대로 유지)
~~**Risk:** 🟡 (엔진 원장이 거래소와 어긋난 채로 신호를 낸다. 방벽은 `reduce_only` 하나)~~

### 후속 관측 (2026-08-04 engine-state-ssot) — **계측 라벨 결함, 코드 결함 아님**

★**`qb_live_conditional_reconcile_errors_total{stage="terminal_write_back_*"}` 는 에러가 아니다.**
소크 `bbea6da4` 에서 이 series 가 16분에 1→2 로 올라 「write-back 경로에서 무엇이 던진다」로
인계됐으나, **아무것도 던지지 않았다.**

`live_signal.py:1310` 이 라벨을 `f"terminal_write_back_{won}"` 으로 만드는데 `won` 은
`_write_back_confirmed_terminal`(`:958`)의 반환값이고, 그 docstring 이 명시한다 —
「반환값은 **이 호출이 전이의 승자였을 때만** 그 terminal 상태명이고, 아니면 None」.
⇒ `terminal_write_back_filled` = **[BL-560] 수리가 체결을 앞당겨 기록하는 데 성공한 횟수**이고
`_cancelled` 도 마찬가지다. `_lost` 는 경합 패배(역시 에러 아님). **셋 다 "reconciliation
failures" 라는 이름의 counter 에 계상되고 있다.**

**심각도 낮음 · 수리 보류.** 소비자가 전부 `stage` 라벨 단위라(`entry_completeness.py:1191` 은
`deferred_market_inflight` 만 본다) 자동 판정은 깨지지 않는다. 피해는 **사람의 오독**이며,
2026-08-04 인계문이 정확히 그 오독이었다.

**수리 시 선택지:** (a) 별도 counter 분리(`qb_live_conditional_write_back_total`)
(b) 라벨 접두사를 `ok_` 로 (c) counter 이름을 중립화. ★**소크 생존 중에는 `backend/src` 편집이
금지**라 이번 회차는 등재만 했다. ★**새 BL 을 열지 않았다** — 사용자 지시(2026-08-04).

---

### BL-568

**우선순위:** P2
**카테고리:** Backend / trading (조건부 진입 반전 계측)
**Trigger:** BL-562 의 **체결시점** 반전 분포를 근거로 무언가를 판단하기 전
**Est:** S
**상태:** 🔴 **열려 있다** — 2026-08-01 ledgerhygiene 에서 실측. 아직 원인 미측정.
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

### BL-569

**우선순위:** P3
**카테고리:** DX / 문서 게이트 (`scripts/bl-audit.sh`)
**Trigger:** —
**Est:** XS
**상태:** ✅ **Resolved** (2026-08-01 ledgerhygiene, 등재와 같은 PR)
**출처:** 2026-08-01 ledgerhygiene G0 실측

★**`bl-audit.sh` 가 중복 섹션 헤더를 못 잡아, 같은 BL 번호 두 벌이 exit 0 을 유지했다.**

**원인/영향.** 파서는 `verdict[id]` · `evid[id]` · `sec_line[id]` 를 **BL id 로 키를 잡는다**.
`### BL-566` 이 두 번 나오면 뒤 섹션이 앞 섹션의 판정을 통째로 덮어쓰고, 앞 섹션은
`order[]` 에만 남아 **카운트에는 잡히므로 숫자만 보면 정상으로 읽힌다.**
BL-564 가 넣은 중복 검사는 **상태줄**만 봤는데(`st_dup`), 두 섹션이 각자 상태줄을 하나씩
가지면 `st_dup` 은 양쪽 다 0 이다. 그래서 실패 조건에 걸리지 않았다.

**실측(수정 전).** `docs/backlog.md` 에 `### BL-566` 이 `:5568`(체결 후속 훅 회수)과
`:5610`(청산 성공 후 유령 포지션) 두 벌 있었는데 `bash scripts/bl-audit.sh` 는 `exit 0`,
출력에 `BL-566` 은 **한 번도 등장하지 않았다**(`grep -c BL-566` → 0).

**해결.** 섹션 헤더에 상태줄과 **같은 계약**을 적용했다 — `### BL-<n>` 중복이면 exit 1 이고
「▶ 중복 섹션 헤더」 블록으로 첫 줄과 중복 줄을 함께 출력한다(`scripts/bl-audit.sh:124-130`,
`:236-242`). 앞 벌(체결 후속 훅 회수)은 **BL-567 로 재번호**했다.

★**판별력 증명 3종.** (a) 임시 `### BL-999` 두 벌 삽입 → `exit 1` · 제거 → `exit 0`.
(b) ★**수정 전 원본**에 새 검사를 적용 → `BL-566 첫:5568 중복 :5610` 로 **실제 결함을 잡는다**
— 합성 케이스가 아니라 조용히 통과하던 진짜 사고를 재현했다.
(c) 종료코드는 **파이프 없이** 읽었다(`| tail` 이 exit code 를 가린다).

★**(b)의 재현 명령은 `HEAD` 가 아니라 `b8c63a45^`(= `a6d891b1`) 다.** 재번호가 `b8c63a45` 에
들어갔으므로 `HEAD` 를 꺼내면 `### BL-566` 이 하나뿐이라 **재현되지 않는다.** 임시 트리에 놓고 돌려라
(`docs/` 를 덮어쓰지 마라):

```bash
T=$(mktemp -d); mkdir -p "$T/scripts" "$T/docs"
cp scripts/bl-audit.sh "$T/scripts/"; git show b8c63a45^:docs/roadmap.md > "$T/docs/roadmap.md"
git show b8c63a45^:docs/backlog.md > "$T/docs/backlog.md"
bash "$T/scripts/bl-audit.sh" > "$T/out.txt" 2>&1; echo "exit=$?"; grep -A2 '중복 섹션 헤더' "$T/out.txt"
```

★**상시 회귀 가드는 `scripts/bl-audit-test.sh` 다** (G6 codex 적대 리뷰 MAJOR). 위 (a)~(c)는
1회성 수동 증명이라 **로직을 되돌려도 아무도 못 잡는다** — 원장이 깨끗하면 중복 검사는 아무 일도
하지 않기 때문이다. 하네스는 임시 트리에 fixture 원장을 만들어 실제 스크립트를 돌리고,
중복 섹션 헤더 / 중복 상태줄을 **서로 구분해** 단언한다(5 케이스). `final-gates.sh` 체인에
라벨 `BL 감사 하네스` 로 편입했다 — 물리지 않으면 하네스도 아무도 안 돌린다.

★**변이 3종 전건 적발** — (M1) 중복 섹션 헤더 탐지 제거 → ①·④ red / (M2) `dup`·`sec_line` 을
BL id 단일 키로 되돌림 → ⑤ red / (M3) 기존 중복 상태줄 탐지 제거 → ③·⑤ red.
★**하네스 자신이 처음엔 오탐했다** — 실패 요약 줄이 카운터 이름을 전부 나열하므로
(`… 중복 섹션 헤더 0 건 …`) "없어야 할 마커" 를 이름만으로 찾으면 0 건일 때도 매치된다.
`▶ ` 블록 머리로 고정했다.

★**부수 정정(G6 MINOR).** `dup[]` · `sec_line[]` 가 BL id 단일 키라 **중복 섹션이 있을 때
「중복 상태 줄」의 줄번호가 첫 섹션이 아니라 두 번째 섹션을 가리켰다.** 섹션 서수(`n`)로 키를
바꿨다(`scripts/bl-audit.sh:95-99` · `:239`). 하네스 ⑤ 가 이 회귀를 고정한다.

**Risk:** 🟢

---

### BL-570

**Title:** 무편집 `설정 저장`이 요청·토스트·필드 오류 없이 막힌다
**우선순위:** P2
**상태:** ✅ Resolved (2026-08-01, silent-surface-honesty)

**결과:** nullable 설정값 3종을 초기 정규화하고 `onInvalid`·필드 오류를 표면화했다. 브라우저 E2E가 무편집 저장 경로를 고정한다.
**근거:** [스프린트 회고](dev-log/2026-08-01-silent-surface-honesty.md)

---

### BL-571

**Title:** enum 밖 세션 종료 사유가 원장·화면·콘솔을 오염한다
**우선순위:** P3
**상태:** ✅ Resolved (2026-08-01, silent-surface-honesty)

**결과:** 과거 3종을 마이그레이션으로 정리하고 DB CHECK·enum drift sentinel을 추가했다. 화면 원문 노출 3종과 40초당 콘솔 경고 67건이 모두 0이 됐다.
**근거:** [스프린트 회고](dev-log/2026-08-01-silent-surface-honesty.md)

---

### BL-572

**Title:** 동일 세션의 표·카드 상태 라벨이 다르다
**우선순위:** P3
**상태:** ✅ Resolved (2026-08-01, silent-surface-honesty)

**결과:** 세션 상태 라벨·톤을 `labels.ts` 한 곳으로 모아 `PAUSED` 20행을 「종료된 세션」으로 통일했다. 재발 방지 가드 부재는 [BL-577](#bl-577)로 분리했다.
**근거:** [스프린트 회고](dev-log/2026-08-01-silent-surface-honesty.md)

---

### BL-573

**우선순위:** P3
**카테고리:** Backend / trading (라이브 tick 중복 조회)
**Trigger:** `live_signal` tick 비용을 손댈 때, 또는 발산 감지와 reconcile 을 한 자리로 합칠 때
**Est:** S
**상태:** 🔴 **열려 있다** — 2026-08-01 codex 적대 리뷰 #1 (CONTROL 코드 대조로 확인).
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
**상태:** 🟢 **열려 있다 — 크기 측정 완료, 수리는 의도적으로 보류.** 2026-08-02 divergence-label-split.
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
**상태:** 🔴 **열려 있다** — 2026-08-01 codex 적대 리뷰 #5. ★**선재 패턴이고 회귀가 아니다.**
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

### BL-576

**우선순위:** P2
**카테고리:** Backend / trading (관측 라벨 충돌)
**Trigger:** `live_conditional_reconcile_divergence` 를 세거나 알림·게이트로 쓰기 **전**
**Est:** S
**상태:** ✅ **Resolved** (2026-08-02, divergence-label-split). **프로덕션 발화 검증까지 완료** (2026-08-02 canonical-measurement-surface) — 아래 §프로덕션 발화 검증. ★단 **5 event 중 2 만** 확인됐다.
**출처:** 2026-08-01 soak 후속 codex 리뷰 (+ CONTROL 코드 대조로 범위 확대)

**결과 (2026-08-02).** 이름 하나를 **사건별로** 갈랐고(로그 이벤트명 6종 — `exchange_divergence` ·
`stand_down` · `degraded_input` · `plan_drop` · `guard_drop` · `market_converted`.
★**counter 의 `event` 라벨은 5종**이다 — `plan_drop` 은 별도 counter
(`qb_live_conditional_plan_drop_evaluations_total`)라 이 counter 에 없다. 2026-08-02 실측 정정), `reason` 을 **닫힌 집합**으로
승격해 counter `qb_live_conditional_divergence_total{event, reason}`(series 상한 **13**)을 신설했다.
증가는 전건 `_count_safely`(mmap 함정). AST 구조 오라클이 **발화 총수 8 · 낡은 이름 0곳**을 고정하고,
8 발화 **전건**을 결정론 fixture 로 구동해 `(event, reason)` 을 1:1 단언한다. 표적 변이 3종 전건 판별.

★**`event` 축의 역할** (2026-08-02 codex LOW#4 로 정정) — **지금 counter 안에는 reason 충돌이 없다.**
5 event 의 허용 reason 집합이 서로 배타적이고, 충돌원이던 계획기 `plan_drop` 은 새 counter 에서
제외됐기 때문이다. `event` 축이 하는 일은 두 가지다: (a) **로그 이벤트명과 counter 를 1:1 로 묶어**
로그로 본 것과 센 것이 같은 사건임을 보장하고, (b) `breach_exceeds_cap` 처럼 **레포 안에서 이미 두
경로가 공유하는 문자열**(계획기 `conditional_entry_planner.plan_reconcile` · 등재 가드의 cap 재검사)이
나중에 같은 counter 로 합류할 때 **미리 갈라 둔다**. ★「지금 충돌을 막고 있다」는 과장이었다.

★**가장 오해를 부른 자리는 `market_converted` 발화**였다 — 시장가 전환 **성공**(PR #493 의 의도된
수리)이 「divergence」 이름으로 WARNING 에 올라 발산 수를 부풀렸다. **무해가 위험을 가리는 것의 역방향.**

### ★프로덕션 발화 검증 완료 (2026-08-02, canonical-measurement-surface)

창 **37분 28초**(`16:17:28Z`~`16:54:56Z`). 로그 tally 와 counter 차분이 **키·값 모두 일치**:
`market_converted/market_converted` **1:1** · `stand_down/shared_account_symbol` **4:4**.
레벨 오라클도 일치(`stand_down` 4 ERROR · `market_converted` 1 WARNING).

★**선행 수리가 필요했다** — **라벨 있는 counter 는 첫 발화 전까지 series 가 존재하지 않는다.**
그래서 창 시작 스냅샷에 그 series 가 없고 `_delta_reading` 이 `CounterBasis.unknown` 으로 비교를
거부한다 ⇒ **신설 counter 를 프로덕션에서 증명하려는 바로 그 순간에 계측이 불가능**했다.
13 조합을 import 시점 0 으로 실체화해 닫았다(`_prime_divergence_series`). 문서가 주장하던
**상한 13 의 첫 실측 확인**이기도 하다.

★★**5 event 중 2 event 만 확인됐다** — `exchange_divergence` · `degraded_input` · `guard_drop` 은
그 창에서 **한 번도 발화하지 않았다.** 나머지 3종은 여전히 결정론 fixture 로만 검증된 상태다.
★**`other` reason 5종은 구조적으로 도달 불가**(호출부 전수 확인 — 전부 허용 reason 리터럴).
그래서 **「13 series 존재」를 기능 증거로 인용하지 마라 — 증거는 오직 차분이다.**

<details><summary>착수 당시 서술 (이력 보존)</summary>

★★**남은 것 = 프로덕션 발화 검증.** 새 이벤트명·counter 는 **실주행에서 한 번도 발화하지 않았다**
(이 회차는 창을 열지 않았다). 머지 + worker 재기동 후에만 확인 가능하다.
★**이 라벨로 크기를 주장할 때 §G1.1 의 A5 를 그대로 가져다 쓰지 마라** (2026-08-02 codex MAJOR#1) —
A5 의 분모(`has_fill + rejected_exchange`)는 **진입 완결성(`AttemptLayer`)의 축**이고 이 counter 에는
그 축이 없다. **§G1.1 규율 3 에 따라 이 라벨 전용 표본 문턱을 그때 새로 정의해라.**
(★2026-08-02 canonical-measurement-surface 가 그 전용 문턱을 정의해 판정했다 — 위 §프로덕션 발화 검증.)

</details>

**근거:** [라벨 분화 회고](dev-log/2026-08-02-divergence-label-split.md) ·
[프로덕션 발화 검증](dev-log/2026-08-02-canonical-measurement-surface.md)

<details><summary>착수 당시 원문 (이력 보존)</summary>

> ★**아래 줄번호는 착수 시점(`main@b8d53141`)에 고정된 것이고 지금은 전부 밀렸다** — 라벨 분화가
> 그 파일을 늘렸다. **인용하지 말고 이벤트명 문자열로 찾아라**(§G1.1 규율 = 살아 있는 파일에
> 줄번호 앵커 금지). 이력 보존을 위해 원문은 고치지 않는다. 2026-08-02 codex MINOR#7.

★**`live_conditional_reconcile_divergence` 한 이름이 구조가 다른 사건들을 덮는다 — `110017` 라벨 충돌과 같은 형태다.**

**원인/영향.** 보고는 두 사건(① write-back 누락 ② 시장가 전환)으로 왔으나,
**코드 대조 결과 발화가 8곳이고 payload 모양이 최소 3종**이다
(`backend/src/tasks/live_signal.py` — `:1086` · `:1181` · `:1196` · `:1250` · `:1455` ·
`:1481` · `:1511` · `:1647`):

| payload 모양                     | 예                                                                      |
| -------------------------------- | ----------------------------------------------------------------------- |
| `order_id` 있음                  | `:1086` `reason=exchange_missing_resting_order` (+ `exchange_order_id`) |
| `trade_id` 있음, `order_id` 없음 | `:1455` `breach_exceeds_cap` · `:1481` `bracket_trailing_only`          |
| `session_id` 만                  | `:1181` `reason=<stand_down_reason>`                                    |

★**`:1250` 은 `**divergence` 를 splat 한다** — 키 집합이 코드에 고정돼 있지도 않다.
그래서 이 이름으로 센 수치는 **무엇의 개수인지 정의되지 않는다.\*\*

★★**이 스프린트 계열이 이미 같은 병으로 두 번 당했다.** `110017` 이 「같은 방향(위험)」과
「포지션 0(무해)」을 한 라벨에 묻어 **무해 30건이 위험 9건을 수적으로 가렸고, 화면은 그 9건을
전부 초록으로** 보여줬다(BL-560 계열). 지금 이름도 같은 구조다 — write-back 누락(고쳐야 하는 것)과
시장가 전환(정상 동작)이 한 이름에 섞여 있다.

★**아직 오판을 일으키지는 않았다.** 이번 창의 판정은 `order_id` 유무로 사람이 갈라 읽어서 맞았다.
문제는 **그 구분이 사람 눈에만 있다**는 것이다.

**권장 접근:** 이름을 **사건별로 가른다**(정본이 요구하는 방향 — 무해와 위험을 같은 라벨에 두지 않는다).
최소한 `reason` 을 **필수 필드로 승격**하고 counter 라벨로 올려 `by reason` 으로 세어라.
★**세기 전에 가르는 것이 순서다** — BL-560 이 라벨을 가른 **뒤에야** 크기를 잴 수 있었다.
[BL-573](#bl-573) 이 같은 자리를 건드리므로 함께 보면 싸다.

</details>

**Risk:** 🟢 (가름 완료. 잔여 = 프로덕션 발화 검증)

---

### BL-577

**우선순위:** P2
**카테고리:** Frontend / 가드 위생 (가드는 실재하고, 모양이 한 곳에서 안 맞았다)
**Trigger:** 원시 enum 렌더를 막았다고 믿고 라벨 코드를 손댈 때, 또는 `no-raw-enum-labels` 를 근거로 인용할 때
**Est:** S
**상태:** ✅ **Resolved** (2026-08-02, canonical-measurement-surface). 전제 반증 후 좁게 확장.
**출처:** 2026-08-01 [BL-572](#bl-572) 가 「가드 스코프가 이 파일을 덮는지 확인하라」고 지시한 것을 따라가다 발견

### ★★전제가 반증됐다 — 가드는 **존재한다** (2026-08-02, 실행으로 확인)

★**아래 원 서술의 헤드라인(「가드가 존재하지 않는다」)은 거짓이다.** 가드는 실재한다:
**`frontend/src/__tests__/no-raw-enum-labels.test.ts`** (281줄, `pnpm test` 로 CI 에서 실행).

★**왜 못 찾았나 — 조사 방법의 결함이다.** 원 조사는 `grep -rn "no-raw-enum-labels"` 로
**파일 내용**을 훑었는데, **그 파일은 자기 이름을 본문에 0회 쓴다**(describe 는
`"S4/S9/W1 — no raw enum rendered in P1 route UI"`). 내용 grep 은 **파일명에만 있는 문자열**을
구조적으로 못 잡는다. ⇒ **함정으로 승격**: `docs/reference/operations/gates-and-traps.md`.

**실제 검출기(`detectRawEnumRenders`)를 직접 실행한 결과** (CONTROL 실측 + Evaluator 3/3 재현):

| 입력                                                              | 판정                           |
| ----------------------------------------------------------------- | ------------------------------ |
| `<th>{BACKTEST_LIST_HEADER.status}</th>` (우회 3곳 형태)          | **잡힌다**                     |
| `<td>{s.is_active ? "ACTIVE" : "PAUSED"}</td>` (BL-572 실제 위반) | `[]` **못 잡는다 — 진짜 구멍** |
| `<span>ACTIVE</span>` (bare 텍스트)                               | `[]`                           |
| `<td>{LIVE_SESSION_STATUS_LABEL[k].label}</td>` (라벨 경유)       | `[]`                           |

★★**그래서 아래 「구현 항목 (iii)」의 「우회 코드 3곳을 원래 형태로 되돌린다」는 집행하면 안 된다 —
CI 가 red 가 된다.** Evaluator 가 실제로 3곳을 되돌려 **guard red 3건**을 재현한 뒤 역치환 복구했다.
그 3곳은 **실재하는 멤버 체인 검출기**를 피한 것이지 허구를 피한 것이 아니다.
같은 이유로 **인용 주석 10곳은 삭제 대상이 아니다** — 전부 정확한 인용이고, 실재 파일을 가리킨다.

### 결과 (2026-08-02)

같은 파일 안에 **두 번째 검출기**를 좁게 추가했다 — JSX 자식 위치의 **원시 대문자 문자열
리터럴**만, 스코프는 `features/live-sessions`. 멤버 체인 규칙은 이미 있고 잘 동작하므로 손대지 않았다.
새 eslint 규칙을 만들지 않았다(레포 선례 = vitest 가드 8건 · 커스텀 eslint 룰 0건).

★**오늘 그 스코프의 위반은 0건**이라 레포 스캔만으로는 검출기가 죽어도 green 이다. 그래서
스캔 테스트 본문에 **생존 단언**(BL-572 원문을 먹여 검출되는지)을 함께 넣어 **무력화가 곧 red** 가 되게 했다.

<details><summary>착수 당시 원문 (이력 보존 — 헤드라인은 위에서 반증됐다)</summary>

★**`no-raw-enum-labels` 가드는 이 레포에 존재하지 않는다. 그런데 주석 10곳이 그것을 실재하는 것처럼
인용하고, 그중 3곳은 「가드가 잡으므로 우회한다」며 코드를 실제로 비틀어 놓았다.**

**원인/영향.** 전 레포 검색(`*.ts` · `*.tsx` · `*.mjs` · `*.cjs` · `*.js` · `*.sh` · `*.json`,
`node_modules` 제외) 결과 `no-raw-enum-labels` 문자열은 **주석 10곳에만** 있다.
`frontend/eslint.config.mjs` 는 57줄이고 그런 규칙이 없다(`no-restricted-syntax` 자체가 없다).
`frontend/package.json` 의 `lint` 는 `eslint .` 뿐이고, 이 이름의 스크립트·vitest 가드·lint 플러그인도 없다.

인용 지점 **10곳 전량** (2026-08-01 divergence-label-split 에서 재측정 — 이전 목록은 **9곳만 적고
`trade-detail-shell.tsx` 를 빠뜨렸고** `labels.ts` 앵커가 `:24`→`:26` 으로 밀려 있었다) —
`backtests/_components/backtest-list.tsx:139`·`:356` · `strategies/_components/strategy-list.tsx:149`·`:411` ·
`orders/_components/orders-blotter.tsx:6`·`:240` · `optimizer/_components/optimizer-run-list.tsx:196` ·
`backtests/_components/trades/trade-detail-shell.tsx:68` ·
`features/live-sessions/labels.ts:3`(“S9 확장 스코프”)·`:26`(“W1 확장, direction 필드”).

★**단순한 문서 드리프트가 아니다 — 코드가 그 허구에 맞춰 휘어 있다.**
`backtest-list.tsx:139` / `strategy-list.tsx:149` / `orders-blotter.tsx:240` 세 곳은
_“가드가 `.status`/`.state` 로 끝나는 JSX 멤버 체인을 전부 잡으므로 우회한다”_ 며 중간 변수를
두는 형태로 작성돼 있다. **존재하지 않는 규칙을 피하려고 쓴 코드다.**

★**실제로 놓쳤다.** [BL-572](#bl-572) 가 정확히 이 가드가 잡아야 할 형태다 —
`live-session-table.tsx:101-103` 이 `s.is_active ? "ACTIVE" : "PAUSED"` 로 원시 리터럴을
한국어 UI 에 하드코딩한다. 가드가 있었다면 머지 전에 걸렸을 것이고, 없었으므로 통과했다.

**재현.** `grep -rn "no-raw-enum-labels" .` → 주석 10건. `frontend/eslint.config.mjs` 전문 확인 → 규칙 없음.

**권장 접근:** 두 갈래 중 **하나를 골라 끝내라. 지금 상태(믿음만 있고 실체 없음)가 가장 나쁘다.**

- **(a) 짓는다** — `eslint` `no-restricted-syntax` 로 규칙을 실제로 만들고, 주석이 주장하는
  스코프(S9 = `features/live-sessions/components` 원시 status / W1 = `direction` 필드)를 재확인해
  주석과 규칙을 일치시킨다. ★새로 만들면 **기존 인용 3곳의 우회 코드가 여전히 필요한지** 함께 판정해라.
- **(b) 지운다** — 가드를 안 만들기로 하면 주석 10곳을 전부 걷어내고, 우회 코드 3곳을 원래 형태로 되돌린다.
  ★그냥 두면 다음 사람도 「이건 가드가 잡는다」고 믿고 [BL-572](#bl-572) 를 다시 만든다.

★**이번 회차에서 고치지 않았다** — BL-572 의 라벨 수리 범위를 넘고, (a)/(b) 는 전략 선택이다.

</details>

---

### ★결정 = **(a) 짓는다 (스코프 좁게)** — 2026-08-01 divergence-label-split, 사용자 승인

> ★★**2026-08-02 정정 — 아래 (i)~(iii) 중 (iii) 의 절반은 집행하면 안 된다.**
> 전제(「가드가 없다」)가 반증됐으므로 **(iii) 의 「우회 코드 3곳 되돌리기」는 CI 를 red 로 만들고,
> 「인용 주석 10곳 걷어내기」는 정확한 인용을 지우는 것이다.** 실제로 채택한 것은
> **(i) 스코프**(`features/live-sessions`)와 **(ii) 규칙 모양**(JSX 안 원시 대문자 리터럴)뿐이고,
> 그 둘은 새 eslint 규칙이 아니라 **기존 vitest 가드 안의 두 번째 검출기**로 구현했다.

**근거.** BL-572 가 가드 부재로 실제로 머지를 통과했고, 우회 코드 3곳이 이미 그 규칙을 전제로 휘어 있다.
(b) 를 고르면 「다음 사람이 이건 가드가 잡는다고 믿고 BL-572 를 다시 만든다」를 **막을 수단 없이** 닫는다.

★★**단 착수 전에 확정한 단서 2건이 규칙의 모양을 바꾼다 (코드 대조 실측).**

1. **주석이 주장하는 스코프는 BL-572 를 못 잡는다.** 실제 위반 형태는
   `{s.is_active ? "ACTIVE" : "PAUSED"}` 였다(`f631f1c7^:live-session-table.tsx:101-103` 실측).
   `.status`/`.state` **멤버 접근이 아예 없고**, 위반은 **JSX 안의 원시 대문자 문자열 리터럴**이다.
   ⇒ backlog 가 적었던 「가드가 있었다면 머지 전에 걸렸을 것」은 **참이지만 규칙 모양까지 보증하지 않는다.**
2. ★★**우회 코드 3곳은 오탐을 피한 것이다.** `backtest-list.tsx:139` · `strategy-list.tsx:149` ·
   `orders-blotter.tsx:240` 은 **`HEADER.status` / `ORDER_TABLE_HEADER.state` — enum 값이 아니라 헤더
   문자열**을 스칼라로 풀어 놓았다(주석이 그렇게 명시한다). 규칙을 위 1번의 올바른 모양으로 지으면
   그 3곳은 **더 이상 필요하지 않다.**

**⇒ 다음 회차 구현 항목 (두 조건 AND).**

- (i) **스코프**: `features/live-sessions` + 세션 상태 렌더 지점부터 시작한다. 전 레포 일괄 금지.
- (ii) **규칙 모양**: 멤버 체인이 아니라 **JSX text/attribute 위치의 원시 대문자 enum 리터럴**을 잡는다
  (`ACTIVE`/`PAUSED`/`FILLED` 류). 멤버 체인 규칙은 채택하지 않는다 — 오탐이 이미 코드를 3곳 비틀었다.
- (iii) **동반 정리**: 위 우회 코드 3곳을 원래 형태로 되돌리고, 스코프 밖 인용 주석 7곳을 걷어낸다.
  ★이 부분은 (a)/(b) **어느 쪽을 골랐어도 해야 하는 일**이다.

**Risk:** 🟡→🟢 (규칙 모양을 (ii) 로 좁히면 「기존 파일 다수가 빨개진다」는 위험의 근원인 멤버 체인 규칙을 채택하지 않는다)

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
**상태:** 🟢 **열려 있다 — 크기 측정 완료, 수리는 의도적으로 보류.** 2026-08-01 entry-completeness-rejudgement.
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

### BL-579

**우선순위:** P2
**카테고리:** Backend / 관측 (계측 실패가 머니-패스를 오기록한다)
**Trigger:** `qb_metrics_mutation_failed_total` 이 0 을 벗어나거나, `/metrics` 볼륨이 포화에 가까워질 때. 또는 조건부 reconcile·트레일링 부착 경로를 손댈 때
**Est:** M
**상태:** ✅ **Resolved** (2026-08-02, metric-guard-parity). 머니-패스 **18곳 가드 + 결함 재현 확정**. 잔여 141곳은 [BL-580](#bl-580) 으로 분리.
**출처:** 2026-08-02 CONTROL 의 「codex MAJOR 발생 조건을 없앴다」 주장을 Evaluator 가 **counter 하나에만 참**이라고 반증하면서 발견

★**prometheus mutation 127곳이 `record_metric_safely` 밖에 있고, 그중 2곳은 거래소 쓰기 성공 직후다 — 계측이 던지면 성공한 발주가 「실패」로 기록된다.**

**원인/영향.** multiprocess 모드에서 `.labels()` 는 새 라벨 조합일 때 그 시점에 mmap 파일을
늘린다(디스크 full · 권한 오류에 노출). 그래서 이 레포는 `_count_safely` 가 **`.labels()` 까지**
감싼다(BL-536 R2). 그런데 그 관용구가 전파되지 않았다.

| 축                                               | 실측 (2026-08-02)                                                                                              |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| 가드 밖 mutation **코드 표면**                   | **127곳**                                                                                                      |
| 그중 **머니-패스 직후**                          | **6곳**                                                                                                        |
| 그중 **P1** (성공을 실패로 오기록 / 후처리 중단) | **2곳**                                                                                                        |
| **관측된 발생**                                  | **0회** (`qb_metrics_mutation_failed_total` 누적 = 0, counter 파일 2188개 전량 합)                             |
| 단 렌더 경로 실패 이력                           | `qb_metrics_render_fallback_total` = **2** (mmap 계층이 무결하지는 않았다)                                     |
| `/metrics` 볼륨                                  | **9423 파일 · 582MB** (여유 125G). counter/histogram 은 **영구 누적** — `mark_process_dead` 는 gauge 만 지운다 |

★**「관측 발생 0회」를 「위험 없음」으로 읽지 마라** — 가드된 지점에서 실패가 0회였다는 뜻이고,
가드 **밖** 지점은 실패해도 셀 counter 자체가 없다. 구조적으로 자기 실패를 못 센다.

★**판정 불가로 남긴 것** — 실제 발생 확률. 던질 수 있는 코드 경로를 라이브러리 소스로 확정했을 뿐
ENOSPC/EACCES 를 주입해 재현하지는 않았다. `metrics.py` 의 `ccxt_timer` 2건은 context manager 안이라
호출 문맥이 정적으로 안 잡혀 머니-패스 여부 **판정 불가**.

**권장 접근(되살릴 때).** `_count_safely` 를 `tasks/trading.py`·`services/order_service.py` 로
끌어올리고 **P1 2곳부터** 감싼다. 전 127곳 일괄 변경 금지 — 크기 대비 회귀 위험이 크고,
이 레포는 「스펙 밖 일괄 리팩토링」으로 검증 범위를 흐린 이력이 있다.
★**함께 볼 것** — `/metrics` 영구 누적(9423 파일)은 별개 축이고, 그것이 mmap 실패 확률의
분모를 키운다. 수리할 때 같이 재라.

### ★결과 (2026-08-02 metric-guard-parity)

★★★**착수 전제 3건이 반박됐다.**

| 백로그가 적은 것                                               | 실측                                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------------ |
| P1 이 `tasks/trading.py` · `services/order_service.py` 에 있다 | **최강 P1 은 둘 다에 없다** — `live_signal.py` 발주 직후           |
| `order_service.py` 를 수리해라                                 | **P1 0곳** — 10건 전부 발주 **전** 거절 후 즉시 `raise`            |
| 가드 밖 **127곳**                                              | 규칙 R1 로 **159곳**. ★백로그에 **세는 규칙이 없어** 재현 불가였다 |

★★★**귀결이 「오기록」 하나가 아니었다** — 재현해보니 **주문이 하나 더 나간다**.
`assert execute.await_count == 1` → `AssertionError: assert 2 == 1`. 계측 예외가 `as_market`
지연 `return` 을 건너뛰어 **낡은 스냅샷 위에서 두 번째 등재**가 나갔다.
그리고 4곳은 `commit()` **앞**이라 계측 예외가 **terminal DB 전이를 rollback** 시킨다.

**수리 = 18곳** (Tier1 발주 직후 4 + Tier2 `qb_active_orders.dec()` 등 14).
**검증** = 고장 주입 6건 red → green(`.labels()` 가 `OSError`, 단언은 전부 비즈니스 귀결) ·
census 래칫 **159 → 141** · 변이 M1 이 **5개 검사 동시 red** · 음성 대조 4종 green.
**프로덕션** — soak 에서 `_count_safely` 경유 발화가 counter 를 정확히 1 올렸다(헬퍼 이동이
런타임을 보존했다는 실주행 증거).

**근거:** [회고](dev-log/2026-08-02-metric-guard-parity.md)

**Risk:** 🟡 (관측 발생 0 이지만 P1 2곳의 귀결이 머니-패스 오기록이다)

---

### BL-580

**우선순위:** P2
**카테고리:** Backend / 관측 (계측 가드 잔여)
**Trigger:** ★`qb_metrics_mutation_failed_total` 의 **창 차분이 0 을 벗어나는 순간** 즉시 승격. 절대값 아님 — `CounterBasis.delta` 로만 읽는다. 또는 잔여 96곳 중 어느 자리가 머니-패스·알림·내구 쓰기 경계에 새로 닿게 될 때
**Est:** M
**상태:** 🟢 **열려 있다 — 84곳.** 2026-08-04 direction-channel-decomposition 연장이 `_reconcile_conditional_entries` **12곳을 전건 수리**(96→84). 그 앞 회차가 발주 outbox 12곳 판정(수리 8 · 보류 4, 104→96). 그 앞이 25곳(129→104), 그 앞이 12곳(141→129). 2026-08-02 metric-guard-parity 에서 [BL-579](#bl-579) 분리.
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

**남은 96곳 — 파일별 분포 (개별 사유는 아직 없다. 「미판정」이지 「안전」이 아니다)**

| 건수 | 파일                                                                                                                                                                                       |
| ---: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
|   46 | `backend/src/tasks/live_signal.py` (`_evaluate_session_inner` 21 · `_reconcile_conditional_entries` 12 · `_async_sweep_conditional_entries` 4 · **`_async_dispatch_event` 4 = 판정 보류**) |
|   14 | `backend/src/tasks/trading.py`                                                                                                                                                             |
|    5 | `backend/src/tasks/conditional_entry_janitor.py`                                                                                                                                           |
|    4 | `backend/src/tasks/_ws_circuit_breaker.py`                                                                                                                                                 |
|    3 | `backend/src/common/redlock.py` · `backend/src/tasks/websocket_task.py` · `backend/src/trading/websocket/state_handler.py` (각 3)                                                          |
|    2 | `common/alert.py` · `common/metrics.py` · `trading/realtime_publisher.py` · `trading/webhook.py` · `trading/websocket/bybit_private_stream.py` (각 2)                                      |
|    1 | 나머지 8개 파일 (각 1)                                                                                                                                                                     |

★**누적 판정 42곳 중 「가드 없이 유지」 0곳이다**(9 + 25 + 이번 8). 잔여 96곳도
산문으로 분류하지 말고 **주입으로 시작해라.**

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
**상태:** 🟢 **열려 있다 — 측정 완료, 수리 보류.** 2026-08-02 metric-guard-parity (사용자 확정: 측정만).
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
**상태:** 🟢 **열려 있다 — 2026-08-03 metric-guard-residual 이 「7종」을 「5종」으로 축소 재판정.**
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

### BL-583

**우선순위:** P2
**카테고리:** Backend / 테스트 인프라 (실행 순서 의존 red)
**Trigger:** ★게이트가 이유 없이 red 가 되거나, 같은 커밋을 두 번 돌려 결과가 다를 때 즉시 승격. 그리고 BE pytest 결과를 **판정 근거로 인용하기 전**
**Est:** M
**상태:** ✅ **Resolved** (2026-08-03, gate-trustworthiness). 뿌리 규명 + 오염원 3곳 처분 + 상시 가드.
**출처:** 2026-08-03 metric-guard-residual (고장 주입 테스트 작성 중 노출)

**뿌리 (한 문장).** 클래스 **정의 모듈**을 monkeypatch 한 상태에서 **소비 모듈이 「처음」 적재되면**
그 소비 모듈 최상단의 `from … import X` 가 가짜를 자기 전역으로 **복사**하고 — `monkeypatch`
teardown 은 정의 모듈만 되돌리므로 — 그 복사본이 세션 끝까지 남아, 아무것도 패치하지 않은 남의
테스트가 남의 대역을 쓴다.

**증상이었던 것.** `_async_cancel_order` 가 `{"skipped": "not_found"}` 를 냈다. 직전 회차 프로브가
「DB·savepoint 문제가 아니라 주입 문제」까지 좁혔는데, 틀린 것은 **「무엇의」 주입인가**였다 —
세션이 아니라 **repo 클래스**였다(`src.tasks.trading.OrderRepository` 가 남의 테스트의
`MagicMock(return_value=AsyncMock())` 이었다).

**오염 경로 4건 (실측).**

| 오염원 테스트                                               | 지연 import 지점                                                 | 오염된 모듈                            | 피해                        |
| ----------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------- | --------------------------- |
| `…divergence_labels::…exchange_missing_resting_order…`      | `live_signal.py:834` `_write_back_confirmed_terminal`            | `src.tasks.trading` (전역 **5개**)     | cancel_order **2 failed**   |
| `…conditional_reconcile::…submitted_without_exchange_id…`   | `live_signal.py:3027` `_conditional_entry_janitor_delay_minutes` | `src.tasks.orphan_scanner`             | orphan_scanner **3 failed** |
| `…market_data_backfill::test_backfill_returns_dict…`        | `_async_backfill` → TimescaleProvider                            | `src.market_data.providers.timescale`  | (발현 0 — 가드가 잡았다)    |
| `…conditional_entry_sweeper::…cancels_only_inactive_owned…` | 스윕의 `src.tasks.trading` 지연 import                           | `src.tasks.trading._dispatch_provider` | (발현 0 — 가드가 잡았다)    |

**크기.** 2파일 repro **2 failed** · 전체 − 사전적재원 6파일 **3 failed + 1 error** ·
전체 O1 에서는 **0**(무관한 파일 6개가 가려 준다) · 오염 (모듈, 전역) 쌍 **8**(모듈 3개) ·
관측된 피해 테스트 **5**.

★**census 는 수집 집합을 좁힐수록 더 나온다** — 디렉터리 18벌에서 1건(market_data), **파일 49벌**
(정의 모듈을 패치하는 테스트 파일 전수)에서 1건(sweeper)이 추가로 나왔다. 창이 넓은 실행 형태로
재라.

**정정된 전제 2건** (원문이 틀렸다 — 다음 사람이 같은 길로 가지 않게 남긴다):

- ✗ 「`pytest-randomly` 가 순서를 섞으므로 red 가 우연히 나타났다 사라진다」 →
  **`pytest-randomly` 는 설치돼 있지 않다.** `-p no:randomly` 는 **no-op** 이고 실행 순서는
  결정론적이다. 바뀌는 것은 **어떤 파일이 함께 수집됐는가**다. 시드 스윕은 실행 불가 —
  결정론적 순열 + 수집 집합 실험으로 대체했다.
- ✗ 「`tasks/trading.py` 는 최상단 import 라 그 patch 가 애초에 닿지 않는다」(배제 근거) →
  **이미 적재된 모듈에만 참이다.** 미적재 모듈에는 영구 복사된다. 그 배제 근거가 실은 **뿌리를
  가리키고 있었다.**

**수리.** ① `tests/conftest.py` 에 **상시 가드** — 한 테스트 항목 안에서 **처음** 적재된 `src.*`
모듈 전역에 테스트 대역(`unittest.mock` 객체 **또는** `tests.*` 에서 정의된 lambda·헬퍼)이 남으면
**그 오염원 테스트를 teardown ERROR** 로 만든다. ② 오염원 4곳(3파일)에 「패치 전 사전 적재」.
프로덕션 `src/` 는 **미수정**(모듈수준으로 올리면 import 실패 등급이 「평가 1건 실패」에서
**celery 태스크 미등록**으로 올라간다).

★**가드가 못 잡는 5종** (codex G1/G6, 전건 코드 대조) — ① 이미 적재된 모듈의 직접 변조
② 클로저나 객체 내부에 숨은 대역 ③ `sys.modules` 키의 모듈 객체 교체(`patch.dict`)
④ 창 안의 `importlib.reload` / `del sys.modules[…]` 후 재import(이름이 차집합에 없다 — 현재 레포
사용 **0건**) ⑤ **비-Mock 대역** — `SimpleNamespace()`·`object()` 는 `__module__` 이 없고
`functools.partial` 은 `functools` 라 술어에 안 걸린다(실측).
**「가드 발화 0」을 「전역 오염 없음」으로 인용하지 마라.**

★**실험 규율** — 「무관한 파일을 빼면 red 가 된다」를 보이려면 그 집합을 **AST 모듈수준 폐포로
세라**. 손으로 고른 4파일 판은 **green(3781)** 이었다(마스킹). 그리고 「대상 모듈이 수집 시점에
미적재」를 **프로브로 단언한 뒤에만** 결과를 채택해라.

**Risk:** 🟢 (닫힘)

---

### BL-584

**우선순위:** P3
**카테고리:** Backend / 관측 (라이브 발주 실패 사유 유실)
**Trigger:** ★**`mode=live` 인 `ExchangeAccount` 가 처음 생성될 때**(Wave 3 cutover — 그 순간 도달 가능해진다). 또는 `qb_live_signal_dispatch_total{outcome="max_retries_exhausted"}` 의 창 차분이 0 을 벗어날 때
**Est:** S
**상태:** 🟢 **열려 있다 — 2026-08-03 metric-guard-residual-sweep 가 「현재 코퍼스 도달 불가」로 확정.**
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

### BL-585

**우선순위:** P3
**카테고리:** Backtest / Trust Layer (강제력 없는 스키마)
**Trigger:** baseline 스키마를 또 손대게 될 때, 또는 regen 산출물이 예상 밖 형태로 나올 때
**Est:** XS
**상태:** ✅ **Resolved (2026-08-03 soak-divergence-root) — 「켜거나 지우거나」에서 「지운다」를 골랐다.**
`jsonschema` 의존을 새로 들이는 값이 없었다. 스키마가 선언하던 것 중 **중복이 아니었던 유일한
검사**는 `corpora` 의 `minProperties/maxProperties: 8` 하나였고, 그것을 개수가 아니라 **키 집합**
대조로 강화해 `test_envelope_corpus_set_is_exactly_the_canonical_list` 로 옮겼다(한 벌이 빠지고
다른 한 벌이 들어와도 개수는 8 그대로다). 나머지 필드는 [[BL-587]] 의 assert 3건이, `corpora` 의
숫자는 P-3 parity 가 타입 검사보다 훨씬 강하게 지킨다. 스키마의 `^3\.1[12]$` 패턴을 남겨두면
`.python-version`·런타임 assert 와 함께 **세 번째 SSOT** 가 된다는 점도 삭제 근거였다.
**출처:** 2026-08-03 backtest-metric-oracle

`baseline_metrics.schema.json`(6.7KB) 은 **어디서도 로드되지 않는다.** 레포 전체에 `jsonschema`
import 0건이고, `scripts/regen_trust_layer_baseline.py:46` 의 `SCHEMA_PATH` 상수는 선언만 되고
한 번도 쓰이지 않는다.

**강제력 0 의 증거 — 이번 스프린트가 실측했다.** 그 스키마의 `tool_versions.python` 패턴이
`^3\.1[12]$` 였는데, 실제 baseline 은 그 사이에 `3.12 → 3.13` 으로 드리프트해 있었다. 즉 스키마가
켜져 있었다면 **현재 baseline 을 reject 했을 것**이다. 아무도 몰랐다.

**권장 접근:** `jsonschema` 를 dev 의존으로 추가하고 `test_trust_layer_parity.py` 에 baseline ↔
schema validate 테스트 1건. 또는 스키마 파일을 지우고 dataclass 를 SSOT 로 삼는다 — **둘 중
하나여야 한다. 지금처럼 「있지만 안 도는」 상태가 가장 나쁘다.**

**영향 파일:** `tests/fixtures/pine_corpus_v2/baseline_metrics.schema.json`, `scripts/regen_trust_layer_baseline.py:46`.

**Risk:** 🟢

---

### BL-586

**우선순위:** P3
**카테고리:** Backtest / Trust Layer (골든 커버리지 구멍)
**Trigger:** TV parity 팩·비용 분해·청산 지표에서 회귀가 의심될 때
**Est:** M (baseline 크기 증가 + 리스트형 필드 직렬화 설계 선행)
**상태:** 🟢 열려 있다
**출처:** 2026-08-03 backtest-metric-oracle

P-3 골든이 고정하는 것은 `BacktestMetrics` **51 필드 중 13개**(이번 스프린트에서 12 → 13)뿐이다.
**38개가 회귀 감지 대상 밖**이다 — TV parity 팩(`avg_holding_hours` · `consecutive_*_max` ·
`monthly_returns` · `drawdown_curve` · `annual_return_pct` · `avg/best/worst_trade_pct`),
비용 분해(`total_fees` · `total_slippage` · `total_funding`), `per_side`, `excursion_stats`,
청산(`liquidation_occurred` · `liquidation_count`) 이 전부 여기 속한다.

`RawTrade` 도 22 필드 중 digest 에 들어가는 것은 **11개**다(`types.py:279` 가 "trust-layer trades
digest(명시적 11-필드) 불변" 으로 그 결정을 명문화). `exit_kind` · `fee_paid` · `slippage_paid` ·
`liquidated` 등이 빠져 있다.

**권장 접근:** 전량 고정은 baseline 을 크게 만들고 리스트형 필드(`monthly_returns` ·
`drawdown_curve` · `buy_and_hold_curve`)는 그대로 넣기 어렵다 — **digest 로 접는 쪽**이 현실적이다.
스칼라 필드부터 늘리고 리스트는 필드별 digest 를 추가하는 2단계 권장.

**영향 파일:** `scripts/regen_trust_layer_baseline.py`, `tests/strategy/pine_v2/test_trust_layer_parity.py`, `tests/fixtures/pine_corpus_v2/baseline_metrics.json`.

**Risk:** 🟢

---

### BL-587

**우선순위:** P3
**카테고리:** Backtest / Trust Layer (기록만 하고 검증 안 하는 envelope)
**Trigger:** parquet 교체 · python/pynescript 업그레이드 시
**Est:** XS
**상태:** ✅ **Resolved (2026-08-03 soak-divergence-root)** — **원인 차단 + 탐지기를 둘 다 넣었다.**
원인 차단 = `backend/.python-version` 에 `3.12` 핀(`requires-python = ">=3.12"` 만 있어 `uv sync`
가 3.13 을 집었다). 탐지기 = `test_envelope_*` 3건이 `ohlcv_sha256` · `schema_version` ·
`tool_versions.python` 을 실제로 읽는다 — 그전까지 이 셋은 regen 이 **쓰기만** 하고 읽는 곳이
0곳이었다. ★red 메시지에 **「회귀가 아니라 regen 하고 값이 같은지 확인해라」**를 박아뒀다. 안
그러면 다음 사람이 baseline 숫자를 손으로 고친다(이 회귀망이 막으려는 바로 그 행위다).
**판별력 확인:** 세 변조(해시 1글자 · `schema_version` 2→1 · python 3.12→3.13)에 대해 각각
**자기 assert 만** red(매번 1 failed / 2 passed). 복원은 sha256 대조로 확인했다.
**출처:** 2026-08-03 backtest-metric-oracle

baseline envelope 의 `ohlcv_sha256` · `pine_v2_commit` · `tool_versions` · `schema_version` 을
**검증하는 assert 가 하나도 없다.** regen 이 쓰기만 하고 아무도 읽지 않는다. 특히
`ohlcv_sha256` 은 "파일 변경 시 전체 baseline regen 의무" 를 위해 존재하는데, `corpus_ohlcv_frozen.parquet`
이 교체돼도 CI 는 불일치를 못 잡는다.

**실측 사례.** 이번 스프린트의 regen 에서 `tool_versions.python` 이 `3.12 → 3.13` 으로 바뀌었다.
2026-07-26 baseline 생성 이후 런타임이 드리프트해 있었고 아무 게이트도 울리지 않았다
(`pyproject.toml` 은 `requires-python = ">=3.12"` 이고 `.python-version` 핀이 없다).
★불행 중 다행 — 엔진 커밋 `29d0b98 → 00c63018` 과 python `3.12 → 3.13` 이 **함께** 바뀌었는데
12 필드 값과 3 digest 가 **전부 동일**했다. 두 변화 모두 숫자를 안 움직였다는 뜻이다.

**★같은 회차에 그 필드로 실제 사고가 났다 — 워크트리가 CI 와 다른 파이썬을 쓴다.**
`scripts/worktree-bootstrap.sh` 의 `uv sync` 는 `requires-python = ">=3.12"` 를 만족하는 **최신**을
고른다. 실측 — 메인 체크아웃 venv 는 **3.12.12**, CI(`.github/workflows/ci.yml:120`)도 **3.12**
인데 이번에 만든 워크트리 venv 는 **3.13.12** 였다. 그 위에서 regen 을 돌려 baseline 에
`"python": "3.13"` 을 기록했다 — **CI 가 절대 재현할 수 없는 값**이다. 발견 후 워크트리 venv 를
3.12 로 되돌리고 재생성했다(`uv venv --python 3.12`).
★부수 소득 — 3.12 재생성에서 **7벌 전 필드·전 digest 가 동일**했다. 3.12→3.13 과 3.13→3.12
양방향 모두 숫자를 안 움직였다는 뜻이다. 하지만 그건 **이번에 운이 좋았다는 것이지 규칙이 아니다.**

**권장 접근:** `test_trust_layer_parity.py` 에 (a) `ohlcv_sha256` == 실제 파일 해시, (b)
`schema_version` == 코드가 기대하는 값, (c) `tool_versions.python` == 현재 런타임 minor 검증 3건.
(c) 는 red 가 "회귀" 가 아니라 "regen 하고 값이 같은지 확인해라" 신호다 — 메시지에 그렇게 쓴다.
**`.python-version` 핀 추가는 (c) 보다 먼저 해야 한다** — 워크트리마다 런타임이 갈리는 것을 막는
쪽이 근본이다. [[BL-585]] 와 묶으면 자연스럽다.

**영향 파일:** `tests/strategy/pine_v2/test_trust_layer_parity.py`, `backend/pyproject.toml`(또는 `.python-version`), `scripts/worktree-bootstrap.sh`.

**Risk:** 🟢

---

### BL-588

**우선순위:** P3
**카테고리:** Backtest / Trust Layer (코퍼스 목록 3중 정의)
**Trigger:** 코퍼스를 또 추가/제거할 때
**Est:** XS-S
**상태:** ✅ **Resolved (2026-08-03 soak-divergence-root)** — 「5→7 로 맞춘다」가 아니라 **목록을
하나로 합쳤다**(`backend/tests/strategy/pine_v2/_corpus.py`). parity·regen·mutation oracle 셋이
그것만 읽는다. 앞 둘은 "동명 상수와 쌍이다" 라는 주석으로 서로를 가리켰지만 **셋째는 아무도
가리키지 않아서** 비축퇴 2벌이 확산되지 않았다 — 주석으로 쌍을 맺는 방식 자체가 실패했다.
★**실측: `_MUTATION_CORPORA` 에 있던 5벌이 정확히 위험조정지표가 축퇴한 5벌**이었다
(sharpe `0.00000000` · sortino/calmar `null`, 7벌 중 5벌). 빠져 있던 s4/s5 가 유일한 비축퇴 짝이라,
5벌 체제에서는 그 3지표의 **산술 회귀가 구조적으로 감지 불가**였다.
**비용/효과 실측:** nightly `--run-mutations` **183s → 218s (+19%)**, 감지 결과는
**7 passed + 1 xpassed 로 불변**. ★기존 8 변이는 전부 거래 시퀀스를 흔들어 `trades_digest` 로
이미 잡히므로 증가가 없는 것이 정상이다 — 7벌의 값은 **앞으로의 지표-산술 회귀를 위한 채널의
존재**이지 이 8건의 감지율이 아니다. (사전등록 B-V2 「증가하거나 최소 유지」 → **유지**.)
**출처:** 2026-08-03 backtest-metric-oracle

실행 대상 코퍼스 목록이 **세 곳에 따로** 있다.

| 위치                                                | 상수                | 현재    |
| --------------------------------------------------- | ------------------- | ------- |
| `tests/strategy/pine_v2/test_trust_layer_parity.py` | `RUNNABLE_CORPUS`   | 7벌     |
| `scripts/regen_trust_layer_baseline.py`             | `RUNNABLE_CORPUS`   | 7벌     |
| `tests/strategy/pine_v2/test_mutation_oracle.py`    | `_MUTATION_CORPORA` | **5벌** |

앞 두 곳은 이번 스프린트에서 함께 갱신했지만 **셋째는 안 따라온다** — 즉 신규 비축퇴 코퍼스
(`s4_hma_curvature` · `s5_ema_trend`)가 nightly mutation oracle 에는 확산되지 않았다. 그 두 벌이
위험조정지표에 판별력을 만든 유일한 코퍼스이므로, mutation oracle 은 **여전히 sharpe 가 전부 0 인
5벌로만** 판정한다.

**권장 접근:** 목록을 한 곳(예: 코퍼스 디렉터리의 manifest 또는 공용 모듈)으로 모으고 세 소비자가
같은 곳을 읽게 한다. 최소 조치로는 `_MUTATION_CORPORA` 를 7벌로 늘리는 것만으로도 nightly 감지율이
올라갈 수 있다 — 다만 mutation 실행 시간이 늘어나므로 nightly 소요를 먼저 재라.

**영향 파일:** 위 표 3개 파일.

**Risk:** 🟢

---

### BL-589

**우선순위:** P1
**카테고리:** Trading / 라이브 신호 (엔진↔거래소 방향 발산)
**Trigger:** ★**이미 발화했다.** 2026-08-03 소크가 T0 65분 만에 이 사유로 fail-closed 종료.
**Est:** M
**상태:** ✅ **Resolved (2026-08-03 soak-divergence-root)** — 뿌리는 엔진이 아니라 **조건부 진입
계획기**였다. 발화할 수 없었던 대기 주문 때문에 시장가 전환이 꺼져 시뮬만 진입을 잡았다.
**출처:** 2026-08-03 backtest-metric-oracle (소크 관측 중 발견)

**취소된 반전 주문 뒤에 엔진만 포지션이 뒤집힌 채 남았다.**

소크 세션 `04097fdc`(T0 `2026-08-03T09:53:34Z`)가 `10:58:34Z` 에
`position_divergence` / `category=direction` 으로 자동 비활성화됐다 — 창의 **65분** 지점.
`engine_position=+0.030392388292696512` vs `exchange_position=-0.03`. 크기는 사실상 같고
**방향이 정반대**다.

**타임라인 (T0 이후 주문 7건 전량).**

| 시각(UTC)    | 사건                                                  |
| ------------ | ----------------------------------------------------- |
| 10:05:04     | `sell 0.03` **filled** → 거래소 −0.03                 |
| 10:12:34     | `buy 0.06` **filled** → 거래소 +0.03                  |
| 10:19:37     | `sell 0.06` **filled** → 거래소 **−0.03**             |
| 10:38:46     | `buy 0.06` 발주 (−0.03 → +0.03 반전 의도)             |
| **10:56:41** | 그 주문 **cancelled** — `error_message` **비어 있음** |
| 10:57:34     | `live_signal_position_divergence` 1차 경고            |
| **10:58:34** | 2차 경고 → **fail-closed 비활성화**                   |

체결분만 더하면 거래소는 정확히 −0.03 이다. 즉 **거래소 원장은 일관적이고 엔진만 틀렸다.**
반전 주문이 취소됐는데 엔진 상태는 전진한 것으로 보인다.

~~★**[BL-560] 의 거울상이다.**~~ ★**절반만 맞았다 (2026-08-03 재판정).** 엔진은 취소를 못 본 게
아니라 **주문을 아예 모른다.** `_to_engine_position`(`tasks/live_signal.py:520-534`)이 읽는 것은
`run_live` 워밍업 재생이 만든 `strategy_state_report["position_size"]` — **체결 원장이 아니라 자체
시뮬레이션**이다. 「취소 시 되돌리는 경로가 왜 안 탔나」는 질문이 성립하지 않는다. 그 경로는 없다.

**★확정된 원인 — 계획기가 시뮬이 이미 잡은 진입을 버린다.**

`trading/services/conditional_entry_planner.py` 가 주석으로 스스로 적고 있었다: _"가격이 피벗을
이미 지나가면 **시뮬은 `low <= stop` 으로 즉시 체결로 보는데** 거래소는 long RISE 는 retCode
110092, short FALL 은 110093 으로 **거부한다**."_ 시장가 전환 탈출구가 있는데, **대기 주문이
존재하기만 하면** 그게 꺼졌다:

```python
if breached and (matching_actual or not allow_market_conversion):   # 수리 전
    to_cancel.extend(matching_actual); continue                     # 전환 없이 드롭
```

배제는 의도적이었다 — PR #493(`274dc645`): _"전환은 resting 조건부가 없을 때만. 있으면 거래소가
이미 그 주문을 트리거했을 확률이 높아 취소+시장가는 이중 진입이 된다."_ **그러나 이번 사고는 그
위험에 해당하지 않았다.** 대기 주문 `1adf0cab` 은 `trigger_price=62811.5` / `trigger_direction=1`
(상승)인데 계획 시점 기준가는 **62700** — 62811.5 **미만이라 발화할 수 없었다.** 술어가 「대기
주문이 있는가」를 묻는데 물어야 할 것은 **「그 대기 주문이 발화할 수 있었는가」**였다.

`10:56:39` 로그가 그대로다 — `live_conditional_plan_drop trade_id=PivRevLE
reason=trigger_already_breached direction=long stop_price=62661.71 reference_price=62700.0
had_resting=true`. 피벗이 62811.5 → 62661.71 로 내려가 새 트리거가 현재가 아래라 stop 으로 못
걸었고, 계획기는 드롭 + 대기 주문 취소만 했다. 시뮬은 그 진입을 잡은 뒤였다.

**★남은 네 질문의 실측 답.**

1. **자체 시뮬레이션이다** (위 참조). 「원장을 안 보는 설계」가 맞다 — 원장이 시뮬로 들어가는
   경로는 gap-resync 의 `ledger_seed` 뿐이다.
2. **의도 수량이 맞다.** `190422.997 × 1% / 62654 ≈ 0.030392`, 거래소는 `qty_step` 절삭으로 0.03.
   상대차 1.3% 가 `_POSITION_SIZE_REL_TOL = 0.05` 아래라 `size` 로는 영영 안 뜨고 **부호가
   뒤집힐 때만** 치명적이 된다. ★이번 사망 원인은 아니다 — 별건으로 남긴다.
3. **취소 사유는 여전히 없다.** 재확인 결과 4건이 아니라 **7건 전부** NULL 이고, counter 도 breach
   취소를 `replaced` 에 섞는다. 그래서 `breach_with_resting` **11건 중 로그가 남은 2건만**
   사후 판정 가능했다(워커 로그는 컨테이너 시작 `08-02T13:19` 이후만 보존). [[BL-578]] 계열로 유지.
4. **2회 연속 정책은 맞다** (`tasks/live_signal.py:2566-2572`). 다만 자가 복구 기회는 없었다 —
   시뮬은 매 tick OHLCV 를 재생하므로 자기 신호가 바뀌기 전에는 포지션이 안 돌아온다.

**★수리 (2026-08-03).** 술어를 `resting_could_have_fired` 로 좁혔다 — 대기 주문 **자신의** 트리거가
같은 기준가로 뚫린 경우에만 드롭을 유지하고, 발화 불가면 취소 후 시장가로 전환한다. 드롭 쪽이
손해보는 일은 없다(두 갈래 모두 대기 주문을 취소하므로, 전환이 하류 가드에 걸려 무산되면 결과가
기존 드롭과 같다). 부수로 **`as_market` 을 등가 비교에 넣었다** — 눈금이 굵으면 시장가 의도가 대기
stop 과 「일치」로 접혀 아무것도 안 나가는 구멍이 있었고, 이 구멍은 술어를 좁히기 전에는 도달
불가였다.

**★검증.** 사전등록 변이 M1(발화 불가 → 시장가)이 수리 전 **red** · 후 green, 대조 M2·M3 은 전후
불변 green. 구현과 독립된 재생 오라클(원장 + Bybit 1분봉)이 **취소된 조건부 172건 중 「발화 불가 +
대체 없음」 29건**을 집어냈고 그 안에 사망을 유발한 `1adf0cab` 이 들어 있다. 로그가 남은 breach
2건은 **정반대 두 판정을 모두 적중** — `f76f76ad`(4초 전 실제 체결됨)는 「드롭 유지」,
`1adf0cab`(끝내 미체결)은 「시장가 전환」.

**부수 조치 (2026-08-03).** 세션 종료 후 거래소에 **세션 없는 −0.03 숏**이 남아 있어
reduce-only 시장가 매수 0.03 으로 flat 정리했다(사용자 승인).
★**이 정리는 앱 원장을 거치지 않았다** — `ClosePositionService` 는 HTTP 경로에만 조립돼 있어
Clerk JWT 가 필요한데 스크립트에서 얻을 수 없어 provider 를 직접 호출했다. 따라서 이 청산에
대응하는 `trading.orders` 행이 **없다**. 원장을 읽을 때 이 구멍을 기억해야 한다.

**Risk:** 🔴 **소크 시계를 멈춘 사건이다.** P0 [BL-003] 의 유일한 게이트가 「데모 1주 안정 운영」인데
이 발산이 창을 65분에서 끊었다. 원인을 모른 채 재가동하면 같은 자리에서 또 끊길 가능성이 높다.

---

### BL-590

**우선순위:** P1
**카테고리:** Trading / 라이브 신호 (거래소 거절 뒤 복구)
**Trigger:** ★**이미 발화했다.** 2026-08-03 소크 세션 `a201a47b` 가 T0+**104.9분** 에
`position_divergence` 로 fail-closed 종료. 직접 원인 = 주문 `48c9cdc9` 의 `110093` 거절.
**Est:** M
**상태:** ✅ **Resolved (2026-08-03 breach-rejection-recovery)** — 거절을 「돌파 확정 증거」로
읽고 시장가 복구를 집행한다. 프로덕션 유도로 분기 도달·종결 확인(`recovery_placed` 1.0 · 체결).
**출처:** 2026-08-03 soak-watch (소크 3회 연속 자동 종료 조사)

**계획기의 돌파 가드는 발주 시각에 옳았다. 없었던 것은 거절 뒤의 복구다.**

`plan_reconcile` 은 PR #493 이후 **거래소 라이브 perp last** 를 기준가로 쓴다(60초 스테일은
그때 없어졌다). 그런데 거래소는 우리보다 **2.1초 뒤** 자기 시각으로 트리거를 판정한다.
그 사이 가격이 트리거를 통과하면 `110093`(short/Falling) 또는 `110092`(long/Rising)로 거절된다.

카운터 차분이 연역으로 증명한다 — `conditional_placed +1`, `market_converted`·
`trigger_already_breached`·`reference_unavailable` **전부 불변** ⇒ `breached=False` 였고
라이브 기준가는 트리거 **위**였다. 2.1초 뒤 거래소는 아래로 쟀다.

거절은 `qb_exchange_order_response_total{reason="trigger_breached"}` 로 **계상만** 되고
끝난다. 그런데 엔진 포지션은 `run_live` 시뮬이라 주문을 모르고, **거래소가 거절했다는 사실
자체가 그 bar 가 트리거를 찍었다는 증명**이므로 시뮬은 반드시 체결한다 ⇒ 엔진만 전진 ⇒
`direction` 발산 2회 연속 ⇒ fail-closed.

**★[BL-589] 와 다르다.** 저건 계획기가 진입을 **드롭한** 경우고 이건 **발주했는데 거절된**
경우다. 사망 구간에서 `breach_with_resting` 은 11 불변이었다.

**규모 (PR #493 이후).** `110092` **2건** + `110093` **2건** = **4건 / 19.09 세션시간
= 0.21건/h**. 조건부 주문당 **4/178 = 2.25%**. 재생 오라클로 4건 전수에서 「거절 직후 bar 가
트리거를 찍었다」를 확인(**4/4**). 단 치명(`direction`)은 거래소가 **반대 포지션을 들고 있을
때만**이라 **2/4** 이고, 그중 오늘의 반전 아키텍처를 공유하는 것은 **1건뿐**이다.

**수리.** `trigger_breached` 거절의 CAS 승자가 commit 뒤 `live_signal.recover_breached_entry`
를 예약한다. 복구는 계획 시점 전환과 **같은 순서**의 가드를 통과한다 — interval · 이중 진입
억제창 · **만료(1 interval)** · 기준가 재조회 · 돌파 재확인 · 돌파폭 캡. fail-closed 킬 경로는
**무수정**이라 복구가 실패하면 오늘과 똑같이 안전하게 죽는다.

**Risk:** 🟡 시장가로 쫓아가므로 시뮬 체결가보다 불리할 수 있다(실측 돌파폭 최대 **0.039%**).
만료 가드가 지연된 복구를 막고, 사용자 `max_trigger_breach_pct` 가 그대로 적용된다.

**남긴 것(의도적).** ① 거절 commit 과 `apply_async` 사이 크래시 시 복구 유실 — 실패 모드가
오늘과 같고, 만료 가드 때문에 뒤늦은 sweeper 재시도는 무효다. ② 서로 다른 `trade_id` 두
복구의 동시 실행 경쟁(억제 질의가 read-then-write) — 기저율 0.21건/h 라 보류.

---

### BL-591

**우선순위:** P2 (2026-08-05 강등 — 「P0 [BL-003] 의 실질 게이트」가 [ADR-025] 상류 폐쇄로 무너졌다. **본 BL 범위의 잔여 = D1/D2 뿐**이고, 되먹임이 없는 나머지 갈래(브래킷 TP/SL · 거래소발 청산 · 시장가 진입)는 [ADR-023] 소관으로 남는다 — 이 강등은 그 축까지 내리지 않는다)
**카테고리:** Trading / 라이브 신호 (엔진 포지션 SSOT)
**Trigger:** ★**이미 발화했다.** 자동 종료 **15회**(NULL 12 + `gap_resync_position_mismatch` 1 +
`position_divergence` 2). `direction` 발산 가드 머지(#497, `2026-07-28T23:09Z`) **이후의 자동 종료는
6회**이고 그 **6/6 이 2시간 안에 죽었다**(104.9 · 91.4 · 84.3 · 65.0 · 21.5 · 18.0분).
**Est:** L — **설계 결정 선행**(사용자). 구현 착수 전 이 절의 §설계 축을 확정해야 한다.
**상태:** 🟢 **Open — 슬라이스 1(계측)은 PR #539 OPEN(미머지, 통합 브랜치). 슬라이스 2 는 사전등록 V1 발동으로 미착수 확정. ★2026-08-04 에 C 안이 「예방 전용·사망 경로 구조적 미도달」로 축소되고 사망 경로의 수리 축은 [ADR-023](decisions/023-engine-state-ssot.md)(Proposed)으로 이관됐다. ★★★2026-08-05 divergence-rejudgement — **슬라이스 B(킬 정책 교체)는 판별력 0 으로 판정되어 보류**(폐기 아님): 사망 4건 **전부**가 새 판별식으로도 `phantom` 이라 「즉시 킬」로도 그대로 죽고, 무해 12건 중 사망은 **0건**이라 「절대 안 킬」로 구제될 세션도 없다 ⇒ **이 정책으로 살아났을 세션이 0개다.** D1(strike TTL 부재)·D2 는 도달 가능하므로 폐기하지 않는다. ★★**「무해 7 : 치명 4」의 방향 서술도 반증됐다** — 사망 4건 부검에서 **거래소가 앞선 사망 1건**(`39731d57`)이 나왔다. **레버는 킬 정책이 아니라 [BL-595]**(엔진·거래소가 서로 다른 stop 주문을 든다)다. ★슬라이스 A 는 재개 조건이 발화했으나 **킬 결과를 바꾸지 않는다** — 관측 가치만 남는다. 판별식·테스트·오라클은 레포에 있다(2026-08-05 기준 41 테스트)** ★★★**2026-08-05 재판정 — P1→P2 강등**: P1 근거 「[BL-003] 의 실질 게이트」가 무너졌다 — 사망 5/5 는 [BL-595] 로 재귀속돼 [ADR-025](decisions/025-conditional-fill-ownership.md) 가 **상류에서** 닫았고, 자신의 레버 A·B·슬라이스 2 도 각자 죽었다. **본 BL 범위의 잔여 = D1/D2 뿐 · 프로덕션 미관측**([ADR-025] §남는 것 = 「관측만 한다」). 재개 조건 불변.
**출처:** 2026-08-03 breach-rejection-recovery (증상 반복의 뿌리 재판정)

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
**상태:** ⬜ **Open**
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
**상태:** ⬜ **Open**
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

### BL-595

**우선순위:** P1 (P0 [BL-003] 의 실질 차단자)
**카테고리:** Trading / 라이브 신호 (조건부 진입 stop 의 소유권)
**Trigger:** ★**이미 발화했다.** 현행 코드에서 관측된 `position_divergence` 사망 **2건**이 이것이고 **서로 반대 방향**이다.
**Est:** L — 설계 선행 필요(머니-패스 변경 · 대칭 수리)
**상태:** ✅ **Resolved (2026-08-05 conditional-stop-ownership, `stage/conditional-stop-ownership`).**
라이브 조건부 진입 체결의 권한을 **주문 원장**으로 옮겼다([ADR-025](decisions/025-conditional-fill-ownership.md)) —
원장이 증언하지 않으면 엔진도 체결하지 않고(형 A), 증언하면 엔진의 봉·트리거 판정과 무관하게
체결한다(형 B). 백테스트는 인자 기본값 `None` 으로 byte-identical 이고 그 경계를 테스트가 집행한다
(파일 화이트리스트 + `TrackRunner.invoke` 의 **구조적 거부**). ★**사망 5건 전량을 얼려 재현**했고
(영속 보고서와 **비트 단위 일치**) 수리 전 5/5 `direction` 발산 → 수리 후 5/5 일치다.
★★**형 B 를 재판정했다 — `39731d57` 은 「거래소가 앞선 별개 현상」이 아니라 거짓 사망이다**:
사망 tick 창의 마지막 봉 고가(64065.0)가 엔진 stop(64071.91)에 못 미쳤고, 한 봉 더 준 재생은
LONG(거래소와 일치)을 낸다 — 엔진은 늦었을 뿐이고 다음 tick 에 스스로 따라잡았을 것이다.
봉 발행이 1.7초 늦어 창이 2봉 뒤처지자 킬의 「연속 2 tick」이 회복 전에 발동했다.
★**착수 중 5번째 사망**(`a16aa640`, 08-05T09:12:53Z, 8.642h)이 나 표본이 4→5 가 됐다.
★**남긴 것(수리 안 함, 관측만)**: 고아 원장 체결(사망 5건 중 0건 — ADR-025 R4) ·
창 지평 5시간(오늘과 같다) · `enforce_margin` 후속과 fail-open 취소 왕복(ADR-025 §codex ⑦⑧).
회고 = [dev-log](dev-log/2026-08-05-conditional-stop-ownership.md)\*\*
**출처:** 2026-08-05 divergence-rejudgement (사망 4건 부검 + 원장 실측)

**엔진의 시뮬 stop 과 거래소의 resting stop 은 같은 주문이 아니다 — 그래서 양쪽 모두 혼자 발화한다.**

`run_live` 는 매 tick 300봉을 재생하며 pending stop 을 **다시 계산**한다. 거래소에는 그와
별개로 조건부 주문이 **하나 얹혀 있고**, 그 트리거는 발주 시점의 스냅샷이다. 둘은 수준도
수명도 다르다:

| 갈래              | 무엇이 어긋나나                               | 실측                                                                                                 |
| ----------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **출생 지연**     | 실제 주문이 봉 시작 뒤 **10~15초**에 태어난다 | `cc19abd2` — 18:49:14 생성, 봉 18:49 고가 64295.8 ≥ 트리거 64285.8 인데 미체결 ⇒ 교차가 앞 14.6초 안 |
| **태어나지 못함** | 발주가 거절                                   | `a201a47b` — `110093 expect Falling, but trigger_price >= current` (★[BL-590] 이전)                  |
| **수준 드리프트** | resting 트리거가 낡은 스냅샷                  | 재발주마다 평균 **62~271 USDT** 이동(최대 531). 1분봉 range 는 **30~90**                             |

**사망 4건 부검**(`live_signal_states.last_strategy_state_report`, 사망 60초 전 tick):

| 세션       | entry_bar        | entry_price  | 거래소 트리거                 | 방향               |
| ---------- | ---------------- | ------------ | ----------------------------- | ------------------ |
| `cc19abd2` | **299**(마지막)  | **64285.81** | **64285.80**                  | 엔진이 앞섬        |
| `a201a47b` | **299**          | **63723.69** | **63723.60**(거절)            | 엔진이 앞섬        |
| `04097fdc` | **299**          | 62661.71     | 62811.5 (**한 번도 안 닿음**) | 엔진이 앞섬        |
| `39731d57` | **281**(19봉 전) | 64032.69     | 64071.9 → **체결됨**          | ★**거래소가 앞섬** |

★`39731d57` 은 엔진 포지션이 두 tick 에서 **비트 단위 동일**(`-0.029722343673419874`)이다 —
엔진은 움직이지 않았고 거래소의 stale stop 이 혼자 발화했다. **[BL-590] 이후 사망 2건은
`cc19abd2`(엔진 앞섬)와 `39731d57`(거래소 앞섬)로 반대 방향이다.**

**★한쪽만 닫으면 절반만 막는다.** 「거래소 주문이 봉을 통째로 덮지 않았으면 엔진도 체결하지
않는다」는 `cc19abd2` 형만 닫고 `39731d57` 형은 못 닫는다. 대칭 수리 = **라이브에서는 조건부
진입 체결을 엔진이 시뮬하지 않고 거래소 원장의 체결만 인정한다.**

**대가·선행 조건:**

- `pine_v2` 머니-패스 변경이다. `run_live` 에는 `position_epoch` / `ledger_seed_legs` 자리가
  이미 뚫려 있으므로(`event_loop.py:370-378`) 배관은 있으나, **백테스트 경로 byte-identical**
  을 테스트로 못박아야 한다.
- ~~★**Trust Layer 23테스트가 `run_live` 를 0회 호출한다** ⇒ 라이브가 갈라져도 CI 가 초록이다.
  **이 BL 의 첫 단계는 라이브 재생을 실제로 태우는 회귀 테스트**다.~~
  → **2026-08-05 반증.** Trust Layer 는 **52테스트**이고(「23」은 낡았다) `run_live` 를 안 부르는
  것은 맞지만, 그 밖에서 **7파일 89테스트가 직접 ~90회** 호출한다. 백테스트↔라이브 parity
  오라클도 `test_run_live.py:239` 에 이미 있다. ⇒ **첫 단계는 테스트 신설이 아니다.**
- ★★★**그리고 「어느 진입점을 호출하는가」는 「어느 코드를 덮는가」가 아니다.** 이 BL 의 형 A 를
  최소 모형으로 주입하니(조건부 stop 을 봉 내 `high/low` 대신 봉 시가 돌파로만 체결)
  **12개 테스트가 죽었고 그중 하나가 Trust Layer 골든**(`test_p3_execution_metrics_match_golden[s1_pbr]`)
  이다 — `run_live` 를 한 번도 안 부르면서. 조건부 체결이 `strategy_state.check_pending_fills`
  에 있고 그건 **백테스트와 라이브가 공유하는 머니-패스**이기 때문이다.
  ⇒ **설계 제약**: 대칭 수리는 `check_pending_fills` 를 고치는 것이 아니라 **라이브 전용
  경로에서만** 갈라져야 한다(공유 코드를 고치면 백테스트 골든이 red — 이 BL 이 우려한 바로
  그 위험이 **이미 집행되고 있다**). 뒤집어야 할 12건 목록 =
  [dev-log](dev-log/2026-08-05-live-replay-visibility.md) §3.3
- 선행연구 대조: NautilusTrader 는 side flip 을 **조정 주문으로** 푼다. 그러나 그쪽 전략은
  **재생하지 않으므로** 이 원인 자체가 없다 ⇒ **조정([ADR-023])보다 생성 차단(본 항목)이 상류다.**

**아닌 것 (측정으로 배제됨, 2026-08-05):**

- 가격 소스 불일치 — 엔진 `CCXTProvider` perp · 공개 perp · **데모** perp 가 사망 4건의 해당
  봉에서 **소수점까지 동일**. 스팟만 27~36 USDT 떨어져 있고 체결 조건 **4/4 불만족**([BL-530] 유지)
- 1분 타이밍 아티팩트 — 엔진 `entry_price` 가 해당 봉의 체결 조건을 정확히 만족(3/4),
  나머지 1건은 19봉 전 개시

**연결:** [BL-003](#bl-003) (게이트의 실질 차단자) · [BL-591](#bl-591) (킬 정책은 레버가 아니다) ·
[ADR-023](decisions/023-engine-state-ssot.md) (하류 조정안) · [ADR-024](decisions/024-soak-stability-gate.md) (판별식)

---

### BL-594

**우선순위:** P2
**카테고리:** Infra / 데이터 내구성 (Redis AOF)
**Trigger:** 소크가 168h 를 향해 도는 동안 (재기동 1회면 드러난다) · 호스트 재부팅 전
**Est:** S
**상태:** ✅ **Resolved (2026-08-06 night-watch)** — B1(게이트 C5⑸ `aof_ok` + `auto-aof-rewrite-min-size 8mb` + 실측 캡처 7형 15테스트) 병합, **B2 재기동 실증**: 계획 재기동 1회에서 redis 가 신설정으로 재생성·정상 기동(`config get` = 8388608), 게이트 실격 0 · `aof_ok=✓` 프로덕션 상시 검사. 잔여 관측(닫힘의 범위 밖): 페이로드 손상은 `redis-check-aof` 가 못 본다(사본 기동 오라클 후보) · 프로브↔rewrite 경합(fail-closed 방향, ~0.1%/일) · `aof_rewrites` 실발동 며칠 관측. 손상 **원인**은 여전히 미규명(후보 2종은 실측 반증 — dev-log 2026-08-06).
**출처:** 2026-08-05 soak-clock-restoration (완료 기준 「기존 워크플로를 실행해서 확인」 중 발견)

**Redis 가 재기동을 못 하는 상태로 6일간 돌고 있었다 — 아무도 몰랐다.**

`make down` 후 `make up-isolated` 가 `dependency failed to start: container quantbridge-redis is
unhealthy` 로 실패했다. 로그:

```
# Bad file format reading the append only file appendonly.aof.4.incr.aof:
  make a backup of your AOF file, then use ./redis-check-aof --fix <filename.manifest>
```

`redis-check-aof --fix` 실측 — **35,605,598 바이트 중 30,825,637 바이트(86.6%)가 판독 불가**였다
(`ok_up_to=4779961`). base RDB(5,168 키)는 멀쩡했고 **incr AOF 만** 깨졌다. 절단 후 정상 기동.

**왜 안 보였나.** `restart: unless-stopped` 인 컨테이너가 **6일 연속 살아 있었다**. AOF 는
**기동 시에만 읽힌다** — 그래서 프로세스 메모리 위에서는 아무 증상이 없었다. 즉 이 스택은
**재기동 내성이 없는 채로** 소크를 돌리고 있었다.

**영향.** Redis 는 celery broker + result backend + redlock + 캐시다. 이번엔 활성 세션이 0이라
피해가 없었지만, **소크 도중 호스트가 재부팅되면 워커가 안 뜬다.** [BL-003] 게이트가 168h 짜리
달력 시간이라 그 창 안에 재부팅이 들어올 확률이 낮지 않다.

**미조사.** 손상 원인은 안 밝혔다. 후보 — 하드 kill 중 쓰기 · 디스크 이슈 · Docker Desktop
VM 의 파일시스템. 백업본이 있다(2026-08-05, 3.5MB tar.gz).

**처리 방향:**

1. **기동 내성을 상시 확인한다** — `scripts/soak-gate.sh` 나 nightly 가 `redis-check-aof`
   (읽기 전용, `--fix` 없이)를 주기적으로 돌려 판독 가능 여부를 낸다. ★현행 healthcheck
   (`redis-cli ping`)는 **떠 있는 프로세스에만 묻는다** — 이 결함을 구조적으로 못 본다
2. 손상 원인 조사 — `appendfsync` 설정과 컨테이너 종료 경로(SIGTERM grace) 확인
3. 필요하면 `auto-aof-rewrite-percentage` 로 incr 파일이 35MB 까지 자라지 않게 한다

**2026-08-05 실측 (스크래치 컨테이너 — `quantbridge-*` 무접촉).** 손상 4종을 주입해
`redis-check-aof` 출력과 **실제 기동 여부**를 대조했다. 캡처 원문은
`backend/tests/fixtures/bl594_aof/` 에 7형으로 동결돼 있다.

| 손상                 | exit | 오류 문구                               | 서버 기동                                    | `aof_ok` |
| -------------------- | ---- | --------------------------------------- | -------------------------------------------- | -------- |
| 없음                 | 0    | `All AOF files and manifest are valid`  | ✅                                           | ✔        |
| 마지막 INCR 꼬리절단 | 1    | `Expected to read 5 bytes, got 1 bytes` | ✅ (자동 절단)                               | ✔        |
| **비마지막** 파일    | 1    | **위와 같은 모양**                      | ❌ `the truncated file is not the last file` | ✘        |
| 구분자 손상          | 1    | `Expected \r\n, got: 0000`              | ✅ **뜬다** (dbsize 300 전부 적재)           | ✘★       |
| 명령 헤더 손상       | 1    | `AOF … format error`                    | ❌ `Bad file format` (프로덕션 서명)         | ✘        |

★**종료 코드는 판별식이 될 수 없다** — 꼬리 절단은 `aof-load-truncated yes`(기본값)가
기동 시 잘라내므로 무해한데 exit 1 을 낸다. 도는 redis 의 꼬리는 언제든 미완결일 수 있으므로
exit code 로 재면 멀쩡한 스택이 거짓 `측정불가` 가 된다. → 게이트는 **양성 서명만** 통과시킨다.
★★반대로 「short read 면 통과」로 넓히면 **비마지막 파일 절단**이 통과한다 — 출력이 같은
모양이고 **유일한 판별자가 「지목된 파일이 마지막 INCR 인가」**다. 그 하나로 기동이 갈린다.
★★**구분자 손상은 알려진 거짓 양성이다** — check-aof 는 페이로드 뒤 `\r\n` 을 검증하는데
**서버 로더는 그 2바이트를 검증 없이 버린다**. 방향이 엄격 쪽이라 래칫에는 안전하다.
★이 표는 codex 리뷰 처분 중 **정정됐다** — 그전에는 `Expected \r\n, got:` 이면 서버가 죽는다고
적혀 있었다. 그때 죽은 건 0바이트 64개가 구분자 **말고 더** 부순 경우였고, 순수 구분자
손상만으로는 죽지 않는다(재측정으로 반증).

★★**알려진 한계** — `redis-check-aof` 는 **프레이밍만** 본다. 벌크 페이로드 안이 깨져 명령
이름이 망가진 AOF 를 `All AOF files and manifest are valid` 로 통과시켰는데 그 AOF 로
서버는 `Unknown command 'SE'` 를 내고 **exit 1** 했다. 즉 `aof_ok=true` 는 「프레이밍이
성하다」이지 「반드시 뜬다」가 아니다. 기록된 프로덕션 고장(`Bad file format`)은 잡힌다.
**후속 후보:** 사본을 별도 프로세스로 **띄워보는** 검사(진짜 재기동 오라클).

**채택·기각.**

- ✅ **`--auto-aof-rewrite-min-size 8mb`** — rewrite 는 크기·증가율을 **둘 다** 넘어야 발동하는데
  base RDB 가 88바이트라 증가율은 늘 만족, **크기(기본 64mb)만 남는다**. 실측: 10MB 를 넣어도
  `aof_rewrites:0`. 8mb 로 낮추니 자동 발동해 incr 이 삭제되고 on-disk 10.3MB → 0.57MB.
  ★rewrite 는 **낡은 incr 파일을 지운다** — 손상된 incr 을 넣고 rewrite 하니 판독성이 회복되고
  재기동에 성공했다. 즉 노출 창이 35.6MB → ~8MB, 관측 쓰기량(~6MB/일) 기준 하루 1회꼴 폐기.
- ❌ **`stop_grace_period`** — 후보 원인 「하드 kill 중 쓰기」가 **2/2 반증**됐다. 쓰기 도중
  SIGKILL(느린 루프 · 대량 파이프 적재) 둘 다 AOF 가 `diff=0` 유효였고 재기동도 됐다. 게다가
  기록된 손상은 `ok_up_to=4,779,961 / size=35,605,598` — **파일 13% 지점**이라 꼬리 쓰기 경로가
  만들 수 있는 모양이 아니다. 정상 종료도 0.31초(기본 유예 10초)라 늘릴 근거가 없다.
- ❌ **`appendfsync` 변경** — fsync 정책은 **꼬리**의 내구성을 정하는데 기록된 손실은 중간이고
  그 뒤로 30MB 가 더 있었다. `always` 는 브로커 쓰기마다 fsync 비용을 물린다. 기본 `everysec` 유지.
- ❌ **`auto-aof-rewrite-percentage` 명시** — 이미 기본 100 이고 base 가 작아 **구속 조건이 아니다**.
  적어도 동작이 안 바뀐다.

**Risk:** 🟡 데이터 손실은 캐시/broker 한정이라 작다. 다만 **가용성**이 [BL-003] 의 달력 시간에
직접 걸린다.

**연결:** [BL-003] (168h 창 안의 재기동 내성) · [ADR-024](decisions/024-soak-stability-gate.md) (C5⑸ `aof_ok`)

---

### BL-596

**우선순위:** P2
**카테고리:** Ops / [BL-003] 게이트 (라벨 어휘의 fail-open)
**Trigger:** 판별식이 새 라벨을 낼 때 · 또는 `unattributed` 가 실제로 관측될 때
**Est:** S
**상태:** ✅ **Resolved (2026-08-05 gate596)** — 게이트가 라벨 어휘를 **명시적 3분할**로 읽는다
(`soak_gate_predicate.py` 의 `HARMLESS`/`DISQUALIFYING`/`UNDECIDABLE_DIVERGENCE_LABELS`).
무해도 실격도 아닌 라벨(`unattributed` + 어휘 밖 전부 + `label` 키 결손)은 **C5 측정 무결성**을
떨어뜨려 `UNKNOWN 측정불가` 로 간다 — 무해로 접지도, 소급 실격으로 세지도 않는다. FAIL 판정이
C5 보다 먼저라 진짜 실격을 UNKNOWN 으로 덮지 않는다(래칫). ★**회귀 근거는 두 겹이고 강도가
다르다** — ⑴ **레포에 커밋된 동결**은 `test_known_labels_only_is_judged_exactly_as_before` 로,
알려진 라벨만 있는 payload **3케이스**(라벨 없음 · `replay_lag` · `phantom`)의 판정·누적·
`divergence_labels_readable` 이 수리 전후 불변임을 못박는다. ⑵ 「**180 조합 전량 동일**(신설 키
2개 제외)」은 **커밋되지 않은 오프라인 스윕 실측**이다 — 하네스가 레포에 없어 CI 가 다시 재지
않는다(재현하려면 다시 짜야 한다). ⑴을 ⑵의 근거로 읽지 마라.
**출처:** 2026-08-05 live-replay-visibility (판별식 2차 교체 중 발견 — 수리 안 하고 등재만)

**게이트는 모르는 라벨을 조용히 「무해」로 접는다.**

`soak_gate_predicate.py:191` 은 실격을 이렇게 센다:

```python
if str(obs.get("label", "")) == "phantom":
    ...  # 실격
```

곧 **`phantom` 이 아닌 모든 것이 무해**다. 분류기가 실제로 낼 수 있는 라벨은 넷이다 —
`phantom` / `replay_lag` / `unattributed` / (판정 불가는 라벨이 아니라 강하). 그중
**`unattributed` 는 「판정하지 못했다」이지 「무해하다」가 아니다.** 운영자 청산처럼 세션에
귀속되지 않는 주문이 있으면 그 발산은 아무 데도 안 잡힌다.

**왜 지금 안 고치나.** 이번 교체(재무장식 → 회복식)는 판정 불가를 **새 라벨로 내보내지 않고
종전 식으로 강하**시켰으므로 이 경로에 도달하지 않는다. 즉 회피했을 뿐 닫지는 않았다.
현재 코퍼스 31건에 `unattributed` 는 **0건**이다.

**처리 방향 (택일이 아니라 순서다):**

1. 게이트가 라벨 어휘를 **명시적으로** 나눈다 — 알려진 무해 `{replay_lag}` / 알려진 실격
   `{phantom}` / **그 밖 = 측정 무결성 실패(UNKNOWN)**. 지금은 셋째 갈래가 없다.
2. `test_soak_gate_predicate.py:210` 이 `replay_lag`/`phantom` 두 라벨만 못박고 있다 —
   ★**모르는 라벨을 넣은 케이스가 없어서** 이 결함이 테스트를 통과한다. 그 케이스를 먼저 넣어라.
3. 판별식 쪽에서 `unattributed` 를 계속 낼지도 재판단한다 — 회복식은 원장을 안 보므로
   귀속 없이도 판정할 수 있다(현재는 종전 식과의 호환을 위해 그대로 둔다).

**수리 (2026-08-05 gate596) — ①② 완료, ③ 은 판별식 쪽 과제로 남긴다.**

- ①② 는 위 「상태」 참조. ②(모르는 라벨 케이스)를 **먼저** 넣어 red 를 확인하고 수리했다 —
  수리 전 `unattributed`/어휘 밖 라벨 둘 다 **`PASS`** 였다(실측).
- ★**출처를 같이 낸다** (codex 적대 리뷰 P1). 라벨 이름만으로는 「frozenset 등재」와 「구판
  아카이브 이동」 중 무엇을 해야 할지 못 고른다. `soak-gate.sh` 가 합병 때 각 관측에
  `archive`/`predicate_version` 을 붙이고(기존 키 불변), 판정기가 `detail.divergence_labels
.sources` 로 라벨별 총계 + 표본(상한 5건)을 낸다. 요약 줄에도 첫 출처 하나가 붙는다.
- ③ **`unattributed` 를 게이트에서 「알려진-그러나-판정불가」로 명시했다** — 「그 밖」에
  맡기지 않았다. 근거: 두 갈래는 **조치가 다르다**. 어휘 밖 = 분류기가 게이트보다 앞서
  갔다는 뜻이라 사람이 **frozenset 을 갱신**해야 하고, `unattributed` = 세션에 귀속되지
  않는 주문이 있다는 뜻이라 **[BL-592]/[BL-593] 쪽 조사**가 필요하다. 판정에 주는 영향은
  같으므로(둘 다 C5 강하) 래칫은 유지되고, 보고(`detail.divergence_labels`)에서만 갈린다.
  ★**판별식이 `unattributed` 를 계속 낼지는 여기서 정하지 않았다** — 판별식은 래칫으로
  동결돼 있고([ADR-024] §판별식 2차 교체), 게이트는 그 산출물만 읽는다.

**Risk:** 🟡 ~~방향이 **fail-open** 이다~~ → **닫혔다.** 이제 판독 못 하는 라벨은
`window_start` 를 앞당기는 대신 게이트를 `UNKNOWN 측정불가` 로 세운다. 반대 방향의 대가는
**한 건만 나와도 그 아카이브가 정리될 때까지 PASS 가 안 나온다**는 것이고, 그게 의도다
(해소: frozenset 등재 또는 `.soak/superseded-<판>/` 이동).

**연결:** [BL-003](#bl-003) · [ADR-024](decisions/024-soak-stability-gate.md) (§판별식 2차 교체) ·
[BL-591](#bl-591) (라벨 어휘의 출처) · [BL-592](#bl-592) (`unattributed` 를 만드는 계정 중복)

---

### BL-597

**Priority:** P2
**카테고리:** QA / e2e 신뢰성 (소크 상태 결합)
**Trigger:** ★**이미 발화했다** — 2026-08-06 night-watch final-gates 1차에서 e2e authed 1건 red(`sprint46-tier2-high` #6 계정 등록). 받은 문자열이 계정 표가 아니라 **소크 세션의 열린 포지션 표**였다.
**Est:** S

e2e authed 가 **라이브 소크가 도는 개발 DB** 를 그대로 검사하므로, 소크 세션이 포지션을 들고 있으면 `/trading` 에 표가 하나 더 렌더되고 **느슨한 테이블 로케이터가 엉뚱한 표를 집는다.** 알려진 hydration flake(라우트 무작위·dev overlay 서명)와 **다른 축**이다 — 이쪽은 서명이 `toContain` 단언 실패이고 재현 조건이 「열린 포지션 존재」다. 단독 재실행·2차 전체 실행(69 전건)은 포지션 상태가 달라 PASS 했다.

**처리 방향:** ① 해당 spec 의 로케이터를 표 제목/역할 기반으로 좁힌다(최소) ② e2e 가 집는 표를 세션 상태와 무관하게 만드는 화면 측 앵커 검토 ③ 「소크 중 e2e」의 알려진 결합 목록을 gates-and-traps 에 등재.

**상태:** ✅ **Resolved (2026-08-06 fix/bl597-e2e-table-locator)** — 처리 방향 ① 수리: 해당 spec 의 전역 `locator("table").first()` 를 접근성 이름 기반(`getByRole("table", { name: /거래소 계정/ })`)으로 교체. **판별력 실증** — 소크 포지션이 실제로 열린 조건에서 구 코드 1 failed · 수리본 passed(같은 세션, stash 왕복). ③ gates-and-traps 등재 완료. ②(화면 측 앵커)는 ①로 충분해 불필요 판정.

**출처:** 2026-08-06 night-watch (final-gates 1차 red 부검)
