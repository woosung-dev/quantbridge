# BL-388 tripwire — BacktestMetrics 4-site 평행 정의(dataclass/schema/serializer/_to_detail) drift 자동 검출
"""메트릭 필드 추가 시 4곳 동시 수정을 구조적으로 강제하는 가드.

- ① field-set parity: engine dataclass ↔ API 스키마 필드 집합 일치
- ② 완전-채움 round-trip identity: 전 필드 non-None 합성 → to_jsonb → from_jsonb == 원본
  (serializer 어느 방향이든 신규 필드 누락 시 즉시 FAIL — 수동 24-field 테스트가 못 잡는 갭)
- ③ _to_detail passthrough: 완전-채움 JSONB → BacktestDetail.metrics 전 필드 값 일치
- negative-control: tripwire ② 가 키 누락을 실제로 검출하는지 자기 검증 (mutation guard)
"""
from __future__ import annotations

import dataclasses
import types
import typing
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

from pydantic import BaseModel

from src.backtest.engine.types import (
    BacktestMetrics,
    ExcursionStats,
    PerSideMetrics,
    SideMetrics,
)
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.schemas import (
    BacktestMetricsOut,
    BacktestMetricsSummary,
    ExcursionStatsOut,
    PerSideMetricsOut,
    SideMetricsOut,
)
from src.backtest.serializers import metrics_from_jsonb, metrics_to_jsonb
from src.backtest.service import BacktestService

# nested dataclass ↔ Pydantic sub-model parity 쌍 (tripwire ① 확장 대상).
_NESTED_PAIRS: tuple[tuple[type, type], ...] = (
    (SideMetrics, SideMetricsOut),
    (PerSideMetrics, PerSideMetricsOut),
    (ExcursionStats, ExcursionStatsOut),
)


def _strip_optional(tp: Any) -> Any:
    """`X | None` → X. Optional 아니면 그대로."""
    if typing.get_origin(tp) in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _synthetic_value(tp: Any, i: int) -> Any:
    """필드 타입별 합성 값 — 필드마다 i 로 값을 달리해 key-swap drift 도 검출."""
    base = _strip_optional(tp)
    if base is Decimal:
        return Decimal(f"{i}.25")
    if base is bool:  # bool 은 int 보다 먼저 (bool ⊂ int)
        return True
    if base is int:
        return 100 + i
    if base is str:
        return f"synthetic-{i}"
    if typing.get_origin(base) is list:  # list[tuple[str, Decimal]] 계열
        return [(f"2024-01-0{(i % 9) + 1}T00:00:00Z", Decimal(f"{i}.5"))]
    if dataclasses.is_dataclass(base) and isinstance(base, type):
        # nested dataclass — 재귀 완전-채움 (per_side/excursion_stats).
        hints = typing.get_type_hints(base)
        return base(**{
            f.name: _synthetic_value(hints[f.name], i * 31 + j)
            for j, f in enumerate(dataclasses.fields(base))
        })
    raise AssertionError(
        f"tripwire 합성기 미지원 타입 {tp!r} — 신규 필드 타입이면 본 함수에 분기 추가"
    )


def _full_metrics() -> BacktestMetrics:
    """전 필드 non-None 합성 BacktestMetrics."""
    hints = typing.get_type_hints(BacktestMetrics)
    values = {
        f.name: _synthetic_value(hints[f.name], i)
        for i, f in enumerate(dataclasses.fields(BacktestMetrics))
    }
    return BacktestMetrics(**values)


def test_dataclass_and_schema_field_sets_match() -> None:
    """tripwire ①: engine dataclass ↔ BacktestMetricsOut 필드 집합 parity."""
    dataclass_fields = {f.name for f in dataclasses.fields(BacktestMetrics)}
    schema_fields = set(BacktestMetricsOut.model_fields)
    assert dataclass_fields == schema_fields, (
        f"BL-388 drift: dataclass-only={dataclass_fields - schema_fields}, "
        f"schema-only={schema_fields - dataclass_fields} — 4-site 동시 수정 필요"
    )


# BacktestMetricsSummary 는 목록·대시보드 응답에 실리지만 tripwire ①의 사각지대다.
# 수기 키가 dataclass 에 없으면 JSONB 에 없어 metrics_summary_from_jsonb 가 항상 None 을 돌린다.
def test_summary_keys_subset_of_dataclass() -> None:
    """목록·대시보드용 summary 키가 engine dataclass 에만 의존하는지 검증."""
    dataclass_fields = {f.name for f in dataclasses.fields(BacktestMetrics)}
    summary_fields = set(BacktestMetricsSummary.model_fields)
    assert summary_fields <= dataclass_fields, (
        "BL-388 summary drift: dataclass 에 없는 summary keys="
        f"{summary_fields - dataclass_fields}"
    )


