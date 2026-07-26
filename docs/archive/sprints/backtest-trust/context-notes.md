<!-- backtest-trust 스프린트 컨텍스트 노트 — 작업 중 내린 결정과 그 근거를 시간순으로 append -->

# backtest-trust — 컨텍스트 노트

> 결정과 **근거**를 계속 append 한다. 다음 세션(사람이든 에이전트든)이 재유도 없이 이어받을 수 있어야 한다.
> 계약 = [`operating-contract.md`](operating-contract.md) · 진행 = [`checklist.md`](checklist.md)

---

## 1. 핸드오프 좌표 정정 4건 (착수 전 코드 전수 대조)

핸드오프(`~/.claude/plans/quantbridge-backtest-trust-handoff.md`)는 grounding 세션 산출물이었으나 **경로 2건이 틀렸고 서술 2건이 사실과 달랐다**. 착수 첫 step 에서 Explore 3기로 전수 대조해 정정했다.

| 핸드오프 표기                                          | 실제                                                                                            |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `backtest/pine_v2/v2_adapter.py`                       | **`backtest/engine/v2_adapter.py`** (줄번호 1130/662 는 정확)                                   |
| `backtest/pine_v2/strategy_state.py`                   | **`strategy/pine_v2/strategy_state.py`** (`compute_qty:285` 정확)                               |
| BL-388 "24 필드 / 4-site"                              | **48 필드 / 실질 3-site** — 4개 site 전 차집합이 공집합, tripwire 6테스트 통과 상태             |
| BL-398 "FE 가 '(bar 수익률 기준)' 라벨로 정직 고지 중" | **그 문자열은 레포에 없다.** 실제 각주는 `key-stats-strip.tsx:136` 의 `"무위험 수익률 0% 가정"` |

**교훈**: grounding 세션의 산출물도 착수 시점에 재대조해야 한다. 특히 "이미 정직하게 고지 중"이라는 안심 서술이 틀렸을 때 손실이 크다 — 실제로는 RFR 2% 도입 즉시 **그 각주가 거짓이 되는** 상태였다.

## 2. ★프레임 이슈 — BL-186a 는 제품에 도달 불가였다

핸드오프는 BL-186a 를 "M(엔진 작업)"으로 잡았다. 실측하니:

- `CreateBacktestRequest.leverage`(1~125 검증) → `service.py:206` config JSONB → `config_mapper.py:103` → `BacktestConfig.leverage` 까지 **배관이 살아 있는데 엔진 참조가 0건**이다.
- 그런데 **FE 폼에 레버리지 입력이 없다** — Sprint 37 BL-187 이 "Live Settings 의 leverage 와 시각적으로 혼동"을 이유로 제거했고(`dev-log/2026-05-06-sprint37-master.md:81,97`), 지금은 `useBacktestForm.ts:92,154` 에 `leverage: 1` 하드코딩이다.
- 즉 **엔진만 고치면 사용자 도달 경로가 0**이다. 게다가 `mdd-caption.ts:19-26` 은 이미 `leverage 10x 가정` 캡션을 렌더할 준비가 돼 있어, API 로 10x 를 넣으면 **10x 라고 표시되면서 1x 로 계산된 결과**가 나온다(잠복 거짓말).

→ 규모를 **L** 로 재평가하고 사용자 인터뷰로 범위를 확정했다.

## 3. 사용자 인터뷰 확정 4건

1. **BL-186a = 엔진 + FE 입력 재도입(완결).** 반쯤 죽은 기능 출하를 거부.
2. **청산 = 단순 모델 + 강한 정직 고지.** Sprint 37 의 기각 근거가 정확히 "부정확한 simple liquidation 도 trust 를 갉아먹는다"(`sprint37-master.md:39,219`)이므로, 그 기각을 **고지로 상쇄**하는 선택임을 명시적으로 인지하고 채택.
3. **마진 가용성 게이트 포함.** 사이징 × 레버리지 + pyramiding 이면 동시 포지션 증거금 합이 자본을 넘길 수 있어, 청산만 넣으면 다시 판타지가 된다.
4. **Sharpe 혼재 = 컨벤션 마커 필드.** 라벨 정정만으로는 `repository.py:75` 의 JSONB→Numeric **서버 정렬**이 두 척도를 섞어 세는 것을 못 막는다.

