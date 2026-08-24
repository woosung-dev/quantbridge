"""Webhook HMAC 검증 + TV payload 파싱.

CSO-1: secret은 DB에서 암호화 저장 (secret_encrypted: bytes).
verify 시 EncryptionService.decrypt로 평문 복원 후 HMAC 비교.
Grace period 내 구 secret도 허용 (spec §2.4 rotation 정책).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from src.common.metrics import qb_order_rejected_total, qb_webhook_symbol_rejected_total
from src.common.metrics_multiproc import record_metric_safely
from src.common.normalized_symbol import normalize_symbol_input
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import StrategySettings, validate_strategy_settings
from src.trading.encryption import EncryptionService
from src.trading.exceptions import WebhookUnauthorized
from src.trading.models import OrderSide, OrderType
from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

logger = logging.getLogger(__name__)

# 미인식 심볼 원문을 로그에 남길 때의 상한. 진짜 포맷을 배우는 것이 목적이므로 자르되,
# 통째로 버리지는 않는다.
_SYMBOL_LOG_MAX = 64

# TV alert 은 JSON 불리언 대신 문자열을 보낼 수 있다. 아래 집합만 참으로 본다.
_TRUTHY = frozenset({"true", "1", "yes"})


def _coerce_bool(raw: object) -> bool:
    """★`bool("false") is True` 방어. 순진한 캐스팅이면 진입 주문이 청산으로 둔갑한다.

    같은 흉터가 이 레포에 있다 — `_parse_order_dispatch_snapshot` 이
    `isinstance(has_lev, bool)` 로 문자열 `has_leverage` 를 통째로 거부하는 이유가
    정확히 이것이다(`tasks/trading.py:197-198`). 여기선 TV alert template 이
    `"reduce_only": "true"` 를 보낼 수 있어 거부 대신 명시 화이트리스트를 쓴다.
    """
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in _TRUTHY
    if isinstance(raw, int):
        return raw != 0
    return False


def _optional_decimal(raw: object) -> Decimal | None:
    """빈 값은 None, 그 외는 Decimal. 변환 실패는 caller 의 except 가 401 로 붕괴시킨다."""
    if raw is None or raw == "":
        return None
    return Decimal(str(raw))


@dataclass(frozen=True, slots=True)
class ParsedTradeSignal:
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None
    # P1-12 (S5-A) — webhook close 주문이 #305 kill-switch SUM 대상이 되려면 TV alert
    # template 이 realized_pnl 을 포함해야 한다. live_signal 경로처럼 OrderRequest
    # 까지 전파되어 Order.realized_pnl 로 저장됨. 없으면 None (legacy backward-compat).
    realized_pnl: Decimal | None = None
    # BL-474 — 프론트(`test-order-webhook.ts:62-70`)가 이미 보내던 3 필드. 파서가
    # 안 읽어서 조용히 버려지고 있었다.
    # ★[BL-438] 2026-08-14 정정 — 종전 주석은 「청산 확정 경로 **전체**가 이 플래그를
    #   요구한다」고 적었는데 이제 거짓이다. 스윕은 `list_unsynced_with_exchange_exit`
    #   로 바뀌어 **거래소 원장의 청산 행**을 보므로 `reduce_only=false` 인 반전 청산도
    #   확정된다. 여전히 이 플래그를 요구하는 것은 단건 즉시 확정
    #   (`tasks/trading.py` `_refresh_closed_pnl_with_session` 의 `not order.reduce_only`
    #   조기 반환) 하나뿐이고, 그 경로가 건너뛴 주문은 스윕이 뒤늦게 회수한다.
    reduce_only: bool = False
    take_profit: Decimal | None = None
    stop_loss: Decimal | None = None
    # risk_percent 는 수량 **상한** 검증용이다 (`order_service._validate_position_size`
    # 가 `balance * risk_percent / 100 / abs(entry - stop)` 로 max_qty 를 구해 초과만
    # 거부한다). 수량을 만들어내지 않으므로 quantity 를 대체하지 않는다 — 다이얼로그
    # 문구도 그에 맞춰 정정했다.
    risk_percent: Decimal | None = None


class WebhookService:
    def __init__(
        self,
        repo: WebhookSecretRepository,
        crypto: EncryptionService,  # CSO-1: decrypt path
        *,
        grace_seconds: int,
        strategy_repo: StrategyRepository,
    ) -> None:
        self._repo = repo
        self._crypto = crypto
        self._grace = timedelta(seconds=grace_seconds)
        self._strategy_repo = strategy_repo

    async def verify(self, strategy_id: UUID, *, token: str, payload: bytes) -> bool:
        """grace_cutoff 이후 revoked된 secret까지 후보 포함.

        CSO-1: 각 candidate를 decrypt 후 HMAC compare_digest.
        """
        grace_cutoff = datetime.now(UTC) - self._grace
        candidates = await self._repo.list_valid_secrets(strategy_id, grace_cutoff=grace_cutoff)
        for ws in candidates:
            plaintext_secret = self._crypto.decrypt(ws.secret_encrypted)
            expected = hmac.new(plaintext_secret.encode(), payload, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, token):
                return True
        return False

    async def ensure_authorized(self, strategy_id: UUID, *, token: str, payload: bytes) -> None:
        if not await self.verify(strategy_id, token=token, payload=payload):
            raise WebhookUnauthorized("Invalid HMAC token or strategy_id")

    async def resolve_trading_params(self, strategy_id: UUID) -> StrategySettings:
        """BL-474 — webhook 주문의 leverage/margin_mode 를 Strategy.settings 에서 해결.

        ★payload 에서 받지 않는다. settings 가 SSOT 여야 `live_signal.py:931-932` /
        `close_service.py:86-92` 와 세 ingress 가 같은 시장으로 나간다. body 로
        override 를 허용하면 secret 보유자가 운영자의 리스크 설정을 우회한다.

        ★미설정은 fail-closed(422)다. spot 으로 흘려보내면 그 진입을 **닫을 수단이
        없다** — 모든 청산 경로가 linear reduce-only 로 나가고 거래소는 110017
        ("current position is zero") 로 거부한다. 게다가 청산 원장·코크핏·
        exchange_exits 가 전부 linear 전용이라 spot 체결은 확정 손익을 영원히 못 받는다.

        owner-scope 를 쓰지 않는 이유 — webhook 은 user context 가 없고 HMAC 자체가
        소유 증명이다. 계정↔전략 소유자 일치는 `OrderService` 의 TRD-4 게이트가
        독립적으로 재검사한다(`order_service.py:160-176`).
        """
        strategy = await self._strategy_repo.find_by_id(strategy_id)
        raw = strategy.settings if strategy is not None else None
        try:
            settings = validate_strategy_settings(raw)
        except ValidationError as exc:
            self._reject("settings_invalid", strategy_id)
            raise HTTPException(status_code=422, detail="settings_invalid") from exc
        if settings is None:
            self._reject("settings_unset", strategy_id)
            raise HTTPException(status_code=422, detail="settings_unset")
        return settings

    @staticmethod
    def _reject(reason: str, strategy_id: UUID) -> None:
        """거부는 반드시 보이게 한다 — 조용한 422 는 '왜 안 나가지' 로만 관측된다."""
        qb_order_rejected_total.labels(exchange="unknown", reason=reason).inc()
        logger.warning(
            "webhook_settings_rejected",
            extra={"strategy_id": str(strategy_id), "reason": reason},
        )


def _normalized_symbol_or_reject(raw: object) -> str:
    """웹훅 심볼을 canonical 로 정규화하고, 못 하면 관측을 남기고 거부한다 (BL-454).

    ★거부 자체는 바깥 `except (KeyError, ValueError, ...)` 가 `WebhookUnauthorized`
    (401) 로 바꾸므로 계약은 그대로다. 여기서 하는 일은 **그 거부를 보이게 만드는 것**
    뿐이다 — 카운터는 "일어나고 있나" 에만 답하고, TradingView 가 실제로 무슨 문자열을
    보내는지는 로그만 답한다. `{{ticker}}` 가 퍼프에서 `BTCUSDT` 인지 `BTCUSDT.P` 인지
    1차 출처로 확인하지 못했으므로, 장식 제거를 추측으로 넣는 대신 첫 실사용의 이 로그로
    실제 포맷을 배운다.
    """
    try:
        return normalize_symbol_input(raw)
    except ValueError:
        record_metric_safely(qb_webhook_symbol_rejected_total.inc)
        logger.warning(
            "webhook_symbol_normalize_failed",
            extra={"symbol": str(raw)[:_SYMBOL_LOG_MAX]},
        )
        raise


def parse_tv_payload(payload: dict[str, object]) -> ParsedTradeSignal:
    """TradingView alert payload -> 표준 signal. 필수 필드: symbol, side, quantity, type.

    Optional realized_pnl (P1-12, S5-A, PR #315) — close 주문의 청산 PnL. 누적손실
    kill-switch (CumulativeLoss / DailyLoss evaluator) 가 SUM 대상으로 사용.
    TV alert template 에 strategy 변수 ({{strategy.position_size}} 등) 로 계산해
    포함시키도록 사용자에게 권장. None 이면 legacy backward-compat (이전 alert
    template 호환).

    P1-12 (S6, BL-309): InvalidOperation 도 catch. Decimal('not-a-number') 은
    KeyError/ValueError/TypeError 가 아닌 decimal.InvalidOperation 을 raise 하므로
    이전엔 caller 에게 silent 전파 → 500. 이제 WebhookUnauthorized 로 통일.
    """
    from decimal import InvalidOperation

    try:
        # InvalidOperation (Decimal 자체 예외) 는 try-except 에서 catch.
        realized_pnl_raw = payload.get("realized_pnl")
        realized_pnl: Decimal | None = (
            None if realized_pnl_raw is None else Decimal(str(realized_pnl_raw))
        )
        return ParsedTradeSignal(
            symbol=_normalized_symbol_or_reject(payload["symbol"]),
            side=OrderSide(str(payload["side"]).lower()),
            type=OrderType(str(payload.get("type", "market")).lower()),
            quantity=Decimal(str(payload["quantity"])),
            price=Decimal(str(payload["price"])) if payload.get("price") else None,
            realized_pnl=realized_pnl,
            # BL-474 — 세 필드 모두 기존 try 안에서 읽어, malformed 값이 계속
            # WebhookUnauthorized(401) 로 붕괴되게 둔다(계약 불변).
            reduce_only=_coerce_bool(payload.get("reduce_only")),
            take_profit=_optional_decimal(payload.get("take_profit")),
            stop_loss=_optional_decimal(payload.get("stop_loss")),
            risk_percent=_optional_decimal(payload.get("risk_percent")),
        )
    except (KeyError, ValueError, TypeError, InvalidOperation) as e:
        raise WebhookUnauthorized(f"Invalid TV payload: {e}") from e
