# QuantBridge — TODO

> **Last Updated:** 2026-07-26 (dogfood-restore 스프린트 — 로컬 실사용 복원 + 누적 신뢰 작업 실화면 검증)
> **Active Sprint:** **dogfood-restore** — `make seed` 신설 + 3스프린트 누적 신뢰 작업 실화면 검증 + 발견 결함 수정
> **Active Branch:** `stage/dogfood-restore` (main @ `0f84d51` 베이스)

## ⚡ dogfood-restore 스프린트 (2026-07-26)

**스코프**: #477·#480·#481 이 전부 **실화면 dogfood 없이** 닫혔고(07-25 DB 전소로 `ts.ohlcv` 0행 → 백테스트 불가), 세 스프린트 분량 신뢰 작업이 우리가 쓴 테스트로만 검증돼 있었다 — §7.3 이 금지하는 circular oracle. (A) 복원 경로 + (B) 실화면 검증 + (C) e2e 소생. 마이그레이션 **0**.

### ★§0.5 실측이 킥오프 전제를 3건 정정했다

```
"authed 13 spec 실패" = 파일 수를 테스트 수로 오독. 실제 = 13파일/64테스트 중
  하드 실패 6, 나머지 57 은 page.route 목킹이라 빈 DB 에서도 통과.
  ★진짜 문제는 따로 — 캐논 감사 9건이 StateBox 만 감사하며 조용히 통과(BL-470).

복원은 거의 공짜 — TimescaleProvider 가 cache-first + live CCXT fill 이라
  백테스트 1회가 곧 시딩. 실측 9,337행 · 갭 0.

프로즌 픽스처는 현재 경로에서 도달 불가 — FixtureProvider 가 canonical
  `BTC/USDT` 의 슬래시를 경로로 해석(BL-468).
```

### ★★워커가 구 코드였다 — 그래서 legacy 행이 공짜였다

