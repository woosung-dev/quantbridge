# 2026-07-26 — live-engine-parity

> 브랜치 `feat/live-engine-parity`.
> 작업 기록(`checklist.md` · `context-notes.md` · `bl-drafts.md`)은 §9 에 따라 이 회고와 [`backlog.md`](../backlog.md) · [`reference/gates-and-traps.md`](../reference/gates-and-traps.md) 로 흡수하고 디렉터리를 비웠다.
> Sprint type **B**. `run_live` 가 `run_historical` 로 넘기지 않던 사이징 equity 기준·leverage·`sessions_allowed`·`pyramiding` 4종을 끝내고, 새로 켜지는 게이트가 조용히 진입을 삼키지 않게 만든다.

---

## 왜 했나

라이브 경로가 백테스트와 다른 인자를 빼먹고 있었다. 사이징 equity 경계는 300바 창에 흔들렸고, `leverage`·세션·피라미딩 게이트는 라이브에서 죽어 있었다. 단순 배선도 위험했다. `leverage` 를 넘기는 즉시 실제 reduce-only 청산 주문을 낼 수 있는 청산 모델도 켜지고, 증거금 부족 진입은 원래 경고만 남겨 조용히 사라진다.

## ★preflight 가 킥오프 전제 4건을 반박했다

| 킥오프 전제                                                    | 실측과 결정                                                                                                                                                          |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `live_signal_states.total_realized_pnl` 을 carry 로 쓸 수 있다 | 기각. 창 스코프 시뮬 값이며 매 tick 덮어써 단조도 아니고 창 이전을 담지 않는다.                                                                                      |
| `Σ orders.realized_pnl` 을 carry 로 쓸 수 있다                 | 기각. 거래소 net과 rejected 주문의 추정 PnL이 섞여 시뮬과 부호까지 달랐다.                                                                                           |
| 라이브 `sessions_allowed` 가 동작할 조건은 이미 갖춰져 있다    | 기각. 라이브 OHLCV는 `RangeIndex`와 `timestamp` 컬럼이라 tz 조건이 예외·경고 없이 no-op 이었다.                                                                      |
| NaN/Inf 기준선은 단순 비교로 fail-closed 된다                  | 기각. `Decimal('NaN') <= Decimal('0')` 은 False가 아니라 `InvalidOperation` 을 raise한다. NaN/Inf는 자본 소진이 아니라 `equity_baseline_missing` 으로 진단해야 한다. |

채택한 carry 는 append-only인 `live_signal_events` 를 `bar_time < window_start` 로 자른 합이다. `sessions_allowed` 는 비어 있으면 프레임을 바꾸지 않고, 값이 있으면 `timestamp` 를 tz-aware 인덱스로 복원해 fail-closed 로 게이트한다. `pyramiding` cap 이 무경고로 신호를 삼킨다는 것도 preflight 에서 확인해 양방향 회귀와 skip 표면화를 같은 스코프에 묶었다.

## ★★D7 — 예측은 맞았지만 이유가 달랐다

16:12Z에 화면이 3건·`5.16879987` 에서 2건·`4.07002377` 로 떨어질 것이라 사실 이전에 기록했고, 16:49Z에 적중했다. 그러나 원인은 창에서 청산이 밀려난 것이 아니었다. `fetch_ohlcv(limit_bars=300)` 은 정확히 300행을 주었고, 12:34 청산은 여전히 창 안이었다.

진짜 원인은 그 거래의 진입 11:50이 창의 bar 0이 되어 EMA를 재현할 수 없었던 것이다. 진입이 열리지 않아 `close()` 가 `None` 을 반환하고, 청산 `bar_time` 은 `window_start` 이상이라 carry 에도 못 들어갔다. 손익이 아무 데서도 세이지 않았다.

이로써 dogfood 계획의 "수정 후에는 carry 만으로 하락하지 않는다" 는 예측도 틀렸다. carry 의 효과는 영구 손실을 보유 기간과 지표 warmup만큼의 **일시 함몰**로 바꾸는 데까지다. 화면 총계는 `Σ live_signal_events.realized_pnl` 원장 SSOT로 바꿔 창과 무관하게 단조로 만들었지만, 사이징 자본의 D2 일시 함몰은 BL-489로 남겼다.

## ★프로덕션 before / after 3종

| 대상                  | 수정 전                                                | 수정 후                                                                                                                                                           |
| --------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 화면 총계 원장 SSOT   | 16:54:57Z 화면 3건·`4.78803856`, 원장 4건·`5.88683554` | 17:10:50Z 화면 4건·`5.88683554` = 원장 4건·`5.88683554`. 17:23Z에도 5건·`5.01015117` 로 2회 연속 일치했다.                                                        |
| `equity_curve` 트리거 | 청산 1건에 15:50Z→16:12Z 동안 +10 pts가 append 됐다.   | 청산 0건·tick 24회에는 +0, 청산 1건에는 정확히 +1. 이후 4건 201, 5건 202, 6건 203으로 1:1을 3회 연속 지켰다.                                                      |
| G2-fix 라이브 도달    | 미측정.                                                | `has_full_skips=f`, `has_lastbar_skips=t`, `has_liq=t`, `liquidation_count=0`. 화면 6건·`4.42411763` = 원장 6건·`4.42411763` 이며 curve 203 pts / 청산 6건이었다. |

## 적대 검증은 무엇을 잡고 무엇을 기각했나

