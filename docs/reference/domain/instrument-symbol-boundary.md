# 심볼 경계 — 어디까지가 `BTC/USDT` 이고 어디부터 `BTC/USDT:USDT` 인가

> **정본.** 코드와 어긋나면 코드가 맞다 — 이 문서를 고쳐라.
> 출처: BL-530(라이브 계기 정렬) · **BL-535**(백테스트 계기 정렬).
> 선행 프리미티브: `src/common/normalized_symbol.py`(BL-454) · `src/market_data/constants.py`.

---

## 0. 한 줄 규칙

**사람과 DB 원장이 보는 것은 시장(`BTC/USDT`)이고, 봉과 주문이 나가는 것은 상품(`BTC/USDT:USDT`)이다.
변환은 _시장 → 상품_ 한 방향뿐이고, 그 변환이 일어나는 자리는 손에 꼽을 수 있어야 한다.**

이 규칙이 없으면 BL-530 이 실측한 결함이 그대로 재발한다 — 엔진은 스팟 봉으로 스톱을 체결시키고
거래소 perp 는 그 근처도 안 가서, 엔진만 믿는 유령 포지션이 생기고 그 청산은 전량 거절된다.

---

## 1. 표기 3층

| 층                    | 표기            | 만드는 함수                                                | 누가 쓰나                                                       |
| --------------------- | --------------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| **canonical (시장)**  | `BTC/USDT`      | `normalize_symbol` / `normalize_symbol_input`(요청 경계)   | DB 컬럼 · API 요청/응답 · UI · 전략 · 세션 스코프 · 원장 매칭   |
| **instrument (상품)** | `BTC/USDT:USDT` | `to_ccxt_perpetual_symbol` (`market_data/constants.py:34`) | CCXT OHLCV fetch · `ts.ohlcv` 저장 키 · `funding_rates` 조회 키 |
| **exchange raw**      | `BTCUSDT`       | `to_bybit_raw_symbol` (`market_data/constants.py:48`)      | Bybit 원장/포지션 응답 대조                                     |

★**새 변환 함수를 만들지 마라.** 위 세 개가 전부다. `to_ccxt_perpetual_symbol` 은 idempotent 이고
(`BTC/USDT:USDT` 를 다시 넣어도 그대로), 인식 불가 심볼은 `ValueError` 를 그대로 올린다.

---

## 2. 경계선 — 어느 코드가 어느 층을 보는가

### 2.1 canonical 로 **남는다** (변경 금지)

| 자리                                                         | 값                                        |
| ------------------------------------------------------------ | ----------------------------------------- |
| `backtest/models.py:61` `Backtest.symbol`                    | `BTC/USDT` — 기존 행 불변                 |
| `backtest/schemas.py:31` 백테스트 생성 요청                  | `BTC/USDT`                                |
| `backtest/service.py:293` `provider.get_ohlcv(bt.symbol, …)` | `BTC/USDT` — 변환은 provider 안에서       |
| `optimizer/service.py:243` · `stress_test/service.py:329`    | `BTC/USDT` — 위와 같은 이유               |
| `backtest/service.py:576` `TradeOhlcvResponse.symbol`        | `BTC/USDT` — 화면은 시장 이름을 본다      |
| `trading` 세션·주문·원장 (`LiveSignalSession.symbol` 등)     | `BTC/USDT` — BL-530 이 명시적으로 고정    |
| `market_data/providers/fixture.py` CSV 파일명                | `BTC/USDT_1h.csv` — 픽스처는 머니-패스 밖 |
| 프론트엔드 전 화면                                           | `BTC/USDT`                                |

### 2.2 instrument 로 **바뀐다**

| 자리                                                                                      | 이 스프린트      |
| ----------------------------------------------------------------------------------------- | ---------------- |
| `market_data/providers/timescale.py:59` `get_ohlcv` 의 lock·gap·fetch·insert·get_range 키 | **신규(BL-535)** |
| `backtest/service.py:551` `trade_ohlcv` 의 `get_range` — perp 우선, 없으면 legacy 스팟    | **신규(BL-535)** |
| `tasks/live_signal.py:1359` CCXT `fetch_ohlcv` 인자                                       | 기존(BL-530)     |
| `backtest/service.py:340` `funding_repo.get_funding_series(symbol=…)`                     | 기존(C6)         |

### 2.3 왜 경계가 `TimescaleProvider` 인가

세 소비자(backtest · optimizer · stress_test)가 전부 `OHLCVProvider` 프로토콜 하나를 지나간다
(`market_data/providers/__init__.py:14`). 변환을 소비자마다 두면 3벌이 되고 갈린다 —
BL-454 가 지적한 결함이 정확히 그 형태였다. 그래서 **프로토콜 경계 안쪽 한 자리**에서 바꾼다:

