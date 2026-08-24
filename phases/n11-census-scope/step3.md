# Step 3: metric 가드의 기록된 사각 — 별칭·모듈 alias·동적 접근

## 읽어야 할 파일

- `apps/api/tests/common/test_metric_guard_census.py` — `_metric_name()`(140행 근처) ·
  `_mutation_site()` · `_guarded_node_ids()`
- `apps/api/tests/trading/test_no_strenum_value_access.py` 의 헤더 주석(23행) — **같은 사각을
  같은 문장으로 적어 둔 선례다.** 읽되 그 파일을 **수정하지 마라**(다른 lane 소유)

## 배경

n7 이 lane→CONTROL 인계로 남긴 기록: **BE metric AST 가드는 별칭·동적 접근·모듈 alias 를 못 잡는다.**
`_metric_name()` 은 `ast.Name` 의 `id` 가 `qb_` 로 시작하는 경우와 `.labels(...)` 호출만 본다.
따라서 아래는 전부 스캐너에 **안 보인다**:

```python
c = qb_live_signal_skipped_total          # 별칭
c.labels(reason="x").inc()

from src.common import metrics as m       # 모듈 alias
m.qb_live_signal_skipped_total.inc()

getattr(module, "qb_live_signal_skipped_total").inc()   # 동적 접근
```

★**이 step 은 「사각을 닫는다」가 아니라 「사각을 기계로 고정한다」가 목표다.** 세 형태 전부를
완전 해석하는 것은 정적 분석의 끝이 없는 구간이다(2026-08-17 에 같은 판단으로 범위를 좁힌 선례가 있다).
**지금 `src` 에 그 형태가 0건임을 단언하고, 생기면 red 가 되게 한다** — 그것이 값의 대부분이다.

## 작업

`apps/api/tests/common/test_metric_alias_access.py` 를 신설한다.
**테스트 이름에 `metric_alias` 를 포함시켜라** — AC 가 `-k metric_alias` 로 잡는다.

### 규칙 — `apps/api/src` 전량에서 아래를 위반으로 센다

1. **별칭 대입** — `<name> = <qb_로 시작하는 Name>` 형태의 대입(모듈·함수 스코프 모두)
2. **모듈 alias 경유** — `<name>.<qb_로 시작하는 attr>` 형태의 `ast.Attribute` 접근
3. **동적 접근** — `getattr(<any>, "<qb_ 로 시작하는 문자열 리터럴>")`

### 동결과 대조

`_FROZEN_ALIAS_ACCESS: dict[str, int] = {...}`(경로→건수)로 **정확 동등** 비교한다.
**수치는 네가 직접 측정해서 넣어라 — 이 문서에 적힌 형태를 정답으로 옮기지 마라.**
빈 집합이 나오면 그대로 `{}` 로 동결한다. ★단, **빈 동결에 「아직 남아 있다」쪽 대칭 검사를
두지 마라** — `actual >= frozenset()` 은 항상 참이라 판별력 0 이면서 통과 수만 늘린다
(`tests/common/test_repository_boundary_guard.py:128` 주석이 같은 것을 경고한다).

### 테스트 3건

1. `test_metric_alias_access_matches_the_frozen_map` — 실측 == 동결
2. `test_metric_alias_scanner_detects_synthetic_violations` — ★**양성 대조.**
   `ast.parse` 로 만든 **합성 소스 문자열**에서 세 형태 각각이 검출되는지 단언한다
   (실파일을 건드리지 않는다). 세 형태 = 3건 이상 검출
3. `test_metric_alias_scanner_ignores_non_metric_names` — ★**음성 대조.**
   `qb_` 로 시작하지 않는 이름의 별칭·attribute·`getattr` 은 잡히지 **않는다**

★**2 와 3 이 둘 다 있어야 한다.** 2 만 있으면 「전부 잡는」 검사기가 통과하고,
3 만 있으면 「아무것도 안 잡는」 검사기가 통과한다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -k metric_alias -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/common -k metric_alias --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common -q
cd apps/api && uv run ruff check tests/common
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **실파일 판별력을 1회 재라** — `src` 어딘가에 별칭 형태를 임시로 심고 red 를 확인한 뒤
   **반드시 원복**해라(`git diff --stat`). 합성 픽스처만으로는 스캔 경로가 실파일에 닿는지 모른다
   (이 레포는 「합성은 통과, 실파일은 미도달」을 실제로 겪었다).
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **세 형태를 완전 해석하려 들지 마라**(별칭의 재대입 추적·조건부 분기 해석 등).
  이유: 끝이 없는 구간이고, 그 모델링 자신이 결함을 만든 선례가 있다. **부재 단언 + 대조 2종**이 이 step 의 범위다.
- **빈 동결에 대칭 검사를 두지 마라.** 이유: 항진명제라 판별력 0 인데 통과 수만 늘린다.
- **`tests/trading/test_no_strenum_value_access.py` 를 수정하지 마라.** 이유: 다른 lane 의 소유 파일이다.
- **`src` 를 고치지 마라**(임시 변이는 원복). 이유: 이 step 의 산출은 검사기다.
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
