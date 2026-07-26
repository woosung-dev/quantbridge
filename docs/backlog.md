# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 [`refactoring-backlog/_archived.md`](archive/refactoring-backlog/_archived.md), trigger 미도래 의도적 부활 가능 항목은 [`refactoring-backlog/_deferred.md`](archive/refactoring-backlog/_deferred.md). 정합성 검증은 [`04_architecture/architecture-conformance.md`](reference/architecture-conformance.md).
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정. `_deferred.md` 도 6-8주마다 재평가.

**작성일:** 2026-04-30
**최종 갱신:** 2026-07-26 (**dogfood-restore 스프린트** — 로컬 실사용 복원 + 3스프린트 누적 신뢰 작업 실화면 검증. **BL-465/467 Resolved** + 신규 **BL-466/468~472/474** + **BL-473 Resolved**(WS auth `expires` 창 — 라이브 체결 스트리밍이 통째로 죽어 있었다). ★**dogfood 가 P1 을 잡았다** — `_periodic_returns` 가 음수 자본을 안 걸러 파산한 실행에 **양수 샤프**가 붙었고(실측 -2179.68% 에 +0.029), **committed Trust Layer baseline 이 그걸 담고 있었다**(s1_pbr 샤프 +0.600 · 소르티노 +2.349 on -536%). 코퍼스 5종 중 4종이 음수 자본이고 골든이 깨진 것도 정확히 그 4종. baseline 재생성 diff = 12 메트릭 키 중 2개 한정. ★**옵티마이저는 이 스택에서 구조적으로 죽어 있었다** — `optimizer_heavy` 유일 소비자에 OHLCV env 3종 부재. ★**`make seed` 신설** — 백테스트 1회가 곧 OHLCV 시딩(TimescaleProvider cache-first). 마이그레이션 0.) // 이전: 2026-07-26 (**money-path-finish 스프린트** — BL-457/454 Resolved + BL-458 부분 Resolved + **신규 BL-464**. 머니-패스 정확도 마감 팩. ★**실측이 BL-457 의 '권장 접근' 을 반박** — `attribution_facts` 재사용은 진짜 우리 청산을 external 로 뒤집는다(백로그 본문에서 제자리 정정). ★**백로그에 없던 결함 발견(BL-464)** — `attribute_exit` 이 거래소 원문↔canonical 심볼을 비교해 `inferred` 귀속이 구조적으로 죽어 있었고, **픽스처 기본값이 그걸 한 스프린트 동안 가렸다**. ★`format:check` 는 이 레포의 통과 가능 게이트가 아님을 실측 확인(선재 356 red). 마이그레이션 0.) // 이전: 2026-07-25 (**exit-money-path 스프린트** — BL-444/445 Resolved + BL-453 부분 Resolved + 신규 BL-454~458. 세션 스코프 머니-패스 정정(Site 3·4). ★§0.5 실측이 BL-438 ② 를 "미룸" 이 아니라 **"현재 데이터로는 정직하게 구현 불가"** 로 재분류 — bracket/trailing 0행 · matched/attributed 0행. ★대조군 판별력을 프로덕션 stash 로 실제 증명. ★active BL 카운트 산식을 헤더에 박아 stale 재발 차단.) // 이전: 2026-07-25 (**exit-attribution 스프린트 + 범위 축소 + dogfood 완주** — BL-438 부분 Resolved(관측 원장, **최근 7일**) + BL-442 Resolved + 신규 BL-443~453. 거래소 청산 원장 신설 + 스윕 계정 독립 열거. ★과거 90일 catch-up 기계장치는 머지 전 축소로 걷어냄 → BL-452. ★로컬 개발 DB 전소 사고 → BL-451 가드. ★dogfood 실측이 알림 크래시 진짜 P1 을 적발·수정 → BL-453 예방 등재.) // 이전: 2026-07-25 (**close-completeness 스프린트** — BL-435/436 Resolved + BL-434 부분 Resolved(display) + 신규 BL-437(스윕 이연). 청산 즉시 flat + margin 503 회피 + 완전 TP/SL 보고.) // 이전: trading-surface-pack — BL-431/416/425/432/433 Resolved + BL-434~436.
**직전 갱신:** 2026-07-24 (**trading-surface-pack 스프린트** — BL-431/416/425/432/433 Resolved + 신규 BL-434~436. 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 완성.)
**현재 상태:** **86 active BL / 전체 135 항목** (2026-07-26 live-engine-parity 기준, 아래 산식으로 기계 측정). **BL-070~075 milestone active 승격** (deferred → P0 prep).

> ★이 수치는 손으로 세지 말고 기계적으로 재라 — 직전까지 "49 active" 로 여러 스프린트 동안 stale 하게 남아 있었다. 산식 = `### BL-` 헤딩 수(전체) 대비 각 섹션 본문에 `Resolved` 가 등장하지 않는 항목 수(active). 부분 Resolved 는 active 로 세지 않는다(본문에 `Resolved` 문자열이 있으므로).
>
> ```bash
> awk '/^### BL-/ { if (id) print id, res?"RESOLVED":"ACTIVE"; id=$2; res=0; next }
>      /^## / && id { print id, res?"RESOLVED":"ACTIVE"; id=""; next }
>      { if (id && /Resolved/) res=1 }
>      END { if (id) print id, res?"RESOLVED":"ACTIVE" }' docs/backlog.md | sort | uniq -c -f1
> ```

**최근 sprint BL 변경 (Sprint 55~Sprint 62 Beta 진입):**