- 프로토콜 **시그니처는 canonical 을 받는다** — 호출자·DB·UI 는 아무것도 안 바뀐다.
- 프로토콜 **안쪽은 instrument 로 쓰고 읽는다** — 저장 키와 거래소 fetch 가 항상 같은 상품이다.
- `FixtureProvider` 는 같은 프로토콜의 다른 구현이고 변환을 하지 않는다. 픽스처는 CSV 파일명이
  곧 키라서 상품 개념이 없고, 머니-패스도 타지 않는다(`settings.ohlcv_provider="fixture"`가 기본).

★`CCXTProvider._build_exchange` 의 `"defaultType": "spot"`(`providers/ccxt.py:46`)은 **건드리지 않는다.**
콜론 표기를 넘기면 ccxt 가 그 market 을 직접 찾으므로 defaultType 은 무시된다 — BL-530 이 라이브에서
외부 오라클로 확정한 사실이다. defaultType 을 바꾸면 콜론 없는 심볼의 해석까지 조용히 달라진다.

---

## 3. 기존 데이터 — 마이그레이션 0

- `ts.ohlcv` 의 PK 는 `(time, symbol, timeframe)` 이다. perp 는 **다른 `symbol` 값**이므로 신규 행이다.
  기존 스팟 행은 **UPDATE 도 DELETE 도 하지 않는다.** 알렘빅 리비전 0개.
- 기존 스팟 행은 `OHLCVRepository.get_range("BTC/USDT", …)` 로 여전히 그대로 읽힌다.
  회귀 잠금: `tests/market_data/test_backtest_instrument_parity.py::TestLegacySpotRowsAreUntouched`.
- 이미 저장된 백테스트 결과(metrics·trades·equity_curve)는 재계산하지 않으므로 값이 바뀌지 않는다.
- 시딩은 별도 작업이 아니다 — `TimescaleProvider` 가 cache-first 라 **백테스트 1회가 곧 perp 시딩**이다
  (`Makefile:246` 의 dogfood-restore 선례와 같은 성질). ★이것이 [BL-469](../../backlog.md#bl-469) 에서
  `market_data.backfill_ohlcv` 를 **되살리지 않고 제거한** 근거다 — 별도 백필 경로가 필요 없다.

### 3.1 `trade_ohlcv` 의 fallback 이 있는 이유

거래 상세 차트는 엔진이 재생한 것과 **같은 상품**을 그려야 한다. 안 그러면 스톱 마커가 그려진 봉의
고저 밖에 놓이고, 화면이 발산을 은폐한다.

그런데 어떤 백테스트가 어느 상품으로 돌았는지는 행에 적혀 있지 않다(컬럼 추가 = 마이그레이션 ≠ 0).
그래서 규칙은 **perp 우선, 그 창에 perp 행이 없으면 legacy 스팟**이다.

- 신규 백테스트 → perp 행이 방금 채워졌으므로 항상 perp 를 그린다.
- 기존 백테스트 → 그 창에 perp 가 없으면 예전과 똑같이 스팟을 그린다(빈 차트 회귀 없음).
- **알려진 잔여** — 기존 백테스트의 창에 나중에 perp 가 채워지면 그 차트는 perp 를 그린다.
  실측 괴리 0.04~0.066% 라 차트 축척에서 보이지 않는다. 정확히 알아야 하면 BL 로 컬럼을 판다.

---

## 4. 파급되지 **않는** 것 (착각 방지)

- **화면 문자열** — `TradeOhlcvResponse.symbol` 은 계속 `BTC/USDT` 다. 라이브 세션이 canonical
  `sess.symbol` 을 들고 perp 에 주문하는 것과 같은 컨벤션이다. 시장 이름과 상품 표기는 다른 층이다.
- **전략** — Pine 소스에도 전략 저장에도 심볼이 없다. 심볼은 백테스트/세션이 들고 있다.
- **`normalize_symbol` 의 관대함** — 요청 경계 강화는 `normalize_symbol_input` 에만 있다(BL-454 주석).
  이 스프린트는 그 경계를 건드리지 않았다.

## 5. 알려진 잔여 / 실패 모드

- **USDT-margined 아닌 시장은 fail-loud 로 바뀐다.** `BTC/USD` 백테스트는
  `to_ccxt_perpetual_symbol` 이 `BTC/USD:USD` 를 만들고 Bybit 에 그런 market 이 없어 fetch 가 실패한다.
  이전에는 조용히 **스팟 봉**이 왔다. 라이브(BL-530)가 이미 같은 성질이므로 두 축이 이제 같다 —
  틀린 상품으로 조용히 도는 것보다 낫다는 판단이다. 플랫폼은 현재 Bybit USDT perp 만 지원한다
  (`CONTEXT.md` 계정 모드).
- **기존 백테스트 재실행은 값이 달라진다.** 같은 파라미터로 다시 돌리면 perp 봉을 쓰므로 결과가
  이전 실행과 정확히 일치하지 않는다. 그것이 BL-535 가 원한 변화다.
