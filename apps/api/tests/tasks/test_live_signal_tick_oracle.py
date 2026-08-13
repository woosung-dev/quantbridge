"""`_evaluate_session_inner` 차분 오라클 — tick 이 만든 상태 **전부**를 얼린다.

왜 있나
-------
이 함수 계열(`_evaluate_session_with_engine`, 580줄)에는 **행위 오라클이 없었다.**
기존 5파일은 각자 필요한 필드 하나씩만 단언한다 — "죽었나", "counter 가 늘었나".
그 형태는 **단언되지 않은 표면이 조용히 바뀌는 것을 못 막는다.** 이 레포는 그 계열의
결함(검사기가 없어서 살아 있던 결함)으로 이미 세 번 덴 적이 있다.

무엇을 얼리나 — 판정 하나가 아니다
----------------------------------
`_evaluate_session_inner` 의 반환 `dict[str, Any]` 는 **tick 이 만든 상태의 일부일
뿐이다.** 반환값만 얼리면 `_block_on_direction_divergence` 를 통째로 no-op 으로 만드는
변이가 **통과한다**(반환 dict 는 그대로인데 세션은 안 죽는다). 그래서 이 오라클은
반환값 + **부작용 원장**을 함께 동결한다:

- 반환 dict
- `deactivate` / `commit` / `upsert_state` / `insert_pending_events` 호출 수와 **인자**
- outbox dispatch enqueue · 실시간 발행 · 알림 발송
- 조건부 진입 리컨사일 호출 인자
- 거래소 조회 횟수
- 이 tick 이 움직인 **prometheus counter 델타 전량**(`qb_` 접두 전부 — 이름을 열거하지
  않으므로 새 counter 가 생겨도 차분에 잡힌다)

★**분류기를 우회하지 않는다.** 기존 `_evaluate_with_divergence`(instrument_parity)는
`_detect_position_divergence` 를 통째로 monkeypatch 해서 `_classify_position_divergence`
가 **한 번도 안 돈다**. 이 오라클은 봉하는 자리를 **거래소 provider 까지 내려서**
`_net_position_size` → `_classify_position_divergence` → `_detect_position_divergence`
전 구간을 실제로 밟는다. 킬 분기(`(engine > 0) != (exchange > 0)`)를 뒤집는 변이가
차분에 잡히는 것은 이 선택 덕분이다.

★**자기 재검증 루프가 없다.** 이 파일은 픽스처를 **읽어서 비교만** 한다 — 기대값을
런타임에 코드로부터 다시 만들지 않는다. 픽스처의 `expected` 는 1회 포획 후
`_how`/`_contract` 에 적힌 소스 계약과 손으로 대조해 동결한 값이다.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from prometheus_client import REGISTRY

from src.strategy.pine_v2.event_loop import LiveSignal, LiveSignalResult
from src.trading.models import LiveSignalEventStatus
from tests.tasks.test_live_signal_eval_task import (
    _build_session_obj,
    _build_strategy,
    _demo_account_repo,
    _patch_inner_dependencies,
    live_signal_module,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "tick_oracle"

# ★`deactivate(at=datetime.now(UTC))` 는 비결정이다. 값 자체를 얼리면 매 실행 red 가
#   되므로 "지금 근처인가" 만 얼린다. 픽스처의 bar 시각(2026-05)과 겹치지 않는 폭이다.
_NOW_TOLERANCE = timedelta(minutes=5)


# ---------------------------------------------------------------------------
# 정규화 — 비결정 5축(uuid4 · now · ccxt · DB · 전역 레지스트리)을 토큰으로 접는다
# ---------------------------------------------------------------------------


def _scrub(text: str, ids: dict[str, str]) -> str:
    """문자열 안에 박힌 uuid(전체·앞 8자)를 심볼 토큰으로 바꾼다.

    알림 message/context 는 `str(session_id)[:8]` 처럼 **잘린** uuid 를 담는다. 전체
    문자열만 치환하면 그 자리가 매 실행 달라져 차분이 못 쓰게 된다.
    """
    for raw, token in ids.items():
        text = text.replace(raw, token).replace(raw[:8], f"{token}[:8]")
    return text


def _normalize(value: Any, ids: dict[str, str]) -> Any:
    """관측값 → JSON 비교 가능한 정규형. 타입은 접두로 보존한다(문자열 "0" 과 Decimal("0") 구분)."""
    if isinstance(value, bool) or value is None or isinstance(value, int | float | str):
        return _scrub(value, ids) if isinstance(value, str) else value
    if isinstance(value, Decimal):
        return f"dec:{value}"
    if isinstance(value, datetime):
        if abs(value - datetime.now(UTC)) < _NOW_TOLERANCE:
            return "dt:<now>"
        return f"dt:{value.isoformat()}"
    if isinstance(value, UUID):
        return ids.get(str(value), "id:<unknown-uuid>")
    if isinstance(value, dict):
        return {
            str(k): _normalize(v, ids) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, list | tuple):
        return [_normalize(v, ids) for v in value]
    if isinstance(value, set | frozenset):
        return sorted(_normalize(v, ids) for v in value)
    if isinstance(value, SimpleNamespace):
        return _normalize(vars(value), ids)
    return f"repr:{_scrub(repr(value), ids)}"


def _metric_snapshot() -> dict[str, float]:
    """`qb_` 접두 시계열 전량. ★이름을 열거하지 않는다 — 새 counter 도 차분에 걸린다."""
    out: dict[str, float] = {}
    for metric in REGISTRY.collect():
        if not metric.name.startswith("qb_"):
            continue
        for sample in metric.samples:
            if sample.name.endswith("_created"):
                continue
            labels = ",".join(f"{k}={v}" for k, v in sorted(sample.labels.items()))
            out[f"{sample.name}{{{labels}}}" if labels else sample.name] = sample.value
    return out


def _metric_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    delta: dict[str, float] = {}
    for key, value in after.items():
        moved = value - before.get(key, 0.0)
        if moved:
            delta[key] = moved
    return delta


async def _flush_pending_alerts() -> None:
    """fire-and-forget 알림(`create_task`)이 끝나도록 양보한다. ★metric 스냅샷 **전에** 돈다."""
    for _ in range(5):
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# 입력 조립 — 픽스처의 `input` 만 읽는다
# ---------------------------------------------------------------------------


def _dt(raw: str | None) -> datetime | None:
    return None if raw is None else datetime.fromisoformat(raw)


def _dec(raw: str | None) -> Decimal | None:
    return None if raw is None else Decimal(raw)


def _build_signals(rows: list[dict[str, Any]]) -> list[LiveSignal]:
    return [
        LiveSignal(
            action=row["action"],
            direction=row["direction"],
            trade_id=row["trade_id"],
            qty=row["qty"],
            sequence_no=row["sequence_no"],
            comment=row.get("comment", ""),
            realized_pnl=_dec(row.get("realized_pnl")),
        )
        for row in rows
    ]


def _build_run_live_result(spec: dict[str, Any]) -> LiveSignalResult:
    return LiveSignalResult(
        last_bar_time=_dt(spec["last_bar_time"]),  # type: ignore[arg-type]
        signals=_build_signals(spec["signals"]),
        strategy_state_report=spec["strategy_state_report"],
        total_closed_trades=spec["total_closed_trades"],
        total_realized_pnl=Decimal(spec["total_realized_pnl"]),
        errors=[(int(bar), str(msg)) for bar, msg in spec.get("errors", [])],
        entry_skips=spec.get("entry_skips", []),
        liquidations=spec.get("liquidations", []),
    )


def _build_events(rows: list[dict[str, Any]]) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            id=uuid4(),
            bar_time=_dt(row["bar_time"]),
            sequence_no=row["sequence_no"],
            action=row["action"],
            trade_id=row["trade_id"],
            direction=row.get("direction", "long"),
            qty=row.get("qty", 1.0),
            realized_pnl=_dec(row.get("realized_pnl")),
            status=LiveSignalEventStatus(row.get("status", "pending")),
        )
        for row in rows
    ]


def _patch_exchange(monkeypatch: pytest.MonkeyPatch, spec: Any) -> AsyncMock:
    """★봉하는 자리를 provider 까지 내린다 — 실제 분류기가 돌아야 킬 분기 변이가 잡힌다."""
    import src.trading.encryption as encryption_mod
    import src.trading.providers as providers_mod
    import src.trading.services.account_service as account_service_mod

    provider = AsyncMock()
    if spec == "probe_error":
        provider.fetch_open_positions = AsyncMock(side_effect=RuntimeError("bybit down"))
    else:
        provider.fetch_open_positions = AsyncMock(
            return_value=[
                SimpleNamespace(side=row["side"], size=Decimal(row["size"])) for row in spec
            ]
        )
    monkeypatch.setattr(providers_mod, "BybitFuturesProvider", MagicMock(return_value=provider))
    monkeypatch.setattr(encryption_mod, "EncryptionService", MagicMock())
    service = MagicMock()
    service.get_credentials_for_order = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr(
        account_service_mod, "ExchangeAccountService", MagicMock(return_value=service)
    )
    return provider


async def run_tick(monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]) -> dict[str, Any]:
    """픽스처 입력으로 tick 을 1회 돌리고 **관측 표면 전체**를 정규형으로 돌려준다."""
    spec = case["input"]
    sess_spec = spec["session"]

    sess = _build_session_obj(
        is_active=sess_spec["is_active"],
        last_evaluated_bar_time=_dt(sess_spec["last_evaluated_bar_time"]),
        equity_baseline_usdt=_dec(sess_spec["equity_baseline_usdt"]),
    )
    sess.symbol = sess_spec["symbol"]
    sess.created_at = _dt(sess_spec["created_at"])
    # `SessionScope.from_live_session` 이 읽는다. 없으면 원장 그림자가 통째로
    # `fetch_failed` 로 접혀 그 tick 의 계측 표면이 사라진다.
    sess.deactivated_at = None

    ids = {
        str(sess.id): "id:<session>",
        str(sess.user_id): "id:<user>",
        str(sess.strategy_id): "id:<strategy>",
        str(sess.exchange_account_id): "id:<account>",
    }

    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=spec["try_claim_bar"])
    sess_repo.deactivate = AsyncMock(return_value=spec["deactivate_rows"])
    sess_repo.commit = AsyncMock()
    sess_repo.upsert_state = AsyncMock()
    previous = spec["previous_state"]
    sess_repo.get_state = AsyncMock(
        return_value=None
        if previous is None
        else SimpleNamespace(
            last_strategy_state_report=previous["last_strategy_state_report"],
            equity_curve=previous["equity_curve"],
        )
    )

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(
            sess.strategy_id,
            pine_source=spec["strategy"]["pine_source"],
            position_size_pct=spec["strategy"]["position_size_pct"],
            leverage=spec["strategy"]["leverage"],
        )
    )

    inserted = _build_events(spec["inserted_events"])
    for index, event in enumerate(inserted):
        ids[str(event.id)] = f"id:<event-{index}>"
    event_repo = AsyncMock()
    event_repo.list_by_session = AsyncMock(return_value=_build_events(spec["existing_events"]))
    event_repo.insert_pending_events = AsyncMock(return_value=inserted)

    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=event_repo,
        account_repo=_demo_account_repo(),
        strategy_repo=strategy_repo,
        ohlcv_rows=spec["ohlcv"],
        run_live_result=_build_run_live_result(spec["run_live_result"]),
        carry_result=(Decimal(spec["carry"][0]), spec["carry"][1]),
        ledger_result=(Decimal(spec["ledger"][0]), spec["ledger"][1]),
    )

    provider = _patch_exchange(monkeypatch, spec["exchange"])

    # 원장 그림자(`_capture_ledger_shadow`)와 engine_only 세분화가 쓰는 조회를 고정한다.
    import src.trading.repositories.order_repository as order_repository_mod

    order_repo = AsyncMock()
    if spec.get("ledger_fills") == "probe_error":
        # 원장 조회가 실패하면 `_capture_ledger_shadow` 가 `conditional_fills` 를 None 으로
        # 접는다 — [ADR-025] §⑧ 의 fail-open tick 이다. 기본값(`[]`)은 그대로 두므로
        # 이 knob 을 안 쓰는 기존 케이스의 관측 표면은 바뀌지 않는다.
        order_repo.list_fills_since = AsyncMock(side_effect=RuntimeError("ledger down"))
    else:
        order_repo.list_fills_since = AsyncMock(return_value=[])
    order_repo.list_resting_conditional_entries = AsyncMock(return_value=[])
    monkeypatch.setattr(order_repository_mod, "OrderRepository", MagicMock(return_value=order_repo))

    dispatch_spy = MagicMock()
    monkeypatch.setattr(
        live_signal_module.dispatch_live_signal_event_task, "apply_async", dispatch_spy
    )
    publisher = AsyncMock()
    monkeypatch.setattr(live_signal_module, "publish_realtime", publisher)
    alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(live_signal_module, "send_rule_alert", alert)
    reconcile = AsyncMock()
    monkeypatch.setattr(live_signal_module, "_reconcile_conditional_entries", reconcile)

    before = _metric_snapshot()
    # ★interval 은 metric label 이 아니라 **판정 입력**이다(strike TTL·평가 공백이 봉 길이로
    #   잰다). 1m 케이스만 있으면 15m·1h 에서만 깨지는 결함이 통째로 안 보인다.
    returned = await live_signal_module._evaluate_session_inner(
        sess.id, spec.get("interval", "1m")
    )
    await _flush_pending_alerts()
    after = _metric_snapshot()

    def _kwargs_of(mock: Any) -> Any:
        """호출 안 됐으면 None. ★`await_args` 는 미호출 시 None 이라 먼저 세어야 한다."""
        if not mock.await_count:
            return None
        return _normalize(dict(mock.await_args.kwargs), ids)

    def _args_of(mock: Any) -> Any:
        if not mock.await_count:
            return None
        return _normalize(list(mock.await_args.args), ids)

    def _deactivate_call() -> Any:
        if not sess_repo.deactivate.await_count:
            return None
        call = sess_repo.deactivate.await_args
        return _normalize({"args": list(call.args), **call.kwargs}, ids)

    return {
        "return": _normalize(returned, ids),
        "calls": {
            "try_claim_bar": sess_repo.try_claim_bar.await_count,
            "deactivate": sess_repo.deactivate.await_count,
            "commit": sess_repo.commit.await_count,
            "upsert_state": sess_repo.upsert_state.await_count,
            "list_by_session": event_repo.list_by_session.await_count,
            "insert_pending_events": event_repo.insert_pending_events.await_count,
            "publish_realtime": publisher.await_count,
            "dispatch_apply_async": dispatch_spy.call_count,
            "send_rule_alert": alert.await_count,
            "reconcile_conditional_entries": reconcile.await_count,
            "fetch_open_positions": provider.fetch_open_positions.await_count,
        },
        "deactivate": _deactivate_call(),
        "upsert_state": _kwargs_of(sess_repo.upsert_state),
        "insert_pending_events": _kwargs_of(event_repo.insert_pending_events),
        "publish_realtime": _args_of(publisher),
        "dispatch": _normalize([dict(call.kwargs) for call in dispatch_spy.call_args_list], ids),
        "alert": _kwargs_of(alert),
        "reconcile": _kwargs_of(reconcile),
        "metrics": _metric_delta(before, after),
    }


# ---------------------------------------------------------------------------
# 차분 — 읽고 비교만 한다
# ---------------------------------------------------------------------------


def _case_ids() -> list[str]:
    return sorted(path.stem for path in FIXTURE_DIR.glob("*.json"))


def _load(case_id: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (FIXTURE_DIR / f"{case_id}.json").read_text(encoding="utf-8")
    )
    return loaded


@pytest.mark.parametrize("case_id", _case_ids())
@pytest.mark.asyncio
async def test_tick_surface_matches_frozen_oracle(
    case_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tick 이 만든 상태 전부가 동결본과 **완전 일치**해야 한다.

    필드 하나만 보는 단언이 아니다 — 반환값이 같아도 부작용이 달라지면 red 다.
    """
    case = _load(case_id)
    observed = await run_tick(monkeypatch, case)
    assert observed == case["expected"], case["_how"]


