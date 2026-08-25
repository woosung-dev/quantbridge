# Step 2: enforce-ast-immutability

## 읽어야 할 파일

- 앞 두 step 의 `summary`
- `apps/api/src/strategy/pine_v2/parser_adapter.py` (step 1 이 캐시를 건 자리)
- `apps/api/src/strategy/pine_v2/` 전 파일 · `apps/api/src/backtest/engine/v2_adapter.py`
- 기존 AST 정적 census 의 선례 — `git log --oneline --all -- 'apps/api/tests/**/*census*'` 로 찾아
  **있으면 그 형태를 따라라**(새 형식을 발명하지 마라)

## 왜 이 step 이 있나

step 1 이 넣은 캐시는 **같은 AST 객체를 여러 소비자에게 나눠 준다.** 소비자 중 하나라도 트리를
변형하면 다음 소비자가 오염된 트리를 본다 — 그리고 그것은 **조용히 틀린 백테스트 결과**로 나온다.

착수 전 census 는 변형 **0건**을 관측했다. pynescript AST 노드는 `@dataclass` 이고
`frozen` 도 `__slots__` 도 아니라 **언어 차원의 보호가 없다.** 그러므로 이 step 이 하는 일은
「지금 0건」을 **기계로 고정**해서 다음 사람이 변형을 넣으면 red 가 나게 만드는 것이다.

## 작업

신설 — `apps/api/tests/strategy/pine_v2/test_ast_immutability_census.py`

`ast` 모듈로 `apps/api/src/strategy/` · `apps/api/src/backtest/` 의 파이썬 소스를 정적 분석해,
**pynescript AST 노드에 대한 변형 연산이 0건**임을 단언한다.

탐지 대상(최소):

1. `ast.Attribute` 를 `Store` / `Del` 문맥으로 쓰는 대입 (`node.body = ...`, `del node.x`)
2. `ast.Subscript` 를 `Store` / `Del` 문맥으로 쓰는 대입 (`tree.body[0] = ...`)
3. `setattr(...)` / `delattr(...)` 호출
4. 리스트 in-place 메서드 호출 (`.append` · `.extend` · `.insert` · `.pop` · `.remove` · `.clear` ·
   `.sort` · `.reverse`) 중 **수신자가 AST 노드에서 파생된 이름**인 것

★**어떤 이름이 「AST 노드에서 파생」인지 판별하는 규칙을 명시적으로 정의하고 docstring 에 적어라.**
가장 단순한 성립 가능한 규칙: `parse_to_ast(...)` · `pyne_ast.parse(...)` 의 반환을 받은 지역 이름과,
그 이름에서 속성/첨자로 파생된 이름들. 규칙이 좁으면 사각이 생기고 넓으면 위양성이 난다 —
**둘 다 대조로 증명해라**(아래).

### ★대조 2종 — 이것이 이 step 의 전부다

- **양성 대조(필수)** — 탐지 대상 **1~4 각각**에 대해 합성 위반 코드를 만들어
  탐지기가 **전부 잡는 것**을 단언한다. 합성 코드는 임시 파일이나 문자열 소스로 만들고
  **`src/` 에 심지 마라.**
- **음성 대조(필수)** — AST 와 무관한 정상 코드(예: 지역 리스트에 `.append`, dict 대입,
  `dataclasses.replace` 로 새 객체를 만드는 것)에서 탐지기가 **0건**을 내는 것.
  ★이 대조가 없으면 「전부 위반으로 세는 탐지기」가 통과한다.

★**빈 입력을 초록으로 흘리지 마라** — 「스캔한 파일 수 ≥ N」을 함께 단언해라. 이 레포에서
「0건이니 통과」가 실제로는 「대상에 안 닿았다」였던 사고가 여러 번 있었다.

## Acceptance Criteria

```
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_ast_immutability_census.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/pine_v2/test_ast_immutability_census.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
cd apps/api && uv run ruff check tests/strategy/pine_v2
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 ⑴ 스캔한 파일 수 ⑵ 「AST 파생 이름」 판별 규칙 한 줄 ⑶ 양성 대조가 잡은 패턴 수
   ⑷ ★**탐지기가 못 잡는 것으로 알려진 사각**(별칭·동적 접근·모듈 alias 등)을 적어라.
   사각을 적는 것은 실패가 아니라 이 회차의 산출이다.
3. 규약: `apps/api/AGENTS.md`.
4. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 후 즉시 중단.

## 금지사항

- **위반이 실제로 발견되면 `src/` 를 고쳐서 없애지 마라.** 이유: 착수 전 census 는 0건을 봤다.
  0건이 아니라면 **내 census 와 그 census 중 하나가 틀린 것**이고, 어느 쪽인지 모른 채 제품 코드를
  고치면 원인을 잃는다. `status:"blocked"` + 좌표를 `blocked_reason` 에 적고 멈춰라.
- **탐지 규칙을 넓혀서 통과시키지 마라.** 이유: 음성 대조가 그것을 잡으라고 있는 것이다.
- 시간(초)을 단언하지 마라.
- 커밋하지 마라(커밋은 러너 소관).
