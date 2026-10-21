"""새 코드 정책의 불변 실행 스냅샷. 기존 Pine 세션에는 적용하지 않는다."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from src.trading.product_policy import require_bybit_demo_account


class CodeSnapshotError(ValueError):
    pass


def validate_code_snapshot(
    snapshot: object, *, version: Any, version_id: UUID | None, account: Any
) -> dict[str, Any]:
    """실제 저장 소스와 핀 버전을 검증하며 미완성 계약은 닫힌 채로 거부한다."""
    require_bybit_demo_account(account.exchange, account.mode)
    if account.read_only is not False or not isinstance(snapshot, dict):
        raise CodeSnapshotError("쓰기 가능한 demo 계정과 실행 스냅샷이 필요합니다")
    expected = {
        "schema_version": 1,
        "source_policy": "code_v1",
        "policy_version": "swing_two_bar_v1",
        "execution_mode": "bybit_demo",
        "market_type": "linear",
    }
    if any(snapshot.get(key) != value for key, value in expected.items()):
        raise CodeSnapshotError("지원하지 않는 실행 정책입니다")
    if (
        version is None
        or version_id is None
        or str(version.id) != str(version_id)
        or snapshot.get("version_id") != str(version_id)
    ):
        raise CodeSnapshotError("실행 버전 핀이 일치하지 않습니다")
    source = getattr(version, "source_code", None)
    language = snapshot.get("language")
    if not isinstance(source, str) or language not in {"pine", "python", "typescript"}:
        raise CodeSnapshotError("동결 실행 소스·언어가 없습니다")
    digest = hashlib.sha256(source.encode()).hexdigest()
    if snapshot.get("source_hash") != digest or getattr(version, "source_hash", None) != digest:
        raise CodeSnapshotError("동결 실행 소스 해시가 일치하지 않습니다")
    if (
        getattr(version, "language", None) != language
        or getattr(version, "execution_policy", None) != "code_v1"
    ):
        raise CodeSnapshotError("저장 버전의 언어·정책이 일치하지 않습니다")
    warmup = snapshot.get("warmup_bars")
    if type(warmup) is not int or warmup < 0 or warmup != getattr(version, "warmup_bars", None):
        raise CodeSnapshotError("워밍업 계약이 일치하지 않습니다")
    if not isinstance(snapshot.get("params"), dict) or snapshot["params"] != getattr(
        version, "params", None
    ):
        raise CodeSnapshotError("실행 파라미터가 일치하지 않습니다")
    try:
        json.dumps(snapshot, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CodeSnapshotError("스냅샷은 유한한 JSON 값이어야 합니다") from exc
    return dict(snapshot)


def build_code_snapshot(*, version: Any, account: Any, settings: dict[str, Any]) -> dict[str, Any]:
    """요청의 파생값을 저장하지 않고 owner 확인이 끝난 버전으로 서버에서 재구성한다."""
    snapshot = {
        "schema_version": 1,
        "source_policy": "code_v1",
        "policy_version": "swing_two_bar_v1",
        "execution_mode": "bybit_demo",
        "market_type": "linear",
        "version_id": str(version.id),
        "language": getattr(version, "language", None),
        "source_hash": getattr(version, "source_hash", None),
        "params": getattr(version, "params", None),
        "warmup_bars": getattr(version, "warmup_bars", None),
        "execution_settings": settings,
    }
    return validate_code_snapshot(snapshot, version=version, version_id=version.id, account=account)
