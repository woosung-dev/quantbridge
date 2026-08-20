# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 `_archived.md`, trigger 미도래 의도적 부활 가능 항목은 `_deferred.md`. 문서 경로 정합성은 `tools/scripts/docs-audit.sh`로 검증한다.
> ★**tombstone (ADR-026 §5).** 본문이 가리키는 `_archived.md`(Resolved + stale 137건)·`_deferred.md`(부활 가능 8건)는
> 2026-08-06 문서 대개편에서 삭제됐다 — 원문 = `git show 0f0f0b06:docs/archive/refactoring-backlog/_archived.md`
> (`_deferred.md` 동일 경로). `_deferred.md` 내용은 본 문서 말미 「Deferred」 섹션으로 승격돼 있다.
> 그 뒤 강등분(2026-08-06 entry-set-divergence)의 본문 = `git show 23a9fcd4:docs/backlog.md`.
> ★**2026-08-13 docs-diet.** RESOLVED **78건**의 본문을 접었다 — 각 섹션에 `### BL-nnn` 헤더 +
> `**Priority:**`(또는 `**우선순위:**`) + `**상태:**` + **원래 있던 경우에 한해** `**Title:**` 을 남기고
> 나머지는 `📦 본문 접힘` 1줄로 대체했다. 접힌 78건의 원문 전량 = `git show 8abd0d67:docs/backlog.md`.
> ★**수치는 여기 박지 않는다** — 이 헤더 자신이 파일 크기를 바꾸므로 박는 순간 stale 이다. `wc -m` 으로 재라.
>
> ★★**어느 줄이 게이트에 집행되는지 실측했다 (변이 5종).** 「넉 줄 다 필수」는 **거짓**이다:
>
> | 지운 것            | `bl-audit` | 비고                                                  |
> | ------------------ | ---------- | ----------------------------------------------------- |
> | `### BL-nnn` 헤더  | **red**    | 「표 행만 있고 섹션이 없다」                          |
> | `**상태:**` 줄     | **red**    | 「표 행에 ✅ 인데 섹션은 ACTIVE」                     |
> | `**Priority:**` 줄 | **red**    | 「Pn 표에 실렸는데 섹션에서 우선순위를 못 읽었다」    |
> | `**Title:**` 줄    | green      | ★**집행되지 않는다** — 78건 중 **33건은 애초에 없다** |
> | `📦 본문 접힘` 줄  | green      | ★**집행되지 않는다** — 사람을 위한 표기다             |
>
> ⇒ 접기를 다시 할 때 **앞 셋은 반드시 남겨라.** 뒤 둘은 사라져도 게이트가 안 운다 — 사람이 지켜야 한다.
>
> ★★★**2026-08-18 수명 분리 완료 ([BL-779]).** 원장은 이제 **파일 셋**이고 **축은 판정어**다 —
> 본 파일 = **ACTIVE ∪ PARTIAL** + **인덱스 표 전량** ·
> [`backlog-deferred.md`](backlog-deferred.md) = **DEFERRED** ·
> [`backlog-resolved.md`](backlog-resolved.md) = **RESOLVED**.
> ★**규칙을 산문으로 두지 않았다** — `bl-audit.sh` 의 「파일 배치」 축이 rc=1 로 집행한다.
> 2026-08-16 의 1차 분할이 산문이라 그 뒤 닫힌 **13건이 전부 이 파일에 다시 쌓여 있었다**.
> ★**표 행의 `#bl-nnn` 앵커는 다른 파일을 안 가리킨다**(접두사 시도 → +18자/행이 줄 길이
> 상한을 넘겨 되돌렸다, [BL-801]). 섹션이 어디 있는지는 `bl-audit.sh --list <판정어>` 의 **4번째 칸**이 답한다.
> ~~원장은 이제 **파일 둘**이다 — 본 파일(열린 것) + `backlog-resolved.md`(RESOLVED 118건 본문).~~
> `bl-audit.sh`·`docs-audit.sh`·`bl-trigger-sweep.sh`·`context-budget.sh` 가 **셋을 한 벌로** 읽고,
> 섹션 수·판정 수는 **합계**다(`bl-audit` 머리줄이 파일별 수를 함께 찍는다).
> ★**인덱스 표 행은 여기 남아 있다** — 아래 `## Pn` 표에서 ✅ 가 붙은 행의 **본문은 저 파일에 있고**
> 행의 `#bl-nnn` 앵커는 같은 파일 안을 가리키지 않는다. 본문은 `backlog-resolved.md` 에서 찾아라.
> ★**항목이 RESOLVED 가 되면 본문을 옮기고 표 행은 남긴다.** 양쪽에 두면(=복사) `bl-audit` 이
> 「중복 섹션 헤더」로 red 를 낸다. 한쪽 파일이 비면 초록이 아니라 **rc=3 ABORT** 다.
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정. `_deferred.md` 도 6-8주마다 재평가.

**작성일:** 2026-04-30
**최종 갱신:** 2026-07-26 (**dogfood-restore 스프린트** — 로컬 실사용 복원 + 3스프린트 누적 신뢰 작업 실화면 검증. **BL-465/467 Resolved** +
신규 **BL-466/468~472/474** + **BL-473 Resolved**(WS auth `expires` 창 — 라이브 체결 스트리밍이 통째로 죽어 있었다). ★**dogfood 가
P1 을 잡았다** — `_periodic_returns` 가 음수 자본을 안 걸러 파산한 실행에 **양수 샤프**가 붙었고(실측 -2179.68% 에 +0.029), **committed
Trust Layer baseline 이 그걸 담고 있었다**(s1_pbr 샤프 +0.600 · 소르티노 +2.349 on -536%). 코퍼스 5종 중 4종이 음수 자본이고 골든이 깨진 것도
정확히 그 4종. baseline 재생성 diff = 12 메트릭 키 중 2개 한정. ★**옵티마이저는 이 스택에서 구조적으로 죽어 있었다** — `optimizer_heavy` 유일 소비자에
OHLCV env 3종 부재. ★**`mise run seed` 신설** — 백테스트 1회가 곧 OHLCV 시딩(TimescaleProvider cache-first). 마이그레이션 0.) // 이전:
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
**현재 상태:** **집계 수치를 여기 박지 않는다** — 정본은 `bash tools/scripts/bl-audit.sh` 이고, 그 스크립트는 `tools/scripts/final-gates.sh` 게이트 체인 안에 있다(라벨 `BL 감사`, BL-564). 숫자가 필요하면 **그 자리에서 재라.** 문서에 박은 수치는 BL 하나만 추가돼도 즉시 stale 이고, 이 줄은 실제로 여러 스프린트 동안 stale 이었다. **BL-070~075 milestone active 승격** (deferred → P0 prep).

