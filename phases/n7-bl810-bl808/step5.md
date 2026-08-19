# Step 5: bl808-check-expression-snapshot

CHECK 축은 **이름 집합만** 보므로 이름을 유지한 채 **표현식만 약화**시키면 초록으로 지나간다.
축 전체를 넓히지 말고(그건 [BL-803] 의 의도된 설계다), **위험한 CHECK 3개에 한해** 표현식
스냅샷 테스트를 따로 둔다. 근거 = [BL-808] ⑶.

## 읽어야 할 파일

- `apps/api/AGENTS.md`
- `apps/api/tests/test_migrations.py` — 특히
  - `_check_constraint_drifts_for_table` (506~531) 의 docstring(왜 식을 비교하지 않는지)
  - `_upgrade_and_inspect` (1087~1093) — `alembic upgrade head` 후 (engine, inspector) 반환
  - **본보기** `test_deactivation_reason_check_matches_the_enum` (1177~1219) — 이미 이 모양이다
- `apps/api/src/trading/models.py` — `CheckConstraint` 3곳 (372 · 491 · 737)

## 문제 (실측 근거)

`ck_kill_switch_events_trigger_scope` 는 이름을 유지한 채 `exchange_account_id IS NULL` 절만
지워도 이름 집합 축은 **초록**이고, DB 는 **strategy 와 exchange account 가 동시에 지정된 잘못된
kill-switch scope** 를 허용하게 된다. 나머지 둘도 같은 모양의 배타 조건을 담는다.

레포의 `CheckConstraint` 는 정확히 이 셋뿐이다 (전부 `trading` schema):

| constraint                                   | table                  | 무엇을 지키나                                 |
| -------------------------------------------- | ---------------------- | --------------------------------------------- |
| `ck_kill_switch_events_trigger_scope`        | `kill_switch_events`   | trigger_type ↔ strategy/exchange account 배타 |
| `ck_live_signal_sessions_deactivated_reason` | `live_signal_sessions` | 종료 사유 값 집합                             |
| `ck_alert_rules_type_threshold`              | `alert_rules`          | rule_type ↔ threshold_percent 배타            |

## 작업

### ⑴ 실제 표현식을 먼저 조회해라 (추측 금지)

PostgreSQL 은 enum cast 를 붙이고 `IN (...)` 을 `= ANY (ARRAY[...])` 로 **재작성**한다.
그러므로 스냅샷 값은 **모델 소스가 아니라 DB 가 실제로 돌려주는 문자열**이어야 한다.
먼저 아래로 실측하고, 그 결과를 스냅샷에 그대로 박아라:

```sql
SELECT c.conname, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'trading'
  AND c.conname IN (
    'ck_kill_switch_events_trigger_scope',
    'ck_live_signal_sessions_deactivated_reason',
    'ck_alert_rules_type_threshold'
  );
```

실행 방법은 자유다(테스트를 한 번 실패시켜 실제 값을 출력해 읽어도 된다). 단
`alembic upgrade head` 를 거친 DB 여야 한다 — conftest 의 `create_all` DB 가 아니다.

### ⑵ 스냅샷 테스트 추가 (이름 고정)

아래 이름으로 정확히 추가한다 — 러너 AC 가 `-k check_constraint_expression` 으로 집행한다.

```python
# ★[BL-808] ⑶ — CHECK 이름 집합 축(`_check_constraint_drifts_for_table`)은 표현식을 보지 않는다.
#   그 설계는 유지하되(PG 재작성 흡수 불가), **배타 조건을 담은 위험 CHECK 3개에 한해**
#   표현식을 동결한다. 이름을 유지한 채 `exchange_account_id IS NULL` 절만 지우는 변경이
#   이름 축에서는 초록이고 DB 는 잘못된 scope 를 허용하게 되는 것이 이 테스트의 존재 이유다.
_RISKY_CHECK_CONSTRAINT_SNAPSHOTS: dict[tuple[str, str], str] = {
    ("kill_switch_events", "ck_kill_switch_events_trigger_scope"): "<실측값>",
    ("live_signal_sessions", "ck_live_signal_sessions_deactivated_reason"): "<실측값>",
    ("alert_rules", "ck_alert_rules_type_threshold"): "<실측값>",
}


def test_risky_check_constraint_expressions_match_the_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """배타 조건을 담은 CHECK 3개의 표현식이 동결값과 같은지 검증한다 (BL-808 ⑶)."""
```

구현 규칙:

- `_upgrade_and_inspect(monkeypatch)` 로 engine 을 얻고 `try/finally` 로 `engine.dispose()` 한다
  (본보기 `test_deactivation_reason_check_matches_the_enum` 와 같은 모양).
- **engine 은 한 번만 만든다** — 3개를 한 연결에서 조회해라. 제약마다 `upgrade head` 를 다시
  돌리지 마라(느리고 얻는 것이 없다).
- 비교 전 공백만 정규화한다: `" ".join(definition.split())`. **그 이상 정규화하지 마라** —
  캐스트·`= ANY (ARRAY[...])` 재작성까지 지우면 이 테스트가 지키려던 것이 사라진다.
- 제약이 아예 없으면(`None`) 「마이그레이션이 빠졌거나 이름이 바뀌었다」는 취지의 한국어
  assert 메시지로 실패시켜라.
- 불일치 메시지에는 **기대값과 실측값을 둘 다** 찍어라 — 의도한 변경이면 스냅샷을 갱신하면
  된다는 안내 한 줄을 포함해라.

### ⑶ 기존 값 집합 테스트는 그대로 둔다

`test_deactivation_reason_check_matches_the_enum` 은 **enum 과의 동기화**를 보고, 새 스냅샷은
**표현식 형태**를 본다. 겹치지만 잡는 것이 다르다. 지우거나 통합하지 마라.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/test_migrations.py -q
cd apps/api && uv run --env-file .env.local pytest tests/test_migrations.py -q -k check_constraint_expression
cd apps/api && uv run ruff check .
```

기준선 = step 4 종료 시점 **29 passed**. 이 step 뒤에는 30 이어야 한다.

## 금지사항

- **`_check_constraint_drifts_for_table` 의 이름 집합 비교를 표현식 비교로 바꾸지 마라.**
  이유: PG 가 `IN (...)` 을 `= ANY (ARRAY...)` 로 재작성하고 enum cast 를 붙여 상시 잡음이 되고,
  그러면 이 축 자체가 꺼진다 — 그 근거가 그 함수 docstring 에 이미 적혀 있다.
- **스냅샷 값을 모델 소스에서 손으로 옮겨 적지 마라.** 반드시 `pg_get_constraintdef()` 실측값을 써라.
- 위 3개 말고 다른 제약을 스냅샷에 추가하지 마라 — 「위험 CHECK 3개 한정」이 원장 처방이다.
- `src/trading/models.py` 의 `CheckConstraint` 를 수정하지 마라. 이 step 은 테스트만 더한다.
- step 3·4 의 변경을 되돌리지 마라. 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
