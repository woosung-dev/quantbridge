# Step 0: parse-call-census-harness

## 읽어야 할 파일

- `apps/api/src/strategy/pine_v2/compat.py` (`parse_and_run_v2` 전문)
- `apps/api/src/strategy/pine_v2/ast_classifier.py` (`:119` `pyne_ast.parse`)
- `apps/api/src/strategy/pine_v2/ast_extractor.py` (`:382` `pyne_ast.parse`)
- `apps/api/src/strategy/pine_v2/event_loop.py` (`:125` `parse_to_ast`)
- `apps/api/src/strategy/pine_v2/virtual_strategy.py` (`:194`) · `alert_hook.py` (`:388`)
- `apps/api/tests/strategy/pine_v2/test_execution_stage_breakdown.py` — **프로즌 OHLCV 로딩 방법의 정본**
- `apps/api/tests/strategy/pine_v2/test_execution_speed.py` — `:140-186` (이 step 이 수리할 양성 대조)

## 배경 — 이미 실측된 사실 (다시 재지 마라)

한 번의 `run_backtest_v2(source, ohlcv)` 는 **같은 소스를 4번 파싱한다.** 4회 전부 동일 sha1 이
확인됐다(`s3_rsid` = `162ad75b4451f2e16b09f0980464b5dbc76957b3`, 6555B). 호출 스택:

| # | 좌표 | 경로 |
| --- | --- | --- |
| 1 | `ast_classifier.py:119` | `compat.py:82 classify_script` |
| 2 | `ast_extractor.py:382` | `compat.py:85` → `sizing.py:60 resolve_default_qty` → `sizing.py:13` |
| 3 | `ast_extractor.py:382` | `compat.py:104 extract_content` |
| 4 | `event_loop.py:125` | `compat.py:106` → `track_runner.py:94 invoke` → `run_historical` |

Track A(indicator + alert)는 4번이 `virtual_strategy.py:194` → `alert_hook.py:388` 로 갈려 **5회**다.

★**4회는 조건부가 아니라 무조건이다** — `v2_adapter.py:93` 이 `initial_capital=float(cfg.init_cash)` 를
항상 채우고 `types.py:28` 기본값이 `Decimal("10000")` 이라 `sizing.py:57-58` 의 early-return 을 안 탄다.

## 작업

### ⑴ 신설 — `apps/api/tests/strategy/pine_v2/test_parse_call_census.py`

파스 호출을 세는 하네스와 그 **판별력 대조**를 만든다. 이 step 에서는 **제품 코드를 고치지 않는다** —
현재 관측값(4·5)을 기계로 박는 것이 산출이다. 다음 step 이 그 상수를 1 로 바꿔 red→green 을 만든다.

계측 지점은 **`pynescript.ast.parse`** 다. `ast_classifier`·`ast_extractor`·`parser_adapter` 가 전부
`from pynescript import ast as pyne_ast` 후 `pyne_ast.parse(...)` 로 **호출 시점에 모듈 속성을 조회**하므로
`monkeypatch.setattr("pynescript.ast.parse", wrapper)` 하나가 네 경로를 다 덮는다.

기록할 것 = 호출마다 `(sha1(source), len(source))`. 상수는 모듈 상단에 이름 있는 값으로 둔다:

```python
_EXPECTED_TRACK_S_PARSES = 4  # step1 에서 1 로 바뀐다
_EXPECTED_TRACK_A_PARSES = 5  # step1 에서 1 로 바뀐다
```

필수 테스트 4종:

1. **Track S 계수** — `run_backtest_v2(<Track S corpus>, frozen_ohlcv)` 1회의 파스 호출 수가
   `_EXPECTED_TRACK_S_PARSES` 와 같고, **기록된 sha1 이 전부 같은 값 1종**임을 단언한다.
