# Step 3: bl808-normalize-quoted-literal

`_normalize_server_default` 가 **따옴표 리터럴 안까지** 캐스트를 지우고 casefold 해서
**서로 다른 DEFAULT 를 같다고 판정**하는 잠재 결함을 고친다. 근거 = [BL-808] ⑴.

## 읽어야 할 파일

- `apps/api/AGENTS.md` (3-Layer · Decimal-first · 도메인 규칙)
- `apps/api/tests/test_migrations.py` — 특히
  - `_strip_postgresql_type_casts` (197~209)
  - `_normalize_server_default` (212~231)
  - `_default_drifts_for_table` (234~264)
  - 기존 단위 3건: `test_server_default_normalization_absorbs_postgres_render_artifacts`(280) ·
    `test_server_default_normalization_still_separates_different_values`(286) ·
    `test_empty_default_drift_baseline_rejects_a_server_default_mutation`(291)

## 문제 (실측 근거)

현재 구현은 문자열 **전체**에 casefold 와 `::<식별자>` 제거를 적용한다:

```python
normalized = _strip_postgresql_type_casts(str(default_arg).strip().casefold()).strip()
```

그래서 두 짝이 같다고 판정된다 — 둘 다 실제로는 **다른 DEFAULT** 다:

| 모델 쪽                                                 | DB 쪽             | 현재 정규화 결과      | 옳은 판정       |
| ------------------------------------------------------- | ----------------- | --------------------- | --------------- |
| `'literal::jsonb'` (따옴표 **안**에 캐스트 모양 문자열) | `'literal'`       | 둘 다 `literal`       | **달라야 한다** |
| `'CaseSensitive'`                                       | `'casesensitive'` | 둘 다 `casesensitive` | **달라야 한다** |

★현재 실측 35컬럼에 그런 값은 없다 — **잠재** 결함이고, 이 step 은 그것을 닫는다.

## 작업

### ⑴ 따옴표 리터럴을 먼저 분리한다

`test_migrations.py` 에 헬퍼를 하나 추가한다 (모듈 상수 정규식 + 함수):

```python
_SQL_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")


def _split_sql_string_literals(value: str) -> list[tuple[bool, str]]:
    """SQL 문자열 리터럴과 그 바깥을 등장 순서대로 (is_literal, 조각) 로 나눈다.

    PostgreSQL 의 리터럴 안 작은따옴표 이스케이프(`''`)를 리터럴의 일부로 본다.
    """
```

그리고 `_normalize_server_default` 를 다음 의미론으로 바꾼다:

1. `str(default_arg).strip()` 로 원문을 얻는다. **여기서 casefold 하지 않는다.**
2. `_split_sql_string_literals` 로 조각을 낸다.
3. **바깥 조각에만** `casefold()` + `_strip_postgresql_type_casts()` 를 적용한다.
4. **리터럴 조각은 원문 그대로** 둔다 (대소문자·`::` 모양 보존).
5. 조각을 다시 이어 붙이고 `.strip()` 한다.
6. 이어 붙인 결과가 **정확히 리터럴 하나뿐**이면(= 바깥 조각이 전부 공백) 기존처럼 바깥
   따옴표를 벗겨 그 안을 반환한다. 그 외에는 이어 붙인 문자열을 반환한다.

`_strip_postgresql_type_casts` 자체는 **고치지 마라** — 그 함수는 이제 바깥 조각만 받으므로
정확해진다. 그 docstring 에 「호출자가 리터럴 바깥 조각만 넘긴다」는 한 줄을 더해라.

### ⑵ 회귀 단위 테스트 추가 (이름 고정)

아래 이름으로 정확히 추가한다 — 러너 AC 가 이 이름을 `-k` 로 집행한다:

```python
def test_server_default_normalization_preserves_quoted_literals() -> None:
    """따옴표 리터럴 안의 캐스트 모양과 대소문자는 서로 다른 DEFAULT 로 남는다 (BL-808 ⑴)."""
    assert _normalize_server_default("'literal::jsonb'") != _normalize_server_default("'literal'")
    assert _normalize_server_default("'CaseSensitive'") != _normalize_server_default(
        "'casesensitive'"
    )
    # 리터럴 **바깥** 캐스트는 여전히 흡수된다 — 이 축이 죽으면 안 된다.
    assert _normalize_server_default("'{}'::jsonb") == _normalize_server_default("'{}'")
    assert _normalize_server_default(text("NOW()")) == _normalize_server_default("now()")
```

### ⑶ 기존 3건이 계속 통과해야 한다

특히 `_normalize_server_default(text("NOW()")) == _normalize_server_default("now()")` 와
`_normalize_server_default("[]") == _normalize_server_default("'[]'::jsonb")` 는 **바깥/리터럴이
섞인 경우**라 이 수리의 핵심 회귀다. 그리고 `test_alembic_schema_matches_sqlmodel_metadata` 의
실 35컬럼 대조(`_DEFAULT_DRIFT_BASELINE` 가 빈 frozenset)가 여전히 green 이어야 한다 —
여기서 red 가 나면 정규화가 **과소** 쪽으로 넘어간 것이다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/test_migrations.py -q
cd apps/api && uv run --env-file .env.local pytest tests/test_migrations.py -q -k preserves_quoted_literals
cd apps/api && uv run ruff check .
```

기준선 = 이 step 착수 전 **27 passed** (2026-08-19 실측). 이 step 뒤에는 28 이어야 한다.

## 금지사항

- **`_DEFAULT_DRIFT_BASELINE` 에 항목을 추가하지 마라.** 이유: 지금 빈 frozenset 인 것이 이 축의
  판별력 자체다. 실 35컬럼 대조가 red 가 되면 그것은 baseline 을 늘릴 사유가 아니라 이 step 의
  정규화가 틀렸다는 신호다.
- **정지 규칙(cascading `return`)을 건드리지 마라** — step 4 소관이다.
- **CHECK 축을 건드리지 마라** — step 5 소관이다.
- 소스(`src/`)를 수정하지 마라. 이 step 은 테스트 인프라 전용이다.
- 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
