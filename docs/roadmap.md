<!-- 남은 작업을 그룹별로 추적하는 living 체크리스트 — 매 세션 첫 step 에서 다음 후보 확인 + 완료 항목 체크 -->

# QuantBridge — 제품 로드맵 · 남은 작업 체크리스트 (Living)

> **용도.** 남은 작업을 그룹별로 추적하는 living 체크리스트. **매 세션 kickoff 시 이 문서에서 다음 후보를 고르고, 스프린트 완료 시 해당 항목을 체크**한다. 상세 8필드 = [`backlog.md`](backlog.md), 활성 sprint 상태 = [`status.md`](../.ai/templates/docs/status.md), 회고 = [`dev-log/INDEX.md`](dev-log/INDEX.md).
>
> **최종 갱신:** 2026-07-28 (**live-outcome-parity 완료** — **BL-526 Resolved**. 라이브 실적을 엔진이 그때 기대한 값과 나란히 놓고 격차를 [체결 격차 / 비용] 두 층으로 쪼개는 read-time 파생 표면. 마이그레이션 0 · 새 엔진 코드 0. 실측 왕복 실효 비용률 **0.1115%** 가 BL 이 물었던 0.11% 문턱과 일치했고, **화면은 아직 답을 말하지 않는다**(표본 9 < 필요 30 이라 성과 비율 차단). ★게이트가 전부 green 인데 **화면을 열자 기능에 도달할 수 없었다**. ★G6 를 **세 번** 돌렸고 2·3차가 앞선 수정이 만든 새 P1 을 잡았다. 신규 BL-527~530.)
>
> **동기화 규약.** BL Resolved 시 (1) REFACTORING-BACKLOG.md 에서 ✅ 마킹 (2) 본 문서 해당 체크박스 `[x]` + 스프린트/PR 표기. 신규 BL 등재 시 본 문서 해당 그룹에 1행 추가. 표류 방지 = 스프린트 마감 산출물 체크리스트에 "product-roadmap.md 갱신" 포함.

---

## 현황 요약

