"""동결 가설의 진입 규칙만 추출한다. 임의 사용자 소스 변환기는 아니다."""

from __future__ import annotations

import ast
import hashlib

from tools.research.catalogue import source_for

POSITION_BLOCK = """    position = ctx.get("position") or {}
    side = position.get("direction", "flat")
    if side == "long":
        entry = float(position["average_price"])
        risk_exit = c[-1] <= entry * 0.98 or c[-1] >= entry * 1.04
        return {"action": "close" if short_signal or not long_filter or risk_exit else "hold"}
    if side == "short":
        entry = float(position["average_price"])
        risk_exit = c[-1] >= entry * 1.02 or c[-1] <= entry * 0.96
        return {"action": "close" if long_signal or not short_filter or risk_exit else "hold"}
"""


def entry_source(candidate: dict) -> tuple[str, dict]:
    """원본의 정확한 단일 앵커를 확인한 뒤 position 의존 청산 절만 제거한다."""
    original = source_for(candidate)
    if original.count(POSITION_BLOCK) != 1:
        raise ValueError("동결 template의 position 앵커가 달라 진입 규칙을 추출할 수 없습니다")
    source = original.replace(POSITION_BLOCK, "", 1)
    tree = ast.parse(source)
    on_bar = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "on_bar"
    )
    if any(
        isinstance(node, ast.Name) and node.id in {"position", "side", "risk_exit"}
        for node in ast.walk(on_bar)
    ):
        raise ValueError("추출된 진입 규칙에 포지션 의존 로직이 남아 있습니다")
    return source, {
        "original_source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "entry_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "transform": "frozen_v2_remove_position_exit_block_v1",
        "entry_rule": "원래 TF 확정 종가의 filter AND entry signal; 보유 포지션과 무관",
        "new_exit_rule": "원본 close/SL/TP 무시; 동일 TF 직전 완료 2봉의 새 공통 risk policy",
        "comparison": "동일 진입 기회 규칙; 청산 차이로 실제 체결 시각·횟수는 달라질 수 있음",
    }
