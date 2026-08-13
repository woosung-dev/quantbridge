"""trust-layer baseline 필드 커버리지 — `regen_trust_layer_baseline` 산출이 좁으면 잡는다.

계약(CONTROL 동결) §3.3: `metrics_dict` 는 `BacktestMetrics` 스칼라 전량, `_trade_to_dict` 는
`RawTrade` 22 전량. **둘 다 `dataclasses.fields()` 자동 유도**여야 한다.

★이 시험도 필드명을 하드코딩하지 않는다 — `types.py` 에 필드가 하나 늘면 이 시험이 **자동으로
더 요구한다**. 하드코딩하면 "필드를 늘렸는데 시험은 그대로 green" 이 되어 커버리지가 조용히 썩는다.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from src.backtest.engine import types as engine_types
from src.backtest.engine.types import BacktestMetrics, RawTrade
from tests.strategy.pine_v2._corpus import SKIPPED_CORPUS

BACKEND_DIR = Path(__file__).resolve().parents[3]
BASELINE_PATH = BACKEND_DIR / "tests" / "fixtures" / "pine_corpus_v2" / "baseline_metrics.json"

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _field_kind(field: dataclasses.Field) -> str:
    """`scalar` | `list` | `nested` — 타입 주석에서 유도한다."""
    annotation = field.type if isinstance(field.type, str) else str(field.type)
    head = annotation.split("|")[0].strip()
    if head.startswith("list["):
        return "list"
    resolved = getattr(engine_types, head, None)
    if resolved is not None and dataclasses.is_dataclass(resolved):
        return "nested"
    return "scalar"


def _resolve_nested(field: dataclasses.Field) -> type:
    annotation = field.type if isinstance(field.type, str) else str(field.type)
    head = annotation.split("|")[0].strip()
    return getattr(engine_types, head)


def _names_by_kind(cls: type, kind: str) -> set[str]:
    return {f.name for f in dataclasses.fields(cls) if _field_kind(f) == kind}


def _flatten_nested_keys(prefix: str, cls: type) -> set[str]:
    """중첩 dataclass 를 `per_side.long.<f>` 꼴로 평탄화한다 (계약 §3.2)."""
    keys: set[str] = set()
    for field in dataclasses.fields(cls):
        if _field_kind(field) == "nested":
            keys |= _flatten_nested_keys(f"{prefix}.{field.name}", _resolve_nested(field))
        else:
            keys.add(f"{prefix}.{field.name}")
    return keys


def _expected_nested_keys() -> set[str]:
    keys: set[str] = set()
    for field in dataclasses.fields(BacktestMetrics):
        if _field_kind(field) == "nested":
            keys |= _flatten_nested_keys(field.name, _resolve_nested(field))
    return keys


def _digest(value: Any) -> str:
    """계약 §3.2 공식 그대로."""
    payload = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


NULL_DIGEST = _digest(None)
EMPTY_LIST_DIGEST = _digest([])


def _sample_value(field: dataclasses.Field) -> Any:
    """더미 인스턴스용 값 — **전부 non-None** 으로 채운다.

    None 을 넣으면 "None 인 키는 생략" 구현이 통과해버려 누락을 못 잡는다.
    """
    annotation = field.type if isinstance(field.type, str) else str(field.type)
    head = annotation.split("|")[0].strip()
    if head.startswith("Literal["):
        first = head[len("Literal[") : head.rindex("]")].split(",")[0].strip()
        return first.strip("'\"")
    if head == "int":
        return 7
    if head == "bool":
        return True
    if head == "str":
        return "sample"
    if head == "Decimal":
        return Decimal("1.5")
    resolved = getattr(engine_types, head, None)
    if resolved is not None and isinstance(resolved, type) and issubclass(resolved, Enum):
        # StrEnum 계열 (ExitOrderKind 등)
        return next(iter(resolved))
    raise AssertionError(
        f"{field.name}: 더미 값을 만들 수 없는 타입 {annotation!r} — "
        f"타입이 늘었으면 _sample_value 를 넓혀라"
    )


def _dummy(cls: type) -> Any:
    return cls(**{f.name: _sample_value(f) for f in dataclasses.fields(cls)})


@pytest.fixture(scope="module")
def baseline() -> dict[str, Any]:
    assert BASELINE_PATH.is_file(), f"baseline 이 없다: {BASELINE_PATH}"
    return json.loads(BASELINE_PATH.read_text())


def _corpora(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    corpora = baseline.get("corpora")
    assert isinstance(corpora, dict) and corpora, (
        f"baseline.corpora 가 비었다 (got {type(corpora).__name__}) — 잴 대상이 없다"
    )
    return corpora


def _is_skipped_entry(corpus_id: str, record: dict[str, Any]) -> bool:
    """실행되지 않은 코퍼스인가 — 제외 근거는 `SKIPPED_CORPUS` 다.

    ★「metrics 가 None 이면 그냥 넘긴다」로 쓰면 안 된다. 그러면 산출이 **전 코퍼스**를
    None 으로 만들어도 통과한다(항진명제화). `_corpus.py` 의 SSOT 와 대조해서, 실행 대상인데
    비어 있으면 **그 자리에서 실패**시킨다.
    """
    if record.get("metrics") is not None:
        return False
    assert corpus_id in SKIPPED_CORPUS, (
        f"{corpus_id}: metrics 가 비었는데 SKIPPED_CORPUS 에 없다 "
        f"(skip 정본 = {sorted(SKIPPED_CORPUS)}). 실행 대상 코퍼스가 산출을 못 남겼거나, "
        f"skip 목록이 _corpus.py 와 어긋난다"
    )
    return True


def test_metrics_dict_covers_all_scalar_backtest_metrics_fields(
    baseline: dict[str, Any],
) -> None:
    """산출 `metrics` 키 집합 ⊇ `BacktestMetrics` 스칼라 전량 + 중첩 2종 평탄화."""
    scalars = _names_by_kind(BacktestMetrics, "scalar")
    nested_keys = _expected_nested_keys()
    assert scalars, "BacktestMetrics 스칼라를 하나도 못 유도했다 — 분류 로직 결함"
    assert nested_keys, "중첩 dataclass 평탄화 키를 못 유도했다 — 분류 로직 결함"

    covered = 0
    for corpus_id, record in _corpora(baseline).items():
        if _is_skipped_entry(corpus_id, record):
            continue

        metrics = record.get("metrics")
        assert isinstance(metrics, dict), (
            f"{corpus_id}: metrics 가 dict 가 아니다 (got {type(metrics).__name__})"
        )
        covered += 1

        missing_scalars = scalars - set(metrics)
        assert not missing_scalars, (
            f"{corpus_id}: 스칼라 {len(missing_scalars)}/{len(scalars)}개 누락 — "
            f"{sorted(missing_scalars)}. metrics_dict 가 하드코딩 키 리스트를 쓰고 있으면 "
            f"types.py 에 필드가 늘어도 여기가 안 늘어난다"
        )

        missing_nested = nested_keys - set(metrics)
        assert not missing_nested, (
            f"{corpus_id}: 중첩 팩 평탄화 키 {len(missing_nested)}/{len(nested_keys)}개 누락 — "
            f"{sorted(missing_nested)}. per_side/excursion_stats 는 "
            f"per_side.long.<f> · per_side.short.<f> · excursion_stats.<f> 로 펴야 한다"
        )

        # 리스트 3종은 digest 로 가고 metrics 에 평문으로 들어오면 안 된다(파일이 폭발한다).
        for list_field in _names_by_kind(BacktestMetrics, "list"):
            assert not isinstance(metrics.get(list_field), list), (
                f"{corpus_id}: metrics[{list_field}] 가 리스트 원문이다 — "
                f"리스트 3종은 metrics_list_digests 로 간다"
            )

    # ★음성 대조 — 실행 대상이 0으로 붕괴하면 위 단언은 한 번도 평가되지 않는다(항진명제).
    assert covered >= 1, (
        f"metrics 를 실제로 가진 코퍼스가 0이다 (전체 {len(_corpora(baseline))}개, "
        f"skip 정본 {sorted(SKIPPED_CORPUS)}) — 이 시험은 아무것도 재지 못했다"
    )


def test_trade_dict_covers_all_rawtrade_fields() -> None:
    """`_trade_to_dict` 산출 키 ⊇ `RawTrade` 전 필드."""
    try:
        from scripts.regen_trust_layer_baseline import _trade_to_dict
    except ImportError as exc:  # pragma: no cover - 계약 위반 시에만
        pytest.fail(
            f"scripts.regen_trust_layer_baseline._trade_to_dict 를 import 못 했다: {exc}. "
            f"계약 §3.3 이 이 이름을 고정한다"
        )

    expected = {f.name for f in dataclasses.fields(RawTrade)}
    produced = _trade_to_dict(_dummy(RawTrade))

    assert isinstance(produced, dict), (
        f"_trade_to_dict 가 dict 를 안 돌려준다 (got {type(produced).__name__})"
    )
    missing = expected - set(produced)
    assert not missing, (
        f"거래 dict 에서 {len(missing)}/{len(expected)}개 필드 누락 — {sorted(missing)}. "
        f"dataclasses.fields(RawTrade) 자동 유도가 아니라 하드코딩 키 리스트를 쓰고 있다"
    )


def test_list_fields_have_digest_entries(baseline: dict[str, Any]) -> None:
    """리스트 3종 digest 존재 + **내용이 다르면 digest 도 다르다**(길이 digest 반증).

    baseline 은 리스트 원문을 남기지 않아 digest 를 직접 재계산할 수 없다. 대신 같은
    코퍼스 안에서 **내용이 서로 다른** 리스트 필드들이 같은 digest 를 갖는지 본다 —
    길이/개수만 해싱한 구현은 여기서 충돌한다.
    """
    list_fields = _names_by_kind(BacktestMetrics, "list")
    assert list_fields, "BacktestMetrics 에서 리스트 필드를 못 유도했다 — 분류 로직 결함"

    informative_corpora = 0
    for corpus_id, record in _corpora(baseline).items():
        if _is_skipped_entry(corpus_id, record):
            continue

        digests = record.get("metrics_list_digests")
        assert isinstance(digests, dict), (
            f"{corpus_id}: metrics_list_digests 가 없다 (got {type(digests).__name__}) — "
            f"리스트 3종 {sorted(list_fields)} 은 digest 로 고정해야 한다"
        )

        missing = list_fields - set(digests)
        assert not missing, (
            f"{corpus_id}: digest 누락 {sorted(missing)} (있는 키: {sorted(digests)})"
        )

        for name in sorted(list_fields):
            value = digests[name]
            assert isinstance(value, str) and DIGEST_RE.match(value), (
                f"{corpus_id}.{name}: digest 형식이 아니다 — {value!r}. "
                f"계약 형식은 'sha256:' + 64 hex"
            )

        substantive = {
            name: digests[name]
            for name in list_fields
            if digests[name] not in (NULL_DIGEST, EMPTY_LIST_DIGEST)
        }
        if len(substantive) < 2:
            continue

        informative_corpora += 1
        collisions = {
            value: sorted(k for k, v in substantive.items() if v == value)
            for value in set(substantive.values())
        }
        duplicated = {v: k for v, k in collisions.items() if len(k) > 1}
        assert not duplicated, (
            f"{corpus_id}: 내용이 서로 다른 리스트 필드가 같은 digest 를 가진다 — "
            f"{list(duplicated.values())}. 길이·개수만 해싱했을 가능성이 크다 "
            f"(drawdown_curve 와 buy_and_hold_curve 는 길이가 같고 내용이 다르다)"
        )

    assert informative_corpora >= 1, (
        "내용 있는 리스트 필드를 2종 이상 가진 코퍼스가 하나도 없다 — "
        "digest 상이성 단언이 한 번도 평가되지 않았다(항진명제). "
        "baseline 재생성이 리스트를 전부 null 로 채웠는지 확인해라"
    )