프로토타입 17벌 이식 완료(NOT-PORTED 0). **트레이딩/머니-패스 축 8스프린트 연속 완주**(#472~#481: 코크핏 잔고/포지션 → TP/SL 열 → 청산 → closedPnl 손익 보정 → 청산 원장 → 세션 스코프 정정 → 백테스트 숫자 신뢰 → 머니-패스 정확도 마감). 엔진(백테스트·트레이딩·옵티마이저·스트레스) 전부 작동.

**머니-패스 정확도 팩은 사실상 닫혔다** — 잔여는 BL-446 1건뿐이고 실측 여유가 임계 10% 대비 54,117배다. 남은 건 (a) 저우선 프로토타입/기능 잔여(대부분 P3·스키마 확장 선행), (b) 거래소 확장(OKX WS·풀 레버리지), (c) 사용자 결정 대기(Beta 배포)이다.

### ★새로 드러난 갭 — 로컬 앱이 지금 "실사용 불가" 상태다 (로드맵에 없던 항목)

실측(2026-07-26 #481 머지 후) — `strategies` **0** · `backtests` **0** · `orders` **0** · `live_signal_sessions` **0** · **`ts.ohlcv` 0행**. 캔들이 없으니 백테스트를 아예 돌릴 수 없고, 원커맨드 복원 경로도 없다(OHLCV 수집은 Celery 태스크로만 존재, `run_auto_dogfood.py` 는 시더가 아니라 pytest 시나리오 러너).

그래서 **최근 3스프린트(#477·#480·#481)가 모두 "실화면 dogfood 미실행" 으로 닫혔다.** 세 스프린트 분량의 신뢰 작업이 **우리가 직접 쓴 테스트로만** 검증돼 있다 — `.ai/common/global.md` §7.3 이 금지하는 circular oracle 에 빈 DB 가 구조적으로 몰아넣는 상황이다. 과거 dogfood 는 실제로 진짜 P1 을 잡았다(#476 StrEnum 크래시 · #468 잠복 2건 · #480 마진 게이트 gross 자본). **dogfood-first 원칙 대비 이게 현재 최대 리스크다.**

## 완료 (참고 — 최근 스프린트, 전량 MERGED)

| 스프린트                   | PR        | 한줄                                                                                                                 |
| -------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------- |
| **live-entry-parity**      | #493      | 조건부 진입 거절 43% → **0%**. 기준가 stale close → 실시간 perp last + 돌파 시 시장가 전환 (BL-511/512)              |
| **live-outcome-parity**    | (PR 대기) | 라이브가 백테스트대로 **버는지** 물을 수 있는 자. 엔진 기대 gross → 체결 격차 → 비용 → 거래소 확정 net 분해 (BL-526) |
| live-observability         | #492      | worker Prometheus metric 스크레이프 배선 + 라이브 실주행 판정표 (BL-506)                                             |
| live-ops-hygiene           | #491      | 조건부 진입 정리 주체 + 계정 스코프 위생 (BL-503/501/502)                                                            |
| C 디자인 언어 이식 완주    | #463/#464 | 17벌 전체 이식 + 리포트 정본 + 부채 마감                                                                             |
| functional-parity          | #468      | C 이식 후 기능 격차 마감 + 잠복 P1 2건                                                                               |
| tier-c                     | #469      | Tier C 4종 + WS Tier 1 (펀딩·포지션 대조·알림·팬아웃)                                                                |
| opspack-ws2                | #470      | 정비 팩 6종 + WS Tier 2 (public ticker·미실현 P&L)                                                                   |
| perf-surface               | #471      | 성과 표면 A1~A4 (read-time 파생, 마이그레이션 0)                                                                     |
| position-cockpit (Phase B) | #472      | WS position 채널 + 코크핏 잔고/포지션                                                                                |
| trading-surface-pack       | #473      | 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 (BL-431/416/425/432/433)                                               |
| close-completeness         | #474      | 청산 즉시 flat + margin 503 회피 + 완전 TP/SL 보고 (BL-435/436)                                                      |
| money-path-accuracy        | #475      | 거래소 closedPnl 손익 보정 + filled_quantity 소생 + BL-362 텔레그램 (BL-014 부분)                                    |
| exit-attribution           | #476      | 거래소 청산 원장 (최근 7일, BL-442)                                                                                  |
| exit-money-path            | #477      | 세션 스코프 머니-패스 정정 (BL-444/445)                                                                              |
| (후속 픽스)                | #478      | 큰 배열 spread RangeError 공유 페이지 크래시 수정                                                                    |
| backtest-trust             | #480      | Sharpe TV 컨벤션 + 격리 레버리지 마진·청산 (BL-398/186a/388)                                                         |
| money-path-finish          | #481      | 원장 실측 매칭 + 심볼 ingress 정규화 + 출처 라벨 (BL-457/454 · 458 부분 · 464)                                       |

## 🔵 진행중 / 📋 계획됨 (핸드오프 SSOT 존재)

| 항목                            | 상태 | 핸드오프 | 스코프                                |
| ------------------------------- | ---- | -------- | ------------------------------------- |
| _(없음 — 활성 핸드오프 문서 0)_ |      |          | 다음 후보는 아래 §권장 착수 순서 참조 |

## ⭐ 권장 착수 순서 (제안 — Trust ≥ Scale · dogfood-first 기준)

1. ✅ **backtest-trust** (완료 · PR #480 머지) — 매일 보는 백테스트 숫자 신뢰(Sharpe·레버리지 청산).
2. ✅ **머니-패스 정확도 마감 팩** (#481 완료 — BL-457/454 Resolved · BL-458 부분 · 신규 BL-464 Resolved). **잔여 = BL-446 1건**(cumulative_loss 시간축/분모 오염 — 구조 결함이지만 실측 여유 54,117배).
3. ✅ **dogfood 복원 + 누적 신뢰 작업 실화면 검증** (dogfood-restore 완료 — `make seed` 신설 · BL-465/467 Resolved · 신규 BL-466/468~472). **★dogfood 가 또 P1 을 잡았다** — 파산한 계좌(총수익률 -2179.68%)에 **양수 샤프 +0.029** 가 붙고 있었고 **Trust Layer baseline 이 그걸 담고 있었다**. **실주문 부분 완주** — 데모 실체결 + 심볼 정규화 실경로 확인. ★키 만료 진단은 **오진**이었고 진짜 원인은 WS `expires` 창(BL-473). **잔여였던 출처 라벨·SessionScope 화면 검증은 PR #484 에서 완료** — 추정값 주입으로 혼재 상태 포착 + 독립 raw-HMAC 오라클 3중 일치.
4. ✅ **live-entry-wiring** (완료 · **PR #486 머지** — **BL-478 (c)** 세션 시작 차단 + evaluate 자동 종료, **BL-479** 자본 기준선 스냅샷 + 사이징 배선). 사용자 결정 = **(c)**. 실주문 3중 대조로 종단 확인(손계산 = DB = 거래소 `0.029 Filled`, 실집행 $1,870 vs 미배선 $64,484). 신규 BL-481~485. **잔여였던 BL-478 (a) 는 #489 에서 Resolved.**
   4b. ✅ **live-engine-parity** (완료 · **PR #487 머지 @840b1259**) — `run_live` 인자 4종 패리티(BL-481/482/483/486/487). ★"화면 총계" 검증은 실제로 **DB 상태 행**이었다(최종 리뷰가 반박). 신규 BL-488~491.
   4c. ✅ **live-conditional-entry** (완료 · **PR #489 머지 @30031efe**) — **BL-478 (a) Resolved** 선언적 reconcile 로 조건부 진입 등재. 데모 실체결 5건 3중 대조. 최종 codex 리뷰가 4세션 연속 P1 적발(계정 공유 시 남의 포지션까지 반전). 신규 BL-492~500.
   4d. ✅ **live-conditional-hardening** (완료 · **PR #490 머지 @9ec56e89**) — **BL-498 Resolved**(활성 세션 0건에서도 잔여 포지션 표시·청산) · **BL-500 Resolved**(거래소 부재가 로컬 행을 이긴다 — 후보마다 `fetch_order` 로 terminal 확인 후에만 제거. ★**나이 게이트 3분은 폐기했다** — reconcile 은 bar 마다 돌아 게이트가 늘 열려 있었고 `submitted_at` 은 부재의 나이가 아니다) · **BL-499 부분 완화**(패자 분류 metric, 근본 경합은 열림). ★preflight 결론이 **틀렸음을 codex 가 반박**(성공 경로와 시도 횟수 혼동). ★e2e 가 **dev 서버 stale CSS 로 거짓 red**. 신규 BL-501/502/503.
   4e. ✅ **live-ops-hygiene** (완료 — **BL-503 Resolved**(조건부 진입 janitor 신설, **거래소에 물어본 뒤에만** 처분 · 세션 활성 여부 무관 · reject 는 CAS) · **BL-501 Resolved**(uid 표시 전용 접기 + readOnly 이중 차단 + 형제 캐시 무효화, **마이그레이션 1**) · **BL-502 Resolved**(포지션 단위 공유 lock) · **BL-499 열림 — 실관측 0건**). ★★★**게이트가 전부 green 인 상태에서 P1 3건** — 거래소 오라클(Bybit 이 `orderId` 우선 → 살아 있는 주문을 미발주로 오판) · 변이 주입(**거짓 게이트 3건**) · codex 최종 리뷰(**접기가 hedge 실포지션 leg 은폐**). ★★**내 F-A 결론이 거래소에 반증**(codex 도 같은 오답 — 둘 다 내부 증거만 봐서 독립 표본이 아니었다). ★**화면 검증이 P1 을 통과시켰다**(dogfood 계정이 one-way 단일 leg). **Generator/Evaluator 파이프라인 1/3 검증** — 변이 28건 전건 판별. 신규 BL-505/506/507.
5. **거래소/엔진 확장** (택1) — BL-186b(cross+tiered+멀티거래소 풀 레버리지) 또는 BL-015(OKX Private WS).
6. **분석 표면 완결 팩** — BL-423(비활성 세션 진단) + BL-414(스트레스 이력) + BL-413(주문 상세) + BL-427/430(전략 목록 파라미터·정렬). 데일리드라이버 편의(스키마 확장 + P3).
7. **옵티마이저 파워업** — BL-236(objective 3→24) + BL-235(N-dim viz) + BL-364(categorical).
8. **tasks 도메인 deepen** (상시 가능 · 내부 부채) — money-path Celery 감사(`/deepen-modules`, codex 빌드 아님).
9. **Beta 배포** (사용자 결정 · 다음 단계) — G1 DB 호스팅 + BL-070~075.

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
- [ ] **BL-463** [P3] optimizer·stress_test 저장 sharpe 도 컨벤션 미표기
- [x] **BL-465** [P1] `_periodic_returns` 음수 자본 미차단 → 파산한 실행에 양수 샤프 — ✅ **dogfood-restore 완료**. 신규 마커 `unavailable_nonpositive_equity` + Trust Layer baseline 재생성(2/12 키 한정)
- [ ] **BL-466** [P2] 레버리지 1 백테스트가 자본을 무제한 음수로 몰 수 있다 — 마진 게이트 no-op(설계) + 청산 없음. 실측 초기자본 21.8배 손실
- [x] **BL-467** [P1] `backend-optimizer-heavy` OHLCV env 3종 부재로 **모든 optimizer 실행 실패** — ✅ **dogfood-restore 완료**
- [ ] **BL-468** [P3] `OHLCV_FIXTURE_ROOT` CWD 상대 기본값 + `FixtureProvider` 가 canonical 슬래시 심볼 미지원
- [ ] **BL-469** [P3] `market_data.backfill_ohlcv` celery 미등록 + docstring 실행법 부존재(dead)
- [ ] **BL-470** [P2] 캐논 감사 9건이 빈 DB 에서 조용히 통과(데이터 전제 부재)
- [ ] **BL-471** [P3] `exchange_exits` row_hash 멱등 → 분류 로직 변경 시 기존 행 재분류 경로 부재
- [ ] **BL-472** [P3] 백테스트 목록이 monthly/daily 컨벤션 각주 미표기
- [x] **BL-473** [P1] Bybit private WS 인증 `expires` 창 +1s 가 왕복 지연에 먹혀 **라이브 체결 스트리밍이 죽어 있었다** — ✅ **dogfood-restore 완료**. 통제 실험(+1s 실패 / +10s·+60s 성공)으로 격리, 10s 로 확대
- [x] **BL-474** [P2] 테스트 주문 다이얼로그가 **spot** 으로 나가는데 라이브 신호는 **linear perp** — ✅ **PR #484**. ★원인은 다이얼로그가 아니라 **webhook ingress 한 자리에서 3건 드롭**(leverage/margin_mode 미해결 + 프론트가 보내던 `reduce_only`·TP/SL 미독). `WebhookService.resolve_trading_params()` 신설 + settings 미설정 **422 fail-closed**. 실주문 dogfood 로 확인(주문 ID 숫자형→UUID). **출처 라벨·SessionScope 화면 검증도 여기서 완료** — 각자 JSONB 에 저장, 3 도메인 동시 마킹은 스코프 폭발로 이연

## 3) 리팩토링 부채 (80 OPEN · P0 1 / P1 6 / P2 26 / P3 47)

### P0

- [ ] **BL-003** [P0] Bybit mainnet 진입 runbook + smoke — IP whitelist·출금OFF·소액 체크리스트 · (H1 종료 직전)

### P1

- [x] **BL-478 (c) ✅ Resolved** [P1] ★**라이브 자동매매가 진입 주문을 낸 적이 없었다** — (c) 세션 시작 차단 + evaluate 자동 종료로 해소. **(a) 조건부 주문 등재는 열려 있다** — `run_live` 가 `fill` 을 dispatch 제외하면서 "broker 가 자체 처리" 를 전제하는데 그 stop 주문을 거래소에 올린 적이 없다(`live_signal.py` 에 `trigger_price` 참조 0건). 청산만 나가 매번 110017. **`stop=` 진입 전략 한정**(시드 `s1_pbr` 이 100% 이 경로) · 회고 = [`dev-log/2026-07-26-live-entry-wiring.md`](dev-log/2026-07-26-live-entry-wiring.md)
- [x] **BL-479 ✅ Resolved** [P1] 라이브 사이징 미배선 — `run_live` 가 사이징 인자 없이 `run_historical` 호출 → `compute_qty()` 항상 `1.0`(1 BTC ≈ $64,000). `position_size_pct` 는 라이브에서 **아무 데서도 안 읽힘**(유일 소비처가 백테스트 어댑터). Pine `default_qty_type` 선언조차 무시 · **BL-478 과 함께**

- [x] **BL-486 ✅ Resolved** [P1] 라이브 사이징 equity 의 창 드리프트 — carry(`live_signal_events` 를 `bar_time < window_start` 로 자른 합)를 `initial_capital` 에 접고, **화면 총계는 원장 SSOT**(`sum_realized_pnl_all`)로 바꿔 창과 무관한 단조 값으로 만들었다. `equity_curve` 는 새 close 이벤트에만 append. 프로덕션 실증 = 화면 3건 `4.78803856` vs 원장 4건 `5.88683554` → 한 tick 만에 **바이트 동일**. ★**사이징 자본의 D2 일시 함몰은 남는다 → BL-489**
- [x] **BL-483 ✅ Resolved** [P1] `leverage` 라이브 마진게이트 배선 + **무음 skip 표면화** — `entry_skips` 구조화 6지점(margin / non_finite_qty / pyramiding_cap / session_closed) + `qb_live_signal_entry_skipped_total`(divergence 아님) + 화면 행. ★배선이 켠 것은 게이트만이 아니었다 — `check_liquidations` 도 살아나 **실제 reduce-only 주문을 내는 머니-패스**라 청산 표면화를 함께 넣었다. cross 증거금 모델 부재는 **BL-490**
- [x] **BL-481 / BL-482 ✅ Resolved** [P2/P3] `sessions_allowed` · `pyramiding` 라이브 배선 — ★`sessions_allowed` 는 넘기기만 하면 **조용한 no-op** 이었다(라이브 프레임이 `RangeIndex` + `timestamp` 컬럼). tz-aware 인덱스 복원 + fail-closed 로 수리하고 SSOT 불변식 감사를 **5계층**으로 확장했다
- [x] **BL-488 ✅ Resolved** [P1] ★평가 갭이 orphan close 를 만든다 — 원인은 beat 가 아니라 `run_live` 의 마지막-bar 발행 계약이었다(실측 갭 131바 중 수면 76 + 배포 50, 서버 기전은 4바). `emit_from_bar_time` opt-in + 벽시계 상한 + resync + close 포지션 가드. 프로덕션에서 resync 발동 관측 · 회고 = [`dev-log/2026-07-27-live-conditional-entry.md`](dev-log/2026-07-27-live-conditional-entry.md) ~~ — 워커가 252 바 중 180 바만 평가(50분 구멍)했고, 구멍에 빠진 진입은 발주된 적 없는데 그 청산은 발주돼 `reduce_only` 주문이 `rejected`. 시뮬은 거래소가 준 적 없는 `+4.87330864` 를 이익 계상했다. 갭 감지 + 재동기화 설계 필요
- [ ] **BL-015** [P1] OKX Private WS — (그룹 2 참조)
- [ ] **BL-022** [P1] Golden expectations 재생성 — strategy.exit 지원 후
- [ ] **BL-023** [P1] KIND-B/C mutation 분류 정밀도 — xfail strict 해소
- [ ] **BL-024** [P1] real_broker E2E 본 구현 — nightly cron (Bybit Demo creds)
- [ ] **BL-025** [P1] autonomous-parallel-sprints 스킬 patch — BUG-1/2/3
- [ ] **BL-026** [P1] Mutation fixture 활성화 회귀 — skip #4-7,#9-15

### P2 — 머니-패스 정확도 (★실자금 전 필수)

- [ ] **BL-446** [P2] cumulative_loss 시간축 불일치 + 외부거래 분모 오염 — 전기간 누적/현재잔고 · (실자금 전 필수)
- [x] **BL-457** [P2] classify_exit `ours` 가 실매칭 아님 — ✅ **money-path-finish 완료**. 계정 스코프 실재 확인(`list_existing_ids`, state 무필터) + 미확인 UUID 는 `unknown`. 부수 이득 = 버려지던 TP/SL·청산 유래 부활
- [~] **BL-458** [P2] 머니-패스 5곳 realized_pnl_synced_at 미구분 — 🟡 **money-path-finish 부분 완료**. Site 3(알림)·Site 4(커브·KPI) 라벨+소계. **Site 1·2 게이트와 Site 5 는 의도적 혼재 유지**(확정만 좁히면 fail-open) · 병합 커브는 포인트별 출처 표현 불가 → 집계 라벨
- [x] **BL-454** [P2] 세션 등록·TV 웹훅 심볼 미정규화 — ✅ **money-path-finish 완료**. `NormalizedSymbol` 공용 프리미티브 + 두 ingress + 거부 관측. ★의도된 동작 변경 = 활성 세션 유니크 충돌(KPI 이중 계상 차단)
- [x] **BL-464** [P2] `attribute_exit` 이 거래소 원문↔canonical 심볼 비교로 `inferred` 귀속 구조적 사망 — ✅ **money-path-finish 완료**(신규 발견). ★픽스처 기본값이 한 스프린트 동안 가렸다
- [ ] **BL-451** [P2] 파괴적 마이그레이션 테스트 env 폴백 dev DB drop 위험 — (부분 완화 완료)

### P2 — 트레이딩/엔진 부채

- [ ] **BL-476** [P2] 공개 webhook 핸들러 동기 CCXT 왕복 3회 — **+4.8초 실측**(mark 1663 · min-notional 1549 · balance 1600). ★게이트는 provider stub 이라 영원히 0ms — 프로덕션에서만 보이는 회귀. 가드를 Celery 경계 뒤로 옮기는 건 **거부 시점이 응답 뒤로 밀리는 계약 변경**
- [x] **BL-365 ✅ Resolved** [P2] `trigger_direction_for` dead-code + 서버 미배선 — 진입 전용 `entry_trigger_direction` 신설(long breakout=1 RISE / short breakdown=2 FALL). 청산 side 기준 역시맨틱을 재사용하면 정반대가 나온다
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

- [ ] **BL-475** [P3] 서버 권위 risk% 사이징 미구현 — UI 문구는 정정했고(PR #484) risk% 는 실제 동작대로 **상한**으로 재정의. 진짜 수량 산출은 미착수
- [ ] **BL-477** [P3] API 키 2개가 같은 Bybit 서브계정 → 청산 원장 2행 적재 + 유령 `unknown`. **선재**, 금액은 안전(`aggregate_closed_pnl` 계정 스코프). 읽기 전용 계정 삭제 시 자연 소멸
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

> 코드로 종결 불가(사용자 manual/의지 게이트). SSOT = [`refactoring-backlog/_deferred.md`](archive/refactoring-backlog/_deferred.md).

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

- [ ] **tasks 도메인 deepen** — 최대 미감사 **6,342 LOC** (2026-07-28 실측; `trading.py` 1,910 + `live_signal.py` 1,877, money-path Celery). ★기재됐던 4,098 은 **55% 낡은 값**이었다. Iron Law = 새 세션
- [ ] **verification-loop 브랜치 종결** — `docs/verification-loop-2026-06-30` (origin 푸시됨, PR 미생성)