## 4. 설계 교차검증에서 나온 추가 사실 4건

Plan 에이전트를 붙여 설계를 교차검증했고, **설계를 바꾸는 사실 4건**이 나왔다. 전부 코드로 재확인했다.

### F1. golden fixture 에 timestamp 컬럼이 없다 → 신규 Sharpe = 0

`tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv` 헤더 = `open,high,low,close,volume`(확인). RangeIndex → `_periodic_returns:35` 의 DatetimeIndex 요구를 못 넘김 → `None` → `Decimal("0")`.
→ `expected.json:14` 는 미세 drift 가 아니라 `-0.342…` → `0` 이다. **이것이 `sharpe_convention` 마커의 정당성을 결정적으로 만든다** — 0 을 "0.00" 으로 렌더하면 거짓이므로 `"unavailable"` 마커로 `—` 를 렌더한다. 컨벤션 값이 3종이 아니라 **4종**이 된 이유.

### F2. Trust Layer corpus 는 6 달력월 → Sharpe 크기가 급감하는 게 정상

`scripts/generate_corpus_ohlcv_frozen.py:36-39` — BTCUSDT 1h, 2024-01-01 ~ 2024-07-01(exclusive), ~4,320 bars(확인). 월말 샘플 6개 → 월간 경로. `√4320 ≈ 65.7` 스케일이 사라진다.
→ ① regen 커밋 메시지·dev-log 에 명시해 리뷰어의 버그 오판을 막는다 ② **랭킹 flip 위험이 예상보다 크다**(4320샘플 t-통계량과 6샘플 비율은 통계적으로 거의 무관) → 실측 의무의 가중치 상향.

### F3. `_periodic_returns` daily fallback 은 sub-daily 를 "1 bar = 1 day" 로 센다 (선재 결함)

`metrics.py:41-43` 이 resample 없이 전 bar 를 쓰고 RFR 은 `0.02/365`. **sortino 가 이미 갖고 있는 결함**이고 sharpe 가 재사용하는 순간 전파된다.
→ **이번에 고치지 않는다.** 고치면 sortino 값까지 바뀌어 "sharpe-only diff" 감사 규약(R1)이 깨진다. docstring + FE 문구로 고지하고 신규 백로그 등재.

### F4. ★`ExitOrderKind` 확장 기각 — 두 판단이 충돌했고 3안으로 해소

- 내 실측: `map_exit_kind`/`trigger_direction_for` 는 `src/` 에서 **호출 0건**(로드맵 `BL-365` 가 "dead-code + 서버 미배선"으로 등재). 오늘의 라이브 위험은 없다.
- 설계 에이전트 지적: `exit_order_mapping.py:48` 의 `else` fall-through 가 새 enum 값을 조용히 trigger-market 으로 빌드한다. **BL-365 배선 시점의 잠복 위험**.
- **채택 3안**: enum 은 불변으로 두고 **DB 문자열 컬럼에만** `"liquidation"` 을 기록(`service.py:442`, `models.py:188` max_length=16 = 11자 수용, 마이그레이션 0). Python `exit_kind` 는 `None` 이라 `v2_adapter.py:337` 이 `"taker"` 로 정확히 라우팅. FE 는 기존 컬럼에서 타입 있는 값을 받는다.
- **FE 필수 동반**: `trade-ledger-table.tsx:29` `EXIT_REASON_LABEL` 에 키를 안 넣으면 `:163` 의 `?? "시그널 청산"` 폴백이 **강제청산을 시그널 청산으로 표시**한다. 이 스프린트가 없애려는 바로 그 종류의 거짓말.

## 5. B1↔B2 baseline 충돌은 순서가 아니라 불변식으로 푼다

`regen_trust_layer_baseline.py:197` 이 `run_backtest_v2(source, ohlcv_df)` 를 **config 없이** 호출한다 → `BacktestConfig()` 기본 `leverage=1.0`. 즉 **Trust Layer baseline·golden 은 전부 1x 경로**다.

