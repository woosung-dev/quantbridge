<!-- backtest-trust 스프린트 진행 체크리스트 — 슬라이스별 완료 + 게이트 실측값 기록 -->

# backtest-trust — 체크리스트

> 플랜 SSOT = `~/.claude/plans/backtest-trust-joyful-wirth.md` · 계약 = [`operating-contract.md`](operating-contract.md) · 결정 기록 = [`context-notes.md`](context-notes.md)
> 브랜치 `stage/backtest-trust` (main @ `a4954e4` 베이스). 마이그레이션 **0**.

## 스코프

| ID             | 내용                                                                      | 규모 |
| -------------- | ------------------------------------------------------------------------- | ---- |
| **B1 BL-398**  | Sharpe → TV 컨벤션(달력월 + RFR 2%) + `sharpe_convention` 마커 4종        | M    |
| **B2 BL-186a** | 레버리지 사이징 + 격리 강제청산 + 마진 게이트 + FE 입력 재도입 (**원자**) | L    |
| **B3 BL-388**  | 이미 해결됨 → Resolved close + micro-tripwire 2 + stale 주석 정정         | XS   |

---

## §0 전제 게이트

- [x] **직전 스프린트 main 머지 확인** — PR #477 `MERGED` 12:29Z / #478 `MERGED` 12:30Z · 열린 PR 0건 · 트리 클린 · main = origin/main @ `a4954e4`
- [x] **브랜치 생성** — `stage/backtest-trust`
- [x] **스택 기동 확인** — db 5433 healthy · redis 6380 healthy · worker/beat/ws-stream/optimizer-heavy Up
- [x] **★8100 백엔드 stale 프로세스 해소** — PID 66385(2026-07-24 08:22 기동)가 닫힌 5436 을 향하고 있었다. 브라우저엔 CORS 로 보이지만 **CORS 문제가 아니다**. kill 후 `make be-isolated` 재기동 → `/health` ok + DB 접촉 엔드포인트 **401 / 26ms**(500·timeout 아님) + 프로세스 env `localhost:5433/quantbridge` 확인
- [x] **BL-388 tripwire 선확인** — `pytest tests/backtest/test_metrics_field_parity.py` → **6 passed**. 재구현 낭비 차단
- [x] **3-env 확인** — `set -a; source backend/.env.local; set +a` → `…5433/quantbridge_test` + `redis://…6380/3`. ★핸드오프의 5436 표기는 **틀렸다**
- [x] **FE baseline** — `pnpm test` → **1097 passed / 193 files**. 플랜 예상 1094 대비 **+3 드리프트**
- [x] **BE baseline** — `pytest -q` → **2717 passed / 46 skipped** (4:02). 플랜 예상과 일치. ★TODO 가 우려한 `test_redis_client::test_get_pool_safe_across_event_loops` 전체실행 flake는 **재현되지 않음**
- [x] **canon baseline 실측 = 32/32 passed** (33.4s, `chromium-design-canon`, base=3100). ★**사전 경고된 "27/32 · 차트 토큰 9/10 런타임 미해석" 은 재현되지 않았다** — `design-canon-tailwind-utilities.spec.ts` 포함 전건 통과. 27 로 기록했다면 나중에 32 를 보고 "개선됐다"고 오판했을 것이다. 원인 추정 = Turbopack CSS 캐시가 재기동을 넘어 생존한 상태에서의 측정(이 레포 알려진 함정). **baseline = 32**
- [x] **3100 정체성 프로브** — `<title>QuantBridge</title>` 확인(3000 은 타 프로젝트 점유 이력)
- [x] **alembic baseline** — `alembic current` = **`20260725_0002 (head)`**. ★`alembic check` 는 드리프트를 보고하나 **코드 변경 0 상태에서 나온 선재 조건**(ts/trading 스키마 hypertable 계열). 마이그레이션 0 게이트 = **신규 리비전 파일 0 + head 불변**으로 판정한다(직전 스프린트들과 동일)
- [x] **codex G0** — **BLOCKING 1 + P1 3 + P2 3**. 전건 코드 대조 후 **5건 수용(설계 개정) · 2건 이미 반영됨**. 최대 수확 = 마진 게이트를 `entry()` 에만 걸면 `check_pending_fills` 의 **직접 `Trade` 생성 경로**로 뚫린다는 것(`Trade(` site 2곳 → 단일 chokepoint 로 통합). 상세 = [`context-notes.md`](context-notes.md) §7

---

## S0 — 와이어 계약 동결

- [x] `sharpe_convention` 4종 값 계약 확정 (`tv_monthly_rfr2` / `tv_daily_rfr2` / `unavailable` / `null`)
- [x] 청산 필드 계약 확정 (`Trade.liquidated`/`liq_price` → `RawTrade.liquidated` → `liquidation_occurred`/`liquidation_count`)
- [x] **★`ExitOrderKind` 확장 기각** — DB 문자열 컬럼에만 `"liquidation"` 기록 (근거 = `map_exit_kind` fall-through, `BL-365` dead code)
- [x] `operating-contract.md` 작성 (워커 병렬 진입 조건)

