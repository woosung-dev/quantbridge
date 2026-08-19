# Step 4: bl808-per-axis-skip

스키마 동등성 검사의 **정지 규칙이 cascading `return`** 이라, 앞 축의 baseline 이 커지면 뒤 축들이
**조용히** 꺼지고 **이미 수집해 둔 증거까지 버려진다**. 축별 지역 skip 으로 바꾸고 skip 을
출력에 찍는다. 근거 = [BL-808] ⑵ (원장 권장 접근 채택 — 의미론은 이미 정해졌다, 재논의하지 마라).

## 읽어야 할 파일

- `apps/api/AGENTS.md`
- `apps/api/tests/test_migrations.py` — 특히
  - baseline 4종 선언: `_NULLABLE_DRIFT_BASELINE`(67) · `_DEFAULT_DRIFT_BASELINE`(86) ·
    `_INDEX_DRIFT_BASELINE`(92) · `_CHECK_CONSTRAINT_DRIFT_BASELINE`(97)
  - `test_alembic_schema_matches_sqlmodel_metadata` (884~1085) — 특히 1006~1085 의 정지 규칙 4개

## 문제 (실측 근거)

현재 구조는 축 사이에 이런 것이 4번 끼어 있다:

```python
_assert_no_new_nullable_drifts(observed_nullable_drifts)

# nullable 축이 기존 drift를 5건 넘겨 동결됐다면, 정지 규칙상 이 회차는 여기서 끝낸다.
if len(_NULLABLE_DRIFT_BASELINE) > 5:
    return
```

⇒ nullable baseline 이 6건이 되는 순간 index · CHECK · default 축이 **한 줄의 출력도 없이**
통째로 꺼진다. `observed_default_drifts` 는 첫 루프에서 **이미 수집됐는데 단언 없이 버려진다.**
2026-08-18 [BL-803] 회차에 이 fail-open 이 실제로 발화한 적이 있다 —
`ck_alert_rules_type_threshold` 이름을 바꾸는 변이가 **27 passed 로 통과**했다.

## 작업

### ⑴ 축별 지역 skip 헬퍼

모듈 수준에 추가한다:

```python
_AXIS_BASELINE_LIMIT = 5


def _axis_is_enabled(axis: str, baseline: frozenset[Any], skipped: list[str]) -> bool:
    """축의 baseline 이 한도를 넘으면 그 축만 끄고 이름을 `skipped` 에 남긴다.

    정지 규칙의 의미는 「이 축이 시끄러우면 **이 축을** 이 회차에 얹지 마라」이지
    「뒤 축을 전부 끄고 이미 모은 증거를 버려라」가 아니다 ([BL-808] ⑵, 2026-08-19).
    """
    if len(baseline) > _AXIS_BASELINE_LIMIT:
        skipped.append(axis)
        return False
    return True
```

### ⑵ `test_alembic_schema_matches_sqlmodel_metadata` 재배선

- 함수 안에 `skipped_axes: list[str] = []` 를 둔다.
- **cascading `return` 4개를 전부 지운다.**
- 각 축의 단언을 `if _axis_is_enabled("<축 이름>", <BASELINE>, skipped_axes): <단언>` 로 감싼다.
  축 이름은 `"type"` · `"nullable"` · `"index"` · `"check_constraint"` · `"default"` 를 쓴다.
  ★`type` 축에는 지금 정지 규칙이 없다 — 있는 4축(nullable · index · check_constraint · default)만
  감싸고, `type` 축은 지금처럼 무조건 단언한다. 있지도 않은 규칙을 새로 만들지 마라.
- 각 축의 **수집(로 루프)은 skip 여부와 무관하게 그대로 돌린다** — 증거를 버리지 않는 것이
  이 수리의 본체다. 끄는 것은 **단언뿐**이다.
- 축 실행 순서는 지금 그대로 둔다 (type → nullable → index → CHECK → default). 순서에 의존하는
  fail-open 이 사라지므로 순서를 설명하던 긴 주석(1012~1020 · 1074~1082)은 **새 사실에 맞게**
  고쳐 써라 — 지우지 말고, 「왜 순서가 중요했고 지금은 왜 아닌가」를 남겨라.

### ⑶ skip 을 **출력에 찍는다**

함수 마지막에:

```python
if skipped_axes:
    warnings.warn(
        f"스키마 동등성 축 {sorted(skipped_axes)} 이(가) baseline "
        f">{_AXIS_BASELINE_LIMIT} 로 이 회차에서 꺼졌다 — 조용한 skip 을 막기 위한 경고다.",
        UserWarning,
        stacklevel=2,
    )
```

`import warnings` 를 파일 상단 표준 라이브러리 import 블록에 더한다(이미 있으면 그대로).
★조용한 skip 이 이 결함의 본체이므로 **경고 없이 끄는 경로가 남으면 안 된다.**

### ⑷ 헬퍼 회귀 단위 테스트 (이름 고정)

아래 이름으로 정확히 추가한다 — 러너 AC 가 `-k axis_skip` 으로 집행한다:

```python
def test_axis_skip_records_a_noisy_baseline_without_disabling_other_axes() -> None:
    """한 축의 baseline 이 한도를 넘어도 그 축만 꺼지고 이름이 남는다 (BL-808 ⑵)."""
    skipped: list[str] = []
    noisy = frozenset((f"drift-{i}",) for i in range(_AXIS_BASELINE_LIMIT + 1))
    quiet = frozenset()
    assert _axis_is_enabled("noisy", noisy, skipped) is False
    assert _axis_is_enabled("quiet", quiet, skipped) is True
    assert skipped == ["noisy"]
```

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/test_migrations.py -q
cd apps/api && uv run --env-file .env.local pytest tests/test_migrations.py -q -k axis_skip
cd apps/api && uv run ruff check .
```

기준선 = step 3 종료 시점 **28 passed**. 이 step 뒤에는 29 여야 한다.

## 금지사항

- **`_AXIS_BASELINE_LIMIT` 을 5 말고 다른 값으로 바꾸지 마라.** 이유: 지금 4축의 baseline 은 전부
  0건이고, 한도를 바꾸면 이 수리가 무엇을 고쳤는지 실측으로 갈라낼 수 없다.
- **baseline 4종에 항목을 추가하지 마라.** 전부 빈 frozenset 인 것이 이 축들의 판별력이다.
- **단언을 지우거나 축을 삭제하지 마라.** 이 step 은 「끄는 방식」만 바꾼다.
- `_normalize_server_default` 를 건드리지 마라 — step 3 이 이미 고쳤다. 되돌리지 마라.
- CHECK 표현식 스냅샷은 step 5 소관이다. 여기서 만들지 마라.
- 소스(`src/`)를 수정하지 마라. 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