→ B2 의 신 로직이 전부 `leverage > 1` 게이트 뒤에 있으면 **B2 는 baseline 재생성을 0회 요구**한다. 레버리지가 equity 변동성을 바꿔 sharpe baseline 을 흔들 여지 자체가 없다.
→ 그럼에도 **B1 을 먼저** 놓는다: B2 가 먼저 들어가면 L=1 에서 미세 누출이 생겼을 때 B1 의 regen 이 그 누출을 "기대값"으로 흡수한다(정확히 anti-circular 위반).
→ 이를 순서가 아니라 **커밋 경계 규약 R1/R2** 로 강제한다(operating-contract §3).

## 6. §0 게이트 실측 (2026-07-25)

| 항목               | 결과                                                              |
| ------------------ | ----------------------------------------------------------------- |
| 직전 스프린트 머지 | #477/#478 둘 다 `MERGED`, 열린 PR 0, main @ `a4954e4`             |
| BE baseline        | **2717 passed / 46 skipped** (4:02)                               |
| FE baseline        | **1097 passed / 193 files** — 플랜 예상 1094 대비 **+3 드리프트** |
| BL-388 tripwire    | **6 passed** → 재구현 낭비 차단                                   |
| alembic            | `20260725_0002 (head)`                                            |
| 3-env              | `…5433/quantbridge_test` + `redis://…6380/3`                      |

### ★환경 사고 2건 (코드 무관)

1. **8100 백엔드가 죽은 포트를 향하고 있었다.** PID 66385 가 2026-07-24 08:22 기동이고 인라인 env 가 `DATABASE_URL=...localhost:5436` 인데 5436 은 포트 정렬(5436→5433) 이후 닫혀 있다. 브라우저에는 **CORS 오류로 보이지만 CORS 문제가 아니다** — DB 를 건드리는 요청이 전송 단계에서 실패할 뿐이다. Makefile 은 이미 정정돼 있어 **kill 후 재기동만으로 해소**(설정 변경 0). 해소 후 `/health` ok + DB 접촉 엔드포인트 401/26ms.
2. **`pnpm test --run` 은 조용히 죽는다.** `Unknown option: 'run'` 을 뱉으면서 **exit code 0** 이라 통과한 것처럼 보인다. `package.json:14` 의 `test` 가 이미 `vitest run` 이므로 **`pnpm test`** 가 정답. 워커 자기보고를 믿었다면 FE 게이트를 안 돌린 채 green 으로 보고했을 것이다.

## 7. codex G0 — 7건 중 **5건 수용 · 2건 이미 반영됨** (전건 코드 대조 §7.3)

| 등급     | 지적                                        | 판정                                                                                                                                                                                                                                                                                                             |
| -------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BLOCKING | `running_equity` 를 가용잔고로 쓰면 안 된다 | **수용(개정)** — `interpreter.py:1322` 가 Pine `strategy.equity` 로 그대로 반환함을 **확인**. 마진용으로 전용 금지. → `Trade.margin_used` 를 기록하고 가용을 **파생**(`running_equity − Σ open margin_used`)한다. 상태 중복이 없어 drift 불가                                                                    |
| P1       | 마진 게이트가 stop 진입을 못 막는다         | **수용(진짜 결함)** — `strategy_state.py:620-640` 의 `check_pending_fills` 가 `entry()` 를 **우회해 `Trade(...)` 를 직접 생성**함을 확인. `Trade(` 생성 site 는 정확히 **2곳**(`:509`, `:626`) → **단일 chokepoint `_open_trade()`** 로 통합해 게이트·liq_price 를 한 관문에 둔다. 청산가 캐시도 같은 함정이었다 |
| P1       | `RawTrade` 에도 `liquidated` 가 필요        | **이미 반영됨** — operating-contract §1.2 표에 `RawTrade.liquidated` 가 이미 있다. codex 가 계약 문서를 못 본 것                                                                                                                                                                                                 |
| P2       | FE 라벨맵 미갱신 시 "시그널 청산" 오표기    | **이미 반영됨** — 착수 전 독립 발견해 계약 §1.2 에 FE 의무로 명시                                                                                                                                                                                                                                                |
| P1       | 마커만으로 정렬 혼재가 안 고쳐진다          | **수용(내 주장 정정)** — `repository.py:71-77` 은 원시 JSONB 숫자만 캐스팅하고 convention 을 보지 않는다. 마커는 정렬을 **고치는** 게 아니라 혼재를 **보이게** 한다. → 정렬은 유지하고 "sharpe 정렬 중 + 두 컨벤션 혼재" 시 FE 고지. 완전 해소는 후속 BL                                                         |
| P2       | optimizer/stress 저장 sharpe 도 혼재        | **수용(스코프 밖)** — 두 도메인이 각자 JSONB 에 sharpe 를 저장한다. 3 도메인 동시 마킹은 스코프 폭발 → 문서화 + 신규 BL                                                                                                                                                                                          |
| P2       | golden diff 0 은 게이트 증명으로 불충분     | **수용(R6 신설)** — DB config 에 저장된 비-1 leverage 가 `config_mapper.py:103` → 재실행/optimizer/stress 경로로 엔진에 들어간다. 그 경로의 명시적 회귀 추가                                                                                                                                                     |