def test_every_case_declares_its_contract() -> None:
    """★기대값의 출처가 없으면 그 동결은 근거가 아니라 관성이다.

    `_how` 는 이 케이스가 무엇을 재는지, `_contract` 는 기대값이 어느 소스 계약에서
    나왔는지를 적는다. 비어 있으면 다음 사람이 red 를 보고 **기대값 쪽을 고쳐서**
    통과시킨다 — 오라클이 그 순간 사라진다.
    """
    case_ids = _case_ids()
    assert case_ids, "픽스처가 하나도 없으면 이 파일은 아무것도 재지 않는다"
    for case_id in case_ids:
        case = _load(case_id)
        assert case["_how"].strip(), case_id
        assert case["_contract"].strip(), case_id
        assert case["expected"]["metrics"], f"{case_id}: 아무 counter 도 안 움직인 tick 은 없다"


def test_kill_path_cases_cover_both_sides_of_the_grace_window() -> None:
    """★유예 창의 **양쪽**이 다 있어야 2-tick 규칙이 실제로 고정된다.

    한쪽만 있으면 `direction_mismatch_persisted` 를 상수로 만드는 변이가 절반은
    통과한다(항상 True 면 1회차 케이스가, 항상 False 면 2회차 케이스가 잡는다).
    """
    killed: list[str] = []
    survived_first: list[str] = []
    for case_id in _case_ids():
        expected = _load(case_id)["expected"]
        if expected["return"].get("deactivated") == "position_divergence":
            killed.append(case_id)
            continue
        upsert = expected["upsert_state"]
        if (
            expected["return"].get("evaluated")
            and upsert is not None
            and upsert["last_strategy_state_report"].get("_qb_direction_mismatch_seen") is True
        ):
            # 방향 불일치를 **봤는데도** 살아서 strike 만 다음 tick 으로 넘긴 케이스.
            survived_first.append(case_id)
    assert killed, "2회 연속 방향 불일치로 죽는 케이스가 없다"
    assert survived_first, "1회차 방향 불일치를 살려 보내는 케이스가 없다"