def test_nested_dataclass_and_schema_field_sets_match() -> None:
    """tripwire ① 확장: nested 팩(dataclass ↔ Pydantic sub-model) parity."""
    for dc, model in _NESTED_PAIRS:
        dc_fields = {f.name for f in dataclasses.fields(dc)}
        model_fields = set(model.model_fields)
        assert dc_fields == model_fields, (
            f"BL-388 nested drift ({dc.__name__} ↔ {model.__name__}): "
            f"dataclass-only={dc_fields - model_fields}, "
            f"schema-only={model_fields - dc_fields}"
        )


# Decimal serializer 누락은 JSON float 변환으로 금융 수치의 정밀도를 조용히 잃게 만든다.
def test_all_decimal_fields_have_field_serializer() -> None:
    """최상위·nested API 모델의 Decimal 필드가 모두 문자열 serializer 를 갖는지 검증."""
    for model in (BacktestMetricsOut, SideMetricsOut, ExcursionStatsOut):
        decimal_fields = {
            name
            for name, annotation in typing.get_type_hints(model).items()
            if annotation is Decimal or Decimal in typing.get_args(annotation)
        }
        serializer_fields = {
            field
            for decorator in model.__pydantic_decorators__.field_serializers.values()
            for field in decorator.info.fields
        }
        assert decimal_fields <= serializer_fields, (
            f"BL-388 Decimal serializer drift ({model.__name__}): "
            f"missing={decimal_fields - serializer_fields}"
        )


def test_full_metrics_generator_fills_every_field() -> None:
    """합성기 자기 검증: 모든 필드가 non-None (생략 필드 = tripwire ② 무력화)."""
    m = _full_metrics()
    for f in dataclasses.fields(BacktestMetrics):
        assert getattr(m, f.name) is not None, f"합성기가 {f.name} 을 채우지 못함"


def test_serializer_round_trip_identity_full_fill() -> None:
    """tripwire ②: 완전-채움 round-trip identity — serializer 방향 무관 누락 검출."""
    m = _full_metrics()
    restored = metrics_from_jsonb(metrics_to_jsonb(m))
    for f in dataclasses.fields(BacktestMetrics):
        assert getattr(restored, f.name) == getattr(m, f.name), (
            f"BL-388 drift: {f.name} round-trip 불일치 — "
            f"metrics_to_jsonb/metrics_from_jsonb 중 한쪽에 필드 누락 의심"
        )


def test_round_trip_tripwire_detects_dropped_key() -> None:
    """negative-control: 키 1개 누락 시 tripwire ② 가 실제로 검출되는지 자기 검증."""
    m = _full_metrics()
    jsonb = metrics_to_jsonb(m)
    jsonb.pop("sortino_ratio")  # serializer 누락 시뮬레이션
    restored = metrics_from_jsonb(jsonb)
    assert restored != m, "키 누락에도 round-trip 이 동일 — tripwire 무력 (합성기 결함)"


def _dbless_service() -> BacktestService:
    """_to_detail 은 순수 변환 — 의존성 미사용이라 None 주입."""
    return BacktestService(
        repo=cast(Any, None),
        strategy_repo=cast(Any, None),
        ohlcv_provider=cast(Any, None),
        dispatcher=cast(Any, None),
    )


def test_to_detail_passes_through_every_metric_field() -> None:
    """tripwire ③: 완전-채움 JSONB → BacktestDetail.metrics 전 필드 passthrough.

    direction_counts=None → override 없이 JSONB 값 그대로 (레거시 fallback 경로).
    """
    m = _full_metrics()
    bt = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        metrics=metrics_to_jsonb(m),
        equity_curve=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    detail = _dbless_service()._to_detail(bt)
    assert detail.metrics is not None
    for name in BacktestMetricsOut.model_fields:
        got = _plain(getattr(detail.metrics, name))
        expected = _plain(getattr(m, name))
        assert got == expected, (
            f"BL-388 drift: _to_detail 이 {name} 을 전달하지 않음 "
            f"(got={got!r}, expected={expected!r})"
        )


def _plain(v: Any) -> Any:
    """Pydantic sub-model / nested dataclass → plain dict + Decimal → str 재귀 정규화.

    model_dump 는 field_serializer(Decimal→str)를 적용하므로 양쪽 모두 str 로 통일.
    """
    if isinstance(v, BaseModel):
        v = v.model_dump(mode="python")
    elif dataclasses.is_dataclass(v) and not isinstance(v, type):
        v = dataclasses.asdict(v)
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, Decimal):
        return str(v)
    return v