**메타 교훈**: 이번 G0 의 최대 수확은 "게이트를 `entry()` 에만 건다"는 내 설계가 **`Trade` 2-site 생성 구조** 때문에 조용히 뚫린다는 것이었다. 같은 구조가 청산가 캐시에도 적용되므로, chokepoint 통합은 두 결함을 한 번에 닫는다. 플랜 단계에서 `check_pending_fills` 를 "체결 판정 선례"로만 읽고 **생성 경로**로는 읽지 않은 것이 원인이다.

### 문서 간 포트 표기 불일치

`docs/archive/sprints/perf-surface/*`·`docs/archive/sprints/money-path-accuracy/*` 는 5436, `docs/archive/sprints/exit-money-path/*` 만 5433 이다. **최신(exit-money-path)이 맞다.** 그래서 본 스프린트 문서는 **포트 숫자를 적지 않고** `.env.local`/Makefile 을 SSOT 로 참조하도록 썼다.

## 8b. ★랭킹 flip 실측 (S3 의무, 2026-07-25)

harness = `scratchpad/measure_sharpe_flip.py`(커밋 대상 아님). 같은 equity 커브에서 **구 수식을 자립 복사**해 신 수식과 동시 산출 → `_sharpe` 삭제 후에도 재현 가능. 셀 = 5 runnable corpus x 3 수수료(0.0002/0.001/0.005) = 15.

**harness 자체 검증**: `s1_pbr@0.001`(= Trust Layer baseline 과 같은 `fees=0.001`)의 구 값이 `+1.141969` 로 baseline `1.14196912` 와 **정확히 일치** → 구 수식 복사가 정확하다.

| 셀                 | 구(bar t-통계량) | 신(TV 월간)              | 총수익률     | trades |
| ------------------ | ---------------- | ------------------------ | ------------ | ------ |
| s1_pbr@0.0002      | +1.302564        | +0.477118                | +1.2941      | 465    |
| s1_pbr@0.001       | +1.141969        | +0.600131                | **−5.3670**  | 465    |
| s1_pbr@0.005       | −1.042714        | −0.171760                | −38.6722     | 465    |
| s2_utbot@0.0002    | −0.261115        | −0.032042                | −0.9556      | 433    |
| s2_utbot@0.001     | −0.421205        | −0.447028                | −7.1913      | 433    |
| **s2_utbot@0.005** | **+0.395549**    | **−0.075683**            | **−38.3698** | 433    |
| s3_rsid@0.0002     | +1.105588        | +0.427723                | +0.7939      | 65     |
| s3_rsid@0.001      | +0.997390        | −0.013884                | −1.0828      | 65     |
| s3_rsid@0.005      | −0.877318        | −0.417151                | −10.4663     | 65     |
| i1_utbot@0.0002    | −0.261115        | −0.032042                | −0.9556      | 433    |
| i1_utbot@0.001     | −0.421205        | −0.447028                | −7.1913      | 433    |
| i1_utbot@0.005     | +0.395549        | −0.075683                | −38.3698     | 433    |
| i2_luxalgo@\*      | 0.000000         | 0.000000 (`unavailable`) | 0.0000       | 0      |