---

## B1 — Sharpe TV 컨벤션 (BL-398)

- [x] **S1** `metrics.py`: `_periodic_returns` → 3-tuple(period 추가) · `sharpe_ratio(equity) -> tuple[Decimal, str]` 신설 · 어댑터 미배선
  - ✅ 평가자 직접 실행: ruff 0 · mypy Success · 대상 **17 passed** · sortino/calmar/oracle 계열 **87 passed**(3-tuple 변경이 sortino 를 안 깨뜨림 증명) · 오라클은 **손계산 상수**(0.335876 / -0.000548) — codex 붙이기 전에 내가 독립 도출한 값과 일치 = anti-circular 성립
- [x] **S2** 4-site + summary + 어댑터 배선 (`v2_adapter.py:662` 교체 · `_sharpe:1130` 삭제 · `_as_float_series` 존치)
  - ✅ 평가자 직접 실행: ruff 0 · mypy **Success(15 files)** · tripwire **6 passed**(신규 필드가 4-site 에 다 들어갔다는 자동 증명) · **baseline/golden 무수정 확인(R1)**
  - ✅ 의도된 red 검증: `test_trust_layer_parity` **4 failed / 12 passed**, 실패 전부 `<corpus>.sharpe_ratio: 드리프트`. **다른 metric 키 실패 0건 = 누출 없음.** `i2_luxalgo` 는 통과(구 값 0.00000000 → 신 값도 `unavailable` 0)
  - 로컬 변수를 `sharpe_ratio_value` 로 개명해 import 한 함수와 이름 충돌 회피
- [x] **S3** 랭킹 flip 실측 + baseline regen + `expected.json` 수동 갱신
  - ✅ **랭킹 flip 실측 (의무)** — 15셀(5 corpus × 3 수수료). **argmax FLIP**(`s1_pbr@0.0002`→`@0.001`) · **Kendall τ = 0.6381** · **11/15 셀 2계단 이상 이동**. ★결정적 증거 = `s2_utbot@0.005`/`i1_utbot@0.005` 가 **자본 38배 손실(총수익률 −3837%)에 구 수식이 양수 샤프 +0.3955 를 줬다** → 신 `−0.0757` 로 부호 정정. 상세표+한계 = [`context-notes.md`](context-notes.md) §8b
  - ✅ **harness 자기검증** — `s1_pbr@0.001` 구 값 `+1.141969` 가 baseline `1.14196912` 와 정확 일치 → 구 수식 자립 복사 정확
  - ✅ **regen `--confirm`** — 신 값이 독립 harness 측정과 **소수 6자리 일치**(0.60013053 / −0.44702772 / −0.01388353)
  - ✅ **R1 검증** — 값 변경은 `sharpe_ratio` 4건 + 메타뿐. **`total_return`·`max_drawdown`·`win_rate`·`num_trades` + 3종 digest(`var_series`/`trades`/`warnings`) 전부 불변** = sharpe 외 엔진 동작 바이트 동일. `i2_luxalgo` 는 0 유지
  - ✅ **golden `expected.json` 갱신** — F1 실증(RangeIndex → `sharpe_convention="unavailable"`, 값 0). 구 값 `-0.34227508263480416` 을 사유와 함께 description 에 보존
- [x] **S4** (W2) FE B1 — `sharpe-convention.ts` SSOT 신설 · zod 2곳(`.optional()` 하위호환) · 렌더 3곳(KPI/상세지표/목록) · 혼재 정렬 고지
  - ✅ 평가자 직접 실행: **`pnpm test` 1109 passed / 194 files**(baseline 1097 → +12) · `pnpm typecheck` 0 · `pnpm lint` 0
  - ✅ **거짓 각주 제거 확인** — `key-stats-strip.tsx` 의 `foot="무위험 수익률 0% 가정"` 이 실제로 사라지고 컨벤션 파생 문구로 교체됨
  - ✅ `unavailable` 에서 `.toFixed(2)` 미호출 → `EMPTY_CELL` 렌더(값 0 을 "0.00" 으로 그리는 거짓 차단)
  - ⚠️ 워커가 `frontend/{checklist,context-notes}.md` 를 잘못된 위치에 생성 → **제거함**(내용은 `docs/archive/sprints/backtest-trust/` 에 이미 있음)

## B2 — 레버리지 충실도 (BL-186a) · ★설계 전환: TV/MT5 컨벤션