- 잡은 것. carry 조회를 `run_live` 의 `try` 밖으로 옮겨 DB 오류가 Pine 발산으로 둔갑하지 않게 했고, 비유한 기준선·Decimal 합산·창 경계·carry=0 음성 케이스·오라클 주석을 바로잡았다. `leverage` 배선이 청산 모델까지 켜는 머니-패스라는 D12도 이 검증에서 확인했다.
- 기각한 것. `status='failed'` 이벤트를 carry 에서 빼자는 제안은 받지 않았다. carry 의 정의는 무한 replay라면 얼마인가이며, 창 안 청산은 dispatch 결과와 관계없이 모두 센다. carry에만 status 필터를 걸면 창 안과 밖의 규칙이 갈려 경계 불연속이 되살아난다.
- 기각한 것. `Σ orders.realized_pnl` 을 원장이나 carry로 쓰자는 제안도 받지 않았다. 같은 청산의 pine_v2 gross `+1.09877350` 과 거래소 net `-1.09767393` 은 수수료 때문에 부호까지 달랐고, rejected 주문의 추정 `+4.87330864` 도 합계에 섞였다. 시뮬 PnL과 거래소 PnL은 같은 누적기에 넣을 수 없다.

## ★내가 틀린 것 2건

1. 플랜 위험표에 레버리지 배선으로 청산 모델이 켜져도 무해하다고 적었다. 실제로는 관측이 아니라 `comment="liquidation"` close 신호에서 `LiveSignalEvent`를 거쳐 실제 reduce-only 주문을 내는 머니-패스 동작이었다. 2x에서는 진입가 x `0.50500`, 125x에서는 진입가 x `0.99700` 이 청산가라 후자는 하락 0.30%면 닿는다.
2. dogfood 계획에 수정 후에는 carry 만으로 손익 하락이 막힌다고 적었다. D7의 entry-outside / close-inside 구간은 carry가 세지 못하므로, 그 하락을 막지 못한다.

## 판별력 변이 10종

| 변이                                | 결과         | 음성  |
| ----------------------------------- | ------------ | ----- |
| M-A `window_start := last_bar_time` | 8 FAIL       | GREEN |
| M-B 창 경계 `<` → `<=`              | 1 FAIL, 실DB | GREEN |
| M-C `carry := 0`                    | 5 FAIL       | GREEN |
| M-D `leverage` forward 절단         | 2 FAIL       | GREEN |
| M-E `sessions_allowed` forward 절단 | 1 FAIL       | GREEN |
| M-F `pyramiding` forward 절단       | 1 FAIL       | GREEN |
| M-G tz 인덱스 수리 제거             | 1 FAIL       | GREEN |
| M-H entry-skip dedupe 가드 제거     | 1 FAIL       | GREEN |
| M-I 청산 표면화 절단                | 1 FAIL       | GREEN |
| M-J 마지막 bar 필터 제거            | 1 FAIL       | GREEN |

매 변이에서 음성 95/96이 GREEN을 유지했고, `MUTANT` 잔존은 0, 복원은 바이트 동일이었다. BL-487의 판별력은 소형 객체 `id()` 재사용 1000/1000으로 원리를 증명했고, Redis 객체는 격리 200회에서 재현하지 않아 그 한계도 그대로 남겼다.

## 게이트

| 게이트            | 기준선 | 실측                                                          |
| ----------------- | ------ | ------------------------------------------------------------- |
| BE pytest         | 3074   | **3102**                                                      |
| FE vitest         | 1151   | **1156**                                                      |
| design-canon      | 32     | 32. 단 `PLAYWRIGHT_BASE_URL=http://localhost:3100` 이 필수다. |
| e2e:authed        | 65-0   | 65-0                                                          |
| ruff / mypy / tsc | 0      | 0                                                             |
| 마이그레이션      | 미측정 | 0                                                             |

canon 기본값 3000은 `<title>Nexus — AI 챗봇 포털</title>` 이었고, 격리 3100은 `<title>QuantBridge</title>` 이었다. 3000에서 나온 27/32는 실패 5건보다 위험한 거짓 그린이었다. 3100으로 재실행한 결과가 32다.

## 신규 BL 4건

- **BL-488 P1.** 평가 갭이 orphan close를 만들어 보유분 없는 `reduce_only` 주문과 시뮬 손익 오염을 낸다. 252바 중 180바만 평가되고 13:10~13:59에 50분 구멍이 있었으며, 청산은 발주됐지만 진입 이벤트는 0건이었다.
- **BL-489 P2.** D2 구간에서 사이징 자본이 일시 함몰한다. 화면 총계는 이번에 원장 SSOT로 해결했지만 `initial_capital`은 별도 설계가 남았다.
- **BL-490 P2.** `margin_mode`가 엔진에 전달되지 않고 청산 모델은 isolated 전용이다. cross 사용자는 실제보다 이르게 강제 청산으로 판정될 수 있다.
- **BL-491 P3.** 백테스트 폼이 Live 레버리지를 미러하지 않는다. 이번에는 거짓 문구만 바로잡았고 실제 미러링은 미착수다.

## 문서 종결

`gates-and-traps.md` 에 이번의 재발 방지 지식을 승격했다(함정 6종). 세 작업 기록은 이 회고와 `backlog.md`(신규 BL 4건 + Resolved 5건)·정본으로 전부 흡수했고 커밋하지 않았다. **`docs/` 최상위는 10 을 유지한다.** 마이그레이션은 0 이다.