2. **Track A 계수** — 같은 방식으로 `_EXPECTED_TRACK_A_PARSES`. corpus 는 `classify_script` 로
   Track 을 확인해 고른다(`i*.pine` 중 alert 를 쓰는 것). **어느 파일인지 추측하지 말고 코드로 판별해라.**
3. **양성 대조** — 래퍼를 씌운 상태에서 `pynescript.ast.parse` 를 **직접 N회**(N≥3) 부르면 카운터가
   정확히 N 이 되는 것. 「캐시가 아니라 카운터가 고장나서 작은 수」를 배제한다.
4. **음성 대조** — 래퍼를 씌우고 **아무것도 파싱하지 않으면** 카운터가 0 인 것.

corpus 는 **소요가 짧은 것**을 골라라 — `s5_ema_trend` 콜드 2.61s / 웜 0.006s 로 실측됐고,
`s3_rsid`(콜드 11.55s) · `i3_drfx`(콜드 52.37s) 는 AC 를 무겁게 만든다. **계수는 corpus 무관하다.**

### ⑵ 수리 — `test_execution_speed.py` 의 판별력 0 인 양성 대조

`test_execution_speed_ratio_guard_rejects_tampered_baseline`(`:178-186`)은 baseline 의
`ratio_to_fastest` 를 10배로 키운 뒤 `pytest.raises(AssertionError, match="ratio_to_fastest")` 를 건다.
그런데 `_assert_relative_ratio_regression` 은 `:149` 의 **baseline 내부 정합 검사**
(`_assert_ratios_match_bars_per_second(baseline_corpora, label="baseline")`)에서 먼저 터지고,
그 메시지에도 `ratio_to_fastest` 가 들어 있어 `match=` 가 갈라내지 못한다.
⇒ **`:154` 의 `actual_ratio <= baseline_ratio * 2.0` 회귀 임계는 한 번도 실행된 적이 없다.**

`_RATIO_REGRESSION_LIMIT = 2.0` 축을 **실제로 통과하는 양성 대조**를 추가해라:
`bars_per_second` 와 `ratio_to_fastest` 의 **정합을 유지한 채** 한 corpus 만 임계 밖으로 밀어
(= 그 corpus 의 measured ratio 가 baseline ratio 의 2배를 넘게) `:154` 가 발화하는 것을 단언한다.
기존 대조는 지우지 말고 **남겨라** — 그것은 내부 정합 축의 대조로 유효하다. 두 대조의 `match=` 는
서로 다른 문자열이어야 한다(같으면 다시 구분이 안 된다).

## Acceptance Criteria

```
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_parse_call_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/pine_v2/test_parse_call_census.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_speed.py -k ratio_guard -q
cd apps/api && uv run ruff check tests/strategy/pine_v2
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 **실제 관측된 계수**(Track S / Track A)와 **고른 corpus 이름**을 적어라.
   다음 step 이 그 상수를 뒤집는다.
3. 프로젝트 규약: `apps/api/AGENTS.md` 3-Layer · Decimal-first · 테스트 위치.
4. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`src/` 를 한 줄도 고치지 마라.** 이유: 이 step 의 산출은 「현재가 4다」라는 관측이고,
  제품 코드가 같이 바뀌면 다음 step 의 red→green 이 무엇 때문인지 갈리지 않는다.
- **시간(초)을 단언하지 마라.** 이유: 같은 파스가 머신 부하로 8.97~16.15초까지 흔들린 기록이 있고,
  호출 횟수는 같은 입력에서 결정적이다(다른 프로세스 2회에서 `adaptivePredict` 3672 완전 일치).
- `test_execution_speed.py` 의 **기존 양성 대조를 삭제하지 마라.** 이유: 그것은 내부 정합 축의
  유효한 대조다. 없애는 것이 아니라 **두 번째 대조를 더하는 것**이 이 작업이다.
- 픽스처 JSON(`tests/fixtures/pine_corpus_v2/*.json`)을 만지지 마라. 이유: step 3 소관이다.
- 커밋하지 마라(커밋은 러너 소관).
