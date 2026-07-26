# ADR-005: DateTime tz-aware + AwareDateTime TypeDecorator 도입

> **상태:** 확정
> **일자:** 2026-04-16
> **작성자:** QuantBridge 팀
> **관련 PR:** [#6](https://github.com/woosung-dev/quantbridge/pull/6) (Sprint 5 Stage B M1, commits `d4eae0b` → `514ab84`)

---

## 컨텍스트

Sprint 4(Backtest API + Celery)까지 도메인 모델은 timestamp 필드를 다음 패턴으로 정의했다.

```python
def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # naive 강제

class Backtest(SQLModel, table=True):
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(), nullable=False),  # TIMESTAMP WITHOUT TIME ZONE
    )
```

이 우회는 Sprint 3 [S3-05] 이슈의 산물이었다 — `asyncpg`가 tz-aware `datetime`을 `TIMESTAMP WITHOUT TIME ZONE` 컬럼에 바인딩할 때 거부했고, 마이그레이션 회귀를 피하기 위해 **모델·코드 양쪽에서 naive로 통일**한 것이다.

Sprint 5에서 다음이 누적되며 더 미룰 수 없는 부담이 됐다.

1. **TimescaleDB hypertable 도입 임박 (M2)** — `ts.ohlcv`의 `time` 컬럼은 hypertable partition key로 `TIMESTAMPTZ`가 사실상 표준. naive 정책과 충돌.
2. **JSON 직렬화 drift** — `serializers.py`에서 naive datetime을 ISO 8601 + `Z` suffix로 직렬화하면서 client가 받는 값은 UTC인데 server의 datetime 비교는 naive로 진행. 잠복 버그 다수 (`_parse_utc_iso` 함수가 naive를 반환하던 것이 실제 production 버그로 식별됨, M1 Task 8에서 catch).
3. **TIMESTAMPTZ 정책 비일관성** — Pydantic 스키마(`period_start`/`period_end`)는 이미 tz-aware를 요구하면서 ORM은 naive로 저장 → "스키마는 받지만 DB는 잘라낸다" 구조.
4. **drift 감지 불가** — 모델이 1줄만 잘못 적혀도 마이그레이션과 metadata가 어긋나면 발견 시점이 incident 발생 후로 밀린다 (M1 Task 9에서 catch — `period_start`/`period_end` 마이그레이션 누락 사례).

문제는 **단순히 `DateTime(timezone=True)`로 컬럼만 바꾸는 것**으로 해결되지 않는다. 코드에서 `_utcnow()`를 무심코 다시 호출하거나 `datetime.now()`(UTC 미명시)을 쓰는 순간 drift가 재발한다. **ORM 레이어에서 naive를 거부하는 가드가 필요**했다.

## 결정

다섯 층에서 동시에 강제한다.

### 1. ORM 레이어 가드 — `AwareDateTime` TypeDecorator (신규)

`backend/src/common/datetime_types.py`에 SQLAlchemy `TypeDecorator` 신규 작성. naive datetime이 들어오면 즉시 `ValueError`로 차단.

```python
class AwareDateTime(TypeDecorator[datetime]):
    """tz-aware datetime만 허용. naive 입력 시 즉시 ValueError."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        if value.tzinfo is None:
            raise ValueError(
                f"Naive datetime rejected: {value}. "
                "Use datetime.now(UTC) or attach tzinfo."
            )
        return value
```

모든 ORM 모델의 `Column(DateTime(timezone=True))`을 `Column(AwareDateTime())`으로 교체.

### 2. 도메인 모델 — `_utcnow()` 함수 제거

3개 도메인 모듈(`auth/models.py`, `strategy/models.py`, `backtest/models.py`)의 `_utcnow()` 헬퍼를 모두 삭제하고 `default_factory=lambda: datetime.now(UTC)`로 일원화.

### 3. Pydantic 스키마 — `AwareDatetime` 사용 강제

`pydantic.AwareDatetime`(Pydantic V2 내장)을 사용하여 입력 측에서도 tz-aware를 강제. `Backtest.period_start`/`period_end`는 client로부터 tz-aware를 명시적으로 요구.

### 4. 마이그레이션 — TIMESTAMP → TIMESTAMPTZ 일괄 변환

`backend/alembic/versions/20260416_1343_convert_datetime_to_timestamptz.py`로 11개 컬럼을 한 번에 변환.

| 테이블 | 컬럼 |
|--------|------|
| `users` | `created_at`, `updated_at` |
| `strategies` | `created_at`, `updated_at` |
| `backtests` | `created_at`, `started_at`, `completed_at`, **`period_start`**, **`period_end`** |
| `backtest_trades` | `entry_time`, `exit_time` |

```sql
ALTER TABLE backtests ALTER COLUMN created_at TYPE TIMESTAMPTZ
    USING created_at AT TIME ZONE 'UTC';
```

(`period_start`/`period_end`는 코드 리뷰어가 누락을 catch한 사례 — drift 위험을 실증한 결정의 한 부분.)

**주의:** `ALTER COLUMN TYPE` 변환은 `ACCESS EXCLUSIVE` lock을 사용. 현재 테이블 크기는 무시 가능하나, 향후 대용량 hypertable에 동일 패턴 적용 금지 (`pg_repack` 등 별도 전략 필요).

### 5. drift 감지 회귀 — Metadata vs Migration diff 테스트

`backend/tests/test_migrations.py`에 SQLModel.metadata와 alembic upgrade 후 실제 DB schema를 column-by-column으로 diff하는 회귀 테스트 추가. 모델 1줄 오타로도 CI에서 즉시 fail.

## 거부한 대안

| 대안 | 거부 이유 |
|------|----------|
| **naive 유지 + 직렬화 시점에서 변환** | drift 검출 수단이 없음. `_parse_utc_iso`처럼 production에서 silent하게 깨지는 패턴이 누적된다. M1 Task 8이 실제 사례. |
| **컬럼만 TIMESTAMPTZ로 변경 (ORM 가드 없음)** | 누군가 `_utcnow()`를 다시 만들거나 `datetime.now()`를 쓰는 순간 회귀. Sprint 4에 한 번 우회한 전례가 있어 동일 사고 재발 가능성 높음. |
| **datetime → date 분리 (시간 정보 제거)** | OHLCV/거래 시점은 millisecond 정밀도가 필수. 시간 정보 손실은 비현실적. |
| **`datetime` 대신 `pendulum` 등 외부 라이브러리** | 의존성 + 학습 곡선. 표준 라이브러리 + Pydantic V2 `AwareDatetime`만으로 충분. |
| **DB 트리거로 강제** | DB 레이어 강제는 ORM 우회 시 무력. 가드는 가장 가까운 레이어에 둬야 한다. |

## 결과

- **380 tests pass / ruff clean / mypy clean / CI green** (M1 PR #6)
- **schema drift 0건** — metadata diff 회귀로 마이그레이션 누락 자동 감지
- **production 버그 1건 사전 차단** — `_parse_utc_iso`의 naive 반환이 EquityPoint validation을 깨뜨리던 것을 회귀 테스트가 catch
- **마이그레이션 누락 1건 catch** — `period_start`/`period_end` 변환 누락을 reviewer가 발견 (commit `74af5b8`)

## 영향 (Sprint 5+ 영구 규칙)

다음을 코딩 컨벤션 수준의 강제 사항으로 격상한다.

1. **모든 신규 SQLModel timestamp 필드는 `Column(AwareDateTime())` 사용 강제.** `Column(DateTime())`/`Column(DateTime(timezone=True))` 직접 사용 금지.
2. **Pydantic 스키마의 timestamp는 `AwareDatetime` 사용 강제.** `datetime` 타입 직접 사용 금지(검증 우회).
3. **코드에서 `datetime.now()`/`datetime.utcnow()` 직접 사용 금지** — 항상 `datetime.now(UTC)`. (Python 3.12 `utcnow()` deprecated와 정합)
4. **신규 마이그레이션은 항상 `TIMESTAMPTZ` 사용.** `TIMESTAMP WITHOUT TIME ZONE` 도입 금지. M2 `ts.ohlcv` hypertable의 `time` 컬럼이 첫 적용 사례.
5. **Celery task가 datetime 인자를 받으면 반드시 ISO 8601 직렬화하여 전달.** datetime 객체 직접 전달 금지(브로커 직렬화 시 tz 정보 누락 가능).

## 의사결정 트레일

- M1 spec: [`docs/superpowers/specs/2026-04-16-sprint5-stage-b-design.md`](../superpowers/specs/2026-04-16-sprint5-stage-b-design.md) §M1
- M1 plan: [`docs/superpowers/plans/2026-04-16-sprint5-stage-b.md`](../superpowers/plans/2026-04-16-sprint5-stage-b.md) §Task 2~9
- 외부 검토: Opus M1/M3 검토 12개 보강안 반영 (drift 감지 강화, ORM 가드 추가가 핵심 권고)
- 사전 이력: Sprint 3 [S3-05] `_utcnow()` 우회 결정 (`docs/TODO.md` "Sprint 5+ 이관" 참조)
