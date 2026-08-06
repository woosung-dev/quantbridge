"""btgap 테스트가 공유하는 스크립트 로더 + 합성 픽스처 빌더.

★**이 파일은 테스트가 아니다** (`test_` 로 시작하지 않으므로 수집되지 않는다).
스크립트 두 벌을 importlib 로 올리는 절차와, `match`/`s1diff` 가 받는 JSON 모양을
한 자리에 모아 둔다 — 네 테스트 파일이 같은 로더를 네 번 베끼지 않게 하려는 것이다.

★**네트워크도 DB 도 타지 않는다.** `conftest._test_engine` 은 session-scoped 이고
autouse 가 아니므로 `drop_all` 이 돌지 않는다 — 소크가 살아 있어도 안전하다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"

SESSION_ID = UUID("11111111-0000-4000-8000-000000000001")
STRATEGY_ID = UUID("22222222-0000-4000-8000-000000000002")


def load_script(name: str) -> Any:
    """`scripts/<name>.py` 를 동적 import 한다.

    ★`sys.modules` 등록이 필수다 — 스크립트가 `from __future__ import annotations` +
    `@dataclass` 라, dataclasses 가 `sys.modules[cls.__module__].__dict__` 로 타입을
    되짚는다. 등록 없이 `exec_module` 하면 `AttributeError: 'NoneType'` 으로 죽는다.
    """
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# 라이브 key — `conditional_entry_planner` 가 만드는 세 형식 그대로
# --------------------------------------------------------------------------


def conditional_entry_key(
    *,
    bar_epoch: int,
    trigger: str,
    quantity: str,
    trade_id: str = "PbR",
    kind: str = "cond",
    session_id: UUID = SESSION_ID,
) -> str:
    """`live:<sess>:cond:<bar_epoch>:<stop>:<qty>:<trade_id>`."""
    return f"live:{session_id}:{kind}:{bar_epoch}:{trigger}:{quantity}:{trade_id}"


def market_entry_key(
    *,
    bar_time_iso: str,
    sequence_no: int = 0,
    trade_id: str = "PbR",
    session_id: UUID = SESSION_ID,
) -> str:
    """`live:<sess>:<bar_time ISO>:<seq>:entry:<trade_id>`."""
    return f"live:{session_id}:{bar_time_iso}:{sequence_no}:entry:{trade_id}"


# --------------------------------------------------------------------------
# 동결 입력 스키마 빌더 — CONTROL 이 덤프하는 모양
# --------------------------------------------------------------------------


def order_row(
    *,
    order_id: str,
    side: str,
    idempotency_key: str | None,
    filled_price: str | None = None,
    filled_quantity: str | None = "0.01",
    quantity: str = "0.01",
    state: str = "filled",
    reduce_only: bool = False,
    realized_pnl: str | None = None,
    realized_pnl_synced_at: str | None = None,
    filled_at: str | None = None,
    price: str | None = None,
) -> dict[str, Any]:
    return {
        "id": order_id,
        "idempotency_key": idempotency_key,
        "side": side,
        "quantity": quantity,
        "price": price,
        "filled_price": filled_price,
        "filled_quantity": filled_quantity,
        "realized_pnl": realized_pnl,
        "realized_pnl_synced_at": realized_pnl_synced_at,
        "filled_at": filled_at,
        "state": state,
        "reduce_only": reduce_only,
    }


def exit_row(
    *,
    exit_id: str,
    closed_pnl: str,
    matched_order_id: str | None = None,
    side: str | None = "Sell",
    closed_size: str | None = "0.01",
    avg_entry_price: str | None = "60000",
    avg_exit_price: str | None = "60100",
    exchange_created_at: str = "2026-08-05T00:05:00+00:00",
    order_link_id: str | None = None,
    classification: str = "ours",
    attribution_confidence: str = "exact",
) -> dict[str, Any]:
    """★`side` 는 거래소 원본(`Buy`/`Sell`)이다 — ccxt 가 뒤집기 전 값."""
    return {
        "id": exit_id,
        "order_link_id": order_link_id,
        "matched_order_id": matched_order_id,
        "side": side,
        "closed_pnl": closed_pnl,
        "closed_size": closed_size,
        "avg_entry_price": avg_entry_price,
        "avg_exit_price": avg_exit_price,
        "exchange_created_at": exchange_created_at,
        "classification": classification,
        "attribution_confidence": attribution_confidence,
    }


def as_dumped_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """★실덤프 모양으로 부풀린다 — 한 청산 event 가 **2행**으로 온다.

    payload 는 같고 `classification` 만 `ours`/`unknown` 으로 갈리며 `id` 만 다르다
    (eval2 실측: 172행 / 86 event). 이 helper 를 거치지 않은 픽스처는 실입력이 아니다.
    """
    dumped: list[dict[str, Any]] = []
    for event in events:
        # 살아남는 쪽(`ours`)이 원래 id 를 갖게 두면 테스트가 읽힌다. 실덤프는 두 행이
        # 서로 다른 uuid 를 갖고, 여기서 중요한 것은 **id 가 다르다**는 사실뿐이다.
        dumped.append({**event, "classification": "ours"})
        dumped.append({**event, "id": f"{event['id']}-dup", "classification": "unknown"})
    return dumped


def session_row(
    *,
    interval: str = "1m",
    symbol: str = "BTC/USDT:USDT",
    created_at: str = "2026-08-05T00:00:00+00:00",
    deactivated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(SESSION_ID),
        "strategy_id": str(STRATEGY_ID),
        "symbol": symbol,
        "interval": interval,
        "created_at": created_at,
        "deactivated_at": deactivated_at,
    }


def trade_row(
    *,
    trade_index: int,
    direction: str = "long",
    entry_time: str = "2026-08-05T00:01:00+00:00",
    exit_time: str | None = "2026-08-05T00:05:00+00:00",
    entry_price: str = "60000",
    exit_price: str | None = "60100",
    size: str = "0.01",
    pnl: str = "0.4",
    fees: str = "0.6",
    fee_paid: str | None = "0.4",
    slippage_paid: str | None = "0.2",
    # ★`comment` 가 라이브 key 의 `trade_id` 와 맞물리는 자리다
    #   (`strategy.entry("PbR", …, comment="PbR")`).
    comment: str | None = "PbR",
    exit_kind: str | None = None,
    status: str = "closed",
) -> dict[str, Any]:
    """`run` 이 낸 trades.json 의 한 행. ★`pnl` 은 net 이다 (gross = pnl + fees)."""
    return {
        "trade_index": trade_index,
        "direction": direction,
        "status": status,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "size": size,
        "pnl": pnl,
        "fees": fees,
        "fee_paid": fee_paid,
        "slippage_paid": slippage_paid,
        "comment": comment,
        "exit_kind": exit_kind,
    }


def collect_floats(node: Any, path: str = "$") -> list[str]:
    """JSON 트리에서 `float` 가 남은 자리를 전부 찾는다 (Decimal 규율 검사용)."""
    found: list[str] = []
    if isinstance(node, float):
        found.append(path)
    elif isinstance(node, dict):
        for key, value in node.items():
            found.extend(collect_floats(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(collect_floats(value, f"{path}[{index}]"))
    return found