- **2026-07-25 close-completeness 스프린트 (codex G0 REJECT→개정 + 2-generator ∥ + Claude 적대평가 per-worker + codex 최종 diff + Opus dogfood 3계통)**: trading-surface-pack(#473) 후속. 청산/TP-SL 완성도 3건. **BL-435 Resolved**(즉시 flat = post-fill Celery 캐시 DEL, accept-time DEL 은 async close 라 무효) + **BL-436 Resolved**(청산 create_order 가 reduce_only 시 set_margin_mode/set_leverage skip = margin 503 회피, ccxt marginMode 신뢰불가 우회) + **BL-434 부분 Resolved**(완전 TP/SL 보고 display = fetch_open_conditional_orders 2콜 union+orderId dedupe+stopOrderType 엄격분류 → §03 병합 리스트 + has_trailing_stop 각주; **스윕은 BL-437 이연**) + hedge positionIdx 409 가드. 마이그레이션 0. 게이트: BE **2611**(+10) / FE **1084**(+1) / canon **32 불변** / ruff·mypy·tsc·lint 0 / alembic 무변경. **검증 체인**: codex G0 = **REJECT**(전건 코드 대조 §7.3 후 개정 — B2 skip 전환·B1 post-fill DEL·B3 union dedupe·trail=position 필드·hedge 가드) → 사용자 재인터뷰(스윕 이연·트레일링 각주) → codex 2워커 생성 ↔ Claude 적대평가(W1 ruff B023×3+mypy → codex resume hoist) → codex 최종 diff([P1] has_trailing_stop 조건부 trail 해소+테스트) → **dogfood 3계통**(독립 오라클 raw ↔ 앱 provider fetch_open_conditional_orders(66000/62000 정확 분류·count=2 dedupe) ↔ get_reconciliation 병합 + **authed 브라우저**(§03 병합·청산 flat·콘솔 0) + B1 redis 키 부재 + B2 no-503 + Bybit Partial 자동취소 실증). **★docker 포트 오버레이 함정**(plain `docker compose up <svc>` 이 db/redis 를 base 5432/6379 로 되돌림 → `--no-deps` 필수). 신규 **BL-437**.
- **2026-07-24 trading-surface-pack 스프린트 (codex 2-generator ∥ + Claude 적대평가 per-worker + Opus dogfood)**: position-cockpit(#472) 후속. 코크핏 §03 포지션 표에 TP/SL 열 + reduce-only 시장가 청산 완성 + 부채 4종. **BL-431 Resolved**(BE: 포지션-보고 TP/SL read-time 0→null 정규화 + `POST /live-sessions/{id}/positions/close` reduce-only 청산 = 신규 `close_service.py` + `OrderService.execute(flatten=True)` 진입-위험 가드 ②~⑧ bypass·ownership 유지·reduce_only 불변식·**청산 leverage=포지션값**으로 set_leverage no-op·cap-bypass 방지 / FE: 익절·손절 2열 + 청산 액션·확인 모달(정직 고지)·colSpan 14) + **BL-416 Resolved**(주문취소 행별 disabled `cancelOrder.variables` + 비-409 broad toast + 실 ACTIVE_ORDER_STATES import) + **BL-425 Resolved**(alert-rule 중복 유형 사전검사 = 마운트 목록 재사용, 409 요청·콘솔 노이즈 회피) + **BL-432 Resolved**(positions select→combine 인덱스 zip + 고아 삭제) + **BL-433 Resolved**(`qb_ws_subscribe_rejected_total{account_id}` counter). 마이그레이션 0. 게이트: BE **2601**(+18) / FE **1083**(+8) / canon **32** / authed **66**(+2 코크핏 §03 구조) / build ✓ / alembic 무변경. **검증 체인**: codex G0 14건(코드 대조 후 반영, BLOCKING 3=leverage 라우팅·flatten 불변식·hedge 거부) → codex 2워커 병렬(backend/frontend 교집합 0) ↔ Claude 적대평가 per-worker(게이트 직접 실행, W1 RUF059 1건 codex resume) → 최종 codex 누적 diff(MAJOR 1=청산 leverage cap-bypass → 포지션값 사용 fix) → **Opus dogfood 2계통**(독립 Bybit HMAC 오라클 ↔ 코크핏 §03: TP/SL 값 66000/62000 정확 일치·빈값→— 정직 / 청산 종단 flat+Order row / **kill-switch 활성 청산 성공 = 가드 bypass 실증, KS 미소비** / 콘솔 error 0). 신규 **BL-434~436**.
- **2026-07-23 functional-parity 스프린트 (codex 4-generator ∥ + Claude 적대평가 + Opus dogfood)**: C 디자인 이식 후 기능 격차 마감. **BL-401 Resolved**(3폼 `formState.errors` → `.field-error` 프리미티브, superRefine 평탄 경로 row 매핑, 메시지 한국어화 — grid min>max 만 거부로 BE 계약 정합) + **BL-411 Resolved**(지원 kind 목록 `OptimizationKind` enum 파생 + Sprint 넘버 문구 중립화) + **BL-402 Resolved (구조 소멸)** — C 이식이 4사이트 전부 네이티브 `<select>` 로 재작성해 uncontrolled/raw-UUID 결함 자체가 소멸(실측 재확인, 코드 변경 0). 신규 A2(주문취소 액션 열 — "API 없음" 미렌더 전제가 거짓이었음, CF4 완비)·B2(orders state 반복 Query + 미체결 nav-count 캐논 §4.6 복원)·B1(strategy.backtest_count read-time GROUP BY, COMPLETED 기준)·A7-lite(스트레스 최신 결과 리로드 복원)·A1(대시보드 전략 링크 404→edit). 게이트: vitest 965→980 / BE 2416+18 / canon 32 불변 / authed 56→62. 신규 **BL-413~416**. **Opus MCP dogfood(10항목)가 잠복 P1 2건 추가 발굴·동일 스프린트 해소**: (a) stress_test enum 혼합 케이싱 — 최초 migration 소문자 라벨 vs SAEnum 대문자 저장으로 실 DB 에서 MC/WF 생성 전부 500 → RENAME VALUE migration `20260723_0001` + alembic-경로 enum 라벨 sentinel 테스트(즉시 status enum 드리프트도 추가 검출). (b) provider cancel_order 전 구현이 ccxt 에 symbol 미전달 — 실거래소 취소가 전부 ArgumentsRequired(CF4 fail-closed 로 submitted 영구 잔존, BL-404 동형) → Protocol+5 provider symbol 관통 + futures linear 정규화. dogfood 최종 V1~V10 전 항목 PASS (취소 200/202 실클릭 + DB 오라클 3점 + A7-lite 리로드 복원 실측).

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
  - P1: BL-014/015/022/023/024/025/026/308
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

| ID                | 제목                                        | Trigger              | Est      | 출처             |
| ----------------- | ------------------------------------------- | -------------------- | -------- | ---------------- |
| [BL-003](#bl-003) | Bybit mainnet 진입 runbook + smoke 스크립트 | H1 Stealth 종료 직전 | M (4-5h) | TODO.md L646~651 |

> 추가 P0 — [BL-005 본인 dogfood](archive/refactoring-backlog/_deferred.md) + [BL-145 EffectiveLeverageEvaluator](archive/refactoring-backlog/_deferred.md) (deferred). Resolved P0 = BL-001/002/004 ([\_archived.md](archive/refactoring-backlog/_archived.md)).

### BL-003

**Title:** Bybit mainnet 진입 runbook + smoke 스크립트
**Category:** Tooling / Infra
**Priority:** P0 (H1 Stealth 종료 직전)
**Trigger:** Bybit Demo 1주 안정 운영 후 + BL-004 완료 후 (BL-004 ✅ Resolved Sprint 28)
**Est:** M (4-5h)
**출처:** [`docs/status.md`](../.ai/templates/docs/status.md) L646~651

**원인 / 영향:** dogfood 가 Bybit Demo 만으로는 H1 종료 gate 충족 안 됨. mainnet 전환 시 수동 step 누락 위험 (IP whitelist / 출금 권한 차단 / 레버리지 1:1 / 소액 시작).

**권장 접근:**

1. `docs/reference/infra/bybit-mainnet-checklist.md` 신규 — IP whitelist · 출금 권한 OFF 확인 · 레버리지 1:1 · 소액 ($10-50) 시작 · Kill Switch 임계값 lower bound
2. `scripts/bybit-smoke.sh` 신규 — mainnet credentials 로 read-only API 호출 (잔고 조회 + 1 USDT limit-order 후 즉시 cancel) dry-run
3. `.env.production` 별도 secret manager + rotation 절차

**의존성:** BL-004 ✅ Resolved (Sprint 28 PR #108).

---

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

| ID                | 제목                                                                                               | Trigger                                         | Est        | 출처                            |
| ----------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------- | ------------------------------- |
| [BL-014](#bl-014) | Partial fill `cumExecQty` tracking                                                                 | partial fill 1건 발견 시                        | M (4-5h)   | TODO.md L709                    |
| [BL-015](#bl-015) | OKX Private WS                                                                                     | Bybit Demo 안정화 후                            | M (6-8h)   | TODO.md L710                    |
| [BL-022](#bl-022) | golden expectations 재생성                                                                         | pine_v2 `strategy.exit` 도입 후                 | M (3-4h)   | TODO.md L17 (skip #1)           |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                       | Trust Layer v2 검토 시                          | M (5-6h)   | TODO.md L23 (skip #16)          |
| [BL-024](#bl-024) | real_broker E2E 본 구현 (nightly cron)                                                             | Bybit Demo credentials + seed data 준비 시      | L (8h+)    | CLAUDE.md Sprint 10 Phase C     |
| [BL-025](#bl-025) | autonomous-parallel-sprints 스킬 patch                                                             | on-demand (BUG-1/2/3 재발 시)                   | S (2h)     | TODO.md L653                    |
| [BL-026](#bl-026) | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                                    | Stage 2c 2차 fixture 활성화 후                  | S (1-2h)   | TODO.md L20-22                  |
| [BL-308](#bl-308) | trading websocket test coverage 4% → ≥70%                                                          | dogfood 직후 (Day 7 후)                         | L (12-16h) | 2026-05-15 trading-deepen audit |
| [BL-404](#bl-404) | ✅ Resolved — watchdog `fetch_order` Bybit 전면 실패 (acknowledged 게이트 + futures 심볼 미정규화) | ✅ `fix/trading-bl404-fetch-order-acknowledged` | S (1-2h)   | 2026-07-05 데모 라이브 dogfood  |
| [BL-488](#bl-488) | 평가 갭 orphan close → 보유분 없는 `reduce_only` 주문과 시뮬 손익 오염                             | 즉시. 평가 갭이 재현되거나 beat 안정화 전       | M          | 2026-07-26 live-engine-parity   |

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

**권장 접근:** `nightly-real-broker.yml` (cron 0 18 \* \* \*) 의 실제 검증 로직 구현. 현재는 skeleton + marker + flag 만.

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
**Trigger:** 전체 정검 2026-05-30 (P1-10/13) — ✅ **Resolved S2** (`stage/fix-trust-layer-leak`)
**Est:** S (2-3h) — 실측 ~1.5h
**출처:** [`docs/archive/audit/2026-05-30-full-inspection.md`](archive/audit/2026-05-30-full-inspection.md) §4.3

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

## P2 — Hardening / 건강도 작업

| ID                | 제목                                                                                                                                                           | Trigger                                                                        | Est          | 출처                                                   |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------ | ------------------------------------------------------ |
| [BL-186](#bl-186) | Full leverage + funding + mm + liquidation 풀 모델                                                                                                             | Sprint 38+ (BL-185 foundation 위)                                              | M-L (16-24h) | Sprint 37 BL-185 후속                                  |
| [BL-190](#bl-190) | PDF export (jsPDF / Playwright)                                                                                                                                | 외부 사용자 요청 시                                                            | M (3-5h)     | Sprint 41 Worker H 결정                                |
| [BL-195](#bl-195) | qb-form-slide-down animation 영구 truncation                                                                                                                   | Sprint 45 codex G.4                                                            | XS (30m)     | Sprint 45 codex G.4 발견                               |
| [BL-235](#bl-235) | N-dim acquisition surface viz (Bayesian 전용)                                                                                                                  | Sprint 57+                                                                     | M (8-12h)    | ADR-013 §6 #8 deferred                                 |
| [BL-236](#bl-236) | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                                                                                                      | Sprint 56+                                                                     | S (3-5h)     | Sprint 55 deferred                                     |
| [BL-309](#bl-309) | trading registry/webhook/fees test 0% → ≥80%                                                                                                                   | BL-308 묶음 또는 dogfood 직후                                                  | M (4-6h)     | 2026-05-15 trading-deepen audit                        |
| [BL-362](#bl-362) | live 경로 coverage↔interpreter divergence silent swallow observability                                                                                         | S5 (trading kill-switch 묶음)                                                  | S (2-4h)     | 2026-05-30 full-inspection §4.3                        |
| [BL-363](#bl-363) | stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)                                                                                   | deepening sprint 또는 5번째 engine 추가 시                                     | S (2-3h)     | 2026-05-30 full-inspection §appendix P1-9              |
| [BL-364](#bl-364) | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩)                                                                           | string 카테고리 sweep 요청 시                                                  | M (4-6h)     | 2026-05-30 full-inspection §appendix P1-9 (S4 후속)    |
| [BL-365](#bl-365) | `trigger_direction_for`/`map_exit_kind` dead + 서버 미배선 (standalone-trigger 방향)                                                                           | 서버 standalone 트리거 발주 시                                                 | S (2-4h)     | 2026-06-26 trading-deepen-2                            |
| [BL-366](#bl-366) | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                                                                                          | trading deepening sprint                                                       | S-M (3-5h)   | 2026-06-26 trading-deepen-2                            |
| [BL-368](#bl-368) | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                                                                                            | trading deepening / 4번째 provider                                             | S-M (3-5h)   | 2026-06-26 trading-deepen-2                            |
| [BL-369](#bl-369) | 3 provider `create_order` try/except/finally ~40 LOC 복붙                                                                                                      | trading deepening sprint                                                       | S (2-4h)     | 2026-06-26 trading-deepen-2                            |
| [BL-372](#bl-372) | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)                                                                                    | Wave 3 실자금 cutover 전                                                       | M (6-10h)    | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)     |
| [BL-373](#bl-373) | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                                                                                                | BL-365 standalone-trigger 발주 시                                              | S-M (3-5h)   | 2026-06-28 grilling (트레일링 후속 scope)              |
| [BL-374](#bl-374) | ✅ Resolved (2026-06-29) — pine_v2 interpreter na-semantics — `x/0`·`math.sqrt(-1)` 등 raw 예외 → Pine `na`                                                    | ✅ `fix/pine-374-na-semantics`                                                 | M (4-6h)     | 2026-06-28 BL-362 G2 codex challenge                   |
| [BL-375](#bl-375) | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱)                                                            | Wave 3 실자금 cutover 전                                                       | S-M (3-5h)   | 2026-06-29 BL-372 same-side stale G1 codex             |
| [BL-376](#bl-376) | ✅ Resolved (2026-06-30) — pine_v2 na/inf 소비 사이트 robustness — na/inf→ta.\* length / na/inf→entry qty skip / inf→math.floor·ceil·round·subscript·timestamp | ✅ `fix/pine-376-na-inf`                                                       | M (4-6h)     | 2026-06-29 BL-374 G1/G2/G3 + generator panel 합의      |
| [BL-377](#bl-377) | pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)                                                                        | pine_v2 robustness 후속 또는 실자금 cutover 전                                 | S (2-4h)     | 2026-06-30 BL-376 G2 codex challenge + G3 fresh review |
| [BL-378](#bl-378) | ✅ Resolved (2026-06-30) — pine_v2 `ta.atr` rolling SMA → Wilder RMA (TV parity, headline harm-class)                                                          | ✅ `fix/pine-378-atr-wilder`                                                   | S (2-4h)     | 2026-06-30 티어드 백테스트 QA 大-tier oracle           |
| [BL-379](#bl-379) | pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐, latent harm-class)                                                                 | pine_v2 robustness 후속                                                        | M (4-6h)     | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-380](#bl-380) | Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반) + VirtualRunResult.warnings 미전파                                                         | Track A 신뢰 표면 sprint                                                       | S-M (3-5h)   | 2026-06-30 QA LuxAlgo 0-trade                          |
| [BL-381](#bl-381) | Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허 (i2_luxalgo 검증 vacuous)                                                     | Trust Layer CI 강화                                                            | S (2-4h)     | 2026-06-30 QA codex G2/diff                            |
| [BL-382](#bl-382) | qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성, mdd_exceeds_capital 은 표시됨)                                                           | sizing 투명성 sprint                                                           | S (2-4h)     | 2026-06-30 QA F1 (codex G2)                            |
| [BL-383](#bl-383) | v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)                                                                                          | pine_v2 관측성 후속                                                            | S (2-3h)     | 2026-06-30 QA codex G2                                 |
| [BL-384](#bl-384) | ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)                                                                                                      | pine_v2 parity 후속                                                            | S (2-3h)     | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-385](#bl-385) | PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse (메타데이터 부정확)                                                                                | pine_v2 coverage 후속                                                          | XS (1-2h)    | 2026-06-30 QA F3                                       |
| [BL-386](#bl-386) | v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject, over-strict)                                                                      | pine_v2 coverage 후속                                                          | XS (1-2h)    | 2026-06-30 QA F4                                       |
| [BL-387](#bl-387) | backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 횡단 (key drift 시 silent 잘못된 sizing, money-path)                                | backtest deepening 또는 sizing 로직 변경 시                                    | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 최강 후보)           |
| [BL-388](#bl-388) | BacktestMetrics 24-field 가 4곳 평행 정의 (dataclass↔schema↔serializer↔_to_detail), field-parity 무검증 (leaky seam)                                           | backtest deepening 또는 BL-236 진행 시                                         | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 가 4번째 site 발견)  |
| [BL-392](#bl-392) | stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass↔serializer↔OutSchema, untyped JSONB seam)                                        | stress_test deepening 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시 | M (4-6h)     | 2026-06-30 stress_test-deepen (deepen-modules 1차)     |
| [BL-401](#bl-401) | ✅ Resolved (2026-07-23) — optimizer 3폼 field-level zod 에러 렌더 (`.field-error` + role=alert, 메시지 한국어화)                                              | ✅ `stage/functional-parity`                                                   | S-M (2-4h)   | 2026-07-05 PR #394 FE 리팩토링 번들 dogfood            |
| [BL-402](#bl-402) | ✅ Resolved (2026-07-23, 구조 소멸) — C 이식 네이티브 select 전환으로 4사이트 결함 자체 소멸 (실측 재확인, 코드 변경 0)                                        | ✅ `stage/functional-parity` (문서만)                                          | XS-S (1-2h)  | 2026-07-05 PR #394 FE 리팩토링 번들 dogfood            |

> Resolved P2 = BL-027/137/140/140b/141/144/150/152/176/178/180/181/183/184/185/187/187a/188/188a/189/200~206/219~234/237 + 30+ Sprint 16~30 stale ([\_archived.md](archive/refactoring-backlog/_archived.md)).

### BL-186

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

**원인 / 영향:** `v2_adapter.py`(964L)의 본 책임은 V2RunResult → BacktestOutcome 변환(orchestration)인데, Sharpe/MaxDD/CAGR/win-rate/streak/monthly 등 도메인-비종속 finance math 10 함수(`_v2_avg_holding_hours`~`_mean`, L707-912 ~250 LOC)가 같은 모듈에 혼재 = shallow-by-size, Locality 깨짐. (codex 가 `engine/metrics.py` 존재로 오판 DOWNGRADE → 실제 부재 확인, 모든 math 가 v2_adapter 내부 → KEEP 정정.) stress_test 재사용은 speculative(현재 `result.metrics` 만 소비)라 추출 정당화는 locality 중심.

**권장 접근:** finance 계산을 `engine/metrics.py` Deep Module 로 이동 — '(equity_curve, trades, config) → 지표 묶음' 작은 Interface 뒤에 큰 behavior 은닉. v2_adapter 는 호출만 남김. 이동(move)이라 golden oracle parity 로 회귀 0 보장.

**영향 파일:** `engine/v2_adapter.py`(L707-912 추출), 신규 `engine/metrics.py`.

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
**Trigger:** BL-389 metrics 추출과 묶음 또는 backtest test 강화 시
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex DOWNGRADE → 좁은 oracle 범위로 축소)

**원인 / 영향:** `_build_raw_trades`(:145) → `_compute_equity_curve`(:154) → `_compute_metrics` 가 상호 의존(equity ← trade pnl, metrics ← 양쪽)하나 각각 isolation 으로만 테스트되고 단계 간 계약(`sum(trade.pnl)` ↔ equity 종가 delta)이 문서화/검증 안 됨 = 'testability 위해 추출된 순수함수' 안티패턴 → off-by-one 등 cross-stage 버그가 단위 테스트를 통과할 수 있다. (codex: golden/cost invariant 일부 존재 → 좁은 closed-trade·no-funding equity↔PnL oracle 만 추가, broad pipeline 재구성 아님.)

**권장 접근:** reconciliation 불변식 명시(docstring) + closed-trade·no-funding 케이스의 equity↔PnL cross-stage oracle 테스트 1건 선작성. BL-389 와 묶으면 자연스러움.

**영향 파일:** `tests/backtest/`(cross-stage oracle 신규), `engine/v2_adapter.py`(불변식 docstring).

**Risk:** 🟢 (test-first — 코드 변경은 docstring 수준).

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
**Trigger:** 2개월 미만 백테스트의 Sharpe/Sortino 문의 시
**Est:** S-M (baseline 2 metric 확산 주의)
**출처:** 2026-07-26 backtest-trust 스프린트 (BL-398 구현 중 발견)

**원인 / 영향:** `engine/metrics.py:41-43` 의 else 분기가 **resample 없이 전 bar** 를 기간 표본으로 쓰고 RFR 은 `0.02/365` 를 적용한다. 1h/5m 백테스트가 2 달력월 미만이면 1시간을 하루로 세어 위험조정 지표가 왜곡된다. **sortino 가 이미 갖고 있던 선재 결함**이고, BL-398 이 `_periodic_returns` 를 재사용하면서 sharpe 로도 전파됐다.

**권장 접근:** daily fallback 에서 `equity.resample("D").last()` 적용. ★고치면 **sortino 값도 바뀌어** baseline regen 이 2 metric 으로 번지므로, "sharpe-only diff" 같은 감사 가능성을 유지하려면 별도 슬라이스로 분리하고 regen diff 범위를 미리 선언할 것.

**현재 대응:** `sharpe_ratio` docstring 명시 + FE 문구 "무위험 2%/년 · 봉 단위 기간 기준(2개월 미만)" 로 정직 고지.

**Risk:** 🟢 (고지 중 · 2개월 이상 백테스트는 월간 경로라 무영향).

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

[`docs/status.md` "Test Skip / xfail 추적표"](../.ai/templates/docs/status.md) 의 dette 2 건이 백로그로 이관:

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

**상태:** ✅ **(c) Resolved (2026-07-26, `feat/live-entry-wiring`)** — 세션 시작 422 `live_stop_entry_unsupported` + evaluate preflight 자동 종료. 실화면 확인(`0e15c3c0` 이 첫 tick 30초 내 자동 종료, PbR 422 문구 + EMA 201 음성 대조). **(a) 조건부 주문 등재는 열려 있다** — (c) 는 거짓말을 멈춘 것이지 기능을 만든 것이 아니다.

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

**Title:** `local_only` 판정이 화면에서 **구조적으로 렌더 불가** — 발산을 은폐하고 "포지션 없음" 이라 안심시킨다
**Category:** Frontend / trading (Surface Trust)
**Priority:** P2
**Trigger:** BL-478 수정 전 (지금은 이게 유일한 발산 표면)
**Est:** S
**출처:** 2026-07-26 dogfood-restore 체크리스트 B 실측

**원인 / 영향:** 백엔드는 발산을 **정확히 안다**. 실측(2026-07-26 04:47, 세션 `0e15c3c0`):

```json
{
  "positions": [],
  "local_open_trades_snapshot": [
    { "id": "PivRevLE", "direction": "long", "qty": 1, "entry_price": 64557.51 }
  ],
  "diff": { "verdict": "local_only", "local_source": "strategy_state_report" }
}
```

프론트에도 문구가 있다 — `open-positions-table.tsx:29` `local_only: "전략에만 열린 거래가 있습니다."`

**그런데 그 행이 만들어지지 않는다.** `hooks.ts:161-170` 이 행을 `positions.positions` 를 순회해 만드는데, `local_only` 는 **정의상 `positions` 가 비어 있는 경우**다. 루프 본문이 한 번도 안 돌아 `rows.length === 0` → `open-positions-table.tsx:234-247` 이 대신 렌더한다:

> **"열린 포지션이 없습니다. 활성 세션의 거래소 보고값에서 열린 포지션을 찾지 못했습니다."**

거래소 기준으로는 참이지만, **pine 이 롱을 들고 있다고 믿는다는 사실을 적극적으로 감춘다.** 같은 이유로 `exchange_only` 도 로컬이 빈 세션에서는 죽는다. 즉 6종 verdict 중 **불일치를 뜻하는 2종이 정확히 그 상황에서만 안 보인다.**

**권장 접근:** 행 생성을 `positions` 순회가 아니라 **세션 단위**로 바꾼다 — 세션마다 최소 1행을 만들고 `positions` 가 비면 verdict 와 `local_open_trades_snapshot` 을 보여주는 행으로 렌더. 회귀 방어는 `verdict='local_only' + positions=[]` 픽스처로 "열린 포지션이 없습니다" 가 **아닌** 것을 단정.

**상태:** ✅ **Resolved (2026-07-26, `feat/bl-474-webhook-ingress-parity`).**

`combineLiveSessionPositions` 에 `divergences` 를 추가했다. `positions` 가 비었을 때 **숨기면 안 되는 판정만** 골라 세션 단위로 건져 올린다(`isDivergentWithoutExchangePosition`):

| 판정                                               | 처리       | 이유                                                     |
| -------------------------------------------------- | ---------- | -------------------------------------------------------- |
| `local_only`                                       | **표면화** | 발산 그 자체                                             |
| `unknown` + `local_source='strategy_state_report'` | **표면화** | 상태 보고는 있는데 대조 실패 = 알아야 하는 상태          |
| `unknown` + `local_source='none'`                  | 조용히     | 아직 평가 전 — 숨길 것이 없다                            |
| `match`                                            | 조용히     | 양쪽 다 비었다. 정상                                     |
| `exchange_only`                                    | 해당 없음  | 정의상 거래소 포지션이 있어야 하므로 이 분기에 도달 불가 |

`isEmpty` 와 빈 상태 가드에 `divergences` 를 포함시켜 "열린 포지션이 없습니다" 로 떨어지지 않게 했다. 표에는 `unsupported` 와 같은 colSpan 행으로 렌더하며 전략이 들고 있다고 **보고한 내용까지** 같이 적는다.

**실화면 확인** — 라이브 세션이 마침 이 상태라 천연 픽스처였다:

> BTC/USDT · PbR Pivot Reversal · **전략에만 열린 거래가 있습니다.** 전략 보고: **PivRevLE 롱 1** 거래소 보고 포지션은 0건입니다.

[`screenshots/2026-07-26-bl480-divergence-surfaced.png`](dev-log/screenshots/2026-07-26-bl480-divergence-surfaced.png)

회귀 = 7건 **수정 전 RED 확인**(훅 5 · 컴포넌트 2). `match`/평가-전 `unknown` 이 조용히 남는 것도 함께 단정해, 가드가 무차별로 시끄러워지지 않음을 증명했다.

★**BL-478 이 살아 있는 동안 이게 유일한 발산 표면이다.** 근본 원인(진입 미발주)은 그대로다 — 이 수정은 **화면이 아는 것을 숨기지 않게** 만든 것뿐이다.

**Risk:** 🟢

---

### BL-481

**Title:** `sessions_allowed` 가 라이브에 미배선 — 거래 시간대를 제한해도 라이브는 24 시간 진입한다
**Category:** Backend / trading (라이브 게이팅 parity)
**Priority:** P2
**Trigger:** 세션 시간대 제한을 실제로 쓰는 사용자 등장 시
**Est:** S
**출처:** 2026-07-26 live-entry-wiring (BL-479 배선 중 발견)

**원인 / 영향:** 백테스트는 `cfg.trading_sessions → compat.parse_and_run_v2(sessions_allowed=...) → run_historical` 로 entry placement 와 pending fill 양쪽에 게이트를 건다(`compat.py:75`, `event_loop.py:72`). `run_live` 는 그 인자를 넘기지 않으므로 `run_historical` 기본값 `()` 가 적용돼 **24 시간 무제한**이다.

`Strategy.trading_sessions` 컬럼은 존재하고 백테스트는 존중한다. 즉 같은 전략이 백테스트에서는 아시아 세션만 거래하는데 라이브에서는 밤새 진입한다.

BL-188 v3 가 "Live `is_allowed` 와 단일 reference 정합" 을 목표로 했는데 라이브 쪽이 비어 있다.

**권장 접근:** `run_live` 에 `sessions_allowed` 를 추가하고 `live_signal.py` 가 `strategy.trading_sessions` 를 넘긴다. 단 `sessions_allowed` 가 비어 있지 않으면 OHLCV 인덱스가 tz-aware 여야 하므로(`event_loop.py:90-92`) 라이브 DataFrame 구성이 그 조건을 만족하는지 먼저 실측할 것. 회귀 = 허용 세션 밖 bar 에서 진입이 **안 나가는지**와 안 밖 양쪽 단정.

**Risk:** 🟡 (사용자가 명시한 제약을 라이브가 무시한다)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

### BL-482

**Title:** `pyramiding` cap 이 라이브에 미배선 — 같은 전략이 백테스트는 cap, 라이브는 무제한 중첩
**Category:** Backend / trading (라이브 게이팅 parity)
**Priority:** P3
**Trigger:** BL-478 (a) 로 진입이 실제로 열린 뒤
**Est:** S
**출처:** 2026-07-26 live-entry-wiring (BL-479 배선 중 발견)

**원인 / 영향:** `compat.py:101` 이 `strategy(pyramiding=N)` 을 추출해 `run_historical` 로 넘기지만 `run_live` 는 안 넘긴다 → `pyramiding=None` = cap 무효(`event_loop.py:115` 주석이 "None 시 무효" 를 명시).

지금은 진입 자체가 드물어 노출이 적지만, BL-478 (a) 로 조건부 진입이 열리면 같은 방향 포지션이 백테스트가 허용한 것보다 많이 쌓일 수 있다.

**권장 접근:** BL-481 과 같은 배선. `extract_content(source).declaration.pyramiding` 을 `run_live` 로 전달. BL-481 과 한 PR 로 묶는 게 자연스럽다.

**Risk:** 🟢 (진입이 열리기 전까지는 도달 불가)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

### BL-483

**Title:** `leverage` 가 라이브 엔진에 미배선 — 증거금 게이트와 청산가 모델이 L=1 로 no-op
**Category:** Backend / trading (라이브 리스크 게이트)
**Priority:** **P1**
**Trigger:** BL-479 머지 직후 (사이징이 켜지는 순간 증거금 판정이 유의미해진다)
**Est:** M
**출처:** 2026-07-26 live-entry-wiring (BL-479 배선 중 발견)

**원인 / 영향:** `StrategySettings.leverage`(1~125)는 `OrderRequest.leverage`(`live_signal.py:931` 근처)로만 흐르고 `configure_sizing(leverage=...)` 에는 안 들어간다. 그래서 라이브 엔진에서 `is_leverage_active(1.0)` 이 False → `_can_afford_entry` 격리증거금 게이트(`strategy_state.py:374`)와 청산가 모델(BL-186a / BL-480 계열)이 **통째로 no-op** 이다.

결과: **백테스트가 증거금 부족으로 거부할 진입을 라이브는 통과시킨다.**

★**그냥 넘기면 안 된다.** 넘기는 순간 그 게이트가 켜지는데, 증거금 부족 시 진입이 `warnings` 만 남기고 **조용히 skip** 된다. `warnings` 는 divergence 를 트리거하지 않으므로 완전 무음이다. BL-479 가 스코프에서 뺀 이유가 이것이고, 배선하려면 **skip 을 표면화하는 경로를 같이 만들어야 한다.**

**권장 접근:** (1) `run_live` 에 `leverage` 전달 (2) `_can_afford_entry` skip 을 `warnings` 가 아니라 관측 가능한 신호로 승격 — preflight 카테고리 또는 `qb_live_signal_skipped_total` reason (3) 회귀 = 증거금 부족 진입이 skip 되고 **그 사실이 화면/메트릭에 보이는지** 양쪽 단정.

**Risk:** 🔴 (백테스트가 거부할 포지션을 라이브가 연다)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

### BL-484

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
**Category:** Backend / trading (라이브 사이징 정합)
**Priority:** **P1**
**Trigger:** 세션이 warmup 창(1m 기준 5시간)보다 오래 살기 시작할 때. 즉 **지금 바로**
**Est:** M
**출처:** 2026-07-26 live-entry-wiring 최종 codex diff 리뷰 → 실측 재현

**원인 / 영향:** BL-479 가 `initial_capital` 을 배선하면서 `configure_sizing` 이 `running_equity = initial_capital` 로 시작하고, `strategy_state.py:668` 이 청산 손익을 누적한다. 백테스트에서는 이게 정확하다(inception 부터 전부 replay 하므로 누적 = 전체 손익).

**라이브는 warmup replay 라 누적 범위가 300 바 롤링 창이다.** 세션 나이가 창보다 짧으면 창 누적 = 세션 누적이라 정확하지만, 넘어가면 오래된 거래가 창 밖으로 밀리며 **같은 바의 수량이 바뀐다.**

실측 재현 (`tests/strategy/pine_v2/test_run_live_sizing.py::test_run_live_qty_drifts_with_warmup_window_KNOWN_LIMITATION`):

```
같은 마지막 바(종가 65536) · 같은 initial_capital=8192 · 같은 pct=50
  창 안에 청산 1건(+4096)  ->  qty 0.09375
  그 청산이 창 밖          ->  qty 0.0625      (50% 차이)
```

**미배선 시절의 `1.0`(모든 상황에서 틀림)보다는 낫지만 완결이 아니다.** BL-479 는 수량을 자본에 연동시켰고, 이 항목은 그 자본이 무엇이어야 하는지를 정한다.

**권장 접근:** 먼저 **시맨틱 결정**이 필요하다 — 셋 중 하나다.

- (a) **세션 시작 고정** — `running_equity` 를 라이브에서 누적하지 않는다. 결정적이지만 복리가 없고, 오래된 세션은 낡은 잔고로 사이징한다
- (b) **세션 누적** — `initial_capital = 스냅샷 + 창 이전 세션 실현손익`(DB 의 세션 손익을 이미 갖고 있다). 백테스트와 가장 가깝지만 실현손익(실제)과 replay 손익(시뮬)을 섞는다
- (c) **실잔고 추종** — 매 tick 조회. 지연(1.6s/tick)에 더해 실잔고에 이미 반영된 손익을 replay 가 다시 더하는 **이중 계상**이 생긴다 (BL-479 가 이 이유로 기각했다)

권고 = **(b)**. 다만 "실현/시뮬 혼합" 을 화면에 고지해야 한다. 어느 쪽이든 회귀는 위 KNOWN_LIMITATION 테스트를 **뒤집어** 같은 바가 창과 무관하게 같은 수량을 내는지 단정하는 형태가 된다.

**Risk:** 🔴 (주문 수량이 조용히 변한다. 머니-패스)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

### BL-487

**Title:** `test_get_pool_safe_across_event_loops` 가 `id()` 재사용에 취약 — 전체 스위트에서 random RED
**Category:** Test / 인프라 (flake)
**Priority:** P3
**Trigger:** CI 가 이유 없이 빨개질 때
**Est:** S
**출처:** 2026-07-26 live-entry-wiring 최종 게이트 (전체 스위트 1회 관측, 격리 실행·재실행은 통과)

**원인 / 영향:** `tests/common/test_redis_client.py:44` 가 두 `asyncio.run` 의 pool 인스턴스가 다름을 `assert first != second` 로 단정하는데, `_touch()` 가 **`id(pool)` 만 반환하고 pool 객체 자체는 붙잡지 않는다.** 첫 pool 이 GC 되면 CPython 이 같은 주소를 재사용할 수 있고 그때 `id` 가 같아진다.

즉 테스트가 검증하려는 것("reset 후 새 인스턴스")은 옳지만 **측정 도구가 틀렸다.** 이 스프린트 변경과 무관한 선재 결함이고, `pytest-randomly` 로 실행 순서/할당 패턴이 바뀔 때 드물게 드러난다.

**권장 접근:** `id()` 대신 **객체 참조 자체를 반환해 붙잡고** `assert first is not second` 로 단정한다. 두 객체가 동시에 살아 있으면 주소 재사용이 원천 불가능하다.

**Risk:** 🟢 (테스트 전용. 프로덕션 영향 없음)

**Status:** ✅ Resolved (2026-07-26, `feat/live-engine-parity`)

---

## 운영 규약

### 신규 항목 추가

1. 적절한 priority 결정 (P0~P3 정의 표 참조)
2. 다음 BL ID 부여 (현재 사용 범위: BL-001~005, BL-010~487)
3. 표준 8 필드 모두 채우기: ID / 제목 / 카테고리 / priority / trigger / est / 출처 / 권장 접근
4. 출처 cross-link (파일:라인 또는 dev-log 파일명) 필수
5. 의존성 있으면 명시 (다른 BL ID 또는 외부 자원)
6. CLAUDE.md / dev-log / TODO.md 의 자연어 표현 옆에 ` → BL-XXX` cross-link 추가

### 항목 해소

1. 해당 BL 절에 `**Status:** ✅ Resolved (2026-XX-YY, PR #NN)` 추가
2. [`_archived.md`](archive/refactoring-backlog/_archived.md) 의 Resolved 테이블에 1-line row 추가
3. 본 문서에서 본문 + main table row 제거
4. 출처 (CLAUDE.md / TODO.md) 의 cross-link 옆에 `(✅ Resolved BL-XXX)` 표기
5. "변경 이력" 섹션에 한 줄 기록

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
