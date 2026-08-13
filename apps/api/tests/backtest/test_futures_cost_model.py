# C8 선물형 비용모델 — taker/maker 분기 leg cost 손계산 오라클 + maker slippage 면제.
"""C8 (정직성 번들 Slice 3) — 단일 leg cost helper 검증.

grounding: pine_v2 엔진은 현재 maker 체결 producer 가 없음(limit/strategy.exit = H2 NOP,
BL-098/BL-104) → 모든 실제 체결은 taker(시장가·트리거). maker 분기는 resting-limit fill
도입 시 활성화될 forward 인프라이며 본 helper 단위 테스트로 정확성을 고정한다(circular
oracle 회피 — 엔진 실행 없이 손계산 oracle).
"""
from __future__ import annotations

from decimal import Decimal

from src.backtest.engine.v2_adapter import _leg_cost

_TAKER_FEE = Decimal("0.001")
_MAKER_FEE = Decimal("0.0002")
_SLIP = Decimal("0.0005")


def test_taker_leg_fee_and_slippage_hand_oracle() -> None:
    # 시장가·트리거 체결 = taker. notional=220 → fee=220*0.001=0.22, slip=220*0.0005=0.11.
    fee, slip = _leg_cost(
        Decimal("220"),
        fill_type="taker",
        taker_fee=_TAKER_FEE,
        maker_fee=_MAKER_FEE,
        slippage=_SLIP,
    )
    assert fee == Decimal("0.22")
    assert slip == Decimal("0.11")


def test_maker_leg_uses_maker_fee_and_zero_slippage() -> None:
    # resting post-only limit 체결 = maker. maker_fee 적용 + slippage 면제(limit 제외).
    fee, slip = _leg_cost(
        Decimal("220"),
        fill_type="maker",
        taker_fee=_TAKER_FEE,
        maker_fee=_MAKER_FEE,
        slippage=_SLIP,
    )
    assert fee == Decimal("0.044")  # 220 * 0.0002
    assert slip == Decimal("0")  # limit 슬리피지 미적용