> **레버리지는 주문 수량을 바꾸지 않는다.** 필요증거금(notional/leverage)으로 진입을 게이트하고 청산가를 정할 뿐이다. → **`compute_qty` 무변경** → 레버리지>1 에서도 TV parity 유지. 근거·출처 = [`context-notes.md`](context-notes.md) §9
> 사이징 상한 완화는 **불필요**(정정) — `default_qty_value` 는 원래 상한이 없어 `percent_of_equity=1000` 이 지금도 입력된다. `position_size_pct le=100` 은 Live 미러 전용이라 유지가 옳다.

- [x] **S5a** `leverage_model.py` 순수 수식 신설 + 단위 테스트 + **라이브 수식 parity 테스트**
  - ✅ 평가자 직접 실행: ruff 0 · mypy Success · **231 passed**. parity 테스트 **216 케이스**(9 레버리지 × 4 진입가 × 3 MMR × 2 방향)가 `trading/liquidation.py` 와의 일치를 CI 로 강제 → **수식 중복 정의의 정당화 성립**
  - `is_leverage_active` = 게이트 술어 단일 SSOT. nan 선차단. 방어값은 예외 대신 `None`/`inf`(bar 루프 안전)
- [x] **S5b** 엔진 배선 — 단일 chokepoint `_open_trade()` · `check_liquidations()` · 배관 4층 · 양 루프
  - ✅ 평가자 직접 실행: **BE 전체 2961 passed / 46 skipped** · ruff 0 · mypy Success(204 files) · **regen 0회**(fixture/golden diff 는 S3 산출물 그대로)
  - ✅ 코드 대조: `compute_qty` **본문 무변경** · pyramiding 검사는 `entry()` 잔류(옮기면 stop 체결까지 cap) · `running_equity` **미변형**(가용은 `Σ margin_used` 로 파생) · `check_pending_fills` 가 `None` 반환을 올바르게 처리
  - ✅ 루프 순서: S/M `intents→pending→**liquidations**→exits→execute` · Track A `pending→**liquidations**→process_bar` (청산 우선 = 비관적)
- [x] **S5c** 통합 회귀 실측
  - ✅ **R2 PASS** — 5 corpus 전부 L=1.0 에서 metrics JSONB + 거래 수 동일
  - ✅ **R3 PASS** — 6 조합에서 변화(§8d "before" 는 소수 19자리까지 동일했다)
  - ✅ **마진 게이트가 corpus 내재 레버리지를 정확히 판정** — `qty=1 BTC`($42k) / 자본 $10k = **~4.2x** 요구 → 3x 거부, 10x 통과
  - ✅ **청산 발화 실측** — 1x **0건**(현물 정합) / 25x **8건**(거리 3.5%) / 100x **267/466**(거리 0.5%). 물리적으로 정확히 단조 증가
  - ⚠️ 측정 함정: `getattr(t,'liquidated',False)` 가 `RawTrade` 미구현 필드를 "정상 False" 로 위장 → `comment` 마커로 재측정. 전파는 S6
- [x] **S6** 청산 전파 — `RawTrade.liquidated` · metrics 4-site(`liquidation_occurred`/`liquidation_count`) · `service.py:442` DB `exit_kind='liquidation'`
  - ✅ 평가자 직접 실행: **BE 전체 2966 passed / 46 skipped** · ruff 0 · mypy Success(204) · tripwire **6 passed** · trust layer+golden **17 passed**(1x byte-identity) · 신규 청산 metrics **5 passed**
  - ✅ **3중 독립 측정 완전 일치**: 1x → metrics `None`/`None` · RawTrade 0 · comment 0 · **JSONB 키 부재**(바이트 동일) / 25x → 8·8·8 / 100x → 267·267·267
  - ✅ `ExitOrderKind` enum **미확장** — DB 문자열 컬럼(`max_length=16`)에만 `'liquidation'`. `map_exit_kind` fall-through 위험 회피 + 마이그레이션 0
- [x] **S7** (W2) FE B2 — `BacktestLeverageFieldSet` 신설(레버리지 입력 재도입) · 5종 고지 배너 · `mdd-caption` 3분기 · `EXIT_REASON_LABEL` 에 **`liquidation: '강제청산'`** · 실행품질 '강제청산' 행
  - ✅ 평가자 직접 실행: **FE 1113 passed / 194 files** · typecheck 0 · lint 0 · 부수 md 0
  - ✅ 배관 확인: `useBacktestForm:154` 가 폼 값을 payload 로 전달 → **레버리지가 실제로 도달**(Sprint 37 이후 처음)
  - ✅ 평가자 추가 편집: gross 자본 판정 고지 1줄 보강(§11 실측 근거)
- [x] **S8** BL-388 micro-tripwire 2 — **8 passed**, 대상 1파일 +33줄, ruff 0

## B3 — BL-388 close