**결과**

- **argmax FLIP** — 구 `s1_pbr@0.0002` → 신 `s1_pbr@0.001`. optimizer `objective_metric="sharpe_ratio"` 의 best-cell 선택이 실제로 바뀐다.
- **Kendall tau = 0.6381** (1.0=동일). F2 예측대로 두 척도는 통계적으로 상당히 무관하다.
- **11/15 셀이 2계단 이상 이동.** 최대 이동 = `s2_utbot@0.005` 4→9, `i1_utbot@0.005` 5→10.
- degenerate 수는 구·신 모두 3(= `i2_luxalgo` 0거래). 신 구현이 `None` 이 아니라 `Decimal("0") + "unavailable"` 을 반환하므로 `grid_search.py:249` dead branch 는 **계속 dead** — 의도한 대로다.
- `s2_utbot` 과 `i1_utbot` 의 값이 전 셀에서 동일하다 — 같은 전략의 Track S / Track A 쌍이므로 정합 확인(baseline 도 둘 다 `-0.42120514`).

**★정직하게 적어야 하는 단서 (과장 금지)**
구 수식의 최대 결함은 `s2_utbot@0.005` / `i1_utbot@0.005` 에서 드러난다 — **자본을 38배 잃은 실행(총수익률 −3837%)에 구 수식이 양수 샤프 `+0.3955` 를 줬다.** 신 수식은 `−0.0757` 로 부호를 바로잡는다. 이것이 이 교체의 핵심 근거다.

그러나 **"신 수식이 모든 곳에서 더 낫다"는 주장은 성립하지 않는다.** corpus 대부분이 이 수수료 수준에서 **equity 가 음수로 내려가고**(총수익률 −537% ~ −3868%), 음수 equity 위에서는 `(cur-prev)/prev` 기반 기간 수익률이 부호까지 뒤집혀 **어떤 비율 지표도 의미를 잃는다**. 실제로 신 수식은 `s1_pbr@0.001`(−537%)을 `@0.0002`(+129%)보다 **높게** 랭크한다. 이는 신 수식의 결함이 아니라 **레버리지 없는 절대-qty 사이징이 만든 판타지 equity**(= `mdd_exceeds_capital` 이 존재하는 이유이자 **B2 가 고치려는 것**)의 증상이다. 따라서 flip 크기의 상당 부분은 B2 이후 재측정해야 최종 해석이 가능하다 → dev-log 에 이 한계를 명시한다.

## 10. B2 배선 검증 실측 (S5b 후, 2026-07-25)

### R2 — leverage=1.0 byte-identity **PASS**

5 corpus 전부 `BacktestConfig()` 기본과 `BacktestConfig(leverage=1.0)` 의 metrics JSONB + 거래 수가 동일.

### R3 — anti-dead-gate **PASS** (6 조합 변화)

`§8d` 의 "before"(L=1 과 L=3 이 소수 19자리까지 동일)와 대비해 이제 실제로 달라진다.

### ★마진 게이트가 corpus 의 내재 레버리지를 정확히 짚어냈다

| leverage | s1_pbr 거래 수 | 해석                   |
| -------- | -------------- | ---------------------- |
| 1x       | 465            | 게이트 없음(현행 유지) |
| 3x       | **0**          | 첫 진입부터 거부       |
| 10x      | 465            | 통과                   |

corpus 전략은 `qty=1 BTC`(2024-01-01 기준 약 $42,000)를 자본 $10,000 으로 잡는다 → **내재 레버리지 약 4.2x**. 3x 로는 증거금이 모자라 첫 진입부터 거부되고 10x 면 통과한다. 즉 **게이트가 "이 전략은 4.2배 레버리지를 요구한다"를 정확히 판정**한다. 1x 에서 이게 통과되던 것이 바로 `mdd_exceeds_capital` 이 존재하던 이유다.

### ★청산 발화 실측 — 레버리지에 따라 물리적으로 정확히 스케일

| leverage | 청산 거리   | 청산 발생     | total_return |
| -------- | ----------- | ------------- | ------------ |
| 1x       | (도달 불가) | **0**         | -5.3670      |
| 25x      | 3.5%        | **8**         | -6.3742      |
| 100x     | 0.5%        | **267 / 466** | -5.2570      |