> ★이 수치는 손으로 세지 말고 기계적으로 재라 — 직전까지 "49 active" 로 여러 스프린트 동안 stale 했고, 그 다음 표기 "86 active / 전체 135" 도 실측(217 섹션)과 어긋나 있었다. **산식은 이제 문서 주석이 아니라 스크립트다:**
>
> ```bash
> tools/scripts/bl-audit.sh                   # 판정 + P별 내역 + 3면 불일치 + UNKNOWN 목록
> #                                       UNKNOWN · 3면 불일치 · 중복 상태줄 · 중복 섹션 헤더 · 미닫힌 펜스/<details> → exit 1
> tools/scripts/bl-audit.sh --list ACTIVE     # 트리거가 **도래한** 것 전량 (★목록 전용 — 판정 불일치로는 exit 0, 게이트에 쓰지 마라)
> tools/scripts/bl-audit.sh --list DEFERRED   # 트리거 **미도래**로 대기 중인 것
> tools/scripts/bl-trigger-sweep.sh --selftest  # ★도래 판정기의 판별력. 전량 스윕보다 **먼저** 돌려라
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
  14건(코드 대조 후 반영, BLOCKING 3=leverage 라우팅·flatten 불변식·hedge 거부) → codex 2워커 병렬(apps/api/frontend 교집합 0) ↔
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
**Trigger:** Bybit Demo 1주 안정 운영 후 + BL-004 완료 후 (BL-004 = 완료, Sprint 28). ★**「1주 안정 운영」은 2026-08-05 부터 기계가 판정한다** — `tools/scripts/soak-gate.sh` 가 PASS/FAIL/UNKNOWN 을 내고 **PASS 만 exit 0** 이다. 술어·창·리셋 규칙 = [ADR-024](decisions/024-soak-stability-gate.md).
**Est:** M (4-5h)
**출처:** [2026-04-30 당시 `docs/TODO.md`의 mainnet 준비 항목](https://github.com/woosung-dev/quantbridge/blob/b2c1541054326b06acf5e64f25094b6d5a37ea10/docs/TODO.md#L650-L653)

**원인 / 영향:** dogfood 가 Bybit Demo 만으로는 H1 종료 gate 충족 안 됨. mainnet 전환 시 수동 step 누락 위험 (IP whitelist / 출금 권한 차단 / 레버리지 1:1 / 소액 시작).

**권장 접근:** ★★★**2026-08-09 에 이 3줄 중 4건이 코드 대조로 반증됐다** — 아래 「반증」 표를 먼저 읽어라.

1. ~~Trigger 충족 시 당시 Bybit 정책·계정 모드에 맞춘 mainnet runbook 신규 작성~~ → **2026-08-09 작성 완료**
   = [`bybit-mainnet-runbook.md`](reference/operations/bybit-mainnet-runbook.md). ★**Trigger 를 기다리지 않았다** —
   Trigger 가 막는 것은 산출물의 **실행**이지 **작성**이 아니다.
2. ~~`tools/scripts/bybit-smoke.sh` 신규~~ → **2026-08-09 신규 + 기존 파이썬 재사용**(`bybit_demo_smoke.py` → `bybit_smoke.py`).
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
**트리거 판정:** 미도래 — 소크 축. ~~2026-08-11 게이트 실측 `rc=2 UNKNOWN` · C1 **68.2197h**/168h · 24h 이상 창 **1/3**(15.30h · 0.01h · 52.91h)~~
→ **2026-08-15 07:03Z 재측정 — 그 수치는 낡았고 분모도 폐기된 것이다.** 현행 문턱은 **24h 창 3회**이고
누적 168h 는 참고값으로 내려갔다([BL-701]). 실측 `rc=2 UNKNOWN` · **C1 0/3** · C2 **14.5507h**/24h ·
C3 실격 0 · C4 공백 0 · C5 6/6 · 귀속 창 1개. **08-11 의 「1/3」이 지금 0/3 인 이유는 후퇴가 아니라
창이 새로 열렸기 때문**이다(08-14T16:29 `up`). 남은 것은 코드가 아니라 **시간 약 9.45h**다.
★이제 「지금 `up` 을 눌러도 되나」는 판독이 답한다 — `soak-gate.sh` 의 `▶ 새 창을 열어도 되나`
블록(2026-08-15 ledger-thaw). 자격을 얻기 전에 누르면 이 14.55h 가 **창 0회로 소멸**한다. PASS 만 도래다([ADR-024])

**산출물 (2026-08-09):**

| 파일                                                                                                  | 무엇                                                                                           |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [`docs/reference/operations/bybit-mainnet-runbook.md`](reference/operations/bybit-mainnet-runbook.md) | 전제조건 · cutover 2곳 · 시크릿 · Kill Switch 표 · 2단계 진입 · **rollback** · [확인 필요] 5건 |
| `tools/scripts/bybit-smoke.sh`                                                                        | 정문. `--dry-run` 기본 · **그 경로 네트워크 호출 0건**(정적+동적 대조) · fail-closed 검사 6종  |
| `apps/api/scripts/bybit_smoke.py`                                                                     | `bybit_demo_smoke.py` rename. `--mode live` · `--market spot` · credentials **env 전용**       |
| `apps/api/.env.prod.example` · `.env.example`                                                         | `KILL_SWITCH_*` mainnet 값 · `BYBIT_SMOKE_*` · 보관처 문구 교체                                |

**★★★반증 (2026-08-09 — 이 회차의 최대 산출):**

| 본문/코드 주석이 말한 것                                                           | 실측                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 「BybitDemo/Futures **base URL mainnet 매핑**」이 할 일 (`providers.py:2256-2257`) | **이미 있다.** `_apply_bybit_env`(`providers.py:2202-2210`)가 demo → `enable_demo_trading(True)` · **live → no-op(`api.bybit.com`)** 로 이미 가른다. 축은 `Credentials.environment`(`:108-109`) ⇒ **provider 본문을 새로 쓸 일이 없다**(단 「cutover 는 2줄」은 **아래에서 다시 반증됐다 — 6곳이다**) |
| 소액 **$10~50** 시작                                                               | **그 자본으로는 세션이 주문을 0건 낸다.** 사이징은 자본 비례(`strategy_state.py:503-506`)이고 서버 실측 자본 190,034 USDT → 주문 0.058 BTC ⇒ `X_min = 190,034 × (0.001/0.058) ≈ **$3,276**`. ★BTC 가격도 pct 도 **소거된다**(비율만 쓴다)                                                             |
| `tools/scripts/bybit-smoke.sh` **신규**                                            | 뼈대가 **이미 있었다** — `apps/api/scripts/bybit_demo_smoke.py` 221줄·6단계. 신규는 셸 래퍼뿐이다                                                                                                                                                                                                     |
| `.env.production` **별도 secret manager**                                          | `apps/api/.env.prod.example` 이 **이미 존재**했고 GCP Secret Manager 를 전제로 쓰여 있었다 — 그런데 **실제 배포는 오라클 docker compose** 다. 신규 작성이 아니라 **현실과 맞추는 개정**이 답이었다                                                                                                    |
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
`grep -rn "ExchangeMode.demo" apps/api/src/` 전수: `live_session_service.py:115` ·
`live_signal.py:3383` · `close_service.py:92` · `position_service.py:332` · `:427` (+`registry.py:43-44`).
★**진입 자물쇠(⑵⑶)와 출구 자물쇠(⑷)가 다르다** ⇒ runbook 에 **「⑷ 를 먼저 풀어라」** 순서 규약을 넣었다.

★**부수로 하나 더 반증됐다** — 「registry stub 이 안전장치다」도 **거짓**이다.
`BybitFuturesProvider()` 를 **직접 생성**해 registry 를 우회하는 자리가 **13곳**이고
(`grep -rn "Bybit\(Futures\|Demo\|Live\)Provider()" apps/api/src/` → 14줄 중 1줄은 주석),
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

**게이트 현황 (2026-08-05 conditional-stop-ownership 재측정):** `tools/scripts/soak-gate.sh` = **FAIL** (exit 1) — 누적 **0h / 168h**. ★**차단자 [BL-595] 를 이 회차에 수리했다**([ADR-025]) — 라이브 조건부 진입 체결의 권한을 주문 원장으로 옮겼고, 사망 **5건 전량을 얼려 재현**(영속 보고서와 비트 단위 일치)한 뒤 수리 전 5/5 `direction` 발산 → 수리 후 5/5 일치를 보였다. ★**착수 중에 소크 세션 `a16aa640` 이 죽었다**(08-05T09:12:53Z, 생존 8.642h) — 5번째 사망이자 워커 로그가 남은 유일한 건이라 오라클을 거래소 실측으로 교차검증하는 데 썼다(3/3 일치). 기저율 재측정: [BL-590] 이후 노출 **18.831h 에 자동 사망 3건 = 0.159/h(MTBF 6.3h)** · `phantom` 6건 = 0.319/h. ★★codex 가 **「가장 오래 산 세션에서 보호가 먼저 꺼지는」** 경로를 잡았다 — 원장 조회가 세션 스코프 + 상한 200 이라 체결 2.55건/h 로 **약 78시간**이면 영구 판정 불가가 된다(이 항목의 168h 누적 경로에서 정확히 밟는다). 재생 창 스코프로 바꿔 닫았다.

**이전 게이트 현황 (2026-08-05 divergence-rejudgement):** C3 **3건**(`cc19abd2` phantom 2 + auto_death 1), 소크 세션 `a16aa640` · 커밋 `f5f06886`. ★★★**실제 차단자는 달력 시간이 아니라 「엔진과 거래소가 서로 다른 stop 주문을 든다」는 것 — 신규 [BL-595]**. 사망 4건 부검에서 **엔진이 앞선 3건 · 거래소가 앞선 1건**으로 방향이 갈렸고, 킬 정책 교체([BL-591] 슬라이스 B)로 살아났을 세션은 **0개**다. ★★**판별식 교체 — 봉경계식 → 재무장 도장식**([ADR-024] §판별식 교체): 19건 전량 재적용 시 phantom **11→7**, 사망 상관 **4/4 보존**, **판정은 여전히 FAIL**(교체가 통과를 사지 않는다). ★아카이브에 판(版)을 실었다 — 안 그러면 취소된 라벨이 영원히 남는다. ★★★**과거 56.44h 는 소급 인정하지 않는다**(귀속 가능 0.46%) · **역대 2위 8.65h 는 마지막 46.7분 평가 정지** ⇒ 「역대 최장 15.3h = 9%」는 두 겹 낙관이었다.

---

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Trigger                                                                      | Est      | 출처                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------- | --------------------------------- |
| [BL-014](#bl-014) | 🟡 부분 Resolved — Partial fill `cumExecQty` tracking (잔여 = BL-439/440/441)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 🟡 2026-07-25 `stage/money-path-accuracy`                                    | M (4-5h) | TODO.md L709                      |
| [BL-724](#bl-724) | ✅ 소크 전략 경제성 판정 — **Resolved (판정)** (2026-08-14 money-path-close). 답 = **실자금 불가 · 데모 유지**. 고유 청산 596건 실측 gross **+82.64** vs 수수료 **−1,204.21** ⇒ 순 **−1,121.57**(gross PF 1.149 → net PF 0.223). 손익분기 요율 단면 **0.00377%** = 현재의 **1/14.6** 이라 어느 VIP tier·maker 로도 구제 안 된다. ★원 표제 「전략은 흑자였다」는 **라이브 한 축에서만** 참 — 같은 정의로 맞춘 백테스트 gross 는 **−34,582** 로 음수이고, 그 전략의 백테스트 4벌이 **전부 PF < 1**(0.57~0.86)이다. 수리 아님 = 코드 변경 0                                                                                                          | —                                                                            | M (2-3h) | 2026-08-14 money-path-attribution |
| [BL-022](#bl-022) | ✅ golden expectations 재생성 — **Resolved** (2026-08-07 backtest-fidelity). `apps/api/scripts/regen_golden.py` 신설(`--confirm`/`--case`/`--check`). ★이 스크립트가 없었던 것이 [BL-621] stale 의 직접 원인이다                                                                                                                                                                                                                                                                                                                                                                                                                                  | pine_v2 `strategy.exit` 도입 후                                              | M (3-4h) | TODO.md L17 (skip #1)             |
| [BL-024](#bl-024) | ✅ real_broker E2E 실주문 leg — **Resolved** (2026-08-14 real-broker-e2e, 로컬 축). Bybit demo linear perp 실주문→watchdog filled→2층 하네스 청산까지 거래소로 확인. ★하네스는 그때까지 한 번도 작동한 적이 없었다(청산이 개발 DB 를 열고 있었다). 잔여(별건) = HTTP webhook 층 · CI 축                                                                                                                                                                                                                                                                                                                                                           | Bybit Demo credentials + seed data 준비 시                                   | L (8h+)  | CLAUDE.md Sprint 10 Phase C       |
| [BL-025](#bl-025) | ✅ autonomous-parallel-sprints 스킬 patch                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | on-demand (BUG-1/2/3 재발 시)                                                | S (2h)   | TODO.md L653                      |
| [BL-026](#bl-026) | ✅ **Mutation Oracle 실행 확인 — Resolved** (2026-08-15). ★**코드 0줄**: 지목된 `:418` 은 이미 묘비명 주석이고 껍데기는 08-11 에 삭제됐다. `--run-mutations` 실행 = **7 passed + 1 xpassed (skip 0)**. 「12 skip 일괄 활성화」는 **대상 집합이 없었다** — 제목·Est·dangling 출처를 함께 정정                                                                                                                                                                                                                                                                                                                                                      | Stage 2c 2차 fixture 활성화 후                                               | S (1-2h) | TODO.md L20-22                    |
| [BL-619](#bl-619) | 🟡 부분 — ★**라이브 파이프라인이 한 세션에 ~17분 멈췄고 뿌리를 모른다.** 관측 장치는 2026-08-08 에 서버로 올렸다(systemd user unit `soak-logs-follow`, 실측 active·871KB·세션 `a4f1cbfb` 로그 유입). ★그것은 Trigger 를 **충족 가능하게** 만든 것이지 뿌리를 안 것이 아니다 — 닫는 조건은 재관측 부검 그대로다                                                                                                                                                                                                                                                                                                                                    | 다음 서버 소크 창에서 같은 정지가 관측되면 (로그가 남아 있는 동안 즉시 부검) | M        | 2026-08-08 bl003-unblock          |
| [BL-633](#bl-633) | ✅ **이중 호스트 오염 — 근인 확정** — 같은 Bybit demo 계정의 맥 로컬 체결이 서버 세션 `39484a2c` 를 죽였다. G-A4‴ 소유권 7/27(귀속 불가 0)·G-A6′ 정본 항등식 4/4(반사실은 정의 4가지 어디서도 4/4 불가, 최대 1/4)·G-A7 계정 결합 27/27 이 뒷받침한다. ★원안 G-A4′ 6/6·G-A6 3/3 은 회차 도중 반증돼 교체됐다. `phantom` 은 증상이며, 오염 창은 ADR-025 의 반례로 셀 수 없다                                                                                                                                                                                                                                                                        | — (부검 완료 · 후속은 BL-634 · BL-641 로 이관)                               | M        | 2026-08-08 bl003-unblock          |
| [BL-634](#bl-634) | ✅ **`register()` 전제조건 가드** — 같은 Bybit demo 계정에 두 호스트가 동시에 붙는 계정 배타성 가드 부재 — 두 DB 의 `live_signal_sessions` unique index 는 다른 호스트를 막지 못하며, 이번 `position_divergence` 사망의 직접 원인이다                                                                                                                                                                                                                                                                                                                                                                                                             | 실자금 전환 전 필수 / 두 번째 호스트를 다시 띄우기 전                        | M        | 2026-08-08 bl003-unblock          |
| [BL-635](#bl-635) | ✅ **게이트 아카이브 오염이 라이브 기전이다** — 판독 불가 로그를 시간 credit 하지 않고 `UNKNOWN 측정불가`로 내리도록 `32ea2a5d` 에서 수리했다. 서버 systemd 만 대상이며 맥 launchd 타이머는 잔여다                                                                                                                                                                                                                                                                                                                                                                                                                                                | — (해결됨. 맥 launchd 잔여는 별도 후속)                                      | S        | 2026-08-08 bl003-unblock          |
| [BL-661](#bl-661) | 🟡 **`flatten` 이 「이미 flat」으로 exit 0 하는데 조건부 주문은 남는다** — 2026-08-10 거짓 성공 제거(보고 + exit 3), 취소는 [BL-669](#bl-669) 로 분리. `close_service.py:100-104` 가 포지션만 보고 미체결 조건부 진입을 안 본다. 운영 CLI(`live_session_admin.py:383-387`)가 그 409 를 **성공으로 출력하고 return** 한다 ⇒ 고아 조건부가 나중에 트리거된다. [BL-003] rollback 이 이걸 **문서로만** 방어한다                                                                                                                                                                                                                                       | 실자금 전환 전 필수 / 조건부 진입 세션을 내릴 때                             | S        | 2026-08-09 bl003-mainnet-runbook  |
| [BL-641](#bl-641) | 🟡 부분 — BL-003 의 실질 선행조건은 문턱이 아니라 **MTBF** 다. 층화 + 95% CI 를 [ADR-024] 에 등재하고 재측정 도구(`mtbf_stratified.py`)를 만들었다. ★★★**점추정을 인용하지 마라 — CI 가 2026-08-12 에도 전 쌍 겹친다**(MTBF 13.39h→24.17h 로 1.8배 올랐는데도 「올랐다」를 못 말한다). 결론이 서는 근거는 셈이다: **24h 도달 1건/40세션 · 최장 65.28h**(2026-08-12 재측정, 노출 +86h 에 자동 사망 0건). ★**「이 표가 `user_stopped` 를 사망과 함께 센다」는 거짓이었다** — `soak_gate_predicate.py:39` 가 정본이고 처음부터 절단이었다                                                                                                            | BL-003 재계획 시 즉시 / 소크 재기동 회차마다 재측정                          | M        | 2026-08-08 bl003-unblock          |
| [BL-716](#bl-716) | ✅ **반증 카드 승격 — Resolved (2026-08-14 gate-surface-close)**. ★처방 2건이 착수 전 반증됐다 — 후보 3종이 이미 카드/승격 완료라 「카드 신설」은 `lessons.md:12` 규약 위반이고, 그래서 「자리 확보 선행」도 불필요했다(정본 동작은 오히려 **362→358줄**). 이행 = [LESSON-101] → `generator-evaluator-pipeline.md` **§8.6** 승격(14회 = dev-log 22줄 중 12 + 기존 2) · 「착수 전제 반증」축(12/22)은 이미 §8.1 이라 **기저율만 보강** · 선행 수리 2건(`LESSON-101` ID 충돌 → [LESSON-107] 재번호 · 죽은 경로 10곳). ★후보 ②는 **1/22 로 문턱 미달** — 승격 안 함. 게이트 결손은 [BL-720]                                                          | 2026-08-13 docs-diet (codex 적대 리뷰 P1)                                    | M        | 2026-08-13 docs-diet              |
| [BL-719](#bl-719) | ✅ **재배치 롤아웃 lockstep — 해결 (2026-08-13)** — PR #619 머지 직후 5단계 완주: ① 서버 uninstall→down→pull→`.metrics` 이행→pin `c3a39d0d`→up→install. 첫 판독 tick_stall 실격 1건 = **down 창 자체**(operational 등재 · 창 리셋 예정대로 · C5 6/6 ✓) ② 맥 LaunchAgent 재설치 ③ 메인 이행(6컨테이너 Healthy · strategies 3행 = 볼륨 무손실 · 잔재 삭제는 중단-후-분류) ④ 워크트리 0벌(재생성은 착수 시 bootstrap) ⑤ canary #620 backend 3레인 발화 + FE 정상 skip. 이행이 낳은 핫픽스 #621(`--strip-components` 2→3)                                                                                                                             | — (이행 완료)                                                                | S        | 2026-08-13 monorepo-realign       |
| [BL-734](#bl-734) | ✅ **소크 사망의 진짜 뿌리 — Resolved** (2026-08-15 soak-survival). `tests/real_broker` 하네스의 `close_position` 이 계정 포지션을 **소유권을 보지 않고** 닫아 서버 소크를 죽였다(거래소 원장 `04:49:56 Buy 0.029 CreateByUser link=(empty)` → `exchange_position=+0.001` → strike 2연속). [BL-633] 재발이며 경로만 다르다. 수리 = `find_foreign_resting` 추출 후 청산 전 fail-closed 호출                                                                                                                                                                                                                                                        | — (부검 완료)                                                                | M        | 2026-08-15 soak-survival          |
| [BL-735](#bl-735) | ✅ **소크를 로컬 맥에서 돌리지 않는다 — Resolved** (2026-08-15). AC 전원에서도 `sleep 1` 이라 로컬 24h 창은 구조적으로 불가능. 기계 강제가 들어갔다 — `_up()` **첫 줄**(`assert-main-checkout` 앞)에서 Darwin 거부(rc=2) · `QB_SOAK_ALLOW_DARWIN=1` 탈출구. 개발 격리 스택은 **파일이 달라** 무영향. 신규 하네스 `soak-stack-test.sh` 9케이스(10종→**11종**) · 음성 대조 · 변이 red 2건                                                                                                                                                                                                                                                           | 도래 — 2026-08-14 실사고                                                     | S        | 2026-08-15 soak-survival          |
| [BL-743](#bl-743) | ✅ **서버 DB 에 migration 이 도달하는 경로 — Resolved (2026-08-15 soak-watch-restore)**. ★가설보다 컸다: `pin` 이 `alembic/` 을 안 뜨는 것은 증상이고, 뿌리는 **소크 compose 에 api 롤이 없어** `run_alembic_with_lock` 을 부르는 경로 자체가 없다는 것(celery `command:` override 가 entrypoint 를 passthrough 로 우회). 채택 = **`soak-stack.sh migrate`**(dry-run 기본 + `--confirm`), ⑴ `up` 자동 upgrade 는 **창 중 암묵 DDL** 이라 기각. upgrade 뒤 `docker exec psql` 재확인으로 오적용 차단. 곁가지 = `SOAK_WATCHED_PATHS` 가 **없는 경로 `scripts`** 를 보고 있었고 alembic 은 안 봤다. 서버 적용 완료(승인) — 인덱스 집합 로컬과 diff 0 | 도래 — 버전 불일치 실측                                                      | S (1-2h) | 2026-08-15 soak-survival          |
| [BL-744](#bl-744) | ✅ **서버 `quantbridge-api.service` 좀비 — Resolved (2026-08-15 soak-watch-restore)**. [BL-737] 과 같은 뿌리인데 더 위험했다: 08-07 기동 프로세스가 **삭제된 cwd**(`…/backend (deleted)`)를 붙들고 살아 있었고 `ExecStart` 는 사라져 **죽으면 rc=203/EXEC 영구 실패**였다(systemd 자신이 `Current command vanished` 를 남겼다). 이 API 가 **C5⑷ 스크레이프 대상**이고 `PROMETHEUS_MULTIPROC_DIR` 도 게이트가 읽는 곳과 어긋나 파일 폴백까지 반쪽이었다. 유닛 3곳 교정 후 재시작 — `/health` 200 · `/metrics` 무인증 401 유지 · bearer 200                                                                                                         | 도래 — 삭제된 cwd 실측                                                       | S (30분) | 2026-08-15 soak-watch-restore     |

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

## P2 — Hardening / 건강도 작업

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Trigger                                                                                                         | Est             | 출처                                                         |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------ |
| [BL-732](#bl-732) | ⏳ **대기 — 표본이 반증됐다.** 등재 근거였던 로컬 소크 6h33m 사망은 **맥 sleep** 이 원인이다(`pmset` 로그와 초 단위 일치 · beat 가 168회 중 **15회**만 tick 했고 그 15회가 DarkWake 횟수). `gap_resync_position_mismatch` 는 그 공백의 하류 증상이라 코드 축 판별에 못 쓴다. C1 을 실제로 끊은 사건은 [BL-734] 로 확정·수리됐다                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | ~~도래~~ → **미도래** (깨끗한 창에서 재발 시)                                                                   | M (3-4h)        | 2026-08-14 money-path-close → 08-15 재기술                   |
| [BL-747](#bl-747) | ✅ **감시 타이머 위상 고정 — Resolved (2026-08-15 soak-watch-restore 후속)**. `OnUnitActiveSec` 은 **마지막 활성화 기준**이라 사람이 손으로 한 번 돌리면 위상이 밀린다 — 최악 `29+30=59`분이고 C4 한계가 60분인데 systemd 기본 `AccuracySec` 이 1분이라 여유가 사실상 0. 실측 **53분**. ★**이 회차의 검증 자신이 만든 위험**이었다. `OnCalendar=*:00/30`+`AccuracySec=30s` 로 벽시계 고정 — 강제 발화 전후 `NEXT` 불변 실증                                                                                                                                                                                                                                                                                                                                                                               | 도래 — 53분 간격 실측                                                                                           | XS (20분)       | 2026-08-15 soak-watch-restore                                |
| [BL-720](#bl-720) | ✅ **Resolved (2026-08-14 gate-pointer-axis)** — 축 **2종** 신설(LESSON ID 유일성·오름차순 = 헤딩 ∪ 승격 표 · 승격 표 백틱 포인터 실재). 하네스 7→**12 케이스**. ★**처방 ②(`legacy_paths` 확장)는 착수 전 반증돼 폐기** — 살아 있는 문서에 `backend/`·`frontend/` 리터럴이 **147줄**이고 [ADR-029] 매핑 표 자신을 포함해 대부분이 고칠 수 없는 정당한 인용이다(부분문자열 매치라 예외 불가). 죽은 포인터는 새 축이 이유 불문 잡으므로 흡수했다. ★**새 축의 첫 판이 실제 트리에서 오탐 3건**(자리표시자·코드 표현식·슬래시 커맨드) — 스텁만 봤으면 못 봤다                                                                                                                                                                                                                                                 | 도래 — 결손 3종이 실측 확정                                                                                     | S               | 2026-08-14 gate-surface-close                                |
| [BL-725](#bl-725) | `exchange_exits` **중복 290행** — 같은 uid 에 계정 행이 둘이라 각자 같은 창을 적재했고 UNIQUE 축이 `(exchange_account_id, row_hash)` 라 안 걸린다. 원장 882행 = 고유 **592** + 중복 290(잉여 −517.84). ★[BL-605] 수리는 작동 중이고 **신규 적재는 2026-08-08 에 멈췄다** — 잔재다. 중복쌍이 서로 다른 라벨을 받는 편향 동반                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 동승 — `exchange_accounts` 행 축 결정 대기                                                                      | S (30분)        | 2026-08-14 money-path-attribution                            |
| [BL-726](#bl-726) | ✅ `rejected` reduce-only 46건 `realized_pnl` **+55.32** — **Resolved (기각)** (2026-08-14 `dde53e68`/#631 + 코드 대조). 모순이 아니었다: 값은 **생성 시점**에 실리는 **체결 전 추정치**다(`order_service.py:393,427` — 라이브·웹훅 두 축 모두). `exchange_order_id` 는 46건 전부 **NULL** = **주문 ID 미발급·미체결**(`110017`/`10005` 는 거래소가 **반환한** retCode 이므로 「미도달」이 아니다). ⇒ `state==filled` 필터가 **옳다**. ★원장 처방 ⑵ 는 이 46건에 **no-op** 이고 채택하면 게이트가 되레 느슨해진다. 동작 변경 0                                                                                                                                                                                                                                                                            | —                                                                                                               | S (1h)          | 2026-08-14 money-path-attribution                            |
| [BL-727](#bl-727) | ✅ `soak-gate.sh` 판정 본체의 맨 `python3` — **Resolved** (2026-08-14 `dde53e68`/#631). `:706`·`:714`~`:716` 을 `uv run python` 으로 + **빈 출력 fail-closed**. 종전에는 맥 3.9 의 `itertools.pairwise` 부재로 죽고도 진행해 **빈 `판정:` 줄**을 찍는 fail-open 이었다. 맥 음성 대조 3단계로 판별력 증명                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | —                                                                                                               | XS (10분)       | 2026-08-14 money-path-attribution                            |
| [BL-729](#bl-729) | ✅ **낡은 비용 가정 백테스트 — Resolved** (2026-08-15). Cost-Assumption 9-cell 을 **실측점 포함 격자**로 돌려 판독: 실측 `−7.74%` vs 저장값 `−22.59%` ⇒ **[BL-724] 유지**(부호가 안 바뀐다). ★부수 — 왕복 비용 2.17배에 손실 2.92배로 **비선형**이라 선형 외삽은 틀린다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 즉시 — 소크 전략을 다시 고를 때의 입력 (소크 정지 창에서)                                                       | S (1h)          | 2026-08-14 money-path-close                                  |
| [BL-730](#bl-730) | ✅ **FE 비용 기본값 drift — Resolved** (2026-08-15). 리터럴 **5벌**을 `cost-defaults.ts` 하나로 모았다(이미 맞던 3벌 포함 — 안 모으면 다음 조정에 같은 3/5 문제). 온보딩 payload 테스트 신설 + stress 프리셋 격자를 기본값 기준 1x/2x/4x 로                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ★이미 발화 — 온보딩 프로덕션 경로                                                                               | XS (15분)       | 2026-08-14 money-path-close                                  |
| [BL-731](#bl-731) | ✅ **`list_synced_with_exchange_exit` LIMIT 500 — Resolved** (2026-08-15). `IS DISTINCT FROM` 을 SQL 술어로 끌어올려 모집단이 **0 으로 수렴**한다 — 상한도 정렬도 안 바꿨다. 수리 전 red 선확인                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | ★이미 발화 조건 성립 — 수리가 머지됐다                                                                          | S (1h)          | 2026-08-14 money-path-close                                  |
| [BL-733](#bl-733) | ✅ **체결 직후 refresh `reduce_only` 게이트 — Resolved** (2026-08-15). `_reversal_bucket_at_fill` 을 재사용해 **반전이 증명된 leg 만** 예약(`unmeasured_*` 는 스윕에 맡긴다). ★실행측 게이트엔 테스트가 **0건**이었다 — 지워도 31 passed 였다. 그 그물도 함께 신설                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 도래 — 나머지 2곳이 유일 잔여                                                                                   | M (2-3h)        | 2026-08-14 money-path-close                                  |
| [BL-736](#bl-736) | 🟡 **QuantBridge 축 종결 — 남은 것은 우리 것이 아니다** (2026-08-15): 로컬 Docker VM **94%** 에서 Redis AOF 가 `No space left` 로 죽어 celery 가 통째 정지했다(08-14T06:04Z). 우리 소유 미사용 볼륨 11개를 개별 삭제 = **70MB**(회수 가능 19.64GB 의 **0.4%**). 이미지는 미삭제 — 프론트 3태그가 **같은 ID** 라 0B 고 백엔드 4종은 소크 재기동에 필요하다. **94% 는 그대로이고 우리가 더 할 것이 없다**                                                                                                                                                                                                                                                                                                                                                                                                   | 도래 — 06:04Z 실사고 로그                                                                                       | S (1h)          | 2026-08-15 soak-survival                                     |
| [BL-737](#bl-737) | ✅ **soak-watch 부활 + 감시자의 죽음을 알리는 축 — Resolved (2026-08-15 soak-watch-restore)**. ★사인·사망시각이 원장과 달랐다: `rc=127`(유닛 `ExecStart` 가 재배치 전 `scripts/` 경로) · **08-13 13:52Z 부터 41시간** 침묵(08-14 아니다). 뿌리는 [BL-719] 롤아웃 체크리스트가 soak-watch 를 안 적은 것. 정본 = **watch 가 게이트 타이머를 대체한다**(병존 경합을 실측 — 0.7초 간격 중복 표본, 단 JSON 손상 0). 이중화 대신 **`OnFailure` 알람 유닛**(스크립트 비의존 인라인 curl)과 **`--status` 설치본 신선도**를 신설. 하네스 23/23 · 변이 4종                                                                                                                                                                                                                                                          | 도래 — failed 실측                                                                                              | S (1h)          | 2026-08-15 soak-survival                                     |
| [BL-741](#bl-741) | ✅ **Resolved (2026-08-15)** — `create_all` 스키마 위에서 새 migration 이 `DuplicateTable` 로 죽었다. CI(fresh DB)는 안 걸리고 **로컬에서 pytest 를 돌린 개발자만** 걸린다. 처방 = `create_all` 직후 `alembic_version` **head stamp**. ★착수 전제 반증: 인덱스 생존 경로는 **없고** 남는 것은 `alembic_version` 하나였다(지우기만 하면 base 부터 돌아 여전히 죽는다)                                                                                                                                                                                                                                                                                                                                                                                                                                      | 도래 — 실제 red                                                                                                 | S (1-2h)        | 2026-08-15 soak-survival                                     |
| [BL-748](#bl-748) | ✅ **소크 게이트 C4 공허 통과 — Resolved** (2026-08-15). `clean`(귀속 창)이 비면 루프가 0회라 `C4_ok = not gaps` 가 **통과**했다 — 「볼 게 없다」가 「이상 없다」로 보고되는 fail-open. 실측 대조에서 상위 공백 5개(최대 **1524.5분**)가 전부 귀속 구간 밖이라 한 건도 안 세졌다. `bool(clean) and not gaps` + 사유 문장 분리 + 소품 2건(darkness 타입 · 복제된 어둠 집합의 동등성 테스트). 술어 72 passed · 변이 red 확인                                                                                                                                                                                                                                                                                                                                                                                | ★이미 발화했다 — 실측 출력이 근거                                                                               | S               | 2026-08-15 clock-fill-sweep                                  |
| [BL-738](#bl-738) | [BL-734] 가드의 **한계 3종** — ⑴ 남이 resting 없이 포지션만 가지면 통과한다(「빈 목록 = 배타적」은 거짓) ⑵ probe↔청산 **경쟁**에는 fail-closed 가 아니다 ⑶ `scan_resting_conditionals` 가 Repository 밖에서 DB 를 읽는다(AGENTS.md §3). 근본 해결은 거래소 계정 분리                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 미도래 — 가드가 열린 관측 없음                                                                                  | M (2-3h)        | 2026-08-15 soak-survival                                     |
| [BL-721](#bl-721) | ✅ **게이트 2단 분할 — Resolved (2026-08-14 gate-2stage)** — 전량 1회 **15~20분**의 대부분을 여섯이 먹고 **CI 가 같은 것을 이미 샤딩해서 돈다**(BE pytest **379초**·e2e ~400초 vs 나머지 20종 합계 1분 안쪽). ⇒ `--pre-pr`(유예) → PR push → **CI 와 나란히** `--deferred-only`. ★유예는 면제가 아니다 — 유예 원장 파일 + 다른 종결 문구, `--deferred-only` 통과만이 원장을 지운다. 하네스 `final-gates-test.sh` 신설(8종→**9종**)                                                                                                                                                                                                                                                                                                                                                                        | 도래 — 회고에서 실측                                                                                            | S               | 2026-08-14 gate-surface-close 회고                           |
| [BL-723](#bl-723) | ✅ **Resolved (2026-08-14 gate-pointer-axis)** — **비싼 게이트에만 영역 판정이 없었다.** `BE ruff`·`BE mypy`·`FE vitest`·`FE build`·`e2e chromium` 은 `has_be`/`has_fe` 에 걸려 있는데 **가장 비싼 셋**(`BE pytest` **357초** · `e2e authed` **268초** · `e2e design-canon` **42초**)만 무조건 돌았다. 앱 코드 diff 0 인 회차에서 **11분 10초**를 태웠고 같은 회차에 CI 는 `backend`·`e2e` 잡을 전부 skip 했다 — 로컬이 CI 보다 더 돌면서 잴 것은 없었다. 처방 = `BE pytest`→`has_be` · `design-canon`→`has_fe` · `authed`→`has_fe∥has_be`. 하네스 8→**9 케이스**(⑤⑥① 환경 의존 동반 수리)                                                                                                                                                                                                                | 도래 — 실측이 있고 처방이 우리 손 안에 있다                                                                     | XS              | 2026-08-14 gate-pointer-axis                                 |
| [BL-522](#bl-522) | ★엔진이 체결로 간주한 진입을 라이브가 완결하지 못하면 복구 경로가 없다 (유실 채널 5종)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 실자금 cutover 전 필수                                                                                          | M-L             | 2026-07-28 live-entry-parity                                 |
| [BL-186](#bl-186) | 🟡 부분 Resolved (186a) — Full leverage + funding + mm + liquidation 풀 모델 (잔여 = BL-186b)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Sprint 38+ (BL-185 foundation 위)                                                                               | M-L (16-24h)    | Sprint 37 BL-185 후속                                        |
| [BL-190](#bl-190) | PDF export (jsPDF / Playwright)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 외부 사용자 요청 시                                                                                             | M (3-5h)        | Sprint 41 Worker H 결정                                      |
| [BL-195](#bl-195) | ✅ qb-form-slide-down animation 영구 truncation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Sprint 45 codex G.4                                                                                             | XS (30m)        | Sprint 45 codex G.4 발견                                     |
| [BL-235](#bl-235) | N-dim acquisition surface viz (Bayesian 전용)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Sprint 57+                                                                                                      | M (8-12h)       | ADR-013 §6 #8 deferred                                       |
| [BL-236](#bl-236) | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Sprint 56+                                                                                                      | S (3-5h)        | Sprint 55 deferred                                           |
| [BL-363](#bl-363) | ✅ stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | deepening sprint 또는 5번째 engine 추가 시                                                                      | S (2-3h)        | 2026-05-30 full-inspection §appendix P1-9                    |
| [BL-364](#bl-364) | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | string 카테고리 sweep 요청 시                                                                                   | M (4-6h)        | 2026-05-30 full-inspection §appendix P1-9 (S4 후속)          |
| [BL-366](#bl-366) | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | trading deepening sprint                                                                                        | S-M (3-5h)      | 2026-06-26 trading-deepen-2                                  |
| [BL-368](#bl-368) | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | trading deepening / 4번째 provider                                                                              | S-M (3-5h)      | 2026-06-26 trading-deepen-2                                  |
| [BL-369](#bl-369) | 3 provider `create_order` try/except/finally ~40 LOC 복붙                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | trading deepening sprint                                                                                        | S (2-4h)        | 2026-06-26 trading-deepen-2                                  |
| [BL-372](#bl-372) | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Wave 3 실자금 cutover 전                                                                                        | M (6-10h)       | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)           |
| [BL-373](#bl-373) | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | BL-365 standalone-trigger 발주 시                                                                               | S-M (3-5h)      | 2026-06-28 grilling (트레일링 후속 scope)                    |
| [BL-375](#bl-375) | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Wave 3 실자금 cutover 전                                                                                        | S-M (3-5h)      | 2026-06-29 BL-372 same-side stale G1 codex                   |
| [BL-379](#bl-379) | pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐, latent harm-class)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | pine_v2 robustness 후속                                                                                         | M (4-6h)        | 2026-06-30 QA codex G2 + 직접 재현                           |
| [BL-380](#bl-380) | Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반) + VirtualRunResult.warnings 미전파                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Track A 신뢰 표면 sprint                                                                                        | S-M (3-5h)      | 2026-06-30 QA LuxAlgo 0-trade                                |
| [BL-381](#bl-381) | Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허 (i2_luxalgo 검증 vacuous)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Trust Layer CI 강화                                                                                             | S (2-4h)        | 2026-06-30 QA codex G2/diff                                  |
| [BL-382](#bl-382) | qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성, mdd_exceeds_capital 은 표시됨)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | sizing 투명성 sprint                                                                                            | S (2-4h)        | 2026-06-30 QA F1 (codex G2)                                  |
| [BL-387](#bl-387) | backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 횡단 (key drift 시 silent 잘못된 sizing, money-path)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | backtest deepening 또는 sizing 로직 변경 시                                                                     | S-M (3-5h)      | 2026-06-30 backtest-deepen (codex 최강 후보)                 |
| [BL-392](#bl-392) | ✅ stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass↔serializer↔OutSchema, untyped JSONB seam)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | stress_test deepening 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시                                  | M (4-6h)        | 2026-06-30 stress_test-deepen (deepen-modules 1차)           |
| [BL-523](#bl-523) | 조건부·전환 진입에 TP/SL 브래킷이 붙지 않는다 (현재 코퍼스 미발현 — `stop=`+`strategy.exit` 동시 사용 시 발현)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 실자금 cutover 전                                                                                               | M               | 2026-07-28 live-entry-parity                                 |
| [BL-524](#bl-524) | `strategy.entry(limit=...)` 이 조용히 버려지고 시장가 진입으로 대체된다 (TV 충실도)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | limit 진입 전략 지원 시                                                                                         | M               | 2026-07-28 live-entry-parity                                 |
| [BL-527](#bl-527) | ★`trade_id` 재사용 + catch-up 다중 emit 이 `pnl_by_trade` 를 덮어써 기대치를 오염시킬 수 있다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 기대치 정확도가 판정에 쓰이기 전                                                                                | S               | 2026-07-28 live-outcome-parity                               |
| [BL-528](#bl-528) | 세션 창 밖 늦은 체결이 어느 표면에도 안 잡힌다 (실측 확정 청산 4건 · net −0.5463)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 세션 손익 완결성이 필요할 때                                                                                    | M               | 2026-07-28 live-outcome-parity                               |
| [BL-529](#bl-529) | 🟡 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 전략 누적 지표를 신뢰해야 할 때                                                                                 | S               | 2026-07-28 live-outcome-parity                               |
| [BL-531](#bl-531) | parity 표면의 `ParitySummary` -> `OutcomeParityScope` 평탄화가 shotgun surgery (지표 1개 추가 = 5파일 편집)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | parity 지표를 더 붙일 때                                                                                        | S               | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-532](#bl-532) | `_sum_decimals` 사본이 `PARITY_DECIMAL_CONTEXT` 밖에서 돈다 (본 레포가 방금 세운 규칙과 불일치)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 다음 parity 손질 시                                                                                             | XS              | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-533](#bl-533) | ✅ **Resolved (2026-08-09, W3)** — 종료 세션 목록이 같은 엔드포인트를 두 쿼리 키로 조회해 미러 state 를 낳는다. ★**키 통일은 [BL-423] 때 이미 끝나 있었다** — 남은 일은 미러 `selectedInactiveSession` 제거뿐(참조 4→0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 코크핏 손질 시                                                                                                  | XS              | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-534](#bl-534) | 외부 오라클 테스트가 27 leg Decimal 합산을 실제로 실행하지 않는다 (총계를 관측 1건에 몰아넣음)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | parity 산술을 손댈 때                                                                                           | XS              | 2026-07-29 PR #496 코드리뷰                                  |
| [BL-538](#bl-538) | 발산 알림 본문이 모든 카테고리에 "전략 수정 후 재활성화" 라고 처방한다 (포지션 불일치엔 틀린 처방)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 운영 알림을 사람이 신뢰해야 할 때                                                                               | S               | 2026-07-29 PR #497 사후 리뷰                                 |
| [BL-541](#bl-541) | 세션 행이 아예 없는 포지션(웹훅 경로·거래소 수동)은 여전히 앱에서 못 닫는다 — ★아직 실측된 적 없음                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | `no_owning_session` 이 실제로 관측될 때                                                                         | M               | 2026-07-29 live-orphan-close                                 |
| [BL-545](#bl-545) | ★gap-resync 게이트가 5% 수량 허용치를 물려받아 구 게이트가 막던 불일치를 통과시킨다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 조건부 진입을 실자금으로 가기 전                                                                                | S               | 2026-07-30 conditional-entry-alignment                       |
| [BL-546](#bl-546) | 원장→엔진 seed 경계에서 `Decimal` 이 `float` 로 강등 (Decimal-first 하드 규칙)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 엔진 수치 표현을 손댈 때 / 큰 notional                                                                          | M               | 2026-07-30 conditional-entry-alignment                       |
| [BL-547](#bl-547) | ★원장 seed 가 그 tick 한 번만 산다 — 조용한 고아 가능 (**아직 실측된 적 없음**)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | `exchange_only` 이 실제로 오르는 것이 관측될 때                                                                 | M               | 2026-07-30 conditional-entry-alignment                       |
| [BL-553](#bl-553) | ★`outcome="applied"`(원장 seed 주입)가 실주행에서 한 번도 안 밟혔다 — 단위테스트로만 증명                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 다음 soak (기회주의적 확인)                                                                                     | XS              | 2026-07-30 conditional-entry-alignment                       |
| [BL-556](#bl-556) | ✅ **`final-gates.sh` §4 에 `e2e chromium` 추가** — ★이것만 영역 판정(`has_fe`)에 건다(BE·DB·인증·소크 무결합). 3분기 전부 같은 3행, 6조합 전수 검증. ★★**4건이 아니라 3건**(`--list` 실측, 문서 5곳 오기). ★`FE build` fail-open 도 같이 닫았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 다음 회차 게이트 실행 전                                                                                        | XS              | 2026-07-30 live-entry-completeness                           |
| [BL-558](#bl-558) | retCode 를 `error_message` 에 싣는 경로가 **동기 1곳뿐** — 비동기 확정 거절이 코드 미상이 된다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 거절 코드로 채널을 가를 때                                                                                      | M               | 2026-07-30 live-entry-completeness                           |
| [BL-565](#bl-565) | `check_exit_fills` 의 close 도 BL-560 과 같은 성질 — 읽기만 하고 남겼다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | `strategy.exit` 을 쓰는 전략을 라이브로 돌리기 전                                                               | S               | 2026-07-31 reversal-ledger-sync                              |
| [BL-567](#bl-567) | `place_trailing_stop` enqueue 가 실패하면 그 주문의 트레일링은 **영구 유실** — 회수 경로가 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 트레일링 전략을 라이브로 상시 운용하기 전                                                                       | —               | 2026-07-31 reversal-ledger-sync                              |
| [BL-568](#bl-568) | BL-562 체결시점 반전 계측이 **11건 중 10건 무측정** — 분류된 건이 0 이다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 그 분포를 근거로 무언가를 판단하기 전                                                                           | S               | 2026-08-01 ledgerhygiene                                     |
| [BL-574](#bl-574) | ★`LIMIT 100` 이 세션 필터보다 앞서 걸려 현 세션 resting 을 놓치고 `awaiting_trigger` 를 `unexplained` 로 오분류 (측정 완료 · 수리 보류 — 동시 최대 2 / 100)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 동시 resting 이 20건을 넘긴 날이 관측될 때                                                                      | S               | 2026-08-01 soak codex                                        |
| [BL-575](#bl-575) | SELECT 실패 후 같은 AsyncSession 을 rollback 없이 재사용 — fail-open 계약이 깨진다 (★선재 패턴, 회귀 아님)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | fail-open 을 근거로 쓰기 전                                                                                     | S               | 2026-08-01 soak codex                                        |
| [BL-580](#bl-580) | 계측 가드 잔여 **96곳** (누적 63곳 수리). ★산문 근거 29곳이 주입에서 **29곳 전건 유해** — 「가드 없이 유지」 누적 0곳. ★2026-08-03 신규 **H8** = 계측 실패가 fail-open `except` 에 삼켜져 **거절을 집행으로 뒤집는다**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | `qb_metrics_mutation_failed_total` 창 차분이 0 을 벗어날 때 (★프록시다 — 가드 밖은 이 counter 를 올리지 않는다) | M               | 2026-08-02 metric-guard-parity                               |
| [BL-591](#bl-591) | ★**뿌리** — 엔진 포지션의 SSOT 가 없다. `run_live` 시뮬이 매 tick 봉을 재생해 포지션을 **도출**하고 정상 운행 중엔 현실로 **보정되지 않는다**. 슬라이스 1(계측) = **PR #539 OPEN**(통합 브랜치 `stage/engine-position-ssot`, 미머지). ★★★**슬라이스 2 미착수 확정** — 사전등록 V1 발동(④ = 0: 사망 2건의 상류에 `exchange_only` 0건 · 최악 상계 ≤1/21). ★★★**유도 함수 재설계 필요** — `trade_id` 는 trade 가 아니라 Pine 진입 규칙 이름이고(`PivRevSE` 56체결/19세션) 반전은 `:close:` 키를 안 만든다 ⇒ 판정 불가 **27.6%**(전량 `duplicate_open`) · **net 은 맞고 legs 는 틀리다**(오라클 11건: 오답 0 · 적중 4 중 3건이 `legs=2` 인데 거래소는 단일 포지션 — 나머지 1건은 반전 없는 먼지 세션이라 정확) ★**2026-08-05 P1→P2 강등**(잔여 = D1/D2 · 근거는 §상태 줄)                                     | 발산 증상 BL 을 또 하나 열기 전에 · 소크가 또 죽었을 때                                                         | L               | 2026-08-03 breach-rejection-recovery                         |
| [BL-592](#bl-592) | 같은 Bybit 데모 계정이 `trading.exchange_accounts` 에 **2행**이라 청산 1건이 **2행으로 적재**되고, 주문을 안 가진 계정 쪽에서는 `ours` 가 **`unknown` 으로 오라벨**된다(실측 91/91 대칭). 원장 구멍 계측을 **3.7배 부풀린다** — [BL-591] 슬라이스 1 관측 전에 인지 필요                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | `exchange_exits` 로 원장 구멍·귀속을 판정하기 전에                                                              | S               | 2026-08-04 engine-position-ssot                              |
| [BL-593](#bl-593) | 운영자 도구(`apps/api/scripts/verify_*.py` 등)가 `ClosePositionService` 를 못 써서 provider 를 **직접 호출** → 그 청산에 대응하는 `trading.orders` 행이 **없다**. 실측 `external_manual` **12건 / 103건(11.7%)**. [BL-591] C 안이 원장을 진실로 쓰므로 이 구멍이 곧 오주입 위험                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 소크를 끄거나 거래소를 손으로 flat 으로 만들기 전에                                                             | S               | 2026-08-04 engine-position-ssot                              |
| [BL-598](#bl-598) | ★**코퍼스 스크립트를 처음 파싱하는 테스트가 비용을 전부 문다** — `test_ast_classifier[i3_drfx]` 단독 **42.66s** vs 전체 스위트 안 **4.58s**. 프로세스 전역 비용이라 **쪼개면 샤드마다 중복**된다(CI 3샤드 합 1796s vs 단일 1278s, +519s 전부가 이 중복). 샤딩 저항의 뿌리이고 CI 14분 벽의 원인. ★**2026-08-08 정체 확정** — ANTLR ALL(\*) DFA 캐시가 **파싱에 의해** 지연 구축되는 것(import 아님·크기 법칙 아님). 같은 프로세스·같은 입력에서 DFA 만 비우면 3.63s→**49.61s** 로 되돌아온다(인과 대조). ⇒ ② 는 **테스트 디스크 캐시로 닫힌다 — `apps/api/src` 0줄**. 도구 = `apps/api/scripts/profile_corpus_parse.py`. ★**규모 대조는 미대조** — ① 은 로컬 9프로세스(+52.89s)이고 CI 3샤드(+519s)와 **직접 대조되지 않았다**(약 10배 차) ⇒ 「+519s 전부가 이 중복」은 여전히 **미검증 가정**이다        | CI backend 를 14분 아래로 내리려 할 때 · pine_v2 코퍼스 테스트를 늘리기 전에                                    | M               | 2026-08-06 ci-diet                                           |
| [BL-603](#bl-603) | ✅ 백테스트 비용 가정이 라이브 실효의 **2.7배** — 가정 왕복 0.30%(fees 0.1+slip 0.05/leg) vs 원장 실측 왕복 **0.1101%**(taker 0.055%/leg 단일 성분, 84 event 중 77 이 8자리 일치·비-taker 잔차 0.03%). 매칭쌍 진입가 잔차 중앙 0.014% vs slippage 가정 0.05%. **2026-08-07 Resolved** — 0.00055/0.00014(두 SSOT+FE 미러 4곳), 왕복 0.138%. 코퍼스 `num_trades` 불변·`s3_rsid` 부호 반전                                                                                                                                                                                                                                                                                                                                                                                                                   | 백테스트 손익을 라이브 예측치로 읽기 전 (비용 축이 3배 비관)                                                    | S               | 2026-08-06 backtest-reality-gap                              |
| [BL-605](#bl-605) | ✅ **스윕 계정 루프 `exchange_uid` dedup** — `exchange_exits` 가 같은 청산 event 를 **정확히 2행**으로 적재하던 뿌리는 같은 실제 계정을 가리키는 계정 **행**이 2개라 같은 창을 두 번 조회한 것이었다. 2026-08-09 수리 · 수리 전 red 실증 · 하네스의 UNIQUE 축(`(exchange_account_id, row_hash)`) 도 함께 정정                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | exchange_exits 를 집계로 소비하는 코드를 추가하기 전                                                            | S               | 2026-08-06 backtest-reality-gap (eval2 실측)                 |
| [BL-610](#bl-610) | ✅ 코드·테스트·설정 **10곳**이 삭제된 문서 경로를 가리킨다. 2026-08-08 수리 — 사용자 표면 2곳은 **참조 제거**(`git:<sha>` 좌표는 사용자에게 쓸모없다), 개발자 8곳은 **tombstone**. ★삭제 커밋이 **둘**이라 sha 도 둘(heikinashi ADR 4곳 = `590eeec9` · 나머지 `0ddf2b53`) · 종전 재검출 명령은 `-n` 누락으로 **전건 오탐**했다                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | BL-003 소크 창 종료 후 첫 apps/api/src 정리 회차                                                                | XS              | 2026-08-06 docs-overhaul (fix-doc)                           |
| [BL-611](#bl-611) | ✅ ★**메타-방법론 영구 규칙이 자동 로드에서 빠졌다** — 구 `.ai/common/global.md` §7 은 `paths` 없는 `.claude/rules/global.md` 로 **매 세션 무조건** 들어왔다(2026-08-07 실측 재현). ADR-026 이 이를 `generator-evaluator-pipeline.md` §8 로 옮기면서 **열어야만 읽히는** 문서가 됐다 — kickoff preflight(§8.1)·codex finding 코드 대조(§8.3)가 조용히 누락될 수 있다. **Resolved** — `AGENTS.md` 에 §8.1/§8.3 두 줄 인라인                                                                                                                                                                                                                                                                                                                                                                                | 다음 Sprint kickoff (Type A/B) 전                                                                               | S               | 2026-08-07 docs-overhaul 리뷰                                |
| [BL-625](#bl-625) | ★**플레이스홀더 시크릿이 development 에서는 아무 게이트에도 안 걸린다** — 서버 `apps/api/.env.local` 이 `CLERK_SECRET_KEY=sk_test_...`(문자 그대로)인데 API 는 정상 기동하고 `/health` 200 을 냈다. 호스트 uvicorn 이 인증 경로를 한 번도 안 밟아서 드러나지 않았고, 브라우저 첫 로그인 요청이 **전건 401** 로 터지고서야 보였다. `_enforce_production_safety` 가 이 계열을 알지만 **`app_env == production` 일 때만** 검사한다. ★2차: 루트 `.env` 인라인 주석(`# [필수 …]`)을 안 떼고 값을 옮기면 한글이 섞여 401 이 아니라 **500**(clerk SDK 헤더 ascii 인코딩)                                                                                                                                                                                                                                         | 새 호스트에 API 를 세울 때 · [BL-071] 발동 시                                                                   | S               | 2026-08-07 fe-oracle-deploy                                  |
| [BL-632](#bl-632) | 골든을 오라클로 승격했지만 그 기대값은 **엔진 자신의 출력**이다(회귀 감지기이지 정확성 오라클이 아니다). ★반순환 근거가 이 축을 안 덮는다 — 손계산 오라클 `test_golden_oracle_ema_sltp.py` 는 4봉·고정 stop/limit 이라 **`ta.atr` 를 한 번도 안 탄다**. ⇒ [BL-621] 의 낡음을 만든 바로 그 축이 **구조적으로 오라클 밖**이다. BL-621 본문의 「틀린 값을 정본으로 고정하게 된다」 경고에 아직 답하지 않았다                                                                                                                                                                                                                                                                                                                                                                                                 | 골든 값이 또 어긋났을 때 · 백테스트 정확성을 대외 주장해야 할 때                                                | M               | 2026-08-07 backtest-fidelity                                 |
| [BL-631](#bl-631) | ✅ **소유자 없던 검사기 2종에 `docs-audit.sh` 를 붙였다** — ★★그전까지 **`runtime-check.mjs` 는 어느 게이트에도 안 붙어 죽은 채로 방치됐다** — `docs/` 재편 커밋 `fcc36bf7` 이후 playwright import 상대깊이가 안 따라와 `ERR_MODULE_NOT_FOUND` 로 즉사했고, 그래서 핸드오프 §8.5 의 **「다크 17벌 17/17 PASS」는 그 커밋 이후 한 번도 재현된 적 없는 숫자**였다(이번 회차가 고쳐 재현). 뿌리는 경로가 아니라 **소유자 부재** — `pnpm test`·CI·`docs-audit` 어디도 안 부른다                                                                                                                                                                                                                                                                                                                               | 다음에 `docs/` 를 재편하거나 프로토타입을 손대기 **전에**                                                       | S               | 2026-08-07 backtest-fidelity                                 |
| [BL-624](#bl-624) | ★**게이트의 HTTP 갈래는 `PROMETHEUS_BEARER_TOKEN` 과 양립 불가** — `soak-gate.sh` 의 `curl -sf` 가 인증 헤더를 안 보내서 401 → `DARKNESS=null` → **C5⑷ 영구 ✗**. `APP_ENV=production` 과 무관하다(토큰이 있으면 development 에서도 강제). 2026-08-07 FE 배포 회차가 실측으로 물렸다 — 서버 체크아웃이 [BL-620] 이전이라 기본이 HTTP 였고 베어러를 켜자 즉시 C5 가 죽었다. ★판별자는 API 로그의 `GET /metrics` 유무다 — 게이트 출력의 `darkness_computed=✓` 는 **어느 경로로 성공했는지 말해주지 않는다**. 지금은 기본이 직독이라 미발동                                                                                                                                                                                                                                                                   | `QB_METRICS_URL`(원격 데몬 + ssh 터널 운영안)을 실제로 쓰려 할 때                                               | S               | 2026-08-07 fe-oracle-deploy                                  |
| [BL-620](#bl-620) | ✅ **소크 스택에 `/metrics` 를 내주는 것이 없어 게이트 C5 가 영구 ✗ 였다** — `soak-stack.sh up` 은 API 컨테이너를 안 띄우고 `:8100` 리스너가 0개라 **C1/C2 를 다 채워도 PASS 불가**였다. **Resolved** — 기본 취득을 HTTP → `apps/api/.metrics` **직독**으로 교체(워커가 같은 counter 를 거기 쓴다). ★PR #556 리뷰 후속: curl 갈래에도 `[ -n ]` 를 걸어 **`200 + 빈 본문` fail-open** 을 닫았고(초판은 직독 갈래에만 있었다), `QB_METRICS_DIR` 을 `.env.example` 에 등재했다(Golden Rule). 판정 `측정불가`→`진행중`, C5 전건 ✓. fail-closed 음성 대조 **3/3**. `QB_METRICS_URL` 명시 시 종전 HTTP 유지                                                                                                                                                                                                     | —                                                                                                               | S               | 2026-08-07 gap-resync-autopsy                                |
| [BL-636](#bl-636) | backlog 인덱스 표 파손 + `bl-audit.sh` 가 표 파손을 감지하지 못 한다 — 수리 전 P1 조각 1행과 P2 조각 13행은 GFM 표로 렌더되지 않았고, 이번 회차에 빈 줄 제거·재결합으로 104행을 보존했지만 검사 축은 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 다음 백로그 인덱스를 편집할 때                                                                                  | S               | 2026-08-08 bl003-unblock                                     |
| [BL-637](#bl-637) | ✅ **`bl-audit.sh` 에 우선순위 배치 검사 축을 세웠다** — 수리 전 불일치 40건(뿌리는 P3 H2 아래에 인덱스 표가 아예 없어 새 P3 항목이 P2 표 꼬리에 붙은 것)을 제자리로 옮기고, 인덱스 행이 섹션 `**Priority:**` 와 같은 H2 표에 있는지를 4번째 축으로 검사한다. 주입 시험 2/2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 다음 백로그 인덱스를 편집할 때                                                                                  | S               | 2026-08-08 bl003-unblock                                     |
| [BL-639](#bl-639) | 🟡 미조인 `exchange_exits` 상시 기저율 — 배타성 판단은 과거 이력이 아니라 미체결 조건부 주문을 대상으로 해야 한다. **2026-08-08 판정식·판별력 확정**: `EXCLUSIVE ⟺ ∀ resting conditional(`reduce_only=None`) : `order_link_id ∈ {Order.id}`(`live_session_admin.py:206-256`에 이미 있다), 정상 상황 실측`FOREIGN_RESTING=0`·**오탐 0**. ★「판별력 0·34행 전량」은 계정 스코프 없이 센 값이라 **틀렸다**(좁히면 287 중 25 = 8.7%) — 결론은 유지, 근거 교체. 남은 것 = 소유권 집합의 계정 축(BL-634 소관)                                                                                                                                                                                                                                                                                                   | BL-634 를 구현하기 전                                                                                           | S               | 2026-08-08 bl003-unblock → 2026-08-08 soak-attribution-close |
| [BL-642](#bl-642) | ✅ `soak-observe.sh` 가 게이트와 **같은 취득 경로**를 쓴다 — 기본 `.metrics` 직독, `QB_METRICS_URL` 명시 시 HTTP(`0f7f9342`). 5경로 격리 검증 5/5, 음성 대조 rc=7. 취득과 series 필터를 분리해 「매치 0건」이 「스크레이프 실패」로 읽히던 인접 fail-open 도 닫았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | — (해결됨. 서버 실행 검증은 다음 재기동 ⑺)                                                                      | XS              | 2026-08-08 bl003-unblock                                     |
| [BL-643](#bl-643) | ✅ `docs/status.md` 진입점의 최신성을 `docs-audit.sh` 가 집행한다 — 술어 2개(⓪ 표 행수 **≥3** · 살아 있는 **`다음 행동 =`** ≤1). ★★낱말이 아니라 **구문**을 재서 오탐 0(설명 문장은 `=` 가 없다) ★★★**파일 전체로 센다** — 실제 사고 2건은 서로 다른 섹션에 하나씩이라 「블록당 1개」로는 통과했다. 변이 **6/6**, 음성 대조 `ce583eef^` 2건 검출. 한계 = 모순 탐지기이지 낡음 탐지기가 아니다                                                                                                                                                                                                                                                                                                                                                                                                             | — (해결됨. 게이트가 매 실행 집행)                                                                               | S               | 2026-08-08 bl003-unblock                                     |
| [BL-650](#bl-650) | ★**Turbopack 영속 캐시(`.next/dev`)가 무한 성장하고 낡은 산출물을 계속 준다** — 1.99GB 까지 자란 상태에서 `next dev` 가 **요청 0건·클라이언트 0개**로 **417% CPU / 1000MB** 를 상시 소모했고(치우면 **0.1%** / 374MB) fork 고갈로 셸·playwright·머신을 함께 죽였다. 또 변이한 CSS 가 **서버 완전 재기동을 넘어** 낡은 채로 서빙돼 음성 대조를 거짓 통과시켰다 — `rm -rf .next` 로만 풀린다. 🟡 2026-08-08: 낡은 디렉터리 **5벌 8.5GB** 삭제(26G→18G) + `mise run fe` 1GB 경고. ★★**재현 실패가 결과다**(593MB 에서 idle **0.1%**) · **`turbopackMemoryLimit` 은 존재하지 않는다** ⇒ 원안 ① 폐기                                                                                                                                                                                                           | dev 서버가 느려지거나 CSS 변경이 안 먹을 때 · 캐시 상한/청소 정책을 정할 때                                     | S               | 2026-08-08 fe-canon-and-responsive                           |
| [BL-651](#bl-651) | ✅ **거래소 조회 루프 `exchange_uid` dedup** — 중복 계정 행이 배타성 판정식의 **개수**를 2배로 부풀린다 — 실측 `RESTING_CONDITIONAL=2` 인데 실제 조건부 주문은 **1건**(같은 `link=dd58ef44` 가 두 계정으로 계상), 포지션도 2행. `EXCLUSIVE`(존재 판정)는 배수에 불변이라 지금 깨지는 것은 없고, **개수를 문턱으로 쓰는 순간** 틀린다. BL-605 처방(스윕 루프)은 **이 자리를 안 고친다** — 여기는 거래소 조회 루프다                                                                                                                                                                                                                                                                                                                                                                                        | BL-634 가드가 resting 개수를 문턱으로 쓰기 전                                                                   | S               | 2026-08-08 soak-attribution-close                            |
| [BL-653](#bl-653) | ✅ **게이트가 자기 해상도를 자백한다 (처방 ⑶ — 판정 불변)**. ①(표본 기반) 정체에 `lag N분 (표본 간격 중앙 …/최대 … · 크기 N배[, 구분 불가])` 병기 · 실격 0건 실행도 `표본 해상도:` 한 줄 ⇒ **「C3 실격 0」을 「정지 없음」으로 못 읽는다**. ★「구분 불가」 = 크기 < 표본 최대 간격 × 2(정체를 가로지르는 표본이 둘도 안 되면 크기는 하한일 뿐). ★★**②(종단 lag)에는 붙이지 않는다** — `deactivated_at`×`last_evaluated_bar_time` 둘 다 DB 값이라 표본에 의존하지 않는다. 아무 데나 붙이면 정확한 값을 깎아 표시가 무의미해진다. 변이 3/3 red(문턱 0.0/1e9/주석 no-op) · 실측 재현(간격 31.0분 → 크기 1.1배 구분 불가) · N 판정 비트 diff 공집합                                                                                                                                                           | BL-619 재관측 시 / 게이트 실격 판정을 신뢰해야 할 때                                                            | S               | 2026-08-08 soak-mortality-repair                             |
| [BL-654](#bl-654) | 증거금 게이트가 **진입 비용을 안 본다** — `_can_afford_entry` 와 `_open_trade` 최종 검증 둘 다 초기 증거금만 비교하고 **바로 아래에서 차감하는 진입 leg 비용**을 빼지 않는다. 고레버리지에서 갈린다: 자본 $1,000 · 125x · 비용률 0.069% · 명목 $118,750 은 증거금 $950 으로 **통과**하는데 진입 수수료 $81.94 후 `gate_equity` 가 **$918.06 < 950** 이라 유지 증거금을 못 댄다. [BL-460] 이 고친 것은 gross/net 축이고 **이 축은 선재**다                                                                                                                                                                                                                                                                                                                                                                 | 고레버리지 백테스트를 신뢰해야 할 때 / [BL-466] 후속                                                            | S               | 2026-08-08 soak-mortality-repair (codex challenge P1)        |
| [BL-655](#bl-655) | `dedupe_accounts_by_exchange_uid` 는 **쓰기 가능한 형제 행이 둘이면** 주문을 누락한다 — 스윕이 대표 `account.id` 로만 매칭·backfill 하므로(`trading.py:1949`·`:1987`·`:2027`) 버려진 형제에 달린 주문의 청산이 `unknown` 이 되고 `realized_pnl` 이 미동기화된다. ★**현재 데이터에선 발화하지 않는다** — 실측 형제 2행 중 하나가 `read_only=t` 라 대표 선택 규칙 ⑵ 가 쓰기 가능한 행을 고른다. 막는 **DB 제약이 없다**는 것이 위험의 실체다                                                                                                                                                                                                                                                                                                                                                                | 같은 `exchange_uid` 에 쓰기 가능한 행이 2개 생기면 / 실자금 전환 전                                             | S               | 2026-08-08 soak-mortality-repair (codex challenge P2)        |
| [BL-656](#bl-656) | ✅ **⓿ 가 `soak-stack.sh ps`(신설, DB 무접촉)로 갈래를 고른다** — 완전 down 이면 **조회보다 먼저** `pin → up` + ⑷·덤프 건너뛰기. red→green: 같은 가짜 트리에서 `rc=2`·스택 호출 **0건** → `rc=0`·**`ps pin up`**. ★★★⓿ 를 ⑴ 앞에 뒀다가 red 에 잡혔다 — 거기선 원장 조회가 먼저 죽어 손으로 `--strategy-id` 를 줘야 한다(= 없애려던 손 절차). ★★★**결함 ①은 회귀해 있었다** — 「정적 카운트 0건으로 동결」이라 적었지만 **그 카운트를 도는 게이트가 없었다.** 신설 `soak-restart-test.sh`(14 단언 · 오라클 = 호출 순서)를 `final-gates.sh` 에 붙였다. 변이 4/4                                                                                                                                                                                                                                            | 다음 소크 재기동 시                                                                                             | S               | 2026-08-08 soak-mortality-repair (P7)                        |
| [BL-657](#bl-657) | ✅ **게이트가 어느 DB 를 봤는지 헤더 한 줄로 찍는다** — `대상: <컨테이너> <host:port>/<dbname> · docker <endpoint> · 실행 <hostname> · 분류기 <host:port/db>`. ★★**BL 본문의 「`DATABASE_URL` 을 따라간다」는 C1~C5 에 대해 거짓** — `_q()` 는 `docker exec ${DB_CONTAINER} psql` 이라 갈리는 축은 **docker 데몬+컨테이너**다. `DATABASE_URL` 은 분류기 전용이지만 `unverified_hours` 로 C1 을 깎으므로 함께 찍는다(한쪽만 찍으면 새 fail-open — 실측으로 이 워크트리는 둘이 어긋난다). 변이 2/2 헤더 추종 · 음성 대조 판정 비트 전건 불변(벽시계만 차이) · 비밀번호 누출 0                                                                                                                                                                                                                               | 다음 게이트 실행 시 / 게이트 숫자를 인용하기 전                                                                 | S               | 2026-08-08 session-handoff                                   |
| [BL-707](#bl-707) | ✅ **authed e2e 오지목 — Resolved (2026-08-14 gate-surface-close)**. ★**처방의 기전이 착수 전 반증** — `NEXT_PUBLIC_API_URL` 은 dev 프로세스에만 주입되고 `playwright.config.ts` 에 dotenv 가 없어 e2e 는 못 받으며 fallback `:8000` 은 **그때 살아 있었다**. 표면도 절반(단정문 **7개** · 도달 test ≤6 vs red **12** · `cockpit.spec.ts:16,38` 은 BE 죽으면 **green**). 채택 = 기존 `subresourceFail` **단언화** + `EXPECTED_CONSOLE` 의 **`/net::err_/i` 제거**(침묵의 진짜 출처) + `setup-authed-reachability` 전량 abort + `probeCount > 0`(§8.6). 실측 = **양성** BE 내림 → 1건 red · **83건 abort**(16s, 문구가 `mise run seed` 를 말하지 않는다) · **음성** 짝 맞춤 → **86 passed**, 신규 단언 **무발화**. ★부수 2건: `:3102` 도 남의 앱 · `FRONTEND_URL` 불일치 시 **CORS** 가 같은 증상을 만든다 | authed e2e 를 다시 손댈 때 / 같은 오진이 재발할 때                                                              | S               | 2026-08-12 surface-demo-pack                                 |
| [BL-708](#bl-708) | ✅ **비결정 원천은 반올림이 아니라 원격 폰트 404 였다** — 지목한 것은 처방이 아니라 **계측**(`NavProbe.subresourceFail`)이다. 계측 전 3회는 19벌 출력이 status/examined/canon 까지 **전건 동일**이라 갈리는 축이 0이었다. 처방 = 「**file:// 대상만 hermetic**」 — 커밋된 정적 산출물일 때만 비-file 요청을 goto 전에 빈 200 으로 봉인하고 봉인량을 `sealed` 로 싣는다(`subresourceFail=0` 을 「네트워크 멀쩡」으로 오독 금지). 판정 계약은 spec 상단 명문화 + `assertCalibrationContract()` 1곳 통합 + **도달 증거**(4폭 status=200 · minExamined>0 · subresourceFail=0 · sealed>0) 동반 단언 — 변이 `widths:[1440,375]` 에서 종전 계약은 **초록**이고 새 단언만 red. 독립 3회 rc=0/0/0 · `22 passed`×3 · 출력 전문 동일 · 최저 대비 4.92/5.41/5.44 고정. ⑵ WARN 강등 **기각**(여유 0.42 < 밴드 ±0.5)    | — (해결됨. 봉인은 http 대상의 코드 경로를 안 지난다)                                                            | S               | 2026-08-12 surface-demo-pack                                 |
| [BL-714](#bl-714) | ✅ **마감 게이트 브랜치 전제 — Resolved (2026-08-14 gate-surface-close)**. ★**원장 처방 2·3 을 착수 전 기각했다** — `--range` 는 압수 A1 의 **유일한 증인**(하네스 케이스 ⑫ · 변이 `M1=⑫` 정확 집합 일치)을 죽이고, `range:` 첫 줄은 squash 머지라 제3자 검증 불가. 채택 = **`final-gates.sh` 입구 거부**(`merge-base == HEAD` → 게이트 체인 진입 전 거부, `--run eod` 와 문형 동일 · `origin/main` 부재 시 비발화). A1 로직 **불변**, `WHY` 에 처방 문장만 추가. 하네스 **26/26** · 변이 **15종**(㉖ 을 지킬 **M12** 신설 — 그 전까지 자기 변이가 없는 케이스였다) · 문서 = `gates-and-traps.md` 「신호 4종」 절 신설                                                                                                                                                                                    | 마감 절차를 다시 쓸 때 / 같은 상태에 또 빠질 때                                                                 | XS-S            | 2026-08-12 surface-demo-pack                                 |
| [BL-717](#bl-717) | ✅ **API 계약축 PoC — Resolved** (2026-08-13 contract-poc, [ADR-031]). 결정적 export `contracts/openapi/openapi.json`(2회 sha 동일·`--check` 양음성 실증) + 후보 판정 = **orval(client:'zod') 채택**(zod v4 직출력·tsc strict·수기와 공존 vitest 3/3). hey-api 는 자체 TS7 의존 크래시로 실행 불가 탈락. ★구조 diff 핵심 = **datetime 엄격도 역전**(계약 Z-only vs 수기 offset 허용 — BE 실직렬화 실측 전 런타임 투입 금지). 번들 3endpoint 2.9KB gz. CI 배선·전면 전환은 [ADR-031] §비결정                                                                                                                                                                                                                                                                                                               | PR-1(ADR-029 재배치) 머지 후                                                                                    | M               | 2026-08-13 monorepo-realign                                  |
| [BL-742](#bl-742) | ⏳ 반전·순포지션 가정 **163곳/12파일** 전수 감사([ADR-032] §대가). ★긴급도 하락 — 2026-08-15 A1 이 「반전은 소크 사망 원인이 **아니다**」를 보였다(서버=계정 배타성, 로컬=맥 sleep). **예방 축**이다. ★감사(읽기)와 수리(쓰기)를 나눠라 — 수리는 재-pin 을 부른다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 미도래 — 반전이 다시 지목되거나 헤지 재검토 시                                                                  | M (2-3h)        | 2026-08-15 soak-survival                                     |
| [BL-812](#bl-812) | ✅ **[ADR-037] 재입힘 목록 대상 생존 7종에 pytest 최소판 — Resolved (2026-08-21 밤샘 루프 1차)**. 재입힘 **7/7** + 인접 4종. `apps/api/tests/scripts/` 신규 8파일 **0건 → 138 passed + 2 xfailed** (8 lane 워크트리 병렬 · 8/8 completed · retry 0 · 변이 10/10 red · PR #713~#720). ★러너가 남긴 xfail 1건이 **phantom** 이었다(픽스처가 alembic 화살표 의미를 뒤집음 → CONTROL 이 정정, [LESSON-121]). ★진짜 결함 2건은 strict xfail 로 고정 — `soak-restart.sh --help` 범위 드리프트 · [BL-791] shim 내용물 미검증                                                                                                                                                                                                                                                                                     | 도래 — 2026-08-20 실사(`git ls-tree harness-v1`)                                                                | M (8 lane 병렬) | 2026-08-20 하네스 4회차                                      |
| [BL-813](#bl-813) | 🔵 **FE 순수 판정 모듈 테스트 0건 — 인증 경계가 무증거로 산다**. 전이 폐포 실측(2026-08-21) 소스 343 중 **어떤 테스트도 import 하지 않는 것 58**, 그중 판정 로직 5종이 완전 미도달 — `proxy.ts`(공개 라우트·geo L2·세션 완전 검증) · `lib/route-matcher.ts` · `lib/auth.ts`(**geo L3 + 탈퇴 fail-closed** — 둘 다 codex P1/P2 수리인데 재는 테스트가 없다) · `lib/auth-server.ts` · `lib/legal-links.ts`. ★같은 자리에서 이 레포는 이미 「**geo L3 이 한 번도 발화한 적 없었다**」를 밟았다([LESSON-114]). 처방 = 대상 **무변경**으로 테스트 파일 10개 신설, 8 lane 워크트리 병렬(`phases/fe2-*`)                                                                                                                                                                                                         | 도래 — 2026-08-21 전이 폐포 실측                                                                                | M (8 lane 병렬) | 2026-08-21 밤샘 루프 2차                                     |

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
**Trigger:** 실제 dogfood / Beta 사용자가 high-leverage 전략을 운영할 때 (BL-185 spot-equivalent foundation 위). ★**2026-08-18 좌표 수리** — 종전 「Sprint 38+ deferred」는 발화할 수 없는 좌표였고, **진짜 게이트는 아래 「원인 / 영향」에 이미 적혀 있었다**. 위 `**트리거 판정:**` 이 2026-08-11 에 그 사실을 기록했는데 Trigger 줄 자신은 안 고쳐져 있었다
**Est:** M-L (16-24h)
**출처:** Sprint 37 BL-185 spot-equivalent 채택 후 풀 모델 후속

**원인 / 영향:** Sprint 37 BL-185 는 spot-equivalent (1x, 롱/숏) 만 보장. 실제 dogfood / Beta 사용자가 high-leverage strategy 운영 시 funding rate / maintenance margin / liquidation 정확 시뮬레이션 불가.

**권장 접근:** funding/mm/liquidation 정확 시뮬. exchange-specific (Bybit linear funding interval / Binance / OKX) parameter 화. Pine `strategy.entry(leverage=N)` 와 정합.

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

### BL-489

**Title:** 사이징 자본이 D2 구간(진입 창 밖 / 청산 창 안)에서 일시 함몰한다
**Category:** Backend / trading (라이브 사이징)
**Priority:** P2
**Trigger:** BL-488 해소 후 (진입 이벤트 신뢰가 선행 조건)
**Est:** M (설계 선행 필요)
**상태:** 🟡 **부분 해결 — 결함은 살아 있고 원장의 처방이 반증됐다** (2026-08-21 재기술). carry 는 여전히 `bar_time < window_start` 단일 절단이고 2-pass 재실행 흔적이 없다(2026-08-09 status-triage-mass 확인, 2026-08-17 레인 γ 재판정). ★**2026-08-20 하네스 3회차 실사가 권장안 (a) 2-pass 를 반증했다** — `percent_of_equity` 사이징에서 손익이 자본에 비례(P=k·C)하므로 불변식 `C+P=B+L` 은 고정점 `C*=(B+L)/(1+k)` 에서만 성립하고 2패스는 거기 도달하지 못한다(원장의 「레버리지 게이트 활성 시 진동 가능성」은 과소 표현이다). 근거로 든 `KNOWN_LIMITATION` 오라클도 **실재하지 않는다**(`grep -rn KNOWN_LIMITATION apps/api` = 0건). ⇒ **처방이 없는 상태다. 착수하려면 수렴하는 사이징 재계산 설계가 먼저다**
**트리거 판정:** **미도래 (2026-08-21 재판정)** — 종전 판정은 「[BL-488] 해소 후」의 선행이 풀렸다는 것이었고 그것은 지금도 참이다. 그러나 **막는 것이 선행 BL 에서 처방으로 바뀌었다** — 원장이 든 2-pass 가 반증돼 지금 착수하면 반증된 처방을 구현하게 된다. 도래 = 수렴하는 사이징 재계산 설계가 서면으로 정해질 때. ★그래서 `docs/status.md` ⓪ 표에서 내렸다(ACTIVE ∪ (PARTIAL ∧ 도래) 정의를 지킨다)
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

**권장 접근:** 머니-패스의 모든 metric mutation 을 `record_metric_safely` 로 감싸고, 그 규칙을 `apps/api/AGENTS.md` 에 등재한다.
**Risk:** 🟡

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived (BL-050/051/052/053/054/055/056/057/138/139/151/153). ~~**활성 P3 = 8**~~ ★**stale** — 2026-08-08 `bl-audit.sh` 실측 P3 ACTIVE **101**. 이 파일 헤더 규약대로 집계 수치는 여기 박지 말고 스크립트를 돌려라 (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2 + BL-389/390/391 2026-06-30 backtest-deepen). ★2026-08-06 entry-set-divergence 강등 = BL-606/607/608/609.

| ID                | 제목                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Trigger                                                                                                           | Est       | 출처                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------ |
| [BL-801](#bl-801) | 인덱스 표 행의 `#bl-nnn` 앵커가 본문이 사는 파일을 안 가리킨다 — 원장 3분할의 잔여. ★접두사를 붙여 봤고 **줄 길이 상한 초과(985→1,012자)로 되돌렸다**. 선행 = 제목 셀 감축                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 동승 — 인덱스 표 제목 셀을 줄이는 회차                                                                            | M         | 2026-08-18 backlog-triage                              |
| [BL-015](#bl-015) | OKX Private WS                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Bybit Demo 안정화 후                                                                                              | M (6-8h)  | TODO.md L710                                           |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Trust Layer v2 검토 시                                                                                            | M (5-6h)  | TODO.md L23 (skip #16)                                 |
| [BL-745](#bl-745) | ⏳ 텔레그램 봇 토큰이 `curl` **argv** 에 실린다 — 같은 UID 의 다른 프로세스가 `ps`/`/proc` 로 읽을 수 있다. ★**이 회차가 만든 결함이 아니다** — 기존 `_notify:128` 이 처음부터 같은 형태이고 새 알람 유닛이 그것을 따랐을 뿐이라 **두 곳을 함께** 고쳐야 한다. 처방 = `curl --config -` 로 URL 을 stdin 에서 받는다                                                                                                                                                                                                                                                                                                                                                                            | 미도래 — 다중 사용자·CI 로 넓힐 때                                                                                | XS (30분) | 2026-08-15 soak-watch-restore                          |
| [BL-728](#bl-728) | ✅ `classify_exit` 이 Bybit `CreateByLiq` 를 못 잡던 건 — **Resolved** (2026-08-14 `dde53e68`/#631). 부분문자열 판정을 `_LIQUIDATION_CREATE_TYPES` frozenset 으로 교체(같은 파일 `:14-16` 의 기존 3종과 통일). `"adl"` 축은 `_PassThrough` 접미사 때문에 유지. 관측 0건 잠복 해소                                                                                                                                                                                                                                                                                                                                                                                                              | —                                                                                                                 | XS (10분) | 2026-08-14 money-path-attribution                      |
| [BL-722](#bl-722) | ✅ **Resolved (2026-08-14 gate-pointer-axis)** — `assert-main-checkout-test.sh` 신설(케이스 4 + 변이 M1), 게이트 하네스 **9→10종**. ★**처방 2건이 뒤집혔다**: ⑴ 「`--selftest` 가 가장 싸다」 → 호출 자리 2곳(`Makefile` 루프 · `final-gates.sh run_gate`)이 **전부 이름 규약 기반**이라 별도 하네스가 더 싸다 ⑵ 「비 git → rc≠0」 → **코드가 반대**이고 코드가 맞다(`:32-37` 이 판정 불가를 의도적으로 통과 — 차단하면 CI·컨테이너에서 정상 타깃이 전부 죽는다)                                                                                                                                                                                                                               | 도래 — 대상 확정                                                                                                  | XS        | 2026-08-14 gate-2stage                                 |
| [BL-377](#bl-377) | pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | pine_v2 robustness 후속 또는 실자금 cutover 전                                                                    | S (2-4h)  | 2026-06-30 BL-376 G2 codex challenge + G3 fresh review |
| [BL-383](#bl-383) | 🟡 v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | pine_v2 관측성 후속                                                                                               | S (2-3h)  | 2026-06-30 QA codex G2                                 |
| [BL-384](#bl-384) | ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | pine_v2 parity 후속                                                                                               | S (2-3h)  | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-385](#bl-385) | PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse (메타데이터 부정확)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | pine_v2 coverage 후속                                                                                             | XS (1-2h) | 2026-06-30 QA F3                                       |
| [BL-386](#bl-386) | v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject, over-strict)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | pine_v2 coverage 후속                                                                                             | XS (1-2h) | 2026-06-30 QA F4                                       |
| [BL-525](#bl-525) | 라이브가 Track A(indicator + alertcondition) 전략을 어떻게 다루는지 정의되지 않았다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Track A 로 라이브 세션을 열 때                                                                                    | S         | 2026-07-28 live-entry-parity                           |
| [BL-539](#bl-539) | ✅ (P3) 방향 불일치 유예가 시간 경계가 없다 — 평가가 드문드문하면 오래된 strike 가 살아남는다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 발산 가드를 다시 손댈 때                                                                                          | S         | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-540](#bl-540) | (P3) `live_signal.py` 반복 3종 — deactivate 의식 6회 · provider+creds 4회 · category 가 맨 `str`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 이 파일을 다시 크게 손댈 때                                                                                       | M         | 2026-07-29 PR #497 사후 리뷰                           |
| [BL-548](#bl-548) | ✅ **Resolved (2026-08-09, W3)** — (P3) `OutcomeParityPanel` 이 375px 에서 본문 가로 스크롤을 만든다. ★**24px 재현 실패** — [BL-607] 반올림이 그 경로를 이미 닫았다. 남은 경로는 반올림 없는 `sub` 캡션 4곳 — 51자리 Decimal 이 오면 **191px**. 넘치는 것이 표가 아니라 텍스트라 처방은 `break-words`                                                                                                                                                                                                                                                                                                                                                                                          | 모바일 폭 점검 시                                                                                                 | XS        | 2026-07-30 conditional-entry-alignment                 |
| [BL-550](#bl-550) | (P3) 비활성 세션의 **세션별** 포지션 대조가 화면에 없다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 죽은 세션을 세션 단위로 대조해야 할 때                                                                            | S         | 2026-07-30 conditional-entry-alignment                 |
| [BL-551](#bl-551) | ✅ (P3) 라이브 세션 상세 진입이 URL 파라미터가 아니다 — 딥링크·새로고침 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 세션 상세를 링크로 공유해야 할 때                                                                                 | S         | 2026-07-30 conditional-entry-alignment                 |
| [BL-557](#bl-557) | (P3) `qb_active_orders` 게이지가 **음수(-2.0)** 로 표류 — inc 1곳 / dec 약 18곳                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 그 게이지로 무언가를 판단하기 전                                                                                  | S         | 2026-07-30 live-entry-completeness                     |
| [BL-559](#bl-559) | ✅ (P3) 진입 완결성 도구 잔여 3건 — 세션 목록 절단 감지 · 사문 라벨(**기각**) · janitor probe 전이                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 그 경로가 실측될 때                                                                                               | S         | 2026-07-30 live-entry-completeness                     |
| [BL-564](#bl-564) | ✅ **Resolved** (2026-08-09 backlog-sweep) — `bl-audit.sh` 가 코드펜스 · `<details>` 안의 옛 상태줄을 SSOT 로 오인할 수 있다. **처방 2건이 이미 구현돼 있었다**(`:114-120` 스킵 · `:268-288` 중복=exit 1)이고 Trigger 「게이트 체인 편입 전」도 도래(`final-gates.sh:151`). 코드 0줄                                                                                                                                                                                                                                                                                                                                                                                                           | 그 관용구가 상태줄을 품게 될 때                                                                                   | XS        | 2026-07-30 close-mismatch-soak                         |
| [BL-573](#bl-573) | (P3) `engine_only` tick 당 `list_resting_conditional_entries` 2회 — 감지가 reconcile 보다 앞서 돌아 공유 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | tick 비용을 손댈 때 / 두 경로를 합칠 때                                                                           | S         | 2026-08-01 soak codex                                  |
| [BL-581](#bl-581) | `/metrics` 영구 누적 **10277 파일 · 635MB · PID 1968** (counter 삭제 금지)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 20000 파일 초과 · 스크레이프 지연 · 여유 20G 미만                                                                 | M         | 2026-08-02 metric-guard-parity                         |
| [BL-582](#bl-582) | divergence counter 13 series 중 **5종** 도달 불가 (2026-08-03 재판정 — 7종에서 축소. 2종은 엔진 구동으로 **반증**), 프로덕션 확인 3/8                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 반증된 2종이 프로덕션에서 발화하거나 `other` def-use 오라클이 red 일 때                                           | S         | 2026-08-02 metric-guard-parity                         |
| [BL-584](#bl-584) | `BalanceUnverified` 가 라이브 dispatch 의 결정론적-거절 튜플 양쪽에 없다 — 소진 시 실제 사유가 `max_retries_exhausted` 로 덮인다. ★2026-08-03 **현재 코퍼스 도달 불가 확정**(계정 mode 는 생성 후 불변 · `mode=live` 계정 0건) ⇒ 수리 보류, Trigger 를 cutover 로 보강                                                                                                                                                                                                                                                                                                                                                                                                                         | **`mode=live` 계정이 생성될 때**(Wave 3 cutover), 또는 `outcome="max_retries_exhausted"` 창 차분이 0 을 벗어날 때 | S         | 2026-08-03 metric-guard-residual-close                 |
| [BL-578](#bl-578) | 조건부 진입 `110092`/`110093` 거절 시 거래소가 준 정답(`current[...]`)을 버린다 — BL-536 재판정에서 유일하게 살아남은 채널의 잔여 (측정 완료 · 수리 보류)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | C1 거절이 하루 3건 이상으로 다시 오르거나 실자금 cutover 로 1건 비용이 달라질 때                                  | S         | 2026-08-01 entry-completeness-rejudgement              |
| [BL-586](#bl-586) | ✅ **Resolved** 2026-08-07 backtest-fidelity — 키 리스트를 `dataclasses.fields()` 자동 유도로 교체(스칼라 46 전량 + 리스트 3종 digest + 중첩 2종 평탄화 + `RawTrade` 22 전량). 원 증상: P-3 골든이 `BacktestMetrics` **51 중 13**, `RawTrade` **22 중 11** 만 고정해 38+11 이 회귀 감지 밖                                                                                                                                                                                                                                                                                                                                                                                                     | TV parity 팩·비용 분해·청산 지표에서 회귀가 의심될 때                                                             | M         | 2026-08-03 backtest-metric-oracle                      |
| [BL-599](#bl-599) | Pine v1 shim(`src/strategy/pine/` 135L)은 타입 4종만 재export 하는 껍데기지만 `BacktestOutcome.parse` 가 코어 DTO 필드라 **단독 철거 불가**. 소비처는 「2곳」보다 넓다 — 프로덕션 import 2 + 생성 site 10+ + 테스트 3파일                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `BacktestOutcome` 를 손볼 일이 생겼을 때 (단독으로 열지 마라)                                                     | M         | 2026-08-06 dead-code-sweep                             |
| [BL-600](#bl-600) | `strategy/trading_sessions.py:26` 의 `TradingSession` 이 CONTEXT 헌법의 _Avoid_ 이름과 **동음이의 충돌**(이쪽은 장중 시간대 필터). 값이 `Strategy.trading_sessions` **JSONB 에 영속**돼 단순 rename 불가                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | `trading_sessions` JSONB 를 마이그레이션할 때 · 도메인 용어 정리 시                                               | M         | 2026-08-06 dead-code-sweep                             |
| [BL-601](#bl-601) | ✅ **호출 0건 잔재 3종 — 처리가 갈렸다.** 저장소 메서드 2건(`get_state_fresh` · `list_unsynced_reduce_only_since`)은 제거했고, `scripts/fleet-dispatch-test.sh` 는 **제거 대신 `final-gates.sh` 에 배선**했다. ★근거 반증 — 「나머지 둘은 final-gates 체인 안에 있다」가 절반 거짓이었다(체인 안은 `bl-audit-test.sh` 하나뿐). 그 하네스는 30/30 통과하고 원본 sed 추출이라 드리프트가 없다                                                                                                                                                                                                                                                                                                    | `OrderRepository` 를 손볼 때 함께 · 다음 dead-code 스윕                                                           | S         | 2026-08-06 dead-code-sweep                             |
| [BL-602](#bl-602) | ✅ 루트 prettier 가 `apps/web/` 안의 md 를 포맷하지 못한다 — **Resolved** (2026-08-17 야간 통합). ★처방(루트 devDependencies 의 `prettier-plugin-tailwindcss`)이 `71f7101e`(2026-08-09) — **이 BL 과 무관한 목적의 커밋** — 에 얹혀 이미 들어와 있었고 8일간 원장은 계속 「대기」였다. 레인 γ 의 DEFERRED 178건 재판정이 잡았다(그 회차 ① 판정 유일 1건). ★★**메시지로는 판별이 안 된다** — prettier 는 **ignore 된 파일에도** 「All matched files…」 + rc=0 을 낸다. `.prettierignore` 회피 3줄을 지운 **뒤에** 재서야 `apps/web/AGENTS.md`·`README.md` 가 rc=1(한 번도 포맷된 적 없다)임이 나왔다. 이연 부채 2건도 함께 처리(①은 대상이 이미 없었고 ②는 [BL-646] Resolved 로 거짓이 된 문장) | `frontend/` 안의 json/md/yml 을 커밋해야 할 때 (지금은 우회 가능하지만 다음엔 막힌다)                             | S         | 2026-08-06 e2e-consolidation                           |
| [BL-612](#bl-612) | ✅ **Resolved** (2026-08-09 backlog-sweep) — LESSON-095 압축 승격 → 버퍼 14,480B 삭제 → INDEX tombstone 전환. ★압축한 이유 = `lessons.md` **400줄 상한이 게이트 강제**(`docs-audit.sh:135`), 착수 시 380줄. ★**같은 위반 버퍼가 9건 더 있다**(최대 48,863B) — 본 항목 범위 밖. 원문: `docs/dev-log/2026-08-06-entry-set-divergence.md` 버퍼가 `docs/lessons.md` 로 승격되지 않았다 — ADR-026 §3 은 「세션 종결 시 승격 의무, 승격하면 버퍼를 비운다」인데 회차는 끝났고(PR #553 머지) 버퍼는 9천자로 남아 있다(반증 카드 상한 1~2천자 초과)                                                                                                                                                    | 다음 문서 정리 회차                                                                                               | XS        | 2026-08-07 docs-overhaul 리뷰                          |
| [BL-613](#bl-613) | `live_signal.py` 핸들러 가시화가 남긴 **줄 수 부채** — `_evaluate_session_with_engine` **506줄**(Kind B 추출 E8~E14 미완) · `_place_planned_entry` 236 · `_reconcile_conditional_entries_inner` 203 · `_async_dispatch_event` 256(최대 `try` 본문 **225줄** — 이제 이게 최대). ★가시성 목표(최대 try 845→8)는 달성됐고 줄 수는 못 채웠다                                                                                                                                                                                                                                                                                                                                                       | `live_signal.py` 를 다음에 크게 손댈 때 ([BL-580] 착수 회차와 겹친다)                                             | M         | 2026-08-04 handler-visibility (status 승계)            |
| [BL-614](#bl-614) | ✅ **Resolved** (2026-08-09 backlog-sweep) — **LESSON-096** 승격(`git show 0f0f0b06:…` 에서 원문 회수). ★3건 중 ③(검증 도구 적대 검증)은 **새 항목을 만들지 않았다** — **LESSON-092 재발**이고 그건 이미 `backend/AGENTS.md` §10 으로 승격돼 있다(작성 규칙 = 같은 패턴이면 반복 횟수 증가). 원문: 2026-08-04 handler-visibility 회차 방법론 **3건이 `docs/lessons.md` 미승격** — dev-log 본문은 문서 대개편에서 삭제됐고 INDEX 한 줄과 git history 에만 남았다(다중집합↔문장 순서 · 재적재 지문 = celery 배너 · 검증 도구를 먼저 적대 검증)                                                                                                                                                   | 다음 문서 정리 회차 ([BL-612] 와 함께)                                                                            | XS        | 2026-08-04 handler-visibility (status 승계)            |
| [BL-615](#bl-615) | 스택 규칙 파일이 공식 권장 크기의 **2배** — `backend/AGENTS.md` **416줄** · `frontend/AGENTS.md` **316줄** (Claude Code 문서 권장 = 파일당 200줄 이하, 「Longer files consume more context and reduce adherence」). 그 디렉터리 파일을 열 때마다 전량 로드된다                                                                                                                                                                                                                                                                                                                                                                                                                                 | 스택 규칙을 다음에 손댈 때 ([ADR-027] 정착 후)                                                                    | S         | 2026-08-07 ADR-027 (배치 이전 중 실측)                 |
| [BL-616](#bl-616) | 부트스트랩을 **우회해 만든** 워크트리는 husky 훅이 없다 — `pnpm install` 을 건너뛰면 `prepare: husky` 가 안 돌아 `.husky/_`(미트래킹)가 안 생기고, git 은 없는 `core.hooksPath` 를 **경고 없이 무시**한다. 실태: 워크트리 5개 중 **4개 정상**, 우회 생성된 1개만 결손(2026-08-07 정상화 완료). ★남은 축 = **감지 수단이 없다** — 훅이 안 도는 실패 모드는 출력이 0줄이라 「통과」와 구별되지 않는다                                                                                                                                                                                                                                                                                            | 워크트리에서 훅 미작동이 또 관측되면                                                                              | S         | 2026-08-07 ADR-027 회차 (자기 커밋에서 발견)           |
| [BL-618](#bl-618) | ✅ **문서를 코드에 맞췄다(①) + 경계 오라클 신설.** ★「1200px」는 **5곳이고 전부 콘텐츠 그리드 축**(셸 미개입) ⇒ 셸 경계는 1024/768 둘뿐. ★★**정본은 셋이 아니라 넷** — `@theme` 이 `sm:` 640→375 · `xl:` 1280→1200 으로 덮어 AGENTS.md 표가 **틀린 값**이었다. ★e2e `sidebar` grep 0건 → `design-canon-responsive.spec.ts` 신설. 잔여 [BL-644~647]                                                                                                                                                                                                                                                                                                                                             | 앱 셸 반응형(사이드바 축소·검색바 숨김·컨테이너 폭)을 다음에 손댈 때                                              | S         | 2026-08-07 prototype-canon-v2                          |
| [BL-617](#bl-617) | ★**「과거 기록」이 아닌 운영 절차 4종이 working tree 밖으로 나갔다** — Cloud Run 런북(39KB)·Grafana 셋업·Bybit mainnet 체크리스트(11KB)·법무 임시 런북. ADR-026 의 분류 기준이 **위치**(폴더 이름)였지 미래 유용성이 아니었던 결과다. 머지 후 `docs/` 전체에서 Cloud Run·Grafana·Prometheus·mainnet·법무 언급 **0건**인데 `alerts.yml`·`Dockerfile`·워크플로 4종은 레포에 살아 있다. ★지금 되살리지 않는다 — 트리거 시점에 갱신해 재등재                                                                                                                                                                                                                                                       | [BL-071] 프로덕션 배포 발동 시 · Bybit mainnet 전환 시                                                            | S         | 2026-08-07 PR #554 리뷰                                |
| [BL-621](#bl-621) | ✅ **골든 `expected.json` 이 두 겹으로 낡아 있었다** — 손익 3지표가 2026-06-26(`80a2138e`) 이후 동결인데 그 뒤 ⑴ `cda575f2` 가 `ta.atr` 를 rolling SMA → Wilder RMA 로 바꾸고 ⑵ [BL-603] 이 비용 기본값을 내렸다. **Resolved** — 구 ATR + 구 비용을 **동시에** 되돌리자 4지표 전건 byte-identical 재현(⑴로 원인 특정). ★유일하게 보던 `num_trades` 는 네 조합 전부 14 라 **판별력 0** 이었다. `regen_golden.py` 신설 + `test_golden_backtest.py` 를 실제 오라클로 승격                                                                                                                                                                                                                         | —                                                                                                                 | XS        | 2026-08-07 gap-resync-autopsy                          |
| [BL-627](#bl-627) | ✅ **`regen_golden.py` 에 출력 경로 리다이렉트가 없어 라운드트립 시험이 **실제 `expected.json` 을 두 번 덮어쓰고 finally 에서 바이트 복원**한다 — 정상 종료 시 오염 0이지만 강제 종료되면 워킹 트리가 더러워진다. `--out-dir` 추가가 수리. ★부수: `--check` 의 「차이 없음」 종료 코드가 계약에 미명시.** 2026-08-09 해결 — `--out-dir`(--confirm 전용) 신설, 시험은 tmp 로 쓰고 **정본 불변을 직접 단언**. ★제안된 변이(SIGKILL→dirty)는 재현 불가라 판별 가능한 변이 2종으로 교체했다                                                                                                                                                                                                        | `regen_golden.py` 를 CI·병렬 실행에 넣을 때                                                                       | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-628](#bl-628) | ✅ **라이트 `--warning` `#875206`→`#824e05`** (subtle 6.03 / card 6.78 / bg 6.33 / bg-alt 5.99). ★자리는 마케팅 푸터가 **아니라** `legal-notice-banner.tsx:15`(전 라우트 상단). ★★**캐논 감사는 다크만 잰다** — 라이트를 재는 게이트가 0이었다 → `light-canon-contrast.test.ts` 신설. 잔여 [BL-648]                                                                                                                                                                                                                                                                                                                                                                                            | 라이트 공개 라우트 canon 을 다크 이하로 내리려 할 때                                                              | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-629](#bl-629) | ✅ **데드 `--chart-*` 7종 삭제**(axis·grid·bullish·bearish·line·area-top·area-bottom, 전부 참조 0건). `--chart-grid` 는 `brand-palette.ts`+sync 테스트도 동반. ★★**삭제를 지킬 것이 없었다** — 계약 테스트가 「정의된 것을 읽나」를 안 봤다 → **역방향 래칫**으로 정의 집합 동결                                                                                                                                                                                                                                                                                                                                                                                                               | 차트 축 색을 손대려 할 때 · 토큰 정리 스윕                                                                        | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-630](#bl-630) | ✅ **언레이어드 `table.trades tbody td.pos/.neg` 로 닫았다** — 명시도가 아니라 **캐스케이드 레이어**로 이긴다(KITPORT 무접촉). ★민짜 `.pos` 는 기각(표 밖 소비자까지 폭발). 오라클 = `design-canon-table-tone.spec.ts` 6조합×2테마, **역방향 2 포함**                                                                                                                                                                                                                                                                                                                                                                                                                                          | `<td>` 안에서 `.pos`/`.neg` 를 `.num` 없이 쓰게 될 때                                                             | XS        | 2026-08-07 backtest-fidelity                           |
| [BL-626](#bl-626) | ✅ **`count` dedup + opt-in 회수 `--prune-archives`** — `unreadable_labels` 가 `(label, at, session_id)` **관측 단위**로 센다(키에 `archive` 를 넣지 않는 것이 요점). 회수는 개수가 아니라 **포함관계** 기준: 같은 `(log_from, predicate_version, classifier_ok)` 에서 `log_to` 최신본이 나머지의 상위집합. ★★★**후보 ⑴ 「최근 N개만」은 판정을 깎는다 — 실측 반증**: 228벌에서 최근 50만 남기면 커버리지 시작이 08-04→08-08(나흘 소실), 168h/30분이면 ~336벌 필요 ⇒ 어떤 상수 N 도 불가. 실측 228→66벌(회수 162 · `log_to='Error'` 파손 10벌은 무접촉 — 문자열 정렬로 재면 파손본이 대표로 뽑힌다), **판정 diff 공집합**(실격 15건 불변). ★동기는 미발화 — 228벌 = **0.10MB · 59ms**          | `.soak/` 디스크 압박이 보일 때 · 게이트 1회 실행이 느려질 때                                                      | XS        | 2026-08-07 soak-unattended-watch                       |
| [BL-623](#bl-623) | 서버 클론이 `--single-branch` 라 feature 브랜치가 기본 fetch 로 안 온다 — `remote.origin.fetch` 가 main 한 줄뿐이라 `git checkout <branch>` 가 `pathspec did not match` 로 죽는다. 우회는 refspec 명시. 근본 수리(`git remote set-branches origin '*'`)는 소크가 도는 서버의 git 설정 변경이라 이연                                                                                                                                                                                                                                                                                                                                                                                            | 서버에서 feature 브랜치를 다시 받아야 할 때                                                                       | XS        | 2026-08-07 fe-oracle-deploy                            |
| [BL-638](#bl-638) | 🟡 `docs/archive/` 부재 — 2026-08-08 에 `lessons-archive-2026H1.md` 하나로 복원됐지만, `legacy_paths` 가 권장하는 하위 경로 4종은 여전히 없어 안내가 실행 불가다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 문서 보관 경로를 다시 안내하거나 정리할 때                                                                        | S         | 2026-08-08 bl003-unblock                               |
| [BL-640](#bl-640) | `.metrics` 가 컨테이너 세대를 넘어 누적된다 — `engine_only_suppressed` 합산 89 중 15가 이전 세대 값이라 창 안 차분에 창 밖 값이 섞인다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 게이트가 `.metrics` 값을 창 기준으로 해석할 때                                                                    | S         | 2026-08-08 bl003-unblock                               |
| [BL-644](#bl-644) | ✅ **Resolved — 767 → 768 한 줄.** 이 훅이 고르는 것은 Sheet vs Dialog 라 **셸의 모바일 판정과 같은 축**이고 셸은 `max-width:768px` 에서 넘어간다 ⇒ CSS 축에 붙였다. ★**세 축은 768 에서 전부 일치할 수 없다** — `min-width`·`max-width` 둘 다 경계값을 포함하므로 768 은 Tailwind `md:`(데스크탑)와 raw CSS(모바일)가 **동시에 참**인 유일한 점이다. 훅↔CSS 는 이제 일치, `md:`↔CSS 겹침은 이 BL 이전부터의 구조적 성질이라 그대로                                                                                                                                                                                                                                                            | 반응형 셸을 다시 손댈 때                                                                                          | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-645](#bl-645) | ✅ **Resolved (2026-08-09, W3)** — ★**처방 ③「주석만 달면 끝」이 틀렸다** — 정의 자리는 KITPORT 센티넬 안이고 가드가 **주석까지 대조**해 한 줄에 빨개진다(② 와 같은 allowlist 선행). ★**「어디에도 안 적혀 있다」도 틀렸다** — `DESIGN.md` §10.6 이 이미 근거까지 적고 있었다. 진짜 결함은 **줄 번호가 낡은 것**(`1159-1178`·`:1853` → 실측 `1146-1165`·`:1840`). 근거는 가드 밖 2곳에 두고 CSS 규칙은 안 건드렸다                                                                                                                                                                                                                                                                             | 백엔드 검색을 붙일 때 · CSS 정리 스윕                                                                             | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-646](#bl-646) | ✅ **Resolved — ① 등재**(`DESIGN.md` §4.3.1 신설, 콘텐츠 그리드 전용 6번째 경계). 흡수 2안 **실측 기각**. ★★**전제가 틀렸다 — 그리드가 받는 폭은 뷰포트가 아니라 `.page` 콘텐츠 박스이고 뷰포트에 단조가 아니다**(`--sidebar-w` 가 1024 에서 232→64 계단): 뷰포트 1023→**1025** 에서 콘텐츠가 911→**745** 로 **166px 줄어든다**. ⇒ 1024 흡수는 **가장 넓을 때 접는다**(모순 166px), 768 흡수는 뷰포트 769(콘텐츠 657)에서 `.trade-detail-metrics` 3열 219px 씩이 되며 `.metric` +6px **실제 파손**(「시각」이 「시/각」으로 꺾임), 900 유지가 모순 42px 로 최소. 근본 해는 컨테이너 쿼리 → [BL-647]. ★`frontend/AGENTS.md` §10 표는 [BL-602] 로 **미반영**                                     | 반응형 정본을 다시 손댈 때                                                                                        | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-647](#bl-647) | `frontend/AGENTS.md` §10 은 mobile-first 필수인데 `globals.css` 의 `@media` **30곳이 전부 `max-width`**(min-width 0건) = 100% desktop-first. 2026-08-08 에 규칙의 **사거리를 좁혀** 봉합했고(신규 Tailwind 컴포넌트만 필수) 전면 전환은 미결                                                                                                                                                                                                                                                                                                                                                                                                                                                   | CSS 규약을 집행 가능하게 만들 때                                                                                  | M         | 2026-08-08 fe-canon-and-responsive                     |
| [BL-648](#bl-648) | 🟡 **공개 라우트 라이트 런타임 커버리지 닫힘** — 처방 ②(`design-canon-public-light.spec.ts` 신설 + 감사 코어에 `theme` 옵션). ★**`colorScheme` 만으론 테마가 안 바뀐다**(`defaultTheme="dark"` ⇒ localStorage 선호값 필요) — `probeTheme()` 이 렌더 배경색을 읽어 도달 확인, 없으면 fail-open. ★★음성 대조: `--warning` 을 [BL-628] 회귀값으로 주입 ⇒ 새 spec **5/5 red**, **기존 다크 spec 은 5/5 초록**(AA 통과·캐논만 미달이라 하드 실패 게이트로 원리상 안 잡힌다). 복원 sha256 일치. 잔여 = **인증 셸 `.sidebar` 실폭**(소크 결합 [BL-597])                                                                                                                                               | 라이트 테마 회귀가 한 번 더 나올 때                                                                               | S         | 2026-08-08 fe-canon-and-responsive                     |
| [BL-649](#bl-649) | ✅ **Resolved — ① 삭제**(라이트·다크·`@theme inline` 3면 21줄). ②(`var(--warning)` 별칭 강등)를 버린 이유 = **별칭도 이름이고 소비자 0건이면 값을 못 한다** — 남기면 `@theme inline` 이 계속 유틸을 찍어 다음 사람이 또 고민한다. ★**「소비 0건」은 맞았지만 「참조 0건」은 아니었다** — [BL-629] 역방향 래칫 `CHART_VARS_FROZEN` 이 `--chart-1..5` 를 동결 목록에 잠그고 있었고(주석이 스스로 「처분은 [BL-649]」라 지목), 목록을 안 고쳤으면 집합 동등 단언이 red — **래칫이 설계대로 물었다**. 부수로 댕글링 주석 2줄 `warning` 정정                                                                                                                                                        | 토큰 정리 스윕                                                                                                    | XS        | 2026-08-08 fe-canon-and-responsive                     |
| [BL-652](#bl-652) | ★**[BL-598] 의 결론은 전부 warm 프로세스 한정이다 — cold 축은 미측정**. 프로파일러 `section_import` 이 **첫 서브프로세스(17초, bytecode 컴파일+파일 캐시 워밍 포함)를 버리고** 이후 0.26s 로 가설 (a) 를 기각했는데, **CI 러너는 매 잡이 cold** 이고 샤드를 나누면 샤드마다 cold 다. 버린 17초가 샤드 수만큼 반복되는지는 아무도 안 쟀다(3샤드면 최악 51초). [BL-598] ② 의 파싱 디스크 캐시는 **파싱 비용만** 지우고 import·bytecode 는 캐시 히트여도 일어나므로 이 축은 남는다                                                                                                                                                                                                                | [BL-598] ② 착수 시 · CI 샤드 수를 늘리려 할 때                                                                    | S         | 2026-08-08 zero-touch-bundle                           |
| [BL-658](#bl-658) | `decisions/013-optimizer-strategy.md` 소급 작성 — ADR-013 은 결번인데 **실체는 삭제된 dev-log 로 git 에 살아 있다**(`94da86b1^`, 24,703B). [BL-504] 는 인용을 tombstone 경로로 돌려 닫았고, 남은 것은 **그 실체를 `decisions/` 로 승격**하는 일이다. 소급 작성은 결정을 새로 만드는 게 아니라 이미 실행된 결정을 기록하는 것이므로 **없는 근거를 지어내지 말고** `optimizer/executors/` 코드와 대조해야 한다                                                                                                                                                                                                                                                                                   | Optimizer 설계를 실제로 바꿀 때 (알고리즘 교체 · scikit-optimize 이탈 · GA 파라미터 변경)                         | M         | 2026-08-09 backlog-sweep ([BL-504] 분리)               |
| [BL-660](#bl-660) | `regen_golden.py --confirm` 산출과 커밋본의 **포맷이 구조적으로 어긋난다** — pre-commit `prettier --write` 가 배열을 한 줄로 접고 스크립트는 `json.dumps(indent=2)` 로 원소당 한 줄을 쓴다. 그래서 정본 갱신 의도로 `--confirm` 을 돌리면 diff 에 **의미 없는 재포맷이 항상 섞인다**(실측 `+29/-2`). ★`--check` 는 **파싱된 값**을 비교하므로 이 어긋남을 구조적으로 못 본다                                                                                                                                                                                                                                                                                                                   | 골든을 의도적으로 갱신할 때 / `regen_golden.py` 를 CI 에 넣을 때                                                  | XS        | 2026-08-09 backlog-sweep-4lane (W2, BL-627 부수)       |
| [BL-659](#bl-659) | `design-canon-calibration.spec.ts` 의 `screen-06-strategies-list.html` 케이스가 **간헐 실패**한다 — 2026-08-09 W3 에서 7회 중 2회. 같은 커밋에서 연속 3회는 42/42 green 이고 `git stash` 로 내 diff 를 걷어내도 통과/실패를 오갔다 ⇒ **코드 회귀가 아니다**. ★위험은 실패 자체가 아니라 **다음 회차가 이걸 자기 회귀로 오독하는 것**                                                                                                                                                                                                                                                                                                                                                           | 디자인 캐논 게이트가 빨개졌을 때 / 캐논 스윕 착수 시                                                              | XS        | 2026-08-09 backlog-sweep-4lane W3                      |
| [BL-709](#bl-709) | ✅ **Resolved — 2026-08-13 step 1~3에서 정렬 화이트리스트와 정규화기를 `features/strategy/sort.ts` 1벌로 공유하고, Next 16 URL `searchParams` 결과를 RSC prefetch·client query/queryKey·select에 일치시켰다. AC의 typecheck/lint/전체 테스트·단일 상수·data-testid·query 정합 검증을 통과했다.**                                                                                                                                                                                                                                                                                                                                                                                               | 전략 목록을 다시 손댈 때 / 정렬 링크 공유가 실사용될 때                                                           | S         | 2026-08-12 surface-demo-pack (G5)                      |
| [BL-710](#bl-710) | 전략 목록 성과 정렬·파생 필드의 **규모 비용 3종** — ⑴ `latest_completed` 서브쿼리가 owner/page 로 스코프되지 않아 전역 백테스트 규모만큼 든다 ⑵ `pine_source` 를 전량 로드해 행마다 정규식을 돈다 ⑶ `live_signal_sessions` 에 `strategy_id` **선행 인덱스가 없다**(기존 3개는 `user_id`/`is_active` 선행). 현 규모(전략 3 · 백테스트 7 · 활성 세션 0)에서는 무해하다                                                                                                                                                                                                                                                                                                                           | 전략 목록이 느려질 때 / 전략·백테스트가 수천 건이 될 때                                                           | S-M       | 2026-08-12 surface-demo-pack (codex G6 #1·#5·#6)       |
| [BL-711](#bl-711) | `metrics` JSONB **손상값**이 정렬 캐스팅에서 목록 전체를 500 으로 만든다 — `astext.cast(Numeric)` 는 `{"total_return":"corrupt"}` 에서 `invalid input syntax for type numeric` 이다. 같은 응답 경로의 `metrics_summary_from_jsonb` 는 손상값을 `None` 으로 격리하는데 **정렬 경로만 그 방어를 우회**한다. ★**선재다** — `backtest/repository.py:165-168` 이 같은 패턴을 4축에 먼저 갖고 있다                                                                                                                                                                                                                                                                                                   | 손상 `metrics` 가 관측될 때 / 정렬 축을 늘릴 때                                                                   | S         | 2026-08-12 surface-demo-pack (codex G6 #2)             |
| [BL-712](#bl-712) | 전략 목록 **표시 정합 2건** — ⑴ `lifecycle` 이 `is_archived` 를 안 봐서 아카이브된 전략도 `validated`/`deployed` 로 응답한다(칩 4번째 값이 없다 = 사용자 결정) ⑵ 정렬 select 라벨이 **방향을 말하지 않는다** — `?order_by=total_return&order=asc` 로 진입하면 오름차순인데 라벨은 「수익률 높은 순」이다(UI 는 그 URL 을 만들지 않지만 공유·수동 편집으로 도달한다)                                                                                                                                                                                                                                                                                                                            | 전략 목록 표시를 다시 손댈 때 / 아카이브 화면을 낼 때                                                             | S         | 2026-08-12 surface-demo-pack (codex G6 #4·#12)         |
| [BL-713](#bl-713) | e2e 정체성 프로브가 `<title>` **부분일치**라 고유 식별자가 아니다 — 다른 앱의 title 이 `QuantBridge` 를 포함하기만 하면 통과한다. 지금은 판별에 성공하지만(`"Nexus Admin"` 실측 red) 우연에 의존한다. 처방 = 고유 마커(예: `<meta name="qb-app" content="quantbridge">`)를 심고 프로브가 **그것**을 본다                                                                                                                                                                                                                                                                                                                                                                                       | 정체성 프로브가 거짓 통과하는 것이 관측될 때 / 같은 호스트에 앱이 늘 때                                           | XS        | 2026-08-12 surface-demo-pack (codex G6 #10)            |
| [BL-715](#bl-715) | ✅ **브랜치 잔재 판정 — Resolved (2026-08-14 gate-surface-close, 삭제 집행은 사용자 결정)**. ★**양 축 모두 반증** — 로컬 39건은 **이미 소멸**(`refs/heads/` = `main` 1개)이고, 원격 분류는 **방향이 뒤집혀 있었다**: 원장 「C(PR 이력 없음) 14」 → 실측 **E 9 + C 5 + D 9**. `gh pr list --head` 가 **이름으로만** 매칭한 산물이고, 팁 sha 로 치면 9건이 머지된 PR #74·#75 head 의 조상 = **23건 중 안전망을 가진 유일한 집합**이었다. 미머지 **152** 만 맞았다. 내용 가치 **0건**(전건 blob 반영 확인) · 유일한 미반영 `TEST_REDIS_LOCK_URL` 1줄은 이 회차가 `.env.example` 에 반영(Golden Rule 위반 실재)                                                                                    | 커밋 491개를 개별 대조할 시간이 확보될 때                                                                         | S-M       | 2026-08-12 branch-debris                               |
| [BL-718](#bl-718) | ✅ **`.github/CODEOWNERS` 부재** — `* @<gh-user>`(`gh api user` 로 확인) + `/apps/`·`/infra/`·`/tools/`·`/docs/decisions/` 구획. ★브랜치 보호 없음 실측(`…/branches/main/protection` 404 · rulesets `[]`) = **강제력 0**, 리뷰 라우팅·구조 문서화 효과만 — PR 본문에 명시하고, 강제가 필요하면 ruleset(required review) 도입을 별도 결정으로 올린다                                                                                                                                                                                                                                                                                                                                            | PR-1 머지 후                                                                                                      | XS        | 2026-08-13 monorepo-realign                            |

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

**★2026-08-16 deploy-activation — Site 6(주문 상세 드로어) 라벨 추가.**
`#641` 이 연 `order-detail-drawer.tsx` 는 손익 **값**은 목록과 같은 SSOT(`displayRealizedPnl`)를
쓰면서 **출처는 말하지 않았다** — 「손익 확정 시각」이 비어 있다는 것으로 사용자가 추정/확정을
**추론**해야 했다. 목록(`orders-blotter.tsx:163,652`)은 같은 판정을
`ORDER_REALIZED_PNL_SOURCE_LABEL` 로 적고 있었으므로, `realizedPnlSource` 주석이 경고한
「화면끼리 각자 계산해 한쪽만 고쳐진다」의 **세 번째 판**이었다.
수리 = 그 함수를 `export` 하고 드로어가 **같은 것을 호출**하게 했다(새 어휘 0 · 원장 처방의 「라벨」축).
★**손익을 안 보여주는 주문에는 출처도 안 적는다** — 목록과 같은 규칙이다. 안 그러면 손익이 빈
rejected 주문에 「추정」이 붙어 **없는 숫자에 등급을 매긴다**. 그 음성 대조가 새 테스트 3건 중 1건이고,
변이 2종(널 가드 제거 · 확정/추정 뒤집기)이 각각 **1건·2건 red** 로 판별력이 확인됐다.

**잔여** — ① Site 1·2 게이트는 여전히 추정·확정 혼재(의도) ② Site 5 일일 리포트 미표면화 ③ **포트폴리오 병합 커브는 포인트별 출처 표현 불가** — `mergeCumulativeCurves` 가 각 세션의 마지막 누적값을 carry-forward 해 더하므로 한 지점의 값은 대부분 과거 거래에서 실려온 값의 합이다. 집계 수준 라벨로 강등했고 구간별 표시는 세션 상세에서만 한다 ④ Site 4 는 `unrecorded_count` 를 세지 않는다(추가 왕복 0 을 택함 — 폴백은 `docs/archive/sprints/money-path-finish/operating-contract.md` §4).

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

### BL-547

**Title:** ★원장 seed 는 **그 tick 한 번만** 산다 — 다음 tick 에 조용한 고아가 될 수 있다 (아직 실측된 적 없음)
**Category:** Backend / trading (BL-544 잔여)
**Priority:** P2
**Trigger:** ★`qb_live_position_divergence_total{category="exchange_only"}` 이 **실제로 오르는 것이 관측될 때**
**Est:** M
**상태:** ⬜ Open — seed 는 여전히 gap tick 1회에만 계산되고 `_qb_ledger_seed_since` watermark 는 레포에 0건 — 처방 미착수. ★**2026-08-11 ledger-truth: 트리거가 도래했다** (아래 판정 줄).
**트리거 판정:** ~~미도래 — 외생 조건(외부 관측). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)~~
→ ★★★**2026-08-11 ledger-truth — 도래. `/metrics` 실측이 「미도래」와 본문 서술을 함께 반증했다.**

서버 `apps/api/.metrics` **1회** 스냅샷(2026-08-11 · prometheus multiproc 직독):

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

**② 「30건 Resolved」 → 16건.** `tools/scripts/bl-audit.sh`(정본) 대조 결과
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
**`apps/api/scripts/verify_*.py` 등 운영자 도구**다(서비스가 HTTP 에만 조립돼 스크립트가 못 쓴다).
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

**오라클** — `apps/api/scripts/classify_direction_divergence.py`(프로덕션 코드 미import).
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
`apps/api/tests/tools/scripts/test_classify_direction_divergence.py` **20 테스트** — 경계
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

이번 회차는 추적되는 `tools/scripts/soak-logs-follow.sh` 를 만들었다 — **466줄 신규**, 이번 브랜치 커밋
`32ea2a5d` 이며 systemd unit 승격 경로를 가진다. 서버 활성 세션은 현재 **0**이다. 이 장치를
서버 소크에 올린 뒤에야 같은 정지를 로그가 남아 있는 동안 재관측할 수 있다.

**Risk:** 🟡 [BL-622] 수리가 이 정지의 **사망 전이**는 막지만 **정지 자체**는 안 막는다.
17분 무평가 = 그 창의 신호를 안 낸다.

---

### BL-638

**Priority:** P3
**카테고리:** Docs / 보관 경로
**Trigger:** 문서 보관 경로를 다시 안내하거나 정리할 때
**Est:** S
**상태:** 🟡 **Partial (2026-08-08 bl003-unblock 회차)** — `docs/archive/` 디렉터리가 실재하게 됐고 `lessons-archive-2026H1.md` 가 들어갔다(lessons 442→341). ★**남은 것** — `docs-audit.sh` 의 `legacy_paths` 가 권장 대체 경로로 가리키는 `docs/archive/{operations,product,architecture,domain}/` 4종은 **여전히 없다**. 경로 존재 검사가 없어 게이트가 이를 안 잡는다.
**트리거 판정:** 미도래 — 동승 조건(문서 보관 경로를 다시 안내하거나 정리할 때). 잔여는 `legacy_paths` 가 가리키는 `docs/archive/{operations,product,architecture,domain}/` 4종 부재이고, 그 안내를 고치는 회차에 붙는다 (2026-08-11 bl-703-partial-verdicts)

**`docs/archive/` 부재로 권장 경로가 실행 불가였다.**

`tools/scripts/docs-audit.sh` 는 `docs/archive` 를 `frozen` 3종 중 하나로 선언하고
`docs/dev-log`·`docs/reports` 와 함께 관리한다. 또한 `legacy_paths` 의 권장 대체 경로는
`docs/archive/operations/` · `docs/archive/product/` · `docs/archive/architecture/…` ·
`docs/archive/domain/…` 이다. 그러나 2026-08-06 문서 대개편이 `docs/archive/` 를 통째로 지워
권장 경로가 없는 디렉터리를 가리켰다.

2026-08-08 실측으로 `docs/archive/` 는 다시 생겼고 다른 에이전트가 `lessons-archive-2026H1.md`
1개를 넣었다. 다만 `legacy_paths` 가 가리키는 하위 경로 4종은 여전히 없다. `docs-audit` 는 권장
문자열일 뿐인 이 불일치를 검사하지 않으므로 조용히 통과한다.

**Risk:** 🟡 안내를 따라가도 대상 경로가 없어 과거 자료를 꺼낼 수 없다.

---

### BL-641

**Priority:** P1
**카테고리:** 운영 / BL-003 게이트 해석
**Trigger:** BL-003 재계획 시 즉시 / 소크 재기동 회차마다 재측정
**Est:** M

★★**2026-08-15 층 경계가 하나 생겼다 — 창 1과 창 2를 같은 모집단으로 묶지 마라.**
첫 24h 창이 `✓ 자격 획득`(연속 **24.0007h** · 실격 0)으로 확정되고(**C1 = 1/3회**) 사용자 승인
아래 R0b(`down → pin b5e24fbf → up`)를 돌렸다. 그 pin 이 워커를 `fb7bb772`(#633) →
`b5e24fbf`(#642)로 **4개 PR · 217 파일** 점프시켰다.
⇒ **창 1 = `fb7bb772` · 창 2 = `b5e24fbf`** 로 층을 나눠 세라. MTBF·사망률을 한 줄로 합치면
서로 다른 코드의 수명을 섞는 것이다(이 항목이 2026-08-08 에 세운 층화 규칙 그대로다).
★부수 실증 — **`pin` 은 C2 를 죽이지 않는다.** 재기동 직후 판독에서 C2 가 **24.0007h 그대로**
남았다([ADR-024] §255 가 코드로 확인됐다). 창 2는 0.0000h 부터 따로 센다.
★창 2 시작(celery ready) = `2026-08-15T16:35:32Z`.
**상태:** 🟡 **부분 해결 — 2026-08-12 재측정 완료. 셈은 움직였지만 CI 는 아직 못 가른다**
(2026-08-08 soak-exclusivity-and-observability 착지 · 2026-08-12 surface-demo-pack 재측정).
⑴ 층화 + **95% 신뢰구간**을 [ADR-024] 에 등재했고
⑵ 재측정 도구 `apps/api/scripts/mtbf_stratified.py` 를 만들어 「회차마다 재측정」 Trigger 를
집행 가능하게 했다(self-check 가 앞 38행으로 이 회차 값을 재현한다, 2/2).
⑶ **2026-08-12 에 그 Trigger 뒷절을 실제로 집행했다** — 아래 표가 새 값이다. 4일 만에 노출이
107.12h → 193.37h(**+86.25h**)로 늘었는데 자동 사망은 **8건 그대로**다. **닫는 조건은 불변** —
사망률이 실제로 내려가야 하고, 그 판정은 며칠 단위 관측이라 이 회차 밖이다.
★★★**그 과정에서 이 BL 자신의 인용값이 반증됐다** — 아래 층화 표는 **점추정끼리 비교할 수
없다**. 네 층의 CI 가 **6쌍 전부 겹친다**(상세 = [ADR-024] §층화). ⇒ 「수리로 MTBF 가 올랐다」도
「내렸다」도 이 데이터로는 말할 수 없다. **닫는 조건은 불변** — 사망률이 실제로 내려가야 한다.

★★★**2026-08-15 clock-fill-sweep — 아래 「관측 밀도」 처방이 코드로 반증됐다. 축을 정정한다.**
`darkness` 가 `evaluate()` 안에서 읽히는 곳은 **정확히 2곳**이고 둘 다 시간 계산과 무관하다:
`soak_gate_predicate.py:752`(존재 여부만 C5 로) · `:797`(출력 전용). **`ratio` 를 비교하는 부등식은
레포 전체에 없다** — 어둠 99.9% 여도 C1/C2/C3/C4 는 비트 단위로 동일하다. 관측으로도 같은 결론이
나왔다: 02:05Z→04:51Z 사이 C2 는 **+2.86h(경과분 100% 귀속)** 인데 어둠 분자는 **+202(경과분 100%
어둠)** 로, 두 셈이 동시에 성립한다. ⇒ **「C1 을 채우려면 관측 밀도가 올라야 한다」는 거짓이다.
타이머 주기 단축안은 철회한다** (30분 주기는 C4 한계 60분에 대한 안전 여유 1회분이라 오히려
건드리면 안 된다 — `soak-watch.sh:196`).
**참인 명제**: C1/C2 크레딧 = `세션 lifetime ∩ 귀속 구간 ∩ [창시작, now] ∩ phantom 커버리지`
(`soak_gate_predicate.py:667-706`, 자르는 것은 `restrict():415`). 그리고 C1 은 시간의 합이 아니라
**「24h 이상 연속 구간을 가진 귀속 구간의 개수」**(`:719-723`)다 — `C1_cumulative_hours` 는 어떤
조건식에도 안 들어간다. 귀속 구간은 `attribution_intervals():210` 이 만들고 **`up` 이 열고
`pin`/`up`/`down` 이 닫는다.** ⇒ **de3db35a 의 「125.6h 살았는데 0.0000h」의 사인은 어둠이 아니라
「귀속 구간 밖」이다** — 실측(`.soak/pin-history.jsonl`)으로 귀속 구간이 2026-08-07 09:33 에 닫히고
다음이 2026-08-14 05:53 에야 열렸다. **처방은 이미 들어가 있다**(BL-737/744/745 = 감시자 부활 +
`OnFailure` 텔레그램). 이 축에서 새로 등재한 것 = **[BL-748]**(C4 공허 통과).

★★**2026-08-15 실측 추가 — 「세션이 살아 있었다」와 「시간이 계상됐다」는 다른 값이다.**
서버 세션 `de3db35a` 의 행은 08-08 23:16 ~ 08-14 04:51 동안 `is_active` 였는데(125.6h),
그 시점 게이트는 **`C1 0/3 · 누적 0.0000h`** 였다. 같은 출력이 **귀속 불가 107.02h · 어둠 비율
98.6%(8684/8808)** 를 함께 찍는다. 표본 435건 · 간격 중앙 **31.0분**(30분 타이머 주기)이므로
표본과 표본 사이는 전부 어둠으로 셈된다. ⇒ **C1 을 채우려면 세션 생존만으로 부족하고 관측
밀도가 함께 올라야 한다.** 이 회차는 그것을 재기만 했다 — 밀도를 올리는 처방은 미착수다.
★이 값을 「소크가 안 돌았다」로 읽지 마라. 2026-08-14 에 실제로 그렇게 읽어 status.md 표에
「7일째 정지」를 적었는데, 그때 서버 소크는 돌고 있었다(2026-08-15 반증).
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
단독으로 정해진다(`apps/api/scripts/mtbf_stratified.py` `parse_rows`). 정본이 코드 옆에 이미 적혀
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

| 창                  | n                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 노출                                | 자동사망 | MTBF                     | 95% CI          | 그 사망의 정체                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------- | ------------------------ | --------------- | ---------------------------------------- |
| 전 이력             | 40 (구 38)                                                                                                                                                                                                                                                                                                                                                                                                                                         | 193.37h (구 107.12)                 | 8        | 24.17h (구 13.39)        | [12.27, 55.99]  | 혼합                                     |
| 2026-08-03 이후     | 16 (구 14)                                                                                                                                                                                                                                                                                                                                                                                                                                         | 147.16h (구 60.91)                  | 7        | 21.02h (구 **8.70**)     | [10.20, 52.29]  | **혼합 — 이 BL 이 인용해 온 값**         |
| [ADR-025] 수리 이후 | 7 (구 5)                                                                                                                                                                                                                                                                                                                                                                                                                                           | 124.72h (구 38.47)                  | 2        | 62.36h (구 19.24)        | [17.26, 514.93] | gap-resync 1 — [BL-622] 가 수리 · 오염 1 |
| [BL-622] 수리 이후  | 4 (구 2)                                                                                                                                                                                                                                                                                                                                                                                                                                           | 91.84h (구 5.59)                    | 1        | 91.84h (구 —)            | [16.48, 3627.6] | **오염 1건뿐** — [BL-634] 미시행         |
| [BL-739](#bl-739)   | ✅ **화면 신호 비대칭 — Resolved (2026-08-15 soak-watch-restore)**. 술어 = **`has_fe` ∪ `has_api_src`**(`^apps/api/src/`, `has_be` 보다 좁다) — 원장 경고대로 단순 `$has_fe` 를 안 썼다. ★**잴 방법이 먼저 없었다**: `signal_gate` 의 dry-run 분기가 required 를 삼켜, 다른 게이트가 표에 보여주는 skip 사유를 신호만 안 보여줬다. 그 노출 회복이 수리의 절반. 케이스 ⑩ + 변이 **M4·M5 신설**(⑩ 이 자기 변이 없이 들어오지 않게 — BL-714 M12 선례) | 도래 — 이 회차가 그 자리에서 멈췄다 | S (30분) | 2026-08-15 soak-survival |

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

### BL-650

**Priority:** P2
**카테고리:** DX / 빌드 캐시
**Trigger:** dev 서버가 느려지거나 CSS 변경이 안 먹을 때 · 캐시 정책을 정할 때
**Est:** S
**상태:** 🟡 **부분 해결 — 부수(디스크 8.5GB)는 닫혔고 관측 장치를 걸었다. 정책은 미정이다**
(2026-08-08 soak-window-and-gate-attribution). ⑴ 낡은 빌드 디렉터리를 지웠다 — **4벌이 아니라
5벌**이고 합계 **8.5GB** 였다(`.next.stale-fp-20260723` **5.8G** · `.next.bak-turbocache` **2.0G** ·
나머지 3벌 117M). 레포 26G → **18G**. ⑵ `mise run fe` 가 `.next` 크기를 재서 1GB 초과 시 경고한다
(양성/음성 대조 2/2). **닫는 조건은 불변** — 「몇 GB에서 태우기 시작하나」를 재야 정책이 선다.
**트리거 판정:** 미도래 — 앞절은 이 회차에 관측되지 않았고(dev 서버 미기동) 뒷절 「캐시 정책을 정할 때」는 동승이다. ★단 `apps/web/.next` 는 2026-08-11 실측 **1.2GB** 로 `mise run fe` 경고선 1GB 를 이미 넘겼다 — 닫는 조건인 「몇 GB에서 태우기 시작하나」는 여전히 두 점(1.99GB 사망 · 593MB 무해)뿐이다 (2026-08-11 bl-703-partial-verdicts)

★★★**재현에 실패했고 그것이 이 회차의 결과다.** 593MB 캐시에 요청 1건을 먹인 뒤 재니
**idle CPU 0.1% · `/` 0.61초 · RSS 945MB** 였다 — 아래 표의 `rm -rf` 후 값과 같다. 즉 증상은
**크기 단조가 아니다**(RSS 는 이미 945MB 인데 CPU 는 0.1%). 1.99GB 를 만들려면 며칠의 개발이
필요하므로 **문턱은 이 회차에서 아래로부터 잴 수 없었다.** `mise run fe` 경고선 1GB 는 그래서
**정책이 아니라 관측 장치**이고, 근거는 두 점(1.99GB 사망 · 593MB 무해)뿐이다 — 인용 금지.

★★**수리 방향 ①은 실행 불가다 — `turbopackMemoryLimit` 은 존재하지 않는다.** Next 가
`experimental.turbo.memoryLimit` 과 `experimental.turbopackMemoryLimit` 을 **둘 다 제거**했고
대체 옵션이 없다(codemod `next-experimental-turbo-to-turbopack` 이 「no longer supported,
removed entirely」라고 명시). 실재하는 손잡이는 **둘뿐**이다:
`experimental.turbopackFileSystemCacheForDev`(dev 기본 **켜짐** — 끄면 재기동이 느려진다,
그게 이 캐시의 존재 이유다) · `turbopackMemoryEviction: false | 'full' | 'auto'`(기본 `'auto'`,
스냅샷 뒤 메모리 회수). ⇒ **①을 「상한을 건다」로 적은 원안은 폐기하고 위 둘로 교체한다.**

★**왜 8.5GB 가 아무 눈에도 안 띄었나 — `apps/web/.gitignore:3` 이 `.next*/` 를 무시한다.**
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

~~★부수 — `apps/web/` 에 낡은 빌드 디렉터리가 **4벌** 방치돼 있다.~~ ★**2026-08-08 정정 —
5벌이었고 합계 8.5GB 였다. 지웠다**(위 상태 줄).

**수리 방향(택1, 조사 필요) — 2026-08-08 개정:** ~~① 캐시 상한(`turbopackMemoryLimit`)~~
**①′ 정기 청소를 정책으로**(상한 옵션은 Next 에 **없다**, 위 참조) ② `next.config.ts` 에서
`experimental.turbopackFileSystemCacheForDev: false` — 증상은 구조적으로 사라지지만 **재기동이
느려진다** ②′ `turbopackMemoryEviction: 'full'` — RSS 945MB 실측에 겨눈다, 단 **CPU 증상에
듣는지는 미검증** ③ Next 업스트림 이슈인지 확인한다 — 2GB 까지 자라는 것 자체가 정상인지
판정이 없다.
~~★**정책을 정하기 전엔 「dev 가 이상하면 `rm -rf .next` 부터」가 유일한 처방이다.**~~
→ ★**2026-08-17 [BL-795] 로 정정.** 순서가 뒤집혔다 — 정본은 **「재기동 먼저, 그래도 남으면 서버를
죽인 뒤 캐시 제거」**이고 전문은 `gates-and-traps.md` 의 2원인 대조표다(`setup` 단계 실패 + 429 0건이면
캐시 축). 이 문장을 그대로 두면 같은 장애 대응의 순서가 한 레포 안에서 충돌한다 — `/codex` 적대 리뷰가 잡았다.
★★**어느 것도 근거 없이 켜지 않는다** — 문턱을 모르는 상태에서 손잡이를 돌리면 「고쳤다」와
「원래 안 났다」를 구분할 수 없다(593MB 재측정이 정확히 그 상태다).
**Risk:** 🟠 개발을 실제로 멈춰 세웠다. 프로덕션 무관(빌드 산출물).

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
"orders": […]}}` 를 낸다. 그런데 `apps/web/src/lib/api-client.ts:53,97` 은 **최상위 `code`** 와
**`detail.detail` 문자열**만 처리한다 ⇒ 주문 목록과 메시지가 사라지고 화면에는
generic `API 409 …` 만 뜬다. `router.py:610` 에 409 `responses` 선언이 없어 **OpenAPI 에도
이 구조가 없다**(생성 응답은 202·422 뿐).

★백엔드는 완화를 이미 넣었다 — `message` 필드에 사람이 읽을 한국어 한 문장을 싣는다.
그러나 클라이언트가 중첩 `detail` 을 안 펴므로 그것조차 화면에 안 나온다.
★2026-08-10 회차는 `apps/web/` **0줄** 제약이라 손대지 않았다.

**권장 접근:** 라우터에 409 error schema 를 선언하고, `api-client.ts` 가 중첩
`detail.code`/`message`/`orders` 를 펴서 렌더하도록 맞춘다.

**§OpenAPI 판단 (2026-08-10 fe-close-surface).** 409 `responses` 선언을 **넣지 않았다**.
근거 셋이 전부 실측이다 — ⑴ `apps/web/` 에 OpenAPI 코드젠이 **없다**(생성 타입 파일 0 ·
codegen 스크립트 0). 화면은 수기 Zod 로만 계약을 아니까 선언이 화면에 도달하는 경로 자체가
없다. ⑵ `responses=` 를 쓰는 라우트가 `apps/api/src` 전체에 **0건**이다 — 넣으면 FE 회차가
선례 없는 관례를 연다. ⑶ `test_main_openapi_gating.py` 는 docs **노출** 게이팅만 재고, 에러
응답 문서화를 요구하는 게이트는 없다. ⇒ 값이 0 인데 `apps/api/src` 를 건드리게 된다.
**넣을 값이 생기는 시점은 FE 가 OpenAPI 에서 타입을 생성하기 시작할 때**다.

**Risk:** 🟡 ~~운영자가 화면만 보면 조건부 잔량을 못 본다~~ → 🟢 화면 축은 닫혔다. 남은 것은 문서 축

---

### BL-667

**Title:** `apps/web/**` 의 json·md 를 스테이징하면 pre-commit 이 죽는다 (루트에 prettier 플러그인 부재)
**Category:** DX / 게이트
**Priority:** P3
**Trigger:** `apps/web/` 안의 json·md·yml 을 커밋할 때
**상태:** 🟡 부분 해결 (2026-08-09 fe-perf-quartet) — 루트 devDependency 를 추가해 즉시 증상은 없앴다. 구조(두 곳이 같은 설정을 서로 다른 해석 뿌리로 읽는다)는 그대로다
**트리거 판정:** 미도래 — 동승 조건(`apps/web/` 안의 json·md·yml 을 커밋할 때). 즉시 증상은 루트 devDependency 로 닫혔고 잔여는 구조(두 곳이 같은 설정을 서로 다른 해석 뿌리로 읽는다)뿐이라 그 파일들을 건드리는 회차에 붙는다 (2026-08-11 bl-703-partial-verdicts)
**Est:** XS
**출처:** 2026-08-09 fe-perf-quartet (커밋이 실제로 막혀서 발견)

**원인 / 영향:** `apps/web/.prettierrc` 가 `"plugins": ["prettier-plugin-tailwindcss"]` 를 선언하는데 그 패키지는 **`apps/web/node_modules` 에만** 있었다. 루트 `package.json` 의 lint-staged 는 `*.{json,md,yml,yaml}` 을 **레포 전역**으로 잡아(패턴에 슬래시가 없어 basename 매칭) `apps/web/package.json` 같은 파일에도 루트 prettier 를 돌린다. 그러면 prettier 가 `apps/web/.prettierrc` 를 찾아 읽고 플러그인을 **루트에서** 해석하려다 실패한다:

```
[error] Cannot find package 'prettier-plugin-tailwindcss' imported from <repo>/noop.js
```

★**기존 결함이다** — 손대지 않은 파일로 재현된다: `npx prettier --check apps/web/tsconfig.json`. 오랫동안 `apps/web/` 의 json 을 커밋한 회차가 없어 잠복해 있었다(직전 사례는 PR #463).

★**증상이 원인을 숨긴다** — lint-staged 가 `prettier --write [FAILED]` 와 함께 eslint 태스크를 `[KILLED]` 로 찍어서 **eslint 가 실패한 것처럼 보인다.** 실제 실패는 prettier 하나뿐이다.

**권장 접근:** 근본 해는 둘 중 하나다 — ⑴ 루트 lint-staged 의 json/md 글롭에서 `apps/web/**` 를 제외하고 frontend 자신의 prettier 에 맡긴다 ⑵ 두 `.prettierrc` 를 하나로 합친다. 지금은 ⑶ **루트에 플러그인 추가**로 막아 뒀는데, 버전이 두 곳에서 각자 흘러가면 같은 파일을 두 도구가 다르게 포맷할 수 있다.
**Risk:** 🟢 포맷만 건드린다.

---

### BL-736

**Title:** 로컬 Docker VM 디스크 94% — Redis AOF 쓰기 실패가 celery 를 통째로 죽였다
**Category:** 운영 / 로컬 환경
**Priority:** P2
**Trigger:** ★**이미 발화했다** — 2026-08-14T06:04:11Z
**Est:** S (1h)
**출처:** 2026-08-15 soak-survival

**원인 / 영향:** 워커 로그 실측 —
`MISCONF Errors writing to the AOF file: No space left on device` → celery
`Unrecoverable error` → `OSError(28) '/tmp/pymp-*'` 반복. beat 도 같은 시각에
`Message Error: Couldn't apply scheduled task evaluate-live-signals` 로 죽었다.
**디스크가 차면 브로커가 죽고 브로커가 죽으면 소크가 멈춘다.**

★2026-08-15 현재도 **94% / 3.1G 여유**다.

★★**초판 처방이 실측으로 반증됐다.** 「`docker image prune -f` 로 7.4GB 회수」라고 적었는데
실제로 돌리자 **`Total reclaimed space: 0B`** 였다. `docker system df` 의 `RECLAIMABLE` 은
**dangling 이미지가 아니라 「어느 컨테이너도 안 쓰는 태그된 이미지」**를 포함하고,
`prune -f` 는 dangling 만 지운다. 회수하려면 `-a` 가 필요하다.

그런데 실측하면 **그 5.5GB 가 전부 남의 프로젝트 것**이다:

```
nexus-clarification-admin        2.04GB      catthehacker/ubuntu:act-latest  1.65GB
nexus-clarification-client       1.83GB      ffwpu-culture-migrate           1.25GB
truewords-backend:30ca81f        1.02GB
```

`-a` 를 돌리면 그 프로젝트들이 **재빌드**를 해야 한다. 볼륨 19.59GB 도 마찬가지로
`feedlens_pgdata` · `nexus_*` · `kairos_*` 등 **남의 DB** 를 포함한다.

⇒ **안전한 자동 회수 경로가 없다.** 무엇을 버릴지는 그 프로젝트들의 소유자(사용자) 판단이고,
이 항목이 할 수 있는 것은 **정확한 목록을 제시하는 것**까지다. 자동화하려면 QuantBridge
소유 이미지만 고르는 필터(`quant-bridge-*` 접두)가 선행이다.

★소크가 서버로 갔으므로([BL-735]) 이 항목이 소크를 다시 죽이지는 않는다. 그러나 로컬 개발·
pytest·`docker build` 가 3.1G 에서 돌아간다.

**Risk:** 🟡

**상태:** 🟡 **부분 해결 — QuantBridge 축은 종결. 남은 것은 우리 것이 아니다 (2026-08-15 clock-fill-sweep)** — 사용자 결정(「QuantBridge 것만 회수」)에 따라 **LINKS=0 인 우리 소유 볼륨 11개**를 개별 `docker volume rm` 으로 지웠다(`prune -a`·`volume prune` 미사용 — 남의 프로젝트를 함께 가져간다). 실측 회수 **19.64GB → 19.57GB = 약 70MB**. ★**원장의 전제가 정량으로 확정됐다** — 회수 가능분 19.64GB 중 우리 몫은 **0.4%** 다. 나머지는 익명 볼륨 85개 + `ffwpu-social`·`feedlens`·`naengpa` 등 남의 프로젝트다. ★**이미지는 지우지 않았다**: `quantbridge-frontend` 3태그는 **같은 ID(`6a4224b1c612`)** 라 태그를 지워도 0B 고, `quant-bridge-backend-*` 4종(612MB×4)은 **소크 스택 재기동에 필요**한데 `docker build` 가 디스크 때문에 금지 상태라 지우면 되돌릴 수 없다. ⇒ **디스크 94% 는 그대로다. 우리가 더 할 것이 없다** — 무엇을 더 버릴지는 그 프로젝트 소유자의 결정이다.
**트리거 판정:** 도래 — 06:04:11Z 실사고 로그가 근거다 (2026-08-15 soak-survival)

---

### BL-774

**Title:** TradingView webhook 이 **body 기반 HMAC** 을 요구한다 — 동적 alert 본문에서 성립하는지 미확인
**Category:** Backend / Trading ingress
**Priority:** P2
**Trigger:** ★사용자가 실제 TradingView alert 로 webhook 을 연결하는 시점 · 또는 그 경로를 문서에 정본으로 올릴 때
**Est:** M (실측 선행 · 결과에 따라 ingress 설계 분기)
**출처:** 2026-08-16 외부 레포 비교 분석(finsight) 지적 → 코드 축만 확정, **TradingView 쪽은 [확인 필요]**

**원인 / 영향:** `trading/webhook.py:116` 은 `hmac.new(secret, payload, sha256)` 으로 **요청 body
전체**에 대한 HMAC 을 계산해 query `token` 과 비교한다. FE 도 그대로 안내한다 —
`tab-webhook.tsx` 의 URL 템플릿이 `.../webhooks/{strategyId}?token={HMAC}` 이고 힌트 문구가
「`{HMAC}` 자리에는 secret 과 body 로 만든 HMAC-SHA256 토큰을 채웁니다」다.

**[확인 필요] — 아직 실측하지 않은 것:** TradingView alert 는 URL 과 message 를 **정적으로** 지정한다.
⑴ body 가 완전히 고정이면 HMAC 도 고정이므로 이 방식은 **동작한다**(외부 분석의 「불가능」은 과장이다)
⑵ 그러나 body 에 `{{close}}`·`{{time}}`·`{{strategy.order.action}}` 같은 placeholder 를 넣는 순간
본문이 매 alert 마다 달라지고 **고정 token 은 전부 401 이 된다.** 실제로 어느 쪽인지는
**사용자의 alert 본문 설계에 달려 있고 아직 실측이 없다.**

**함께 볼 것 — idempotency:** `trading/router.py` 의 idempotency key 는 **optional query
parameter** 다. 고정 키를 쓰면 다음 정상 alert 가 충돌로 거부되고, 생략하면 TradingView 의
재전송이 **중복 주문**이 된다. 즉 HMAC 축과 idempotency 축이 **같은 결정에 묶여 있다.**

**권장 접근:** ⑴ ★**먼저 실측해라** — 실제 TradingView alert 하나를 정적 body 로 걸어 200 이 나는지
확인한다. 코드를 고치기 전에 이 한 건이 설계를 가른다 ⑵ 동적 body 가 필요하다고 판정되면 세 갈래 중
선택: (a) 고정 endpoint token + body fingerprint (b) 서명 relay (c) 서버가
`strategy_version + symbol + side + bar_timestamp` 로 idempotency key 를 **자동 생성**
⑶ (c) 는 [BL-773] 의 `strategy_version` 에 의존한다 — 순서를 보라

**Risk:** 🟡 (ingress 계약 변경은 기존 연결을 끊을 수 있다. 지금 실사용 연결이 있는지부터 확인)

**상태:** ⬜ Open — 2026-08-16 에 코드 축(body-HMAC + optional idempotency)만 확정. **TradingView 쪽 실측 미착수**
**트리거 판정:** 도래 — 다만 첫 step 은 코드 수리가 아니라 **실측 1건**이다 (2026-08-16 external-comparison)

### BL-813

**Title:** FE 순수 판정 모듈에 테스트가 0건이다 — 인증 경계(`proxy.ts`)·마케팅 캐논·어댑터가 무증거로 산다
**Category:** 테스트 / 프런트엔드
**상태:** 🔵 **ACTIVE** — 2026-08-21 밤샘 루프 2차가 짊어진다
**Priority:** P2
**Trigger:** 도래 — 2026-08-21 전이 폐포 실측으로 확인됐다
**Est:** M (8 lane 워크트리 병렬)
**출처:** 2026-08-21 밤샘 루프 2차 착수 (1차 [BL-812] 의 FE 판)

**원인 / 영향:** `apps/web` 의 vitest 는 227 파일 1,497 케이스로 두텁지만, **어떤 테스트도 import 하지
않는 소스가 58개**다(전이 폐포 실측 2026-08-21 — 소스 343 중). 그중 **완전 미도달 5종이 판정 로직**이다:

- `src/proxy.ts` — **이 앱의 인증 경계**([ADR-034] 가 Clerk 미들웨어를 대신한 자리). 공개 라우트 판정 ·
  geo L2 리다이렉트 · 세션 완전 검증이 전부 여기 있는데 테스트가 0건이다
- `src/lib/route-matcher.ts` — 그 판정을 컴파일하는 술어
- `src/lib/auth.ts` — **geo-block L3**(가입 거부)과 **탈퇴 fail-closed**(돈을 멈추는 경로).
  둘 다 2026-08-17 codex 적대 리뷰의 P1/P2 수리인데 그 수리를 재는 테스트가 없다
- `src/lib/auth-server.ts` — SSR prefetch 의 `{userId, token}`. 「실패를 삼킨다」가 계약이다
- `src/lib/legal-links.ts` — 법무 링크 상수

★**이 축의 위험은 「있다고 여겨진 것이 그 경로를 안 지났다」이다** — 이 레포가 이미 4번 밟았고,
그중 하나가 바로 **geo-block L3 이 한 번도 발화한 적이 없었다**는 것이다([LESSON-114]).
같은 자리에 다시 테스트가 없다.

★**직접 단언 0(전이적으로만 실행)** 인 것도 함께 든다 — `lib/unsupported-builtin-hints.ts`(화면에
나가는 미지원 사유 문장) · `lib/marketing-canon.ts`(화면 3벌이 셀 단위로 같은 값을 렌더하는 공동 원장) ·
`lib/webhook-base.ts`(dev/prod 배지) · `lib/zod-v4-resolver.ts`(폼 오류 매핑) ·
`store/ui-store.ts` · `hooks/use-media-query.ts`.

**처방:** 대상 소스 **무변경**으로 `apps/web` 에 테스트 파일 10개를 신설한다. 8 lane 워크트리 병렬
(`phases/fe2-*`). lane 간 파일 겹침 0 — 각 lane 은 자기 테스트 파일만 만들고 대상 소스 ·
`vitest.config.ts` · `tests/setup.ts` 를 건드리지 않는다.

★**착수 전 실측(2026-08-21)** — AC 판별력 8/8 red(`pnpm test -- --run <부재 파일>` rc=1 ·
양성 대조 count=0 → rc=1) · 기준선 `227 files / 1497 passed · 21초` · `tsc --noEmit` rc=0 · 2초.
★**구조적 전제 1건을 사전 배치 커밋이 해결했다** — `src/lib/auth-server.ts` 는 `import "server-only"`
가 **vitest 에서 top-level throw** 라 import 조차 불가능했다(`vi.mock` 으로도 못 막는다 — CJS
외부화라 Node 의 require 가 먼저 돈다). `vitest.config.ts` 의 `resolve.alias` + `tests/stubs/server-only.ts`
로 길을 텄다.

### BL-811

**Title:** 로컬 검증 두 레그가 **같은 BE 를 서로 다른 origin 으로** 요구한다 — 한 번에 다 통과시킬 수 없다
**Category:** 테스트 / 인프라 / DX
**Priority:** P3
**Trigger:** 도래 — 2026-08-19 실측으로 확인됐다 (구 종결 게이트 실행 중)
**Est:** S~M (갈래 선택이 먼저다. 코드는 그다음)
**출처:** 2026-08-19 n6-authed-evidence — 종결 게이트를 돌리려다 실측

★**2026-08-19 재기술 ([ADR-037]).** 이 항목의 초판은 `final-gates.sh --deferred-only` 의 **유예 집합**을
프레임으로 썼는데, 그 스크립트는 같은 날 제로베이스로 **철거됐다**(원문 = `git show harness-v1:tools/scripts/final-gates.sh`).
유예 원장·종결 절차라는 껍데기는 사라졌지만 **밑에 있던 제약은 그대로 참이다** — 아래로 좁혀 다시 적는다.

**원인 / 영향:** 로컬에서 돌리는 두 검증이 서로 다른 origin 을 요구한다.

- `e2e chromium` · `e2e design-canon` · `e2e authed` — **FE dev 서버** `:3100` (`apps/web/e2e/_base-url.ts` 파생)
- **화면 증거 팩 (authed)** — 러너가 띄우는 **프로덕션 서버** `:3110` (`screen-evidence.config.json` 의
  `serverPortBase` + 슬롯). dev 서버를 쓰면 Turbopack 캐시 상태에 따라 번들 바이트가 흔들려 이 측정의
  존재 이유가 사라지므로 **그 분리는 의도된 것**이다.

그런데 BE 의 CORS 는 **단일 값**이다 — `apps/api/src/main.py` `allow_origins=[settings.frontend_url]`.
`BETTER_AUTH_URL`(JWKS 취득 + JWT issuer)도 하나다. ⇒ 한 BE 인스턴스가 두 origin 을 동시에 받을 수 없고,
**BE 를 한 번 띄운 채로 두 레그를 다 통과시킬 방법이 지금 없다.**

★**거짓 초록은 안 난다** — origin 이 안 맞으면 화면 증거 레그의 전제 프로브가 그 자리에서 죽는다
(진단 문구가 두 변수를 다 짚는다). 잃는 것은 **BE 재기동 없이 한 번에 끝내는 것** 하나다.

**권장 접근:** ⑴ 갈래를 먼저 정해라 — ⓐ BE 를 **두 벌** 띄운다(포트가 다르면 `NEXT_PUBLIC_API_URL` 도
갈라야 해서 빌드가 둘이 된다) ⓑ `allow_origins` 를 목록으로 넓힌다(**개발 전용 경로에 한정** — 프로덕션에서
넓히면 [BL-754] 계열 결함이 된다) ⓒ 두 레그를 **다른 실행으로 나눈다**(가장 싸고 지금 실질적으로 하는 것.
★[ADR-037] 이후에는 「유예 원장이 비어야 종결」 규약 자체가 없으므로 **ⓒ 의 유일했던 단점이 사라졌다**
— 현재 기본 권장은 ⓒ 다) ⑵ ★**ⓑ 를 고른다면 `frontend_url` 을 읽는 곳 전부**(`config.py` validator ·
`waitlist_invite_base_url` · 초대 메일 링크)를 함께 봐라 — 이 값은 CORS 전용이 아니다.

**Risk:** 🟢 (거짓 초록은 안 난다. 로컬 검증이 두 번으로 나뉠 뿐)

**상태:** ⬜ Open — 2026-08-19 등재 · 같은 날 **재기술**(구 `final-gates.sh` 프레임 제거). 미착수. ★실측: BE 를 `e2e` 짝(`FRONTEND_URL=:3100`)으로 맞추니 `e2e chromium`·`e2e design-canon`·`e2e authed`·`BE pytest`·`CI fresh DB alembic` 은 통과하고 **화면 증거 팩(authed)만 전제 프로브에서 죽었다** — 「측정 서버: `http://localhost:3110` / BE 가 허용: (헤더 없음 — 거부)」. 그 레그 자체는 별도 실행으로 rc=0 을 여러 번 확인했다
**트리거 판정:** 도래 — 레그가 실재하고 충돌이 **종결 게이트 실행으로** 확인됐다 (2026-08-19 n6-authed-evidence)

---
