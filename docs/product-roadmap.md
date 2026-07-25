<!-- 남은 작업을 그룹별로 추적하는 living 체크리스트 — 매 세션 첫 step 에서 다음 후보 확인 + 완료 항목 체크 -->

# QuantBridge — 제품 로드맵 · 남은 작업 체크리스트 (Living)

> **용도.** 남은 작업을 그룹별로 추적하는 living 체크리스트. **매 세션 kickoff 시 이 문서에서 다음 후보를 고르고, 스프린트 완료 시 해당 항목을 체크**한다. 상세 8필드 = [`REFACTORING-BACKLOG.md`](REFACTORING-BACKLOG.md), 활성 sprint 상태 = [`TODO.md`](TODO.md), 회고 = [`dev-log/INDEX.md`](dev-log/INDEX.md).
>
> **최종 갱신:** 2026-07-25 (main @ #478 후). **상태 범례:** ✅ 완료 · 🔵 진행중 · 📋 계획됨(핸드오프 존재) · ⬜ 미착수 · ⏸ 보류(사용자/deferred).
>
> **동기화 규약.** BL Resolved 시 (1) REFACTORING-BACKLOG.md 에서 ✅ 마킹 (2) 본 문서 해당 체크박스 `[x]` + 스프린트/PR 표기. 신규 BL 등재 시 본 문서 해당 그룹에 1행 추가. 표류 방지 = 스프린트 마감 산출물 체크리스트에 "product-roadmap.md 갱신" 포함.

---

## 현황 요약

프로토타입 17벌 이식 완료(NOT-PORTED 0). **트레이딩/머니-패스 축은 6스프린트 연속 완주**(#472~#478: 코크핏 잔고/포지션 → TP/SL 열 → 청산 → closedPnl 손익 보정 → 청산 원장 → 세션 스코프 정정). 엔진(백테스트·트레이딩·옵티마이저·스트레스) 전부 작동. **backtest-trust(백테스트 숫자 신뢰도)는 진행중**. 남은 건 (a) 최근 트레이딩 스프린트가 남긴 **머니-패스 정확도 부채(실자금 전 필수)**, (b) 저우선 프로토타입/기능 잔여(대부분 P3·스키마 확장 선행), (c) 거래소 확장(OKX WS·풀 레버리지), (d) 사용자 결정 대기(Beta 배포)이다.

## 완료 (참고 — 최근 스프린트, 전량 MERGED)

| 스프린트                   | PR        | 한줄                                                                              |
| -------------------------- | --------- | --------------------------------------------------------------------------------- |
| C 디자인 언어 이식 완주    | #463/#464 | 17벌 전체 이식 + 리포트 정본 + 부채 마감                                          |
| functional-parity          | #468      | C 이식 후 기능 격차 마감 + 잠복 P1 2건                                            |
| tier-c                     | #469      | Tier C 4종 + WS Tier 1 (펀딩·포지션 대조·알림·팬아웃)                             |
| opspack-ws2                | #470      | 정비 팩 6종 + WS Tier 2 (public ticker·미실현 P&L)                                |
| perf-surface               | #471      | 성과 표면 A1~A4 (read-time 파생, 마이그레이션 0)                                  |
| position-cockpit (Phase B) | #472      | WS position 채널 + 코크핏 잔고/포지션                                             |
| trading-surface-pack       | #473      | 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 (BL-431/416/425/432/433)            |
| close-completeness         | #474      | 청산 즉시 flat + margin 503 회피 + 완전 TP/SL 보고 (BL-435/436)                   |
| money-path-accuracy        | #475      | 거래소 closedPnl 손익 보정 + filled_quantity 소생 + BL-362 텔레그램 (BL-014 부분) |
| exit-attribution           | #476      | 거래소 청산 원장 (최근 7일, BL-442)                                               |
| exit-money-path            | #477      | 세션 스코프 머니-패스 정정 (BL-444/445)                                           |
| (후속 픽스)                | #478      | 큰 배열 spread RangeError 공유 페이지 크래시 수정                                 |

## 🔵 진행중 / 📋 계획됨 (핸드오프 SSOT 존재)

| 항목               | 상태              | 핸드오프                                                                         | 스코프                                                                                                               |
| ------------------ | ----------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **backtest-trust** | ✅ 완료 (PR 대기) | `docs/backtest-trust/` (플랜 = `~/.claude/plans/backtest-trust-joyful-wirth.md`) | BL-398 Resolved + **BL-186a Resolved**(★TV/MT5 컨벤션 = 레버리지가 수량을 안 바꿈) + BL-388 Resolved. 마이그레이션 0 |

## ⭐ 권장 착수 순서 (제안 — Trust ≥ Scale · dogfood-first 기준)

1. 🔵 **backtest-trust** (진행중) — 매일 보는 백테스트 숫자 신뢰(Sharpe·레버리지 청산).
2. **머니-패스 정확도 마감 팩** (★강추 · 실자금 전 필수) — 최근 트레이딩 5스프린트가 남긴 정확도 갭. **BL-457**(청산 오보고 진행형·즉시) + **BL-446**(cumulative_loss 시간축/분모 오염) + **BL-458**(realized_pnl 추정↔확정 혼합) + **BL-454**(웹훅 심볼 정규화). 실자금 전환 전 반드시.
3. **거래소/엔진 확장** (택1) — BL-186b(cross+tiered+멀티거래소 풀 레버리지) 또는 BL-015(OKX Private WS).
4. **분석 표면 완결 팩** — BL-423(비활성 세션 진단) + BL-414(스트레스 이력) + BL-413(주문 상세) + BL-427/430(전략 목록 파라미터·정렬). 데일리드라이버 편의(스키마 확장 + P3).
5. **옵티마이저 파워업** — BL-236(objective 3→24) + BL-235(N-dim viz) + BL-364(categorical).
6. **tasks 도메인 deepen** (상시 가능 · 내부 부채) — money-path Celery 감사(`/deepen-modules`, codex 빌드 아님).
7. **Beta 배포** (사용자 결정 · 다음 단계) — G1 DB 호스팅 + BL-070~075.

---

## 1) 프로토타입 이식 잔여 (스키마/API 확장 선행)

- [ ] **BL-413** [P3] 주문 상세 조회 배선 — `GET /orders/{id}` 존재, 프로토타입에 행 확장/드로어 부재 · 선행: 상세 UI 캐논 추가
- [ ] **BL-414** [P3] 스트레스 테스트 이력 리스트 UI — `GET /stress-tests` 존재, 이력 화면 부재(최신 1건만) · 선행: 이력 화면 캐논 + 페이지 응답 캐시
- [ ] **BL-427** [P3] 전략 목록 파라미터 열 / 수명주기 칩 — `StrategyListItem` 스키마에 필드 부재 · 선행: BE 파라미터 요약·lifecycle 파생
- [ ] **BL-428** [P3] 트레이드 구간 미니차트 share 페이지 미지원 — `/trades/{i}/ohlcv` owner-authed 401 · 선행: token 공개 OHLCV 경로
- [ ] **BL-429** [P3] 대시보드 §03 최적화행 수익률/MDD `—` 고정 — best 조합 backtest metric 미보유 · 선행: denormalize
- [ ] **BL-430** [P3] 전략 목록 성과 정렬(수익률/샤프) 미제공 — latest_backtest 정렬 축 부재 · 선행: 서버 정렬 축 + FE SORT_OPTIONS

## 2) 기능 갭 (진짜 미구현)

- [ ] **BL-014** [P1] Partial fill 추적 — **부분 완료(#475: closedPnl overwrite + filled_quantity 4경로)** · 잔여 = per-execution ledger(BL-440)·cancelled 부분체결(BL-439)·entry warmup-replay(BL-441)
- [ ] **BL-015** [P1] OKX Private WS — OKX 어댑터 REST 만, WS 부재로 fetch_order polling 부담 · 선행: OKX WS signing(Bybit Demo 안정화 후)
- [x] **BL-186a** [P2] 레버리지 충실도 — ✅ **backtest-trust 완료**. ★TV/MT5 컨벤션(레버리지는 **수량을 바꾸지 않고** 필요증거금·청산가만 정함) → `compute_qty` 무변경 → 레버리지>1 에서도 TV parity 유지. 격리 청산 + 마진 게이트(단일 chokepoint) + FE 입력 재도입. L=1 byte-identical
- [ ] **BL-186b** [P2] cross/tiered MM + 파산수수료 + 멀티거래소 + 펀딩-청산 상호작용 — 186a 이후 이연
- [ ] **BL-460** [P2] 마진 게이트가 **gross 자본**으로 판정 — `running_equity` 가 수수료·슬리피지 차감 전이라(`close()` "fees=0 Sprint 37 가정") 실측 gross +38,679 vs net −53,670. 고치면 `compute_qty`·Pine `strategy.equity` 가 바뀌어 L=1 byte-identity 파괴 → 별도 설계 필요 · (실자금 레버리지 사용 전)
- [ ] **BL-461** [P3] `_periodic_returns` daily fallback 이 sub-daily 를 "1 bar = 1 day" 로 계산 — resample 부재. sortino 도 동일 영향이라 고치면 baseline 2 metric 확산
- [ ] **BL-462** [P3] Sharpe 목록 정렬 신·구 컨벤션 혼재 — `repository.py:75` 가 원시 JSONB 숫자만 캐스팅. 현재는 FE 고지로 대응, 완전 해소는 read-time recompute
- [ ] **BL-463** [P3] optimizer·stress_test 저장 sharpe 도 컨벤션 미표기 — 각자 JSONB 에 저장, 3 도메인 동시 마킹은 스코프 폭발로 이연

## 3) 리팩토링 부채 (80 OPEN · P0 1 / P1 6 / P2 26 / P3 47)

### P0

- [ ] **BL-003** [P0] Bybit mainnet 진입 runbook + smoke — IP whitelist·출금OFF·소액 체크리스트 · (H1 종료 직전)

### P1

- [ ] **BL-015** [P1] OKX Private WS — (그룹 2 참조)
- [ ] **BL-022** [P1] Golden expectations 재생성 — strategy.exit 지원 후
- [ ] **BL-023** [P1] KIND-B/C mutation 분류 정밀도 — xfail strict 해소
- [ ] **BL-024** [P1] real_broker E2E 본 구현 — nightly cron (Bybit Demo creds)
- [ ] **BL-025** [P1] autonomous-parallel-sprints 스킬 patch — BUG-1/2/3
- [ ] **BL-026** [P1] Mutation fixture 활성화 회귀 — skip #4-7,#9-15

### P2 — 머니-패스 정확도 (★실자금 전 필수)

- [ ] **BL-446** [P2] cumulative_loss 시간축 불일치 + 외부거래 분모 오염 — 전기간 누적/현재잔고 · (실자금 전 필수)
- [ ] **BL-457** [P2] classify_exit `ours` 가 실매칭 아님 — orderLinkId UUID 파싱만 · (★즉시, 오보고 진행형)
- [ ] **BL-458** [P2] 머니-패스 5곳 realized_pnl_synced_at 미구분 — 추정↔확정 혼합 합계 · (실자금 전)
- [ ] **BL-454** [P2] 세션 등록·TV 웹훅 심볼 미정규화 — 두 자유문자열 스코프 어긋남 · (TV 웹훅 실사용 시)
- [ ] **BL-451** [P2] 파괴적 마이그레이션 테스트 env 폴백 dev DB drop 위험 — (부분 완화 완료)

### P2 — 트레이딩/엔진 부채

- [ ] **BL-365** [P2] trigger_direction_for dead-code + 서버 미배선 — standalone-trigger 방향 · (standalone exit 도입 시)
- [ ] **BL-366** [P2] live-signal OrderService DI 인라인 중복 — HTTP factory drift
- [ ] **BL-368** [P2] \_merge_exit_params ccxt 키명 3 call site 누설
- [ ] **BL-369** [P2] 3 provider create_order try/except ~40 LOC 복붙
- [ ] **BL-372** [P2] STEP B 트레일링 live-placement follow-up (9항목) · (Wave 3 전)
- [ ] **BL-373** [P2] OCO 형제취소 — standalone exit 시점 · (BL-365 도입 시)
- [ ] **BL-375** [P2] trailing same-side stale 완전 닫기 — fill-time 소싱 · (Wave 3 전)
- [ ] **BL-387** [P2] sizing-canonical config_payload untyped dict seam · (backtest/sizing 변경)
- [ ] **BL-392** [P2] stress CA/PS 2D grid sweep DTO 8-site 통합
- [ ] **BL-363** [P2] stress*test \_execute*\* 4-method boilerplate 추출

### P2 — pine_v2 / Track A / 옵티마이저

- [ ] **BL-379** [P2] pine_v2 user-fn 지역변수 `x[1]` history=na
- [ ] **BL-380** [P2] Track A INFORMATION/UNKNOWN alert 무경고 drop
- [ ] **BL-381** [P2] Track A VirtualRunResult var_series/warnings 미반환
- [ ] **BL-382** [P2] qty=1.0 fallback sizing-source FE 미표면화
- [ ] **BL-393** [P2] pine_v2 strategy.exit trail_points 틱 시맨틱스 + mintick 하드코딩
- [ ] **BL-441** [P2] entry 부분체결 시 pine_v2 warmup-replay 사이즈 발산
- [ ] **BL-190** [P2] 백테스트 리포트 PDF export · (외부 인쇄 요청 시)
- [ ] **BL-195** [P2] qb-form-slide-down 애니메이션 truncation
- [ ] **BL-235** [P2] N-dim acquisition surface viz (Bayesian) · (Sprint 57+)
- [ ] **BL-236** [P2] objective_metric whitelist 자유화 (24+ 지표) · (Sprint 56+)
- [ ] **BL-364** [P2] Optimizer string-label CategoricalField sweep

### P3 — 문서 lint

- [ ] **BL-306** [P3] CLAUDE.md §5 한국어 콜론 종결 lint (181 위반, auto-fix)
- [ ] **BL-307** [P3] CLAUDE.md §6 한국어 file header lint + 70 file backfill

### P3 — pine_v2 엣지 / parity

- [ ] **BL-377** [P3] pine_v2 non-finite 주문/청산 가격 + OverflowError
- [ ] **BL-383** [P3] v2_adapter catch-all 런타임 예외 parse_failed 오분류
- [ ] **BL-384** [P3] ta.valuewhen na-source occurrence skip
- [ ] **BL-385** [P3] PineVersion enum v6 부재 → v5 collapse
- [ ] **BL-386** [P3] v4 bare math builtin floor/ceil/round/sqrt 미별칭
- [ ] **BL-399** [P3] ta.sar TV hand-oracle 부재
- [ ] **BL-406** [P3] DrFXGOD 잔여 미지원 builtin 5종
- [ ] **BL-409** [P3] pine_v2 워밍업 TV-parity 잔여 2건 (ta.ema 시딩 + bool[n])

### P3 — backtest 엔진 추출

- [ ] **BL-389** [P3] backtest finance-math 10함수 Deep Module 추출
- [ ] **BL-390** [P3] exit-leg maker/taker fill_type 라우팅 복제
- [ ] **BL-391** [P3] trades→equity→metrics reconciliation oracle 부재 (BL-389 묶음)

### P3 — 차트 일원화 / 리포트 UI

- [ ] **BL-394** [P3] BE 거래 분포/수익구조 집계 엔드포인트 (2000-cap 대체)
- [ ] **BL-395** [P3] lightweight-charts v5 업그레이드 spike (멀티-pane)
- [ ] **BL-396** [P3] /backtests/[id]/trades 서브페이지 TV 신규 컬럼 정렬
- [ ] **BL-397** [P3] 리포트 섹션 탭 URL 딥링크 `?section=`
- [ ] **BL-403** [P3] recharts↔lwc↔inline-SVG 차트 3원화 해소 (BL-395 후)
- [ ] **BL-408** [P3] 리포트/위저드 Precision Instrument 잔여물 팩 6건
- [ ] **BL-415** [P3] .field-error FieldError 3사본 공용 승격
- [ ] **BL-424** [P3] 대시보드 실현손익 카드 foot 미실현 부기 밀착

### P3 — vercel / FE·optimizer polish

- [ ] **BL-400** [P3] optimizer 쿼리 `enabled:userId` 가드 비일관
- [ ] **BL-410** [P3] FE vercel-react 감사 low 잔여 8건 (BL-408 묶음)
- [ ] **BL-412** [P3] optimizer result read-side 판별 유니온

### P3 — 진단/네비 (프로토타입 잔여와 중첩)

- [ ] **BL-423** [P3] 비활성(과거) 세션 진단 UI 부재
- [ ] (그룹 1 의 BL-413/414/427/428/429/430 참조)

### P3 — trading / live / money-path 하드닝

- [ ] **BL-367** [P3] \_async_dispatch_event 205 LOC + 8× mark_failed 추출
- [ ] **BL-370** [P3] exit-field multi-SSOT 8필드 × 3 boundary type
- [ ] **BL-371** [P3] ws-stream 고빈도 fill 스트레스 (orphan buffer cap 1000)
- [ ] **BL-420** [P3] WS 인바운드 서버 하드닝 (비인증 소켓 상한/rate-limit) · (Beta 전)
- [ ] **BL-426** [P3] ws_stream 워커 용량 정책 (멀티계정 starvation)
- [ ] **BL-437** [P3] 청산 스윕 — post-fill 세션 귀속 잔여 조건부 주문 자동취소
- [ ] **BL-439** [P3] 부분체결 후 cancelled 청산 실체결 손익 누락
- [ ] **BL-440** [P3] per-execution ledger(order_executions) — BL-014 원안 잔여
- [ ] **BL-447** [P3] exchange_order_id write `""`/`"None"` 저장
- [ ] **BL-448** [P3] WS replay_orphan 프로덕션 호출자 0 (dead code)
- [ ] **BL-449** [P3] Order.webhook_payload JSONB `'null'` 저장
- [ ] **BL-450** [P3] get_daily_summary 테넌트 스코프 없음 · (Beta 다사용자)
- [ ] **BL-452** [P3] 거래소 청산 원장 최근 7일만 (백필 불가)
- [ ] **BL-455** [P3] 수동 청산 LiveSignalEvent 미기록
- [ ] **BL-456** [P3] 세션 창 filled_at 반열림 늦은 체결 오귀속
- [ ] **BL-459** [P3] 세션 읽기↔주문 조회 TOCTOU

> **그룹3 미포함(상태 note):** BL-388(#391 완료→backtest-trust close) · BL-362(✅#369 완료) · BL-398/BL-186a(backtest-trust 계획됨).

---

## Beta · Deferred (사용자 결정 / 다음 단계 — 전량 미착수)

> 코드로 종결 불가(사용자 manual/의지 게이트). SSOT = [`refactoring-backlog/_deferred.md`](refactoring-backlog/_deferred.md).

### 그룹 4 — Beta 본격 진입 (사용자 manual · deploy-time)

- [ ] **G1 DB 호스팅 재결정 (USER-DECIDE · ★최대 blocker)** — TimescaleDB Cloud SQL 미지원 → self-host CE / TimescaleDB Cloud / Fly Postgres 택1
- [ ] **BL-070** 도메인 + DNS + (옵션) Cloudflare — 1-2h + 전파 24h
- [ ] **BL-071** Backend 프로덕션 배포 — Cloud Run/Railway/Render + Postgres/Redis prod + Clerk production + gunicorn 보안헤더
- [ ] **BL-072** Resend 이메일 + Waitlist 활성화 — 1-2h + verify 24h
- [ ] **BL-073** Twitter/X #buildinpublic 캠페인 — (BL-070~072 후 trigger)
- [ ] **BL-074** Beta 인터뷰 3명 × 3회 — (BL-073 후 + onboarding 후)
- [ ] **BL-075** H2 진입 게이트 설계 — (BL-005 self-assess ≥7 직후)

> ★ BL-070/071/072 상호 의존 → **번들 처리 필수**. Trigger = BL-005 self-assessment ≥7/10 + 본인 의지 second gate.

### 그룹 5 — Deferred (조건 충족 시 부활)

- [ ] **BL-005** 본인 실자본 1~2주 dogfood — Trigger: BL-001~004 완료 + self-assess ≥7 + 본인 의지
- [ ] **BL-145** EffectiveLeverageEvaluator (Cross Margin aggregation) — H1→H2 prereq

### 즉시 이월 (다음 단계 후보)

- [ ] **tasks 도메인 deepen** — 최대 미감사 4,098 LOC (trading.py + live_signal.py, money-path Celery). Iron Law = 새 세션
- [ ] **verification-loop 브랜치 종결** — `docs/verification-loop-2026-06-30` (origin 푸시됨, PR 미생성)
