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

| ID                | 제목                                        | Trigger              | Est      | 출처                 |
| ----------------- | ------------------------------------------- | -------------------- | -------- | -------------------- |
| [BL-003](#bl-003) | Bybit mainnet 진입 runbook + smoke 스크립트 | H1 Stealth 종료 직전 | M (4-5h) | 2026-04-30 TODO 이력 |

> 추가 P0 — BL-005 본인 dogfood + BL-145 EffectiveLeverageEvaluator (deferred). Resolved P0 = BL-001/002/004 (`_archived.md`).

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

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                       | Trigger                                                                      | Est      | 출처                        |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------- | --------------------------- |
| [BL-014](#bl-014) | 🟡 부분 Resolved — Partial fill `cumExecQty` tracking (잔여 = BL-439/440/441)                                                                                                                                                                                                                                                                                              | 🟡 2026-07-25 `stage/money-path-accuracy`                                    | M (4-5h) | TODO.md L709                |
| [BL-015](#bl-015) | OKX Private WS                                                                                                                                                                                                                                                                                                                                                             | Bybit Demo 안정화 후                                                         | M (6-8h) | TODO.md L710                |
| [BL-022](#bl-022) | ✅ golden expectations 재생성 — **Resolved** (2026-08-07 backtest-fidelity). `backend/scripts/regen_golden.py` 신설(`--confirm`/`--case`/`--check`). ★이 스크립트가 없었던 것이 [BL-621] stale 의 직접 원인이다                                                                                                                                                            | pine_v2 `strategy.exit` 도입 후                                              | M (3-4h) | TODO.md L17 (skip #1)       |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                                                                                                                                                                                                                                                                                               | Trust Layer v2 검토 시                                                       | M (5-6h) | TODO.md L23 (skip #16)      |
| [BL-024](#bl-024) | real_broker E2E 본 구현 (nightly cron)                                                                                                                                                                                                                                                                                                                                     | Bybit Demo credentials + seed data 준비 시                                   | L (8h+)  | CLAUDE.md Sprint 10 Phase C |
| [BL-025](#bl-025) | autonomous-parallel-sprints 스킬 patch                                                                                                                                                                                                                                                                                                                                     | on-demand (BUG-1/2/3 재발 시)                                                | S (2h)   | TODO.md L653                |
| [BL-026](#bl-026) | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                                                                                                                                                                                                                                                                                                            | Stage 2c 2차 fixture 활성화 후                                               | S (1-2h) | TODO.md L20-22              |
| [BL-619](#bl-619) | ★**라이브 파이프라인이 한 세션에 ~17분 멈췄고 뿌리를 모른다** — 서버 `.soak/logs` 는 존재하지 않아 로컬 전용 비추적 `.soak/logs/follow.sh` 가 서버에는 배포된 적 없다. 로그 소실은 그대로이며, 추적 `scripts/soak-logs-follow.sh` 와 systemd unit 승격 경로를 만든 뒤 다음 서버 소크에서 재관측해야 한다                                                                   | 다음 서버 소크 창에서 같은 정지가 관측되면 (로그가 남아 있는 동안 즉시 부검) | M        | 2026-08-08 bl003-unblock    |
| [BL-633](#bl-633) | ✅ **이중 호스트 오염 — 근인 확정** — 같은 Bybit demo 계정의 맥 로컬 체결이 서버 세션 `39484a2c` 를 죽였다. G-A4‴ 소유권 7/27(귀속 불가 0)·G-A6′ 정본 항등식 4/4(반사실은 정의 4가지 어디서도 4/4 불가, 최대 1/4)·G-A7 계정 결합 27/27 이 뒷받침한다. ★원안 G-A4′ 6/6·G-A6 3/3 은 회차 도중 반증돼 교체됐다. `phantom` 은 증상이며, 오염 창은 ADR-025 의 반례로 셀 수 없다 | — (부검 완료 · 후속은 BL-634 · BL-641 로 이관)                               | M        | 2026-08-08 bl003-unblock    |
| [BL-634](#bl-634) | 같은 Bybit demo 계정에 두 호스트가 동시에 붙는 계정 배타성 가드 부재 — 두 DB 의 `live_signal_sessions` unique index 는 다른 호스트를 막지 못하며, 이번 `position_divergence` 사망의 직접 원인이다                                                                                                                                                                          | 실자금 전환 전 필수 / 두 번째 호스트를 다시 띄우기 전                        | M        | 2026-08-08 bl003-unblock    |
| [BL-635](#bl-635) | ✅ **게이트 아카이브 오염이 라이브 기전이다** — 판독 불가 로그를 시간 credit 하지 않고 `UNKNOWN 측정불가`로 내리도록 `32ea2a5d` 에서 수리했다. 서버 systemd 만 대상이며 맥 launchd 타이머는 잔여다                                                                                                                                                                         | — (해결됨. 맥 launchd 잔여는 별도 후속)                                      | S        | 2026-08-08 bl003-unblock    |
| [BL-641](#bl-641) | BL-003 의 실질 선행조건은 문턱이 아니라 **MTBF** 다 — 2026-08-03 이후 MTBF **8.70h**, P(168h) **4.115e-09** 이므로 168h 연속 무실격은 사실상 도달 불가다                                                                                                                                                                                                                   | BL-003 재계획 시 즉시 / 소크 재기동 회차마다 재측정                          | M        | 2026-08-08 bl003-unblock    |

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

## P2 — Hardening / 건강도 작업

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Trigger                                                                                                         | Est          | 출처                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ | --------------------------------------------------- |
| [BL-522](#bl-522) | ★엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다 (유실 채널 5종)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 실자금 cutover 전 필수                                                                                          | M-L          | 2026-07-28 live-entry-parity                        |
| [BL-186](#bl-186) | 🟡 부분 Resolved (186a) — Full leverage + funding + mm + liquidation 풀 모델 (잔여 = BL-186b)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Sprint 38+ (BL-185 foundation 위)                                                                               | M-L (16-24h) | Sprint 37 BL-185 후속                               |
| [BL-190](#bl-190) | PDF export (jsPDF / Playwright)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 외부 사용자 요청 시                                                                                             | M (3-5h)     | Sprint 41 Worker H 결정                             |
| [BL-195](#bl-195) | qb-form-slide-down animation 영구 truncation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Sprint 45 codex G.4                                                                                             | XS (30m)     | Sprint 45 codex G.4 발견                            |
| [BL-235](#bl-235) | N-dim acquisition surface viz (Bayesian 전용)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Sprint 57+                                                                                                      | M (8-12h)    | ADR-013 §6 #8 deferred                              |
| [BL-236](#bl-236) | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Sprint 56+                                                                                                      | S (3-5h)     | Sprint 55 deferred                                  |
| [BL-363](#bl-363) | stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | deepening sprint 또는 5번째 engine 추가 시                                                                      | S (2-3h)     | 2026-05-30 full-inspection §appendix P1-9           |
| [BL-364](#bl-364) | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | string 카테고리 sweep 요청 시                                                                                   | M (4-6h)     | 2026-05-30 full-inspection §appendix P1-9 (S4 후속) |
| [BL-366](#bl-366) | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | trading deepening sprint                                                                                        | S-M (3-5h)   | 2026-06-26 trading-deepen-2                         |
| [BL-368](#bl-368) | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | trading deepening / 4번째 provider                                                                              | S-M (3-5h)   | 2026-06-26 trading-deepen-2                         |
| [BL-369](#bl-369) | 3 provider `create_order` try/except/finally ~40 LOC 복붙                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | trading deepening sprint                                                                                        | S (2-4h)     | 2026-06-26 trading-deepen-2                         |
| [BL-372](#bl-372) | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Wave 3 실자금 cutover 전                                                                                        | M (6-10h)    | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)  |
| [BL-373](#bl-373) | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | BL-365 standalone-trigger 발주 시                                                                               | S-M (3-5h)   | 2026-06-28 grilling (트레일링 후속 scope)           |
| [BL-375](#bl-375) | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Wave 3 실자금 cutover 전                                                                                        | S-M (3-5h)   | 2026-06-29 BL-372 same-side stale G1 codex          |
| [BL-379](#bl-379) | pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐, latent harm-class)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | pine_v2 robustness 후속                                                                                         | M (4-6h)     | 2026-06-30 QA codex G2 + 직접 재현                  |
| [BL-380](#bl-380) | Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반) + VirtualRunResult.warnings 미전파                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Track A 신뢰 표면 sprint                                                                                        | S-M (3-5h)   | 2026-06-30 QA LuxAlgo 0-trade                       |
| [BL-381](#bl-381) | Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허 (i2_luxalgo 검증 vacuous)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Trust Layer CI 강화                                                                                             | S (2-4h)     | 2026-06-30 QA codex G2/diff                         |
| [BL-382](#bl-382) | qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성, mdd_exceeds_capital 은 표시됨)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | sizing 투명성 sprint                                                                                            | S (2-4h)     | 2026-06-30 QA F1 (codex G2)                         |
| [BL-387](#bl-387) | backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 횡단 (key drift 시 silent 잘못된 sizing, money-path)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | backtest deepening 또는 sizing 로직 변경 시                                                                     | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 최강 후보)        |
| [BL-392](#bl-392) | stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass↔serializer↔OutSchema, untyped JSONB seam)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | stress_test deepening 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시                                  | M (4-6h)     | 2026-06-30 stress_test-deepen (deepen-modules 1차)  |
| [BL-523](#bl-523) | 조건부·전환 진입에 TP/SL 브래킷이 붙지 않는다 (현재 코퍼스 미발현 — `stop=`+`strategy.exit` 동시 사용 시 발현)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 실자금 cutover 전                                                                                               | M            | 2026-07-28 live-entry-parity                        |
| [BL-524](#bl-524) | `strategy.entry(limit=...)` 이 조용히 버려지고 시장가 진입으로 대체된다 (TV 충실도)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | limit 진입 전략 지원 시                                                                                         | M            | 2026-07-28 live-entry-parity                        |
| [BL-527](#bl-527) | ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 기대치 정확도가 판정에 쓰이기 전                                                                                | S            | 2026-07-28 live-outcome-parity                      |
| [BL-528](#bl-528) | 세션 창 밖 늦은 체결이 어느 표면에도 안 잡힌다 (실측 확정 청산 4건 · net −0.5463)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 세션 손익 완결성이 필요할 때                                                                                    | M            | 2026-07-28 live-outcome-parity                      |
| [BL-529](#bl-529) | 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 전략 누적 지표를 신뢰해야 할 때                                                                                 | S            | 2026-07-28 live-outcome-parity                      |
| [BL-531](#bl-531) | parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery (지표 1개 추가 = 5파일 편집)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | parity 지표를 더 붙일 때                                                                                        | S            | 2026-07-29 PR #496 코드리뷰                         |
| [BL-532](#bl-532) | `_sum_decimals` 사본이 `PARITY_DECIMAL_CONTEXT` 밖에서 돈다 (본 레포가 방금 세운 규칙과 불일치)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 다음 parity 손질 시                                                                                             | XS           | 2026-07-29 PR #496 코드리뷰                         |
| [BL-533](#bl-533) | 종료 세션 목록이 같은 엔드포인트를 두 쿼리 키로 조회해 미러 state 를 낳는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 코크핏 손질 시                                                                                                  | XS           | 2026-07-29 PR #496 코드리뷰                         |
| [BL-534](#bl-534) | 외부 오라클 테스트가 27 leg Decimal 합산을 실제로 실행하지 않는다 (총계를 관측 1건에 몰아넣음)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | parity 산술을 손댈 때                                                                                           | XS           | 2026-07-29 PR #496 코드리뷰                         |
| [BL-538](#bl-538) | 발산 알림 본문이 모든 카테고리에 "전략 수정 후 재활성화" 라고 처방한다 (포지션 불일치엔 틀린 처방)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 운영 알림을 사람이 신뢰해야 할 때                                                                               | S            | 2026-07-29 PR #497 사후 리뷰                        |
| [BL-541](#bl-541) | 세션 행이 아예 없는 포지션(웹훅 경로·거래소 수동)은 여전히 앱에서 못 닫는다 — ★아직 실측된 적 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | `no_owning_session` 이 실제로 관측될 때                                                                         | M            | 2026-07-29 live-orphan-close                        |
| [BL-545](#bl-545) | ★gap-resync 게이트가 5% 수량 허용치를 물려받아 구 게이트가 막던 불일치를 통과시킨다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 조건부 진입을 실자금으로 가기 전                                                                                | S            | 2026-07-30 conditional-entry-alignment              |
| [BL-546](#bl-546) | 원장→엔진 seed 경계에서 `Decimal` 이 `float` 로 강등 (Decimal-first 하드 규칙)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 엔진 수치 표현을 손댈 때 / 큰 notional                                                                          | M            | 2026-07-30 conditional-entry-alignment              |
| [BL-547](#bl-547) | ★원장 seed 가 그 tick 한 번만 산다 — 조용한 고아 가능 (**아직 실측된 적 없음**)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | `exchange_only` 이 실제로 오르는 것이 관측될 때                                                                 | M            | 2026-07-30 conditional-entry-alignment              |
| [BL-553](#bl-553) | ★`outcome="applied"`(원장 seed 주입)가 실주행에서 한 번도 안 밟혔다 — 단위테스트로만 증명                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 다음 soak (기회주의적 확인)                                                                                     | XS           | 2026-07-30 conditional-entry-alignment              |
| [BL-556](#bl-556) | `final-gates.sh` 가 `pnpm e2e`(chromium 4건)를 집행하지 않는다 — CI e2e 잡에는 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 다음 회차 게이트 실행 전                                                                                        | XS           | 2026-07-30 live-entry-completeness                  |
| [BL-558](#bl-558) | retCode 를 `error_message` 에 싣는 경로가 **동기 1곳뿐** — 비동기 확정 거절이 코드 미상이 된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 거절 코드로 채널을 가를 때                                                                                      | M            | 2026-07-30 live-entry-completeness                  |
| [BL-565](#bl-565) | `check_exit_fills` 의 close 도 BL-560 과 같은 성질 — 읽기만 하고 남겼다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `strategy.exit` 을 쓰는 전략을 라이브로 돌리기 전                                                               | S            | 2026-07-31 reversal-ledger-sync                     |
| [BL-567](#bl-567) | `place_trailing_stop` enqueue 가 실패하면 그 주문의 트레일링은 **영구 유실** — 회수 경로가 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 트레일링 전략을 라이브로 상시 운용하기 전                                                                       | —            | 2026-07-31 reversal-ledger-sync                     |
| [BL-568](#bl-568) | BL-562 체결시점 반전 계측이 **11건 중 10건 무측정** — 분류된 건이 0 이다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 그 분포를 근거로 무언가를 판단하기 전                                                                           | S            | 2026-08-01 ledgerhygiene                            |
| [BL-574](#bl-574) | ★`LIMIT 100` 이 세션 필터보다 앞서 걸려 현 세션 resting 을 놓치고 `awaiting_trigger` 를 `unexplained` 로 오분류 (측정 완료 · 수리 보류 — 동시 최대 2 / 100)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 동시 resting 이 20건을 넘긴 날이 관측될 때                                                                      | S            | 2026-08-01 soak codex                               |
| [BL-575](#bl-575) | SELECT 실패 후 같은 AsyncSession 을 rollback 없이 재사용 — fail-open 계약이 깨진다 (★선재 패턴, 회귀 아님)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | fail-open 을 근거로 쓰기 전                                                                                     | S            | 2026-08-01 soak codex                               |
| [BL-580](#bl-580) | 계측 가드 잔여 **96곳** (누적 63곳 수리). ★산문 근거 29곳이 주입에서 **29곳 전건 유해** — 「가드 없이 유지」 누적 0곳. ★2026-08-03 신규 **H8** = 계측 실패가 fail-open `except` 에 삼켜져 **거절을 집행으로 뒤집는다**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `qb_metrics_mutation_failed_total` 창 차분이 0 을 벗어날 때 (★프록시다 — 가드 밖은 이 counter 를 올리지 않는다) | M            | 2026-08-02 metric-guard-parity                      |
| [BL-591](#bl-591) | ★**뿌리** — 엔진 포지션의 SSOT 가 없다. `run_live` 시뮬이 매 tick 봉을 재생해 포지션을 **도출**하고 정상 운행 중엔 현실로 **보정되지 않는다**. 슬라이스 1(계측) = **PR #539 OPEN**(통합 브랜치 `stage/engine-position-ssot`, 미머지). ★★★**슬라이스 2 미착수 확정** — 사전등록 V1 발동(④ = 0: 사망 2건의 상류에 `exchange_only` 0건 · 최악 상계 ≤1/21). ★★★**유도 함수 재설계 필요** — `trade_id` 는 trade 가 아니라 Pine 진입 규칙 이름이고(`PivRevSE` 56체결/19세션) 반전은 `:close:` 키를 안 만든다 ⇒ 판정 불가 **27.6%**(전량 `duplicate_open`) · **net 은 맞고 legs 는 틀리다**(오라클 11건: 오답 0 · 적중 4 중 3건이 `legs=2` 인데 거래소는 단일 포지션 — 나머지 1건은 반전 없는 먼지 세션이라 정확) ★**2026-08-05 P1→P2 강등**(잔여 = D1/D2 · 근거는 §상태 줄) | 발산 증상 BL 을 또 하나 열기 전에 · 소크가 또 죽었을 때                                                         | L            | 2026-08-03 breach-rejection-recovery                |
| [BL-592](#bl-592) | 같은 Bybit 데모 계정이 `trading.exchange_accounts` 에 **2행**이라 청산 1건이 **2행으로 적재**되고, 주문을 안 가진 계정 쪽에서는 `ours` 가 **`unknown` 으로 오라벨**된다(실측 91/91 대칭). 원장 구멍 계측을 **3.7배 부풀린다** — [BL-591] 슬라이스 1 관측 전에 인지 필요                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `exchange_exits` 로 원장 구멍·귀속을 판정하기 전에                                                              | S            | 2026-08-04 engine-position-ssot                     |
| [BL-593](#bl-593) | 운영자 도구(`backend/scripts/verify_*.py` 등)가 `ClosePositionService` 를 못 써서 provider 를 **직접 호출** → 그 청산에 대응하는 `trading.orders` 행이 **없다**. 실측 `external_manual` **12건 / 103건(11.7%)**. [BL-591] C 안이 원장을 진실로 쓰므로 이 구멍이 곧 오주입 위험                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 소크를 끄거나 거래소를 손으로 flat 으로 만들기 전에                                                             | S            | 2026-08-04 engine-position-ssot                     |
| [BL-598](#bl-598) | ★**코퍼스 스크립트를 처음 파싱하는 테스트가 비용을 전부 문다** — `test_ast_classifier[i3_drfx]` 단독 **42.66s** vs 전체 스위트 안 **4.58s**. 프로세스 전역 비용이라 **쪼개면 샤드마다 중복**된다(CI 3샤드 합 1796s vs 단일 1278s, +519s 전부가 이 중복). 샤딩 저항의 뿌리이고 CI 14분 벽의 원인. 캐시 데코레이터는 **찾아봤고 없다** — 정체 규명이 먼저                                                                                                                                                                                                                                                                                                                                                                                                               | CI backend 를 14분 아래로 내리려 할 때 · pine_v2 코퍼스 테스트를 늘리기 전에                                    | M            | 2026-08-06 ci-diet                                  |
| [BL-603](#bl-603) | ✅ 백테스트 비용 가정이 라이브 실효의 **2.7배** — 가정 왕복 0.30%(fees 0.1+slip 0.05/leg) vs 원장 실측 왕복 **0.1101%**(taker 0.055%/leg 단일 성분, 84 event 중 77 이 8자리 일치·비-taker 잔차 0.03%). 매칭쌍 진입가 잔차 중앙 0.014% vs slippage 가정 0.05%. **2026-08-07 Resolved** — 0.00055/0.00014(두 SSOT+FE 미러 4곳), 왕복 0.138%. 코퍼스 `num_trades` 불변·`s3_rsid` 부호 반전                                                                                                                                                                                                                                                                                                                                                                               | 백테스트 손익을 라이브 예측치로 읽기 전 (비용 축이 3배 비관)                                                    | S            | 2026-08-06 backtest-reality-gap                     |
| [BL-605](#bl-605) | `exchange_exits` 가 같은 청산 event 를 **정확히 2행**(classification `ours`/`unknown` 쌍, payload 동일)으로 적재 — 실측 86 event = 172행. `SUM(closed_pnl)` 류 소비가 손익을 **정확히 2배** 계상한다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | exchange_exits 를 집계로 소비하는 코드를 추가하기 전                                                            | S            | 2026-08-06 backtest-reality-gap (eval2 실측)        |
| [BL-610](#bl-610) | `entry_completeness.py:158` 의 `source=` 문자열이 문서 대개편으로 삭제된 dev-log 경로를 가리킨다 — 런타임 무해(값일 뿐)지만 근거 추적이 git history 경유로 바뀌었다. 소크 중 `backend/src` 무접촉 원칙으로 이연                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | BL-003 소크 창 종료 후 첫 backend/src 정리 회차                                                                 | XS           | 2026-08-06 docs-overhaul (fix-doc)                  |
| [BL-611](#bl-611) | ✅ ★**메타-방법론 영구 규칙이 자동 로드에서 빠졌다** — 구 `.ai/common/global.md` §7 은 `paths` 없는 `.claude/rules/global.md` 로 **매 세션 무조건** 들어왔다(2026-08-07 실측 재현). ADR-026 이 이를 `generator-evaluator-pipeline.md` §8 로 옮기면서 **열어야만 읽히는** 문서가 됐다 — kickoff preflight(§8.1)·codex finding 코드 대조(§8.3)가 조용히 누락될 수 있다. **Resolved** — `AGENTS.md` 에 §8.1/§8.3 두 줄 인라인                                                                                                                                                                                                                                                                                                                                            | 다음 Sprint kickoff (Type A/B) 전                                                                               | S            | 2026-08-07 docs-overhaul 리뷰                       |
| [BL-625](#bl-625) | ★**플레이스홀더 시크릿이 development 에서는 아무 게이트에도 안 걸린다** — 서버 `backend/.env.local` 이 `CLERK_SECRET_KEY=sk_test_...`(문자 그대로)인데 API 는 정상 기동하고 `/health` 200 을 냈다. 호스트 uvicorn 이 인증 경로를 한 번도 안 밟아서 드러나지 않았고, 브라우저 첫 로그인 요청이 **전건 401** 로 터지고서야 보였다. `_enforce_production_safety` 가 이 계열을 알지만 **`app_env == production` 일 때만** 검사한다. ★2차: 루트 `.env` 인라인 주석(`# [필수 …]`)을 안 떼고 값을 옮기면 한글이 섞여 401 이 아니라 **500**(clerk SDK 헤더 ascii 인코딩)                                                                                                                                                                                                      | 새 호스트에 API 를 세울 때 · [BL-071] 발동 시                                                                   | S            | 2026-08-07 fe-oracle-deploy                         |
| [BL-632](#bl-632) | 골든을 오라클로 승격했지만 그 기대값은 **엔진 자신의 출력**이다(회귀 감지기이지 정확성 오라클이 아니다). ★반순환 근거가 이 축을 안 덮는다 — 손계산 오라클 `test_golden_oracle_ema_sltp.py` 는 4봉·고정 stop/limit 이라 **`ta.atr` 를 한 번도 안 탄다**. ⇒ [BL-621] 의 낡음을 만든 바로 그 축이 **구조적으로 오라클 밖**이다. BL-621 본문의 「틀린 값을 정본으로 고정하게 된다」 경고에 아직 답하지 않았다                                                                                                                                                                                                                                                                                                                                                             | 골든 값이 또 어긋났을 때 · 백테스트 정확성을 대외 주장해야 할 때                                                | M            | 2026-08-07 backtest-fidelity                        |
| [BL-631](#bl-631) | ✅ **소유자 없던 검사기 2종에 `docs-audit.sh` 를 붙였다** — ★★그전까지 **`runtime-check.mjs` 는 어느 게이트에도 안 붙어 죽은 채로 방치됐다** — `docs/` 재편 커밋 `fcc36bf7` 이후 playwright import 상대깊이가 안 따라와 `ERR_MODULE_NOT_FOUND` 로 즉사했고, 그래서 핸드오프 §8.5 의 **「다크 17벌 17/17 PASS」는 그 커밋 이후 한 번도 재현된 적 없는 숫자**였다(이번 회차가 고쳐 재현). 뿌리는 경로가 아니라 **소유자 부재** — `pnpm test`·CI·`docs-audit` 어디도 안 부른다                                                                                                                                                                                                                                                                                           | 다음에 `docs/` 를 재편하거나 프로토타입을 손대기 **전에**                                                       | S            | 2026-08-07 backtest-fidelity                        |
| [BL-624](#bl-624) | ★**게이트의 HTTP 갈래는 `PROMETHEUS_BEARER_TOKEN` 과 양립 불가** — `soak-gate.sh` 의 `curl -sf` 가 인증 헤더를 안 보내서 401 → `DARKNESS=null` → **C5⑷ 영구 ✗**. `APP_ENV=production` 과 무관하다(토큰이 있으면 development 에서도 강제). 2026-08-07 FE 배포 회차가 실측으로 물렸다 — 서버 체크아웃이 [BL-620] 이전이라 기본이 HTTP 였고 베어러를 켜자 즉시 C5 가 죽었다. ★판별자는 API 로그의 `GET /metrics` 유무다 — 게이트 출력의 `darkness_computed=✓` 는 **어느 경로로 성공했는지 말해주지 않는다**. 지금은 기본이 직독이라 미발동                                                                                                                                                                                                                               | `QB_METRICS_URL`(원격 데몬 + ssh 터널 운영안)을 실제로 쓰려 할 때                                               | S            | 2026-08-07 fe-oracle-deploy                         |
| [BL-620](#bl-620) | ✅ **소크 스택에 `/metrics` 를 내주는 것이 없어 게이트 C5 가 영구 ✗ 였다** — `soak-stack.sh up` 은 API 컨테이너를 안 띄우고 `:8100` 리스너가 0개라 **C1/C2 를 다 채워도 PASS 불가**였다. **Resolved** — 기본 취득을 HTTP → `backend/.metrics` **직독**으로 교체(워커가 같은 counter 를 거기 쓴다). ★PR #556 리뷰 후속: curl 갈래에도 `[ -n ]` 를 걸어 **`200 + 빈 본문` fail-open** 을 닫았고(초판은 직독 갈래에만 있었다), `QB_METRICS_DIR` 을 `.env.example` 에 등재했다(Golden Rule). 판정 `측정불가`→`진행중`, C5 전건 ✓. fail-closed 음성 대조 **3/3**. `QB_METRICS_URL` 명시 시 종전 HTTP 유지                                                                                                                                                                  | —                                                                                                               | S            | 2026-08-07 gap-resync-autopsy                       |
| [BL-636](#bl-636) | backlog 인덱스 표 파손 + `bl-audit.sh` 가 표 파손을 감지하지 못 한다 — 수리 전 P1 조각 1행과 P2 조각 13행은 GFM 표로 렌더되지 않았고, 이번 회차에 빈 줄 제거·재결합으로 104행을 보존했지만 검사 축은 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 다음 백로그 인덱스를 편집할 때                                                                                  | S            | 2026-08-08 bl003-unblock                            |
| [BL-637](#bl-637) | ✅ **`bl-audit.sh` 에 우선순위 배치 검사 축을 세웠다** — 수리 전 불일치 40건(뿌리는 P3 H2 아래에 인덱스 표가 아예 없어 새 P3 항목이 P2 표 꼬리에 붙은 것)을 제자리로 옮기고, 인덱스 행이 섹션 `**Priority:**` 와 같은 H2 표에 있는지를 4번째 축으로 검사한다. 주입 시험 2/2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 다음 백로그 인덱스를 편집할 때                                                                                  | S            | 2026-08-08 bl003-unblock                            |
| [BL-639](#bl-639) | 미조인 `exchange_exits` 상시 기저율 — 미조인 체결 이력으로 배타성을 판정하면 BL-605 중복 채널 때문에 상시 거부가 된다. 배타성 판단은 과거 이력이 아니라 미체결 조건부 주문을 대상으로 해야 한다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | BL-634 를 구현하기 전                                                                                           | S            | 2026-08-08 bl003-unblock                            |
| [BL-642](#bl-642) | `soak-observe.sh` 가 아직 `localhost:8100/metrics` 를 긁어 재기동 ⑺ 을 실패시킨다 — [BL-620] 이 게이트에 대해 닫은 그 경로다(`soak-stack.sh up` 은 API 컨테이너를 안 띄운다). 세션 등재는 ⑺ 전에 끝나므로 재기동 자체는 성공하지만 ⑻ 까지 못 가고, 빨간 줄이 진짜 실패처럼 보인다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 다음 소크 재기동                                                                                                | XS           | 2026-08-08 bl003-unblock                            |
| [BL-643](#bl-643) | `docs/status.md` 「다음 스프린트」 블록의 최신성을 어떤 게이트도 안 본다 — 끝난 일을 지시하는 「다음 행동」 2곳이 살아 있는 동안 bl-audit·docs-audit 이 둘 다 exit 0 이었다. ★단순 문자열 술어는 오탐한다(규칙을 설명하는 문장이 걸린다) ⇒ 필드 승격이 선행. ★PR #562 로 선행 착지 — §G8 **7필드**(⓪ 다음 후보 신설)이고 계약은 「정확히 1」이 아니라 **≤1**(안 고른 0개가 정상). 남은 것 = 술어 2개(⓪ 행수 ≥3 · 비취소선 「다음 행동」 ≤1)                                                                                                                                                                                                                                                                                                                           | 다음 회차 종결 시                                                                                               | S            | 2026-08-08 bl003-unblock                            |

> Resolved P2 = BL-027/137/140/140b/141/144/150/152/176/178/180/181/183/184/185/187/187a/188/188a/189/200~206/219~234/237 + 30+ Sprint 16~30 stale (`_archived.md`). + BL-603 (2026-08-07 gap-resync-autopsy). + BL-597 (2026-08-06 entry-set-divergence).

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

### BL-363

**Title:** stress*test `StressTestService.\_execute*\*`4-method boilerplate 추출
**Category:** Stress / Architecture (deep module)
**Priority:** P2
**Trigger:** deepening sprint 또는 5번째 stress engine 추가 시
**Est:** S (2-3h)
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

**권장 접근:** 머니-패스의 모든 metric mutation 을 `record_metric_safely` 로 감싸고, 그 규칙을 `backend/AGENTS.md` 에 등재한다.
**Risk:** 🟡

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived (BL-050/051/052/053/054/055/056/057/138/139/151/153). ~~**활성 P3 = 8**~~ ★**stale** — 2026-08-08 `bl-audit.sh` 실측 P3 ACTIVE **101**. 이 파일 헤더 규약대로 집계 수치는 여기 박지 말고 스크립트를 돌려라 (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2 + BL-389/390/391 2026-06-30 backtest-deepen). ★2026-08-06 entry-set-divergence 강등 = BL-606/607/608/609.

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Trigger                                                                                                           | Est       | 출처                                                   |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------ |
| [BL-377](#bl-377) | pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)                                                                                                                                                                                                                                                                                                                                                                                                      | pine_v2 robustness 후속 또는 실자금 cutover 전                                                                    | S (2-4h)  | 2026-06-30 BL-376 G2 codex challenge + G3 fresh review |
| [BL-383](#bl-383) | v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)                                                                                                                                                                                                                                                                                                                                                                                                                        | pine_v2 관측성 후속                                                                                               | S (2-3h)  | 2026-06-30 QA codex G2                                 |
| [BL-384](#bl-384) | ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)                                                                                                                                                                                                                                                                                                                                                                                                                                    | pine_v2 parity 후속                                                                                               | S (2-3h)  | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-385](#bl-385) | PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse (메타데이터 부정확)                                                                                                                                                                                                                                                                                                                                                                                                              | pine_v2 coverage 후속                                                                                             | XS (1-2h) | 2026-06-30 QA F3                                       |
| [BL-386](#bl-386) | v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject, over-strict)                                                                                                                                                                                                                                                                                                                                                                                                    | pine_v2 coverage 후속                                                                                             | XS (1-2h) | 2026-06-30 QA F4                                       |
| [BL-525](#bl-525) | 라이브가 Track A(indicator + alertcondition) 전략을 어떻게 다루는지 정의되지 않았다                                                                                                                                                                                                                                                                                                                                                                                                          | Track A 로 라이브 세션을 열 때                                                                                    | S         | 2026-07-28 live-entry-parity                           |
| [BL-539](#bl-539) | (P3) 방향 불일치 유예가 시간 경계가 없다 — 평가가 드문드문하면 오래된 strike 가 살아남는다                                                                                                                                                                                                                                                                                                                                                                                                   | 발산 가드를 다시 손댈 때                                                                                          | S         | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-540](#bl-540) | (P3) `live_signal.py` 반복 3종 — deactivate 의식 6회 · provider+creds 4회 · category 가 맨 `str`                                                                                                                                                                                                                                                                                                                                                                                             | 이 파일을 다시 크게 손댈 때                                                                                       | M         | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-548](#bl-548) | (P3) `OutcomeParityPanel` 이 375px 에서 본문 가로 스크롤 24px 을 만든다 (기존 결함)                                                                                                                                                                                                                                                                                                                                                                                                          | 모바일 폭 점검 시                                                                                                 | XS        | 2026-07-30 conditional-entry-alignment                 |
| [BL-550](#bl-550) | (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다                                                                                                                                                                                                                                                                                                                                                                                                                                      | 죽은 세션을 세션 단위로 대조해야 할 때                                                                            | S         | 2026-07-30 conditional-entry-alignment                 |
| [BL-551](#bl-551) | (P3) 라이브 세션 상세 진입이 URL 파라미터가 아니다 — 딥링크·새로고침 불가                                                                                                                                                                                                                                                                                                                                                                                                                    | 세션 상세를 링크로 공유해야 할 때                                                                                 | S         | 2026-07-30 conditional-entry-alignment                 |
| [BL-557](#bl-557) | (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳                                                                                                                                                                                                                                                                                                                                                                                                              | 그 게이지로 무언가를 판단하기 전                                                                                  | S         | 2026-07-30 live-entry-completeness                     |
| [BL-559](#bl-559) | (P3) 진입 완결성 도구 잔여 3건 — 세션 목록 절단 감지 · 사문 라벨 · janitor probe 전이                                                                                                                                                                                                                                                                                                                                                                                                        | 그 경로가 실측될 때                                                                                               | S         | 2026-07-30 live-entry-completeness                     |
| [BL-564](#bl-564) | (P3) `bl-audit.sh` 가 코드펜스 · `<details>` 안의 옛 상태줄을 SSOT 로 오인할 수 있다                                                                                                                                                                                                                                                                                                                                                                                                         | 그 관용구가 상태줄을 품게 될 때                                                                                   | XS        | 2026-07-30 close-mismatch-soak                         |
| [BL-573](#bl-573) | (P3) `engine_only` tick 당 `list_resting_conditional_entries` 2회 — 감지가 reconcile 보다 앞서 돌아 공유 불가                                                                                                                                                                                                                                                                                                                                                                                | tick 비용을 손댈 때 / 두 경로를 합칠 때                                                                           | S         | 2026-08-01 soak codex                                  |
| [BL-581](#bl-581) | `/metrics` 영구 누적 **10277 파일 · 635MB · PID 1968** (counter 삭제 금지)                                                                                                                                                                                                                                                                                                                                                                                                                   | 20000 파일 초과 · 스크레이프 지연 · 여유 20G 미만                                                                 | M         | 2026-08-02 metric-guard-parity                         |
| [BL-582](#bl-582) | divergence counter 13 series 중 **5종** 도달 불가 (2026-08-03 재판정 — 7종에서 축소. 2종은 엔진 구동으로 **반증**), 프로덕션 확인 3/8                                                                                                                                                                                                                                                                                                                                                        | 반증된 2종이 프로덕션에서 발화하거나 `other` def-use 오라클이 red 일 때                                           | S         | 2026-08-02 metric-guard-parity                         |
| [BL-584](#bl-584) | `BalanceUnverified` 가 라이브 dispatch 의 결정론적-거절 튜플 양쪽에 없다 — 소진 시 실제 사유가 `max_retries_exhausted` 로 덮인다. ★2026-08-03 **현재 코퍼스 도달 불가 확정**(계정 mode 는 생성 후 불변 · `mode=live` 계정 0건) ⇒ 수리 보류, Trigger 를 cutover 로 보강                                                                                                                                                                                                                       | **`mode=live` 계정이 생성될 때**(Wave 3 cutover), 또는 `outcome="max_retries_exhausted"` 창 차분이 0 을 벗어날 때 | S         | 2026-08-03 metric-guard-residual-close                 |
| [BL-578](#bl-578) | 조건부 진입 `110092`/`110093` 거절 시 거래소가 준 정답(`current[...]`)을 버린다 — BL-536 재판정에서 유일하게 살아남은 채널의 잔여 (측정 완료 · 수리 보류)                                                                                                                                                                                                                                                                                                                                    | C1 거절이 하루 3건 이상으로 다시 오르거나 실자금 cutover 로 1건 비용이 달라질 때                                  | S         | 2026-08-01 entry-completeness-rejudgement              |
| [BL-586](#bl-586) | ✅ **Resolved** 2026-08-07 backtest-fidelity — 키 리스트를 `dataclasses.fields()` 자동 유도로 교체(스칼라 46 전량 + 리스트 3종 digest + 중첩 2종 평탄화 + `RawTrade` 22 전량). 원 증상: P-3 골든이 `BacktestMetrics` **51 중 13**, `RawTrade` **22 중 11** 만 고정해 38+11 이 회귀 감지 밖                                                                                                                                                                                                   | TV parity 팩·비용 분해·청산 지표에서 회귀가 의심될 때                                                             | M         | 2026-08-03 backtest-metric-oracle                      |
| [BL-599](#bl-599) | Pine v1 shim(`src/strategy/pine/` 135L)은 타입 4종만 재export 하는 껍데기지만 `BacktestOutcome.parse` 가 코어 DTO 필드라 **단독 철거 불가**. 소비처는 「2곳」보다 넓다 — 프로덕션 import 2 + 생성 site 10+ + 테스트 3파일                                                                                                                                                                                                                                                                    | `BacktestOutcome` 를 손볼 일이 생겼을 때 (단독으로 열지 마라)                                                     | M         | 2026-08-06 dead-code-sweep                             |
| [BL-600](#bl-600) | `strategy/trading_sessions.py:26` 의 `TradingSession` 이 CONTEXT 헌법의 _Avoid_ 이름과 **동음이의 충돌**(이쪽은 장중 시간대 필터). 값이 `Strategy.trading_sessions` **JSONB 에 영속**돼 단순 rename 불가                                                                                                                                                                                                                                                                                     | `trading_sessions` JSONB 를 마이그레이션할 때 · 도메인 용어 정리 시                                               | M         | 2026-08-06 dead-code-sweep                             |
| [BL-601](#bl-601) | 호출 0건 잔재 3종 — `OrderRepository.get_state_fresh` · `list_unsynced_reduce_only_since` · `scripts/fleet-dispatch-test.sh`. ★원안의 「고아 하니스 3종」은 **1종으로 정정**(나머지 둘은 final-gates 체인 안에 있다)                                                                                                                                                                                                                                                                         | `OrderRepository` 를 손볼 때 함께 · 다음 dead-code 스윕                                                           | S         | 2026-08-06 dead-code-sweep                             |
| [BL-602](#bl-602) | ★**루트 prettier 가 `frontend/` 안의 json/md/yml 을 포맷하지 못한다** — `frontend/.prettierrc` 가 `prettier-plugin-tailwindcss` 를 선언하는데 lint-staged 는 **루트**에서 prettier 를 돌리고 루트 `node_modules` 엔 그 플러그인이 없다. ⇒ `frontend/package.json` 을 스테이징하는 커밋은 **pre-commit 에서 죽는다**(실측 재현)                                                                                                                                                               | `frontend/` 안의 json/md/yml 을 커밋해야 할 때 (지금은 우회 가능하지만 다음엔 막힌다)                             | S         | 2026-08-06 e2e-consolidation                           |
| [BL-612](#bl-612) | `docs/dev-log/2026-08-06-entry-set-divergence.md` 버퍼가 `docs/lessons.md` 로 승격되지 않았다 — ADR-026 §3 은 「세션 종결 시 승격 의무, 승격하면 버퍼를 비운다」인데 회차는 끝났고(PR #553 머지) 버퍼는 9천자로 남아 있다(반증 카드 상한 1~2천자 초과)                                                                                                                                                                                                                                       | 다음 문서 정리 회차                                                                                               | XS        | 2026-08-07 docs-overhaul 리뷰                          |
| [BL-613](#bl-613) | `live_signal.py` 핸들러 가시화가 남긴 **줄 수 부채** — `_evaluate_session_with_engine` **506줄**(Kind B 추출 E8~E14 미완) · `_place_planned_entry` 236 · `_reconcile_conditional_entries_inner` 203 · `_async_dispatch_event` 256(최대 `try` 본문 **225줄** — 이제 이게 최대). ★가시성 목표(최대 try 845→8)는 달성됐고 줄 수는 못 채웠다                                                                                                                                                     | `live_signal.py` 를 다음에 크게 손댈 때 ([BL-580] 착수 회차와 겹친다)                                             | M         | 2026-08-04 handler-visibility (status 승계)            |
| [BL-614](#bl-614) | 2026-08-04 handler-visibility 회차 방법론 **3건이 `docs/lessons.md` 미승격** — dev-log 본문은 문서 대개편에서 삭제됐고 INDEX 한 줄과 git history 에만 남았다(다중집합↔문장 순서 · 재적재 지문 = celery 배너 · 검증 도구를 먼저 적대 검증)                                                                                                                                                                                                                                                    | 다음 문서 정리 회차 ([BL-612] 와 함께)                                                                            | XS        | 2026-08-04 handler-visibility (status 승계)            |
| [BL-615](#bl-615) | 스택 규칙 파일이 공식 권장 크기의 **2배** — `backend/AGENTS.md` **416줄** · `frontend/AGENTS.md` **316줄** (Claude Code 문서 권장 = 파일당 200줄 이하, 「Longer files consume more context and reduce adherence」). 그 디렉터리 파일을 열 때마다 전량 로드된다                                                                                                                                                                                                                               | 스택 규칙을 다음에 손댈 때 ([ADR-027] 정착 후)                                                                    | S         | 2026-08-07 ADR-027 (배치 이전 중 실측)                 |
| [BL-616](#bl-616) | 부트스트랩을 **우회해 만든** 워크트리는 husky 훅이 없다 — `pnpm install` 을 건너뛰면 `prepare: husky` 가 안 돌아 `.husky/_`(미트래킹)가 안 생기고, git 은 없는 `core.hooksPath` 를 **경고 없이 무시**한다. 실태: 워크트리 5개 중 **4개 정상**, 우회 생성된 1개만 결손(2026-08-07 정상화 완료). ★남은 축 = **감지 수단이 없다** — 훅이 안 도는 실패 모드는 출력이 0줄이라 「통과」와 구별되지 않는다                                                                                          | 워크트리에서 훅 미작동이 또 관측되면                                                                              | S         | 2026-08-07 ADR-027 회차 (자기 커밋에서 발견)           |
| [BL-618](#bl-618) | ★**반응형 브레이크포인트 정본이 셋인데 서로 다르다** — `DESIGN.md` 가 자기 자신과 어긋나고(§10.2 「1200px↓ 사이드바 축소」 vs §10.6 「1024px~」), 2세대 `_kit.html` 실측(사이드바 232/64 · 컨테이너 1240 · 검색바 숨김 1024)과도 어긋나며(`DESIGN.md` 220/60 · 1200), `frontend/AGENTS.md` 는 Tailwind 기본값만 규정하고 셸 고유 값은 0건이다. `HANDOFF-react-port.md` 가 「1024px 아이콘 레일」을 🔴 미구현으로 등재해 둔 상태라 **어느 값이 정본인지부터 정해야** 그 구현을 시작할 수 있다 | 앱 셸 반응형(사이드바 축소·검색바 숨김·컨테이너 폭)을 다음에 손댈 때                                              | S         | 2026-08-07 prototype-canon-v2                          |
| [BL-617](#bl-617) | ★**「과거 기록」이 아닌 운영 절차 4종이 working tree 밖으로 나갔다** — Cloud Run 런북(39KB)·Grafana 셋업·Bybit mainnet 체크리스트(11KB)·법무 임시 런북. ADR-026 의 분류 기준이 **위치**(폴더 이름)였지 미래 유용성이 아니었던 결과다. 머지 후 `docs/` 전체에서 Cloud Run·Grafana·Prometheus·mainnet·법무 언급 **0건**인데 `alerts.yml`·`Dockerfile`·워크플로 4종은 레포에 살아 있다. ★지금 되살리지 않는다 — 트리거 시점에 갱신해 재등재                                                     | [BL-071] 프로덕션 배포 발동 시 · Bybit mainnet 전환 시                                                            | S         | 2026-08-07 PR #554 리뷰                                |
| [BL-621](#bl-621) | ✅ **골든 `expected.json` 이 두 겹으로 낡아 있었다** — 손익 3지표가 2026-06-26(`80a2138e`) 이후 동결인데 그 뒤 ⑴ `cda575f2` 가 `ta.atr` 를 rolling SMA → Wilder RMA 로 바꾸고 ⑵ [BL-603] 이 비용 기본값을 내렸다. **Resolved** — 구 ATR + 구 비용을 **동시에** 되돌리자 4지표 전건 byte-identical 재현(⑴로 원인 특정). ★유일하게 보던 `num_trades` 는 네 조합 전부 14 라 **판별력 0** 이었다. `regen_golden.py` 신설 + `test_golden_backtest.py` 를 실제 오라클로 승격                       | —                                                                                                                 | XS        | 2026-08-07 gap-resync-autopsy                          |
| [BL-627](#bl-627) | `regen_golden.py` 에 출력 경로 리다이렉트가 없어 라운드트립 시험이 **실제 `expected.json` 을 두 번 덮어쓰고 finally 에서 바이트 복원**한다 — 정상 종료 시 오염 0이지만 강제 종료되면 워킹 트리가 더러워진다. `--out-dir` 추가가 수리. ★부수: `--check` 의 「차이 없음」 종료 코드가 계약에 미명시                                                                                                                                                                                            | `regen_golden.py` 를 CI·병렬 실행에 넣을 때                                                                       | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-628](#bl-628) | 마케팅 푸터 법적 고지가 `--warning` 을 `--warning-subtle` 위에 얹어 **5.66:1**(캐논 5.82 미달, AA 통과) — 공개 4라우트 라이트 canon **68 > 다크 24** 미충족의 **단일 원인**이다(인증 12라우트 171 ≤ 255 충족 · 전체 16라우트 239 ≤ 279 충족). ★B2 가 만든 게 아니다 — 구팔레트에선 같은 자리가 **4.30:1 = AA 하드 실패**였다                                                                                                                                                                 | 라이트 공개 라우트 canon 을 다크 이하로 내리려 할 때                                                              | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-629](#bl-629) | `--chart-axis` 는 정의만 있고 **아무도 안 읽는 데드 토큰**이다 — `chart-tokens.ts:65` 는 `--text-muted` 를 축 색으로 읽고 `--chart-axis` 참조는 `frontend/src` 전체에 0건. 증거: 다크 `--text-muted` 는 캐논 교정으로 `#8b939c` 가 됐는데 `--chart-axis` 는 구값 `#7a828c` 에 남아 있다                                                                                                                                                                                                      | 차트 축 색을 손대려 할 때 · 토큰 정리 스윕                                                                        | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-630](#bl-630) | `.pos`/`.neg` **단독**(`.num` 없이)은 여전히 `td` 색에 진다 — 핸드오프가 등재한 「표 손익 색이 죽었다」는 `td.num.pos`(명시도 0,3,3) 규칙으로 **이미 수리됐고**, 남은 구멍은 `.pos` 단독(0,1,0)이 `td`(0,2,3)에 지는 것이다. 지금 마크업이 항상 `.num` 과 함께 붙여 써서 미발현 — **관례가 지키고 있을 뿐 규칙이 아니다**                                                                                                                                                                    | `<td>` 안에서 `.pos`/`.neg` 를 `.num` 없이 쓰게 될 때                                                             | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-626](#bl-626) | `.soak/phantom-*.json` 이 상한 없이 쌓이고 판정기가 매번 전부를 읽는다 — 수집 실행마다 1개씩 새로 쓰는데 회수가 없다(2026-08-07 실측 4시간 29개, 30분 타이머만으로 하루 48개). 실격은 `(at, kind, detail)` dedup 이라 판정은 안전하지만 ⑴ 파싱 시간·디스크가 선형 증가 ⑵ `unreadable_labels` 의 `count` 는 dedup 되지 않아 `측정불가` 요약의 `총 N건` 이 아카이브 수만큼 부풀려진다. ★파일명 STAMP 이 1초 해상도라 같은 초 두 실행은 충돌                                                    | `.soak/` 디스크 압박이 보일 때 · 게이트 1회 실행이 느려질 때                                                      | XS        | 2026-08-07 soak-unattended-watch                       |
| [BL-623](#bl-623) | 서버 클론이 `--single-branch` 라 feature 브랜치가 기본 fetch 로 안 온다 — `remote.origin.fetch` 가 main 한 줄뿐이라 `git checkout <branch>` 가 `pathspec did not match` 로 죽는다. 우회는 refspec 명시. 근본 수리(`git remote set-branches origin '*'`)는 소크가 도는 서버의 git 설정 변경이라 이연                                                                                                                                                                                          | 서버에서 feature 브랜치를 다시 받아야 할 때                                                                       | XS        | 2026-08-07 fe-oracle-deploy                            |
| [BL-638](#bl-638) | 🟡 `docs/archive/` 부재 — 2026-08-08 에 `lessons-archive-2026H1.md` 하나로 복원됐지만, `legacy_paths` 가 권장하는 하위 경로 4종은 여전히 없어 안내가 실행 불가다                                                                                                                                                                                                                                                                                                                             | 문서 보관 경로를 다시 안내하거나 정리할 때                                                                        | S         | 2026-08-08 bl003-unblock                               |
| [BL-640](#bl-640) | `.metrics` 가 컨테이너 세대를 넘어 누적된다 — `engine_only_suppressed` 합산 89 중 15가 이전 세대 값이라 창 안 차분에 창 밖 값이 섞인다                                                                                                                                                                                                                                                                                                                                                       | 게이트가 `.metrics` 값을 창 기준으로 해석할 때                                                                    | S         | 2026-08-08 bl003-unblock                               |

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
**Trigger:** 누적 위반 181 line 검출 (2026-05-15 audit) — auto-fix 가능
**Est:** S (3-5h)
**출처:** `2026-05-15-claudemd-align-audit.md` §6 Track C1, [LESSON-068](lessons.md)

**현 상태:** docs/dev-log 161 + dogfood 12 + guides 8 = 181 line 한국어 sentence + `:` end-of-line 위반. false positive 0. lint mechanism 0 = LLM 매 generation 자연 위반.

**권장 접근:**

1. markdownlint custom rule 또는 ruff custom plugin 으로 한국어 콜론 종결 검출 (regex `[가-힣]+\s*:\s*$` minus 코드 fence + URL + table cell + frontmatter)
2. auto-fix script — 검출 line `:` → `.` 일괄 sed (false positive 0 검증된 docs/\* scope 만)
3. pre-commit hook 추가 + CI gate
4. LESSON-068 2/3 누적 → 3차 시 문서 lint 영구 규칙 승격 (구 `global.md` §5 는 ADR-026 으로 소멸 — 승격처는 `scripts/docs-audit.sh` 확장)

**영향 파일:** 새 lint config 1 + auto-fix script 1 + pre-commit hook 1 + 검출 181 line edit (auto-fix 1회).

**Risk:** 🟢 (lint + docs only, code 영향 0).

---

### BL-307

**Title:** `~/.claude/CLAUDE.md` §6 한국어 file header lint + 누락 70 file backfill
**Category:** Lint / Source
**Priority:** P3
**Trigger:** 누적 누락 70 file 검출 (BE 14 + FE 56, 2026-05-15 audit). main.py / core/config.py / trading/registry.py / app/layout.tsx 등 핵심 file 포함
**Est:** M (8-12h — lint rule 4-6h + 70 file 의미 있는 한국어 1줄 주석 작성 4-6h)
**출처:** `2026-05-15-claudemd-align-audit.md` §6 Track C2, [LESSON-068](lessons.md)

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
**출처:** `2026-06-26-trading-deepen-2.md`

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

### BL-507

**Title:** 계정 표의 접기·청산 가능성 판정이 view 컴포넌트 안에 있다
**Category:** Frontend / trading (레이어)
**Priority:** P3
**Trigger:** 접기 규칙이 한 번 더 바뀔 때
**Est:** S
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
**출처:** 2026-07-25 money-path-accuracy 계획 단계 실발견 (`context-notes.md` §3.1)

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

**잔여 / 권장 접근:** ① 같은 폴백 구조가 `tests/conftest.py` 에도 있다(`TEST_DATABASE_URL > DATABASE_URL > default`) — 파괴성은 낮지만 동일 가드가 필요한지 검토 ② 로컬 개발 DB 주기 백업(`pg_dump` cron 또는 `make db-snapshot`)이 없다. dogfood 데이터는 재현 비용이 크고 API 키는 복구 불가다 ③ 서브에이전트에 DB env 를 넘길 때의 표준 레시피를 `backend/AGENTS.md` 로 승격 ④ **`alembic/env.py:40` 이 `settings.database_url` 을 주입하므로 수동 `alembic downgrade` 는 가드 없이 개발 DB 를 향한다** — `_assert_disposable_database` 는 pytest 경로만 막는다. CLI 경로 가드 또는 `make` 래퍼 검토.

---

### BL-452

**Title:** 거래소 청산 원장이 최근 7일만 담는다 — 과거 이력 적재·백필 불가
**Category:** Backend / trading (money path)
**Priority:** P3
**Trigger:** 아래 중 하나가 실제로 관측될 때 — ① 워커가 7일 넘게 정지한 실사례 ② 7일보다 오래된 미동기화 reduce-only 주문 관측 ③ 한 계정의 7일 청산이 500행 초과(`closed_pnl_window_truncated` 경고 발화) ④ `list_unsynced_reduce_only` 목록이 영구 좀비로 포화
**Est:** M (4-6h — 일회성 catch-up 재도입)
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

### BL-545

**Title:** ★gap-resync 안전 게이트가 5% 수량 허용치를 물려받아, 구 게이트가 막던 불일치를 통과시킨다
**Category:** Backend / trading (가용성 ↔ 안전 트레이드오프)
**Priority:** P2
**Trigger:** 조건부 진입 세션이 실자금으로 가기 전 / 부분체결이 흔해질 때
**Est:** S
**출처:** 2026-07-30 conditional-entry-alignment codex 적대 리뷰 (P1 제기 → 오케스트레이터가 코드 대조 후 P2 로 강등)
**상태:** ⬜ **Open**

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

**원인 / 영향:** `/trading` 에서 세션 상세를 열면 body 가 24px 가로 스크롤된다(375px 기준).
인과 분리 실측 — 상세 닫힘 **0px** / 상세 열림 **24px** / 상세 열림 + `outcome-parity-panel`
`display:none` **0px**. 대조군 `/dashboard` 는 **0px**.

★**이번 회차 회귀가 아니다.** `outcome-parity-panel.tsx` 는 BL-526(PR #496, 2026-07-29)의
컴포넌트이고 이번 diff 가 만지지 않았으며, 그 경로는 이번 변경 **이전에도 도달 가능**했다.

**권장 접근:** 패널 안 넓은 콘텐츠를 자기 `overflow-x:auto` 컨테이너로 감싼다 — 같은 화면의 세 표는
이미 `div.table-wrap{overflow-x:auto}` 로 그렇게 하고 있다. 그 패턴을 패널에도 적용.
**Risk:** 🟢

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

### BL-602

**Priority:** P3
**카테고리:** DX / 커밋 훅 (prettier 플러그인 해석)
**Trigger:** `frontend/` 안의 `*.json` / `*.md` / `*.yml` 을 커밋해야 할 때
**Est:** S
**상태:** ⬜ **Open** — ★2026-08-07 [ADR-027] 로 **표면이 넓어졌다**: 스택 규칙을 `frontend/AGENTS.md`·`frontend/CLAUDE.md` 로 옮기면서 이 함정에 걸리는 파일이 2개 늘었고, 당장은 `.prettierignore` **회피**로 막아 뒀다(근본 수리 아님). 회피 두 줄은 본 BL 해소 시 함께 지운다.

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

**잔존 기록 (2026-08-06 docs-overhaul):** 문서 대개편(fix-doc)에서 `frontend/README.md:39` 의
구 `.ai/rules/frontend.md` 참조를 **이 트랩 때문에 못 고치고 이연**했다(md 스테이징 = pre-commit 사망).
본 BL 해소 시 `frontend/README.md:39` → `frontend/AGENTS.md` 갱신을 함께 처리할 것.

**출처:** 2026-08-06 e2e-consolidation (커밋 시도 중 실측 재현)

---

### BL-598

**Priority:** P2
**카테고리:** Backend / 테스트 인프라 (코퍼스 첫-접촉 파싱 비용)
**Trigger:** CI backend 를 **14분 아래**로 내리려 할 때 · pine_v2 코퍼스 테스트를 늘리기 전에
**Est:** M
**상태:** ⬜ **Open**

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

**처리 방향:** ① 첫-접촉 비용의 **정체 규명**이 먼저다 — `lru_cache` 도 session fixture 도 못 찾았고
(`src/strategy/pine_v2/*.py` 에 캐시 데코레이터 0건), i3_drfx.pine 은 39KB 다. 파서/분류기의
비선형 구간인지, import 시점 워밍업인지 **프로파일로 확정**한다. ② 확정 후: 코퍼스 파싱 결과를
디스크 캐시로 고정하거나(테스트 픽스처), 파서의 해당 구간을 고친다. ③ ②가 되면 샤드 재분배로
추가 이득이 열린다.

★**「캐시가 있을 것이다」로 시작하지 마라** — 찾아봤고 없었다. 관측부터 해라.

**Risk:** 🟢 CI 시간·비용 문제이고 프로덕션 정확성과 무관. 단 **테스트 시간 추정을 반복해서
빗나가게 만드는** 원인이라 계측 신뢰도에 영향.

**연결:** [BL-583] (수집 집합이 결과를 바꾼 선례 — 같은 「무엇이 함께 도는가」 축)

**출처:** 2026-08-06 ci-diet (CI run 31071389290 잡별 실측 부검)

### BL-599

**Priority:** P3
**카테고리:** Backend / 죽은 코드 (Pine v1 shim)
**Trigger:** `BacktestOutcome` 를 손볼 일이 생겼을 때 (단독으로 열지 마라 — 이득 대비 파급이 크다)
**Est:** M
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

**호출자가 0인 채 남아 있는 것 3종** (2026-08-06 실측 — 정의 줄 외 참조 0):

| 대상                                                          | 비고                                                       |
| ------------------------------------------------------------- | ---------------------------------------------------------- |
| `OrderRepository.get_state_fresh` (`order_repository.py:280`) | 테스트도 없다                                              |
| `OrderRepository.list_unsynced_reduce_only_since` (`:733`)    | 테스트도 없다                                              |
| `scripts/fleet-dispatch-test.sh`                              | 자기 docstring 외 참조 0. `fleet-dispatch.sh` 는 살아 있다 |

★**원안의 「고아 하니스 3종」은 1종으로 정정한다** — `bl-audit-test.sh` ·
`pre-push-guard-test.sh` · `sentinel_bl181_worker_reload.sh` 는 **고아가 아니다**(각각 backlog ·
soak-gate 주석 · dev-log 가 참조하고, 앞의 둘은 `final-gates.sh` 체인 안에 있다).

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
**상태:** ⬜ **Open**

**`exchange_exits` 가 같은 청산 event 를 정확히 2행으로 적재한다.**

**실측 (2026-08-06, eval2):** 08-05 이후 172행 = **86 event × 정확히 2행**. 각 쌍은
`closed_pnl`·`closed_size`·`avg_entry/exit_price`·`exchange_created_at` 이 한 필드도 다르지
않고, 다른 것은 `id`·`matched_order_id`(ours 만 보유)·`classification`(`ours`/`unknown`)·
`attribution_confidence` 뿐. ⇒ `SUM(closed_pnl)` 형 소비는 손익을 **정확히 2배** 계상한다
(실측 −289.13 vs 진값 −144.57). `row_hash` 컬럼이 있는데도 중복이 들어온다 — 적재 경로가
분류 pass 별로 행을 새로 쓰는 것으로 보인다(뿌리 미확정).

**처방 후보:** 적재 시 `order_link_id` 단위 upsert 로 분류만 갱신, 또는 소비 계약에
「`classification='ours'` 필터/`DISTINCT order_link_id` 의무」를 정본화. 기존 소비처 전수
확인이 선행(이번 회차 도구는 dedup 를 자체 강제했다 — `btgap_compare.py`).

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
**상태:** ⬜ **Open**

**코드·테스트·설정 10곳이 삭제된 문서 경로를 가리킨다.** 문서 대개편(ADR-026, fix-doc)이
`docs/archive/`·dev-log 원문을 지웠다. 소크 활성 중 `backend/src` 무접촉 원칙 때문에 이번 회차에서
고치지 않고 이연한다. **2026-08-07 PR #554 리뷰에서 전수 재검출** — 최초 등재 시엔 1곳만 잡았다.

★**그중 2곳은 사용자에게 그대로 보인다** (주석이 아니다):

- `backend/src/backtest/service.py:191` — `StrategyDegraded.detail` 에 `"See docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md."` 가 들어가 **API 응답으로 나간다**
- `backend/src/strategy/pine_v2/coverage.py:697` — heikinashi 경고 문자열의 `"참고: …"` 가 **UI 로 표면화된다**

나머지 8곳 (동작 무해):

- `backend/src/trading/entry_completeness.py:158` — `source=` 메타데이터 (최초 등재분)
- `backend/prometheus/alerts.yml:14` · `backend/tests/strategy/pine_v2/{test_coverage_sprint21.py:197,test_dogfood_pine_corpus_e2e.py:56,test_trust_layer_parity.py:10}`
- `frontend/src/__tests__/design-canon-tokens.test.ts:62` · `frontend/src/app/(dashboard)/backtests/_components/charts/equity-chart-v2.tsx:9` · `frontend/src/components/charts/trading-chart.tsx:4`

수리 = tombstone 형식(`git:0f0f0b06 <경로>`) 또는 현존 정본 경로로 교체.
재검출 명령 (게이트가 아니라 손으로 돌린다):

```bash
git grep -oE 'docs/(archive|dev-log)/[A-Za-z0-9_./-]+\.(md|html)' -- backend frontend \
  | while IFS=: read -r f l p; do [ -e "$p" ] || echo "DANGLING $f -> $p"; done
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
**상태:** ⬜ **Open**

**entry-set-divergence 회차의 dev-log 버퍼가 승격되지 않은 채 남아 있다.**
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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

**2026-08-04 handler-visibility 회차의 방법론 3건이 `docs/lessons.md` 에 없다.**
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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open** — 관측된 결함(워크트리 1개의 훅 결손)은 2026-08-07 에 정상화했다. **감지 수단 부재**만 열려 있다.

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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

### BL-627

**Priority:** P3
**카테고리:** Test infra / 골든 재생성
**Trigger:** `regen_golden.py` 를 CI 나 병렬 실행에 넣을 때
**Est:** XS
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

**마케팅 푸터 법적 고지 한 곳이 공개 라우트 라이트 캐논 미충족의 단일 원인이다.**

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
**상태:** ⬜ **Open**

**`--chart-axis` 는 정의만 있고 아무도 안 읽는 데드 토큰이다.**

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
**상태:** ⬜ **Open**

**`.pos`/`.neg` **단독**은 여전히 `td` 색에 진다.**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

**`DESIGN.md` 의 반응형 규정이 자기 자신과 어긋나고, 2세대 프로토타입 실측과도 어긋난다.**

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

★`HANDOFF-react-port.md:58,166` 이 「1024px 아이콘 레일」을 🔴 **미구현**으로 등재해 뒀다
(`sidebarOpen` 이 뷰포트를 안 보고 Zustand 수동 토글). ⇒ **어느 값이 정본인지부터 정해야** 그 구현을
시작할 수 있다.

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

**미조인 `exchange_exits` 는 상시 기저율이어서 배타성 판정의 근거가 될 수 없다.**

BL-634 의 가드를 「원장에 없는 체결 이력이 있으면 남의 호스트다」로 만들면 상시 거부가 된다.
실측: `matched_order_id IS NULL` 은 서버 `exchange_exits` **34행 / 유니크 27 = 전량**을 고른다 — BL-605 의 2배 중복 때문에 모든 청산이 최소 1벌은 미조인이라 **이 필터의 판별력은 0** 이다. ★부검 초판이 인용한 「6건」은 판정식에 적지 않은 시간 필터의 산물이었고 회차 도중 반증됐다.
BL-605 의 중복 채널이 살아 있는 한 미조인 행은 항상 존재한다. 과거 회차의 계정별 `ours/unknown`
분리도 부수효과 dedup 의 산물이지 소유권 판정이 아니었다.

따라서 배타성 판정 대상은 체결 이력이 아니라 미체결 resting 조건부 주문이어야 한다. 이는 지금 이
계정을 누가 잡고 있는지를 재고하므로 과거 이력의 기저율에 오염되지 않는다.

**Risk:** 🔴 체결 이력을 가드로 쓰면 정상 운영도 상시 거부할 수 있다.

---

### BL-640

**Priority:** P3
**카테고리:** 운영 / 지표 세대 경계
**Trigger:** 게이트가 `.metrics` 값을 창 기준으로 해석할 때
**Est:** S
**상태:** ⬜ **Open**

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
**Trigger:** 다음 회차 종결 시 · `docs/status.md` 진입점이 또 낡은 채 PR 이 올라갈 때
**Est:** S
**상태:** ⬜ **Open**

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
**Trigger:** 다음 소크 재기동 · `soak-restart.sh --confirm` 의 ⑺ 이 또 실패할 때
**Est:** XS
**상태:** ⬜ **Open**

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
**상태:** ⬜ **Open**

**BL-003 의 실질 선행조건은 문턱이 아니라 MTBF 다.**

ADR-024 리셋 표에 의해 실격은 C1 을 0 으로 되돌린다. 그러므로 「누적 clean 168h」는 사실상
「168시간 연속 무실격」이고, 그 확률이 P(168h 생존)이다.

2026-08-08 재측정 2벌 — 원자료 `.claude/fleet/bl003/artifacts/mtbf-analysis.txt`:

| 표본            |   n | 누적        | 최장       | 자동 사망 | MTBF       | P(24h)     | P(168h)       |
| --------------- | --: | ----------- | ---------- | --------: | ---------- | ---------- | ------------- |
| 전 이력         |  38 | **107.12h** | **19.42h** |         8 | **13.39h** | **16.66%** | **3.558e-06** |
| 2026-08-03 이후 |  14 | **60.91h**  | **19.42h** |         7 | **8.70h**  | **6.34%**  | **4.115e-09** |

24h 도달은 전 이력 통틀어 0건이다. 08-03 이후 사인은 `position_divergence` **6** ·
`user_stopped` **7** · `gap_resync_position_mismatch` **1** 이다.

현 사망률에서 168h 연속 무실격은 어렵다가 아니라 사실상 도달 불가다 — **4.115e-09**. 문턱을 낮추는
것이 아니라 사망률을 낮추는 것이 유일한 경로다. 첫 표적은 BL-634 계정 배타성이고, 그 다음은
`position_divergence` 계열 전체다. 이 BL 은 BL-003 의 하위 작업이 아니라 게이트 해석이므로,
BL-003 의 Est 를 다시 잡기 전에 읽어야 한다.

**Risk:** 🔴 MTBF 를 개선하지 않으면 168h 연속 무실격 조건은 사실상 도달 불가다.

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

| 창                  | n   | 노출    | 자동사망 | MTBF      | P(168h)  | 그 사망의 정체                           |
| ------------------- | --- | ------- | -------- | --------- | -------- | ---------------------------------------- |
| 전 이력             | 38  | 107.12h | 8        | 13.39h    | 3.56e-06 | 혼합                                     |
| 2026-08-03 이후     | 14  | 60.91h  | 7        | **8.70h** | 4.12e-09 | **혼합 — 이 BL 이 인용한 값**            |
| [ADR-025] 수리 이후 | 5   | 38.47h  | 2        | 19.24h    | 1.61e-04 | gap-resync 1 — [BL-622] 가 수리 · 오염 1 |
| [BL-622] 수리 이후  | 2   | 5.59h   | 1        | —         | —        | **오염 1건뿐** — [BL-634] 미시행         |

★**각 수리 이후의 사망은 전부 「그 다음 원인」이었다.** 알려진 원인이 모두 닫힌 뒤의 **미설명 사망은
0건**이지만 노출이 5.59h 뿐이라 **아래에서 못 잰다** — rule of three 로 상계만 말할 수 있다
(λ ≤ 3/5.59h ⇒ P(168h) ≥ exp(−168×0.537) 는 사실상 0이지만, 그건 **표본이 없다는 뜻이지 나쁘다는 뜻이 아니다**).

★★**그러므로 이 BL 의 결론을 「MTBF 가 병목이다」로 단정하지 마라.** 정확한 문장은
**「현행 사망률을 아래에서 잴 표본이 아직 없다 — 층화 전 값(8.70h)은 고친 원인을 섞은 상한이다」**이다.
판정에 필요한 것은 **[BL-634] 착지 이후의 노출**이고, 그때까지 이 BL 은 **측정 대기**다.

★부수 — **오염은 자동사망 8건 중 1건뿐**이었다(나머지 7건은 맥→오라클 이관 전이라 호스트가 하나였다).
「배타성을 고치면 MTBF 가 오른다」는 성립하지 않는다. [BL-634] 가 사는 것은 **재발 방지**다.
