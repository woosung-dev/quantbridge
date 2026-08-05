"""[BL-595] `position_divergence` 사망 5건을 얼린 입력으로 재현하고, 원장 권한이 그것을 닫는지 본다.

## 이 파일이 답하는 질문 둘

1. **판별력** — 수리 **전** 동작(= `ledger_conditional_fills` 를 안 넘기는 호출)이 사망 5건의
   발산을 실제로 재현하는가. 재현하지 못하면 아래 2 의 green 은 아무 의미가 없다.
2. **수리** — 원장이 증언한 체결만 인정하면 5건 전부에서 엔진과 거래소가 **같은 부호**가 되는가.

## 오라클 (★엔진을 안 거친다)

`oracle.ledger_net_at_death` = `Σ(buy:+filled_quantity, sell:-filled_quantity)` (사망 시각 이전).
순수 원장 산술이고, 워커 로그가 남은 3건에서 로그의 `exchange_position` 과 3/3 일치한다.
판정자는 **프로덕션 분류기** `_classify_position_divergence` 다 — 「이 tick 이 세션을 죽이는가」를
그 함수가 정의하므로, 테스트가 자기 문턱을 새로 만들면 다른 질문에 답하게 된다.

## 픽스처는 네트워크도 DB 도 안 탄다

`backend/scripts/capture_bl595_death_fixtures.py` 가 한 번 뜬 JSON 만 읽는다. Pine 소스는
`tests/fixtures/pine_corpus_v2/s1_pbr.pine` 을 쓴다 — 소크가 돌리는 전략과 **md5 동일**이며
픽스처가 그 md5 를 실어 대조한다(다르면 skip 이 아니라 **fail** 이다. 조용히 넘어가면
「그 전략을 검증했다」가 거짓이 된다).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_live
from src.tasks.live_signal import _classify_position_divergence

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "bl595"
_PINE_SOURCE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "pine_corpus_v2" / "s1_pbr.pine"
)
# 조건부 진입 key 의 두 형식. `conditional_entry_planner.CONDITIONAL_ENTRY_KINDS` 와 같은 값이며,
# 여기서 다시 적는 이유는 이 테스트가 **원장 문자열의 소비자**이지 그 파서의 단위 테스트가
# 아니기 때문이다. 두 값이 갈리면 아래 `test_fixture_shape` 가 잡는다.
_CONDITIONAL_KINDS = ("cond", "condmkt")


@dataclass(frozen=True, slots=True)
class DeathFixture:
    prefix: str
    payload: dict[str, Any]

    def __str__(self) -> str:  # pytest 파라미터 id
        return self.prefix


def _load_fixtures() -> list[DeathFixture]:
    return [
        DeathFixture(prefix=path.stem, payload=json.loads(path.read_text()))
        for path in sorted(_FIXTURE_DIR.glob("*.json"))
    ]


_FIXTURES = _load_fixtures()


def _frame(rows: list[list[Any]]) -> pd.DataFrame:
    """`live_signal._ohlcv_rows_to_dataframe` 와 같은 모양을 만든다."""
    frame = pd.DataFrame(rows, columns=["timestamp_ms", "open", "high", "low", "close", "volume"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp_ms"], unit="ms", utc=True)
    return frame.drop(columns=["timestamp_ms"])


def _run_kwargs(fixture: DeathFixture) -> dict[str, Any]:
    kwargs = dict(fixture.payload["run_live_kwargs"])
    kwargs["sessions_allowed"] = tuple(kwargs["sessions_allowed"])
    kwargs["position_epoch"] = datetime.fromisoformat(kwargs["position_epoch"])
    emit = kwargs.pop("emit_from_bar_time")
    if emit is not None:
        kwargs["emit_from_bar_time"] = datetime.fromisoformat(emit)
    return kwargs


def _conditional_fills(fixture: DeathFixture) -> list[Any]:
    """원장이 증언하는 조건부 진입 체결 — 사망 tick 이 **볼 수 있었던 것만**.

    `observed_before_death` 로 거르는 이유: 사망 시각 뒤에 관측된 체결을 넣으면 그 tick 이
    알 수 없었던 정보로 판정하는 것이 되어, 수리의 효과를 **과대평가**한다.
    """
    from src.strategy.pine_v2.strategy_state import LedgerConditionalFill

    fills = []
    for order in fixture.payload["ledger_orders"]:
        if order["entry_kind"] not in _CONDITIONAL_KINDS:
            continue
        if not order["observed_before_death"]:
            continue
        quantity = order["filled_quantity"]
        price = order["filled_price"]
        if quantity is None or price is None or Decimal(quantity) == 0:
            continue
        fills.append(
            LedgerConditionalFill(
                trade_id=order["trade_id"],
                filled_at=datetime.fromisoformat(order["filled_at"]),
                fill_price=float(price),
            )
        )
    return fills


def _engine_position(fixture: DeathFixture, **extra: Any) -> Decimal:
    source = _PINE_SOURCE_PATH.read_text()
    digest = hashlib.md5(source.encode()).hexdigest()
    assert digest == fixture.payload["pine_source_md5"], (
        "픽스처를 뜬 전략과 코퍼스의 s1_pbr.pine 이 다르다 — 이 테스트는 그 전략을 검증하지 못한다"
    )
    result = run_live(source, _frame(fixture.payload["ohlcv"]), **_run_kwargs(fixture), **extra)
    return Decimal(str(result.strategy_state_report["position_size"]))


def _ledger_net(fixture: DeathFixture) -> Decimal:
    return Decimal(fixture.payload["oracle"]["ledger_net_at_death"])


def test_every_death_has_a_fixture() -> None:
    """★공허화 방지 — 픽스처가 사라지면 아래 파라미터가 0개가 되어 전부 조용히 통과한다."""
    assert len(_FIXTURES) == 5, f"사망 픽스처 5건을 기대했는데 {len(_FIXTURES)}건이다"


@pytest.mark.parametrize("fixture", _FIXTURES, ids=str)
def test_fixture_shape(fixture: DeathFixture) -> None:
    """픽스처가 판정에 필요한 것을 전부 싣고 있는가 (조용한 결측 방지)."""
    payload = fixture.payload
    assert len(payload["ohlcv"]) == 300
    assert payload["oracle"]["ledger_net_at_death"] not in (None, "0")
    assert Decimal(str(payload["oracle"]["engine_position_previous_tick"])) != 0
    # 조건부 진입 체결이 하나도 없으면 원장 권한이 판정할 것 자체가 없다.
    assert _conditional_fills(fixture), "조건부 진입 체결이 원장에 하나도 없다"


@pytest.mark.parametrize("fixture", _FIXTURES, ids=str)
def test_replay_without_ledger_authority_reproduces_the_death(fixture: DeathFixture) -> None:
    """★판별력 — 수리 전 동작이 사망 시점의 `direction` 발산을 실제로 재현한다.

    이 테스트는 수리 뒤에도 **계속 green 이어야 한다** — 인자를 안 넘기면 기존 경로이기
    때문이다. red 로 바뀌면 라이브 전용 분기가 기본 경로로 샌 것이다.
    """
    engine = _engine_position(fixture)
    ledger = _ledger_net(fixture)
    assert _classify_position_divergence(engine, ledger) == "direction", (
        f"{fixture.prefix}: 엔진 {engine} vs 원장 {ledger} 이 direction 발산이 아니다 "
        "— 픽스처가 사망을 재현하지 못하므로 아래 수리 테스트의 green 은 근거가 없다"
    )
    # 재구성이 충실한지 한 번 더 — 영속 보고서와 비트 단위로 같아야 한다.
    # ★`Decimal(float)` 은 이진 전개를 그대로 편다. 문자열을 거쳐야 보고서 값과 비교된다.
    assert engine == Decimal(str(fixture.payload["oracle"]["engine_position_previous_tick"]))


@pytest.mark.parametrize("fixture", _FIXTURES, ids=str)
def test_ledger_authority_makes_the_engine_agree_with_the_exchange(
    fixture: DeathFixture,
) -> None:
    """★수리 — 원장이 증언한 체결만 인정하면 그 tick 은 세션을 죽이지 않는다."""
    engine = _engine_position(fixture, ledger_conditional_fills=_conditional_fills(fixture))
    ledger = _ledger_net(fixture)
    category = _classify_position_divergence(engine, ledger)
    assert category is None, f"{fixture.prefix}: 엔진 {engine} vs 원장 {ledger} → {category}"