착수 시 `quantbridge-worker` 가 `b97ac57`(#480) **8시간 전** 이미지로 돌고 있었다(§7.2 위반). 덕분에 **조작 0의 진짜 pre-#480 행**을 얻었다 — 계획했던 "`metrics` 에서 마커만 SQL 로 제거" 는 오히려 **부정직**했다(신 컨벤션 숫자에 구 기준 각주가 붙는다). 순서가 비가역이라 legacy 를 먼저 돌리고 워커를 bind-mount 로 교체했다(재빌드 0).

### ★★dogfood 가 P1 을 잡았다 — 파산한 계좌에 양수 샤프

`_periodic_returns` 가 `prev == 0` 만 막고 **`prev < 0` 을 안 막아** 자본이 음수면 부호가 뒤집힌다 → **더 잃을수록 수익률이 양수**. 실측 = 10,000 → **-207,968**(총수익률 **-2179.68%**) 실행의 월간 수익률 13개 중 11개가 양수, **샤프 +0.029**. BL-398(#480)이 없애려던 거짓말의 다른 얼굴(그쪽은 수식, 이쪽은 분모 부호).

**★committed Trust Layer baseline 이 이걸 담고 있었다** — `s1_pbr` baseline 샤프 **+0.600** · 소르티노 **+2.349**(총수익률 -536%). 코퍼스 5종 중 4종이 음수 자본이고 **골든이 깨진 것도 정확히 그 4종**(거래 0인 `i2_luxalgo` 만 무관). baseline 재생성 diff = **12 메트릭 키 중 2개**(sharpe/sortino)·해당 4종 한정, `ohlcv_sha256` 불변.

### Completed

- [x] **S0 환경** — `docker builder prune -f`(8.9G→12.9G) · **`ts.ohlcv` hypertable 복구**(dev DB 만 평범한 테이블이었다, test DB 는 정상 = 07-25 사고 잔재. 0행이라 무료) · BE 8100 기동
- [x] **S1 `make seed`** — `backend/scripts/seed_dogfood.py`. **실 서비스 계층 + 실 Celery** 경유(HTTP/auth 만 우회 — clerk SDK 가 `azp` 클레임을 필수로 요구해 헤드리스 HTTP 시딩이 구조적으로 불가). 함정 3종을 상수로 박음(canonical `BTC/USDT` · 격자 정렬 UTC · `exchange` NOT NULL). **멱등**
- [x] **S2 커버리지** — 전략 3 / 백테스트 6 / 거래 3,194 / OHLCV 9,337 / optimizer 1. 샤프 4상태 전부 + 100x 청산 503
- [x] **S3 외부 오라클 대조**(엔진 미개입) — 샤프 **양 컨벤션 독립 재계산 일치**(구 수식 6.66e-16, 신 수식 1.5e-05) · legacy↔monthly **에쿼티 9,337 포인트 바이트 동일**(격차 42배가 전부 컨벤션) · 청산수 **엔진 503 = trades 테이블 503**, 1x 대조군 0 · 청산가 **롱 최대 0.995000 / 숏 최소 1.005000 = 손수식 정확 일치**(유리한 체결 0건)
- [x] **S5 결함 수정 4건** — **D1** 샤프 raw 렌더 **5곳**(계획은 4곳, CSV export 를 놓쳤다) → `describeSharpe` 경유 + 소스 스캔 가드 · **D2** 전체 원장 청산 사유 열(리포트 미리보기는 최신 25건 한정이라 503 청산이 안 보였다) · **BL-465** 음수 자본 가드 · **BL-467** optimizer-heavy OHLCV env
- [x] 게이트: BE **3005**(+5) · FE **1125**(+1) · ruff/mypy/tsc/lint 0 · **canon 32 불변** · build ok · **마이그레이션 0**
- [x] **e2e:authed 65 passed / 0 failed** — 빈 DB 하드 실패 6건 전부 초록
- [x] 실브라우저(MCP Playwright) — 전략목록 degenerate `—` · 목록 5행 각 컨벤션 각주 · **혼재 정렬 고지 발화** · 전체 원장 "청산 사유" 열 · 콘솔 error 0

### ★사용자가 알아야 할 것

**Bybit demo API 키가 죽었다.** ws-stream 실측 — `00:45:02Z ws_stream_auth_failed … Params Error` → `ws_circuit_opened`(1h). 시계 드리프트는 배제(호스트·컨테이너·Bybit 서버 시각 일치). **키 재등록 전까지 S4(실주문 머니-패스 dogfood)는 불가** — #481 출처 라벨과 #477 SessionScope 는 여전히 화면 미검증이다.

### ★S4 실주문 — 진단 정정 + 부분 완주

**"키 만료" 진단이 틀렸다.** 독립 HMAC 오라클로 REST 를 치니 **양쪽 키 모두 `retCode 0`**(자산 846,921.08). 진짜 원인은 **우리 WS 인증 `expires` 창이 +1s** 라 왕복 지연에 먹힌 것(**BL-473 Resolved**, 통제 실험 +1s 실패 / +10s·+60s 성공). 사용자에게 불필요한 키 재등록을 시켰다. 새 키는 `readOnly: 1` 로 생성돼 거래 불가였고 기존 키로 진행했다.

**검증됨** — Bybit 데모 **실주문 체결**(독립 오라클로 거래소 확인) · **BL-454 심볼 정규화 실경로 작동**(다이얼로그 `BTCUSDT` → `Order.symbol` canonical `BTC/USDT`) · 라이브 신호 경로 종단(`live_signal_events` dispatched + 주문 연결 + pine_v2 추정 손익) · **D3 수정 화면 확인**(`API 422 …` → `Cannot normalize symbol: BTCUSDT.P`).

**★신규 발견 BL-474** — 테스트 주문 다이얼로그는 `has_leverage=false` 라 **spot** 으로, 라이브 신호는 `true` 라 **linear perp** 로 나간다. 청산 원장·코크핏은 linear 만 보므로 **이 도구로 머니-패스를 dogfood 하면 조용히 아무것도 검증하지 못한다.**

### Blocked

- **출처 라벨(#481)·SessionScope(#477) 화면 검증** — linear perp 체결이 청산까지 가야 확정/추정이 섞인다. 라이브 세션은 1분마다 평가 중이나 PbR 피벗 신호 미발생(`events_inserted: 0`). 시드로 만들면 조작이라 하지 않음

### Next Actions

- [x] **PR [#482](https://github.com/woosung-dev/quantbridge/pull/482)** `stage/dogfood-restore` → main — **squash 는 사용자**
- [ ] **다음 세션 = [`docs/dogfood-restore/checklist.md`](dogfood-restore/checklist.md)** — 사용자 확정. (A) **BL-474** 테스트 주문 다이얼로그가 spot 으로 나가는 것 먼저 → 고치면 perp 진입→청산을 결정적으로 만들 수 있어 **출처 라벨·SessionScope 화면 검증이 열린다** (B) pine_v2 시뮬 상태 ↔ 거래소 포지션 발산 조사(`retCode 110017`, 수량 1.0 사이징 미반영 의혹 포함)
- [ ] (선택) 최종 codex 누적 diff 리뷰

---

## ⚡ money-path-finish 스프린트 (2026-07-26, `docs/money-path-finish/`)

**스코프**: 트레이딩 6스프린트(#472~#478)가 남긴 **숫자 정확도 부채**. 로드맵 권장 착수 순서 #2. 마이그레이션 **0**.

### ★§0.5 실측이 전제를 2건 정정하고 결함 1건을 새로 찾았다

```
BL-457 의 "새 쿼리 불필요" 는 틀렸다 — attribution_facts 는 limit=500 + state==filled 로
좁혀졌고 실재 확인이 필요한 행은 정의상 filled 매칭 실패 행이다 → 재사용하면 진짜 우리
청산이 external 로 뒤집힌다. 백로그 본문의 그 권장 접근을 제자리에서 정정했다.

format:check 는 이 레포의 통과 가능 게이트가 아니다 — main 에서 이미 356 파일 red.
lint-staged 가 FE TS 에 eslint 만 돌려서 드리프트가 누적된 구조다(package.json:14-26).

★신규 BL-464 — attribute_exit 이 order.symbol(BTC/USDT)을 snapshot.symbol(BTCUSDT)과
비교해 inferred 귀속이 구조적으로 죽어 있었다. 픽스처 기본값이 우리 canonical 로
위장돼 한 스프린트 동안 안 보였다.
```

### Completed

- [x] **S1 BL-464** — `_order_facts` + `attribute_exit` 호출 양쪽 `to_bybit_raw_symbol` 정렬. C-red 로 죽은 축을 **테스트로 증명**한 뒤 green. `normalize_symbol` 미사용 이유 = raise 시 계정 원장 적재 전체 손실
- [x] **S2 BL-457** — `classify_exit(known_order_ids)` **필수** + `list_existing_ids`(술어 2개 · **state 무필터**) + 분기 8 신규(`unknown` — 사람은 UUID4 를 타이핑하지 않는다) + 메트릭 2 + 경고 로그. 부수 이득 = **버려지던 TP/SL·청산 유래 부활**
- [x] **S3 BL-454** — `src/common/normalized_symbol.py` 공용 프리미티브(선례 `strict_decimal_input.py` 미러) + 두 ingress + **거부 + 관측**(장식 제거 추측 금지). 순수 이동 증명 = `test_constants.py` **git diff 0 통과**
- [x] **S4 BL-458 부분** — Site 3 `realized_pnl_split_for_session`(PG `FILTER` 5 스칼라, 개명·retype 으로 "출처 안 보고 합산" 표현 불가화) + 한국어 알림 본문 + Site 4 포인트별 `source` + 평면 소계 4필드
- [x] **S5·S6 FE** — zod strip 가드 **선행** + 집계 `number|null`(부분 분할 금지) + 세션 상세 칩 + KPI foot + carry-forward 출처 동반 + 차트 per-point color(**미지정 시 출력 불변** 증명)
- [x] 게이트: BE **3000**(+28) · FE **1124**(+9) · ruff/mypy/tsc/lint 0 · **canon 32 불변** · build ok · **마이그레이션 0**
- [x] 검증: codex G0 **BLOCKING 0 · P1 4 · P2 1** → 전건 코드 대조(**P2 수용** — context 는 5키가 아니라 6키이고 인용 테스트는 두 값만 단정 / **P1-4 절반 기각** — 신규 nullable 과 기존 non-null 을 혼동) + `/vercel-react-best-practices`(줌-리셋 함정 재발 없음 확인, 지적 1건 수정)

### ★사용자가 알아야 할 의도된 동작 변경 1건

정규화로 `BTCUSDT` 와 `BTC/USDT` 가 한 문자열로 붕괴해 `uq_live_sessions_active_unique` 에서 **충돌**한다 — 예전 201 이던 등록이 4xx 가 된다. 그게 대시보드 §01 KPI 이중 계상의 원인이었으므로 수정의 요점이다. `live_signal_sessions` 0행이라 배포 시 위반도 백필도 없다.

### Questions

- 화면 종단 dogfood 는 `orders`/`sessions` 0행이라 seed 없이 불가 — 실주문이 필요하면 사용자 요청 선행 [확인 필요]

### Next Actions

- [ ] `stage/money-path-finish` → main PR (squash 는 사용자)

---

## ⚡ backtest-trust 스프린트 (2026-07-26, `docs/backtest-trust/`)

**스코프**: 라이브 머니-패스 5스프린트(#474~#478) 완주 후, 이번엔 **백테스트가 화면에 내놓는 숫자**. **BL-398**(Sharpe TV 컨벤션) + **BL-186a**(레버리지 충실도) + **BL-388**(SSOT close). 마이그레이션 **0**.

### ★§0.5 실측이 전제를 3건 뒤집었다

```
핸드오프 경로 2건 오류(engine/ vs pine_v2/) · BL-388 은 "24필드 4-site" 가 아니라 48필드 전 차집합 공집합(이미 해결)
BL-398 "FE 가 (bar 기준) 라벨로 고지 중" → 그 문자열은 없다. 실제 각주는 "무위험 수익률 0% 가정"(RFR 2% 도입 즉시 거짓)
BL-186a "M" → 실제 L — FE 폼에 레버리지 입력이 아예 없어(Sprint 37 BL-187 이 제거) 엔진만 고치면 도달 경로 0
```

### ★★사용자 결정이 설계를 뒤집었다 — TV/MT5 컨벤션

핸드오프는 "사이징 × leverage" 였으나 사용자가 TV 정렬을 지시했고, 1차 출처 조사 결과 **곱하기 모델은 업계 어디에도 없었다**(TV=`margin_long/short` %, MT5=계좌 레버리지→필요증거금, QC=`SetLeverage`=매수여력 상한. 거래소 UI 조차 곱하는 대상은 _증거금_ 입력). → **레버리지는 주문 수량을 바꾸지 않는다.**

이 전환이 설계를 **줄이면서 강하게** 만들었다 — `compute_qty` 무변경 → 레버리지>1 에서도 **TV parity 유지**, 마진 게이트가 부가기능이 아니라 **레버리지의 작동 기제 자체**, "사이징+청산 원자성" 우려 소멸.

### Completed

- [x] **B1 BL-398** — `metrics.py` 에 TV 컨벤션 `sharpe_ratio()`(달력월 + RFR 2%, 모집단 SD, 연율화 없음) + `_periodic_returns` 3-tuple 확장 + `_sharpe` 제거 + **`sharpe_convention` 마커 4종**(4-site 동시) + FE `sharpe-convention.ts` SSOT + 렌더 3곳 + **혼재 정렬 고지**
- [x] **B1 랭킹 flip 실측(의무)** — 15셀. **argmax FLIP** · Kendall τ **0.6381** · 11/15 셀 2계단 이상 이동. ★결정적 증거 = `s2_utbot@0.005` 가 **자본 38배 손실(−3837%)에 구 수식이 양수 샤프 +0.3955** 를 줬다 → 신 −0.0757
- [x] **B2 BL-186a** — `leverage_model.py`(순수 수식) + **단일 chokepoint `_open_trade()`**(마진 게이트 + 청산가) + `check_liquidations()` + 배관 4층 + **양 루프**(Track S/M + A) + `RawTrade.liquidated` → metrics 4-site → DB `exit_kind='liquidation'` + FE 레버리지 입력 재도입 + 고지 5종
- [x] **B3 BL-388** — 이미 해결 상태 확인 후 close + micro-tripwire 2 + stale 주석 정정(숫자 재기입 금지)
- [x] 게이트: BE **2968**(+251) · FE **1113**(+16) · ruff/mypy/tsc/lint 0 · **canon 32 불변** · build ok · **마이그레이션 0**
- [x] 검증: codex G0 **BLOCKING 1 + P1 3 + P2 3**(전건 코드 대조 → 5 수용/2 이미반영) → **설계 결함 적발**(마진 게이트를 `entry()` 에만 걸면 `check_pending_fills` 의 직접 `Trade` 생성 경로로 뚫림 → chokepoint 통합) → 슬라이스별 게이트 **평가자 직접 실행**
- [x] **dogfood** — 엔진: Sharpe 손오라클 일치 · 청산 1x=0/25x=8/100x=267(**metrics·RawTrade·comment 3중 일치**) · 마진 게이트가 corpus 내재 **4.2x** 판정(3x 거부/10x 통과) · L=1 byte-identity 5 corpus. 실브라우저: 레버리지 배너 파생값 산술 정확(4.0%/3.50%) · 고지 7종 · **콘솔 0**

### ★발견 — 마진 게이트는 gross 자본으로 판정한다

`running_equity` 가 수수료·슬리피지 차감 전이라(`close()` 의 "fees=0 Sprint 37 가정"), `s1_pbr` 에서 gross **+38,679** 인데 net 은 **−53,670**(차이 약 92,000). 게이트가 실제 순자산이 깊은 마이너스일 때도 증거금 충분으로 본다. **선재 구조**이고 고치면 `compute_qty`·Pine `strategy.equity` 가 바뀌어 L=1 byte-identity 가 깨진다 → **배너에 명시 고지 + 후속 BL**. 단 **초기 판정은 정확**(초기 자본은 gross=net).

### Questions

- authed e2e 7건 실패는 **빈 DB**(strategies=0/backtests=0) 때문 — 코드 회귀 아님(로케이터 타임아웃으로 판별). 전략·백테스트 데이터 복원은 스코프 밖 [확인 필요]
- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 [확인 필요]

### Next Actions

- [ ] 최종 codex 누적 diff 리뷰
- [ ] 백로그 갱신(BL-398/388 Resolved · BL-186 부분) + 신규 BL(BL-186b · 마진게이트 net 자본 · `_periodic_returns` sub-daily fallback · Sharpe 목록 read-time recompute · optimizer/stress sharpe 혼재)
- [ ] `stage/backtest-trust` → main PR (squash 는 사용자)

---

## ⚡ exit-money-path 스프린트 (2026-07-25, `docs/exit-money-path/`)

**스코프**: exit-attribution(#476) 후속. **BL-444(P1) + BL-445(P2)** — 라이브 세션 손익을 읽는 두 소비처가 서로 다른 행 집합을 세면서 둘 다 "이 세션의 손익" 이라고 주장하던 것을 **하나의 스코프 정의**로 통일한다. 마이그레이션 **0**.

### ★§0.5 측정이 스코프를 확정했다

```
trading.orders 0 | live_signal_sessions 0 | live_signal_events 0 | strategies 0
소비처 5곳 전부: 0행 위에서 0 합산
원장: ours/none 3 · external_manual/none 1 · bracket/trailing/liquidation 0행
      matched_order_id NOT NULL = 0 · attributed_strategy_id NOT NULL = 0
```

- **BL-438 ② 는 스코프 밖** — 귀속 등급이 `exact`(0행)·`inferred`(투입 금지)뿐이라 남는 건 `none` = 귀속 불가. **미룬 게 아니라 현재 데이터로는 정직하게 구현 불가**다.
- **BL-444 본문의 규모 근거는 재현 불가**(DB 전소 이전 데이터) → 이 PR 은 **코드 경로 논증**에 근거한다고 명시.

### Completed

- [x] **Slice 0 대조군** — `test_session_scope_money_path.py`. 세션 3개 + 주문 11건, 손익을 2의 거듭제곱으로 심어 **어떤 부분합도 유일**. ★**프로덕션을 `git stash` 로 되돌려 before 값 5 passed 를 확인해 판별력을 실제로 증명**한 뒤 after 로 뒤집었다
- [x] **Slice 1** — `SessionScope`(frozen, 생성 경로 `from_live_session` 하나) + `_session_scope_where`(SQL 번역 단일 지점) + 개명 2건, 구 메서드 삭제
- [x] **Slice 2a** — `router.py` Site 4 배선 + 라우터 종단(인접 세션 2개가 서로 다른 커브)
- [x] **Slice 2b** — `alert_rules.py` Site 3 배선 + **알림 문구 2곳 정직화**(event-join 서술이 거짓이 됨) + 신규 실 DB 태스크 테스트(이벤트 있는 −5 만 세면 5.00% 미발화, 수동 청산 −7 포함 시 12.00% 발화 → 판별)
- [x] **Slice 3** — BL-453 부분: 코드베이스 마지막 `.value` 잔존 제거 + StrEnum **6필드**(감사 누락분 `attribution_confidence` 포함) 주석 통일
- [x] 기존 테스트 3파일 갱신 + 개명 잔존 참조 전수 grep(코드 0건)
- [x] 게이트: ruff 0 / **mypy 203 files Success** / **FE 1094 = baseline 정확 일치**(FE 변경 0)
- [x] 검증: Plan 압박검증 반론 4건 **전건 코드 대조**(1건은 과장으로 정정) → codex G0 **REVISE [P1] 2건**(둘 다 코드 확인 후 수용, 1건은 codex 가 말한 것보다 나빴다) → fixture 기대값 10건 독립 산술 검증
- [x] BL: **BL-444/445 Resolved** · **BL-453 부분** · **BL-438 ② 재분류** · 신규 **BL-454~458** · active 카운트 산식 헤더 고정(49 → 실제 81)

### ★인프라 사고 2건 (코드 무관, 시간을 가장 많이 먹었다)

1. **3-env 미export** — 셸에 env 가 없어 conftest 가 `localhost:5432` 로 폴백 → 400+ 에러. `set -a; source backend/.env.local; set +a` 필수(3개를 통째로).
2. **Docker VM 디스크 100% 포화** — Postgres 가 `PANIC: could not write ... No space left on device` 로 **무한 크래시-복구 루프**. 호스트는 49Gi 여유였으나 Docker Desktop VM 이 58.4G 중 0. **빌드 캐시만** 정리(10GB 회수) → 복구, 데이터 무손실. ★볼륨(33GB)·이미지는 건드리지 않았다 — 캐시는 재생성되지만 볼륨은 아니다(BL-451 전력).

### Next Actions

- [ ] BE 전체 스위트 재확인 — `test_redis_client.py::test_get_pool_safe_across_event_loops` 가 전체 실행에서만 1회 실패(단독·clean main 모두 통과). 순서 의존 flake 여부 판정 중
- [ ] canon 32 + MCP Playwright 브라우저 회귀 dogfood(콘솔 error 0 · 빈 상태 `—` · state shape 불변)
- [x] 최종 codex 누적 diff 리뷰 — **REVISE [P2] 1건**(TOCTOU) → 전건 대조 후 회귀 아님 판정, BL-459 등재
- [x] **PR [#477](https://github.com/woosung-dev/quantbridge/pull/477)** — squash 는 사용자

---

## exit-attribution 스프린트 (2026-07-25, `docs/exit-attribution/`) — 완료 · main @ `0a8e229` (#476)

**스코프**: money-path-accuracy(#475) 후속. **BL-438 부분** — 거래소에만 존재하는 청산 기록을 원장으로 흡수해 보이게 만들고, 우리 주문의 손익만 계상한다. 마이그레이션 **1**(`20260725_0002`, 신규 테이블 1개 — 과거 스캔 경계 테이블은 머지 전 범위 축소로 제거).

### ★§0.5 측정 스파이크가 전제를 뒤집었다

독립 오라클 실측(계정 `0f666fae`, 07-01~07-25) — closed-pnl **11행** 중 우리 매칭 7 / **거래소 전용 4**(행 36.4% · |손익| **55.8%**). 머니-패스가 보는 합은 거래소 확정 총합의 **10.4%** 뿐이고 잔여는 고아 55.8% + 07-05 시뮬 오차 33.8% 로 정확히 닫힌다.

- **거래소 전용 4행은 브래킷이 아니다** — 전부 `createType=CreateByUser`·`orderLinkId` 없음 = 앱 밖 수동 청산.
- **브래킷 체결 전 기간 0건** — 조건부 주문 4건 전부 `Deactivated`, DB 17행 중 TP/SL/트레일링 실은 주문 **0**. 경로는 살아 있으므로 잠복 구멍.
- **거래소 전용 4행 중 우리 포지션은 1건뿐** — 전량 자동 계상하면 남의 거래로 우리 전략을 차단한다.

### Completed

- [x] **S1 provider** — `ClosedPnlSnapshot` 9필드 확장(위치 인자 하위호환) + `fetch_closed_pnl_window`(7일 상한 강제) + 심볼리스 열거(계정당 1콜) + `fetch_closed_order_meta`(`fetch_closed_orders`, UTA 대응) + **페이징 커서 createdTime 축 교정** + 기존 3필드 strict 파싱 복원
- [x] **S2 원장** — `trading.exchange_exits`(행 단위 원본 + provenance JSONB `none_as_null`) + `compute_row_hash`(제어문자 구분자 · `None`/`""` 동일 정규화 · 빈 order_id 거부) + 리포지토리(청킹·집계)
- [x] **S3 스윕 재작성** — 계정 독립 열거 + **최근 7일 1창** + 조건부 보강(정상 상태 0콜) + **원장 전체 집계 백필** + 커밋 후 계상 + 알림 1회성 + `orphan_row` 계상 제거
- [x] **S4 분류·귀속** — classification 7종(`stopOrderType` 폴백 · `orderLinkId` UUID 검증) + attribution 3등급(두 조건 AND) + `qb_exchange_exit_rows_total`. **`inferred` 는 머니-패스 미투입**(검정력 없음)
- [x] **S5 FE** — `displayRealizedPnl`/`isPartialFill`/`realizedPnlSource` SSOT + 체결 전 주문 손익 은닉 + 사유 title + CSV 3열 복원
- [x] **안전** — `_assert_disposable_database`(파괴적 마이그레이션 테스트가 `_test` 아닌 DB 향하면 `RuntimeError`) + 스키마 열거 센티널 9→**10**
- [x] **S6 범위 축소 (머지 전)** — 과거 90일 catch-up 기계장치 제거(워터마크 테이블·창 전진·잘림 처리). **실측 = 그 기계장치는 ~13주기(65분) 후 영구 자기정지하는 일회성 catch-up 이었다** → 정상 상태 동작은 축소 전후 동일, 실제 소멸분은 일회성 역사 수입 하나. 원장은 **최근 7일만** → BL-452. 잘림은 발생 지점 로그(계정 식별자)로 대체
- [x] 게이트: BE **2706** / FE **1094**(미변경) / ruff·mypy·tsc·lint 0 / alembic 왕복 + head `20260725_0002` / 마이그레이션 신규 테이블 **1개**
- [x] 검증: codex G0 **REJECT**(전건 대조 후 절반 수용, "계정 단위 열거 불가" 는 **실측 반박**) → Explore 3-리더(핸드오프 좌표 **3건 반박**) → **Plan 압박검증이 내 설계 결함 적발**(원장 min 파생 워터마크가 빈 창에서 영구 정지 → 실측 시각 시뮬레이션으로 반증·재검증) → 사용자 인터뷰 **10건** → codex 4워커 ↔ **Claude 적대평가 4기**(BLOCKING 4 + MAJOR 4, **내가 넣은 회귀 1건**(`row_hash` 가 `None`/`""` 를 다르게 봐 손익 2배 백필) 포함 전건 수정 + 회귀 테스트) → 최종 codex 누적 diff **DO-NOT-SHIP 2**
- [x] **축소 후 최종 codex 재실행 = P1 1건 추가** — `fetch_closed_pnl_window` 커서가 `oldest_ms - 1` 이라 **같은 createdTime 을 공유하는 분할 행**(구분은 updatedTime)이 페이지 상한을 넘으면 조용히 누락되고 부분합이 `realized_pnl` 로 영구 고정. 경계 포함(`until = oldest_ms`)으로 수정 + 중복은 원장 UNIQUE 흡수 + 회귀 테스트(구 커서로 red 실증)
- [x] BL: **BL-438 부분 Resolved**(관측 원장 **최근 7일**) · **BL-442 Resolved** · 신규 **BL-443~453**
- [x] **dogfood 완주** — 사용자가 Bybit demo 계정 재등록 후 독립 오라클(raw HMAC) 실측 = 원장 적재와 **완전 일치**(4행, 합계 −0.12392537). 분류(3 ours·1 external_manual)·멱등·알림 1회성·§9.5 라이브 worker·authed(`/orders` 5/5 green) 전부 실 계정으로 검증. 백필 종단 검증은 주문 이력 소실로 여전히 불가(정직 각주).
- [x] **★dogfood 가 진짜 P1 을 하나 더 잡았다** — `_alert_new_exchange_exits` 가 원장을 새 세션으로 재조회하면 `classification` 컬럼이 평문 `str` 로 와서(`ExitClassification` StrEnum 재캐스팅 안 됨) `.value` 접근이 `AttributeError` → 신규 미귀속 행 알림이 매 사이클 조용히 죽고 있었다. `str()` 로 수정 + 실 DB 회귀 테스트(커밋 후 `expire_all()` 로 강제 재조회) + 재검증(`alerted:1` 확인). 같은 패턴 4개 필드 감사 → 실제 크래시 사이트는 이 한 곳뿐, 예방 등재 BL-453
- [x] **§7.2 sentinel 이 stale 워커를 실제로 검출** — 재빌드 전 이미지가 `78ceadd` 시점에 baked 되어 있었다(제거 심볼 3종 잔존)

### Questions

- ★**사고 기록** — 적대 평가 서브에이전트에 `DATABASE_URL`(개발 DB)만 export 한 셸을 주었고 거기서 `pytest tests/test_migrations.py` 가 돌아 `downgrade base` 로 **개발 DB 가 전소**했다. 주문 17행 · 거래소 계정(암호화 API 키) · 전략 6종 Pine 소스 소실. 주문 17행 SQL 스냅샷만 남았으나 부모 행이 없어 단독 복원 불가. 가드는 넣었고([BL-451](REFACTORING-BACKLOG.md#bl-451)) 잔여는 **로컬 DB 주기 백업 부재** [확인 필요]
- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [x] 사용자: 거래소 계정 재등록 → dogfood 8단계 완주
- [x] 최종 codex 누적 diff 리뷰 — **DO-NOT-SHIP 2 + MAJOR 1 + MINOR 1 전건 수정**(원장 우회 CAS · max_pages 소진 · malformed 미계상 · downgrade 인덱스) + 축소 후 재실행 **P1 1건**(커서 tie 누락) 추가 수정
- [x] canon 32 / authed `/orders` / §9.5 라이브 worker 검증 — 전부 green
- [x] **PR [#476](https://github.com/woosung-dev/quantbridge/pull/476)** stage/exit-attribution → main 사용자 squash — **머지 완료 @ `0a8e229`**
- [x] 다음 세션 = BL-438 잔여 → **exit-money-path 로 착수**(② 는 §0.5 실측으로 스코프 제외, BL-444/445 로 재조준)

---

> **Sprint type (exit-attribution):** 머니-패스 관측 (마이그레이션 **1**) — §0.5 측정 스파이크가 전제 3건 반박 + codex G0 REJECT→§7.3 전건 대조 + Explore 3-리더 + **Plan 압박검증이 내 설계 결함 적발** + 사용자 인터뷰 10건 + codex 4워커 ↔ Claude 적대평가 4기(BLOCKING 4/MAJOR 4) + ★로컬 개발 DB 전소 사고 대응
>
> **Sprint type (money-path-accuracy, 완료):** 머니-패스 정확도 (마이그레이션 **1**) — codex G0 REJECT→§7.3 전건 코드 대조 후 절반 수용/절반 실측 반박 + Explore 3-리더 grounding + Plan 압박검증(설계 결함 R1) + 사용자 인터뷰 11건 + codex 3-pass 워커(be 2 / fe 1) ↔ Claude 적대평가 per-worker(게이트 직접 실행, **프로덕션 파손 2건 발견**) + 최종 codex 누적 diff(**DO-NOT-SHIP 2 BLOCKING**) + 실자금 데이터 dogfood
> **office-hours 진행:** N
> **Next Trigger:** money-path-accuracy 머지 후 → **BL-438**(거래소 네이티브 TP/SL 청산 손익 미계상, P1) 또는 다음 deepen = tasks 도메인. // 사용자 manual = G1 (TimescaleDB↔DB 호스팅) + BL-070~072 → 실 prod 배포.

## ⚡ money-path-accuracy 스프린트 (2026-07-25, `docs/money-path-accuracy/`)

**스코프**: close-completeness(#474) 후속. ① **BL-014 부분** — `Order.realized_pnl` 이 close 주문 _생성 시점_ pine_v2 시뮬레이션 값(수수료 0·바 종가·전량청산 가정)이고 체결 후 보정이 없었다. 머니-패스 5곳(Kill Switch 2 · 세션 에쿼티 커브 · loss-limit 알림 · 일일 보고)이 이 값을 SUM 하므로 **리스크 게이트가 시뮬레이션으로 작동**했고, `close_service` 의 수동 청산은 아예 NULL 이라 5곳 전부에서 보이지 않았다 → Bybit `/v5/position/closed-pnl` 의 `closedPnl`(net) 로 reduce-only 체결분 overwrite + `realized_pnl_synced_at` 출처 마커 + 4 winner 공용 backfill task + beat 스윕 ② dead 컬럼 `filled_quantity` 를 4 체결 경로 전부에 write + `qb_partial_fill_total` + API/블로터 노출 ③ **BL-362** 발산 알림 Slack→Slack+Telegram(raw 예외 문자열은 호출부에서 제거). **마이그레이션 1**(`20260725_0001`, 순수 증분).

### Completed

- [x] **B1 BL-014(부분)** — `fetch_closed_pnl`/`fetch_closed_pnl_page`(ccxt `fetch_positions_history`, `info.closedPnl` 원본 문자열→Decimal, 분할 행 합산, malformed 행 skip+계상) + `realized_pnl_synced_at` 컬럼 + `backfill_exchange_realized_pnl`(non-optional Decimal · 3-guard 멱등 CAS) + `trading.refresh_closed_pnl`(4 winner 공용 helper, 5/10/20/40s 재시도, 실패 시 기존값 보존이 **구조적 보장**) + `trading.sweep_closed_pnl`(beat 5분, 그룹당 provider 1콜, 뒤로 훑는 페이징, orphan 카운터)
- [x] **B1 filled_quantity** — `OrderReceipt` += 필드 + 4 create_order 구현 + 4 체결 winner write(WS 는 Bybit 원본 `cumExecQty`, reconciler 는 ccxt 통합 `filled`) + `qb_partial_fill_total{source}` + `OrderResponse` 3필드 + 주문 원장 **10→12열** + 손익 출처 배지
- [x] **B2 BL-362** — `send_rule_alert(channel=both)` 라우팅 + 외곽 try/except 유지 + `run_live_error` raw 제거(호출부) + `backend/.env{,.prod}.example` TELEGRAM\_\*
- [x] 게이트: BE **2653**(+42)·FE **1088**(+4)·ruff/mypy/tsc/lint 0·**canon 32 불변**·alembic 왕복+base 체인+드리프트 0·마이그레이션 **1**
- [x] 검증: codex G0 **REJECT**(§7.3 전건 대조 → "부분체결→취소 누락" BLOCKING 은 **실측 반박**(청산은 전부 시장가 → `PartiallyFilledCanceled`→ccxt `closed`→우리 `filled`), "BL-362 이미 Resolved" 는 오독) → Explore 3-리더 + Plan 압박검증(**설계 결함 R1** = 마커 컬럼 없이는 스윕 종료 불가 → 마이그레이션 0→1) → 사용자 인터뷰 **11건** → codex 워커 3-pass ↔ **Claude 적대평가**(BE **인도 시점 FAIL** — `since` 창이 ccxt `filter_by_since_limit` 에 걸려 대상 행을 버림 / malformed 행이 페이지 전체를 죽임) → 최종 codex 누적 diff **DO-NOT-SHIP 2 BLOCKING**(스윕이 분할 행을 마지막 하나로 축약 / 단일 페이지 조회로 오래된 행 영구 누락) 전건 수정
- [x] **dogfood — 새 거래 없이 실자금 데이터로 종단**: 07-24 수동 청산 3건(`realized_pnl=NULL`)이 오라클 closed-pnl 행과 1:1 매칭 → 백필 후 `-0.04524449`/`-0.08623685`/`0.08781055` **오라클 완전 일치** · 스윕 run1 `{scanned:3,applied:3}` → run2 `{0,0}` **멱등** · **라이브 worker §9.5**(같은 child 4 task 연속 성공 + beat 자체 발화 + NULL 되돌린 행 회수) · Kill Switch SUM `42.4607`→**`42.41703`** 이동 실증 · authed 브라우저 12열+배지+**콘솔 0**+가로스크롤 false · **BL-362 텔레그램 실수신**(`{'slack': False, 'telegram': True}` — ★`SLACK_WEBHOOK_URL` 미설정이라 **이전엔 발산 알림이 아무에게도 도달하지 않았음** 확인)
- [x] BL: **BL-014 부분 Resolved** · **BL-362 Resolved** · 신규 **BL-438~442**

### Blocked

- 없음.

### Questions

- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [ ] stage/money-path-accuracy → main PR 사용자 squash
- [ ] (후속·P1) **BL-438** 거래소 네이티브 TP/SL 청산 손익 미계상 — 브래킷 익절 손익이 리스크 게이트에 안 잡힌다. ★첫 step = 구멍 규모 측정 스파이크(현 `orphan_row` 는 스윕 후보가 우리 미동기화 주문이라 steady state 에서 0 으로 읽히는 하한선)
- [ ] (이월) 다음 deepen = tasks 도메인
- [ ] ★환경 함정: codex 샌드박스가 localhost:5436 을 막아 워커는 DB 테스트를 못 돌린다 — **전체 스위트는 평가자가 직접** 돌릴 것

---

## ⚡ close-completeness 스프린트 (2026-07-25, `docs/close-completeness/`)

**스코프**: trading-surface-pack(#473) 후속. ① **BL-435** 청산 즉시 flat — post-fill Celery 캐시 DEL(accept-time DEL 은 async close 라 무효; `_execute_with_session` reduce_only fill 승자 → 활성 세션 캐시 DEL, SSOT 키 헬퍼) ② **BL-436** 청산 margin 503 회피 — `create_order` reduce_only 시 set_margin_mode/set_leverage skip(ccxt marginMode 신뢰불가 우회) ③ **BL-434 부분** 완전 TP/SL 보고(display) — `fetch_open_conditional_orders`(2콜 union+orderId dedupe+stopOrderType 엄격분류) → §03 병합 리스트(익절/손절 plural)+has_trailing_stop 각주; **스윕 BL-437 이연** ④ hedge positionIdx 409 가드. 마이그레이션 0.

### Completed

- [x] **B1 BL-435** — `position_snapshot_cache_key` SSOT(3곳) + tasks/trading.py `_execute_with_session` reduce_only fill 승자 → `list_active_by_account` 세션 캐시 best-effort DEL
- [x] **B2 BL-436** — `create_order` set_margin_mode/set_leverage 를 `if not order.reduce_only:` 로 감쌈(fast-fail 불변, reduce_only 이미 Order 영속=마이그레이션 0)
- [x] **B3 BL-434(부분)** — `fetch_open_conditional_orders` provider + `ConditionalOrderSnapshot` + PositionSnapshot(position_idx/trailing_stop) + position_service 조인(병합 리스트 source-dedup·마크근접순) + ExchangePositionSchema plural(BE+FE 미러) + FE 병합 표시·각주 + close_service hedge 409 가드
- [x] 게이트: BE **2611**(+10)·FE **1084**(+1)·ruff/mypy/tsc/lint 0·canon **32 불변**·마이그레이션 0(alembic 20260724_0002 head 무변경)
- [x] 검증: codex G0 **REJECT**(전건 코드 대조 §7.3 후 개정 = B2 skip·B1 post-fill·B3 union dedupe·trail=position 필드·hedge 가드) → 사용자 재인터뷰(스윕 이연·트레일링 각주) → codex 2워커 ↔ Claude 적대평가 per-worker(W1 ruff B023×3+mypy → codex resume hoist `_merged_prices`) → codex 최종 diff **[P1] 1**(has_trailing_stop 조건부 trail → `or any(kind=="trail")`+테스트) → **dogfood 3계통**(독립 오라클 raw ↔ 앱 provider(66000/62000 분류·count=2 dedupe) ↔ get_reconciliation 병합=익절['66000.0']/손절['62000.0'] + **authed 브라우저**(§03 병합·청산 flat·콘솔 0) + B1 redis 키 부재 + B2 no-503 + Bybit Partial 자동취소=스윕 이연 안전)
- [x] BL: BL-435/436 Resolved + BL-434 부분 Resolved + 신규 **BL-437**(스윕 이연)

### Blocked

- 없음.

### Questions

- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [ ] stage/close-completeness → main PR 사용자 squash
- [ ] (후속) BL-437 청산 스윕(post-fill flat 확인 + orderLinkId 세션 귀속)
- [ ] (이월) 다음 deepen = tasks 도메인
- [ ] ★환경 함정: docker db/redis 5436/6380 커스텀 오버레이 — worker 재빌드 시 `--no-deps` 필수(plain `docker compose up <svc>` 이 base 5432/6379 로 되돌림)

---

## ⚡ trading-surface-pack 스프린트 (2026-07-24, `docs/trading-surface-pack/`)

**스코프**: position-cockpit(#472) 후속. ① BL-431 코크핏 §03 포지션 표 **TP/SL 열**(거래소 보고 포지션-부착, 0→— 정직) + **reduce-only 시장가 청산**(세션스코프 `POST /live-sessions/{id}/positions/close` 202, `OrderService.execute(flatten=True)` 진입-위험 가드 ②~⑧ bypass·ownership 유지·청산 leverage=포지션값) ② BL-416 주문취소 polish ③ BL-425 alert 409 콘솔 노이즈 ④ BL-432 select→combine ⑤ BL-433 subscribe-reject metric. 마이그레이션 0.

### Completed

- [x] BL-431 BE — PositionSnapshot/ExchangePositionSchema TP/SL 2필드(0/''→None) + 신규 `close_service.py`(canonical settings 검증·hedge/no-position 409·demo·bybit) + `close` 엔드포인트(202 ClosePositionResponse) + `execute(flatten=True)` 가드 bypass(reduce_only 불변식) + dependencies 배선
- [x] BL-431 FE — §03 익절/손절 2열 + 청산 액션열(colSpan 14) + 확인 모달(reduce-only 시장가·계정 순포지션·재진입 정직 고지) + `useClosePosition`(pending 행별 disabled) + demo 계정 게이팅 + 각주(포지션-보고값)
- [x] BL-416 — `cancelOrder.variables===o.id` 행별 disabled + 비-409 broad toast + 실 ACTIVE_ORDER_STATES import
- [x] BL-425 — alert-rule 사전 중복검사(마운트 목록 재사용, 409 요청·콘솔 노이즈 회피, broad allowlist 없음)
- [x] BL-432 — positions select→combine 인덱스 zip + 고아 삭제 / BL-433 — `qb_ws_subscribe_rejected_total{account_id}` counter
- [x] 게이트: BE **2601**(+18)·FE **1083**(+8)·ruff/mypy/tsc/lint 0·canon **32**·authed **66**(+2 §03 구조)·build ✓·마이그레이션 0(alembic 무변경)
- [x] 검증: codex G0 **14건**(코드 대조 후 반영·BLOCKING 3=leverage 라우팅·flatten 불변식·hedge 거부) → codex 2워커 생성 ↔ Claude 적대평가 per-worker(게이트 직접 실행·W1 RUF059 codex resume) → 최종 codex diff **MAJOR 1**(청산 leverage cap-bypass → 포지션값 사용 fix) → **Opus dogfood 2계통**(독립 Bybit HMAC 오라클 ↔ 코크핏 §03 TP/SL 66000/62000 일치·빈값→— 정직 / 청산 종단 flat+Order row / **kill-switch 활성 청산 성공=bypass 실증·KS 미소비** / 콘솔 error 0)
- [x] BL: BL-431/416/425/432/433 Resolved + 신규 BL-434~436

### Blocked

- 없음.

### Questions

- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [ ] stage/trading-surface → main PR 사용자 squash
- [ ] (후속) BL-434 완전 TP/SL 보고(fetch_open_orders 조인+청산 스윕) / BL-435 청산 캐시 DEL(즉시 flat) / BL-436 청산 margin_mode 포지션값
- [ ] (이월) 다음 deepen = tasks 도메인

---

## ⚡ position-cockpit 스프린트 (2026-07-24, `docs/position-cockpit/`)

**스코프**: Phase B(perf-surface #471 후속). ① BybitPrivateStream 에 WS **position 토픽 + 실시간 팬아웃** ② 코크핏 **계좌 잔고 KPI**(활성 세션 계정) ③ **세션별 열린 포지션 표**. 캐논 screen-01 정직 실현, 미실현 계정-보고 vs 세션-추정 불일치 보정 금지. 마이그레이션 0(비영속).

### Completed

- [x] **B1** WS position 채널 — PositionFanoutHandler + PrivateTopicRouter(message_handler 주입, handler 제거), position_update 3-site 등재, DEL-before-debounce, 비활성계정 no-op, list_active_by_account, 클럭 주입 debounce
- [x] **B2** per-user position_update 발행 + qb_pos_snapshot 캐시 DEL(비영속)
- [x] **B3** 계좌 잔고 REST — `GET /exchange-accounts/{id}/balance`(P2) + BalanceSnapshot·fetch_usdt_balance_snapshot + AccountBalanceService(Redis 15s) + 404/503/unsupported 정직, fetch_balance 불변
- [x] **B4** 세션별 열린 포지션 표(세션열·short 부호·빈상태·503 재시도·verdict·각주) + 활성세션 잔고 카드 + §02/§03 삽입·§04~08 renumber(rise d8/d9) + 진단 포지션 카드 제거(2카드)
- [x] 게이트: BE **2583**(+26)·FE **1075**(+18)·ruff/mypy/tsc/lint 0·canon **32 불변**·authed **64**(코크핏 §02/§03 spec 확장)·마이그레이션 0(alembic 무변경)
- [x] 검증: codex G0 **12건 전부 CONFIRMED**(기각 0) → 전건 반영 → codex 생성 3워커(생성/평가 분리) → Claude 적대 평가 3/3(W1 테스트버그 codex resume 수정) → codex 최종 diff **NO BLOCKING** → Opus MCP dogfood 2계통(잔고 190679 curl 일치·flat) + **WS 4점 실주문**(주문→§03 포지션 64963.1↔curl→발행프레임 `position_update` P1 정확→청산)
- [x] BL: 신규 BL-431~433 등재

### Blocked

- 없음.

### Questions

- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [ ] stage/position-cockpit → main PR 사용자 squash
- [ ] (후속) 포지션 표 TP/SL·청산 액션 = BL-431(API 신설) / 잔고 selector 메모 = BL-432
- [ ] (이월) 다음 deepen = tasks 도메인

---

## ⚡ perf-surface 스프린트 (2026-07-24, `docs/perf-surface/`)

**스코프**: 이미 계산돼 있으나 미노출이던 백테스트 성과 지표(`backtests.metrics` JSONB)를 목록/전략목록/대시보드 표면으로 read-time 파생 노출 + 트레이드 상세 구간 OHLCV 미니차트. 2단계 스프린트의 Phase A(Phase B=position-cockpit 별도 세션). 마이그레이션 0.

### Completed

- [x] A1 백테스트 목록 성과 열 — 캐논 11열(종료시각 제거) + read-time `metrics_summary` 파생 + 서버 정렬(order_by/order 화이트리스트, NULLS LAST, aria-sort) + 미청산 부기(total_open_trades>0)
- [x] A2 전략 목록 성과 3칸 — DISTINCT ON 전략별 최신 COMPLETED 백테스트 metric 조인 + CSV 확장 + 무완료 `—`
- [x] A3 대시보드 §03 백테스트+최적화 병합(유형 파생 라벨·per-panel 정직성·C5 optimizer denormalize) + §04 per-strategy 성과 미터(latest_backtest 재사용, 추가 페치 0, min(return,150)/150 clamp)
- [x] A4 트레이드 상세 구간 미니차트 — `GET /backtests/{id}/trades/{index}/ohlcv`(±4봉·stride≤500·first/last/entry/exit 보존) + TradingChart 재사용(펼침 마운트 fetch 게이트)
- [x] 리포트 시맨틱 각주 — 총수익률(기말 미청산·펀딩 반영) vs 순손익(실현분)
- [x] 게이트: BE **2557**(+24)·FE **1056**(+12)·ruff/mypy/tsc/lint 0·canon **32 불변**·authed **64**(+1, /backtests 11열 구조 e2e)·마이그레이션 0(alembic 무변경)
- [x] 검증: codex G0(REVISE 6 반영·1 기각) → 워커별 Claude 적대 평가 4/4 PASS → codex 최종 누적 diff(P1 4 + vercel 1 + e2e 회귀 1 해소) → Opus MCP 실브라우저 dogfood 3점 오라클(psql↔목록↔리포트 일치, 모순표본 4a3bb5d3/8f6ba11a 미청산 부기 실증) + 실버그 1(open-trade 차트 라벨) 즉시 수정
- [x] BL: 신규 BL-427~430 등재

### Blocked

- 없음.

### Questions

- ~~[확인 필요] 백테스트 리포트 총수익률(+) vs 순손익(−) 표면 모순~~ → ✅ **해소(버그 아님)**: total_return=(실현+기말 미청산 open_pnl−펀딩)/초기자본, net_profit_abs=closed 만(`v2_adapter.py:543/656/712`). psql 표본 2건 소수 10자리 일치. 해소책=미청산 부기/각주(perf-surface A1/리포트에 반영 완료).
- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [x] stage/perf-surface → main PR #471 squash 완료 (main @ `6dbd545`)
- [x] Phase B = position-cockpit → 실행 완료(위 섹션, stage→main PR 대기)
- [ ] (이월) 다음 deepen = tasks 도메인 → position-cockpit 섹션으로 이월

---

## ⚡ opspack-ws2 스프린트 (2026-07-24, `docs/opspack-ws2/`)

**스코프**: Phase 1 정비 팩 6종(beat /data 권한 영구픽스·BL-417 제거·BL-421 pending·BL-422·BL-418·BL-419) → ★단계 게이트 → Phase 2 WS Tier 2(public ticker + 미실현 P&L 추정, position 채널 제외). 실측 반전 — TELEGRAM env 가 세팅되어 있어 실수신 dogfood 로 승격.

### Completed

- [x] beat /data 권한 영구 픽스 — Dockerfile /data seed(appuser). 익명 볼륨 fresh-seed + 재시작 발화 반증 (만성 함정 Sprint 4→tier-c 종결)
- [x] BL-417 dead snapshot 컬럼 drop(alembic, non-empty 0/3 오라클) / BL-421 `/state` 200+`evaluated:false` + authed 브로드 4xx allowlist 제거(404 미허용) / BL-422 ok 어포던스+trimming / BL-418 발행측 payload 계약(invalid counter) / BL-419 errors 경로 발행
- [x] WS Tier 2: BybitPrivateStream 3-seam(기존 테스트 무수정 green) + `bybit_public_stream.py`(1s 스로틀·delta 병합) + lease `ws:lease:public-ticker`·60s refresh·no_symbols 종료·reconcile 확장·register 킥 + manager 전원 브로드캐스트 + FE ticker Zustand 캐시(첫 실시간 데이터 캐시) + 미실현 KPI("총 세션" 교체) + 시세 지연 배지
- [x] 게이트: BE **2531**(+29+telegram hermetic)·FE **1044**(+18)·ruff/mypy/tsc/lint/prettier 0·canon **32**·authed **63**(404 비허용 하)·alembic 왕복
- [x] dogfood D1~D8 전 PASS: **Telegram 실수신 2단**(직발송 + beat 실발화 fired:1→throttled) / ticker 3계통 오라클 0.02% / 미실현 손계산 3표본 일치 / 재연결(lease 소멸→reconcile 재기동→배지 4상) / 콘솔 0 / 폴링 5.03s 단일 폴 실측
- [x] BL: BL-417/418/419/421/422 Resolved + 신규 BL-423~426

### Blocked

- 없음.

### Questions

- [확인 필요] 백테스트 리포트 총수익률(+) vs 순손익(−) 표면 모순 — tier-c 에서 이월 (dogfood 발견 #5)
- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [ ] stage/opspack-ws2 → main PR 사용자 squash
- [ ] WS position 채널 (BL-417 정리 완료로 전제 충족) — 후속 스프린트 후보
- [ ] (이월) 다음 deepen = tasks 도메인

---

## ⚡ tier-c 스프린트 (2026-07-24, `docs/tier-c/`)

**스코프**: functional-parity 에서 제외했던 Tier C 4종 전부 + WS Tier 1 (사용자 A안 확정). 실측 반전 2건 — 펀딩은 이미 엔진 배선 완료(노출 완성만), WS 는 인바운드 전층 신설(최대 규모).

### Completed

- [x] 펀딩: total_funding 4-site 노출 + FE 체크박스 활성화 + 과거 backfill(3심볼×2804행, 8h 갭 0) + beat SOL — psql 3점 오라클 25자리 일치
- [x] 옵티마이저: 베이지안 normal prior FE 해제 + E1 폼 검증 (BE 는 Sprint 57 부터 기구현)
- [x] 포지션 대조: `GET /live-sessions/{id}/positions` + PositionService(verdict 6종, 비영속) + 코크핏 카드 배선
- [x] 알림 규칙: trading.alert_rules(마이그레이션 1) + CRUD + beat evaluate_loss(세션 귀속 조인) + watchdog giveup 훅(order_id 정확 귀속) + Telegram 최초 배선(실수신 검증은 채널 미세팅으로 이연) + 코크핏 카드 UI
- [x] WS Tier 1: src/realtime 인바운드 서버(첫 메시지 auth·Origin 403) + Redis 팬아웃 발행 13지점(commit 직후) + FE ws-client/realtime feature(invalidate 힌트 전용, 폴링=SSOT) + 스트림 카드
- [x] cancel_order 실거래소 왕복(전 스프린트 잔여) — 실 demo 2건 submitted→cancelled psql 확정
- [x] 게이트: BE **2490**(+57)·FE **1019**(+36)·ruff/mypy/tsc/lint/prettier 0·canon **32 불변**·authed **63**(+1, --list 증빙)·alembic 실왕복
- [x] 검증 체인: codex G0(프레임 2 반증→플랜 수정) → 워커별 Claude 적대 평가(실버그 P1급 3건 + F 2건 적발·해소) → codex 최종 diff(MAJOR 2 해소) → Opus dogfood V1~V5 PASS
- [x] BL: 신규 BL-417~422 등재

### Blocked

- 없음.

### Questions

- [확인 필요] 백테스트 리포트 총수익률(+) vs 순손익(−) 표면 모순 — 기말 미청산 평가손익이 자본에 반영되는 기존 메트릭 시맨틱으로 추정 (tier-c 무관, dogfood 발견 #5)
- ~~beat-data 볼륨 /data root 소유~~ → ✅ opspack-ws2 에서 Dockerfile seed 로 영구 해소
- ~~알림 실수신 검증~~ → ✅ opspack-ws2 D4 에서 Telegram 실수신 2단 검증 완료 (Slack 은 여전히 미세팅 — mock 유지)
- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 지속 (pine_v2 na-safe 실험 잔재) [확인 필요]

### Next Actions

- [x] stage/tier-c → main PR #469 squash 완료 (main @ `6edc8e9`)
- [x] WS Tier 2 후보 → opspack-ws2 스프린트로 실행 (position 채널만 잔여)
- [ ] (이월) 다음 deepen = tasks 도메인 → opspack-ws2 섹션으로 이월

---

## ⚡ functional-parity 스프린트 (2026-07-23, `docs/functional-parity/`)

**스코프**: C 디자인 이식(PR #463/#464)이 남긴 기능 격차 마감 (Tier A+B, 사용자 확정. Tier C = WS/포지션동기화/알림/펀딩 제외).

### Completed

- [x] A2 주문 취소 배선 — "API unbacked" 미렌더 전제가 거짓(CF4 완비 실측) → 액션 열 재도입(프로토타입 title 바이트 일치), 200/202/409 3분기
- [x] B2 nav-count 미체결 소스 — BE `state` 반복 Query + `useOpenOrdersCount`, 캐논 §4.6 복원
- [x] B1 `strategy.backtest_count` — read-time GROUP BY(COMPLETED 기준, migration 0) + 열 재렌더
- [x] A7-lite 스트레스 최신 결과 리로드 복원 + C1 정리(dead card·viewBacktestShare·StrategyWithPine stub)
- [x] A1 대시보드 전략 링크 404 → edit 재조준
- [x] BL-401(zod field 에러 렌더)·BL-411(stale 422)·BL-402(구조 소멸) Resolved / 신규 BL-413~416
- [x] 게이트: vitest 965→980 · BE pytest 2416+18 · canon **32 불변** · authed **56→62** (`--list` 증빙)

### Blocked

- 없음.

### Questions

- wf_b2f8516a-320-1/2/3 워크트리 3개 보류 중 — pine_v2 na-safe 실험 미커밋 잔재(BL-374/PR #373 계열). 삭제 여부 사용자 판단 [확인 필요]

### Next Actions

- [x] stage/functional-parity → main PR #468 squash 완료 (main @ `16c8f20`)
- [x] Tier C 후보 재평가 → tier-c 스프린트로 실행 (★prereq spike 반전: WS 가 최저비용 아닌 최대 규모, 펀딩이 최소)
- [ ] (이월) 다음 deepen = tasks 도메인 → tier-c 섹션으로 이월

---

## 🔁 Verification Loop — 문서검증 + 아키텍처 감사 (2026-06-30, `docs/audit/2026-06-30-verification-loop.md`)

**스코프**: methodology-tooled Stage 0/4 를 quant-bridge 에 실제 적용. 코드 로직 변경 0. 브랜치 `docs/verification-loop-2026-06-30` (docs-only commits, **푸시/PR 사용자 승인 대기**).

**산출**:

- **Stage 0**: 루트 `CONTEXT.md` 도메인 헌법 신설 (codex consult 7 보정) + AGENTS.md 온보딩 4종으로 갱신.
- **문서 드리프트 수정 5 파일**: system-architecture/data-flow vectorbt→pine_v2 / ADR-020 초안→확정 / domain-overview FK 노트 / entities ENT-009 exchange→trading.
- **backtest 1차 deepen** (improve-codebase-architecture, Workflow 4-agent + codex challenge): **신규 BL-387~391** (P2 2 + P3 3) + **ADR-021** (C3 idempotency 통합 거부). 45 → **50 active BL**.
- **cadence 배선**: `.ai/common/global.md §7.5` methodology 스킬 invocable 화.

**Next Actions**:

- [ ] 브랜치 `docs/verification-loop-2026-06-30` 푸시 + PR (사용자 승인)
- [x] (선택) 다음 deepen = ~~stress_test~~ ✅ (2026-06-30 `/deepen-modules`, [`dev-log`](dev-log/2026-06-30-stress_test-deepen.md)): C1 BL-363 sharpen + C2 신규 BL-392, C3/C4 거부. 코드 0, 50 → 51 active.
- [x] (선택) 다음 deepen = ~~optimizer~~ ✅ (2026-07-13 `/improve-codebase-architecture` — 감사→같은 세션 구현): STOP 실측 repository.py 40% → S0 test-first(→100%) + A/B/N1 디스패치·직렬화 SSOT + C-min get 404 + N2 pick-best 공유. PR #431/#432/+cmin-n2 → stage/optimizer-deepen. N3→BL-411, C-full→BL-412.
- [ ] (선택) 다음 deepen = **tasks** (잔여 미감사 도메인 중 최대 4,098 LOC — trading.py 1,109 + live_signal.py 993, money-path Celery entrypoint. Iron Law = 새 session)
- [ ] `.ai/` 마스터 ai-rules repo 미러 (LESSON-068 manual sync)

---

## 🧪 Phase C 라이브 QA (2026-05-30, `docs/qa/2026-05-30-phase-c/report.md`)

**스코프**: audit Phase C deferred 실행 + S5/S6/S7 (#315/#316/#318) 머지 후 라이브 재검증. MCP Playwright `:8100/:3100` 격리 stack + Clerk test 계정.

**결과**: ✅ 8 페이지 coverage 통과 + 🚨 **1 신규 P1 발견·hotfix·머지 close-out** = audit Phase F P1 7/7 + Phase C QA 정합.

**★ S7-A regression (PR #318 머지 직후 발견 → #319 hotfix)**:

- 증상: `/trading` 계정 추가 → OKX 선택 + passphrase 비운 채 등록 → console `ZodError unhandled` + FormMessage 미표시 = silent bypass.
- 원인: `register-exchange-account-dialog` 가 평범한 `zodResolver` 사용 → Zod v4 superRefine custom issue 매핑 안 됨. `test-order-dialog` 의 custom `zodV4Resolver` 패턴 미적용.
- Fix: `frontend/src/lib/zod-v4-resolver.ts` 공유 helper 추출 + register-exchange-account-dialog 적용. 라이브 재검증 (`qa-2026-05-30/12-s7a-hotfix-validated.png`) 통과.
- Why unit test 가 못 잡았는가: schema-level test (4건 PASS) 는 superRefine 동작 검증. 그러나 dialog → resolver → RHF errors → FormMessage 통합 wiring 은 Base UI Select onValueChange 가 jsdom 에서 안 됨 → unit test 로 cover 불가.

**LESSON-068 (★★★ 공통 발견 패턴) 4번째 누적**:

- Sprint 60→61 / Sprint 61→62 / Sprint 62→Beta 진입 / **Sprint 63 S7 #318 → Phase C QA**
- 정식 승격 의무 조건 = 3/3 → 4/4 충족. 다음 sprint cycle 진입 시 `.ai/common/global.md` 정식 등재 권고.
- 핵심: **머지된 fix 의 _라이브 환경 재검증_** 이 unit test green 만으로는 잡지 못하는 통합 wiring 결함을 발견.

**P3 follow-up (별도 PR)**:

- `test-order-dialog.tsx` inline `zodV4Resolver` 공유 helper 마이그레이션 (refactor only).
- Base UI Select "uncontrolled after initialized" console warning (controlled 마이그레이션).

---

## 🔬 Full-Inspection Audit (2026-05-30, `docs/audit/2026-05-30-full-inspection.md`)

**스코프**: main @ `4aa5c2a` (PR #305~#310 머지 후). 8 차원 멀티에이전트 평가자 패널 (198 에이전트 / ~32M 토큰, stall → 트랜스크립트 복구). Decision Log DEC-1~14.

**발견 요약 (148건 검증 생존, P0 0 / P1 14 / P2 58 / P3 76)**:

- **✅ P0 = 0** — #305~#310 money-path hardening 유효, kill-switch revival / IDOR / precision / notional / stale-RUNNING reclaim 모두 살아있음 (CONFIRM 모드 재공격 통과).
- ⚠️ **P1 14건 — Beta 차단급** — Trust Layer 누출 (P1-10/13) + avg_holding_hours 288x 회귀 (P1-5) + WF backtest_config 미전달 (P1-7) + Genetic Categorical 크래시 (P1-9) + 4 trading 방어심층 갭 (P1-2/3/11/12/13/14) + frontend UX 3건.

**Fix-and-Merge Ledger (Phase F, 사용자 배치 승인 = DEC-12)**:

| 테마            | 핵심                                                                   | PR       | 상태                   |
| --------------- | ---------------------------------------------------------------------- | -------- | ---------------------- |
| S1              | P1-5 avg_holding_hours 288x                                            | #311     | ✅ Merged (2026-05-30) |
| S2              | P1-10/13 Trust Layer 누출 (28 symbols 망라 parity)                     | #312     | ✅ Merged              |
| S3              | P1-7 WF backtest_config 미전달 (BL-222 follow-up)                      | #313     | ✅ Merged              |
| S4              | P1-9 Genetic+Bayesian CategoricalField 비숫자/non-finite reject        | #314     | ✅ Merged              |
| S5              | P1-2/12/14 trading kill-switch/notional/reconcile (money path)         | #315     | ✅ Merged (2026-05-30) |
| S6              | P1-12 parse_tv_payload InvalidOperation + error path coverage (BL-309) | #316     | ✅ Merged              |
| S7              | P1-1/11 frontend 계정등록 UX + P1-8 optimizer picker                   | #318     | ✅ Merged              |
| **S7-A hotfix** | **zodV4Resolver 채택 (Phase C QA 발견 regression)**                    | **#319** | **✅ Merged**          |
| S8+             | P2 58 + P3 76 도메인별 배치                                            | TBD      | TODO (BL 등재 후 배치) |

**의사결정 매트릭스 (USER-DECIDE, 코드 불가)**:

- **G1 ★ Sprint 63 최대 blocker**: TimescaleDB 는 Cloud SQL 미지원 → DB 호스팅 재결정 필요 (self-host CE / TimescaleDB Cloud / Fly Postgres).
- G7/G8: 배포옵션 + 도메인 + healthz + worker hosting 8 P0 결정.
- BL-070 (도메인+DNS) + BL-072 (Resend) = 사용자 manual.

---

## Recently Completed — S5/S6/S7 + S7-A hotfix (audit Phase F + Phase C, 2026-05-30)

> 사용자 옵션 G (S5+S6+D) → A (S7) → A (Phase C QA + S7-A hotfix + D2 governance) 순차 진행. 모두 main merged.

### S5 — money path defense in depth (`stage/fix-trading-kill-switch`, P1-2/12/14)

- [x] **P1-2 / P1-12 (S5-A)**: `ParsedTradeSignal.realized_pnl` + `parse_tv_payload` 추출 + `receive_webhook` → OrderRequest 매핑. webhook close-alert 가 #305 CumulativeLoss/DailyLoss SUM 대상 포함. legacy backward-compat (None default).
- [x] **P1-13 (S5-B)**: market order (price=None) notional 가드 — `BybitFuturesProvider.fetch_mark_price` + `ExchangeAccountService.fetch_mark_price` + OrderService 가 2% 보수 buffer 후 기존 initial-margin 모델 재사용. live + mark 실패 = BalanceUnverified / demo = skip 기존 정책 유지.
- [x] **P1-14 (S5-C, BL-308 후속)**: `BybitReconcileFetcher.fetch_recent_orders` 가 `fetch_canceled_orders` union 반환. CCXT `has['fetchCanceledOrders']` 가드 + 미지원/실패 graceful degrade.
- [x] **검증**: trading 도메인 309 PASS (+12 신규 test = S5-A 3 + S5-B 4 + S5-C 3 + 기존 1 update) / ruff clean / mypy clean.
- [x] **commit**: `2f504dc` on `stage/fix-trading-kill-switch`.

### S6 — parse_tv_payload error path coverage (`stage/fix-trading-coverage`, BL-309)

- [x] **InvalidOperation catch**: `parse_tv_payload` except 절에 `decimal.InvalidOperation` 추가 → 비숫자 quantity/price 가 500 silent 전파 대신 WebhookUnauthorized 로 통일. main 의 실제 bug.
- [x] **신규 `tests/trading/test_parse_tv_payload.py`**: parametrized error case 30 건 (필수필드 3 + invalid side 5 + invalid type 5 + 비숫자 quantity 5 + 비숫자 price 4 + happy 분기 6 + edge case 2).
- [x] **검증**: test_parse_tv_payload 30 PASS / test_webhook_hmac + test_router_webhook 회귀 10 PASS / ruff clean / mypy clean.
- [x] **commit**: `45d582b` on `stage/fix-trading-coverage`.

### D — TODO.md governance 갱신 (PR #317 `docs/audit-todo-governance`)

- [x] PR #305~#314 + audit 2026-05-30 + Sprint 63 매트릭스 반영. docs-only.

### S7 — frontend trading UX (PR #318 `stage/fix-frontend-trading-ux`)

- [x] **P1-1/11 (S7-A)** `register-exchange-account-dialog.tsx` + `schemas.ts`: test-order-dialog 의 `root.serverError` 패턴 재사용. onSubmit try/catch + 실패 시 inline alert + 재submit clearErrors. Zod schema superRefine — OKX + passphrase null/empty 클라 검증.
- [x] **P1-8 (S7-B)** `app/(dashboard)/optimizer/page.tsx`: raw UUID input → shadcn `<Select>` picker. `useBacktests({limit:100,offset:0})` + 클라측 `status='completed'` 필터 (useMemo dep 안정화).
- [x] **검증**: frontend 신규 7 PASS + vitest 716→723 / lint clean / tsc clean / build success.

### Phase C 라이브 QA + S7-A hotfix (PR #319 `stage/fix-s7a-zodv4-resolver-hotfix`)

- [x] **🚨 신규 P1 발견**: S7-A 의 OKX passphrase superRefine 이 `zodResolver` 와 호환 안 됨 → console `ZodError unhandled` + FormMessage 미표시 = silent bypass.
- [x] **Hotfix**: `frontend/src/lib/zod-v4-resolver.ts` 공유 helper 추출 (test-order-dialog 의 inline 버전) + register-exchange-account-dialog 적용.
- [x] **라이브 재검증**: OKX 선택 + passphrase 비운 채 등록 → "OKX 계정은 Passphrase 가 필수입니다" inline FormMessage 정상 표시 (`docs/qa/2026-05-30-phase-c/12-s7a-hotfix-validated.png`).
- [x] **상세 report**: `docs/qa/2026-05-30-phase-c/report.md` (Coverage 매트릭스 + Evidence + 근본 원인 + LESSON-068 4번째 누적 + P3 follow-up).

### D2 — Phase C QA report + TODO.md governance 갱신 (본 commit, `docs/phase-c-qa-report`)

- [x] `docs/qa/2026-05-30-phase-c/report.md` + screenshot 12개 commit.
- [x] TODO.md last-updated 2026-05-30 갱신 + Phase C 발견·hotfix 반영. docs-only.

---

## Recently Completed — Phase B/C 배포 prep + audit S1~S4 (PR #305~#314, 2026-05-29 ~ 2026-05-30)

- **PR #305**: Beta money-path hardening — dead kill-switch (CRITICAL realized_pnl 미기록 → 평가기 inert) + ASYNC-1 + TRD-4/CF1 IDOR 2건 + CF4 cancel orphan + CF5/MP-3 notional Bybit 모델.
- **PR #306**: docs Phase B reconciliation — 도메인 spec / API / 거버넌스 / conformance gate / ERD 16-table 재작성 + ADR-013 충돌 해소 (trust-layer → ADR-020, optimizer 013 유지).
- **PR #307**: MP-4 — CCXT 경계 float() 제거, `_to_exchange_precision` helper (load_markets + amount/price_to_precision).
- **PR #308**: deploy-prep — entrypoint ws-stream/optimizer-heavy role + DATABASE_URL fail-fast guard + prod SECRET_KEY validator + `.env.prod.example`.
- **PR #309**: Phase C-1 CF3 — optimizer/stress stale-RUNNING reclaim watchdog mirror.
- **PR #310**: BL-308 — BybitReconcileFetcher coverage 0% → 100% (WS reconcile gap).
- **PR #311**: S1 P1-5 avg_holding_hours 288x + audit report.
- **PR #312**: S2 P1-10/13 Trust Layer 28 symbols 망라 parity (BL-361 Resolved + BL-362 follow-up).
- **PR #313**: S3 P1-7 WF backtest_config (BL-222 follow-up, BL-363 deepening 등재).
- **PR #314**: S4 P1-9 Genetic+Bayesian CategoricalField 비숫자/non-finite reject (BL-364 follow-up).

**baseline**: BE 1850 PASS / FE 716 PASS @ `4aa5c2a` → BE 1852 후 S1 → S4. green.

---

## 🚀 Beta 본격 진입 결정 (2026-05-17)

**근거**:

- Composite Health 4.18 (2026-05-13) → 6.08 (Sprint 60 후) → 7.5 (Sprint 61 후) → **추정 8.5+** (Sprint 62 후, 재측정 skip 결정).
- 4-AND gate: (a) Composite ≥ 7 ✅ / (b) Critical = 0 ✅ (BL-340 회복 + BL-339 페이지 내부 BL-356~359 fix) / (c) High ≤ 3 ✅ (P0 BL-350+354 fix + P1 BL-353/356 fix) / **(d) 본인 의지 ✅**.
- Sprint 60→62 누적 3-sprint cycle = 17 + 11 + 6 = **34 BL Resolved**. LESSON-067 6차 검증 (단일 worker 단축 패턴 누적).
- Multi-Agent QA 1차 → Sprint 60 fix → 2차 → Sprint 61 fix → 3차 → Sprint 62 fix = LESSON-068 보강 **3/3 누적** (정식 승격 후보).

**Beta 본격 진입 prep (BL-070~072) 필수 manual**:

- **BL-070** 도메인 구매 (e.g. quantbridge.io) + DNS + Cloudflare (선택) — 1-2h + DNS 전파 24h
- **BL-071** Backend 프로덕션 배포 — Cloud Run / Railway / Render 선택 + Postgres prod + Redis prod + Clerk production key + 보안 헤더 production gunicorn (BL-347 server strip 동시 처리) — 2-4h
- **BL-072** Resend 계정 + 이메일 도메인 verify + Waitlist 활성화 — 1-2h + 24h verify

**Beta 본격 진입 자연 trigger (BL-070~072 완료 후)**:

- **BL-073** Twitter/X #buildinpublic 캠페인 시작 (사용자 수동)
- **BL-074** Beta 인터뷰 3명 × 3회 (5-10명 onboarding 후, narrowest wedge 60% 검증)
- **BL-075** H2 진입 게이트 설계 (BL-005 self-assess ≥ 7/10 직후, 3-5h)

**Sprint 62 production deploy 시점 묶음 자동 해소 BL**:

- BL-320 Development mode 배지 → production key 사용 시 자동 해소
- BL-321/352 Clerk application name → dashboard 1분 변경 (BL-070 시점)
- BL-347 server header leak → gunicorn `--server_header False` (BL-071 시점) — **PR #308 에서 이미 코드 해소 (uvicorn `--server_header False` + security_headers middleware)**
- BL-261 Clerk custom domain → DNS CNAME (BL-070 시점)

---

## 🚀 Beta 본격 진입 결정 (2026-05-17)

**근거**:

- Composite Health 4.18 (2026-05-13) → 6.08 (Sprint 60 후) → 7.5 (Sprint 61 후) → **추정 8.5+** (Sprint 62 후, 재측정 skip 결정).
- 4-AND gate: (a) Composite ≥ 7 ✅ / (b) Critical = 0 ✅ (BL-340 회복 + BL-339 페이지 내부 BL-356~359 fix) / (c) High ≤ 3 ✅ (P0 BL-350+354 fix + P1 BL-353/356 fix) / **(d) 본인 의지 ✅**.
- Sprint 60→62 누적 3-sprint cycle = 17 + 11 + 6 = **34 BL Resolved**. LESSON-067 6차 검증 (단일 worker 단축 패턴 누적).
- Multi-Agent QA 1차 → Sprint 60 fix → 2차 → Sprint 61 fix → 3차 → Sprint 62 fix = LESSON-068 보강 **3/3 누적** (정식 승격 후보).

**Beta 본격 진입 prep (BL-070~072) 필수 manual**:

- **BL-070** 도메인 구매 (e.g. quantbridge.io) + DNS + Cloudflare (선택) — 1-2h + DNS 전파 24h
- **BL-071** Backend 프로덕션 배포 — Cloud Run / Railway / Render 선택 + Postgres prod + Redis prod + Clerk production key + 보안 헤더 production gunicorn (BL-347 server strip 동시 처리) — 2-4h
- **BL-072** Resend 계정 + 이메일 도메인 verify + Waitlist 활성화 — 1-2h + 24h verify

**Beta 본격 진입 자연 trigger (BL-070~072 완료 후)**:

- **BL-073** Twitter/X #buildinpublic 캠페인 시작 (사용자 수동)
- **BL-074** Beta 인터뷰 3명 × 3회 (5-10명 onboarding 후, narrowest wedge 60% 검증)
- **BL-075** H2 진입 게이트 설계 (BL-005 self-assess ≥ 7/10 직후, 3-5h)

**Sprint 62 production deploy 시점 묶음 자동 해소 BL**:

- BL-320 Development mode 배지 → production key 사용 시 자동 해소
- BL-321/352 Clerk application name → dashboard 1분 변경 (BL-070 시점)
- BL-347 server header leak → gunicorn `--server_header False` (BL-071 시점)
- BL-261 Clerk custom domain → DNS CNAME (BL-070 시점)

---

## Recently Completed — Sprint 62 fix-first (PR #290 main merge, 2026-05-17)

- [x] **T-1 BL-350+354** ★★★ Optimizer Zod resilience — FE row-level safeParse + skipped_count + 컴포넌트 graceful + BE row-level try/except (PR #290)
- [x] **T-2 BL-356/357/358/359** 모바일 페이지 내부 터치 ≥44pt 묶음 — TabsList + date-preset-pills + KPI ? + 편집 링크 + UserButton + 계정 삭제 모두 mobile h-11/size-11 + md: 분기
- [x] **T-3 BL-353** landing step 01 라벨 hero 정합 ("전략 업로드" → "전략 코드 붙여넣기")
- [x] **PR #289 + #290 머지 완료** — main `36bb4e0`
- [x] **검증**: BE optimizer 145 PASS + 2 skipped / FE 716 PASS / tsc + lint + ruff + mypy clean
- [x] **신규 11 test**: BE row-level resilience 3 + FE component graceful 3 + 회귀 갱신

**실측 시간**: ~2-3h vs plan 6-8h (Sprint 60/61 패턴 재현, LESSON-067 6차 검증).

### Sprint 62 BL Resolved 마킹 (6 BL)

- ✅ BL-350+354 ★★★ Optimizer Zod error 도배 차단 / BL-353 landing step 01 라벨 / BL-356 모바일 페이지 내부 / BL-357 strategies 편집 링크 / BL-358 UserButton width 28 / BL-359 trading 계정 삭제

---

## Recently Completed — Sprint 61 fix-first + Multi-Agent QA 재측정 (2026-05-17)

### Sprint 61 fix-first (PR #288 main @`26b7486` merge + hotfix `9103134` PR #289)

- [x] **PR #288 merge** — 8 BL fix (T-4 BL-312 OpenAPI gate / T-5 BL-311 보안 헤더 / T-6 BL-310 healthz /livez / T-1 BL-340 overflow / T-2 BL-339 터치 / T-3 BL-319+321+328 Clerk dev surface / T-7 BL-327 KPI tooltip / T-8 BL-322+323 Hero copy + Optimizer 메뉴)
- [x] **Hotfix PR #289** — BL-348 protected route accounts.dev redirect (clerkMiddleware second arg signInUrl/signUpUrl 명시) + BL-349 healthz timeout 8→12s

### Multi-Agent QA 재측정 (Standard depth, `docs/qa/2026-05-17-post-sprint61/`)

- [x] **QA Sentinel 재측정** — 7.45 → 7.8 (+0.35), Sprint 61 fix 11 BL 직접 검증 8 PASS / 2 PARTIAL / 1 manual pending
- [x] **Curious 재측정** — 6.5 → 8.0 (+1.5), Maybe → **Yes (가벼운 조건부)**, 친구 추천도 ★★★ → ★★★★
- [x] **Casual 재측정** — 5.2 → 7.4 (+2.2), 용어 해독률 22% → **89%**, 막힘 9 → 3, 포기 abandon 안 함
- [x] **Mobile 재측정** — 3.8 → 6.5 (+2.7), Critical 2 → 1 (BL-340 회복 ✅, BL-339 페이지 내부 ~15 잔존)
- [x] **통합 HTML** `docs/qa/2026-05-17-post-sprint61/integrated-report.html` — **Composite 7.5/10** (목표 정확 도달, Pre 6.08 → △ +1.42)

### Sprint 61 BL Resolved 마킹 (11 BL)

- ✅ BL-310 (PARTIAL — /livez 분리 PASS / healthz timeout 12s 완화) / BL-311 (4/5 헤더 PASS, server strip FAIL → BL-347 follow-up) / BL-312 / BL-319 (hotfix BL-348 와 묶음) / BL-322 / BL-323 / BL-327 / BL-328 / BL-339 (PARTIAL — navigation chrome ✅, 페이지 내부 ~15 잔존 → BL-356~359 follow-up) / BL-340 / BL-348 / BL-349
- ⏭️ BL-320 (defer Sprint 62 production deploy) / BL-321 (사용자 manual pending)

### 신규 BL (Multi-Agent QA 재측정, BL-347 ~ BL-360, 11건)

- **P0 ★★★ 공통**: BL-350 (Curious) + BL-354 (Casual) = `/optimizer` Zod error 도배 (Sprint 50-52 retro row + 53-55 schema tightening 합집합, Sprint 61 BL-323 사이드바 노출의 side-effect)
- **P1**: BL-353 (step 01 라벨 통일) / BL-356 (모바일 페이지 내부 터치 11 violations)
- **P2**: BL-347 (server header leak — uvicorn flag) / BL-351 (Apple/Google SSO aria-label 영어) / BL-357 (strategies 텍스트 링크 38x16) / BL-358 (UserButton width 28 + ghost DOM) / BL-359 (trading "계정 삭제" 16x16)
- **P3**: BL-352 (Clerk dashboard application name manual) / BL-355 ("Demo" → "데모") / BL-360 (backtests 375x667 +9px overflow noise)

---

## Sprint 62 분기 후보 (사용자 결정 대기)

| 옵션                               | 권고                                                          | scope                               | 기대 효과                             |
| ---------------------------------- | ------------------------------------------------------------- | ----------------------------------- | ------------------------------------- |
| **A. fix-first Sprint 62 (★★★★★)** | BL-350/354 (4-5h) + BL-356~359 묶음 (2-3h) + BL-353 (5분)     | ~6-8h 1 day single worker           | Composite 7.5 → 8.5+ → Beta 본격 진입 |
| B. Beta 본격 진입 즉시 (★★★)       | gate (a) PASS, BL-350/354 = Optimizer 메뉴 일시 hide          | dogfood 5명 onboarding 중 추가 처리 | BL-070~075 트랙                       |
| C. Sprint 47 Deepening 2차 (★★)    | BL-201/203/204 architectural                                  | —                                   | Mobile/UX 갭 우선순위 낮음            |
| D. mainnet 진입 (★)                | BL-003 Bybit runbook + BL-347 server strip + Clerk production | —                                   | H1 종료 gate                          |

---

## Recently Completed — Multi-Agent QA 2026-05-17 1차 (Sprint 60 → 61 baseline)

- [x] **사전 환경 검증** — FE :3100 + BE :8100 + worker 3종 (default/ws_stream/optimizer_heavy) 부팅 + environment fingerprint 기록
- [x] **QA Sentinel** Exhaustive — 7.45/10, BL-310~316 (7건, Critical 0 / High 4 / Med 2 / Low 1), Sprint 60 P0 fix source-level PASS 10/0
- [x] **Curious** Exhaustive — 6.5/10 Maybe, BL-317~326 (10건, Critical 0 / High 2 / Med 5 / Low 3)
- [x] **Casual** Exhaustive — 5.2/10, BL-327~337 (11건, Critical 0 / High 2 / Med 4 / Low 5), 막힘 9건 + 용어 해독률 40% + axe-core 92 serious
- [x] **Mobile** Exhaustive — 3.8/10, BL-338~346 (9건, **Critical 2** / High 3 / Med 2 / Low 1) — Casual PASS 보고 중 2건 false positive 검출
- [x] **통합 HTML** `docs/qa/2026-05-17/integrated-report.html` — Composite 6.08/10 (베이스라인 4.18 → △ +1.90)
- [x] **Sprint 61 plan** `docs/sprint-61-plan.md` — 8 BL fix-first, ≈ 23h scope

**Composite 6.08 / 10** — Beta 4-AND gate (a) FAIL 6.08<7 / (b) FAIL Crit 2 / (c) FAIL High 11 / (d) Day 7 NPS 결과 보류.
**분기 결론**: Sprint 61 fix-first 진입 → Sprint 62 Beta gate 재측정.

### 신규 BL (Sprint 61 fix-first 진입)

- **P0 (3)**: BL-339 터치 타겟 / BL-340 Trading overflow / BL-319+320+328+321 Clerk production (★★★ 3 페르소나 공통)
- **P1 (5)**: BL-310 healthz /livez / BL-311 BE 보안 헤더 / BL-312 OpenAPI gate / BL-327 KPI tooltip / BL-322+323 Hero copy + Optimizer 메뉴

### 신규 BL (Sprint 62+ 이연)

- **P2 (8)**: BL-313/314/315/316/329/330/332/344/345
- **P3 (13)**: BL-317/318/324/325/326/331/333/334/335/336/337/338/346

---

## Recently Completed — Sprint 60 (2026-05-14, ~8h actual / plan 25h)

- [x] **S0 Preflight** — slowapi inventory 강화 (false-positive 해소) + codex G.0 (master plan 31 finding 반영)
- [x] **S1 BL-244** — Optimizer 3 endpoint slowapi headers_enabled Response param fix (commit 026f7c9, codex G.1 PASS 0 findings)
- [x] **S2 UI 정직** — 가짜 marketing/testimonial/Disclaimer/내부 ID 일괄 제거 (3 commit / 27 files / vitest 27 PASS / codex G.2 2회 FAIL → 사용자 gate 명시 승인)
- [x] **S3 Auth/Routing** — Hero CTA /sign-up + middleware redirect + webhook env + /pricing (commit 14fda48)
- [x] **S4 Mobile + Clerk** — Sheet drawer + UserButton wrapper + SheetClose 44×44 + appearance.elements size-9 (2 commit / codex G.3 PASS 재진입)
- [x] **S5 안전헤더** — next.config.ts 5 헤더 + /metrics auth test (commit 2d352c2)
- [x] **S6 Close-out** — dev-log + REFACTORING-BACKLOG + TODO.md 갱신 (this)
- [x] **17 BL Resolved**: BL-244/260/262/265/268/269/270/271/273/275/280/285/300/303/305 + BL-245/246/274

**Composite Health 추정**: 4.18 → ~7.8-8.5 (manual smoke 후 보정 의무, 목표 8.0 달성).

### Sprint 60 Deferred (사용자 manual)

- [ ] Playwright e2e Mobile-Safari spot-check (viewport 4종 + a11y axe-core) — BL-285/300/305 evidence
- [ ] Critical 11 → 0 BL별 evidence 표 (screenshot/curl trace, dev-log 첨부)
- [ ] Celery worker 1+ 환경 manual smoke (backtest/optimizer 영구 pending 회피)
- [ ] PR 분리 — 1a1dbda LLM convert + Sprint 60 8 commit squash merge 결정
- [ ] codex G.4 GATE 호출 (close-out 마지막 단계, 700k tokens)

### Sprint 61 후보 (Day 7 + manual smoke 결과 합산 분기)

- **(a) Composite ≥8.0 + 본인 의지 O** → Beta 본격 진입 (BL-070~075 + BL-261 Clerk custom domain)
- **(b) Composite 6.5~7.9 + polish iter** → P1 Cleanup: BL-245/274 보안 헤더 polish (CSP strict) / BL-247 에러 schema / BL-250 ADR-003 request.security / BL-264 TTFV WS / BL-301 모바일 가로 / Casual UX BL-281~286
- **(c) Composite <6.5** → 추가 trust 회복 + Sprint 60 회고

### 신규 BL (Sprint 61 follow-up)

- [ ] BL-신규 Clerk JWT 60s expired E2E case (plan v2 P1-2 Playwright auth-flow.spec)
- [ ] BL-신규 MobileNav unit test (G.3 P2-3 append, drawer open/close/route/Escape/UserButton hit target)
- [ ] BL-신규 Backend test fixture DB password 환경 (S1/S5 integration test 3 ERROR 공통)

> 사람과 AI 가 공동 관리하는 활성 작업 추적 파일.
> 차단 항목은 `[blocked]` 표시 / 질문은 §Questions / 활성 BL 상세는 [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md) / sprint 회고는 [`dev-log/INDEX.md`](./dev-log/INDEX.md).

---

## 활성 sprint 상태

### Sprint 59 (완료, 2026-05-13)

- **PR 묶음 (5 PR squash merge):** #273 (`_worker_engine` SSOT, -163L) + #274 (Pine v1 demolition, -4838L) + #275 (BACKLOG 압축 1028→587L) + #276 (158 BL → 13 Active 트리아주) + #277 (backtest-form 5-split, 866→232L)
- **검증:** BE 회귀 0 (pine_v2 537 PASS / tasks 146 PASS / engine 138 PASS) + FE 회귀 0 (vitest 680 PASS) + ruff/mypy/tsc/lint clean
- **신규 BL:** 0 / Resolved (PR-D 5-rule triage): 158 BL → **13 Active + 8 Deferred + 137 Archived**
- **누적 net deletion:** ~6,000+ lines (메타 노이즈 + dead code + locality 정리)
- **상세:** [`docs/dev-log/2026-05-13-sprint59-close.md`](./dev-log/2026-05-13-sprint59-close.md)
- **13 active BL** (상세 = [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md) + [`refactoring-backlog/_archived.md`](./refactoring-backlog/_archived.md) + [`refactoring-backlog/_deferred.md`](./refactoring-backlog/_deferred.md))

### 직전 sprint: Sprint 58 (BL-241/242/243 Pine TA 확장)

- 상세: [`docs/dev-log/2026-05-11-sprint58-close.md`](./dev-log/2026-05-11-sprint58-close.md)

---

## 다음 분기 (Sprint 60)

dogfood Day 7 인터뷰 (2026-05-16, 사용자 manual) 결과 + 본인 의지 second gate 에 따라 4-way 분기:

- **(a)** NPS ≥7 + critical bug 0 + self-assess ≥7 + 본인 의지 → Sprint 60 = **Beta 본격 진입** (BL-070~075 도메인+DNS / BE 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)
- **(b)** dogfood mixed / no urgent bug → Sprint 60 = 잔여 active BL (BL-003 mainnet runbook / BL-014 partial fill / BL-022 golden / BL-235 N-dim viz / BL-236 objective whitelist)
- **(c)** mainnet trigger 도래 → Sprint 60 = BL-003 / BL-005 mainnet 본격
- **(d)** trust-breaking bug 노출 → Sprint 60 = 그 fix 1 sprint 우선, 후속은 Sprint 61+ 이연

### Sprint 60 첫 step 의무

- Day 7 카톡 인터뷰 결과 정리 (`sprint42-feedback.md` Day 7 row) + Sprint 59 evidence 검토 ([`dev-log/2026-05-13-sprint59-close.md`](./dev-log/2026-05-13-sprint59-close.md))
- 4-AND gate 검증: (a) self-assess ≥7 / (b) BL-178 production BH 정상 / (c) BL-180 hand oracle 8 test GREEN / (d) new P0=0 AND unresolved Sprint-59-caused P1=0
- **Sprint 50/51/52 `result_jsonb` retro-incorrect 안내 유지** — BL-222 fix 이전 CA / PS 결과는 사용자 manual 재실행 권고
- PR-E (5-split) 의 **5분 dev smoke** (LESSON-004 PR 규약, 사용자 manual) — 누락 시 회귀 의무 검증

---

## 상시 활성 컨텍스트 (영구 기록 외 발견 패턴)

- `dogfood Day N` 노트는 sprint 묶음과 별개로 `dev-log/` 에 단독 파일로 보관
- BL-005 (본인 1-2 주 dogfood) trigger 도래 후 H1→H2 gate (self-assessment ≥7) 가 재평가 기준
- `make up-isolated` (3100 / 8100 / 5433 / 6380) 가 다른 웹앱 병렬 시 디폴트
- **Pine SSOT 4 invariant audit** (`tests/strategy/pine_v2/test_ssot_invariants.py`) — supported list 추가 시 4 collection 동시 갱신 의무 자동 검증
- **Surface Trust sub-pillar (Sprint 30 ADR-019)** — Backend Reliability + Risk Management + Security + Surface Trust (가정박스 / 차트 / 24 metric / 거래목록). 측정: PRD 24 metric BE+FE 100% / config 5 가정 FE 100% / lightweight-charts 정합 / dogfood self-assess Day 3 ≥7
- **자율 병렬 sprint Agent worktree 패턴** — 충돌 회피 신규 파일 only / 통합 작업은 메인 세션 후처리 / gh CLI auto-merge --squash / `--no-verify` 1 회 우회 사용자 명시 승인 패턴

---

## 활성 BL 요약 (상세는 [`REFACTORING-BACKLOG.md`](./REFACTORING-BACKLOG.md))

> 본 sprint kickoff 시 백로그 review 의무. 자연어 표현은 컨텍스트 복원성 위해 sprint 회고 안에 유지하되, 새 항목 추가 시 BL ID 부여 후 등록.

핵심 cross-link (Sprint 59 PR-D 트리아주 후):

- **P0 active**: [BL-003](./REFACTORING-BACKLOG.md#bl-003) Bybit mainnet runbook
- **P1 active**: [BL-014](./REFACTORING-BACKLOG.md#bl-014) partial fill / [BL-015](./REFACTORING-BACKLOG.md#bl-015) OKX WS / [BL-022](./REFACTORING-BACKLOG.md#bl-022) golden 재생성 / [BL-023](./REFACTORING-BACKLOG.md#bl-023) KIND-B/C / [BL-024](./REFACTORING-BACKLOG.md#bl-024) real_broker E2E / [BL-025](./REFACTORING-BACKLOG.md#bl-025) autonomous-parallel patch / [BL-026](./REFACTORING-BACKLOG.md#bl-026) mutation fixture
- **P2 active**: [BL-186](./REFACTORING-BACKLOG.md#bl-186) full leverage model / [BL-190](./REFACTORING-BACKLOG.md#bl-190) PDF export / [BL-195](./REFACTORING-BACKLOG.md#bl-195) form animation / [BL-235](./REFACTORING-BACKLOG.md#bl-235) N-dim viz / [BL-236](./REFACTORING-BACKLOG.md#bl-236) objective whitelist
- **Deferred milestone** ([`_deferred.md`](./refactoring-backlog/_deferred.md)): BL-005 본인 dogfood / BL-070~075 Beta 본격 진입 / BL-145 EffectiveLeverageEvaluator
- **Archived 138건** ([`_archived.md`](./refactoring-backlog/_archived.md)): 모든 ✅ Resolved + Sprint 16~30 stale follow-up + P3 전부
- **정합성 audit:** [`04_architecture/architecture-conformance.md`](./04_architecture/architecture-conformance.md) — 15 항목 영구 체크리스트

---

## Test Skip / xfail 추적표 (Sprint 15-C 신설, 2026-04-28)

> 18 skip + 0 fail (Sprint 14 기준). "이 skip 이 왜 존재 + 언제 해소" 명시. 신규 skip 추가 시 본 표 업데이트 의무.

| #    | 위치                                                                                   | 종류                     | 사유                                                                                 | 해소 트리거                                                                  |
| ---- | -------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 1    | `tests/backtest/engine/test_golden_backtest.py:19`                                     | `pytestmark.skip`        | legacy golden expectations — pine_v2 `strategy.exit` 지원 + expected 재생성 필요     | pine_v2 strategy.exit 도입 후 golden 재생성                                  |
| 2    | `tests/real_broker/test_webhook_to_filled_e2e.py:31`                                   | `pytestmark.real_broker` | nightly E2E (Bybit Demo 실 호출). `--run-real-broker` flag + `BYBIT_DEMO_*` env 필요 | 매일 nightly cron (`.github/workflows/nightly-real-broker.yml`)              |
| 3    | `tests/real_broker/conftest.py:43`                                                     | `skip_marker`            | 위 #2 의 conftest fallback (env 미주입 시 collection-time skip)                      | 동일                                                                         |
| 4-7  | `tests/strategy/pine_v2/test_trust_layer_parity.py:251/334/357/421`                    | `skipif`                 | Trust Layer fixture (`regen_trust_layer_baseline.py` / 8 mutation set) 미생성        | Path β Stage 2c 2 차 mutation 8/8 도달 (2026-04-23 완료, 회귀로 활성화 검토) |
| 8    | `tests/strategy/pine_v2/test_trust_layer_parity.py:405`                                | `pytest.mark.skip`       | Mutation oracle 은 nightly workflow 또는 `--run-mutations` 수동 (CI default 차단)    | nightly mutation workflow 또는 manual gate                                   |
| 9-15 | `tests/strategy/pine_v2/test_mutation_oracle.py:147/179/212/253/296/328/376/414` (8건) | `skipif`                 | mutation fixture 미생성 시 collection skip                                           | Stage 2c 2 차 fixture 활성화 후 사용 가능 (현재 안전 fallback)               |
| 16   | `tests/strategy/pine_v2/test_mutation_oracle.py:213`                                   | `xfail(strict=False)`    | KIND=B/C 가 NaN-tolerance 한계로 mutation 구분 못 함. strict=False 로 명시           | KIND-B/C 분류 정밀도 향상 (Trust Layer v2 검토)                              |
| 17   | `tests/conftest.py:93`                                                                 | `skip_mutation` autouse  | 모든 `@pytest.mark.mutation` 자동 skip (CI default), `--run-mutations` 시 활성화     | pytest collection-time guard (영구)                                          |
| 18   | (집계 차이)                                                                            | xfail/skip 누적          | pytest collection-time 자동 분기 (real_broker / mutation 기본 차단)                  | 표 업데이트 의무                                                             |

**카테고리:**

- 영구 (정상): #2, #3, #8, #17 — opt-in flag 가 정확한 안전장치
- fixture 활성화 후 자동 해소: #4-7, #9-15 — Path β Stage 2c 2 차 후 회귀 검토 → [BL-026](./REFACTORING-BACKLOG.md#bl-026)
- dette: #1 (golden 재생성) → [BL-022](./REFACTORING-BACKLOG.md#bl-022) / #16 (KIND-B/C 정밀도) → [BL-023](./REFACTORING-BACKLOG.md#bl-023)

**관리 규약:** 신규 skip 추가 시 본 표 동일 PR 업데이트 / 매 sprint 끝 fixture 카테고리 재검토.

---

## Blocked

(현재 없음 — Sprint 58 종료)

---

## Questions

(없음 — 활성 질문 시 추가)

---

## Next Actions

- Sprint 59 진입 = Day 7 인터뷰 2026-05-16 결과 분석 후 결정
- Tier 1 refactor audit (현재 진행 중) → 사용자 승인 후 commit + PR