1x 에서 0건(현물 정합)이고 레버리지가 오를수록 단조 증가한다.

**★측정 함정 1건**: 처음에 `result.trades` 의 `liquidated` 속성으로 셌더니 전부 0이 나왔다. 원인은 `result.trades` 가 `RawTrade` 인데 **`liquidated` 는 아직 `Trade` 에만 있고 `RawTrade` 전파는 S6 작업**이라는 것. `getattr(t,'liquidated',False)` 가 조용히 항상 False 를 돌려줬다. `total_return` 이 레버리지마다 바뀌는 것을 보고 이상을 감지해 `comment` 마커로 재측정했다. **`getattr` 기본값은 미구현 필드를 "정상 False" 로 위장한다.**

## 11. ★★마진 게이트의 실제 한계 — gross equity 를 쓴다 (실측으로 규모 확인)

계약 §3 에 "게이트가 gross `running_equity` 를 써서 약간 낙관적" 이라고 적었는데, **규모를 실측하니 '약간' 이 아니었다.**

`s1_pbr`, leverage=1, 초기자본 10,000:

```
종료 running_equity (gross)  =  +38,678.96
total_return (net)           =  -5.3670  (= -53,670)
```

차이 약 **92,000**. 원인은 `close()`(strategy_state.py:551) 가 **gross pnl 만 누적**하기 때문이다(docstring 의 "fees=0 Sprint 37 가정"). 465거래 x $42k notional x 0.15%(수수료 0.1% + 슬리피지 0.05%) x 2레그 ≈ **$58,590** 의 비용이 엔진 equity 에 반영되지 않는다.

→ **마진 게이트는 실제 순자산이 -53,670 일 때도 +38,679 의 증거금이 있다고 판단한다.** 이 때문에 L=25 에서 466 거래가 한 번도 거부되지 않았다.

### 왜 이번에 고치지 않는가

- 이건 **S5b 가 만든 결함이 아니라 선재 구조**다. 엔진 equity 는 Sprint 37 부터 gross 였다.
- `close()` 를 net 으로 바꾸면 `running_equity` 가 바뀌고, 그것이 `compute_qty`(percent_of_equity)의 입력이자 Pine `strategy.equity`(interpreter.py:1322)의 값이라 **L=1 byte-identity 가 즉시 깨진다**(이번 스프린트의 최상위 불변식).
- `leverage > 1` 에서만 net 으로 전환하는 안은 가능하지만, 그러면 같은 Pine 스크립트가 레버리지 설정에 따라 다른 `strategy.equity` 를 보게 되어 별도 검증이 필요한 스코프 확장이다.

### 그래도 게이트는 무의미하지 않다

**초기 판정은 정확하다** - 초기 자본에서는 gross = net 이다. 실제로 "corpus 전략이 4.2배 레버리지를 요구한다"는 판정(3x 거부 / 10x 통과)은 첫 진입 시점 판단이라 **정확**하다. 오차는 거래가 누적되며 커진다.

→ **정직 고지 의무**: FE 배너에 "증거금 판정은 수수료·슬리피지 차감 전 자본 기준" 을 명시한다. 후속 BL 등재.

## 8d. ★B2 "before" 기준선 실측 — 레버리지는 오늘 완전히 무시된다

B2 착수 전에 R3(anti-dead-gate)의 기준선을 실측해 고정했다. `s1_pbr` corpus 로 `BacktestConfig(leverage=1.0)` 과 `leverage=3.0` 을 각각 돌려 `metrics_to_jsonb` 를 비교:

```
L=1 == L=3 (JSONB 완전 동일)?  True
L=1  465 거래  total_return = -5.3669612764999641713
L=3  465 거래  total_return = -5.3669612764999641713
```

**소수 19자리까지 동일.** 즉 `CreateBacktestRequest.leverage` 가 1~125 범위 검증을 거치고 DB JSONB 를 통과해 `BacktestConfig.leverage` 까지 도달한 뒤 **엔진에서 완전히 무시된다**. 이것이 BL-186a 가 고치는 대상이고, 동시에 `BacktestConfigOut.leverage` 로 응답에 노출되며 `mdd-caption.ts` 가 "leverage Nx 가정" 캡션까지 그릴 준비가 돼 있다는 점에서 **잠복 거짓말**이다.

