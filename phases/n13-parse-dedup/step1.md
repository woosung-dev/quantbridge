# Step 1: route-parse-through-cached-adapter

## 읽어야 할 파일

- 앞 step 의 `summary` (관측된 계수와 고른 corpus)
- `apps/api/src/strategy/pine_v2/parser_adapter.py` — **11줄짜리 파일. 여기가 작업의 중심이다**
- `apps/api/src/strategy/pine_v2/ast_classifier.py:119` · `ast_extractor.py:382` · `alert_hook.py:388`
- `apps/api/src/strategy/router.py:38-48` — 파스 엔드포인트의 rate limit **부재**를 직접 확인해라
- `apps/api/src/strategy/schemas.py` — `pine_source` 의 길이 상한 **부재**
- `apps/api/tests/strategy/pine_v2/test_execution_hotspots.py:121-130` — `_function_coordinates`

## 배경 — 이 step 의 함정 하나

★**`parse_to_ast` 에만 캐시를 걸면 한 백테스트 안에서 제거되는 중복은 0건이다.**
4파스 중 `parser_adapter.parse_to_ast` 를 지나는 것은 **1회**(`event_loop.py:125`)뿐이고,
콜드 11.23초를 무는 **첫 파스는 `ast_classifier.py:119` 의 직접 `pyne_ast.parse`** 다.

`parser_adapter.py:1` 의 docstring 은 「이 파일만 `import pynescript` 허용」이라고 적혀 있지만
**실제로는 8개 파일이 직접 import 한다**(`ast_classifier.py:25` · `ast_extractor.py:22` ·
`ast_metrics.py:13` · `interpreter.py:38` · `alert_hook.py:37` · `signal_extractor.py:92,307` ·
`parser_adapter.py:10` · 도메인 밖 `backtest/engine/v2_adapter.py:23`).
같은 디렉터리 `README.md:12` 는 「둘」이라고 적어 **문서끼리도 어긋나 있다.**

## 왜 이 값이 큰가 — 옵티마이저

`src/optimizer/engine/grid_search.py:241` · `genetic.py:509` · `bayesian.py:391` 이
**동일한 `pine_source`** 로 `run_backtest` 를 셀마다 반복 호출한다. grid 는 9셀 상한이지만
genetic 은 `population_size * (n_generations + 1)` 이고 상한이 `population_size ≤ 200`(`schemas.py:165`) ·
`n_generations ≤ 100` 이다. 즉 **한 번의 최적화가 같은 소스를 최대 20,200 × 4 = 80,800번 파싱**한다.
프로세스 수명 캐시는 그것을 **1회**로 만든다. 이 step 의 값은 백테스트 1건이 아니라 여기에 있다.

## 작업

### ⑴ 세 직접 호출을 `parse_to_ast` 경유로 바꾼다

`ast_classifier.py:119` · `ast_extractor.py:382` · `alert_hook.py:388` 의 `pyne_ast.parse(source)` 를
`parse_to_ast(source)` 로 바꾼다.

★**세 파일 다 `pyne_ast` 를 `isinstance` 판정에도 쓰므로 기존 import 를 지우지 마라.**
`parse_to_ast` import 를 **추가**하는 형태다.

★**`ast_classifier.py` 는 줄 번호가 밀리면 픽스처 가드가 red 가 된다.**
`test_execution_hotspots.py:150-170` 이 `classify_script` 를 `:117` 로 박아 두었고,
`_function_coordinates`(`:121-130`)는 함수 정의 줄과 **데코레이터 줄**만 좌표로 인정한다.
step 3 이 재생성하므로 red 자체는 허용이지만, **이 step 의 AC 에 그 테스트를 넣지 않은 이유가 그것**이다.
줄 밀림을 피하려고 코드를 부자연스럽게 압축하지 마라 — 재생성이 정규 절차다.

### ⑵ `parse_to_ast` 에 캐시를 건다

```python
@lru_cache(maxsize=8)
def parse_to_ast(source: str) -> Any:
    ...
```