- [x] micro-tripwire 2건 (summary 키 부분집합 · Decimal↔field_serializer 전수) — S8 에서 완료
- [x] stale 주석 정정(숫자 재기입 금지, **R5**) — S2/S6 에서 완료
- [ ] 백로그 Resolved 마킹 + 신규 BL 등재
- [ ] **S7** (W2) FE B2 — 레버리지 입력 재도입 · 청산 고지 배너 · `mdd-caption` 확장 · **`EXIT_REASON_LABEL` 에 `liquidation`**
  - 검증: L=1 배너 미렌더 · L>1 배너·청산가 프리뷰 · Live Settings 구분 문구

## B3 — BL-388 close

- [ ] **S8** micro-tripwire 2건 + stale 주석 정정(숫자 재기입 금지, **R5**) + 백로그 Resolved
- [ ] **S9** (선택) `MirrorNotAllowed`/`leverage_basis` unlock — **`margin_mode == "isolated"` 한정**

---

## 검증 / 마감

- [x] **게이트 전종** — BE **2968 passed / 46 skipped** · ruff 0 · mypy Success(204) / FE **1113 passed / 194 files** · typecheck 0 · lint 0 / **canon 32/32**(회귀 0) / **build ok** / **마이그레이션 0**(신규 리비전 0 · `alembic/` 변경 0 · head `20260725_0002` 불변)
- [x] **authed e2e** — 57 passed / 7 failed / 1 skipped. ★7건 전부 **빈 DB 환경 문제**로 판별: 실패 사유가 `waiting for locator('[data-testid^="backtest-row-"]')` 타임아웃이고 DB 는 `strategies=0 backtests=0`. 코드 회귀 아님(직전 스프린트에서도 동일 사유 6건 이월)
- [x] **실브라우저 dogfood — 레버리지 폼** (독립 Playwright + 기존 storageState)
  - L=1 → 배너 **미노출**(0) / L=25 → 배너 노출(1)
  - 필요 증거금 **4.0%**(=100/25) · 청산 거리 **3.50%**(=(1/25−0.005)×100) — 파생값 산술 정확
  - 고지 7종 전부 렌더(모델 한계 · **TV/MT5 시맨틱** · 노출은 주문크기로 · **gross 자본 판정** · Live Settings 구분)
  - **콘솔 error 0**
- [x] **엔진 dogfood** — Sharpe 손오라클 ↔ 엔진 일치 / 청산 1x=0·25x=8·100x=267(3중 교차검증) / 마진 게이트가 corpus 내재 4.2x 판정 / L=1 byte-identity
- [x] **최종 codex 누적 diff — BLOCKING 2 + P1 2 + P2 2, 전건 코드 대조 후 전부 수정**
  - **BLOCKING ①** `entry():571-573` 이 flip/close 를 게이트보다 먼저 실행 → 증거금 거부 시 **역전이 조용히 전량청산으로 바뀜**(실거래소는 주문 전체 거부). → **`_can_afford_entry()` pre-flight 신설**: flip 부작용 전에 "청산 예정분의 실현손익 + 해제 증거금" 을 반영한 사후 상태로 판정, 불가하면 flip 자체를 안 함. 두 경로(`entry`/`check_pending_fills`) 모두 적용. `is_leverage_active` 아니면 즉시 `True` → **1x no-op 보존**
  - **BLOCKING ②** 청산 metrics 가 `cfg.leverage > 1` 로 판정해 **단일 게이트 술어 우회** → `is_leverage_active(cfg.leverage)` 로 교체
  - **P1 ①** `assumptions-card` 가 Nx 실행에도 "1x · 롱/숏 / 강제 청산 미반영" 표시 = **엔진과 정반대 고지**(내가 S7 스펙에서 누락) → `config.leverage` 분기
  - **P1 ②** 폼 배너에 **TV=부분청산 vs 우리=전량청산** 차이 미고지(계약 요구사항 누락) → "TradingView·MT5 와 동일" 문구 **바로 뒤**에 배치
  - **P2** 구 Nx 실행이 "레버리지 1배 실행" 오표기 / "지표 24종" 라벨이 실제 25행과 불일치(★숫자 재기입 금지 규약대로 숫자 없는 표현으로)
  - ✅ 수정 후 재검증: **R2 PASS**(5 corpus 1x 동일) · **R3 PASS**(10 조합, 6→10 증가) · FE **1115 passed** · typecheck/lint 0 · dogfood 재실행 고지 7종 + **콘솔 0**
- [ ] `context-notes.md` + TODO + dev-log + 백로그(BL-398/388 Resolved · BL-186 부분) + **`roadmap.md` 갱신**
- [ ] 신규 BL: BL-186b · `_periodic_returns` sub-daily fallback · Sharpe 목록 read-time recompute · BL-389 재실사
- [ ] PR `stage/backtest-trust` → main (squash 는 사용자)