→ **B2 완료 후 이 두 결과가 반드시 달라져야 한다.** 안 달라지면 게이트를 `if False:` 로 둔 것과 구분되지 않는다(R3).

## 9. ★★설계 전환 — 레버리지 시맨틱을 TV/MT5 컨벤션으로 (사용자 확정)

§8e 에서 "곱하기 모델로 가되 TV 비교 불가를 고지하겠다"고 적었으나, **사용자가 TV 정렬을 지시**했고 1차 출처 조사 결과 **곱하기 모델이 업계 어디에도 없다**는 것이 확인돼 설계를 바꿨다.

### 조사 결과 (1차 출처)

| 플랫폼           | 레버리지가 수량을 바꾸나 | 표현                                                                           | 청산                                              |
| ---------------- | ------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------- |
| TradingView      | ❌                       | `margin_long/short` = 포지션 중 자기 자금 비율(%). 25% → 자본의 400% 까지 진입 | **부분** 청산. 에뮬레이터는 필요액의 **4배** 청산 |
| MT5              | ❌                       | 계좌 레버리지 1:N → 필요증거금 = notional/N                                    | Stop Out, 손실 큰 것부터                          |
| QuantConnect     | ❌                       | `SetLeverage` = 매수여력 상한                                                  | 마진콜                                            |
| 거래소 UI(Bybit) | △                        | **증거금** 입력 × N = notional                                                 | 격리 **전량** 청산                                |

**핵심**: 어디서도 레버리지가 *notional 입력*을 곱하지 않는다. 거래소 UI 조차 곱하는 대상은 **증거금** 입력이다. 우리 `percent_of_equity` 는 notional 기준이라 곱하면 두 컨벤션을 섞는 것이었다.

출처: tradingview.com/support/solutions/43000717375 · 43000628599 · tradingview.com/blog/en/strategy-leverage-24638 · metatrader5.com/en/terminal/help/trading_advanced/margin_forex · mql5.com/en/forum/466267

### 채택 결과 — 설계가 단순해지면서 강해졌다

- **`compute_qty` 를 아예 안 건드린다.** → 레버리지>1 에서도 Pine 사이징이 TV 와 동일 → **TV parity 유지**(제품의 북극성).
- 레버리지 = 필요증거금(notional/leverage) + 청산가. **마진 게이트가 부가기능이 아니라 레버리지의 작동 기제 자체**가 된다.
- 청산은 TV 의 부분청산이 아니라 **Bybit isolated 전량 청산**(우리 사용자는 크립토 무기한 트레이더, `liquidation.py` 가 그 모델). 의도적 divergence → UI 고지.
- BL-186a 의 "사이징+청산 원자성" 우려가 **소멸**한다 — 포지션이 커지지 않으므로 청산 없는 판타지 equity 자체가 생기지 않는다. 그래도 마진 게이트+청산은 함께 출하한다(둘이 곧 모델).

### ★내가 틀렸던 것 — 사이징 상한

사용자에게 "`position_size_pct` 상한 100% 때문에 레버리지 노출을 표현할 수 없다"고 보고했는데 **틀렸다.** 두 필드를 혼동했다.

- `position_size_pct`(BE `le=100`) = **Live Settings 미러 전용**. Live 설정 자체가 `le=100` 이라 이 상한은 **올바르다**(올리면 미러 시맨틱이 깨진다). S9 영역.
- 일반 수동 사이징 = `default_qty_value` 이고 **상한이 없다**(BE `gt=0` 만 / FE `min={0}`, max 없음 / zod `positive()`).
  → **`strategy.percent_of_equity = 1000` 은 지금도 폼에서 입력 가능**하며 **사이징 스키마 변경은 불필요**하다. 사용자의 "leverage 연동 상한" 선택은 이 잘못된 전제 위에서 나온 것이라 즉시 정정 보고했다.

### R3 는 청산이 담당한다