★**`maxsize=None`(`@cache`) 금지.** 이유: `POST /api/v1/strategies/parse`(`router.py:38-44`)에
**rate limit 이 없고**(바로 아래 `:48` 이 `@limiter.limit("30/minute")` 를 걸어 둔 것이 대조군)
`pine_source` 에 **길이 상한도 없다**(`schemas.py` `Field(min_length=1)`). 무제한 캐시는
임의 입력으로 채워지는 메모리 표면이 된다. 실측 참고: 39KB 소스(`i3_drfx`)의 AST 노드 수 10,289.

`maxsize` 의 구체 값은 세션 재량이되 **한 자릿수~수십**을 넘기지 마라. 고른 근거를 docstring 에 적어라.

★**`parser_adapter.py` 의 docstring 을 사실에 맞게 고쳐라** — 「이 파일만 import 허용」은 거짓이다.
지금 참인 문장은 「**파싱 진입점은 이 파일 하나**」다(`isinstance` 판정용 import 는 여러 곳에 있다).
같은 디렉터리 `README.md:12` 도 같이 맞춰라. 그 외 문서는 이 step 의 범위가 아니다.

### ⑶ step 0 의 상수를 뒤집고 대조를 2종 더한다

`_EXPECTED_TRACK_S_PARSES` · `_EXPECTED_TRACK_A_PARSES` 를 **1** 로 바꾼다.
그리고 `test_parse_call_census.py` 에 아래 둘을 **추가**한다:

5. **캐시 우회 양성 대조** — 같은 백테스트를 소스 끝에 개행 1개를 더한 문자열로 한 번 더 돌리면
   파스 카운터가 **다시 증가**하는 것. 「캐시가 아니라 계측이 죽어서 1」을 배제한다.
6. **예외 음성 대조** — 파싱에 실패하는 소스로 `parse_to_ast` 를 **두 번** 부르면 **두 번 다** 예외가
   나는 것. `functools` 캐시는 예외를 캐시하지 않으므로 이것이 참이어야 한다.
   (재료 = `tests/strategy/pine_v2/` 안의 기존 파스 실패 테스트를 찾아 그 소스를 재사용해라.)

## Acceptance Criteria

```
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_parse_call_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/pine_v2/test_parse_call_census.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2 -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/backtest tests/optimizer -q
cd apps/api && uv run ruff check src/strategy tests/strategy
```

★`tests/strategy/pine_v2` 전량에 `test_execution_hotspots.py` 의 좌표 단언이 포함된다 —
줄 밀림으로 red 가 나면 **픽스처를 손으로 고치지 말고** `REGEN_EXECUTION_HOTSPOTS=1` 로 재생성해라
(그것이 step 3 의 작업이지만, 이 step 의 AC 를 통과시키기 위해 필요하면 여기서 해도 된다).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 ⑴ 고른 `maxsize` 와 근거 ⑵ 재생성한 픽스처가 있으면 무엇인지 ⑶ 파스 계수가
   4→1 · 5→1 로 실제로 바뀐 것을 적어라.
3. 규약: `apps/api/AGENTS.md`.
4. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 후 즉시 중단.

## 금지사항

- **`pynescript` 를 수정하지 마라**(`.venv` 안). 이유: 라이선스 경계이고 재설치로 사라진다.
- **`interpreter.py` · `event_loop.py` · `virtual_strategy.py` 의 파싱 외 로직을 건드리지 마라.**
  이유: 이 회차는 파스 횟수만 바꾼다. 실행 의미가 바뀌면 golden oracle 테스트가 무엇 때문에
  움직였는지 갈리지 않는다.
- **시간(초)을 단언하지 마라.** 이유: step 0 과 같다.
- **AST 노드를 복사(`deepcopy`)해서 반환하지 마라.** 이유: 안전성 집행은 step 2 가 **부재 단언**으로
  한다. 여기서 복사를 넣으면 step 2 의 census 가 무엇을 지키는지 흐려지고, 실측상 복사는
  웜 파스보다 65배 싸지만 **불필요한 비용**이다(변형이 0건이므로).
- 커밋하지 마라(커밋은 러너 소관).
