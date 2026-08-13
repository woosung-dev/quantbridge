# Pine 전략의 기본 주문 수량 우선순위를 해석한다.

from __future__ import annotations

from src.strategy.pine_v2.ast_extractor import extract_content


def extract_pine_default_qty(source: str) -> tuple[str | None, float | None]:
    """Pine strategy() 의 default_qty_type/value 를 추출. strategy 가 아니면 (None, None).

    BL-185: ScriptContent.declaration 의 명시 필드 (TDD-1.1) 사용.
    """
    decl = extract_content(source).declaration
    if decl.kind != "strategy":
        return None, None
    qt = decl.default_qty_type
    qv_str = decl.default_qty_value
    qv: float | None = None
    if qv_str is not None:
        try:
            qv = float(qv_str)
        except (TypeError, ValueError):
            qv = None
    return qt, qv


def resolve_default_qty(
    source: str,
    *,
    initial_capital: float | None,
    live_position_size_pct: float | None = None,
    form_default_qty_type: str | None = None,
    form_default_qty_value: float | None = None,
) -> tuple[str | None, float | None]:
    """기본 주문 수량을 4단계 우선순위로 해석한다.

    BL-188 v3 D2 priority chain (Pine > form > Live > None):
      1. Pine `strategy(default_qty_type=..., default_qty_value=...)` 명시 → override
      2. Pine 미명시 + form_default_qty_type/value 명시 → 폼 값 사용
      3. Pine·form 미명시 + live_position_size_pct 명시 → ("strategy.percent_of_equity", live_pct)
      4. 모두 None → qty=1.0 fallback (회귀 호환)

    이 우선순위 체인의 단일 SSOT이며, backtest (`compat.parse_and_run_v2`)와 live
    (`event_loop.run_live`)가 공유한다.

    BL-479 — live tier 는 capital baseline 없이 silent skip 금지. pct 만 주고
    initial_capital 을 빠뜨리면 조용히 (None, None) 을 돌려 qty=1.0 fallback 으로
    실주문이 나간다. 그게 BL-479 가 없애려는 실패 그 자체라 여기서 fail-closed 한다.
    `compat.py` 의 동일 assert 는 남겨둔다 (그쪽은 classify_script 보다 먼저 터지는
    순서 계약이 있고, 이건 엔진 층 방어라 역할이 다르다).
    """
    if live_position_size_pct is not None and initial_capital is None:
        raise ValueError(
            "live_position_size_pct 명시 시 initial_capital 도 필수 — capital baseline "
            "없이 사이징을 건너뛰면 qty=1.0 으로 조용히 발주된다 (BL-479)."
        )
    if initial_capital is None:
        return None, None

    pine_qty_type, pine_qty_value = extract_pine_default_qty(source)
    if pine_qty_type is not None and pine_qty_value is not None:
        return pine_qty_type, pine_qty_value
    if form_default_qty_type is not None and form_default_qty_value is not None:
        return form_default_qty_type, form_default_qty_value
    if live_position_size_pct is not None:
        return "strategy.percent_of_equity", float(live_position_size_pct)
    return None, None