1x 는 IMR=1 이라 청산가가 `entry x 0.005`(사실상 도달 불가 = 현물 정합)지만 3x 는 `entry x 0.672` 라 33% 역행에 청산된다. corpus 는 대형 낙폭이 있어 반드시 트리거된다. leverage=1 은 마진 모델 없음(현행 유지, byte-identity) — 1x 마진 모델은 후속 BL.

## 8e. (폐기됨) 레버리지 사이징 곱하기 모델 — §9 로 대체

**쟁점**: TradingView 는 `strategy()` 의 `margin_long`/`margin_short`(포지션 가치 대비 필요 증거금 %)로 레버리지를 표현하고, **`default_qty_type` 기반 수량은 leverage 로 스케일하지 않는다.** 즉 TV 에서 `percent_of_equity=100` + 10x 는 "자본만큼의 notional 을 열되 증거금은 1/10 만 묶인다" 이지 "notional 이 10배" 가 아니다.

우리가 채택하는 것은 **notional 을 leverage 배로 키우는 모델**이다(`percent_of_equity`/`cash` × leverage, `fixed` 는 절대 수량이므로 불변). 근거:

- 핸드오프와 사용자 인터뷰가 명시적으로 "레버리지 사이징"을 요구했다.
- 리테일 사용자의 기대("10x = 같은 자본으로 10배 포지션")와 일치한다.
- 기존 `mdd_exceeds_capital` 문서(`types.py:161-167`)가 leverage 를 "자본 100% 초과 손실을 해석하는 가정"으로 서술해 온 것과도 정합한다.

**정직 고지 의무 (FE 배너에 포함)**: 이 모델은 **TV 와 직접 비교 불가**하다. 같은 Pine 스크립트를 TV 에서 10x 로 돌린 것과 우리 백테스트 10x 는 다른 것을 계산한다. Trust Layer parity 는 leverage=1 경로만 보장하므로 **parity 자체는 깨지지 않는다**(baseline 은 전부 1x).

→ 이 선택이 뒤집히면 S5b 의 `compute_qty` 분기와 FE 문구가 함께 바뀐다. 사용자에게 명시 보고 후 진행.

## 8c. 전체 스위트가 워커 부분 실행이 놓친 회귀를 잡았다

S1/S2 워커는 지정한 부분 스위트만 돌리고 green 을 보고했다. **평가자가 전체 스위트를 돌리자 1건이 실패**했다.

`tests/api/test_backtests_list.py::test_list_projects_metrics_summary_and_sorts_metrics` 가 목록 응답의 `metrics_summary` 를 **정확한 dict 일치**로 단언하는데, `sharpe_convention` 이 추가되면서 `{'sharpe_convention': None}` 키가 하나 늘었다. 값 `None` 은 구 실행 JSONB 에 키가 없어 나온 **의도한 하위호환 동작**이므로 기대값에 키를 추가하는 것이 옳은 수정이다(사유 주석 동반).

**교훈 재확인**: codex 샌드박스가 로컬 DB 포트를 막아 워커는 DB 의존 테스트를 못 돌린다. 이 테스트가 정확히 그런 API 통합 테스트였다. **전체 스위트는 평가자가 메인 venv 로 직접** 이라는 규약이 실제로 값을 했다.

## 8. B1 S2 배선 완료 (2026-07-25)

`v2_adapter` 는 `metrics.sharpe_ratio()`의 `(Decimal, convention)` 반환을 그대로
`BacktestMetrics`에 전달한다. 기존 `_sharpe`는 삭제했고 `_as_float_series`는
MDD·Sortino 경로를 위해 유지했다.

`sharpe_convention`은 엔진 dataclass, detail schema, JSONB 직렬화, 목록 summary에
동시 추가했다. JSONB 키 누락은 구 실행으로서 `None`이며, 목록 요약은 문자열이
아닌 손상값을 `None`으로 무시한다.

ruff·mypy·지정한 serializer 및 parity 테스트는 green이다. Trust Layer P3는
`s1_pbr`·`s2_utbot`·`s3_rsid`·`i1_utbot`에서 `sharpe_ratio` 키만 red이고
`i2_luxalgo`는 green이다. baseline과 golden fixture는 수정하지 않았다.
